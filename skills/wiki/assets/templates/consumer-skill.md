---
name: {{name}}
description: {{description}}
---

# {{title}}

Esta skill entrega, em modo somente leitura, um wiki compilado por um agente mantenedor a partir de fontes originais. Use-a para descobrir **o que já se sabe** sobre o assunto antes de planejar, implementar, revisar ou responder, e para citar de onde veio cada afirmação.

Duas ideias sustentam o resto:

- **A fonte decide, o wiki relata.** As páginas em `references/wiki/` organizam, relacionam e resumem. A evidência é o documento em `references/raw/`. Um resumo pode perder uma exceção, então o que importa de verdade se confere na fonte.
- **Lacuna se declara, não se preenche.** Quando o wiki não cobre o caso, quem lê a sua resposta precisa saber disso. Uma afirmação inventada com cara de citação se espalha.

## Como navegar

1. Leia `references/wiki/index.md`. É curto: lista todas as páginas com uma linha de resumo.
2. Leia `references/wiki/manifest.md`, se existir. Ele lista **todas as fontes**, inclusive as que ainda não viraram página. O índice mostra o que o wiki já sabe; o manifesto mostra o que existe para saber. Uma tarefa quase sempre esbarra em assunto fora da página principal.
3. Leia por inteiro as páginas que cobrem a tarefa e siga os links `related` que a tocam.
4. Antes de aplicar um valor literal (número, data, nome de propriedade, comando, citação), abra a fonte citada em `references/raw/` e confira. Valores saem da fonte, não do resumo.
5. Leia os blocos `Status: Disputed` e `Status: Outdated` e as páginas de perguntas abertas: é onde o wiki diz o que ainda não está resolvido.
6. Sem candidatos no índice nem no manifesto, busque texto completo (`rg -il "<termo>|<sinônimo>" references/`). Só então diga que o wiki não cobre o assunto, e diga que buscou.

### Fonte sem página

O manifesto marca como "não ingerida" a fonte que ainda não tem página. Ela vale como as outras; só não passou por curadoria. Abra o arquivo em `references/raw/`, leia por inteiro e cite documento e seção. Diga na resposta que veio direto da fonte.

Se `references/raw/` não existir, as fontes não foram publicadas com esta versão: as páginas são a única evidência disponível, e valores literais ficam marcados como "não conferido na fonte".

## Como aplicar

- Cite página e, quando conferiu, fonte e seção em toda afirmação que vier do wiki. A citação deixa quem revisa conferir em um minuto.
- Mantenha a força do texto original. "Recomenda-se" não vira "deve"; "em um experimento" não vira "sempre".
- Havendo contradição aberta sobre algo que você vai usar, mostre os dois lados e não escolha um em silêncio.
- O seu conhecimento geral é bem-vindo, desde que marcado: "não consta no wiki".
- Esta skill é somente leitura: não edite nada em `references/`. Defeito ou lacuna que você encontrar vira sugestão de issue no repositório do wiki (`{{repository}}`).

## Formato da resposta

Em plano, revisão ou descrição de PR que dependa do wiki, inclua:

```markdown
## Base no wiki

Wiki: <versão em references/VERSION.md> · Páginas consultadas: <lista>

| Afirmação usada | Origem | Conferido na fonte? |
| --- | --- | --- |
| <...> | <página do wiki, ou fonte §seção> | <sim / não / fonte bruta, sem página> |

Lacunas e pontos em aberto: <contradições e perguntas abertas que tocam a tarefa, ou "nenhum">
Fora do wiki: <o que veio do seu conhecimento geral, ou "nada">
```
