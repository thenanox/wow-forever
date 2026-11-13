-- La base de datos de Forever compuesta por el propio código de QuestieDB, para compararla con tools/questie.py
-- (la comparación la hace tools/questie-check.py). Ejecuta código del repositorio de Questie: es un paso voluntario.
-- Desde la raíz de un clon de Questie/QuestieDB (bastan src, generator, data/Forever y support/Forever):
--   luajit <guía>/tools/questie-oracle.lua <dir de salida> [Alliance|Horde] [CLASE]
-- Solo lee el repositorio y escribe JSON en el directorio de salida.

-- LuaJIT no admite más de 65536 constantes por función, y el repositorio está pensado para Lua 5.1, que admite
-- cuatro veces más. Dos apaños que no cambian ningún valor:
--   * los datos en bruto son una tabla con una fila por línea: si no cabe entera, se evalúa fila a fila;
--   * un archivo de correcciones que no cabe (traces/foreverNpcTraces.lua) se carga con su tabla construida por
--     tramos: `return { [id] = {...}, ... }` pasa a ser `t[id] = {...}` repartido en varias funciones.
local realLoadstring, realLoadfile = loadstring, loadfile

local function tooBig(err) return type(err) == "string" and err:find("constants", 1, true) ~= nil end

local function rowByRow(text, name)
  return function()
    local t, rows, lines = {}, 0, 0
    for line in text:gmatch("[^\n]+") do
      lines = lines + 1
      local id, body = line:match("^%[(%-?%d+)%] = (.+),%s*$")
      if id then
        local f, err = realLoadstring("return " .. body, name)
        if not f then error("fila " .. id .. " de " .. tostring(name) .. ": " .. tostring(err), 0) end
        t[tonumber(id)] = f()
        rows = rows + 1
      elseif not (line:match("^return {%s*$") or line:match("^}%s*$")) then
        error("línea inesperada en " .. tostring(name) .. ": " .. line:sub(1, 80), 0)
      end
    end
    io.stderr:write(("  %s: %d filas evaluadas una a una\n"):format(tostring(name), rows))
    return t
  end
end

