# 0020. Identidade visual: troféu com capelo e cara de prova

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
O ícone era um "visto" genérico e a interface não lembrava o ENEM. O autor pediu algo que remeta à prova e ao
triunfo: um troféu junto com o capelo (chapéu de formatura).

## Decisão
- **Ícone** (`app/static/icone.svg`): troféu dourado usando um capelo, sobre o azul do caderno de prova.
  O `.ico` do instalador (`instalador/triunfo.ico`, 16 a 256 px) é gerado do SVG por `instalador/gerar_icone.py`,
  que usa o Chrome para desenhar cada tamanho. O `.ico` fica no repositório.
- **Cores:** azul do caderno (`#1f4fb8`) como cor principal; dourado do troféu (`#ffc61a`) para conquistas, sempre
  como fundo com texto escuro (o dourado sobre branco não teria contraste suficiente).
- **Elementos de prova:** faixa com as cores dos cadernos do ENEM (azul, amarelo, branco, rosa) sob o topo; letras
  das alternativas como as bolinhas ovais do cartão-resposta; marca com o troféu e o slogan "Bora, ENEM!".
- As cores de destaque escolhidas pelo aluno (Configurações) continuam valendo.

## Consequências
- O ícone aparece igual no navegador, no atalho, no instalador e no desinstalador.
- Mudou o ícone? Rode `gerar_icone.py` e gere o instalador de novo.
