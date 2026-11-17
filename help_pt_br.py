# =============================================================================
# help_pt_br.py — the Help in Portuguese (Brazil)                                   ### NEW v0.20.0 UI1e ###
# Generated from the English Help (help_text.py): the same 13 topics in the same order, the same markup line by
# line (help_text.py explains the markup).  The self-test checks the parity, the markup and that every app label
# the Help must name appears exactly as the app shows it in Portuguese (Brazil).
# Brand, format and file names, [[keys]] and XML tags stay as in English.
# =============================================================================
TAB_01 = """
# Primeiros passos

## O que o app faz
O Metadata & MediaClinic audita e repara bibliotecas de filmes do Kodi, Jellyfin, Emby e Plex. Ele verifica as pastas das suas bibliotecas, confere cada arquivo de imagem, de metadados e de vídeo, e mostra uma tabela de saúde colorida, para você ver num relance o que falta ou está quebrado. A maioria dos problemas pode ser corrigida na mesma tabela.

## Como é uma pasta de filme
Uma pasta = um filme. Uma pasta completa contém:
- o vídeo, p. ex. **Movie Name (2001).mkv** (ou .mp4, .avi …)
- os metadados do Kodi, **<video>.nfo** ou **movie.nfo**
- **movie.xml**, um formato antigo (opcional): só o plugin XML do Emby o lê, e o Media Center Master o grava; Kodi, Jellyfin e Plex não o leem
- **poster.jpg** (retrato, 2:3) e **fanart.jpg** (largo, 16:9)
- **folder.jpg**, uma cópia idêntica do pôster (opcional: Plex, Jellyfin, Emby e Infuse leem poster.jpg, e o Kodi o nome próprio do pôster)
- fundos extras: **backdrop.jpg**, **backdrop1.jpg** … ou os **<video>-fanart1.jpg** … do Kodi
- legendas externas como **Movie Name.pt.srt** (opcional)
A aba Servidores de mídia lista todos os nomes que os servidores leem.

## Primeiro uso
1. Clique em **Procurar…** e escolha a pasta dos seus filmes. Adicione mais pastas depois com **Bibliotecas…**.
2. Clique em **Full Scan** ([[F5]]). A tabela é preenchida em fases: pastas, imagens, metadados e depois vídeo — com o FFprobe quando a chave **FFprobe** da barra de status está ligada.
3. Cada linha mostra a saúde de um filme: verde = nenhuma regra acionada, amarelo = avisos, vermelho = erros.
4. Selecione um filme: o painel à direita mostra o pôster, os problemas, cada um com um botão **Corrigir**, os arquivos e as ações comuns.
5. O último scan é salvo e restaurado na próxima vez que o app abrir.
6. Na primeira vez que abre, uma janela pergunta o idioma, a pasta dos seus filmes, **Quais programas reproduzem seus filmes?** (marque todos os que você usa; nada marcado também funciona), o rigor (Rigoroso, Médio, Fácil) e o FFprobe (opcional: nada vem incluído nem é baixado por você; **Escolher pasta…** ou **Página de download**). Só **Começar** salva as respostas; fechar a janela faz ela voltar no próximo início. Escolha o idioma primeiro: **Reiniciar agora** mostra a janela de novo nesse idioma. Quem atualiza de uma versão anterior vê só a pergunta dos programas, uma vez, com **Agora não**. Os programas marcados definem o **modo de saúde**: ele decide quais arquivos o MediaClinic verifica e repara.
- **Kodi, Plex, Jellyfin, Emby, Infuse** (só NFO; o próprio Plex não lê NFO, só a arte — veja abaixo): os arquivos .nfo, como o tinyMediaManager, o Radarr ou o MediaElch os criam. O movie.xml é ignorado (não é lido, verificado nem gravado; sem coluna .xml).
- **Um deles + MediaBrowser / Media Center Master** (NFO e movie.xml): o NFO e o movie.xml, todas as verificações e correções dos dois.
- **Só MediaBrowser / Media Center Master** (só movie.xml): só o movie.xml. O NFO é ignorado (não é lido nem verificado, nunca é gravado; sem coluna .nfo). Título, ano, nota, IDs e gêneros vêm do movie.xml, e as correções gravam o movie.xml. Coleções, Renomear NFO para o Kodi e a correção do **&** trabalham no NFO, por isso não são oferecidas.
Mude isso depois em **Configurações → Regras de saúde → Quais programas reproduzem seus filmes?**: marque todos os programas que você usa (Kodi, Plex, Jellyfin, Emby, Infuse, MediaBrowser / Media Center Master). As marcas definem o modo de saúde, e a linha abaixo delas mostra os arquivos verificados e os nomes que uma correção grava: um nome que todo programa marcado lê: <vídeo>.nfo, <vídeo>-poster.jpg e <vídeo>-fanart.jpg, os nomes que o Kodi recomenda, que funcionam com qualquer configuração do Kodi e são lidos por todos os outros programas (movie.nfo e poster.jpg só funcionam no Kodi com a opção da fonte "Movies are in separate folders that match the movie title"). Uma pasta cujos nomes todo programa marcado lê mantém esses nomes. Nada marcado mantém o modo como estava e os nomes de cada pasta. A leitura não muda: todo nome que esses programas aceitam continua sendo lido. Uma biblioteca reproduzida por outros programas tem a sua própria escolha em **Bibliotecas… → Programas…** (ela substitui a marca **Só NFO** dessa biblioteca). Mudar entre NFO e movie.xml oferece um novo scan.
7. No modo **NFO e movie.xml**, uma biblioteca em que nenhum filme tem movie.xml recebe mais uma pergunta depois do scan: **Biblioteca só com NFO?** **Sim, só NFO** desliga as verificações de XML só para essa biblioteca (sem o erro "Arquivo XML faltando", sem comparação NFO / XML; a coluna XML mostra —). Mude isso depois em **Bibliotecas…** com o botão **Só NFO**.

## Lista para começar rápido
- **Configurações → Editor e FFmpeg**: defina a pasta do FFmpeg (análise de vídeo e extração de imagens de fundo).
- **Configurações → Chaves de API**: adicione as chaves do TMDB e do OMDb (notas, busca e verificação de IDs, imagens); uma chave do fanart.tv traz mais pôsteres e imagens de fundo.
- **Configurações → Idioma**: o idioma de destino da coluna Idioma (padrão PT). O idioma do próprio app fica em **Configurações → Interface → Idioma da interface** (English, Português (Brasil), Español ou Igual ao Windows; **Reiniciar agora** reinicia nele).
- **Configurações → Regras de saúde**: escolha o que conta como erro ou aviso. Um **Perfil de saúde** (Fácil / Médio / Rigoroso) define todas de uma vez; um usuário novo começa com Rigoroso.
- Para fazer a triagem: ordene por **Saúde** (Erros primeiro), clique no contador **Erros** ou marque **Só problemas**.

## Ícones de status
| ⬤ | OK — presente e válido
| ◐ | aviso — conflito, proporções erradas, um problema menor
| ○ | faltando
| ✕ | erro — imagem corrompida, erro de XML, valor ilegível
| — | não usado — movie.xml numa biblioteca só com NFO, ou o arquivo que o modo de saúde não usa

## Arquivos que o app grava
| settings.json | todas as configurações (%APPDATA%\\MediaMetadataClinic)
| last_results.json | o último scan, restaurado ao abrir (mesma pasta)
| ffprobe_cache.json | resultados do FFprobe guardados (mesma pasta)
| fanarttv_cache.json | respostas do fanart.tv, guardadas por 7 dias (sem a chave)
| collections_cache.json | as coleções do TMDB (nomes em todos os idiomas)
| last_ignored.json | as pastas que o último scan não adicionou como filmes (o relatório de pastas ignoradas)
| not_duplicates.json | suas respostas "Não é duplicado"
| no_collection.json | os filmes que você marcou como "fora de qualquer coleção"
| backup_cleanup_log.json | os backups que a limpeza por tamanho removeu (o Histórico de backups os lista)
| logs/app.log | o log ao lado do programa; as chaves de API nunca são gravadas nele (**Ajuda → Abrir a pasta de logs**)
| backup/ | os backups automáticos (mesma pasta; movidos da pasta do programa uma vez — uma atualização os mantém)
"""

