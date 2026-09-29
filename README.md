# 🚨 HackRadar — Real-Time Hackathon Discovery & Telegram Alert System

HackRadar is a production-ready, low-cost/free hackathon monitoring and alert platform. It continuously tracks trusted hackathon and event sources, normalizes unstructured event data, deduplicates listings, matches opportunities against user-configured preferences (location, domain, event format, prize amount), and delivers instant, rich notifications directly to Telegram subscribers.

---

## 🌟 Key Features

* **Multi-Source Ingestion**: Unified adapter architecture supporting:
  * **Devfolio**: Official public API integration (25+ active hackathons)
  * **Unstop**: Official opportunities API (25+ national hackathons & challenges)
  * **Devpost**: Official API with browser headers (global challenges & prize pools)
  * **Major League Hacking (MLH)**: Schema.org Event microdata parsing (student hackathons)
  * **Tathva (NIT Calicut)**: Workshops & technical competitions API
  * **Generic Web Adapter**: Extracts events from arbitrary websites using JSON-LD (`@type: Event`) and OpenGraph metadata
  * **Kaggle & Hack2skill**: Documented adapters with graceful status handling
* **Smart Deduplication & Change Tracking**: Stable deduplication key (`source:source_event_id`) prevents duplicate alerts. Detects and tracks changes in registration deadlines, dates, prizes, and status.
* **Granular Preference Matching**:
  * **Locations**: Anywhere, Online, India, Kerala, Karnataka, Tamil Nadu, Maharashtra, Delhi, Telangana, International, or custom cities.
  * **Categories**: AI / ML, Web Development, App Development, Cybersecurity, Blockchain, IoT, Robotics, Cloud, Data Science, Open Source, Hardware, Game Development, General.
  * **Modes**: Online, Offline, Hybrid.
  * **Prize Thresholds**: Filter by minimum prize amount.
* **Full-Featured Telegram Bot**:
  * Real-time interactive commands: `/start`, `/help`, `/preferences`, `/locations`, `/categories`, `/sources`, `/status`, `/pause`, `/resume`, `/events`, `/latest`, `/settings`.
  * Interactive inline keyboards for one-tap preference toggling.
  * Rich mobile alerts with direct buttons: `[🚀 Register Now]`, `[🔍 Details]`.
* **Modern Web Dashboard**: Responsive dashboard with real-time statistics, searchable hackathon catalog, source health monitor, error logs, and one-click manual monitor trigger.
* **Robust Fault Tolerance**: Per-source error isolation ensures failure of one website never halts discovery on others.
* **₹0 Operating Cost**: Runs on GitHub Actions + SQLite + Telegram Bot API.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Trusted Sources                             │
│  Devfolio  │  Unstop  │  Devpost  │  MLH  │  Tathva  │  Generic │
└──────┬──────────┬──────────┬─────────┬────────┬──────────┬──────┘
       │          │          │         │        │          │
┌──────▼──────────▼──────────▼─────────▼────────▼──────────▼──────┐
│                    Source Adapter Layer                         │
│   (fetch_events -> parse_event -> normalize_event -> health)    │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Normalized HackathonEvent
┌────────────────────────────────▼────────────────────────────────┐
│                   Deduplication & Storage                       │
│    (SQLite / SQLAlchemy ORM: Hackathons & EventChange Log)      │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Genuinely NEW Events
┌────────────────────────────────▼────────────────────────────────┐
│                   User Preference Matching                      │
│   (Locations: India/Online... | Categories: AI/Web... | Mode)   │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Matching Users
┌────────────────────────────────▼────────────────────────────────┐
│                   Telegram Dispatcher                           │
│     (Rich formatting, inline buttons, delivery logging)         │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
             Telegram Users            Web Dashboard
```

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
* Python 3.10+ (tested through Python 3.14)
* A Telegram Bot token from [@BotFather](https://t.me/BotFather)

### 2. Clone and Setup Environment

```bash
git clone https://github.com/nikhilkswork/tathva-monitor.git
cd tathva-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuvWxyz
TELEGRAM_CHAT_ID=1935241312
DATABASE_URL=sqlite:///hackradar.db
ADMIN_USERNAME=admin
ADMIN_PASSWORD=hackradar123
```

### 4. Initialize Database & Seed Sources

```bash
python -m app.database.init_db
```

---

## 🏃 Running the Application

### Run the Monitoring Engine (CLI)

Executes a full discovery cycle across all enabled sources, prints a formatted summary table, and dispatches alerts for new hackathons:

```bash
python -m app.monitor
```

Example Output:
```
==================================================
  🚨 HackRadar Hackathon Monitor
==================================================
  Tathva          ✓  59 events (0 new)
  Devfolio        ✓  25 events (0 new)
  Unstop          ✓  25 events (0 new)
  Devpost         ✓  9 events (0 new)
  Mlh             ✓  25 events (0 new)
  Generic         ✓  0 events (0 new)
