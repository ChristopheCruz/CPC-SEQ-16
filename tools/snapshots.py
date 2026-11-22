"""snapshots.py : refait les captures d'écran de SEQ-16 (snapshots/).

Le programme tourne dans le CPC simulé (tools/cpcsim.py) ; chaque scène
appuie sur quelques touches, puis l'écran est dessiné avec la police de la
ROM du CPC, dans les quatre couleurs du programme (mode 1 : 40 colonnes),
avec la bordure, agrandi 4 fois (1344 × 864) pour les README, 2 fois
(672 × 432) pour le site.  Les scènes partent de la disquette de
démonstration (tools/gen_demo.py), morceau ARCADE chargé.

La police vient de la ROM système du CPC 6128 (OS6128.ROM, la matrice des
caractères est à #3800). Elle n'est pas dans le dépôt : le script la
cherche dans la variable CPC_ROM, puis dans le WinAPE de CPC-DISK voisin
(cpc_tools/WinAPE20B2/ROM/OS6128.ROM).

    python tools/snapshots.py                 # fr, en et es
    python tools/snapshots.py fr --rom C:\\WinAPE\\ROM\\OS6128.ROM

Sorties : snapshots/*.png (français), snapshots/en/*.png, snapshots/es/*.png,
et docs/assets/img/<langue>/*.png (le site).
Il faut les disquettes de build/ (build.bat) et le paquet z80.
"""
import argparse
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import cpcsim  # noqa: E402
from cpcsim import (CPC, KEY_INST, KEY_DISK, KEY_SAMPLE, KEY_SPACE,  # noqa: E402
                    KEY_SONG, KEY_MOTIF, KEY_LOAD)  # noqa: E402

KEY_C, KEY_DOWN = 62, 2

# Couleurs : encre 0 bleu, 1 jaune, 2 cyan (couleurs du CPC au démarrage),
# 3 orange (le programme la change). La bordure est bleue.
INKS = [(0, 0, 127), (255, 255, 0), (0, 255, 255), (255, 127, 0)]
BORDER = INKS[0]
SCALE = 4
BORDER_PX = 8                     # pixels CPC (mode 1) de bordure autour du texte
MATRIX = 0x3800                   # matrice des caractères dans OS6128.ROM


def find_rom(explicit=None):
    cands = [explicit, os.environ.get("CPC_ROM")]
    up = ROOT
    for _ in range(6):
        up = os.path.dirname(up)
        for name in ("CPC-DISK", "AmstradCPC"):
            cands.append(os.path.join(up, name, "cpc_tools", "WinAPE20B2", "ROM", "OS6128.ROM"))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    raise SystemExit("OS6128.ROM introuvable : --rom <fichier> ou variable CPC_ROM")


def load_font(path):
    with open(path, "rb") as fh:
        rom = fh.read()
    if len(rom) < MATRIX + 256 * 8:
        raise SystemExit(f"{path} : ce n'est pas une ROM système de CPC 6128")
    return rom[MATRIX:MATRIX + 256 * 8]


def render(cpc, font, scale=SCALE):
    """Image RGB (largeur, hauteur, octets) de l'écran du CPC simulé."""
    SCALE = scale
    cols, rows = 40, 25
    w = (cols * 8 + 2 * BORDER_PX) * SCALE
    h = (rows * 8 + 2 * BORDER_PX) * SCALE
    border_row = bytes(BORDER) * w
    lines = [border_row] * (BORDER_PX * SCALE)
    side = bytes(BORDER) * (BORDER_PX * SCALE)
    for r in range(rows):
        for y in range(8):
            line = bytearray(side)
            for c in range(cols):
                code = cpc.codes[r][c]
                pen, paper = cpc.attr[r][c]
                bits = font[code * 8 + y]
                fg, bg = bytes(INKS[pen & 3]), bytes(INKS[paper & 3])
                for x in range(8):
                    line += (fg if bits & (0x80 >> x) else bg) * SCALE
            line += side
            lines.extend([bytes(line)] * SCALE)
    lines.extend([border_row] * (BORDER_PX * SCALE))
    return w, h, b"".join(lines)


def write_png(path, w, h, rgb):
    raw = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


class SnapCPC(CPC):
    """Le CPC simulé, avec un catalogue AMSDOS qui s'affiche (CAS_CATALOG).

    Comme AMSDOS : « Drive A: user  0 », les fichiers par ordre alphabétique
    sur deux colonnes (taille en Ko de blocs), puis la place libre ; le texte
    défile dans la fenêtre ouverte par le programme."""

    dsk_path = None

    def fw_CAS_CATALOG(self):
        import cpcdisk
        amsdos = cpcdisk.charger()
        from cpc_dsk.core.adf import ADFDisk
        fs = amsdos.AmsdosFilesystem(ADFDisk.load(self.dsk_path))
        files = sorted(fs.list_files(), key=lambda f: f.field11)
        entries = []
        for f in files:
            base, ext = f.field11[:8], f.field11[8:]
            entries.append(f"{base}.{ext} {len(f.blocks):>3}K")
        lines = ["Drive A: user  0", ""]
        for i in range(0, len(entries), 2):
            lines.append("  ".join(entries[i:i + 2]))
        lines += ["", f"{fs.free_bytes() // 1024}K free"]
        left, right, top, bottom = getattr(self, "window", (0, 39, 0, 24))
        height = bottom - top + 1
        shown = lines[-height:]                   # le texte a défilé
        for k, text in enumerate(shown):
            r = top + k
            for c in range(left, right + 1):
                ch = text[c - left] if c - left < len(text) else " "
                self.screen[r][c] = ch
                self.codes[r][c] = ord(ch)
                self.attr[r][c] = (self.pen, self.paper)
        self._corrupt("af", "bc", "de", "hl")
        self._carry(True)


