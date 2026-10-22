"""Readable colors over GitHub's own light, dark and dimmed backgrounds."""
TRANSPARENT = (0, 0, 0, 0)
THEMES = {
    'light': dict(name='light', text='#242d38', muted='#5b6572',
                  accent='#344050', line='#d5dde4', portrait='#526170', matte='#ffffff',
                  brand='#315978', brand_line='#c1d0dd',
                  calendar=['#eff2f5', '#aceebb', '#4ac26b', '#2da44e', '#116329']),
    'dark': dict(name='dark', text='#e5ebf1', muted='#9ba8b6',
                 accent='#c5d0dc', line='#303b47', portrait='#b4c1d2', matte='#0d1117',
                 brand='#8dabc5', brand_line='#3a5064',
                 calendar=['#151b23', '#033a16', '#196c2e', '#2ea043', '#56d364']),
}
