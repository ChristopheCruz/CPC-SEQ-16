"""Tests de wav2smp.py, amsdsk.py et de la banque d'usine.

Lancer :  python -m unittest discover -s tools -p "test_*.py"
     ou :  python tools/test_wav2smp.py
"""
import math
import os
import random
import shutil
import struct
import sys
import tempfile
import unittest
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import amsdsk      # noqa: E402
import gen_drums   # noqa: E402
import wav2smp     # noqa: E402

ROOT = os.path.join(HERE, "..")


def sine(freq, seconds, rate=44100, amp=0.8):
    return [amp * math.sin(2 * math.pi * freq * i / rate) for i in range(int(seconds * rate))]


def write_raw_wav(path, frames, rate, width, channels):
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(frames)


class TestConversion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_ay_table(self):
        """16 niveaux croissants, de 0 à 1 (table Ayumi)."""
        self.assertEqual(len(wav2smp.AY_LEVELS), 16)
        self.assertEqual(wav2smp.AY_LEVELS[0], 0.0)
        self.assertEqual(wav2smp.AY_LEVELS[15], 1.0)
        self.assertEqual(sorted(wav2smp.AY_LEVELS), wav2smp.AY_LEVELS)

    def test_sine_roundtrip(self):
        """Un sinus converti puis relu : taille, niveaux, forme conservée."""
        x = sine(440, 0.5)
        s = wav2smp.convert(x, 44100, "sinus", rate=8000)
        raw = wav2smp.build_bank([s])
        back = wav2smp.parse_bank(raw)[0]
        self.assertEqual(back.name, "SINUS")
        self.assertEqual(back.code, 125)                # 1 000 000 / 8000
        self.assertEqual(len(back.data), 2000)          # 4000 échantillons / 2
        codes = wav2smp.unpack(back.data)
        self.assertTrue(all(0 <= c <= 15 for c in codes))
        self.assertIn(15, codes)                        # normalisé : crête au max
        # Le rendu doit rester corrélé au sinus d'origine (même période)
        ref = sine(440, 0.5, rate=8000)
        r = wav2smp.render(codes)
        corr = sum(a * b for a, b in zip(ref, r))
        norm = math.sqrt(sum(a * a for a in ref) * sum(b * b for b in r))
        self.assertGreater(corr / norm, 0.9)

    def test_quantize_nearest(self):
        """Chaque amplitude va au niveau AY le plus proche."""
        for code, lv in enumerate(wav2smp.AY_LEVELS):
            v = lv * 2 - 1                              # amplitude -> signal
            self.assertEqual(wav2smp.quantize([v])[0], code)
        rng = random.Random(0)
        for _ in range(500):
            v = rng.uniform(-1, 1)
            c = wav2smp.quantize([v])[0]
            a = (v + 1) / 2
            best = min(abs(lv - a) for lv in wav2smp.AY_LEVELS)
            self.assertAlmostEqual(abs(wav2smp.AY_LEVELS[c] - a), best)

    def test_dither_levels(self):
        x = [math.sin(i / 7) * 0.3 for i in range(2000)]
        codes = wav2smp.quantize(x, "noise", random.Random(5))
        self.assertTrue(all(0 <= c <= 15 for c in codes))

    def test_bits(self):
        x = sine(300, 0.2)
        for bits, mask in ((3, 0xE), (2, 0xC), (1, 0x8)):
            s = wav2smp.convert(x, 44100, "b", bits=bits)
            codes = wav2smp.unpack(s.data)
            self.assertTrue(all(c & ~mask == 0 for c in codes), bits)
        codes = wav2smp.unpack(wav2smp.convert(x, 44100, "b", bits=1).data)
        self.assertEqual(set(codes), {0, 8})

    def test_trim(self):
        x = [0.0] * 50 + [0.001, 0.5, -1.0, 0.3] + [0.0] * 80
        self.assertEqual(wav2smp.trim(x), [0.5, -1.0, 0.3])
        self.assertEqual(wav2smp.trim([0.0, 0.0]), [0.0, 0.0])

    def test_pack_order(self):
        """Premier échantillon dans les 4 bits de poids fort."""
        self.assertEqual(wav2smp.pack([1, 2, 3, 4]), bytes([0x12, 0x34]))
        self.assertEqual(wav2smp.pack([5]), bytes([0x55]))
        self.assertEqual(wav2smp.unpack(bytes([0xAB])), [10, 11])

    def test_header_and_entries(self):
        s1 = wav2smp.Sample("KICK", b"\x11" * 10, 160, decim=3, bits=2)
        s2 = wav2smp.Sample("LONGNAME", b"\x22" * 7, 80, loop=4,
                            flags=wav2smp.F_LOOP | wav2smp.F_BACKWARD | (2 << 4))
        raw = wav2smp.build_bank([s1, s2])
        self.assertEqual(raw[:4], b"SQSM")
        self.assertEqual(raw[4], 1)
        self.assertEqual(raw[5], 2)
        self.assertEqual(raw[6:16], bytes(10))
        self.assertEqual(len(raw), 16 + 2 * 16 + 17)
        e = raw[16:32]
        self.assertEqual(e[:6], b"KICK  ")
        self.assertEqual(e[6], 0)
        self.assertEqual(struct.unpack("<HHBHBB", e[7:16]), (0, 10, 160, 0xFFFF, 0, 2 | 2 << 3))
        e = raw[32:48]
        self.assertEqual(e[:6], b"LONGNA")
        self.assertEqual(struct.unpack("<H", e[7:9])[0], 10)   # après le 1er
        a, b = wav2smp.parse_bank(raw)
        self.assertEqual((a.decim, a.bits), (3, 2))
        self.assertEqual((b.loop, b.flags, b.data), (4, 0x23, b"\x22" * 7))

    def test_bad_headers(self):
        good = wav2smp.build_bank([wav2smp.Sample("A", b"\x00", 125)])
        with self.assertRaises(ValueError):
            wav2smp.parse_bank(b"XXXX" + good[4:])
        with self.assertRaises(ValueError):
            wav2smp.parse_bank(good[:4] + b"\x09" + good[5:])
        with self.assertRaises(ValueError):
            wav2smp.build_bank([])
        with self.assertRaises(ValueError):
            wav2smp.build_bank([wav2smp.Sample("A", b"\x00", 125)] * 17)

    def test_no_block_crossing(self):
        """Aucun sample ne chevauche une frontière de 16 Ko."""
        sizes = [10000, 10000, 16384, 300]
        raw = wav2smp.build_bank([wav2smp.Sample("S%d" % i, bytes([i]) * n, 125)
                                  for i, n in enumerate(sizes)])
        base = 16 + 16 * len(sizes)
        for i, n in enumerate(sizes):
            e = raw[16 + 16 * i:32 + 16 * i]
            blk, off = e[6], struct.unpack("<H", e[7:9])[0]
            self.assertLessEqual(off + n, wav2smp.BLOCK, i)
            start = base + blk * wav2smp.BLOCK + off
            self.assertEqual(raw[start:start + n], bytes([i]) * n)
        self.assertEqual([s.data for s in wav2smp.parse_bank(raw)],
                         [bytes([i]) * n for i, n in enumerate(sizes)])

    def test_rate_codes(self):
        self.assertEqual(wav2smp.rate_to_code(4000), 250)
        self.assertEqual(wav2smp.rate_to_code(16000), 62)
        self.assertEqual(wav2smp.rate_to_code(100000), 62)     # borné
        self.assertEqual(wav2smp.rate_to_code(1000), 250)

    def test_decimation_render(self):
        r = wav2smp.render([0, 15, 3, 7, 9, 1], decim=2)
        lv = wav2smp.AY_LEVELS
        expected = [lv[0], lv[0], lv[3], lv[3], lv[9], lv[9]]
        mean = sum(expected) / 6
        for a, b in zip(r, expected):
            self.assertAlmostEqual(a, b - mean)

    def test_resample_no_filter(self):
        x = list(range(100))
        self.assertEqual(wav2smp.resample(x, 1000, 250), [0, 4, 8, 12] + list(range(16, 100, 4)))
        self.assertEqual(len(wav2smp.resample(x, 1000, 250, clean=True)), 25)

    def test_wav_formats(self):
        """8 bits stéréo et 16 bits mono sont lus et mixés en mono."""
        p8 = os.path.join(self.tmp, "a.wav")
        write_raw_wav(p8, bytes([255, 1, 128, 128]), 22050, 1, 2)
        x, sr = wav2smp.read_wav(p8)
        self.assertEqual(sr, 22050)
        self.assertEqual(len(x), 2)
        self.assertAlmostEqual(x[0], 0.0, places=2)
        p16 = os.path.join(self.tmp, "b.wav")
        write_raw_wav(p16, struct.pack("<hh", 16384, -32768), 8000, 2, 1)
        x, _ = wav2smp.read_wav(p16)
        self.assertEqual(x, [0.5, -1.0])

    def test_cli_slice_and_preview(self):
        """--slice 4 : 4 samples de taille égale, 4 WAV d'écoute."""
        src = os.path.join(self.tmp, "boucle.wav")
        wav2smp.write_wav(src, sine(100, 1.0, rate=16000), 16000)
        out = os.path.join(self.tmp, "B.SMP")
        wav2smp.main([src, "--slice", "4", "--rate", "8000", "-o", out])
        bank = wav2smp.parse_bank(open(out, "rb").read())
        self.assertEqual([s.name for s in bank], ["BOUC00", "BOUC01", "BOUC02", "BOUC03"])
        self.assertEqual({len(s.data) for s in bank}, {1000})   # 0,25 s à 8 kHz
        for s in bank:
            p = os.path.join(self.tmp, "B_%s_ecoute.wav" % s.name)
            with wave.open(p) as w:
                self.assertEqual(w.getframerate(), 8000)
                self.assertEqual(w.getnframes(), 2000)

    def test_cli_names_and_size_warning(self):
        src = os.path.join(self.tmp, "x.wav")
        wav2smp.write_wav(src, sine(200, 1.0, rate=8000), 8000)
        out = os.path.join(self.tmp, "N.SMP")
        wav2smp.main([src, "--names", "ZAP", "--no-preview", "-o", out])
        raw = open(out, "rb").read()
        self.assertEqual(wav2smp.parse_bank(raw)[0].name, "ZAP")
        msgs = []
        wav2smp.check_sizes(raw, msgs.append)            # 4000 octets : < 4 Ko
        self.assertEqual(msgs, [])
        big = wav2smp.build_bank([wav2smp.Sample("A", bytes(16384), 125),
                                  wav2smp.Sample("B", bytes(100), 125)])
        wav2smp.check_sizes(big, msgs.append)
        self.assertIn("16 Ko", msgs[0])


