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

// Modo turma (ADR 0022): "local" é o próprio PC (sem login); "turma" é quem entra pela rede com nome e PIN.
let eu = { modo: "local", aluno: null };
class PrecisaEntrar extends Error {}
// Cada navegação ganha um número. Resposta que chega depois de outra navegação é descartada (a promessa nunca
// termina): sem isso, uma tela lenta terminava de carregar por cima da tela nova.
let geracao = 0;

async function api(caminho, opcoes) {
  const minha = geracao;
  const r = await fetch(caminho, opcoes);
  if (r.status === 401 && eu.modo === "turma") {
    eu.aluno = null; // PIN trocado pelo organizador ou participante removido
    telaEntrar();
    throw new PrecisaEntrar();
  }
  if (minha !== geracao) return new Promise(() => {});
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(typeof d.detail === "string" ? d.detail : `Erro ${r.status} em ${caminho}`);
  }
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
  simulado: telaSimulado,
  plano: telaPlano,
  guia: telaGuia,
  config: telaConfig,
  questao: (id) => telaQuestaoAvulsa(Number(id)),
};

let sessao = null; // sessão de prática ativa
let limparTela = null; // função de limpeza (ex.: parar cronômetro)

async function navegar() {
  geracao++;
  limparTela?.();
  limparTela = null;
  if (eu.modo === "turma") {
    // Confere a cada tela: o organizador pode ter gerado um PIN novo ou removido o participante.
    eu = await fetch("/api/turma/eu").then((r) => r.json()).catch(() => eu);
    mostrarQuemSou();
    if (!eu.aluno) return telaEntrar();
  }
  const [rota, ...args] = (location.hash.slice(1) || "inicio").split("/");
  document.querySelectorAll(".topo [data-rota]").forEach((a) => a.classList.toggle("ativo", a.dataset.rota === rota));
  conteudo.innerHTML = '<p class="carregando">Carregando…</p>';
  try {
    await (rotas[rota] || telaInicio)(...args);
  } catch (e) {
    if (e instanceof PrecisaEntrar) return;
    conteudo.innerHTML = `<div class="cartao erro"><h2>Algo deu errado</h2><p>${esc(e.message)}</p>
      <p>Verifique se o servidor está rodando e se as questões foram importadas.</p></div>`;
  }
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", navegar);

/* ---------------------------- Início ---------------------------- */

async function telaInicio() {
  const [est, f, g, rev, pl] = await Promise.all([
    api("/api/estatisticas"), filtros(), api("/api/guia"), api("/api/revisao"), api("/api/plano"),
  ]);
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
      <div class="hero"><img src="/static/icone.svg" alt="">
        <div><h1>Bora, ENEM!</h1><p class="sub">Cada questão de hoje é um passo rumo ao seu triunfo.</p></div></div>
      <p>${totalBanco.toLocaleString("pt-BR")} questões oficiais de ${f.anos.length} edições do ENEM (${Math.min(...f.anos)}–${Math.max(...f.anos)}), todas no seu computador.</p>
      <a class="botao grande" href="#praticar">Praticar agora</a>
      <p class="resumo-plano">${
        pl.configurado
          ? `<a href="#plano">Seu plano</a>: ${pl.feitos.length} de ${pl.plano.ciclo.length} blocos nesta semana${pl.plano.dias >= 0 ? ` · faltam ${pl.plano.dias} dias` : ""}`
          : `Ainda sem plano de estudos? <a href="#plano">Monte o seu em 1 minuto</a>.`
      }</p>
    </section>
    ${
      rev.hoje
        ? `<section class="cartao destaque revisao-dia">
            <div><h2>Revisão do dia: ${rev.hoje} ${rev.hoje === 1 ? "questão" : "questões"}</h2>
              <p class="sub">Questões que você errou, na hora certa de rever. As mais fáceis primeiro: na TRI, errar fácil pesa mais.</p></div>
            <button class="botao" id="revisar">Revisar agora</button>
          </section>`
        : rev.proximos_7_dias
          ? `<p class="sub">Nada para revisar hoje. ${rev.proximos_7_dias} ${rev.proximos_7_dias === 1 ? "questão volta" : "questões voltam"} para revisão nos próximos 7 dias.</p>`
          : ""
    }

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
  $("#revisar")?.addEventListener("click", irParaRevisao);
  mostrarLembreteVersao(); // depois de desenhar: não atrasa a tela inicial
}

function irParaRevisao() {
  prefs.salvar({ ...prefs.ler(), modo: "revisao" });
  sessao = null;
  location.hash = "#praticar";
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
        <button type="button" data-v="revisao">Revisão do dia</button>
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
        p.modo === "revisao"
          ? "Nada para revisar hoje. As questões que você errar voltam aqui em 1, 3, 7 e 21 dias."
          : p.modo === "erros"
            ? "Você não tem erros para refazer com esses filtros. Ótimo sinal!"
            : "Nenhuma questão encontrada com esses filtros.";
    }
  };
}

async function carregarProxima() {
  const { area, ano, idioma, modo } = sessao.filtros;
  // As vistas vão no corpo: na URL, sessões longas passavam do limite de tamanho.
  const r = await post("/api/proxima", { area: area || null, ano: ano ? +ano : null, idioma, modo, excluir: sessao.vistas });
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
  renderizarQuestao(q, { placar: "Revisando questão", voltar: "#erros" });
}

/* ---------------------------- Questão ---------------------------- */

// Texto, imagens, enunciado e alternativas: usado na prática e no simulado.
function corpoQuestao(q) {
  const textoTodo = (q.contexto || "") + (q.introducao || "");
  const extras = q.arquivos.filter((a) => !textoTodo.includes(a));
  return `
      <div class="texto">${markdown(q.contexto)}</div>
      ${extras.map((a) => `<img src="${esc(a)}" alt="Imagem da questão" loading="lazy">`).join("")}
      <div class="enunciado">${markdown(q.introducao)}</div>
      <ol class="alternativas" id="alternativas">
        ${q.alternativas
          .map(
            (a) => `<li><button type="button" data-letra="${esc(a.letra)}">
              <span class="letra">${esc(a.letra)}</span>
              <span class="alt-texto">${a.texto ? markdown(a.texto) : ""}${a.arquivo ? `<img src="${esc(a.arquivo)}" alt="Alternativa ${esc(a.letra)}">` : ""}</span>
            </button></li>`
          )
          .join("")}
      </ol>
      ${q.alternativas.length < 5 // 7 questões vêm assim do enem.dev (sem a E); o gabarito está entre as presentes
        ? '<p class="sub">Esta questão veio da fonte com menos de 5 alternativas. A resposta certa está entre as mostradas.</p>'
        : ""}`;
}

