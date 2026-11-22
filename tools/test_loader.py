"""Tests de l'écran de chargement (tools/gen_screen.py, src/loader.asm).

RUN"SEQ16 lance le chargeur SEQ16 (sans extension) : il affiche SEQ16.SCR
en mode 0, charge SEQ16.BIN et le lance comme RUN" (MC_START_PROGRAM).
Lancement :  python -m unittest tools.test_loader
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
import gen_screen  # noqa: E402
import test_player  # noqa: E402

cpcsim = test_player.cpcsim
LANGS = ("fr", "en", "es")


def read(*parts):
    with open(os.path.join(ROOT, *parts), "rb") as fh:
        return fh.read()


class ScreenFilesTest(unittest.TestCase):
    def test_screens(self):
        for lang in LANGS:
            packed = read("build", "SEQ16-%s.SCR" % lang)
            self.assertLess(len(packed), 4096)                   # compressé
            scr = gen_screen.lz_unpack(packed)
            self.assertEqual(len(scr), 0x4000)
            self.assertEqual(gen_screen.from_scr(scr), gen_screen.draw(lang), lang)
            used = {c for row in gen_screen.draw(lang) for c in row}
            self.assertLessEqual(len(used), 16)

    def test_mode0_packing(self):
        for p0 in range(16):
            for p1 in range(16):
                self.assertEqual(gen_screen.unpack_pair(gen_screen.pack_pair(p0, p1)), (p0, p1))
        self.assertEqual(gen_screen.pack_pair(1, 0), 0x80)        # bit 0 du pixel de gauche
        self.assertEqual(gen_screen.pack_pair(0, 8), 0x01)        # bit 3 du pixel de droite
        self.assertEqual(gen_screen.screen_address(1, 0), 0x800)  # ligne 1 : 2 Ko plus loin
        self.assertEqual(gen_screen.screen_address(8, 3), 83)

    def test_files_up_to_date(self):
        self.assertEqual(read("src", "loader_inks.asm").decode("utf-8"), gen_screen.inks_asm())

    def test_disks(self):
        loader = read("build", "loader.bin")
        for lang in LANGS:
            dsk = os.path.join(ROOT, "build", "seq16-%s.dsk" % lang)
            files = amsdsk.list_files(dsk)
            for name in ("SEQ16", "SEQ16.SCR", "SEQ16.BIN"):
                self.assertIn(name, files, lang)
            self.assertEqual(amsdsk.read_file(dsk, "SEQ16.SCR"), read("build", "SEQ16-%s.SCR" % lang))
            self.assertEqual(amsdsk.read_file(dsk, "SEQ16"), loader)
            head = amsdsk.read_file(dsk, "SEQ16", keep_header=True)[:128]
            self.assertEqual(head[0x12], 2)                         # binaire
            self.assertEqual(head[0x15] | head[0x16] << 8, 0xA400)  # chargé en #A400
            self.assertEqual(head[0x1A] | head[0x1B] << 8, 0xA400)  # lancé en #A400


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class LoaderRunTest(unittest.TestCase):
    def run_loader(self, keep_screen=True):
        """Le chargeur sur une copie de seq16-fr.dsk ; renvoie la machine et
        ce que l'écran montrait au moment de lancer le programme."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        dsk = os.path.join(d, "t.dsk")
        shutil.copy(os.path.join(ROOT, "build", "seq16-fr.dsk"), dsk)
        if not keep_screen:
            amsdsk.remove_file(dsk, "SEQ16.SCR")
        cpc = cpcsim.CPC.from_build(dsk)
        cpc.use_disk(dsk)
        seen = {}
        orig = cpc.fw_MC_START_PROGRAM

        def start():
            seen["screen"] = cpc.peek(0xC000, 0x4000)
            seen["inks"] = dict(cpc.inks)
            seen["mode"] = cpc.mode
            orig()
        cpc.handlers = dict(cpc.handlers, MC_START_PROGRAM=start)
        cpc.poke(0xA400, read("build", "loader.bin"))
        cpc.m.iff1 = cpc.m.iff2 = 1
        cpc.m.sp = 0xC000
        cpc.m.pc = 0xA400
        cpc.run_until("MAIN_LOOP")
        return cpc, seen

    def test_loader_shows_screen_then_starts_program(self):
        cpc, seen = self.run_loader()
        self.assertEqual(seen["mode"], 0)
        self.assertEqual(seen["screen"], gen_screen.lz_unpack(read("build", "SEQ16-fr.SCR")))
        self.assertEqual(seen["inks"], {i: c for i, c in enumerate(gen_screen.INKS)})
        self.assertEqual(cpc.started, [(0x3F00, 0xFF)])     # lancé comme RUN"
        self.assertEqual(cpc.mode, 1)                         # le programme : mode 1
        self.assertIn("1SONG 2MOTIF", cpc.row(1))
        self.assertEqual(cpc.peek(cpc.addr("smp_ok"))[0], 1)  # samples en marche
        self.assertEqual(cpc.file_errors, [])

    def test_loader_without_screen_still_starts(self):
        cpc, seen = self.run_loader(keep_screen=False)
        self.assertEqual(cpc.started, [(0x3F00, 0xFF)])
        self.assertIn("1SONG 2MOTIF", cpc.row(1))


if __name__ == "__main__":
    unittest.main()
