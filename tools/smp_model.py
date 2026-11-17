"""smp_model.py : le modèle d'une banque .SMP (éditeur de banques).

Il fait maintenant partie de CPC DISK (cpc_dsk/seq16/smp_model.py) ; ce
fichier n'est qu'un renvoi.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpcdisk  # noqa: E402

cpcdisk.remplacer(__name__, "smp_model")
