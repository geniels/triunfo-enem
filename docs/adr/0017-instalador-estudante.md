# 0017. Instalador da edição Estudante com Python embutido

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
Até aqui, usar o TRIunfo exigia instalar o Python e rodar o `iniciar.bat`, o que não é realista para um estudante
sem conhecimento técnico (ADR 0010). O PC-alvo é modesto (i3, 8 GB), às vezes sem internet e sem senha de
administrador (escolas, lan houses).

## Decisão
- **Um arquivo `TRIunfo-Estudante-<versão>.exe`** gerado pelo Inno Setup (`instalador/triunfo.iss`), montado por
  `instalador/construir.py`.
- **Python embutido oficial** (python.org, "embeddable", mesma versão do `.venv`) com as dependências e o código
  pré-compilados. Evitamos empacotadores como o PyInstaller, que costumam gerar falsos positivos em antivírus.
- **Instala só para o usuário** (`%LOCALAPPDATA%\Programs\TRIunfo`), sem pedir administrador. Atalhos no Menu
  Iniciar e, opcionalmente, na Área de Trabalho.
- **Funciona offline desde o início:** o banco já vem com as 2.749 questões, as imagens e os parâmetros TRI.
  O banco do instalador é uma cópia limpa, sem dados de aluno.
- **Lançador** (`instalador/triunfo.py`): usa as portas 8765–8774, lembra a última porta usada, reabre o navegador
  se o TRIunfo já estiver aberto, e roda numa janela minimizada ("feche esta janela para sair").
- **Atualizar preserva o progresso:** o `enem.db` só é instalado se ainda não existir. Desinstalar pergunta se
  apaga os dados (padrão: manter); desinstalação silenciosa nunca apaga.
- Cada instalador sai com o **SHA-256** publicado junto, para conferência de integridade (ADR 0012).

## Medições (PC de referência, i3-N305, 8 GB)
Instalador de ~93 MB; instalação em ~21 s; ~120 MB instalados; primeira abertura em ~3 s.

## Consequências
- **Sem assinatura digital**, o Windows mostra o aviso do SmartScreen ("O Windows protegeu o computador" →
  "Mais informações" → "Executar assim mesmo"). Para distribuição oficial, assinar com certificado de código.
- **Achado em 2026-11-08:** no PC de referência, com o **Controle Inteligente de Aplicativos** (Smart App Control)
  do Windows 11 ligado, o `unins000.exe` sem assinatura foi **bloqueado** (evento 3077 do Code Integrity), sem
  opção de "executar assim mesmo". O bloqueio depende da reputação de cada arquivo: outras execuções passaram.
  Isso torna a assinatura digital necessária antes de distribuir em escala (ROADMAP).
- (Resolvido pela ADR 0018.) Banco de questões e progresso do aluno estavam no mesmo arquivo: uma versão com questões novas não atualiza o banco
  de quem já instalou. Próximo passo: separar o progresso do aluno num arquivo próprio, ou atualizar as questões
  pelo botão de atualizações.
- Atualização em 1 clique pelo app (ADR 0012) pode agora baixar este instalador e conferir o SHA-256.
