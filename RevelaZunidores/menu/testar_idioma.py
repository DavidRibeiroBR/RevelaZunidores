"""Confere se a janela em inglês ficou sem textos em português (modo demo).

Uso: python testar_idioma.py
"""
import importlib.machinery
import importlib.util
import os
import re
import sys
import tkinter as tk

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["x", "--demo", "--en"]
loader = importlib.machinery.SourceFileLoader("menu", os.path.join(AQUI, "menu_revela.pyw"))
spec = importlib.util.spec_from_loader("menu", loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)

# palavras/sinais tipicos do portugues que nao existem nos textos em ingles
PT = re.compile(r"[ãõçáéíóúâêô]|\b(de|do|da|dos|das|não|para|com|categoria|itens|mais|todas|jogo|janela|"
                r"distância|padrão|limite|voz|bipe|camada|seta|bússola|marcador|ocultos?|recolher|expandir|"
                r"busca|filtro|texto|limpar|sair|ajuda|exibir|alcance|teste|contorno|vibração)\b", re.I)

app = m.Menu(True)
for _ in range(3):
    app.atualizar()
    app.update()


def textos(w):
    out = []
    try:
        t = w.cget("text")
        if isinstance(t, str) and t:
            out.append(("widget", t))
    except (tk.TclError, AttributeError):
        pass
    cls = w.winfo_class()
    if cls == "TNotebook":
        out += [("aba", w.tab(a, "text")) for a in w.tabs()]
    elif cls == "Treeview":
        out += [("coluna", w.heading(c, "text")) for c in ("#0",) + tuple(w["columns"])]
        for cat in w.get_children(""):
            out.append(("lista", w.item(cat, "text")))
            out += [("lista", " ".join(map(str, w.item(f, "values")))) for f in w.get_children(cat)]
    elif cls == "Menu":
        fim = w.index("end")
        for i in range(0 if fim is None else fim + 1):
            try:
                out.append(("menu", w.entrycget(i, "label")))
            except tk.TclError:
                pass
    elif cls == "TCombobox":
        out += [("opcao", v) for v in w["values"]]
    for f in w.winfo_children():
        out += textos(f)
    return out


achados = sorted({(tipo, t) for tipo, t in textos(app) if PT.search(t) and "RevelaZunidores" not in t and "estado.json" not in t
                 and t != "Português (Brasil)"})  # nome da opcao de idioma fica no proprio idioma
# textos dinamicos e ajuda
extras = [m.direcao_texto(a) for a in (0, 45, -45, 90, -90, 135, 180)] + [m.altura_texto(d) for d in (10, -10, 0)]
extras += [m.texto_limite(0), m.texto_limite(50)]
achados += [("dinamico", t) for t in extras if PT.search(t)]
print(f"{len(textos(app))} textos verificados em inglês")
for tipo, t in achados:
    print(f"  EM PORTUGUÊS? [{tipo}] {t[:110]!r}")
print("COBERTURA OK" if not achados else f"{len(achados)} texto(s) sem tradução")
app.fechar()
sys.exit(1 if achados else 0)
