import pytest
from unittest.mock import MagicMock
from app.sources.tathva import TathvaSourceAdapter
from app.sources.devfolio import DevfolioSourceAdapter
from app.sources.unstop import UnstopSourceAdapter
from app.sources.devpost import DevpostSourceAdapter
from app.sources.mlh import MLHSourceAdapter
from app.sources.generic import GenericSourceAdapter

def test_tathva_adapter_parsing():
    adapter = TathvaSourceAdapter()
    raw_item = {
        "id": 52,
        "heading": "Data Science with AI - 2",
        "datetime": "2026-10-11T03:30:00.000Z",
        "price": 99900,
        "description": "Discover how Artificial Intelligence transforms modern data science.",
        "picture": "https://cdn.tathva.org/events/example.webp",
        "committee": "Workshop committee",
        "status": "OPEN",
        "venue": {"name": "East Campus Complex"},
        "_tathva_type": "workshops"
    }

    event = adapter.parse_event(raw_item)
    assert event.source == "tathva"
    assert event.source_event_id == "52"
    assert event.title == "Data Science with AI - 2"
    assert "AI / ML" in event.categories
    assert event.prize_pool_amount == 999.0
    assert event.country == "India"
    assert event.state == "Kerala"


def test_devfolio_adapter_parsing():
    adapter = DevfolioSourceAdapter()
    raw_item = {
        "uuid": "devfolio-uuid-1",
        "name": "CodeStorm 2026",
        "slug": "codestorm-2026",
        "starts_at": "2026-07-31T18:30:00.000Z",
        "ends_at": "2026-10-15T18:29:00.000Z",
        "is_online": True,
        "hackathon_setting": {
            "site": "https://codestorm.pages.dev",
            "reg_ends_at": "2026-09-29T18:29:00.000Z",
            "logo": "https://assets.devfolio.co/logo.png"
        },
        "themes": [{"name": "AI"}, {"name": "Design"}]
    }

    event = adapter.parse_event(raw_item)
    assert event.source == "devfolio"
    assert event.source_event_id == "devfolio-uuid-1"
    assert event.online is True
    assert "AI / ML" in event.categories
    assert event.url == "https://codestorm.pages.dev"


def test_unstop_adapter_parsing():
    adapter = UnstopSourceAdapter()
    raw_item = {
        "id": 1737808,
        "title": "HackCelestial 3.0",
        "public_url": "hackathons/hackcelestial-30-1737808",
        "region": "offline",
        "details": "<p>A grand engineering hackathon</p>",
        "end_date": "2026-09-27T23:59:00+05:30",
        "prizes": [{"cash": 150000, "currency": "INR"}],
        "filters": [{"name": "Engineering Students"}],
        "locations": ["Navi Mumbai"]
    }

    event = adapter.parse_event(raw_item)
    assert event.source == "unstop"
    assert event.source_event_id == "1737808"
    assert event.online is False
    assert event.prize_pool_amount == 150000.0
    assert "Unstop" in event.tags


def test_devpost_adapter_parsing():
    adapter = DevpostSourceAdapter()
    raw_item = {
        "id": 29969,
        "title": "Shipaton 2026",
        "displayed_location": {"location": "Online"},
        "url": "https://shipaton.devpost.com/",
        "prize_amount": "$<span data-currency-value>50,000</span>",
        "themes": [{"name": "Mobile"}],
        "organization_name": "RevenueCat"
    }

    event = adapter.parse_event(raw_item)
    assert event.source == "devpost"
    assert event.source_event_id == "29969"
    assert event.online is True
    assert event.prize_pool_amount == 50000.0
    assert event.currency == "USD"
    assert "App Development" in event.categories


def test_generic_jsonld_adapter_parsing():
    adapter = GenericSourceAdapter()
    sample_html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Event",
          "@id": "https://example.com/events/ai-summit",
          "name": "Global AI Challenge 2026",
          "description": "An international hackathon on machine learning.",
          "startDate": "2026-11-01T09:00:00Z",
          "location": {
            "@type": "VirtualLocation",
            "name": "Online"
          },
          "url": "https://example.com/events/ai-summit"
        }
        </script>
      </head>
      <body></body>
    </html>
    """

    extracted = adapter.extract_from_html(sample_html, "https://example.com")
    assert len(extracted) == 1
    event = adapter.parse_event(extracted[0])
    assert event.title == "Global AI Challenge 2026"
    assert event.online is True
    assert event.source == "generic"
