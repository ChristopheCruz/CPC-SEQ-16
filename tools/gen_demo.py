"""gen_demo.py : la disquette de démonstration de SEQ-16.

Deux morceaux, avec leurs motifs, leurs instruments et leurs samples :

    ARCADE   chiptune, SANS sample : l'intro et le refrain en son composé
             (une voix qui joue un accord), le thème et le pont en voix
             séparées ; les 7 effets des pas (FX) y sont tous.
    STUDIO   ce que l'on peut faire avec les samples : batterie en
             digidrums (KICK, SNARE, HAT, CLAP), un crash, et un sample
             long, la voix « SEQ seize » (elle prend tout le processeur
             pendant qu'elle joue : les autres sons s'arrêtent, c'est
             normal).

    samples/STUDIO.SMP        la banque du morceau STUDIO (DRUMS, SEQ16, CRASH)
    demo/NOM.SNG, NOM.INS     les morceaux et leurs instruments
    demo/pat/*.PAT            tous leurs motifs
    demo/LISTE.md             ce que contient la disquette
    build/seq16-demo-fr.dsk   SEQ16.BIN (français) et tout ce qui précède
    build/seq16-demo-en.dsk   pareil, programme en anglais
    build/seq16-demo-es.dsk   pareil, programme en espagnol

    python tools/gen_demo.py      (après build.bat : il faut build/seq16*.dsk)

Les motifs sont écrits avec le petit langage de gen_patterns.py ; « ~XX »
ajoute l'effet XX à une note (A3@LEAD~37 : arpège à la quinte), fx() en
pose sur des notes déjà écrites (batterie).
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import gen_songs as gs  # noqa: E402
import gen_patterns as gp  # noqa: E402
import wav2smp  # noqa: E402
from gen_patterns import R, L, G, NK, DK, fx, merge  # noqa: E402
from gen_songs import ins, song, poly, mono  # noqa: E402

DIGI = gp.DIGI

# Les morceaux de test de gen_songs restent à part : on construit les nôtres
# dans une liste vide.
_saved = list(gs.SONGS)
del gs.SONGS[:]

# ============================================================================
# 1. ARCADE : chiptune sans sample, son composé et effets des pas
# ============================================================================
arcade = song(
    "ARCADE", "Arcade", "chiptune (son composé, effets)", 132, "A:min",
    "La mineur : intro et refrain en son composé (accords d'une seule voix), "
    "thème et pont en voix séparées, les 7 effets des pas",
    volumes=(14, 13, 12, 14),
    instruments=[(ins("ARCLD", d=6, s=11, r=8, v=14), "lead"),
                 (ins("ARCBS", d=12, s=9, r=14), "bass"),
                 (ins("ARCPL", d=24, s=0, r=10, v=13), "pluck"),
                 (ins("ARCPD", a=12, d=2, s=12, r=6, v=12), "chord")],
    order=["ARINTRO", "ARTHEME", "ARTHEME", "ARCHORUS", "ARCHORUS",
           "ARBRIDGE", "ARTHEME", "ARCHORUS", "ARFIN"],
    loop="ARTHEME",
    tests="son composé (intro, refrain) ; FX : 73 vibrato, 37/34 arpège, "
          "22 descend, 42 répète (roulement), 44 répète (accords), 52 coupe, "
          "14 monte, 62 retard (swing), 2C descend (laser)")

mono(arcade, "ARINTRO", "intro : accords mineur 7 et majeur, vibrato (FX 73)",
     R("x......-x......-", "A3@6~73 F3@1~73"))
poly(arcade, "ARTHEME", "thème : arpège à la quinte (37), vibrato (73), basse qui descend (22)",
     A=fx(R("x.xxx.x-x.xxx.x-", "A2 A2 A3 A2 A2 F2 F2 F3 F2 F2", "ARCBS"), {14: 0x22}),
     B=L("A4@ARCLD . C5@ARCLD . E5@ARCLD . . - F4@ARCLD . A4@ARCLD . C5@ARCLD~73 . . -"),
     C=L("A3@ARCPL~37 . . . A3@ARCPL~37 . . . F3@ARCPL~34 . . . F3@ARCPL~34 . . ."),
     N=fx(G("k.h.s.hhk.h.s.s.", NK), {14: 0x42}))
mono(arcade, "ARCHORUS", "refrain : accords qui se répètent (44)",
     R("x..x..x.x..x..x-", "A3@0 A3@0~44 A3@0 F3@1 F3@1~44 G3@1"))
poly(arcade, "ARBRIDGE", "pont : basse coupée (52), lead qui monte (14), charleston en retard (62)",
     A=fx(R("x.x.x.x.x.x.x.x.", "D2 D2 D2 D2 E2 E2 E2 E2", "ARCBS"),
          {s: 0x52 for s in range(0, 16, 2)}),
     B=L("D4@ARCLD~14 . . . . . . - E4@ARCLD~14 . . . . . . -"),
     C=L("F3@ARCPD . . . . . . - G3@ARCPD . . . . . . -"),
     N=fx(G("h.h.h.h.h.h.h.h.", NK), {2: 0x62, 6: 0x62, 10: 0x62, 14: 0x62}))
poly(arcade, "ARFIN", "fin : accord tenu, vibrato, chute en laser (2C)",
     A=R("x..............-", "A2", "ARCBS"),
     B=L("A4@ARCLD~73 . . . . . . . . . . . . . . -"),
     C=L(". . . . . . . . E4@ARCPL~2C . . . . . . -"),
     N=G("x...............", NK))

# ============================================================================
# 2. STUDIO : les samples (digidrums, crash, voix longue)
# ============================================================================
studio = song(
    "STUDIO", "Studio", "samples (digidrums, voix)", 100, "D:min",
    "Ré mineur : batterie en samples (DRUMS), crash, et la voix « SEQ seize », "
    "un sample long qui ouvre le morceau et revient au break",
    volumes=(14, 13, 15, 14), bank="STUDIO",
    instruments=[(ins("VOIX", f=DIGI, n=4), "pluck"),
                 (ins("CRASH", f=DIGI, n=5), "pluck"),
                 (ins("STBS", d=12, s=10, r=16), "bass"),
                 (ins("STLD", d=6, s=12, r=10, vd=2, vs=36, vdel=16), "lead")],
    order=["STINTRO", "STBEAT", "STBEAT2", "STBEAT", "STBEAT2",
           "STVOIX", "STBEAT", "STBEAT2", "STFIN"],
    loop="STBEAT",
    tests="banque STUDIO.SMP chargée avec le morceau ; la voix (sample long) "
          "arrête les autres sons pendant qu'elle joue ; crash au début des "
          "mesures paires")

poly(studio, "STINTRO", "la voix « SEQ seize », puis le charleston",
     C=merge(L("C4@VOIX . . . . . . . . . . . . . . ."),
             G("..........H.H.HH", DK)))
poly(studio, "STBEAT", "rythme : basse, lead, batterie en samples",
     A=R("x..x..x.x..x..x-", "D2 D2 D3 C2 C2 C3", "STBS"),
     B=L("D4@STLD . F4@STLD . A4@STLD . . - C4@STLD . E4@STLD . G4@STLD . . -"),
     C=G("K.H.S.H.K.HKS.H.", DK))
poly(studio, "STBEAT2", "variante : crash, clap",
     A=R("x..x..x.x..x..x-", "D2 D2 D3 C2 C2 C3", "STBS"),
     B=L("A4@STLD . . - F4@STLD . . - G4@STLD . . - E4@STLD . . -"),
     C=merge(G("..H.S.H.K.HKC.C.", DK), L("C4@CRASH . . . . . . . . . . . . . . .")))
poly(studio, "STVOIX", "break : la voix, puis la basse repart",
     A=R("........x..x..x-", "D2 D2 C2", "STBS"),
     C=merge(L("C4@VOIX . . . . . . . . . . . . . . ."),
             G("........K.H.S.H.", DK)))
poly(studio, "STFIN", "fin : crash et ré mineur tenu",
     A=R("x..............-", "D2", "STBS"),
     B=L("D4@STLD . . . . . . . . . . . . . . -"),
     C=L("C4@CRASH . . . . . . . . . . . . . . ."))

DEMO = list(gs.SONGS)
gs.SONGS[:] = _saved


# ============================================================================
# Fabrication
# ============================================================================
def studio_bank():
    """STUDIO.SMP : DRUMS (0 KICK, 1 SNARE, 2 HAT, 3 CLAP : les digidrums
    d'usine), 4 SEQ16 (VOIX.SMP), 5 CRASH (BATTERI2.SMP)."""
    def bank(name):
        with open(os.path.join(ROOT, "samples", name + ".SMP"), "rb") as fh:
            return wav2smp.parse_bank(fh.read())
    drums = bank("DRUMS")
    voix = {s.name: s for s in bank("VOIX")}
    batt = {s.name: s for s in bank("BATTERI2")}
    return wav2smp.build_bank(list(drums) + [voix["SEQ16"], batt["CRASH"]])


def check():
    problems = []
    for s in DEMO:
        problems += ["%s : %s" % (s["name"], e) for e in gs.check_song(s)]
    if problems:
        raise SystemExit("\n".join(problems))


def liste_md():
    out = ["# Disquette de démonstration", "",
           "Fabriquée par `tools/gen_demo.py` : `build/seq16-demo-fr.dsk` (et `-en`, `-es`).", ""]
    for s in DEMO:
        pos, loop = gs.positions(s)
        out += ["## %s (%s, %d BPM, %s)" % (s["name"], s["style"], s["bpm"], s["key"]), "",
                s["desc"] + ".", "",
                "Enchaînement : " + " ".join(s["order"]) + " (boucle : %s)." % s["loop"], "",
                "| Motif | Mode | Contenu |", "|---|---|---|"]
        for p in s["patterns"]:
            mode = "son composé" if p["mode"] == gp.MONO else "voix séparées"
            out.append("| %s | %s | %s |" % (p["name"], mode, p["desc"]))
        out += ["", "À écouter : " + s["tests"] + ".", ""]
    return "\n".join(out)


def write_all():
    import amsdsk
    check()
    smp = studio_bank()
    with open(os.path.join(ROOT, "samples", "STUDIO.SMP"), "wb") as fh:
        fh.write(smp)
    out = os.path.join(ROOT, "demo")
    pat_dir = os.path.join(out, "pat")
    os.makedirs(pat_dir, exist_ok=True)
    for d in (out, pat_dir):
        for f in os.listdir(d):
            if f.upper().endswith((".SNG", ".INS", ".PAT")):
                os.remove(os.path.join(d, f))
    files = []
    for s in DEMO:
        files.append((s["name"] + ".SNG", gs.song_file(s)))
        files.append((s["name"] + ".INS", gs.ins_bank(s)))
    for s in DEMO:
        for name, data in gs.encode_patterns(s):
            files.append((name + ".PAT", data))
    for name, data in files:
        sub = pat_dir if name.endswith(".PAT") else out
        with open(os.path.join(sub, name), "wb") as fh:
            fh.write(data)
    with open(os.path.join(out, "LISTE.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(liste_md())
    with open(os.path.join(ROOT, "samples", "DRUMS.SMP"), "rb") as fh:
        drums = fh.read()
    files += [("STUDIO.SMP", smp), ("DRUMS.SMP", drums)]
    disks = []
    for suffix in ("-fr", "-en", "-es"):
        src = os.path.join(ROOT, "build", "seq16%s.dsk" % suffix)
        dsk = os.path.join(ROOT, "build", "seq16-demo%s.dsk" % suffix)
        shutil.copy(src, dsk)
        for name in amsdsk.list_files(dsk):
            if name not in ("SEQ16", "SEQ16.SCR", "SEQ16.BIN"):
                amsdsk.remove_file(dsk, name)
        for name, data in files:
            amsdsk.add_file(dsk, name, data)
        disks.append(dsk)
    return disks, len(files)


def main():
    disks, n = write_all()
    for s in DEMO:
        print("%-6s %3d BPM  %d motifs  banque : %s" % (s["name"], s["bpm"], len(s["patterns"]),
                                                       s["bank"] or "aucune"))
    for d in disks:
        print("%s : SEQ16.BIN et %d fichiers" % (d, n))


if __name__ == "__main__":
    main()
