#!/usr/bin/env python3
"""Los datos descargados de Warcraft DB viajan con el repositorio, en data/db/.

Warcraft DB no tiene versiones: lo que se bajó un día puede no poder bajarse igual otro. Por eso la copia va al
repositorio. La caché de trabajo (cache/) son miles de archivos pequeños y no se sube; aquí se empaqueta en un
archivo por tipo, con una línea por ficha y siempre en el mismo orden, para que git guarde solo lo que cambia:

  data/db/quest.jsonl    fichas de quest        (cache/quest/)
  data/db/list.jsonl     listados por zona      (cache/list/)
  data/db/item.jsonl     fichas de objeto       (cache/item/)
  data/db/search.jsonl   búsquedas por nombre   (cache/search/)

  python3 tools/datos.py            empaqueta cache/ en data/db/
  python3 tools/datos.py --restore  rehace cache/ a partir de data/db/

No hace falta llamarlo a mano: crawl.py y build.py rehacen la caché al empezar si data/db/ ha cambiado
(por ejemplo, tras un git pull) y la empaquetan al terminar una descarga.
Las fichas que fallaron al descargarse no se empaquetan: así se vuelven a pedir en el siguiente equipo.
"""
import os, re, sys, json, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'cache')
DB = os.path.join(ROOT, 'data', 'db')
KINDS = ('quest', 'list', 'item', 'search')
STAMP = os.path.join(CACHE, '.db-stamp')
SAFE = re.compile(r'[A-Za-z0-9._-]+\Z')


def _order(k):
    return (0, int(k), '') if k.isdigit() else (1, 0, k)


def _stamp():
    """Huella de data/db/: cambia cuando cambia cualquiera de sus archivos."""
    h = hashlib.sha1()
    for kind in KINDS:
        p = os.path.join(DB, kind + '.jsonl')
        if os.path.exists(p):
            h.update(kind.encode()); h.update(open(p, 'rb').read())
    return h.hexdigest()


def pack():
    """cache/ -> data/db/. Devuelve cuántas fichas hay empaquetadas."""
    os.makedirs(DB, exist_ok=True)
    total = 0
    for kind in KINDS:
        d = os.path.join(CACHE, kind)
        if not os.path.isdir(d): continue
        lines = []
        for k in sorted((f[:-5] for f in os.listdir(d) if f.endswith('.json')), key=_order):
            v = json.load(open(os.path.join(d, k + '.json'), encoding='utf-8'))
            if isinstance(v, dict) and 'err' in v: continue
            lines.append(json.dumps({'k': k, 'v': v}, ensure_ascii=False, separators=(',', ':')))
        text = ''.join(l + '\n' for l in lines)
        p = os.path.join(DB, kind + '.jsonl')
        if not os.path.exists(p) or open(p, encoding='utf-8').read() != text:
            open(p, 'w', encoding='utf-8').write(text)
        total += len(lines)
    if os.path.isdir(CACHE): open(STAMP, 'w').write(_stamp())
    return total


def restore(force=False):
    """data/db/ -> cache/, si data/db/ ha cambiado desde la última vez. Escribe lo que falte o sea distinto y no borra
    nada: lo que solo esté en la caché se queda, y se empaquetará después. Devuelve cuántas fichas ha escrito."""
    if not os.path.isdir(DB): return 0
    stamp = _stamp()
    if not force and os.path.exists(STAMP) and open(STAMP).read() == stamp: return 0
    made = 0
    for kind in KINDS:
        p = os.path.join(DB, kind + '.jsonl')
        if not os.path.exists(p): continue
        d = os.path.join(CACHE, kind)
        os.makedirs(d, exist_ok=True)
        for line in open(p, encoding='utf-8'):
            rec = json.loads(line)
            if not SAFE.match(rec['k']): continue
            f = os.path.join(d, rec['k'] + '.json')
            if os.path.exists(f):
                try:
                    if json.load(open(f, encoding='utf-8')) == rec['v']: continue
                except ValueError: pass
            json.dump(rec['v'], open(f, 'w', encoding='utf-8'), ensure_ascii=False)
            made += 1
    open(STAMP, 'w').write(stamp)
    return made


if __name__ == '__main__':
    if '--restore' in sys.argv:
        print('fichas escritas en cache/:', restore(force=True))
    else:
        n = pack()
        size = sum(os.path.getsize(os.path.join(DB, f)) for f in os.listdir(DB))
        print(f'{n} fichas en data/db/ · {size // 1024} KB')
