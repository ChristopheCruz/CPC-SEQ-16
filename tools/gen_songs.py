"""gen_songs.py : des morceaux de test complets (.SNG), avec leurs motifs
(.PAT) et leurs instruments (.INS).

Chaque morceau est écrit avec le petit langage de gen_patterns.py (R, L, G)
et passe les mêmes vérifications musicales (gamme, tessiture, frottements,
notes tenues).  Les motifs jouent de vraies doubles croches : charleston
sur les 16 pas, basses et lignes syncopées.

    songs/NOM.SNG            le morceau : instruments, sons composés, ses
                             motifs (les autres sont vides), banque de
                             samples associée (bloc v2)
    songs/NOM.INS            ses instruments (usine + ses 4 instruments à
                             lui, dans les places libres USER1 à USER4)
    songs/pat/*.PAT          tous les motifs, un fichier chacun
    songs/LISTE.md           ce que contient chaque morceau, quoi tester
    build/seq16-songs.dsk    SEQ16.BIN, DRUMS.SMP et tout ce qui précède

    python tools/gen_songs.py

Les .SNG sont en version 4 : ils gardent l'enchaînement du panneau SONG
(positions, répétitions, transposition, boucle), le nom de chaque motif, et
leur banque de samples (ROBOT emporte DRUMS.SMP).
Dans l'ordre d'un morceau, « NOM/+5 » transpose la position de 5 demi-tons ;
deux positions identiques qui se suivent deviennent une position x2.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import gen_patterns as gp  # noqa: E402
import insbank  # noqa: E402
from gen_patterns import R, L, G, NK, DK, OFF  # noqa: E402,F401

TON, BRUIT, ENV, PORTA = insbank.TON, insbank.BRUIT, insbank.ENV, insbank.PORTA
NB_PAT = 32
SONG_VER = 4
POS_MAX = 64
EMPTY_PAT = bytes([0, 125, 0, 0] + [0xFF, 0, 0xFF, 0] * 64)
USER_SLOTS = ["USER1", "USER2", "USER3", "USER4"]
ROLES = {"lead": gp.MELODIC, "bass": gp.BASSY, "chord": gp.CHORDY, "pluck": set()}
ROLE_RANGES = {"lead": (36, 88), "bass": (24, 52), "chord": (40, 79), "pluck": (33, 84)}


def ins(name, a=255, d=8, s=10, r=12, v=15, f=TON, n=0, shape=0, shift=0,
        arp1=0, arp2=0, arps=0, vd=0, vs=0, vdel=0, slide=0):
    """Un instrument au format de gen_factory : (nom, 16 valeurs)."""
    if (arp1 or arp2) and not arps:
        arps = 2
    if f & ENV and not shape:
        shape = 8
    return (name, a, d, s, r, v, f, n, shape, shift, arp1, arp2, arps, vd, vs, vdel, slide)


def ins_bytes(t):
    return bytes(x & 0xFF for x in t[1:])


SONGS = []


def song(name, title, style, bpm, key, desc, volumes=(15, 15, 15, 15), bank=None,
         instruments=(), order=(), loop=None, tests=""):
    s = dict(name=name, title=title, style=style, bpm=bpm, key=key, desc=desc,
             volumes=volumes, bank=bank, instruments=list(instruments), order=list(order),
             loop=loop, tests=tests, patterns=[])
    SONGS.append(s)
    return s


def poly(s, name, desc, A=None, B=None, C=None, N=None, bpm=None):
    s["patterns"].append(dict(disk="songs", name=name, style=s["style"], bpm=bpm or s["bpm"],
                              key=s["key"], desc=desc, mode=gp.POLY,
                              lanes=[A or [None] * 16, B, C, N]))   # (check lit toujours la voix A)


def mono(s, name, desc, lane, bpm=None):
    s["patterns"].append(dict(disk="songs", name=name, style=s["style"], bpm=bpm or s["bpm"],
                              key=s["key"], desc=desc, mode=gp.MONO, lanes=[lane, None, None, None]))


# ============================================================================
# 1. NUIT : synthwave, notes tenues et arrêts (traits de durée), vibrato
# ============================================================================
nuit = song("NUIT", "Nuit", "synthwave", 112, "A:min",
            "Am - F - C - G, basse en doubles croches, lead tenu avec vibrato",
            volumes=(15, 14, 12, 13),
            instruments=[(ins("NUITLD", d=4, s=13, r=8, vd=2, vs=40, vdel=18), "lead"),
                         (ins("NUITBS", d=14, s=10, r=20), "bass"),
                         (ins("NUITPD", a=10, d=2, s=12, r=4, v=13, arp1=3, arp2=7), "chord"),
                         (ins("NUITPM", a=10, d=2, s=12, r=4, v=13, arp1=4, arp2=7), "chord")],
            order=["NUINTRO", "NUINTRO", "NUCOUPL", "NUCOUP2", "NUCOUPL", "NUCOUP2",
                   "NUREFR", "NUREFR2", "NUREFR", "NUREFR2", "NUBREAK", "NUREFR", "NUREFR2", "NUFIN"],
            loop="NUCOUPL",
            tests="notes tenues jusqu'à leur arrêt (traits ■──X), vibrato du lead, "
                  "accords tenus (arpège rapide), 16 pas de charleston")
poly(nuit, "NUINTRO", "intro : nappe Am puis F, charleston qui monte",
     C=L("A3@NUITPD . . . . . . - F3@NUITPM . . . . . . -"),
     N=G("........h.h.hhhH", NK))
poly(nuit, "NUCOUPL", "couplet 1 : Am - F",
     A=R("x.xxx.x-x.xxx.x-", "A2 A2 A3 A2 A2 F2 F2 F3 F2 F2", "NUITBS"),
     C=L("A3@NUITPD . . . . . . - F3@NUITPM . . . . . . -"),
     N=G("k.h.s.hhk.hhs.hh", NK))
poly(nuit, "NUCOUP2", "couplet 2 : C - G",
     A=R("x.xxx.x-x.xxx.x-", "C2 C2 C3 C2 C2 G2 G2 G3 G2 G2", "NUITBS"),
     C=L("C4@NUITPM . . . . . . - G3@NUITPM . . . . . . -"),
     N=G("k.h.s.hhk.hhs.hk", NK))
poly(nuit, "NUREFR", "refrain 1 : le lead entre (Am - F)",
     A=R("x.xxx.x-x.xxx.x-", "A2 A2 A3 A2 A2 F2 F2 F3 F2 F2", "NUITBS"),
     B=L("E5 . . C5 . A4 . - A4 . C5 . F5 . . -", "NUITLD"),
     C=L("A3@NUITPD . . . . . . - F3@NUITPM . . . . . . -"),
     N=G("khhhshhhkhhhshhh", NK))
poly(nuit, "NUREFR2", "refrain 2 : C - G, le lead redescend",
     A=R("x.xxx.x-x.xxx.x-", "C2 C2 C3 C2 C2 G2 G2 G3 G2 G2", "NUITBS"),
     B=L("G5 . . E5 . C5 . - D5 . B4 . G4 . . -", "NUITLD"),
     C=L("C4@NUITPM . . . . . . - G3@NUITPM . . . . . . -"),
     N=G("khhhshhhkhhhshSS", NK))
poly(nuit, "NUBREAK", "pont : le lead seul, une note par temps",
     B=L("A4 . . - C5 . . - E5 . . - A5 . . -", "NUITLD"),
     N=G("h.h.h.h.h.h.h.hh", NK))
poly(nuit, "NUFIN", "fin : accord de la mineur tenu, puis arrêt",
     A=L("A2 . . . . . . . . . . . . . . -", "NUITBS"),
     C=L("A3 . . . . . . . . . . . . . . -", "NUITPD"),
     N=G("x...............", NK))

# ============================================================================
# 2. ROBOT : électro avec digidrums (DRUMS.SMP rechargée avec le morceau)
# ============================================================================
robot = song("ROBOT", "Robot", "electro (digidrums)", 125, "D:min",
             "grosse caisse et caisse claire samplées, basse buzzer, zaps",
             volumes=(15, 15, 13, 12), bank="DRUMS",
             instruments=[(ins("ROBOBS", d=0, s=15, r=255, f=ENV, shape=10, shift=4), "bass"),
                          (ins("ROBOPL", d=12, s=0, r=12), "pluck"),
                          (ins("ROBOLD", d=6, s=12, r=10, arp1=12, arps=1), "lead"),
                          (ins("ROBOZP", d=10, s=0, r=10, slide=-6), "pluck")],
             order=["RBINTRO", "RBINTRO", "RBGROOV", "RBGROOV", "RBBASS", "RBBASS",
                    "RBTHEME", "RBTHEME", "RBBREAK", "RBTHEME", "RBFIN"],
             loop="RBGROOV",
             tests="digidrums (la banque DRUMS se recharge avec le morceau), mode "
                   "BLOQUANT et rattrapage du tempo, basse à enveloppe matérielle")
poly(robot, "RBINTRO", "intro : digidrums seuls",
     A=G("K.....K...K.....", DK), B=G("....S.......S..s", DK),
     N=G("h.hhh.hhh.hhh.hh", NK))
poly(robot, "RBGROOV", "groove : digidrums + pluck syncopé",
     A=G("K.....K...K.....", DK), B=G("....S.......S..s", DK),
     C=R("..x..x.x..x..x-.", "D4 F4 A4 D4 C4", "ROBOPL"),
     N=G("h.hhh.hhh.hhh.hh", NK))
poly(robot, "RBBASS", "la basse buzzer entre",
     A=G("K.....K...K.....", DK),
     B=L("D2 . . - D2 . F2 - . A2 . - C3 . . -", "ROBOBS"),
     C=R("..x..x.x..x..x-.", "D4 F4 A4 D4 C4", "ROBOPL"),
     N=G("h.hhs.hhh.hhs.hh", NK))
poly(robot, "RBTHEME", "thème en octaves sur la basse",
     A=G("K.....K...K.....", DK),
     B=L("D2 . . - D2 . F2 - . A2 . - C3 . . -", "ROBOBS"),
     C=L("D4 . . A4 . . F4 . E4 . . D4 . C4 . -", "ROBOLD"),
     N=G("h.hhs.hhh.hhs.hh", NK))
poly(robot, "RBBREAK", "break : zaps et caisse claire",
     A=G("....S.......S.SS", DK),
     C=R("x...x...x...x.x-", "A4 F4 D4 A4 D5", "ROBOZP"),
     N=G("h.h.h.h.h.h.h.h.", NK))
poly(robot, "RBFIN", "fin : un coup de grosse caisse et un zap",
     A=G("K...............", DK), C=R("x...............", "D4", "ROBOZP"))

# ============================================================================
# 3. PIXEL : chiptune rapide, arpèges en doubles croches
# ============================================================================
pixel = song("PIXEL", "Pixel", "chiptune", 150, "C:maj",
             "thème de jeu en do majeur, arpèges en doubles croches",
             volumes=(14, 15, 13, 13),
             instruments=[(ins("PIXLD", d=4, s=12, r=8, vd=1, vs=32, vdel=10), "lead"),
                          (ins("PIXAR", d=6, s=10, r=8, arp1=4, arp2=7, arps=1), "chord"),
                          (ins("PIXARM", d=6, s=10, r=8, arp1=3, arp2=7, arps=1), "chord"),
                          (ins("PIXBS", d=20, s=8, r=20), "bass")],
             order=["PXINTRO", "PXTHEME", "PXTHEM2", "PXTHEME", "PXTHEM2",
                    "PXPONT", "PXPONT", "PXTHEME", "PXFIN"],
             loop="PXTHEME",
             tests="tempo rapide, arpèges d'instrument (accords en une voix), "
                   "notes sur tous les pas")
poly(pixel, "PXINTRO", "intro : arpège do majeur seul",
     C=L("C4@PIXAR . C4@PIXAR . E4@PIXARM . E4@PIXARM . G4@PIXAR . G4@PIXAR . E4@PIXARM . E4@PIXARM -"),
     N=G("..........h.hhhH", NK))
poly(pixel, "PXTHEME", "thème : do - fa",
     A=R("x.xxx.xxx.xxx.x-", "C2 C3 C2 C3 C2 C3 F2 F3 F2 F3 F2", "PIXBS"),
     B=L("E5 . G5 . C6 . G5 E5 F5 . A5 . C6 . A5 -", "PIXLD"),
     C=R("x...x...x...x..-", "C4 C4 F3 F3", "PIXAR"),
     N=G("h.hhs.hhh.hhs.hh", NK))
poly(pixel, "PXTHEM2", "thème, suite : sol - do",
     A=R("x.xxx.xxx.xxx.x-", "G2 G3 G2 G3 G2 G3 C2 C3 C2 C3 C2", "PIXBS"),
     B=L("D5 . G5 . B5 . G5 D5 C5 . E5 . G5 . C6 -", "PIXLD"),
     C=R("x...x...x...x..-", "G3 G3 C4 C4", "PIXAR"),
     N=G("h.hhs.hhh.hhs.SS", NK))
poly(pixel, "PXPONT", "pont : la mineur - fa, arpèges",
     A=R("x.x.x.x.x.x.x.x-", "A2 A2 A2 A2 F2 F2 F2 F2", "PIXBS"),
     C=L("A3@PIXARM A3@PIXARM A3@PIXARM A3@PIXARM A3@PIXARM A3@PIXARM A3@PIXARM - "
         "F3@PIXAR F3@PIXAR F3@PIXAR F3@PIXAR F3@PIXAR F3@PIXAR F3@PIXAR -"),
     N=G("h.h.s.h.h.h.s.hh", NK))
poly(pixel, "PXFIN", "fin : niveau terminé",
     B=L("C5 E5 G5 C6 . . . . . . . . . . . -", "PIXLD"),
     C=L("C4 . . . . . . . . . . . . . . -", "PIXAR"),
     N=G("x...............", NK))

# ============================================================================
# 4. FUNKY : funk en mi dorien, basse en doubles croches, glissando
# ============================================================================
funky = song("FUNKY", "Funky", "funk", 100, "E:dor",
             "basse funk en doubles croches, accords piqués, lead glissé",
             volumes=(15, 13, 13, 14),
             instruments=[(ins("FKBASS", d=24, s=6, r=24), "bass"),
                          (ins("FKSTAB", d=40, s=0, r=30, arp1=3, arp2=10, arps=1), "chord"),
                          (ins("FKSLID", d=4, s=13, r=8, f=TON | PORTA, slide=6), "lead"),
                          (ins("FKCLAV", d=30, s=0, r=20), "pluck")],
             order=["FKINTRO", "FKGROOV", "FKGROOV", "FKRIFF", "FKRIFF",
                    "FKBREAK", "FKGROOV/+5", "FKRIFF/+5", "FKGROOV", "FKFIN"],
             loop="FKGROOV",
             tests="basse sur les doubles croches, notes fantômes (volumes), "
                   "glissando (PORTA), accords mineurs 7 en une voix")
poly(funky, "FKINTRO", "intro : charleston et notes fantômes",
     N=G("hgh.shgqhgh.shgh", NK))
poly(funky, "FKGROOV", "groove : basse + accords piqués",
     A=L("E2 . - E3 - . E2 G2 . A2 - . B2 . D3 -", "FKBASS"),
     B=R("..x...x...x..x..", "E4 E4 B3 E4", "FKSTAB"),
     N=G("hgh.shgqhgh.shgh", NK))
poly(funky, "FKRIFF", "riff : le lead glisse",
     A=L("E2 . - E3 - . E2 G2 . A2 - . B2 . D3 -", "FKBASS"),
     B=R("..x...x...x..x..", "E4 E4 B3 E4", "FKSTAB"),
     C=L("B4 . . - D5 . E5 . . - G5 . E5 . . -", "FKSLID"),
     N=G("hgh.shgqhgh.shgh", NK))
poly(funky, "FKBREAK", "break : clavinet syncopé seul",
     C=R("x.xx.x.x.xx.x.x-", "E4 G4 A4 B4 A4 G4 E4 D4 E4", "FKCLAV"),
     N=G("h.h.h.h.h.h.h.h.", NK))
poly(funky, "FKFIN", "fin : basse et accord",
     A=L("E2 . . . . . . . . . . . . . . -", "FKBASS"),
     B=R("x...............", "E4", "FKSTAB"),
     N=G("x...............", NK))

# ============================================================================
# 5. NAPPE : mode son composé (une voix qui joue un son à 4 voix)
# ============================================================================
nappe = song("NAPPE", "Nappe", "ambient (son composé)", 90, "A:min",
             "accords des sons composés : mineur, majeur, sus4, mineur 7, batterie",
             volumes=(13, 12, 12, 14),
             instruments=[(ins("DOUX", a=24, d=2, s=11, r=6, v=12), "lead"),
                          (ins("SIFFLE", a=30, d=2, s=12, r=6, v=11, vd=1, vs=48), "lead"),
                          (ins("CHORUS", d=4, s=12, r=8, arp1=12, arps=3, vd=1, vs=20), "lead"),
                          (ins("HEROS", d=4, s=13, r=8, vd=2, vs=40, vdel=18), "lead")],
             order=["NPINTRO", "NPACCO", "NPACCO2", "NPACCO", "NPACCO2", "NPRYTHM", "NPRYTHM", "NPFIN"],
             loop="NPACCO",
             tests="mode son composé : une seule voix SON et les 4 couches du son "
                   "affichées sous la grille ; sons 0, 1, 5, 6, 7")
mono(nappe, "NPINTRO", "intro : sus4 lents",
     R("x......-x......-", "D4@5 E4@5"))
mono(nappe, "NPACCO", "accords lam7 - fa",
     R("x..-..x-x..-..x-", "A3@6 A3@6 F3@1 F3@1"))
mono(nappe, "NPACCO2", "accords do - mi mineur",
     R("x..-..x-x..-..x-", "C4@1 C4@1 E4@0 E4@0"))
mono(nappe, "NPRYTHM", "la grosse caisse du son 7",
     R("x.x.x.x.x.x.x.x.", "A2@7"))
mono(nappe, "NPFIN", "fin : accord mineur tenu",
     R("x..............-", "A3@0"))


# ============================================================================
# Fabrication
# ============================================================================
def _apply_instruments(s):
    """Met les instruments du morceau dans les places USER1 à USER4 (pour
    gen_patterns : noms, tessitures, rôles).  -> fonction qui annule."""
    saved = (list(gp.INSTRUMENTS), dict(gp.I), dict(gp.RANGES),
             {k: set(v) for k, v in ROLES.items()})
    for slot, (t, role) in zip(USER_SLOTS, s["instruments"]):
        idx = saved[1][slot]
        gp.INSTRUMENTS[idx] = t
        gp.I.pop(slot, None)
        gp.I[t[0]] = idx
        gp.RANGES[t[0]] = ROLE_RANGES[role]
        ROLES[role].add(t[0])

    def undo():
        gp.INSTRUMENTS[:] = saved[0]
        gp.I.clear()
        gp.I.update(saved[1])
        gp.RANGES.clear()
        gp.RANGES.update(saved[2])
        for k, v in saved[3].items():
            ROLES[k].clear()
            ROLES[k].update(v)
    return undo


def check_song(s):
    """Problèmes du morceau (liste vide = bon)."""
    err = []
    if len(s["instruments"]) > 4:
        err.append("plus de 4 instruments à lui")
    names = [p["name"] for p in s["patterns"]]
    if len(set(names)) != len(names):
        err.append("motifs en double")
    for o in s["order"]:
        name, _, tr = o.partition("/")
        if name not in names:
            err.append("ordre : motif inconnu %s" % o)
        if tr and not -12 <= int(tr) <= 12:
            err.append("ordre : transposition %s" % o)
    if s["loop"] is not None and s["loop"] not in names:
        err.append("boucle : motif inconnu %s" % s["loop"])
    if len(positions(s)[0]) > POS_MAX:
        err.append("plus de %d positions" % POS_MAX)
    undo = _apply_instruments(s)
    try:
        for p in s["patterns"]:
            for e in gp.check(p):
                err.append("%s : %s" % (p["name"], e))
    finally:
        undo()
    return err


def encode_patterns(s):
    undo = _apply_instruments(s)
    try:
        return [(p["name"], gp.encode(p)) for p in s["patterns"]]
    finally:
        undo()


def ins_bank(s):
    """La banque .INS du morceau : usine + ses instruments en USER1-4."""
    with open(os.path.join(ROOT, "instruments", "USINE.INS"), "rb") as fh:
        sounds, sons = insbank.parse_ins_bank(fh.read())
    for slot, (t, _) in zip(USER_SLOTS, s["instruments"]):
        idx = gp.I[slot]
        sounds[idx] = (t[0], ins_bytes(t))
    return insbank.build_ins_bank(sounds, sons, s["volumes"])


def song_file(s):
    """Le .SNG (version 2) : en-tête, instruments, noms, sons, 32 motifs,
    bloc v2 (mode BLOQUANT, banque de samples)."""
    bank = ins_bank(s)
    head = b"SQ16" + bytes([SONG_VER]) + bytes(s["volumes"]) + bytes(7)
    pats = [data for _, data in encode_patterns(s)]
    assert len(pats) <= NB_PAT
    pats += [EMPTY_PAT] * (NB_PAT - len(pats))
    name = (s["bank"] or "").ljust(8).encode("ascii") if s["bank"] else bytes(8)
    v2 = bytes([0]) + name + bytes(7)
    data = head + bank[16:] + b"".join(pats) + v2 + v3_block(s)
    assert len(data) == IMAGE_LEN
    smp = sample_bank(s)                    # version 4 : la banque de samples
    return data + len(smp).to_bytes(2, "little") + smp


def sample_bank(s):
    """La banque de samples du morceau (samples/NOM.SMP), ou rien."""
    if not s["bank"]:
        return b""
    with open(os.path.join(ROOT, "samples", s["bank"] + ".SMP"), "rb") as fh:
        return fh.read()


V3_LEN = 2 + POS_MAX * 3 + NB_PAT * 8
IMAGE_LEN = 16 + 32 * 16 + 32 * 6 + 8 * 16 + NB_PAT * 260 + 16 + V3_LEN


def positions(s):
    """L'ordre du morceau -> ([(motif, répétitions, transposition)], boucle)."""
    index = {p["name"]: i for i, p in enumerate(s["patterns"])}
    out, starts = [], {}
    for o in s["order"]:
        name, _, tr = o.partition("/")
        tr = int(tr) if tr else 0
        pat = index[name]
        if out and out[-1][0] == pat and out[-1][2] == tr and out[-1][1] < 16:
            out[-1][1] += 1
        else:
            starts.setdefault(name, len(out))
            out.append([pat, 1, tr])
    loop = starts.get(s["loop"], 0) if s["loop"] else 0
    return [tuple(x) for x in out], loop


