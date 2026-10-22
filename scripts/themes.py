"""Readable colors over GitHub's own light, dark and dimmed backgrounds."""
TRANSPARENT = (0, 0, 0, 0)
THEMES = {
    'light': dict(name='light', text='#182b43', muted='#52677c',
                  accent='#223b58', line='#d4e0ec', portrait='#165e94', matte='#ffffff',
                  brand='#1f5fb5', brand_line='#8eb3d6', cyan='#076f7d', copper='#9b562b',
                  surfaces=['#f0f6ff', '#eef9f9', '#fcf5ee'],
                  calendar=['#eff2f5', '#aceebb', '#4ac26b', '#2da44e', '#116329']),
    'dark': dict(name='dark', text='#edf4ff', muted='#a6b8ce',
                 accent='#d3e3f6', line='#294159', portrait='#75b8e9', matte='#0d1117',
                 brand='#77b5ff', brand_line='#416e97', cyan='#44d3d3', copper='#e2ad7c',
                 surfaces=['#101f31', '#0d262d', '#2b221e'],
                 calendar=['#151b23', '#033a16', '#196c2e', '#2ea043', '#56d364']),
}
