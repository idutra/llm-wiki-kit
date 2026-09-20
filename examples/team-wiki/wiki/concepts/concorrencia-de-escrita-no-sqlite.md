---
title: Concorrência de escrita no SQLite
type: concept
status: reviewed
created: 2026-09-20
updated: 2026-09-20
sources:
  - raw/research/2026-09-20-appropriate-uses-for-sqlite.md
  - raw/research/2026-09-20-concurrent-writes-database-is-locked.md
  - raw/notes/2026-09-20-pico-de-sqlite-busy-no-servico-de-relatorios.md
  - raw/research/2026-09-20-migrei-postgres-para-sqlite-litefs.md
related:
  - wiki/questions/sqlite-em-producao.md
tags: [sqlite, concorrencia]
sensitivity: internal
concept_kind: concept
---

# Concorrência de escrita no SQLite

## Definição

O SQLite aceita leitores simultâneos sem limite, mas apenas **um escritor por vez**: "it will only allow
one writer at any instant in time" ([Appropriate Uses For SQLite §High Concurrency](../sources/appropriate-uses-for-sqlite.md)).
As demais escritas entram em fila; se a espera passar do `busy_timeout`, o cliente recebe `SQLITE_BUSY`.

## Como aparece nas fontes

- [Appropriate Uses For SQLite](../sources/appropriate-uses-for-sqlite.md) - a própria documentação diz que
  a fila não é problema quando "no lock lasts for more than a few dozen milliseconds", e recomenda um banco
  cliente/servidor quando o site é `write-intensive`.
- [Concurrent writes and "database is locked"](../sources/concurrent-writes-database-is-locked.md) - mede a
  degradação por número de escritores e nomeia a causa: "Long write transactions are killers of SQLite
  concurrency".
- [Pico de SQLITE_BUSY no serviço de relatórios](../sources/pico-de-sqlite-busy-no-servico-de-relatorios.md) -
  caso nosso: a transação segurava o lock por 4,1 s porque renderizava um PDF dentro dela.
- [Migração de um cluster Postgres para SQLite distribuído com LiteFS](../sources/migrei-postgres-para-sqlite-litefs.md) -
  mostra SQLite sustentando produção de tráfego alto, mas sem informar a carga de escrita; entra como
  evidência de viabilidade, não de limite.

## Posição atual do wiki

O número que importa não é escritas por segundo, é **lock-segundos por segundo**: a duração da transação
multiplicada pela frequência. Dezenas de escritas por segundo com transações de dezenas de milissegundos
ficam longe do limite; uma única transação de segundos derruba tudo, em qualquer volume.

Confiança: média. Sustenta-se em uma fonte oficial, um benchmark de terceiro e um caso nosso. Derrubaria
esta posição um caso com transações curtas que mesmo assim saturasse a escrita.

## Relações

- Aplicado em [SQLite serve para produção com escrita moderada?](../questions/sqlite-em-producao.md)

## Contradições e incertezas

Nenhuma contradição aberta entre as fontes. Elas divergem em ênfase, não em fato: a documentação fala em
quando trocar de banco, o benchmark e o nosso caso falam em como não chegar lá.

## Perguntas abertas

- Qual o limite de escrita do nosso hardware com WAL e transações curtas? (nota de sessão, não medido)
