"""Source-linked overnight headlines, 20:00–07:00 America/New_York."""
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
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
FALLBACK_FEEDS = (
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
)
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
            if not (start.timestamp() <= published.timestamp() < end.timestamp()):
                continue
        except (TypeError, ValueError):
            continue
        results.append({"category": category, "title": title, "url": link,
                        "published_et": published.isoformat()})
    return results

def fetch_feed(feed, start, end):
    category, url = feed
    try:
        response = requests.get(url, timeout=(8, 15), headers={"User-Agent": "MarketNewsTracker/1.0"})
        response.raise_for_status()
        return parse_rss(response.content, start, end, category), None
    except (requests.RequestException, ET.ParseError) as exc:
        LOG.warning("%s feed unavailable: %s", category, exc)
        return [], category


def collect(start, end, failed_feeds=None):
    feeds = [
        (category, "https://news.google.com/rss/search?q=" + quote(query + " when:2d")
         + "&hl=en-US&gl=US&ceid=US:en")
        for category, query in QUERIES.items()
    ]
    stories = []
    failures = set()
    with ThreadPoolExecutor(max_workers=len(feeds)) as pool:
        for items, failed in pool.map(lambda feed: fetch_feed(feed, start, end), feeds):
            stories.extend(items)
            if failed:
                failures.add(failed)
        if failures or not stories:
            for items, failed in pool.map(lambda feed: fetch_feed(feed, start, end), FALLBACK_FEEDS):
                stories.extend(items)
                if failed:
                    failures.add(failed)
    if failed_feeds is not None:
        failed_feeds.update(failures)
    unique = {}
    for story in stories:
        key = normalize_title(story["title"])
        if key and key not in unique:
            unique[key] = story
    return sorted(unique.values(), key=lambda x: datetime.fromisoformat(x["published_et"]).timestamp(), reverse=True)

def render(start, end, stories, failed_feeds=()):
    header = [f"# Overnight Market Digest — {end:%B %d, %Y}",
              f"**Window:** {start:%Y-%m-%d %I:%M %p %Z} to {end:%Y-%m-%d %I:%M %p %Z}",
              "", "Source-linked headlines only. Article claims and market implications are not independently verified.",
              "This feed is not comprehensive; RSS indexing may be delayed.", ""]
    observed = {story["category"] for story in stories}
    categories = [*QUERIES, *(name for name, _ in FALLBACK_FEEDS if name in observed or name in failed_feeds)]
    for category in categories:
        header.append(f"## {category}")
        subset = [s for s in stories if s["category"] == category][:15]
        if category in failed_feeds:
            header.append("Headline feed unavailable.")
        elif not subset:
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
