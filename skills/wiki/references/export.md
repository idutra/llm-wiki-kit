# Exportar artefatos

Produz saídas a partir do que já está no wiki. Regra central: **um artefato não introduz fatos novos**. Tudo nele precisa existir nas páginas listadas em `generated_from`. Se faltar informação, a resposta é ingerir uma fonte ou arquivar uma query, não inventar no slide.

## Pré-condições

1. Leia `AGENTS.md` e `.llm-wiki/config.yml` (`export.marp`, `export.redact_sensitivity_above`).
2. Identifique as páginas de origem via `wiki-query` (index-first). Liste-as para o usuário antes de gerar.
3. Verifique `sensitivity` de cada página. Se alguma estiver acima de `redact_sensitivity_above`, pare e peça aprovação explícita; registre `approved_by` no log. Sem aprovação, gere com a seção omitida e um marcador "[omitido: confidencial]".

## Formatos

### Deck Marp

Arquivo `wiki/outputs/<YYYY-MM-DD>-<slug>.marp.md`:

```
---
marp: true
theme: default
paginate: true
---
<!-- llm-wiki: type=output; generated_from=wiki/syntheses/a.md, wiki/comparisons/b.md; sensitivity=internal; created=YYYY-MM-DD -->

# Título
...
```

Regras: 1 ideia por slide; máximo ~6 bullets; último slide "Fontes" com links para as páginas do wiki; notas do apresentador (`<!-- ... -->`) com as citações detalhadas. Renderize com `npx @marp-team/marp-cli <arquivo> -o <saida>.pdf` se o usuário pedir e a ferramenta estiver disponível; caso contrário, entregue o markdown.

O helper `wiki_tools.py check` reconhece frontmatter Marp e não exige as chaves de página normais nesse arquivo; os metadados do wiki ficam no comentário HTML.

### Relatório / sumário executivo

`wiki/outputs/<YYYY-MM-DD>-<slug>.md` com template `.llm-wiki/templates/output.md`. Estrutura: contexto, achados (cada um com link), implicações, lacunas, fontes.

### Tabela comparativa

Se ainda não existir, gere via `wiki-query` e arquive em `wiki/comparisons/` (é conhecimento, não só saída). O export então referencia a comparação.

### Gráficos (opcional)

Se houver dados tabulares em páginas, gere um script Python `wiki/outputs/<slug>.py` que lê os valores **explicitamente listados no script com comentário da página de origem** e plota com matplotlib. Rode só com consentimento. Salve a imagem em `wiki/outputs/<slug>.png` e referencie no relatório/deck.

## Após gerar

1. Adicione o artefato ao `wiki/index.md` na seção Outputs.
2. Log:

```
python .llm-wiki/scripts/wiki_tools.py log-append --op export --title "<título>" --agent <agente> --files "<caminho>" --approved-by "<nome|n/a>" --notes "format=<marp|report|chart>; from=<n> pages"
```

3. `python .llm-wiki/scripts/wiki_tools.py check`.

## Específico por agente

- **Claude Code / Cursor / Codex / Copilot**: fluxo idêntico; a diferença é só a ferramenta de shell para renderizar Marp. Em Cursor, um deck também pode ser pré-visualizado com a extensão Marp for VS Code.
