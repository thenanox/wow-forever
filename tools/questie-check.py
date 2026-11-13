"""Compara, campo a campo, lo que compone tools/questie.py con lo que compone el propio código de QuestieDB.

La otra mitad es tools/questie-oracle.lua, que ejecuta el código del repositorio de Questie: por eso es un paso
aparte y voluntario. Con un clon de Questie/QuestieDB en la misma versión que cache/questie/version.json:

  cd <clon> && luajit <guía>/tools/questie-oracle.lua <salida> Alliance SHAMAN
  python3 tools/questie-check.py <salida> [<clon>]
"""
import sys, os, json, copy, collections, subprocess

odir = sys.argv[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import questie as q

if len(sys.argv) > 2:                                        # las dos mitades tienen que salir de la misma versión
    head = subprocess.run(['git', '-C', sys.argv[2], 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    mine = (q.version().get('db') or {}).get('sha')
    print('versión de QuestieDB:', 'la misma en el clon y en la caché' if head == mine else f'DISTINTA: clon {head[:8]}, caché {str(mine)[:8]}')


def canon(v):
    """JSON del oráculo -> misma forma que el lector: claves numéricas como enteros."""
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            try: k2 = int(k)
            except ValueError:
                try: k2 = float(k)
                except ValueError: k2 = k
            out[k2] = canon(x)
        return out
    return v


def eq(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(eq(a[k], b[k]) for k in a)
    if isinstance(a, bool) or isinstance(b, bool): return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)): return abs(a - b) < 1e-9
    return a == b


def load(name):
    return canon(json.load(open(os.path.join(odir, name), encoding='utf-8', errors='replace')))


def compare(title, mine, theirs, names, skip=()):
    ids_m, ids_t = set(mine), set(theirs)
    only_m, only_t = sorted(ids_m - ids_t), sorted(ids_t - ids_m)
    diff, ex, cells = collections.Counter(), collections.defaultdict(list), 0
    for i in ids_m & ids_t:
        a, b = mine[i], theirs[i]
        for f in set(a) | set(b):
            if f in skip: continue
            cells += 1
            if not eq(a.get(f), b.get(f)):
                diff[f] += 1
                if len(ex[f]) < 4: ex[f].append((i, a.get(f), b.get(f)))
    bad = sum(diff.values())
    print(f'{title}: {len(ids_m & ids_t)} filas comunes · {cells} campos comparados · distintos {bad} · '
          f'solo en la guía {len(only_m)} · solo en Questie {len(only_t)}')
    if only_m: print('    solo en la guía:', only_m[:12])
    if only_t: print('    solo en Questie:', only_t[:12])
    for f, n in diff.most_common():
        print(f'    campo {names.get(f, f)}: {n}')
        for i, a, b in ex[f]:
            print(f'       {i}: guía {json.dumps(a, ensure_ascii=False)[:140]}')
            print(f'       {" " * len(str(i))}  Questie {json.dumps(b, ensure_ascii=False)[:140]}')
    return bad + len(only_m) + len(only_t)


E = q.enums()
keys, shapes = {}, {}
for kind in q.META: keys[kind], shapes[kind] = q.meta(kind)
env = q.make_env(E, keys)
total = 0


def static(kind):
    rows = q.base_rows(kind, keys[kind])
    raw = copy.deepcopy(rows)
    for name, func in q.STATIC[kind]:
        q.merge(rows, q.provider(name, func, env), shapes[kind], name, None)
    return raw, rows


qn = {v: k for k, v in keys['Quest'].items()}
nn = {v: k for k, v in keys['Npc'].items()}
on = {v: k for k, v in keys['Object'].items()}

raw, quests = static('Quest')
total += compare('quests, datos en bruto', raw, load('quest-raw.json'), qn)
total += compare('quests, con las capas estáticas', quests, load('quest-static.json'), qn)

_, npcs = static('Npc')
total += compare('PNJ, con las capas estáticas', npcs, load('npc-static.json'), nn, skip={keys['Npc']['waypoints']})
_, objects = static('Object')
total += compare('objetos, con las capas estáticas', objects, load('object-static.json'), on, skip={keys['Object'].get('waypoints')})

q.derive_races(quests, npcs, keys['Quest'], keys['Npc'], E['raceKeys'])
total += compare('quests, tras el pase de razas', quests, load('quest-derived.json'), qn)

q.compose(quests, [(name, q.provider(name, func, env)) for name, func in q.DYNAMIC['Quest']], shapes['Quest'], None)
total += compare('quests, con las correcciones del personaje (resultado final)', quests, load('quest-final.json'), qn)

print('capas dinámicas que aplicó Questie:', json.load(open(os.path.join(odir, 'dynamic-entries.json'))))
print('capas estáticas que aplicó Questie:', [(e['name'], e['order']) for e in canon(json.load(open(os.path.join(odir, 'static-entries.json')))).values()])
print('\nRESULTADO:', 'idéntico' if not total else f'{total} diferencias')
sys.exit(1 if total else 0)
