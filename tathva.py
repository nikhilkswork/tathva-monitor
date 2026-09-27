import requests

API_URL = " https://api.tathva.org/api/events/all?type=workshops"


def get_workshops():
    response = requests.get(API_URL, timeout=20)
    response.raise_for_status()

    data = response.json()

    return data["events"]


if __name__ == "__main__":
    workshops = get_workshops()

    for workshop in workshops:
        print(workshop["id"], "→", workshop["heading"])