"""Génère src/smptables.asm : les tables de la lecture des samples.

- smp_curves     5 courbes x 16 octets : code lu -> code écrit dans l'AY.
                 Ce sont EXACTEMENT les tables de wav2smp.py (mêmes calculs),
                 pour que le WAV d'écoute sur PC et le CPC sonnent pareil.
- smp_pitch      25 multiplicateurs (mots de 16 bits) pour jouer un sample
                 de -12 à +12 demi-tons : durée d'un échantillon =
                 code x smp_pitch[n + 12] / 256, avec
                 smp_pitch[n + 12] = 256 x 2^(-n/12), arrondi.
- smp_decims     les 6 valeurs de décimation (1, 2, 3, 4, 6, 8)
- smp_masks      les 4 masques de bits (4, 3, 2, 1 bits)
- smp_curve_names  noms des courbes, 8 caractères chacun

Lancer :  python tools/gen_smp_tables.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wav2smp  # noqa: E402

NAMES = ["LINEAIRE", "LOG     ", "SATUREE ", "REPLIEE ", "INVERSEE"]


def pitch_table():
    return [round(256 * 2 ** (-n / 12)) for n in range(-12, 13)]


def main():
    out = ["; Fichier généré par tools/gen_smp_tables.py - ne pas modifier à la main.",
           "", "; Courbes : code lu dans le sample -> code écrit dans le registre de volume.",
           "smp_curves:"]
    for name, t in zip(wav2smp.CURVES, wav2smp.CURVE_TABLES):
        out.append("        db " + ",".join("%2d" % v for v in t) + "   ; " + name)
    out += ["", "; Hauteur : multiplicateur de la durée d'un échantillon (x/256),",
            "; de -12 à +12 demi-tons.", "smp_pitch:"]
    p = pitch_table()
    for i in range(0, 25, 8):
        out.append("        dw " + ",".join(str(v) for v in p[i:i + 8]))
    out += ["", "smp_decims:", "        db " + ",".join(str(d) for d in wav2smp.DECIMS),
            "", "; Masques pour 4, 3, 2 et 1 bits", "smp_masks:",
            "        db " + ",".join("#%X" % wav2smp.BITS_MASK[b] for b in (4, 3, 2, 1)),
            "", "smp_bits_txt:", '        db "4321"',
            "", "smp_curve_names:"]
    for n in NAMES:
        out.append('        db "%s"' % n)
    out.append("")
    path = os.path.join(HERE, "..", "src", "smptables.asm")
    open(path, "w", encoding="utf-8").write("\n".join(out))
    print("src/smptables.asm écrit")


if __name__ == "__main__":
    main()
