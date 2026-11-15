"""Review-only macro surprise tracker. Never infers actual values from mismatched units."""
import csv
import json
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yfinance as yf
from config import FRED_API_KEY, TICKERS, THRESHOLDS

ET = ZoneInfo("America/New_York")
LOG = logging.getLogger("surprises")
ROOT = Path(__file__).resolve().parent

def classify(indicator, surprise):
    threshold = THRESHOLDS.get(indicator)
    if threshold is None:
        return "above forecast" if surprise > 0 else "below forecast" if surprise < 0 else "in line"
    return "big beat" if surprise > threshold else "big miss" if surprise < -threshold else "in line"

def surprise_math(actual, forecast):
    difference = float(actual) - float(forecast)
    percent = difference / abs(float(forecast)) * 100 if float(forecast) else None
    return round(difference, 6), round(percent, 4) if percent is not None else None

def fred_actual(series, observation_date):
    if not FRED_API_KEY:
        raise ValueError("FRED_API_KEY missing; skipping FRED actual")
    response = requests.get("https://api.stlouisfed.org/fred/series/observations",
        params={"series_id": series, "api_key": FRED_API_KEY, "file_type": "json",
                "observation_start": observation_date, "observation_end": observation_date},
        timeout=20)
    response.raise_for_status()
    observations = response.json().get("observations", [])
    if not observations or observations[-1]["value"] == ".":
        raise ValueError("No matching FRED observation for specified period")
    return float(observations[-1]["value"])

def market_reaction(release_dt):
    """Returns release-to-one-hour-later price changes only when both quotes exist.
    Yahoo 1m history is typically limited to recent days. Never substitutes daily prices.
    """
    out = {}
    for label, ticker in TICKERS.items():
        try:
            start = release_dt - timedelta(minutes=5)
            end = release_dt + timedelta(minutes=70)
            df = yf.download(ticker, start=start, end=end, interval="1m",
                             progress=False, auto_adjust=True, threads=False)
            if df.empty:
                out[label] = None
                continue
            times = df.index.tz_convert(ET) if df.index.tz is not None else df.index.tz_localize(ET)
            closes = df["Close"]
            if hasattr(closes, "columns"):
                closes = closes.iloc[:, 0]
            at = [(t, float(v)) for t, v in zip(times, closes) if math.isfinite(float(v))]
            before = [v for t, v in at if release_dt <= t <= release_dt + timedelta(minutes=5)]
            after = [v for t, v in at if release_dt + timedelta(minutes=55) <= t <= release_dt + timedelta(minutes=65)]
            if not before or not after:
                out[label] = None
            elif label == "10Y":
                # ^TNX quotes 10x yield percentage: 1 index point = 10 bp.
                out[label] = round((after[0] - before[0]) * 10, 3)
            else:
                out[label] = round((after[0] / before[0] - 1) * 100, 4) if before[0] else None
        except Exception as exc:
            LOG.warning("Market data %s failed: %s", ticker, exc)
            out[label] = None
    return out

def process(releases, history, now=None):
    now = now or datetime.now(ET)
    existing = {r["id"] for r in history}
    for event in releases:
        try:
            if event.get("category") == "earnings" or not event.get("time"):
                continue
            dt = datetime.fromisoformat(event["date"] + "T" + event["time"]).replace(tzinfo=ET)
            event_id = event.get("id", f'{event["date"]}:{event["indicator"]}')
            if event_id in existing or dt > now:
                continue
            if event.get("forecast") is None or not event.get("series") or not event.get("observation_date"):
                LOG.warning("Skipping %s: forecast, series, or observation_date missing", event_id)
                continue
            # FRED raw series units MUST match manually entered consensus units.
            # No automatic YoY conversion of CPI index, monthly payroll levels, etc.
            if event.get("unit") != event.get("fred_unit"):
                LOG.warning("Skipping %s: forecast and FRED units differ", event_id)
                continue
            actual = fred_actual(event["series"], event["observation_date"])
            diff, pct = surprise_math(actual, event["forecast"])
            history.append({"id": event_id, "release_at_et": dt.isoformat(),
                "indicator": event["indicator"], "unit": event["unit"],
                "forecast": float(event["forecast"]), "actual": actual,
                "surprise": diff, "surprise_pct": pct,
                "classification": classify(event["indicator"], diff),
                "market_moves": market_reaction(dt),
                "warning": "FRED latest observation may be revised; not verified first-release vintage"})
            existing.add(event_id)
            LOG.info("Processed %s", event_id)
        except Exception as exc:
            LOG.warning("Release failed (%s): %s", event.get("indicator", "?"), exc)
    return history

def write_outputs(history):
    (ROOT / "surprise_log.json").write_text(json.dumps(history, indent=2) + "\n")
    lines = ["ECONOMIC SURPRISE TRACKER", f"Generated: {datetime.now(ET).isoformat()}", "",
             "FRED data may be revised; verify original release and forecast before trading.", ""]
    if not history:
        lines.append("No verified, unit-matched economic releases processed.")
    for r in history[-10:][::-1]:
        lines += [f'{r["indicator"]}: actual {r["actual"]} vs forecast {r["forecast"]} {r["unit"]} ({r["surprise"]:+g} surprise)',
                  f'  10Y: {r["market_moves"].get("10Y")} bp; S&P: {r["market_moves"].get("SP500")}%; DXY: {r["market_moves"].get("DXY")}%',
                  "  Missing moves are unavailable, not zero.", ""]
    (ROOT / "daily_brief.txt").write_text("\n".join(lines) + "\n")
    rows = []
    for indicator in sorted({r["indicator"] for r in history}):
        subset = [r for r in history if r["indicator"] == indicator]
        for market, unit in [("10Y", "bp"), ("SP500", "%"), ("DXY", "%")]:
            values = [abs(r["market_moves"][market]) for r in subset if r["market_moves"].get(market) is not None]
            rows.append({"indicator": indicator, "market": market, "unit": unit,
                         "sample_size": len(values),
                         "average_absolute_move": round(sum(values)/len(values), 4) if values else ""})
    with (ROOT / "impact_rankings.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["indicator", "market", "unit", "sample_size", "average_absolute_move"])
        writer.writeheader()
        writer.writerows(rows)

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    releases = json.loads((ROOT / "releases.json").read_text())
    path = ROOT / "surprise_log.json"
    history = json.loads(path.read_text()) if path.exists() else []
    write_outputs(process(releases, history))
    LOG.info("Wrote surprise_log.json, daily_brief.txt, impact_rankings.csv")

if __name__ == "__main__":
    main()
