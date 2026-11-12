#!/usr/bin/env python3
"""Genera index.html (guía navegable) y print.html (versión para PDF).

  python3 tools/build.py            usa la caché y consulta lo que falte
  python3 tools/build.py --offline  solo caché
"""
import os, re, sys, json, html, glob, urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gamedata as G

ROOT = G.ROOT
G.OFFLINE = '--offline' in sys.argv
esc = lambda s: html.escape(str(s), quote=True)
WH = 'https://www.wowhead.com/forever/'

Q = G.load_quests()
NAMES = G.Names(Q)
USED_Q, USED_I, USED_N = set(), {}, {}

# ---------------------------------------------------------------- metadatos
# (clave de grupo, nombre, zona en la base de datos, nueva, dónde, guía WT, quests WT, guía wfi, alas)
# ala = (clave, etiqueta, nivel mín., nivel máx., logro de Legacy)
DG = [
 ('hall-of-thanes', 'Hall of Thanes', 'The Hall of Thanes', True, 'Bajo Ironforge', 'hall-of-thanes', ['hall-of-thanes'], 'hall-of-thanes', [('hall-of-thanes', '', 13, 20, 'N')]),
 ('ragefire-chasm', 'Ragefire Chasm', 'Ragefire Chasm', False, 'Orgrimmar (Horda)', 'ragefire-chasm', [], 'ragefire-chasm', [('ragefire-chasm', '', 13, 18, 'N')]),
 ('ruins-of-lordaeron', 'Ruins of Lordaeron', 'Ruins of Lordaeron', True, 'Tirisfal Glades (Horda)', 'the-ruins-of-lordaeron', ['the-ruins-of-lordaeron'], 'ruins-of-lordaeron', [('ruins-of-lordaeron', '', 15, 22, 'N')]),
 ('wailing-caverns', 'Wailing Caverns', 'Wailing Caverns', False, 'The Barrens', 'wailing-caverns', ['wailing-caverns'], 'wailing-caverns', [('wailing-caverns', '', 15, 24, 'N')]),
 ('deadmines', 'The Deadmines', 'The Deadmines', False, 'Moonbrook, Westfall', 'the-deadmines', ['the-deadmines'], 'deadmines', [('deadmines', '', 17, 26, 'N')]),
 ('shadowfang-keep', 'Shadowfang Keep', 'Shadowfang Keep', False, 'Silverpine Forest (Horda)', 'shadowfang-keep', [], 'shadowfang-keep', [('shadowfang-keep', '', 20, 30, 'N')]),
 ('blackfathom-deeps', 'Blackfathom Deeps', 'Blackfathom Deeps', False, 'Zoram Strand, Ashenvale', 'blackfathom-deeps', ['blackfathom-deeps'], 'blackfathom-deeps', [('blackfathom-deeps', '', 24, 32, 'E')]),
 ('stockade', 'The Stockade', 'The Stockade', False, 'Stormwind', 'the-stockade-dungeon-map-location-bosses', ['the-stockade'], 'stockade', [('stockade', '', 25, 29, '')]),
 ('excavation-site', 'Excavation Site: Wetlands', 'Excavation Site: Wetlands', True, 'Wetlands', 'excavation-site-wetlands', ['excavation-site-wetlands'], 'excavation-site', [('excavation-site', '', 26, 33, 'N')]),
 ('city-of-dalaran', 'City of Dalaran', 'City of Dalaran', True, 'Alterac Mountains', 'city-of-dalaran', ['city-of-dalaran'], None, [('city-of-dalaran', '', 28, 35, 'E')]),
 ('razorfen-kraul', 'Razorfen Kraul', 'Razorfen Kraul', False, 'Sur de The Barrens', 'razorfen-kraul', ['razorfen-kraul'], 'razorfen-kraul', [('razorfen-kraul', '', 29, 38, 'E')]),
 ('gnomeregan', 'Gnomeregan', 'Gnomeregan', False, 'Dun Morogh', 'gnomeregan', ['gnomeregan'], 'gnomeregan', [('gnomeregan', '', 29, 38, 'E')]),
 ('scarlet-monastery', 'Scarlet Monastery', 'Scarlet Monastery', False, 'Tirisfal Glades (Horda)', 'scarlet-monastery', ['scarlet-monastery'], 'scarlet-monastery',
  [('sm-graveyard', 'Graveyard', 30, 38, 'E'), ('sm-library', 'Library', 33, 41, 'E'), ('sm-armory', 'Armory', 36, 44, 'E'), ('sm-cathedral', 'Cathedral', 38, 46, 'E')]),
 ('drowned-city', 'The Drowned City', 'The Drowned City', True, 'Frente a Stranglethorn Vale, bajo el agua', 'the-drowned-city', [], None, [('drowned-city', '', 35, 42, 'E')]),
 ('razorfen-downs', 'Razorfen Downs', 'Razorfen Downs', False, 'Sur de The Barrens', 'razorfen-downs', ['razorfen-downs'], 'razorfen-downs', [('razorfen-downs', '', 37, 46, 'M')]),
 ('kroldok-stronghold', "Krol'dok Stronghold", "Krol'dok Stronghold", True, 'Riverglades', 'kroldok-stronghold', [], None, [('kroldok-stronghold', '', 40, 45, 'E')]),
 ('uldaman', 'Uldaman', 'Uldaman', False, 'Badlands', 'uldaman', ['uldaman'], 'uldaman', [('uldaman', '', 41, 51, 'M')]),
 ('zulfarrak', "Zul'Farrak", "Zul'Farrak", False, 'Tanaris', 'zulfarrak', ['zulfarrak'], None, [('zulfarrak', '', 44, 54, 'M')]),
 ('maraudon', 'Maraudon', 'Maraudon', False, 'Desolace', 'maraudon', ['maraudon'], None, [('maraudon', '', 46, 55, 'M')]),
 ('alcaz-prison', 'Alcaz Prison', 'Alcaz Prison', True, 'Isla de Alcaz, Dustwallow Marsh', 'alcaz-island-prison', [], None, [('alcaz-prison', '', 48, 55, 'M')]),
 ('sunken-temple', 'Sunken Temple', 'Sunken Temple', False, 'Swamp of Sorrows', 'sunken-temple', ['sunken-temple'], None, [('sunken-temple', '', 50, 60, 'M')]),
 ('blackrock-depths', 'Blackrock Depths', 'Blackrock Depths', False, 'Blackrock Mountain', 'blackrock-depths', ['blackrock-depths'], None, [('blackrock-depths', '', 52, 60, 'M')]),
 ('dire-maul', 'Dire Maul', 'Dire Maul', False, 'Feralas', 'dire-maul', ['dire-maul-east', 'dire-maul-west', 'dire-maul-north'], None,
  [('dire-maul-east', 'East', 54, 60, 'M'), ('dire-maul-west', 'West', 56, 60, 'M'), ('dire-maul-north', 'North', 56, 60, 'M')]),
 ('blackrock-spire', 'Blackrock Spire', 'Blackrock Spire', False, 'Blackrock Mountain', 'blackrock-spire', ['lower-blackrock-spire', 'upper-blackrock-spire'], None,
  [('lbrs', 'Lower (LBRS)', 55, 60, 'M'), ('ubrs', 'Upper (UBRS)', 59, 60, 'M')]),
 ('blackmaw-hold', 'Blackmaw Hold', 'Blackmaw Hold', True, 'Azshara', 'blackmaw-hold', [], None, [('blackmaw-hold', '', 55, 60, 'M')]),
 ('stratholme', 'Stratholme', 'Stratholme', False, 'Eastern Plaguelands', 'stratholme', ['stratholme-living', 'stratholme-undead'], None,
  [('stratholme-live', 'Live (puerta principal)', 58, 60, 'M'), ('stratholme-dead', 'Dead (puerta de servicio)', 58, 60, 'M')]),
 ('scholomance', 'Scholomance', 'Scholomance', False, 'Caer Darrow, Western Plaguelands', 'scholomance', ['scholomance'], None, [('scholomance', '', 58, 60, 'M')]),
 ('shapers-terrace', "Shaper's Terrace", "The Shaper's Terrace", True, "Un'Goro Crater", 'shapers-terrace', [], None, [('shapers-terrace', '', 58, 60, 'M')]),
]
TIER = {'N': 'Novice Spelunker', 'E': 'Experienced Spelunker', 'M': 'Master Spelunker', '': ''}

