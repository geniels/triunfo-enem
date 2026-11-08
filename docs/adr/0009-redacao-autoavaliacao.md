# 0009. Redação: escrita cronometrada e autoavaliação guiada, antes de qualquer IA

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
A redação vale até 1.000 pontos e é a prova em que o treino mais muda a nota. O aluno precisa escrever com
frequência e entender **por que** perdeu pontos. Uma correção por IA ajudaria, mas o PC-alvo (8 GB, sem GPU) roda
modelos locais lentos e limitados, e a IA na nuvem exige internet e chave (ver ROADMAP).

## Decisão
- **Temas:** os temas oficiais de 1998 a 2026 (inclusive reaplicações, quando conhecidas) ficam em
  `app/conteudo/redacao.json`, junto com a grade das 5 competências. Conferidos em duas fontes; nas divergências de
  pontuação, prevaleceu a forma do INEP.
- **Escrita:** editor com folha pautada, cronômetro com meta de 1h20 (Guia da prova), sem corretor ortográfico
  (como na prova) e salvamento automático a cada 10 s e ao sair da tela.
- **Linhas:** estimativa de 70 letras por linha manuscrita. Avisa abaixo de 8 linhas (nota zero, edital 14.7.3) e
  acima de 30 (não cabe na folha). É uma estimativa, e a interface diz isso.
- **Autoavaliação:** para cada competência, o aluno escolhe um dos 6 níveis (0 a 200) descritos em linguagem simples.
  Na C5, marcar os 5 elementos da proposta (agente, ação, modo, efeito, detalhamento) sugere o nível (40 por elemento).
  A nota estimada e o histórico mostram a evolução. O servidor só aceita notas c1..c5 nos níveis válidos.
- A correção por IA (Fase 3.3) virá **por cima** disso, como segunda opinião opcional; a autoavaliação continua sendo
  o exercício principal (metacognição, ADR 0004).

## Consequências
- Funciona 100% offline e em qualquer PC.
- A autoavaliação depende da honestidade do aluno; a interface pede que ele seja exigente. Professores (modo escola)
  poderão avaliar a mesma redação no futuro, comparando a nota com a do aluno.
- Os temas e a grade podem ser atualizados pelo mesmo mecanismo do guia (ADR 0008) quando isso for implementado para este arquivo.
