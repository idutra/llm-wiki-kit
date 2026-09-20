# Capturar: o que a sessão de trabalho ensinou vira fonte

Boa parte do que um time aprende nunca vira documento: a decisão tomada no meio de uma tarefa, o erro que custou uma tarde, o fato sobre um sistema que só se descobre mexendo nele. Isso morre com a sessão do agente. `capture` extrai esse material para uma **nota de sessão** imutável em `raw/`, que entra no wiki pelo `ingest` como qualquer outra fonte. É assim que o wiki aprende com o uso, e não só com o que alguém lembra de trazer.

Três regras próprias desta operação:

- **Opt-in, sempre.** Nada é capturado automaticamente. O agente pode oferecer; quem decide é o usuário, e ele vê a nota inteira antes de ela ser gravada.
- **A nota é passada pelo scanner antes de ir para `raw/`.** `raw/` é imutável e versionado: segredo gravado ali fica no histórico do git. Depois de gravar é tarde.
- **Nota não é transcrição.** Entra o que alguém vai precisar daqui a seis meses, escrito para quem não estava na sessão. Não entra a conversa, nem código que já está no repositório.

## Quando oferecer

Ao fim de uma sessão (ou de uma etapa longa) em que houve pelo menos um destes: decisão com alternativa descartada; erro com causa encontrada; fato sobre sistema, API ou processo verificado na prática; correção do usuário sobre algo que o wiki ou o agente afirmavam; pergunta que ficou sem resposta. Sessão rotineira sem nada disso: não ofereça.

## O que entra e o que não entra

| Entra | Não entra |
|---|---|
| Decisão, o porquê e as alternativas descartadas | Transcrição, histórico de comandos, diffs |
| Erro: sintoma, causa, correção, como evitar | Segredos, tokens, senhas, strings de conexão, dados pessoais |
| Fato verificado, com **como** foi verificado | Opinião sobre pessoas ou times |
| Correção a uma página do wiki (qual página, o que está errado) | Especulação sem verificação, a não ser marcada como `reported` |
| Pergunta em aberto e o que a responderia | Conteúdo de terceiros sob confidencialidade que o wiki não pode guardar |

Cada item precisa ficar de pé sozinho: quem ler só aquele item entende do que se trata, sem "como vimos acima".

## Passo 1 - Rascunhar a nota

Monte a nota na conversa, **sem gravar ainda**:

```
---
source_url: session
collected: <YYYY-MM-DD>
author: <nome do humano responsável pela sessão>
agent: <claude-code|cursor|codex|copilot|opencode>
title: <o que foi feito, em uma linha>
kind: session-note
found_by: capture
repo: <repositório onde o trabalho aconteceu>
refs: [<commits, PRs, issues, caminhos arquivo:linha>]
capture: full
---

# <título>

## Contexto
Duas a quatro frases: o que se queria fazer e por quê.

## Decisões
- **<decisão>** - Porquê: <...>. Alternativas descartadas: <...>. Evidência: verified | reported.

## Erros e correções
- **<sintoma>** - Causa: <...>. Correção: <...>. Como evitar: <...>. Evidência: verified | reported.

## Fatos verificados
- <fato> - Verificado por: <comando e saída resumida, arquivo:linha, link>.

## Correções ao wiki
- <página> afirma <X>; o observado foi <Y>. Verificado por: <...>.

## Perguntas em aberto
- <pergunta> - O que responderia: <fonte, teste, pessoa>.
```

Em **Decisões**, a evidência qualifica o *porquê*. Consequência que foi medida vai, separada, em "Fatos verificados"; assim uma decisão com justificativa `reported` não rebaixa o fato que a acompanha.

Material sensível misturado com material útil: se o item importa, **mantenha o item e troque o valor** por `<redacted: tipo>` ("verificado com o token de CI `<redacted: token>`"); não descarte em silêncio uma lição por causa do segredo ao lado dela. Se o trecho não ensina nada (credencial citada de passagem), fica de fora. Diga ao usuário o que omitiu.

`verified` = o agente ou o usuário conferiu nesta sessão (rodou, leu, mediu). `reported` = alguém afirmou e ninguém conferiu. A distinção sobrevive até a página do wiki. Seções vazias saem da nota.

