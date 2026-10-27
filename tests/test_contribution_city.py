"""The city must describe real recent days, never decorative contribution data."""
from datetime import date, timedelta
import copy, importlib, importlib.util, sys, unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


class ContributionCity(unittest.TestCase):
    def model(self,calendar):
        self.assertIsNotNone(importlib.util.find_spec('contribution_city'),
                             'The recent contribution city renderer is required')
        return importlib.import_module('contribution_city').build_city_model(calendar)

    def calendar(self):
        start=date(2026,9,1)
        counts={'2026-09-27':9000,'2026-09-28':2,'2026-10-27':3,'2026-10-28':8000}
        return {'as_of':'2026-10-27','days':[{'date':(start+timedelta(days=i)).isoformat(),
                  'count':counts.get((start+timedelta(days=i)).isoformat(),0)} for i in range(60)]}

    def test_exact_thirty_day_window_excludes_older_and_future_activity(self):
        model=self.model(self.calendar())
        self.assertEqual((model['start'],model['end']),('2026-09-28','2026-10-27'))
        self.assertEqual(len(model['days']),30)
        self.assertEqual((model['total'],model['active_days'],model['peak']),(5,2,3))

    def test_building_heights_follow_actual_counts_and_zero_days_have_no_tower(self):
        model=self.model(self.calendar())
        rows={item['date']:item for item in model['days']}
        self.assertEqual(rows['2026-10-01']['height'],0)
        self.assertGreater(rows['2026-09-28']['height'],0)
        self.assertAlmostEqual(rows['2026-10-27']['height']/rows['2026-09-28']['height'],1.5)

    def test_incomplete_duplicate_or_invalid_daily_data_stops_rendering(self):
        baseline=self.calendar()
        for change in ['missing','duplicate','negative','fractional']:
            calendar=copy.deepcopy(baseline)
            chosen=next(item for item in calendar['days'] if item['date']=='2026-10-15')
            if change=='missing': calendar['days'].remove(chosen)
            elif change=='duplicate': calendar['days'].append(chosen.copy())
            elif change=='negative': chosen['count']=-1
            else: chosen['count']=.5
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.model(calendar)

    def test_empty_activity_has_no_invented_buildings_or_statistics(self):
        calendar=self.calendar()
        for item in calendar['days']: item['count']=0
        model=self.model(calendar)
        self.assertEqual((model['total'],model['active_days'],model['peak']),(0,0,0))
        self.assertTrue(all(item['height']==0 for item in model['days']))


if __name__=='__main__': unittest.main()
