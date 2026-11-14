"""Menu do RevelaZunidores (Atomic Heart).

Janela que conversa com o mod Lua por arquivos:
  - le    ../estado.json  (itens e distancias, a cada 0,5 s)
  - le    ../camera.json  (camera do jogador, a cada 50 ms - usado pela camada sobre o jogo)
  - grava ../comandos.txt (recarregar, atualizar, categoria, teleportar, indicador, inspecionar)

Uso:
  pythonw menu_revela.pyw                        # normal
  python  menu_revela.pyw --demo                 # dados simulados, sem o jogo
  python  menu_revela.pyw --demo --autoteste 8   # abre, testa e fecha
"""
import ctypes
import json
import math
import os
import random
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

PASTA_MENU = os.path.dirname(os.path.abspath(__file__))
if PASTA_MENU not in sys.path:
    sys.path.insert(0, PASTA_MENU)
import indicadores as ind  # noqa: E402
import idioma  # noqa: E402
from idioma import T  # noqa: E402

PASTA_MOD = os.path.dirname(PASTA_MENU)
ARQ_ESTADO = os.path.join(PASTA_MOD, "estado.json")
ARQ_CAMERA = os.path.join(PASTA_MOD, "camera.json")
ARQ_COMANDOS = os.path.join(PASTA_MOD, "comandos.txt")
ARQ_PREFS = os.path.join(PASTA_MENU, "preferencias.json")
ARQ_RESHADE = os.path.join(PASTA_MOD, "reshade_ativo.txt")  # gravado pelo add-on do ReShade

ATUALIZAR_MS = 500
SEM_SINAL_S = 5
ESCALA_MEDIDOR_M = 300
LIMIARES_VOZ = (200, 100, 50, 25, 10, 5)

try:  # coordenadas em pixels reais (necessario para a camada coincidir com o jogo)
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


# ---------------------------------------------------------------------------
# texto
# ---------------------------------------------------------------------------
def direcao_texto(ang):
    a = abs(ang)
    lado = T("direita") if ang >= 0 else T("esquerda")
    if a <= 22.5:
        return T("à frente")
    if a <= 67.5:
        return T("frente-{}").format(lado)
    if a <= 112.5:
        return T("à {}").format(lado)
    if a <= 157.5:
        return T("atrás-{}").format(lado)
    return T("atrás")


def altura_texto(dz):
    if dz > 3:
        return T("{} m (acima)").format(f"{dz:+.0f}")
    if dz < -3:
        return T("{} m (abaixo)").format(f"{dz:+.0f}")
    return T("mesmo nível")


def opcoes_dist():
    return [T("padrão"), T("sem limite"), "25", "40", "50", "75", "100", "150", "200", "300", "500", "1000"]


def opcoes_dist_padrao():
    return [T("sem limite"), "25", "50", "100", "150", "200", "300", "500", "1000"]


def ler_dist(txt):
    """'padrão' -> None (usa o padrão), 'sem limite' -> 0, '120 m' -> 120.0"""
    t = str(txt).strip().lower()
    if not t or t.startswith(("padr", "default")):
        return None
    if t.startswith(("sem", "no lim", "no ", "unlim")):
        return 0.0
    t = t.rstrip("m").replace(",", ".").strip()  # aceita "120 m"
    if t == "0":
        return 0.0
    try:
        return max(0.0, float(t))
    except ValueError:
        return None


def texto_limite(v):
    return T("sem limite") if not v else f"{v:.0f} m"


def dist_texto(d):
    if d < 0:
        return "—"
    if d >= 1000:
        return f"{d / 1000:.2f} km"
    return f"{d:.0f} m"


# ---------------------------------------------------------------------------
# dados simulados (--demo)
# ---------------------------------------------------------------------------
class Demo:
    NOMES = ["Zunidores (Chirpers)", "Corpos falantes", "Baus Lootyagin", "Macas (Limbo)", "Estatuetas / golfinho"]

    def __init__(self):
        random.seed(3826)
        self.t0 = time.time()
        self.cats = []
        for i, nome in enumerate(self.NOMES, 1):
            itens = []
            for k in range(random.randint(0 if i == 4 else 2, 9)):
                ang = random.uniform(-math.pi, math.pi)
                r = random.uniform(500, 20000)
                itens.append({"n": f"BP_Demo_{i}_{k}", "c": f"BP_Demo{i}_C",
                              "x": r * math.cos(ang), "y": r * math.sin(ang),
                              "z": random.uniform(-800, 1500), "h": k == 1})
            self.cats.append({"i": i, "nome": T(nome), "conteudo": "Demo", "referencia": T("dados simulados"), "itens": itens})

    def camera(self):
        t = time.time() - self.t0
        return {"seq": int(t * 20), "t": int(time.time()), "x": 1500 * math.cos(t / 6), "y": 1500 * math.sin(t / 6),
                "z": 170.0, "pitch": -5 + 5 * math.sin(t / 3), "yaw": (t * 25) % 360 - 180, "roll": 0.0, "fov": 90.0}

    def estado(self, indicadores):
        cam = self.camera()
        cats = []
        for c in self.cats:
            itens = []
            for it in c["itens"]:
                dx, dy, dz = it["x"] - cam["x"], it["y"] - cam["y"], it["z"] - cam["z"]
                ang = ind.normalizar(math.degrees(math.atan2(dy, dx)) - cam["yaw"])
                itens.append({**it, "d": math.sqrt(dx * dx + dy * dy + dz * dz) / 100, "ang": ang, "dz": dz / 100})
            dist = indicadores.get("distancias", {}).get(c["i"], 150.0)
            cats.append({**c, "itens": itens, "dist": dist, "dist_cfg": 40.0 if c["i"] == 4 else None})
        return {"versao": 3, "t": int(time.time()), "jogador": True, "categoria_atual": 1,
                "indicadores": {**indicadores, "dist_padrao": 150.0}, "categorias": cats}


# ---------------------------------------------------------------------------
# janela
# ---------------------------------------------------------------------------
def idioma_inicial(prefs):
    escolha = prefs.get("idioma", "auto")
    if escolha in idioma.IDIOMAS:
        return escolha
    try:
        with open(ARQ_ESTADO, encoding="utf-8") as f:
            return json.load(f).get("idioma", "en")
    except (OSError, ValueError):
        return "en"


