/**
 * Conferencia Escolas x PDF (Fev/2025) — Rede Estadual MS
 *
 * Valida alinhamento entre Unidade Escolar, Municipio e CRE na planilha
 * usando como referencia o PDF "Contatos e Enderecos das Escolas Estaduais".
 *
 * Instalacao:
 * 1. Extensions > Apps Script — cole este arquivo (Code.gs)
 * 2. Salve e recarregue a planilha
 * 3. Menu "Conferencia Escolas" > Conferir planilha ativa
 *
 * Atualizar referencia (quando sair novo PDF):
 *   python scripts/gerar_referencia_conferencia_escolas.py
 *   Copie o conteudo gerado de ConferenciaEscolas.gs para o Apps Script
 */

var REFERENCIA_JSON = __REFERENCIA_JSON__;

var CONFIG = {
  abaReferencia: '_Referencia',
  colStatus: 'Status Conferencia',
  colObs: 'Observacao Conferencia',
  limiarNucleo: 0.72,
  cores: {
    ok: '#d9ead3',           // match 100%
    parcial: '#fff2cc',      // nucleo coincide, nome difere
    creErrada: '#fce5cd',    // escola/municipio ok, CRE errada
    municipioErrado: '#f4cccc', // municipio nao bate com referencia
    naoEncontrada: '#e6b8af',   // escola ausente no PDF
    vazia: '#efefef',
    cabecalho: '#cfe2f3'
  }
};

var _cacheRef = null;

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Conferencia Escolas')
    .addItem('Conferir planilha ativa', 'conferirPlanilhaAtiva')
    .addItem('Popular aba _Referencia', 'popularAbaReferencia')
    .addItem('Limpar marcacoes', 'limparMarcacoes')
    .addSeparator()
    .addItem('Ver legenda de cores', 'mostrarLegenda')
    .addToUi();
}

function mostrarLegenda() {
  var msg = [
    'Verde: escola, municipio e CRE conferem (match 100%)',
    'Amarelo: nucleo do nome coincide, mas grafia difere; municipio e CRE ok',
    'Laranja: escola e municipio ok mas CRE divergente, ou municipio associado a CRE errada',
    'Vermelho: municipio errado (escola existe em outro municipio no PDF)',
    'Marrom: escola nao encontrada no PDF de referencia',
    'Cinza: linha vazia'
  ].join('\n');
  SpreadsheetApp.getUi().alert('Legenda', msg, SpreadsheetApp.getUi().ButtonSet.OK);
}

// --- Normalizacao -----------------------------------------------------------

function normalizarTexto(texto) {
  if (texto === null || texto === undefined || texto === '') return '';
  var s = String(texto).trim().toUpperCase();
  s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  s = s.replace(/[^A-Z0-9 ]+/g, ' ');
  s = s.replace(/\s+/g, ' ').trim();
  return s;
}

function normalizarNomeEscola(texto) {
  var s = normalizarTexto(texto);
  if (!s) return '';

  s = s.replace(/\bPROF A\b|\bPROF O\b/g, 'PROF');
  s = s.replace(/\bPROFAS?\b|\bPROFS?\b/g, 'PROF');
  s = s.replace(/\bESCOLA CIVICO MILITAR\b/g, 'ECIM');
  s = s.replace(/\bESCOLA CIVICO\b\s+\bMILITAR\b/g, 'ECIM');
  s = s.replace(/\bCIVICO MILITAR\b/g, 'ECIM');
  s = s.replace(/\bEE\s*CM\b/g, 'ECIM');
  s = s.replace(/\bEECM\b/g, 'ECIM');

  var subs = [
    [/\bESCOLA ESTADUAL\b/g, 'EE'],
    [/\bE\s*\.\s*E\s*\./g, 'EE'],
    [/\bE\s+E\b/g, 'EE'],
    [/\bESC EST\b/g, 'EE'],
    [/\bESCOLA\b/g, 'EE'],
    [/\bCENTRO ESTADUAL DE EDUCACAO PROFISSIONAL\b/g, 'CEEP'],
    [/\bCENTRO DE EDUCACAO PROFISSIONAL\b/g, 'CEEP'],
    [/\bCENTRO ESTADUAL DE EDUCACAO DE JOVENS E ADULTOS\b/g, 'CEEJA'],
    [/\bCENTRO DE EDUCACAO DE JOVENS E ADULTOS\b/g, 'CEEJA'],
    [/\bPROFESSORA\b/g, 'PROF'],
    [/\bPROFESSOR\b/g, 'PROF'],
    [/\bPROFA\b/g, 'PROF'],
    [/\bPROF\b/g, 'PROF'],
    [/\bPADRE\b/g, 'PE'],
    [/\bPRESIDENTE\b/g, 'PRES'],
    [/\bDEPUTADO\b/g, 'DEP'],
    [/\bCORONEL\b/g, 'CEL'],
    [/\bMARECHAL\b/g, 'MAL'],
    [/\bDOUTORA\b/g, 'DRA'],
    [/\bDOUTOR\b/g, 'DR'],
    [/\bIRMA\b/g, 'IRMA'],
    [/\bIRMAO\b/g, 'IRMA'],
    [/\bDONA\b/g, 'DONA']
  ];
  subs.forEach(function (par) { s = s.replace(par[0], par[1]); });

  s = s.replace(/\bEE\s+EE\b/g, 'EE');
  s = s.replace(/\bECIM\b/g, 'EE');
  s = s.replace(/\bEXTENSAO\b.*$/, '');
  s = s.replace(/\bANEXO\b.*$/, '');
  s = s.replace(/\bSALA\b.*$/, '');
  s = s.replace(/\bMS\b$/, '');
  s = s.replace(/\bDE\b|\bDO\b|\bDA\b|\bDOS\b|\bDAS\b/g, ' ');
  s = s.replace(/\s+/g, ' ').trim();
  return s;
}

