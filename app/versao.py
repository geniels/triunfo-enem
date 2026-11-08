"""Versão do app e aviso de versão nova publicada no GitHub (ADR 0012)."""
import json
import urllib.error
import urllib.request

from app.guia import versao as comparavel

VERSAO = "0.4.1"
URL = "https://api.github.com/repos/geniels/triunfo-enem/releases/latest"


def verificar() -> dict:
    """Só consulta; não baixa nem instala nada. OSError = sem internet."""
    req = urllib.request.Request(URL, headers={"User-Agent": "triunfo", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            dados = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # nenhuma versão publicada ainda
            return {"atual": VERSAO, "nova": None}
        raise
    publicada = dados["tag_name"].lstrip("v")
    if comparavel(publicada) <= comparavel(VERSAO):
        return {"atual": VERSAO, "nova": None}
    url = dados["html_url"]
    if not url.startswith("https://github.com/geniels/triunfo-enem/"):  # o link vai para a tela do aluno
        raise ValueError("link de versão fora do repositório oficial")
    return {"atual": VERSAO, "nova": publicada, "url": url}