def v3_block(s):
    """Bloc v3 : nombre de positions, boucle, 64 positions, 32 noms."""
    pos, loop = positions(s)
    data = bytearray([len(pos), loop])
    for pat, rep, tr in pos:
        data += bytes([pat, rep, tr & 0xFF])
    data += bytes(3 * (POS_MAX - len(pos)))
    names = [p["name"] for p in s["patterns"]] + [""] * (NB_PAT - len(s["patterns"]))
    for n in names:
        data += n.ljust(8).encode("ascii")
    assert len(data) == V3_LEN
    return bytes(data)


def odd_ratio(s):
    """Part des notes jouées sur les pas impairs (vraies doubles croches)."""
    odd = total = 0
    for p in s["patterns"]:
        for lane in p["lanes"]:
            for st, ev in enumerate(lane or []):
                if ev not in (None, OFF):
                    total += 1
                    odd += st % 2
    return odd / total if total else 0


def validate():
    bad = []
    for s in SONGS:
        for e in check_song(s):
            bad.append("%s / %s" % (s["name"], e))
    if bad:
        raise SystemExit("Morceaux de test refusés :\n  " + "\n  ".join(bad))


def liste_md():
    out = ["# Morceaux de test", "",
           "Fabriqués par `tools/gen_songs.py` ; tous sur `build/seq16-songs.dsk`.", "",
           "Charger un morceau : panneau SONG (f2), puis f9 ; ESPACE le joue depuis "
           "la position du curseur.  ↑ marque le départ de la boucle.", ""]
    for s in SONGS:
        out += ["## %s : %s (%s, %d BPM)" % (s["name"], s["title"], s["style"], s["bpm"]), "",
                s["desc"] + ".", "",
                "- Fichiers : `%s.SNG`%s, `%s.INS`" % (s["name"],
                                                     " (avec sa banque `%s.SMP`)" % s["bank"] if s["bank"] else "",
                                                     s["name"]),
                "- Instruments à lui : " + ", ".join(t[0] for t, _ in s["instruments"]),
                "- À tester : " + s["tests"],
                "- Enchaînement (panneau SONG) : " + " ".join(
                    "%s%s%s%s" % ("↑" if i == positions(s)[1] else "",
                                  s["patterns"][pat]["name"],
                                  " x%d" % rep if rep > 1 else "",
                                  " %+d" % tr if tr else "")
                    for i, (pat, rep, tr) in enumerate(positions(s)[0])), "",
                "| Motif | N° | Contenu |", "|---|---|---|"]
        for i, p in enumerate(s["patterns"]):
            out.append("| `%s` | %02d | %s |" % (p["name"], i + 1, p["desc"]))
        out.append("")
    return "\n".join(out)


