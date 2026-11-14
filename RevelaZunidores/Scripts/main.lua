-- RevelaZunidores: mostra onde estao os colecionaveis do mapa atual.
--
-- Teclas no jogo:
--   F5 = troca a categoria
--   F6 = lista as classes de atores do mapa em classes.txt
--   F7 = lista os itens da categoria em encontrados.txt e no console
--   F8 = teleporta para o proximo item da categoria
--   Ctrl+R = recarrega todos os mods (recurso do UE4SS)
--
-- Janela de menu (menu\menu_revela.pyw):
--   o mod grava estado.json a cada INTERVALO_MS e le comandos.txt
--   (comandos: recarregar | atualizar | categoria <n> | teleportar <n> <nome do ator>)

local UEHelpers = require("UEHelpers")

local PASTA_MOD = (debug.getinfo(1, "S").source:gsub("^@", ""):gsub("[/\\]Scripts[/\\]main%.lua$", ""))
package.path = PASTA_MOD .. "/Scripts/?.lua;" .. package.path
package.loaded["config"] = nil
local cfg = require("config")
local MENU = cfg.MENU or { ATIVO = false }

local ARQ_ESTADO = PASTA_MOD .. "/estado.json"
local ARQ_COMANDOS = PASTA_MOD .. "/comandos.txt"

-- idioma: "en" (padrao) ou "pt-BR"; pode mudar ao vivo com o comando "idioma"
local idioma = (cfg.IDIOMA == "pt-BR") and "pt-BR" or "en"
local function L(en, pt) return idioma == "pt-BR" and pt or en end
local function nomeCat(c) return idioma == "pt-BR" and c.nome or (c.nome_en or c.nome) end
local function refCat(c) return idioma == "pt-BR" and c.referencia or (c.referencia_en or c.referencia) end

local function log(msg)
    print("[RevelaZunidores] " .. msg .. "\n")
end

local categoriaAtual = cfg.CATEGORIA_INICIAL or 1
local indice = 0 -- posicao do F8 na lista atual
local function categoria() return cfg.CATEGORIAS[categoriaAtual] end

---------------------------------------------------------------------------
-- utilitarios
---------------------------------------------------------------------------
local function escrever(nome, linhas)
    local f = io.open(PASTA_MOD .. "/" .. nome, "w")
    if not f then
        log(L("Could not write ", "Nao consegui gravar ") .. nome)
        return
    end
    f:write(table.concat(linhas, "\n"), "\n")
    f:close()
    log(L("Saved to ", "Salvo em ") .. PASTA_MOD .. "/" .. nome)
end

local function contem(texto, lista)
    local t = texto:lower()
    for _, p in ipairs(lista) do
        if t:find(p:lower(), 1, true) then return true end
    end
    return false
end

local function nomeClasse(ator)
    local ok, nome = pcall(function() return ator:GetClass():GetFName():ToString() end)
    return ok and nome or "?"
end

local function casaCategoria(c, classe)
    return contem(classe, c.palavras) and not contem(classe, cfg.IGNORAR)
end

local function casaCaminho(c, ator)
    if not c.caminho then return true end
    local ok, nome = pcall(function() return ator:GetFullName() end)
    return ok and contem(nome, { c.caminho })
end

local function jogador()
    local pc = UEHelpers.GetPlayerController()
    if not pc or not pc:IsValid() then return nil end
    local pawn = pc.Pawn
    if not pawn or not pawn:IsValid() then return nil end
    return pc, pawn
end

-- angulo relativo a camera: 0 = a frente, positivo = a direita (-180..180)
local function anguloRelativo(yaw, origem, alvo)
    local dx, dy = alvo.X - origem.X, alvo.Y - origem.Y
    local angulo = math.deg(math.atan(dy, dx))
    return (angulo - yaw + 540) % 360 - 180
end

local function direcaoTexto(rel)
    local nomes = {
        { 22.5, "a frente" }, { 67.5, "frente-direita" }, { 112.5, "a direita" },
        { 157.5, "tras-direita" }, { 180.1, "atras" },
    }
    local abs = math.abs(rel)
    for _, n in ipairs(nomes) do
        if abs <= n[1] then
            local d = n[2]
            if rel < 0 then d = d:gsub("direita", "esquerda") end
            return d
        end
    end
    return "?"