# nombre de la zona en la guía -> (zonas en la base de datos, guía paso a paso de wowforeverinfo)
ZONES = {
 'Dun Morogh': (['Dun Morogh', 'Coldridge Valley', 'Kharanos', 'Anvilmar'], 'dun-morogh-1-12'),
 'Loch Modan': (['Loch Modan', 'Stonewrought Dam'], 'loch-modan-10-20'),
 'Westfall': (['Westfall'], 'westfall-10-20'),
 'Redridge Mountains': (['Redridge Mountains'], 'redridge-mountains-15-25'),
 'Darkshore': (['Darkshore', 'Auberdine'], 'darkshore-10-20'),
 'Duskwood': (['Duskwood'], 'duskwood-18-30'),
 'Wetlands': (['Wetlands'], 'wetlands-20-30'),
 'Ashenvale': (['Ashenvale'], 'ashenvale-alliance-18-30'),
 'Hillsbrad Foothills': (['Hillsbrad Foothills', "Thoradin's Wall"], 'hillsbrad-foothills-alliance-28-35'),
 'Arathi Highlands': (['Arathi Highlands'], 'arathi-highlands-30-40'),
 'Alterac Mountains': (['Alterac Mountains', 'Dalaran'], 'alterac-mountains-30-40'),
 'Stranglethorn Vale': (['Stranglethorn Vale', 'Booty Bay', 'Gurubashi Arena'], 'stranglethorn-vale-30-45'),
 'Desolace': (['Desolace'], 'desolace-30-40'),
 'The Riverglades': (['Riverglades'], 'riverglades-35-45'),
 'Dustwallow Marsh': (['Dustwallow Marsh', 'Alcaz Island'], 'dustwallow-marsh-35-45'),
 'Badlands': (['Badlands'], 'badlands-35-45'),
 'Swamp of Sorrows': (['Swamp of Sorrows'], 'swamp-of-sorrows-35-45'),
 'Feralas': (['Feralas', 'Feathermoon Stronghold'], 'feralas-40-50'),
 'Tanaris': (['Tanaris', 'Gadgetzan'], 'tanaris-40-50'),
 'The Hinterlands': (['The Hinterlands', 'Aerie Peak'], 'the-hinterlands-40-50'),
 'Searing Gorge': (['Searing Gorge'], 'searing-gorge-43-50'),
 "Un'Goro Crater": (["Un'Goro Crater"], 'un-goro-crater-48-55'),
 'Felwood': (['Felwood', 'Timbermaw Hold'], 'felwood-48-55'),
 'Azshara': (['Azshara'], 'azshara-45-55'),
 'Blasted Lands': (['Blasted Lands'], 'blasted-lands-45-55'),
 'Western Plaguelands': (['Western Plaguelands'], 'western-plaguelands-51-58'),
 'Eastern Plaguelands': (['Eastern Plaguelands'], 'eastern-plaguelands-53-60'),
 'Burning Steppes': (['Burning Steppes', 'Blackrock Mountain'], 'burning-steppes-50-58'),
 'Winterspring': (['Winterspring'], 'winterspring-54-60'),
 'Silithus': (['Silithus'], 'silithus-55-60'),
 'Mount Hyjal': (['Mount Hyjal', 'Elderwild'], None),
}
# zonas sin apartado propio en la guía: se generan solo con el listado completo
EXTRA_ZONES = [
 ('Ironforge', 'ciudad', 'Tu capital', ['Ironforge'], None, 'Entrenadores de chamán y de armas, Tinker Town, Hall of Explorers y el Deeprun Tram a Stormwind.'),
 ('Stormwind City', 'ciudad', 'Capital humana', ['Stormwind City', 'Deeprun Tram'], None, 'Quests de Deadmines, Stockade y Dalaran, y el barco nuevo a Auberdine.'),
 ('Elwynn Forest', '1-10', 'base: Goldshire', ['Elwynn Forest', 'Northshire Valley'], 'elwynn-forest-1-10', 'Zona inicial humana. Gris a partir de nivel 15: solo por completar y explorar.'),
 ('Teldrassil y Darnassus', '1-12', 'base: Dolanaar', ['Teldrassil', 'Darnassus'], 'teldrassil-1-12', 'Zona inicial élfica. En Darnassus se cogen quests de Blackfathom Deeps y Blackmaw Hold.'),
 ('The Barrens', '10-25', 'base: Ratchet (neutral)', ['The Barrens', 'Ratchet'], None, 'Zona de la Horda con Ratchet como puerto neutral. Aquí están Wailing Caverns, Razorfen Kraul y Razorfen Downs.'),
 ('Stonetalon Mountains', '15-27', 'base: Stonetalon Peak', ['Stonetalon Mountains'], None, 'Paso entre Ashenvale y Desolace. Un tramo de la bolsa de dormir.'),
 ('Thousand Needles', '25-35', 'base: Shimmering Flats (neutral)', ['Thousand Needles', 'The Shimmering Flats'], None, 'Aquí termina Heed My Call, de tu cadena del arma, y empieza la quest de Razorfen Kraul del diario de Lonebrow.'),
 ("Shen'dralas", '40-55', 'compartida', ["Shen'dralas"], None, 'Zona nueva al sur de Desolace, por el Valley of Bones. Centauros y quests de Dire Maul, Maraudon y Razorfen Downs.'),
 ('Moonglade', '—', 'base: Nighthaven (neutral)', ['Moonglade', 'Nighthaven'], None, 'Refugio druida neutral. Quests de Dire Maul y de Silithus.'),
 ('Deadwind Pass', '55+', 'sin base', ['Deadwind Pass'], None, 'Paso entre Duskwood y Swamp of Sorrows, con Karazhan.'),
]

