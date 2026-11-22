"""gen_screen.py : l'écran de chargement de SEQ-16 (synthwave).

Mode 0 du CPC : 160 x 200 pixels (deux fois plus larges que hauts), 16
couleurs parmi les 27 de la palette.  Un écran par langue (le sous-titre).

    build/SEQ16-fr.SCR, -en, -es    la mémoire écran (#C000-#FFFF, 16 Ko),
                                    compressée (lz_pack : environ 2,5 Ko)
    src/loader_inks.asm             les 16 encres et la bordure (src/loader.asm)
    snapshots/ecran-chargement*.png l'aperçu (x4 en largeur, x2 en hauteur)

    python tools/gen_screen.py          écrit tout cela
    python tools/gen_screen.py --disks  et met le chargeur (build/loader.bin,
                                        assemblé par build.bat) et l'écran sur
                                        build/seq16-fr.dsk, -en, -es

Sur la disquette : SEQ16 (le chargeur, sans extension : RUN"SEQ16 le trouve
avant SEQ16.BIN), SEQ16.SCR (l'écran), SEQ16.BIN (le programme).
"""
import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

W, H = 160, 200
LV = (0, 128, 255)
LOADER_ADDR = 0xA400                       # voir src/loader.asm
SUBTITLES = {"fr": "SEQUENCEUR CHIPTUNE", "en": "CHIPTUNE SEQUENCER",
             "es": "SECUENCIADOR CHIPTUNE"}
# Les 16 encres (couleurs du firmware, 0 à 26) et la bordure
INKS = [0, 1, 4, 10, 8, 16, 15, 24, 26, 20, 2, 7, 3, 6, 23, 25]
#       0 noir 1 bleu nuit 2 violet 3 mauve 4 magenta 5 rose 6 orange
#       7 jaune 8 blanc 9 cyan 10 bleu 11 rose pâle 12 rouge sombre 13 rouge
#       14 bleu pastel 15 jaune pâle
BORDER = 0


