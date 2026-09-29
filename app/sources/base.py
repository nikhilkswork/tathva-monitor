from abc import ABC, abstractmethod
import logging
from typing import List, Dict, Any, Tuple, Optional
import requests
from app.config import settings
from app.models.hackathon import HackathonEvent

logger = logging.getLogger("hackradar.sources")

class SourceAdapter(ABC):
    """
    Abstract base class for all hackathon/event source adapters.
    Each adapter encapsulates fetching, parsing, normalizing, and health checks.
    """
    source_name: str = "base"
    display_name: str = "Base Source"
    base_url: str = ""

    def __init__(self, timeout: int = settings.REQUEST_TIMEOUT):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.USER_AGENT,
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        retries: int = 2
    ) -> requests.Response:
        """Robust request wrapper with retries and timeout"""
        merged_headers = dict(self.session.headers)
        if headers:
            merged_headers.update(headers)

        last_exc = None
        for attempt in range(retries + 1):
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    headers=merged_headers,
                    params=params,
                    data=data,
                    timeout=self.timeout
                )
                resp.raise_for_status()
                return resp
            except Exception as e:
                last_exc = e
                logger.warning(
                    f"[{self.source_name}] Attempt {attempt + 1}/{retries + 1} failed for {url}: {e}"
                )
        raise last_exc

    @abstractmethod
    def fetch_events(self) -> List[Dict[str, Any]]:
        """Fetch raw event items from the source."""
        pass

    @abstractmethod
    def parse_event(self, raw_data: Dict[str, Any]) -> HackathonEvent:
        """Parse raw event dict into a normalized HackathonEvent."""
        pass

    def normalize_event(self, raw_data: Dict[str, Any]) -> HackathonEvent:
        """Wrapper around parse_event to ensure consistent normalization."""
        return self.parse_event(raw_data)

    def health_check(self) -> Tuple[bool, str]:
        """Perform a quick health check on the source."""
        try:
            resp = self.request(self.base_url, retries=1)
            if resp.status_code in (200, 204):
                return True, "Healthy"
            return False, f"Unexpected HTTP status {resp.status_code}"
        except Exception as e:
            return False, str(e)
