/* Sentinela — conversor Markdown mínimo.
   Existe para o painel funcionar sem CDN nem dependência externa: cobre o
   subconjunto que a documentação do projeto usa (títulos, listas, tabelas,
   código, citação, ênfase, links).
   Autoria: Luiz Matheus Marassi de Paula */

const MD = (() => {

  const escapa = (t) => t
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  // Trechos de linha: código, negrito, itálico, link. Ordem importa.
  function inline(t) {
    return t
      .replace(/`([^`]+)`/g, (_, c) => `<code>${escapa(c)}</code>`)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
      .replace(/~~([^~]+)~~/g, "<del>$1</del>")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, txt, href) =>
        href.startsWith("http")
          ? `<a href="${href}" target="_blank" rel="noopener">${txt}</a>`
          : `<a href="#/documentos?doc=${encodeURIComponent(normaliza(href))}">${txt}</a>`);
  }

  // Links relativos entre documentos: docs/X.md, ../LOG.md, X.md
  function normaliza(href) {
    const limpo = href.split("#")[0].replace(/^\.\//, "");
    if (limpo.startsWith("docs/") || !limpo.includes("/")) {
      return limpo.includes("/") ? limpo
        : (["README.md", "LOG.md", "ERROS.md"].includes(limpo) ? limpo : "docs/" + limpo);
    }
    return limpo.replace(/^\.\.\//, "");
  }

  function tabela(linhas) {
    const celulas = (l) => l.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
    const cab = celulas(linhas[0]);
    const corpo = linhas.slice(2).map(celulas);
    const th = cab.map((c) => `<th>${inline(c)}</th>`).join("");
    const tr = corpo.map((linha) =>
      `<tr>${linha.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("");
    return `<div class="tabela-caixa"><table><thead><tr>${th}</tr></thead>`
         + `<tbody>${tr}</tbody></table></div>`;
  }

  const ehTabela = (linhas, i) =>
    linhas[i].startsWith("|") && (linhas[i + 1] || "").match(/^\|[\s\-:|]+\|$/);

  function bloco(estado, saida) {
    if (estado.lista.length) {
      const itens = estado.lista.map((t) => `<li>${inline(t)}</li>`).join("");
      saida.push(`<${estado.tipoLista}>${itens}</${estado.tipoLista}>`);
      estado.lista = [];
    }
    if (estado.paragrafo.length) {
      saida.push(`<p>${inline(estado.paragrafo.join(" "))}</p>`);
      estado.paragrafo = [];
    }
  }

  function render(md) {
    const linhas = md.replace(/\r/g, "").split("\n");
    const saida = [];
    const estado = { lista: [], tipoLista: "ul", paragrafo: [] };
    let i = 0;

    while (i < linhas.length) {
      const l = linhas[i];

      if (l.startsWith("```")) {
        bloco(estado, saida);
        const corpo = [];
        i++;
        while (i < linhas.length && !linhas[i].startsWith("```")) corpo.push(linhas[i++]);
        i++;
        saida.push(`<pre><code>${escapa(corpo.join("\n"))}</code></pre>`);
        continue;
      }

      if (ehTabela(linhas, i)) {
        bloco(estado, saida);
        const t = [];
        while (i < linhas.length && linhas[i].startsWith("|")) t.push(linhas[i++]);
        saida.push(tabela(t));
        continue;
      }

      const cab = l.match(/^(#{1,4})\s+(.*)$/);
      if (cab) {
        bloco(estado, saida);
        saida.push(`<h${cab[1].length}>${inline(cab[2])}</h${cab[1].length}>`);
        i++; continue;
      }

      if (l.startsWith(">")) {
        bloco(estado, saida);
        const cit = [];
        while (i < linhas.length && linhas[i].startsWith(">")) {
          cit.push(linhas[i].replace(/^>\s?/, "")); i++;
        }
        saida.push(`<blockquote>${inline(cit.join(" "))}</blockquote>`);
        continue;
      }

      if (/^(-{3,}|\*{3,})$/.test(l.trim())) {
        bloco(estado, saida); saida.push("<hr>"); i++; continue;
      }

      const item = l.match(/^\s*([-*+]|\d+\.)\s+(.*)$/);
      if (item) {
        const tipo = /\d/.test(item[1]) ? "ol" : "ul";
        if (estado.tipoLista !== tipo) { bloco(estado, saida); estado.tipoLista = tipo; }
        if (estado.paragrafo.length) bloco(estado, saida);
        estado.lista.push(item[2]);
        i++; continue;
      }

      if (!l.trim()) { bloco(estado, saida); i++; continue; }

      if (estado.lista.length) estado.lista[estado.lista.length - 1] += " " + l.trim();
      else estado.paragrafo.push(l.trim());
      i++;
    }

    bloco(estado, saida);
    return saida.join("\n");
  }

  return { render };
})();
