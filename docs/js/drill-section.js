(function (ED) {
  let SEL_CRE = null;
  let SEL_MUN = null;
  let _ctx = null;

  function bread() {
    const b = document.getElementById('bread');
    let h = `<span class="crumb ${SEL_CRE ? '' : 'active'}" onclick="resetDrill()">Estado \u00b7 MS</span>`;
    if (SEL_CRE) {
      h += `<span class="sepc">\u2192</span><span class="crumb ${SEL_MUN ? '' : 'active'}" onclick="selectCre('${SEL_CRE.replace(/'/g, "\\'")}')">${SEL_CRE}</span>`;
    }
    if (SEL_MUN) {
      h += `<span class="sepc">\u2192</span><span class="crumb active">${SEL_MUN}</span>`;
    }
    b.innerHTML = h;
  }

  function renderAreas(containerId, areas, refMap) {
    const ctx = _ctx;
    const { ANOS, DATA, AREANOME, ACOR, C, BL, CFG } = ctx;
    const host = document.getElementById(containerId);
    host.innerHTML = '';
    ctx.AREAKEYS.forEach((k) => {
      const v = areas[k];
      const last = v[v.length - 1];
      const ref = refMap[k];
      const warn = last < ref;
      const tile = document.createElement('div');
      tile.className = `atile${warn ? ' warn' : ''}`;
      const delta = last - ref;
      tile.innerHTML = `<div class="at"><span>${k}</span><span class="fl" style="color:${warn ? C.critico : C.verde}">${delta >= 0 ? '+' : ''}${delta.toFixed(0)}</span></div><div id="${containerId}_${k}" style="height:74px"></div>`;
      host.appendChild(tile);
      Plotly.newPlot(`${containerId}_${k}`, [
        { x: ANOS, y: DATA.msArea[k].ms, mode: 'lines', line: { color: C.brasil, width: 1.4, dash: 'dot' }, hovertemplate: `${AREANOME[k]} \u00b7 MS estadual<br><b>%{x}</b> \u00b7 %{y:.0f} pts<extra></extra>` },
        { x: ANOS, y: v, mode: 'lines+markers', line: { color: ACOR[k], width: 2 }, marker: { size: 3 }, hovertemplate: `${AREANOME[k]}<br><b>%{x}</b> \u00b7 %{y:.0f} pts<extra></extra>` },
      ], {
        ...BL, height: 74, margin: { l: 4, r: 6, t: 4, b: 14 },
        showlegend: false, xaxis: { visible: false }, yaxis: { visible: false },
      }, CFG);
    });
  }

  function renderMun(creName, muns) {
    const ctx = _ctx;
    const { C, BL, CFG, NF, MS_GERAL_2024, MS_AREA_2024 } = ctx;
    document.getElementById('munTitle').childNodes[0].nodeValue = `Munic\u00edpios de ${creName} \u00b7 participa\u00e7\u00e3o \u00d7 desempenho (2024) `;
    document.getElementById('munAttTitle').childNodes[0].nodeValue = `Aten\u00e7\u00e3o por \u00e1rea \u00b7 munic\u00edpios de ${creName} (2024) `;
    const xs = [];
    const ys = [];
    const sz = [];
    const tt = [];
    const col = [];
    const cd = [];
    const semtx = [];
    muns.forEach((m) => {
      const g = m.med[5];
      const t = m.tx[5];
      const c = m.concl || 30;
      if (t == null) { semtx.push(m.nome); return; }
      xs.push(t);
      ys.push(g);
      sz.push(Math.max(8, Math.sqrt(c) * 1.6));
      col.push(g < MS_GERAL_2024 && t < 27 ? C.critico : C.azul);
      tt.push(m.nome);
      cd.push([m.nome, NF(m.n && m.n[5]), NF(m.concl)]);
    });
    const xmin = xs.length ? Math.min(...xs) : 0;
    const xmax = xs.length ? Math.max(...xs) : 60;
    const ymin = ys.length ? Math.min(...ys) : 470;
    const ymax = ys.length ? Math.max(...ys) : 520;
    Plotly.react('g_mun', [{
      x: xs, y: ys, text: tt, customdata: cd,
      mode: 'markers+text', type: 'scatter', textposition: 'top center', textfont: { size: 9, color: C.muted },
      marker: { size: sz, color: col, opacity: 0.7, line: { color: '#fff', width: 1 } },
      hovertemplate: '<b>%{text}</b><br>Part.: %{x:.1f}% \u00b7 %{customdata[1]} part. efetivos<br>M\u00e9dia: %{y:.1f}<br>Concluintes: %{customdata[2]}<extra></extra>',
    }], {
      ...BL, height: 300, showlegend: false,
      xaxis: { title: { text: 'participa\u00e7\u00e3o efetiva (%)', font: { size: 10 } }, gridcolor: C.subtle },
      yaxis: { title: { text: 'm\u00e9dia geral', font: { size: 10 } }, gridcolor: C.subtle },
      shapes: [
        { type: 'line', x0: 27, x1: 27, y0: ymin - 5, y1: ymax + 5, line: { color: C.borda, width: 1, dash: 'dot' } },
        { type: 'line', x0: xmin - 3, x1: xmax + 3, y0: MS_GERAL_2024, y1: MS_GERAL_2024, line: { color: C.brasil, width: 1, dash: 'dash' } },
      ],
    }, CFG).then((gd) => {
      if (gd.removeAllListeners) gd.removeAllListeners('plotly_click');
      gd.on('plotly_click', (e) => { selectMun(e.points[0].customdata[0]); });
    });
    const nn = document.getElementById('munNota');
    nn.innerHTML = semtx.length
      ? `<b>Sem taxa de participa\u00e7\u00e3o (${semtx.length}):</b> ${semtx.join(', ')} \u2014 sem registro de concluintes na base municipal, ent\u00e3o n\u00e3o h\u00e1 eixo de participa\u00e7\u00e3o para posicion\u00e1-los aqui. Eles continuam no mapa de aten\u00e7\u00e3o por \u00e1rea abaixo (que usa apenas o desempenho).`
      : '';
    const A4 = ['CN', 'CH', 'LC', 'MT', 'RED'];
    const rows = muns.map((m) => ({
      n: m.nome,
      z: A4.map((k) => {
        const val = m.a2024[k];
        return val == null ? null : Math.round(val - MS_AREA_2024[k]);
      }),
    }));
    rows.sort((a, b) => a.z.reduce((s, v) => s + (v || 0), 0) - b.z.reduce((s, v) => s + (v || 0), 0));
    Plotly.react('g_munheat', [{
      z: rows.map((r) => r.z), x: A4, y: rows.map((r) => r.n), type: 'heatmap',
      colorscale: [[0, '#B23A36'], [0.5, '#F2F4F7'], [1, '#1E7A4D']],
      zmid: 0, zmin: -30, zmax: 30,
      text: rows.map((r) => r.z), texttemplate: '%{text}', textfont: { size: 9 },
      colorbar: { thickness: 9, len: 0.8, tickfont: { size: 8 } },
      hovertemplate: '%{y} \u00b7 %{x}: %{z}<extra></extra>',
    }], {
      ...BL, height: 300, margin: { l: 120, r: 8, t: 6, b: 22 },
      xaxis: { side: 'top', tickfont: { size: 10 } },
      yaxis: { tickfont: { size: 8.5 }, autorange: 'reversed' },
    }, CFG);
  }

  function selectCre(name) {
    const ctx = _ctx;
    const { DATA, MS_AREA_2024 } = ctx;
    SEL_CRE = name;
    SEL_MUN = null;
    document.querySelectorAll('.ctile').forEach((t) =>
      t.classList.toggle('sel', t.querySelector('.ct span').textContent === name)
    );
    document.getElementById('escCard').style.display = 'none';
    document.getElementById('creAreaCard').style.display = 'block';
    document.querySelector('#creAreaTitle span').textContent = `${name} \u00b7 2019\u20132024`;
    renderAreas('creAreas', DATA.cre[name].areas, MS_AREA_2024);
    const muns = (DATA.creMuns[name] || [])
      .map((m) => (DATA.mun[m] ? { nome: m, ...DATA.mun[m] } : null))
      .filter(Boolean);
    document.getElementById('munRow').style.display = muns.length ? 'grid' : 'none';
    renderMun(name, muns);
    bread();
    document.getElementById('munRow').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function selectMun(name) {
    const ctx = _ctx;
    const { DATA, MS_AREA_2024, MS_GERAL_2024 } = ctx;
    SEL_MUN = name;
    bread();
    document.querySelector('#creAreaTitle span').textContent = `${name} \u00b7 2019\u20132024`;
    if (DATA.mun[name]) renderAreas('creAreas', DATA.mun[name].areas, MS_AREA_2024);
    const list = (DATA.esc[name] || []).slice().sort((a, b) => a.geral - b.geral);
    document.getElementById('escCard').style.display = list.length ? 'block' : 'none';
    document.getElementById('escTitle').childNodes[0].nodeValue = `Escolas de ${name} \u00b7 2024 `;
    const body = document.getElementById('escBody');
    body.innerHTML = '';
    const cell = (v, k) => {
      const cls = v < MS_AREA_2024[k] ? 'bad' : (v >= MS_AREA_2024[k] + 8 ? 'ok' : '');
      return `<td class="${cls}">${v.toFixed(0)}</td>`;
    };
    list.forEach((s) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${s.nome}</td><td>${s.concl != null ? s.concl : '<span class="muted">\u2014</span>'}</td><td>${s.part}</td><td>${s.tx != null ? `${s.tx.toFixed(0)}%` : '<span class="muted">\u2014</span>'}</td>`
        + cell(s.cn, 'CN') + cell(s.ch, 'CH') + cell(s.lc, 'LC') + cell(s.mt, 'MT') + cell(s.red, 'RED')
        + `<td class="b${s.geral < MS_GERAL_2024 ? ' bad' : ''}">${s.geral.toFixed(0)}</td>`;
      body.appendChild(tr);
    });
    document.getElementById('escCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function resetDrill() {
    SEL_CRE = null;
    SEL_MUN = null;
    document.querySelectorAll('.ctile').forEach((t) => t.classList.remove('sel'));
    ['creAreaCard', 'munRow', 'escCard'].forEach((id) => {
      document.getElementById(id).style.display = 'none';
    });
    bread();
  }

  ED.initDrill = function (ctx) {
    _ctx = ctx;
    const { DATA, ANOS, C, BL, CFG, NF, norm } = ctx;
    const row = document.getElementById('creRow');
    function creTrajData(o) {
      const xs = [];
      const ys = [];
      const cd = [];
      ANOS.forEach((a, i) => {
        const tx = o.tx?.[i];
        const med = o.med?.[i];
        if (tx == null || med == null || Number.isNaN(tx) || Number.isNaN(med)) return;
        xs.push(tx);
        ys.push(med);
        cd.push([a, NF(o.n && o.n[i])]);
      });
      return { xs, ys, cd };
    }

    function creTrajRanges(o) {
      const { xs, ys } = creTrajData(o);
      const padX = (v) => Math.max(2, v * 0.15);
      const padY = 4;
      const xMin = xs.length ? Math.min(...xs) : 0;
      const xMax = xs.length ? Math.max(...xs) : 60;
      const yMin = ys.length ? Math.min(...ys) : 460;
      const yMax = ys.length ? Math.max(...ys) : 535;
      return {
        x: [Math.max(0, xMin - padX(xMin)), xMax + padX(xMax)],
        y: [yMin - padY, yMax + padY],
      };
    }

    Object.keys(DATA.cre || {}).forEach((name) => {
      const o = DATA.cre[name];
      const adv = o.med[5] >= o.med[0];
      const sid = `ct_${norm(name).replace(/ /g, '_')}`;
      const t = document.createElement('div');
      t.className = 'ctile';
      t.onclick = () => selectCre(name);
      t.innerHTML = `<div class="ct"><span>${name}</span><span class="arr" style="color:${adv ? C.verde : C.critico}">${adv ? '\u25B2' : '\u25BC'}</span></div><div id="${sid}" style="height:78px"></div>`;
      row.appendChild(t);
      const traj = creTrajData(o);
      const rng = creTrajRanges(o);
      const traces = [];
      if (traj.xs.length >= 2) {
        traces.push({
          x: traj.xs, y: traj.ys, customdata: traj.cd, mode: 'lines',
          line: { color: 'rgba(10,77,140,.55)', width: 2 },
          hovertemplate: '<b>%{customdata[0]}</b><br>Participa\u00e7\u00e3o: %{x:.1f}%<br>M\u00e9dia: %{y:.0f}<br>Part. efetivos: %{customdata[1]}<extra></extra>',
        });
        traces.push({
          x: [traj.xs[0]], y: [traj.ys[0]], customdata: [traj.cd[0]], mode: 'markers',
          marker: { color: C.borda, size: 6 },
          hovertemplate: '<b>%{customdata[0]}</b><br>Participa\u00e7\u00e3o: %{x:.1f}%<br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
        const li = traj.xs.length - 1;
        traces.push({
          x: [traj.xs[li]], y: [traj.ys[li]], customdata: [traj.cd[li]], mode: 'markers',
          marker: { color: adv ? C.verde : C.critico, size: 8, line: { color: '#fff', width: 1 } },
          hovertemplate: '<b>%{customdata[0]}</b><br>Participa\u00e7\u00e3o: %{x:.1f}%<br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
      } else {
        const medPts = (o.med || []).filter((v) => v != null && !Number.isNaN(v));
        rng.y = medPts.length
          ? [Math.min(...medPts) - 4, Math.max(...medPts) + 4]
          : [460, 535];
        delete rng.x;
        traces.push({
          x: ANOS.map(String), y: o.med, mode: 'lines+markers',
          line: { color: 'rgba(10,77,140,.55)', width: 2 },
          marker: { size: 4, color: C.azul },
          hovertemplate: '<b>%{x}</b><br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
        traces.push({
          x: [String(ANOS[0])], y: [o.med[0]], mode: 'markers', marker: { color: C.borda, size: 6 },
          hovertemplate: '<b>2019</b><br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
        traces.push({
          x: [String(ANOS[5])], y: [o.med[5]], mode: 'markers',
          marker: { color: adv ? C.verde : C.critico, size: 8, line: { color: '#fff', width: 1 } },
          hovertemplate: '<b>2024</b><br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
      }
      const xaxis = rng.x
        ? { visible: false, range: rng.x }
        : { visible: false, type: 'category', categoryorder: 'array', categoryarray: ANOS.map(String) };
      Plotly.newPlot(sid, traces, {
        ...BL, height: 78, margin: { l: 4, r: 6, t: 4, b: 4 },
        showlegend: false, hovermode: 'closest',
        xaxis,
        yaxis: { visible: false, range: rng.y },
      }, CFG);
    });
    bread();
    window.selectCre = selectCre;
    window.selectMun = selectMun;
    window.resetDrill = resetDrill;
  };
})(window.EnemDash);
