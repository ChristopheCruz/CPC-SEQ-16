"""wav2smp.py : convertit des fichiers WAV en banque de samples .SMP pour SEQ-16.

Rôle
----
Le CPC joue un sample en écrivant très vite le registre de volume d'une voie
de l'AY-3-8912 (16 niveaux, courbe presque logarithmique). Ce script prépare
les données sur PC :

  1. normalisation ;
  2. gain / saturation (--drive) ;
  3. rééchantillonnage SANS filtre anti-repliement (un point sur N) :
     l'aliasing est voulu. --clean ajoute un filtre simple ;
  4. quantification sur les 16 niveaux MESURÉS de l'AY (niveau le plus proche
     en amplitude) ;
  5. réduction de résolution --bits 4|3|2|1 (masque #F, #E, #C, #8) ;
  6. tramage --dither none|noise (none par défaut).

Il écrit une banque .SMP et, pour chaque sample, un WAV « d'écoute » qui
simule le rendu du CPC (mêmes niveaux, même fréquence, même décimation).

Mode d'emploi
-------------
    python tools/wav2smp.py kick.wav snare.wav -o samples/MABANK.SMP
    python tools/wav2smp.py boucle.wav --slice 8 --rate 6000 -o BOUCLE.SMP
    python tools/wav2smp.py son.wav --bits 2 --decim 3 --drive 4 -o SALE.SMP
    python tools/wav2smp.py son.wav -o X.SMP --dsk          # + ajoute au .dsk
    python tools/wav2smp.py --info samples/DRUMS.SMP         # contenu d'une banque

Bibliothèque standard uniquement (wave, struct, array, argparse).

Format .SMP (version 1)
-----------------------
En-tête, 16 octets :
    0-3   "SQSM"
    4     version (1)
    5     nombre de samples (1 à 16)
    6-15  réserve (0)
Puis une fiche de 16 octets par sample :
    0-5   nom (6 caractères ASCII, complété par des espaces)
    6     bloc de 16 Ko dans la zone de données (0 à 3)
    7-8   décalage dans ce bloc (0 à #3FFF), poids faible d'abord
    9-10  longueur en octets
    11    code de fréquence = durée d'un échantillon en NOP (µs), de 62 à 250
          -> fréquence = 1 000 000 / code (16,1 kHz à 4 kHz). C'est directement
          la durée de la boucle de lecture du Z80.
    12-13 point de boucle (en octets depuis le début du sample), #FFFF = aucun
    14    drapeaux : bit 0 sens arrière, bit 1 boucle active, bit 2 ton mêlé,
                     bit 3 tremblement, bits 4-6 courbe (0 à 4), bit 7 réservé
    15    réglages : bits 0-2 décimation (indice dans 1,2,3,4,6,8),
                     bits 3-4 bits (0 = 4 bits, 1 = 3, 2 = 2, 3 = 1),
                     bits 5-7 réservés
La zone de données suit les fiches (adresse 16 + 16 x nombre). Le bloc et le
décalage d'un sample se comptent depuis le début de cette zone. Un sample ne
chevauche JAMAIS une frontière de 16 Ko (le script complète si besoin) : la
routine Z80 n'a donc jamais à changer de bloc pendant la lecture.
Données : 2 échantillons de 4 bits par octet, le premier dans les 4 bits de
poids fort. Chaque échantillon est un CODE DE NIVEAU de l'AY (0 à 15) : écrit
tel quel dans le registre de volume, il redonne le son d'origine au mieux.

Décimation (réglage de lecture, non destructif) : la durée ne change pas ;
seul un échantillon sur N est joué et maintenu N périodes (sample & hold).
"""
import argparse
import array
import math
import os
import random
import struct
import sys
import wave

# ---------------------------------------------------------------------------
# Niveaux de sortie de l'AY-3-8912 pour les volumes 0 à 15 (amplitude
# relative, 1.0 = volume 15).
# Source : émulateur Ayumi de Peter Sovietov, https://github.com/true-grue/ayumi
# (fichier ayumi.c, tableau AY_dac_table, licence MIT). Ayumi indexe ce
# tableau de 32 cases par volume * 2 + 1 ; les cases vont par paires égales.
# ---------------------------------------------------------------------------
AY_LEVELS = [
    0.0, 0.00999465934234, 0.0144502937362, 0.0210574502174,
    0.0307011520562, 0.0455481803616, 0.0644998855573, 0.107362478065,
    0.126588845655, 0.20498970016, 0.292210269322, 0.372838941024,
    0.492530708782, 0.635324635691, 0.805584802014, 1.0,
]

