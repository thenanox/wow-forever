"""Base de datos de Questie para Forever (repositorio Questie/QuestieDB), compuesta como la compone el addon.

Aporta lo que la API de Warcraft DB no trae: requisitos entre quests, raza y clase exigidas, quién las da.
El addon no lee un único archivo: parte de unos datos en bruto y les aplica capas en este orden
(src/config.lua y src/corrections/registry.lua del repositorio):

  1. data/Forever/forever*DB.lua                  datos en bruto, heredados de Classic
  2. legacy/classicQuestReputationFixes.lua       reputación (generada)
  3. legacy/classic*Fixes.lua : Load              correcciones heredadas de Classic
  4. generated/foreverBase*.lua                   quests, PNJ y objetos nuevos de Forever
  5. traces/forever*Traces.lua                    lo observado en partidas reales
  6. traces/foreverQuestRelationTraces.lua        requisitos y cadenas deducidos de esas partidas
  7. forever*Fixes.lua : Load                     correcciones escritas a mano para Forever
  8. pase derivado requiredRaces                  una quest sin raza hereda la facción del PNJ que la da
  9. classic*Fixes.lua : LoadFactionFixes         correcciones según el personaje (aquí, Alianza)
 10. forever*Fixes.lua : LoadDynamic              ídem, las de Forever

Cada corrección sustituye el campo entero, salvo las claves `campo_add` y `campo_remove`, que añaden o quitan
elementos de una lista; `{}` borra el campo. Las quests que Questie oculta salen de su lista negra
(Questie/Questie, Database/Corrections/QuestieQuestBlacklist.lua), evaluada como en Classic Era, que es
como se identifica Forever.

Este módulo solo lee los archivos: no ejecuta nada de lo descargado.

  python3 tools/questie.py              descarga lo que falte y regenera la caché
  python3 tools/questie.py --refresh    vuelve a descargar todo (de la última versión del repositorio)
  python3 tools/questie.py --why 1275   de qué capa sale cada campo de una quest

La versión descargada queda apuntada en data/questie-version.json, que va al repositorio: en otro equipo se baja
esa misma versión, no la última, para que la guía salga igual. Solo --refresh pasa a la última.

Al regenerar comprueba que cada capa se ha leído entera y que salen los valores que fijan las pruebas del repositorio.
"""
import os, re, sys, json, copy, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'cache', 'questie')
PIN = os.path.join(ROOT, 'data', 'questie-version.json')
OUT, OUT_NPC, OUT_OBJ, OUT_VER = (os.path.join(DIR, n) for n in ('quests.json', 'npcs.json', 'objects.json', 'version.json'))
DB_REPO, ADDON_REPO = 'Questie/QuestieDB', 'Questie/Questie'
C = 'src/corrections/'
DB_FILES = {
    'questMeta.lua': 'src/meta/questMeta.lua', 'npcMeta.lua': 'src/meta/npcMeta.lua', 'objectMeta.lua': 'src/meta/objectMeta.lua',
    'enum-expansions.lua': C + 'enum/expansions.lua', 'enum-quests.lua': C + 'enum/quests.lua', 'enum-zones.lua': C + 'enum/zones.lua',
    'enum-professions.lua': C + 'enum/professions.lua', 'enum-factions.lua': C + 'enum/factions.lua', 'enum-icons.lua': C + 'enum/icons.lua',
    'enum-phases.lua': C + 'enum/phases.lua', 'enum-waypoints.lua': C + 'enum/waypoints.lua', 'enum-items.lua': C + 'enum/items.lua',
    'foreverQuestDB.lua': 'data/Forever/foreverQuestDB.lua', 'foreverNpcDB.lua': 'data/Forever/foreverNpcDB.lua',
    'foreverObjectDB.lua': 'data/Forever/foreverObjectDB.lua',
    'classicQuestReputationFixes.lua': C + 'Forever/legacy/classicQuestReputationFixes.lua',
    'classicQuestFixes.lua': C + 'Forever/legacy/classicQuestFixes.lua', 'classicNPCFixes.lua': C + 'Forever/legacy/classicNPCFixes.lua',
    'classicObjectFixes.lua': C + 'Forever/legacy/classicObjectFixes.lua',
    'foreverBaseQuest.lua': C + 'Forever/generated/foreverBaseQuest.lua', 'foreverBaseNpc.lua': C + 'Forever/generated/foreverBaseNpc.lua',
    'foreverBaseObject.lua': C + 'Forever/generated/foreverBaseObject.lua',
    'foreverQuestTraces.lua': C + 'Forever/traces/foreverQuestTraces.lua', 'foreverNpcTraces.lua': C + 'Forever/traces/foreverNpcTraces.lua',
    'foreverObjectTraces.lua': C + 'Forever/traces/foreverObjectTraces.lua',
    'foreverQuestRelationTraces.lua': C + 'Forever/traces/foreverQuestRelationTraces.lua',
    'foreverQuestFixes.lua': C + 'Forever/foreverQuestFixes.lua', 'foreverNPCFixes.lua': C + 'Forever/foreverNPCFixes.lua',
    'foreverObjectFixes.lua': C + 'Forever/foreverObjectFixes.lua',
}
BLACKLIST = 'QuestieQuestBlacklist.lua'
ADDON_FILES = {BLACKLIST: 'Database/Corrections/QuestieQuestBlacklist.lua'}