## Passo 2 - Revisão humana e scanner

1. Mostre o rascunho ao usuário. Ele corta, corrige e aprova. Sem aprovação explícita, nada é gravado.
2. Passe o texto aprovado pelo scanner **antes** de gravar em `raw/` (grave primeiro fora do repositório, ou use stdin):

```
python .llm-wiki/scripts/wiki_tools.py scan <arquivo-temporario>      # ou:  ... scan -  < nota.md
```

   Saída com achado (`secret`, `pii`) e código 1: substitua o valor por `<redacted: tipo>`, mostre de novo ao usuário e rode outra vez. O scanner pega padrões conhecidos (chaves, tokens, blocos de chave privada, `senha=...`, strings de conexão com credencial, e-mails); **não** substitui a leitura humana. Nome de cliente, valor de contrato e dado interno sensível nenhum padrão pega.

## Passo 3 - Gravar

**Dentro do repositório do wiki:** grave em `raw/notes/<YYYY-MM-DD>-<slug>.md` (ou em `raw/<capture.raw_category>/`, se o `config.yml` tiver o bloco `capture:`). Nunca sobrescreva; nota gravada não se edita, corrige-se com outra nota.

**Em outro repositório** (o caso comum: o trabalho acontece onde o código está), a nota precisa chegar ao wiki. Em ordem de preferência, sempre com o ok do usuário:

1. O wiki está clonado na máquina e o usuário indica o caminho: grave em `<wiki>/raw/notes/` e **pare aí**. A ingestão acontece numa sessão no repositório do wiki, com o schema dele carregado.
2. Abra uma issue no repositório do wiki com a nota no corpo e o rótulo `wiki-capture` (`gh issue create`, ou o equivalente do host). Do lado do wiki, a issue é salva literalmente em `raw/notes/` e ingerida.
3. Entregue o markdown ao usuário para ele levar.

## Passo 4 - Ingerir

No repositório do wiki, siga `references/ingest.md` por inteiro. O que muda para nota de sessão:

- Página `wiki/sources/` com `source_meta.kind: other` e `origin_url: n/a`; o autor é o humano da sessão.
- Decisões e fatos propagam para as páginas de entidade e conceito que tocam. Item `reported` entra marcado como tal ("relatado em sessão, não verificado"); não vira fato.
- "Correções ao wiki" viram `Status: Disputed` na página afetada, com link para a nota, até alguém conferir a fonte original. Uma nota de sessão não sobrescreve uma fonte primária: ela a contesta.
- "Perguntas em aberto" viram páginas em `wiki/questions/` com `question_status: open`, que são a entrada natural da operação `research`.
- Se as lições se acumularem, proponha (operação `schema`) uma categoria própria, por exemplo `lessons: lesson`, com template. Não crie por conta própria.

## Passo 5 - Registrar

```
python .llm-wiki/scripts/wiki_tools.py manifest --write
python .llm-wiki/scripts/wiki_tools.py log-append --op capture --title "<título da nota>" --agent <agente> --files "raw/notes/<arquivo>" --approved-by "<humano que aprovou a nota>" --notes "decisions=<n>; errors=<n>; facts=<n>; corrections=<n>; questions=<n>; redactions=<n>"
python .llm-wiki/scripts/wiki_tools.py check
```

A captura e a ingestão têm entradas separadas no log (`capture`, depois `ingest`).

## Relatório

Nota gravada (caminho ou issue); itens por seção; redações feitas; páginas que a ingestão tocou ou, se a nota só foi entregue, onde ela está esperando.

## Específico por agente

- **Todos**: o `AGENTS.md` do wiki instrui o agente a oferecer `capture` ao fim de sessões com decisão, erro ou correção; é o lembrete que funciona em qualquer ferramenta.
- **Claude Code**: `/wiki capture`. Pode-se acrescentar um hook `Stop` que só imprime um lembrete; o pacote não instala esse hook, porque lembrete a cada resposta vira ruído.
- **Skill publicada** (`publish`): o template do consumidor traz a seção "Devolver ao wiki", que leva o agente consumidor a este mesmo formato de nota.
