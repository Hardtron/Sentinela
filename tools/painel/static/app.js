/* Sentinela — painel de controle.
   Roteamento por hash, uma função de render por rota. Cada render recebe dados
   já prontos do servidor e só monta HTML — mantém a complexidade baixa e o
   estado fora da view.
   Autoria: Matheus Marassi */

const api = async (rota) => {
  const r = await fetch(rota);
  if (!r.ok) throw new Error(`${rota}: ${r.status}`);
  return r.json();
};

const el = (id) => document.getElementById(id);
const esc = (t) => String(t ?? "").replace(/[<>&]/g, (c) =>
  ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));

const cache = {};
async function dados(rota) {
  if (!cache[rota]) cache[rota] = api(rota);
  return cache[rota];
}

/* ------------------------------------------------------------ componentes */

const metrica = (rot, val, sub = "", classe = "") => `
  <div class="cartao metrica">
    <div class="rot">${rot}</div>
    <div class="val ${classe}">${val}</div>
    ${sub ? `<div class="sub">${sub}</div>` : ""}
  </div>`;

const cabecalho = (titulo, desc) => `
  <div class="pagina-cab"><h1>${titulo}</h1><p>${desc}</p></div>`;

const secao = (t) => `<h2 class="secao">${t}</h2>`;

function tabela(colunas, linhas) {
  if (!linhas.length) return `<div class="vazio">sem registros</div>`;
  const th = colunas.map((c) => `<th>${c.rot}</th>`).join("");
  const tr = linhas.map((l) =>
    `<tr>${colunas.map((c) => {
      const v = c.val(l);
      return `<td class="${c.classe || ""}">${v}</td>`;
    }).join("")}</tr>`).join("");
  return `<div class="tabela-caixa"><table>
    <thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></div>`;
}

const CORES_VEREDITO = { APROVADO: "ok", LIMITE: "atencao", REPROVADO: "erro" };
const tagVeredito = (v) =>
  `<span class="tag ${CORES_VEREDITO[v] || "neutro"}">${v}</span>`;

const CORES_CC = { simples: "ok", moderada: "atencao", complexa: "erro", critica: "erro" };

/* --------------------------------------------------------------- gráficos */

function grafDispersao(pontos, opc) {
  const L = 52, D = 16, T = 16, B = 34, larg = 720, alt = 300;
  const xs = pontos.map(opc.x), ys = pontos.map(opc.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const y0 = Math.min(...ys), y1 = Math.max(...ys);
  const px = (v) => L + ((v - x0) / (x1 - x0 || 1)) * (larg - L - D);
  const py = (v) => T + (1 - (v - y0) / (y1 - y0 || 1)) * (alt - T - B);

  const grade = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const v = y0 + f * (y1 - y0), y = py(v);
    return `<line class="grade-l" x1="${L}" y1="${y}" x2="${larg - D}" y2="${y}"/>
            <text x="${L - 7}" y="${y + 3}" text-anchor="end">${v.toFixed(0)}</text>`;
  }).join("");

  // Pontos próximos em x teriam os rótulos sobrepostos: alterna acima/abaixo.
  const ocupados = [];
  const marcas = pontos.map((p) => {
    const cx = px(opc.x(p)), cy = py(opc.y(p));
    const colide = ocupados.some((o) => Math.abs(o.cx - cx) < 26 && Math.abs(o.cy - cy) < 18);
    ocupados.push({ cx, cy });
    const dy = colide ? 19 : -10;
    return `<circle cx="${cx}" cy="${cy}" r="5"
              fill="var(--${opc.cor(p)})" fill-opacity=".9"/>
            <text class="rotulo-pt" x="${cx}" y="${cy + dy}"
              text-anchor="middle">${opc.rot(p)}</text>`;
  }).join("");

  const marcasX = [x0, (x0 + x1) / 2, x1].map((v) =>
    `<text x="${px(v)}" y="${alt - 12}" text-anchor="middle">${v.toFixed(0)}</text>`).join("");

  return `<svg class="grafico" viewBox="0 0 ${larg} ${alt}" role="img"
    aria-label="${opc.aria}">
    ${grade}
    <line class="eixo" x1="${L}" y1="${alt - B}" x2="${larg - D}" y2="${alt - B}"/>
    <line class="eixo" x1="${L}" y1="${T}" x2="${L}" y2="${alt - B}"/>
    ${marcas}${marcasX}
    <text x="${larg / 2}" y="${alt - 1}" text-anchor="middle">${opc.eixoX}</text>
  </svg>`;
}

