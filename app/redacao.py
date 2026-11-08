"""Regras da redação que não dependem do banco (ADR 0009)."""
from app.db import RAIZ

CONTEUDO = RAIZ / "app" / "conteudo" / "redacao.json"
COMPETENCIAS = {"c1", "c2", "c3", "c4", "c5"}
NIVEIS = {0, 40, 80, 120, 160, 200}


def notas_validas(notas: dict) -> bool:
    """As 5 competências, cada uma num nível oficial (0 a 200, de 40 em 40)."""
    return set(notas) == COMPETENCIAS and all(type(n) is int and n in NIVEIS for n in notas.values())
