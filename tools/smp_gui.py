"""smp_gui.py : l'éditeur graphique de banques .SMP.

Il fait maintenant partie de CPC DISK : c'est l'onglet « SAMPLES SEQ-16 »
de l'application (cpc_dsk/seq16/smp_gui.py). Ce fichier l'ouvre seul,
dans sa propre fenêtre :

    python tools/smp_gui.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpcdisk  # noqa: E402

_module = cpcdisk.remplacer(__name__, "smp_gui")

if __name__ == "__main__":
    _module.run()