function grafBarras(itens) {
  const total = itens.reduce((s, i) => s + i.valor, 0) || 1;
  return itens.map((i) => `
    <div style="margin-bottom:11px">
      <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:4px">
        <span>${i.rot}</span>
        <span style="font-family:var(--mono);color:var(--texto-3)">${i.valor}</span>
      </div>
      <div class="barra-fina">
        <i style="width:${(i.valor / total * 100).toFixed(1)}%;
           background:var(--${i.cor || "acento"})"></i>
      </div>
    </div>`).join("");
}

/* ----------------------------------------------------------------- rotas */

const rotas = {};

rotas["visao-geral"] = async () => {
  const [v, g] = await Promise.all([dados("/api/visao-geral"), dados("/api/git")]);
  const m = v.modelo;
  const ccClasse = v.cc_maxima > v.cc_limite ? "erro" : "ok";

  return cabecalho("Visão geral", `Estado do projeto em ${v.gerado_em.replace("T", " ")}.`)
    + `<div class="grade g4">
      ${metrica("Fase", v.fase.split("—")[0].trim(), v.fase.split("—")[1] || "")}
      ${metrica("Pendências abertas", v.pendencias_abertas,
        `de ${v.pendencias_total} registradas`,
        v.pendencias_abertas > 8 ? "atencao" : "")}
      ${metrica("Complexidade máx.", v.cc_maxima,
        `limite ${v.cc_limite} · média ${v.cc_media}`, ccClasse)}
      ${metrica("Documentação", v.linhas_doc.toLocaleString("pt-BR"),
        `${v.documentos} documentos`)}
    </div>`
    + secao("Modelo de propagação medido")
    + `<div class="grade g4">
      ${metrica("Expoente n", m.expoente_n, `RMS ${m.rms_db} dB`, "ok")}
      ${metrica("Ganho por altura", "+" + m.ganho_altura_db + " dB",
        "validado por dois raios")}
      ${metrica("Perda fixa", m.perda_fixa_db + " dB", "confinamento do nó fixo",
        "atencao")}
      ${metrica("Literatura", m.referencia_literatura.floresta_tropical,
        "floresta tropical, 923 MHz")}
    </div>
    <p class="nota">O expoente medido (3,28) é praticamente idêntico ao publicado
    para floresta tropical (3,22) — alvenaria esparsa e mata atenuam de forma
    comparável.</p>`
    + secao("Atividade recente")
    + `<div class="cartao"><div class="linha-tempo">
      ${g.commits.slice(0, 6).map((c) => `
        <div class="evento">
          <div class="quando">${c.data}</div>
          <div class="oque">${esc(c.assunto)}</div>
        </div>`).join("")}
    </div></div>`;
};

rotas["pendencias"] = async () => {
  const p = await dados("/api/pendencias");
  const abertas = p.filter((i) => !i.resolvida);
  const grupos = [...new Set(p.map((i) => i.grupo))];

  return cabecalho("Pendências",
    "Consolidado de todos os documentos. Itens resolvidos ficam registrados para rastreabilidade.")
    + `<div class="filtros">
        <button class="filtro ativo" data-f="abertas">Abertas (${abertas.length})</button>
        <button class="filtro" data-f="todas">Todas (${p.length})</button>
        ${grupos.map((g) => `<button class="filtro" data-f="${g}">${g}</button>`).join("")}
      </div><div id="lista-pend"></div>`;
};

