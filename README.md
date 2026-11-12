# TRIunfo — Bora, ENEM!

Plataforma **gratuita, aberta e offline** para estudar para o ENEM com as **questões oficiais** das provas, um
**simulado com a nota TRI calculada como o INEP calcula** e um **método de estudo** que mostra ao aluno o que
estudar, quando revisar e como se sair melhor no dia da prova.

## Por que existe

O material para estudar para o ENEM está espalhado, muitas vezes é pago e quase sempre exige internet boa. O TRIunfo
reúne as provas oficiais num só lugar, roda em computadores modestos e **funciona sem internet**. Foi pensado para
ser usado por estudantes sozinhos e, no futuro, em turma (escolas, cursinhos ou amigos): um PC pode atender uma sala inteira.

O nome junta a **TRI** (Teoria de Resposta ao Item, o método de correção do ENEM) com "triunfo".

## Como usar (Windows)

1. Baixe o **TRIunfo-Estudante** na [página de versões](https://github.com/geniels/triunfo-enem/releases/latest).
2. Dê dois cliques e avance. Não precisa de senha de administrador.
3. Abra pelo atalho **TRIunfo ENEM** no Menu Iniciar ou na Área de Trabalho. Ele abre no navegador.

Tudo já vem dentro do instalador (questões, imagens e parâmetros da nota TRI): **funciona sem internet desde o
primeiro minuto**. Para atualizar, instale a versão nova por cima: seu progresso é mantido.

> O Windows pode mostrar "O Windows protegeu o computador", porque o instalador ainda não tem assinatura digital.
> Clique em **Mais informações** e depois em **Executar assim mesmo**. Para conferir o arquivo, compare o SHA-256
> publicado junto com a versão.

### Assinatura de código

O instalador é gerado de forma automática e pública no GitHub Actions, a partir deste repositório. O projeto está
se candidatando à assinatura gratuita para código aberto da **SignPath Foundation**: depois de aprovado, as versões
virão com *free code signing provided by [SignPath.io](https://signpath.io), certificate by
[SignPath Foundation](https://signpath.org)*.

## O que o TRIunfo faz

**Estudar com questões oficiais**
- **Praticar**: 2.749 questões do ENEM de 2009 a 2023, nas quatro áreas, com filtro por área, ano e língua
  estrangeira. Modos: questões novas, revisão do dia, refazer erros e todas.
- **Gabarito só depois de responder**, cronômetro por questão (fica vermelho após 3 minutos, o ritmo da prova) e
  marcação de **por que errou**: conteúdo, atenção, tempo ou chute.
- **Rascunho com caneta**: risque alternativas, sublinhe e faça contas por cima da questão, com Apple Pencil,
  caneta do Windows, dedo ou mouse, como no caderno da prova.
- **Caderno de erros** automático e **painel de desempenho** por área, com tempo médio, motivos dos erros e
  histórico dos últimos 14 dias.

**Treinar como no dia da prova**
- **Simulado**: um dia inteiro de prova de um ano, na ordem e no tempo oficiais (5h30 no 1º dia, 5h no 2º), com
  cartão-resposta, numeração oficial e marcação para revisar (técnica das duas passadas).
- **Nota TRI**: calculada com os parâmetros oficiais de cada questão publicados pelo INEP. Conferida contra notas
  oficiais de participantes reais, com diferença média abaixo de 1 ponto. Quando não dá para garantir a nota de um
  ano ou área, o TRIunfo não mostra uma nota inventada.

**Estudar com método**
- **Plano de estudos**: informe a data da prova e as horas livres por semana. O TRIunfo monta um ciclo de blocos de
  50 minutos que dá mais tempo às áreas em que você mais erra, com redação semanal e simulados conforme a fase
  (base, simulados, reta final, semana da prova).
- **Revisão do dia**: as questões erradas voltam em 1, 3, 7 e 21 dias. As mais fáceis vêm primeiro, porque na TRI
  errar questão fácil pesa mais.

**Redação**
- Temas oficiais de 1998 a 2026, folha pautada com cronômetro e contador de linhas (avisa abaixo de 8 e acima de
  30), salvamento automático e **autoavaliação pelas 5 competências**, com nota estimada e histórico.

**Guia da prova**
- Regras do edital do ano (horários, documentos, caneta, o que elimina, redação nota zero), com o número de cada
  item do edital. Também gestão de tempo nos dois dias e um modelo de estudo com base em evidências.
- As **Regras de ouro** aparecem também na tela inicial.

**Configurações**
- Tema claro, escuro ou automático e quatro cores de destaque.
- Botão **Verificar atualizações**: atualiza o guia quando sai um edital novo e, se houver versão nova do programa,
  oferece **Atualizar agora**: baixa, confere a integridade e instala, mantendo o progresso.
- **Lembrete de versão nova** na tela inicial: o TRIunfo confere no máximo uma vez por dia, se houver internet, e
  nunca instala nada sem o clique. Dá para desligar em Configurações.

**Acessibilidade**: funciona no celular, pode ser usado só pelo teclado, tem foco visível e não comunica nada apenas
por cor.

## Privacidade

Tudo fica no computador do aluno: respostas, redações e plano de estudos não são enviados a lugar nenhum. A internet
só é usada para conferir se há versão nova (no máximo uma vez por dia, desligável), quando o aluno pede
(verificar atualizações) ou na primeira preparação para desenvolvedores. Nenhum dado
de estudante vai para serviços que o usem para treinar inteligência artificial (LGPD). Detalhes na
[política de privacidade](PRIVACIDADE.md).

## Edições

| | Estudante | Modo turma (em desenvolvimento) |
|---|---|---|
| Para quem | Quem estuda sozinho | Uma escola, um cursinho ou um grupo de amigos que estudam juntos |
| Quem organiza | Ninguém: instalar, abrir e usar | O organizador (professor ou um dos amigos) abre a turma no seu PC |
| Como entra | Direto | Pelo navegador, na mesma rede Wi-Fi, com nome e PIN de 4 dígitos |

## Roteiro

| Fase | Conteúdo | Status |
|---|---|---|
| 1 | Banco de questões, prática, caderno de erros, painel | ✅ |
| 2 | Simulado, nota TRI oficial, revisão espaçada, plano de estudos | ✅ |
| 3 | Redação: temas, escrita e autoavaliação ✅ · correção por IA local, opcional ⏳ | ▶️ |
| 4 | Modo turma: estudar em grupo na rede local, painel do organizador | ⏳ |
| 5 | Instalador da edição Estudante ✅ · atualização em 1 clique ✅ · provas 2024/2025, questões por assunto ⏳ | ▶️ |

O roteiro detalhado e as decisões do projeto estão em [docs/ROADMAP.md](docs/ROADMAP.md) e [docs/adr/](docs/adr/README.md).

## Para desenvolvedores

Com o Python 3.12 instalado, dê dois cliques em **`iniciar.bat`**. Ele prepara o ambiente, baixa as questões, as
imagens e os parâmetros da nota TRI na primeira vez e abre <http://localhost:8000>.

Manualmente, em qualquer sistema:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip
.venv/bin/python scripts/importar_enem_dev.py    # questões e imagens (enem.dev)
.venv/bin/python scripts/importar_tri.py         # parâmetros da nota TRI (microdados do INEP, ~30 MB)
.venv/bin/python -m uvicorn app.main:app --port 8000
.venv/bin/python -m unittest discover tests      # testes
```

Gerar o instalador (Windows, requer o Inno Setup 6): `.venv\Scripts\python.exe instalador\construir.py`.

### Estrutura

```
app/main.py            API (FastAPI) e servidor da interface
app/db.py              bancos SQLite: data/questoes.db (conteúdo) e data/aluno.db (progresso do aluno)
app/tri.py             nota TRI (modelo de 3 parâmetros, estimativa EAP)
app/revisao.py         calendário da revisão espaçada
app/plano.py           plano de estudos em ciclo
app/redacao.py         regras da autoavaliação da redação
app/guia.py            guia da prova e sincronização
app/versao.py          versão do programa e aviso de versão nova
app/conteudo/          guia da prova (Markdown) e temas/grade da redação (JSON)
app/static/            interface (HTML, CSS e JavaScript puros, sem dependências externas)
scripts/               importadores de questões (enem.dev) e de parâmetros TRI (INEP)
instalador/            lançador, script de montagem e instalador (Inno Setup)
tests/                 testes automatizados
docs/                  roteiro e registros de decisão (ADRs)
```

Antes de contribuir, leia o [CLAUDE.md](CLAUDE.md) (regras do projeto) e as ADRs.

## Fontes dos dados

- Provas, gabaritos, editais e microdados (parâmetros TRI e notas usadas na conferência):
  [INEP](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem) (dados públicos).
- Questões estruturadas: projeto comunitário [enem.dev](https://enem.dev). Algumas imagens estão faltando na fonte
  e aparecem como *"imagem indisponível"*.

## Licença

[MIT](LICENSE): uso, cópia e modificação livres, inclusive por escolas e órgãos públicos.