MILESTONES = [
 (4, 'Totem de Tierra (Call of Earth) y Earth Shock'), (6, 'Earthbind Totem. Cocina con Camping 101'), (8, 'Lightning Shield y Stoneclaw Totem'),
 (10, 'Totem de Fuego (Call of Fire), Flame Shock, primer talento y Oficial en profesiones'), (12, 'Fire Nova, Purge y Ancestral Spirit'),
 (13, 'Primera mazmorra: Hall of Thanes'), (14, 'Empieza la cadena de la Cozy Sleeping Bag'), (16, 'Cure Poison'), (18, 'Tremor Totem'),
 (20, 'Totem de Agua (Call of Water), Ghost Wolf, Frost Shock, Call of the Elements y Experto en profesiones'),
 (22, 'Cure Disease, Poison Cleansing Totem y Totemic Projection'), (25, 'Stormstrike (talento) y primer punto de Legacy'),
 (26, 'Magma Totem, Mana Spring Totem e Improved Ghost Wolf'), (28, 'Flametongue Totem'),
 (30, 'Totem de Aire (Call of Air), Windfury Weapon, Reincarnation y especialización de Ingeniería (con 200)'),
 (32, 'Windfury Totem y Chain Lightning'), (35, 'Artesano en profesiones y Maelstrom Weapon (35-39)'),
 (40, 'Montura, doble especialización, malla, Rage of the Farseer y Chain Heal'), (48, 'Las quests empiezan a dar oro extra'),
 (50, 'Quest de clase: Elemental Mastery → Da Voodoo'), (55, 'Attunement to the Core'), (60, 'Mount Hyjal y raids'),
]
PROF = [  # hasta nivel, minería, ingeniería
 (10, 'Minería 1-65: cobre', 'Ingeniería 1-75'), (20, 'Minería 65-125: estaño y bronce', 'Ingeniería 75-150 (Oficial desde nivel 10)'),
 (30, 'Minería 125-175: hierro (Experto desde nivel 20)', 'Ingeniería 150-200'),
 (40, 'Minería 175-230: mitril', 'Ingeniería 200-250: especialización y Artesano a nivel 35 en Gadgetzan'),
 (50, 'Minería 230-275: mitril, truesilver y Dark Iron', 'Ingeniería 250-285'), (60, 'Minería 275-300: torio', 'Ingeniería 285-300'),
]
CLASSIC_BASED = {'sunken-temple', 'blackrock-depths', 'dire-maul-east', 'dire-maul-west', 'dire-maul-north', 'lbrs', 'ubrs',
                 'stratholme-live', 'stratholme-dead', 'scholomance', 'zulfarrak', 'maraudon'}
NOT_ITEMS = ('Pechera Tier', 'Perneras Tier')
KIND = {'arma2m': 'dos manos', 'arma1m': 'una mano', 'escudo': 'escudo', 'armadura': 'armadura', 'reliquia': 'reliquia', 'abalorio': 'abalorio',
        'llave': 'llave', 'inicia-quest': 'inicia quest', 'plano': 'plano', 'profesion': 'profesión', 'otro': 'utilidad'}


# ---------------------------------------------------------------- enlaces
def A(t, i, inner, cls=''):
    return f'<a class="x x-{t}{cls}" data-t="{t}" data-id="{i}" href="{WH}{t}={i}" target="_blank" rel="noopener">{inner}</a>'

def AS(name, inner):
    return (f'<a class="x x-s" data-t="search" data-q="{esc(name)}" href="{WH}search?q={urllib.parse.quote(name)}" '
            f'target="_blank" rel="noopener">{inner}</a>')

def qa(qid, text=None):
    USED_Q.add(qid)
    return A('quest', qid, esc(text or Q[qid]['name']))

def ia(iid, name, inner=None):
    tip = G.item_tip(iid)
    if tip: USED_I[iid] = tip
    return A('item', iid, inner or esc(name), f' q{tip["q"]}' if tip else '')

def na(nid, name, inner=None):
    USED_N[nid] = name
    return A('npc', nid, inner or esc(name))

def item_link(name):
    iid = NAMES.search(name, 'item')
    return ia(iid, name) if iid else AS(name, esc(name))

def npc_link(name):
    nid = NAMES.search(name, 'npc')
    return na(nid, name) if nid else AS(name, esc(name))

def ref_link(ref, name, inner):
    t, i = ref
    if t == 'quest': USED_Q.add(i); return A('quest', i, inner)
    if t == 'item': return ia(i, name, inner)
    if t == 'npc': return na(i, name, inner)
    return A(t, i, inner)


# ---------------------------------------------------------------- enlazado automático del texto
TAG = re.compile(r'<!--.*?-->|<(/?)([a-zA-Z0-9]+)((?:[^>"\']|"[^"]*"|\'[^\']*\')*)>', re.S)
NOLINK = {'a', 'summary', 'h1', 'h2', 'h3', 'h4', 'nav', 'script', 'style', 'title', 'button', 'option', 'select', 'textarea', 'th'}
PLAIN = [l.strip() for l in open(os.path.join(ROOT, 'data', 'plain-names.txt'), encoding='utf-8') if l.strip()]
PLAIN_RE = re.compile(r"(?<![\w>'])(" + '|'.join(re.escape(html.escape(n, quote=False)) for n in sorted(PLAIN, key=len, reverse=True)) + r")(?![\w])")
SPANISH = re.compile(r'[áéíóúñ¿¡]')
STATS = {'linked': 0, 'search': 0}

def link_plain(text):
    def sub(m):
        name = html.unescape(m.group(1))
        ref = NAMES.any(name)
        if not ref:
            for want in ('npc', 'item'):
                i = NAMES.search(name, want)
                if i: ref = (want, i); break
        if not ref: return m.group(0)
        STATS['linked'] += 1
        return ref_link(ref, name, m.group(1))
    return PLAIN_RE.sub(sub, text)

def link_em(inner):
    name = html.unescape(re.sub(r'<[^>]+>', '', inner)).strip()
    if not name or len(name) > 70 or SPANISH.search(name) or not name[0].isupper() and name[0] not in '.…"':
        return f'<em>{inner}</em>'
    ref = NAMES.any(name)
    if ref:
        STATS['linked'] += 1
        return ref_link(ref, name, f'<em>{inner}</em>')
    if len(name) >= 5 and ' ' in name or name.endswith('!'):
        STATS['search'] += 1
        return AS(name, f'<em>{inner}</em>')
    return f'<em>{inner}</em>'