class Menu(tk.Tk):
    def __init__(self, demo=None):
        super().__init__()
        self.demo = None
        self.title("RevelaZunidores — Atomic Heart" + ("  [DEMO]" if demo else ""))
        self.geometry("600x780")
        self.minsize(480, 560)
        self.estado = None
        self.abertas = {}
        self.cat_visivel = {}
        self.selecionado = None
        self.erros = []
        self.prefs = self._ler_prefs()
        if "--en" in sys.argv or "--pt" in sys.argv:  # usado nos testes
            self.prefs["idioma"] = "pt-BR" if "--pt" in sys.argv else "en"
        idioma.definir(idioma_inicial(self.prefs))
        self.demo = Demo() if demo else None
        P = self.prefs.get

        # busca
        self.var_topo = tk.BooleanVar(value=P("topo", True))
        self.var_opac = tk.DoubleVar(value=P("opacidade", 0.95))
        self.var_texto = tk.StringVar()
        self.var_max = tk.StringVar(value=str(P("max_m", 0)))
        self.var_ocultos = tk.BooleanVar(value=P("esconder_ocultos", False))
        self.var_vazias = tk.BooleanVar(value=P("esconder_vazias", False))
        self.var_cat = tk.StringVar()
        # indicadores na tela
        self.var_camada = tk.BooleanVar(value=P("camada", True))
        self.var_marcadores = tk.BooleanVar(value=P("marcadores", True))
        self.var_nomes = tk.BooleanVar(value=P("nomes", False))
        self.var_seta = tk.BooleanVar(value=P("seta", True))
        self.var_bussola = tk.BooleanVar(value=P("bussola", True))
        self.var_max_marc = tk.StringVar(value=str(P("max_marcadores", 40)))
        # revelacao: categorias proprias, independentes da aba Busca
        self.cat_revelar = {}
        self.var_dist_padrao = tk.StringVar(value=str(P("dist_padrao", "")))  # vazio = usar o do mod
        self.cat_dist = {}  # "numero da categoria" -> StringVar ("padrão", "sem limite" ou metros)
        self.lbl_limite = {}
        self.var_rev_ocultos = tk.BooleanVar(value=P("rev_ocultos", False))
        # som e voz
        self.var_bip = tk.BooleanVar(value=P("bip", False))
        self.var_alcance = tk.StringVar(value=str(P("alcance_bip", 100)))
        self.var_volume = tk.DoubleVar(value=P("volume_bip", 0.5))
        self.var_voz = tk.BooleanVar(value=P("voz", False))
        self.var_voz_coleta = tk.BooleanVar(value=P("voz_coleta", True))
        # dentro do jogo (Lua)
        self.var_contorno = tk.BooleanVar(value=P("contorno", False))
        self.var_contorno_valor = tk.StringVar(value=str(P("contorno_valor", 252)))
        self.var_vibracao = tk.BooleanVar(value=P("vibracao", False))
        self.var_vibracao_dist = tk.StringVar(value=str(P("vibracao_dist", 15)))

        self._ultimo_sync = 0.0
        self._voz_estado = {"alvo": None, "limiar": None, "contagem": None}
        self._cam_cache = (None, None)

        self.bip = ind.Bip()
        self.voz = ind.Voz(idioma.LANG)
        self.atalhos = ind.Atalhos()
        self.overlay = ind.Overlay(self, self.ler_camera, regiao_fixa=(60, 60, 960, 540) if demo else None)

        self._estilo()
        self._menu()
        self._layout()
        self._aplicar_topo()
        self._aplicar_camada()
        idioma.aplicar(self)
        self.protocol("WM_DELETE_WINDOW", self.fechar)
        self.after(50, self.atualizar)
        self.after(100, self._ler_atalhos)

    # ---- preferencias -----------------------------------------------------
    def _ler_prefs(self):
        try:
            with open(ARQ_PREFS, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _gravar_prefs(self):
        g = lambda v: v.get()
        p = {"topo": g(self.var_topo), "opacidade": round(g(self.var_opac), 2), "max_m": self._num(self.var_max),
             "esconder_ocultos": g(self.var_ocultos), "esconder_vazias": g(self.var_vazias),
             "abertas": self.abertas, "categoria": (self._cat_atual() or {}).get("i"), "geometria": self.geometry(),
             "visiveis": {k: v.get() for k, v in self.cat_visivel.items()},
             "camada": g(self.var_camada), "marcadores": g(self.var_marcadores), "nomes": g(self.var_nomes),
             "seta": g(self.var_seta), "bussola": g(self.var_bussola), "max_marcadores": int(self._num(self.var_max_marc, 40)),
             "revelar": {k: v.get() for k, v in self.cat_revelar.items()}, "dist_padrao": self.var_dist_padrao.get(), "dist_cat": {k: v.get() for k, v in self.cat_dist.items()}, "rev_ocultos": g(self.var_rev_ocultos), "bip": g(self.var_bip), "alcance_bip": self._num(self.var_alcance, 100),
             "volume_bip": round(g(self.var_volume), 2), "voz": g(self.var_voz), "voz_coleta": g(self.var_voz_coleta),
             "contorno": g(self.var_contorno), "contorno_valor": int(self._num(self.var_contorno_valor, 252)),
             "vibracao": g(self.var_vibracao), "vibracao_dist": self._num(self.var_vibracao_dist, 15),
             "idioma": self.var_idioma.get() if hasattr(self, "var_idioma") else self.prefs.get("idioma", "auto")}
        try:
            with open(ARQ_PREFS, "w", encoding="utf-8") as f:
                json.dump(p, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def fechar(self):
        if not self.demo:
            self._gravar_prefs()
        self.overlay.desligar()
        self.voz.encerrar()
        self.destroy()

    def registrar_erro(self, msg):
        if msg not in self.erros:
            self.erros.append(msg)
            print("ERRO:", msg, file=sys.stderr)

    # ---- montagem ---------------------------------------------------------
    def _estilo(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Dist.TLabel", font=("Segoe UI", 26, "bold"))
        st.configure("Sub.TLabel", font=("Segoe UI", 10))
        st.configure("Status.TLabel", font=("Segoe UI", 9))
        st.configure("Treeview", rowheight=22)
        if "geometria" in self.prefs:
            try:
                self.geometry(self.prefs["geometria"])
            except tk.TclError:
                pass

    def _menu(self):
        barra = tk.Menu(self)
        m_mod = tk.Menu(barra, tearoff=False)
        m_mod.add_command(label="Recarregar mod", command=self.cmd_recarregar, accelerator="Ctrl+R")
        m_mod.add_command(label="Atualizar busca", command=self.cmd_atualizar, accelerator="F5")
        m_mod.add_separator()
        m_mod.add_command(label="Teleportar para o mais próximo", command=self.cmd_tele_proximo)
        m_mod.add_command(label="Inspecionar item mais próximo (F9)", command=lambda: self.enviar("inspecionar"))
        m_mod.add_separator()
        m_mod.add_command(label="Abrir pasta do mod", command=lambda: os.startfile(PASTA_MOD))
        m_mod.add_separator()
        m_mod.add_command(label="Sair", command=self.fechar)
        barra.add_cascade(label="Mod", menu=m_mod)

        m_ind = tk.Menu(barra, tearoff=False)
        self.menu_revelar = tk.Menu(m_ind, tearoff=False)
        m_ind.add_cascade(label="Categorias reveladas", menu=self.menu_revelar)
        m_ind.add_separator()
        m_ind.add_checkbutton(label="Camada sobre o jogo", variable=self.var_camada, command=self._aplicar_camada, accelerator="Ctrl+Shift+O")
        m_ind.add_checkbutton(label="   Marcadores através das paredes", variable=self.var_marcadores)
        m_ind.add_checkbutton(label="   Seta na borda da tela", variable=self.var_seta)
        m_ind.add_checkbutton(label="   Bússola", variable=self.var_bussola)
        m_ind.add_separator()
        m_ind.add_checkbutton(label="Bipe de proximidade", variable=self.var_bip, accelerator="Ctrl+Shift+B")
        m_ind.add_checkbutton(label="Voz", variable=self.var_voz, accelerator="Ctrl+Shift+V")
        m_ind.add_separator()
        m_ind.add_checkbutton(label="Contorno no jogo (experimental)", variable=self.var_contorno, command=self.sync_lua)
        m_ind.add_checkbutton(label="Vibração do controle (experimental)", variable=self.var_vibracao, command=self.sync_lua)
        barra.add_cascade(label="Revelação", menu=m_ind)

        m_ex = tk.Menu(barra, tearoff=False)
        m_ex.add_checkbutton(label="Janela sempre por cima", variable=self.var_topo, command=self._aplicar_topo)
        m_ex.add_separator()
        m_ex.add_command(label="Expandir todas as categorias", command=lambda: self.expandir_todas(True))
        m_ex.add_command(label="Recolher todas as categorias", command=lambda: self.expandir_todas(False))
        barra.add_cascade(label="Exibir", menu=m_ex)

        m_aj = tk.Menu(barra, tearoff=False)
        m_aj.add_command(label="Como usar", command=self.ajuda)
        barra.add_cascade(label="Ajuda", menu=m_aj)

        # idioma: "auto" segue o mod (config.lua IDIOMA, padrao inglês)
        m_lang = tk.Menu(barra, tearoff=False)
        self.var_idioma = tk.StringVar(value=self.prefs.get("idioma", "auto"))
        m_lang.add_radiobutton(label="Auto (follow mod / segue o mod)", value="auto", variable=self.var_idioma,
                               command=self.trocar_idioma)
        for cod, nome in idioma.IDIOMAS.items():
            m_lang.add_radiobutton(label=nome, value=cod, variable=self.var_idioma, command=self.trocar_idioma)
        barra.add_cascade(label="Language / Idioma", menu=m_lang)
        self.config(menu=barra)
        self.bind("<Control-r>", lambda e: self.cmd_recarregar())
        self.bind("<F5>", lambda e: self.cmd_atualizar())

    def _layout(self):
        raiz = ttk.Frame(self, padding=8)
        raiz.pack(fill="both", expand=True)
        topo = ttk.Frame(raiz)
        topo.pack(fill="x")
        self.lbl_status = ttk.Label(topo, text="Aguardando o jogo…", style="Status.TLabel")
        self.lbl_status.pack(side="left", fill="x", expand=True)
        ttk.Button(topo, text="⟳ Recarregar mod", command=self.cmd_recarregar).pack(side="right")
        ttk.Button(topo, text="Atualizar busca", command=self.cmd_atualizar).pack(side="right", padx=4)

        abas = ttk.Notebook(raiz)
        abas.pack(fill="both", expand=True, pady=(8, 0))
        aba_busca = ttk.Frame(abas, padding=4)
        aba_ind = ttk.Frame(abas, padding=8)
        abas.add(aba_busca, text="Busca")
        abas.add(aba_ind, text="Revelação")
        self._layout_busca(aba_busca)
        self._layout_indicadores(aba_ind)

        rod = ttk.Frame(raiz)
        rod.pack(fill="x", pady=(6, 0))
        ttk.Label(rod, text="Opacidade da janela").pack(side="left")
        ttk.Scale(rod, from_=0.4, to=1.0, variable=self.var_opac,
                  command=lambda v: self.attributes("-alpha", float(v))).pack(side="left", padx=6)
        self.attributes("-alpha", self.var_opac.get())

    def _layout_busca(self, raiz):
        med = ttk.LabelFrame(raiz, text="Medidor de distância", padding=8)
        med.pack(fill="x", pady=(0, 4))
        linha = ttk.Frame(med)
        linha.pack(fill="x")
        ttk.Label(linha, text="Categoria:").pack(side="left")
        self.cb_cat = ttk.Combobox(linha, textvariable=self.var_cat, state="readonly", width=34)
        self.cb_cat.pack(side="left", padx=6, fill="x", expand=True)
        self.cb_cat.bind("<<ComboboxSelected>>", self.on_categoria)
        corpo = ttk.Frame(med)
        corpo.pack(fill="x", pady=(6, 0))
        self.canvas = tk.Canvas(corpo, width=110, height=110, highlightthickness=0, bg="#1e1f24")
        self.canvas.pack(side="left")
        info = ttk.Frame(corpo)
        info.pack(side="left", fill="both", expand=True, padx=10)
        self.lbl_dist = ttk.Label(info, text="—", style="Dist.TLabel")
        self.lbl_dist.pack(anchor="w")
        self.lbl_dir = ttk.Label(info, text="", style="Sub.TLabel")
        self.lbl_dir.pack(anchor="w")
        self.lbl_nome = ttk.Label(info, text="", style="Status.TLabel", wraplength=360)
        self.lbl_nome.pack(anchor="w", pady=(2, 4))
        self.barra = ttk.Progressbar(info, maximum=100)
        self.barra.pack(fill="x")
        ttk.Button(info, text="Teleportar para o mais próximo", command=self.cmd_tele_proximo).pack(anchor="w", pady=(6, 0))

        fil = ttk.LabelFrame(raiz, text="Filtro", padding=8)
        fil.pack(fill="x", pady=4)
        l1 = ttk.Frame(fil)
        l1.pack(fill="x")
        ttk.Label(l1, text="Texto:").pack(side="left")
        ttk.Entry(l1, textvariable=self.var_texto).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(l1, text="Limpar", command=lambda: self.var_texto.set("")).pack(side="left")
        l2 = ttk.Frame(fil)
        l2.pack(fill="x", pady=(6, 0))
        ttk.Label(l2, text="Distância máx. (m, 0 = sem limite):").pack(side="left")
        ttk.Spinbox(l2, from_=0, to=100000, increment=50, width=8, textvariable=self.var_max).pack(side="left", padx=6)
        self.mb_cats = ttk.Menubutton(l2, text="Categorias ▾")
        self.mb_cats.pack(side="right")
        self.menu_cats = tk.Menu(self.mb_cats, tearoff=False)
        self.mb_cats["menu"] = self.menu_cats
        l3 = ttk.Frame(fil)
        l3.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(l3, text="Esconder itens ocultos", variable=self.var_ocultos).pack(side="left")
        ttk.Checkbutton(l3, text="Esconder categorias vazias", variable=self.var_vazias).pack(side="left", padx=12)

        lst = ttk.LabelFrame(raiz, text="Colecionáveis por categoria", padding=8)
        lst.pack(fill="both", expand=True, pady=(4, 0))
        bts = ttk.Frame(lst)
        bts.pack(fill="x", pady=(0, 6))
        ttk.Button(bts, text="▸ Recolher/expandir categoria", command=self.alternar_categoria).pack(side="left")
        ttk.Button(bts, text="Expandir todas", command=lambda: self.expandir_todas(True)).pack(side="left", padx=4)
        ttk.Button(bts, text="Recolher todas", command=lambda: self.expandir_todas(False)).pack(side="left")
        frame_arv = ttk.Frame(lst)
        frame_arv.pack(fill="both", expand=True)
        self.arv = ttk.Treeview(frame_arv, columns=("dist", "dir", "alt"), selectmode="browse")
        for col, txt in (("#0", "Item"), ("dist", "Distância"), ("dir", "Direção"), ("alt", "Altura")):
            self.arv.heading(col, text=txt)
        self.arv.column("#0", width=230, stretch=True)
        self.arv.column("dist", width=80, anchor="e", stretch=False)
        self.arv.column("dir", width=110, stretch=False)
        self.arv.column("alt", width=110, stretch=False)
        sb = ttk.Scrollbar(frame_arv, orient="vertical", command=self.arv.yview)
        self.arv.configure(yscrollcommand=sb.set)
        self.arv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.arv.tag_configure("cat", font=("Segoe UI", 10, "bold"))
        self.arv.tag_configure("oculto", foreground="#888888")
        self.arv.bind("<<TreeviewOpen>>", lambda e: self._lembrar_aberta(True))
        self.arv.bind("<<TreeviewClose>>", lambda e: self._lembrar_aberta(False))
        self.arv.bind("<<TreeviewSelect>>", self.on_selecao)
        self.arv.bind("<Double-1>", self.on_duplo)
        ttk.Label(lst, text="Duplo clique em um item = teleportar até ele", style="Status.TLabel").pack(anchor="w", pady=(4, 0))

    def _layout_indicadores(self, raiz):
        def chk(pai, texto, var, cmd=None):
            ttk.Checkbutton(pai, text=texto, variable=var, command=cmd).pack(anchor="w", pady=1)

        ttk.Label(raiz, text="A revelação é independente da aba Busca: escolha aqui quais tipos de coletável são "
                             "revelados e por quais métodos.", style="Status.TLabel", wraplength=540).pack(anchor="w")
        sub_abas = ttk.Notebook(raiz)
        sub_abas.pack(fill="both", expand=True, pady=(6, 0))
        a_cat = ttk.Frame(sub_abas, padding=8)
        a_tela = ttk.Frame(sub_abas, padding=8)
        a_som = ttk.Frame(sub_abas, padding=8)
        a_jogo = ttk.Frame(sub_abas, padding=8)
        sub_abas.add(a_cat, text="Categorias")
        sub_abas.add(a_tela, text="Na tela")
        sub_abas.add(a_som, text="Som e voz")
        sub_abas.add(a_jogo, text="No jogo")

        # --- categorias reveladas: um liga/desliga por tipo de coletavel ---
        ttk.Label(a_cat, text="Tipos de coletável revelados (marcadores, seta, bússola, bipe, voz, contorno e vibração):",
                  wraplength=520).pack(anchor="w")
        self.frame_revelar = ttk.Frame(a_cat, padding=(4, 6))
        self.frame_revelar.pack(fill="x")
        ttk.Label(self.frame_revelar, text="(as categorias aparecem quando o mod ou a demo enviar o estado)",
                  style="Status.TLabel").grid(row=0, column=0, sticky="w")
        b = ttk.Frame(a_cat)
        b.pack(fill="x", pady=(4, 0))
        ttk.Button(b, text="Marcar todas", command=lambda: self._marcar_reveladas(True)).pack(side="left")
        ttk.Button(b, text="Desmarcar todas", command=lambda: self._marcar_reveladas(False)).pack(side="left", padx=4)
        ttk.Button(b, text="Só a do medidor", command=self._revelar_so_medidor).pack(side="left")
        filtro = ttk.LabelFrame(a_cat, text="Distância de exibição", padding=8)
        filtro.pack(fill="x", pady=(10, 0))
        l = ttk.Frame(filtro)
        l.pack(fill="x")
        ttk.Label(l, text="Padrão para todas as categorias:").pack(side="left")
        cb = ttk.Combobox(l, textvariable=self.var_dist_padrao, values=opcoes_dist_padrao(), width=11)
        cb.pack(side="left", padx=6)
        for ev in ("<<ComboboxSelected>>", "<Return>", "<FocusOut>"):
            cb.bind(ev, lambda e: self.sync_lua())
        rap = ttk.Frame(filtro)
        rap.pack(fill="x", pady=(4, 0))
        ttk.Label(rap, text="Rápido:").pack(side="left")
        for txt in ("50", "100", "150", "300", T("sem limite")):
            ttk.Button(rap, text=texto_limite(ler_dist(txt)), width=9,
                       command=lambda t=txt: (self.var_dist_padrao.set(t), self.sync_lua())).pack(side="left", padx=1)
        ttk.Button(rap, text="Todas = padrão", command=self._dist_todas_padrao).pack(side="left", padx=(8, 0))
        ttk.Label(filtro, text="Cada categoria pode ter a sua (coluna Distância acima). Só itens até essa distância "
                               "recebem marcador, seta, bússola, bipe, voz e contorno.",
                  style="Status.TLabel", wraplength=520).pack(anchor="w", pady=(4, 0))
        chk(filtro, "Não revelar itens ocultos", self.var_rev_ocultos)
        self.lbl_rev_resumo = ttk.Label(a_cat, text="", style="Status.TLabel", wraplength=520)
        self.lbl_rev_resumo.pack(anchor="w", pady=(8, 0))

        # --- na tela ---
        chk(a_tela, "Ativar camada sobre o jogo (Ctrl+Shift+O)", self.var_camada, self._aplicar_camada)
        sub = ttk.Frame(a_tela, padding=(18, 0, 0, 0))
        sub.pack(fill="x")
        chk(sub, "Marcadores nos itens (visíveis através das paredes)", self.var_marcadores)
        chk(sub, "   mostrar o nome do ator no marcador", self.var_nomes)
        chk(sub, "Seta na borda da tela apontando o mais próximo", self.var_seta)
        chk(sub, "Bússola no topo da tela", self.var_bussola)
        l = ttk.Frame(sub)
        l.pack(fill="x", pady=(4, 0))
        ttk.Label(l, text="Máx. de marcadores:").pack(side="left")
        ttk.Spinbox(l, from_=1, to=300, increment=5, width=6, textvariable=self.var_max_marc).pack(side="left", padx=6)
        ttk.Label(a_tela, text="Cada categoria tem sua cor (veja a subaba Categorias). Requer o jogo em modo janela ou "
                               "janela sem bordas. Se o add-on do ReShade estiver ativo, esta camada pausa sozinha.",
                  style="Status.TLabel", wraplength=520).pack(anchor="w", pady=(8, 0))
        self.lbl_reshade = ttk.Label(a_tela, text="", style="Status.TLabel")
        self.lbl_reshade.pack(anchor="w")

        # --- som e voz ---
        chk(a_som, "Bipe de proximidade — mais rápido e agudo quanto mais perto (Ctrl+Shift+B)", self.var_bip)
        l = ttk.Frame(a_som, padding=(18, 0, 0, 0))
        l.pack(fill="x")
        ttk.Label(l, text="Alcance (m):").pack(side="left")
        ttk.Spinbox(l, from_=5, to=2000, increment=10, width=6, textvariable=self.var_alcance).pack(side="left", padx=6)
        ttk.Label(l, text="Volume:").pack(side="left", padx=(12, 0))
        ttk.Scale(l, from_=0.05, to=1.0, variable=self.var_volume).pack(side="left", padx=6)
        chk(a_som, "Voz — anuncia tipo, distância e direção ao se aproximar (Ctrl+Shift+V)", self.var_voz)
        sub = ttk.Frame(a_som, padding=(18, 0, 0, 0))
        sub.pack(fill="x")
        chk(sub, "anunciar quando um item for coletado", self.var_voz_coleta)
        ttk.Button(sub, text="Testar voz", command=lambda: self.voz.falar(T("Teste de voz do RevelaZunidores"), forcar=True)).pack(anchor="w")
        ttk.Label(a_som, text="O bipe e a voz seguem o item revelado mais próximo, de qualquer categoria marcada.",
                  style="Status.TLabel", wraplength=520).pack(anchor="w", pady=(8, 0))

        # --- no jogo (mod Lua) ---
        chk(a_jogo, "Contorno no item (Custom Depth/Stencil) — experimental", self.var_contorno, self.sync_lua)
        l = ttk.Frame(a_jogo, padding=(18, 0, 0, 0))
        l.pack(fill="x")
        ttk.Label(l, text="Valor de stencil (1–255):").pack(side="left")
        ttk.Button(l, text="◀", width=3, command=lambda: self._passo_stencil(-1)).pack(side="left", padx=(6, 0))
        ttk.Spinbox(l, from_=1, to=255, width=5, textvariable=self.var_contorno_valor, command=self.sync_lua).pack(side="left", padx=2)
        ttk.Button(l, text="▶", width=3, command=lambda: self._passo_stencil(1)).pack(side="left")
        ttk.Label(a_jogo, text="Só aparece se o pós-processamento do jogo usar esse valor. Vá trocando até algum destacar o item.",
                  style="Status.TLabel", wraplength=500).pack(anchor="w", padx=18)
        chk(a_jogo, "Vibração do controle quando perto — experimental", self.var_vibracao, self.sync_lua)
        l = ttk.Frame(a_jogo, padding=(18, 0, 0, 0))
        l.pack(fill="x")
        ttk.Label(l, text="Distância (m):").pack(side="left")
        ttk.Spinbox(l, from_=1, to=200, width=5, textvariable=self.var_vibracao_dist, command=self.sync_lua).pack(side="left", padx=6)
        ttk.Button(a_jogo, text="Inspecionar item mais próximo (grava inspecao.txt)",
                   command=lambda: self.enviar("inspecionar")).pack(anchor="w", pady=(6, 0))
        self.lbl_lua = ttk.Label(a_jogo, text="", style="Status.TLabel", wraplength=520)
        self.lbl_lua.pack(anchor="w", pady=(4, 0))

        ttk.Label(raiz, text="Atalhos globais: Ctrl+Shift+O camada · B bipe · V voz · M mostrar/ocultar janela · "
                             "N próxima categoria do medidor", style="Status.TLabel", wraplength=540).pack(anchor="w", pady=(6, 0))

    # ---- categorias reveladas ---------------------------------------------
    def _montar_reveladas(self):
        """(Re)cria uma linha por categoria: cor, revelar sim/não e distância de exibição própria."""
        for w in self.frame_revelar.winfo_children():
            w.destroy()
        salvas = self.prefs.get("revelar", {})
        dists = self.prefs.get("dist_cat", {})
        self.menu_revelar.delete(0, "end")
        self.lbl_limite = {}
        ttk.Label(self.frame_revelar, text="Distância", style="Status.TLabel").grid(row=0, column=2, sticky="w")
        ttk.Label(self.frame_revelar, text="Limite em uso", style="Status.TLabel").grid(row=0, column=3, sticky="w", padx=(8, 0))
        for k, c in enumerate(self.estado["categorias"], 1):
            r = self._chave(c)
            if r not in self.cat_revelar:
                self.cat_revelar[r] = tk.BooleanVar(value=salvas.get(r, True))
            if r not in self.cat_dist:
                self.cat_dist[r] = tk.StringVar(value=dists.get(r, T("padrão")))
            tk.Label(self.frame_revelar, text="  ", bg=ind.cor_categoria(c["i"]), relief="solid", bd=1).grid(
                row=k, column=0, padx=(0, 4), pady=1, sticky="w")
            ttk.Checkbutton(self.frame_revelar, text=f"{c['nome']}  [{c['conteudo']}]", variable=self.cat_revelar[r],
                            command=self.sync_lua).grid(row=k, column=1, sticky="w", padx=(0, 8))
            cb = ttk.Combobox(self.frame_revelar, textvariable=self.cat_dist[r], values=opcoes_dist(), width=10)
            cb.grid(row=k, column=2, sticky="w")
            for ev in ("<<ComboboxSelected>>", "<Return>", "<FocusOut>"):
                cb.bind(ev, lambda e: self.sync_lua())
            self.lbl_limite[c["i"]] = ttk.Label(self.frame_revelar, text="", style="Status.TLabel")
            self.lbl_limite[c["i"]].grid(row=k, column=3, sticky="w", padx=(8, 0))
            self.menu_revelar.add_checkbutton(label=self._rotulo(c), variable=self.cat_revelar[r], command=self.sync_lua)
        self.menu_revelar.add_separator()
        self.menu_revelar.add_command(label="Marcar todas", command=lambda: self._marcar_reveladas(True))
        self.menu_revelar.add_command(label="Desmarcar todas", command=lambda: self._marcar_reveladas(False))
        idioma.aplicar(self.frame_revelar)
        idioma.aplicar(self.menu_revelar)

    def _dist_padrao(self):
        """Padrão escolhido na janela; se vazio, o do mod (config.lua)."""
        v = ler_dist(self.var_dist_padrao.get())
        if v is None:
            v = float(((self.estado or {}).get("indicadores") or {}).get("dist_padrao", 150))
        return v

    def _limite(self, c):
        """Distância de exibição (m) da categoria; 0 = sem limite."""
        v = self.cat_dist.get(self._chave(c))
        o = ler_dist(v.get()) if v else None
        if o is not None:
            return o
        if c.get("dist_cfg") is not None:
            return float(c["dist_cfg"])  # valor da categoria no config.lua (ex.: maçãs 40 m)
        return self._dist_padrao()

    def _dist_todas_padrao(self):
        for v in self.cat_dist.values():
            v.set(T("padrão"))
        self.sync_lua()

    def _marcar_reveladas(self, valor):
        for v in self.cat_revelar.values():
            v.set(valor)
        self.sync_lua()

    def _revelar_so_medidor(self):
        atual = self._cat_atual()
        for r, v in self.cat_revelar.items():
            v.set(atual is not None and r == self._chave(atual))
        self.sync_lua()

    def _revelada(self, c):
        v = self.cat_revelar.get(self._chave(c))
        return v is None or v.get()

    def _ids_revelados(self):
        if not self.estado:
            return []
        return [c["i"] for c in self.estado["categorias"] if self._revelada(c)]

    def _filtrar_revelacao(self, cat):
        mx = self._limite(cat)
        out = [it for it in cat["itens"]
               if not (self.var_rev_ocultos.get() and it.get("h")) and not (mx and it["d"] >= 0 and it["d"] > mx)]
        out.sort(key=lambda it: it["d"] if it["d"] >= 0 else 1e12)
        return out

    # ---- comandos para o mod ---------------------------------------------
    def enviar(self, cmd):
        if self.demo:
            self.lbl_status.config(text=T("[demo] comando: {}").format(cmd))
            return
        try:
            with open(ARQ_COMANDOS, "a", encoding="utf-8") as f:
                f.write(cmd + "\n")
        except OSError as e:
            messagebox.showerror("RevelaZunidores", T("Não consegui enviar o comando:\n{}").format(e))

    def cmd_recarregar(self):
        self.enviar("recarregar")

    def cmd_atualizar(self):
        self.enviar("atualizar")

    def cmd_tele_proximo(self):
        c = self._cat_atual()
        if c:
            itens = self._filtrar(c)
            if itens:
                self.enviar(f"teleportar {c['i']} {itens[0]['n']}")

    def _desejado_lua(self):
        return {"contorno": self.var_contorno.get(), "contorno_valor": int(self._num(self.var_contorno_valor, 252)),
                "vibracao": self.var_vibracao.get(), "vibracao_dist": float(self._num(self.var_vibracao_dist, 15)),
                "categorias": sorted(self._ids_revelados()),
                "distancias": {c["i"]: self._limite(c) for c in (self.estado or {}).get("categorias", [])}}

    def sync_lua(self, forcar=True):
        d = self._desejado_lua()
        self.enviar(f"indicador contorno_valor {max(1, min(255, d['contorno_valor']))}")
        self.enviar(f"indicador contorno {1 if d['contorno'] else 0}")
        self.enviar(f"indicador vibracao_dist {d['vibracao_dist']:.0f}")
        self.enviar(f"indicador vibracao {1 if d['vibracao'] else 0}")
        if self.estado:  # so depois de conhecer as categorias
            cats = ",".join(str(i) for i in d["categorias"]) or "nenhuma"
            self.enviar(f"indicador categorias {cats}")
            self.enviar(f"indicador distancia_padrao {self._dist_padrao():.0f}")
            for c in self.estado["categorias"]:
                self.enviar(f"indicador distancia {c['i']} {self._limite(c):.0f}")
        self._ultimo_sync = time.time()

    def _passo_stencil(self, passo):
        v = int(self._num(self.var_contorno_valor, 252)) + passo
        self.var_contorno_valor.set(str((v - 1) % 255 + 1))
        self.sync_lua()

    def on_categoria(self, _=None):
        c = self._cat_atual()
        if c:
            self.enviar(f"categoria {c['i']}")
        self.desenhar()

    def proxima_categoria(self):
        vals = list(self.cb_cat["values"])
        if vals:
            i = (vals.index(self.var_cat.get()) + 1) % len(vals) if self.var_cat.get() in vals else 0
            self.var_cat.set(vals[i])
            self.on_categoria()
            if self.var_voz.get():
                self.voz.falar(T("Categoria {}").format(self.var_cat.get().split('. ', 1)[-1]), forcar=True)

    def on_duplo(self, ev):
        iid = self.arv.identify_row(ev.y)
        if iid.startswith("it|"):
            _, i, nome = iid.split("|", 2)
            self.enviar(f"teleportar {i} {nome}")

    def on_selecao(self, _=None):
        sel = self.arv.selection()
        self.selecionado = sel[0] if sel else None

    # ---- atalhos globais ----------------------------------------------------
    def _ler_atalhos(self):
        try:
            while True:
                a = self.atalhos.fila.get_nowait()
                if a == "camada":
                    self.var_camada.set(not self.var_camada.get())
                    self._aplicar_camada()
                elif a == "bip":
                    self.var_bip.set(not self.var_bip.get())
                elif a == "voz":
                    self.var_voz.set(not self.var_voz.get())
                    self.voz.falar(T("Voz ligada") if self.var_voz.get() else T("Voz desligada"), forcar=True)
                elif a == "janela":
                    if self.state() == "withdrawn":
                        self.deiconify()
                    else:
                        self.withdraw()
                elif a == "categoria":
                    self.proxima_categoria()
        except Exception:
            pass
        self.after(100, self._ler_atalhos)

    # ---- expandir/recolher -----------------------------------------------
    def _lembrar_aberta(self, aberta):
        iid = self.arv.focus()
        if iid.startswith("cat|"):
            self.abertas[iid] = aberta

    def alternar_categoria(self):
        iid = self.arv.focus() or (self.arv.selection() or [""])[0]
        if iid.startswith("it|"):
            iid = self.arv.parent(iid)
        if not iid.startswith("cat|"):
            c = self._cat_atual()
            iid = f"cat|{c['i']}" if c else ""
        if iid and self.arv.exists(iid):
            novo = not self.arv.item(iid, "open")
            self.arv.item(iid, open=novo)
            self.abertas[iid] = novo

    def expandir_todas(self, abrir):
        for iid in self.arv.get_children(""):
            self.arv.item(iid, open=abrir)
            self.abertas[iid] = abrir

    # ---- dados -------------------------------------------------------------
    def _ler_estado(self):
        if self.demo:
            return self.demo.estado(self._desejado_lua()), 0
        try:
            idade = time.time() - os.path.getmtime(ARQ_ESTADO)
            with open(ARQ_ESTADO, encoding="utf-8") as f:
                return json.load(f), idade
        except (OSError, ValueError):
            return None, None

    def ler_camera(self):
        if self.demo:
            return self.demo.camera()
        try:
            mt = os.path.getmtime(ARQ_CAMERA)
            if time.time() - mt > 2:
                return None  # jogo parado/fechado
            if self._cam_cache[0] != mt:
                with open(ARQ_CAMERA, encoding="utf-8") as f:
                    self._cam_cache = (mt, json.load(f))
            return self._cam_cache[1]
        except (OSError, ValueError):
            return self._cam_cache[1]

    @staticmethod
    def _num(var, padrao=0.0):
        try:
            return max(0.0, float(str(var.get()).replace(",", ".")))
        except (ValueError, tk.TclError):
            return padrao

    def _filtrar(self, cat):
        txt = self.var_texto.get().strip().lower()
        mx = self._num(self.var_max)
        out = []
        for it in cat["itens"]:
            if self.var_ocultos.get() and it.get("h"):
                continue
            if mx and it["d"] >= 0 and it["d"] > mx:
                continue
            if txt and txt not in it["n"].lower() and txt not in it["c"].lower():
                continue
            out.append(it)
        out.sort(key=lambda it: it["d"] if it["d"] >= 0 else 1e12)
        return out

    def _cat_atual(self):
        if not self.estado:
            return None
        for c in self.estado["categorias"]:
            if self._rotulo(c) == self.var_cat.get():
                return c
        return None

    @staticmethod
    def _chave(c):
        """Chave estavel da categoria (o numero), igual em qualquer idioma."""
        return str(c["i"])

    @staticmethod
    def _rotulo(c):
        return f"{c['i']}. {c['nome']}"

    def _visivel(self, c):
        v = self.cat_visivel.get(self._chave(c))
        return v is None or v.get()

    # usados pelo overlay
    def reshade_ativo(self):
        try:
            return time.time() - os.path.getmtime(ARQ_RESHADE) < 3
        except OSError:
            return False

    def opcoes_overlay(self):
        return {"marcadores": self.var_marcadores.get(), "nomes": self.var_nomes.get(), "seta": self.var_seta.get(),
                "bussola": self.var_bussola.get(), "max_marcadores": int(self._num(self.var_max_marc, 40)) or 1}

    def itens_para_overlay(self):
        """Itens das categorias reveladas (independe da aba Busca). Todos podem ser alvo da seta."""
        if not self.estado:
            return []
        out = []
        for c in self.estado["categorias"]:
            if self._revelada(c):
                for it in self._filtrar_revelacao(c):
                    out.append((c["i"], c["nome"], it, True))
        return out

    def _alvo_revelado(self):
        """(categoria, item) revelado mais proximo, de qualquer categoria marcada."""
        melhor = None
        for c in (self.estado or {}).get("categorias", []):
            if self._revelada(c):
                itens = self._filtrar_revelacao(c)
                if itens and itens[0]["d"] >= 0 and (melhor is None or itens[0]["d"] < melhor[1]["d"]):
                    melhor = (c, itens[0])
        return melhor

    def _sincronizar_categorias(self):
        rotulos = [self._rotulo(c) for c in self.estado["categorias"]]
        if list(self.cb_cat["values"]) != rotulos:
            self.cb_cat["values"] = rotulos
            pref = next((self._rotulo(c) for c in self.estado["categorias"]
                         if str(c["i"]) == str(self.prefs.get("categoria"))), None)
            self.var_cat.set(pref if pref in rotulos else rotulos[0])
            self.menu_cats.delete(0, "end")
            vis = self.prefs.get("visiveis", {})
            for c in self.estado["categorias"]:
                r = self._chave(c)
                if r not in self.cat_visivel:
                    self.cat_visivel[r] = tk.BooleanVar(value=vis.get(r, True))
                self.menu_cats.add_checkbutton(label=self._rotulo(c), variable=self.cat_visivel[r])
            self.menu_cats.add_separator()
            self.menu_cats.add_command(label="Marcar todas", command=lambda: [v.set(True) for v in self.cat_visivel.values()])
            self.menu_cats.add_command(label="Desmarcar todas", command=lambda: [v.set(False) for v in self.cat_visivel.values()])
            idioma.aplicar(self.menu_cats)
            for k, v in self.prefs.get("abertas", {}).items():
                self.abertas.setdefault(k, v)
            self._montar_reveladas()
            self.on_categoria()
            self.sync_lua()

    # ---- ciclo -------------------------------------------------------------
    def atualizar(self):
        est, idade = self._ler_estado()
        if est is not None:
            self.estado = est
            self._sincronizar_categorias()
            if idade is not None and idade > SEM_SINAL_S:
                self.lbl_status.config(text=T("⚠ Sem sinal do jogo há {:.0f} s (jogo fechado ou mod parado)").format(idade))
            elif not est.get("jogador"):
                self.lbl_status.config(text=T("● Conectado — carregue um save para começar"))
            else:
                total = sum(c.get("total", len(c["itens"])) for c in est["categorias"])
                self.lbl_status.config(text=T("● Conectado — {} itens no mapa carregado").format(total))
            self._conferir_lua(est)
            self.lbl_reshade.config(text=T("● Add-on do ReShade ativo — camada desta janela pausada") if self.reshade_ativo() else "")
            self.desenhar()
            self._indicadores_som()
        elif not self.demo:
            self.lbl_status.config(text=T("Aguardando o jogo… (estado.json ainda não existe)"))
            self.bip.distancia = None
        self.after(ATUALIZAR_MS, self.atualizar)

    def _conferir_lua(self, est):
        real = est.get("indicadores")
        if not real:
            self.lbl_lua.config(text=T("Mod sem suporte a indicadores (versão antiga?) — recarregue o mod."))
            return
        d = self._desejado_lua()
        ok = (real.get("contorno") == d["contorno"] and real.get("vibracao") == d["vibracao"]
              and int(real.get("contorno_valor", -1)) == max(1, min(255, d["contorno_valor"]))
              and abs(float(real.get("vibracao_dist", -1)) - d["vibracao_dist"]) < 0.6
              and ("categorias" not in real or sorted(real["categorias"]) == d["categorias"])
              and all(abs(float(c.get("dist", d["distancias"].get(c["i"], 0))) - d["distancias"].get(c["i"], 0)) < 0.6
                      for c in est["categorias"]))
        for c in est["categorias"]:
            if c["i"] in self.lbl_limite:
                self.lbl_limite[c["i"]].config(text=texto_limite(self._limite(c)))
        if not ok and time.time() - self._ultimo_sync > 2:
            self.sync_lua()  # o mod foi reiniciado ou ainda nao recebeu: reenvia
        self.lbl_lua.config(text=(T("No jogo: contorno {} (stencil {}), vibração {} ({:.0f} m), categorias {}").format(
            T("ligado") if real.get("contorno") else T("desligado"), real.get("contorno_valor"),
            T("ligada") if real.get("vibracao") else T("desligada"), float(real.get("vibracao_dist", 0)),
            ",".join(str(i) for i in real.get("categorias", [])) or T("nenhuma"))))

    def _indicadores_som(self):
        """Bipe e voz seguem o item revelado mais proximo (categorias da revelacao, nao a do medidor)."""
        par = self._alvo_revelado()
        alvo = par[1] if par else None
        self.bip.ativo = self.var_bip.get()
        self.bip.alcance = self._num(self.var_alcance, 100) or 100
        self.bip.volume = self.var_volume.get()
        self.bip.distancia = alvo["d"] if alvo else None
        reveladas = [c for c in self.estado["categorias"] if self._revelada(c)]
        total = sum(c.get("total", len(c["itens"])) for c in reveladas)
        n_rev = len(reveladas)
        self.lbl_rev_resumo.config(text=(
            T("{} de {} categorias reveladas · {} itens no mapa carregado").format(n_rev, len(self.estado['categorias']), total)
            + (T(" · mais próximo: {} a {}").format(par[0]['nome'], dist_texto(alvo['d'])) if par else "")))
        ve = self._voz_estado
        if not self.var_voz.get():
            ve.update(alvo=None, limiar=None, contagem=total)
            return
        if ve["contagem"] is not None and total < ve["contagem"] and self.var_voz_coleta.get():
            self.voz.falar(T("Coletado. Restam {} itens revelados no mapa.").format(total), forcar=True)
        ve["contagem"] = total
        if not alvo:
            ve.update(alvo=None, limiar=None)
            return
        nome_cat = par[0]["nome"].split(" (")[0]
        limiar = next((l for l in reversed(LIMIARES_VOZ) if alvo["d"] <= l), None)
        texto = T("{:.0f} metros, {}").format(alvo['d'], direcao_texto(alvo['ang']))
        if alvo["n"] != ve["alvo"]:
            self.voz.falar(f"{nome_cat}: {texto}")
            ve.update(alvo=alvo["n"], limiar=limiar)
        elif limiar is not None and (ve["limiar"] is None or limiar < ve["limiar"]):
            self.voz.falar(f"{nome_cat}, {texto}")
            ve["limiar"] = limiar

    def desenhar(self):
        if self.estado:
            self._desenhar_medidor()
            self._desenhar_lista()

    def _desenhar_medidor(self):
        c = self._cat_atual()
        cv = self.canvas
        cv.delete("all")
        cx, cy, r = 55, 55, 44
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#555b66", width=2)
        cv.create_text(cx, cy - r, text="▲", fill="#555b66", font=("Segoe UI", 7))
        itens = self._filtrar(c) if c else []
        if not itens:
            self.lbl_dist.config(text="—")
            self.lbl_dir.config(text=T("Nenhum item desta categoria no mapa carregado") if c else "")
            self.lbl_nome.config(text=T("Referência: {}").format(c['referencia']) if c else "")
            self.barra["value"] = 0
            cv.create_text(cx, cy, text="?", fill="#888", font=("Segoe UI", 18, "bold"))
            return
        it = itens[0]
        d, ang = it["d"], it["ang"]
        cor = "#4cd964" if d <= 25 else ("#ffcc00" if d <= 100 else "#ff6b5b")
        rad = math.radians(ang)
        if d <= 10:
            cv.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, fill=cor, outline="")
        else:
            cv.create_line(cx, cy, cx + r * 0.85 * math.sin(rad), cy - r * 0.85 * math.cos(rad),
                           fill=cor, width=5, arrow="last", arrowshape=(14, 16, 6))
        cv.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#e8e8e8", outline="")
        self.lbl_dist.config(text=dist_texto(d))
        self.lbl_dir.config(text=f"{direcao_texto(ang)} · {altura_texto(it['dz'])}{T('  · OCULTO') if it.get('h') else ''}")
        self.lbl_nome.config(text=T("{}  ({} na categoria · ref.: {})").format(it['n'], len(itens), c['referencia']))
        self.barra["value"] = max(0.0, 100.0 * (1 - min(d, ESCALA_MEDIDOR_M) / ESCALA_MEDIDOR_M))

    def _desenhar_lista(self):
        arv = self.arv
        sel = self.selecionado
        rolagem = arv.yview()[0]
        existentes = set(arv.get_children(""))
        manter = set()
        for pos, c in enumerate(self.estado["categorias"]):
            if not self._visivel(c):
                continue
            itens = self._filtrar(c)
            if self.var_vazias.get() and not itens:
                continue
            iid = f"cat|{c['i']}"
            manter.add(iid)
            mais = T(" — mais perto: {}").format(dist_texto(itens[0]['d'])) if itens else ""
            total = c.get("total", len(c["itens"]))
            extra = T(", {} mais próximos listados").format(len(c['itens'])) if total > len(c["itens"]) else ""
            texto = f"{c['nome']}  ({len(itens)}/{total}{extra}){mais}"
            if arv.exists(iid):
                arv.item(iid, text=texto)
                arv.move(iid, "", pos)
            else:
                arv.insert("", pos, iid=iid, text=texto, open=self.abertas.get(iid, True), tags=("cat",))
            arv.item(iid, values=("", c["conteudo"], c["referencia"][:24]))
            novos = [f"it|{c['i']}|{it['n']}" for it in itens]
            if list(arv.get_children(iid)) != novos:
                arv.delete(*arv.get_children(iid))
                for it, fid in zip(itens, novos):
                    arv.insert(iid, "end", iid=fid, text=it["n"], tags=("oculto",) if it.get("h") else ())
            for it, fid in zip(itens, novos):
                arv.item(fid, values=(dist_texto(it["d"]), direcao_texto(it["ang"]), altura_texto(it["dz"])))
        for iid in existentes - manter:
            arv.delete(iid)
        if sel and arv.exists(sel):
            arv.selection_set(sel)
        arv.yview_moveto(rolagem)

    def _aplicar_topo(self):
        self.attributes("-topmost", self.var_topo.get())

    def _aplicar_camada(self):
        if self.var_camada.get():
            self.overlay.ligar()
        else:
            self.overlay.desligar()

    def trocar_idioma(self):
        escolha = self.var_idioma.get()
        self.prefs["idioma"] = escolha
        if escolha != "auto":
            self.enviar(f"idioma {escolha}")  # o mod (e o ReShade em "seguir o mod") trocam junto
        self._gravar_prefs()
        if self.demo:
            return
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv, cwd=PASTA_MENU)
        self.fechar()

    def ajuda(self):
        if idioma.LANG == "en":
            messagebox.showinfo("How to use", (
                "1. Open the game (with UE4SS) in windowed or borderless mode and load a save.\n"
                "2. Keep this window open; it updates by itself.\n\n"
                "SEARCH TAB\n"
                "Meter: the arrow points to the nearest item of the category relative to\n"
                "where you are looking (up = ahead). Filter: text, max distance, categories\n"
                "and hidden items. List: arrow or buttons to collapse/expand; double-click teleports.\n\n"
                "REVEAL TAB (independent of Search)\n"
                "• Categories: toggle each collectible type (chirpers, talking dead, chests,\n"
                "  apples, coins, figurines...), each with its color and display distance.\n"
                "• On screen: markers through walls, screen-edge arrow and compass.\n"
                "• Sound & voice: beep and voice follow the nearest revealed item.\n"
                "• In game (experimental): stencil outline and controller vibration.\n\n"
                "Global hotkeys: Ctrl+Shift+O overlay, B beep, V voice, M window, N category.\n"
                "In-game keys: F5 category, F6 classes, F7 list, F8 teleport, F9 inspect,\n"
                "Ctrl+R reloads all mods.\n\n"
                "Language: menu Language / Idioma."))
            return
        messagebox.showinfo("Como usar", (
            "1. Abra o jogo (com o UE4SS) em modo janela ou janela sem bordas e carregue um save.\n"
            "2. Mantenha esta janela aberta; ela atualiza sozinha.\n\n"
            "ABA BUSCA\n"
            "Medidor: a seta aponta para o item mais próximo da categoria em relação a\n"
            "para onde você olha (para cima = à frente). Filtro: texto, distância máxima,\n"
            "categorias e itens ocultos. Lista: setinha ou botões para recolher/expandir;\n"
            "duplo clique teleporta.\n\n"
            "ABA REVELAÇÃO (independente da aba Busca)\n"
            "• Categorias: liga/desliga cada tipo de coletável (zunidores, corpos, baús,\n"
            "  maçãs, moedas, estatuetas...), cada um com sua cor; filtro próprio.\n"
            "• Na tela: marcadores através das paredes, seta na borda e bússola.\n"
            "• Som e voz: bipe e voz seguem o item revelado mais próximo.\n"
            "• No jogo (experimental): contorno via stencil e vibração do controle.\n\n"
            "Atalhos globais: Ctrl+Shift+O camada, B bipe, V voz, M janela, N categoria.\n"
            "Teclas no jogo: F5 categoria, F6 classes, F7 lista, F8 teleporte, F9 inspecionar,\n"
            "Ctrl+R recarrega todos os mods."))


def main():
    app = Menu("--demo" in sys.argv)
    if "--autoteste" in sys.argv:
        seg = float(sys.argv[sys.argv.index("--autoteste") + 1])
        app.var_volume.set(0.03)  # autoteste quase mudo
        acoes = [lambda: app.var_texto.set("_1"), lambda: app.var_texto.set(""),
                 lambda: app.var_max.set("200"), lambda: app.var_max.set("0"),
                 lambda: app.expandir_todas(False), lambda: app.expandir_todas(True),
                 app.alternar_categoria, lambda: app.var_ocultos.set(True), lambda: app.var_vazias.set(True),
                 lambda: app._revelar_so_medidor(), lambda: app._marcar_reveladas(True), lambda: app.var_nomes.set(True),
                 lambda: app.var_bip.set(True), lambda: app.var_alcance.set("2000"),
                 lambda: (app.var_dist_padrao.set("50"), app.sync_lua()),
                 lambda: (app.var_dist_padrao.set("sem limite"), app.sync_lua()),
                 lambda: (app.var_contorno.set(True), app.sync_lua()), lambda: app._passo_stencil(1),
                 app.proxima_categoria, app.cmd_tele_proximo, app.cmd_recarregar,
                 lambda: (app.var_camada.set(False), app._aplicar_camada()),
                 lambda: (app.var_camada.set(True), app._aplicar_camada())]
        for k, a in enumerate(acoes):
            app.after(int(300 + k * seg * 1000 / (len(acoes) + 1)), a)

        def fim():
            n = len(app.overlay.cv.find_all()) if app.overlay.win else -1
            print("AUTOTESTE", "OK" if not app.erros else f"ERROS={app.erros}",
                  "|", app.lbl_status.cget("text"), "| medidor:", app.lbl_dist.cget("text"),
                  "| linhas:", sum(1 + len(app.arv.get_children(i)) for i in app.arv.get_children("")),
                  "| elementos na camada:", n, "| bip:", app.bip.ativo, round(app.bip.distancia or -1, 1),
                  "| lua:", app.lbl_lua.cget("text"))
            app.fechar()
        app.after(int(seg * 1000), fim)
    app.mainloop()


if __name__ == "__main__":
    main()
