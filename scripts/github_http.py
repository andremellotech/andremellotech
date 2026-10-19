"""Retry temporary read failures while keeping permanent errors visible."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def github_session(backoff_factor=2):
    retry = Retry(total=3, connect=3, read=3, status=3,
                  backoff_factor=backoff_factor,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(['GET']),
                  respect_retry_after_header=True)
    session = requests.Session()
    session.headers.update({'User-Agent': 'andremellotech-profile',
                            'Cache-Control': 'no-cache'})
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.mount('http://', HTTPAdapter(max_retries=retry))
    return session
