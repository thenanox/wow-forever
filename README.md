# Enano Chamán en WoW Forever

Guía de leveo 1-60 para un enano chamán (Alianza, Mejora, Ingeniería + Minería) en World of Warcraft: Forever.

## Cómo usarla

- **`index.html`**: ábrelo con doble clic, o en https://thenanox.github.io/wow-forever/. Tiene ruta de 1 a 60, una página por zona, mazmorra y cadena de quests, mapa esquemático de zonas, buscador, panel por nivel y fichas emergentes.
- **Quests**: el nombre de una quest abre su ficha dentro de la guía, con anterior y siguiente en su cadena. Para verla en Wowhead: el botón de la ficha, el enlace de la ficha emergente, o clic central o Ctrl y clic.
- **Zonas**: cada una dice de qué bando es (Alianza, Horda, disputada o neutral), qué esperar, un poco de historia, dónde está y cómo se llega. Las de la Horda también tienen página: no hay quests para un enano, pero sí mazmorras y mapa por descubrir.
- **Imprescindibles**: solo lo que es de mazmorra, de clase, un objeto muy bueno, una llave o acceso, o una ventaja permanente. El resto de cada zona va aparte, como «Para aprovechar».
- **Progreso**: las casillas se guardan en el `localStorage` del navegador donde las marcas. En Referencia › Importar se pueden marcar las quests completadas a partir del `Questie.lua` de SavedVariables o de una lista de números de quest.
- **`Enano-Chaman-WoW-Forever.pdf`**: versión para leer o imprimir, con marcadores. No incluye el listado completo de quests por zona.

## Cómo actualizarla

```sh
python3 tools/build.py      # genera index.html y dist/ (consulta objetos y PNJ que falten)
python3 tools/crawl.py      # descarga las quests nuevas de forever.warcraftdb.com
python3 tools/wfi.py        # vuelve a leer las guías paso a paso de wowforeverinfo: de ahí salen las ★
python3 tools/questie.py --refresh   # pasa a la última versión de Questie y comprueba que se lee entera
python3 tools/questie.py --why 1275  # de qué capa de Questie sale cada campo de una quest
sh tools/make-pdf.sh        # regenera index.html y el PDF sin conexión
```

### Los datos viajan con el repositorio

En un equipo nuevo basta con clonar y lanzar `python3 tools/build.py`: no hay que volver a descargar las quests.

- **Warcraft DB** (`data/db/`): la copia de lo descargado, un archivo por tipo con una línea por ficha. `cache/` es solo la carpeta de trabajo y no se sube. `crawl.py` y `build.py` rehacen la caché a partir de `data/db/` si falta o si ha cambiado, y la empaquetan al terminar una descarga (`tools/datos.py`). Warcraft DB no tiene versiones, y sus listados cambian: por eso se guarda la copia.
- **Questie** (`data/questie-version.json`): solo se apunta la versión. Si falta en el equipo, `build.py` baja esa misma versión con `gh`, no la última; solo `questie.py --refresh` la cambia.
- **wowforeverinfo** (`data/wfi-quests.json`): de sus guías solo se guarda qué quests nombran. El texto es suyo y se queda en `cache/`.

Después de descargar algo, haz commit de `data/` junto con `index.html`.

## De dónde sale cada cosa

| Parte | Fuente |
| --- | --- |
| Texto de la guía, ruta y checklist | `src/guia.html`, escrito a mano |
| Requisitos entre quests, raza, clase, profesión y quién da cada quest | `cache/questie/`, de los repositorios Questie/QuestieDB y Questie/Questie (`tools/questie.py`). Se descarga con `gh`, todo de una misma versión |
| Cadenas paso a paso | `data/chains.json` para las explicadas a mano; las previas a quests de mazmorra se generan solas a partir de los requisitos de Questie |
| Pestaña Quests y fichas de quest | Se pintan en el navegador con los datos incrustados en la página |
| Fichas de quest, listados por zona, quests de mazmorra | `data/db/quest.jsonl` y `list.jsonl`, de la API de forever.warcraftdb.com |
| Jefes, botín y consejos de mazmorra | `data/dungeons-*.json`, extraído de Warcraft Tavern y wowforeverinfo |
| Estadísticas de objetos | `data/db/item.jsonl`, de la misma API |
| Identificadores de quests por mazmorra y facción | `data/wt-dungeon-quests.json`, de Warcraft Tavern |
| ★ de los listados de zona y quests de la Horda en zonas compartidas | `data/wfi-quests.json`, de las guías por zona de wowforeverinfo (`tools/wfi.py`) |
| Bando, bases, qué esperar, historia, vecinas y sitio en el mapa de cada zona | `data/zonas.json`, escrito a mano. Lo propio de Forever sale de wowforeverinfo y de los datos del juego; la historia, del Warcraft clásico |
| Por qué es imprescindible cada punto | `IMP_CAT` en `tools/build.py` (categoría) y `data/imprescindibles.json` (explicación) |

