"""Send generated market reports through iCloud Mail SMTP."""
import argparse
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORTS = {
    "overnight": ("Overnight Market Digest", "overnight_digest.md"),
    "economic": ("Economic News", "daily_brief.txt"),
}

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
