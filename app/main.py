"""Servidor local do TRIunfo.

Rodar:  python -m uvicorn app.main:app --port 8000
Abrir:  http://localhost:8000
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import guia, plano, redacao, revisao, tri, versao
from app.db import AREAS, IMAGENS_DIR, RAIZ, abrir, conectar, criar_tabelas

STATIC_DIR = RAIZ / "app" / "static"
ALUNO_PADRAO = 1  # o modo escola (vários alunos) vem numa fase seguinte

_inicial = conectar()  # migração, tabelas e modo WAL, uma vez ao iniciar
criar_tabelas(_inicial)
_inicial.close()
IMAGENS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="TRIunfo", version=versao.VERSAO)


def banco():
    """Uma conexão por requisição, fechada no fim (pré-requisito do modo escola)."""
    con = abrir()
    try:
        yield con
    finally:
        con.close()


Con = Annotated[sqlite3.Connection, Depends(banco)]


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


@app.post("/api/atualizar")
def atualizar_programa():
    """Baixa o instalador novo (conferindo o SHA-256) e o executa; ele fecha o TRIunfo, atualiza e reabre."""
    if not versao.instalado():
        raise HTTPException(409, "A atualização automática só funciona no TRIunfo instalado pelo instalador.")
    try:
        exe = versao.baixar_instalador()
    except OSError:
        raise HTTPException(503, "Não foi possível baixar agora. Verifique a internet e tente de novo.")
    except ValueError as e:
        raise HTTPException(502, f"Atualização cancelada: {e}.")
    import subprocess
    # Processo independente: o instalador fecha este servidor (CloseApplications) e reabre o app (/REABRIR).
    subprocess.Popen([str(exe), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/REABRIR"],
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
    return {"ok": True}


@app.get("/api/versao")
def verificar_versao(verificar: bool = False):
    if not verificar:  # sem internet: só informa a versão instalada
        return {"atual": versao.VERSAO}
    try:
        return versao.verificar()
    except OSError:
        raise HTTPException(503, "Não foi possível verificar a versão agora.")
    except (ValueError, KeyError):
        raise HTTPException(502, "Resposta inesperada ao verificar a versão.")


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
def filtros(con: Con):
    anos = [r[0] for r in con.execute("SELECT DISTINCT ano FROM questoes ORDER BY ano DESC")]
    contagem = dict(con.execute("SELECT area, COUNT(*) FROM questoes WHERE idioma IN ('', 'ingles') GROUP BY area"))
    return {
        "anos": anos,
        "areas": [{"valor": k, "nome": v, "total": contagem.get(k, 0)} for k, v in AREAS.items()],
    }


def _revisoes(con: sqlite3.Connection) -> dict:
    """Questões com revisão para hoje (mais fáceis primeiro) e quantas vencem nos próximos 7 dias."""
    historico = defaultdict(list)
    for qid, dia, correta in con.execute(
        "SELECT questao_id, date(criado_em), correta FROM respostas WHERE aluno_id = ? ORDER BY id", (ALUNO_PADRAO,)
    ):
        historico[qid].append((dia, bool(correta)))
    hoje = date.today()
    datas = {qid: d for qid, h in historico.items() if (d := revisao.proxima(h))}
    devidas = [qid for qid, d in datas.items() if d <= hoje]
    # Na TRI, errar questão fácil pesa mais: revisa primeiro as de menor dificuldade (parâmetro b); sem parâmetro, por último.
    b = dict(con.execute(
        f"SELECT questao_id, b FROM questoes_tri WHERE questao_id IN ({','.join('?' * len(devidas))})", devidas
    )) if devidas else {}
    devidas.sort(key=lambda q: (q not in b, b.get(q, 0)))
    semana = sum(1 for d in datas.values() if hoje < d <= hoje + timedelta(days=7))
    return {"hoje": devidas, "proximos_7_dias": semana}


@app.get("/api/revisao")
def resumo_revisao(con: Con):
    r = _revisoes(con)
    return {"hoje": len(r["hoje"]), "proximos_7_dias": r["proximos_7_dias"]}


@app.get("/api/proxima")
def proxima(
    con: Con,
    area: str | None = None,
    ano: int | None = None,
    idioma: Literal["ingles", "espanhol"] = "ingles",
    modo: Literal["novas", "todas", "erros", "revisao"] = "novas",
    excluir: list[int] = Query(default=[]),
):
    """Sorteia a próxima questão conforme o modo de estudo."""
    if modo == "revisao":  # ordem fixa: as mais fáceis primeiro (ADR 0015)
        fila = [q for q in _revisoes(con)["hoje"] if q not in set(excluir)]
        return {"id": fila[0] if fila else None, "restantes": len(fila)}
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
def questao(con: Con, qid: int):
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
def responder(con: Con, r: Resposta):
    q = con.execute("SELECT gabarito FROM questoes WHERE id = ?", (r.questao_id,)).fetchone()
    if not q:
        raise HTTPException(404, "Questão não encontrada")
    correta = q["gabarito"] == r.alternativa
    with con:
        rid = con.execute(
            "INSERT INTO respostas (aluno_id, questao_id, alternativa, correta, tempo_seg) VALUES (?, ?, ?, ?, ?) "
            "RETURNING id",
            (ALUNO_PADRAO, r.questao_id, r.alternativa, int(correta), r.tempo_seg),
        ).fetchone()[0]
    return {"resposta_id": rid, "correta": correta, "gabarito": q["gabarito"]}


class Motivo(BaseModel):
    motivo: Literal["conteudo", "atencao", "tempo", "chute"]


@app.post("/api/resposta/{rid}/motivo")
def marcar_motivo(con: Con, rid: int, m: Motivo):
    with con:
        n = con.execute(
            "UPDATE respostas SET motivo_erro = ? WHERE id = ? AND aluno_id = ? AND correta = 0", (m.motivo, rid, ALUNO_PADRAO)
        ).rowcount
    if not n:
        raise HTTPException(404, "Resposta não encontrada")
    return {"ok": True}


@app.get("/api/estatisticas")
def estatisticas(con: Con):
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
def caderno_de_erros(con: Con, area: str | None = None):
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


# ---------------------------- Redação ----------------------------

@app.get("/api/redacao/conteudo")
def redacao_conteudo():
    return FileResponse(redacao.CONTEUDO)


class NovaRedacao(BaseModel):
    tema: str = Field(min_length=3, max_length=300)


class AtualizaRedacao(BaseModel):
    texto: str | None = Field(default=None, max_length=12000)
    tempo_seg: int | None = Field(default=None, ge=0)
    entregue: bool | None = None
    notas: dict[str, int] | None = None


def _redacao(con: sqlite3.Connection, rid: int) -> dict:
    r = con.execute("SELECT * FROM redacoes WHERE id = ? AND aluno_id = ?", (rid, ALUNO_PADRAO)).fetchone()
    if not r:
        raise HTTPException(404, "Redação não encontrada")
    return dict(r) | {"notas": json.loads(r["notas"]) if r["notas"] else None}


@app.get("/api/redacoes")
def listar_redacoes(con: Con):
    rows = con.execute(
        "SELECT id, tema, tempo_seg, entregue, notas, criado_em, length(texto) AS caracteres "
        "FROM redacoes WHERE aluno_id = ? ORDER BY id DESC",
        (ALUNO_PADRAO,),
    ).fetchall()
    return [dict(r) | {"notas": json.loads(r["notas"]) if r["notas"] else None} for r in rows]


@app.post("/api/redacoes")
def criar_redacao(con: Con, n: NovaRedacao):
    with con:
        rid = con.execute(
            "INSERT INTO redacoes (aluno_id, tema) VALUES (?, ?) RETURNING id", (ALUNO_PADRAO, n.tema.strip())
        ).fetchone()[0]
    return {"id": rid}


@app.get("/api/redacoes/{rid}")
def abrir_redacao(con: Con, rid: int):
    return _redacao(con, rid)


@app.patch("/api/redacoes/{rid}")
def atualizar_redacao(con: Con, rid: int, a: AtualizaRedacao):
    _redacao(con, rid)  # 404 se não existir
    if a.notas is not None and not redacao.notas_validas(a.notas):
        raise HTTPException(422, "Notas devem ter c1..c5, cada uma em 0, 40, 80, 120, 160 ou 200")
    campos = a.model_dump(exclude_none=True)
    if "notas" in campos:
        campos["notas"] = json.dumps(campos["notas"])
    if campos:
        sets = ", ".join(f"{k} = ?" for k in campos)  # chaves vêm do modelo, não do usuário
        with con:
            con.execute(
                f"UPDATE redacoes SET {sets}, atualizado_em = datetime('now', 'localtime') WHERE id = ?",
                [*campos.values(), rid],
            )
    return _redacao(con, rid)


@app.delete("/api/redacoes/{rid}")
def apagar_redacao(con: Con, rid: int):
    with con:
        n = con.execute("DELETE FROM redacoes WHERE id = ? AND aluno_id = ?", (rid, ALUNO_PADRAO)).rowcount
    if not n:
        raise HTTPException(404, "Redação não encontrada")
    return {"ok": True}


# ---------------------------- Plano de estudos (ADR 0016) ----------------------------


class ConfigPlano(BaseModel):
    data_prova: date
    horas_semana: int = Field(ge=1, le=60)


class BlocoFeito(BaseModel):
    posicao: int = Field(ge=0, le=60)
    feito: bool


def _semana() -> str:
    ano, semana, _ = date.today().isocalendar()
    return f"{ano}-W{semana:02d}"


@app.get("/api/plano")
def ler_plano(con: Con):
    cfg = con.execute("SELECT data_prova, horas_semana FROM plano WHERE aluno_id = ?", (ALUNO_PADRAO,)).fetchone()
    if not cfg:
        return {"configurado": False}
    # Taxa de acerto por área só conta com pelo menos 10 respostas; antes disso, o plano trata como "sem dados".
    taxas = {
        area: (acertos / n if n >= 10 else None)
        for area, n, acertos in con.execute(
            "SELECT q.area, COUNT(*), SUM(r.correta) FROM respostas r JOIN questoes q ON q.id = r.questao_id "
            "WHERE r.aluno_id = ? GROUP BY q.area",
            (ALUNO_PADRAO,),
        )
    }
    semana = _semana()
    feitos = [r[0] for r in con.execute(
        "SELECT posicao FROM plano_feitos WHERE aluno_id = ? AND semana = ?", (ALUNO_PADRAO, semana))]
    return {
        "configurado": True, "data_prova": cfg["data_prova"], "horas_semana": cfg["horas_semana"],
        "semana": semana, "feitos": feitos,
        "plano": plano.montar(cfg["horas_semana"], date.fromisoformat(cfg["data_prova"]), date.today(), taxas),
    }


@app.put("/api/plano")
def configurar_plano(con: Con, c: ConfigPlano):
    with con:
        con.execute(
            "INSERT INTO plano (aluno_id, data_prova, horas_semana) VALUES (?, ?, ?) "
            "ON CONFLICT (aluno_id) DO UPDATE SET data_prova = excluded.data_prova, horas_semana = excluded.horas_semana",
            (ALUNO_PADRAO, c.data_prova.isoformat(), c.horas_semana),
        )
    return ler_plano(con)


@app.post("/api/plano/feito")
def marcar_bloco(con: Con, b: BlocoFeito):
    with con:
        if b.feito:
            con.execute("INSERT OR IGNORE INTO plano_feitos VALUES (?, ?, ?)", (ALUNO_PADRAO, _semana(), b.posicao))
        else:
            con.execute("DELETE FROM plano_feitos WHERE aluno_id = ? AND semana = ? AND posicao = ?",
                        (ALUNO_PADRAO, _semana(), b.posicao))
    return {"ok": True}


# ---------------------------- Simulado (ADR 0013) ----------------------------

DURACAO_SEG = {1: 330 * 60, 2: 300 * 60}  # edital 3.3: 5h30 no 1º dia (com redação), 5h no 2º
Letra = Literal["A", "B", "C", "D", "E"]


class NovoSimulado(BaseModel):
    ano: int = Field(ge=2009, le=2100)
    dia: Literal[1, 2]
    idioma: Literal["ingles", "espanhol"] = "ingles"


class AtualizaSimulado(BaseModel):
    respostas: dict[int, Letra | None] | None = None  # junta com as salvas; None apaga a resposta
    marcadas: list[int] | None = None
    tempo_seg: int | None = Field(default=None, ge=0)


def _questoes_do_dia(con: sqlite3.Connection, ano: int, dia: int, idioma: str) -> list[tuple[int, int]]:
    """(id, número oficial), na ordem oficial: o 1º dia vai da questão 1 à 90 e o 2º da 91 à 180, em todos os anos."""
    inicio = 1 if dia == 1 else 91
    return [
        (r[0], r[1])
        for r in con.execute(
            "SELECT id, indice FROM questoes WHERE ano = ? AND indice BETWEEN ? AND ? AND (idioma = '' OR idioma = ?) "
            "ORDER BY indice",
            (ano, inicio, inicio + 89, idioma),
        )
    ]


def _resultado(con: sqlite3.Connection, s: dict) -> dict:
    ids = s["questoes"]
    rows = con.execute(
        f"SELECT id, indice, area, gabarito FROM questoes WHERE id IN ({','.join('?' * len(ids))}) ORDER BY indice",
        ids,
    ).fetchall()
    areas, itens = {}, []
    for r in rows:
        resposta = s["respostas"].get(str(r["id"]))
        a = areas.setdefault(r["area"], {"area": r["area"], "nome": AREAS[r["area"]], "total": 0, "acertos": 0, "brancos": 0})
        a["total"] += 1
        a["brancos"] += resposta is None
        a["acertos"] += resposta == r["gabarito"]
        itens.append({"id": r["id"], "indice": r["indice"], "area": r["area"], "resposta": resposta, "gabarito": r["gabarito"]})
    _nota_tri(con, s["ano"], areas, itens)
    return {"areas": list(areas.values()), "itens": itens}


def _nota_tri(con: sqlite3.Connection, ano: int, areas: dict, itens: list[dict]) -> None:
    """Nota TRI por área, só quando a escala passou na conferência contra as notas oficiais (ADR 0014)."""
    params = {
        r["questao_id"]: r
        for r in con.execute(
            f"SELECT * FROM questoes_tri WHERE questao_id IN ({','.join('?' * len(itens))})", [i["id"] for i in itens]
        )
    }
    for area, a in areas.items():
        escala = con.execute(
            "SELECT k, s, erro_medio FROM tri_escala WHERE ano = ? AND area = ? AND erro_medio < 1", (ano, area)
        ).fetchone()
        da_area = [i for i in itens if i["area"] == area]
        usadas = [(params[i["id"]], i) for i in da_area if i["id"] in params and not params[i["id"]]["anulada"]]
        if not escala or len(usadas) < 0.9 * len(da_area):
            continue
        a["nota_tri"] = tri.nota([(p["a"], p["b"], p["c"], i["resposta"] == i["gabarito"]) for p, i in usadas],
                                 escala["k"], escala["s"])
        a["tri_questoes"] = len(usadas)


def _simulado(con: sqlite3.Connection, sid: int) -> dict:
    row = con.execute("SELECT * FROM simulados WHERE id = ? AND aluno_id = ?", (sid, ALUNO_PADRAO)).fetchone()
    if not row:
        raise HTTPException(404, "Simulado não encontrado")
    s = dict(row) | {"respostas": json.loads(row["respostas"]), "marcadas": json.loads(row["marcadas"])}
    pares = _questoes_do_dia(con, s["ano"], s["dia"], s["idioma"])
    s["questoes"] = [qid for qid, _ in pares]
    s["numeros"] = [n for _, n in pares]  # numeração oficial, igual à do caderno
    s["duracao_seg"] = DURACAO_SEG[s["dia"]]
    if s["entregue"]:  # o gabarito só sai depois da entrega
        s["resultado"] = _resultado(con, s)
    return s


@app.get("/api/simulados")
def listar_simulados(con: Con):
    ids = [r[0] for r in con.execute("SELECT id FROM simulados WHERE aluno_id = ? ORDER BY id DESC", (ALUNO_PADRAO,))]
    lista = []
    for sid in ids:
        s = _simulado(con, sid)
        acertos = sum(a["acertos"] for a in s["resultado"]["areas"]) if s["entregue"] else None
        lista.append({k: s[k] for k in ("id", "ano", "dia", "entregue", "criado_em", "tempo_seg")}
                     | {"total": len(s["questoes"]), "respondidas": len(s["respostas"]), "acertos": acertos})
    return lista


@app.post("/api/simulados")
def criar_simulado(con: Con, n: NovoSimulado):
    if not _questoes_do_dia(con, n.ano, n.dia, n.idioma):
        raise HTTPException(404, "Não há questões desse ano e dia no banco.")
    with con:
        sid = con.execute(
            "INSERT INTO simulados (aluno_id, ano, dia, idioma) VALUES (?, ?, ?, ?) RETURNING id",
            (ALUNO_PADRAO, n.ano, n.dia, n.idioma),
        ).fetchone()[0]
    return {"id": sid}


@app.get("/api/simulados/{sid}")
def abrir_simulado(con: Con, sid: int):
    return _simulado(con, sid)


@app.patch("/api/simulados/{sid}")
def atualizar_simulado(con: Con, sid: int, a: AtualizaSimulado):
    s = _simulado(con, sid)
    if s["entregue"]:
        raise HTTPException(409, "Este simulado já foi entregue.")
    validas = set(s["questoes"])
    if a.respostas:
        if not set(a.respostas) <= validas:
            raise HTTPException(422, "Questão que não faz parte deste simulado.")
        for qid, letra in a.respostas.items():
            if letra is None:
                s["respostas"].pop(str(qid), None)
            else:
                s["respostas"][str(qid)] = letra
    if a.marcadas is not None:
        s["marcadas"] = sorted(set(a.marcadas) & validas)
    with con:
        con.execute(
            "UPDATE simulados SET respostas = ?, marcadas = ?, tempo_seg = COALESCE(?, tempo_seg) WHERE id = ?",
            (json.dumps(s["respostas"]), json.dumps(s["marcadas"]), a.tempo_seg, sid),
        )
    return {"ok": True}


@app.post("/api/simulados/{sid}/entregar")
def entregar_simulado(con: Con, sid: int):
    s = _simulado(con, sid)
    if s["entregue"]:
        raise HTTPException(409, "Este simulado já foi entregue.")
    with con:
        con.execute("UPDATE simulados SET entregue = 1 WHERE id = ?", (sid,))
        # As respostas entram no histórico: erros vão para o caderno de erros e para o painel.
        for item in _resultado(con, s)["itens"]:
            if item["resposta"]:
                con.execute(
                    "INSERT INTO respostas (aluno_id, questao_id, alternativa, correta) VALUES (?, ?, ?, ?)",
                    (ALUNO_PADRAO, item["id"], item["resposta"], int(item["resposta"] == item["gabarito"])),
                )
    return _simulado(con, sid)


app.mount("/imagens", StaticFiles(directory=IMAGENS_DIR), name="imagens")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
