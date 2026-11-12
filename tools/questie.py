"""Base de datos de quests de Questie para Forever (repositorio Questie/QuestieDB).

Aporta lo que la API de Warcraft DB no trae: requisitos entre quests, raza y clase exigidas.
Se aplican las capas en el mismo orden que el addon:
  data/Forever/foreverQuestDB.lua -> legacy/classicQuestFixes.lua -> generated/foreverBaseQuest.lua -> foreverQuestFixes.lua

  python3 tools/questie.py            descarga lo que falte y regenera cache/questie/quests.json
  python3 tools/questie.py --refresh  vuelve a descargar los cuatro archivos
"""
import os, re, sys, json, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'cache', 'questie')
OUT = os.path.join(DIR, 'quests.json')
FILES = [('foreverNpcDB.lua', 'data/Forever/foreverNpcDB.lua'),
         ('foreverBaseNpc.lua', 'src/corrections/Forever/generated/foreverBaseNpc.lua'),
         ('foreverQuestDB.lua', 'data/Forever/foreverQuestDB.lua'),
         ('classicQuestFixes.lua', 'src/corrections/Forever/legacy/classicQuestFixes.lua'),
         ('foreverBaseQuest.lua', 'src/corrections/Forever/generated/foreverBaseQuest.lua'),
         ('foreverQuestFixes.lua', 'src/corrections/Forever/foreverQuestFixes.lua')]
DWARF, SHAMAN = 4, 64
ALLY_BITS, HORDE_BITS = 77 | 1 << 32, 178 | 1 << 33      # bits 32 y 33: la raza nueva (Skyborne) en cada facción
TOKEN = re.compile(r'-?\d+(?:\.\d+)?|-?[A-Za-z_][\w.]*')
NAMEKEY = re.compile(r'([A-Za-z_]\w*)\s*=(?!=)')


class Lua:
    """Lector mínimo de tablas Lua: cadenas, números, nil, sumas de constantes y tablas con o sin clave."""

    def __init__(self, s, keys):
        self.s, self.i, self.keys = s, 0, keys

    def ws(self):
        s = self.s
        while self.i < len(s):
            if s[self.i] in ' \t\r\n': self.i += 1
            elif s.startswith('--', self.i):
                j = s.find('\n', self.i)
                self.i = len(s) if j < 0 else j
            else: break

    def value(self):
        self.ws()
        ch = self.s[self.i]
        if ch == '{': return self.table()
        if ch in '"\'': return self.string()
        return self.expr()

    def string(self):
        s, q = self.s, self.s[self.i]
        j, out = self.i + 1, []
        while s[j] != q:
            if s[j] == '\\': j += 1
            out.append(s[j]); j += 1
        self.i = j + 1
        return ''.join(out)

    def expr(self):
        terms = []
        while True:
            self.ws()
            m = TOKEN.match(self.s, self.i)
            if not m: raise ValueError('expresión no reconocida: ' + self.s[self.i:self.i + 40])
            self.i = m.end(); self.ws()
            if self.i < len(self.s) and self.s[self.i] == '(':       # llamada, p. ej. l10n("texto"): vale su primer argumento
                self.i += 1; args = []
                while True:
                    self.ws()
                    if self.s[self.i] == ')': self.i += 1; break
                    args.append(self.value()); self.ws()
                    if self.s[self.i] == ',': self.i += 1
                terms.append(('v', args[0] if args else None))
            else:
                terms.append(('t', m.group(0)))
            self.ws()
            if self.i < len(self.s) and self.s[self.i] == '+': self.i += 1; continue
            if self.s.startswith('..', self.i): self.i += 2; continue
            break
        vals = [v if k == 'v' else self.const(v) for k, v in terms]
        if len(vals) == 1: return vals[0]
        if all(isinstance(v, (int, float)) for v in vals): return sum(vals)
        return tuple(str(v) for v in vals)

    def const(self, t):
        if t == 'nil': return None
        if t == 'true': return True
        if t == 'false': return False
        if re.match(r'-?\d', t): return float(t) if '.' in t else int(t)
        if t.startswith('questKeys.'): return self.keys[t[10:]]
        return t                                             # raceIDs.X, classIDs.X, zoneIDs.X: se dejan como nombre

    def table(self):
        s = self.s
        self.i += 1
        d, n = {}, 0
        while True:
            self.ws()
            if s[self.i] == '}': self.i += 1; break
            if s[self.i] == '[':
                self.i += 1
                k = self.value(); self.ws()
                assert s[self.i] == ']', s[self.i - 30:self.i + 30]
                self.i += 1; self.ws()
                assert s[self.i] == '=', s[self.i - 30:self.i + 30]
                self.i += 1
                d[k] = self.value()
            else:
                m = NAMEKEY.match(s, self.i)
                if m:
                    self.i = m.end(); d[m.group(1)] = self.value()
                else:
                    n += 1; d[n] = self.value()
            self.ws()
            if s[self.i] in ',;': self.i += 1
        return d


