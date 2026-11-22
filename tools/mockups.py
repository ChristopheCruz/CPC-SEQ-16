"""mockups.py : maquettes des écrans de la v1.0 (voir PLAN.md).

Dessine des écrans CPC (mode 1, 40 x 25, quatre encres) avec la police de
la ROM du CPC 6128, comme tools/snapshots.py, mais sans faire tourner le
programme : chaque écran est composé à la main, caractère par caractère.
Sert à valider l'interface avant de l'écrire en assembleur.

    python tools/mockups.py                  # écrit plan/img/*.png
    python tools/mockups.py --out dossier

La ROM (OS6128.ROM) n'est pas dans le dépôt : variable CPC_ROM, ou le
WinAPE de CPC-DISK voisin (cpc_tools/WinAPE20B2/ROM/OS6128.ROM).
"""
import argparse
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

INKS = [(0, 0, 127), (255, 255, 0), (0, 255, 255), (255, 127, 0)]
SCALE, BORDER_PX, MATRIX = 4, 8, 0x3800
BLUE, YELLOW, CYAN, ORANGE = 0, 1, 2, 3


def find_rom():
    cands = [os.environ.get('CPC_ROM')]
    up = ROOT
    for _ in range(6):
        up = os.path.dirname(up)
        for name in ('CPC-DISK', 'AmstradCPC'):
            cands.append(os.path.join(up, name, 'cpc_tools', 'WinAPE20B2', 'ROM', 'OS6128.ROM'))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    raise SystemExit('OS6128.ROM introuvable : variable CPC_ROM')


FONT = None


def load_font():
    global FONT
    with open(find_rom(), 'rb') as fh:
        FONT = fh.read()[MATRIX:MATRIX + 2048]


class Screen:
    def __init__(self):
        self.codes = [[32] * 40 for _ in range(25)]
        self.attr = [[(CYAN, BLUE)] * 40 for _ in range(25)]

    def put(self, r, c, text, pen=CYAN, paper=BLUE):
        for k, ch in enumerate(text):
            if 0 <= c + k < 40:
                self.codes[r][c + k] = ch if isinstance(ch, int) else ord(ch)
                self.attr[r][c + k] = (pen, paper)

    def code(self, r, c, code, pen=CYAN, paper=BLUE, n=1):
        for k in range(n):
            self.codes[r][c + k] = code
            self.attr[r][c + k] = (pen, paper)

    def png(self, path):
        w = (40 * 8 + 2 * BORDER_PX) * SCALE
        h = (25 * 8 + 2 * BORDER_PX) * SCALE
        border_row = bytes(INKS[0]) * w
        lines = [border_row] * (BORDER_PX * SCALE)
        side = bytes(INKS[0]) * (BORDER_PX * SCALE)
        for r in range(25):
            for y in range(8):
                line = bytearray(side)
                for c in range(40):
                    pen, paper = self.attr[r][c]
                    bits = FONT[self.codes[r][c] * 8 + y]
                    fg, bg = bytes(INKS[pen]), bytes(INKS[paper])
                    for x in range(8):
                        line += (fg if bits & (0x80 >> x) else bg) * SCALE
                line += side
                lines.extend([bytes(line)] * SCALE)
        lines.extend([border_row] * (BORDER_PX * SCALE))
        rgb = b''.join(lines)
        raw = b''.join(b'\x00' + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))

        def chunk(t, d):
            return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
        with open(path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                    + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))

ON, DOT, HOLD, CUT = 233, 144, 154, 203        # ■ · ─ X
TL, TR, BL, BR, H, V = 150, 156, 147, 153, 154, 149
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Motif d'exemple : n = (note, octave, instr) / '-' = arrêt / None = vide
def lane(spec):
    out = []
    for tok in spec.split():
        if tok == '.':
            out.append(None)
        elif tok == '-':
            out.append('-')
        else:
            n, o, i = tok.split(':')
            out.append((n, int(o), int(i)))
    return out

