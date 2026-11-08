# 0019. Atualização em 1 clique, com conferência de integridade

- **Status:** Aceita (completa a ADR 0012)
- **Data:** 2026-11-08

## Contexto
O aluno não tem conhecimento técnico (ADR 0010). Baixar o instalador novo e rodá-lo por conta própria é um passo a
mais em que ele pode desistir. Mas um programa que baixa e executa código sozinho é uma porta para ataques.

## Decisão
- Em Configurações → **Verificar atualizações**, se houver versão nova **e** o TRIunfo foi instalado pelo
  instalador (há `unins000.exe` na pasta), aparece **Atualizar agora (N MB)**. Nada acontece sem esse clique.
- O app baixa o `TRIunfo-Estudante-<versão>.exe` e o `.sha256` **somente** de
  `github.com/geniels/triunfo-enem/releases/download/`, confere o SHA-256 e, se não bater, apaga o arquivo e
  não instala nada. Limite de 300 MB.
- Roda o instalador com `/SILENT /REABRIR`: o aluno vê a barra de progresso, o instalador fecha o TRIunfo
  (CloseApplications), atualiza e o reabre. O progresso fica no `aluno.db`, que o instalador não toca (ADR 0018).
- O lançador apaga `data/atualizacao` ao abrir.
- Na versão de desenvolvimento continua só o aviso com o link.

## Limites conhecidos
- O SHA-256 vem do mesmo lugar que o instalador: protege contra download corrompido, mas não contra alguém que
  controle a conta do GitHub. A proteção completa é a **assinatura digital** do instalador, a ser verificada antes
  de executar quando houver certificado.
