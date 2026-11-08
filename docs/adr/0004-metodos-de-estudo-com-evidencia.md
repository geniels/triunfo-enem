# 0004. Funcionalidades guiadas por métodos de estudo com evidência

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
Existem muitos bancos de questões. O diferencial deste projeto deve ser **ajudar o aluno a estudar melhor**,
não só oferecer mais conteúdo. A pesquisa em ciência da aprendizagem tem resultados sólidos sobre o que funciona.

## Decisão
Cada funcionalidade deve se apoiar em pelo menos um destes princípios:

| Princípio | Como aparece no produto |
|---|---|
| **Prática de recuperação** (testar-se em vez de reler) | O núcleo é responder questões; o gabarito só aparece depois. |
| **Revisão espaçada** | Modo "Refazer erros" (já existe); intervalos de 1, 3, 7 e 21 dias (Fase 2). |
| **Prática intercalada** | O padrão é "Todas (misturado)". |
| **Metacognição / análise de erros** | Ao errar, o aluno marca o motivo (conteúdo, atenção, tempo, chute); o painel mostra o padrão. |
| **Simular as condições reais** | Cronômetro por questão (alerta após 3 min); simulado completo de 2 dias (Fase 2). |
| **Entender a nota TRI** | Estimativa TRI e a dica de "não errar as fáceis" (Fase 2). |
| **Redação por competências** | Checklist das 5 competências, temas desde 1998 e correção assistida (Fase 3). |

Fora de escopo por enquanto: gamificação competitiva (rankings entre alunos), que pode desmotivar quem está atrás.
Sequências diárias e metas pessoais são bem-vindas.

## Consequências
- Funcionalidades novas devem dizer qual princípio atendem. Se não atendem nenhum, questionar.
- O motivo do erro só é útil se o aluno marcar; a interface precisa tornar isso rápido (um toque).
