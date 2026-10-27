"""Two complete profile editions built from the same data and layout."""
DEFAULT = 'pt-BR'
LOCALES = (DEFAULT, 'en-US')

EN = {
    'CIDADE DE CONTRIBUIÇÕES': 'CONTRIBUTION CITY',
    'contribuições nos': 'contributions in the',
    'últimos 12 meses': 'last 12 months',
    'Últimos 12 meses': 'Last 12 months',
    'contribuições em 12 meses': 'contributions in 12 months',
    'dias ativos': 'active days',
    'Pico diário': 'Daily peak',
    'Cada bloco representa um dia.': 'Each block represents one day.',
    'Altura proporcional às contribuições.': 'Height is proportional to contributions.',
    'Contribuições em 3D': 'Contributions in 3D',
    'DADOS · AUTOMAÇÃO · ENGENHARIA': 'DATA · AUTOMATION · ENGINEERING',
    'Dados e automação na prática.': 'Data and automation in practice.',
    'Projetos de análise de dados, integrações e engenharia.': 'Data analytics, integration and engineering projects.',
    'Tecnologias e ferramentas': 'Technology and tools',
    'Sistemas e colaboração': 'Systems and collaboration',
    'Linguagens · conhecimentos': 'Languages · working knowledge',
    'CONSULTORIA · ENGENHARIA · DADOS': 'CONSULTING · ENGINEERING · DATA',
    'Engenharia, dados e governança.': 'Engineering, data and governance.',
    'Da estratégia à execução.': 'From strategy to execution.',
    'Portfólio, PMO e automação com foco em resultados.': 'Portfolio governance, PMO and automation.',
    'Consultor na KPMG Brasil · Mais de 6 anos de experiência': 'Consultant at KPMG Brasil · 6+ years of experience',
    'Engenheiro Civil · Mestre em Administração': 'Civil Engineer · MSc in Administration',
    'Atuação e resultados': 'Experience and results',
    'Engenharia e visão de negócio para transformar informação em ação.': 'Engineering rigor and business insight to turn information into action.',
    'R$ 660 mi': 'BRL 660M',
    'Portfólio de ativos': 'Asset portfolio',
    'sob governança': 'under governance',
    '+25%': '+25%',
    'Eficiência operacional': 'Efficiency gain',
    'com dados e automação': 'data and automation',
    '240 h/ano': '240 h/year',
    'Retrabalho eliminado': 'Rework eliminated',
    'por meio de automação': 'through automation',
    'Até 80': 'Up to 80',
    'Liderança de equipes': 'Team leadership',
    'multifuncionais': 'across functions',
    'Governança e PMO': 'Governance and PMO',
    'Portfólio, indicadores executivos e acompanhamento físico-financeiro.': 'Portfolio oversight, executive KPIs and physical and financial progress.',
    'Engenharia e contratos': 'Engineering contracts',
    'Ativos físicos, terceiros e contratos com CAPEX de até R$ 125 milhões.': 'Physical assets, vendors and contracts with CAPEX up to BRL 125 million.',
    'Dados e automação': 'Data and automation',
    'Painéis executivos e integração de dados com Power BI, SAP e Power Automate.': 'Executive dashboards and data integration with Power BI, SAP and Power Automate.',
    'Tecnologias e formação': 'Technology and education',
    'Dados, sistemas e automação': 'Data, systems and automation',
    'Análise, integração de dados e automação de rotinas.': 'Analytics, data integration and workflow automation.',
    'Sistemas e comunicação': 'Systems and communication',
    'Office 365, apresentações executivas': 'Office 365, executive presentations',
    'e organização de informações.': 'and information management.',
    'Linguagens e versionamento': 'Languages and version control',
    'Banco de dados · experiência anterior': 'Databases · previous experience',
    'MySQL em servidores de Tibia e GTA V / FiveM.': 'MySQL for Tibia and GTA V / FiveM servers.',
    'Formação em evolução': 'Continuing education',
    'Engenharia Elétrica · São Judas Tadeu (em curso)': 'Electrical Engineering · São Judas Tadeu (in progress)',
    'Engenharia de Segurança do Trabalho · UFPR (em curso)': 'Occupational Safety Engineering · UFPR (in progress)',
    'Pós-graduação em Construção Civil · FAVENI': 'Postgraduate studies in Civil Construction · FAVENI',
    'Pesquisa e reconhecimento': 'Research and recognition',
    'Ex-bolsista FAPESP e CAPES': 'Former FAPESP and CAPES scholarship holder',
    'Artigo na Brazilian Administration Review': 'Article in Brazilian Administration Review',
    'Destaque profissional KPMG · FY25': 'KPMG Professional Distinction · FY25',
    'Destaque REIAd · 2023 e 2024': 'REIAd recognition · 2023 and 2024',
    'Presença no GitHub': 'GitHub presence',
    'Atividade pública': 'Public activity',
    'Repositórios públicos': 'Public repositories',
    'Estrelas recebidas': 'Stars received',
    'Alterações registradas': 'Recorded commits',
    'Propostas de alteração': 'Pull requests',
    'Ocorrências criadas': 'Issues opened',
    'Seguidores': 'Followers',
    'Linguagens nos repositórios': 'Repository languages',
    'Distribuição por bytes de código': 'Distribution by code bytes',
    'Contribuições totais': 'Total contributions',
    'Maior sequência': 'Longest streak',
    'Sequência atual': 'Current streak',
    'Atividade e contribuições': 'Activity and contributions',
    'Menos': 'Less', 'Mais': 'More', 'Seg': 'Mon', 'Qua': 'Wed', 'Sex': 'Fri', 'Outras': 'Other',
    'LinkedIn — André Mello': 'LinkedIn — André Mello',
    'GitHub — explorar meus repositórios': 'GitHub — explore my repositories',
    'E-mail — andremello@outlook.com': 'Email — andremello@outlook.com',
    'Linguagens por bytes em até seis repositórios públicos recentes: ': 'Languages by bytes across up to six recent public repositories: ',
}


