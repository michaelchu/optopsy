"""Use FXMacroData release-calendar events in options research.

The example keeps the dependency footprint small by using only the Python
standard library. The public USD calendar endpoint returns scheduled macro
events with market-tier metadata that can be joined to option quote dates.
"""

import json
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen


BASE_URL = "https://fxmacrodata.com/api/v1/calendar/{currency}"


def fetch_calendar(currency="USD", start_date=None, end_date=None, timeout=20):
    today = date.today()
    start_date = start_date or today.isoformat()
    end_date = end_date or (today + timedelta(days=30)).isoformat()
    query = urlencode({"start_date": start_date, "end_date": end_date})

    with urlopen(f"{BASE_URL.format(currency=currency)}?{query}", timeout=timeout) as response:
        payload = json.load(response)

    return payload.get("data", [])


def top_tier_event_dates(events):
    dates = set()
    for event in events:
        if event.get("top_tier_for_currency") or event.get("market_tier") == 1:
            event_time = event.get("announcement_datetime_utc") or event.get("announcement_datetime_local")
            dates.add((event_time or event.get("date", ""))[:10])
    return sorted(item for item in dates if item)


def main():
    events = fetch_calendar(start_date="2026-07-01", end_date="2026-07-20")
    print("Top-tier USD release dates for event-window analysis:")
    for event_date in top_tier_event_dates(events):
        print(f"- {event_date}")


if __name__ == "__main__":
    main()
