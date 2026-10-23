# Perfil de André Mello

O README de `andremellotech/andremellotech` apresenta o perfil com dados públicos do próprio GitHub, temas claro/escuro, retrato ASCII animado e cobrinha gerada automaticamente.

## Identidade e organização

O topo oferece dois botões: Português (Brasil) e English (US). O português abre o perfil principal; o inglês abre `README.en-US.md` no próprio GitHub, com caminho de volta. O GitHub não permite executar JavaScript para trocar o conteúdo do README na mesma tela. Ambas as versões são geradas pelo mesmo workflow e pelos mesmos JSONs de dados, incluindo as imagens e datas; o usuário não precisa atualizar uma versão separadamente.

`scripts/profile_i18n.py` centraliza a tradução; `language_buttons.py` desenha os botões localmente. A versão inglesa mantém a escala visual, o retrato, os temas e a cobrinha oficiais. Textos novos precisam de tradução explícita, evitando uma edição inglesa parcialmente em português.

A abertura tem 1200 × 304 pixels, com nome de 40 pixels, textos neutros e retrato em uma moldura de desenho técnico adaptada ao tema. O fundo externo é transparente. Os contatos aparecem abaixo, em badges locais de 22 pixels exibidos: somente o ícone e o identificador (André Mello, @andremellotech e andremello@outlook.com), sem repetir o nome da plataforma. O botão de e-mail abre o aplicativo de mensagens com o destinatário preenchido, sem enviar automaticamente. Os títulos das seções não têm numeração.

O foco é o GitHub: dados, automação, integrações e engenharia em código. A abertura não repete cargo, formação ou resultados profissionais do LinkedIn. Os textos e datas têm versões em português e inglês dos EUA; nomes próprios de tecnologias são preservados.

A ordem é: apresentação curta; contatos; presença no GitHub; atividade e contribuições com a cobrinha; tecnologias e ferramentas. Não há cartões de projetos. O botão GitHub continua levando aos repositórios.

Os blocos de resultados de carreira, formação acadêmica e reconhecimentos foram retirados a pedido de André. O LinkedIn permanece acessível pelo botão de contato. O módulo antigo `professional_panel.py` não é executado nem incluído no perfil ou no novo staging do Pages.

Power BI, Python, Excel, Alteryx, SAP, Power Automate, Oracle Cloud, PowerPoint e GitHub refletem o uso informado. HTML, CSS, JavaScript e Lua são conhecimentos; MySQL é experiência anterior em servidores de Tibia e GTA V/FiveM. Nenhum nível de proficiência foi inventado.

`scripts/branding.py` centraliza margens de 24 pixels e a escala tipográfica: nome 40, chamada 32, títulos de seção 26, títulos de cartões 22, corpo 20, apoio 18 e indicadores 36 pixels. As artes têm 1200 pixels de largura e reduzem juntas no README. Todos os badges de tecnologias seguem o mesmo padrão neutro: altura 48, fonte 20, ícone alinhado e borda fina. As cores ficam nos símbolos; as superfícies e os textos acompanham o tema. Os símbolos são desenhados localmente, com GitHub e Alteryx derivados da arte local existente, sem consultas a serviços externos.

