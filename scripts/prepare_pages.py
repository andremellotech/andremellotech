"""Stage only the public profile images and preview for GitHub Pages."""
from pathlib import Path
import shutil
from profile_i18n import DEFAULT, LOCALES, localized, preview_name

ROOT=Path(__file__).resolve().parents[1]
def prepare(root=ROOT):
    dest=root/'work/pages'
    (dest/'assets').mkdir(parents=True,exist_ok=True)
    images = []
    images.extend(f'badge-{stem}.png' for stem in ['linkedin','github','email'])
    images.extend(f'language-{locale}.png' for locale in LOCALES)
    for locale in LOCALES:
        for theme in ['light', 'dark']:
            images.append(f'{localized("profile-card",locale)}-{theme}.png')
            images.extend(f'{localized(stem,locale)}-{theme}.{extension}' for stem, extension in
                          [('profile-intro', 'png'), ('profile-intro', 'gif'), ('status', 'png'),
                           ('activity', 'png'), ('stack', 'png')])
    for name in images:
        shutil.copy2(root/'assets'/name,dest/'assets'/name)
    shutil.copy2(root/'previa.html',dest/'index.html')
    (dest/'en-US').mkdir(exist_ok=True)
    english = (root/preview_name('en-US')).read_text(encoding='utf-8').replace('./assets/', '../assets/')
    (dest/'en-US/index.html').write_text(english, encoding='utf-8')
    (dest/'.nojekyll').write_text('')
    return dest
if __name__=='__main__':print('Public images staged:',prepare())
