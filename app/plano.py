"""Plano de estudos em ciclo (ADR 0016): mais blocos para as áreas mais fracas, intercalados."""
from datetime import date

AREAS = ["linguagens", "ciencias-humanas", "ciencias-natureza", "matematica"]

FASES = [  # (até quantos dias antes da prova, nome, simulados por semana, dica)
    (7, "Semana da prova", 0, "Só revisão leve e a Revisão do dia. Nada de matéria nova. Durma bem e confira o Guia da prova."),
    (30, "Reta final", 1, "Um simulado por semana, no horário real (13h30). Foque no caderno de erros e na Revisão do dia."),
    (90, "Simulados", 0.5, "Um simulado a cada duas semanas, aos domingos às 13h30. Continue o ciclo nas áreas mais fracas."),
    (None, "Base", 0, "Construa a base: um pouco de teoria e muitas questões por área, sempre intercalando as matérias."),
]


def fase(dias: int) -> dict:
    for limite, nome, simulados, dica in FASES:
        if limite is None or dias <= limite:
            return {"nome": nome, "simulados_por_semana": simulados, "dica": dica}


def montar(horas_semana: int, data_prova: date, hoje: date, taxas: dict[str, float | None]) -> dict:
    """taxas: acerto de 0 a 1 por área (None = sem dados ainda). 1 bloco = 50 min de estudo + 10 de pausa."""
    blocos = max(2, min(60, horas_semana))
    resto = blocos - 1  # 1 bloco fixo de redação
    # Toda área recebe peso; quem erra mais recebe mais (sem dados, conta como 50% de acerto).
    pesos = {a: 0.5 + (1 - (taxas.get(a) if taxas.get(a) is not None else 0.5)) for a in AREAS}
    cotas = {a: resto * p / sum(pesos.values()) for a, p in pesos.items()}
    n = {a: int(c) for a, c in cotas.items()}
    for a in sorted(AREAS, key=lambda a: cotas[a] - n[a], reverse=True)[: resto - sum(n.values())]:
        n[a] += 1  # maior resto: a soma fecha exatamente em `resto`
    # Intercala: a cada rodada, uma de cada área que ainda tem blocos, começando pelas mais fracas.
    ciclo, faltam = [], dict(n)
    while any(faltam.values()):
        for a in sorted(AREAS, key=lambda a: (-faltam[a], AREAS.index(a))):
            if faltam[a]:
                ciclo.append(a)
                faltam[a] -= 1
    ciclo.insert(len(ciclo) // 2, "redacao")
    dias = (data_prova - hoje).days
    return {"dias": dias, "fase": fase(dias), "ciclo": ciclo, "blocos_por_area": n}
