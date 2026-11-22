# 0029. Assunto das questões pela Matriz de Referência do ENEM

- **Status:** Aceita
- **Data:** 2026-11-22

## Contexto
O estudante quer praticar "Geometria" ou "Química", e não só "Matemática" ou "Ciências da Natureza", e quer saber
em que assunto erra mais. O enem.dev só informa a área. Etiquetar 2.749 questões à mão seria trabalhoso e
subjetivo.

Os microdados do INEP, que o projeto já usa para a nota TRI (ADR 0014), trazem em `ITENS_PROVA` a **habilidade
(H1–H30) da Matriz de Referência** de cada item, preenchida em todos os anos a partir de 2010. A Matriz agrupa as 30
habilidades de cada área em **competências** (9 em Linguagens, 6 em Humanas, 8 em Natureza, 7 em Matemática).

## Decisão
- **Assunto = competência da Matriz.** `app/conteudo/assuntos.json` guarda, para cada área, as competências com as
  faixas de habilidades e o texto oficial, extraídos do PDF da Matriz do INEP. Também guarda um **nome curto para o
  estudante** (ex.: "Proporcionalidade e variação" para "Construir noções de variação de grandezas…"; em Natureza,
  "Física", "Química" e "Biologia").
- **Habilidade no banco de questões:** coluna `questoes_tri.habilidade`, gravada pelo `scripts/importar_tri.py` no
  mesmo casamento questão–item que já dá os parâmetros da TRI. Cobre **2.267 de 2.749 questões (82%)**. Ficam sem
  assunto as que não casam com nenhum caderno oficial (2009 Natureza e Humanas, 2016 em três áreas, 2017 inteiro e
  2011 Linguagens).
- Para gerar o banco desta versão, a habilidade foi **copiada** de uma reimportação para o banco já publicado, sem
  trocar os parâmetros nem a escala da TRI. A reimportação completa tinha perdido a escala de 2011 Linguagens, que
  ficou no limite do casamento (40 de 45, abaixo dos 90%).
- **Na interface:**
  - filtro "Assunto (opcional)" na prática, depois de escolher a área, com a quantidade de questões;
  - o assunto aparece no topo da questão;
  - cartão **"O que reforçar"** no Início, com os assuntos de menor acerto (pelo menos 5 respostas e menos de 70%) e um
    botão que abre a prática daquele assunto (questões novas).
- **Bancos antigos** (de antes desta versão) ganham a coluna vazia ao abrir (`COLUNAS_NOVAS`, agora também para o
  banco de questões), e a função de assunto só não aparece até o pacote de dados novo chegar.
- Pacote de dados **`dados-2026.2`**, igual ao `dados-2026.1` exceto pelo `questoes.db`.

## Consequências
- O assunto é a classificação oficial do INEP, e não uma opinião do projeto; os nomes curtos são do projeto e podem
  ser ajustados em `assuntos.json` sem mexer no código.
- Competências como "Cultura e identidade" (Humanas) são mais amplas que um "conteúdo" de cursinho. Para quem quiser
  o detalhe, o texto oficial aparece como dica no filtro.
- As provas de 2024 e 2025 (Fase 5.3) já trazem a habilidade nos microdados e entram com assunto desde o início.