# Capas estáticas en el orden de carga del registro (ventana + banda + posición) y, después, las del personaje.
STATIC = {
    'Quest': [('classicQuestReputationFixes.lua', 'Load'), ('classicQuestFixes.lua', 'Load'), ('foreverBaseQuest.lua', 'Load'),
              ('foreverQuestTraces.lua', 'Load'), ('foreverQuestRelationTraces.lua', 'Load'), ('foreverQuestFixes.lua', 'Load')],
    'Npc': [('classicNPCFixes.lua', 'Load'), ('foreverBaseNpc.lua', 'Load'), ('foreverNpcTraces.lua', 'Load'), ('foreverNPCFixes.lua', 'Load')],
    'Object': [('classicObjectFixes.lua', 'Load'), ('foreverBaseObject.lua', 'Load'), ('foreverObjectTraces.lua', 'Load'),
               ('foreverObjectFixes.lua', 'Load')],
}
DYNAMIC = {
    'Quest': [('classicQuestFixes.lua', 'LoadFactionFixes'), ('foreverQuestFixes.lua', 'LoadDynamic')],
    'Npc': [('classicNPCFixes.lua', 'LoadFactionFixes'), ('foreverNPCFixes.lua', 'LoadDynamic')],
    'Object': [('classicObjectFixes.lua', 'LoadFactionFixes'), ('foreverObjectFixes.lua', 'LoadDynamic')],
}
BASE = {'Quest': ('foreverQuestDB.lua', 'questData'), 'Npc': ('foreverNpcDB.lua', 'npcData'), 'Object': ('foreverObjectDB.lua', 'objectData')}
META = {'Quest': 'questMeta.lua', 'Npc': 'npcMeta.lua', 'Object': 'objectMeta.lua'}
FACTION = 'Alliance'                       # el personaje de la guía
RACE, CLASS = 'DWARF', 'SHAMAN'
OP = 1000                                  # campo + 1000 añade elementos, campo - 1000 los quita (src/corrections/tablePatch.lua)
NIL = '<nil>'                              # una corrección del personaje que borra un campo


# ---------------------------------------------------------------- lector de Lua (solo datos)
TOKEN = re.compile(r'''
    (?P<ws>\s+)
  | (?P<bc>--\[(?P<lv>=*)\[.*?\](?P=lv)\])
  | (?P<lc>--[^\n]*)
  | (?P<num>0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)
  | (?P<str>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
  | (?P<id>[A-Za-z_]\w*(?:[.:][A-Za-z_]\w*)*)
  | (?P<op>\.\.|==|~=|<=|>=|[{}\[\]=,;()+\-*/<>])
  | (?P<other>.)
''', re.S | re.X)
ESC = {'n': '\n', 't': '\t', 'r': '\r', 'a': '\a', 'b': '\b', 'f': '\f', 'v': '\v', '0': '\0'}
UNESC = re.compile(r'\\(\d{1,3}|.)', re.S)


def unquote(s):
    body = s[1:-1]
    if '\\' not in body: return body
    return UNESC.sub(lambda m: chr(int(m.group(1))) if m.group(1).isdigit() else ESC.get(m.group(1), m.group(1)), body)


def truthy(v):
    return v is not None and v is not False


