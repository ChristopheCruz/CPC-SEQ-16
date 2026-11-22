"""Fabrique les banques d'instruments .INS de la disquette SEQ-16.

Chaque banque contient 32 sons, rangés par thème (batterie, basses, leads,
nappes, effets...).  Les sons par défaut du programme restent dans le
programme (src/factory.asm) ; la banque USINE en est une simple copie, pour
pouvoir les recharger après avoir chargé une autre banque.

Lancement :
    python tools/gen_instruments.py            -> instruments/*.INS
    python tools/gen_instruments.py --dsk      -> et ajout à build/seq16-fr.dsk
    python tools/gen_instruments.py --list     -> liste des sons

Sur le CPC : écran f3, touche O pour charger une banque entière ; écran f2,
touche O pour prendre un seul son dans une banque.
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import insbank  # noqa: E402
from insbank import TON, BRUIT, ENV, PORTA  # noqa: E402

OUT_DIR = os.path.join(ROOT, "instruments")


def ins(a=255, d=8, s=10, r=12, v=15, f=TON, n=0, shape=0, shift=0,
        arp1=0, arp2=0, arps=0, vd=0, vs=0, vdel=0, slide=0):
    """Un instrument de 16 octets (voir tools/insbank.py pour le sens).

    a, d, s, r : attaque, déclin, tenue (0-15), relâche ; v : volume (0-15) ;
    f : drapeaux TON / BRUIT / ENV / PORTA ; n : période du bruit (0-31) ;
    shape, shift : enveloppe matérielle ; arp1, arp2, arps : arpège ;
    vd, vs, vdel : vibrato ; slide : glissando (positif = le son descend).
    """
    if arp1 or arp2:
        arps = arps or 2                 # vitesse 1 à 15 si l'arpège sert
    if f & ENV and not shape:
        shape = 8                        # forme 8 à 15 si l'enveloppe sert
    return bytes([a, d, s, r, v, f, n, shape, shift, arp1, arp2, arps,
                  vd, vs, vdel, slide & 0xFF])


# ---------------------------------------------------------------------------
# Les banques
# ---------------------------------------------------------------------------
def usine():
    """Les 32 instruments par défaut, relus dans src/factory.asm."""
    src = open(os.path.join(ROOT, "src", "factory.asm"), encoding="utf-8").read()
    rows = re.findall(r"^\s*;?\s*db\s+([0-9, ]+?)\s*;\s*\d+\s+(\S+)\s*$", src, re.M)
    out = []
    for values, name in rows[:32]:
        b = bytes(int(x) for x in values.split(","))
        assert len(b) == 16, name
        out.append((name, b))
    assert len(out) == 32
    return out


def batterie():
    k = []
    for i, sl in enumerate((24, 18, 30, 12, 40)):            # grosses caisses
        k.append((f"KICK{i + 1}", ins(d=20 + 4 * i, s=0, r=20 + 4 * i, slide=sl)))
    k.append(("KICK8B", ins(d=6, s=0, r=6, slide=20)))       # longue, façon 808
    k.append(("KICKBZ", ins(d=16, s=0, r=16, f=TON | BRUIT, n=31, slide=24)))
    for i, n in enumerate((8, 10, 12, 14)):                  # caisses claires
        k.append((f"SNARE{i + 1}", ins(d=18 + 2 * i, s=0, r=18 + 2 * i, f=TON | BRUIT, n=n, slide=10)))
    k.append(("SNRBRU", ins(d=16, s=0, r=16, f=BRUIT, n=6)))
    k.append(("RIM", ins(d=60, s=0, r=60, f=TON | BRUIT, n=2, slide=4)))
    k.append(("CLAP", ins(d=30, s=0, r=30, f=BRUIT, n=6, arp1=12, arps=1)))
    k.append(("CLAP2", ins(d=22, s=0, r=22, f=BRUIT, n=9, arp1=7, arp2=12, arps=1)))
    for i, (n, d) in enumerate(((0, 60), (1, 48), (2, 40))):  # charlestons fermés
        k.append((f"HAT{i + 1}", ins(d=d, s=0, r=d, v=12, f=BRUIT, n=n)))
    k.append(("HATOUV", ins(d=8, s=0, r=8, v=12, f=BRUIT, n=1)))
    k.append(("HATPED", ins(d=30, s=0, r=30, v=10, f=BRUIT, n=3)))
    k.append(("CRASH", ins(d=3, s=0, r=3, v=13, f=BRUIT, n=2)))
    k.append(("RIDE", ins(d=5, s=2, r=6, v=11, f=TON | BRUIT, n=1)))
    for i, sl in enumerate((5, 7, 9)):                       # toms
        k.append((("TOMAIG", "TOMMED", "TOMGRV")[i], ins(d=14, s=0, r=14, slide=sl)))
    k.append(("TOMSYN", ins(d=10, s=0, r=10, slide=-6)))
    k.append(("COWBEL", ins(d=14, s=0, r=14, arp1=7, arps=1)))
    k.append(("SHAKER", ins(a=40, d=40, s=0, r=40, v=10, f=BRUIT, n=0)))
    k.append(("CLAVES", ins(d=70, s=0, r=70, slide=-2)))
    k.append(("BLOC", ins(d=50, s=0, r=50, f=TON | BRUIT, n=0, slide=2)))
    k.append(("ZAPDRM", ins(d=12, s=0, r=12, slide=-12)))
    k.append(("BUZDRM", ins(d=0, s=15, r=255, f=ENV, shape=8, shift=3, slide=16)))
    return k


def basses():
    k = []
    k.append(("BASS1", ins(d=16, s=12, r=24)))
    k.append(("BASS2", ins(d=10, s=8, r=12)))
    k.append(("BASSCR", ins(d=40, s=0, r=40)))                # courte
    k.append(("BASSLG", ins(d=4, s=13, r=8)))                 # longue
    k.append(("BASPLK", ins(d=24, s=0, r=24, slide=2)))
    k.append(("BASPNC", ins(d=30, s=6, r=20, slide=-1)))
    k.append(("BASOCT", ins(d=8, s=10, r=12, arp1=12, arps=1)))
    k.append(("BASOC2", ins(d=8, s=10, r=12, arp1=12, arps=3)))
    k.append(("BAS5", ins(d=8, s=10, r=12, arp1=7, arps=2)))
    k.append(("BASSUB", ins(a=60, d=2, s=14, r=10)))
    k.append(("BASVIB", ins(d=6, s=12, r=12, vd=1, vs=24, vdel=10)))
    k.append(("BASWOB", ins(d=0, s=15, r=20, vd=3, vs=16)))
    k.append(("BASWB2", ins(d=0, s=15, r=20, vd=4, vs=40)))
    k.append(("BASGLI", ins(d=6, s=12, r=12, f=TON | PORTA, slide=6)))
    k.append(("BASGL2", ins(d=6, s=12, r=12, f=TON | PORTA, slide=16)))
    k.append(("BASDRO", ins(d=6, s=12, r=12, slide=1)))
    k.append(("BASMON", ins(d=6, s=12, r=12, slide=-1)))
    k.append(("BASBZ1", ins(d=0, s=15, r=255, f=ENV, shape=8, shift=4)))
    k.append(("BASBZ2", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=4)))
    k.append(("BASBZ3", ins(d=0, s=15, r=255, f=ENV, shape=8, shift=3)))
    k.append(("BASBZ4", ins(d=0, s=15, r=255, f=ENV, shape=12, shift=5)))
    k.append(("BASBZT", ins(d=0, s=15, r=255, f=TON | ENV, shape=8, shift=4)))
    k.append(("BASBZG", ins(d=0, s=15, r=255, f=TON | ENV, shape=10, shift=5, slide=2)))
    k.append(("BASSAL", ins(d=10, s=10, r=14, f=TON | BRUIT, n=31)))
    k.append(("BASGRS", ins(d=12, s=8, r=12, f=TON | BRUIT, n=28)))
    k.append(("BASSAT", ins(d=0, s=15, r=30, v=15)))
    k.append(("BASDOU", ins(a=20, d=4, s=10, r=6, v=13)))
    k.append(("BASFUN", ins(d=36, s=4, r=30, slide=-3)))
    k.append(("BASACI", ins(d=20, s=6, r=20, f=TON | PORTA, slide=10, vd=1, vs=60)))
    k.append(("BASTRM", ins(d=0, s=15, r=12, arp1=12, arp2=0, arps=1, vd=0)))
    k.append(("BASARP", ins(d=8, s=12, r=12, arp1=3, arp2=7, arps=2)))
    k.append(("BASS8", ins(d=2, s=14, r=4, v=14)))
    return k


def leads():
    k = []
    k.append(("LEAD1", ins(d=8, s=10, r=12)))
    k.append(("LEAD2", ins(d=4, s=12, r=8)))
    k.append(("LEADCR", ins(d=30, s=6, r=20)))
    k.append(("LEADLG", ins(d=2, s=14, r=4)))
    for i, (vd, vs, vdel) in enumerate(((1, 32, 15), (2, 32, 20), (2, 48, 0), (3, 24, 25), (1, 64, 8))):
        k.append((f"VIB{i + 1}", ins(d=6, s=12, r=10, vd=vd, vs=vs, vdel=vdel)))
    k.append(("PORTA1", ins(d=4, s=13, r=8, f=TON | PORTA, slide=6)))
    k.append(("PORTA2", ins(d=4, s=13, r=8, f=TON | PORTA, slide=12)))
    k.append(("PORTA3", ins(d=4, s=13, r=8, f=TON | PORTA, slide=3, vd=1, vs=32, vdel=15)))
    k.append(("MONTE", ins(d=4, s=13, r=8, slide=-2)))
    k.append(("DESCEN", ins(d=4, s=13, r=8, slide=2)))
    k.append(("SYNC", ins(d=0, s=15, r=10, f=TON | ENV, shape=10, shift=2)))
    k.append(("SYNC2", ins(d=0, s=15, r=10, f=TON | ENV, shape=8, shift=1)))
    k.append(("BUZLD1", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=4, vd=1, vs=32, vdel=10)))
    k.append(("BUZLD2", ins(d=0, s=15, r=255, f=ENV, shape=14, shift=4)))
    k.append(("OCTLD", ins(d=6, s=12, r=10, arp1=12, arps=1)))
    k.append(("QUINTE", ins(d=6, s=12, r=10, arp1=7, arps=1)))
    k.append(("TRILLE", ins(d=6, s=12, r=10, arp1=2, arps=2)))
    k.append(("TRIL3", ins(d=6, s=12, r=10, arp1=1, arps=1)))
    k.append(("SALE", ins(d=6, s=11, r=10, f=TON | BRUIT, n=20)))
    k.append(("SALE2", ins(d=6, s=11, r=10, f=TON | BRUIT, n=8)))
    k.append(("DOUX", ins(a=24, d=2, s=11, r=6, v=12)))
    k.append(("DOUX2", ins(a=12, d=2, s=12, r=4, v=13, vd=1, vs=28, vdel=12)))
    k.append(("PERCU", ins(d=40, s=4, r=30)))
    k.append(("STAB", ins(d=40, s=6, r=30, arp1=4, arp2=7, arps=1)))
    k.append(("HEROS", ins(d=4, s=13, r=8, vd=2, vs=40, vdel=18)))
    k.append(("SIFFLE", ins(a=30, d=2, s=12, r=6, v=11, vd=1, vs=48)))
    k.append(("CHORUS", ins(d=4, s=12, r=8, arp1=12, arps=3, vd=1, vs=20)))
    k.append(("FUZZ", ins(d=0, s=15, r=10, f=TON | BRUIT | ENV, shape=10, shift=3, n=4)))
    return k


def nappes():
    k = []
    for i, (a, r) in enumerate(((6, 4), (3, 3), (2, 2), (12, 6), (1, 1))):
        k.append((f"PAD{i + 1}", ins(a=a, d=2, s=12, r=r, v=13)))
    for i, (vd, vs) in enumerate(((1, 24), (1, 40), (2, 20))):
        k.append((f"PADVB{i + 1}", ins(a=4, d=2, s=12, r=3, v=13, vd=vd, vs=vs)))
    chords = (("MAJ", 4, 7), ("MIN", 3, 7), ("SUS4", 5, 7), ("SUS2", 2, 7), ("MAJ7", 4, 11),
              ("MIN7", 3, 10), ("DIM", 3, 6), ("AUG", 4, 8), ("ADD9", 4, 14), ("5TE", 7, 12))
    for name, a1, a2 in chords:                              # accords lents
        k.append((f"P{name}"[:6], ins(a=5, d=2, s=12, r=3, v=12, arp1=a1, arp2=a2, arps=1)))
    k.append(("CHOEUR", ins(a=3, d=1, s=13, r=2, v=12, vd=1, vs=20, vdel=20)))
    k.append(("CORDES", ins(a=4, d=1, s=13, r=3, v=13, vd=1, vs=32, vdel=10)))
    k.append(("ORGUE", ins(a=255, d=0, s=15, r=40, v=12, arp1=12, arps=1)))
    k.append(("ORGUE2", ins(a=255, d=0, s=15, r=40, v=12, arp1=12, arp2=19, arps=1)))
    k.append(("SOUFLE", ins(a=4, d=1, s=10, r=2, v=11, f=TON | BRUIT, n=31)))
    k.append(("VENT", ins(a=2, d=1, s=10, r=1, v=10, f=BRUIT, n=20, vd=2, vs=8)))
    k.append(("NAPBUZ", ins(a=3, d=0, s=15, r=2, f=ENV, shape=14, shift=6)))
    k.append(("NAPBZ2", ins(a=3, d=0, s=15, r=2, f=ENV, shape=10, shift=7)))
    k.append(("LENT", ins(a=1, d=1, s=14, r=1, v=13)))
    k.append(("NUAGE", ins(a=2, d=1, s=11, r=1, v=11, vd=3, vs=6)))
    k.append(("ESPACE", ins(a=2, d=1, s=12, r=1, v=12, arp1=12, arp2=7, arps=4, vd=1, vs=16)))
    k.append(("REVE", ins(a=3, d=1, s=12, r=2, v=12, arp1=7, arp2=12, arps=6)))
    k.append(("AURORE", ins(a=2, d=1, s=12, r=1, v=12, arp1=4, arp2=11, arps=5, vd=1, vs=12)))
    k.append(("GLACE", ins(a=6, d=1, s=11, r=2, v=11, arp1=24, arps=3)))
    return k


def arpeges():
    k = []
    chords = (("MAJ", 4, 7), ("MIN", 3, 7), ("7", 4, 10), ("M7", 3, 10), ("MAJ7", 4, 11),
              ("SUS4", 5, 7), ("SUS2", 2, 7), ("DIM", 3, 6), ("AUG", 4, 8), ("OCT", 12, 0),
              ("5TE", 7, 12), ("6", 4, 9))
    for name, a1, a2 in chords:                               # vitesse 1 (chiptune)
        k.append((("A" + name)[:6], ins(d=4, s=12, r=8, arp1=a1, arp2=a2, arps=1)))
    for name, a1, a2 in chords[:8]:                           # vitesse 2
        k.append((("B" + name)[:6], ins(d=4, s=12, r=8, arp1=a1, arp2=a2, arps=2)))
    for name, a1, a2 in chords[:4]:                           # vitesse 4, lent
        k.append((("L" + name)[:6], ins(d=4, s=12, r=8, arp1=a1, arp2=a2, arps=4)))
    k.append(("AMAJCR", ins(d=24, s=0, r=24, arp1=4, arp2=7, arps=1)))
    k.append(("AMINCR", ins(d=24, s=0, r=24, arp1=3, arp2=7, arps=1)))
    k.append(("ABUZMA", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=4, arp1=4, arp2=7, arps=1)))
    k.append(("ABUZMI", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=4, arp1=3, arp2=7, arps=1)))
    k.append(("AOCT2", ins(d=4, s=12, r=8, arp1=12, arp2=24, arps=1)))
    k.append(("ADOUX", ins(a=16, d=2, s=11, r=6, v=12, arp1=4, arp2=7, arps=2)))
    k.append(("AVIB", ins(d=4, s=12, r=8, arp1=3, arp2=7, arps=2, vd=1, vs=32)))
    k.append(("ASALE", ins(d=4, s=11, r=8, f=TON | BRUIT, n=16, arp1=4, arp2=7, arps=1)))
    return k


def effets():
    k = []
    k.append(("LASER1", ins(d=9, s=0, r=9, slide=6)))
    k.append(("LASER2", ins(d=6, s=0, r=6, slide=10)))
    k.append(("LASER3", ins(d=12, s=0, r=12, slide=3, arp1=12, arps=1)))
    k.append(("ZAP1", ins(d=12, s=0, r=12, slide=-8)))
    k.append(("ZAP2", ins(d=8, s=0, r=8, slide=-16)))
    k.append(("SIRENE", ins(d=0, s=15, r=20, v=13, vd=6, vs=8)))
    k.append(("SIREN2", ins(d=0, s=15, r=20, v=13, vd=5, vs=20)))
    k.append(("ALARME", ins(d=0, s=15, r=20, v=13, arp1=5, arps=8)))
    k.append(("BIP", ins(d=40, s=0, r=40, v=12)))
    k.append(("BIPBIP", ins(d=0, s=15, r=40, v=12, arp1=12, arps=4)))
    k.append(("PIECE", ins(d=10, s=0, r=10, arp1=5, arp2=12, arps=2)))
    k.append(("BONUS", ins(d=6, s=0, r=6, arp1=4, arp2=7, arps=1, slide=-2)))
    k.append(("SAUT", ins(d=10, s=0, r=10, slide=-6)))
    k.append(("CHUTE", ins(d=4, s=0, r=4, slide=4)))
    k.append(("TOMBE", ins(d=2, s=0, r=2, slide=2)))
    k.append(("TIR", ins(d=24, s=0, r=24, f=BRUIT, n=4, slide=6)))
    k.append(("TIR2", ins(d=16, s=0, r=16, f=TON | BRUIT, n=10, slide=12)))
    k.append(("EXPLO1", ins(d=3, s=0, r=3, f=BRUIT, n=31)))
    k.append(("EXPLO2", ins(d=2, s=0, r=2, f=BRUIT, n=24)))
    k.append(("BOOM", ins(d=4, s=0, r=4, f=TON | BRUIT, n=31, slide=8)))
    k.append(("MOTEUR", ins(d=0, s=15, r=20, f=ENV, shape=8, shift=6, vd=2, vs=10)))
    k.append(("HELICO", ins(d=0, s=14, r=20, f=BRUIT, n=20, vd=0, arp1=0)))
    k.append(("VAPEUR", ins(a=60, d=8, s=4, r=6, v=11, f=BRUIT, n=0)))
    k.append(("ROBOT", ins(d=0, s=15, r=20, f=ENV, shape=12, shift=3, arp1=7, arps=3)))
    k.append(("UFO", ins(d=0, s=14, r=20, v=12, vd=4, vs=60)))
    k.append(("TELEPH", ins(d=0, s=15, r=30, v=12, arp1=4, arps=2)))
    k.append(("GOUTTE", ins(d=30, s=0, r=30, v=12, slide=-4)))
    k.append(("RESSOR", ins(d=6, s=0, r=6, vd=6, vs=90)))
    k.append(("GAMEOV", ins(d=2, s=6, r=3, slide=1, vd=2, vs=16)))
    k.append(("POWRUP", ins(d=4, s=4, r=4, slide=-3, arp1=12, arps=2)))
    k.append(("WARP", ins(a=8, d=1, s=12, r=2, slide=-1, vd=3, vs=40)))
    k.append(("TIC", ins(d=120, s=0, r=120, v=11, f=TON | BRUIT, n=0)))
    return k


def buzzer():
    k = []
    for shape in (8, 10, 12, 14):                            # 4 formes
        for shift in (3, 4, 5):                               #  x 3 divisions
            k.append((f"BZ{shape}-{shift}", ins(d=0, s=15, r=255, f=ENV, shape=shape, shift=shift)))
    for shape in (8, 10, 12, 14):                            # avec le ton
        k.append((f"BT{shape}-4", ins(d=0, s=15, r=255, f=TON | ENV, shape=shape, shift=4)))
    k.append(("BZVIB", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=4, vd=1, vs=32, vdel=10)))
    k.append(("BZVIB2", ins(d=0, s=15, r=255, f=ENV, shape=8, shift=4, vd=2, vs=24)))
    k.append(("BZARMA", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=4, arp1=4, arp2=7, arps=1)))
    k.append(("BZARMI", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=4, arp1=3, arp2=7, arps=1)))
    k.append(("BZOCT", ins(d=0, s=15, r=255, f=ENV, shape=8, shift=4, arp1=12, arps=1)))
    k.append(("BZGLI", ins(d=0, s=15, r=255, f=ENV | PORTA, shape=10, shift=4, slide=8)))
    k.append(("BZMONT", ins(d=0, s=15, r=255, f=ENV, shape=8, shift=4, slide=-2)))
    k.append(("BZDESC", ins(d=0, s=15, r=255, f=ENV, shape=8, shift=4, slide=3)))
    k.append(("BZBRUI", ins(d=0, s=15, r=255, f=BRUIT | ENV, shape=8, shift=3, n=10)))
    k.append(("BZBRU2", ins(d=0, s=15, r=255, f=BRUIT | ENV, shape=12, shift=6, n=31)))
    k.append(("BZPERC", ins(d=0, s=15, r=255, f=ENV, shape=0, shift=4)))
    k.append(("BZPRC2", ins(d=0, s=15, r=255, f=TON | ENV, shape=9, shift=5, slide=6)))
    k.append(("BZTRIL", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=4, arp1=1, arps=1)))
    k.append(("BZ5TE", ins(d=0, s=15, r=255, f=ENV, shape=14, shift=4, arp1=7, arps=2)))
    k.append(("BZGRAV", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=6)))
    k.append(("BZAIGU", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=2)))
    return k


def claviers():
    k = []
    k.append(("PIANO", ins(d=10, s=4, r=10)))
    k.append(("PIANO2", ins(d=6, s=6, r=8, arp1=12, arps=1, v=14)))
    k.append(("EPIANO", ins(d=6, s=5, r=8, vd=1, vs=40)))
    k.append(("CLAVEC", ins(d=14, s=2, r=14, arp1=12, arps=1)))
    k.append(("PLUCK", ins(d=10, s=0, r=10)))
    k.append(("PLUCK2", ins(d=16, s=0, r=16, slide=1)))
    k.append(("GUITAR", ins(d=8, s=3, r=10, slide=1)))
    k.append(("GUIT2", ins(d=8, s=3, r=10, f=TON | BRUIT, n=28)))
    k.append(("HARPE", ins(d=6, s=0, r=6, arp1=12, arps=2)))
    k.append(("KOTO", ins(d=10, s=2, r=10, vd=1, vs=64, vdel=6)))
    k.append(("BANJO", ins(d=24, s=0, r=24, arp1=12, arps=1)))
    k.append(("CLOCHE", ins(d=4, s=0, r=4, arp1=7, arp2=12, arps=1)))
    k.append(("CLOCH2", ins(d=3, s=0, r=3, arp1=19, arps=1)))
    k.append(("CARILL", ins(d=5, s=0, r=5, arp1=12, arp2=24, arps=1)))
    k.append(("GLOCK", ins(d=12, s=0, r=12, v=13, arp1=24, arps=1)))
    k.append(("XYLO", ins(d=30, s=0, r=30, arp1=12, arps=1)))
    k.append(("MARIMB", ins(d=20, s=0, r=20)))
    k.append(("VIBRAP", ins(d=6, s=0, r=6, vd=1, vs=48)))
    k.append(("BOITE", ins(d=8, s=0, r=8, v=12, arp1=12, arp2=19, arps=1)))
    k.append(("ORGUE", ins(a=255, d=0, s=15, r=60, v=13)))
    k.append(("ORGBAR", ins(a=255, d=0, s=15, r=60, v=13, arp1=12, arp2=19, arps=1)))
    k.append(("ORGVIB", ins(a=255, d=0, s=15, r=60, v=13, vd=1, vs=48)))
    k.append(("ORGPER", ins(a=255, d=20, s=10, r=40, v=13, arp1=12, arps=1)))
    k.append(("ORGEGL", ins(a=255, d=0, s=15, r=8, v=12, arp1=12, arp2=7, arps=1, vd=1, vs=24)))
    k.append(("ACCORD", ins(a=60, d=0, s=14, r=20, v=12, vd=1, vs=56)))
    k.append(("HARMON", ins(a=30, d=2, s=13, r=12, v=12, vd=1, vs=40, vdel=8)))
    k.append(("CLAVI", ins(d=40, s=4, r=30, f=TON | BRUIT, n=0)))
    k.append(("SYNBRS", ins(a=20, d=4, s=12, r=10, v=14)))
    k.append(("CUIVRE", ins(a=12, d=4, s=12, r=10, v=14, vd=1, vs=32, vdel=16)))
    k.append(("FLUTE", ins(a=16, d=2, s=12, r=8, v=12, vd=1, vs=32, vdel=10)))
    k.append(("HAUTBO", ins(a=20, d=2, s=12, r=8, v=12, f=TON | BRUIT, n=31, vd=1, vs=36)))
    k.append(("OCARIN", ins(a=8, d=2, s=12, r=6, v=11, vd=1, vs=24)))
    return k


def chiptune():
    k = []
    k.append(("CHIP1", ins(d=4, s=12, r=8)))
    k.append(("CHIP2", ins(d=12, s=8, r=12)))
    k.append(("CHIPCR", ins(d=40, s=0, r=40)))
    k.append(("ECHO", ins(d=3, s=6, r=3)))
    k.append(("ARPMAJ", ins(d=4, s=12, r=8, arp1=4, arp2=7, arps=1)))
    k.append(("ARPMIN", ins(d=4, s=12, r=8, arp1=3, arp2=7, arps=1)))
    k.append(("ARPOCT", ins(d=4, s=12, r=8, arp1=12, arps=1)))
    k.append(("VIBRAT", ins(d=4, s=12, r=8, vd=2, vs=32, vdel=12)))
    k.append(("LEADGL", ins(d=4, s=12, r=8, f=TON | PORTA, slide=10)))
    k.append(("BASSE", ins(d=12, s=10, r=16)))
    k.append(("BASSBZ", ins(d=0, s=15, r=255, f=ENV, shape=8, shift=4)))
    k.append(("BASSAR", ins(d=8, s=10, r=12, arp1=12, arps=2)))
    k.append(("KICK", ins(d=28, s=0, r=28, slide=24)))
    k.append(("SNARE", ins(d=20, s=0, r=20, f=TON | BRUIT, n=10, slide=8)))
    k.append(("HAT", ins(d=48, s=0, r=48, v=12, f=BRUIT, n=1)))
    k.append(("HATOUV", ins(d=10, s=0, r=10, v=12, f=BRUIT, n=1)))
    k.append(("TOM", ins(d=14, s=0, r=14, slide=6)))
    k.append(("CLAP", ins(d=30, s=0, r=30, f=BRUIT, n=6, arp1=12, arps=1)))
    k.append(("CRASH", ins(d=3, s=0, r=3, v=13, f=BRUIT, n=2)))
    k.append(("PIECE", ins(d=10, s=0, r=10, arp1=5, arp2=12, arps=2)))
    k.append(("SAUT", ins(d=10, s=0, r=10, slide=-6)))
    k.append(("LASER", ins(d=9, s=0, r=9, slide=6)))
    k.append(("DOUX", ins(a=20, d=2, s=11, r=6, v=12)))
    k.append(("NAPPE", ins(a=4, d=2, s=12, r=3, v=12, vd=1, vs=24)))
    k.append(("CLOCHE", ins(d=4, s=0, r=4, arp1=7, arp2=12, arps=1)))
    k.append(("ORGUE", ins(a=255, d=0, s=15, r=40, v=12, arp1=12, arps=1)))
    k.append(("SYNC", ins(d=0, s=15, r=10, f=TON | ENV, shape=10, shift=2)))
    k.append(("BUZLD", ins(d=0, s=15, r=255, f=ENV, shape=10, shift=4, vd=1, vs=32, vdel=10)))
    k.append(("TRILLE", ins(d=4, s=12, r=8, arp1=2, arps=2)))
    k.append(("SALE", ins(d=4, s=11, r=8, f=TON | BRUIT, n=16)))
    k.append(("PLUCK", ins(d=10, s=0, r=10)))
    k.append(("STAB", ins(d=40, s=6, r=30, arp1=4, arp2=7, arps=1)))
    return k


def percus():
    k = []
    k.append(("CONGA1", ins(d=20, s=0, r=20, slide=2)))
    k.append(("CONGA2", ins(d=16, s=0, r=16, slide=3)))
    k.append(("CONGAM", ins(d=50, s=0, r=50, slide=1)))
    k.append(("BONGO1", ins(d=26, s=0, r=26, slide=1)))
    k.append(("BONGO2", ins(d=22, s=0, r=22, slide=2)))
    k.append(("TIMBAL", ins(d=16, s=0, r=16, f=TON | BRUIT, n=4, slide=1)))
    k.append(("TIMBA2", ins(d=10, s=0, r=10, f=TON | BRUIT, n=6)))
    k.append(("CLAVES", ins(d=70, s=0, r=70, slide=-2)))
    k.append(("BLOC1", ins(d=50, s=0, r=50, f=TON | BRUIT, n=0, slide=2)))
    k.append(("BLOC2", ins(d=60, s=0, r=60, slide=-1)))
    k.append(("TRIANG", ins(d=3, s=0, r=3, v=11, arp1=24, arps=1)))
    k.append(("TRIAN2", ins(d=12, s=0, r=12, v=11, arp1=24, arps=1)))
    k.append(("TAMBOU", ins(d=14, s=0, r=14, v=12, f=BRUIT, n=1)))
    k.append(("TAMBO2", ins(d=10, s=0, r=10, v=12, f=TON | BRUIT, n=1, arp1=12, arps=1)))
    k.append(("MARACA", ins(a=80, d=50, s=0, r=50, v=10, f=BRUIT, n=0)))
    k.append(("GUIRO", ins(d=12, s=0, r=12, v=11, f=BRUIT, n=3, arp1=1, arps=1)))
    k.append(("CABASA", ins(a=60, d=30, s=0, r=30, v=10, f=BRUIT, n=1)))
    k.append(("AGOGO1", ins(d=14, s=0, r=14, arp1=7, arps=1)))
    k.append(("AGOGO2", ins(d=14, s=0, r=14, arp1=5, arps=1)))
    k.append(("COWBEL", ins(d=14, s=0, r=14, arp1=7, arps=1)))
    k.append(("TABLA", ins(d=12, s=0, r=12, slide=-2)))
    k.append(("TABLA2", ins(d=8, s=0, r=8, slide=-4, vd=1, vs=64)))
    k.append(("DJEMBE", ins(d=18, s=0, r=18, f=TON | BRUIT, n=24, slide=3)))
    k.append(("TAIKO", ins(d=6, s=0, r=6, f=TON | BRUIT, n=31, slide=4)))
    k.append(("TIMPAN", ins(d=4, s=0, r=4, slide=1, vd=1, vs=20)))
    k.append(("GONG", ins(d=1, s=0, r=1, f=TON | BRUIT, n=31, vd=1, vs=8)))
    k.append(("STEELD", ins(d=8, s=0, r=8, arp1=12, arp2=19, arps=2)))
    k.append(("KALIMB", ins(d=14, s=0, r=14, arp1=12, arps=1, v=13)))
    k.append(("CLAQUE", ins(d=30, s=0, r=30, f=BRUIT, n=8)))
    k.append(("DOIGTS", ins(d=60, s=0, r=60, v=12, f=TON | BRUIT, n=2)))
    k.append(("CASTAG", ins(d=50, s=0, r=50, f=BRUIT, n=0, arp1=12, arps=1)))
    k.append(("SURDO", ins(d=6, s=0, r=6, slide=6)))
    return k


def glisses():
    k = []
    for i, sl in enumerate((2, 4, 6, 10, 16, 24)):           # portamentos
        k.append((f"PORT{i + 1}", ins(d=4, s=13, r=8, f=TON | PORTA, slide=sl)))
    for i, sl in enumerate((1, 2, 4, 8)):                     # le son descend
        k.append((f"DESC{i + 1}", ins(d=4, s=13, r=8, slide=sl)))
    for i, sl in enumerate((1, 2, 4, 8)):                     # le son monte
        k.append((f"MONT{i + 1}", ins(d=4, s=13, r=8, slide=-sl)))
    k.append(("PRTVIB", ins(d=4, s=13, r=8, f=TON | PORTA, slide=6, vd=1, vs=32, vdel=12)))
    k.append(("PRTBZ", ins(d=0, s=15, r=255, f=ENV | PORTA, shape=10, shift=4, slide=8)))
    k.append(("PRTBAS", ins(d=6, s=12, r=12, f=TON | PORTA, slide=12)))
    k.append(("PRTDOU", ins(a=16, d=2, s=12, r=6, v=12, f=TON | PORTA, slide=4)))
    k.append(("PRTOCT", ins(d=4, s=13, r=8, f=TON | PORTA, slide=8, arp1=12, arps=2)))
    k.append(("PRTSAL", ins(d=4, s=12, r=8, f=TON | BRUIT | PORTA, n=18, slide=8)))
    k.append(("DIVE", ins(d=3, s=4, r=3, slide=6)))
    k.append(("PLONGE", ins(d=6, s=0, r=6, slide=12)))
    k.append(("FUSEE", ins(d=4, s=0, r=4, slide=-10)))
    k.append(("SIRENA", ins(d=0, s=15, r=10, v=13, vd=6, vs=4)))
    k.append(("YOYO", ins(d=0, s=15, r=10, v=13, vd=4, vs=12)))
    k.append(("GUITSL", ins(d=8, s=6, r=10, slide=-1, vd=1, vs=48, vdel=20)))
    k.append(("BASSLI", ins(d=8, s=10, r=12, slide=1)))
    k.append(("ZIP", ins(d=20, s=0, r=20, slide=-20)))
    k.append(("ZOUP", ins(d=20, s=0, r=20, slide=20)))
    k.append(("THEREM", ins(a=10, d=1, s=13, r=4, v=12, f=TON | PORTA, slide=3, vd=2, vs=40)))
    k.append(("SCIE", ins(d=0, s=15, r=10, v=12, f=TON | ENV, shape=8, shift=2, slide=-1)))
    k.append(("CHUTE", ins(d=2, s=0, r=2, slide=3)))
    return k


def bruits():
    k = []
    for n in (0, 2, 4, 8, 12, 16, 20, 24, 28, 31):           # bruit tenu, du plus aigu
        k.append((f"BR{n:02d}", ins(d=0, s=15, r=20, v=12, f=BRUIT, n=n)))
    k.append(("SOUFLE", ins(a=4, d=1, s=10, r=2, v=11, f=BRUIT, n=0)))
    k.append(("VENT", ins(a=2, d=1, s=10, r=1, v=10, f=BRUIT, n=20)))
    k.append(("PLUIE", ins(a=255, d=0, s=9, r=4, v=10, f=BRUIT, n=1)))
    k.append(("MER", ins(a=2, d=2, s=6, r=2, v=11, f=BRUIT, n=10, vd=0)))
    k.append(("TONNER", ins(a=40, d=2, s=0, r=2, v=15, f=BRUIT, n=31)))
    k.append(("FEU", ins(a=255, d=0, s=10, r=4, v=10, f=BRUIT, n=14)))
    k.append(("STATIC", ins(a=255, d=0, s=12, r=4, v=11, f=TON | BRUIT, n=0)))
    k.append(("RADIO", ins(a=255, d=0, s=12, r=4, v=11, f=TON | BRUIT, n=6, vd=3, vs=60)))
    k.append(("TRAIN", ins(d=0, s=15, r=20, f=BRUIT | ENV, shape=8, shift=7, n=12)))
    k.append(("LOCO", ins(d=0, s=15, r=20, f=BRUIT | ENV, shape=12, shift=7, n=20)))
    k.append(("VAPEUR", ins(a=60, d=8, s=4, r=6, v=11, f=BRUIT, n=0)))
    k.append(("PSHHH", ins(d=6, s=0, r=6, v=12, f=BRUIT, n=0)))
    k.append(("TCHAK", ins(d=40, s=0, r=40, f=BRUIT, n=4)))
    k.append(("GRAVIE", ins(d=20, s=0, r=20, f=BRUIT, n=24)))
    k.append(("BRTON1", ins(d=8, s=10, r=10, f=TON | BRUIT, n=31)))
    k.append(("BRTON2", ins(d=8, s=10, r=10, f=TON | BRUIT, n=12)))
    k.append(("BRTON3", ins(d=8, s=10, r=10, f=TON | BRUIT, n=2)))
    k.append(("BRARP", ins(d=0, s=15, r=20, f=TON | BRUIT, n=8, arp1=12, arps=1)))
    k.append(("BRBUZ", ins(d=0, s=15, r=255, f=BRUIT | ENV, shape=10, shift=4, n=6)))
    k.append(("BRBUZ2", ins(d=0, s=15, r=255, f=BRUIT | ENV, shape=14, shift=5, n=16)))
    k.append(("GRESIL", ins(a=255, d=0, s=11, r=6, v=10, f=BRUIT, n=3, vd=2, vs=80)))
    k.append(("SOURD", ins(a=8, d=2, s=8, r=4, v=12, f=BRUIT, n=31)))
    return k


BANKS = [
    ("USINE", usine, "les 32 instruments par défaut du programme"),
    ("BATTERIE", batterie, "grosses caisses, caisses claires, charlestons, toms, cymbales"),
    ("BASSES", basses, "basses courtes, longues, glissées, « buzzer », sales"),
    ("LEADS", leads, "sons de mélodie : vibratos, portamentos, sync, trilles"),
    ("NAPPES", nappes, "nappes lentes, accords tenus, choeurs, orgues"),
    ("ARPEGES", arpeges, "accords arpégés à 3 vitesses : majeur, mineur, 7e, sus..."),
    ("EFFETS", effets, "lasers, sirènes, pièces, sauts, explosions, moteurs"),
    ("BUZZER", buzzer, "l'enveloppe matérielle : 4 formes x 3 divisions, et variantes"),
    ("CLAVIERS", claviers, "pianos, cordes pincées, cloches, orgues, vents"),
    ("CHIPTUNE", chiptune, "une banque complète pour un morceau de jeu vidéo"),
    ("PERCUS", percus, "congas, bongos, claves, triangle, tablas, gong"),
    ("GLISSES", glisses, "portamentos, glissandos vers le haut ou le bas"),
    ("BRUITS", bruits, "bruit tenu à 10 hauteurs, vent, pluie, mer, train"),
]


def all_banks():
    """[(nom de fichier, description, données .INS)] pour toutes les banques."""
    out = []
    for name, make, desc in BANKS:
        sounds = make()
        if len(sounds) != 32:
            raise ValueError(f"{name} : {len(sounds)} sons au lieu de 32")
        names = [insbank.clean_name(n) for n, _ in sounds]
        if len(set(names)) != 32:
            dup = sorted({n for n in names if names.count(n) > 1})
            raise ValueError(f"{name} : noms en double {dup}")
        out.append((name + ".INS", desc, insbank.build_ins_bank(sounds)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dsk", nargs="?", const=os.path.join(ROOT, "build", "seq16-fr.dsk"),
                    help="ajoute aussi les banques à cette disquette (build/seq16-fr.dsk par défaut)")
    ap.add_argument("--list", action="store_true", help="affiche les sons de chaque banque")
    a = ap.parse_args(argv)
    os.makedirs(OUT_DIR, exist_ok=True)
    banks = all_banks()
    for fname, desc, data in banks:
        open(os.path.join(OUT_DIR, fname), "wb").write(data)
        print(f"{fname:13s} {desc}")
        if a.list:
            sounds, _ = insbank.parse_ins_bank(data)
            for i in range(0, 32, 8):
                print("   " + " ".join(f"{j + 1:02d} {sounds[j][0]}" for j in range(i, i + 8)))
    if a.dsk:
        import amsdsk
        for fname, _, data in banks:
            amsdsk.add_file(a.dsk, fname, data)
        print(f"{len(banks)} banques ajoutées à {a.dsk}")
    print(f"{len(banks)} banques, {32 * len(banks)} sons, dans {OUT_DIR}")


if __name__ == "__main__":
    main()
