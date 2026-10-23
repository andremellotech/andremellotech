"""Readable colors over GitHub's own light, dark and dimmed backgrounds."""
TRANSPARENT = (0, 0, 0, 0)
THEMES = {
    'light': dict(name='light', text='#1b2f46', muted='#53667d',
                  accent='#163b66', line='#cbdcf0', portrait='#26629a', matte='#ffffff',
                  brand='#0969da', brand_line='#adc9e8', surface='#eef5ff',
                  surface_end='#ffffff', icon_bg='#deecff', highlight='#0797b8',
                  calendar=['#eff2f5', '#aceebb', '#4ac26b', '#2da44e', '#116329']),
    'dark': dict(name='dark', text='#eaf3ff', muted='#9eb1c8',
                 accent='#d9eaff', line='#2a4363', portrait='#78b9e8', matte='#0d1117',
                 brand='#58a6ff', brand_line='#3b628c', surface='#13263b',
                 surface_end='#101923', icon_bg='#173657', highlight='#55c5df',
                 calendar=['#151b23', '#033a16', '#196c2e', '#2ea043', '#56d364']),
}
