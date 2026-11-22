"""gen_drums.py : fabrique la banque d'usine samples/DRUMS.SMP par synthèse.

Rôle
----
Les 4 sons de batterie sont calculés ici (sinus à hauteur descendante, bruit
filtré). Aucun échantillon venu d'ailleurs : pas de question de droits.
Le hasard utilise une graine fixe : deux exécutions donnent le même fichier.

Sorties
-------
    samples/synth/*.wav        sons de synthèse en 44,1 kHz (réutilisables
                               avec wav2smp.py et d'autres réglages)
    samples/DRUMS.SMP          la banque (moins de 4 Ko : marche aussi sur 464)
    samples/ecoute/*.wav       ce que le CPC rendra, à écouter sur PC

Ordre des samples (les instruments d'usine DGKICK, DGSNARE, DGHAT, DGCLAP
pointent sur 0, 1, 2, 3) : KICK, SNARE, HAT, CLAP. Chacun dure moins de
150 ms, la limite des digidrums en mode BLOQUANT.

Mode d'emploi :  python tools/gen_drums.py [--dsk]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wav2smp  # noqa: E402

SR = 44100
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "samples")


def env(t, decay):
    """Chute exponentielle : vaut 1 à t = 0, 1/e au bout de « decay » s."""
    return math.exp(-t / decay)


def onepole_lp(x, cutoff):
    a = 1 - math.exp(-2 * math.pi * cutoff / SR)
    y, out = 0.0, []
    for v in x:
        y += a * (v - y)
        out.append(y)
    return out


def onepole_hp(x, cutoff):
    lp = onepole_lp(x, cutoff)
    return [v - l for v, l in zip(x, lp)]


def noise(n, rng):
    return [rng.uniform(-1, 1) for _ in range(n)]


def kick(rng):
    n = int(0.148 * SR)
    out, phase = [], 0.0
    for i in range(n):
        t = i / SR
        f = 45 + 110 * math.exp(-t / 0.025)     # 155 Hz -> 45 Hz
        phase += 2 * math.pi * f / SR
        click = 0.6 * env(t, 0.002) * rng.uniform(-1, 1)
        out.append(math.sin(phase) * env(t, 0.06) + click)
    return out


def snare(rng):
    n = int(0.14 * SR)
    body = onepole_lp(onepole_hp(noise(n, rng), 1200), 6000)
    out = []
    for i in range(n):
        t = i / SR
        tone = 0.5 * math.sin(2 * math.pi * 190 * t) * env(t, 0.03)
        out.append(2.5 * body[i] * env(t, 0.045) + tone)
    return out


def hat(rng):
    n = int(0.06 * SR)
    b = onepole_hp(onepole_hp(noise(n, rng), 6000), 6000)
    return [b[i] * env(i / SR, 0.015) for i in range(n)]


def clap(rng):
    n = int(0.14 * SR)
    b = onepole_lp(onepole_hp(noise(n, rng), 800), 2500)
    out = []
    for i in range(n):
        t = i / SR
        # trois claquements rapprochés puis une queue
        bursts = sum(env(t - s, 0.004) for s in (0.0, 0.011, 0.022) if t >= s)
        tail = env(t - 0.022, 0.04) if t >= 0.022 else 0.0
        out.append(b[i] * (bursts + tail))
    return out


# nom, synthèse, fréquence de lecture sur CPC, saturation (--drive)
# Le silence tombe sur le niveau 12 de l'AY et les petits écarts s'y écrasent :
# la saturation remonte les queues de son (et salit, ce qui est voulu).
DRUMS = [("KICK", kick, 6250, 1.5), ("SNARE", snare, 8000, 3.0),
         ("HAT", hat, 12500, 2.5), ("CLAP", clap, 8000, 3.0)]


def build():
    rng = random.Random(6128)
    os.makedirs(os.path.join(ROOT, "synth"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "ecoute"), exist_ok=True)
    samples = []
    for name, fn, rate, drv in DRUMS:
        x = wav2smp.normalize(fn(rng))
        wav2smp.write_wav(os.path.join(ROOT, "synth", name.lower() + ".wav"),
                          [0.9 * v for v in x], SR)
        s = wav2smp.convert(x, SR, name, rate=rate, drive_amount=drv)
        samples.append(s)
        wav2smp.write_wav(os.path.join(ROOT, "ecoute", "DRUMS_%s_ecoute.wav" % name),
                          wav2smp.render(wav2smp.unpack(s.data)), s.rate)
    raw = wav2smp.build_bank(samples)
    path = os.path.join(ROOT, "DRUMS.SMP")
    open(path, "wb").write(raw)
    return path, raw, samples


def main():
    path, raw, samples = build()
    size = wav2smp.check_sizes(raw)
    print("samples/DRUMS.SMP : %d octets (%d de données)" % (len(raw), size))
    for s in samples:
        print("  %-6s %4d octets  %3.0f ms à %5.0f Hz" %
              (s.name, len(s.data), 1000 * s.seconds, s.rate))
    if "--dsk" in sys.argv:
        import amsdsk
        dsk = os.path.join(ROOT, "..", "build", "seq16-fr.dsk")
        amsdsk.add_file(dsk, "DRUMS.SMP", raw)
        print("DRUMS.SMP ajouté à build/seq16-fr.dsk")


if __name__ == "__main__":
    main()
