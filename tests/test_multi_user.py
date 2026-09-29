from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.database.schema import Base, User, UserPreference, Hackathon, Notification, EventChange
from app.database.crud import init_database, get_or_create_user, upsert_hackathon
from app.models.hackathon import HackathonEvent
from app.notifications.sender import dispatch_hackathon_notifications

@pytest.fixture
def multi_user_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    init_database(db)
    yield db
    db.close()

def test_independent_multi_user_preferences_and_matching(multi_user_db):
    """
    Phase 8 Test:
    User A: India, Online, AI/ML
    User B: Anywhere, Offline, Cybersecurity
    Verify:
    - Independent preferences
    - Independent matching & notifications
    - No cross-notification
    - Pause / Resume per user
    - No duplicate alerts
    """
    db = multi_user_db

    # 1. Register User A
    user_a, _ = get_or_create_user(db, telegram_id=1001, username="user_a", first_name="Alice")
    pref_a = user_a.preferences
    pref_a.locations = ["India", "Online"]
    pref_a.categories = ["AI / ML"]
    pref_a.modes = ["Online", "Offline"]
    user_a.is_active = True

    # 2. Register User B
    user_b, _ = get_or_create_user(db, telegram_id=1002, username="user_b", first_name="Bob")
    pref_b = user_b.preferences
    pref_b.locations = ["Anywhere"]
    pref_b.categories = ["Cybersecurity"]
    pref_b.modes = ["Offline"]
    user_b.is_active = True
    db.commit()

    now = datetime.now(timezone.utc)

    # 3. Event 1: India AI/ML Online Hackathon -> Matches User A, NOT User B (wrong category & mode)
    ai_event = HackathonEvent(
        source="test_src",
        source_event_id="ai-001",
        title="India GenAI Developers Challenge",
        url="https://india-ai.org",
        location="Online",
        country="India",
        online=True,
        categories=["AI / ML"],
        prize_pool="₹2,00,000",
        prize_pool_amount=200000.0,
        status="open"
    )

    # 4. Event 2: Global CyberSec Offline CTF -> Matches User B, NOT User A (wrong category)
    cyber_event = HackathonEvent(
        source="test_src",
        source_event_id="sec-002",
        title="DefCon RedTeam Offline CTF",
        url="https://defcon.org/ctf",
        location="Las Vegas, NV, USA",
        country="US",
        online=False,
        categories=["Cybersecurity"],
        prize_pool="$10,000",
        prize_pool_amount=10000.0,
        status="open"
    )

    with patch("app.notifications.sender.telegram_notifier.send_hackathon_alert", return_value=(True, None)) as mock_send:
        # Upsert Event 1
        h_ai, is_new_1, _ = upsert_hackathon(db, ai_event.to_dict())
        assert is_new_1 is True

        # Dispatch Event 1
        sent_ai = dispatch_hackathon_notifications(db, h_ai, ai_event)
        # Should be sent ONLY to User A
        assert sent_ai == 1
        assert mock_send.call_count == 1
        call_args = mock_send.call_args[1]
        assert call_args["chat_id"] == 1001

        # Check DB records
        notif_a1 = db.query(Notification).filter(Notification.user_id == user_a.id, Notification.hackathon_id == h_ai.id).first()
        notif_b1 = db.query(Notification).filter(Notification.user_id == user_b.id, Notification.hackathon_id == h_ai.id).first()
        assert notif_a1 is not None and notif_a1.status == "sent"
        assert notif_b1 is None  # User B did NOT receive Event 1!

        # Reset mock
        mock_send.reset_mock()

        # Upsert Event 2
        h_sec, is_new_2, _ = upsert_hackathon(db, cyber_event.to_dict())
        assert is_new_2 is True

        # Dispatch Event 2
        sent_sec = dispatch_hackathon_notifications(db, h_sec, cyber_event)
        # Should be sent ONLY to User B
        assert sent_sec == 1
        assert mock_send.call_count == 1
        call_args_sec = mock_send.call_args[1]
        assert call_args_sec["chat_id"] == 1002

        notif_a2 = db.query(Notification).filter(Notification.user_id == user_a.id, Notification.hackathon_id == h_sec.id).first()
        notif_b2 = db.query(Notification).filter(Notification.user_id == user_b.id, Notification.hackathon_id == h_sec.id).first()
        assert notif_a2 is None  # User A did NOT receive Event 2!
        assert notif_b2 is not None and notif_b2.status == "sent"

        # 5. Test Pause / Resume per user:
        # Pause User A
        user_a.is_active = False
        db.commit()

        # Event 3: Matches both User A and User B categories
        multi_match_event = HackathonEvent(
            source="test_src",
            source_event_id="both-003",
            title="AI and Cyber Threat Defense Hackathon",
            url="https://threat.ai",
            location="Bangalore, Karnataka, India",
            country="India",
            online=False,
            categories=["AI / ML", "Cybersecurity"],
            status="open"
        )
        h_multi, is_new_3, _ = upsert_hackathon(db, multi_match_event.to_dict())
        assert is_new_3 is True

        mock_send.reset_mock()
        sent_multi = dispatch_hackathon_notifications(db, h_multi, multi_match_event)
        # Only User B should receive it because User A is paused!
        assert sent_multi == 1
        assert mock_send.call_count == 1
        assert mock_send.call_args[1]["chat_id"] == 1002

        # 6. Test No Duplicate Notification on Rescan:
        mock_send.reset_mock()
        h_multi_rescan, is_new_rescan, _ = upsert_hackathon(db, multi_match_event.to_dict())
        assert is_new_rescan is False
        sent_rescan = dispatch_hackathon_notifications(db, h_multi_rescan, multi_match_event)
        assert sent_rescan == 0
        assert mock_send.call_count == 0  # No duplicate alert sent!
