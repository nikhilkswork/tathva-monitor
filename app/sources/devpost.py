from typing import List, Dict, Any, Tuple
import logging
import re
from app.sources.base import SourceAdapter
from app.models.hackathon import HackathonEvent, extract_prize_amount

logger = logging.getLogger("hackradar.sources.devpost")

class DevpostSourceAdapter(SourceAdapter):
    source_name = "devpost"
    display_name = "Devpost"
    base_url = "https://devpost.com/api/hackathons"

    def __init__(self, timeout: int = 15):
        super().__init__(timeout=timeout)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://devpost.com/hackathons",
            "X-Requested-With": "XMLHttpRequest"
        })

    def fetch_events(self) -> List[Dict[str, Any]]:
        resp = self.request(self.base_url)
        data = resp.json()
        return data.get("hackathons", [])

    def parse_event(self, raw: Dict[str, Any]) -> HackathonEvent:
        event_id = str(raw.get("id"))
        title = raw.get("title") or "Devpost Hackathon"
        url = raw.get("url") or f"https://devpost.com"
        reg_url = raw.get("start_a_submission_url") or url

        # Location
        loc_obj = raw.get("displayed_location") or {}
        loc_str = loc_obj.get("location") if isinstance(loc_obj, dict) else str(loc_obj)
        is_online = bool(loc_str and "online" in loc_str.lower())

        # Organizer
        org = raw.get("organization_name") or "Devpost Host"

        # Image
        thumb = raw.get("thumbnail_url")
        if thumb and thumb.startswith("//"):
            thumb = f"https:{thumb}"

        # Prize
        prize_raw = raw.get("prize_amount") or ""
        clean_prize = re.sub(r"<[^>]+>", "", prize_raw).strip()
        amount, currency = extract_prize_amount(clean_prize)

        # Themes / Categories
        themes = raw.get("themes") or []
        theme_names = [t.get("name") for t in themes if isinstance(t, dict) and t.get("name")]
        
        categories = ["General"]
        for t in theme_names:
            tlow = t.lower()
            if any(k in tlow for k in ["ai", "machine learning"]):
                categories.append("AI / ML")
            elif any(k in tlow for k in ["web", "frontend", "backend"]):
                categories.append("Web Development")
            elif any(k in tlow for k in ["mobile", "app", "ios", "android"]):
                categories.append("App Development")
            elif any(k in tlow for k in ["blockchain", "crypto", "web3"]):
                categories.append("Blockchain")
            elif any(k in tlow for k in ["security", "cyber"]):
                categories.append("Cybersecurity")
            elif any(k in tlow for k in ["game", "gaming"]):
                categories.append("Game Development")
            elif any(k in tlow for k in ["iot", "hardware"]):
                categories.append("IoT")
            else:
                categories.append(t)

        dates_str = raw.get("submission_period_dates") or ""
        desc = f"Devpost Hackathon. Dates: {dates_str}. Themes: {', '.join(theme_names) if theme_names else 'Open'}"

        return HackathonEvent(
            source=self.source_name,
            source_event_id=event_id,
            title=title,
            organizer=org,
            description=desc,
            url=url,
            registration_url=reg_url,
            image_url=thumb,
            location=loc_str or ("Online" if is_online else "Global"),
            country="International" if not is_online else None,
            online=is_online,
            hybrid=False,
            prize_pool=clean_prize if clean_prize else None,
            prize_pool_amount=amount,
            currency=currency or "USD",
            categories=list(set(categories)),
            tags=theme_names + ["Devpost"],
            status="open",
            raw_source_data=raw
        )

    def health_check(self) -> Tuple[bool, str]:
        try:
            resp = self.request(self.base_url, retries=1)
            data = resp.json()
            items = data.get("hackathons", [])
            return True, f"Healthy ({len(items)} hackathons)"
        except Exception as e:
            return False, str(e)
