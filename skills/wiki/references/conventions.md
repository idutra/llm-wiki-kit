# Convenções de página e schema

Skill de referência. Não executa operações; garante que `wiki ingest`, `wiki-query`, `wiki lint` e `wiki export` escrevam páginas consistentes, e define o processo para evoluir o schema.

A fonte de verdade em tempo de execução é o `AGENTS.md` do repositório-alvo e os templates em `.llm-wiki/templates/`. Se este documento e o `AGENTS.md` do repositório divergirem, o `AGENTS.md` do repositório vence (ele pode ter sido customizado para o domínio). Sinalize a divergência ao usuário.

## Tipos de página

| Tipo | Diretório | Quando criar | Regra especial |
|---|---|---|---|
| `source` | `wiki/sources/` | Uma por arquivo (ou conjunto coeso) ingerido de `raw/` | `sources:` obrigatório e não vazio; resume na voz da fonte |
| `entity` | `wiki/entities/` | Pessoa, organização, equipe, produto, sistema citado por 2+ fontes ou central ao domínio | Campo `aliases` para nomes alternativos |
| `concept` | `wiki/concepts/` | Conceito, processo, decisão, métrica, política | Seção "Posição atual do wiki" é a síntese viva |
| `synthesis` | `wiki/syntheses/` | Tese transversal que o wiki sustenta e revisa a cada ingestão | Seção "Histórico" registra cada revisão |
| `comparison` | `wiki/comparisons/` | Resposta a "compare A e B" arquivada | Toda célula factual com fonte |
| `question` | `wiki/questions/` | Pergunta respondida e arquivada, ou pergunta aberta | `question_status` |
| `output` | `wiki/outputs/` | Deck Marp, relatório, gráfico gerado a partir de páginas | `generated_from` lista as páginas de origem; não introduz fatos |

## Frontmatter

Chaves obrigatórias em toda página: `title`, `type`, `status`, `created`, `updated`. Recomendadas: `sources`, `related`, `tags`, `sensitivity`. Datas em `YYYY-MM-DD`. Valores de enum:

- `status`: `draft` (escrito pelo agente, não revisado), `reviewed` (humano aprovou), `stale` (fonte mais nova pode ter superado), `disputed` (contradição aberta).
- `sensitivity`: `public`, `internal`, `confidential`, `restricted`. Herda de `default_sensitivity` na config; nunca rebaixe o nível de uma página sem aprovação humana.

`updated` reflete a última mudança de conteúdo, não de formatação. Ao só corrigir um link, não altere `updated`.

## Nomes de arquivo e links

- `kebab-case`, ASCII, sem acentos: `politica-de-credito.md`, não `Política de Crédito.md`.
- Páginas de fonte: `wiki/sources/<YYYY-MM-DD>-<slug>.md` quando a data de publicação for conhecida; só `<slug>.md` caso contrário.
- Arquivos em `raw/`: `raw/<categoria>/<YYYY-MM-DD>-<slug>.<ext>`. Categoria em kebab-case; reutilize categorias existentes antes de criar nova.
- Links entre páginas: relativos ao arquivo atual. Dentro de `wiki/entities/x.md`, um link para conceito é `../concepts/y.md`; para raw é `../../raw/cat/file.md`.
- Ao citar em conversa (fora de arquivos), use caminhos relativos à raiz do repo: `wiki/concepts/y.md`.
- Se `link_style: wikilink` estiver configurado (Obsidian), use `[[slug]]` e mantenha nomes de arquivo únicos em todo o `wiki/`.

## Citações e fidelidade

- Toda afirmação com número, data, nome ou citação literal precisa de link para a página `source` ou para o arquivo em `raw/`, e o valor precisa existir literalmente na fonte. Localize antes de escrever; copie como está (`42K` fica `42K`).
- Valores derivados (somas, diferenças) mostram os componentes.
- Separe sempre "o que a fonte diz" de "o que o wiki conclui". Use as seções dos templates para isso.
- Quando o agente usa conhecimento próprio para contextualizar, marque explicitamente: "(contexto geral, não consta nas fontes)".

## Contradições e obsolescência

Nunca reescreva história em silêncio. Use blocos de citação padronizados, sempre com data:

```
> **Status: Disputed** (2026-09-19) - [Fonte A](../sources/a.md) afirma X; [Fonte B](../sources/b.md) afirma Y. Pendente de decisão humana.
> **Status: Outdated** (2026-09-19) - Substituído por [Fonte C](../sources/c.md). Mantido para histórico.
```

Marque a página com `status: disputed` ou `stale` conforme o caso e liste no relatório da operação.

## index.md

- Uma seção `## <Categoria>` por diretório, na ordem: Overview, Sources, Entities, Concepts, Syntheses, Comparisons, Questions, Outputs.
- Linha: `- [Título](caminho/relativo.md) - resumo de uma linha (sources: N, updated: YYYY-MM-DD)`.
- Respostas arquivadas: resumo começa com `[Archived]`.
- `python .llm-wiki/scripts/wiki_tools.py index` gera o esqueleto preservando resumos existentes; use `--write` para gravar e depois melhore resumos `(no summary)`.

## log.md

```
## [YYYY-MM-DD] <op> | <título>
- agent: <claude-code|cursor|codex|copilot|human>
- files: <caminhos>
- approved_by: <nome|pending>
- notes: <uma linha>
```

`op` em {`init`, `ingest`, `query`, `archive`, `lint`, `index`, `export`, `schema`}. Queries que não escrevem nada não precisam de log, salvo se a config pedir auditoria de leitura. Use `wiki_tools.py log-append` para garantir o formato.

## Evoluir o schema (operação `schema`)

O `AGENTS.md` é co-evoluído com o humano. Para propor mudança:

1. Descreva o problema observado (ex.: "fontes de reunião não cabem em `source`; precisamos de `meeting`").
2. Proponha a alteração mínima ao `AGENTS.md` e, se for o caso, novo template em `.llm-wiki/templates/`. Tipo, categoria ou status novo também é declarado em `.llm-wiki/config.yml` (`categories: <diretório>: <tipo>`, `statuses`), que é o que `wiki_tools.py check` valida; chaves obrigatórias e enums do tipo novo vão em `required_by_type` e `enums`. Não edite o script.
3. Se `approval_mode` for `plan` ou `all`, não escreva antes da aprovação.
4. Registre `## [data] schema | <resumo>` no log com `approved_by`.
5. Se a mudança afetar páginas existentes (nova chave obrigatória), planeje a migração e rode `wiki_tools.py check` depois.

Mudanças no schema **do pacote** (esta coleção de skills) seguem o versionamento do pacote, não do wiki; ver o `README.md` do pacote.
