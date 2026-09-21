# CHANGELOG

Formato: uma seção por versão fechada, da mais recente para a mais antiga. Versões seguem o semver do
pacote; o fechamento de cada uma está descrito em [`docs/convencao-de-branches.md`](docs/convencao-de-branches.md).

## 1.0.1 - 2026-09-20

Só documentação; nenhuma mudança de comportamento.

- `solution-draft.md` seção 10.1: a fase 6 (adoção num repositório de documentação real) fica
  especificada, com o protocolo de medição, as duas portas de aceite, o critério de parada explícito e a
  fronteira entre spec e wiki. Não iniciada.
- As fases 0 a 5 do roadmap ficam marcadas como concluídas com o fechamento na `1.0.0`.

## 1.0.0 - 2026-09-20

Fecha o desenvolvimento do kit. Nenhuma funcionalidade nova: consolida o que existe e registra o estado.

- `docs/estado-e-backlog.md`: o que foi medido (A/B de uma instância, testes ao vivo de `research`,
  `capture` e `publish`), o que **não** foi validado (uso real num acervo de time, fluxo completo de
  pesquisa, concorrência entre branches, escala acima de 20 páginas, quatro dos cinco agentes,
  instalação em máquina limpa) e o backlog com o motivo de cada corte.
- README declara o estado e aponta para esse documento.

O kit entrega: 2 skills (`wiki`, `wiki-query`), 11 referências carregadas sob demanda, 5 subagentes
somente leitura, `wiki_tools.py` com 8 subcomandos e sem dependências, empacotamento para APM,
`npx skills` e marketplace do Claude Code, um wiki de exemplo válido e 59 testes.

Retomar o projeto começa por adotar o padrão num repositório de documentação real, não por escrever mais
código; o roteiro está no fim do documento de estado.

## 0.6.0 - 2026-09-20

- `lint`: cada verificação tem severidade `error`, `warning` ou `info`, ajustável por wiki em
  `lint.severity` (`off` silencia). `check --fail-on LEVEL` decide o que quebra CI; sem ele vale
  `lint.fail_on`, e o padrão continua sendo `error`.
- Verificação `freshness`: página mais velha que o prazo da sua `volatility` (`high`, `medium`, `low`,
  `static`, prazos em `lint.freshness`). Nasce como `info`: é fila de revisão, não defeito.
- `publish` passa a preservar os nomes de diretório de `paths`. Um repositório de documentação que adota
  o wiki e mantém a sua pasta `docs/` publica em `references/docs/`, e a skill gerada cita esse nome.
  Antes, os links relativos das páginas quebravam e a montagem falhava.
- `references/init.md` ganha "Adotar um repositório que já tem documentação".
- `parse_yaml` aceita mapas aninhados de qualquer profundidade; antes o terceiro nível
  (`lint.freshness.high`) era achatado em silêncio.

**Mudanças de comportamento**: `sources:` apontando para fora de `raw/` e página duplicada no índice
passam de aviso a erro. `lint.severity` reverte qualquer uma das duas.

## 0.5.0 - 2026-09-20

- `docs/anatomia-do-repositorio.md`: como fica um repositório com LLM Wiki, camada por camada.
- `docs/uso-em-uma-semana.md`: passo a passo de uso, do `init` ao consumo em outro repositório.
- `examples/team-wiki/`: wiki de exemplo completo, gerado pelas próprias operações; passa em `check`,
  `manifest` e `publish`.
- `docs/convencao-de-branches.md`: `release/`, `hotfix/`, `feature/`, `bugfix/` e o fechamento de versão
  com commit de fechamento e tag.

## 0.4.0 - 2026-09-20

- Operação `capture`: lições de uma sessão de trabalho viram nota imutável em `raw/notes/`, com revisão
  humana e scanner de segredos antes da gravação; itens marcados `verified` ou `reported`.
- `wiki_tools.py scan <arquivo>|-`: padrões de segredo e PII, sem ecoar o valor encontrado.
- `wiki_tools.py --version` e a seção "Atualizar um wiki existente" em `references/init.md`.
- Template do consumidor ganha a seção "Devolver ao wiki".

## 0.3.0 - 2026-09-20

- Operação `research`: busca por ângulos em paralelo, lista de fontes sempre aprovada por humano, captura
  em `raw/research/` com proveniência, ingestão e síntese; modo tese com veredito.
- Subagente `wiki-research-agent`, somente leitura e sem shell.
- `wiki_tools.py seen <url>...`: URLs normalizadas contra `raw/` e `origin_url`.

## 0.2.0 - 2026-09-20

- As oito skills `wiki-*` viram duas: `wiki` (mantenedor, roteador com uma referência por operação) e
  `wiki-query` (leitor, somente leitura). O arquivamento vira a operação `archive`.
- Operação `publish` e `wiki_tools.py publish [--out] [--install REPO]`: o wiki vira skill somente leitura
  para outros repositórios.
- `wiki/manifest.md` e detecção de fonte alterada (`source-changed`).

## 0.1.0 - 2026-09-20

- Primeira versão: oito skills, quatro subagentes somente leitura, hook de sessão e `wiki_tools.py`.
