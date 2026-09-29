from typing import List, Dict, Any, Tuple
import logging
from bs4 import BeautifulSoup
from app.sources.base import SourceAdapter
from app.models.hackathon import HackathonEvent, parse_flexible_date

logger = logging.getLogger("hackradar.sources.mlh")

class MLHSourceAdapter(SourceAdapter):
    source_name = "mlh"
    display_name = "Major League Hacking (MLH)"
    base_url = "https://mlh.io/seasons/2026/events"

    def fetch_events(self) -> List[Dict[str, Any]]:
        resp = self.request(self.base_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        event_nodes = soup.find_all(attrs={"itemtype": lambda v: v and "Event" in v})
        results = []
        for node in event_nodes:
            item = {}
            # URL
            url = node.get("href")
            meta_url = node.find("meta", attrs={"itemprop": "url"})
            if meta_url and meta_url.get("content"):
                url = meta_url.get("content")
            item["url"] = url

            # Attendance mode (Online / Offline)
            mode_meta = node.find("meta", attrs={"itemprop": "eventAttendanceMode"})
            item["attendance_mode"] = mode_meta.get("content") if mode_meta else ""

            # Name / Title: Check headings inside or itemprop="name"
            h3 = node.find("h3")
            if h3:
                item["title"] = h3.text.strip()
            else:
                name_tag = node.find(attrs={"itemprop": "name"})
                item["title"] = name_tag.text.strip() if name_tag else "MLH Hackathon"

            # Dates
            start_meta = node.find("meta", attrs={"itemprop": "startDate"})
            if start_meta:
                item["startDate"] = start_meta.get("content")
            end_meta = node.find("meta", attrs={"itemprop": "endDate"})
            if end_meta:
                item["endDate"] = end_meta.get("content")

            # Location details
            loc_tag = node.find(attrs={"itemprop": "location"})
            item["location_text"] = loc_tag.text.strip() if loc_tag else ""
            
            locality = node.find(attrs={"itemprop": "addressLocality"})
            item["city"] = locality.text.strip() if locality else ""

            region = node.find(attrs={"itemprop": "addressRegion"})
            item["state"] = region.text.strip() if region else ""

            country_node = node.find(attrs={"itemprop": "addressCountry"})
            item["country"] = (country_node.get("content") or country_node.text.strip()) if country_node else ""

            # Image
            img = node.find("img")
            if img:
                item["image_url"] = img.get("src")

            if item.get("url"):
                results.append(item)

        return results

    def parse_event(self, raw: Dict[str, Any]) -> HackathonEvent:
        url = raw.get("url") or "https://mlh.io"
        title = raw.get("title") or "MLH Hackathon"
        
        # Derive stable event id from URL
        event_id = url.split("?")[0].rstrip("/").split("/")[-1]

        start_dt = parse_flexible_date(raw.get("startDate"))
        end_dt = parse_flexible_date(raw.get("endDate"))

        attendance = raw.get("attendance_mode", "").lower()
        is_online = "online" in attendance

        city = raw.get("city")
        state = raw.get("state")
        country = raw.get("country")
        
        loc_parts = [p for p in [city, state, country] if p]
        loc_str = "Online" if is_online else (", ".join(loc_parts) if loc_parts else (raw.get("location_text") or "In-Person"))

        return HackathonEvent(
            source=self.source_name,
            source_event_id=event_id,
            title=title,
            organizer="Major League Hacking (MLH)",
            description=f"Official MLH Member Hackathon ({loc_str})",
            url=url,
            registration_url=url,
            image_url=raw.get("image_url"),
            location=loc_str,
            country=country or ("International" if not is_online else None),
            state=state,
            city=city,
            online=is_online,
            hybrid=False,
            start_datetime=start_dt,
            end_datetime=end_dt,
            registration_deadline=start_dt,
            prize_pool="Swag & Sponsor Prizes",
            currency="USD",
            categories=["General", "Open Source"],
            tags=["MLH", "Student Hackathon"],
            status="open",
            raw_source_data=raw
        )

    def health_check(self) -> Tuple[bool, str]:
        try:
            resp = self.request(self.base_url, retries=1)
            soup = BeautifulSoup(resp.text, "html.parser")
            count = len(soup.find_all(attrs={"itemtype": lambda v: v and "Event" in v}))
            return True, f"Healthy ({count} events parsed)"
        except Exception as e:
            return False, str(e)