function renderizarQuestao(q, { placar, aoResponder, proxima, encerrar, voltar }) {
  // Na sessão de prática a rota não muda entre questões: sem isto, o teclado da questão anterior continuaria
  // ligado e gravaria respostas que o aluno não deu.
  limparTela?.();
  limparTela = null;
  const inicio = Date.now();
  let escolhida = null;
  let respondida = false;

  conteudo.innerHTML = `
    <div class="barra-questao">
      <span class="etiqueta ${CORES_AREA[q.area]}">${esc(q.area_nome.replace(" e suas Tecnologias", ""))}</span>
      <span>ENEM ${q.ano} · Questão ${q.indice}${q.idioma ? " · " + (q.idioma === "ingles" ? "Inglês" : "Espanhol") : ""}</span>
      <span class="cronometro" id="cronometro" role="timer" aria-label="Tempo nesta questão">0:00</span>
    </div>
    <p class="placar">${esc(placar)}</p>

    <article class="cartao questao">
      ${corpoQuestao(q)}

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
      retorno.innerHTML = `<div class="retorno ok"><b>Acertou!</b> Resposta ${esc(r.gabarito)} em ${formatarTempo(tempo)}.</div>`;
    } else {
      retorno.innerHTML = `<div class="retorno nao">
        <b>Resposta certa: ${esc(r.gabarito)}.</b> Por que você errou? <small>(isso alimenta seu caderno de erros)</small>
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
  const desligarRascunho = Rascunho.ligar($(".questao"), `q${q.id}`, lista);
  limparTela = () => { clearInterval(timer); document.removeEventListener("keydown", teclado); desligarRascunho(); };
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
              <div class="erro-rodape">Marcou <b>${esc(e.alternativa)}</b>, certa <b>${esc(e.gabarito)}</b>
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

// Apagar pede um segundo clique (sem diálogo do navegador, que atrapalha leitores de tela).
function ligarApagar(rid, antes) {
  const b = $("#r-apagar");
  b.onclick = async () => {
    if (!b.dataset.confirmar) {
      b.dataset.confirmar = "1";
      b.textContent = "Clique de novo para apagar de vez";
      return;
    }
    antes?.();
    await api(`/api/redacoes/${rid}`, { method: "DELETE" });
    location.hash = "#redacao";
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
        <button class="botao link perigo" id="r-apagar">Apagar</button>
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
  ligarApagar(r.id, () => (sujo = false)); // não salvar de volta o que foi apagado
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
        <button class="botao link perigo" id="r-apagar">Apagar</button>
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
  ligarApagar(r.id);
  limparTela = () => (conteudo.onchange = null);
  atualizarTotal();
}

/* ---------------------------- Simulado (ADR 0013) ---------------------------- */

const NOME_DIA = {
  1: "1º dia: Linguagens e Ciências Humanas",
  2: "2º dia: Ciências da Natureza e Matemática",
};
const relogio = (s) =>
  `${Math.floor(s / 3600)}:${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

async function telaSimulado(id, qid) {
  if (id && qid) return revisarQuestaoSimulado(Number(id), Number(qid));
  if (id) return abrirSimulado(Number(id));
  const [f, lista] = await Promise.all([filtros(), api("/api/simulados")]);
  const p = prefs.ler();
  conteudo.innerHTML = `
    <section class="cartao config">
      <h1>Simulado</h1>
      <p class="sub">Um dia de prova inteiro de um ano, na ordem oficial e com o tempo oficial. Treine o ritmo, a técnica
        das duas passadas e o preenchimento do cartão-resposta. O gabarito só aparece quando você entregar.</p>
      <div class="campos">
        <label>Ano da prova
          <select id="s-ano">${f.anos.map((a) => `<option>${a}</option>`).join("")}</select>
        </label>
        <label>Dia
          <select id="s-dia">
            <option value="1">${NOME_DIA[1]} (90 questões, 5h30)</option>
            <option value="2">${NOME_DIA[2]} (90 questões, 5h)</option>
          </select>
        </label>
        <label>Língua estrangeira
          <select id="s-idioma"><option value="ingles">Inglês</option><option value="espanhol">Espanhol</option></select>
        </label>
      </div>
      <p class="sub">No 1º dia, as 5h30 incluem a redação: reserve cerca de 1h20 e escreva na aba
        <a href="#redacao">Redação</a> com o tema do mesmo ano.</p>
      <div class="acoes"><button class="botao grande" id="s-comecar">Começar simulado</button></div>
    </section>
    <section class="cartao">
      <h2>Seus simulados</h2>
      ${
        lista.length
          ? `<ul class="lista-redacoes">${lista
              .map(
                (s) => `<li><a href="#simulado/${s.id}"><b>ENEM ${s.ano} · ${NOME_DIA[s.dia]}</b>
                  <span>${dataCurta(s.criado_em)} · ${
                    s.entregue
                      ? `<b>${s.acertos}</b> acertos de ${s.total} · ${relogio(s.tempo_seg)}`
                      : `em andamento: ${s.respondidas} de ${s.total} respondidas`
                  }</span></a></li>`
              )
              .join("")}</ul>`
          : "<p class='vazio'>Nenhum ainda. Que tal reservar um domingo à tarde, das 13h30 em diante, como no dia da prova?</p>"
      }
    </section>`;
  $("#s-idioma").value = p.idioma || "ingles";
  $("#s-comecar").onclick = async () => {
    const r = await post("/api/simulados", { ano: +$("#s-ano").value, dia: +$("#s-dia").value, idioma: $("#s-idioma").value });
    location.hash = `#simulado/${r.id}`;
  };
}

async function abrirSimulado(id) {
  const s = await api(`/api/simulados/${id}`);
  return s.entregue ? resultadoSimulado(s) : fazerSimulado(s);
}

