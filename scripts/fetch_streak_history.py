"""Collect complete public history directly from GitHub, with daily historical caching."""
import json, os
from datetime import date, datetime, timezone
from pathlib import Path
from fetch_contributions import parse_contributions, derive_stats
from github_http import github_session

ROOT = Path(__file__).resolve().parents[1]


def collect_history(get_days, created, today, cache):
    years, all_days = {}, []
    for year in range(created.year, today.year + 1):
        start, end = max(created, date(year, 1, 1)), min(today, date(year, 12, 31))
        cached = cache.get('years', {}).get(str(year), {})
        days = (cached['days'] if year < today.year and cached.get('checked_on') == today.isoformat()
                else get_days(year))
        days = sorted((d for d in days if start.isoformat() <= d['date'] <= end.isoformat()), key=lambda d:d['date'])
        actual = [date.fromisoformat(d['date']) for d in days]
        if (len(set(actual)) != len(actual) or len(actual) != (end-start).days+1
                or not actual or actual[0] != start or actual[-1] != end
                or any(d['count'] < 0 for d in days)):
            raise ValueError(f'Incomplete or invalid contribution history for {year}')
        years[str(year)] = {'checked_on':today.isoformat(), 'days':days}
        all_days.extend(days)
    return {'as_of':today.isoformat(), 'days':all_days, 'years':years, 'stats':derive_stats(all_days, today)}


def main():
    profile = json.loads((ROOT/'data/github-content.json').read_text(encoding='utf-8'))['user']
    username = profile['login']
    created = date.fromisoformat(profile['created_at'][:10])
    today = datetime.now(timezone.utc).date()
    target = ROOT/'data/contributions-history.json'
    cache = json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
    if cache.get('username') != username:
        cache = {}
    with github_session() as session:
        def get_days(year):
            response = session.get(f'https://github.com/users/{username}/contributions',
                                   params={'from':f'{year}-01-01','to':f'{year}-12-31'}, timeout=30)
            response.raise_for_status()
            return parse_contributions(response.text)
        result = collect_history(get_days, created, today, cache)
    result['username'] = username
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    os.replace(temp, target)
    print(f"Public history collected: {result['stats']['total']} contributions since {created.year}")


if __name__ == '__main__':
    main()
