"use strict";
/* Rascunho com caneta (ADR 0023): uma camada transparente por cima da questão para riscar alternativas, sublinhar
   e fazer contas, como no caderno da prova. Funciona com caneta (Apple Pencil, caneta do Windows), dedo e mouse.

   - Quando aparece uma caneta, só ela desenha e o dedo rola a página. Sem caneta, dedo e mouse desenham.
   - Os traços são guardados em coordenadas relativas à largura: redesenham certo ao mudar o tamanho da tela.
   - Ficam na memória enquanto a página está aberta (no simulado, ao ir e voltar entre questões). Nada vai ao servidor.
*/
const Rascunho = (() => {
  const guardados = new Map(); // chave -> { tracos: [], historico: [] }
  let temCaneta = false;
  let ferramenta = "caneta";
  let aberto = false;
  let atual = null; // camada ligada agora

  const ESTILO = {
    caneta: { largura: 2.5, alfa: 1 },
    marca: { largura: 18, alfa: 0.35 },
  };

  function cor(tipo) {
    const css = getComputedStyle(document.documentElement);
    return tipo === "marca" ? "#facc15" : css.getPropertyValue("--primaria").trim() || "#1f4fb8";
  }

  // Barra fixa no canto da tela (uma só, reaproveitada entre as questões).
  function barra() {
    let b = document.getElementById("rascunho-barra");
    if (b) return b;
    b = document.createElement("div");
    b.id = "rascunho-barra";
    b.className = "rascunho-barra";
    b.setAttribute("role", "toolbar");
    b.setAttribute("aria-label", "Rascunho");
    b.innerHTML = `
      <div class="rascunho-ferramentas" hidden>
        <button type="button" data-f="caneta" aria-pressed="true" title="Caneta">✏️<span>Caneta</span></button>
        <button type="button" data-f="marca" aria-pressed="false" title="Marca-texto">🖍️<span>Marca-texto</span></button>
        <button type="button" data-f="borracha" aria-pressed="false" title="Borracha: apaga o traço que tocar">🧽<span>Borracha</span></button>
        <button type="button" data-a="desfazer" title="Desfazer">↶<span>Desfazer</span></button>
        <button type="button" data-a="limpar" title="Apagar todo o rascunho desta questão">🗑️<span>Limpar</span></button>
      </div>
      <button type="button" class="rascunho-abrir" aria-pressed="false" aria-expanded="false">✏️ Rascunho</button>`;
    document.body.append(b);
    b.onclick = (e) => {
      const botao = e.target.closest("button");
      if (!botao || !atual) return;
      if (botao.classList.contains("rascunho-abrir")) return alternar(!aberto);
      if (botao.dataset.f) {
        ferramenta = botao.dataset.f;
        b.querySelectorAll("[data-f]").forEach((x) => x.setAttribute("aria-pressed", x === botao));
      } else if (botao.dataset.a === "desfazer") atual.desfazer();
      else if (botao.dataset.a === "limpar") atual.limpar();
    };
    return b;
  }

  function alternar(abrir) {
    aberto = abrir;
    const b = barra();
    b.querySelector(".rascunho-ferramentas").hidden = !abrir;
    const botao = b.querySelector(".rascunho-abrir");
    botao.setAttribute("aria-pressed", abrir);
    botao.setAttribute("aria-expanded", abrir);
    botao.textContent = abrir ? "Fechar rascunho" : "✏️ Rascunho";
    atual?.ativar(abrir);
  }

  /* Liga o rascunho em `area` (posicionada), cobrindo do topo até o fim de `ate` (as alternativas), para os botões
     de confirmar continuarem clicáveis. Devolve a função que desliga. */
  function ligar(area, chave, ate) {
    atual?.desligar();
    const dados = guardados.get(chave) || { tracos: [], historico: [] };
    guardados.set(chave, dados);
    const canvas = document.createElement("canvas");
    canvas.className = "rascunho-camada";
    canvas.setAttribute("aria-hidden", "true");
    area.classList.add("rascunho-area");
    area.prepend(canvas);
    const ctx = canvas.getContext("2d");
    let largura = 1;

    function medir() {
      const fim = ate ? ate.offsetTop + ate.offsetHeight + 8 : area.scrollHeight;
      largura = area.clientWidth || 1;
      const dpr = window.devicePixelRatio || 1;
      canvas.style.width = largura + "px";
      canvas.style.height = fim + "px";
      canvas.width = Math.round(largura * dpr);
      canvas.height = Math.round(fim * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      desenhar();
    }

    function tracar(t) {
      const s = ESTILO[t.tipo];
      ctx.globalAlpha = s.alfa;
      ctx.strokeStyle = cor(t.tipo);
      ctx.lineWidth = s.largura * (t.tipo === "caneta" ? (t.pressao || 1) : 1);
      ctx.lineCap = ctx.lineJoin = "round";
      ctx.beginPath();
      t.pontos.forEach(([x, y], i) => (i ? ctx.lineTo(x * largura, y * largura) : ctx.moveTo(x * largura, y * largura)));
      if (t.pontos.length === 1) ctx.lineTo(t.pontos[0][0] * largura + 0.1, t.pontos[0][1] * largura);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    function desenhar() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      // marca-texto por baixo da caneta, como no papel
      dados.tracos.filter((t) => t.tipo === "marca").forEach(tracar);
      dados.tracos.filter((t) => t.tipo === "caneta").forEach(tracar);
    }

    const ponto = (e) => {
      const r = canvas.getBoundingClientRect();
      return [(e.clientX - r.left) / largura, (e.clientY - r.top) / largura];
    };

    function apagarEm([x, y]) {
      const raio = 12 / largura;
      const tocados = dados.tracos.filter((t) => t.pontos.some(([a, b]) => Math.hypot(a - x, b - y) < raio));
      if (!tocados.length) return;
      dados.tracos = dados.tracos.filter((t) => !tocados.includes(t));
      dados.historico.push({ apagou: tocados });
      desenhar();
    }

    let traco = null, rolando = null;
    canvas.addEventListener("pointerdown", (e) => {
      if (e.pointerType === "pen") temCaneta = true;
      if (e.pointerType === "touch" && temCaneta) { // com caneta, o dedo só rola
        rolando = e.clientY;
        return;
      }
      if (e.button > 0) return;
      e.preventDefault();
      try { canvas.setPointerCapture(e.pointerId); } catch {} // sem captura, o traço segue enquanto estiver sobre a camada
      if (ferramenta === "borracha") return apagarEm(ponto(e)), (traco = { borracha: true });
      traco = { tipo: ferramenta, pontos: [ponto(e)], pressao: e.pointerType === "pen" ? 0.6 + e.pressure : 1 };
      dados.tracos.push(traco);
      dados.historico.push({ fez: traco });
      desenhar();
    });
    canvas.addEventListener("pointermove", (e) => {
      if (rolando !== null) {
        window.scrollBy(0, rolando - e.clientY);
        rolando = e.clientY;
        return;
      }
      if (!traco) return;
      const eventos = e.getCoalescedEvents ? e.getCoalescedEvents() : [e];
      if (traco.borracha) return eventos.forEach((x) => apagarEm(ponto(x)));
      eventos.forEach((x) => traco.pontos.push(ponto(x)));
      desenhar();
    });
    const soltar = () => { traco = null; rolando = null; };
    canvas.addEventListener("pointerup", soltar);
    canvas.addEventListener("pointercancel", soltar);

    // Imagens que terminam de carregar e mudança de largura mudam a altura da questão.
    const observador = new ResizeObserver(medir);
    observador.observe(area);
    const tema = new MutationObserver(desenhar);
    tema.observe(document.documentElement, { attributes: true, attributeFilter: ["data-tema", "data-cor"] });

    const camada = {
      ativar(sim) {
        canvas.classList.toggle("ativa", sim);
      },
      desfazer() {
        const passo = dados.historico.pop();
        if (!passo) return;
        if (passo.fez) dados.tracos = dados.tracos.filter((t) => t !== passo.fez);
        else dados.tracos.push(...passo.apagou);
        desenhar();
      },
      limpar() {
        if (!dados.tracos.length) return;
        dados.historico.push({ apagou: dados.tracos });
        dados.tracos = [];
        desenhar();
      },
      desligar() {
        observador.disconnect();
        tema.disconnect();
        canvas.remove();
        area.classList.remove("rascunho-area");
        if (atual !== camada) return; // já existe outra camada ligada
        atual = null;
        barra().hidden = true;
      },
    };
    atual = camada;
    barra().hidden = false;
    medir();
    alternar(aberto); // mantém aberto ao passar para a próxima questão do simulado
    // Sair da tela fecha o rascunho; trocar de questão no simulado (nova chamada a ligar) o mantém aberto.
    return () => {
      const eraAtual = atual === camada;
      camada.desligar();
      if (eraAtual) alternar(false);
    };
  }

  return { ligar };
})();
