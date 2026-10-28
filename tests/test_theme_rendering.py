"""Exercise the shipped generator and the exact files deployed to Pages."""
from pathlib import Path
from html.parser import HTMLParser
import shutil, subprocess, sys, tempfile, unittest
from PIL import Image, ImageSequence
import hashlib, json

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
            calendar = json.loads((root/'data/contributions.json').read_text(encoding='utf-8'))
            # A controlled annual calendar makes animation/weight checks independent
            # of André's future activity. Production still renders the real data.
            for day in calendar['days']:day.update(count=0,level=0)
            for day,count,level in zip(calendar['days'][-4:],[1,3,8,21],[1,2,3,4]):
                day.update(count=count,level=level)
            (root/'data/contributions.json').write_text(json.dumps(calendar),encoding='utf-8')
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
                             ['profile-intro', 'status', 'activity', 'stack'])
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
                with Image.open(root / f'assets/activity-{theme}.png') as city:
                    self.assertEqual(city.size,(1200,918),'One card contains metrics and the full annual Aurora city')
                    self.assertEqual(city.mode,'RGBA')
                    self.assertEqual(city.getpixel((0,0))[3],0)
                self.assertLess((root / f'assets/activity-{theme}.png').stat().st_size, 1_000_000)
                city_animation = root / f'assets/activity-{theme}.gif'
                self.assertTrue(city_animation.exists(),'The annual city must animate on the profile itself')
                with Image.open(city_animation) as gif:
                    self.assertEqual(gif.size,(1200,918))
                    self.assertGreaterEqual(gif.n_frames,24,'The city needs a smooth visible animation')
                    self.assertEqual(gif.info.get('loop'),0,'The city must restart without reloading the profile')
                    durations=[frame.info['duration'] for frame in ImageSequence.Iterator(gif)]
                    self.assertEqual(sum(durations),10000,'A complete construction cycle must last ten seconds')
                    self.assertEqual(sum(durations[:-1]),3000,'Keep the three-second construction pace')
                    self.assertEqual(durations[-1],7000,'Keep the completed city visible for seven seconds')
                    gif.seek(0)
                    titles,labels,city_frames,floor_frames=set(),set(),set(),set()
                    for frame in ImageSequence.Iterator(gif):
                        rgba=frame.convert('RGBA')
                        self.assertEqual(rgba.getpixel((0,0))[3],0)
                        self.assertEqual(rgba.getpixel((70,370))[:3],
                                         (255,255,255) if theme=='light' else (13,17,23),
                                         'The city backdrop must match the rest of the profile')
                        titles.add(hashlib.sha256(rgba.crop((0,0,1200,354)).tobytes()).hexdigest())
                        labels.add(hashlib.sha256(rgba.crop((44,354,330,918)).tobytes()).hexdigest())
                        city_frames.add(hashlib.sha256(rgba.crop((340,354,1176,906)).tobytes()).hexdigest())
                        floor_frames.add(hashlib.sha256(rgba.crop((390,430,490,460)).tobytes()).hexdigest())
                    self.assertEqual(len(titles),1,'Contribution numbers and heading cannot move or flicker')
                    self.assertEqual(len(labels),1,'The city summary must stay fixed')
                    self.assertGreater(len(city_frames),12,'The city itself must visibly move')
                    self.assertEqual(len(floor_frames),1,'The annual floor must not rotate or wobble')
                    github_colors=(['#aceebb','#4ac26b','#2da44e','#116329'] if theme=='light'
                                   else ['#033a16','#196c2e','#2ea043','#56d364'])
                    final_image=rgba.crop((340,354,1176,906)).convert('RGB')
                    final_colors={color for _,color in final_image.getcolors(maxcolors=final_image.width*final_image.height)}
                    for color in github_colors:
                        self.assertIn(tuple(bytes.fromhex(color[1:])),final_colors,'Keep each GitHub level exact')
                self.assertLess(city_animation.stat().st_size,1_000_000,'Keep the corporate payload below 1 MB')
                self.assertTrue(any(f'activity-{theme}.gif' in s.get('srcset', '') for s in sources))
            self.assertNotIn('contribution-snake',readme_text)
            self.assertNotIn('cobrinha',readme_text)
            self.assertIn('últimos 12 meses',readme_text)
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
                self.assertEqual(im.size, (1200, 344),'Streaks belong to the activity card, without duplication')
            self.assertIn('Atividade e contribuições: contribuições totais',readme_text)
            self.assertNotIn('composição de código dos repositórios; total de contribuições',readme_text)
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
                for stem in ['profile-intro','activity']:
                    with Image.open(root/f'assets/{stem}-en-US-{theme}.gif') as gif:
                        self.assertGreater(gif.n_frames, 1)
                        self.assertEqual(gif.info.get('loop'),0)
                        self.assertEqual(gif.convert('RGBA').getpixel((0,0))[3], 0)
                        if stem=='activity':
                            durations=[frame.info['duration'] for frame in ImageSequence.Iterator(gif)]
                            self.assertEqual(sum(durations),10000)
                            self.assertEqual(durations[-1],7000)
                with Image.open(root/f'assets/activity-en-US-{theme}.png') as city:
                    self.assertEqual(city.size,(1200,918))
                self.assertIn('last 12 months',english_readme)
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