Los enlaces van a Wowhead Forever. Los identificadores son los del juego, así que valen igual en Warcraft DB.

## Limitaciones conocidas

- La base de datos no distingue facción en las quests clásicas. Se descartan las de la Horda por la reputación que dan, así que en zonas disputadas puede colarse alguna.
- Warcraft DB no trae los requisitos entre quests: salen de Questie. Las quests que Questie todavía no tiene aparecen sin requisitos.
- Questie no es un archivo sino capas que se aplican en orden: datos en bruto de Classic, correcciones heredadas, quests nuevas de Forever, lo observado en partidas reales (incluidos los requisitos deducidos de ellas), correcciones a mano y, al final, las que dependen de la facción y la clase. `tools/questie.py` las compone igual que el addon, sin ejecutar nada de lo descargado, y explica el orden en su cabecera.
- La guía aplica las reglas con las que Questie decide si una quest se puede coger: con `preQuestSingle` basta una de la lista; con `preQuestGroup` hacen falta todas; una quest deja de ofrecerse cuando completas la siguiente de su cadena, el destino de un recado o su quest madre; las que piden una profesión que el personaje no tiene quedan fuera. Los requisitos sacados de partidas reales son deducciones con mucha evidencia, no datos del juego.
- `tools/questie.py` se ha comparado campo a campo con lo que compone el propio código de Questie (versión `90ab55b` de QuestieDB, 13 de noviembre de 2026) y sale idéntico: 5893 quests, 15564 PNJ y 7285 objetos, en cada etapa. La comparación se repite con `tools/questie-oracle.lua` y `tools/questie-check.py`; como el primero ejecuta código del repositorio de Questie, es un paso aparte y voluntario. Al regenerar, `questie.py` comprueba por su cuenta que cada capa se lee entera y que salen los valores que fijan las pruebas de ese repositorio.
- Esa comparación exacta se hizo con la versión `90ab55b`. El repositorio apunta ahora la `f0ad908` (13 de noviembre de 2026, 5890 quests): con ella han pasado las comprobaciones propias de `questie.py`, pero la comparación campo a campo no se ha repetido.
- Una quest cuenta como de mazmorra solo si se hace dentro: la base de datos la marca así o su zona es la propia mazmorra. Los demás pasos de la misma cadena llevan «cadena de» y el nombre de la mazmorra, y en la página de la mazmorra salen en un bloque aparte.
- El mapa de zonas es un esquema, no está a escala. «Cómo llegar desde Ironforge» es el camino con menos zonas por medio, por tierra, barco y tranvía, sin contar vuelos. Evita el territorio de la Horda y las zonas de bastante más nivel que el destino cuando hay otro camino; si no lo hay, la zona de paso lleva su nivel al lado.
- Las zonas de la Horda (Durotar, Mulgore, Tirisfal Glades y Silverpine Forest) tienen página, pero no cuentan como «zona de tu nivel». Sus quests no cuentan como del personaje aunque las fuentes no digan de quién son: quien las da está en un pueblo enemigo. Solo entraría una que Questie dé por de la Alianza y Warcraft DB no dé por de la Horda.
- La ficha de Shen'dralas es corta a propósito: las fuentes aún no la detallan.
- Questie marca solo para la Horda las quests de clase de nivel 50 y 58 (Da Voodoo, The Darkreaver Menace): la guía las deja como sin confirmar.
- Cada quest tiene una sola marca (`chk-q<id>` en `localStorage`). Imprescindibles, ruta y filas de varios pasos no guardan nada: muestran el estado de sus quests.
- Cada fila sabe si la quest se puede coger ya, si le falta un requisito o si pide más nivel; de ahí salen el filtro «Puedo cogerlas ahora» y el resumen de cada mazmorra.
- Reglas de sincronización: un recado que solo lleva a otra quest no es obligatorio; dos variantes que se excluyen cuentan como la misma quest; marcar una quest marca las que el juego exige antes. Los puntos que no dependen de ninguna quest llevan la etiqueta «a mano».
- Al importar, las versiones de otra raza o facción de una quest (el juego las da por completadas al hacer la tuya) cuentan como la quest de la guía. Se emparejan con los grupos de quests excluyentes de Questie y, si no los hay, por nombre y puesto en la cadena. Las que no se emparejan se guardan en el navegador y se repasan al abrir una versión nueva.
- Warcraft DB deja sin nivel unas 450 quests reales: se toman de Questie, salvo las que el addon oculta siempre, las repetibles y los encargos en serie.
- Las fichas de mazmorras de nivel 44 o más usan guías basadas en Classic para jefes y consejos.
