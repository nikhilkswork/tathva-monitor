import time
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
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=10
        )
    except Exception as e:
        logger.error(f"Error sending reply: {e}")

def run_bot_polling():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not configured. Bot cannot start.")
        return

    logger.info("🤖 Starting HackRadar Telegram Bot Polling...")
    offset = None

    while True:
        try:
            params = {"timeout": 20}
            if offset:
                params["offset"] = offset

            resp = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params=params,
                timeout=30
            )
            data = resp.json()
            if not data.get("ok"):
                time.sleep(3)
                continue

            updates = data.get("result", [])
            for upd in updates:
                offset = upd["update_id"] + 1
                db = SessionLocal()
                try:
                    # 1. Handle Callback Queries (button clicks)
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
                            # Default reply
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
            logger.warning(f"Connection error in polling: {e}. Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected bot loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot_polling()
