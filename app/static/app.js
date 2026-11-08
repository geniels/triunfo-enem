"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const conteudo = $("#conteudo");

const MOTIVOS = {
  conteudo: "Não sabia o conteúdo",
  atencao: "Falta de atenção",
  tempo: "Faltou tempo",
  chute: "Chutei",
};

const CORES_AREA = {
  linguagens: "area-ling",
  "ciencias-humanas": "area-hum",
  "ciencias-natureza": "area-nat",
  matematica: "area-mat",
};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function api(caminho, opcoes) {
  const r = await fetch(caminho, opcoes);
  if (!r.ok) throw new Error(`Erro ${r.status} em ${caminho}`);
  return r.json();
}

const post = (caminho, corpo) =>
  api(caminho, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });

// Preferências do aluno ficam no navegador (área, ano, idioma, modo).
const prefs = {
  ler() {
    try { return JSON.parse(localStorage.getItem("enem-prefs")) || {}; } catch { return {}; }
  },
  salvar(p) {
    try { localStorage.setItem("enem-prefs", JSON.stringify(p)); } catch {}
  },
};

let filtrosCache = null;
async function filtros() {
  return (filtrosCache ??= await api("/api/filtros"));
}

/* ---------------------------- Rotas ---------------------------- */

const rotas = {
  inicio: telaInicio,
  praticar: telaPraticar,
  erros: telaErros,
  redacao: telaRedacao,
  guia: telaGuia,
  config: telaConfig,
  questao: (id) => telaQuestaoAvulsa(Number(id)),
};

let sessao = null; // sessão de prática ativa
let limparTela = null; // função de limpeza (ex.: parar cronômetro)

async function navegar() {
  limparTela?.();
  limparTela = null;
  const [rota, arg] = (location.hash.slice(1) || "inicio").split("/");
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("ativo", a.dataset.rota === rota));
  conteudo.innerHTML = '<p class="carregando">Carregando…</p>';
  try {
    await (rotas[rota] || telaInicio)(arg);
  } catch (e) {
    conteudo.innerHTML = `<div class="cartao erro"><h2>Algo deu errado</h2><p>${esc(e.message)}</p>
      <p>Verifique se o servidor está rodando e se as questões foram importadas.</p></div>`;
  }
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", navegar);

/* ---------------------------- Início ---------------------------- */