function renderPendencias(itens) {
  el("lista-pend").innerHTML = tabela([
    { rot: "ID", val: (i) => `<span class="tag ${i.resolvida ? "neutro" : "acento"}">${i.id}</span>` },
    { rot: "Descrição", val: (i) => esc(i.descricao), classe: "livre" },
    { rot: "Situação", val: (i) => esc(i.situacao), classe: "livre" },
    { rot: "Origem", val: (i) => `<code>${i.origem.replace("docs/", "")}</code>` },
  ], itens);
}

rotas["timeline"] = async () => {
  const g = await dados("/api/git");
  return cabecalho("Linha do tempo",
    `Histórico do repositório — branch <code>${g.branch}</code>.`)
    + `<div class="cartao"><div class="linha-tempo">
      ${g.commits.map((c) => `
        <div class="evento">
          <div class="quando">${c.data} · <span class="hash">${c.hash}</span></div>
          <div class="oque">${esc(c.assunto)}</div>
        </div>`).join("")}
    </div></div>`;
};

rotas["hardware"] = async () => {
  const h = await dados("/api/hardware");
  const r = h.radio;
  return cabecalho("Hardware",
    "Inventário das placas e configuração de rádio em uso.")
    + `<div class="grade g4">
      ${metrica("Frequência", r.frequencia_mhz, "MHz · AU915 sub-banda 2")}
      ${metrica("Spreading factor", "SF" + r.sf, `${r.bw_khz} kHz · CR ${r.cr}`)}
      ${metrica("Potência", r.potencia_dbm + " dBm", `tempo no ar ${r.toa_ms} ms`)}
      ${metrica("Sensibilidade", r.sensibilidade_dbm, "dBm para o SF em uso")}
    </div>`
    + secao("Placas")
    + tabela([
      { rot: "ID", val: (p) => `<strong>${p.id}</strong>` },
      { rot: "Papel", val: (p) => p.papel },
      { rot: "Ambiente", val: (p) => `<code>${p.env}</code>` },
      { rot: "MAC", val: (p) => p.mac ? `<code>${p.mac}</code>`
        : `<span class="tag neutro">não gravada</span>` },
      { rot: "Flash", val: (p) => p.flash, classe: "num" },
    ], h.placas)
    + secao("Portas seriais")
    + (h.portas.length
      ? tabela([{ rot: "Porta", val: (p) => `<code>${p.porta}</code>` },
                { rot: "Estado", val: () => `<span class="tag ok">conectada</span>` }],
               h.portas)
      : `<div class="vazio">nenhuma placa conectada à USB</div>`)
    + `<p class="nota">Os CP2102 destas placas compartilham o mesmo número de série
       USB — só o MAC do ESP32 identifica qual está na porta.</p>`;
};