class Lua:
    """Lee expresiones y tablas de Lua sin ejecutar nada. Los identificadores se resuelven con `env(nombre)`,
    que debe fallar con los que no conozca: aquí un dato sin entender no se salta, se avisa."""

    def __init__(self, text, env, start=0, end=None):
        self.kind, self.val, self.pos = [], [], []
        i, n = start, len(text) if end is None else end
        match = TOKEN.match
        while i < n:
            m = match(text, i, n)
            k = m.lastgroup                                  # lo que no sea dato (código suelto) solo falla si se llega a leer
            if k in ('num', 'str', 'id', 'op', 'other'):
                self.kind.append(k); self.val.append(m.group(k)); self.pos.append(i)
            i = m.end()
        self.kind.append('eof'); self.val.append(''); self.pos.append(n)
        self.i, self.env, self.text = 0, env, text

    def fail(self, what):
        p = self.pos[self.i]
        raise ValueError(f'Lua: {what} cerca de {self.text[max(0, p - 60):p + 60]!r}')

    def op(self, s):
        if self.kind[self.i] == 'op' and self.val[self.i] == s: self.i += 1; return True
        return False

    def word(self, s):
        if self.kind[self.i] == 'id' and self.val[self.i] == s: self.i += 1; return True
        return False

    def expect(self, s):
        if not self.op(s): self.fail(f'se esperaba {s!r}')

    # precedencia de Lua: or < and < comparación < .. < suma < producto < unarios
    def expr(self):
        v = self.conj()
        while self.word('or'):
            w = self.conj()
            v = v if truthy(v) else w
        return v

    def conj(self):
        v = self.comp()
        while self.word('and'):
            w = self.comp()
            v = w if truthy(v) else v
        return v

    def comp(self):
        v = self.concat()
        while self.kind[self.i] == 'op' and self.val[self.i] in ('==', '~=', '<', '<=', '>', '>='):
            o = self.val[self.i]; self.i += 1
            w = self.concat()
            v = (v == w if o == '==' else v != w if o == '~=' else v < w if o == '<' else v <= w if o == '<=' else v > w if o == '>' else v >= w)
        return v

    def concat(self):
        v = self.add()
        while self.op('..'): v = str(v) + str(self.add())
        return v

    def add(self):
        v = self.mul()
        while True:
            if self.op('+'): v = v + self.mul()
            elif self.op('-'): v = v - self.mul()
            else: return v

    def mul(self):
        v = self.unary()
        while True:
            if self.op('*'): v = v * self.unary()
            elif self.op('/'): v = v / self.unary()
            else: return v

    def unary(self):
        if self.op('-'): return -self.unary()
        if self.word('not'): return not truthy(self.unary())
        return self.primary()

    def primary(self):
        k, v = self.kind[self.i], self.val[self.i]
        if k == 'num':
            self.i += 1
            if v[:2] in ('0x', '0X'): return int(v, 16)
            return float(v) if any(c in v for c in '.eE') else int(v)
        if k == 'str':
            self.i += 1; return unquote(v)
        if k == 'op' and v == '{': return self.table()
        if k == 'op' and v == '(':
            self.i += 1; r = self.expr(); self.expect(')'); return self.index(r)
        if k != 'id': self.fail('valor inesperado')
        self.i += 1
        if v == 'nil': return None
        if v == 'true': return True
        if v == 'false': return False
        if self.op('('):                                      # llamada: solo l10n("texto"), que vale su texto
            args = []
            while not self.op(')'):
                args.append(self.expr()); self.op(',')
            if v != 'l10n': self.fail(f'llamada a {v} no admitida')
            return args[0] if args else None
        return self.index(self.env(v))

    def index(self, r):
        """`tabla[clave]` detrás de un valor, como en `({SHAMAN = 8380, …})[playerClass]`. Sin esa clave vale nil."""
        while self.kind[self.i] == 'op' and self.val[self.i] == '[' and isinstance(r, dict):
            self.i += 1; key = self.expr(); self.expect(']'); r = r.get(key)
        return r

    def table(self):
        """Tabla de Lua como diccionario: los elementos sin clave van con 1, 2, 3… y un nil no ocupa sitio, como en Lua."""
        self.expect('{')
        d, n = {}, 0
        kind, val = self.kind, self.val
        while True:
            if self.op('}'): return d
            if kind[self.i] == 'op' and val[self.i] == '[':
                self.i += 1; key = self.expr(); self.expect(']'); self.expect('=')
                v = self.expr()
            elif kind[self.i] == 'id' and kind[self.i + 1] == 'op' and val[self.i + 1] == '=':
                key = val[self.i]; self.i += 2
                v = self.expr()
            else:
                n += 1; key = n
                v = self.expr()
            if v is not None: d[key] = v
            if not (self.op(',') or self.op(';')):
                self.expect('}'); return d


def literal(name):
    raise KeyError(name)


def seq(t):
    """Parte de lista de una tabla, en orden."""
    if not isinstance(t, dict): return []
    return [t[k] for k in sorted(k for k in t if isinstance(k, int))]


def as_table(values):
    return {i + 1: v for i, v in enumerate(values)}


# ---------------------------------------------------------------- descarga
def read(name):
    return open(os.path.join(DIR, name), encoding='utf-8').read()


