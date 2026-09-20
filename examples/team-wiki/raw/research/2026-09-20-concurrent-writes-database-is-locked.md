---
source_url: https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/
collected: 2026-09-20
published: 2025-02-01
author: Victor Skvortsov
title: SQLite concurrent writes and "database is locked" errors
found_by: research
research_question: wiki/questions/sqlite-em-producao.md
angle: contrarian
capture: partial
---

> Captura parcial: trechos citados. Benchmarks próprios do autor, medindo operações por segundo por
> número de threads.

A write transaction holds the lock and blocks other writes during the entire write transaction duration.
[...] Long write transactions are killers of SQLite concurrency.

O autor mede a degradação conforme o número de escritores concorrentes aumenta e mostra que o
`busy_timeout` transforma o erro `SQLITE_BUSY` em espera, em vez de falha, até o limite configurado.
