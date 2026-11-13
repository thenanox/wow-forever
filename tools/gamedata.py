"""Datos del juego: carga de la caché, clasificación por facción, resolución de nombres
y consultas a forever.warcraftdb.com (siempre con caché en disco)."""
import os, re, json, glob, html, time, urllib.request, urllib.parse
from collections import defaultdict, Counter

import questie

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'cache')
DATA = os.path.join(ROOT, 'data')
HOST = 'https://forever.warcraftdb.com'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
OFFLINE = False
QS = questie.load()          # Questie: requisitos, raza y clase de cada quest ({} si no se ha descargado)
QV = questie.version()       # versión descargada y nombres de zonas y profesiones por número
MY_SKILLS = {202: 'Ingeniería', 186: 'Minería', 185: 'Cocina', 356: 'Pesca', 129: 'Primeros auxilios'}     # las del personaje
SKILL_ES = {**MY_SKILLS, 164: 'Herrería', 165: 'Peletería', 171: 'Alquimia', 182: 'Herboristería', 197: 'Sastrería',
            333: 'Encantamiento', 393: 'Desuello', 762: 'Equitación'}

ALLY_REP = {'Stormwind', 'Ironforge', 'Gnomeregan Exiles', 'Darnassus', 'Wildhammer Clan', 'Brotherhood of the Horse',
            'The League of Arathor', 'Stormpike Guard', 'Silverwing Sentinels', 'Theramore Expeditionary Force',
            'Azeroth Commerce Authority', 'High Order', 'Alliance'}
HORDE_REP = {'Orgrimmar', 'Undercity', 'Thunder Bluff', 'Darkspear Trolls', "Bolder'ok Clan", 'Revantusk Trolls',
             'The Defilers', 'Frostwolf Clan', 'Warsong Outriders', 'Durotar Supply and Logistics', 'Horde',
             'Windshaper', 'Windshapers', 'Tranquillien', 'Silvermoon City'}
HORDE_MAPS = {'Orgrimmar', 'Undercity', 'Thunder Bluff', 'Durotar', 'Mulgore', 'Tirisfal Glades', 'Silverpine Forest'}
BAD_NAME = re.compile(r'\[|<|\bTEST\b|\bUNUSED\b|\bDEPRECATED\b|\bREUSE\b|zzOLD|\bNYI\b|\(old\)|\bDEP\b', re.I)
QUALITY = {'#9d9d9d': 0, '#ffffff': 1, '#1eff00': 2, '#0070dd': 3, '#a335ee': 4, '#ff8000': 5}


def norm(s):
    s = html.unescape(s or '').replace('’', "'").replace('‘', "'").replace('…', '...')
    return re.sub(r'\s+', ' ', s).strip().lower().rstrip('.').strip()


