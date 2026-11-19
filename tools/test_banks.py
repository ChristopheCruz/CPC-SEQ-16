"""Tests des instruments : copier / coller (f2), banques .INS (f2 et f3).

On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py).
Lancement :  python -m unittest tools.test_banks   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import insbank  # noqa: E402
import test_player  # noqa: E402

cpcsim = test_player.cpcsim
ROOT = test_player.ROOT
KEY_F2, KEY_F3 = 14, 5
KEY_CTRL, KEY_RIGHT, KEY_LEFT = 23, 1, 8
KEY_COPY, KEY_P, KEY_O, KEY_I = 9, 27, 34, 35
INS_ROW = 25                              # f2 : ligne des messages
DSK_ROW = 17                              # f3 : ligne des messages


def test_bank():
    """Une banque où chaque son est reconnaissable : son octet 1 vaut 100+i."""
    sounds = []
    for i in range(32):
        ins = bytes([255, 100 + i, 7, 9, 15, 1, i % 32, 8, 4, 0, 0, 1, 0, 0, 0, 0])
        sounds.append((f"SND{i + 1:02d}", ins))
    return insbank.build_ins_bank(sounds)


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class BanksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cpc = cpcsim.CPC.from_build()
        cpc.boot()
        cls.base = cpc

    def setUp(self):
        self.cpc = test_player.PlayerTest._clone(self.base)

    make_disk = test_player.PlayerTest.make_disk

    # --- aides ---------------------------------------------------------------
    def key(self, *keys):
        """Un appui (une image avec ces touches, puis une image sans)."""
        self.cpc.frames(1, keys=set(keys))
        self.cpc.frames(1)

    def inst(self, i):
        return self.cpc.peek(self.song() + 16 + 16 * i, 16)

    def name(self, i):
        return self.cpc.peek(self.song() + 16 + 32 * 16 + 6 * i, 6)

    def song(self):
        return self.cpc.addr("smp_blk_src")      # le morceau commence là

    def goto_inst(self, n):
        """Ecran f2, instrument numéro n (0 à 31)."""
        self.key(KEY_F2)
        for _ in range(32):                      # on revient au premier (au
            self.key(KEY_CTRL, KEY_LEFT)         # démarrage, l'instrument est
        for _ in range(n):                       # celui de la case du curseur)
            self.key(KEY_CTRL, KEY_RIGHT)
        self.assertEqual(self.cpc.peek(self.cpc.addr("cur_inst"))[0], n)

    # --- copier / coller -----------------------------------------------------
    def test_copy_paste(self):
        cpc = self.cpc
        self.goto_inst(0)
        lead = self.inst(0)
        self.key(KEY_COPY)
        self.assertIn("INSTRUMENT COPIE", cpc.row(INS_ROW))
        self.key(KEY_CTRL, KEY_RIGHT)
        self.key(KEY_CTRL, KEY_RIGHT)            # instrument 3 (PAD)
        self.assertEqual(self.name(2), b"PAD   ")
        self.key(KEY_P)
        self.assertEqual(self.inst(2), lead)
        self.assertEqual(self.name(2), b"LEAD  ")
        self.assertIn("INSTRUMENT COLLE", cpc.row(INS_ROW))
        self.assertIn("03 LEAD", cpc.row(2))     # l'écran montre le collage
        self.assertEqual(self.name(1), b"BASS  ")   # les autres ne bougent pas

    def test_paste_without_copy(self):
        self.goto_inst(4)
        before = self.inst(4)
        self.key(KEY_P)
        self.assertIn("RIEN A COLLER", self.cpc.row(INS_ROW))
        self.assertEqual(self.inst(4), before)

    # --- f3 : sauver / charger une banque entière ----------------------------
    def test_save_ins(self):
        cpc = self.cpc
        self.key(KEY_F3)
        self.key(KEY_I)
        self.assertIn("INSTRUMENTS SAUVES", cpc.row(DSK_ROW))
        data = cpc.saved["MORCEAU1.INS"]
        self.assertEqual(len(data), insbank.INS_FILE_LEN)
        sounds, sons = insbank.parse_ins_bank(data)
        self.assertEqual(sounds[0][0], "LEAD  ")
        self.assertEqual(sounds[27][0], "USER4 ")
        self.assertEqual(sounds[31][0], "DGCLAP")
        self.assertEqual(sons, insbank.SONS_USINE)

    def test_load_ins_bank(self):
        cpc = self.cpc
        bank = test_bank()
        self.make_disk({"TESTS.INS": bank})
        self.key(KEY_F3)
        head = cpc.peek(self.song(), 16)
        cpc.chars = [13]                         # un seul .INS : RETURN
        self.key(KEY_O)
        self.assertEqual(cpc.peek(cpc.addr("smp_nfiles"))[0], 1)
        self.assertIn("INSTRUMENTS CHARGES", cpc.row(DSK_ROW))
        self.assertEqual(cpc.peek(self.song() + 16, 832), bank[16:])
        self.assertEqual(cpc.peek(self.song(), 16), head)   # mixage intact

    def test_real_disk_banks(self):
        """La disquette du build : 13 banques .INS, 9 banques .SMP."""
        cpc = self.cpc
        self.make_disk({}, keep=None)            # la disquette entière
        self.key(KEY_F3)
        cpc.chars = [0xF1, 13]                   # la 2e banque : BATTERIE
        self.key(KEY_O)
        self.assertEqual(cpc.peek(cpc.addr("smp_nfiles"))[0], 13)
        self.assertEqual(cpc.peek(test_player.SMP_FILES, 16), b"USINE   BATTERIE")
        self.assertIn("INSTRUMENTS CHARGES", cpc.row(DSK_ROW))
        bank = open(os.path.join(ROOT, "instruments", "BATTERIE.INS"), "rb").read()
        self.assertEqual(cpc.peek(self.song() + 16, 832), bank[16:])
        self.assertEqual(self.name(0), b"KICK1 ")
        cpc.chars = [0xFC]                       # f3 + D : 9 banques .SMP
        self.key(test_player.KEY_D)
        self.assertEqual(cpc.peek(cpc.addr("smp_nfiles"))[0], 9)

    def test_load_not_a_bank(self):
        cpc = self.cpc
        self.make_disk({"FAUX.INS": bytes(500)})
        self.key(KEY_F3)
        before = cpc.peek(self.song(), 848)
        cpc.chars = [13]
        self.key(KEY_O)
        self.assertIn("PAS UNE BANQUE .INS", cpc.row(DSK_ROW))
        self.assertEqual(cpc.peek(self.song(), 848), before)

    def test_no_ins_on_disk(self):
        self.make_disk({})                       # la disquette du build seule
        self.key(KEY_F3)
        self.key(KEY_O)
        self.assertIn("AUCUN FICHIER DE CE TYPE", self.cpc.row(DSK_ROW))

    # --- f2 : prendre un seul son --------------------------------------------
    def test_take_one_sound(self):
        cpc = self.cpc
        bank = test_bank()
        self.make_disk({"TESTS.INS": bank})
        self.goto_inst(3)
        others = [self.inst(i) for i in range(32) if i != 3]
        # RETURN sur la banque, puis 5 fois bas et droite (colonne suivante,
        # +16) : son numéro 21, puis RETURN
        cpc.chars = [13, 0xF1, 0xF1, 0xF1, 0xF1, 0xF1, 0xF3, 13]
        self.key(KEY_O)
        sounds, _ = insbank.parse_ins_bank(bank)
        self.assertEqual(self.inst(3), sounds[21][1])
        self.assertEqual(self.name(3), b"SND22 ")
        self.assertEqual([self.inst(i) for i in range(32) if i != 3], others)
        self.assertIn("SON PRIS DANS LA BANQUE", cpc.row(INS_ROW))
        self.assertIn("04 SND22", cpc.row(2))    # écran redessiné
        self.assertIn("ATTAQUE", cpc.row(4))

    def test_take_cancel(self):
        cpc = self.cpc
        self.make_disk({"TESTS.INS": test_bank()})
        self.goto_inst(5)
        before = self.inst(5)
        cpc.chars = [13, 0xF1, 0xFC]             # banque, puis ESC
        self.key(KEY_O)
        self.assertEqual(self.inst(5), before)
        self.assertIn("ATTAQUE", cpc.row(4))     # écran redessiné

    def test_names_listed(self):
        """La liste des 32 sons s'affiche à droite, en 2 colonnes de 16."""
        cpc = self.cpc
        self.make_disk({"TESTS.INS": test_bank()})
        self.goto_inst(0)
        seen = {}

        def spy():                               # on regarde l'écran au moment
            seen["r5"] = cpc.row(5)              # où l'on attend la 2e touche
            seen["r20"] = cpc.row(20)
            return 0xFC
        cpc.chars = [13, spy]
        self.key(KEY_O)
        self.assertIn("SND01", seen["r5"][22:])
        self.assertIn("SND17", seen["r5"][22:])
        self.assertIn("SND16", seen["r20"][22:])
        self.assertIn("SND32", seen["r20"][22:])


if __name__ == "__main__":
    unittest.main()
