"""Guia da prova: Markdown que vem com o app e pode ser atualizado pela internet (ADR 0008)."""
from __future__ import annotations

import functools
import re
import urllib.request

from app.db import DATA_DIR, RAIZ

EMBUTIDO = RAIZ / "app" / "conteudo" / "guia.md"
LOCAL = DATA_DIR / "guia.md"  # versão baixada pela sincronização
URL = "https://raw.githubusercontent.com/geniels/triunfo-enem/main/app/conteudo/guia.md"
LIMITE_BYTES = 200_000
CABECALHO = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def versao(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def ler(texto: str) -> dict:
    """Valida e divide o guia em seções ("## Título"). Levanta ValueError se o arquivo não for um guia."""
    texto = texto.replace("\r\n", "\n")
    m = CABECALHO.match(texto)
    if not m:
        raise ValueError("guia sem cabeçalho ---")
    meta = {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)}
    if not meta.get("versao") or not meta.get("edital"):
        raise ValueError("cabeçalho sem versao/edital")
    versao(meta["versao"])  # versão precisa ser numérica, ex.: 2026.1
    secoes = []
    for parte in re.split(r"^## ", texto[m.end():], flags=re.M)[1:]:
        titulo, _, corpo = parte.partition("\n")
        secoes.append({"titulo": titulo.strip(), "markdown": corpo.strip()})
    if not secoes:
        raise ValueError("guia sem seções")
    return meta | {"secoes": secoes}


def atual() -> dict:
    """O guia mais novo entre o embutido no app e o sincronizado. Em memória até um dos arquivos mudar."""
    return _atual(EMBUTIDO.stat().st_mtime, LOCAL.stat().st_mtime if LOCAL.exists() else None)


@functools.lru_cache(maxsize=1)
def _atual(_mtime_embutido: float, _mtime_local: float | None) -> dict:
    guias = [ler(EMBUTIDO.read_text(encoding="utf-8")) | {"origem": "embutido"}]
    if LOCAL.exists():
        try:
            guias.append(ler(LOCAL.read_text(encoding="utf-8")) | {"origem": "sincronizado"})
        except ValueError:
            pass  # arquivo local corrompido: fica o embutido
    return max(guias, key=lambda g: versao(g["versao"]))


def sincronizar() -> dict:
    """Baixa o guia do repositório oficial; grava só se for válido e mais novo. OSError = sem internet."""
    vigente = atual()
    req = urllib.request.Request(URL, headers={"User-Agent": "triunfo-sincronizacao"})
    with urllib.request.urlopen(req, timeout=15) as r:
        bruto = r.read(LIMITE_BYTES + 1)
    if len(bruto) > LIMITE_BYTES:
        raise ValueError("arquivo grande demais")
    texto = bruto.decode("utf-8")
    novo = ler(texto)
    if versao(novo["versao"]) <= versao(vigente["versao"]):
        return {"atualizado": False, "versao": vigente["versao"], "edital": vigente["edital"]}
    DATA_DIR.mkdir(exist_ok=True)
    tmp = LOCAL.with_suffix(".tmp")
    tmp.write_text(texto, encoding="utf-8")
    tmp.replace(LOCAL)
    return {"atualizado": True, "versao": novo["versao"], "edital": novo["edital"]}
