# 0018. Progresso do aluno separado do banco de questões, com ids fixos

- **Status:** Aceita (substitui a parte de dados da ADR 0017)
- **Data:** 2026-11-08

## Contexto
Até a versão 0.4.1, questões e progresso do aluno ficavam no mesmo `data/enem.db`. Para não apagar o progresso, o
instalador não trocava esse arquivo, então **uma versão nova não conseguia trazer questões novas** (ex.: provas de
2024 e 2025). Além disso, o `id` de cada questão era sequencial: um banco recriado em outro PC daria números
diferentes às mesmas questões, e o progresso apontaria para questões erradas.

## Decisão
- **Dois arquivos:** `data/questoes.db` (questões, alternativas, parâmetros TRI, escalas), que o instalador **sempre
  troca**, e `data/aluno.db` (respostas, redações, simulados, plano), criado pelo app e **nunca tocado** pelo
  instalador. O app abre o `aluno.db` e anexa o `questoes.db` (`ATTACH ... AS banco`); as consultas não mudam.
- **Id fixo por questão:** `ano × 10000 + número × 10 + idioma` (0 = comum, 1 = inglês, 2 = espanhol).
  Ex.: ENEM 2022, questão 175 → `20221750`. Igual em qualquer instalação.
- O `questoes.db` não usa WAL: o instalador troca o arquivo, e um `-wal` antigo ao lado corromperia o novo
  (o instalador também apaga `questoes.db-wal`/`-shm`). O `aluno.db` continua em WAL.
- **Migração automática** (`app/db.py: migrar`), na primeira abertura: guarda `enem-antes-da-migracao.db`, copia o
  progresso para o `aluno.db` convertendo os ids (inclusive dentro dos simulados) e transforma o restante no
  `questoes.db`, ou o descarta se o instalador já trouxe um novo.

## Verificação
Testes automatizados da migração (formato de desenvolvimento e atualização pelo instalador) e teste real de
atualização 0.4.1 → 0.4.2 com uma resposta: a resposta continuou ligada à mesma questão (ENEM 2022, nº 169).

## Consequências
- Questões novas chegam com o instalador (e, no futuro, pelo botão de atualizações) sem risco ao progresso.
- O modo escola poderá guardar um `aluno.db` por aluno, ou vários alunos no mesmo arquivo, sem duplicar as questões.
