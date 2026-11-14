# Plantilla: guía de leveo de WoW Forever para cualquier personaje

Este repositorio es una guía de leveo de 1 a 60 para un personaje concreto: un enano chamán de la Alianza, con Ingeniería y Minería. Esta plantilla sirve para montar una guía igual para cualquier raza, clase y facción con un asistente de código (por ejemplo, Claude Code).

**Cómo se usa:**

1. Abre el asistente en una carpeta vacía.
2. Rellena los huecos `<…>` del bloque «Datos del personaje».
3. Copia todo lo que hay debajo de la segunda línea horizontal y pégalo como primer mensaje.

El asistente tiene que poder usar `git`, `gh` (con una cuenta de GitHub iniciada), Python 3 y Chrome o Chromium.

El aspecto es libre: colores, letra, iconos, el tono de los textos y los toques especiales. Lo que conviene seguir tal cual es la estructura, los datos y las reglas.

---

## Datos del personaje

| Campo | Valor | Notas |
| --- | --- | --- |
| Raza | `<raza>` | Alianza: Human, Dwarf, Night Elf, Gnome, Skyborne. Horda: Orc, Undead, Tauren, Troll, Skyborne |
| Clase | `<clase>` | Warrior, Paladin, Hunter, Rogue, Priest, Shaman, Mage, Warlock, Druid, según lo que permita la raza en Forever |
| Facción | `<Alianza u Horda>` | |
| Especialización y rol | `<especialización>`, `<rol>` | Por ejemplo: Mejora; daño y alguna vez curar |
| Profesiones primarias | `<profesión 1>`, `<profesión 2>` | |
| Profesiones secundarias | `<Cocina, Pesca, Primeros auxilios>` | Las que se vayan a llevar |
| Estilo de juego | `<estilo>` | Con calma y explorando, o directo al 60; en grupo o solo; reino JcJ o normal |
| Idioma de la guía | `<idioma>` | |
| Repositorio en GitHub | `<usuario>/<repositorio>` | Se publicará en `https://<usuario>.github.io/<repositorio>/` |

---

## El encargo

Vas a construir una guía web de leveo de 1 a 60 en WoW Forever para el personaje de arriba y a publicarla en GitHub Pages. La forma es la misma que la de la guía de referencia: un `index.html` de un solo archivo, generado por un script de Python a partir de datos descargados y de textos escritos a mano, con el progreso guardado en el navegador.

### Punto de partida: la guía de referencia

El repositorio público https://github.com/thenanox/wow-forever (la guía publicada está en https://thenanox.github.io/wow-forever/) es una guía terminada para un enano chamán de la Alianza. **Clónalo y léelo entero antes de escribir nada**: `README.md`, `tools/`, `data/` y `src/`. Tu trabajo es adaptarlo, no reescribirlo: el código de datos y de navegación sirve tal cual, y lo propio del enano chamán está localizado en los sitios que se listan más abajo.

- Crea el repositorio nuevo a partir de una copia del de referencia, sin su historial: `gh repo create <repositorio> --public` y copia los archivos.
- Mantén `data/db/`, `data/questie-version.json`, `data/wfi-quests.json`, `data/dungeons-*.json`, `data/wt-*.json` y `data/wt-ids.tsv`. No dependen del personaje: son los datos de todas las quests, de las dos facciones.
- Borra o rehaz lo que es del enano chamán: `index.html`, el PDF, `src/guia.html` y los textos de `data/` que se nombran abajo.
- Antes de cada fase, enseña al usuario la lista de lo que vas a cambiar y espera su visto bueno.

### Qué hay en el repositorio de referencia