def validate(locale):
    if locale not in LOCALES:
        raise ValueError('Unsupported profile locale: ' + locale)
    return locale


def tr(locale, text):
    validate(locale)
    return text if locale == DEFAULT else EN[text]


def localized(stem, locale=DEFAULT):
    validate(locale)
    return stem if locale == DEFAULT else stem + '-' + locale


def readme_name(locale=DEFAULT):
    return 'README.md' if validate(locale) == DEFAULT else 'README.en-US.md'


def preview_name(locale=DEFAULT):
    return 'previa.html' if validate(locale) == DEFAULT else 'preview.en-US.html'


def preview_image(theme, locale=DEFAULT):
    validate(locale)
    return ('PREVIA.png' if theme == 'light' else 'PREVIA-ESCURO.png') if locale == DEFAULT else f'PREVIEW-en-US-{theme}.png'


INTRO_ALT = {
    DEFAULT: 'André Mello — Dados, automação e engenharia. Dados e automação na prática. '
             'Projetos de análise de dados, integrações e engenharia. Retrato ASCII animado.',
    'en-US': 'André Mello — Data, automation and engineering. Data and automation in practice. '
             'Data analytics, integration and engineering projects. Animated ASCII portrait.',
}
PROFESSIONAL_ALT = {
    DEFAULT: 'Atuação e resultados informados por André: governança de R$ 660 milhões em ativos físicos; aumento de 25% na eficiência operacional; '
             'eliminação de 240 horas anuais de retrabalho; liderança de equipes com até 80 profissionais. Governança de portfólio e PMO, '
             'engenharia e contratos com CAPEX de até R$ 125 milhões, análise de dados e automação.',
    'en-US': 'Experience and results reported by André: governance of BRL 660 million in physical assets; a 25% increase in operational efficiency; '
             '240 annual hours of rework eliminated; leadership of cross-functional teams of up to 80 professionals. Portfolio governance and PMO, '
             'engineering and contracts with CAPEX up to BRL 125 million, data analytics and automation.',
}
TECHNOLOGY_ALT = {
    DEFAULT: 'Tecnologias e ferramentas: Power BI, Python, Excel, Alteryx, Power Automate e Oracle Cloud; '
             'SAP, PowerPoint, Git e GitHub; conhecimentos de HTML, CSS, JavaScript e Lua; '
             'experiência anterior em MySQL para servidores de Tibia e GTA V / FiveM.',
    'en-US': 'Technology and tools: Power BI, Python, Excel, Alteryx, Power Automate and Oracle Cloud; '
             'SAP, PowerPoint, Git and GitHub; working knowledge of HTML, CSS, JavaScript and Lua; '
             'previous MySQL experience with Tibia and GTA V / FiveM servers.',
}
STATUS_ALT = {
    DEFAULT: 'Presença no GitHub: repositórios públicos, estrelas, registros de alterações, propostas de alteração, ocorrências e seguidores; '
             'composição de código dos repositórios.',
    'en-US': 'GitHub presence: public repositories, stars, commits, pull requests, issues and followers; repository code composition.',
}
ACTIVITY_ALT = {
    DEFAULT: 'Atividade e contribuições: contribuições totais desde a criação da conta, sequência atual e maior sequência, '
             'com suas datas. A cidade 3D mostra o ano inteiro, nos últimos 12 meses: cada bloco é um dia; '
             'cada prédio é um dia com atividade e sua altura é proporcional ao número de contribuições públicas reais de André Mello.',
    'en-US': 'Activity and contributions: total contributions since account creation, current streak and longest streak, '
             'with their date ranges. The 3D city shows a complete year, covering the last 12 months: each block is one day; '
             'each building is an active day with height proportional to André Mello’s actual public contributions.',
}
