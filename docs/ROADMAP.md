# Roteiro

Atualize este arquivo ao terminar cada etapa. É o primeiro lugar para retomar o trabalho.

## Onde estamos (2026-11-08)

**Fase 1 concluída**, programa renomeado para **TRIunfo** (ADR 0007), aba **Guia da prova** pronta (regras do
Edital nº 64/2026, gestão de tempo e modelo de estudo), **sincronizável** em Configurações (ADR 0008). Revisão de código feita (agent-skills + ponytail).
**Próximo passo:** Fase 3, Redação.

## Fases

| Fase | Conteúdo | Status |
|---|---|---|
| 1 | Banco de questões 2009–2023, prática com filtros, cronômetro, motivo do erro, caderno de erros, painel | ✅ Concluída |
| 2 | Simulado completo (formato de 2 dias), estimativa TRI, revisão espaçada (1/3/7/21 dias), plano de estudos | ⏳ |
| 3 | **Redação** (prioridade do usuário): temas desde 1998, cronômetro, checklist das 5 competências, histórico; correção por IA opcional | ⏳ Próxima |
| 4 | **Modo escola** (prioridade do usuário): servir na rede local, alunos com login simples, painel do professor | ⏳ |
| 5 | Provas 2024/2025 a partir dos PDFs do INEP; classificação por assunto; instalador `.exe`; Raspberry Pi | ⏳ |

## Decisões pendentes
- **IA na redação:** o PC-alvo tem 8 GB de RAM e não tem GPU. Um modelo local é lento e limitado; um modelo na
  nuvem é melhor, mas exige internet e chave. Provavelmente as duas opções, ambas opcionais.

## Pré-requisitos do modo escola (revisão de código, 2026-11-08)
- **Uma conexão SQLite por requisição** (hoje há uma só, compartilhada entre threads; com vários alunos ao mesmo tempo,
  um commit ou rollback de um aluno pode afetar a resposta de outro). Usar `INSERT ... RETURNING id` em `responder`.
- Identificar o aluno (cookie assinado ou código da turma) antes de abrir em `0.0.0.0`; avaliar `TrustedHostMiddleware`.
- `/api/proxima`: não mandar todas as questões vistas na URL (passa do limite em sessões muito longas).
- `esc()` nos campos vindos da fonte que entram no HTML (letra, gabarito) ou validar `A-E` no importador.
- Importador: trocar URLs de imagem pelo regex, não por substring.
- 7 questões vêm com só 4 alternativas da fonte (ids 539, 783, 1305, 2256, 2326, 2475, 2497).

## Melhorias registradas (backlog)
- Edital 2027: editar `app/conteudo/guia.md`, versao 2027.1, e dar push (passo a passo na ADR 0008).
- Navegação inferior fixa no celular (hoje o menu ocupa duas linhas em 390 px).
- Esconder a dica de atalhos de teclado em telas de toque.
- Descrições de texto para as imagens das questões (acessibilidade para cegos; ADR 0005).
- Importador: avisar no fim quantas imagens faltaram, com um resumo.
- Testes automatizados da API (pytest) antes do modo escola.
