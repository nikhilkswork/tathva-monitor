import json
from pathlib import Path
from app.database.session import engine, Base, SessionLocal
from app.database.crud import init_database
from app.database.schema import Hackathon, utc_now
from app.config import BASE_DIR

def setup_database():
    """Create all tables and seed default sources"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_database(db)

        # Check if known_workshops.json exists to migrate past Tathva IDs
        known_file = BASE_DIR / "known_workshops.json"
        if known_file.exists():
            try:
                with open(known_file, "r") as f:
                    known_ids = json.load(f)
                count = 0
                for wid in known_ids:
                    dedup_key = f"tathva:{wid}"
                    exists = db.query(Hackathon).filter(Hackathon.dedup_key == dedup_key).first()
                    if not exists:
                        h = Hackathon(
                            source="tathva",
                            source_event_id=str(wid),
                            dedup_key=dedup_key,
                            title=f"Tathva Workshop #{wid}",
                            url=f"https://tathva.org/workshops/{wid}",
                            status="open",
                            detected_at=utc_now(),
                            first_seen_at=utc_now(),
                            last_seen_at=utc_now(),
                        )
                        db.add(h)
                        count += 1
                if count > 0:
                    db.commit()
                    print(f"Migrated {count} existing workshop IDs from known_workshops.json")
            except Exception as e:
                print(f"Note: Error migrating known_workshops.json: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    setup_database()
    print("✅ Database initialized successfully.")
