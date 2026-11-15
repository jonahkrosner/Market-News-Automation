import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import email_reports

class EmailReportsTests(unittest.TestCase):
    def test_message_contains_report_and_attachment(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "overnight_digest.md").write_text("# Market headlines\nStory")
            msg = email_reports.build_message("overnight", "me@icloud.com", "me@icloud.com", Path(d))
            self.assertEqual(msg["Subject"], "Overnight Market Digest")
            self.assertIn("Market headlines", msg.get_body(preferencelist=("plain",)).get_content())
            self.assertEqual(next(msg.iter_attachments()).get_filename(), "overnight_digest.md")

    def test_empty_report_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "daily_brief.txt").write_text(" ")
            with self.assertRaises(ValueError):
                email_reports.build_message("economic", "a@icloud.com", "a@icloud.com", Path(d))

    @patch.dict("os.environ", {"EMAIL_ADDRESS": "me@icloud.com", "EMAIL_APP_PASSWORD": "secret"})
    @patch("email_reports.smtplib.SMTP_SSL")
    def test_smtp_send(self, smtp):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "daily_brief.txt").write_text("Daily report")
            email_reports.send("economic", Path(d))
            conn = smtp.return_value.__enter__.return_value
            conn.login.assert_called_once_with("me@icloud.com", "secret")
            self.assertEqual(conn.send_message.call_count, 1)

    @patch.dict("os.environ", {"EMAIL_ADDRESS": "", "EMAIL_APP_PASSWORD": ""})
    def test_missing_secrets_rejected(self):
        with self.assertRaises(ValueError):
            email_reports.send("economic")
