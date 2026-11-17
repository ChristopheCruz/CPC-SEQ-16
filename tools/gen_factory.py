"""Génère src/factory.asm : le contenu d'usine d'un morceau.

Ce contenu est recopié dans le morceau au démarrage :
  - l'en-tête (signature, volumes des 4 voix),
  - 32 instruments (24 préréglés, 4 libres, 4 digidrums) et leurs noms,
  - 8 sons composés,
  - 2 motifs de démonstration, rangés case par case (seules les cases non
    vides sont gardées : init_song remplit d'abord tous les motifs de cases
    vides).  Cela économise environ 400 octets de mémoire.
"""
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def note(s):                       # "C#3" -> numéro de note
    return 12 * int(s[-1]) + NAMES.index(s[:-1])

TON, BRUIT, EG, PORTA, DIGI = 1, 2, 4, 8, 16   # DIGI : digidrum (sample)
# nom, attaque, déclin, tenue, relâche, volume, drapeaux, bruit,
#      forme EG, division EG, arp2, arp3, vitesse arp,
#      vibrato prof., vitesse, attente, glissando
INSTRUMENTS = [
    ("LEAD",   255,  8, 10, 12, 15, TON,        0,  0, 0,   0,  0, 0,  0,  0,  0,   0),
    ("BASS",   255, 16, 12, 24, 15, TON,        0,  0, 0,   0,  0, 0,  0,  0,  0,   0),
    ("PAD",      6,  2, 12,  4, 13, TON,        0,  0, 0,   0,  0, 0,  0,  0,  0,   0),
    ("PLUCK",  255, 10,  0, 10, 15, TON,        0,  0, 0,   0,  0, 0,  0,  0,  0,   0),
    ("HAT",    255, 48,  0, 48, 12, BRUIT,      1,  0, 0,   0,  0, 0,  0,  0,  0,   0),
    ("SNARE",  255, 20,  0, 20, 15, TON+BRUIT, 10,  0, 0,   0,  0, 0,  0,  0,  0,   0),
    ("BUZZ",   255,  0, 15,255, 15, EG,         0,  8, 4,   0,  0, 0,  0,  0,  0,   0),
    ("ARP",    255,  8, 11, 12, 15, TON,        0,  0, 0,   4,  7, 2,  0,  0,  0,   0),
    ("VIBRA",  255,  8, 12, 10, 15, TON,        0,  0, 0,   0,  0, 0,  3, 32, 15,   0),
    ("LASER",  255,  9,  0,  9, 15, TON,        0,  0, 0,   0,  0, 0,  0,  0,  0,   6),
    ("PORTA",  255,  4, 13,  4, 15, TON+PORTA,  0,  0, 0,   0,  0, 0,  0,  0,  0,   8),
    ("KICK",   255, 28,  0, 28, 15, TON,        0,  0, 0,   0,  0, 0,  0,  0,  0,  24),
    ("TOM",    255, 14,  0, 14, 15, TON,        0,  0, 0,   0,  0, 0,  0,  0,  0,   5),
    ("CLAP",   255, 30,  0, 30, 15, BRUIT,      6,  0, 0,   0,  0, 0,  0,  0,  0,   0),
    ("ORGAN",  255,  0, 15, 40, 13, TON,        0,  0, 0,  12,  0, 1,  0,  0,  0,   0),
    ("BELL",   255,  4,  0,  4, 15, TON,        0,  0, 0,   7, 12, 1,  0,  0,  0,   0),
    ("ARPMIN", 255,  8, 11, 12, 15, TON,        0,  0, 0,   3,  7, 2,  0,  0,  0,   0),
    ("ZAP",    255, 12,  0, 12, 15, TON,        0,  0, 0,   0,  0, 0,  0,  0,  0,  -8),
    ("SIREN",  255,  0, 15, 20, 13, TON,        0,  0, 0,   0,  0, 0,  6,  8,  0,   0),
    ("BUZZTR", 255,  0, 15,255, 15, EG,         0, 10, 5,   0,  0, 0,  0,  0,  0,   0),
    ("SOFT",    40,  4,  9,  8, 12, TON,        0,  0, 0,   0,  0, 0,  0,  0,  0,   0),
    ("STAB",   255, 40,  6, 30, 15, TON,        0,  0, 0,   0,  0, 0,  0,  0,  0,   0),
    ("CYMBAL", 255,  4,  0,  4, 13, BRUIT,      2,  0, 0,   0,  0, 0,  0,  0,  0,   0),
    ("WOBBLE", 255,  0, 15, 20, 14, TON,        0,  0, 0,   0,  0, 0,  5, 20,  0,   0),
]
while len(INSTRUMENTS) < 28:       # instruments libres : une copie de LEAD
    n = len(INSTRUMENTS) - 23
    INSTRUMENTS.append(("USER%d" % n,) + INSTRUMENTS[0][1:])
# Digidrums : ils jouent les samples 0 à 3 de la banque chargée (DRUMS.SMP
# par défaut : KICK, SNARE, HAT, CLAP).  L'octet du bruit donne le numéro
# du sample, le volume règle la force ; le reste ne sert pas.
for n, name in enumerate(("DGKICK", "DGSNAR", "DGHAT", "DGCLAP")):
    INSTRUMENTS.append((name, 255, 8, 10, 12, 15, DIGI, n, 0, 0, 0, 0, 0, 0, 0, 0, 0))
I = {ins[0]: i for i, ins in enumerate(INSTRUMENTS)}