def linkify(body):
    out, pos, stack = [], 0, []
    while True:
        m = TAG.search(body, pos)
        if not m:
            rest = body[pos:]
            out.append(rest if stack else link_plain(rest)); break
        text = body[pos:m.start()]
        out.append(text if stack else link_plain(text))
        tag = m.group(0)
        name = (m.group(2) or '').lower()
        closing = m.group(1) == '/'
        if name == 'em' and not closing and not stack:
            end = body.find('</em>', m.end())
            if end != -1:
                out.append(link_em(body[m.end():end])); pos = end + 5; continue
        if name in NOLINK:
            if closing:
                if name in stack: del stack[len(stack) - 1 - stack[::-1].index(name)]
            elif not tag.endswith('/>'):
                stack.append(name)
        out.append(tag); pos = m.end()
    return ''.join(out)


# ---------------------------------------------------------------- datos para las fichas emergentes
def chain_info(q):
    ids = [i for i in (q.get('chain_ids') or []) if i in Q]
    if not q.get('chain') or q['id'] not in ids or len(ids) < 2: return None
    k = ids.index(q['id'])
    return [q['chain'], k + 1, len(ids), ids[k - 1] if k else 0, ids[k + 1] if k + 1 < len(ids) else 0]

def qd(q):
    d = {'n': q['name'], 'l': q['level'], 'm': q.get('min') or 0, 'z': q.get('zone') or ''}
    if q.get('type'): d['t'] = q['type']
    f = G.faction(q)
    if f == 'A': d['f'] = 1
    if q.get('starts'): s = q['starts'][0]; d['g'] = [s['t'], s['id'], s['name']]
    if q.get('sc'): d['gc'] = q['sc']
    if q.get('ends'): e = q['ends'][0]; d['e'] = [e['t'], e['id'], e['name']]
    if q.get('ec'): d['ec'] = q['ec']
    o = G.clean(q.get('obj') or '')
    if o: d['o'] = o[:320]
    if q.get('xp'): d['x'] = q['xp']
    if q.get('money'): d['c'] = q['money']
    r = [[i['id'], i['name'], G.QUALITY.get((i.get('color') or '').lower(), 1)] for i in (q.get('items') or []) if i.get('name')]
    rc = [[i['id'], i['name'], G.QUALITY.get((i.get('color') or '').lower(), 1)] for i in (q.get('choice') or []) if i.get('name')]
    if r: d['r'] = r
    if rc: d['rc'] = rc
    p = [[x['name'], x['v']] for x in (q.get('rep') or []) if x.get('v')]
    if p: d['p'] = p
    k = chain_info(q)
    if k: d['k'] = k
    if q.get('group'): d['gr'] = q['group']
    if q.get('timer'): d['ti'] = G.clean(str(q['timer']))
    if q.get('provided'): d['pv'] = [q['provided']['id'], q['provided']['name']]
    return d


# ---------------------------------------------------------------- listado completo por zona
def wfi_sections(slug):
    """(texto de secciones de la Alianza o comunes, texto de secciones de la Horda) de la guía paso a paso."""
    p = os.path.join(G.CACHE, 'wfi', f'{slug}.txt') if slug else None
    if not p or not os.path.exists(p): return '', ''
    ally, horde, cur = [], [], 'a'
    for line in open(p, encoding='utf-8'):
        if line.startswith('## '):
            cur = 'h' if re.match(r'## \s*Horde', line) else 'a'
        (horde if cur == 'h' else ally).append(line)
    return ''.join(ally), ''.join(horde)

def fmt_coord(c, dbzones):
    if not c: return ''
    s = f'{c[0]:g}, {c[1]:g}'
    if c[2] and c[2] not in dbzones: s += f' en {c[2]}'
    return s

def quest_meta(group, dbzones):
    """Texto secundario de una fila: quién la da y dónde."""
    for q in group:
        if q.get('starts'):
            s = q['starts'][0]
            who = esc(s['name'])
            if s['t'] == 'item': who = 'objeto ' + who
            c = fmt_coord(q.get('sc'), dbzones)
            return who + (f' · {c}' if c else '')
    for q in group:
        c = fmt_coord(q.get('sc'), dbzones)
        if c: return c
    return ''

def zone_list(title, dbzones, slug):
    ally_txt, horde_txt = wfi_sections(slug)
    groups = defaultdict(list)
    for q in Q.values():
        if q.get('zone') in dbzones and G.usable(q) and G.faction(q) != 'H':
            n = q['name']
            if horde_txt and n in horde_txt and n not in ally_txt: continue
            groups[n].append(q)
    if not groups: return '', 0
    rows = []
    for n, g in groups.items():
        g.sort(key=lambda q: (q['level'], q['id']))
        rows.append((min(q['level'] for q in g), n, g))
    rows.sort(key=lambda r: (r[0], r[1]))
    out = []
    for lvl, n, g in rows:
        first = g[0]
        USED_Q.add(first['id'])
        tags = ''
        isnew = any(G.is_new(q) for q in g)
        if isnew: tags += '<span class="tag new">nueva</span>'
        t = first.get('type')
        if t in ('Elite', 'Dungeon', 'Raid', 'PvP'):
            tags += f'<span class="tag ty">{ {"Elite": "élite", "Dungeon": "mazmorra", "Raid": "raid", "PvP": "JcJ"}[t] }</span>'
        if len(g) > 1: tags += f'<span class="tag st">{len(g)} pasos</span>'
        star = '<span class="star" title="Aparece en la guía paso a paso">★</span>' if ally_txt and n in ally_txt else ''
        k = chain_info(first)
        chain = f' · cadena {esc(k[0])}' if k else ''
        meta = quest_meta(g, dbzones)
        xp = sum(q.get('xp') or 0 for q in g)
        lo = min((q.get('min') or q['level']) for q in g)
        out.append(
            f'<li data-lv="{lo}-{lvl + 2}"{" data-new" if isnew else ""}{" data-star" if star else ""}><label><input type="checkbox" data-k="q{first["id"]}"><span>'
            f'<span class="lv">{lvl}</span> {star}{A("quest", first["id"], esc(n))}{tags}'
            f'<span class="qm">{meta}{chain}{f" · {xp} XP" if xp else ""}</span></span></label></li>')
    note = ('Datos del juego (Warcraft DB). Puede incluir alguna quest de otra clase o retirada. '
            + ('★ = aparece en la guía paso a paso.' if ally_txt else ''))
    chips = ('<button type="button" data-f="" class="on">Todas</button><button type="button" data-f="pend">Pendientes</button>'
             '<button type="button" data-f="new">Nuevas en Forever</button>'
             + ('<button type="button" data-f="star">★ En la guía</button>' if ally_txt else ''))
    htmlout = (f'<section class="blk allq" data-total="{len(out)}"><div class="blk-h"><h3>Todas las quests <span class="prog"></span></h3>'
               f'<div class="filters">{chips}</div></div><p class="src">{note}</p><ul class="chk ql">{"".join(out)}</ul></section><!--/allq-->')
    return htmlout, len(out)


