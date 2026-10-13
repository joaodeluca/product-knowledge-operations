# Salvamento privado entre dispositivos

A edição web 0.9 acrescenta uma conta pessoal com projetos privados no Supabase. O titular autorizou e criou o recurso Free, definiu suas credenciais e autorizou seu usuário. `site/browser/cloud-config.mjs` contém somente o endereço do projeto e a chave pública publishable. Esses arquivos não criam contas ou contratam planos.

## Resultado proposto

Entre com a mesma conta do Workspace em outro dispositivo para abrir os projetos salvos. O servidor confirma cada gravação; uma versão desatualizada recebe conflito, sem sobrescrever outra edição. Falha de rede mantém o editor e informa que a gravação pode ter chegado ao servidor. Não há sincronização offline automática nem edição colaborativa simultânea.

Originais, histórico, revisões e publicações ficam no projeto privado. A cópia dos projetos locais exige confirmação e conserva os originais neste navegador. O backup JSON continua disponível. A sessão (tokens de acesso e renovação, identificador e e-mail) fica no localStorage deste site, por projeto Supabase, por autorização do titular. A senha nunca é persistida. Recarregar restaura a conta; Sair remove o login do navegador. Web Locks serializa a renovação entre abas quando disponível. Falha temporária de rede conserva a sessão para reconexão, enquanto credencial revogada é removida. Troca de conta não autoriza gravar o rascunho de outra identidade.

## Configuração de uma instalação pessoal

1. Em uma nova instalação, autorizar e criar **uma conta pessoal e um projeto Supabase no plano Free**, sem dados/contas de outra empresa. A criação e os termos devem ser concluídos pelo titular. Não compartilhar senha de banco, token administrativo ou `service_role` no chat ou no aplicativo.
2. Aplicar `schema.sql` no SQL Editor do novo projeto. Ele cria armazenamento privado e três funções autenticadas. A lista de membros começa vazia: nenhum usuário recebe acesso automaticamente.
3. Desativar cadastro público e provedores anônimos em Authentication. Criar somente o usuário pessoal do Workspace em Authentication → Users, com senha definida pelo titular e confirmação administrada pelo titular. Não abrir cadastros de terceiros. A conta administrativa Supabase e o usuário do Workspace são identidades separadas.
4. Copiar o UUID desse usuário (não a senha) e executar no SQL Editor:

   ```sql
   insert into kw_private.members(user_id) values ('UUID_DO_USUARIO');
   ```

5. Configurar apenas os dados públicos do projeto: URL `https://…supabase.co` e chave `sb_publishable_…`.

   ```sh
   python3 scripts/configure_cloud.py --url https://PROJETO.supabase.co --publishable-key sb_publishable_CHAVE_PUBLICA
   ```

   O comando prepara a configuração e permite somente essa origem no CSP. Não cria recursos nem publica. Para desligar a integração: `python3 scripts/configure_cloud.py --disable`.
6. Antes de publicar, verificar o projeto hospedado de verdade: login, acesso sem login recusado, conta não autorizada recusada, salvamento/abertura em dois contextos separados, conflito de versão, cópia local consentida, backup e logout. Só depois conferir o candidato e realizar um dispatch manual com `expected_sha` do commit pessoal revisado.

O backend não envia convites, mensagens comerciais ou e-mails de recuperação. Nesta prévia privada, o titular administra recuperação do usuário no painel do provedor. O SMTP padrão do Supabase é limitado a endereços da equipe; acesso público exigiria outro trabalho e autorização, inclusive recuperação por e-mail adequada.

## Dados e limites

