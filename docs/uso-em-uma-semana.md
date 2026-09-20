# Uma semana usando o wiki

Este é o passo a passo que produziu [`examples/team-wiki/`](../examples/team-wiki), do repositório vazio até
o conhecimento chegar ao serviço onde o código está. Os comandos são reais e o resultado de cada um está no
exemplo; os diálogos com o agente estão encurtados.

O time: Ana mantém o wiki; o resto do time consome. O assunto: escolha e operação de banco de dados.

## Segunda: criar o wiki (operação `init`)

```
/wiki init
```

O agente pergunta idioma, `approval_mode` (Ana escolhe `plan`: o agente propõe, ela aprova, ele escreve) e
sensibilidade padrão. Depois cria `AGENTS.md`, `CLAUDE.md`, `.llm-wiki/`, `wiki/` e `raw/`, roda `check` e
registra `init` no log.

```
$ python .llm-wiki/scripts/wiki_tools.py check
1 pages, 0 errors, 0 warnings
```

Um wiki vazio já é um wiki válido. Ana faz o primeiro commit.

## Terça: pesquisar (operação `research`)

Um engenheiro pergunta se o SQLite aguenta o serviço de relatórios. Ninguém sabe, e ninguém tem fonte.

```
/wiki research "SQLite serve como banco de produção para uma aplicação web com escrita moderada?"
```

**1. O agente confere o que já se sabe.** Lê índice e manifesto; o wiki está vazio. Registra a pergunta em
`wiki/questions/sqlite-em-producao.md` com `question_status: open`.

**2. Propõe ângulos.** Ana aprova o plano:

| Ângulo | Consultas |
|---|---|
| `applied` | "SQLite in production web application experience", "migrated from Postgres to SQLite production" |
| `contrarian` | "SQLite production problems concurrency SQLITE_BUSY", "SQLite single writer bottleneck" |

O ângulo `contrarian` é obrigatório. Sem ele, a pesquisa só confirma o que a pergunta já supunha.

**3. Busca em paralelo.** Um subagente `wiki-research-agent` por ângulo, somente leitura, sem shell. Cada um
devolve candidatos com autor, data, tipo, por que importa, posição e alertas. Nenhum escreve nada.

**4. Ana aprova as fontes.** O agente consolida, roda `seen` para descartar o que já foi capturado, e mostra
a tabela, com o que ficou de fora e por quê:

```
$ python .llm-wiki/scripts/wiki_tools.py seen https://sqlite.org/whentouse.html ...
new   https://sqlite.org/whentouse.html
```

Ana aprova 3 de 8. Rejeita um agregador sem autoria e um post promocional cujos números não têm origem. O
post da Turso, com interesse comercial mas fato verificável, ela aprova com o alerta registrado.

**5. Captura e ingestão.** As três entram em `raw/research/` com cabeçalho de proveniência:

```yaml
source_url: https://sqlite.org/whentouse.html
collected: 2026-09-20
found_by: research
research_question: wiki/questions/sqlite-em-producao.md
angle: contrarian
capture: partial
```

Depois são ingeridas uma por vez. A primeira cria `wiki/sources/appropriate-uses-for-sqlite.md` e o conceito
`concorrencia-de-escrita-no-sqlite.md`; as outras duas enriquecem o mesmo conceito.

**6. Síntese.** A resposta vira a página da pergunta, com `question_status: partial`, porque nenhuma fonte
pública mede a faixa de carga do time. Essa lacuna fica escrita, não escondida.

Ao fim da terça: 4 páginas, 3 fontes, uma pergunta parcialmente respondida e duas lacunas registradas.

## Quarta: o incidente (operação `capture`)

O serviço de relatórios começa a dar erro 500 no fim do dia. Ana debuga com o agente, no repositório
`reporting-service`, e descobre que a transação de escrita segurava o lock por 4,1 segundos porque
renderizava um PDF dentro dela. O PR 412 corrige.

Ao fim da sessão, o agente **oferece** registrar o que se aprendeu. Ana aceita. Ele monta a nota na conversa,
sem gravar, com decisões, erros e correções, fatos verificados e perguntas em aberto. Cada item marcado:

- `verified` - "transação caiu de 4,1 s para 38 ms" (medido nesta sessão);
- `reported` - "decidimos manter o SQLite" (a justificativa não foi medida).

Durante o debug apareceram um token de CI e a URL do banco com senha. O agente troca por
`<redacted: token>` e roda o scanner **antes** de gravar:

```
$ python .llm-wiki/scripts/wiki_tools.py scan .tmp/nota.md
0 finding(s). Pattern scan only: a clean result does not replace human review.
```

A ordem importa: `raw/` é imutável e versionado, então segredo gravado ali fica no histórico do git.

A nota vai para `raw/notes/` no repositório do wiki e é ingerida. Ela atualiza o conceito com o número real
e muda a resposta da pergunta, que passa de teórica a operacional.

