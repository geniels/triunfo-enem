# 0005. Acessibilidade como requisito, não como extra

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
Um programa educacional, sobretudo se adotado pelo poder público, precisa atender alunos com deficiência
(a Lei Brasileira de Inclusão, 13.146/2015, e o padrão eMAG do governo exigem isso). Uma auditoria com a skill
`ui-ux-pro-max` sobre a Fase 1 encontrou três problemas:
1. Alternativa certa ou errada indicada **só pela cor** (verde/vermelho), o que falha para daltônicos.
2. `aria-live` na área principal: o leitor de tela anunciaria o cronômetro **a cada segundo**.
3. Foco do teclado sem estilo consistente nos botões personalizados.

## Decisão
- Corrigidos: selos em texto ("Correta", "Sua resposta"); `aria-live` só na caixa de retorno da resposta;
  cronômetro com `role="timer"`; `:focus-visible` global com contorno de 3 px.
- Requisitos mínimos para toda tela nova (base WCAG 2.2 AA):
  - contraste de texto de pelo menos 4,5:1 nos temas claro e escuro;
  - nada comunicado só por cor;
  - tudo utilizável pelo teclado, com foco visível;
  - funcionar em 390 px de largura sem rolagem horizontal;
  - imagens das questões com texto alternativo (a fonte quase nunca traz; ver Consequências);
  - respeitar `prefers-reduced-motion` se houver animações.
- Antes de concluir uma fase, testar no navegador real com `playwright-cli` (desktop e celular).

## Consequências
- As imagens das questões vêm sem descrição na fonte. Para alunos cegos, isso é uma lacuna real e exige
  descrições escritas (trabalho futuro, com possível ajuda de IA e revisão humana).
- Em telas pequenas, a navegação ocupa duas linhas; avaliar uma barra inferior (registrado no ROADMAP).
