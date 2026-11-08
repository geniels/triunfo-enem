# CLAUDE.md

Plataforma offline de estudo para o ENEM: **TRIunfo**, slogan "Bora, ENEM!" (ADR 0007).
Autor: Geniel Bonfim (GitHub: geniels). Commits só em nome dele, **sem** linha Co-Authored-By. Comunicação com o usuário em **português**.

## Antes de começar qualquer tarefa
1. Leia `docs/ROADMAP.md`: onde estamos e qual é o próximo passo.
2. Consulte as ADRs relevantes em `docs/adr/`. Não contrarie uma ADR aceita sem propor uma nova.
3. Ao terminar uma etapa: atualize o ROADMAP, crie uma ADR se houve decisão relevante e faça o commit.

## Comandos
```powershell
.\iniciar.bat                                            # prepara tudo e abre http://localhost:8000
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
.\.venv\Scripts\python.exe scripts\importar_enem_dev.py  # (re)importa questões e imagens
playwright-cli open http://localhost:8000                # testar a interface (desktop e 390 px)
.\.venv\Scripts\python.exe -m unittest discover tests   # testes
```

## Regras do projeto
- Sem CDN e sem build no frontend. Tudo precisa funcionar offline (ADR 0002).
- O gabarito nunca vai ao navegador antes da resposta (ADR 0003).
- Toda tela nova cumpre os requisitos de acessibilidade da ADR 0005; verifique com o playwright-cli antes de concluir.
- Funcionalidade nova deve atender um princípio de estudo da ADR 0004.
- `data/` (banco e imagens) não é versionado.
- Regras do edital ficam em `app/conteudo/guia.md`; ao mudar, aumente `versao` (ADR 0008).
