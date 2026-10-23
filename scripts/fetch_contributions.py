"""Fetch public contributions. Never overwrite a valid snapshot on failure."""
import json
import os
import re
from collections import defaultdict
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup
from github_http import github_session

ROOT = Path(__file__).resolve().parents[1]

def parse_contributions(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    tips = {t.get('for'): t.get_text(' ', strip=True) for t in soup.select('tool-tip[for]')}
    days, seen = [], set()
    for cell in soup.select('[data-date][data-level]'):
        day = cell['data-date']
        date.fromisoformat(day)
        if day in seen: raise ValueError('Duplicate contribution date')
        seen.add(day)
        level = int(cell['data-level'])
        if not 0 <= level <= 4: raise ValueError('Invalid contribution level')
        raw = cell.get('data-count')
        if raw is None:
            tip = tips.get(cell.get('id'), '')
            if re.match(r'No contributions\b', tip): raw = '0'
            else:
                match = re.match(r'([\d,]+) contributions?\b', tip)
                if not match: raise ValueError(f'Missing count for {day}')
                raw = match.group(1).replace(',', '')
        count = int(raw)
        if count < 0: raise ValueError('Negative contribution count')
        days.append({'date':day,'count':count,'level':level})
    if not days: raise ValueError('No contribution days found')
    return sorted(days, key=lambda d: d['date'])

def derive_stats(days: list[dict], today: date) -> dict:
    days = sorted((d for d in days if date.fromisoformat(d['date']) <= today), key=lambda d:d['date'])
    if not days: raise ValueError('No past contribution days')
    counts = {date.fromisoformat(d['date']):d['count'] for d in days}
    current, cursor = 0, today
    if counts.get(cursor, 0) == 0: cursor -= timedelta(days=1)
    current_end = cursor
    while counts.get(cursor,0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    current_range = ({'start':(cursor+timedelta(days=1)).isoformat(), 'end':current_end.isoformat()}
                     if current else None)
    run = longest = 0
    longest_range = None
    previous = None
    monthly = defaultdict(int)
    for d in days:
        day = date.fromisoformat(d['date'])
        if previous is not None and day != previous + timedelta(days=1): run = 0
        run = run + 1 if d['count'] > 0 else 0
        if run > longest:
            longest = run
            longest_range = {'start':(day-timedelta(days=run-1)).isoformat(), 'end':day.isoformat()}
        monthly[d['date'][:7]] += d['count']
        previous = day
    best = max(days, key=lambda d:d['count'])
    return {'total':sum(d['count'] for d in days), 'current_streak':current,
            'longest_streak':longest,'best_day':{'date':best['date'],'count':best['count']},
            'monthly_totals':dict(monthly),
            'first_contribution':next((d['date'] for d in days if d['count'] > 0), None),
            'current_streak_range':current_range, 'longest_streak_range':longest_range}

def validate_calendar(days: list[dict], today: date) -> None:
    dates = sorted(date.fromisoformat(d['date']) for d in days)
    if len(dates) < 350: raise ValueError('Incomplete calendar; keeping previous snapshot')
    if dates[-1] < today - timedelta(days=1): raise ValueError('Stale calendar')
    if any(b != a + timedelta(days=1) for a,b in zip(dates,dates[1:])):
        raise ValueError('Calendar has missing or duplicate days')

def main():
    profile = json.loads((ROOT / 'profile.json').read_text(encoding='utf-8-sig'))
    username = profile['username']
    if not re.fullmatch(r'[A-Za-z0-9-]+', username): raise ValueError('Invalid username')
    with github_session() as session:
        response = session.get(f'https://github.com/users/{username}/contributions', timeout=30)
    response.raise_for_status()
    today = datetime.now(timezone.utc).date()
    days = [d for d in parse_contributions(response.text) if date.fromisoformat(d['date']) <= today]
    validate_calendar(days,today)
    data = {'username':username,'as_of':today.isoformat(),'days':days,'stats':derive_stats(days,today)}
    target = ROOT / 'data/contributions.json'
    target.parent.mkdir(exist_ok=True)
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    os.replace(temp,target)
    print(f"Fetched {len(days)} days: {data['stats']['total']} contributions")

if __name__ == '__main__': main()
