# 🚨 HackRadar — Real-Time Hackathon Discovery & Telegram Alert System

HackRadar is a production-grade, 24/7 hackathon monitoring and alert platform. It continuously tracks trusted hackathon and technical event sources, normalizes unstructured event data, deduplicates listings, matches opportunities against each user's personalized preferences, and delivers instant, rich notifications directly to Telegram subscribers.

---

## 🏛️ Production Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Trusted Sources                             │
│  Devfolio  │  Unstop  │  Devpost  │  MLH  │  Tathva  │  Generic │
└──────┬──────────┬──────────┬─────────┬────────┬──────────┬──────┘
       │
       ▼ (Every 30 Mins Scheduled Discovery)
┌─────────────────────────────────────────────────────────────────┐
│               GitHub Actions Scheduled Monitor                  │
│             Runs: python -m app.monitor                         │
│  (Fault-isolated scraping -> Normalization -> Deduplication)   │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│             Persistent PostgreSQL Database                      │
│             (Supabase / Neon / Managed Postgres)                │
│    • Tables: users, preferences, hackathons, notifications      │
│    • Event Change Log & Deduplication Keys                      │
└──────┬───────────────────────────────────────────────────┬──────┘
       │                                                   │
       ▼ (Real-time Preference Matching)                   ▼ (REST API)
┌─────────────────────────────────┐       ┌───────────────────────┐
│     24/7 Cloud Bot Worker       │       │  FastAPI Web App      │
│  (Render / Railway / Fly.io)    │       │  & Admin Dashboard    │
│  python -m app.bot.runner       │       │  uvicorn app.main:app │
│  • Responds to user commands    │       │  • Real-time stats    │
│  • Dynamic preference toggles   │       │  • Searchable catalog │
│  • Active when Mac is OFF       │       │  • Source health      │
└────────────────┬────────────────┘       └───────────────────────┘
                 │
                 ▼
          Telegram Users
```

### Roles & Responsibilities

| Component | Host / Environment | Responsibility |
| :--- | :--- | :--- |
| **PostgreSQL Database** | Supabase or Neon (Free) | Persistent single source of truth for users, preferences, hackathons, and notification history. |
| **Telegram Bot Worker** | Render, Railway, or Fly.io | 24/7 persistent long-polling background worker (`python -m app.bot.runner`). Responds to users even when your local Mac is shut down. |
| **Discovery Monitor** | GitHub Actions | Cron workflow (`.github/workflows/monitor.yml`) running every 30 minutes to fetch new hackathons and write directly to PostgreSQL. |
| **Web Dashboard** | Local or Cloud Web Service | Visual monitoring, live metrics, and search catalog (`uvicorn app.main:app`). |

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
* Python 3.10+ (tested on Python 3.12, 3.13, 3.14)
* A Telegram Bot token from [@BotFather](https://t.me/BotFather)

### 2. Clone and Setup Environment

```bash
git clone https://github.com/nikhilkswork/tathva-monitor.git
cd tathva-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (including PostgreSQL driver & Alembic)
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:
```ini
# Telegram Bot credentials
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Database: Uses SQLite for local dev, or paste your Supabase/Neon PostgreSQL URL
DATABASE_URL=sqlite:///hackradar.db

# Admin Dashboard
ADMIN_USERNAME=admin
ADMIN_PASSWORD=hackradar_secure_password_123
```

### 4. Initialize Database

```bash
python -m app.database.init_db
```
*(Optionally run Alembic migrations: `alembic upgrade head`)*

---

## 🐘 Production PostgreSQL Setup (Supabase / Neon)

HackRadar is completely PostgreSQL-ready using modern `psycopg 3` connection pooling.

