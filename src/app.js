(function(){
  var D = JSON.parse(document.getElementById('gd').textContent);
  var LOCAL = document.body.classList.contains('local');
  var PRINT_ALL = document.body.classList.contains('print-all');
  var $ = function(s, r){ return (r || document).querySelector(s); };
  var $$ = function(s, r){ return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var store = {
    get: function(k){ try { return window.localStorage.getItem(k); } catch(e){ return null; } },
    set: function(k, v){ try { window.localStorage.setItem(k, v); return true; } catch(e){ return false; } }
  };
  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  var VIEWS = ['inicio', 'zonas', 'mazmorras', 'cadenas', 'chaman', 'referencia'];
  var cur = { view: 'inicio', page: null };

  // grupos de mazmorra (una entrada por mazmorra, con sus alas)
  var DG = [], dgBy = {};
  D.dungeons.forEach(function(d){
    var g = dgBy[d.g];
    if (!g){ g = dgBy[d.g] = { g: d.g, n: d.gn, a: d.a, b: d.b, loc: d.loc, isNew: d['new'], wings: [] }; DG.push(g); }
    g.a = Math.min(g.a, d.a); g.b = Math.max(g.b, d.b); g.wings.push(d.k);
  });

  // ---------------------------------------------------------------- destino de los enlaces
  var BASE = { wh: 'https://www.wowhead.com/forever/', whes: 'https://www.wowhead.com/forever/es/', wdb: 'https://forever.warcraftdb.com/' };
  var mode = store.get('fichas') || 'wh';
  if (!BASE[mode]) mode = 'wh';
  function url(t, id){
    if (t === 'search') return (mode === 'whes' ? BASE.whes : BASE.wh) + 'search?q=' + encodeURIComponent(id);
    return mode === 'wdb' ? BASE.wdb + 'data/' + t + '/' + id : BASE[mode] + t + '=' + id;
  }
  function applyLinks(){ $$('a.x').forEach(function(a){ a.href = url(a.dataset.t, a.dataset.t === 'search' ? a.dataset.q : a.dataset.id); }); }
  var sel = $('#fichas');
  if (sel){ sel.value = mode; sel.addEventListener('change', function(){ mode = sel.value; store.set('fichas', mode); applyLinks(); }); }
  if (mode !== 'wh') applyLinks();

  // ---------------------------------------------------------------- casillas y progreso
  var boxes = $$('input[type=checkbox][data-k]');
  function countIn(el, q){
    if (!el) return [0, 0];
    var all = $$(q || 'input[type=checkbox][data-k]', el);
    return [all.filter(function(b){ return b.checked; }).length, all.length];
  }
  function uniq(q){
    var seen = {}, on = 0, n = 0;
    $$(q).forEach(function(b){ if (seen[b.dataset.k]) return; seen[b.dataset.k] = 1; n++; if (b.checked) on++; });
    return [on, n];
  }
  function updateBlocks(root){
    $$('.blk', root || document).forEach(function(b){
      var p = $('.prog', b); if (!p) return;
      var c = countIn(b); p.textContent = c[1] ? c[0] + '/' + c[1] : '';
    });
  }
  function isDone(k){ var b = $('input[data-dg="' + k + '"]'); return !!(b && b.checked); }
  function zoneDone(id){ var b = $('input[data-zdone="' + id + '"]'); return !!(b && b.checked); }
  function refresh(){
    $$('input[data-dg]').forEach(function(b){
      var row = $('.gr[data-dg="' + b.dataset.dg + '"]'); if (row) row.classList.toggle('done', b.checked);
    });
    var dg = countIn(document, 'input[data-dg]'), im = uniq('.blk.imp input[data-k]'), ql = countIn(document, '.allq input[data-k]'), rt = countIn($('#ruta'));
    var box = $('#progreso');
    if (box) box.innerHTML = '<span>Mazmorras <b>' + dg[0] + '/' + dg[1] + '</b></span><span>Imprescindibles <b>' + im[0] + '/' + im[1] +
      '</b></span><span>Quests de zona <b>' + ql[0] + '/' + ql[1] + '</b></span><span>Ruta <b>' + rt[0] + '/' + rt[1] + '</b></span>';
    updateChains(); renderCards(); renderSide(); renderNow(); updateRoute();
  }
  function restore(){
    boxes.forEach(function(b){ var v = store.get('chk-' + b.dataset.k); b.checked = v === null ? b.defaultChecked : v === '1'; });
    updateBlocks(); refresh();
  }
  document.addEventListener('change', function(e){
    var b = e.target;
    if (!b.matches || !b.matches('input[type=checkbox][data-k]')) return;
    savedToast(store.set('chk-' + b.dataset.k, b.checked ? '1' : '0'));
    $$('input[data-k="' + b.dataset.k + '"]').forEach(function(o){ o.checked = b.checked; });
    // una fila de varios pasos marcada da por hechos todos sus pasos
    if (b.checked && b.dataset.all) b.dataset.all.split(',').forEach(function(id){
      store.set('chk-q' + id, '1'); $$('input[data-k="q' + id + '"]').forEach(function(o){ o.checked = true; });
    });
    updateBlocks(b.dataset.all ? document : b.closest('.page') || document); refresh();
  });

  // aviso de guardado
  var toast = document.createElement('div'), toastT = null;
  toast.id = 'saved'; toast.setAttribute('aria-live', 'polite'); document.body.appendChild(toast);
  function savedToast(ok){
    toast.textContent = ok ? 'Guardado en este navegador' : 'Este navegador no deja guardar: la marca se perderá al cerrar la página';
    toast.className = ok ? 'on' : 'on bad';
    clearTimeout(toastT); toastT = setTimeout(function(){ toast.className = ''; }, ok ? 1300 : 6000);
  }

  // cadenas: progreso y paso siguiente
  var CH = {};
  function chainState(c){ return CH[c.k] || { done: 0, n: c.n, next: 1 }; }
  function updateChains(){
    (D.chains || []).forEach(function(c){
      var pg = document.getElementById('cad-' + c.k); if (!pg) return;
      var lis = $$('ol.chain > li', pg), done = 0, next = 0;
      lis.forEach(function(li, i){
        var on = $('input', li).checked;
        li.classList.toggle('done', on); li.classList.remove('next');
        if (on) done++; else if (!next){ next = i + 1; li.classList.add('next'); }
      });
      CH[c.k] = { done: done, n: lis.length, next: next };
      var cp = $('.cprog', pg);
      if (cp) cp.textContent = done === lis.length ? 'completada' : done ? done + ' de ' + lis.length + ' · sigue el paso ' + next : 'sin empezar';
    });
    $$('a.clink').forEach(function(a){
      var s = CH[a.dataset.chain]; if (!s) return;
      a.classList.toggle('done', s.done === s.n);
      $('.cl-p', a).textContent = s.done === s.n ? 'completada' : s.done ? s.done + '/' + s.n + ' · sigue el paso ' + s.next : s.n + ' pasos';
    });
  }

  // pasos de la ruta: hecho, pendiente de antes o el que toca
  function updateRoute(){
    var v = L();
    $$('#ruta .steps > li').forEach(function(li){
      var c = countIn(li), p = (li.dataset.lv || '').split('-'), b = +p[1];
      var done = c[1] > 0 && c[0] === c[1], behind = !done && v > b;
      li.classList.toggle('done', done); li.classList.toggle('behind', behind);
      var t = $('.st-tag', li);
      if (t) t.textContent = done ? 'hecho' : behind ? 'te queda ' + (c[1] - c[0]) + ' de ' + c[1] : c[0] ? c[0] + ' de ' + c[1] : '';
    });
  }

  // ---------------------------------------------------------------- nivel
  var lvl = $('#nivel');
  var saved = parseInt(store.get('nivel'), 10);
  if (saved >= 1 && saved <= 60) lvl.value = saved;
  function L(){ var v = parseInt(lvl.value, 10); return v >= 1 && v <= 60 ? v : 0; }
  function inRange(v, a, b){ return v > 0 && a != null && v >= a && v <= b; }
  function applyLevel(){
    var v = L();
    $$('[data-lv]').forEach(function(el){ var p = el.dataset.lv.split('-'); el.classList.toggle('at-level', inRange(v, +p[0], +p[1])); });
    var now = $('.g-now');
    if (now){ now.hidden = !(v >= 10); now.style.setProperty('--p', (Math.max(10, Math.min(60, v)) - 10) / 50); now.dataset.l = v; }
    renderCards(); renderSide(); renderNow(); updateRoute();
  }
  lvl.addEventListener('input', function(){ store.set('nivel', lvl.value); applyLevel(); });

  // ---------------------------------------------------------------- tarjetas de zonas y mazmorras
  function bar(done, total){ return '<span class="bar"><i style="width:' + (total ? Math.round(done / total * 100) : 0) + '%"></i></span>'; }
  function renderCards(){
    var v = L(), host = $('#zcards');
    if (host){
      var groups = [], by = {};
      D.zones.forEach(function(z){
        if (!by[z.grp]){ by[z.grp] = []; groups.push(z.grp); }
        var pg = document.getElementById(z.id), im = countIn(pg, '.imp input'), q = countIn(pg, '.allq input'), done = zoneDone(z.id);
        by[z.grp].push('<a class="card' + (inRange(v, z.a, z.b) && !done ? ' at-level' : '') + (done ? ' done' : '') + '" href="#' + z.id + '">' +
          '<span class="c-h"><b>' + esc(z.n) + '</b><span class="lv">' + esc(z.lv) + '</span></span>' +
          '<span class="c-s">' + esc(z.base) + (z['new'] ? ' · nueva en Forever' : '') + '</span>' + bar(im[0] + q[0], im[1] + q[1]) +
          '<span class="c-f">' + (im[1] ? 'Imprescindibles ' + im[0] + '/' + im[1] + ' · ' : '') + 'Quests ' + q[0] + '/' + q[1] + '</span></a>');
      });
      host.innerHTML = groups.map(function(g){ return '<h4 class="cg">' + esc(g) + '</h4><div class="cards">' + by[g].join('') + '</div>'; }).join('');
    }
    host = $('#ccards');
    if (host){
      var cg = [], cby = {};
      (D.chains || []).forEach(function(c){
        if (!cby[c.g]){ cby[c.g] = []; cg.push(c.g); }
        var s = chainState(c), done = s.done === s.n;
        cby[c.g].push('<a class="card' + (inRange(v, c.a, c.b) && !done ? ' at-level' : '') + (done ? ' done' : '') + '" href="#cad-' + c.k + '">' +
          '<span class="c-h"><b>' + esc(c.t) + '</b><span class="lv">' + esc(c.lv) + '</span></span>' + bar(s.done, s.n) +
          '<span class="c-f">' + (done ? 'Completada' : s.done ? 'Vas por el paso ' + s.next + ' de ' + s.n : s.n + ' pasos') + '</span></a>');
      });
      host.innerHTML = cg.map(function(g){ return '<h4 class="cg">' + esc(g) + '</h4><div class="cards">' + cby[g].join('') + '</div>'; }).join('');
    }
    host = $('#dcards');
    if (host){
      host.innerHTML = '<div class="cards">' + DG.map(function(g){
        var pg = document.getElementById('dg-' + g.g), q = countIn(pg, '.dq input');
        var wd = g.wings.filter(isDone).length, done = wd === g.wings.length;
        return '<a class="card' + (inRange(v, g.a, g.b) && !done ? ' at-level' : '') + (done ? ' done' : '') + '" href="#dg-' + g.g + '">' +
          '<span class="c-h"><b>' + esc(g.n) + '</b><span class="lv">' + g.a + '-' + g.b + '</span></span>' +
          '<span class="c-s">' + esc(g.loc) + (g.isNew ? ' · nueva en Forever' : '') + '</span>' + bar(q[0], q[1]) +
          '<span class="c-f">' + (g.wings.length > 1 ? 'Alas ' + wd + '/' + g.wings.length + ' · ' : '') + 'Quests ' + q[0] + '/' + q[1] + '</span></a>';
      }).join('') + '</div>';
    }
  }

  // ---------------------------------------------------------------- menú lateral según la sección
  function renderSide(){
    var side = $('#side'), shell = $('.shell'), v = L(), h = '';
    if (!side) return;
    var pid = cur.page ? cur.page.id : '';
    if (cur.view === 'zonas'){
      h = '<a class="s-all' + (pid ? '' : ' on') + '" href="#zonas">Todas las zonas</a>';
      var last = '';
      D.zones.forEach(function(z){
        if (z.grp !== last){ h += '<h4>' + esc(z.grp) + '</h4>'; last = z.grp; }
        h += '<a href="#' + z.id + '" class="' + (z.id === pid ? 'on ' : '') + (inRange(v, z.a, z.b) ? 'at-level ' : '') + (zoneDone(z.id) ? 'done' : '') +
          '"><span>' + esc(z.n) + '</span><span class="lv">' + esc(z.lv) + '</span></a>';
      });
    } else if (cur.view === 'mazmorras'){
      h = '<a class="s-all' + (pid ? '' : ' on') + '" href="#mazmorras">Todas las mazmorras</a><h4>Por nivel</h4>';
      DG.forEach(function(g){
        var done = g.wings.filter(isDone).length === g.wings.length;
        h += '<a href="#dg-' + g.g + '" class="' + ('dg-' + g.g === pid ? 'on ' : '') + (inRange(v, g.a, g.b) ? 'at-level ' : '') + (done ? 'done' : '') +
          '"><span>' + esc(g.n) + '</span><span class="lv">' + g.a + '-' + g.b + '</span></a>';
      });
    } else if (cur.view === 'cadenas'){
      h = '<a class="s-all' + (pid ? '' : ' on') + '" href="#cadenas">Todas las cadenas</a>';
      var lg = '';
      (D.chains || []).forEach(function(c){
        if (c.g !== lg){ h += '<h4>' + esc(c.g) + '</h4>'; lg = c.g; }
        var s = chainState(c);
        h += '<a href="#cad-' + c.k + '" class="' + ('cad-' + c.k === pid ? 'on ' : '') + (inRange(v, c.a, c.b) ? 'at-level ' : '') + (s.done === s.n ? 'done' : '') +
          '"><span>' + esc(c.t) + '</span><span class="lv">' + esc(c.lv) + '</span></a>';
      });
    } else if (cur.view === 'chaman' || cur.view === 'referencia'){
      h = '<h4>En esta sección</h4>';
      $$('#v-' + cur.view + ' > section.sec').forEach(function(s){
        var t = $('h2', s); if (t && s.id) h += '<a href="#' + s.id + '"><span>' + esc(t.textContent.trim()) + '</span></a>';
      });
    }
    side.innerHTML = h;
    shell.classList.toggle('noside', !h);
    var on = $('a.on', side); if (on && on.scrollIntoView && !PRINT_ALL) on.scrollIntoView({ block: 'nearest' });
  }

  // ---------------------------------------------------------------- inicio: panel por nivel y pendientes
  function chip(href, name, lv, cls){ return '<li><a class="chip' + (cls ? ' ' + cls : '') + '" href="#' + href + '">' + esc(name) + ' <span class="lv">' + esc(lv) + '</span></a></li>'; }
  function renderNow(){
    var host = $('#now'); if (!host) return;
    var v = L(); $('#now-lvl').textContent = v || '?';
    if (!v){ host.innerHTML = '<div class="tile"><p>Escribe tu nivel arriba.</p></div>'; return; }
    var zs = D.zones.filter(function(z){ return inRange(v, z.a, z.b); });
    var zn = D.zones.filter(function(z){ return z.a > v && z.a <= v + 3; });
    var ds = D.dungeons.filter(function(d){ return inRange(v, d.a, d.b); });
    var dn = D.dungeons.filter(function(d){ return d.a > v && d.a <= v + 4; });
    var past = D.miles.filter(function(m){ return m[0] <= v; }).slice(-2), next = D.miles.filter(function(m){ return m[0] > v; }).slice(0, 3);
    var pr = D.prof.filter(function(p){ return v <= p[0]; })[0] || D.prof[D.prof.length - 1];
    var h = '<div class="tile"><h4>Zonas de tu nivel</h4><ul class="chips">' +
      (zs.map(function(z){ return chip(z.id, z.n, z.lv, zoneDone(z.id) ? 'done' : ''); }).join('') || '<li><small>Ninguna.</small></li>') + '</ul>' +
      (zn.length ? '<small>Pronto:</small><ul class="chips">' + zn.map(function(z){ return chip(z.id, z.n, z.lv, 'soon'); }).join('') + '</ul>' : '') + '</div>';
    h += '<div class="tile"><h4>Mazmorras en rango</h4><ul class="chips">' +
      (ds.map(function(d){ return chip('dg-' + d.g, d.n, d.a + '-' + d.b, isDone(d.k) ? 'done' : ''); }).join('') || '<li><small>Ninguna todavía: la primera es a nivel 13.</small></li>') + '</ul>' +
      (dn.length ? '<small>Pronto:</small><ul class="chips">' + dn.map(function(d){ return chip('dg-' + d.g, d.n, d.a + '-' + d.b, 'soon'); }).join('') + '</ul>' : '') + '</div>';
    var cs = (D.chains || []).filter(function(c){ var s = chainState(c); return s.done !== s.n && (inRange(v, c.a, c.b) || s.done > 0); });
    h += '<div class="tile"><h4>Cadenas a tu nivel</h4><ul class="chips">' +
      (cs.map(function(c){ var s = chainState(c); return chip('cad-' + c.k, c.t, s.done + '/' + s.n, ''); }).join('') || '<li><small>Ninguna pendiente.</small></li>') + '</ul>' +
      '<small><a href="#cadenas">Ver todas las cadenas paso a paso</a></small></div>';
    h += '<div class="tile"><h4>Lo que tienes y lo que viene</h4><ul class="ms">' +
      past.map(function(m){ return '<li class="past"><span class="lv">' + m[0] + '</span><span>' + esc(m[1]) + '</span></li>'; }).join('') +
      next.map(function(m){ return '<li><span class="lv">' + m[0] + '</span><span>' + esc(m[1]) + '</span></li>'; }).join('') + '</ul></div>';
    h += '<div class="tile"><h4>Profesiones a este nivel</h4><p>' + esc(pr[1]) + '</p><p>' + esc(pr[2]) + '</p><small><a href="#profesiones">Ver rutas y materiales que guardar</a></small></div>';
    host.innerHTML = h;
    var pend = $('#pend');
    if (pend){
      var seen = {}, items = [];
      zs.forEach(function(z){
        if (zoneDone(z.id)) return;
        $$('#' + z.id + ' .blk.imp input[data-k]').forEach(function(b){
          if (b.checked || seen[b.dataset.k]) return; seen[b.dataset.k] = 1;
          var c = b.parentNode.cloneNode(true); $$('.tag', c).forEach(function(x){ x.remove(); });
          var t = c.textContent.replace(/\s+/g, ' ').trim(); if (t.length > 150) t = t.slice(0, 147) + '…';
          items.push('<li><a href="#' + z.id + '"><b>' + esc(z.n) + '</b>' + esc(t) + '</a></li>');
        });
      });
      pend.innerHTML = items.length ? '<ul class="pend">' + items.join('') + '</ul>' : '<p class="src">Nada pendiente en las zonas de tu nivel.</p>';
    }
  }

  // ---------------------------------------------------------------- navegación entre secciones y páginas
  var pending = null;
  function pageOrder(page){
    if (page.classList.contains('zpage')) return D.zones.map(function(z){ return { id: z.id, n: z.n }; });
    if (page.classList.contains('cpage')) return (D.chains || []).map(function(c){ return { id: 'cad-' + c.k, n: c.t }; });
    return DG.map(function(g){ return { id: 'dg-' + g.g, n: g.n }; });
  }
  function addPrevNext(page){
    if ($('.pn', page)) return;
    var list = pageOrder(page), i = -1;
    list.forEach(function(x, k){ if (x.id === page.id) i = k; });
    var p = list[i - 1], n = list[i + 1], nav = document.createElement('nav');
    nav.className = 'pn';
    nav.innerHTML = (p ? '<a href="#' + p.id + '">← ' + esc(p.n) + '</a>' : '<span></span>') + (n ? '<a href="#' + n.id + '">' + esc(n.n) + ' →</a>' : '<span></span>');
    page.appendChild(nav);
  }
  function route(id){
    if (PRINT_ALL) return;
    id = (id != null ? id : (location.hash || '')).replace(/^#/, '');
    try { id = decodeURIComponent(id); } catch(e){}
    var view = 'inicio', page = null, target = null;
    if (VIEWS.indexOf(id) >= 0) view = id;
    else if (id){
      var el = document.getElementById(id);
      if (el){
        var v = el.closest('.view'); if (v) view = v.id.slice(2);
        page = el.classList.contains('page') ? el : el.closest('.page');
        if (el !== page) target = el;
      }
    }
    cur = { view: view, page: page };
    $$('.view').forEach(function(v){ v.hidden = v.id !== 'v-' + view; });
    $$('.tabs a').forEach(function(a){ a.classList.toggle('on', a.dataset.view === view); });
    var vEl = $('#v-' + view), pages = $$('.page', vEl), ov = $('.overview', vEl);
    pages.forEach(function(p){ p.hidden = p !== page; });
    if (ov) ov.hidden = !!page;
    if (page) addPrevNext(page);
    renderSide();
    var go = pending || target; pending = null;
    if (go){
      go.scrollIntoView({ block: go === target ? 'start' : 'center' });
      if (go !== target){ go.classList.add('flash'); setTimeout(function(){ go.classList.remove('flash'); }, 1700); }
    } else window.scrollTo(0, 0);
  }
  function navigate(id){
    if (('#' + id) === location.hash) { route(id); return; }
    try { location.hash = id; } catch(e){ route(id); }
  }
  window.addEventListener('hashchange', function(){ route(); });
  document.addEventListener('click', function(e){
    var a = e.target.closest ? e.target.closest('a[href^="#"]') : null;
    if (!a || a.classList.contains('res')) return;
    var id = a.getAttribute('href').slice(1);
    if (!id) return;
    e.preventDefault(); navigate(id);
    var cfg = $('details.cfg'); if (cfg) cfg.open = false;
  });

  // filtros de la lista de quests
  document.addEventListener('click', function(e){
    var b = e.target.closest ? e.target.closest('.filters button') : null; if (!b) return;
    var box = b.closest('.allq');
    $$('.filters button', box).forEach(function(o){ o.classList.toggle('on', o === b); });
    box.classList.remove('f-pend', 'f-new', 'f-star');
    if (b.dataset.f) box.classList.add('f-' + b.dataset.f);
  });

  // ---------------------------------------------------------------- fichas emergentes
  var pop = document.createElement('div'); pop.id = 'pop'; pop.hidden = true; pop.setAttribute('role', 'tooltip');
  document.body.appendChild(pop);
  var touch = window.matchMedia('(hover: none)').matches;
  var curA = null, hideT = null;
  function money(c){ var g = Math.floor(c / 10000), s = Math.floor(c % 10000 / 100), k = c % 100; return (g ? g + ' o ' : '') + (s ? s + ' p ' : '') + (k && !g ? k + ' c' : ''); }
  function coord(c){ return c ? (c[2] ? esc(c[2]) + ' ' : '') + '(' + c[0] + ', ' + c[1] + ')' : ''; }
  function items(list){ return list.map(function(i){ return '<span class="q' + i[2] + '">' + esc(i[1]) + '</span>'; }).join(', '); }
  var TY = { Elite: 'élite', Dungeon: 'mazmorra', Raid: 'raid', PvP: 'JcJ' };
  function questHTML(id){
    var q = D.q[id]; if (!q) return '';
    var sub = [q.l ? 'nivel ' + q.l + (q.m ? ' (desde ' + q.m + ')' : '') : '', q.z];
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
      h += '<dt>Cadena</dt><dd>' + esc(q.k[0]) + ', paso ' + q.k[1] + ' de ' + q.k[2] + (prev ? '<br>Antes: ' + esc(prev) : '') + (nxt ? '<br>Después: ' + esc(nxt) : '') + '</dd>';
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
    clearTimeout(hideT); curA = a; pop.innerHTML = h; pop.hidden = false;
    var r = a.getBoundingClientRect(), pw = pop.offsetWidth, ph = pop.offsetHeight;
    var x = Math.max(12, Math.min(r.left, window.innerWidth - pw - 12)), y = r.bottom + 8;
    if (y + ph > window.innerHeight - 8) y = Math.max(8, r.top - ph - 8);
    pop.style.left = x + 'px'; pop.style.top = y + 'px';
    return true;
  }
  function hide(){ pop.hidden = true; curA = null; }
  function target(e){ return e.target.closest ? e.target.closest('a.x[data-t], .gr[data-tip]') : null; }
  if (!touch){
    document.addEventListener('mouseover', function(e){ var a = target(e); if (a && a !== curA) show(a); else if (e.target.closest && e.target.closest('#pop')) clearTimeout(hideT); });
    document.addEventListener('mouseout', function(e){ if (target(e) || (e.target.closest && e.target.closest('#pop'))){ clearTimeout(hideT); hideT = setTimeout(hide, 140); } });
    document.addEventListener('focusin', function(e){ var a = target(e); if (a) show(a); });
    document.addEventListener('focusout', function(){ hide(); });
  } else {
    document.addEventListener('click', function(e){
      var a = target(e);
      if (a && a !== curA && !a.classList.contains('gr')){ if (show(a)) e.preventDefault(); }
      else if (!(e.target.closest && e.target.closest('#pop'))) hide();
    }, true);
  }
  window.addEventListener('scroll', function(){ if (!pop.hidden && !touch) hide(); }, { passive: true });

  // ---------------------------------------------------------------- buscador que lleva al sitio
  var q = $('#buscar'), results = $('#results'), idx = null, found = [], timer = null;
  function pageName(el){ var p = el.closest('.page'); return p ? p.dataset.name : ''; }
  function buildIndex(){
    idx = [];
    var seen = {};
    function add(t, n, c, ref){ n = (n || '').trim(); if (!n) return; var k = t + '|' + n + '|' + c; if (seen[k]) return; seen[k] = 1; idx.push({ t: t, n: n, c: c, s: n.toLowerCase(), ref: ref }); }
    D.zones.forEach(function(z){ add('Zona', z.n, 'niveles ' + z.lv, z.id); });
    DG.forEach(function(g){ add('Mazmorra', g.n, 'niveles ' + g.a + '-' + g.b + ' · ' + g.loc, 'dg-' + g.g); });
    (D.chains || []).forEach(function(c){ add('Cadena', c.t, 'niveles ' + c.lv + ' · ' + c.n + ' pasos', 'cad-' + c.k); });
    $$('.view > section.sec').forEach(function(s){ var h = $('h2', s); if (h && s.id) add('Sección', h.textContent, '', s.id); });
    $$('ol.chain > li').forEach(function(li){ var a = $('.cs-t a.x-quest, .cs-t b', li); if (a) add('Quest', a.textContent, 'cadena ' + pageName(li), li); });
    $$('ul.ql > li').forEach(function(li){ var a = $('a.x-quest', li); if (a) add('Quest', a.textContent, pageName(li), li); });
    $$('.blk.imp li').forEach(function(li){ var a = $('a.x', li); if (a) add('Quest', a.textContent, pageName(li) + ' · imprescindible', li); });
    $$('.bosses > li > b').forEach(function(b){ add('Jefe', b.textContent, pageName(b), b.parentNode); });
    $$('.keyitems > li, .loot a.x').forEach(function(el){ var a = el.matches('a') ? el : $('a.x', el); if (a) add('Objeto', a.textContent, pageName(el), el); });
  }
  var ORDER = { Zona: 0, Mazmorra: 1, Cadena: 2, 'Sección': 3, Quest: 4, Jefe: 5, Objeto: 6 };
  function runSearch(){
    var term = q.value.trim().toLowerCase();
    if (term.length < 2){ results.hidden = true; return; }
    if (!idx) buildIndex();
    found = idx.filter(function(e){ return e.s.indexOf(term) !== -1; });
    found.sort(function(a, b){ return (a.s.indexOf(term) === 0 ? 0 : 1) - (b.s.indexOf(term) === 0 ? 0 : 1) || ORDER[a.t] - ORDER[b.t] || a.s.localeCompare(b.s); });
    var total = found.length; found = found.slice(0, 40);
    results.innerHTML = found.length ? found.map(function(e, i){
      return '<a class="res' + (i ? '' : ' sel') + '" href="#" data-i="' + i + '"><span class="rt">' + e.t + '</span><span class="rn">' + esc(e.n) + '</span>' +
        (e.c ? '<span class="rc">' + esc(e.c) + '</span>' : '') + '</a>';
    }).join('') + (total > 40 ? '<div class="res-empty">Y ' + (total - 40) + ' más: escribe algo más concreto.</div>' : '')
      : '<div class="res-empty">Sin resultados para «' + esc(q.value.trim()) + '»</div>';
    results.hidden = false;
  }
  function pick(e){
    results.hidden = true; q.blur();
    if (typeof e.ref === 'string'){ navigate(e.ref); return; }
    var p = e.ref.closest('.page'), v = e.ref.closest('.view');
    pending = e.ref;
    var id = p ? p.id : v.id.slice(2);
    if (('#' + id) === location.hash) route(id); else navigate(id);
  }
  q.addEventListener('input', function(){ clearTimeout(timer); timer = setTimeout(runSearch, 140); });
  q.addEventListener('focus', function(){ if (q.value.trim().length >= 2) runSearch(); });
  q.addEventListener('keydown', function(e){
    if (e.key === 'Enter' && found.length && !results.hidden){ e.preventDefault(); pick(found[0]); }
    if (e.key === 'Escape'){ results.hidden = true; q.blur(); }
  });
  results.addEventListener('click', function(e){
    var a = e.target.closest('.res'); if (!a) return;
    e.preventDefault(); pick(found[+a.dataset.i]);
  });
  document.addEventListener('click', function(e){ if (!(e.target.closest && e.target.closest('.search'))) results.hidden = true; });
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape') hide();
    if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)){ e.preventDefault(); q.focus(); }
  });

  // ---------------------------------------------------------------- copiar y cargar progreso
  var code = $('#sync-code'), msg = $('#sync-msg');
  function exportCode(){
    var on = {}, off = {};
    boxes.forEach(function(b){ if (b.checked) on[b.dataset.k] = 1; else if (b.defaultChecked) off[b.dataset.k] = 1; });
    return btoa(unescape(encodeURIComponent(JSON.stringify({ v: 2, nivel: lvl.value, on: Object.keys(on), off: Object.keys(off) }))));
  }
  var bc = $('#sync-copy'), bl = $('#sync-load');
  if (bc) bc.addEventListener('click', function(){
    code.value = exportCode(); code.select();
    var ok = function(){ msg.textContent = 'Código copiado.'; }, manual = function(){ msg.textContent = 'Código listo: cópialo del cuadro.'; };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(code.value).then(ok, manual); else manual();
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

  // ---------------------------------------------------------------- importar quests completadas (Questie o lista de números)
  var impFile = $('#imp-file'), impChar = $('#imp-char'), impIds = $('#imp-ids'), impGo = $('#imp-go'), impMsg = $('#imp-msg'), impData = null;
  function parseQuestie(txt){
    var chars = {}, re = /\["complete"\]\s*=\s*\{/g, m;
    while ((m = re.exec(txt))){
      var i = re.lastIndex, depth = 1;
      while (i < txt.length && depth){ var ch = txt.charAt(i++); if (ch === '{') depth++; else if (ch === '}') depth--; }
      var block = txt.slice(re.lastIndex, i), ids = [], r = /\[(\d+)\]\s*=\s*true|^\s*(\d+),\s*--\s*\[\d+\]/gm, x;
      while ((x = r.exec(block))) ids.push(+(x[1] || x[2]));
      var names = txt.slice(0, m.index).match(/\["([^"\n]+ - [^"\n]+)"\]\s*=\s*\{/g);
      var name = names ? names[names.length - 1].replace(/^\["|"\]\s*=\s*\{$/g, '') : 'Personaje ' + (Object.keys(chars).length + 1);
      if (ids.length) chars[name] = (chars[name] || []).concat(ids);
    }
    return chars;
  }
  function markDone(ids){
    var have = {}, fresh = 0, known = 0;
    boxes.forEach(function(b){ have[b.dataset.k] = 1; });
    ids.forEach(function(id){
      var k = 'q' + id; if (!have[k]) return;
      known++; if (store.get('chk-' + k) !== '1'){ store.set('chk-' + k, '1'); fresh++; }
    });
    restore(); applyLevel();
    return [fresh, known];
  }
  if (impFile) impFile.addEventListener('change', function(){
    var f = impFile.files && impFile.files[0]; impData = null; impChar.hidden = true;
    if (!f) return;
    var rd = new FileReader();
    rd.onload = function(){
      var chars = parseQuestie(String(rd.result)), names = Object.keys(chars);
      if (!names.length){ impMsg.textContent = 'No encuentro la lista de quests completadas en ese archivo. Comprueba que es Questie.lua de la carpeta SavedVariables.'; return; }
      impData = chars;
      names.sort(function(a, b){ return chars[b].length - chars[a].length; });
      impChar.innerHTML = names.map(function(n){ return '<option value="' + esc(n) + '">' + esc(n) + ' · ' + chars[n].length + ' quests</option>'; }).join('');
      impChar.hidden = names.length < 2;
      impMsg.textContent = names.length > 1 ? 'Hay ' + names.length + ' personajes en el archivo: elige uno y pulsa el botón.' : 'Leído «' + names[0] + '»: ' + chars[names[0]].length + ' quests completadas. Pulsa el botón para marcarlas.';
    };
    rd.onerror = function(){ impMsg.textContent = 'No se ha podido leer el archivo.'; };
    rd.readAsText(f);
  });
  if (impGo) impGo.addEventListener('click', function(){
    var ids = [], src = '';
    if (impData){ src = impChar.value || Object.keys(impData)[0]; ids = impData[src] || []; }
    var typed = (impIds.value.match(/\d+/g) || []).map(Number);
    if (typed.length){ ids = ids.concat(typed); src = src ? src + ' y la lista pegada' : 'la lista pegada'; }
    if (!ids.length){ impMsg.textContent = 'Elige antes el archivo de Questie o pega una lista de números.'; return; }
    var r = markDone(ids);
    impMsg.textContent = 'De ' + src + ': ' + ids.length + ' quests completadas, ' + r[1] + ' están en la guía. Marcadas ahora ' + r[0] + (r[1] - r[0] ? '; las otras ' + (r[1] - r[0]) + ' ya lo estaban.' : '.');
  });

  // ---------------------------------------------------------------- arranque
  restore();
  applyLevel();
  route();

  // Versión local: al imprimir se muestran todas las secciones y páginas
  if (LOCAL && !PRINT_ALL){
    window.addEventListener('beforeprint', function(){
      document.body.classList.add('printing');
      $$('.view, .page, .overview').forEach(function(el){ el.hidden = false; });
    });
    window.addEventListener('afterprint', function(){ document.body.classList.remove('printing'); route(); });
    var pb = $('#imprimir');
    if (pb) pb.addEventListener('click', function(){ window.print(); });
  }
})();