def gh(path, raw=True):
    cmd = ['gh', 'api', path] + (['-H', 'Accept: application/vnd.github.raw'] if raw else [])
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def download(refresh=False):
    """Descarga los archivos de una misma versión de cada repositorio y apunta cuál es."""
    os.makedirs(DIR, exist_ok=True)
    ver = json.load(open(OUT_VER, encoding='utf-8')) if os.path.exists(OUT_VER) else {}
    pin = json.load(open(PIN, encoding='utf-8')) if os.path.exists(PIN) else {}
    changed = False
    for key, repo, files in (('db', DB_REPO, DB_FILES), ('addon', ADDON_REPO, ADDON_FILES)):
        missing = [n for n in files if not os.path.exists(os.path.join(DIR, n))]
        want = None if refresh else pin.get(key)             # la versión apuntada en el repositorio manda, salvo con --refresh
        if not refresh and not missing and ver.get(key) and (not want or ver[key]['sha'] == want['sha']): continue
        if want: sha, date = want['sha'], want.get('date')
        else:
            head = json.loads(gh(f'repos/{repo}/commits/HEAD', raw=False))
            sha, date = head['sha'], head['commit']['committer']['date']
        for name, path in files.items():                    # todos de la misma versión: las capas dependen unas de otras
            open(os.path.join(DIR, name), 'wb').write(gh(f'repos/{repo}/contents/{path}?ref={sha}'))
        ver[key] = {'repo': repo, 'sha': sha, 'date': date}
        changed = True
    if changed: json.dump(ver, open(OUT_VER, 'w', encoding='utf-8'), indent=1)
    new = {k: ver[k] for k in ('db', 'addon') if k in ver}
    if new != pin: open(PIN, 'w', encoding='utf-8').write(json.dumps(new, indent=1, sort_keys=True) + '\n')
    return changed


# ---------------------------------------------------------------- esquema y constantes
def meta(kind):
    """(campo -> índice, índice -> forma) del esquema del repositorio."""
    s = read(META[kind])
    body = s[s.index('keys = {'):s.index('names = {')]
    keys = {m.group(1): int(m.group(2)) for m in re.finditer(r"\['(\w+)'\] = (\d+),", body)}
    st = re.search(r'structures = \{(.*?)\}', s, re.S).group(1)
    return keys, {int(m.group(1)): m.group(2) for m in re.finditer(r"\[(\d+)\]='(\w+)'", st)}


def enums():
    """Constantes con nombre que usan las correcciones, leídas de src/corrections/enum/."""
    t = {}
    for name in ('quests', 'zones', 'professions', 'factions', 'icons', 'phases', 'items', 'waypoints'):
        s = read(f'enum-{name}.lua')
        for m in re.finditer(r'^constants\.(\w+) = \{', s, re.M):
            try: t[m.group(1)] = Lua(s, literal, m.end() - 1).table()
            except (KeyError, ValueError): pass                # tablas con código (rutas predefinidas): fallarán solo si se usan
    s = read('enum-expansions.lua')
    loc = {}
    env = lambda n: loc[n]
    m = re.search(r'^constants\.raceMaskById = \{', s, re.M)
    loc['raceMaskById'] = Lua(s, literal, m.end() - 1).table()
    for m in re.finditer(r'^local (\w+) = (raceMaskById|classic|tbc|cata)[^\n]*$', s, re.M):
        loc[m.group(1)] = Lua(s, env, m.start(2), m.end()).expr()
    m = re.search(r'^constants\.byExpansion = \{', s, re.M)
    by = Lua(s, env, m.end() - 1).table()
    for name in ('raceKeys', 'classKeys', 'npcFlags'):          # Forever define las suyas; lo que falte, de Classic
        t[name] = by['Forever'].get(name) or by['Classic'][name]
    return t


ALIASES = {'raceIDs': 'raceKeys', 'classIDs': 'classKeys', 'profKeys': 'professionKeys', 'specKeys': 'specializationKeys',
           'rankKeys': 'rankNames', 'Questie': 'iconTypes'}
MODULES = ('QuestieDB', 'ZoneDB', 'QuestieProfessions', 'Phasing')


def make_env(E, keys):
    """Resuelve `questKeys.name`, `zoneIDs.DUN_MOROGH`, `raceIDs.ALL_ALLIANCE`… Un nombre desconocido es un error."""
    tables = dict(E)
    for kind, k in keys.items():
        full = dict(k)
        for name, idx in k.items():
            full[name + '_add'], full[name + '_remove'] = idx + OP, idx - OP
        tables[kind.lower() + 'Keys'] = full
    def env(name):
        if name == 'playerClass': return CLASS                  # algunas correcciones eligen por clase
        parts = name.split('.')
        if len(parts) == 3 and parts[0] in MODULES: parts = parts[1:]
        if len(parts) != 2: raise KeyError(name)
        return tables[ALIASES.get(parts[0], parts[0])][parts[1]]
    return env


