---
title: Appropriate Uses For SQLite
type: source
status: reviewed
created: 2026-09-20
updated: 2026-09-20
sources:
  - raw/research/2026-09-20-appropriate-uses-for-sqlite.md
related:
  - wiki/concepts/concorrencia-de-escrita-no-sqlite.md
tags: [sqlite]
sensitivity: internal
confidence: medium
source_meta:
  author: SQLite project
  published: 2025-05-31
  collected: 2026-09-20
  origin_url: https://sqlite.org/whentouse.html
  kind: doc
---

# Appropriate Uses For SQLite

## Resumo

Página oficial do projeto SQLite sobre quando ele é adequado e quando convém um banco cliente/servidor. Trata leitura simultânea como ilimitada e escrita como exclusiva, e usa a duração do lock como critério prático. Sobre sites, diz que o SQLite atende bem tráfego baixo e médio.

## Claims extraídos

- Um escritor por vez, leitores simultâneos sem limite - [§High Concurrency](../../raw/research/2026-09-20-appropriate-uses-for-sqlite.md)
- A fila de escritores é aceitável enquanto nenhum lock passa de "a few dozen milliseconds" - [§High Concurrency](../../raw/research/2026-09-20-appropriate-uses-for-sqlite.md)
- Site `write-intensive` ou que precise de vários servidores: considerar banco cliente/servidor - [§Websites](../../raw/research/2026-09-20-appropriate-uses-for-sqlite.md)

## Entidades e conceitos mencionados

- [Concorrência de escrita no SQLite](../concepts/concorrencia-de-escrita-no-sqlite.md)

## Relação com o wiki

É a fonte primária do conceito: vem do próprio projeto e define o critério de duração do lock que o wiki adota.

## Perguntas abertas

- Não define `write-intensive` em números, o que deixa a decisão de troca sem limiar objetivo.
