"""All-time streaks cross calendar years and do not accept incomplete snapshots."""
from pathlib import Path
from datetime import date
import sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class StreakHistory(unittest.TestCase):
    def test_complete_history_and_daily_cache_preserve_a_streak_across_years(self):
        from fetch_streak_history import collect_history
        from fetch_contributions import derive_stats
        previous = [{'date':'2025-12-30','count':1,'level':1}, {'date':'2025-12-31','count':1,'level':1}]
        cache = {'years':{'2025':{'checked_on':'2026-01-02','days':previous}}}
        calls = []
        def get_days(year):
            calls.append(year)
            self.assertEqual(year, 2026)
            return [{'date':'2026-01-01','count':5,'level':4}, {'date':'2026-01-02','count':0,'level':0}]
        result = collect_history(get_days, date(2025,12,30), date(2026,1,2), cache)
        self.assertEqual(calls, [2026])
        stats = derive_stats(result['days'], date(2026,1,2))
        self.assertEqual(stats['total'], 7)
        self.assertEqual(stats['current_streak'], 3)
        self.assertEqual(stats['longest_streak'], 3)

    def test_incomplete_historical_year_is_rejected(self):
        from fetch_streak_history import collect_history
        with self.assertRaises(ValueError):
            collect_history(lambda year:[{'date':'2025-12-31','count':1,'level':1}],
                            date(2025,12,30), date(2026,1,2), {})