A = lane('C:2:2 . C:2:2 C:3:2  . C:2:2 - .  D#:2:2 . D#:2:2 D#:3:2  . F:2:2 G:2:2 -')
B = lane('C:4:1 . . D#:4:1  . . G:4:1 .  F:4:1 . D#:4:1 .  D:4:1 . - .')
C = lane('. . G:3:4 .  . . G:3:4 .  . . G#:3:4 .  . . G:3:4 .')
N = lane('BD:1:6 . BR:5:5 BR:5:5  SN:1:3 . BR:5:5 BR:5:5  BD:1:6 . BR:5:5 BD:1:6  SN:1:3 . BR:5:5 SN:1:3')
INSTR = {1: 'LEAD', 2: 'BASS', 3: 'SNARE', 4: 'PAD', 5: 'HIHAT', 6: 'KICK'}


TABS = ['MOTIF', 'SONG', 'INST', 'SAMPLE', 'DISQUE']


def tabs(s, active=0):
    """Barre des 5 panneaux : SEQ16 1MOTIF 2SONG 3INST 4SAMPLE 5DISQUE (40 col.)."""
    s.put(0, 0, 'SEQ16', BLUE, YELLOW)
    c = 6
    for k, name in enumerate(TABS):
        if k == active:
            s.put(0, c - 1 if k else c, ' ' if k else '', BLUE, ORANGE)
            s.put(0, c, str(k + 1) + name, BLUE, ORANGE)
        else:
            s.put(0, c, str(k + 1), ORANGE)
            s.put(0, c + 1, name, CYAN)
        c += len(name) + 2


def status(s, mode='VOIX SEPAREES', playing=False):
    s.put(1, 0, 'MOTIF:', CYAN); s.put(1, 6, '01', ORANGE)
    s.put(1, 9, mode, ORANGE)
    s.put(1, 24, 'BPM:', CYAN); s.put(1, 28, '125', ORANGE)
    if playing:
        s.code(1, 32, 246, YELLOW); s.put(1, 33, 'LECTURE', YELLOW)
    else:
        s.code(1, 32, 233, CYAN); s.put(1, 33, 'ARRET', CYAN)


def brush(s, r):
    s.put(r, 0, 'PINCEAU', CYAN); s.code(r, 8, 237, ORANGE)
    s.put(r, 10, 'D#4', ORANGE); s.put(r, 14, 'INS 01 LEAD', ORANGE)
    s.put(r, 26, 'COPY', ORANGE); s.put(r, 31, 'PRENDRE', CYAN)


def box(s, r0, r1, title):
    s.code(r0, 0, TL, CYAN); s.code(r0, 1, H, CYAN, n=38); s.code(r0, 39, TR, CYAN)
    for r in range(r0 + 1, r1):
        s.code(r, 0, V, CYAN); s.code(r, 39, V, CYAN)
    s.code(r1, 0, BL, CYAN); s.code(r1, 1, H, CYAN, n=38); s.code(r1, 39, BR, CYAN)
    s.put(r0, 2, ' ' + title + ' ', YELLOW)


def keyboard(s, r, c, octave0, hl=None):
    """Clavier de 2 octaves sur 2 lignes (28 colonnes). hl = (note, octave)."""
    whites = [0, 2, 4, 5, 7, 9, 11]
    letters = 'CDEFGAB'
    hl_idx = None
    if hl:
        hl_idx = NAMES.index(hl[0]) + 12 * (hl[1] - octave0)
    # Chaque blanche fait 2 colonnes : [lettre][séparateur].  La noire est un
    # bloc plein posé sur le séparateur, donc centrée entre les deux blanches.
    for o in range(2):
        for k, semi in enumerate(whites):
            col = c + 14 * o + 2 * k
            paper = YELLOW if hl_idx == semi + 12 * o else CYAN
            last = (o == 1 and k == 6)
            s.put(r + 1, col, letters[k], BLUE, paper)
            s.code(r + 1, col + 1, 32 if last else 149, BLUE, CYAN if not last else paper)
            s.code(r, col, 32, BLUE, paper)
            if semi in (0, 2, 5, 7, 9):            # une noire à droite de cette blanche
                pen = YELLOW if hl_idx == semi + 1 + 12 * o else BLUE
                s.code(r, col + 1, 143, pen, CYAN)
            else:
                s.code(r, col + 1, 32 if last else 149, BLUE, CYAN if not last else paper)
    s.put(r, c + 29, 'OCT', CYAN); s.put(r + 1, c + 29, '%d-%d' % (octave0, octave0 + 1), ORANGE)


