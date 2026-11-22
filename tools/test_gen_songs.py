"""Tests des morceaux de test (tools/gen_songs.py).

- les morceaux passent les vérifications musicales et ont le bon format ;
- les fichiers de songs/ sont à jour ;
- dans le CPC simulé, chaque morceau se charge (panneau SONG, f9), ses
  motifs sont les bons, et il joue (ROBOT recharge sa banque DRUMS).

Lancement :  python -m unittest tools.test_gen_songs
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gen_songs as gs  # noqa: E402
import insbank  # noqa: E402
import test_player  # noqa: E402

cpcsim = test_player.cpcsim
KEY_MOTIF, KEY_SONG, KEY_LOAD, KEY_SPACE, KEY_CTRL, KEY_RIGHT = 13, 14, 3, 47, 23, 1
PAT = 260
FIXED = 16 + 32 * 16 + 32 * 6 + 8 * 16


class SongFilesTest(unittest.TestCase):
    def test_songs_are_valid(self):
        for s in gs.SONGS:
            self.assertEqual(gs.check_song(s), [], s["name"])

    def test_format(self):
        for s in gs.SONGS:
            data = gs.song_file(s)
            self.assertEqual(len(data), FIXED + 32 * PAT + 16, s["name"])
            self.assertEqual(data[:5], b"SQ16\x02")
            self.assertEqual(tuple(data[5:9]), s["volumes"])
            bank = data[FIXED + 32 * PAT + 1:][:8]
            self.assertEqual(bank, (s["bank"] or "").ljust(8).encode() if s["bank"] else bytes(8))
            pats = gs.encode_patterns(s)
            for i, (_, p) in enumerate(pats):
                self.assertEqual(data[FIXED + i * PAT:FIXED + (i + 1) * PAT], p)
            for i in range(len(pats), 32):
                self.assertEqual(data[FIXED + i * PAT:FIXED + (i + 1) * PAT], gs.EMPTY_PAT)

    def test_ins_banks(self):
        for s in gs.SONGS:
            sounds, _ = insbank.parse_ins_bank(gs.ins_bank(s))
            names = [n.strip() for n, _ in sounds[24:28]]
            self.assertEqual(names[:len(s["instruments"])],
                             [t[0] for t, _ in s["instruments"]], s["name"])
            self.assertEqual(gs.ins_bank(s)[16:], gs.song_file(s)[16:FIXED])

    def test_sixteenths(self):
        """De vraies doubles croches (sauf la nappe en son composé)."""
        for s in gs.SONGS:
            if s["name"] != "NAPPE":
                self.assertGreater(gs.odd_ratio(s), 0.2, s["name"])

    def test_files_up_to_date(self):
        for s in gs.SONGS:
            for name, data in ((s["name"] + ".SNG", gs.song_file(s)), (s["name"] + ".INS", gs.ins_bank(s))):
                with open(os.path.join(ROOT, "songs", name), "rb") as fh:
                    self.assertEqual(fh.read(), data, name + " : python tools/gen_songs.py")


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class SongsInSimulatorTest(unittest.TestCase):
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

    def test_load_and_play(self):
        for s in gs.SONGS:
            with self.subTest(song=s["name"]):
                self.cpc = test_player.PlayerTest._clone(self.base)
                cpc = self.cpc
                self.make_disk({s["name"] + ".SNG": gs.song_file(s)})
                self.key(KEY_SONG)
                cpc.chars = [13]                      # un seul .SNG
                self.key(KEY_LOAD)
                self.assertIn("MORCEAU", cpc.row(25))
                self.assertEqual(cpc.peek(cpc.addr("screen"))[0], 4)   # toujours SONG
                self.assertIn("MORCEAU : " + s["name"], cpc.row(4))
                self.assertEqual(cpc.peek(cpc.addr("fname"), 8), s["name"].ljust(8).encode())
                if s["bank"]:
                    self.assertEqual(cpc.peek(cpc.addr("smp_name"), 8), s["bank"].ljust(8).encode())
                self.key(KEY_MOTIF)
                pats = gs.encode_patterns(s)
                for i, (name, data) in enumerate(pats):
                    work = cpc.word(cpc.addr("seq_pattern"))
                    self.assertEqual(cpc.peek(work, PAT), data, name)
                    self.key(KEY_CTRL, KEY_RIGHT)
                self.key(KEY_CTRL, 8)                 # retour au dernier motif joué
                n0 = len(cpc.ay_writes)
                self.key(KEY_SPACE)
                cpc.frames(60)
                self.assertEqual(cpc.peek(cpc.addr("seq_playing"))[0], 1)
                self.assertGreater(len(cpc.ay_writes), n0 + 20)


if __name__ == "__main__":
    unittest.main()
