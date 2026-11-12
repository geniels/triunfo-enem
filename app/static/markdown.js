// Conversor mínimo de Markdown -> HTML para os textos das questões.
// Escapa todo HTML antes, então o conteúdo nunca injeta código na página.
(function () {
  function escapar(s) {
    return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // Imagens e links viram marcadores (\u0000n\u0000) antes das outras trocas e só voltam como HTML no fim:
  // nenhuma regra roda sobre HTML já montado (antes, imagem e link aninhados escapavam do atributo alt).
  let dims = {}; // {"/imagens/x.png": [largura, altura]} da questão: reserva o espaço antes da imagem chegar
  const tamanho = (url) => (dims[url] ? ` width="${dims[url][0]}" height="${dims[url][1]}"` : "");

  function inline(s) {
    const guardados = [];
    const guardar = (html) => `\u0000${guardados.push(html) - 1}\u0000`;
    s = s.replace(/!\[([^\[\]]*)\]\(([^()\s]+)\)/g, (m, alt, url) => {
      // Só imagens locais: o TRIunfo funciona offline e não busca nada fora (ADR 0002).
      if (!url.startsWith("/imagens/")) return guardar('<span class="img-faltando">[imagem indisponível na fonte]</span>');
      const u = url.replace(/&amp;/g, "&");
      return guardar(`<img src="${escapar(u)}"${tamanho(u)} alt="${alt || "Imagem da questão"}" loading="lazy">`);
    });
    // Links só para https:// ou âncoras internas (#rota): nada de javascript: vindo de conteúdo baixado.
    s = s.replace(/\[([^\[\]]+)\]\((https:\/\/[^()\s]+|#[\w-]+)\)/g, (m, t, url) =>
      guardar(`<a href="${url}"${url.startsWith("#") ? "" : ' target="_blank" rel="noopener"'}>${t}</a>`));
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
    s = s.replace(/(^|\s)_([^_]+)_(?=\s|$|[.,;:!?])/g, "$1<em>$2</em>");
    // Um link pode conter uma imagem: devolve em até duas passadas.
    for (let i = 0; i < 2; i++) s = s.replace(/\u0000(\d+)\u0000/g, (m, n) => guardados[n]);
    return s;
  }

  function tabela(linhas) {
    const celulas = (l) => l.replace(/^\||\|$/g, "").split("|").map((c) => inline(c.trim()));
    const [cab, , ...corpo] = linhas;
    return (
      '<div class="tabela"><table><thead><tr>' +
      celulas(cab).map((c) => `<th>${c}</th>`).join("") +
      "</tr></thead><tbody>" +
      corpo.map((l) => "<tr>" + celulas(l).map((c) => `<td>${c}</td>`).join("") + "</tr>").join("") +
      "</tbody></table></div>"
    );
  }

  window.markdown = function (texto, dimensoes) {
    if (!texto) return "";
    dims = dimensoes || {};
    const blocos = escapar(texto.replace(/\r\n/g, "\n")).split(/\n{2,}/);
    return blocos
      .map((b) => {
        const linhas = b.split("\n").map((l) => l.replace(/\s+$/, ""));
        if (linhas.length >= 2 && /^\|.*\|$/.test(linhas[0]) && /^\|?[\s:-]+\|/.test(linhas[1])) return tabela(linhas);
        const h = b.match(/^(#{1,4})\s+(.*)$/);
        if (h && linhas.length === 1) return h[1] === "###" ? `<h3>${inline(h[2])}</h3>` : `<h4>${inline(h[2])}</h4>`;
        if (linhas.every((l) => /^- /.test(l))) return "<ul>" + linhas.map((l) => `<li>${inline(l.slice(2))}</li>`).join("") + "</ul>";
        if (linhas.every((l) => /^\d+\. /.test(l)))
          return "<ol>" + linhas.map((l) => `<li>${inline(l.replace(/^\d+\. /, ""))}</li>`).join("") + "</ol>";
        return "<p>" + linhas.map(inline).join("<br>") + "</p>";
      })
      .join("");
  };
})();
