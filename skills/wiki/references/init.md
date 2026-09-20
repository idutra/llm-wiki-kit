# Inicializar ou adotar um wiki

Cria a estrutura de um LLM Wiki no repositório atual ou adota um repositório que já tem `raw/` e/ou `wiki/`.
É idempotente: nunca sobrescreve arquivos existentes; apenas cria o que falta e reporta o que já existia.

## Quando usar

- O usuário pede para criar, iniciar ou adotar um LLM Wiki.
- A skill `wiki-query` ou outra operação não encontrou `wiki/` ou `.llm-wiki/config.yml` e o usuário confirmou que quer inicializar.

Não use para migrar wikis de outros formatos (Notion, Confluence, MediaWiki): isso é ingestão, não init.

## Pré-condições

1. Identifique a raiz do repositório-alvo (o diretório de trabalho atual, salvo indicação contrária). Confirme com o usuário se houver dúvida.
2. Confirme que o diretório está sob controle de versão (`git status`). Se não estiver, avise: o wiki depende de git para histórico, revisão e auditoria. Prossiga só com consentimento.
3. Pergunte (ou infira do pedido) três decisões e registre-as em `.llm-wiki/config.yml`:
   - `language` (padrão `pt-BR`);
   - `approval_mode`: `none`, `plan` (padrão) ou `all`;
   - `default_sensitivity` (padrão `internal`).

## Passos

Os arquivos-fonte estão em `assets/` na raiz desta skill (`skills/wiki/assets/`). Copie-os para o repositório-alvo conforme a tabela; se um destino já existir, não sobrescreva, apenas registre no relatório final.

| Origem (nesta skill) | Destino (repositório-alvo) | Observação |
|---|---|---|
| `assets/AGENTS.md` | `AGENTS.md` | Schema do wiki. Se já existir um `AGENTS.md`, acrescente ao final uma seção `## LLM Wiki` com o conteúdo, em vez de substituir. |
| `assets/CLAUDE.md` | `CLAUDE.md` | Contém apenas `@AGENTS.md`. Se já existir `CLAUDE.md`, acrescente a linha `@AGENTS.md`. |
| `assets/config.yml` | `.llm-wiki/config.yml` | Ajuste os valores escolhidos nas pré-condições. |
| `assets/templates/*.md` | `.llm-wiki/templates/` | Templates por tipo de página, mais `consumer-skill.md`, usado pelo `publish`. |
| `assets/scripts/wiki_tools.py` | `.llm-wiki/scripts/wiki_tools.py` | Helper determinístico (Python 3.9+, sem dependências). |
| `assets/wiki/index.md` | `wiki/index.md` | Catálogo vazio por categoria. |
| `assets/wiki/log.md` | `wiki/log.md` | Log append-only. |
| `assets/wiki/overview.md` | `wiki/overview.md` | Substitua as datas `1970-01-01` pela data de hoje. |
| (criar) | `raw/.gitkeep`, `raw/assets/.gitkeep` | Diretório de fontes imutáveis. |
| (acrescentar) | `.gitignore` | Linha `dist/` (saída do `publish`), se ainda não houver. |
| (criar) | `wiki/sources/`, `wiki/entities/`, `wiki/concepts/`, `wiki/syntheses/`, `wiki/comparisons/`, `wiki/questions/`, `wiki/outputs/` | Um `.gitkeep` em cada. |

Depois de copiar:

1. Se o repositório for usado com GitHub Copilot, crie `.github/copilot-instructions.md` com uma linha apontando para `AGENTS.md` ("Siga as convenções em AGENTS.md"). Copilot também lê `AGENTS.md` diretamente; o arquivo é redundância segura.
2. Adote conteúdo pré-existente: se já houver arquivos em `raw/` sem página correspondente em `wiki/sources/`, liste-os como backlog de ingestão. Não ingira agora.
3. Rode `python .llm-wiki/scripts/wiki_tools.py check` e confirme zero erros (avisos de raw não referenciado são esperados na adoção).
4. Registre no log:

```
python .llm-wiki/scripts/wiki_tools.py log-append --op init --title "Wiki inicializado" --agent <seu-agente> --files "AGENTS.md, .llm-wiki/, wiki/" --notes "approval_mode=<valor>; language=<valor>"
```

5. Se `approval_mode` for `all`, oriente o usuário a proteger a branch principal e exigir PR para `wiki/**` (seção Governança do `AGENTS.md`).

## Atualizar um wiki existente

O `init` copia arquivos do kit para dentro do repositório do wiki; quando o kit evolui, essas cópias ficam para trás. Sintomas: `wiki_tools.py` não conhece um subcomando (`manifest`, `seen`, `scan`, `publish`), `log-append` recusa uma operação, ou o `AGENTS.md` não descreve um workflow que a skill oferece.

Cada arquivo tem um dono, e isso decide como atualizar:

| Arquivo no wiki | Dono | Como atualizar |
|---|---|---|
| `.llm-wiki/scripts/wiki_tools.py` | Kit | **Sobrescreva** com `assets/scripts/wiki_tools.py`. Ninguém deve editá-lo no wiki; o vocabulário vem do `config.yml`. |
| `.llm-wiki/templates/*.md` | Wiki | Copie só os templates que **não existem** (por exemplo `consumer-skill.md`). Para os demais, mostre o diff e deixe o humano decidir. |
| `.llm-wiki/config.yml` | Wiki | Não sobrescreva. Acrescente ao final os blocos que faltam (`publish:`, `research:`, `capture:`) a partir de `assets/config.yml`. |
| `AGENTS.md` | Wiki | Não sobrescreva: o time pode ter regras próprias. Compare com `assets/AGENTS.md`, proponha os workflows e as operações de log que faltam. É operação `schema`: aprovação humana e log. |
| `wiki/log.md`, `wiki/index.md`, páginas | Wiki | Não toque. |

Depois: `python .llm-wiki/scripts/wiki_tools.py --version` deve mostrar a versão do kit; rode `check`, `manifest --write` se o manifesto ainda não existir, e registre:

```
python .llm-wiki/scripts/wiki_tools.py log-append --op schema --title "Atualizado para llm-wiki-kit <versão>" --agent <agente> --files ".llm-wiki/, AGENTS.md" --approved-by "<nome>" --notes "from=<versão anterior ou desconhecida>"
```

## Relatório final

Liste: arquivos criados, arquivos pré-existentes preservados, decisões de configuração, backlog de ingestão e próximos passos (operação `ingest` para a primeira fonte).

## Específico por agente

- **Claude Code**: `CLAUDE.md` com `@AGENTS.md` faz o schema ser carregado em toda sessão. As skills ficam disponíveis como `/wiki <operação>` e `/wiki-query` quando instaladas via plugin.
- **Cursor**: lê `AGENTS.md` automaticamente. Skills invocáveis com `/` no chat.
- **Codex**: lê `AGENTS.md`; skills em `.agents/skills/` invocáveis com `$wiki ingest`.
- **Copilot**: lê `AGENTS.md` e `.github/copilot-instructions.md`.
