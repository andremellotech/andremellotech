"""Readable colors over GitHub's own light, dark and dimmed backgrounds."""
TRANSPARENT = (0, 0, 0, 0)
THEMES = {
    'light': dict(name='light', text='#1f2328', muted='#59636e',
                  accent='#3d444d', line='#d1d9e0', portrait='#475668', matte='#ffffff',
                  calendar=['#eff2f5', '#aceebb', '#4ac26b', '#2da44e', '#116329']),
    'dark': dict(name='dark', text='#e6edf3', muted='#9da7b3',
                 accent='#c9d1d9', line='#3d444d', portrait='#b4c1d2', matte='#0d1117',
                 calendar=['#151b23', '#033a16', '#196c2e', '#2ea043', '#56d364']),
}