async function telaInicio() {
  const [est, f, g] = await Promise.all([api("/api/estatisticas"), filtros(), api("/api/guia")]);
  const regras = g.secoes[0];
  const totalBanco = f.areas.reduce((s, a) => s + a.total, 0);

  const barrasArea = est.areas
    .map(
      (a) => `
      <div class="linha-area">
        <div class="linha-area-topo">
          <span class="bolinha ${CORES_AREA[a.valor]}"></span>
          <span class="nome">${esc(a.nome.replace(" e suas Tecnologias", ""))}</span>
          <span class="valor">${a.taxa === null ? "—" : a.taxa + "%"}</span>
        </div>
        <div class="barra"><div class="barra-cheia ${CORES_AREA[a.valor]}" style="width:${a.taxa ?? 0}%"></div></div>
        <div class="detalhe">${a.acertos}/${a.respondidas} acertos${a.tempo_medio ? ` · ${formatarTempo(a.tempo_medio)} por questão` : ""}</div>
      </div>`
    )
    .join("");

  const totalMotivos = Object.values(est.motivos).reduce((s, n) => s + n, 0);
  const motivos = totalMotivos
    ? Object.entries(MOTIVOS)
        .map(([k, nome]) => `<li><span>${nome}</span><b>${est.motivos[k] || 0}</b></li>`)
        .join("")
    : "<li class='vazio'>Quando errar uma questão, marque o motivo. Isso mostra onde focar.</li>";

  const maxDia = Math.max(1, ...est.dias.map((d) => d.respondidas));
  const dias = est.dias.length
    ? `<div class="grafico-dias">${est.dias
        .map(
          (d) => `<div class="dia" title="${d.dia}: ${d.acertos}/${d.respondidas}">
            <div class="dia-barra" style="height:${(100 * d.respondidas) / maxDia}%">
              <div class="dia-acertos" style="height:${(100 * d.acertos) / d.respondidas}%"></div>
            </div><span>${d.dia.slice(8)}/${d.dia.slice(5, 7)}</span></div>`
        )
        .join("")}</div>`
    : "<p class='vazio'>Seu histórico dos últimos 14 dias aparece aqui.</p>";

  conteudo.innerHTML = `
    <section class="boas-vindas">
      <h1>Bons estudos!</h1>
      <p>${totalBanco.toLocaleString("pt-BR")} questões oficiais de ${f.anos.length} edições do ENEM (${Math.min(...f.anos)}–${Math.max(...f.anos)}), todas no seu computador.</p>
      <a class="botao grande" href="#praticar">Praticar agora</a>
    </section>

    <section class="numeros">
      <div class="numero"><b>${est.total}</b><span>questões respondidas</span></div>
      <div class="numero"><b>${est.taxa === null ? "—" : est.taxa + "%"}</b><span>de acertos</span></div>
      <div class="numero"><b>${est.total - est.acertos}</b><span>erros para revisar</span></div>
    </section>

    <div class="grade">
      <section class="cartao"><h2>Desempenho por área</h2>${barrasArea}</section>
      <section class="cartao">
        <h2>Por que você erra</h2><ul class="lista-motivos">${motivos}</ul>
        <h2 class="espaco">Últimos dias</h2>${dias}
      </section>
    </div>

    <section class="cartao guia destaque espaco-topo">
      <h2>${esc(regras.titulo)}: ${esc(g.edital)}</h2>
      ${markdown(regras.markdown)}
      <a href="#guia">Ver o guia completo da prova</a>
    </section>

    <section class="cartao dicas">
      <h2>Como estudar com mais resultado</h2>
      <ul>
        <li><b>Resolva questões em vez de só reler.</b> Lembrar ativamente fixa muito mais que reler o resumo.</li>
        <li><b>Revise seus erros depois de alguns dias.</b> Use o modo “Refazer erros”: rever no momento certo evita o esquecimento.</li>
        <li><b>Misture as áreas.</b> A prova é misturada; treinar assim prepara melhor que 50 questões do mesmo tema.</li>
        <li><b>Cuide do tempo.</b> No ENEM você tem cerca de 3 minutos por questão, contando a redação no 1º dia.</li>
        <li><b>Não erre as fáceis.</b> Na nota TRI, acertar difíceis e errar fáceis vale menos. Faça as fáceis primeiro.</li>
      </ul>
    </section>`;
}

function formatarTempo(seg) {
  seg = Math.round(seg);
  const m = Math.floor(seg / 60);
  const s = seg % 60;
  return m ? `${m}min${s ? " " + s + "s" : ""}` : `${s}s`;
}

/* ---------------------------- Praticar ---------------------------- */

