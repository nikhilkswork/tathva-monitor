import sys
import logging
from app.database.init_db import setup_database
from app.database.session import SessionLocal
from app.monitoring.runner import run_monitoring_cycle

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("hackradar.cli")

def main():
    print("=" * 50)
    print("  🚨 HackRadar Hackathon Monitor")
    print("=" * 50)

    # Ensure DB tables and sources exist
    setup_database()

    db = SessionLocal()
    try:
        results = run_monitoring_cycle(db)

        print("\n" + "=" * 50)
        print("  Summary Results")
        print("=" * 50)
        for s_name, data in results["sources"].items():
            if data["status"] == "success":
                icon = "✓"
                details = f"{data['events_found']} events ({data['new_events']} new)"
            else:
                icon = "✗"
                details = f"ERROR ({data['error'][:40]}...)"
            print(f"  {s_name.capitalize():<15} {icon}  {details}")

        print("-" * 50)
        print(f"  Total Events Found:   {results['total_events_found']}")
        print(f"  Genuinely New Events: {results['new_events_found']}")
        print(f"  Notifications Sent:   {results['notifications_sent']}")
        print(f"  Sources Succeeded:    {results['sources_succeeded']}/{results['sources_checked']}")
        print(f"  Status:               {results['status'].upper()}")
        print("=" * 50)

    except Exception as e:
        logger.error(f"Fatal monitor run failure: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
