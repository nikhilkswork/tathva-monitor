from datetime import datetime, timezone
import json
import logging
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.database.schema import (
    User, UserPreference, Source, Hackathon, MonitorRun, Notification, EventChange, ErrorLog, utc_now
)

logger = logging.getLogger("hackradar.crud")

# Default source configurations
DEFAULT_SOURCES = [
    {
        "name": "tathva",
        "display_name": "Tathva (NIT Calicut)",
        "base_url": "https://api.tathva.org/api/events/all",
        "source_type": "api",
        "enabled": True,
        "trust_status": "trusted",
        "parser_class": "TathvaSourceAdapter",
    },
    {
        "name": "devfolio",
        "display_name": "Devfolio",
        "base_url": "https://api.devfolio.co/api/hackathons",
        "source_type": "api",
        "enabled": True,
        "trust_status": "trusted",
        "parser_class": "DevfolioSourceAdapter",
    },
    {
        "name": "unstop",
        "display_name": "Unstop",
        "base_url": "https://unstop.com/api/public/opportunity/search-result",
        "source_type": "api",
        "enabled": True,
        "trust_status": "trusted",
        "parser_class": "UnstopSourceAdapter",
    },
    {
        "name": "devpost",
        "display_name": "Devpost",
        "base_url": "https://devpost.com/api/hackathons",
        "source_type": "api",
        "enabled": True,
        "trust_status": "trusted",
        "parser_class": "DevpostSourceAdapter",
    },
    {
        "name": "mlh",
        "display_name": "Major League Hacking (MLH)",
        "base_url": "https://mlh.io/seasons/2026/events",
        "source_type": "html",
        "enabled": True,
        "trust_status": "trusted",
        "parser_class": "MLHSourceAdapter",
    },
    {
        "name": "hack2skill",
        "display_name": "Hack2skill",
        "base_url": "https://hack2skill.com",
        "source_type": "scraper",
        "enabled": False,  # Disabled by default due to dynamic reCAPTCHA SPA
        "trust_status": "degraded",
        "parser_class": "Hack2SkillSourceAdapter",
    },
    {
        "name": "kaggle",
        "display_name": "Kaggle Competitions",
        "base_url": "https://www.kaggle.com/api/v1/competitions/list",
        "source_type": "api",
        "enabled": False,  # Requires Kaggle API token
        "trust_status": "needs_auth",
        "parser_class": "KaggleSourceAdapter",
    },
    {
        "name": "generic",
        "display_name": "Generic Web Source",
        "base_url": "https://example.com/events",
        "source_type": "generic",
        "enabled": True,
        "trust_status": "trusted",
        "parser_class": "GenericSourceAdapter",
    }
]


def init_database(db: Session):
    """Seed initial sources if not present"""
    for src in DEFAULT_SOURCES:
        existing = db.query(Source).filter(Source.name == src["name"]).first()
        if not existing:
            source_obj = Source(
                name=src["name"],
                display_name=src["display_name"],
                base_url=src["base_url"],
                source_type=src["source_type"],
                enabled=src["enabled"],
                trust_status=src["trust_status"],
                parser_class=src["parser_class"],
            )
            db.add(source_obj)
    db.commit()


