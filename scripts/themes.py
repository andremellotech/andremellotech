"""Readable colors over GitHub's own light, dark and dimmed backgrounds."""
TRANSPARENT = (0, 0, 0, 0)
THEMES = {
    'light': dict(name='light', text='#1f2328', muted='#59636e', blue='#0969da',
                  accent='#087e8b', line='#d1d9e0', portrait='#475668',
                  calendar=['#eff2f5', '#aceebb', '#4ac26b', '#2da44e', '#116329']),
    'dark': dict(name='dark', text='#e6edf3', muted='#9da7b3', blue='#79b8ff',
                 accent='#58dfe8', line='#3d444d', portrait='#b4c1d2',
                 calendar=['#151b23', '#033a16', '#196c2e', '#2ea043', '#56d364']),
}
