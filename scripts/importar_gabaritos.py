"""Importa os gabaritos oficiais de um ENEM (PDFs do INEP) para o "Conferir minha prova" (ADR 0028).

Uso (desenvolvimento; precisa do pypdf, que não vai no instalador):
    .venv\\Scripts\\python.exe -m pip install pypdf
    .venv\\Scripts\\python.exe scripts\\importar_gabaritos.py 2026

Saída: app/conteudo/gabaritos/<ano>.json, que vai dentro do programa (funciona offline). Cada caderno é conferido:
90 questões na faixa do dia, letras A-E (ou anulada) e cor identificada. Se algo não bater, nada é gravado.
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "app" / "conteudo" / "gabaritos"
URL = "https://download.inep.gov.br/enem/provas_e_gabaritos/{ano}_GB_impresso_D{dia}_CD{caderno}.pdf"
CORES = ["Azul", "Amarelo", "Branco", "Verde", "Rosa", "Cinza", "Laranja", "Marrom", "Roxo"]
LINHA = re.compile(r"^(\d{1,3})((?: (?:[A-E]|ANULAD[AO]|X))+)$", re.I)


def baixar(url: str) -> bytes | None:
    """None se o caderno não existe (404). O servidor do INEP falha às vezes: tenta de novo."""
    for tentativa in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except OSError:
            pass
        time.sleep(2 * (tentativa + 1))
    raise OSError(f"não foi possível baixar {url}")


def letra(texto: str) -> str | None:
    """A-E; None para questão anulada (vale para todo mundo)."""
    t = texto.upper()
    return t if t in "ABCDE" and len(t) == 1 else None


def ler_gabarito(pdf: bytes, dia: int) -> dict:
    """{"cor", "numero", "gabarito": {"1": {"ingles": "B", "espanhol": "A"}, "6": "D", ...}}."""
    import pypdf  # só no desenvolvimento
    texto = "\n".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf)).pages)
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    gabarito = {}
    for l in linhas:
        m = LINHA.match(l)
        if not m:
            continue
        numero, letras = int(m.group(1)), [letra(x) for x in m.group(2).split()]
        gabarito[str(numero)] = {"ingles": letras[0], "espanhol": letras[1]} if len(letras) == 2 else letras[0]
    faixa = range(1, 91) if dia == 1 else range(91, 181)
    if sorted(map(int, gabarito)) != list(faixa):
        raise ValueError(f"esperava as questões {faixa.start}–{faixa.stop - 1}, li {len(gabarito)}")
    cor = next((c for c in CORES if re.search(rf"\b{c}\b", texto, re.I)), None)
    numero = re.search(r"CADERNO\s+(\d+)", texto)
    if not cor or not numero:
        raise ValueError("cor ou número do caderno não encontrado")
    return {"cor": cor, "numero": int(numero.group(1)), "gabarito": gabarito}


def main() -> None:
    ano = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if not ano:
        sys.exit("Informe o ano. Exemplo: scripts\\importar_gabaritos.py 2026")
    cadernos = {"1": [], "2": []}
    for dia in (1, 2):
        for caderno in range(1, 15):
            pdf = baixar(URL.format(ano=ano, dia=dia, caderno=caderno))
            if pdf is None:
                continue
            lido = ler_gabarito(pdf, dia)
            if lido["numero"] != caderno:
                raise ValueError(f"o arquivo do caderno {caderno} diz ser o caderno {lido['numero']}")
            cadernos[str(dia)].append(lido)
            print(f"  dia {dia}, caderno {caderno} ({lido['cor']}): {len(lido['gabarito'])} questões")
    if not cadernos["1"] or not cadernos["2"]:
        sys.exit(f"Gabaritos de {ano} incompletos no site do INEP. Nada foi gravado.")
    DESTINO.mkdir(parents=True, exist_ok=True)
    saida = DESTINO / f"{ano}.json"
    dados = {"ano": ano, "fonte": URL.format(ano=ano, dia="N", caderno="N"), "cadernos": cadernos}
    saida.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Gravado: {saida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
