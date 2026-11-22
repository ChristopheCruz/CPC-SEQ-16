"""Tests de la disquette de démonstration (tools/gen_demo.py).

Lancement :  python -m unittest tools.test_demo
"""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gen_demo  # noqa: E402
import gen_patterns as gp  # noqa: E402
import gen_songs as gs  # noqa: E402
import wav2smp  # noqa: E402
import test_player  # noqa: E402

cpcsim = test_player.cpcsim


def read(*parts):
    with open(os.path.join(ROOT, *parts), "rb") as fh:
        return fh.read()


class DemoFilesTest(unittest.TestCase):
    def test_songs_are_valid(self):
        gen_demo.check()                                  # (SystemExit sinon)
        self.assertEqual([s["name"] for s in gen_demo.DEMO], ["ARCADE", "STUDIO"])
        self.assertEqual(len(gs.SONGS), 5)                # les morceaux de test restent à part

    def test_files_up_to_date(self):
        """demo/ et samples/STUDIO.SMP sont ceux que fabrique gen_demo.py."""
        self.assertEqual(read("samples", "STUDIO.SMP"), gen_demo.studio_bank())
        for s in gen_demo.DEMO:
            self.assertEqual(read("demo", s["name"] + ".SNG"), gs.song_file(s), s["name"])
            self.assertEqual(read("demo", s["name"] + ".INS"), gs.ins_bank(s), s["name"])
            for name, data in gs.encode_patterns(s):
                self.assertEqual(read("demo", "pat", name + ".PAT"), data, name)

    def test_arcade_without_samples_shows_layered_sound_and_effects(self):
        arcade = gen_demo.DEMO[0]
        self.assertIsNone(arcade["bank"])
        modes = {p["mode"] for p in arcade["patterns"]}
        self.assertEqual(modes, {gp.MONO, gp.POLY})       # son composé et voix séparées
        effects = set()
        for name, data in gs.encode_patterns(arcade):
            for cell in range(64):
                f = data[4 + 4 * cell + 3]
                if f:
                    effects.add(f >> 4)
        self.assertEqual(effects, set(range(1, 8)))       # les 7 effets

    def test_studio_bank(self):
        bank = wav2smp.parse_bank(read("samples", "STUDIO.SMP"))
        self.assertEqual([s.name for s in bank], ["KICK", "SNARE", "HAT", "CLAP", "SEQ16", "CRASH"])
        voice = bank[4]
        self.assertGreater(len(voice.data), 3000)         # le sample long
        sng = read("demo", "STUDIO.SNG")
        n = int.from_bytes(sng[gs.IMAGE_LEN:gs.IMAGE_LEN + 2], "little")
        self.assertEqual(sng[gs.IMAGE_LEN + 2:], read("samples", "STUDIO.SMP"))
        self.assertEqual(n, len(read("samples", "STUDIO.SMP")))

    def test_demo_disks(self):
        import amsdsk
        want = {"SEQ16", "SEQ16.SCR", "SEQ16.BIN", "ARCADE.SNG", "ARCADE.INS", "STUDIO.SNG", "STUDIO.INS",
                "STUDIO.SMP", "DRUMS.SMP"}
        want |= {p["name"] + ".PAT" for s in gen_demo.DEMO for p in s["patterns"]}
        for suffix in ("-fr", "-en", "-es"):
            dsk = os.path.join(ROOT, "build", "seq16-demo%s.dsk" % suffix)
            self.assertEqual(set(amsdsk.list_files(dsk)), want, suffix)
            prog = os.path.join(ROOT, "build", "seq16%s.dsk" % suffix)
            self.assertEqual(amsdsk.read_file(dsk, "SEQ16.BIN"),
                             amsdsk.read_file(prog, "SEQ16.BIN"), suffix)


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class DemoPlayTest(unittest.TestCase):
    def test_studio_loads_its_bank_and_plays_the_voice(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        path = os.path.join(d, "t.dsk")
        shutil.copy(os.path.join(ROOT, "build", "seq16-demo-fr.dsk"), path)
        cpc = cpcsim.CPC.from_build(path)
        cpc.boot()
        cpc.use_disk(path)
        cpc.frames(1, keys={cpcsim.KEY_SONG})
        cpc.frames(1)
        names = [n for n in cpc.files if n.endswith(".SNG")]
        cpc.chars = [0xF1] * names.index("STUDIO.SNG") + [13]
        cpc.frames(1, keys={3})                           # f9
        cpc.frames(1)
        self.assertIn("SAMPLES CHARGES", cpc.row(25))
        self.assertEqual(cpc.peek(cpc.addr("smp_count"))[0], 6)
        dg = cpc.addr("dg_play")
        played = []
        orig = cpc.step

        def step():
            if cpc.m.pc == dg:
                played.append(cpc.peek(cpc.addr("dg_smp"))[0])
            orig()
        cpc.step = step
        cpc.frames(1, keys={47})                          # ESPACE
        cpc.frames(200)
        cpc.step = orig
        self.assertEqual(played[0], 4)                    # la voix ouvre le morceau
        self.assertTrue({0, 2}.issubset(played))          # puis la batterie
        self.assertEqual(cpc.file_errors, [])

    def test_disk_panel_line_without_gap(self):
        """Panneau DISQUE : « ENTER : DANS 1SONG » - la traduction, plus
        courte, ne laisse pas de trou avant le nom de l'onglet."""
        want = {"-fr": "ARCADE.SNG  ENTER : DANS 1SONG", "-en": "ARCADE.SNG  ENTER: INTO 1SONG",
                "-es": "ARCADE.SNG  ENTER: EN 1TEMA"}
        for suffix, line in want.items():
            dsk = os.path.join(ROOT, "build", "seq16-demo%s.dsk" % suffix)
            cpc = cpcsim.CPC.from_build(dsk)
            cpc.boot()
            cpc.use_disk(dsk)
            cpc.frames(1, keys={cpcsim.KEY_DISK})
            cpc.frames(2)
            self.assertEqual(cpc.row(19).rstrip(), line, suffix)


if __name__ == "__main__":
    unittest.main()