MAGIC = b"SQSM"
VERSION = 1
HEADER_SIZE = 16
ENTRY_SIZE = 16
MAX_SAMPLES = 16
BLOCK = 16384                      # un bloc de mémoire supplémentaire du 6128
BANK_MAX_6128 = 65536              # 4 blocs de 16 Ko
BANK_MAX_464 = 4096                # banque de repli en mémoire principale
CODE_MIN, CODE_MAX = 62, 250       # durée d'un échantillon en NOP
DECIMS = [1, 2, 3, 4, 6, 8]
BITS_MASK = {4: 0xF, 3: 0xE, 2: 0xC, 1: 0x8}
BITS_INDEX = {4: 0, 3: 1, 2: 2, 1: 3}
CURVES = ["lineaire", "log", "saturee", "repliee", "inversee"]
CURVE_LOG = 1                      # courbe par défaut : rendu fidèle
REST = 12                          # niveau de repos (signal nul) : code 12


def nearest_code(a):
    """Amplitude 0..1 -> code de niveau AY le plus proche."""
    a = max(0.0, min(1.0, a))
    return min(range(16), key=lambda i: abs(AY_LEVELS[i] - a))


def curve_table(curve):
    """Table de 16 codes appliquée pendant la lecture : code lu -> code écrit
    dans le registre de volume. Les données sont des codes de niveau AY.
      0 linéaire  : le code est pris pour une amplitude linéaire (code/15
                    -> AY). C'est la « table linéaire écrite telle quelle dans
                    l'AY logarithmique » : distorsion voulue.
      1 log       : identité. Rendu fidèle (les données sont déjà des niveaux
                    de l'AY).
      2 saturée   : gain x2,5 autour du repos, écrêté.
      3 repliée   : gain x2,5, ce qui dépasse est replié (wavefolding).
      4 inversée  : forme d'onde retournée autour du repos.
    """
    mid = AY_LEVELS[REST]
    out = []
    for c in range(16):
        a = AY_LEVELS[c]
        if curve == 0:
            out.append(round(15 * a))       # amplitude -> valeur linéaire 0..15
            continue
        if curve == 1:
            out.append(c)
            continue
        if curve == 2:
            b = mid + (a - mid) * 2.5
        elif curve == 3:
            b = mid + (a - mid) * 2.5
            while b > 1 or b < 0:
                b = 2 - b if b > 1 else -b
        elif curve == 4:
            b = 2 * mid - a
        else:
            raise ValueError("courbe inconnue : %d" % curve)
        out.append(nearest_code(b))
    return out


CURVE_TABLES = [curve_table(i) for i in range(len(CURVES))]
NO_LOOP = 0xFFFF
F_BACKWARD, F_LOOP, F_TONE, F_JITTER = 1, 2, 4, 8


# --- lecture / écriture de WAV --------------------------------------------
def read_wav(path):
    """Renvoie (liste de flottants entre -1 et 1, fréquence). Stéréo -> mono."""
    with wave.open(path, "rb") as w:
        nch, width, rate, n = (w.getnchannels(), w.getsampwidth(),
                               w.getframerate(), w.getnframes())
        raw = w.readframes(n)
    if width == 1:                              # 8 bits non signé
        vals = [(b - 128) / 128.0 for b in raw]
    elif width == 2:                            # 16 bits signé
        a = array.array("h")
        a.frombytes(raw)
        if sys.byteorder == "big":
            a.byteswap()
        vals = [v / 32768.0 for v in a]
    elif width == 3:                            # 24 bits signé (accepté en plus)
        vals = [int.from_bytes(raw[i:i + 3], "little", signed=True) / 8388608.0
                for i in range(0, len(raw), 3)]
    else:
        raise ValueError("%s : seuls les WAV 8, 16 ou 24 bits sont gérés" % path)
    if nch > 1:                                 # mixage en mono
        vals = [sum(vals[i:i + nch]) / nch for i in range(0, len(vals), nch)]
    return vals, rate


