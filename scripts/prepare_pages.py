"""Stage only the public profile images and preview for GitHub Pages."""
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
def prepare(root=ROOT):
    dest=root/'work/pages'
    (dest/'assets').mkdir(parents=True,exist_ok=True)
    for name in ['profile-card.png','profile-card.gif','footer-linkedin.png','footer-github.png']:
        shutil.copy2(root/'assets'/name,dest/'assets'/name)
    shutil.copy2(root/'previa.html',dest/'index.html')
    (dest/'.nojekyll').write_text('')
    return dest
if __name__=='__main__':print('Public images staged:',prepare())
