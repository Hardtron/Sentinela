/* Sentinela — central de operações.
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

const legendaSeries = (series) => `<div class="legenda">${series.map((s) =>
  `<span><i class="pt" style="background:var(--${s.cor})"></i>${s.rot}</span>`)
  .join("")}</div>`;

/* Série temporal com várias curvas. Usada no monitoramento: o eixo x é a
   ordem das amostras (mais recente à direita), não o relógio — o intervalo
   entre pacotes é regular o bastante para isso e evita buracos visuais quando
   um ping se perde. */
function grafLinhas(serie, opc) {
  const L = 54, D = 14, T = 14, B = 28, larg = 760, alt = 230;
  const vals = serie.flatMap((p) => opc.series.map((s) => p[s.chave]))
    .filter((v) => v != null);
  if (!vals.length) return `<div class="vazio">sem amostras ainda</div>`;

  const refs = (opc.refs || []).map((r) => r.v);
  let y0 = Math.min(...vals, ...refs), y1 = Math.max(...vals, ...refs);
  const folga = (y1 - y0) * 0.12 || 1;
  y0 -= folga; y1 += folga;

  const px = (i) => L + (serie.length < 2 ? 0.5 : i / (serie.length - 1)) * (larg - L - D);
  const py = (v) => T + (1 - (v - y0) / (y1 - y0 || 1)) * (alt - T - B);

  const grade = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const v = y0 + f * (y1 - y0), y = py(v);
    return `<line class="grade-l" x1="${L}" y1="${y}" x2="${larg - D}" y2="${y}"/>
            <text x="${L - 7}" y="${y + 3}" text-anchor="end">${v.toFixed(0)}</text>`;
  }).join("");

  const ref = (r) => `
    <line class="ref" x1="${L}" y1="${py(r.v)}" x2="${larg - D}" y2="${py(r.v)}"
      style="stroke:var(--${r.cor})"/>
    <text x="${larg - D - 3}" y="${py(r.v) - 4}" text-anchor="end"
      style="fill:var(--${r.cor})">${r.rot}</text>`;

  const caminho = (chave) => {
    let d = "", ligado = false;
    serie.forEach((p, i) => {
      const v = p[chave];
      if (v == null) { ligado = false; return; }
      d += `${ligado ? "L" : "M"}${px(i).toFixed(1)} ${py(v).toFixed(1)} `;
      ligado = true;
    });
    return d;
  };

  return `<svg class="grafico" viewBox="0 0 ${larg} ${alt}" role="img"
    aria-label="${opc.aria}">
    ${grade}${(opc.refs || []).map(ref).join("")}
    <line class="eixo" x1="${L}" y1="${alt - B}" x2="${larg - D}" y2="${alt - B}"/>
    <line class="eixo" x1="${L}" y1="${T}" x2="${L}" y2="${alt - B}"/>
    ${opc.series.map((s) =>
      `<path class="serie" d="${caminho(s.chave)}" style="stroke:var(--${s.cor})"/>`).join("")}
    <text x="${larg / 2}" y="${alt - 7}" text-anchor="middle">${opc.eixoX
      || "amostras — mais recentes à direita"}</text>
  </svg>` + legendaSeries(opc.series);
}

/* Tira de perdas: uma haste por amostra, alta quando houve buraco de
   sequência. Densidade importa mais que valor exato — o que se procura é
   se as perdas são isoladas ou em rajada. */
function grafPerdas(serie) {
  const max = Math.max(1, ...serie.map((p) => p.perdidos || 0));
  return `<div class="tiras">${serie.map((p) => {
    const v = p.perdidos || 0;
    const h = v ? Math.max(18, (v / max) * 100) : 5;
    return `<i class="${v ? "perda" : ""}" style="height:${h}%"
      title="seq ${p.seq}: ${v} perdido(s)"></i>`;
  }).join("")}</div>`;
}

/* ----------------------------------------------------------------- rotas */

/* T-32: Helper de tooltip contextual. Renderiza um ⓘ com texto de ajuda. */
const dica = (texto) => `<span class="dica">
  <span class="dica-icone">ⓘ</span>
  <span class="dica-conteudo">${esc(texto)}</span></span>`;

