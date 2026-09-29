from typing import List, Dict, Any, Tuple
import os
import logging
from app.sources.base import SourceAdapter
from app.models.hackathon import HackathonEvent, parse_flexible_date

logger = logging.getLogger("hackradar.sources.kaggle")

class KaggleSourceAdapter(SourceAdapter):
    """
    Kaggle Competitions adapter.
    Kaggle requires API credentials (KAGGLE_USERNAME and KAGGLE_KEY) to query competition listings.
    If credentials are missing, health check returns 'needs_auth' rather than failing the run.
    """
    source_name = "kaggle"
    display_name = "Kaggle Competitions"
    base_url = "https://www.kaggle.com/api/v1/competitions/list"

    def __init__(self, timeout: int = 15):
        super().__init__(timeout=timeout)
        self.username = os.getenv("KAGGLE_USERNAME")
        self.key = os.getenv("KAGGLE_KEY")
        if self.username and self.key:
            self.session.auth = (self.username, self.key)

    def fetch_events(self) -> List[Dict[str, Any]]:
        if not (self.username and self.key):
            logger.info("[kaggle] KAGGLE_USERNAME or KAGGLE_KEY not set. Skipping live fetch.")
            return []

        try:
            resp = self.request(self.base_url)
            return resp.json()
        except Exception as e:
            logger.error(f"[kaggle] Error querying competitions: {e}")
            return []

    def parse_event(self, raw: Dict[str, Any]) -> HackathonEvent:
        comp_id = str(raw.get("id"))
        title = raw.get("title") or "Kaggle Competition"
        url = raw.get("url") or f"https://www.kaggle.com/competitions/{raw.get('ref', comp_id)}"
        
        deadline = parse_flexible_date(raw.get("deadline"))
        reward = raw.get("reward")
        prize_amount = None
        if reward and "$" in reward:
            try:
                prize_amount = float(reward.replace("$", "").replace(",", ""))
            except Exception:
                pass

        return HackathonEvent(
            source=self.source_name,
            source_event_id=comp_id,
            title=title,
            organizer=raw.get("organizationName") or "Kaggle",
            description=raw.get("description"),
            url=url,
            registration_url=url,
            location="Online",
            online=True,
            registration_deadline=deadline,
            prize_pool=reward or "Knowledge / Swag",
            prize_pool_amount=prize_amount,
            currency="USD",
            categories=["Data Science", "AI / ML"],
            tags=["Kaggle", "Data Science", "Competition"],
            status="open",
            raw_source_data=raw
        )

    def health_check(self) -> Tuple[bool, str]:
        if not (self.username and self.key):
            return True, "Requires KAGGLE_USERNAME & KAGGLE_KEY env vars"
        try:
            resp = self.request(f"{self.base_url}?page=1", retries=1)
            return True, "Healthy (Authenticated)"
        except Exception as e:
            return False, str(e)
