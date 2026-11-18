"""bank_disks.py : les disquettes de banques, sans le programme.

    build/seq16-sons.dsk      les 13 banques d'instruments .INS
    build/seq16-samples.dsk   les 9 banques de samples .SMP

Elles servent de disquettes de données : sur le CPC (ou le Gotek), on
change de disquette puis on charge une banque (f3 : O pour un .INS,
D pour un .SMP ; f2 : O, f4 : O pour prendre un seul son).

    python tools/bank_disks.py
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cpcdisk  # noqa: E402

amsdos = cpcdisk.charger()
from cpc_dsk.core.adf import ADFDisk  # noqa: E402
import lang  # noqa: E402  (ordre des banques, le même que build.bat)

DISQUES = {
    "seq16-sons.dsk": [p for p in lang.BANKS if p.endswith(".INS")],
    "seq16-samples.dsk": [p for p in lang.BANKS if p.endswith(".SMP")],
}


def fabriquer(nom, fichiers):
    disk = ADFDisk.new_blank()
    fs = amsdos.AmsdosFilesystem(disk)
    for rel in fichiers:
        with open(os.path.join(ROOT, rel), "rb") as fh:
            fs.write_file(os.path.basename(rel), fh.read(), mode="amsdos")
    chemin = os.path.join(ROOT, "build", nom)
    disk.save(chemin)
    return chemin, len(fichiers), fs.free_bytes() // 1024


def main():
    # Toutes les banques du dépôt doivent être sur une disquette.
    presentes = {os.path.relpath(p, ROOT).replace(os.sep, "/")
                 for ext in ("samples/*.SMP", "instruments/*.INS")
                 for p in glob.glob(os.path.join(ROOT, ext))}
    oubliees = presentes - set(lang.BANKS)
    if oubliees:
        raise SystemExit("banques absentes de lang.BANKS : " + ", ".join(sorted(oubliees)))
    for nom, fichiers in DISQUES.items():
        chemin, n, libre = fabriquer(nom, fichiers)
        print(f"OK : {chemin} ({n} banques, {libre} Ko libres)")


if __name__ == "__main__":
    main()
