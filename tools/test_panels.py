"""Tests des cinq panneaux (lot 2 du plan) : onglets f1 à f5, f6 mode,
f8 sauver et f9 charger dans chaque panneau, panneau SONG provisoire.

On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py).
Lancement :  python -m unittest tools.test_panels   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402
from test_banks import test_bank as ins_bank  # noqa: E402
from test_patterns import make_pattern  # noqa: E402

cpcsim = test_player.cpcsim
wav2smp = test_player.wav2smp
KEY_MOTIF, KEY_SONG, KEY_INST, KEY_SAMPLE, KEY_DISK = 13, 14, 5, 20, 12
KEY_MODE, KEY_SAVE, KEY_LOAD, KEY_F7 = 4, 11, 3, 10
ESC = 0xFC                                # code de ESC rendu par KM_WAIT_CHAR
PAT_SIZE = 260
SONG_FIXED = 16 + 32 * 16 + 32 * 6 + 8 * 16
SONG_SIZE = SONG_FIXED + 32 * PAT_SIZE + 16 + 2 + 64 * 3 + 32 * 8   # version 3
MSG = 25                                  # ligne des messages (hors DISQUE)


def typed(text):
    return [ord(c) for c in text] + [13]


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class PanelsTest(unittest.TestCase):
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

    def screen(self):
        return self.cpc.peek(self.cpc.addr("screen"))[0]

    def pat_work(self):
        return self.cpc.peek(self.cpc.word(self.cpc.addr("seq_pattern")), PAT_SIZE)

    # --- onglets ---------------------------------------------------------------
    def test_tabs(self):
        """f1 à f5 : le bon panneau, et son onglet en bleu sur orange."""
        cpc = self.cpc
        tabs = {KEY_MOTIF: (0, "1MOTIF"), KEY_SONG: (4, "2SONG"), KEY_INST: (1, "3INST"),
                KEY_SAMPLE: (3, "4SAMPLE"), KEY_DISK: (2, "5DISQUE")}
        for k, (scr, label) in tabs.items():
            self.key(k)
            self.assertEqual(self.screen(), scr, label)
            row = cpc.row(1)
            self.assertEqual(row, "SEQ16 1MOTIF 2SONG 3INST 4SAMPLE 5DISQUE")
            col = row.index(label)
            self.assertEqual(cpc.attr[0][col], (0, 3), label)          # chiffre : bleu/orange
            self.assertEqual(cpc.attr[0][col + 1], (0, 3), label)      # nom aussi
            others = [c for c in range(6, 40) if not col - 1 <= c < col + len(label)]
            self.assertTrue(all(cpc.attr[0][c][1] == 0 for c in others), label)
        self.key(KEY_SONG)
        self.assertEqual(cpc.attr[0][row.index("1MOTIF")], (3, 0))    # chiffre orange
        self.assertEqual(cpc.attr[0][row.index("1MOTIF") + 1], (2, 0))  # nom cyan

    def test_f6_mode_and_f5_disk(self):
        cpc = self.cpc
        mode = cpc.peek(cpc.word(cpc.addr("seq_pattern")))[0]
        self.key(KEY_MODE)                                  # f6 : mode
        self.assertNotEqual(cpc.peek(cpc.word(cpc.addr("seq_pattern")))[0], mode)
        self.assertIn("SON COMPOSE", cpc.row(2))
        self.key(KEY_DISK)                                  # f5 : panneau DISQUE
        self.assertEqual(self.screen(), 2)

    def test_song_panel(self):
        cpc = self.cpc
        self.key(KEY_SONG)
        self.assertTrue(cpc.row(2).startswith("SONG:MORCEAU1"))
        self.assertTrue(cpc.row(4).startswith("POS MOTIF"))
        self.key(47)                                        # ESPACE : lecture du morceau
        self.assertEqual(cpc.peek(cpc.addr("seq_playing"))[0], 1)
        self.assertEqual(cpc.peek(cpc.addr("song_live"))[0], 1)

    # --- f8 ------------------------------------------------------------------
    def test_f8_motif(self):
        cpc = self.cpc
        mine = make_pattern(seed=4)
        cpc.poke(cpc.word(cpc.addr("seq_pattern")), mine)
        seen = []
        cpc.chars = [lambda: seen.append(cpc.row(MSG)) or ord("G")] + typed("RV")
        self.key(KEY_SAVE)
        self.assertIn("FICHIER : MOTIF-01.PAT", seen[0])   # le nom proposé : celui du motif
        self.assertEqual(cpc.saved["GRV.PAT"], mine)
        self.assertIn("MOTIF SAUVE (.PAT)", cpc.row(MSG))
        self.assertIn("PAS  0 1 2 3", cpc.row(10))          # écran redessiné

    def test_f8_escape_cancels(self):
        cpc = self.cpc
        cpc.chars = [ord("Z"), ESC]
        self.key(KEY_SAVE)
        self.assertEqual(cpc.saved, {})
        self.assertEqual(cpc.row(MSG).strip(), "")            # rien à dire
        self.assertTrue(cpc.row(24).startswith("SHIFT"))      # l'aide est intacte

    def test_f8_existing_file(self):
        cpc = self.cpc
        self.make_disk({"OLD.PAT": make_pattern(seed=1)})
        cpc.chars = typed("OLD") + [ord("N")]                # pas RETURN : annulé
        self.key(KEY_SAVE)
        self.assertNotIn("OLD.PAT", cpc.saved)
        seen = []
        cpc.chars = typed("OLD") + [lambda: seen.append(cpc.row(MSG)) or 13]
        self.key(KEY_SAVE)
        self.assertIn("DEJA SUR LA DISQUETTE", seen[0])
        self.assertEqual(cpc.saved["OLD.PAT"], self.pat_work())

    def test_f8_song(self):
        cpc = self.cpc
        self.key(KEY_SONG)
        cpc.chars = typed("NUIT")
        self.key(KEY_SAVE)
        data = cpc.saved["NUIT.SNG"]
        self.assertEqual(len(data), SONG_SIZE)
        self.assertEqual(data[:4], b"SQ16")
        self.assertTrue(cpc.row(2).startswith("SONG:NUIT"))  # le morceau a ce nom
        self.assertIn("MORCEAU SAUVE", cpc.row(MSG))

    def test_f8_inst(self):
        cpc = self.cpc
        self.key(KEY_INST)
        cpc.chars = typed("SONS")
        self.key(KEY_SAVE)
        data = cpc.saved["SONS.INS"]
        self.assertEqual(data, cpc.peek(cpc.addr("smp_blk_src"), 848))

    def test_f8_sample(self):
        cpc = self.cpc
        self.key(KEY_SAMPLE)
        self.assertEqual(cpc.peek(cpc.addr("smp_count"))[0], 4)   # DRUMS chargée
        cpc.chars = typed("KIT")
        self.key(KEY_SAVE)
        n = cpc.word(cpc.addr("smp_bank_len"))
        self.assertEqual(cpc.saved["KIT.SMP"], cpc.peek(test_player.BANK, n))
        self.assertEqual(cpc.peek(cpc.addr("smp_name"), 8), b"KIT     ")
        self.assertIn("MORCEAU1", cpc.peek(cpc.addr("fname"), 8).decode())  # fname intact

    # --- f9 ------------------------------------------------------------------
    def test_f9_motif(self):
        cpc = self.cpc
        pat = make_pattern(mode=0, bpm=111, seed=6)
        self.make_disk({"GROOVE.PAT": pat})
        cpc.chars = [13]                                    # un seul .PAT
        self.key(KEY_LOAD)
        self.assertEqual(self.pat_work(), pat)
        self.assertIn("MOTIF CHARGE", cpc.row(MSG))
        self.assertIn("BPM:111", cpc.row(2))                # écran redessiné

    def test_f9_song(self):
        cpc = self.cpc
        self.key(KEY_SONG)
        cpc.chars = typed("NUIT")
        self.key(KEY_SAVE)
        song = bytearray(cpc.saved["NUIT.SNG"])
        song[SONG_FIXED:SONG_FIXED + PAT_SIZE] = make_pattern(seed=9)
        self.make_disk({"NUIT.SNG": bytes(song)}, keep=("SEQ16.BIN",))
        cpc.poke(cpc.addr("fname"), b"AUTRE   ")
        cpc.chars = [13]                                    # un seul .SNG
        self.key(KEY_LOAD)
        self.assertIn("MORCEAU CHARGE", cpc.row(MSG))
        self.assertEqual(cpc.peek(cpc.addr("fname"), 8), b"NUIT    ")
        self.assertEqual(self.pat_work(), make_pattern(seed=9))

    def test_f9_inst(self):
        cpc = self.cpc
        bank = ins_bank()
        self.make_disk({"TESTS.INS": bank})
        self.key(KEY_INST)
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertIn("INSTRUMENTS CHARGES", cpc.row(MSG))
        self.assertEqual(cpc.peek(cpc.addr("smp_blk_src") + 16, 832), bank[16:])

    def test_f9_sample(self):
        cpc = self.cpc
        two = [wav2smp.Sample("ONE", b"\x11" * 50, 125), wav2smp.Sample("TWO", b"\x22" * 60, 100)]
        self.make_disk({"TEST.SMP": wav2smp.build_bank(two)}, keep=("SEQ16.BIN",))
        self.key(KEY_SAMPLE)
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertEqual(cpc.peek(cpc.addr("smp_count"))[0], 2)
        self.assertEqual(cpc.peek(cpc.addr("smp_name"), 8), b"TEST    ")


if __name__ == "__main__":
    unittest.main()
