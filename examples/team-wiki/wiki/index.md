# Índice do wiki

Catálogo de todas as páginas, por categoria. Uma linha por página: link, resumo de uma linha, metadados.
Mantido pelo agente em toda operação de ingest, archive e lint. Leia este arquivo primeiro ao responder perguntas.

## Overview

- [Visão geral](overview.md) - O que o time apurou sobre persistência; hoje só SQLite em produção (sources: 0, updated: 2026-09-20)

## Sources

- [Appropriate Uses For SQLite](sources/appropriate-uses-for-sqlite.md) - Documentação oficial: um escritor por vez e quando trocar por banco cliente/servidor (sources: 1, updated: 2026-09-20)
- [Concurrent writes and "database is locked"](sources/concurrent-writes-database-is-locked.md) - Benchmark de terceiro: transação longa, não volume, é o que mata a concorrência (sources: 1, updated: 2026-09-20)
- [Migração de um cluster Postgres para SQLite distribuído com LiteFS](sources/migrei-postgres-para-sqlite-litefs.md) - Relato de migração real para SQLite em produção, sem informar carga de escrita (sources: 1, updated: 2026-09-20)
- [Pico de SQLITE_BUSY no serviço de relatórios](sources/pico-de-sqlite-busy-no-servico-de-relatorios.md) - Caso nosso: lock de 4,1 s causado por render de PDF dentro da transação (sources: 1, updated: 2026-09-20)

## Entities

(vazio)

## Concepts

- [Concorrência de escrita no SQLite](concepts/concorrencia-de-escrita-no-sqlite.md) - Um escritor por vez; o limite prático é lock-segundos por segundo, não escritas/s (sources: 4, updated: 2026-09-20)

## Syntheses

(vazio)

## Comparisons

(vazio)

## Questions

- [SQLite serve para produção com escrita moderada?](questions/sqlite-em-producao.md) - [Archived] Sim, com transações curtas; falta evidência pública na nossa faixa de carga (sources: 0, updated: 2026-09-20)

## Outputs

(vazio)
