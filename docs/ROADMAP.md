# Roteiro

Atualize este arquivo ao terminar cada etapa. É o primeiro lugar para retomar o trabalho.

## Onde estamos (2026-11-08)

**Fase 1 concluída** e verificada no navegador (desktop e 390 px).
**Próximo passo:** definir o nome do programa (pendente, ver abaixo) e começar a Fase 3, Redação.

## Fases

| Fase | Conteúdo | Status |
|---|---|---|
| 1 | Banco de questões 2009–2023, prática com filtros, cronômetro, motivo do erro, caderno de erros, painel | ✅ Concluída |
| 2 | Simulado completo (formato de 2 dias), estimativa TRI, revisão espaçada (1/3/7/21 dias), plano de estudos | ⏳ |
| 3 | **Redação** (prioridade do usuário): temas desde 1998, cronômetro, checklist das 5 competências, histórico; correção por IA opcional | ⏳ Próxima |
| 4 | **Modo escola** (prioridade do usuário): servir na rede local, alunos com login simples, painel do professor | ⏳ |
| 5 | Provas 2024/2025 a partir dos PDFs do INEP; classificação por assunto; instalador `.exe`; Raspberry Pi | ⏳ |

## Decisões pendentes
- **Nome do programa.** "ENEM Estudo" é genérico. Ideias em discussão: *Nem Desisto*, *TRIunfo*, *Tanto Bate*.
  Quando escolhido: criar ADR, renomear interface, README e pasta, e só então definir a identidade visual
  (cores e logo) com a skill de UI/UX.
- **IA na redação:** o PC-alvo tem 8 GB de RAM e não tem GPU. Um modelo local é lento e limitado; um modelo na
  nuvem é melhor, mas exige internet e chave. Provavelmente as duas opções, ambas opcionais.

## Melhorias registradas (backlog)
- Navegação inferior fixa no celular (hoje o menu ocupa duas linhas em 390 px).
- Esconder a dica de atalhos de teclado em telas de toque.
- Descrições de texto para as imagens das questões (acessibilidade para cegos; ADR 0005).
- Importador: avisar no fim quantas imagens faltaram, com um resumo.
- Testes automatizados da API (pytest) antes do modo escola.
