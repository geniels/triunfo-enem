"""Servidor local do TRIunfo.

Rodar:  python -m uvicorn app.main:app --port 8000
Abrir:  http://localhost:8000
"""
from __future__ import annotations

import json
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import guia
from app.db import AREAS, IMAGENS_DIR, RAIZ, conectar, criar_tabelas

STATIC_DIR = RAIZ / "app" / "static"
ALUNO_PADRAO = 1  # o modo escola (vários alunos) vem numa fase seguinte

con = conectar()
criar_tabelas(con)
IMAGENS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="TRIunfo", version="0.1.0")


@app.middleware("http")
async def sem_cache(request: Request, call_next):
    resposta = await call_next(request)
    # Força o navegador a conferir (304 é barato): sem isso, uma atualização do app não aparece para o aluno.
    resposta.headers["Cache-Control"] = "no-cache"
    return resposta


@app.get("/api/guia")
def ler_guia():
    return guia.atual()


@app.post("/api/guia/sincronizar")
def sincronizar_guia():
    try:
        return guia.sincronizar()
    except OSError:
        raise HTTPException(503, "Não foi possível baixar (sem internet ou servidor fora do ar). O guia atual continua valendo.")
    except ValueError:  # inclui UnicodeDecodeError
        raise HTTPException(502, "O arquivo recebido não é um guia válido. Nada foi alterado.")


def filtro_sql(area: str | None, ano: int | None, idioma: str) -> tuple[str, list]:
    """Monta o WHERE comum. Questões de língua estrangeira só aparecem no idioma escolhido."""
    where, params = ["(q.idioma = '' OR q.idioma = ?)"], [idioma]
    if area:
        where.append("q.area = ?")
        params.append(area)
    if ano:
        where.append("q.ano = ?")
        params.append(ano)
    return " AND ".join(where), params


@app.get("/api/filtros")
def filtros():
    anos = [r[0] for r in con.execute("SELECT DISTINCT ano FROM questoes ORDER BY ano DESC")]
    contagem = dict(con.execute("SELECT area, COUNT(*) FROM questoes WHERE idioma IN ('', 'ingles') GROUP BY area"))
    return {
        "anos": anos,
        "areas": [{"valor": k, "nome": v, "total": contagem.get(k, 0)} for k, v in AREAS.items()],
    }


@app.get("/api/proxima")
def proxima(
    area: str | None = None,
    ano: int | None = None,
    idioma: Literal["ingles", "espanhol"] = "ingles",
    modo: Literal["novas", "todas", "erros"] = "novas",
    excluir: list[int] = Query(default=[]),
):
    """Sorteia a próxima questão conforme o modo de estudo."""
    where, params = filtro_sql(area, ano, idioma)
    if modo == "novas":
        where += " AND q.id NOT IN (SELECT questao_id FROM respostas WHERE aluno_id = ?)"
        params.append(ALUNO_PADRAO)
    elif modo == "erros":
        # questões cuja ÚLTIMA resposta do aluno foi errada
        where += """ AND q.id IN (
            SELECT r.questao_id FROM respostas r
            WHERE r.aluno_id = ? AND r.id = (
                SELECT MAX(r2.id) FROM respostas r2
                WHERE r2.aluno_id = r.aluno_id AND r2.questao_id = r.questao_id)
            AND r.correta = 0)"""
        params.append(ALUNO_PADRAO)
    if excluir:
        where += f" AND q.id NOT IN ({','.join('?' * len(excluir))})"
        params.extend(excluir)

    row = con.execute(f"SELECT q.id FROM questoes q WHERE {where} ORDER BY RANDOM() LIMIT 1", params).fetchone()
    restantes = con.execute(f"SELECT COUNT(*) FROM questoes q WHERE {where}", params).fetchone()[0]
    return {"id": row[0] if row else None, "restantes": restantes}


@app.get("/api/questao/{qid}")
def questao(qid: int):
    """Retorna a questão SEM o gabarito (ele só vem depois de responder)."""
    q = con.execute("SELECT * FROM questoes WHERE id = ?", (qid,)).fetchone()
    if not q:
        raise HTTPException(404, "Questão não encontrada")
    alts = con.execute(
        "SELECT letra, texto, arquivo FROM alternativas WHERE questao_id = ? ORDER BY letra", (qid,)
    ).fetchall()
    return {
        "id": q["id"],
        "ano": q["ano"],
        "indice": q["indice"],
        "area": q["area"],
        "area_nome": AREAS.get(q["area"], q["area"]),
        "idioma": q["idioma"],
        "titulo": q["titulo"],
        "contexto": q["contexto"],
        "introducao": q["introducao"],
        "arquivos": json.loads(q["arquivos"] or "[]"),
        "alternativas": [dict(a) for a in alts],
    }


