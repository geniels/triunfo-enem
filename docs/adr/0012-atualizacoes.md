# 0012. Atualizações: conteúdo pelo botão, programa com aviso e instalação verificada

- **Status:** Aceita. Alterada pela ADR 0024: lembrete de versão nova na tela inicial, com consulta automática
  diária (desligável)
- **Data:** 2026-11-08

## Contexto
Conteúdo (guia do edital, temas) muda todo ano; o programa muda a cada versão. Um programa que baixa e executa o
próprio código sozinho é uma porta para ataques: se alguém adulterar o pacote, todos os PCs executam o código
adulterado. E o aluno não tem como avaliar isso (ADR 0010).

## Decisão
- **Um botão só**, em Configurações: **"Verificar atualizações"**. Só usa a internet quando o aluno toca nele.
- **Conteúdo:** atualizado na hora, validado e só se for de versão maior (ADR 0008).
- **Programa:** o botão consulta a última *release* publicada em `github.com/geniels/triunfo-enem/releases` e, se for
  mais nova que `app/versao.py`, **avisa** com o link do que mudou. Nada é baixado nem executado automaticamente.
  O link só é exibido se apontar para o repositório oficial.
- **Aplicação em 1 clique** virá com o instalador (Fase 5): baixar o pacote da release, **conferir a integridade**
  (hash SHA-256 publicado na release; depois, assinatura digital) e aplicar só ao reabrir o programa, mantendo `data/`.

## Como publicar uma versão
1. Aumente `VERSAO` em `app/versao.py` (ex.: `0.4.0`), rode os testes, faça commit e push.
2. `gh release create v0.4.0 --title "TRIunfo 0.4.0" --notes "o que mudou, em linguagem para alunos"`.

## Consequências
- Hoje o aluno fica sabendo que há versão nova, mas a atualização em si ainda depende de alguém baixar o pacote.
- Proteger a branch `main` e as releases quando houver mais colaboradores.
