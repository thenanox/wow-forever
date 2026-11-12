# Enano Chamán en WoW Forever

Guía de leveo 1-60 para un enano chamán (Alianza, Mejora, Ingeniería + Minería) en World of Warcraft: Forever.

## Cómo usarla

- **`index.html`**: ábrelo con doble clic, o en https://thenanox.github.io/wow-forever/. Tiene ruta de 1 a 60, una página por zona, mazmorra y cadena de quests, buscador, panel por nivel y fichas emergentes.
- **Progreso**: las casillas se guardan en el `localStorage` del navegador donde las marcas. En Referencia › Importar se pueden marcar las quests completadas a partir del `Questie.lua` de SavedVariables o de una lista de números de quest.
- **`Enano-Chaman-WoW-Forever.pdf`**: versión para leer o imprimir, con marcadores. No incluye el listado completo de quests por zona.

## Cómo actualizarla

```sh
python3 tools/crawl.py      # descarga las quests nuevas de forever.warcraftdb.com a cache/
python3 tools/build.py      # genera index.html y dist/ (consulta objetos y PNJ que falten)
sh tools/make-pdf.sh        # regenera index.html y el PDF sin conexión
```

## De dónde sale cada cosa

| Parte | Fuente |
| --- | --- |
| Texto de la guía, ruta y checklist | `src/guia.html`, escrito a mano |
| Cadenas paso a paso | `data/chains.json`: orden y notas a mano; nombres, PNJ, coordenadas y objetivos salen de `cache/quest/` |
| Fichas de quest, listados por zona, quests de mazmorra | `cache/quest/`, de la API de forever.warcraftdb.com |
| Jefes, botín y consejos de mazmorra | `data/dungeons-*.json`, extraído de Warcraft Tavern y wowforeverinfo |
| Estadísticas de objetos | `cache/item/`, de la misma API |
| Identificadores de quests por mazmorra y facción | `data/wt-dungeon-quests.json`, de Warcraft Tavern |

Los enlaces van a Wowhead Forever. Los identificadores son los del juego, así que valen igual en Warcraft DB.

## Limitaciones conocidas

- La base de datos no distingue facción en las quests clásicas. Se descartan las de la Horda por la reputación que dan, así que en zonas disputadas puede colarse alguna.
- Tampoco trae los requisitos entre quests clásicas ni quién da algunas de ellas. Por eso el orden de las cadenas está puesto a mano.
- El importador de Questie asume el formato de Questie para Classic (`["complete"] = { [id] = true }` por personaje). No está probado con un archivo real de Forever.
- Las fichas de mazmorras de nivel 44 o más usan guías basadas en Classic para jefes y consejos.