class TestCurves(unittest.TestCase):
    def test_curve_tables(self):
        t = wav2smp.CURVE_TABLES
        self.assertEqual(len(t), 5)
        self.assertEqual(t[wav2smp.CURVE_LOG], list(range(16)))     # fidèle
        for row in t:
            self.assertEqual(len(row), 16)
            self.assertTrue(all(0 <= v <= 15 for v in row))
        self.assertEqual(t[4][wav2smp.REST], wav2smp.REST)          # repos fixe

    def test_asm_tables_match(self):
        """src/smptables.asm contient bien les tables de wav2smp.py."""
        import gen_smp_tables
        txt = open(os.path.join(ROOT, "src", "smptables.asm"), encoding="utf-8").read()
        rows = [l.split(";")[0].strip()[3:] for l in txt.splitlines()
                if l.strip().startswith("db") and ";" in l and "," in l]
        got = [[int(v) for v in r.split(",")] for r in rows[:5]]
        self.assertEqual(got, wav2smp.CURVE_TABLES)
        p = gen_smp_tables.pitch_table()
        self.assertEqual((p[0], p[12], p[24]), (512, 256, 128))
        self.assertIn("dw " + ",".join(str(v) for v in p[:8]), txt)

    def test_render_uses_curve(self):
        codes = [12, 15, 0]
        lin = wav2smp.render(codes, curve=0)
        log = wav2smp.render(codes, curve=1)
        self.assertNotEqual(lin, log)


