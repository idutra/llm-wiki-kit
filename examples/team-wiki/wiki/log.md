# Log do wiki

Registro cronológico append-only. Nunca edite entradas anteriores; apenas acrescente ao final.
Cabeçalho de entrada: `## [YYYY-MM-DD] <op> | <título>` com uma das operações válidas listadas no `AGENTS.md`.
Registre sempre por `wiki_tools.py log-append`, que valida a operação.
Últimas 5 entradas: `grep "^## \[" wiki/log.md | tail -5`.

## [2026-09-20] init | Wiki inicializado
- agent: claude-code
- files: AGENTS.md, .llm-wiki/, wiki/
- notes: approval_mode=plan; language=pt-BR

## [2026-09-20] research | SQLite serve para producao com escrita moderada?
- agent: claude-code
- files: wiki/questions/sqlite-em-producao.md, raw/research/
- approved_by: Ana Souza
- notes: mode=question; angles=2; candidates=8; approved=3; ingested=3; rounds=1

## [2026-09-20] ingest | Appropriate Uses For SQLite
- agent: claude-code
- files: wiki/sources/appropriate-uses-for-sqlite.md, wiki/concepts/concorrencia-de-escrita-no-sqlite.md
- approved_by: Ana Souza
- notes: disposition=New; pages=3

## [2026-09-20] ingest | Concurrent writes and "database is locked"
- agent: claude-code
- files: wiki/sources/concurrent-writes-database-is-locked.md, wiki/concepts/concorrencia-de-escrita-no-sqlite.md
- approved_by: Ana Souza
- notes: disposition=Update; pages=2

## [2026-09-20] ingest | Migracao de um cluster Postgres para SQLite distribuido com LiteFS
- agent: claude-code
- files: wiki/sources/migrei-postgres-para-sqlite-litefs.md
- approved_by: Ana Souza
- notes: disposition=New; pages=2

## [2026-09-20] capture | Pico de SQLITE_BUSY no servico de relatorios
- agent: claude-code
- files: raw/notes/2026-09-20-pico-de-sqlite-busy-no-servico-de-relatorios.md
- approved_by: Ana Souza
- notes: decisions=1; errors=1; facts=1; corrections=0; questions=1; redactions=1

## [2026-09-20] ingest | Pico de SQLITE_BUSY no servico de relatorios
- agent: claude-code
- files: wiki/sources/pico-de-sqlite-busy-no-servico-de-relatorios.md, wiki/concepts/concorrencia-de-escrita-no-sqlite.md, wiki/questions/sqlite-em-producao.md
- approved_by: Ana Souza
- notes: disposition=Update; pages=4

## [2026-09-20] publish | team-data-wiki 2026-09-20
- agent: claude-code
- files: dist/team-data-wiki/
- approved_by: Ana Souza
- notes: channel=install; raw=true
