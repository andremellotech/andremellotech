"""Native project links: public metadata, no repository screenshots."""
from html import escape
import re

MAX_PROJECTS = 3
TITLES = {'financial-performance-analytics': 'Performance financeira',
          'finance-close-automation': 'Automação de fechamento',
          'sap-project-financial-control-tower': 'Controle financeiro de projetos SAP',
          'sap-procurement-control-tower': 'Controle de compras SAP',
          'mello-charts-desktop': 'Mello Charts para PowerPoint'}


def _escape(value):
    text = escape(' '.join(str(value).split()), quote=False)
    return re.sub(r'([\\`*_\[\]|])', r'\\\1', text)


def featured(content, username):
    repos = [r for r in content['repositories']
             if not r.get('fork') and not r.get('private') and r.get('description')
             and r.get('name', '').lower() != username.lower()
             and re.fullmatch(r'[A-Za-z0-9_.-]+', r.get('name', ''))
             and r.get('html_url') == f'https://github.com/{username}/{r["name"]}']
    return sorted(repos, key=lambda r: r.get('pushed_at') or '', reverse=True)[:MAX_PROJECTS]


def _title(repo):
    return TITLES.get(repo['name'], repo['name'].replace('-', ' ').replace('_', ' ').capitalize())


def projects_markdown(content, username):
    projects = featured(content, username)
    if not projects:
        return ''
    rows = ['| Projeto | Aplicação |', '|:--|:--|']
    for repo in projects:
        rows.append(f'| **[{_escape(_title(repo))}]({repo["html_url"]})** | {_escape(repo["description"])} |')
    return '\n'.join(rows) + '\n'


def projects_html(content, username):
    projects = featured(content, username)
    if not projects:
        return ''
    head = '<tr><th align="left">Projeto</th><th align="left">Aplicação</th></tr>'
    body = ''.join('<tr><td><b><a href="' + escape(r['html_url']) + '">' + escape(_title(r))
                   + '</a></b></td><td>' + escape(' '.join(r['description'].split())) + '</td></tr>'
                   for r in projects)
    return '<table>' + head + body + '</table>'
