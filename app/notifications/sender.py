import logging
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.config import settings
from app.database.schema import User, Hackathon, Notification, utc_now
from app.database.crud import get_or_create_user, record_notification, log_error
from app.models.hackathon import HackathonEvent
from app.matching.matcher import match_user_preference
from app.notifications.telegram import telegram_notifier

logger = logging.getLogger("hackradar.notifications.dispatcher")

def dispatch_hackathon_notifications(
    db: Session,
    hackathon_obj: Hackathon,
    event: HackathonEvent
) -> int:
    """
    Match a newly discovered hackathon against all registered active users
    and send Telegram notifications. Returns count of notifications successfully sent.
    """
    # If no users registered yet, seed default TELEGRAM_CHAT_ID from .env if present
    user_count = db.query(User).count()
    if user_count == 0 and settings.TELEGRAM_CHAT_ID:
        try:
            chat_id_int = int(settings.TELEGRAM_CHAT_ID)
            get_or_create_user(
                db=db,
                telegram_id=chat_id_int,
                username="default_admin_chat",
                first_name="Default Admin"
            )
        except Exception as e:
            logger.warning(f"Could not register default TELEGRAM_CHAT_ID: {e}")

    active_users = db.query(User).filter(User.is_active == True).all()
    if not active_users:
        logger.info("No active Telegram users found for notification.")
        return 0

    sent_count = 0
    for user in active_users:
        # Check if already notified for this event
        already_notified = db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.hackathon_id == hackathon_obj.id,
            Notification.status == "sent"
        ).first()

        if already_notified:
            continue

        # Evaluate preference matching
        is_match, reasons = match_user_preference(user, event)
        if not is_match:
            logger.debug(f"User {user.telegram_id} skipped: {reasons}")
            continue

        logger.info(f"User {user.telegram_id} matches '{event.title}' ({', '.join(reasons)})")

        # Send Telegram notification
        success, error_msg = telegram_notifier.send_hackathon_alert(
            chat_id=user.telegram_id,
            event=event
        )

        status_str = "sent" if success else "failed"
        record_notification(
            db=db,
            user_id=user.id,
            hackathon_id=hackathon_obj.id,
            channel="telegram",
            status=status_str,
            error_message=error_msg
        )

        if success:
            sent_count += 1
            logger.info(f"✅ Notification sent to Telegram user {user.telegram_id}")
        else:
            logger.error(f"❌ Failed to notify Telegram user {user.telegram_id}: {error_msg}")
            log_error(
                db=db,
                component="telegram_dispatcher",
                error_type="TelegramDeliveryError",
                message=f"Failed to deliver alert to user {user.telegram_id}: {error_msg}",
                source=event.source
            )

    return sent_count
