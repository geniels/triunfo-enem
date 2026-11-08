# TRIunfo — Bora, ENEM!

Plataforma **gratuita e offline** para estudar para o ENEM com as questões oficiais das provas,
organizadas pelas quatro áreas do exame, mais um módulo de redação.

Roda no próprio computador e abre no navegador. Um único PC também pode atender uma sala inteira pela
rede local (modo escola, em desenvolvimento).

## Como usar (Windows)

1. Instale o [Python 3.12+](https://www.python.org/downloads/) e marque **"Add python.exe to PATH"**.
2. Baixe este projeto e dê dois cliques em **`iniciar.bat`**.
3. Na primeira vez, ele baixa as questões (cerca de 2.700, de 2009 a 2023), as imagens e os parâmetros da nota TRI (cerca de 30 MB). Depois disso, **funciona sem internet**.
4. O navegador abre em <http://localhost:8000>.

### Manualmente (qualquer sistema)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip
.venv/bin/python scripts/importar_enem_dev.py    # baixa questões + imagens
.venv/bin/python -m uvicorn app.main:app --port 8000
```

## O que já funciona (Fase 1)

- **Praticar**: questões sorteadas, com filtro por área, ano e língua estrangeira (inglês ou espanhol). Modos *novas*, *refazer erros* e *todas*.
- **Cronômetro por questão**, que fica vermelho depois de 3 minutos (o ritmo médio da prova).
- **Gabarito só depois de responder**, e o aluno marca **por que errou** (conteúdo, atenção, tempo ou chute).
- **Caderno de erros automático**: a questão sai do caderno quando o aluno acerta de novo.
- **Painel de desempenho**: acertos por área, tempo médio, motivos dos erros e histórico dos últimos 14 dias.
- **Simulado**: um dia de prova inteiro de um ano, com tempo e numeração oficiais, cartão-resposta, marcação para revisar e **nota TRI calculada com os parâmetros oficiais do INEP** (conferida contra notas reais: diferença média abaixo de 1 ponto).
- **Redação**: temas oficiais de 1998 a 2026, folha pautada com cronômetro e contador de linhas, salvamento automático, autoavaliação pelas 5 competências com nota estimada e histórico.
- **Guia da prova**: regras do edital do ano, gestão de tempo e modelo de estudo. Atualizável pela internet em Configurações, sem reinstalar.
- Atalhos de teclado (A–E, Enter), tema claro e escuro, funciona no celular.

## Roteiro

| Fase | Conteúdo |
|---|---|
| 1 ✅ | Banco de questões, prática, caderno de erros, estatísticas |
| 2 | Simulado completo cronometrado (formato de 2 dias), estimativa de nota TRI, revisão espaçada, plano de estudos |
| 3 | Redação: banco de temas desde 1998, checklist pelas 5 competências, correção assistida por IA (opcional) |
| 4 | Modo escola: vários alunos na rede local, painel do professor |
| 5 | Provas 2024 e 2025 a partir dos PDFs do INEP; classificação das questões por assunto; instalador |

## Estrutura

```
app/main.py                 API (FastAPI) + serve a interface
app/db.py                   esquema do banco SQLite (data/enem.db)
app/static/                 interface web (HTML/CSS/JS puro, sem dependências externas)
scripts/importar_enem_dev.py  importa questões e imagens
iniciar.bat                 inicializador de dois cliques para Windows
```

## Fontes dos dados

- Provas e gabaritos: [INEP](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos) (documentos públicos).
- Questões estruturadas: projeto comunitário [enem.dev](https://enem.dev).
  Algumas imagens estão faltando na fonte e aparecem como *“imagem indisponível”*.
