"""smp_gui.py : éditeur graphique de banques de samples .SMP pour SEQ-16.

Rôle
----
Une fenêtre (tkinter, bibliothèque standard uniquement) pour fabriquer une
banque .SMP à partir de fichiers WAV, sans ligne de commande :
  - liste des samples de la banque (16 au plus) : ajouter des WAV, retirer,
    monter / descendre, ouvrir une banque .SMP existante ;
  - réglages de chaque sample (nom, fréquence, bits, décimation, courbe,
    drive, trim, clean, tramage, découpage en tranches) ;
  - forme d'onde : le WAV d'origine et le rendu simulé du CPC ;
  - écoute du son d'origine et du rendu CPC ;
  - jauge de mémoire (16 320 octets au plus) ;
  - sauvegarde du .SMP et ajout à une disquette .dsk.

Toute la conversion est faite par smp_model.py (sans interface), qui
s'appuie sur wav2smp.py et amsdsk.py.

Habillage repris de CPC DISK : palette du firmware CPC (bleu, jaune, cyan)
ou moniteur vert GT65 (F3), polices pixel « Press Start 2P » et « VT323 »
(licence OFL) du dossier tools/fonts/.

Raccourcis : Ctrl+O ouvrir un .SMP, Ctrl+W ajouter des WAV, Ctrl+S sauver,
Suppr retirer le sample, F3 moniteur couleur / vert, F1 aide.

Lancement :
    python tools/smp_gui.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import font as tkfont
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wav2smp                                   # noqa: E402
from smp_model import (BankError, BankModel, RATE_PRESETS,  # noqa: E402
                       dsk_name)

# Racine du dépôt (dossiers samples/ et build/ proposés par défaut). Sous
# PyInstaller, le dossier courant fait office de racine.
ROOT = (os.getcwd() if getattr(sys, "frozen", False)
        else os.path.normpath(os.path.join(HERE, "..")))
# Polices : à côté de ce fichier, ou dans le paquet PyInstaller (_MEIPASS).
FONT_DIR = os.path.join(getattr(sys, "_MEIPASS", HERE), "fonts")
PIXEL_TITLE = "Press Start 2P"
PIXEL_BODY = "VT323"

# Noms affichés des courbes (dans l'ordre de wav2smp.CURVES).
CURVE_LABELS = ["LINEAIRE", "LOG", "SATUREE", "REPLIEE", "INVERSEE"]

# ====================================================================== #
# Thèmes (palette du firmware CPC / moniteur vert GT65), comme CPC DISK
# ====================================================================== #
THEMES = {
    "couleur": dict(
        frame="#0000FF", paper="#000080", panel="#000040", ink="#FFFF00",
        acc="#00FFFF", hi="#FFFFFF", warm="#FF8000", dim="#2828A8",
        btn="#00FFFF", btn_ink="#000080", pri="#FFFF00", pri_ink="#000080",
        danger="#FF0000", danger_ink="#000000",
        r="#FF0000", g="#00FF00", b="#00A0FF"),
    "vert": dict(
        frame="#0B3D16", paper="#021A07", panel="#010D04", ink="#33FF66",
        acc="#9CFFB4", hi="#E0FFE8", warm="#1FA344", dim="#0F4A1E",
        btn="#9CFFB4", btn_ink="#021A07", pri="#33FF66", pri_ink="#021A07",
        danger="#E0FFE8", danger_ink="#021A07",
        r="#33FF66", g="#9CFFB4", b="#E0FFE8"),
}

# Icônes 8x8 (X = pixel allumé), dessinées à l'échelle 2.
ICONS = {
    "open": ("........", "XXX.....", "XXXXXXXX", "XXXXXXXX",
             "XXXXXXXX", "XXXXXXXX", "XXXXXXXX", "........"),
    "new": ("...XX...", "...XX...", "...XX...", "XXXXXXXX",
            "XXXXXXXX", "...XX...", "...XX...", "...XX..."),
    "save": ("XXXXXXX.", "XX...XXX", "XX...XXX", "XXXXXXXX",
             "XXXXXXXX", "XX....XX", "XX....XX", "XXXXXXXX"),
    "trash": ("..XXXX..", "XXXXXXXX", "........", ".XXXXXX.",
              ".X.XX.X.", ".X.XX.X.", ".X.XX.X.", ".XXXXXX."),
    "up": ("........", "...XX...", "..XXXX..", ".XXXXXX.",
           "XXXXXXXX", "...XX...", "...XX...", "........"),
    "down": ("........", "...XX...", "...XX...", "XXXXXXXX",
             ".XXXXXX.", "..XXXX..", "...XX...", "........"),
    "play": (".X......", ".XXX....", ".XXXXX..", ".XXXXXXX",
             ".XXXXXXX", ".XXXXX..", ".XXX....", ".X......"),
    "stop": ("........", ".XXXXXX.", ".XXXXXX.", ".XXXXXX.",
             ".XXXXXX.", ".XXXXXX.", ".XXXXXX.", "........"),
    "disk": ("XXXXXXXX", "X.XXXX.X", "X.XXXX.X", "XXXXXXXX",
             "X......X", "X.XXXX.X", "X......X", "XXXXXXXX"),
    "cut": ("X.....X.", ".X...X..", "..X.X...", "...X....",
            "..X.X...", "XX...XX.", "XX...XX.", "........"),
}


# ====================================================================== #
# Utilitaires
# ====================================================================== #
def _mix(c1, c2, a):
    """Mélange deux couleurs #RRGGBB (a = part de c2)."""
    x = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    y = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join("%02X" % round(p + (q - p) * a) for p, q in zip(x, y))


def _num(n):
    """Entier à la française : 16320 -> '16 320'."""
    return "{:,}".format(n).replace(",", " ")


def _sec(s):
    """Durée en secondes à la française : 0.52 -> '0,52 s'."""
    return ("%.2f s" % s).replace(".", ",")


def _load_private_fonts():
    """Rend les .ttf du dossier fonts/ visibles par Tk (Windows seulement).
    À appeler AVANT la création de la fenêtre Tk. Ailleurs, les polices
    doivent être installées ; sinon une police à chasse fixe les remplace."""
    if sys.platform != "win32" or not os.path.isdir(FONT_DIR):
        return
    try:
        import ctypes
        gdi32 = ctypes.windll.gdi32
        gdi32.AddFontResourceExW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint,
                                             ctypes.c_void_p]
        FR_PRIVATE = 0x10                       # police visible de ce seul processus
        for name in os.listdir(FONT_DIR):
            if name.lower().endswith((".ttf", ".otf")):
                gdi32.AddFontResourceExW(os.path.join(FONT_DIR, name),
                                         FR_PRIVATE, None)
    except Exception:  # noqa: BLE001 - confort visuel, pas critique
        pass