# ---------------------------------------------------------------- capas
def base_rows(kind, keys):
    """Filas en bruto: {id: {índice de campo: valor}}."""
    name, field = BASE[kind]
    s = read(name)
    own = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s*\['(\w+)'\] = (\d+),", s[:s.index(f'QuestieDB.{field}')], re.M)}
    bad = {k: v for k, v in own.items() if keys.get(k) != v}
    if bad: raise ValueError(f'{name}: el esquema ha cambiado: {bad}')
    a = s.index('[[', s.index(f'QuestieDB.{field}')) + 2
    a = s.index('{', a)
    return Lua(s, literal, a, s.rindex(']]')).table()


def region(name, func):
    """(texto, inicio, fin) de la tabla que devuelve una función de un archivo de correcciones.
    Las del personaje declaran una tabla por facción y devuelven una u otra: se toma la de la guía."""
    s = read(name)
    m = re.search(r'^function \w+:' + func + r'\(\)', s, re.M)
    if not m: return s, 0, 0
    end = re.compile(r'^end\b', re.M).search(s, m.end())
    body_end = end.start() if end else len(s)
    pick = re.compile(r'^\s*local (\w+' + FACTION + r') = \{', re.M).search(s, m.end(), body_end)
    if pick:                                                 # la tabla de la facción acaba donde empieza lo siguiente
        nxt = re.compile(r'^    (local \w+ = \{|if )', re.M).search(s, pick.end(), body_end)
        return s, pick.end() - 1, nxt.start() if nxt else body_end
    pick = re.compile(r'^\s*return \{', re.M).search(s, m.end(), body_end)
    return (s, pick.end() - 1, body_end) if pick else (s, 0, 0)


def provider(name, func, env):
    """La tabla {id: {campo: valor}} de una capa."""
    s, a, b = region(name, func)
    return Lua(s, env, a, b).table() if b else {}


GROUPED = {'questgivers', 'objectives', 'spawnlist', 'waypointlist'}
ATOMIC = {'pair', 'trigger'}


def same(a, b, shape):
    if shape == 'spawnlist' and isinstance(a, dict) and isinstance(b, dict):      # sin fase es la fase cero
        return (a.get(1), a.get(2), a.get(3) or 0) == (b.get(1), b.get(2), b.get(3) or 0)
    return a == b


def resolve(fields, shapes, base, fallback=None):
    """Convierte las claves `_add` y `_remove` de una corrección en el valor final del campo (tablePatch.Resolve)."""
    ops = {}
    for k, v in fields.items():
        if isinstance(k, int) and (k <= 0 or k >= OP):
            ops.setdefault(k - OP if k >= OP else k + OP, {})['add' if k >= OP else 'remove'] = v
    if not ops: return fields
    out = {k: v for k, v in fields.items() if not (isinstance(k, int) and (k <= 0 or k >= OP))}
    for field, o in ops.items():
        shape = shapes.get(field)
        if shape is None or shape in ATOMIC or field in out: raise ValueError(f'operación no admitida sobre el campo {field} ({shape})')
        added, removed = o.get('add') or {}, o.get('remove') or {}
        if not added and not removed: continue
        cur = base.get(field) if base else None
        if cur is None and fallback: cur = fallback(field)
        if cur == NIL: cur = None
        result = copy.deepcopy(cur) if isinstance(cur, dict) else {}
        grouped = shape in GROUPED
        targets = result if grouped else {1: result}
        adds, rems = (added, removed) if grouped else ({1: added}, {1: removed})
        for g in set(adds) | set(rems):
            if shape == 'objectives' and g == 4: raise ValueError('operación sobre el objetivo de reputación')
            rem, kept = seq(rems.get(g)), []
            for v in seq(targets.get(g)):
                if not any(same(v, r, shape) for r in rem): kept.append(v)
            for v in seq(adds.get(g)):
                if not any(same(v, x, shape) for x in kept): kept.append(copy.deepcopy(v))
            if kept: targets[g] = as_table(kept)
            else: targets.pop(g, None)
        out[field] = targets if grouped else targets.get(1) or {}
    return out


def merge(rows, corrections, shapes, layer, prov):
    """Aplica una capa estática (registry.MergeInto): crea la fila si no existe y sustituye campo a campo."""
    for qid, fields in corrections.items():
        if not isinstance(qid, int) or not isinstance(fields, dict): continue
        row = rows.get(qid)
        resolved = resolve(fields, shapes, row)
        if row is None and (resolved is fields or resolved):
            row = rows[qid] = {}
        if row is None: continue
        p = prov.setdefault(qid, {}) if prov is not None else None
        for k, v in resolved.items():
            if isinstance(k, int):
                row[k] = v
                if p is not None: p[k] = layer