async function telaPraticar() {
  if (sessao) return mostrarQuestaoDaSessao();
  const f = await filtros();
  const p = { area: "", ano: "", idioma: "ingles", modo: "novas", ...prefs.ler() };

  conteudo.innerHTML = `
    <section class="cartao config">
      <h1>Praticar</h1>
      <p class="sub">Escolha o que estudar. Questões sorteadas na ordem aleatória.</p>

      <fieldset><legend>Área</legend><div class="chips" id="f-area">
        <button type="button" data-v="">Todas (misturado)</button>
        ${f.areas.map((a) => `<button type="button" data-v="${a.valor}" class="${CORES_AREA[a.valor]}-borda">${esc(a.nome.replace(" e suas Tecnologias", ""))} <small>${a.total}</small></button>`).join("")}
      </div></fieldset>

      <div class="campos">
        <label>Ano da prova
          <select id="f-ano"><option value="">Todos os anos</option>${f.anos.map((a) => `<option>${a}</option>`).join("")}</select>
        </label>
        <label>Língua estrangeira
          <select id="f-idioma"><option value="ingles">Inglês</option><option value="espanhol">Espanhol</option></select>
        </label>
      </div>

      <fieldset><legend>Modo</legend><div class="chips" id="f-modo">
        <button type="button" data-v="novas">Questões novas</button>
        <button type="button" data-v="erros">Refazer erros</button>
        <button type="button" data-v="todas">Todas</button>
      </div></fieldset>

      <button class="botao grande" id="comecar">Começar</button>
      <p class="aviso" id="aviso" hidden></p>
    </section>`;

  const marcarChip = (grupo, valor) =>
    grupo.querySelectorAll("button").forEach((b) => b.classList.toggle("ativo", b.dataset.v === valor));
  const gArea = $("#f-area");
  const gModo = $("#f-modo");
  marcarChip(gArea, p.area);
  marcarChip(gModo, p.modo);
  $("#f-ano").value = p.ano;
  $("#f-idioma").value = p.idioma;
  gArea.onclick = (e) => { const b = e.target.closest("button"); if (b) { p.area = b.dataset.v; marcarChip(gArea, p.area); } };
  gModo.onclick = (e) => { const b = e.target.closest("button"); if (b) { p.modo = b.dataset.v; marcarChip(gModo, p.modo); } };

  $("#comecar").onclick = async () => {
    p.ano = $("#f-ano").value;
    p.idioma = $("#f-idioma").value;
    prefs.salvar(p);
    sessao = { filtros: { ...p }, vistas: [], acertos: 0, respondidas: 0 };
    const ok = await carregarProxima();
    if (!ok) {
      sessao = null;
      const aviso = $("#aviso");
      aviso.hidden = false;
      aviso.textContent =
        p.modo === "erros" ? "Você não tem erros para refazer com esses filtros. Ótimo sinal!" : "Nenhuma questão encontrada com esses filtros.";
    }
  };
}

async function carregarProxima() {
  const { area, ano, idioma, modo } = sessao.filtros;
  const qs = new URLSearchParams({ idioma, modo });
  if (area) qs.set("area", area);
  if (ano) qs.set("ano", ano);
  sessao.vistas.forEach((id) => qs.append("excluir", id));
  const r = await api("/api/proxima?" + qs);
  if (!r.id) return false;
  sessao.restantes = r.restantes;
  sessao.atual = await api("/api/questao/" + r.id);
  sessao.vistas.push(r.id);
  mostrarQuestaoDaSessao();
  return true;
}

function mostrarQuestaoDaSessao() {
  const placar = `${sessao.acertos}/${sessao.respondidas} acertos nesta sessão · ${sessao.restantes - 1} restantes`;
  renderizarQuestao(sessao.atual, {
    placar,
    aoResponder: (correta) => { sessao.respondidas++; if (correta) sessao.acertos++; },
    proxima: async () => {
      if (!(await carregarProxima())) {
        conteudo.innerHTML = `<section class="cartao fim"><h1>Sessão concluída!</h1>
          <p>Você acertou <b>${sessao.acertos} de ${sessao.respondidas}</b> questões.</p>
          <a class="botao" href="#inicio">Ver meu desempenho</a></section>`;
        sessao = null;
      }
    },
    encerrar: () => { sessao = null; location.hash = "#inicio"; },
  });
}

async function telaQuestaoAvulsa(id) {
  const q = await api("/api/questao/" + id);
  renderizarQuestao(q, { placar: "Revisando questão do caderno de erros", voltar: "#erros" });
}

/* ---------------------------- Questão ---------------------------- */

