# 0001. Registrar decisões com ADRs

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
O projeto é desenvolvido em sessões com um agente de IA (Claude Code), com pausas entre elas.
Cada sessão nova começa sem memória do que foi discutido. O projeto também pretende ser aberto
e, quem sabe, adotado por redes públicas de ensino: outras pessoas precisarão entender as escolhas.

## Decisão
- Toda decisão que afete arquitetura, dados, dependências, público-alvo ou identidade vira uma ADR
  em `docs/adr/`, numerada e em português.
- O plano de fases e o "próximo passo" ficam em `docs/ROADMAP.md`, atualizado ao fim de cada etapa.
- O arquivo `CLAUDE.md` na raiz aponta para esses dois documentos, para que qualquer sessão de agente
  carregue o contexto automaticamente.

## Consequências
- Retomar o projeto = ler `CLAUDE.md` → `ROADMAP.md` → ADRs relevantes.
- Custo: escrever um texto curto a cada decisão relevante. Decisões pequenas (nome de variável,
  ajuste de CSS) **não** viram ADR.
