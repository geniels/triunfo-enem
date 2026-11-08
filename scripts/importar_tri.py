"""Importa os parâmetros TRI oficiais (microdados do INEP) e a escala de cada área (ADR 0014).

Uso:  python scripts/importar_tri.py            # todos os anos do banco
      python scripts/importar_tri.py 2019 2020

Não baixa os pacotes inteiros (~600 MB cada): lê só o que precisa de dentro do ZIP remoto (HTTP Range),
cerca de 2 MB por ano. Para cada ano:
  1. ITENS_PROVA: parâmetros a, b, c de cada questão em cada cor de caderno.
  2. Descobre qual caderno tem a mesma ordem das nossas questões, comparando a sequência de gabaritos.
  3. Ajusta nota = k + s * theta com uma amostra de participantes e mede o erro contra as notas oficiais.
"""
from __future__ import annotations

import csv
import io
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import tri  # noqa: E402
from app.db import DATA_DIR, conectar, criar_tabelas  # noqa: E402

URL = "https://download.inep.gov.br/microdados/microdados_enem_{ano}.zip"
AREAS = {"CN": "ciencias-natureza", "CH": "ciencias-humanas", "LC": "linguagens", "MT": "matematica"}
LINGUA = {"ingles": "0", "espanhol": "1"}
# Escala fixa do ENEM por área (nota = k + s * theta): igual em todos os anos de 2009 a 2023 nos ajustes contra
# as notas oficiais. Um ano só é aceito se o ajuste dele coincidir com ela (protege contra caderno casado errado).
ESCALA_INEP = {"CN": (501.1, 113.1), "CH": (501.5, 112.3), "LC": (500.0, 108.1), "MT": (500.0, 129.65)}
TOLERANCIA = 1.5        # pontos de diferença aceitos em k e em s
MIN_CONFERE = 0.4       # fração mínima de participantes da amostra que precisa bater
AMOSTRA_LINHAS = 15000
AJUSTE_MAX = 300  # participantes por área no ajuste da escala


class ArquivoHTTP(io.RawIOBase):
    """Arquivo remoto que só baixa os trechos pedidos."""

    def __init__(self, url: str):
        self.url, self.pos, self.baixado = url, 0, 0
        with self._abrir(method="HEAD") as r:
            self.tamanho = int(r.headers["Content-Length"])

    def _abrir(self, **kw):
        for t in range(5):  # o servidor do INEP às vezes derruba a conexão
            try:
                req = urllib.request.Request(self.url, headers={"User-Agent": "triunfo", **kw.pop("headers", {})}, **kw)
                return urllib.request.urlopen(req, timeout=120)
            except OSError:
                if t == 4:
                    raise
                time.sleep(2 ** t)

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.tamanho + off}[whence]
        return self.pos

    def readinto(self, b):
        if self.pos >= self.tamanho:
            return 0
        fim = min(self.pos + len(b), self.tamanho) - 1
        with self._abrir(headers={"Range": f"bytes={self.pos}-{fim}"}) as r:
            dados = r.read()
        b[: len(dados)] = dados
        self.pos += len(dados)
        self.baixado += len(dados)
        return len(dados)


def ler_csv(z: zipfile.ZipFile, nome_final: str, limite: int | None = None) -> list[dict]:
    nome = next(n for n in z.namelist() if Path(n).name.upper() == nome_final.upper())
    linhas = []
    with z.open(nome) as arq:
        texto = io.TextIOWrapper(arq, encoding="latin-1", newline="")
        for i, r in enumerate(csv.DictReader(texto, delimiter=";")):
            if limite is not None and i >= limite:
                break
            linhas.append(r)
    return linhas


def num(v: str) -> float:
    return float(v.replace(",", ".")) if v else 0.0


def itens_por_prova(itens: list[dict]) -> dict[str, list[dict]]:
    provas = defaultdict(list)
    for r in itens:
        provas[r["CO_PROVA"]].append({
            "area": r["SG_AREA"], "pos": int(r["CO_POSICAO"]), "gab": r["TX_GABARITO"].strip().upper(), "item": r["CO_ITEM"],
            "a": num(r["NU_PARAM_A"]), "b": num(r["NU_PARAM_B"]), "c": num(r["NU_PARAM_C"]),
            "aban": r["IN_ITEM_ABAN"] == "1", "lingua": (r.get("TP_LINGUA") or "").strip(),
        })
    return provas


def casar_questoes(con, ano: int, provas: dict[str, list[dict]]) -> dict[str, tuple[str, int, int]]:
    """Para cada área, escolhe o caderno com a mesma ordem das nossas questões e grava os parâmetros."""
    resumo = {}
    for sigla, area in AREAS.items():
        nossas = con.execute("SELECT id, indice, idioma, gabarito FROM questoes WHERE ano = ? AND area = ?",
                             (ano, area)).fetchall()
        if not nossas:
            continue
        melhor = (0, None, {})
        for cod, itens in provas.items():
            if itens[0]["area"] != sigla:
                continue
            mapa = {(i["pos"], i["lingua"]): i for i in itens}
            pares = {}
            for q in nossas:
                i = mapa.get((q["indice"], LINGUA.get(q["idioma"], ""))) or mapa.get((q["indice"], ""))
                if i and i["gab"] == q["gabarito"]:
                    pares[q["id"]] = i
            if len(pares) > melhor[0]:
                melhor = (len(pares), cod, pares)
        acertos, cod, pares = melhor
        # Só aceita se a ordem bateu em quase tudo (por acaso, bateria em ~20%).
        if acertos < 0.9 * len(nossas):
            resumo[sigla] = (cod, acertos, len(nossas))
            continue
        con.executemany(
            "INSERT OR REPLACE INTO questoes_tri (questao_id, a, b, c, anulada) VALUES (?, ?, ?, ?, ?)",
            [(qid, i["a"], i["b"], i["c"], int(i["aban"])) for qid, i in pares.items()],
        )
        resumo[sigla] = (cod, acertos, len(nossas))
    return resumo


