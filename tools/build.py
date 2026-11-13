#!/usr/bin/env python3
"""Genera index.html (guía navegable) y print.html (versión para PDF).

  python3 tools/build.py            usa la caché y consulta lo que falte
  python3 tools/build.py --offline  solo caché
"""
import os, re, sys, json, html, glob, difflib, urllib.parse
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
 ('ragefire-chasm', 'Ragefire Chasm', 'Ragefire Chasm', False, 'Orgrimmar (Horda): es la Hall of Thanes de la Horda, a ti no te hace falta', 'ragefire-chasm', [], 'ragefire-chasm', [('ragefire-chasm', '', 13, 18, 'N')]),
 ('ruins-of-lordaeron', 'Ruins of Lordaeron', 'Ruins of Lordaeron', True, 'Tirisfal Glades (Horda)', 'the-ruins-of-lordaeron', ['the-ruins-of-lordaeron'], 'ruins-of-lordaeron', [('ruins-of-lordaeron', '', 15, 22, 'N')]),
 ('wailing-caverns', 'Wailing Caverns', 'Wailing Caverns', False, 'The Barrens (Horda)', 'wailing-caverns', ['wailing-caverns'], 'wailing-caverns', [('wailing-caverns', '', 15, 24, 'N')]),
 ('deadmines', 'The Deadmines', 'The Deadmines', False, 'Moonbrook, Westfall', 'the-deadmines', ['the-deadmines'], 'deadmines', [('deadmines', '', 17, 26, 'N')]),
 ('shadowfang-keep', 'Shadowfang Keep', 'Shadowfang Keep', False, 'Silverpine Forest (Horda)', 'shadowfang-keep', [], 'shadowfang-keep', [('shadowfang-keep', '', 20, 30, 'N')]),
 ('blackfathom-deeps', 'Blackfathom Deeps', 'Blackfathom Deeps', False, 'Zoram Strand, Ashenvale', 'blackfathom-deeps', ['blackfathom-deeps'], 'blackfathom-deeps', [('blackfathom-deeps', '', 24, 32, 'E')]),
 ('stockade', 'The Stockade', 'The Stockade', False, 'Stormwind', 'the-stockade-dungeon-map-location-bosses', ['the-stockade'], 'stockade', [('stockade', '', 25, 29, '')]),
 ('excavation-site', 'Excavation Site: Wetlands', 'Excavation Site: Wetlands', True, 'Wetlands', 'excavation-site-wetlands', ['excavation-site-wetlands'], 'excavation-site', [('excavation-site', '', 26, 33, 'N')]),
 ('city-of-dalaran', 'City of Dalaran', 'City of Dalaran', True, 'Alterac Mountains', 'city-of-dalaran', ['city-of-dalaran'], None, [('city-of-dalaran', '', 28, 35, 'E')]),
 ('razorfen-kraul', 'Razorfen Kraul', 'Razorfen Kraul', False, 'Sur de The Barrens (Horda)', 'razorfen-kraul', ['razorfen-kraul'], 'razorfen-kraul', [('razorfen-kraul', '', 29, 38, 'E')]),
 ('gnomeregan', 'Gnomeregan', 'Gnomeregan', False, 'Dun Morogh', 'gnomeregan', ['gnomeregan'], 'gnomeregan', [('gnomeregan', '', 29, 38, 'E')]),
 ('scarlet-monastery', 'Scarlet Monastery', 'Scarlet Monastery', False, 'Tirisfal Glades (Horda)', 'scarlet-monastery', ['scarlet-monastery'], 'scarlet-monastery',
  [('sm-graveyard', 'Graveyard', 30, 38, 'E'), ('sm-library', 'Library', 33, 41, 'E'), ('sm-armory', 'Armory', 36, 44, 'E'), ('sm-cathedral', 'Cathedral', 38, 46, 'E')]),
 ('drowned-city', 'The Drowned City', 'The Drowned City', True, 'Frente a Stranglethorn Vale, bajo el agua', 'the-drowned-city', [], None, [('drowned-city', '', 35, 42, 'E')]),
 ('razorfen-downs', 'Razorfen Downs', 'Razorfen Downs', False, 'Sur de The Barrens (Horda)', 'razorfen-downs', ['razorfen-downs'], 'razorfen-downs', [('razorfen-downs', '', 37, 46, 'M')]),
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
 ('Teldrassil y Darnassus', '1-12', 'base: Dolanaar', ['Teldrassil', 'Darnassus', 'Shadowglen', "Rut'theran Village"], 'teldrassil-1-12', 'Zona inicial élfica. En Darnassus se cogen quests de Blackfathom Deeps y Blackmaw Hold.'),
 ('The Barrens', '10-25', 'base: Ratchet (neutral)', ['The Barrens', 'Ratchet'], None, 'Zona de la Horda con Ratchet como puerto neutral. Aquí están Wailing Caverns, Razorfen Kraul y Razorfen Downs.'),
 ('Stonetalon Mountains', '15-27', 'base: Stonetalon Peak', ['Stonetalon Mountains'], None, 'Paso entre Ashenvale y Desolace. Un tramo de la bolsa de dormir.'),
 ('Thousand Needles', '25-35', 'base: Shimmering Flats (neutral)', ['Thousand Needles', 'The Shimmering Flats'], None, 'Aquí termina Heed My Call, de tu cadena del arma, y empieza la quest de Razorfen Kraul del diario de Lonebrow.'),
 ("Shen'dralas", '40-55', 'compartida', ["Shen'dralas"], None, 'Zona nueva al sur de Desolace, por el Valley of Bones. Centauros y quests de Dire Maul, Maraudon y Razorfen Downs.'),
 ('Moonglade', '—', 'base: Nighthaven (neutral)', ['Moonglade', 'Nighthaven'], None, 'Refugio druida neutral. Quests de Dire Maul y de Silithus.'),
 ('Deadwind Pass', '55+', 'sin base', ['Deadwind Pass'], None, 'Paso entre Duskwood y Swamp of Sorrows, con Karazhan.'),
]