TAB_02 = """
# A janela e a tabela

## A janela
- **O cabeçalho** (em cima): as partes **Filmes** e **Séries**, **Histórico de backups / Desfazer…**, **Configurações ▾**, **Ajuda ▾** e **Sobre**. O suporte a séries chega na v0.22; a parte Séries mostra o que está planejado e as pastas que o último scan não adicionou.
- **A barra de ferramentas Filmes**: **Bibliotecas…**, **Procurar…**, a caixa de biblioteca, **Full Scan**, **Quick Scan**, **Ferramentas ▾**, **Exportar…** e **•••** (**Limpar tudo…**, **Salvar resultados do scan…**, **Abrir resultados do scan…**).
- **A linha de ordenação**, a caixa **Filtro** e a legenda de cores, depois a tabela.
- **O painel do filme selecionado** à direita da tabela (próxima seção).
- **A barra de status** (embaixo): os contadores (clique em **Erros** ou **Avisos** para mostrar só essas linhas), a quantidade selecionada, a última ação e a chave **FFmpeg ✓ | FFprobe**.

## O painel do filme selecionado
Selecione um filme e o painel mostra o pôster, o ano, os gêneros, a nota, a biblioteca e um selo de saúde; depois **PROBLEMAS** (cada motivo de saúde), **CORREÇÕES** (cada problema corrigível com o seu botão **Corrigir**), **ARQUIVOS** (NFO, XML, pôster, pasta, fanart, vídeo: ✓ ou ✕) e **AÇÕES** (**Abrir pasta**, **Editar NFO**, **Buscar pôster/pasta…**, **Procurar fontes**, **Atualizar**). **Todas as ações ▾** abre o menu completo do botão direito.
- Vários filmes selecionados: "N filmes selecionados", as ações que funcionam em vários e as correções com quantos filmes têm cada problema.
- Uma linha de coleção (vista agrupada) mostra o painel da coleção (aba Coleções).
- **Ocultar ›** ou [[Ctrl+B]] oculta o painel; a faixa estreita **‹** na borda direita o mostra de novo. Arraste o divisor para mudar a largura; um clique duplo no divisor a restaura. As duas coisas são lembradas.

## Colunas
| Nome do filme | NFO <title>, depois XML <LocalTitle>, títulos originais, o nome da pasta. Ao passar o mouse: a pasta, a biblioteca, a data de inclusão e cada motivo de saúde. Clique duplo abre a pasta. Um filme em várias partes (Filme-CD1.mkv + Filme-CD2.mkv) aparece como "Nome — Parte 1 + Parte 2"; só a exibição muda, não os arquivos.
| Ano | NFO <year> ou XML <ProductionYear>.
| Gêneros | tags <genre> do NFO; quando o NFO não tem nenhuma, o XML <Genres> (a dica diz a origem).
| Nota | NFO <rating> (ou o bloco <ratings> do Kodi), XML <IMDBrating> / <Rating>. Ao passar o mouse: valor, votos, fonte.
| Votos | NFO <votes>, XML <Votes> / <VoteCount>.
| Fonte | os IDs do IMDb e do TMDB de cada tag: ⬤ todos iguais, ◐ parcial ou em conflito, ○ faltando, ✕ algumas tags preenchidas e outras vazias. Ao passar o mouse mostra o último resultado de Verificar IDs; clique duplo abre o IMDb ou o TMDB.
| Pôster, Pasta, Fanart | status e nível de qualidade de cada imagem (aba Imagens).
| Fundos | o número de imagens de fundo; ao passar o mouse: o tamanho médio delas.
| .nfo / .xml | o status do arquivo de metadados. Ao passar o mouse lista os erros com a linha e os nomes das tags (os 5 primeiros); clique duplo abre o arquivo no seu editor. O modo de saúde oculta a coluna do arquivo que não usa (.xml para Kodi, Jellyfin, Emby…; .nfo para só movie.xml); — significa não usado (uma biblioteca só com NFO).
| Idioma | o <Language> de nível superior do movie.xml: o idioma para baixar metadados. Sem movie.xml: o <language> de nível superior do NFO (o mesmo significado), senão o idioma da primeira faixa de áudio. A dica diz a origem. Vazio é normal.
| Vídeo, Tamanho, Qualidade | contêiner, tamanho e classe de resolução.
| Áudio | faixas de áudio do FFprobe, p. ex. EN (5.1), PT (2.0).
| Idioma OK? | S / N: o idioma de destino no áudio ou nas legendas (o cabeçalho mostra o código, p. ex. "PT OK?").
| Legendas | faixas embutidas (FFprobe) e arquivos externos.
| Biblioteca | a biblioteca (pasta raiz). Oculta por padrão.
| Coleção | a coleção do filme (NFO <set>). Oculta por padrão.
**Ferramentas → Escolher colunas…** mostra ou oculta colunas; a escolha é mantida. Arraste a borda de um cabeçalho para redimensionar uma coluna, dê um clique duplo num cabeçalho para ajustá-la, ou use **↔ Ajustar colunas**. **↺ Larguras padrão** devolve a largura original a todas as colunas depois de um redimensionamento que deu errado. Na vista agrupada a coluna Ano se alarga para os anos de uma coleção ("1979–1986") e volta à sua largura quando você desagrupa. Larguras, tamanhos e posições das janelas são lembrados.

## Filtro
Digite na caixa **Filtro** ([[Ctrl+F]]) para manter os filmes cujo nome, ano, gênero, idioma, qualidade, status de saúde, motivo de saúde ou coleção corresponde — "fundo" lista todos os problemas de imagens de fundo. [[Esc]] limpa o filtro.
- **Só problemas** oculta as linhas verdes.
- A caixa de biblioteca ao lado de **Bibliotecas…** mostra uma biblioteca ou todas.
- "n de m mostrados" conta os filmes que o filtro mantém.

## Ordenação
A linha de ordenação diz "Ordenar por [coluna] [direção]"; **+ depois por** adiciona até mais dois níveis (✕ remove um). A direção é dita em palavras — A → Z, Mais novos primeiro, Maior → menor, Piores primeiro, Erros primeiro … — clique nela para invertê-la.
- Toda coluna pode ser usada, além de **Saúde** e **Número de problemas** (as duas primeiras opções) e **Data de inclusão** (NFO <dateadded>, XML <DateAdded>, senão a data de criação do vídeo ou da pasta).
- Clique no cabeçalho de uma coluna para ordenar por ela (de novo = invertido); Shift+clique a adiciona como o próximo nível. ▲1 / ▼2 nos cabeçalhos mostram os níveis.
- Valores vazios (sem nota, sem pôster, sem data) vão por último, a menos que um nível peça os vazios primeiro (a predefinição Metadados faltando pede); valores iguais ficam na ordem de Nome do filme.
- **★ Predefinições ▾**: Problemas primeiro, Piores imagens primeiro, Metadados faltando, Melhores notas, Maiores arquivos, Por biblioteca, Por nome da coleção (coleção A → Z, depois ano, depois nome do filme; filmes sem coleção por último), e as suas (**Salvar a ordem atual como predefinição…**; renomeie ou exclua no mesmo menu). [[Ctrl+1]] … [[Ctrl+9]] aplicam as predefinições 1 a 9.
- **↺ Atualizar vista** ordena e filtra de novo, para que os filmes que você acabou de corrigir vão para o seu lugar.
- A ordenação é mantida depois de um scan e depois de reiniciar.

## Duplicados
Filmes que têm o mesmo ID do IMDb, o mesmo ID do TMDB ou o mesmo título + ano são um "Possível duplicado" (o mesmo título + ano com dois IDs do IMDb diferentes não é: é uma refilmagem ou um homônimo). Clique direito → **✔ Não é duplicado…** guarda sua resposta em not_duplicates.json, para que o aviso não volte; uma nova terceira cópia ainda é encontrada. **↺ Desfazer 'não é duplicado'** volta atrás; **Ferramentas → Gerenciar marcas 'Não é duplicado'…** lista cada par. **Ferramentas → Relatório de filmes duplicados** lista todos.
"""

TAB_03 = """
# Scans e bibliotecas

## Scans
| Full Scan | lê de novo todos os filmes das bibliotecas incluídas ([[F5]]).
| Quick Scan | lê só os filmes adicionados, removidos ou alterados desde o último scan (um NFO, imagem, legenda ou pasta de disco alterado conta).
| Chave FFprobe | na barra de status: quando ligada, os scans também leem a resolução do vídeo, as faixas de áudio e as legendas embutidas. Um scan sem FFprobe mantém os dados anteriores do FFprobe.
| Cancelar / Esc | para um scan em andamento; os filmes lidos até ali são mantidos.
Um scan nunca grava nos seus arquivos. Enquanto ele roda, as ações que alteram arquivos esperam por ele (a barra de status avisa).

## Bibliotecas
Você pode verificar várias pastas raiz. **Procurar…** adiciona uma pasta; **Bibliotecas…** adiciona, remove e ordena as pastas. Depois que a lista muda, o app oferece Full Scan, Quick Scan ou Agora não. **Ativa / desligada** desliga uma biblioteca sem removê-la: ela não é escaneada (o disco dela não é tocado) e os filmes dela saem da tabela e dos contadores, mas ficam guardados; ligada de novo, eles voltam na hora (um Quick Scan os atualiza). A parte da pasta das coleções define a pasta de onde o Kodi lê a arte das coleções: **Escolher…**, **Criar…** (cria "Sets" ao lado da primeira biblioteca, depois de um sim) ou **Limpar**. Os scans nunca a listam como filme nem como pasta ignorada.
- Todas as bibliotecas compartilham uma tabela; a coluna **Biblioteca** e a dica do Nome do filme mostram onde um filme está.
- A caixa de biblioteca escolhe o que a tabela mostra e o que os scans cobrem ("Todas as bibliotecas" ou uma delas).
- Uma biblioteca que não pode ser acessada (um compartilhamento de rede desconectado) mantém o último scan, é pulada pelos scans e aparece como "(offline)". Uma pasta de filme que não pode ser lida por um momento mantém a sua linha, marcada como "(não lido)".
- Os duplicados são encontrados entre bibliotecas.
- Os filmes podem estar mais fundo: uma pasta que só contém outras pastas (Single Movies / HD / <movie>, Boxsets / <saga> / <movie>) é pesquisada, até 5 níveis abaixo da biblioteca. Cada filme mantém a sua biblioteca na coluna Biblioteca.

## Pastas ignoradas
Um scan só adiciona uma linha para pastas de filme. Estas não são adicionadas:
- Séries de TV: tvshow.nfo, pastas Season ou arquivos de episódio (S01E02, 1x02). O suporte a séries chega na v0.22.
- Pastas de pastas 5 níveis abaixo da biblioteca: os filmes delas estariam mais fundo do que o scan procura (5 níveis). A linha diz a profundidade da pasta; adicione-a como biblioteca para incluir os filmes dela.
- Pastas com vários vídeos separados: dê a cada filme a sua própria pasta.
- Pastas sem vídeo, NFO ou XML, pastas do sistema ($RECYCLE.BIN, @eaDir …) e pastas que não puderam ser lidas.
Uma pasta com metadados de filme é sempre um filme, e uma pasta com um vídeo e sem NFO também. Depois de um scan, a janela **Pastas ignoradas no último scan…** abre quando algo ficou de fora (filtrar, ordenar, clique duplo para abrir, **Exportar para TXT…**, **Copiar tudo**); desligue isso com "Mostrar esta janela depois de um scan". **Ferramentas → Pastas ignoradas no último scan…** a abre a qualquer momento.

## Atualizar filmes individuais
Clique direito → **Atualizar (sem FFprobe)** ([[Ctrl+R]]) lê de novo o filme ou a seleção; **Atualizar (com FFprobe)** ([[Ctrl+Shift+R]]) também analisa o vídeo (um filme: uma linha de status; vários: uma janela de progresso com Cancelar). Depois de cada reparo, sincronização, busca ou exclusão, as linhas afetadas se atualizam sozinhas.

## Filmes que desaparecem
Quando uma pasta de filme foi excluída, Atualizar ou a atualização automática remove a sua linha. Clique direito → **Remover da lista** tira linhas sem tocar em nenhum arquivo; o próximo scan traz de volta os filmes que ainda existem.

## Salvar e carregar scans
- O último scan é salvo em last_results.json e carregado em segundo plano ao abrir ("⏳ Carregando o último scan…"); as regras de saúde são aplicadas de novo, então regras alteradas nunca deixam motivos antigos para trás.
- **••• → Salvar resultados do scan…** / **Abrir resultados do scan…** gravam um scan num arquivo ou carregam um.
- **••• → Limpar tudo…** ([[Ctrl+L]]) esvazia a tabela (pergunta antes). Nenhum arquivo de filme muda; o último scan salvo também é esvaziado, para que as linhas não voltem na próxima vez que o app abrir.
"""

