# 0025. O dono do PC usa o mesmo progresso no tablet ou celular

- **Status:** Aceita
- **Data:** 2026-11-11
- **Altera:** ADR 0022 (o dono do PC não podia entrar pela rede)

## Contexto
Um retorno de uso: o estudante tentou abrir o TRIunfo no iPad pelo endereço `127.0.0.1` e não conseguiu. Só
abriu depois de ativar o modo turma. Não era o firewall: `127.0.0.1` (ou `localhost`) é sempre "o próprio aparelho",
então no iPad aponta para o iPad. O servidor normal só atende o PC (ADR 0010), e a única porta para outros
aparelhos é o servidor da turma (ADR 0022).

Pela ADR 0022, porém, o dono do PC (aluno 1) nunca entrava pela rede. Um estudante que estuda sozinho precisava
criar outro participante no iPad, com o progresso separado do que fez no computador.

## Decisão
- Em Configurações, a seção passa a se chamar **"Outros aparelhos e turma"** e explica os dois usos: o seu tablet ou
  celular com o mesmo progresso, ou colegas, cada um com o seu. O botão vira **"Abrir acesso pela rede"**, e a tela
  avisa que endereços com 127.0.0.1 ou localhost só funcionam no próprio computador.
- **"Seu acesso nos outros aparelhos":** o dono do PC escolhe um nome e um PIN (`PUT /api/turma/meu-acesso`, só
  no próprio PC). No outro aparelho, ele entra com esse nome e PIN como **aluno 1**: o mesmo progresso, os mesmos
  rascunhos e os mesmos simulados.
- Enquanto o dono não cria o PIN, o aluno 1 continua sem entrar pela rede, como antes.
- **As funções de administração continuam só no PC**, mesmo para o dono entrando pela rede: atualizar o programa,
  abrir ou fechar o acesso, ver participantes, gerar PIN e remover. O bloqueio depende da porta por onde a
  requisição chega, e não de quem entrou. Assim, um PIN de 4 dígitos descoberto não dá controle do programa.
- Esqueceu o PIN? O dono troca em Configurações, no PC. Trocar o PIN tira os aparelhos lembrados.

## Consequências
- O estudante independente usa o tablet sem perder nada do que fez no computador.
- O PC precisa estar ligado, com o TRIunfo aberto e o acesso pela rede ligado, e os dois aparelhos na mesma rede
  Wi-Fi. É a consequência de funcionar sem internet e sem servidor na nuvem.
- Numa turma, os colegas também conseguiriam tentar o nome do dono. A espera depois de 5 PINs errados vale para ele
  também.
