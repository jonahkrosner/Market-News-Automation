"""Send market reports through iCloud SMTP with readable HTML and text fallbacks."""
import argparse
import html
import os
import re
import smtplib
import ssl
import json
import urllib.error
import urllib.request
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
REPORTS = {
    "overnight": ("Overnight Market Digest", "overnight_digest.md"),
    "economic": ("Economic News", "daily_brief.txt"),
}
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")

def _inline(value):
    """Escape untrusted headlines and permit only HTTP(S) Markdown links."""
    parts = []
    pos = 0
    for match in LINK.finditer(value):
        parts.append(html.escape(value[pos:match.start()]))
        label, url = match.groups()
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            parts.append(f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>')
        else:
            parts.append(html.escape(match.group(0)))
        pos = match.end()
    parts.append(html.escape(value[pos:]))
    return "".join(parts)

def render_html(body):
    """Render a restricted Markdown subset without trusting RSS text as HTML."""
    blocks = []
    in_list = False
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            continue
        if line.startswith("- "):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{_inline(line[2:])}</li>")
            continue
        if in_list:
            blocks.append("</ul>")
            in_list = False
        if line.startswith("## "):
            blocks.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            blocks.append(f"<h1>{_inline(line[2:])}</h1>")
        else:
            blocks.append(f"<p>{_inline(line)}</p>")
    if in_list:
        blocks.append("</ul>")
    return ('<!doctype html><html><head><meta charset="utf-8"></head>'
            '<body style="margin:0;background:#f4f6f8;font-family:Arial,sans-serif;color:#18212d">'
            '<main style="max-width:700px;margin:24px auto;padding:28px;background:white;'
            'border-radius:12px;line-height:1.55">'
            + "\n".join(blocks) +
            '<hr><p style="font-size:12px;color:#667085">Automated news digest. '
            'Headlines and market claims are not independently verified.</p>'
            '</main></body></html>')

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
    msg.add_alternative(render_html(body), subtype="html")
    msg.add_attachment(body.encode("utf-8"), maintype="text",
                       subtype="plain", filename=filename)
    return msg

def send(kind, root=ROOT, dry_run=False):
    sender = os.environ.get("EMAIL_ADDRESS", "").strip()
    recipient = os.environ.get("EMAIL_RECIPIENT", "").strip() or sender
    provider = os.environ.get("EMAIL_PROVIDER", "smtp").strip().lower()
    if provider not in ("smtp", "resend"):
        raise ValueError("EMAIL_PROVIDER must be smtp or resend")
    if not recipient:
        raise ValueError("EMAIL_RECIPIENT or EMAIL_ADDRESS is required")
    if provider == "smtp" and not sender:
        raise ValueError("EMAIL_ADDRESS is required for SMTP")
    if provider == "resend":
        sender = os.environ.get("RESEND_FROM_EMAIL", "").strip()
        if not sender:
            raise ValueError("RESEND_FROM_EMAIL is required (verified sender/domain)")
    msg = build_message(kind, sender, recipient, root)
    if dry_run:
        print(f"DRY RUN ({provider}): {msg['Subject']} -> {recipient}; no email sent")
        return msg
    if provider == "resend":
        api_key = os.environ.get("RESEND_API_KEY", "").strip()
        if not api_key:
            raise ValueError("RESEND_API_KEY secret is required")
        payload = json.dumps({
            "from": sender,
            "to": [recipient],
            "subject": str(msg["Subject"]),
            "text": msg.get_body(preferencelist=("plain",)).get_content(),
            "html": msg.get_body(preferencelist=("html",)).get_content(),
        }).encode("utf-8")
        request = urllib.request.Request(
            "https://api.resend.com/emails", data=payload,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status not in (200, 201, 202):
                    raise RuntimeError(f"Email API returned HTTP {response.status}")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Email API rejected request (HTTP {exc.code}); "
                               "check verified sender, recipient and API key") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("Email API connection failed; check HTTPS connectivity") from exc
    else:
        password = os.environ.get("EMAIL_APP_PASSWORD", "").strip()
        if not password:
            raise ValueError("EMAIL_APP_PASSWORD secret is required")
        try:
            with smtplib.SMTP_SSL("smtp.mail.me.com", 465,
                                 context=ssl.create_default_context(), timeout=30) as smtp:
                smtp.login(sender, password)
                smtp.send_message(msg)
        except (smtplib.SMTPException, OSError) as exc:
            raise RuntimeError(f"SMTP delivery failed ({type(exc).__name__}); "
                               "port 465 may be blocked on GitHub runners. "
                               "Use EMAIL_PROVIDER=resend for HTTPS delivery") from exc
    print(f"Sent {kind} report via {provider} to {recipient}")
    return msg

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=REPORTS)
    parser.add_argument("--dry-run", action="store_true",
                        help="Build and validate message without SMTP delivery")
    args = parser.parse_args()
    send(args.kind, dry_run=args.dry_run)
