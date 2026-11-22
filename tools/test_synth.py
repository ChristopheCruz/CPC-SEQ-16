"""Tests de SYNTH, la song synthwave d'usine (tools/gen_synth.py).

C'est le morceau du démarrage (src/boot.asm, src/factory_song.asm) et un
fichier livré sur les disquettes du programme (SYNTH.SNG).
Lancement :  python -m unittest tools.test_synth
"""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import amsdsk  # noqa: E402
import gen_patterns as gp  # noqa: E402
import gen_songs as gs  # noqa: E402
import gen_synth  # noqa: E402
import test_player  # noqa: E402

cpcsim = test_player.cpcsim
FIXED = 16 + 32 * 16 + 32 * 6 + 8 * 16
V3 = FIXED + 16                               # song_v3, après le bloc v2


def read(*parts):
    with open(os.path.join(ROOT, *parts), "rb") as fh:
        return fh.read()


class SynthFilesTest(unittest.TestCase):
    def test_song_is_valid(self):
        gen_synth.check()
        s = gen_synth.SYNTH
        self.assertEqual(s["name"], "SYNTH")
        self.assertEqual(s["instruments"], [])              # instruments d'usine
        self.assertIsNone(s["bank"])                         # pas de sample
        self.assertEqual({p["mode"] for p in s["patterns"]}, {gp.MONO, gp.POLY})
        self.assertEqual(s["patterns"][0]["mode"], gp.POLY)  # motif 1 : voix séparées
        self.assertEqual(len(gs.SONGS), 5)                   # les morceaux de test à part

    def test_files_up_to_date(self):
        self.assertEqual(read("src", "factory_song.asm").decode("utf-8"), gen_synth.song_asm())
        self.assertEqual(read("usine", "SYNTH.SNG"), gs.song_file(gen_synth.SYNTH))

    def test_on_program_disks(self):
        for lang in ("fr", "en", "es"):
            dsk = os.path.join(ROOT, "build", "seq16-%s.dsk" % lang)
            self.assertEqual(amsdsk.read_file(dsk, "SYNTH.SNG"), read("usine", "SYNTH.SNG"), lang)


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class SynthBootTest(unittest.TestCase):
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

    def test_boot_song_is_synth(self):
        cpc = self.cpc
        _, v3 = gen_synth.parts()
        self.assertEqual(cpc.peek(cpc.addr("smp_blk_src") + V3, len(v3)), v3)
        self.assertIn("MOTIF:01 SYDRIVE", cpc.row(2))
        self.assertEqual(cpc.peek(cpc.addr("seq_bpm"))[0], 108)
        self.key(cpcsim.KEY_SONG)
        self.assertIn("SYINTRO", cpc.row(5))                 # position 00
        self.assertIn("SYDRIVE", cpc.row(6))

    def test_song_plays_through_positions(self):
        cpc = self.cpc
        self.key(cpcsim.KEY_SONG)
        self.key(cpcsim.KEY_SPACE)
        seen = set()
        for _ in range(700):                                 # environ 2 mesures et demie
            cpc.frames(1)
            seen.add(cpc.peek(cpc.addr("song_pos"))[0])
        self.assertTrue({0, 1, 2}.issubset(seen), seen)
        self.assertEqual(cpc.peek(cpc.addr("seq_playing"))[0], 1)

    def test_shipped_file_loads_same_song(self):
        """SYNTH.SNG, chargé par f9, redonne le morceau du démarrage."""
        cpc = self.cpc
        start = cpc.peek(cpc.addr("smp_blk_src") + V3, 450)
        cpc.poke(cpc.addr("smp_blk_src") + V3, bytes(450))   # on l'efface
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        dsk = os.path.join(d, "t.dsk")
        shutil.copy(os.path.join(ROOT, "build", "seq16-fr.dsk"), dsk)
        cpc.use_disk(dsk)
        self.key(cpcsim.KEY_SONG)
        names = [n for n in cpc.files if n.endswith(".SNG")]
        self.assertEqual(names, ["SYNTH.SNG"])
        cpc.chars = [13]
        self.key(3)                                          # f9
        self.assertIn("CHARGE", cpc.row(25))
        self.assertEqual(cpc.peek(cpc.addr("smp_blk_src") + V3, 450), start)


if __name__ == "__main__":
    unittest.main()
