"""Nota TRI do ENEM (ADR 0014): modelo logístico de 3 parâmetros, D = 1, estimativa EAP com priori N(0, 1).

Validado contra as notas oficiais dos microdados: erro médio de ~0,03 ponto (ver scripts/importar_tri.py).
"""
import math

PONTOS = [-4 + i * 0.1 for i in range(81)]
PRIORI = [math.exp(-x * x / 2) for x in PONTOS]


def theta(itens: list[tuple[float, float, float, bool]]) -> float:
    """itens: [(a, b, c, acertou)]. Questão em branco conta como erro, como no ENEM."""
    num = den = 0.0
    for x, peso in zip(PONTOS, PRIORI):
        v = peso
        for a, b, c, acertou in itens:
            p = c + (1 - c) / (1 + math.exp(-a * (x - b)))
            v *= p if acertou else 1 - p
        num += x * v
        den += v
    return num / den


def nota(itens, k: float, s: float) -> float:
    """Converte para a escala do ENEM da área (nota = k + s * theta)."""
    return round(k + s * theta(itens), 1)
