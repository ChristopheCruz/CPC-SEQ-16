"""gen_patterns.py : la bibliothèque de motifs d'usine (.PAT).

Fabrique environ 60 motifs « mono » (mode son composé) et 60 motifs
« poly » (mode voix séparées), chargeables avec f3 P :

    patterns/mono/*.PAT          fichiers bruts de 260 octets (sans en-tête
    patterns/poly/*.PAT          AMSDOS : la bibliothèque disque l'ajoute)
    patterns/LISTE.md            la liste des motifs, par disquette
    build/seq16-motifs-mono.dsk  disquette de données : les motifs mono
    build/seq16-motifs-poly.dsk  disquette de données : les motifs poly

    python tools/gen_patterns.py

Format d'un motif (voir src/seq.asm) : mode, tempo, 0, 0, puis 16 pas de
4 cases (A, B, C, bruit) de 4 octets : note, instrument, volume, effet.
Les motifs utilisent les instruments et les sons composés d'usine
(tools/gen_factory.py, = instruments/USINE.INS).

Les motifs sont écrits avec un petit langage :
  R("x.x-x...", "A2 C3 E3", "BASS")   rythme + notes : x = note suivante,
        X = accentuée (volume 15), v = douce (10), w = très douce (6),
        . = la note continue, - = arrêt de la note ; les notes tournent.
  L("A2 . C3 - K . E3@PLUCK!9 -")     16 jetons : note[@instrument][!volume],
        . = continue, - = arrêt, ou un nom de la batterie (K, S, T...).
  G("x...x...x...x...", NK)           grille de batterie : un caractère par pas.
En mode son composé, l'« instrument » est le numéro du son (0 à 7) : C3@4.

Chaque motif est vérifié (sinon le script s'arrête) : notes dans la gamme
annoncée (y compris les notes ajoutées par les arpèges des instruments et
par les sons composés), tessiture de chaque instrument, pas de demi-ton
frottant entre deux voix sur un temps fort, pas de note tenue sans fin.
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)


# --- le contenu d'usine (instruments, sons composés) ---------------------------
def _factory():
    """Lit les définitions de gen_factory.py sans exécuter la partie qui écrit
    src/factory.asm (tout ce qui précède « le bloc d'usine »)."""
    path = os.path.join(HERE, "gen_factory.py")
    src = open(path, encoding="utf-8").read()
    cut = src.index("# --- le bloc d'usine")
    ns = {}
    exec(compile(src[:cut], path, "exec"), ns)
    return ns


_F = _factory()
INSTRUMENTS = _F["INSTRUMENTS"]
I = _F["I"]                                # nom -> numéro d'instrument
SONS = _F["SONS"]
NAMES = _F["NAMES"]
TON, BRUIT, EG, DIGI = _F["TON"], _F["BRUIT"], _F["EG"], _F["DIGI"]
assert len(INSTRUMENTS) == 32 and len(SONS) == 8

PAT_SIZE = 260
NOTE_NONE, NOTE_OFF = 0xFF, 0xFE
MONO, POLY = 1, 0                          # octet 0 du motif


def ins_field(name, k):
    """Champ k d'un instrument : 1 attaque, 2 déclin, 3 tenue, 6 drapeaux,
    10/11 arpège."""
    return INSTRUMENTS[I[name]][k]


# Instruments qui ne jouent pas une hauteur « musicale » (batterie, bruitages)
UNPITCHED = {"KICK", "TOM", "SNARE", "HAT", "CLAP", "CYMBAL", "LASER", "ZAP",
             "SIREN", "DGKICK", "DGSNAR", "DGHAT", "DGCLAP"}
# Instruments d'accompagnement : jamais de frottement, même sur un pas faible
CHORDY = {"PAD", "ARP", "ARPMIN", "ORGAN", "STAB", "SOFT"}
BASSY = {"BASS", "BUZZ", "BUZZTR", "WOBBLE"}
MELODIC = {"LEAD", "VIBRA", "BELL"}
RANGES = {}                                # tessiture (notes 0-95) par instrument
for _n in BASSY:
    RANGES[_n] = (24, 52)                  # C2 - E4
for _n in CHORDY:
    RANGES[_n] = (40, 79)                  # E3 - G6
for _n in MELODIC:
    RANGES[_n] = (36, 88)                  # C3 - E7
RANGES.update({"PLUCK": (33, 84), "PORTA": (24, 84),
               "KICK": (33, 62), "TOM": (33, 62), "SNARE": (36, 62),
               "HAT": (36, 84), "CLAP": (36, 84), "CYMBAL": (36, 84),
               "LASER": (48, 84), "ZAP": (48, 84), "SIREN": (48, 84),
               "DGKICK": (36, 60), "DGSNAR": (36, 60), "DGHAT": (36, 60),
               "DGCLAP": (36, 60)})
NOISE_INS = {"HAT", "SNARE", "CLAP", "CYMBAL", "KICK", "TOM"}


def pitched(name):
    return name not in UNPITCHED


def implied(name):
    """Les intervalles joués par une note de cet instrument (arpège)."""
    a2, a3 = ins_field(name, 10), ins_field(name, 11)
    return [0] + [x for x in (a2, a3) if x]


def hold_steps(name, bpm):
    """Durée d'une note en pas : None = tenue jusqu'à l'arrêt."""
    if ins_field(name, 3) > 0:
        return None
    decay = max(ins_field(name, 2), 1)
    frames = 255 / decay
    return max(1, math.ceil(frames * bpm / 750))


# --- gammes ------------------------------------------------------------------
SCALES = {
    "maj": ("major", "majeur", "mayor", [0, 2, 4, 5, 7, 9, 11]),
    "min": ("minor", "mineur", "menor", [0, 2, 3, 5, 7, 8, 10]),
    "hmin": ("harmonic minor", "mineur harmonique", "menor armónica", [0, 2, 3, 5, 7, 8, 11]),
    "dor": ("dorian", "dorien", "dórico", [0, 2, 3, 5, 7, 9, 10]),
    "mix": ("mixolydian", "mixolydien", "mixolidio", [0, 2, 4, 5, 7, 9, 10]),
    "phr": ("phrygian", "phrygien", "frigio", [0, 1, 3, 5, 7, 8, 10]),
    "blues": ("blues", "blues", "blues", [0, 3, 4, 5, 6, 7, 9, 10]),
    "pentmaj": ("major pentatonic", "pentatonique majeure", "pentatónica mayor", [0, 2, 4, 7, 9]),
    "pentmin": ("minor pentatonic", "pentatonique mineure", "pentatónica menor", [0, 3, 5, 7, 10]),
}
FLATS = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
NOTE_RE = re.compile(r"^([A-G](?:#|b)?)(\d)$")


def pc_of(name):
    name = FLATS.get(name, name)
    return NAMES.index(name)


def parse_key(key):
    """'A:min', 'C:maj', 'A:min+G#' -> (texte, ensemble des classes de hauteur).
    None : motif sans hauteur (batterie seule)."""
    if key is None:
        return None
    base, _, extra = key.partition("+")
    root, scale = base.split(":")
    pcs = {(pc_of(root) + i) % 12 for i in SCALES[scale][3]}
    for e in filter(None, extra.split(",")):
        pcs.add(pc_of(e))
    return pcs


def key_text(key, lang=0):
    if key is None:
        return "-"
    base, _, extra = key.partition("+")
    root, scale = base.split(":")
    t = "%s %s" % (root, SCALES[scale][lang])
    return t + (" (+%s)" % extra if extra else "")


# --- le petit langage ----------------------------------------------------------
def note(s):
    """'C#3', 'Bb2' -> numéro de note (0 = C0)."""
    m = NOTE_RE.match(s)
    if not m:
        raise ValueError("note invalide : %r" % s)
    return 12 * int(m.group(2)) + pc_of(m.group(1))


OFF = "off"
# Batterie sur la voix de bruit : caractère -> (période du bruit, instrument, volume)
NK = {
    "h": (1, "HAT", 7), "H": (1, "HAT", 11),          # charleston fermé
    "o": (4, "CYMBAL", 8),                            # charleston ouvert
    "x": (2, "CYMBAL", 12),                           # crash
    "r": (1, "CYMBAL", 5),                            # ride
    "s": (12, "SNARE", 14), "S": (9, "SNARE", 15),    # caisse claire
    "q": (12, "SNARE", 9), "g": (12, "SNARE", 6),     # douce, fantôme
    "c": (6, "CLAP", 13),                             # clap
    "m": (3, "HAT", 13),                              # rimshot / clave
    "k": (31, "KICK", 15),                            # grosse caisse en bruit
}
# Batterie sur une voie de ton (A, B, C) : caractère -> (note, instrument, volume)
TK = {
    "K": ("A3", "KICK", 15), "k": ("A3", "KICK", 10),
    "S": ("G3", "SNARE", 14), "s": ("G3", "SNARE", 8),
    "T": ("D4", "TOM", 14), "M": ("A3", "TOM", 14), "L": ("E3", "TOM", 14),
    "C": ("C4", "CLAP", 12), "R": ("C5", "HAT", 12),
}
# Digidrums (samples de DRUMS.SMP) : C4 = hauteur d'origine
DK = {
    "K": ("C4", "DGKICK", 15), "S": ("C4", "DGSNAR", 15), "s": ("C4", "DGSNAR", 9),
    "H": ("C4", "DGHAT", 11), "C": ("C4", "DGCLAP", 15),
}
ACCENTS = {"x": None, "X": 15, "v": 10, "w": 6}


def _event(tok, ins, vol=None):
    """Un jeton -> événement (note, instrument, volume) ; '.' -> None ; '-' -> OFF."""
    if tok == ".":
        return None
    if tok == "-":
        return OFF
    if tok in TK and not NOTE_RE.match(tok):
        n, i, v = TK[tok]
        return (note(n), i, v)
    m = re.match(r"^([^@!]+)(?:@([A-Z0-9]+))?(?:!(\d+))?$", tok)
    if not m:
        raise ValueError("jeton invalide : %r" % tok)
    n = note(m.group(1))
    if m.group(2):
        ins = int(m.group(2)) if m.group(2).isdigit() else m.group(2)
    if m.group(3):
        vol = int(m.group(3))
    if ins is None:
        raise ValueError("instrument manquant : %r" % tok)
    return (n, ins, vol)


def _clean(s):
    return s.replace(" ", "").replace("|", "")


def L(s, ins=None):
    """16 jetons séparés par des espaces."""
    toks = s.replace("|", " ").split()
    if len(toks) != 16:
        raise ValueError("%d jetons au lieu de 16 : %r" % (len(toks), s))
    return [_event(t, ins) for t in toks]


def R(rhythm, notes, ins=None):
    """Rythme de 16 caractères + liste de notes (qui tourne)."""
    r = _clean(rhythm)
    if len(r) != 16:
        raise ValueError("rythme de %d pas : %r" % (len(r), rhythm))
    ns = notes.split()
    out, k = [], 0
    for ch in r:
        if ch == ".":
            out.append(None)
        elif ch == "-":
            out.append(OFF)
        elif ch in ACCENTS:
            out.append(_event(ns[k % len(ns)], ins, ACCENTS[ch]))
            k += 1
        else:
            raise ValueError("caractère de rythme inconnu %r" % ch)
    return out


def G(grid, kit):
    """Grille de batterie : un caractère par pas, cherché dans kit."""
    g = _clean(grid)
    if len(g) != 16:
        raise ValueError("grille de %d pas : %r" % (len(g), grid))
    out = []
    for ch in g:
        if ch == ".":
            out.append(None)
        elif ch == "-":
            out.append(OFF)
        else:
            n, i, v = kit[ch]
            out.append((note(n) if isinstance(n, str) else n, i, v))
    return out


def merge(*lanes):
    """Superpose des lignes sur une même voix (la dernière l'emporte)."""
    out = [None] * 16
    for lane in lanes:
        for s, ev in enumerate(lane):
            if ev is not None:
                out[s] = ev
    return out


# --- les motifs ----------------------------------------------------------------
PATTERNS = []


def mono(name, style, bpm, key, desc, lane):
    PATTERNS.append(dict(disk="mono", name=name, style=style, bpm=bpm, key=key,
                         desc=desc, mode=MONO, lanes=[lane, None, None, None]))


def poly(name, style, bpm, key, desc, A=None, B=None, C=None, N=None):
    PATTERNS.append(dict(disk="poly", name=name, style=style, bpm=bpm, key=key,
                         desc=desc, mode=POLY, lanes=[A, B, C, N]))


# Sons composés : 0 accord mineur, 1 accord majeur, 2 basse + percussion,
# 3 quinte + octave, 4 trois octaves, 5 accord sus4, 6 accord mineur 7,
# 7 grosse caisse + charleston (la note du pas donne la hauteur de la caisse).

# ---------------------------------------------------------------- MONO -------
mono("POPCHRD1", "synth-pop", 118, "C:maj",
     ("I-V-vi-IV pop chords (C G Am F)", "Accords pop I-V-vi-IV (do sol lam fa)",
      "Acordes pop I-V-vi-IV (do sol lam fa)"),
     R("x.x-x.x-x.x-x.x-", "C4@1 C4@1 G3@1 G3@1 A3@0 A3@0 F3@1 F3@1"))
mono("POPCHRD2", "synth-pop", 124, "G:maj",
     ("Syncopated pop chords G D Em C", "Accords pop syncopés sol ré mim do",
      "Acordes pop sincopados sol re mim do"),
     R("x..x..x-x..x..x-", "G3@1 G3@1 D4@1 E4@0 E4@0 C4@1"))
mono("REGGSKA1", "reggae", 90, "A:min",
     ("Offbeat skank chords Am-G", "Accords skank à contretemps lam-sol",
      "Acordes skank a contratiempo lam-sol"),
     R("..x-..x-..x-..x-", "A3@0 A3@0 G3@1 G3@1"))
mono("HOUSECH1", "house", 124, "D:dor",
     ("House m7 chord stabs on the offbeat", "Accords m7 house à contretemps",
      "Acordes m7 house a contratiempo"),
     R("..x-..x.-.x-.x-.", "D4@6 D4@6 D4@6 E4@6 A3@6"))
mono("LOFIM7", "lo-fi", 84, "A:min",
     ("Laid-back lo-fi chords Am7 Dm7 Em7 C", "Accords lo-fi nonchalants lam7 rém7 mim7 do",
      "Acordes lo-fi relajados lam7 rem7 mim7 do"),
     R("x..-..x-x..-..x-", "A3@6 D4@6 E4@6 C4@1"))
mono("SUSPAD1", "ambient", 80, "C:maj",
     ("Slow sus4 pads Dsus4-Gsus4", "Nappes sus4 lentes résus4-solsus4",
      "Colchones sus4 lentos resus4-solsus4"),
     R("x......-x......-", "D4@5 G3@5"))
mono("SUSPAD2", "ambient", 90, "A:min",
     ("Sus4 chords resolving to minor", "Accords sus4 qui se résolvent en mineur",
      "Acordes sus4 que resuelven a menor"),
     R("x...x..-x...x..-", "D4@5 D4@0 A3@5 A3@0"))
mono("TRANCEG1", "trance", 138, "A:min",
     ("Trance gated chords Am F C G", "Accords hachés trance lam fa do sol",
      "Acordes entrecortados trance lam fa do sol"),
     R("x-x-x-x-x-x-x-x-", "A3@0 A3@0 F3@1 F3@1 C4@1 C4@1 G3@1 G3@1"))
mono("TRANCEG2", "trance", 140, "E:min",
     ("Syncopated trance gate Em C G D", "Hachage trance syncopé mim do sol ré",
      "Entrecortado trance sincopado mim do sol re"),
     R("x.xx-xx-x.xx-xx-", "E4@0 E4@0 E4@0 C4@1 C4@1 G3@1 G3@1 G3@1 D4@1 D4@1"))
mono("TECHSTB1", "techno", 130, "F:min",
     ("Techno minor stabs Fm Cm Bbm", "Stabs techno mineurs fam dom sibm",
      "Stabs techno menores fam dom sibm"),
     R("x-.x-.x-..x-.x-.", "F3@0 F3@0 F3@0 C4@0 A#3@0"))
mono("DUBCHRD1", "dub techno", 120, "D:min",
     ("Sparse dub-techno m7 chords", "Accords m7 dub techno espacés",
      "Acordes m7 dub techno espaciados"),
     R("..x-....x-...x-.", "D4@6 D4@6 A3@6"))
mono("ARPMIN1", "arpeggio", 120, "A:min",
     ("16th arpeggios Am F C G, three octaves", "Arpèges en doubles croches lam fa do sol, trois octaves",
      "Arpegios en semicorcheas lam fa do sol, tres octavas"),
     R("xxxxxxxxxxxxxxx-", "A2 C3 E3 C3 F2 A2 C3 A2 C3 E3 G3 E3 G2 B2 D3", 4))
mono("ARPMAJ1", "arpeggio", 132, "C:maj",
     ("Bright fifth+octave arpeggios C F G", "Arpèges brillants quinte+octave do fa sol",
      "Arpegios brillantes quinta+octava do fa sol"),
     R("xxxxxxxxxxxxxxx-", "C4 E4 G4 E4 F4 A4 C5 A4 G4 D4 G4 D4 C4 E4 G4", 3))
mono("ARPUP1", "arpeggio", 150, "E:min",
     ("Rising 3-note arpeggio across the beat", "Arpège montant de 3 notes à cheval sur les temps",
      "Arpegio ascendente de 3 notas a caballo del pulso"),
     R("xxxxxxxxxxxxxxx-", "E2 G2 B2 E2 G2 B2 E2 G2 C3 E3 G3 C3 E3 G3 D3", 4))
mono("BASSRIF1", "bass riff", 120, "A:min",
     ("Driving minor bass riff", "Riff de basse mineur entraînant",
      "Riff de bajo menor contundente"),
     R("x.x-x.-xx.x-x.x-", "A2 A2 C3 A2 G2 G2 E2 G2", 4))
mono("BASSOCT1", "bass riff", 128, "E:min",
     ("Octave-jumping bass Em G Am", "Basse en sauts d'octave mim sol lam",
      "Bajo con saltos de octava mim sol lam"),
     R("x-x-x-x-x-x-x-x-", "E2 E3 E2 E3 G2 G3 A2 A3", 4))
mono("FUNKBAS1", "funk", 104, "E:dor",
     ("Syncopated dorian funk bass", "Basse funk dorienne syncopée",
      "Bajo funk dórico sincopado"),
     R("x..x..x.-x.x.xx-", "E2 E3 E2 G2 A2 B2 D3", 4))
mono("SLAPBAS1", "funk", 100, "E:pentmin",
     ("Slap bass with a snap on every note", "Basse slap avec claquement sur chaque note",
      "Bajo slap con chasquido en cada nota"),
     R("x.-x.-x.x.-x-.x-", "E2 E2 G2 A2 E2 D3", 2))
mono("GROOVE1", "groove", 120, "A:min",
     ("Kick, bass and snare in one line", "Grosse caisse, basse et caisse claire sur une ligne",
      "Bombo, bajo y caja en una sola línea"),
     R("x.x-x.x-x.x-x.x-", "A3@7 A2@4 E2@2 A2@4 A3@7 C3@4 G2@2 E2@4"))
mono("GROOVE2", "hip-hop", 90, "D:min",
     ("Boom-bap groove: kick, bass, snare", "Groove boom-bap : grosse caisse, basse, caisse claire",
      "Groove boom-bap: bombo, bajo, caja"),
     L("A3@7 . D2@4 . F2@2 . - A3@7 . . A3@7 . A2@2 . C3@4 -"))
mono("TECHGRV1", "techno", 130, "F:min",
     ("Four-on-the-floor kick with offbeat bass", "Grosse caisse à chaque temps, basse à contretemps",
      "Bombo a negras con bajo a contratiempo"),
     R("x.x-x.x-x.x-x.x-", "A3@7 F2@4 A3@7 F2@4 A3@7 F2@4 A3@7 G#2@4"))
mono("CHIPLD1", "chiptune", 140, "C:maj",
     ("Cheerful chiptune melody in C", "Mélodie chiptune joyeuse en do",
      "Melodía chiptune alegre en do"),
     L("E3 . G3 . C4 . B3 A3 G3 . E3 . F3 D3 C3 -", 4))
mono("CHIPLD2", "chiptune", 150, "A:min",
     ("Minor chiptune hook", "Accroche chiptune mineure",
      "Gancho chiptune menor"),
     L("A2 . C3 E3 A3 . G3 E3 F3 . E3 C3 D3 B2 A2 -", 4))
mono("CHIPLD3", "chiptune", 160, "G:maj",
     ("Fast game-loop lead in fifths", "Mélodie rapide de jeu en quintes",
      "Melodía rápida de videojuego en quintas"),
     L("G4 . D4 . G4 A4 B4 . A4 G4 E4 . D4 . - .", 3))
mono("FANFARE1", "game jingle", 140, "C:maj",
     ("Level-clear fanfare", "Fanfare de fin de niveau",
      "Fanfarria de nivel superado"),
     L("C4@3 . . E4@3 . . G4@3 . C5@1 . . . . . - ."))
mono("ONEUP1", "game jingle", 160, "C:maj",
     ("Extra-life jingle", "Jingle de vie supplémentaire",
      "Jingle de vida extra"),
     L("E2 . G2 . E3 . C3 . D3 . G3 . . . - .", 4))
mono("GAMEOVR1", "game jingle", 96, "C:min",
     ("Falling game-over chords", "Accords descendants de fin de partie",
      "Acordes descendentes de fin de partida"),
     L("C4@0 . . G3@0 . . F3@0 . . . C4@0 . . . . -"))
mono("POWERUP1", "game jingle", 170, "C:maj",
     ("Power-up rising arpeggio", "Arpège montant de bonus",
      "Arpegio ascendente de power-up"),
     L("C4 E4 G4 C5 E4 G4 C5 E5 G4 C5 E5 G5 - . . .", 3))
mono("VICTORY1", "game jingle", 120, "C:maj",
     ("Victory fanfare C Am F G", "Fanfare de victoire do lam fa sol",
      "Fanfarria de victoria do lam fa sol"),
     L("C4@1 . C4@1 C4@1 C4@1 . . . A3@0 . . . F3@1 . G3@1 -"))
mono("BOOGIE1", "blues", 96, "E:blues",
     ("Boogie-woogie bass line in E", "Basse boogie-woogie en mi",
      "Bajo boogie-woogie en mi"),
     R("x.x.x.x.x.x.x.x-", "E2 G#2 B2 C#3 D3 C#3 B2 G#2", 4))
mono("BLUESLK1", "blues", 88, "G:blues",
     ("Shuffled blues lick in G", "Plan blues shuffle en sol",
      "Frase de blues shuffle en sol"),
     R("x.xx.xx.xx.x..-.", "G2 A#2 C3 C#3 D3 F3 D3 C3", 4))
mono("BLUESCH1", "blues", 100, "E:blues",
     ("Shuffle stabs I-IV (E A)", "Accords shuffle I-IV (mi la)",
      "Acordes shuffle I-IV (mi la)"),
     R("x..x..x-x..x..x-", "E3@1 E3@1 E3@1 A3@1 A3@1 A3@1"))
mono("ROCKRIF1", "rock", 128, "E:min",
     ("Power-chord rock riff in E", "Riff rock en accords de puissance en mi",
      "Riff rock con power chords en mi"),
     L("E3 . E3 - G3 . A3 - E3 . E3 - B3 . A3 -", 3))
mono("ROCKRIF2", "rock", 140, "A:min",
     ("Chugging power chords Am C G F", "Accords de puissance martelés lam do sol fa",
      "Power chords machacados lam do sol fa"),
     L("A3 A3 A3 - A3 A3 C4 . A3 A3 A3 - G3 . F3 -", 3))
mono("PUNK1", "punk", 170, "E:min",
     ("Fast punk eighths E C D", "Croches punk rapides mi do ré",
      "Corcheas punk rápidas mi do re"),
     R("x-x-x-x-x-x-x-x-", "E3 E3 E3 E3 C4 C4 D4 D4", 3))
mono("METAL1", "metal", 150, "E:min",
     ("Galloping metal riff", "Riff metal au galop",
      "Riff metal al galope"),
     L("E3 - E3 E3 E3 - E3 E3 G3 - G3 G3 A3 - B3 -", 3))
mono("DISCOOCT", "disco", 118, "G:min",
     ("Disco octave bass Gm Eb F", "Basse disco en octaves solm mib fa",
      "Bajo disco en octavas solm mib fa"),
     R("x-x-x-x-x-x-x-x-", "G2 G3 G2 G3 D#2 D#3 F2 F3", 4))
mono("SYNTHWV1", "synthwave", 100, "A:min",
     ("Synthwave pulse bass with chord hits", "Basse pulsée synthwave et accords",
      "Bajo pulsante synthwave con acordes"),
     L("A3@0 . A2@4 A2@4 A2@4 . A2@4 . F3@1 . F2@4 F2@4 G3@1 . G2@4 -"))
mono("POPOCT1", "synth-pop", 112, "F:maj",
     ("Bass and chord ping-pong F Dm Bb C", "Ping-pong basse/accord fa rém sib do",
      "Ping-pong bajo/acorde fa rem sib do"),
     R("x-x-x-x-x-x-x-x-", "F2@4 F3@1 D2@4 D4@0 A#2@4 A#3@1 C3@4 C4@1"))
mono("ELECTRO1", "electro", 125, "E:min",
     ("Electro kick and slap-bass line", "Ligne électro grosse caisse et basse claquée",
      "Línea electro de bombo y bajo slap"),
     L("A3@7 . . E2@2 . . A3@7 . E3@4 . G2@2 - A3@7 . D3@4 -"))
mono("WALTZ1", "waltz", 120, "G:maj",
     ("Oom-pah-pah 3+3+3+3+4 G D C D", "Boum-tchak-tchak 3+3+3+3+4 sol ré do ré",
      "Bum-chas-chas 3+3+3+3+4 sol re do re"),
     L("G2@4 G3@1 G3@1 D2@4 D4@1 D4@1 C2@4 C4@1 C4@1 D2@4 D4@1 D4@1 G2@4 . . -"))
mono("MARCH1", "march", 112, "Bb:maj",
     ("Dotted march fanfare in Bb", "Fanfare de marche pointée en sib",
      "Fanfarria de marcha con puntillo en sib"),
     L("F3 . . F3 A#3 . . A#3 D4 . A#3 . F4 . - .", 3))
mono("BOSSA1", "bossa nova", 120, "D:dor",
     ("Bossa bass and m7 comping", "Basse bossa et accords m7",
      "Bajo bossa y acordes m7"),
     L("D2@4 . . E4@6 . - A2@4 . D2@4 . . E4@6 . - A2@4 -"))
mono("DEMBOW1", "reggaeton", 95, "D:min",
     ("Dembow rhythm: kick and bass-snare", "Rythme dembow : grosse caisse et basse-caisse claire",
      "Ritmo dembow: bombo y bajo-caja"),
     L("A3@7 . . D2@2 A3@7 . F2@2 . A3@7 . . D2@2 A3@7 . C3@2 -"))
mono("DNBMONO1", "drum & bass", 170, "F:min",
     ("Two-step drum & bass with sub notes", "Drum & bass two-step avec basses",
      "Drum & bass two-step con bajos"),
     L("A3@7 . . . F2@2 . . . . . A3@7 . G#2@2 . . -"))
mono("DREAMPAD", "ambient", 80, "C:maj",
     ("Dreamy Csus4 to Am7 pads", "Nappes rêveuses dosus4 vers lam7",
      "Colchones soñadores dosus4 a lam7"),
     L("C4@5 . . . . . . - A3@6 . . . . . . -"))
mono("CHIPBAS1", "chiptune", 145, "C:min",
     ("Bouncy chiptune bass with rests", "Basse chiptune bondissante avec silences",
      "Bajo chiptune saltarín con silencios"),
     R("x-xx-x-xx-x-x-xx", "C2 C3 C2 D#2 F2 F2 G2 A#2 G2 F2", 4))
mono("MINLEAD1", "chiptune", 132, "D:hmin",
     ("Harmonic-minor lead in D", "Mélodie en ré mineur harmonique",
      "Melodía en re menor armónica"),
     L("D3 . F3 A3 C#3 . D3 . E3 F3 E3 D3 C#3 . A2 -", 4))
mono("MAJLEAD1", "chiptune", 120, "D:maj",
     ("Major lead in fifths, D", "Mélodie majeure en quintes, ré",
      "Melodía mayor en quintas, re"),
     L("D4 . F#4 . A4 . F#4 E4 D4 . B3 . A3 . - .", 3))
mono("ANDALUS1", "flamenco", 110, "A:min+G#",
     ("Andalusian cadence Am G F E", "Cadence andalouse lam sol fa mi",
      "Cadencia andaluza lam sol fa mi"),
     L("A3@0 . . A3@0 G3@1 . . G3@1 F3@1 . . F3@1 E3@1 . . -"))
mono("TECHOCT1", "techno", 132, "A:min",
     ("Pulsing techno fifths", "Quintes techno pulsées",
      "Quintas techno pulsantes"),
     R("x-x-xx-x-x-xx-x-", "A3 A3 A3 C4 A3 A3 G3 A3 E3", 3))
mono("LOFIHOP1", "lo-fi", 86, "A:min",
     ("Lo-fi hip-hop: kick, m7 chords, bass-snare", "Hip-hop lo-fi : grosse caisse, accords m7, basse-caisse claire",
      "Hip-hop lo-fi: bombo, acordes m7, bajo-caja"),
     L("A3@7 . A3@6 . A2@2 - . A3@7 D4@6 . A3@7 . D2@2 . - ."))
mono("KICKMEL1", "drums", 140, None,
     ("Tuned kick + hat melody (808 style)", "Mélodie de grosse caisse accordée + charleston (style 808)",
      "Melodía de bombo afinado + charles (estilo 808)"),
     R("x..x..x.x.x..x..", "A3 A3 E4 A3 C4 G3", 7))
mono("ITALO1", "italo disco", 120, "A:min",
     ("Italo-disco 16th octave bass", "Basse italo-disco en octaves rapides",
      "Bajo italo-disco en octavas rápidas"),
     R("xxxxxxxxxxxxxxxx", "A2 A3 A2 A3 A2 A3 A2 A3 F2 F3 F2 F3 G2 G3 G2 G3", 4))
mono("SKACHD1", "ska", 150, "C:maj",
     ("Ska upstrokes C F G", "Contretemps ska do fa sol",
      "Contratiempos ska do fa sol"),
     R("..x-..x-..x-..x-", "C4 C4 F3 G3", 1))
mono("LULLABY1", "lullaby", 80, "F:maj",
     ("Gentle lullaby line in F", "Douce berceuse en fa",
      "Suave canción de cuna en fa"),
     L("C3 . A2 . F2 . A2 . A#2 . G2 . C3 . - .", 4))
mono("RPGTOWN1", "chiptune", 110, "F:maj",
     ("RPG town theme in F", "Thème de village de RPG en fa",
      "Tema de pueblo de RPG en fa"),
     L("F2 . A2 C3 F3 . E3 C3 D3 . A#2 . C3 . - .", 4))
mono("SPACEARP", "arpeggio", 125, "D:min",
     ("Spacey fifth arpeggios Dm Bb C", "Arpèges spatiaux en quintes rém sib do",
      "Arpegios espaciales en quintas rem sib do"),
     R("xxxxxxxxxxxxxxx-", "D4 A4 F4 A4 D4 A4 F4 A4 A#3 F4 D4 F4 C4 G4 C5", 3))
mono("STEPUP1", "octave jumps", 128, "C:maj",
     ("Climbing octave jumps C D E G", "Sauts d'octave qui montent do ré mi sol",
      "Saltos de octava ascendentes do re mi sol"),
     L("C2 . C3 . D2 . D3 . E2 . E3 . G2 . G3 -", 4))
mono("FUNKCHD1", "funk", 108, "E:dor",
     ("Funky Em7 / A chord stabs", "Stabs funky mim7 / la",
      "Stabs funky mim7 / la"),
     R("x.-x.-x-.x-x.-x-", "E4@6 E4@6 E4@6 A3@1 A3@1 E4@6"))
mono("SOULBAS1", "soul", 110, "C:pentmaj",
     ("Pentatonic soul bass in C", "Basse soul pentatonique en do",
      "Bajo soul pentatónico en do"),
     L("C2 . . C3 . G2 A2 . C3 . A2 G2 E2 . G2 -", 4))
mono("ACIDLN1", "acid", 132, "A:phr",
     ("Phrygian acid line", "Ligne acid phrygienne",
      "Línea acid frigia"),
     R("xx-xx-x-xx-xxx-x", "A2 A3 A2 C3 A2 A#2 A2 G2 A2 E3 A2", 4))

# ---------------------------------------------------------------- POLY -------
# Batterie seule
poly("DRUMS01", "house drums", 124, None,
     ("House beat: kick, clap, open hats", "Rythme house : grosse caisse, clap, charleston ouvert",
      "Ritmo house: bombo, palmas, charles abierto"),
     A=G("K...K...K...K...", TK), B=G("....C.......C...", TK),
     N=G("h.o.h.o.h.o.h.oh", NK))
poly("DRUMS02", "rock drums", 120, None,
     ("Basic rock beat", "Rythme rock de base", "Ritmo rock básico"),
     A=G("K.....K.K.....K.", TK), N=G("h.h.s.h.h.h.s.hh", NK))
poly("DRUMS03", "hip-hop drums", 90, None,
     ("Boom-bap drums", "Batterie boom-bap", "Batería boom-bap"),
     A=G("K......K..K.....", TK), B=G("....S.......S..s", TK),
     N=G("h.h.h.h.h.hHh.h.", NK))
poly("DRUMS04", "breakbeat", 136, None,
     ("Amen-style breakbeat", "Breakbeat façon Amen", "Breakbeat estilo Amen"),
     A=G("K.K.......KK....", TK), B=G("....S..s.s..S..s", TK),
     N=G("h.h.h.h.h.h.o.h.", NK))
poly("DRUMS05", "drum & bass", 170, None,
     ("Two-step drum & bass beat", "Rythme drum & bass two-step", "Ritmo drum & bass two-step"),
     A=G("K.........K.....", TK), B=G("....S..s....S...", TK),
     N=G("h.hHh.hhh.hHh.hh", NK))
poly("DRUMS06", "drum fill", 112, None,
     ("Tom fill with crash", "Roulement de toms avec crash", "Redoble de toms con crash"),
     A=G("K.......K.......", TK), B=G("T.TTM.MML.LLM.L.", TK),
     N=G("x...........q.qq", NK))
poly("DRUMS07", "reggae drums", 80, None,
     ("One-drop reggae beat", "Rythme reggae one drop", "Ritmo reggae one drop"),
     A=G("........K.......", TK), B=G("........S.......", TK),
     N=G("h.h.h.h.h.h.m.h.", NK))
poly("DRUMS08", "electro drums", 125, None,
     ("808-style electro beat", "Rythme électro façon 808", "Ritmo electro estilo 808"),
     A=G("K.....K...K.....", TK), N=G("h.h.c.h.h.h.c.hh", NK))
poly("DRUMS09", "bossa drums", 120, None,
     ("Bossa nova kick, rim clave and hats", "Bossa nova : grosse caisse, clave au cerclage, charleston",
      "Bossa nova: bombo, clave en aro, charles"),
     A=G("K..kK..kK..kK..k", TK), B=G("R..R..R...R.R...", TK),
     N=G("h.h.h.h.h.h.h.h.", NK))
poly("SAMBA01", "samba drums", 100, None,
     ("Batucada: surdo, tamborim, shaker", "Batucada : surdo, tamborim, shaker",
      "Batucada: surdo, tamborim, shaker"),
     A=G("k...K...k...K...", TK), B=G("R.RR.R.RR.R.R.R.", TK),
     N=G("hhHhhhHhhhHhhhHh", NK))
# Basse + batterie
poly("BASDRM01", "techno", 130, "A:min",
     ("Techno bass + drums block", "Bloc basse + batterie techno", "Bloque bajo + batería techno"),
     A=G("K...K...K...K...", TK), B=R("..x-..x-..x-..x-", "A2 A2 A2 G2", "BASS"),
     N=G("h.H.h.H.h.H.h.Hh", NK))
poly("BASDRM02", "funk", 104, "E:dor",
     ("Funk bass + drums with ghost notes", "Basse + batterie funk avec notes fantômes",
      "Bajo + batería funk con notas fantasma"),
     A=L("E2 . - E3 - . E2 G2 . A2 - . B2 . D3 -", "BASS"),
     B=G("K.....K...K..K..", TK), N=G("h.hgs.hgh.hgs.hg", NK))
poly("BASDRM03", "drum & bass", 170, "F:min",
     ("Reese bass + breakbeat", "Basse reese + breakbeat", "Bajo reese + breakbeat"),
     A=R("x.......x.....-.", "F2 C#3", "WOBBLE"), B=G("K.........K.....", TK),
     C=G("....S.......S...", TK), N=G("h.hhh.hhh.hhh.hh", NK))
poly("BASDRM04", "hip-hop", 90, "D:min",
     ("Hip-hop bass + drums", "Basse + batterie hip-hop", "Bajo + batería hip-hop"),
     A=R("x..-...x..x-x.x-", "D2 D2 F2 A2 C3", "BASS"), B=G("K......K..K.....", TK),
     N=G("h.h.s.h.h.h.s.hh", NK))
poly("BASDRM05", "house", 124, "G:min",
     ("House bass + drums", "Basse + batterie house", "Bajo + batería house"),
     A=G("K...K...K...K...", TK), B=R("..x-..xx..x-.xx-", "G2 G2 G3 A#2 F2 G2", "BASS"),
     N=G("h.o.c.o.h.o.c.o.", NK))
poly("BASDRM06", "rock", 130, "E:min",
     ("Rock eighth-note bass + drums", "Basse en croches + batterie rock", "Bajo en corcheas + batería rock"),
     A=R("x-x-x-x-x-x-x-x-", "E2 E2 E2 E2 C2 C2 D2 D2", "BASS"),
     B=G("K.....K.K.....K.", TK), N=G("h.h.s.h.h.h.s.h.", NK))
# Morceaux complets
poly("TECHNO01", "techno", 130, "A:min",
     ("Rolling techno bass with minor chord blips", "Basse techno roulante et accords mineurs brefs",
      "Bajo techno rodante con acordes menores breves"),
     A=G("K...K...K...K...", TK),
     B=R(".xx-.xx-.xx-.xx-", "A2 A2 A2 A2 A2 C3 A2 G2", "BASS"),
     C=R("...x-.....x-....", "E3 A3", "ARPMIN"),
     N=G("h.H.h.H.h.H.h.HH", NK))
poly("TECHNO02", "acid techno", 135, "F:min",
     ("Acid line with portamento", "Ligne acid avec portamento", "Línea acid con portamento"),
     A=G("K...K...K...K...", TK),
     B=R("xxx-xx-xxx-xx-xx", "F2 F3 F2 G#2 F2 C3 F2 F3 D#3 F2 C#3 C3", "PORTA"),
     C=R("x-..............", "F3", "ARPMIN"),
     N=G("h.h.c.h.h.h.c.h.", NK))
poly("TECHNO03", "minimal techno", 126, "D:min",
     ("Minimal techno with bell blips", "Techno minimale avec clochettes", "Techno minimal con campanitas"),
     A=G("K...K...K...K...", TK), B=R("......x-......x-", "D2 F2", "BASS"),
     C=R("..x.....x..x....", "A4 D5 F4", "BELL"),
     N=G("..h.m.h...h.m.hh", NK))
poly("HOUSE01", "house", 124, "G:min",
     ("House organ chords Gm Eb F", "Accords d'orgue house solm mib fa",
      "Acordes de órgano house solm mib fa"),
     A=G("K...K...K...K...", TK), B=R("..x-..x-..x-..x-", "G2 G2 D#2 F2", "BASS"),
     C=R("..x-..x-..x-..x-", "G3 G3 D#4@ARP F3@ARP", "ARPMIN"),
     N=G("h.o.c.o.h.o.c.o.", NK))
poly("HOUSE02", "deep house", 120, "C:min",
     ("Deep house m7 chords Cm7 Fm7", "Accords m7 deep house dom7 fam7",
      "Acordes m7 deep house dom7 fam7"),
     A=merge(G("K...K...K...K...", TK), R("..x-..x-..x-..x-", "C2 C2 F2 F2", "BASS")),
     B=R("x..-..x-x..-.x.-", "D#4 D#4 G#4 G#4", "SOFT"),
     C=R("x..-..x-x..-.x.-", "A#4 A#4 D#5 D#5", "SOFT"),
     N=G("..h.c.h...h.c.h.", NK))
poly("ELECTR01", "electro", 128, "E:min",
     ("Electro buzz bass, 808 kick and clap", "Basse buzzer électro, grosse caisse 808 et clap",
      "Bajo buzzer electro, bombo 808 y palmas"),
     A=R("x.-x.-x-..x-.x.-", "E2 E2 G2 D2 E2", "BUZZ"),
     B=G("K.....K...K.....", TK), C=G("....C.......C...", TK),
     N=G("h.hhh.hhh.hhh.hh", NK))
poly("ELECTR02", "electro", 120, "C:min",
     ("Robotic electro with laser zaps", "Électro robotique avec tirs laser",
      "Electro robótico con disparos láser"),
     A=G("K.....K...K..K..", TK),
     B=R("x.-xx.-.x.-xx.-.", "C2 C3 C2 C2 D#2 G2", "BUZZTR"),
     C=R("......x.......x.", "C5 G4", "LASER"),
     N=G("h.h.c.hhh.h.c.h.", NK))
poly("HIPHOP01", "hip-hop", 90, "D:min",
     ("Boom-bap with stabs", "Boom-bap avec stabs", "Boom-bap con stabs"),
     A=R("x..-...x..x-x.x-", "D2 D2 F2 A2 C3", "BASS"),
     B=G("K......K..K.....", TK),
     C=R("..x-......x-....", "A4 C5", "STAB"),
     N=G("h.h.s.h.h.h.s.hh", NK))
poly("HIPHOP02", "lo-fi hip-hop", 84, "A:min",
     ("Lo-fi pads Am7 F with lazy bass", "Nappes lo-fi lam7 fa et basse paresseuse",
      "Colchones lo-fi lam7 fa con bajo perezoso"),
     A=R("x...-..x..x.-...", "A2 G2 F2", "BASS"),
     B=R("x......-x......-", "C4 A3", "PAD"),
     C=R("x......-x......-", "G4 C4", "PAD"),
     N=G("k.h.s.h..kh.s.hh", NK))
poly("TRAP01", "trap", 140, "F:min",
     ("Trap: 808 bass, bell melody, hat rolls", "Trap : basse 808, mélodie de cloche, roulements de charleston",
      "Trap: bajo 808, melodía de campana, redobles de charles"),
     A=G("K......K..K.....", TK), B=R("x......x..x....-", "F2 F2 C#2", "BASS"),
     C=R("x..x..x...x.....", "C5 G#4 F4 D#4", "BELL"),
     N=G("h.h.hhh.s.hhhhhh", NK))
poly("ROCK01", "rock", 130, "E:min",
     ("Rock: eighth bass and power chords", "Rock : basse en croches et accords de puissance",
      "Rock: bajo en corcheas y power chords"),
     A=R("x-x-x-x-x-x-x-x-", "E2 E2 E2 E2 C2 C2 D2 D2", "BASS"),
     B=R("x.-xx.-.x.-xx.-.", "E4 E4 E4 C4 D4 D4", "LEAD"),
     C=R("x.-xx.-.x.-xx.-.", "B4 B4 B4 G4 A4 A4", "LEAD"),
     N=G("k.h.s.h.k.k.s.h.", NK))
poly("ROCK02", "rock", 120, "A:min",
     ("Half-time rock with power dyads", "Rock en demi-tempo avec quintes",
      "Rock a medio tiempo con quintas"),
     A=G("K.......K.K.....", TK), B=R("x......-x.x....-", "A2 F2 G2", "BASS"),
     C=R("x......-x.x....-", "E4 C4 D4", "LEAD"),
     N=G("h.h.h.h.s.h.h.h.", NK))
poly("FUNK01", "funk", 104, "E:dor",
     ("Funk: syncopated bass and chord scratches", "Funk : basse syncopée et grattés d'accords",
      "Funk: bajo sincopado y rasgueos de acordes"),
     A=L("E2 - . E2 G2 - A2 - . A2 - B2 D3 - E3 -", "BASS"),
     B=R(".x-.x-.x.x-..x-.", "E3 E3 A3@ARP A3@ARP E3", "ARPMIN"),
     C=G("K..K..K...K..K..", TK),
     N=G("h.hgs.hgh.hgs.hg", NK))
poly("FUNK02", "funk", 110, "G:mix",
     ("Mixolydian funk G C F", "Funk mixolydien sol do fa", "Funk mixolidio sol do fa"),
     A=L("G2 . - G3 - G2 E2 - D2 . - E2 F2 - G2 -", "BASS"),
     B=R("..x-..x-.x-...x-", "G3 C4 G3 F3", "ARP"),
     C=G("K.....K.K..K....", TK),
     N=G("h.h.s.hhh.hgs.h.", NK))
poly("REGGAE01", "reggae", 80, "A:min",
     ("One-drop reggae with offbeat chops", "Reggae one drop et accords à contretemps",
      "Reggae one drop con acordes a contratiempo"),
     A=R("x..x.-x...x-x.-.", "A2 C3 D3 G2 A2", "BASS"),
     B=R("..x-..x-..x-..x-", "A3 A3 G3@ARP G3@ARP", "ARPMIN"),
     C=G("........K.......", TK),
     N=G("h.h.h.h.m.h.h.h.", NK))
poly("REGGAE02", "dub", 84, "E:min",
     ("Dub with echoing chord stabs", "Dub avec accords en écho", "Dub con acordes en eco"),
     A=R("x...x.x-......x-", "E2 G2 A2 B2", "BASS"),
     B=R("....x-..v-..w-..", "E3", "ARPMIN"),
     C=G("........K.......", TK),
     N=G("h...h.m.h...h.h.", NK))
poly("BOSSA01", "bossa nova", 120, "D:dor",
     ("Bossa nova Dm7-G7 with clave", "Bossa nova rém7-sol7 avec clave",
      "Bossa nova rem7-sol7 con clave"),
     A=R("x..xx..xx..xx..x", "D2 A2 A2 D2 G2 D2 D2 G2", "BASS"),
     B=R("x.-x.-x-..x-x.-.", "F4", "SOFT"),
     C=R("x.-x.-x-..x-x.-.", "C5 C5 C5 B4 B4", "SOFT"),
     N=G("m.hm.hm.h.m.m.h.", NK))
poly("DNB01", "drum & bass", 170, "F:min",
     ("Drum & bass: wobble bass and pads", "Drum & bass : basse wobble et nappes",
      "Drum & bass: bajo wobble y colchones"),
     A=G("K.........K.....", TK), B=R("x......-x.....-.", "F2 C#2", "WOBBLE"),
     C=R("x.......x......-", "G#4 F4", "PAD"),
     N=G("h.h.s.hgh.hhs.hh", NK))
poly("DNB02", "liquid d&b", 170, "A:min",
     ("Liquid drum & bass with bells", "Drum & bass liquide avec cloches",
      "Drum & bass líquido con campanas"),
     A=G("K......K..K.....", TK), B=R("x...x.-.x...x.-.", "A2 A2 F2 G2", "BASS"),
     C=R("x..x..x.x..x..x.", "E5 C5 A4 G4 F4 A4", "BELL"),
     N=G("h.hhs.hhh.hhs.hh", NK))
poly("CHIP01", "chiptune", 150, "C:maj",
     ("Chiptune game loop C F G", "Boucle de jeu chiptune do fa sol",
      "Bucle de videojuego chiptune do fa sol"),
     A=L("K . C2 - C3 - G2 - K . F2 - F3 - G2 -", "BASS"),
     B=R("x.x.x.x.x.x.x.x.", "C4 C4 C4 C4 F3 F3 G3 G3", "ARP"),
     C=L("E5 . G5 - C6 . G5 E5 F5 . A5 - G5 . D5 -", "LEAD"),
     N=G("h.h.s.h.h.h.s.hh", NK))
poly("CHIP02", "chiptune", 160, "A:hmin",
     ("Boss battle in A harmonic minor", "Combat de boss en la mineur harmonique",
      "Batalla de jefe en la menor armónica"),
     A=L("A2 A3 A2 A3 A2 A3 A2 A3 F2 F3 F2 F3 E2 E3 E2 E3", "BASS"),
     B=R("x...x...x...x...", "A3 A3 F3@ARP E3@ARP", "ARPMIN"),
     C=L("A4 . C5 . E5 . D5 C5 F5 . A5 . G#5 . B5 -", "LEAD"),
     N=G("H.h.s.h.H.h.s.hs", NK))
poly("CHIP03", "chiptune", 120, "F:maj",
     ("Overworld theme with vibrato lead", "Thème de carte avec mélodie vibrato",
      "Tema de mapa con melodía con vibrato"),
     A=L("F2 - C3 - F2 - C3 - A#2 - F2 - C3 - E2 -", "BASS"),
     B=R("x-x-x-x-x-x-x-x-", "F3 F3 F3 F3 A#3 A#3 C4 C4", "ARP"),
     C=L("A4 . . C5 . . F5 . D5 . . A#4 . G4 . -", "VIBRA"),
     N=G("h.hhs.h.h.hhs.h.", NK))
poly("CHIP04", "chiptune", 140, "E:hmin",
     ("Dungeon theme Em C B", "Thème de donjon mim do si", "Tema de mazmorra mim do si"),
     A=L("E2 . . E2 . . E2 . C3 . . C3 B2 . B2 .", "BASS"),
     B=R("x.......x...x..-", "E3 C4@ARP B3@ARP", "ARPMIN"),
     C=L("B4 . . . G4 . B4 . E5 . . . D#5 . . -", "LEAD"),
     N=G("h...s...h...s.h.", NK))
poly("CHIP05", "chiptune", 110, "D:maj",
     ("Village shop tune with bells", "Air de boutique de village avec cloches",
      "Melodía de tienda de pueblo con campanas"),
     A=L("D3 - A2 - D3 - A2 - G2 - D3 - A2 - E3 -", "BASS"),
     B=R("x.x.x.x.x.x.x.x.", "D4 F#4 A4 D5 G4 B4 A4 E4", "BELL"),
     C=L("F#5 . . . E5 . D5 . B4 . . . C#5 . . -", "VIBRA"),
     N=G("h..hh..hh..hh..h", NK))
poly("WALTZ01", "waltz", 120, "G:maj",
     ("Waltz feel 3+3+3+3+4 G D C D", "Valse 3+3+3+3+4 sol ré do ré", "Vals 3+3+3+3+4 sol re do re"),
     A=L("G2 - . D2 - . C2 - . D2 - . G2 . . -", "BASS"),
     B=L(". G3 G3 - D4 D4 - C4 C4 - D4 D4 - G3 . -", "ARP"),
     C=L("B4 . . A4 . . G4 . . F#4 . . G4 . . -", "LEAD"),
     N=G("h..h..h..h..h...", NK))
poly("WALTZ02", "waltz", 132, "D:hmin",
     ("Minor waltz Dm A Bb A", "Valse mineure rém la sib la", "Vals menor rem la sib la"),
     A=L("D2 - . A2 - . A#2 - . A2 - . D2 . . -", "BASS"),
     B=L(". D4 D4 - A3@ARP A3@ARP - A#3@ARP A#3@ARP - A3@ARP A3@ARP - D4 . -", "ARPMIN"),
     C=L("F5 . . E5 . . D5 . . C#5 . . D5 . . -", "LEAD"),
     N=G("h..h..h..h..h...", NK))
poly("BALLAD01", "ballad", 80, "C:maj",
     ("Ballad C Am F G with vibrato melody", "Ballade do lam fa sol avec mélodie vibrato",
      "Balada do lam fa sol con melodía con vibrato"),
     A=R("x..-x..-x..-x..-", "C3 A2 F2 G2", "BASS"),
     B=R("x...x...x...x..-", "E4 C4 A3 B3", "PAD"),
     C=L("G5 . . E5 C5 . . E5 A5 . . G5 F5 . D5 -", "VIBRA"),
     N=G("h...q...h...q...", NK))
poly("MARCH01", "march", 112, "Bb:maj",
     ("Brass-band march in Bb", "Marche de fanfare en sib", "Marcha de banda en sib"),
     A=L("A#2 - F2 - A#2 - F2 - F2 - C3 - F2 - C3 -", "BASS"),
     B=L("F4 . . F4 A#4 . . D5 C5 . A4 . F4 . - .", "LEAD"),
     C=G("K.......K.......", TK),
     N=G("s..gs.g.s..gs.ss", NK))
poly("MINIMAL1", "minimal", 122, "A:min",
     ("Sparse minimal groove", "Groove minimal dépouillé", "Groove minimal despojado"),
     A=G("K...K...K...K...", TK), B=R("...x-......x-...", "A2 G2", "BASS"),
     C=R("......x.......x.", "E5 C5", "BELL"),
     N=G("..h...h.m.h...hh", NK))
poly("TRANCE01", "trance", 138, "A:min",
     ("Trance gated chords Am F G", "Accords hachés trance lam fa sol",
      "Acordes entrecortados trance lam fa sol"),
     A=G("K...K...K...K...", TK), B=R("..x-..x-..x-..x-", "A2 A2 F2 G2", "BASS"),
     C=R("x-x-x-x-x-x-x-x-", "A3 A3 A3 A3 F3@ARP F3@ARP G3@ARP G3@ARP", "ARPMIN"),
     N=G("h.o.c.o.h.o.c.o.", NK))
poly("SYNPOP01", "synth-pop", 118, "C:maj",
     ("Synth-pop C Am F G, octave bass", "Synth-pop do lam fa sol, basse en octaves",
      "Synth-pop do lam fa sol, bajo en octavas"),
     A=R("x-x-x-x-x-x-x-x-", "C2 C3 A2 A3 F2 F3 G2 G3", "BASS"),
     B=R("x.x-x.x-x.x-x.x-", "C4 C4 A3@ARPMIN A3@ARPMIN F3 F3 G3 G3", "ARP"),
     C=G("K...S...K..KS...", TK),
     N=G("h.h.h.h.h.h.h.hh", NK))
poly("SYNWAVE1", "synthwave", 100, "A:min",
     ("Synthwave: pulse bass, pad, gated snare", "Synthwave : basse pulsée, nappe, caisse claire",
      "Synthwave: bajo pulsante, colchón, caja"),
     A=R("x-x-x-x-x-x-x-x-", "A2 A2 A2 A2 F2 F2 G2 G2", "BASS"),
     B=R("x......-x...x..-", "E4 C4 D4", "PAD"),
     C=G("K...S...K...S...", TK),
     N=G("h.h.h.h.h.h.h.h.", NK))
poly("DISCO01", "disco", 120, "G:min",
     ("Disco octave bass, offbeat chords, open hats", "Disco : basse en octaves, accords à contretemps, charleston ouvert",
      "Disco: bajo en octavas, acordes a contratiempo, charles abierto"),
     A=R("x-x-x-x-x-x-x-x-", "G2 G3 G2 G3 D#2 D#3 F2 F3", "BASS"),
     B=R("..x-..x-..x-..x-", "G3 G3 D#4@ARP F3@ARP", "ARPMIN"),
     C=G("K...K...K...K...", TK),
     N=G("h.o.s.o.h.o.s.o.", NK))
poly("SKA01", "ska", 150, "C:maj",
     ("Ska: walking bass and upstrokes", "Ska : basse marchante et contretemps",
      "Ska: bajo caminante y contratiempos"),
     A=L("C3 . E2 . F2 . G2 . A2 . G2 . F2 . E2 .", "BASS"),
     B=R("..x-..x-..x-..x-", "C4 C4 F3 G3", "ARP"),
     C=G("K...S...K...S...", TK),
     N=G("h.h.h.h.h.h.h.h.", NK))
poly("GARAGE01", "UK garage", 132, "F:min",
     ("2-step garage with organ stabs", "Garage 2-step avec stabs d'orgue",
      "Garage 2-step con stabs de órgano"),
     A=G("K......K..K.....", TK), B=R("x.-.x..x..x-..x-", "F2 F2 G#2 C3 D#2", "BASS"),
     C=R("...x-.....x-....", "C5 G#4", "ORGAN"),
     N=G("..h.s.h...h.s.hh", NK))
poly("DUBSTEP1", "dubstep", 140, "F:min",
     ("Half-time dubstep wobble", "Wobble dubstep en demi-tempo", "Wobble dubstep a medio tiempo"),
     A=G("K.........K.....", TK), B=R("x.......x..x..-.", "F2 G#2 D#2", "WOBBLE"),
     C=R("...............x", "C5", "ZAP"),
     N=G("h.h.h.h.s.h.h.hh", NK))
poly("JAZZ01", "jazz", 110, "F:maj",
     ("Walking bass, F6-C7 comping, ride", "Walking bass, accords fa6-do7, ride",
      "Walking bass, acordes fa6-do7, ride"),
     A=L("F2 . A2 . C3 . D3 . C3 . E2 . G2 . A#2 .", "BASS"),
     B=R("x.-...x-x.-...x-", "A4 A4 A#4 A#4", "SOFT"),
     C=R("x.-...x-x.-...x-", "D5 D5 E5 E5", "SOFT"),
     N=G("r..rr..rr..rr..r", NK))
poly("LATIN01", "salsa", 100, "C:maj",
     ("Salsa: tumbao bass, montuno, son clave", "Salsa : basse tumbao, montuno, clave son",
      "Salsa: bajo tumbao, montuno, clave de son"),
     A=L(". . . . . . G2 . . . . - C3 . . -", "BASS"),
     B=R("x.x.x.x.x.x.x.x.", "C4 E4 G4 E4 F4 A4 G4 D4", "PLUCK"),
     C=G("R..R..R...R.R...", TK),
     N=G("h.hhh.hhh.hhh.hh", NK))
poly("COUNTRY1", "country", 120, "G:maj",
     ("Country train beat, root-fifth bass", "Country : rythme de train, basse fondamentale-quinte",
      "Country: ritmo de tren, bajo tónica-quinta"),
     A=L("G2 - D2 - G2 - D2 - C3 - G2 - C3 - G2 -", "BASS"),
     B=R("..x...x...x...x.", "B3 D4 C4 E4", "PLUCK"),
     C=G("K.......K.......", TK),
     N=G("h.g.s.g.h.g.s.gg", NK))
poly("INDUST01", "industrial", 125, "C:phr",
     ("Industrial phrygian buzz", "Buzz industriel phrygien", "Buzz industrial frigio"),
     A=R("x.-xx-x-x.-xx-x-", "C2 C2 C2 C2 C2 C#2 C2 D#2", "BUZZ"),
     B=G("K..K..K.K..K..K.", TK), C=G("....S.......S...", TK),
     N=G("hhHhhhHhhhHhhhHh", NK))
poly("BLUES01", "blues", 96, "A:blues",
     ("Shuffle boogie with A7 stabs", "Boogie shuffle avec accords la7",
      "Boogie shuffle con acordes la7"),
     A=L("A2 . . C#3 E3 . . F#3 G3 . . F#3 E3 . . C#3", "BASS"),
     B=R("..x-......x-....", "C#4", "SOFT"),
     C=R("..x-......x-....", "G4", "SOFT"),
     N=G("h..hs..hh..hs..h", NK))
poly("MUSICBOX", "lullaby", 90, "F:maj",
     ("Music-box lullaby in F", "Berceuse de boîte à musique en fa",
      "Canción de cuna de caja de música en fa"),
     A=R("x..-x..-x..-x..-", "F2 C3 A#2 C3", "BASS"),
     B=L("C5 . A4 . F4 . A4 . A#4 . G4 . C5 . G4 .", "PLUCK"),
     C=R("x.......x......-", "F4 D4", "PAD"))
poly("SPACE01", "ambient", 90, "D:min",
     ("Ambient pads and distant bells", "Nappes ambient et cloches lointaines",
      "Colchones ambient y campanas lejanas"),
     A=R("x.......x......-", "D4 A#3", "PAD"),
     B=R("x.......x......-", "A4 F4", "PAD"),
     C=R("x.....x....x....", "D5 F5 A#4", "BELL"),
     N=G("o...............", NK))
# Digidrums (samples de DRUMS.SMP : il faut cette banque chargée)
poly("DIGIHOP1", "hip-hop (digidrums)", 90, "D:min",
     ("Hip-hop with sampled kick and snare (DRUMS.SMP)", "Hip-hop avec grosse caisse et caisse claire samplées (DRUMS.SMP)",
      "Hip-hop con bombo y caja sampleados (DRUMS.SMP)"),
     A=G("K......K..K.....", DK), B=G("....S.......S...", DK),
     C=R("x..-...x..x-x.x-", "D2 D2 F2 A2 C3", "BASS"),
     N=G("h.h.h.h.h.h.h.hh", NK))
poly("DIGIHSE1", "house (digidrums)", 124, "G:min",
     ("House with sampled kick and clap (DRUMS.SMP)", "House avec grosse caisse et clap samplés (DRUMS.SMP)",
      "House con bombo y palmas sampleados (DRUMS.SMP)"),
     A=G("K...K...K...K...", DK), B=R("..x-..xx..x-.xx-", "G2 G2 G3 A#2 F2 G2", "BASS"),
     C=G("....C.......C...", DK),
     N=G("..o...o...o...o.", NK))
poly("DIGIFNK1", "funk (digidrums)", 104, "E:dor",
     ("Funk with sampled drums and ghost snares (DRUMS.SMP)", "Funk avec batterie samplée et notes fantômes (DRUMS.SMP)",
      "Funk con batería sampleada y notas fantasma (DRUMS.SMP)"),
     A=G("K..K..K...K..K..", DK), B=G("....S..s....S..s", DK),
     C=L("E2 - . E2 G2 - A2 - . A2 - B2 D3 - E3 -", "BASS"),
     N=G("h.h.h.h.h.h.h.h.", NK))
poly("DIGIBRK1", "breakbeat (digidrums)", 136, "G:min",
     ("Sampled amen-style break with buzz bass (DRUMS.SMP)", "Break façon Amen samplé avec basse buzzer (DRUMS.SMP)",
      "Break estilo Amen sampleado con bajo buzzer (DRUMS.SMP)"),
     A=G("K.K.......KK....", DK), B=G("....S..s.s..S..s", DK),
     C=R("x..x..x-..x-x.-.", "G2 G2 A#2 F2 G2", "BUZZ"),
     N=G("h.h.h.h.h.h.o.h.", NK))

# Les 16 premiers fichiers du catalogue : ceux que la liste de f3 P montre
# (elle affiche au plus 16 fichiers, MAX_FILES dans src/smpscreen.asm).
SHOWCASE = {
    "mono": ["POPCHRD1", "TRANCEG1", "ARPMIN1", "BASSRIF1", "GROOVE1", "CHIPLD1",
             "FANFARE1", "BOOGIE1", "ROCKRIF1", "DISCOOCT", "LOFIM7", "HOUSECH1",
             "WALTZ1", "DEMBOW1", "ANDALUS1", "ONEUP1"],
    "poly": ["TECHNO01", "HOUSE01", "ELECTR01", "HIPHOP01", "ROCK01", "FUNK01",
             "REGGAE01", "BOSSA01", "DNB01", "CHIP01", "WALTZ01", "BALLAD01",
             "DRUMS01", "DRUMS02", "BASDRM01", "DIGIHOP1"],
}


# --- vérifications ---------------------------------------------------------------
NAME_RE = re.compile(r"^[A-Z0-9]{1,8}$")


def attacks(p, step):
    """Ce que joue le pas : [(voix, note, instrument)], et les voix arrêtées
    (None = toutes)."""
    ev_list, offs = [], []
    lanes = p["lanes"]
    if p["mode"] == MONO:
        ev = lanes[0][step]
        if ev == OFF:
            return [], None
        if ev is not None:
            n, son = ev[0], ev[1]
            for v, voice in enumerate(SONS[son][1:]):
                if voice is None:
                    continue
                off, ins = voice
                ev_list.append((v, off if v == 3 else n + off, ins))
        return ev_list, offs
    for v, lane in enumerate(lanes):
        ev = lane[step] if lane else None
        if ev == OFF:
            offs.append(v)
        elif ev is not None:
            ev_list.append((v, ev[0], ev[1]))
    return ev_list, offs


def check(p):
    """Liste des problèmes d'un motif (vide = bon)."""
    err = []
    name = p["name"]
    if not NAME_RE.match(name):
        err.append("nom invalide")
    if not 60 <= p["bpm"] <= 200:
        err.append("tempo %d" % p["bpm"])
    for i, lane in enumerate(p["lanes"]):
        if lane is not None and len(lane) != 16:
            err.append("voix %d : %d pas" % (i, len(lane)))
    scale = parse_key(p["key"])
    mode = p["mode"]
    # contenu des cases
    for v, lane in enumerate(p["lanes"]):
        for s, ev in enumerate(lane or []):
            if ev is None or ev == OFF:
                continue
            n, ins, vol = ev
            if mode == MONO:
                if v != 0 or not isinstance(ins, int) or not 0 <= ins <= 7:
                    err.append("pas %d : son composé %r" % (s, ins))
                continue
            if not isinstance(ins, str) or ins not in I:
                err.append("pas %d : instrument %r" % (s, ins))
                continue
            if vol is not None and not 0 <= vol <= 15:
                err.append("pas %d : volume %r" % (s, vol))
            if v == 3:
                if not 0 <= n <= 31:
                    err.append("pas %d : période de bruit %d" % (s, n))
                if ins not in NOISE_INS:
                    err.append("pas %d : %s sur la voix de bruit" % (s, ins))
    if err:
        return err
    # simulation sur deux tours : hauteurs, gamme, frottements
    bpm = p["bpm"]
    sounding = {}                          # voix -> (classes, instrument, fin)
    for t in range(32):
        s = t % 16
        evs, offs = attacks(p, s)
        if offs is None:
            sounding.clear()
        else:
            for v in offs:
                sounding.pop(v, None)
        for v in [v for v, x in sounding.items() if x[2] is not None and x[2] <= t]:
            del sounding[v]
        new = {}
        for v, n, ins in evs:
            if v == 3:                     # voix de bruit : pas de hauteur
                continue
            lo, hi = RANGES.get(ins, (24, 88))
            if t < 16 and not lo <= n <= hi:
                err.append("pas %d : %s hors tessiture pour %s" % (s, note_name(n), ins))
            if not pitched(ins):
                sounding.pop(v, None)
                continue
            pcs = {(n + i) % 12 for i in implied(ins)}
            if t < 16 and n + max(implied(ins)) > 95:
                err.append("pas %d : note trop haute" % s)
            if t < 16 and scale is not None and not pcs <= scale:
                err.append("pas %d : %s (%s) hors de la gamme %s"
                           % (s, note_name(n), ins, p["key"]))
            if t < 16 and scale is None:
                err.append("pas %d : note sans tonalité annoncée" % s)
            h = hold_steps(ins, bpm)
            new[v] = (pcs, ins, None if h is None else t + h)
        sounding.update(new)
        if t < 16:
            continue
        ev0 = p["lanes"][0][s]             # mono : un accord n'est jamais exempté
        chord_step = mode == MONO and ev0 not in (None, OFF) and ev0[1] in (0, 1, 5, 6)
        for v, (pcs, ins, _) in new.items():
            exempt = s % 2 == 1 and ins not in CHORDY and not chord_step
            if exempt:
                continue
            for u, (pcs2, ins2, _) in sounding.items():
                if u == v:
                    continue
                if any((a - b) % 12 in (1, 11) for a in pcs for b in pcs2):
                    err.append("pas %d : demi-ton entre la voix %d (%s) et la voix %d (%s)"
                               % (s, v, ins, u, ins2))
    # notes tenues sans fin
    lanes = p["lanes"] if mode == POLY else [p["lanes"][0]]
    for v, lane in enumerate(lanes):
        if lane is None or (mode == POLY and v == 3):
            continue
        hits = [ev for ev in lane if ev not in (None, OFF)]
        held = False
        for ev in hits:
            if mode == MONO:
                held |= any(x is not None and x[0] < 3 and ins_field(x[1], 3) > 0
                            for x in [(i, vo[1]) if vo else None
                                      for i, vo in enumerate(SONS[ev[1]][1:])])
            else:
                held |= ins_field(ev[1], 3) > 0 and not ins_field(ev[1], 6) & DIGI
        if held and OFF not in lane and len(hits) < 4:
            err.append("voix %d : note tenue sans arrêt" % v)
    return sorted(set(err), key=err.index)


def note_name(n):
    return "%s%d" % (NAMES[n % 12], n // 12)


# --- fichiers ------------------------------------------------------------------
def encode(p):
    data = bytearray([p["mode"], p["bpm"], 0, 0])
    for s in range(16):
        for v in range(4):
            lane = p["lanes"][v]
            ev = lane[s] if lane else None
            if ev is None:
                data += bytes([NOTE_NONE, 0, 0xFF, 0])
            elif ev == OFF:
                data += bytes([NOTE_OFF, 0, 0xFF, 0])
            else:
                n, ins, vol = ev
                idx = ins if isinstance(ins, int) else I[ins]
                data += bytes([n, idx, 0xFF if vol is None else vol, 0])
    assert len(data) == PAT_SIZE
    return bytes(data)


def disk_order(disk):
    """Les motifs d'une disquette, dans l'ordre du catalogue."""
    pats = [p for p in PATTERNS if p["disk"] == disk]
    first = [next(p for p in pats if p["name"] == n) for n in SHOWCASE[disk]]
    return first + [p for p in pats if p["name"] not in SHOWCASE[disk]]


def validate():
    problems = []
    names = [p["name"] for p in PATTERNS]
    for n in sorted(set(x for x in names if names.count(x) > 1)):
        problems.append("%s : nom en double" % n)
    for disk in ("mono", "poly"):
        k = sum(p["disk"] == disk for p in PATTERNS)
        if k > 64:
            problems.append("%s : %d motifs, le catalogue n'a que 64 entrées" % (disk, k))
        for n in SHOWCASE[disk]:
            if not any(p["name"] == n and p["disk"] == disk for p in PATTERNS):
                problems.append("%s : %s absent" % (disk, n))
    for p in PATTERNS:
        for e in check(p):
            problems.append("%s : %s" % (p["name"], e))
    if problems:
        raise SystemExit("Motifs refusés :\n  " + "\n  ".join(problems))


def liste_md():
    out = ["# SEQ-16 : motifs d'usine / factory patterns / patrones de fábrica", "",
           "Généré par `tools/gen_patterns.py` — ne pas modifier à la main.", "",
           "- **mono** : mode son composé (une ligne, les 8 sons composés d'usine) / "
           "layered-sound mode / modo sonido compuesto.",
           "- **poly** : mode voix séparées (A, B, C + bruit) / split voices / voces separadas.",
           "- Chargement : f3 P. Les 16 premiers fichiers de chaque disquette sont "
           "ceux que la liste de f3 P affiche (16 fichiers au plus) / f3 P lists the "
           "first 16 files of the disk / f3 P muestra los 16 primeros archivos.",
           "- Les motifs `DIGI*` jouent les samples de `DRUMS.SMP` (instruments 29-32).", ""]
    for disk, dsk in (("mono", "seq16-motifs-mono.dsk"), ("poly", "seq16-motifs-poly.dsk")):
        pats = disk_order(disk)
        out += ["## %s — `build/%s` (%d)" % (disk.upper(), dsk, len(pats)), "",
                "| # | Fichier | Style | BPM | Key | English | Français | Español |",
                "|---|---|---|---|---|---|---|---|"]
        for i, p in enumerate(pats, 1):
            en, fr, es = p["desc"]
            out.append("| %d | `%s.PAT` | %s | %d | %s | %s | %s | %s |"
                       % (i, p["name"], p["style"], p["bpm"], key_text(p["key"]), en, fr, es))
        out.append("")
    return "\n".join(out)


def write_all():
    validate()
    import cpcdisk
    amsdos = cpcdisk.charger()
    from cpc_dsk.core.adf import ADFDisk
    summary = []
    for disk in ("mono", "poly"):
        d = os.path.join(ROOT, "patterns", disk)
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):            # pas de vieux motifs oubliés
            if f.upper().endswith(".PAT"):
                os.remove(os.path.join(d, f))
        dsk = ADFDisk.new_blank()
        fs = amsdos.AmsdosFilesystem(dsk)
        pats = disk_order(disk)
        for p in pats:
            data = encode(p)
            with open(os.path.join(d, p["name"] + ".PAT"), "wb") as fh:
                fh.write(data)
            fs.write_file(p["name"] + ".PAT", data, mode="amsdos")
        path = os.path.join(ROOT, "build", "seq16-motifs-%s.dsk" % disk)
        dsk.save(path)
        summary.append((path, len(pats), fs.free_entries(), fs.free_bytes() // 1024))
    with open(os.path.join(ROOT, "patterns", "LISTE.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(liste_md())
    return summary


def main():
    for path, n, entries, free in write_all():
        print("OK : %s (%d motifs, %d entrées libres, %d Ko libres)"
              % (os.path.relpath(path, ROOT), n, entries, free))
    styles = sorted({p["style"] for p in PATTERNS})
    print("     %d styles : %s" % (len(styles), ", ".join(styles)))
    print("     patterns/mono, patterns/poly, patterns/LISTE.md")


if __name__ == "__main__":
    main()
