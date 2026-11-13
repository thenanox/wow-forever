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
  var VIEWS = ['inicio', 'zonas', 'mazmorras', 'cadenas', 'quests', 'chaman', 'profesiones', 'referencia', 'muro'];
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
  // Cada quest y cada mazmorra tiene una sola marca, guardada por su clave. Las casillas con data-dep
  // (imprescindibles, ruta, filas de varios pasos) no guardan nada: muestran el estado de las claves de las que dependen.
  var boxes = $$('input[type=checkbox][data-k]');
  var plain = boxes.filter(function(b){ return !b.dataset.dep; }), views = boxes.filter(function(b){ return !!b.dataset.dep; });
  var KS = {}, storeOK = true;
  try {
    for (var si = 0; si < window.localStorage.length; si++){
      var sk = window.localStorage.key(si);
      if (sk && sk.indexOf('chk-') === 0 && window.localStorage.getItem(sk) === '1') KS[sk.slice(4)] = 1;
    }
  } catch(e){}
  // dos variantes que se excluyen son la misma gesta: hecha una, la otra cuenta como hecha
  function exDone(id){ var q = D.q[id]; return !!(q && q.ex && q.ex.some(function(x){ return KS['q' + x]; })); }
  function isQ(id){ return !!KS['q' + id] || exDone(id); }
  function keyDone(k){ return !!KS[k] || (k.charAt(0) === 'q' && exDone(+k.slice(1))); }
  function tokDone(t){ return t.split('|').some(keyDone); }
  function setKey(k, on){
    if (on) KS[k] = 1; else delete KS[k];
    storeOK = store.set('chk-' + k, on ? '1' : '0') && storeOK;
    $$('input[data-k="' + k + '"]').forEach(function(o){ if (!o.dataset.dep) o.checked = on; });
  }
  // marcar una quest da por hechas las que el juego exige antes (si hay varias alternativas no se sabe cuál, y no se toca)
  function markBefore(id, seen){
    var q = D.q[id]; if (!q || seen[id]) return; seen[id] = 1;
    (q.pa || []).concat(q.po && q.po.length === 1 ? q.po : []).forEach(function(p){
      if (!D.q[p]) return;
      if (!KS['q' + p]) setKey('q' + p, true);
      markBefore(p, seen);
    });
  }
  function syncViews(){
    views.forEach(function(b){
      var ks = b.dataset.dep.split(','), n = ks.filter(tokDone).length;
      b.checked = n === ks.length; b.indeterminate = n > 0 && n < ks.length;
      var sp = b.nextElementSibling;
      if (sp){ if (b.indeterminate) sp.dataset.part = n + ' de ' + ks.length; else sp.removeAttribute('data-part'); }
    });
  }
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
    var dg = countIn(document, 'input[data-dg]'), im = uniq('.blk.imp input[data-k]'), rt = countIn($('#ruta'));
    var ql = [UNI.filter(isQ).length, UNI.length];
    var box = $('#progreso');
    if (box) box.innerHTML = '<span>Mazmorras <b>' + dg[0] + '/' + dg[1] + '</b></span><span>Imprescindibles <b>' + im[0] + '/' + im[1] +
      '</b></span><span>Quests <b>' + ql[0] + '/' + ql[1] + '</b></span><span>Ruta <b>' + rt[0] + '/' + rt[1] + '</b></span>';
    updateChains(); markAvail(); renderCards(); renderSide(); renderNow(); updateRoute(); questStats(); updateTotems(); updateWall();
  }
  function restore(){
    // una marca antigua puesta a mano en una vista pasa a sus quests
    views.forEach(function(b){
      if (!KS[b.dataset.k]) return;
      b.dataset.dep.split(',').forEach(function(k){ setKey(k, true); });
      setKey(b.dataset.k, false);
    });
    plain.forEach(function(b){ b.checked = !!KS[b.dataset.k]; });
    syncViews(); updateBlocks(); refresh();
  }
  document.addEventListener('change', function(e){
    var b = e.target;
    if (!b.matches || !b.matches('input[type=checkbox][data-k]')) return;
    storeOK = true;
    if (b.checked) tink();
    var mark = function(k){ setKey(k, true); if (/^q\d+$/.test(k)) markBefore(+k.slice(1), {}); };
    if (!b.dataset.dep){ if (b.checked) mark(b.dataset.k); else setKey(b.dataset.k, false); }
    else b.dataset.dep.split(',').forEach(function(t){
      var alts = t.split('|');
      if (!b.checked) alts.forEach(function(k){ setKey(k, false); });
      else if (!tokDone(t)) mark(alts[0]);
    });
    savedToast(storeOK);
    syncViews(); updateBlocks(); refresh();
  });

  // ---------------------------------------------------------------- qué se puede coger ahora
  // Estado de una quest para este personaje: hecha, disponible, bloqueada por un requisito o por nivel.
  function questState(id){
    var q = D.q[id]; if (!q) return { s: 'x' };
    if (isQ(id)) return { s: 'done' };
    var miss = (q.pa || []).filter(function(p){ return D.q[p] && !isQ(p); });
    if (!miss.length && q.po && q.po.length && !q.po.some(function(p){ return !D.q[p] || isQ(p); })) miss = [q.po[0]];
    if (miss.length) return { s: 'pre', need: miss[0] };
    var v = L(); if (v && (q.m || 0) > v) return { s: 'lv', need: q.m };
    return { s: 'ok' };
  }
  // una fila puede ser una quest, varios pasos seguidos o variantes de las que basta una
  function rowState(box){
    var dep = box.dataset.dep;
    if (!dep) return /^q\d+$/.test(box.dataset.k) ? questState(+box.dataset.k.slice(1)) : null;
    var ids = dep.split(/[,|]/).filter(function(k){ return /^q\d+$/.test(k); }).map(function(k){ return +k.slice(1); });
    if (!ids.length) return null;
    var sts = ids.map(questState);
    if (dep.indexOf('|') >= 0) return sts.filter(function(s){ return s.s === 'done'; })[0] || sts.filter(function(s){ return s.s === 'ok'; })[0] || sts[0];
    return sts.filter(function(s){ return s.s !== 'done'; })[0] || { s: 'done' };
  }
  function markAvail(){
    $$('.allq li, .dq li').forEach(function(li){
      var box = $('input', li), st = box && rowState(box), qm = $('.qm', li); if (!st) return;
      li.classList.toggle('avail', st.s === 'ok'); li.classList.toggle('blocked', st.s === 'pre'); li.classList.toggle('low', st.s === 'lv');
      if (!qm) return;
      if (st.s === 'pre') qm.dataset.why = 'antes hay que hacer ' + D.q[st.need].n;
      else if (st.s === 'lv') qm.dataset.why = 'desde nivel ' + st.need;
      else qm.removeAttribute('data-why');
    });
    // estado de cada imprescindible: hecho, se puede hacer ya, falta nivel o falta algo antes
    var lvNow = L();
    $$('.blk.imp li').forEach(function(li){
      var box = $('input', li), out = $('.imp-s', li); if (!box || !out) return;
      var cls = 'st-man', txt = 'Esta se marca a mano: no depende de ninguna quest.';
      if (box.dataset.dep){
        var toks = box.dataset.dep.split(','), left = toks.filter(function(t){ return !tokDone(t); });
        if (!left.length){ cls = 'st-done'; txt = 'Hecha.'; }
        else if (!/^q\d+/.test(left[0])){ cls = 'st-ok'; txt = 'Pendiente: se marca sola cuando marques la mazmorra como hecha.'; }
        else {
          var id = +left[0].split('|')[0].slice(1), st = questState(id), q = D.q[id] || {}, prog = toks.length > 1 ? ' Llevas ' + (toks.length - left.length) + ' de ' + toks.length + '.' : '';
          if (st.s === 'lv'){ cls = 'st-lv'; txt = 'Todavía no: pide nivel ' + st.need + (lvNow ? ' y tienes ' + lvNow : '') + '.' + prog; }
          else if (st.s === 'pre'){ var nq = D.q[st.need]; cls = 'st-pre'; txt = 'Todavía no: antes hay que hacer ' + nq.n + (nq.g ? ', que da ' + nq.g[2] + (nq.gc && nq.gc[2] ? ' en ' + nq.gc[2] : '') : '') + '.' + prog; }
          else { cls = 'st-ok'; txt = 'Puedes hacerla ya' + (toks.length > 1 ? ': te toca ' + (q.n || '') : '') + (q.g ? ', con ' + q.g[2] + (q.gc ? ' (' + (q.gc[2] ? q.gc[2] + ' ' : '') + q.gc[0] + ', ' + q.gc[1] + ')' : '') : '') + '.' + prog; }
        }
      }
      out.textContent = txt;
      li.className = li.className.replace(/\bst-\w+/g, '').trim() + ' ' + cls;
    });
    $$('.dpage').forEach(function(pg){
      var blk = $('.dq', pg); if (!blk) return;
      var n = $$('li', blk).length, ok = $$('li.avail', blk).length, pre = $$('li.blocked', blk).length, lv = $$('li.low', blk).length, done = n - ok - pre - lv;
      if (!n) return;
      var el = $('.dq-ready', blk);
      if (!el){ el = document.createElement('p'); el.className = 'dq-ready'; var h = $('h3', blk); if (h) h.parentNode.insertBefore(el, h.nextSibling); else blk.insertBefore(el, blk.firstChild); }
      el.innerHTML = '<b>' + ok + '</b> ' + (ok === 1 ? 'puedes cogerla' : 'puedes cogerlas') + ' ya' + (pre ? ' · <b>' + pre + '</b> con algo que hacer antes' : '') + (lv ? ' · <b>' + lv + '</b> piden más nivel' : '') + (done ? ' · <b>' + done + '</b> hechas' : '');
    });
  }

  // los cuatro totems de la portada se encienden al entregar la quest que da cada uno
  function updateTotems(){
    var v = L();
    $$('a.totem').forEach(function(a){
      var got = !!KS['q' + a.dataset.q], lv = +a.dataset.tl, st = $('i', a);
      a.classList.toggle('got', got); a.classList.toggle('ready', !got && v >= lv);
      if (st) st.textContent = got ? 'conseguido' : v >= lv ? 'disponible' : 'a nivel ' + lv;
    });
  }

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
  function markSteps(root){
    var lis = $$('ol.chain > li', root), done = 0, next = 0;
    lis.forEach(function(li, i){
      // un paso sin marcar cuenta como superado si ya está hecho uno posterior que depende de él o al que solo llevaba
      var box = $('input', li), on = box.checked, skip = !on && (keyDone(box.dataset.k) || (!!li.dataset.imp && li.dataset.imp.split(',').some(keyDone)));
      li.classList.toggle('done', on); li.classList.toggle('skip', skip); li.classList.remove('next');
      if (on || skip) done++; else if (!next){ next = i + 1; li.classList.add('next'); }
    });
    return { done: done, n: lis.length, next: next };
  }
  function updateChains(){
    (D.chains || []).forEach(function(c){
      var pg = document.getElementById('cad-' + c.k); if (!pg) return;
      var s = CH[c.k] = markSteps(pg), cp = $('.cprog', pg);
      if (cp) cp.textContent = s.done === s.n ? 'completada' : s.done ? s.done + ' de ' + s.n + ' · sigue el paso ' + s.next : 'sin empezar';
    });
    $$('a.clink[data-chain]').forEach(function(a){
      var s = CH[a.dataset.chain]; if (!s) return;
      a.classList.toggle('done', s.done === s.n);
      $('.cl-p', a).textContent = s.done === s.n ? 'completada' : s.done ? s.done + '/' + s.n + ' · sigue el paso ' + s.next : s.n + ' pasos';
    });
    if (cur.page && cur.page.classList.contains('cpage')) chainEmblem(cur.page);
    var qd = $('#qdetail');
    if (qd && !qd.hidden){ var s = markSteps(qd), pr = $('.cprog', qd); if (pr) pr.textContent = s.n > 1 ? s.done + ' de ' + s.n : ''; }
  }

  function manualBehind(){
    var v = L(), out = [];
    $$('#ruta .steps > li').forEach(function(li){
      if (!(v > +(li.dataset.lv || '').split('-')[1])) return;
      $$('li.man input', li).forEach(function(b){ if (!b.checked) out.push(b); });
    });
    return out;
  }
  document.addEventListener('click', function(e){
    if (!e.target.closest || !e.target.closest('#man-up')) return;
    manualBehind().forEach(function(b){ setKey(b.dataset.k, true); });
    savedToast(storeOK); syncViews(); updateBlocks(); refresh();
  });

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
    var mb = $('#man-up'), todo = manualBehind();
    if (mb){ mb.hidden = !todo.length; mb.textContent = 'Dar por hechos los ' + todo.length + ' puntos «a mano» de los tramos que ya pasé'; }
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
    var rail = $('.rail'); if (rail) rail.style.setProperty('--lv', v || 1);
    updateTotems(); updateWall(); markAvail();
    var tnow = $('#tl-now');
    if (tnow){
      var curT = null, nextT = null, tname = function(li){ return $('b', li).textContent; };
      $$('ol.tl > li').forEach(function(li){
        var p = li.dataset.lv.split('-'), a = +p[0], b = +p[1];
        li.classList.toggle('past', v > b);
        if (v >= a && v <= b) curT = li; else if (v < a && !nextT) nextT = li;
      });
      tnow.textContent = !v ? '' : v < 10 ? 'Los talentos empiezan a nivel 10. El primero es ' + tname(nextT) + '.'
        : 'Con nivel ' + v + ' tienes ' + (v - 9) + ' puntos.' + (curT ? ' Ahora toca ' + tname(curT) + '.' : '') +
          (nextT ? ' Después, a nivel ' + nextT.dataset.lv.split('-')[0] + ', ' + tname(nextT) + '.' : '');
    }
    renderCards(); renderSide(); renderNow(); updateRoute();
    if (cur.view === 'quests' && !cur.page && qf.level && qf.level.checked) renderQuests();
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
          '<span class="c-f">' + (im[1] ? 'Imprescindibles ' + im[0] + '/' + im[1] + ' · ' : '') + 'Quests ' + q[0] + '/' + q[1] + (function(){ var n = $$('.allq li.avail', pg).length; return n ? ' · ' + n + ' ahora' : ''; })() + '</span></a>');
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
          '<span class="c-h"><b>' + esc(c.t) + '</b><span class="lv">' + esc(c.lv) + '</span></span>' + (c.sub ? '<span class="c-s">' + esc(c.sub) + '</span>' : '') + bar(s.done, s.n) +
          '<span class="c-f">' + (done ? 'Completada' : s.done ? 'Vas por el paso ' + s.next + ' de ' + s.n : s.n + ' pasos') + '</span></a>');
      });
      host.innerHTML = cg.map(function(g){ return '<h4 class="cg">' + esc(g) + '</h4><div class="cards">' + cby[g].join('') + '</div>'; }).join('');
    }
    host = $('#zchains');
    if (host){
      var zg = [], zby = {};
      leafChains().forEach(function(c){
        if (!zby[c.place]){ zby[c.place] = []; zg.push(c.place); }
        var d = c.ids.filter(function(i){ return KS['q' + i]; }).length, q = D.q[c.id];
        zby[c.place].push('<li><a class="clink' + (d === c.ids.length ? ' done' : '') + (inRange(v, q.m || q.l, q.l + 3) ? ' at-level' : '') + '" href="#q-' + c.id + '"><b>' + esc(q.n) +
          '</b><span class="lv">' + (q.l || '') + '</span><span class="cl-h">' + c.ids.length + ' pasos</span><span class="cl-p">' + (d === c.ids.length ? 'completada' : d + '/' + c.ids.length) + '</span></a></li>');
      });
      host.innerHTML = zg.map(function(g){ return '<h4 class="cg">' + esc(g) + '</h4><ul class="clinks">' + zby[g].join('') + '</ul>'; }).join('');
    }
    host = $('#dcards');
    if (host){
      host.innerHTML = '<div class="cards">' + DG.map(function(g){
        var pg = document.getElementById('dg-' + g.g), q = countIn(pg, '.dq input');
        var wd = g.wings.filter(isDone).length, done = wd === g.wings.length;
        return '<a class="card' + (inRange(v, g.a, g.b) && !done ? ' at-level' : '') + (done ? ' done' : '') + '" href="#dg-' + g.g + '">' +
          '<span class="c-h"><b>' + esc(g.n) + '</b><span class="lv">' + g.a + '-' + g.b + '</span></span>' +
          '<span class="c-s">' + esc(g.loc) + (g.isNew ? ' · nueva en Forever' : '') + '</span>' + bar(q[0], q[1]) +
          '<span class="c-f">' + (g.wings.length > 1 ? 'Alas ' + wd + '/' + g.wings.length + ' · ' : '') + 'Quests ' + q[0] + '/' + q[1] + (function(){ var n = $$('.dq li.avail', pg).length; return n ? ' · ' + n + ' ahora' : ''; })() + '</span></a>';
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
    } else if (cur.view === 'chaman' || cur.view === 'profesiones' || cur.view === 'referencia'){
      h = '<a class="s-all' + (pid ? '' : ' on') + '" href="#' + cur.view + '">Resumen</a><h4>Apartados</h4>';
      $$('#v-' + cur.view + ' > .spage').forEach(function(s){
        h += '<a href="#' + s.id + '" class="' + (s.id === pid ? 'on' : '') + '"><span>' + esc(s.dataset.name) + '</span></a>';
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
      (zn.length ? '<small>Pronto:</small><ul class="chips">' + zn.map(function(z){ return chip(z.id, z.n, z.lv, 'soon'); }).join('') + '</ul>' : '') +
      (function(){ var n = 0; zs.forEach(function(z){ n += $$('#' + z.id + ' .allq li.avail').length; }); return n ? '<small><a href="#quests" data-qf="a">' + n + ' quests que puedes coger ahora en estas zonas</a></small>' : ''; })() + '</div>';
    h += '<div class="tile"><h4>Mazmorras en rango</h4><ul class="chips">' +
      (ds.map(function(d){ return chip('dg-' + d.g, d.n, d.a + '-' + d.b, isDone(d.k) ? 'done' : ''); }).join('') || '<li><small>Ninguna todavía: la primera es a nivel 13.</small></li>') + '</ul>' +
      (dn.length ? '<small>Pronto:</small><ul class="chips">' + dn.map(function(d){ return chip('dg-' + d.g, d.n, d.a + '-' + d.b, 'soon'); }).join('') + '</ul>' : '') + '</div>';
    var cs = (D.chains || []).filter(function(c){ var s = chainState(c); return s.done !== s.n && (inRange(v, c.a, c.b) || s.done > 0); });
    var GORD = { 'Tu chamán': 0, 'Tu personaje': 1, 'Mazmorras': 2, 'Zonas': 3 };
    cs.sort(function(a, b){ return (chainState(b).done > 0) - (chainState(a).done > 0) || GORD[a.g] - GORD[b.g] || a.a - b.a; });
    var extra = cs.length - 6;
    h += '<div class="tile"><h4>Cadenas a tu nivel</h4><ul class="chips">' +
      (cs.slice(0, 6).map(function(c){ var s = chainState(c); return chip('cad-' + c.k, c.t, s.done + '/' + s.n, ''); }).join('') || '<li><small>Ninguna pendiente.</small></li>') + '</ul>' +
      '<small><a href="#cadenas">' + (extra > 0 ? 'Y ' + extra + ' más: ver todas las cadenas' : 'Ver todas las cadenas paso a paso') + '</a></small></div>';
    h += '<div class="tile"><h4>Lo que tienes y lo que viene</h4><ul class="ms">' +
      past.map(function(m){ return '<li class="past"><span class="lv">' + m[0] + '</span><span>' + esc(m[1]) + '</span></li>'; }).join('') +
      next.map(function(m){ return '<li><span class="lv">' + m[0] + '</span><span>' + esc(m[1]) + '</span></li>'; }).join('') + '</ul>' +
      '<h4 class="t2">Profesiones a este nivel</h4><p>' + esc(pr[1]) + '</p><p>' + esc(pr[2]) + '</p><small><a href="#profesiones">Ver el plan de profesiones</a></small></div>';
    host.innerHTML = h;
    var pend = $('#pend');
    if (pend){
      var seen = {}, items = [];
      zs.forEach(function(z){
        if (zoneDone(z.id)) return;
        $$('#' + z.id + ' .blk.imp input[data-k]').forEach(function(b){
          if (b.checked || seen[b.dataset.k]) return;
          var bl = b.closest('li'); if (bl && (bl.classList.contains('st-lv') || bl.classList.contains('st-pre'))) return;   // aún no se puede hacer
          seen[b.dataset.k] = 1;
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
    if (page.classList.contains('spage')) return $$('.spage', page.parentNode).map(function(s){ return { id: s.id, n: s.dataset.name }; });
    return DG.map(function(g){ return { id: 'dg-' + g.g, n: g.n }; });
  }
  function addPrevNext(page){
    if ($('.pn', page) || page.classList.contains('qpage')) return;
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
    var mq = /^q-(\d+)$/.exec(id);
    if (mq && D.q[mq[1]]){ view = 'quests'; page = $('#qdetail'); renderQuest(+mq[1]); }
    else if (VIEWS.indexOf(id) >= 0) view = id;
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
    var tabOn = $('.tabs a.on'), tabs = $('.tabs');
    if (tabOn && tabs && tabs.scrollWidth > tabs.clientWidth) tabs.scrollLeft = Math.max(0, tabOn.offsetLeft - 24);
    var vEl = $('#v-' + view), pages = $$('.page', vEl), ov = $('.overview', vEl);
    pages.forEach(function(p){ p.hidden = p !== page; });
    if (ov) ov.hidden = !!page;
    if (page) addPrevNext(page);
    if (view === 'quests' && !page) renderQuests();
    if (view === 'muro') openWall();
    if (page && page.classList.contains('cpage')) chainEmblem(page);
    if (page && page.id === 'qdetail') updateChains();
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
    if (a.dataset.qf && qf.state){ qf.state.value = a.dataset.qf; qf.zone.value = ''; qf.kind.value = ''; qf.text.value = ''; qf.level.checked = false; qshown = 150; }
    e.preventDefault(); navigate(id);
    var cfg = $('details.cfg'); if (cfg) cfg.open = false;
  });

  // filtros de la lista de quests
  document.addEventListener('click', function(e){
    var b = e.target.closest ? e.target.closest('.filters button') : null; if (!b) return;
    var box = b.closest('.allq');
    $$('.filters button', box).forEach(function(o){ o.classList.toggle('on', o === b); });
    box.classList.remove('f-pend', 'f-new', 'f-star', 'f-avail');
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
    if (q.aka) h += '<dt>Otro número</dt><dd>' + q.aka.join(', ') + '</dd>';
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
    if (a.classList.contains('rn')) return h + '<div class="p-f"><span>' + (KS['q' + id] ? 'Tallada' : 'Sin tallar') + '</span>' +
      (touch ? '<a href="' + a.getAttribute('href') + '">Ver su ficha</a>' : '<span>Clic para ver su ficha</span>') + '</div>';
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
  function target(e){ return e.target.closest ? e.target.closest('a.x[data-t], a.rn[data-t], [data-tip]') : null; }
  if (!touch){
    document.addEventListener('mouseover', function(e){ var a = target(e); if (a && a !== curA) show(a); else if (e.target.closest && e.target.closest('#pop')) clearTimeout(hideT); });
    document.addEventListener('mouseout', function(e){ if (target(e) || (e.target.closest && e.target.closest('#pop'))){ clearTimeout(hideT); hideT = setTimeout(hide, 140); } });
    document.addEventListener('focusin', function(e){ var a = target(e); if (a) show(a); });
    document.addEventListener('focusout', function(){ hide(); });
  } else {
    document.addEventListener('click', function(e){
      var a = target(e);
      if (a && a !== curA && !a.classList.contains('gr') && !a.classList.contains('br')){ if (show(a)) e.preventDefault(); }
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
    $$('.spage').forEach(function(s){ add('Sección', s.dataset.name, '', s.id); });
    QALL.forEach(function(id){ add('Quest', D.q[id].n, qPlace(D.q[id]) + ' · ficha', 'q-' + id); });
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
    return btoa(unescape(encodeURIComponent(JSON.stringify({ v: 3, nivel: lvl.value, on: Object.keys(KS) }))));
  }
  var bc = $('#sync-copy'), bl = $('#sync-load');
  if (bc) bc.addEventListener('click', function(){
    code.value = exportCode(); code.select();
    var ok = function(){ msg.textContent = 'Código copiado.'; }, manual = function(){ msg.textContent = 'Código listo: cópialo del cuadro.'; };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(code.value).then(ok, manual); else manual();
  });
  if (bl) bl.addEventListener('click', function(){
    try {
      var d = JSON.parse(decodeURIComponent(escape(atob(code.value.trim())))), on = {};
      (d.on || []).forEach(function(k){ on[k] = 1; });
      Object.keys(KS).forEach(function(k){ if (!on[k]) setKey(k, false); });
      Object.keys(on).forEach(function(k){ setKey(k, true); });
      if (d.nivel){ lvl.value = d.nivel; store.set('nivel', d.nivel); }
      restore(); applyLevel();
      msg.textContent = 'Progreso cargado: ' + (d.on || []).length + ' marcas.';
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
    var fresh = 0, known = 0, unk = [];
    ids.forEach(function(id){
      if (D.alias && D.alias[id]) id = D.alias[id];          // la misma quest con otro número
      if (!D.q[id]){ unk.push(id); return; }
      known++; if (!KS['q' + id]){ setKey('q' + id, true); fresh++; }
    });
    var ub = $('#imp-unk-box'), ut = $('#imp-unk');
    if (ub){ ub.hidden = !unk.length; ut.value = unk.join(', '); $('#imp-unk-n').textContent = unk.length; }
    restore(); applyLevel();
    if (cur.view === 'quests' && !cur.page) renderQuests();
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

  // ---------------------------------------------------------------- todas las quests: una ficha por quest y vistas de ella
  var QALL = Object.keys(D.q).filter(function(id){ return D.q[id].u; }).map(Number);
  QALL.sort(function(a, b){ var x = D.q[a], y = D.q[b]; return (x.l || 0) - (y.l || 0) || x.n.localeCompare(y.n) || a - b; });
  // una por gesta: de cada grupo de variantes excluyentes se cuenta solo la primera
  var UNI = QALL.filter(function(id){ var q = D.q[id]; return !(q.ex && q.ex.some(function(x){ return x < id && D.q[x] && D.q[x].u; })); });
  var ZN = {}, DN = {};
  D.zones.forEach(function(z){ ZN[z.id.slice(2)] = z.n; });
  DG.forEach(function(g){ DN[g.g] = g.n; });
  function qPlace(q){ return q.dg ? DN[q.dg] : q.zp ? ZN[q.zp] : q.z || ''; }
  function qHome(q){ return q.dg ? 'dg-' + q.dg : q.zp ? 'z-' + q.zp : ''; }
  function qTags(q){
    var t = '';
    if (q.nw) t += '<span class="tag new">nueva</span>';
    if (q.dg) t += '<span class="tag ty">mazmorra</span>'; else if (q.t && TY[q.t]) t += '<span class="tag ty">' + TY[q.t] + '</span>';
    if (q.cl) t += '<span class="tag ty">clase</span>';
    if (q.im) t += '<span class="tag st">imprescindible</span>';
    if (q.bc) t += '<span class="tag st">recado opcional</span>';
    return t;
  }
  function qLink(id){ return '<a class="x x-quest" data-t="quest" data-id="' + id + '" href="' + url('quest', id) + '" target="_blank" rel="noopener">' + esc(D.q[id].n) + '</a>'; }
  function qBox(id, label){ return '<input type="checkbox" data-k="q' + id + '"' + (KS['q' + id] ? ' checked' : '') + (label ? ' aria-label="' + label + '"' : '') + '>'; }
  function spot(ref, c){ return esc(ref[2]) + (c ? ' <span class="co">' + esc(c[2] || '') + ' ' + c[0] + ', ' + c[1] + '</span>' : ''); }
  function qRow(id){
    var q = D.q[id], meta = [], home = qHome(q);
    if (qPlace(q)) meta.push(home ? '<a href="#' + home + '">' + esc(qPlace(q)) + '</a>' : esc(qPlace(q)));
    if (q.g) meta.push(esc(q.g[2]) + (q.gc ? ' · ' + q.gc[0] + ', ' + q.gc[1] : ''));
    if (q.ch) meta.push('<a class="qc" href="#cad-' + q.ch[0] + '">cadena, paso ' + q.ch[1] + '</a>');
    else if (q.pa || q.po || q.nx) meta.push('<a class="qc" href="#q-' + id + '">cadena</a>');
    else meta.push('<a class="qc" href="#q-' + id + '">ficha</a>');
    var qs = questState(id);
    if (qs.s === 'pre') meta.push('<span class="why">antes: <a class="qc" href="#q-' + qs.need + '">' + esc(D.q[qs.need].n) + '</a></span>');
    else if (qs.s === 'lv') meta.push('<span class="why">desde nivel ' + qs.need + '</span>');
    return '<li><label>' + qBox(id) + '<span><span class="lv">' + (q.l || '?') + '</span> ' + qLink(id) + qTags(q) + (!KS['q' + id] && exDone(id) ? '<span class="tag okk">hecha en otra variante</span>' : '') + '<span class="qm">' + meta.join(' · ') + '</span></span></label></li>';
  }
  var qf = { text: $('#qf-text'), zone: $('#qf-zone'), state: $('#qf-state'), kind: $('#qf-kind'), level: $('#qf-level') }, qshown = 150;
  if (qf.zone){
    qf.zone.innerHTML = '<option value="">Todas las zonas y mazmorras</option><optgroup label="Zonas">' +
      D.zones.map(function(z){ return '<option value="' + z.id + '">' + esc(z.n) + '</option>'; }).join('') + '</optgroup><optgroup label="Mazmorras">' +
      DG.map(function(g){ return '<option value="dg-' + g.g + '">' + esc(g.n) + '</option>'; }).join('') + '</optgroup>';
  }
  function qFilter(){
    var t = qf.text.value.trim().toLowerCase(), z = qf.zone.value, st = qf.state.value, k = qf.kind.value, lv = qf.level.checked ? L() : 0;
    return QALL.filter(function(id){
      var q = D.q[id];
      if (t && q.n.toLowerCase().indexOf(t) < 0 && !(q.g && q.g[2].toLowerCase().indexOf(t) >= 0)) return false;
      if (z && qHome(q) !== z) return false;
      if (st === 'a' ? questState(id).s !== 'ok' : st && (st === 'd') !== isQ(id)) return false;
      if (k === 'im' && !q.im || k === 'dg' && !q.dg || k === 'cl' && !q.cl || k === 'nw' && !q.nw) return false;
      if (k === 'ch' && !(q.ch || q.pa || q.po || q.nx) || k === 'el' && !(q.t === 'Elite' || q.gr)) return false;
      if (lv && !((q.m || q.l || 0) <= lv && (q.l || 0) >= lv - 4)) return false;
      return true;
    });
  }
  function questStats(ids){
    var el = $('#qstats'); if (!el || !qf.text) return;
    ids = ids || qFilter();
    var d = ids.filter(isQ).length;
    el.textContent = ids.length + ' quests · ' + d + ' hechas · ' + (ids.length - d) + ' pendientes';
  }
  function renderQuests(){
    var list = $('#qlist'); if (!list) return;
    var ids = qFilter(), more = $('#qmore');
    // lo que puedes coger ahora, empezando por lo más cercano a tu nivel
    if (qf.state.value === 'a') ids.sort(function(a, b){ return (D.q[b].l || 0) - (D.q[a].l || 0) || D.q[a].n.localeCompare(D.q[b].n); });
    questStats(ids);
    list.innerHTML = ids.slice(0, qshown).map(qRow).join('') || '<li class="src">Ninguna quest con esos filtros.</li>';
    more.hidden = ids.length <= qshown;
    more.textContent = 'Ver ' + Math.min(150, ids.length - qshown) + ' más';
  }
  ['text', 'zone', 'state', 'kind', 'level'].forEach(function(k){
    if (qf[k]) qf[k].addEventListener(k === 'text' ? 'input' : 'change', function(){ qshown = 150; renderQuests(); });
  });
  if ($('#qmore')) $('#qmore').addEventListener('click', function(){ qshown += 150; renderQuests(); });

  // lo que hay que hacer antes de una quest, en orden: primero lo más lejano
  function chainOf(id){
    var seen = {}, out = [];
    (function walk(i){
      var q = D.q[i]; if (!q) return;
      (q.pa || []).concat(q.po || []).forEach(function(p){ if (!seen[p] && D.q[p]){ seen[p] = 1; walk(p); out.push(p); } });
    })(id);
    return out;
  }
  var LEAF = null;
  function leafChains(){
    if (LEAF) return LEAF;
    LEAF = [];
    QALL.forEach(function(id){
      var q = D.q[id];
      if (q.ch || (q.nx && q.nx.length) || !(q.pa || q.po)) return;
      var ids = chainOf(id).concat([id]);
      if (ids.length >= 3) LEAF.push({ id: id, ids: ids, place: qPlace(q) || 'Otras' });
    });
    var order = {}; D.zones.forEach(function(z, i){ order[z.n] = i; }); DG.forEach(function(g, i){ order[g.n] = 500 + i; });
    LEAF.sort(function(a, b){ return (order[a.place] == null ? 999 : order[a.place]) - (order[b.place] == null ? 999 : order[b.place]) || (D.q[a.id].l || 0) - (D.q[b.id].l || 0); });
    return LEAF;
  }
  function stepLi(id, n, isCur, imp){
    var q = D.q[id], w = [];
    if (q.g) w.push('La da ' + spot(q.g, q.gc) + '.');
    if (q.e) w.push('Se entrega a ' + spot(q.e, q.ec) + '.');
    var alt = q.po && q.po.length > 1 ? '<p class="cs-need">Para que te la den basta con haber hecho una de estas: ' + q.po.map(qLink).join(', ') + '.</p>' : '';
    return '<li' + (isCur ? ' class="cur"' : '') + (imp && imp.length ? ' data-imp="' + imp.map(function(x){ return 'q' + x; }).join(',') + '"' : '') + '><label class="cs-n">' + qBox(id, 'Paso ' + n + ' hecho') + '<span data-n="' + n + '"></span></label>' +
      '<div class="cs-b"><div class="cs-t">' + qLink(id) + '<span class="lv">nivel ' + (q.l || '?') + (q.m && q.m < q.l ? ', desde ' + q.m : '') + '</span>' + qTags(q) +
      (isCur ? '' : '<a class="qc" href="#q-' + id + '">ficha</a>') + '</div>' +
      (w.length ? '<p class="cs-w">' + w.join(' ') + '</p>' : '') + (q.o ? '<p class="cs-o">' + esc(q.o) + '</p>' : '') + alt + '</div></li>';
  }
  function renderQuest(id){
    var pg = $('#qdetail'), q = D.q[id], anc = chainOf(id), home = qHome(q), rows = [], rw = [];
    pg.dataset.name = q.n;
    if (q.o) rows.push('<dt>Objetivo</dt><dd>' + esc(q.o) + '</dd>');
    if (q.g) rows.push('<dt>La da</dt><dd>' + spot(q.g, q.gc) + '</dd>');
    if (q.e) rows.push('<dt>Se entrega a</dt><dd>' + spot(q.e, q.ec) + '</dd>');
    if (q.x) rw.push(q.x + ' XP'); if (q.c) rw.push(money(q.c));
    if (rw.length) rows.push('<dt>Premio</dt><dd>' + rw.join(' · ') + '</dd>');
    if (q.rc) rows.push('<dt>A elegir</dt><dd>' + items(q.rc) + '</dd>');
    if (q.r) rows.push('<dt>Además</dt><dd>' + items(q.r) + '</dd>');
    if (q.p) rows.push('<dt>Reputación</dt><dd>' + q.p.map(function(x){ return '+' + x[1] + ' ' + esc(x[0]); }).join(', ') + '</dd>');
    if (q.aka) rows.push('<dt>Otro número</dt><dd>En Forever esta quest lleva el número ' + id + '. La base de datos la trae duplicada también como ' + q.aka.join(', ') + ': ese otro número solo sirve para reconocerla al importar.</dd>');
    var where = [];
    if (home) where.push('<a href="#' + home + '">' + esc(qPlace(q)) + '</a>');
    if (q.ch) where.push('<a href="#cad-' + q.ch[0] + '">su cadena, paso ' + q.ch[1] + '</a>');
    if (q.im) where.push('imprescindibles' + (home ? ' de <a href="#' + home + '">' + esc(qPlace(q)) + '</a>' : ''));
    var after = (q.nx || []).filter(function(i){ return D.q[i]; });
    pg.innerHTML = '<header class="ph"><div class="crumb"><a href="#quests">Quests</a><span>›</span>' + esc(q.n) + '</div><h2>' + esc(q.n) + '</h2>' +
      '<div class="ph-meta"><span class="lv">nivel ' + (q.l || '?') + (q.m && q.m < q.l ? ', desde ' + q.m : '') + '</span>' + (qPlace(q) ? '<span>' + esc(qPlace(q)) + '</span>' : '') + qTags(q) +
      (function(){ var s = questState(id); return s.s === 'ok' ? '<span class="tag okk">puedes cogerla ya</span>' : s.s === 'pre' ? '<span class="why">antes hay que hacer <a href="#q-' + s.need + '">' + esc(D.q[s.need].n) + '</a></span>' : s.s === 'lv' ? '<span class="why">desde nivel ' + s.need + '</span>' : ''; })() +
      '<span class="cprog"></span></div><div class="dones"><label class="done">' + qBox(id) + ' Hecha</label> ' + qLink(id).replace('>' + esc(q.n) + '<', '>Abrir en ' + (mode === 'wdb' ? 'Warcraft DB' : 'Wowhead') + '<') + '</div></header>' +
      '<section class="blk"><h3>Ficha</h3><dl class="qd">' + rows.join('') + '</dl>' + (where.length ? '<p class="src">Aparece en: ' + where.join(', ') + '.</p>' : '') + '</section>' +
      '<section class="blk csteps"><h3>' + (anc.length ? 'Cadena hasta aquí' : 'Requisitos') + '</h3>' +
      (anc.length ? '<p class="src">Lo que hay que haber hecho antes, en orden, según los requisitos de Questie. La última es esta quest.</p><ol class="chain">' +
        (function(){
          var list = anc.concat([id]), A = {};
          list.forEach(function(t){ A[t] = chainOf(t); });
          return list.map(function(i, n){
            // lo da por superado cualquier paso posterior que lo exija, o un requisito alternativo del mismo paso
            var imp = list.slice(n + 1).filter(function(t){ return A[t].indexOf(i) >= 0; });
            list.forEach(function(t){ var po = D.q[t].po || []; if (po.length > 1 && po.indexOf(i) >= 0) po.forEach(function(o){ if (o !== i && imp.indexOf(o) < 0) imp.push(o); }); });
            return stepLi(i, n + 1, i === id, imp);
          }).join('');
        })() + '</ol>'
        : '<p>No tiene requisitos: se puede coger directamente' + (q.m ? ' desde nivel ' + q.m : '') + '.</p><ol class="chain" hidden>' + stepLi(id, 1, true) + '</ol>') + '</section>' +
      (after.length ? '<section class="blk"><h3>Al terminarla se abre</h3><ul class="clinks">' + after.map(function(i){
        var n = D.q[i]; return '<li><a class="clink" href="#q-' + i + '"><b>' + esc(n.n) + '</b><span class="lv">' + (n.l || '') + '</span><span class="cl-h">' + esc(qPlace(n)) + '</span><span class="cl-p">' + (KS['q' + i] ? 'hecha' : '') + '</span></a></li>';
      }).join('') + '</ul></section>' : '');
  }

  // ---------------------------------------------------------------- el muro de gestas
  // Cada quest es una runa que se puede leer: el trazo de arriba dice el nivel, el del centro qué hay que hacer,
  // el del pie si da objeto, y las marcas del asta si es de mazmorra, de grupo o de clase. Una cadena es una runa ligada.
  var RUNE_TOP = ['', 'M8 8L14 3', 'M8 8L14 3M8 8L2 3', 'M8 4L14 9', 'M8 4L14 9M8 4L2 9', 'M8 3L14 6L8 9'];
  var RUNE_MID = { 1: 'M3 9L13 15M13 9L3 15', 2: 'M8 10H13V15H8', 3: 'M8 12H14', 4: 'M2 12H14', 5: 'M8 9L12 12L8 15L4 12Z' };
  function runeSVG(q){
    var d = 'M8 2V22' + RUNE_TOP[Math.min(5, Math.floor((q.l || 1) / 10))] + RUNE_MID[q.ac || 5];
    if (q.rc || q.r) d += 'M8 17L14 21';
    if (q.dg) d += 'M3 22H13';
    if (q.t === 'Elite' || q.gr) d += 'M4 2H12';
    if (q.cl) d += 'M8 0L10.5 2.5L8 5L5.5 2.5Z';
    return '<svg viewBox="0 0 16 24" aria-hidden="true"><path d="' + d + '"/></svg>';
  }
  function bindRune(c){
    var ids = c.ids || [], n = ids.length, H = 10 + n * 9, all = n > 0;
    var segs = ids.map(function(id, k){
      var im = c.im && c.im[id], on = isQ(id) || !!(im && im.some(isQ)); if (!on) all = false;
      return '<path' + (on ? ' class="on"' : '') + ' transform="translate(0 ' + (H - 21.5 - k * 9) + ')" d="' + RUNE_MID[(D.q[id] || {}).ac || 5] + '"/>';
    });
    return '<svg viewBox="0 0 16 ' + H + '"' + (all ? ' class="full"' : '') + ' aria-hidden="true"><path class="st" d="M8 2V' + (H - 2) + '"/>' + segs.join('') + '</svg>';
  }
  function frieze(){
    return (D.chains || []).map(function(c){
      var s = chainState(c);
      return '<a class="br" href="#cad-' + c.k + '" data-tip="' + esc(c.t + (c.sub ? ' · ' + c.sub : '') + ' · ' + (s.done === s.n ? 'saga completa' : s.done + ' de ' + s.n + ' pasos')) + '" aria-label="' + esc(c.t) + '">' + bindRune(c) + '</a>';
    }).join('');
  }
  function chainEmblem(pg){
    var c = null; (D.chains || []).forEach(function(x){ if ('cad-' + x.k === pg.id) c = x; });
    var ph = $('.ph', pg); if (!c || !ph) return;
    var el = $('.brune', ph);
    if (!el){ el = document.createElement('div'); el.className = 'brune'; el.setAttribute('aria-hidden', 'true'); ph.appendChild(el); }
    el.innerHTML = bindRune(c);
  }
  function inscription(){
    var name = (store.get('nombre') || '').trim(), v = L();
    var nq = UNI.filter(isQ).length;
    var nc = (D.chains || []).filter(function(c){ var s = CH[c.k]; return s && s.n && s.done === s.n; }).length;
    var nd = DG.filter(function(g){ return g.wings.filter(isDone).length === g.wings.length; }).length;
    var nt = $$('a.totem.got').length;
    if (!nq && !nd) return 'Este muro está por tallar. Aquí constarán las gestas de <b>' + esc(name || 'un enano todavía sin nombre') + '</b>, chamán de Ironforge.';
    return 'Aquí consta que <b>' + esc(name || 'un enano sin nombre') + '</b>, chamán de Ironforge, ha tallado <b>' + nq + '</b> de ' + UNI.length + ' gestas, ha cerrado <b>' + nc + '</b> ' + (nc === 1 ? 'saga' : 'sagas') +
      ', ha limpiado <b>' + nd + '</b> ' + (nd === 1 ? 'mazmorra' : 'mazmorras') + ' y ha alzado <b>' + nt + '</b> de sus cuatro totems.' + (v ? ' Nivel ' + v + '.' : '');
  }
  var wallBuilt = false, wallGroups = [];
  function buildWall(){
    var by = {}, order = [];
    D.zones.forEach(function(z){ by[z.id] = { id: z.id, n: z.n, lv: z.lv, ids: [] }; order.push(z.id); });
    DG.forEach(function(g){ by['dg-' + g.g] = { id: 'dg-' + g.g, n: g.n, lv: g.a + '-' + g.b, ids: [] }; order.push('dg-' + g.g); });
    by[''] = { id: '', n: 'Sin zona fija', lv: '', ids: [] }; order.push('');
    QALL.forEach(function(id){ (by[qHome(D.q[id])] || by['']).ids.push(id); });
    wallGroups = order.map(function(k){ return by[k]; }).filter(function(g){ return g.ids.length; });
    $('#muro').innerHTML = wallGroups.map(function(g, gi){
      return '<section class="mz" data-g="' + gi + '"><h4>' + (g.id ? '<a href="#' + g.id + '">' + esc(g.n) + '</a>' : esc(g.n)) + (g.lv ? '<span class="lv">' + esc(g.lv) + '</span>' : '') + '<span class="mz-n"></span></h4><div class="runes">' +
        g.ids.map(function(id){ return '<a class="rn" tabindex="-1" href="#q-' + id + '" data-t="quest" data-id="' + id + '" aria-label="' + esc(D.q[id].n) + '">' + runeSVG(D.q[id]) + '</a>'; }).join('') + '</div></section>';
    }).join('');
    var S = function(q, t){ return '<span class="ley"><i class="rn on">' + runeSVG(q) + '</i>' + t + '</span>'; };
    $('#leyenda').innerHTML =
      '<p><b>El trazo de arriba es el nivel.</b></p><div class="leys">' + ['1 a 9', '10 a 19', '20 a 29', '30 a 39', '40 a 49', '50 a 60'].map(function(t, i){ return S({ l: i * 10 + 1, ac: 3 }, t); }).join('') + '</div>' +
      '<p><b>El trazo del centro es lo que te piden.</b></p><div class="leys">' + [[1, 'matar'], [2, 'recoger o conseguir'], [3, 'llevar algo o hablar'], [4, 'escoltar'], [5, 'otra cosa']].map(function(x){ return S({ l: 1, ac: x[0] }, x[1]); }).join('') + '</div>' +
      '<p><b>El pie y las marcas.</b></p><div class="leys">' + S({ l: 1, ac: 3, r: 1 }, 'da un objeto') + S({ l: 1, ac: 3, dg: 'x' }, 'se hace en una mazmorra') + S({ l: 1, ac: 3, t: 'Elite' }, 'élite o de grupo') + S({ l: 1, ac: 3, cl: 1 }, 'de tu clase') + '</div>' +
      '<p class="src">Ejemplo: ' + S({ l: 22, ac: 1, r: 1, dg: 'x' }, 'una quest de nivel 20 a 29 de matar, con premio, dentro de una mazmorra.') + '</p>';
    wallBuilt = true;
  }
  function updateWall(){
    var a = $('#insc-ini'), f = $('#friso-ini'), text = inscription();
    if (a) a.innerHTML = text;
    if (f) f.innerHTML = frieze();
    if (!wallBuilt || cur.view !== 'muro') return;
    $('#insc').innerHTML = text; $('#friso').innerHTML = frieze();
    $$('#muro .mz').forEach(function(sec){
      var g = wallGroups[+sec.dataset.g], d = 0;
      $$('.rn', sec).forEach(function(r){ var on = isQ(+r.dataset.id); if (on) d++; if (r.classList.contains('on') !== on) r.classList.toggle('on', on); });
      $('.mz-n', sec).textContent = d + ' de ' + g.ids.length;
      sec.classList.toggle('full', d === g.ids.length);
    });
  }
  // al entrar, las gestas nuevas desde la última visita se tallan una a una
  function openWall(){
    if (!wallBuilt) buildWall();
    updateWall();
    var seen = {}, fresh = [];
    try { (JSON.parse(store.get('muro-visto') || '[]') || []).forEach(function(id){ seen[id] = 1; }); } catch(e){}
    $$('#muro .rn.on').forEach(function(r){ r.classList.remove('fresh'); if (!seen[r.dataset.id]) fresh.push(r); });
    fresh.forEach(function(r, i){ r.style.setProperty('--i', Math.min(i, 90)); r.classList.add('fresh'); });
    for (var k = 0; k < Math.min(fresh.length, 12); k++) tink(0.05 + k * 0.19);
    $('#muro-new').textContent = fresh.length ? (fresh.length === 1 ? 'Una gesta nueva tallada desde tu última visita.' : fresh.length + ' gestas nuevas talladas desde tu última visita.') : '';
    store.set('muro-visto', JSON.stringify(QALL.filter(isQ)));
  }
  // el cincel: un golpe corto y un timbre de metal, solo si se ha pedido
  var actx = null;
  function tink(delay){
    if (store.get('cincel') !== '1') return;
    try {
      actx = actx || new (window.AudioContext || window.webkitAudioContext)();
      var t = actx.currentTime + (delay || 0), o = actx.createOscillator(), g = actx.createGain();
      o.type = 'triangle'; o.frequency.setValueAtTime(1900 + Math.random() * 900, t);
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.08, t + 0.004); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.17);
      o.connect(g); g.connect(actx.destination); o.start(t); o.stop(t + 0.2);
      var buf = actx.createBuffer(1, 1100, actx.sampleRate), ch = buf.getChannelData(0), n = actx.createBufferSource(), ng = actx.createGain();
      for (var i = 0; i < ch.length; i++) ch[i] = (Math.random() * 2 - 1) * (1 - i / ch.length);
      ng.gain.value = 0.05; n.buffer = buf; n.connect(ng); ng.connect(actx.destination); n.start(t);
    } catch(e){}
  }
  var nameIn = $('#nombre'), cinIn = $('#cincel');
  if (nameIn){ nameIn.value = store.get('nombre') || ''; nameIn.addEventListener('input', function(){ store.set('nombre', nameIn.value); updateWall(); }); }
  if (cinIn){ cinIn.checked = store.get('cincel') === '1'; cinIn.addEventListener('change', function(){ store.set('cincel', cinIn.checked ? '1' : '0'); tink(); }); }

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
