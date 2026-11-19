"""Tests de la bibliothèque de motifs d'usine (tools/gen_patterns.py).

- le format de chaque motif (.PAT de 260 octets) ;
- les fichiers de patterns/ et les deux disquettes build/seq16-motifs-*.dsk
  sont à jour et identiques à ce que le générateur produit ;
- au simulateur (paquet z80) : quelques motifs de chaque disquette sont
  chargés par f3 P dans le vrai SEQ16.BIN, puis joués sur f1 (ESPACE).

Lancement :  python -m unittest tools.test_gen_patterns
Il faut la bibliothèque CPC DISK (variable CPC_DISK, voir tools/cpcdisk.py).
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_patterns as gp  # noqa: E402
import amsdsk  # noqa: E402
import test_player  # noqa: E402

cpcsim = test_player.cpcsim
ROOT = gp.ROOT
DISKS = {"mono": "seq16-motifs-mono.dsk", "poly": "seq16-motifs-poly.dsk"}
KEY_F1, KEY_F3, KEY_F4, KEY_P, KEY_SPACE = 13, 5, 20, 27, 47
DSK_ROW = 17                              # f3 : ligne des messages
SONG_FIXED = 16 + 32 * 16 + 32 * 6 + 8 * 16


def cells(data):
    """[(pas, voix, note, instrument, volume, effet)] d'un motif."""
    out = []
    for s in range(16):
        for v in range(4):
            o = 4 + 16 * s + 4 * v
            out.append((s, v) + tuple(data[o:o + 4]))
    return out


class FormatTest(unittest.TestCase):
    def test_counts(self):
        for disk in DISKS:
            n = sum(p["disk"] == disk for p in gp.PATTERNS)
            self.assertTrue(55 <= n <= 63, (disk, n))

    def test_names(self):
        names = [p["name"] for p in gp.PATTERNS]
        self.assertEqual(len(names), len(set(names)))
        for n in names:
            self.assertRegex(n, r"^[A-Z0-9]{1,8}$")

    def test_metadata(self):
        for p in gp.PATTERNS:
            self.assertEqual(len(p["desc"]), 3, p["name"])
            self.assertTrue(all(d.strip() for d in p["desc"]), p["name"])
            self.assertTrue(p["style"])
            self.assertTrue(80 <= p["bpm"] <= 170, p["name"])

    def test_every_pattern_format(self):
        for p in gp.PATTERNS:
            with self.subTest(p["name"]):
                data = gp.encode(p)
                self.assertEqual(len(data), 260)
                mode = data[0]
                self.assertEqual(mode, 1 if p["disk"] == "mono" else 0)
                self.assertEqual(data[1], p["bpm"])
                self.assertEqual(data[2:4], b"\0\0")
                notes = 0
                for s, v, n, ins, vol, fx in cells(data):
                    self.assertEqual(fx, 0)
                    self.assertTrue(vol <= 15 or vol == 0xFF)
                    self.assertTrue(n <= 95 or n in (0xFE, 0xFF))
                    if mode == 1 and v > 0:      # mono : seule la 1re case sert
                        self.assertEqual((n, ins, vol), (0xFF, 0, 0xFF))
                        continue
                    if n in (0xFE, 0xFF):
                        continue
                    notes += 1
                    if mode == 1:
                        self.assertLessEqual(ins, 7)           # son composé
                    else:
                        self.assertLessEqual(ins, 31)
                        if v == 3:
                            self.assertLessEqual(n, 31)        # période du bruit
                self.assertGreater(notes, 0)

    def test_musical_checks(self):
        """Gamme, tessiture, frottements, notes tenues (gen_patterns.check)."""
        for p in gp.PATTERNS:
            self.assertEqual(gp.check(p), [], p["name"])

    def test_checker_catches_problems(self):
        good = next(p for p in gp.PATTERNS if p["name"] == "POPCHRD1")
        wrong = dict(good, lanes=[gp.R("x.x-x.x-x.x-x.x-", "C4@1 C#4@1"), None, None, None])
        self.assertTrue(any("gamme" in e for e in gp.check(wrong)))
        clash = dict(next(p for p in gp.PATTERNS if p["name"] == "BALLAD01"))
        clash["lanes"] = [gp.R("x..-x..-x..-x..-", "C3 A2 F2 G2", "BASS"),
                          gp.R("x...x...x...x..-", "B3 C4 A3 B3", "PAD"), None, None]
        self.assertTrue(any("demi-ton" in e for e in gp.check(clash)))
        drone = dict(good, lanes=[gp.R("x...............", "C4@1"), None, None, None])
        self.assertTrue(any("tenue" in e for e in gp.check(drone)))

    def test_showcase_first(self):
        for disk in DISKS:
            order = [p["name"] for p in gp.disk_order(disk)]
            self.assertEqual(order[:16], gp.SHOWCASE[disk])