/* T-28: POST JSON sem multipart. */
async function postJSON(rota, corpo) {
  const r = await fetch(rota, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  return r.json();
}

/* Converte segundos em texto legível para o operador. */
function tempoAtras(s) {
  if (s == null) return "—";
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${Math.round(s / 60)} min`;
  if (s < 86400) return `${Math.round(s / 3600)} h`;
  return `${Math.round(s / 86400)} dias`;
}

/* Estado da Atalaia em linguagem operacional. */
const NOMES_ESTADO = {
  REGISTRADA: "Cadastrada",
  INSTALADA: "Instalada em campo",
  COMISSIONANDO: "Em ativação",
  VALIDANDO_ENLACE: "Testando comunicação…",
  OPERACIONAL: "Operacional",
  FALHA_ENLACE: "Falha na comunicação",
  MANUTENCAO: "Em manutenção",
  DESATIVADA: "Desativada",
};

const rotas = {};

/* ================================================= T-25: DASHBOARD (Situação)
   Tela principal do operador — substitui a antiga "Visão geral" que mostrava
   fases do PLANO.md e commits. Aqui só há informação de operação. */

rotas["situacao"] = async () => {
  const [sit, com, tel] = await Promise.all([
    api("/api/situacao").catch(() => null),
    api("/api/comissionamento").catch(() => null),
    api("/api/telemetria").catch(() => null),
  ]);

  const estacoes = sit?.estacoes || [];
  const atalaias = com?.atalaias || [];
  const oper = atalaias.filter((a) => a.estado === "OPERACIONAL").length;
  const alertas = (com?.transicoes || []).length;
  const chuvaMax = estacoes.reduce((m, e) => Math.max(m, e.mm_84h || 0), 0);
  const mqttOk = tel?.ligacao?.conectado;

  return cabecalho("Situação",
    "Resumo operacional do sistema de monitoramento.")
    + `<div class="grade g4">
      ${metrica("Atalaias operacionais", `${oper}/${atalaias.length}`,
        oper ? "em campo" : "nenhuma ativa ainda",
        oper ? "ok" : "")}
      ${metrica("Comunicação", mqttOk ? "conectada" : "sem conexão",
        mqttOk ? `${tel.amostras} amostras na janela` : "broker MQTT fora do ar",
        mqttOk ? "ok" : "erro")}
      ${metrica("Chuva 84h máxima",
        chuvaMax ? chuvaMax + " mm" : "—",
        `${estacoes.length} estações oficiais`,
        chuvaMax > 80 ? "atencao" : "")}
      ${metrica("Estações oficiais", estacoes.length || "—",
        "CEMADEN / INMET")}
    </div>`

    + (estacoes.length ? secao("Chuva acumulada — rede oficial")
      + tabela([
        { rot: "Estação", val: (e) => `<strong>${esc(e.nome || e.codigo)}</strong>` },
        { rot: "Município", val: (e) => esc(e.municipio || "—") },
        { rot: "24h", val: (e) => (e.mm_24h ?? "—") + " mm", classe: "num" },
        { rot: "72h", val: (e) => (e.mm_72h ?? "—") + " mm", classe: "num" },
        { rot: "84h", val: (e) => `<strong>${e.mm_84h ?? "—"} mm</strong>`, classe: "num" },
      ], estacoes)
      + `<p class="nota">Acumulados em janela móvel. 84 h é a referência
        da Serra do Mar. ${dica("Baseado na envoltória de Tatizana et al. (1987), referência fundacional para correlação chuva-deslizamento na Serra do Mar.")}</p>`
      : "")

    + secao("Atalaias")
    + (atalaias.length ? tabela([
      { rot: "Atalaia", val: (a) => `<strong>${esc(a.placa)}</strong>` },
      { rot: "Estado", val: (a) => `<span class="tag ${CORES_ESTADO_TAG[a.estado] || "neutro"}">${esc(NOMES_ESTADO[a.estado] || a.estado)}</span>` },
      { rot: "Posição", val: (a) => a.tem_posicao
        ? `<span class="tag ok">sim</span>`
        : `<span class="tag neutro">não</span>` },
      { rot: "Enlace", val: (a) => a.teste_enlace_aprovado === true
        ? `<span class="tag ok">aprovado</span>`
        : a.teste_enlace_aprovado === false
        ? `<span class="tag erro">reprovado</span>`
        : `<span class="tag neutro">—</span>` },
    ], atalaias.slice(0, 10))
    + (atalaias.length > 10 ? `<p class="nota"><a href="#/atalaias">Ver todas as ${atalaias.length} Atalaias →</a></p>` : "")
    : `<div class="vazio">Nenhuma Atalaia cadastrada no sistema.</div>`);
};

/* Alias: rota padrão é "situacao", não mais "visao-geral" */
rotas["visao-geral"] = rotas["situacao"];

/* ================================================= T-30: PROGRESSO (consolida visão geral + pendências + timeline) */

rotas["progresso"] = async () => {
  const [v, g, p] = await Promise.all([
    dados("/api/visao-geral"), dados("/api/git"), dados("/api/pendencias"),
  ]);
  const m = v.modelo;
  const abertas = p.filter((i) => !i.resolvida);

  return cabecalho("Progresso do Projeto",
    `Estado do desenvolvimento — para a equipe de engenharia.`)
    + `<div class="grade g4">
      ${metrica("Fase", v.fase.split("—")[0].trim(), v.fase.split("—")[1] || "")}
      ${metrica("Pendências abertas", abertas.length,
        `de ${p.length} registradas`,
        abertas.length > 8 ? "atencao" : "")}
      ${metrica("CC máxima", v.cc_maxima,
        `limite ${v.cc_limite} · média ${v.cc_media}`,
        v.cc_maxima > v.cc_limite ? "erro" : "ok")}
      ${metrica("Documentação", v.linhas_doc.toLocaleString("pt-BR"),
        `${v.documentos} documentos`)}
    </div>`

    + secao("Progresso por fase")
    + `<div class="cartao">${(v.fases || []).map((f) => {
        const tot = f.feitos + f.parciais + f.abertos || 1;
        const pctF = (f.feitos / tot * 100).toFixed(1);
        const pctP = (f.parciais / tot * 100).toFixed(1);
        const encerrada = !f.abertos && !f.parciais;
        return `
        <div style="margin-bottom:11px">
          <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:4px">
            <span>${esc(f.fase)} — ${esc(f.titulo)}</span>
            <span style="font-family:var(--mono);color:var(--texto-3)">
              ${f.feitos}/${tot}${encerrada ? " ✓" : ""}</span>
          </div>
          <div class="barra-fina" title="${f.feitos} feitos · ${f.parciais} parciais · ${f.abertos} abertos">
            <i style="width:${pctF}%;background:var(--ok)"></i>
            <i style="width:${pctP}%;background:var(--atencao);margin-top:-6px;margin-left:${pctF}%"></i>
          </div>
        </div>`;
      }).join("")}
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
    </div>`

    + secao("Pendências abertas")
    + `<div id="lista-pend"></div>`

    + secao("Atividade recente")
    + `<div class="cartao"><div class="linha-tempo">
      ${g.commits.slice(0, 10).map((c) => `
        <div class="evento">
          <div class="quando">${c.data} · <span class="hash">${c.hash}</span></div>
          <div class="oque">${esc(c.assunto)}</div>
        </div>`).join("")}
    </div></div>`;
};

/* Mantém rotas antigas como alias para não quebrar bookmarks */
rotas["pendencias"] = rotas["progresso"];
rotas["timeline"] = rotas["progresso"];

/* ================================================= T-29/T-30: CHUVA E SENSORES (renomeia "sensor") */

rotas["chuva"] = async () => {
  const [s, sit] = await Promise.all([
    api("/api/sensor"), api("/api/situacao").catch(() => null)]);
  const cab = cabecalho("Chuva e Sensores",
    `Chuva: dados oficiais da rede CEMADEN/INMET. Umidade de solo e
     inclinação: sensores locais da Atalaia.`);

  if (!s.leituras.length) {
    return cab + blocoChuvaOficial(sit) + semDado(
      "Nenhuma leitura de sensor local no banco ainda.")
      + `<p class="nota">Os sensores locais passam a mostrar dados
      quando a primeira Atalaia com sensor entrar em operação.</p>`;
  }

  const chuva = Object.fromEntries(s.chuva.map((c) => [c.node_id, c]));
  return cab + blocoChuvaOficial(sit) + secao("Sensores locais — última leitura")
    + tabela([
      { rot: "Atalaia", val: (l) => `<strong>${esc(l.placa || l.node_id)}</strong>` },
      { rot: "Chuva 1h", val: (l) => l.chuva_valida
        ? `${l.chuva_1h_mm} mm` : `<span class="tag neutro">sem leitura</span>` },
      { rot: "24h", val: (l) => (chuva[l.node_id]?.mm_24h ?? "—") + " mm", classe: "num" },
      { rot: "72h", val: (l) => (chuva[l.node_id]?.mm_72h ?? "—") + " mm", classe: "num" },
      { rot: "Inclinação", val: (l) => l.inclin_valida
        ? `${l.pitch_graus}° / ${l.roll_graus}°`
        : `<span class="tag neutro">sem leitura</span>` },
      { rot: "Solo", val: (l) => l.solo_valido
        ? `${l.umidade_solo}%` : `<span class="tag neutro">—</span>` },
      { rot: "Bateria", val: (l) => `${l.bateria_mv} mV`, classe: "num" },
    ], s.leituras);
};

/* Alias: "sensor" antigo aponta para "chuva" */
rotas["sensor"] = rotas["chuva"];

/* ================================================= T-31: ATALAIAS CADASTRADAS */

rotas["atalaias"] = async () => {
  const c = await api("/api/comissionamento");
  if (c.erro) return cabecalho("Atalaias Cadastradas", "") + semDado("Banco indisponível.", c.erro);

  return cabecalho("Atalaias Cadastradas",
    `Todas as Atalaias registradas no sistema, do cadastro à operação.`)
    + `<div class="grade g4">
      ${metrica("Total", c.atalaias.length, "cadastradas")}
      ${metrica("Operacionais", c.atalaias.filter((a) => a.estado === "OPERACIONAL").length,
        "", "ok")}
      ${metrica("Em manutenção",
        c.atalaias.filter((a) => a.estado === "MANUTENCAO").length, "", "atencao")}
      ${metrica("Com falha",
        c.atalaias.filter((a) => a.estado === "FALHA_ENLACE").length, "", "erro")}
    </div>`
    + `<div class="filtros">
        <button class="filtro ativo" data-e="todas">Todas (${c.atalaias.length})</button>
        <button class="filtro" data-e="OPERACIONAL">Operacionais</button>
        <button class="filtro" data-e="MANUTENCAO">Em manutenção</button>
        <button class="filtro" data-e="FALHA_ENLACE">Com falha</button>
      </div><div id="lista-atalaias"></div>`;
};

function renderAtalaias(itens) {
  el("lista-atalaias").innerHTML = tabela([
    { rot: "Atalaia", val: (a) => `<strong>${esc(a.placa)}</strong>` },
    { rot: "Estado", val: (a) =>
      `<span class="tag ${CORES_ESTADO_TAG[a.estado] || "neutro"}">${esc(NOMES_ESTADO[a.estado] || a.estado)}</span>` },
    { rot: "Posição", val: (a) => a.tem_posicao
      ? `<span class="tag ok">sim</span>`
      : `<span class="tag neutro">não</span>` },
    { rot: "Suscetibilidade", val: (a) => esc(a.classe_suscetibilidade || "—") },
    { rot: "Estação mais próxima", val: (a) => a.distancia_estacao_m
      ? `${Math.round(a.distancia_estacao_m)} m` : "—", classe: "num" },
    { rot: "Enlace", val: (a) => a.teste_enlace_aprovado === true
      ? `<span class="tag ok">aprovado</span>`
      : a.teste_enlace_aprovado === false
      ? `<span class="tag erro">reprovado</span>`
      : `<span class="tag neutro">—</span>` },
    { rot: "Responsável", val: (a) => esc(a.responsavel_campo || "—"), classe: "livre" },
    { rot: "Ficha", val: (a) => a.checklist_em
      ? `<a href="#/laudo?no=${a.node_id}">ver laudo</a>` : "—" },
  ], itens);
}

/* ================================================= T-28: ALERTAS COM AÇÃO */

rotas["alertas"] = async () => {
  const f = await dados("/api/frota");
  const sev = f.por_severidade;
  const grupos = [...new Set(f.alarmes.map((a) => a.grupo))];

  return cabecalho("Alertas",
    `Alarmes do sistema de monitoramento. Uma Atalaia fora do ar é um
     talude sem monitoramento — por isso silêncio é classificado como crítico.`)
    + `<div class="grade g4">
      ${metrica("Críticos", sev.CRITICO || 0, "ação imediata", "erro")}
      ${metrica("Urgentes", sev.URGENTE || 0, "dias de margem", "atencao")}
      ${metrica("Atenção", sev.ATENCAO || 0, "semanas de margem")}
      ${metrica("Atalaias monitoradas", f.operando, `${f.previstos} previstas`)}
    </div>`

    + secao("O que cada padrão de energia revela")
    + tabela([
      { rot: "O que se observa", val: (a) => esc(a.padrao), classe: "livre" },
      { rot: "Diagnóstico provável", val: (a) => `<strong>${esc(a.diagnostico)}</strong>`, classe: "livre" },
      { rot: "Ação recomendada", val: (a) => esc(a.acao) },
    ], f.assinaturas)
    + `<p class="nota">Sujeira reduz a captação uniformemente; sombra atua em
       janela horária específica. A forma da curva separa as duas.
       ${dica("A comparação é feita contra a mediana das Atalaias vizinhas, eliminando a variável climática sem sensor de referência.")}</p>`

    + secao("Catálogo de alarmes")
    + `<div class="filtros">
        <button class="filtro ativo" data-g="todos">Todos (${f.alarmes.length})</button>
        ${grupos.map((g) => `<button class="filtro" data-g="${g}">${g}</button>`).join("")}
      </div><div id="lista-alarmes"></div>`

    + secao("Como se calcula o índice de saúde")
    + `<div class="cartao">${grafBarras(f.pesos_saude.map((p) => ({
        rot: `${p.componente} — ${p.entra_com}`, valor: p.peso })))}
      <p class="nota">Faixas: 90–100 saudável · 70–89 observar · 50–69 agendar ·
      abaixo de 50 intervir. Qualquer alarme crítico zera o índice.
      ${dica("Uma Atalaia muda com bateria cheia não é 70% saudável — é inútil. Por isso alarme crítico zera o índice inteiro.")}</p>
    </div>`;
};

/* Alias: "frota" mantém compatibilidade com bookmarks antigos */

/* ------------------------------------------------- monitoramento ao vivo */

const CORES_VEREDITO_ENLACE = {
  confortavel: "ok", limite: "atencao", critico: "erro", "sem dados": "neutro",
};

const NOMES_VEREDITO = {
  confortavel: "confortável", limite: "no limite", critico: "crítico",
  "sem dados": "sem dados",
};

rotas["monitor"] = async () => cabecalho("Rede ao Vivo",
  `Comunicação em tempo real com as Atalaias. Atualiza a cada 2 segundos.
   ${dica("Subida é o nó falando com o gateway. Descida é o gateway respondendo. Medir os dois sentidos revela assimetrias no enlace.")}`)
  + `<div id="mon-estado"></div>
     <div id="mon-metricas"></div>
     <div id="mon-graficos"></div>
     <div id="mon-frota"></div>`;

function monEstado(t) {
  const lig = t.ligacao;
  if (lig.conectado) {
    return `<div class="ao-vivo"><i></i>conectado a <code>${esc(lig.broker)}</code>
      · ${t.amostras} amostras na janela · atualizado ${esc(t.gerado_em.slice(11))}</div>`;
  }
  const causa = lig.erro
    ? `<code>${esc(lig.erro)}</code>`
    : `o broker <code>${esc(lig.broker || "—")}</code> não respondeu`;
  return `<div class="aviso">
    <strong>Sem telemetria ao vivo</strong> — ${causa}.
    <p>O painel busca o broker em <code>localhost:1883</code>. Como o Mosquitto
    do Raspberry Pi escuta só no próprio host (sem autenticação, não deve ser
    aberto na rede), abra um túnel SSH antes de subir o painel:</p>
    <pre><code>ssh -N -L 1883:127.0.0.1:1883 sentinelapi@192.168.15.73</code></pre>
    <p>O resto do painel funciona normalmente sem isso.</p>
  </div>`;
}

function monMetricas(t) {
  const m = t.metricas, lim = t.limiares;
  const cor = CORES_VEREDITO_ENLACE[m.veredito] || "neutro";
  const md = (e, suf = "") => (e ? e.media + suf : "—");
  return `<div class="grade g4">
    ${metrica("Estado do enlace", NOMES_VEREDITO[m.veredito] || m.veredito,
      `margem atual ${m.margem_atual ?? "—"} dB`, cor + " texto")}
    ${metrica("Margem — subida", md(m.margem_sobe, " dB"),
      `mín ${m.margem_sobe?.min ?? "—"} · bom ≥ ${lim.margem_boa_db}`,
      m.margem_sobe && m.margem_sobe.media >= lim.margem_boa_db ? "ok" : "atencao")}
    ${metrica("Margem — descida", md(m.margem_desce, " dB"),
      `mín ${m.margem_desce?.min ?? "—"} · piso ${lim.sensibilidade_dbm} dBm`,
      m.margem_desce && m.margem_desce.media >= lim.margem_boa_db ? "ok" : "atencao")}
    ${metrica("Perda de pacotes", m.perda_pct + "%",
      `${m.pacotes_min} pacotes/min`, m.perda_pct > 5 ? "erro" : "ok")}
    ${metrica("RSSI subida", md(m.rssi_sobe, " dBm"),
      `${m.rssi_sobe?.min ?? "—"} a ${m.rssi_sobe?.max ?? "—"}`)}
    ${metrica("RSSI descida", md(m.rssi_desce, " dBm"),
      `${m.rssi_desce?.min ?? "—"} a ${m.rssi_desce?.max ?? "—"}`)}
    ${metrica("SNR subida", md(m.snr_sobe, " dB"), `descida ${md(m.snr_desce, " dB")}`)}
    ${metrica("Assimetria", md(m.assimetria, " dB"),
      `limite ±${lim.assimetria_max_db} dB`,
      m.assimetria && Math.abs(m.assimetria.media) > lim.assimetria_max_db
        ? "atencao" : "ok")}
  </div>`;
}

function monGraficos(t) {
  const s = t.serie, lim = t.limiares;
  if (!s.length) return `<div class="vazio">aguardando os primeiros pacotes…</div>`;

  return secao("Margem de enlace — quanta folga antes de o enlace sumir")
    + `<div class="cartao">${grafLinhas(s, {
        series: [{ chave: "margem_sobe", cor: "acento", rot: "subida (nó → gateway)" },
                 { chave: "margem_desce", cor: "atencao", rot: "descida (gateway → nó)" }],
        refs: [{ v: lim.margem_boa_db, cor: "ok", rot: `confortável ${lim.margem_boa_db} dB` },
               { v: lim.margem_min_db, cor: "erro", rot: `mínimo ${lim.margem_min_db} dB` }],
        aria: "Margem de enlace ao longo do tempo",
      })}
      <p class="nota">Margem é o RSSI acima da sensibilidade do SF em uso
      (${lim.sensibilidade_dbm} dBm). É o número que importa em campo: abaixo de
      ${lim.margem_min_db} dB o enlace cai na primeira chuva forte — justamente o
      evento que o sistema existe para monitorar.</p></div>`

    + secao("RSSI nos dois sentidos")
    + `<div class="cartao">${grafLinhas(s, {
        series: [{ chave: "rssi_sobe", cor: "acento", rot: "subida (dBm)" },
                 { chave: "rssi_desce", cor: "atencao", rot: "descida (dBm)" }],
        aria: "RSSI ao longo do tempo",
      })}</div>`

    + secao("Assimetria do enlace")
    + `<div class="cartao">${grafLinhas(s, {
        series: [{ chave: "assimetria", cor: "acento", rot: "subida − descida (dB)" }],
        refs: [{ v: lim.assimetria_max_db, cor: "atencao", rot: `+${lim.assimetria_max_db} dB` },
               { v: -lim.assimetria_max_db, cor: "atencao", rot: `−${lim.assimetria_max_db} dB` }],
        aria: "Assimetria entre os sentidos do enlace",
      })}
      <p class="nota">Positivo significa que o gateway ouve o nó melhor do que o
      nó ouve o gateway. Fora da faixa de ±${lim.assimetria_max_db} dB há antena,
      obstrução próxima ou ruído local em uma das pontas — defeito que só
      aparece porque cada troca mede os dois sentidos.</p></div>`

    + secao("SNR nos dois sentidos")
    + `<div class="cartao">${grafLinhas(s, {
        series: [{ chave: "snr_sobe", cor: "acento", rot: "subida (dB)" },
                 { chave: "snr_desce", cor: "atencao", rot: "descida (dB)" }],
        aria: "SNR ao longo do tempo",
      })}
      <p class="nota">O SX1276 em SF9 ainda demodula por volta de −12,5 dB de
      SNR. Valores confortavelmente positivos indicam que o limite atual é
      distância/obstrução, não ruído.</p></div>`

    + secao("Perdas por amostra")
    + `<div class="cartao">${grafPerdas(s)}
      <p class="nota">Cada haste é um pacote recebido; as altas marcam buracos na
      numeração — pings que não chegaram. Perda isolada é desvanecimento normal;
      perda em rajada indica interferência ou obstrução intermitente.</p></div>`;
}

/* O que a placa está fazendo na rede agora. Ausência de telemetria tem três
   causas bem diferentes, e confundi-las esconde defeito: a bridge não aparece
   como nó porque ela é quem *recebe*; a placa de bancada não transmite de
   propósito; e a que nunca foi gravada simplesmente não existe na rede. */
function selTelemetria(l) {
  if (l.vivo) {
    return `<span class="tag ${l.vivo.estado === "ativo" ? "ok" : "erro"}">${l.vivo.estado}</span>`;
  }
  if (l.env === "bridge") return `<span class="tag acento">gateway</span>`;
  if (!l.mac) return `<span class="tag neutro">não gravada</span>`;
  return `<span class="tag neutro">bancada — só escuta</span>`;
}

function monFrota(t, placas) {
  const vivos = Object.fromEntries(t.nos.map((n) => [n.node_id, n]));
  const linhas = placas.map((p) => ({ ...p, vivo: vivos[p.node_id] || null }));

  return secao("Nós da rede")
    + tabela([
      { rot: "Placa", val: (l) => `<strong>${l.id}</strong>` },
      { rot: "Papel", val: (l) => esc(l.papel), classe: "livre" },
      { rot: "Antena", val: (l) => l.antena
        ? `<span class="tag ok">sim</span>` : `<span class="tag neutro">não</span>` },
      { rot: "Telemetria", val: selTelemetria },
      { rot: "Pacotes", val: (l) => l.vivo ? l.vivo.pacotes : "—", classe: "num" },
      { rot: "Perda", val: (l) => l.vivo ? l.vivo.perda_pct + "%" : "—", classe: "num" },
      { rot: "Último seq", val: (l) => l.vivo ? l.vivo.ultimo_seq : "—", classe: "num" },
      { rot: "Silêncio", val: (l) => l.vivo ? l.vivo.silencio_s + " s" : "—", classe: "num" },
    ], linhas)
    + `<p class="nota"><strong>gateway</strong> é a placa que recebe — ela não
       aparece como nó porque a telemetria descreve o enlace <em>até</em> ela;
       o estado dela está na tabela de bridges abaixo.
       <strong>bancada</strong> (<code>bench_*</code>) escuta mas nunca
       transmite: sem antena, transmitir degrada o PA (A-003) — é o
       comportamento correto, não falha. Silêncio acima de
       ${t.limiares.silencio_s} s numa placa que deveria falar é o gatilho do
       alarme de nó mudo (RC-02).</p>`

    + secao("Bridges")
    + (t.bridges.length ? tabela([
      { rot: "Bridge", val: (b) => `<strong>${esc(b.bridge_id)}</strong>` },
      { rot: "Estado", val: (b) => `<span class="tag ${b.estado === "ativa" ? "ok" : "erro"}">${b.estado}</span>` },
      { rot: "Publicados", val: (b) => b.publicados, classe: "num" },
      { rot: "Fila em disco", val: (b) => b.fila_pendente, classe: "num" },
      { rot: "No ar há", val: (b) => (b.ativa_ha_s / 60).toFixed(0) + " min", classe: "num" },
      { rot: "Última saúde", val: (b) => b.silencio_s + " s", classe: "num" },
    ], t.bridges) : `<div class="vazio">nenhuma bridge publicou saúde ainda</div>`)
    + `<p class="nota">Fila em disco acima de zero significa que a bridge está
       recebendo do rádio mas não conseguindo publicar — o dado não se perde,
       fica em <code>buffer.jsonl</code> até o broker voltar.</p>`;
}

/* --------------------------------------------------- sensores (Frente 3C) */

const CORES_FAIXA = {
  SAUDAVEL: "ok", OBSERVAR: "acento", AGENDAR: "atencao",
  INTERVIR: "erro", SEM_DADO: "neutro",
};

/// Banco fora do ar ou aba ainda sem dado: dizer isso, não desenhar zero.
/// É o RC-07 na interface — número plausível e falso é pior que "sem dado".
const semDado = (msg, erro) => `<div class="aviso">
  <strong>${msg}</strong>
  ${erro ? `<p>Motivo: <code>${esc(erro)}</code></p>` : ""}
</div>`;

function blocoChuvaOficial(sit) {
  if (!sit || !sit.estacoes.length) {
    return secao("Chuva — rede oficial")
      + semDado("Nenhuma estação oficial importada ainda.", sit?.erro)
      + `<p class="nota">A chuva do sistema vem de rede oficial
        (CEMADEN/INMET, <strong>[G]</strong>) e não de pluviômetro próprio —
        ver ADR-009. Importe com
        <code>backend/cemaden.py --estacoes … --chuva …</code>.</p>`;
  }
  const semLimiar = sit.atalaias.some((a) => a.limiar_calibrado === false);
  return secao("Chuva — rede oficial [G]")
    + tabela([
      { rot: "Estação", val: (e) => `<strong>${esc(e.nome || e.codigo)}</strong>` },
      { rot: "Rede", val: (e) => `<span class="tag acento">${esc(e.rede)}</span>` },
      { rot: "Município", val: (e) => esc(e.municipio || "—") },
      { rot: "1h", val: (e) => (e.mm_1h ?? "—") + " mm", classe: "num" },
      { rot: "24h", val: (e) => (e.mm_24h ?? "—") + " mm", classe: "num" },
      { rot: "72h", val: (e) => (e.mm_72h ?? "—") + " mm", classe: "num" },
      { rot: "84h", val: (e) => `<strong>${e.mm_84h ?? "—"} mm</strong>`, classe: "num" },
    ], sit.estacoes)
    + `<p class="nota"><strong>Por que 84 h.</strong> É a janela da envoltória
      de Tatizana et al. (1987) para a Serra do Mar <strong>[L]</strong>,
      referência fundacional brasileira do tema. 24 h e 72 h acompanham porque
      são as janelas com que o CEMADEN opera limiares por município
      <strong>[G]</strong>.</p>`
    + (semLimiar ? `<div class="aviso">
        <strong>Limiar automático desligado — e isso é proposital.</strong>
        <p>A envoltória precisa ser <em>calibrada com o histórico de
        ocorrências do próprio município</em>; os coeficientes de Cubatão não
        valem para outro lugar, e a própria literatura exige atualização
        contínua. Enquanto não houver calibração local, o sistema
        <strong>acumula e mostra, mas não dispara alerta de chuva</strong>
        (RC-18). Pôr um número aqui sem calibração daria aparência de critério
        técnico a um palpite.</p></div>` : "");
}

/* ------------------------------------------- comissionamento (Frente 9/10) */

const CORES_ESTADO_TAG = {
  REGISTRADA: "neutro", INSTALADA: "acento", COMISSIONANDO: "atencao",
  VALIDANDO_ENLACE: "atencao", OPERACIONAL: "ok", FALHA_ENLACE: "erro",
  MANUTENCAO: "atencao", DESATIVADA: "neutro",
};

const selEstado = (e) =>
  `<span class="tag ${CORES_ESTADO_TAG[e] || "neutro"}">${esc(NOMES_ESTADO[e] || e || "—")}</span>`;

/* T-26: Definição do checklist — 6 seções com itens e ajuda. */
const CHECKLIST = [
  { id: "secao_a_identificacao", titulo: "A — Identificação", campos: [
    { chave: "codigo", tipo: "text", rot: "Código da Atalaia", ajuda: "Ex: ATL-CGB-001", obg: true },
    { chave: "farol", tipo: "text", rot: "Farol de referência", ajuda: "Marco geográfico próximo" },
  ]},
  { id: "secao_b_mecanica", titulo: "B — Estabilidade mecânica", campos: [
    { chave: "ancoragem", tipo: "select", rot: "Ancoragem da haste", ajuda: "A haste está firme no solo, sem folga?" },
    { chave: "separacao", tipo: "select", rot: "Separação da vegetação", ajuda: "Vegetação encostando pode causar falsos alarmes de movimento" },
    { chave: "folga_veg", tipo: "select", rot: "Folga mínima 50 cm", ajuda: "Distância da vegetação mais próxima" },
    { chave: "profundidade", tipo: "text", rot: "Profundidade (cm)", ajuda: "Quanto da haste está enterrada" },
  ]},
  { id: "secao_c_energia", titulo: "C — Energia fotovoltaica", campos: [
    { chave: "orientacao", tipo: "select", rot: "Orientação do painel", ajuda: "O painel está voltado para o norte?" },
    { chave: "sombra", tipo: "select", rot: "Livre de sombreamento", ajuda: "Nenhuma sombra sobre o painel nas horas de sol" },
    { chave: "tensao_v", tipo: "text", rot: "Tensão aberta (V)", ajuda: "Medida com multímetro, painel desconectado" },
  ]},
  { id: "secao_d_estanqueidade", titulo: "D — Estanqueidade", campos: [
    { chave: "oring", tipo: "select", rot: "O-ring presente e sem dano", ajuda: "Borracha de vedação da tampa" },
    { chave: "prensacabos", tipo: "select", rot: "Prensa-cabos apertados", ajuda: "Passagem de cabos vedada" },
    { chave: "umidade_pct", tipo: "text", rot: "Umidade interna (%)", ajuda: "Sensor BME280 interno, leitura via display" },
    { chave: "silica", tipo: "select", rot: "Sílica-gel presente", ajuda: "Sachê absorvente dentro do invólucro" },
  ]},
  { id: "secao_e_sensoriamento", titulo: "E — Sensoriamento", campos: [
    { chave: "ref_zero", tipo: "select", rot: "Referência zero do inclinômetro", ajuda: "O inclinômetro foi zerado com a haste nivelada?" },
    { chave: "prof_solo", tipo: "text", rot: "Profundidade sensores de solo (cm)", ajuda: "A que profundidade os sensores de umidade foram enterrados" },
    { chave: "temp_base", tipo: "text", rot: "Temperatura baseline (°C)", ajuda: "Temperatura do BME280 no momento da instalação" },
  ]},
  { id: "secao_f_radio", titulo: "F — Conectividade rádio", campos: [
    { chave: "antena", tipo: "select", rot: "Antena externa conectada", ajuda: "A antena de 6 dBi está conectada ao pigtail?" },
    { chave: "conector_selado", tipo: "select", rot: "Conector selado", ajuda: "Vedação do conector SMA na passagem pelo invólucro" },
    { chave: "obs_radio", tipo: "area", rot: "Observações de conectividade", ajuda: "Obstáculos, linha de visada, distância ao gateway" },
  ]},
];

/* Monta um item de formulário. CC = 3 */
function campoForm(c) {
  const req = c.obg ? '<span class="obrigatorio">*</span>' : "";
  const ajuda = c.ajuda ? `<span class="campo-ajuda">${esc(c.ajuda)}</span>` : "";
  const id = `chk-${c.chave}`;
  let input;
  if (c.tipo === "select") {
    input = `<select class="entrada" id="${id}" name="${c.chave}">
      <option value="">— selecionar —</option>
      <option value="SIM">Conforme</option>
      <option value="NAO">Não conforme</option>
    </select>`;
  } else if (c.tipo === "area") {
    input = `<textarea class="entrada" id="${id}" name="${c.chave}" placeholder="${esc(c.ajuda || "")}"></textarea>`;
  } else {
    input = `<input class="entrada" id="${id}" name="${c.chave}" type="text" placeholder="${esc(c.ajuda || "")}">`;
  }
  return `<div class="campo">
    <label class="campo-label" for="${id}">${esc(c.rot)} ${req}</label>
    ${ajuda}${input}
    <span class="campo-erro">Este campo é obrigatório</span></div>`;
}

/* Monta uma seção do checklist como accordion. CC = 1 */
function secaoChecklist(s) {
  return `<div class="expansivel" data-secao="${s.id}">
    <div class="expansivel-cab">${esc(s.titulo)}
      <span class="expansivel-status pendente">pendente</span></div>
    <div class="expansivel-corpo">
      <div class="campo-grupo">${s.campos.map(campoForm).join("")}</div>
    </div></div>`;
}

/* T-26: Wizard — renderizador de cada passo. CC = 2 */
function wizardPasso1(atalaias) {
  const opts = atalaias
    .filter((a) => ["REGISTRADA", "INSTALADA", "FALHA_ENLACE"].includes(a.estado))
    .map((a) => `<option value="${a.node_id}">${esc(a.placa)} — ${esc(NOMES_ESTADO[a.estado] || a.estado)}</option>`);
  return `<div class="campo">
    <label class="campo-label" for="wiz-atalaia">Selecione a Atalaia ${dica("Escolha a Atalaia que a equipe de campo acabou de instalar ou que precisa ser recomissionada.")}</label>
    <select class="entrada" id="wiz-atalaia"><option value="">— selecionar —</option>${opts.join("")}</select>
  </div>
  <div class="campo-grupo">
    <div class="campo"><label class="campo-label" for="wiz-resp">Responsável de campo (CRT) <span class="obrigatorio">*</span></label>
      <input class="entrada" id="wiz-resp" placeholder="Nome do técnico responsável"></div>
    <div class="campo"><label class="campo-label" for="wiz-geo">Responsável geotécnico (CREA)</label>
      <input class="entrada" id="wiz-geo" placeholder="Eng. geotécnico ou geólogo"></div>
    <div class="campo"><label class="campo-label" for="wiz-autor">Submetido por <span class="obrigatorio">*</span></label>
      <input class="entrada" id="wiz-autor" placeholder="Quem está cadastrando agora"></div>
  </div>`;
}

function wizardPasso2() {
  return CHECKLIST.map(secaoChecklist).join("");
}

function wizardPasso3() {
  return `<div class="campo">
    <label class="campo-label" for="wiz-lat">Latitude ${dica("Coordenada da instalação. Se a foto georeferenciada estiver na pasta da Atalaia, o sistema usa o EXIF automaticamente.")}</label>
    <input class="entrada" id="wiz-lat" type="text" placeholder="-23.5754 (opcional se há foto com GPS)"></div>
  <div class="campo">
    <label class="campo-label" for="wiz-lon">Longitude</label>
    <input class="entrada" id="wiz-lon" type="text" placeholder="-45.3305 (opcional se há foto com GPS)"></div>
  <div class="campo">
    <label class="campo-label" for="wiz-just">Justificativa da posição ${dica("Obrigatória quando lat/lon é digitada manualmente, sem foto EXIF.")}</label>
    <textarea class="entrada" id="wiz-just" placeholder="Obrigatória se a posição foi digitada manualmente"></textarea></div>
  <div class="campo">
    <label class="campo-label" for="wiz-obs">Observações gerais</label>
    <textarea class="entrada" id="wiz-obs" placeholder="Condições do terreno, acesso, notas relevantes"></textarea></div>
  <p class="nota">As fotos da instalação devem ser copiadas para a pasta da Atalaia
    no servidor. O sistema lê automaticamente o GPS do EXIF.
    ${dica("Pasta padrão: /DATA/Projects/Sentinela-Media/Atalaias/<código>/fotos/")}</p>`;
}

/* Monta resumo do checklist preenchido. CC = 3 */
function wizardPasso4Resumo() {
  const dados = coletaChecklist();
  let html = '<div class="grade g3">';
  html += metrica("Atalaia", dados.placa || "—", "");
  html += metrica("Responsável", dados.responsavel_campo || "—", "");
  html += metrica("Submetido por", dados.submetido_por || "—", "");
  html += "</div>";
  CHECKLIST.forEach((s) => {
    const secDados = dados[s.id] || {};
    const total = s.campos.length;
    const preenchidos = s.campos.filter((c) => secDados[c.chave]).length;
    const cor = preenchidos === total ? "ok" : "atencao";
    html += `<p><span class="tag ${cor}">${preenchidos}/${total}</span> ${esc(s.titulo)}</p>`;
  });
  return html;
}

/* Coleta os dados de todos os campos do wizard. CC = 5 */
function coletaChecklist() {
  const v = (id) => (el(id)?.value || "").trim();
  const dados = {
    node_id: parseInt(v("wiz-atalaia")) || null,
    placa: el("wiz-atalaia")?.selectedOptions?.[0]?.textContent?.split(" — ")[0] || "",
    submetido_por: v("wiz-autor"),
    responsavel_campo: v("wiz-resp"),
    responsavel_geotecnico: v("wiz-geo"),
    lat: parseFloat(v("wiz-lat")) || null,
    lon: parseFloat(v("wiz-lon")) || null,
    justificativa_posicao: v("wiz-just"),
    observacoes: v("wiz-obs"),
  };
  CHECKLIST.forEach((s) => {
    const sec = {};
    s.campos.forEach((c) => { sec[c.chave] = v(`chk-${c.chave}`); });
    dados[s.id] = sec;
  });
  return dados;
}

/* Envia o comissionamento ao backend. CC = 4 */
async function enviaComissionamento() {
  const dados = coletaChecklist();
  if (!dados.node_id) return exibeFeedback("erro", "Selecione a Atalaia no passo 1.");
  if (!dados.submetido_por) return exibeFeedback("erro", "Informe quem está submetendo.");
  if (!dados.responsavel_campo) return exibeFeedback("erro", "Informe o responsável de campo.");
  el("wiz-enviar").disabled = true;
  el("wiz-enviar").textContent = "Enviando…";
  const r = await postJSON("/api/comissionamento/cadastrar", dados);
  el("wiz-enviar").disabled = false;
  el("wiz-enviar").textContent = "Submeter comissionamento";
  if (r.erro) return exibeFeedback("erro", r.erro);
  exibeFeedback("ok", `Comissionamento registrado com sucesso. ${r.estado ? "Estado: " + (NOMES_ESTADO[r.estado] || r.estado) : ""}`);
}

function exibeFeedback(tipo, msg) {
  const alvo = el("wiz-feedback");
  if (!alvo) return;
  const cls = tipo === "ok" ? "aviso-sucesso" : "aviso-erro";
  alvo.innerHTML = `<div class="${cls}"><strong>${tipo === "ok" ? "✓" : "✗"}</strong> ${esc(msg)}</div>`;
}

/* T-26: Rota principal do wizard. CC = 2 */
rotas["comissionamento"] = async () => {
  const c = await api("/api/comissionamento");
  if (c.erro) return cabecalho("Nova Atalaia", "") + semDado("Banco indisponível.", c.erro);

  return cabecalho("Nova Atalaia",
    `Cadastro e comissionamento de uma Atalaia. O sistema valida automaticamente cada etapa.
     ${dica("Uma Atalaia comissionada sem validação é fonte de falso positivo ou negativo — os dois perigosos num sistema de alerta.")}`)
    + `<div class="stepper">
        <div class="passo passo-ativo" data-p="1">Selecionar</div>
        <div class="passo" data-p="2">Checklist</div>
        <div class="passo" data-p="3">Posição</div>
        <div class="passo" data-p="4">Revisão</div>
      </div>
      <div class="passo-conteudo visivel" id="wiz-p1">${wizardPasso1(c.atalaias)}</div>
      <div class="passo-conteudo" id="wiz-p2">${wizardPasso2()}</div>
      <div class="passo-conteudo" id="wiz-p3">${wizardPasso3()}</div>
      <div class="passo-conteudo" id="wiz-p4">
        <div id="wiz-resumo"></div>
        <div id="wiz-feedback"></div>
      </div>
      <div class="acoes-barra">
        <button class="btn btn-secundario" id="wiz-ant" disabled>← Anterior</button>
        <span class="espaco"></span>
        <button class="btn btn-primario" id="wiz-prox">Próximo →</button>
        <button class="btn btn-primario" id="wiz-enviar" style="display:none">Submeter comissionamento</button>
      </div>`;
};

/* Liga wizard — navegação de passos e accordions. CC = 7 */
function ligaWizard() {
  let pAtual = 1;
  const passos = document.querySelectorAll(".stepper .passo");
  const ant = el("wiz-ant"), prox = el("wiz-prox"), enviar = el("wiz-enviar");

  function vaiPara(n) {
    pAtual = n;
    passos.forEach((p, i) => {
      p.classList.toggle("passo-ativo", i + 1 === n);
      p.classList.toggle("passo-feito", i + 1 < n);
    });
    for (let i = 1; i <= 4; i++) {
      const d = el(`wiz-p${i}`);
      if (d) d.classList.toggle("visivel", i === n);
    }
    ant.disabled = n === 1;
    prox.style.display = n < 4 ? "" : "none";
    enviar.style.display = n === 4 ? "" : "none";
    if (n === 4) el("wiz-resumo").innerHTML = wizardPasso4Resumo();
  }

  prox.onclick = () => { if (pAtual < 4) vaiPara(pAtual + 1); };
  ant.onclick = () => { if (pAtual > 1) vaiPara(pAtual - 1); };
  enviar.onclick = enviaComissionamento;

  document.querySelectorAll(".expansivel-cab").forEach((cab) => {
    cab.onclick = () => cab.parentElement.classList.toggle("aberto");
  });
}

/* -------------------------------------------- laudo de homologação (§H) */

rotas["laudo"] = async (params) => {
  const nodeId = params?.get("no") || "1";
  const l = await api(`/api/laudo?no=${encodeURIComponent(nodeId)}`);
  if (l.erro) return cabecalho("Laudo", "") + semDado("Banco indisponível.", l.erro);
  if (!l.no.length) return cabecalho("Laudo", "") + semDado("Atalaia não encontrada.");

  const n = l.no[0];
  const c = l.checklist[0];
  if (!c) {
    return cabecalho(`Laudo — ${esc(n.placa)}`, "")
      + semDado("Esta Atalaia ainda não foi comissionada.")
      + `<p class="nota">A ficha de homologação é gerada a partir do checklist
        de instalação. Estado atual: ${selEstado(n.estado)}.</p>`;
  }

  const secoes = [
    ["A — Identificação", c.secao_a_identificacao],
    ["B — Estabilidade mecânica", c.secao_b_mecanica],
    ["C — Energia fotovoltaica", c.secao_c_energia],
    ["D — Estanqueidade", c.secao_d_estanqueidade],
    ["E — Sensoriamento", c.secao_e_sensoriamento],
    ["F — Conectividade rádio", c.secao_f_radio],
  ];
  const item = (v) => v === true || v === "SIM"
    ? `<span class="tag ok">conforme</span>`
    : v === false || v === "NAO"
    ? `<span class="tag erro">não conforme</span>`
    : `<span class="tag neutro">${esc(v)}</span>`;

  return `<div class="laudo">
    ${cabecalho(`Ficha técnica de homologação — ${esc(n.placa)}`,
      `Documento gerado pelo sistema em ${new Date().toLocaleString("pt-BR")}.
       <strong>Não é laudo geotécnico</strong>: atesta a instalação e o enlace
       (Camada 1), não a estabilidade do talude, que exige ART de engenheiro
       ou geólogo (Camada 2 — RESPONSABILIDADE_TECNICA.md §3).`)}

    <div class="grade g4">
      ${metrica("Estado", n.estado, "", CORES_ESTADO_TAG[n.estado] + " texto")}
      ${metrica("Coordenada", c.lat ? `${(+c.lat).toFixed(5)}` : "—",
        c.lon ? `${(+c.lon).toFixed(5)} · WGS84` : "sem posição")}
      ${metrica("Suscetibilidade", c.classe_suscetibilidade || "não cadastrada",
        "CPRM/SGB [G]", c.classe_suscetibilidade ? "atencao texto" : "neutro texto")}
      ${metrica("Estação de chuva", c.distancia_estacao_m
        ? `${Math.round(c.distancia_estacao_m)} m` : "—",
        esc(c.estacao_codigo || ""), c.distancia_estacao_m > 5000 ? "atencao" : "")}
    </div>
    ${c.distancia_estacao_m > 5000 ? `<div class="aviso">
      <strong>Chuva oficial com representatividade limitada neste ponto.</strong>
      <p>A estação está a ${Math.round(c.distancia_estacao_m)} m. Células
      convectivas na Serra do Mar têm 1–5 km, então a chuva medida pode
      subestimar a do talude. A <strong>umidade de solo local ganha peso
      relativo</strong> na avaliação deste ponto (ADR-009).</p></div>` : ""}

    ${secao("Exposição no raio de 300 m")}
    <div class="grade g3">
      ${metrica("Domicílios", c.domicilios_300m ?? "—", "no raio de 300 m")}
      ${metrica("População", c.populacao_300m ?? "—", "estimada [G]")}
      ${metrica("Declividade", c.declividade_graus ?? "—",
        c.declividade_graus ? "graus (FABDEM)" : "raster não importado")}
    </div>
    <p class="nota"><strong>Não é área de alcance de massa.</strong> O raio de
    300 m é geométrico; delimitar alcance real exige análise geotécnica com ART.
    Serve para priorizar vistoria e dimensionar resposta.</p>

    ${secao("Teste de enlace no comissionamento")}
    <div class="grade g4">
      ${metrica("Resultado", c.teste_enlace_aprovado ? "aprovado" : "reprovado",
        `${c.teste_enlace_amostras ?? 0} amostras`,
        (c.teste_enlace_aprovado ? "ok" : "erro") + " texto")}
      ${metrica("RSSI", c.teste_enlace_rssi_med != null
        ? (+c.teste_enlace_rssi_med).toFixed(1) + " dBm" : "—", "médio")}
      ${metrica("Margem", c.teste_enlace_margem != null
        ? (+c.teste_enlace_margem).toFixed(1) + " dB" : "—", "sobre a sensibilidade")}
      ${metrica("Perdas", c.teste_enlace_perdas ?? "—", "na janela de 60 s",
        c.teste_enlace_perdas ? "erro" : "ok")}
    </div>
    <p class="nota">O teste consulta o <strong>banco</strong>, não o broker:
    aprova apenas se o dado atravessou a esteira inteira — rádio, bridge, MQTT,
    ingestor e PostgreSQL —, que é onde a decisão de risco acontece.</p>

    ${secao("Checklist de instalação")}
    ${secoes.map(([titulo, dados]) => `
      <h3 style="font-size:13px;margin:16px 0 6px;color:var(--texto-2)">${titulo}</h3>
      ${Object.keys(dados || {}).length
        ? tabela([
            { rot: "Item", val: (k) => esc(k[0]), classe: "livre" },
            { rot: "Verificação", val: (k) => item(k[1]) },
          ], Object.entries(dados))
        : `<div class="vazio">seção sem itens</div>`}`).join("")}

    ${secao("Responsabilidade técnica")}
    <div class="tabela-caixa"><table><tbody>
      <tr><td>Camada 1 — produto (instalação, firmware)</td>
          <td><strong>${esc(c.responsavel_campo || "—")}</strong></td></tr>
      <tr><td>Camada 2 — geotecnia (ART CREA)</td>
          <td><strong>${esc(c.responsavel_geotecnico || "não informado")}</strong></td></tr>
      <tr><td>Camada 3 — decisão de evacuação</td>
          <td>Defesa Civil municipal — <em>o sistema não decide (RC-00)</em></td></tr>
      <tr><td>Submetido por</td><td>${esc(c.submetido_por || "—")}</td></tr>
      <tr><td>Submetido em</td>
          <td>${esc((c.submetido_em || "").replace("T", " ").slice(0, 19))}</td></tr>
    </tbody></table></div>
    ${c.justificativa_posicao ? `<p class="nota"><strong>Justificativa de
      posição:</strong> ${esc(c.justificativa_posicao)}</p>` : ""}
    ${c.observacoes ? `<p class="nota"><strong>Observações:</strong>
      ${esc(c.observacoes)}</p>` : ""}

    ${secao("Assinaturas")}
    <div class="assinaturas">
      <div><hr>Técnico responsável (CRT)</div>
      <div><hr>Eng. Geotécnico / Geólogo (CREA)</div>
      <div><hr>Defesa Civil Municipal</div>
    </div>
    <p class="nota imprimir-nao">Use <strong>Imprimir → Salvar como PDF</strong>
    para gerar a via oficial: a folha de estilo já remove menu e cores de tela.</p>
  </div>`;
};

/* ------------------------------------------------------- mapa (Frente 5) */

rotas["mapa"] = async () => cabecalho("Mapa",
  `Centro de comando geoespacial. Roda no navegador, sem exigir QGIS nem
   software proprietário no computador do operador.`)
  + `<div class="cartao" style="padding:0;overflow:hidden">
       <div id="mapa" style="height:min(72vh,640px);width:100%"></div>
     </div>
     <div class="legenda" style="margin-top:12px">
       <span><i class="pt" style="background:#3fb950"></i>operacional</span>
       <span><i class="pt" style="background:#d29922"></i>comissionando / manutenção</span>
       <span><i class="pt" style="background:#4da3ff"></i>instalada</span>
       <span><i class="pt" style="background:#f85149"></i>falha de enlace</span>
       <span><i class="pt" style="background:#6e7d8f"></i>registrada</span>
       <span><i class="pt" style="background:#4da3ff;border-radius:2px"></i>estação de chuva [G]</span>
     </div>
     <p class="nota">Círculo é Atalaia (instrumento do projeto), quadrado é
     estação oficial de chuva — escalas de confiança diferentes. A cor da
     Atalaia vem do <strong>estado do ciclo de vida</strong>, não do índice de
     saúde: uma Atalaia ainda em comissionamento não é ponto de dado confiável,
     e mostrá-la verde induziria o operador a confiar em medição não
     homologada.</p>
     <div id="mapa-aviso"></div>`;

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

/* A rota "frota" agora é alias para "alertas" — mantém compatibilidade */
rotas["frota"] = rotas["alertas"];

function renderAlarmes(itens) {
  el("lista-alarmes").innerHTML = tabela([
    { rot: "Severidade", val: (a) =>
      `<span class="tag ${CORES_SEV[a.severidade]}">${a.severidade}</span>` },
    { rot: "Alarme", val: (a) => `<strong>${esc(a.nome)}</strong>` },
    { rot: "Gatilho", val: (a) => esc(a.gatilho), classe: "livre" },
    { rot: "Ação recomendada", val: (a) => esc(a.acao), classe: "livre" },
    { rot: "Atendimento", val: (a) => a.reconhecido_em
      ? `<span class="tag ok" title="Por ${esc(a.reconhecido_por || "operador")}">✓ Reconhecido</span>`
      : `<button class="btn btn-sm btn-secundario btn-rec-alarme" data-id="${a.id || 0}" data-nome="${esc(a.nome)}">Reconhecer</button>` },
  ], itens);
}

function abrirModalReconhecimento(id, nome) {
  let modal = el("modal-rec-alarme");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-rec-alarme";
    modal.className = "modal-fundo";
    document.body.appendChild(modal);
  }
  modal.innerHTML = `<div class="modal">
    <div class="modal-cab">
      <span>Reconhecer Alarme — ${esc(nome)}</span>
      <button onclick="fecharModalReconhecimento()">×</button>
    </div>
    <div class="modal-corpo">
      <div class="campo">
        <label class="campo-label" for="rec-operador">Operador / Agente <span class="obrigatorio">*</span></label>
        <input class="entrada" id="rec-operador" placeholder="Seu nome ou código de agente">
      </div>
      <div class="campo">
        <label class="campo-label" for="rec-acao">Ação tomada</label>
        <select class="entrada" id="rec-acao">
          <option value="RECONHECIDO">Ciente / Monitorando</option>
          <option value="DESPACHO_CAMPO">Despachar Equipe de Campo</option>
          <option value="MANUTENCAO_AGENDADA">Agendar Manutenção</option>
          <option value="FALSO_POSITIVO">Falso Positivo / Teste</option>
        </select>
      </div>
      <div class="campo">
        <label class="campo-label" for="rec-nota">Nota de atendimento</label>
        <textarea class="entrada" id="rec-nota" placeholder="Observações para o diário de operações..."></textarea>
      </div>
      <div id="modal-rec-feedback"></div>
    </div>
    <div class="modal-rodape">
      <button class="btn btn-secundario" onclick="fecharModalReconhecimento()">Cancelar</button>
      <button class="btn btn-primario" onclick="submeterReconhecimento(${id})">Confirmar</button>
    </div>
  </div>`;
  modal.classList.add("visivel");
}

function fecharModalReconhecimento() {
  const modal = el("modal-rec-alarme");
  if (modal) modal.classList.remove("visivel");
}

async function submeterReconhecimento(alarmeId) {
  const op = el("rec-operador")?.value?.trim();
  if (!op) {
    el("modal-rec-feedback").innerHTML = `<div class="aviso-erro">Informe o nome do operador.</div>`;
    return;
  }
  const acao = el("rec-acao")?.value || "RECONHECIDO";
  const nota = el("rec-nota")?.value?.trim() || "";
  const despacho = acao === "DESPACHO_CAMPO";

  const res = await postJSON("/api/alarme/reconhecer", {
    alarme_id: alarmeId,
    operador: op,
    acao_tomada: acao,
    despacho_equipe: despacho,
    nota_operador: nota,
  });

  if (res.erro) {
    el("modal-rec-feedback").innerHTML = `<div class="aviso-erro">${esc(res.erro)}</div>`;
  } else {
    fecharModalReconhecimento();
    navega();
  }
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
  const bruto = location.hash.replace(/^#\/?/, "") || "situacao";
  const [nome, query] = bruto.split("?");
  return { nome: nome || "situacao", params: new URLSearchParams(query || "") };
}

async function navega() {
  const { nome, params } = partesDaRota();
  const render = rotas[nome] || rotas["situacao"];

  paraMonitor();   // sair da aba encerra o polling; nada roda em segundo plano

  /* Expande o grupo de desenvolvimento se a rota ativa estiver dentro dele */
  const rotasDev = ["progresso", "hardware", "rede", "documentos", "referencias",
                    "pendencias", "timeline", "firmware", "qualidade"];
  if (rotasDev.includes(nome)) expandeGrupoDev();

  document.querySelectorAll("nav a").forEach((a) =>
    a.classList.toggle("ativo", a.dataset.rota === nome));

  const alvo = el("rota");
  alvo.innerHTML = `<div class="carregando">carregando…</div>`;
  window.scrollTo({ top: 0 });
  try {
    alvo.innerHTML = await render(params);
  } catch (e) {
    alvo.innerHTML = `<div class="vazio">falha ao carregar: ${esc(e.message)}</div>`;
    return;
  }
  await depoisDeRenderizar(nome, params);
}

async function depoisDeRenderizar(nome, params) {
  if (nome === "progresso") return ligaProgresso();
  if (nome === "documentos") return ligaDocumentos(params);
  if (nome === "alertas" || nome === "frota") return ligaFrota();
  if (nome === "monitor") return ligaMonitor();
  if (nome === "mapa") return ligaMapa();
  if (nome === "atalaias") return ligaAtalaias();
  if (nome === "comissionamento") return ligaWizard();
}

/* ----------------------------------------------------------------- mapa */

let mapa = null;

const CORES_MAPA = {
  SAUDAVEL: "#3fb950", OBSERVAR: "#4da3ff", AGENDAR: "#d29922",
  INTERVIR: "#f85149", SEM_DADO: "#6e7d8f",
};

/* Estado do ciclo de vida (Frente 9). O marcador no mapa é colorido pelo
   estado, não pelo índice de saúde: uma Atalaia em COMISSIONANDO ainda não é
   ponto de dado confiável, e mostrá-la verde induziria o operador a confiar em
   medição que ainda não foi homologada. */
const CORES_ESTADO = {
  REGISTRADA: "#6e7d8f", INSTALADA: "#4da3ff", COMISSIONANDO: "#d29922",
  VALIDANDO_ENLACE: "#d29922", OPERACIONAL: "#3fb950",
  FALHA_ENLACE: "#f85149", MANUTENCAO: "#d29922", DESATIVADA: "#3a4553",
};

/// Fundo do mapa. Tiles online são conveniência; o mapa **precisa** continuar
/// utilizável sem internet, porque é durante a tempestade — quando o enlace
/// tende a cair — que o operador mais precisa dele. Por isso o basemap é
/// opcional e as camadas de dados vêm do banco local.
function camadaBase() {
  return L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    { maxZoom: 19, attribution: "© OpenStreetMap, © CARTO" });
}

/// Chuva oficial no popup. Sai **junto com a distância da estação** sempre:
/// o acumulado sozinho sugere uma precisão que ele não tem. Acima de 5 km a
/// representatividade cai (ADR-009) e o número aparece marcado, não escondido
/// — ocultar dado ruim é pior que exibi-lo com a ressalva.
function chuvaNoPopup(p) {
  if (p.distancia_estacao_m == null) {
    return '<div class="pop-chuva">chuva oficial: sem estação associada</div>';
  }
  const km = (p.distancia_estacao_m / 1000).toFixed(1);
  const longe = p.distancia_estacao_m > 5000;
  const mm = (v) => (v == null ? "—" : `${v} mm`);
  return `<div class="pop-chuva${longe ? " pop-atencao" : ""}">
    chuva oficial · ${esc(p.estacao || "—")} a ${km} km${longe
      ? " <strong>(representatividade limitada)</strong>" : ""}<br>
    24 h ${mm(p.mm_24h)} · 72 h ${mm(p.mm_72h)} · <strong>84 h ${mm(p.mm_84h)}</strong>
  </div>`;
}

/// Enlace e energia correntes. Sem leitura, diz "sem leitura" — nunca zero
/// (RC-07: ausência de medida não pode virar valor plausível).
function enlaceNoPopup(p) {
  if (p.rssi_dbm == null) return "enlace: sem leitura<br>";
  const bat = p.v_fim_mv != null ? ` · bat ${(p.v_fim_mv / 1000).toFixed(2)} V` : "";
  const umi = p.umidade_interna != null ? ` · U<sub>int</sub> ${p.umidade_interna}%` : "";
  return `enlace: ${p.rssi_dbm} dBm · SNR ${p.snr_db ?? "—"} dB${bat}${umi}<br>`;
}

function marcador(f) {
  const p = f.properties || {};
  const cor = CORES_ESTADO[p.estado] || CORES_MAPA[p.faixa] || CORES_MAPA.SEM_DADO;
  const [lon, lat] = f.geometry.coordinates;
  const foto = p.foto_oficial_path
    ? `<img class="pop-foto" alt="instalação de ${esc(p.placa || "")}"
         src="/media/${encodeURIComponent(p.placa)}/${esc(p.foto_oficial_path)}">`
    : "";
  return L.circleMarker([lat, lon], {
    radius: 9, color: cor, fillColor: cor, fillOpacity: 0.75, weight: 2,
  }).bindPopup(`
    <strong>${esc(p.placa || p.node_id)}</strong><br>
    <span style="color:${cor}">● ${esc(p.estado || "—")}</span><br>
    ${esc(p.papel || "")}<br>
    ${foto}
    índice: ${p.indice ?? "sem dado"} (${esc(p.faixa || "—")})<br>
    comunicação: ${esc(p.estado_comunicacao || "—")}<br>
    ${enlaceNoPopup(p)}
    alarmes abertos: ${p.alarmes_abertos ?? 0}<br>
    ${chuvaNoPopup(p)}
    <a href="#/laudo?no=${p.node_id}">ficha de homologação</a>`);
}

function pontoEnsaio(f) {
  const p = f.properties || {};
  const [lon, lat] = f.geometry.coordinates;
  const cor = CORES_VEREDITO[p.veredito] === "ok" ? "#3fb950"
    : CORES_VEREDITO[p.veredito] === "atencao" ? "#d29922" : "#f85149";
  return L.circleMarker([lat, lon], {
    radius: 5, color: cor, fillColor: cor, fillOpacity: 0.6, weight: 1,
  }).bindPopup(`<strong>${esc(p.ensaio)} · P${p.ponto}</strong><br>
    ${p.distancia_m} m · RSSI ${p.rssi_med} dBm<br>
    margem ${p.margem_db} dB · ${esc(p.veredito)}`);
}

async function ligaMapa() {
  if (mapa) { mapa.remove(); mapa = null; }
  mapa = L.map("mapa", { zoomControl: true }).setView([-23.5754, -45.3305], 15);
  camadaBase().addTo(mapa);

  const [atalaias, ensaios, susc, estacoes] = await Promise.all([
    api("/api/gis/atalaias").catch(() => null),
    api("/api/gis/ensaios").catch(() => null),
    api("/api/gis/suscetibilidade").catch(() => null),
    api("/api/gis/estacoes").catch(() => null),
  ]);

  const camadas = {};
  const grupoAtalaias = L.layerGroup();
  (atalaias?.features || []).forEach((f) => marcador(f).addTo(grupoAtalaias));
  grupoAtalaias.addTo(mapa);
  camadas["Atalaias"] = grupoAtalaias;

  const grupoEnsaio = L.layerGroup();
  (ensaios?.features || []).forEach((f) => pontoEnsaio(f).addTo(grupoEnsaio));
  camadas["Pontos de ensaio"] = grupoEnsaio;

  // Rede oficial de chuva (ADR-009). Quadrado, não círculo: distinguir de
  // relance o que é instrumento nosso do que é dado de terceiro importa —
  // são escalas de confiança diferentes (regional vs. talude).
  const grupoEstacoes = L.layerGroup();
  (estacoes?.features || []).forEach((f) => {
    const p = f.properties || {};
    const [lon, lat] = f.geometry.coordinates;
    L.marker([lat, lon], {
      icon: L.divIcon({
        className: "",
        html: `<div style="width:13px;height:13px;background:#4da3ff;
               border:2px solid #fff;border-radius:2px"></div>`,
        iconSize: [13, 13], iconAnchor: [7, 7],
      }),
    }).bindPopup(`<strong>${esc(p.nome || p.codigo)}</strong><br>
      ${esc(p.rede)} · ${esc(p.municipio || "")}<br>
      24h: ${p.mm_24h ?? "—"} mm · 72h: ${p.mm_72h ?? "—"} mm<br>
      <strong>84h: ${p.mm_84h ?? "—"} mm</strong> (janela de Tatizana)`)
      .addTo(grupoEstacoes);
  });
  if ((estacoes?.features || []).length) {
    grupoEstacoes.addTo(mapa);
    camadas["Chuva oficial (CEMADEN)"] = grupoEstacoes;
  }

  if (susc?.features?.length) {
    const g = L.geoJSON(susc, { style: { color: "#f85149", weight: 1, fillOpacity: 0.2 } });
    camadas["Suscetibilidade"] = g;
  }
  L.control.layers(null, camadas, { collapsed: false }).addTo(mapa);

  const pontos = [...(atalaias?.features || []), ...(ensaios?.features || [])];
  if (pontos.length) {
    grupoEnsaio.addTo(mapa);
    mapa.fitBounds(pontos.map((f) => [f.geometry.coordinates[1],
                                      f.geometry.coordinates[0]]),
                   { padding: [40, 40], maxZoom: 17 });
  }

  const aviso = el("mapa-aviso");
  const semAtalaia = !(atalaias?.features || []).length;
  const erro = atalaias?.erro || ensaios?.erro;
  if (aviso && (semAtalaia || erro)) {
    aviso.innerHTML = `<p class="nota">${
      erro ? `Banco indisponível: <code>${esc(erro)}</code>. `
           : "Nenhuma Atalaia tem coordenada cadastrada ainda — as placas estão "
             + "em bancada, e <code>no.posicao</code> só é preenchido na "
             + "instalação em campo. "}
      Os pontos do ensaio 02 aparecem porque já estão no PostGIS.</p>`;
  }
}

