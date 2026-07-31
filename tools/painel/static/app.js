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
      <p class="nota">Contado das caixas do <code>PLANO.md</code>, não escrito à
      mão — verde é concluído, âmbar é parcial. O trabalho corre em mais de uma
      fase ao mesmo tempo: a Fase 2 fechou enquanto a Fase 0 ainda tem o ensaio
      de campo de SF em aberto.</p>
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

/* ------------------------------------------------- monitoramento ao vivo */

const CORES_VEREDITO_ENLACE = {
  confortavel: "ok", limite: "atencao", critico: "erro", "sem dados": "neutro",
};

const NOMES_VEREDITO = {
  confortavel: "confortável", limite: "no limite", critico: "crítico",
  "sem dados": "sem dados",
};

rotas["monitor"] = async () => cabecalho("Monitoramento em tempo real",
  `Telemetria ao vivo da rede LoRa, direto do broker MQTT. Atualiza sozinho a
   cada 2 s. <strong>Subida</strong> é o nó falando com o gateway;
   <strong>descida</strong> é o gateway respondendo — medir os dois sentidos é
   o que revela enlace assimétrico.`)
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

  paraMonitor();   // sair da aba encerra o polling; nada roda em segundo plano

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
  if (nome === "monitor") return ligaMonitor();
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

window.addEventListener("hashchange", navega);
iniciaTema();
navega();
atualizaSelos();
