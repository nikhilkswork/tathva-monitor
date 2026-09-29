from typing import List, Dict, Any, Tuple
import logging
from app.sources.base import SourceAdapter
from app.models.hackathon import HackathonEvent, parse_flexible_date

logger = logging.getLogger("hackradar.sources.tathva")

class TathvaSourceAdapter(SourceAdapter):
    source_name = "tathva"
    display_name = "Tathva (NIT Calicut)"
    base_url = "https://api.tathva.org/api/events/all"

    def fetch_events(self) -> List[Dict[str, Any]]:
        events = []
        # Tathva has workshops and competitions
        for event_type in ["workshops", "competitions"]:
            url = f"{self.base_url}?type={event_type}"
            try:
                resp = self.request(url, retries=1)
                data = resp.json()
                items = data.get("events", [])
                for it in items:
                    it["_tathva_type"] = event_type
                events.extend(items)
            except Exception as e:
                logger.error(f"[tathva] Failed to fetch {event_type}: {e}")
        return events

    def parse_event(self, raw: Dict[str, Any]) -> HackathonEvent:
        event_id = str(raw.get("id"))
        title = raw.get("heading") or f"Tathva Event #{event_id}"
        description = raw.get("description") or ""
        event_type = raw.get("_tathva_type", "event")

        # Datetime
        dt_val = raw.get("datetime")
        start_dt = parse_flexible_date(dt_val)

        # Venue / Location
        venue_name = raw.get("venue", {}).get("name") if isinstance(raw.get("venue"), dict) else "NIT Calicut"
        location = f"{venue_name}, NIT Calicut, Kerala, India"

        # Organizer
        committee = raw.get("committee") or "Tathva, NIT Calicut"

        # Image
        pic = raw.get("picture")

        # Status
        raw_status = (raw.get("status") or "OPEN").upper()
        status = "open" if raw_status == "OPEN" else "closed"

        # Fee or prize (price in paise)
        price_paise = raw.get("price") or 0
        price_inr = price_paise / 100.0

        # Tags & Categories
        categories = ["General"]
        title_lower = title.lower()
        if any(w in title_lower for w in ["ai", "ml", "data science", "gen ai"]):
            categories.append("AI / ML")
        if any(w in title_lower for w in ["web", "frontend", "backend", "full stack"]):
            categories.append("Web Development")
        if any(w in title_lower for w in ["app", "flutter", "mobile"]):
            categories.append("App Development")
        if any(w in title_lower for w in ["robo", "drone"]):
            categories.append("Robotics")
        if any(w in title_lower for w in ["cyber", "security", "forensics"]):
            categories.append("Cybersecurity")
        if any(w in title_lower for w in ["cloud"]):
            categories.append("Cloud")
        if any(w in title_lower for w in ["pcb", "3d printing", "cad", "hardware"]):
            categories.append("Hardware")
        if any(w in title_lower for w in ["game"]):
            categories.append("Game Development")

        return HackathonEvent(
            source=self.source_name,
            source_event_id=event_id,
            title=title,
            organizer=committee,
            description=description,
            url=f"https://tathva.org/events/{event_id}",
            registration_url=f"https://tathva.org/events/{event_id}",
            image_url=pic,
            location=location,
            country="India",
            state="Kerala",
            city="Calicut",
            online=False,
            hybrid=False,
            start_datetime=start_dt,
            prize_pool=f"₹{price_inr:.0f} (Reg/Prize)" if price_inr > 0 else "Free",
            prize_pool_amount=price_inr,
            currency="INR",
            categories=list(set(categories)),
            tags=[event_type, "NIT Calicut", "Tech Fest"],
            status=status,
            raw_source_data=raw
        )

    def health_check(self) -> Tuple[bool, str]:
        try:
            resp = self.request(f"{self.base_url}?type=workshops", retries=1)
            data = resp.json()
            count = len(data.get("events", []))
            return True, f"Healthy ({count} workshops available)"
        except Exception as e:
            return False, str(e)
