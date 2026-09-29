from typing import List, Dict, Any, Tuple, Optional
import json
import logging
import re
from bs4 import BeautifulSoup
from app.sources.base import SourceAdapter
from app.models.hackathon import HackathonEvent, parse_flexible_date, extract_prize_amount

logger = logging.getLogger("hackradar.sources.generic")

class GenericSourceAdapter(SourceAdapter):
    """
    Generic source adapter capable of extracting hackathons and events from arbitrary websites
    using JSON-LD (@type: Event), OpenGraph tags, and semantic HTML elements.
    """
    source_name = "generic"
    display_name = "Generic Event Website"
    base_url = "https://example.com"

    def __init__(self, target_url: Optional[str] = None, timeout: int = 15):
        super().__init__(timeout=timeout)
        if target_url:
            self.base_url = target_url

    def fetch_events(self) -> List[Dict[str, Any]]:
        if not self.base_url or "example.com" in self.base_url:
            return []
        resp = self.request(self.base_url)
        return self.extract_from_html(resp.text, self.base_url)

    def extract_from_html(self, html_text: str, source_url: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html_text, "html.parser")
        events: List[Dict[str, Any]] = []

        # 1. Look for JSON-LD scripts with Event schema
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                if not script.string:
                    continue
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    # Look inside @graph if present
                    if "@graph" in item and isinstance(item["@graph"], list):
                        items.extend(item["@graph"])

                    item_type = item.get("@type")
                    if item_type and ("Event" in item_type or item_type == "Hackathon"):
                        events.append({
                            "_type": "json-ld",
                            "source_url": source_url,
                            "raw": item
                        })
            except Exception as e:
                logger.debug(f"[generic] JSON-LD parse error: {e}")

        # 2. If no JSON-LD events, check OpenGraph metadata for single event page
        if not events:
            og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "og:title"})
            if og_title and og_title.get("content"):
                og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "og:description"})
                og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
                og_url = soup.find("meta", property="og:url") or soup.find("meta", attrs={"name": "og:url"})

                # Check if page looks like a hackathon / event
                page_title = og_title.get("content", "")
                text_corpus = (page_title + " " + (og_desc.get("content", "") if og_desc else "")).lower()
                if any(w in text_corpus for w in ["hackathon", "challenge", "competition", "workshop"]):
                    events.append({
                        "_type": "opengraph",
                        "source_url": source_url,
                        "raw": {
                            "title": page_title,
                            "description": og_desc.get("content") if og_desc else None,
                            "image": og_image.get("content") if og_image else None,
                            "url": og_url.get("content") if og_url else source_url
                        }
                    })

        return events

    def parse_event(self, raw: Dict[str, Any]) -> HackathonEvent:
        data_type = raw.get("_type")
        source_url = raw.get("source_url", self.base_url)
        content = raw.get("raw", {})

        if data_type == "json-ld":
            title = content.get("name") or "Extracted Event"
            desc = content.get("description") or ""
            url = content.get("url") or source_url
            start_dt = parse_flexible_date(content.get("startDate"))
            end_dt = parse_flexible_date(content.get("endDate"))

            # Location extraction
            location_val = content.get("location")
            loc_str = "Online"
            is_online = False
            city = None
            country = None
            if isinstance(location_val, dict):
                loc_type = location_val.get("@type", "")
                if "Virtual" in loc_type or "online" in str(location_val).lower():
                    is_online = True
                    loc_str = "Online"
                else:
                    addr = location_val.get("address")
                    if isinstance(addr, dict):
                        city = addr.get("addressLocality")
                        country = addr.get("addressCountry")
                    loc_str = location_val.get("name") or (f"{city}, {country}" if city else "In-Person")
            elif isinstance(location_val, str):
                loc_str = location_val
                is_online = "online" in loc_str.lower()

            # Image
            img = content.get("image")
            if isinstance(img, list) and img:
                img = img[0]
            elif isinstance(img, dict):
                img = img.get("url")

            # ID
            event_id = str(content.get("@id") or content.get("identifier") or url)

            return HackathonEvent(
                source=self.source_name,
                source_event_id=event_id,
                title=title,
                organizer=content.get("organizer", {}).get("name") if isinstance(content.get("organizer"), dict) else "Event Organizer",
                description=desc[:500] if desc else None,
                url=url,
                registration_url=url,
                image_url=img if isinstance(img, str) else None,
                location=loc_str,
                country=country,
                city=city,
                online=is_online,
                hybrid=False,
                start_datetime=start_dt,
                end_datetime=end_dt,
                registration_deadline=start_dt,
                categories=["General"],
                tags=["Generic-JSONLD"],
                status="open",
                raw_source_data=raw
            )
        else:
            # OpenGraph extraction
            title = content.get("title") or "Generic Hackathon"
            desc = content.get("description") or ""
            url = content.get("url") or source_url
            img = content.get("image")

            return HackathonEvent(
                source=self.source_name,
                source_event_id=url,
                title=title,
                organizer="Website Host",
                description=desc[:500] if desc else None,
                url=url,
                registration_url=url,
                image_url=img,
                location="See website",
                online=False,
                hybrid=False,
                categories=["General"],
                tags=["Generic-OpenGraph"],
                status="open",
                raw_source_data=raw
            )

    def health_check(self) -> Tuple[bool, str]:
        if not self.base_url or self.base_url == "https://example.com":
            return True, "Ready for custom target URL"
        return super().health_check()
