"""The annual city must include every real day without decorative activity."""
from datetime import date, timedelta
import copy, importlib, importlib.util, sys, unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


class ContributionCity(unittest.TestCase):
    def model(self,calendar):
        self.assertIsNotNone(importlib.util.find_spec('contribution_city'),
                             'The annual contribution city renderer is required')
        return importlib.import_module('contribution_city').build_city_model(calendar)

    def calendar(self):
        start=date(2025,10,26)
        counts={'2025-10-27':9000,'2025-10-28':2,'2026-09-28':4,'2026-10-27':3,'2026-10-28':8000}
        return {'as_of':'2026-10-27','days':[{'date':(start+timedelta(days=i)).isoformat(),
                  'count':counts.get((start+timedelta(days=i)).isoformat(),0)} for i in range(368)]}

    def test_full_year_includes_older_activity_but_excludes_padding_and_future(self):
        model=self.model(self.calendar())
        self.assertEqual((model['start'],model['end']),('2025-10-28','2026-10-27'))
        self.assertEqual(len(model['days']),365)
        self.assertEqual((model['total'],model['active_days'],model['peak']),(9,3,4))

    def test_annual_window_preserves_leap_day(self):
        start=date(2023,3,2); end=date(2024,3,1)
        calendar={'as_of':end.isoformat(),'days':[{'date':(start+timedelta(days=i)).isoformat(),'count':0}
                  for i in range((end-start).days+1)]}
        calendar['days'][-2]['count']=7
        model=self.model(calendar)
        self.assertEqual((model['start'],model['end']),('2023-03-02','2024-03-01'))
        self.assertEqual(len(model['days']),366)
        self.assertEqual(model['total'],7)

    def test_building_heights_follow_actual_counts_and_zero_days_have_no_tower(self):
        model=self.model(self.calendar())
        rows={item['date']:item for item in model['days']}
        self.assertEqual(rows['2026-10-01']['height'],0)
        self.assertGreater(rows['2026-09-28']['height'],0)
        self.assertAlmostEqual(rows['2026-10-27']['height']/rows['2025-10-28']['height'],1.5)

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