rotas["rede"] = async () => {
  const [e, v] = await Promise.all([dados("/api/ensaios"), dados("/api/visao-geral")]);
  const pts = e.pontos.filter((p) => p.distancia_m != null);
  if (!pts.length) return cabecalho("Rede LoRa", "Sem dados de ensaio.");

  const m = v.modelo;
  const aprovados = pts.filter((p) => p.veredito === "APROVADO").length;

  return cabecalho("Rede LoRa",
    "Ensaio 02 — percurso urbano noturno sob sereno e chuva fina, 7 pontos.")
    + `<div class="grade g4">
      ${metrica("Pontos medidos", pts.length, `${aprovados} aprovados`)}
      ${metrica("Alcance máximo",
        Math.max(...pts.map((p) => p.distancia_m)).toFixed(0) + "<small>m</small>",
        "com enlace fechado")}
      ${metrica("Modelo", "n = " + m.expoente_n, `RMS ${m.rms_db} dB`, "ok")}
      ${metrica("Ganho de altura", "+" + m.ganho_altura_db + " dB", "por 11 m de elevação", "ok")}
    </div>`
    + secao("RSSI por distância")
    + `<div class="cartao">${grafDispersao(pts, {
        x: (p) => p.distancia_m, y: (p) => p.rssi_med,
        cor: (p) => CORES_VEREDITO[p.veredito] || "neutro",
        rot: (p) => "P" + p.ponto,
        eixoX: "distância ao nó fixo (m)", aria: "RSSI por distância",
      })}
      <div class="legenda">
        <span><i class="pt" style="background:var(--ok)"></i>aprovado</span>
        <span><i class="pt" style="background:var(--atencao)"></i>limite</span>
        <span><i class="pt" style="background:var(--erro)"></i>reprovado</span>
      </div>
      <p class="nota">P5 e P6 estão mais distantes e ainda assim acima da curva:
      são os pontos elevados (17 m). A altura compensou a distância.</p>
    </div>`
    + secao("Pontos do ensaio")
    + tabela([
      { rot: "Ponto", val: (p) => `<strong>P${p.ponto}</strong>` },
      { rot: "Dist.", val: (p) => p.distancia_m.toFixed(0) + " m", classe: "num" },
      { rot: "Alt.", val: (p) => (p.altitude_m ?? "—") + " m", classe: "num" },
      { rot: "RSSI", val: (p) => p.rssi_med + " dBm", classe: "num" },
      { rot: "Margem", val: (p) => p.margem_db + " dB", classe: "num" },
      { rot: "Perda", val: (p) => p.perda_pct + "%", classe: "num" },
      { rot: "Veredito", val: (p) => tagVeredito(p.veredito) },
      { rot: "Ambiente", val: (p) => esc(p.ambiente || ""), classe: "livre" },
    ], pts);
};

const CORES_SEV = { CRITICO: "erro", URGENTE: "atencao", ATENCAO: "acento", INFO: "neutro" };

rotas["frota"] = async () => {
  const f = await dados("/api/frota");
  const sev = f.por_severidade;
  const grupos = [...new Set(f.alarmes.map((a) => a.grupo))];

  return cabecalho("Frota e alarmes",
    `Saúde das <strong>Atalaias</strong> em campo. Nenhuma operando ainda —
     o catálogo existe para ser revisado antes da implantação.`)
    + `<div class="grade g4">
      ${metrica("Atalaias operando", f.operando, `${f.previstos} previstas`)}
      ${metrica("Alarmes críticos", sev.CRITICO || 0, "lacuna de cobertura", "erro")}
      ${metrica("Alarmes urgentes", sev.URGENTE || 0, "dias de margem", "atencao")}
      ${metrica("Alarmes de atenção", sev.ATENCAO || 0, "semanas de margem")}
    </div>
    <p class="nota"><strong>Atalaia fora do ar é talude sem monitoramento</strong>
    — lacuna de cobertura num sistema de alerta, não indisponibilidade de
    serviço. É isso que põe o silêncio como CRÍTICO.</p>`

    + secao("Assinaturas de energia — o que a curva de carga revela")
    + tabela([
      { rot: "Padrão observado", val: (a) => esc(a.padrao), classe: "livre" },
      { rot: "Diagnóstico provável", val: (a) => `<strong>${esc(a.diagnostico)}</strong>`, classe: "livre" },
      { rot: "Ação", val: (a) => esc(a.acao) },
    ], f.assinaturas)
    + `<p class="nota">Sujeira reduz a captação de forma uniforme ao longo do dia;
       sombra atua em janela horária específica. É a <em>forma</em> da curva que
       separa as duas — por isso a janela de carga é registrada junto com a
       energia. A comparação é feita contra a mediana das Atalaias vizinhas, o
       que elimina a variável climática sem sensor de referência.</p>`

    + secao("Catálogo de alarmes")
    + `<div class="filtros">
        <button class="filtro ativo" data-g="todos">Todos (${f.alarmes.length})</button>
        ${grupos.map((g) => `<button class="filtro" data-g="${g}">${g}</button>`).join("")}
      </div><div id="lista-alarmes"></div>`

    + secao("Composição do índice de saúde")
    + `<div class="cartao">${grafBarras(f.pesos_saude.map((p) => ({
        rot: `${p.componente} — ${p.entra_com}`, valor: p.peso })))}
      <p class="nota">Faixas: 90–100 saudável · 70–89 observar · 50–69 agendar ·
      abaixo de 50 intervir. <strong>Qualquer alarme crítico zera o índice</strong>
      — Atalaia muda com bateria cheia não é 70% saudável, é inútil.</p>
    </div>`;
};