function renderizarQuestao(q, { placar, aoResponder, proxima, encerrar, voltar }) {
  const inicio = Date.now();
  let escolhida = null;
  let respondida = false;

  const textoTodo = (q.contexto || "") + (q.introducao || "");
  const extras = q.arquivos.filter((a) => !textoTodo.includes(a));

  conteudo.innerHTML = `
    <div class="barra-questao">
      <span class="etiqueta ${CORES_AREA[q.area]}">${esc(q.area_nome.replace(" e suas Tecnologias", ""))}</span>
      <span>ENEM ${q.ano} · Questão ${q.indice}${q.idioma ? " · " + (q.idioma === "ingles" ? "Inglês" : "Espanhol") : ""}</span>
      <span class="cronometro" id="cronometro" role="timer" aria-label="Tempo nesta questão">0:00</span>
    </div>
    <p class="placar">${esc(placar)}</p>

    <article class="cartao questao">
      <div class="texto">${markdown(q.contexto)}</div>
      ${extras.map((a) => `<img src="${esc(a)}" alt="Imagem da questão" loading="lazy">`).join("")}
      <div class="enunciado">${markdown(q.introducao)}</div>

      <ol class="alternativas" id="alternativas">
        ${q.alternativas
          .map(
            (a) => `<li><button type="button" data-letra="${a.letra}">
              <span class="letra">${a.letra}</span>
              <span class="alt-texto">${a.texto ? markdown(a.texto) : ""}${a.arquivo ? `<img src="${esc(a.arquivo)}" alt="Alternativa ${a.letra}">` : ""}</span>
            </button></li>`
          )
          .join("")}
      </ol>

      <div id="retorno" aria-live="polite"></div>
      <div class="acoes" id="acoes">
        <button class="botao" id="confirmar" disabled>Confirmar resposta</button>
        ${proxima ? '<button class="botao secundario" id="pular">Pular</button>' : ""}
        ${encerrar ? '<button class="botao link" id="encerrar">Encerrar sessão</button>' : ""}
        ${voltar ? `<a class="botao link" href="${voltar}">Voltar</a>` : ""}
      </div>
    </article>
    <p class="atalhos">Atalhos: teclas <kbd>A</kbd>–<kbd>E</kbd> escolhem, <kbd>Enter</kbd> confirma / avança.</p>`;

  const cron = $("#cronometro");
  const timer = setInterval(() => {
    const s = Math.floor((Date.now() - inicio) / 1000);
    cron.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    cron.classList.toggle("estourou", s > 180);
  }, 1000);

  const lista = $("#alternativas");
  const btnConfirmar = $("#confirmar");

  function escolher(letra) {
    if (respondida) return;
    escolhida = letra;
    lista.querySelectorAll("button").forEach((b) => b.classList.toggle("escolhida", b.dataset.letra === letra));
    btnConfirmar.disabled = false;
  }

  async function confirmar() {
    if (respondida || !escolhida) return;
    respondida = true;
    const tempo = Math.round((Date.now() - inicio) / 1000);
    let r;
    try {
      r = await post("/api/responder", { questao_id: q.id, alternativa: escolhida, tempo_seg: tempo });
    } catch {
      respondida = false; // deixa tentar de novo
      $("#retorno").innerHTML =
        '<div class="retorno nao"><b>Não foi possível salvar a resposta.</b> Verifique se o TRIunfo está aberto e tente de novo.</div>';
      return;
    }
    clearInterval(timer);
    aoResponder?.(r.correta);

    // Selo em texto além da cor: quem é daltônico também precisa distinguir certa/errada.
    const selo = (texto) => `<span class="selo">${texto}</span>`;
    lista.querySelectorAll("button").forEach((b) => {
      b.disabled = true;
      if (b.dataset.letra === r.gabarito) {
        b.classList.add("certa");
        b.insertAdjacentHTML("beforeend", selo(r.correta ? "Correta · sua resposta" : "Correta"));
      } else if (b.dataset.letra === escolhida) {
        b.classList.add("errada");
        b.insertAdjacentHTML("beforeend", selo("Sua resposta"));
      }
    });

    const retorno = $("#retorno");
    if (r.correta) {
      retorno.innerHTML = `<div class="retorno ok"><b>Acertou!</b> Resposta ${r.gabarito} em ${formatarTempo(tempo)}.</div>`;
    } else {
      retorno.innerHTML = `<div class="retorno nao">
        <b>Resposta certa: ${r.gabarito}.</b> Por que você errou? <small>(isso alimenta seu caderno de erros)</small>
        <div class="chips motivos">${Object.entries(MOTIVOS).map(([k, n]) => `<button type="button" data-m="${k}">${n}</button>`).join("")}</div>
      </div>`;
      retorno.querySelector(".motivos").onclick = async (e) => {
        const b = e.target.closest("button");
        if (!b) return;
        await post(`/api/resposta/${r.resposta_id}/motivo`, { motivo: b.dataset.m });
        retorno.querySelectorAll(".motivos button").forEach((x) => x.classList.toggle("ativo", x === b));
      };
    }

    btnConfirmar.remove();
    $("#pular")?.remove();
    if (proxima) {
      const b = document.createElement("button");
      b.className = "botao";
      b.id = "proxima";
      b.textContent = "Próxima questão →";
      b.onclick = proxima;
      $("#acoes").prepend(b);
      b.focus();
    }
  }

  lista.onclick = (e) => { const b = e.target.closest("button"); if (b) escolher(b.dataset.letra); };
  btnConfirmar.onclick = confirmar;
  if ($("#pular")) $("#pular").onclick = proxima;
  if ($("#encerrar")) $("#encerrar").onclick = encerrar;

  function teclado(e) {
    if (e.target.matches("input, select, textarea") || e.ctrlKey || e.metaKey || e.altKey) return;
    const k = e.key.toUpperCase();
    if (!respondida && "ABCDE".includes(k) && k.length === 1) escolher(k);
    else if (e.key === "Enter") {
      if (!respondida) confirmar();
      else if (document.activeElement?.id !== "proxima") $("#proxima")?.click();
    }
  }
  document.addEventListener("keydown", teclado);
  limparTela = () => { clearInterval(timer); document.removeEventListener("keydown", teclado); };
}

