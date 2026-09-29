from typing import List, Optional
from pydantic import BaseModel, Field

DEFAULT_LOCATIONS = [
    "Anywhere",
    "Online",
    "India",
    "Kerala",
    "Karnataka",
    "Tamil Nadu",
    "Maharashtra",
    "Delhi",
    "Telangana",
    "Andhra Pradesh",
    "International"
]

DEFAULT_CATEGORIES = [
    "AI / ML",
    "Web Development",
    "App Development",
    "Cybersecurity",
    "Blockchain",
    "IoT",
    "Robotics",
    "Cloud",
    "Data Science",
    "Open Source",
    "Hardware",
    "Game Development",
    "General"
]

DEFAULT_MODES = ["Online", "Offline", "Hybrid"]

class UserPreferencesModel(BaseModel):
    locations: List[str] = Field(default_factory=lambda: ["Anywhere"])
    categories: List[str] = Field(default_factory=lambda: ["General"])
    modes: List[str] = Field(default_factory=lambda: ["Online", "Offline", "Hybrid"])
    min_prize_pool: float = 0.0
    keywords: List[str] = Field(default_factory=list)
    notify_updates: bool = False