def cpc_rgb(n):
    """Couleur n du firmware -> RGB (vert = n / 9, rouge = n / 3 mod 3, bleu = n mod 3)."""
    return (LV[(n // 3) % 3], LV[n // 9], LV[n % 3])


# --- polices --------------------------------------------------------------------
F3 = {                                     # 3 x 5 : le texte
    " ": ["...", "...", "...", "...", "..."],
    "A": [".#.", "#.#", "###", "#.#", "#.#"], "C": [".##", "#..", "#..", "#..", ".##"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."], "E": ["###", "#..", "##.", "#..", "###"],
    "H": ["#.#", "#.#", "###", "#.#", "#.#"], "I": ["###", ".#.", ".#.", ".#.", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."], "P": ["##.", "#.#", "##.", "#..", "#.."],
    "Q": [".#.", "#.#", "#.#", "##.", ".##"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["##.", "..#", ".#.", "#..", "###"], "6": [".##", "#..", "###", "#.#", "###"],
    "8": ["###", "#.#", "###", "#.#", "###"],
}
F7 = {                                     # 7 x 9 : le logo
    "S": [".#####.", "##...##", "##.....", ".####..", "...###.", ".....##", "##...##", "##...##", ".#####."],
    "E": ["#######", "##.....", "##.....", "######.", "##.....", "##.....", "##.....", "##.....", "#######"],
    "Q": [".#####.", "##...##", "##...##", "##...##", "##...##", "##.#.##", "##..###", "##...##", ".####.#"],
    "-": [".......", ".......", ".......", ".......", ".#####.", ".......", ".......", ".......", "......."],
    "1": ["...##..", "..###..", ".####..", "...##..", "...##..", "...##..", "...##..", "...##..", ".######"],
    "6": [".#####.", "##...##", "##.....", "######.", "##...##", "##...##", "##...##", "##...##", ".#####."],
}


class Img:
    def __init__(self, bg=0):
        self.p = [[bg] * W for _ in range(H)]

    def px(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.p[y][x] = c

    def rect(self, x, y, w, h, c):
        for j in range(y, y + h):
            for i in range(x, x + w):
                self.px(i, j, c)

    def text(self, s, x, y, c, shadow=None):
        for ch in s:
            g = F3[ch]
            for j, row in enumerate(g):
                for i, b in enumerate(row):
                    if b == "#":
                        if shadow is not None:
                            self.px(x + i + 1, y + j + 1, shadow)
                        self.px(x + i, y + j, c)
            x += len(g[0]) + 1

    def centered(self, s, y, c, shadow=None):
        w = sum(len(F3[ch][0]) + 1 for ch in s) - 1
        self.text(s, (W - w) // 2, y, c, shadow)

    def logo(self, y, grad, sx=2, sy=3, shadow=None):
        w = sum((len(F7[c][0]) + 1) * sx for c in "SEQ-16") - sx
        for layer in ("shadow", "face"):
            if layer == "shadow" and shadow is None:
                continue
            x = (W - w) // 2
            for ch in "SEQ-16":
                g = F7[ch]
                for j, row in enumerate(g):
                    c = grad[min(j * len(grad) // len(g), len(grad) - 1)]
                    for i, b in enumerate(row):
                        if b != "#":
                            continue
                        for dj in range(sy):
                            for di in range(sx):
                                if layer == "shadow":
                                    self.px(x + i * sx + di + 2, y + j * sy + dj + 2, shadow)
                                else:
                                    self.px(x + i * sx + di, y + j * sy + dj, c)
                x += (len(g[0]) + 1) * sx


def draw(lang):
    """L'écran synthwave : ciel en bandes, soleil rayé, montagnes, grille."""
    img = Img(0)
    sky = [1, 1, 1, 2, 2, 3, 3, 4]
    for j in range(120):
        band = j * len(sky) // 120
        c = sky[band]
        if j % 8 == 7 and band < len(sky) - 1:     # tramage entre deux bandes
            c = sky[band + 1]
        img.rect(0, j, W, 1, c)
    for (sx, sy) in [(9, 8), (27, 30), (52, 12), (118, 9), (144, 25), (133, 44), (16, 52),
                     (74, 4), (101, 36), (150, 6)]:
        img.px(sx, sy, 8)
    cx, cy, r = 80, 96, 34                         # le soleil, rayé en bas
    sun = [7, 7, 15, 6, 6, 5, 13, 4]
    for y in range(cy - r, cy + 1):
        dy = cy - y
        half = int(math.sqrt(max(0, r * r - dy * dy))) // 2
        band = (y - (cy - r)) * len(sun) // (r + 1)
        if y > cy - r // 2 and (cy - y) % 5 in (0, 1):
            continue
        img.rect(cx - half, y, 2 * half, 1, sun[min(band, len(sun) - 1)])
    for x in range(W):                             # montagnes (deux plans)
        h1 = 18 + int(9 * math.sin(x * 0.09) + 6 * math.sin(x * 0.23 + 1))
        h2 = 10 + int(5 * math.sin(x * 0.15 + 2))
        img.rect(x, 120 - h1, 1, h1, 2)
        img.rect(x, 120 - h2, 1, h2, 1)
    img.rect(0, 120, W, 1, 5)                      # horizon
    for k in range(1, 12):                         # grille en perspective
        y = 120 + int(80 * (k / 11) ** 1.8)
        if y < H:
            img.rect(0, y, W, 1, 4 if k % 2 else 3)
    for k in range(-12, 13):
        for y in range(121, H):
            img.px(int(80 + k * (4 + 30 * (y - 120) / 80)), y, 4)
    img.logo(14, [8, 9, 9, 9, 14, 10, 10, 10, 2], shadow=0)
    img.centered(SUBTITLES[lang], 46, 5)
    img.centered("AMSTRAD CPC 6128", 186, 8, shadow=0)
    return img.p


# --- la mémoire écran du mode 0 ------------------------------------------------------
def pack_pair(p0, p1):
    """Deux pixels du mode 0 -> l'octet de la mémoire écran.
    bit 7 = p0 bit 0, 6 = p1 bit 0, 5 = p0 bit 2, 4 = p1 bit 2,
    bit 3 = p0 bit 1, 2 = p1 bit 1, 1 = p0 bit 3, 0 = p1 bit 3."""
    b = 0
    for bit, (src, sh) in enumerate([(p1, 3), (p0, 3), (p1, 1), (p0, 1),
                                     (p1, 2), (p0, 2), (p1, 0), (p0, 0)]):
        b |= ((src >> sh) & 1) << bit
    return b


def unpack_pair(b):
    p0 = ((b >> 7) & 1) | ((b >> 3) & 1) << 1 | ((b >> 5) & 1) << 2 | ((b >> 1) & 1) << 3
    p1 = ((b >> 6) & 1) | ((b >> 2) & 1) << 1 | ((b >> 4) & 1) << 2 | (b & 1) << 3
    return p0, p1


def screen_address(y, xbyte):
    """Décalage dans #C000-#FFFF de l'octet xbyte (0-79) de la ligne y."""
    return (y & 7) * 0x800 + (y >> 3) * 80 + xbyte


def to_scr(img):
    scr = bytearray(0x4000)
    for y in range(H):
        for xb in range(80):
            scr[screen_address(y, xb)] = pack_pair(img[y][2 * xb], img[y][2 * xb + 1])
    return bytes(scr)


def from_scr(scr):
    img = [[0] * W for _ in range(H)]
    for y in range(H):
        for xb in range(80):
            img[y][2 * xb], img[y][2 * xb + 1] = unpack_pair(scr[screen_address(y, xb)])
    return img


# --- compression (décodée par src/loader.asm, ld_unlz) ------------------------------
# Une suite de jetons, jusqu'à 16 384 octets écrits :
#   c = 0 à 127    : c + 1 octets bruts suivent
#   c = 128 à 255  : copie de c - 125 octets (3 à 130), pris d (2 octets, poids
#                    faible d'abord) octets en arrière dans ce qui est déjà écrit
LZ_MIN, LZ_MAX, LZ_WINDOW = 3, 130, 4096


def lz_pack(data):
    out = bytearray()
    lit = bytearray()
    heads = {}                                     # 3 octets -> positions

    def flush():
        nonlocal lit
        while lit:
            out.append(min(len(lit), 128) - 1)
            out.extend(lit[:128])
            lit = lit[128:]

    def add(pos):
        if pos + 3 <= len(data):
            heads.setdefault(data[pos:pos + 3], []).append(pos)
    i = 0
    while i < len(data):
        best, dist = 0, 0
        for j in reversed(heads.get(data[i:i + 3], [])[-64:]):
            if i - j > LZ_WINDOW:
                break
            n = 0
            while i + n < len(data) and n < LZ_MAX and data[j + n] == data[i + n]:
                n += 1
            if n > best:
                best, dist = n, i - j
        if best >= LZ_MIN:
            flush()
            out.append(128 + best - LZ_MIN)
            out += dist.to_bytes(2, "little")
            for k in range(best):
                add(i + k)
            i += best
        else:
            lit.append(data[i])
            add(i)
            i += 1
    flush()
    return bytes(out)


def lz_unpack(packed, size=0x4000):
    out = bytearray()
    i = 0
    while len(out) < size:
        c = packed[i]
        i += 1
        if c < 128:
            out += packed[i:i + c + 1]
            i += c + 1
        else:
            d = packed[i] | packed[i + 1] << 8
            i += 2
            for _ in range(c - 128 + LZ_MIN):
                out.append(out[-d])
    return bytes(out)


# --- fichiers ------------------------------------------------------------------------
def write_png(path, img, sx=4, sy=2):
    rows = []
    for y in range(H):
        line = b"".join(bytes(cpc_rgb(INKS[c])) * sx for c in img[y])
        rows += [b"\x00" + line] * sy

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W * sx, H * sy, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(data)


def inks_asm():
    return "\n".join([
        "; Fichier généré par tools/gen_screen.py - ne pas modifier à la main.",
        "; Les 16 encres de l'écran de chargement (couleurs du firmware), puis la bordure.",
        "loader_inks:",
        "        db " + ",".join("%2d" % n for n in INKS),
        "        db %d" % BORDER, ""])


def write_all():
    assert len(INKS) == 16 and all(0 <= n <= 26 for n in INKS)
    out = {}
    for lang in SUBTITLES:
        img = draw(lang)
        scr = to_scr(img)
        assert from_scr(scr) == img
        packed = lz_pack(scr)
        assert lz_unpack(packed) == scr
        path = os.path.join(ROOT, "build", "SEQ16-%s.SCR" % lang)
        with open(path, "wb") as fh:
            fh.write(packed)
        name = "ecran-chargement.png" if lang == "fr" else "ecran-chargement-%s.png" % lang
        write_png(os.path.join(ROOT, "snapshots", name), img)
        out[lang] = packed
    with open(os.path.join(ROOT, "src", "loader_inks.asm"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(inks_asm())
    return out


def add_to_disks(screens):
    """Le chargeur (SEQ16) et l'écran (SEQ16.SCR) sur les disquettes du programme."""
    import amsdsk
    with open(os.path.join(ROOT, "build", "loader.bin"), "rb") as fh:
        loader = fh.read()
    for lang, scr in screens.items():
        dsk = os.path.join(ROOT, "build", "seq16-%s.dsk" % lang)
        amsdsk.add_file(dsk, "SEQ16", loader, load=LOADER_ADDR, exec_addr=LOADER_ADDR)
        amsdsk.add_file(dsk, "SEQ16.SCR", scr, load=0xC000)
        print("%s : SEQ16 (chargeur) et SEQ16.SCR ajoutés" % dsk)


if __name__ == "__main__":
    screens = write_all()
    print("écrans : build/SEQ16-fr.SCR, -en, -es ; src/loader_inks.asm ; snapshots/ecran-chargement*.png")
    if "--disks" in sys.argv:
        add_to_disks(screens)