function normalizarCre(cre) {
  if (cre === null || cre === undefined || cre === '') return '';
  var s = String(cre).trim().toUpperCase();
  if (s.indexOf('SED') >= 0 || s.indexOf('CAMPO GRANDE CAPITAL') >= 0) return 'SED';
  var m = s.match(/CRE\s*\d+/);
  if (m) return m[0].replace(/\s+/g, ' ');
  return s;
}

function chaveEscolaMunicipio(escola, municipio) {
  return normalizarNomeEscola(escola) + '|' + normalizarTexto(municipio);
}

// --- Referencia -------------------------------------------------------------

function parseReferenciaEmbutida_() {
  if (Array.isArray(REFERENCIA_JSON)) {
    return REFERENCIA_JSON;
  }
  if (typeof REFERENCIA_JSON === 'string' && REFERENCIA_JSON.length) {
    return JSON.parse(REFERENCIA_JSON);
  }
  throw new Error('Referencia embutida invalida. Regenere o script.');
}

function carregarReferencia() {
  if (_cacheRef) return _cacheRef;

  var dados = null;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(CONFIG.abaReferencia);
  if (sh && sh.getLastRow() > 1) {
    dados = lerReferenciaDaAba_(sh);
  }
  if (!dados || !dados.length) {
    try {
      dados = parseReferenciaEmbutida_();
    } catch (e) {
      throw new Error('Referencia indisponivel. Execute popularAbaReferencia() ou regenere o script.');
    }
  }

  _cacheRef = indexarReferencia_(dados);
  return _cacheRef;
}

function lerReferenciaDaAba_(sh) {
  var vals = sh.getDataRange().getValues();
  if (vals.length < 2) return [];
  var hdr = vals[0].map(function (h) { return normalizarTexto(h); });
  var ixInep = hdr.indexOf('INEP');
  var ixEsc = hdr.indexOf('UNIDADE ESCOLAR') >= 0 ? hdr.indexOf('UNIDADE ESCOLAR') : hdr.indexOf('ESCOLA');
  var ixMun = hdr.indexOf('MUNICIPIO');
  var ixCre = hdr.indexOf('CRE');
  if (ixInep < 0) ixInep = 0;
  if (ixEsc < 0) ixEsc = 1;
  if (ixMun < 0) ixMun = 2;
  if (ixCre < 0) ixCre = 3;

  var out = [];
  for (var r = 1; r < vals.length; r++) {
    var row = vals[r];
    if (!row[ixEsc] && !row[ixInep]) continue;
    out.push({
      i: String(row[ixInep] || '').trim(),
      e: String(row[ixEsc] || '').trim(),
      m: String(row[ixMun] || '').trim(),
      c: String(row[ixCre] || '').trim()
    });
  }
  return out;
}

