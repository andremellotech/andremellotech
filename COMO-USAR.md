# Perfil de André Mello

O README de `andremellotech/andremellotech` apresenta o perfil com dados públicos do próprio GitHub, temas claro/escuro, retrato ASCII animado, cidade 3D anual gerada automaticamente.

## Identidade e organização

O topo oferece dois botões: Português (Brasil) e English (US). O português abre o perfil principal; o inglês abre `README.en-US.md` no próprio GitHub, com caminho de volta. O GitHub não permite executar JavaScript para trocar o conteúdo do README na mesma tela. Ambas as versões são geradas pelo mesmo workflow e pelos mesmos JSONs de dados, incluindo as imagens e datas; o usuário não precisa atualizar uma versão separadamente.

`scripts/profile_i18n.py` centraliza a tradução; `language_buttons.py` desenha os botões localmente. A versão inglesa mantém a escala visual, o retrato, os temas e a cidade anual. Textos novos precisam de tradução explícita, evitando uma edição inglesa parcialmente em português.

A abertura tem 1200 × 304 pixels, com nome de 40 pixels, textos neutros e retrato em uma moldura de desenho técnico adaptada ao tema. O fundo externo é transparente. Os contatos aparecem abaixo, em badges locais de 22 pixels exibidos: somente o ícone e o identificador (André Mello, @andremellotech e andremello@outlook.com), sem repetir o nome da plataforma. O botão de e-mail abre o aplicativo de mensagens com o destinatário preenchido, sem enviar automaticamente. Os títulos das seções não têm numeração.

O foco é o GitHub: dados, automação, integrações e engenharia em código. A abertura não repete cargo, formação ou resultados profissionais do LinkedIn. Os textos e datas têm versões em português e inglês dos EUA; nomes próprios de tecnologias são preservados.

A ordem é: apresentação curta; contatos; presença no GitHub; atividade e contribuições; tecnologias e ferramentas. A seção Atividade e contribuições reúne, em um único cartão, contribuições totais, sequência atual, maior sequência, cidade 3D dos últimos 12 meses. Os recortes ficam identificados em cada visualização. Não há cartões de projetos. O botão GitHub continua levando aos repositórios.

Os blocos de resultados de carreira, formação acadêmica e reconhecimentos foram retirados a pedido de André. O LinkedIn permanece acessível pelo botão de contato. O módulo antigo `professional_panel.py` não é executado nem incluído no perfil ou no novo staging do Pages.

Power BI, Python, Excel, Alteryx, SAP, Power Automate, Oracle Cloud, PowerPoint, Git e GitHub refletem o uso informado. Git e GitHub aparecem lado a lado no cartão Sistemas e colaboração, com o mesmo padrão dos demais badges. HTML, CSS, JavaScript e Lua são conhecimentos; MySQL é experiência anterior em servidores de Tibia e GTA V/FiveM. Nenhum nível de proficiência foi inventado.

`scripts/branding.py` centraliza margens de 24 pixels e a escala tipográfica: nome 40, chamada 32, títulos de seção 26, títulos de cartões 22, corpo 20, apoio 18 e indicadores 36 pixels. As artes têm 1200 pixels de largura e reduzem juntas no README. Todos os badges de tecnologias seguem o mesmo padrão neutro: altura 48, fonte 20, ícone alinhado e borda fina. As cores ficam nos símbolos; as superfícies e os textos acompanham o tema. Os símbolos são desenhados localmente, com GitHub e Alteryx derivados da arte local existente, sem consultas a serviços externos.

