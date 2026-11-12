"""Versão do app, aviso de versão nova e atualização em 1 clique (ADR 0012 e 0019)."""
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

from app.db import DATA_DIR, RAIZ
from app.guia import versao as comparavel

VERSAO = "0.5.3"
URL = "https://api.github.com/repos/geniels/triunfo-enem/releases/latest"
DOWNLOADS = "https://github.com/geniels/triunfo-enem/releases/download/"  # único lugar de onde se baixa
LIMITE_BYTES = 300_000_000


def _baixar(url: str, timeout: int = 10):
    req = urllib.request.Request(url, headers={"User-Agent": "triunfo", "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout)


def _ultima() -> dict | None:
    try:
        with _baixar(URL) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # nenhuma versão publicada ainda
            return None
        raise


def instalado() -> bool:
    """Edição Estudante instalada pelo instalador (tem desinstalador ao lado), e não a de desenvolvimento."""
    return (RAIZ / "unins000.exe").exists()


def _instalador(dados: dict, versao: str) -> tuple[dict, dict] | None:
    nomes = {a["name"]: a for a in dados.get("assets", [])}
    exe, sha = nomes.get(f"TRIunfo-Estudante-{versao}.exe"), nomes.get(f"TRIunfo-Estudante-{versao}.exe.sha256")
    if not exe or not sha or not all(a["browser_download_url"].startswith(DOWNLOADS) for a in (exe, sha)):
        return None
    return exe, sha


def verificar() -> dict:
    """Só consulta; não baixa nem instala nada. OSError = sem internet."""
    dados = _ultima()
    if not dados:
        return {"atual": VERSAO, "nova": None}
    publicada = dados["tag_name"].lstrip("v")
    if comparavel(publicada) <= comparavel(VERSAO):
        return {"atual": VERSAO, "nova": None}
    url = dados["html_url"]
    if not url.startswith("https://github.com/geniels/triunfo-enem/"):  # o link vai para a tela do aluno
        raise ValueError("link de versão fora do repositório oficial")
    pacote = _instalador(dados, publicada)
    return {"atual": VERSAO, "nova": publicada, "url": url,
            "pode_instalar": bool(pacote) and instalado(),
            "tamanho_mb": round(pacote[0]["size"] / 1e6) if pacote else None}


def baixar_instalador() -> Path:
    """Baixa o instalador da última versão e confere o SHA-256 publicado junto. ValueError se algo não bater."""
    dados = _ultima()
    if not dados:
        raise ValueError("nenhuma versão publicada")
    publicada = dados["tag_name"].lstrip("v")
    if comparavel(publicada) <= comparavel(VERSAO):
        raise ValueError("já está na versão mais nova")
    pacote = _instalador(dados, publicada)
    if not pacote:
        raise ValueError("a versão publicada não tem instalador")
    exe, sha = pacote
    with _baixar(sha["browser_download_url"], 30) as r:
        esperado = r.read(200).decode("ascii", "replace").split()[0].lower()
    pasta = DATA_DIR / "atualizacao"
    pasta.mkdir(exist_ok=True)
    destino = pasta / exe["name"]
    h, total = hashlib.sha256(), 0
    with _baixar(exe["browser_download_url"], 60) as r, open(destino, "wb") as f:
        while (bloco := r.read(1 << 20)) and total <= LIMITE_BYTES:
            total += len(bloco)
            h.update(bloco)
            f.write(bloco)
    if total > LIMITE_BYTES or h.hexdigest() != esperado:
        destino.unlink()
        raise ValueError("o arquivo baixado não confere (SHA-256 diferente); nada foi instalado")
    return destino
