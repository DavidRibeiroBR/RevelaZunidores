-- Configuracao do RevelaZunidores
--
-- Cada categoria tem palavras-chave buscadas no NOME DA CLASSE dos atores
-- (sem diferenciar maiusculas/minusculas). "caminho" (opcional) exige que o
-- nome completo do ator (que inclui o mapa/nivel) contenha aquele texto.
--
-- Nomes CONFIRMADOS no save da campanha (11.sav, descomprimido em 14/11/2026):
--   Zunidores/Chirpers ... BP_Pickupable_AudioDiary  (tags AudioDiary.<Zona>.Schebetar.N)
--   Corpos falantes ...... BP_CorpseDialog
--   Baus dos Campos ...... BP_LootBox_Crate / CrateSilver / CrateGold nos mapas Indoor/Polygons
--   Projetos ............. BP_Pickable_<Arma>_Recipe (pasta RecipesTubus)
--   Macas de Limbo ....... BP_Collectable_Limbo_Apple
-- Nomes CONFIRMADOS nos saves de Trapped in Limbo (25-28.sav, mapa limboWorld_DLC2):
--   Moedas de ouro ....... BP_Collectable_Limbo_Coin_WithCounter  (/Game/DLC2/.../Collectables/)
--   Macas de surf ........ BP_Collectable_Limbo_Apple_Surf (+ _Surf_Spawn, ponto de spawn, ignorado)
--   Loja das moedas ...... BP_DLC2Shop / BP_DLC2ShopManager
-- Nomes ENCONTRADOS nos indices dos .pak do jogo (DLCs ainda nao iniciadas,
-- a classe existe mas a contagem no mapa ainda nao foi conferida):
--   Chirpers DLC2/DLC3 ... BP_Pickupable_AudioDiary_Limbo / BP_DLC03_Pickupable_AudioDiary_Child
--   Cartas Alionka ....... BP_Pickable_Alenka (DLC1, /Game/DLC/)
--   Projetos das DLCs .... BP_Pickable_Klusha_*_Recipe, BP_Pickable_Plasmagun_*_Recipe, Kuzmich, Gromoverzhec
--   Esconderijo Cacador .. BP_LootBox_CrateHunter_DLC3
--   Estatuetas DLC4 ...... BP_PickableBoy_Collectable_<Local> (11 classes = 11 da conquista)
--   Golfinho secreto ..... BP_Pickble_Dolphin_DLC4 (mascotes da DLC3: BP_Pickble_Dolphin_Mascot_*)
--   Corpos DLC4 .......... BP_DLC4_CrystalPeople_Corpses (a verificar se sao os "corpos falantes")
-- Peras de Limbo e a boneca estranha da DLC4 nao tem classe propria nos .pak;
-- talvez sejam uma variacao de outra classe (ex.: ENUM_MoneyType das moedas). Use F6.
--
-- Quantidades de referencia: prioridade para o contador das conquistas da Steam
-- (steamcommunity.com/stats/668580/achievements, consultado em 14/11/2026).
-- "Steam" = contador da conquista; "guias" = catalogo atomic_heart_colecionaveis_referencias.md,
-- usado so quando nao existe conquista com contador para aquele item.
return {
    -- Idioma das mensagens do mod e dos nomes das categorias: "en" (padrao) ou "pt-BR".
    -- A janela de menu e o add-on do ReShade seguem este idioma (cada um pode trocar).
    IDIOMA = "en",

    CATEGORIAS = {
        -- Jogo base
        { nome = "Zunidores (Chirpers)", nome_en = "Chirpers",      conteudo = "Base + DLCs", palavras = { "Pickupable_AudioDiary" },
          referencia = "Base 73 (Steam: Burning Ears) | DLC1 10, DLC3 17, DLC4 16 ou 17 (guias)",
          referencia_en = "Base 73 (Steam: Burning Ears) | DLC1 10, DLC3 17, DLC4 16 or 17 (guides)" },
        { nome = "Corpos falantes", nome_en = "Talking Dead",           conteudo = "Base + DLC3", palavras = { "CorpseDialog", "CrystalPeople_Corpses" },
          referencia = "Base 46 (Steam: The Necromancer) | DLC3 10 (guias)",
          referencia_en = "Base 46 (Steam: The Necromancer) | DLC3 10 (guides)" },
        { nome = "Animais falantes / mortos", nome_en = "Talking / Dead Animals", conteudo = "Base + DLCs", palavras = { "TalkingAnimal", "AnimalDialogue", "DeadAnimal", "Dolphin_Dead" },
          referencia = "Base 3 (Steam: Beast Friend) | DLC3 1, DLC4 1 (guias)",
          referencia_en = "Base 3 (Steam: Beast Friend) | DLC3 1, DLC4 1 (guides)" },
        { nome = "Baus Lootyagin", nome_en = "Lootyagin Chests",            conteudo = "Base",        palavras = { "LootBox_Crate" }, caminho = "/Indoor/Polygons/",
          referencia = "24 (Steam: More Than Profit), em 8 Campos de Teste (Steam: Explorer/Clean-up)",
          referencia_en = "24 (Steam: More Than Profit), in 8 Testing Grounds (Steam: Explorer/Clean-up)" },
        { nome = "Projetos (Blueprints)", nome_en = "Blueprints",     conteudo = "Base + DLC1", palavras = { "_Recipe" },
          referencia = "Base 63 (guias; sem conquista com contador)",
          referencia_en = "Base 63 (guides; no achievement counter)" },
        -- DLC 1 - Annihilation Instinct
        { nome = "Cartas Alionka", nome_en = "Alionka Cards",            conteudo = "DLC1",        palavras = { "Pickable_Alenka" },
          referencia = "5 (guias; sem conquista com contador)",
          referencia_en = "5 (guides; no achievement counter)" },
        -- DLC 2 - Trapped in Limbo
        { nome = "Macas (Limbo)", nome_en = "Apples (Limbo)",             conteudo = "DLC2",        palavras = { "Collectable_Limbo_Apple" }, distancia = 40,
          referencia = "114 (Steam: Apple Pie, 'todas as macas') | 3826 (Steam: Apple Pie 3826, total coletado)",
          referencia_en = "114 (Steam: Apple Pie, 'all apples') | 3826 (Steam: Apple Pie 3826, total collected)" },
        { nome = "Moedas (Limbo)", nome_en = "Gold Coins (Limbo)",            conteudo = "DLC2",        palavras = { "Collectable_Limbo_Coin" },
          referencia = "76 (Steam: Gold Rush) + 77a extra (Steam: Overkill, oculta) | guias citam 80",
          referencia_en = "76 (Steam: Gold Rush) + extra 77th (Steam: Overkill, hidden) | guides say 80" },
        { nome = "Peras (Limbo)", nome_en = "Pears (Limbo)",             conteudo = "DLC2",        palavras = { "Collectable_Limbo_Pear", "Pear", "Grusha" }, caminho = "/DLC2/",
          referencia = "10 (guias; sem conquista com contador)",
          referencia_en = "10 (guides; no achievement counter)" },
        -- DLC 3 - Enchantment Under the Sea
        { nome = "Esconderijos do Cacador", nome_en = "Hunter's Stashes",   conteudo = "DLC3",        palavras = { "CrateHunter" },
          referencia = "3 (Steam: Master of Survival)",
          referencia_en = "3 (Steam: Master of Survival)" },
        -- DLC 4 - Blood on Crystal
        { nome = "Estatuetas / golfinho", nome_en = "Figurines / Dolphin",     conteudo = "DLC4",        palavras = { "PickableBoy_Collectable", "Pickble_Dolphin_DLC4" },
          referencia = "11 (Steam: Crystal Platinum) + golfinho secreto (Steam: Better Late Than Never)",
          referencia_en = "11 (Steam: Crystal Platinum) + secret dolphin (Steam: Better Late Than Never)" },
    },

    -- Categoria ativa ao carregar o jogo (indice na lista acima). 1 = Zunidores.
    CATEGORIA_INICIAL = 1,

    -- Palavras que excluem um ator mesmo que ele bata com a categoria
    -- (gerenciadores, spawners, componentes de UI etc.).
    IGNORAR = {
        "Manager",
        "Subsystem",
        "Widget",
        "Spawner",
        "Settings",
        "Controller",
        "_Spawn",
    },

    -- Quantos resultados mostrar no console ao apertar F7
    MAX_LISTA = 30,

    -- Altura (em cm) acima do item ao teleportar com F8, para nao ficar preso no chao
    ALTURA_TELEPORTE = 120,

    -- Comunicacao com a janela de menu (menu\menu_revela.pyw)
    MENU = {
        ATIVO = true,
        -- A cada quantos ms o mod grava estado.json (posicao do jogador e distancias)
        INTERVALO_MS = 500,
        -- A cada quantos ms o mod rele a posicao dos itens das classes ja conhecidas
        INTERVALO_ITENS_MS = 3000,
        -- A cada quantos ms o mod varre TODOS os atores para descobrir classes novas
        -- (e a operacao mais pesada; tambem roda ao trocar de mapa e no botao "Atualizar busca")
        INTERVALO_DESCOBERTA_MS = 60000,
        -- Logo depois de carregar um save ou trocar de mapa, o nivel ainda esta
        -- carregando: a busca completa se repete a cada INTERVALO_DESCOBERTA_RAPIDA_MS
        -- ate o numero de atores estabilizar (ou DESCOBERTA_RAPIDA_MAX_MS passar)
        INTERVALO_DESCOBERTA_RAPIDA_MS = 3000,
        DESCOBERTA_RAPIDA_MAX_MS = 45000,
        -- A cada quantos ms o mod grava camera.json (usado pela camada sobre o jogo)
        CAMERA_MS = 50,
        -- Quantos itens por categoria (os mais proximos) vao para estado.json.
        -- O Limbo tem milhares de macas; gravar todas a cada 0,5 s pesa no jogo.
        MAX_ITENS_POR_CATEGORIA = 300,
    },

    -- Indicadores que rodam DENTRO do jogo (os de tela/som/voz ficam na janela de menu).
    -- Todos podem ser ligados/desligados pela janela de menu, aba "Indicadores".
    INDICADORES = {
        -- Categorias reveladas (indices da lista CATEGORIAS). Independente da
        -- categoria do medidor/F5. nil = todas. Ex.: { 1, 2, 4 }
        CATEGORIAS = nil,
        -- Distancia de exibicao (metros) dos itens revelados: marcadores, seta, bussola,
        -- bipe, voz e contorno so consideram itens ate essa distancia. 0 = sem limite.
        -- Cada categoria pode ter a sua com "distancia = N" na lista CATEGORIAS
        -- (ex.: as macas de Limbo usam 40 m). A janela e o ReShade podem mudar ao vivo.
        DISTANCIA_PADRAO_M = 150,
        -- Contorno via Custom Depth/Stencil (EXPERIMENTAL): so aparece se o
        -- pos-processamento do jogo usar este valor de stencil. Teste valores
        -- pela janela (1 a 255) ate algum destacar o item.
        CONTORNO = false,
        CONTORNO_VALOR = 252,
        -- Vibracao do controle quando o item mais proximo da categoria estiver perto (EXPERIMENTAL)
        VIBRACAO = false,
        VIBRACAO_DISTANCIA_M = 15,
    },
}