function indexarReferencia_(dados) {
  var porInep = {};
  var porChave = {};
  var porMunicipio = {};
  var lista = [];

  dados.forEach(function (item) {
    var ref = {
      inep: String(item.i || item.inep || '').trim(),
      escola: String(item.e || item.escola || '').trim(),
      municipio: String(item.m || item.municipio || '').trim(),
      cre: String(item.c || item.cre || '').trim(),
      escolaNorm: normalizarNomeEscola(item.e || item.escola),
      municipioNorm: normalizarTexto(item.m || item.municipio),
      creNorm: normalizarCre(item.c || item.cre)
    };
    lista.push(ref);
    if (ref.inep) porInep[ref.inep] = ref;
    var chave = ref.escolaNorm + '|' + ref.municipioNorm;
    if (!porChave[chave]) porChave[chave] = ref;
    if (!porMunicipio[ref.municipioNorm]) porMunicipio[ref.municipioNorm] = [];
    porMunicipio[ref.municipioNorm].push(ref);
  });

  var crePorMunicipio = {};
  lista.forEach(function (ref) {
    if (ref.municipioNorm && ref.creNorm) {
      crePorMunicipio[ref.municipioNorm] = ref.creNorm;
    }
  });

  return {
    lista: lista,
    porInep: porInep,
    porChave: porChave,
    porMunicipio: porMunicipio,
    crePorMunicipio: crePorMunicipio
  };
}

function popularAbaReferencia() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(CONFIG.abaReferencia);
  if (!sh) {
    sh = ss.insertSheet(CONFIG.abaReferencia);
  }
  sh.clear();
  sh.getRange(1, 1, 1, 4).setValues([['INEP', 'Unidade Escolar', 'Municipio', 'CRE']]);
  var dados = parseReferenciaEmbutida_();
  var rows = dados.map(function (d) { return [d.i, d.e, d.m, d.c]; });
  if (rows.length) {
    sh.getRange(2, 1, 1 + rows.length, 4).setValues(rows);
  }
  sh.setFrozenRows(1);
  _cacheRef = null;
  SpreadsheetApp.getUi().alert('Aba _Referencia populada com ' + rows.length + ' escolas.');
}

// --- Matching ---------------------------------------------------------------

var TOKENS_STOP = {
  'EE': 1, 'CEEP': 1, 'CEEJA': 1, 'PROF': 1, 'PE': 1, 'PRES': 1, 'DEP': 1,
  'CEL': 1, 'MAL': 1, 'DR': 1, 'DRA': 1, 'IRMA': 1, 'DONA': 1, 'MS': 1, 'ECIM': 1
};

function tokensNucleo(escolaNorm) {
  return escolaNorm.split(' ').filter(function (t) {
    return t.length > 1 && !TOKENS_STOP[t];
  });
}

function similaridadeNucleo(aNorm, bNorm) {
  if (!aNorm || !bNorm) return 0;
  if (aNorm === bNorm) return 1;

  var ta = tokensNucleo(aNorm);
  var tb = tokensNucleo(bNorm);
  if (!ta.length || !tb.length) return 0;

  var setB = {};
  tb.forEach(function (t) { setB[t] = true; });
  var inter = 0;
  ta.forEach(function (t) { if (setB[t]) inter++; });

  var union = {};
  ta.concat(tb).forEach(function (t) { union[t] = true; });
  var jaccard = inter / Object.keys(union).length;

  var minSize = Math.min(ta.length, tb.length);
  var subset = inter >= Math.max(2, minSize - 1) && inter >= minSize * 0.85;

  return Math.max(jaccard, subset ? 0.86 : 0);
}

function buscarReferencia(refIdx, escola, municipio, inepOpt) {
  if (inepOpt) {
    var direto = refIdx.porInep[String(inepOpt).trim()];
    if (direto) {
      return { ref: direto, score: 1, modo: 'inep' };
    }
  }

  var escNorm = normalizarNomeEscola(escola);
  var munNorm = normalizarTexto(municipio);
  if (!escNorm) return null;

  var chave = escNorm + '|' + munNorm;
  if (refIdx.porChave[chave]) {
    return { ref: refIdx.porChave[chave], score: 1, modo: 'exato' };
  }

  var candidatos = refIdx.porMunicipio[munNorm] || [];
  var melhor = null;
  candidatos.forEach(function (c) {
    var sc = similaridadeNucleo(escNorm, c.escolaNorm);
    if (!melhor || sc > melhor.score) melhor = { ref: c, score: sc, modo: 'fuzzy_municipio' };
  });
  if (melhor && melhor.score >= CONFIG.limiarNucleo) return melhor;

  // Busca global para detectar municipio errado
  var global = null;
  refIdx.lista.forEach(function (c) {
    var sc = similaridadeNucleo(escNorm, c.escolaNorm);
    if (!global || sc > global.score) global = { ref: c, score: sc, modo: 'fuzzy_global' };
  });
  if (global && global.score >= CONFIG.limiarNucleo) return global;

  return null;
}

