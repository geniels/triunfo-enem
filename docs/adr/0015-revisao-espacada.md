# 0015. Revisão espaçada com prioridade pela dificuldade TRI

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
Rever um erro no momento certo, pouco antes de esquecer, fixa mais do que rever tudo de uma vez (ADR 0004).
O "Refazer erros" mostrava todos os erros juntos, sem calendário. Com os parâmetros TRI (ADR 0014), sabemos também
quais erros mais custam na nota: errar questão fácil derruba a TRI.

## Decisão
- **Calendário por questão** (`app/revisao.py`): errou, volta em **1 dia**; cada acerto **na data ou depois** leva a
  próxima revisão para **3, 7 e 21 dias**; após o 4º acerto, a questão está dominada. Errar de novo recomeça.
  Acerto antes da data não conta (evita "passar" respondendo várias vezes no mesmo dia).
- O calendário é calculado do histórico de respostas (prática, revisões e simulados); não há tabela nova.
- **Ordem do dia:** mais fáceis primeiro (menor parâmetro b da TRI); questões sem parâmetro vão por último.
- **Interface:** cartão "Revisão do dia" na tela inicial e modo "Revisão do dia" no Praticar.

## Consequências
- O aluno tem uma tarefa diária curta e objetiva.
- O "Refazer erros" continua existindo para quem quiser rever tudo de uma vez.