def compose(rows, layers, shapes, prov):
    """Correcciones del personaje (registry.recompose): cada capa pisa a la anterior y todas a los datos estáticos."""
    over = {}
    for layer, corrections in layers:
        for qid, fields in corrections.items():
            if not isinstance(qid, int) or not isinstance(fields, dict): continue
            row = over.get(qid)
            static = rows.get(qid) or {}
            for k, v in resolve(fields, shapes, row, static.get).items():
                if not isinstance(k, int): continue
                if row is None: row = over[qid] = {}
                row[k] = NIL if isinstance(v, dict) and not v else v
                if prov is not None: prov.setdefault(qid, {})[k] = layer
    for qid, fields in over.items():
        row = rows.setdefault(qid, {})
        for k, v in fields.items():
            if v == NIL: row.pop(k, None)
            else: row[k] = v


def entities(kind, E, keys, shapes, prov=None, derive=None):
    env = make_env(E, keys)
    rows = base_rows(kind, keys[kind])
    if prov is not None:
        for qid, row in rows.items(): prov[qid] = {k: 'datos en bruto' for k in row}
    for name, func in STATIC[kind]:
        merge(rows, provider(name, func, env), shapes[kind], name, prov)
    if derive: derive(rows)
    compose(rows, [(f'{name} ({FACTION})', provider(name, func, env)) for name, func in DYNAMIC[kind]], shapes[kind], prov)
    return rows


def derive_races(quests, npcs, qk, nk, races, prov=None):
    """Pase derivado de Questie: una quest sin raza hereda la facción de los PNJ que la dan, si son de una sola."""
    for qid, q in quests.items():
        if q.get(qk['requiredRaces']) not in (None, 0): continue
        starts = q.get(qk['startedBy'])
        if not isinstance(starts, dict): continue
        a = h = False
        for nid in seq(starts.get(1)):
            f = (npcs.get(nid) or {}).get(nk['friendlyToFaction'])
            if f == 'H': h = True
            elif f == 'A': a = True
            elif f == 'AH': a = h = True
        if a != h:
            q[qk['requiredRaces']] = races['ALL_ALLIANCE'] if a else races['ALL_HORDE']
            if prov is not None: prov.setdefault(qid, {})[qk['requiredRaces']] = 'facción del PNJ que la da'


# ---------------------------------------------------------------- quests que Questie oculta
def hidden_quests():
    """{id: 1 oculta, 2 solo fuera del mapa} según la lista negra del addon, evaluada como Classic Era sin temporada."""
    if not os.path.exists(os.path.join(DIR, BLACKLIST)): return {}
    s = read(BLACKLIST)
    a = s.index('local questsToBlacklist = {')
    b = re.compile(r'^    \}', re.M).search(s, a).end()
    known = {'Expansions.Current': 1, 'Expansions.Era': 1, 'Expansions.Tbc': 2, 'Expansions.Wotlk': 3, 'Expansions.Cata': 4,
             'Expansions.MoP': 5, 'Questie.IsSoD': False, 'Questie.IsTitanReforged': False, 'Questie.IsChinaRegion': False,
             'HIDE_ON_MAP': 'HIDE_ON_MAP', 'ContentPhases.activePhases.TBC': 0}
    t = Lua(s, lambda n: known[n], s.index('{', a), b).table()
    return {k: 2 if v == 'HIDE_ON_MAP' else 1 for k, v in t.items() if isinstance(k, int) and truthy(v)}


# ---------------------------------------------------------------- salida
def ids(t):
    return [x for x in seq(t) if isinstance(x, int)]


def spots(spawns):
    """Primera posición conocida en cada zona: {zona: [x, y]}. (-1, -1) es «dentro de una mazmorra»."""
    out = {}
    if isinstance(spawns, dict):
        for zone, pts in spawns.items():
            for p in seq(pts):
                xy = seq(p)
                if len(xy) >= 2 and all(isinstance(v, (int, float)) for v in xy[:2]) and xy[0] >= 0:
                    out[zone] = [xy[0], xy[1]]; break
    return out