def _register_drag_drop(root, on_drop):
    """Glisser-déposer de fichiers depuis l'explorateur Windows, sans
    dépendance (même méthode que CPC DISK : DragAcceptFiles puis
    sous-classement de la procédure de fenêtre pour lire WM_DROPFILES).
    Renvoie False hors Windows ou en cas d'échec."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
        WM_DROPFILES, GWLP_WNDPROC = 0x0233, -4
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                                     wintypes.WPARAM, wintypes.LPARAM)
        set_wl = (user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8
                  else user32.SetWindowLongW)
        set_wl.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        set_wl.restype = ctypes.c_void_p
        user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND,
                                           wintypes.UINT, wintypes.WPARAM,
                                           wintypes.LPARAM]
        user32.CallWindowProcW.restype = LRESULT
        shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT,
                                           wintypes.LPWSTR, wintypes.UINT]
        shell32.DragQueryFileW.restype = wintypes.UINT
        shell32.DragFinish.argtypes = [ctypes.c_void_p]
        root.update_idletasks()
        hwnd = root.winfo_id()
        try:                                    # processus admin : laisser passer
            user32.ChangeWindowMessageFilterEx.argtypes = [
                wintypes.HWND, wintypes.UINT, wintypes.DWORD, ctypes.c_void_p]
            for msg in (WM_DROPFILES, 0x004A, 0x0049):
                user32.ChangeWindowMessageFilterEx(hwnd, msg, 1, None)
        except Exception:  # noqa: BLE001
            pass
        old_proc = [None]

        def _wndproc(h, msg, wp, lp):
            """Intercepte WM_DROPFILES, laisse le reste à Tk."""
            if msg == WM_DROPFILES:
                count = shell32.DragQueryFileW(wp, 0xFFFFFFFF, None, 0)
                buf = ctypes.create_unicode_buffer(32768)
                paths = [buf.value for i in range(count)
                         if shell32.DragQueryFileW(wp, i, buf, 32768)]
                shell32.DragFinish(wp)
                if paths:
                    root.after(0, lambda p=paths: on_drop(p))
                return 0
            return user32.CallWindowProcW(old_proc[0], h, msg, wp, lp)

        callback = WNDPROC(_wndproc)
        globals()["_drag_drop_callback"] = callback   # garder une référence
        old_proc[0] = set_wl(hwnd, GWLP_WNDPROC, ctypes.cast(callback, ctypes.c_void_p))
        if not old_proc[0]:
            return False
        shell32.DragAcceptFiles(hwnd, True)
        return True
    except Exception:  # noqa: BLE001 - confort, pas critique
        return False


# ====================================================================== #
# Écoute
# ====================================================================== #
class Player:
    """Joue un WAV (octets) sans bloquer l'interface.

    Windows : winsound.PlaySound en asynchrone. CPython refuse
    SND_MEMORY avec SND_ASYNC (« Cannot play asynchronously from memory ») :
    le WAV en mémoire est donc écrit dans un fichier temporaire, joué avec
    SND_FILENAME | SND_ASYNC.
    Ailleurs : fichier temporaire joué par aplay, paplay ou afplay."""

    PLAYERS = (["aplay", "-q"], ["paplay"], ["afplay"])

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="smp_gui_")
        self.proc = None
        self.count = 0

    def play(self, data):
        """Joue data (fichier WAV complet en octets). Renvoie None si la
        lecture démarre, sinon un message d'erreur en français."""
        self.stop()
        self.count += 1
        path = os.path.join(self.tmp, "ecoute%d.wav" % (self.count % 8))
        try:
            with open(path, "wb") as f:
                f.write(data)
        except OSError as e:
            return "Fichier temporaire impossible : %s" % e
        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(path, winsound.SND_FILENAME
                                   | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                return None
            except Exception as e:  # noqa: BLE001
                return "Lecture impossible : %s" % e
        for cmd in self.PLAYERS:
            if shutil.which(cmd[0]):
                try:
                    self.proc = subprocess.Popen(cmd + [path],
                                                 stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.DEVNULL)
                    return None
                except OSError:
                    continue
        return ("Pas de lecteur audio trouvé (aplay, paplay ou afplay). "
                "Le fichier est ici : " + path)

    def stop(self):
        """Arrête la lecture en cours."""
        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:  # noqa: BLE001
                pass
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except OSError:
                pass
        self.proc = None

    def close(self):
        """Arrête et efface les fichiers temporaires."""
        self.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)


# ====================================================================== #
# Widgets pixel art (repris de CPC DISK, en plus compact)
# ====================================================================== #
class PixelButton(tk.Canvas):
    """Bouton à relief 4 px, coins crantés, icône 8x8 facultative."""

    KINDS = {"normal": ("btn", "btn_ink"), "primary": ("pri", "pri_ink"),
             "danger": ("danger", "danger_ink")}

    def __init__(self, master, app, text="", command=None, kind="normal",
                 icon=None, padx=12):
        """Crée le bouton ; text est mis en capitales sans accents."""
        bg_key, fg_key = self.KINDS[kind]
        self._bg, self._fg = getattr(app.t, bg_key), getattr(app.t, fg_key)
        self._dim = app.t.dim
        self._text = app.caps(text)
        self._icon, self._cmd, self._font, self._padx = icon, command, app.f_btn, padx
        self._hover = self._press = self._focus = False
        self._enabled = True
        tw = self._font.measure(self._text) if self._text else 0
        iw = 16 if icon else 0
        self._content_w = tw + iw + (8 if icon and text else 0)
        self._bw = self._content_w + 2 * padx + 8
        self._bh = max(34, self._font.metrics("linespace") + 16)
        super().__init__(master, width=self._bw, height=self._bh,
                         bg=master.cget("bg"), highlightthickness=0, bd=0,
                         cursor="hand2", takefocus=1)
        self.bind("<Enter>", lambda e: self._set(hover=True))
        self.bind("<Leave>", lambda e: self._set(hover=False, press=False))
        self.bind("<ButtonPress-1>", lambda e: self._set(press=True))
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<FocusIn>", lambda e: self._set(focus=True))
        self.bind("<FocusOut>", lambda e: self._set(focus=False))
        self.bind("<space>", lambda e: self.invoke())
        self.bind("<Return>", lambda e: self.invoke())
        self._draw()

    def set_enabled(self, on):
        """Active ou grise le bouton."""
        self._enabled = bool(on)
        self.configure(cursor="hand2" if on else "arrow")
        self._draw()

    def invoke(self):
        """Lance la commande (si le bouton est actif)."""
        if self._cmd and self._enabled:
            self._cmd()

    def _release(self, event):
        """Clic validé seulement si on relâche sur le bouton."""
        inside = 0 <= event.x < self._bw and 0 <= event.y < self._bh
        was = self._press
        self._set(press=False)
        if was and inside:
            self.invoke()

    def _set(self, **kw):
        """Change un état (survol, appui, focus) et redessine."""
        for k, v in kw.items():
            setattr(self, "_" + k, v)
        self._draw()

    def _draw(self):
        """Dessine le bouton : corps, relief, icône, texte."""
        w, h, n = self._bw, self._bh, 4
        self.delete("all")
        base = self._bg if self._enabled else self._dim
        body = _mix(base, "#FFFFFF", 0.15) if self._hover and self._enabled else base
        light, dark = _mix(body, "#FFFFFF", 0.55), _mix(body, "#000000", 0.35)
        press = self._press and self._enabled
        tl, br = (dark, _mix(body, "#FFFFFF", 0.35)) if press else (light, dark)
        self.create_polygon(0, n, n, n, n, 0, w - n, 0, w - n, n, w, n,
                            w, h - n, w - n, h - n, w - n, h, n, h, n, h - n,
                            0, h - n, fill=body, outline="")
        self.create_rectangle(n, 0, w - n, n, fill=tl, outline="")
        self.create_rectangle(0, n, n, h - n, fill=tl, outline="")
        self.create_rectangle(n, h - n, w - n, h, fill=br, outline="")
        self.create_rectangle(w - n, n, w, h - n, fill=br, outline="")
        fg = self._fg if self._enabled else _mix(self._dim, "#FFFFFF", 0.4)
        off = 2 if press else 0
        x = (w - self._content_w) / 2 + off
        cy = h / 2 + off
        if self._icon:
            for r, line in enumerate(ICONS[self._icon]):
                for c, ch in enumerate(line):
                    if ch == "X":
                        px, py = x + c * 2, cy - 8 + r * 2
                        self.create_rectangle(px, py, px + 2, py + 2, fill=fg,
                                              outline="")
            x += 16 + (8 if self._text else 0)
        if self._text:
            self.create_text(x, cy + 1, text=self._text, anchor="w",
                             font=self._font, fill=fg)
        if self._focus:
            self.create_rectangle(6, 6, w - 6, h - 6, outline=fg, dash=(2, 2))


