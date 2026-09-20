---
source_url: https://kentcdodds.com/blog/i-migrated-from-a-postgres-cluster-to-distributed-sqlite-with-litefs
collected: 2026-09-20
published: 2022-11-21
author: Kent C. Dodds
title: I Migrated from a Postgres Cluster to Distributed SQLite with LiteFS
found_by: research
research_question: wiki/questions/sqlite-em-producao.md
angle: applied
capture: partial
---

> Captura parcial: trechos citados. Relato de migração de produção de um site pessoal de tráfego alto,
> com cerca de meio milhão de linhas na tabela principal.

The whole thing took about an hour and fifteen minutes to run the migration script. But once that was
finished, everything else went off pretty much without issue.

O autor relata ganhos de latência de leitura por ter o banco no mesmo host da aplicação, e descreve os
problemas que encontrou depois da migração, ligados à replicação entre regiões.
