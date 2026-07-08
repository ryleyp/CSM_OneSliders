(() => {
  'use strict';

  function sameOriginTesseractAsset(resource) {
    try {
      const url = new URL(typeof resource === 'string' ? resource : resource.url, window.location.href);
      return url.origin === window.location.origin && url.pathname.includes('/assets/vendor/tesseract/');
    } catch (_err) {
      return false;
    }
  }

  if ('fetch' in window) {
    const originalFetch = window.fetch.bind(window);
    window.fetch = (resource, options = {}) => {
      const method = String(options.method || 'GET').toUpperCase();
      if (method === 'GET' && sameOriginTesseractAsset(resource)) {
        return originalFetch(resource, options);
      }
      return Promise.reject(new Error('External network access is disabled in this static app.'));
    };
  }
  if ('sendBeacon' in navigator) {
    navigator.sendBeacon = () => false;
  }
  if ('XMLHttpRequest' in window) {
    const XHR = window.XMLHttpRequest;
    window.XMLHttpRequest = function DisabledXMLHttpRequest() {
      const xhr = new XHR();
      const open = xhr.open;
      xhr.open = function guardedOpen(method, url, ...rest) {
        if (String(method || 'GET').toUpperCase() === 'GET' && sameOriginTesseractAsset(url)) {
          return open.call(this, method, url, ...rest);
        }
        throw new Error('External network access is disabled in this static app.');
      };
      xhr._open = open;
      return xhr;
    };
  }

  const MONTHS = {
    jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6,
    jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12
  };

  const US_STATES = new Set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split(' '));
  const STATE_NAMES = {
    alabama: 'AL', alaska: 'AK', arizona: 'AZ', arkansas: 'AR', california: 'CA',
    colorado: 'CO', connecticut: 'CT', delaware: 'DE', florida: 'FL', georgia: 'GA',
    hawaii: 'HI', idaho: 'ID', illinois: 'IL', indiana: 'IN', iowa: 'IA',
    kansas: 'KS', kentucky: 'KY', louisiana: 'LA', maine: 'ME', maryland: 'MD',
    massachusetts: 'MA', michigan: 'MI', minnesota: 'MN', mississippi: 'MS',
    missouri: 'MO', montana: 'MT', nebraska: 'NE', nevada: 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM',
    'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', ohio: 'OH',
    oklahoma: 'OK', oregon: 'OR', pennsylvania: 'PA', 'rhode island': 'RI',
    'south carolina': 'SC', 'south dakota': 'SD', tennessee: 'TN', texas: 'TX',
    utah: 'UT', vermont: 'VT', virginia: 'VA', washington: 'WA',
    'west virginia': 'WV', wisconsin: 'WI', wyoming: 'WY', 'district of columbia': 'DC'
  };

  const EXAMPLES = {
    machine: [
      'Year\tQuarter\tMonth\tMachine Type\tDistinct count',
      '2025\tQ1\tJanuary\tExisting\t690',
      '2025\tQ1\tJanuary\tNew\t42',
      '2025\tQ1\tFebruary\tExisting\t704',
      '2025\tQ1\tFebruary\tNew\t38',
      '2025\tQ1\tMarch\tExisting\t711',
      '2025\tQ1\tMarch\tNew\t51',
      '2025\tQ2\tApril\tExisting\t730',
      '2025\tQ2\tApril\tNew\t66',
      '2025\tQ2\tMay\tExisting\t744',
      '2025\tQ2\tMay\tNew\t58',
      '2025\tQ2\tJune\tExisting\t751',
      '2025\tQ2\tJune\tNew\t62'
    ].join('\n'),
    locations: [
      'ip_country\tip_region\tip_city\tMeasure Names\tproduct_name\tMeasure Values',
      'United States\tTexas\tAustin\tDistinct count of machine_id\tLabVIEW\t188',
      'United States\tTexas\tAustin\tDistinct count of machine_id\tTestStand\t142',
      'United States\tMichigan\tDetroit\tDistinct count of machine_id\tLabVIEW\t96',
      'United States\tMichigan\tDetroit\tDistinct count of machine_id\tTestStand\t71',
      'United States\tCalifornia\tSan Jose\tDistinct count of machine_id\tLabVIEW\t83'
    ].join('\n'),
    versions: [
      'product_name\tproduct_version\tDistinct count of machine_id',
      'LabVIEW\t2021\t399',
      'LabVIEW\t2024\t126',
      'TestStand\t2022\t188',
      'TestStand\t2024\t49',
      'VeriStand\t2023\t72'
    ].join('\n'),
    finite: [
      '25\tNamed User\tLabVIEW Professional',
      '12\tConcurrent\tTestStand',
      '8\tNamed User\tDIAdem'
    ].join('\n'),
    bundles: ['EA Platform Bundle', 'LabVIEW Bundle'].join('\n')
  };

  const uploadedShots = { a: null, b: null, c: null };
  let ocrWorkerPromise = null;

  const SHOT_META = {
    a: {
      inputId: 'screenshotA',
      previewId: 'shotPreviewA',
      rawId: 'ocrRawA',
      statusId: 'ocrStatusA',
      label: 'Screenshot A - Contract details'
    },
    b: {
      inputId: 'screenshotB',
      previewId: 'shotPreviewB',
      rawId: 'ocrRawB',
      statusId: 'ocrStatusB',
      label: 'Screenshot B - Finite licenses'
    },
    c: {
      inputId: 'screenshotC',
      previewId: 'shotPreviewC',
      rawId: 'ocrRawC',
      statusId: 'ocrStatusC',
      label: 'Screenshot C - Unlimited bundles'
    }
  };

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
  const setStatus = (message, kind = '') => {
    if (!$('appStatus')) return;
    $('appStatus').textContent = message || '';
    $('appStatus').className = `app-status ${kind}`.trim();
  };
  const fmt = (value) => {
    const n = toNumber(value);
    return n === null ? esc(value || '—') : Math.round(n).toLocaleString();
  };

  function toNumber(value) {
    if (value === null || value === undefined) return null;
    const match = String(value).replace(/,/g, '').match(/-?\d+(\.\d+)?/);
    return match ? Number(match[0]) : null;
  }

  function rows(text) {
    return String(text || '').split(/\r?\n/).map((line) => {
      if (!line.trim()) return null;
      return (line.includes('\t') ? line.split('\t') : line.trim().split(/\s{2,}/))
        .map((cell) => cell.trim());
    }).filter(Boolean);
  }

  function looksHeader(cells, numericIndexes) {
    return numericIndexes.every((idx) => idx >= cells.length || toNumber(cells[idx]) === null);
  }

  function monthNum(value) {
    return MONTHS[String(value || '').trim().slice(0, 3).toLowerCase()] || null;
  }

  function parseMachine(text) {
    const data = rows(text);
    const isLong = data.some((cells) => {
      if (cells.length < 4) return false;
      const joined = cells.join(' ').toLowerCase();
      return joined.includes('machine type') || cells.some((c) => /^(new|existing)$/i.test(c));
    });
    return isLong ? parseMachineLong(data) : parseMachineWide(data);
  }

  function parseMachineLong(data) {
    if (!data.length) return [];
    const header = data[0];
    const hasHeader = toNumber(header[header.length - 1]) === null;
    let yearI = 0, quarterI = 1, monthI = 2, typeI = 3, countI = header.length - 1;
    const dataRows = hasHeader ? data.slice(1) : data;
    if (hasHeader) {
      header.forEach((h, i) => {
        const low = h.toLowerCase();
        if (low.includes('year')) yearI = i;
        else if (low.includes('quarter')) quarterI = i;
        else if (low.includes('month')) monthI = i;
        else if (low.includes('machine type') || low === 'type' || low.includes('type')) typeI = i;
        else if (low.includes('count') || low.includes('machine_id') || low.includes('distinct')) countI = i;
      });
    }
    const buckets = new Map();
    dataRows.forEach((cells) => {
      if (cells.length <= Math.max(yearI, monthI, typeI, countI)) return;
      const year = toNumber(cells[yearI]);
      let mnum = monthNum(cells[monthI]);
      if (!mnum && quarterI < cells.length) {
        const q = String(cells[quarterI]).match(/[1-4]/);
        if (q) mnum = (Number(q[0]) - 1) * 3 + 2;
      }
      const count = toNumber(cells[countI]);
      if (year === null || !mnum || count === null) return;
      const type = cells[typeI].toLowerCase().includes('new') ? 'new'
        : cells[typeI].toLowerCase().includes('exist') ? 'existing' : '';
      if (!type) return;
      const quarter = Math.floor((mnum - 1) / 3) + 1;
      const key = `${Math.trunc(year)}|${quarter}`;
      const bucket = buckets.get(key) || new Map();
      const entry = bucket.get(mnum) || { new: 0, existing: 0 };
      entry[type] += count;
      bucket.set(mnum, entry);
      buckets.set(key, bucket);
    });
    const parsed = Array.from(buckets.entries()).sort(([a], [b]) => {
      const [ay, aq] = a.split('|').map(Number);
      const [by, bq] = b.split('|').map(Number);
      return ay - by || aq - bq;
    }).map(([key, bucket]) => {
      const [year, quarter] = key.split('|').map(Number);
      const vals = Array.from(bucket.values());
      const n = vals.length || 1;
      const newer = Math.round(vals.reduce((s, m) => s + m.new, 0) / n);
      const existing = Math.round(vals.reduce((s, m) => s + m.existing, 0) / n);
      return { period: `Q${quarter} ${year}`, new: newer, existing, total: newer + existing, months: n };
    });
    if (parsed.length) {
      const full = Math.max(...parsed.map((r) => r.months));
      while (parsed.length > 1 && parsed[parsed.length - 1].months < full) parsed.pop();
    }
    return parsed.map(({ months, ...r }) => r);
  }

  function parseMachineWide(data) {
    return data.map((cells, i) => {
      if (cells.length < 3) return null;
      if (i === 0 && looksHeader(cells, [1, 2])) return null;
      const newer = toNumber(cells[1]);
      const existing = toNumber(cells[2]);
      if (!cells[0] || newer === null || existing === null) return null;
      return { period: cells[0], new: newer, existing, total: newer + existing };
    }).filter(Boolean);
  }

  function computeStats(machine) {
    if (!machine.length) return { max_total: 0, max_period: '—', min_total: 0, min_period: '—', avg_pct_change: 0 };
    const max = machine.reduce((a, b) => a.total >= b.total ? a : b);
    const min = machine.reduce((a, b) => a.total <= b.total ? a : b);
    const changes = [];
    for (let i = 1; i < machine.length; i += 1) {
      if (machine[i - 1].total) changes.push((machine[i].total - machine[i - 1].total) / machine[i - 1].total * 100);
    }
    const avg = changes.length ? changes.reduce((a, b) => a + b, 0) / changes.length : 0;
    return { max_total: Math.round(max.total), max_period: max.period, min_total: Math.round(min.total), min_period: min.period, avg_pct_change: Math.round(avg * 10) / 10 };
  }

  function abbrevState(region) {
    const r = String(region || '').trim();
    if (US_STATES.has(r.toUpperCase())) return r.toUpperCase();
    return STATE_NAMES[r.toLowerCase()] || r;
  }

  function splitLocation(location) {
    const loc = String(location || '').trim();
    if (loc.includes(',')) {
      const [city, rest] = loc.split(/,(.*)/);
      const state = String(rest || '').trim().split(/\s+/)[0] || '';
      return { state: US_STATES.has(state.toUpperCase()) ? state.toUpperCase() : state, city: city.trim() };
    }
    const parts = loc.split(/\s+/);
    const tail = parts[parts.length - 1] || '';
    if (parts.length >= 2 && US_STATES.has(tail.toUpperCase())) {
      return { state: tail.toUpperCase(), city: parts.slice(0, -1).join(' ') };
    }
    return { state: '', city: loc };
  }

  function parseLocations(text, avoidDoubleCount) {
    const data = rows(text);
    if (!data.length) return [];
    const header = data[0].join(' ').toLowerCase();
    const looksGeo = header.includes('ip_city') || header.includes('ip_region') || (header.includes('measure value') && header.includes('city'))
      || data.slice(0, 5).some((cells) => {
        if (cells.length < 5 || toNumber(cells[cells.length - 1]) === null) return false;
        return ['machine', 'distinct', 'count'].some((key) => cells.slice(0, -1).join(' ').toLowerCase().includes(key));
      });
    if (looksGeo) {
      return parseGeoLocations(data, avoidDoubleCount);
    }
    return data.map((cells, i) => {
      if (cells.length < 2) return null;
      if (i === 0 && looksHeader(cells, [cells.length - 1])) return null;
      const count = toNumber(cells[cells.length - 1]);
      if (!cells[0] || count === null) return null;
      const split = splitLocation(cells[0]);
      if (looksLikeNonSite(split.city || cells[0])) return null;
      return { location: cells[0], state: split.state, city: split.city, count: Math.trunc(count) };
    }).filter(Boolean);
  }

  function parseGeoLocations(data, avoidDoubleCount) {
    const first = data[0];
    const firstJoined = first.join(' ').toLowerCase();
    const hasHeader = (firstJoined.includes('ip_') || firstJoined.includes('measure value') || firstJoined.includes('measure name') || firstJoined.includes('product_name') || firstJoined.includes('city'))
      && toNumber(first[first.length - 1]) === null;
    const header = hasHeader ? first : [];
    const dataRows = hasHeader ? data.slice(1) : data;
    let regionI = null, cityI = null, valueI = null, productI = null, measureI = null;
    if (hasHeader) {
      header.forEach((h, i) => {
        const low = h.toLowerCase();
        if (low.includes('region') || low.endsWith('state') || low === 'state') regionI = i;
        else if (low.includes('city')) cityI = i;
        else if (low.includes('product')) productI = i;
        else if (low.includes('measure name')) measureI = i;
        else if (low.includes('measure value') || low.includes('(measure)') || low.includes('count')) valueI = i;
      });
    } else {
      regionI = 1;
      cityI = 2;
      measureI = 3;
      productI = 4;
      valueI = first.length - 1;
    }
    if (cityI === null) return [];
    if (valueI === null) valueI = first.length - 1;
    const required = [regionI, cityI, valueI, measureI].filter((v) => v !== null);
    const useMax = avoidDoubleCount && productI !== null;
    const agg = new Map();
    dataRows.forEach((cells) => {
      if (cells.length <= Math.max(...required)) return;
      if (measureI !== null) {
        const measure = cells[measureI].toLowerCase();
        if (measure && !['machine', 'distinct', 'count'].some((k) => measure.includes(k))) return;
      }
      const region = regionI !== null ? cells[regionI].trim() : '';
      const city = cells[cityI].trim();
      const count = toNumber(cells[valueI]);
      if (!city || count === null) return;
      if (looksLikeNonSite(city)) return;
      const key = `${region}|${city}`;
      const current = agg.get(key) || 0;
      agg.set(key, useMax ? Math.max(current, Math.trunc(count)) : current + Math.trunc(count));
    });
    return Array.from(agg.entries()).map(([key, count]) => {
      const [region, city] = key.split('|');
      const state = abbrevState(region);
      return { location: state ? `${city}, ${state}` : city, state, city, count };
    });
  }

  function looksLikeNonSite(value) {
    const text = String(value || '').trim();
    if (!text) return true;
    const low = text.toLowerCase();
    if (['*', 'all', 'total', 'grand total', 'subtotal', 'null', 'none'].includes(low)) return true;
    if (/^\d{4}(?:\s+q[1-4])?$/.test(low)) return true;
    if (/^q[1-4](?:\s+\d{4})?$/.test(low)) return true;
    if (['new', 'existing', 'machine type', 'product_name', 'product version'].includes(low)) return true;
    return false;
  }

  function topLocations(locations, n = 5) {
    return [...locations]
      .filter((site) => !looksLikeNonSite(site.city || site.location))
      .sort((a, b) => b.count - a.count)
      .slice(0, n);
  }

  function parseVersions(text) {
    return rows(text).map((cells, i) => {
      if (cells.length < 3) return null;
      if (i === 0 && looksHeader(cells, [2])) return null;
      const users = toNumber(cells[2]);
      if (!cells[0] || users === null) return null;
      return { product: cells[0], version: cells[1], users: Math.trunc(users) };
    }).filter(Boolean);
  }

  function topVersions(versions, n = 5) {
    const groups = new Map();
    versions.forEach((v) => groups.set(v.product, [...(groups.get(v.product) || []), v]));
    return Array.from(groups.entries()).map(([product, items]) => {
      const total = items.reduce((s, v) => s + v.users, 0);
      const top = items.reduce((a, b) => a.users >= b.users ? a : b);
      return { product, version: top.version, users: top.users, product_total: total, pct: total ? Math.round(top.users / total * 100) : 0 };
    }).sort((a, b) => b.product_total - a.product_total).slice(0, n);
  }

  function parseFinite(text) {
    return rows(text).map((cells) => {
      if (cells.length >= 3) {
        const count = toNumber(cells[0]);
        return count === null ? null : { count: Math.trunc(count), license_type: normalizeFiniteLicenseType(cells[1]), license_name: cells.slice(2).join(' ') };
      }
      if (cells.length === 1) {
        const match = cells[0].match(/^(\d[\d,]*)\s+(.+)$/);
        if (!match) return null;
        return { count: Math.trunc(toNumber(match[1])), license_type: normalizeFiniteLicenseType(match[2]), license_name: '' };
      }
      return null;
    }).filter(Boolean);
  }

  const FINITE_LICENSE_TYPES = ['Concurrent', 'Named-User or Computer-Based'];
  const blankFiniteRow = () => ({ count: '', license_type: '', license_name: '' });
  const blankBundleRow = () => ({ bundle_name: '' });

  function normalizeFiniteLicenseType(value) {
    const text = String(value || '').trim();
    const low = text.toLowerCase().replace(/[-_]+/g, ' ').replace(/\s+/g, ' ');
    if (low.includes('concurrent')) return 'Concurrent';
    if (low.includes('named') || low.includes('computer based')) return 'Named-User or Computer-Based';
    return '';
  }

  function finiteRowsToText(editorRows) {
    return editorRows
      .filter((row) => row.count || row.license_type || row.license_name)
      .map((row) => `${row.count}\t${normalizeFiniteLicenseType(row.license_type)}\t${row.license_name}`)
      .join('\n');
  }

  function finiteEditorRowsFromText(text) {
    const parsed = rows(text).map((cells) => {
      if (cells.length >= 3) {
        return { count: cells[0], license_type: normalizeFiniteLicenseType(cells[1]), license_name: cells.slice(2).join(' ') };
      }
      if (cells.length === 1) {
        const match = cells[0].match(/^(\d[\d,]*)\s+(.+)$/);
        if (!match) return null;
        return { count: match[1], license_type: normalizeFiniteLicenseType(match[2]), license_name: '' };
      }
      return null;
    }).filter(Boolean);
    return parsed.length ? parsed : [blankFiniteRow()];
  }

  function bundleEditorRowsFromText(text) {
    const parsed = String(text || '').split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((bundle_name) => ({ bundle_name }));
    return parsed.length ? parsed : [blankBundleRow()];
  }

  function renderFiniteEditorRows(editorRows) {
    const container = $('finiteRows');
    if (!container) return;
    const rowsToRender = editorRows.length ? editorRows : [blankFiniteRow()];
    container.innerHTML = [
      '<div class="editor-header"><span>Count</span><span>License Type</span><span>License Name</span><span></span></div>',
      ...rowsToRender.map((row, i) => {
        const type = normalizeFiniteLicenseType(row.license_type);
        const options = [''].concat(FINITE_LICENSE_TYPES)
          .map((option) => `<option value="${esc(option)}"${option === type ? ' selected' : ''}>${esc(option || 'Select type')}</option>`)
          .join('');
        return `
        <div class="editor-row" data-index="${i}">
          <input data-field="count" inputmode="numeric" aria-label="Finite count" placeholder="142" value="${esc(row.count || '')}">
          <select data-field="license_type" aria-label="Finite license type">${options}</select>
          <input data-field="license_name" aria-label="Finite license name" placeholder="DIAdem Professional with DAC" value="${esc(row.license_name || '')}">
          <button class="remove-row" type="button">Remove</button>
        </div>`;
      })
    ].join('');
  }

  function renderBundleEditorRows(editorRows) {
    const container = $('bundleRows');
    if (!container) return;
    const rowsToRender = editorRows.length ? editorRows : [blankBundleRow()];
    container.innerHTML = [
      '<div class="editor-header"><span>Bundle Name</span><span></span></div>',
      ...rowsToRender.map((row, i) => `
        <div class="editor-row" data-index="${i}">
          <input data-field="bundle_name" aria-label="Unlimited bundle name" placeholder="EA Platform Bundle" value="${esc(row.bundle_name || '')}">
          <button class="remove-row" type="button">Remove</button>
        </div>`)
    ].join('');
  }

  function readFiniteEditorRows() {
    const container = $('finiteRows');
    if (!container) return [];
    return Array.from(container.querySelectorAll('.editor-row')).map((row) => ({
      count: row.querySelector('[data-field="count"]').value.trim(),
      license_type: normalizeFiniteLicenseType(row.querySelector('[data-field="license_type"]').value),
      license_name: row.querySelector('[data-field="license_name"]').value.trim()
    }));
  }

  function readBundleEditorRows() {
    const container = $('bundleRows');
    if (!container) return [];
    return Array.from(container.querySelectorAll('.editor-row')).map((row) => ({
      bundle_name: row.querySelector('[data-field="bundle_name"]').value.trim()
    }));
  }

  function syncFiniteTextFromEditor(renderNow = true) {
    $('finiteText').value = finiteRowsToText(readFiniteEditorRows());
    if (renderNow) render();
  }

  function syncBundleTextFromEditor(renderNow = true) {
    $('bundleText').value = readBundleEditorRows()
      .map((row) => row.bundle_name)
      .filter(Boolean)
      .join('\n');
    if (renderNow) render();
  }

  function setFiniteText(value, renderNow = true) {
    const editorRows = finiteEditorRowsFromText(value || '');
    $('finiteText').value = finiteRowsToText(editorRows);
    renderFiniteEditorRows(editorRows);
    if (renderNow) render();
  }

  function setBundleText(value, renderNow = true) {
    $('bundleText').value = value || '';
    renderBundleEditorRows(bundleEditorRowsFromText($('bundleText').value));
    if (renderNow) render();
  }

  function setupEditableTables() {
    setFiniteText($('finiteText').value, false);
    setBundleText($('bundleText').value, false);
    $('addFiniteRow').addEventListener('click', () => {
      renderFiniteEditorRows([...readFiniteEditorRows(), blankFiniteRow()]);
      syncFiniteTextFromEditor();
    });
    $('addBundleRow').addEventListener('click', () => {
      renderBundleEditorRows([...readBundleEditorRows(), blankBundleRow()]);
      syncBundleTextFromEditor();
    });
    $('finiteRows').addEventListener('input', () => syncFiniteTextFromEditor());
    $('finiteRows').addEventListener('change', () => syncFiniteTextFromEditor());
    $('bundleRows').addEventListener('input', () => syncBundleTextFromEditor());
    $('finiteRows').addEventListener('click', (event) => {
      const button = event.target.closest('.remove-row');
      if (!button) return;
      button.closest('.editor-row').remove();
      if (!$('finiteRows').querySelector('.editor-row')) renderFiniteEditorRows([blankFiniteRow()]);
      syncFiniteTextFromEditor();
    });
    $('bundleRows').addEventListener('click', (event) => {
      const button = event.target.closest('.remove-row');
      if (!button) return;
      button.closest('.editor-row').remove();
      if (!$('bundleRows').querySelector('.editor-row')) renderBundleEditorRows([blankBundleRow()]);
      syncBundleTextFromEditor();
    });
  }

  function cleanOcrLine(line) {
    return String(line || '').replace(/\s+/g, ' ').trim();
  }

  function parseContractDetails(text) {
    const lines = String(text || '').split(/\r?\n/).filter((line) => line.trim());
    const flat = lines.join(' ');
    const result = {
      service_id: '',
      customer: '',
      start_date: '',
      ep_term: '',
      flex_credits: '',
      support_level: '',
      debug_licenses: '',
      systemlink_snow: ''
    };
    let match = flat.match(/\bEA[-\s]?(\d{4,6})\b/i);
    if (match) result.service_id = `EA-${match[1]}`;

    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i];
      if (/\b(company|customer)\b/i.test(line)) {
        const tail = cleanOcrLine(line).replace(/^.*\b(company|customer)\b[^A-Za-z0-9]*\d*\s*/i, '').trim();
        if (tail.length >= 2) result.customer = tail.split(/\s{2,}/)[0].trim();
        else if (i + 1 < lines.length) result.customer = cleanOcrLine(lines[i + 1]);
        break;
      }
    }

    const dateRe = /\b(\d{1,2}[-/\s][A-Za-z]{3,9}[-/\s]\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})\b/;
    match = flat.match(dateRe);
    for (const line of lines) {
      if (/\b(start|effective)\b/i.test(line)) {
        const preferred = line.match(dateRe);
        if (preferred) {
          match = preferred;
          break;
        }
      }
    }
    if (match) result.start_date = match[1];

    match = flat.match(/(\d+)\s*(year|yr|month|mo)s?\b/i);
    if (match) {
      const unit = /^(year|yr)/i.test(match[2]) ? 'years' : 'months';
      result.ep_term = `${match[1]} ${unit}`;
    }

    match = flat.match(/FLEX\s*Credits?\D*([\d,]{2,})/i);
    if (match) result.flex_credits = match[1].trim();

    for (const line of lines) {
      const low = line.toLowerCase();
      if (low.includes('service id') || low.includes('flex')) continue;
      const support = cleanOcrLine(line).match(/\b(?:support(?:\s+level)?|services?\s+(?:level|info))\s*[:\-]?\s+(.+)$/i);
      if (support) {
        const tail = support[1].trim();
        if (tail.length >= 2 && tail.length <= 60) {
          result.support_level = tail;
          break;
        }
      }
    }

    match = flat.match(/debug[^\n]*?\b(yes|no|included|y|n)\b/i);
    if (match) {
      const val = match[1].toLowerCase();
      result.debug_licenses = ['yes', 'included', 'y'].includes(val) ? 'Yes' : 'No';
    }
    if (/system\s*link/i.test(flat) && /\b(snow|service\s*now)\b/i.test(flat)) {
      result.systemlink_snow = 'Yes';
    }
    return result;
  }

  const TYPE_KEYWORDS = [
    'named user or computer based', 'named-user or computer-based',
    'named user', 'named-user', 'computer based', 'computer-based',
    'concurrent', 'floating', 'node locked', 'node-locked', 'site'
  ];

  function splitTypeAndName(rest, raw) {
    if (String(raw || '').includes('\t')) {
      const parts = String(raw || '').split('\t').map((p) => p.trim()).filter(Boolean);
      if (parts.length >= 2) {
        return [parts[0].replace(/^\d[\d,]*\s*/, '').trim(), parts[1].trim()];
      }
    }
    const chunks = String(rest || '').split(/\s{2,}/).map((p) => p.trim()).filter(Boolean);
    if (chunks.length >= 2) return [chunks[0], chunks.slice(1).join(' ')];
    const low = String(rest || '').toLowerCase();
    for (const kw of TYPE_KEYWORDS) {
      if (low.startsWith(kw)) return [rest.slice(0, kw.length).trim(), rest.slice(kw.length).trim()];
    }
    return [String(rest || '').trim(), ''];
  }

  function parseFiniteLicensesOcr(text) {
    return String(text || '').split(/\r?\n/).map((raw) => {
      const line = cleanOcrLine(raw);
      if (!line) return null;
      if (/finite\s+quantity/i.test(line)) return null;
      if (/quantity\s+and\s+license/i.test(line)) return null;
      const match = line.match(/^(\d[\d,]*)\s+(.*)$/);
      if (!match) return null;
      const [license_type, license_name] = splitTypeAndName(match[2], raw);
      return {
        count: Math.trunc(toNumber(match[1]) || 0),
        license_type,
        license_name
      };
    }).filter(Boolean);
  }

  function cleanOcrLines(text) {
    return String(text || '').split(/\r?\n/)
      .map((line) => cleanOcrLine(line))
      .filter(Boolean);
  }

  function parseFiniteLicensesColumns(leftText, rightText) {
    const leftRows = cleanOcrLines(leftText).map((line) => {
      if (/finite\s+quantity|quantity\s+and\s+license|software\s+licenses/i.test(line)) return null;
      const match = line.match(/^(\d[\d,]*)\s+(.+)$/);
      if (!match) return null;
      return {
        count: Math.trunc(toNumber(match[1]) || 0),
        license_type: match[2].trim()
      };
    }).filter(Boolean);

    const names = cleanOcrLines(rightText).filter((line) => {
      if (/software\s+title|software\s+licenses|finite\s+quantity|quantity\s+and\s+license/i.test(line)) return false;
      if (/shall\s+be|unlimited\s+quantity|pricing\s+for/i.test(line)) return false;
      if (!/[A-Za-z]{3}/.test(line)) return false;
      return line.length >= 3;
    });

    if (!leftRows.length || !names.length) return [];
    return leftRows.map((row, i) => ({
      count: row.count,
      license_type: row.license_type,
      license_name: names[i] || ''
    })).filter((row) => row.license_name || row.license_type);
  }

  function parseUnlimitedBundlesOcr(text) {
    const bundles = [];
    String(text || '').split(/\r?\n/).forEach((raw) => {
      const line = cleanOcrLine(raw);
      if (!line || /unlimited\s+quantity/i.test(line)) return;
      let match = line.match(/(?:bundle\s*tit(?:le|ie|1e)|title)\s*[:\-]\s*(.+)$/i);
      if (match && match[1].trim()) {
        bundles.push(match[1].trim());
        return;
      }
      if (line.includes(':') && /bundle/i.test(line)) {
        const name = line.slice(line.indexOf(':') + 1).trim();
        if (name && !/unlimited\s+quantity/i.test(name)) bundles.push(name);
      }
    });
    const seen = new Set();
    return bundles.filter((name) => {
      const key = name.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function parseUnlimitedBundlesColumns(_leftText, rightText) {
    return parseUnlimitedBundlesOcr(rightText);
  }

  function extractOcrWords(data) {
    const words = [];
    (data.blocks || []).forEach((block) => {
      (block.paragraphs || []).forEach((para) => {
        (para.lines || []).forEach((line) => {
          (line.words || []).forEach((word) => {
            if (word.text) words.push({ text: word.text, conf: Number(word.confidence) });
          });
        });
      });
    });
    return words;
  }

  function fieldConfidence(words, value) {
    if (!value || !words.length) return null;
    const tokens = String(value).split(/[\s,]+/).map((t) => t.trim()).filter((t) => t.length >= 2);
    if (!tokens.length) return null;
    const lookup = new Map();
    words.forEach((word) => {
      const key = String(word.text || '').toLowerCase().replace(/^[.,:;]+|[.,:;]+$/g, '');
      if (!key) return;
      const arr = lookup.get(key) || [];
      arr.push(word.conf);
      lookup.set(key, arr);
    });
    const confs = [];
    tokens.forEach((token) => {
      const vals = lookup.get(token.toLowerCase().replace(/^[.,:;]+|[.,:;]+$/g, ''));
      if (vals && vals.length) confs.push(Math.max(...vals));
    });
    return confs.length ? confs.reduce((a, b) => a + b, 0) / confs.length : null;
  }

  function parseDate(value) {
    const s = String(value || '').trim();
    if (!s) return null;
    let m = s.match(/(\d{1,2})[-\s]([A-Za-z]{3})[A-Za-z]*[-\s](\d{4})/);
    if (m) {
      const mon = MONTHS[m[2].slice(0, 3).toLowerCase()];
      if (mon) return new Date(Number(m[3]), mon - 1, Number(m[1]));
    }
    m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
    if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    m = s.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$/);
    if (m) {
      const year = Number(m[3].length === 2 ? `20${m[3]}` : m[3]);
      return new Date(year, Number(m[1]) - 1, Number(m[2]));
    }
    const parsed = new Date(s);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function parseTermYears(value) {
    const s = String(value || '').toLowerCase();
    const n = toNumber(s);
    if (n === null) return null;
    return s.includes('month') ? n / 12 : n;
  }

  function addYears(start, years) {
    const whole = Math.trunc(years);
    const fracDays = Math.round((years - whole) * 365);
    const bumped = new Date(start.getFullYear() + whole, start.getMonth(), start.getDate());
    bumped.setDate(bumped.getDate() + fracDays);
    return bumped;
  }

  function computeEndDate(start, termYears) {
    if (!start || termYears === null) return null;
    const end = addYears(start, termYears);
    end.setDate(end.getDate() - 1);
    return end;
  }

  function computePhase(start, termYears) {
    const end = computeEndDate(start, termYears);
    if (!start || termYears === null || !end) return { phase: '', hint: '' };
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (today < start) return { phase: 'Not started', hint: 'Term has not begun' };
    if (today > end) return { phase: 'Expired', hint: 'Past end date' };
    const total = Math.max(1, end - start);
    const elapsed = today - start;
    const phase = elapsed / total < 0.5 ? 'First Half' : 'Second Half';
    const n = Math.max(1, Math.round(termYears));
    const yearX = Math.min(Math.floor(elapsed / (365 * 24 * 3600 * 1000)) + 1, n);
    return { phase, hint: `Year ${yearX} of ${n}` };
  }

  function fmtDate(date) {
    if (!date) return '';
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).replace(/ /g, '-').toUpperCase();
  }

  function truthy(value) {
    if (value === true) return true;
    return ['1', 'true', 'yes', 'y', 'on'].includes(String(value || '').trim().toLowerCase());
  }

  function num(value) {
    return toNumber(value);
  }

  function generateInsights(data) {
    const insights = [];
    const machine = data.machine.df;
    const stats = data.machine.stats;
    const renewal = data.ea_end_date ? ` Tie this to the EA end date (${data.ea_end_date}).` : '';
    if (machine.length) {
      const first = machine[0].total;
      const last = machine[machine.length - 1].total;
      const avg = stats.avg_pct_change;
      if (avg > 1) insights.push({ p: 3, cat: 'Adoption trend', text: `Healthy growth: total machines rose from ${fmt(first)} to ${fmt(last)} (avg +${avg.toFixed(1)}% per period). Expansion story supports a strong renewal.${renewal}` });
      else if (avg < -1) insights.push({ p: 1, cat: 'Adoption trend', text: `RISK - declining usage: total machines fell from ${fmt(first)} to ${fmt(last)} (avg ${avg.toFixed(1)}% per period). Investigate churn before renewal.${renewal}` });
      else insights.push({ p: 2, cat: 'Adoption trend', text: `Flat usage: total machines roughly steady around ${fmt(last)} (avg ${avg >= 0 ? '+' : ''}${avg.toFixed(1)}% per period). Look for an expansion lever.${renewal}` });
      const latest = machine[machine.length - 1];
      const newPct = latest.total ? latest.new / latest.total * 100 : 0;
      if (newPct < 10) insights.push({ p: 2, cat: 'New vs existing', text: `Churn signal: only ${newPct.toFixed(0)}% of current machines are new (${fmt(latest.new)} new vs ${fmt(latest.existing)} existing). Low new-seat flow weakens the expansion case.` });
      else if (newPct > 40) insights.push({ p: 3, cat: 'New vs existing', text: `Strong onboarding: ${newPct.toFixed(0)}% of machines are new (${fmt(latest.new)} new vs ${fmt(latest.existing)} existing). Active rollout in progress.` });
    }
    const totalFinite = data.finite_licenses.reduce((s, r) => s + (Number(r.count) || 0), 0);
    const lastMachines = machine.length ? machine[machine.length - 1].total : stats.max_total;
    if (totalFinite) {
      const util = lastMachines / totalFinite * 100;
      if (util >= 90) insights.push({ p: 1, cat: 'License utilization', text: `UPSELL - near/over capacity: ~${fmt(lastMachines)} machines against ${fmt(totalFinite)} finite licenses (${util.toFixed(0)}% utilized). Raise an expansion conversation.${renewal}` });
      else if (util <= 40) insights.push({ p: 2, cat: 'License utilization', text: `ADOPTION RISK - low utilization: ~${fmt(lastMachines)} machines against ${fmt(totalFinite)} finite licenses (${util.toFixed(0)}% utilized). Drive adoption to protect the renewal.${renewal}` });
    }
    data.versions_top5.slice(0, 3).forEach((v) => {
      const oldYear = String(v.version).match(/\d{4}/);
      if (v.pct >= 60 && oldYear && Number(oldYear[0]) <= 2022) insights.push({ p: 2, cat: 'Version health', text: `Upgrade conversation: ${v.pct}% of ${v.product} users (${fmt(v.users)}) are on ${v.version}, an older release. Plan an upgrade path.` });
    });
    const purchased = num(data.credits.purchased);
    const used = num(data.credits.used) || 0;
    if (purchased) {
      const pct = used / purchased * 100;
      if (pct < 50) insights.push({ p: pct < 25 ? 1 : 2, cat: 'Training credits', text: `Unused value: only ${pct.toFixed(0)}% of ${fmt(purchased)} FLEX/training credits used (${fmt(purchased - used)} remaining). Schedule training to burn credits before they expire.${renewal}` });
    }
    if (data.locations_top5.length) {
      const total = data.locations_top5.reduce((s, l) => s + l.count, 0);
      const top = data.locations_top5[0];
      const pct = total ? top.count / total * 100 : 0;
      if (pct >= 50) insights.push({ p: 3, cat: 'Location concentration', text: `Concentration risk: ${top.city || top.location} holds ${pct.toFixed(0)}% of machines across the top sites. A single-site dependency is a renewal risk - broaden the footprint.` });
    }
    if (data.ea_end_date) insights.push({ p: 4, cat: 'Renewal context', text: `EA for ${data.customer || 'the customer'} ends ${data.ea_end_date}.${data.phase ? ` Currently ${data.phase}.` : ''} Align the actions above to a renewal/expansion plan ahead of that date.` });
    return insights.sort((a, b) => a.p - b.p);
  }

  function chartSvg(machine) {
    if (!machine.length) return '<div class="empty">No machine-count data</div>';
    const width = 340, height = 205, padL = 34, padR = 8, padT = 8, padB = 20;
    const totals = machine.map((r) => r.total);
    const periods = machine.map((r) => r.period);
    let lo = Math.min(...totals), hi = Math.max(...totals);
    let span = hi - lo || 1;
    lo -= span * 0.08; hi += span * 0.08; span = hi - lo;
    const iw = width - padL - padR, ih = height - padT - padB;
    const x = (i) => padL + iw * i / Math.max(machine.length - 1, 1);
    const y = (v) => padT + ih * (1 - (v - lo) / span);
    const pts = totals.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    const peakI = totals.indexOf(Math.max(...totals));
    const grid = [0, .5, 1].map((f) => `<line x1="${padL}" y1="${(padT + ih * f).toFixed(1)}" x2="${width - padR}" y2="${(padT + ih * f).toFixed(1)}" stroke="#f0f0f0"/>`).join('');
    return `<svg viewBox="0 0 ${width} ${height}" width="100%" role="img" aria-label="Total machines over time">${grid}<polyline points="${pts}" fill="none" stroke="#18af7c" stroke-width="2.5"/><circle cx="${x(peakI).toFixed(1)}" cy="${y(totals[peakI]).toFixed(1)}" r="5" fill="#18af7c" stroke="#fff" stroke-width="2"/><text x="${x(0).toFixed(0)}" y="${height - 5}" font-size="8" fill="#6e6e6e">${esc(periods[0])}</text><text x="${x(machine.length - 1).toFixed(0)}" y="${height - 5}" text-anchor="end" font-size="8" fill="#6e6e6e">${esc(periods[periods.length - 1])}</text></svg>`;
  }

  function card(title, body, extra = '') {
    return `<div class="card ${extra}"><div class="card-title">${esc(title)}</div><div class="card-body">${body}</div></div>`;
  }

  function table(headers, rowsHtml, className = '') {
    const cls = className ? ` class="${esc(className)}"` : '';
    return `<table${cls}><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join('')}</tr>${rowsHtml}</table>`;
  }

  function renderSlide(data) {
    const stats = data.machine.stats;
    const bundles = data.bundles.length ? data.bundles.slice(0, 5).map((b) => `<div class="pill">${esc(b)}</div>`).join('') : '<div class="empty">No bundles provided</div>';
    const finiteClass = data.finite_licenses.length > 8 ? 'finite-table ultra-dense' : data.finite_licenses.length > 5 ? 'finite-table dense' : 'finite-table';
    const finiteRows = data.finite_licenses.length ? data.finite_licenses.map((r) => `<tr><td class="qty">${fmt(r.count)}</td><td>${esc(r.license_name)}</td><td class="muted">${esc(r.license_type)}</td></tr>`).join('') : '';
    const finite = finiteRows ? table(['QTY', 'LICENSE', 'TYPE'], finiteRows, finiteClass) : '<div class="empty">No finite licenses provided</div>';
    const locRows = data.locations_top5.map((r) => `<tr><td>${esc(r.state)}</td><td>${esc(r.city || r.location)}</td><td class="qty">${fmt(r.count)}</td></tr>`).join('');
    const verRows = data.versions_top5.map((r) => `<tr><td>${esc(r.product)}</td><td>${fmt(r.product_total ?? r.users)}</td><td>${esc(r.version)}</td><td class="qty">${r.pct}%</td></tr>`).join('');
    return `
      <div class="slide-header"><div><div class="slide-label">Enterprise Agreement</div><div class="slide-title">${esc(data.service_id || 'EA')} · ${esc(data.customer || 'Customer')}</div></div><div class="updated">Updated ${esc(data.updated_date)}</div></div>
      <div class="slide-grid">
        <div class="col left">
          ${card('Contract Details', [['EA End Date', data.ea_end_date], ['Term Duration', data.ep_term], ['Contract Scope', data.contract_scope], ['Phase', data.phase]].map(([k, v]) => `<div class="krow"><span class="key">${esc(k)}</span><span class="value">${esc(v || '—')}</span></div>`).join(''), 'contract-card')}
          ${card('Bundle Information', bundles)}
          ${card('NI SW Licenses (Finite Qty)', finite)}
        </div>
        <div class="col center">
          ${card('Software Usage Trend', chartSvg(data.machine.df))}
          ${card('Software Usage Data', `<div class="stats"><div class="stat accent"><div class="big">${fmt(stats.max_total)}</div><div class="lbl">Peak machines</div><div class="per">${esc(stats.max_period)}</div></div><div class="stat"><div class="big">${fmt(stats.min_total)}</div><div class="lbl">Min machines</div><div class="per">${esc(stats.min_period)}</div></div></div><div class="strip"><span>Avg quarterly increase</span><span class="pct">${stats.avg_pct_change >= 0 ? '+' : ''}${stats.avg_pct_change.toFixed(1)}%</span></div>`)}
        </div>
        <div class="col right">
          ${card('Top Site Locations', locRows ? table(['STATE', 'CITY', 'MACHINES'], locRows, 'site-table') : '<div class="empty">No location data</div>')}
          ${card('Version Usage', verRows ? table(['PRODUCT', 'TOTAL', 'TOP VER.', '%'], verRows, 'version-table') : '<div class="empty">No version data</div>')}
          ${card('Training Credit Usage', `<div class="stats3"><div><div class="lbl">Purchased</div><div class="med">${fmt(data.credits.purchased)}</div></div><div><div class="lbl">Used</div><div class="med">${fmt(data.credits.used)}</div></div><div><div class="lbl">Utilized</div><div class="med">${data.credits.pct_used === '—' ? '—' : `${data.credits.pct_used}%`}</div></div></div>`)}
          ${card('Technical Support', `<b>${esc(data.support.tier || '—')}</b><span class="scope">${esc(data.support.scope || '')}</span>${data.support.systemlink_snow ? '<b class="snow">SystemLink Support (SNOW)</b>' : ''}`, 'support-card')}
        </div>
      </div>`;
  }

  function buildData() {
    const machine = parseMachine($('machineText').value);
    const locations = parseLocations($('locationsText').value, $('avoidLocationDoubleCount').checked);
    const versions = parseVersions($('versionsText').value);
    const purchased = toNumber($('creditsPurchased').value);
    const used = toNumber($('creditsUsed').value);
    const pctUsed = purchased && used !== null && purchased > 0 ? Math.round(used / purchased * 100) : '—';
    const systemlinkSnow = $('systemlinkSnow').checked;
    const supportScope = $('supportScope').value.trim();
    return {
      service_id: $('serviceId').value.trim(),
      customer: $('customer').value.trim(),
      updated_date: fmtDate(new Date()),
      ea_end_date: $('endDate').value.trim(),
      ep_term: $('epTerm').value.trim(),
      contract_scope: $('contractScope').value.trim(),
      phase: $('phase').value.trim(),
      debug_licenses: $('debugLicenses').value,
      bundles: $('bundleText').value.split(/\r?\n/).map((s) => s.trim()).filter(Boolean),
      finite_licenses: parseFinite($('finiteText').value),
      machine: { df: machine, stats: computeStats(machine) },
      locations_top5: topLocations(locations),
      versions_top5: topVersions(versions),
      credits: { purchased: $('creditsPurchased').value.trim() || '—', used: $('creditsUsed').value.trim() || '—', pct_used: pctUsed },
      support: { tier: $('supportTier').value.trim() || '—', scope: supportScope, systemlink_snow: systemlinkSnow }
    };
  }

  function warnings(data) {
    const items = [];
    if (!data.machine.df.length) items.push('Machine Count did not parse. Paste the Machine Count table before relying on the preview.');
    if (!data.customer) items.push('Customer / Company is blank.');
    if (!data.ea_end_date) items.push('EA End Date is blank or could not be computed.');
    if (!data.locations_top5.length) items.push('Locations did not parse; Top Site Locations will be empty.');
    if (!data.versions_top5.length) items.push('Usage Versions did not parse; Version Usage will be empty.');
    if (data.credits.pct_used === '—') items.push('Enter purchased and used credits to calculate utilization.');
    return items;
  }

  function setOcrStatus(key, message) {
    const meta = SHOT_META[key];
    if (meta && $(meta.statusId)) $(meta.statusId).textContent = message || '';
  }

  function handleScreenshotInput(key) {
    const meta = SHOT_META[key];
    const input = $(meta.inputId);
    const preview = $(meta.previewId);
    const file = input.files && input.files[0];
    uploadedShots[key] = null;
    if ($(meta.rawId)) $(meta.rawId).value = '';
    setOcrStatus(key, '');
    if (!file) {
      preview.textContent = 'No image selected';
      render();
      return;
    }
    if (!/^image\//.test(file.type)) {
      preview.textContent = 'Choose an image file';
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const image = new Image();
      image.onload = () => {
        uploadedShots[key] = {
          label: meta.label,
          name: file.name,
          dataUrl: String(reader.result),
          width: image.naturalWidth || image.width,
          height: image.naturalHeight || image.height
        };
        preview.innerHTML = `<img src="${esc(reader.result)}" alt="${esc(meta.label)}">`;
        render();
        if (key === 'a' && $('autoContractOcr') && $('autoContractOcr').checked) {
          setTimeout(() => runOcr('a'), 0);
        }
      };
      image.onerror = () => {
        preview.textContent = 'Could not preview image';
      };
      image.src = String(reader.result);
    };
    reader.readAsDataURL(file);
  }

  function loadImageElement(dataUrl) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error('Could not load image for OCR.'));
      image.src = dataUrl;
    });
  }

  function imageToCanvas(dataUrl) {
    return loadImageElement(dataUrl).then((image) => {
      const scale = image.width < 2200 ? Math.min(4, 2200 / Math.max(image.width, 1)) : 1.25;
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(image.width * scale);
      canvas.height = Math.round(image.height * scale);
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < img.data.length; i += 4) {
        const gray = Math.round(img.data[i] * 0.299 + img.data[i + 1] * 0.587 + img.data[i + 2] * 0.114);
        const boosted = Math.max(0, Math.min(255, (gray - 128) * 1.22 + 128));
        img.data[i] = boosted;
        img.data[i + 1] = boosted;
        img.data[i + 2] = boosted;
      }
      ctx.putImageData(img, 0, 0);
      return canvas;
    });
  }

  function clustersFromFlags(flags) {
    const clusters = [];
    let start = null;
    flags.forEach((flag, i) => {
      if (flag && start === null) start = i;
      if ((!flag || i === flags.length - 1) && start !== null) {
        const end = flag && i === flags.length - 1 ? i : i - 1;
        clusters.push({ start, end, center: Math.round((start + end) / 2), size: end - start + 1 });
        start = null;
      }
    });
    return clusters;
  }

  function imageDataAtNaturalSize(image) {
    const canvas = document.createElement('canvas');
    canvas.width = image.naturalWidth || image.width;
    canvas.height = image.naturalHeight || image.height;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    return ctx.getImageData(0, 0, canvas.width, canvas.height);
  }

  function grayFromData(data, idx) {
    return Math.round(data[idx] * 0.299 + data[idx + 1] * 0.587 + data[idx + 2] * 0.114);
  }

  function contentBounds(imageData, threshold = 235) {
    const { data, width, height } = imageData;
    let minX = width, minY = height, maxX = 0, maxY = 0;
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const i = (y * width + x) * 4;
        if (grayFromData(data, i) < threshold && data[i + 3] > 10) {
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
        }
      }
    }
    if (minX > maxX || minY > maxY) return { x: 0, y: 0, w: width, h: height };
    const pad = 8;
    minX = Math.max(0, minX - pad);
    minY = Math.max(0, minY - pad);
    maxX = Math.min(width - 1, maxX + pad);
    maxY = Math.min(height - 1, maxY + pad);
    return { x: minX, y: minY, w: maxX - minX + 1, h: maxY - minY + 1 };
  }

  function detectTableGeometry(image) {
    const imageData = imageDataAtNaturalSize(image);
    const { data, width, height } = imageData;
    const box = contentBounds(imageData);
    const rowFlags = [];
    for (let y = box.y; y < box.y + box.h; y += 1) {
      let dark = 0;
      for (let x = box.x; x < box.x + box.w; x += 1) {
        if (grayFromData(data, (y * width + x) * 4) < 150) dark += 1;
      }
      rowFlags.push(dark > box.w * 0.42);
    }
    const rowClusters = clustersFromFlags(rowFlags).map((c) => ({
      start: c.start + box.y,
      end: c.end + box.y,
      center: c.center + box.y,
      size: c.size
    }));
    if (rowClusters.length < 3) return null;

    const tableY0 = Math.max(0, rowClusters[0].start - 4);
    const tableY1 = Math.min(height - 1, rowClusters[rowClusters.length - 1].end + 4);
    const tableH = Math.max(1, tableY1 - tableY0 + 1);
    const colFlags = [];
    for (let x = box.x; x < box.x + box.w; x += 1) {
      let dark = 0;
      for (let y = tableY0; y <= tableY1; y += 1) {
        if (grayFromData(data, (y * width + x) * 4) < 150) dark += 1;
      }
      colFlags.push(dark > tableH * 0.42);
    }
    const colClusters = clustersFromFlags(colFlags).map((c) => ({
      start: c.start + box.x,
      end: c.end + box.x,
      center: c.center + box.x,
      size: c.size
    }));

    let leftX = box.x;
    let rightX = box.x + box.w - 1;
    let splitX = box.x + Math.round(box.w / 2);
    if (colClusters.length >= 3) {
      leftX = colClusters[0].center;
      rightX = colClusters[colClusters.length - 1].center;
      const mid = (leftX + rightX) / 2;
      splitX = colClusters.slice(1, -1).reduce((best, c) => (
        Math.abs(c.center - mid) < Math.abs(best.center - mid) ? c : best
      ), colClusters[1]).center;
    }
    if (splitX - leftX < 80 || rightX - splitX < 80) return null;
    return { leftX, splitX, rightX, y0: tableY0, y1: tableY1 };
  }

  function removeLongLines(img, width, height) {
    const data = img.data;
    const rowLines = [];
    const colLines = [];
    for (let y = 0; y < height; y += 1) {
      let dark = 0;
      for (let x = 0; x < width; x += 1) if (data[(y * width + x) * 4] < 128) dark += 1;
      if (dark > width * 0.55) rowLines.push(y);
    }
    for (let x = 0; x < width; x += 1) {
      let dark = 0;
      for (let y = 0; y < height; y += 1) if (data[(y * width + x) * 4] < 128) dark += 1;
      if (dark > height * 0.55) colLines.push(x);
    }
    rowLines.forEach((row) => {
      for (let y = Math.max(0, row - 1); y <= Math.min(height - 1, row + 1); y += 1) {
        for (let x = 0; x < width; x += 1) {
          const i = (y * width + x) * 4;
          data[i] = 255; data[i + 1] = 255; data[i + 2] = 255;
        }
      }
    });
    colLines.forEach((col) => {
      for (let x = Math.max(0, col - 1); x <= Math.min(width - 1, col + 1); x += 1) {
        for (let y = 0; y < height; y += 1) {
          const i = (y * width + x) * 4;
          data[i] = 255; data[i + 1] = 255; data[i + 2] = 255;
        }
      }
    });
  }

  function preprocessCrop(image, crop, options = {}) {
    const targetWidth = options.targetWidth || 1800;
    const scale = Math.min(5, Math.max(2.5, targetWidth / Math.max(crop.w, 1)));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(crop.w * scale);
    canvas.height = Math.round(crop.h * scale);
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, crop.x, crop.y, crop.w, crop.h, 0, 0, canvas.width, canvas.height);
    const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const threshold = options.threshold || 210;
    for (let i = 0; i < img.data.length; i += 4) {
      const value = grayFromData(img.data, i) < threshold ? 0 : 255;
      img.data[i] = value;
      img.data[i + 1] = value;
      img.data[i + 2] = value;
      img.data[i + 3] = 255;
    }
    if (options.removeLines) removeLongLines(img, canvas.width, canvas.height);
    ctx.putImageData(img, 0, 0);
    return canvas;
  }

  async function tableColumnCanvases(dataUrl) {
    const image = await loadImageElement(dataUrl);
    const geom = detectTableGeometry(image);
    if (!geom) return null;
    const pad = 6;
    const imgH = image.naturalHeight || image.height;
    const y = Math.max(0, geom.y0 - pad);
    const h = Math.min(imgH, geom.y1 + pad) - y;
    const left = {
      x: Math.max(0, geom.leftX + pad),
      y,
      w: Math.max(1, geom.splitX - geom.leftX - 2 * pad),
      h
    };
    const right = {
      x: Math.max(0, geom.splitX + pad),
      y,
      w: Math.max(1, geom.rightX - geom.splitX - 2 * pad),
      h
    };
    return {
      left: preprocessCrop(image, left, { targetWidth: 1900, threshold: 210, removeLines: true }),
      right: preprocessCrop(image, right, { targetWidth: 2100, threshold: 210, removeLines: true })
    };
  }

  async function recognizeCanvas(worker, canvas, psm = '6') {
    await worker.setParameters({
      preserve_interword_spaces: '1',
      tessedit_pageseg_mode: String(psm),
      user_defined_dpi: '300'
    });
    const result = await worker.recognize(canvas, {}, { text: true, blocks: true });
    return {
      text: result.data.text || '',
      words: extractOcrWords(result.data)
    };
  }

  async function recognizeShot(key, shot, worker) {
    if (key === 'b' || key === 'c') {
      const columns = await tableColumnCanvases(shot.dataUrl);
      if (columns) {
        setOcrStatus(key, 'OCR table left column');
        const left = await recognizeCanvas(worker, columns.left, '6');
        setOcrStatus(key, 'OCR table right column');
        const right = await recognizeCanvas(worker, columns.right, '6');
        return {
          text: `LEFT COLUMN\n${left.text.trim()}\n\nRIGHT COLUMN\n${right.text.trim()}`.trim(),
          words: [...left.words, ...right.words],
          leftText: left.text,
          rightText: right.text,
          tableMode: true
        };
      }
    }
    const canvas = await imageToCanvas(shot.dataUrl);
    return recognizeCanvas(worker, canvas, key === 'a' ? '6' : '11');
  }

  async function getOcrWorker(activeKey) {
    if (!window.Tesseract || !window.Tesseract.createWorker) {
      throw new Error('Browser OCR failed to load.');
    }
    if (!ocrWorkerPromise) {
      ocrWorkerPromise = window.Tesseract.createWorker('eng', 1, {
        workerPath: 'assets/vendor/tesseract/worker.min.js',
        corePath: 'assets/vendor/tesseract/core',
        langPath: 'assets/vendor/tesseract/lang',
        cacheMethod: 'none',
        workerBlobURL: false,
        logger: (m) => {
          if (!activeKey || !m || !m.status) return;
          const pct = typeof m.progress === 'number' ? ` ${Math.round(m.progress * 100)}%` : '';
          setOcrStatus(activeKey, `${m.status}${pct}`);
        }
      }).then(async (worker) => {
        await worker.setParameters({
          preserve_interword_spaces: '1',
          user_defined_dpi: '300'
        });
        return worker;
      }).catch((err) => {
        ocrWorkerPromise = null;
        throw err;
      });
    }
    return ocrWorkerPromise;
  }

  function applyContractOcr(detail) {
    const parsed = parseContractDetails(detail.text);
    if (parsed.service_id) $('serviceId').value = parsed.service_id;
    if (parsed.customer) $('customer').value = parsed.customer;
    if (parsed.start_date) $('startDate').value = parsed.start_date;
    if (parsed.ep_term) $('epTerm').value = parsed.ep_term;
    if (parsed.flex_credits) $('creditsPurchased').value = parsed.flex_credits;
    if (parsed.support_level) $('supportTier').value = parsed.support_level;
    if (parsed.debug_licenses) $('debugLicenses').value = parsed.debug_licenses;
    if (parsed.systemlink_snow) $('systemlinkSnow').checked = true;
    recomputeDates();
    const labels = {
      service_id: 'EA/EP Service ID',
      customer: 'Customer / Company',
      start_date: 'Start / Effective Date',
      ep_term: 'EP Term',
      flex_credits: 'FLEX credits purchased',
      support_level: 'Support tier',
      debug_licenses: 'Debug licenses'
    };
    const low = [];
    const missing = [];
    Object.entries(labels).forEach(([key, label]) => {
      const value = parsed[key];
      if (!value) {
        missing.push(label);
        return;
      }
      const conf = fieldConfidence(detail.words, value);
      if (conf !== null && conf < 70) low.push(`${label} (${Math.round(conf)}%)`);
    });
    const notes = [];
    if (low.length) notes.push(`Low confidence: ${low.join(', ')}`);
    if (missing.length) notes.push(`Not found: ${missing.join(', ')}`);
    setOcrStatus('a', notes.join(' | ') || 'OCR applied');
  }

  function applyFiniteOcr(detail) {
    let parsed = detail.leftText || detail.rightText
      ? parseFiniteLicensesColumns(detail.leftText || '', detail.rightText || '')
      : parseFiniteLicensesOcr(detail.text);
    if (!parsed.length) parsed = parseFiniteLicensesOcr(detail.text);
    if (parsed.length) {
      setFiniteText(parsed.map((r) => `${r.count}\t${r.license_type}\t${r.license_name}`).join('\n'), false);
      setOcrStatus('b', `OCR applied ${parsed.length} row${parsed.length === 1 ? '' : 's'}${detail.tableMode ? ' from table columns' : ''}`);
    } else {
      setOcrStatus('b', 'OCR finished; no finite rows found');
    }
    render();
  }

  function applyBundleOcr(detail) {
    let parsed = detail.leftText || detail.rightText
      ? parseUnlimitedBundlesColumns(detail.leftText || '', detail.rightText || '')
      : parseUnlimitedBundlesOcr(detail.text);
    if (!parsed.length) parsed = parseUnlimitedBundlesOcr(detail.text);
    if (parsed.length) {
      setBundleText(parsed.join('\n'), false);
      setOcrStatus('c', `OCR applied ${parsed.length} bundle${parsed.length === 1 ? '' : 's'}${detail.tableMode ? ' from table columns' : ''}`);
    } else {
      setOcrStatus('c', 'OCR finished; no bundles found');
    }
    render();
  }

  async function runOcr(key) {
    const meta = SHOT_META[key];
    const shot = uploadedShots[key];
    if (!shot) {
      setOcrStatus(key, 'Select an image first');
      return;
    }
    setOcrStatus(key, 'Preparing image');
    try {
      const worker = await getOcrWorker(key);
      const detail = await recognizeShot(key, shot, worker);
      if ($(meta.rawId)) $(meta.rawId).value = detail.text;
      if (key === 'a') applyContractOcr(detail);
      else if (key === 'b') applyFiniteOcr(detail);
      else applyBundleOcr(detail);
    } catch (err) {
      setOcrStatus(key, `OCR error: ${err.message || err}`);
    }
  }

  function render() {
    const data = buildData();
    $('warnings').innerHTML = warnings(data).map((w) => `<div class="warning">${esc(w)}</div>`).join('');
    $('slidePreview').innerHTML = renderSlide(data);
    const insightItems = generateInsights(data);
    $('insights').innerHTML = insightItems.length
      ? insightItems.map((i) => `<div class="insight"><strong>${esc(i.cat)}</strong>${esc(i.text)}</div>`).join('')
      : '<p class="small">Not enough data to generate insights yet.</p>';
  }

  function recomputeDates() {
    const start = parseDate($('startDate').value);
    const term = parseTermYears($('epTerm').value);
    const end = computeEndDate(start, term);
    const ph = computePhase(start, term);
    if (end) $('endDate').value = fmtDate(end);
    if (ph.phase) $('phase').value = ph.phase;
    render();
  }

  function loadExamples() {
    $('machineText').value = EXAMPLES.machine;
    $('locationsText').value = EXAMPLES.locations;
    $('versionsText').value = EXAMPLES.versions;
    setFiniteText(EXAMPLES.finite, false);
    setBundleText(EXAMPLES.bundles, false);
    $('serviceId').value = 'EA-15725';
    $('customer').value = 'Sample Customer';
    $('startDate').value = '02-JAN-2026';
    $('epTerm').value = '3 years';
    $('contractScope').value = 'All NI software';
    $('supportTier').value = 'Enterprise Support';
    $('supportScope').value = 'All Users';
    $('systemlinkSnow').checked = false;
    $('creditsPurchased').value = '20,000';
    $('creditsUsed').value = '7,500';
    recomputeDates();
  }

  function safeFileName(value) {
    return String(value || 'EA_slide').replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '_') || 'EA_slide';
  }

  function suggestProfileName() {
    return safeFileName([$('serviceId').value.trim(), $('customer').value.trim()].filter(Boolean).join(' ') || 'profile');
  }

  function downloadBlob(blob, fileName) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.dataset.interception = 'off';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }, 100);
  }

  function currentProfilePayload() {
    return {
      version: 2,
      app: 'EA Slide Builder Pages',
      saved_at: new Date().toISOString(),
      texts: {
        machine_text: $('machineText').value,
        locations_text: $('locationsText').value,
        versions_text: $('versionsText').value
      },
      fields: {
        f_service_id: $('serviceId').value,
        f_customer: $('customer').value,
        f_start_date: $('startDate').value,
        f_ep_term: $('epTerm').value,
        f_end_date: $('endDate').value,
        f_phase: $('phase').value,
        f_phase_hint: '',
        f_contract_scope: $('contractScope').value,
        f_debug: $('debugLicenses').value,
        f_support_tier: $('supportTier').value,
        f_support_scope: $('supportScope').value,
        f_systemlink_snow: $('systemlinkSnow').checked,
        f_flex_purchased: $('creditsPurchased').value,
        f_flex_used: $('creditsUsed').value
      },
      settings: {
        avoid_location_double_count: $('avoidLocationDoubleCount').checked
      },
      finite_licenses: parseFinite($('finiteText').value),
      bundles: $('bundleText').value.split(/\r?\n/).map((s) => s.trim()).filter(Boolean)
    };
  }

  function dataFromProfilePayload(payload) {
    const texts = payload.texts || {};
    const fields = payload.fields || {};
    const machine = parseMachine(texts.machine_text || '');
    const locations = parseLocations(texts.locations_text || '', payload.settings ? payload.settings.avoid_location_double_count !== false : true);
    const versions = parseVersions(texts.versions_text || '');
    const purchased = toNumber(fields.f_flex_purchased || '');
    const used = toNumber(fields.f_flex_used || '');
    const pctUsed = purchased && used !== null && purchased > 0 ? Math.round(used / purchased * 100) : '—';
    const systemlinkSnow = truthy(fields.f_systemlink_snow);
    const supportScope = (fields.f_support_scope || '').trim();
    return {
      service_id: fields.f_service_id || '',
      customer: fields.f_customer || '',
      updated_date: fmtDate(new Date()),
      ea_end_date: fields.f_end_date || '',
      ep_term: fields.f_ep_term || '',
      contract_scope: fields.f_contract_scope || '',
      phase: fields.f_phase || '',
      debug_licenses: fields.f_debug || '',
      bundles: Array.isArray(payload.bundles) ? payload.bundles : [],
      finite_licenses: Array.isArray(payload.finite_licenses) ? payload.finite_licenses : [],
      machine: { df: machine, stats: computeStats(machine) },
      locations_top5: topLocations(locations),
      versions_top5: topVersions(versions),
      credits: { purchased: fields.f_flex_purchased || '—', used: fields.f_flex_used || '—', pct_used: pctUsed },
      support: { tier: fields.f_support_tier || '—', scope: supportScope, systemlink_snow: systemlinkSnow }
    };
  }

  function applyProfilePayload(payload) {
    const texts = payload.texts || {};
    const fields = payload.fields || {};
    $('machineText').value = texts.machine_text || '';
    $('locationsText').value = texts.locations_text || '';
    $('versionsText').value = texts.versions_text || '';
    $('serviceId').value = fields.f_service_id || '';
    $('customer').value = fields.f_customer || '';
    $('startDate').value = fields.f_start_date || '';
    $('epTerm').value = fields.f_ep_term || '';
    $('endDate').value = fields.f_end_date || '';
    $('phase').value = fields.f_phase || '';
    $('contractScope').value = fields.f_contract_scope || '';
    $('debugLicenses').value = fields.f_debug || 'No';
    $('supportTier').value = fields.f_support_tier || '';
    $('supportScope').value = fields.f_support_scope || '';
    $('systemlinkSnow').checked = truthy(fields.f_systemlink_snow);
    $('creditsPurchased').value = fields.f_flex_purchased || '';
    $('creditsUsed').value = fields.f_flex_used || '';
    $('avoidLocationDoubleCount').checked = payload.settings ? payload.settings.avoid_location_double_count !== false : true;
    setFiniteText((payload.finite_licenses || []).map((r) => `${r.count || 0}\t${r.license_type || ''}\t${r.license_name || ''}`).join('\n'), false);
    setBundleText((payload.bundles || []).join('\n'), false);
    $('profileName').value = suggestProfileName();
    render();
  }

  function readJsonFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          resolve(JSON.parse(String(reader.result || '{}')));
        } catch (err) {
          reject(new Error(`${file.name}: invalid JSON`));
        }
      };
      reader.onerror = () => reject(new Error(`${file.name}: could not be read`));
      reader.readAsText(file);
    });
  }

  function exportProfile() {
    if (!$('profileName').value.trim()) $('profileName').value = suggestProfileName();
    const payload = currentProfilePayload();
    const name = safeFileName($('profileName').value || suggestProfileName());
    downloadBlob(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }), `${name}.json`);
    setStatus(`Profile exported: ${name}.json`, 'ok');
  }

  async function importProfile() {
    const file = $('importProfile').files && $('importProfile').files[0];
    if (!file) return;
    try {
      applyProfilePayload(await readJsonFile(file));
      setStatus('Profile imported.', 'ok');
    } catch (err) {
      setStatus(err.message || String(err), 'error');
    } finally {
      $('importProfile').value = '';
    }
  }

  function pptxConstructor() {
    return window.PptxGenJS || window.pptxgen || window.pptxgenjs || null;
  }

  function newPresentation() {
    const Ctor = pptxConstructor();
    if (!Ctor) throw new Error('PPTX generator failed to load.');
    const pptx = new Ctor();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'EA Slide Builder Pages';
    pptx.company = '';
    pptx.subject = 'Browser-only EA one-slider';
    pptx.title = 'EA Slide Builder';
    pptx.lang = 'en-US';
    return pptx;
  }

  const PPT = {
    W: 13.333,
    H: 7.5,
    dark: '013324',
    accent: '18AF7C',
    tint: 'ECF7F2',
    muted: '8FC9B6',
    border: 'DDDDDD',
    gray: '6E6E6E',
    white: 'FFFFFF',
    red: 'C03A2B',
    amber: 'C88A1E'
  };

  function shapeNames(pptx) {
    return {
      rect: (pptx.ShapeType && pptx.ShapeType.rect) || 'rect',
      line: (pptx.ShapeType && pptx.ShapeType.line) || 'line',
      ellipse: (pptx.ShapeType && pptx.ShapeType.ellipse) || 'ellipse'
    };
  }

  // ----- fit-to-size estimation -------------------------------------------
  // PowerPoint text boxes do not clip: overflowing text spills past the card.
  // Estimate rendered text height (accounting for wrapping) and shrink fonts
  // until each table/row fits the space its card gives it.
  const FIT = { charW: 0.52, lineH: 1.25, sidePad: 0.08, rowPad: 0.035 };

  function estLines(text, colWIn, size) {
    const avail = Math.max(colWIn - FIT.sidePad, 0.08);
    const perLine = Math.max(1, Math.floor((avail * 72) / (size * FIT.charW)));
    return Math.max(1, Math.ceil(String(text ?? '').length / perLine));
  }

  function estRowH(cells, colWsIn, size) {
    let lines = 1;
    cells.forEach((t, i) => { lines = Math.max(lines, estLines(t, colWsIn[i], size)); });
    return (lines * size * FIT.lineH) / 72 + FIT.rowPad;
  }

  function estTableH(rowTexts, colWsIn, size) {
    return rowTexts.reduce((s, r) => s + estRowH(r, colWsIn, size), 0);
  }

  function fitTableFont(rowTexts, colWsIn, totalH, base, minimum) {
    let size = base;
    while (size > minimum) {
      if (estTableH(rowTexts, colWsIn, size) <= totalH) return size;
      size = Math.round((size - 0.2) * 10) / 10;
    }
    return minimum;
  }

  function fitOneLine(text, availWIn, size, minimum = 6) {
    const est = (String(text ?? '').length * size * FIT.charW) / 72;
    if (est <= availWIn || est <= 0) return size;
    return Math.max(minimum, size * (availWIn / est));
  }

  function addText(slide, text, opts) {
    slide.addText(String(text ?? ''), {
      margin: 0.04,
      fontFace: opts.fontFace || 'Calibri',
      fontSize: opts.fontSize || 9,
      bold: !!opts.bold,
      color: opts.color || PPT.dark,
      align: opts.align || 'left',
      valign: opts.valign || 'top',
      fit: 'shrink',
      breakLine: false,
      ...opts
    });
  }

  function addRect(slide, pptx, x, y, w, h, fill = PPT.white, line = PPT.border, width = 0.6) {
    slide.addShape(shapeNames(pptx).rect, {
      x, y, w, h,
      fill: { color: fill, transparency: fill === 'transparent' ? 100 : 0 },
      line: line ? { color: line, width } : { color: fill, transparency: 100 }
    });
  }

  function addHeader(slide, pptx, data, title = 'Enterprise Agreement') {
    addRect(slide, pptx, 0, 0, PPT.W, 0.92, PPT.dark, PPT.dark);
    addText(slide, title.toUpperCase(), { x: 0.35, y: 0.12, w: 6.5, h: 0.2, fontSize: 8, bold: true, color: PPT.muted });
    addText(slide, `${data.service_id || 'EA'}  ·  ${data.customer || 'Customer'}`, { x: 0.35, y: 0.34, w: 9.6, h: 0.46, fontFace: 'Georgia', fontSize: 20, bold: true, color: PPT.white });
    addText(slide, data.updated_date ? `Updated ${data.updated_date}` : '', { x: 10.2, y: 0.32, w: 2.8, h: 0.28, fontSize: 9, color: PPT.muted, align: 'right' });
  }

  function addCard(slide, pptx, title, x, y, w, h, options = {}) {
    const fill = options.fill || PPT.white;
    const line = options.line === undefined ? PPT.border : options.line;
    addRect(slide, pptx, x, y, w, h, fill, line);
    addText(slide, title.toUpperCase(), { x: x + 0.12, y: y + 0.09, w: w - 0.24, h: 0.2, fontSize: 7.5, bold: true, color: options.titleColor || PPT.accent });
    return { x: x + 0.14, y: y + 0.38, w: w - 0.28, h: h - 0.52 };
  }

  function addKeyRows(slide, area, pairs) {
    const rowH = area.h / pairs.length;
    const labelSize = Math.max(6.2, Math.min(8.5, rowH * 24));
    const valueW = area.w * 0.57 - 0.06;
    pairs.forEach(([label, value], i) => {
      const y = area.y + i * rowH;
      const text = value || '—';
      addText(slide, label, { x: area.x, y, w: area.w * 0.48, h: rowH, fontSize: labelSize, color: PPT.gray, valign: 'mid' });
      addText(slide, text, { x: area.x + area.w * 0.43, y, w: area.w * 0.57, h: rowH, fontSize: fitOneLine(text, valueW, Math.max(6.4, Math.min(8.8, rowH * 24.5))), bold: true, color: PPT.dark, align: 'right', valign: 'mid' });
    });
  }

  function addSimpleTable(slide, pptx, headers, rowsData, area, colW, options = {}) {
    if (!rowsData.length) {
      addText(slide, 'No data provided', { x: area.x, y: area.y + 0.12, w: area.w, h: 0.24, fontSize: 8.5, color: PPT.gray, align: 'center' });
      return;
    }
    const colWsIn = colW.map((f) => area.w * f);
    const texts = (rows) => [headers].concat(rows.map((row) => row.map((c) => c.text)));
    let rowsToShow = rowsData;
    let rowTexts = texts(rowsToShow);
    const minSize = Math.min(options.minFontSize || 5.4, 5.4);
    const bodySize = fitTableFont(rowTexts, colWsIn, area.h, options.fontSize || 7.6, minSize);
    // If even the minimum font can't fit every row, truncate and note it
    // instead of spilling past the card.
    let overflow = 0;
    if (estTableH(rowTexts, colWsIn, bodySize) > area.h) {
      while (rowsToShow.length > 1 && estTableH(rowTexts, colWsIn, bodySize) > area.h) {
        rowsToShow = rowsToShow.slice(0, -1);
        overflow = rowsData.length - rowsToShow.length;
        rowTexts = texts(rowsToShow).concat([[`+${overflow} more`]]);
      }
    }
    // Row heights proportional to what each row's wrapped text needs.
    const needs = rowTexts.map((r) => estRowH(r, colWsIn, bodySize));
    const scale = area.h / needs.reduce((s, n) => s + n, 0);
    const rowHs = needs.map((n) => n * scale);
    const headerSize = Math.max(options.minHeaderSize || 5.2, Math.min(6.8, bodySize - 0.4));
    let x = area.x;
    headers.forEach((head, i) => {
      const cw = area.w * colW[i];
      addRect(slide, pptx, x, area.y, cw, rowHs[0], PPT.dark, PPT.dark);
      addText(slide, head, { x: x + 0.03, y: area.y + 0.02, w: cw - 0.06, h: Math.max(0.08, rowHs[0] - 0.03), fontSize: headerSize, bold: true, color: PPT.white, align: i === headers.length - 1 ? 'right' : 'left', valign: 'mid' });
      x += cw;
    });
    let y = area.y + rowHs[0];
    rowsToShow.forEach((row, r) => {
      x = area.x;
      const rowH = rowHs[r + 1];
      const fill = r % 2 ? PPT.tint : PPT.white;
      row.forEach((cell, i) => {
        const cw = area.w * colW[i];
        addRect(slide, pptx, x, y, cw, rowH, fill, 'EEF1EF', 0.2);
        addText(slide, cell.text, { x: x + 0.03, y: y + 0.02, w: cw - 0.06, h: Math.max(0.08, rowH - 0.02), fontSize: Math.min(cell.size || bodySize, bodySize), bold: !!cell.bold, color: cell.color || PPT.dark, align: cell.align || 'left', valign: 'mid' });
        x += cw;
      });
      y += rowH;
    });
    if (overflow) {
      addText(slide, `+${overflow} more`, { x: area.x + 0.03, y, w: area.w - 0.06, h: Math.max(0.08, rowHs[rowHs.length - 1] - 0.02), fontSize: Math.max(5, bodySize - 0.5), color: PPT.gray, valign: 'mid' });
    }
  }

  function addTrend(slide, pptx, machine, area) {
    const data = machine || [];
    if (!data.length) {
      addText(slide, 'No machine-count data', { x: area.x, y: area.y + 0.2, w: area.w, h: 0.3, fontSize: 9, color: PPT.gray, align: 'center' });
      return;
    }
    const shapes = shapeNames(pptx);
    const values = data.map((r) => r.total);
    let lo = Math.min(...values);
    let hi = Math.max(...values);
    const span0 = hi - lo || 1;
    lo -= span0 * 0.08;
    hi += span0 * 0.08;
    const span = hi - lo || 1;
    const plot = { x: area.x + 0.24, y: area.y + 0.12, w: area.w - 0.34, h: area.h - 0.48 };
    [0, 0.5, 1].forEach((f) => {
      const y = plot.y + plot.h * f;
      slide.addShape(shapes.line, { x: plot.x, y, w: plot.w, h: 0, line: { color: 'EEF1EF', width: 0.5 } });
    });
    const point = (i) => ({
      x: plot.x + plot.w * i / Math.max(data.length - 1, 1),
      y: plot.y + plot.h * (1 - (values[i] - lo) / span)
    });
    for (let i = 1; i < data.length; i += 1) {
      const a = point(i - 1);
      const b = point(i);
      slide.addShape(shapes.line, { x: a.x, y: a.y, w: b.x - a.x, h: b.y - a.y, line: { color: PPT.accent, width: 1.8 } });
    }
    const peakI = values.indexOf(Math.max(...values));
    const p = point(peakI);
    slide.addShape(shapes.ellipse, { x: p.x - 0.05, y: p.y - 0.05, w: 0.1, h: 0.1, fill: { color: PPT.accent }, line: { color: PPT.white, width: 1 } });
    addText(slide, data[0].period, { x: plot.x, y: area.y + area.h - 0.22, w: 1.4, h: 0.16, fontSize: 6.5, color: PPT.gray });
    addText(slide, data[data.length - 1].period, { x: plot.x + plot.w - 1.4, y: area.y + area.h - 0.22, w: 1.4, h: 0.16, fontSize: 6.5, color: PPT.gray, align: 'right' });
  }

  function addStatsCard(slide, pptx, area, stats) {
    const boxW = (area.w - 0.12) / 2;
    [
      [area.x, stats.max_total, 'Peak machines', stats.max_period, PPT.accent, PPT.accent],
      [area.x + boxW + 0.12, stats.min_total, 'Min machines', stats.min_period, PPT.dark, PPT.border]
    ].forEach(([x, num, label, period, color, line]) => {
      addRect(slide, pptx, x, area.y, boxW, area.h * 0.62, PPT.white, line, 1);
      addText(slide, fmt(num), { x, y: area.y + 0.13, w: boxW, h: 0.36, fontFace: 'Georgia', fontSize: 24, bold: true, color, align: 'center' });
      addText(slide, label, { x, y: area.y + 0.55, w: boxW, h: 0.2, fontSize: 7.8, color: PPT.gray, align: 'center' });
      addText(slide, period, { x, y: area.y + 0.76, w: boxW, h: 0.2, fontSize: 7, color: PPT.dark, align: 'center' });
    });
    addRect(slide, pptx, area.x, area.y + area.h * 0.7, area.w, area.h * 0.3, PPT.tint, null);
    addText(slide, 'Avg quarterly increase', { x: area.x + 0.12, y: area.y + area.h * 0.77, w: area.w * 0.55, h: 0.25, fontSize: 8.7, color: PPT.dark, valign: 'mid' });
    addText(slide, `${stats.avg_pct_change >= 0 ? '+' : ''}${stats.avg_pct_change.toFixed(1)}%`, { x: area.x + area.w * 0.58, y: area.y + area.h * 0.72, w: area.w * 0.36, h: 0.32, fontFace: 'Georgia', fontSize: 18, bold: true, color: PPT.accent, align: 'right' });
  }

  function addEaSlide(pptx, data) {
    const slide = pptx.addSlide();
    slide.background = { color: PPT.white };
    addHeader(slide, pptx, data);
    const margin = 0.3;
    const gap = 0.2;
    const colW = (PPT.W - 2 * margin - 2 * gap) / 3;
    const top = 1.08;
    const leftX = margin;
    const centerX = margin + colW + gap;
    const rightX = margin + 2 * colW + 2 * gap;
    let area = addCard(slide, pptx, 'Contract Details', leftX, top, colW, 1.68);
    addKeyRows(slide, area, [['EA End Date', data.ea_end_date], ['Term Duration', data.ep_term], ['Contract Scope', data.contract_scope], ['Phase', data.phase]]);

    const bundles = data.bundles || [];
    const finite = data.finite_licenses || [];
    let y = top + 1.8;
    if (bundles.length) {
      const h = finite.length ? Math.min(2.0, 0.55 + bundles.slice(0, 4).length * 0.38) : 4.95;
      area = addCard(slide, pptx, 'Bundle Information', leftX, y, colW, h);
      bundles.slice(0, Math.floor(area.h / 0.34)).forEach((bundle, i) => {
        addRect(slide, pptx, area.x, area.y + i * 0.38, area.w, 0.3, PPT.white, PPT.accent, 1);
        addText(slide, bundle, { x: area.x + 0.05, y: area.y + i * 0.38 + 0.06, w: area.w - 0.1, h: 0.18, fontSize: fitOneLine(bundle, area.w - 0.2, 8), bold: true, align: 'center' });
      });
      y += h + 0.12;
    }
    if (finite.length) {
      area = addCard(slide, pptx, 'NI SW Licenses (Finite Qty)', leftX, y, colW, Math.max(1.35, 7.24 - y - 0.15));
      addSimpleTable(slide, pptx, ['QTY', 'LICENSE', 'TYPE'], finite.map((r) => [
        { text: fmt(r.count), bold: true, color: PPT.accent, align: 'right' },
        { text: r.license_name || '' },
        { text: r.license_type || '', color: PPT.gray, size: 6.8 }
      ]), area, [0.14, 0.56, 0.30], { fitAll: true, minFontSize: 5.1 });
    } else if (!bundles.length) {
      area = addCard(slide, pptx, 'Licenses & Bundles', leftX, y, colW, 4.95);
      addText(slide, 'No license or bundle data provided', { x: area.x, y: area.y + 0.3, w: area.w, h: 0.3, fontSize: 8.5, color: PPT.gray, align: 'center' });
    }

    area = addCard(slide, pptx, 'Software Usage Trend', centerX, top, colW, 3.4);
    addTrend(slide, pptx, data.machine.df, area);
    area = addCard(slide, pptx, 'Software Usage Data', centerX, top + 3.52, colW, 2.68);
    addStatsCard(slide, pptx, area, data.machine.stats);

    // Locations/version cards split their space by their actual row counts.
    const nLoc = Math.max(data.locations_top5.length, 1);
    const nVer = Math.max(data.versions_top5.length, 1);
    const tablesH = 3.8;
    const hLoc = tablesH * (nLoc + 1) / (nLoc + nVer + 2);
    area = addCard(slide, pptx, 'Top Site Locations', rightX, top, colW, hLoc);
    addSimpleTable(slide, pptx, ['STATE', 'CITY', 'MACHINES'], data.locations_top5.map((r) => [
      { text: r.state || '' },
      { text: r.city || r.location || '' },
      { text: fmt(r.count), bold: true, color: PPT.accent, align: 'right' }
    ]), area, [0.22, 0.48, 0.3], { fitAll: true, minFontSize: 6.2 });
    area = addCard(slide, pptx, 'Version Usage', rightX, top + hLoc + 0.12, colW, tablesH - hLoc);
    addSimpleTable(slide, pptx, ['PRODUCT', 'TOTAL', 'TOP VER.', '%'], data.versions_top5.map((r) => [
      { text: r.product || '' },
      { text: fmt(r.product_total ?? r.users), bold: true, align: 'right' },
      { text: r.version || '' },
      { text: `${r.pct || 0}%`, bold: true, color: PPT.accent, align: 'right' }
    ]), area, [0.38, 0.19, 0.27, 0.16], { fitAll: true, minFontSize: 5.8 });
    area = addCard(slide, pptx, 'Training Credit Usage', rightX, top + 4.04, colW, 1.18);
    [['Purchased', data.credits.purchased, PPT.dark], ['Used', data.credits.used, PPT.dark], ['Utilized', data.credits.pct_used === '—' ? '—' : `${data.credits.pct_used}%`, PPT.accent]].forEach(([label, value, color], i) => {
      const x = area.x + area.w / 3 * i;
      addText(slide, label, { x, y: area.y, w: area.w / 3, h: 0.2, fontSize: 7.2, color: PPT.gray, align: 'center' });
      addText(slide, fmt(value), { x, y: area.y + 0.27, w: area.w / 3, h: 0.32, fontFace: 'Georgia', fontSize: 16, bold: true, color, align: 'center' });
    });
    addRect(slide, pptx, rightX, top + 5.34, colW, 0.86, PPT.dark, PPT.dark);
    addText(slide, 'TECHNICAL SUPPORT', { x: rightX + 0.14, y: top + 5.44, w: colW - 0.28, h: 0.2, fontSize: 7.5, bold: true, color: PPT.muted });
    const snow = !!data.support.systemlink_snow;
    const supportRuns = [
      { text: data.support.tier || '—', options: { fontSize: 11, bold: true, color: PPT.white, breakLine: snow && !data.support.scope } }
    ];
    if (data.support.scope) supportRuns.push({ text: `   ${data.support.scope}`, options: { fontSize: 9, color: PPT.muted, breakLine: snow } });
    if (snow) supportRuns.push({ text: 'SystemLink Support (SNOW)', options: { fontSize: 11, bold: true, color: PPT.white } });
    slide.addText(supportRuns, { x: rightX + 0.14, y: top + 5.64, w: colW - 0.28, h: 0.5, fontFace: 'Calibri', valign: 'mid' });
  }

  function addInsightsSlide(pptx, data, insights) {
    if (!insights || !insights.length) return;
    const slide = pptx.addSlide();
    slide.background = { color: PPT.white };
    addHeader(slide, pptx, data, 'CSM Insights');
    const colors = { 1: PPT.red, 2: PPT.amber, 3: PPT.accent, 4: PPT.dark };
    const labels = { 1: 'HIGH', 2: 'MEDIUM', 3: 'GOOD', 4: 'CONTEXT' };
    insights.slice(0, 6).forEach((ins, i) => {
      const y = 1.15 + i * 1.0;
      addRect(slide, pptx, 0.35, y, 12.63, 0.88, i % 2 ? PPT.white : PPT.tint, PPT.border);
      const p = ins.p || ins.priority || 4;
      addRect(slide, pptx, 0.48, y + 0.28, 1.0, 0.3, colors[p] || PPT.dark, null);
      addText(slide, labels[p] || '', { x: 0.48, y: y + 0.35, w: 1.0, h: 0.12, fontSize: 7.2, bold: true, color: PPT.white, align: 'center' });
      addText(slide, (ins.cat || ins.category || '').toUpperCase(), { x: 1.65, y: y + 0.12, w: 10.9, h: 0.18, fontSize: 8, bold: true, color: PPT.accent });
      addText(slide, ins.text || '', { x: 1.65, y: y + 0.34, w: 10.9, h: 0.38, fontSize: 9, color: PPT.dark });
    });
  }

  function containBox(imgW, imgH, boxW, boxH) {
    const ratio = Math.min(boxW / Math.max(imgW, 1), boxH / Math.max(imgH, 1));
    return { w: imgW * ratio, h: imgH * ratio };
  }

  function addScreenshotsSlide(pptx, data, shots) {
    if (!shots.length) return;
    const slide = pptx.addSlide();
    slide.background = { color: PPT.white };
    addHeader(slide, pptx, data, 'Source Screenshots');
    const boxes = [
      { x: 0.35, y: 1.22, w: 4.05, h: 5.8 },
      { x: 4.64, y: 1.22, w: 4.05, h: 5.8 },
      { x: 8.93, y: 1.22, w: 4.05, h: 5.8 }
    ];
    shots.slice(0, 3).forEach((shot, i) => {
      const box = boxes[i];
      addRect(slide, pptx, box.x, box.y, box.w, box.h, PPT.white, PPT.border);
      addText(slide, `${shot.label}: ${shot.name}`, { x: box.x + 0.1, y: box.y + 0.1, w: box.w - 0.2, h: 0.25, fontSize: 8.2, bold: true, color: PPT.accent });
      const imgArea = { x: box.x + 0.12, y: box.y + 0.46, w: box.w - 0.24, h: box.h - 0.62 };
      const size = containBox(shot.width, shot.height, imgArea.w, imgArea.h);
      slide.addImage({ data: shot.dataUrl, x: imgArea.x + (imgArea.w - size.w) / 2, y: imgArea.y + (imgArea.h - size.h) / 2, w: size.w, h: size.h });
    });
  }

  async function writePresentation(pptx, fileName) {
    setStatus(`Preparing ${fileName}...`);
    await pptx.writeFile({ fileName });
    setStatus(`Downloaded ${fileName}`, 'ok');
  }

  async function downloadCurrentPptx() {
    const data = buildData();
    const used = toNumber(data.credits.used);
    if (used === null) {
      setStatus('Credits used is required before generating the PPTX.', 'error');
      return;
    }
    if (!data.machine.df.length) {
      setStatus('Paste the Machine Count table before generating the PPTX.', 'error');
      return;
    }
    try {
      const pptx = newPresentation();
      addEaSlide(pptx, data);
      if ($('includeInsights').checked) addInsightsSlide(pptx, data, generateInsights(data));
      if ($('includeScreenshots') && $('includeScreenshots').checked) addScreenshotsSlide(pptx, data, Object.values(uploadedShots).filter(Boolean));
      await writePresentation(pptx, `${safeFileName(`${data.service_id || 'EA'}_${data.customer || 'customer'}`)}.pptx`);
    } catch (err) {
      setStatus(err.message || String(err), 'error');
    }
  }

  async function downloadBatchPptx() {
    const files = Array.from(($('batchProfiles').files || []));
    if (!files.length) {
      setStatus('Choose one or more exported profile JSON files first.', 'error');
      return;
    }
    try {
      const payloads = await Promise.all(files.map(readJsonFile));
      const pptx = newPresentation();
      payloads.forEach((payload) => {
        const data = dataFromProfilePayload(payload);
        addEaSlide(pptx, data);
        if ($('includeInsights').checked) addInsightsSlide(pptx, data, generateInsights(data));
      });
      await writePresentation(pptx, 'EA_batch_deck.pptx');
    } catch (err) {
      setStatus(err.message || String(err), 'error');
    }
  }

  function clearAll() {
    document.querySelectorAll('input, textarea').forEach((el) => {
      if (el.type === 'checkbox') el.checked = ['avoidLocationDoubleCount', 'includeInsights', 'includeScreenshots', 'autoContractOcr'].includes(el.id);
      else el.value = '';
    });
    $('debugLicenses').value = 'No';
    Object.entries(SHOT_META).forEach(([key, meta]) => {
      uploadedShots[key] = null;
      if ($(meta.previewId)) $(meta.previewId).textContent = 'No image selected';
      setOcrStatus(key, '');
    });
    setFiniteText('', false);
    setBundleText('', false);
    render();
  }

  setupEditableTables();
  $('recomputeDates').addEventListener('click', recomputeDates);
  $('loadExamples').addEventListener('click', loadExamples);
  $('generate').addEventListener('click', render);
  $('downloadPptx').addEventListener('click', downloadCurrentPptx);
  $('exportProfile').addEventListener('click', exportProfile);
  $('importProfile').addEventListener('change', importProfile);
  $('downloadBatchPptx').addEventListener('click', downloadBatchPptx);
  $('printPage').addEventListener('click', () => window.print());
  $('clearAll').addEventListener('click', clearAll);
  Object.entries(SHOT_META).forEach(([key, meta]) => {
    if ($(meta.inputId)) $(meta.inputId).addEventListener('change', () => handleScreenshotInput(key));
  });
  if ($('ocrA')) $('ocrA').addEventListener('click', () => runOcr('a'));
  if ($('ocrB')) $('ocrB').addEventListener('click', () => runOcr('b'));
  if ($('ocrC')) $('ocrC').addEventListener('click', () => runOcr('c'));
  document.querySelectorAll('input, textarea, select').forEach((el) => {
    if (el.closest('.row-editor') || el.classList.contains('source-data')) return;
    el.addEventListener('input', render);
  });
  render();
})();
