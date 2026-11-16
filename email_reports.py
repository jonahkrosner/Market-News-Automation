"""Send readable HTML market newsletters through iCloud Mail SMTP."""
import argparse
import html
import json
import os
import re
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
REPORTS = {
    "overnight": ("Overnight Market Digest", "overnight_digest.md"),
    "economic": ("Economic News", "daily_brief.txt"),
}

def safe_url(value):
    value = str(value or "").strip()
    return value if urlparse(value).scheme in ("https", "http") else ""

def clean_title(value):
    return re.sub(r"\s+-\s+[^-]+$", "", str(value or "")).strip()

def publisher(value):
    match = re.search(r"\s+-\s+([^-]+)$", str(value or ""))
    return match.group(1).strip() if match else "Source"

def ranked_stories(stories, interests):
    blocked = ("stock analysis - simply wall st", "journalarta", "brand icon image")
    unique = set()
    output = []
    for story in stories:
        title = str(story.get("title", ""))
        if any(b in title.lower() for b in blocked):
            continue
        key = re.sub(r"[^a-z0-9 ]", "", clean_title(title).lower())
        if not key or key in unique or not safe_url(story.get("url")):
            continue
        unique.add(key)
        score = sum(6 for term in interests if term.lower() in title.lower())
        score += 2 if any(t in title.lower() for t in ("fed", "inflation", "earnings", "treasury", "nvidia", "stocks")) else 0
        score += 1 if publisher(title).lower() in ("reuters", "associated press", "bloomberg", "cnbc", "financial times", "yahoo finance") else 0
        output.append((score, story))
    return [story for _, story in sorted(output, key=lambda pair: pair[0], reverse=True)]

def render_newsletter(data, recipient_name="", interests=()):
    stories = ranked_stories(data.get("stories", []), interests)
    featured = stories[:8]
    personalized = [s for s in stories if any(t.lower() in s.get("title", "").lower() for t in interests)][:4]
    date = data.get("window_end_et", "")[:10]
    try:
        date = datetime.fromisoformat(date).strftime("%B %d, %Y")
    except ValueError:
        pass
    greeting = f"Prepared for {recipient_name}" if recipient_name else "Your morning market briefing"
    esc = lambda x: html.escape(str(x), quote=True)
    def card(s):
        title = esc(clean_title(s.get("title", "")))
        source = esc(publisher(s.get("title", "")))
        category = esc(s.get("category", "Market news"))
        url = esc(safe_url(s.get("url", "")))
        return (f'<tr><td style="padding:18px 24px;border-bottom:1px solid #e6eaf0">'
                f'<div style="color:#53708d;font-size:11px;font-weight:700;letter-spacing:1px">{category.upper()}</div>'
                f'<div style="font-size:17px;font-weight:700;color:#14253c;margin:7px 0">{title}</div>'
                f'<div style="font-size:12px;color:#69788a">{source} &nbsp;·&nbsp; '
                f'<a href="{url}" style="color:#1661a9">Read original report</a></div></td></tr>')
    top = featured[:3]
    takeaways = "".join(f'<li style="margin:0 0 9px">{esc(clean_title(s.get("title", "")))}</li>' for s in top)
    story_cards = "".join(card(s) for s in featured)
    personalized_html = ("".join(card(s) for s in personalized) if personalized else
        '<tr><td style="padding:18px 24px;color:#637083">No matching stories in this collection window.</td></tr>')
    note = ("This edition summarizes source headlines, not independently verified article content. "
            "Headlines may omit context; follow source links before making investment decisions. "
            "RSS coverage may be incomplete or delayed.")
    return f"""<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;background:#f1f4f8;font-family:Arial,Helvetica,sans-serif;color:#17273a">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f4f8"><tr><td align="center" style="padding:26px 10px">
<table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:100%;max-width:620px;background:white;border-radius:12px;overflow:hidden">
<tr><td style="background:#11243b;padding:30px 26px;color:white">
<div style="color:#9dbbd7;font-size:11px;font-weight:700;letter-spacing:2px">MARKET INTELLIGENCE / MORNING EDITION</div>
<h1 style="font-size:30px;line-height:1.15;margin:15px 0 6px;color:white">The Overnight Brief</h1>
<div style="color:#c9d5e2;font-size:13px">{esc(date)} &nbsp; | &nbsp; {esc(greeting)}</div>
</td></tr>
<tr><td style="padding:25px 26px 15px">
<div style="color:#42617e;font-size:11px;font-weight:700;letter-spacing:1px">EXECUTIVE SCAN</div>
<h2 style="font-size:21px;line-height:1.35;margin:9px 0;color:#17283f">What is making headlines before the open</h2>
<p style="font-size:14px;line-height:1.65;color:#43536a">A curated overview of the most relevant overnight market coverage. Story titles are source-attributed; market implications have not been independently verified.</p>
<ol style="font-size:14px;line-height:1.5;padding-left:20px;color:#243c56">{takeaways or '<li>No qualifying headlines were collected.</li>'}</ol>
</td></tr>
<tr><td style="background:#edf3f9;padding:15px 26px;color:#234c73;font-size:12px;font-weight:700;letter-spacing:1px">TOP MARKET DEVELOPMENTS</td></tr>
{story_cards or '<tr><td style="padding:20px 26px">No qualifying headlines found.</td></tr>'}
<tr><td style="background:#edf3f9;padding:15px 26px;color:#234c73;font-size:12px;font-weight:700;letter-spacing:1px">YOUR WATCHLIST</td></tr>
{personalized_html}
<tr><td style="padding:22px 26px;background:#f7f9fc;color:#718093;font-size:11px;line-height:1.6">{esc(note)}<br>Coverage window: {esc(data.get("window_start_et",""))} to {esc(data.get("window_end_et",""))}.</td></tr>
</table></td></tr></table></body></html>"""

def build_message(kind, sender, recipient, root=ROOT):
    if kind not in REPORTS:
        raise ValueError("Unknown report kind")
    title, filename = REPORTS[kind]
    body = (root / filename).read_text(encoding="utf-8")
    if not body.strip():
        raise ValueError(f"{filename} is empty; refusing to send")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = title
    msg.set_content(body)
    if kind == "overnight":
        data = json.loads((root / "overnight_digest.json").read_text(encoding="utf-8"))
        interests = tuple(x.strip() for x in os.environ.get("NEWSLETTER_INTERESTS", "").split(",") if x.strip())
        name = os.environ.get("NEWSLETTER_NAME", "").strip()
        msg.add_alternative(render_newsletter(data, name, interests), subtype="html")
    msg.add_attachment(body.encode("utf-8"), maintype="text", subtype="plain", filename=filename)
    return msg

def send(kind, root=ROOT):
    sender = os.environ.get("EMAIL_ADDRESS", "").strip()
    password = os.environ.get("EMAIL_APP_PASSWORD", "").strip()
    if not sender or not password:
        raise ValueError("EMAIL_ADDRESS and EMAIL_APP_PASSWORD secrets are required")
    msg = build_message(kind, sender, sender, root)
    with smtplib.SMTP_SSL("smtp.mail.me.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)
    print(f"Sent {kind} report to {sender}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=REPORTS)
    send(parser.parse_args().kind)