class Panel(tk.Frame):
    """Cadre bordé 4 px avec bandeau de titre en vidéo inverse."""

    def __init__(self, master, app, title):
        """title : texte du bandeau (mis en capitales)."""
        super().__init__(master, bg=app.t.acc, padx=4, pady=4)
        self.head = tk.Label(self, text=app.caps(title), bg=app.t.acc,
                             fg=app.t.paper, font=app.f_head, anchor="w",
                             padx=8, pady=4)
        self.head.pack(fill="x")
        self.body = tk.Frame(self, bg=app.t.panel)
        self.body.pack(fill="both", expand=True)


class Segmented(tk.Frame):
    """Choix exclusif en cases pixel (remplace un menu déroulant)."""

    def __init__(self, master, app, var, options):
        """options : liste de (valeur, texte affiché)."""
        super().__init__(master, bg=master.cget("bg"))
        self.app, self.var = app, var
        self._enabled = True
        self._labels = []
        for value, label in options:
            lbl = tk.Label(self, text=label, font=app.f_body, padx=7, pady=0,
                           cursor="hand2", highlightthickness=2, takefocus=1)
            lbl.pack(side="left", padx=(0, 4))
            lbl.bind("<Button-1>", lambda e, v=value: self._pick(v))
            lbl.bind("<space>", lambda e, v=value: self._pick(v))
            self._labels.append((value, lbl))
        self._trace = var.trace_add("write", lambda *a: self._paint())
        self.bind("<Destroy>", self._untrace, add="+")
        self._paint()

    def _pick(self, value):
        """Choisit une valeur (si actif)."""
        if self._enabled:
            self.var.set(value)

    def set_enabled(self, on):
        """Active ou grise le choix."""
        self._enabled = bool(on)
        self._paint()

    def _untrace(self, _e=None):
        """Retire la surveillance de la variable à la destruction."""
        try:
            self.var.trace_remove("write", self._trace)
        except (tk.TclError, ValueError):
            pass

    def _paint(self):
        """Colore la case choisie en vidéo inverse."""
        t = self.app.t
        for value, lbl in self._labels:
            on = value == self.var.get()
            if self._enabled:
                bg, fg, hl = (t.ink, t.paper, t.ink) if on else (t.panel, t.acc, t.acc)
            else:
                bg, fg, hl = (t.dim, t.paper, t.dim) if on else (t.panel, t.dim, t.dim)
            try:
                lbl.config(bg=bg, fg=fg, highlightbackground=hl, highlightcolor=t.hi)
            except tk.TclError:
                pass


class PixelDialog:
    """Boîte modale (info / erreur / question) dans le style CPC."""

    def __init__(self, app, title, message, kind="info",
                 buttons=(("OK", True, "primary"),)):
        """buttons : liste de (texte, valeur renvoyée, genre de bouton)."""
        t = app.t
        self.result = None
        accent = {"info": t.acc, "error": t.danger, "ask": t.ink}.get(kind, t.acc)
        head_fg = t.danger_ink if kind == "error" else t.paper
        self.win = win = tk.Toplevel(app.root)
        win.title(title)
        win.configure(bg=accent)
        win.transient(app.root)
        win.resizable(False, False)
        tk.Label(win, text=app.caps(title), bg=accent, fg=head_fg,
                 font=app.f_head, anchor="w", padx=12, pady=8).pack(
            fill="x", padx=4, pady=(4, 0))
        body = tk.Frame(win, bg=t.panel, padx=18, pady=14)
        body.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        tk.Label(body, text=message, bg=t.panel, fg=t.hi, font=app.f_body,
                 justify="left", wraplength=560, anchor="w").pack(fill="x", pady=(0, 14))
        row = tk.Frame(body, bg=t.panel)
        row.pack(anchor="e")
        first = None
        for label, value, bkind in buttons:
            b = PixelButton(row, app, label, kind=bkind,
                            command=lambda v=value: self._close(v))
            b.pack(side="left", padx=(8, 0))
            first = first or b
        win.bind("<Escape>", lambda e: self._close(None))
        win.protocol("WM_DELETE_WINDOW", lambda: self._close(None))
        win.update_idletasks()                  # centrer sur la fenêtre principale
        x = app.root.winfo_rootx() + (app.root.winfo_width() - win.winfo_reqwidth()) // 2
        y = app.root.winfo_rooty() + (app.root.winfo_height() - win.winfo_reqheight()) // 3
        win.geometry("+%d+%d" % (max(0, x), max(0, y)))
        win.grab_set()
        if first is not None:
            first.focus_set()
        app.root.wait_window(win)

    def _close(self, value):
        """Ferme la boîte en gardant la réponse."""
        self.result = value
        self.win.destroy()