function avaliarLinha(refIdx, escola, municipio, cre, inepOpt) {
  if (!escola && !municipio && !cre) {
    return { status: 'VAZIA', obs: '', cor: CONFIG.cores.vazia };
  }

  var munPlan = normalizarTexto(municipio);
  var crePlan = normalizarCre(cre);
  var creEsperadaMuni = munPlan ? refIdx.crePorMunicipio[munPlan] : '';

  if (munPlan && crePlan && creEsperadaMuni && crePlan !== creEsperadaMuni) {
    return {
      status: 'CRE/MUNICIPIO INCOMPATIVEL',
      obs: 'Municipio "' + municipio + '" pertence a ' + creEsperadaMuni +
        ' (planilha: ' + (cre || '(vazio)') + ')',
      cor: CONFIG.cores.creErrada
    };
  }

  var match = buscarReferencia(refIdx, escola, municipio, inepOpt);

  if (!match) {
    return {
      status: 'NAO ENCONTRADA',
      obs: 'Escola nao localizada no PDF de referencia (Fev/2025)',
      cor: CONFIG.cores.naoEncontrada
    };
  }

  var ref = match.ref;
  var nomeExato = match.score >= 1 && normalizarNomeEscola(escola) === ref.escolaNorm;
  var munOk = munPlan === ref.municipioNorm;
  var creOk = crePlan === ref.creNorm;

  if (!munOk) {
    return {
      status: 'MUNICIPIO ERRADO',
      obs: 'No PDF: ' + ref.municipio + ' / CRE ' + ref.cre + ' (INEP ' + ref.inep + ')',
      cor: CONFIG.cores.municipioErrado,
      ref: ref
    };
  }

  if (!creOk) {
    return {
      status: 'CRE ERRADA',
      obs: 'CRE esperada: ' + ref.cre + ' | Planilha: ' + (cre || '(vazio)') + ' | INEP ' + ref.inep,
      cor: CONFIG.cores.creErrada,
      ref: ref
    };
  }

  if (nomeExato || match.modo === 'exato' || match.modo === 'inep') {
    return {
      status: 'OK',
      obs: 'Conferido com PDF (INEP ' + ref.inep + ')',
      cor: CONFIG.cores.ok,
      ref: ref
    };
  }

  return {
    status: 'OK PARCIAL',
    obs: 'Nucleo coincide; PDF: "' + ref.escola + '" | INEP ' + ref.inep,
    cor: CONFIG.cores.parcial,
    ref: ref
  };
}

// --- Planilha ---------------------------------------------------------------

function detectarColunas_(headerRow) {
  var cols = { escola: -1, municipio: -1, cre: -1, inep: -1 };
  for (var c = 0; c < headerRow.length; c++) {
    var h = normalizarTexto(headerRow[c]);
    if (cols.escola < 0 && (h.indexOf('UNIDADE ESCOLAR') >= 0 || h === 'ESCOLA' || h.indexOf('NOME ESCOLA') >= 0)) {
      cols.escola = c;
    } else if (cols.municipio < 0 && h.indexOf('MUNICIPIO') >= 0) {
      cols.municipio = c;
    } else if (cols.cre < 0 && (h === 'CRE' || /^CRE(\s|$)/.test(h))) {
      cols.cre = c;
    } else if (cols.inep < 0 && (h.indexOf('INEP') >= 0 || h.indexOf('COD INEP') >= 0 || h.indexOf('CODIGO INEP') >= 0)) {
      cols.inep = c;
    }
  }
  return cols;
}

function encontrarLinhaCabecalho_(sheet) {
  var maxScan = Math.min(15, sheet.getLastRow());
  var width = Math.max(sheet.getLastColumn(), 10);
  for (var r = 1; r <= maxScan; r++) {
    var row = sheet.getRange(r, 1, 1, width).getValues()[0];
    var cols = detectarColunas_(row);
    if (cols.escola >= 0 && cols.municipio >= 0) {
      return { row: r, cols: cols, header: row };
    }
  }
  throw new Error('Cabecalho nao encontrado. Colunas necessarias: Unidade Escolar e Municipio.');
}

