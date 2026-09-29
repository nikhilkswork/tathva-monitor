from typing import List, Dict, Any, Tuple
import logging
from app.sources.base import SourceAdapter
from app.models.hackathon import HackathonEvent

logger = logging.getLogger("hackradar.sources.hack2skill")

class Hack2SkillSourceAdapter(SourceAdapter):
    """
    Hack2skill adapter.
    Note: Hack2skill relies on a dynamic client-rendered SPA protected by Google reCAPTCHA.
    Standard HTTP scrapers cannot extract events without executing the client bundle or
    running headless browser automation. Rather than inventing fake data or attempting to bypass
    anti-bot protections, this adapter records its degraded state and provides headless hooks.
    """
    source_name = "hack2skill"
    display_name = "Hack2skill"
    base_url = "https://hack2skill.com"

    def fetch_events(self) -> List[Dict[str, Any]]:
        # Checked via health_check / status
        logger.info(
            "[hack2skill] Platform requires headless browser / reCAPTCHA clearance. No direct public API available."
        )
        return []

    def parse_event(self, raw: Dict[str, Any]) -> HackathonEvent:
        raise NotImplementedError("Hack2skill parsing requires dynamic browser rendering.")

    def health_check(self) -> Tuple[bool, str]:
        try:
            resp = self.request(self.base_url, retries=1)
            if resp.status_code == 200:
                return True, "Reachable (SPA client-side bundle; requires browser automation / official API key)"
            return False, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, str(e)