--------------------------------------------------
  Total Events Found:   143
  Genuinely New Events: 0
  Notifications Sent:   0
  Sources Succeeded:    6/6
  Status:               SUCCESS
==================================================
```

### Run the Web Dashboard & API

```bash
uvicorn app.main:app --reload --port 8000
```
Open your browser at:
* **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
* **Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Run the Interactive Telegram Bot Runner

```bash
python -m app.bot.runner
```

### Seed Demo Hackathons (for testing without live websites)

```bash
python -m app.seed_demo
```

---

## 🧪 Automated Testing

Run the automated test suite covering normalization, deduplication, location matching, category semantic matching, source parsing, Telegram formatting, and Section 36 acceptance flow:

```bash
pytest -v
```

All 20 tests execute in < 1 second using clean in-memory mocks.

---

## 🤖 Telegram Bot Setup & User Flow

1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Type `/newbot` and follow instructions to create a bot name and username (e.g. `HackRadarBot`).
3. Copy the HTTP API token into `TELEGRAM_BOT_TOKEN` in your `.env`.
4. To find your personal Telegram Chat ID, start a chat with [@userinfobot](https://t.me/userinfobot) or send `/start` to your bot.
5. In your bot chat, the following commands are available:
   * `/start` — Welcome message and initial preference setup.
   * `/preferences` — View your current active filters.
   * `/locations` — Interactive buttons to toggle regions (India, Kerala, Karnataka, Online, etc.).
   * `/categories` — Interactive buttons to toggle domains (AI/ML, Web, Mobile, etc.).
   * `/sources` — Status and discovery count of all monitored platforms.
   * `/status` — Bot and monitoring statistics.
   * `/events` — Browse recent hackathons.
   * `/latest` — View the newest hackathon.
   * `/pause` / `/resume` — Temporarily stop or restart notifications.

---

## ➕ How to Add a New Source Adapter

Adding a new event source requires just 3 steps:

1. Create a new adapter file in `app/sources/mysource.py`:

```python
from typing import List, Dict, Any
from app.sources.base import SourceAdapter
from app.models.hackathon import HackathonEvent, parse_flexible_date

class MySourceAdapter(SourceAdapter):
    source_name = "mysource"
    display_name = "My Hackathon Portal"
    base_url = "https://mysource.com/api/events"

    def fetch_events(self) -> List[Dict[str, Any]]:
        resp = self.request(self.base_url)
        return resp.json().get("events", [])

    def parse_event(self, raw: Dict[str, Any]) -> HackathonEvent:
        return HackathonEvent(
            source=self.source_name,
            source_event_id=str(raw["id"]),
            title=raw["name"],
            url=raw["url"],
            location=raw.get("city", "Online"),
            online=raw.get("is_virtual", False),
            start_datetime=parse_flexible_date(raw.get("start_date")),
            categories=["General"],
            status="open",
            raw_source_data=raw
        )
```

2. Register the adapter in `app/sources/registry.py`:
```python
from app.sources.mysource import MySourceAdapter
self.register("mysource", MySourceAdapter)
```

3. Add source definition to `DEFAULT_SOURCES` in `app/database/crud.py`.

---

## ⚙️ GitHub Actions Scheduling & Persistence

HackRadar includes a GitHub Actions workflow in `.github/workflows/monitor.yml` that runs automatically every 30 minutes.

### Setting Up Secrets in GitHub:
1. Go to your GitHub repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Add the following repository secrets:
   * `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token.
   * `TELEGRAM_CHAT_ID`: Your Telegram Chat ID.

### SQLite Persistence on GitHub Actions:
GitHub Actions runners use an ephemeral filesystem. HackRadar solves this reliably for ₹0 cost by staging and committing the updated `hackradar.db` file back to the repository after every run using `[skip ci]`.

For production deployments with multi-user write frequency, configure `DATABASE_URL` to point to a managed PostgreSQL instance (e.g. Supabase, Neon, or Railway free tier).

---

## ⚖️ Cost & Free-Tier Limitations

1. **Detection Delay**:
   Notification delivery time is:
   $$\text{Notification Time} = \text{Source Publication} + \text{Polling Interval} + \text{Telegram Delivery}$$
   Because sources are polled periodically (default: every 30 minutes on GitHub Actions), events are not detected "at the exact microsecond" of publication.
2. **Telegram Rate Limits**:
   The Telegram Bot API limits private messages to ~20-30 messages per minute per individual chat. HackRadar includes automatic backoff and retry handling to avoid hitting 429 rate limit errors.
3. **Anti-Bot & Dynamic SPAs**:
   Platforms like Hack2skill that protect listings behind client-side reCAPTCHAs are marked as degraded rather than using fragile bypasses.

---

## 📜 License

MIT License. Designed and built with ❤️ for developers and student innovators.
