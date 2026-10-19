# Instalar no perfil do GitHub

1. Abra o repositório `andremellotech/andremellotech` no GitHub.
2. Envie o conteúdo desta pasta para a raiz do repositório. Preserve a pasta `assets` e substitua o README.md anterior.
3. Confirme o commit. O README será exibido no perfil.

Abra `previa.html` para ver a composição localmente. `PREVIA.png` oferece uma visão estática; o README e a prévia HTML mostram o retrato animado.

## Atualização

O workflow consulta os dados públicos a cada 5 minutos (minutos 2, 7, 12 e assim por diante) e também após alterações na branch main deste repositório. Esse é o menor intervalo de agendamento do GitHub Actions. O agendamento pode atrasar ou perder execuções durante períodos de alta demanda; portanto, o intervalo não é uma garantia de prazo. Alterações em outros repositórios são detectadas na próxima consulta. A publicação só é reconstruída quando há mudanças nos dados ou na arte. Também pode ser executado manualmente pela aba Actions.

O painel no README usa imagens atualizadas automaticamente, sem execução de JavaScript. Apenas o retrato tem animação; os números exibidos não mudam dentro de uma página já aberta. É necessário recarregar a página para mostrar dados novos. O próprio GitHub pode levar até 24 horas para contabilizar contribuições; a coleta reproduz os dados publicados por ele e não antecipa esse processamento. Imagens exportadas ou mostradas na conversa são capturas estáticas.

Cada execução deixa um resumo na aba Actions com horário da consulta, resultado, total coletado e situação da publicação. Quando a coleta encontra os mesmos dados, as etapas de publicação aparecem como dispensadas (skipped); isso é esperado e não indica falha. Solicitações GET são repetidas até três vezes após erros temporários de conexão, limite de requisições ou respostas 5xx. Erros permanentes continuam interrompendo a execução e ficam visíveis nos logs. A leitura usa a branch main mais recente e o token continua limitado às permissões já existentes.

O ambiente de execução está fixado em Ubuntu 24.04. As Actions oficiais usam versões compatíveis com Node.js 24, fixadas pelo SHA completo da versão verificada. O upload preserva o arquivo público .nojekyll da pasta de publicação. O workflow verifica a compatibilidade das dependências com pip check antes dos testes e interrompe a atualização se houver erro.

Para atualizar manualmente: abra Actions → Atualizar perfil visual → Run workflow → main → Run workflow. A execução manual aguarda 90 segundos antes da coleta para dar tempo ao gráfico do GitHub processar alterações recentes; esse prazo não garante que todo processamento do GitHub já tenha terminado.

As métricas e o calendário usam o perfil público de andremellotech. A data, o intervalo consultado e os dias ativos continuam sendo coletados nos arquivos de dados, mas as duas linhas explicativas abaixo do calendário ficam ocultas no painel. A consulta automática a cada 5 minutos permanece ativa. Falhas na coleta interrompem a publicação e preservam o último painel válido.

Títulos, subtítulos, números de seção, métricas e botões de contato usam uma paleta neutra: grafite no tema claro e branco suave no escuro, com textos de apoio em cinza. A hierarquia vem dos tamanhos, pesos e espaçamentos. As cores ficam concentradas nos selos das ferramentas e no calendário, que conserva as paletas verdes nativas do GitHub. Os níveis de intensidade são os mesmos retornados pelo calendário público, sem reinterpretar as faixas de contagem.

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

No tema claro, os badges recebem uma base escura opaca dentro da cápsula para manter o contraste dos nomes brancos e dos ícones. As bordas coloridas e a transparência fora das cápsulas são preservadas. No tema escuro, os badges originais continuam sendo usados.

A revisão tipográfica usa Segoe UI e Segoe UI Semibold no Windows. O nome foi reduzido de 88 para 52 pixels na arte original; os títulos de apresentação usam 30 pixels, os de cards 25 e os de categorias 22. Os tamanhos exibidos no GitHub variam proporcionalmente à largura disponível. O retrato ocupa 36% da largura e o texto de apresentação 49%, para equilibrar as alturas. Os badges de tecnologias mantêm os 36 pixels de altura.

## Composição contínua no GitHub

O conteúdo principal usa três blocos adjacentes em cada tema: `profile-header-*.png`, `profile-about-*.gif` e `profile-body-*.png`. Eles conservam as dimensões e o alinhamento da composição contínua. O elemento HTML `picture` permite ao próprio GitHub selecionar as cores adequadas ao tema. Espaços vazios, cards e retrato mantêm transparência, acompanhando o fundo da página. As cores estão centralizadas em `scripts/themes.py`.

A animação reaproveita os quadros e tempos de `assets/andre-ascii.gif`. O texto é gravado uma vez no GIF e somente o retângulo do retrato muda nos quadros seguintes. Assim, as ferramentas e o restante do painel continuam em PNG sem perda de nitidez. A seleção por tema mantém o GIF solicitado mesmo quando o sistema indica movimento reduzido, sem modificar configurações do computador. As versões paradas `profile-about-*.png` e os arquivos completos `profile-card-light.png` e `profile-card-dark.png` continuam disponíveis para exportação estática.

Os dois recortes transparentes do rodapé continuam sendo links reais para LinkedIn e repositórios. `scripts/github_layout.py` gera essa composição e é chamado pelo gerador principal. A prévia HTML segue o tema do sistema. `PREVIA.png` mostra a versão clara e `PREVIA-ESCURO.png` a escura. Os arquivos individuais dos badges permanecem disponíveis para edição, mas são incorporados ao painel no perfil. O perfil termina após os botões de contato, sem seções recolhíveis ou links repetidos.

## Imagens e compatibilidade com redes corporativas

A versão principal usa PNG e GIF com transparência nos dois temas. As imagens são publicadas por HTTPS em https://andremellotech.github.io/andremellotech/assets/ e referenciadas por URLs absolutas no README, para passarem pelo proxy de imagens do GitHub, como as imagens externas da referência mixzira. Cada URL inclui uma versão calculada a partir do conteúdo, evitando que o cache mantenha um painel antigo após atualizações. A animação não depende de JavaScript, vídeos, SVG animado ou novos serviços externos.

O workflow precisa de contents:write para salvar os dados e a arte, e de pages:write e id-token:write para publicar os arquivos no GitHub Pages. Em Settings → Pages, a origem deve ser GitHub Actions. A publicação das imagens acontece antes do commit que atualiza os links do README. Apenas as imagens públicas do painel/rodapé e sua prévia são enviadas à hospedagem; os testes verificam que cada imagem referenciada está incluída.

A versão anterior com essa mesma hospedagem e o proxy do GitHub foi confirmada por André como funcionando dentro da rede KPMG. As mudanças de tema e a animação preservam esse fluxo de carregamento.
