# Registros de Decisão de Arquitetura (ADRs)

Cada ADR registra **uma** decisão importante: o contexto, o que foi decidido e as consequências.
Servem para retomar o projeto depois de uma pausa (ou numa nova sessão com um agente de IA)
sem precisar redescobrir por que as coisas são como são.

## Índice

| Nº | Título | Status |
|---|---|---|
| [0001](0001-registrar-decisoes-com-adrs.md) | Registrar decisões com ADRs | Aceita |
| [0002](0002-app-web-local-offline.md) | App web local e offline (Python + SQLite + JS puro) | Aceita |
| [0003](0003-fonte-de-dados-e-correcoes.md) | Questões do enem.dev, com correções e imagens locais | Aceita |
| [0004](0004-metodos-de-estudo-com-evidencia.md) | Funcionalidades guiadas por métodos de estudo com evidência | Aceita |
| [0005](0005-acessibilidade-como-requisito.md) | Acessibilidade como requisito, não como extra | Aceita |
| [0006](0006-ferramentas-de-desenvolvimento.md) | Ferramentas de desenvolvimento com agentes de IA | Aceita |
| [0007](0007-nome-triunfo.md) | Nome do programa: TRIunfo | Aceita |
| [0008](0008-guia-sincronizavel.md) | Guia da prova em Markdown, sincronizável sob demanda | Aceita |
| [0009](0009-redacao-autoavaliacao.md) | Redação: escrita cronometrada e autoavaliação guiada | Aceita |
| [0010](0010-edicoes-estudante-e-escola.md) | Duas edições: Estudante e Escola | Aceita |
| [0011](0011-ia-na-redacao.md) | IA na redação: local por padrão; online só com conta paga da escola | Aceita |
| [0012](0012-atualizacoes.md) | Atualizações: conteúdo pelo botão, programa com aviso e instalação verificada | Aceita |
| [0013](0013-simulado.md) | Simulado por dia de prova, na ordem e no tempo oficiais | Aceita |
| [0014](0014-nota-tri.md) | Nota TRI com os parâmetros oficiais, validada contra notas reais | Aceita |
| [0015](0015-revisao-espacada.md) | Revisão espaçada com prioridade pela dificuldade TRI | Aceita |
| [0016](0016-plano-de-estudos.md) | Plano de estudos em ciclo, guiado pelos pontos fracos | Aceita |

Plano e próximos passos: [docs/ROADMAP.md](../ROADMAP.md).

## Como escrever uma nova ADR

1. Copie o modelo abaixo para `NNNN-titulo-curto.md` (próximo número livre).
2. Status: `Proposta` → `Aceita` (ou `Rejeitada`). Uma decisão trocada não é apagada:
   a ADR antiga vira `Substituída por NNNN` e a nova explica o porquê.
3. Adicione a linha no índice acima.

```markdown
# NNNN. Título

- **Status:** Proposta | Aceita | Rejeitada | Substituída por NNNN
- **Data:** AAAA-MM-DD

## Contexto
Qual problema ou força nos obriga a decidir?

## Decisão
O que decidimos fazer.

## Consequências
O que fica mais fácil, o que fica mais difícil, o que precisamos acompanhar.
```
