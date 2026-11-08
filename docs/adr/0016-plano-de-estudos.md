# 0016. Plano de estudos em ciclo, guiado pelos pontos fracos

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
Estudantes costumam montar horários fixos que quebram na primeira semana. O Guia da prova recomenda o ciclo de
estudos: uma lista de blocos seguida na ordem, quando houver tempo (ADR 0004).

## Decisão
- O aluno informa só **a data da prova e as horas por semana**. Cada hora vira um bloco (50 min + 10 de pausa).
- **1 bloco fixo de redação** por semana; os demais vão para as 4 áreas com peso `0,5 + (1 − taxa de acerto)`:
  toda área recebe tempo, e as mais fracas recebem mais. A taxa só conta com pelo menos 10 respostas na área.
- Os blocos são **intercalados** (uma área diferente por vez), e a redação fica no meio do ciclo.
- **Fases** pela distância da prova: Base (> 90 dias), Simulados (≤ 90, um a cada 2 semanas), Reta final (≤ 30,
  um por semana) e Semana da prova (≤ 7, só revisão leve). Mais a Revisão do dia, todos os dias.
- O aluno marca os blocos feitos; o progresso é por semana ISO. Regras em `app/plano.py`, com testes.

## Consequências
- O plano se ajusta sozinho conforme o desempenho muda.
- Sem calendário fixo: o aluno decide quando estudar, o plano decide o quê.
