/* Costruisce le pagine inglesi /en/ a partire da quelle italiane (gira nel file manager Tophost) */
window._buildEN = async function (RAW, scrivi) {
  const pages = ['index','music','games','app','killa-news','about','contact','classifiche','epk','scarica-il-mio-bar','privacy','termini','link'];
  const SITO = 'https://www.killarecordsgames.com';
  const EN = await fetch(RAW + 'en-testi.json').then(r => r.json());
  const norm = s => s.replace(/\s+/g, ' ').trim();
  const docs = {}; const seen = new Map();
  for (const p of pages) {
    const h = _dec((await _cf.getFileContents('/htdocs/' + p + '.html')).data.data);
    docs[p] = h;
    const d = new DOMParser().parseFromString(h, 'text/html');
    const add = s => { s = norm(s || ''); if (!s || !/[A-Za-zÀ-ú]/.test(s)) return; if (!seen.has(s)) seen.set(s, p); };
    add(d.title);
    d.querySelectorAll('meta[name=description],meta[property="og:title"],meta[property="og:description"],meta[name="twitter:title"],meta[name="twitter:description"],meta[property="og:image:alt"]').forEach(m => add(m.content));
    d.querySelectorAll('[alt],[aria-label],[title],[placeholder]').forEach(e => ['alt','aria-label','title','placeholder'].forEach(a => e.hasAttribute(a) && add(e.getAttribute(a))));
    const w = d.createTreeWalker(d.body, NodeFilter.SHOW_TEXT, { acceptNode: n => n.parentElement.closest('script,style,noscript') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    let n; while ((n = w.nextNode())) add(n.nodeValue);
  }
  const IT = [...seen.keys()];
  if (IT.length !== EN.length) return 'ERRORE: frasi ' + IT.length + ' traduzioni ' + EN.length;
  if (IT[45] !== 'Seguici:' || IT[430] !== '· © 2026 Killa Records') return 'ERRORE: ordine diverso';
  const MAP = new Map(IT.map((s, i) => [s, EN[i]]));
  const tr = s => { const k = norm(s || ''); return MAP.has(k) ? s.replace(k.length ? s.trim() : s, MAP.get(k)) : null; };
  const PAG = /^(?:https:\/\/www\.killarecordsgames\.com)?\/(music|games|app|killa-news|about|contact|classifiche|epk|scarica-il-mio-bar|privacy|termini|link)?(#.*)?$/;
  const urlIT = p => SITO + '/' + (p === 'index' ? '' : p);
  const urlEN = p => SITO + '/en/' + (p === 'index' ? '' : p);
  const alt = p => '\n  <link rel="alternate" hreflang="it" href="' + urlIT(p) + '">\n  <link rel="alternate" hreflang="en" href="' + urlEN(p) + '">\n  <link rel="alternate" hreflang="x-default" href="' + urlIT(p) + '">\n';
  const SCRIPT = [['"it-IT"', '"en-GB"'], ['"Ultima versione disponibile: "', '"Latest version available: "'], ['", pubblicata il "', '", released on "'], ['"Per Windows 10 e 11. Versione "', '"For Windows 10 and 11. Version "'], ['", aggiornata il "', '", updated on "']];
  const rapporto = [];
  for (const p of pages) {
    const d = new DOMParser().parseFromString(docs[p], 'text/html');
    let mancanti = [];
    d.documentElement.lang = 'en';
    const t = tr(d.title); if (t) d.title = norm(t);
    d.querySelectorAll('meta[name=description],meta[property="og:title"],meta[property="og:description"],meta[name="twitter:title"],meta[name="twitter:description"],meta[property="og:image:alt"]').forEach(m => { const x = tr(m.content); if (x) m.content = norm(x); else if (m.content) mancanti.push(m.content); });
    d.querySelectorAll('[alt],[aria-label],[title],[placeholder]').forEach(e => ['alt','aria-label','title','placeholder'].forEach(a => { if (e.hasAttribute(a)) { const x = tr(e.getAttribute(a)); if (x) e.setAttribute(a, norm(x)); } }));
    const w = d.createTreeWalker(d.body, NodeFilter.SHOW_TEXT, { acceptNode: n => n.parentElement.closest('script,style,noscript') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    const nodi = []; let n; while ((n = w.nextNode())) nodi.push(n);
    nodi.forEach(n => { const k = norm(n.nodeValue); if (!k || !/[A-Za-zÀ-ú]/.test(k)) return; if (MAP.has(k)) { const lead = n.nodeValue.match(/^\s*/)[0], tail = n.nodeValue.match(/\s*$/)[0]; n.nodeValue = lead + MAP.get(k) + tail; } else mancanti.push(k); });
    const loc = d.querySelector('meta[property="og:locale"]'); if (loc) { loc.content = 'en_GB'; loc.insertAdjacentHTML('afterend', '\n  <meta property="og:locale:alternate" content="it_IT">'); }
    const can = d.querySelector('link[rel=canonical]'); if (can) can.href = urlEN(p);
    const ogu = d.querySelector('meta[property="og:url"]'); if (ogu) ogu.content = urlEN(p);
    d.querySelectorAll('link[rel=alternate][hreflang]').forEach(l => l.remove());
    (can || d.head.lastChild).insertAdjacentHTML('afterend', alt(p));
    d.querySelectorAll('a[href]').forEach(a => { const h = a.getAttribute('href'); const m = h.match(PAG); if (m) a.setAttribute('href', '/en/' + (m[1] || '') + (m[2] || '')); });
    d.querySelectorAll('link[href],script[src],img[src],a[href],source[src]').forEach(e => { const at = e.hasAttribute('src') ? 'src' : 'href'; const v = e.getAttribute(at); if (v && !/^(\/|https?:|#|mailto:|tel:|data:|javascript:)/.test(v)) e.setAttribute(at, '/' + v); });
    d.querySelectorAll('script[src*="site-content.js"],script[src*="killa-newsletter.js"]').forEach(s => s.remove());
    d.querySelectorAll('script:not([src])').forEach(s => { let c = s.textContent; SCRIPT.forEach(([a, b]) => { c = c.split(a).join(b); }); s.textContent = c; });
    const nav = d.querySelector('ul.nav-list');
    if (nav) nav.insertAdjacentHTML('beforeend', '<li><a href="' + urlIT(p).replace(SITO, '') + '" lang="it" hreflang="it">Italiano</a></li>');
    const piede = d.querySelector('.lk-piede'); if (piede) piede.insertAdjacentHTML('beforeend', ' · <a href="/link" lang="it" hreflang="it">Italiano</a>');
    if (p === 'privacy' || p === 'termini') { const h1 = d.querySelector('h1'); if (h1) h1.insertAdjacentHTML('afterend', '\n<p><em>This is an English translation provided for convenience. In case of any difference, the <a href="/' + p + '" lang="it" hreflang="it">Italian version</a> prevails.</em></p>'); }
    const html = '<!DOCTYPE html>\n' + d.documentElement.outerHTML + '\n';
    if (scrivi) await _cf.putFileContents('/htdocs/en/' + p + '.html', html, null, undefined, false, true);
    // pagina italiana: hreflang e link English
    let it = docs[p];
    if (!it.includes('hreflang="en"')) {
      it = it.replace(/(<link rel="canonical"[^>]*>)/, '$1' + alt(p).replace(/\n$/, ''));
      if (/<ul class="nav-list">/.test(it)) { const i = it.indexOf('</ul>', it.indexOf('<ul class="nav-list">')); it = it.slice(0, i) + '  <li><a href="/en/' + (p === 'index' ? '' : p) + '" lang="en" hreflang="en">English</a></li>\n        ' + it.slice(i); }
      if (p === 'link') it = it.replace('&copy; 2026 Killa Records</p>', '&copy; 2026 Killa Records · <a href="/en/link" lang="en" hreflang="en">English</a></p>');
      if (scrivi) await _cf.putFileContents('/htdocs/' + p + '.html', it, null, undefined, false, true);
    }
    rapporto.push(p + ': ' + html.length + (mancanti.length ? ' MANCANTI ' + mancanti.length + ': ' + mancanti.slice(0, 4).join(' | ') : ' ok'));
  }
  return rapporto.join('\n');
};
'pronto';
