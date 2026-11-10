# 0023. Rascunho com caneta sobre a questão

- **Status:** Aceita
- **Data:** 2026-11-10

## Contexto
Na prova, o aluno risca alternativas, sublinha o texto e faz contas no próprio caderno. Na tela, isso não era
possível. Quem estuda em tablet (iPad com Apple Pencil) ou em notebook com caneta quer o mesmo gesto. Atende o
princípio de **prática ativa** e de treinar nas condições da prova (ADR 0004). Precisa funcionar offline, sem
biblioteca (ADR 0002).

## Decisão
- Um botão flutuante **"✏️ Rascunho"** na prática e no simulado. Aberto, mostra caneta, marca-texto, borracha (apaga
  o traço inteiro que tocar), desfazer e limpar. Fechado, os rabiscos continuam visíveis e as alternativas voltam a
  ser clicáveis.
- Uma camada `<canvas>` transparente cobre a questão do topo até o fim das alternativas. Os botões de confirmar
  ficam fora dela, para continuarem clicáveis.
- **Pointer Events.** Quando o navegador vê uma caneta (`pointerType = "pen"`), só a caneta desenha, e o dedo passa
  a rolar a página (rolagem feita pelo próprio código, porque a camada usa `touch-action: none`). Sem caneta (celular,
  mouse), dedo e mouse desenham.
- Os traços são guardados em coordenadas relativas à largura: redesenham certo ao girar o tablet, redimensionar a
  janela ou carregar imagens. A caneta usa a cor de destaque do tema e acompanha a troca de tema; o marca-texto
  fica por baixo da caneta.
- **Só na memória da página:** no simulado, o rabisco continua ao ir e voltar entre questões; recarregar a página
  apaga. Nada vai ao servidor nem ao disco, então não há dado novo de aluno (ADR 0011).
- Sair da tela fecha o rascunho. No simulado, trocar de questão o mantém aberto.

## Consequências
- Com o rascunho aberto, tocar numa alternativa risca em vez de escolher, como no papel. Para responder, o aluno
  fecha o rascunho ou usa as teclas A–E.
- A camada é decorativa (`aria-hidden`). Quem usa leitor de tela continua com a questão e as teclas de sempre, e os
  botões da barra têm nome e estado (`aria-pressed`).
- Testado com eventos simulados de caneta e de toque. Falta confirmar num iPad com Apple Pencil e num notebook
  Windows com caneta de verdade.
- Possível evolução: guardar o rascunho junto com a resposta para revê-lo no caderno de erros.