TAB_04 = """
# Saúde e correção de problemas

## Como a saúde funciona
Toda condição que pode deixar uma linha vermelha (erros) ou amarela (avisos) é uma regra em **Configurações → Regras de saúde**, com uma caixa de seleção e às vezes um nível ou um limite. **Ferramentas → Recalcular a saúde (sem novo scan)** aplica as regras alteradas na hora (o que também é feito toda vez que o app abre).
- Passe o mouse sobre o Nome do filme para ver cada motivo de um filme; o painel do filme selecionado também os lista.
- **Ferramentas → Relatório de saúde — Todos os filmes** grava todos eles, com os problemas mais comuns primeiro e os filmes cuja coleção não foi verificada online.
- **Ferramentas → Verificar melhorias — Todos os filmes…** lista metadados que poderiam ser melhores (pares de tags de **Configurações → NFO / XML**, tamanhos de arquivo).
- **Ferramentas → Estatísticas da biblioteca**: saúde, qualidade, gêneros, décadas, bibliotecas.

## Corrigir problemas
O menu do botão direito começa com o nome do filme (ou "N filmes selecionados") e o seu número de problemas, depois **⚠ Corrigir problemas**: os problemas reais da seleção, cada um ligado à ação que o corrige — com vários filmes, quantos filmes têm cada problema (a ação roda só neles). O painel do filme selecionado tem a mesma lista como botões **Corrigir**.
| Pôster / folder.jpg faltando | Buscar pôster/pasta…
| Fanart faltando | Buscar fanart…
| Poucas imagens de fundo / pequenas | Buscar imagens de fundo…
| Proporções / tamanho da imagem | Corrigir proporções / tamanho da imagem…
| folder.jpg diferente do pôster | Copiar poster.jpg → folder.jpg
| Erros no NFO / XML | mostrar os erros (cada erro com a sua linha)
| Título local diferente (NFO ↔ XML) | Igualar os títulos…
| Coleção faltando / diferente | Corrigir coleção… (aba Coleções)
| Pasta / imagens da coleção faltando | Imagens da coleção… (uma coleção) ou Criar pasta da coleção… (várias)
| Possível duplicado | Não é duplicado…
| Qualidade do vídeo abaixo do mínimo | precisa de uma cópia melhor do vídeo (sem correção automática)
| NFO com o nome da pasta | Renomear NFO para o Kodi…
| ID do IMDb / TMDB faltando | Procurar fontes…
| IDs só num arquivo / em conflito | Normalizar fontes
| IDs não verificados / filme errado | Verificar IDs do IMDb/TMDB
| Nota / votos faltando ou errados | Sincronizar notas
| Faixa / idioma de áudio | Legendas…
| Idioma de legenda faltando | Legendas embutidas na imagem…
| O Reparo automático pode corrigir mais | Reparo automático

## O menu do botão direito
Também [[Shift+F10]] ou a tecla Menu, na linha selecionada. Uma ação que não se aplica fica no seu lugar, acinzentada, com o motivo ("faltando", "só um filme" …).
- **Repetir**: a última ação de novo na seleção atual (Configurações → Interface pode ocultar esta linha).
- **Abrir pasta** ([[Ctrl+O]]), **Reproduzir vídeo**, **Editar NFO** ([[Ctrl+E]]).
- **Imagens**: abrir as imagens — a opção diz o nome do arquivo encontrado, p. ex. **Abrir poster.jpg**, **Abrir folder.jpg**, **Abrir fanart.jpg** (**Abrir pôster** acinzentado quando não há nenhum ou vários filmes estão selecionados); **Buscar pôster/pasta**, **Buscar fanart**, **Buscar imagens de fundo**, **Substituir todas as imagens de fundo**, **Extrair imagem(ns) de fundo**, **Copiar poster.jpg → folder.jpg**, **Corrigir proporções / tamanho da imagem…**.
- **Metadados**: **Abrir .nfo**, **Abrir movie.xml**, **[!] Erros no NFO** / **[!] Erros no XML**, **Igualar os títulos (NFO ↔ XML)…**, **Renomear NFO para o Kodi…**, **Coleção ▸**, **Sincronizar notas do IMDb / TMDB**, **Normalizar gêneros**, **Comparar gêneros com o TMDB…**, **Remover links de arte online do NFO…**, **Adicionar gênero(s) personalizado(s) às configurações**.
- **IDs e fontes**: **Procurar fontes**, **Verificar IDs do IMDb/TMDB**, **Normalizar fontes**, **Copiar o nome do filme**.
- **Vídeo e legendas**: **Legendas…**, **Legendas embutidas na imagem…**.
- **Abrir online**: **Abrir no IMDb**, **Abrir no TMDB**, **Abrir no Fanart.tv**, **Abrir no OpenSubtitles.org**, **Abrir no scraper**.
- **Verificar e reparar**: **Relatório de saúde**, **Verificar melhorias**, **Reparo automático**.
- **Atualizar**: **Atualizar (sem FFprobe)**, **Atualizar (com FFprobe)**; **Remover da lista**.
Vários filmes: selecione com Ctrl+clique, Shift+clique, Shift+setas ou Shift+PageUp / PageDown / Home / End. O mesmo menu executa as versões em lote; execuções mais longas mostram uma janela de progresso com Cancelar.

## Clique duplo
| Nome do filme | a pasta do filme
| Gêneros, Nota, Votos | o arquivo .nfo no seu editor
| Fonte | escolher a página do IMDb ou do TMDB
| Pôster, Pasta, Fanart | a imagem no seu visualizador
| Fundos | a primeira imagem de fundo
| .nfo / .xml | o arquivo no seu editor (também quando tem erros)
| Idioma | o arquivo de onde veio o valor (movie.xml ou o NFO) no seu editor
| Vídeo, Qualidade | reproduz o vídeo
| Legendas | as faixas de legenda
| Biblioteca | a pasta da biblioteca
| Coleção | o arquivo .nfo no seu editor

## Regras de saúde que vale a pena conhecer
- "Imagem da pasta faltando" fica desligada quando o modo de saúde é só NFO (todo servidor mostra o poster.jpg sem um folder.jpg); todo perfil a liga nos modos com movie.xml. "Pôster e imagem da pasta diferentes" vem desligada por padrão.
- "Logo (clear logo) / arte do disco faltando" (clearlogo.png, logo.png, disc.png, discart.png, cdart.png, também como <vídeo>-clearlogo.png …) só vem ligada no perfil Rigoroso: o skin padrão do Kodi quase não as usa, alguns outros skins usam. O MediaClinic ainda não as baixa.
- "Não lido pelo Infuse: movie.nfo (precisa de <video>.nfo)" — com programas marcados no topo das Regras de saúde, um aviso quando o NFO, o pôster ou o fanart tem um nome que um deles não lê (o Infuse, verificado numa Apple TV com as opções "Preferir arte locais" e "Preferir metadados locais" ligadas, lê <video>.nfo, nunca movie.nfo; de arte ele lê <video>-poster.jpg, <video>.jpg, poster.jpg, folder.jpg, <video>-fanart.jpg e fanart.jpg, e sem nenhuma delas mostra qualquer outra imagem da pasta como pôster). O Emby foi verificado num servidor real: lê <video>.nfo e movie.nfo, a coleção do NFO e todos os nomes comuns de pôster e fanart, então uma pasta no estilo do Kodi funciona no Emby como está. O Jellyfin também foi verificado e lê o mesmo; ele cria coleções a partir do NFO só quando a opção da biblioteca "Automatically add to collection" está ligada (Dashboard → Libraries → Manage library; desligada por padrão) e dois ou mais filmes têm o mesmo nome de coleção. O Plex foi verificado num servidor real: lê todos os nomes comuns de pôster e fanart (poster, folder, cover, <video>, <video>-poster, fanart, backdrop, background, .jpg ou .png), mas nenhum NFO e nenhuma coleção vinda dele; com só o Plex marcado, uma janela pergunta uma vez se as verificações de NFO e de coleções devem ser desligadas (mude depois na caixa abaixo dos programas). As marcas também desligam o que esses programas não usam: só o Infuse não tem verificações de folder.jpg, backdrops extras nem coleções, e as verificações de NFO só do Kodi rodam apenas quando o Kodi está marcado. Buscar grava a arte nova no nome que todo programa marcado lê; quando não há nenhum, grava um arquivo para cada um.
- **Renomear arquivos para meus programas…** (clique direito, ⚠ Corrigir problemas, ou Ferramentas → **Renomear arquivos para meus programas — Todos os filmes…**) é a correção desse aviso: dá ao NFO, ao pôster e ao fanart os nomes que todo programa marcado lê (ex.: movie.nfo → <video>.nfo para o Infuse). Uma prévia lista cada renomeação antes; um backup vem primeiro e o Histórico de backups pode desfazer. O vídeo nunca é renomeado, um arquivo existente nunca é sobrescrito, e uma pasta com dois NFOs, uma pasta de DVD / Blu-ray ou um par de programas sem nome em comum é listada e deixada como está.
- **Converter movie.xml → NFO…** (clique direito num filme que tem movie.xml e não tem NFO, ou Ferramentas → **Converter movie.xml → NFO — Todos os filmes sem NFO…**) é para uma biblioteca que passa do MediaBrowser / Media Center Master para Kodi, Plex, Jellyfin, Emby ou Infuse: cria um NFO a partir de cada movie.xml (títulos, ano, data de lançamento, duração, sinopse, nota e votos, IDs, gêneros, estúdios, diretor, roteiristas, atores, coleção) com o nome que os programas marcados leem (<vídeo>.nfo quando um programa está marcado; movie.nfo quando nenhum está, ou para uma pasta de DVD / Blu-ray, um filme em várias partes ou uma pasta sem vídeo). O movie.xml não é alterado; uma prévia vem primeiro e o Histórico de backups pode desfazer (remove os NFOs novos).
- "O NFO tem links de arte online" vem desligada em todos os perfis. **Remover links de arte online do NFO…** (clique direito → a parte do NFO, ou Ferramentas → … — Todos os filmes…) remove os links da web (<thumb> / <fanart><thumb>) só das artes que a pasta tem como arquivo; conta-os antes, faz backup de cada NFO e mantém as imagens de atores, as artes de coleção e todas as outras tags.
- "O NFO tem um '&' sem escape": o Kodi lê um NFO assim, mas o Jellyfin pode ignorar o arquivo inteiro. O Reparo automático grava '&amp;'. Um ID do IMDb / TMDB só em <imdbid> / <tmdbid> também é um aviso: o Kodi lê <uniqueid>, então o Reparo automático o adiciona (e mantém as outras tags); uma data em <premiered> vale como o ano. No movie.xml, um ID ou os votos só em <IMDB_ID> / <TMDB> / <Votes> também são um aviso: os programas antigos leem <IMDbId> / <TMDbId> / <VoteCount>, e o Reparo automático os adiciona. "Tags de ID gravadas no NFO" (nestas regras do NFO) escolhe como um ID IMDb / TMDB é gravado: todos os estilos de tag (<id>, <uniqueid>, <imdbid>, <id moviedb>, para todo programa achar; o padrão) ou só <uniqueid> (o Kodi, o Jellyfin e o Emby o leem). Com só <uniqueid>, as tags de ID que o NFO já tem continuam sendo corrigidas, nenhuma outra tag de ID e nenhuma tag vazia é adicionada; o movie.xml não muda.
- Verificações de conteúdo: IDs que não são válidos, um ano fora do intervalo, uma duração ou votos que não são um número, uma nota acima de 10, uma tag escrita duas vezes, um <title> / <plot> vazio (ligado só no perfil Rigoroso).
- "Título diferente entre NFO e XML" mostra os dois títulos locais; "Quando o Reparo automático não sabe qual é o título local certo" escolhe o que o Reparo automático faz nesse caso.
- Um ID faltando: "Filme com UMA fonte só" e "Filme SEM fonte" podem ser cada um um erro, um aviso ou desligado.
"""