| Parte | Qué hace |
| --- | --- |
| `tools/build.py` | Genera `index.html`, `dist/print.html` (para el PDF) y `dist/artifact.html`. Junta los textos de `src/guia.html` con los datos y mete todo en un JSON dentro de la página (`<script id="gd">`). Avisa de enlaces internos rotos. |
| `tools/gamedata.py` | Carga las quests de la caché, decide de qué facción es cada una, resuelve nombres a números de quest, PNJ u objeto, y lee los tooltips de objetos. |
| `tools/questie.py` | Lee la base de datos de Questie componiendo sus capas como el addon, sin ejecutar nada de lo descargado. |
| `tools/crawl.py` | Descarga de Warcraft DB los listados por zona y la ficha de cada quest. |
| `tools/wfi.py` | Lee las guías por zona de wowforeverinfo y guarda solo qué quests nombra cada una. |
| `tools/datos.py` | Empaqueta la caché en `data/db/*.jsonl` para el repositorio y la rehace al clonar. |
| `src/guia.html` | Todo el texto escrito a mano: ruta de 1 a 60, imprescindibles por zona, clase, talentos, profesiones, referencia. |
| `src/app.js` | Navegación, casillas, estado de cada quest, buscador, fichas emergentes, importar desde Questie, mapa y extras. |
| `src/style.css` | El aspecto. Es la parte que se puede cambiar a gusto de cada uno. |
| `data/*.json` | Los datos escritos a mano o extraídos: cadenas, mazmorras, zonas, imprescindibles, crónica. |

### Lo que hay que cambiar para otro personaje

Busca cada sitio y cámbialo; no dejes nada del enano chamán.

**Personaje, en las herramientas**

- `tools/questie.py`: `FACTION`, `RACE` y `CLASS`. Los nombres son los de Questie para Forever: razas `HUMAN`, `DWARF`, `NIGHT_ELF`, `GNOME`, `SKYBORNE_ALLIANCE`, `ORC`, `UNDEAD`, `TAUREN`, `TROLL`, `SKYBORNE_HORDE`; clases `WARRIOR`, `PALADIN`, `HUNTER`, `ROGUE`, `PRIEST`, `SHAMAN`, `MAGE`, `WARLOCK`, `DRUID`. Confírmalos en `src/corrections/enum/expansions.lua` de QuestieDB, en el bloque `Forever`. Ojo: en Forever hay combinaciones de raza y clase nuevas (los Skyborne de la Alianza pueden ser magos, los de la Horda, chamanes).
- `tools/gamedata.py`:
  - `MY_SKILLS`: los números de habilidad de las profesiones del personaje. Son 202 Ingeniería, 186 Minería, 185 Cocina, 356 Pesca, 129 Primeros auxilios, 164 Herrería, 165 Peletería, 171 Alquimia, 182 Herboristería, 197 Sastrería, 333 Encantamiento y 393 Desuello.
  - `ALLY_REP`, `HORDE_REP` y `HORDE_MAPS`: sirven para reconocer las quests de la otra facción. Si el personaje es de la Horda, «la otra facción» es la Alianza: revisa `faction()` y todo lo que en `build.py` compara con `'H'`.
- `tools/crawl.py`: en `PRESETS`, cambia `class/shaman` por la clase del personaje y pon sus profesiones (`profession/<nombre>`). Añade las zonas de la facción contraria si vas a darles página.

**Guía, en `tools/build.py`**

- `DG`: la columna «dónde» de cada mazmorra y qué mazmorras están en territorio enemigo.
- `ZONES` y `EXTRA_ZONES`: las zonas de la ruta del personaje, con sus guías de wowforeverinfo. `HORDE_ZONES` pasa a ser la lista de zonas enemigas.
- `MILESTONES`: lo que aprende el personaje a cada nivel con su clase.
- `PROF`: sus profesiones por tramo de nivel.
- `IMP_CAT`, `APRO`, `IMP_MAP` y `DEP_MAP`: van con las casillas de los imprescindibles del nuevo `src/guia.html`.
- `HOME`: la capital del personaje, que es el origen de «Cómo llegar».
- `CLASS_Q` sale del listado de clase descargado: comprueba que apunta al de la clase del personaje.

**Textos y datos escritos a mano**

