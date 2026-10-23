"""Display real intervals in the date format shown in the reference cards."""
from pathlib import Path
from datetime import date
import sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import status_panel


class StreakDates(unittest.TestCase):
    def test_english_us_uses_the_same_real_ranges_with_english_dates(self):
        summary = {'first_contribution':'2022-03-25',
                   'current_streak_range':{'start':'2026-10-19','end':'2026-10-22'},
                   'longest_streak_range':{'start':'2023-01-09','end':'2023-01-14'}}
        self.assertEqual(status_panel.streak_date_labels(summary, date(2026,10,22), locale='en-US'),
                         {'total':'Mar 25, 2022 — present','current':'Oct 19 — Oct 22',
                          'longest':'Jan 9, 2023 — Jan 14, 2023'})

    def test_reference_format_keeps_past_years_and_hides_redundant_current_year(self):
        formatter = getattr(status_panel, 'streak_date_labels', None)
        self.assertIsNotNone(formatter, 'The cards need actual contribution date labels')
        summary = {'first_contribution':'2022-03-25',
                   'current_streak_range':{'start':'2026-10-19','end':'2026-10-22'},
                   'longest_streak_range':{'start':'2023-01-09','end':'2023-01-14'}}
        self.assertEqual(formatter(summary, date(2026,10,22)),
                         {'total':'25 mar 2022 — atual','current':'19 out — 22 out',
                          'longest':'9 jan 2023 — 14 jan 2023'})

    def test_single_day_and_missing_ranges_are_not_fabricated(self):
        formatter = getattr(status_panel, 'streak_date_labels', None)
        self.assertIsNotNone(formatter)
        self.assertEqual(formatter({'first_contribution':None, 'current_streak_range':None,
                                    'longest_streak_range':{'start':'2026-10-19','end':'2026-10-19'}}, date(2026,10,22)),
                         {'total':'—','current':'—','longest':'19 out'})
