# Convenção de branches e fechamento de versão

Vale para o repositório do kit e é a convenção recomendada para os repositórios de wiki.

## As quatro branches

| Branch | Deriva de | Para quê | Volta para |
|---|---|---|---|
| `release/{versão}` | `main` | Reunir o trabalho de uma versão nova | `main`, com commit de fechamento e tag |
| `hotfix/{versão}` | a **tag** da versão a corrigir | Corrigir uma versão já publicada | `main`, com commit de fechamento e tag |
| `feature/{slug}` | a `release` em andamento | Uma entrega dentro da versão | a `release` de origem |
| `bugfix/{slug}` | o `hotfix` em andamento | Uma correção dentro do hotfix | o `hotfix` de origem |

Regras que sustentam o resto:

- **Ninguém commita direto em `main`.** `main` só recebe merge de `release/*` ou `hotfix/*`.
- **`feature/*` e `bugfix/*` nunca saem de `main`.** Saem da branch de integração à qual pertencem.
- **Um hotfix sai da tag, não de `main`.** É o que permite corrigir a versão que está em produção sem
  arrastar o que já entrou depois dela.
- **Toda versão publicada tem tag.** É a tag que torna o hotfix possível e a instalação reprodutível
  (`apm install <org>/llm-wiki-kit#v0.5.0`).

## Numeração

Segue o semver do pacote, que aparece em `apm.yml`, nos dois arquivos de `.claude-plugin/`, no `metadata.version`
de cada `SKILL.md` e em `KIT_VERSION` no helper. Os cinco precisam bater: há um teste que falha se divergirem.

| Mudança | Versão |
|---|---|
| Operação nova, skill nova, campo novo de config | menor (`0.4.0` → `0.5.0`) |
| Correção sem mudança de comportamento | patch (`0.5.0` → `0.5.1`) |
| Mudança que quebra wikis existentes | maior, com roteiro de migração em `references/init.md` |

A branch leva a versão que está sendo fechada: `release/0.5.0`, `hotfix/0.5.1`.

## Fluxo de uma release

```bash
git checkout main
git pull
git checkout -b release/0.5.0

git checkout -b feature/exemplo-e-documentacao    # a partir da release
# ... trabalho ...
git checkout release/0.5.0
git merge --no-ff feature/exemplo-e-documentacao
```

Quando a versão está pronta, **fechar** é uma sequência só:

```bash
# 1. subir a versão nos cinco lugares e rodar a suíte
python -m unittest discover -s tests

# 2. commit de fechamento, na release
git commit -am "Fecha a versao 0.5.0"

# 3. merge na principal, sem fast-forward, para a versão virar um ponto no histórico
git checkout main
git merge --no-ff release/0.5.0 -m "Merge release/0.5.0"

# 4. tag na main
git tag -a v0.5.0 -m "llm-wiki-kit v0.5.0"
git push origin main --follow-tags
```

O commit de fechamento é o que carrega o bump de versão e o `CHANGELOG`. Ele fica **na release**, antes do
merge, para que a tag na `main` aponte para um estado já fechado.

## Fluxo de um hotfix

```bash
git checkout -b hotfix/0.5.1 v0.5.0        # da TAG, não de main
git checkout -b bugfix/scan-ignora-placeholder
# ... correção ...
git checkout hotfix/0.5.1
git merge --no-ff bugfix/scan-ignora-placeholder
```

Fecha igual: bump para `0.5.1`, commit de fechamento, merge `--no-ff` em `main`, tag `v0.5.1`.

Se houver uma `release` aberta enquanto o hotfix acontece, traga a correção para ela também (`git merge main`
na release, ou cherry-pick), senão a próxima versão nasce com o defeito de volta.

## Como isso aparece no repositório público

A cópia pública (`idutra/llm-wiki-kit`) recebe um commit único por versão, construído sobre o topo dela, e
não o histórico deste repositório. O nome da branch lá acompanha a versão:
`claude/llm-wiki-kit-v0.5.0` → PR → `develop`. A tag `v0.5.0` existe nos dois lados, apontando para
conteúdos idênticos e históricos diferentes.

## Nos repositórios de wiki

A mesma convenção serve, com uma diferença: a "versão" de um wiki é a data ou o número do ciclo de curadoria,
não um semver de software. Com `approval_mode: all`, cada ingestão vira uma `feature/ingest-<slug>` sobre a
release do ciclo, e o fechamento do ciclo é o que dispara o `publish`.
