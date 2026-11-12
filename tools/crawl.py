#!/usr/bin/env python3
"""Descarga de forever.warcraftdb.com los listados de quests por zona y la ficha de cada quest.
Todo queda en cache/ y no se vuelve a pedir. Uso: python3 tools/crawl.py [--lists-only]"""
import sys, os, re, json, time, html, threading, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'cache')
HOST = 'https://forever.warcraftdb.com'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'

PRESETS = """
eastern-kingdoms/coldridge-valley eastern-kingdoms/anvilmar eastern-kingdoms/kharanos eastern-kingdoms/dun-morogh
eastern-kingdoms/ironforge eastern-kingdoms/loch-modan eastern-kingdoms/stonewrought-dam eastern-kingdoms/elwynn-forest
eastern-kingdoms/northshire-valley eastern-kingdoms/stormwind-city eastern-kingdoms/westfall eastern-kingdoms/redridge-mountains
eastern-kingdoms/duskwood eastern-kingdoms/wetlands eastern-kingdoms/hillsbrad-foothills eastern-kingdoms/thoradins-wall
eastern-kingdoms/alterac-mountains eastern-kingdoms/dalaran eastern-kingdoms/arathi-highlands eastern-kingdoms/stranglethorn-vale
eastern-kingdoms/booty-bay eastern-kingdoms/gurubashi-arena eastern-kingdoms/badlands eastern-kingdoms/swamp-of-sorrows
eastern-kingdoms/riverglades eastern-kingdoms/the-hinterlands eastern-kingdoms/aerie-peak eastern-kingdoms/searing-gorge
eastern-kingdoms/blasted-lands eastern-kingdoms/burning-steppes eastern-kingdoms/blackrock-mountain
eastern-kingdoms/western-plaguelands eastern-kingdoms/eastern-plaguelands eastern-kingdoms/deadwind-pass
eastern-kingdoms/gnomeregan eastern-kingdoms/uldaman eastern-kingdoms/shadowfang-keep eastern-kingdoms/the-temple-of-atalhakkar
eastern-kingdoms/blackrock-depths eastern-kingdoms/blackrock-spire eastern-kingdoms/crafting
kalimdor/darkshore kalimdor/auberdine kalimdor/ashenvale kalimdor/stonetalon-mountains kalimdor/the-barrens kalimdor/ratchet
kalimdor/thousand-needles kalimdor/the-shimmering-flats kalimdor/desolace kalimdor/dustwallow-marsh kalimdor/alcaz-island
kalimdor/feralas kalimdor/feathermoon-stronghold kalimdor/tanaris kalimdor/gadgetzan kalimdor/ungoro-crater kalimdor/felwood
kalimdor/azshara kalimdor/winterspring kalimdor/silithus kalimdor/moonglade kalimdor/nighthaven kalimdor/mount-hyjal
kalimdor/shendralas kalimdor/teldrassil kalimdor/darnassus kalimdor/timbermaw-hold kalimdor/elderwild kalimdor/lands-end-beach
kalimdor/south-seas kalimdor/razorfen-kraul kalimdor/zulfarrak kalimdor/blackmaw-hold kalimdor/the-shapers-terrace kalimdor/the-maul
deeprun-tram/deeprun-tram dungeons class/shaman profession/engineering profession/cooking profession/first-aid profession/fishing
""".split()

lock = threading.Lock()

def get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            if k == tries - 1: raise
            time.sleep(1.5 * (k + 1))

def fetch_list(preset):
    path = os.path.join(CACHE, 'list', preset.replace('/', '__') + '.json')
    if os.path.exists(path): return json.load(open(path))
    rows, page = [], 1
    while True:
        d = get(f"{HOST}/api/data/list/quests?page={page}&per_page=100&preset={urllib.parse.quote(preset, safe='')}")
        rows += [{'id': r['record_id'], 'name': r['name'], 'min': (r.get('required_level') or {}).get('min'),
                  'zone': r.get('zone'), 'type': r.get('quest_type')} for r in d.get('rows', [])]
        if page >= (d.get('pages') or 1): break
        page += 1; time.sleep(0.25)
    json.dump(rows, open(path, 'w'), ensure_ascii=False)
    return rows