def seq(t):
    """Parte posicional de una tabla, como lista."""
    if not isinstance(t, dict): return []
    return [t[k] for k in sorted(k for k in t if isinstance(k, int))]


def flat_ids(t):
    return [x for x in seq(t) if isinstance(x, int)]


def mask_ok(v, bit, names):
    """¿Admite la máscara de raza o clase el bit pedido? Sin máscara, admite a todos."""
    if v is None or v == 0: return True
    if isinstance(v, (int, float)): return bool(int(v) & bit)
    parts = v if isinstance(v, tuple) else (v,)
    return any(p.split('.')[-1] in names for p in parts)


def side(v):
    if v is None or v == 0: return 'N'
    if isinstance(v, (int, float)):
        a, h = int(v) & ALLY_BITS, int(v) & HORDE_BITS
    else:
        parts = [p.split('.')[-1] for p in (v if isinstance(v, tuple) else (v,))]
        if 'NONE' in parts or 'ALL' in parts: return 'N'
        horde = {'ALL_HORDE', 'ORC', 'UNDEAD', 'TAUREN', 'TROLL', 'SKYBORNE_HORDE', 'BLOOD_ELF', 'GOBLIN'}
        h = any(p in horde for p in parts)
        a = any(p not in horde for p in parts)
    return 'N' if a and h else 'A' if a else 'H' if h else 'N'


ENTRY = re.compile(r'^\s{4,12}\[(\d+)\] = (\{)', re.M)

def keyed_tables(text, keys):
    """Entradas {id: {campo: valor}} de un archivo de correcciones, sin el bloque exclusivo de la Horda.
    Cada entrada se lee por separado: una que no se entienda se salta y se cuenta."""
    h = text.find('local questFixesHorde = {')
    a = text.find('local questFixesAlliance = {')
    skip = (h, a if a > h else len(text)) if h >= 0 else (-1, -1)
    out, bad, pos = {}, 0, 0
    while True:
        m = ENTRY.search(text, pos)
        if not m: break
        if skip[0] <= m.start() < skip[1]:
            pos = m.end(); continue
        p = Lua(text, keys); p.i = m.start(2)
        try:
            out.setdefault(int(m.group(1)), {}).update(p.table()); pos = p.i
        except Exception:
            bad += 1; pos = m.end()
    return out, bad


def download(refresh=False):
    os.makedirs(DIR, exist_ok=True)
    for name, path in FILES:
        dst = os.path.join(DIR, name)
        if os.path.exists(dst) and not refresh: continue
        data = subprocess.run(['gh', 'api', f'repos/Questie/QuestieDB/contents/{path}', '-H', 'Accept: application/vnd.github.raw'],
                              capture_output=True, check=True).stdout
        open(dst, 'wb').write(data)


