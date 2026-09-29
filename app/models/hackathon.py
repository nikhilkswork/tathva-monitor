from datetime import datetime, timezone
import hashlib
import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

def parse_flexible_date(val: Any) -> Optional[datetime]:
    """Parse flexible date strings or timestamps into UTC datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)

    val_str = str(val).strip()
    if not val_str:
        return None

    # Handle ISO 8601 with Z or offset
    try:
        # replace Z with +00:00 for fromisoformat in older pythons
        cleaned = val_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # Common date formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue

    return None


def extract_prize_amount(prize_str: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    """Extract numeric prize amount and currency from string like '$740,000' or '₹1,50,000'"""
    if not prize_str:
        return None, None

    currency = None
    if "$" in prize_str or "USD" in prize_str:
        currency = "USD"
    elif "₹" in prize_str or "INR" in prize_str or "Rs" in prize_str:
        currency = "INR"
    elif "€" in prize_str or "EUR" in prize_str:
        currency = "EUR"
    elif "£" in prize_str or "GBP" in prize_str:
        currency = "GBP"

    # Remove currency symbols and commas
    cleaned = re.sub(r"[^\d.]", "", prize_str)
    try:
        amount = float(cleaned)
        return amount, currency
    except Exception:
        return None, currency


from typing import Tuple

class HackathonEvent(BaseModel):
    source: str
    source_event_id: str
    title: str
    organizer: Optional[str] = None
    description: Optional[str] = None
    url: str
    registration_url: Optional[str] = None
    image_url: Optional[str] = None

    location: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None

    online: bool = False
    hybrid: bool = False

    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None

    prize_pool: Optional[str] = None
    prize_pool_amount: Optional[float] = None
    currency: Optional[str] = None

    team_size_min: Optional[int] = None
    team_size_max: Optional[int] = None
    eligibility: Optional[str] = None

    categories: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    status: str = "open"  # open, upcoming, ended, cancelled
    is_demo: bool = False
    raw_source_data: Dict[str, Any] = Field(default_factory=dict)

    @property
    def dedup_key(self) -> str:
        """
        Generate stable deduplication key.
        Prefers source + source_event_id, fallback to normalized title + url hash.
        """
        if self.source_event_id:
            cleaned_id = re.sub(r"\s+", "", str(self.source_event_id).strip())
            return f"{self.source.lower().strip()}:{cleaned_id}"
        
        # Fallback hash
        norm_title = re.sub(r"[^a-zA-Z0-9]", "", self.title.lower())
        h = hashlib.sha256(f"{self.source}:{norm_title}:{self.url}".encode()).hexdigest()[:16]
        return f"{self.source.lower().strip()}:{h}"

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        data["dedup_key"] = self.dedup_key
        return data
