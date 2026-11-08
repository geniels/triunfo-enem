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
  const [est, f] = await Promise.all([api("/api/estatisticas"), filtros()]);
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

function telaRedacao() {
  conteudo.innerHTML = `
    <section class="cartao">
      <h1>Redação</h1>
      <p class="sub">Módulo em construção: banco de temas desde 1998, cronômetro, checklist pelas 5 competências e correção assistida.</p>
      <h2>As 5 competências avaliadas (até 200 pontos cada)</h2>
      <ol class="competencias">
        <li><b>Norma culta</b>: domínio da escrita formal da língua portuguesa.</li>
        <li><b>Tema e tipo de texto</b>: compreender a proposta e desenvolver um texto dissertativo-argumentativo, usando repertório de várias áreas.</li>
        <li><b>Argumentação</b>: selecionar, organizar e interpretar informações e argumentos em defesa de um ponto de vista.</li>
        <li><b>Coesão</b>: usar bem os conectivos e mecanismos linguísticos que ligam as ideias.</li>
        <li><b>Proposta de intervenção</b>: propor uma solução detalhada (agente, ação, meio, finalidade e detalhamento) que respeite os direitos humanos.</li>
      </ol>
    </section>`;
}

/* ---------------------------- Guia da prova ---------------------------- */
// Conteúdo estático do Edital nº 64/2026 (itens citados entre parênteses). Atualizar a cada edital novo.

