"""Servidor local do TRIunfo.

Rodar:  python -m uvicorn app.main:app --port 8000
Abrir:  http://localhost:8000
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import re
import secrets
import sqlite3
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi import Path as FPath
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import guia, imagens, plano, redacao, revisao, tri, turma, versao
from app.db import AREAS, IMAGENS_DIR, RAIZ, abrir, conectar, criar_tabelas

STATIC_DIR = RAIZ / "app" / "static"

_inicial = conectar()  # migração, tabelas e modo WAL, uma vez ao iniciar
criar_tabelas(_inicial)
_inicial.close()
IMAGENS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="TRIunfo", version=versao.VERSAO)
app.add_middleware(GZipMiddleware, minimum_size=1000)  # app.js, CSS e JSON grandes viajam comprimidos no Wi-Fi


def banco():
    """Uma conexão por requisição, fechada no fim (pré-requisito do modo escola)."""
    con = abrir()
    try:
        yield con
    finally:
        con.close()


Con = Annotated[sqlite3.Connection, Depends(banco)]


def pela_turma(request: Request) -> bool:
    """A requisição chegou pelo servidor da turma (rede local), e não pelo do próprio PC.
    Pela faixa de portas, e não pelo estado da turma: ao fechar, um pedido em andamento não vira administrador."""
    return request.scope.get("server", (None, None))[1] in turma.PORTAS


def aluno_atual(request: Request, con: Con) -> int:
    """No próprio PC: o organizador (aluno 1). Pela turma: quem entrou com nome e PIN neste aparelho."""
    if not pela_turma(request):
        return turma.ORGANIZADOR
    aluno = turma.aluno_do_cookie(con, request.cookies.get(turma.COOKIE))
    if aluno is None:
        raise HTTPException(401, "Entre com seu nome e PIN para continuar.")
    return aluno


def so_organizador(request: Request) -> None:
    if pela_turma(request):
        raise HTTPException(403, "Só quem organiza a turma, no computador dele, pode fazer isso.")


Aluno = Annotated[int, Depends(aluno_atual)]
Organizador = Depends(so_organizador)


# Proteção contra ataques vindos de sites da internet (ADR 0026). O servidor local não tem login porque só o próprio PC
# o alcança, mas o navegador do aluno pode ser usado por outro site: CSRF (POST para 127.0.0.1), DNS rebinding (um
# domínio que passa a apontar para 127.0.0.1 e lê as respostas) e clickjacking (a tela dentro de um iframe).
_script_inline = re.search(r"<script>(.*?)</script>", (STATIC_DIR / "index.html").read_text(encoding="utf-8"), re.S)
_hash_script = base64.b64encode(hashlib.sha256(_script_inline.group(1).encode()).digest()).decode()
CSP = (f"default-src 'self'; script-src 'self' 'sha256-{_hash_script}'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
       "frame-ancestors 'none'")
SEGUROS = {"GET", "HEAD", "OPTIONS"}
LIMITE_PEDIDO = 1_000_000  # bytes: bem acima do maior pedido legítimo (rascunho de 400 KB)


def host_permitido(host: str) -> bool:
    """Só endereço IP ou localhost: o DNS rebinding precisa de um nome de domínio no Host."""
    nome = host.rsplit(":", 1)[0].strip("[]") if not host.endswith("]") else host.strip("[]")
    if nome == "localhost":
        return True
    try:
        ipaddress.ip_address(nome)
        return True
    except ValueError:
        return False


def origem_estranha(request: Request) -> bool:
    """Pedido que altera dados vindo de outro site (CSRF). Pedidos sem Origin (não são de navegador) passam."""
    if request.method in SEGUROS:
        return False
    if request.headers.get("sec-fetch-site") == "cross-site":
        return True
    origem = request.headers.get("origin")
    return origem is not None and origem != f"http://{request.headers.get('host', '')}"


@app.middleware("http")
async def protecao_e_cache(request: Request, call_next):
    if not host_permitido(request.headers.get("host", "")):
        return JSONResponse({"detail": "Endereço não permitido. Abra o TRIunfo pelo atalho ou pelo endereço mostrado nele."}, 400)
    if origem_estranha(request):
        return JSONResponse({"detail": "Pedido vindo de outro site foi recusado."}, 403)
    # Tamanho antes de ler o corpo: um envio gigante pela rede derrubaria o PC de quem organiza a turma.
    if "transfer-encoding" in request.headers:
        return JSONResponse({"detail": "Envie o tamanho do pedido (Content-Length)."}, 411)
    if int(request.headers.get("content-length") or 0) > LIMITE_PEDIDO:
        return JSONResponse({"detail": "Pedido grande demais."}, 413)
    resposta = await call_next(request)
    # Imagens das questões: nunca mudam (prova oficial), então o navegador guarda e não pergunta de novo; com uma sala
    # inteira no mesmo PC, eram centenas de revalidações. O resto: o navegador confere (304 é barato), senão uma
    # atualização do app não aparece para o aluno.
    imutavel = request.url.path.startswith("/imagens/") and resposta.status_code == 200
    resposta.headers["Cache-Control"] = "public, max-age=31536000, immutable" if imutavel else "no-cache"
    resposta.headers["Content-Security-Policy"] = CSP
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    return resposta


@app.get("/api/guia")
def ler_guia():
    return guia.atual()


@app.post("/api/guia/sincronizar", dependencies=[Organizador])
def sincronizar_guia():
    try:
        return guia.sincronizar()
    except OSError:
        raise HTTPException(503, "Não foi possível baixar (sem internet ou servidor fora do ar). O guia atual continua valendo.")
    except ValueError:  # inclui UnicodeDecodeError
        raise HTTPException(502, "O arquivo recebido não é um guia válido. Nada foi alterado.")


@app.post("/api/atualizar", dependencies=[Organizador])
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
def verificar_versao(request: Request, verificar: bool = False):
    # Pela rede, só a versão: consultar o GitHub em laço gastaria a cota (60/hora) do IP da escola.
    if not verificar or pela_turma(request):  # sem internet: só informa a versão instalada
        return {"atual": versao.VERSAO}
    try:
        return versao.verificar()
    except OSError:
        raise HTTPException(503, "Não foi possível verificar a versão agora.")
    except (ValueError, KeyError):
        raise HTTPException(502, "Resposta inesperada ao verificar a versão.")


def _config(con: sqlite3.Connection, chave: str, padrao: str) -> str:
    r = con.execute("SELECT valor FROM config WHERE chave = ?", (chave,)).fetchone()
    return r[0] if r else padrao


def _gravar_config(con: sqlite3.Connection, chave: str, valor: str) -> None:
    with con:
        con.execute("INSERT INTO config (chave, valor) VALUES (?, ?) ON CONFLICT (chave) DO UPDATE SET valor = excluded.valor",
                    (chave, valor))


UM_DIA = 86400


@app.get("/api/versao/lembrete")
def lembrete_versao(request: Request, con: Con):
    """Lembrete de versão nova (ADR 0024): consulta o GitHub no máximo 1 vez por dia, em segundo plano.
    Sem internet, fica quieto e tenta de novo em 6 horas. Nada é baixado nem instalado sem o clique."""
    if pela_turma(request) or _config(con, "lembrete_versao", "1") != "1":
        return {"nova": None}  # na turma, quem atualiza é o organizador
    agora = time.time()
    if agora - float(_config(con, "versao_consultada_em", "0")) > UM_DIA:
        try:
            _gravar_config(con, "versao_lembrete", json.dumps(versao.verificar()))
            _gravar_config(con, "versao_consultada_em", str(agora))
        except (OSError, ValueError, KeyError):
            _gravar_config(con, "versao_consultada_em", str(agora - UM_DIA + 6 * 3600))
    info = json.loads(_config(con, "versao_lembrete", "{}"))
    if not info.get("nova") or guia.versao(info["nova"]) <= guia.versao(versao.VERSAO):
        return {"nova": None}  # já atualizou
    return info


class Preferencias(BaseModel):
    lembrete_versao: bool


@app.get("/api/preferencias", dependencies=[Organizador])
def ler_preferencias(con: Con):
    return {"lembrete_versao": _config(con, "lembrete_versao", "1") == "1"}


@app.put("/api/preferencias", dependencies=[Organizador])
def gravar_preferencias(p: Preferencias, con: Con):
    _gravar_config(con, "lembrete_versao", "1" if p.lembrete_versao else "0")
    return ler_preferencias(con)


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


def _revisoes(con: sqlite3.Connection, aluno: int) -> dict:
    """Questões com revisão para hoje (mais fáceis primeiro) e quantas vencem nos próximos 7 dias."""
    historico = defaultdict(list)
    for qid, dia, correta in con.execute(
        # Só questões que já tiveram erro: as outras nunca entram na revisão (revisao.proxima devolve None).
        "SELECT questao_id, date(criado_em), correta FROM respostas WHERE aluno_id = ? AND questao_id IN "
        "(SELECT questao_id FROM respostas WHERE aluno_id = ? AND correta = 0) ORDER BY id", (aluno, aluno)
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
def resumo_revisao(con: Con, aluno: Aluno):
    r = _revisoes(con, aluno)
    return {"hoje": len(r["hoje"]), "proximos_7_dias": r["proximos_7_dias"]}


def _com_questao(con: sqlite3.Connection, qid: int | None, restantes: int) -> dict:
    return {"id": qid, "restantes": restantes, "questao": questao(con, qid) if qid else None}


class PedidoProxima(BaseModel):
    area: str | None = None
    ano: int | None = None
    idioma: Literal["ingles", "espanhol"] = "ingles"
    modo: Literal["novas", "todas", "erros", "revisao"] = "novas"
    excluir: list[int] = Field(default=[], max_length=10_000)  # vistas na sessão; no corpo, sem limite de URL


@app.post("/api/proxima")
def proxima(p: PedidoProxima, con: Con, aluno: Aluno):
    """Sorteia a próxima questão conforme o modo de estudo."""
    area, ano, idioma, modo, excluir = p.area, p.ano, p.idioma, p.modo, p.excluir
    if modo == "revisao":  # ordem fixa: as mais fáceis primeiro (ADR 0015)
        vistas = set(excluir)
        fila = [q for q in _revisoes(con, aluno)["hoje"] if q not in vistas]
        return _com_questao(con, fila[0] if fila else None, len(fila))
    where, params = filtro_sql(area, ano, idioma)
    if modo == "novas":
        where += " AND q.id NOT IN (SELECT questao_id FROM respostas WHERE aluno_id = ?)"
        params.append(aluno)
    elif modo == "erros":
        # questões cuja ÚLTIMA resposta do aluno foi errada
        where += """ AND q.id IN (
            SELECT r.questao_id FROM respostas r
            WHERE r.aluno_id = ? AND r.id = (
                SELECT MAX(r2.id) FROM respostas r2
                WHERE r2.aluno_id = r.aluno_id AND r2.questao_id = r.questao_id)
            AND r.correta = 0)"""
        params.append(aluno)
    if excluir:  # um só parâmetro (JSON): sem o limite de variáveis do SQLite
        where += " AND q.id NOT IN (SELECT value FROM json_each(?))"
        params.append(json.dumps(excluir))

    row = con.execute(f"SELECT q.id FROM questoes q WHERE {where} ORDER BY RANDOM() LIMIT 1", params).fetchone()
    # A questão vem junto (sem gabarito): uma ida e volta a menos por questão no Wi-Fi da turma.
    restantes = con.execute(f"SELECT COUNT(*) FROM questoes q WHERE {where}", params).fetchone()[0]
    return _com_questao(con, row[0] if row else None, restantes)


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
        "dimensoes": imagens.da_questao(q["contexto"], q["introducao"], q["arquivos"],
                                        *(a["texto"] for a in alts), *(a["arquivo"] for a in alts)),
    }


class Resposta(BaseModel):
    questao_id: int
    alternativa: str = Field(pattern="^[A-E]$")
    tempo_seg: int | None = Field(default=None, ge=0)


@app.post("/api/responder")
def responder(con: Con, aluno: Aluno, r: Resposta):
    q = con.execute("SELECT gabarito FROM questoes WHERE id = ?", (r.questao_id,)).fetchone()
    if not q:
        raise HTTPException(404, "Questão não encontrada")
    correta = q["gabarito"] == r.alternativa
    with con:
        rid = con.execute(
            "INSERT INTO respostas (aluno_id, questao_id, alternativa, correta, tempo_seg) VALUES (?, ?, ?, ?, ?) "
            "RETURNING id",
            (aluno, r.questao_id, r.alternativa, int(correta), r.tempo_seg),
        ).fetchone()[0]
    return {"resposta_id": rid, "correta": correta, "gabarito": q["gabarito"]}


class Motivo(BaseModel):
    motivo: Literal["conteudo", "atencao", "tempo", "chute"]


@app.post("/api/resposta/{rid}/motivo")
def marcar_motivo(con: Con, aluno: Aluno, rid: int, m: Motivo):
    with con:
        n = con.execute(
            "UPDATE respostas SET motivo_erro = ? WHERE id = ? AND aluno_id = ? AND correta = 0", (m.motivo, rid, aluno)
        ).rowcount
    if not n:
        raise HTTPException(404, "Resposta não encontrada")
    return {"ok": True}


@app.get("/api/estatisticas")
def estatisticas(con: Con, aluno: Aluno):
    por_area = {
        r["area"]: dict(r)
        for r in con.execute(
            """SELECT q.area, COUNT(*) AS respondidas, SUM(r.correta) AS acertos,
                      ROUND(AVG(r.tempo_seg)) AS tempo_medio
               FROM respostas r JOIN questoes q ON q.id = r.questao_id
               WHERE r.aluno_id = ? GROUP BY q.area""",
            (aluno,),
        )
    }
    motivos = dict(
        con.execute(
            "SELECT motivo_erro, COUNT(*) FROM respostas WHERE aluno_id = ? AND correta = 0 "
            "AND motivo_erro IS NOT NULL GROUP BY motivo_erro",
            (aluno,),
        )
    )
    dias = [
        dict(r)
        for r in con.execute(
            """SELECT date(criado_em) AS dia, COUNT(*) AS respondidas, SUM(correta) AS acertos
               FROM respostas WHERE aluno_id = ? GROUP BY dia ORDER BY dia DESC LIMIT 14""",
            (aluno,),
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
def caderno_de_erros(con: Con, aluno: Aluno, area: str | None = None):
    """Questões cuja última resposta foi errada, com o motivo marcado pelo aluno."""
    params: list = [aluno]
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


def _redacao(con: sqlite3.Connection, aluno: int, rid: int) -> dict:
    r = con.execute("SELECT * FROM redacoes WHERE id = ? AND aluno_id = ?", (rid, aluno)).fetchone()
    if not r:
        raise HTTPException(404, "Redação não encontrada")
    return dict(r) | {"notas": json.loads(r["notas"]) if r["notas"] else None}


@app.get("/api/redacoes")
def listar_redacoes(con: Con, aluno: Aluno):
    rows = con.execute(
        "SELECT id, tema, tempo_seg, entregue, notas, criado_em, length(texto) AS caracteres "
        "FROM redacoes WHERE aluno_id = ? ORDER BY id DESC",
        (aluno,),
    ).fetchall()
    return [dict(r) | {"notas": json.loads(r["notas"]) if r["notas"] else None} for r in rows]


@app.post("/api/redacoes")
def criar_redacao(con: Con, aluno: Aluno, n: NovaRedacao):
    with con:
        rid = con.execute(
            "INSERT INTO redacoes (aluno_id, tema) VALUES (?, ?) RETURNING id", (aluno, n.tema.strip())
        ).fetchone()[0]
    return {"id": rid}


@app.get("/api/redacoes/{rid}")
def abrir_redacao(con: Con, aluno: Aluno, rid: int):
    return _redacao(con, aluno, rid)


@app.patch("/api/redacoes/{rid}")
def atualizar_redacao(con: Con, aluno: Aluno, rid: int, a: AtualizaRedacao):
    _redacao(con, aluno, rid)  # 404 se não existir
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
    return _redacao(con, aluno, rid)


@app.delete("/api/redacoes/{rid}")
def apagar_redacao(con: Con, aluno: Aluno, rid: int):
    with con:
        n = con.execute("DELETE FROM redacoes WHERE id = ? AND aluno_id = ?", (rid, aluno)).rowcount
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
def ler_plano(con: Con, aluno: Aluno):
    cfg = con.execute("SELECT data_prova, horas_semana FROM plano WHERE aluno_id = ?", (aluno,)).fetchone()
    if not cfg:
        return {"configurado": False}
    # Taxa de acerto por área só conta com pelo menos 10 respostas; antes disso, o plano trata como "sem dados".
    taxas = {
        area: (acertos / n if n >= 10 else None)
        for area, n, acertos in con.execute(
            "SELECT q.area, COUNT(*), SUM(r.correta) FROM respostas r JOIN questoes q ON q.id = r.questao_id "
            "WHERE r.aluno_id = ? GROUP BY q.area",
            (aluno,),
        )
    }
    semana = _semana()
    feitos = [r[0] for r in con.execute(
        "SELECT posicao FROM plano_feitos WHERE aluno_id = ? AND semana = ?", (aluno, semana))]
    return {
        "configurado": True, "data_prova": cfg["data_prova"], "horas_semana": cfg["horas_semana"],
        "semana": semana, "feitos": feitos,
        "plano": plano.montar(cfg["horas_semana"], date.fromisoformat(cfg["data_prova"]), date.today(), taxas),
    }


@app.put("/api/plano")
def configurar_plano(con: Con, aluno: Aluno, c: ConfigPlano):
    with con:
        con.execute(
            "INSERT INTO plano (aluno_id, data_prova, horas_semana) VALUES (?, ?, ?) "
            "ON CONFLICT (aluno_id) DO UPDATE SET data_prova = excluded.data_prova, horas_semana = excluded.horas_semana",
            (aluno, c.data_prova.isoformat(), c.horas_semana),
        )
    return ler_plano(con, aluno)


@app.post("/api/plano/feito")
def marcar_bloco(con: Con, aluno: Aluno, b: BlocoFeito):
    with con:
        if b.feito:
            con.execute("INSERT OR IGNORE INTO plano_feitos VALUES (?, ?, ?)", (aluno, _semana(), b.posicao))
        else:
            con.execute("DELETE FROM plano_feitos WHERE aluno_id = ? AND semana = ? AND posicao = ?",
                        (aluno, _semana(), b.posicao))
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
    if not ids:  # o banco de questões novo não tem mais esse ano/idioma (ADR 0018): resultado vazio, sem erro
        return {"areas": [], "itens": []}
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
    if not itens:
        return
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


def _simulado(con: sqlite3.Connection, aluno: int, sid: int) -> dict:
    row = con.execute("SELECT * FROM simulados WHERE id = ? AND aluno_id = ?", (sid, aluno)).fetchone()
    if not row:
        raise HTTPException(404, "Simulado não encontrado")
    s = dict(row) | {"respostas": json.loads(row["respostas"]), "marcadas": json.loads(row["marcadas"])}
    guardado = s.pop("resultado")
    pares = _questoes_do_dia(con, s["ano"], s["dia"], s["idioma"])
    s["questoes"] = [qid for qid, _ in pares]
    s["numeros"] = [n for _, n in pares]  # numeração oficial, igual à do caderno
    s["duracao_seg"] = DURACAO_SEG[s["dia"]]
    if s["entregue"]:  # o gabarito só sai depois da entrega
        s["resultado"] = json.loads(guardado) if guardado else _guardar_resultado(con, s)
    return s


def _guardar_resultado(con: sqlite3.Connection, s: dict) -> dict:
    """Calcula o resultado (com a nota TRI) uma vez e guarda: antes, era refeito a cada abertura e a cada questão
    da revisão. Simulados entregues antes desta versão são guardados na primeira vez que abrem."""
    resultado = _resultado(con, s)
    with con:
        con.execute("UPDATE simulados SET resultado = ? WHERE id = ?", (json.dumps(resultado), s["id"]))
    return resultado


@app.get("/api/simulados")
def listar_simulados(con: Con, aluno: Aluno):
    """Sem recalcular resultados: usa o guardado na entrega (antes, a nota TRI de cada simulado era refeita aqui)."""
    lista, totais = [], {}
    for r in con.execute("SELECT id, ano, dia, idioma, entregue, criado_em, tempo_seg, respostas, resultado "
                         "FROM simulados WHERE aluno_id = ? ORDER BY id DESC", (aluno,)).fetchall():
        dia = (r["ano"], r["dia"], r["idioma"])
        if dia not in totais:
            totais[dia] = len(_questoes_do_dia(con, *dia))
        acertos = None
        if r["entregue"]:
            resultado = json.loads(r["resultado"]) if r["resultado"] else _simulado(con, aluno, r["id"])["resultado"]
            acertos = sum(a["acertos"] for a in resultado["areas"])
        lista.append({k: r[k] for k in ("id", "ano", "dia", "entregue", "criado_em", "tempo_seg")}
                     | {"total": totais[dia], "respondidas": len(json.loads(r["respostas"])), "acertos": acertos})
    return lista


@app.post("/api/simulados")
def criar_simulado(con: Con, aluno: Aluno, n: NovoSimulado):
    if not _questoes_do_dia(con, n.ano, n.dia, n.idioma):
        raise HTTPException(404, "Não há questões desse ano e dia no banco.")
    with con:
        sid = con.execute(
            "INSERT INTO simulados (aluno_id, ano, dia, idioma) VALUES (?, ?, ?, ?) RETURNING id",
            (aluno, n.ano, n.dia, n.idioma),
        ).fetchone()[0]
    return {"id": sid}


@app.get("/api/simulados/{sid}")
def abrir_simulado(con: Con, aluno: Aluno, sid: int):
    return _simulado(con, aluno, sid)


@app.patch("/api/simulados/{sid}")
def atualizar_simulado(con: Con, aluno: Aluno, sid: int, a: AtualizaSimulado):
    # BEGIN IMMEDIATE: ler-alterar-gravar o JSON sem que outro salvamento simultâneo apague uma resposta.
    with con:
        con.execute("BEGIN IMMEDIATE")
        s = _simulado(con, aluno, sid)
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
        con.execute(
            "UPDATE simulados SET respostas = ?, marcadas = ?, tempo_seg = COALESCE(?, tempo_seg) WHERE id = ?",
            (json.dumps(s["respostas"]), json.dumps(s["marcadas"]), a.tempo_seg, sid),
        )
    return {"ok": True}


@app.post("/api/simulados/{sid}/entregar")
def entregar_simulado(con: Con, aluno: Aluno, sid: int):
    with con:
        con.execute("BEGIN IMMEDIATE")  # duas entregas ao mesmo tempo (duplo clique) não duplicam o histórico
        s = _simulado(con, aluno, sid)
        if s["entregue"]:
            raise HTTPException(409, "Este simulado já foi entregue.")
        resultado = _resultado(con, s)
        con.execute("UPDATE simulados SET entregue = 1, resultado = ? WHERE id = ?", (json.dumps(resultado), sid))
        # As respostas entram no histórico: erros vão para o caderno de erros e para o painel.
        for item in resultado["itens"]:
            if item["resposta"]:
                con.execute(
                    "INSERT INTO respostas (aluno_id, questao_id, alternativa, correta) VALUES (?, ?, ?, ?)",
                    (aluno, item["id"], item["resposta"], int(item["resposta"] == item["gabarito"])),
                )
    return _simulado(con, aluno, sid)


# ---------------------------- Rascunho com caneta (ADR 0023) ----------------------------

CHAVE_RASCUNHO = r"^(q\d{1,9}|s\d{1,9}-\d{1,9})$"
LIMITE_RASCUNHO = 400_000  # bytes de JSON por questão: muito acima de uma página cheia de contas


class Traco(BaseModel):
    tipo: Literal["caneta", "marca"]
    pressao: float = Field(default=1, ge=0, le=3)
    pontos: list[tuple[float, float]] = Field(max_length=20_000)


class NovoRascunho(BaseModel):
    tracos: list[Traco] = Field(max_length=2_000)


def _rascunho_permitido(con: sqlite3.Connection, aluno: int, chave: str) -> None:
    if chave.startswith("s"):  # o simulado precisa ser do próprio aluno
        sid = int(chave[1:].split("-")[0])
        if not con.execute("SELECT 1 FROM simulados WHERE id = ? AND aluno_id = ?", (sid, aluno)).fetchone():
            raise HTTPException(404, "Simulado não encontrado")


@app.get("/api/rascunhos/{chave}")
def ler_rascunho(con: Con, aluno: Aluno, chave: str = FPath(pattern=CHAVE_RASCUNHO)):
    _rascunho_permitido(con, aluno, chave)
    r = con.execute("SELECT tracos FROM rascunhos WHERE aluno_id = ? AND chave = ?", (aluno, chave)).fetchone()
    return {"tracos": json.loads(r[0]) if r else []}


@app.put("/api/rascunhos/{chave}")
def salvar_rascunho(n: NovoRascunho, con: Con, aluno: Aluno, chave: str = FPath(pattern=CHAVE_RASCUNHO)):
    _rascunho_permitido(con, aluno, chave)
    tracos = [{"tipo": t.tipo, "pressao": round(t.pressao, 2), "pontos": [[round(x, 4), round(y, 4)] for x, y in t.pontos]}
              for t in n.tracos]
    texto = json.dumps(tracos, separators=(",", ":"))
    if len(texto) > LIMITE_RASCUNHO:
        raise HTTPException(413, "Rascunho grande demais para uma questão. Use Limpar e continue.")
    with con:
        if tracos:
            con.execute(
                "INSERT INTO rascunhos (aluno_id, chave, tracos) VALUES (?, ?, ?) ON CONFLICT (aluno_id, chave) "
                "DO UPDATE SET tracos = excluded.tracos, atualizado_em = datetime('now', 'localtime')",
                (aluno, chave, texto))
        else:
            con.execute("DELETE FROM rascunhos WHERE aluno_id = ? AND chave = ?", (aluno, chave))
    return {"ok": True}


# ---------------------------- Modo turma (ADR 0022) ----------------------------

class Acesso(BaseModel):
    nome: str = Field(min_length=2, max_length=40)
    pin: str = Field(pattern=r"^\d{4}$")


def _guardar_aparelho(resposta: Response, con: sqlite3.Connection, aluno: int) -> None:
    resposta.set_cookie(turma.COOKIE, turma.cookie_para(con, aluno), max_age=turma.VALIDADE_SEG, httponly=True,
                        samesite="strict")


@app.get("/api/turma/eu")
def quem_sou(request: Request, resposta: Response, con: Con):
    if not pela_turma(request):
        return {"modo": "local", "aluno": None}
    lido = turma.ler_cookie(con, request.cookies.get(turma.COOKIE))
    aluno = lido[0] if lido else None
    if lido and time.time() - lido[1] > turma.RENOVAR_SEG:  # quem usa não precisa entrar de novo a cada 90 dias
        _guardar_aparelho(resposta, con, aluno)
    nome = con.execute("SELECT nome FROM alunos WHERE id = ?", (aluno,)).fetchone() if aluno else None
    return {"modo": "turma", "aluno": {"id": aluno, "nome": nome[0]} if nome else None}


def _so_pela_turma(request: Request) -> None:
    if not pela_turma(request):
        raise HTTPException(409, "No computador do organizador não é preciso entrar.")


@app.post("/api/turma/entrar", dependencies=[Depends(_so_pela_turma)])
def entrar_na_turma(a: Acesso, resposta: Response, con: Con):
    aluno, erro = turma.entrar(con, a.nome, a.pin)
    if aluno is None:
        raise HTTPException(401, erro)
    _guardar_aparelho(resposta, con, aluno)
    return {"ok": True}


@app.post("/api/turma/cadastrar", dependencies=[Depends(_so_pela_turma)])
def cadastrar_na_turma(a: Acesso, request: Request, resposta: Response, con: Con):
    nome = " ".join(a.nome.split())
    if not turma.pode_cadastrar(request.client.host if request.client else "?"):
        raise HTTPException(429, "Muitos cadastros deste aparelho. Espere 1 minuto e tente de novo.")
    try:
        with con:
            con.execute("BEGIN IMMEDIATE")  # conferir e gravar juntos: dois cadastros iguais ao mesmo tempo
            if turma.achar(con, nome, com_pin=False):
                raise sqlite3.IntegrityError
            aluno = con.execute(
                "INSERT INTO alunos (nome, pin_hash, criado_em) VALUES (?, ?, datetime('now', 'localtime')) RETURNING id",
                (nome, turma.hash_pin(a.pin)),
            ).fetchone()[0]
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Já existe alguém com esse nome na turma. Se é você, escolha \"Já tenho acesso\". "
                                 "Se não, acrescente o sobrenome.")
    _guardar_aparelho(resposta, con, aluno)
    return {"ok": True}


@app.post("/api/turma/sair")
def sair_da_turma(request: Request, resposta: Response, con: Con):
    aluno = turma.aluno_do_cookie(con, request.cookies.get(turma.COOKIE))
    if aluno is not None:
        turma.encerrar_sessao(con, aluno)  # o cookie deixa de valer no servidor, não só neste navegador
    resposta.delete_cookie(turma.COOKIE)
    return {"ok": True}


@app.get("/api/turma", dependencies=[Organizador])
def ver_turma(con: Con):
    participantes = [dict(r) for r in con.execute(
        """SELECT a.id, a.nome, a.criado_em,
                  COUNT(r.id) AS respondidas, SUM(r.correta) AS acertos, MAX(r.criado_em) AS ultima_atividade
           FROM alunos a LEFT JOIN respostas r ON r.aluno_id = a.id
           WHERE a.id != ? GROUP BY a.id ORDER BY a.nome COLLATE NOCASE""", (turma.ORGANIZADOR,))]
    dono = con.execute("SELECT nome, pin_hash IS NOT NULL FROM alunos WHERE id = ?", (turma.ORGANIZADOR,)).fetchone()
    enderecos = turma.enderecos()
    return {"aberta": turma.porta() is not None, "endereco": enderecos[0] if enderecos else None,
            "outros_enderecos": enderecos[1:], "participantes": participantes,
            "meu_acesso": {"nome": dono[0], "definido": bool(dono[1])}}


@app.put("/api/turma/meu-acesso", dependencies=[Organizador])
def definir_meu_acesso(a: Acesso, con: Con):
    """Nome e PIN do dono do PC para usar o mesmo progresso no tablet ou celular (ADR 0025)."""
    nome = " ".join(a.nome.split())
    try:
        with con:
            con.execute("BEGIN IMMEDIATE")
            if turma.achar(con, nome, com_pin=False) not in (None, turma.ORGANIZADOR):
                raise sqlite3.IntegrityError
            con.execute("UPDATE alunos SET nome = ?, pin_hash = ?, tentativas = 0, bloqueado_ate = NULL WHERE id = ?",
                        (nome, turma.hash_pin(a.pin), turma.ORGANIZADOR))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Já existe um participante com esse nome. Use outro, por exemplo com o sobrenome.")
    return ver_turma(con)


@app.post("/api/turma/abrir", dependencies=[Organizador])
def abrir_turma(con: Con):
    try:
        turma.abrir(app)
    except OSError:
        raise HTTPException(503, "Não foi possível abrir a turma: as portas de rede estão ocupadas. Reinicie o computador e tente de novo.")
    if not turma.enderecos():
        turma.fechar()
        raise HTTPException(503, "Este computador não está conectado a nenhuma rede. Conecte-se ao Wi-Fi e tente de novo.")
    return ver_turma(con)


@app.post("/api/turma/fechar", dependencies=[Organizador])
def fechar_turma(con: Con):
    turma.fechar()
    return ver_turma(con)


def _participante(con: sqlite3.Connection, pid: int) -> None:
    if pid == turma.ORGANIZADOR or not con.execute("SELECT 1 FROM alunos WHERE id = ?", (pid,)).fetchone():
        raise HTTPException(404, "Participante não encontrado.")


@app.post("/api/turma/participantes/{pid}/pin", dependencies=[Organizador])
def novo_pin(pid: int, con: Con):
    """Para quem esqueceu: gera um PIN novo; o aparelho que estava lembrado precisa entrar de novo."""
    _participante(con, pid)
    pin = f"{secrets.randbelow(10000):04d}"
    with con:
        con.execute("UPDATE alunos SET pin_hash = ?, tentativas = 0, bloqueado_ate = NULL WHERE id = ?",
                    (turma.hash_pin(pin), pid))
    return {"pin": pin}


@app.delete("/api/turma/participantes/{pid}", dependencies=[Organizador])
def remover_participante(pid: int, con: Con):
    """Apaga o participante e todo o progresso dele."""
    _participante(con, pid)
    with con:
        for tabela in ("respostas", "redacoes", "plano", "plano_feitos", "simulados", "rascunhos"):
            con.execute(f"DELETE FROM {tabela} WHERE aluno_id = ?", (pid,))
        con.execute("DELETE FROM alunos WHERE id = ?", (pid,))
    return {"ok": True}


app.mount("/imagens", StaticFiles(directory=IMAGENS_DIR), name="imagens")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
