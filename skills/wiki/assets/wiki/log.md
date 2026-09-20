# Log do wiki

Registro cronológico append-only. Nunca edite entradas anteriores; apenas acrescente ao final.
Cabeçalho de entrada: `## [YYYY-MM-DD] <op> | <título>` com op em {init, ingest, query, archive, lint, index, export, schema}.
Últimas 5 entradas: `grep "^## \[" wiki/log.md | tail -5` (ou `rg "^## \[" wiki/log.md | Select-Object -Last 5` no PowerShell).