local function splitTable(src, path)
  local outLines, state, n, chunk = {}, "head", 0, 0
  local function open()
    chunk = chunk + 1
    outLines[#outLines + 1] = "    local function __c" .. chunk .. "()"
  end
  local function close()
    outLines[#outLines + 1] = "    end"
    outLines[#outLines + 1] = "    __c" .. chunk .. "()"
  end
  for line in (src .. "\n"):gmatch("(.-)\n") do
    if state == "head" then
      if line == "    return {" then
        state = "table"
        outLines[#outLines + 1] = "    local __t = {}"
        open()
      else
        outLines[#outLines + 1] = line
      end
    elseif state == "table" then
      local id = line:match("^        %[(%-?%d+)%] = {$")
      if id then
        if n > 0 and n % 150 == 0 then close(); open() end
        n = n + 1
        outLines[#outLines + 1] = "        __t[" .. id .. "] = {"
      elseif line == "        }," then
        outLines[#outLines + 1] = "        }"
      elseif line == "    }" then
        close()
        outLines[#outLines + 1] = "    return __t"
        state = "tail"
      elseif line:match("^            ") or line:match("^%s*%-%-") or line:match("^%s*$") then
        outLines[#outLines + 1] = line
      else
        error("no sé partir " .. path .. ": " .. line:sub(1, 80), 0)
      end
    else
      outLines[#outLines + 1] = line
    end
  end
  if state ~= "tail" then error("no sé partir " .. path .. ": no encuentro la tabla", 0) end
  io.stderr:write(("  %s: %d entradas en %d tramos\n"):format(path, n, chunk))
  return table.concat(outLines, "\n")
end

local function loadfileCompat(path)
  local chunk, err = realLoadfile(path)
  if chunk or not tooBig(err) then return chunk, err end
  local f = assert(io.open(path, "rb"))
  local src = f:read("*a")
  f:close()
  return realLoadstring(splitTable(src, path), "@" .. path)
end

if arg[1] == "--compile-check" then                  -- solo compila, no ejecuta nada del repositorio
  for i = 2, #arg do
    local chunk, err = loadfileCompat(arg[i])
    print(arg[i], chunk and "compila" or err)
  end
  return
end

_G.loadfile = loadfileCompat
_G.loadstring = function(text, name)
  local chunk, err = realLoadstring(text, name)
  if chunk or not tooBig(err) then return chunk, err end
  return rowByRow(text, name)
end

local out = assert(arg[1], "falta el directorio de salida")
local faction, class = arg[2] or "Alliance", arg[3] or "SHAMAN"

local config = dofile("src/config.lua")
local flavor = config.flavorByName.Forever
local flavorLoader = dofile("generator/flavor.lua")
local corrections = dofile("generator/corrections.lua")
local derived = dofile("generator/derived.lua")

local function jstr(s)
  return '"' .. s:gsub('[%c"\\]', function(c)
    if c == '"' then return '\\"' elseif c == '\\' then return '\\\\' elseif c == '\n' then return '\\n'
    elseif c == '\r' then return '\\r' elseif c == '\t' then return '\\t' end
    return string.format('\\u%04x', c:byte())
  end) .. '"'
end

local function jnum(v)
  if v % 1 == 0 and v > -1e15 and v < 1e15 then return string.format("%.0f", v) end
  return string.format("%.17g", v)
end

local function json(v, buf)
  local t = type(v)
  if t == "table" then
    local keys = {}
    for k in pairs(v) do keys[#keys + 1] = k end
    table.sort(keys, function(a, b)
      if type(a) == type(b) then return a < b end
      return type(a) == "number"
    end)
    buf[#buf + 1] = "{"
    for i, k in ipairs(keys) do
      if i > 1 then buf[#buf + 1] = "," end
      buf[#buf + 1] = jstr(type(k) == "number" and jnum(k) or tostring(k))
      buf[#buf + 1] = ":"
      json(v[k], buf)
    end
    buf[#buf + 1] = "}"
  elseif t == "number" then buf[#buf + 1] = jnum(v)
  elseif t == "string" then buf[#buf + 1] = jstr(v)
  elseif t == "boolean" then buf[#buf + 1] = v and "true" or "false"
  else buf[#buf + 1] = "null" end
end

local function dump(name, value)
  local buf = {}
  json(value, buf)
  local f = assert(io.open(out .. "/" .. name, "wb"))
  f:write(table.concat(buf))
  f:close()
  local n = 0
  for _ in pairs(value) do n = n + 1 end
  print(name, n)
end

local function without(entities, drop)
  local res = {}
  for id, row in pairs(entities) do
    local r = {}
    for k, v in pairs(row) do if not drop[k] then r[k] = v end end
    res[id] = r
  end
  return res
end

-- 1) datos en bruto
local raw = flavorLoader.load(flavor, nil, false)
dump("quest-raw.json", raw.Quest.entities)

-- 2) con las correcciones estáticas, sin pases derivados
local st = flavorLoader.load(flavor, nil, false)
corrections.applyStatic(st, flavor)
dump("quest-static.json", st.Quest.entities)
local npcKeys, objKeys = st.Npc.meta.keys, st.Object.meta.keys
dump("npc-static.json", without(st.Npc.entities, { [npcKeys.waypoints] = true }))
dump("object-static.json", without(st.Object.entities, { [objKeys.waypoints or -1] = true }))
dump("meta.json", { quest = st.Quest.meta.keys, npc = npcKeys, object = objKeys })

-- 3) con los pases derivados (requiredRaces por la facción de quien da la quest)
derived.run(st, flavor)
dump("quest-derived.json", st.Quest.entities)

-- 4) correcciones dinámicas para un personaje concreto, compuestas como hace el registro
_G.UnitFactionGroup = function() return faction, faction end
_G.UnitClassBase = function() return class, 7 end
_G.UnitClass = function() return class, class, 7 end
_G.UnitRace = function() return "Dwarf", "Dwarf", 3 end
local lib = corrections.prepare(flavor).lib
local registry, meta = lib.Corrections, lib.Meta["Quest"]
local composed, used = {}, {}
for _, entry in ipairs(registry.Select({ datatype = "Quest", dynamic = true })) do
  if registry.EntryApplies(entry, flavor) then
    local rows, n = entry.func(), 0
    for id, fields in pairs(rows or {}) do
      local row = composed[id]
      fields = lib.TablePatch.Resolve(fields, meta, entry, id, row, function(qid, field)
        local e = st.Quest.entities[qid]
        return e and e[field]
      end, entry.options and entry.options.noOverwrites, registry.NIL)
      for f, v in pairs(fields) do
        if type(f) == "number" and f <= meta.fieldCount then
          if not row then row = {}; composed[id] = row end
          row[f] = (type(v) == "table" and next(v) == nil) and registry.NIL or v
          n = n + 1
        end
      end
    end
    used[#used + 1] = { name = entry.name, order = entry.loadOrder, fields = n }
  end
end

local final = {}
for id, row in pairs(st.Quest.entities) do
  local r = {}
  for k, v in pairs(row) do r[k] = v end
  final[id] = r
end
for id, row in pairs(composed) do
  local r = final[id]
  if not r then r = {}; final[id] = r end
  for f, v in pairs(row) do
    if v == registry.NIL then r[f] = nil else r[f] = v end
  end
end
dump("quest-final.json", final)
dump("dynamic-entries.json", used)

local statics = {}
for _, entry in ipairs(registry.Select({ datatype = "Quest", dynamic = false })) do
  statics[#statics + 1] = { name = entry.name, order = entry.loadOrder }
end
dump("static-entries.json", statics)
print("FIN")
