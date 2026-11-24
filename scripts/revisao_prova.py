"""PILOTO (Fase 5.3): página de revisão lado a lado das questões extraídas por importar_prova_pdf.py.

Uso:
    .venv\\Scripts\\python.exe scripts\\revisao_prova.py <pasta da extração> <gabarito.pdf> <dia>

Gera <pasta>/revisao.html: à esquerda, o recorte do caderno; à direita, como a questão fica no TRIunfo (mesmo
conversor de Markdown do app), com o gabarito oficial e os avisos do extrator. Abre direto no navegador, sem servidor.
"""
from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
from importar_gabaritos import ler_gabarito  # noqa: E402

PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisão do piloto</title>
<style>
body { font-family: system-ui, sans-serif; margin: 0 auto; max-width: 1400px; padding: 16px; background: #f5f6f8; color: #1d2330; }
h1 { margin: .2rem 0 1rem; } .resumo { margin-bottom: 1rem; }
.q { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; background: #fff; border: 1px solid #e1e4ea;
  border-radius: 12px; padding: 16px; margin-bottom: 16px; }
.q.aviso { border: 3px solid #c2410c; }
.q h2 { grid-column: 1 / -1; margin: 0; font-size: 1.1rem; }
.original img { max-width: 100%; border: 1px solid #e1e4ea; display: block; margin-bottom: 6px; }
.extraida img { max-width: 100%; }
.alternativas { list-style: none; padding: 0; }
.alternativas li { border: 1px solid #e1e4ea; border-radius: 8px; padding: .4rem .6rem; margin: .3rem 0; }
.alternativas li.certa { border: 2px solid #157a3f; background: #e5f5eb; }
.avisos { color: #c2410c; font-weight: 700; }
.enunciado { font-weight: 600; }
@media (max-width: 800px) { .q { grid-template-columns: 1fr; } }
</style></head><body>
<h1>Revisão do piloto: ENEM __ANO__, __DIA__º dia</h1>
<p class="resumo">__RESUMO__ À esquerda, o caderno do INEP; à direita, como a questão aparece no TRIunfo. A
alternativa em verde é o gabarito oficial. Questões com borda laranja têm aviso do extrator.</p>
<div id="lista"></div>
<script src="markdown.js"></script>
<script>
const questoes = __DADOS__;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
document.getElementById("lista").innerHTML = questoes.map((q) => `
  <section class="q ${q.avisos.length ? "aviso" : ""}">
    <h2>Questão ${q.numero}${q.idioma ? " (" + q.idioma + ")" : ""} · página ${q.pagina} · gabarito ${esc(q.gabarito ?? "?")}</h2>
    <div class="original">${q.originais.map((o) => `<img src="${o}" alt="Recorte do caderno">`).join("")}</div>
    <div class="extraida">
      ${q.avisos.length ? `<p class="avisos">${q.avisos.map(esc).join("<br>")}</p>` : ""}
      ${markdown(q.contexto)}
      <div class="enunciado">${markdown(q.introducao)}</div>
      <ol class="alternativas">${q.alternativas.map((a) => `<li class="${a.letra === q.gabarito ? "certa" : ""}">
        <b>${a.letra}</b> ${markdown(a.texto)}</li>`).join("")}</ol>
    </div>
  </section>`).join("");
</script></body></html>
"""


def main() -> None:
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    pasta, gabarito_pdf, dia = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
    ano = int(gabarito_pdf.name[:4])
    gab = ler_gabarito(gabarito_pdf.read_bytes(), dia)["gabarito"]
    questoes = json.loads((pasta / "questoes.json").read_text(encoding="utf-8"))
    for q in questoes:
        g = gab.get(str(q["numero"]))
        q["gabarito"] = g.get(q["idioma"] or "ingles") if isinstance(g, dict) else g
        for campo in ("contexto", "introducao"):  # as figuras ficam na mesma pasta da página
            q[campo] = q[campo].replace("/imagens/", "")
        for a in q["alternativas"]:
            a["texto"] = a["texto"].replace("/imagens/", "")
    shutil.copy(RAIZ / "app" / "static" / "markdown.js", pasta / "markdown.js")
    # O markdown.js só aceita imagens de /imagens/ (ADR 0026); aqui elas ficam ao lado da página.
    js = (pasta / "markdown.js").read_text(encoding="utf-8").replace('if (!url.startsWith("/imagens/"))', "if (false)")
    (pasta / "markdown.js").write_text(js, encoding="utf-8")
    com_aviso = sum(1 for q in questoes if q["avisos"])
    resumo = f"{len(questoes)} questões; {len(questoes) - com_aviso} com a estrutura completa e {com_aviso} com aviso."
    pagina = (PAGINA.replace("__ANO__", str(ano)).replace("__DIA__", str(dia)).replace("__RESUMO__", html.escape(resumo))
              .replace("__DADOS__", json.dumps(questoes, ensure_ascii=False).replace("</", "<\\/")))
    (pasta / "revisao.html").write_text(pagina, encoding="utf-8")
    print(f"Revisão: {pasta / 'revisao.html'} ({resumo})")


if __name__ == "__main__":
    main()
