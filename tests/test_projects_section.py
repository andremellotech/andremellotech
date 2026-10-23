from pathlib import Path
import sys, unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from projects_section import featured, projects_markdown, projects_html


class ProjectsSection(unittest.TestCase):
    def test_only_public_owned_described_projects_are_shown(self):
        repos = [
            dict(name='novo', description='A | B', html_url='https://github.com/u/novo', pushed_at='2026-10-22'),
            dict(name='privado', description='Private', private=True, html_url='https://github.com/u/privado'),
            dict(name='estrangeiro', description='Wrong owner', html_url='https://github.com/other/estrangeiro'),
            dict(name='copia', description='Fork', fork=True, html_url='https://github.com/u/copia'),
            dict(name='u', description='Profile', html_url='https://github.com/u/u'),
            dict(name='sem', description=None, html_url='https://github.com/u/sem'),
            dict(name='antigo', description='Old', html_url='https://github.com/u/antigo'),
        ]
        self.assertEqual([r['name'] for r in featured({'repositories': repos}, 'u')], ['novo', 'antigo'])

    def test_escapes_html_and_markdown_in_descriptions(self):
        content = {'repositories': [dict(name='demo', html_url='https://github.com/u/demo',
                                        description='A | B <img src=x> [clicar](https://evil.test)')]}
        markdown = projects_markdown(content, 'u')
        self.assertIn('A \\| B', markdown)
        self.assertIn('&lt;img src=x&gt;', markdown)
        self.assertIn('\\[clicar\\]', markdown)
        self.assertNotIn('<img', projects_html(content, 'u'))
