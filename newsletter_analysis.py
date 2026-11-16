"""Conservative, auditable headline-based story selection.

This module does not fetch article bodies or claim to verify headline assertions.
"""
import re
from urllib.parse import urlparse

BLOCKED = ("simply wall st", "journalarta", "brand icon image")
PREFERRED = ("reuters", "associated press", "bloomberg", "financial times", "cnbc", "wsj", "yahoo finance")
STOPWORDS = {"the", "a", "an", "and", "of", "in", "on", "for", "to", "as", "with", "at", "after", "before", "today"}

def source_name(title):
    return title.rsplit(" - ", 1)[-1].strip() if " - " in title else "Source"

def headline(title):
    return title.rsplit(" - ", 1)[0].strip() if " - " in title else title.strip()

def tokens(title):
    return {w for w in re.findall(r"[a-z0-9]+", headline(title).lower()) if len(w) > 2 and w not in STOPWORDS}

def select_stories(stories, interests=(), limit=8):
    """Score relevant stories and cluster near-duplicate coverage by token overlap."""
    candidates = []
    for story in stories:
        title = str(story.get("title", ""))
        url = str(story.get("url", ""))
        if urlparse(url).scheme not in ("http", "https") or any(x in title.lower() for x in BLOCKED):
            continue
        words = tokens(title)
        if len(words) < 3:
            continue
        score = sum(7 for term in interests if term and term.lower() in title.lower())
        score += 3 if source_name(title).lower() in PREFERRED else 0
        score += 2 if any(term in words for term in ("fed", "inflation", "earnings", "treasury", "nvidia", "stocks", "tariffs")) else 0
        candidates.append((score, story, words))
    candidates.sort(key=lambda x: (x[0], x[1].get("published_et", "")), reverse=True)
    chosen = []
    for _, story, words in candidates:
        if any(len(words & existing) / max(1, min(len(words), len(existing))) >= 0.6 for _, existing in chosen):
            continue
        chosen.append((story, words))
        if len(chosen) == limit:
            break
    return [story for story, _ in chosen]
