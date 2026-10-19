"""Exercise the shipped generator and the exact files deployed to Pages."""
from pathlib import Path
from html.parser import HTMLParser
import shutil, subprocess, sys, tempfile, unittest
from PIL import Image, ImageSequence
import hashlib

ROOT = Path(__file__).resolve().parents[1]


class Elements(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class ThemeRendering(unittest.TestCase):
    def test_generated_profile_blends_with_the_page_and_keeps_only_contact_buttons(self):
        scratch = ROOT / 'work/theme-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            root = Path(folder)
            shutil.copytree(ROOT / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT / 'data', root / 'data')
            shutil.copytree(ROOT / 'assets/badges', root / 'assets/badges')
            for name in ['andre-ascii.png', 'andre-ascii.gif']:
                shutil.copy2(ROOT / 'assets' / name, root / 'assets' / name)
            subprocess.run([sys.executable, str(root / 'scripts/design.py')], check=True, capture_output=True)
            parsed = Elements((root / 'README.md').read_text(encoding='utf-8'))
            sources = [attrs for tag, attrs in parsed.tags if tag == 'source']
            self.assertTrue(any('prefers-color-scheme: dark' in s.get('media', '') for s in sources),
                            'The GitHub theme must choose the matching text colors')
            links = [attrs['href'] for tag, attrs in parsed.tags if tag == 'a']
            self.assertEqual(links, ['https://www.linkedin.com/in/aamello/',
                                     'https://github.com/andremellotech?tab=repositories'])
            self.assertFalse(any(tag == 'details' for tag, _ in parsed.tags))
            portrait_sources = [s for s in sources if 'profile-about-' in s.get('srcset', '')]
            self.assertTrue(all('.gif?' in s['srcset'] for s in portrait_sources),
                            'The requested animation must remain selected on this reduced-motion computer')
            for theme in ['light', 'dark']:
                animation = root / f'assets/profile-about-{theme}.gif'
                self.assertTrue(animation.exists(), 'The portrait must animate on the profile itself')
                with Image.open(animation) as gif:
                    self.assertGreater(gif.n_frames, 1)
                    self.assertEqual(gif.info.get('loop'), 0, 'The animation must repeat')
                    first = gif.convert('RGBA')
                    self.assertEqual(first.getpixel((0, 0))[3], 0, 'No rectangular background')
                    portraits, text = set(), set()
                    for frame in ImageSequence.Iterator(gif):
                        rgba = frame.convert('RGBA')
                        portraits.add(hashlib.sha256(rgba.crop((84, 0, 514, 550)).tobytes()).hexdigest())
                        text.add(hashlib.sha256(rgba.crop((532, 0, 1200, 550)).tobytes()).hexdigest())
                    self.assertGreater(len(portraits), 1, 'The portrait must move')
                    self.assertEqual(len(text), 1, 'Text must stay stable')
                self.assertLess(animation.stat().st_size, 2_000_000, 'Keep the corporate proxy payload small')
                self.assertTrue(any(f'profile-about-{theme}.gif' in s.get('srcset', '') for s in sources))
            images = []
            for theme in ['light', 'dark']:
                path = root / f'assets/profile-card-{theme}.png'
                self.assertTrue(path.exists(), f'Missing {theme} profile image')
                with Image.open(path) as im:
                    self.assertEqual(im.mode, 'RGBA')
                    self.assertEqual(im.getpixel((0, 0))[3], 0, 'Page background must remain visible')
                    self.assertEqual(im.getpixel((600, 235))[3], 0, 'Section spacing must stay transparent')
                    images.append(im.copy())
            self.assertEqual(images[0].size, images[1].size)
            self.assertNotEqual(images[0].tobytes(), images[1].tobytes(), 'Text must adapt to the selected theme')
            for name in ['footer-linkedin.png', 'footer-github.png']:
                with Image.open(root / 'assets' / name) as im:
                    self.assertEqual(im.getpixel((0, 0))[3], 0)
            subprocess.run([sys.executable, str(root / 'scripts/prepare_pages.py')], check=True, capture_output=True)
            for tag, attrs in parsed.tags:
                url = attrs.get('src') or attrs.get('srcset')
                if url:
                    self.assertTrue(url.startswith('https://andremellotech.github.io/andremellotech/assets/'))
                    name = url.split('/')[-1].split('?')[0]
                    self.assertTrue((root / 'work/pages/assets' / name).exists(), f'{name} must deploy before the README')


if __name__ == '__main__':
    unittest.main()
