"""Tests des versions anglaise et espagnole (tools/lang.py).

    python tools/lang.py en es --rasm <rasm>    (fabrique les disquettes)
    python tools/test_lang.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lang  # noqa: E402

try:
    import amsdsk
    from cpcsim import CPC, KEY_F3, KEY_F4
except ImportError:                  # paquet z80 ou CPC DISK absent
    CPC = None

KEY_F2 = 14
ROOT = lang.ROOT


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def dsk(code):
    return os.path.join(ROOT, "build", "seq16%s.dsk" % ("" if code == "fr" else "-" + code))


class TranslationTest(unittest.TestCase):
    def test_no_problem(self):
        self.assertEqual(lang.problems(), [])

    def test_translations_fit(self):
        for fr, trans in lang.TEXTS.items():
            for tr in trans:
                self.assertLessEqual(len(tr), len(fr), fr)

    def test_translate_line_keeps_length(self):
        line = '        db 1,25,3,0, "ESC MAINTENUE 1 SECONDE : QUITTER",0   ; aide\n'
        en = lang.translate_line(line, 0)
        self.assertIn('"HOLD ESC 1 SECOND: QUIT          "', en)
        self.assertTrue(en.endswith("; aide\n"))
        self.assertEqual(len(en), len(line))
        # Hors db : rien ne change (ici un commentaire et un 'save').
        for other in ('; "MORCEAU SAUVE"\n', "        save 'SEQ16.BIN',start\n"):
            self.assertEqual(lang.translate_line(other, 1), other)


@unittest.skipIf(CPC is None, "paquet z80 ou bibliothèque CPC DISK absent")
class BuiltLanguagesTest(unittest.TestCase):
    """Les trois disquettes : même programme, textes de la langue."""

    @classmethod
    def setUpClass(cls):
        for code in ("fr",) + lang.LANGS:
            if not os.path.exists(dsk(code)):
                raise unittest.SkipTest("disquettes non fabriquées (tools/lang.py)")

    def test_same_size_and_symbols(self):
        fr = amsdsk.read_file(dsk("fr"), "SEQ16.BIN")
        sym = read(os.path.join(ROOT, "build", "seq16.sym"))
        for code in lang.LANGS:
            other = amsdsk.read_file(dsk(code), "SEQ16.BIN")
            self.assertEqual(len(other), len(fr), code)
            path = os.path.join(ROOT, "build", "seq16-%s.sym" % code)
            self.assertEqual(read(path), sym, code)
            self.assertEqual(set(amsdsk.list_files(dsk(code))),
                             set(amsdsk.list_files(dsk("fr"))), code)

    def screens(self, code):
        """Texte des quatre écrans de la langue, après le démarrage."""
        cpc = CPC.from_build(dsk(code))
        cpc.boot()
        out = {"f1": cpc.screen_text()}
        for name, key in (("f2", KEY_F2), ("f3", KEY_F3), ("f4", KEY_F4)):
            cpc.frames(2, keys={key})
            cpc.frames(1)
            out[name] = cpc.screen_text()
        return out

    def check(self, code, expected):
        screens = self.screens(code)
        for name, words in expected.items():
            for w in words:
                self.assertIn(w, screens[name], f"{code} {name} : {w!r}")
        for name, text in screens.items():
            for line in text.splitlines():
                self.assertLessEqual(len(line.rstrip()), 40)

    def test_english(self):
        self.check("en", {
            "f1": ["PATTERN", "CURSOR", "SOUND LOCK", "f3 DISK"],
            "f2": ["ENVELOPE", "ATTACK", "BANK SOUND"],
            "f3": ["MIXER", "SAVE INSTR.", "CATALOG", "HOLD ESC 1 SECOND: QUIT"],
            "f4": ["BANK   :", "SETTINGS", "FREQUENCY", "TAKE 1 SAMPLE"],
        })

    def test_spanish(self):
        self.check("es", {
            "f1": ["PATRON:", "CURSOR", "BLOQ.SONID", "f3 DISCO"],
            "f2": ["ENVOLV.", "ATAQUE", "SON. BANCO"],
            "f3": ["MEZCLA", "GRABAR INSTR.", "CATALOGO", "ESC PULSADA 1 SEGUNDO: SALIR"],
            "f4": ["BANCO  :", "AJUSTES", "FRECUENC.", "TOMAR 1 SAMPLE"],
        })

    def test_french_unchanged(self):
        self.check("fr", {
            "f1": ["MOTIF :", "VERROU SON"],
            "f3": ["MIXAGE", "SAUVER INSTR."],
            "f4": ["REGLAGES"],
        })


if __name__ == "__main__":
    unittest.main()
