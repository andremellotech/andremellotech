# Instalar no perfil do GitHub

1. Abra o repositório `andremellotech/andremellotech` no GitHub.
2. Envie o conteúdo desta pasta para a raiz do repositório. Preserve a pasta `assets` e substitua o README.md anterior.
3. Confirme o commit. O README será exibido no perfil.

Abra `previa.html` para ver a composição localmente. `PREVIA.png` oferece uma visão estática; o README mostra a composição estática.

## Atualização

O workflow consulta os dados públicos nos minutos 13 e 43 de cada hora e também após alterações na branch main deste repositório. O agendamento do GitHub Actions pode atrasar. Alterações em outros repositórios são detectadas na próxima consulta. A publicação só é reconstruída quando há mudanças nos dados ou na arte. Também pode ser executado manualmente pela aba Actions.

As métricas e o calendário usam o perfil público de andremellotech. A data, o intervalo consultado e os dias ativos continuam sendo coletados nos arquivos de dados, mas as duas linhas explicativas abaixo do calendário ficam ocultas no painel. A consulta automática a cada 30 minutos permanece ativa. Falhas na coleta interrompem a publicação e preservam o último painel válido.

Para reconstruir localmente: instale `scripts/requirements.txt` e execute `python scripts/design.py`. Os textos e cores ficam nesse arquivo. As fontes são Segoe UI no Windows e DejaVu Sans no Linux.

## Direção visual

Combina a identidade animada do arquivo original com a organização de apresentação e ferramentas da referência mixzira. Os textos descrevem somente as áreas e ferramentas documentadas no material fornecido. Não foram acrescentados experiência, formação ou projetos não confirmados.

O GitHub controla o layout externo e pode reduzir os painéis no celular. A prévia local aproxima o conteúdo, mas não reproduz a interface completa do GitHub. Há descrições alternativas nas imagens. O contato usa somente os dois botões de LinkedIn e repositórios, sem links repetidos abaixo.

A capa usa uma apresentação tipográfica sem gráficos decorativos. A seção "Em construção" foi retirada. Os links de LinkedIn e repositórios usam badges retangulares compactos, em duas cores, seguindo a referência enviada. Métricas públicas e calendário de contribuições ficam integrados no painel. A prévia PNG mostra o conteúdo principal.

## Tecnologias selecionadas

Os badges representam o uso informado por André: Power BI, Python, Excel, Alteryx, SAP, PowerPoint, HTML e GitHub. Office 365 é mencionado junto de Excel e PowerPoint, evitando repetir a suíte em outro badge. MySQL aparece como experiência anterior no desenvolvimento de servidores de Tibia e GTA V / FiveM. Nenhum nível de proficiência foi presumido.

HTML, GitHub e MySQL mantêm os badges de https://github.com/mixzira, originados em https://content.mixzira.dev/Github/. Os demais foram preparados no mesmo formato compacto com ícones dos conjuntos SVG Logos, vscode-icons e Simple Icons, via Iconify. Os SVGs usados estão em assets/icons e os badges prontos em assets/badges. Os badges têm 36 pixels de altura e fundo translúcido, adaptando-se ao fundo do perfil.

Fontes dos ícones: https://api.iconify.design/logos/python.svg, https://api.iconify.design/logos/microsoft-power-bi.svg, https://api.iconify.design/logos/sap.svg, https://api.iconify.design/simple-icons/alteryx.svg, https://api.iconify.design/vscode-icons/file-type-excel.svg e https://api.iconify.design/vscode-icons/file-type-powerpoint.svg.

HTML, CSS, JavaScript e Lua aparecem em Linguagens · Conhecimentos, conforme informado pelo usuário. Python permanece destacado em Dados & Automação. Os badges adicionais CSS, JavaScript e Lua mantêm os arquivos da referência mixzira, totalizando 12 badges.

A revisão tipográfica usa Segoe UI e Segoe UI Semibold no Windows. O nome foi reduzido de 88 para 52 pixels na arte original; os títulos de apresentação usam 30 pixels, os de cards 25 e os de categorias 22. Os tamanhos exibidos no GitHub variam proporcionalmente à largura disponível. O retrato ocupa 36% da largura e o texto de apresentação 49%, para equilibrar as alturas. Os badges de tecnologias mantêm os 36 pixels de altura.

## Composição contínua no GitHub

O conteúdo principal usa `assets/profile-card-light.png` e `assets/profile-card-dark.png`, ambos com fundo transparente. O elemento HTML `picture` permite ao próprio GitHub selecionar a imagem com cores de texto adequadas ao tema. A transparência acompanha também os fundos dos temas escuro suave, de alto contraste e de acessibilidade, sem fixar uma cor de fundo no painel. Cards e retrato também não têm preenchimento de fundo. As cores estão em `scripts/themes.py`.

Os dois recortes transparentes do rodapé continuam sendo links reais para LinkedIn e repositórios. `scripts/github_layout.py` gera essa composição e é chamado pelo gerador principal. A prévia HTML segue o tema do sistema. `PREVIA.png` mostra a versão clara e `PREVIA-ESCURO.png` a escura. Os arquivos individuais dos badges permanecem disponíveis para edição, mas são incorporados ao painel no perfil. O perfil termina após os botões de contato, sem seções recolhíveis ou links repetidos.

## Imagens e compatibilidade com redes corporativas

A versão principal usa PNG estático com transparência nos dois temas. As imagens são publicadas por HTTPS em https://andremellotech.github.io/andremellotech/assets/ e referenciadas por URLs absolutas no README, para passarem pelo proxy de imagens do GitHub, como as imagens externas da referência mixzira. Cada URL inclui uma versão calculada a partir do conteúdo, evitando que o cache mantenha um painel antigo após atualizações.

O workflow precisa de contents:write para salvar os dados e a arte, e de pages:write e id-token:write para publicar os arquivos no GitHub Pages. Em Settings → Pages, a origem deve ser GitHub Actions. A publicação das imagens acontece antes do commit que atualiza os links do README. Apenas os quatro arquivos públicos do painel/rodapé e sua prévia são enviados à hospedagem.

A versão anterior com essa mesma hospedagem e o proxy do GitHub foi confirmada por André como funcionando dentro da rede KPMG. A mudança de tema preserva esse fluxo de carregamento.
