# Knowledge Workspace

Beta por convite para quem mantém a documentação do próprio software: escreva ou importe respostas, escolha os artigos prontos, revise e publique uma central com busca e páginas individuais. Um responsável edita; leitores abrem os links sem conta. A utilidade para outras pessoas, a redução de chamados e a disposição a pagar ainda precisam ser demonstradas. Não há contratação ou cobrança abertas.

**[Conhecer o Workspace](https://joaodeluca.github.io/product-knowledge-operations/)** · **[Roteiro da primeira central](https://joaodeluca.github.io/product-knowledge-operations/beta.html)** · **[Entrar com acesso já liberado](https://joaodeluca.github.io/product-knowledge-operations/browser/)**

## Acesso à beta e primeiro uso — web 0.15

O acesso individual e a recuperação de senha são administrados pelo responsável pela beta no canal privado já combinado. Não há cadastro público, solicitação automática de convite ou recuperação automática. Nunca envie senha ou documentos privados em issues públicas.

Prepare três a cinco orientações próprias e autorizadas para publicação. Crie um projeto → importe Markdown/texto ou escreva no editor visual → **Incluir na central** nos artigos desejados → **Revisar selecionados** → **Publicar central**, conferir a prévia e confirmar → **Copiar link**. Artigos novos são rascunhos; só os selecionados e revisados entram no link. O painel **Próximo passo** acompanha o estado salvo, sem revisar ou publicar por você.

Abra o link sem login, teste busca e artigo individual e confira os rascunhos excluídos. Depois, edite uma resposta, aguarde o salvamento, revise e use **Atualizar publicação**: o endereço continua o mesmo. Salvar um rascunho não altera o que os leitores veem. Categorias, logo e cores são opcionais para o primeiro uso.

O [roteiro público](https://joaodeluca.github.io/product-knowledge-operations/beta.html) inclui preparação, instruções, obstáculos e retorno. A [ficha local](site/beta-notes.txt) distingue conclusão com/sem ajuda, esforço de preparação, uso real e retorno apenas para testar. Não há envio automático, analytics ou contato externo. Uma meta de 15 minutos é uma hipótese de avaliação, não promessa de desempenho ou resultado já observado.

## Capacidades e limites atuais

- Editor visual com títulos, listas, citações, código, links e imagens; importação de Markdown/texto UTF-8. Tiptap é distribuído localmente, com versões e licenças registradas, sem CDN em tempo de uso.
- Projetos privados na conta, login persistente e salvamento automático com confirmação. Use **Sair da conta** em dispositivos compartilhados. Sem conexão/conflito, preserve a aba ou baixe o rascunho antes de reabrir; não há sincronização offline ou colaboração simultânea.
- Central com categorias, marca, busca e links estáveis de artigos. Quem tiver o link pode ler; não é compartilhamento privado. **Retirar do ar** impede novas leituras, mas não recolhe cópias anteriores. Não há domínio personalizado ou contas de equipe.
- 20 projetos/8 MiB por conta; 50 artigos por projeto. Importação até 32 arquivos/512 KiB por lote, 128 KiB por arquivo. Imagens/anexos referenciados na importação não são carregados. Imagens inseridas no editor são reduzidas e integram o limite de 128 KiB por artigo.
- Até 20 versões hospedadas por central, 2 MiB por versão e 8 MiB de histórico hospedado por conta. A beta não oferece disponibilidade contínua ou suporte com prazo garantido.
- **Backup privado** JSON guarda originais, rascunhos, notas, histórico e downloads HTML. Não inclui links ou versões hospedadas; a recuperação cria novos projetos e exige nova publicação. Guarde-o em local privado. Não é compatível com o ZIP da edição Python.
- Revisão é declaração do operador, não certificação independente. A edição vence a revisão daquela versão. Duas abas não podem sobrescrever silenciosamente a mesma versão.

## Biblioteca de exemplos preservada

A [biblioteca pública](https://joaodeluca.github.io/product-knowledge-operations/library.html) contém três guias próprios; não são casos de clientes. O ensaio Excalidraw de 04/10 permanece parcial; o recorte distinto de 05/10 inclui arquivos originais e recuperação observada. No OpenRefine, o CSV após desfazer perdeu espaços externos e o aceite integral original falhou, apesar da recuperação por API. O guia Renovate cobre validação delimitada, sem implantação, autenticação ou manutenção do bot. [Fontes e limites dos guias](docs/README.md).

## Executar o Knowledge Workspace

[Conhecer o aplicativo e começar](https://joaodeluca.github.io/product-knowledge-operations/workspace.html). A edição local abaixo tem fluxo próprio; o roteiro principal da beta é para a edição web.

A [prévia independente do aplicativo](workspace/README.md) permite criar um projeto vazio, importar documentos Markdown próprios em lote com prévia e sem sobrescrita, registrar fontes, revisar artigos e exportar uma central HTML com busca local. Os originais são preservados; a importação não aprova os artigos.

**[Baixar Knowledge Workspace 0.5.0](https://github.com/joaodeluca/product-knowledge-operations/releases/tag/workspace-v0.5.0)** — inclui importação e atualização por arquivo, comparação antes/depois e histórico. O backup privado recupera fontes, rascunhos, revisões e publicações em uma pasta nova. Mudanças nas fontes vencem as revisões dependentes. A exportação do leitor exclui fontes, evidências e notas internas; o operador deve conferir o texto público antes de compartilhar.

Funciona localmente com Python, sem Codex, chave de IA ou conta. É uma nova forma experimental de entregar a capacidade editorial deste projeto, ainda sem clientes, receita ou benefício econômico demonstrado. Não é serviço hospedado, execução autônoma do produto ou substituto comprovado de uma operação completa. A biblioteca e seus resultados históricos permanecem intactos. [Instruções, requisitos e limites](workspace/README.md).

## Descrever um escopo público

[Abrir avaliação de procedimento](https://github.com/joaodeluca/product-knowledge-operations/issues/new?template=public-product-scope.yml). Somente URL pública, procedimento e lacuna. O conteúdo e a autoria GitHub serão públicos. Não envie contatos pessoais, dados de clientes, arquivos privados, segredos ou acesso. Não é contratação ou promessa de entrega. O formulário exige sessão GitHub; nenhuma conta é criada por este projeto.

O operador avalia necessidade, entradas disponíveis, possibilidade de reproduzir o procedimento e trabalho residual do responsável. Um pedido aceito para análise não é cliente pagante, autorização de publicação ou aceite de entrega. Nenhuma resposta automática ou envio comercial está instalado.

## Conteúdo

- `site/workspace.html`: apresentação atual, entregue também em `index.html`; `dist/index.html` histórico preservado.
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

### Workspace web 0.13 — publicar só o que está pronto

Cada artigo pode ficar como rascunho ou entrar na próxima publicação. Artigos novos começam como rascunho. Inclua os desejados, confira apenas esses artigos e abra a prévia antes de publicar. A lista distingue seleção para a próxima versão e artigos atualmente no ar. Alterar a seleção não muda o link até confirmar Atualizar publicação; para retirar toda a central, use Retirar do ar. Categorias vazias e aliases de rascunhos ficam fora da versão pública. A seleção acompanha o backup e o salvamento na conta.

### Workspace web 0.14 — páginas de artigos e navegação

A central hospedada abre em uma página inicial por categorias. Cada artigo tem endereço próprio, botão **Copiar link do artigo**, caminho de volta à categoria e navegação anterior/próximo. A busca considera título, texto e categoria, incluindo artigos do editor visual. Links antigos com âncora continuam funcionando. Renomear ou reorganizar um artigo preserva seu endereço; retirar o artigo da publicação torna sua página indisponível em novas aberturas. No Workspace, os artigos no ar oferecem **Abrir artigo** e **Copiar link do artigo**. Rascunhos permanecem privados. Os links usam parâmetros no endereço e funcionam ao recarregar no GitHub Pages, sem hospedagem adicional.