def press(cpc, key, after=1):
    cpc.frames(2, keys={key})
    cpc.frames(after)


# Les scènes : (fichier du README, image du site, préparation).  Chacune part
# du démarrage, sur la disquette de démonstration de la langue, avec le
# morceau ARCADE chargé (f1, f9).
KEY_CTRL, KEY_RIGHT, KEY_UP, KEY_TAB, KEY_F6 = 23, 1, 0, 68, 4


def load_song(cpc, name="ARCADE.SNG"):
    press(cpc, KEY_SONG)
    names = [n for n in cpc.files if n.endswith(".SNG")]
    cpc.chars = [0xF1] * names.index(name) + [13]        # flèche bas, RETURN
    press(cpc, KEY_LOAD)


def s_song(cpc):
    load_song(cpc)
    press(cpc, KEY_DOWN)
    press(cpc, KEY_SPACE)                                # le morceau, depuis 01
    cpc.frames(60)


def to_theme(cpc):
    load_song(cpc)
    press(cpc, KEY_MOTIF)
    cpc.frames(2, keys={KEY_CTRL, KEY_RIGHT})            # motif 2 : ARTHEME
    cpc.frames(2)


def s_split(cpc):
    to_theme(cpc)


def s_playing(cpc):
    to_theme(cpc)
    press(cpc, KEY_SPACE)
    cpc.frames(45)


def s_layered(cpc):
    load_song(cpc)
    press(cpc, KEY_MOTIF)                                # motif 1 : ARINTRO


def s_fx(cpc):
    """Le pas 0 de la voix C (ARPEGE 37) : TAB, puis le chiffre de l'effet."""
    to_theme(cpc)
    press(cpc, KEY_DOWN)
    press(cpc, KEY_DOWN)
    press(cpc, KEY_TAB)
    for _ in range(3):
        press(cpc, KEY_RIGHT)
    press(cpc, KEY_UP)                                   # 47 REPETE...
    press(cpc, KEY_DOWN)                                 # ... puis 37 ARPEGE


def s_instrument(cpc):
    load_song(cpc)
    press(cpc, KEY_INST)


def s_sounds(cpc):
    load_song(cpc)
    press(cpc, KEY_INST)
    press(cpc, KEY_F6)


def s_sampler(cpc):
    load_song(cpc, "STUDIO.SNG")                         # et sa banque STUDIO.SMP
    press(cpc, KEY_SAMPLE, after=3)
    for _ in range(4):                                   # sample 5 : SEQ16
        cpc.frames(2, keys={KEY_CTRL, KEY_RIGHT})
        cpc.frames(1)
    cpc.frames(2)


def s_disk(cpc):
    load_song(cpc)
    press(cpc, KEY_DISK, after=3)


SCENES = [
    ("01_song.png", "song.png", s_song),
    ("02_motif_voix_separees.png", "pattern-split.png", s_split),
    ("03_motif_en_lecture.png", "pattern-playing.png", s_playing),
    ("04_motif_son_compose.png", "pattern-layered.png", s_layered),
    ("05_effets_fx.png", "pattern-fx.png", s_fx),
    ("06_instrument.png", "instrument.png", s_instrument),
    ("07_sons_composes.png", "layered-sounds.png", s_sounds),
    ("08_sampler.png", "sampler.png", s_sampler),
    ("09_disque.png", "disk.png", s_disk),
]


def snapshots(lang, font):
    """Les captures du README (snapshots/, x4) et les images du site
    (docs/assets/img/<langue>/, x2)."""
    suffix = "" if lang == "fr" else "-" + lang
    dsk = os.path.join(ROOT, "build", "seq16-demo%s.dsk" % suffix)
    out = os.path.join(ROOT, "snapshots") if lang == "fr" else os.path.join(ROOT, "snapshots", lang)
    site = os.path.join(ROOT, "docs", "assets", "img", lang)
    for d in (out, site):
        os.makedirs(d, exist_ok=True)
    done = []
    for name, web, scene in SCENES:
        cpc = SnapCPC.from_build(dsk)
        cpc.dsk_path = dsk
        cpc.boot()
        cpc.use_disk(dsk)
        cpc.frames(1)
        scene(cpc)
        for folder, file, scale in ((out, name, SCALE), (site, web, SCALE // 2)):
            w, h, rgb = render(cpc, font, scale)
            path = os.path.join(folder, file)
            write_png(path, w, h, rgb)
            done.append(path)
    return done


def main():
    p = argparse.ArgumentParser(description="Captures d'écran de SEQ-16")
    p.add_argument("langues", nargs="*", default=["fr", "en", "es"])
    p.add_argument("--rom", help="OS6128.ROM (police du CPC)")
    a = p.parse_args()
    font = load_font(find_rom(a.rom))
    for lang in a.langues:
        for path in snapshots(lang, font):
            print("OK :", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    if cpcsim is None:
        raise SystemExit("paquet z80 absent (pip install z80)")
    main()