def fields(s, r, cell, lane_name, noise=False, son=None):
    if cell is None or cell == '-':
        s.put(r, 2, 'NOTE:', CYAN)
        s.put(r, 7, '---' if cell is None else 'ARRET', ORANGE)
        s.put(r, 16, 'PINCEAU: C 2 INS 02', CYAN)
        return
    n, o, i = cell
    s.put(r, 2, 'NOTE:', CYAN)
    if noise:
        s.put(r, 7, 'BRUIT %02d' % o, ORANGE)
    else:
        s.put(r, 7, '%-2s%d' % (n, o), ORANGE)
    if son:
        s.put(r, 13, 'SON:', CYAN); s.put(r, 17, son, ORANGE)
    else:
        s.put(r, 13, 'INS:', CYAN); s.put(r, 17, '%02d %-5s' % (i, INSTR[i]), ORANGE)
    s.put(r, 27, 'VOL:', CYAN); s.put(r, 31, 'F', ORANGE)
    s.put(r, 33, 'FX:', CYAN); s.put(r, 36, '--', ORANGE)


def step_col(st):
    return 5 + 2 * st + st // 4


def grid(s, r0, lanes, cur=None, play=None, gap=2):
    s.put(r0, 0, 'PAS', CYAN)
    for st in range(16):
        c = step_col(st)
        pen = YELLOW if st % 4 == 0 else CYAN
        if play == st:
            s.put(r0, c, '%X' % st, BLUE, ORANGE)
            s.code(r0, c + 1, 32, BLUE, ORANGE)
        else:
            s.put(r0, c, '%X' % st, pen)
    for li, (label, cells, noise) in enumerate(lanes):
        r = r0 + 1 + gap * li
        s.put(r, 1, label, YELLOW)
        # durée : un trait relie une note à son arrêt (même voix, que des vides entre)
        tail = [False] * 16          # un trait part de la droite de ce pas
        for st, cell in enumerate(cells):
            if isinstance(cell, tuple):
                k = st + 1
                while k < 16 and cells[k] is None:
                    k += 1
                if k < 16 and cells[k] == '-':
                    for j in range(st, k):
                        tail[j] = True
        pen = ORANGE if noise else CYAN
        for st, cell in enumerate(cells):
            c = step_col(st)
            paper = BLUE
            if cell is None:
                code = HOLD if (st and tail[st - 1]) else DOT
                cpen = pen if code == HOLD else (YELLOW if st % 4 == 0 else CYAN)
            elif cell == '-':
                code, cpen = CUT, ORANGE
            else:
                code, cpen = ON, pen
            if play == st and code == ON:
                code, cpen = 143, YELLOW          # la note jouée s'allume
            if cur == (li, st):
                cpen = YELLOW
            s.code(r, c, code, cpen, paper)
            if tail[st]:
                s.code(r, c + 1, HOLD, pen, BLUE)
                if st % 4 == 3 and st < 15:
                    s.code(r, c + 2, HOLD, pen, BLUE)
            if cur == (li, st):
                s.code(r, c + 1, 247, YELLOW)     # ◄ montre la case
                s.put(r0, c, '%X' % st, BLUE, YELLOW)
                s.put(r, 1, label, BLUE, YELLOW)


