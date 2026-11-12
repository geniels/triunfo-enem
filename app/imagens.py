"""Largura e altura das imagens das questões, lidas do cabeçalho do arquivo (sem dependência).

Com width/height no <img>, o navegador reserva o espaço antes da imagem chegar: o texto não pula e a camada do
rascunho não precisa ser redesenhada a cada imagem carregada.
"""
from __future__ import annotations

import functools
import re
import struct

from app.db import IMAGENS_DIR

URL_RE = re.compile(r"/imagens/([\w.-]+)")


@functools.lru_cache(maxsize=4096)
def dimensoes(nome: str) -> tuple[int, int] | None:
    """(largura, altura) de um PNG, JPEG, GIF ou BMP de data/imagens; None se não reconhecer."""
    try:
        with open(IMAGENS_DIR / nome, "rb") as f:
            cab = f.read(32)
            if cab.startswith(b"\x89PNG"):
                return struct.unpack(">II", cab[16:24])
            if cab[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", cab[6:10])
            if cab.startswith(b"BM"):
                largura, altura = struct.unpack("<ii", cab[18:26])
                return largura, abs(altura)
            if cab.startswith(b"\xff\xd8"):
                return _jpeg(f)
    except (OSError, struct.error):
        pass
    return None


def _jpeg(f) -> tuple[int, int] | None:
    """Procura o marcador SOF (início do quadro), que traz altura e largura."""
    f.seek(2)
    while True:
        marcador = f.read(2)
        if len(marcador) < 2 or marcador[0] != 0xFF:
            return None
        tipo = marcador[1]
        if tipo in (0xD8, 0x01) or 0xD0 <= tipo <= 0xD7:  # marcadores sem tamanho
            continue
        tamanho = struct.unpack(">H", f.read(2))[0]
        if 0xC0 <= tipo <= 0xCF and tipo not in (0xC4, 0xC8, 0xCC):
            altura, largura = struct.unpack(">xHH", f.read(5))
            return largura, altura
        f.seek(tamanho - 2, 1)


def da_questao(*textos: str | None) -> dict[str, list[int]]:
    """{"/imagens/x.png": [largura, altura]} para as imagens citadas nos textos."""
    saida = {}
    for texto in textos:
        for nome in URL_RE.findall(texto or ""):
            if d := dimensoes(nome):
                saida[f"/imagens/{nome}"] = list(d)
    return saida