class TestDsk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dsk = os.path.join(self.tmp, "t.dsk")
        shutil.copy(os.path.join(ROOT, "build", "seq16.dsk"), self.dsk)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_add_and_read_back(self):
        before = amsdsk.read_file(self.dsk, "SEQ16.BIN")
        data = bytes(random.Random(1).randrange(256) for _ in range(20000))
        amsdsk.add_file(self.dsk, "BIG.SMP", data)            # 2 extents
        self.assertEqual(amsdsk.read_file(self.dsk, "BIG.SMP"), data)
        self.assertEqual(amsdsk.read_file(self.dsk, "SEQ16.BIN"), before)
        amsdsk.add_file(self.dsk, "BIG.SMP", b"court")        # remplace
        self.assertEqual(amsdsk.read_file(self.dsk, "BIG.SMP"), b"court")
        files = amsdsk.list_files(self.dsk)
        self.assertIn("BIG.SMP", files)
        self.assertIn("SEQ16.BIN", files)

    def test_header_checksum(self):
        amsdsk.add_file(self.dsk, "DRUMS.SMP", b"\x01\x02\x03")
        raw = amsdsk.read_file(self.dsk, "DRUMS.SMP", keep_header=True)
        h = raw[:128]
        self.assertEqual(h[1:12], b"DRUMS   SMP")
        self.assertEqual(h[18], 2)
        self.assertEqual(struct.unpack("<H", h[67:69])[0], sum(h[:67]) & 0xFFFF)

    def test_cli_dsk(self):
        src = os.path.join(self.tmp, "x.wav")
        wav2smp.write_wav(src, sine(200, 0.1, rate=8000), 8000)
        out = os.path.join(self.tmp, "TEST.SMP")
        wav2smp.main([src, "--no-preview", "-o", out, "--dsk", self.dsk])
        self.assertEqual(amsdsk.read_file(self.dsk, "TEST.SMP"), open(out, "rb").read())


class TestFactoryBank(unittest.TestCase):
    def test_drums_bank(self):
        """La banque d'usine : 4 sons, < 4 Ko, < 150 ms chacun, à jour."""
        path = os.path.join(ROOT, "samples", "DRUMS.SMP")
        committed = open(path, "rb").read()
        bank = wav2smp.parse_bank(committed)
        self.assertEqual([s.name for s in bank], ["KICK", "SNARE", "HAT", "CLAP"])
        self.assertLess(len(committed), wav2smp.BANK_MAX_464)
        for s in bank:
            self.assertLessEqual(s.seconds, 0.150 + 1e-9, s.name)
        # Le fichier du dépôt correspond bien au script (synthèse déterministe)
        _, raw, _ = gen_drums.build()
        self.assertEqual(raw, committed)

    def test_dsk_contains_drums(self):
        dsk = os.path.join(ROOT, "build", "seq16.dsk")
        self.assertEqual(amsdsk.read_file(dsk, "DRUMS.SMP"),
                         open(os.path.join(ROOT, "samples", "DRUMS.SMP"), "rb").read())


if __name__ == "__main__":
    unittest.main()
