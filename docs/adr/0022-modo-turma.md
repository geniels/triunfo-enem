# 0022. Modo turma: estudar em grupo na rede local, com nome e PIN

- **Status:** Aceita
- **Data:** 2026-11-10
- **Altera:** ADR 0010 (a edição "Escola" passa a ser o **modo turma**)

## Contexto
A Fase 4 previa um "modo escola". O mesmo recurso serve a uma escola, a um cursinho ou a um grupo de amigos que
estudam juntos, então o nome "escola" limitava. Quem usa costuma entrar pelo notebook. Não há e-mail nem senha
forte: o público é adolescente, sem conhecimento técnico (ADR 0010). Os dados não podem sair do computador (LGPD,
ADR 0011).

## Decisão
- **Nome:** "modo turma". Quem abre a turma no próprio PC é o **organizador** (professor ou um dos amigos).
- **Sem mudança para quem estuda sozinho:** o servidor normal continua só em `127.0.0.1`, sem login. Quem usa o
  PC do organizador é o aluno 1 ("Eu").
- **Abrir turma** (Configurações) sobe um **segundo servidor** em `0.0.0.0`, nas portas 8780 a 8789, só enquanto a
  turma estiver aberta. O TRIunfo mostra o endereço (`http://IP:porta`) para os colegas digitarem. Fechar a turma
  ou o programa derruba esse servidor.
- **Tudo o que chega pelo servidor da turma exige login.** Isso vale até para requisições do próprio PC por esse
  endereço. A separação é pela porta de chegada, e não pelo IP; com `proxy_headers=False`, ninguém finge outro
  endereço por cabeçalho.
- **Login = nome + PIN de 4 dígitos.** Na 1ª vez, a pessoa escolhe "Primeira vez" e cria o PIN. Depois, o aparelho
  fica lembrado (cookie `HttpOnly`, `SameSite=Strict`, assinado com HMAC-SHA256; a chave é gerada no `aluno.db`).
  O nome é único, sem diferenciar maiúsculas.
- **PIN guardado como PBKDF2-SHA256** (200 mil iterações, sal aleatório). Depois de 5 PINs errados seguidos, aquele
  nome espera 60 s.
- **Esqueceu o PIN:** o organizador clica em "Novo PIN" e passa o número para a pessoa. O hash do PIN entra na
  assinatura do cookie, então os aparelhos lembrados saem sozinhos. Não existe recuperação por e-mail.
- **Só o organizador**, no próprio PC, abre ou fecha a turma, vê os participantes, gera PIN novo, remove
  participante (o que apaga o progresso dele), atualiza o programa e sincroniza o guia. Pela rede, essas rotas
  respondem 403.
- QR code descartado: os participantes entram principalmente pelo notebook, onde digitar o endereço é simples.

## Consequências
- Cada aluno tem o próprio progresso. Todas as consultas já filtravam por `aluno_id`, que agora vem da requisição.
- Com o PIN de 4 dígitos e a espera, o modelo protege contra o colega curioso, não contra um ataque dedicado. É
  adequado para uma rede local de confiança, e o dado protegido é o progresso de estudo.
- O Windows pergunta sobre o Firewall na 1ª vez que a turma abre. A tela orienta a marcar "Redes privadas" e
  permitir. Em PCs de escola sem permissão de administrador, essa liberação pode precisar do responsável pela TI.
  Isso ainda precisa ser confirmado no PC de referência.
- Redes Wi-Fi com "isolamento de clientes" (comum em redes de visitante) impedem os aparelhos de se enxergarem. A
  mensagem de erro da tela de entrada lembra de conferir o Wi-Fi.
- Próximos passos: painel do organizador por área e por pessoa; ver a turma sem precisar abrir as Configurações.
