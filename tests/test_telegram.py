import pytest
from app.models.hackathon import HackathonEvent
from app.notifications.telegram import format_hackathon_message, TelegramNotifier

def test_telegram_message_formatting():
    ev = HackathonEvent(
        source="devfolio",
        source_event_id="test-101",
        title="AI Innovation Hackathon 2026",
        organizer="XYZ Technologies",
        location="Bangalore, Karnataka, India",
        online=False,
        prize_pool="₹5,00,000",
        categories=["AI / ML", "Web"],
        description="A premier hackathon for machine learning builders.",
        url="https://devfolio.co/ai-hack",
        team_size_min=2,
        team_size_max=4,
    )

    msg = format_hackathon_message(ev)
    assert "🚨 <b>NEW HACKATHON DETECTED</b>" in msg
    assert "AI Innovation Hackathon 2026" in msg
    assert "XYZ Technologies" in msg
    assert "Bangalore, Karnataka, India" in msg
    assert "₹5,00,000" in msg
    assert "2–4" in msg
    assert "Devfolio" in msg


def test_telegram_notifier_missing_token():
    notifier = TelegramNotifier(token="")
    success, err = notifier.send_message(123456, "Hello test")
    assert success is False
    assert "not configured" in err