def get_or_create_user(
    db: Session,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> Tuple[User, bool]:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        # Update details if changed
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if last_name and user.last_name != last_name:
            user.last_name = last_name
        db.commit()
        return user, False

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Create default preferences
    pref = UserPreference(
        user_id=user.id,
        locations_json=json.dumps(["Anywhere"]),
        categories_json=json.dumps(["General"]),
        modes_json=json.dumps(["Online", "Offline", "Hybrid"]),
        min_prize_pool=0.0,
        notify_updates=False
    )
    db.add(pref)
    db.commit()
    db.refresh(user)
    return user, True


def get_active_users(db: Session) -> List[User]:
    return db.query(User).filter(User.is_active == True).all()


def upsert_hackathon(
    db: Session,
    event_data: Dict[str, Any]
) -> Tuple[Hackathon, bool, List[str]]:
    """
    Upsert hackathon by dedup_key.
    Returns: (hackathon, is_new, list_of_changed_fields)
    """
    dedup_key = event_data["dedup_key"]
    existing = db.query(Hackathon).filter(Hackathon.dedup_key == dedup_key).first()

    now = utc_now()
    if not existing:
        hackathon = Hackathon(
            source=event_data["source"],
            source_event_id=str(event_data["source_event_id"]),
            dedup_key=dedup_key,
            title=event_data["title"],
            organizer=event_data.get("organizer"),
            description=event_data.get("description"),
            url=event_data["url"],
            registration_url=event_data.get("registration_url") or event_data["url"],
            image_url=event_data.get("image_url"),
            location=event_data.get("location"),
            country=event_data.get("country"),
            state=event_data.get("state"),
            city=event_data.get("city"),
            online=event_data.get("online", False),
            hybrid=event_data.get("hybrid", False),
            start_datetime=event_data.get("start_datetime"),
            end_datetime=event_data.get("end_datetime"),
            registration_deadline=event_data.get("registration_deadline"),
            prize_pool=event_data.get("prize_pool"),
            prize_pool_amount=event_data.get("prize_pool_amount"),
            currency=event_data.get("currency"),
            team_size_min=event_data.get("team_size_min"),
            team_size_max=event_data.get("team_size_max"),
            eligibility=event_data.get("eligibility"),
            categories_json=json.dumps(event_data.get("categories", [])),
            technologies_json=json.dumps(event_data.get("technologies", [])),
            tags_json=json.dumps(event_data.get("tags", [])),
            detected_at=now,
            first_seen_at=now,
            last_seen_at=now,
            status=event_data.get("status", "open"),
            is_demo=event_data.get("is_demo", False),
            raw_source_data=json.dumps(event_data.get("raw_source_data", {}))
        )
        db.add(hackathon)
        db.flush()

        change = EventChange(
            hackathon_id=hackathon.id,
            change_type="created",
            field_name=None,
            old_value=None,
            new_value="Created event",
            changed_at=now
        )
        db.add(change)
        db.commit()
        return hackathon, True, []

    # Existing event: update last_seen_at and check for changes
    existing.last_seen_at = now
    changed_fields = []

    fields_to_track = [
        ("title", event_data.get("title")),
        ("registration_deadline", event_data.get("registration_deadline")),
        ("status", event_data.get("status")),
        ("prize_pool", event_data.get("prize_pool")),
        ("start_datetime", event_data.get("start_datetime")),
        ("end_datetime", event_data.get("end_datetime")),
    ]

    for field_name, new_val in fields_to_track:
        if new_val is not None:
            old_val = getattr(existing, field_name)
            differs = False
            if old_val is None:
                differs = True
            elif isinstance(old_val, datetime) and isinstance(new_val, datetime):
                o = old_val.replace(tzinfo=timezone.utc) if old_val.tzinfo is None else old_val.astimezone(timezone.utc)
                n = new_val.replace(tzinfo=timezone.utc) if new_val.tzinfo is None else new_val.astimezone(timezone.utc)
                differs = (o != n)
            else:
                differs = (old_val != new_val)

            if differs:
                setattr(existing, field_name, new_val)
                changed_fields.append(field_name)
                change = EventChange(
                    hackathon_id=existing.id,
                    change_type="deadline_changed" if field_name == "registration_deadline" else "updated",
                    field_name=field_name,
                    old_value=str(old_val),
                    new_value=str(new_val),
                    changed_at=now
                )
                db.add(change)

    # Update description / images / tags if provided
    if event_data.get("description"):
        existing.description = event_data["description"]
    if event_data.get("image_url"):
        existing.image_url = event_data["image_url"]
    if event_data.get("categories"):
        existing.categories_json = json.dumps(event_data["categories"])
    if event_data.get("tags"):
        existing.tags_json = json.dumps(event_data["tags"])

    db.commit()
    return existing, False, changed_fields


def record_notification(
    db: Session,
    user_id: int,
    hackathon_id: int,
    channel: str = "telegram",
    status: str = "sent",
    error_message: Optional[str] = None
):
    notif = Notification(
        user_id=user_id,
        hackathon_id=hackathon_id,
        channel=channel,
        sent_at=utc_now(),
        status=status,
        error_message=error_message
    )
    db.add(notif)
    db.commit()


def log_error(
    db: Session,
    component: str,
    error_type: str,
    message: str,
    source: Optional[str] = None,
    traceback: Optional[str] = None
):
    err = ErrorLog(
        source=source,
        component=component,
        error_type=error_type,
        message=message,
        traceback=traceback,
        created_at=utc_now()
    )
    db.add(err)
    db.commit()


def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    total_events = db.query(func.count(Hackathon.id)).scalar() or 0
    active_sources = db.query(func.count(Source.id)).filter(Source.enabled == True).scalar() or 0
    failed_sources = db.query(func.count(Source.id)).filter(Source.last_error != None).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_notifications = db.query(func.count(Notification.id)).filter(Notification.status == "sent").scalar() or 0

    # Events detected today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    new_today = db.query(func.count(Hackathon.id)).filter(Hackathon.detected_at >= today_start).scalar() or 0

    last_run = db.query(MonitorRun).order_by(desc(MonitorRun.started_at)).first()

    return {
        "total_events": total_events,
        "new_today": new_today,
        "active_sources": active_sources,
        "failed_sources": failed_sources,
        "total_users": total_users,
        "total_notifications": total_notifications,
        "last_run": {
            "started_at": last_run.started_at.isoformat() if last_run else None,
            "status": last_run.status if last_run else None,
            "new_events": last_run.new_events_found if last_run else 0,
            "total_events": last_run.total_events_found if last_run else 0,
        } if last_run else None
    }
