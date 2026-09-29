import random
import uuid
from datetime import datetime, timezone, timedelta
from app.database.session import SessionLocal
from app.database.init_db import setup_database
from app.database.crud import upsert_hackathon, get_or_create_user
from app.models.hackathon import HackathonEvent
from app.config import settings

def seed_demo_hackathons(count: int = 3):
    """Seed clearly marked DEMO hackathons for testing and demonstration."""
    setup_database()
    db = SessionLocal()

    # Ensure a demo user exists if TELEGRAM_CHAT_ID is present or use a test ID
    if settings.TELEGRAM_CHAT_ID:
        try:
            get_or_create_user(db, int(settings.TELEGRAM_CHAT_ID), username="test_user", first_name="Test")
        except Exception:
            pass

    demo_events = [
        {
            "title": "[DEMO] AI Innovation Hackathon 2026",
            "organizer": "XYZ Technologies & Antigravity Lab",
            "location": "Bangalore, Karnataka, India",
            "country": "India",
            "state": "Karnataka",
            "city": "Bangalore",
            "online": False,
            "hybrid": False,
            "prize_pool": "₹5,00,000",
            "prize_pool_amount": 500000.0,
            "currency": "INR",
            "categories": ["AI / ML", "Web Development", "General"],
            "technologies": ["Python", "PyTorch", "FastAPI", "React"],
            "tags": ["AI", "Innovation", "Demo"],
            "description": "A premier 48-hour offline hackathon in Bangalore focusing on Generative AI and intelligent autonomous agents.",
            "url": "https://hackradar.demo/events/ai-innovation-2026",
            "team_size_min": 2,
            "team_size_max": 4,
        },
        {
            "title": "[DEMO] Global Web3 & CyberSec Summit 2026",
            "organizer": "Decentral Foundation",
            "location": "Online",
            "country": None,
            "state": None,
            "city": None,
            "online": True,
            "hybrid": False,
            "prize_pool": "$25,000",
            "prize_pool_amount": 25000.0,
            "currency": "USD",
            "categories": ["Blockchain", "Cybersecurity"],
            "technologies": ["Solidity", "Rust", "Ethereum", "ZK-SNARKs"],
            "tags": ["Web3", "Cyber", "Online", "Demo"],
            "description": "Global virtual hackathon for blockchain security, smart contract auditing, and privacy-preserving dApps.",
            "url": "https://hackradar.demo/events/web3-cybersec-2026",
            "team_size_min": 1,
            "team_size_max": 3,
        },
        {
            "title": "[DEMO] Kerala Tech Spark Robotics Challenge",
            "organizer": "Kerala State Innovation Council",
            "location": "Kochi, Kerala, India",
            "country": "India",
            "state": "Kerala",
            "city": "Kochi",
            "online": False,
            "hybrid": True,
            "prize_pool": "₹2,00,000",
            "prize_pool_amount": 200000.0,
            "currency": "INR",
            "categories": ["Robotics", "IoT", "Hardware"],
            "technologies": ["ROS", "ESP32", "Computer Vision", "Sensors"],
            "tags": ["Robotics", "Kerala", "Hardware", "Demo"],
            "description": "Build innovative autonomous rovers and IoT hardware prototypes in Kochi.",
            "url": "https://hackradar.demo/events/kerala-tech-spark-2026",
            "team_size_min": 2,
            "team_size_max": 5,
        }
    ]

    now = datetime.now(timezone.utc)
    inserted = []

    for raw in demo_events[:count]:
        demo_id = str(uuid.uuid4())[:8]
        event = HackathonEvent(
            source="demo",
            source_event_id=f"demo-{demo_id}",
            title=raw["title"],
            organizer=raw["organizer"],
            description=raw["description"],
            url=raw["url"],
            registration_url=f"{raw['url']}/register",
            location=raw["location"],
            country=raw.get("country"),
            state=raw.get("state"),
            city=raw.get("city"),
            online=raw["online"],
            hybrid=raw["hybrid"],
            start_datetime=now + timedelta(days=14),
            end_datetime=now + timedelta(days=16),
            registration_deadline=now + timedelta(days=10),
            prize_pool=raw["prize_pool"],
            prize_pool_amount=raw["prize_pool_amount"],
            currency=raw["currency"],
            team_size_min=raw["team_size_min"],
            team_size_max=raw["team_size_max"],
            categories=raw["categories"],
            technologies=raw["technologies"],
            tags=raw["tags"],
            status="open",
            is_demo=True,
            raw_source_data={"seeded_by": "seed_demo"}
        )

        h_obj, is_new, _ = upsert_hackathon(db, event.to_dict())
        inserted.append((h_obj.title, is_new))

    db.close()
    return inserted

if __name__ == "__main__":
    results = seed_demo_hackathons()
    print("🌱 Seeded demo hackathons:")
    for title, is_new in results:
        status_label = "NEW" if is_new else "UPDATED"
        print(f"  • [{status_label}] {title}")