As referências são [Solon](https://github.com/solonz), para o cartão compacto de linguagens e o indicador com chama; [GitSkins](https://www.gitskins.com/readme-generator), para a ideia de cidade de contribuições enviada por André. A cidade tem implementação própria em Pillow. Os dados são sempre de André.

## Estatísticas ligadas ao GitHub

`scripts/fetch_github_content.py` coleta os repositórios públicos e seus bytes por linguagem. Estrelas são somadas; commits, PRs e issues usam buscas por autor com `is:public`. PRs e issues incluem todos os estados. A busca de commits considera as branches padrão e depende da indexação do GitHub; não equivale ao total de contribuições.

Buscas opcionais indisponíveis ou incompletas mostram `—`. Valores antigos não são apresentados como uma consulta nova. Falhas na coleta principal interrompem a publicação e preservam a versão publicada.

O gráfico compacto mostra as cinco maiores linguagens e a soma das demais. As cores vêm diretamente do [GitHub Linguist](https://github.com/github-linguist/linguist/blob/main/lib/linguist/languages.yml), com uma cópia local das 694 cores oficiais em `data/language-colors.json`, consultada em 23/10/2026. São usados os mesmos valores hexadecimais na barra e na legenda, nos temas claro e escuro e nos dois idiomas. Não há ajuste de saturação ou luminosidade das cores oficiais. O grupo Outras e linguagens sem cor definida no Linguist usam o cinza neutro do tema. Os marcadores da legenda têm 12 pixels e bordas suavizadas. Separadores finos distinguem segmentos sem alterar seus percentuais. O recorte é de até seis repositórios públicos recentes, por bytes: não representa proficiência. As parcelas incluem todo o recorte, com barra segmentada e legenda colorida. A legenda reserva uma coluna para o percentual, sem reduzir a fonte de nomes longos. Nomes excepcionalmente extensos são abreviados; os nomes completos e o recorte permanecem no texto alternativo da imagem.

`scripts/fetch_streak_history.py` consulta diretamente o calendário público do GitHub desde a criação da conta, em 2021. Valida todos os dias de cada ano e calcula:

- **Contribuições totais:** soma de todo o histórico público.
- **Sequência atual:** dias consecutivos com atividade; um dia atual ainda vazio pode continuar a sequência encerrada ontem.
- **Maior sequência:** maior sequência em todo o histórico.

O ano atual é consultado a cada execução. Anos encerrados são revalidados uma vez por dia e reutilizados entre consultas do mesmo dia. Um ano incompleto impede gravar o novo histórico. As linhas técnicas de consulta continuam ocultas.

Os indicadores têm datas em português, como `7 abr 2021 — atual` e `13 out — 22 out`. O ano aparece nos anos anteriores. Um único dia não é repetido como intervalo. Sem atividade, a faixa correspondente mostra —; em empate da maior sequência, mantém-se a primeira. As datas vêm dos mesmos dias usados no cálculo dos números. A chama curva e o aro laranja seguem a referência do Solon; o aro é decorativo, sem representar porcentagem de progresso. O painel de presença no GitHub tem 1200 × 344 pixels, com repositórios e linguagens. Os três indicadores de contribuição aparecem apenas no cartão de atividade, de 1200 × 918 pixels, junto da cidade anual. Os números continuam com 36 pixels, rótulos com 22 e datas com 18.

## Cidade anual de contribuições

`scripts/contribution_city.py` desenha o ano inteiro a partir de `data/contributions.json`: do dia seguinte à mesma data no ano anterior até `as_of`, inclusive. O intervalo tem 365 ou 366 dias, preservando 29 de fevereiro. Datas ausentes ou duplicadas, contagens negativas e valores fracionários interrompem a geração, sem inventar dias nem publicar um recorte parcial.

Cada dia tem um lote em sua semana e dia da semana; apenas dias com contribuições têm prédio. A altura é linearmente proporcional à contagem, normalizada pelo maior dia do ano. A perspectiva e a composição com resumo à esquerda continuam inspiradas no [Contribution City do GitSkins](https://www.gitskins.com/readme-builder?username=andremellotech&template=contribution-city). O degradê e a moldura interna colorida foram retirados: a cena tem fundo transparente e se integra à superfície neutra do cartão, branca no tema claro e #0d1117 no escuro. As faces dos prédios mantêm azul e verde-petróleo com contraste próprio.

A cidade agora é animada em GIF, com 32 quadros de 140 ms e repetição contínua (4,48 segundos por ciclo). A câmera oscila suavemente em torno da mesma perspectiva isométrica. As contagens e alturas permanecem fixas; nenhum prédio nasce, some ou muda sua contribuição para produzir o movimento. O enquadramento usa limites comuns para todos os quadros, preservando o ano inteiro e evitando zoom variável. Título, métricas, resumo e datas ficam estáticos. Os retângulos de diferença entre quadros e a paleta compartilhada reduzem o arquivo e evitam redesenhar os textos.

A cena anual ocupa a largura do cartão, com resumo, identificador e intervalo visíveis. O texto alternativo explica a relação entre dias, prédios e alturas. Dias sem atividade continuam representados por lotes vazios. Não há cobrinha no perfil nem etapa Platane/snk no Actions; os módulos e testes específicos da cobrinha foram removidos. Arquivos antigos no histórico Git não são referenciados pelo README nem selecionados para o novo Pages.

O painel publicado é `activity[-en-US]-{light,dark}.gif`, com os três indicadores e a cidade dentro da mesma borda. O PNG do primeiro quadro continua sendo gerado para a composição estática das prévias. O GIF evita depender de SVG, JavaScript ou serviço externo para o movimento. A implementação é própria em Pillow, inspirada na referência visual GitSkins enviada por André e conferida no navegador com seu usuário; usa somente as contribuições públicas do próprio André. Nenhum export do GitSkins foi consumido, nem foi adicionada consulta à API do GitSkins na geração ou abertura do perfil. O mesmo modelo produz PT/US e claro/escuro.

## Atualização automática

O workflow `.github/workflows/update-profile-art.yml` roda após push em main, por acionamento manual, pelo agendamento de cinco minutos e por `repository_dispatch` do tipo `repo-updated`.

O GitHub pode atrasar ou dispensar execuções agendadas. A indexação e o calendário do próprio GitHub também podem demorar. A página aberta precisa ser recarregada para buscar imagens novas. Não há garantia de atualização em tempo real.

O acionamento manual aguarda 90 segundos; o evento externo aguarda 45 segundos antes da coleta. Dados e imagens são publicados quando mudam. Commits do bot não disparam outra atualização por push; o horário de alteração do próprio perfil é neutralizado na coleta para evitar ciclos.

### Avisos entre repositórios: ativação pendente

André informou que o segredo `PROFILE_DISPATCH_TOKEN` ainda não existe. O recebimento está preparado e o modelo está em `templates/notify-profile.yml`; nenhum token foi criado e o notificador não foi instalado nos outros repositórios. Isso não impede o agendamento nem a atualização da cidade anual.

Para ativar depois, crie uma credencial restrita ao repositório de destino com **Contents: write**, salve como segredo `PROFILE_DISPATCH_TOKEN` nos repositórios de origem e instale o modelo em `.github/workflows/notify-profile.yml`. Não coloque a credencial em código ou chat. Consulte a [API de repository dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event). A ativação entre repositórios ainda não foi testada de ponta a ponta.

## Temas e rede corporativa

Todos os PNGs e GIFs do README ficam em `https://andremellotech.github.io/andremellotech/assets/`, com URLs absolutas e versão derivada do conteúdo para passarem pelo Camo do GitHub. Mantém-se a hospedagem que André confirmou na KPMG. O visitante não precisa acessar Vercel, Heroku, serviços de estatísticas ou o GitSkins.

O HTML picture escolhe o tema. O fundo externo é transparente; o painel do retrato e os cards têm suas próprias superfícies. A animação do retrato conserva a duração original, com texto fixo e somente a região do rosto mudando. Na cidade, apenas a geometria isométrica se move; os textos e números ficam estáticos e o fundo segue o restante do perfil. A nova versão precisa ser conferida por André na rede interna da KPMG; não foi testada dentro dessa rede.

`scripts/prepare_pages.py` seleciona 29 imagens para os dois idiomas, as prévias HTML e `.nojekyll`. A prévia inglesa fica em `/en-US/`. Código e dados não são hospedados no Pages. As imagens são publicadas antes de o bot atualizar os links dos dois READMEs.

## Edição e verificação

Instale `scripts/requirements.txt`. A ordem no workflow é: testes; calendário recente; dados públicos; histórico completo; design; publicação. A geração local usa os JSONs de dados, os ícones e o retrato existentes.

`previa.html` inclui a apresentação, contatos e os painéis sem projetos. `PREVIA.png` e `PREVIA-ESCURO.png` são composições estáticas: não mostram movimento nem os contatos nativos do README.

A apresentação fica em `scripts/intro_panel.py`; tecnologias e ferramentas em `scripts/technology_panel.py`; estatísticas em `scripts/status_panel.py`; temas em `scripts/themes.py`; composição em `scripts/github_layout.py`. As fontes são Segoe UI no Windows e DejaVu Sans no Ubuntu. O workflow usa Ubuntu 24.04 e Python 3.11; as Actions são fixadas por SHA.

Execute `python -m unittest discover -s tests -v`. Os testes cobrem dados públicos, falhas HTTP, prevenção de ciclos, histórico completo entre anos e cache, recusa de histórico incompleto, recorte anual da cidade, ano bissexto, alturas proporcionais e dias sem atividade, fontes ausentes, temas, movimento real da cidade, fundo neutro, estabilidade dos textos e inclusão dos arquivos selecionados no staging.
