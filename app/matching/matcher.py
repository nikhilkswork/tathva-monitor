import re
from typing import List, Tuple, Dict, Any
from app.models.hackathon import HackathonEvent
from app.database.schema import User, UserPreference

# Category synonyms and keyword mapping for robust semantic matching
CATEGORY_KEYWORDS = {
    "AI / ML": [
        "ai", "ml", "machine learning", "artificial intelligence", "deep learning",
        "genai", "generative ai", "llm", "neural", "computer vision", "nlp", "data science"
    ],
    "Web Development": [
        "web", "frontend", "backend", "full stack", "fullstack", "react", "next.js",
        "node", "vue", "angular", "javascript", "typescript", "html", "css", "django", "flask"
    ],
    "App Development": [
        "app", "mobile", "android", "ios", "flutter", "react native", "swift", "kotlin"
    ],
    "Cybersecurity": [
        "cyber", "security", "infosec", "forensics", "cryptography", "hacking", "ctf"
    ],
    "Blockchain": [
        "blockchain", "web3", "crypto", "defi", "solidity", "ethereum", "smart contract", "nft"
    ],
    "IoT": [
        "iot", "internet of things", "embedded", "sensors", "arduino", "raspberry pi"
    ],
    "Robotics": [
        "robot", "robotics", "robowars", "drone", "autonomous", "mechatronics", "bot"
    ],
    "Cloud": [
        "cloud", "aws", "azure", "gcp", "devops", "docker", "kubernetes", "serverless"
    ],
    "Data Science": [
        "data science", "data analytics", "data mining", "pandas", "analytics", "big data"
    ],
    "Open Source": [
        "open source", "opensource", "foss", "github", "git"
    ],
    "Hardware": [
        "hardware", "pcb", "electronics", "3d printing", "cad", "vlsi", "fpga"
    ],
    "Game Development": [
        "game", "gaming", "unity", "unreal", "godot", "game dev"
    ],
    "General": [
        "hackathon", "innovation", "code", "tech", "competition", "development"
    ]
}

INDIAN_STATES = [
    "kerala", "karnataka", "tamil nadu", "maharashtra", "delhi", "telangana",
    "andhra pradesh", "gujarat", "west bengal", "uttar pradesh", "rajasthan",
    "punjab", "haryana", "bihar", "madhya pradesh"
]

INDIAN_CITIES = [
    "bangalore", "bengaluru", "mumbai", "delhi", "new delhi", "hyderabad",
    "chennai", "kolkata", "pune", "kochi", "cochin", "calicut", "kozhikode",
    "trivandrum", "thiruvananthapuram", "noida", "gurgaon", "gurugram", "ahmedabad"
]


def match_location(pref_locations: List[str], event: HackathonEvent) -> Tuple[bool, str]:
    """Check if event matches user location preference"""
    if not pref_locations or "Anywhere" in pref_locations:
        return True, "Location: Anywhere"

    # Online match
    if event.online and ("Online" in pref_locations or "Anywhere" in pref_locations):
        return True, "Mode/Location: Online"

    # Normalize event location strings
    loc_text = " ".join(filter(None, [
        event.location or "",
        event.city or "",
        event.state or "",
        event.country or "",
        event.title or ""
    ])).lower()

    for target in pref_locations:
        t_low = target.lower().strip()
        if t_low == "anywhere":
            return True, "Location: Anywhere"
        if t_low == "online" and event.online:
            return True, "Location: Online"
        if t_low == "india":
            if event.country and "india" in event.country.lower():
                return True, "Location: India"
            if any(st in loc_text for st in INDIAN_STATES) or any(ct in loc_text for ct in INDIAN_CITIES):
                return True, "Location: India"
        elif t_low == "international":
            # If not India and not empty
            is_india = (event.country and "india" in event.country.lower()) or any(st in loc_text for st in INDIAN_STATES)
            if not is_india and not event.online and loc_text.strip():
                return True, "Location: International"
        else:
            # Exact or substring match for state/city
            if t_low in loc_text:
                return True, f"Location match: {target}"

    return False, "Location does not match"


def match_mode(pref_modes: List[str], event: HackathonEvent) -> Tuple[bool, str]:
    """Check if event mode matches user preferred modes"""
    if not pref_modes:
        return True, "Mode: any"

    if event.hybrid and "Hybrid" in pref_modes:
        return True, "Mode: Hybrid"
    if event.online and "Online" in pref_modes:
        return True, "Mode: Online"
    if not event.online and "Offline" in pref_modes:
        return True, "Mode: Offline"

    return False, "Mode does not match"


def match_category(pref_categories: List[str], event: HackathonEvent) -> Tuple[bool, str]:
    """Check if event matches user preferred categories"""
    if not pref_categories or "General" in pref_categories:
        return True, "Category: General"

    event_text = " ".join([
        event.title.lower(),
        (event.description or "").lower(),
        " ".join([c.lower() for c in event.categories]),
        " ".join([t.lower() for t in event.technologies]),
        " ".join([tag.lower() for tag in event.tags])
    ])

    for cat in pref_categories:
        if cat == "General":
            return True, "Category: General"
        
        keywords = CATEGORY_KEYWORDS.get(cat, [cat.lower()])
        for kw in keywords:
            # Use word boundary or direct search
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, event_text, re.IGNORECASE):
                return True, f"Category match: {cat} (via '{kw}')"

    return False, "Category does not match"


def match_prize(min_prize: float, event: HackathonEvent) -> Tuple[bool, str]:
    """Check if event meets minimum prize requirement"""
    if min_prize <= 0:
        return True, "Prize: no minimum requirement"

    if event.prize_pool_amount is not None:
        if event.prize_pool_amount >= min_prize:
            return True, f"Prize: {event.prize_pool_amount} >= {min_prize}"
        return False, f"Prize: {event.prize_pool_amount} < {min_prize}"

    # If event has no prize info and user asked for min prize, do not match
    return False, "Prize information missing or 0"


def match_user_preference(user: User, event: HackathonEvent) -> Tuple[bool, List[str]]:
    """
    Evaluate all preference criteria for a user against an event.
    Returns: (is_match, reasons)
    """
    if not user.is_active:
        return False, ["User paused alerts"]

    pref = user.preferences
    if not pref:
        # Default match everything
        return True, ["Default preferences"]

    reasons = []

    # 1. Mode Match
    mode_ok, mode_reason = match_mode(pref.modes, event)
    if not mode_ok:
        return False, [mode_reason]
    reasons.append(mode_reason)

    # 2. Location Match
    loc_ok, loc_reason = match_location(pref.locations, event)
    if not loc_ok:
        return False, [loc_reason]
    reasons.append(loc_reason)

    # 3. Category Match
    cat_ok, cat_reason = match_category(pref.categories, event)
    if not cat_ok:
        return False, [cat_reason]
    reasons.append(cat_reason)

    # 4. Prize Match
    prize_ok, prize_reason = match_prize(pref.min_prize_pool or 0.0, event)
    if not prize_ok:
        return False, [prize_reason]
    reasons.append(prize_reason)

    return True, reasons
