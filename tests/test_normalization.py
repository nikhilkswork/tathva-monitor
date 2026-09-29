from datetime import datetime, timezone
import pytest
from app.models.hackathon import (
    HackathonEvent, parse_flexible_date, extract_prize_amount
)

def test_flexible_date_parsing():
    # ISO 8601 with Z
    d1 = parse_flexible_date("2026-10-15T18:29:00.000Z")
    assert d1 is not None
    assert d1.year == 2026 and d1.month == 10 and d1.day == 15
    assert d1.tzinfo is not None

    # ISO with offset
    d2 = parse_flexible_date("2026-09-13T11:59:43+05:30")
    assert d2 is not None
    assert d2.tzinfo is not None

    # Standard date formats
    d3 = parse_flexible_date("2026-11-20")
    assert d3 is not None
    assert d3.year == 2026 and d3.month == 11 and d3.day == 20

    # None and empty
    assert parse_flexible_date(None) is None
    assert parse_flexible_date("") is None


def test_prize_amount_extraction():
    amount, curr = extract_prize_amount("$740,000")
    assert amount == 740000.0
    assert curr == "USD"

    amount_inr, curr_inr = extract_prize_amount("₹1,50,000")
    assert amount_inr == 150000.0
    assert curr_inr == "INR"

    amount_eur, curr_eur = extract_prize_amount("5,000 €")
    assert amount_eur == 5000.0
    assert curr_eur == "EUR"

    amt_none, curr_none = extract_prize_amount("Free to enter")
    assert amt_none is None


def test_hackathon_dedup_key():
    ev1 = HackathonEvent(
        source="devfolio",
        source_event_id="abc-123",
        title="Test Hackathon",
        url="https://devfolio.co/abc",
        online=True
    )
    assert ev1.dedup_key == "devfolio:abc-123"

    ev2 = HackathonEvent(
        source="devfolio",
        source_event_id="  abc-123  ",
        title="Test Hackathon 2",
        url="https://devfolio.co/abc2",
        online=True
    )
    assert ev2.dedup_key == "devfolio:abc-123"

    # Empty source_event_id fallback
    ev3 = HackathonEvent(
        source="generic",
        source_event_id="",
        title="Global AI Challenge",
        url="https://example.com/ai",
        online=True
    )
    assert ev3.dedup_key.startswith("generic:")
