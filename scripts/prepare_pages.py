"""Stage only the public profile images and preview for GitHub Pages."""
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
def prepare(root=ROOT):
    dest=root/'work/pages'
    (dest/'assets').mkdir(parents=True,exist_ok=True)
    images = ['profile-card-light.png','profile-card-dark.png']
    images.extend(f'badge-{stem}.png' for stem in ['linkedin','github','email'])
    for theme in ['light', 'dark']:
        images.extend(f'{stem}-{theme}.{extension}' for stem, extension in
                      [('profile-intro', 'png'), ('profile-intro', 'gif'), ('status', 'png'),
                       ('contribution-snake', 'gif'), ('stack', 'png')])
    for name in images:
        shutil.copy2(root/'assets'/name,dest/'assets'/name)
    shutil.copy2(root/'previa.html',dest/'index.html')
    (dest/'.nojekyll').write_text('')
    return dest
if __name__=='__main__':print('Public images staged:',prepare())