def help_rows(s, r):
    s.code(r, 0, 242, ORANGE); s.code(r, 1, 243, ORANGE); s.code(r, 2, 240, ORANGE); s.code(r, 3, 241, ORANGE)
    s.put(r, 5, 'PAS/VOIX', CYAN); s.put(r, 14, 'ENTER', ORANGE); s.put(r, 20, 'ON/OFF', CYAN)
    s.put(r, 27, 'CLR', ORANGE); s.put(r, 31, 'ARRET', CYAN)
    s.put(r + 1, 0, 'PIANO', ORANGE); s.put(r + 1, 6, 'NOTE+ON', CYAN); s.put(r + 1, 14, 'TAB', ORANGE)
    s.put(r + 1, 18, 'EDITER NOTE', CYAN); s.put(r + 1, 30, 'ESPACE', ORANGE); s.code(r + 1, 37, 246, CYAN)
    s.put(r + 2, 0, 'SHIFT', ORANGE); s.code(r + 2, 6, 240, ORANGE); s.code(r + 2, 7, 241, ORANGE)
    s.put(r + 2, 9, 'OCT', CYAN); s.code(r + 2, 13, 242, ORANGE); s.code(r + 2, 14, 243, ORANGE)
    s.put(r + 2, 16, 'INSTR', CYAN)
    s.put(r + 2, 22, 'CTRL', ORANGE); s.code(r + 2, 27, 240, ORANGE); s.code(r + 2, 28, 241, ORANGE)
    s.put(r + 2, 30, 'BPM', CYAN); s.code(r + 2, 34, 242, ORANGE); s.code(r + 2, 35, 243, ORANGE)
    s.put(r + 2, 37, 'MOT', CYAN)


LANES = [('A', A, False), ('B', B, False), ('C', C, False), ('N', N, True)]


def screen_edit(path, cur=(1, 3), play=None, edit_panel=False):
    s = Screen()
    tabs(s); status(s, playing=play is not None)
    li, st = cur
    cell = LANES[li][1][st]
    box(s, 3, 7, 'PAS %X %c VOIX %s ' % (st, 154, LANES[li][0]))
    hl = (cell[0], cell[1]) if isinstance(cell, tuple) and not LANES[li][2] else None
    keyboard(s, 4, 2, 3, hl)
    fields(s, 6, cell, LANES[li][0], noise=LANES[li][2])
    if edit_panel:
        s.attr[6][7] = (BLUE, YELLOW); s.attr[6][8] = (BLUE, YELLOW); s.attr[6][9] = (BLUE, YELLOW)
        s.put(3, 26, ' EDITION ', BLUE, YELLOW)
    grid(s, 9, LANES, cur=None if edit_panel else cur, play=play)
    if edit_panel:
        c = step_col(st)
        s.attr[10 + 2 * li][c] = (YELLOW, BLUE)
    brush(s, 18)
    help_rows(s, 21)
    s.png(path)


def screen_layered(path):
    s = Screen()
    tabs(s); status(s, mode='SON COMPOSE')
    son = lane('C:2:2 . C:3:2 .  C:2:2 . - C:2:2  D#:2:2 . D#:3:2 .  F:2:2 . G:2:2 .')
    box(s, 3, 7, 'PAS 2 %c SON COMPOSE ' % 154)
    keyboard(s, 4, 2, 2, ('C', 3))
    fields(s, 6, ('C', 3, 2), 'S', son='S2 4 VOIX')
    grid(s, 9, [('SON', son, False)], cur=(0, 2))
    # les 4 couches du son, sous la grille
    s.put(12, 0, 'COUCHES DU SON S2', YELLOW)
    s.put(13, 2, 'VOIX  INSTR       DECALAGE  VOL', CYAN)
    rows = [('A', '02 BASS ', '+0', 'F'), ('B', '01 LEAD ', '+12', 'C'),
            ('C', '04 PAD  ', '+7', 'A'), ('N', '06 KICK ', 'BR 01', 'F')]
    for k, (v, ins, tr, vol) in enumerate(rows):
        s.put(14 + k, 3, v, YELLOW); s.put(14 + k, 8, ins, ORANGE)
        s.put(14 + k, 20, tr, ORANGE); s.put(14 + k, 30, vol, ORANGE)
    help_rows(s, 21)
    s.png(path)