function renderAlarmes(itens) {
  el("lista-alarmes").innerHTML = tabela([
    { rot: "Severidade", val: (a) =>
      `<span class="tag ${CORES_SEV[a.severidade]}">${a.severidade}</span>` },
    { rot: "Alarme", val: (a) => `<strong>${esc(a.nome)}</strong>` },
    { rot: "Gatilho", val: (a) => esc(a.gatilho), classe: "livre" },
    { rot: "Ação de manutenção", val: (a) => esc(a.acao), classe: "livre" },
  ], itens);
}

rotas["firmware"] = async () => {
  const [f, c] = await Promise.all([dados("/api/firmware"), dados("/api/complexidade")]);
  const arqs = c.arquivos.filter((a) => a.arquivo.startsWith("firmware/"));
  const funcs = arqs.flatMap((a) => a.funcoes.map((fn) => ({ ...fn, arquivo: a.arquivo })));
  const maxima = Math.max(0, ...funcs.map((fn) => fn.complexidade));

  return cabecalho("Firmware",
    "Builds do PlatformIO e complexidade das funções embarcadas.")
    + `<div class="grade g3">
      ${metrica("Ambientes", f.ambientes.filter((a) => a.compilado).length + "/" + f.ambientes.length,
        "compilados")}
      ${metrica("Funções", funcs.length, "no firmware")}
      ${metrica("Complexidade máx.", maxima, `limite ${c.limite}`,
        maxima > c.limite ? "erro" : "ok")}
    </div>`
    + secao("Builds")
    + tabela([
      { rot: "Ambiente", val: (a) => `<code>${a.env}</code>` },
      { rot: "Estado", val: (a) => a.compilado
        ? `<span class="tag ok">compilado</span>`
        : `<span class="tag neutro">não compilado</span>` },
      { rot: "Tamanho", val: (a) => a.bytes ? (a.bytes / 1024).toFixed(0) + " KB" : "—", classe: "num" },
      { rot: "Gerado em", val: (a) => a.modificado ? a.modificado.replace("T", " ") : "—" },
    ], f.ambientes)
    + secao("Funções por complexidade")
    + tabela([
      { rot: "Arquivo", val: (fn) => `<code>${fn.arquivo.replace("firmware/", "")}</code>` },
      { rot: "Função", val: (fn) => fn.nome },
      { rot: "Linha", val: (fn) => fn.linha, classe: "num" },
      { rot: "CC", val: (fn) => fn.complexidade, classe: "num" },
      { rot: "Faixa", val: (fn) => `<span class="tag ${CORES_CC[fn.rotulo]}">${fn.rotulo}</span>` },
    ], funcs.sort((a, b) => b.complexidade - a.complexidade));
};