/* ------------------------------------------------ monitoramento ao vivo */

let timerMonitor = null;

function paraMonitor() {
  if (timerMonitor) { clearInterval(timerMonitor); timerMonitor = null; }
}

async function atualizaMonitor(placas) {
  let t;
  try {
    t = await api("/api/telemetria");
  } catch (e) {
    el("mon-estado").innerHTML =
      `<div class="aviso">painel sem resposta: ${esc(e.message)}</div>`;
    return;
  }
  if (!el("mon-estado")) return paraMonitor();   // usuário já mudou de aba
  el("mon-estado").innerHTML = monEstado(t);
  el("mon-metricas").innerHTML = monMetricas(t);
  el("mon-graficos").innerHTML = monGraficos(t);
  el("mon-frota").innerHTML = monFrota(t, placas);
}

async function ligaMonitor() {
  const h = await dados("/api/hardware");
  await atualizaMonitor(h.placas);
  paraMonitor();
  timerMonitor = setInterval(() => atualizaMonitor(h.placas), 2000);
}

async function ligaFrota() {
  const f = await dados("/api/frota");
  const aplica = (g) => {
    renderAlarmes(g === "todos" ? f.alarmes : f.alarmes.filter((a) => a.grupo === g));
    document.querySelectorAll(".btn-rec-alarme").forEach((b) => {
      b.onclick = () => abrirModalReconhecimento(b.dataset.id, b.dataset.nome);
    });
  };
  aplica("todos");
  document.querySelectorAll(".filtro").forEach((b) => b.onclick = () => {
    document.querySelectorAll(".filtro").forEach((x) => x.classList.remove("ativo"));
    b.classList.add("ativo");
    aplica(b.dataset.g);
  });
}

