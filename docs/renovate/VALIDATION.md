# Renovate: validar o arquivo certo antes de implantar

Este procedimento resolve uma decisão estreita: escolher o modo do validador e interpretar sua saída. Foi conferido em 05/10/2026 com Renovate **44.135.0**, Node **24.15.0** e configurações fictícias próprias. Não é documentação oficial nem implantação realizada para um cliente.

A motivação foi uma dúvida pública de adoção na [discussão do fornecedor](https://github.com/renovatebot/renovate/discussions/41411). Não usamos arquivos ou credenciais do participante e não afirmamos resolver sua instalação.

## Checklist para o responsável

1. **Escolha quem opera o bot.** A opção hospedada e o self-hosting têm responsabilidades diferentes. Confirme instalação, repositórios permitidos e responsável por atualizações antes de executar. A [orientação oficial de onboarding](https://docs.renovatebot.com/getting-started/installing-onboarding/) é a referência para esse fluxo. Este guia para na validação local; não concede permissões.
2. **Classifique o arquivo.** Configuração da instância self-hosted é global. Configuração de um repositório ou preset compartilhado deve ser validada com `--no-global` quando o nome é passado explicitamente. O nome `default.json` sozinho não escolhe essa categoria. [Referência oficial de validação](https://docs.renovatebot.com/config-validation/).
3. **Confirme o contexto.** Registre versão, arquivo e hash. Variáveis `RENOVATE_*` e `config.js` existentes podem influenciar a leitura; use uma pasta de trabalho controlada. Não execute configurações JavaScript recebidas de desconhecidos.
4. **Leia o diagnóstico, além do código de saída.** Confirme que o arquivo foi realmente encontrado e qual modo foi usado. Na amostra sem arquivos, a ferramenta devolveu **0**, sem validar qualquer configuração.
5. **Trate migração explicitamente.** `--strict` também exige ausência de migração pendente. Uma configuração antiga pode retornar 0 sem essa opção e 1 com ela. Isso não testa permissões, dependências reais ou atualização de branches.
6. **Entregue a decisão ao operador.** Guarde modo, versão, hash, saída e alterações necessárias. A instalação só está pronta após observar o comportamento esperado no ambiente autorizado; essa etapa não foi executada aqui.

## Comandos após instalar a versão escolhida

Execute a partir de uma pasta controlada, utilizando o binário dessa instalação:

```sh
# Repositório ou preset compartilhado
renovate-config-validator --no-global --strict renovate.json

# Instância self-hosted
renovate-config-validator --strict global.json
```

## O que mudou nos resultados observados

Os [exemplos](examples/) são pequenos controles próprios; os hashes e comandos estão em [OBSERVATIONS.json](OBSERVATIONS.json).

| Entrada própria | Modo global | Modo de repositório | Decisão |
|---|---:|---:|---|
| Lista fictícia `repositories` | 0 | 1 | A lista pertence à instância, não ao arquivo do repositório. |
| `onboarding` com texto no lugar de booleano | 1 | 1 | Os diagnósticos diferem: tipo no modo global, escopo no modo de repositório. |
| `automerge: false` | Não executado | 0 | Controle válido do modo de repositório. |
| `onboarding: false` e `platform: github` | 0 | Não executado | Controle válido global, sem autenticação conferida. |

O controle antigo `dryRun: true` retornou 0 normalmente e 1 com `--strict`; o validador apontou migração para `dryRun: "full"`. Na pasta vazia, o comando sem argumentos retornou 0 sem arquivos validados. Os seis casos iniciais foram conferidos com e sem `--strict`; os três controles adicionais foram definidos antes de suas execuções.

## Limites da conferência

A instalação foi temporária, com scripts de instalação desabilitados. RE2 não carregou e houve aviso de fallback: **não foi certificada validação de expressões regulares**. Não usamos presets remotos nem executamos o bot. O comportamento de uma versão antiga mencionada na discussão não foi reproduzido.

A documentação oficial já oferece essas regras. A contribuição aqui é reuni-las numa decisão com exemplos executados; não medimos economia de tempo frente a um operador competente. Não há cliente, manutenção contratada, aceite externo ou vantagem comercial demonstrados. Nenhum arquivo do fornecedor é redistribuído neste diretório.