- `src/guia.html`: todo el texto, de nuevo, para la clase y la ruta del personaje.
- `src/app.js`: la portada lleva los cuatro totems del chamán (en `src/guia.html`, con el número de su quest). Cámbialos por lo equivalente de la clase del personaje o quítalos. En el Legacy, los retos de clase y profesión tienen nombres en inglés que hay que cambiar.
- `data/chains.json`: las cadenas explicadas a mano. Las de clase son las primeras que hay que rehacer.
- `data/imprescindibles.json`: el porqué de cada imprescindible.
- `data/zonas.json`: el bando de cada zona (`A`, `H`, `D`, `N`) es fijo y vale para todos. Los textos de «qué esperar» están escritos para un enano de la Alianza («para ti es territorio enemigo»): reescríbelos desde la facción del personaje, junto con las bases y las rutas en barco y zepelín de esa facción y `xy` si añades zonas.
- `data/cronica.json`: si quieres la crónica, sus textos son para un enano. Se puede quitar o cambiar por otro toque propio.

### Los datos: de dónde sale cada cosa

#### 1. Warcraft DB (forever.warcraftdb.com)

Es la fuente de las fichas: nombre, zona, nivel, quién la da y dónde, objetivo, premio, experiencia y reputación.

- **Listados:** `/api/data/list/quests?page=N&per_page=100&preset=<continente>/<zona>`. También valen `class/<clase>`, `profession/<profesión>` y `dungeons`. Si un preset no existe, la API no da error: devuelve todas las quests (unas 69 páginas). Si ves `pages` cerca de 69, el preset está mal.
- **Ficha de quest:** `/api/data/node/quest/<id>`. Trae `data`, con `starts`/`ends` en HTML con enlaces `/data/npc|object|item/<id>`, `rewards`, `storyline`, `log_description` y `objectives`. Trae también `extra.quest_map`, con las coordenadas de inicio y entrega (`u`, `v` de 0 a 1, y la planta).
- **Búsqueda:** `/api/v1/search?q=<nombre>`.
- **Tooltip de objeto:** `/api/v1/tooltip/item/<id>`.
- **Cómo pedir:** con cabecera `User-Agent` de navegador, 3 peticiones a la vez como mucho y una pausa de unos 0,35 segundos.
- **Caché:** se guarda todo y no se vuelve a pedir. Un error queda como `{"err": …}` y no se reintenta: búscalos y bórralos.

Trampas:

- No trae requisitos entre quests: salen de Questie.
- Unas 450 quests reales vienen sin nivel: se toma el de Questie.
- En las quests de Classic no distingue facción (`side: Both`).
- Hay quests duplicadas con otro número.
- Algunas desaparecen de los listados aunque existan (`data/extra-quest-ids.json`).
- Las coordenadas son de la planta que dice `ui_map_id`, que no siempre es la zona de la quest.

#### 2. Questie (repositorios Questie/QuestieDB y Questie/Questie)

Da lo que Warcraft DB no tiene: requisitos, raza y clase, quién da y recoge cada quest, cadenas y quests ocultas. **Es la parte más delicada:** lee `tools/questie.py` con calma y no la simplifiques.

Questie no es un archivo, sino capas que se aplican en este orden:

1. `data/Forever/forever*DB.lua`: datos en bruto, heredados de Classic.
2. `legacy/classicQuestReputationFixes.lua`.
3. `legacy/classic*Fixes.lua`, función `Load`.
4. `generated/foreverBase*.lua`: quests, PNJ y objetos nuevos de Forever.
5. `traces/forever*Traces.lua`: lo observado en partidas reales.
6. `traces/foreverQuestRelationTraces.lua`: requisitos y cadenas deducidos de esas partidas.
7. `forever*Fixes.lua`, función `Load`: correcciones a mano.
8. Pase derivado: una quest sin raza hereda la facción del PNJ que la da, si es de una sola.
9. `classic*Fixes.lua`, función `LoadFactionFixes`: correcciones según la facción del personaje.
10. `forever*Fixes.lua`, función `LoadDynamic`: ídem, las de Forever.

Cómo se aplican:

- Cada corrección sustituye el campo entero.
- Las claves `campo_add` y `campo_remove` (el número del campo ±1000) añaden o quitan elementos de una lista.
- `{}` borra el campo.
- Las quests ocultas salen de `Database/Corrections/QuestieQuestBlacklist.lua` del addon, evaluado como Classic Era: así se identifica Forever.
- **Nunca ejecutes el Lua descargado.** Léelo como datos, y que un nombre desconocido sea un error, no algo que se salta en silencio.
- Descarga los archivos de un mismo commit de cada repositorio, porque las capas dependen unas de otras, y apunta el commit en `data/questie-version.json`.

Al componer, comprueba que cada capa se ha leído entera y que salen los valores que fijan las pruebas del propio repositorio. Para una comprobación completa están `tools/questie-oracle.lua` y `tools/questie-check.py`, que comparan campo a campo con lo que compone el código de Questie. Este paso ejecuta código de Questie, así que es voluntario y aparte.

Cómo se leen los campos, que es como decide el addon si una quest se puede coger:

- `preQuestSingle`: basta con una de la lista.
- `preQuestGroup`: hacen falta todas, y solo cuenta si no hay `preQuestSingle`. Un número negativo exige esa quest exacta; si no, vale también otra que se excluya con ella.
- `exclusiveTo`: variantes que se excluyen. Hecha una, la otra cuenta como hecha.
- `nextQuestInChain`, `breadcrumbForQuestId`/`breadcrumbs`, `parentQuest` y `availableUntilCompleted`: una quest deja de ofrecerse cuando completas la siguiente de su cadena, el destino de su recado, su quest madre o la que la retira. Un recado que solo lleva a otra quest no es obligatorio.
- `requiredSkill`, `requiredSpecialization` (como Ingeniería gnómica o goblin), `requiredMinRep` y `requiredMaxRep`: las que piden algo que el personaje no tiene se quedan fuera.
- `specialFlags & 1`: repetible.

#### 3. wowforeverinfo.com

Guías paso a paso por zona: `/guides/<zona>-<niveles>/`. Las direcciones salen de `/guides/leveling-alliance/` y `/guides/leveling-horde/`. El cuerpo es el `<main>` a partir del `<h1>`, con apartados `<h2>`; los que empiezan por «Horde» o «Alliance» dicen de qué facción es lo que hay debajo. **Al repositorio solo van los nombres de quest de cada apartado** (`data/wfi-quests.json`): el texto es de sus autores. De ahí salen la ★ («aparece en la guía paso a paso») y qué quests de una zona compartida son de la otra facción. Sus apartados «Overview» sirven para escribir «qué esperar» de cada zona con palabras propias.

#### 4. Warcraft Tavern y Wowhead

- **Warcraft Tavern:** guías de mazmorra (jefes, botín, consejos, quests por facción) y los números de quest de cada mazmorra (`data/wt-dungeon-quests.json`). Las fichas de mazmorra (`data/dungeons-*.json`) se sacaron de ahí y de wowforeverinfo; las de nivel 44 o más usan guías de Classic.
- **Enlaces:** `https://www.wowhead.com/forever/quest=<id>` (o `/forever/es/`) y `https://forever.warcraftdb.com/data/quest/<id>`. Los números son los del juego y valen igual en las dos.

### Reglas que tiene que cumplir la guía

**Facción y qué cuenta como tuyo**

- Una quest es del personaje si Questie la da por buena para su raza, clase y facción, no está oculta y no pide una profesión que no tiene.
- Si Questie no la conoce, se decide con Warcraft DB por este orden: lado declarado, reputación que da y si quien la da está en un mapa de la otra facción.
- En las zonas de la facción contraria, quien da las quests está en un pueblo enemigo. Allí una quest solo cuenta si Questie dice que es de la facción del personaje y Warcraft DB no dice que es de la otra.

**Progreso y casillas**

