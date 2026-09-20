---
title: Visão geral
type: synthesis
status: reviewed
created: 2026-09-20
updated: 2026-09-20
sources: []
related:
  - wiki/questions/sqlite-em-producao.md
  - wiki/concepts/concorrencia-de-escrita-no-sqlite.md
tags: [exemplo]
sensitivity: internal
confidence: medium
---

# Visão geral

## Escopo

O que este time apurou sobre escolha e operação da camada de persistência dos seus serviços. Hoje cobre
um assunto só: SQLite em produção. É um wiki de exemplo, pequeno de propósito.

## Teses centrais

- O limite prático do SQLite em aplicação web não é o volume de escrita, é a **duração** de cada
  transação de escrita. Ver [Concorrência de escrita no SQLite](concepts/concorrencia-de-escrita-no-sqlite.md).
- A decisão de trocar de banco precisa de carga medida. No nosso único caso real, a suspeita de volume
  estava errada e a causa era uma transação longa.

## Mapa do conhecimento

- Pergunta que originou o wiki: [SQLite serve para produção com escrita moderada?](questions/sqlite-em-producao.md)
- Conceito central: [Concorrência de escrita no SQLite](concepts/concorrencia-de-escrita-no-sqlite.md)
- Fontes externas: 3, todas de captura parcial. Nota de sessão própria: 1.

## Lacunas conhecidas

- Nenhum caso público medido na faixa de dezenas de escritas por segundo, que é justamente a nossa.
- Não sabemos o limite do nosso hardware com transações curtas; falta o teste de carga.
- Nada sobre replicação, backup ou restauração.

## Histórico de revisão

- 2026-09-20 - criado a partir da primeira rodada de `research` e da nota de sessão do serviço de relatórios.
