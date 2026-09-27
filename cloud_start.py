import time

from tathva import get_workshops

from database import create_database
from database import get_known_workshop_ids
from database import save_workshop

from monitor import check_workshops


def initialize_database():

    create_database()

    known_ids = get_known_workshop_ids()

    if known_ids:

        print("Database already initialized.")

        return

    print("First startup detected.")
    print("Loading existing Tathva workshops...")
    print("These workshops will NOT trigger notifications.")

    workshops = get_workshops()

    for workshop in workshops:

        save_workshop(workshop)

    print(f"Saved {len(workshops)} existing workshops.")


initialize_database()


print("🚀 Tathva cloud monitor started.")


while True:

    try:

        print("Checking Tathva...")

        check_workshops()

        print("Waiting 5 minutes...")

    except Exception as error:

        print("ERROR:", error)

    time.sleep(300)