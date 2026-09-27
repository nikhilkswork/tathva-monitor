import json
from pathlib import Path

DATABASE_FILE = Path("known_workshops.json")


def get_known_workshop_ids():
    if not DATABASE_FILE.exists():
        return set()

    with open(DATABASE_FILE, "r") as file:
        data = json.load(file)

    return set(data)


def save_workshop_ids(ids):
    with open(DATABASE_FILE, "w") as file:
        json.dump(sorted(list(ids)), file, indent=2)