def build(why=None):
    E = enums()
    keys, shapes = {}, {}
    for kind in META: keys[kind], shapes[kind] = meta(kind)
    qk, nk, ok = keys['Quest'], keys['Npc'], keys['Object']
    races, classes = E['raceKeys'], E['classKeys']
    ally, horde, mine, cls = races['ALL_ALLIANCE'], races['ALL_HORDE'], races[RACE], classes[CLASS]
    prov = {} if why else None
    npcs = entities('Npc', E, keys, shapes)
    objects = entities('Object', E, keys, shapes)
    # el pase derivado ve los PNJ con sus correcciones estáticas; las del personaje no cambian su facción
    quests = entities('Quest', E, keys, shapes, prov, lambda rows: derive_races(rows, npcs, qk, nk, races, prov))
    hidden = hidden_quests()
    if why:
        names = {v: k for k, v in qk.items()}
        for k, v in sorted((quests.get(why) or {}).items()):
            print(f'  {names.get(k, k):24} {json.dumps(v, ensure_ascii=False)[:150]:150}  ← {prov.get(why, {}).get(k)}')
        print('  oculta por Questie:', hidden.get(why, 'no'))
        return
    out = {}
    for qid, r in quests.items():
        if not r.get(qk['name']): continue
        g = lambda f: r.get(qk[f])
        mask, cmask = g('requiredRaces') or 0, g('requiredClasses') or 0
        st, en = g('startedBy') or {}, g('finishedBy') or {}
        group = ids(g('preQuestGroup'))
        skill = seq(g('requiredSkill'))
        out[qid] = {
            'n': g('name'), 'min': g('requiredLevel') or 0, 'lv': g('questLevel') or 0, 'max': g('requiredMaxLevel') or 0,
            'races': mask, 'classes': cmask,
            'dwarf': not mask or bool(mask & mine), 'shaman': not cmask or bool(cmask & cls), 'cls': bool(cmask),
            'side': 'N' if not mask or (mask & ally and mask & horde) else 'A' if mask & ally else 'H' if mask & horde else 'N',
            # preQuestSingle: basta una. preQuestGroup: hacen falta todas, y solo cuenta si no hay preQuestSingle.
            # En el grupo, un número negativo exige esa quest exacta (sin valer otra que se excluya con ella).
            'pres': ids(g('preQuestSingle')), 'preg': [abs(x) for x in group], 'strict': [-x for x in group if x < 0],
            'next': g('nextQuestInChain') or 0, 'excl': ids(g('exclusiveTo')),
            'parent': g('parentQuest') or 0, 'child': ids(g('childQuests')),
            'bfor': g('breadcrumbForQuestId') or 0, 'bread': ids(g('breadcrumbs')),
            'until': g('availableUntilCompleted') or 0, 'from': g('availableStartingWith') or 0, 'off': g('disabledByQuest') or 0,
            'sn': ids(st.get(1)), 'so': ids(st.get(2)), 'si': ids(st.get(3)), 'en': ids(en.get(1)), 'eo': ids(en.get(2)),
            'skill': skill if len(skill) == 2 and any(skill) else None, 'spell': g('requiredSpell') or 0,
            'spec': g('requiredSpecialization') or 0, 'rep': seq(g('requiredMinRep')) or None, 'maxrep': seq(g('requiredMaxRep')) or None,
            'zone': g('zoneOrSort') or 0, 'obj': next((x for x in seq(g('objectivesText')) if isinstance(x, str) and x), ''),
            'flags': g('specialFlags') or 0, 'qflags': g('questFlags') or 0, 'hid': hidden.get(qid, 0),
        }
    dump = lambda o, p: json.dump(o, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    dump(out, OUT)
    dump({i: [r.get(nk['name']), spots(r.get(nk['spawns'])), r.get(nk['friendlyToFaction']) or '', r.get(nk['zoneID']) or 0]
          for i, r in npcs.items() if r.get(nk['name'])}, OUT_NPC)
    dump({i: [r.get(ok['name']), spots(r.get(ok['spawns'])), r.get(ok['zoneID']) or 0] for i, r in objects.items() if r.get(ok['name'])}, OUT_OBJ)
    ver = json.load(open(OUT_VER, encoding='utf-8')) if os.path.exists(OUT_VER) else {}
    ver['zones'] = {str(v): k for k, v in sorted(E['zoneIDs'].items()) if isinstance(v, int)}
    ver['sorts'] = {str(v): k for k, v in E['sortKeys'].items() if isinstance(v, int)}
    ver['skills'] = {str(v): k for k, v in E['professionKeys'].items()}
    ver['factions'] = {str(v): k for k, v in E['factionIDs'].items()}
    json.dump(ver, open(OUT_VER, 'w', encoding='utf-8'), indent=1)
    return out


# ---------------------------------------------------------------- comprobación
# Valores que fijan las pruebas del propio repositorio (tools/validation/forever-delta-base.test.lua): si alguno
# falla, o ha cambiado el dato o este lector ya no compone las capas como el addon.
WITNESS_Q = [(2, 'n', "Sharptalon's Claw"), (90902, 'races', 16), (90902, 'classes', 2), (94007, 'races', 12884901888),
             (86585, 'races', 4294967373), (94004, 'races', 0), (97286, 'races', 0), (97286, 'classes', 128),
             (86585, 'n', 'Banner of the Fallen'), (86585, 'sn', [269153]), (86585, 'en', [1092]), (94004, 'si', [264011])]
WITNESS_N = [(211033, 2, 'A'), (205729, 2, 'H'), (202093, 2, 'AH'), (269153, 0, 'Mountaineer Ylva'), (269153, 3, 38), (251428, 3, 16593)]
WITNESS_O = [(424005, 2, 406), (375548, 2, 331), (175725, 0, 'The Old Gods and the Ordering of Azeroth')]
HELD = (92534, 94901, 3911)                                  # quests que el repositorio retiene: no deben existir


def check():
    """Lista de fallos: capas que no se han leído enteras y valores de referencia que no coinciden."""
    bad = []
    E = enums(); keys, shapes = {}, {}
    for kind in META: keys[kind], shapes[kind] = meta(kind)
    env = make_env(E, keys)
    for kind in META:
        s = read(BASE[kind][0])
        if len(re.findall(r'^\[\d+\] = \{', s, re.M)) != len(base_rows(kind, keys[kind])): bad.append(f'{BASE[kind][0]}: filas sin leer')
        for name, func in STATIC[kind] + DYNAMIC[kind]:
            s, a, b = region(name, func)
            code = re.sub(r'--\[(=*)\[.*?\]\1\]', '', s[a:b], flags=re.S)
            code = re.sub(r'^\s*--[^\n]*$', '', code, flags=re.M)
            top = set(re.findall(r'^ {8}\[(\d+)\]\s*=\s*\{', code, re.M))
            got = provider(name, func, env)
            if len(top) != len(got): bad.append(f'{name}:{func}: {len(got)} entradas leídas de {len(top)}')
    q = {int(k): v for k, v in json.load(open(OUT, encoding='utf-8')).items()}
    n, o = json.load(open(OUT_NPC, encoding='utf-8')), json.load(open(OUT_OBJ, encoding='utf-8'))
    for i, f, want in WITNESS_Q:
        got = (q.get(i) or {}).get(f)
        if (got[:len(want)] if isinstance(want, list) and isinstance(got, list) else got) != want: bad.append(f'quest {i} {f}: {got!r}, se esperaba {want!r}')
    for table, wit, what in ((n, WITNESS_N, 'PNJ'), (o, WITNESS_O, 'objeto')):
        for i, f, want in wit:
            got = (table.get(str(i)) or [None] * 4)[f]
            if got != want: bad.append(f'{what} {i} campo {f}: {got!r}, se esperaba {want!r}')
    bad += [f'quest {i} no debería existir' for i in HELD if i in q]
    return bad


# ---------------------------------------------------------------- consulta
def load():
    """{id: ficha}. Si falta, o si el repositorio apunta otra versión, la descarga (hace falta `gh` con sesión iniciada)."""
    pin = json.load(open(PIN, encoding='utf-8')) if os.path.exists(PIN) else {}
    have = version()
    stale = any(k in pin and (have.get(k) or {}).get('sha') != pin[k]['sha'] for k in ('db', 'addon'))
    changed = False
    if stale or not all(os.path.exists(os.path.join(DIR, n)) for n in list(DB_FILES) + list(ADDON_FILES)):
        try:
            changed = download()
        except (OSError, subprocess.CalledProcessError) as e:
            sys.exit(f'Falta la base de datos de Questie y no se ha podido descargar ({e}). Ejecuta: python3 tools/questie.py')
    if changed or not os.path.exists(OUT): return build()            # lo compuesto era de otra versión: se rehace
    return {int(k): v for k, v in json.load(open(OUT, encoding='utf-8')).items()}


def _names(path, want):
    if not os.path.exists(path): return {}
    d = json.load(open(path, encoding='utf-8'))
    return {i: [d[str(i)][0], {int(z): xy for z, xy in d[str(i)][1].items()}] for i in want if str(i) in d}


def npcs(want):
    """{id: [nombre, {zona: [x, y]}]} de los PNJ pedidos."""
    return _names(OUT_NPC, set(want))


def objects(want):
    """{id: [nombre, {zona: [x, y]}]} de los objetos pedidos."""
    return _names(OUT_OBJ, set(want))


def version():
    """Versión descargada y nombres de zonas, categorías y profesiones por número."""
    return json.load(open(OUT_VER, encoding='utf-8')) if os.path.exists(OUT_VER) else {}


if __name__ == '__main__':
    args = sys.argv[1:]
    download('--refresh' in args)
    if '--why' in args:
        build(int(args[args.index('--why') + 1]))
    else:
        d = build()
        v = version()
        print(f'{len(d)} quests · con requisito {sum(1 for q in d.values() if q["preg"] or q["pres"])} · '
              f'para enano {sum(1 for q in d.values() if q["dwarf"])} · de clase {sum(1 for q in d.values() if q["cls"])} · '
              f'ocultas {sum(1 for q in d.values() if q["hid"])}')
        print('QuestieDB', v.get('db', {}).get('sha', '?')[:8], v.get('db', {}).get('date', ''), '· Questie', v.get('addon', {}).get('sha', '?')[:8])
        bad = check()
        print('comprobación:', 'todas las capas leídas enteras y los valores de referencia coinciden' if not bad else f'{len(bad)} fallos')
        for b in bad: print('  ', b)
        if bad: sys.exit(1)