- Tabelas no schema privado, sem privilégios para `anon`/`authenticated`, com RLS habilitado. Funções `security definer` têm caminho de busca vazio, identificam o titular por `auth.uid()` e exigem membro habilitado. O cliente não escolhe `owner_id`.
- Gravação/recuperação valida estrutura, tamanho e identificadores no servidor. Uma transação bloqueia a linha do titular e confere a versão antes de salvar. Recuperação em lote é atômica.
- Limites da prévia: 20 projetos e 8 MiB de JSON no servidor; 50 artigos/20 publicações por projeto. JSONB pode ocupar um pouco mais que a representação compacta local.
- A chave pública não concede acesso por si só. Nenhuma chave secreta pode ir ao site, ao repositório ou à configuração do navegador.
- Não é criptografia ponta a ponta. O titular do projeto e o provedor controlam o armazenamento; backups baixados também contêm dados privados.
- O plano gratuito pode pausar após uma semana sem atividade. Não promete disponibilidade contínua; manter backup. Não contratar plano pago automaticamente.

## Verificações locais

`node --test scripts/tests/browser-cloud.test.mjs scripts/tests/browser-autosave.test.mjs scripts/tests/browser-model.test.mjs` verifica o cliente com respostas HTTP simuladas e as regras editoriais. Não comprova autenticação hospedada.

`test-database.py` aplica a migração a um PostgreSQL descartável vazio e verifica permissões, isolamento entre duas identidades, concorrência, rollback e limites. Exige `KW_TEST_CONTAINER` e usa o ambiente Docker explicitamente fornecido. O teste cria um substituto de `auth.uid()` com claims simulados; não representa o gateway JWT do Supabase. Nunca executar em um banco de produção.