function conferirPlanilhaAtiva() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getActiveSheet();
  if (sheet.getName() === CONFIG.abaReferencia) {
    SpreadsheetApp.getUi().alert('Selecione a aba de dados (nao _Referencia).');
    return;
  }

  var refIdx = carregarReferencia();
  var cab = encontrarLinhaCabecalho_(sheet);
  var header = cab.header.slice();
  var cols = cab.cols;

  var ixStatus = header.map(function (h) { return String(h); }).indexOf(CONFIG.colStatus);
  var ixObs = header.map(function (h) { return String(h); }).indexOf(CONFIG.colObs);
  var nextCol = header.length;

  if (ixStatus < 0) {
    ixStatus = nextCol++;
    sheet.getRange(cab.row, ixStatus + 1).setValue(CONFIG.colStatus);
  }
  if (ixObs < 0) {
    ixObs = nextCol++;
    sheet.getRange(cab.row, ixObs + 1).setValue(CONFIG.colObs);
  }

  var lastRow = sheet.getLastRow();
  if (lastRow <= cab.row) {
    SpreadsheetApp.getUi().alert('Nenhuma linha de dados abaixo do cabecalho.');
    return;
  }

  var numRows = lastRow - cab.row;
  var width = Math.max(sheet.getLastColumn(), ixObs + 1);
  var data = sheet.getRange(cab.row + 1, 1, numRows, width).getValues();

  var resumo = { ok: 0, parcial: 0, cre: 0, mun: 0, ne: 0, vazia: 0 };
  var backgrounds = [];
  var statusCol = [];
  var obsCol = [];

  for (var i = 0; i < data.length; i++) {
    var row = data[i];
    var escola = row[cols.escola];
    var municipio = row[cols.municipio];
    var cre = cols.cre >= 0 ? row[cols.cre] : '';
    var inep = cols.inep >= 0 ? row[cols.inep] : '';

    var av = avaliarLinha(refIdx, escola, municipio, cre, inep);
    statusCol.push([av.status]);
    obsCol.push([av.obs]);

    var bgRow = [];
    for (var j = 0; j < width; j++) bgRow.push(null);
    bgRow[cols.escola] = av.cor;
    if (cols.municipio >= 0) bgRow[cols.municipio] = av.cor;
    if (cols.cre >= 0) bgRow[cols.cre] = av.cor;
    backgrounds.push(bgRow);

    switch (av.status) {
      case 'OK': resumo.ok++; break;
      case 'OK PARCIAL': resumo.parcial++; break;
      case 'CRE ERRADA':
      case 'CRE/MUNICIPIO INCOMPATIVEL': resumo.cre++; break;
      case 'MUNICIPIO ERRADO': resumo.mun++; break;
      case 'NAO ENCONTRADA': resumo.ne++; break;
      default: resumo.vazia++;
    }
  }

  var dataRange = sheet.getRange(cab.row + 1, 1, numRows, width);
  dataRange.setBackgrounds(backgrounds);
  sheet.getRange(cab.row + 1, ixStatus + 1, numRows, 1).setValues(statusCol);
  sheet.getRange(cab.row + 1, ixObs + 1, numRows, 1).setValues(obsCol);
  sheet.getRange(cab.row, ixStatus + 1, 1, 2).setBackground(CONFIG.cores.cabecalho);

  var msg = [
    'Conferencia concluida — ' + sheet.getName(),
    '',
    'OK (100%): ' + resumo.ok,
    'OK parcial (nome): ' + resumo.parcial,
    'CRE errada: ' + resumo.cre,
    'Municipio errado: ' + resumo.mun,
    'Nao encontrada: ' + resumo.ne,
    'Linhas vazias: ' + resumo.vazia,
    '',
    'Verifique linhas em vermelho, laranja e marrom.'
  ].join('\n');

  SpreadsheetApp.getUi().alert('Conferencia Escolas', msg, SpreadsheetApp.getUi().ButtonSet.OK);
}

function limparMarcacoes() {
  var sheet = SpreadsheetApp.getActiveSheet();
  if (sheet.getName() === CONFIG.abaReferencia) return;

  var cab = encontrarLinhaCabecalho_(sheet);
  var lastRow = sheet.getLastRow();
  if (lastRow <= cab.row) return;

  var width = sheet.getLastColumn();
  sheet.getRange(cab.row + 1, 1, lastRow - cab.row, width).setBackground(null);

  var header = sheet.getRange(cab.row, 1, 1, width).getValues()[0];
  [CONFIG.colStatus, CONFIG.colObs].forEach(function (nome) {
    for (var c = 0; c < header.length; c++) {
      if (String(header[c]) === nome) {
        sheet.getRange(cab.row + 1, c + 1, lastRow - cab.row, 1).clearContent();
      }
    }
  });
}