TAB_05 = """
# Imagens

## Pôster, pasta e fanart
**Buscar pôster/pasta…** mostra a sua imagem ao lado dos pôsteres do TMDB (e do fanart.tv); **Usar esta** baixa o tamanho completo para o pôster (e para o folder.jpg quando a pasta usa um) depois de um backup. **Buscar fanart…** faz o mesmo para o fanart. **Copiar poster.jpg → folder.jpg** corrige pastas cujo folder.jpg é diferente; **Ferramentas → Copiar poster.jpg → folder.jpg — Todos os filmes com diferenças…** mostra uma prévia antes.
- Um download é verificado antes de substituir qualquer coisa: uma página que não é uma imagem, ou uma imagem cortada, nunca substitui um arquivo bom.
- As janelas de busca fecham com **Concluído** (ou [[Esc]]); as imagens aplicadas antes são mantidas. Enquanto um download roda, Concluído mostra "Finalizando…".

## Níveis de qualidade
| Pôster / Pasta (2:3) | 4K 2000×3000 · 1440p 1500×2250 · 1080p 1000×1500 · 720p 666×1000 · 540p 540×810 · 480p 480×720 · 360p
| Fanart (16:9) | 4K 3840×2160 · 1440p 2560×1440 · 1080p 1920×1080 · 720p 1280×720 · 540p 960×540 · 480p 854×480 · 360p
Tolerância de ±5 %. O nível mínimo é uma configuração (Configurações → Regras de saúde e Configurações → Tamanhos de imagem); imagens abaixo dele são avisos. Proporções: pôster e pasta 2:3 (3:4 opcional), fanart 16:9 (3:2 opcional). "Corrompida" (✕) significa que o scan encontrou um cabeçalho ou um fim de arquivo ruim. Um arquivo danificado no meio pode passar no scan; Corrigir imagem ou Copiar pôster então diz que ele não pode ser lido. Um PNG chamado poster.jpg é lido e recebe um aviso de "a extensão não corresponde".

## Imagens de fundo
| Extrair imagem(ns) de fundo | quadros do FFmpeg espalhados ao longo do filme
| Buscar imagens de fundo | escolha imagens de fundo do TMDB / fanart.tv; substitua um arquivo ou salve um novo
| Substituir todas as imagens de fundo | escolha a fonte e quantas (começa no número que você tem); a maior resolução primeiro, um download que falha é substituído pela próxima imagem; um backup antes
**Ferramentas → Excluir subpastas extrafanart — Todos os filmes…** remove as pastas extrafanart (um backup antes). O Jellyfin e o Emby as usam como imagens de fundo extras; o Kodi e o Plex não as leem. As regras de saúde marcam poucas imagens de fundo e as muito pequenas.

## Quadros do filme
Buscar fanart e Buscar imagens de fundo têm um botão **🎞 Quadros do filme** (com o FFmpeg definido e um vídeo na pasta).
- 10 quadros de 10 %–90 % da duração; quadros pretos ou chapados são substituídos por um momento próximo. **Mais quadros** traz um novo conjunto.
- Os quadros mantêm a resolução do vídeo e são marcados quando estão abaixo do mínimo de fanart. São arquivos temporários, excluídos quando a janela fecha.
- Não precisa de ID do TMDB: sem ele, Buscar fanart e Buscar imagens de fundo abrem nos quadros do filme (ou no fanart.tv pelo ID do IMDb).

## fanart.tv
Com uma chave do fanart.tv (Configurações → Chaves de API) as janelas de busca e Substituir todas as imagens de fundo ganham uma escolha de **Fonte**: TMDB, fanart.tv ou Ambos.
- Pôsteres: primeiro o idioma da sua biblioteca, depois imagens sem texto, depois inglês.
- Imagens de fundo: fundos do fanart.tv (1920×1080); marque "incluir miniaturas paisagem" para as de 1000×562.
- O fanart.tv não informa o tamanho em pixels: "~1920×1080" é o tamanho habitual; o tamanho real é verificado depois do download. As respostas são guardadas por 7 dias.

## Corrigir proporções e tamanho
Clique direito → Imagens → **Corrigir proporções / tamanho da imagem…** corrige um pôster, imagem da pasta ou fanart com proporções erradas ou resolução baixa, com uma vista de antes / depois.
- **Método**: Preencher com desfoque mantém a imagem inteira e preenche as faixas vazias com uma cópia desfocada (pôsteres); Corte inteligente mantém a parte mais detalhada (fanart); Corte central; Preencher com cor sólida. Até 3 % é simplesmente esticado.
- **Tamanho**: o nível mais próximo da imagem, com o seu fator e uma marca — ✓ recomendado, ⚠ suave, ✕ longe demais (não oferecido). "Manter o tamanho atual" corrige só as proporções. Para uma imagem muito maior use **Procurar uma melhor online**.
- **Ampliar com IA** (opcional): **Baixar o ampliador (cerca de 45 MB)…** instala o Real-ESRGAN (conferido pelo seu SHA-256) e o testa uma vez; ele precisa de uma placa de vídeo com Vulkan. ×2 é recomendado, até ×4 é permitido — confira a prévia: a IA pode inventar detalhes.
- "Copiar também o resultado para folder.jpg" vem marcado quando o folder.jpg é a mesma imagem do pôster; quando é outra imagem, aparece "Corrigir também folder.jpg (outra imagem: corrigida à parte, não substituída)". Cada arquivo tem backup antes.
- Vários filmes, ou **Ferramentas → Corrigir proporções / tamanho das imagens — Todos os filmes com avisos de imagem…**: uma prévia lista cada imagem e a sua correção; só os tamanhos ✓ são usados. Você pode minimizar a janela enquanto ela roda; **■ Parar** a interrompe.
"""

