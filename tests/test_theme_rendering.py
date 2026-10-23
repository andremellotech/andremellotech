"""Exercise the shipped generator and the exact files deployed to Pages."""
from pathlib import Path
from html.parser import HTMLParser
import shutil, subprocess, sys, tempfile, unittest
from PIL import Image, ImageSequence
import hashlib, json
from snake_fixture import write_snake_fixture

ROOT = Path(__file__).resolve().parents[1]


class Elements(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class ThemeRendering(unittest.TestCase):
    def test_profile_preserves_contacts_and_theme_assets_without_project_showcase(self):
        scratch = ROOT / 'work/theme-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            root = Path(folder)
            shutil.copytree(ROOT / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT / 'data', root / 'data')
            shutil.copytree(ROOT / 'assets/badges', root / 'assets/badges')
            for name in ['andre-ascii.png', 'andre-ascii.gif']:
                shutil.copy2(ROOT / 'assets' / name, root / 'assets' / name)
            write_snake_fixture(root)
            calendar = json.loads((root/'data/contributions.json').read_text(encoding='utf-8'))
            (root/'data/contributions-history.json').write_text(json.dumps(calendar), encoding='utf-8')
            subprocess.run([sys.executable, str(root / 'scripts/design.py')], check=True, capture_output=True)
            parsed = Elements((root / 'README.md').read_text(encoding='utf-8'))
            sources = [attrs for tag, attrs in parsed.tags if tag == 'source']
            self.assertTrue(any('prefers-color-scheme: dark' in s.get('media', '') for s in sources),
                            'The GitHub theme must choose the matching text colors')
            links = [attrs['href'] for tag, attrs in parsed.tags if tag == 'a']
            language_urls = ['https://github.com/andremellotech',
                             'https://github.com/andremellotech/andremellotech/blob/main/README.en-US.md']
            self.assertEqual(links[:2], language_urls, 'Both language buttons must work on GitHub')
            self.assertEqual(links[2:], ['https://www.linkedin.com/in/aamello/',
                                         'https://github.com/andremellotech?tab=repositories',
                                         'mailto:andremello@outlook.com'],
                             'All three contact buttons must keep the correct destinations')
            readme_text = (root / 'README.md').read_text(encoding='utf-8')
            self.assertNotIn('| Projeto | Aplicação |', readme_text)
            self.assertNotIn('Projetos em destaque', readme_text)
            self.assertNotIn('<table', (root/'previa.html').read_text(encoding='utf-8'))
            self.assertFalse(any('profile-project' in (a.get('src', '') + a.get('srcset', ''))
                                 for _, a in parsed.tags), 'Do not show repository image cards')
            self.assertFalse(any(tag == 'details' for tag, _ in parsed.tags))
            # The profile leads with live GitHub activity, not a duplicate resume.
            panels = [a['src'] for tag, a in parsed.tags if tag == 'img' and a.get('width') == '100%']
            self.assertEqual([url.split('/')[-1].split('-light.')[0] for url in panels],
                             ['profile-intro', 'status', 'contribution-snake', 'stack'])
            for resume_text in ['KPMG', '660 milhões', 'UFPR', 'Mestre em Administração', 'FAPESP']:
                self.assertNotIn(resume_text, readme_text, 'Career details belong on LinkedIn')
            for english in ['Total Contributions', 'Current Streak', 'Longest Streak', 'Present', 'Data & Analytics', 'MSc.']:
                self.assertNotIn(english, readme_text)
            portrait_sources = [s for s in sources if 'profile-intro-' in s.get('srcset', '')]
            self.assertEqual(len(portrait_sources), 2, 'A single animated introduction adapts to both themes')
            self.assertTrue(all('.gif?' in s['srcset'] for s in portrait_sources),
                            'The requested animation must remain selected on this reduced-motion computer')
            for theme in ['light', 'dark']:
                animation = root / f'assets/profile-intro-{theme}.gif'
                self.assertTrue(animation.exists(), 'The portrait must animate on the profile itself')
                with Image.open(animation) as gif:
                    self.assertGreater(gif.n_frames, 1)
                    self.assertEqual(gif.info.get('loop'), 0, 'The animation must repeat')
                    first = gif.convert('RGBA')
                    self.assertEqual(first.getpixel((0, 0))[3], 0, 'No rectangular background')
                    portraits, text = set(), set()
                    for frame in ImageSequence.Iterator(gif):
                        rgba = frame.convert('RGBA')
                        portraits.add(hashlib.sha256(rgba.crop((850, 18, 1140, 382)).tobytes()).hexdigest())
                        text.add(hashlib.sha256(rgba.crop((0, 0, 740, rgba.height)).tobytes()).hexdigest())
                    self.assertGreater(len(portraits), 1, 'The portrait must move')
                    self.assertEqual(len(text), 1, 'Text must stay stable')
                    gif.seek(0)
                    duration = sum(frame.info.get('duration', 100) for frame in ImageSequence.Iterator(gif))
                with Image.open(root / 'assets/andre-ascii.gif') as original:
                    source_duration = sum(frame.info.get('duration', 100) for frame in ImageSequence.Iterator(original))
                self.assertAlmostEqual(duration, source_duration, delta=20, msg='Preserve the original animation pace')
                self.assertLess(animation.stat().st_size, 1_000_000, 'Keep the corporate proxy payload below 1 MB')
                self.assertTrue(any(f'profile-intro-{theme}.gif' in s.get('srcset', '') for s in sources))
                with Image.open(root / f'assets/contribution-snake-{theme}.gif') as gif:
                    self.assertGreater(gif.n_frames, 2, 'The live contribution section must animate')
                    self.assertEqual(gif.info.get('loop'), 0)
                    self.assertEqual(gif.convert('RGBA').getpixel((0, 0))[3], 0)
                    # Persistent titles must not blink or disappear as the snake moves.
                    title_frames = {hashlib.sha256(frame.convert('RGBA').crop((0, 0, 1200, 60)).tobytes()).hexdigest()
                                    for frame in ImageSequence.Iterator(gif)}
                    self.assertEqual(len(title_frames), 1)
                self.assertLess((root / f'assets/contribution-snake-{theme}.gif').stat().st_size, 1_000_000)
                self.assertTrue(any(f'contribution-snake-{theme}.gif' in s.get('srcset', '') for s in sources))
            images = []
            for theme in ['light', 'dark']:
                path = root / f'assets/profile-card-{theme}.png'
                self.assertTrue(path.exists(), f'Missing {theme} profile image')
                with Image.open(path) as im:
                    self.assertEqual(im.mode, 'RGBA')
                    self.assertEqual(im.getpixel((0, 0))[3], 0, 'Page background must remain visible')
                    with Image.open(root/f'assets/intro-background-{theme}.png') as intro:
                        self.assertEqual(intro.size, (1200, 304), 'Keep the introduction compact')
                        self.assertEqual(im.getpixel((600, intro.height+14))[3], 0,
                                         'Section spacing must stay transparent')
                    images.append(im.copy())
            self.assertEqual(images[0].size, images[1].size)
            self.assertNotEqual(images[0].tobytes(), images[1].tobytes(), 'Text must adapt to the selected theme')
            badge_images = [attrs['src'] for tag, attrs in parsed.tags if tag == 'img' and attrs.get('height') == '22']
            self.assertEqual(len(badge_images), 3, 'Three contact badges without duplicated statistics')
            for name in ['badge-linkedin.png', 'badge-github.png', 'badge-email.png']:
                with Image.open(root / 'assets' / name) as im:
                    self.assertEqual(im.height, 56, 'Contact source images stay sharp at the compact display height')
                    self.assertEqual(im.getpixel((0, 0))[3], 0, 'Rounded corners stay transparent')
            with Image.open(root / 'assets/status-light.png') as im:
                self.assertEqual(im.size, (1200, 640))
            for theme in ['light', 'dark']:
                with Image.open(root / f'assets/stack-{theme}.png') as im:
                    self.assertEqual(im.mode, 'RGBA')
                    self.assertEqual(im.size, (1200, 568), 'The stack excludes the academic resume')
                    self.assertEqual(im.getpixel((0, 0))[3], 0)
            subprocess.run([sys.executable, str(root / 'scripts/prepare_pages.py')], check=True, capture_output=True)
            english = Elements((root/'README.en-US.md').read_text(encoding='utf-8'))
            self.assertEqual([a['href'] for tag, a in english.tags if tag == 'a'], links,
                             'English must return to the Portuguese profile and keep contact links')
            english_panels = [a['src'] for tag, a in english.tags if tag == 'img' and a.get('width') == '100%']
            self.assertEqual(len(english_panels), 4)
            self.assertTrue(all('-en-US-' in url for url in english_panels),
                            'English needs translated pictures, not only an English heading')
            english_readme = (root/'README.en-US.md').read_text(encoding='utf-8')
            self.assertIn('Data and automation in practice.', english_readme)
            self.assertNotIn('Experience and results', english_readme)
            self.assertNotIn('KPMG', english_readme)
            self.assertNotIn('Tecnologias e formação', english_readme)
            for theme in ['light', 'dark']:
                for stem in ['profile-intro', 'contribution-snake']:
                    with Image.open(root/f'assets/{stem}-en-US-{theme}.gif') as gif:
                        self.assertGreater(gif.n_frames, 1)
                        self.assertEqual(gif.info.get('loop'), 0)
                        self.assertEqual(gif.convert('RGBA').getpixel((0,0))[3], 0)
                with Image.open(root/f'assets/status-{theme}.png') as pt, Image.open(root/f'assets/status-en-US-{theme}.png') as en:
                    self.assertEqual(pt.size, en.size, 'Both languages keep the same proportions')
                    self.assertNotEqual(pt.tobytes(), en.tobytes(), 'The card text must actually be translated')
            self.assertTrue((root/'work/pages/en-US/index.html').exists())
            for tag, attrs in parsed.tags + english.tags:
                url = attrs.get('src') or attrs.get('srcset')
                if url:
                    self.assertTrue(url.startswith('https://andremellotech.github.io/andremellotech/assets/'))
                    name = url.split('/')[-1].split('?')[0]
                    self.assertTrue((root / 'work/pages/assets' / name).exists(), f'{name} must deploy before the README')


if __name__ == '__main__':
    unittest.main()