function fazerSimulado(s) {
  const cache = {}; // questões já baixadas
  const buscar = (qid) => (cache[qid] ??= api(`/api/questao/${qid}`).catch((e) => { delete cache[qid]; throw e; }));
  const marcadas = new Set(s.marcadas);
  let atual = Math.max(0, s.questoes.findIndex((q) => !s.respostas[q])); // primeira sem resposta
  const inicio = Date.now() - s.tempo_seg * 1000;
  const decorrido = () => Math.floor((Date.now() - inicio) / 1000);

  conteudo.innerHTML = `
    <div class="barra-questao">
      <span class="etiqueta area-mat">Simulado</span>
      <span>ENEM ${s.ano} · ${NOME_DIA[s.dia]}</span>
      <span class="cronometro" id="cronometro" role="timer" aria-label="Tempo restante"></span>
    </div>
    <p class="placar" id="s-progresso"></p>
    <div class="simulado">
      <article class="cartao questao" id="s-questao"><p class="carregando">Carregando…</p></article>
      <aside class="cartao cartao-resposta" aria-label="Cartão-resposta">
        <h2>Cartão-resposta</h2>
        <div class="grade-cartao" id="s-grade"></div>
        <p class="legenda"><span class="q respondida">1</span> respondida <span class="q marcada">2</span> marcada para revisar</p>
        <button class="botao" id="s-entregar">Entregar simulado</button>
        <p id="s-aviso" class="sub" aria-live="polite"></p>
      </aside>
    </div>
    <p class="atalhos">Atalhos: <kbd>A</kbd>–<kbd>E</kbd> respondem, <kbd>←</kbd> <kbd>→</kbd> mudam de questão,
      <kbd>M</kbd> marca para revisar.</p>`;

  const salvar = (corpo) =>
    s.entregue
      ? Promise.resolve()
      : patch(`/api/simulados/${s.id}`, { tempo_seg: decorrido(), ...corpo }).catch(() => {
          const aviso = $("#s-aviso");
          if (aviso) aviso.textContent = "Não foi possível salvar agora; tente de novo.";
        });

  function atualizarGrade() {
    const n = Object.keys(s.respostas).length;
    $("#s-progresso").textContent = `${n} de ${s.questoes.length} respondidas · ${marcadas.size} marcadas para revisar`;
    $("#s-grade").innerHTML = s.questoes
      .map((qid, i) => {
        const estado = [s.respostas[qid] && "respondida", marcadas.has(qid) && "marcada", i === atual && "atual"].filter(Boolean);
        return `<button type="button" class="q ${estado.join(" ")}" data-i="${i}"
          aria-label="Questão ${s.numeros[i]}${s.respostas[qid] ? ", resposta " + s.respostas[qid] : ", em branco"}${marcadas.has(qid) ? ", marcada" : ""}"
          ${i === atual ? 'aria-current="true"' : ""}>${s.numeros[i]}</button>`;
      })
      .join("");
  }

  let desligarRascunho = null;
  let pronta = false; // a questão de "atual" está na tela: só então dá para responder ou marcar
  async function mostrar(i) {
    atual = Math.min(Math.max(i, 0), s.questoes.length - 1);
    const qid = s.questoes[atual];
    pronta = false;
    atualizarGrade();
    let q;
    try {
      q = await buscar(qid);
    } catch (e) {
      if (e instanceof PrecisaEntrar || s.questoes[atual] !== qid) return;
      $("#s-questao").innerHTML = `<div class="retorno nao"><b>Não foi possível carregar a questão.</b>
        Verifique a conexão com o computador do TRIunfo.</div>
        <div class="acoes"><button class="botao" id="s-tentar">Tentar de novo</button></div>`;
      $("#s-tentar").onclick = () => mostrar(atual);
      return;
    }
    if (s.questoes[atual] !== qid) return; // o aluno já mudou de questão enquanto carregava
    $("#s-questao").innerHTML = `
      <p class="placar"><b>Questão ${q.indice}</b> · ${esc(q.area_nome.replace(" e suas Tecnologias", ""))}</p>
      ${corpoQuestao(q)}
      <div class="acoes">
        <button class="botao secundario" id="s-anterior" ${atual === 0 ? "disabled" : ""}>← Anterior</button>
        <button class="botao secundario" id="s-marcar" aria-pressed="${marcadas.has(qid)}">${marcadas.has(qid) ? "Desmarcar revisão" : "Marcar para revisar"}</button>
        <button class="botao" id="s-proxima" ${atual === s.questoes.length - 1 ? "disabled" : ""}>Próxima →</button>
      </div>`;
    desligarRascunho = Rascunho.ligar($("#s-questao"), `s${s.id}-${qid}`, $("#alternativas"));
    $("#alternativas").querySelectorAll("button").forEach((b) => b.classList.toggle("escolhida", b.dataset.letra === s.respostas[qid]));
    $("#alternativas").onclick = (e) => {
      const b = e.target.closest("button");
      if (b) responder(b.dataset.letra);
    };
    $("#s-anterior").onclick = () => mostrar(atual - 1);
    $("#s-proxima").onclick = () => mostrar(atual + 1);
    $("#s-marcar").onclick = alternarMarca;
    pronta = true;
    buscar(s.questoes[atual + 1] ?? qid).catch(() => {}); // adianta a próxima
  }

  function responder(letra) {
    if (!pronta) return; // a tela ainda mostra a questão anterior
    const qid = s.questoes[atual];
    const nova = s.respostas[qid] === letra ? null : letra; // tocar de novo apaga
    if (nova) s.respostas[qid] = nova;
    else delete s.respostas[qid];
    $("#alternativas").querySelectorAll("button").forEach((b) => b.classList.toggle("escolhida", b.dataset.letra === nova));
    atualizarGrade();
    salvar({ respostas: { [qid]: nova } });
  }

  function alternarMarca() {
    if (!pronta) return;
    const qid = s.questoes[atual];
    marcadas.has(qid) ? marcadas.delete(qid) : marcadas.add(qid);
    salvar({ marcadas: [...marcadas] });
    mostrar(atual);
  }

  $("#s-grade").onclick = (e) => {
    const b = e.target.closest("button");
    if (b) mostrar(+b.dataset.i);
  };
  const entregar = $("#s-entregar");
  entregar.onclick = async () => {
    const brancos = s.questoes.length - Object.keys(s.respostas).length;
    if (!entregar.dataset.confirmar) {
      entregar.dataset.confirmar = "1";
      entregar.textContent = "Confirmar entrega";
      $("#s-aviso").textContent = brancos
        ? `Você deixou ${brancos} em branco. No ENEM não há desconto por erro: vale chutar com consciência antes de entregar.`
        : "Tudo respondido. Clique de novo para entregar.";
      return;
    }
    entregar.disabled = true; // duplo clique não entrega duas vezes
    entregar.textContent = "Entregando…";
    try {
      await patch(`/api/simulados/${s.id}`, { tempo_seg: decorrido() });
      await post(`/api/simulados/${s.id}/entregar`, {});
    } catch (e) {
      if (e instanceof PrecisaEntrar) return; // a tela de entrada já está aberta
      entregar.disabled = false;
      entregar.textContent = "Confirmar entrega";
      $("#s-aviso").textContent = `Não foi possível entregar agora: ${e.message} Tente de novo.`;
      return;
    }
    s.entregue = 1; // nada mais a salvar ao sair da tela
    navegar();
  };

  const cron = $("#cronometro");
  const tique = () => {
    const resta = s.duracao_seg - decorrido();
    cron.textContent = resta > 0 ? relogio(resta) : "Tempo esgotado";
    cron.classList.toggle("estourou", resta <= 30 * 60);
  };
  tique();
  const t1 = setInterval(tique, 1000);
  const t2 = setInterval(() => salvar({}), 30000); // guarda o tempo de prova

  function teclado(e) {
    if (e.target.matches("input, select, textarea") || e.ctrlKey || e.metaKey || e.altKey) return;
    const k = e.key.toUpperCase();
    if (k.length === 1 && "ABCDE".includes(k)) responder(k);
    else if (e.key === "ArrowRight") mostrar(atual + 1);
    else if (e.key === "ArrowLeft") mostrar(atual - 1);
    else if (k === "M") alternarMarca();
  }
  document.addEventListener("keydown", teclado);
  limparTela = () => {
    clearInterval(t1);
    clearInterval(t2);
    document.removeEventListener("keydown", teclado);
    desligarRascunho?.();
    salvar({});
  };
  mostrar(atual);
}

