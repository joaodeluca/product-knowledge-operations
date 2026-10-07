# Product Knowledge Operations

Operação de conhecimento para produtos de software, em validação: aprender procedimentos, preparar ajuda conferida, incorporar sob autorização e acompanhar mudanças. Contratação e cobrança ainda não estão abertas. Nenhum cliente, redução de dúvidas ou economia comprovados.

**[Abrir a biblioteca de ajuda](https://joaodeluca.github.io/product-knowledge-operations/library.html)** — três guias e arquivos próprios disponíveis por HTTPS, sem depender do Mac. A [leitura dos guias no GitHub](docs/README.md) permanece como alternativa.

Este repositório contém a apresentação e amostras editoriais originais e independentes. [Transferir e recuperar um projeto OpenRefine](docs/openrefine/TRANSFER.md) entrega fonte fictícia, CSVs, arquivo real de projeto e comparador específico. Importação inicial pela interface; transformação, exportação e recuperação pela API local. A conferência independente cobre recuperação por API em outro workspace. CSV após desfazer perdeu espaços externos: o aceite integral original falhou, mesmo com células recuperadas. Não cobre toda a produção inicial pela interface nem prova vantagem comercial.

O ensaio Excalidraw de 04/10 continua parcial: backup e restauração ficaram pendentes naquela amostra. Um recorte próprio distinto de 05/10 conserva cena editável, PNG e recuperação observada em sessão separada; o [novo guia](docs/excalidraw/SAVE-RESTORE.md) e seus quatro arquivos originais preservam essa distinção. Não há vínculo com o fornecedor.

[Validar a configuração correta do Renovate](docs/renovate/VALIDATION.md) responde a uma dúvida pública específica com exemplos próprios executados no validador oficial. Não inclui implantação, autenticação ou manutenção do bot.

## Executar o Knowledge Workspace

A [prévia independente do aplicativo](workspace/README.md) permite criar um projeto vazio, importar documentos Markdown próprios em lote com prévia e sem sobrescrita, registrar fontes, revisar artigos e exportar uma central HTML com busca local. Os originais são preservados; a importação não aprova os artigos.

**[Baixar Knowledge Workspace 0.2.0](https://github.com/joaodeluca/product-knowledge-operations/releases/tag/workspace-v0.2.0)** — inclui três guias próprios de uso, que podem ser importados juntos. Mudanças nas fontes vencem as revisões dependentes. A exportação do leitor exclui fontes, evidências e notas internas; o operador deve conferir o texto público antes de compartilhar.

Funciona localmente com Python, sem Codex, chave de IA ou conta. É uma nova forma experimental de entregar a capacidade editorial deste projeto, ainda sem clientes, receita ou benefício econômico demonstrado. Não é serviço hospedado, execução autônoma do produto ou substituto comprovado de uma operação completa. A biblioteca e seus resultados históricos permanecem intactos. [Instruções, requisitos e limites](workspace/README.md).

## Descrever um escopo público

[Abrir avaliação de procedimento](https://github.com/joaodeluca/product-knowledge-operations/issues/new?template=public-product-scope.yml). Somente URL pública, procedimento e lacuna. O conteúdo e a autoria GitHub serão públicos. Não envie contatos pessoais, dados de clientes, arquivos privados, segredos ou acesso. Não é contratação ou promessa de entrega. O formulário exige sessão GitHub; nenhuma conta é criada por este projeto.

O operador avalia necessidade, entradas disponíveis, possibilidade de reproduzir o procedimento e trabalho residual do responsável. Um pedido aceito para análise não é cliente pagante, autorização de publicação ou aceite de entrega. Nenhuma resposta automática ou envio comercial está instalado.

## Conteúdo

- `dist/index.html`: apresentação, limites e preparação local de escopo.
- `dist/library.html`: biblioteca com busca e filtros locais para três procedimentos.
- `dist/excalidraw.html`: novo recorte próprio de 05/10 e arquivos originais.
- `dist/renovate.html`: leitura da decisão de validação já publicada, sem nova execução do fornecedor.
- `dist/sample.html`: ensaio anterior parcial, preservado.
- `dist/openrefine.html`: nova ajuda de transferência/recuperação, arquivos próprios reais e limites.
- `docs/openrefine/TRANSFER.md`: guia completo e correções após revisão.
- `.github/ISSUE_TEMPLATE/`: entrada voluntária de escopo público.

O formulário do site somente prepara uma página de revisão no GitHub. Não envia conteúdo automaticamente, não grava formulário, não usa API de IA nem coleta analytics. A biblioteca está hospedada no GitHub Pages. A execução inicial falhou antes de executar qualquer etapa por ausência de runner; essa falha permanece no histórico. Após a recuperação do serviço, a [execução 37474065025](https://github.com/joaodeluca/product-knowledge-operations/actions/runs/37474065025) implantou a revisão `0b854731dbe485ddd6c0ca66f6d1d7d5a21708b7`. O endereço externo e os 26 arquivos foram conferidos contra a entrega congelada dessa revisão. Publicações futuras exigem uma nova conferência da revisão efetivamente implantada. A entrega usa a apresentação e os arquivos próprios já selecionados de `dist/`, com os três leitores gerados a partir dos guias revisados em `docs/`. Nenhum banco, sessão, pacote operacional ou protocolo privado é enviado. Não é loja ou serviço comercial aberto.

Projeto pessoal de João de Luca. Sem recursos de outra empresa. Implementação estática original; não contém protocolo privado, dados de clientes ou credenciais. Imagens e conteúdo de amostra não devem ser apresentados como documentação oficial do Excalidraw.


## Uma fonte para o guia e a página de leitura

Os guias em `docs/` são a fonte de texto dos três leitores. O gerador original
`scripts/build_readers.py` produz uma nova pasta de entrega, sem alterar o
`dist/` histórico, executar os fornecedores ou acessar dados privados. A pasta
recebe os leitores, o índice de seções, os arquivos próprios selecionados e um
manifesto de fontes, referências e saídas. Uma mudança no guia, no estilo, nos
arquivos referenciados ou na saída invalida a conferência daquela entrega.

Use uma pasta nova fora deste checkout:

```sh
python3 scripts/build_readers.py --output /tmp/product-help-reviewed
python3 scripts/build_readers.py --output /tmp/product-help-reviewed --check
```

O gerador admite somente os três caminhos definidos, não um CMS genérico.
Recusa links locais ausentes ou fora do recorte, esquemas inseguros e saída já
existente. A conferência não aprova a verdade do texto ou certifica direitos:
a revisão editorial e os limites de cada ensaio continuam necessários.

A publicação de Pages é manual e exige o SHA completo da revisão conferida.
O workflow gera e confere novamente a entrega antes de enviar somente essa
pasta. Não há publicação automática em cada commit. A implantação inicial
falhou antes de executar qualquer etapa. Após a resolução do incidente de
Actions/Pages, uma execução delimitada da revisão conferida concluiu a
implantação; a biblioteca HTTPS, os arquivos e quatro downloads foram
verificados em 06/10/2026. A leitura nativa dos guias no GitHub permanece
disponível. Essa entrega não comprova audiência, operação de comprador,
aceite externo ou benefício econômico. Não foram criadas outra conta,
assinatura, agenda ou promessa comercial.
