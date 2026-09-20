---
title: Migração de um cluster Postgres para SQLite distribuído com LiteFS
type: source
status: reviewed
created: 2026-09-20
updated: 2026-09-20
sources:
  - raw/research/2026-09-20-migrei-postgres-para-sqlite-litefs.md
related:
  - wiki/concepts/concorrencia-de-escrita-no-sqlite.md
tags: [sqlite]
sensitivity: internal
confidence: medium
source_meta:
  author: Kent C. Dodds
  published: 2022-11-21
  collected: 2026-09-20
  origin_url: https://kentcdodds.com/blog/i-migrated-from-a-postgres-cluster-to-distributed-sqlite-with-litefs
  kind: article
---

# Migração de um cluster Postgres para SQLite distribuído com LiteFS

## Resumo

Relato de uma migração real de produção, de um cluster Postgres para SQLite distribuído com LiteFS, num site de tráfego alto. Descreve o processo, o ganho de latência de leitura por proximidade do banco e os problemas que apareceram depois, ligados à replicação entre regiões.

## Claims extraídos

- A migração rodou em cerca de 1h15 e, feita ela, "everything else went off pretty much without issue" - [post](../../raw/research/2026-09-20-migrei-postgres-para-sqlite-litefs.md)

## Entidades e conceitos mencionados

- [Concorrência de escrita no SQLite](../concepts/concorrencia-de-escrita-no-sqlite.md)

## Relação com o wiki

É o contraponto aplicado: mostra SQLite sustentando produção de verdade. Não mede escrita por segundo, então não responde à nossa pergunta; entra como evidência de viabilidade, não de limite.

## Perguntas abertas

- Qual era a carga de escrita do site? O relato não informa.
