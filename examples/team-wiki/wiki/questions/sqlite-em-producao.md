---
title: SQLite serve para produção com escrita moderada?
type: question
status: reviewed
created: 2026-09-20
updated: 2026-09-20
sources: []
related:
  - wiki/concepts/concorrencia-de-escrita-no-sqlite.md
tags: [sqlite]
sensitivity: internal
question_status: partial
archived_from: research
---

# SQLite serve para produção com escrita moderada?

## Pergunta

Um engenheiro do time perguntou, em 2026-09-20, se o SQLite aguenta uma aplicação web com dezenas de
escritas por segundo, ou se já é caso de banco cliente/servidor.

## Resposta

Sim, desde que cada transação de escrita seja curta. A restrição do SQLite é um escritor por vez, e a
[documentação do projeto](../sources/appropriate-uses-for-sqlite.md) considera a fila aceitável enquanto
nenhum lock passa de algumas dezenas de milissegundos. O que satura não é a frequência, é a duração:
ver [Concorrência de escrita no SQLite](../concepts/concorrencia-de-escrita-no-sqlite.md).

No único caso nosso, o problema atribuído a volume era uma transação de 4,1 s; depois da correção, a
mesma carga passou a rodar sem erro
([nota de sessão](../sources/pico-de-sqlite-busy-no-servico-de-relatorios.md)).

## Confiança e lacunas

Resposta parcial. Nenhuma das fontes públicas mede exatamente a nossa faixa de carga: os relatos são de
escala muito maior ou de benchmarks sintéticos com dezenas de threads. Falta também um postmortem de quem
abandonou o SQLite por escrita moderada, que seria a evidência contrária mais forte.

## Próximos passos sugeridos

- Rodar o teste de carga do nosso hardware com transações de duração conhecida.
- Uma segunda rodada de `research` só sobre a lacuna: casos medidos na faixa de dezenas de escritas/s.

## Páginas citadas

- [Concorrência de escrita no SQLite](../concepts/concorrencia-de-escrita-no-sqlite.md)
- [Appropriate Uses For SQLite](../sources/appropriate-uses-for-sqlite.md)
- [Concurrent writes and "database is locked"](../sources/concurrent-writes-database-is-locked.md)
- [Pico de SQLITE_BUSY no serviço de relatórios](../sources/pico-de-sqlite-busy-no-servico-de-relatorios.md)
