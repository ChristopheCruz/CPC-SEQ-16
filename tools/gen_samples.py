"""gen_samples.py : fabrique les banques de samples de la disquette.

Tous les sons sont calculés ici (synthèse) ou dits par espeak (voix) : aucun
échantillon venu d'ailleurs, donc pas de question de droits.  Le hasard
utilise une graine fixe : deux exécutions donnent les mêmes fichiers.

La banque d'usine DRUMS.SMP (tools/gen_drums.py) et VOIX.SMP restent
inchangées ; DRUMS.SMP est toujours chargée par défaut sur l'écran f4.

Banques produites (samples/*.SMP) :
    BATTERI2   batterie façon boîte à rythmes : grosse caisse longue, toms...
    PERCUS     congas, bongos, claves, triangle, tambourin, cloche...
    EFFETS     laser, explosion, pièce, saut, sirène, alarme...
    BASSES     notes de basse (à jouer avec le piano de f4 : +-12 demi-tons)
    NOTES      notes d'instruments : pincé, cloche, orgue, cuivres, choeur
    CHIFFRES   « zéro » à « dix », en français (espeak)
    MOTS       petits mots pour faire chanter le CPC (espeak)

Mode d'emploi :  python tools/gen_samples.py [--dsk]
"""
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wav2smp  # noqa: E402
from gen_drums import env, onepole_lp, onepole_hp, noise  # noqa: E402

SR = 44100
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "samples")


# --- briques de synthèse -----------------------------------------------------
def tone(f0, dur, decay, wave="sin", f1=None, glide=0.03, rng=None):
    """Note de hauteur f0 (qui glisse vers f1), enveloppe exponentielle."""
    n = int(dur * SR)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        f = f0 if f1 is None else f1 + (f0 - f1) * math.exp(-t / glide)
        ph += f / SR
        p = ph % 1.0
        if wave == "sin":
            v = math.sin(2 * math.pi * p)
        elif wave == "sqr":
            v = 1.0 if p < 0.5 else -1.0
        elif wave == "saw":
            v = 2 * p - 1
        else:                                   # triangle
            v = 4 * abs(p - 0.5) - 1
        out.append(v * env(t, decay))
    return out


def mix(*parts):
    """Somme de signaux de longueurs différentes."""
    n = max(len(p) for p in parts)
    return [sum(p[i] for p in parts if i < len(p)) for i in range(n)]


def gain(x, g):
    return [g * v for v in x]


def burst(rng, dur, decay, lo=None, hi=None):
    """Bruit filtré (passe-haut lo, passe-bas hi) avec une chute."""
    x = noise(int(dur * SR), rng)
    if lo:
        x = onepole_hp(x, lo)
    if hi:
        x = onepole_lp(x, hi)
    return [v * env(i / SR, decay) for i, v in enumerate(x)]


def am(x, f, depth=1.0):
    """Modulation d'amplitude (trémolo, sirène, alarme)."""
    return [v * (1 - depth / 2 + depth / 2 * math.sin(2 * math.pi * f * i / SR))
            for i, v in enumerate(x)]


def fm_tone(f0, dur, decay, ratio, index, idecay):
    """Synthèse FM simple : cloches, métal."""
    out = []
    for i in range(int(dur * SR)):
        t = i / SR
        mod = index * env(t, idecay) * math.sin(2 * math.pi * f0 * ratio * t)
        out.append(math.sin(2 * math.pi * f0 * t + mod) * env(t, decay))
    return out