class Resposta(BaseModel):
    questao_id: int
    alternativa: str = Field(pattern="^[A-E]$")
    tempo_seg: int | None = Field(default=None, ge=0)


@app.post("/api/responder")
def responder(r: Resposta):
    q = con.execute("SELECT gabarito FROM questoes WHERE id = ?", (r.questao_id,)).fetchone()
    if not q:
        raise HTTPException(404, "Questão não encontrada")
    correta = q["gabarito"] == r.alternativa
    with con:
        cur = con.execute(
            "INSERT INTO respostas (aluno_id, questao_id, alternativa, correta, tempo_seg) VALUES (?, ?, ?, ?, ?)",
            (ALUNO_PADRAO, r.questao_id, r.alternativa, int(correta), r.tempo_seg),
        )
    return {"resposta_id": cur.lastrowid, "correta": correta, "gabarito": q["gabarito"]}


class Motivo(BaseModel):
    motivo: Literal["conteudo", "atencao", "tempo", "chute"]


@app.post("/api/resposta/{rid}/motivo")
def marcar_motivo(rid: int, m: Motivo):
    with con:
        n = con.execute(
            "UPDATE respostas SET motivo_erro = ? WHERE id = ? AND aluno_id = ? AND correta = 0", (m.motivo, rid, ALUNO_PADRAO)
        ).rowcount
    if not n:
        raise HTTPException(404, "Resposta não encontrada")
    return {"ok": True}


@app.get("/api/estatisticas")
def estatisticas():
    por_area = {
        r["area"]: dict(r)
        for r in con.execute(
            """SELECT q.area, COUNT(*) AS respondidas, SUM(r.correta) AS acertos,
                      ROUND(AVG(r.tempo_seg)) AS tempo_medio
               FROM respostas r JOIN questoes q ON q.id = r.questao_id
               WHERE r.aluno_id = ? GROUP BY q.area""",
            (ALUNO_PADRAO,),
        )
    }
    motivos = dict(
        con.execute(
            "SELECT motivo_erro, COUNT(*) FROM respostas WHERE aluno_id = ? AND correta = 0 "
            "AND motivo_erro IS NOT NULL GROUP BY motivo_erro",
            (ALUNO_PADRAO,),
        )
    )
    dias = [
        dict(r)
        for r in con.execute(
            """SELECT date(criado_em) AS dia, COUNT(*) AS respondidas, SUM(correta) AS acertos
               FROM respostas WHERE aluno_id = ? GROUP BY dia ORDER BY dia DESC LIMIT 14""",
            (ALUNO_PADRAO,),
        )
    ]
    areas = []
    for valor, nome in AREAS.items():
        a = por_area.get(valor, {})
        resp = a.get("respondidas", 0) or 0
        ac = a.get("acertos", 0) or 0
        areas.append({
            "valor": valor, "nome": nome, "respondidas": resp, "acertos": ac,
            "taxa": round(100 * ac / resp) if resp else None, "tempo_medio": a.get("tempo_medio"),
        })
    total = sum(a["respondidas"] for a in areas)
    acertos = sum(a["acertos"] for a in areas)
    return {
        "total": total, "acertos": acertos, "taxa": round(100 * acertos / total) if total else None,
        "areas": areas, "motivos": motivos, "dias": dias[::-1],
    }


@app.get("/api/erros")
def caderno_de_erros(area: str | None = None):
    """Questões cuja última resposta foi errada, com o motivo marcado pelo aluno."""
    params: list = [ALUNO_PADRAO]
    extra = ""
    if area:
        extra = "AND q.area = ?"
        params.append(area)
    rows = con.execute(
        f"""SELECT q.id, q.ano, q.indice, q.area, r.alternativa, q.gabarito, r.motivo_erro, r.criado_em,
                   (SELECT COUNT(*) FROM respostas x WHERE x.aluno_id = r.aluno_id
                      AND x.questao_id = q.id AND x.correta = 0) AS vezes_errada,
                   substr(COALESCE(q.introducao, q.contexto, ''), 1, 160) AS trecho
            FROM respostas r JOIN questoes q ON q.id = r.questao_id
            WHERE r.aluno_id = ? AND r.correta = 0 {extra}
              AND r.id = (SELECT MAX(r2.id) FROM respostas r2
                          WHERE r2.aluno_id = r.aluno_id AND r2.questao_id = r.questao_id)
            ORDER BY r.criado_em DESC""",
        params,
    ).fetchall()
    return [dict(r) | {"area_nome": AREAS.get(r["area"], r["area"])} for r in rows]


app.mount("/imagens", StaticFiles(directory=IMAGENS_DIR), name="imagens")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
