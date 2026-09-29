from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.session import get_db
from app.database.schema import Hackathon, Source, MonitorRun, Notification, ErrorLog, User
from app.database.crud import get_dashboard_stats
from app.monitoring.runner import run_monitoring_cycle
from app.sources.registry import source_registry
from app.notifications.telegram import telegram_notifier
from app.models.hackathon import HackathonEvent
from app.config import settings

api_router = APIRouter(prefix="/api")

@api_router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Summary statistics for admin dashboard"""
    return get_dashboard_stats(db)

@api_router.get("/events")
def list_events(
    db: Session = Depends(get_db),
    source: Optional[str] = None,
    mode: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    query = db.query(Hackathon)
    if source:
        query = query.filter(Hackathon.source == source.lower())
    if mode:
        if mode.lower() == "online":
            query = query.filter(Hackathon.online == True)
        elif mode.lower() == "offline":
            query = query.filter(Hackathon.online == False)
        elif mode.lower() == "hybrid":
            query = query.filter(Hackathon.hybrid == True)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Hackathon.title.ilike(search_filter)) |
            (Hackathon.organizer.ilike(search_filter)) |
            (Hackathon.location.ilike(search_filter))
        )

    total = query.count()
    items = query.order_by(desc(Hackathon.detected_at)).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": ev.id,
                "source": ev.source,
                "title": ev.title,
                "organizer": ev.organizer,
                "url": ev.url,
                "registration_url": ev.registration_url,
                "image_url": ev.image_url,
                "location": ev.location,
                "online": ev.online,
                "hybrid": ev.hybrid,
                "start_datetime": ev.start_datetime.isoformat() if ev.start_datetime else None,
                "end_datetime": ev.end_datetime.isoformat() if ev.end_datetime else None,
                "registration_deadline": ev.registration_deadline.isoformat() if ev.registration_deadline else None,
                "prize_pool": ev.prize_pool,
                "currency": ev.currency,
                "categories": ev.categories,
                "tags": ev.tags,
                "status": ev.status,
                "is_demo": ev.is_demo,
                "detected_at": ev.detected_at.isoformat() if ev.detected_at else None,
            }
            for ev in items
        ]
    }

@api_router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    ev = db.query(Hackathon).filter(Hackathon.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    return {
        "id": ev.id,
        "source": ev.source,
        "source_event_id": ev.source_event_id,
        "dedup_key": ev.dedup_key,
        "title": ev.title,
        "organizer": ev.organizer,
        "description": ev.description,
        "url": ev.url,
        "registration_url": ev.registration_url,
        "image_url": ev.image_url,
        "location": ev.location,
        "country": ev.country,
        "state": ev.state,
        "city": ev.city,
        "online": ev.online,
        "hybrid": ev.hybrid,
        "start_datetime": ev.start_datetime.isoformat() if ev.start_datetime else None,
        "end_datetime": ev.end_datetime.isoformat() if ev.end_datetime else None,
        "registration_deadline": ev.registration_deadline.isoformat() if ev.registration_deadline else None,
        "prize_pool": ev.prize_pool,
        "categories": ev.categories,
        "technologies": ev.technologies,
        "tags": ev.tags,
        "status": ev.status,
        "detected_at": ev.detected_at.isoformat() if ev.detected_at else None,
        "changes": [
            {
                "change_type": c.change_type,
                "field_name": c.field_name,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "changed_at": c.changed_at.isoformat()
            }
            for c in ev.changes
        ]
    }

@api_router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "display_name": s.display_name,
            "base_url": s.base_url,
            "source_type": s.source_type,
            "enabled": s.enabled,
            "trust_status": s.trust_status,
            "events_discovered": s.events_discovered,
            "last_checked_at": s.last_checked_at.isoformat() if s.last_checked_at else None,
            "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
            "last_error": s.last_error,
        }
        for s in sources
    ]

@api_router.patch("/sources/{source_id}")
def update_source(source_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    s = db.query(Source).filter(Source.id == source_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Source not found")
    if "enabled" in payload:
        s.enabled = bool(payload["enabled"])
    if "base_url" in payload and payload["base_url"]:
        s.base_url = str(payload["base_url"])
    db.commit()
    return {"message": "Source updated successfully", "enabled": s.enabled}

@api_router.get("/monitor/runs")
def list_monitor_runs(db: Session = Depends(get_db), limit: int = 15):
    runs = db.query(MonitorRun).order_by(desc(MonitorRun.started_at)).limit(limit).all()
    return [
        {
            "id": r.id,
            "started_at": r.started_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "status": r.status,
            "sources_checked": r.sources_checked,
            "sources_succeeded": r.sources_succeeded,
            "sources_failed": r.sources_failed,
            "total_events_found": r.total_events_found,
            "new_events_found": r.new_events_found,
            "notifications_sent": r.notifications_sent,
            "summary": r.summary,
            "error_message": r.error_message,
        }
        for r in runs
    ]

@api_router.post("/monitor/trigger")
def trigger_monitor_run(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger an immediate monitoring run"""
    results = run_monitoring_cycle(db)
    return {
        "message": "Monitoring cycle completed",
        "results": results
    }

@api_router.get("/logs")
def get_logs(db: Session = Depends(get_db), limit: int = 30):
    logs = db.query(ErrorLog).order_by(desc(ErrorLog.created_at)).limit(limit).all()
    return [
        {
            "id": l.id,
            "source": l.source,
            "component": l.component,
            "error_type": l.error_type,
            "message": l.message,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]

@api_router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "telegram_id": u.telegram_id,
            "username": u.username,
            "first_name": u.first_name,
            "is_active": u.is_active,
            "preferences": {
                "locations": u.preferences.locations if u.preferences else [],
                "categories": u.preferences.categories if u.preferences else [],
                "modes": u.preferences.modes if u.preferences else [],
                "min_prize_pool": u.preferences.min_prize_pool if u.preferences else 0,
            } if u.preferences else None,
            "notifications_received": len(u.notifications)
        }
        for u in users
    ]

@api_router.post("/notifications/test")
def trigger_test_notification():
    """Send a test notification to the configured default Telegram chat"""
    chat_id = settings.TELEGRAM_CHAT_ID
    if not chat_id:
        raise HTTPException(status_code=400, detail="TELEGRAM_CHAT_ID is not configured in environment")

    test_event = HackathonEvent(
        source="test",
        source_event_id="test-ping",
        title="[TEST ALERT] HackRadar System Verification",
        organizer="HackRadar Core Engine",
        description="This is a test notification verifying that the Telegram Bot alert delivery pipeline is active and functioning properly.",
        url="https://github.com/nikhilkswork/tathva-monitor",
        registration_url="https://github.com/nikhilkswork/tathva-monitor",
        location="Global Cloud / Telegram API",
        online=True,
        prize_pool="₹0 (Test)",
        categories=["General", "AI / ML"],
        tags=["SystemTest", "HackRadar"],
        status="open",
        is_demo=True
    )

    success, err = telegram_notifier.send_hackathon_alert(chat_id=chat_id, event=test_event)
    if not success:
        raise HTTPException(status_code=500, detail=f"Telegram delivery failed: {err}")

    return {"message": "Test notification sent successfully to Telegram!", "chat_id": chat_id}