# --- BATTERI2 ----------------------------------------------------------------
def batteri2(rng):
    return [
        ("KICK8", mix(tone(150, 0.35, 0.18, f1=42, glide=0.04), burst(rng, 0.01, 0.002)), 6250, 1.6),
        ("KICKDR", mix(tone(220, 0.12, 0.04, f1=55, glide=0.01), burst(rng, 0.02, 0.004, 2000)), 6250, 2.5),
        ("SNARE8", mix(gain(burst(rng, 0.2, 0.06, 1500, 7000), 2), tone(180, 0.1, 0.03)), 8000, 2.5),
        ("RIM", mix(tone(1700, 0.03, 0.006), burst(rng, 0.03, 0.004, 3000)), 10000, 2.0),
        ("HATOUV", burst(rng, 0.3, 0.12, 7000), 12500, 2.5),
        ("HATFER", burst(rng, 0.05, 0.012, 8000), 12500, 2.5),
        ("TOMAIG", tone(260, 0.25, 0.08, f1=180, glide=0.06), 6250, 1.8),
        ("TOMMED", tone(180, 0.28, 0.09, f1=120, glide=0.06), 6250, 1.8),
        ("TOMGRV", tone(120, 0.3, 0.1, f1=80, glide=0.06), 6250, 1.8),
        ("CLAP8", mix(*[gain(burst(rng, 0.2, d, 900, 3000), 1.0) for d in (0.05,)],
                      [0.0] * 1), 8000, 3.0),
        ("COWBEL", mix(tone(560, 0.25, 0.07, "sqr"), tone(845, 0.25, 0.07, "sqr")), 8000, 1.5),
        ("CRASH", burst(rng, 0.6, 0.25, 4000), 10000, 3.0),
    ]


# --- PERCUS ------------------------------------------------------------------
def percus(rng):
    return [
        ("CONGAH", tone(330, 0.2, 0.06, f1=300, glide=0.02), 6250, 1.6),
        ("CONGAB", tone(220, 0.25, 0.08, f1=200, glide=0.02), 6250, 1.6),
        ("BONGO", tone(450, 0.12, 0.04, f1=400, glide=0.01), 8000, 1.6),
        ("CLAVES", tone(2500, 0.06, 0.015), 12500, 1.4),
        ("BLOC", mix(tone(900, 0.07, 0.015, "tri"), burst(rng, 0.01, 0.002, 2000)), 10000, 1.6),
        ("TRIANG", fm_tone(1800, 0.6, 0.25, 2.76, 2.0, 0.1), 12500, 1.4),
        ("TAMBOU", mix(burst(rng, 0.2, 0.06, 6000), gain(fm_tone(1200, 0.2, 0.05, 3.1, 3, 0.02), 0.4)), 12500, 2.5),
        ("MARACA", burst(rng, 0.08, 0.02, 5000), 12500, 2.5),
        ("AGOGO", fm_tone(900, 0.3, 0.1, 1.48, 1.5, 0.05), 10000, 1.5),
        ("TIMBAL", mix(tone(500, 0.3, 0.1, f1=480), gain(burst(rng, 0.1, 0.03, 2000), 0.6)), 8000, 2.0),
        ("TABLA", tone(300, 0.35, 0.12, f1=500, glide=0.05), 6250, 1.5),
        ("GUIRO", am(burst(rng, 0.25, 0.2, 2500, 6000), 40, 1.0), 10000, 2.5),
    ]


