"""Tests de la lecture des samples sur le vrai binaire, au simulateur Z80.

Le binaire testé est celui de build/seq16.dsk (et ses étiquettes dans
build/seq16.sym) : lancer build.bat avant, après toute modification de src/.

Nécessite le paquet z80 :  pip install z80
Lancer :  python -m unittest tools.test_player   (depuis la racine)
     ou :  python tools/test_player.py
"""
import os
import sys
import unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wav2smp  # noqa: E402
import gen_smp_tables  # noqa: E402

try:
    import cpcsim
    from cpcsim import CPC, KEY_F3, KEY_F4, KEY_SPACE, KEY_D, KEY_RIGHT, \
        KEY_DOWN, KEY_CTRL, PIANO_KEYS
except ImportError:                      # paquet z80 absent
    cpcsim = None

ROOT = os.path.join(HERE, "..")
BANK = 0x0040                            # BANK_START dans src/sample.asm
KEY_PERIOD = 163 + 4                     # durée d'un échantillon après le test
                                         # du clavier, quand P est plus court


def drums():
    return wav2smp.parse_bank(open(os.path.join(ROOT, "samples", "DRUMS.SMP"), "rb").read())


def expected_codes(data, decim=1, bits=4, curve=wav2smp.CURVE_LOG):
    """Ce que la routine doit écrire dans le registre de volume."""
    codes = wav2smp.unpack(data)
    m = wav2smp.BITS_MASK[bits]
    t = wav2smp.CURVE_TABLES[curve]
    return [t[codes[(i // decim) * decim] & m] for i in range(len(codes))]


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class PlayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Démarrage puis passage sur f4 : la banque d'usine se charge seule.
        cpc = CPC.from_build()
        cpc.boot()
        cpc.frames(2, keys={KEY_F4})
        cpc.frames(1)
        cls.base = cpc

    def setUp(self):
        # Chaque test repart d'une copie de la machine après le démarrage.
        self.cpc = self._clone(self.base)
        self.cpc.strict = [(self.cpc.addr("smp_play"), self.cpc.addr("smp_blk_end"))]

    @staticmethod
    def _clone(src):
        c = CPC(b"", src.sym)
        c.m.set_memory_block(0, bytes(src.mem))
        for r in ("af", "bc", "de", "hl", "ix", "iy", "sp", "pc"):
            setattr(c.m, r, getattr(src.m, r))
        c.m.iff1 = c.m.iff2 = 1
        c.files = dict(src.files)
        c.screen = [row[:] for row in src.screen]
        c.attr = [row[:] for row in src.attr]
        c.ay = list(src.ay)
        c.t = src.t
        return c

    def fiche(self, i):
        return BANK + 16 + 16 * i

    def play(self, i=0, semi=0, chan=0):
        """Joue le sample i ; renvoie [(instant, valeur)] des écritures du
        volume pendant la lecture (interruptions coupées)."""
        cpc = self.cpc
        n0 = len(cpc.ay_writes)
        cpc.call("smp_play_sample", a=i, b=semi & 0xFF, c=chan)
        start, end = cpc.di_spans[-1]
        w = [x for x in cpc.ay_writes[n0:] if start <= x[0] <= end]
        return w

    def samples_of(self, writes, reg=8):
        """Les écritures du volume qui sont des échantillons (sans la remise
        du volume à la fin)."""
        vol = [(t, v) for t, r, v in writes if r == reg]
        return vol[:-1]

    # --- installation et écran -------------------------------------------
    def test_installed(self):
        cpc = self.cpc
        self.assertEqual(cpc.peek(cpc.addr("smp_ok"))[0], 1)
        self.assertEqual(cpc.peek(cpc.addr("smp_count"))[0], 4)
        # la routine recopiée en zone haute est identique à celle du fichier
        # SEQ16.BIN (en mémoire, sa source est ensuite recouverte par le
        # morceau : on compare donc avec le fichier, chargé en #4000)
        src = cpc.addr("smp_blk_src") if "SMP_BLK_SRC" in cpc.sym else None
        self.assertIsNotNone(src)
        n = cpc.addr("smp_blk_end") - cpc.addr("smp_play")
        binary = cpcsim.amsdsk.read_file(os.path.join(ROOT, "build", "seq16.dsk"), "SEQ16.BIN")
        self.assertEqual(binary[src - 0x4000:src - 0x4000 + n],
                         cpc.peek(cpc.addr("smp_play"), n))
        self.assertGreaterEqual(cpc.addr("smp_play"), 0x8000)
        # le morceau commence bien sur cette source, devenue inutile
        self.assertEqual(cpc.addr("song_data") if "SONG_DATA" in cpc.sym else src, src)
        self.assertEqual(cpc.peek(src, 4), b"SQ16")

    def test_screen_f4(self):
        txt = self.cpc.screen_text()
        self.assertIn("f4 SAMPLE", self.cpc.row(1))
        self.assertEqual(len(self.cpc.row(1).rstrip()), 40)
        self.assertIn("BANQUE : DRUMS", txt)
        self.assertIn("2037/16320", txt)
        for i, name in enumerate(["KICK", "SNARE", "HAT", "CLAP"]):
            self.assertIn("%02d %-6s" % (i + 1, name), self.cpc.row(5 + i))
        self.assertIn("147MS", self.cpc.row(5))
        self.assertIn("6250 HZ", self.cpc.row(5))
        self.assertIn("LOG", self.cpc.row(8))
        self.assertIn("160 NOP", self.cpc.row(9))
        self.assertIn("BANQUE CHARGEE", self.cpc.row(22))
        # le sample choisi en jaune inversé : encre 0 sur fond 1
        self.assertEqual(self.cpc.attr[4][3], (0, 1))
        self.assertEqual(self.cpc.attr[5][3], (3, 0))

    # --- la lecture elle-même ---------------------------------------------
    def check_cadence(self, samples, period):
        iv = [b[0] - a[0] for a, b in zip(samples, samples[1:])]
        c = Counter(iv)
        glitch = 0 if period >= KEY_PERIOD else KEY_PERIOD
        allowed = {period, glitch} if glitch else {period}
        self.assertTrue(set(c) <= allowed, c)
        if glitch:                       # un accroc toutes les 256 échantillons
            self.assertEqual(c[glitch], (len(samples) - 1) // 256)

    def test_play_kick_values_and_rate(self):
        w = self.play(0)
        s = self.samples_of(w)
        kick = drums()[0]
        self.assertEqual([v for _, v in s], expected_codes(kick.data))
        self.check_cadence(s, 160)               # 1 000 000 / 160 = 6250 Hz

    def test_space_key_from_f4(self):
        """ESPACE sur l'écran f4 joue le sample choisi, en entier."""
        cpc = self.cpc
        n0 = len(cpc.ay_writes)
        cpc.frames(1, keys={KEY_SPACE})
        start, end = cpc.di_spans[-1]
        s = [(t, v) for t, r, v in cpc.ay_writes[n0:] if r == 8 and start <= t <= end][:-1]
        self.assertEqual(len(s), 2 * len(drums()[0].data))

    def test_register_selection_and_restore(self):
        cpc = self.cpc
        mixer = cpc.peek(cpc.addr("ay_regs") + 7)[0]
        vol_a = cpc.peek(cpc.addr("ay_regs") + 8)[0]
        s0 = len(cpc.ay_selects)
        w = self.play(1)
        # pendant la lecture, seuls le mixeur (7) et le volume A (8) sont écrits
        self.assertEqual({r for _, r, _ in w}, {7, 8})
        # premier : mixeur avec le ton et le bruit de A fermés (bits 0 et 3)
        self.assertEqual(w[0][1], 7)
        self.assertEqual(w[0][2], mixer | 0x09)
        # le registre 14 (clavier) n'est choisi que pour le test d'ESPACE, et
        # le registre de volume est rechoisi juste après
        sel = [r for _, r in cpc.ay_selects[s0:]]
        for i, r in enumerate(sel):
            if r == 14:
                self.assertEqual(sel[i + 1], 8)
        # à la fin : mixeur et volume du moteur remis, interruptions ouvertes
        self.assertEqual(w[-2][1:], (7, mixer))
        self.assertEqual(w[-1][1:], (8, vol_a))
        self.assertTrue(cpc.m.iff1)
        self.assertEqual(cpc.ppi_ctrl[-1][1], 0x82)   # port A en sortie
        self.assertEqual(cpc.ppi_c & 0xC0, 0)          # AY au repos
        self.assertFalse(cpc.ppi_a_input)

    def test_shadow_registers_preserved(self):
        """BC' (et les autres registres « bis ») servent au firmware."""
        cpc = self.cpc
        cpc.m.alt_bc, cpc.m.alt_de, cpc.m.alt_hl, cpc.m.alt_af = 0x7F89, 0x1234, 0x5678, 0x9ABC
        self.play(2)
        self.assertEqual((cpc.m.alt_bc, cpc.m.alt_de, cpc.m.alt_hl, cpc.m.alt_af),
                         (0x7F89, 0x1234, 0x5678, 0x9ABC))

    def test_grain_settings(self):
        """Décimation, bits et courbe changent exactement ce qui est écrit."""
        snare = drums()[1]
        for decim_i, bits_i, curve in ((2, 0, 1), (0, 2, 1), (0, 0, 3), (5, 3, 0), (1, 1, 4)):
            with self.subTest(decim=decim_i, bits=bits_i, curve=curve):
                self.cpc = self._clone(self.base)
                f = self.fiche(1)
                self.cpc.poke(f + 15, [decim_i | bits_i << 3])
                self.cpc.poke(f + 14, [curve << 4])
                s = self.samples_of(self.play(1))
                exp = expected_codes(snare.data, wav2smp.DECIMS[decim_i],
                                     [4, 3, 2, 1][bits_i], curve)
                self.assertEqual([v for _, v in s], exp)
                self.check_cadence(s, 125)

    def test_frequency_and_pitch(self):
        pitch = gen_smp_tables.pitch_table()
        for code, semi in ((250, 0), (200, -12), (125, 7), (100, 12), (62, 0), (62, 12), (250, -12)):
            with self.subTest(code=code, semi=semi):
                self.cpc = self._clone(self.base)
                self.cpc.poke(self.fiche(2) + 11, [code])
                s = self.samples_of(self.play(2, semi))
                p = code * pitch[semi + 12] // 256
                p = max(56, min(1000, p))
                self.check_cadence(s, p)

    def test_channels(self):
        for chan in (1, 2, 3):           # 3 = voie N : c'est la voie C
            with self.subTest(chan=chan):
                self.cpc = self._clone(self.base)
                mixer = self.cpc.peek(self.cpc.addr("ay_regs") + 7)[0]
                w = self.play(3, chan=chan)
                reg = 8 + min(chan, 2)
                self.assertEqual({r for _, r, _ in w}, {7, reg})
                self.assertEqual(w[0][2], mixer | (0x09 << min(chan, 2)))
                self.assertEqual(len(self.samples_of(w, reg)), 2 * len(drums()[3].data))

    def test_space_stops_long_sample(self):
        """ESPACE, relâchée puis enfoncée, arrête une longue lecture."""
        cpc = self.cpc
        long_smp = wav2smp.Sample("LONG", bytes([0xC3]) * 4096, 125)
        cpc.files["LONG.SMP"] = wav2smp.build_bank([long_smp])
        self.assertEqual(self.load("LONG.SMP"), 0)
        # 1er test : encore enfoncée (appui de départ) ; 2e : relâchée ;
        # 3e : enfoncée -> arrêt
        script = {1: {KEY_SPACE}, 2: set(), 3: {KEY_SPACE}}
        cpc.on_key_read = lambda c: setattr(c, "keys", script.get(c.key_reads, set()))
        cpc.key_reads = 0
        s = self.samples_of(self.play(0))
        self.assertEqual(len(s), 3 * 256)
        self.assertTrue(cpc.m.iff1)

    # --- chargement des banques -------------------------------------------
    def load(self, name):
        cpc = self.cpc
        addr = cpc.addr("fname_full")
        cpc.poke(addr, name.encode())
        cpc.m.hl = addr
        cpc.call("smp_load_bank", b=len(name))
        return cpc.m.a

    def test_load_errors(self):
        cpc = self.cpc
        self.assertEqual(self.load("ABSENT.SMP"), 1)
        self.assertEqual(cpc.peek(cpc.addr("smp_count"))[0], 0)
        cpc.files["BAD.SMP"] = b"XXXX" + bytes(40)
        self.assertEqual(self.load("BAD.SMP"), 3)
        cpc.files["BIG.SMP"] = wav2smp.build_bank(
            [wav2smp.Sample("A", bytes(16384), 125)] * 2)
        self.assertEqual(self.load("BIG.SMP"), 2)
        self.assertEqual(self.load("DRUMS.SMP"), 0)
        self.assertEqual(cpc.peek(cpc.addr("smp_count"))[0], 4)

    def test_no_bank_no_play(self):
        cpc = self.cpc
        self.load("ABSENT.SMP")
        n0 = len(cpc.ay_writes)
        cpc.call("smp_play_sample", a=0, b=0, c=0)
        self.assertEqual(len(cpc.ay_writes), n0)

    # --- l'écran f4 au clavier ---------------------------------------------
    def test_f4_keys_change_settings(self):
        cpc = self.cpc
        f = self.fiche(0)
        cpc.frames(1, keys={KEY_RIGHT})          # fréquence plus aiguë
        cpc.frames(1)
        self.assertEqual(cpc.peek(f + 11)[0], 159)
        cpc.frames(1, keys={KEY_DOWN})           # décimation
        cpc.frames(1)
        cpc.frames(1, keys={KEY_RIGHT})
        cpc.frames(1)
        self.assertEqual(cpc.peek(f + 15)[0] & 7, 1)
        self.assertIn("DECIMATION 2", cpc.row(6))
        cpc.frames(1, keys={KEY_CTRL, KEY_RIGHT})  # sample suivant
        cpc.frames(1)
        self.assertEqual(cpc.peek(cpc.addr("cur_smp"))[0], 1)
        self.assertEqual(cpc.attr[5][3], (0, 1))

    def test_piano_on_f4(self):
        """Une touche du piano joue le sample, plus aigu ou plus grave."""
        cpc = self.cpc
        pitch = gen_smp_tables.pitch_table()
        for idx, semi in ((12, 0), (19, 7), (0, -12)):
            with self.subTest(semi=semi):
                n0 = len(cpc.ay_writes)
                cpc.frames(1, keys={PIANO_KEYS[idx]})
                cpc.frames(1)
                start, end = cpc.di_spans[-1]
                s = [(t, v) for t, r, v in cpc.ay_writes[n0:] if r == 8 and start <= t <= end][:-1]
                self.check_cadence(s, 160 * pitch[semi + 12] // 256)

    def make_disk(self, extra, keep=("SEQ16.BIN", "DRUMS.SMP", "VOIX.SMP")):
        """Une disquette : celle du build, réduite aux fichiers keep (None :
        tous), + des fichiers en plus."""
        import shutil
        import tempfile
        import amsdsk
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        path = os.path.join(d, "t.dsk")
        shutil.copy(os.path.join(ROOT, "build", "seq16.dsk"), path)
        if keep is not None:
            for name in amsdsk.list_files(path):
                if name not in keep:
                    amsdsk.remove_file(path, name)
        for name, data in extra.items():
            amsdsk.add_file(path, name, data)
        self.cpc.use_disk(path)

    def test_f3_choose_bank(self):
        """f3 + D : liste des .SMP de la disquette, flèches, RETURN."""
        cpc = self.cpc
        two = [wav2smp.Sample("ONE", b"\x11" * 50, 125), wav2smp.Sample("TWO", b"\x22" * 60, 100)]
        self.make_disk({"TEST.SMP": wav2smp.build_bank(two),
                        "MORCEAU1.SNG": bytes(100)})
        cpc.frames(1, keys={KEY_F3})
        cpc.frames(1)
        # ordre du répertoire : DRUMS, VOIX, TEST -> bas, bas, haut, bas,
        # bas (déjà au dernier), RETURN : TEST
        cpc.chars = [0xF1, 0xF1, 0xF0, 0xF1, 0xF1, 13]
        cpc.frames(1, keys={KEY_D})
        cpc.frames(1)
        self.assertEqual(cpc.sector_reads[:4], [(0, 0, 0xC1), (0, 0, 0xC2),
                                                (0, 0, 0xC3), (0, 0, 0xC4)])
        self.assertEqual(cpc.peek(cpc.addr("smp_nfiles"))[0], 3)
        names = cpc.peek(cpc.addr("smp_files"), 24)
        self.assertEqual(names, b"DRUMS   VOIX    TEST    ")
        self.assertIn("BANQUE CHARGEE", cpc.row(17))
        self.assertEqual(cpc.row(19).strip(), "")      # la liste est effacée
        self.assertEqual(cpc.peek(cpc.addr("smp_count"))[0], 2)
        self.assertEqual(cpc.peek(cpc.addr("fname"), 8), b"MORCEAU1")  # NOM intact
        cpc.frames(1, keys={KEY_F4})
        cpc.frames(1)
        self.assertIn("BANQUE : TEST", cpc.screen_text())
        self.assertIn("01 ONE", cpc.row(5))
        self.assertIn("02 TWO", cpc.row(6))


    def test_song_save_and_load_still_work(self):
        """Non-régression : S puis L sur l'écran f3 (fichier .SNG)."""
        cpc = self.cpc
        song_size = 16 + 32 * 16 + 32 * 6 + 8 * 16 + 32 * (4 + 16 * 16)
        cpc.frames(1, keys={KEY_F3})
        cpc.frames(1)
        cpc.frames(1, keys={60})                 # S
        cpc.frames(1)
        self.assertIn("MORCEAU SAUVE", cpc.row(17))
        self.assertEqual(len(cpc.saved["MORCEAU1.SNG"]), song_size)
        cpc.files["MORCEAU1.SNG"] = cpc.saved["MORCEAU1.SNG"]
        cpc.frames(1, keys={36})                 # L
        cpc.frames(1)
        self.assertIn("MORCEAU CHARGE", cpc.row(17))


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class TimingTableTest(unittest.TestCase):
    def test_some_durations(self):
        mem = bytearray(65536)

        def nops(code, new_pc=None):
            mem[0x100:0x100 + len(code)] = bytes(code)
            return cpcsim.cpc_nops(mem, 0x100, new_pc if new_pc is not None else 0x100 + len(code))
        self.assertEqual(nops([0xED, 0x49]), 4)          # OUT (C),C
        self.assertEqual(nops([0xED, 0x71]), 4)          # OUT (C),0
        self.assertEqual(nops([0x1A]), 2)                # LD A,(DE)
        self.assertEqual(nops([0x5E]), 2)                # LD E,(HL)
        self.assertEqual(nops([0xD9]), 1)                # EXX
        self.assertEqual(nops([0x20, 0xFE], 0x100), 3)   # JR NZ pris
        self.assertEqual(nops([0x20, 0xFE]), 2)          # JR NZ non pris
        self.assertEqual(nops([0x10, 0xFE], 0x100), 4)   # DJNZ pris
        self.assertEqual(nops([0xC5]), 4)                # PUSH BC
        self.assertEqual(nops([0xED, 0x78]), 4)          # IN A,(C)


if __name__ == "__main__":
    unittest.main()
