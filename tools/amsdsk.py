"""amsdsk.py : ajouter ou relire un fichier dans une disquette CPC (.dsk).

Rôle
----
RASM fabrique build/seq16-fr.dsk avec le programme SEQ16.BIN. Ce module ajoute
d'autres fichiers sur la même disquette (banques .SMP et .INS).

Depuis la fusion avec CPC DISK, le format est géré par la bibliothèque de
CPC DISK (cpc_dsk/core/amsdos.py : catalogue AMSDOS, formats DATA et
SYSTEM), trouvée par tools/cpcdisk.py. Ce module garde seulement
l'interface qu'utilisent build.bat, les générateurs et les tests.

Mode d'emploi
-------------
    python tools/amsdsk.py build/seq16-fr.dsk samples/DRUMS.SMP     # ajoute
    python tools/amsdsk.py build/seq16-fr.dsk --list                 # catalogue

Depuis Python :  add_file(chemin_dsk, "DRUMS.SMP", données)
                 read_file(chemin_dsk, "DRUMS.SMP") -> données (sans en-tête)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpcdisk  # noqa: E402

amsdos = cpcdisk.charger()
from cpc_dsk.core.adf import ADFDisk, ADFError  # noqa: E402
from cpc_dsk.core.cpcfs import CpcError  # noqa: E402


class Disk:
    """Accès brut aux secteurs par ID (pour le simulateur : BIOS READ SECTOR).

    ``raw`` : l'image ; ``sect_off[(piste, ID)]`` : position du secteur."""

    def __init__(self, raw):
        try:
            disk = ADFDisk(bytes(raw))
        except ADFError as exc:
            raise ValueError(str(exc))
        self.raw = bytearray(raw)
        self.sect_off = {}
        for t in range(disk.num_tracks):
            ids = amsdos._track_ids(disk, t)
            if not ids:
                continue
            size = (disk.track_sizes[t] - 256) // len(ids)
            base = disk.track_offsets[t] + 256
            for i, sid in enumerate(ids):
                self.sect_off[(t, sid)] = base + i * size


def amsdos_header(name, length, load=0x0000, entry=0x0000):
    """En-tête AMSDOS de 128 octets pour un fichier binaire (type 2)."""
    return amsdos.build_header(amsdos.to_field11(name), length, 2, load, entry)


def _ouvrir(dsk_path):
    try:
        disk = ADFDisk.load(dsk_path)
        if amsdos.detect_format(disk) is not amsdos.DATA:
            raise ValueError("disquette au format DATA (#C1) attendue")
        return disk, amsdos.AmsdosFilesystem(disk)
    except (ADFError, CpcError) as exc:
        raise ValueError(str(exc))


def add_file(dsk_path, name, data, load=0x0000):
    """Ajoute (ou remplace) un fichier binaire AMSDOS dans l'image .dsk.

    Renvoie la taille écrite, en-tête compris."""
    disk, fs = _ouvrir(dsk_path)
    try:
        fs.write_file(name, bytes(data), load_addr=load, exec_addr=0,
                      mode="amsdos", overwrite=True)
    except CpcError as exc:
        raise ValueError(str(exc))
    disk.save(dsk_path)
    return 128 + len(data)


def remove_file(dsk_path, name):
    """Efface un fichier (ses entrées passent à #E5). True s'il existait."""
    disk, fs = _ouvrir(dsk_path)
    if fs.find(name) is None:
        return False
    fs.delete_file(name)
    disk.save(dsk_path)
    return True


def read_file(dsk_path, name, keep_header=False):
    """Relit un fichier ; renvoie les données sans l'en-tête AMSDOS."""
    _, fs = _ouvrir(dsk_path)
    if fs.find(name) is None:
        raise FileNotFoundError(name + " absent de la disquette")
    return fs.read_raw(name) if keep_header else fs.read_file(name)


def list_files(dsk_path):
    """{nom: taille au catalogue (multiple de 128 octets)}."""
    _, fs = _ouvrir(dsk_path)
    return {f.name: f.records * 128 for f in fs.list_files()}


def main():
    p = argparse.ArgumentParser(description="Ajoute des fichiers à une disquette CPC")
    p.add_argument("dsk")
    p.add_argument("fichiers", nargs="*")
    p.add_argument("--list", action="store_true", help="affiche le catalogue")
    a = p.parse_args()
    for f in a.fichiers:
        n = add_file(a.dsk, os.path.basename(f), open(f, "rb").read())
        print("%s ajouté à %s (%d octets avec en-tête)" % (os.path.basename(f), a.dsk, n))
    if a.list or not a.fichiers:
        for n, size in list_files(a.dsk).items():
            print("  %-12s %6d octets" % (n, size))


if __name__ == "__main__":
    sys.exit(main())
