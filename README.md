# Market News Tracker

Two independent, review-only automations for a macro desk.

## 1. Economic surprise tracker
Reads `releases.json`, fetches published FRED observations (when `FRED_API_KEY` is configured), compares actual versus manually entered forecasts, and estimates market reaction using Yahoo Finance. Outputs `surprise_log.json`, `daily_brief.txt`, and `impact_rankings.csv`.

**Important:** FRED data is often revised and is not a point-in-time economic release feed. The tracker will not claim a release-time actual when the release's value or unit cannot be reliably matched. For a production desk, use a timestamped release calendar with original vintage values and a licensed consensus feed. 8:30 ET releases precede US cash equity trading; Yahoo intraday SPX coverage may be absent and is reported as unavailable, never fabricated.

## 2. Overnight market digest
Collects free Google News RSS search results published between **8:00 PM and 7:00 AM America/New_York** (the previous evening through the morning). Deduplicates headlines, groups by subject, and produces `overnight_digest.md` and `overnight_digest.json`. This is a sourced **headline digest**, not an AI-generated analysis or a verified live market-price dashboard. It labels timestamps and links to articles, and does not invent market moves.

## Run locally
```bash
python -m pip install -r requirements.txt
cp .env.example .env
# Optional: put your free FRED_API_KEY in .env
python tracker.py
python overnight_digest.py
python -m unittest discover -s tests -v
```

Populate `releases.json` with confirmed dates, forecasts, units, and the appropriate FRED series. **Do not use example forecasts for trading.** If no valid releases are configured, the tracker generates a clear no-data brief.

## GitHub Actions
- `overnight-digest.yml`: scheduled at **7:00 AM New York time**, using GitHub's timezone-aware cron; manual run supported.
- `economic-surprises.yml`: checks at 10:45 AM New York time on weekdays, plus manual runs. Data availability is not guaranteed at that time.
- Both upload output as downloadable workflow artifacts. They **do not send email, post to Slack, commit generated files, or trade**.
- Set `FRED_API_KEY` in GitHub repository **Settings → Secrets and variables → Actions** for the economic tracker. Without it, the tracker skips FRED retrieval and explains why.

GitHub Actions schedules may run late. The digest always computes its previous-night window from New York calendar time, not runner UTC time.