function telaGuia() {
  conteudo.innerHTML = `
    <section class="cartao guia">
      <h1>Guia da prova</h1>
      <p class="sub">Regras do <b>Edital nº 64, de 21 de maio de 2026</b> (ENEM 2026), como administrar o tempo
        no dia e um modelo de estudo que funciona. Os números entre parênteses são os itens do edital.</p>
      <nav class="indice" aria-label="Seções do guia">
        <a href="#guia-regras">Regras do edital</a>
        <a href="#guia-tempo">Tempo na prova</a>
        <a href="#guia-estudo">Como estudar</a>
        <a href="#guia-vespera">Véspera e dia da prova</a>
      </nav>
    </section>

    <section class="cartao guia" id="guia-regras">
      <h2>Regras do edital: o essencial</h2>
      <p><b>Datas:</b> 8 e 15 de novembro de 2026, domingos (1.3). Tudo no <b>horário de Brasília</b> (1.7).
        Se o seu estado tem outro fuso, faça a conta: no Amazonas, por exemplo, os portões fecham ao meio-dia local.</p>
      <div class="tabela"><table>
        <thead><tr><th>Momento</th><th>Horário (Brasília)</th></tr></thead>
        <tbody>
          <tr><td>Portões abrem</td><td>12h</td></tr>
          <tr><td>Portões fecham</td><td><b>13h</b>: depois disso, ninguém entra (9.2)</td></tr>
          <tr><td>Início das provas</td><td>13h30</td></tr>
          <tr><td>Fim do 1º dia</td><td>19h (5h30 de prova)</td></tr>
          <tr><td>Fim do 2º dia</td><td>18h30 (5h de prova)</td></tr>
        </tbody>
      </table></div>
      <div class="tabela"><table>
        <thead><tr><th>Dia</th><th>Provas</th></tr></thead>
        <tbody>
          <tr><td>1º dia</td><td>Linguagens (45, com inglês ou espanhol) + Ciências Humanas (45) + <b>Redação</b></td></tr>
          <tr><td>2º dia</td><td>Ciências da Natureza (45) + Matemática (45)</td></tr>
        </tbody>
      </table></div>

      <h3>Documento com foto (10.1)</h3>
      <p>Original e válido: RG, CIN (nova identidade), CNH, passaporte, carteira de trabalho emitida após 27/01/1997
        ou carteira de conselho profissional. <b>Valem as versões digitais</b> de e-Título, CNH e CIN no aplicativo oficial
        ou no Gov.br, mas o INEP não se responsabiliza se o celular ou o aplicativo falhar (10.3). Leve o físico se puder.
        <b>Não valem:</b> boletim de ocorrência, protocolos, certidão de nascimento ou casamento, título impresso (10.4).</p>

      <h3>Caneta e material</h3>
      <p>Só <b>caneta esferográfica de tinta preta, de tubo transparente</b> (11.1.30). Lápis, borracha, régua, corretivo,
        relógio de qualquer tipo, boné, gorro, óculos escuros, celular e eletrônicos ficam <b>desligados no envelope
        porta-objetos</b>, embaixo da carteira (11.1.10 a 11.1.15). O lanche será vistoriado (11.1.19).</p>

      <h3>Saídas da sala</h3>
      <ul>
        <li>Sair em definitivo: só <b>depois de 2 horas</b> de prova (11.1.35).</li>
        <li>Levar o caderno de questões: só se sair nos <b>últimos 30 minutos</b> (11.1.34).</li>
        <li>Banheiro a partir das 13h: só acompanhado por um fiscal (11.1.17.1).</li>
      </ul>

      <h3>O que elimina (12.1, principais)</h3>
      <ul>
        <li>Celular ou qualquer aparelho <b>tocar ou vibrar</b>, mesmo dentro do envelope (12.1.20).</li>
        <li>Falar com outro participante a partir das 13h, ou começar antes de autorizado (12.1.3, 12.1.15).</li>
        <li>Anotar em qualquer lugar que não seja o caderno, o rascunho ou o cartão, inclusive na mão (12.1.22).</li>
        <li>Arrancar página do caderno (12.1.23) ou levar o cartão-resposta embora (12.1.24).</li>
        <li>Recusar a revista eletrônica ou a vistoria do lanche (12.1.11).</li>
      </ul>

      <h3>Redação nota zero (14.7)</h3>
      <ul>
        <li>Fugir do tema ou não escrever um texto dissertativo-argumentativo.</li>
        <li>Escrever <b>até 7 linhas</b> (texto insuficiente). Linhas copiadas da proposta não contam (14.8).</li>
        <li>Pôr nome, assinatura ou rubrica no espaço do texto, desenhos ou trechos desconectados de propósito.</li>
        <li>Letra ilegível, ou texto escrito principalmente em outra língua.</li>
      </ul>
      <p>A nota vai de 0 a 1.000: dois corretores dão de 0 a 200 em cada uma das 5 competências; se divergirem muito,
        entra um terceiro (14.5 e 14.6). As objetivas são corrigidas pela <b>TRI</b> (14.3).</p>

      <h3>Depois da prova</h3>
      <p>Gabarito oficial em até <b>10 dias úteis</b> após o 2º dia (15.1). O resultado individual sai na
        Página do Participante, em data a ser divulgada (15.2).</p>
      <p class="fonte">Fonte oficial: Edital nº 64/2026 no Diário Oficial (in.gov.br) e a Cartilha do Participante
        (redação) no portal do INEP (gov.br/inep → ENEM → Outros documentos). Em caso de dúvida, vale o texto oficial.</p>
    </section>

    <section class="cartao guia" id="guia-tempo">
      <h2>Tempo na prova</h2>
      <p>Não há desconto por erro: <b>nunca deixe questão em branco</b>. Mas, na TRI, acertar as fáceis vale mais que
        acertar difíceis no chute. Por isso o tempo deve ir primeiro para as questões que você sabe resolver.</p>

      <h3>Técnica das duas passadas</h3>
      <ol>
        <li><b>1ª passada:</b> resolva tudo o que for fácil ou médio. Travou por mais de 3 minutos? Marque a questão no
          caderno e siga em frente.</li>
        <li><b>2ª passada:</b> volte às marcadas com o tempo que sobrou.</li>
        <li><b>Chute consciente no final:</b> elimine as alternativas absurdas e escolha entre as restantes.</li>
      </ol>

      <h3>Plano sugerido: 1º dia (5h30 = 330 min)</h3>
      <div class="tabela"><table>
        <thead><tr><th>Bloco</th><th>Tempo</th></tr></thead>
        <tbody>
          <tr><td>Ler o tema da redação e anotar ideias (elas amadurecem enquanto você faz as questões)</td><td>10 min</td></tr>
          <tr><td>90 questões de Linguagens e Humanas (cerca de 2 min cada)</td><td>3h20</td></tr>
          <tr><td>Redação: planejar, rascunhar e passar a limpo</td><td>1h20</td></tr>
          <tr><td>Passar as respostas para o cartão (aos poucos, por blocos)</td><td>20 min</td></tr>
          <tr><td>Folga para imprevistos</td><td>20 min</td></tr>
        </tbody>
      </table></div>

      <h3>Plano sugerido: 2º dia (5h = 300 min)</h3>
      <p>Comece pela área em que você é mais forte: ganhar confiança cedo ajuda no resto da prova.</p>
      <div class="tabela"><table>
        <thead><tr><th>Bloco</th><th>Tempo</th></tr></thead>
        <tbody>
          <tr><td>Ciências da Natureza: 45 questões</td><td>2h</td></tr>
          <tr><td>Matemática: 45 questões (as contas pedem mais tempo)</td><td>2h20</td></tr>
          <tr><td>Cartão-resposta</td><td>20 min</td></tr>
          <tr><td>Folga</td><td>20 min</td></tr>
        </tbody>
      </table></div>
      <p><b>Cartão-resposta:</b> passe as respostas a cada bloco de 15 a 20 questões. Deixar tudo para os últimos
        15 minutos é a forma mais comum de perder pontos já conquistados. Treine esse ritmo nos simulados.</p>
    </section>

    <section class="cartao guia" id="guia-estudo">
      <h2>Como estudar: o modelo que funciona</h2>
      <p>As técnicas com mais evidência científica, aplicadas ao ENEM:</p>
      <ol>
        <li><b>Diagnóstico.</b> Faça questões de todas as áreas aqui no TRIunfo e veja no painel onde você está mais fraco.</li>
        <li><b>Ciclo de estudos em vez de horário fixo.</b> Monte uma lista das matérias com mais horas para as que pesam
          mais e para as que você domina menos. Estude na ordem da lista sempre que tiver tempo; perdeu um dia, continua
          de onde parou.</li>
        <li><b>Sessões de foco:</b> 50 minutos de estudo e 10 de pausa (ou 25 e 5), com o celular em outro cômodo.</li>
        <li><b>Mais questões, menos resumo:</b> cerca de 20% do tempo em teoria e 80% resolvendo questões. Testar-se fixa
          muito mais do que reler.</li>
        <li><b>Revise o que errou:</b> 1 dia, 7 dias e 30 dias depois. O <a href="#erros">caderno de erros</a> faz isso
          por você; marque sempre o motivo do erro.</li>
        <li><b>Misture as áreas.</b> A prova é misturada; treinar assim prepara melhor.</li>
        <li><b>Redação toda semana:</b> no mínimo uma, cronometrada (até 1h20), avaliada pelas 5 competências. Monte um
          repertório de dados, leis, filósofos e obras que sirva para vários temas.</li>
        <li><b>Simulados:</b> nos últimos 3 meses, um simulado completo a cada 2 semanas, aos domingos, das 13h30 em diante.
          Assim o corpo se acostuma ao horário real.</li>
        <li><b>Durma de 7 a 9 horas.</b> É no sono que a memória se consolida. Virar a noite antes da prova atrapalha.</li>
      </ol>
    </section>

    <section class="cartao guia" id="guia-vespera">
      <h2>Véspera e dia da prova</h2>
      <ul class="checklist">
        <li>Documento original com foto (e, se usar o digital, celular carregado só até a porta da sala)</li>
        <li>Cartão de Confirmação da Inscrição impresso: diz o prédio e a sala</li>
        <li>Duas canetas pretas de tubo transparente</li>
        <li>Lanche e água (serão vistoriados)</li>
        <li>Rota até o local testada, com folga para trânsito: chegue às 12h (horário de Brasília)</li>
        <li>Celular desligado e <b>sem alarme</b> antes de entrar na sala</li>
        <li>Na véspera: revisão leve, nada de matéria nova, e boa noite de sono</li>
      </ul>
    </section>`;

  // O índice rola dentro da página; sem isso, "#guia-regras" seria tratado como rota.
  $(".indice").onclick = (e) => {
    const a = e.target.closest("a");
    if (!a) return;
    e.preventDefault();
    $(a.getAttribute("href")).scrollIntoView();
  };
}

navegar();