/* ---------------------------- Caderno de erros ---------------------------- */

async function telaErros() {
  const erros = await api("/api/erros");
  const porArea = {};
  erros.forEach((e) => (porArea[e.area] = (porArea[e.area] || 0) + 1));

  conteudo.innerHTML = `
    <section class="cartao">
      <h1>Caderno de erros</h1>
      <p class="sub">Questões em que sua última resposta foi errada. Ao acertar de novo, ela sai daqui.</p>
      ${
        erros.length
          ? `<div class="acoes"><button class="botao" id="refazer">Refazer todos os ${erros.length} erros</button></div>`
          : "<p class='vazio'>Nenhum erro por enquanto. Vá praticar!</p>"
      }
    </section>
    <ul class="lista-erros">
      ${erros
        .map(
          (e) => `<li class="cartao">
            <a href="#questao/${e.id}">
              <div class="erro-topo">
                <span class="etiqueta ${CORES_AREA[e.area]}">${esc(e.area_nome.replace(" e suas Tecnologias", ""))}</span>
                <span>ENEM ${e.ano} · Q${e.indice}</span>
                ${e.vezes_errada > 1 ? `<span class="repetido">errou ${e.vezes_errada}x</span>` : ""}
              </div>
              <p class="trecho">${esc(limparTrecho(e.trecho))}…</p>
              <div class="erro-rodape">Marcou <b>${e.alternativa}</b>, certa <b>${e.gabarito}</b>
                ${e.motivo_erro ? ` · ${MOTIVOS[e.motivo_erro]}` : ""}</div>
            </a>
          </li>`
        )
        .join("")}
    </ul>`;

  $("#refazer")?.addEventListener("click", () => {
    const p = { ...prefs.ler(), modo: "erros", area: "", ano: "" };
    prefs.salvar(p);
    sessao = null;
    location.hash = "#praticar";
  });
}

function limparTrecho(t) {
  return (t || "").replace(/!\[[^\]]*\]\([^)]*\)/g, "[imagem]").replace(/[*_#>|]/g, "").replace(/\s+/g, " ").trim();
}

/* ---------------------------- Redação ---------------------------- */

const LETRAS_POR_LINHA = 70; // shortcut: média de letra cursiva na folha do ENEM; cada letra é diferente, é só estimativa
const TEMPO_REDACAO = 80 * 60; // 1h20, o tempo sugerido no Guia da prova

function contarLinhas(texto) {
  return texto
    .split("\n")
    .filter((p) => p.trim())
    .reduce((n, p) => n + Math.max(1, Math.ceil(p.trim().length / LETRAS_POR_LINHA)), 0);
}
const somaNotas = (notas) => Object.values(notas).reduce((s, n) => s + n, 0);
const dataCurta = (d) => `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}`;
const patch = (caminho, corpo) =>
  api(caminho, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });

let redacaoConteudo = null;
async function conteudoRedacao() {
  return (redacaoConteudo ??= await api("/api/redacao/conteudo"));
}

