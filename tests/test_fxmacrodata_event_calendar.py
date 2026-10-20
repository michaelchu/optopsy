"""Offline release-calendar sample regressions; no upstream/API calls."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch


path = Path(__file__).resolve().parents[1] / "samples/fxmacrodata_event_calendar.py"
spec = importlib.util.spec_from_file_location("calendar_sample", path)
sample = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sample)


class CalendarSampleTests(unittest.TestCase):
    def test_canonical_epoch_is_used_instead_of_reference_period(self):
        events = [{"market_tier": 1, "announcement_datetime": 1783497600,
                   "date": "2026-06-01"}]
        self.assertEqual(["2026-07-08"], sample.top_tier_event_dates(events))

    def test_numeric_utc_timestamp_is_supported(self):
        self.assertEqual(["2026-07-08"], sample.top_tier_event_dates([
            {"market_tier": 1, "announcement_datetime_utc": 1783497600},
        ]))

    def test_epoch_zero_is_not_treated_as_missing(self):
        self.assertEqual(["1970-01-01"], sample.top_tier_event_dates([
            {"market_tier": 1, "announcement_datetime": 0, "date": "2026-06-01"},
        ]))

    def test_reference_period_does_not_invent_a_release_date(self):
        self.assertEqual([], sample.top_tier_event_dates([
            {"market_tier": 1, "date": "2026-06-01"},
        ]))

    def test_offset_timestamp_is_converted_to_utc_date(self):
        self.assertEqual(["2026-07-07"], sample.top_tier_event_dates([
            {"market_tier": 1, "announcement_datetime_local": "2026-07-08T01:00:00+09:00"},
        ]))

    def test_invalid_or_ambiguous_time_is_skipped(self):
        for value in ("not a timestamp", "2026-07-08T01:00:00", True, float("inf")):
            with self.subTest(value=value):
                self.assertEqual([], sample.top_tier_event_dates([
                    {"market_tier": 1, "announcement_datetime_utc": value},
                ]))

    def test_iso_dates_tier_filter_and_deduplication_are_preserved(self):
        events = [
            {"market_tier": 1, "announcement_datetime_utc": "2026-07-08T12:00:00Z"},
            {"top_tier_for_currency": True, "announcement_datetime_utc": "2026-07-08T14:00:00Z"},
            {"market_tier": 2, "announcement_datetime_utc": "2026-07-09T12:00:00Z"},
        ]
        self.assertEqual(["2026-07-08"], sample.top_tier_event_dates(events))

    def test_error_details_are_not_echoed(self):
        response = io.StringIO(json.dumps({"detail": "fixture-private-value"}))
        with patch.object(sample, "urlopen", return_value=response):
            with self.assertRaises(ValueError) as raised:
                sample.fetch_calendar()
        self.assertNotIn("fixture-private-value", str(raised.exception))

    def test_valid_empty_calendar_is_preserved(self):
        response = io.StringIO(json.dumps({"data": []}))
        with patch.object(sample, "urlopen", return_value=response):
            self.assertEqual([], sample.fetch_calendar())


if __name__ == "__main__":
    unittest.main()
