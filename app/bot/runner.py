import time
import signal
import sys
import logging
import requests
from app.config import settings
from app.database.session import SessionLocal
from app.bot.handlers import (
    handle_start, handle_help, handle_preferences, handle_locations_menu,
    handle_categories_menu, handle_modes_menu, handle_toggle_callback,
    handle_sources, handle_status, handle_pause, handle_resume,
    handle_events, handle_latest
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hackradar.bot.runner")

# Global graceful shutdown flag
_shutdown_requested = False

def sig_handler(signum, frame):
    global _shutdown_requested
    sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    logger.info(f"Received {sig_name}. Shutting down Telegram bot gracefully...")
    _shutdown_requested = True

def mask_token(token: str) -> str:
    """Mask token for safe logging without exposing secrets"""
    if not token or len(token) < 10:
        return "***"
    return f"{token[:4]}...{token[-4:]}"

def verify_and_clear_webhook(token: str) -> bool:
    """
    Verify bot credentials and ensure any existing webhook is removed
    so that getUpdates long-polling operates without 409 Conflict.
    """
    masked = mask_token(token)
    try:
        # 1. Verify getMe
        me_resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        me_data = me_resp.json()
        if not me_data.get("ok"):
            err_code = me_data.get("error_code")
            desc = me_data.get("description", "Unknown error")
            if err_code == 401:
                logger.error(f"❌ Telegram authentication failed (401 Unauthorized): Invalid token {masked}. Check TELEGRAM_BOT_TOKEN.")
            else:
                logger.error(f"❌ Telegram getMe failed: code={err_code}, error={desc}")
            return False

        bot_username = me_data.get("result", {}).get("username", "UnknownBot")
        logger.info(f"✅ Connected to Telegram as @{bot_username} (Token: {masked})")

        # 2. Check and delete existing webhook if set
        wh_resp = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=10)
        wh_data = wh_resp.json()
        if wh_data.get("ok"):
            has_webhook = bool(wh_data.get("result", {}).get("url"))
            if has_webhook:
                logger.info("Found active webhook. Deleting webhook to enable long-polling mode...")
                del_resp = requests.post(
                    f"https://api.telegram.org/bot{token}/deleteWebhook",
                    json={"drop_pending_updates": False},
                    timeout=10
                )
                if del_resp.json().get("ok"):
                    logger.info("✅ Active webhook deleted successfully.")
                else:
                    logger.warning(f"⚠️ Could not delete webhook: {del_resp.text}")

        return True
    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error during Telegram connection check: {e}")
        return True  # Allow loop to attempt connecting

def answer_callback_query(token: str, callback_query_id: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id},
            timeout=5
        )
    except Exception as e:
        logger.debug(f"Error answering callback query: {e}")

def send_bot_reply(token: str, chat_id: int, text: str, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=10
        )
        res_data = resp.json()
        if not res_data.get("ok"):
            logger.warning(f"Reply send failed to {chat_id}: {res_data.get('description')}")
    except Exception as e:
        logger.error(f"Error sending reply to {chat_id}: {e}")