# ---------------------------------------------------------------- mazmorras
WTDQ = json.load(open(os.path.join(ROOT, 'data', 'wt-dungeon-quests.json'), encoding='utf-8'))
def load_dungeon_cards():
    cards = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', 'dungeons-*.json'))):
        for d in json.load(open(p, encoding='utf-8')):
            cards[d['key']] = d
    return cards
CARDS = load_dungeon_cards()

def dungeon_quest_ids(dbzone, slugs):
    horde, keep = set(), set()
    for s in slugs:
        for sec, lst in WTDQ.get(s, {}).items():
            if 'Horde' in sec: horde.update(lst)
            elif sec.startswith(('Alliance', 'Neutral')): keep.update(lst)
    ids = set()
    for i in keep:
        if i in Q and i not in horde and G.usable(Q[i]) and G.faction(Q[i]) != 'H': ids.add(i)
    for q in Q.values():
        if q.get('zone') == dbzone and q['id'] not in horde and G.usable(q) and G.faction(q) != 'H':
            if G.faction(q) == 'A' or G.is_new(q) or not slugs or q['id'] in keep:
                ids.add(q['id'])
    return ids

def reward_chips(q, limit=4):
    its = (q.get('choice') or []) + (q.get('items') or [])
    out = []
    for i in its[:limit]:
        if i.get('id') and i.get('name'): out.append(ia(i['id'], i['name']))
    more = len(its) - limit
    return ' · '.join(out) + (f' y {more} más' if more > 0 else '')

def dungeon_quest_rows(dbzone, slugs):
    ids = dungeon_quest_ids(dbzone, slugs)
    outside, inside, unknown = [], [], []
    for i in ids:
        q = Q[i]
        c = q.get('sc')
        s = q['starts'][0] if q.get('starts') else None
        if s and s['t'] in ('item', 'object') and not (c and c[2] and c[2] != dbzone):
            where, bucket = ('cae: ' if s['t'] == 'item' else 'objeto: ') + esc(s['name']), inside
        elif c and c[2] and (c[2] == dbzone or dbzone.replace('The ', '') in c[2]):
            where, bucket = (esc(s['name']) if s else 'dentro'), inside
        elif s or c:
            where = (esc(s['name']) if s else '') + (f' · {c[2] or ""} ({c[0]:g}, {c[1]:g})' if c else '')
            bucket = outside
        else:
            where, bucket = '', unknown
        k = chain_info(q)
        order = (k[1] if k else 0, q['level'], q['name'], q['id'])
        chain = f'<span class="tag st">paso {k[1]} de {k[2]}</span>' if k else ''
        new = '<span class="tag new">nueva</span>' if G.is_new(q) else ''
        rw = reward_chips(q)
        row = (f'<li data-lv="{q.get("min") or q["level"]}-{q["level"] + 3}"><label><input type="checkbox" data-k="q{i}"><span>'
               f'<span class="lv">{q["level"]}</span> {qa(i)}{new}{chain}'
               f'<span class="qm">{where}{f" · {q["xp"]} XP" if q.get("xp") else ""}</span>'
               f'{f"<span class=qr>{rw}</span>" if rw else ""}</span></label></li>')
        bucket.append((order, row))
    def block(title, rows):
        if not rows: return ''
        rows.sort(key=lambda r: r[0])
        return f'<h5>{title}</h5><ul class="chk ql">{"".join(r[1] for r in rows)}</ul>'
    return (block('Se cogen fuera: recógelas antes de entrar', outside) + block('Se cogen dentro o caen de un jefe', inside)
            + block('Sin datos de dónde empiezan', unknown)), len(ids)

def li_list(items):
    return '<ul>' + ''.join(f'<li>{linkify(esc(x))}</li>' for x in items if x) + '</ul>' if items else ''

def boss_block(card):
    bosses = card.get('bosses') or []
    if not bosses: return '<p class="src">Las guías aún no detallan los jefes de esta mazmorra.</p>'
    out = []
    for b in bosses:
        name = b.get('name', '')
        head = f'<b>{esc(name)}</b>' if name.startswith('Botín') else f'<b>{npc_link(name)}</b>'
        if b.get('optional'): head += ' <span class="tag">opcional</span>'
        loot = ' · '.join(item_link(n) for n in (b.get('loot') or [])[:14])
        out.append(f'<li>{head}{" — " + linkify(esc(b["tip"])) if b.get("tip") else ""}'
                   f'{f"<div class=loot>{loot}</div>" if loot else ""}</li>')
    return f'<ol class="bosses">{"".join(out)}</ol>'

def key_items_block(cards):
    rows = []
    for label, card in cards:
        for k in card.get('key_items') or []:
            if k['name'].startswith(NOT_ITEMS): continue
            src = esc(k.get('from') or '')
            if label: src = f'{esc(label)}: {src}' if src else esc(label)
            rows.append(f'<li>{item_link(k["name"])} <span class="kind k-{esc(k.get("kind", "otro"))}">{KIND.get(k.get("kind"), "utilidad")}</span>'
                        f'<span class="qm">{linkify(esc(k.get("why", "")))}{f" · {src}" if src else ""}</span></li>')
    return f'<ul class="keyitems">{"".join(rows)}</ul>' if rows else ''

