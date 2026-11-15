"""Validate and summarize manually maintained events without inventing forecasts."""
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def validate(events):
    ids = set()
    for event in events:
        for key in ("id", "date", "indicator", "category"):
            if not event.get(key):
                raise ValueError(f"Missing {key}: {event!r}")
        if event["id"] in ids:
            raise ValueError(f'Duplicate id: {event["id"]}')
        ids.add(event["id"])
        datetime.strptime(event["date"], "%Y-%m-%d")
        if event.get("time"):
            datetime.strptime(event["time"], "%H:%M")
        if event["category"] not in ("macro", "earnings"):
            raise ValueError("Unknown category")
        if event.get("forecast") is not None and not event.get("unit"):
            raise ValueError("Forecast requires explicit unit")
    return Counter(e["category"] for e in events)

def render(events):
    counts = validate(events)
    lines = ["# Upcoming economic releases and earnings", "",
             f'{len(events)} user-supplied, unverified events ({counts["macro"]} macro; {counts["earnings"]} earnings).',
             "Forecasts are not supplied. Confirm dates with official calendars before trading.", ""]
    for e in sorted(events, key=lambda x:(x["date"], x.get("time") or "99:99", x["indicator"])):
        clock = e.get("time") or (e.get("session") or "time TBD").replace("_", " ")
        lines.append(f'- {e["date"]} {clock} ET — {e["indicator"]} ({e["category"]})')
    return "\n".join(lines)+"\n"

def main():
    events = json.loads((ROOT/"releases.json").read_text())
    (ROOT/"upcoming_calendar.md").write_text(render(events))
    print(f"Validated {len(events)} events; wrote upcoming_calendar.md")

if __name__ == "__main__":
    main()
