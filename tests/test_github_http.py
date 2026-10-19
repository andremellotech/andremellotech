"""Verify transient GitHub failures are retried using a real local HTTP server."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import importlib.util, sys, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class GithubHttp(unittest.TestCase):
    def request_with_statuses(self, statuses):
        self.assertIsNotNone(importlib.util.find_spec('github_http'),
                             'GitHub requests need transient-failure recovery')
        from github_http import github_session
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                index = min(len(calls), len(statuses) - 1)
                calls.append(self.path)
                self.send_response(statuses[index])
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with github_session(backoff_factor=0) as session:
                response = session.get(f'http://127.0.0.1:{server.server_port}/public-data', timeout=2)
            return response, calls
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_transient_error_recovers_without_manual_rerun(self):
        response, calls = self.request_with_statuses([503, 502, 200])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(calls), 3)

    def test_permanent_error_does_not_loop(self):
        response, calls = self.request_with_statuses([404])
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