LINK = re.compile(r'<a href="/data/(npc|object|item)/(\d+)"[^>]*>(.*?)</a>', re.S)
def links(s):
    return [{'t': t, 'id': int(i), 'name': html.unescape(re.sub(r'<[^>]+>', '', n)).strip()} for t, i, n in LINK.findall(s or '')]

def compact(qid, d):
    x = d.get('data') or {}
    qm = (d.get('extra') or {}).get('quest_map') or {}
    floors = {f['id']: f['name'] for f in qm.get('floors', [])}
    def pt(lst):
        if not lst: return None
        p = lst[0]
        return [round(p['u'] * 100, 1), round(p['v'] * 100, 1), floors.get(p.get('ui_map_id'))]
    rw = x.get('rewards') or {}
    def it(lst): return [{'id': i.get('id'), 'name': i.get('name'), 'color': i.get('color'), 'n': i.get('amount') or i.get('quantity')} for i in (lst or [])]
    st = x.get('storyline') or {}
    return {
        'id': qid, 'name': x.get('name'), 'zone': x.get('zone'), 'zone_id': x.get('zone_id'), 'level': x.get('level'),
        'min': x.get('min_level'), 'side': x.get('side'), 'type': x.get('quest_type'), 'group': x.get('suggested_group'),
        'timer': x.get('time_limit'), 'tags': x.get('tags'), 'starts': links(x.get('starts')), 'ends': links(x.get('ends')),
        'sc': pt(qm.get('starts')), 'ec': pt(qm.get('turn_ins')), 'obj': x.get('log_description'),
        'objectives': [{'d': o.get('description'), 'n': o.get('amount')} for o in (x.get('objectives') or [])],
        'xp': rw.get('xp'), 'money': rw.get('money'), 'items': it(rw.get('items')), 'choice': it(rw.get('choice_items')),
        'rep': [{'name': r.get('name'), 'v': r.get('value')} for r in (rw.get('reputation') or [])],
        'provided': ({'id': x['provided_item'].get('id'), 'name': x['provided_item'].get('name')} if x.get('provided_item') else None),
        'chain': st.get('name'), 'chain_ids': [q['id'] for q in (st.get('quests') or [])],
    }

done = [0]
def fetch_quest(qid):
    path = os.path.join(CACHE, 'quest', f'{qid}.json')
    if os.path.exists(path): return
    try:
        rec = compact(qid, get(f'{HOST}/api/data/node/quest/{qid}'))
    except Exception as e:
        rec = {'id': qid, 'err': str(e)[:120]}
    json.dump(rec, open(path, 'w'), ensure_ascii=False)
    time.sleep(0.35)
    with lock:
        done[0] += 1
        if done[0] % 200 == 0: print('  quests', done[0], flush=True)

def main():
    ids, per = {}, {}
    for p in PRESETS:
        try: rows = fetch_list(p)
        except Exception as e: print('LIST FAIL', p, e, flush=True); continue
        per[p] = len(rows)
        for r in rows: ids.setdefault(r['id'], r)
    print('listas:', len(per), 'quests únicas:', len(ids), flush=True)
    print('  ' + ', '.join(f"{k.split('/')[-1]}={v}" for k, v in per.items()), flush=True)
    extra = os.path.join(ROOT, 'data', 'extra-quest-ids.json')
    if os.path.exists(extra):
        for q in json.load(open(extra)): ids.setdefault(int(q), {'id': int(q)})
    if '--lists-only' in sys.argv: return
    todo = [q for q in ids if not os.path.exists(os.path.join(CACHE, 'quest', f'{q}.json'))]
    print('por descargar:', len(todo), flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex: list(ex.map(fetch_quest, todo))
    print('FIN', flush=True)

if __name__ == '__main__': main()
