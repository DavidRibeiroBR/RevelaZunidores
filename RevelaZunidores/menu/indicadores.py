"""Indicadores do RevelaZunidores que rodam fora do jogo.

- Overlay: janela transparente, sem bordas e que deixa o clique passar, posicionada
  sobre a area do jogo. Desenha marcadores (visiveis atraves das paredes), seta na
  borda da tela e bussola. A projecao 3D->tela usa camera.json gravado pelo mod.
- Bip: "contador Geiger" - bipes mais rapidos e agudos conforme o item se aproxima.
- Voz: anuncios falados (Windows SAPI via PowerShell, voz em portugues se instalada).
- Atalhos globais (funcionam com o jogo em foco): RegisterHotKey do Windows.
"""
import ctypes
import io
import json
import math
import os
import queue
import struct
import subprocess
import threading
import time
import tkinter as tk
import wave
import winsound
from ctypes import wintypes

user32 = ctypes.windll.user32
CHAVE = "#010203"  # cor tratada como transparente no overlay
CORES = ["#ffd23f", "#4cc9f0", "#f72585", "#80ed99", "#ff9f1c", "#b388ff",
         "#ff595e", "#2ec4b6", "#f4a261", "#e9ff70", "#90e0ef", "#ffafcc"]


def cor_categoria(i):
    return CORES[(int(i) - 1) % len(CORES)]


def normalizar(a):
    return (a + 540.0) % 360.0 - 180.0


# ---------------------------------------------------------------------------
# janela do jogo
# ---------------------------------------------------------------------------
def janela_jogo():
    """(x, y, largura, altura, hwnd) da area cliente do jogo, ou None."""
    hwnd = user32.FindWindowW("UnrealWindow", None)
    if not hwnd or user32.IsIconic(hwnd):
        return None
    r = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    p = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(p))
    if r.right <= 0 or r.bottom <= 0:
        return None
    return p.x, p.y, r.right, r.bottom, hwnd


def hwnd_raiz(widget):
    return user32.GetAncestor(widget.winfo_id(), 2)  # GA_ROOT


# ---------------------------------------------------------------------------
# projecao (convencoes da Unreal: X frente, Y direita, Z cima, FOV horizontal)
# ---------------------------------------------------------------------------
class Camera:
    def __init__(self, d):
        self.x, self.y, self.z = d["x"], d["y"], d["z"]
        self.yaw = d["yaw"]
        p, y, r = (math.radians(d[k]) for k in ("pitch", "yaw", "roll"))
        sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
        self.fx = (cp * cy, cp * sy, sp)
        self.rx = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
        self.ux = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
        self.tan = math.tan(math.radians(max(10.0, min(170.0, d.get("fov", 90.0)))) / 2)

    def local(self, x, y, z):
        dx, dy, dz = x - self.x, y - self.y, z - self.z
        f = dx * self.fx[0] + dy * self.fx[1] + dz * self.fx[2]
        r = dx * self.rx[0] + dy * self.rx[1] + dz * self.rx[2]
        u = dx * self.ux[0] + dy * self.ux[1] + dz * self.ux[2]
        return f, r, u

    def projetar(self, x, y, z, w, h):
        """(sx, sy, na_frente) em pixels da area do jogo."""
        f, r, u = self.local(x, y, z)
        if f <= 1:
            return None, None, False
        k = (w / 2) / self.tan
        return w / 2 + r / f * k, h / 2 - u / f * k, True

    def distancia(self, x, y, z):
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2 + (z - self.z) ** 2) / 100

    def rumo(self, x, y):
        return normalizar(math.degrees(math.atan2(y - self.y, x - self.x)) - self.yaw)