### Option A: Supabase (Recommended — Free Tier)
1. Go to [supabase.com](https://supabase.com) and create a free project.
2. In Project Settings -> **Database**, scroll down to **Connection String**.
3. Select **URI** mode and copy the string:
   * **Direct Connection (Port 5432)**:
     `postgresql+psycopg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
   * **Transaction Pooler (Port 6543)**:
     `postgresql+psycopg://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
4. Set this URL as your `DATABASE_URL` in `.env`, GitHub Secrets, and your cloud hosting environment.

### Option B: Neon Serverless PostgreSQL (Free Tier)
1. Go to [neon.tech](https://neon.tech) and create a free project.
2. Copy the connection string:
   `postgresql+psycopg://[USER]:[PASSWORD]@[ENDPOINT].neon.tech/neondb?sslmode=require`
3. Set this URL as your `DATABASE_URL`.

*Note: HackRadar automatically normalizes legacy `postgres://` or `postgresql://` prefixes to `postgresql+psycopg://`.*

---

## ☁️ Deploying the 24/7 Cloud Bot Worker

To ensure your Telegram bot responds to commands and delivers notifications even when your local computer is powered off, deploy the bot worker as a background service.

### Option 1: Render.com (1-Click Blueprint or Background Worker)
1. Fork or push this repository to your GitHub account.
2. Log into [render.com](https://render.com) and click **New +** -> **Blueprint**.
3. Select this repository. Render will read `render.yaml` and configure:
   * `hackradar-bot-worker`: Background worker running `python -m app.bot.runner`.
   * `hackradar-web`: Web service running `uvicorn app.main:app`.
4. In the Render Dashboard, add the environment variables:
   * `DATABASE_URL`: Your Supabase/Neon PostgreSQL connection string.
   * `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token.
   * `TELEGRAM_CHAT_ID`: Your Telegram Chat ID.
5. Click **Apply**. The worker will automatically connect to Telegram, clear webhook conflicts, and begin 24/7 polling!

### Option 2: Railway.app
1. Go to [railway.app](https://railway.app) -> **New Project** -> **Deploy from GitHub repo**.
2. Set the Start Command to: `python -m app.bot.runner`.
3. Add environment variables: `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`.
4. Deploy!

### Option 3: Docker / Self-Hosted VPS
```bash
# Build and run container in background with restart policy
docker compose up -d
```

---

## ⚙️ GitHub Actions Scheduled Monitoring

HackRadar automatically discovers new hackathons every 30 minutes via GitHub Actions.

### Configure GitHub Secrets:
1. In your GitHub repository, navigate to **Settings** -> **Secrets and variables** -> **Actions**.
2. Add the following secrets:
   * `DATABASE_URL`: Your production PostgreSQL connection string (`postgresql+psycopg://...`).
   * `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather.
   * `TELEGRAM_CHAT_ID`: Your personal chat ID.
3. The workflow in `.github/workflows/monitor.yml` runs every 30 minutes and can also be triggered manually using the **Run workflow** button in the **Actions** tab.
4. Because PostgreSQL is the persistent database, no files need to be committed back to the repository.

---

## 🏃 Local Commands Reference

```bash
# 1. Run the hackathon discovery cycle locally
python -m app.monitor

# 2. Run the interactive Telegram bot polling service locally
python -m app.bot.runner

# 3. Start the Web Dashboard and REST API
uvicorn app.main:app --reload --port 8000
# Open http://localhost:8000 in your browser

# 4. Run automated test suite
pytest -v

# 5. Seed sample demo hackathons
python -m app.seed_demo
```

---

## 🤖 Telegram Bot Commands & Multi-User Usage

Each user who starts the bot has completely independent preferences stored in the database:

| Command | Description |
| :--- | :--- |
| `/start` | Welcome greeting and interactive preference setup. |
| `/preferences` | View active locations, categories, modes, and alert status. |
| `/locations` | Interactive buttons to toggle regions (India, Kerala, Karnataka, Online, etc.). |
| `/categories` | Interactive buttons to toggle domains (AI/ML, Web, Cybersecurity, etc.). |
| `/status` | View current subscriber status and tracking stats. |
| `/pause` | Temporarily pause receiving alerts. |
| `/resume` | Resume receiving alerts. |
| `/events` | Browse the latest discovered hackathons. |
| `/latest` | View full details of the most recently discovered hackathon. |
| `/help` | Detailed command guide. |

---

## 🧪 Testing & Verification

Run the comprehensive automated test suite:

```bash
pytest -v
```

Tests cover:
* Data model normalization, flexible date parsing, and currency extraction.
* Stable deduplication keys (`source:source_event_id`).
* Independent multi-user preference matching & isolation (Phase 8).
* PostgreSQL URL normalization (`postgres://` -> `postgresql+psycopg://`) and credential masking.
* Webhook clearing and Telegram API error handling (401, 409, 429).
* Source adapters for Devfolio, Unstop, Devpost, MLH, Tathva, and Generic JSON-LD.
* FastAPI endpoints and dashboard UI.
* Section 36 End-to-End Acceptance Simulation.

---

## 🛠️ Troubleshooting

### 1. Telegram API `409 Conflict: terminated by other getUpdates request`
* **Cause**: Multiple polling processes running simultaneously using the same bot token (e.g. running on your Mac and on a cloud worker at the same time).
* **Fix**: Stop the local bot runner (`Ctrl+C`) when the cloud worker is active. HackRadar handles this gracefully with backoff.

### 2. Telegram API `401 Unauthorized`
* **Cause**: Invalid or revoked bot token.
* **Fix**: Check `TELEGRAM_BOT_TOKEN` in your `.env` or cloud service variables. Ensure there are no surrounding quotes or extra spaces.

### 3. PostgreSQL `Tenant or user not found` / Connection Closed
* **Cause**: Incorrect database username or using direct connection port when behind PgBouncer.
* **Fix**: For Supabase, use port `5432` for direct connection or port `6543` for transaction pooler. Ensure password does not contain unescaped special characters.

---

## 📜 License

MIT License. Designed and built with ❤️ for developers and student innovators.