function ligaDocumentos(params) {
  document.querySelectorAll("#doc-lista button").forEach((b) =>
    b.onclick = () => abreDocumento(b.dataset.doc));
  const inicial = params.get("doc") || "README.md";
  abreDocumento(inicial);
}

/* --------------------------------------------------------------- selos */

async function atualizaSeloVivo() {
  try {
    const t = await api("/api/telemetria");
    const s = el("selo-vivo");
    const mudos = t.nos.filter((n) => n.estado === "silencioso").length;
    s.textContent = t.ligacao.conectado ? (mudos ? "!" : "●") : "";
    s.className = "selo " + (!t.ligacao.conectado ? "" : mudos ? "alerta" : "bom");
  } catch { /* selo é enfeite: falhar aqui não pode afetar o painel */ }
}

async function atualizaSelos() {
  atualizaSeloVivo();
  setInterval(atualizaSeloVivo, 10000);
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

/* --------------------------------------------- grupo colapsável */

function expandeGrupoDev() {
  const g = el("nav-dev-grupo");
  const i = el("nav-dev-itens");
  if (g && i) { g.classList.remove("fechado"); i.classList.remove("nav-colapsado"); }
}

function iniciaNavColapsavel() {
  const g = el("nav-dev-grupo");
  const i = el("nav-dev-itens");
  if (!g || !i) return;
  g.addEventListener("click", () => {
    g.classList.toggle("fechado");
    i.classList.toggle("nav-colapsado");
  });
}

/* -------------------------------------------- hooks de rotas novas */

async function ligaAtalaias() {
  const c = await api("/api/comissionamento").catch(() => ({ atalaias: [] }));
  const aplica = (e) => renderAtalaias(
    e === "todas" ? c.atalaias : c.atalaias.filter((a) => a.estado === e));
  aplica("todas");
  document.querySelectorAll(".filtro").forEach((b) => b.onclick = () => {
    document.querySelectorAll(".filtro").forEach((x) => x.classList.remove("ativo"));
    b.classList.add("ativo");
    aplica(b.dataset.e);
  });
}

async function ligaProgresso() {
  const p = await dados("/api/pendencias");
  const abertas = p.filter((i) => !i.resolvida);
  renderPendencias(abertas);
}

function renderPendencias(itens) {
  const alvo = el("lista-pend");
  if (!alvo) return;
  alvo.innerHTML = tabela([
    { rot: "Tipo", val: (i) => `<span class="tag ${i.resolvida ? "ok" : i.grupo === "[?]" ? "erro" : "atencao"}">${esc(i.grupo)}</span>` },
    { rot: "Descrição", val: (i) => esc(i.descricao), classe: "livre" },
    { rot: "Documento", val: (i) => `<code>${esc(i.arquivo)}</code>` },
    { rot: "Linha", val: (i) => i.linha, classe: "num" },
  ], itens);
}

window.addEventListener("hashchange", navega);
iniciaTema();
iniciaNavColapsavel();
navega();
atualizaSelos();