function resultadoSimulado(s) {
  const { areas, itens } = s.resultado;
  const acertos = areas.reduce((n, a) => n + a.acertos, 0);
  const brancos = areas.reduce((n, a) => n + a.brancos, 0);
  conteudo.innerHTML = `
    <section class="cartao">
      <h1>Resultado do simulado</h1>
      <p class="sub">ENEM ${s.ano} · ${NOME_DIA[s.dia]} · ${relogio(s.tempo_seg)} de prova (limite ${relogio(s.duracao_seg)})</p>
      <section class="numeros">
        <div class="numero"><b>${acertos}</b><span>acertos de ${itens.length}</span></div>
        <div class="numero"><b>${itens.length - acertos - brancos}</b><span>erros</span></div>
        <div class="numero"><b>${brancos}</b><span>em branco</span></div>
      </section>
      ${areas
        .map(
          (a) => `<div class="linha-area">
            <div class="linha-area-topo"><span class="bolinha ${CORES_AREA[a.area]}"></span>
              <span class="nome">${esc(a.nome.replace(" e suas Tecnologias", ""))}</span>
              <span class="valor">${a.acertos}/${a.total} acertos${a.nota_tri != null ? ` · <span class="nota-tri">${a.nota_tri.toLocaleString("pt-BR")}</span>` : ""}</span></div>
            <div class="barra"><div class="barra-cheia ${CORES_AREA[a.area]}" style="width:${(100 * a.acertos) / a.total}%"></div></div>
          </div>`
        )
        .join("")}
      ${
        areas.some((a) => a.nota_tri != null)
          ? `<p class="sub"><b>Nota TRI estimada</b>, calculada com os parâmetros oficiais de cada questão publicados pelo
              INEP. Conferimos o cálculo com notas oficiais de participantes: a diferença média ficou abaixo de 1 ponto.
              Duas pessoas com o mesmo número de acertos podem ter notas diferentes: acertar as fáceis vale mais.
              ${areas.some((a) => a.nota_tri != null && a.tri_questoes < 45) ? "Nesta prova faltam algumas questões no banco ou os parâmetros oficiais de algumas delas, então a estimativa pode variar alguns pontos." : ""}</p>`
          : `<p class="sub">A nota TRI não está disponível para esta prova (faltam os parâmetros oficiais deste ano).</p>`
      }
      <p class="sub">Seus erros já estão no <a href="#erros">caderno de erros</a>.</p>
    </section>
    <section class="cartao">
      <h2>Questão por questão</h2>
      <p class="legenda"><span class="q certa">1</span> certa <span class="q errada">2</span> errada <span class="q">3</span> em branco ·
        toque numa questão para revê-la</p>
      <div class="grade-cartao">${itens
        .map((it, i) => {
          const estado = !it.resposta ? "" : it.resposta === it.gabarito ? "certa" : "errada";
          const rotulo = !it.resposta ? "em branco" : estado === "certa" ? "certa" : `errada, marcou ${it.resposta}`;
          return `<a class="q ${estado}" href="#simulado/${s.id}/${it.id}" aria-label="Questão ${it.indice}: ${rotulo}, gabarito ${esc(it.gabarito)}">${it.indice}</a>`;
        })
        .join("")}</div>
      <div class="acoes"><a class="botao" href="#simulado">Voltar aos simulados</a></div>
    </section>`;
}

// Revisão de uma questão do simulado entregue: sua resposta, o gabarito e o seu rascunho, como você deixou.
async function revisarQuestaoSimulado(sid, qid) {
  const s = await api(`/api/simulados/${sid}`);
  if (!s.entregue) {
    location.hash = `#simulado/${sid}`; // o gabarito só sai depois da entrega
    return;
  }
  const itens = s.resultado.itens;
  const i = itens.findIndex((it) => it.id === qid);
  if (i < 0) throw new Error("Essa questão não faz parte deste simulado.");
  const it = itens[i];
  const q = await api(`/api/questao/${qid}`);
  const anterior = itens[i - 1], seguinte = itens[i + 1];
  const situacao = !it.resposta ? "Você deixou em branco" : it.resposta === it.gabarito ? "Você acertou" : `Você marcou ${esc(it.resposta)}`;
  // Mesmo layout do simulado (questão + cartão-resposta ao lado): a questão fica com a mesma largura e o
  // rascunho, guardado em coordenadas relativas à largura, cai exatamente onde a pessoa riscou.
  const grade = itens.map((x) => {
    const estado = !x.resposta ? "" : x.resposta === x.gabarito ? "certa" : "errada";
    const rotulo = !x.resposta ? "em branco" : estado === "certa" ? "certa" : `errada, marcou ${x.resposta}`;
    const aqui = x.id === qid;
    return `<a class="q ${estado}${aqui ? " atual" : ""}" href="#simulado/${sid}/${x.id}" ${aqui ? 'aria-current="page"' : ""}
      aria-label="Questão ${x.indice}: ${rotulo}">${x.indice}</a>`;
  }).join("");
  conteudo.innerHTML = `
    <div class="barra-questao">
      <span class="etiqueta area-mat">Revisão</span>
      <span>Simulado ENEM ${s.ano} · ${NOME_DIA[s.dia]}</span>
    </div>
    <p class="placar"><b>${situacao}</b> · gabarito ${esc(it.gabarito)}${s.marcadas.includes(qid) ? " · você marcou esta para revisar" : ""}</p>
    <div class="simulado">
      <article class="cartao questao" id="s-questao">
        <p class="placar"><b>Questão ${it.indice}</b> · ${esc(q.area_nome.replace(" e suas Tecnologias", ""))}</p>
        ${corpoQuestao(q)}
        <div class="acoes">
          <button class="botao secundario" id="r-anterior" ${anterior ? "" : "disabled"}>← Anterior</button>
          <button class="botao secundario" id="r-proxima" ${seguinte ? "" : "disabled"}>Próxima →</button>
        </div>
      </article>
      <aside class="cartao cartao-resposta" aria-label="Questões do simulado">
        <h2>Questões</h2>
        <div class="grade-cartao">${grade}</div>
        <p class="legenda"><span class="q certa">1</span> certa <span class="q errada">2</span> errada <span class="q">3</span> em branco</p>
        <a class="botao secundario" href="#simulado/${sid}">Voltar ao resultado</a>
      </aside>
    </div>
    <p class="atalhos">Atalhos: <kbd>←</kbd> e <kbd>→</kbd> passam as questões.</p>`;

  const selo = (texto) => `<span class="selo">${texto}</span>`;
  const lista = $("#alternativas");
  lista.querySelectorAll("button").forEach((b) => {
    b.disabled = true;
    if (b.dataset.letra === it.gabarito) {
      b.classList.add("certa");
      b.insertAdjacentHTML("beforeend", selo(it.resposta === it.gabarito ? "Correta · sua resposta" : "Correta"));
    } else if (b.dataset.letra === it.resposta) {
      b.classList.add("errada");
      b.insertAdjacentHTML("beforeend", selo("Sua resposta"));
    }
  });
  const ir = (outro) => outro && (location.hash = `#simulado/${sid}/${outro.id}`);
  $("#r-anterior").onclick = () => ir(anterior);
  $("#r-proxima").onclick = () => ir(seguinte);
  function teclado(e) {
    if (e.target.matches("input, select, textarea") || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "ArrowLeft") ir(anterior);
    else if (e.key === "ArrowRight") ir(seguinte);
  }
  document.addEventListener("keydown", teclado);
  const desligarRascunho = Rascunho.ligar($("#s-questao"), `s${sid}-${qid}`, lista);
  limparTela = () => { document.removeEventListener("keydown", teclado); desligarRascunho(); };
}

