from tathva import get_workshops
from database import save_workshop_ids


workshops = get_workshops()

ids = {workshop["id"] for workshop in workshops}

save_workshop_ids(ids)

print(f"Saved {len(ids)} existing workshops.")
print("These workshops will NOT trigger notifications.")