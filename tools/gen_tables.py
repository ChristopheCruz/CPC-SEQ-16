"""Génère src/tables.asm : tables calculées une fois pour toutes.

- note_periods : périodes AY des notes (horloge AY du CPC = 1 MHz),
                 période = 1 000 000 / (16 x fréquence) = 62500 / fréquence
- note_names   : noms des 12 notes, 2 caractères chacun
- vol_table    : volume final = niveau d'enveloppe x volume d'instrument / 15
"""
NAMES = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]
out = ["; Fichier généré par tools/gen_tables.py - ne pas modifier à la main.", "",
       "; Périodes AY (12 bits) : octaves 0 à 7, 12 notes par octave.",
       "note_periods:"]
for octave in range(8):
    vals = []
    for n in range(12):
        midi = 12 * (octave + 1) + n            # C4 = 60, A4 = 69 = 440 Hz
        freq = 440.0 * 2 ** ((midi - 69) / 12)
        vals.append(min(4095, round(62500 / freq)))
    out.append("        dw " + ",".join(str(v) for v in vals) + "   ; octave %d" % octave)
out += ["", "; Noms des notes, 2 caractères chacun.", "note_names:",
        '        db "' + "".join(NAMES) + '"', "",
        "; vol_table[16 x volume d'instrument + niveau] = volume envoyé à l'AY",
        "vol_table:"]
for iv in range(16):
    out.append("        db " + ",".join(str(round(v * iv / 15)) for v in range(16)))
out.append("")
open("src/tables.asm", "w", encoding="utf-8").write("\n".join(out))
print("src/tables.asm écrit")
