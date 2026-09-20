# LLM Wiki Kit - Proposta e Implementation Spec

| Campo | Valor |
|---|---|
| Documento | Proposta de solução + especificação de implementação (POC) |
| Pacote | `llm-wiki-kit` v0.2.0 (`apm.yml`, `.claude-plugin/plugin.json`) |
| Marketplace | `idutra-agent-plugins` (`.claude-plugin/marketplace.json`) |
| Autor | Igor Dutra |
| Data | 2026-09-20 |
| Status | Draft |

Este documento é a referência citada por `hooks/hooks.json`, `skills/wiki-init/SKILL.md` (seção Governança) e `skills/wiki-conventions/SKILL.md` (versionamento do pacote). Ele descreve o que **já existe** no repositório `llm-wiki-poc` e o que falta para o POC. Onde o texto afirma algo sobre ferramentas externas (APM, `npx skills`, Claude Code, Cursor, Codex, Copilot), a seção 2 indica a fonte verificada e a data.

---

## 0. Mudanças na v0.2.0 (leia antes do resto)

As seções 1 a 11 descrevem a v0.1.0, com oito skills `wiki-*`. A v0.2.0 mantém todo o comportamento descrito, mas muda o empacotamento e acrescenta uma operação. Onde o texto abaixo disser "skill `wiki-<operação>`", leia "skill `wiki`, operação `<operação>`, referência `skills/wiki/references/<operação>.md`".

| Mudança | Antes (0.1.0) | Agora (0.2.0) | Motivo |
|---|---|---|---|
| Skills | 8 skills `wiki-*`, 8 descrições sempre em contexto | 2 skills: `wiki` (mantenedor, roteador + 9 referências sob demanda) e `wiki-query` (leitor, somente leitura) | Descrições parecidas disputam o disparo e custam tokens em toda sessão; progressive disclosure carrega só a operação pedida |
| Arquivamento | Passo 4 de `wiki-query` | Operação `archive` da skill `wiki` | `wiki-query` passa a ser estritamente somente leitura |
| Assets do init | `skills/wiki-init/assets/` | `skills/wiki/assets/` | Consequência da consolidação |
| Manifesto de fontes | não existia | `wiki/manifest.md` via `wiki_tools.py manifest --write`; `check` emite `source-changed` e `manifest` | O índice diz o que o wiki já sabe; o manifesto diz o que existe para saber, e o hash acusa fonte alterada |
| Publicação | não existia | Operação `publish` + `wiki_tools.py publish [--out] [--install REPO]`: monta o wiki como skill somente leitura (`SKILL.md`, `references/wiki`, `references/raw`, `VERSION.md`) | É como o conhecimento chega aos outros repositórios e às outras ferramentas sem ninguém lembrar de consultar o wiki |
| Log | 8 operações | + `publish` | Auditoria de o que saiu do repositório |
| Testes | 13 | 27 (`python -m unittest discover -s tests`) | Manifesto e publish cobertos |

Guardas do `publish`: recusa com erro no `check`, sem `publish.description`, com página acima de `publish.max_sensitivity`, ou com link que não resolve dentro da skill montada. `raw/` não tem classificação de sensibilidade; distribuí-lo (`include_raw: true`) é decisão humana.

Próximos itens do roadmap do kit, fora deste documento: `research` (subagentes somente leitura por ângulo, lista de fontes aprovada por humano, captura em `raw/` com proveniência), `capture` (lições de sessão viram fonte), severidade e `--fail-on` no lint, frescor por volatilidade, `_index.md` por diretório.

---

## 1. Resumo executivo e problema

### 1.1 Problema

Times de produto e engenharia acumulam conhecimento em fontes dispersas (documentos internos, transcrições de reunião, artigos, PDFs, threads). Quando alguém pergunta "o que já sabemos sobre X", a resposta depende de memória individual ou de buscas manuais. Agentes de código (Claude Code, Cursor, Codex, Copilot) já estão nas máquinas dos engenheiros, mas sem disciplina compartilhada cada sessão reinventa a estrutura, escreve sem rastreabilidade e não deixa trilha de auditoria.

### 1.2 Proposta

Empacotar o padrão **LLM Wiki** (Andrej Karpathy) como um conjunto instalável de **skills** e **subagentes** que funciona nos quatro agentes usados na empresa. O agente vira um mantenedor disciplinado de uma base de conhecimento em markdown, versionada em git:

- `raw/` guarda fontes imutáveis;
- `wiki/` guarda páginas compiladas, interligadas, com frontmatter e citações para `raw/`;
- `AGENTS.md` é o schema (regras, convenções, workflows) que todo agente lê;
- `wiki/index.md` e `wiki/log.md` dão navegação e auditoria;
- um helper determinístico (`wiki_tools.py`) valida links, frontmatter, índice e log sem chamar LLM.

O pacote é distribuído como **Plugin collection** do Claude Code (`.claude-plugin/plugin.json` + `skills/` + `agents/` + `hooks/`) e consumido por três canais: `apm install` (Microsoft APM, todos os targets), `npx skills add` (só skills), e marketplace privado do Claude Code.

### 1.3 O que já está pronto

| Item | Estado |
|---|---|
| 8 skills em `skills/*/SKILL.md` (init, ingest, query, lint, index, search, export, conventions) | escritas, frontmatter conforme agentskills.io, ASCII-only |
| 4 subagentes somente leitura em `agents/*.md` | escritos, com `tools`/`disallowedTools`/`maxTurns` (Claude, Copilot) e `readonly: true` (Cursor) |
| Assets do `wiki-init` (AGENTS.md, CLAUDE.md, config.yml, 7 templates, index/log/overview, `wiki_tools.py`) | escritos; `wiki_tools.py` testado em Python 3.14 (check, index, log-append, log-tail) |
| `apm.yml` metadata-only com `targets`, `includes`, bloco `marketplace` | escrito, conforme manifest schema v0.3 |
| `.claude-plugin/plugin.json` e `marketplace.json` | escritos, conforme schema do Claude Code |
| `hooks/hooks.json` (SessionStart, imprime últimas 3 entradas do log) | escrito, formato Claude Code |
| Este documento | este arquivo |

### 1.4 O que falta (ver seção 10)

Repositório git interno com tag `v0.1.0`, teste de instalação nos quatro agentes, primeiro wiki piloto com 10 a 20 fontes reais, CHANGELOG, pipeline de release (`apm pack`, `claude plugin validate --strict`), e decisão sobre hospedagem (GitHub Enterprise, Azure DevOps, GitLab).

---

## 2. O que foi confirmado sobre APM e `npx skills`

Verificação feita em 2026-09-19 e 2026-09-20 lendo os arquivos-fonte abaixo. Nada nesta seção é de memória.

### 2.1 APM - Agent Package Manager (Microsoft)

