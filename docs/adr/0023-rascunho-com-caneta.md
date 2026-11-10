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
- **Salvo no `aluno.db`** (revisado no mesmo dia; a 1ª versão guardava só na memória da página e perdia tudo ao
  recarregar). Tabela `rascunhos (aluno_id, chave, tracos)`, com chave `q<questão>` na prática e
  `s<simulado>-<questão>` no simulado. O salvamento acontece 1,5 s depois do último traço e na hora ao sair da
  questão (`fetch` com `keepalive`). Limite de 400 KB por questão. No modo turma, cada pessoa só lê e grava o
  próprio rascunho, no PC do organizador (ADR 0022). Remover um participante apaga os rascunhos dele.
- **Na prática:** o rascunho é um por questão e volta quando a questão reaparece (revisão do dia, caderno de
  erros, praticar), para a pessoa ver como pensou da outra vez.
- **Revisão do simulado entregue** (`#simulado/<id>/<questão>`): mostra a resposta, o gabarito e o rascunho, com o
  cartão-resposta ao lado para navegar. Usa o mesmo layout do simulado de propósito: os traços são relativos à
  largura da questão, e outra largura faria o texto quebrar diferente e o risco sair do lugar.
- Sair da tela fecha o rascunho. No simulado, trocar de questão o mantém aberto.

## Consequências
- Com o rascunho aberto, tocar numa alternativa risca em vez de escolher, como no papel. Para responder, o aluno
  fecha o rascunho ou usa as teclas A–E.
- A camada é decorativa (`aria-hidden`). Quem usa leitor de tela continua com a questão e as teclas de sempre, e os
  botões da barra têm nome e estado (`aria-pressed`).
- Testado com eventos simulados de caneta e de toque. Falta confirmar num iPad com Apple Pencil e num notebook
  Windows com caneta de verdade.
- Mudar a largura da janela também muda as quebras de linha do texto: o traço acompanha a proporção, mas pode
  ficar um pouco deslocado do texto. É uma limitação aceita.
- Na revisão do simulado, os selos "Correta" e "Sua resposta" entram nas alternativas e podem deslocar um pouco o
  rascunho, se o texto da alternativa for longo.