def render_dungeons():
    out, dash = [], []
    for gkey, name, dbzone, new, loc, wt, wtq, wfi, wings in DG:
        cards = [(w[1], CARDS.get(w[0], {})) for w in wings]
        first = cards[0][1]
        lo, hi = min(w[2] for w in wings), max(w[3] for w in wings)
        qrows, qn = dungeon_quest_rows(dbzone, wtq)
        tiers = sorted({TIER[w[4]] for w in wings if w[4]})
        for w in wings:
            dash.append({'k': w[0], 'g': gkey, 'gn': name, 'n': name + (f' · {w[1]}' if w[1] else ''), 'a': w[2], 'b': w[3],
                         'new': 1 if new else 0, 'loc': loc, 'q': qn})
        done = ''.join(f'<label class="done"><input type="checkbox" data-k="dg-{w[0]}" data-dg="{w[0]}"> Hecha{f": {esc(w[1])}" if w[1] else ""}</label>' for w in wings)
        how = ''
        if first.get('where'): how += f'<p>{linkify(esc(first["where"]))}</p>'
        if first.get('route'): how += f'<p>{linkify(esc(first["route"]))}</p>'
        if first.get('time'): how += f'<p class="src">Duración: {esc(first["time"])}</p>'
        before, shaman, tips = [], [], []
        for label, c in cards:
            pre = f'{label}: ' if label and len(cards) > 1 else ''
            before += [pre + x for x in c.get('before') or []]
            shaman += [pre + x for x in c.get('shaman') or []]
            tips += [pre + x for x in c.get('tips') or []]
        bosses = ''
        for label, c in cards:
            if len(cards) > 1: bosses += f'<h5>{esc(label)}</h5>'
            bosses += boss_block(c)
        links = [f'<a href="https://www.warcrafttavern.com/forever/guides/{wt}/" target="_blank" rel="noopener">Guía de Warcraft Tavern</a>']
        if wfi: links.append(f'<a href="https://wowforeverinfo.com/guides/{wfi}/" target="_blank" rel="noopener">Guía de wowforeverinfo</a>')
        for sl in wtq: links.append(f'<a href="https://www.warcrafttavern.com/forever/guides/{sl}-quests/" target="_blank" rel="noopener">Quests en Warcraft Tavern</a>')
        ki = key_items_block(cards)
        classic = ('<p class="src">Jefes y consejos según Classic: Warcraft Tavern no pudo probar esta mazmorra en la beta de Forever. '
                   'Las quests sí salen de los datos de Forever.</p>') if any(w[0] in CLASSIC_BASED for w in wings) else ''
        legacy = ('Legacy: ' + ', '.join(tiers)) if tiers else 'No cuenta para el Legacy'
        blk = lambda title, inner, cls='': f'<section class="blk{cls}"><h3>{title}</h3>{inner}</section>' if inner else ''
        out.append(f'''
<article class="page dpage" id="dg-{gkey}" data-name="{esc(name)}" data-lv="{lo}-{hi}" hidden>
<header class="ph">
<div class="crumb"><a href="#mazmorras">Mazmorras</a><span>›</span>{esc(name)}</div>
<h2>{esc(name)}</h2>
<div class="ph-meta"><span class="lv">{lo}-{hi}</span><span>{esc(loc)}</span>{'<span class="tag new">nueva</span>' if new else ''}<span>{legacy}</span></div>
<div class="dones">{done}</div>
</header>
<div class="cols">
<div>
{blk('Cómo llegar', how)}
{blk('Antes de entrar', li_list(before[:7]))}
<section class="blk dq"><h3>Quests <span class="prog"></span></h3>{qrows or '<p class="src">Sin quests de Alianza documentadas.</p>'}</section>
</div>
<div>
{blk('Jefes en orden', classic + bosses)}
{blk('Objetos clave para ti', ki)}
{blk('Consejos de chamán', li_list(shaman[:6]))}
{blk('Consejos', li_list(tips[:6]))}
</div>
</div>
<p class="src">{" · ".join(links)}</p>
</article>''')
    return ''.join(out), dash

def render_gantt(dash):
    LO, HI = 10, 60
    pct = lambda v: (v - LO) / (HI - LO) * 100
    rows = []
    for d in dash:
        left, width = pct(d['a']), max(pct(d['b']) - pct(d['a']), 2.2)
        rows.append(f'<a class="gr" href="#dg-{d["g"]}" data-dg="{d["k"]}" data-lv="{d["a"]}-{d["b"]}" data-tip="{esc(d["n"])} · niveles {d["a"]}-{d["b"]} · {esc(d["loc"])} · {d["q"]} quests">'
                    f'<span class="gl">{esc(d["n"])}</span><span class="gt"><i class="gb{" gn" if d["new"] else ""}" style="left:{left:.2f}%;width:{width:.2f}%"></i></span>'
                    f'<span class="gv">{d["a"]}-{d["b"]}</span></a>')
    ticks = ''.join(f'<span style="left:{pct(v):.2f}%">{v}</span>' for v in range(LO, HI + 1, 10))
    return f'''
<figure class="gantt" aria-label="Mazmorras por rango de nivel">
<figcaption><b>Mazmorras por nivel</b><span class="lg"><i class="gb"></i>Clásica</span><span class="lg"><i class="gb gn"></i>Nueva en Forever</span><span class="lg"><i class="gline"></i>Tu nivel</span></figcaption>
<div class="g-body"><div class="g-rows">{"".join(rows)}</div><div class="g-now" aria-hidden="true"></div></div>
<div class="g-axis" aria-hidden="true"><span class="gl"></span><span class="gt">{ticks}</span><span class="gv"></span></div>
<div class="g-tip" hidden></div>
</figure>'''


# ---------------------------------------------------------------- ensamblado
def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

# casilla de la checklist -> zonas en cuya página aparece
IMP_MAP = {}
def _imp(keys, *zones):
    for k in keys.split(): IMP_MAP[k] = list(zones)
_imp('dm1 dm2 dm3', 'Dun Morogh'); _imp('dm4', 'Ironforge'); _imp('lm1 lm2 lm3', 'Loch Modan'); _imp('ds1 ds2 ds3', 'Darkshore')
_imp('ew1 ew2 ew3', 'Elwynn Forest'); _imp('wf1 wf2 wf3 wf4 wf5 wf6', 'Westfall'); _imp('rr1 rr2 rr3 rr4', 'Redridge Mountains')
_imp('dw1 dw2 dw3 dw4', 'Duskwood'); _imp('wl1 wl2 wl3 wl4 wl5 wl6', 'Wetlands'); _imp('av1 av2', 'Ashenvale')
_imp('bs1', 'The Barrens', 'Stonetalon Mountains'); _imp('bs2', 'The Barrens')
_imp('hb1', 'Hillsbrad Foothills'); _imp('hb2', 'Hillsbrad Foothills', 'Alterac Mountains'); _imp('hb3', 'Alterac Mountains')
_imp('ar1 ar2 ar3', 'Arathi Highlands'); _imp('tw1', 'Arathi Highlands', 'The Barrens')
_imp('tw2', 'Dustwallow Marsh', 'Desolace', 'Swamp of Sorrows', 'Badlands'); _imp('tw3', 'Thousand Needles'); _imp('tw4', 'Alterac Mountains')
_imp('sd1', 'Stranglethorn Vale'); _imp('sd2', 'Stranglethorn Vale', 'Hillsbrad Foothills'); _imp('sd3', 'Desolace')
_imp('rg1 rg2 rg3 rg4 rg5', 'The Riverglades'); _imp('bd1', 'Badlands'); _imp('bd2', 'Dustwallow Marsh'); _imp('bd3', 'Swamp of Sorrows')
_imp('ft1', 'Feralas', 'Tanaris'); _imp('ft2', 'Tanaris'); _imp('ft3', 'The Hinterlands'); _imp('ft4', 'The Hinterlands', 'Feralas')
_imp('sg1', 'Searing Gorge'); _imp('sg2', 'Burning Steppes', 'Ironforge'); _imp('sg3 sg4', 'Burning Steppes')
_imp('ug1 ug2', "Un'Goro Crater"); _imp('ug3', 'Felwood'); _imp('ug4', 'Azshara', 'Teldrassil y Darnassus'); _imp('ug5', 'Azshara'); _imp('ug6', 'Blasted Lands')
_imp('pl1', 'Western Plaguelands', 'Eastern Plaguelands'); _imp('pl2 pl3', 'Western Plaguelands'); _imp('pl4', 'Eastern Plaguelands'); _imp('pl5', 'Winterspring')
DONE_DEFAULT = {'Dun Morogh', 'Loch Modan'}