def get_json(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception:
            if k == tries - 1: raise
            time.sleep(1.2 * (k + 1))


def cached(kind, key, url):
    """Devuelve el JSON de `url`, guardado en cache/<kind>/<key>.json."""
    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', str(key))[:120]
    path = os.path.join(CACHE, kind, safe + '.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    if OFFLINE:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        d = get_json(url)
    except Exception as e:
        d = {'err': str(e)[:120]}
    json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    time.sleep(0.12)
    return d


# ---------- quests ----------
def load_quests():
    Q = {}
    for p in glob.glob(os.path.join(CACHE, 'quest', '*.json')):
        d = json.load(open(p, encoding='utf-8'))
        if 'err' in d or not d.get('name'): continue
        Q[d['id']] = d
    enrich(Q)
    return Q


def playable(qid):
    """¿Puede hacerla este enano chamán? None si Questie no conoce la quest.
    Questie la descarta si es de otra raza, clase o facción, si pide una profesión que el personaje no tiene
    o si está en su lista de ocultas (1). Las ocultas solo en el mapa (2) existen y se pueden hacer."""
    s = QS.get(qid)
    if not s: return None
    return bool(s['dwarf'] and s['shaman'] and s['side'] != 'H' and s.get('hid') != 1 and not other_skill(qid))


def other_skill(qid):
    """Nombre de la profesión que pide la quest si el personaje no la tiene."""
    sk = (QS.get(qid) or {}).get('skill')
    if sk and sk[0] not in MY_SKILLS: return SKILL_ES.get(sk[0], str(sk[0]))
    return None


NOISE = re.compile(r"^Craftsman's Writ|\bMission [IVXLC]+:", re.I)

def repeatable(qid):
    f = (QS.get(qid) or {}).get('flags', 0)
    return 'REPEATABLE' in str(f).upper() if isinstance(f, (str, list, tuple)) else bool(int(f or 0) & 1)


def prereqs(qid):
    """(todas estas, una de estas): lo que hay que tener completado, como lo comprueba Questie (QuestieDB.IsDoable).
    Si la quest tiene preQuestSingle basta una de esa lista y preQuestGroup no cuenta; si no, hacen falta todas
    las de preQuestGroup, y por cada una vale también otra que se excluya con ella (salvo las marcadas como exactas)."""
    s = QS.get(qid)
    if not s: return [], []
    if s['pres']: return [], [i for i in s['pres'] if playable(i)]
    al = []
    for i in s['preg']:
        if playable(i): al.append(i)
        elif i not in s.get('strict', ()):
            alt = [e for e in (QS.get(i) or {}).get('excl', []) if playable(e)]
            if alt: al.append(alt[0])
    return al, []


def parent(qid):
    """Quest que hay que tener cogida, sin entregar, para que salga esta (parentQuest)."""
    p = (QS.get(qid) or {}).get('parent')
    return p if p and playable(p) else None


def pretty_zone(z):
    """Nombre legible de una zona de Questie por su número: DUN_MOROGH -> Dun Morogh."""
    name = (QV.get('zones') or {}).get(str(z))
    if not name: return None
    return ' '.join(w.capitalize() if w not in ('OF', 'THE') or k == 0 else w.lower() for k, w in enumerate(name.split('_')))


def enrich(Q):
    """Completa las fichas de Warcraft DB con Questie: nivel y objetivo que falten, quién da y recoge, requisitos."""
    if not QS: return
    # las quests sin nivel en Warcraft DB solo cuentan si enlazan por requisitos con una que sí lo tiene
    link = defaultdict(set)
    for i in Q:
        if not playable(i): continue
        al, an = prereqs(i)
        for p in al + an:
            if p in Q: link[i].add(p); link[p].add(i)
    seen = {i for i, q in Q.items() if q.get('level') is not None}
    stack = list(seen)
    while stack:
        for j in link[stack.pop()]:
            if j not in seen: seen.add(j); stack.append(j)
    need, oneed = set(), set()
    for i, q in Q.items():
        s = QS.get(i)
        if not s: continue
        # Warcraft DB deja sin nivel muchas quests reales: valen las de Questie que no sean repetibles ni encargos en serie
        if q.get('level') is None and playable(i) and (s.get('lv') or 0) > 0 and (i in seen or not (repeatable(i) or NOISE.search(q.get('name') or ''))):
            q['level'], q['min'] = s['lv'], s.get('min') or q.get('min')
        # si las dos fuentes dan un nivel mínimo distinto vale el más alto: llegar antes de tiempo es peor que llegar tarde
        if q.get('min') and (s.get('min') or 0) > q['min'] and playable(i): q['min'] = s['min']
        if not q.get('obj') and s.get('obj'): q['obj'] = s['obj']
        if not q.get('starts'): need.update(s['sn'][:1]); oneed.update(s['so'][:1])
        if not q.get('ends'): need.update(s['en'][:1]); oneed.update(s['eo'][:1])
        need.update(x['id'] for x in (q.get('starts') or [])[:1] if x.get('t') == 'npc')
    NP, OB = questie.npcs(need), questie.objects(oneed)
    votes = defaultdict(Counter)                             # número de zona de Questie -> nombre de mapa de Warcraft DB
    for q in Q.values():
        st = (q.get('starts') or [None])[0]
        if st and st.get('t') == 'npc' and q.get('sc') and q['sc'][2] and st['id'] in NP:
            zs = [z for z in NP[st['id']][1] if isinstance(z, int)]
            if len(zs) == 1: votes[zs[0]][q['sc'][2]] += 1
    zname = {z: c.most_common(1)[0][0] for z, c in votes.items()}
    zn = lambda z: zname.get(z) or pretty_zone(z)
    def where(nid, qzone, kind='npc'):
        """Referencia al PNJ u objeto y su posición: en la zona de la quest si aparece allí; si hay varias y ninguna encaja, sin posición."""
        n = (NP if kind == 'npc' else OB).get(nid)
        if not n: return None, None
        named = [(zn(z), xy) for z, xy in n[1].items()]
        pick = next(((z, xy) for z, xy in named if z and z == qzone), None) or (named[0] if len(named) == 1 and named[0][0] else None)
        return {'t': kind, 'id': nid, 'name': n[0]}, ([round(pick[1][0], 1), round(pick[1][1], 1), pick[0]] if pick else None)
    for i, q in Q.items():
        s = QS.get(i)
        if not s: continue
        for field, coord, who, what in (('starts', 'sc', s['sn'], s['so']), ('ends', 'ec', s['en'], s['eo'])):
            if q.get(field): continue
            ref, c = where(who[0], q.get('zone')) if who else where(what[0], q.get('zone'), 'object') if what else (None, None)
            if ref:
                q[field] = [ref]
                if c and not q.get(coord): q[coord] = c


def faction(q):
    """'A' Alianza, 'H' Horda o no disponible para un enano chamán, 'N' neutral o desconocida."""
    ok = playable(q['id'])
    if ok is False: return 'H'
    if ok: return 'A' if QS[q['id']]['side'] == 'A' else 'N'
    if q.get('side') == 'Horde': return 'H'
    if q.get('side') == 'Alliance': return 'A'
    reps = {r['name'] for r in (q.get('rep') or []) if (r.get('v') or 0) > 0}
    if reps & HORDE_REP and not reps & ALLY_REP: return 'H'
    if reps & ALLY_REP: return 'A'
    for c in (q.get('sc'), q.get('ec')):
        if c and c[2] in HORDE_MAPS: return 'H'
    return 'N'


def usable(q):
    return q.get('level') is not None and q.get('name') and not BAD_NAME.search(q['name'])


def is_new(q):
    return q['id'] >= 90000


class Names:
    """Resuelve un nombre a (tipo, id) con preferencia por la Alianza."""

    def __init__(self, Q):
        self.Q = Q
        self.wt = defaultdict(dict)          # tipo -> nombre normalizado -> id (enlaces de Warcraft Tavern)
        p = os.path.join(DATA, 'wt-ids.tsv')
        if os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                t, i, n = line.rstrip('\n').split('\t')
                self.wt[t].setdefault(norm(n), int(i))
        self.pre = {}
        p = os.path.join(DATA, 'resolved-names.json')
        if os.path.exists(p):
            for n, v in json.load(open(p, encoding='utf-8')).items():
                if v.get('id') and v.get('type') in ('quest', 'npc', 'item', 'object', 'spell'):
                    self.pre[norm(n)] = (v['type'], int(v['id']))
        self.byname = defaultdict(list)
        for q in Q.values():
            if q.get('name') and not BAD_NAME.search(q['name']) and faction(q) != 'H':
                self.byname[norm(q['name'])].append(q)
        self.manual = {}
        p = os.path.join(DATA, 'manual-ids.json')
        if os.path.exists(p):
            for n, v in json.load(open(p, encoding='utf-8')).items():
                self.manual[norm(n)] = (v[0], int(v[1]))

    def quest(self, name):
        k = norm(name)
        if k in self.manual and self.manual[k][0] == 'quest': return self.manual[k][1]
        c = self.byname.get(k)
        if not c: return None
        w = self.wt['quest'].get(k)
        if w and any(q['id'] == w for q in c): return w
        c = sorted(c, key=lambda q: (0 if q.get('level') is not None else 1, 0 if faction(q) == 'A' else 1, 0 if q.get('starts') else 1, q['id']))
        return c[0]['id']

    def any(self, name):
        """(tipo, id) o None. Quests primero; luego lo que enlaza Warcraft Tavern; luego la búsqueda previa."""
        k = norm(name)
        if k in self.manual: return self.manual[k]
        q = self.quest(name)
        if q: return ('quest', q)
        for t in ('item', 'npc', 'object', 'spell'):
            if k in self.wt[t]: return (t, self.wt[t][k])
        if k in self.pre and self.pre[k][0] != 'quest': return self.pre[k]
        return None

    def search(self, name, want):
        """Busca en la base de datos un nombre exacto del tipo pedido ('item' o 'npc')."""
        k = norm(name)
        if k in self.manual and self.manual[k][0] == want: return self.manual[k][1]
        if k in self.wt[want]: return self.wt[want][k]
        if k in self.pre and self.pre[k][0] == want: return self.pre[k][1]
        res = cached('search', want + '-' + k, f"{HOST}/api/v1/search?q={urllib.parse.quote(name)}")
        if not isinstance(res, list): return None
        hits = [r for r in res if r.get('type') == want and norm(r.get('name')) == k]
        if not hits: return None
        return max(h['id'] for h in hits) if want == 'item' else hits[0]['id']


# ---------- objetos ----------
def clean(s):
    s = re.sub(r'<br\s*/?>', ' ', s or '')
    s = html.unescape(re.sub(r'<[^>]+>', '', s))
    s = s.replace('$N', 'aventurero').replace('$n', 'aventurero').replace('$B', ' ').replace('$b', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def item_tip(iid):
    """{'n': nombre, 'q': calidad 0-5, 'l': [líneas del tooltip]} o None."""
    d = cached('item', iid, f'{HOST}/api/v1/tooltip/item/{iid}')
    if not d or 'html' not in d: return None
    h = d['html']
    m = re.search(r'<tt-title[^>]*data-quality="(\d+)"', h)
    q = int(m.group(1)) if m else (d.get('quality') or 1)
    h = re.sub(r'<tt-title[^>]*>.*?</tt-title>', '', h, flags=re.S)
    h = re.sub(r'<tt-double-line>\s*<span>(.*?)</span>\s*<span>(.*?)</span>\s*</tt-double-line>',
               lambda m: '<L>' + m.group(1) + ' · ' + m.group(2) + '</L>', h, flags=re.S)
    h = re.sub(r'<tt-line[^>]*>(.*?)</tt-line>', r'<L>\1</L>', h, flags=re.S)
    lines = []
    for x in re.findall(r'<L>(.*?)</L>', h, re.S):
        t = clean(x).strip(' ·')
        if t and not t.lower().startswith('sell price') and t not in lines:
            lines.append(t)
    return {'n': d.get('name') or '', 'q': max(0, min(5, q)), 'l': lines[:14]}