def screen_variant_b(path, cur=(1, 3)):
    """Variante : une seule ligne d'info, et le nom des notes sous chaque voix."""
    s = Screen()
    tabs(s); status(s)
    li, st = cur
    cell = LANES[li][1][st]
    s.code(3, 0, H, CYAN, n=40)
    s.put(3, 1, ' PAS %X VOIX %s ' % (st, LANES[li][0]), YELLOW)
    fields(s, 4, cell, LANES[li][0])
    s.code(5, 0, H, CYAN, n=40)
    grid(s, 7, LANES, cur=cur, gap=3)
    for li2, (label, cells, noise) in enumerate(LANES):
        r = 7 + 1 + 3 * li2 + 1
        for st2, c in enumerate(cells):
            if isinstance(c, tuple):
                txt = ('%-2s' % c[0]) if not noise else c[0][:2]
                pen = YELLOW if st2 % 2 == 0 else CYAN
                if noise:
                    pen = ORANGE if st2 % 2 == 0 else YELLOW
                s.put(r, step_col(st2), txt, pen)
    help_rows(s, 21)
    s.png(path)


def rhythm(cells_by_lane):
    """Aperçu d'un motif sur 16 caractères : un pas avec au moins une note = ■."""
    out = []
    for st in range(16):
        on = any(isinstance(l[st], tuple) for l in cells_by_lane)
        out.append(ON if on else DOT)
    return out


def screen_song(path, cur_row=5, cur_field=1, play_row=3):
    s = Screen()
    tabs(s, 1)
    s.put(1, 0, 'SONG:', CYAN); s.put(1, 5, 'NUIT', ORANGE)
    s.put(1, 14, 'BPM:', CYAN); s.put(1, 18, '125', ORANGE)
    s.code(1, 23, 246, YELLOW); s.put(1, 24, 'LECTURE SONG', YELLOW)
    s.put(3, 0, 'POS MOTIF        REP TR. APERCU', CYAN)
    # motifs d'exemple (aperçus fabriqués à partir du motif des maquettes)
    full = rhythm([A, B, C, N])
    drums = rhythm([N])
    bass = rhythm([A, N])
    intro = [ON if st % 4 == 0 else DOT for st in range(16)]
    rows = [
        (1, 'INTRO1', 1, 0, intro), (2, 'KICKS', 2, 0, drums), (3, 'BASSE1', 2, 0, bass),
        (4, 'NUIT-A', 4, 0, full), (5, 'NUIT-B', 2, 0, full), (4, 'NUIT-A', 2, 5, full),
        (6, 'BREAK', 1, 0, drums), (4, 'NUIT-A', 4, 0, full), (7, 'FIN', 1, 0, intro),
    ]
    loop = 3
    for k, (pat, name, rep, tr, prev) in enumerate(rows):
        r = 4 + k
        pen = CYAN
        s.put(r, 0, '%02d' % k, YELLOW if k == loop else CYAN)
        if k == loop:
            s.code(r, 2, 240, YELLOW)                   # ↑ début de la boucle
        if k == play_row:
            s.code(r, 2, 246, ORANGE)                   # ► en cours
        vals = [('%02d' % pat, 4), (name, 7), ('x%d' % rep, 17), ('%+d' % tr if tr else ' 0', 21)]
        for f, (txt, col) in enumerate(vals):
            p, q = (ORANGE, BLUE)
            if k == cur_row:
                p = YELLOW
                if f == cur_field or (cur_field == 1 and f == 0):
                    p, q = BLUE, YELLOW
            s.put(r, col, txt, p, q)
        for st, g in enumerate(prev):
            col = 24 + st
            pc = (YELLOW if g == ON else CYAN) if k == play_row else (CYAN if g == ON else (YELLOW if st % 4 == 0 else CYAN))
            if k == play_row and st == 9:
                s.code(r, col, 143, YELLOW)
            else:
                s.code(r, col, g, pc)
    s.put(4 + len(rows), 0, '%02d' % len(rows), CYAN)
    s.put(4 + len(rows), 4, '-- FIN : RETOUR EN 03 --', CYAN)
    # mixage, déplacé de l'ancien écran Disque : il appartient au morceau
    s.put(15, 0, 'MIXAGE', YELLOW)
    for k, (v, vol) in enumerate([('A', 'F'), ('B', 'C'), ('C', 'A'), ('N', 'F')]):
        s.put(15, 8 + 8 * k, v, YELLOW); s.put(15, 10 + 8 * k, vol, ORANGE)
        s.code(15, 12 + 8 * k, 143, CYAN, n=max(1, round(int(vol, 16) * 4 / 15)))
    s.put(17, 0, 'DUREE', CYAN); s.put(17, 6, '19 MESURES  0:36', ORANGE)
    s.put(17, 24, 'POSITIONS', CYAN); s.put(17, 34, '09/64', ORANGE)
    # aide
    s.code(21, 0, 240, ORANGE); s.code(21, 1, 241, ORANGE); s.put(21, 3, 'POSITION', CYAN)
    s.code(21, 12, 242, ORANGE); s.code(21, 13, 243, ORANGE); s.put(21, 15, 'CHAMP', CYAN)
    s.put(21, 21, 'SHIFT', ORANGE); s.code(21, 27, 240, ORANGE); s.code(21, 28, 241, ORANGE)
    s.put(21, 30, 'VALEUR', CYAN)
    s.put(22, 0, 'ENTER', ORANGE); s.put(22, 6, 'INSERER', CYAN); s.put(22, 14, 'DEL', ORANGE)
    s.put(22, 18, 'OTER', CYAN); s.put(22, 23, 'COPY', ORANGE); s.put(22, 28, 'DOUBLER', CYAN)
    s.put(23, 0, 'B', ORANGE); s.put(23, 2, 'BOUCLE ICI', CYAN); s.put(23, 13, 'ESPACE', ORANGE)
    s.put(23, 20, 'LIRE DEPUIS ICI', CYAN)
    s.put(24, 0, 'f8', ORANGE); s.put(24, 3, 'SAUVER .SNG', CYAN); s.put(24, 16, 'f9', ORANGE)
    s.put(24, 19, 'CHARGER .SNG', CYAN)
    s.png(path)


