"""Fetch today's U.S. economic releases from agency calendars."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from icalendar import Calendar
import requests

from overnight_digest import TZ

LOG = logging.getLogger(__name__)


def bls_events(content, day, url):
    events = Calendar.from_ical(content).walk("VEVENT")
    if not events:
        raise ValueError("BLS calendar contains no events")
    for event in events:
        start = event.decoded("DTSTART")
        if isinstance(start, datetime):
            start = start.astimezone(TZ) if start.tzinfo else start.replace(tzinfo=TZ)
            if start.date() == day:
                yield start.time(), str(event["SUMMARY"]), url


def bea_events(content, day, url):
    table = BeautifulSoup(content, "html.parser").select_one("#release-schedule-table")
    if table is None or str(day.year) not in table.th.get_text():
        raise ValueError(f"BEA schedule for {day.year} unavailable")
    for row in table.select("tbody tr"):
        date = row.select_one(".release-date")
        if date is not None and date.get_text(strip=True) == f"{day:%B} {day.day}":
            clock = datetime.strptime(row.select_one("small").get_text(strip=True), "%I:%M %p").time()
            title = row.select_one(".release-title").get_text(" ", strip=True)
            yield clock, title, url


def census_events(content, day, url):
    rows = BeautifulSoup(content, "html.parser").select("#calendar td[sorttable_customkey]")
    if not rows:
        raise ValueError("Census release table missing or empty")
    for date in rows:
        key = date["sorttable_customkey"]
        if key.startswith(day.strftime("%Y%m%d")):
            clock = datetime.strptime(key[8:], "%H%M").time()
            title = date.find_previous_sibling("td").get_text(" ", strip=True)
            yield clock, title, url


def fetch_calendar(source, day):
    name, url, parser = source
    try:
        response = requests.get(url, timeout=(8, 20), headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        return list(parser(response.content, day, url)), None
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError) as exc:
        LOG.warning("%s calendar unavailable: %s", name, exc)
        return [], name


def render_today(day):
    sources = [
        ("BLS", "https://www.bls.gov/schedule/news_release/bls.ics", bls_events),
        ("BEA", "https://www.bea.gov/news/schedule", bea_events),
        ("Census", urljoin("https://www.census.gov/economic-indicators/",
                           f"calendar-listview-{day.year}.html"), census_events),
    ]
    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        results = list(pool.map(lambda source: fetch_calendar(source, day), sources))
    events = sorted({event for items, _ in results for event in items})
    unavailable = [name for _, name in results if name]
    lines = ["## Today's U.S. economic releases", ""]
    for clock, title, url in events:
        lines.append(f"- {clock:%I:%M %p} ET — {title} ({url})")
    if not events and len(unavailable) < len(sources):
        lines.append("No releases scheduled on the agency calendars that responded.")
    if unavailable:
        lines.append(f"Calendar coverage incomplete. Unavailable: {', '.join(unavailable)}.")
    lines.append("Coverage: BLS, BEA, and Census Bureau.")
    return "\n".join(lines) + "\n"