end

---------------------------------------------------------------------------
-- cache de itens por categoria (usado pela janela de menu)
--   cache[i] = { classes = { [nomeClasse] = true }, itens = { {ator, nome, classe, x, y, z} } }
---------------------------------------------------------------------------
local cache = {}
local contornoAplicado = {} -- nome do ator -> valor de stencil aplicado
local function zerarCache()
    cache = {}
    contornoAplicado = {}
    for i = 1, #cfg.CATEGORIAS do cache[i] = { classes = {}, itens = {} } end
end
zerarCache()

-- Varredura pesada: passa por todos os atores para descobrir quais classes
-- pertencem a cada categoria.
local function descobrirClasses()
    local n = 0
    for _, a in ipairs(FindAllOf("Actor") or {}) do
        if a:IsValid() then
            n = n + 1
            local classe = nomeClasse(a)
            for i, c in ipairs(cfg.CATEGORIAS) do
                if casaCategoria(c, classe) then cache[i].classes[classe] = true end
            end
        end
    end
    return n
end

-- Varredura leve: so as classes ja conhecidas
local function atualizarItens()
    for i, c in ipairs(cfg.CATEGORIAS) do
        local lista, vistos = {}, {}
        for classe in pairs(cache[i].classes) do
            for _, a in ipairs(FindAllOf(classe) or {}) do
                if a:IsValid() and casaCaminho(c, a) then
                    local okN, nome = pcall(function() return a:GetFName():ToString() end)
                    local okP, p = pcall(function() return a:K2_GetActorLocation() end)
                    if okN and okP and p and not vistos[nome] then
                        vistos[nome] = true
                        table.insert(lista, { ator = a, nome = nome, classe = nomeClasse(a), x = p.X, y = p.Y, z = p.Z })
                    end
                end
            end
        end
        cache[i].itens = lista
    end
end

---------------------------------------------------------------------------
-- busca direta (teclas F7/F8)
---------------------------------------------------------------------------
local function buscarZunidores()
    local pc, pawn = jogador()
    if not pawn then
        log(L("Player not found (load a save first).", "Jogador nao encontrado (carregue um save primeiro)."))
        return nil
    end
    local origem = pawn:K2_GetActorLocation()
    local yaw = pc:GetControlRotation().Yaw
    local c = categoria()
    local achados = {}
    for _, a in ipairs(FindAllOf("Actor") or {}) do
        if a:IsValid() then
            local classe = nomeClasse(a)
            if casaCategoria(c, classe) and casaCaminho(c, a) then
                local p = a:K2_GetActorLocation()
                local dx, dy, dz = p.X - origem.X, p.Y - origem.Y, p.Z - origem.Z
                table.insert(achados, {
                    ator = a, classe = classe, nome = a:GetFName():ToString(),
                    x = p.X, y = p.Y, z = p.Z,
                    dist = math.sqrt(dx * dx + dy * dy + dz * dz) / 100, -- metros
                    dir = direcaoTexto(anguloRelativo(yaw, origem, p)),
                    dz = dz / 100,
                })
            end
        end
    end
    table.sort(achados, function(a, b) return a.dist < b.dist end)
    return achados, pawn
end

-- F6: inventario de classes do mapa
local function listarClasses()
    local contagem = {}
    for _, a in ipairs(FindAllOf("Actor") or {}) do
        if a:IsValid() then
            local c = nomeClasse(a)
            contagem[c] = (contagem[c] or 0) + 1
        end
    end
    local lista = {}
    for c, n in pairs(contagem) do table.insert(lista, { c = c, n = n }) end
    table.sort(lista, function(a, b) return a.c < b.c end)
    local linhas = { L("Actor classes on the current map (count  class):", "Classes de atores no mapa atual (quantidade  classe):") }
    for _, e in ipairs(lista) do
        table.insert(linhas, string.format("%5d  %s", e.n, e.c))
    end
    escrever("classes.txt", linhas)
    log(#lista .. L(" classes found. Look for the collectible class in classes.txt and put it in config.lua.",
        " classes encontradas. Procure no classes.txt o nome do colecionavel e coloque-o em config.lua."))
