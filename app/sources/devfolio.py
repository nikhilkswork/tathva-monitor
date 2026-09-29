from typing import List, Dict, Any, Tuple
import logging
from app.sources.base import SourceAdapter
from app.models.hackathon import HackathonEvent, parse_flexible_date

logger = logging.getLogger("hackradar.sources.devfolio")

class DevfolioSourceAdapter(SourceAdapter):
    source_name = "devfolio"
    display_name = "Devfolio"
    base_url = "https://api.devfolio.co/api/hackathons"

    def fetch_events(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}?filter=all&page=1&limit=25"
        resp = self.request(url)
        data = resp.json()
        return data.get("result", [])

    def parse_event(self, raw: Dict[str, Any]) -> HackathonEvent:
        uuid = str(raw.get("uuid"))
        slug = raw.get("slug") or uuid
        title = raw.get("name") or "Devfolio Hackathon"
        
        setting = raw.get("hackathon_setting") or {}
        site_url = setting.get("site") or f"https://{slug}.devfolio.co"

        # Dates
        starts_at = parse_flexible_date(raw.get("starts_at"))
        ends_at = parse_flexible_date(raw.get("ends_at"))
        reg_ends_at = parse_flexible_date(setting.get("reg_ends_at"))

        # Location
        is_online = bool(raw.get("is_online", False))
        city = raw.get("city")
        state = raw.get("state")
        country = raw.get("country") or ("India" if not is_online and (city or state) else None)
        raw_location = raw.get("location")
        
        if is_online:
            loc_str = "Online"
        else:
            loc_parts = [p for p in [city, state, country] if p]
            loc_str = ", ".join(loc_parts) if loc_parts else (raw_location or "In-Person")

        # Themes & Categories
        themes = raw.get("themes") or []
        theme_names = [t.get("name") for t in themes if isinstance(t, dict) and t.get("name")]
        
        categories = ["General"]
        for tname in theme_names:
            tlow = tname.lower()
            if "ai" in tlow or "machine learning" in tlow:
                categories.append("AI / ML")
            elif "web" in tlow or "full stack" in tlow:
                categories.append("Web Development")
            elif "app" in tlow or "mobile" in tlow:
                categories.append("App Development")
            elif "blockchain" in tlow or "web3" in tlow or "crypto" in tlow:
                categories.append("Blockchain")
            elif "iot" in tlow:
                categories.append("IoT")
            elif "cloud" in tlow:
                categories.append("Cloud")
            elif "security" in tlow:
                categories.append("Cybersecurity")
            elif "game" in tlow:
                categories.append("Game Development")
            else:
                categories.append(tname)

        # Image
        img = raw.get("cover_img") or setting.get("logo")

        return HackathonEvent(
            source=self.source_name,
            source_event_id=uuid,
            title=title,
            organizer=setting.get("subdomain") or "Devfolio Community",
            description=f"Hackathon hosted on Devfolio. Themes: {', '.join(theme_names) if theme_names else 'Open Innovation'}",
            url=site_url,
            registration_url=site_url,
            image_url=img,
            location=loc_str,
            country=country,
            state=state,
            city=city,
            online=is_online,
            hybrid=False,
            start_datetime=starts_at,
            end_datetime=ends_at,
            registration_deadline=reg_ends_at,
            categories=list(set(categories)),
            tags=theme_names + ["Devfolio"],
            status="open",
            raw_source_data=raw
        )

    def health_check(self) -> Tuple[bool, str]:
        try:
            url = f"{self.base_url}?filter=all&page=1&limit=1"
            resp = self.request(url, retries=1)
            data = resp.json()
            count = data.get("count", 0)
            return True, f"Healthy ({count} hackathons on platform)"
        except Exception as e:
            return False, str(e)
