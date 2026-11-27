"""Fase 5.3: leva ao banco as questões de uma prova em PDF depois da revisão humana (ADR 0030).

Uso (desenvolvimento; precisa de requirements-dev.txt):
    .venv\\Scripts\\python.exe scripts\\importar_prova_revisada.py <pasta da extração> <gabarito.pdf> <dia>
    depois: .venv\\Scripts\\python.exe scripts\\importar_tri.py <ano>     (nota TRI e assunto, dos microdados)

Entra só o que foi revisado em scripts\\revisao_prova.py: "texto" entra como texto, "print" como imagem do caderno,
"fora" não entra (e sai do banco, se já estava). Questão pendente ou anulada fica de fora, com aviso. As imagens
são copiadas para data/imagens com o prefixo "inep<ano>-", para não se confundirem com as do enem.dev.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

from app.db import DATA_DIR, conectar, criar_tabelas, id_questao  # noqa: E402
from importar_enem_dev import area_oficial  # noqa: E402
from importar_gabaritos import ler_gabarito  # noqa: E402
from importar_prova_pdf import como_print  # noqa: E402
from revisao_prova import chave  # noqa: E402

IMAGEM = re.compile(r"\]\(/imagens/([^()\s]+)\)")


def preparar(q: dict, decisao: str, ano: int) -> tuple[dict, list[str]]:
    """A questão como vai ao banco e as imagens que ela usa (nomes na pasta da extração)."""
    if decisao == "print":
        q = como_print(q)
    elif [a["letra"] for a in q["alternativas"]] != list("ABCDE"):  # ex.: alternativas que são figuras
        raise ValueError(f"questão {chave(q)}: o texto não tem as alternativas A a E. Revise como Print ou Fora.")
    contexto = "\n\n".join(x for x in (q["prefixo"], q["contexto"]) if x)
    usadas = IMAGEM.findall(" ".join([contexto, q["introducao"]] + [a["texto"] for a in q["alternativas"]]))
    trocar = lambda s: IMAGEM.sub(lambda m: f"](/imagens/inep{ano}-{m.group(1)})", s)  # noqa: E731
    return {**q, "contexto": trocar(contexto), "introducao": trocar(q["introducao"]),
            "alternativas": [{**a, "texto": trocar(a["texto"])} for a in q["alternativas"]]}, usadas


def importar(pasta: Path, gabarito_pdf: Path, dia: int, dados: Path = DATA_DIR, sem_revisao: bool = False) -> dict:
    ano = int(gabarito_pdf.name[:4])
    gab = ler_gabarito(gabarito_pdf.read_bytes(), dia)["gabarito"]
    questoes = json.loads((pasta / "questoes.json").read_text(encoding="utf-8"))
    arq = pasta / "revisao.json"
    revisao = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    con = conectar(dados)
    criar_tabelas(con)
    (dados / "imagens").mkdir(exist_ok=True)
    conta = {"texto": 0, "print": 0, "fora": 0, "pendentes": [], "anuladas": []}
    with con:
        for q in questoes:
            qid = id_questao(ano, q["numero"], q["idioma"])
            decisao = revisao.get(chave(q), {}).get("decisao")
            if not decisao and sem_revisao:  # só para testar o app: usa a sugestão do extrator
                decisao = "print" if q["print"] else "texto"
            g = gab.get(str(q["numero"]))
            letra = g.get(q["idioma"] or "ingles") if isinstance(g, dict) else g
            if decisao in (None, "fora") or letra is None:
                if decisao == "fora":
                    conta["fora"] += 1
                elif not decisao:
                    conta["pendentes"].append(q["numero"])
                else:
                    conta["anuladas"].append(q["numero"])
                con.execute("DELETE FROM questoes WHERE id = ?", (qid,))  # pode ter entrado numa importação anterior
                con.execute("DELETE FROM alternativas WHERE questao_id = ?", (qid,))
                continue
            final, usadas = preparar(q, decisao, ano)
            for nome in usadas:
                shutil.copyfile(pasta / nome, dados / "imagens" / f"inep{ano}-{nome}")
            con.execute(
                """
                INSERT INTO questoes (id, ano, indice, area, idioma, titulo, contexto, introducao, arquivos, gabarito, fonte)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, 'inep')
                ON CONFLICT (ano, indice, idioma) DO UPDATE SET
                    area = excluded.area, titulo = excluded.titulo, contexto = excluded.contexto,
                    introducao = excluded.introducao, arquivos = excluded.arquivos,
                    gabarito = excluded.gabarito, fonte = excluded.fonte
                """,
                (qid, ano, q["numero"], area_oficial(ano, q["numero"], ""), q["idioma"],
                 f"Questão {q['numero']} - ENEM {ano}", final["contexto"], final["introducao"], letra),
            )
            con.execute("DELETE FROM alternativas WHERE questao_id = ?", (qid,))
            con.executemany("INSERT INTO alternativas (questao_id, letra, texto, arquivo) VALUES (?, ?, ?, NULL)",
                            [(qid, a["letra"], a["texto"]) for a in final["alternativas"]])
            conta[decisao] += 1
    con.close()
    return conta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", type=Path)
    ap.add_argument("gabarito", type=Path)
    ap.add_argument("dia", type=int)
    ap.add_argument("--dados", type=Path, default=DATA_DIR, help="pasta de dados (padrão: data/)")
    ap.add_argument("--sem-revisao", action="store_true",
                    help="SÓ PARA TESTE: pendentes entram pela sugestão do extrator. Nunca use para o pacote de dados.")
    args = ap.parse_args()
    c = importar(args.pasta, args.gabarito, args.dia, args.dados, args.sem_revisao)
    print(f"{c['texto']} em texto, {c['print']} como print, {c['fora']} fora.")
    if c["anuladas"]:
        print(f"Anuladas (fora do banco): {c['anuladas']}")
    if c["pendentes"]:
        print(f"Ainda sem revisão (fora do banco): {len(c['pendentes'])} questões, a primeira é a {c['pendentes'][0]}.")
    if args.sem_revisao:
        print("ATENÇÃO: importado SEM revisão humana. Não use este banco para o pacote de dados.")


if __name__ == "__main__":
    main()