- Cada quest tiene una sola marca (`chk-q<id>` en `localStorage`). Lo demás (imprescindibles, pasos de la ruta, filas de varios pasos) no guarda nada: muestra el estado de las quests de las que depende (`data-dep`).
- Marcar una quest marca las que el juego exige antes.
- Cada quest sabe si está hecha, si se puede coger ya, si le falta un requisito, si pide más nivel o si ya no se puede coger.

**Importar desde el juego**

- Hay que poder importar el `Questie.lua` de `WTF/Account/<cuenta>/SavedVariables` o una lista de números de quest.
- El juego da por hechas las versiones de otra raza de cada quest que completas: emparéjalas con los grupos `exclusiveTo` y, si no los hay, por nombre y puesto en la cadena.
- Las que no se emparejan se enseñan con su nombre y el motivo.

**Qué es imprescindible**

- Solo cinco motivos: mazmorra, clase, objeto muy bueno para el personaje, llave o acceso, y ventaja permanente.
- Cada imprescindible lleva su etiqueta y el porqué.
- Lo demás de cada zona va aparte, como «Para aprovechar»: buena experiencia, equipo corriente, pasos de cadenas de otra zona.

**Quests de mazmorra**

- Una quest es de mazmorra solo si se hace dentro: la base de datos la marca como `Dungeon` o su zona es la mazmorra.
- Los pasos previos de su cadena se hacen fuera: llevan «cadena de» y el nombre de la mazmorra, y en la página de la mazmorra van en un bloque aparte.

**Zonas**

- Cada zona lleva su bando desde el punto de vista del personaje, sus bases, «qué esperar», un poco de historia, sus mazmorras, sus vecinas y «Cómo llegar» desde su capital.
- Las zonas enemigas tienen página, con sus mazmorras y la casilla de exploración, pero no cuentan como «zona de tu nivel».

**No inventes**

- Forever salió en noviembre de 2026 y cambia cada semana. Nada de Forever se afirma de memoria: zonas nuevas, mazmorras nuevas, Skyborne, barcos nuevos, facciones. Todo eso se toma de las fuentes.
- La historia clásica de Warcraft sí se puede contar.
- Si una fuente no lo dice, la guía lo dice así: «las fuentes aún no lo detallan».

**Datos en el repositorio**

- Lo descargado de Warcraft DB va en `data/db/` (`tools/datos.py`), porque la web no guarda versiones y sus listados cambian.
- Questie se fija por commit.
- Un clon limpio tiene que generar la misma guía sin descargar quests.

**Siempre igual**

- Ordena siempre por número de quest al cargar. El orden de los archivos en disco cambia de un equipo a otro, y con él los desempates.
- Dos generaciones seguidas dan el mismo `index.html`, byte a byte.

### La estructura de la web (la plantilla)

**Pestañas:** Inicio, Zonas, Mazmorras, Cadenas, Quests, Tu clase, Profesiones y Referencia. Además, dos vistas sin pestaña: el muro de gestas y la crónica, que son los toques especiales de la de referencia; haz los tuyos.

**Rutas por hash:**

| Hash | Lleva a |
| --- | --- |
| `#z-<zona>` | Una zona |
| `#dg-<mazmorra>` | Una mazmorra |
| `#cad-<cadena>` | Una cadena |
| `#q-<id>` | La ficha de una quest |
| `#<sección>` | Un apartado de Tu clase, Profesiones o Referencia |

**Inicio:**

- Panel «Ahora, con nivel X»: zonas, mazmorras y cadenas de tu nivel, y lo que aprendes en los próximos niveles.
- La ruta de 1 a 60 por tramos.
- Los imprescindibles pendientes a tu nivel.

**Zonas:**

- Un mapa esquemático de los dos continentes, en SVG: una ficha por zona con el color de su bando y líneas para caminos, barcos y tranvía (`data/zonas.json`).
- Debajo, las tarjetas de zona agrupadas por tramo de nivel.

**Página de zona:**

