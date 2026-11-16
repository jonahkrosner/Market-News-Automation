"""Generate per-firm HTML previews without sending email."""
import argparse
import json
from pathlib import Path
from newsletter_profiles import load_profiles, profile_by_id
from newsletter_analysis import select_stories
from email_reports import render_newsletter

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", default="firms.example.json")
    parser.add_argument("--firm", required=True)
    parser.add_argument("--input", default="overnight_digest.json")
    parser.add_argument("--output", default="newsletter_preview.html")
    args = parser.parse_args()
    firm = profile_by_id(load_profiles(args.profiles), args.firm)
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    interests = firm.get("interests", []) + firm.get("tickers", [])
    filtered = dict(data, stories=select_stories(data.get("stories", []), interests))
    rendered = render_newsletter(filtered, firm["name"], interests)
    Path(args.output).write_text(rendered, encoding="utf-8")
    print(f"Preview written to {args.output}; no email sent")

if __name__ == "__main__":
    main()
