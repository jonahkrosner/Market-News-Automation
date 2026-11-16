import json
import tempfile
import unittest
from pathlib import Path
from newsletter_analysis import select_stories
from newsletter_profiles import load_profiles, profile_by_id
from email_reports import render_newsletter

class NewsletterProductTests(unittest.TestCase):
    def test_duplicate_headlines_collapsed(self):
        stories = [
            {"title": "Nvidia earnings loom as global stocks slide - Reuters", "url": "https://example.com/a", "published_et": "2026-11-16T06:00:00"},
            {"title": "Global stocks slide as Nvidia earnings loom - CNBC", "url": "https://example.com/b", "published_et": "2026-11-16T05:00:00"},
        ]
        self.assertEqual(len(select_stories(stories)), 1)

    def test_invalid_urls_and_low_quality_pages_excluded(self):
        stories = [{"title": "Arxis Stock Analysis - Simply Wall St", "url": "https://example.com/a"},
                   {"title": "Important earnings news overnight - Reuters", "url": "javascript:alert(1)"}]
        self.assertEqual(select_stories(stories), [])

    def test_html_escapes_untrusted_headline(self):
        markup = render_newsletter({"stories": [{"title": "<script>alert(1)</script> earnings report - Reuters", "url": "https://example.com", "category": "Companies"}]}, "Demo")
        self.assertNotIn("<script>", markup)
        self.assertIn("&lt;script&gt;", markup)

    def test_duplicate_firm_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "firms.json"
            path.write_text(json.dumps({"firms": [{"id": "demo", "name": "A"}, {"id": "demo", "name": "B"}]}))
            with self.assertRaises(ValueError):
                load_profiles(path)

    def test_firm_lookup(self):
        self.assertEqual(profile_by_id([{"id": "demo", "name": "A"}], "demo")["name"], "A")

if __name__ == "__main__":
    unittest.main()