def screen_disk(path):
    s = Screen()
    tabs(s, 4)
    s.put(1, 0, 'DISQUE A:', CYAN); s.put(1, 10, '96K LIBRES', ORANGE)
    s.put(1, 22, '31 FICHIERS', ORANGE)
    # filtre par type
    filt = ['TOUT', 'SNG', 'PAT', 'INS', 'SMP']
    c = 0
    for k, f in enumerate(filt):
        if k == 0:
            s.put(3, c, ' ' + f + ' ', BLUE, YELLOW)
        else:
            s.put(3, c, ' ' + f + ' ', CYAN)
        c += len(f) + 3
    s.put(3, 30, 'TAB TYPE', ORANGE)
    files = ['NUIT    .SNG', 'DEMO    .SNG', 'ACIDLN1 .PAT', 'TECHNO1 .PAT', 'FUNK2   .PAT',
             'REGGAE1 .PAT', 'INTRO1  .PAT', 'BREAK   .PAT', 'USINE   .INS', 'BASSES  .INS',
             'LEADS   .INS', 'NAPPES  .INS', 'BATTERIE.INS', 'CHIPTUNE.INS', 'DRUMS   .SMP',
             'VOIX    .SMP', 'PERCUS  .SMP', 'MOTS    .SMP', 'BASSES  .SMP', 'EFFETS  .SMP']
    color = {'SNG': YELLOW, 'PAT': CYAN, 'INS': ORANGE, 'SMP': CYAN}
    sel = 3
    for k, f in enumerate(files):
        r, col = 5 + k % 10, (k // 10) * 14
        base, ext = f.split('.')
        if k == sel:
            s.put(r, col, base.rstrip().ljust(8) + '.' + ext, BLUE, YELLOW)
        else:
            s.put(r, col, base, CYAN if ext != 'SNG' else YELLOW)
            s.put(r, col + 8, '.' + ext, color[ext])
    s.put(5, 28, '1/2', ORANGE); s.code(6, 28, 241, ORANGE)
    # fiche du fichier choisi
    s.code(16, 0, H, CYAN, n=40)
    s.put(16, 1, ' TECHNO1.PAT ', YELLOW)
    s.put(17, 0, 'MOTIF', CYAN); s.put(17, 6, '1K', ORANGE); s.put(17, 10, 'VOIX SEPAREES', ORANGE)
    s.put(17, 25, 'BPM', CYAN); s.put(17, 29, '130', ORANGE)
    s.put(18, 0, 'ENTER', ORANGE); s.put(18, 6, 'LE CHARGE DANS', CYAN); s.put(18, 21, '1MOTIF', BLUE, ORANGE)
    s.put(18, 28, '(MOTIF 01)', CYAN)
    # actions
    s.put(21, 0, 'ENTER', ORANGE); s.put(21, 6, 'CHARGER', CYAN); s.put(21, 15, 'DEL', ORANGE)
    s.put(21, 19, 'EFFACER', CYAN); s.put(21, 28, 'A/B', ORANGE); s.put(21, 32, 'LECTEUR', CYAN)
    s.put(22, 0, 'f8', ORANGE); s.put(22, 3, 'SAUVER TOUT : NOM.SNG + NOM.SMP', CYAN)
    s.put(23, 0, 'COPY', ORANGE); s.put(23, 5, 'RENOMMER', CYAN)
    s.png(path)


def screen_save_prompt(path):
    """Le dialogue de sauvegarde, identique dans tous les panneaux (ici f1)."""
    s = Screen()
    tabs(s, 0); status(s)
    li, st = (1, 3)
    cell = LANES[li][1][st]
    box(s, 3, 7, 'PAS %X %c VOIX %s ' % (st, 154, LANES[li][0]))
    keyboard(s, 4, 2, 3, (cell[0], cell[1]))
    fields(s, 6, cell, 'B')
    grid(s, 9, LANES, cur=(li, st))
    # dialogue en bas, à la place de l'aide
    s.code(19, 0, H, ORANGE, n=40)
    s.put(19, 1, ' f8 SAUVER LE MOTIF 01 ', ORANGE)
    s.put(20, 0, 'NOM :', CYAN); s.put(20, 6, 'NUIT-A', YELLOW); s.code(20, 12, 143, YELLOW)
    s.put(20, 14, '.PAT', CYAN)
    s.put(21, 0, 'IL EXISTE DEJA : ENTER REMPLACE', ORANGE)
    s.put(23, 0, 'ENTER', ORANGE); s.put(23, 6, 'VALIDER', CYAN); s.put(23, 15, 'ESC', ORANGE)
    s.put(23, 19, 'ANNULER', CYAN); s.put(23, 28, 'f9', ORANGE); s.put(23, 31, 'CHARGER', CYAN)
    s.png(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default=os.path.join(ROOT, 'plan', 'img'))
    OUT = ap.parse_args().out
    os.makedirs(OUT, exist_ok=True)
    load_font()
    screen_song(OUT + '/6_song.png')
    screen_disk(OUT + '/7_disque.png')
    screen_save_prompt(OUT + '/8_sauver.png')
    screen_edit(OUT + '/1_edition.png')
    screen_edit(OUT + '/2_lecture.png', cur=(1, 3), play=6)
    screen_edit(OUT + '/3_edition_note.png', cur=(1, 3), edit_panel=True)
    screen_layered(OUT + '/4_son_compose.png')
    screen_variant_b(OUT + '/5_variante_b.png')
    print('maquettes :', OUT)


if __name__ == '__main__':
    main()
