# 0011. IA na redação: local por padrão; online só com conta paga da escola

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
A correção por IA seria uma segunda opinião sobre a autoavaliação (ADR 0009). As redações são dados pessoais de
estudantes, em grande parte **menores de idade** (LGPD, art. 14: tratamento no melhor interesse da criança e do
adolescente). Opções avaliadas:

| Opção | Custo | Dados do aluno | Qualidade |
|---|---|---|---|
| IA local (modelo de ~4 bilhões de parâmetros, quantizado) | R$ 0 | **Não saem do PC** | Limitada para dar nota; razoável para apontar estrutura |
| Gemini, plano gratuito | R$ 0 | Podem ser usados para melhorar os produtos do Google e lidos por revisores humanos | Boa |
| API paga (ex.: Claude Haiku 5.5, ~US$ 0,0015 por redação) | Baixo | Não usados para treino, conforme os termos comerciais | Boa |

## Decisão
- **Edição Estudante: só IA local**, opcional, baixada com um clique (~2,5 GB) quando o aluno quiser. Nenhum dado sai do PC.
- **Edição Escola: IA local, ou IA online com conta paga da própria escola**, configurada pelo responsável, nunca pelo aluno.
- **Planos gratuitos que usam os dados enviados para treino ou revisão humana estão vetados**, para qualquer edição.
- Por causa da qualidade limitada, a IA local **não dá nota**: ela aponta o que verificar, com o trecho do texto.
  Por exemplo: "a proposta não indica o agente", "pouco uso de conectivos", "o 2º parágrafo não retoma o tema".
  A nota continua sendo a da autoavaliação. A IA online (Escola) pode sugerir níveis por competência, sempre com
  justificativa e como segunda opinião.
- Antes de liberar qualquer IA para alunos: medir a concordância com redações de nota oficial conhecida (Cartilha do
  Participante) e o tempo real no PC de referência (i3-N305, 8 GB).

## Consequências
- Funciona em qualquer escola, mesmo sem orçamento e sem internet.
- A medição de desempenho da IA local neste PC está **pendente** (ROADMAP).
- Se a escola usar IA online, ela precisa informar os responsáveis e cuidar do contrato de tratamento de dados.
