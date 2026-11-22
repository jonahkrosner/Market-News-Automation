# Market News Tracker

Two independent, review-only automations for a macro desk.

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
python -m unittest discover -s tests -v
```

Populate `releases.json` with confirmed dates, forecasts, units, and the appropriate FRED series. **Do not use example forecasts for trading.** If no valid releases are configured, the tracker generates a clear no-data brief.

## GitHub Actions
- `overnight-digest.yml`: scheduled at **7:00 AM New York time**, using GitHub's timezone-aware cron; manual run supported.
- `economic-surprises.yml`: checks at 10:45 AM New York time on weekdays, plus manual runs. Data availability is not guaranteed at that time.
- Both upload output as downloadable workflow artifacts. They email the generated report to the configured iCloud address after successful report generation, and also upload artifacts. They **do not post to Slack, commit generated files, or trade**.
- Set `FRED_API_KEY` in GitHub repository **Settings → Secrets and variables → Actions** for the economic tracker. Without it, the tracker skips FRED retrieval and explains why.

GitHub Actions schedules may run late. The digest always computes its previous-night window from New York calendar time, not runner UTC time.

## Email delivery
Set repository Actions secrets `EMAIL_ADDRESS` (your iCloud email) and `EMAIL_APP_PASSWORD` (Apple app-specific password). Each workflow sends from and to `EMAIL_ADDRESS` using iCloud SMTP over TLS on port 465. The digest sends its Markdown report, and Economic News sends the daily brief. Both include a text attachment. Manual workflow dispatch also sends a report; avoid repeatedly dispatching if you don't want duplicate messages. Test email code locally with `python -m unittest discover -s tests -v`; this mocks SMTP and does not send a real message.

## HTTPS email delivery (recommended for GitHub Actions)
GitHub-hosted runners may time out when connecting to iCloud SMTP on port 465. The email script now supports Resend's HTTPS API as an alternative. This requires a Resend account, a verified sending domain, and an API key; an iCloud address cannot be used as the sender unless the sending domain is verified and authorized by the provider.

In **Settings → Secrets and variables → Actions** configure:
- **Repository variables:** `EMAIL_PROVIDER=resend`, `EMAIL_RECIPIENT=jonahkrosner@icloud.com`, and `RESEND_FROM_EMAIL=digest@YOUR_VERIFIED_DOMAIN`.
- **Repository secret:** `RESEND_API_KEY` with the API key from Resend.

The existing `EMAIL_ADDRESS` and `EMAIL_APP_PASSWORD` remain available for SMTP mode (`EMAIL_PROVIDER=smtp`, or unset). The Resend API mode sends HTML and text alternatives; the original local report remains in the downloadable GitHub Actions artifact. The SMTP mode continues to attach the report. No emails will be delivered through Resend until you configure and verify the sender.

Run `python -m unittest discover -s tests -v` before merging. To preview without sending, run `EMAIL_PROVIDER=resend EMAIL_RECIPIENT=you@example.com RESEND_FROM_EMAIL=digest@verified.example python email_reports.py overnight --dry-run` after generating the report.
