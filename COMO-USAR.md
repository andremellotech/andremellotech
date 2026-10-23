# Perfil de André Mello

O perfil está no repositório `andremellotech/andremellotech`. O GitHub exibe o `README.md` desse repositório na página do usuário. O gerador mantém versões clara e escura, retrato ASCII animado e dados públicos atualizados pelo GitHub Actions.

## Composição

O banner usa azul-marinho, um detalhe dourado e o monograma AM. O nome tem 46 pixels na arte de 1200 pixels de largura; o tamanho exibido é proporcional à largura do README. As linhas do banner são decorativas e não representam indicadores. A apresentação foi compactada para 372 pixels de altura, mantendo o retrato animado. Os dois contatos aparecem logo abaixo do banner em badges locais com resolução dupla e 28 pixels de altura exibida.

A ordem é: banner; contatos; apresentação; estatísticas públicas e composição do código; contribuições e sequências; calendário; ferramentas; projetos em texto. As métricas usam tons neutros e azul; o calendário mantém as cores verdes nativas do GitHub. As ferramentas conservam os badges coloridos já aprovados por André.

Power BI, Python, Excel, Alteryx, SAP, PowerPoint e GitHub representam o uso informado pelo usuário. HTML, CSS, JavaScript e Lua aparecem como conhecimentos. Office 365 é mencionado junto de Excel e PowerPoint. MySQL é identificado como experiência anterior em servidores de Tibia e GTA V / FiveM. Nenhum nível de proficiência, emprego, certificação ou resultado de cliente foi acrescentado.

Os três projetos descritos mais recentemente atualizados são selecionados automaticamente a partir da lista pública. Forks, o próprio perfil, itens privados, endereços de outro proprietário e projetos sem descrição são excluídos. Os nomes conhecidos recebem títulos curtos; as descrições vêm dos repositórios. A lista usa Markdown nativo, com links e texto selecionável, sem capturas de tela. O campo de linguagem principal do repositório não é apresentado como se fosse a stack completa de cada solução.

## Dados e significado dos indicadores

`scripts/fetch_contributions.py` coleta o calendário público do GitHub. O total no período, a sequência atual e a maior sequência são calculados sobre esses dias. As datas e os dias ativos continuam nos arquivos de dados; as linhas técnicas de consulta ficam fora do painel.