1. Bando y nivel.
2. «Qué esperar» e historia.
3. «Dónde está»: minimapa con la zona y sus vecinas, y «Cómo llegar».
4. Imprescindibles.
5. «Para aprovechar».
6. Cadenas que pasan por la zona.
7. Ruta por la zona.
8. Todas sus quests, con filtros: «Puedo cogerlas ahora», pendientes, nuevas en Forever y ★.

**Página de mazmorra:**

- Cómo llegar y qué coger antes.
- Quests en tres bloques: se hacen dentro y se cogen fuera; se cogen dentro; los demás pasos de sus cadenas.
- Jefes en orden, objetos clave para la clase del personaje y consejos.
- Casilla «Hecha» por ala.

**Página de cadena:**

- Por qué hacerla y qué ganas.
- Pasos numerados con quién la da, dónde se entrega, el objetivo y qué hace falta antes.
- El siguiente paso, resaltado.

**Ficha de quest:**

- Objetivo, quién la da y dónde, premio y reputación.
- Lo que hay que haber hecho antes, en orden, y lo que se abre al terminarla.
- Anterior y siguiente en su cadena.
- Botón «Abrir en Wowhead».

**Navegación:**

- El nombre de una quest abre su ficha dentro de la guía.
- A Wowhead se sale por el botón de la ficha, por la ficha emergente o con Ctrl/clic central.
- Objetos y PNJ van directos a Wowhead.
- En pantallas táctiles, el primer toque enseña la ficha emergente.

**Siempre a mano:**

- Campo de nivel, que resalta lo de tu nivel en toda la guía.
- Buscador de quests, zonas, jefes y objetos.
- Ajustes: abrir las fichas en Wowhead, Wowhead en español o Warcraft DB.
- Código para copiar el progreso a otro dispositivo.
- Importar desde Questie.
- Imprimir o guardar en PDF.

**Estilo:** libre. Solo hay tres requisitos:

- Tema claro y oscuro.
- Que funcione en el móvil, sin scroll horizontal.
- Que la versión impresa salga limpia.

### Cómo trabajar

1. Clona la referencia y léela. Resume al usuario qué vas a cambiar y espera su visto bueno.
2. Cambia el personaje en las herramientas.
3. Prepara los datos:
   - `python3 tools/build.py`: rehace la caché a partir de `data/db/` y baja la versión de Questie apuntada.
   - `python3 tools/crawl.py`: solo si añades presets nuevos.
   - `python3 tools/questie.py`: para recomponer Questie con la raza y la clase del personaje.
   - `python3 tools/wfi.py`: si añades guías.
4. Genera la guía con los textos de la referencia como borrador y compara cifras. ¿Cuántas quests puede hacer el personaje, cuántas hay por zona, sale alguna de la otra facción?
5. Escribe los textos del personaje: `src/guia.html`, cadenas de clase, imprescindibles, zonas.
6. Comprueba en Chrome sin ventana, con un perfil aparte (`--user-data-dir`) y estado sembrado en `localStorage`:
   - **Navegación:** que lleguen bien una zona, una mazmorra, una cadena y una ficha de quest; que las quests se abran dentro de la guía y los objetos y PNJ salgan a Wowhead; con ratón y en modo táctil.
   - **Funciones:** el mapa, los filtros y que marcar una quest se refleje en los imprescindibles, la cadena y la zona.
   - **Integridad:** sin errores en la consola, sin «ENLACES INTERNOS ROTOS» al generar, el mismo `index.html` en dos generaciones seguidas y en un clon limpio.
   - **Aspecto:** capturas en escritorio, en móvil y en tema oscuro, y míralas.
7. Publica:
   - Commit de `data/`, `src/`, `tools/` e `index.html`.
   - Push a `main`.
   - GitHub Pages desde `main` y la raíz (Settings › Pages, o `gh api repos/<usuario>/<repo>/pages -X POST -f source[branch]=main -f source[path]=/`).
   - Comprueba que la web publicada es igual al `index.html` del repositorio.

Cuando acabes, deja en el `README.md` cómo se actualiza, de dónde sale cada cosa y las limitaciones conocidas, como en la referencia.
