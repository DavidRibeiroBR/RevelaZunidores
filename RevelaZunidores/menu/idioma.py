"""Idioma da janela do RevelaZunidores: inglês (padrão) ou português (Brasil).

Os textos do código-fonte estão em português; com o idioma "en", T() devolve a
tradução em inglês. aplicar() percorre os widgets e traduz rótulos fixos
(botões, caixas de seleção, abas, menus, títulos de colunas).
"""
import tkinter as tk

IDIOMAS = {"en": "English", "pt-BR": "Português (Brasil)"}
LANG = "en"


def definir(lang):
    global LANG
    LANG = "pt-BR" if lang == "pt-BR" else "en"


def T(texto):
    if LANG == "pt-BR":
        return texto
    return EN.get(texto, texto)


EN = {
    # menus
    "Mod": "Mod",
    "Recarregar mod": "Reload mod",
    "Atualizar busca": "Refresh scan",
    "Teleportar para o mais próximo": "Teleport to nearest",
    "Inspecionar item mais próximo (F9)": "Inspect nearest item (F9)",
    "Abrir pasta do mod": "Open mod folder",
    "Sair": "Exit",
    "Categorias reveladas": "Revealed categories",
    "Camada sobre o jogo": "Game overlay",
    "   Marcadores através das paredes": "   Markers through walls",
    "   Seta na borda da tela": "   Screen-edge arrow",
    "   Bússola": "   Compass",
    "Bipe de proximidade": "Proximity beep",
    "Voz": "Voice",
    "Contorno no jogo (experimental)": "In-game outline (experimental)",
    "Vibração do controle (experimental)": "Controller vibration (experimental)",
    "Revelação": "Reveal",
    "Exibir": "View",
    "Janela sempre por cima": "Window always on top",
    "Expandir todas as categorias": "Expand all categories",
    "Recolher todas as categorias": "Collapse all categories",
    "Ajuda": "Help",
    "Como usar": "How to use",
    "Marcar todas": "Check all",
    "Desmarcar todas": "Uncheck all",
    # janela principal / aba Busca
    "Aguardando o jogo…": "Waiting for the game…",
    "⟳ Recarregar mod": "⟳ Reload mod",
    "Busca": "Search",
    "Opacidade da janela": "Window opacity",
    "Medidor de distância": "Distance meter",
    "Categoria:": "Category:",
    "Filtro": "Filter",
    "Texto:": "Text:",
    "Limpar": "Clear",
    "Distância máx. (m, 0 = sem limite):": "Max. distance (m, 0 = no limit):",
    "Categorias ▾": "Categories ▾",
    "Esconder itens ocultos": "Hide hidden items",
    "Esconder categorias vazias": "Hide empty categories",
    "Colecionáveis por categoria": "Collectibles by category",
    "▸ Recolher/expandir categoria": "▸ Collapse/expand category",
    "Expandir todas": "Expand all",
    "Recolher todas": "Collapse all",
    "Item": "Item",
    "Distância": "Distance",
    "Direção": "Direction",
    "Altura": "Height",
    "Duplo clique em um item = teleportar até ele": "Double-click an item = teleport to it",
    # aba Revelação
    "A revelação é independente da aba Busca: escolha aqui quais tipos de coletável são revelados e por quais métodos.":
        "Reveal is independent of the Search tab: choose here which collectible types are revealed and by which methods.",
    "Categorias": "Categories",
    "Na tela": "On screen",
    "Som e voz": "Sound & voice",
    "No jogo": "In game",
    "Tipos de coletável revelados (marcadores, seta, bússola, bipe, voz, contorno e vibração):":
        "Revealed collectible types (markers, arrow, compass, beep, voice, outline and vibration):",
    "(as categorias aparecem quando o mod ou a demo enviar o estado)":
        "(categories appear once the mod or the demo sends its state)",
    "Só a do medidor": "Only the meter's",
    "Distância de exibição": "Display distance",
    "Padrão para todas as categorias:": "Default for all categories:",
    "Rápido:": "Quick:",
    "Todas = padrão": "All = default",
    "Cada categoria pode ter a sua (coluna Distância acima). Só itens até essa distância recebem marcador, seta, bússola, bipe, voz e contorno.":
        "Each category can have its own (Distance column above). Only items within that distance get markers, arrow, compass, beep, voice and outline.",
    "Não revelar itens ocultos": "Don't reveal hidden items",
    "Limite em uso": "Limit in use",
    "Ativar camada sobre o jogo (Ctrl+Shift+O)": "Enable game overlay (Ctrl+Shift+O)",
    "Marcadores nos itens (visíveis através das paredes)": "Item markers (visible through walls)",
    "   mostrar o nome do ator no marcador": "   show the actor name on the marker",
    "Seta na borda da tela apontando o mais próximo": "Screen-edge arrow pointing to the nearest",
    "Bússola no topo da tela": "Compass at the top of the screen",
    "Máx. de marcadores:": "Max. markers:",
    "Cada categoria tem sua cor (veja a subaba Categorias). Requer o jogo em modo janela ou janela sem bordas. Se o add-on do ReShade estiver ativo, esta camada pausa sozinha.":
        "Each category has its own color (see the Categories sub-tab). Requires the game in windowed or borderless mode. If the ReShade add-on is active, this overlay pauses itself.",
    "Bipe de proximidade — mais rápido e agudo quanto mais perto (Ctrl+Shift+B)":
        "Proximity beep — faster and higher-pitched the closer you get (Ctrl+Shift+B)",
    "Alcance (m):": "Range (m):",
    "Volume:": "Volume:",
    "Voz — anuncia tipo, distância e direção ao se aproximar (Ctrl+Shift+V)":
        "Voice — announces type, distance and direction as you approach (Ctrl+Shift+V)",
    "anunciar quando um item for coletado": "announce when an item is collected",
    "Testar voz": "Test voice",
    "O bipe e a voz seguem o item revelado mais próximo, de qualquer categoria marcada.":
        "The beep and the voice follow the nearest revealed item, from any checked category.",
    "Contorno no item (Custom Depth/Stencil) — experimental": "Item outline (Custom Depth/Stencil) — experimental",
    "Valor de stencil (1–255):": "Stencil value (1–255):",
    "Só aparece se o pós-processamento do jogo usar esse valor. Vá trocando até algum destacar o item.":
        "Only shows if the game's post-processing uses this value. Keep changing it until one highlights the item.",
    "Vibração do controle quando perto — experimental": "Controller vibration when close — experimental",
    "Distância (m):": "Distance (m):",
    "Inspecionar item mais próximo (grava inspecao.txt)": "Inspect nearest item (writes inspecao.txt)",
    "Atalhos globais: Ctrl+Shift+O camada · B bipe · V voz · M mostrar/ocultar janela · N próxima categoria do medidor":
        "Global hotkeys: Ctrl+Shift+O overlay · B beep · V voice · M show/hide window · N next meter category",
    # textos dinamicos
    "à frente": "ahead",
    "atrás": "behind",
    "frente-{}": "ahead-{}",
    "atrás-{}": "behind-{}",
    "à {}": "to the {}",
    "direita": "right",
    "esquerda": "left",
    "{} m (acima)": "{} m (above)",
    "{} m (abaixo)": "{} m (below)",
    "mesmo nível": "same level",
    "padrão": "default",
    "sem limite": "no limit",
    "dados simulados": "simulated data",
    "Zunidores (Chirpers)": "Chirpers",
    "Corpos falantes": "Talking Dead",
    "Baus Lootyagin": "Lootyagin Chests",
    "Macas (Limbo)": "Apples (Limbo)",
    "Estatuetas / golfinho": "Figurines / Dolphin",
    "[demo] comando: {}": "[demo] command: {}",
    "Não consegui enviar o comando:\n{}": "Could not send the command:\n{}",
    "Categoria {}": "Category {}",
    "Voz ligada": "Voice on",
    "Voz desligada": "Voice off",
    "Teste de voz do RevelaZunidores": "RevelaZunidores voice test",
    "⚠ Sem sinal do jogo há {:.0f} s (jogo fechado ou mod parado)": "⚠ No signal from the game for {:.0f} s (game closed or mod stopped)",
    "● Conectado — carregue um save para começar": "● Connected — load a save to start",
    "● Conectado — {} itens no mapa carregado": "● Connected — {} items on the loaded map",
    "● Add-on do ReShade ativo — camada desta janela pausada": "● ReShade add-on active — this window's overlay is paused",
    "Aguardando o jogo… (estado.json ainda não existe)": "Waiting for the game… (estado.json does not exist yet)",
    "Mod sem suporte a indicadores (versão antiga?) — recarregue o mod.": "Mod has no indicator support (old version?) — reload the mod.",
    "No jogo: contorno {} (stencil {}), vibração {} ({:.0f} m), categorias {}": "In game: outline {} (stencil {}), vibration {} ({:.0f} m), categories {}",
    "ligado": "on",
    "desligado": "off",
    "ligada": "on",
    "desligada": "off",
    "nenhuma": "none",
    "{} de {} categorias reveladas · {} itens no mapa carregado": "{} of {} categories revealed · {} items on the loaded map",
    " · mais próximo: {} a {}": " · nearest: {} at {}",
    "Coletado. Restam {} itens revelados no mapa.": "Collected. {} revealed items left on the map.",
    "{:.0f} metros, {}": "{:.0f} meters, {}",
    "{}: {}": "{}: {}",
    "{}, {}": "{}, {}",
    "Nenhum item desta categoria no mapa carregado": "No items of this category on the loaded map",
    "Referência: {}": "Reference: {}",
    "  · OCULTO": "  · HIDDEN",
    "{}  ({} na categoria · ref.: {})": "{}  ({} in category · ref.: {})",
    " — mais perto: {}": " — nearest: {}",
    ", {} mais próximos listados": ", {} nearest listed",
    "Idioma alterado. A janela será reaberta.": "Language changed. The window will reopen.",
}


def aplicar(raiz):
    """Traduz rótulos fixos de todos os widgets abaixo de raiz (inclusive menus e abas)."""
    if LANG == "pt-BR":
        return
    pilha = [raiz]
    while pilha:
        w = pilha.pop()
        pilha.extend(w.winfo_children())
        try:
            t = w.cget("text")
            if isinstance(t, str) and t in EN:
                w.configure(text=EN[t])
        except (tk.TclError, AttributeError):
            pass
        cls = w.winfo_class()
        if cls == "TNotebook":
            for aba in w.tabs():
                t = w.tab(aba, "text")
                if t in EN:
                    w.tab(aba, text=EN[t])
        elif cls == "Treeview":
            for col in ("#0",) + tuple(w["columns"]):
                t = w.heading(col, "text")
                if t in EN:
                    w.heading(col, text=EN[t])
        elif cls == "Menu":
            fim = w.index("end")
            if fim is not None:
                for i in range(fim + 1):
                    try:
                        t = w.entrycget(i, "label")
                    except tk.TclError:
                        continue
                    if t in EN:
                        w.entryconfigure(i, label=EN[t])
