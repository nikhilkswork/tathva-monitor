import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "HackRadar"
    PROJECT_DESCRIPTION: str = "Real-Time Hackathon Discovery & Telegram Alert System"
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'hackradar.db'}")

    @property
    def normalized_database_url(self) -> str:
        """
        Normalize DATABASE_URL for SQLAlchemy 2.0+ and psycopg3:
        Converts 'postgres://' or 'postgresql://' to 'postgresql+psycopg://'.
        """
        raw = self.DATABASE_URL.strip()
        if raw.startswith("postgres://"):
            return "postgresql+psycopg://" + raw[len("postgres://"):]
        if raw.startswith("postgresql://") and not raw.startswith("postgresql+"):
            return "postgresql+psycopg://" + raw[len("postgresql://"):]
        return raw

    @property
    def masked_database_url(self) -> str:
        """Mask credentials for safe logging"""
        url = self.normalized_database_url
        if "@" in url and "://" in url:
            prefix, rest = url.split("://", 1)
            creds, host_part = rest.split("@", 1)
            user = creds.split(":", 1)[0] if ":" in creds else creds
            return f"{prefix}://{user}:***@{host_part}"
        return url

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Admin Auth
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "hackradar123")

    # Monitoring Settings
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 HackRadar/1.0"
    )

    # Polling & Scheduling
    MONITOR_INTERVAL_MINUTES: int = int(os.getenv("MONITOR_INTERVAL_MINUTES", "15"))

settings = Settings()
