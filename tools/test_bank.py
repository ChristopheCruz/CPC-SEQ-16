"""Tests de la mémoire supplémentaire du 6128 (src/bank.asm, lot 1 du plan).

Les 32 motifs vivent dans le bloc 4 (montré en #4000-#7FFF) ; seul le motif
affiché est en mémoire principale (pat_work).  Un .SNG est l'image du bloc.
On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py).
Lancement :  python -m unittest tools.test_bank   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402
from test_patterns import make_pattern  # noqa: E402

cpcsim = test_player.cpcsim
KEY_MOTIF, KEY_DISK, KEY_S, KEY_L = 14, 12, 60, 36
KEY_CTRL, KEY_RIGHT, KEY_LEFT = 23, 1, 8
PAT_SIZE = 260
SONG_FIXED = 16 + 32 * 16 + 32 * 6 + 8 * 16
SONG_SIZE = SONG_FIXED + 32 * PAT_SIZE + 16 + 2 + 64 * 3 + 32 * 8   # version 3
BANK_PATS = 0x4000 + SONG_FIXED
EMPTY = bytes([0, 125, 0, 0] + [0xFF, 0, 0xFF, 0] * 64)
MSG_ROW = 25                              # ligne des messages


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class BankTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cpc = cpcsim.CPC.from_build()
        cpc.boot()
        cls.base = cpc

    def setUp(self):
        self.cpc = test_player.PlayerTest._clone(self.base)

    def key(self, *keys):
        self.cpc.frames(1, keys=set(keys))
        self.cpc.frames(1)

    def pat_work(self):
        return self.cpc.word(self.cpc.addr("seq_pattern"))

    def bank_pattern(self, n):
        return self.cpc.bank_peek(4, BANK_PATS + PAT_SIZE * n, PAT_SIZE)

    def cur_pat(self):
        return self.cpc.peek(self.cpc.addr("cur_pat"))[0]

    # --- carte de la mémoire ---------------------------------------------------
    def test_layout(self):
        cpc = self.cpc
        # tout ce qui tourne pendant qu'un bloc est montré est sous #4000
        for name in ("bank_copy", "bank_cas_in", "bank_cas_out", "bank_normal", "bank_check"):
            self.assertLess(cpc.addr(name), 0x4000, name)
        self.assertEqual(cpc.addr("start"), 0x3F00)           # adresse de chargement
        # le motif affiché et le tampon d'AMSDOS sont hors de la fenêtre
        self.assertGreaterEqual(self.pat_work(), 0x8000)
        self.assertLessEqual(self.pat_work() + PAT_SIZE, 0x9800)
        self.assertEqual(cpc.ram_block, 1)                       # mémoire normale

    # --- morceau d'usine ---------------------------------------------------------
    def test_factory_patterns_in_bank(self):
        """Le morceau d'usine (SYNTH, tools/gen_synth.py) : ses 32 motifs dans
        le bloc 4, le motif 1 dans pat_work."""
        import gen_synth
        cpc = self.cpc
        pats, _ = gen_synth.parts()
        self.assertEqual(self.cur_pat(), 0)
        self.assertEqual(cpc.peek(self.pat_work(), PAT_SIZE), pats[:PAT_SIZE])
        for n in range(32):
            self.assertEqual(self.bank_pattern(n), pats[n * PAT_SIZE:(n + 1) * PAT_SIZE], n)
        self.assertEqual(self.bank_pattern(31), EMPTY)

    # --- changer de motif ----------------------------------------------------------
    def test_switch_keeps_edits(self):
        cpc = self.cpc
        mine = make_pattern(mode=0, bpm=133, seed=7)
        cpc.poke(self.pat_work(), mine)                       # on « édite » le motif 1
        demo1 = self.bank_pattern(1)
        self.key(KEY_MOTIF)
        self.key(KEY_CTRL, KEY_RIGHT)                         # motif 2
        self.assertEqual(self.cur_pat(), 1)
        self.assertEqual(cpc.peek(self.pat_work(), PAT_SIZE), demo1)
        self.assertEqual(self.bank_pattern(0), mine)          # rangé dans le bloc
        self.key(KEY_CTRL, KEY_LEFT)                          # retour au motif 1
        self.assertEqual(cpc.peek(self.pat_work(), PAT_SIZE), mine)
        self.assertEqual(cpc.peek(cpc.addr("seq_bpm"))[0], 133)
        self.assertEqual(cpc.ram_block, 1)

    def test_switch_interrupts(self):
        """Les copies se font interruptions coupées, moins de 2 ms, et les
        interruptions sont rendues ensuite."""
        cpc = self.cpc
        self.key(KEY_MOTIF)
        n0 = len(cpc.di_spans)
        self.key(KEY_CTRL, KEY_RIGHT)
        spans = cpc.di_spans[n0:]
        self.assertGreaterEqual(len(spans), 2)                # rangement + chargement
        for start, end in spans:
            self.assertLess(end - start, 2000)                # NOP = µs
        self.assertEqual(cpc.m.iff1, 1)

    # --- .SNG : l'image du bloc 4 -------------------------------------------------
    def test_save_song_is_bank_image(self):
        cpc = self.cpc
        mine = make_pattern(mode=1, bpm=99, seed=3)
        cpc.poke(self.pat_work(), mine)                       # motif affiché modifié
        self.key(KEY_DISK)
        cpc.chars = [13]                                      # f8 : le nom proposé
        self.key(11)
        self.assertIn("MORCEAU SAUVE", cpc.row(MSG_ROW))
        data = cpc.saved["MORCEAU1.SNG"]
        n = cpc.word(cpc.addr("smp_bank_len")) if cpc.peek(cpc.addr("smp_count"))[0] else 0
        self.assertEqual(len(data), SONG_SIZE + 2 + n)        # version 4 : + la banque
        song = cpc.addr("smp_blk_src")                        # song_data
        self.assertEqual(data[:SONG_FIXED], cpc.peek(song, SONG_FIXED))
        self.assertEqual(data[SONG_FIXED:SONG_FIXED + PAT_SIZE], mine)
        self.assertEqual(data[:SONG_SIZE], cpc.bank_peek(4, 0x4000, SONG_SIZE))
        self.assertEqual(data[SONG_SIZE:SONG_SIZE + 2], n.to_bytes(2, "little"))
        self.assertEqual(cpc.ram_block, 1)

    def test_load_song_roundtrip(self):
        cpc = self.cpc
        self.key(KEY_DISK)
        cpc.chars = [13]                                      # f8 : le nom proposé
        self.key(11)
        song = bytearray(cpc.saved["MORCEAU1.SNG"])
        pats = [make_pattern(mode=n % 2, bpm=100 + n, seed=n) for n in range(32)]
        for n, p in enumerate(pats):
            o = SONG_FIXED + PAT_SIZE * n
            song[o:o + PAT_SIZE] = p
        names = 16 + 32 * 16                                  # noms des instruments
        song[names:names + 6] = b"TESTIN"                     # nom de l'instrument 1
        test_player.PlayerTest.make_disk(self, {"MORCEAU1.SNG": bytes(song)})
        cpc.poke(self.pat_work(), EMPTY)                      # à écraser
        self.key(13)                                          # f1 (SONG), puis f9
        cpc.chars = [13]
        self.key(3)
        self.assertIn("MORCEAU CHARGE", cpc.row(MSG_ROW))
        self.assertEqual(self.cur_pat(), 0)
        self.assertEqual(cpc.peek(self.pat_work(), PAT_SIZE), pats[0])
        for n in range(1, 32):
            self.assertEqual(self.bank_pattern(n), pats[n], n)
        names = cpc.addr("smp_blk_src") + 16 + 32 * 16
        self.assertEqual(cpc.peek(names, 6), b"TESTIN")       # copie de travail
        self.key(KEY_MOTIF)
        for _ in range(5):
            self.key(KEY_CTRL, KEY_RIGHT)
        self.assertEqual(cpc.peek(self.pat_work(), PAT_SIZE), pats[5])
        self.assertEqual(cpc.ram_block, 1)


if cpcsim is not None:
    class CPC464(cpcsim.CPC):
        """Un CPC sans mémoire supplémentaire : le port ne change rien."""
        def _ram_config(self, cfg):
            pass


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class No6128Test(unittest.TestCase):
    def test_needs_6128(self):
        cpc = CPC464.from_build()
        before = cpc.peek(0x4000, 16)
        seen = []
        cpc.chars = [lambda: seen.append(cpc.row(1)) or 32]   # l'écran à la frappe
        cpc.m.iff1 = cpc.m.iff2 = 1
        cpc.m.pc = cpc.addr("start")
        cpc.run_until("main_loop", limit=2_000_000)            # s'arrête sur RST 0
        self.assertTrue(cpc.stopped)
        self.assertIn("IL FAUT UN CPC 6128", seen[0])
        self.assertEqual(cpc.peek(0x4000, 16), before)         # programme réparé
        self.assertEqual(cpc.m.iff1, 1)


if __name__ == "__main__":
    unittest.main()
