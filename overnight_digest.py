"""Source-linked overnight headlines, 20:00–07:00 America/New_York."""
import json
import logging
import re
from datetime import datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo
import requests

TZ = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parent
QUERIES = {
    "Macro and central banks": "Federal Reserve inflation economic data central bank",
    "Global markets": "Asia stocks Europe markets US stock futures treasury dollar",
    "Geopolitics and policy": "geopolitics tariffs sanctions trade markets",
    "Companies and earnings": "earnings guidance merger acquisition stocks after hours",
}
LOG = logging.getLogger("overnight")

def window(now=None):
    now = (now or datetime.now(TZ)).astimezone(TZ)
    today = now.date()
    # A manual run before 07:00 reviews the window ending today; after 07:00 likewise.
    start = datetime.combine(today - timedelta(days=1), time(20), TZ)
    end = datetime.combine(today, time(7), TZ)
    return start, end

def normalize_title(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

def parse_rss(xml, start, end, category):
    root = ET.fromstring(xml)
    results = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        stamp = item.findtext("pubDate")
        if not title or not link or not stamp:
            continue
        try:
            published = parsedate_to_datetime(stamp)
            if published.tzinfo is None:
                continue
            published = published.astimezone(TZ)
            if not (start <= published < end):
                continue
        except (TypeError, ValueError):
            continue
        results.append({"category": category, "title": title, "url": link,
                        "published_et": published.isoformat()})
    return results

def collect(start, end):
    stories = []
    for category, query in QUERIES.items():
        try:
            url = "https://news.google.com/rss/search?q=" + quote(query + " when:2d") + "&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(url, timeout=25, headers={"User-Agent": "MarketNewsTracker/1.0"})
            response.raise_for_status()
            stories.extend(parse_rss(response.content, start, end, category))
            LOG.info("%s: %d matching headlines so far", category, len(stories))
        except Exception as exc:
            LOG.warning("%s feed failed: %s", category, exc)
    unique = {}
    for story in stories:
        key = normalize_title(story["title"])
        if key and key not in unique:
            unique[key] = story
    return sorted(unique.values(), key=lambda x: x["published_et"], reverse=True)

def render(start, end, stories):
    header = [f"# Overnight Market Digest — {end:%B %d, %Y}",
              f"**Window:** {start:%Y-%m-%d %I:%M %p %Z} to {end:%Y-%m-%d %I:%M %p %Z}",
              "", "Source-linked headlines only. Article claims and market implications are not independently verified.",
              "This feed is not comprehensive; RSS indexing may be delayed.", ""]
    for category in QUERIES:
        header.append(f"## {category}")
        subset = [s for s in stories if s["category"] == category][:15]
        if not subset:
            header.append("No matching sourced headlines found in the window.")
        for s in subset:
            header.append(f'- [{s["title"]}]({s["url"]}) — {s["published_et"][11:16]} ET')
        header.append("")
    return "\n".join(header) + "\n"

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    start, end = window()
    stories = collect(start, end)
    (ROOT / "overnight_digest.json").write_text(json.dumps({
        "window_start_et": start.isoformat(), "window_end_et": end.isoformat(),
        "stories": stories}, indent=2) + "\n")
    (ROOT / "overnight_digest.md").write_text(render(start, end, stories))
    LOG.info("Saved %d stories to overnight_digest.md and .json", len(stories))

if __name__ == "__main__":
    main()
