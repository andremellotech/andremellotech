"""Stage only the public profile images and preview for GitHub Pages."""
from pathlib import Path
import shutil
from portfolio import selected_projects

ROOT=Path(__file__).resolve().parents[1]
def prepare(root=ROOT):
    dest=root/'work/pages'
    (dest/'assets').mkdir(parents=True,exist_ok=True)
    images = ['profile-card-light.png','profile-card-dark.png','footer-linkedin.png','footer-github.png']
    projects = selected_projects(root)
    for theme in ['light', 'dark']:
        images.extend(f'profile-{stem}-{theme}.{extension}' for stem, extension in
                      [('header', 'png'), ('about', 'png'), ('about', 'gif'), ('body', 'png')])
        if projects:
            images.append(f'profile-projects-heading-{theme}.png')
            images.extend(f'profile-project-{index + 1}-{theme}.png' for index in range(len(projects)))
    for name in images:
        shutil.copy2(root/'assets'/name,dest/'assets'/name)
    shutil.copy2(root/'previa.html',dest/'index.html')
    (dest/'.nojekyll').write_text('')
    return dest
if __name__=='__main__':print('Public images staged:',prepare())
