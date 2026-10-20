"""Use FXMacroData release-calendar events in options research.

The example keeps the dependency footprint small by using only the Python
standard library. The public USD calendar endpoint returns scheduled macro
events with market-tier metadata that can be joined to option quote dates.
"""

import json
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen


BASE_URL = "https://api.fxmacrodata.com/v1/calendar/{currency}"


def fetch_calendar(currency="USD", start_date=None, end_date=None, timeout=20):
    today = date.today()
    start_date = start_date or today.isoformat()
    end_date = end_date or (today + timedelta(days=30)).isoformat()
    query = urlencode({"start_date": start_date, "end_date": end_date})

    with urlopen(f"{BASE_URL.format(currency=currency)}?{query}", timeout=timeout) as response:
        payload = json.load(response)

    events = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        raise ValueError("Unexpected FXMacroData calendar response: no data list")
    return events


def _event_date_utc(event):
    for field in (
        "announcement_datetime_utc",
        "announcement_datetime",
        "announcement_datetime_local",
    ):
        value = event.get(field)
        if value is None or value == "" or isinstance(value, bool):
            continue
        try:
            if isinstance(value, (int, float)) or (
                isinstance(value, str) and value.strip().lstrip("-").isdigit()
            ):
                timestamp = datetime.fromtimestamp(float(value), tz=timezone.utc)
            else:
                timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    continue
            return timestamp.astimezone(timezone.utc).date().isoformat()
        except (ValueError, TypeError, OverflowError, OSError):
            continue
    return None


def top_tier_event_dates(events):
    """Return UTC release dates; skip events without a usable event timestamp."""
    dates = set()
    for event in events:
        if event.get("top_tier_for_currency") or event.get("market_tier") == 1:
            event_date = _event_date_utc(event)
            if event_date is not None:
                dates.add(event_date)
    return sorted(dates)


def main():
    events = fetch_calendar(start_date="2026-07-01", end_date="2026-07-20")
    print("Top-tier USD release dates for event-window analysis:")
    for event_date in top_tier_event_dates(events):
        print(f"- {event_date}")


if __name__ == "__main__":
    main()