def respostas_do_participante(r: dict, sigla: str, itens: list[dict]):
    resp = (r.get(f"TX_RESPOSTAS_{sigla}") or "").strip()
    ordenados = sorted(itens, key=lambda i: i["pos"])
    if sigla == "LC":
        por_lingua = [i for i in ordenados if i["lingua"] == "0"] + [i for i in ordenados if i["lingua"] == "1"]
        comuns = [i for i in ordenados if i["lingua"] not in ("0", "1")]
        if len(resp) == len(por_lingua) + len(comuns):
            ordenados = por_lingua + comuns
        else:  # só o idioma escolhido aparece nas respostas
            escolhida = (r.get("TP_LINGUA") or "").strip()
            ordenados = [i for i in ordenados if i["lingua"] in ("", escolhida) or i["lingua"] not in ("0", "1")]
    if len(resp) != len(ordenados):
        return None
    return [(i["a"], i["b"], i["c"], x == i["gab"]) for i, x in zip(ordenados, resp) if not i["aban"] and x != "9"]


def mesma_aplicacao(provas: dict[str, list[dict]], cod: str) -> set[str]:
    """Cadernos (cores) com as mesmas questões do caderno casado: exclui reaplicação, digital etc."""
    itens = {i["item"] for i in provas[cod]}
    return {c for c, lista in provas.items() if {i["item"] for i in lista} == itens}


def ajustar_escala(participantes: list[dict], provas: dict[str, list[dict]], sigla: str, permitidas: set[str]):
    pares = []
    for r in participantes:
        nota, prova = (r.get(f"NU_NOTA_{sigla}") or "").strip(), (r.get(f"CO_PROVA_{sigla}") or "").strip()
        if not nota or prova not in permitidas:
            continue
        itens = respostas_do_participante(r, sigla, provas[prova])
        if itens:
            pares.append((tri.theta(itens), num(nota)))
        if len(pares) >= AJUSTE_MAX:
            break
    if len(pares) < 50:
        return None

    def reta(p):
        n = len(p)
        mx, my = sum(t for t, _ in p) / n, sum(y for _, y in p) / n
        s = sum((t - mx) * (y - my) for t, y in p) / sum((t - mx) ** 2 for t, _ in p)
        return my - s * mx, s

    k, s = reta(pares)
    bons = [(t, y) for t, y in pares if abs(k + s * t - y) <= 2]  # descarta casos especiais (ex.: nota recalculada)
    k, s = reta(bons)
    erro = sum(abs(k + s * t - y) for t, y in bons) / len(bons)
    return k, s, erro, len(bons), len(pares)


def importar(ano: int, con) -> None:
    f = ArquivoHTTP(URL.format(ano=ano))
    z = zipfile.ZipFile(io.BufferedReader(f, buffer_size=1 << 20))
    provas = itens_por_prova(ler_csv(z, f"ITENS_PROVA_{ano}.csv"))
    participantes = ler_csv(z, f"MICRODADOS_ENEM_{ano}.csv", AMOSTRA_LINHAS)
    with con:
        resumo = casar_questoes(con, ano, provas)
        for sigla, area in AREAS.items():
            cod, acertos, total = resumo.get(sigla, (None, 0, 0))
            casou = cod and acertos >= 0.9 * total  # sem a ordem casada, não há parâmetros para usar
            escala = ajustar_escala(participantes, provas, sigla, mesma_aplicacao(provas, cod)) if casou else None
            texto = f"  {sigla}: caderno {cod}, ordem bateu em {acertos}/{total}"
            con.execute("DELETE FROM tri_escala WHERE ano = ? AND area = ?", (ano, area))
            if not escala:
                texto += " | sem conferência possível: SEM nota TRI"
            else:
                k, s, erro, n, n_total = escala
                k0, s0 = ESCALA_INEP[sigla]
                ok = n >= MIN_CONFERE * n_total and abs(k - k0) <= TOLERANCIA and abs(s - s0) <= TOLERANCIA
                texto += f" | ajuste {k:.1f} + {s:.1f}*theta, erro {erro:.2f}, {n}/{n_total} batem"
                if ok:
                    con.execute("INSERT INTO tri_escala VALUES (?, ?, ?, ?, ?, ?)", (ano, area, k0, s0, erro, n))
                    texto += " -> OK"
                else:
                    texto += " -> não confere com a escala do INEP: SEM nota TRI"
            print(texto)
    print(f"  baixados {f.baixado / 1e6:.1f} MB de {f.tamanho / 1e6:.0f} MB")


def main() -> None:
    con = conectar()
    criar_tabelas(con)
    anos = [int(a) for a in sys.argv[1:]] or [r[0] for r in con.execute("SELECT DISTINCT ano FROM questoes ORDER BY ano")]
    falhas = []
    for ano in anos:
        print(f"ENEM {ano}")
        try:
            importar(ano, con)
        except Exception as e:  # um ano com problema não impede os outros
            falhas.append(ano)
            print(f"  ! não foi possível importar {ano}: {type(e).__name__}: {e}")
    if not falhas:
        (DATA_DIR / ".tri").write_text(",".join(map(str, anos)), encoding="utf-8")
    print("Pronto." if not falhas else f"Pronto, com falhas em: {falhas}. Rode de novo para tentar outra vez.")


if __name__ == "__main__":
    main()
