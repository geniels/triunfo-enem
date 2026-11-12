# 0024. Lembrete de versão nova na tela inicial

- **Status:** Aceita
- **Data:** 2026-11-11
- **Altera:** ADR 0012 (antes, a internet só era usada quando o aluno tocava em "Verificar atualizações")

## Contexto
A atualização em 1 clique (ADR 0019) só acontecia se a pessoa abrisse Configurações e tocasse em "Verificar
atualizações". Quem nunca fizesse isso ficaria para sempre na versão antiga, sem correções. O autor pediu que o
programa lembre a pessoa quando houver versão nova.

## Decisão
- Ao abrir a tela inicial, o TRIunfo consulta a versão mais recente no GitHub **no máximo uma vez por dia**, em
  segundo plano, sem atrasar a tela. Sem internet, não mostra nada e tenta de novo em 6 horas. O resultado fica
  guardado no `aluno.db` (`config`).
- Se houver versão nova, aparece uma **faixa de lembrete no Início** com **Atualizar agora** (o mesmo fluxo da ADR
  0019: baixa, confere o SHA-256 e instala) e **Agora não**, que esconde o lembrete daquela versão por 3 dias
  (preferência do navegador).
- **Nada é baixado nem instalado sem o clique.** A consulta automática só lê a página pública da versão; nenhum dado
  do aluno é enviado.
- **Opção em Configurações:** "Avisar na tela inicial quando houver versão nova", ligada por padrão. Desligada, o
  TRIunfo volta a usar a internet só quando a pessoa pede.
- **No modo turma**, os participantes não recebem o lembrete nem acessam a opção: quem atualiza é o organizador, no
  PC dele.

## Consequências
- A consulta diária faz o GitHub receber o IP do computador uma vez por dia. Isso está documentado no
  `PRIVACIDADE.md`, junto com como desligar.
- A edição Estudante continua sem exigir nenhuma configuração (ADR 0010): o padrão já funciona.
- O lembrete só chega a quem tem a versão 0.5.2 ou mais nova. Quem está numa versão anterior precisa atualizar uma vez
  por Configurações.
