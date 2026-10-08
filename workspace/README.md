# Knowledge Workspace · prévia 0.3.0

Uma central de ajuda que acompanha as fontes do produto. Registre conhecimento próprio, escreva artigos vinculados, confira o que mudou e exporte uma central de leitura. Quando uma fonte ou um procedimento muda, a revisão dos artigos dependentes vence; a publicação anterior permanece disponível.

Este é um aplicativo local para um operador. Não exige Codex, Node, chave de IA, conta, banco externo ou conexão à internet. Não gera artigos por IA, executa seu produto, valida a verdade do conteúdo ou hospeda a central. A revisão é declarada pelo operador e não é assinatura de identidade verificada.

## Iniciar em uma pasta nova

Requer Python 3.10+ e macOS ou Linux. Esta versão foi executada em macOS; Linux ainda não foi verificado. Windows não é suportado nesta versão. Não instale pacotes Python.

Extraia o ZIP da distribuição e, na pasta extraída, execute:

```sh
python3 serve.py --store "$HOME/KnowledgeWorkspace/meu-projeto" --open
```

O comando abre a interface no navegador padrão. Sem `--open`, a sessão fica no arquivo privado `session.json` dentro da pasta de dados escolhida: abra a URL desse arquivo. O servidor usa uma porta livre de `127.0.0.1`, aceita somente conexões locais e encerra com Ctrl+C. Para reabrir, execute o mesmo comando com a mesma pasta. A sessão muda; os projetos permanecem.

A pasta de dados deve estar vazia na primeira execução e fora de um checkout Git. O aplicativo recusa adotar pastas com outros dados e recusa dois processos simultâneos no mesmo workspace. Não substitua o diretório de uma versão anterior de outro aplicativo. Não publique a pasta de dados nem `session.json`.

## Do projeto à central

1. **Novo projeto:** informe o nome público da central. Propósito, autoridade e limites do projeto são internos. Use somente conteúdo próprio; não insira credenciais ou dados pessoais.
2. **Fontes:** registre o texto original, versão, o que foi observado e seus limites. Fontes são internas e têm histórico de versões.
3. **Procedimentos:** opcionalmente documente os passos e resultados observados, vinculados às fontes. Sem execução, registre a pendência; o aplicativo não executa o produto por você.
4. **Artigos:** escreva o texto público e os limites públicos. Selecione fontes e, quando aplicável, um procedimento. A evidência para revisão é interna.
5. **Conferir e revisar:** leia a prévia salva, fontes e procedimento. Informe um identificador local do revisor e a nota. A revisão fica vinculada àquela versão; selecionar “assistida por IA” não equivale a revisão independente.
6. **Publicações:** confirme os campos públicos e gere a central. Abra a prévia e baixe o ZIP. O ZIP contém HTML independente e manifesto de integridade. Pode ser extraído e lido ou colocado em um destino de hospedagem que você tenha autorizado; este aplicativo não faz upload.
7. **Manutenção:** atualize a fonte quando houver mudança real. Os artigos vinculados ficam com revisão vencida. Edite o artigo, confira a nova versão e gere outra publicação. A seleção de uma versão anterior não apaga nem restaura rascunhos.

## Importar documentação e buscar na central

Em **Artigos → Importar Markdown**, selecione de 1 a 32 arquivos próprios, total até 128 KiB UTF-8. A prévia mostra originais, rascunhos, endereços e adaptação de links entre arquivos do mesmo lote. Só a confirmação cria os registros, em uma transação; nenhum existente é sobrescrito. Todos entram sem revisão. Nomes que geram o mesmo endereço, HTML, front matter, imagens e links locais não resolvidos impedem a entrada. Não há importação de ZIP, diretórios, anexos ou sites.

Os três documentos próprios em `guide/` acompanham o produto e podem ser importados juntos para conhecer o fluxo. São ajuda deste aplicativo, sem dados de clientes. O corpo original UTF-8 fica na fonte e no histórico; a importação adapta links do rascunho e extrai o título inicial para evitar duplicação no leitor. A importação não valida execução ou veracidade.

