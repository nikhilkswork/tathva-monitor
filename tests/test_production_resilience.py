from unittest.mock import patch, MagicMock
import pytest
from app.config import Settings
from app.bot.runner import mask_token, verify_and_clear_webhook

def test_database_url_normalization():
    s = Settings()

    # postgres://
    s.DATABASE_URL = "postgres://user:secret123@aws.pooler.supabase.com:6543/postgres"
    assert s.normalized_database_url == "postgresql+psycopg://user:secret123@aws.pooler.supabase.com:6543/postgres"

    # postgresql:// without driver
    s.DATABASE_URL = "postgresql://user:secret123@localhost:5432/testdb"
    assert s.normalized_database_url == "postgresql+psycopg://user:secret123@localhost:5432/testdb"

    # postgresql+psycopg:// already specified
    s.DATABASE_URL = "postgresql+psycopg://user:secret123@localhost:5432/testdb"
    assert s.normalized_database_url == "postgresql+psycopg://user:secret123@localhost:5432/testdb"

    # sqlite://
    s.DATABASE_URL = "sqlite:///hackradar.db"
    assert s.normalized_database_url == "sqlite:///hackradar.db"


def test_masked_database_url():
    s = Settings()
    s.DATABASE_URL = "postgresql+psycopg://postgres_user:super_secret_password@db.supabase.co:5432/postgres"
    masked = s.masked_database_url
    assert "super_secret_password" not in masked
    assert "postgres_user:***@db.supabase.co:5432/postgres" in masked


def test_bot_token_masking():
    token = "8900008117:AAHMcqf6llLotM3kKapoMrUTmEWkDPslTqo"
    masked = mask_token(token)
    assert token not in masked
    assert masked.startswith("8900")
    assert masked.endswith("Tqo")

    # Short string
    assert mask_token("short") == "***"


def test_verify_and_clear_webhook_active():
    """Verify that an active webhook is detected and deleted before polling starts"""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        # Mock getMe -> success
        mock_get.side_effect = [
            MagicMock(json=lambda: {"ok": True, "result": {"username": "HackRadarBot"}}),
            MagicMock(json=lambda: {"ok": True, "result": {"url": "https://old-webhook.example.com/hook"}})
        ]
        # Mock deleteWebhook -> success
        mock_post.return_value = MagicMock(json=lambda: {"ok": True, "description": "Webhook deleted"})

        result = verify_and_clear_webhook("123456789:ABCdefGhIJKlmNoPQRstuvWxyz")
        assert result is True
        assert mock_post.call_count == 1
        call_url = mock_post.call_args[0][0]
        assert "deleteWebhook" in call_url


def test_verify_and_clear_webhook_401():
    """Verify that invalid bot token (401) is reported without crashing"""
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: {"ok": False, "error_code": 401, "description": "Unauthorized"})

        result = verify_and_clear_webhook("invalid_token_12345")
        assert result is False