class Overlay:
    """Camada transparente sobre o jogo."""

    def __init__(self, app, ler_camera, regiao_fixa=None):
        self.app = app
        self.ler_camera = ler_camera
        self.regiao_fixa = regiao_fixa  # usado no modo demo
        self.win = None
        self.geo = None
        self.visivel = False

    def ligar(self):
        if self.win:
            return
        w = tk.Toplevel(self.app)
        w.overrideredirect(True)
        w.config(bg=CHAVE)
        w.attributes("-topmost", True)
        w.attributes("-transparentcolor", CHAVE)
        self.cv = tk.Canvas(w, bg=CHAVE, highlightthickness=0, bd=0)
        self.cv.pack(fill="both", expand=True)
        w.withdraw()
        self.win = w
        self.visivel = False
        self.geo = None
        self._passar_clique()
        self._ciclo()

    def desligar(self):
        if self.win:
            self.win.destroy()
        self.win = None

    def _passar_clique(self):
        self.win.update_idletasks()
        hwnd = hwnd_raiz(self.win)
        GWL_EXSTYLE = -20
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        # LAYERED | TRANSPARENT (clique passa) | TOOLWINDOW (fora da barra de tarefas) | NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | 0x80000 | 0x20 | 0x80 | 0x08000000)

    def _regiao(self):
        if self.regiao_fixa:
            return self.regiao_fixa
        if self.app.reshade_ativo():
            return None  # o add-on do ReShade ja desenha dentro do jogo
        j = janela_jogo()
        if not j:
            return None
        x, y, w, h, hwnd = j
        fg = user32.GetForegroundWindow()
        if fg != hwnd and fg != hwnd_raiz(self.app):
            return None  # jogo fora de foco: esconde a camada
        return x, y, w, h

    def _ciclo(self):
        if not self.win:
            return
        try:
            self._desenhar()
        except Exception as e:  # nunca derrubar a janela principal
            self.app.registrar_erro(f"overlay: {e}")
        self.win.after(33, self._ciclo)

    def _desenhar(self):
        reg = self._regiao()
        cam_d = self.ler_camera()
        if not reg or not cam_d:
            if self.visivel:
                self.win.withdraw()
                self.visivel = False
            return
        x, y, w, h = reg
        if self.geo != reg:
            self.win.geometry(f"{w}x{h}+{x}+{y}")
            self.geo = reg
        if not self.visivel:
            self.win.deiconify()
            self.win.attributes("-topmost", True)
            self.visivel = True
        cam = Camera(cam_d)
        cv = self.cv
        cv.delete("all")
        op = self.app.opcoes_overlay()
        itens = self.app.itens_para_overlay()  # [(cat_i, cat_nome, item, eh_alvo)]
        alvo = None
        desenhados = []
        for cat_i, cat_nome, it, eh_alvo in itens:
            d = cam.distancia(it["x"], it["y"], it["z"])
            if eh_alvo and (alvo is None or d < alvo[1]):
                alvo = (it, d, cat_i)
            desenhados.append((d, cat_i, it))
        desenhados.sort(key=lambda t: t[0])
        if op["marcadores"]:
            for d, cat_i, it in desenhados[: op["max_marcadores"]]:
                sx, sy, frente = cam.projetar(it["x"], it["y"], it["z"], w, h)
                if not frente or sx < -20 or sx > w + 20 or sy < -20 or sy > h + 20:
                    continue
                cor = cor_categoria(cat_i)
                t = max(5, min(13, 13 - d / 25))
                cv.create_polygon(sx, sy - t, sx + t, sy, sx, sy + t, sx - t, sy, outline="#000000", fill=cor, width=2)
                rot = f"{d:.0f} m"
                if op["nomes"]:
                    rot = f"{it['n']}  {rot}"
                cv.create_text(sx + 1, sy - t - 9, text=rot, fill="#000000", font=("Segoe UI", 9, "bold"))
                cv.create_text(sx, sy - t - 10, text=rot, fill=cor, font=("Segoe UI", 9, "bold"))
        if op["seta"] and alvo:
            self._seta(cam, alvo, w, h)
        if op["bussola"]:
            self._bussola(cam, desenhados, alvo, w, h)

    def _seta(self, cam, alvo, w, h):
        it, d, cat_i = alvo
        sx, sy, frente = cam.projetar(it["x"], it["y"], it["z"], w, h)
        margem = 60
        if frente and margem < sx < w - margem and margem < sy < h - margem:
            return  # item na tela: o marcador ja mostra
        f, r, u = cam.local(it["x"], it["y"], it["z"])
        vx, vy = r, -u
        if f <= 1 and abs(vx) < 1e-3:
            vx = 1.0
        n = math.hypot(vx, vy) or 1.0
        vx, vy = vx / n, vy / n
        cx, cy = w / 2, h / 2
        rx, ry = w / 2 - margem, h / 2 - margem
        k = 1 / math.sqrt((vx / rx) ** 2 + (vy / ry) ** 2)
        px, py = cx + vx * k, cy + vy * k
        ang = math.atan2(vy, vx)
        cor = cor_categoria(cat_i)
        pts = []
        for da, raio in ((0, 26), (2.5, 14), (math.pi, 6), (-2.5, 14)):
            pts += [px + raio * math.cos(ang + da), py + raio * math.sin(ang + da)]
        self.cv.create_polygon(*pts, fill=cor, outline="#000000", width=2)
        txt = f"{d:.0f} m"
        tx, ty = px - vx * 34, py - vy * 34
        self.cv.create_text(tx + 1, ty + 1, text=txt, fill="#000000", font=("Segoe UI", 11, "bold"))
        self.cv.create_text(tx, ty, text=txt, fill=cor, font=("Segoe UI", 11, "bold"))

    def _bussola(self, cam, desenhados, alvo, w, h):
        cv = self.cv
        larg = min(700, w * 0.45)
        x0, x1, yb = w / 2 - larg / 2, w / 2 + larg / 2, 34
        cv.create_line(x0, yb, x1, yb, fill="#c8c8c8", width=2)
        for a in range(-90, 91, 15):
            xx = w / 2 + a / 90 * larg / 2
            cv.create_line(xx, yb - (6 if a % 45 == 0 else 3), xx, yb, fill="#c8c8c8", width=1)
        cv.create_text(w / 2, yb - 14, text="▼", fill="#ffffff", font=("Segoe UI", 9))
        for d, cat_i, it in desenhados[:60]:
            a = cam.rumo(it["x"], it["y"])
            if abs(a) > 90:
                continue
            xx = w / 2 + a / 90 * larg / 2
            eh_alvo = alvo is not None and it is alvo[0]
            r = 6 if eh_alvo else 3
            cv.create_oval(xx - r, yb + 4, xx + r, yb + 4 + 2 * r, fill=cor_categoria(cat_i), outline="#000000")
            if eh_alvo:
                cv.create_text(xx, yb + 24, text=f"{d:.0f} m", fill=cor_categoria(cat_i), font=("Segoe UI", 9, "bold"))
        if alvo:
            a = cam.rumo(alvo[0]["x"], alvo[0]["y"])
            if abs(a) > 90:
                lado = x1 + 14 if a > 0 else x0 - 14
                cv.create_text(lado, yb, text="▶" if a > 0 else "◀", fill=cor_categoria(alvo[2]), font=("Segoe UI", 14, "bold"))