A nova central exportada inclui busca por título e corpo público, com todas as palavras e comparação sem acentos. A busca funciona no navegador sem rede. A lista continua utilizável com JavaScript desativado. Publicações antigas preservadas não recebem busca retroativamente.

## Atualizar um documento importado

Em **Artigos → Atualizar por arquivo**, escolha a nova versão com o mesmo nome original. A prévia compara a fonte interna e o rascunho público, mostra o título, as diferenças e os artigos que dependem da fonte. A confirmação salva fonte e artigo juntos; se houver conflito, nada é salvo. Endereço, limites públicos e vínculos são mantidos. Links para outros documentos já importados são adaptados ao endereço atual do artigo correspondente.

Uma alteração vence a revisão anterior e exige nova conferência antes de publicar. A fonte original continua em **Fontes → Histórico**; o texto anterior do artigo fica em **Versões anteriores** após cada atualização por arquivo. Publicações anteriores permanecem intactas. Um arquivo sem mudança não cria revisão, histórico ou cópia adicional.

Este fluxo substitui o texto atual do artigo, inclusive edições manuais, apenas após a prévia e confirmação. Não faz mesclagem automática. Se você mudou os vínculos, anexou arquivos à fonte ou renomeou o endereço do próprio artigo, use a edição manual. Para documentos diferentes, continue usando Importar Markdown.

## O que sai no ZIP

| Informação | Central exportada |
|---|---|
| Nome do projeto | Sim |
| Títulos, texto dos artigos e limites públicos | Sim |
| Corpo e título das fontes, procedimentos e histórico | Não |
| Evidências internas, notas de revisão/publicação e revisor | Não |
| Propósito, autoridade e limites internos do projeto | Não |
| Sessão e banco do workspace | Não |

O sistema não reconhece segredos colocados no campo de texto público. Confira o leitor antes de compartilhar. O ZIP da central **não é backup** dos dados de trabalho.

## Formato e limites

Markdown simples: títulos, listas, blocos de código, tabelas e links HTTPS. HTML não é aceito. Imagens remotas e links locais que não correspondam a artigos da publicação não são ativados. Nesta prévia a interface é textual; anexos e editores visuais não estão disponíveis.

Até 64 fontes, 64 procedimentos e 64 artigos por projeto. Cada pedido HTTP tem limite de 256 KiB; texto longo ou caracteres multibyte consomem esse limite. Central até 8 MiB. Rascunhos não têm salvamento automático: use Salvar. Uma edição concorrente é recusada em vez de sobrescrever silenciosamente; copie seu texto antes de recarregar o estado.

## Operação e confiança

O conteúdo permanece em SQLite e arquivos locais. Não há telemetria, mensageria, credenciais externas, serviço persistente ou túnel. O processo precisa estar em execução para editar; a central exportada é independente dele. Não use o servidor como serviço público ou sistema multiusuário. Outro processo com acesso aos mesmos arquivos do usuário pode ler ou alterar dados; esta versão não oferece criptografia do armazenamento.

Esta prévia não demonstra redução de esforço, adequação a uma organização, manutenção contratada ou aceitação por clientes. A preparação editorial continua exigindo competência do operador. Código derivado do núcleo editorial original deste projeto; a distribuição independente tem atribuição de revisão pelo operador e exportação pública separada dos registros internos. Dados e históricos das amostras não estão incluídos.

## Conferência para desenvolvimento

No repositório de origem:

```sh
python3 -m unittest discover -s workspace/tests -v
python3 workspace/build_distribution.py --output /caminho/fora/do/checkout/knowledge-workspace-0.3.0.zip
```

O construtor inclui uma lista fixa de arquivos do produto; não empacota a pasta de dados, o checkout inteiro ou amostras.
