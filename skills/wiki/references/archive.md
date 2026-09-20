# Arquivar uma resposta no wiki (filing back)

Uma boa resposta a uma pergunta é conhecimento novo: uma comparação, uma síntese transversal, uma conexão entre páginas que ninguém tinha escrito. Arquivá-la faz o wiki aprender com o uso. A resposta em si vem da skill `wiki-query`; esta operação só a grava.

Use quando o usuário pedir ("arquive", "salve no wiki", "guarde esta resposta") ou quando `auto_archive: true` na config e a resposta for comparação ou síntese.

## Passos

1. Escolha o tipo: `comparison` -> `wiki/comparisons/`, síntese transversal -> `wiki/syntheses/`, pergunta e resposta -> `wiki/questions/`. Use o template correspondente em `.llm-wiki/templates/`.
2. Sempre crie página nova; nunca funda uma resposta arquivada em página existente. Nome: slug do tema (`comparacao-x-vs-y.md`).
3. Converta citações de caminho-raiz para caminho relativo ao arquivo (`wiki/entities/x.md` vira `../entities/x.md`).
4. Frontmatter: `archived_from: query`, `question: <pergunta original>`, `sources` vazio (o conteúdo vem do wiki), `related` com as páginas citadas.
5. Um arquivamento não introduz fatos novos. O que veio de conhecimento geral fica fora da página ou marcado como "(contexto geral, não consta nas fontes)".
6. Adicione ao `wiki/index.md` na seção correta com prefixo `[Archived]` no resumo. Se a resposta revelou uma conexão nova entre páginas, adicione links `related` recíprocos nelas e registre no log.
7. Log:

```
python .llm-wiki/scripts/wiki_tools.py log-append --op archive --title "<título da página>" --agent <agente> --files "<caminho>" --notes "question=<pergunta resumida>"
```

8. `python .llm-wiki/scripts/wiki_tools.py check`.

Em `approval_mode: all`, o arquivamento vai por PR como qualquer escrita em `wiki/`.

## Perguntas que o wiki não responde

Registre-as (se o usuário concordar) em `wiki/questions/<slug>.md` com `question_status: open` e sugestão de fontes. Perguntas abertas são o backlog de ingestão e, no futuro, o ponto de partida da pesquisa.