async function telaRedacao(id) {
  if (id) return abrirRedacao(Number(id));
  const [c, lista] = await Promise.all([conteudoRedacao(), api("/api/redacoes")]);
  conteudo.innerHTML = `
    <section class="cartao">
      <h1>Redação</h1>
      <p class="sub">Escolha um tema oficial do ENEM (ou escreva o seu), escreva com o cronômetro de 1h20 e depois
        avalie seu texto pelas 5 competências, do jeito que os corretores fazem.</p>
      <div class="campos">
        <label class="campo-largo">Tema
          <select id="r-tema">
            ${c.temas.map((t) => `<option value="${esc(t.tema)}">${t.ano} · ${esc(t.tema)}${t.obs ? ` (${esc(t.obs)})` : ""}</option>`).join("")}
            <option value="">Outro tema (digitar)…</option>
          </select>
        </label>
        <label class="campo-largo" id="r-livre-rotulo" hidden>Seu tema
          <input id="r-livre" maxlength="300" autocomplete="off">
        </label>
      </div>
      <div class="acoes">
        <button class="botao" id="r-comecar">Começar a escrever</button>
        <button class="botao secundario" id="r-sortear">Sortear tema</button>
      </div>
      <p class="aviso" id="r-aviso" hidden></p>
    </section>
    <section class="cartao">
      <h2>Suas redações</h2>
      ${
        lista.length
          ? `<ul class="lista-redacoes">${lista
              .map(
                (r) => `<li><a href="#redacao/${r.id}"><b>${esc(r.tema)}</b>
                  <span>${dataCurta(r.criado_em)} · ${
                    !r.entregue ? "rascunho" : r.notas ? `<b>${somaNotas(r.notas)}</b> pontos (autoavaliação)` : "falta avaliar"
                  }</span></a></li>`
              )
              .join("")}</ul>`
          : "<p class='vazio'>Nenhuma ainda. A primeira é a mais difícil: comece hoje!</p>"
      }
    </section>`;

  const sel = $("#r-tema");
  sel.onchange = () => ($("#r-livre-rotulo").hidden = sel.value !== "");
  $("#r-sortear").onclick = () => {
    sel.selectedIndex = Math.floor(Math.random() * c.temas.length); // a última opção ("Outro") fica de fora
    sel.onchange();
  };
  $("#r-comecar").onclick = async () => {
    const tema = (sel.value || $("#r-livre").value).trim();
    if (tema.length < 3) {
      $("#r-aviso").hidden = false;
      $("#r-aviso").textContent = "Escreva o tema que você quer treinar.";
      return;
    }
    const r = await post("/api/redacoes", { tema });
    location.hash = `#redacao/${r.id}`;
  };
}

async function abrirRedacao(id) {
  const [r, c] = await Promise.all([api(`/api/redacoes/${id}`), conteudoRedacao()]);
  return r.entregue ? avaliarRedacao(r, c) : escreverRedacao(r);
}

function escreverRedacao(r) {
  conteudo.innerHTML = `
    <div class="barra-questao">
      <span class="etiqueta area-ling">Redação</span>
      <span>${esc(r.tema)}</span>
      <span class="cronometro" id="cronometro" role="timer" aria-label="Tempo de redação">0:00</span>
    </div>
    <article class="cartao">
      <label for="r-texto" class="sub">Escreva em parágrafos (Enter separa um parágrafo do outro). Sem corretor
        ortográfico, como na prova. Tudo é salvo automaticamente.</label>
      <textarea id="r-texto" class="folha" spellcheck="false">${esc(r.texto)}</textarea>
      <div class="rodape-folha"><span id="r-linhas"></span><span id="r-salvo" class="sub" aria-live="polite"></span></div>
      <div class="acoes">
        <button class="botao" id="r-entregar">Entregar e avaliar</button>
        <a class="botao link" href="#redacao">Voltar (fica salvo)</a>
      </div>
    </article>`;

  const area = $("#r-texto");
  const cron = $("#cronometro");
  const inicio = Date.now() - r.tempo_seg * 1000;
  const tempo = () => Math.floor((Date.now() - inicio) / 1000);
  let sujo = false;

  function atualizarLinhas() {
    const n = contarLinhas(area.value);
    const aviso = n <= 7 ? " · até 7 linhas tira nota zero" : n > 30 ? " · passou de 30: não cabe na folha oficial" : "";
    $("#r-linhas").innerHTML = `≈ <b>${n}</b> de 30 linhas<span class="aviso-linhas">${aviso}</span>`;
  }
  async function salvar(extra = {}) {
    sujo = false;
    await patch(`/api/redacoes/${r.id}`, { texto: area.value, tempo_seg: tempo(), ...extra });
    const hora = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    const salvo = $("#r-salvo");
    if (salvo) salvo.textContent = `Salvo às ${hora}`;
  }

  const relogio = setInterval(() => {
    const s = tempo();
    cron.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    cron.classList.toggle("estourou", s > TEMPO_REDACAO);
  }, 1000);
  const autosalvar = setInterval(() => {
    if (sujo) salvar().catch(() => ($("#r-salvo").textContent = "Não foi possível salvar agora"));
  }, 10000);

  area.oninput = () => {
    sujo = true;
    atualizarLinhas();
  };
  $("#r-entregar").onclick = async () => {
    await salvar({ entregue: true });
    navegar(); // reabre a mesma rota, agora na avaliação
  };
  atualizarLinhas();
  area.focus();
  limparTela = () => {
    clearInterval(relogio);
    clearInterval(autosalvar);
    if (sujo) salvar().catch(() => {}); // saiu da tela: não perder o que foi escrito
  };
}