rotas["qualidade"] = async () => {
  const c = await dados("/api/complexidade");
  const r = c.resumo;
  const dist = r.distribuicao || {};
  const acima = (r.piores || []).filter((f) => f.complexidade > c.limite);

  return cabecalho("Qualidade de código",
    `Complexidade ciclomática (McCabe) — limite adotado pelo projeto: ${c.limite}.`)
    + `<div class="grade g4">
      ${metrica("Funções", r.funcoes, `em ${r.arquivos} arquivos`)}
      ${metrica("Média", r.media, "caminhos por função", "ok")}
      ${metrica("Máxima", r.maxima, `limite ${c.limite}`,
        r.maxima > c.limite ? "erro" : "ok")}
      ${metrica("Acima do limite", acima.length,
        acima.length ? "refatorar" : "nenhuma", acima.length ? "erro" : "ok")}
    </div>`
    + secao("Distribuição")
    + `<div class="cartao">${grafBarras(
      Object.entries(dist).map(([k, v]) => ({ rot: k, valor: v, cor: CORES_CC[k] })))}
      <p class="nota">Faixas de McCabe: até 10 simples, até 20 moderada,
      até 50 complexa, acima disso crítica.</p></div>`
    + secao("Dez funções mais complexas")
    + tabela([
      { rot: "Função", val: (f) => f.nome },
      { rot: "Linha", val: (f) => f.linha, classe: "num" },
      { rot: "CC", val: (f) => f.complexidade, classe: "num" },
      { rot: "Faixa", val: (f) => `<span class="tag ${CORES_CC[f.rotulo]}">${f.rotulo}</span>` },
    ], r.piores || [])
    + secao("Por arquivo")
    + tabela([
      { rot: "Arquivo", val: (a) => `<code>${a.arquivo}</code>` },
      { rot: "Linguagem", val: (a) => a.linguagem },
      { rot: "Funções", val: (a) => a.total_funcoes, classe: "num" },
      { rot: "Máxima", val: (a) => a.maxima, classe: "num" },
    ], c.arquivos);
};

rotas["documentos"] = async () => {
  const d = await dados("/api/documentos");
  return cabecalho("Documentos", "Documentação do projeto, renderizada.")
    + `<div class="doc-layout">
      <div class="doc-lista" id="doc-lista">
        ${d.map((doc) => `<button data-doc="${doc.arquivo}">${doc.nome}</button>`).join("")}
      </div>
      <div class="md" id="doc-conteudo"><div class="carregando">selecione um documento</div></div>
    </div>`;
};

async function abreDocumento(caminho) {
  document.querySelectorAll("#doc-lista button").forEach((b) =>
    b.classList.toggle("ativo", b.dataset.doc === caminho));
  const alvo = el("doc-conteudo");
  alvo.innerHTML = `<div class="carregando">carregando…</div>`;
  try {
    const r = await api(`/api/documento?path=${encodeURIComponent(caminho)}`);
    alvo.innerHTML = MD.render(r.conteudo);
    alvo.scrollIntoView({ block: "start", behavior: "smooth" });
  } catch {
    alvo.innerHTML = `<div class="vazio">não foi possível abrir ${esc(caminho)}</div>`;
  }
}

rotas["referencias"] = async () => {
  const d = await dados("/api/documentos");
  const total = {};
  d.forEach((doc) => Object.entries(doc.marcas).forEach(([k, v]) =>
    total[k] = (total[k] || 0) + v));

  const NOMES = {
    M: "Medido em ensaio próprio", N: "Norma técnica",
    L: "Literatura revisada", G: "Fonte governamental",
    E: "Estimativa própria", "?": "Pendente de referência",
  };
  const CORES = { M: "ok", N: "acento", L: "acento", G: "acento", E: "atencao", "?": "erro" };

  return cabecalho("Referências e proveniência",
    "Toda afirmação técnica carrega a origem. Marcações contadas na documentação.")
    + `<div class="grade g3">
      ${Object.entries(NOMES).map(([k, nome]) =>
        metrica(`[${k}] ${nome}`, total[k] || 0, "", CORES[k] === "erro" && total[k] ? "erro" : "")
      ).join("")}
    </div>`
    + secao("Marcações por documento")
    + tabela([
      { rot: "Documento", val: (doc) => `<a href="#/documentos?doc=${encodeURIComponent(doc.arquivo)}">${doc.nome}</a>` },
      { rot: "Título", val: (doc) => esc(doc.titulo), classe: "livre" },
      { rot: "Linhas", val: (doc) => doc.linhas, classe: "num" },
      { rot: "Marcas", val: (doc) => Object.entries(doc.marcas).map(([k, v]) =>
          `<span class="tag ${CORES[k] || "neutro"}">${k}·${v}</span>`).join(" ") || "—" },
    ], d)
    + `<p class="nota">A política completa está em
       <a href="#/documentos?doc=docs%2FREFERENCIAS.md">REFERENCIAS.md</a>.
       Afirmação de domínio geológico, geotécnico ou geográfico nunca recebe [E].</p>`;
};

