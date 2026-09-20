# Verificar a saúde do wiki

Mantém o wiki saudável conforme ele cresce. Dois níveis: **mecânico** (script determinístico, correções seguras automáticas) e **julgamento** (você lê e avalia; só reporta, não corrige fatos).

## Pré-condições

Leia `AGENTS.md` e `.llm-wiki/config.yml`. Confirme o escopo: wiki inteiro (padrão) ou subconjunto (`--scope wiki/concepts/`, ou páginas tocadas desde a última entrada `lint` no log: `python .llm-wiki/scripts/wiki_tools.py log-tail -n 20`).

## Nível 1 - Mecânico

```
python .llm-wiki/scripts/wiki_tools.py check --json
```

Regras e tratamento:

| Kind | Significado | Ação |
|---|---|---|
| `config` | `.llm-wiki/config.yml` malformado (categoria sem tipo, lista vazia, `required_by_type` de tipo não declarado); o checker segue com o padrão | Reporte; o vocabulário de páginas é decisão humana (operação `schema`). |
| `frontmatter` | chave obrigatória ausente, enum inválido, data malformada | **Corrija** quando o valor correto for inequívoco (ex.: `type` deduzível do diretório; `created` do git log). Caso contrário reporte. |
| `broken-link` / `broken-wikilink` | alvo não existe | Procure arquivo com o mesmo nome em `wiki/`. Um único candidato: **corrija** o caminho. Zero ou vários: reporte. |
| `raw-ref` | `sources:` aponta para arquivo inexistente | Procure em `raw/` pelo mesmo nome. Um candidato: **corrija**. Senão reporte; nunca crie ou mova arquivos em `raw/`. |
| `orphan` | página sem links de entrada | Não corrija automaticamente. Proponha 1 a 3 páginas que deveriam linkar para ela. |
| `index` | página fora do índice, entrada para arquivo inexistente, duplicata | **Corrija**: adicione a linha faltante (resumo a partir do frontmatter/primeiro parágrafo); entrada para arquivo inexistente vira `[MISSING]` no texto (não apague; humano decide). |
| `placement` | `type` não bate com o diretório | Reporte; mover arquivo quebra links e exige decisão. |
| `log` | cabeçalho fora do formato | Reporte (log é append-only; não edite entradas antigas). |
| `unreferenced-raw` | arquivo em `raw/` sem página | Liste como backlog de ingestão. Com manifesto, vem resumido em uma linha; o detalhe está em `wiki/manifest.md`. |
| `source-changed` | a fonte mudou desde a última ingestão (hash difere do manifesto) | **Prioridade máxima.** Releia a fonte e revise a página que a compila; a página pode estar afirmando o que a fonte não diz mais. Só regenere o manifesto depois, senão a evidência da mudança se perde. |
| `manifest` | fonte nova ou removida desde a última geração | `manifest --write`. Se a fonte sumiu, confira antes se foi remoção intencional no sync. |

Após correções, rode `check` de novo e confirme.

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
