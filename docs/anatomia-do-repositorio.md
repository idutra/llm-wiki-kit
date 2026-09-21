# Anatomia de um repositório com LLM Wiki

Dois repositórios distintos aparecem neste projeto, e confundi-los é a causa mais comum de erro:

| | **O kit** (`llm-wiki-kit`) | **O wiki** (um por assunto) |
|---|---|---|
| O que é | O pacote de skills que você instala no agente | O repositório de conhecimento, em markdown |
| Quem versiona | Quem mantém o kit | O time dono do assunto |
| Conteúdo | `skills/`, `agents/`, `hooks/`, manifestos | `raw/`, `wiki/`, `.llm-wiki/`, `AGENTS.md` |
| Quantos | Um | Quantos você quiser |

O kit não sabe nada sobre o seu assunto; o wiki não contém código de ferramenta. A operação `init` copia
alguns arquivos do kit para dentro do wiki, e é essa cópia que precisa ser atualizada quando o kit evolui
(veja "Atualizar um wiki existente" em `skills/wiki/references/init.md`).

O exemplo completo e funcional deste documento está em [`examples/team-wiki/`](../examples/team-wiki).
Ele foi gerado pelas próprias operações do kit e passa em `check`, `manifest` e `publish`.

## O repositório do wiki, arquivo por arquivo

```text
team-wiki/
├── AGENTS.md                     Schema: regras, convenções e workflows. Todo agente lê.
├── CLAUDE.md                     Uma linha: @AGENTS.md
├── .gitignore                    dist/ (artefato derivado do publish)
│
├── raw/                          FONTES IMUTÁVEIS. Ninguém edita, nunca.
│   ├── research/                 Capturadas pela operação research, com proveniência
│   │   └── 2026-09-20-appropriate-uses-for-sqlite.md
│   └── notes/                    Notas de sessão, capturadas pela operação capture
│       └── 2026-09-20-pico-de-sqlite-busy-no-servico-de-relatorios.md
│
├── wiki/                         PÁGINAS COMPILADAS. O agente escreve, humanos revisam.
│   ├── index.md                  Catálogo: o que o wiki já sabe
│   ├── manifest.md               Catálogo: o que existe para saber (toda fonte + hash)
│   ├── log.md                    Trilha append-only: quem fez o quê, quando
│   ├── overview.md               Teses centrais e lacunas conhecidas
│   ├── sources/                  Uma página por fonte ingerida
│   ├── concepts/                 Conceitos que atravessam fontes
│   ├── questions/                Perguntas, respondidas ou abertas
│   ├── entities/  syntheses/  comparisons/  outputs/
│
├── .llm-wiki/
│   ├── config.yml                Configuração e vocabulário de páginas
│   ├── templates/                Um template por tipo de página + consumer-skill.md
│   └── scripts/wiki_tools.py     Helper determinístico, só stdlib, nunca chama LLM
│
└── dist/                         DERIVADO, fora do git: saída do publish
    └── team-data-wiki/           A skill somente leitura que vai para outros repositórios
```

### As três camadas e quem escreve em cada uma

| Camada | Diretório | Quem escreve | Regra |
|---|---|---|---|
| **Raw** | `raw/` | Humano, ou o agente ao capturar uma vez | Imutável. Corrige-se acrescentando, nunca editando. |
| **Wiki** | `wiki/` | O agente; o humano revisa | Toda afirmação rastreável a `raw/`. Toda escrita atualiza índice e log. |
| **Schema** | `AGENTS.md`, `.llm-wiki/` | Humano com o agente | Muda por operação `schema`, com aprovação e registro. |

A separação é o que torna o wiki auditável: um diff em `raw/` é sempre suspeito, e um diff em `wiki/` sempre
tem uma fonte para conferir.

### Os dois catálogos, que respondem a perguntas diferentes

`index.md` responde **"o que o wiki já sabe"**: uma linha por página compilada.

```markdown
## Concepts

- [Concorrência de escrita no SQLite](concepts/concorrencia-de-escrita-no-sqlite.md) - Um escritor por vez;
  o limite prático é lock-segundos por segundo, não escritas/s (sources: 4, updated: 2026-09-20)
```

