"""Importa as questões do ENEM (2009-2023) da API aberta enem.dev para o banco local.

Uso:
    python scripts/importar_enem_dev.py              # questões + imagens (uso offline)
    python scripts/importar_enem_dev.py --sem-imagens
    python scripts/importar_enem_dev.py --anos 2022 2023

Os dados são do projeto comunitário enem.dev (https://enem.dev), que por sua vez
os extrai das provas públicas do INEP.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.db import DATA_DIR, IMAGENS_DIR, conectar, criar_tabelas  # noqa: E402

API = "https://api.enem.dev/v1"
USER_AGENT = "triunfo-importador/0.1"
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
IMAGEM_QUEBRADA = "broken-image.svg"


def baixar_json(url: str, tentativas: int = 6):
    for t in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except (OSError, ValueError, http.client.HTTPException) as e:  # rede instável, JSON cortado
            if t == tentativas - 1:
                raise
            espera = 2 ** t
            print(f"  ! erro em {url} ({e}); tentando de novo em {espera}s")
            time.sleep(espera)


def nome_local(url: str) -> str:
    ext = Path(url.split("?")[0]).suffix.lower() or ".png"
    if len(ext) > 5:
        ext = ".png"
    return hashlib.sha1(url.encode()).hexdigest()[:16] + ext


def baixar_imagem(url: str) -> bool:
    destino = IMAGENS_DIR / nome_local(url)
    if destino.exists() and destino.stat().st_size > 0:
        return True
    for t in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                tmp = destino.with_suffix(".tmp")  # grava inteiro antes de valer: Ctrl+C não deixa imagem cortada
                tmp.write_bytes(r.read())
                tmp.replace(destino)
            return True
        except Exception as e:  # imagem individual falhando não deve parar a importação
            if t == 3:
                print(f"  ! imagem não baixada: {url} ({e})")
                return False
            time.sleep(2 ** t)
    return False


def urls_da_questao(q: dict) -> set[str]:
    urls: set[str] = set()
    for campo in (q.get("context"), q.get("alternativesIntroduction")):
        if campo:
            urls.update(IMG_RE.findall(campo))
    urls.update(q.get("files") or [])
    for alt in q.get("alternatives") or []:
        if alt.get("file"):
            urls.add(alt["file"])
        if alt.get("text"):
            urls.update(IMG_RE.findall(alt["text"]))
    return {u for u in urls if u.startswith("http") and IMAGEM_QUEBRADA not in u}


ORDEM_ATE_2016 = ("ciencias-humanas", "ciencias-natureza", "linguagens", "matematica")
ORDEM_DESDE_2017 = ("linguagens", "ciencias-humanas", "ciencias-natureza", "matematica")


def area_oficial(ano: int, indice: int, area_fonte: str) -> str:
    """A área pela numeração oficial da prova. A classificação da fonte tem erros
    (ex.: em 2010 só 7 questões vinham como Linguagens), mas a ordem dos blocos de 45 é fixa."""
    if not 1 <= indice <= 180:
        return area_fonte
    ordem = ORDEM_ATE_2016 if ano <= 2016 else ORDEM_DESDE_2017
    return ordem[(indice - 1) // 45]


def reescrever(texto: str | None, mapa: dict[str, str]) -> str | None:
    if not texto:
        return texto
    for url, local in mapa.items():
        texto = texto.replace(url, local)
    return texto


def buscar_questoes(ano: int, idiomas: list[str]) -> list[dict]:
    """Baixa a prova uma vez por idioma (a API devolve só um idioma de língua estrangeira
    por chamada) e junta tudo sem repetir questões."""
    unicas: dict[tuple, dict] = {}
    for idioma in idiomas or [None]:
        offset = 0
        while True:
            url = f"{API}/exams/{ano}/questions?limit=50&offset={offset}"
            if idioma:
                url += f"&language={idioma}"
            dados = baixar_json(url)
            for q in dados["questions"]:
                unicas.setdefault((q["index"], q.get("language") or ""), q)
            time.sleep(0.5)  # respeita o limite de requisições da API
            if not dados["metadata"].get("hasMore"):
                break
            offset += 50
    return list(unicas.values())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sem-imagens", action="store_true", help="não baixa as imagens (exige internet para vê-las)")
    ap.add_argument("--anos", nargs="*", type=int, help="importa só estes anos")
    args = ap.parse_args()

    DATA_DIR.mkdir(exist_ok=True)
    IMAGENS_DIR.mkdir(exist_ok=True)
    con = conectar()
    criar_tabelas(con)

    provas = {p["year"]: p for p in baixar_json(f"{API}/exams")}
    anos = sorted(provas)
    if args.anos:
        anos = [a for a in anos if a in args.anos]

    total = 0
    for ano in anos:
        print(f"ENEM {ano}: baixando questões...")
        questoes = buscar_questoes(ano, [i["value"] for i in provas[ano].get("languages") or []])

        mapa: dict[str, str] = {}
        if not args.sem_imagens:
            urls = set().union(*(urls_da_questao(q) for q in questoes)) if questoes else set()
            with ThreadPoolExecutor(max_workers=8) as ex:
                ok = dict(zip(urls, ex.map(baixar_imagem, urls)))
            mapa = {u: f"/imagens/{nome_local(u)}" for u, baixou in ok.items() if baixou}
            print(f"  {sum(ok.values())}/{len(urls)} imagens salvas")

        with con:
            for q in questoes:
                arquivos = [mapa.get(u, u) for u in (q.get("files") or []) if IMAGEM_QUEBRADA not in u]
                cur = con.execute(
                    """
                    INSERT INTO questoes (ano, indice, area, idioma, titulo, contexto, introducao,
                                          arquivos, gabarito, fonte)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'enem.dev')
                    ON CONFLICT (ano, indice, idioma) DO UPDATE SET
                        area = excluded.area, titulo = excluded.titulo, contexto = excluded.contexto,
                        introducao = excluded.introducao, arquivos = excluded.arquivos,
                        gabarito = excluded.gabarito
                    RETURNING id
                    """,
                    (
                        q["year"], q["index"], area_oficial(q["year"], q["index"], q["discipline"]),
                        q.get("language") or "", q.get("title"),
                        reescrever(q.get("context"), mapa), reescrever(q.get("alternativesIntroduction"), mapa),
                        json.dumps(arquivos), q.get("correctAlternative"),
                    ),
                )
                qid = cur.fetchone()[0]
                con.execute("DELETE FROM alternativas WHERE questao_id = ?", (qid,))
                for alt in q.get("alternatives") or []:
                    arq = alt.get("file")
                    con.execute(
                        "INSERT INTO alternativas (questao_id, letra, texto, arquivo) VALUES (?, ?, ?, ?)",
                        (qid, alt["letter"], reescrever(alt.get("text"), mapa), mapa.get(arq, arq) if arq else None),
                    )
        total += len(questoes)
        print(f"  {len(questoes)} questões gravadas")

    # Marca de importação completa: o iniciar.bat refaz a importação enquanto ela não existir.
    (DATA_DIR / ".importado").write_text(str(total), encoding="utf-8")
    print(f"\nPronto! {total} questões no banco: {DATA_DIR / 'enem.db'}")


if __name__ == "__main__":
    main()
