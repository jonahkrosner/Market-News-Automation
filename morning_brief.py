"""Build one morning email with overnight headlines and today's schedule."""
from concurrent.futures import ThreadPoolExecutor
import logging

from morning_calendar import render_today
from overnight_digest import ROOT, collect, render, window


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    start, end = window()
    with ThreadPoolExecutor(max_workers=2) as pool:
        calendar = pool.submit(render_today, end.date())
        failed_feeds = set()
        stories = collect(start, end, failed_feeds)
    headlines = render(start, end, stories, failed_feeds)
    # Put timed releases first so they are visible in the email preview.
    title, _, digest_body = headlines.partition("\n")
    report = f"{title}\n\n{calendar.result()}\n## Overnight headlines\n{digest_body}"
    (ROOT / "morning_brief.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