As referências são [Solon](https://github.com/solonz), para o cartão compacto de linguagens e o indicador com chama, e [Mateus Hoffman](https://github.com/MateusHoffman), para a cobrinha. Os dados são sempre de André.

## Estatísticas ligadas ao GitHub

`scripts/fetch_github_content.py` coleta os repositórios públicos e seus bytes por linguagem. Estrelas são somadas; commits, PRs e issues usam buscas por autor com `is:public`. PRs e issues incluem todos os estados. A busca de commits considera as branches padrão e depende da indexação do GitHub; não equivale ao total de contribuições.

Buscas opcionais indisponíveis ou incompletas mostram `—`. Valores antigos não são apresentados como uma consulta nova. Falhas na coleta principal interrompem a publicação e preservam a versão publicada.

O gráfico compacto mostra as cinco maiores linguagens e a soma das demais. Usa uma paleta categórica própria para separar os tons: HTML em terracota, TypeScript em azul, C# em violeta, Python em verde-petróleo, Power Query em ocre e Outras em cinza. A versão escura eleva a luminosidade mantendo essas famílias; barra e legenda usam o mesmo mapeamento nos dois idiomas. Separadores finos distinguem segmentos sem alterar seus percentuais. O recorte é de até seis repositórios públicos recentes, por bytes: não representa proficiência. As parcelas incluem todo o recorte, com barra segmentada e legenda colorida. A legenda reserva uma coluna para o percentual, sem reduzir a fonte de nomes longos. Nomes excepcionalmente extensos são abreviados; os nomes completos e o recorte permanecem no texto alternativo da imagem.

`scripts/fetch_streak_history.py` consulta diretamente o calendário público do GitHub desde a criação da conta, em 2021. Valida todos os dias de cada ano e calcula:

- **Contribuições totais:** soma de todo o histórico público.
- **Sequência atual:** dias consecutivos com atividade; um dia atual ainda vazio pode continuar a sequência encerrada ontem.
- **Maior sequência:** maior sequência em todo o histórico.

O ano atual é consultado a cada execução. Anos encerrados são revalidados uma vez por dia e reutilizados entre consultas do mesmo dia. Um ano incompleto impede gravar o novo histórico. As linhas técnicas de consulta continuam ocultas.

Os indicadores têm datas em português, como `7 abr 2021 — atual` e `13 out — 22 out`. O ano aparece nos anos anteriores. Um único dia não é repetido como intervalo. Sem atividade, a faixa correspondente mostra —; em empate da maior sequência, mantém-se a primeira. As datas vêm dos mesmos dias usados no cálculo dos números. A chama curva e o aro laranja seguem a referência do Solon; o aro é decorativo, sem representar porcentagem de progresso. O painel de estatísticas tem 1200 × 640 pixels; usa números de 36 pixels nas sequências, rótulos de 22 e datas de 18.

`scripts/fetch_contributions.py` mantém também o calendário público recente, validado, como fonte para a composição inicial da seção de atividade e para os dados locais.

## Cobrinha fiel à referência

O workflow usa **Platane/snk**, o mesmo gerador do perfil de Mateus, fixado no commit `d8f6715049803e982ee5ff501b6b9b7d5deeb09b`. Esse commit fixa também a imagem Docker por digest. O gerador consulta o perfil de André com o token automático de Actions.

São usadas as cores da referência: cobra `#005bcf` no tema claro e `#429aff` no escuro; contribuições `#FFC4A8, #FFA473, #FF8545, #FF5F1F`. A rota, a interpolação e a barra de células consumidas vêm do gerador original. É uma animação, sem controle pelo teclado dentro do README.

A saída é GIF, em vez do SVG exibido por Mateus. `scripts/contribution_snake.py` adapta os frames ao painel, preservando a duração, o movimento e a repetição. Não desenha uma rota substituta. A ausência do GIF original gera erro. Os arquivos fonte `assets/snake-source-*.gif` são gerados pelo Actions; a hospedagem pública usa apenas o resultado composto.

Os testes usam um GIF pequeno e controlado para testar o compositor sem rede. Essa amostra nunca é usada como alternativa no workflow de produção. A integração real de Platane/snk deve ser conferida na execução do Actions.

## Atualização automática

O workflow `.github/workflows/update-profile-art.yml` roda após push em main, por acionamento manual, pelo agendamento de cinco minutos e por `repository_dispatch` do tipo `repo-updated`.

O GitHub pode atrasar ou dispensar execuções agendadas. A indexação e o calendário do próprio GitHub também podem demorar. A página aberta precisa ser recarregada para buscar imagens novas. Não há garantia de atualização em tempo real.

O acionamento manual aguarda 90 segundos; o evento externo aguarda 45 segundos antes da coleta. Dados e imagens são publicados quando mudam. Commits do bot não disparam outra atualização por push; o horário de alteração do próprio perfil é neutralizado na coleta para evitar ciclos.

### Avisos entre repositórios: ativação pendente

André informou que o segredo `PROFILE_DISPATCH_TOKEN` ainda não existe. O recebimento está preparado e o modelo está em `templates/notify-profile.yml`; nenhum token foi criado e o notificador não foi instalado nos outros repositórios. Isso não impede o agendamento nem a geração da cobrinha com o token automático do perfil.

Para ativar depois, crie uma credencial restrita ao repositório de destino com **Contents: write**, salve como segredo `PROFILE_DISPATCH_TOKEN` nos repositórios de origem e instale o modelo em `.github/workflows/notify-profile.yml`. Não coloque a credencial em código ou chat. Consulte a [API de repository dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event). A ativação entre repositórios ainda não foi testada de ponta a ponta.

## Temas e rede corporativa

Todos os PNGs e GIFs do README ficam em `https://andremellotech.github.io/andremellotech/assets/`, com URLs absolutas e versão derivada do conteúdo para passarem pelo Camo do GitHub. Mantém-se a hospedagem que André confirmou na KPMG. O visitante não precisa acessar Vercel, Heroku, serviços de estatísticas ou o gerador da cobrinha.

O HTML picture escolhe o tema. O fundo externo é transparente; o painel do retrato e os cards têm suas próprias superfícies. A animação do retrato conserva a duração original, com texto fixo e somente a região do rosto mudando. O compositor da cobrinha escreve retângulos de diferença entre frames. A nova versão precisa ser conferida por André na rede interna da KPMG; não foi testada dentro dessa rede.

`scripts/prepare_pages.py` seleciona 29 imagens para os dois idiomas, as prévias HTML e `.nojekyll`. A prévia inglesa fica em `/en-US/`. Código, dados e GIFs fonte não são hospedados no Pages. As imagens são publicadas antes de o bot atualizar os links dos dois READMEs.

## Edição e verificação

Instale `scripts/requirements.txt`. A ordem no workflow é: testes; calendário recente; dados públicos; histórico completo; Platane/snk; design; publicação. Para gerar localmente, são necessários os dois GIFs fonte produzidos por Platane/snk, além dos JSONs de dados.

`previa.html` inclui a apresentação, contatos e os painéis sem projetos. `PREVIA.png` e `PREVIA-ESCURO.png` são composições estáticas: não mostram movimento nem os contatos nativos do README.

A apresentação fica em `scripts/intro_panel.py`; tecnologias e ferramentas em `scripts/technology_panel.py`; estatísticas em `scripts/status_panel.py`; temas em `scripts/themes.py`; composição em `scripts/github_layout.py`. As fontes são Segoe UI no Windows e DejaVu Sans no Ubuntu. O workflow usa Ubuntu 24.04 e Python 3.11; as Actions são fixadas por SHA.

Execute `python -m unittest discover -s tests -v`. Os testes cobrem dados públicos, falhas HTTP, prevenção de ciclos, histórico completo entre anos e cache, recusa de histórico incompleto, adaptação fiel dos frames da cobrinha, fontes ausentes, temas, estabilidade dos textos e inclusão dos arquivos selecionados no staging.
