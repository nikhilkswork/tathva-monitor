import pytest
from app.models.hackathon import HackathonEvent
from app.database.schema import User, UserPreference
from app.matching.matcher import (
    match_location, match_category, match_mode, match_prize, match_user_preference
)

def make_test_event(
    title="AI Innovation Hackathon",
    location="Bangalore, Karnataka, India",
    online=False,
    hybrid=False,
    categories=None,
    prize_amount=50000.0
):
    return HackathonEvent(
        source="test",
        source_event_id="t-1",
        title=title,
        url="https://test.com",
        location=location,
        country="India",
        state="Karnataka",
        city="Bangalore",
        online=online,
        hybrid=hybrid,
        categories=categories or ["AI / ML"],
        prize_pool_amount=prize_amount,
        prize_pool=f"₹{prize_amount:.0f}"
    )

def test_location_matching():
    ev_india = make_test_event(location="Bangalore, Karnataka, India", online=False)
    ev_online = make_test_event(location="Online", online=True)
    ev_us = HackathonEvent(
        source="test", source_event_id="t-2", title="MIT Hack",
        url="https://mit.edu", location="Cambridge, MA, USA",
        country="US", online=False
    )

    # Anywhere matches all
    assert match_location(["Anywhere"], ev_india)[0] is True
    assert match_location(["Anywhere"], ev_online)[0] is True
    assert match_location(["Anywhere"], ev_us)[0] is True

    # Online
    assert match_location(["Online"], ev_online)[0] is True
    assert match_location(["Online"], ev_india)[0] is False

    # India
    assert match_location(["India"], ev_india)[0] is True
    assert match_location(["India"], ev_us)[0] is False

    # State specific
    assert match_location(["Karnataka"], ev_india)[0] is True
    assert match_location(["Kerala"], ev_india)[0] is False

    # International
    assert match_location(["International"], ev_us)[0] is True
    assert match_location(["International"], ev_india)[0] is False


def test_category_matching():
    ev_ai = make_test_event(title="Autonomous Deep Learning Sprint", categories=["AI / ML"])
    ev_web = make_test_event(title="React & Next.js Showcase", categories=["Web Development"])

    # General matches everything
    assert match_category(["General"], ev_ai)[0] is True
    assert match_category(["General"], ev_web)[0] is True

    # Exact domain
    assert match_category(["AI / ML"], ev_ai)[0] is True
    assert match_category(["AI / ML"], ev_web)[0] is False
    assert match_category(["Web Development"], ev_web)[0] is True

    # Keyword match from title
    ev_robowars = make_test_event(title="Robowars 8KG Arena Battle", categories=["General"])
    assert match_category(["Robotics"], ev_robowars)[0] is True


def test_mode_and_prize_matching():
    ev_online = make_test_event(online=True, prize_amount=10000.0)
    ev_offline = make_test_event(online=False, prize_amount=50000.0)

    # Modes
    assert match_mode(["Online"], ev_online)[0] is True
    assert match_mode(["Online"], ev_offline)[0] is False
    assert match_mode(["Offline"], ev_offline)[0] is True

    # Prize threshold
    assert match_prize(20000.0, ev_offline)[0] is True
    assert match_prize(20000.0, ev_online)[0] is False


def test_full_user_preference_matching():
    user = User(telegram_id=999888, is_active=True)
    pref = UserPreference(
        user_id=1,
        locations_json='["India", "Online"]',
        categories_json='["AI / ML"]',
        modes_json='["Online", "Offline"]',
        min_prize_pool=10000.0
    )
    user.preferences = pref

    # Matching event
    match_ev = make_test_event(
        title="India Generative AI Challenge",
        location="Bangalore, Karnataka, India",
        online=False,
        categories=["AI / ML"],
        prize_amount=25000.0
    )
    is_match, reasons = match_user_preference(user, match_ev)
    assert is_match is True

    # Non-matching event (different domain)
    non_match_ev = make_test_event(
        title="Solidity Smart Contract CTF",
        location="Bangalore, Karnataka, India",
        online=False,
        categories=["Blockchain"],
        prize_amount=25000.0
    )
    is_match, reasons = match_user_preference(user, non_match_ev)
    assert is_match is False

    # Paused user should not match
    user.is_active = False
    is_match, _ = match_user_preference(user, match_ev)
    assert is_match is False
