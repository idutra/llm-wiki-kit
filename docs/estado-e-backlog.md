# Estado do kit na 1.0.0: o que foi medido, o que não foi, o que ficou de fora

A versão 1.0.0 fecha o desenvolvimento do `llm-wiki-kit`. Este documento existe para que ninguém — nem
quem retomar o projeto, nem um agente lendo o repositório — precise adivinhar o que está provado e o que
é só coerente.

A regra que vale aqui: **não confunda "tem teste" com "funciona em produção"**. O kit tem 59 testes e
nenhum minuto de uso num corpus real de um time.

## O que existe

| Peça | O que é |
|---|---|
| `wiki` | Skill do mantenedor: roteia para uma referência por operação. 893 palavras em contexto |
| `wiki-query` | Skill do leitor, somente leitura. 486 palavras |
| 11 referências | `init`, `research`, `ingest`, `capture`, `archive`, `lint`, `index`, `search`, `export`, `publish`, `conventions`. Carregadas sob demanda |
| 5 subagentes | `wiki-research-agent`, `wiki-ingest-agent`, `wiki-query-agent`, `wiki-lint-agent`, `wiki-curator`. Todos somente leitura |
| `wiki_tools.py` | 1.086 linhas, só biblioteca padrão, nunca chama LLM: `check`, `index`, `manifest`, `publish`, `scan`, `seen`, `log-tail`, `log-append` |
| Empacotamento | APM, `npx skills` e marketplace do Claude Code; 5 alvos de agente |
| `examples/team-wiki/` | Wiki completo e válido, com teste que impede de apodrecer |
| Documentação | Anatomia do repositório, uso em uma semana, convenção de branches, este documento, e a spec original |

## O que foi medido

**Teste A/B, uma instância, 3 tarefas, 2 braços (Sonnet).** Wiki compilado contra os documentos crus
entregues como skill:

| | Wiki | Documentos crus |
|---|---|---|
| Asserções corretas | 30/32 | 22/32 |
| Citação da fonte | 3/3 | 0/3 |
| Lacuna declarada | 6/6 | 1/6 |
| Regra aplicada | 21/23 | 21/23 |
| Tokens por tarefa | +7% | referência |
| Tempo | +27% | referência |

Três leituras honestas deste número:

1. **O wiki não economiza tokens.** Mediu-se o contrário. O ganho está em lacuna sinalizada e citação
   conferível, não em custo.
2. **Empate onde mais se esperava ganho.** Aplicar a regra que a tarefa já menciona deu igual nos dois
   braços. A diferença apareceu no que ninguém perguntou.
3. **O gabarito foi escrito por quem construiu o wiki**, e não validado pelo time dono do conteúdo.
   Isso enviesa a favor do wiki. O número serve para orientar, não para vender.

**Visão de túnel, e a correção.** Na primeira rodada, com um tema só compilado, o agente consumidor não
enxergava as normas fora dele e concluía que não existiam. Foi daí que nasceu o `wiki/manifest.md`. Na
segunda rodada, com manifesto: 12/12, lendo 27 arquivos em vez de 34 e 136k tokens em vez de 219k.

**Testes ao vivo de operações isoladas:**

| Operação | Como foi testada | Resultado |
|---|---|---|
| `research` | Dois subagentes reais, ângulos `applied` e `contrarian`, busca na web | Contrato YAML cumprido; ângulos acharam fontes diferentes; ambos apontaram a mesma lacuna. ~75k tokens e ~90s por ângulo |
| `capture` | Subagente seguindo a referência sobre uma sessão com token, URL de banco e e-mail plantados | Nota saiu sem nenhum dos três; causa não confirmada marcada como `reported` |
| `publish` | Wiki gerado do zero a partir dos assets, mais o exemplo | Dois defeitos encontrados e corrigidos (nome inválido derivado do diretório, título vazio) |
| `check`, `manifest`, `scan`, `seen` | 59 testes automatizados | Verdes |

## O que **não** foi validado

Esta é a parte que importa mais.

- **Nenhum uso real.** O kit nunca operou o acervo de um time durante uma semana de trabalho de verdade.
- **Fluxo completo de `research`** com aprovação humana, captura e ingestão de ponta a ponta. Só os
  subagentes foram exercitados.
- **Ingestão de uma nota de `capture`**, e o canal por issue entre repositórios.
- **Nenhuma comparação contra um RAG.** O que está escrito sobre isso são argumentos, não medições.
- **Concorrência.** Vários desenvolvedores capturando em branches paralelas produzem conflito em
  `index.md` e `log.md`. A saída provável é regenerar o índice em vez de mesclar, e resolver o log
  mantendo os dois lados — mas isso nunca foi exercitado nem documentado.
- **Escala.** O maior wiki testado tem 20 páginas. O índice é lido inteiro; o limite prático estimado é
  de algumas centenas de páginas, e não foi medido.
- **Os cinco agentes.** Só Claude Code foi exercitado de verdade. Cursor, Codex, Copilot e OpenCode têm
  o formato compatível e nenhuma execução real.
- **Instalação.** `apm install` e `npx skills add` estão documentados a partir dos manifestos, não de uma
  instalação numa máquina limpa. Caminhos longos no Windows quebram o `apm install` local.

## Backlog: o que ficou de fora, e por quê

| Item | Por quê ficou de fora |
|---|---|
| `_index.md` por diretório | Resolve escala acima de algumas centenas de páginas. Nenhum wiki chegou perto |
| `publish --mode link` | Para wiki e consumidor na mesma máquina: aponta em vez de copiar, e nunca desatualiza. Só vale quando aparecer a dor |
| `init --embedded` (wiki dentro do repositório do produto) | Topologia diferente da que os repositórios reais usam. Foi proposto por um mal-entendido e descartado |
| `assess`: repositório contra wiki | Útil e caro; sem demanda concreta ainda |
| Ciclo de vida: arquivar página vencida | O `freshness` sinaliza; arquivar exige decidir o que fazer com os links |
| Curador de feedback, hub multi-wiki, especialistas com allowlist | Vêm do [nvk/llm-wiki](https://github.com/nvk/llm-wiki), que é ferramenta de pesquisa pessoal. Não se aplicam a conhecimento de time |
| `qmd` como motor de busca | Documentado em `references/search.md`, nunca configurado |
| Modelos de CI prontos | `check --fail-on` já serve; falta o arquivo de workflow pronto para copiar |

## Se for retomar

O próximo passo **não é código**. É adotar o padrão em um repositório de documentação real. A fase está
especificada em [`solution-draft.md`, seção 10.1](solution-draft.md#101-fase-6-em-detalhe), com as duas
portas de aceite e o critério de parada. Em resumo:

1. `init` com `paths.raw` apontando para a pasta de documentos que já existe, sem mover nada.
2. `manifest --write`: o catálogo inteiro fica visível no primeiro dia, mesmo sem nenhuma página compilada.
3. `publish` para os repositórios que consomem aquele conhecimento.
4. Medir, antes de compilar qualquer página, se os agentes passam a citar documento certo em vez de
   inventar. Esse é o teste que decide se o padrão se paga.
5. Só então compilar as cinco ou dez páginas dos assuntos mais perguntados, e medir de novo.

Se o passo 4 não mostrar diferença, o problema não é o kit, e construir mais kit não resolve.