function avaliarRedacao(r, c) {
  const linhas = contarLinhas(r.texto);
  const notas = { ...(r.notas || {}) };
  conteudo.innerHTML = `
    <section class="cartao">
      <h1>Avalie sua redação</h1>
      <p><b>Tema:</b> ${esc(r.tema)}</p>
      <p class="sub">≈ ${linhas} linhas · ${formatarTempo(r.tempo_seg)} de escrita. Releia o texto e, para cada competência,
        marque o nível que descreve melhor o que você escreveu. Seja exigente: é assim que se evolui.</p>
      <details><summary>Ver o texto</summary><div class="folha leitura">${esc(r.texto) || "<i>(vazio)</i>"}</div></details>
      ${linhas <= 7 ? '<p class="retorno nao"><b>Texto insuficiente:</b> com até 7 linhas, a redação recebe nota zero no ENEM (14.7.3).</p>' : ""}
    </section>
    ${c.competencias
      .map(
        (k, i) => `
      <fieldset class="cartao competencia">
        <legend>Competência ${i + 1}: ${esc(k.nome)}</legend>
        <p class="sub">${esc(k.pergunta)}</p>
        ${
          k.elementos
            ? `<div class="elementos"><p><b>Quais elementos sua proposta tem?</b></p>${k.elementos
                .map((e) => `<label><input type="checkbox" class="elemento"> ${esc(e)}</label>`)
                .join("")}</div>`
            : ""
        }
        ${Object.entries(k.niveis)
          .sort((a, b) => b[0] - a[0])
          .map(
            ([n, d]) => `<label class="nivel"><input type="radio" name="${k.id}" value="${n}"${notas[k.id] === +n ? " checked" : ""}>
              <b>${n}</b><span>${esc(d)}</span></label>`
          )
          .join("")}
      </fieldset>`
      )
      .join("")}
    <section class="cartao total">
      <p class="nota-total" aria-live="polite">Nota estimada: <b id="r-total">—</b> / 1000</p>
      <div class="acoes">
        <button class="botao" id="r-salvar">Salvar avaliação</button>
        <button class="botao secundario" id="r-reescrever">Reescrever este tema</button>
        <a class="botao link" href="#redacao">Voltar</a>
      </div>
      <p id="r-msg" aria-live="polite"></p>
    </section>`;

  const completo = () => Object.keys(notas).length === 5;
  const atualizarTotal = () =>
    ($("#r-total").textContent = completo() ? (linhas <= 7 ? 0 : somaNotas(notas)) : "—");

  conteudo.onchange = (e) => {
    const campo = e.target;
    if (campo.type === "radio") notas[campo.name] = +campo.value;
    if (campo.classList.contains("elemento")) {
      // Cada elemento da proposta vale cerca de 40 pontos na C5: sugere o nível, o aluno pode ajustar.
      const n = conteudo.querySelectorAll(".elemento:checked").length * 40;
      conteudo.querySelector(`input[name="c5"][value="${n}"]`).checked = true;
      notas.c5 = n;
    }
    atualizarTotal();
  };
  $("#r-salvar").onclick = async () => {
    if (!completo()) {
      $("#r-msg").textContent = "Marque um nível em cada uma das 5 competências.";
      return;
    }
    await patch(`/api/redacoes/${r.id}`, { notas });
    $("#r-msg").innerHTML = 'Avaliação salva. <a href="#redacao">Ver todas as redações</a>';
  };
  $("#r-reescrever").onclick = async () => {
    const nova = await post("/api/redacoes", { tema: r.tema });
    location.hash = `#redacao/${nova.id}`;
  };
  limparTela = () => (conteudo.onchange = null);
  atualizarTotal();
}

