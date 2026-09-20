---
source_url: session
collected: 2026-09-20
author: Ana Souza
agent: claude-code
title: Pico de SQLITE_BUSY no serviço de relatórios
kind: session-note
found_by: capture
repo: reporting-service
refs: [PR 412, src/db/writer.py:88]
capture: full
---

# Pico de SQLITE_BUSY no serviço de relatórios

## Contexto

O serviço de relatórios passou a devolver erro 500 intermitente no fim do dia. Suspeita inicial: volume
de escrita acima do que o SQLite aguenta.

## Decisões

- **Manter o SQLite e corrigir a transação, em vez de migrar para Postgres** - Porquê: a carga medida
  é de dezenas de escritas por segundo, dentro do que a documentação do projeto considera adequado;
  o problema estava na duração da transação, não no volume. Alternativas descartadas: migrar para
  Postgres agora (custo alto, sem evidência de que resolveria), e serializar tudo numa fila
  (esconderia a transação longa). Evidência: reported.

## Erros e correções

- **`SQLITE_BUSY` em rajada no fim do dia** - Causa: a geração do relatório abria a transação de
  escrita antes de renderizar o PDF e só commitava depois, segurando o lock por cerca de 4 segundos.
  Correção: renderizar fora da transação e abrir a escrita só para gravar o resultado. Como evitar:
  nenhuma transação de escrita deve conter trabalho de CPU ou de rede. Evidência: verified - tempo de
  transação medido antes (4,1 s) e depois (38 ms) em `src/db/writer.py:88`.

## Fatos verificados

- Com `busy_timeout` em 5000 ms, o erro vira espera e desaparece dos logs, mas a latência p99 sobe
  para o tempo da transação mais longa. Verificado por: teste de carga com 40 escritas por segundo,
  antes e depois do PR 412.

## Perguntas em aberto

- Qual é o limite de escrita por segundo do nosso hardware com WAL e transações curtas? - O que
  responderia: um teste de carga com transações de duração conhecida, que ainda não rodamos.
