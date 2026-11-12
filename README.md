# Enano Chamán en WoW Forever

Guía de leveo 1-60 para un enano chamán (Alianza, Mejora, Ingeniería + Minería) en World of Warcraft: Forever.

## Cómo usarla

- **`index.html`**: ábrelo con doble clic, o en https://thenanox.github.io/wow-forever/. Tiene ruta de 1 a 60, una página por zona, mazmorra y cadena de quests, buscador, panel por nivel y fichas emergentes.
- **Progreso**: las casillas se guardan en el `localStorage` del navegador donde las marcas. En Referencia › Importar se pueden marcar las quests completadas a partir del `Questie.lua` de SavedVariables o de una lista de números de quest.
- **`Enano-Chaman-WoW-Forever.pdf`**: versión para leer o imprimir, con marcadores. No incluye el listado completo de quests por zona.

## Cómo actualizarla

```sh
python3 tools/crawl.py      # descarga las quests nuevas de forever.warcraftdb.com a cache/
python3 tools/questie.py --refresh   # vuelve a bajar la base de datos de Questie (requisitos, raza y clase)
python3 tools/build.py      # genera index.html y dist/ (consulta objetos y PNJ que falten)
sh tools/make-pdf.sh        # regenera index.html y el PDF sin conexión
```

## De dónde sale cada cosa

| Parte | Fuente |
| --- | --- |
| Texto de la guía, ruta y checklist | `src/guia.html`, escrito a mano |
| Requisitos entre quests, raza y clase | `cache/questie/`, del repositorio Questie/QuestieDB (`tools/questie.py`). Se descarga con `gh` |
| Cadenas paso a paso | `data/chains.json` para las explicadas a mano; las previas a quests de mazmorra se generan solas a partir de los requisitos de Questie |
| Pestaña Quests y fichas de quest | Se pintan en el navegador con los datos incrustados en la página |
| Fichas de quest, listados por zona, quests de mazmorra | `cache/quest/`, de la API de forever.warcraftdb.com |
| Jefes, botín y consejos de mazmorra | `data/dungeons-*.json`, extraído de Warcraft Tavern y wowforeverinfo |
| Estadísticas de objetos | `cache/item/`, de la misma API |
| Identificadores de quests por mazmorra y facción | `data/wt-dungeon-quests.json`, de Warcraft Tavern |

Los enlaces van a Wowhead Forever. Los identificadores son los del juego, así que valen igual en Warcraft DB.

## Limitaciones conocidas

- La base de datos no distingue facción en las quests clásicas. Se descartan las de la Horda por la reputación que dan, así que en zonas disputadas puede colarse alguna.
- Warcraft DB no trae los requisitos entre quests: salen de Questie. Las quests que Questie todavía no tiene (casi todas de nivel 60) aparecen sin requisitos.
- Questie marca solo para la Horda las quests de clase de nivel 50 y 58 (Da Voodoo, The Darkreaver Menace): la guía las deja como sin confirmar.
- Cada quest tiene una sola marca (`chk-q<id>` en `localStorage`). Imprescindibles, ruta y filas de varios pasos no guardan nada: muestran el estado de sus quests.
- Reglas de sincronización: un recado que solo lleva a otra quest no es obligatorio; dos variantes que se excluyen cuentan como la misma quest; marcar una quest marca las que el juego exige antes. Los puntos que no dependen de ninguna quest llevan la etiqueta «a mano».
- Warcraft DB deja sin nivel unas 450 quests reales: se toman de Questie, salvo las que el addon oculta siempre, las repetibles y los encargos en serie.
- Las fichas de mazmorras de nivel 44 o más usan guías basadas en Classic para jefes y consejos.
