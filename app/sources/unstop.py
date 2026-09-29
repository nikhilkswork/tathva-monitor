from typing import List, Dict, Any, Tuple
import logging
import re
from app.sources.base import SourceAdapter
from app.models.hackathon import HackathonEvent, parse_flexible_date

logger = logging.getLogger("hackradar.sources.unstop")

class UnstopSourceAdapter(SourceAdapter):
    source_name = "unstop"
    display_name = "Unstop"
    base_url = "https://unstop.com/api/public/opportunity/search-result"

    def fetch_events(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}?opportunity=hackathons&per_page=25"
        resp = self.request(url)
        data = resp.json()
        if "data" in data and isinstance(data["data"], dict) and "data" in data["data"]:
            return data["data"]["data"]
        return []

    def parse_event(self, raw: Dict[str, Any]) -> HackathonEvent:
        event_id = str(raw.get("id"))
        title = raw.get("title") or "Unstop Hackathon"
        
        public_url = raw.get("public_url") or ""
        if public_url.startswith("http"):
            full_url = public_url
        else:
            full_url = f"https://unstop.com/{public_url.lstrip('/')}"

        # Organizer
        org_obj = raw.get("organisation") or {}
        organizer = org_obj.get("name") if isinstance(org_obj, dict) else "Unstop Host"

        # Details/Description: clean HTML tags
        details_html = raw.get("details") or ""
        clean_desc = re.sub(r"<[^>]+>", " ", details_html)
        clean_desc = re.sub(r"\s+", " ", clean_desc).strip()[:500]

        # Region & Location
        region = (raw.get("region") or "").lower()
        is_online = region == "online"
        
        locations = raw.get("locations") or []
        loc_str = "Online" if is_online else (", ".join(locations) if locations else "India (In-Person)")

        # Dates
        end_date = parse_flexible_date(raw.get("end_date"))
        reg_end_date = parse_flexible_date(raw.get("regn_end_date") or raw.get("end_date"))

        # Prize calculation
        prizes = raw.get("prizes") or []
        prize_amount = 0.0
        currency = "INR"
        for p in prizes:
            if isinstance(p, dict) and p.get("cash"):
                try:
                    cash_val = float(p.get("cash"))
                    prize_amount = max(prize_amount, cash_val)
                    if p.get("currency") in ("USD", "$"):
                        currency = "USD"
                except Exception:
                    pass
        
        prize_str = f"₹{prize_amount:,.0f}" if prize_amount > 0 and currency == "INR" else (
            f"${prize_amount:,.0f}" if prize_amount > 0 else "Recognition & Certificates"
        )

        # Filters / Tags
        filters = raw.get("filters") or []
        tag_names = [f.get("name") for f in filters if isinstance(f, dict) and f.get("name")]
        categories = ["General"]
        for t in tag_names + [title]:
            tlow = t.lower()
            if "ai" in tlow or "data" in tlow or "machine learning" in tlow:
                categories.append("AI / ML")
            if "web" in tlow:
                categories.append("Web Development")
            if "app" in tlow or "mobile" in tlow:
                categories.append("App Development")
            if "engineering" in tlow or "coding" in tlow:
                categories.append("General")

        img = raw.get("logoUrl2") or raw.get("thumb")

        return HackathonEvent(
            source=self.source_name,
            source_event_id=event_id,
            title=title,
            organizer=organizer,
            description=clean_desc,
            url=full_url,
            registration_url=full_url,
            image_url=img,
            location=loc_str,
            country="India" if not is_online else None,
            online=is_online,
            hybrid=False,
            end_datetime=end_date,
            registration_deadline=reg_end_date,
            prize_pool=prize_str,
            prize_pool_amount=prize_amount if prize_amount > 0 else None,
            currency=currency,
            categories=list(set(categories)),
            tags=tag_names + ["Unstop"],
            status="open",
            raw_source_data=raw
        )

    def health_check(self) -> Tuple[bool, str]:
        try:
            url = f"{self.base_url}?opportunity=hackathons&per_page=1"
            resp = self.request(url, retries=1)
            data = resp.json()
            items = data.get("data", {}).get("data", [])
            return True, f"Healthy ({len(items)} sample items returned)"
        except Exception as e:
            return False, str(e)