Referências consultadas em 13/10/2026: [Auth com senha](https://supabase.com/docs/guides/auth/passwords), [chaves de API](https://supabase.com/docs/guides/getting-started/api-keys), [segurança por linha](https://supabase.com/docs/guides/database/postgres/row-level-security), [SMTP](https://supabase.com/docs/guides/auth/auth-smtp), [plano Free](https://supabase.com/pricing).

A integração hospedada foi conferida em 13/10/2026 com o login feito pelo titular, duas sessões em origens locais distintas e Supabase real: criação/gravação/leitura compartilhada, conflito recusado, rascunho preservado, cópia local consentida, backup validado e logout de uma sessão sem apagar os projetos. Não representa teste em dois dispositivos físicos, aceitação externa ou auditoria independente.

Na edição0.8, o editor salva após900ms sem digitação e serializa alterações feitas durante gravações. Confirma somente após resposta válida. Uma resposta perdida exige conferência da versão remota antes de qualquer nova tentativa; JSONB pode reordenar chaves, por isso a comparação é estrutural. Conflito mantém texto, oferece download do rascunho e não sobrescreve automaticamente. A saída da tela aguarda gravação ou pede descarte explícito. Originais e histórico continuam privados. [Sessões Supabase](https://supabase.com/docs/guides/auth/sessions).

## Centrais publicadas por link (0.9)

A migração aditiva `publication.sql` deve ser aplicada após `schema.sql`. Não republicar a migração base em produção. A nova tabela privada `help_sites` mantém snapshots imutáveis e um identificador público aleatório estável por projeto. Nada existente se torna público ao aplicar a migração.

As funções autenticadas `kw_help_status`, `kw_publish_help` e `kw_unpublish_help` exigem membro habilitado e só administram projetos do titular. A publicação bloqueia a mesma linha das gravações privadas, confere versão e revisão de todos os artigos e constrói no servidor uma projeção restrita: nome da central, IDs, títulos e textos, além de aliases de links já presentes nesses textos. Nunca copia originais, notas de revisão, histórico privado ou campos arbitrários do cliente. Limites: 2 MiB por snapshot, 20 versões por central, 8 MiB de versões publicadas por titular. Respostas repetidas da mesma publicação são idempotentes.

Somente `kw_read_help(UUID)` permite execução anônima. Retorna a última versão de uma central ativa; não lista centrais, não lê projetos privados e retorna 404 após retirada. Tabelas continuam sem acesso direto. O leitor em `site/help/` usa apenas chave pública, sem sessão ou cabeçalho de autorização, com cache desabilitado. Qualquer pessoa com o link pode ler; UUID e noindex não tornam uma publicação privada. Retirar do ar impede novas respostas, mas não revoga cópias já feitas.

O backup JSON do Workspace conserva projetos e downloads HTML, mas não IDs públicos, status ou histórico hospedado. Recuperação cria projetos privados novos; publicar essas cópias gera novos links. A edição offline e os arquivos históricos permanecem preservados.

`KW_TEST_CONTAINER=CONTAINER_DESCARTAVEL python3 cloud/supabase/test-publication.py` verifica a base e a migração nova em PostgreSQL isolado, com duas identidades simuladas. Inclui privilégio anônimo restrito, dono, revisão/versão, projeção de campos, rascunho privado, atualização estável, retirada, republicação e repetição idempotente. Não equivale a teste no gateway hospedado.

## Aparência da central (0.10)

Após schema.sql e publication.sql, aplique branding.sql uma vez. A migração valida a aparência opcional e inclui apenas logo PNG normalizado e duas cores no próximo snapshot explicitamente publicado; mantém permissões, links e versões anteriores. Projetos legados mantêm o visual padrão. Nenhuma publicação acontece na migração ou ao salvar aparência.

Personalizar aparência altera o nome da central, logo e cores com prévia ampla/celular. Salvar aparência guarda na conta com proteção contra conflito; cancelar descarta a prévia. PNG/JPEG/WebP de até 2 MiB são decodificados e normalizados para PNG de até 512×512, sem URL externa/metadados do original; resultado limitado a 192 KiB incluindo data URL. SVG não é aceito. O servidor valida tipo, tamanho, cabeçalho/dimensões PNG e cores hexadecimais, e a projeção pública usa campos explícitos. Logos contam nas quotas existentes. Texto do cabeçalho e botões usa preto/branco conforme contraste.

Nome e aparência entram também no backup JSON e nos novos downloads HTML. Snapshots já publicados só mudam por Atualizar publicação, no mesmo endereço. Os limites e a dependência do Supabase Free permanecem.

## Categorias e ordem (0.11)

Após branding.sql, aplique organization.sql uma vez. Campo opcional categories preserva a ordem de categorias, documents preserva a ordem de artigos dentro de cada grupo; categoryId opcional referencia uma categoria. Sem categoria fica por último. Projetos anteriores mantêm sua ordem. Validação recusa IDs/nomes duplicados, referências ausentes e categorias extras/inválidas; no máximo 20 categorias e 80 caracteres por nome.

A publicação projeta apenas id/name de categorias não vazias e categoryId dos artigos, mantendo marca e campos públicos anteriores. Não altera snapshots históricos nem grants. Busca inclui o nome da categoria e oculta grupos sem resultados. Backup e novos HTMLs preservam organização; alterações exigem salvar privado e confirmar publicação. CAS existente protege edições em outra aba/dispositivo.

## Seleção de artigos (0.13)

Após organization.sql, aplique selection.sql uma vez. Nenhum grant novo, mudança de acesso ou publicação automática. O campo booleano publish é opcional: ausente conserva a seleção do legado; artigos novos usam false (rascunho). O servidor publica apenas artigos selecionados com revisão vigente, filtra categorias e aliases para esse conjunto e recusa seleção vazia. CAS e limites anteriores permanecem. Metadados autenticados incluem IDs dos artigos da última versão para distinguir seleção privada de conteúdo no ar.

Manter como rascunho salva a escolha; a versão pública só muda após Atualizar publicação. Retirar todos usa Retirar do ar. Selecionar um artigo não revisa seu conteúdo, e editá-lo continua vencendo sua revisão. Backup preserva seleção e histórico. HTML baixado e prévias também excluem rascunhos. Links escritos manualmente para artigos excluídos podem deixar de funcionar; não incluímos aliases privados para resolvê-los.

`KW_TEST_CONTAINER=CONTAINER_DESCARTAVEL python3 cloud/supabase/test-selection.py` verifica seleção, rascunhos não revisados, aliases/categorias, legado, CAS e recusa de seleção vazia em PostgreSQL isolado com identidades simuladas.
