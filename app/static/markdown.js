// Conversor mínimo de Markdown -> HTML para os textos das questões.
// Escapa todo HTML antes, então o conteúdo nunca injeta código na página.
(function () {
  function escapar(s) {
    return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function urlSegura(u) {
    return u.startsWith("/imagens/") || u.startsWith("https://") ? u : null;
  }

  function inline(s) {
    s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (m, alt, url) => {
      if (url.includes("broken-image.svg")) return '<span class="img-faltando">[imagem indisponível na fonte]</span>';
      const u = urlSegura(url.replace(/&amp;/g, "&"));
      return u ? `<img src="${escapar(u)}" alt="${alt || "Imagem da questão"}" loading="lazy">` : "";
    });
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
    s = s.replace(/(^|\s)_([^_]+)_(?=\s|$|[.,;:!?])/g, "$1<em>$2</em>");
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

  window.markdown = function (texto) {
    if (!texto) return "";
    const blocos = escapar(texto.replace(/\r\n/g, "\n")).split(/\n{2,}/);
    return blocos
      .map((b) => {
        const linhas = b.split("\n").map((l) => l.replace(/\s+$/, ""));
        if (linhas.length >= 2 && /^\|.*\|$/.test(linhas[0]) && /^\|?[\s:-]+\|/.test(linhas[1])) return tabela(linhas);
        const h = b.match(/^(#{1,4})\s+(.*)$/);
        if (h && linhas.length === 1) return `<h4>${inline(h[2])}</h4>`;
        return "<p>" + linhas.map(inline).join("<br>") + "</p>";
      })
      .join("");
  };
})();