MILESTONES = [
 (4, 'Totem de Tierra (Call of Earth) y Earth Shock'), (6, 'Earthbind Totem. Cocina con Camping 101'), (8, 'Lightning Shield y Stoneclaw Totem'),
 (10, 'Totem de Fuego (Call of Fire), Flame Shock, primer talento y Oficial en profesiones. Entrena mazas y hachas de dos manos en Ironforge'), (12, 'Fire Nova, Purge y Ancestral Spirit'),
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

def action(q):
    """Qué pide la quest, para su runa: 1 matar, 2 recoger, 3 llevar o hablar, 4 escoltar, 5 otra cosa."""
    o = (q.get('obj') or '').lower()
    if re.search(r'\b(escort|protect)\b', o): return 4
    if re.search(r'\b(kill|slay|defeat|destroy|eliminate|hunt)\b', o): return 1
    if re.search(r'\b(bring|collect|gather|obtain|retrieve|acquire|recover|steal|fill)\b', o): return 2
    if re.search(r'\b(speak|talk|deliver|take|report|find|seek|return|travel|give|show|locate)\b', o): return 3
    return 5

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
    al, an = PRE.get(q['id'], ([], []))
    if al: d['pa'] = al
    if an: d['po'] = an
    nx = [x for x in SUCC.get(q['id'], []) if not repeatable(x)]
    if nx: d['nx'] = nx
    if q['id'] in CLASS_Q: d['cl'] = 1
    d['ac'] = action(q)
    if G.is_new(q): d['nw'] = 1
    zp = MAP2ZONE.get(q.get('zone'))
    if zp: d['zp'] = slug(zp)
    if q['id'] in DQ_OF or q.get('zone') in DGZ: d['dg'] = DQ_OF.get(q['id']) or DGZ[q['zone']]
    ex = sorted(EXCL.get(q['id'], ()))
    if ex: d['ex'] = ex
    if q['id'] in BREAD: d['bc'] = 1
    pq = G.parent(q['id'])
    if pq and pq in Q and in_guide(pq): d['pq'] = pq
    gn = closes(q['id'])
    if gn: d['gn'] = gn
    rq = extra_reqs(q['id'])
    if rq: d['rq'] = rq
    if q['id'] in AKA: d['aka'] = sorted(AKA[q['id']])
    if q['id'] in QCHAIN: d['ch'] = list(QCHAIN[q['id']][:2])
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

def chain_badge(g):
    """Enlace a la cadena de una fila: a su página si la tiene, o a la vista de requisitos de la quest."""
    for q in g:
        if q['id'] in QCHAIN:
            k, n, _ = QCHAIN[q['id']]
            return f' · <a class="qc" href="#cad-{k}">cadena, paso {n}</a>'
    for q in reversed(g):
        if q['id'] in PRE or any(not repeatable(x) for x in SUCC.get(q['id'], [])):
            return f' · <a class="qc" href="#q-{q["id"]}">cadena</a>'
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
    for n, grp in groups.items():
        for kind, g in split_group(grp):
            g.sort(key=lambda q: (q['level'], q['id']))
            rows.append((min(q['level'] for q in g), n, g, kind))
    rows.sort(key=lambda r: (r[0], r[1], r[2][0]['id']))
    out = []
    for lvl, n, g, kind in rows:
        first = g[0]
        USED_Q.add(first['id'])
        tags = ''
        isnew = any(G.is_new(q) for q in g)
        if isnew: tags += '<span class="tag new">nueva</span>'
        t = first.get('type')
        if t in ('Elite', 'Dungeon', 'Raid', 'PvP'):
            tags += f'<span class="tag ty">{ {"Elite": "élite", "Dungeon": "mazmorra", "Raid": "raid", "PvP": "JcJ"}[t] }</span>'
        if kind == 'chain': tags += f'<span class="tag st">{len(g)} pasos</span>'
        elif kind == 'alt': tags += f'<span class="tag st">{len(g)} variantes: basta una</span>'
        if first['id'] in BREAD: tags += '<span class="tag st">recado opcional</span>'
        star = '<span class="star" title="Aparece en la guía paso a paso">★</span>' if ally_txt and n in ally_txt else ''
        chain = chain_badge(g)
        meta = quest_meta(g, dbzones)
        xp = max(q.get('xp') or 0 for q in g) if kind == 'alt' else sum(q.get('xp') or 0 for q in g)
        lo = min((q.get('min') or q['level']) for q in g)
        box = (f'data-k="g{first["id"]}" data-dep="{("|" if kind == "alt" else ",").join("q%d" % q["id"] for q in g)}"' if len(g) > 1 else f'data-k="q{first["id"]}"')
        out.append(
            f'<li data-lv="{lo}-{lvl + 2}"{" data-new" if isnew else ""}{" data-star" if star else ""}><label><input type="checkbox" {box}><span>'
            f'<span class="lv">{lvl}</span> {star}{A("quest", first["id"], esc(n))}{tags}'
            f'<span class="qm">{meta}{chain}{f" · {xp} XP" if xp else ""}</span></span></label></li>')
    note = ('Datos del juego (Warcraft DB). Puede incluir alguna quest de otra clase o retirada. '
            + ('★ = aparece en la guía paso a paso.' if ally_txt else ''))
    chips = ('<button type="button" data-f="" class="on">Todas</button><button type="button" data-f="avail">Puedo cogerlas ahora</button><button type="button" data-f="pend">Pendientes</button>'
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
                    f'<span class="gl">{"<i class=gh>H</i>" if "(Horda)" in d["loc"] else ""}{esc(d["n"])}</span><span class="gt"><i class="gb{" gn" if d["new"] else ""}" style="left:{left:.2f}%;width:{width:.2f}%"></i></span>'
                    f'<span class="gv">{d["a"]}-{d["b"]}</span></a>')
    ticks = ''.join(f'<span style="left:{pct(v):.2f}%">{v}</span>' for v in range(LO, HI + 1, 10))
    return f'''
<figure class="gantt" aria-label="Mazmorras por rango de nivel">
<figcaption><b>Mazmorras por nivel</b><span class="lg"><i class="gb"></i>Ya estaba en Classic</span><span class="lg"><i class="gb gn"></i>Nueva en Forever</span><span class="lg"><i class="gh">H</i>En territorio de la Horda</span><span class="lg"><i class="gline"></i>Tu nivel</span></figcaption>
<p class="src">El color no indica facción: todas las mazmorras se pueden hacer con la Alianza. La H marca las que están en zona de la Horda, donde llegar cuesta más.</p>
<div class="g-body"><div class="g-rows">{"".join(rows)}</div><div class="g-now" aria-hidden="true"></div></div>
<div class="g-axis" aria-hidden="true"><span class="gl"></span><span class="gt">{ticks}</span><span class="gv"></span></div>
<div class="g-tip" hidden></div>
</figure>'''


# ---------------------------------------------------------------- ensamblado
def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

# ---------------------------------------------------------------- cadenas paso a paso
CHAINS = json.load(open(os.path.join(ROOT, 'data', 'chains.json'), encoding='utf-8'))
MAP2ZONE = {}
for _n, (_dbz, _s) in ZONES.items():
    for _d in _dbz: MAP2ZONE.setdefault(_d, _n)
for _n, _lv, _b, _dbz, _s, _t in EXTRA_ZONES:
    for _d in _dbz: MAP2ZONE.setdefault(_d, _n)
DG_NAME = {d[0]: d[1] for d in DG}
QTYPE = {'Dungeon': 'mazmorra', 'Elite': 'élite', 'Raid': 'raid'}

def step_ref(x, c):
    if not x: return ''
    link = ref_link((x['t'], x['id']), x['name'], esc(x['name']))
    loc = f' <span class="co">{esc(c[2] or "")} {c[0]:g}, {c[1]:g}</span>' if c else ''
    return ('el objeto ' if x['t'] in ('object', 'item') else '') + link + loc

def step_where(q):
    """Quién da el paso y a quién se entrega, según los datos del juego."""
    st, en = (q.get('starts') or [None])[0], (q.get('ends') or [None])[0]
    a, b = step_ref(st, q.get('sc')), step_ref(en, q.get('ec'))
    if a and b and st['id'] == en['id'] and q.get('sc') == q.get('ec'): return f'La da y la recoge {a}.'
    to = 'Se entrega en' if en and en['t'] in ('object', 'item') else 'Se entrega a'
    return ' '.join(x for x in (f'La da {a}.' if a else '', f'{to} {b}.' if b else '') if x)

def runs(nums):
    """[1, 2, 3, 5] -> '1-3 y 5'"""
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1: j += 1
        out.append(str(nums[i]) if i == j else f'{nums[i]}-{nums[j]}')
        i = j + 1
    return out[0] if len(out) == 1 else ', '.join(out[:-1]) + ' y ' + out[-1]

def chain_link(ch, here=''):
    return (f'<li><a class="clink" href="#cad-{ch["k"]}" data-chain="{ch["k"]}" data-lv="{ch["lv"]}"><b>{esc(ch["t"])}</b>'
            f'<span class="lv">{ch["lv"]}</span><span class="cl-h">{here}</span><span class="cl-p"></span></a></li>')

def _class_ids():
    """Quests de la lista de clase de chamán de Warcraft DB."""
    p, out = os.path.join(G.CACHE, 'list', 'class__shaman.json'), set()
    def walk(x):
        if isinstance(x, dict):
            if 'id' in x and 'name' in x: out.add(x['id'])
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    if os.path.exists(p): walk(json.load(open(p, encoding='utf-8')))
    return out
CLASS_Q = _class_ids()

def in_guide(i):
    return i in Q and G.usable(Q[i]) and G.faction(Q[i]) != 'H'

# requisitos entre quests (Questie), solo entre las que puede hacer el personaje
PRE, SUCC = {}, defaultdict(list)
for _i in Q:
    if not in_guide(_i): continue
    _al, _an = G.prereqs(_i)
    _al, _an = [x for x in _al if in_guide(x)], [x for x in _an if in_guide(x)]
    if _al or _an: PRE[_i] = (_al, _an)
    for _p in _al + _an: SUCC[_p].append(_i)

# variantes que se excluyen entre sí (solo se puede hacer una): cuentan como la misma gesta
EXCL = defaultdict(set)
for _i in Q:
    if not in_guide(_i): continue
    for _e in (G.QS.get(_i) or {}).get('excl', []):
        if _e != _i and in_guide(_e): EXCL[_i].add(_e); EXCL[_e].add(_i)
# recados que solo llevan a otra quest: Questie lo apunta en el recado (breadcrumbForQuestId) o en el destino (breadcrumbs)
BFOR = {}
for _i in Q:
    if not in_guide(_i): continue
    _s = G.QS.get(_i) or {}
    if _s.get('bfor'): BFOR[_i] = _s['bfor']
    for _b in _s.get('bread', []):
        if in_guide(_b): BFOR.setdefault(_b, _i)
BREAD = set(BFOR)

REP_ES = [(42000, 'Exaltado'), (21000, 'Reverenciado'), (9000, 'Honorable'), (3000, 'Amistoso'), (0, 'Neutral'), (-3000, 'Antipático'), (-6000, 'Hostil')]
def standing(v):
    return next((n for t, n in REP_ES if v >= t), 'Odiado')

def faction_name(fid):
    n = (G.QV.get('factions') or {}).get(str(fid))
    return ' '.join(w.capitalize() if w not in ('OF', 'THE') or k == 0 else w.lower() for k, w in enumerate(n.split('_'))) if n else f'facción {fid}'

def closes(i):
    """Quests de la guía que, una vez hechas, dejan esta sin poder cogerse (así lo comprueba Questie):
    la siguiente de su cadena, el destino de un recado, la que la retira y su quest madre."""
    s_ = G.QS.get(i) or {}
    out = [s_.get('next'), BFOR.get(i), s_.get('until'), s_.get('parent')]
    return sorted({x for x in out if x and x != i and x in Q and in_guide(x)})

def extra_reqs(i):
    """Requisitos que no son otra quest: profesión, especialización y reputación."""
    s_ = G.QS.get(i) or {}
    out = []
    sk = s_.get('skill')
    if sk and sk[1] > 1: out.append(f'{G.SKILL_ES.get(sk[0], sk[0])} {sk[1]}')
    elif sk: out.append(f'tener {G.SKILL_ES.get(sk[0], sk[0])}')
    if s_.get('spec') in (20219, 20222): out.append('Ingeniería ' + ('gnómica' if s_['spec'] == 20219 else 'goblin'))
    if s_.get('rep') and s_['rep'][1] > 0: out.append(f'{standing(s_["rep"][1])} con {faction_name(s_["rep"][0])}')
    if s_.get('maxrep'): out.append(f'no pasar de {standing(s_["maxrep"][1])} con {faction_name(s_["maxrep"][0])}')
    return out
DGZ = {d[2]: d[0] for d in DG}

def linked(a, b):
    """¿Son dos pasos de la misma cadena?"""
    return a in ancestors(b) or b in ancestors(a) or (G.QS.get(a) or {}).get('next') == b or (G.QS.get(b) or {}).get('next') == a

def split_group(g):
    """Parte las quests de un mismo nombre en filas: [(tipo, quests)] con tipo 'one', 'chain' (varios pasos) o 'alt' (variantes: basta una)."""
    left, comps = sorted(g, key=lambda q: q['id']), []
    while left:
        c, grew = [left.pop(0)], True
        while grew:
            grew = False
            for r in list(left):
                if any(linked(r['id'], x['id']) for x in c): c.append(r); left.remove(r); grew = True
        comps.append(c)
    out = []
    while comps:
        c = comps.pop(0)
        alts = [c]
        for o in list(comps):
            if any(b['id'] in EXCL[a['id']] for grp in alts for a in grp for b in o): alts.append(o); comps.remove(o)
        if len(alts) > 1: out.append(('alt', [sorted(x, key=lambda q: (q['level'], q['id']))[-1] for x in alts]))
        else: out.append(('chain' if len(c) > 1 else 'one', c))
    return out

def req_tokens(ids):
    """Claves de casilla para una lista de quests: las variantes excluyentes se juntan en «una u otra»."""
    out, used = [], set()
    for i in ids:
        if i in used: continue
        alts = [i] + [j for j in ids if j != i and j in EXCL[i] and j not in used]
        used.update(alts)
        out.append('|'.join(f'q{j}' for j in alts))
    return out

# la misma quest con otro número: versiones que la base de datos trae duplicadas y que Questie no tiene para Forever.
# No se sabe cuál de los dos números usa el juego, así que cualquiera de ellos cuenta.
ALIAS, AKA = {}, defaultdict(list)
_twin = defaultdict(list)
for _i, _q in Q.items():
    if in_guide(_i): _twin[(G.norm(_q['name']), _q.get('zone'))].append(_i)
for _i, _q in Q.items():
    if in_guide(_i) or not _q.get('name'): continue
    _s = G.QS.get(_i)
    if _s is not None and _s.get('hid') != 1: continue
    _t = _twin.get((G.norm(_q['name']), _q.get('zone')))
    if _t and len(_t) == 1: ALIAS[_i] = _t[0]; AKA[_t[0]].append(_i)

# En Forever vale el número clásico (comprobado en el juego con Researching the Corruption, 1275):
# el otro número solo sirve para reconocer la quest al importar.

# Variantes de otra raza, clase o facción. El juego las da por completadas cuando haces la tuya (un enano tiene
# marcadas las Call of Earth de orcos y tauren), así que al importar cuentan como la quest equivalente de la guía.
ALIAS_WHY = {}
def _variants():
    hand = {s_['q'] for ch in CHAINS for s_ in ch['s'] if 'q' in s_}
    name = lambda i: G.norm(G.QS[i]['n'])
    obj = lambda i: (G.QS[i].get('obj') or '').lower()
    sim = lambda a, b: difflib.SequenceMatcher(None, obj(a), obj(b)).ratio() if obj(a) and obj(b) else 0
    fam, mine = defaultdict(list), defaultdict(list)
    for i in G.QS:
        fam[name(i)].append(i)
        if in_guide(i): mine[name(i)].append(i)
    def pick(i, cands):
        """De varias variantes de la guía: la de una cadena escrita a mano, la que pide lo mismo o, si no, la más antigua."""
        c = [x for x in cands if x in hand] or sorted(cands)
        sc = sorted(((sim(i, x), -x) for x in c), reverse=True)
        if len(sc) > 1 and sc[0][0] - sc[1][0] >= 0.15: return -sc[0][1]
        return c[0]
    # 1) Questie dice qué quests se excluyen entre sí. Con el mismo nombre son la misma quest contada por otro PNJ...
    grp = defaultdict(set)
    for i, d in G.QS.items():
        for e in d.get('excl') or []:
            if e in G.QS and e != i: grp[i].add(e); grp[e].add(i)
    for i in G.QS:
        if i in ALIAS or in_guide(i): continue
        c = [e for e in grp[i] if in_guide(e) and name(e) == name(i)]
        if not c: continue
        t = pick(i, c)
        # ...salvo cuando lo que se excluye es la elección contraria (ingeniería gnómica o goblin): ahí manda el objetivo
        if len(c) == len(mine[name(i)]) or sim(i, t) >= 0.5: ALIAS[i] = t; ALIAS_WHY[i] = 'excl'
    # 2) mismo nombre y mismo puesto en su cadena. El recado que lleva al primer paso cuenta como puesto anterior.
    pos, lead = {}, {}
    for ch in CHAINS:
        qs = [s_ for s_ in ch['s'] if 'q' in s_]
        for x, y in zip(qs, qs[1:]):
            if x.get('bc'): lead[x['q']] = y['q']
    for ids in fam.values():
        fs, pred = set(ids), defaultdict(set)
        for a in ids:
            d = G.QS[a]
            for nx in (d.get('next'), d.get('bfor'), lead.get(a)):
                if nx in fs and nx != a: pred[nx].add(a)
            for p_ in d['pres'] + d['preg']:
                if p_ in fs: pred[a].add(p_)
        def depth(x, guard=()):
            if x not in pos:
                pos[x] = 1 + max((depth(y, guard + (x,)) for y in pred[x] if y not in guard), default=-1)
            return pos[x]
        for i in ids: depth(i)
    first = lambda i: obj(i).split(' ')[0]
    for i, d in G.QS.items():
        if i in ALIAS or in_guide(i) or d.get('hid') == 1 or G.playable(i): continue
        same = [c for c in mine[name(i)] if pos.get(c) == pos.get(i)]
        if len(same) > 1 and not all(c in EXCL[same[0]] for c in same[1:]):       # varias que se excluyen son la misma
            same = [c for c in same if first(c) == first(i)]
        if same and all(c in EXCL[same[0]] for c in same[1:]): ALIAS[i] = pick(i, same); ALIAS_WHY[i] = 'pos'
_variants()
if os.environ.get('ALIAS_DEBUG'):
    json.dump({str(k): [v, ALIAS_WHY.get(k, 'twin')] for k, v in ALIAS.items()}, open(os.environ['ALIAS_DEBUG'], 'w'))

def unknown_names():
    """Nombre y motivo de las quests de Questie que la guía no usa, para explicar las que salen al importar."""
    out = {}
    for i, d in G.QS.items():
        if in_guide(i) or i in ALIAS: continue
        why = ('O' if d.get('hid') == 1 else 'H' if d['side'] == 'H' else 'R' if not d['dwarf'] else 'C' if not d['shaman']
               else 'P' if G.other_skill(i) else 'T' if d['flags'] & 1 else 'Z' if d['lv'] > 0 else 'X')
        out[str(i)] = d['n'] + '|' + why
    return out

def repeatable(i):
    f = (G.QS.get(i) or {}).get('flags', 0)
    return 'REPEATABLE' in str(f).upper() if isinstance(f, (str, list, tuple)) else bool(int(f or 0) & 1)

def ancestors(i, acc=None):
    """Todo lo que hay que hacer antes de la quest i, sin orden."""
    acc = [] if acc is None else acc
    al, an = PRE.get(i, ([], []))
    for x in al + an:
        if x not in acc: acc.append(x); ancestors(x, acc)
    return acc

def topo(ids):
    """Ordena por requisitos: primero lo que no depende de nada; a igualdad, por nivel."""
    ids, depth = list(dict.fromkeys(ids)), {}
    def d(i, guard=()):
        if i in depth: return depth[i]
        al, an = PRE.get(i, ([], []))
        ps = [x for x in al + an if x in ids and x not in guard]
        depth[i] = 1 + max((d(x, guard + (i,)) for x in ps), default=0)
        return depth[i]
    return sorted(ids, key=lambda i: (d(i), Q[i].get('level') or 0, i))

def payoff(ids):
    """Qué se gana con una cadena: XP, reputación y premio del último paso."""
    qs = [Q[i] for i in ids if i in Q]
    xp = sum(q.get('xp') or 0 for q in qs)
    rep = defaultdict(int)
    for q in qs:
        for r in q.get('rep') or []:
            if (r.get('v') or 0) > 0: rep[r['name']] += r['v']
    out = []
    if xp: out.append(f'{xp:,} XP en total'.replace(',', '.'))
    top = sorted(rep.items(), key=lambda x: -x[1])[:2]
    if top: out.append('reputación: ' + ', '.join(f'+{v} {esc(n)}' for n, v in top))
    last = next((q for q in reversed(qs) if (q.get('choice') or q.get('items'))), None)
    if last:
        rw = reward_chips(last, 4)
        if rw: out.append(f'premio de {qa(last["id"])}: {rw}')
    return '; '.join(out)

DQ_OF, WINGS = {}, {}                      # quest de mazmorra -> clave de mazmorra; mazmorra -> claves de sus alas
for _d in DG:
    WINGS[_d[0]] = [w[0] for w in _d[8]]
    for _i in dungeon_quest_ids(_d[2], _d[6]): DQ_OF.setdefault(_i, _d[0])

def auto_chains(covered):
    """Cadenas previas a quests de mazmorra, según los requisitos de Questie, que no cubre ninguna cadena escrita a mano."""
    groups = []                                              # [conjunto de quests, mazmorras, quests finales]
    for t, gk in sorted(DQ_OF.items()):
        anc = ancestors(t)
        if not anc: continue
        ids = set(anc) | {t}
        hit = [g for g in groups if g[0] & ids]
        for g in hit:
            ids |= g[0]; groups.remove(g)
        groups.append([ids, sorted({gk} | {x for g in hit for x in g[1]}), sorted({t} | {x for g in hit for x in g[2]})])
    out = []
    for ids, dgs, targets in groups:
        if ids <= covered: continue
        order = topo(ids)
        lv = [Q[i]['level'] for i in order if Q[i].get('level')]
        last = order[-1]
        tn = ', '.join(dict.fromkeys(f'<em>{esc(Q[t]["name"])}</em>' for t in targets[:4])) + (' y otras' if len(targets) > 4 else '')
        out.append({'k': f'a{last}', 't': Q[last]['name'], 'g': 'Mazmorras', 'lv': f'{min(Q[i].get("min") or Q[i]["level"] for i in order)}-{max(lv)}',
                    'dg': dgs, 'auto': True, 's': [{'q': i} for i in order],
                    'why': f'Lo que hay que hacer antes para poder coger {tn}, de {" y ".join(esc(DG_NAME[g]) for g in dgs)}. '
                           'Si entras a la mazmorra sin estos pasos, esas quests no te aparecen. El orden sale de los requisitos de Questie.'})
    return out

QCHAIN = {}                                # quest -> (clave de cadena, número de paso, título)
CHAIN_IDS = {}                             # clave de cadena -> ids de quest de sus pasos
CHAIN_REQ = {}                             # lo mismo, sin los pasos opcionales

def imp_attr(implied, s):
    v = implied.get(s.get('q'))
    return f' data-imp="{",".join("q%d" % x for x in v)}"' if v else ''

def render_chains():
    """(páginas, datos para tarjetas, enlaces por zona, enlaces por mazmorra)"""
    pages, meta, byzone, bydg = [], [], defaultdict(list), defaultdict(list)
    covered = {s['q'] for ch in CHAINS for s in ch['s'] if 'q' in s}
    specs = CHAINS + auto_chains(covered)
    for ch in specs:
        ids = [s['q'] for s in ch['s'] if 'q' in s and s['q'] in Q]
        CHAIN_IDS[ch['k']] = ids
        for s in ch['s']:                                    # recado que solo lleva al paso siguiente: no es obligatorio
            if 'q' in s and BFOR.get(s['q']) in ids: s['bc'] = 1
        CHAIN_REQ[ch['k']] = [s['q'] for s in ch['s'] if 'q' in s and s['q'] in Q and not s.get('opt') and not s.get('bc')]
        for n, s in enumerate(ch['s'], 1):
            if 'q' in s: QCHAIN.setdefault(s['q'], (ch['k'], n, ch['t']))
    for ch in specs:
        lis, zsteps, seen, implied = [], {z: [] for z in ch.get('z', [])}, set(), {}
        qsteps = [x for x in ch['s'] if 'q' in x]
        for n, x in enumerate(qsteps):                       # pasos posteriores que dan este por superado
            if x.get('opt'): continue
            nxt, cur_ = set(), (G.QS.get(x['q']) or {}).get('next')
            while cur_ and cur_ not in nxt: nxt.add(cur_); cur_ = (G.QS.get(cur_) or {}).get('next')
            later = [y['q'] for y in qsteps[n + 1:] if not y.get('opt') and (x.get('bc') or y['q'] in nxt or x['q'] in ancestors(y['q']))]
            if later: implied[x['q']] = later
        inchain = [x['q'] for x in qsteps]
        for x in qsteps:
            alt = [e for e in EXCL.get(x['q'], ()) if e in inchain]
            for t in inchain:                                # dos requisitos alternativos de un mismo paso: con uno basta
                an = [a for a in PRE.get(t, ([], []))[1] if a in inchain]
                if len(an) > 1 and x['q'] in an: alt += [a for a in an if a != x['q']]
            if alt: implied[x['q']] = list(dict.fromkeys(implied.get(x['q'], []) + alt))
            if x.get('bc'): BREAD.add(x['q'])
        for i, s in enumerate(ch['s'], 1):
            note = linkify(s.get('d') or s.get('o') or '')
            obj = rw = lv = tag = need = ''
            if 'q' in s:
                q = Q[s['q']]; key = f'q{q["id"]}'
                title = qa(q['id'])
                if q.get('level'):
                    lv = f'nivel {q["level"]}' + (f', desde {q["min"]}' if q.get('min') and q['min'] < q['level'] else '')
                where = linkify(s['w']) if s.get('w') else step_where(q)
                obj = esc(G.clean(q.get('obj') or ''))
                rw = reward_chips(q, 3)
                if q['id'] in DQ_OF or q.get('type') == 'Dungeon': tag = '<span class="tag ty">mazmorra</span>'
                elif q.get('type') in QTYPE: tag = f'<span class="tag ty">{QTYPE[q["type"]]}</span>'
                if s.get('opt'): tag += '<span class="tag st">opcional</span>'
                if s.get('bc'): tag += '<span class="tag st">recado opcional</span>'
                al, an = PRE.get(q['id'], ([], []))
                miss = [x for x in al if x not in seen]
                if miss: need = 'Requiere antes: ' + ', '.join(qa(x) for x in miss) + '.'
                elif an and not any(x in seen for x in an):
                    need = ('Requiere antes: ' if len(an) == 1 else 'Requiere antes una de estas: ') + ', '.join(qa(x) for x in an) + '.'
                seen.add(q['id'])
                if not s.get('w'):
                    for c in (q.get('sc'), q.get('ec')):
                        z = MAP2ZONE.get(c[2]) if c else None
                        if z and i not in zsteps.setdefault(z, []): zsteps[z].append(i)
            else:
                key = f'c-{ch["k"]}-{s["x"]}'; title = f'<b>{esc(s["n"])}</b>'; where = linkify(s.get('w', ''))
            lis.append(
                f'<li{imp_attr(implied, s)}><label class="cs-n"><input type="checkbox" data-k="{key}" aria-label="Paso {i} hecho"><span data-n="{i}"></span></label>'
                f'<div class="cs-b"><div class="cs-t">{title}' + (f'<span class="lv">{lv}</span>' if lv else '') + tag + '</div>'
                + (f'<p class="cs-w">{where}</p>' if where else '')
                + (f'<p class="cs-o">{obj}</p>' if obj else '')
                + (f'<p class="cs-d">{note}</p>' if note else '')
                + (f'<p class="cs-need">{need}</p>' if need else '')
                + (f'<p class="cs-r">Premio: {rw}</p>' if rw else '') + '</div></li>')
        for z, nums in zsteps.items():
            byzone[z].append(chain_link(ch, f'aquí: paso{"s" if len(nums) > 1 or "-" in runs(nums) else ""} {runs(nums)}' if nums else 'pasa por aquí'))
        for g in ch.get('dg', []):
            bydg[g].append(chain_link(ch))
        ids = CHAIN_IDS[ch['k']]
        after = [x for x in dict.fromkeys(j for i in ids for j in SUCC.get(i, [])) if x not in ids and not repeatable(x)]
        zl = ', '.join(f'<a href="#z-{slug(z)}">{esc(z)}</a>' for z in zsteps)
        dl = ', '.join(f'<a href="#dg-{g}">{esc(DG_NAME[g])}</a>' for g in ch.get('dg', []))
        gain = payoff(ids)
        a, b = lv_nums(ch['lv'])
        sub = ' · '.join(DG_NAME[g] for g in ch.get('dg', [])) if ch.get('auto') else ''
        pages.append(f'''
<article class="page cpage" id="cad-{ch["k"]}" data-name="{esc(ch["t"])}" data-lv="{ch["lv"]}" hidden>
<header class="ph">
<div class="crumb"><a href="#cadenas">Cadenas</a><span>›</span>{esc(ch["t"])}</div>
<h2>{esc(ch["t"])}</h2>
<div class="ph-meta"><span class="lv">{ch["lv"]}</span><span>{esc(sub or ch["g"])}</span><span>{len(lis)} pasos</span><span class="cprog"></span></div>
</header>
<section class="blk why"><h3>Por qué hacerla</h3><p>{linkify(ch["why"])}</p>
{f'<p class="gain"><b>Qué ganas:</b> {gain}.</p>' if gain else ''}
{f'<p class="src">Pasa por: {zl}.</p>' if zl else ''}{f'<p class="src">Mazmorra: {dl}.</p>' if dl else ''}</section>
<section class="blk csteps"><h3>Pasos <span class="prog"></span></h3>
<p class="src">Marca cada paso al entregarlo. El siguiente que te toca queda resaltado. El texto en inglés es el objetivo tal como sale en el juego.</p>
<ol class="chain">{"".join(lis)}</ol>
{f'<p class="after"><b>Al terminar se abre:</b> {", ".join(qa(x) for x in after[:8])}.</p>' if after else ''}</section>
</article>''')
        meta.append({'k': ch['k'], 't': ch['t'], 'g': ch['g'], 'lv': ch['lv'], 'a': a, 'b': b, 'n': len(lis), 'sub': sub, 'ids': ids, 'im': {str(k): v for k, v in implied.items()}})
    order = ['Tu chamán', 'Tu personaje', 'Mazmorras', 'Zonas']
    meta.sort(key=lambda m: (order.index(m['g']), m['a'] or 0, m['b'] or 0))
    return ''.join(pages), meta, byzone, bydg

def chains_block(links, title='Cadenas paso a paso'):
    return f'<section class="blk zchains"><h3>{title}</h3><ul class="clinks">{"".join(links)}</ul></section>' if links else ''

# casilla de la checklist -> zonas en cuya página aparece
IMP_MAP = {}
def _imp(keys, *zones):
    for k in keys.split(): IMP_MAP[k] = list(zones)
_imp('dm1 dm2 dm3 dm5', 'Dun Morogh'); _imp('dm4 dm6', 'Ironforge'); _imp('lm1 lm2 lm3 lm4 lm5', 'Loch Modan'); _imp('ds1 ds2 ds3', 'Darkshore')
_imp('ew1 ew2', 'Elwynn Forest'); _imp('wf1 wf2 wf3 wf4 wf5 wf6', 'Westfall'); _imp('rr1 rr2 rr3 rr4', 'Redridge Mountains')
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
DONE_DEFAULT = set()

# explorar: el mismo punto en todas las zonas con mapa
EXPLORE = ('<li class="man"><label><input type="checkbox" data-k="{k}"><span><b>Exploración</b>: descubre todas las subzonas del mapa de {name}.</span></label>'
           '<div class="imp-d"><p class="imp-s" aria-live="polite"></p><dl class="imp-g">'
           '<dt>Por qué</dt><dd>Cada subzona que pisas por primera vez da experiencia. Y descubrir el mapa entero del mundo con un mismo personaje es uno de los retos de Legacy, '
           '«Explore the world», que vale 1 punto de cuenta. Cuentan todas las zonas: con una sola a medias no hay punto. '
           'El recuento de todas está en <a href="#legacy">Sistema Legacy</a>.</dd>'
           '<dt>Cómo</dt><dd>Abre el mapa con la tecla M: lo que no has pisado sale tapado. Al entrar en una subzona nueva aparece su nombre en pantalla y recibes la experiencia. '
           'Suele quedar algún rincón lejos de los caminos y de las quests: repasa el mapa antes de dar la zona por terminada.</dd></dl></div></li>')

# casilla -> de qué depende, cuando no se deduce bien del texto ([] = manual)
_tok = lambda x: x if isinstance(x, str) else '|'.join(f'q{i}' for i in x) if isinstance(x, tuple) else f'q{x}'
DEP_MAP = {k: [_tok(i) for i in v] for k, v in {
    'wl1': [94495, 94497], 'rr3': [94499], 'av1': [94500], 'lm5': [94494], 'lm4': [94465, 94466, 94467, 94468], 'dm6': [],
    'wf5': [79008], 'bs1': [79192, 79980], 'lm3': [79974], 'ar2': [79975, 79976],
    'ar1': [94789], 'tw1': [96264], 'tw2': [79358], 'tw3': [96135], 'tw4': [96016],
    'rt1d': [96392, 96390, 96391], 'rt3a': [94465, 94466, 94467, 94468], 'rt4d': [79008], 'rt4e': [168, 167, 2040],
    'rt6b': [94494, 94495, 94497], 'rt6c': [94499], 'rt6d': [94500], 'rt6e': [79192, 79980, 79974, 79975, 79976], 'rt6f': [94501, 94502, 94503, 94505],
    'rt8b': [94789], 'rt8c': [96264], 'rt8e': [79358, 96135, 96016],
    'wf3': [214], 'wf4': [153], 'wf6': [92744], 'rt11d': [],
    # puntos que eran manuales y son en realidad una quest
    'ds1': [1275], 'bd3': [1393], 'rg4': [94980], 'ar3': [685], 'sg3': [3801, 3802, 7848], 'sg2': [4363, 4126], 'dm4': [(2926, 2927), 971, 1050],
    'rt5a': [65], 'bs2': ['dg-wailing-caverns'], 'sd1': [208], 'rt12a': [3962], 'pl4': [5944], 'pl1': [(5401, 5405, 5503)],
    'rt13a': [(5401, 5405, 5503), 5505], 'rt11e': [(4022, 4023)],
    # casillas de las páginas de profesiones
    'pfc1': [96608, 96629], 'pfc2': [], 'pfc3': [], 'pfc4': [6610], 'pfp1': [], 'pfp2': [96050], 'pfp3': [], 'pfp4': [6607],
    'pfa1': [], 'pfa2': [96047], 'pfa3': [], 'pfa4': [6624], 'pfm1': [96046], 'pfe1': [96058],
    'rt1a': [233, 234], 'dm3': [233, 234], 'rt1f': [], 'rt2a': [], 'rt2b': [], 'rt2c': [], 'rt3b': [], 'rt3d': [], 'rt4a': [], 'rt6a': [], 'ew3': [],
}.items()}
NAME_IDS = defaultdict(list)
for _i in Q:
    if in_guide(_i): NAME_IDS[G.norm(Q[_i]['name'])].append(_i)
DEPS_SEEN = {}

# ---- por qué importa cada imprescindible: motivo escrito a mano y datos del premio sacados del juego
WHYS = json.load(open(os.path.join(ROOT, 'data', 'imprescindibles.json'), encoding='utf-8'))
SLOT = {'Two-Hand': 'dos manos', 'One-Hand': 'una mano', 'Main Hand': 'mano principal', 'Off Hand': 'mano secundaria', 'Held In Off-hand': 'mano secundaria',
        'Ranged': 'a distancia', 'Head': 'cabeza', 'Shoulder': 'hombros', 'Chest': 'pecho', 'Wrist': 'muñecas', 'Hands': 'manos', 'Waist': 'cintura',
        'Legs': 'piernas', 'Feet': 'pies', 'Back': 'capa', 'Finger': 'anillo', 'Neck': 'collar', 'Trinket': 'abalorio', 'Relic': 'reliquia'}
KINDW = {'Mace': 'maza', 'Axe': 'hacha', 'Sword': 'espada', 'Staff': 'bastón', 'Dagger': 'daga', 'Fist Weapon': 'arma de puño', 'Polearm': 'arma de asta',
         'Shield': 'escudo', 'Cloth': 'tela', 'Leather': 'cuero', 'Mail': 'malla', 'Plate': 'placas', 'Gun': 'arma de fuego', 'Bow': 'arco',
         'Crossbow': 'ballesta', 'Wand': 'varita', 'Totem': 'totem'}
STAT = {'Strength': 'Fuerza', 'Agility': 'Agilidad', 'Stamina': 'Aguante', 'Intellect': 'Intelecto', 'Spirit': 'Espíritu'}
NO_USE = {'Sword', 'Polearm', 'Gun', 'Bow', 'Crossbow', 'Wand', 'Plate'}

def item_note(iid):
    """(descripción corta de un objeto, si le sirve a un chamán de Mejora): 'top', 'ok', 'mail' (desde 40) o 'no'."""
    tip = G.item_tip(iid)
    if not tip: return '', None
    slot = kind = speed = dps = cls = ''
    stats = []
    for l in tip['l']:
        if ' · ' in l and 'Damage' not in l and not slot:
            a, b = [x.strip() for x in l.split(' · ', 1)]
            if a in SLOT: slot, kind = a, b
        elif l in SLOT and not slot: slot = l
        m = re.search(r'Speed (\d+\.\d+)', l)
        if m: speed = m.group(1)
        m = re.match(r'\((\d+(?:\.\d+)?) damage per second\)', l)
        if m: dps = m.group(1)
        m = re.match(r'\+(\d+) (Strength|Agility|Stamina|Intellect|Spirit)$', l)
        if m: stats.append(f'+{m.group(1)} {STAT[m.group(2)]}')
        m = re.search(r'Increases attack power by (\d+)', l)
        if m: stats.append(f'+{m.group(1)} poder de ataque')
        if l.startswith('Classes:'): cls = l[8:].strip()
    parts = []
    weapon = slot in ('Two-Hand', 'One-Hand', 'Main Hand', 'Off Hand', 'Ranged') and kind in KINDW and kind != 'Shield'
    if weapon: parts.append(KINDW[kind] if slot == 'Ranged' else f'{KINDW[kind]} de {SLOT[slot]}')
    elif kind == 'Shield': parts.append('escudo')
    elif kind in KINDW: parts.append(f'{SLOT.get(slot, slot.lower())}, {KINDW[kind]}')
    elif slot: parts.append(SLOT[slot])
    if speed: parts.append(f'velocidad {speed}')
    if dps: parts.append(f'{dps} de daño por segundo')
    parts += stats[:4]
    use = ('no' if kind in NO_USE or (cls and 'Shaman' not in cls) else 'mail' if kind == 'Mail'
           else 'top' if slot == 'Two-Hand' and kind in ('Mace', 'Axe') else 'ok')
    return ', '.join(parts), use

USE_TXT = {'no': ' <i class="no">no la puedes usar</i>', 'mail': ' <i>malla: desde nivel 40</i>', 'top': ' <i class="top">dos manos de las tuyas</i>'}

def imp_detail(key, deps, zone=None):
    """(bloque de detalle de un imprescindible, nivel mínimo para empezarlo): estado, cuándo, por qué, qué hay que hacer, premio y datos."""
    ids = [int(t.split('|')[0][1:]) for t in deps if t[0] == 'q']
    ids = [i for i in ids if i in Q]
    rows, mn = [], None
    if ids:
        mn = min((Q[i].get('min') or Q[i].get('level') or 99) for i in ids)
        lo, hi = min(Q[i]['level'] for i in ids), max(Q[i]['level'] for i in ids)
        when = f'Se puede coger desde nivel {mn}. ' + (f'Es de nivel {lo}' if lo == hi else f'Sus quests van de nivel {lo} a {hi}') + ': con menos nivel que ese, sus enemigos te quedan grandes.'
        if zone and zone[1] and mn > zone[1] + 2:
            when += f' Se coge en esta zona, pero no al nivel de la zona ({zone[0]}-{zone[1]}): vuelve cuando tengas nivel {mn}.'
        def dg_ref(g):
            w = next(d[8] for d in DG if d[0] == g)
            return f'<a href="#dg-{g}">{esc(DG_NAME[g])}</a> (niveles {min(x[2] for x in w)}-{max(x[3] for x in w)})'
        # dentro de la mazmorra de verdad, o solo un paso previo que lleva a ella
        inside = list(dict.fromkeys(DQ_OF[i] for i in ids if i in DQ_OF and (Q[i].get('type') == 'Dungeon' or DGZ.get(Q[i].get('zone')) == DQ_OF[i])))
        lead = [g for g in dict.fromkeys(DQ_OF[i] for i in ids if i in DQ_OF) if g not in inside]
        if inside: when += ' Se resuelve dentro de ' + ' y '.join(dg_ref(g) for g in inside) + ': llévala cogida antes de entrar.'
        if lead: when += ' Es un paso previo a las quests de ' + ' y '.join(dg_ref(g) for g in lead) + '.'
        rows.append(('Cuándo', when))
    if WHYS.get(key): rows.append(('Por qué', linkify(WHYS[key])))
    if ids:
        if len(ids) <= 4:
            lines = []
            for i in ids:
                q = Q[i]
                who = step_where(q)
                lines.append(f'<li>{qa(i)} <span class="lv">nivel {q["level"]}</span>: {esc(G.clean(q.get("obj") or "")) or "sin objetivo en los datos"}' + (f' <span class="in">{who}</span>' if who else '') + '</li>')
            rows.append(('Qué hay que hacer', '<ul class="imp-q">' + ''.join(lines) + '</ul>'))
        else:
            q = Q[ids[0]]
            rows.append(('Qué hay que hacer', f'Son {len(ids)} quests seguidas. Empieza con {qa(ids[0])}: {esc(G.clean(q.get("obj") or ""))} <span class="in">{step_where(q)}</span> El resto, paso a paso, en su cadena.'))
    prize = []
    for q in [Q[i] for i in ids if (Q[i].get('choice') or Q[i].get('items'))][-2:]:
        bits = []
        for it in ((q.get('choice') or []) + (q.get('items') or []))[:5]:
            if not it.get('id') or not it.get('name'): continue
            note, use = item_note(it['id'])
            bits.append(ia(it['id'], it['name']) + (f' <span class="in">({note})</span>' if note else '') + USE_TXT.get(use, ''))
        if bits: prize.append(('A elegir' if q.get('choice') else 'Te dan') + (f' en {qa(q["id"])}' if len(ids) > 1 else '') + ': ' + '; '.join(bits) + '.')
    if prize: rows.append(('Premio', '<br>'.join(prize)))
    facts = []
    if ids:
        xp = sum(Q[i].get('xp') or 0 for i in ids)
        if xp: facts.append(f'{xp:,} XP'.replace(',', '.') + (' en total' if len(ids) > 1 else ''))
        rep = defaultdict(int)
        for i in ids:
            for r in Q[i].get('rep') or []:
                if (r.get('v') or 0) > 0: rep[r['name']] += r['v']
        if rep:
            n, v = max(rep.items(), key=lambda x: x[1]); facts.append(f'+{v} de reputación con {esc(n)}')
        after = [x for x in dict.fromkeys(j for i in ids for j in SUCC.get(i, [])) if x not in ids and not repeatable(x)][:3]
        if after: facts.append('al terminarla se abre ' + ', '.join(qa(x) for x in after))
    if facts: rows.append(('Además', ' · '.join(facts) + '.'))
    if not rows: return '', mn
    return ('<div class="imp-d"><p class="imp-s" aria-live="polite"></p><dl class="imp-g">'
            + ''.join(f'<dt>{k}</dt><dd>{v}</dd>' for k, v in rows) + '</dl></div>'), mn

def deps_for(key, inner):
    """Claves de las casillas de las que depende un punto de la guía: sus quests o, si solo nombra una mazmorra, sus alas."""
    if key in DEP_MAP: out = DEP_MAP[key]
    else:
        cads = re.findall(r'href="#cad-([a-z0-9]+)"', inner)
        ids = list(dict.fromkeys(i for c in cads for i in CHAIN_REQ.get(c, [])))
        if not ids:
            for i in map(int, re.findall(r'data-t="quest" data-id="(\d+)"', inner)):
                if in_guide(i):
                    for j in sorted(NAME_IDS[G.norm(Q[i]['name'])]):
                        if j not in ids and j not in BREAD: ids.append(j)
        out = req_tokens(ids)
        if not out:
            out = [f'dg-{w}' for g in dict.fromkeys(re.findall(r'href="#dg-([a-z0-9-]+)"', inner)) for w in WINGS.get(g, [])]
    DEPS_SEEN[key] = out
    return out

def dep_attr(key, inner):
    d = deps_for(key, inner)
    return f' data-dep="{",".join(d)}"' if d else ''

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
<a class="brand" href="#inicio"><svg viewBox="0 0 20 30" aria-hidden="true"><path fill="var(--air)" d="M5 0h10l2 2v5H3V2z"/><path fill="var(--water)" d="M2 8h16v6H2z"/><path fill="var(--fire)" d="M3 15h14v6H3z"/><path fill="var(--earth)" d="M3 22h14l3 3v5H0v-5z"/></svg>Enano Chamán<span>WoW Forever</span></a>
<nav class="tabs" aria-label="Secciones">
<a href="#inicio" data-view="inicio">Inicio</a><a href="#zonas" data-view="zonas">Zonas</a><a href="#mazmorras" data-view="mazmorras">Mazmorras</a><a href="#cadenas" data-view="cadenas">Cadenas</a><a href="#quests" data-view="quests">Quests</a><a href="#chaman" data-view="chaman">Tu chamán</a><a href="#profesiones" data-view="profesiones">Profesiones</a><a href="#referencia" data-view="referencia">Referencia</a>
</nav>
<div class="top-tools">
<label class="lvl" for="nivel">Nivel<input id="nivel" type="number" min="1" max="60" value="1" inputmode="numeric"></label>
<div class="search"><input id="buscar" type="search" placeholder="Buscar quest, zona, jefe, objeto…" autocomplete="off" aria-label="Buscar en la guía"><div id="results" hidden></div></div>
<details class="cfg"><summary>Ajustes</summary><div class="cfg-body">
<label for="fichas">Abrir fichas en</label>
<select id="fichas"><option value="wh">Wowhead</option><option value="whes">Wowhead en español</option><option value="wdb">Warcraft DB</option></select>
<div id="progreso" class="prog-box" aria-live="polite"></div>
<button id="imprimir" type="button">Imprimir o guardar PDF</button>
<p><a href="#importar">Importar quests completadas desde Questie</a></p>
<p>Las casillas se guardan en este navegador. Para llevarlas a otro dispositivo, copia este código y cárgalo allí.</p>
<textarea id="sync-code" rows="3" spellcheck="false" aria-label="Código de progreso"></textarea>
<div class="sync-btns"><button id="sync-copy" type="button">Copiar código</button><button id="sync-load" type="button">Cargar código</button></div>
<div id="sync-msg" aria-live="polite"></div>
</div></details>
</div></div>
<div class="rail" aria-hidden="true"><i></i><b class="e1" style="--at:4"></b><b class="e2" style="--at:10"></b><b class="e3" style="--at:20"></b><b class="e4" style="--at:30"></b><b style="--at:40"></b><b style="--at:60"></b></div>
</header>'''

IMPORT_HTML = '''<section id="importar" class="sec">
<h2>Importar tu progreso del juego</h2>
<p>Las casillas de quests de la guía usan el mismo número de quest que el juego. Por eso se pueden marcar solas a partir de la lista de quests que tu personaje ya ha completado. El archivo se lee en tu navegador y no se envía a ningún sitio; las marcas se guardan, como siempre, en este navegador.</p>
<h3>Con Questie</h3>
<ol>
<li>En el juego, escribe <code>/reload</code> o sal del personaje. Los addons solo guardan sus datos en disco en ese momento.</li>
<li>En el ordenador donde juegas, busca dentro de la carpeta del juego: <code>WTF</code> › <code>Account</code> › tu cuenta › <code>SavedVariables</code> › <code>Questie.lua</code>.</li>
<li>Elige ese archivo aquí abajo y pulsa el botón.</li>
</ol>
<div class="imp-box">
<input id="imp-file" type="file" accept=".lua,.txt,text/plain" aria-label="Archivo de Questie">
<select id="imp-char" aria-label="Personaje" hidden></select>
<h3>O pegando una lista</h3>
<p class="src">Si tienes los números de las quests completadas por otra vía, pégalos separados por comas o espacios.</p>
<textarea id="imp-ids" rows="2" spellcheck="false" placeholder="65, 132, 135, 141…" aria-label="Lista de números de quest"></textarea>
<div class="sync-btns"><button id="imp-go" type="button">Marcar las quests completadas</button></div>
<div id="imp-msg" aria-live="polite"></div>
<details id="imp-unk-box" hidden><summary><span id="imp-unk-n"></span> quests completadas que la guía no usa</summary>
<p class="src"><b id="imp-unk-sum"></b></p>
<p class="src">Cada una va con su nombre y el motivo. El juego da por hechas las versiones de otras razas de las quests que completas, y la guía ya las cuenta como la tuya: aquí quedan solo las que no sabe emparejar, además de eventos, repetibles y quests retiradas. La lista se guarda en este navegador. Si alguna te parece que debería estar, cópiala y pásala para revisarla.</p>
<textarea id="imp-unk" rows="6" readonly spellcheck="false" aria-label="Quests completadas que la guía no usa"></textarea>
<div class="sync-btns"><button id="imp-unk-copy" type="button">Copiar la lista</button></div></details>
</div>
<p class="src">Solo añade marcas, nunca quita. Marca las quests de las listas de cada zona y los pasos de las cadenas. Los imprescindibles y la ruta del inicio no son quests sueltas: esos se marcan a mano. El formato del archivo es el de Questie para Classic; si el de Forever cambia y no reconoce tu archivo, el mensaje lo dirá.</p>
</section>'''

NOW_HTML = '''<section id="ahora" class="sec">
<h2>Ahora, con nivel <span id="now-lvl">1</span></h2>
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
    body = re.sub(r'\[\[cad:([a-z]+)(?:\|([^\]]+))?\]\]', lambda m: f'<a class="cgo" href="#cad-{m.group(1)}">{m.group(2) or "ver los pasos"}</a>', body)
    # casillas de las páginas de profesiones: dependen de su quest o se marcan a mano
    body = re.sub(r'<li>(<label><input type="checkbox" data-k="(pf[a-z0-9]+)")(><span>)(.*?)(</span></label></li>)',
                  lambda m: ('<li>' if deps_for(m.group(2), m.group(4)) else '<li class="man">') + m.group(1) + dep_attr(m.group(2), m.group(4)) + m.group(3) + m.group(4) + m.group(5),
                  body, flags=re.S)
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

    cpages, cmeta, czone, cdg = render_chains()
    secs['ruta'] = re.sub(r'<li>(<label><input type="checkbox" data-k="(rt[0-9a-z]+)")(><span>)(.*?)(</span></label></li>)',
                          lambda m: ('<li class="man">' if not deps_for(m.group(2), m.group(4)) else '<li class="mand">' if all(d.startswith('dg-') for d in deps_for(m.group(2), m.group(4))) else '<li>') + m.group(1) + dep_attr(m.group(2), m.group(4)) + m.group(3) + m.group(4) + m.group(5),
                          secs.get('ruta', ''), flags=re.S)
    secs['ruta'] = secs['ruta'].replace('<ol class="steps">', '<p class="man-up"><button id="man-up" type="button" hidden></button></p>\n<ol class="steps">', 1)
    zpages, zdash = [], []
    for z in zones:
        name = z['name']
        dbz, wslug = z.get('extra') or ZONES[name]
        lst, n = zone_list(name, dbz, wslug)
        zid, a, b = 'z-' + slug(name), *lv_nums(z['lv'])
        items = imp.get(name, [])
        imp_html = ''
        now, later = [], []
        for k, inner in items:
            det, mn = imp_detail(k, deps_for(k, inner), (a, b))
            row = f'<li{"" if deps_for(k, inner) else " class=man"}><label><input type="checkbox" data-k="{k}"{dep_attr(k, inner)}><span>{inner}</span></label>{det}</li>'
            (later if mn and b and mn > b + 2 else now).append(row)
        if 'ciudad' not in z['lv']:                          # explorar el mapa cuenta en todas las zonas, no solo en una
            now.append(EXPLORE.format(k='xpl-' + slug(name), name=esc(name)))
        if now or later:
            lis = ''.join(now) + (f'<li class="imp-later">Para más adelante: se cogen aquí, pero piden más nivel del que tiene la zona</li>' + ''.join(later) if later else '')
            imp_html = (f'<section class="blk imp"><h3>Imprescindibles <span class="prog"></span></h3>'
                        f'<ul class="chk">{lis}</ul>{paras.get(name, "")}</section>')
        guide = (f'<a href="https://wowforeverinfo.com/guides/{wslug}/" target="_blank" rel="noopener">Guía paso a paso</a>') if wslug else ''
        dl = f' data-lv="{z["datalv"]}"' if z['datalv'] else ''
        chk = ' checked' if name in DONE_DEFAULT else ''
        title = 'Qué hay aquí' if 'extra' in z else 'Ruta por la zona'
        zpages.append(f'''
<article class="page zpage" id="{zid}" data-name="{esc(name)}"{dl} hidden>
<header class="ph">
<div class="crumb"><a href="#zonas">Zonas</a><span>›</span>{esc(name)}</div>
<h2>{esc(name)}</h2>
<div class="ph-meta"><span class="lv">{esc(z["lv"])}</span><span>{z["base"]}</span>{'<span class="tag new">nueva</span>' if z["new"] else ''}{guide}</div>
<div class="dones"><label class="done"><input type="checkbox" data-k="zdone-{slug(name)}" data-zdone="{zid}"{chk}> Zona completada</label></div>
</header>
{imp_html}
{chains_block(czone.get(name))}
<section class="blk ruta"><h3>{title}</h3>{z["body"]}</section>
{lst}
</article>''')
        zdash.append({'id': zid, 'n': name, 'lv': z['lv'], 'a': a, 'b': b, 'base': html.unescape(re.sub(r'<[^>]+>', '', z['base'])),
                      'grp': bracket(a), 'new': 1 if z['new'] else 0, 'imp': len(items), 'q': n})

    dungeons, dash = render_dungeons()
    for gk, links in cdg.items():
        dungeons, k = re.subn(r'(<article class="page dpage" id="dg-%s".*?</header>)' % re.escape(gk),
                              lambda m: m.group(1) + '\n' + chains_block(links, 'Cadenas que acaban aquí'), dungeons, count=1, flags=re.S)
        assert k == 1, gk
    secs['explorar'] = '<h2>Exploración y reputaciones</h2>' + explore if explore else ''
    secs['importar'] = re.sub(r'^<section[^>]*>|</section>$', '', IMPORT_HTML.strip())
    sec = lambda sid: f'<section id="{sid}" class="sec">{secs[sid]}</section>' if secs.get(sid) else ''
    def hub(view, title, intro, items):
        """Vista con tarjetas arriba y una página por apartado."""
        cards, pages = [], []
        for sid, desc in items:
            src = secs.get('zonas' if sid == 'tabla-zonas' else sid)
            if not src: continue
            m = re.search(r'<h2>(.*?)</h2>', src, re.S)
            name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            cards.append(f'<a class="card" href="#{sid}"><span class="c-h"><b>{esc(name)}</b></span><span class="c-s">{desc}</span></a>')
            pages.append(f'<article class="page spage" id="{sid}" data-name="{esc(name)}" hidden><header class="ph"><div class="crumb"><a href="#{view}">{title}</a>'
                         f'<span>›</span>{esc(name)}</div><h2>{name}</h2></header>{src[:m.start()] + src[m.end():]}</article>')
        return (f'<section class="view" id="v-{view}" hidden>\n<div class="overview"><h2 class="vh">{title}</h2>\n<p class="intro">{intro}</p>\n'
                f'<div class="cards hubcards">{"".join(cards)}</div></div>\n{"".join(pages)}\n</section>')
    views = f'''
<section class="view" id="v-inicio">
{hero}
{NOW_HTML.split('<section id="tus-pendientes"')[0]}
<section id="tu-muro" class="sec">
<h2>Tu muro de gestas</h2>
<p class="insc" id="insc-ini"></p>
<div class="friso" id="friso-ini"></div>
<p class="src">Los enanos no apuntan sus hazañas: las tallan. Cada asta es una de tus cadenas, y se va dorando paso a paso. <a href="#muro">Entra a ver el muro entero</a>, con una runa por cada quest del juego.</p>
</section>
{sec('ruta')}
<section id="tus-pendientes"{NOW_HTML.split('<section id="tus-pendientes"')[1]}
</section>
<section class="view" id="v-zonas" hidden>
<div class="overview"><h2 class="vh">Zonas</h2>
<p class="intro">Una página por zona con sus imprescindibles, sus cadenas, su ruta y todas sus quests. Las de tu nivel van resaltadas.</p>
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
<section class="view" id="v-cadenas" hidden>
<div class="overview"><h2 class="vh">Cadenas paso a paso</h2>
<p class="intro">Las quests encadenadas, con cada paso numerado: quién lo da, dónde se entrega, qué hay que hacer y qué ganas. El orden sale de los requisitos de Questie. Están las de tu clase, las que llevan a cada mazmorra y las largas de cada zona.</p>
<div id="ccards"></div>
<h3 class="cg">Más cadenas, por zona</h3>
<p class="src">Todas las demás quests con requisitos. Cada una abre su ficha con lo que hay que hacer antes.</p>
<div id="zchains"></div></div>
{cpages}
</section>
<section class="view" id="v-quests" hidden>
<div class="overview"><h2 class="vh">Todas las quests</h2>
<p class="intro">La base de datos completa de lo que puede hacer un enano chamán. Cada quest es una sola ficha: si la marcas aquí, queda marcada en su zona, en su cadena, en su mazmorra y en los imprescindibles. Y al revés.</p>
<div class="qf">
<input id="qf-text" type="search" placeholder="Nombre de la quest o de quien la da…" autocomplete="off" aria-label="Filtrar por nombre">
<select id="qf-zone" aria-label="Zona"><option value="">Todas las zonas</option></select>
<select id="qf-state" aria-label="Estado"><option value="">Hechas y pendientes</option><option value="a">Puedo cogerlas ahora</option><option value="p">Pendientes</option><option value="d">Hechas</option></select>
<select id="qf-kind" aria-label="Tipo"><option value="">Todos los tipos</option><option value="im">Imprescindibles</option><option value="ch">Con cadena</option><option value="dg">De mazmorra</option><option value="cl">De clase</option><option value="nw">Nuevas en Forever</option><option value="el">Élite o de grupo</option></select>
<label class="qf-lv"><input id="qf-level" type="checkbox"> Solo las de mi nivel</label>
</div>
<div id="qstats" class="src" aria-live="polite"></div>
<ul class="chk ql" id="qlist"></ul>
<button id="qmore" type="button" hidden>Ver más</button></div>
<article class="page qpage" id="qdetail" data-name="" hidden></article>
</section>
<section class="view" id="v-muro" hidden>
<div class="muro">
<p class="eyebrow">Sala de los Thanes · Ironforge</p>
<h2 class="vh">El muro de gestas</h2>
<p class="insc" id="insc"></p>
<div class="muro-tools">
<label for="nombre">Nombre de tu enano <input id="nombre" type="text" maxlength="24" autocomplete="off" placeholder="sin nombre"></label>
<label class="qf-lv" for="cincel"><input id="cincel" type="checkbox"> Oír el cincel al tallar</label>
<span id="muro-new" class="src" aria-live="polite"></span>
</div>
<p class="intro">Los enanos no apuntan sus hazañas: las tallan. Este muro tiene una runa por cada quest que puede hacer tu personaje. Las que aún no has hecho están solo marcadas a punzón; cada quest que entregas se talla y se rellena de oro. Pasa por encima de una runa para saber cuál es, y entra en ella para ver su ficha.</p>
<details class="leer"><summary>Cómo se leen las runas</summary><div id="leyenda"></div></details>
<h3>Las sagas</h3>
<p class="src">Cada cadena es una runa ligada: un asta con un trazo por paso, de abajo arriba. Las más altas son las cadenas más largas.</p>
<div class="friso" id="friso"></div>
<h3>Las gestas, zona a zona</h3>
<div id="muro"></div>
</div>
</section>
{hub('chaman', 'Tu chamán', 'Cómo se juega la clase, dónde poner los talentos, qué arma llevar y qué hay que comprar o entrenar.', [
    ('basico', 'Totems, imbuir el arma, shocks y por qué llevas un arma lenta.'),
    ('clase', 'Las quests que te dan cada totem y tu arma.'),
    ('talentos', 'Dónde poner cada punto de 10 a 60 y por qué.'),
    ('rotacion', 'Qué pulsar al questear y qué estadísticas buscar.'),
    ('armas', 'La mejor arma de dos manos de cada tramo y dónde sale.'),
    ('rol', 'Curar o tanquear en mazmorras y los totems que salvan al grupo.'),
    ('compras', 'Lo que hay que pagar o ir a aprender: armas, hechizos, montura.'),
    ('personaje', 'Bolsa de dormir, cocina, campamentos y ventajas de enano.'),
    ('legacy', 'El sistema de puntos de cuenta y qué talentos convienen.')])}
{hub('profesiones', 'Profesiones', 'Minería e Ingeniería, y las tres secundarias que no ocupan hueco: qué rango toca a cada nivel, qué fabricar y qué hay que ir a buscar.', [
    ('prof-plan', 'Rangos, entrenadores, precios y la habilidad que conviene llevar a cada nivel.'),
    ('mineria', 'Qué mineral buscar en cada tramo y en qué zonas.'),
    ('ingenieria', 'Qué fabricar para subir de 1 a 300, especialización y qué guardar.'),
    ('cocina', 'Secundaria. La comida da experiencia y el cocinero enciende la hoguera del campamento.'),
    ('pesca', 'Secundaria. Dónde pescar, cebos y el Fish Bowl, que da un 8% a todo.'),
    ('auxilios', 'Secundaria. Vendas con tu tela y, en Forever, las pociones de curación.'),
    ('prof-quests', 'Quests que piden barras o inventos tuyos: guárdalos al fabricarlos.')])}
{hub('referencia', 'Referencia', 'Material de consulta: vocabulario, tablas, llaves, estado del juego y fuentes.', [
    ('vocabulario', 'Las palabras del juego que usa la guía.'),
    ('importar', 'Marca solas las quests completadas a partir de Questie.'),
    ('plan', 'El plan maestro por tramos de nivel.'),
    ('tabla-zonas', 'Todas las zonas en una tabla, con lo que aporta cada una.'),
    ('llaves', 'Llaves de mazmorra y cadenas que saltan de una mazmorra a otra.'),
    ('estado', 'Cómo está el juego y los últimos hotfixes que te afectan.'),
    ('explorar', 'Lo que aporta explorar: reputaciones, barcos y rincones.'),
    ('pendiente', 'Lo que ninguna fuente confirma todavía.'),
    ('fuentes', 'De dónde sale cada dato y cómo abrir las fichas.')])}'''
    foot = re.search(r'<footer>.*?</footer>', body, re.S)
    main = f'{TOP}\n<div class="shell"><aside class="side" id="side" aria-label="En esta sección"></aside>\n<main>{views}\n{foot.group(0) if foot else ""}</main></div>'

    for i in list(USED_Q):
        k = chain_info(Q[i]) if i in Q else None
        if k:
            for j in (k[3], k[4]):
                if j: USED_Q.add(j)
    IMQ = {int(t[1:]) for k2, v in DEPS_SEEN.items() if not k2.startswith('rt') for k in v for t in k.split('|') if t[0] == 'q'}
    for i in Q:
        if in_guide(i): USED_Q.add(i)
    npcloc = {}
    for q in Q.values():
        if q.get('starts') and q.get('sc') and q['starts'][0]['t'] == 'npc':
            npcloc.setdefault(q['starts'][0]['id'], q['sc'])
    data = {
        'q': {str(i): dict(qd(Q[i]), **({'im': 1} if i in IMQ else {}), **({'u': 1} if in_guide(i) else {})) for i in sorted(USED_Q) if i in Q},
        'i': {str(i): t for i, t in USED_I.items()},
        'n': {str(i): [n] + (npcloc.get(i) or []) for i, n in USED_N.items()},
        'zones': zdash, 'dungeons': dash, 'chains': cmeta, 'alias': {str(k): v for k, v in sorted(ALIAS.items())}, 'names': unknown_names(),
        'legacy': dict({t: [w[0] for d in DG for w in d[8] if w[4] == t] for t in 'NEM'}, val=8995,
                       xh=['Durotar', 'Mulgore', 'Tirisfal Glades', 'Silverpine Forest']), 'miles': [list(m) for m in MILESTONES], 'prof': [list(p) for p in PROF],
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    page = ('<title>Enano Chamán en WoW Forever</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Germania+One&family=Alegreya+Sans:ital,wght@0,400;0,500;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap">\n'
            f'<style>\n{css}</style>\n{main}\n<script id="gd" type="application/json">{blob}</script>\n<script>\n{js}</script>\n')
    ids = set(re.findall(r'\sid="([^"]+)"', main)) | {'inicio', 'zonas', 'mazmorras', 'cadenas', 'quests', 'chaman', 'profesiones', 'referencia', 'muro'}
    broken = sorted({h for h in re.findall(r'href="#([^"]+)"', main) if h not in ids and not re.fullmatch(r'q-\d+', h)})
    if broken: print('ENLACES INTERNOS ROTOS:', ', '.join(broken))
    os.makedirs(os.path.join(ROOT, 'dist'), exist_ok=True)
    open(os.path.join(ROOT, 'dist', 'artifact.html'), 'w', encoding='utf-8').write(page)
    def wrap(p, cls):
        return ('<!doctype html>\n<html lang="es"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 32 32%27%3E%3Crect width=%2732%27 height=%2732%27 fill=%27%2310151A%27/%3E%3Cpath fill=%27%237FC0CE%27 d=%27M11 3h10l2 2v4H9V5z%27/%3E%3Cpath fill=%27%2362ADE5%27 d=%27M8 10h16v5H8z%27/%3E%3Cpath fill=%27%23F47B40%27 d=%27M9 16h14v5H9z%27/%3E%3Cpath fill=%27%23CFA560%27 d=%27M9 22h14l3 3v4H6v-4z%27/%3E%3C/svg%3E">\n'
                + p.replace('</style>', f'</style></head><body class="{cls}">', 1) + '\n</body></html>\n')
    open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(wrap(page, 'local'))
    pr = re.sub(r'<section class="blk allq".*?<!--/allq-->', '', page, flags=re.S)
    pr = re.sub(r'(<(?:section class="view"|article class="page [a-z]+")[^>]*?) hidden>', r'\1>', pr)
    open(os.path.join(ROOT, 'dist', 'print.html'), 'w', encoding='utf-8').write(wrap(pr, 'local print-all'))
    print(f'quests en caché {len(Q)} · fichas de quest {len(data["q"])} · objetos {len(data["i"])} · PNJ {len(data["n"])}')
    print(f'enlaces en el texto: {STATS["linked"]} directos, {STATS["search"]} por búsqueda · zonas {len(zdash)} · mazmorras {len(dash)} · cadenas {len(cmeta)}')
    print(f'index.html {os.path.getsize(os.path.join(ROOT, "index.html")) // 1024} KB')
    if '--deps' in sys.argv:
        for k, v in DEPS_SEEN.items():
            names = list(dict.fromkeys(' o '.join(dict.fromkeys(Q[int(t[1:])]['name'] for t in x.split('|'))) if x[0] == 'q' else x for x in v))
            print(f'  {k:6} {len(v):3}  ' + ' | '.join(names)[:150])

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
