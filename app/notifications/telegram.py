import os
from datetime import datetime, timezone
import logging
from typing import Optional, Dict, Any, List
import requests
from app.config import settings
from app.models.hackathon import HackathonEvent

logger = logging.getLogger("hackradar.notifications.telegram")

def format_hackathon_message(event: HackathonEvent) -> str:
    """Format a hackathon event into a clean, mobile-friendly Telegram alert."""
    # Dates formatting
    dates_str = "TBD"
    if event.start_datetime and event.end_datetime:
        dates_str = f"{event.start_datetime.strftime('%d %b %Y')} – {event.end_datetime.strftime('%d %b %Y')}"
    elif event.start_datetime:
        dates_str = event.start_datetime.strftime('%d %b %Y, %I:%M %p UTC')

    deadline_str = "Open / Not specified"
    if event.registration_deadline:
        deadline_str = event.registration_deadline.strftime('%d %b %Y, %I:%M %p UTC')

    # Mode
    if event.hybrid:
        mode_str = "Hybrid (Online + In-Person)"
    elif event.online:
        mode_str = "Online (Virtual)"
    else:
        mode_str = "In-Person (Offline)"

    # Categories & tags
    cats = ", ".join(event.categories) if event.categories else "General"

    # Description snippet
    desc = event.description or "No description provided."
    if len(desc) > 280:
        desc = desc[:277] + "..."

    # Team size
    team_str = None
    if event.team_size_min and event.team_size_max:
        team_str = f"{event.team_size_min}–{event.team_size_max}"
    elif event.team_size_max:
        team_str = f"Up to {event.team_size_max}"

    # Detected time
    detected_dt = event.start_datetime or datetime.now(timezone.utc)
    detected_str = detected_dt.strftime("%d %b %Y, %I:%M %p UTC")

    lines = [
        "🚨 <b>NEW HACKATHON DETECTED</b>",
        "",
        f"🏆 <b>{event.title}</b>",
        "",
        f"🏢 <b>Organizer:</b>\n{event.organizer or 'Community / Organization'}",
        "",
        f"📍 <b>Location:</b>\n{event.location or 'Global'}",
        "",
        f"🌐 <b>Mode:</b>\n{mode_str}",
        "",
        f"📅 <b>Event Dates:</b>\n{dates_str}",
        "",
        f"⏰ <b>Registration Deadline:</b>\n{deadline_str}",
    ]

    if event.prize_pool:
        lines.extend([
            "",
            f"💰 <b>Prize Pool:</b>\n{event.prize_pool}"
        ])

    if team_str:
        lines.extend([
            "",
            f"👥 <b>Team Size:</b>\n{team_str}"
        ])

    lines.extend([
        "",
        f"🏷️ <b>Categories:</b>\n{cats}",
        "",
        f"📝 <b>Description:</b>\n{desc}",
        "",
        f"🔎 <b>Source:</b>\n{event.source.capitalize()}",
        "",
        f"🕐 <b>Detected:</b>\n{detected_str}"
    ])

    if event.is_demo:
        lines.insert(1, "⚠️ <b>[DEMO EVENT — FOR TESTING ONLY]</b>")

    return "\n".join(lines)


class TelegramNotifier:
    def __init__(self, token: Optional[str] = None):
        self.token = token if token is not None else settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else None

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = False,
        reply_markup: Optional[Dict[str, Any]] = None,
        retries: int = 2
    ) -> Tuple[bool, Optional[str]]:
        """Send message via Telegram Bot API with retries"""
        if not self.token or not self.base_url:
            return False, "TELEGRAM_BOT_TOKEN is not configured"

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        last_error = None
        for attempt in range(retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=10)
                res_data = resp.json()
                if resp.status_code == 200 and res_data.get("ok"):
                    return True, None
                last_error = res_data.get("description") or f"HTTP {resp.status_code}"
                logger.warning(f"Telegram send attempt {attempt + 1} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Telegram send exception on attempt {attempt + 1}: {e}")

        return False, last_error

    def send_hackathon_alert(
        self,
        chat_id: int | str,
        event: HackathonEvent
    ) -> Tuple[bool, Optional[str]]:
        """Send formatted hackathon alert with interactive buttons"""
        msg = format_hackathon_message(event)

        # Inline keyboard buttons
        inline_keyboard = []
        row = []
        reg_url = event.registration_url or event.url
        if reg_url:
            row.append({"text": "🚀 Register Now", "url": reg_url})
        if event.url and event.url != reg_url:
            row.append({"text": "🔍 Details", "url": event.url})
        if row:
            inline_keyboard.append(row)

        reply_markup = {"inline_keyboard": inline_keyboard} if inline_keyboard else None

        return self.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

# Global singleton
telegram_notifier = TelegramNotifier()
