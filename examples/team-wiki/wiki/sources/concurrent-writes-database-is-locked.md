---
title: Concurrent writes and "database is locked"
type: source
status: reviewed
created: 2026-09-20
updated: 2026-09-20
sources:
  - raw/research/2026-09-20-concurrent-writes-database-is-locked.md
related:
  - wiki/concepts/concorrencia-de-escrita-no-sqlite.md
tags: [sqlite]
sensitivity: internal
confidence: medium
source_meta:
  author: Victor Skvortsov
  published: 2025-02-01
  collected: 2026-09-20
  origin_url: https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/
  kind: benchmark
---

# Concurrent writes and "database is locked"

## Resumo

Artigo com benchmarks próprios de escrita concorrente em SQLite, medindo operações por segundo conforme o número de threads. Explica o papel do `busy_timeout` e atribui a perda de concorrência à duração das transações de escrita, não ao número de escritores.

## Claims extraídos

- "Long write transactions are killers of SQLite concurrency" - [artigo](../../raw/research/2026-09-20-concurrent-writes-database-is-locked.md)
- A transação de escrita segura o lock durante toda a sua duração - [artigo](../../raw/research/2026-09-20-concurrent-writes-database-is-locked.md)
- `busy_timeout` troca o erro `SQLITE_BUSY` por espera, até o limite configurado - [artigo](../../raw/research/2026-09-20-concurrent-writes-database-is-locked.md)

## Entidades e conceitos mencionados

- [Concorrência de escrita no SQLite](../concepts/concorrencia-de-escrita-no-sqlite.md)

## Relação com o wiki

Confirma e quantifica o que a documentação oficial afirma em prosa. Foi a fonte que fez o wiki trocar "escritas por segundo" por duração da transação como medida.

## Perguntas abertas

- Os benchmarks usam transações sintéticas; não há equivalente com carga de aplicação real.