/* ---------------------------- Plano de estudos (ADR 0016) ---------------------------- */

const NOME_BLOCO = {
  linguagens: "Linguagens",
  "ciencias-humanas": "Ciências Humanas",
  "ciencias-natureza": "Ciências da Natureza",
  matematica: "Matemática",
  redacao: "Redação",
};

async function telaPlano(arg) {
  const p = await api("/api/plano");
  if (!p.configurado || arg === "editar") return formularioPlano(p);
  const { plano: pl, feitos } = p;
  const feito = new Set(feitos);
  const simulado =
    pl.fase.simulados_por_semana === 1
      ? "Um simulado completo por semana, no horário real (13h30)."
      : pl.fase.simulados_por_semana
        ? "Um simulado completo a cada duas semanas, aos domingos às 13h30."
        : "";
  conteudo.innerHTML = `
    <section class="cartao">
      <h1>${pl.dias >= 0 ? `Faltam ${pl.dias} ${pl.dias === 1 ? "dia" : "dias"} para a prova` : "A data da prova já passou"}</h1>
      <p class="sub">Prova em ${dataCurta(p.data_prova)} · ${p.horas_semana} ${p.horas_semana === 1 ? "hora" : "horas"} por semana ·
        <a href="#plano/editar">alterar</a></p>
      ${pl.dias < 0 ? '<p class="aviso">Atualize a data para a próxima edição do ENEM.</p>' : ""}
    </section>
    <section class="cartao destaque">
      <h2>Fase: ${esc(pl.fase.nome)}</h2>
      <p>${esc(pl.fase.dica)}</p>
    </section>
    <section class="cartao">
      <h2>Seu ciclo desta semana</h2>
      <p class="sub">Cada bloco tem 50 minutos de estudo e 10 de pausa. Siga a ordem quando tiver tempo; perdeu um dia,
        continue de onde parou. As áreas em que você mais erra ganham mais blocos.</p>
      <p class="placar" id="pl-progresso"></p>
      <ol class="ciclo" id="pl-ciclo">
        ${pl.ciclo
          .map(
            (a, i) => `<li><label class="bloco ${a === "redacao" ? "" : CORES_AREA[a]}">
              <input type="checkbox" data-i="${i}" ${feito.has(i) ? "checked" : ""}>
              <span class="bolinha ${CORES_AREA[a] || ""}"></span>
              <span class="nome">${NOME_BLOCO[a]}</span>
              <a href="${a === "redacao" ? "#redacao" : "#praticar"}" data-area="${a}">${a === "redacao" ? "escrever (1h20)" : "praticar"}</a>
            </label></li>`
          )
          .join("")}
      </ol>
      <h2 class="espaco">Também nesta semana</h2>
      <ul>
        <li><b>Todo dia:</b> a <a href="#inicio">Revisão do dia</a> (cerca de 15 minutos).</li>
        ${simulado ? `<li><b>Simulado:</b> ${simulado} <a href="#simulado">Fazer simulado</a></li>` : ""}
      </ul>
    </section>`;

  const progresso = () => {
    $("#pl-progresso").textContent = `${feito.size} de ${pl.ciclo.length} blocos feitos nesta semana`;
  };
  progresso();
  $("#pl-ciclo").onchange = async (e) => {
    const i = +e.target.dataset.i;
    e.target.checked ? feito.add(i) : feito.delete(i);
    progresso();
    await post("/api/plano/feito", { posicao: i, feito: e.target.checked });
  };
  $("#pl-ciclo").onclick = (e) => {
    const link = e.target.closest("a[data-area]");
    if (link && link.dataset.area !== "redacao") {
      // Abre o Praticar já filtrado na área do bloco, com questões novas.
      prefs.salvar({ ...prefs.ler(), area: link.dataset.area, modo: "novas" });
      sessao = null;
    }
  };
}