/* -------------------------------------------------------------- roteador */

function partesDaRota() {
  const bruto = location.hash.replace(/^#\/?/, "") || "visao-geral";
  const [nome, query] = bruto.split("?");
  return { nome: nome || "visao-geral", params: new URLSearchParams(query || "") };
}

async function navega() {
  const { nome, params } = partesDaRota();
  const render = rotas[nome] || rotas["visao-geral"];

  document.querySelectorAll("nav a").forEach((a) =>
    a.classList.toggle("ativo", a.dataset.rota === nome));

  const alvo = el("rota");
  alvo.innerHTML = `<div class="carregando">carregando…</div>`;
  window.scrollTo({ top: 0 });
  try {
    alvo.innerHTML = await render();
  } catch (e) {
    alvo.innerHTML = `<div class="vazio">falha ao carregar: ${esc(e.message)}</div>`;
    return;
  }
  await depoisDeRenderizar(nome, params);
}

async function depoisDeRenderizar(nome, params) {
  if (nome === "pendencias") return ligaPendencias();
  if (nome === "documentos") return ligaDocumentos(params);
  if (nome === "frota") return ligaFrota();
}

async function ligaFrota() {
  const f = await dados("/api/frota");
  const aplica = (g) => renderAlarmes(
    g === "todos" ? f.alarmes : f.alarmes.filter((a) => a.grupo === g));
  aplica("todos");
  document.querySelectorAll(".filtro").forEach((b) => b.onclick = () => {
    document.querySelectorAll(".filtro").forEach((x) => x.classList.remove("ativo"));
    b.classList.add("ativo");
    aplica(b.dataset.g);
  });
}

async function ligaPendencias() {
  const p = await dados("/api/pendencias");
  const aplica = (f) => renderPendencias(
    f === "todas" ? p : f === "abertas" ? p.filter((i) => !i.resolvida)
      : p.filter((i) => i.grupo === f));
  aplica("abertas");
  document.querySelectorAll(".filtro").forEach((b) => b.onclick = () => {
    document.querySelectorAll(".filtro").forEach((x) => x.classList.remove("ativo"));
    b.classList.add("ativo");
    aplica(b.dataset.f);
  });
}

function ligaDocumentos(params) {
  document.querySelectorAll("#doc-lista button").forEach((b) =>
    b.onclick = () => abreDocumento(b.dataset.doc));
  const inicial = params.get("doc") || "README.md";
  abreDocumento(inicial);
}

/* --------------------------------------------------------------- selos */

async function atualizaSelos() {
  try {
    const [v, g] = await Promise.all([dados("/api/visao-geral"), dados("/api/git")]);
    const sp = el("selo-pend");
    sp.textContent = v.pendencias_abertas;
    sp.className = "selo " + (v.pendencias_abertas > 8 ? "alerta" : "");
    const sc = el("selo-cc");
    sc.textContent = v.cc_maxima;
    sc.className = "selo " + (v.cc_maxima > v.cc_limite ? "alerta" : "bom");
    el("estado-git").textContent = `${g.branch}${g.sujo ? " ·" : ""}`;
  } catch { /* painel funciona sem os selos */ }
}

/* ---------------------------------------------------------------- tema */

function iniciaTema() {
  const salvo = localStorage.getItem("sentinela-tema");
  if (salvo) document.documentElement.dataset.tema = salvo;
  el("alternar-tema").onclick = () => {
    const novo = document.documentElement.dataset.tema === "escuro" ? "claro" : "escuro";
    document.documentElement.dataset.tema = novo;
    localStorage.setItem("sentinela-tema", novo);
  };
}

window.addEventListener("hashchange", navega);
iniciaTema();
navega();
atualizaSelos();