def poll_updates_loop(token: str):
    """Inner polling loop with comprehensive HTTP status and Telegram error code handling."""
    global _shutdown_requested
    offset = None

    logger.info("🤖 HackRadar Telegram Bot Polling service is active.")

    while not _shutdown_requested:
        try:
            params = {"timeout": 20}
            if offset:
                params["offset"] = offset

            resp = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params=params,
                timeout=30
            )

            # Handle HTTP-level errors
            if resp.status_code == 401:
                logger.error("❌ Telegram API 401 Unauthorized: Invalid bot token.")
                time.sleep(30)
                continue
            elif resp.status_code == 409:
                logger.warning("⚠️ Telegram API 409 Conflict: Another polling instance is active or webhook is registered. Retrying in 10s...")
                time.sleep(10)
                continue
            elif resp.status_code == 429:
                retry_after = 10
                try:
                    retry_after = resp.json().get("parameters", {}).get("retry_after", 10)
                except Exception:
                    pass
                logger.warning(f"⚠️ Telegram API 429 Too Many Requests: Rate limited. Sleeping for {retry_after}s...")
                time.sleep(retry_after)
                continue

            data = resp.json()
            if not data.get("ok"):
                err_code = data.get("error_code")
                desc = data.get("description", "Unknown error")
                logger.warning(f"⚠️ Telegram API response not ok (code={err_code}): {desc}")
                time.sleep(5)
                continue

            updates = data.get("result", [])
            for upd in updates:
                offset = upd["update_id"] + 1
                db = SessionLocal()
                try:
                    # 1. Handle Callback Queries (inline button clicks)
                    if "callback_query" in upd:
                        cq = upd["callback_query"]
                        cq_id = cq["id"]
                        chat_id = cq["message"]["chat"]["id"]
                        data_str = cq.get("data", "")
                        answer_callback_query(token, cq_id)

                        text, markup = handle_toggle_callback(db, chat_id, data_str)
                        send_bot_reply(token, chat_id, text, markup)
                        continue

                    # 2. Handle Text Messages / Commands
                    if "message" in upd and "text" in upd["message"]:
                        msg = upd["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg["text"].strip()
                        cmd = text.split()[0].lower() if text else ""
                        from_user = msg.get("from", {})

                        if cmd in ("/start", "/start@hackradarbot"):
                            reply_text, markup = handle_start(db, chat_id, from_user)
                            send_bot_reply(token, chat_id, reply_text, markup)
                        elif cmd in ("/help", "/help@hackradarbot"):
                            send_bot_reply(token, chat_id, handle_help())
                        elif cmd in ("/preferences", "/settings", "/preferences@hackradarbot"):
                            reply_text, markup = handle_preferences(db, chat_id)
                            send_bot_reply(token, chat_id, reply_text, markup)
                        elif cmd in ("/locations", "/locations@hackradarbot"):
                            reply_text, markup = handle_locations_menu(db, chat_id)
                            send_bot_reply(token, chat_id, reply_text, markup)
                        elif cmd in ("/categories", "/categories@hackradarbot"):
                            reply_text, markup = handle_categories_menu(db, chat_id)
                            send_bot_reply(token, chat_id, reply_text, markup)
                        elif cmd in ("/sources", "/sources@hackradarbot"):
                            send_bot_reply(token, chat_id, handle_sources(db))
                        elif cmd in ("/status", "/status@hackradarbot"):
                            send_bot_reply(token, chat_id, handle_status(db, chat_id))
                        elif cmd in ("/pause", "/pause@hackradarbot"):
                            send_bot_reply(token, chat_id, handle_pause(db, chat_id))
                        elif cmd in ("/resume", "/resume@hackradarbot"):
                            send_bot_reply(token, chat_id, handle_resume(db, chat_id))
                        elif cmd in ("/events", "/events@hackradarbot"):
                            send_bot_reply(token, chat_id, handle_events(db))
                        elif cmd in ("/latest", "/latest@hackradarbot"):
                            reply_text, markup = handle_latest(db)
                            send_bot_reply(token, chat_id, reply_text, markup)
                        else:
                            send_bot_reply(
                                token,
                                chat_id,
                                "Unknown command. Type /help to view available commands."
                            )

                except Exception as e:
                    logger.error(f"Error processing update: {e}", exc_info=True)
                finally:
                    db.close()

        except requests.exceptions.RequestException as e:
            if not _shutdown_requested:
                logger.warning(f"Connection error in polling: {e}. Retrying in 5s...")
                time.sleep(5)
        except Exception as e:
            if not _shutdown_requested:
                logger.error(f"Unexpected bot loop error: {e}", exc_info=True)
                time.sleep(5)

def run_bot_polling():
    """Supervisor entrypoint with signal handling and restart resilience."""
    # Register OS signals for cloud worker restarts (Render, Railway, Docker)
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not configured in environment. Bot cannot start.")
        sys.exit(1)

    logger.info("Initializing HackRadar Bot Worker...")
    is_valid = verify_and_clear_webhook(token)
    if not is_valid:
        logger.warning("Bot verification returned false. Please verify TELEGRAM_BOT_TOKEN.")

    # Outer resilience loop: if inner loop exits unexpectedly without shutdown signal, restart
    while not _shutdown_requested:
        try:
            poll_updates_loop(token)
        except Exception as e:
            if not _shutdown_requested:
                logger.error(f"Bot worker crashed: {e}. Restarting worker in 5s...", exc_info=True)
                time.sleep(5)

    logger.info("HackRadar Telegram Bot Worker stopped successfully.")

if __name__ == "__main__":
    run_bot_polling()
