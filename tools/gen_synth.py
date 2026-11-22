"""gen_synth.py : SYNTH, la song synthwave d'usine.

C'est le morceau du démarrage (et de N N, nouveau morceau) : ses motifs et
son enchaînement sont compressés dans src/factory_song.asm, décompressés au
démarrage par src/boot.asm.  Elle est aussi livrée en fichier sur les
disquettes du programme.

    src/factory_song.asm      les 32 motifs et le bloc v3, compressés
    usine/SYNTH.SNG           le morceau (instruments d'usine, sans sample)
    build/seq16-fr.dsk, -en, -es : SYNTH.SNG ajouté (--disks)

    python tools/gen_synth.py [--disks]

La mineur, 108 BPM, la grille du synthwave : Am - F - C - G.  Seulement
les instruments et les sons composés d'usine.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import gen_songs as gs  # noqa: E402
import gen_screen  # noqa: E402
from gen_patterns import R, L, G, NK, fx  # noqa: E402
from gen_songs import song, poly, mono  # noqa: E402

_saved = list(gs.SONGS)
del gs.SONGS[:]

synth = song(
    "SYNTH", "Synth", "synthwave", 108, "A:min",
    "La mineur : Am - F - C - G, basse en octaves, arpèges, lead avec vibrato, "
    "accords en son composé",
    volumes=(15, 13, 13, 14),
    order=["SYINTRO", "SYDRIVE", "SYDRIVE2", "SYDRIVE", "SYDRIVE2",
           "SYREFR", "SYREFR", "SYPONT", "SYREFR", "SYFIN"],
    loop="SYDRIVE",
    tests="le morceau du démarrage ; FX 72/73 vibrato, 42/43 roulement, "
          "14 montée, 44 accords répétés")

# Motif 1 (le premier affiché au démarrage) : voix séparées
poly(synth, "SYDRIVE", "couplet : Am - F, basse en octaves, arpèges, lead",
     A=R("x.x.x.x.x.x.x.x.", "A2 A3 A2 A3 F2 F3 F2 F3", "BASS"),
     B=L("A3@ARPMIN . . . . . . - F3@ARP . . . . . . -"),
     C=L("E4@VIBRA . . . C5@VIBRA . . - A4@VIBRA . C5@VIBRA . . . . -"),
     N=fx(G("k.h.s.h.k.hks.s.", NK), {14: 0x42}))
mono(synth, "SYINTRO", "intro : accords Am7, F, C, G en son composé, vibrato",
     R("x...x...x...x..-", "A3@6~72 F3@1~72 C4@1~72 G3@1~72"))
poly(synth, "SYDRIVE2", "couplet : C - G",
     A=R("x.x.x.x.x.x.x.x.", "C2 C3 C2 C3 G2 G3 G2 G3", "BASS"),
     B=L("C4@ARP . . . . . . - G3@ARP . . . . . . -"),
     C=L("G4@VIBRA . . . E4@VIBRA . . - D4@VIBRA . G4@VIBRA . B4@VIBRA~72 . . -"),
     N=G("k.h.s.h.k.hks.h.", NK))
poly(synth, "SYREFR", "refrain : Am - F - C - G, lead qui monte (14), roulement (43)",
     A=R("x.x.x.x.x.x.x.x.", "A2 A3 F2 F3 C2 C3 G2 G3", "BASS"),
     B=L("A4@LEAD . C5@LEAD . F4@LEAD . A4@LEAD . G4@LEAD . E4@LEAD . D4@LEAD . B4@LEAD~14 -"),
     C=L("A3@ARPMIN . . - F3@ARP . . - C4@ARP . . - G3@ARP . . -"),
     N=fx(G("x.h.s.h.k.h.s.ss", NK), {14: 0x43}))
mono(synth, "SYPONT", "pont : accords F - G qui se répètent (44)",
     R("x..x..x.x..x..x-", "F3@1 F3@1~44 F3@1 G3@1 G3@1~44 G3@1"))
poly(synth, "SYFIN", "fin : la mineur tenu, vibrato",
     A=R("x..............-", "A2", "BASS"),
     B=L("A3@ARPMIN . . . . . . . . . . . . . . -"),
     C=L("E4@VIBRA~73 . . . . . . . . . . . . . . -"),
     N=G("x...............", NK))

SYNTH = synth
gs.SONGS[:] = _saved


def check():
    err = gs.check_song(SYNTH)
    if err:
        raise SystemExit("\n".join("SYNTH : " + e for e in err))


def parts():
    """(les 32 motifs, 32 x 260 octets ; le bloc v3, 450 octets)."""
    pats = [data for _, data in gs.encode_patterns(SYNTH)]
    pats += [gs.EMPTY_PAT] * (gs.NB_PAT - len(pats))
    return b"".join(pats), gs.v3_block(SYNTH)


def song_asm():
    pats, v3 = parts()
    zp, zv = gen_screen.lz_pack(pats), gen_screen.lz_pack(v3)
    assert gen_screen.lz_unpack(zp, len(pats)) == pats
    assert gen_screen.lz_unpack(zv, len(v3)) == v3

    def dump(label, data):
        out = [label + ":"]
        for i in range(0, len(data), 16):
            out.append("        db " + ",".join("#%02X" % b for b in data[i:i + 16]))
        return out
    out = ["; Fichier généré par tools/gen_synth.py - ne pas modifier à la main.",
           "; SYNTH, la song synthwave d'usine : les 32 motifs (%d octets) et le" % len(pats),
           "; bloc v3 (%d octets), compressés comme l'écran de chargement" % len(v3),
           "; (tools/gen_screen.py, lz_pack) : %d + %d octets." % (len(zp), len(zv)), ""]
    out += dump("factory_pats_lz", zp) + [""] + dump("factory_v3_lz", zv) + [""]
    return "\n".join(out)


def write_all(disks=False):
    import amsdsk
    check()
    with open(os.path.join(ROOT, "src", "factory_song.asm"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(song_asm())
    os.makedirs(os.path.join(ROOT, "usine"), exist_ok=True)
    data = gs.song_file(SYNTH)
    with open(os.path.join(ROOT, "usine", "SYNTH.SNG"), "wb") as fh:
        fh.write(data)
    if disks:
        for lang in ("fr", "en", "es"):
            dsk = os.path.join(ROOT, "build", "seq16-%s.dsk" % lang)
            amsdsk.add_file(dsk, "SYNTH.SNG", data)
            print("%s : SYNTH.SNG ajouté" % dsk)


if __name__ == "__main__":
    write_all("--disks" in sys.argv)
    print("src/factory_song.asm et usine/SYNTH.SNG écrits")