end

-- F7: lista os itens da categoria
local function listar()
    local achados = buscarZunidores()
    if not achados then return end
    local c = categoria()
    if #achados == 0 then
        log(L("No '", "Nenhum item de '") .. nomeCat(c) .. L("' on this map with the current keywords. Use F6 and adjust config.lua.",
            "' neste mapa com as palavras-chave atuais. Use F6 e ajuste config.lua."))
        return
    end
    local linhas = { string.format(L("%s: %d on the loaded map (total reference: %s). Nearest to farthest:",
        "%s: %d no mapa carregado (referencia total: %s). Do mais perto ao mais longe:"),
        nomeCat(c), #achados, refCat(c)) }
    for i, z in ipairs(achados) do
        local altura = z.dz > 3 and L("above", "acima") or (z.dz < -3 and L("below", "abaixo") or L("same level", "mesmo nivel"))
        local l = string.format("%3d. %6.0f m  %-16s %-11s  X=%.0f Y=%.0f Z=%.0f  [%s] %s",
            i, z.dist, z.dir, altura, z.x, z.y, z.z, z.classe, z.nome)
        table.insert(linhas, l)
        if i <= cfg.MAX_LISTA then log(l) end
    end
    escrever("encontrados.txt", linhas)
end

-- F5: troca a categoria
local function definirCategoria(n)
    if n < 1 or n > #cfg.CATEGORIAS then return end
    categoriaAtual = n
    indice = 0
    local c = categoria()
    log(string.format(L("Category %d/%d: %s [%s] - reference: %s", "Categoria %d/%d: %s [%s] - referencia: %s"),
        categoriaAtual, #cfg.CATEGORIAS, nomeCat(c), c.conteudo, refCat(c)))
end

local function trocarCategoria()
    definirCategoria(categoriaAtual % #cfg.CATEGORIAS + 1)
end

local function teleportarPara(pawn, x, y, z, rotulo)
    pawn:K2_SetActorLocation({ X = x, Y = y, Z = z + cfg.ALTURA_TELEPORTE }, false, {}, true)
    log(L("Teleported to ", "Teleportado para ") .. rotulo)
end

-- F8: teleporta para o proximo
local function teleportar()
    local achados, pawn = buscarZunidores()
    if not achados or #achados == 0 then
        log(L("Nothing to teleport to. Use F7 to check the list.", "Nada para teleportar. Use F7 para conferir a lista."))
        return
    end
    indice = indice % #achados + 1
    local z = achados[indice]
    teleportarPara(pawn, z.x, z.y, z.z, string.format("%d/%d: %s (%s)", indice, #achados, z.nome, z.classe))
end

---------------------------------------------------------------------------
-- estado.json para a janela de menu
---------------------------------------------------------------------------
-- indicadores dentro do jogo: contorno (custom depth), vibracao, camera.json
---------------------------------------------------------------------------
local IND = cfg.INDICADORES or {}
local ind = {
    contorno = IND.CONTORNO == true,
    contornoValor = IND.CONTORNO_VALOR or 252,
    vibracao = IND.VIBRACAO == true,
    vibracaoDist = IND.VIBRACAO_DISTANCIA_M or 15,
    categorias = {}, -- [indice da categoria] = true -> revelada (contorno/vibracao)
}
for i = 1, #cfg.CATEGORIAS do ind.categorias[i] = IND.CATEGORIAS == nil end
for _, i in ipairs(IND.CATEGORIAS or {}) do ind.categorias[i] = true end

-- distancia de exibicao (m) por categoria: ajuste ao vivo > config da categoria > padrao. 0 = sem limite
ind.distanciaPadrao = IND.DISTANCIA_PADRAO_M or 150
ind.distancias = {} -- [indice] = metros (ajustes recebidos da janela)

local function distanciaDe(i)
    if ind.distancias[i] ~= nil then return ind.distancias[i] end
    local c = cfg.CATEGORIAS[i]
    if c and c.distancia ~= nil then return c.distancia end
    return ind.distanciaPadrao
end

local function dentroDoLimite(i, d)
    local lim = distanciaDe(i)
    return lim <= 0 or (d ~= nil and d >= 0 and d <= lim)
end

local function distanciaAte(it, origem)
    local dx, dy, dz = it.x - origem.X, it.y - origem.Y, it.z - origem.Z
    return math.sqrt(dx * dx + dy * dy + dz * dz) / 100
end

local function listaCategoriasReveladas()
    local t = {}
    for i = 1, #cfg.CATEGORIAS do
        if ind.categorias[i] then table.insert(t, tostring(i)) end
    end
    return t
end
local ARQ_CAMERA = PASTA_MOD .. "/camera.json"
local classePrimitiva, customDepthLigado, avisouVibracao, encerrando = nil, false, false, false

local function componentesPorClasse(ator, caminhoClasse)
    local lista = {}
    local okC, classe = pcall(StaticFindObject, caminhoClasse)
    if not okC or not classe or not classe:IsValid() then return lista end
    local ok, arr = pcall(function() return ator:K2_GetComponentsByClass(classe) end)
    if ok and arr then
        pcall(function()
            arr:ForEach(function(_, elem)
                local c = elem:get()
                if c and c:IsValid() then table.insert(lista, c) end
            end)
        end)
    end
    return lista
end

local function ligarCustomDepthGlobal(pc)
    if customDepthLigado then return end
    customDepthLigado = true
    local ok, err = pcall(function()
        local ksl = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
        ksl:ExecuteConsoleCommand(UEHelpers.GetWorld(), "r.CustomDepth 3", pc)
    end)
    if not ok then log(L("Could not enable r.CustomDepth 3: ", "Nao consegui ativar r.CustomDepth 3: ") .. tostring(err)) end
end

local function aplicarContorno(ator, valor, pc)
    if valor then ligarCustomDepthGlobal(pc) end
    for _, comp in ipairs(componentesPorClasse(ator, "/Script/Engine.PrimitiveComponent")) do
        pcall(function()
            comp:SetRenderCustomDepth(false)
            if valor then
                comp:SetCustomDepthStencilValue(valor)
                comp:SetRenderCustomDepth(true)
            end
        end)
    end
end

-- contorno nas categorias reveladas (independente da categoria do medidor/F5)
local function atualizarContornos(pc, origem)
    for i = 1, #cache do
        for _, it in ipairs(cache[i].itens) do
            local perto = origem ~= nil and dentroDoLimite(i, distanciaAte(it, origem))
            local desejado = (ind.contorno and ind.categorias[i] and perto) and ind.contornoValor or nil
            if contornoAplicado[it.nome] ~= desejado and it.ator:IsValid() then
                aplicarContorno(it.ator, desejado, pc)
                contornoAplicado[it.nome] = desejado
            end
        end
    end
end

local function vibrar(pc, origem)
    if not ind.vibracao or not origem then return end
    local melhor
    for i = 1, #cache do
        if ind.categorias[i] then
            for _, it in ipairs(cache[i].itens) do
                if it.ator:IsValid() then
                    local d = distanciaAte(it, origem)
                    if dentroDoLimite(i, d) and (not melhor or d < melhor) then melhor = d end
                end
            end
        end
    end
    if melhor and melhor <= ind.vibracaoDist then
        local intensidade = math.max(0.15, 1 - melhor / ind.vibracaoDist)
        local ok, err = pcall(function()
            pc:PlayDynamicForceFeedback(intensidade, 0.12, true, true, true, true, 0, {})
        end)
        if not ok and not avisouVibracao then
            avisouVibracao = true
            log(L("Vibration unavailable: ", "Vibracao indisponivel: ") .. tostring(err))
        end
    end
end

local seqCamera = 0
local function gravarCamera()
    local pc = UEHelpers.GetPlayerController()
    if not pc or not pc:IsValid() then return end
    local cm = pc.PlayerCameraManager
    if not cm or not cm:IsValid() then return end
    local l = cm:GetCameraLocation()
    local r = cm:GetCameraRotation()
    local fov = cm:GetFOVAngle()
    seqCamera = seqCamera + 1
    local tmp = ARQ_CAMERA .. ".tmp"
    local f = io.open(tmp, "w")
    if not f then return end
    f:write(string.format('{"seq":%d,"t":%d,"x":%.1f,"y":%.1f,"z":%.1f,"pitch":%.3f,"yaw":%.3f,"roll":%.3f,"fov":%.3f}',
        seqCamera, os.time(), l.X, l.Y, l.Z, r.Pitch, r.Yaw, r.Roll, fov))
    f:close()
    os.remove(ARQ_CAMERA)
    os.rename(tmp, ARQ_CAMERA)
end

-- F9 / comando "inspecionar": grava funcoes, propriedades e componentes do item
-- mais proximo em inspecao.txt (para descobrir como o scanner do jogo destaca itens)
local function inspecionarAtor(ator, rotulo)
    local saida = { L("Inspection of ", "Inspecao de ") .. rotulo, "" }
    local function add(s) table.insert(saida, s) end
    pcall(function() add(L("Full name: ", "Nome completo: ") .. ator:GetFullName()) end)
    pcall(function()
        local cls = ator:GetClass()
        while cls and cls:IsValid() do
            local nome = cls:GetFName():ToString()
            if nome == "Actor" or nome == "Object" then
                add("")
                add(L("== (inherits from ", "== (herda de ") .. nome .. ")")
                break
            end
            add("")
            add(L("== Class ", "== Classe ") .. nome)
            pcall(function() cls:ForEachFunction(function(fn) add(L("  function: ", "  funcao: ") .. fn:GetFName():ToString()) end) end)
            pcall(function() cls:ForEachProperty(function(p) add(L("  property: ", "  propriedade: ") .. p:GetFName():ToString()) end) end)
            local okS, sup = pcall(function() return cls:GetSuperStruct() end)
            if not okS or not sup or not sup:IsValid() then break end
            cls = sup
        end
    end)
    add("")
    add(L("== Components", "== Componentes"))
    for _, c in ipairs(componentesPorClasse(ator, "/Script/Engine.ActorComponent")) do
        pcall(function() add("  " .. c:GetClass():GetFName():ToString() .. "  " .. c:GetFName():ToString()) end)
    end
    escrever("inspecao.txt", saida)
end

local function inspecionarMaisProximo()
    local achados = buscarZunidores()
    if not achados or #achados == 0 then
        log(L("Nothing to inspect in this category.", "Nada para inspecionar nesta categoria."))
        return
    end
    inspecionarAtor(achados[1].ator, achados[1].nome .. " (" .. achados[1].classe .. ")")
end

---------------------------------------------------------------------------
local function js(s)
    return '"' .. (tostring(s):gsub('[%c"\\]', function(ch) return string.format("\\u%04x", ch:byte()) end)) .. '"'
end
local function jn(v) return string.format("%.1f", v) end
local function lerOculto(ator) return ator.bHidden end

local function gravarEstado(pc, pawn)
    local partes = {}
    local origem, yaw
    if pawn then
        origem = pawn:K2_GetActorLocation()
        yaw = pc:GetControlRotation().Yaw
    end
    local limite = MENU.MAX_ITENS_POR_CATEGORIA or 300
    for i, c in ipairs(cfg.CATEGORIAS) do
        local vivos = {}
        for _, it in ipairs(cache[i].itens) do
            if it.ator:IsValid() then
                table.insert(vivos, it)
                it.d = -1
                if origem then
                    local dx, dy, dz = it.x - origem.X, it.y - origem.Y, it.z - origem.Z
                    it.d = math.sqrt(dx * dx + dy * dy + dz * dz) / 100
                end
            end
        end
        cache[i].itens = vivos -- itens destruidos (coletados) saem da lista
        -- so os N mais proximos vao para o arquivo (Limbo tem milhares de macas)
        local ordem = vivos
        if #vivos > limite and origem then
            ordem = {}
            for k, it in ipairs(vivos) do ordem[k] = it end
            table.sort(ordem, function(a, b) return a.d < b.d end)
        end
        local itens = {}
        for k = 1, math.min(#ordem, limite) do
            local it = ordem[k]
            local okH, oculto = pcall(lerOculto, it.ator)
            local ang, dz = 0, 0
            if origem then
                ang = anguloRelativo(yaw, origem, { X = it.x, Y = it.y })
                dz = (it.z - origem.Z) / 100
            end
            itens[k] = string.format('{"n":%s,"c":%s,"d":%s,"ang":%s,"dz":%s,"x":%s,"y":%s,"z":%s,"h":%s}',
                js(it.nome), js(it.classe), jn(it.d), jn(ang), jn(dz), jn(it.x), jn(it.y), jn(it.z),
                (okH and oculto) and "true" or "false")
        end
        table.insert(partes, string.format('{"i":%d,"nome":%s,"nome_en":%s,"nome_pt":%s,"conteudo":%s,"referencia":%s,"total":%d,"dist":%s,"dist_cfg":%s,"itens":[%s]}',
            i, js(nomeCat(c)), js(c.nome_en or c.nome), js(c.nome), js(c.conteudo), js(refCat(c)), #vivos, jn(distanciaDe(i)),
            c.distancia ~= nil and jn(c.distancia) or "null", table.concat(itens, ",")))
    end
    local indicadores = string.format('{"contorno":%s,"contorno_valor":%d,"vibracao":%s,"vibracao_dist":%s,"categorias":[%s],"dist_padrao":%s}',
        ind.contorno and "true" or "false", ind.contornoValor, ind.vibracao and "true" or "false", jn(ind.vibracaoDist),
        table.concat(listaCategoriasReveladas(), ","), jn(ind.distanciaPadrao))
    local texto = string.format('{"versao":3,"idioma":"' .. idioma .. '","t":%d,"jogador":%s,"categoria_atual":%d,"indicadores":%s,"categorias":[%s]}',
        os.time(), pawn and "true" or "false", categoriaAtual, indicadores, table.concat(partes, ","))
    local tmp = ARQ_ESTADO .. ".tmp"
    local f = io.open(tmp, "w")
    if not f then return end
    f:write(texto)
    f:close()
    os.remove(ARQ_ESTADO)
    os.rename(tmp, ARQ_ESTADO)
end

local function lerComandos()
    local f = io.open(ARQ_COMANDOS, "r")
    if not f then return {} end
    local t = {}
    for l in f:lines() do
        if l:match("%S") then table.insert(t, (l:gsub("%s+$", ""))) end
    end
    f:close()
    os.remove(ARQ_COMANDOS)
    return t
end

local proximaDescoberta, proximaAtualizacao, pedirRecarga = 0, 0, false

local function executarComando(cmd, pc, pawn)
    local nome, resto = cmd:match("^(%S+)%s*(.*)$")
    if nome == "recarregar" then
        pedirRecarga = true
    elseif nome == "atualizar" then
        proximaDescoberta = 0
        log(L("Full scan requested by the menu.", "Busca completa pedida pelo menu."))
    elseif nome == "categoria" then
        definirCategoria(tonumber(resto) or categoriaAtual)
    elseif nome == "teleportar" then
        local n, ator = resto:match("^(%d+)%s+(.+)$")
        n = tonumber(n)
        if not pawn or not n or not cache[n] then return end
        for _, it in ipairs(cache[n].itens) do
            if it.nome == ator then
                teleportarPara(pawn, it.x, it.y, it.z, it.nome .. " (" .. it.classe .. ")")
                return
            end
        end
        log("Item '" .. tostring(ator) .. L("' is no longer on the map.", "' nao esta mais no mapa."))
    elseif nome == "idioma" then
        idioma = (resto == "pt-BR") and "pt-BR" or "en"
        log(L("Language: English", "Idioma: Portugues (Brasil)"))
    elseif nome == "inspecionar" then
        inspecionarMaisProximo()
    elseif nome == "indicador" and resto:match("^distancia%s") then
        -- "indicador distancia <categoria> <metros|padrao>"  (0 = sem limite)
        local ci, cv = resto:match("^distancia%s+(%d+)%s+(%S+)$")
        ci = tonumber(ci)
        if ci and cfg.CATEGORIAS[ci] then
            ind.distancias[ci] = (cv ~= "padrao") and math.max(0, tonumber(cv) or 0) or nil
            log(string.format(L("Display distance for '%s': %s", "Distancia de exibicao de '%s': %s"), nomeCat(cfg.CATEGORIAS[ci]),
                distanciaDe(ci) > 0 and string.format("%.0f m", distanciaDe(ci)) or L("no limit", "sem limite")))
        end
    elseif nome == "indicador" then
        local qual, valor = resto:match("^(%S+)%s+(%S+)$")
        local num = tonumber(valor)
        if qual == "contorno" then
            ind.contorno = valor == "1"
        elseif qual == "contorno_valor" and num then
            ind.contornoValor = math.max(1, math.min(255, math.floor(num)))
        elseif qual == "vibracao" then
            ind.vibracao = valor == "1"
        elseif qual == "distancia_padrao" and num then
            ind.distanciaPadrao = math.max(0, num)
        elseif qual == "vibracao_dist" and num then
            ind.vibracaoDist = math.max(1, num)
        elseif qual == "categorias" and valor then
            -- "1,3,5" ou "nenhuma"
            for i = 1, #cfg.CATEGORIAS do ind.categorias[i] = false end
            for n in valor:gmatch("%d+") do
                local k = tonumber(n)
                if k and k >= 1 and k <= #cfg.CATEGORIAS then ind.categorias[k] = true end
            end
        else
            return
        end
        log(string.format(L("Indicators: outline=%s (value %d), vibration=%s (%.0f m), revealed categories: %s",
            "Indicadores: contorno=%s (valor %d), vibracao=%s (%.0f m), categorias reveladas: %s"),
            tostring(ind.contorno), ind.contornoValor, tostring(ind.vibracao), ind.vibracaoDist,
            table.concat(listaCategoriasReveladas(), ",")))
    end
end

local function tickMenu()
    local pc, pawn = jogador()
    for _, cmd in ipairs(lerComandos()) do
        local ok, err = pcall(executarComando, cmd, pc, pawn)
        if not ok then log(L("Error in command '", "Erro no comando '") .. cmd .. "': " .. tostring(err)) end
    end
    local agora = os.time() * 1000
    if pawn and agora >= proximaDescoberta then
        local n = descobrirClasses()
        atualizarItens()
        proximaDescoberta = agora + MENU.INTERVALO_DESCOBERTA_MS
        proximaAtualizacao = agora + MENU.INTERVALO_ITENS_MS
        log(L("Full scan: ", "Busca completa: ") .. n .. L(" actors checked.", " atores verificados."))
    elseif pawn and agora >= proximaAtualizacao then
        atualizarItens()
        proximaAtualizacao = agora + MENU.INTERVALO_ITENS_MS
    end
    if pawn then
        local ok1, e1 = pcall(atualizarContornos, pc, pawn:K2_GetActorLocation())
        if not ok1 then log(L("Outline error: ", "Erro no contorno: ") .. tostring(e1)) end
        local ok2, e2 = pcall(vibrar, pc, pawn:K2_GetActorLocation())
        if not ok2 then log(L("Vibration error: ", "Erro na vibracao: ") .. tostring(e2)) end
    end
    gravarEstado(pc, pawn)
end

-- Os loops rodam NA THREAD DO JOGO (LoopInGameThreadWithDelay, UE4SS 4.x).
-- A versao anterior usava LoopAsync + ExecuteInGameThread: duas threads mexendo
-- no mesmo estado Lua, o que corrompeu o estado e derrubou o jogo no Limbo
-- ("Ref was not function", erro falso em ipairs e crash dentro do Lua do UE4SS).
local loops = {}

local function cancelarLoops()
    for _, h in ipairs(loops) do pcall(CancelDelayedAction, h) end
    loops = {}
end

local function recarregar()
    log(L("Reloading the mod...", "Recarregando o mod..."))
    encerrando = true
    cancelarLoops()
    if type(RestartCurrentMod) == "function" then
        ExecuteWithDelay(100, function() RestartCurrentMod() end)
    else
        log(L("RestartCurrentMod is not available in this UE4SS version; use Ctrl+R.",
            "RestartCurrentMod indisponivel nesta versao do UE4SS; use Ctrl+R."))
    end
end

-- acoes pedidas pelas teclas F6-F9: executadas pelo loop na thread do jogo
local acoesPendentes = {}

local function executarPendentes()
    local lista = acoesPendentes
    acoesPendentes = {}
    for _, fn in ipairs(lista) do
        local ok, err = pcall(fn)
        if not ok then log(L("Error: ", "Erro: ") .. tostring(err)) end
    end
end

local function tickMenuSeguro()
    if encerrando then return end
    if pedirRecarga then
        pedirRecarga = false
        recarregar()
        return
    end
    executarPendentes()
    local ok, err = pcall(tickMenu)
    if not ok then log(L("Menu error: ", "Erro no menu: ") .. tostring(err)) end
end

local function tickCameraSeguro()
    if not encerrando then pcall(gravarCamera) end
end

if MENU.ATIVO then
    if type(LoopInGameThreadWithDelay) == "function" then
        table.insert(loops, LoopInGameThreadWithDelay(MENU.INTERVALO_MS or 500, tickMenuSeguro))
        -- camera.json para a camada sobre o jogo (marcadores, seta, bussola)
        table.insert(loops, LoopInGameThreadWithDelay(MENU.CAMERA_MS or 50, tickCameraSeguro))
    else
        -- UE4SS antigo: um unico LoopAsync, sem closures novas a cada volta
        log(L("LoopInGameThreadWithDelay not available; using LoopAsync (less safe).",
            "LoopInGameThreadWithDelay indisponivel; usando LoopAsync (menos seguro)."))
        local function noJogoTick() tickMenuSeguro(); tickCameraSeguro() end
        LoopAsync(MENU.INTERVALO_MS or 500, function()
            if encerrando then return true end
            ExecuteInGameThread(noJogoTick)
            return false
        end)
    end

    -- ao trocar de mapa, recomeca a descoberta de classes
    pcall(function()
        RegisterLoadMapPostHook(function()
            zerarCache()
            proximaDescoberta = os.time() * 1000 + 5000
        end)
    end)
end

---------------------------------------------------------------------------
-- teclas
---------------------------------------------------------------------------
local usaLoopNoJogo = MENU.ATIVO and type(LoopInGameThreadWithDelay) == "function"

local function noJogo(fn)
    return function()
        if usaLoopNoJogo then
            -- so enfileira; o loop da thread do jogo executa em ate INTERVALO_MS
            table.insert(acoesPendentes, fn)
        else
            ExecuteInGameThread(function()
                local ok, err = pcall(fn)
                if not ok then log(L("Error: ", "Erro: ") .. tostring(err)) end
            end)
        end
    end
end

RegisterKeyBind(Key.F5, trocarCategoria)
RegisterKeyBind(Key.F6, noJogo(listarClasses))
RegisterKeyBind(Key.F7, noJogo(listar))
RegisterKeyBind(Key.F8, noJogo(teleportar))
RegisterKeyBind(Key.F9, noJogo(inspecionarMaisProximo))

log(L("Loaded. Category: ", "Carregado. Categoria: ") .. nomeCat(categoria()) ..
    L(". F5 = next category, F6 = map classes, F7 = list, F8 = teleport, F9 = inspect.",
      ". F5 = trocar categoria, F6 = classes do mapa, F7 = listar, F8 = teleportar, F9 = inspecionar.") ..
    (MENU.ATIVO and L(" Menu: estado.json active.", " Menu: estado.json ativo.") or ""))
