"""Regression tests for the email branch; no network requests."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from email_reports import build_message, render_html, send


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "overnight_digest.md").write_text(
            "# Digest\n## Markets\n- [Stocks](https://example.com/a) — 06:30 ET\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_multipart_email_and_attachment(self):
        msg = build_message("overnight", "sender@icloud.com", "reader@example.com", self.root)
        self.assertEqual(msg["To"], "reader@example.com")
        parts = list(msg.walk())
        self.assertTrue(any(p.get_content_type() == "text/html" for p in parts))
        self.assertTrue(any(p.get_content_disposition() == "attachment" for p in parts))
        self.assertIn("Stocks", msg.as_string())

    def test_unsafe_headline_is_escaped(self):
        result = render_html("# <script>alert(1)</script>\n- [link](https://example.com)")
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)
        self.assertIn('href="https://example.com"', result)

    def test_empty_report_refused(self):
        (self.root / "overnight_digest.md").write_text("   ")
        with self.assertRaises(ValueError):
            build_message("overnight", "a@b.com", "a@b.com", self.root)

    def test_dry_run_never_uses_smtp(self):
        with patch.dict(os.environ, {"EMAIL_ADDRESS": "sender@icloud.com",
                                     "EMAIL_RECIPIENT": "reader@example.com"}, clear=True):
            with patch("email_reports.smtplib.SMTP_SSL") as smtp:
                msg = send("overnight", root=self.root, dry_run=True)
                smtp.assert_not_called()
                self.assertEqual(msg["To"], "reader@example.com")


if __name__ == "__main__":
    unittest.main()
