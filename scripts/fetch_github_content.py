"""Collect public GitHub data; optional Actions token avoids anonymous limits."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]

def normalize_content(user:dict,repos:list,languages:dict)->dict:
    if not user.get('login') or not user.get('created_at'):
        raise ValueError('Incomplete GitHub user response')
    fields=['login','name','bio','public_repos','followers','following','created_at','html_url']
    public=[]
    for repo in repos:
        if repo.get('private'): continue
        if not repo.get('name') or not repo.get('html_url','').startswith('https://github.com/'):
            raise ValueError('Invalid repository response')
        entry={k:repo.get(k) for k in ['name','description','html_url','language','fork','stargazers_count','forks_count','pushed_at']}
        # Generated artwork changes this timestamp; it is not a new project update.
        if repo['name'].lower()==user['login'].lower():entry['pushed_at']=None
        public.append(entry)
    public.sort(key=lambda r:(r.get('pushed_at') or '',r['name']),reverse=True)
    totals={}
    for repo in public[:6]:
        for lang,count in languages.get(repo['name'],{}).items():
            if not isinstance(count,int) or count<0: raise ValueError('Invalid language byte count')
            totals[lang]=totals.get(lang,0)+count
    return {'user':{key:user.get(key) for key in fields},'repositories':public,
            'languages':dict(sorted(totals.items(),key=lambda item:item[1],reverse=True)),
            'languages_scope':'Até seis repositórios públicos atualizados mais recentemente'}

def main():
    username=json.loads((ROOT/'profile.json').read_text(encoding='utf-8-sig'))['username']
    if not re.fullmatch(r'[A-Za-z0-9-]+',username): raise ValueError('Invalid username')
    session=requests.Session()
    session.headers.update({'Accept':'application/vnd.github+json','User-Agent':'andremellotech-profile','X-GitHub-Api-Version':'2022-11-28'})
    token=os.getenv('GITHUB_TOKEN')
    if token: session.headers['Authorization']=f'Bearer {token}'
    def get(url):
        response=session.get(url,timeout=30)
        response.raise_for_status()
        return response
    user=get(f'https://api.github.com/users/{username}').json()
    url=f'https://api.github.com/users/{username}/repos?per_page=100&sort=pushed'
    repos=[]
    while url:
        response=get(url)
        batch=response.json()
        if not isinstance(batch,list): raise ValueError('Invalid repository list')
        repos.extend(batch)
        url=response.links.get('next',{}).get('url')
    langs={}
    for repo in [r for r in repos if r.get('name','').lower()!=username.lower()][:6]:
        langs[repo['name']]=get(f'https://api.github.com/repos/{username}/{repo["name"]}/languages').json()
    data=normalize_content(user,repos,langs)
    data['as_of']=datetime.now(timezone.utc).date().isoformat()
    temp=ROOT/'data/github-content.tmp'
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temp,ROOT/'data/github-content.json')
    print(f'Fetched {len(data["repositories"])} public repositories; {len(data["languages"])} detected languages')

if __name__=='__main__': main()
