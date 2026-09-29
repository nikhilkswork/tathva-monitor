from datetime import datetime, timezone
import time
import logging
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.database.schema import Source, Hackathon, MonitorRun, utc_now
from app.database.crud import upsert_hackathon, log_error
from app.sources.registry import source_registry
from app.notifications.sender import dispatch_hackathon_notifications
from app.models.hackathon import HackathonEvent

logger = logging.getLogger("hackradar.monitor")

def run_monitoring_cycle(db: Session, force_demo: bool = False) -> Dict[str, Any]:
    """
    Execute a full monitoring run across all enabled sources.
    Per-source failures are isolated and do not prevent other sources from completing.
    """
    start_time = utc_now()
    logger.info(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}] HackRadar Monitor started")

    # Record run in DB
    run_record = MonitorRun(
        started_at=start_time,
        status="running",
    )
    db.add(run_record)
    db.commit()

    enabled_adapters = source_registry.get_enabled_adapters(db)
    
    source_results = {}
    total_events_found = 0
    new_events_found = 0
    notifications_sent = 0
    sources_succeeded = 0
    sources_failed = 0

    for db_source, adapter in enabled_adapters:
        s_name = db_source.name
        t0 = time.time()
        logger.info(f"Checking source: {db_source.display_name} ({s_name})...")

        try:
            raw_events = adapter.fetch_events()
            parsed_events: List[HackathonEvent] = []
            
            for item in raw_events:
                try:
                    ev = adapter.normalize_event(item)
                    if ev and ev.title:
                        parsed_events.append(ev)
                except Exception as parse_err:
                    logger.warning(f"[{s_name}] Error parsing individual event: {parse_err}")

            event_count = len(parsed_events)
            total_events_found += event_count
            db_source.events_discovered = (db_source.events_discovered or 0) + event_count
            db_source.last_checked_at = utc_now()
            db_source.last_success_at = utc_now()
            db_source.last_error = None
            sources_succeeded += 1

            source_new_count = 0
            # Database upsert & new event detection
            for ev in parsed_events:
                hackathon_obj, is_new, changed_fields = upsert_hackathon(db, ev.to_dict())
                if is_new:
                    source_new_count += 1
                    new_events_found += 1
                    # Dispatch Telegram notifications for new event
                    notifs = dispatch_hackathon_notifications(db, hackathon_obj, ev)
                    notifications_sent += notifs

            duration = time.time() - t0
            source_results[s_name] = {
                "status": "success",
                "events_found": event_count,
                "new_events": source_new_count,
                "duration_sec": round(duration, 2),
                "error": None
            }
            logger.info(f"[{s_name}] ✓ {event_count} events ({source_new_count} new) in {duration:.2f}s")

        except Exception as e:
            sources_failed += 1
            duration = time.time() - t0
            error_msg = str(e)
            db_source.last_checked_at = utc_now()
            db_source.last_error = error_msg
            logger.error(f"[{s_name}] ❌ ERROR: {error_msg}")
            
            log_error(
                db=db,
                source=s_name,
                component="monitor_runner",
                error_type="SourceScrapeError",
                message=error_msg
            )
            
            source_results[s_name] = {
                "status": "error",
                "events_found": 0,
                "new_events": 0,
                "duration_sec": round(duration, 2),
                "error": error_msg
            }

    completed_time = utc_now()
    overall_status = "success"
    if sources_failed > 0:
        overall_status = "partial_failure" if sources_succeeded > 0 else "failed"

    # Update run record
    run_record.completed_at = completed_time
    run_record.status = overall_status
    run_record.sources_checked = len(enabled_adapters)
    run_record.sources_succeeded = sources_succeeded
    run_record.sources_failed = sources_failed
    run_record.total_events_found = total_events_found
    run_record.new_events_found = new_events_found
    run_record.notifications_sent = notifications_sent
    run_record.summary = source_results
    db.commit()

    summary_data = {
        "status": overall_status,
        "started_at": start_time.isoformat(),
        "completed_at": completed_time.isoformat(),
        "sources_checked": len(enabled_adapters),
        "sources_succeeded": sources_succeeded,
        "sources_failed": sources_failed,
        "total_events_found": total_events_found,
        "new_events_found": new_events_found,
        "notifications_sent": notifications_sent,
        "sources": source_results
    }

    return summary_data
