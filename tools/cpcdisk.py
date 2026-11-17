"""cpcdisk.py : trouver la bibliothèque disque de CPC DISK (paquet cpc_dsk).

SEQ-16 ne gère plus lui-même le format des disquettes : il utilise le
catalogue AMSDOS de CPC DISK (cpc_dsk/core/amsdos.py), le projet voisin.

Recherche, dans l'ordre :
1. le paquet installé (pip install -e ../CPC-DISK) ;
2. le dossier donné par la variable d'environnement CPC_DISK ;
3. un dossier voisin CPC-DISK (ou AmstradCPC, son ancien nom), en
   remontant depuis ce fichier : _Codes/CPC-SEQ-16 et _Codes/CPC-DISK.
"""
import os
import sys

NOMS_VOISINS = ("CPC-DISK", "CPC DISK", "AmstradCPC")


def _candidats():
    env = os.environ.get("CPC_DISK")
    if env:
        yield env
    ici = os.path.dirname(os.path.abspath(__file__))
    while True:
        parent = os.path.dirname(ici)
        for nom in NOMS_VOISINS:
            yield os.path.join(parent, nom)
        if parent == ici:
            return
        ici = parent


def charger():
    """Importe cpc_dsk.core.amsdos (et l'ajoute au chemin si besoin)."""
    try:
        from cpc_dsk.core import amsdos
        return amsdos
    except ImportError:
        pass
    for dossier in _candidats():
        if os.path.isfile(os.path.join(dossier, "cpc_dsk", "core", "amsdos.py")):
            sys.path.insert(0, dossier)
            from cpc_dsk.core import amsdos
            return amsdos
    raise ImportError(
        "Bibliothèque CPC DISK introuvable (cpc_dsk/core/amsdos.py).\n"
        "  - placer le projet CPC-DISK à côté de CPC-SEQ-16 (et faire git pull),\n"
        "  - ou : pip install -e ../CPC-DISK\n"
        "  - ou : définir la variable CPC_DISK=<dossier de CPC-DISK>")
