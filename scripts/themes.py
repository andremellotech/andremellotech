"""Readable colors over GitHub's own light, dark and dimmed backgrounds."""
TRANSPARENT = (0, 0, 0, 0)
THEMES = {
    'light': dict(name='light', text='#1f2328', muted='#59636e',
                  accent='#273c50', line='#d1d9e0', portrait='#294b70', matte='#ffffff',
                  brand='#294b70', brand_line='#a6b7c8', surface='#f6f8fa',
                  calendar=['#eff2f5', '#aceebb', '#4ac26b', '#2da44e', '#116329']),
    'dark': dict(name='dark', text='#f0f6fc', muted='#9198a1',
                 accent='#d0dae5', line='#30363d', portrait='#a7bdd3', matte='#0d1117',
                 brand='#a7c3df', brand_line='#52677d', surface='#151b23',
                 calendar=['#151b23', '#033a16', '#196c2e', '#2ea043', '#56d364']),
}
