---
title: Pico de SQLITE_BUSY no serviço de relatórios
type: source
status: reviewed
created: 2026-09-20
updated: 2026-09-20
sources:
  - raw/notes/2026-09-20-pico-de-sqlite-busy-no-servico-de-relatorios.md
related:
  - wiki/concepts/concorrencia-de-escrita-no-sqlite.md
tags: [sqlite]
sensitivity: internal
confidence: medium
source_meta:
  author: Ana Souza
  published: 2026-09-20
  collected: 2026-09-20
  origin_url: n/a
  kind: other
---

# Pico de SQLITE_BUSY no serviço de relatórios

## Resumo

Nota da sessão de trabalho que investigou erros 500 intermitentes no serviço de relatórios. A suspeita inicial era volume de escrita; a causa medida foi uma transação que segurava o lock por 4,1 s porque renderizava um PDF dentro dela.

## Claims extraídos

- Transação de escrita caiu de 4,1 s para 38 ms ao mover a renderização para fora dela - [nota §Erros e correções](../../raw/notes/2026-09-20-pico-de-sqlite-busy-no-servico-de-relatorios.md)
- Com `busy_timeout` de 5000 ms o erro some dos logs, mas a p99 sobe para a duração da transação mais longa - [nota §Fatos verificados](../../raw/notes/2026-09-20-pico-de-sqlite-busy-no-servico-de-relatorios.md)
- Decisão de manter o SQLite em vez de migrar (relatado em sessão, não verificado) - [nota §Decisões](../../raw/notes/2026-09-20-pico-de-sqlite-busy-no-servico-de-relatorios.md)

## Entidades e conceitos mencionados

- [Concorrência de escrita no SQLite](../concepts/concorrencia-de-escrita-no-sqlite.md)

## Relação com o wiki

Única fonte com números do nosso próprio ambiente. Confirma na prática o que as fontes externas afirmam e é o que transforma a resposta do wiki em recomendação operacional.

## Perguntas abertas

- Qual o limite de escrita do nosso hardware com transações curtas? Não medido.
