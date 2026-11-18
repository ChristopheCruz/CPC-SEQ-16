"""Tests des digidrums (phase 4, mode BLOQUANT) et du morceau version 2.

On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py).
Lancement :  python -m unittest tools.test_digidrum   (paquet z80 nécessaire)
"""

import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402
import wav2smp  # noqa: E402

cpcsim = test_player.cpcsim
ROOT = test_player.ROOT
KEY_F1, KEY_F2, KEY_F3, KEY_F4 = 14 - 1, 14, 5, 20
KEY_SPACE, KEY_CTRL, KEY_LEFT, KEY_RIGHT = 47, 23, 8, 1
KEY_S, KEY_L, KEY_E = 60, 36, 58
DGKICK, DGSNAR = 28, 29                  # instruments d'usine 29 et 30
SONG_V1 = 16 + 32 * 16 + 32 * 6 + 8 * 16 + 32 * (4 + 16 * 16)
PAT_SIZE = 4 + 16 * 16


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class DigidrumTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cpc = cpcsim.CPC.from_build()
        cpc.boot()
        cpc.frames(2, keys={KEY_F4})             # f4 : DRUMS.SMP se charge
        cpc.frames(1)
        cpc.frames(1, keys={KEY_F1})             # retour au séquenceur
        cpc.frames(1)
        cls.base = cpc

    def setUp(self):
        self.cpc = test_player.PlayerTest._clone(self.base)
        self.drums = test_player.drums()

    make_disk = test_player.PlayerTest.make_disk

    # --- aides ---------------------------------------------------------------
    def song(self):
        return self.cpc.addr("smp_blk_src")

    def inst_addr(self, i):
        return self.song() + 16 + 16 * i

    def pattern_with(self, cells, mode=0):
        """Motif 1 vidé, puis ces cases : {(pas, voix): (note, instrument)}."""
        p = self.song() + 16 + 32 * 16 + 32 * 6 + 8 * 16
        data = bytearray([mode, 125, 0, 0] + [0xFF, 0, 0xFF, 0] * 64)
        for (step, lane), (note, ins) in cells.items():
            o = 4 + 16 * step + 4 * lane
            data[o:o + 4] = bytes([note, ins, 0xFF, 0])
        self.cpc.poke(p, data)

    def count_calls(self, label, action):
        """Exécute action() en comptant les passages sur l'étiquette."""
        cpc = self.cpc
        target = cpc.addr(label)
        n = [0]
        orig = cpc.step

        def step():
            if cpc.m.pc == target:
                n[0] += 1
            orig()
        cpc.step = step
        try:
            action()
        finally:
            cpc.step = orig
        return n[0]

    def key(self, *keys):
        self.cpc.frames(1, keys=set(keys))
        self.cpc.frames(1)

    def last_play(self, n_spans):
        """Ecritures des volumes pendant la dernière lecture (interruptions
        coupées) : {registre: [valeurs]}, sans la remise du volume à la fin."""
        cpc = self.cpc
        self.assertGreater(len(cpc.di_spans), n_spans, "aucun sample n'a joué")
        start, end = cpc.di_spans[-1]
        out = {}
        for t, r, v in cpc.ay_writes:
            if start <= t <= end and r in (8, 9, 10):
                out.setdefault(r, []).append(v)
        return {r: v[:-1] for r, v in out.items()}

    def frames_of(self, i, period):
        """Durée du sample i en images de 20 ms (arrondie au-dessus)."""
        n = len(self.drums[i].data) * 2
        return math.ceil(n * period / 20000)

    # --- séquenceur ----------------------------------------------------------
    def test_sequencer_plays_and_catches_up(self):
        cpc = self.cpc
        self.pattern_with({(0, 0): (48, DGKICK)})
        spans = len(cpc.di_spans)
        n = self.count_calls("seq_frame", lambda: self.key(KEY_SPACE))
        vols = self.last_play(spans)
        expected = test_player.expected_codes(self.drums[0].data)
        self.assertEqual(vols[8], expected)          # voie A, sample 0 (KICK)
        f = self.frames_of(0, 160)
        # 2 images normales (appui + relâche) + le rattrapage
        self.assertEqual(n, 2 + f)
        self.assertEqual(cpc.peek(cpc.addr("dg_debt"))[0], 0)
        self.assertEqual(cpc.peek(cpc.addr("dg_pending"))[0], 0)
        self.assertEqual(cpc.peek(cpc.addr("spr_att"))[0], 0)   # remise à 0

    def test_lane_gives_channel_and_mute(self):
        cpc = self.cpc
        self.pattern_with({(0, 1): (48, DGSNAR)})    # voix B -> registre 9
        spans = len(cpc.di_spans)
        self.key(KEY_SPACE)
        vols = self.last_play(spans)
        self.assertEqual(vols[9], test_player.expected_codes(self.drums[1].data))
        self.assertNotIn(8, vols)

    def test_noise_voice_uses_channel_c(self):
        cpc = self.cpc
        self.pattern_with({(0, 3): (1, DGKICK)})     # voix N : voie C, hauteur
        spans = len(cpc.di_spans)                    # d'origine
        self.key(KEY_SPACE)
        vols = self.last_play(spans)
        self.assertEqual(vols[10], test_player.expected_codes(self.drums[0].data))
        self.assertEqual(cpc.word(cpc.addr("smp_v_period")), 160)

    def test_muted_voice_is_silent(self):
        cpc = self.cpc
        self.pattern_with({(0, 0): (48, DGKICK)})
        cpc.poke(self.song() + 9, [1])               # voix A muette
        spans = len(cpc.di_spans)
        self.key(KEY_SPACE)
        self.assertEqual(len(cpc.di_spans), spans)

    def test_pitch_and_volume(self):
        cpc = self.cpc
        self.pattern_with({(0, 0): (60, DGKICK)})    # +12 demi-tons
        cpc.poke(self.inst_addr(DGKICK) + 4, [10])   # volume 10 : -5 niveaux
        spans = len(cpc.di_spans)
        self.key(KEY_SPACE)
        vols = self.last_play(spans)
        self.assertEqual(cpc.word(cpc.addr("smp_v_period")), 80)
        expected = [max(0, v - 5) for v in test_player.expected_codes(self.drums[0].data)]
        self.assertEqual(vols[8], expected)

    def test_missing_sample_plays_nothing(self):
        cpc = self.cpc
        cpc.poke(self.inst_addr(DGKICK) + 6, [9])    # la banque n'a que 4 sons
        self.pattern_with({(0, 0): (48, DGKICK)})
        spans = len(cpc.di_spans)
        self.key(KEY_SPACE)
        self.assertEqual(len(cpc.di_spans), spans)
        self.assertEqual(cpc.peek(cpc.addr("dg_pending"))[0], 0)

    # --- écran f2 ------------------------------------------------------------
    def goto_inst(self, n):
        self.key(KEY_F2)
        for _ in range(32):
            self.key(KEY_CTRL, KEY_LEFT)
        for _ in range(n):
            self.key(KEY_CTRL, KEY_RIGHT)

    def test_f2_shows_sample(self):
        cpc = self.cpc
        self.goto_inst(DGKICK)
        self.assertIn("29 DGKICK", cpc.row(2))
        self.assertIn("SAMPLE KICK", cpc.row(4 + 7))
        self.assertIn("DIGIDRUM", cpc.row(4 + 19))
        self.assertIn("OUI", cpc.row(4 + 19))
        self.goto_inst(0)                            # LEAD : période du bruit
        self.assertIn("PERIODE", cpc.row(4 + 7))
        self.assertIn("NON", cpc.row(4 + 19))

    def test_f2_piano_plays_digidrum(self):
        cpc = self.cpc
        self.goto_inst(DGKICK)
        spans = len(cpc.di_spans)
        self.key(67)                                 # touche du piano
        vols = self.last_play(spans)
        self.assertIn(8, vols)

    # --- morceau version 2 ---------------------------------------------------
    def test_song_v2_keeps_bank_name(self):
        cpc = self.cpc
        self.key(KEY_F3)
        self.key(KEY_S)
        data = cpc.saved["MORCEAU1.SNG"]
        self.assertEqual(len(data), SONG_V1 + 16)
        self.assertEqual(data[4], 2)                         # version 2
        self.assertEqual(data[SONG_V1 + 1:SONG_V1 + 9], b"DRUMS   ")

    def test_load_song_v1(self):
        """Un ancien morceau (version 1, sans le bloc v2) se charge encore."""
        cpc = self.cpc
        self.make_disk({})
        self.key(KEY_F3)
        self.key(KEY_S)
        v2 = cpc.saved["MORCEAU1.SNG"]
        v1 = bytearray(v2[:SONG_V1])
        v1[4] = 1
        cpc.poke(self.song() + SONG_V1, b"\x01XXXXXXXX")    # bloc v2 sali
        cpc.files["MORCEAU1.SNG"] = bytes(v1)
        self.key(KEY_L)
        self.assertIn("MORCEAU CHARGE", cpc.row(17))
        self.assertEqual(cpc.peek(self.song() + 4)[0], 2)
        self.assertEqual(cpc.peek(self.song() + SONG_V1, 16), bytes(16))

    def test_load_song_v2_loads_its_bank(self):
        cpc = self.cpc
        self.make_disk({})
        self.key(KEY_F3)
        self.key(KEY_S)
        v2 = bytearray(cpc.saved["MORCEAU1.SNG"])
        v2[SONG_V1 + 1:SONG_V1 + 9] = b"VOIX    "
        cpc.files["MORCEAU1.SNG"] = bytes(v2)
        self.key(KEY_L)
        self.assertIn("MORCEAU ET BANQUE", cpc.row(17))
        self.assertEqual(cpc.peek(cpc.addr("smp_name"), 8), b"VOIX    ")
        v2[SONG_V1 + 1:SONG_V1 + 9] = b"ABSENT  "            # banque absente
        cpc.files["MORCEAU1.SNG"] = bytes(v2)
        self.key(KEY_L)
        self.assertIn("BANQUE .SMP ABSENTE", cpc.row(17))
        self.assertEqual(cpc.peek(cpc.addr("smp_name"), 8), b"VOIX    ")

    # --- f4, O : prendre un sample dans une autre banque ---------------------
    def test_take_sample_from_bank(self):
        cpc = self.cpc
        self.make_disk({})                       # SEQ16.BIN, DRUMS, VOIX
        voix = wav2smp.parse_bank(open(os.path.join(ROOT, "samples", "VOIX.SMP"), "rb").read())
        self.key(KEY_F4)
        before = cpc.peek(test_player.BANK, cpc.word(cpc.addr("smp_bank_len")))
        # liste des .SMP : DRUMS, VOIX -> bas, RETURN ; puis le 2e sample
        cpc.chars = [0xF1, 13, 0xF1, 13]
        self.key(34)                             # O
        self.assertIn("SAMPLE AJOUTE", cpc.row(25))
        self.assertEqual(cpc.peek(cpc.addr("smp_count"))[0], 5)
        self.assertEqual(cpc.peek(cpc.addr("cur_smp"))[0], 4)
        n = cpc.word(cpc.addr("smp_bank_len"))
        bank = wav2smp.parse_bank(cpc.peek(test_player.BANK, n))
        self.assertEqual(len(bank), 5)
        old = wav2smp.parse_bank(before)
        for a, b in zip(bank[:4], old):              # les 4 anciens intacts
            self.assertEqual((a.name, a.data, a.code), (b.name, b.data, b.code))
        self.assertEqual(bank[4].name, voix[1].name)
        self.assertEqual(bank[4].data, voix[1].data)
        self.assertEqual(bank[4].code, voix[1].code)
        self.assertIn("05 " + voix[1].name.strip(), cpc.screen_text())
        # le nouveau sample se joue
        spans = len(cpc.di_spans)
        cpc.frames(1, keys={KEY_SPACE})
        cpc.frames(1)
        self.assertGreater(len(cpc.di_spans), spans)
        # et la banque agrandie se sauve
        self.key(KEY_F3)
        self.key(KEY_E)
        self.assertEqual(cpc.saved["DRUMS.SMP"], cpc.peek(test_player.BANK, n))

    def test_take_sample_too_big(self):
        cpc = self.cpc
        self.make_disk({})
        self.key(KEY_F4)
        cpc.poke(cpc.addr("smp_bank_len"), (16000).to_bytes(2, "little"))  # banque presque pleine
        cpc.chars = [0xF1, 13, 0xF1, 13]
        self.key(34)
        self.assertIn("TROP GRANDE", cpc.row(25))
        self.assertEqual(cpc.peek(cpc.addr("smp_count"))[0], 4)

    # --- f3, E : sauver la banque de samples ---------------------------------
    def test_save_smp(self):
        cpc = self.cpc
        self.key(KEY_F3)
        self.key(KEY_E)
        self.assertIn("BANQUE DE SAMPLES SAUVEE", cpc.row(17))
        original = open(os.path.join(ROOT, "samples", "DRUMS.SMP"), "rb").read()
        self.assertEqual(cpc.saved["DRUMS.SMP"], original)
        # un réglage changé sur f4 est sauvé avec la banque
        cpc.poke(test_player.BANK + 16 + 15, [3 << 3])  # réglages : 1 bit
        self.key(KEY_E)
        self.assertEqual(wav2smp.parse_bank(cpc.saved["DRUMS.SMP"])[0].bits, 1)


if __name__ == "__main__":
    unittest.main()