TAB_06 = """
# Notas, gêneros e IDs

## Notas
**Sincronizar notas** busca a nota e os votos no TMDB e / ou no OMDb (dados do IMDb) e os grava no NFO (<rating>, <votes>, <ratings> do Kodi) e no XML (<IMDBrating>, <Rating>, <Votes>, <VoteCount>).
- A janela mostra as duas fontes lado a lado. Uma nota 0 ou 0 votos conta como sem dados.
- Vários filmes: "Aplicar esta escolha a todos os filmes restantes" ou "Usar a fonte com mais votos" (votos iguais → média); **Ferramentas → Sincronizar notas online — Todos os filmes…** busca primeiro e depois mostra atual → novo para cada filme.
- Quando nenhuma fonte tem dados, uma segunda janela pede uma vez valores digitados ou Pular.
- Quando o TMDB ou o OMDb não pode ser acessado, o filme é pulado e listado no final — nunca tratado como "sem nota".
Os padrões das caixas de seleção: Configurações → Notas.
| ⬤ | encontrada, NFO e XML iguais
| ◐ | NFO e XML diferentes
| ○ | nenhuma tag encontrada
| ✕ | a tag não é um número

## Gêneros
**Normalizar gêneros** corrige os gêneros nos dois arquivos: maiúsculas, sinônimos ("Sci-Fi" → "Science Fiction"), traduções (PT, DE, FR, ES, IT, RU, ZH, AR), duplicados e tags juntadas ("Family/Fantasy"). Copia os gêneros para o arquivo que não tem nenhum e transforma <Genres>/<Genre> num NFO em tags <genre> do Kodi. Filmes sem gêneros os recebem do TMDB (depois do OMDb), com uma prévia antes. Gêneros que não estão em Configurações → Gêneros são "personalizados": mantenha ou exclua, ou Clique direito → **Adicionar gênero(s) personalizado(s) às configurações**. **Ferramentas → Normalizar gêneros — Todos os filmes…** mostra a prévia de cada alteração.
**Comparar gêneros com o TMDB…** (clique direito, ou Ferramentas → … — Todos os filmes…) procura no TMDB os filmes que já têm gêneros e um ID, e lista só aqueles cujos gêneros são diferentes (arquivo → TMDB). Nada vem marcado: cada arquivo mantém os seus gêneros, a não ser que você marque o filme; os marcados recebem os gêneros do TMDB (backup antes, Desfazer). Precisa de uma chave da API do TMDB.

## IDs do IMDb e do TMDB
- **Normalizar fontes** preenche as tags faltando, deixa você escolher entre IDs em conflito (títulos consultados no TMDB) e pede um ID onde não há nenhum. Quando só um ID é conhecido, cada gravação de ID deixa tags VAZIAS para a outra fonte (p. ex. <tmdbid></tmdbid>), prontas para preencher à mão (não com **só <uniqueid>**, Configurações → Regras de saúde → NFO). Valores existentes nunca são apagados.
- **Procurar fontes** procura o filme no TMDB por título + ano (em inglês, no idioma da sua biblioteca e pelo título original). Cada filme mostra os IDs que os seus arquivos têm agora e, primeiro, o filme por trás desse ID. **Digitar ID…** deixa você digitar um ID do IMDb (tt…) ou do TMDB, mostra título, ano e pôster e depois grava os dois IDs. Ele também aceita o endereço de uma página do IMDb ou do TMDB, ou um número do IMDb sem tt; um valor errado no IMDb ao lado de um ID do TMDB válido é deixado de fora (a janela avisa) e o ID do IMDb que o TMDB indica é usado.
- Filmes no IMDb mas não no TMDB: a primeira linha diz "IMDb tt… — não está no TMDB"; **Confirmar IMDb** grava o ID do IMDb e marca o filme como "OK (IMDb only — not on TMDB)", para que Verificar IDs e o Reparo automático parem de procurá-lo.
- **Verificar IDs do IMDb/TMDB** confere no TMDB se os IDs pertencem ao filme (título em qualquer idioma, ano ±1): OK, IMDb e TMDB apontam para filmes diferentes, ID pertence a outro filme, ID não existe, NFO e XML discordam, sem IDs. O relatório ordena por qualquer coluna e salva em .txt ou .csv; nada é gravado até você clicar em **Corrigir…**. Ele também guarda a coleção do TMDB do filme (aba Coleções). Uma tag com algo que não é um ID (p. ex. o número do TMDB 7840 numa tag do IMDb) dá "ID do IMDb faltando (a tag contém '7840', que não é um ID válido)", ou "Conflito de ID do IMDb entre as tags: '7840' não é um ID válido" ao lado de um ID bom; o Reparo automático então o preenche, conferindo primeiro o ID que o filme já tem (título + ano) antes de procurar pelo título. Em **Escolha o registro do TMDB**, clique em qualquer lugar da linha de um filme para escolhê-lo (borda verde); um clique duplo o aplica.
- **Copiar o nome do filme** copia o título (pergunta quando os arquivos têm vários).

## Títulos locais
Quando o NFO <title> e o XML <LocalTitle> diferem, Clique direito → Metadados → **Igualar os títulos (NFO ↔ XML)…** deixa você escolher; o Reparo automático dá ao lado que é o título original (ou que não corresponde à pasta) o outro título.

## Áudio, legendas e idioma
- **Áudio**: faixas do FFprobe como IDIOMA (CANAIS); passe o mouse para ver codec e bitrate. Uma faixa que o FFprobe informa como UND recebe o idioma do NFO ou do XML quando combina ("POR — from NFO"). Nada é gravado.
- **Legendas**: faixas embutidas e arquivos externos (p. ex. Movie.pt.srt, também numa pasta Subs; as marcas forced e SDH são lidas). Clique direito → **Legendas…** abre para qualquer filme; **🌐 Abrir no OpenSubtitles.org** procura o filme lá.
- **Legendas embutidas na imagem…** marca legendas gravadas na imagem (elas não podem ser detectadas): marque o(s) idioma(s) ou digite um código ISO 639-2. O app grava <tag>Hardsub POR</tag> no NFO e <Tags><Tag>Hardsub POR</Tag></Tags> no XML; a coluna mostra "Hard: POR".
- A coluna **Idioma OK?** é S quando o idioma de destino (Configurações → Idioma) está numa faixa de áudio ou numa legenda: lido pelo FFprobe, um arquivo de legenda, uma marca de legenda embutida ou um fluxo escrito no NFO (streamdetails) ou no movie.xml (MediaInfo). O <language> do NFO e o <Language> / <LanguageCode> do XML no nível superior não contam: eles são o idioma para baixar metadados.
"""