function formularioPlano(p) {
  conteudo.innerHTML = `
    <section class="cartao config">
      <h1>Montar meu plano</h1>
      <p class="sub">Duas perguntas e o TRIunfo monta um ciclo de estudos para você, dando mais tempo às áreas em que
        você mais erra. Dá para mudar quando quiser.</p>
      <div class="campos">
        <label>Data da prova (1º dia)
          <input type="date" id="pl-data" value="${esc(p.data_prova || "")}" required>
        </label>
        <label>Horas de estudo por semana
          <select id="pl-horas">
            ${[3, 5, 8, 10, 12, 15, 20, 25, 30, 40].map((h) => `<option value="${h}">${h} horas</option>`).join("")}
          </select>
        </label>
      </div>
      <p class="sub">As datas do ENEM saem no edital, geralmente com a prova em novembro. Seja realista nas horas:
        um plano que cabe na sua semana funciona melhor do que um plano perfeito que não é cumprido.</p>
      <div class="acoes"><button class="botao" id="pl-salvar">Montar plano</button>
        ${p.configurado ? '<a class="botao link" href="#plano">Cancelar</a>' : ""}</div>
      <p class="aviso" id="pl-aviso" hidden></p>
    </section>`;
  $("#pl-horas").value = String(p.horas_semana || 10);
  $("#pl-salvar").onclick = async () => {
    const data = $("#pl-data").value;
    if (!data) {
      $("#pl-aviso").hidden = false;
      $("#pl-aviso").textContent = "Escolha a data da prova.";
      return;
    }
    await api("/api/plano", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data_prova: data, horas_semana: +$("#pl-horas").value }),
    });
    if (location.hash === "#plano") navegar(); // mesma rota: o navegador não avisa a troca
    else location.hash = "#plano";
  };
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
  const [g, v] = await Promise.all([api("/api/guia"), api("/api/versao")]);
  const atual = window.aparencia({});
  const TEMAS = { auto: "Automático (igual ao sistema)", claro: "Claro", escuro: "Escuro" };
  const CORES = { azul: "#1f4fb8", roxo: "#6d28d9", verde: "#047857", laranja: "#c2410c" };
  const chips = (grupo, opcoes, valor, rotulo) =>
    `<div class="chips" id="${grupo}">${Object.entries(opcoes)
      .map(([v, t]) => `<button type="button" data-v="${v}" class="${v === valor ? "ativo" : ""}" aria-pressed="${v === valor}">${rotulo(v, t)}</button>`)
      .join("")}</div>`;
  conteudo.innerHTML = `
    <section class="cartao config">
      <h1>Configurações</h1>
      <fieldset><legend>Tema</legend>${chips("c-tema", TEMAS, atual.tema, (v, t) => t)}</fieldset>
      <fieldset><legend>Cor de destaque</legend>${chips("c-cor", CORES, atual.cor,
        (v, hex) => `<span class="amostra" style="background:${hex}"></span>${v[0].toUpperCase() + v.slice(1)}`)}</fieldset>
      <p class="sub">A escolha fica salva neste aparelho.</p>
    </section>
    ${eu.modo === "turma" ? `
    <section class="cartao">
      <h2>Sua conta</h2>
      <p>Você entrou como <b>${esc(eu.aluno.nome)}</b>. Este aparelho fica lembrado.</p>
      <p class="sub">Num computador que outras pessoas usam, saia ao terminar.</p>
      <div class="acoes"><button class="botao secundario" id="sair">Sair</button></div>
    </section>` : `
    <section class="cartao" aria-labelledby="turma-titulo">
      <h2 id="turma-titulo">Outros aparelhos e turma</h2>
      <p class="sub">Use o TRIunfo deste computador em outros aparelhos na mesma rede Wi-Fi: no <b>seu tablet ou
        celular</b>, com o mesmo progresso, ou com <b>colegas</b> (escola, cursinho, amigos), cada um com o seu. Os
        outros aparelhos entram pelo navegador, com nome e um PIN de 4 números. Tudo fica guardado só neste computador,
        que precisa estar ligado com o TRIunfo aberto.</p>
      <div id="turma-corpo"><p class="carregando">Carregando…</p></div>
    </section>`}
    <section class="cartao" ${eu.modo === "turma" ? "hidden" : ""}>
      <h2>Atualizações</h2>
      <p>TRIunfo versão <b>${esc(v.atual)}</b><br>Regras do guia: <b>${esc(g.edital)}</b> (versão ${esc(g.versao)})</p>
      <p class="sub">O TRIunfo funciona sem internet. De vez em quando, conectado, toque abaixo: o guia da prova é
        atualizado na hora (alguns KB) e você fica sabendo se existe uma versão nova do programa.</p>
      <div class="acoes"><button class="botao" id="sincronizar">Verificar atualizações</button></div>
      <label class="opcao"><input type="checkbox" id="lembrete-versao"> Avisar na tela inicial quando houver versão
        nova <small>(consulta o GitHub no máximo uma vez por dia, só se houver internet; nada é instalado sem você clicar)</small></label>
      <div id="resultado" aria-live="polite"></div>
    </section>`;

  for (const [grupo, chave] of [["#c-tema", "tema"], ["#c-cor", "cor"]]) {
    $(grupo).onclick = (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      window.aparencia({ [chave]: b.dataset.v === "auto" ? undefined : b.dataset.v });
      $(grupo).querySelectorAll("button").forEach((x) => {
        x.classList.toggle("ativo", x === b);
        x.setAttribute("aria-pressed", x === b);
      });
    };
  }

  if (eu.modo === "turma") {
    $("#sair").onclick = async () => {
      await fetch("/api/turma/sair", { method: "POST" });
      eu.aluno = null;
      telaEntrar();
    };
    return;
  }
  desenharTurma(await api("/api/turma"));
  const lembrete = $("#lembrete-versao");
  lembrete.checked = (await api("/api/preferencias")).lembrete_versao;
  lembrete.onchange = () =>
    api("/api/preferencias", {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lembrete_versao: lembrete.checked }),
    });

  $("#sincronizar").onclick = async (e) => {
    const botao = e.currentTarget;
    const saida = $("#resultado");
    botao.disabled = true;
    saida.innerHTML = '<p class="carregando">Verificando…</p>';
    const pedir = (url, opcoes) =>
      fetch(url, opcoes).then(async (r) => ({ ok: r.ok, dados: await r.json().catch(() => ({})) }));
    const [gr, vr] = await Promise.all([pedir("/api/guia/sincronizar", { method: "POST" }), pedir("/api/versao?verificar=1")]);
    botao.disabled = false;
    const linhas = [];
    if (!gr.ok) linhas.push(`<div class="retorno nao">${esc(gr.dados.detail || "Não foi possível verificar o guia agora.")}</div>`);
    else if (gr.dados.atualizado)
      linhas.push(`<div class="retorno ok"><b>Guia atualizado!</b> Agora com as regras do ${esc(gr.dados.edital)}. <a href="#guia">Ver as regras</a></div>`);
    else linhas.push(`<div class="retorno ok">Guia da prova: você já tem a versão mais nova.</div>`);
    if (vr.ok && vr.dados.nova && vr.dados.pode_instalar)
      linhas.push(`<div class="retorno destaque-aviso"><b>Nova versão do TRIunfo: ${esc(vr.dados.nova)}.</b>
        <a href="${esc(vr.dados.url)}" target="_blank" rel="noopener">Veja o que mudou</a>. Seu progresso é mantido.
        <div class="acoes"><button class="botao" id="atualizar">Atualizar agora (${vr.dados.tamanho_mb} MB)</button></div></div>`);
    else if (vr.ok && vr.dados.nova)
      linhas.push(`<div class="retorno destaque-aviso"><b>Nova versão do TRIunfo: ${esc(vr.dados.nova)}.</b>
        <a href="${esc(vr.dados.url)}" target="_blank" rel="noopener">Veja o que mudou e como atualizar</a>.
        Na escola, avise o professor ou o responsável pelo laboratório.</div>`);
    else if (vr.ok) linhas.push(`<div class="retorno ok">Programa: você já tem a versão mais nova (${esc(vr.dados.atual)}).</div>`);
    saida.innerHTML = linhas.join("");
    const atualizar = $("#atualizar");
    if (atualizar) atualizar.onclick = () => instalarAtualizacao(atualizar, saida);
  };
}

/* ---------------------------- Atualização e lembrete (ADR 0019 e 0024) ---------------------------- */

