from pathlib import Path
import sys,unittest,importlib.util,json,tempfile
from datetime import date,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fetch_github_content import normalize_content

class ActivityUpdates(unittest.TestCase):
    def test_profile_generated_commits_do_not_cause_endless_updates(self):
        user={'login':'andremellotech','created_at':'2021-04-07'}
        repo={'name':'andremellotech','html_url':'https://github.com/andremellotech/andremellotech','pushed_at':'2026-10-17T10:00:00Z'}
        first=normalize_content(user,[repo],{})
        second=normalize_content(user,[dict(repo,pushed_at='2026-10-17T11:00:00Z')],{})
        self.assertEqual(first,second,'The updater must not react to its own generated commit timestamp')
    def test_actual_project_changes_are_still_detected(self):
        user={'login':'andremellotech','created_at':'2021-04-07'}
        repo={'name':'project','html_url':'https://github.com/andremellotech/project','pushed_at':'2026-10-17T10:00:00Z'}
        self.assertNotEqual(normalize_content(user,[repo],{}),normalize_content(user,[dict(repo,pushed_at='2026-10-17T11:00:00Z')],{}))
    def test_unified_panel_uses_calendar_data(self):
        spec=importlib.util.find_spec('activity_panel')
        self.assertIsNotNone(spec,'Unified contribution panel is missing')
        from activity_panel import contribution_summary,week_grid
        days=[{'date':(date(2026,1,1)+timedelta(days=i)).isoformat(),'count':c,'level':min(c,4)} for i,c in enumerate([0,3,2,0,1])]
        summary=contribution_summary({'user':{'public_repos':7}},{'as_of':'2026-01-05','days':days})
        self.assertEqual(summary['total'],6)
        self.assertEqual(summary['active_days'],3)
        self.assertEqual(summary['repositories'],7)
        self.assertEqual(summary['current_streak'],1)
        self.assertEqual(summary['longest_streak'],2)
        cells=week_grid(days)
        self.assertEqual(cells[0]['row'],4) # Thursday, with Sunday at row zero.
        self.assertEqual(cells[-1]['column'],1)
        self.assertEqual(sum(c['count'] for c in cells),6)

if __name__=='__main__':unittest.main()

