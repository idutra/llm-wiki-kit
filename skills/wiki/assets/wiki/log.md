# Log do wiki

Registro cronológico append-only. Nunca edite entradas anteriores; apenas acrescente ao final.
Cabeçalho de entrada: `## [YYYY-MM-DD] <op> | <título>` com uma das operações válidas listadas no `AGENTS.md`. Registre sempre por `wiki_tools.py log-append`, que valida a operação.
Últimas 5 entradas: `grep "^## \[" wiki/log.md | tail -5` (ou `rg "^## \[" wiki/log.md | Select-Object -Last 5` no PowerShell).