# ---------------------------------------------------------------------------
# som
# ---------------------------------------------------------------------------
def gerar_bip(freq, volume, ms=60, taxa=22050):
    n = int(taxa * ms / 1000)
    amp = int(32767 * max(0.0, min(1.0, volume)))
    quadros = bytearray()
    for i in range(n):
        env = min(1.0, i / (n * 0.1), (n - i) / (n * 0.3))
        quadros += struct.pack("<h", int(amp * env * math.sin(2 * math.pi * freq * i / taxa)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wv:
        wv.setnchannels(1)
        wv.setsampwidth(2)
        wv.setframerate(taxa)
        wv.writeframes(bytes(quadros))
    return buf.getvalue()


class Bip(threading.Thread):
    """Bipes mais rapidos e agudos conforme a distancia diminui."""

    def __init__(self):
        super().__init__(daemon=True)
        self.ativo = False
        self.distancia = None
        self.alcance = 100.0
        self.volume = 0.5
        self._cache = {}
        self.start()

    def _som(self, freq):
        chave = (int(freq / 20) * 20, round(self.volume, 2))
        if chave not in self._cache:
            self._cache[chave] = gerar_bip(chave[0], chave[1])
        return self._cache[chave]

    def run(self):
        while True:
            d = self.distancia
            if not self.ativo or d is None or d < 0 or d > self.alcance:
                time.sleep(0.15)
                continue
            frac = d / self.alcance
            try:
                winsound.PlaySound(self._som(1500 - 900 * frac), winsound.SND_MEMORY)
            except RuntimeError:
                pass
            time.sleep(0.05 + 1.25 * frac)


class Voz:
    """Fala textos com a voz do Windows (prefere voz em portugues)."""

    SCRIPT = (
        "[Console]::InputEncoding=[System.Text.Encoding]::UTF8;"
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$v=$s.GetInstalledVoices()|Where-Object{$_.VoiceInfo.Culture.Name -like '%CULTURA%*'}|Select-Object -First 1;"
        "if($v){$s.SelectVoice($v.VoiceInfo.Name)};$s.Rate=1;"
        "while(($l=[Console]::In.ReadLine()) -ne $null){$s.SpeakAsyncCancelAll();if($l -ne '::parar'){$s.SpeakAsync($l)|Out-Null}}"
    )

    def __init__(self, lang="en"):
        self.proc = None
        self.ultima = 0.0
        self.cultura = "pt" if lang == "pt-BR" else "en"  # escolhe uma voz instalada desse idioma

    def _garantir(self):
        if self.proc and self.proc.poll() is None:
            return True
        try:
            self.proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", self.SCRIPT.replace("%CULTURA%", self.cultura)],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=0x08000000)  # CREATE_NO_WINDOW
            return True
        except OSError:
            self.proc = None
            return False

    def falar(self, texto, intervalo_min=2.5, forcar=False):
        agora = time.time()
        if not forcar and agora - self.ultima < intervalo_min:
            return
        if not self._garantir():
            return
        try:
            self.proc.stdin.write((texto.replace("\n", " ") + "\n").encode("utf-8"))
            self.proc.stdin.flush()
            self.ultima = agora
        except OSError:
            self.proc = None

    def encerrar(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.close()
                self.proc.terminate()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# atalhos globais
# ---------------------------------------------------------------------------
MOD_CTRL_SHIFT = 0x0002 | 0x0004 | 0x4000  # CONTROL | SHIFT | NOREPEAT
ATALHOS = {1: ("O", "camada"), 2: ("B", "bip"), 3: ("V", "voz"), 4: ("M", "janela"), 5: ("N", "categoria")}


class Atalhos(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.fila = queue.Queue()
        self.falhas = []
        self.start()

    def run(self):
        for i, (tecla, _) in ATALHOS.items():
            if not user32.RegisterHotKey(None, i, MOD_CTRL_SHIFT, ord(tecla)):
                self.falhas.append(tecla)
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312 and msg.wParam in ATALHOS:  # WM_HOTKEY
                self.fila.put(ATALHOS[msg.wParam][1])
