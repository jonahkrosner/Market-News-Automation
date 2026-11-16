"""Firm-scoped newsletter configuration. No client PII or holdings required."""
import json
import re
from pathlib import Path

def load_profiles(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    profiles = raw.get("firms", [])
    ids = set()
    for firm in profiles:
        fid = firm.get("id", "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", fid) or fid in ids:
            raise ValueError("Firm IDs must be unique, lowercase, and URL-safe")
        ids.add(fid)
        if not isinstance(firm.get("name"), str) or not firm["name"].strip():
            raise ValueError("Firm name is required")
        for key in ("interests", "tickers"):
            if not isinstance(firm.get(key, []), list) or not all(isinstance(v, str) for v in firm.get(key, [])):
                raise ValueError(f"{key} must be a list of strings")
    return profiles

def profile_by_id(profiles, firm_id):
    matches = [p for p in profiles if p["id"] == firm_id]
    if len(matches) != 1:
        raise ValueError("Unknown firm ID")
    return matches[0]
