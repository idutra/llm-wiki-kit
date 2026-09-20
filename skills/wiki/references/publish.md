# Publicar o wiki como skill somente leitura

Quem mantém o wiki é um agente, em um repositório. Quem **usa** o conhecimento são outros agentes, em outros repositórios, no meio de tarefas que não têm nada a ver com manter wiki. `publish` monta o wiki como uma Agent Skill autocontida e somente leitura, que qualquer ferramenta compatível carrega sozinha quando o assunto aparece. É assim que o wiki entra no dia a dia: ninguém precisa lembrar de consultá-lo.

A skill publicada é um artefato **derivado**. A fonte de verdade continua sendo o repositório do wiki; `dist/` fica no `.gitignore`.

## O que é montado

```
dist/<name>/
├── SKILL.md               instruções de navegação e de citação para o agente consumidor
└── references/
    ├── wiki/              cópia de wiki/, sem log.md (trilha do mantenedor) e sem categorias vazias
    ├── raw/               cópia de raw/: todas as fontes, compiladas ou não (se include_raw: true)
    └── VERSION.md         commit do wiki, data, contagem de páginas e de fontes compiladas
```

Os links relativos das páginas (`../../raw/...`) continuam válidos porque `wiki/` e `raw/` permanecem irmãos dentro de `references/`.

Os nomes vêm do `paths:` do wiki, não são fixos. Um repositório de documentação que adota o wiki e mantém a sua pasta `docs/` (`paths.raw: docs`) publica em `references/docs/`, e a skill gerada cita esse nome. Uma SKILL.md escrita à mão que fale de um diretório diferente do publicado faz o `publish` recusar, em vez de entregar um caminho que não existe.

## Pré-condições

1. `python .llm-wiki/scripts/wiki_tools.py check` sem erros. O `publish` recusa-se a montar com erro, porque um link quebrado no wiki vira um beco sem saída para o agente consumidor.
2. `python .llm-wiki/scripts/wiki_tools.py manifest --write`. Sem manifesto, o consumidor só enxerga o que já foi compilado e conclui que o resto não existe.
3. Confirme com o usuário **para onde a skill vai**. Publicar tira conteúdo do repositório: tudo em `wiki/` e, com `include_raw: true`, tudo em `raw/`. `sensitivity` só existe nas páginas; as fontes em `raw/` não têm classificação, então a decisão de distribuí-las é humana.

## Passo 1 - Configurar (uma vez)

Bloco `publish` em `.llm-wiki/config.yml`. Mudá-lo é edição de configuração, não de schema.

```yaml
publish:
  name: acme-payments-wiki      # kebab-case; vazio = <nome-do-repo>-wiki
  title: Wiki de pagamentos da Acme
  description: Use antes de desenhar, implementar ou revisar cobranca, PIX, conciliacao e estorno na Acme ...
  out: dist
  include_raw: true
  max_sensitivity: internal
```

`description` é o campo que decide se a skill funciona. É só por ela que o agente consumidor decide carregar a skill, e ele tende a **não** carregar. Escreva-a a partir do `wiki/index.md` real:

- diga o que a skill entrega em uma frase;
- liste os **assuntos concretos** cobertos, com os termos que aparecem em tarefas reais (nomes de sistemas, tecnologias, siglas, sinônimos), não categorias abstratas;
- diga quando usar mesmo sem pedido explícito ("use antes de desenhar, implementar ou revisar X, mesmo que ninguém cite o wiki");
- uma linha só no YAML (o helper lê escalares de uma linha), sem dois-pontos seguidos de espaço no meio do texto.

Refaça a `description` quando o wiki ganhar um assunto novo; é o passo que mais envelhece.

Para controle total do texto, escreva `.llm-wiki/publish/SKILL.md` à mão (frontmatter `name` igual a `publish.name`). Ele vence o template `.llm-wiki/templates/consumer-skill.md`. Use isso quando o domínio tiver regras próprias de leitura, por exemplo força normativa literal ou um formato de resposta específico.

## Passo 2 - Montar

```
python .llm-wiki/scripts/wiki_tools.py publish
```

Recusas e o que fazer:

| Mensagem | Causa | Ação |
|---|---|---|
| `check reports N error(s)` | Wiki com erro mecânico | Operação `lint`, depois publique |
| `publish.description is empty` | Sem descrição e sem SKILL.md próprio | Passo 1 |
| `pages above publish.max_sensitivity` | Página `confidential` ou `restricted` | Reclassifique a página, suba o teto de propósito e com aprovação, ou não publique |
| `links that do not resolve inside the published skill` | Página aponta para fora de `wiki/` e `raw/` | Corrija o link no wiki |

## Passo 3 - Entregar

Escolha um canal, do mais simples para o mais governado:

1. **Cópia direta** em um repositório consumidor, nos dois diretórios de descoberta:

   ```
   python .llm-wiki/scripts/wiki_tools.py publish --install ../meu-servico
   ```

   Grava em `.claude/skills/<name>/` (Claude Code) e `.agents/skills/<name>/` (Codex, OpenCode, GitHub Copilot, Cursor, Gemini CLI). O consumidor versiona a cópia; a versão fica em `references/VERSION.md`.
2. **Instalação pessoal**: copie `dist/<name>/` para `~/.claude/skills/` ou `~/.agents/skills/`. Vale para todos os projetos daquela pessoa.
3. **Repositório de distribuição**: um repositório (ou branch) que contém só `dist/<name>/`, atualizado por CI a cada merge no wiki. Consumidores instalam com `npx skills add <repo>` ou `apm install <repo>`, com versão fixada por tag.

Em CI, o job é: `check` → `manifest` sem diferença → `publish` → commit do `dist/` no repositório de distribuição com a tag da versão.

## Passo 4 - Conferir e registrar

1. Abra `dist/<name>/SKILL.md` e confirme que não sobrou `{{...}}`.
2. Teste de disparo: em um repositório consumidor, faça uma pergunta de trabalho real **sem citar o wiki**. Se a skill não carregar, o problema é a `description`; volte ao passo 1.
3. Log:

```
python .llm-wiki/scripts/wiki_tools.py log-append --op publish --title "<name> <versão>" --agent <agente> --files "dist/<name>/" --approved-by "<nome>" --notes "channel=<install|personal|dist-repo>; raw=<true|false>"
```

## O que a skill publicada não faz

- Não escreve no wiki. Defeito ou lacuna encontrados pelo consumidor voltam como issue no repositório do wiki e entram pelo `ingest` ou pelo `lint`.
- Não promete economia de tokens por tarefa em relação a ler as fontes diretamente. O ganho esperado está em lacunas sinalizadas, citação conferível e no assunto que ninguém lembrou de perguntar.
- Não se atualiza sozinha. Ela é tão atual quanto o último `publish`; por isso o `VERSION.md` e, de preferência, o CI.
