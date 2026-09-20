# Verificar a saúde do wiki

Mantém o wiki saudável conforme ele cresce. Dois níveis: **mecânico** (script determinístico, correções seguras automáticas) e **julgamento** (você lê e avalia; só reporta, não corrige fatos).

## Pré-condições

Leia `AGENTS.md` e `.llm-wiki/config.yml`. Confirme o escopo: wiki inteiro (padrão) ou subconjunto (`--scope wiki/concepts/`, ou páginas tocadas desde a última entrada `lint` no log: `python .llm-wiki/scripts/wiki_tools.py log-tail -n 20`).

## Nível 1 - Mecânico

```
python .llm-wiki/scripts/wiki_tools.py check --json
```

### Severidade

Cada verificação tem um nível: `error`, `warning` ou `info`. O nível não é fixo: cada wiki decide o que
lhe custa caro, em `lint.severity` no `.llm-wiki/config.yml`.

```yaml
lint:
  fail_on: error           # a partir de que nível o check sai com código 1
  severity:
    orphan: info           # wiki novo, ainda sem malha de links
    source-changed: error  # fontes sincronizadas de fora: mudança silenciosa não pode passar
    placement: off         # desligado de propósito
```

`off` silencia a verificação por completo. Reclassificar é decisão de time, não do agente: proponha e
explique, não edite o config por conta própria.

`--fail-on` na linha de comando vence a config, e é o que torna o `check` utilizável em CI:

| Uso | Comando |
|---|---|
| CI que barra só defeito mecânico | `check --fail-on error` (padrão) |
| CI rigoroso, que barra também órfã e fonte alterada | `check --fail-on warning` |
| Relatório que nunca quebra o build | `check --fail-on never` |

Sem `--fail-on`, vale o `lint.fail_on` da config; sem ele, `error`.

### Regras e tratamento

A coluna "Padrão" é o nível de fábrica, que a config pode mudar.

| Kind | Padrão | Significado | Ação |
|---|---|---|---|
| `config` | warning | `.llm-wiki/config.yml` malformado (categoria sem tipo, lista vazia, `required_by_type` de tipo não declarado); o checker segue com o padrão | Reporte; o vocabulário de páginas é decisão humana (operação `schema`). |
| `frontmatter` | error | chave obrigatória ausente, enum inválido, data ou `volatility` malformada | **Corrija** quando o valor correto for inequívoco (ex.: `type` deduzível do diretório; `created` do git log). Caso contrário reporte. |
| `broken-link` / `broken-wikilink` | error | alvo não existe | Procure arquivo com o mesmo nome em `wiki/`. Um único candidato: **corrija** o caminho. Zero ou vários: reporte. |
| `raw-ref` | error | `sources:` aponta para arquivo inexistente, ou para fora de `raw/` | Procure em `raw/` pelo mesmo nome. Um candidato: **corrija**. Senão reporte; nunca crie ou mova arquivos em `raw/`. |
| `orphan` | warning | página sem links de entrada | Não corrija automaticamente. Proponha 1 a 3 páginas que deveriam linkar para ela. |
| `index` | error | página fora do índice, entrada para arquivo inexistente, duplicata | **Corrija**: adicione a linha faltante (resumo a partir do frontmatter/primeiro parágrafo); entrada para arquivo inexistente vira `[MISSING]` no texto (não apague; humano decide). |
| `placement` | warning | `type` não bate com o diretório | Reporte; mover arquivo quebra links e exige decisão. |
| `log` | error | cabeçalho fora do formato | Reporte (log é append-only; não edite entradas antigas). |
| `unreferenced-raw` | warning | arquivo em `raw/` sem página | Liste como backlog de ingestão. Com manifesto, vem resumido em uma linha; o detalhe está em `wiki/manifest.md`. |
| `source-changed` | warning | a fonte mudou desde a última ingestão (hash difere do manifesto) | **Prioridade máxima.** Releia a fonte e revise a página que a compila; a página pode estar afirmando o que a fonte não diz mais. Só regenere o manifesto depois, senão a evidência da mudança se perde. |
| `manifest` | warning | fonte nova ou removida desde a última geração | `manifest --write`. Se a fonte sumiu, confira antes se foi remoção intencional no sync. |

| `freshness` | info | página mais velha que o prazo da sua `volatility` | Não é defeito: é fila de revisão. Releia a página, confirme se ainda vale e atualize `updated`; se mudou, é caso de `ingest` ou `research`. |