ZD = re.compile(r'<details class="zona" data-lv="([^"]*)"><summary><span class="zn">(.*?)</span><span class="lv">(.*?)</span>(.*?)</summary><div class="body">(.*?)</div></details>', re.S)
CKG = re.compile(r'<details class="zona ck"[^>]*><summary><span class="zn">(.*?)</span>.*?</summary><div class="body">(.*?)</div></details>', re.S)
CKI = re.compile(r'<li><label><input type="checkbox" data-k="([a-z0-9]+)"><span>(.*?)</span></label></li>', re.S)

def lv_nums(txt):
    nums = [int(x) for x in re.findall(r'\d+', txt)]
    return (nums[0], nums[-1]) if nums else (None, None)

def bracket(a):
    if a is None: return 'Ciudades y otras zonas'
    return 'Niveles 1-20' if a < 20 else 'Niveles 20-35' if a < 35 else 'Niveles 35-50' if a < 50 else 'Niveles 50-60'

TOP = '''<header class="top"><div class="top-in">
<a class="brand" href="#inicio">Enano Chamán<span>WoW Forever</span></a>
<nav class="tabs" aria-label="Secciones">
<a href="#inicio" data-view="inicio">Inicio</a><a href="#zonas" data-view="zonas">Zonas</a><a href="#mazmorras" data-view="mazmorras">Mazmorras</a><a href="#chaman" data-view="chaman">Tu chamán</a><a href="#referencia" data-view="referencia">Referencia</a>
</nav>
<div class="top-tools">
<label class="lvl" for="nivel">Nivel<input id="nivel" type="number" min="1" max="60" value="20" inputmode="numeric"></label>
<div class="search"><input id="buscar" type="search" placeholder="Buscar quest, zona, jefe, objeto…" autocomplete="off" aria-label="Buscar en la guía"><div id="results" hidden></div></div>
<details class="cfg"><summary>Ajustes</summary><div class="cfg-body">
<label for="fichas">Abrir fichas en</label>
<select id="fichas"><option value="wh">Wowhead</option><option value="whes">Wowhead en español</option><option value="wdb">Warcraft DB</option></select>
<div id="progreso" class="prog-box" aria-live="polite"></div>
<button id="imprimir" type="button">Imprimir o guardar PDF</button>
<p>Las casillas se guardan en este navegador. Para llevarlas a otro dispositivo, copia este código y cárgalo allí.</p>
<textarea id="sync-code" rows="3" spellcheck="false" aria-label="Código de progreso"></textarea>
<div class="sync-btns"><button id="sync-copy" type="button">Copiar código</button><button id="sync-load" type="button">Cargar código</button></div>
<div id="sync-msg" aria-live="polite"></div>
</div></details>
</div></div></header>'''

NOW_HTML = '''<section id="ahora" class="sec">
<h2>Ahora, con nivel <span id="now-lvl">20</span></h2>
<div class="now" id="now"></div>
</section>
<section id="tus-pendientes" class="sec">
<h2>Imprescindibles pendientes a tu nivel</h2>
<p class="intro">Lo que aún no has marcado en las zonas de tu nivel. Toca una para ir a su zona.</p>
<div id="pend"></div>
</section>'''