class FilesTest(unittest.TestCase):
    def test_pattern_files_up_to_date(self):
        for disk in DISKS:
            folder = os.path.join(ROOT, "patterns", disk)
            expected = {p["name"] + ".PAT": gp.encode(p) for p in gp.PATTERNS if p["disk"] == disk}
            self.assertEqual(set(os.listdir(folder)), set(expected))
            for name, data in expected.items():
                with open(os.path.join(folder, name), "rb") as fh:
                    self.assertEqual(fh.read(), data, name)

    def test_disks(self):
        for disk, dsk in DISKS.items():
            path = os.path.join(ROOT, "build", dsk)
            pats = gp.disk_order(disk)
            listed = amsdsk.list_files(path)
            self.assertEqual(list(listed), [p["name"] + ".PAT" for p in pats])
            for p in pats:
                name = p["name"] + ".PAT"
                self.assertEqual(amsdsk.read_file(path, name), gp.encode(p), name)
                raw = amsdsk.read_file(path, name, keep_header=True)
                head = amsdsk.amsdos.parse_header(raw)          # en-tête AMSDOS
                self.assertIsNotNone(head, name)
                self.assertEqual(head["length"], 260)

    def test_liste(self):
        with open(os.path.join(ROOT, "patterns", "LISTE.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(text, gp.liste_md())
        for p in gp.PATTERNS:
            self.assertIn("`%s.PAT`" % p["name"], text)


def sample(disk, k=8):
    """k motifs répartis sur la disquette (dont un digidrum s'il y en a)."""
    pats = gp.disk_order(disk)
    out = [pats[i * len(pats) // k] for i in range(k)]
    digi = [p for p in pats if p["name"].startswith("DIGI")]
    if digi and not any(p in digi for p in out):
        out[-1] = digi[0]
    return out


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class SimulatorTest(unittest.TestCase):
    """f3 P charge le motif, ESPACE sur f1 le joue."""

    @classmethod
    def setUpClass(cls):
        cpc = cpcsim.CPC.from_build()
        cpc.boot()
        cpc.frames(2, keys={KEY_F4})       # f4 : la banque DRUMS.SMP se charge
        cpc.frames(1)                      # (pour les motifs à digidrums)
        cls.base = cpc

    def setUp(self):
        self.cpc = test_player.PlayerTest._clone(self.base)

    make_disk = test_player.PlayerTest.make_disk

    def key(self, *keys):
        self.cpc.frames(1, keys=set(keys))
        self.cpc.frames(1)

    def play(self, p):
        cpc = self.cpc
        data = gp.encode(p)
        self.make_disk({p["name"] + ".PAT": data})
        self.key(KEY_F3)
        cpc.chars = [13]                   # un seul .PAT : RETURN
        self.key(KEY_P)
        self.assertIn("MOTIF CHARGE", cpc.row(DSK_ROW))
        slot = cpc.addr("smp_blk_src") + SONG_FIXED       # motif 1 (en cours)
        self.assertEqual(cpc.peek(slot, 260), data)
        self.assertEqual(cpc.peek(cpc.addr("seq_bpm"))[0], p["bpm"])
        self.key(KEY_F1)
        self.assertIn("BPM:%03d" % p["bpm"], cpc.row(3))
        n0 = len(cpc.ay_writes)
        self.key(KEY_SPACE)
        self.assertEqual(cpc.peek(cpc.addr("seq_playing"))[0], 1)
        steps = set()
        for _ in range(30):                # 300 images = 6 secondes
            cpc.frames(10)
            self.assertFalse(cpc.stopped)
            steps.add(cpc.peek(cpc.addr("seq_pos"))[0])
        self.assertEqual(cpc.peek(cpc.addr("seq_playing"))[0], 1)
        self.assertGreaterEqual(len(steps), 8)             # la lecture avance
        writes = cpc.ay_writes[n0:]
        vols = [v for _, r, v in writes if r in (8, 9, 10) and v & 0x1F]
        tones = [v for _, r, v in writes if r <= 5]
        self.assertTrue(vols, "aucun volume envoyé à l'AY")
        self.assertTrue(tones, "aucune hauteur envoyée à l'AY")

    def test_mono_sample(self):
        for p in sample("mono"):
            with self.subTest(p["name"]):
                self.setUp()
                self.play(p)

    def test_poly_sample(self):
        for p in sample("poly"):
            with self.subTest(p["name"]):
                self.setUp()
                self.play(p)


if __name__ == "__main__":
    unittest.main()