## Quinta: publicar (operação `publish`)

O conhecimento está no wiki, mas o trabalho acontece nos repositórios de serviço. Ninguém vai lembrar de
abrir o wiki.

```
$ python .llm-wiki/scripts/wiki_tools.py publish --install ../reporting-service
examples/team-wiki/dist/team-data-wiki: 15 files, 3635 words, version a3f91c2
installed: ../reporting-service/.claude/skills/team-data-wiki
installed: ../reporting-service/.agents/skills/team-data-wiki
```

O que foi montado:

```text
dist/team-data-wiki/
├── SKILL.md                  navegação e citação, para o agente consumidor
└── references/
    ├── wiki/                 as páginas, sem log.md
    ├── raw/                  as fontes, compiladas ou não
    └── VERSION.md            commit, data, 7 páginas, 4 de 4 fontes compiladas
```

O campo que decide se isso funciona é a `description` em `.llm-wiki/config.yml`. É só por ela que um agente
resolve carregar a skill, e o padrão dele é não carregar. Ana escreve citando os assuntos concretos:

```yaml
publish:
  description: O que este time ja apurou sobre escolha e operacao de banco de dados - SQLite em producao,
    concorrencia de escrita, WAL, contencao e SQLITE_BUSY, quando trocar por um banco cliente/servidor...
```

O `publish` recusa-se a montar com erro no `check`, com página acima de `publish.max_sensitivity`, sem
`description`, ou com link que não resolva dentro da skill.

## Sexta: alguém usa sem saber que está usando

Em `reporting-service`, um engenheiro que não participou de nada disso pede ao agente:

> adiciona um endpoint que grava o resultado da conciliação

O agente carrega a skill sozinho, pela descrição, e responde com o bloco que o `SKILL.md` exige:

```markdown
## Base no wiki

Wiki: a3f91c2 · Páginas consultadas: concepts/concorrencia-de-escrita-no-sqlite.md

| Afirmação usada | Origem | Conferido na fonte? |
| --- | --- | --- |
| Um escritor por vez; o que satura é a duração da transação | concepts/concorrencia-de-escrita-no-sqlite.md | sim, Appropriate Uses For SQLite §High Concurrency |
| Não fazer trabalho de CPU ou rede dentro da transação | sources/pico-de-sqlite-busy-no-servico-de-relatorios.md | sim, nota §Erros e correções |

Lacunas: o limite de escrita do nosso hardware com transações curtas não foi medido.
Fora do wiki: o desenho do endpoint em si.
```

Ele não perguntou pelo wiki, não sabia que a conciliação tocava esse assunto, e mesmo assim não repetiu o
erro de quarta-feira. É esse o produto.

Se, ao usar, ele descobrir que o wiki está errado ou calado, a seção "Devolver ao wiki" do `SKILL.md` leva a
uma nota de sessão, que volta como issue `wiki-capture`. O ciclo fecha.

## O ciclo, em uma figura

```text
        pergunta sem fonte                      trabalho real
               │                                     │
          [research]                            [capture]
               │                                     │
               ▼                                     ▼
          raw/research/  ─────────┐        ┌──── raw/notes/
                                  ▼        ▼
                              [ingest] → wiki/  ←── [lint] saúde
                                  │        │
                                  │   [archive] respostas boas
                                  ▼
                             [publish] → skill somente leitura
                                  │
                                  ▼
                    repositórios de serviço (uso diário)
                                  │
                                  └──── issue wiki-capture ──┐
                                                             │
                                          (volta para capture)┘
```

## Rotinas que valem a pena

| Quando | O quê |
|---|---|
| A cada pergunta sem fonte | `research` em vez de responder de memória |
| Ao fim de sessão com decisão, erro ou fato verificado | `capture` (o agente oferece; você decide) |
| A cada 5 a 10 ingestões | `lint`, e as lacunas que ele reporta viram perguntas de `research` |
| A cada merge no wiki | `publish` por CI, para os consumidores não ficarem para trás |
| Periodicamente, em assunto que muda | `research` só com o ângulo `recent`, e o que mudou vira `Status: Outdated` |

## O que não esperar

- **Economia de tokens por tarefa.** Medimos: o wiki não reduziu tokens por tarefa em relação a ler as fontes
  direto. O ganho está em lacuna sinalizada, citação conferível e no assunto que ninguém lembrou de perguntar.
- **Escala ilimitada.** O índice é lido inteiro; até algumas centenas de páginas isso é barato. Acima disso,
  `_index.md` por diretório ou `qmd` (operação `search`).
- **Atualização automática.** O wiki é tão atual quanto a última ingestão, e a skill publicada, quanto o
  último `publish`. Por isso o `VERSION.md` e o CI.
- **Dispensa de revisão humana.** O scanner pega padrões; nome de cliente e valor de contrato ele não pega.
