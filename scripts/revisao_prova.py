"""Fase 5.3: revisão humana das questões extraídas por importar_prova_pdf.py (ADR 0030).

Uso:
    .venv\\Scripts\\python.exe scripts\\revisao_prova.py <pasta da extração> <gabarito.pdf> <dia> [--porta 8811]

Abre no navegador uma página com cada questão lado a lado: à esquerda, o recorte do caderno; à direita, como ela fica
no TRIunfo (mesmo conversor de Markdown do app), com o gabarito oficial e os avisos do extrator. Para cada questão,
escolha "Texto", "Print" ou "Fora". Cada escolha é gravada na hora em <pasta>/revisao.json; dá para parar e
continuar depois. Só as questões revisadas entram no banco (scripts/importar_prova_revisada.py).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
from importar_gabaritos import ler_gabarito  # noqa: E402

DECISOES = ("texto", "print", "fora")


def chave(q: dict) -> str:
    return f"{q['numero']}-{q['idioma']}" if q["idioma"] else str(q["numero"])


def gravar_decisao(pasta: Path, dados: dict) -> dict:
    """Grava uma decisão em revisao.json (arquivo temporário + troca: um Ctrl+C não deixa o arquivo pela metade)."""
    if dados.get("decisao") not in DECISOES or not isinstance(dados.get("chave"), str):
        raise ValueError("decisão inválida")
    arq = pasta / "revisao.json"
    revisao = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    revisao[dados["chave"]] = {"decisao": dados["decisao"], "em": datetime.now().isoformat(timespec="seconds")}
    tmp = arq.with_suffix(".tmp")
    tmp.write_text(json.dumps(revisao, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, arq)
    return revisao


class Revisao(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/decisao":
            self.send_error(404)
            return
        try:
            tamanho = int(self.headers.get("Content-Length", 0))
            revisao = gravar_decisao(Path(self.directory), json.loads(self.rfile.read(min(tamanho, 10_000))))
        except ValueError as e:  # inclui JSON inválido
            self.send_error(400, str(e))
            return
        corpo = json.dumps({"revisadas": len(revisao)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # revisao.json muda a cada clique
        super().end_headers()


PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisão ENEM __ANO__ (__DIA__º dia)</title>
<style>
body { font-family: system-ui, sans-serif; margin: 0 auto; max-width: 1400px; padding: 16px; background: #f5f6f8; color: #1d2330; }
h1 { margin: .2rem 0 .5rem; font-size: 1.4rem; }
.topo { position: sticky; top: 0; background: #f5f6f8; padding: .25rem 0; z-index: 1; border-bottom: 1px solid #d6dae2; margin-bottom: 1rem; }
.topo p { margin: .3rem 0; }
.q { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; background: #fff; border: 1px solid #d6dae2;
  border-radius: 12px; padding: 16px; margin-bottom: 16px; }
.q.aviso { border: 3px solid #c2410c; }
.q h2 { grid-column: 1 / -1; margin: 0; font-size: 1.1rem; }
.original img { max-width: 100%; border: 1px solid #d6dae2; display: block; margin-bottom: 6px; }
.extraida img { max-width: 100%; display: block; margin: .5rem 0; }
.alternativas { list-style: none; padding: 0; }
.alternativas li { border: 1px solid #d6dae2; border-radius: 8px; padding: .4rem .6rem; margin: .3rem 0; }
.alternativas li.certa { border: 2px solid #157a3f; background: #e5f5eb; }
.alternativas li.certa::after { content: " (gabarito)"; color: #157a3f; font-weight: 700; }
.avisos { color: #9a3412; font-weight: 700; }
.enunciado { font-weight: 600; }
.decisao { grid-column: 1 / -1; display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }
.decisao button { font: inherit; padding: .5rem 1rem; border-radius: 8px; border: 2px solid #4b5563; background: #fff; cursor: pointer; }
.decisao button[aria-pressed="true"] { background: #1d4ed8; border-color: #1d4ed8; color: #fff; font-weight: 700; }
.decisao button:focus-visible { outline: 3px solid #b45309; outline-offset: 2px; }
.estado { color: #4b5563; }
@media (max-width: 800px) { .q { grid-template-columns: 1fr; } .topo { position: static; } }
</style></head><body>
<div class="topo">
  <h1>Revisão: ENEM __ANO__, __DIA__º dia</h1>
  <p><b id="progresso"></b> · <label><input type="checkbox" id="pendentes"> mostrar só as pendentes</label></p>
  <p>Compare com o caderno à esquerda. <b>Texto</b>: a versão em texto está fiel. <b>Print</b>: a questão entra como
  imagem do caderno (use quando o texto tiver qualquer erro). <b>Fora</b>: não entra no banco.
  Questões com borda laranja têm aviso do extrator e já aparecem como print.</p>
</div>
<div id="lista"></div>
<script src="markdown.js"></script>
<script>
const questoes = __DADOS__;
let revisao = {};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const NOMES = { texto: "Texto", print: "Print", fora: "Fora" };

function previa(q, modo) {
  const prefixo = q.prefixo ? markdown(q.prefixo) : "";
  if (modo === "print") {
    return prefixo + q.prints.map((p) => `<img src="${esc(p)}" alt="Print do caderno">`).join("")
      + `<p class="estado">No app, os botões A–E aparecem só com a letra.</p>`;
  }
  return `${prefixo}${markdown(q.contexto)}<div class="enunciado">${markdown(q.introducao)}</div>
    <ol class="alternativas">${q.alternativas.map((a) => `<li class="${a.letra === q.gabarito ? "certa" : ""}">
      <b>${a.letra}</b> ${markdown(a.texto)}</li>`).join("")}</ol>`;
}

function cartao(q) {
  const d = revisao[q.chave]?.decisao;
  const modo = d === "print" || (!d && q.print) ? "print" : "texto";
  return `<section class="q ${q.avisos.length ? "aviso" : ""}" aria-labelledby="t-${esc(q.chave)}">
    <h2 id="t-${esc(q.chave)}">Questão ${q.numero}${q.idioma ? " (" + q.idioma + ")" : ""} · página ${q.pagina} ·
      gabarito ${esc(q.gabarito ?? "anulada")} · ${d ? "revisada: " + NOMES[d] : "pendente"}</h2>
    <div class="original">${q.originais.map((o) => `<img src="${esc(o)}" alt="Recorte do caderno">`).join("")}</div>
    <div class="extraida">
      ${q.avisos.length ? `<p class="avisos">Aviso: ${q.avisos.map(esc).join("; ")}</p>` : ""}
      <p class="estado">Como fica no app (${modo === "print" ? "print do caderno" : "texto"}):</p>
      ${previa(q, modo)}
    </div>
    <div class="decisao" role="group" aria-label="Decisão da questão ${q.numero}">
      ${["texto", "print", "fora"].map((x) => `<button type="button" data-chave="${esc(q.chave)}" data-decisao="${x}"
        aria-pressed="${d === x}">${NOMES[x]}</button>`).join("")}
      <span class="estado" role="status"></span>
    </div>
  </section>`;
}

const progresso = () => {
  document.getElementById("progresso").textContent =
    `${questoes.filter((q) => revisao[q.chave]).length} de ${questoes.length} revisadas`;
};
function desenhar() {
  const so = document.getElementById("pendentes").checked;
  document.getElementById("lista").innerHTML = questoes.filter((q) => !so || !revisao[q.chave]).map(cartao).join("");
  progresso();
}

document.getElementById("pendentes").onchange = desenhar;
document.getElementById("lista").onclick = async (e) => {
  const b = e.target.closest("button[data-decisao]");
  if (!b) return;
  const { chave: k, decisao } = b.dataset;
  const r = await fetch("/decisao", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chave: k, decisao }) }).catch(() => null);
  if (!r || !r.ok) {
    b.parentElement.querySelector(".estado").textContent = "Não gravou: deixe o revisao_prova.py aberto no terminal.";
    return;
  }
  revisao[k] = { decisao };
  b.closest("section").outerHTML = cartao(questoes.find((q) => q.chave === k));
  progresso();
  document.querySelector(`[data-chave="${CSS.escape(k)}"][data-decisao="${decisao}"]`)?.focus();
};
fetch("revisao.json").then((r) => (r.ok ? r.json() : {})).catch(() => ({})).then((r) => { revisao = r; desenhar(); });
</script></body></html>
"""