TAB_07 = """
# Ferramentas e Reparo automático

## O menu Ferramentas
| Exportar lista de filmes… | CSV, TSV, texto, Excel ou uma página HTML ([[Ctrl+Shift+E]], também o botão **Exportar…**)
| Escolher colunas… | mostrar ou ocultar colunas
| Pastas ignoradas no último scan… | as pastas que o último scan não incluiu
| Estatísticas da biblioteca | saúde, qualidade, gêneros, décadas, bibliotecas
| Relatório de filmes duplicados | o mesmo ID, ou título + ano, em outro lugar
| Gerenciar marcas 'Não é duplicado'… | suas respostas, com Remover
| Recalcular a saúde (sem novo scan) | as regras de novo, sem ler arquivos
| Salvar / Abrir resultados do scan… | um scan para ou de um arquivo (**Salvar resultados do scan…**, **Abrir resultados do scan…**)
| Histórico de backups / Desfazer… | cada execução que alterou arquivos (aba Backups e desfazer)
| Atualizar ícones — Todos os filmes | redesenha todas as linhas ([[Ctrl+I]])
Os itens "— Todos os filmes": **Sincronizar notas online — Todos os filmes…**, **Normalizar fontes — Todos os filmes…**, **Procurar fontes — Todos os filmes…**, **Verificar IDs do IMDb/TMDB — Todos os filmes…**, **Verificar coleções online — Todos os filmes…**, **Corrigir coleções — Todos os filmes…**, **Criar pastas de coleção — Todas…**, **Reparo automático — Todos os filmes…**, **Normalizar gêneros — Todos os filmes…**, **Comparar gêneros com o TMDB — Todos os filmes…**, **Verificar melhorias — Todos os filmes…**, **Relatório de saúde — Todos os filmes**, **Copiar poster.jpg → folder.jpg — Todos os filmes com diferenças…**, **Corrigir proporções / tamanho das imagens — Todos os filmes com avisos de imagem…**, **Renomear NFOs para o Kodi — Todos os filmes com NFO com o nome da pasta…**, **Remover links de arte online dos NFOs — Todos os filmes…**, **Excluir subpastas extrafanart — Todos os filmes…**. Eles sempre abrangem todos os filmes de todas as bibliotecas; quando um filtro oculta linhas, a prévia diz "todos os N filmes de todas as bibliotecas (o filtro mostra M)".

## Prévias antes de gravar
As ferramentas em lote mostram primeiro o que vai mudar; fechar a prévia não grava nada, o botão **▶** (com o nome da própria ação) grava. Cada execução cria uma pasta de backup, pode ser cancelada ("Cancelado após k de n; m ficaram de fora") e termina com um resumo que aponta para **Histórico de backups / Desfazer**.

## Reparo automático
Aplica todas as correções seguras de uma vez. As imagens nunca são tocadas. Primeiro um backup; o resumo lista os filmes corrigidos, pulados e que ainda falham; **Reparo automático — Todos os filmes…** oferece uma prévia de simulação. As etapas, nesta ordem:
1. Escapar '&' no NFO (& → &amp;; o Jellyfin ignora um NFO com '&' sem escape)
2. Resolver IDs IMDb/TMDB em conflito com o TMDB
3. Procurar IDs IMDb/TMDB no TMDB (título + ano exatos aplica sozinho, senão pergunta)
4. Copiar o ID IMDb/TMDB para o outro arquivo; Adicionar <uniqueid> para os IDs que o Kodi não lê (mantém <imdbid> / <tmdbid>); Adicionar as tags do movie.xml que os programas antigos leem (<IMDbId>, <TMDbId>, <VoteCount>)
5. Sincronizar nota e votos online (TMDB/OMDb)
6. Normalizar gêneros e sincronizá-los entre NFO e XML (gêneros personalizados mantidos)
7. Preencher gêneros pelo TMDB (exige ID do TMDB verificado)
8. Preencher o ano pelo TMDB (exige ID do TMDB verificado)
9. Copiar o título entre NFO <title> e XML <LocalTitle>
10. Igualar o título local no NFO <title> e no XML <LocalTitle>
12. Limpar IDs como 'tt0133093/' e remover tags duplicadas idênticas (NFO / XML)
13. Gravar a coleção que o TMDB lista para o filme (NFO <set>; suas próprias coleções são mantidas)
14. Renomear o NFO com nome da pasta para o Kodi lê-lo (<video>.nfo; movie.nfo para discos, várias partes, versões)

## Exportar lista de filmes
- Colunas: Básico, Identificar (links + sinopse), Padrão, Todas, ou sua própria escolha (a coluna Coleção também).
- Linhas: todos os filmes ou a vista filtrada atual (na vista agrupada: os filmes, nunca as linhas de coleção).
- Formatos: CSV com vírgula, CSV com ponto e vírgula (Excel em CH / DE / PT / FR), separado por tabulação, lista simples, Excel .xlsx, página HTML. Um arquivo salvo oferece "Abrir agora?".
- Página HTML: um arquivo que abre em qualquer navegador, com as colunas escolhidas, uma caixa de filtro e ordenação com um clique no título da coluna; claro ou escuro como o sistema. **Incluir miniaturas dos pôsteres** põe uma cópia pequena de cada pôster dentro do arquivo (arquivo maior; os pôsteres são lidos com uma janela de progresso e Cancelar).
"""

TAB_08 = """
# Coleções

## O que é uma coleção
Uma coleção (o Kodi a chama de movie set) agrupa os filmes de uma saga — "Harry Potter Collection", "The Matrix Collection". O NFO a guarda como <set><name>…</name></set>; o Kodi agrupa os filmes por esse **nome**, então duas grafias formam dois conjuntos. O Jellyfin também lê o ID da coleção no TMDB (<set tmdbcolid="…">). O movie.xml guarda a mesma coleção (TMDbCollectionId, CollectionName); o MediaClinic lê e grava os dois arquivos.

## A coluna Coleção e a vista agrupada
- A coluna **Coleção** (oculta por padrão, Ferramentas → Escolher colunas…) mostra o nome; a caixa Filtro a encontra.
- **Agrupar por coleção** (ao lado dos botões de ordenação, ou Configurações → NFO / XML → Coleções; desligado por padrão) mostra cada coleção como uma linha — "Harry Potter Collection (8)", o intervalo de anos, a pior cor de saúde — com seus filmes abaixo dela. Filmes sem coleção ficam soltos, na sua ordem.
- Onde fica uma linha de coleção: numa coluna de texto (Nome do filme, Gêneros…) ela é ordenada pelo nome da coleção; em qualquer outra coluna ela fica onde está seu primeiro filme.
- Um clique seleciona uma linha de coleção; a seta ▸, um duplo clique ou [[+]] / [[-]] a abrem ou fecham; coleções abertas continuam abertas enquanto o app roda. O **Todas as ações ▾** do painel da coleção mostra o menu da linha.
- Selecionar uma linha de coleção significa seus filmes para qualquer ação ("8 filmes selecionados"); [[Ctrl+A]] seleciona todos os filmes, também dentro de coleções fechadas.
- Clique direito numa linha de coleção: **Expandir / Recolher**, **Selecionar seus filmes**, **Corrigir coleção…**, **Renomear / juntar coleção…** (escolha uma coleção em uso para se juntar a ela: seus filmes recebem o nome e o ID do TMDB dela), **Criar pasta da coleção…**, **Imagens da coleção…**, **Abrir a pasta da coleção**, **Abrir a coleção no TMDB** (**Procurar a coleção no TMDB** quando o ID da coleção no TMDB não é conhecido), **Verificar coleção online**, **Expandir todas / Recolher todas**. O painel mostra a coleção: seu pôster (da pasta da coleção), ID do TMDB, anos, pasta, imagens, sinopse, seus filmes e as correções, com **Imagens…**, **Abrir pôster**, **Abrir fanart**, **Abrir pasta** e **TMDB** (a página da coleção com seus filmes, ou uma busca no TMDB pelo nome).
- Uma coleção, um nome: o Kodi mostra um conjunto por nome, então uma coleção do TMDB recebe UM nome para todos os seus filmes — em inglês, a menos que MAIS DA METADE dos seus filmes tenha o título local em um mesmo outro idioma (NFO <title>; XML <LocalTitle> quando o NFO não tem) — então nesse idioma. **Configurações → NFO / XML → Coleções → Idioma do nome da coleção** pode fixar um idioma para todas as coleções (o nome do TMDB nele, senão em inglês). Um título que o app não consegue associar a um título do TMDB conta como inglês. O idioma da biblioteca nunca é usado para o nome; quando o TMDB ainda não deu o nome em inglês, o nome nos seus NFOs é mantido e **Verificar coleções online** o busca. Quando NFO <title> e XML <LocalTitle> diferem, o filme mostra **Título diferente** e sua correção pergunta qual título manter. O aviso, **Corrigir coleção…** e o Reparo automático usam o mesmo nome, e **Corrigir coleção…** o grava em todos os filmes da coleção (a prévia os lista). Quando sua própria coleção está escrita de dois jeitos, a correção grava o nome que a maioria dos seus filmes usa. Depois de qualquer alteração a tabela é verificada de novo, então um aviso corrigido desaparece.

## Verificar coleções online
**Ferramentas → Verificar coleções online — Todos os filmes…** (ou Clique direito → Metadados → Coleção ▸ → **Verificar coleção online**) pergunta ao TMDB a que coleção cada filme pertence — um pedido por filme, dois por coleção, de novo só depois de 30 dias. **Verificar IDs do IMDb/TMDB** guarda os mesmos dados sem custo extra. Filmes sem ID do TMDB, ou cujo ID o Verificar IDs marcou, são pulados e contados. Scans e Recalcular a saúde nunca acessam a internet.

## As regras de coleção
Três regras em Configurações → Regras de saúde, ligadas no perfil Rigoroso (desligadas em Fácil e Médio), todas avisos:
- **Coleção faltando ou diferente**: o TMDB lista uma coleção que o NFO não tem, o NFO cita outra, ou uma coleção está escrita de dois jeitos na sua biblioteca ("written as X here and as Y in 3 other movies — Kodi shows two sets").
- **Imagens da coleção**: falta a pasta da coleção, seu pôster ou seu fanart (só enquanto houver uma pasta de coleções definida).
Suas próprias coleções ("Disney", "Oscar winners") nunca recebem aviso e nunca são removidas. Um nome sem ID do TMDB que não corresponde a nenhum nome do TMDB conta como seu, mesmo quando o TMDB lista o filme numa coleção; só **Corrigir coleção…** nesse filme, pedido por você, o substitui. Um filme que não foi verificado online não recebe aviso de "faltando / diferente do TMDB" (sua dica diz isso); uma coleção escrita de dois jeitos e um movie.xml diferente do NFO são encontrados por qualquer scan.

## Corrigir coleções
Clique direito → Metadados → **Coleção ▸**:
- **Corrigir coleção…** grava a coleção que o TMDB lista, com o nome único da coleção (veja "Uma coleção, um nome" acima), com sua sinopse quando o NFO não tem uma. Vários filmes: primeiro uma prévia. Também **Ferramentas → Corrigir coleções — Todos os filmes…** e a etapa do Reparo automático.
- **Definir coleção…** coloca os filmes selecionados numa coleção: uma em uso, um nome seu, ou uma coleção do TMDB encontrada com **Procurar no TMDB** (o ID e o nome no TMDB são gravados). Com a caixa marcada, ele depois cria a pasta da coleção e abre **Imagens da coleção…**. **Remover da coleção…** (pergunta antes) é a única ação que remove um <set>: ela diz que os filmes estão **fora de qualquer coleção**. O MediaClinic lembra disso (no_collection.json), então a coleção do TMDB não é mais sugerida para eles enquanto o NFO não tiver <set>; isso também serve para um filme que o TMDB coloca numa coleção que você não quer. **Definir coleção…** coloca um filme numa coleção de novo.
- Uma coleção que o TMDB não tem mais: quando um NFO liga uma coleção do TMDB (tmdbcolid) que o TMDB não lista mais para o filme, ou que não existe mais, **Verificar coleções online** dá o aviso "Collection: '…' no longer exists on TMDB" (ou "is not listed by TMDB for this movie"); **Corrigir** executa **Remover da coleção…**.
- **Atualizar** lê o NFO de novo: um filme cujo <set> você alterou vai para a nova coleção na vista agrupada. movie.xml: toda ação de coleção grava a mesma coleção no movie.xml (TMDbCollectionId e CollectionNumber = o ID da coleção no TMDB, ou 0 para nenhuma; CollectionName); Remover da coleção… põe os IDs em 0 e remove o nome. Um bloco <set> no estilo NFO dentro do movie.xml não pertence a ele e é removido. Quando o movie.xml e o NFO indicam coleções diferentes, o aviso "Collection: movie.xml says …" é corrigido por **Sincronizar coleção (NFO ↔ movie.xml)…** (a coleção do NFO vai para o movie.xml; um NFO sem coleção recebe a do movie.xml). <JSONDump> nunca é alterado.
Cada NFO recebe backup antes; **Histórico de backups / Desfazer** o restaura. Todos os outros bytes do arquivo ficam como estavam.

## A pasta da coleção (imagens da coleção)
O Kodi lê as imagens das coleções de UMA pasta que você escolhe no Kodi: Settings → Media → Videos → **Movie set information folder**. Defina a mesma pasta em **Bibliotecas…** → **Pasta de coleções** (Configurações → NFO / XML → Coleções a mostra; marcar **Agrupar por coleção** sem ela pede uma) (o mesmo compartilhamento, ex.: \\\\NAS\\Movies\\Sets ou Z:\\Sets).
- Cada coleção tem uma pasta com o nome da coleção, com / \\ ? : * " < > | escritos como _ (a regra do Kodi), contendo poster.jpg e fanart.jpg.
- **Criar pasta da coleção…** (clique direito, uma linha de coleção, ou **Ferramentas → Criar pastas de coleção — Todas…**) mostra uma prévia, cria a pasta e baixa do TMDB o pôster (primeiro no idioma da biblioteca) e o fanart. Um arquivo existente nunca é substituído. Uma chave de API do TMDB ausente, ou uma coleção sem pôster ou fanart no TMDB, aparece no resultado. Suas próprias coleções recebem a pasta: escolha as imagens com **Imagens da coleção…**. Desfazer remove o que a execução criou.
- **Imagens da coleção…** (clique direito num filme ou numa linha de coleção, o **Imagens…** do painel, ou **Corrigir** em "Collection artwork: … missing" para uma coleção) mostra os pôsteres e as imagens de fanart da coleção do TMDB, ou de **Os filmes desta coleção** (o pôster / fanart de cada um). Sem uma coleção do TMDB conhecida, **Procurar no TMDB** encontra uma pelo nome. Os pôsteres vêm 12 por página (4 por linha) e as imagens de fanart 9 por página (3 por linha): **Próxima ›** e **‹ Anterior** mostram as outras páginas, e uma imagem escolhida continua escolhida. A janela mantém o tamanho que você der a ela. Clique num pôster e numa imagem de fanart e depois em **Salvar na pasta**: a pasta é criada quando falta; uma imagem existente só é substituída depois de um backup, então o Histórico de backups pode desfazer a troca.
- Uma pasta que difere só em maiúsculas/minúsculas é encontrada (Windows, SMB); uma que difere em acentos não é a mesma pasta para o Kodi, e o aviso a cita.
- Quando uma coleção recebe um novo nome (**Corrigir coleção…**, **Definir coleção…**, **Renomear / juntar coleção…**, Reparo automático), a pasta vai junto: os arquivos da pasta antiga vão para a pasta do novo nome, e a pasta antiga vazia é removida. Quando as duas pastas têm um pôster (ou fanart), a imagem da pasta antiga é mantida e a outra vai para replaced\\ dentro da pasta — nada é excluído. A pasta fica onde está enquanto outro filme ainda usar o nome antigo. Histórico de backups / Desfazer restaura tudo.
- Uma pasta deixada com outro nome do TMDB da coleção (de antes) mostra **Collection folder: images left in '…'**; sua correção **Mover para a pasta da coleção** move os arquivos do mesmo jeito.
"""