async function instalarAtualizacao(botao, saida) {
  botao.disabled = true;
  botao.textContent = "Baixando… (pode levar alguns minutos)";
  const r = await fetch("/api/atualizar", { method: "POST" }).catch(() => null);
  const d = r ? await r.json().catch(() => ({})) : {};
  saida.innerHTML = r?.ok
    ? `<div class="retorno ok"><b>Instalando a versão nova.</b> O TRIunfo vai fechar e abrir de novo sozinho em
        instantes. Pode fechar esta aba.</div>`
    : `<div class="retorno nao">${esc(d.detail || "Não foi possível atualizar agora. Verifique a internet e tente de novo.")}</div>`;
  if (!r?.ok) {
    botao.disabled = false;
    botao.textContent = "Tentar de novo";
  }
}

const ADIAR_DIAS = 3;
function lembreteAdiado(versao) {
  try {
    const a = JSON.parse(localStorage.getItem("triunfo-lembrete")) || {};
    return a.versao === versao && Date.now() < a.ate;
  } catch { return false; }
}

async function mostrarLembreteVersao() {
  if (eu.modo === "turma") return; // na turma, quem atualiza é o organizador
  const v = await fetch("/api/versao/lembrete").then((r) => r.json()).catch(() => null);
  const inicio = $(".boas-vindas");
  if (!v?.nova || !inicio || lembreteAdiado(v.nova) || $("#lembrete")) return; // já saiu do Início ou já mostrou
  inicio.insertAdjacentHTML("beforebegin", `
    <section class="cartao lembrete" id="lembrete" aria-labelledby="lembrete-titulo">
      <h2 id="lembrete-titulo">Versão nova do TRIunfo: ${esc(v.nova)}</h2>
      <p>Traz melhorias e correções. <a href="${esc(v.url)}" target="_blank" rel="noopener">Veja o que mudou</a>.
        Seu progresso é mantido.</p>
      <div class="acoes">
        ${v.pode_instalar ? `<button class="botao" id="l-atualizar">Atualizar agora (${v.tamanho_mb} MB)</button>` : ""}
        <button class="botao link" id="l-depois">Agora não</button>
      </div>
      <div id="l-saida" aria-live="polite"></div>
    </section>`);
  $("#l-atualizar")?.addEventListener("click", (e) => instalarAtualizacao(e.currentTarget, $("#l-saida")));
  $("#l-depois").onclick = () => {
    try { localStorage.setItem("triunfo-lembrete", JSON.stringify({ versao: v.nova, ate: Date.now() + ADIAR_DIAS * 864e5 })); } catch {}
    $("#lembrete").remove();
    $(".hero")?.closest("section")?.querySelector("a, button")?.focus();
  };
}

/* ---------------------------- Modo turma (ADR 0022) ---------------------------- */

function desenharTurma(t, aviso = "") {
  const corpo = $("#turma-corpo");
  if (!corpo) return;
  const linhas = t.participantes.map((p) => `
    <tr>
      <th scope="row">${esc(p.nome)}
        <div class="acoes-linha">
          <button class="botao secundario pequeno" data-pin="${p.id}" aria-label="Gerar novo PIN para ${esc(p.nome)}">Novo PIN</button>
          <button class="botao link pequeno" data-remover="${p.id}" data-nome="${esc(p.nome)}" aria-label="Remover ${esc(p.nome)} da turma">Remover</button>
        </div>
      </th>
      <td>${p.respondidas}</td>
      <td>${p.respondidas ? Math.round((100 * p.acertos) / p.respondidas) + "%" : "—"}</td>
      <td>${p.ultima_atividade ? dataCurta(p.ultima_atividade) : "—"}</td>
    </tr>`).join("");
  corpo.innerHTML = `
    ${t.aberta ? `
      <div class="retorno destaque-aviso">
        <b>Acesso pela rede aberto.</b> No outro aparelho, conectado na mesma rede Wi-Fi, digite no navegador:
        <p class="endereco">${esc(t.endereco)}</p>
        <small>Fica aberto até você fechar aqui ou fechar o TRIunfo. O endereço com 127.0.0.1 ou localhost só funciona
          neste computador.</small>
      </div>
      <div class="acoes"><button class="botao secundario" id="turma-fechar">Fechar o acesso pela rede</button></div>` : `
      <p class="sub">Ao abrir, o Windows pode perguntar sobre o <b>Firewall</b>: marque <b>Redes privadas</b> e
        clique em <b>Permitir acesso</b>. Sem isso, os outros aparelhos não conseguem entrar.</p>
      <div class="acoes"><button class="botao" id="turma-abrir">Abrir acesso pela rede</button></div>`}
    <div class="meu-acesso">
      <h3>Seu acesso nos outros aparelhos</h3>
      <p class="sub">${t.meu_acesso.definido
        ? `No tablet ou celular, escolha "Já tenho acesso" e entre como <b>${esc(t.meu_acesso.nome)}</b> com o seu PIN: o
           progresso é o mesmo deste computador. Para trocar o nome ou o PIN, preencha de novo.`
        : `Para estudar no seu tablet ou celular com o mesmo progresso deste computador, escolha um nome e um PIN. Quem
           vai usar só com colegas não precisa disso.`}</p>
      <form id="meu-acesso" class="campos" novalidate>
        <label>Seu nome <input id="ma-nome" maxlength="40" autocomplete="name"
          value="${t.meu_acesso.definido ? esc(t.meu_acesso.nome) : ""}"></label>
        <label>PIN de 4 números <input id="ma-pin" type="password" inputmode="numeric" maxlength="4" autocomplete="off"></label>
        <label>Repita o PIN <input id="ma-pin2" type="password" inputmode="numeric" maxlength="4" autocomplete="off"></label>
        <div class="acoes"><button class="botao secundario" type="submit">${t.meu_acesso.definido ? "Trocar meu acesso" : "Criar meu acesso"}</button></div>
      </form>
    </div>
    <div id="turma-aviso" aria-live="polite">${aviso}</div>
    ${t.participantes.length ? `
      <div class="tabela"><table>
        <caption>Participantes (${t.participantes.length})</caption>
        <thead><tr><th scope="col">Nome</th><th scope="col">Questões</th><th scope="col">Acertos</th>
          <th scope="col">Última vez</th></tr></thead>
        <tbody>${linhas}</tbody>
      </table></div>
      <p class="sub">Esqueceu o PIN? Clique em <b>Novo PIN</b> e passe o número para a pessoa.</p>`
      : `<p class="sub">Ninguém entrou ainda.</p>`}`;

  const acao = async (botao, fazer) => {
    botao.disabled = true;
    try {
      await fazer();
    } catch (e) {
      desenharTurma(t, `<div class="retorno nao">${esc(e.message)}</div>`);
    }
  };
  $("#meu-acesso").onsubmit = (e) => {
    e.preventDefault();
    const nome = $("#ma-nome").value.trim(), pin = $("#ma-pin").value;
    const falha = (msg, campo) => { // sem redesenhar: não apaga o que a pessoa digitou
      $("#turma-aviso").innerHTML = `<div class="retorno nao">${esc(msg)}</div>`;
      $(campo)?.focus();
    };
    if (nome.length < 2) return falha("Escreva seu nome.", "#ma-nome");
    if (!/^\d{4}$/.test(pin)) return falha("O PIN tem exatamente 4 números.", "#ma-pin");
    if (pin !== $("#ma-pin2").value) return falha("Os dois PINs estão diferentes. Digite de novo.", "#ma-pin");
    acao(e.submitter || $("#meu-acesso button"), async () => {
      const novo = await api("/api/turma/meu-acesso", {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nome, pin }),
      });
      desenharTurma(novo, `<div class="retorno ok">Pronto! No outro aparelho, entre como <b>${esc(novo.meu_acesso.nome)}</b>
        com o seu PIN.${novo.aberta ? "" : " Antes, clique em <b>Abrir acesso pela rede</b>."}</div>`);
    });
  };
  const abrir = $("#turma-abrir");
  if (abrir) abrir.onclick = () => acao(abrir, async () => {
    abrir.textContent = "Abrindo…";
    desenharTurma(await post("/api/turma/abrir", {}));
    $("#turma-fechar")?.focus();
  });
  const fechar = $("#turma-fechar");
  if (fechar) fechar.onclick = () => acao(fechar, async () => {
    desenharTurma(await post("/api/turma/fechar", {}));
    $("#turma-abrir")?.focus();
  });
  corpo.querySelectorAll("[data-pin]").forEach((b) => (b.onclick = () => acao(b, async () => {
    const { pin } = await post(`/api/turma/participantes/${b.dataset.pin}/pin`, {});
    const nome = t.participantes.find((p) => p.id === +b.dataset.pin).nome;
    desenharTurma(await api("/api/turma"),
      `<div class="retorno ok">Novo PIN de <b>${esc(nome)}</b>: <b class="pin">${esc(pin)}</b>. Passe o número para a
        pessoa; ele não aparece de novo.</div>`);
  })));
  corpo.querySelectorAll("[data-remover]").forEach((b) => (b.onclick = () => {
    if (!confirm(`Remover ${b.dataset.nome} da turma? Todo o progresso dessa pessoa será apagado.`)) return;
    acao(b, async () => {
      await api(`/api/turma/participantes/${b.dataset.remover}`, { method: "DELETE" });
      desenharTurma(await api("/api/turma"), `<div class="retorno ok">${esc(b.dataset.nome)} saiu da turma.</div>`);
    });
  }));
}