# ====================================================================== #
# Application
# ====================================================================== #
class SmpApp:
    """La fenêtre de l'éditeur de banques."""

    def __init__(self, root, model=None):
        """root : fenêtre Tk ; model : BankModel (un neuf par défaut)."""
        self.root = root
        self.model = model or BankModel()
        self.player = Player()
        self.bank_path = None                   # dernier .SMP ouvert ou sauvé
        self.dsk_path = os.path.join(ROOT, "build", "seq16.dsk")
        self._theme_name = "couleur"
        self._sel_index = None                  # sample choisi
        self._loading = False                   # vrai pendant le remplissage des champs
        self._apply_id = None                   # réglage en attente (anti-rebond)
        self._status_text = ("Prêt. Ajoute des WAV (Ctrl+W) ou ouvre une "
                             "banque .SMP (Ctrl+O). F1 : aide.")
        self._status_err = False
        root.title("SEQ-16 SAMPLER - banques .SMP")
        self.scale = max(1.0, root.winfo_fpixels("1i") / 96)   # 1,25 à 125 %
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h = min(round(1280 * self.scale), sw - 40), min(round(800 * self.scale), sh - 80)
        root.geometry("%dx%d+%d+%d" % (w, h, max(0, (sw - w) // 2), max(0, (sh - h) // 3)))
        root.minsize(min(1100, sw - 40), min(680, sh - 80))

        # Variables des réglages (survivent au changement de thème)
        self.v_name = tk.StringVar()
        self.v_hz = tk.StringVar()
        self.v_code = tk.StringVar()
        self.v_bits = tk.StringVar(value="4")
        self.v_decim = tk.StringVar(value="1")
        self.v_curve = tk.StringVar(value=str(wav2smp.CURVE_LOG))
        self.v_drive = tk.StringVar(value="1.0")
        self.v_trim = tk.BooleanVar(value=False)
        self.v_clean = tk.BooleanVar(value=False)
        self.v_dither = tk.StringVar(value="none")
        self.v_slices = tk.StringVar(value="1")
        for v in (self.v_name, self.v_code, self.v_bits, self.v_decim,
                  self.v_curve, self.v_drive, self.v_trim, self.v_clean,
                  self.v_dither):
            v.trace_add("write", lambda *a: self._schedule_apply())

        self._setup_fonts()
        self._apply_theme()
        self._build_ui()

        root.bind_all("<Control-o>", lambda e: self.open_smp())
        root.bind_all("<Control-O>", lambda e: self.open_smp())
        root.bind_all("<Control-w>", lambda e: self.add_wavs())
        root.bind_all("<Control-W>", lambda e: self.add_wavs())
        root.bind_all("<Control-s>", lambda e: self.save_smp())
        root.bind_all("<Control-S>", lambda e: self.save_smp())
        root.bind_all("<F3>", lambda e: self.toggle_monitor())
        root.bind_all("<F1>", lambda e: self.show_help())
        root.protocol("WM_DELETE_WINDOW", self.quit)
        if _register_drag_drop(root, self._on_drop):
            self._set_status(self._status_text + " Glisser-déposer actif.")

    # ------------------------------------------------------------------ #
    # Polices et thème
    # ------------------------------------------------------------------ #
    def _setup_fonts(self):
        """Polices pixel si elles sont présentes, sinon chasse fixe."""
        families = set(tkfont.families(self.root))
        mono = next((f for f in ("Consolas", "Lucida Console", "Menlo",
                                 "DejaVu Sans Mono", "Courier New", "Courier")
                     if f in families), "TkFixedFont")
        self.has_title_font = PIXEL_TITLE in families
        has_body = PIXEL_BODY in families
        s = self.scale

        def px8(base):
            """Press Start 2P : toujours un multiple de 8 px (net)."""
            return -8 * max(1, round(base * s / 8))

        if self.has_title_font:
            self.f_title = tkfont.Font(family=PIXEL_TITLE, size=px8(16))
            self.f_head = tkfont.Font(family=PIXEL_TITLE, size=px8(8))
            self.f_btn = tkfont.Font(family=PIXEL_TITLE, size=px8(8))
        else:
            self.f_title = tkfont.Font(family=mono, weight="bold", size=-round(20 * s))
            self.f_head = tkfont.Font(family=mono, weight="bold", size=-round(12 * s))
            self.f_btn = tkfont.Font(family=mono, weight="bold", size=-round(12 * s))
        body = PIXEL_BODY if has_body else mono
        self.f_body = tkfont.Font(family=body, size=-round((20 if has_body else 14) * s))
        self.f_small = tkfont.Font(family=body, size=-round((17 if has_body else 12) * s))

    def caps(self, text):
        """Capitales ; sans accents avec Press Start 2P (comme sur le CPC)."""
        text = text.upper()
        if self.has_title_font:
            text = "".join(c for c in unicodedata.normalize("NFD", text)
                           if unicodedata.category(c) != "Mn")
        return text

    def _apply_theme(self):
        """Couleurs de la fenêtre et des widgets ttk (liste, menu déroulant)."""
        self.t = t = SimpleNamespace(**THEMES[self._theme_name])
        self.root.configure(bg=t.frame)
        st = ttk.Style(self.root)
        st.theme_use("clam")
        st.configure("Pixel.Treeview", background=t.panel, fieldbackground=t.panel,
                     foreground=t.ink, font=self.f_body, borderwidth=0,
                     rowheight=self.f_body.metrics("linespace") + 4, relief="flat")
        st.map("Pixel.Treeview", background=[("selected", t.ink)],
               foreground=[("selected", t.paper)])
        st.configure("Pixel.Treeview.Heading", background=t.panel, foreground=t.acc,
                     font=self.f_small, relief="flat", borderwidth=0, padding=(4, 2))
        st.map("Pixel.Treeview.Heading", background=[("active", t.dim)])
        st.layout("Pixel.Treeview", [("Pixel.Treeview.treearea", {"sticky": "nswe"})])
        st.configure("Pixel.TCombobox", fieldbackground=t.paper, background=t.acc,
                     foreground=t.ink, arrowcolor=t.paper, bordercolor=t.acc,
                     lightcolor=t.paper, darkcolor=t.paper, insertcolor=t.ink,
                     selectbackground=t.ink, selectforeground=t.paper)
        st.map("Pixel.TCombobox", fieldbackground=[("readonly", t.paper)],
               foreground=[("disabled", t.dim)])
        self.root.option_add("*TCombobox*Listbox.background", t.paper)
        self.root.option_add("*TCombobox*Listbox.foreground", t.ink)
        self.root.option_add("*TCombobox*Listbox.selectBackground", t.ink)
        self.root.option_add("*TCombobox*Listbox.selectForeground", t.paper)
        self.root.option_add("*TCombobox*Listbox.font", self.f_body)

    def toggle_monitor(self):
        """F3 : bascule couleur (CTM644) <-> moniteur vert (GT65)."""
        self._theme_name = "vert" if self._theme_name == "couleur" else "couleur"
        self.shell.destroy()
        self._apply_theme()
        self._build_ui()

    # ------------------------------------------------------------------ #
    # Petits constructeurs de widgets
    # ------------------------------------------------------------------ #
    def _label(self, master, text="", fg=None, font=None, **kw):
        """Étiquette sur le fond de son parent."""
        return tk.Label(master, text=text, fg=fg or self.t.ink,
                        bg=master.cget("bg"), font=font or self.f_body, **kw)

    def _entry(self, master, var, width=8):
        """Zone de saisie aux couleurs du thème."""
        t = self.t
        return tk.Entry(master, textvariable=var, width=width, font=self.f_body,
                        bg=t.paper, fg=t.ink, insertbackground=t.ink,
                        insertwidth=8, relief="flat", bd=2, highlightthickness=2,
                        highlightbackground=t.acc, highlightcolor=t.hi,
                        selectbackground=t.ink, selectforeground=t.paper,
                        disabledbackground=t.panel, disabledforeground=t.dim)

    def _spin(self, master, var, width=5, **kw):
        """Compteur (Spinbox) aux couleurs du thème."""
        t = self.t
        return tk.Spinbox(master, textvariable=var, width=width, font=self.f_body,
                          bg=t.paper, fg=t.ink, insertbackground=t.ink,
                          buttonbackground=t.acc, relief="flat", bd=2,
                          highlightthickness=2, highlightbackground=t.acc,
                          highlightcolor=t.hi, selectbackground=t.ink,
                          selectforeground=t.paper, disabledbackground=t.panel,
                          disabledforeground=t.dim, **kw)

    def _check(self, master, text, var):
        """Case à cocher aux couleurs du thème."""
        t = self.t
        return tk.Checkbutton(master, text=text, variable=var, font=self.f_body,
                              bg=t.panel, fg=t.acc, selectcolor=t.paper,
                              activebackground=t.panel, activeforeground=t.hi,
                              disabledforeground=t.dim, highlightthickness=0,
                              bd=0, cursor="hand2")

    # ------------------------------------------------------------------ #
    # Construction de l'interface
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        """Construit toute la fenêtre (rappelée à chaque changement de thème)."""
        t = self.t
        self.shell = tk.Frame(self.root, bg=t.frame, padx=10, pady=10)
        self.shell.pack(fill="both", expand=True)
        screen = tk.Frame(self.shell, bg=t.paper, padx=12, pady=8)
        screen.pack(fill="both", expand=True)

        # --- en-tête ---
        head = tk.Frame(screen, bg=t.paper)
        head.pack(fill="x")
        self._label(head, "SEQ-16 SAMPLER", font=self.f_title).pack(side="left")
        self._label(head, "  WAV -> banque .SMP pour Amstrad CPC", fg=t.acc).pack(
            side="left", anchor="s")
        PixelButton(head, self, "F3 Moniteur %s" % ("couleur" if self._theme_name == "vert"
                                                    else "vert"),
                    command=self.toggle_monitor).pack(side="right")
        stripes = tk.Frame(head, bg=t.paper)
        stripes.pack(side="right", padx=(0, 14))
        for c in (t.r, t.g, t.b):
            tk.Frame(stripes, bg=c, width=130, height=6).pack(pady=1)
        tk.Frame(screen, bg=t.ink, height=4).pack(fill="x", pady=(6, 8))

        # --- pied : sorties et ligne d'état (avant le contenu pour rester visible) ---
        foot = tk.Frame(screen, bg=t.paper)
        foot.pack(side="bottom", fill="x", pady=(8, 0))
        self.b_save = PixelButton(foot, self, "Sauver .SMP", kind="primary",
                                  icon="save", command=self.save_smp)
        self.b_save.pack(side="left")
        self.b_dsk = PixelButton(foot, self, "Ajouter à la disquette", icon="disk",
                                 command=self.add_to_dsk)
        self.b_dsk.pack(side="left", padx=(8, 0))
        self.status = self._label(foot, "", fg=t.hi, anchor="w", justify="left",
                                  width=1, font=self.f_small)
        self.status.pack(side="left", fill="x", expand=True, padx=(14, 0))
        self.status.bind("<Configure>", lambda e: self.status.config(
            wraplength=max(100, e.width - 4)))

        # --- contenu : banque à gauche, réglages et forme d'onde à droite ---
        content = tk.Frame(screen, bg=t.paper)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=5, minsize=480)
        content.columnconfigure(1, weight=6, minsize=600)
        content.rowconfigure(0, weight=1)
        left = tk.Frame(content, bg=t.paper)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = tk.Frame(content, bg=t.paper)
        right.grid(row=0, column=1, sticky="nsew")
        self._build_bank_panel(left)
        self._build_settings_panel(right)
        self._build_wave_panel(right)

        self._set_status(self._status_text, self._status_err)
        self.refresh(keep=self._sel_index)

    def _build_bank_panel(self, parent):
        """Panneau de gauche : liste des samples, boutons, jauge de mémoire."""
        t = self.t
        p = Panel(parent, self, "Banque (16 samples au plus)")
        p.pack(fill="both", expand=True)
        body = p.body
        # Boutons sous la liste (empaquetés d'abord pour rester visibles)
        gauge = tk.Frame(body, bg=t.panel, padx=8, pady=6)
        gauge.pack(side="bottom", fill="x")
        self.gauge = tk.Canvas(gauge, height=22, bg=t.paper, highlightthickness=2,
                               highlightbackground=t.acc, bd=0)
        self.gauge.pack(fill="x")
        self.gauge.bind("<Configure>", lambda e: self._draw_gauge())
        self.gauge_lbl = self._label(gauge, "", fg=t.acc, anchor="w",
                                     font=self.f_small)
        self.gauge_lbl.pack(fill="x", pady=(4, 0))

        bar2 = tk.Frame(body, bg=t.panel, padx=8)
        bar2.pack(side="bottom", fill="x", pady=(4, 0))
        self.b_remove = PixelButton(bar2, self, "Retirer", icon="trash",
                                    kind="danger", command=self.remove)
        self.b_remove.pack(side="left")
        self.b_up = PixelButton(bar2, self, "", icon="up", padx=8,
                                command=lambda: self.move(-1))
        self.b_up.pack(side="left", padx=(8, 0))
        self.b_down = PixelButton(bar2, self, "", icon="down", padx=8,
                                  command=lambda: self.move(1))
        self.b_down.pack(side="left", padx=(8, 0))
        bar1 = tk.Frame(body, bg=t.panel, padx=8)
        bar1.pack(side="bottom", fill="x", pady=(6, 0))
        PixelButton(bar1, self, "Ajouter WAV", icon="new",
                    command=self.add_wavs).pack(side="left")
        PixelButton(bar1, self, "Ouvrir .SMP", icon="open",
                    command=self.open_smp).pack(side="left", padx=(8, 0))

        # La liste
        cols = (("n", "N°", 34, "e"), ("nom", "NOM", 78, "w"),
                ("duree", "DURÉE", 72, "e"), ("hz", "FRÉQ.", 70, "e"),
                ("nop", "NOP", 44, "e"), ("oct", "OCTETS", 70, "e"),
                ("src", "SOURCE", 120, "w"))
        frame = tk.Frame(body, bg=t.panel, padx=6, pady=6)
        frame.pack(side="top", fill="both", expand=True)
        self.tree = ttk.Treeview(frame, style="Pixel.Treeview", show="headings",
                                 selectmode="browse", columns=[c[0] for c in cols])
        for key, title, width, anchor in cols:
            self.tree.heading(key, text=title, anchor=anchor)
            self.tree.column(key, width=width, anchor=anchor,
                             stretch=(key == "src"), minwidth=30)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Delete>", lambda e: self.remove())

    def _build_settings_panel(self, parent):
        """Panneau des réglages du sample choisi."""
        t = self.t
        p = Panel(parent, self, "Réglages du sample")
        p.pack(side="top", fill="x")
        g = tk.Frame(p.body, bg=t.panel, padx=10, pady=6)
        g.pack(fill="x")
        g.columnconfigure(1, weight=1)
        self._widgets_src = []                  # widgets réservés aux samples avec WAV
        self._widgets_all = []                  # widgets actifs dès qu'un sample est choisi

        def lab(text, row):
            """Étiquette de la colonne de gauche."""
            self._label(g, text, fg=t.acc, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=2)

        def line(row):
            """Ligne (cadre) de la colonne de droite."""
            f = tk.Frame(g, bg=t.panel)
            f.grid(row=row, column=1, sticky="w", pady=2)
            return f

        # Nom
        lab("NOM", 0)
        f = line(0)
        e = self._entry(f, self.v_name, width=8)
        e.pack(side="left")
        e.bind("<Return>", lambda ev: self._sync_fields())
        e.bind("<FocusOut>", lambda ev: self._sync_fields())
        self._widgets_all.append(e)
        self.src_lbl = self._label(f, "", fg=t.hi, font=self.f_small, anchor="w")
        self.src_lbl.pack(side="left", padx=(12, 0))

        # Fréquence : Hz (préréglages ou saisie) et période en NOP
        lab("FRÉQUENCE", 1)
        f = line(1)
        cb = ttk.Combobox(f, textvariable=self.v_hz, width=7, style="Pixel.TCombobox",
                          values=[str(r) for r in RATE_PRESETS], font=self.f_body)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda ev: self._hz_entered())
        cb.bind("<Return>", lambda ev: self._hz_entered())
        cb.bind("<FocusOut>", lambda ev: self._hz_entered())
        self._widgets_all.append(cb)
        self._label(f, "Hz   période", fg=t.acc).pack(side="left", padx=(6, 6))
        sp = self._spin(f, self.v_code, width=4, from_=wav2smp.CODE_MIN,
                        to=wav2smp.CODE_MAX, increment=1)
        sp.pack(side="left")
        self._widgets_all.append(sp)
        self._label(f, "NOP (µs)", fg=t.acc).pack(side="left", padx=(6, 0))
        self.rate_lbl = self._label(f, "", fg=t.hi, font=self.f_small)
        self.rate_lbl.pack(side="left", padx=(10, 0))

        # Bits, décimation, courbe
        lab("BITS", 2)
        self.seg_bits = Segmented(line(2), self, self.v_bits,
                                  [(str(b), str(b)) for b in (4, 3, 2, 1)])
        self.seg_bits.pack(side="left")
        lab("DÉCIMATION", 3)
        self.seg_decim = Segmented(line(3), self, self.v_decim,
                                   [(str(d), str(d)) for d in wav2smp.DECIMS])
        self.seg_decim.pack(side="left")
        lab("COURBE", 4)
        self.seg_curve = Segmented(line(4), self, self.v_curve,
                                   [(str(i), c) for i, c in enumerate(CURVE_LABELS)])
        self.seg_curve.pack(side="left")

        # Réglages de conversion (il faut le WAV d'origine)
        lab("CONVERSION", 5)
        f = line(5)
        self._label(f, "drive", fg=t.acc).pack(side="left", padx=(0, 4))
        sp = self._spin(f, self.v_drive, width=4, from_=0.5, to=8.0, increment=0.5,
                        format="%.1f")
        sp.pack(side="left")
        self._widgets_src.append(sp)
        for text, var in (("trim", self.v_trim), ("clean", self.v_clean)):
            c = self._check(f, text, var)
            c.pack(side="left", padx=(12, 0))
            self._widgets_src.append(c)
        self._label(f, "tramage", fg=t.acc).pack(side="left", padx=(12, 4))
        self.seg_dither = Segmented(f, self, self.v_dither,
                                    [("none", "aucun"), ("noise", "bruit")])
        self.seg_dither.pack(side="left")

        lab("TRANCHES", 6)
        f = line(6)
        sp = self._spin(f, self.v_slices, width=3, from_=1, to=16, increment=1)
        sp.pack(side="left")
        self._widgets_src.append(sp)
        self.b_slice = PixelButton(f, self, "Découper", icon="cut", padx=8,
                                   command=self.apply_slices)
        self.b_slice.pack(side="left", padx=(8, 0))
        self._label(f, "le WAV en N parts égales (comme --slice)",
                    fg=t.acc, font=self.f_small).pack(side="left", padx=(8, 0))

        # Message d'aide sur le type de sample
        self.note = self._label(g, "", fg=t.warm, font=self.f_small, anchor="w",
                                justify="left")
        self.note.grid(row=7, column=0, columnspan=2, sticky="we", pady=(4, 0))
        self.note.bind("<Configure>", lambda e: self.note.config(
            wraplength=max(100, e.width - 4)))

    def _build_wave_panel(self, parent):
        """Panneau de la forme d'onde et des boutons d'écoute."""
        t = self.t
        p = Panel(parent, self, "Forme d'onde : origine / rendu CPC")
        p.pack(side="top", fill="both", expand=True, pady=(8, 0))
        bar = tk.Frame(p.body, bg=t.panel, padx=8, pady=6)
        bar.pack(side="bottom", fill="x")
        self.b_play_src = PixelButton(bar, self, "Écouter l'origine", icon="play",
                                      command=lambda: self.play(False))
        self.b_play_src.pack(side="left")
        self.b_play_cpc = PixelButton(bar, self, "Écouter le CPC", icon="play",
                                      kind="primary", command=lambda: self.play(True))
        self.b_play_cpc.pack(side="left", padx=(8, 0))
        PixelButton(bar, self, "Stop", icon="stop",
                    command=self.player.stop).pack(side="left", padx=(8, 0))
        self.wave = tk.Canvas(p.body, bg=t.paper, highlightthickness=0, bd=0,
                              height=120)
        self.wave.pack(side="top", fill="both", expand=True, padx=8, pady=(8, 0))
        self.wave.bind("<Configure>", lambda e: self._draw_wave())

    # ------------------------------------------------------------------ #
    # Rafraîchissement
    # ------------------------------------------------------------------ #
    def _set_status(self, text, error=False):
        """Ligne d'état en bas (rouge/inverse si erreur)."""
        self._status_text, self._status_err = text, error
        try:
            self.status.config(text=text, fg=self.t.danger if error else self.t.hi)
        except (tk.TclError, AttributeError):
            pass

    def refresh(self, keep=None):
        """Recharge la liste, la jauge, les champs et la forme d'onde.
        keep : indice du sample à garder choisi."""
        self.tree.delete(*self.tree.get_children())
        for i, it in enumerate(self.model.items):
            if it.has_source:
                src = os.path.basename(it.path)
                if it.part[1] > 1:
                    src += " [%d/%d]" % (it.part[0] + 1, it.part[1])
            else:
                src = "(banque .SMP)"
            self.tree.insert("", "end", iid=str(i), values=(
                i, it.name, _sec(it.seconds), _num(round(it.rate)), it.code,
                _num(len(it.data)), src))
        n = len(self.model.items)
        if keep is not None and n:
            keep = max(0, min(n - 1, keep))
            self.tree.selection_set(str(keep))
            self.tree.see(str(keep))
        self._sel_index = keep if n else None
        self._fill_fields()
        self._draw_gauge()
        self._draw_wave()

    def _update_row(self, i):
        """Met à jour une seule ligne de la liste (après un réglage)."""
        it = self.model.items[i]
        vals = list(self.tree.item(str(i), "values"))
        vals[1:6] = [it.name, _sec(it.seconds), _num(round(it.rate)), it.code,
                     _num(len(it.data))]
        self.tree.item(str(i), values=vals)

    def _draw_gauge(self):
        """Jauge de mémoire : octets utilisés sur 16 320 (rouge au-delà)."""
        try:
            c = self.gauge
            c.delete("all")
        except (tk.TclError, AttributeError):
            return
        t = self.t
        used = self.model.used_bytes()
        limit = wav2smp.BANK_MAX_MAIN
        over = used > limit
        w, h = max(1, c.winfo_width()), max(1, c.winfo_height())
        frac = min(1.0, used / limit)
        c.create_rectangle(0, 0, w * frac, h, fill=t.danger if over else t.ink,
                           outline="")
        for k in range(1, 4):                   # repères tous les 4 Ko
            x = w * k * 4096 / limit
            c.create_line(x, 0, x, h, fill=t.dim)
        pct = 100 * used / limit
        txt = "MÉMOIRE : %s / %s octets (%d %%) - %d sample(s), %s" % (
            _num(used), _num(limit), round(pct), len(self.model),
            _sec(self.model.total_seconds()))
        if over:
            txt += " - TROP GRAND de %s octets : sauvegarde refusée" % _num(used - limit)
        self.gauge_lbl.config(text=txt, fg=t.danger if over else t.acc)
        ok = 0 < used <= limit
        self.b_save.set_enabled(ok)
        self.b_dsk.set_enabled(ok)

    def _draw_wave(self):
        """Dessine l'origine (en haut) et le rendu CPC (en bas), même échelle
        de temps."""
        try:
            c = self.wave
            c.delete("all")
        except (tk.TclError, AttributeError):
            return
        t = self.t
        w, h = max(10, c.winfo_width()), max(10, c.winfo_height())
        i = self._sel_index
        if i is None:
            c.create_text(w / 2, h / 2, text="Choisis un sample dans la liste",
                          fill=t.acc, font=self.f_body)
            return
        try:
            orig = self.model.original(i)
            cpc = self.model.rendered(i)
        except BankError as e:
            c.create_text(w / 2, h / 2, text=str(e), fill=t.danger, font=self.f_body)
            return
        dur = max(len(cpc[0]) / cpc[1], len(orig[0]) / orig[1] if orig else 0, 1e-6)
        lane = h / 2
        for k, (sig, col, title) in enumerate((
                (orig, t.acc, "ORIGINE"), (cpc, t.ink, "RENDU CPC"))):
            top = k * lane
            mid = top + lane / 2
            c.create_line(0, mid, w, mid, fill=t.dim)
            c.create_text(6, top + 4, text=title, anchor="nw", fill=col,
                          font=self.f_small)
            if sig is None:
                c.create_text(w / 2, mid, text="Pas de WAV d'origine : sample "
                              "relu dans une banque .SMP", fill=t.warm,
                              font=self.f_small)
                continue
            self._draw_signal(c, sig[0], sig[1], dur, w, mid, lane * 0.42, col)
        c.create_line(0, lane, w, lane, fill=t.acc)
        c.create_text(w - 6, h - 4, text=_sec(dur), anchor="se", fill=t.acc,
                      font=self.f_small)

    @staticmethod
    def _draw_signal(c, x, rate, dur, w, mid, amp, col):
        """Enveloppe min/max par colonne de pixels d'un signal."""
        if not x:
            return
        peak = max(1e-9, max(abs(v) for v in x))
        width = max(1, int(w * (len(x) / rate) / dur))   # pixels occupés
        step = len(x) / width
        for px in range(width):
            a, b = int(px * step), max(int(px * step) + 1, int((px + 1) * step))
            seg = x[max(0, a - 1):b]            # + point d'avant : marches reliées
            lo, hi = min(seg), max(seg)
            c.create_line(px, mid - hi / peak * amp, px, mid - lo / peak * amp + 1,
                          fill=col)

    def _fill_fields(self):
        """Remplit les champs avec les réglages du sample choisi."""
        i = self._sel_index
        has = i is not None
        it = self.model.items[i] if has else None
        self._loading = True
        try:
            if has:
                s = it.settings()
                self.v_name.set(s["name"])
                self.v_code.set(str(s["code"]))
                self.v_hz.set(str(round(it.rate)))
                self.v_bits.set(str(s["bits"]))
                self.v_decim.set(str(s["decim"]))
                self.v_curve.set(str(s["curve"]))
                self.v_drive.set("%.1f" % s["drive"] if s["drive"] * 10 == int(s["drive"] * 10)
                                 else str(s["drive"]))
                self.v_trim.set(s["trim"])
                self.v_clean.set(s["clean"])
                self.v_dither.set(s["dither"])
                self.v_slices.set(str(s["slices"]))
        finally:
            self._loading = False
        src = has and it.has_source
        for wdg in self._widgets_all:
            wdg.configure(state="normal" if has else "disabled")
        for wdg in self._widgets_src:
            wdg.configure(state="normal" if src else "disabled")
        for seg in (self.seg_bits, self.seg_decim, self.seg_curve):
            seg.set_enabled(has)
        self.seg_dither.set_enabled(src)
        self.b_slice.set_enabled(src)
        self.b_play_src.set_enabled(src)
        self.b_play_cpc.set_enabled(has)
        for b in (self.b_remove, self.b_up, self.b_down):
            b.set_enabled(has)
        if not has:
            self.src_lbl.config(text="")
            self.rate_lbl.config(text="")
            self.note.config(text="Aucun sample choisi.")
        elif src:
            self.src_lbl.config(text=os.path.basename(it.path))
            self.note.config(text="Chaque réglage reconvertit le son depuis le WAV "
                             "d'origine. Décimation et courbe ne sont que des "
                             "réglages de lecture (stockés dans la fiche).")
        else:
            self.src_lbl.config(text="(relu dans une banque .SMP)")
            self.note.config(text="Sample relu dans une banque .SMP : il n'y a "
                             "pas de WAV d'origine à reconvertir. Seuls le nom, "
                             "la fréquence, les bits, la décimation et la courbe "
                             "se modifient, et ils ne changent que la fiche (pas "
                             "les données), comme sur l'écran f4 du CPC.")
        self._show_rate()

    def _show_rate(self):
        """Affiche la fréquence réelle et la durée du sample choisi."""
        i = self._sel_index
        if i is None:
            return
        it = self.model.items[i]
        self.rate_lbl.config(text="= %s Hz, %s, %s octets" % (
            ("%.0f" % it.rate), _sec(it.seconds), _num(len(it.data))))

    def _sync_fields(self):
        """Réécrit les champs avec les valeurs retenues (nom nettoyé, etc.)."""
        self._apply_now()
        self._fill_fields()

    # ------------------------------------------------------------------ #
    # Réglages
    # ------------------------------------------------------------------ #
    def _on_select(self, _e=None):
        """Un sample est choisi dans la liste."""
        if self._apply_id:                      # appliquer d'abord ce qui attend
            self._apply_now()
        sel = self.tree.selection()
        new = int(sel[0]) if sel else None
        if new == self._sel_index:
            return
        self._sel_index = new
        self._fill_fields()
        self._draw_wave()

    def _schedule_apply(self):
        """Un champ a changé : application différée (anti-rebond 250 ms)."""
        if self._loading or self._sel_index is None:
            return
        if self._apply_id:
            self.root.after_cancel(self._apply_id)
        self._apply_id = self.root.after(250, self._apply_now)

    def _hz_entered(self):
        """Fréquence saisie ou choisie en Hz : convertie en période (NOP)."""
        if self._loading or self._sel_index is None:
            return
        txt = self.v_hz.get().strip().replace(" ", "").replace(",", ".")
        try:
            hz = float(txt)
        except ValueError:
            self._set_status("Fréquence invalide : %s" % txt, True)
            return
        if not 4000 <= hz <= 16200:
            self._set_status("La fréquence va de 4 000 à 16 000 Hz.", True)
            return
        code = str(wav2smp.rate_to_code(hz))
        if code != self.v_code.get():
            self.v_code.set(code)               # déclenche l'application
        self._loading = True
        self.v_hz.set(str(round(wav2smp.code_to_rate(int(code)))))
        self._loading = False

    def _read_fields(self, it):
        """Lit les champs -> dictionnaire de réglages pour BankModel.update."""
        d = dict(name=self.v_name.get(), code=int(self.v_code.get()),
                 bits=int(self.v_bits.get()), decim=int(self.v_decim.get()),
                 curve=int(self.v_curve.get()))
        if it.has_source:
            d.update(drive=float(self.v_drive.get().replace(",", ".")),
                     trim=self.v_trim.get(), clean=self.v_clean.get(),
                     dither=self.v_dither.get())
        return d

    def _apply_now(self):
        """Applique les champs au sample choisi (reconversion si besoin)."""
        if self._apply_id:
            self.root.after_cancel(self._apply_id)
        self._apply_id = None
        i = self._sel_index
        if i is None or self._loading or i >= len(self.model):
            return
        it = self.model.items[i]
        try:
            d = self._read_fields(it)
        except (ValueError, tk.TclError):
            self._set_status("Valeur invalide dans un champ (nombre attendu).", True)
            return
        old = it.settings()
        try:
            self._busy(True)
            self.model.update(i, **d)
        except BankError as e:
            self._set_status(str(e), True)
            return
        finally:
            self._busy(False)
        if it.settings() != old:
            self._set_status("%s : %s octets, %s à %.0f Hz." % (
                it.name, _num(len(it.data)), _sec(it.seconds), it.rate))
        self._update_row(i)
        self._loading = True
        self.v_hz.set(str(round(it.rate)))
        self._loading = False
        self._show_rate()
        self._draw_gauge()
        self._draw_wave()

    def _busy(self, on):
        """Curseur sablier pendant une conversion."""
        try:
            self.root.config(cursor="watch" if on else "")
            if on:
                self.root.update_idletasks()
        except tk.TclError:
            pass

    def apply_slices(self):
        """Découpe le WAV du sample choisi en N tranches."""
        i = self._sel_index
        if i is None:
            return
        try:
            n = int(self.v_slices.get())
        except ValueError:
            self._set_status("Nombre de tranches invalide.", True)
            return
        self._apply_now()
        try:
            self._busy(True)
            first = self.model.set_slices(i, n)
        except BankError as e:
            self.error("Découpage impossible", str(e))
            return
        finally:
            self._busy(False)
        self._set_status("WAV découpé en %d tranche(s)." % n)
        self.refresh(keep=first)

    # ------------------------------------------------------------------ #
    # Liste
    # ------------------------------------------------------------------ #
    def add_wavs(self, paths=None):
        """Ajoute un ou plusieurs WAV (boîte de dialogue si paths est vide)."""
        if not paths:
            paths = filedialog.askopenfilenames(
                parent=self.root, title="Ajouter des WAV",
                initialdir=os.path.join(ROOT, "samples"),
                filetypes=[("Fichiers WAV", "*.wav *.WAV"), ("Tous", "*.*")])
        if not paths:
            return
        self._apply_now()
        added, errors = [], []
        self._busy(True)
        try:
            for p in paths:
                try:
                    added.append(self.model.add_wav(p))
                except BankError as e:
                    errors.append(str(e))
                    if len(self.model) >= wav2smp.MAX_SAMPLES:
                        break
        finally:
            self._busy(False)
        if added:
            self.refresh(keep=added[-1])
            self._set_status("%d WAV ajouté(s)." % len(added))
        if errors:
            self.error("WAV non ajoutés", "\n".join(errors))

    def remove(self):
        """Retire le sample choisi."""
        i = self._sel_index
        if i is None:
            return
        self._apply_now()
        name = self.model.items[i].name
        self.model.remove(i)
        self.refresh(keep=i)
        self._set_status("%s retiré." % name)

    def move(self, delta):
        """Monte (-1) ou descend (+1) le sample choisi."""
        i = self._sel_index
        if i is None:
            return
        self._apply_now()
        self.refresh(keep=self.model.move(i, delta))

    def open_smp(self, path=None):
        """Ouvre une banque .SMP existante (remplace la banque en cours)."""
        if not path:
            path = filedialog.askopenfilename(
                parent=self.root, title="Ouvrir une banque .SMP",
                initialdir=os.path.join(ROOT, "samples"),
                filetypes=[("Banques SEQ-16", "*.smp *.SMP"), ("Tous", "*.*")])
        if not path:
            return
        self._apply_now()
        if self.model.items and self.model.dirty and not self.ask(
                "Ouvrir une banque",
                "La banque en cours n'est pas sauvée. La remplacer ?"):
            return
        try:
            self.model.open_bank(path)
        except BankError as e:
            self.error("Ouverture impossible", str(e))
            return
        self.bank_path = path
        self.refresh(keep=0)
        self._set_status("%s ouvert : %d sample(s). Pas de WAV d'origine : seuls "
                         "nom, fréquence, bits, décimation et courbe se "
                         "modifient." % (os.path.basename(path), len(self.model)))

    def _on_drop(self, paths):
        """Fichiers déposés : WAV ajoutés, premier .SMP ouvert."""
        wavs = [p for p in paths if p.lower().endswith(".wav")]
        smps = [p for p in paths if p.lower().endswith(".smp")]
        if smps:
            self.open_smp(smps[0])
        if wavs:
            self.add_wavs(wavs)
        if not wavs and not smps:
            self._set_status("Seuls les fichiers .wav et .smp sont acceptés.", True)

    # ------------------------------------------------------------------ #
    # Écoute
    # ------------------------------------------------------------------ #
    def play(self, cpc):
        """Écoute le rendu CPC (cpc vrai) ou le son d'origine."""
        i = self._sel_index
        if i is None:
            return
        self._apply_now()
        try:
            data = self.model.rendered_wav(i) if cpc else self.model.original_wav(i)
        except BankError as e:
            self._set_status(str(e), True)
            return
        if data is None:
            self._set_status("Pas de WAV d'origine pour ce sample.", True)
            return
        err = self.player.play(data)
        if err:
            self._set_status(err, True)
        else:
            self._set_status("Écoute : %s (%s)." % (self.model.items[i].name,
                                                   "rendu CPC" if cpc else "origine"))

    # ------------------------------------------------------------------ #
    # Sorties
    # ------------------------------------------------------------------ #
    def _check_ready(self):
        """Vrai si la banque peut être écrite ; sinon explique pourquoi."""
        self._apply_now()
        try:
            self.model.checked_bytes()
            return True
        except BankError as e:
            self.error("Banque refusée", str(e))
            return False

    def save_smp(self):
        """Sauve la banque dans un .SMP (dossier samples/ par défaut).
        Renvoie True si le fichier est écrit."""
        if not self._check_ready():
            return False
        init = self.bank_path or os.path.join(ROOT, "samples", "MABANK.SMP")
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Sauver la banque .SMP",
            initialdir=os.path.dirname(init), initialfile=os.path.basename(init),
            defaultextension=".SMP",
            filetypes=[("Banques SEQ-16", "*.SMP *.smp"), ("Tous", "*.*")])
        if not path:
            return False
        try:
            size = self.model.save(path)
        except BankError as e:
            self.error("Sauvegarde impossible", str(e))
            return False
        self.bank_path = path
        self._set_status("%s sauvé : %s octets (%s octets de données)." % (
            path, _num(size), _num(self.model.used_bytes())))
        return True

    def add_to_dsk(self):
        """Ajoute la banque à une disquette .dsk (build/seq16.dsk par défaut),
        sous un nom AMSDOS 8.3 tiré du nom du fichier .SMP."""
        if not self._check_ready():
            return
        if not self.bank_path and not self.save_smp():
            self._set_status("Sauve d'abord la banque : son nom de fichier "
                             "donne le nom sur la disquette.", True)
            return
        dsk = filedialog.askopenfilename(
            parent=self.root, title="Choisir la disquette .dsk",
            initialdir=os.path.dirname(self.dsk_path),
            initialfile=os.path.basename(self.dsk_path),
            filetypes=[("Disquettes CPC", "*.dsk *.DSK"), ("Tous", "*.*")])
        if not dsk:
            return
        name = dsk_name(self.bank_path)
        try:
            exists = self.model.dsk_has(dsk, name)
        except BankError as e:
            self.error("Disquette illisible", str(e))
            return
        if exists and not self.ask("Remplacer ?", "%s existe déjà sur %s. "
                                   "Le remplacer ?" % (name, os.path.basename(dsk))):
            return
        try:
            self.model.add_to_dsk(dsk, name)
        except BankError as e:
            self.error("Ajout impossible", str(e))
            return
        self.dsk_path = dsk
        self._set_status("%s ajouté à %s." % (name, dsk))

    # ------------------------------------------------------------------ #
    # Boîtes et fin
    # ------------------------------------------------------------------ #
    def error(self, title, message):
        """Boîte d'erreur."""
        PixelDialog(self, title, message, kind="error")

    def ask(self, title, message):
        """Question oui / non ; renvoie True pour oui."""
        dlg = PixelDialog(self, title, message, kind="ask",
                          buttons=(("Non", False, "normal"), ("Oui", True, "primary")))
        return bool(dlg.result)

    def show_help(self):
        """F1 : rappel des raccourcis."""
        PixelDialog(self, "Aide", (
            "Ctrl+W : ajouter des WAV\n"
            "Ctrl+O : ouvrir une banque .SMP\n"
            "Ctrl+S : sauver la banque .SMP\n"
            "Suppr : retirer le sample choisi (dans la liste)\n"
            "F3 : moniteur couleur / vert\n\n"
            "Une banque tient en %s octets de données au plus (mémoire "
            "principale du CPC, #0040-#3FFF). Une seconde à 8 000 Hz occupe "
            "4 000 octets." % _num(wav2smp.BANK_MAX_MAIN)))

    def quit(self):
        """Fermeture : propose de garder une banque non sauvée."""
        self._apply_now()
        if self.model.items and self.model.dirty and not self.ask(
                "Quitter", "La banque n'est pas sauvée. Quitter quand même ?"):
            return
        self.player.close()
        self.root.destroy()


def run():
    """Point d'entrée : crée la fenêtre et lance la boucle Tk."""
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)    # Windows 8.1 et plus
        except Exception:  # noqa: BLE001
            try:
                ctypes.windll.user32.SetProcessDPIAware()     # Windows 7
            except Exception:  # noqa: BLE001
                pass
    _load_private_fonts()
    root = tk.Tk()
    app = SmpApp(root)
    for p in sys.argv[1:]:                      # fichiers passés en argument
        app._on_drop([p])
    root.mainloop()


if __name__ == "__main__":
    run()