/* ---------------------------- Guia da prova ---------------------------- */
// O conteúdo vem de app/conteudo/guia.md (ou da versão sincronizada em Configurações).

async function telaGuia() {
  const g = await api("/api/guia");
  const [regras, ...secoes] = g.secoes;
  conteudo.innerHTML = `
    <section class="cartao guia">
      <h1>Guia da prova</h1>
      <p class="sub">Regras do <b>${esc(g.edital)}</b>, como administrar o tempo no dia e um modelo de estudo que
        funciona. Os números entre parênteses são os itens do edital.</p>
      <p class="fonte">Versão ${esc(g.versao)} · atualizado em ${esc(g.atualizado || "—")} ·
        <a href="#config">verificar atualização</a></p>
      <nav class="indice" aria-label="Seções do guia">
        ${g.secoes.map((s, i) => `<a href="#guia-${i}">${esc(s.titulo)}</a>`).join("")}
      </nav>
    </section>
    <section class="cartao guia destaque" id="guia-0"><h2>${esc(regras.titulo)}</h2>${markdown(regras.markdown)}</section>
    ${secoes.map((s, i) => `<section class="cartao guia" id="guia-${i + 1}"><h2>${esc(s.titulo)}</h2>${markdown(s.markdown)}</section>`).join("")}`;

  // O índice rola dentro da página; sem isso, "#guia-1" seria tratado como rota.
  $(".indice").onclick = (e) => {
    const a = e.target.closest("a");
    if (!a) return;
    e.preventDefault();
    $(a.getAttribute("href")).scrollIntoView();
  };
}

/* ---------------------------- Configurações ---------------------------- */

async function telaConfig() {
  const g = await api("/api/guia");
  conteudo.innerHTML = `
    <section class="cartao">
      <h1>Configurações</h1>
      <h2 class="espaco">Guia da prova</h2>
      <p>Regras de: <b>${esc(g.edital)}</b><br>Versão ${esc(g.versao)}
        (${g.origem === "sincronizado" ? "baixada da internet" : "a que veio com o TRIunfo"}).</p>
      <p class="sub">O TRIunfo funciona sem internet. Quando sair um edital novo, conecte-se e toque abaixo:
        só o guia é baixado (alguns KB), e só se houver versão mais nova.</p>
      <div class="acoes"><button class="botao" id="sincronizar">Verificar atualização</button></div>
      <div id="resultado" aria-live="polite"></div>
    </section>`;

  $("#sincronizar").onclick = async (e) => {
    const botao = e.currentTarget;
    const saida = $("#resultado");
    botao.disabled = true;
    saida.innerHTML = '<p class="carregando">Verificando…</p>';
    const r = await fetch("/api/guia/sincronizar", { method: "POST" });
    const dados = await r.json().catch(() => ({}));
    botao.disabled = false;
    if (!r.ok) {
      saida.innerHTML = `<div class="retorno nao">${esc(dados.detail || "Não foi possível verificar agora.")}</div>`;
    } else if (dados.atualizado) {
      saida.innerHTML = `<div class="retorno ok"><b>Guia atualizado!</b> Agora com as regras do ${esc(dados.edital)}.
        <a href="#guia">Ver as regras</a></div>`;
    } else {
      saida.innerHTML = `<div class="retorno ok">Você já tem a versão mais nova (${esc(dados.versao)}).</div>`;
    }
  };
}

navegar();
