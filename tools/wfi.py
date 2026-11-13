#!/usr/bin/env python3
"""Guías paso a paso de wowforeverinfo.com. De ellas salen dos cosas de los listados de zona:
la ★ de las quests que la guía nombra y qué quests son de la Horda en las zonas compartidas.

  python3 tools/wfi.py            descarga las guías que falten a cache/wfi/ y regenera data/wfi-quests.json
  python3 tools/wfi.py --refresh  vuelve a descargarlas todas

El texto de las guías se queda en cache/ (no va al repositorio: es de sus autores). Al repositorio va solo
data/wfi-quests.json: por guía, los nombres de quest que aparecen en los apartados de la Alianza o comunes («a»)
y los que solo aparecen en los de la Horda («h»). Con eso basta para generar la guía sin conexión.
"""
import os, re, sys, json, glob, html, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'cache', 'wfi')
OUT = os.path.join(ROOT, 'data', 'wfi-quests.json')
HOST = 'https://wowforeverinfo.com/guides/'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'

# guías de zona que usa la guía (tools/build.py: ZONES, EXTRA_ZONES) y las de las zonas de la Horda, para sus descripciones
SLUGS = """
dun-morogh-1-12 loch-modan-10-20 westfall-10-20 redridge-mountains-15-25 darkshore-10-20 duskwood-18-30 wetlands-20-30
ashenvale-alliance-18-30 hillsbrad-foothills-alliance-28-35 arathi-highlands-30-40 alterac-mountains-30-40
stranglethorn-vale-30-45 desolace-30-40 riverglades-35-45 dustwallow-marsh-35-45 badlands-35-45 swamp-of-sorrows-35-45
feralas-40-50 tanaris-40-50 the-hinterlands-40-50 searing-gorge-43-50 un-goro-crater-48-55 felwood-48-55 azshara-45-55
blasted-lands-45-55 western-plaguelands-51-58 eastern-plaguelands-53-60 burning-steppes-50-58 winterspring-54-60
silithus-55-60 elwynn-forest-1-10 teldrassil-1-12
tirisfal-glades-1-12 silverpine-forest-10-20 durotar-1-12 mulgore-1-12 the-barrens-10-20
stonetalon-mountains-horde-15-27 thousand-needles-horde-25-35
""".split()


def fetch(slug):
    req = urllib.request.Request(HOST + slug + '/', headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')


def to_text(page):
    """El cuerpo de la guía en texto, con una línea «## Título» por apartado."""
    m = re.search(r'<main\b.*?</main>', page, re.S)
    b = m.group(0) if m else page
    h1 = re.search(r'</h1>', b)
    if h1: b = b[h1.end():]
    b = re.sub(r'<(script|style|svg|nav)\b.*?</\1>', '', b, flags=re.S)
    b = re.sub(r'<h2[^>]*>(.*?)</h2>', lambda m: '\n## ' + re.sub(r'<[^>]+>', '', m.group(1)).strip() + '\n', b, flags=re.S)
    b = re.sub(r'<h3[^>]*>(.*?)</h3>', lambda m: '\n### ' + re.sub(r'<[^>]+>', '', m.group(1)).strip() + '\n', b, flags=re.S)
    b = re.sub(r'</(p|li|tr|div|summary|label)>|<br\s*/?>', '\n', b)
    t = html.unescape(re.sub(r'<[^>]+>', '', b)).replace('’', "'").replace('‘', "'").replace('⁠', '')
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    return re.sub(r'\n\s*\n+', '\n', t).strip() + '\n'


def sections(text):
    """(texto de los apartados de la Alianza o comunes, texto de los de la Horda)"""
    ally, horde, cur = [], [], 'a'
    for line in text.splitlines(True):
        if line.startswith('## '):
            cur = 'h' if re.match(r'## \s*Horde', line) else 'a'
        (horde if cur == 'h' else ally).append(line)
    return ''.join(ally), ''.join(horde)


def quest_names():
    names = set()
    for p in glob.glob(os.path.join(ROOT, 'cache', 'quest', '*.json')):
        n = json.load(open(p, encoding='utf-8')).get('name')
        if n: names.add(n)
    return names


def main():
    os.makedirs(DIR, exist_ok=True)
    refresh = '--refresh' in sys.argv
    for s in SLUGS:
        p = os.path.join(DIR, s + '.txt')
        if os.path.exists(p) and not refresh: continue
        try:
            t = to_text(fetch(s))
        except Exception as e:
            print('FALLA', s, str(e)[:100]); continue
        if '## ' not in t:
            print('SIN APARTADOS', s); continue
        open(p, 'w', encoding='utf-8').write(t)
        time.sleep(0.4)
    names = quest_names()
    if not names:
        sys.exit('No hay quests en cache/quest: ejecuta antes tools/crawl.py')
    out = {}
    for s in SLUGS:
        p = os.path.join(DIR, s + '.txt')
        if not os.path.exists(p): continue
        ally, horde = sections(open(p, encoding='utf-8').read())
        a = sorted(n for n in names if n in ally)
        h = sorted(n for n in names if n in horde and n not in ally)
        out[s] = {'a': a, 'h': h}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    print(f'guías {len(out)} de {len(SLUGS)} · quests nombradas {sum(len(v["a"]) for v in out.values())} · solo de la Horda {sum(len(v["h"]) for v in out.values())}')


if __name__ == '__main__':
    main()
