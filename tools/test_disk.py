"""Tests du panneau DISQUE (lot 5 du plan) : catalogue par type, ENTER
charge dans le bon panneau, DEL efface (|ERA), COPY renomme (|REN).

On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py).
Lancement :  python -m unittest tools.test_disk   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402
from test_patterns import make_pattern  # noqa: E402
from test_banks import test_bank as ins_bank  # noqa: E402

cpcsim = test_player.cpcsim
wav2smp = test_player.wav2smp
KEY_DISK, KEY_SAVE = 12, 11
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 8
TAB, RETURN, DEL, COPY, KEY_N = 68, 18, 79, 9, 46
ESC = 0xFC
MSG = 25


def typed(text):
    return [ord(c) for c in text] + [13]


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class DiskPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cpc = cpcsim.CPC.from_build()
        cpc.boot()
        cls.base = cpc

    def setUp(self):
        self.cpc = test_player.PlayerTest._clone(self.base)

    make_disk = test_player.PlayerTest.make_disk

    def key(self, *keys):
        self.cpc.frames(1, keys=set(keys))
        self.cpc.frames(1)

    def var(self, name):
        return self.cpc.peek(self.cpc.addr(name))[0]

    def disk_with_files(self):
        song = bytes(self.cpc.saved.get("X", b"")) or None
        two = [wav2smp.Sample("ONE", b"\x11" * 50, 125)]
        self.make_disk({"GROOVE.PAT": make_pattern(seed=3, bpm=111),
                        "AUTRE.PAT": make_pattern(seed=4),
                        "SONS.INS": ins_bank(),
                        "KIT.SMP": wav2smp.build_bank(two)}, keep=("SEQ16.BIN", "DRUMS.SMP"))
        return song

    # --- affichage ---------------------------------------------------------------------
    def test_layout_and_types(self):
        cpc = self.cpc
        self.disk_with_files()
        self.key(KEY_DISK)
        self.assertTrue(cpc.row(2).startswith("DISQUE :"))
        self.assertIn("6 FICHIERS", cpc.row(2))               # SEQ16, DRUMS + 4
        self.assertIn("K LIBRES", cpc.row(2))
        self.assertEqual(cpc.attr[3][2], (0, 1))              # SNG choisi
        self.assertIn("AUCUN FICHIER", cpc.row(MSG))          # pas de .SNG
        self.key(TAB)                                         # .PAT
        self.assertEqual(cpc.attr[3][8], (0, 1))
        self.assertEqual(self.var("smp_nfiles"), 2)
        self.assertIn("GROOVE", cpc.row(6) + cpc.row(7))
        self.assertIn("ENTER : DANS 2MOTIF", cpc.row(19))
        self.key(TAB)
        self.assertIn("SONS", cpc.row(6))
        self.assertIn("3INST", cpc.row(19))
        self.key(TAB)
        self.assertIn("4SAMPLE", cpc.row(19))
        self.assertEqual(self.var("smp_nfiles"), 2)           # DRUMS, KIT
        self.key(TAB)                                         # retour à .SNG
        self.assertEqual(self.var("dk_type"), 0)

    def test_free_space(self):
        cpc = self.cpc
        self.make_disk({}, keep=("SEQ16.BIN",))
        self.key(KEY_DISK)
        blocks = (len(cpc.files["SEQ16.BIN"]) + 128 + 1023) // 1024   # avec l'en-tête
        self.assertIn("%dK LIBRES" % (178 - blocks), cpc.row(2))
        self.assertIn(" 1 FICHIERS", cpc.row(2).replace("01 F", " 1 F"))

    # --- ENTER : charger dans son panneau ---------------------------------------------
    def test_enter_loads_pattern_into_motif(self):
        cpc = self.cpc
        self.disk_with_files()
        self.key(KEY_DISK)
        self.key(TAB)                                         # .PAT
        names = [cpc.peek(test_player.SMP_FILES + 8 * i, 8) for i in range(2)]
        k = names.index(b"GROOVE  ")
        if k:
            self.key(DOWN)
        self.key(RETURN)
        self.assertEqual(self.var("screen"), 0)               # le panneau MOTIF
        self.assertIn("MOTIF CHARGE", cpc.row(MSG))
        self.assertIn("BPM:111", cpc.row(2))
        work = cpc.word(cpc.addr("seq_pattern"))
        self.assertEqual(cpc.peek(work, 260), make_pattern(seed=3, bpm=111))

    def test_enter_loads_ins_and_smp(self):
        cpc = self.cpc
        self.disk_with_files()
        self.key(KEY_DISK)
        self.key(TAB)
        self.key(TAB)                                         # .INS
        self.key(RETURN)
        self.assertEqual(self.var("screen"), 1)
        self.assertIn("INSTRUMENTS CHARGES", cpc.row(MSG))
        self.key(KEY_DISK)                                    # (le type reste .INS)
        self.key(TAB)                                         # .SMP
        self.assertEqual(self.var("dk_type"), 3)
        names = [cpc.peek(test_player.SMP_FILES + 8 * i, 8) for i in range(2)]
        if names.index(b"KIT     "):
            self.key(DOWN)
        self.key(RETURN)
        self.assertEqual(self.var("screen"), 3)
        self.assertEqual(cpc.peek(cpc.addr("smp_name"), 8), b"KIT     ")

    def test_enter_loads_song(self):
        cpc = self.cpc
        self.key(KEY_DISK)
        cpc.chars = typed("NUIT")
        self.key(KEY_SAVE)                                    # f8 : le morceau
        self.assertIn("MORCEAU SAUVE", cpc.row(MSG))
        data = cpc.saved["NUIT.SNG"]
        self.make_disk({"NUIT.SNG": data}, keep=("SEQ16.BIN",))
        cpc.poke(cpc.addr("fname"), b"AUTRE   ")
        self.key(62)                                          # C : relire la disquette
        self.assertIn("NUIT.SNG", cpc.row(19))
        self.key(RETURN)
        self.assertEqual(self.var("screen"), 4)               # le panneau SONG
        self.assertTrue(cpc.row(2).startswith("SONG:NUIT"))

    # --- DEL, COPY, N --------------------------------------------------------------------
    def test_delete_needs_two_presses(self):
        cpc = self.cpc
        self.disk_with_files()
        self.key(KEY_DISK)
        self.key(TAB)                                         # .PAT
        first = cpc.peek(test_player.SMP_FILES, 8).decode().strip()
        self.key(DEL)
        self.assertIn("DEL A NOUVEAU", cpc.row(MSG))
        self.assertIn(first + ".PAT", cpc.files)
        self.key(DEL)
        self.assertEqual(cpc.rsx_log[-1], ("ERA", first + ".PAT"))
        self.assertNotIn(first + ".PAT", cpc.files)
        self.assertIn("FICHIER EFFACE", cpc.row(MSG))
        self.assertEqual(self.var("smp_nfiles"), 1)           # liste relue

    def test_delete_disarmed_by_another_key(self):
        cpc = self.cpc
        self.disk_with_files()
        self.key(KEY_DISK)
        self.key(TAB)
        self.key(DEL)
        self.key(DOWN)
        self.key(DEL)                                         # une seule fois : rien
        self.assertEqual(cpc.rsx_log, [])

    def test_rename(self):
        cpc = self.cpc
        self.disk_with_files()
        self.key(KEY_DISK)
        self.key(TAB)
        self.key(TAB)                                         # .INS : SONS
        cpc.chars = typed("BASSES2")
        self.key(COPY)
        self.assertEqual(cpc.rsx_log[-1], ("REN", "BASSES2.INS", "SONS.INS"))
        self.assertIn("BASSES2.INS", cpc.files)
        self.assertNotIn("SONS.INS", cpc.files)
        self.assertIn("FICHIER RENOMME", cpc.row(MSG))
        self.assertIn("BASSES2", cpc.row(6))

    def test_rename_cancel(self):
        cpc = self.cpc
        self.disk_with_files()
        self.key(KEY_DISK)
        self.key(TAB)
        cpc.chars = [ord("Z"), ESC]
        self.key(COPY)
        self.assertEqual(cpc.rsx_log, [])

    def test_new_song_needs_two_presses(self):
        cpc = self.cpc
        self.key(KEY_DISK)
        cpc.poke(cpc.word(cpc.addr("seq_pattern")), make_pattern(seed=9))
        self.key(KEY_N)
        self.assertIn("N A NOUVEAU", cpc.row(MSG))
        self.key(KEY_N)
        self.assertIn("NOUVEAU MORCEAU", cpc.row(MSG))
        self.assertNotEqual(cpc.peek(cpc.word(cpc.addr("seq_pattern")), 260), make_pattern(seed=9))


if __name__ == "__main__":
    unittest.main()
