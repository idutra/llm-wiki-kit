# Índice, manifesto e log

Cuida dos três arquivos de navegação do wiki: `wiki/index.md` (catálogo das páginas), `wiki/manifest.md` (catálogo das fontes) e `wiki/log.md` (cronologia append-only). As demais skills atualizam esses arquivos incrementalmente; esta skill reconstrói e repara.

Os dois catálogos respondem a perguntas diferentes, e é por isso que existem separados. O índice responde "o que o wiki já sabe"; o manifesto responde "o que existe para saber". Sem o manifesto, um agente consumidor só enxerga o que já foi compilado e conclui que o resto não existe.

## Reconstruir index.md

1. Pré-visualize:

```
python .llm-wiki/scripts/wiki_tools.py index
```

O script lista toda página de `wiki/` (exceto `index.md` e `log.md`) por categoria, preservando o resumo já existente para cada caminho e usando `(no summary)` onde não houver.

2. Compare com o `index.md` atual. Se houver seções ou notas manuais fora do padrão (ex.: "Leituras recomendadas"), preserve-as ao final, sob `## Notas`.
3. Grave: `python .llm-wiki/scripts/wiki_tools.py index --write`.
4. Para cada `(no summary)`, abra a página e escreva um resumo de uma linha (máximo ~140 caracteres) a partir do frontmatter e do primeiro parágrafo. Páginas com `archived_from: query` recebem prefixo `[Archived]`.
5. Rode `python .llm-wiki/scripts/wiki_tools.py check` e confirme zero erros de `index`.
6. Log: `python .llm-wiki/scripts/wiki_tools.py log-append --op index --title "Indice reconstruido" --agent <agente> --files "wiki/index.md"`.

Regras: uma linha por página, exatamente uma vez; ordem de seções fixa (Overview, Sources, Entities, Concepts, Syntheses, Comparisons, Questions, Outputs); dentro da seção, ordem alfabética por título, exceto Sources, que fica em ordem cronológica decrescente pela data no nome do arquivo.

## Regenerar o manifesto

```
python .llm-wiki/scripts/wiki_tools.py manifest --write
```

Gera `wiki/manifest.md` com uma linha por arquivo de `raw/`: caminho, título, página que o compilou (ou "não ingerida") e hash curto do conteúdo. Regenere a cada ingestão e a cada sync de fontes, e registre `--op index` no log quando for uma regeneração avulsa.

O hash normaliza CRLF, então o mesmo arquivo dá o mesmo valor no Windows e no Linux. É esse hash que transforma um re-sync silencioso em aviso:

| Aviso do `check` | O que aconteceu | O que fazer |
|---|---|---|
| `source-changed` | A fonte mudou depois de ter sido ingerida | Releia a fonte, revise a página que a compila e só então regenere o manifesto. Regenerar primeiro apaga a evidência |
| `manifest` (fonte ausente) | Chegou fonte nova em `raw/` | Regenere o manifesto; a fonte entra como pendente e vai para o backlog |
| `manifest` (fonte sumiu) | Um arquivo saiu de `raw/` | Confira se foi remoção intencional no sync; as páginas que o citam ficam com link quebrado |
| `unreferenced-raw` | Há fontes sem página | É o backlog de ingestão, resumido em uma linha porque o manifesto já lista item a item |

## Ler o log

```
python .llm-wiki/scripts/wiki_tools.py log-tail -n 10
```

Use no início de sessões longas para retomar contexto: o que foi ingerido, que lint está pendente, que perguntas ficaram abertas. Em shell: `grep "^## \[" wiki/log.md | tail -5` (bash) ou `Select-String "^## \[" wiki/log.md | Select-Object -Last 5` (PowerShell).

## Registrar no log

Sempre pelo helper, para garantir o formato:

```
python .llm-wiki/scripts/wiki_tools.py log-append --op <init|ingest|query|archive|lint|index|export|schema> --title "<título>" --agent <claude-code|cursor|codex|copilot|human> --files "<a, b>" --approved-by "<nome|pending>" --notes "<uma linha>"
```

Nunca edite entradas anteriores. Se uma entrada estiver errada, acrescente uma nova com `notes: corrige entrada de <data>`.

## Escala

Até algumas centenas de páginas, o índice é suficiente para localização (leitura completa custa poucos milhares de tokens). Acima disso, considere dividir o índice por categoria (`wiki/index.md` com links para `wiki/<categoria>/_index.md`) e habilitar `wiki search` com `qmd`. Proponha a mudança como operação `schema`.
