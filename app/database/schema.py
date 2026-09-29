from datetime import datetime, timezone
import json
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, Float, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database.session import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    # Stored as JSON serialized lists/objects
    locations_json = Column(Text, default='["Anywhere"]')
    categories_json = Column(Text, default='["General"]')
    modes_json = Column(Text, default='["Online", "Offline", "Hybrid"]')
    min_prize_pool = Column(Float, default=0.0)
    keywords_json = Column(Text, default='[]')
    notify_updates = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="preferences")

    @property
    def locations(self):
        try:
            return json.loads(self.locations_json) if self.locations_json else ["Anywhere"]
        except Exception:
            return ["Anywhere"]

    @locations.setter
    def locations(self, val):
        self.locations_json = json.dumps(val)

    @property
    def categories(self):
        try:
            return json.loads(self.categories_json) if self.categories_json else ["General"]
        except Exception:
            return ["General"]

    @categories.setter
    def categories(self, val):
        self.categories_json = json.dumps(val)

    @property
    def modes(self):
        try:
            return json.loads(self.modes_json) if self.modes_json else ["Online", "Offline", "Hybrid"]
        except Exception:
            return ["Online", "Offline", "Hybrid"]

    @modes.setter
    def modes(self, val):
        self.modes_json = json.dumps(val)


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    base_url = Column(String(255), nullable=False)
    source_type = Column(String(50), default="api")  # api, html, feed, generic
    enabled = Column(Boolean, default=True, nullable=False)
    trust_status = Column(String(50), default="trusted")  # trusted, experimental, degraded, needs_auth
    parser_class = Column(String(100), nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    events_discovered = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Hackathon(Base):
    __tablename__ = "hackathons"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), index=True, nullable=False)
    source_event_id = Column(String(255), index=True, nullable=False)
    dedup_key = Column(String(255), unique=True, index=True, nullable=False)

    title = Column(String(255), index=True, nullable=False)
    organizer = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String(500), nullable=False)
    registration_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)

    location = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    online = Column(Boolean, default=False)
    hybrid = Column(Boolean, default=False)

    start_datetime = Column(DateTime(timezone=True), nullable=True)
    end_datetime = Column(DateTime(timezone=True), nullable=True)
    registration_deadline = Column(DateTime(timezone=True), nullable=True)

    prize_pool = Column(String(100), nullable=True)
    prize_pool_amount = Column(Float, nullable=True)
    currency = Column(String(20), nullable=True)

    team_size_min = Column(Integer, nullable=True)
    team_size_max = Column(Integer, nullable=True)
    eligibility = Column(String(255), nullable=True)

    categories_json = Column(Text, default='[]')
    technologies_json = Column(Text, default='[]')
    tags_json = Column(Text, default='[]')

    detected_at = Column(DateTime(timezone=True), default=utc_now)
    first_seen_at = Column(DateTime(timezone=True), default=utc_now)
    last_seen_at = Column(DateTime(timezone=True), default=utc_now)

    status = Column(String(50), default="open")  # new, open, upcoming, ended, cancelled
    is_demo = Column(Boolean, default=False)
    raw_source_data = Column(Text, nullable=True)

    notifications = relationship("Notification", back_populates="hackathon", cascade="all, delete-orphan")
    changes = relationship("EventChange", back_populates="hackathon", cascade="all, delete-orphan")

    @property
    def categories(self):
        try:
            return json.loads(self.categories_json) if self.categories_json else []
        except Exception:
            return []

    @categories.setter
    def categories(self, val):
        self.categories_json = json.dumps(val)

    @property
    def technologies(self):
        try:
            return json.loads(self.technologies_json) if self.technologies_json else []
        except Exception:
            return []

    @technologies.setter
    def technologies(self, val):
        self.technologies_json = json.dumps(val)

    @property
    def tags(self):
        try:
            return json.loads(self.tags_json) if self.tags_json else []
        except Exception:
            return []

    @tags.setter
    def tags(self, val):
        self.tags_json = json.dumps(val)


class MonitorRun(Base):
    __tablename__ = "monitor_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="running")  # running, success, partial_failure, failed
    sources_checked = Column(Integer, default=0)
    sources_succeeded = Column(Integer, default=0)
    sources_failed = Column(Integer, default=0)
    total_events_found = Column(Integer, default=0)
    new_events_found = Column(Integer, default=0)
    notifications_sent = Column(Integer, default=0)
    summary_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    @property
    def summary(self):
        try:
            return json.loads(self.summary_json) if self.summary_json else {}
        except Exception:
            return {}

    @summary.setter
    def summary(self, val):
        self.summary_json = json.dumps(val)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    hackathon_id = Column(Integer, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(50), default="telegram")
    sent_at = Column(DateTime(timezone=True), default=utc_now)
    status = Column(String(50), default="sent")  # sent, failed, mocked
    error_message = Column(Text, nullable=True)

    user = relationship("User", back_populates="notifications")
    hackathon = relationship("Hackathon", back_populates="notifications")


class EventChange(Base):
    __tablename__ = "event_changes"

    id = Column(Integer, primary_key=True, index=True)
    hackathon_id = Column(Integer, ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    change_type = Column(String(50), nullable=False)  # created, updated, deadline_changed, cancelled, ended
    field_name = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_at = Column(DateTime(timezone=True), default=utc_now)

    hackathon = relationship("Hackathon", back_populates="changes")


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=True)
    component = Column(String(100), nullable=False)
    error_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    traceback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