def write_all():
    validate()
    import amsdsk
    out = os.path.join(ROOT, "songs")
    pat_dir = os.path.join(out, "pat")
    os.makedirs(pat_dir, exist_ok=True)
    for d in (out, pat_dir):                     # pas de vieux fichiers oubliés
        for f in os.listdir(d):
            if f.upper().endswith((".SNG", ".INS", ".PAT")):
                os.remove(os.path.join(d, f))
    files = []
    for s in SONGS:
        files.append((s["name"] + ".SNG", song_file(s)))
        files.append((s["name"] + ".INS", ins_bank(s)))
    for s in SONGS:
        for name, data in encode_patterns(s):
            files.append((name + ".PAT", data))
    for name, data in files:
        sub = pat_dir if name.endswith(".PAT") else out
        with open(os.path.join(sub, name), "wb") as fh:
            fh.write(data)
    with open(os.path.join(out, "LISTE.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(liste_md())
    dsk = os.path.join(ROOT, "build", "seq16-songs.dsk")   # programme + DRUMS + tout
    shutil.copy(os.path.join(ROOT, "build", "seq16.dsk"), dsk)
    for name in amsdsk.list_files(dsk):
        if name not in ("SEQ16.BIN", "DRUMS.SMP"):
            amsdsk.remove_file(dsk, name)
    for name, data in files:
        amsdsk.add_file(dsk, name, data)
    return dsk, len(files)


def main():
    dsk, n = write_all()
    for s in SONGS:
        print("%-6s %3d BPM  %d motifs  %2.0f %% de notes sur les pas impairs"
              % (s["name"], s["bpm"], len(s["patterns"]), 100 * odd_ratio(s)))
    print("%s : SEQ16.BIN, DRUMS.SMP et %d fichiers" % (dsk, n))


if __name__ == "__main__":
    main()