`scripts/fetch_github_content.py` coleta o perfil público, repositórios e composição do código. As estrelas são somadas nos repositórios públicos. Commits, pull requests e issues usam buscas por autor limitadas a `is:public`. Pull requests e issues incluem todos os estados: o rótulo é **Issues criadas**, não "abertas". A busca de commits considera as branches padrão, conforme a [documentação do GitHub](https://docs.github.com/en/search-github/searching-on-github/searching-commits). Esses totais indexados não são a mesma métrica que as contribuições do último ano.

Se uma busca opcional falhar ou retornar resultado incompleto ou inválido, o indicador correspondente mostra `—`. Um valor antigo não é reapresentado como uma consulta atual. As demais partes do painel continuam disponíveis. Falhas na coleta principal interrompem a publicação e preservam o último painel publicado.

A composição do código usa bytes em até seis repositórios públicos recentes. As quatro maiores linguagens e a soma das demais são exibidas, para que as parcelas representem o total do recorte. O gráfico descreve os arquivos dos repositórios; não mede proficiência nem tempo de trabalho. A legenda informa o recorte em bytes.

## Atualização automática

O workflow `.github/workflows/update-profile-art.yml` roda após push na branch `main`, por acionamento manual e pelo agendamento `2-57/5 * * * *`. Também está preparado para receber `repository_dispatch` do tipo `repo-updated`.

O agendamento consulta a cada cinco minutos, mas o GitHub pode atrasar ou dispensar execuções em períodos de demanda elevada. Alterações em outros repositórios são detectadas na próxima coleta. Não é uma garantia de atualização em tempo real. É necessário recarregar uma página já aberta para mostrar a nova versão. A contabilização do próprio GitHub e os índices de busca podem ter atraso.

O acionamento manual aguarda 90 segundos antes da coleta. O evento externo aguarda 45 segundos para dar tempo ao GitHub registrar o push. Esses prazos não garantem a conclusão da indexação. A publicação só é reconstruída quando os dados ou a arte mudam; uma execução sem alteração pode dispensar a publicação. Cada execução registra seu resultado na aba Actions.

Os commits do gerador são atribuídos ao bot e não iniciam outra atualização por push. O horário de alteração do próprio repositório de perfil é neutralizado na coleta, evitando ciclos provocados apenas pelas imagens geradas. Erros HTTP temporários têm novas tentativas limitadas; erros permanentes continuam visíveis nos logs.

## Avisos entre repositórios — preparação concluída, ativação pendente

André informou que o segredo `PROFILE_DISPATCH_TOKEN` ainda não está configurado. O modelo está em `templates/notify-profile.yml`; ele não foi instalado nos outros repositórios e nenhum token foi criado ou salvo por esta atualização. O recebimento do evento está declarado no perfil. O agendamento de cinco minutos continua ativo independentemente desse recurso.

Para ativar depois:

1. Configure uma credencial apropriada para o repositório de destino `andremellotech/andremellotech`. Um token fine-grained precisa da permissão **Contents: write** nesse repositório, conforme a [API de repository dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event). Restrinja o destino ao repositório do perfil.
2. Salve a credencial como segredo de Actions chamado `PROFILE_DISPATCH_TOKEN` em cada repositório de origem que enviará o aviso. Não coloque o valor no código, em arquivos do projeto ou em mensagens de chat.
3. Copie o modelo para `.github/workflows/notify-profile.yml` nesses repositórios e ajuste a branch se necessário.
4. Confira na aba Actions do perfil uma execução com o evento `repository_dispatch` após o próximo push de origem.

O modelo usa `permissions: {}` para o token automático do repositório de origem. A credencial do segredo é usada somente para enviar o evento ao perfil. Ausência do segredo gera um aviso e encerra o notificador; o agendamento permanece como alternativa. O modelo evita notificar o perfil a partir dele mesmo e limita tempo e tentativas da chamada HTTP. A ativação entre repositórios não foi validada de ponta a ponta porque a credencial de origem ainda não existe.

## Imagens, temas e rede corporativa

Os arquivos do README são PNG e GIF publicados em `https://andremellotech.github.io/andremellotech/assets/`, com URLs absolutas para passarem pelo proxy Camo do GitHub. A versão em cada URL é calculada a partir do conteúdo. O fluxo de hospedagem é o mesmo que André confirmou como funcionando na rede KPMG. A revisão não introduz um novo serviço de imagens, JavaScript, vídeo ou SVG animado no perfil.

O HTML `picture` seleciona a versão clara ou escura. O fundo externo permanece transparente; os cards usam superfícies apropriadas ao tema. Somente o banner mantém o azul-marinho nos dois temas. A animação reaproveita o arquivo original e preserva sua duração. Quadros consecutivos iguais são combinados; o texto é gravado uma vez e somente o retrato muda nos seguintes. Os testes verificam repetição, movimento, estabilidade do texto, transparência e tamanho abaixo de 1 MB.

`scripts/prepare_pages.py` publica somente as 14 imagens necessárias ao painel e às exportações estáticas, a prévia HTML e `.nojekyll`. As imagens são publicadas antes de o bot atualizar os links do README. Código, dados de trabalho e o modelo de notificação não são colocados na hospedagem Pages. O workflow usa as permissões existentes `contents: write`, `pages: write` e `id-token: write`.

## Edição e verificação local

Instale `scripts/requirements.txt` e execute:

```sh
python scripts/fetch_contributions.py
python scripts/fetch_github_content.py
python scripts/design.py
python -m unittest discover -s tests -v
python scripts/prepare_pages.py
```

`previa.html` contém contatos e projetos em texto, além das imagens. `PREVIA.png` e `PREVIA-ESCURO.png` mostram somente a composição gráfica estática; não incluem os elementos nativos do README nem reproduzem a interface completa do GitHub.

Os textos e a seleção de ferramentas ficam em `scripts/design.py`; as cores, em `scripts/themes.py`; o banner e a moldura, em `scripts/branding.py`; as estatísticas, em `scripts/status_panel.py`; a lista de projetos, em `scripts/projects_section.py`; a composição, em `scripts/github_layout.py`. As fontes são Segoe UI no Windows e DejaVu Sans no Ubuntu. O workflow permanece em Ubuntu 24.04 e Python 3.11, com as Actions oficiais fixadas pelos SHAs já utilizados.

Os testes cobrem atualização por dados reais, prevenção de ciclos do bot, falhas HTTP, filtragem e escape de projetos, escopo público das estatísticas, respostas incompletas e a renderização dos temas com todos os arquivos referenciados incluídos no staging.
