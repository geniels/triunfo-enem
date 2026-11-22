# 0028. Conferir minha prova: acertos da prova real com o gabarito oficial

- **Status:** Aceita
- **Data:** 2026-11-22

## Contexto
Nos dias depois do ENEM, o estudante quer saber quanto acertou. O INEP publica os gabaritos de cada caderno em PDF
poucos dias depois da prova; a nota (TRI) e os parâmetros das questões só saem meses depois, com os microdados.
Em 2026, os gabaritos já estavam publicados quando esta função foi feita.

## Decisão
- **`scripts/importar_gabaritos.py <ano>`** baixa os PDFs de gabarito do INEP
  (`<ano>_GB_impresso_D<dia>_CD<caderno>.pdf`), lê o texto com o **pypdf** (só no desenvolvimento,
  `requirements-dev.txt`; não vai no instalador) e grava `app/conteudo/gabaritos/<ano>.json`, que vai **dentro do
  programa** (funciona offline). Cada caderno é conferido: 90 questões na faixa do dia, letras A–E ou anulada, cor e
  número do caderno. Se algo não bater, nada é gravado.
- **Tela `#conferir`:** a pessoa escolhe o ano, o dia, o caderno (cor) e a língua estrangeira, e preenche as 90
  respostas num cartão de campos de uma letra. O cursor avança sozinho, o Backspace volta, e dá para colar uma
  sequência (`-` para branco). O rascunho fica só no navegador (conveniência); **nada é guardado no servidor**.
- **`GET /api/conferir`** lista anos e cadernos **sem gabarito** (ADR 0003). **`POST /api/conferir`** devolve a
  correção: acertos por área (pela ordem das áreas desde 2017), brancos, anuladas e o resultado de cada questão.
  As rotas são públicas, inclusive pela turma: não usam dados de aluno.
- **Anulada não conta**, nem como acerto nem no total: é como o INEP trata o item na nota.
- **Sem nota estimada.** A tela diz claramente que aquilo é o número de acertos, e não a nota: a TRI pesa cada
  questão pela dificuldade, com parâmetros que só saem depois. Uma "nota estimada" com parâmetros de outro ano seria
  enganosa.
- Convite no Simulado (sempre que houver gabarito) e no Início (só quando o gabarito é do ano atual).

## Consequências
- Para cada ENEM novo: rodar o script poucos dias depois da prova, conferir o resultado e lançar uma versão.
- Gabaritos de cadernos adaptados (ampliada, Libras, ledor), quando publicados com os mesmos nomes, entram
  automaticamente; o script lê todos os números de caderno de 1 a 14.
- Quando os microdados do ano saírem, dá para acrescentar a nota TRI de verdade, com os parâmetros oficiais
  (como no simulado, ADR 0014).
