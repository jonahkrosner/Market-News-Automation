import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tracker import surprise_math, classify, process
from overnight_digest import window, parse_rss

class TrackerTests(unittest.TestCase):
    def test_math(self):
        self.assertEqual(surprise_math(3.2, 3.1), (0.1, 3.2258))
        self.assertEqual(surprise_math(0, 0), (0, None))
    def test_threshold(self):
        self.assertEqual(classify("Nonfarm Payrolls", 60), "big beat")
        self.assertEqual(classify("CPI YoY", -0.3), "big miss")
    def test_missing_forecast_skips(self):
        self.assertEqual(process([{"date":"2026-01-01","time":"08:30","indicator":"CPI YoY"}], [], datetime(2026, 2, 1, tzinfo=ZoneInfo("America/New_York"))), [])
    def test_dst_window(self):
        start, end = window(datetime(2026, 11, 2, 8, tzinfo=ZoneInfo("America/New_York")))
        self.assertEqual(start.hour, 20)
        self.assertEqual(end.hour, 7)
        self.assertEqual(start.utcoffset(), end.utcoffset())
    def test_rss_boundary(self):
        xml = b'<rss><channel><item><title>Test</title><link>https://example.com</link><pubDate>Mon, 02 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>'
        start, end = window(datetime(2026, 11, 2, 8, tzinfo=ZoneInfo("America/New_York")))
        self.assertEqual(len(parse_rss(xml, start, end, "Macro")), 1)

if __name__ == "__main__":
    unittest.main()
