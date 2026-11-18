"""wav2smp.py : convertit des WAV en banque de samples .SMP pour SEQ-16.

Le convertisseur fait maintenant partie de CPC DISK
(cpc_dsk/seq16/wav2smp.py). Ce fichier n'est qu'un renvoi, pour que les
scripts et les tests de SEQ-16 gardent `import wav2smp` et la commande :

    python tools/wav2smp.py sons/*.wav -o samples/MABANQ.SMP
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpcdisk  # noqa: E402

_module = cpcdisk.remplacer(__name__, "wav2smp")

if __name__ == "__main__":
    sys.exit(_module.main())