X = None                           # voix non utilisée
# Sons composés : (décalage, instrument) pour A, B, C ; (période, instrument) pour le bruit
SONS = [
    ("accord mineur",       (0, "LEAD"), (3, "LEAD"),  (7, "LEAD"),  X),
    ("accord majeur",       (0, "LEAD"), (4, "LEAD"),  (7, "LEAD"),  X),
    ("basse + percussion",  (0, "BASS"), (12, "PLUCK"), X,           (12, "SNARE")),
    ("quinte + octave",     (0, "LEAD"), (7, "LEAD"),  (12, "LEAD"), X),
    ("trois octaves",       (0, "BASS"), (12, "LEAD"), (24, "PLUCK"), X),
    ("accord sus4",         (0, "PAD"),  (5, "PAD"),   (7, "PAD"),   X),
    ("accord mineur 7",     (0, "SOFT"), (3, "SOFT"),  (10, "SOFT"), X),
    ("grosse caisse + hat", (0, "KICK"), X,            X,            (1, "HAT")),
]

OFF = "off"
def pattern(p, mode, bpm, lanes, comment):
    """Les cases non vides du motif p : (p x 64 + pas x 4 + voix, note, instr.)
    plus une fiche d'en-tête (#80 + p, mode, tempo)."""
    out = ["", "; " + comment, "        db #%02X,%d,%d   ; en-tête : mode, tempo" % (0x80 + p, mode, bpm)]
    for step in range(16):
        for lane in range(4):
            ev = lanes[lane].get(step) if lane < len(lanes) else None
            if ev is None:
                continue
            if ev == OFF:
                n, ins = 0xFE, 0
            else:
                n, ins = ev
                n = note(n) if isinstance(n, str) else n
                ins = I[ins] if isinstance(ins, str) else ins
            out.append("        db %3d,%3d,%3d   ; pas %X, voix %d" % (p * 64 + step * 4 + lane, n, ins, step, lane))
    return out

# --- le bloc d'usine (en-tête, instruments, noms, sons composés) ------------
block = bytearray(b"SQ16" + bytes([2, 15, 15, 15, 15, 0, 0, 0, 0, 0, 0, 0]))
for ins in INSTRUMENTS:
    block += bytes(v & 255 for v in ins[1:])
for ins in INSTRUMENTS:
    block += (ins[0] + "      ")[:6].encode("ascii")
for name, *voices in SONS:
    for v in voices:
        block += bytes([0, 0xFF, 0xFF]) if v is None else bytes([v[0], I[v[1]], 0xFF])
    block += bytes(4)
assert len(block) == 848

def rle_zeros(data):
    """Compression des suites de zéros : 0, n = n zéros (1 à 255) ; 0, 0 = fin."""
    out, i = bytearray(), 0
    while i < len(data):
        if data[i] == 0:
            j = i
            while j < len(data) and data[j] == 0 and j - i < 255:
                j += 1
            out += bytes([0, j - i])
            i = j
        else:
            out.append(data[i])
            i += 1
    return bytes(out + b"\0\0")

rle = rle_zeros(block)
out = ["; Fichier généré par tools/gen_factory.py - ne pas modifier à la main.",
       "; Contenu d'usine du morceau, recopié en mémoire au démarrage.",
       "; L'ordre et les tailles doivent suivre le bloc 'morceau' de song.asm.", "",
       "; Le bloc d'usine (848 octets : en-tête, instruments, noms, sons composés)",
       "; est compressé : 0, n = n zéros ; 0, 0 = fin (%d octets au lieu de 848)." % len(rle),
       "; Pour mémoire, les instruments :"]
for i, ins in enumerate(INSTRUMENTS):
    vals = [v & 255 for v in ins[1:]]
    out.append(";       db " + ",".join("%3d" % v for v in vals) + "   ; %2d %s" % (i + 1, ins[0]))
out += ["", "factory_rle:"]
for i in range(0, len(rle), 16):
    out.append("        db " + ",".join("#%02X" % v for v in rle[i:i + 16]))

bass = {0: ("C2", "BASS"), 1: OFF, 3: ("C2", "BASS"), 4: OFF, 6: ("D#2", "BASS"), 7: OFF,
        8: ("C2", "BASS"), 9: OFF, 11: ("F2", "BASS"), 12: OFF, 14: ("G2", "BASS"), 15: OFF}
lead = {0: ("C4", "LEAD"), 2: ("D#4", "LEAD"), 3: ("G4", "LEAD"), 6: ("A#4", "LEAD"),
        8: ("G4", "LEAD"), 11: ("F4", "LEAD"), 12: ("D#4", "LEAD"), 14: ("D4", "LEAD")}
pluck = {2: ("G3", "PLUCK"), 6: ("G3", "PLUCK"), 10: ("G#3", "PLUCK"), 14: ("G3", "PLUCK")}
drums = {0: (31, "SNARE"), 2: (1, "HAT"), 4: (12, "SNARE"), 6: (1, "HAT"),
         8: (31, "SNARE"), 10: (1, "HAT"), 12: (12, "SNARE"), 14: (1, "HAT")}
comp = {0: ("C3", 0), 3: OFF, 4: ("C3", 2), 6: ("D#3", 1), 7: OFF, 8: ("F3", 0),
        11: OFF, 12: ("G3", 1), 14: ("G3", 2), 15: OFF}
out += ["", "; Les 2 motifs de démonstration, case par case : numéro de case",
        "; (motif x 64 + pas x 4 + voix), note, instrument ; volume #FF, effet 0.",
        "; #80 + motif : en-tête (mode, tempo).  #FF : fin.",
        "factory_cells:"]
out += pattern(0, 0, 125, [bass, lead, pluck, drums], "Motif 1 : voix séparées")
out += pattern(1, 1, 125, [comp], "Motif 2 : son composé")
out += ["        db #FF", ""]
open("src/factory.asm", "w", encoding="utf-8").write("\n".join(out))
print("src/factory.asm écrit :", len(INSTRUMENTS), "instruments,", len(SONS), "sons composés")
