(function(){
  var D = JSON.parse(document.getElementById('gd').textContent);
  var LOCAL = document.body.classList.contains('local');
  var $ = function(s, r){ return (r || document).querySelector(s); };
  var $$ = function(s, r){ return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var store = {
    get: function(k){ try { return window.localStorage.getItem(k); } catch(e){ return null; } },
    set: function(k, v){ try { window.localStorage.setItem(k, v); } catch(e){} }
  };
  function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  // ---------------------------------------------------------------- destino de los enlaces
  var BASE = { wh: 'https://www.wowhead.com/forever/', whes: 'https://www.wowhead.com/forever/es/', wdb: 'https://forever.warcraftdb.com/' };
  var mode = store.get('fichas') || 'wh';
  if (!BASE[mode]) mode = 'wh';
  function url(t, id){
    if (t === 'search') return (mode === 'whes' ? BASE.whes : BASE.wh) + 'search?q=' + encodeURIComponent(id);
    return mode === 'wdb' ? BASE.wdb + 'data/' + t + '/' + id : BASE[mode] + t + '=' + id;
  }
  function applyLinks(){
    $$('a.x').forEach(function(a){ a.href = url(a.dataset.t, a.dataset.t === 'search' ? a.dataset.q : a.dataset.id); });
  }
  var sel = $('#fichas');
  if (sel){
    sel.value = mode;
    sel.addEventListener('change', function(){ mode = sel.value; store.set('fichas', mode); applyLinks(); });
  }
  if (mode !== 'wh') applyLinks();

  // ---------------------------------------------------------------- casillas y progreso
  var boxes = $$('input[type=checkbox][data-k]');
  function countIn(el, q){
    var all = $$(q || 'input[type=checkbox][data-k]', el);
    var on = all.filter(function(b){ return b.checked; }).length;
    return [on, all.length];
  }
  function updateContainer(d){
    var p = $(':scope > summary .prog', d);
    if (!p) return;
    var c = countIn(d, d.classList.contains('dg') ? '.ql input[type=checkbox]' : null);
    p.textContent = c[1] ? c[0] + '/' + c[1] : '';
  }
  function dungeonState(){
    var done = 0, total = 0;
    $$('input[data-dg]').forEach(function(b){
      total++; if (b.checked) done++;
      var row = $('.gr[data-dg="' + b.dataset.dg + '"]');
      if (row) row.classList.toggle('done', b.checked);
    });
    $$('details.dg').forEach(function(d){
      var c = countIn(d, 'input[data-dg]');
      var t = $(':scope > summary .okk', d);
      if (t) t.hidden = !(c[1] && c[0] === c[1]);
    });
    return [done, total];
  }
  function updateGlobal(){
    var dg = dungeonState();
    var ck = countIn($('#checklist'));
    var ql = countIn(document, '.allq input[type=checkbox]');
    var box = $('#progreso');
    if (box) box.innerHTML = '<span>Mazmorras <b>' + dg[0] + '/' + dg[1] + '</b></span>' +
      '<span>Imprescindibles <b>' + ck[0] + '/' + ck[1] + '</b></span>' +
      '<span>Quests de zona <b>' + ql[0] + '/' + ql[1] + '</b></span>';
    if (typeof renderNow === 'function') renderNow();
  }
  function restore(){
    boxes.forEach(function(b){ b.checked = store.get('chk-' + b.dataset.k) === '1'; });
    $$('details.ck, details.allq, details.dg').forEach(updateContainer);
    updateGlobal();
  }
  document.addEventListener('change', function(e){
    var b = e.target;
    if (!b.matches || !b.matches('input[type=checkbox][data-k]')) return;
    store.set('chk-' + b.dataset.k, b.checked ? '1' : '0');
    // la misma quest puede aparecer en su zona y en su mazmorra
    $$('input[data-k="' + b.dataset.k + '"]').forEach(function(o){ o.checked = b.checked; });
    var d = b.closest('details');
    while (d){ updateContainer(d); d = d.parentElement ? d.parentElement.closest('details') : null; }
    updateGlobal();
  });

  // ---------------------------------------------------------------- nivel
  var lvl = $('#nivel');
  var saved = parseInt(store.get('nivel'), 10);
  if (saved >= 1 && saved <= 60) lvl.value = saved;
  function L(){ var v = parseInt(lvl.value, 10); return v >= 1 && v <= 60 ? v : 0; }
  function applyLevel(){
    var v = L();
    $$('[data-lv]').forEach(function(el){
      var p = el.dataset.lv.split('-'), a = +p[0], b = +p[1];
      el.classList.toggle('at-level', v > 0 && a > 0 && v >= a && v <= b);
    });
    var now = $('.g-now');
    if (now){
      now.hidden = !(v >= 10);
      now.style.setProperty('--p', (Math.max(10, Math.min(60, v)) - 10) / 50);
      now.dataset.l = v;
    }
    renderNow();
  }
  lvl.addEventListener('input', function(){ store.set('nivel', lvl.value); applyLevel(); });

  // ---------------------------------------------------------------- panel "ahora"
  function chip(href, name, lv, cls){
    return '<li><a class="chip' + (cls ? ' ' + cls : '') + '" href="#' + href + '">' + esc(name) + ' <span class="lv">' + lv + '</span></a></li>';
  }
  function isDone(k){ var b = $('input[data-dg="' + k + '"]'); return !!(b && b.checked); }
  function renderNow(){
    var host = $('#now'); if (!host) return;
    var v = L(); $('#now-lvl').textContent = v || '?';
    if (!v){ host.innerHTML = '<div class="tile"><p>Escribe tu nivel en el panel lateral.</p></div>'; return; }
    var zs = D.zones.filter(function(z){ return v >= z.a && v <= z.b; }).sort(function(x, y){ return x.a - y.a; });
    var zn = D.zones.filter(function(z){ return z.a > v && z.a <= v + 3; });
    var ds = D.dungeons.filter(function(d){ return v >= d.a && v <= d.b; });
    var dn = D.dungeons.filter(function(d){ return d.a > v && d.a <= v + 4; });
    var past = D.miles.filter(function(m){ return m[0] <= v; }).slice(-2);
    var next = D.miles.filter(function(m){ return m[0] > v; }).slice(0, 3);
    var pr = D.prof.filter(function(p){ return v <= p[0]; })[0] || D.prof[D.prof.length - 1];
    var h = '';
    h += '<div class="tile"><h4>Zonas de tu nivel</h4><ul class="chips">' +
      (zs.map(function(z){ return chip(z.id, z.n, z.a + '-' + z.b); }).join('') || '<li><small>Ninguna en la guía.</small></li>') + '</ul>' +
      (zn.length ? '<small>Pronto:</small><ul class="chips">' + zn.map(function(z){ return chip(z.id, z.n, z.a + '-' + z.b, 'soon'); }).join('') + '</ul>' : '') + '</div>';
    h += '<div class="tile"><h4>Mazmorras en rango</h4><ul class="chips">' +
      (ds.map(function(d){ return chip('dg-' + d.g, d.n, d.a + '-' + d.b, isDone(d.k) ? 'done' : ''); }).join('') || '<li><small>Ninguna todavía: la primera es a nivel 13.</small></li>') + '</ul>' +
      (dn.length ? '<small>Pronto:</small><ul class="chips">' + dn.map(function(d){ return chip('dg-' + d.g, d.n, d.a + '-' + d.b, 'soon'); }).join('') + '</ul>' : '') + '</div>';
    h += '<div class="tile"><h4>Lo que tienes y lo que viene</h4><ul class="ms">' +
      past.map(function(m){ return '<li class="past"><span class="lv">' + m[0] + '</span><span>' + esc(m[1]) + '</span></li>'; }).join('') +
      next.map(function(m){ return '<li><span class="lv">' + m[0] + '</span><span>' + esc(m[1]) + '</span></li>'; }).join('') + '</ul></div>';
    h += '<div class="tile"><h4>Profesiones a este nivel</h4><p>' + esc(pr[1]) + '</p><p>' + esc(pr[2]) + '</p><small><a href="#profesiones">Ver rutas y materiales que guardar</a></small></div>';
    host.innerHTML = h;
  }

  // ---------------------------------------------------------------- enlaces internos: abrir la sección plegada
  function reveal(id){
    var t = document.getElementById(id); if (!t) return;
    var d = t.tagName === 'DETAILS' ? t : t.closest('details');
    while (d){ d.open = true; d = d.parentElement ? d.parentElement.closest('details') : null; }
    t.scrollIntoView({ block: 'start' });
  }
  document.addEventListener('click', function(e){
    var a = e.target.closest ? e.target.closest('a[href^="#"]') : null;
    if (!a) return;
    var id = a.getAttribute('href').slice(1);
    if (id && document.getElementById(id)){ e.preventDefault(); reveal(id); if (window.history && history.replaceState) { try { history.replaceState(null, '', '#' + id); } catch(err){} } }
    var toc = $('nav.toc details.toc-list');
    if (toc && a.closest('nav.toc') && window.matchMedia('(max-width: 900px)').matches) toc.open = false;
  });

  // ---------------------------------------------------------------- fichas emergentes
  var pop = document.createElement('div'); pop.id = 'pop'; pop.hidden = true; pop.setAttribute('role', 'tooltip');
  document.body.appendChild(pop);
  var touch = window.matchMedia('(hover: none)').matches;
  var cur = null, hideT = null;
  function money(c){ var g = Math.floor(c / 10000), s = Math.floor(c % 10000 / 100), k = c % 100; return (g ? g + ' o ' : '') + (s ? s + ' p ' : '') + (k && !g ? k + ' c' : ''); }
  function coord(c){ return c ? (c[2] ? esc(c[2]) + ' ' : '') + '(' + c[0] + ', ' + c[1] + ')' : ''; }
  function items(list){ return list.map(function(i){ return '<span class="q' + i[2] + '">' + esc(i[1]) + '</span>'; }).join(', '); }
  var TY = { Elite: 'élite', Dungeon: 'mazmorra', Raid: 'raid', PvP: 'JcJ' };
  function questHTML(id){
    var q = D.q[id]; if (!q) return '';
    var sub = ['nivel ' + q.l + (q.m ? ' (desde ' + q.m + ')' : ''), q.z];
    if (q.t) sub.push(TY[q.t] || q.t);
    if (q.gr) sub.push('grupo de ' + q.gr);
    if (q.ti) sub.push('con tiempo');
    var h = '<div class="p-h">' + esc(q.n) + '</div><div class="p-s">' + esc(sub.filter(Boolean).join(' · ')) + '</div>';
    if (q.o) h += '<div class="p-o">' + esc(q.o) + '</div>';
    h += '<dl>';
    if (q.g) h += '<dt>Empieza</dt><dd>' + esc(q.g[2]) + (q.gc ? ' · ' + coord(q.gc) : '') + '</dd>';
    else if (q.gc) h += '<dt>Empieza</dt><dd>' + coord(q.gc) + '</dd>';
    if (q.e) h += '<dt>Entrega</dt><dd>' + esc(q.e[2]) + (q.ec ? ' · ' + coord(q.ec) : '') + '</dd>';
    if (q.pv) h += '<dt>Te dan</dt><dd>' + esc(q.pv[1]) + '</dd>';
    var rw = [];
    if (q.x) rw.push(q.x + ' XP');
    if (q.c) rw.push(money(q.c));
    if (rw.length) h += '<dt>Premio</dt><dd>' + rw.join(' · ') + '</dd>';
    if (q.rc) h += '<dt>A elegir</dt><dd>' + items(q.rc) + '</dd>';
    if (q.r) h += '<dt>Además</dt><dd>' + items(q.r) + '</dd>';
    if (q.p) h += '<dt>Reputación</dt><dd>' + q.p.map(function(p){ return '+' + p[1] + ' ' + esc(p[0]); }).join(', ') + '</dd>';
    if (q.k){
      var prev = q.k[3] && D.q[q.k[3]] ? D.q[q.k[3]].n : '', nxt = q.k[4] && D.q[q.k[4]] ? D.q[q.k[4]].n : '';
      h += '<dt>Cadena</dt><dd>' + esc(q.k[0]) + ', paso ' + q.k[1] + ' de ' + q.k[2] +
        (prev ? '<br>Antes: ' + esc(prev) : '') + (nxt ? '<br>Después: ' + esc(nxt) : '') + '</dd>';
    }
    return h + '</dl>';
  }
  function itemHTML(id){
    var it = D.i[id]; if (!it) return '';
    return '<div class="p-h q' + it.q + '">' + esc(it.n) + '</div>' + it.l.map(function(l){ return '<div class="p-l">' + esc(l) + '</div>'; }).join('');
  }
  function npcHTML(id){
    var n = D.n[id]; if (!n) return '';
    return '<div class="p-h">' + esc(n[0]) + '</div>' + (n.length > 2 ? '<div class="p-o">' + coord([n[1], n[2], n[3]]) + '</div>' : '<div class="p-s">Sin ubicación en los datos</div>');
  }
  function content(a){
    if (a.dataset.tip) return '<div class="p-o">' + esc(a.dataset.tip) + '</div>';
    var t = a.dataset.t, id = a.dataset.id, h = '';
    if (t === 'quest') h = questHTML(id); else if (t === 'item') h = itemHTML(id); else if (t === 'npc') h = npcHTML(id);
    if (!h) return '';
    var where = mode === 'wdb' ? 'Warcraft DB' : 'Wowhead';
    return h + '<div class="p-f"><span>' + (touch ? '' : 'Clic para abrir en ' + where) + '</span>' +
      (touch ? '<a href="' + a.href + '" target="_blank" rel="noopener">Abrir en ' + where + '</a>' : '') + '</div>';
  }
  function show(a){
    var h = content(a); if (!h) return false;
    clearTimeout(hideT); cur = a; pop.innerHTML = h; pop.hidden = false;
    var r = a.getBoundingClientRect(), pw = pop.offsetWidth, ph = pop.offsetHeight;
    var x = Math.max(12, Math.min(r.left, window.innerWidth - pw - 12));
    var y = r.bottom + 8;
    if (y + ph > window.innerHeight - 8) y = Math.max(8, r.top - ph - 8);
    pop.style.left = x + 'px'; pop.style.top = y + 'px';
    return true;
  }
  function hide(){ pop.hidden = true; cur = null; }
  function target(e){ return e.target.closest ? e.target.closest('a.x[data-t], .gr[data-tip]') : null; }
  if (!touch){
    document.addEventListener('mouseover', function(e){ var a = target(e); if (a && a !== cur) show(a); else if (e.target.closest && e.target.closest('#pop')) clearTimeout(hideT); });
    document.addEventListener('mouseout', function(e){ if (target(e) || (e.target.closest && e.target.closest('#pop'))){ clearTimeout(hideT); hideT = setTimeout(hide, 140); } });
    document.addEventListener('focusin', function(e){ var a = target(e); if (a) show(a); });
    document.addEventListener('focusout', function(){ hide(); });
  } else {
    document.addEventListener('click', function(e){
      var a = target(e);
      if (a && a !== cur && !a.classList.contains('gr')){ if (show(a)) e.preventDefault(); }
      else if (!(e.target.closest && e.target.closest('#pop'))) hide();
    });
  }
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') hide(); });
  window.addEventListener('scroll', function(){ if (!pop.hidden && !touch) hide(); }, { passive: true });

  // ---------------------------------------------------------------- búsqueda
  var q = $('#buscar'), count = $('#search-count');
  var units = null, textCache = new Map(), openState = new Map(), timer = null;
  function runSearch(){
    var term = q.value.trim().toLowerCase();
    if (!units) units = $$('details.zona, details.allq, .tw tbody tr, ol.steps > li, ul.ql > li, .keyitems > li, .bosses > li');
    var hits = 0;
    units.forEach(function(u){
      var isD = u.tagName === 'DETAILS';
      if (!term){
        u.classList.remove('hidden-by-search');
        if (isD && openState.has(u)) u.open = openState.get(u);
        return;
      }
      if (isD && !openState.has(u)) openState.set(u, u.open);
      var txt = textCache.get(u);
      if (txt === undefined){ txt = u.textContent.toLowerCase(); textCache.set(u, txt); }
      var m = txt.indexOf(term) !== -1;
      u.classList.toggle('hidden-by-search', !m);
      if (m){ if (isD) u.open = true; else hits++; }
    });
    if (!term){ openState.clear(); count.textContent = ''; }
    else count.textContent = hits ? hits + ' resultados' : 'Sin resultados para «' + q.value.trim() + '»';
  }
  q.addEventListener('input', function(){ clearTimeout(timer); timer = setTimeout(runSearch, 180); });
  document.addEventListener('keydown', function(e){
    if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)){ e.preventDefault(); q.focus(); }
  });

  // ---------------------------------------------------------------- copiar y cargar progreso
  var code = $('#sync-code'), msg = $('#sync-msg');
  function exportCode(){
    var on = {};
    boxes.forEach(function(b){ if (b.checked) on[b.dataset.k] = 1; });
    return btoa(unescape(encodeURIComponent(JSON.stringify({ v: 1, nivel: lvl.value, fichas: mode, on: Object.keys(on) }))));
  }
  var bc = $('#sync-copy'), bl = $('#sync-load');
  if (bc) bc.addEventListener('click', function(){
    code.value = exportCode(); code.select();
    var done = function(){ msg.textContent = 'Código copiado.'; }, sel = function(){ msg.textContent = 'Código listo: cópialo del cuadro.'; };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(code.value).then(done, sel); else sel();
  });
  if (bl) bl.addEventListener('click', function(){
    try {
      var d = JSON.parse(decodeURIComponent(escape(atob(code.value.trim()))));
      var on = {}; (d.on || []).forEach(function(k){ on[k] = 1; });
      boxes.forEach(function(b){ store.set('chk-' + b.dataset.k, on[b.dataset.k] ? '1' : '0'); });
      if (d.nivel){ lvl.value = d.nivel; store.set('nivel', d.nivel); }
      restore(); applyLevel();
      msg.textContent = 'Progreso cargado: ' + (d.on || []).length + ' casillas.';
    } catch (err){ msg.textContent = 'Ese código no es válido. Cópialo entero desde el otro dispositivo.'; }
  });

  // ---------------------------------------------------------------- arranque
  var tocList = $('nav.toc details.toc-list');
  if (tocList && window.matchMedia('(max-width: 900px)').matches) tocList.open = false;
  restore();
  applyLevel();
  if (location.hash.length > 1) reveal(location.hash.slice(1));

  // Versión local: imprimir con todo desplegado y restaurar después
  if (LOCAL){
    var prevOpen = [];
    window.addEventListener('beforeprint', function(){
      prevOpen = [];
      $$('details.zona, details.sync').forEach(function(d){ prevOpen.push([d, d.open]); d.open = !d.classList.contains('sync'); });
    });
    window.addEventListener('afterprint', function(){ prevOpen.forEach(function(p){ p[0].open = p[1]; }); });
    var pb = $('#imprimir');
    if (pb) pb.addEventListener('click', function(){ window.print(); });
  }
})();
