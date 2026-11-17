"""Tests des banques d'instruments .INS (sans simulateur).

Lancement :  python -m unittest tools.test_insbank
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_instruments  # noqa: E402
import insbank  # noqa: E402


class InsBankTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.banks = gen_instruments.all_banks()

    def test_format(self):
        for fname, _, data in self.banks:
            with self.subTest(fname):
                self.assertEqual(len(data), insbank.INS_FILE_LEN)     # 848 octets
                self.assertEqual(data[:5], b"SQ16\x01")
                sounds, sons = insbank.parse_ins_bank(data)
                self.assertEqual(len(sounds), 32)
                self.assertEqual(len({n for n, _ in sounds}), 32)     # noms uniques
                self.assertEqual(sons, insbank.SONS_USINE)

    def test_amsdos_names(self):
        names = [f for f, _, _ in self.banks]
        self.assertEqual(len(names), len(set(names)))
        for f in names:
            base, ext = f.split(".")
            self.assertLessEqual(len(base), 8)
            self.assertEqual(ext, "INS")
        # la liste de choix du CPC montre 16 fichiers au plus : on en laisse
        # au moins 2 pour les banques de l'utilisateur
        self.assertLessEqual(len(names), 14)

    def test_values_in_range(self):
        """Chaque valeur reste dans les bornes de l'écran f2."""
        for fname, _, data in self.banks:
            sounds, _ = insbank.parse_ins_bank(data)
            for name, b in sounds:
                with self.subTest(bank=fname, sound=name):
                    self.assertLessEqual(b[2], 15)                    # tenue
                    self.assertLessEqual(b[4], 15)                    # volume
                    self.assertGreater(b[4], 0)
                    self.assertLessEqual(b[5], 15)                    # drapeaux
                    self.assertTrue(b[5] & (insbank.TON | insbank.BRUIT | insbank.ENV),
                                    "ni ton, ni bruit, ni enveloppe : muet")
                    self.assertLessEqual(b[6], 31)                    # bruit
                    if b[5] & insbank.ENV:
                        self.assertTrue(8 <= b[7] <= 15 or fname == "USINE.INS" or b[7] == 0)
                        self.assertLessEqual(b[8], 7)                 # division
                    self.assertLessEqual(b[9], 24)                    # arpège
                    self.assertLessEqual(b[10], 24)
                    if b[9] or b[10]:
                        self.assertTrue(1 <= b[11] <= 15)             # vitesse
                    self.assertLessEqual(b[12], 6)                    # vibrato

    def test_usine_is_factory(self):
        """USINE.INS = les instruments par défaut, gardés dans le programme."""
        usine = dict((f, d) for f, _, d in self.banks)["USINE.INS"]
        sounds, _ = insbank.parse_ins_bank(usine)
        self.assertEqual(sounds[0][0], "LEAD  ")
        self.assertEqual(sounds[11][0], "KICK  ")
        self.assertEqual(sounds[0][1], bytes([255, 8, 10, 12, 15, 1] + [0] * 10))

    def test_files_up_to_date(self):
        """Les fichiers de instruments/ sont ceux que produit le script."""
        for fname, _, data in self.banks:
            path = os.path.join(gen_instruments.OUT_DIR, fname)
            with self.subTest(fname):
                self.assertTrue(os.path.exists(path), "lancer tools/gen_instruments.py")
                self.assertEqual(open(path, "rb").read(), data)

    def test_build_errors(self):
        with self.assertRaises(ValueError):
            insbank.build_ins_bank([("X", bytes(16))] * 33)
        with self.assertRaises(ValueError):
            insbank.build_ins_bank([("X", bytes(15))])
        with self.assertRaises(ValueError):
            insbank.parse_ins_bank(bytes(848))


if __name__ == "__main__":
    unittest.main()
