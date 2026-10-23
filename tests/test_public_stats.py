from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
import sys, unittest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_github_content


class PublicStats(unittest.TestCase):
    def test_counts_only_public_authored_activity(self):
        collect = getattr(fetch_github_content, 'collect_stats', None)
        self.assertTrue(callable(collect), 'The profile needs a public statistics collector')
        def get(url):
            parsed = urlparse(url)
            query = parse_qs(parsed.query)['q'][0]
            if 'author:andre' not in query or 'is:public' not in query:
                raise ValueError('Query may include private or unrelated activity')
            total = 13 if parsed.path == '/search/commits' else 5 if 'type:pr' in query else 2
            return SimpleNamespace(json=lambda: {'total_count': total, 'incomplete_results': False})
        self.assertEqual(collect(get, 'andre', [{'stargazers_count': 3}, {'stargazers_count': 7}]),
                         {'stars': 10, 'commits': 13, 'pull_requests': 5, 'issues': 2})

    def test_unavailable_or_incomplete_results_are_not_reported_as_current_totals(self):
        collect = getattr(fetch_github_content, 'collect_stats', None)
        self.assertTrue(callable(collect))
        for body in [None, {'total_count': 50, 'incomplete_results': True},
                     {'total_count': True, 'incomplete_results': False},
                     {'total_count': -1, 'incomplete_results': False}]:
            with self.subTest(body=body):
                def get(url):
                    if body is None:
                        raise requests.HTTPError('Temporary search failure')
                    return SimpleNamespace(json=lambda: body)
                self.assertEqual(collect(get, 'andre', []),
                                 {'stars': 0, 'commits': None, 'pull_requests': None, 'issues': None})
