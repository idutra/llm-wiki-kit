# Busca

Estratégia de localização em três degraus. Use o degrau mais barato que resolve.

## Degrau 1 - Índice

`wiki/index.md` é a primeira consulta, sempre. Ele foi feito para ser lido inteiro. Selecione candidatos por título e resumo. Funciona bem até algumas centenas de páginas.

## Degrau 2 - Busca textual (rg)

Quando o índice não basta:

```
rg -i -l "<termo>|<sinonimo>|<sigla>" wiki/
rg -i -n -C 2 "<termo>" wiki/concepts/
rg -l "^type: entity" wiki/            # por frontmatter
rg -l "status: disputed" wiki/          # contradições abertas
```

Regras: sempre inclua sinônimos e siglas; busque também em `raw/` quando a pergunta pedir fonte primária (`rg -i -l "<termo>" raw/`). Sem `rg`, use `grep -ril` ou `Select-String -Path wiki\**\*.md -Pattern "<termo>"` no PowerShell.

## Degrau 3 - qmd (opcional)

[qmd](https://github.com/tobi/qmd) é um buscador local para markdown com BM25 + vetores e re-ranking, tudo on-device, com CLI e servidor MCP. Só ative quando `rg` começar a devolver dezenas de páginas por termo.

Configuração (proponha ao usuário; não instale sem consentimento):

1. Instalar conforme o README do projeto (Node.js ou Bun). Verifique a versão atual antes de recomendar comandos.
2. Registrar a coleção: `qmd collection add <nome> ./wiki` (confirme a sintaxe da versão instalada).
3. Indexar: `qmd index` (repita após ingests grandes; pode entrar no fluxo de `wiki ingest` como passo final).
4. Anotar na config: `search.engine: qmd`, `search.qmd_collection: <nome>`.
5. Uso: `qmd search "<pergunta>"` para BM25; `qmd query "<pergunta>"` para híbrido com re-ranking. Como MCP, registre o servidor no agente (Claude Code: `.mcp.json`; Cursor: `.cursor/mcp.json`; Codex: `config.toml`) e use a ferramenta em vez do shell.

Governança: qmd roda localmente e não envia dados para fora; ainda assim, o índice é um arquivo derivado que pode conter texto de páginas `confidential`. Adicione o diretório de índice ao `.gitignore` e não o distribua.

## Índices por categoria (alternativa sem ferramenta)

Para wikis grandes sem qmd: crie `wiki/<categoria>/_index.md` por diretório e faça `wiki/index.md` apontar para eles. Leitura em dois níveis mantém o custo previsível. Isso é mudança de schema: siga `wiki conventions`, seção "Evoluir o schema".

## Sinais para subir de degrau

- `wiki-query` precisa de mais de 3 buscas `rg` para achar candidatos.
- `index.md` passa de ~600 linhas.
- Usuários perguntam por sinônimos que o índice não cobre.
