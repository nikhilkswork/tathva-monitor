from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.database.schema import Base, User, UserPreference, Hackathon, Source, MonitorRun, Notification, EventChange
from app.database.crud import init_database, get_or_create_user, upsert_hackathon
from app.models.hackathon import HackathonEvent
from app.notifications.sender import dispatch_hackathon_notifications
from app.sources.registry import SourceRegistry
from app.sources.base import SourceAdapter
from app.monitoring.runner import run_monitoring_cycle

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    init_database(db)
    yield db
    db.close()

def test_full_acceptance_flow(test_db):
    """
    Simulation of Section 36:
    1. Create test Telegram user.
    2. Configure: India, Online, AI/ML.
    3. Insert a fake matching event.
    4. Run monitor / dispatch.
    5. Verify detected as NEW.
    6. Verify stored once.
    7. Verify Telegram notification is generated/sent.
    8. Run monitor again.
    9. Verify same event does NOT generate another NEW notification.
    10. Change the event.
    11. Verify event is updated without a duplicate NEW notification.
    12. Create a non-matching event.
    13. Verify user does not receive it.
    14. Simulate one source failure.
    15. Verify other sources continue working.
    """
    # 1. Create a test Telegram user
    user, is_new_user = get_or_create_user(
        db=test_db,
        telegram_id=888999,
        username="test_hacker",
        first_name="Test",
        last_name="Hacker"
    )
    assert is_new_user is True

    # 2. Configure preferences: India, Online, AI/ML
    pref = user.preferences
    pref.locations = ["India", "Online"]
    pref.categories = ["AI / ML"]
    pref.modes = ["Online", "Offline"]
    test_db.commit()

    now = datetime.now(timezone.utc)

    # 3. Create a fake matching event
    matching_event = HackathonEvent(
        source="acceptance_src",
        source_event_id="acc-event-1",
        title="India GenAI Hackathon 2026",
        organizer="AI India Tech",
        description="Top AI innovation challenge in Bangalore",
        url="https://india-ai.dev/hackathon",
        registration_url="https://india-ai.dev/register",
        location="Bangalore, Karnataka, India",
        country="India",
        state="Karnataka",
        city="Bangalore",
        online=False,
        hybrid=False,
        start_datetime=now + timedelta(days=10),
        end_datetime=now + timedelta(days=12),
        registration_deadline=now + timedelta(days=8),
        prize_pool="₹5,00,000",
        prize_pool_amount=500000.0,
        currency="INR",
        categories=["AI / ML"],
        tags=["GenAI", "India"],
        status="open",
        is_demo=True
    )

    # Mock telegram sending
    with patch("app.notifications.sender.telegram_notifier.send_hackathon_alert", return_value=(True, None)) as mock_send:
        # 4. Upsert & detect NEW
        h_obj, is_new, changed_fields = upsert_hackathon(test_db, matching_event.to_dict())
        
        # 5. Verify it is detected as NEW
        assert is_new is True

        # 6. Verify stored once
        stored_count = test_db.query(Hackathon).filter(Hackathon.dedup_key == matching_event.dedup_key).count()
        assert stored_count == 1

        # 7. Dispatch notifications and verify sent
        sent_count = dispatch_hackathon_notifications(test_db, h_obj, matching_event)
        assert sent_count == 1
        assert mock_send.call_count == 1

        notif_record = test_db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.hackathon_id == h_obj.id
        ).first()
        assert notif_record is not None
        assert notif_record.status == "sent"

        # 8 & 9. Run again: Verify the same event does NOT generate another NEW notification
        h_obj_2, is_new_2, changed_2 = upsert_hackathon(test_db, matching_event.to_dict())
        assert is_new_2 is False
        assert len(changed_2) == 0

        # Dispatch again - should not send duplicate notification
        sent_again = dispatch_hackathon_notifications(test_db, h_obj_2, matching_event)
        assert sent_again == 0
        assert mock_send.call_count == 1  # Still 1, no duplicate call!

        # 10 & 11. Change the event: registration deadline changed
        updated_deadline = now + timedelta(days=14)
        matching_event.registration_deadline = updated_deadline
        h_obj_3, is_new_3, changed_3 = upsert_hackathon(test_db, matching_event.to_dict())
        assert is_new_3 is False
        assert "registration_deadline" in changed_3
        # Check event_changes log recorded this change
        changes = test_db.query(EventChange).filter(
            EventChange.hackathon_id == h_obj.id,
            EventChange.field_name == "registration_deadline"
        ).all()
        assert len(changes) >= 1

        # 12 & 13. Create a non-matching event (Cybersecurity in Germany, offline)
        non_matching_event = HackathonEvent(
            source="acceptance_src",
            source_event_id="acc-event-2",
            title="Berlin CyberSec CTF 2026",
            organizer="Berlin Cyber Club",
            url="https://berlin-cyber.de",
            location="Berlin, Germany",
            country="Germany",
            online=False,
            hybrid=False,
            categories=["Cybersecurity"],
            prize_pool="€10,000",
            prize_pool_amount=10000.0,
            currency="EUR",
            status="open"
        )
        h_non_match, is_new_nm, _ = upsert_hackathon(test_db, non_matching_event.to_dict())
        assert is_new_nm is True

        sent_nm = dispatch_hackathon_notifications(test_db, h_non_match, non_matching_event)
        assert sent_nm == 0  # User did not receive because location and category don't match!

    # 14 & 15. Simulate one source failure and verify other sources continue working
    class WorkingMockAdapter(SourceAdapter):
        source_name = "mock_working"
        def fetch_events(self):
            return [{"id": 1, "title": "Mock Hackathon"}]
        def parse_event(self, raw):
            return HackathonEvent(
                source=self.source_name,
                source_event_id=str(raw["id"]),
                title=raw["title"],
                url="https://mock.com",
                online=True
            )

    class FailingMockAdapter(SourceAdapter):
        source_name = "mock_failing"
        def fetch_events(self):
            raise ConnectionError("Simulated Network Timeout on Remote API")
        def parse_event(self, raw):
            raise NotImplementedError()

    # Disable other sources in test_db so only the mock sources run
    test_db.query(Source).update({Source.enabled: False})
    test_db.commit()

    custom_registry = SourceRegistry()
    custom_registry.register("mock_working", WorkingMockAdapter)
    custom_registry.register("mock_failing", FailingMockAdapter)

    # Add both sources to DB
    src1 = Source(name="mock_working", display_name="Working Source", base_url="https://mock.com", enabled=True, parser_class="WorkingMockAdapter")
    src2 = Source(name="mock_failing", display_name="Failing Source", base_url="https://fail.com", enabled=True, parser_class="FailingMockAdapter")
    test_db.add_all([src1, src2])
    test_db.commit()

    with patch("app.monitoring.runner.source_registry", custom_registry):
        cycle_result = run_monitoring_cycle(test_db)
        # Verify that run completed with partial_failure, working source succeeded, failing source logged error
        assert cycle_result["status"] == "partial_failure"
        assert cycle_result["sources_succeeded"] == 1
        assert cycle_result["sources_failed"] == 1
        assert cycle_result["total_events_found"] == 1
        assert cycle_result["sources"]["mock_failing"]["status"] == "error"
        assert "Simulated Network Timeout" in cycle_result["sources"]["mock_failing"]["error"]
        assert cycle_result["sources"]["mock_working"]["status"] == "success"
