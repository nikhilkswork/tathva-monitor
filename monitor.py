from tathva import get_workshops
from database import get_known_workshop_ids, save_workshop_ids
from telegram import send_message


def create_notification(workshop):
    message = f"""
🚨 NEW TATHVA WORKSHOP

🎓 {workshop["heading"]}

📅 {workshop["datetime"]}

💰 ₹{workshop["price"] / 100:.0f}

📍 {workshop["venue"]["name"]}

🆔 Workshop ID: {workshop["id"]}
"""

    return message.strip()


def check_workshops():

    print("1️⃣ Starting check...", flush=True)

    workshops = get_workshops()

    print(f"2️⃣ Tathva returned {len(workshops)} workshops", flush=True)

    known_ids = get_known_workshop_ids()

    print(f"3️⃣ Known workshop IDs: {len(known_ids)}", flush=True)

    current_ids = set()
    new_workshops = []

    for workshop in workshops:

        workshop_id = workshop["id"]

        current_ids.add(workshop_id)

        if workshop_id not in known_ids:
            new_workshops.append(workshop)

    print(f"4️⃣ New workshops found: {len(new_workshops)}", flush=True)

    for workshop in new_workshops:

        print(
            f"🆕 NEW WORKSHOP: {workshop['heading']}",
            flush=True
        )

        message = create_notification(workshop)

        send_message(message)

        print("✅ Telegram notification sent.", flush=True)

    updated_ids = known_ids | current_ids

    save_workshop_ids(updated_ids)

    print(
        f"5️⃣ Saved {len(updated_ids)} workshop IDs",
        flush=True
    )

    if not new_workshops:
        print("✅ No new workshops.", flush=True)


if __name__ == "__main__":

    print("🚀 Monitor started", flush=True)

    try:
        check_workshops()

    except Exception as error:

        print("❌ ERROR:", error, flush=True)
        raise

    print("🏁 Monitor finished", flush=True)
    