Após correções, rode `check` de novo e confirme.

### Frescor por volatilidade

Uma página não envelhece pelo calendário, envelhece pelo assunto. Preço, versão e roadmap viram mentira em
semanas; a ata de uma decisão não envelhece nunca. Cada página declara o seu ritmo no frontmatter:

```yaml
volatility: high | medium | low | static
```

Sem a chave, vale `lint.default_volatility` (padrão `medium`). Os prazos vêm de `lint.freshness`:

| Banda | Padrão | Para quê |
|---|---|---|
| `high` | 30 dias | preços, versões, roadmap, pessoas em papéis |
| `medium` | 180 dias | o padrão: conceito, entidade, síntese |
| `low` | 365 dias | assunto estável |
| `static` | nunca | decisão histórica, ata, fato fechado |

O aviso conta a partir de `updated`, então revisar uma página e atualizar a data zera o relógio. É por
isso que `freshness` nasce como `info`: um wiki grande sempre tem páginas vencidas, e isso não deveria
quebrar CI. Wiki de norma ou de preço costuma subir para `warning`.

## Nível 2 - Julgamento

Leia as páginas em escopo (índice primeiro, depois páginas; em wikis grandes, amostre por categoria e priorize `status: draft` e páginas atualizadas recentemente). Procure:

1. **Contradições** entre páginas que não estejam marcadas com `Status: Disputed`. Cite as duas páginas e os trechos.
2. **Claims obsoletos**: afirmação em página antiga que fonte mais nova (por `published`/`updated`) supera, sem bloco `Status: Outdated`.
3. **Conceitos sem página**: termo que aparece em 3+ páginas (ou é central) e não tem página própria. Sugira título e diretório.
4. **Cross-references faltantes**: páginas claramente relacionadas sem link mútuo. Sugira; não adicione em silêncio (exceto se `approval_mode: none`, aí adicione e registre).
5. **Blocos de status malformados**: `Disputed`/`Outdated` sem data ou sem explicação.
6. **Respostas arquivadas envelhecidas**: `comparison`/`question` cujas páginas citadas mudaram substancialmente depois de `created`. Sugira `status: stale` e re-execução da query.
7. **Lacunas de dados**: perguntas em `wiki/questions/` com `question_status: open` e seções "Não consta nas fontes" recorrentes. Sugira fontes concretas a buscar (web, documentos internos), sem buscá-las agora a menos que autorizado.
8. **Sensibilidade**: página com indícios de dado confidencial (credencial, dado pessoal) sem `sensitivity` adequado. Reporte imediatamente, com prioridade alta.
9. **Overview desatualizado**: teses centrais em `overview.md` que sínteses recentes não sustentam mais.

## Relatório

Estruture assim:

```
## Lint - YYYY-MM-DD
Escopo: ...
Mecânico: N erros encontrados, M corrigidos automaticamente (lista)
Julgamento:
- [ALTA] ...
- [MEDIA] ...
- [BAIXA] ...
Backlog de ingestão: ...
Perguntas sugeridas para investigar: ...
```

Em `approval_mode: plan`/`all`, as correções de julgamento viram lista de tarefas para o humano aprovar; execute-as depois via `wiki ingest`/edições pontuais com log próprio.

## Log

```
python .llm-wiki/scripts/wiki_tools.py log-append --op lint --title "<N> issues, <M> auto-fixed" --agent <agente> --files "<arquivos corrigidos>" --notes "scope=<...>"
```

## Delegação

O agente `wiki-lint-agent` (somente leitura) pode executar o nível 2 sobre um subconjunto de páginas em paralelo e devolver achados estruturados; o agente principal consolida, corrige o que é seguro e registra.

## Específico por agente

- **Claude Code**: `/wiki lint`; subagente `wiki-lint-agent`. Pode ser agendado com hook `SessionStart` que roda apenas o nível 1 e imprime o resumo (opcional; ver `hooks/` no pacote).
- **Cursor**: `/wiki lint`; para rodar periodicamente, use a skill nativa `/loop` ou uma Automation.
- **Codex**: `$wiki lint`.
- **Copilot**: rode o nível 1 em CI (`python .llm-wiki/scripts/wiki_tools.py check`) e o nível 2 sob demanda.