def gerar(pasta: Path, gabarito_pdf: Path, dia: int) -> list[dict]:
    ano = int(gabarito_pdf.name[:4])
    gab = ler_gabarito(gabarito_pdf.read_bytes(), dia)["gabarito"]
    questoes = json.loads((pasta / "questoes.json").read_text(encoding="utf-8"))
    for q in questoes:
        g = gab.get(str(q["numero"]))
        q["gabarito"] = g.get(q["idioma"] or "ingles") if isinstance(g, dict) else g
        q["chave"] = chave(q)
        for campo in ("contexto", "introducao", "prefixo"):  # as figuras ficam na mesma pasta da página
            q[campo] = q[campo].replace("/imagens/", "")
        for a in q["alternativas"]:
            a["texto"] = a["texto"].replace("/imagens/", "")
    # O markdown.js só aceita imagens de /imagens/ (ADR 0026); aqui elas ficam ao lado da página.
    js = (RAIZ / "app" / "static" / "markdown.js").read_text(encoding="utf-8")
    (pasta / "markdown.js").write_text(js.replace('if (!url.startsWith("/imagens/"))', "if (false)"), encoding="utf-8")
    pagina = (PAGINA.replace("__ANO__", str(ano)).replace("__DIA__", str(dia))
              .replace("__DADOS__", json.dumps(questoes, ensure_ascii=False).replace("</", "<\\/")))
    (pasta / "revisao.html").write_text(pagina, encoding="utf-8")
    return questoes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", type=Path)
    ap.add_argument("gabarito", type=Path)
    ap.add_argument("dia", type=int)
    ap.add_argument("--porta", type=int, default=8811)
    ap.add_argument("--sem-servidor", action="store_true", help="só gera a página")
    args = ap.parse_args()
    questoes = gerar(args.pasta, args.gabarito, args.dia)
    print(f"{len(questoes)} questões, {sum(1 for q in questoes if q['print'])} com sugestão de print.")
    if args.sem_servidor:
        return
    url = f"http://127.0.0.1:{args.porta}/revisao.html"
    print(f"Revisão em {url} (Ctrl+C para encerrar; cada decisão já fica gravada)")
    servidor = ThreadingHTTPServer(("127.0.0.1", args.porta), partial(Revisao, directory=str(args.pasta)))
    webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