`manifest.md` responde **"o que existe para saber"**: toda fonte de `raw/`, compilada ou não, com o hash do
conteúdo.

```markdown
| Fonte | Título | Página no wiki | Hash |
| --- | --- | --- | --- |
| `research/2026-09-20-appropriate-uses-for-sqlite.md` | Appropriate Uses For SQLite | [Appropriate Uses For SQLite](sources/appropriate-uses-for-sqlite.md) | `10990c0f8075` |
```

Sem o manifesto, um agente que lê só o índice conclui que o que não foi compilado não existe. O hash fecha a
outra lacuna: se uma fonte mudar depois de ingerida, o `check` avisa com `source-changed`, e a página
correspondente precisa ser revista **antes** de o manifesto ser regenerado.

### Anatomia de uma página

Toda página tem frontmatter com rastreabilidade e seções fixas do seu tipo:

```yaml
---
title: Concorrência de escrita no SQLite
type: concept
status: reviewed
created: 2026-09-20
updated: 2026-09-20
sources:                      # os arquivos de raw/ que sustentam esta página
  - raw/research/2026-09-20-appropriate-uses-for-sqlite.md
  - raw/notes/2026-09-20-pico-de-sqlite-busy-no-servico-de-relatorios.md
related:
  - wiki/questions/sqlite-em-producao.md
sensitivity: internal
concept_kind: concept
---
```

No corpo, cada afirmação carrega de onde veio:

```markdown
O SQLite aceita leitores simultâneos sem limite, mas apenas **um escritor por vez**: "it will only allow
one writer at any instant in time" ([Appropriate Uses For SQLite §High Concurrency](../sources/appropriate-uses-for-sqlite.md)).
```

A seção **"Posição atual do wiki"** é onde o wiki se compromete com uma leitura, com o grau de confiança e o
que a derrubaria. É a diferença entre um arquivo de resumos e uma base de conhecimento.

### O log como auditoria

```markdown
## [2026-09-20] capture | Pico de SQLITE_BUSY no servico de relatorios
- agent: claude-code
- files: raw/notes/2026-09-20-pico-de-sqlite-busy-no-servico-de-relatorios.md
- approved_by: Ana Souza
- notes: decisions=1; errors=1; facts=1; corrections=0; questions=1; redactions=1
```

Append-only, sempre pelo helper, que valida a operação. `git log` diz o que mudou nos arquivos; o `log.md`
diz qual operação foi, qual agente executou e quem aprovou.

## O que o kit copia para dentro do wiki

| Arquivo no wiki | Dono | O kit pode sobrescrever? |
|---|---|---|
| `.llm-wiki/scripts/wiki_tools.py` | Kit | Sim. Ninguém deve editá-lo no wiki. |
| `.llm-wiki/templates/*.md` | Wiki | Não. Só acrescenta os que faltam. |
| `.llm-wiki/config.yml` | Wiki | Não. Só acrescenta blocos novos. |
| `AGENTS.md` | Wiki | Não. Diff e aprovação; é operação `schema`. |
| `wiki/`, `raw/` | Wiki | Nunca. |

`python .llm-wiki/scripts/wiki_tools.py --version` diz de qual versão do kit veio a cópia local.

## Governança por git

Nada de runtime próprio nem de painel de permissões: o controle é o do repositório.

- **`approval_mode: all`** em `.llm-wiki/config.yml` faz toda escrita em `wiki/` passar por PR.
- **Branch protection** em `main` e **CODEOWNERS** em `wiki/**` definem quem revisa.
- **CI** roda `wiki_tools.py check --fail-on error` (ou `warning`, num wiki rigoroso); qualquer diff em `raw/**` que não seja adição merece rejeição.
- O subagente `wiki-curator` revisa a proposta contra o schema antes de o humano olhar.
- **`sensitivity`** por página, e `publish.max_sensitivity` impede que uma página `confidential` saia do
  repositório dentro de uma skill publicada.