def build():
    read = lambda n: open(os.path.join(DIR, n), encoding='utf-8').read()
    base = read('foreverQuestDB.lua')
    head = base[:base.index('QuestieDB.questData')]
    keys = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s*\['(\w+)'\] = (\d+),", head, re.M)}
    raw = {}
    for m in re.finditer(r'^\[(\d+)\] = (\{)', base, re.M):
        p = Lua(base, keys); p.i = m.start(2)
        raw[int(m.group(1))] = p.table()
    for name in ('classicQuestFixes.lua', 'foreverBaseQuest.lua', 'foreverQuestFixes.lua'):
        tab, bad = keyed_tables(read(name), keys)
        if bad: print(f'{name}: {bad} entradas sin leer')
        for qid, fields in tab.items():
            raw.setdefault(qid, {}).update({k: v for k, v in fields.items() if isinstance(k, int)})
    K = keys
    out = {}
    for qid, r in raw.items():
        if not r.get(K['name']): continue
        races, classes = r.get(K['requiredRaces']), r.get(K['requiredClasses'])
        st, en = r.get(K['startedBy']) or {}, r.get(K['finishedBy']) or {}
        skill = seq(r.get(K['requiredSkill']))
        q = {'n': r[K['name']], 'min': r.get(K['requiredLevel']), 'lv': r.get(K['questLevel']),
             'dwarf': mask_ok(races, DWARF, {'DWARF', 'ALL_ALLIANCE', 'ALL', 'NONE'}),
             'shaman': mask_ok(classes, SHAMAN, {'SHAMAN', 'ALL', 'NONE', 'ALL_CLASSES'}),
             'cls': bool(classes), 'side': side(races),
             'preg': flat_ids(r.get(K['preQuestGroup'])), 'pres': flat_ids(r.get(K['preQuestSingle'])),
             'next': r.get(K['nextQuestInChain']) or 0, 'excl': flat_ids(r.get(K['exclusiveTo'])),
             'parent': r.get(K['parentQuest']) or 0, 'child': flat_ids(r.get(K['childQuests'])),
             'bfor': r.get(K['breadcrumbForQuestId']) or 0,
             'sn': flat_ids(st.get(1)), 'so': flat_ids(st.get(2)), 'si': flat_ids(st.get(3)),
             'en': flat_ids(en.get(1)), 'eo': flat_ids(en.get(2)),
             'skill': skill if skill else None, 'zone': r.get(K['zoneOrSort']),
             'obj': next((x for x in seq(r.get(K['objectivesText'])) if isinstance(x, str)), ''),
             'flags': r.get(K['specialFlags']) or 0}
        out[qid] = q
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    return out


def npcs(ids):
    """{id: [nombre, {zona (número o constante): [x, y]}]} para los PNJ pedidos."""
    read = lambda n: open(os.path.join(DIR, n), encoding='utf-8').read()
    want, out = set(ids), {}
    if not want or not os.path.exists(os.path.join(DIR, 'foreverNpcDB.lua')): return out
    base = read('foreverNpcDB.lua')
    keys = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s*\['(\w+)'\] = (\d+),", base[:base.index('QuestieDB.npcData')], re.M)}
    def put(nid, r):
        name = r.get(keys['name'])
        if not name: return
        cur = out.setdefault(nid, [name, {}]); cur[0] = name
        sp = r.get(keys['spawns'])
        if isinstance(sp, dict):
            for zone, pts in sp.items():
                first = seq(pts)[0] if seq(pts) else None
                xy = seq(first) if isinstance(first, dict) else []
                if len(xy) >= 2 and all(isinstance(v, (int, float)) for v in xy[:2]) and xy[0] >= 0:
                    cur[1][zone] = [xy[0], xy[1]]
    for m in re.finditer(r'^\[(\d+)\] = (\{)', base, re.M):
        nid = int(m.group(1))
        if nid in want:
            p = Lua(base, keys); p.i = m.start(2)
            try: put(nid, p.table())
            except Exception: pass
    gen = read('foreverBaseNpc.lua') if os.path.exists(os.path.join(DIR, 'foreverBaseNpc.lua')) else ''
    gen = gen.replace('npcKeys.', 'questKeys.')              # mismo lector: las claves se resuelven con el mapa de PNJ
    for m in ENTRY.finditer(gen):
        nid = int(m.group(1))
        if nid in want:
            p = Lua(gen, keys); p.i = m.start(2)
            try: put(nid, {k: v for k, v in p.table().items() if isinstance(k, int)})
            except Exception: pass
    return out


def load():
    """{id: ficha} o {} si no se ha descargado nunca."""
    if not os.path.exists(OUT):
        if not all(os.path.exists(os.path.join(DIR, n)) for n, _ in FILES): return {}
        return build()
    return {int(k): v for k, v in json.load(open(OUT, encoding='utf-8')).items()}


if __name__ == '__main__':
    download('--refresh' in sys.argv)
    d = build()
    print(f'{len(d)} quests · con requisito {sum(1 for q in d.values() if q["preg"] or q["pres"])} · '
          f'para enano {sum(1 for q in d.values() if q["dwarf"])} · de clase {sum(1 for q in d.values() if q["cls"])}')
