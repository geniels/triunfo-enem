# 0014. Nota TRI com os parâmetros oficiais, validada contra notas reais

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
A nota do ENEM vem da Teoria de Resposta ao Item (TRI, edital 14.3), não do número de acertos. Um simulado sem a
nota TRI deixa o aluno sem saber onde está. Uma "nota aproximada" inventada seria enganosa. O INEP publica, nos
microdados de cada ano, o arquivo `ITENS_PROVA_<ano>.csv` com os parâmetros a, b e c de cada questão em cada cor de
caderno, e o arquivo de participantes com respostas e notas oficiais.

## Decisão
- **Modelo:** logístico de 3 parâmetros, constante D = 1, estimativa EAP com priori normal padrão
  (81 pontos entre -4 e 4). Questão em branco conta como erro; questões anuladas ficam fora. Código: `app/tri.py`.
- **Importação** (`scripts/importar_tri.py`): lê de dentro do ZIP do INEP (~600 MB) só o necessário, via HTTP Range,
  cerca de 2 MB por ano. Para cada área:
  1. descobre qual caderno tem a mesma ordem das nossas questões, comparando a sequência de gabaritos
     (aceita só se ≥ 90% bater; por acaso bateria ~20%);
  2. ajusta `nota = k + s × theta` com até 300 participantes **da mesma aplicação** (mesmo conjunto de questões) e
     grava o erro médio contra as notas oficiais.
- **O app só mostra a nota** quando o erro médio da conferência for menor que 1 ponto e houver parâmetros para pelo
  menos 90% das questões da área.
- **Resultado da validação (2020):** erro médio de 0,02 a 0,03 ponto nas quatro áreas, com 300 de 300 participantes
  dentro de 2 pontos. Um teste automatizado (`tests/dados/tri_2020_mt.json`) reproduz 5 notas oficiais.

## Consequências
- O TRIunfo calcula a nota do simulado praticamente como o INEP calcula.
- Quando faltam questões no banco (a fonte não tem algumas), a nota usa as disponíveis e a tela avisa.
- Anos sem microdados acessíveis ficam sem nota, nunca com uma nota inventada.
- A primeira execução baixa cerca de 30 MB (todos os anos); depois, tudo é offline.
