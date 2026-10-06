# Entregar dados e conservar um projeto no OpenRefine

Esta é uma amostra original de uma operação de documentação de produto. Usamos OpenRefine 3.10.0 e 48 registros fictícios. Não é documentação oficial, execução para cliente ou prova de vantagem comercial.

## Escolha o que precisa entregar

| Necessidade | Arquivo | O que verificar |
|---|---|---|
| Consumir apenas a categoria A | filtered.csv | 16 registros, todos A |
| Consumir todos os dados tratados | full.csv | 48 registros, IDs como 00001 |
| Continuar o trabalho e desfazer uma transformação | handoff.openrefine.tar.gz | Importar como projeto, não como CSV |


Arquivos desta amostra: [fonte](../../dist/openrefine/files/source.csv), [categoria A](../../dist/openrefine/files/filtered.csv), [todos tratados](../../dist/openrefine/files/full.csv), [projeto para importar](../../dist/openrefine/files/handoff.openrefine.tar.gz), [comparador específico](../../dist/openrefine/files/check_exports.py).

CSV não conserva o histórico. O arquivo de projeto conserva estados anteriores: trate também dados antigos como informação que será compartilhada. Nesta amostra todos são fictícios. O arquivo de projeto não promete conservar filtros ou a visualização ativa.

## Importar, tratar e exportar pela interface

1. Abra uma instalação própria do OpenRefine 3.10.0. Em Create project → This Computer, escolha source.csv. Se o seletor de arquivo não funcionar, abra o CSV como texto e use a entrada Clipboard. Não copie dados de outra pessoa.
2. Na prévia, escolha vírgulas e cabeçalho de uma linha. Deixe desmarcadas a conversão automática para números e a remoção de espaços. Confira os IDs 00001 e 00002 antes de criar.
3. Crie o projeto. Sem filtros ativos, abra a coluna descricao → Edit cells → Transform e digite value.trim(). Espere a prévia mostrar a descrição sem espaços externos antes de confirmar. Uma caixa com texto novo não prova que o produto aplicou esse texto.
4. Confira Undo / Redo: a descrição da operação deve indicar value.trim() e 48 células alteradas. Se indicar apenas value e zero células, pare: essa operação não removeu os espaços. Não refaça alterações em dados de cliente sem revisar o histórico.
5. Na coluna categoria, abra Facet → Text facet e selecione A. Confira 16 linhas e exporte CSV. Salve como filtered.csv.
6. Remova a seleção A. Confira 48 linhas e exporte novamente, como full.csv. Filtrar e exportar não apaga as demais linhas do projeto, mas muda o CSV recebido.
7. Em Export, escolha o arquivo completo de projeto (.tar.gz). Salve-o separadamente do CSV.

## Restaurar e verificar a recuperação

Em outra instalação ou workspace vazio, use Import project para o arquivo .tar.gz. Abra o projeto importado e confira 48 linhas. Exporte restored.csv sem filtros e confronte todas as células com full.csv. Em Undo / Redo, selecione o estado inicial de criação, antes das transformações. Nesta versão, a recuperação de espaços externos não pôde ser comprovada por CSV: no ensaio o estado inicial das células tinha os espaços, mas o CSV exportado os removeu. Portanto não use CSV como backup exato e não declare restauração fiel usando apenas esse formato. Confira as células pela API get-rows e mantenha o arquivo de projeto; o critério original de CSV idêntico falhou e permanece registrado.

Confira também IDs, acentos, aspas e células vazias. A rotina original check_exports.py compara esses quatro arquivos à fonte congelada; ela não prova utilidade econômica nem funciona como validador universal de outros produtos/dados.

## Reprodução técnica com API local

No ensaio registrado, importação textual e criação ocorreram pela interface. A transformação efetiva, os arquivos de exportação e a restauração foram executados pela API do próprio OpenRefine. O seletor de arquivos da sessão de controle não completou; não apresentamos esses passos como cliques verificados. Para reproduzir a parte técnica em um workspace vazio, use uma segunda instância que escute somente 127.0.0.1, em porta própria. Não exponha a instância à rede.

Obtenha o token em GET /command/core/get-csrf-token. Faça POST multipart em /command/core/import-project?csrf_token=TOKEN, campo project-file com o arquivo handoff.openrefine.tar.gz e project-name com um nome novo. O redirecionamento devolve o ID do projeto. Não use outro projeto já existente como destino.

1. Exporte via POST /command/core/export-rows/restored.csv?csrf_token=TOKEN, formulário project=ID, format=csv, options={"quoteAll":false} e engine={"mode":"row-based","facets":[]}.
2. Para desfazer, faça POST /command/core/undo-redo?project=ID&lastDoneID=0&csrf_token=TOKEN com engine igual. Uma resposta code=pending não conclui o desfazer. Nesse caso, consulte GET /command/core/get-processes?project=ID até processes ficar vazio (no máximo 30 segundos, intervalos de um segundo). Qualquer erro ou espera esgotada interrompe a reprodução. Depois consulte GET /command/core/get-history?project=ID e exija past vazio; um processo vazio sozinho não prova que o estado desejado foi atingido. Para code=ok, também confira o histórico.
3. Só então exporte undo.csv com o mesmo método e execute check_exports.py --source source.csv --filtered filtered.csv --full full.csv --restored restored.csv --undo undo.csv. Preserve falhas, não altere a fonte para aprovar. O resultado observado desta amostra foi reprovação em undo.csv por perda de espaços externos; filtered, full e restored passaram. O comparador não foi relaxado para aprovar.
4. Para conferir a recuperação do estado, consulte GET /command/core/get-rows?project=ID&start=0&limit=50&engine=JSON_ENCODED (engine sem filtros), compare cada valor v à fonte e exija 48 registros.
5. Nesta amostra, as 12 células nulas de observacao correspondem aos campos CSV vazios: um objeto de célula ausente ou sem valor nessa coluna pode ser comparado a string vazia, sem converter erros ou outros valores. Essa equivalência decorre das opções de importação observadas e não deve ser aplicada universalmente. Esse resultado separado não transforma a falha CSV em aprovação do plano inteiro.

## Referências e limites

[Instalação oficial](https://openrefine.org/docs/manual/installing), [execução e workspace](https://openrefine.org/docs/manual/running), [exportação](https://openrefine.org/docs/manual/exporting). Os nomes de comandos locais foram conferidos na distribuição oficial usada. Não há garantia de compatibilidade com versões diferentes.

Esta amostra não mede redução de chamados ou tempo frente ao manual oficial. Não inclui produto privado, publicação no CMS de cliente, suporte contínuo, compra ou aceite externo. O ensaio anterior com outro produto permanece parcial; este procedimento não o substitui retroativamente.

## Correção após execução independente

O primeiro guia exigia code=ok imediato para desfazer. Outro agente importou o arquivo e encontrou code=pending: parou sem declarar recuperação concluída. A instrução acima foi corrigida para acompanhar processos e confirmar o histórico. A revisão também encontrou nomes sem links de download; os cinco links reais foram acrescentados. Esses problemas foram observados nesta amostra, não atribuídos a um cliente ou a uma nova versão do fornecedor.

Uma segunda execução independente chegou ao estado inicial do histórico, mas encontrou perda de espaços no CSV. A inspeção das células separou restauração do projeto de serialização de saída. A ajuda foi atualizada para retirar a promessa de fidelidade por CSV; o critério original não foi modificado, e seu resultado segue reprovado. Não afirmamos falha geral do OpenRefine nem perda das células no backup.
