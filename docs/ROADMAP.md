# Roteiro

Atualize este arquivo ao terminar cada etapa. É o primeiro lugar para retomar o trabalho.

## Onde estamos (2026-11-08)

**Fase 1 concluída**, programa renomeado para **TRIunfo** (ADR 0007), aba **Guia da prova** pronta (regras do
Edital nº 64/2026, gestão de tempo e modelo de estudo), **sincronizável** em Configurações (ADR 0008). Revisão de código feita (agent-skills + ponytail).
Aparência: tema claro, escuro ou automático e 4 cores de destaque, com engrenagem de Configurações no topo.
**Fase 3 em andamento:** 3.1 (escrever) e 3.2 (autoavaliar) prontas (ADR 0009).
**Fase 2 concluída** (versão 0.4.0): simulado, nota TRI, revisão espaçada e plano de estudos (ADR 0013 a 0016).
**Instalador da edição Estudante pronto** (versão 0.4.1, ADR 0017).
Progresso do aluno separado do banco de questões, com ids fixos (versão 0.4.2, ADR 0018).
Atualização em 1 clique com conferência do SHA-256 (versão 0.4.3, ADR 0019).
**Próximo passo:** modo escola (Fase 4), começando pelos pré-requisitos de segurança. A 3.3 (IA local) aguarda a medição de desempenho.

## Fases

| Fase | Conteúdo | Status |
|---|---|---|
| 1 | Banco de questões 2009–2023, prática com filtros, cronômetro, motivo do erro, caderno de erros, painel | ✅ Concluída |
| 2 | 2.1 simulado por dia, tempo e numeração oficiais ✅ · 2.2 nota TRI com parâmetros oficiais, validada ✅ · 2.3 revisão espaçada (1/3/7/21 dias, fáceis primeiro) ✅ · 2.4 plano de estudos em ciclo ✅ | ✅ Concluída |
| 3 | **Redação**: 3.1 temas desde 1998, editor pautado, cronômetro, linhas, salvamento ✅ · 3.2 autoavaliação pelas 5 competências e histórico ✅ · 3.3 correção por IA opcional ⏳ | ▶️ Em andamento |
| 4 | **Modo escola** (prioridade do usuário): servir na rede local, alunos com login simples, painel do professor | ⏳ |
| 5 | **Instalador `.exe` da edição Estudante** ✅ (v0.4.1) · atualização em 1 clique ✅ · provas 2024/2025; classificação por assunto; Raspberry Pi | ⏳ |

## Decisões tomadas em 2026-11-08
- **Duas edições** (ADR 0010): Estudante (zero administração) e Escola (configurada por um responsável).
- **IA na redação** (ADR 0011): local por padrão, apontando o que revisar sem dar nota; online só na edição Escola,
  com conta paga. Planos gratuitos que usam os dados para treino estão vetados (LGPD).
- **Atualizações** (ADR 0012): botão único "Verificar atualizações"; o programa avisa sobre versão nova; aplicação em
  1 clique virá com o instalador.

## Pendências anotadas
- **Medir a IA local no PC de referência** (i3-N305, 8 GB): tempo por redação, uso de memória e concordância com
  redações de nota oficial conhecida. Pré-requisito da Fase 3.3.

## Pré-requisitos do modo escola (revisão de código, 2026-11-08)
- **Uma conexão SQLite por requisição** (hoje há uma só, compartilhada entre threads; com vários alunos ao mesmo tempo,
  um commit ou rollback de um aluno pode afetar a resposta de outro). Usar `INSERT ... RETURNING id` em `responder`.
- Identificar o aluno (cookie assinado ou código da turma) antes de abrir em `0.0.0.0`; avaliar `TrustedHostMiddleware`.
- `/api/proxima`: não mandar todas as questões vistas na URL (passa do limite em sessões muito longas).
- `esc()` nos campos vindos da fonte que entram no HTML (letra, gabarito) ou validar `A-E` no importador.
- Importador: trocar URLs de imagem pelo regex, não por substring.
- 7 questões vêm com só 4 alternativas da fonte (ids 539, 783, 1305, 2256, 2326, 2475, 2497).

## Melhorias registradas (backlog)
- Teste automatizado do simulado (montagem do dia, validação das respostas, resultado), com banco temporário.
- TRI: cobertura atual de 47 das 60 combinações ano/área (2009–2023). Sem nota: 2009 CN/CH, 2016 CN/CH/LC e 2017
  (a ordem do enem.dev não casa com nenhum caderno oficial); 2011 CN, 2013 MT, 2018 CN e 2019 MT (o ajuste não confere
  com a escala do INEP, causa a investigar: provavelmente a ordem das respostas no arquivo de participantes).
- TRI no treino livre: mostrar a dificuldade (parâmetro b) de cada questão e priorizar as fáceis erradas.
- Redação: gráfico da evolução da nota; dica da competência mais fraca; sincronizar `redacao.json` como o guia.
- "Conferir minha prova": o aluno informa a cor do caderno e as respostas e recebe os acertos (precisa dos gabaritos por cor de cada ano, em PDF do INEP). Útil na semana da prova; avaliar na Fase 5.
- Edital 2027: editar `app/conteudo/guia.md`, versao 2027.1, e dar push (passo a passo na ADR 0008).
- Navegação inferior fixa no celular (hoje o menu ocupa duas linhas em 390 px).
- Esconder a dica de atalhos de teclado em telas de toque.
- Descrições de texto para as imagens das questões (acessibilidade para cegos; ADR 0005).
- Importador: avisar no fim quantas imagens faltaram, com um resumo.
- Testes automatizados da API (pytest) antes do modo escola.