TAB_09 = """
# Backups e desfazer

## Backups automáticos
Antes de o app alterar um arquivo .nfo, .xml ou de imagem, ele copia o original para backup\\backup_<Movie>_<date>_<time>\\ em %APPDATA%\\MediaMetadataClinic (junto com as configurações, então uma atualização os mantém). Uma execução (um lote, ou uma ação em um filme) é uma pasta de backup com um manifest.json (de onde veio cada arquivo, qual ação o criou). Toda gravação de NFO / XML é atômica: uma gravação que falha nunca deixa um arquivo pela metade, e a codificação, o BOM e as quebras de linha do arquivo são mantidos.
> Se não for possível fazer o backup, a alteração não acontece — o filme é informado como falho.

## Histórico de backups / Desfazer
**Histórico de backups / Desfazer…** (no cabeçalho e em Ferramentas) lista as execuções, das mais novas para as mais antigas. **Restaurar esta execução** devolve os arquivos:
- seus arquivos atuais recebem backup antes, então um desfazer pode ser desfeito;
- arquivos alterados depois da execução são listados e podem ser pulados;
- um NFO renomeado recebe o nome antigo de volta, e arquivos que uma execução criou (imagens da coleção) são removidos;
- as linhas são atualizadas.
Execuções removidas pela limpeza por tamanho continuam na lista como "removido pela limpeza de tamanho".

## Limite de tamanho
Configurações → Backup: o tamanho máximo da pasta de backup e "Excluir os backups mais antigos automaticamente" (ligado por padrão). Execuções desta sessão e dos últimos 14 dias nunca são excluídas automaticamente; a limpeza é registrada num log. Uma execução maior que o limite é avisada antes de começar. **Excluir todas as pastas de backup** esvazia a pasta.
"""

TAB_10 = """
# Servidores de mídia

## Kodi
O MediaClinic lê todos os nomes que o Kodi usa e mostra o arquivo que o Kodi escolheria, na ordem do Kodi:
| Pôster | <video>-poster.jpg/.png, poster.jpg/.png, <video>.tbn, movie.tbn, <pilha>-poster.jpg (filme em várias partes: Filme-poster.jpg para Filme-CD1.mkv)
| Fanart | <video>-fanart.jpg/.png, fanart.jpg/.png, <pilha>-fanart.jpg
| NFO | movie.nfo, <video>.nfo, <pilha>.nfo para um filme em várias partes (Filme.nfo para Filme-CD1.mkv + Filme-CD2.mkv; o Jellyfin lê o movie.nfo), e o único NFO da pasta, com qualquer nome, quando ele contém <movie> (um .nfo de informação do release é ignorado)
| Extra fanart | fanart1.jpg…, <video>-fanart1.jpg… (a pasta extrafanart é para o Jellyfin e o Emby)
<video> é o nome do arquivo de vídeo sem a extensão. As dicas dizem qual arquivo foi encontrado. Buscar pôster/pasta, Buscar fanart e Copiar pôster → pasta gravam no estilo que a pasta já usa: uma pasta do Kodi recebe <video>-poster.jpg. Copiar pôster → pasta também cria um folder.jpg numa pasta que não tem. Novas imagens de fundo seguem a mesma regra.
- **Renomear NFO para o Kodi…**: o Kodi lê "<video>.nfo" ou "movie.nfo", não um NFO com o nome da pasta (exceto quando é o único NFO). Ele oferece os dois nomes (o recomendado já selecionado); **Ferramentas → Renomear NFOs para o Kodi — Todos os filmes com NFO com o nome da pasta…** mostra uma prévia. Um nome que já existe nunca é sobrescrito; Desfazer devolve o nome antigo.
- Pastas de DVD e Blu-ray: uma estrutura VIDEO_TS ou BDMV é o filme; VIDEO_TS-poster.jpg, VIDEO_TS.nfo, index-poster.jpg e index.nfo também são lidos. O FFprobe e os quadros usam o maior arquivo .VOB / .m2ts.
- Coleções: a movie set information folder do Kodi — aba Coleções.

## Jellyfin, Emby e Plex
Os nomes que os outros servidores leem também são encontrados, depois dos do Kodi:
| Pôster | <video>.jpg, cover, default, movie, <video>-cover…
| Fanart | backdrop, background, art
| Imagens de fundo extras | backdrop-1, fanart-1, background-1, art-1
| Imagens | .jpg, .png, .jpeg, .webp, .gif, .bmp
- As dicas de pôster, pasta e fanart dizem quais servidores leem o arquivo encontrado. folder.jpg sozinho conta como pôster (Plex, Jellyfin, Emby e Infuse o usam; o Kodi não).
- NFO: o Plex não lê NFO; o Kodi lê movie.nfo primeiro quando "Movies are in separate folders" está ligado. Dois NFOs que os servidores leem (ex.: movie.nfo e <video>.nfo) são um aviso: exclua o que você não precisa. mymovies.xml aparece na dica do XML: nenhum servidor atual o lê.
- Outros vídeos não são "Vários arquivos de vídeo na mesma pasta": trailers (-trailer), amostras, extras (-featurette, -deleted …), as partes de um conjunto (cd1, part2) e versões ("Movie - 1080p"). A dica de Vídeo os lista.
"""

