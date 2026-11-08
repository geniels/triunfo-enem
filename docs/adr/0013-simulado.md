# 0013. Simulado por dia de prova, na ordem e no tempo oficiais

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
Treinar questões soltas não prepara para o cansaço, o ritmo e o cartão-resposta de 90 questões em 5h ou 5h30.
A ADR 0004 pede "simular as condições reais".

## Decisão
- O simulado é **um dia de prova de um ano**: 1º dia = questões 1 a 90; 2º dia = 91 a 180 (vale para todos os anos,
  mesmo com a troca de ordem das áreas em 2017). Língua estrangeira escolhida pelo aluno.
- **Tempo oficial** (edital 3.3): 5h30 no 1º dia (inclui a redação, feita na aba Redação) e 5h no 2º, em contagem
  regressiva, que fica vermelha nos últimos 30 minutos. Não encerra sozinho: avisa "Tempo esgotado".
- **Cartão-resposta** com a **numeração oficial**; marcar para revisar (técnica das duas passadas); atalhos de teclado.
  Tudo é salvo a cada resposta, e o simulado pode ser retomado depois.
- **Gabarito só depois da entrega**, garantido pelo servidor. Na entrega, as respostas entram no histórico: os erros
  vão para o caderno de erros e para o painel.
- **Nota TRI ainda não é mostrada.** Uma estimativa honesta exige os parâmetros oficiais de cada item (microdados do
  INEP) e o casamento com a ordem das questões da fonte. Até lá, o resultado mostra acertos por área, sem inventar nota.

## Consequências
- Questões faltantes na fonte aparecem puladas na numeração (ex.: 2019, 2º dia, tem 87 das 90).
- Próximo passo da Fase 2: obter os parâmetros TRI (a, b, c) dos microdados e calcular a nota por área.
