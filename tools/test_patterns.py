"""Tests des motifs sur disquette : f3 M (sauver le motif) et f3 P (charger).

On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py).
Lancement :  python -m unittest tools.test_patterns   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402

cpcsim = test_player.cpcsim
KEY_MOTIF, KEY_DISK = 13, 12
KEY_CTRL, KEY_RIGHT = 23, 1
KEY_P, KEY_M = 27, 38
DSK_ROW = 17                              # f3 : ligne des messages
SONG_FIXED = 16 + 32 * 16 + 32 * 6 + 8 * 16
PAT_SIZE = 260


def make_pattern(mode=0, bpm=140, seed=1):
    """Un motif reconnaissable : notes et instruments dépendent de seed."""
    data = bytearray([mode, bpm, 0, 0])
    for step in range(16):
        for lane in range(4):
            if (step + lane + seed) % 3 == 0:
                data += bytes([(24 + step + seed) % 96, (lane + seed) % 32, 0xFF, 0])
            else:
                data += bytes([0xFF, 0, 0xFF, 0])
    return bytes(data)


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class PatternsTest(unittest.TestCase):
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

    def pattern(self, n):
        """Le motif n : le motif affiché est dans pat_work (pointé par
        seq_pattern), les autres dans le bloc 4 de la mémoire supplémentaire."""
        cpc = self.cpc
        if cpc.peek(cpc.addr("cur_pat"))[0] == n:
            return cpc.peek(cpc.word(cpc.addr("seq_pattern")), PAT_SIZE)
        return cpc.bank_peek(4, 0x4000 + SONG_FIXED + PAT_SIZE * n, PAT_SIZE)

    def goto_pattern(self, n):
        self.key(KEY_MOTIF)
        for _ in range(n):
            self.key(KEY_CTRL, KEY_RIGHT)
        self.assertEqual(self.cpc.peek(self.cpc.addr("cur_pat"))[0], n)

    # --- aide de l'écran f3 ----------------------------------------------------
    def test_help_line(self):
        self.key(KEY_DISK)
        row = self.cpc.row(18)
        self.assertIn("M SAUVER MOTIF", row)
        self.assertIn("P CHARGER MOTIF (.PAT)", row)

    # --- M : sauver ------------------------------------------------------------
    def test_save_pattern(self):
        cpc = self.cpc
        self.goto_pattern(1)                      # le 2e motif de démonstration
        self.key(KEY_DISK)
        self.key(KEY_M)
        self.assertIn("MOTIF SAUVE (.PAT)", cpc.row(DSK_ROW))
        data = cpc.saved["MORCEAU1.PAT"]
        self.assertEqual(len(data), PAT_SIZE)
        self.assertEqual(data, self.pattern(1))

    # --- P : charger -----------------------------------------------------------
    def test_load_pattern_into_current_slot(self):
        cpc = self.cpc
        pat = make_pattern(mode=1, bpm=150, seed=5)
        self.make_disk({"GROOVE.PAT": pat})
        self.goto_pattern(3)
        others = [self.pattern(i) for i in range(32) if i != 3]
        self.key(KEY_DISK)
        cpc.chars = [13]                          # un seul .PAT : RETURN
        self.key(KEY_P)
        self.assertIn("MOTIF CHARGE", cpc.row(DSK_ROW))
        self.assertEqual(self.pattern(3), pat)
        self.assertEqual([self.pattern(i) for i in range(32) if i != 3], others)
        self.assertEqual(cpc.peek(cpc.addr("seq_bpm"))[0], 150)   # son tempo
        self.key(KEY_MOTIF)                          # l'écran f1 montre le motif chargé
        self.assertIn("SON COMPOSE", cpc.row(2))
        self.assertIn("BPM:150", cpc.row(2))

    def test_save_then_load_roundtrip(self):
        cpc = self.cpc
        self.key(KEY_DISK)
        self.key(KEY_M)                           # motif 1 -> MORCEAU1.PAT
        saved = cpc.saved["MORCEAU1.PAT"]
        self.make_disk({"MORCEAU1.PAT": saved})
        self.goto_pattern(7)                      # un motif vide
        self.assertNotEqual(self.pattern(7), saved)
        self.key(KEY_DISK)
        cpc.chars = [13]
        self.key(KEY_P)
        self.assertEqual(self.pattern(7), saved)

    def test_load_wrong_size_refused(self):
        cpc = self.cpc
        self.make_disk({"FAUX.PAT": bytes(100)})
        self.goto_pattern(2)
        before = self.pattern(2)
        self.key(KEY_DISK)
        cpc.chars = [13]
        self.key(KEY_P)
        self.assertIn("PAS UN MOTIF .PAT", cpc.row(DSK_ROW))
        self.assertEqual(self.pattern(2), before)

    def test_unknown_mode_becomes_split_voices(self):
        cpc = self.cpc
        self.make_disk({"ODD.PAT": make_pattern(mode=7)})
        self.key(KEY_DISK)
        cpc.chars = [13]
        self.key(KEY_P)
        self.assertEqual(self.pattern(0)[0], 0)

    def test_choose_among_several(self):
        cpc = self.cpc
        a, b = make_pattern(seed=1), make_pattern(seed=2, bpm=99)
        self.make_disk({"AAA.PAT": a, "BBB.PAT": b})
        self.key(KEY_DISK)
        cpc.chars = [0xF1, 13]                    # le 2e de la liste
        self.key(KEY_P)
        self.assertEqual(cpc.peek(cpc.addr("smp_nfiles"))[0], 2)
        self.assertEqual(self.pattern(0), b)

    # --- liste en pages de 24 : tout le catalogue (64 entrées) --------------
    def mono_disk(self):
        """La disquette des motifs mono (62 .PAT), à côté du programme."""
        folder = os.path.join(test_player.ROOT, "patterns", "mono")
        files = {}
        for name in sorted(os.listdir(folder)):
            with open(os.path.join(folder, name), "rb") as fh:
                files[name] = fh.read()
        self.make_disk(files, keep=("SEQ16.BIN",))
        return files

    def test_pick_beyond_first_page(self):
        cpc = self.cpc
        files = self.mono_disk()
        self.key(KEY_DISK)
        seen = {}

        def spy():                                # la page affichée pendant le choix
            seen["row19"] = cpc.row(19)
            return 13
        cpc.chars = [0xF1] * 40 + [spy]           # 40 fois bas : le 41e nom
        self.key(KEY_P)
        n = cpc.peek(cpc.addr("smp_nfiles"))[0]
        self.assertEqual(n, len(files))
        self.assertGreater(n, 24)
        name = cpc.peek(test_player.SMP_FILES + 8 * 40, 8).decode().strip()
        self.assertEqual(self.pattern(0), files[name + ".PAT"])
        first_of_page2 = cpc.peek(test_player.SMP_FILES + 8 * 24, 8).decode().strip()
        self.assertTrue(seen["row19"].lstrip().startswith(first_of_page2))
        self.assertIn("MOTIF CHARGE", cpc.row(DSK_ROW))

    def test_right_arrow_turns_the_page(self):
        cpc = self.cpc
        files = self.mono_disk()
        self.key(KEY_DISK)
        # 4 colonnes de 6 : 4 fois droite = 24 noms plus loin (page 2), puis
        # 4 fois encore = 48 (page 3)
        cpc.chars = [0xF3] * 8 + [13]
        self.key(KEY_P)
        name = cpc.peek(test_player.SMP_FILES + 8 * 48, 8).decode().strip()
        self.assertEqual(self.pattern(0), files[name + ".PAT"])

    def test_no_pattern_on_disk(self):
        self.make_disk({})
        self.key(KEY_DISK)
        self.key(KEY_P)
        self.assertIn("AUCUN FICHIER DE CE TYPE", self.cpc.row(DSK_ROW))


if __name__ == "__main__":
    unittest.main()
