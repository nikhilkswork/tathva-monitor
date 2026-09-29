import json
import logging
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.database.crud import get_or_create_user
from app.database.schema import User, UserPreference, Hackathon, Source
from app.models.preferences import DEFAULT_LOCATIONS, DEFAULT_CATEGORIES, DEFAULT_MODES
from app.models.hackathon import HackathonEvent

logger = logging.getLogger("hackradar.bot.handlers")

def handle_start(db: Session, chat_id: int, user_data: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
    user, is_new = get_or_create_user(
        db=db,
        telegram_id=chat_id,
        username=user_data.get("username"),
        first_name=user_data.get("first_name"),
        last_name=user_data.get("last_name")
    )
    user.is_active = True
    db.commit()

    text = (
        "👋 <b>Welcome to HackRadar 🚨</b>\n\n"
        "I monitor trusted hackathon sources (Devfolio, Unstop, Devpost, MLH, Tathva, etc.) "
        "and notify you instantly when new opportunities matching your preferences appear.\n\n"
        "Let’s configure your alert preferences!\n\n"
        "<b>Available Commands:</b>\n"
        "• /preferences — View your active filters\n"
        "• /locations — Choose target locations\n"
        "• /categories — Select tech domains (AI/ML, Web, etc.)\n"
        "• /status — Check bot and monitoring status\n"
        "• /events — View recent hackathons\n"
        "• /latest — View the newest hackathon\n"
        "• /pause — Pause notifications\n"
        "• /resume — Resume notifications\n"
        "• /help — Full commands guide"
    )

    inline_keyboard = [
        [
            {"text": "📍 Configure Locations", "callback_data": "menu_locations"},
            {"text": "🏷️ Configure Categories", "callback_data": "menu_categories"}
        ],
        [
            {"text": "⚙️ View Preferences", "callback_data": "view_preferences"},
            {"text": "🔥 Latest Hackathons", "callback_data": "view_latest"}
        ]
    ]

    return text, {"inline_keyboard": inline_keyboard}


def handle_help() -> str:
    return (
        "🤖 <b>HackRadar Bot Guide</b>\n\n"
        "<b>Commands:</b>\n"
        "• <code>/preferences</code> — Display your current filter settings\n"
        "• <code>/locations</code> — Select target regions (India, Kerala, Online, etc.)\n"
        "• <code>/categories</code> — Select domains (AI/ML, Web, Mobile, etc.)\n"
        "• <code>/sources</code> — Check monitored platform status\n"
        "• <code>/status</code> — Current alert status and statistics\n"
        "• <code>/pause</code> — Temporarily stop receiving alerts\n"
        "• <code>/resume</code> — Unpause alert notifications\n"
        "• <code>/events</code> — Browse recently discovered events\n"
        "• <code>/latest</code> — Show the most recent event\n"
        "• <code>/settings</code> — Interactive settings dashboard\n\n"
        "💡 <i>Tip: Use the buttons to toggle preferences on and off interactively!</i>"
    )


def handle_preferences(db: Session, chat_id: int) -> Tuple[str, Optional[Dict[str, Any]]]:
    user, _ = get_or_create_user(db, chat_id)
    pref = user.preferences

    locs = ", ".join(pref.locations) if pref.locations else "Anywhere"
    cats = ", ".join(pref.categories) if pref.categories else "General"
    modes = ", ".join(pref.modes) if pref.modes else "All"
    status_str = "🟢 Active (Receiving alerts)" if user.is_active else "🔴 Paused"
    prize_str = f"₹{pref.min_prize_pool:,.0f}" if pref.min_prize_pool > 0 else "No minimum"

    text = (
        "⚙️ <b>Your HackRadar Preferences:</b>\n\n"
        f"• <b>Status:</b> {status_str}\n"
        f"• <b>Locations:</b> {locs}\n"
        f"• <b>Categories:</b> {cats}\n"
        f"• <b>Modes:</b> {modes}\n"
        f"• <b>Min Prize:</b> {prize_str}\n"
    )

    inline_keyboard = [
        [
            {"text": "📍 Locations", "callback_data": "menu_locations"},
            {"text": "🏷️ Categories", "callback_data": "menu_categories"}
        ],
        [
            {"text": "🌐 Modes", "callback_data": "menu_modes"},
            {"text": "🔴 Pause" if user.is_active else "🟢 Resume", "callback_data": f"toggle_active:{0 if user.is_active else 1}"}
        ]
    ]

    return text, {"inline_keyboard": inline_keyboard}


def handle_locations_menu(db: Session, chat_id: int) -> Tuple[str, Dict[str, Any]]:
    user, _ = get_or_create_user(db, chat_id)
    pref = user.preferences
    current_locs = pref.locations

    keyboard = []
    # Build 2-column buttons
    row = []
    for loc in DEFAULT_LOCATIONS:
        is_selected = loc in current_locs
        label = f"✅ {loc}" if is_selected else loc
        row.append({"text": label, "callback_data": f"tog_loc:{loc}"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([{"text": "« Back to Preferences", "callback_data": "view_preferences"}])

    text = "📍 <b>Select Locations:</b>\nTap an option to toggle it on or off."
    return text, {"inline_keyboard": keyboard}


def handle_categories_menu(db: Session, chat_id: int) -> Tuple[str, Dict[str, Any]]:
    user, _ = get_or_create_user(db, chat_id)
    pref = user.preferences
    current_cats = pref.categories

    keyboard = []
    row = []
    for cat in DEFAULT_CATEGORIES:
        is_selected = cat in current_cats
        label = f"✅ {cat}" if is_selected else cat
        row.append({"text": label, "callback_data": f"tog_cat:{cat}"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([{"text": "« Back to Preferences", "callback_data": "view_preferences"}])

    text = "🏷️ <b>Select Categories:</b>\nTap a domain to toggle alerts for it."
    return text, {"inline_keyboard": keyboard}


def handle_modes_menu(db: Session, chat_id: int) -> Tuple[str, Dict[str, Any]]:
    user, _ = get_or_create_user(db, chat_id)
    pref = user.preferences
    current_modes = pref.modes

    keyboard = []
    row = []
    for mode in DEFAULT_MODES:
        is_selected = mode in current_modes
        label = f"✅ {mode}" if is_selected else mode
        row.append({"text": label, "callback_data": f"tog_mode:{mode}"})
    keyboard.append(row)
    keyboard.append([{"text": "« Back to Preferences", "callback_data": "view_preferences"}])

    text = "🌐 <b>Select Event Modes:</b>\nChoose Online, Offline, or Hybrid."
    return text, {"inline_keyboard": keyboard}


def handle_toggle_callback(db: Session, chat_id: int, callback_data: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    user, _ = get_or_create_user(db, chat_id)
    pref = user.preferences

    if callback_data.startswith("tog_loc:"):
        loc = callback_data.split("tog_loc:", 1)[1]
        locs = list(pref.locations)
        if loc == "Anywhere":
            locs = ["Anywhere"]
        else:
            if "Anywhere" in locs:
                locs.remove("Anywhere")
            if loc in locs:
                locs.remove(loc)
            else:
                locs.append(loc)
            if not locs:
                locs = ["Anywhere"]
        pref.locations = locs
        db.commit()
        return handle_locations_menu(db, chat_id)

    elif callback_data.startswith("tog_cat:"):
        cat = callback_data.split("tog_cat:", 1)[1]
        cats = list(pref.categories)
        if cat == "General":
            cats = ["General"]
        else:
            if "General" in cats:
                cats.remove("General")
            if cat in cats:
                cats.remove(cat)
            else:
                cats.append(cat)
            if not cats:
                cats = ["General"]
        pref.categories = cats
        db.commit()
        return handle_categories_menu(db, chat_id)

    elif callback_data.startswith("tog_mode:"):
        mode = callback_data.split("tog_mode:", 1)[1]
        modes = list(pref.modes)
        if mode in modes:
            if len(modes) > 1:
                modes.remove(mode)
        else:
            modes.append(mode)
        pref.modes = modes
        db.commit()
        return handle_modes_menu(db, chat_id)

    elif callback_data.startswith("toggle_active:"):
        val = callback_data.split("toggle_active:", 1)[1]
        user.is_active = (val == "1")
        db.commit()
        return handle_preferences(db, chat_id)

    elif callback_data == "view_preferences":
        return handle_preferences(db, chat_id)
    elif callback_data == "menu_locations":
        return handle_locations_menu(db, chat_id)
    elif callback_data == "menu_categories":
        return handle_categories_menu(db, chat_id)
    elif callback_data == "menu_modes":
        return handle_modes_menu(db, chat_id)
    elif callback_data == "view_latest":
        return handle_latest(db)

    return "Updated", None


def handle_sources(db: Session) -> str:
    sources = db.query(Source).all()
    lines = ["📡 <b>HackRadar Monitored Sources:</b>\n"]
    for s in sources:
        status_icon = "🟢" if s.enabled and not s.last_error else ("🟡" if s.enabled else "⚪")
        err_str = f"\n   ⚠️ <i>{s.last_error}</i>" if s.last_error else ""
        lines.append(
            f"{status_icon} <b>{s.display_name}</b> ({s.name})\n"
            f"   Status: {'Enabled' if s.enabled else 'Disabled'} | Discovered: {s.events_discovered}{err_str}"
        )
    return "\n\n".join(lines)


def handle_status(db: Session, chat_id: int) -> str:
    user, _ = get_or_create_user(db, chat_id)
    total_events = db.query(Hackathon).count()
    enabled_sources = db.query(Source).filter(Source.enabled == True).count()
    status_icon = "🟢 Active" if user.is_active else "🔴 Paused"

    return (
        f"📊 <b>HackRadar Status</b>\n\n"
        f"• <b>Alerts:</b> {status_icon}\n"
        f"• <b>Active Sources:</b> {enabled_sources}\n"
        f"• <b>Total Events Tracked:</b> {total_events}\n"
        f"• <b>Active Locations:</b> {', '.join(user.preferences.locations)}\n"
        f"• <b>Active Categories:</b> {', '.join(user.preferences.categories)}"
    )


def handle_pause(db: Session, chat_id: int) -> str:
    user, _ = get_or_create_user(db, chat_id)
    user.is_active = False
    db.commit()
    return "⏸️ <b>Alerts Paused.</b> You will not receive new hackathon notifications until you run /resume."


def handle_resume(db: Session, chat_id: int) -> str:
    user, _ = get_or_create_user(db, chat_id)
    user.is_active = True
    db.commit()
    return "▶️ <b>Alerts Resumed!</b> You will now receive notifications for newly discovered hackathons."


def handle_events(db: Session, limit: int = 5) -> str:
    events = db.query(Hackathon).order_by(Hackathon.detected_at.desc()).limit(limit).all()
    if not events:
        return "ℹ️ No hackathons found in database yet. Run the monitor to populate!"

    lines = [f"🔥 <b>Latest {len(events)} Hackathons:</b>\n"]
    for ev in events:
        mode_label = "Online" if ev.online else (ev.location or "Offline")
        prize_label = f" | 💰 {ev.prize_pool}" if ev.prize_pool else ""
        lines.append(
            f"🏆 <b><a href='{ev.url}'>{ev.title}</a></b>\n"
            f"📍 {mode_label}{prize_label}\n"
            f"🔎 {ev.source.capitalize()}"
        )
    return "\n\n".join(lines)


def handle_latest(db: Session) -> Tuple[str, Optional[Dict[str, Any]]]:
    ev = db.query(Hackathon).order_by(Hackathon.detected_at.desc()).first()
    if not ev:
        return "ℹ️ No hackathons discovered yet.", None

    from app.notifications.telegram import format_hackathon_message
    from app.models.hackathon import HackathonEvent
    event_model = HackathonEvent(
        source=ev.source,
        source_event_id=ev.source_event_id,
        title=ev.title,
        organizer=ev.organizer,
        description=ev.description,
        url=ev.url,
        registration_url=ev.registration_url,
        image_url=ev.image_url,
        location=ev.location,
        country=ev.country,
        state=ev.state,
        city=ev.city,
        online=ev.online,
        hybrid=ev.hybrid,
        start_datetime=ev.start_datetime,
        end_datetime=ev.end_datetime,
        registration_deadline=ev.registration_deadline,
        prize_pool=ev.prize_pool,
        prize_pool_amount=ev.prize_pool_amount,
        currency=ev.currency,
        team_size_min=ev.team_size_min,
        team_size_max=ev.team_size_max,
        eligibility=ev.eligibility,
        categories=ev.categories,
        technologies=ev.technologies,
        tags=ev.tags,
        status=ev.status,
        is_demo=ev.is_demo
    )
    msg = format_hackathon_message(event_model)
    buttons = [[{"text": "🚀 Register", "url": ev.registration_url or ev.url}]]
    return msg, {"inline_keyboard": buttons}
