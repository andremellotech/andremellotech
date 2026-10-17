# Instalar no perfil do GitHub

1. Abra o repositório `andremellotech/andremellotech` no GitHub.
2. Envie o conteúdo desta pasta para a raiz do repositório. Preserve a pasta `assets` e substitua o README.md anterior.
3. Confirme o commit. O README será exibido no perfil.

Abra `previa.html` para ver a composição localmente. `PREVIA.png` oferece uma visão estática; no README o retrato usa o GIF original.

## Atualização

O workflow incluído consulta os dados públicos diariamente e reconstrói as imagens. Ative GitHub Actions no repositório. O workflow precisa de permissão de escrita em Contents para salvar os dados e a arte. Também pode ser executado manualmente pela aba Actions.

Os dados iniciais são do ZIP original, de 13/10/2026. A data aparece no painel. O primeiro workflow bem-sucedido atualiza os números.

Para reconstruir localmente: instale `scripts/requirements.txt` e execute `python scripts/design.py`. Os textos e cores ficam nesse arquivo. As fontes são Segoe UI no Windows e DejaVu Sans no Linux.

## Direção visual

Combina a identidade animada do arquivo original com a organização de apresentação e ferramentas da referência mixzira. Os textos descrevem somente as áreas e ferramentas documentadas no material fornecido. Não foram acrescentados experiência, formação ou projetos não confirmados.

O GitHub controla o layout externo e pode reduzir os painéis no celular. A prévia local aproxima o conteúdo, mas não reproduz a interface completa do GitHub. Há descrições alternativas nas imagens e uma apresentação em texto recolhível.

A capa usa uma apresentação tipográfica sem gráficos decorativos. A seção "Em construção" foi retirada. Os links de LinkedIn e repositórios usam badges retangulares compactos, em duas cores, seguindo a referência enviada. As métricas públicas ficam em uma seção recolhível ao final do README, com a data do snapshot indicada. A prévia PNG mostra o conteúdo principal, com as seções recolhíveis fechadas; abra previa.html para expandi-las.

## Tecnologias selecionadas

Os badges representam o uso informado por André: Power BI, Python, Excel, Alteryx, SAP, PowerPoint, HTML e GitHub. Office 365 é mencionado junto de Excel e PowerPoint, evitando repetir a suíte em outro badge. MySQL aparece como experiência anterior no desenvolvimento de servidores de Tibia e GTA V / FiveM. Nenhum nível de proficiência foi presumido.

HTML, GitHub e MySQL mantêm os badges de https://github.com/mixzira, originados em https://content.mixzira.dev/Github/. Os demais foram preparados no mesmo formato compacto com ícones dos conjuntos SVG Logos, vscode-icons e Simple Icons, via Iconify. Os SVGs usados estão em assets/icons e os badges prontos em assets/badges. Os badges têm 36 pixels de altura e fundo translúcido, adaptando-se ao fundo do perfil.

Fontes dos ícones: https://api.iconify.design/logos/python.svg, https://api.iconify.design/logos/microsoft-power-bi.svg, https://api.iconify.design/logos/sap.svg, https://api.iconify.design/simple-icons/alteryx.svg, https://api.iconify.design/vscode-icons/file-type-excel.svg e https://api.iconify.design/vscode-icons/file-type-powerpoint.svg.

HTML, CSS, JavaScript e Lua aparecem em Linguagens · Conhecimentos, conforme informado pelo usuário. Python permanece destacado em Dados & Automação. Os badges adicionais CSS, JavaScript e Lua mantêm os arquivos da referência mixzira, totalizando 12 badges.

A revisão tipográfica usa Segoe UI e Segoe UI Semibold no Windows. O nome foi reduzido de 88 para 52 pixels na arte original; os títulos de apresentação usam 30 pixels, os de cards 25 e os de categorias 22. Os tamanhos exibidos no GitHub variam proporcionalmente à largura disponível. O retrato ocupa 36% da largura e o texto de apresentação 49%, para equilibrar as alturas. Os badges de tecnologias mantêm os 36 pixels de altura.
