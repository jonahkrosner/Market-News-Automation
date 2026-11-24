# Market News Tracker

A daily market brief and an on-demand economic release tracker.

## 1. Economic news
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
python morning_brief.py
python -m unittest discover -s tests -v
```

Populate `releases.json` with confirmed dates, forecasts, units, and the appropriate FRED series. **Do not use example forecasts for trading.** If no valid releases are configured, the tracker generates a clear no-data brief.

## GitHub Actions

- **Morning market brief** starts daily at **7:00 AM Eastern**, including weekends and holidays. It combines the overnight headlines with that day's scheduled BLS, BEA, and Census releases, all in Eastern time. It reports feed failures and uses BBC and MarketWatch as headline fallbacks. GitHub can start scheduled jobs late.
- **Economic news** is available on demand for post-release tracking. Set `FRED_API_KEY` in repository Actions secrets for FRED retrieval.
- Both workflows upload downloadable report artifacts. Manual dispatch of the morning brief can generate the artifact with email disabled.

## Email delivery

Set the repository Actions secrets `EMAIL_ADDRESS` and `EMAIL_APP_PASSWORD` to the iCloud address and its Apple app-specific password. The workflows send to that address via authenticated iCloud SMTP with STARTTLS on port 587. Run the unit tests to exercise email generation and mocked SMTP without sending a real message.
