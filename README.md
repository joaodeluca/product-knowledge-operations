# Product Knowledge Operations

Operação de conhecimento para produtos de software, em validação: aprender procedimentos, preparar ajuda conferida, incorporar sob autorização e acompanhar mudanças. Contratação e cobrança ainda não estão abertas. Nenhum cliente, redução de dúvidas ou economia comprovados.

**[Abrir a biblioteca de ajuda](https://joaodeluca.github.io/product-knowledge-operations/library.html)** — três guias e arquivos próprios disponíveis por HTTPS, sem depender do Mac. A [leitura dos guias no GitHub](docs/README.md) permanece como alternativa.

Este repositório contém a apresentação e amostras editoriais originais e independentes. [Transferir e recuperar um projeto OpenRefine](docs/openrefine/TRANSFER.md) entrega fonte fictícia, CSVs, arquivo real de projeto e comparador específico. Importação inicial pela interface; transformação, exportação e recuperação pela API local. A conferência independente cobre recuperação por API em outro workspace. CSV após desfazer perdeu espaços externos: o aceite integral original falhou, mesmo com células recuperadas. Não cobre toda a produção inicial pela interface nem prova vantagem comercial.

O ensaio Excalidraw de 04/10 continua parcial: backup e restauração ficaram pendentes naquela amostra. Um recorte próprio distinto de 05/10 conserva cena editável, PNG e recuperação observada em sessão separada; o [novo guia](docs/excalidraw/SAVE-RESTORE.md) e seus quatro arquivos originais preservam essa distinção. Não há vínculo com o fornecedor.

[Validar a configuração correta do Renovate](docs/renovate/VALIDATION.md) responde a uma dúvida pública específica com exemplos próprios executados no validador oficial. Não inclui implantação, autenticação ou manutenção do bot.

## Abrir o Workspace no navegador

**[Abrir a edição web 0.9](https://joaodeluca.github.io/product-knowledge-operations/browser/)** — prévia sem instalação ou chave de IA, com conta privada e salvamento automático entre dispositivos. Crie um projeto, importe Markdown/texto próprio, edite com prévia, confira cada artigo e use **Publicar central → Copiar link**. O leitor abre sem login, com busca, sem baixar arquivos ou configurar hospedagem.

A publicação mostra o nome da central e o conteúdo dos artigos revisados, após prévia e confirmação. **Atualizar publicação** mantém o mesmo link; salvar rascunhos não muda o que os leitores veem. **Retirar do ar** bloqueia novas leituras; não apaga cópias já feitas. Quem tiver o link pode ler: não é compartilhamento privado, mesmo com a orientação para buscadores não indexarem. Originais, histórico e notas ficam privados. O backup JSON não inclui links nem versões hospedadas; projetos recuperados exigem nova publicação. Cada central aceita até 20 versões publicadas, 2 MiB por versão e 8 MiB de histórico hospedado por conta.

Os projetos são criados e salvos na sua conta Supabase. Entre uma vez: o login fica salvo neste navegador e a sessão é renovada quando necessário; a senha não é guardada pelo aplicativo. Use **Sair da conta** em um dispositivo compartilhado. Ao escrever, aguarde **Salvo na sua conta**: mudanças durante uma gravação são enfileiradas. Sem conexão ou em conflito, o texto permanece na aba com aviso e opção de baixar rascunho; não feche até resolver ou guardá-lo. Não há gravação silenciosa em um modo local.

Projetos locais antigos continuam preservados e podem ser copiados pela opção **Importar projetos antigos**, com confirmação. Faça backup JSON privado para guardar originais, histórico, notas e downloads HTML; a recuperação cria novos projetos sem substituir os existentes. O cadastro público está fechado. Não há sincronização offline, edição colaborativa simultânea ou compatibilidade com o backup ZIP Python. O plano Free pode pausar por inatividade.

Limites da prévia: 20 projetos/8 MiB no total, 50 artigos e 20 publicações por projeto. Markdown básico (títulos, listas, negrito, código e links HTTPS); sem imagens, anexos ou HTML ativo. Revisão é uma declaração do operador, não certificação independente. Edições vencem a revisão do artigo; publicações anteriores permanecem preservadas. Duas abas não podem sobrescrever silenciosamente a mesma versão.

O código estático está em `site/browser/`, sem bibliotecas externas. O modo conta usa Supabase Auth e funções privadas do banco; somente a chave pública publishable vai ao aplicativo. A interface confirma salvamentos após resposta do servidor e recusa versões desatualizadas. Revisão, busca e geração ocorrem no navegador. A edição local Python abaixo permanece disponível com suas capacidades próprias.

## Executar o Knowledge Workspace

[Conhecer o aplicativo e começar](https://joaodeluca.github.io/product-knowledge-operations/workspace.html). A biblioteca e a página inicial dão acesso ao produto; a visão geral guia importação, revisão individual, geração e download da central.

A [prévia independente do aplicativo](workspace/README.md) permite criar um projeto vazio, importar documentos Markdown próprios em lote com prévia e sem sobrescrita, registrar fontes, revisar artigos e exportar uma central HTML com busca local. Os originais são preservados; a importação não aprova os artigos.

**[Baixar Knowledge Workspace 0.5.0](https://github.com/joaodeluca/product-knowledge-operations/releases/tag/workspace-v0.5.0)** — inclui importação e atualização por arquivo, comparação antes/depois e histórico. O backup privado recupera fontes, rascunhos, revisões e publicações em uma pasta nova. Mudanças nas fontes vencem as revisões dependentes. A exportação do leitor exclui fontes, evidências e notas internas; o operador deve conferir o texto público antes de compartilhar.

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

O gerador mantém somente os três guias canônicos. Uma lista fixa adicional inclui a página original do aplicativo e sua chamada na biblioteca e na apresentação, preservando o dist histórico. Não é um CMS genérico.
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

### Web 0.10 — identidade visual com prévia

Abra um projeto → **Personalizar aparência** para editar nome, enviar logo PNG/JPEG/WebP e escolher cor principal/fundo do cabeçalho. A prévia acompanha a edição, com opção de largura de celular. **Salvar aparência** guarda na conta; **Atualizar publicação** confirma a versão pública no mesmo link. Cancelar mantém a aparência anterior. Projetos antigos continuam válidos. Logo normalizado, cores validadas, contraste automático do texto; sem hospedagem ou plano pago adicional.

### Web 0.11 — categorias e ordem de artigos

No projeto, use **Organizar artigos** para criar/renomear categorias, atribuir artigos e ordenar categorias/artigos com Subir/Descer. A prévia acompanha a organização, inclusive a marca escolhida. **Salvar organização** guarda na conta; a central pública só muda em **Atualizar publicação**, no mesmo link. Remover uma categoria mantém os artigos sem categoria. Categorias vazias não são publicadas; até 20 categorias de 80 caracteres. Organização não altera texto, histórico nem revisão dos artigos.

## Browser 0.12 — editor visual

Editar/Escrever artigo abre Tiptap com títulos, negrito, itálico, sublinhado, listas, citação, código, desfazer/refazer, links HTTPS e envio de imagens. Prévia usa o mesmo renderizador seguro da revisão e central. Imagens PNG/JPEG/WebP até4MiB são redimensionadas (máximo1200px) e recomprimidas para dataURL até48KiB, dentro do corpo versionado de128KiB. Ficam na conta/backup e só aparecem publicamente após revisão e confirmação. Remover imagem é reversível com Desfazer antes de sair do editor.

Documentos antigos continuam Markdown; ao editar o conteúdo visualmente, o corpo passa a um documento JSON com prefixo versionado. Abrir sem editar não migra nem altera a revisão. Original e histórico são preservados. Nenhuma migração SQL ou novo grant é necessário: os campos existentes continuam strings e as quotas/CAS continuam vigentes. O leitor aceita apenas nós e atributos permitidos; imagens externas/SVG/HTML ativo e links fora de HTTPS são recusados. Colar não importa imagens: use Imagem.

Editor baseado no [Tiptap](https://tiptap.dev/docs/editor/getting-started/install/vanilla-javascript), distribuído localmente sem CDN em tempo de uso. Fontes de integração em editor-src/vendor.mjs, versões fixas no package-lock.json e licenças em site/browser/editor-licenses.txt. Para reconstruir: npm ci; npm run build:editor. O build Pages usa o bundle previamente revisado. Testes: node --test scripts/tests/*.test.mjs.