def build():
    body = open(os.path.join(ROOT, 'src', 'guia.html'), encoding='utf-8').read()
    css = open(os.path.join(ROOT, 'src', 'style.css'), encoding='utf-8').read()
    js = open(os.path.join(ROOT, 'src', 'app.js'), encoding='utf-8').read()
    prefetch()
    body = linkify(body)
    hero = re.search(r'<header class="hero">.*?</header>', body, re.S).group(0)
    secs = {m.group(1): m.group(2).replace('<span class="n"></span>', '')
            for m in re.finditer(r'<section id="([^"]+)">(.*?)</section>', body, re.S)}

    # imprescindibles repartidos por zona
    imp, paras = defaultdict(list), {}
    ck = secs.get('checklist', '')
    for _, gbody in CKG.findall(ck):
        zs = set()
        for k, inner in CKI.findall(gbody):
            for z in IMP_MAP.get(k, []):
                imp[z].append((k, inner)); zs.add(z)
        ps = re.findall(r'<p[^>]*>.*?</p>', gbody, re.S)
        if ps and len(zs) == 1: paras[next(iter(zs))] = ''.join(ps)
    mark = '<h3>Lo que aporta si te gusta explorar</h3>'
    explore = ck[ck.index(mark) + len(mark):] if mark in ck else ''

    zones = []
    for sid in ('zonas-1-30', 'zonas-30-45', 'zonas-40-60'):
        for datalv, zn, lvtxt, rest, zbody in ZD.findall(secs.get(sid, '')):
            base = re.search(r'<span class="base">(.*?)</span>', rest)
            zones.append({'name': html.unescape(zn), 'lv': lvtxt, 'datalv': datalv, 'base': base.group(1) if base else '',
                          'new': 'tag new' in rest, 'body': zbody})
    for name, lv, base, dbz, wslug, text in EXTRA_ZONES:
        zones.append({'name': name, 'lv': lv, 'datalv': lv if re.fullmatch(r'\d+-\d+', lv) else '', 'base': esc(base),
                      'new': name == "Shen'dralas", 'body': f'<p>{linkify(esc(text))}</p>', 'extra': (dbz, wslug)})
    def zkey(z):
        a, _ = lv_nums(z['lv'])
        return (0 if a is not None else 1, a or 0, z['name'])
    zones.sort(key=zkey)

    zpages, zdash = [], []
    for z in zones:
        name = z['name']
        dbz, wslug = z.get('extra') or ZONES[name]
        lst, n = zone_list(name, dbz, wslug)
        zid, a, b = 'z-' + slug(name), *lv_nums(z['lv'])
        items = imp.get(name, [])
        imp_html = ''
        if items:
            lis = ''.join(f'<li><label><input type="checkbox" data-k="{k}"><span>{inner}</span></label></li>' for k, inner in items)
            imp_html = (f'<section class="blk imp"><h3>Imprescindibles <span class="prog"></span></h3>'
                        f'<ul class="chk">{lis}</ul>{paras.get(name, "")}</section>')
        guide = (f'<a href="https://wowforeverinfo.com/guides/{wslug}/" target="_blank" rel="noopener">Guía paso a paso</a>') if wslug else ''
        dl = f' data-lv="{z["datalv"]}"' if z['datalv'] else ''
        chk = ' checked' if name in DONE_DEFAULT else ''
        title = 'Qué hay aquí' if 'extra' in z else 'Ruta y cadenas'
        zpages.append(f'''
<article class="page zpage" id="{zid}" data-name="{esc(name)}"{dl} hidden>
<header class="ph">
<div class="crumb"><a href="#zonas">Zonas</a><span>›</span>{esc(name)}</div>
<h2>{esc(name)}</h2>
<div class="ph-meta"><span class="lv">{esc(z["lv"])}</span><span>{z["base"]}</span>{'<span class="tag new">nueva</span>' if z["new"] else ''}{guide}</div>
<div class="dones"><label class="done"><input type="checkbox" data-k="zdone-{slug(name)}" data-zdone="{zid}"{chk}> Zona completada</label></div>
</header>
{imp_html}
<section class="blk ruta"><h3>{title}</h3>{z["body"]}</section>
{lst}
</article>''')
        zdash.append({'id': zid, 'n': name, 'lv': z['lv'], 'a': a, 'b': b, 'base': html.unescape(re.sub(r'<[^>]+>', '', z['base'])),
                      'grp': bracket(a), 'new': 1 if z['new'] else 0, 'imp': len(items), 'q': n})

    dungeons, dash = render_dungeons()
    sec = lambda sid, newid=None: f'<section id="{newid or sid}" class="sec">{secs[sid]}</section>' if secs.get(sid) else ''
    views = f'''
<section class="view" id="v-inicio">
{hero}
{NOW_HTML}
{sec('plan-20')}
</section>
<section class="view" id="v-zonas" hidden>
<div class="overview"><h2 class="vh">Zonas</h2>
<p class="intro">Una página por zona con sus imprescindibles, su ruta y todas sus quests. Las de tu nivel van resaltadas.</p>
<div id="zcards"></div></div>
{"".join(zpages)}
</section>
<section class="view" id="v-mazmorras" hidden>
<div class="overview"><h2 class="vh">Mazmorras</h2>
<p class="intro">Una página por mazmorra: cómo llegar, qué coger antes, jefes, objetos clave y quests. Marca las que hagas: cuentan para los logros de Legacy.</p>
{render_gantt(dash)}
<div id="dcards"></div></div>
{dungeons}
</section>
<section class="view" id="v-chaman" hidden>
{sec('clase')}{sec('spec')}{sec('personaje')}{sec('profesiones')}
</section>
<section class="view" id="v-referencia" hidden>
{sec('plan')}{sec('zonas', 'tabla-zonas')}{sec('cadenas')}{sec('estado')}
{f'<section id="explorar" class="sec"><h2>Exploración y reputaciones</h2>{explore}</section>' if explore else ''}
{sec('pendiente')}{sec('fuentes')}
</section>'''
    foot = re.search(r'<footer>.*?</footer>', body, re.S)
    main = f'{TOP}\n<div class="shell"><aside class="side" id="side" aria-label="En esta sección"></aside>\n<main>{views}\n{foot.group(0) if foot else ""}</main></div>'

    for i in list(USED_Q):
        k = chain_info(Q[i]) if i in Q else None
        if k:
            for j in (k[3], k[4]):
                if j: USED_Q.add(j)
    npcloc = {}
    for q in Q.values():
        if q.get('starts') and q.get('sc') and q['starts'][0]['t'] == 'npc':
            npcloc.setdefault(q['starts'][0]['id'], q['sc'])
    data = {
        'q': {str(i): qd(Q[i]) for i in sorted(USED_Q) if i in Q},
        'i': {str(i): t for i, t in USED_I.items()},
        'n': {str(i): [n] + (npcloc.get(i) or []) for i, n in USED_N.items()},
        'zones': zdash, 'dungeons': dash, 'miles': [list(m) for m in MILESTONES], 'prof': [list(p) for p in PROF],
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    page = ('<title>Enano Chamán en WoW Forever</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:wght@600;700;800&family=Source+Sans+3:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap">\n'
            f'<style>\n{css}</style>\n{main}\n<script id="gd" type="application/json">{blob}</script>\n<script>\n{js}</script>\n')
    os.makedirs(os.path.join(ROOT, 'dist'), exist_ok=True)
    open(os.path.join(ROOT, 'dist', 'artifact.html'), 'w', encoding='utf-8').write(page)
    def wrap(p, cls):
        return ('<!doctype html>\n<html lang="es"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + p.replace('</style>', f'</style></head><body class="{cls}">', 1) + '\n</body></html>\n')
    open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(wrap(page, 'local'))
    pr = re.sub(r'<section class="blk allq".*?<!--/allq-->', '', page, flags=re.S)
    pr = re.sub(r'(<(?:section class="view"|article class="page [a-z]+")[^>]*?) hidden>', r'\1>', pr)
    open(os.path.join(ROOT, 'dist', 'print.html'), 'w', encoding='utf-8').write(wrap(pr, 'local print-all'))
    print(f'quests en caché {len(Q)} · fichas de quest {len(data["q"])} · objetos {len(data["i"])} · PNJ {len(data["n"])}')
    print(f'enlaces en el texto: {STATS["linked"]} directos, {STATS["search"]} por búsqueda · zonas {len(zdash)} · mazmorras {len(dash)}')
    print(f'index.html {os.path.getsize(os.path.join(ROOT, "index.html")) // 1024} KB')

def prefetch():
    """Resuelve en paralelo los nombres de jefes y objetos de las fichas de mazmorra."""
    if G.OFFLINE: return
    items, npcs = set(), set()
    for c in CARDS.values():
        for b in c.get('bosses') or []:
            if not b.get('name', '').startswith('Botín'): npcs.add(b['name'])
            items.update((b.get('loot') or [])[:14])
        items.update(k['name'] for k in c.get('key_items') or [])
    with ThreadPoolExecutor(max_workers=4) as ex:
        ids = list(ex.map(lambda n: NAMES.search(n, 'item'), sorted(items)))
        list(ex.map(lambda n: NAMES.search(n, 'npc'), sorted(npcs)))
        list(ex.map(G.item_tip, [i for i in ids if i]))
    rew = set()
    for _, _, dbzone, _, _, _, wtq, _, _ in DG:
        for i in dungeon_quest_ids(dbzone, wtq):
            for it in ((Q[i].get('choice') or []) + (Q[i].get('items') or []))[:4]:
                if it.get('id'): rew.add(it['id'])
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(G.item_tip, sorted(rew)))

if __name__ == '__main__':
    build()
