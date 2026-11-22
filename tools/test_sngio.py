"""Tests du .SNG version 4 (src/sngio.asm, lot 5 du plan) : un seul fichier
qui garde le morceau ET sa banque de samples, écrit et relu octet par
octet avec un en-tête AMSDOS écrit par le programme.

On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py).
Lancement :  python -m unittest tools.test_sngio   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402

cpcsim = test_player.cpcsim
KEY_SONG, KEY_SAMPLE, KEY_SAVE, KEY_LOAD = 14, 20, 11, 3
PAT = 260
FIXED = 16 + 32 * 16 + 32 * 6 + 8 * 16
SONG_SIZE3 = FIXED + 32 * PAT + 16 + 2 + 64 * 3 + 32 * 8
BANK = test_player.BANK
MSG = 25


def typed(text):
    return [ord(c) for c in text] + [13]


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class SngV4Test(unittest.TestCase):
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

    def save(self, name):
        self.key(KEY_SONG)
        self.cpc.chars = typed(name)
        self.key(KEY_SAVE)
        return self.cpc.saved[name + ".SNG"]

    def with_drums(self):
        self.key(KEY_SAMPLE)                      # f4 charge DRUMS.SMP
        self.assertEqual(self.var("smp_count"), 4)
        return self.cpc.word(self.cpc.addr("smp_bank_len"))

    def test_header(self):
        """L'en-tête AMSDOS écrit par le programme : nom, type binaire,
        longueurs, somme de contrôle des octets 0 à 66."""
        n = self.with_drums()
        data = self.save("AVEC")
        head = self.cpc.saved_headers["AVEC.SNG"]
        self.assertEqual(head[0], 0)                          # utilisateur 0
        self.assertEqual(head[1:12], b"AVEC    SNG")
        self.assertEqual(head[0x12], 2)                       # binaire
        self.assertEqual(head[0x17], 0xFF)
        total = SONG_SIZE3 + 2 + n
        self.assertEqual(len(data), total)
        for off in (0x13, 0x18, 0x40):
            self.assertEqual(head[off] | head[off + 1] << 8, total, hex(off))
        self.assertEqual(head[0x42], 0)
        self.assertEqual(head[0x43] | head[0x44] << 8, sum(head[:67]))

    def test_samples_travel_with_the_song(self):
        """La disquette n'a pas DRUMS.SMP : la banque revient du .SNG."""
        cpc = self.cpc
        n = self.with_drums()
        drums = cpc.peek(BANK, n)
        data = self.save("AVEC")
        self.assertEqual(data[4], 4)                          # version 4
        self.assertEqual(data[SONG_SIZE3:SONG_SIZE3 + 2], n.to_bytes(2, "little"))
        self.assertEqual(data[SONG_SIZE3 + 2:], drums)
        cpc.poke(BANK, bytes(n))                              # banque effacée
        cpc.poke(cpc.addr("smp_count"), [0])
        cpc.poke(cpc.addr("smp_name"), b"AUTRE   ")
        self.make_disk({"AVEC.SNG": data}, keep=("SEQ16.BIN",))
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertIn("MORCEAU ET BANQUE DE SAMPLES CHARGES", cpc.row(MSG))
        self.assertEqual(self.var("smp_count"), 4)
        self.assertEqual(cpc.peek(BANK, n), drums)
        self.assertEqual(cpc.word(cpc.addr("smp_bank_len")), n)
        self.assertEqual(cpc.peek(cpc.addr("smp_name"), 8), b"DRUMS   ")

    def test_song_without_bank(self):
        cpc = self.cpc
        cpc.poke(cpc.addr("smp_count"), [0])
        data = self.save("SANS")
        self.assertEqual(len(data), SONG_SIZE3 + 2)
        self.assertEqual(data[-2:], b"\x00\x00")
        self.make_disk({"SANS.SNG": data}, keep=("SEQ16.BIN",))
        before = cpc.peek(BANK, 64)
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertIn("MORCEAU CHARGE", cpc.row(MSG))
        self.assertEqual(cpc.peek(BANK, 64), before)          # rien d'écrasé

    def test_truncated_file_refused(self):
        cpc = self.cpc
        self.with_drums()
        data = self.save("COURT")
        self.make_disk({"COURT.SNG": data[:-100]}, keep=("SEQ16.BIN",))
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertNotIn("CHARGE", cpc.row(MSG))
        self.assertEqual(cpc.ram_block, 1)

    def test_old_v3_file_still_loads(self):
        cpc = self.cpc
        self.with_drums()
        data = bytearray(self.save("ANCIEN")[:SONG_SIZE3])
        data[4] = 3
        self.make_disk({"ANCIEN.SNG": bytes(data)}, keep=("SEQ16.BIN", "DRUMS.SMP"))
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertIn("MORCEAU", cpc.row(MSG))
        self.assertEqual(self.var("smp_count"), 4)             # par son nom (DRUMS.SMP)


if __name__ == "__main__":
    unittest.main()