TAB_11 = """
# Configurações

**Configurações ▾** no cabeçalho abre **Todas as configurações…** ou uma das abas; [[Ctrl+S]] abre a janela Configurações e [[F10]] o menu Configurações ▾. **Salvar e aplicar** grava o settings.json; um campo que não é válido é indicado e nada é salvo. Mudanças nas regras de saúde e nos tamanhos de imagem valem na hora; mudanças em Idioma, Gêneros ou nas tags NFO / XML oferecem um scan de atualização.
| Editor e FFmpeg | editor de texto, pasta do FFmpeg (**Testar FFmpeg**; encontrada sozinha quando está no PATH ou numa pasta de instalação comum), número de quadros para imagens de fundo, scan em paralelo (workers; processos do FFprobe), scraper opcional, "Lembrar os resultados do FFprobe" (cada vídeo é analisado uma vez; um vídeo alterado é analisado de novo)
| Chaves de API | chaves do TMDB, OMDb e fanart.tv com botões **Validar** e links para obtê-las; as chaves nunca são gravadas no log
| Navegador | o navegador para links da web
| Idioma | o código ISO 639-1 da coluna Idioma OK? (padrão PT)
| Melhorias | as verificações do relatório de Melhorias e os tamanhos máximos de NFO / XML
| Tamanhos de imagem | nível mínimo de qualidade (o mesmo valor de Regras de saúde), aceitação de 3:4 e 3:2, tamanhos mínimos de arquivo
| Notas | os padrões das caixas de seleção de Sincronizar notas
| Gêneros | a lista padrão de gêneros, um por linha
| NFO / XML | os pares de tags da verificação de melhorias; **Coleções**: a pasta das coleções (mostrada aqui, definida em **Bibliotecas…**) e **Agrupar a tabela de filmes por coleção**
| Interface | **Idioma da interface** (English, Português (Brasil), Español ou Igual ao Windows; **Reiniciar agora** reinicia nele), cores alternadas nas linhas, dicas nos cabeçalhos, modo compacto, a linha Repetir, a janela de pastas ignoradas depois de um scan, barras de título escuras, "Procurar atualizações ao abrir"
| Regras de saúde | **Perfil de saúde** (Fácil / Médio / Rigoroso define todas as regras de uma vez; Personalizado depois das suas próprias alterações; um usuário novo começa com Rigoroso, e escolher um perfil depois das suas alterações pergunta antes), **Modo de saúde** (qual programa reproduz seus filmes: o NFO, NFO + movie.xml, ou só movie.xml; mudá-lo oferece um novo scan); as regras em quatro seções — **Regras gerais**, **Regras do NFO**, **Regras do movie.xml** e **Comparações NFO ↔ movie.xml** — cada regra com sua caixa, limite e nível (erro / aviso). As seções que o modo de saúde não usa continuam visíveis, mas em cinza, e não podem ser alteradas; suas configurações são mantidas para quando você voltar. **Restaurar padrões**
| Backup | o limite de tamanho, exclusão automática dos backups mais antigos, **Excluir todas as pastas de backup**
"""

TAB_12 = """
# Atalhos

## Teclado
| [[F1]], [[Ctrl+H]] | Ajuda
| [[F5]] | Full Scan
| [[Esc]] | cancelar um scan; limpar a caixa Filtro; fechar uma janela (Configurações pergunta antes se você alterou algo)
| [[Ctrl+F]] | ir para a caixa Filtro
| [[Ctrl+L]] | Limpar tudo…
| [[Ctrl+S]] | Configurações (todas as abas)
| [[F10]] | o menu Configurações ▾
| [[Ctrl+B]] | ocultar / mostrar o painel do filme selecionado
| [[Ctrl+O]] | abrir a pasta do filme selecionado
| [[Ctrl+E]] | abrir o .nfo do filme selecionado (a barra de status avisa quando não há)
| [[Ctrl+R]] | Atualizar o(s) filme(s) selecionado(s) (sem FFprobe)
| [[Ctrl+Shift+R]] | Atualizar o(s) filme(s) selecionado(s) (com FFprobe)
| [[Ctrl+I]] | Atualizar ícones — Todos os filmes
| [[Ctrl+Shift+E]] | Exportar lista de filmes…
| [[Ctrl+1]] … [[Ctrl+9]] | predefinições de ordenação 1 a 9
| [[Alt+S]], [[Alt+T]], [[Alt+H]] | os menus Configurações, Ferramentas e Ajuda
Os atalhos da tabela de filmes funcionam enquanto a parte Filmes é mostrada.

## Seleção e movimento
| A–Z, 0–9 | pular para o próximo filme com essa letra (repita para percorrer)
| [[PageUp]], [[PageDown]] | uma página; [[Home]] / [[End]]: primeira / última linha
| [[Shift+Up]], [[Shift+Down]] | aumentar ou reduzir a seleção
| [[Shift+PageUp]], [[Shift+PageDown]] | aumentar uma página
| [[Shift+Home]], [[Shift+End]] | aumentar até a primeira / última linha
| [[Ctrl+A]] | selecionar todos os filmes mostrados (na caixa Filtro: o texto)
| [[+]], [[-]] | abrir / fechar uma linha de coleção (vista agrupada)
| Duplo clique | a ação da coluna (aba Saúde e correção de problemas)
| Clique direito, [[Shift+F10]], tecla Menu | o menu do(s) filme(s) selecionado(s)
Com mais de um filme selecionado, a barra de status mostra "N selecionados".
"""

TAB_13 = """
# Solução de problemas

## Perguntas comuns
### A coluna Áudio está vazia
Ligue o FFprobe e execute Atualizar (com FFprobe).
### Um motivo de saúde não vale mais
Ferramentas → Recalcular a saúde (sem novo scan) — também feito a cada abertura.
### Fonte mostra ✕ embora o filme tenha um ID
Algumas tags estão vazias (ex.: <TMDB></TMDB>) enquanto outras têm o ID; Normalizar fontes as preenche.
### A extração de imagens de fundo não gera arquivos
Confira o FFmpeg em Configurações → Editor e FFmpeg (**Testar FFmpeg**) e aumente **Tempo limite por quadro** na janela Extrair imagem(ns) de fundo.
### O Excel abre o CSV numa coluna só
Exporte com "CSV — separado por ponto e vírgula" ou como .xlsx.
### As coleções não mostram aviso
Execute primeiro **Ferramentas → Verificar coleções online — Todos os filmes…** (as regras precisam dos dados de coleção do TMDB); a regra de imagens da coleção precisa da pasta de coleções (Bibliotecas…).

## Quando o TMDB ou o OMDb não respondem
O IMDb nunca é consultado diretamente: as notas do IMDb vêm pelo OMDb, os IDs do IMDb pelo TMDB. A mensagem indica a causa e o que fazer.
- TMDB "pedidos demais": espere cerca de um minuto.
- Limite diário do OMDb (1.000 pedidos com uma chave gratuita): tente de novo em algumas horas; o TMDB continua funcionando.
- Chave de API recusada: Configurações → Chaves de API → Validar. Sem conexão: verifique a internet e tente de novo.
- Num lote a mensagem vem uma vez, com "Pausar esta execução", "Continuar com …" (a outra fonte) e "Cancelar". Um serviço em pausa mostra "⚠ … em pausa" na barra de status (clique para ver o motivo ou encerrar a pausa); a próxima ação pergunta "Tentar mesmo assim?".
- Um erro de rede interrompe uma execução e mantém o que foi feito; um arquivo que não pode ser gravado (bloqueado, somente leitura) faz falhar só aquele filme; um arquivo somente leitura é nomeado e o app oferece tirar o somente leitura (um filme: depois tenta de novo; um lote: uma pergunta, depois execute de novo).

## Logs
**Ajuda → Abrir a pasta de logs** abre logs\\ com o app.log selecionado. Todo erro inesperado é gravado ali (chaves de API nunca): anexe-o a um relatório de bug.

## Atualizações
**Ajuda → Procurar atualizações…** (ou o botão em Sobre) pergunta ao GitHub qual é a versão mais recente; nada mais é enviado. Uma nova versão pode ser aberta no GitHub ou pulada. O programa para Windows também pode baixá-la e instalá-la (uma versão para Linux só abre a página de download): o pacote é conferido pelo SHA-256 e descompactado ao lado da versão atual, que nunca é alterada. Suas configurações, resultados e backups são mantidos (ficam em %APPDATA%). Configurações → Interface → "Procurar atualizações ao abrir" (desligado por padrão) verifica uma vez por dia e só mostra um link na barra de status.

## Uma janela por vez
O MediaClinic roda uma vez só: abri-lo de novo traz a janela aberta para a frente.
"""

# (menu / tab label, text) in the order of help_text.HELP_TABS
HELP_TABS = [
    ('🚀  Primeiros passos', TAB_01),
    ('📊  A janela e a tabela', TAB_02),
    ('🔄  Scans e bibliotecas', TAB_03),
    ('🩺  Saúde e correção de problemas', TAB_04),
    ('🖼  Imagens', TAB_05),
    ('⭐  Notas, gêneros e IDs', TAB_06),
    ('🛠  Ferramentas e Reparo automático', TAB_07),
    ('🗂  Coleções', TAB_08),
    ('🕘  Backups e desfazer', TAB_09),
    ('📺  Servidores de mídia', TAB_10),
    ('⚙️  Configurações', TAB_11),
    ('⌨  Atalhos', TAB_12),
    ('🧰  Solução de problemas', TAB_13),
]
ABOUT_LABEL = 'ℹ️  Sobre'