# --- EFFETS ------------------------------------------------------------------
def effets(rng):
    return [
        ("LASER", tone(3000, 0.25, 0.2, "sqr", f1=200, glide=0.06), 8000, 1.5),
        ("ZAP", tone(150, 0.2, 0.15, "saw", f1=2500, glide=0.05), 8000, 1.5),
        ("EXPLO", burst(rng, 0.5, 0.18, None, 1200), 6250, 3.0),
        ("PIECE", mix(tone(988, 0.08, 1, "sqr"), [0.0] * int(0.08 * SR) + tone(1319, 0.25, 0.1, "sqr")), 6250, 1.2),
        ("SAUT", tone(200, 0.25, 0.3, "sqr", f1=900, glide=0.08), 6250, 1.2),
        ("SIRENE", [math.sin(2 * math.pi * (700 * i / SR + 40 * math.sin(2 * math.pi * 2 * i / SR) / (2 * math.pi * 2))) for i in range(int(0.6 * SR))], 6250, 1.3),
        ("ALARME", am(tone(1000, 0.5, 9, "sqr"), 8, 2.0), 6250, 1.2),
        ("POWRUP", tone(1600, 0.4, 0.6, "tri", f1=200, glide=0.2), 6250, 1.3),
        ("UFO", [math.sin(2 * math.pi * (600 * i / SR + 30 * math.sin(2 * math.pi * 10 * i / SR))) for i in range(int(0.5 * SR))], 6250, 1.3),
        ("BIP", tone(1500, 0.12, 9, "sqr"), 8000, 1.2),
        ("TIR", mix(burst(rng, 0.3, 0.07, 500), tone(800, 0.2, 0.05, f1=100, glide=0.03)), 6250, 3.0),
        ("GLITCH", [rng.choice((-1, 1)) * (1 if (i // 220) % 3 else 0) for i in range(int(0.3 * SR))], 6250, 1.0),
    ]


# --- BASSES ------------------------------------------------------------------
def basses(rng):
    return [
        ("SCIE", onepole_lp(tone(65.4, 0.5, 0.3, "saw"), 900), 6250, 1.4),
        ("CARRE", onepole_lp(tone(65.4, 0.5, 0.3, "sqr"), 700), 6250, 1.3),
        ("SUB", tone(55, 0.6, 0.4), 6250, 1.6),
        ("ACIDE", [v * (0.5 + 0.5 * math.exp(-i / SR / 0.08)) for i, v in enumerate(onepole_lp(tone(65.4, 0.4, 0.25, "saw"), 1800))], 6250, 2.5),
        ("PINCEE", onepole_lp(tone(65.4, 0.4, 0.12, "saw"), 1200), 6250, 1.6),
        ("WOBBLE", am(onepole_lp(tone(55, 0.6, 2, "saw"), 600), 6, 1.6), 6250, 2.0),
        ("SALE", tone(65.4, 0.4, 0.25, "sqr"), 6250, 3.5),
        ("SLAP", mix(tone(82.4, 0.35, 0.15, "tri"), gain(tone(330, 0.03, 0.01), 0.6)), 6250, 2.0),
        ("OCTAVE", mix(tone(65.4, 0.4, 0.2, "saw"), gain(tone(130.8, 0.4, 0.15, "saw"), 0.5)), 6250, 1.6),
        ("DOUCE", tone(65.4, 0.6, 0.35, "tri"), 6250, 1.4),
    ]


# --- NOTES -------------------------------------------------------------------
def choir(f0, dur):
    """Un « aah » : quelques harmoniques renforcées autour des formants."""
    out = []
    for i in range(int(dur * SR)):
        t = i / SR
        a = min(1.0, t / 0.08) * env(t, 0.6)
        v = sum(math.sin(2 * math.pi * f0 * k * t) * w
                for k, w in ((1, 1), (2, .5), (3, .8), (4, .6), (5, .3), (6, .2)))
        out.append(a * v * (1 + 0.02 * math.sin(2 * math.pi * 5 * t)))
    return out


def notes(rng):
    c4 = 261.6
    return [
        ("PINCE", onepole_lp(tone(c4, 0.4, 0.12, "saw"), 3000), 6250, 1.4),
        ("PIANO", mix(tone(c4, 0.5, 0.25), gain(tone(2 * c4, 0.5, 0.12), 0.4), gain(tone(3 * c4, 0.3, 0.06), 0.2)), 6250, 1.4),
        ("CLOCHE", fm_tone(c4 * 2, 0.6, 0.3, 3.5, 4.0, 0.15), 6250, 1.3),
        ("ORGUE", mix(tone(c4, 0.4, 9), gain(tone(2 * c4, 0.4, 9), 0.6), gain(tone(4 * c4, 0.4, 9), 0.3)), 6250, 1.3),
        ("CUIVRE", [v * min(1.0, i / SR / 0.04) for i, v in enumerate(onepole_lp(tone(c4, 0.45, 0.4, "saw"), 2500))], 8000, 1.6),
        ("CHOEUR", choir(c4, 0.5), 6250, 1.3),
        ("ORCHES", mix(onepole_lp(tone(c4, 0.4, 0.15, "saw"), 3000), gain(onepole_lp(tone(c4 * 1.5, 0.4, 0.15, "saw"), 3000), 0.7),
                       gain(burst(rng, 0.05, 0.02, 2000), 0.5)), 6250, 2.2),
        ("MARIMB", fm_tone(c4, 0.35, 0.08, 4.0, 1.2, 0.02), 6250, 1.4),
        ("FLUTE", [v * min(1.0, i / SR / 0.06) for i, v in enumerate(mix(tone(c4 * 2, 0.4, 0.5), gain(burst(rng, 0.4, 0.5, 2000, 5000), 0.08)))], 8000, 1.3),
        ("SYNTH", onepole_lp(mix(tone(c4, 0.4, 0.3, "saw"), tone(c4 * 1.007, 0.4, 0.3, "saw")), 2500), 6250, 1.5),
    ]


# --- voix (espeak) -----------------------------------------------------------
def espeak_words(words, prefix):
    """Fait dire chaque mot à espeak (français) ; renvoie [(nom, flottants)].
    Les WAV sont gardés dans samples/voix/ (réutilisables avec wav2smp.py)."""
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise SystemExit("espeak est nécessaire pour les banques de voix")
    out_dir = os.path.join(ROOT, "voix")
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for name, text in words:
        path = os.path.join(out_dir, f"{prefix}_{name.lower()}.wav")
        subprocess.run([exe, "-v", "fr", "-s", "150", "-w", path, text], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        x, rate = wav2smp.read_wav(path)
        out.append((name, wav2smp.trim(x), rate))
    return out


def chiffres(rng):
    words = [("ZERO", "zéro"), ("UN", "un"), ("DEUX", "deux"), ("TROIS", "trois"),
             ("QUATRE", "quatre"), ("CINQ", "cinq"), ("SIX", "six"), ("SEPT", "sept"),
             ("HUIT", "huit"), ("NEUF", "neuf"), ("DIX", "dix")]
    return [(n, x, 6250, 2.0, r) for n, x, r in espeak_words(words, "chiffre")]


def mots(rng):
    words = [("ALLEZ", "allez"), ("OUI", "oui"), ("NON", "non"), ("ENCORE", "encore"),
             ("STOP", "stop"), ("GO", "go"), ("HE", "hé"), ("BOUM", "boum"),
             ("DANSE", "danse"), ("SUPER", "super"), ("OUAIS", "ouais"), ("BRAVO", "bravo"),
             ("CPC", "cé pé cé"), ("MUSIQ", "musique")]
    # 6 000 Hz (et non 6 250) : la banque doit tenir en 16 064 octets
    return [(n, x, 6000, 2.0, r) for n, x, r in espeak_words(words, "mot")]


BANKS = [("BATTERI2", batteri2), ("PERCUS", percus), ("EFFETS", effets),
         ("BASSES", basses), ("NOTES", notes), ("CHIFFRES", chiffres), ("MOTS", mots)]


def build_bank(name, make):
    """Construit une banque ; renvoie (chemin, octets, samples)."""
    rng = random.Random(6128)
    samples = []
    for item in make(rng):
        sname, x, rate, drv = item[:4]
        src_rate = item[4] if len(item) > 4 else SR
        s = wav2smp.convert(x, src_rate, sname, rate=rate, drive_amount=drv)
        samples.append(s)
        wav2smp.write_wav(os.path.join(ROOT, "ecoute", f"{name}_{s.name.strip()}_ecoute.wav"),
                          wav2smp.render(wav2smp.unpack(s.data)), s.rate)
    raw = wav2smp.build_bank(samples)
    path = os.path.join(ROOT, name + ".SMP")
    open(path, "wb").write(raw)
    return path, raw, samples


def main():
    os.makedirs(os.path.join(ROOT, "ecoute"), exist_ok=True)
    built = []
    for name, make in BANKS:
        path, raw, samples = build_bank(name, make)
        size = wav2smp.check_sizes(raw)
        print("%-9s %5d octets, %2d samples : %s" % (
            name + ".SMP", size, len(samples), " ".join(s.name.strip() for s in samples)))
        if size > wav2smp.BANK_MAX_MAIN:
            raise SystemExit(f"{name} : trop grande pour la mémoire du CPC")
        built.append((name + ".SMP", raw))
    if "--dsk" in sys.argv:
        import amsdsk
        dsk = os.path.join(ROOT, "..", "build", "seq16-fr.dsk")
        for fname, raw in built:
            amsdsk.add_file(dsk, fname, raw)
        print(f"{len(built)} banques ajoutées à build/seq16-fr.dsk")


if __name__ == "__main__":
    main()