function mostrarQuemSou() {
  const quem = $("#quem");
  quem.hidden = !eu.aluno;
  quem.textContent = eu.aluno ? `Olá, ${eu.aluno.nome}` : "";
  document.body.classList.toggle("sem-login", eu.modo === "turma" && !eu.aluno);
}

function telaEntrar() {
  limparTela?.();
  limparTela = null;
  Rascunho.esquecer();
  mostrarQuemSou();
  let primeira = false;
  conteudo.innerHTML = `
    <section class="cartao config entrar">
      <img src="/static/icone.svg" alt="" width="64" height="64">
      <h1>Entrar no TRIunfo</h1>
      <p class="sub">Entre com seu nome e um PIN de 4 números para guardar o seu progresso. Se o computador é seu, use o
        nome e o PIN que você criou em Configurações. Este aparelho fica lembrado.</p>
      <fieldset><legend>Você já entrou antes?</legend>
        <div class="chips" id="e-modo">
          <button type="button" data-v="nao" class="ativo" aria-pressed="true">Já tenho acesso</button>
          <button type="button" data-v="sim" aria-pressed="false">Primeira vez</button>
        </div>
      </fieldset>
      <form id="f-entrar" novalidate>
        <div class="campos">
          <label>Seu nome
            <input id="e-nome" autocomplete="name" maxlength="40" required>
          </label>
          <label>PIN de 4 números
            <input id="e-pin" type="password" inputmode="numeric" maxlength="4" autocomplete="off" required
              aria-describedby="e-dica">
          </label>
          <label id="l-pin2" hidden>Repita o PIN
            <input id="e-pin2" type="password" inputmode="numeric" maxlength="4" autocomplete="off">
          </label>
        </div>
        <p class="sub" id="e-dica">Esqueceu o PIN? Peça um novo a quem organiza a turma ou, se o computador é seu, troque em Configurações.</p>
        <div class="acoes"><button class="botao" type="submit" id="e-botao">Entrar</button></div>
        <div id="e-erro" class="retorno nao" role="alert" hidden></div>
      </form>
    </section>`;
  $("#e-nome").focus();

  $("#e-modo").onclick = (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    primeira = b.dataset.v === "sim";
    $("#e-modo").querySelectorAll("button").forEach((x) => {
      x.classList.toggle("ativo", x === b);
      x.setAttribute("aria-pressed", x === b);
    });
    $("#l-pin2").hidden = !primeira;
    $("#e-botao").textContent = primeira ? "Criar meu acesso" : "Entrar";
    $("#e-dica").textContent = primeira
      ? "Use nome e sobrenome, como os colegas conhecem você. Escolha um PIN fácil de lembrar e não conte para ninguém."
      : "Esqueceu o PIN? Peça um novo a quem organiza a turma ou, se o computador é seu, troque em Configurações.";
    $("#e-erro").hidden = true;
  };

  $("#f-entrar").onsubmit = async (e) => {
    e.preventDefault();
    const erro = (msg, campo) => {
      $("#e-erro").hidden = false;
      $("#e-erro").textContent = msg;
      campo?.focus();
    };
    const nome = $("#e-nome").value.trim(), pin = $("#e-pin").value;
    if (nome.length < 2) return erro("Escreva seu nome.", $("#e-nome"));
    if (!/^\d{4}$/.test(pin)) return erro("O PIN tem exatamente 4 números.", $("#e-pin"));
    if (primeira && pin !== $("#e-pin2").value) return erro("Os dois PINs estão diferentes. Digite de novo.", $("#e-pin2"));
    const botao = $("#e-botao");
    botao.disabled = true;
    // fetch direto: aqui um 401 é "PIN errado", e não "precisa entrar".
    const r = await fetch(primeira ? "/api/turma/cadastrar" : "/api/turma/entrar", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nome, pin }),
    }).catch(() => null);
    botao.disabled = false;
    if (!r) return erro("Não foi possível falar com o computador da turma. Confira se você está no mesmo Wi-Fi e se a turma está aberta.");
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      return erro(typeof d.detail === "string" ? d.detail : "Confira o nome e o PIN.", $("#e-pin"));
    }
    eu = await api("/api/turma/eu");
    mostrarQuemSou();
    if (location.hash === "#inicio" || !location.hash) navegar();
    else location.hash = "#inicio";
  };
}

(async function iniciar() {
  try {
    eu = await (await fetch("/api/turma/eu")).json();
  } catch {}
  mostrarQuemSou();
  navegar();
})();