def write_wav(path, samples, rate):
    """Écrit un WAV mono 16 bits ; samples entre -1 et 1."""
    a = array.array("h", (max(-32767, min(32767, int(round(v * 32767))))
                          for v in samples))
    if sys.byteorder == "big":
        a.byteswap()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(round(rate)))
        w.writeframes(a.tobytes())


# --- traitements -----------------------------------------------------------
def normalize(x):
    peak = max((abs(v) for v in x), default=0.0)
    return [v / peak for v in x] if peak > 0 else list(x)


def drive(x, amount):
    """Gain puis écrêtage dur : au-delà de 1, le son sature (voulu)."""
    if amount == 1.0:
        return list(x)
    return [max(-1.0, min(1.0, v * amount)) for v in x]


def rate_to_code(rate):
    """Fréquence voulue -> code (durée d'un échantillon en NOP)."""
    return max(CODE_MIN, min(CODE_MAX, int(round(1_000_000 / rate))))


def code_to_rate(code):
    return 1_000_000 / code


def resample(x, src_rate, dst_rate, clean=False):
    """Un point sur N, sans filtre (aliasing voulu). clean : moyenne glissante
    sur la largeur d'un pas avant la prise du point (filtre simple)."""
    if not x:
        return []
    step = src_rate / dst_rate
    n = max(1, int(len(x) / step))
    if clean and step > 1:
        width = int(math.ceil(step))
        acc = [0.0]                             # sommes cumulées
        for v in x:
            acc.append(acc[-1] + v)
        out = []
        for i in range(n):
            c = int(i * step)
            a, b = max(0, c - width // 2), min(len(x), c + width - width // 2)
            out.append((acc[b] - acc[a]) / (b - a))
        return out
    return [x[min(len(x) - 1, int(i * step))] for i in range(n)]


def quantize(x, dither="none", rng=None):
    """Flottants -1..1 -> codes de niveau AY 0..15 (le plus proche en
    amplitude). Le signal est recentré : -1 -> amplitude 0, +1 -> 1.
    dither="noise" : arrondi aléatoire entre les deux niveaux voisins,
    proportionnel à la distance (tramage adapté aux niveaux inégaux)."""
    rng = rng or random.Random(1234)
    out = []
    for v in x:
        a = (max(-1.0, min(1.0, v)) + 1.0) / 2.0
        if dither == "noise":
            hi = next(i for i, lv in enumerate(AY_LEVELS) if lv >= a)
            if hi == 0 or AY_LEVELS[hi] == a:
                out.append(hi)
                continue
            lo = hi - 1
            frac = (a - AY_LEVELS[lo]) / (AY_LEVELS[hi] - AY_LEVELS[lo])
            out.append(hi if rng.random() < frac else lo)
        else:
            out.append(min(range(16), key=lambda i: abs(AY_LEVELS[i] - a)))
    return out


def reduce_bits(codes, bits):
    m = BITS_MASK[bits]
    return [c & m for c in codes]


def pack(codes):
    """2 codes par octet, le premier dans les 4 bits de poids fort."""
    if len(codes) % 2:
        codes = codes + [codes[-1]]
    return bytes((codes[i] << 4) | codes[i + 1] for i in range(0, len(codes), 2))


def unpack(data):
    out = []
    for b in data:
        out += [b >> 4, b & 0xF]
    return out


# --- simulation du rendu CPC (WAV d'écoute) -------------------------------
def render(codes, decim=1, bits=4, curve=CURVE_LOG):
    """Ce que l'AY sortira : niveau mesuré de chaque code, après le masque de
    bits, la courbe et la décimation (un échantillon sur N, maintenu N
    périodes). C'est exactement le calcul de la routine Z80.
    La composante continue est retirée pour l'écoute."""
    m = BITS_MASK[bits]
    t = CURVE_TABLES[curve]
    lv = [AY_LEVELS[t[codes[(i // decim) * decim] & m]] for i in range(len(codes))]
    if not lv:
        return []
    mean = sum(lv) / len(lv)
    return [v - mean for v in lv]


# --- une banque ------------------------------------------------------------
class Sample:
    def __init__(self, name, data, code, loop=NO_LOOP, flags=0, decim=1, bits=4):
        self.name = name
        self.data = bytes(data)
        self.code = code
        self.loop = loop
        self.flags = flags
        self.decim = decim
        self.bits = bits

    @property
    def rate(self):
        return code_to_rate(self.code)

    @property
    def seconds(self):
        return 2 * len(self.data) / self.rate


def clean_name(name):
    n = "".join(c for c in name.upper() if c.isalnum())
    return (n or "SAMPLE")[:6]


def convert(x, src_rate, name, rate=8000, drive_amount=1.0, clean=False,
            bits=4, dither="none", decim=1, max_len=BLOCK, rng=None):
    """Chaîne complète pour un son : flottants -> Sample."""
    code = rate_to_code(rate)
    y = normalize(x)
    y = drive(y, drive_amount)
    y = resample(y, src_rate, code_to_rate(code), clean)
    codes = reduce_bits(quantize(y, dither, rng), bits)
    data = pack(codes)
    if len(data) > max_len:
        data = data[:max_len]
    return Sample(clean_name(name), data, code, flags=CURVE_LOG << 4, decim=decim)


def build_bank(samples):
    """Assemble l'en-tête, les fiches et les données. Renvoie des octets."""
    if not 1 <= len(samples) <= MAX_SAMPLES:
        raise ValueError("une banque contient de 1 à 16 samples")
    header = MAGIC + bytes([VERSION, len(samples)]) + bytes(10)
    entries, data = b"", bytearray()
    for s in samples:
        if len(s.data) > BLOCK:
            raise ValueError("%s : un sample ne dépasse pas 16 Ko" % s.name)
        if len(data) // BLOCK != (len(data) + len(s.data) - 1) // BLOCK:
            pad = BLOCK - len(data) % BLOCK     # ne pas chevaucher deux blocs
            data += bytes([0x00]) * pad
        off = len(data)
        data += s.data
        flags = s.flags & 0x7F
        settings = DECIMS.index(s.decim) | BITS_INDEX[s.bits] << 3
        entries += (s.name.ljust(6)[:6].encode("ascii")
                    + bytes([off // BLOCK])
                    + struct.pack("<HHBHBB", off % BLOCK, len(s.data), s.code,
                                  s.loop, flags, settings))
    return header + entries + bytes(data)


def parse_bank(raw):
    """Relit une banque .SMP -> liste de Sample. Vérifie l'en-tête."""
    if raw[:4] != MAGIC:
        raise ValueError("signature SQSM absente")
    if raw[4] != VERSION:
        raise ValueError("version de banque inconnue : %d" % raw[4])
    n = raw[5]
    if not 1 <= n <= MAX_SAMPLES:
        raise ValueError("nombre de samples invalide : %d" % n)
    base = HEADER_SIZE + ENTRY_SIZE * n
    out = []
    for i in range(n):
        e = raw[HEADER_SIZE + ENTRY_SIZE * i:HEADER_SIZE + ENTRY_SIZE * (i + 1)]
        name = e[:6].decode("ascii").rstrip()
        off, length, code, loop, flags, settings = struct.unpack("<HHBHBB", e[7:16])
        start = base + e[6] * BLOCK + off
        s = Sample(name, raw[start:start + length], code, loop, flags,
                   DECIMS[settings & 7],
                   {v: k for k, v in BITS_INDEX.items()}[(settings >> 3) & 3])
        out.append(s)
    return out


def data_size(raw):
    """Taille de la zone de données (ce qui ira en mémoire du CPC)."""
    return len(raw) - HEADER_SIZE - ENTRY_SIZE * raw[5]


def check_sizes(raw, warn=print):
    size = data_size(raw)
    if size > BANK_MAX_6128:
        warn("ATTENTION : la banque dépasse 64 Ko (%d octets) : trop grande "
             "même pour un 6128" % size)
    elif size > BANK_MAX_464:
        warn("Note : la banque dépasse 4 Ko (%d octets) : elle ne tiendra pas "
             "sur un CPC 464/664" % size)
    return size


def info(path):
    raw = open(path, "rb").read()
    bank = parse_bank(raw)
    print("%s : %d samples, %d octets de données" % (path, len(bank), data_size(raw)))
    for i, s in enumerate(bank):
        print("  %2d %-6s %5d oct. %6.0f Hz (%3d NOP) %5.3f s  décim %d  %d bits"
              % (i, s.name, len(s.data), s.rate, s.code, s.seconds, s.decim, s.bits))


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Convertit des WAV en banque de samples .SMP pour SEQ-16")
    p.add_argument("wav", nargs="*", help="fichiers WAV d'entrée")
    p.add_argument("-o", "--output", help="banque .SMP à écrire")
    p.add_argument("--rate", type=float, default=8000,
                   help="fréquence cible en Hz (4000 à 16000, défaut 8000)")
    p.add_argument("--drive", type=float, default=1.0,
                   help="gain avant écrêtage (1 = aucun, 4 = très saturé)")
    p.add_argument("--clean", action="store_true",
                   help="filtre avant rééchantillonnage (moins d'aliasing)")
    p.add_argument("--bits", type=int, choices=[4, 3, 2, 1], default=4)
    p.add_argument("--dither", choices=["none", "noise"], default="none")
    p.add_argument("--decim", type=int, choices=DECIMS, default=1,
                   help="décimation de lecture (réglage stocké, non destructif)")
    p.add_argument("--slice", type=int, default=1,
                   help="découpe chaque WAV en N tranches égales")
    p.add_argument("--names", help="noms des samples, séparés par des virgules")
    p.add_argument("--preview-dir", help="dossier des WAV d'écoute "
                   "(défaut : à côté de la banque)")
    p.add_argument("--no-preview", action="store_true")
    p.add_argument("--dsk", nargs="?", const="build/seq16.dsk",
                   help="ajoute la banque à la disquette (défaut build/seq16.dsk)")
    p.add_argument("--info", metavar="SMP", help="affiche le contenu d'une banque")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)

    if a.info:
        info(a.info)
        return 0
    if not a.wav or not a.output:
        p.error("il faut au moins un WAV et -o banque.SMP")
    if not 4000 <= a.rate <= 16200:
        p.error("--rate doit être entre 4000 et 16000 Hz")

    names = a.names.split(",") if a.names else []
    samples = []
    for path in a.wav:
        x, sr = read_wav(path)
        base = os.path.splitext(os.path.basename(path))[0]
        n = max(1, a.slice)
        size = len(x) // n
        for k in range(n):
            part = x[k * size:(k + 1) * size] if n > 1 else x
            default = clean_name(base)[:4 if n > 1 else 6] + ("%02d" % k if n > 1 else "")
            name = names[len(samples)] if len(samples) < len(names) else default
            samples.append(convert(part, sr, name, a.rate, a.drive, a.clean,
                                   a.bits, a.dither, a.decim))
    if len(samples) > MAX_SAMPLES:
        p.error("%d samples : une banque en contient 16 au plus" % len(samples))

    raw = build_bank(samples)
    open(a.output, "wb").write(raw)
    size = check_sizes(raw)
    if a.verbose:
        total = sum(s.seconds for s in samples)
        print("%s : %d samples, %d octets de données, %.2f s en tout"
              % (a.output, len(samples), size, total))
        for s in samples:
            print("  %-6s %5d octets  %.3f s à %.0f Hz" % (s.name, len(s.data), s.seconds, s.rate))

    if not a.no_preview:
        d = a.preview_dir or os.path.dirname(os.path.abspath(a.output))
        os.makedirs(d, exist_ok=True)
        stem = os.path.splitext(os.path.basename(a.output))[0]
        for s in samples:
            out = os.path.join(d, "%s_%s_ecoute.wav" % (stem, s.name))
            write_wav(out, render(unpack(s.data), s.decim, s.bits, (s.flags >> 4) & 7),
                      s.rate)
            if a.verbose:
                print("  écoute : " + out)

    if a.dsk:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import amsdsk
        name = os.path.basename(a.output).upper()
        amsdsk.add_file(a.dsk, name, raw)
        print("%s ajouté à %s" % (name, a.dsk))
    return 0


if __name__ == "__main__":
    sys.exit(main())
