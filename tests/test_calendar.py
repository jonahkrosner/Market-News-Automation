import json
import unittest
from pathlib import Path
from event_calendar import validate, render
ROOT = Path(__file__).resolve().parents[1]
class CalendarTests(unittest.TestCase):
    def test_all_events(self):
        events = json.loads((ROOT/"releases.json").read_text())
        self.assertEqual(len(events), 69)
        self.assertEqual(dict(validate(events)), {"earnings": 28, "macro": 41})
        self.assertIn("Nvidia earnings", render(events))
    def test_duplicate(self):
        e = {"id":"a","date":"2026-11-17","indicator":"CPI","category":"macro"}
        with self.assertRaises(ValueError):
            validate([e,e])
    def test_forecast_requires_unit(self):
        with self.assertRaises(ValueError):
            validate([{"id":"a","date":"2026-11-17","indicator":"CPI","category":"macro","forecast":3.1}])
