"""Revisão espaçada (ADR 0015): a questão errada volta em 1, 3, 7 e 21 dias."""
from datetime import date, timedelta

INTERVALOS = [1, 3, 7, 21]  # dias até a próxima revisão, depois de 0, 1, 2 e 3 acertos na data


def proxima(historico: list[tuple[str, bool]]) -> date | None:
    """historico: [(data 'AAAA-MM-DD', acertou)] em ordem. Devolve quando revisar, ou None
    (nunca errou, ou já acertou nas 4 revisões). Acerto antes da data marcada não conta."""
    devida, acertos = None, 0
    for dia, acertou in historico:
        d = date.fromisoformat(dia[:10])
        if not acertou:
            devida, acertos = d + timedelta(days=INTERVALOS[0]), 0
        elif devida is not None and d >= devida:
            acertos += 1
            devida = d + timedelta(days=INTERVALOS[acertos]) if acertos < len(INTERVALOS) else None
    return devida