| Aspecto | Confirmado | Fonte |
|---|---|---|
| Repositório e docs | `github.com/microsoft/apm`; docs em `microsoft.github.io/apm`. Criado por Daniel Meppiel. Open source. | [README](https://raw.githubusercontent.com/microsoft/apm/main/README.md) |
| Targets suportados | Copilot, Claude Code, Grok Build, Cursor, OpenCode, Codex, Gemini, Windsurf, Kiro (+ `antigravity`, `agent-skills`). | README; [manifest-schema.md](https://raw.githubusercontent.com/microsoft/apm/main/docs/src/content/docs/reference/manifest-schema.md) seção 3.6 |
| Instalação do CLI | macOS: `brew install apm`. Linux/macOS: `curl -sSL https://aka.ms/apm-unix \| sh`. Windows: `irm https://aka.ms/apm-windows \| iex`, `winget install --id Microsoft.APM --exact --source winget`, `scoop`, ou `pip install apm-cli` (Python 3.10+). | README, seção Get Started |
| Manifesto `apm.yml` | v0.3 Working Draft (2026-05-20). Obrigatórios: `name`, `version`. Opcionais usados por nós: `description`, `author`, `license`, `targets`, `includes`, `marketplace`. `targets` aceita `copilot`, `claude`, `cursor`, `codex` (entre outros); valores desconhecidos são erro de parse. `includes` em forma de lista é "explicit path list (strongest governance)" e é a única forma aceita quando `policy.manifest.require_explicit_includes: true`. | manifest-schema.md seções 2, 3.6, 3.9 |
| Bloco `marketplace` | `owner.name` obrigatório; `output` padrão `.claude-plugin/marketplace.json`; `metadata` livre; `build.tagPattern` padrão `v{version}`; `packages[]` com `name`, `source` (`./` local dispensa `version`/`ref`), `description`, `tags`, `keywords`, `category`. Chaves desconhecidas são rejeitadas. `apm pack` gera o `marketplace.json`. | manifest-schema.md seção 7 |
| Tipos de pacote | Seis layouts. O nosso é **Plugin collection** (`plugin.json` sem `$schema` reconhecido + `skills/` + `agents/`). Regra crítica: "When plugin signals coexist with an eligible apm.yml, the APM layout wins. An apm.yml is eligible when the root also has `.apm/` or the manifest declares APM or MCP dependencies. To intentionally select a plugin layout, omit apm.yml or keep it metadata-only". Por isso nosso `apm.yml` não tem `dependencies` nem `.apm/`. | [package-types.md](https://raw.githubusercontent.com/microsoft/apm/main/docs/src/content/docs/reference/package-types.md) |
| Regras do Plugin collection | Caminhos declarados em `plugin.json` (`skills`, `agents`, `hooks`) são requisitos: se faltarem, `apm install` sai com erro antes de escrever. Chave declarada substitui o scan do diretório padrão. `--skill <nome>` seleciona skills por nome ou caminho. | package-types.md, seção Plugin collection |
| Regras de skills | `name` do frontmatter deve bater com o diretório; `description` deve existir; **todos os valores do frontmatter devem ser ASCII**. | package-types.md, seção Skill collection |
| Instalação de pacote | `apm install <owner>/<repo>#<tag>`; `apm install <host>/<owner>/<repo>` para GHE, GitLab, Azure DevOps, Bitbucket, Gitea; `--skill` (repetível, persistido em `apm.yml`/`apm.lock.yaml`); `--target claude,cursor`; `--frozen` (equivalente a `npm ci`); `--update`; `--dry-run`. `ref:` aceita semver range (`^0.1.0`) resolvido contra tags `v{version}`. | [install.md](https://raw.githubusercontent.com/microsoft/apm/main/docs/src/content/docs/reference/cli/install.md); manifest-schema.md 4.1.2 |
| Marketplace | `apm marketplace add <owner>/<repo>`; `apm install <pacote>@<marketplace>`. | README |
| Governança | `apm.lock.yaml` com hashes; `apm audit` (scan de Unicode oculto, drift); `apm lock export --format cyclonedx\|spdx` (SBOM); `apm-policy.yml` com herança enterprise > org > repo. | README, seção Secure by default / Governed by policy |
| Versionamento de marketplace | `marketplace.versioning.strategy`: `lockstep` (padrão), `tag_pattern`, `per_package`. `apm pack --check-versions --dry-run` valida antes da tag. Para Plugin collection sem `apm.yml`, usa `plugin.json.version`. | [versioning-strategies.md](https://raw.githubusercontent.com/microsoft/apm/main/docs/src/content/docs/producer/versioning-strategies.md) |
| Mapeamento por target | `claude`: `CLAUDE.md`; `cursor`: `.cursor/rules/`, `.cursor/agents/`, `.cursor/skills/`; `codex`: `AGENTS.md`, `.agents/skills/`, `.codex/agents/`; `copilot`: `AGENTS.md`, `.github/skills/`, `.github/agents/`, `.github/hooks/`. | manifest-schema.md 3.6; package-types.md |

### 2.2 `skills` CLI (Vercel Labs) - "npx skills add"

O que o pedido chama de "skillsnpm" é o pacote npm **`skills`**, mantido pela Vercel Labs, invocado como `npx skills`.

| Aspecto | Confirmado | Fonte |
|---|---|---|
| Repositório e diretório | `github.com/vercel-labs/skills`; diretório público em `skills.sh`; especificação em `agentskills.io`. Licença MIT. | [README](https://raw.githubusercontent.com/vercel-labs/skills/main/README.md) |
| Agentes suportados | 79+ agentes, incluindo Claude Code (`.claude/skills/`), Cursor (`.agents/skills/`), Codex (`.agents/skills/`), GitHub Copilot (`.agents/skills/`). | README, tabela Supported Agents |
| Fontes aceitas | `owner/repo` (GitHub), URL GitHub completa (inclusive `tree/<ref>/skills/<nome>`), URL GitLab, Azure DevOps (`https://dev.azure.com/org/project/_git/repo`), qualquer URL git (`git@...`, `ssh://`), caminho local, URL direta de `SKILL.md` ou `.zip/.tar.gz`. | README, Source Formats |
| Repositórios privados | Mesmo comando; usa credential helper do git, depois `gh`, depois SSH. `GITHUB_TOKEN`/`GH_TOKEN` opcionais. | README, Private Repositories |
| Opções | `-g` (global), `-a <agente>` (repetível ou `'*'`), `-s/--skill <nome>` (repetível ou `'*'`), `--list`, `--copy` (cópia em vez de symlink), `-y`, `--all`. | README, Options |
| Outros comandos | `npx skills list`, `find`, `remove`, `update`, `init`, `use`. | README, Other Commands |
| Descoberta | `skills/<nome>/SKILL.md` (até 3 níveis), diretórios de agentes, raiz com `SKILL.md`. Também lê `.claude-plugin/plugin.json` e `marketplace.json` para descobrir skills declaradas. | README, Skill Discovery / Plugin Manifest Discovery |
| Frontmatter | Obrigatórios `name` (a-z, 0-9, hífen, máx 64, igual ao diretório) e `description` (máx 1024). Opcionais `license`, `compatibility` (máx 500), `metadata` (map string->string), `allowed-tools`. `metadata.internal: true` oculta a skill. | [agentskills.io/specification](https://agentskills.io/specification); README |
| Limitação central | Instala **somente skills**. Não instala `agents/` nem `hooks/`. Recursos por agente: hooks só em Claude Code, Cline, Kiro; `context: fork` só em Claude Code. | README, Compatibility |
| Telemetria | Anônima; desligar com `DISABLE_TELEMETRY=1` ou `DO_NOT_TRACK=1`. Para repos não públicos no GitHub, identificadores de fonte podem ser enviados. | README, Telemetry |
| Relação com APM | O README do APM se posiciona como drop-in: `apm install vercel-labs/agent-skills` equivale a `npx skills add`, acrescentando manifesto e lockfile. | README do APM |

### 2.3 Claude Code (plugin, marketplace, agentes)

| Aspecto | Confirmado | Fonte |
|---|---|---|
| `plugin.json` | Só `name` é obrigatório. Campos usados por nós: `version`, `description`, `author{name,url}`, `homepage`, `repository`, `license`, `keywords`, `skills` (string ou array; **adiciona** ao scan de `skills/`), `agents` (array; **substitui** `agents/`), `hooks` (caminho). Campos desconhecidos são ignorados; `claude plugin validate --strict` trata avisos como erro. | [plugins-reference](https://code.claude.com/docs/en/plugins-reference.md), Plugin manifest schema |
| Agentes de plugin | Frontmatter suportado: `name`, `description`, `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`, `background`, `omitClaudeMd`, `isolation`. Não suportam `hooks`, `mcpServers`, `permissionMode`. Aparecem como `llm-wiki-kit:wiki-ingest-agent`. | plugins-reference, Agents |
| Hooks de plugin | `hooks/hooks.json` na raiz do plugin ou inline em `plugin.json`. | plugins-reference, Hooks |
| `marketplace.json` | Obrigatórios `name` (kebab-case, nomes reservados proibidos), `owner{name}`, `plugins[]{name, source}`. `source: "./"` (caminho relativo) é aceito. `$schema` é ignorado em runtime. `version` na entrada ou no `plugin.json` fixa a versão; sem ambos, usa SHA do commit. | [plugin-marketplaces](https://code.claude.com/docs/en/plugin-marketplaces.md), Marketplace schema / Version management |
| Comandos | `claude plugin marketplace add <owner/repo \| url>`, `claude plugin install <plugin>@<marketplace> [--scope user\|project\|local]`, `claude plugin update`, `claude plugin uninstall`, `claude plugin validate <dir> --strict`, `claude plugin list`, `enable`, `disable`. | plugins-reference, CLI commands reference |
| Privado | Usa credential helpers do git; `owner/repo` clona via SSH por padrão (`CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` para HTTPS). GitLab e Bitbucket suportados por URL. `extraKnownMarketplaces` em `.claude/settings.json` registra o marketplace ao confiar na pasta. Distribuição por Organization settings (Team/Enterprise). | plugin-marketplaces, Private repositories / Require marketplaces |

### 2.4 Cursor, Codex, Copilot (skills e subagentes)

| Agente | Confirmado | Fonte |
|---|---|---|
| Cursor | Skills em `.agents/skills/` e `.cursor/skills/` (projeto), `~/.agents/skills/` e `~/.cursor/skills/` (usuário); por compatibilidade também lê `.claude/skills/` e `.codex/skills/`. Subagentes em `.cursor/agents/` (também `.claude/agents/` e `.codex/agents/`); frontmatter: `name`, `description`, `model`, `readonly`, `is_background`. | [cursor.com/docs/context/skills](https://cursor.com/docs/context/skills); [cursor.com/docs/context/subagents](https://cursor.com/docs/context/subagents) |
| Codex | Lê `.agents/skills` do CWD até a raiz do repo, `~/.agents/skills`, `/etc/codex/skills`. Invocação explícita `$nome-da-skill`; `allow_implicit_invocation` controla o disparo implícito. | [developers.openai.com/codex/skills](https://developers.openai.com/codex/skills) |
| Copilot | Skills de projeto em `.github/skills`, `.claude/skills` ou `.agents/skills`; pessoais em `~/.copilot/skills` ou `~/.agents/skills`. `gh skill` no GitHub CLI instala skills de repositórios. | [docs.github.com about-agent-skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) |

Não verificado nesta rodada (marcado como decisão em aberto na seção 11): formato de hooks do Cursor e do Codex; suporte a `maxTurns` em agentes do Copilot; se o Codex carrega `.codex/agents/` como subagentes em todas as versões.

---

## 3. Arquitetura

### 3.1 Camadas

O LLM Wiki tem três camadas com direitos de escrita distintos:

| Camada | Diretório | Quem escreve | Regra |
|---|---|---|---|
| **Raw** | `raw/<categoria>/`, `raw/assets/` | Humano (ou agente ao capturar URL/colagem, uma vez) | Imutável. Nunca editar, renomear ou apagar. |
| **Wiki** | `wiki/sources/`, `entities/`, `concepts/`, `syntheses/`, `comparisons/`, `questions/`, `outputs/`, `index.md`, `log.md`, `overview.md` | Agente (orquestrador da skill); humano revisa | Toda afirmação rastreável a `raw/`. Toda escrita atualiza `index.md` e `log.md`. |
| **Schema** | `AGENTS.md`, `CLAUDE.md`, `.llm-wiki/config.yml`, `.llm-wiki/templates/`, `.llm-wiki/scripts/wiki_tools.py` | Humano com o agente (operação `schema`) | Co-evoluído com aprovação humana e registro no log. |

Em volta dessas camadas fica o **pacote** (`llm-wiki-kit`), que é instalado no ambiente do agente e não no repositório do wiki (exceto quando o time opta por escopo de projeto). O pacote traz as skills que sabem operar as três camadas e os subagentes somente leitura que paralelizam leitura e revisão.

### 3.2 Diagrama

```mermaid
flowchart TB
  subgraph pkg["Pacote llm-wiki-kit (instalado no agente)"]
    direction LR
    S1[wiki-init]
    S2[wiki-ingest]
    S3[wiki-query]
    S4[wiki-lint]
    S5[wiki-index]
    S6[wiki-search]
    S7[wiki-export]
    S8[wiki-conventions]
    A1[wiki-ingest-agent RO]
    A2[wiki-query-agent RO]
    A3[wiki-lint-agent RO]
    A4[wiki-curator RO]
    H[hooks/hooks.json SessionStart]
  end

  subgraph repo["Repositório do wiki (git)"]
    subgraph schema["Schema"]
      AG[AGENTS.md]
      CL[CLAUDE.md -> @AGENTS.md]
      CFG[.llm-wiki/config.yml]
      TPL[.llm-wiki/templates/*.md]
      TOOLS[.llm-wiki/scripts/wiki_tools.py]
    end
    subgraph raw["Raw (imutável)"]
      R1[raw/categoria/YYYY-MM-DD-slug.ext]
      R2[raw/assets/]
    end
    subgraph wiki["Wiki (compilado)"]
      IDX[wiki/index.md]
      LOG[wiki/log.md]
      OV[wiki/overview.md]
      SRC[wiki/sources/]
      ENT[wiki/entities/]
      CON[wiki/concepts/]
      SYN[wiki/syntheses/]
      CMP[wiki/comparisons/]
      QST[wiki/questions/]
      OUT[wiki/outputs/]
    end
  end

  Human((Humano)) -->|adiciona fonte| R1
  Human -->|aprova plano / PR| wiki
  S1 -->|cria| schema
  S1 -->|cria| IDX & LOG & OV
  S2 -->|lê| R1
  S2 -->|escreve| SRC & ENT & CON & SYN
  S2 -->|atualiza| IDX & LOG
  S2 -.delega leitura.-> A1
  S3 -->|lê| IDX & wiki
  S3 -->|arquiva opcional| CMP & QST & SYN
  S3 -.delega busca.-> A2
  S4 -->|roda| TOOLS
  S4 -.delega julgamento.-> A3
  S4 -->|corrige seguro| IDX
  S5 -->|reconstrói| IDX
  S5 -->|append| LOG
  S7 -->|gera| OUT
  A4 -->|revisa diff| wiki
  H -->|log-tail| TOOLS
  schema -.lido por todas as skills.-> pkg
```

### 3.3 Princípios de projeto

1. **Só o orquestrador escreve, e escreve uma vez.** Subagentes devolvem pacotes YAML de propostas; o agente principal aplica. Evita escrita concorrente em `index.md` e `log.md`.
2. **Determinístico onde possível.** Links, frontmatter, índice e formato do log são verificados por `wiki_tools.py` (stdlib, sem LLM). Julgamento (contradições, obsolescência) é do modelo, mas só reporta ou corrige o que a config permite.
3. **Fonte é dado, não instrução.** Toda skill e todo agente carregam a regra anti-prompt-injection.
4. **Aprovação humana configurável.** `approval_mode: none | plan | all` em `.llm-wiki/config.yml`.
5. **Um pacote, quatro agentes.** Mesmos `SKILL.md` e `agents/*.md`; a instalação mapeia para os diretórios de cada agente. Diferenças ficam na seção "Específico por agente" de cada skill.

---

## 4. Inventário do que já existe no repositório

Todos os itens abaixo foram lidos nos arquivos reais em 2026-09-20.

### 4.1 Skills (`skills/<nome>/SKILL.md`)

Todas têm frontmatter `name`, `description`, `license: MIT`, `metadata.author: idutra`, `metadata.version: "0.1.0"`, `metadata.package: llm-wiki-kit`. `wiki-search` e `wiki-export` também têm `compatibility`. Nenhum valor de frontmatter contém caractere não ASCII (validado por script; exigência do APM).

| Skill | Propósito | Gatilho (frases da `description`) | Entradas | Saídas / arquivos que toca | Delegação |
|---|---|---|---|---|---|
| `wiki-init` | Criar ou adotar um LLM Wiki no repositório atual. Idempotente: nunca sobrescreve. Pergunta `language`, `approval_mode`, `default_sensitivity`. | "init wiki", "criar wiki", "iniciar llm wiki", "adotar wiki neste repo"; ou outra skill `wiki-*` não achou `wiki/`. | Raiz do repo; três decisões de config. | Cria `AGENTS.md` (ou anexa seção `## LLM Wiki`), `CLAUDE.md` (`@AGENTS.md`), `.llm-wiki/config.yml`, `.llm-wiki/templates/*.md`, `.llm-wiki/scripts/wiki_tools.py`, `wiki/index.md`, `wiki/log.md`, `wiki/overview.md`, `raw/.gitkeep`, `raw/assets/.gitkeep`, 7 subdiretórios de `wiki/` com `.gitkeep`, opcional `.github/copilot-instructions.md`. Roda `check` e `log-append --op init`. | Nenhuma. |
| `wiki-ingest` | Ingerir uma fonte por vez: capturar em `raw/`, ler por completo, triar (New/Update/Disputed/No material), planejar, escrever página `source` e propagar para entidades, conceitos e sínteses, atualizar índice e log. | "ingest", "ingerir", "processar esta fonte", "adicionar ao wiki", "add to wiki", arquivo solto em `raw/`. | Caminho em `raw/`, texto colado ou URL aprovada; `approval_mode`; ênfase opcional. | Cria/atualiza `raw/<cat>/<data>-<slug>.md` (só se veio de URL/colagem), `wiki/sources/<slug>.md`, páginas em `entities/`, `concepts/`, `syntheses/`, `wiki/index.md`, `wiki/overview.md` (se mudou), `wiki/log.md` (`--op ingest`). Roda `check`. | `wiki-ingest-agent` para fontes longas. |
| `wiki-query` | Responder perguntas com citações, index-first; declarar lacunas; opcionalmente arquivar a resposta (filing back). Somente leitura por padrão. | "what do we know about", "o que o wiki diz sobre", "compare A e B", "responda com base no wiki", "arquivar esta resposta". | Pergunta; profundidade `quick`/padrão/`deep`. | Lê `wiki/index.md`, `overview.md`, páginas, `raw/` se necessário. Se arquivar: cria página nova em `wiki/comparisons/`, `syntheses/` ou `questions/` com `archived_from: query`, atualiza `index.md` (prefixo `[Archived]`), links `related` recíprocos, `log.md` (`--op archive`). | `wiki-query-agent` para perguntas amplas. |
| `wiki-lint` | Saúde do wiki em dois níveis: mecânico (`wiki_tools.py check --json`, corrige só o seguro) e julgamento (contradições, claims obsoletos, conceitos sem página, cross-refs faltantes, blocos de status malformados, respostas arquivadas envelhecidas, lacunas, sensibilidade, overview desatualizado). | "lint", "lint wiki", "verificar o wiki", "health check", "saude do wiki", "auditar wiki"; periodicamente. | Escopo (wiki inteiro, diretório, ou páginas desde último lint). | Corrige `frontmatter` inequívoco, `broken-link` com candidato único, `raw-ref` com candidato único, `index`. Reporta `orphan`, `placement`, `log`, `unreferenced-raw` e tudo do nível 2. Escreve `wiki/log.md` (`--op lint`). Nunca toca `raw/`. | `wiki-lint-agent` para paralelizar nível 2. |
| `wiki-index` | Reconstruir/reparar `wiki/index.md` preservando resumos existentes; ler e registrar `wiki/log.md` no formato canônico. | "rebuild index", "regenerar indice", "atualizar index.md", "o que aconteceu recentemente no wiki", "ultimas entradas do log"; erros de índice do lint. | Nenhuma além do repo. | `wiki/index.md` via `wiki_tools.py index --write`; `wiki/log.md` via `log-append`. Define ordem de seções e regras de ordenação. Propõe índices por categoria como operação `schema` quando o wiki cresce. | Nenhuma. |
| `wiki-search` | Estratégia de localização em três degraus: índice, `rg` com sinônimos, `qmd` opcional (BM25 + vetores, local). | "configurar busca", "instalar qmd", "search the wiki", "buscar no wiki"; ou `wiki-query` sem candidatos. | Termos, sinônimos, siglas. | Só leitura. Se habilitar `qmd`: `.llm-wiki/config.yml` (`search.engine`, `search.qmd_collection`), `.gitignore` para o índice. Propõe `_index.md` por categoria como alternativa. | Nenhuma. |
| `wiki-export` | Gerar artefatos derivados (deck Marp, relatório executivo, tabela, gráfico matplotlib opcional) em `wiki/outputs/` com `generated_from`, checagem de `sensitivity` e log. Regra: um artefato não introduz fatos novos. | "apresentacao", "slides", "deck", "Marp", "relatorio executivo", "exportar", "gerar tabela comparativa a partir do wiki". | Páginas de origem (via `wiki-query`); `export.marp`, `export.redact_sensitivity_above`. | `wiki/outputs/<data>-<slug>.marp.md` ou `.md` (template `output.md`), `.py`/`.png` opcionais, `wiki/index.md` (seção Outputs), `wiki/log.md` (`--op export`). | Nenhuma. |
| `wiki-conventions` | Referência: tipos de página, frontmatter, nomes de arquivo, links, citações, blocos `Status: Disputed/Outdated`, formatos de `index.md` e `log.md`, processo para evoluir o schema. Se divergir do `AGENTS.md` do repo, o `AGENTS.md` vence. | "convencoes do wiki", "formato das paginas", "alterar o schema"; qualquer escrita/revisão de página. | Nenhuma. | Não executa operações. Descreve a operação `schema` (mudança em `AGENTS.md`/templates com aprovação e log). | Nenhuma. |

### 4.2 Subagentes (`agents/<nome>.md`)

Todos: `model: inherit`, `readonly: true` (Cursor), `tools: Read, Grep, Glob, Bash`, `disallowedTools: Write, Edit, MultiEdit, NotebookEdit` (Claude Code, Copilot), instrução para agir como somente leitura mesmo onde o runtime não impõe. Todos devolvem YAML estruturado, nunca prosa solta, e nunca afirmam ter aplicado mudanças.

| Agente | Propósito | Invocado por | Entradas | Saída (YAML) | `maxTurns` |
|---|---|---|---|---|---|
| `wiki-ingest-agent` | Ler exatamente uma fonte de `raw/` mais páginas relevantes do wiki e devolver um pacote de propostas (páginas a criar/atualizar com conteúdo completo, claims com localizador, contradições, achados sensíveis, perguntas abertas). Não escreve. | `wiki-ingest` (fontes longas, lotes). | Raiz do repo, caminho em `raw/`, ênfase, `approval_mode`, lista de páginas que pode inspecionar. | `status`, `source{path,title,kind}`, `disposition`, `proposals[]{path,action,summary,content}`, `claims[]{text,locator}`, `contradictions[]`, `sensitive_findings[]`, `open_questions[]`, `partial{reason,remaining}`. | 40 |
| `wiki-query-agent` | Localizar material para responder uma pergunta: lê `index.md`, expande sinônimos, busca com `rg`/`qmd`, lê candidatos (padrão 10), devolve páginas, trechos exatos, contradições e lacunas. Não sintetiza a resposta. | `wiki-query` (perguntas amplas). | Pergunta. | `question`, `searched[]`, `pages[]{path,relevance,excerpts,sensitivity}`, `raw_used[]`, `contradictions[]`, `gaps[]`, `status`. | 30 |
| `wiki-lint-agent` | Executar o nível 2 do lint sobre um subconjunto de páginas: contradições sem `Disputed`, claims superados sem `Outdated`, termos recorrentes (3+ páginas) sem página, pares sem link mútuo, blocos `Status` sem data, arquivos `archived_from: query` envelhecidos, indícios de dado sensível, teses de `overview.md` não sustentadas. | `wiki-lint`. | Escopo + saída de `wiki_tools.py check --json`. | `scope`, `pages_reviewed`, `findings[]{severity,kind,pages,evidence,proposed_action,safe_to_autofix}`, `suggested_questions[]`, `suggested_sources[]`, `status`, `remaining[]`. `safe_to_autofix: true` só para links, índice e frontmatter mecânico. | 40 |
| `wiki-curator` | Revisor humano-no-loop: avalia um conjunto de mudanças propostas (pacote do ingest, diff de PR, working tree) contra o schema. Checklist de 10 itens: imutabilidade de `raw/`, rastreabilidade, fidelidade (amostra 3 a 5 valores com `rg`), templates/frontmatter, contradições, propagação, índice e log, sensibilidade, escopo, `check` sem erros. | Humano antes de aplicar em `approval_mode: plan/all`; revisor de PR sobre `wiki/**`. | Proposta + `AGENTS.md`, `config.yml`, templates. | `verdict: approve \| request-changes \| reject`, `summary`, `blocking[]{file,issue,fix}`, `non_blocking[]`, `verified_values[]{value,found_in}`, `approved_by` (humano preenche). | 30 |

### 4.3 Assets do `wiki-init` (`skills/wiki-init/assets/`)

| Arquivo | Destino no repo-alvo | Conteúdo |
|---|---|---|
| `AGENTS.md` | `AGENTS.md` | Schema completo: 6 regras de ouro, estrutura de diretórios, convenções de página e frontmatter, formatos de `index.md` e `log.md`, workflows Ingest/Query/Lint, Governança, seção por agente. |
| `CLAUDE.md` | `CLAUDE.md` | Uma linha: `@AGENTS.md`. |
| `config.yml` | `.llm-wiki/config.yml` | `schema_version: 1`, `language: pt-BR`, `link_style: markdown`, `approval_mode: plan`, `auto_archive: false`, `default_sensitivity: internal`, `paths{raw,wiki,assets}`, `categories[7]`, `search{engine: index, qmd_collection}`, `export{marp: true, redact_sensitivity_above: internal}`. |
| `templates/source.md` | `.llm-wiki/templates/` | Frontmatter com `source_meta{author,published,collected,origin_url,kind}`; seções Resumo, Claims extraídos, Entidades e conceitos, Relação com o wiki, Perguntas abertas. |
| `templates/entity.md` | idem | `entity_kind`, `aliases`; seções Em uma frase, Fatos, Relações, Linha do tempo, Contradições e incertezas, Fontes. |
| `templates/concept.md` | idem | `concept_kind`; seções Definição, Como aparece nas fontes, Posição atual do wiki, Relações, Contradições e incertezas, Perguntas abertas. |
| `templates/synthesis.md` | idem | `confidence`; seções Tese, Evidências a favor, Evidências contrárias, Implicações, O que mudaria esta síntese, Histórico. |
| `templates/comparison.md` | idem | `question`, `archived_from: query`; seções Pergunta, Critérios, Tabela comparativa (coluna Fonte), Leitura, Lacunas, Páginas citadas. |
| `templates/question.md` | idem | `question_status: answered \| partial \| open`, `archived_from: query`; seções Pergunta, Resposta, Confiança e lacunas, Próximos passos, Páginas citadas. |
| `templates/output.md` | idem | `output_format: marp \| report \| chart \| table`, `generated_from[]`; instrução para decks Marp usarem frontmatter Marp + comentário HTML `<!-- llm-wiki: ... -->`. |
| `wiki/index.md` | `wiki/index.md` | Cabeçalho + 8 seções na ordem Overview, Sources, Entities, Concepts, Syntheses, Comparisons, Questions, Outputs, vazias. |
| `wiki/log.md` | `wiki/log.md` | Cabeçalho explicando o formato `## [YYYY-MM-DD] <op> \| <título>` e o comando para ver as últimas entradas. |
| `wiki/overview.md` | `wiki/overview.md` | Página `type: synthesis` com seções Escopo, Teses centrais, Mapa do conhecimento, Lacunas conhecidas, Histórico de revisão; datas `1970-01-01` a substituir. |
| `scripts/wiki_tools.py` | `.llm-wiki/scripts/wiki_tools.py` | Ver 4.4. |

### 4.4 Helper determinístico `wiki_tools.py`

Python 3.9+, stdlib. Nunca chama LLM, nunca toca `raw/`, só escreve `wiki/index.md` (com `--write`) e faz append em `wiki/log.md`. Testado em 2026-09-20 (Python 3.14) sobre os assets: `check` retornou `1 pages, 0 errors, 0 warnings`; `log-append`, `log-tail` e `index` funcionaram.

| Comando | Faz | Exit code |
|---|---|---|
| `check [--json]` | Frontmatter (chaves obrigatórias `title`, `type`, `status`, `created`, `updated`; enums `type`, `status`, `sensitivity`; datas; `sources` obrigatório em `source`), `raw-ref`, `placement` (tipo x diretório), `broken-link`, `broken-wikilink`, `orphan`, `index` (página fora do índice, entrada para arquivo inexistente, duplicata), `log` (cabeçalho e `op` válidos), `unreferenced-raw`. Reconhece frontmatter Marp e não exige chaves de página nele. | 0 ok, 1 erros, 2 sem `wiki/` |
| `index [--write]` | Regera o índice por categoria preservando resumos existentes; `(no summary)` onde faltar; prefixo `[Archived]` para `archived_from`; metadados `(sources: N, updated: D)`. | 0 |
| `log-tail [-n 5]` | Imprime as últimas N entradas. | 0 / 2 |
| `log-append --op <op> --title T [--agent A] [--files f1,f2] [--approved-by X] [--notes N]` | Acrescenta entrada no formato canônico com a data de hoje. `--agent` cai para `LLM_WIKI_AGENT` ou `unknown`. | 0 / 1 op inválida |

### 4.5 Manifestos e hooks

| Arquivo | Campos relevantes | Observação |
|---|---|---|
| `apm.yml` | `name: llm-wiki-kit`, `version: 0.1.0`, `description`, `author: Igor Dutra`, `license: MIT`, `targets: [claude, cursor, codex, copilot]`, `includes: [skills/, agents/, hooks/, .claude-plugin/]`, `marketplace{owner{name,url}, output: .claude-plugin/marketplace.json, metadata{homepage}, build{tagPattern: "v{version}"}, packages[{name: llm-wiki-kit, source: ./, description, tags, category: productivity}]}`. Sem `type`, sem `dependencies`, sem `.apm/`. | Metadata-only de propósito para o APM tratar o repo como Plugin collection (seção 2.1). |
| `.claude-plugin/plugin.json` | `name: llm-wiki-kit`, `version: 0.1.0`, `description`, `author{name,url}`, `homepage`, `repository`, `license: MIT`, `keywords[9]`, `skills: "./skills/"`, `agents: [4 caminhos]`, `hooks: "./hooks/hooks.json"`. | Todos os caminhos declarados existem (requisito do APM e do Claude Code). |
| `.claude-plugin/marketplace.json` | `$schema`, `name: idutra-agent-plugins`, `version: 0.1.0`, `description`, `owner{name,url}`, `metadata{homepage}`, `plugins[{name: llm-wiki-kit, description, version: 0.1.0, author{name}, source: "./", category, keywords}]`. | Mantido em sincronia manual com o bloco `marketplace` do `apm.yml`; `apm pack` pode regerá-lo. |
| `hooks/hooks.json` | `hooks.SessionStart[0].hooks[0]{type: command, command: python -c "...", timeout: 15}`. | Se `.llm-wiki/scripts/wiki_tools.py` existir no CWD, roda `log-tail -n 3`; senão sai 0. Formato do Claude Code. |
| `.gitignore` | `__pycache__/`, `*.pyc`, `.DS_Store`, `Thumbs.db`, `apm_modules/`, `apm.lock.yaml`, `.claude/settings.local.json`, `.cursor/mcp.json`. | Este repo é produtor; consumidores têm seu próprio lockfile. |

---

## 5. Fluxos

### 5.1 Init

1. Identificar raiz do repo-alvo; confirmar `git status` (avisar se não for git).
2. Coletar `language`, `approval_mode`, `default_sensitivity`.
3. Copiar assets conforme tabela da skill, sem sobrescrever; anexar seção a `AGENTS.md`/`CLAUDE.md` existentes.
4. Criar `raw/`, `raw/assets/` e os 7 subdiretórios de `wiki/` com `.gitkeep`.
5. Copilot: criar `.github/copilot-instructions.md` apontando para `AGENTS.md`.
6. Listar arquivos pré-existentes em `raw/` sem página como backlog (não ingerir).
7. `python .llm-wiki/scripts/wiki_tools.py check` deve retornar 0 erros.
8. `log-append --op init ... --notes "approval_mode=<v>; language=<v>"`.
9. Se `approval_mode: all`, orientar proteção de branch e PR obrigatório para `wiki/**`.
10. Relatório: criados, preservados, config, backlog, próximo passo (`wiki-ingest`).

### 5.2 Ingest

Passo a passo (skill `wiki-ingest`):

1. Pré-condições: ler `AGENTS.md`, `.llm-wiki/config.yml`, `wiki/index.md`, `wiki/overview.md`; `log-tail -n 5`. Sem `AGENTS.md`, oferecer `wiki-init`.
2. Capturar em `raw/`: se já está lá, não tocar; se veio por URL/colagem, confirmar domínio e salvar `raw/<categoria>/<YYYY-MM-DD>-<slug>.md` com cabeçalho `source_url`, `collected`, `published`, `author`, `title`. Nunca sobrescrever (sufixo `-2`, `-3`).
3. Ler por completo e extrair: metadados, claims com localizador, entidades/conceitos com sinônimos, confirmações/extensões/contradições, perguntas abertas. Buscar páginas existentes com `rg -i` (ou `qmd`).
4. Triagem: New, Update, Disputed, No material (este último: manter raw, logar, parar).
5. Plano: tabela caminho / ação / mudança. Em `plan`/`all`, aguardar aprovação explícita. Se passar de 20 páginas, propor dividir.
6. Escrever: `wiki/sources/<slug>.md` pelo template; entidades/conceitos (reutilizar antes de criar; link de volta); sínteses (Tese + Histórico); contradições com `Status: Disputed` nas duas páginas e `status: disputed`; superados com `Status: Outdated`; fidelidade de valores; `updated`.
7. Índice, overview e log: `index.md` (uma linha por página tocada), `overview.md` só se a visão geral mudou, `log-append --op ingest ... --approved-by "<nome|pending>" --notes "disposition=<...>; pages=<n>"`, depois `check`.
8. Relatório: disposição, páginas, contradições, dados sensíveis, perguntas abertas, próximas fontes. Em `all`, abrir PR.

```mermaid
sequenceDiagram
  autonumber
  actor H as Humano
  participant O as Orquestrador (skill wiki-ingest)
  participant A as wiki-ingest-agent (RO)
  participant R as raw/
  participant W as wiki/
  participant T as wiki_tools.py

  H->>O: "ingerir raw/reunioes/2026-09-18-kickoff.md"
  O->>W: lê AGENTS.md, config.yml, index.md, overview.md
  O->>T: log-tail -n 5
  O->>R: confirma que a fonte existe (não altera)
  alt fonte longa ou lote
    O->>A: Task(fonte, escopo de páginas, approval_mode)
    A->>R: lê a fonte por completo
    A->>W: rg -i entidades/conceitos; lê até 8 páginas
    A-->>O: YAML: disposition, proposals[], claims[], contradictions[], sensitive_findings[]
  else fonte curta
    O->>R: lê a fonte
    O->>W: rg -i e leitura das páginas relacionadas
  end
  O->>O: triagem New / Update / Disputed / No material
  alt approval_mode = plan ou all
    O-->>H: plano (tabela caminho / ação / mudança)
    H-->>O: aprova (ou pede ajustes)
  end
  O->>W: escreve sources/<slug>.md e propaga (entities, concepts, syntheses)
  O->>W: marca Status: Disputed / Outdated onde houver
  O->>W: atualiza index.md (e overview.md se necessário)
  O->>T: log-append --op ingest --approved-by <nome|pending>
  O->>T: check
  T-->>O: 0 erros (ou lista de erros mecânicos para corrigir)
  O-->>H: relatório (disposição, páginas, contradições, sensíveis, próximas fontes)
  opt approval_mode = all
    H->>W: abre PR em wiki/**; wiki-curator revisa
  end
```

### 5.3 Query

1. Ler `AGENTS.md` e config. Sem `wiki/`, informar e oferecer `wiki-init` (não responder de memória).
2. Localizar (index-first): `index.md` inteiro; `overview.md` se ampla; `rg -i` com sinônimos (ou `qmd`) se candidatos insuficientes; ler páginas por completo; `raw/` só se necessário. Profundidade `quick`/padrão/`deep`. Para perguntas amplas, delegar localização ao `wiki-query-agent`.
3. Sintetizar: preferir o wiki ao conhecimento geral (marcar "(contexto geral, não consta no wiki)"); citações inline com caminhos relativos à raiz; trazer `Disputed`/`Outdated` explicitamente; seções Fontes usadas e Lacunas; respeitar `sensitivity`.
4. Formato: prosa, tabela (comparação), lista cronológica, ou propor `wiki-export` para deck.
5. Arquivar (se pedido ou `auto_archive: true` para comparação/síntese): página nova em `comparisons/`, `syntheses/` ou `questions/`; converter links para relativos ao arquivo; frontmatter `archived_from: query`, `question`, `related`; `index.md` com `[Archived]`; links recíprocos; `log-append --op archive`; `check`. Em `all`, via PR.
6. Perguntas sem resposta: com consentimento, criar `wiki/questions/<slug>.md` com `question_status: open`.

### 5.4 Lint

1. Ler `AGENTS.md` e config; definir escopo (wiki inteiro, diretório, ou desde o último `lint` no log).
2. Nível 1: `wiki_tools.py check --json`. Aplicar a tabela de tratamento por `kind`: corrigir `frontmatter` inequívoco, `broken-link`/`raw-ref` com candidato único, `index`; reportar `orphan`, `placement`, `log`, `unreferenced-raw`. Rodar `check` de novo.
3. Nível 2: ler páginas em escopo (amostrar por categoria em wikis grandes; priorizar `draft` e recentes). Procurar os 9 tipos de achado. Delegar subconjuntos ao `wiki-lint-agent` e consolidar.
4. Relatório no formato `## Lint - YYYY-MM-DD` com Mecânico, Julgamento por severidade, Backlog de ingestão, Perguntas sugeridas.
5. Em `plan`/`all`, correções de julgamento viram lista para aprovação humana.
6. `log-append --op lint --title "<N> issues, <M> auto-fixed" --notes "scope=<...>"`.

### 5.5 Sessão (hook)

No Claude Code, `hooks/hooks.json` roda em `SessionStart`: se `.llm-wiki/scripts/wiki_tools.py` existir no diretório atual, imprime as últimas 3 entradas do log para o agente retomar o contexto. Sem LLM, timeout 15 s, sai 0 quando não é um wiki.

---

## 6. Convenções de página, frontmatter, index.md e log.md

Fonte de verdade em runtime: `AGENTS.md` do repositório-alvo e `.llm-wiki/templates/`. Templates de referência: `skills/wiki-init/assets/templates/{source,entity,concept,synthesis,comparison,question,output}.md`. Resumo:

### 6.1 Tipos e diretórios

| `type` | Diretório | Quando | Regra especial |
|---|---|---|---|
| `source` | `wiki/sources/` | Uma por arquivo (ou conjunto coeso) de `raw/` | `sources:` obrigatório e não vazio; resumo na voz da fonte; `source_meta` |
| `entity` | `wiki/entities/` | Pessoa, organização, equipe, produto, sistema citado por 2+ fontes ou central | `entity_kind`, `aliases` |
| `concept` | `wiki/concepts/` | Conceito, processo, decisão, métrica, política | `concept_kind`; "Posição atual do wiki" é a síntese viva |
| `synthesis` | `wiki/syntheses/` | Tese transversal revisada a cada ingestão | "Histórico" registra cada revisão |
| `comparison` | `wiki/comparisons/` | Resposta a "compare A e B" arquivada | Toda célula factual com fonte; `question`, `archived_from: query` |
| `question` | `wiki/questions/` | Pergunta respondida e arquivada, ou aberta | `question_status` |
| `output` | `wiki/outputs/` | Deck Marp, relatório, gráfico | `generated_from`; não introduz fatos; Marp usa frontmatter Marp + comentário HTML |

### 6.2 Frontmatter

Obrigatórias: `title`, `type`, `status`, `created`, `updated`. Recomendadas: `sources`, `related`, `tags`, `sensitivity`, `confidence`. Datas `YYYY-MM-DD`.

- `status`: `draft` | `reviewed` | `stale` | `disputed`.
- `sensitivity`: `public` | `internal` | `confidential` | `restricted`. Herda `default_sensitivity`; nunca rebaixar sem aprovação humana.
- `updated` muda só com mudança de conteúdo, não de formatação.

### 6.3 Nomes e links

- Arquivos `kebab-case`, ASCII, sem acentos. Fontes: `wiki/sources/<YYYY-MM-DD>-<slug>.md` quando a data é conhecida. Raw: `raw/<categoria>/<YYYY-MM-DD>-<slug>.<ext>`.
- Links entre páginas relativos ao arquivo (`../concepts/y.md`; para raw `../../raw/cat/file.md`). Em conversa, relativos à raiz (`wiki/concepts/y.md`). `[[wikilink]]` só com `link_style: wikilink`.
- Todo número, data, nome ou citação literal tem link para `source` ou `raw/` e existe literalmente na fonte. Derivados mostram componentes. Conhecimento geral é marcado.

### 6.4 Contradições e obsolescência

```
> **Status: Disputed** (2026-09-19) - [Fonte A](../sources/a.md) afirma X; [Fonte B](../sources/b.md) afirma Y. Pendente de decisão humana.
> **Status: Outdated** (2026-09-19) - Substituído por [Fonte C](../sources/c.md). Mantido para histórico.
```

Sempre com data; nas duas páginas envolvidas; `status: disputed` ou `stale` no frontmatter.

### 6.5 `index.md`

- Seções `## <Categoria>` na ordem Overview, Sources, Entities, Concepts, Syntheses, Comparisons, Questions, Outputs.
- Linha: `- [Título](caminho/relativo.md) - resumo de uma linha (sources: N, updated: YYYY-MM-DD)`.
- Toda página exceto `index.md` e `log.md` aparece exatamente uma vez. Arquivadas com `[Archived]`. Sources em ordem cronológica decrescente; demais alfabéticas.
- `wiki_tools.py index [--write]` gera o esqueleto preservando resumos.

### 6.6 `log.md`

```
## [YYYY-MM-DD] <op> | <título>
- agent: <claude-code|cursor|codex|copilot|human>
- files: <caminhos>
- approved_by: <nome|pending>
- notes: <uma linha>
```

`op` em {`init`, `ingest`, `query`, `archive`, `lint`, `index`, `export`, `schema`}. Append-only; correções são entradas novas. Sempre via `wiki_tools.py log-append`. Queries que não escrevem não precisam de log.

### 6.7 Evoluir o schema (operação `schema`)

Descrever o problema, propor alteração mínima em `AGENTS.md` (e template, se for o caso), aguardar aprovação em `plan`/`all`, registrar `schema` no log com `approved_by`, planejar migração e rodar `check`. Mudanças no schema **do pacote** seguem o semver do pacote (seção 8.4), não do wiki.

---

## 7. Compatibilidade por agente

| Capacidade | Claude Code | Cursor | Codex | GitHub Copilot |
|---|---|---|---|---|
| Lê `AGENTS.md` | Via `CLAUDE.md` com `@AGENTS.md` (o `wiki-init` cria) | Nativo | Nativo | Nativo; `.github/copilot-instructions.md` como redundância |
| Skills (`SKILL.md`) | Nativo. Instaladas via plugin ou `.claude/skills/`. Invocação `/wiki-ingest`. | Nativo. `.agents/skills/` ou `.cursor/skills/` (também lê `.claude/skills/`). Invocação `/wiki-ingest`. | Nativo. `.agents/skills/` do CWD até a raiz. Invocação `$wiki-ingest`. | Nativo. `.github/skills/`, `.agents/skills/` ou `.claude/skills/`. |
| Subagentes (`agents/*.md`) | Nativo via plugin (`llm-wiki-kit:wiki-ingest-agent`). Honra `tools`, `disallowedTools`, `maxTurns`, `model`. Ignora `readonly`. | Nativo em `.cursor/agents/` (também lê `.claude/agents/`, `.codex/agents/`). Honra `readonly: true`, `model`, `is_background`. Ignora `tools`/`disallowedTools`/`maxTurns`. | **Degrada**: APM instala em `.codex/agents/`, mas as skills orientam executar o fluxo no agente principal onde subagentes não estiverem disponíveis. Campos desconhecidos são ignorados. | Parcial: `.github/agents/*.agent.md` quando disponível; campos `tools`/`disallowedTools` no formato Copilot. Não verificado nesta rodada (seção 11). |
| Hooks (`hooks/hooks.json`) | Nativo (`SessionStart`). | **Degrada**: formato próprio de hooks; o pacote não traz equivalente. Alternativa: skill nativa `/loop` ou Automation para rodar `wiki-lint` periodicamente. | **Degrada**: formato não verificado; sem equivalente no pacote. | **Degrada**: APM mapeia para `.github/hooks/`, mas o JSON do Claude Code não foi validado contra o formato do Copilot. Alternativa: nível 1 do lint em CI. |
| Modo somente leitura dos subagentes | Imposto pelo runtime (`disallowedTools`). | Imposto pelo runtime (`readonly`). | Instrução textual apenas. | Instrução textual + `disallowedTools` se suportado. |
| `wiki_tools.py` | Bash | Shell integrado (PowerShell no Windows: os SKILL.md trazem equivalentes `Select-String`). | Shell | Shell / CI |
| Instalação recomendada | Marketplace privado (`claude plugin install llm-wiki-kit@idutra-agent-plugins`) ou `apm install --target claude`. | `apm install --target cursor` (skills + agents) ou `npx skills add ... -a cursor` (só skills). | `apm install --target codex` ou `npx skills add ... -a codex`. | `apm install --target copilot` ou `npx skills add ... -a github-copilot`; `gh skill` também existe. |

Resumo da degradação: o núcleo (skills + `AGENTS.md` + `wiki_tools.py`) funciona igual nos quatro. Subagentes são nativos em Claude Code e Cursor, incertos em Codex e Copilot. O hook é exclusivo do Claude Code. `npx skills add` nunca instala agentes nem hooks; para tê-los, usar APM ou plugin do Claude Code.

---

## 8. Distribuição corporativa

### 8.1 Hospedagem

O pacote é um repositório git (`<host>/<org>/llm-wiki-kit`) com tags `v<semver>`. Os três canais (APM, `npx skills`, Claude Code) leem direto do git usando as credenciais já configuradas na máquina (credential helper, `gh`, SSH). Funciona em GitHub Enterprise, Azure DevOps, GitLab e Bitbucket. URLs abaixo usam `github.com/idutra/llm-wiki-kit` como placeholder (valor atual em `apm.yml` e `plugin.json`); trocar pelo host interno é decisão em aberto (seção 11).

### 8.2 Instalação via APM (recomendado: skills + agents + hooks em todos os targets)

```bash
# CLI (uma vez por máquina)
brew install apm                                   # macOS
curl -sSL https://aka.ms/apm-unix | sh             # Linux/macOS
irm https://aka.ms/apm-windows | iex               # Windows PowerShell
pip install apm-cli                                # alternativa (Python 3.10+)

# Pacote inteiro, versão fixa, target detectado pelas pastas do repo consumidor
apm install idutra/llm-wiki-kit#v0.1.0

# Host interno (GHE, Azure DevOps, GitLab)
apm install ghe.example.internal/platform/llm-wiki-kit#v0.1.0
apm install https://dev.azure.com/example/platform/_git/llm-wiki-kit#v0.1.0

# Targets explícitos
apm install idutra/llm-wiki-kit#v0.1.0 --target claude,cursor

# Subconjunto de skills (persistido em apm.yml e apm.lock.yaml)
apm install idutra/llm-wiki-kit#v0.1.0 --skill wiki-ingest --skill wiki-query

# Via marketplace registrado
apm marketplace add idutra/llm-wiki-kit
apm install llm-wiki-kit@idutra-agent-plugins

# Range semver (resolve a maior tag v0.1.x)
# em apm.yml do consumidor:
#   dependencies:
#     apm:
#       - git: idutra/llm-wiki-kit
#         ref: ^0.1.0

# CI: reproduzir exatamente o lockfile
apm install --frozen

# Preview sem escrever
apm install idutra/llm-wiki-kit#v0.1.0 --dry-run
```

Escopo: por padrão instala no projeto (commit de `apm.yml` e `apm.lock.yaml` compartilha com o time). `-g` instala no usuário.

### 8.3 Instalação via `npx skills add` (só skills)

```bash
# Todas as skills, agentes detectados automaticamente
npx skills add idutra/llm-wiki-kit

# URL completa em host interno
npx skills add https://ghe.example.internal/platform/llm-wiki-kit.git
npx skills add https://dev.azure.com/example/platform/_git/llm-wiki-kit
npx skills add git@ghe.example.internal:platform/llm-wiki-kit.git

# Versão fixa (URL de tree em tag)
npx skills add https://github.com/idutra/llm-wiki-kit/tree/v0.1.0/skills/wiki-ingest

# Agentes e skills específicos, não interativo
npx skills add idutra/llm-wiki-kit -a claude-code -a cursor -a codex -a github-copilot --skill wiki-ingest --skill wiki-query -y

# Global, cópia em vez de symlink (Windows sem privilégio de symlink)
npx skills add idutra/llm-wiki-kit -g --copy

# Manutenção
npx skills list
npx skills update
npx skills remove wiki-export

# Governança: desligar telemetria em ambiente corporativo
DISABLE_TELEMETRY=1 npx skills add idutra/llm-wiki-kit
```

Limitação: não instala `agents/` nem `hooks/`. Use quando o time só quer as skills ou o agente não é coberto pelo APM.

### 8.4 Marketplace privado do Claude Code

O repositório já é um marketplace (`.claude-plugin/marketplace.json`, nome `idutra-agent-plugins`) com um plugin (`llm-wiki-kit`, `source: "./"`).

```bash
# Usuário
claude plugin marketplace add idutra/llm-wiki-kit            # GitHub (SSH por padrão)
claude plugin marketplace add https://ghe.example.internal/platform/llm-wiki-kit.git
claude plugin install llm-wiki-kit@idutra-agent-plugins       # escopo user
claude plugin install llm-wiki-kit@idutra-agent-plugins --scope project   # grava em .claude/settings.json
claude plugin update llm-wiki-kit@idutra-agent-plugins
claude plugin uninstall llm-wiki-kit@idutra-agent-plugins

# Dentro da sessão: /plugin marketplace add ..., /plugin install ...
```

Registro automático para o time: em `.claude/settings.json` do repositório do wiki:

```json
{
  "extraKnownMarketplaces": {
    "idutra-agent-plugins": {
      "source": { "source": "github", "repo": "idutra/llm-wiki-kit" }
    }
  },
  "enabledPlugins": { "llm-wiki-kit@idutra-agent-plugins": true }
}
```

Para host não-GitHub, `source: { "source": "url", "url": "https://ghe.example.internal/platform/llm-wiki-kit.git" }`. Em plano Team/Enterprise, o marketplace pode ser distribuído por Organization settings (repo privado no github.com/GHE/GitLab; plugins por caminho relativo `./`, como o nosso). Não incluir diretório `bin/` na raiz do plugin.

Autenticação em background: o refresh automático desabilita credential helpers; para repos privados, configurar `CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE=1` ou um `url.insteadOf` com token read-only.

### 8.5 Versionamento

- **Semver** em três lugares que devem ser iguais: `apm.yml.version`, `plugin.json.version`, `marketplace.json.plugins[0].version` (e `marketplace.json.version`). Estratégia APM `lockstep` (padrão). `metadata.version` em cada `SKILL.md` acompanha o pacote.
- **Tag git** `v{version}` (padrão `build.tagPattern`). A tag é o que `apm install ...#v0.1.0` e ranges `^0.1.0` resolvem.
- **Claude Code** usa `plugin.json.version` como chave de cache: sem bump, `claude plugin update` diz "already at the latest version". Bump obrigatório a cada release.
- **CHANGELOG.md** na raiz (Keep a Changelog): MAJOR para mudança de schema que exige migração de páginas (ex.: nova chave obrigatória em frontmatter, mudança em `log.md`), MINOR para skill/agente novo ou seção nova em template, PATCH para correção de texto.
- **Release gate** (CI):

```bash
claude plugin validate . --strict
apm pack --check-versions --check-clean --dry-run
python -c "..."   # opcional: validar ASCII-only e name==dir em skills/*/SKILL.md
git tag v0.1.0 && git push --tags
apm pack          # regenera .claude-plugin/marketplace.json a partir de apm.yml (commitar)
```

### 8.6 Atualização e rollback

| Canal | Atualizar | Voltar versão |
|---|---|---|
| APM | `apm install --update` (ou `apm update`); commitar `apm.lock.yaml`. | Trocar o `ref` em `apm.yml` para `v0.1.0` e `apm install`; ou `git revert` do commit que mudou `apm.lock.yaml` e `apm install --frozen`. `apm uninstall llm-wiki-kit` remove todos os arquivos registrados no lockfile. |
| `npx skills` | `npx skills update` (pega o HEAD da fonte). | `npx skills remove ...` e `npx skills add <url>/tree/v0.1.0/...` ou de um clone local na tag (`npx skills add ./llm-wiki-kit`). Não há lockfile. |
| Claude Code | `claude plugin update llm-wiki-kit@idutra-agent-plugins` (só se `version` mudou). | Publicar tag/commit com `version` anterior (ou `x.y.z+1` revertendo o conteúdo) no marketplace; ou apontar `extraKnownMarketplaces.source.ref` para a tag antiga e `claude plugin update`. |

Regra operacional: **nunca reescrever uma tag publicada**. Rollback é uma nova versão (ex.: `0.1.2` que reverte `0.1.1`) ou um pin explícito para a tag antiga.

### 8.7 Feed/repositório interno

Opções, da mais simples à mais controlada:

1. **Um repositório git por pacote** (estado atual): `llm-wiki-kit` é pacote e marketplace ao mesmo tempo. Suficiente para o POC.
2. **Repositório-marketplace agregador** (`idutra-agent-plugins`) com `apm.yml` listando vários pacotes em `marketplace.packages[]` (remotos com `version`/`ref`, ou locais em `./plugins/<nome>`) e `apm pack` gerando o `marketplace.json`. Um único `claude plugin marketplace add` e `apm marketplace add` para todos os plugins do time. Recomendado a partir do segundo pacote.
3. **Registry APM privado** (`registries:` em `apm.yml`, `APM_REGISTRY_TOKEN_*`): marcado como experimental na doc; não recomendado agora.
4. **Política**: `apm-policy.yml` no nível org restringindo fontes ao host interno e exigindo `includes` explícito; `apm audit --ci` em branch protection.

---

## 9. Governança

### 9.1 Revisão humana

- `approval_mode` em `.llm-wiki/config.yml`: `none` (agente escreve direto; só para wikis pessoais), `plan` (padrão; humano aprova o plano antes da escrita), `all` (toda escrita em `wiki/**` vai por PR).
- `wiki-curator` prepara a decisão (verdict, blocking, verified_values) mas não substitui a aprovação humana. `approved_by` no `log.md` registra quem aprovou; `pending` quando ainda não.
- Páginas nascem `status: draft`; humano promove a `reviewed`.

### 9.2 RBAC via git

- Branch protection na `main` do wiki; CODEOWNERS para `wiki/**` (curadores), `raw/**` (quem pode adicionar fontes) e `AGENTS.md` + `.llm-wiki/**` (mantenedores do schema).
- `raw/` imutável: regra de PR que rejeita modificação/remoção em `raw/**` (só adição). O `wiki-curator` checa isso como item 1.
- Repositório do pacote: CODEOWNERS em `skills/**`, `agents/**`, `apm.yml`, `.claude-plugin/**`; tags protegidas.
- Escopo de instalação: `--scope project` (Claude) e `apm.yml` commitado dão ao time a mesma versão; `-g` fica para experimentação individual.

### 9.3 Auditoria pelo `log.md`

- Cada operação que altera `wiki/` gera uma entrada com `agent`, `files`, `approved_by`, `notes`. Parseável com `rg "^## \["`.
- `wiki_tools.py check` valida o formato; `wiki-lint` reporta cabeçalhos fora do padrão.
- Combinar com `git log -- wiki/` para autoria técnica e com `apm.lock.yaml` (hashes de conteúdo do pacote) para saber qual versão das skills estava instalada.
- Opcional: exigir auditoria de leitura (`query` sem escrita) via config, para wikis `confidential`.

### 9.4 Dados sensíveis e PII

- `sensitivity` por página (`public`, `internal`, `confidential`, `restricted`); herda `default_sensitivity`; nunca rebaixar sem aprovação.
- `wiki-ingest` e `wiki-ingest-agent` não copiam credenciais ou dados pessoais para `wiki/`; registram `sensitive_findings` sem reproduzir o dado.
- `wiki-export` bloqueia páginas acima de `export.redact_sensitivity_above` sem aprovação explícita; gera com `[omitido: confidencial]`.
- `wiki-query` avisa antes de detalhar conteúdo `confidential`/`restricted` e não copia para fora do repo sem confirmação.
- `wiki-lint` nível 2 item 8 procura indícios de dado sensível sem `sensitivity` adequado (severidade alta).
- Índices derivados (`qmd`) podem conter texto de páginas confidenciais: ficam em `.gitignore` e não são distribuídos.
- Fontes web: confirmar domínio e permissão de armazenamento antes de baixar.
- Telemetria de ferramentas: `DISABLE_TELEMETRY=1` para `npx skills`; revisar política de telemetria do APM antes do rollout.

### 9.5 Prompt injection

Todo conteúdo de `raw/` e de páginas é dado não confiável (regra 6 do `AGENTS.md`, seção Segurança das skills e agentes). Subagentes somente leitura reduzem o raio de dano; o orquestrador é o único que escreve, e só em `wiki/`. `apm install` faz scan de Unicode oculto no pacote; `apm audit` detecta drift entre o instalado e o esperado.

### 9.6 Hooks

- Claude Code: `hooks/hooks.json` só lê (`log-tail`). Qualquer hook futuro que escreva deve ser determinístico e registrado no log.
- Recomendação para o POC: manter hooks como opcionais e sem efeito colateral. Automação periódica de lint via CI (`wiki_tools.py check` em PR) e não via hook.

---

## 10. Roadmap do POC

| Fase | Entregas | Critérios de aceite |
|---|---|---|
| **0. Pacote instalável** (concluída, exceto repo remoto) | `skills/`, `agents/`, `.claude-plugin/`, `apm.yml`, `hooks/`, este documento. | `claude plugin validate . --strict` passa; `apm install ./ --dry-run --target claude,cursor,codex,copilot` lista todas as 8 skills e 4 agentes sem erro; `wiki_tools.py check` retorna 0 sobre os assets. |
| **1. Publicação interna** | Repo git no host escolhido; tag `v0.1.0`; `CHANGELOG.md`; CODEOWNERS. | `apm install <host>/<org>/llm-wiki-kit#v0.1.0` funciona em uma máquina limpa (Windows e macOS/Linux); `claude plugin marketplace add` + `install` funcionam; `npx skills add` lista as 8 skills. |
| **2. Wiki piloto** | Um repo `team-wiki` inicializado com `wiki-init` (`approval_mode: plan`); 10 a 20 fontes reais ingeridas (docs internos, transcrições); 3 sínteses; 1 comparação arquivada; 1 deck Marp. | Cada fonte gera página `source` + 3 a 10 páginas propagadas; `check` zero erros ao fim de cada ingest; `log.md` com uma entrada por operação; amostra de 20 valores numéricos/datas confere 100% com `raw/`; ao menos 1 `Status: Disputed` legítimo detectado. |
| **3. Multi-agente** | Mesmo wiki operado por Claude Code, Cursor, Codex e Copilot em sessões distintas. | Cada agente executa `wiki-ingest` e `wiki-query` com sucesso; diffs de páginas geradas por agentes diferentes seguem o mesmo template (revisão do `wiki-curator` sem `blocking`); lista de degradações reais observadas anexada à seção 7. |
| **4. Governança** | `approval_mode: all` no piloto; branch protection; CODEOWNERS; `wiki-curator` como revisor de PR; CI rodando `wiki_tools.py check`. | 5 PRs de `wiki/**` revisados com `wiki-curator`; nenhum diff em `raw/**` aceito; 100% das entradas do log com `approved_by` preenchido. |
| **5. Avaliação e decisão** | Relatório de 2 páginas: custo por ingest (tokens/tempo), qualidade (fidelidade, contradições), adoção, degradações por agente; recomendação go/no-go para `1.0.0`. | Mantenedor e stakeholders decidem: expandir para outros times, ajustar schema (release `0.2.0`) ou encerrar. |

Fora do POC (backlog): `qmd` para wikis grandes, índices por categoria, migração de Notion/Confluence/MediaWiki como ingestão em lote, hooks para Cursor/Codex/Copilot, registry APM privado.

---

## 11. Riscos e decisões em aberto

### 11.1 Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| APM em v0.3 working draft; formato pode mudar | Instalação quebra após update do CLI | Fixar versão do CLI no rollout; `apm install --frozen` em CI; revisar release notes antes de atualizar |
| `plugin.json` sem `$schema` reconhecido é classificado por estrutura pelo APM | Se o APM passar a reconhecer um `$schema` de Agent Plugins, layout pode mudar | Não adicionar `$schema` ao `plugin.json` sem testar `apm install --dry-run` |
| `apm.yml` deixar de ser metadata-only (alguém adiciona `dependencies`) | APM ignora `plugin.json` e trata como pacote APM classico; agentes deixam de ser instalados | Comentário no `apm.yml`; teste de `--dry-run` em CI que confere a lista de artefatos |
| Subagentes não nativos em Codex/Copilot | Fluxos mais lentos e menos isolados nesses agentes | Skills já orientam fallback no agente principal; medir na fase 3 |
| Hook só no Claude Code | Retomada de contexto desigual entre agentes | `wiki-index` documenta `log-tail` manual; skills leem o log nas pré-condições |
| Escrita concorrente em `index.md`/`log.md` (dois ingests em paralelo) | Corrupção do índice | Regra "uma fonte por vez" nas skills; `approval_mode: all` serializa por PR |
| Fidelidade de valores (alucinação de números/datas) | Wiki perde confiança | Regra de localizador antes de escrever; `wiki-curator` amostra valores; critério de 100% na fase 2 |
| Dados sensíveis em `raw/` versionado | Vazamento por clone do repo | Classificar o repo do wiki como interno/confidencial; `sensitivity` por página; não exportar acima do limiar |
| Telemetria de `npx skills` para repos não-GitHub-públicos | Envio de identificadores de fonte | `DISABLE_TELEMETRY=1` ou usar só APM |
| Symlinks no Windows (`npx skills`) | Instalação falha sem privilégio | `--copy`, ou APM |

### 11.2 Decisões em aberto

1. **Host do repositório do pacote e do wiki piloto**: GitHub Enterprise, Azure DevOps ou GitLab? Define as URLs em `apm.yml`, `plugin.json`, `marketplace.json` (hoje `github.com/idutra/...`) e o método de autenticação.
2. **Canal primário de distribuição**: APM para todos (um comando, lockfile, targets) ou marketplace do Claude Code para quem usa Claude e APM para o resto? Afeta o que entra no guia de onboarding.
3. **Escopo de instalação padrão**: projeto (`apm.yml` commitado no repo do wiki; `--scope project` no Claude) ou usuário (`-g`)?
4. **`approval_mode` do piloto**: começar em `plan` (mais rápido) e migrar para `all` na fase 4, ou já em `all`?
5. **Nome do marketplace**: manter `idutra-agent-plugins` (agregador futuro) ou um nome específico do time?
6. **Repositório agregador**: criar já o `idutra-agent-plugins` separado (seção 8.7 opção 2) ou esperar o segundo pacote?
7. **`$schema` do `marketplace.json`**: hoje `https://anthropic.com/claude-code/marketplace.schema.json` (ignorado em runtime). Manter, remover, ou trocar por uma URL do schemastore quando confirmada?
8. **Idioma das skills**: corpo em pt-BR, `description` em inglês (para o matcher dos agentes). Manter ou traduzir `description` também?
9. **Verificações pendentes** antes da fase 3: formato de hooks do Cursor e Codex; se Codex carrega `.codex/agents/`; se Copilot honra `maxTurns`/`disallowedTools` em `.github/agents/*.agent.md`. Quem faz e quando.
10. **Telemetria e política**: exigir `DISABLE_TELEMETRY=1` no onboarding e escrever um `apm-policy.yml` corporativo já no POC?
11. **Licença**: `MIT` está nos manifestos e skills. Confirmar com jurídico se o pacote pode ser MIT ou deve ser proprietário/interno.
12. **Python nas máquinas-alvo**: `wiki_tools.py` exige Python 3.9+. Confirmar disponibilidade nos ambientes de Cursor/Copilot dos times ou empacotar alternativa.

---

## Apêndice A. Comandos de referência rápida

```bash
# Wiki (dentro do repo do wiki)
python .llm-wiki/scripts/wiki_tools.py check [--json]
python .llm-wiki/scripts/wiki_tools.py index [--write]
python .llm-wiki/scripts/wiki_tools.py log-tail -n 5
python .llm-wiki/scripts/wiki_tools.py log-append --op ingest --title "T" --agent cursor --files "a, b" --approved-by "Ana" --notes "n"

# Skills nos agentes
/wiki-init  /wiki-ingest <fonte>  /wiki-query <pergunta>  /wiki-lint  /wiki-index  /wiki-search  /wiki-export     # Claude Code, Cursor
$wiki-init  $wiki-ingest ...                                                                                    # Codex

# Pacote (produtor)
claude plugin validate . --strict
apm pack --check-versions --check-clean --dry-run
apm pack

# Pacote (consumidor)
apm install idutra/llm-wiki-kit#v0.1.0 [--target claude,cursor,codex,copilot] [--skill wiki-ingest]
npx skills add idutra/llm-wiki-kit [-a claude-code -a cursor -a codex -a github-copilot] [--skill wiki-ingest] [-y]
claude plugin marketplace add idutra/llm-wiki-kit && claude plugin install llm-wiki-kit@idutra-agent-plugins
```

## Apêndice B. Fontes verificadas

- APM README: https://raw.githubusercontent.com/microsoft/apm/main/README.md
- APM manifest schema (v0.3 WD, 2026-05-20): https://raw.githubusercontent.com/microsoft/apm/main/docs/src/content/docs/reference/manifest-schema.md
- APM package types: https://raw.githubusercontent.com/microsoft/apm/main/docs/src/content/docs/reference/package-types.md
- APM `apm install`: https://raw.githubusercontent.com/microsoft/apm/main/docs/src/content/docs/reference/cli/install.md
- APM versioning strategies: https://raw.githubusercontent.com/microsoft/apm/main/docs/src/content/docs/producer/versioning-strategies.md
- APM docs site: https://microsoft.github.io/apm/
- skills CLI README (Vercel Labs): https://raw.githubusercontent.com/vercel-labs/skills/main/README.md
- Agent Skills specification: https://agentskills.io/specification
- skills.sh: https://skills.sh
- Claude Code plugins reference: https://code.claude.com/docs/en/plugins-reference
- Claude Code plugin marketplaces: https://code.claude.com/docs/en/plugin-marketplaces
- Cursor skills: https://cursor.com/docs/context/skills
- Cursor subagents: https://cursor.com/docs/context/subagents
- Codex skills: https://developers.openai.com/codex/skills
- GitHub Copilot agent skills: https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
- Karpathy, LLM Wiki (padrão de referência; não verificado nesta rodada, citado como origem do conceito).
