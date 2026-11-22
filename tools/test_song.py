"""Tests du panneau SONG (lot 4 du plan) : l'enchaînement des motifs, sa
lecture, le mixage, le .SNG version 3 et les noms des motifs.

On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py).
Lancement :  python -m unittest tools.test_song   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402
from test_patterns import make_pattern  # noqa: E402

cpcsim = test_player.cpcsim
KEY_MOTIF, KEY_SONG, KEY_SAVE, KEY_LOAD = 14, 13, 11, 3
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 8
SHIFT, CTRL, SPACE, RETURN, DEL, COPY, KEY_B = 21, 23, 47, 18, 79, 9, 54
PAT = 260
FIXED = 16 + 32 * 16 + 32 * 6 + 8 * 16
V3_LEN = 2 + 64 * 3 + 32 * 8
SONG_SIZE3 = FIXED + 32 * PAT + 16 + V3_LEN


def typed(text):
    return [ord(c) for c in text] + [13]


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class SongPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cpc = cpcsim.CPC.from_build()
        cpc.boot()
        test_player.demo_song(cpc)               # contenu connu (pas SYNTH)
        cls.base = cpc

    def setUp(self):
        self.cpc = test_player.PlayerTest._clone(self.base)
        self.v3 = self.cpc.addr("smp_blk_src") + FIXED + 16    # bloc v3 en mémoire

    make_disk = test_player.PlayerTest.make_disk

    def key(self, *keys):
        self.cpc.frames(1, keys=set(keys))
        self.cpc.frames(1)

    def var(self, name):
        return self.cpc.peek(self.cpc.addr(name))[0]

    def song(self):
        """(positions, boucle) du morceau en mémoire."""
        n = self.cpc.peek(self.v3)[0]
        loop = self.cpc.peek(self.v3 + 1)[0]
        raw = self.cpc.peek(self.v3 + 2, 3 * n)
        return [tuple(raw[i:i + 3]) for i in range(0, 3 * n, 3)], loop

    def set_song(self, pos, loop=0):
        data = bytes([len(pos), loop]) + b"".join(bytes([p, r, t & 0xFF]) for p, r, t in pos)
        self.cpc.poke(self.v3, data)

    # --- morceau d'usine, affichage ------------------------------------------------
    def test_factory_song(self):
        cpc = self.cpc
        self.assertEqual(self.song(), ([(0, 1, 0), (1, 1, 0)], 0))
        self.key(KEY_SONG)
        self.assertTrue(cpc.row(4).startswith("POS MOTIF"))
        self.assertTrue(cpc.row(5).startswith("00"))
        self.assertEqual(cpc.codes[4][2], 240)               # ↑ : départ de la boucle
        self.assertIn("01", cpc.row(5)[4:6])
        self.assertIn("x1", cpc.row(5))
        self.assertIn("-- FIN : RETOUR EN 00 --", cpc.row(7))
        self.assertIn("MIXAGE", cpc.row(20))
        self.assertIn("2 MESURES", cpc.row(21))
        self.assertIn("02/64", cpc.row(21))
        self.assertEqual(cpc.attr[4][4], (0, 1))             # curseur : motif en inverse

    def test_preview(self):
        """Aperçu : un ■ pour chaque pas qui a une note (motif 1 de démonstration)."""
        cpc = self.cpc
        self.key(KEY_SONG)
        work = cpc.peek(cpc.word(cpc.addr("seq_pattern")), PAT)
        for step in range(16):
            cells = work[4 + 16 * step:4 + 16 * step + 16]
            on = any(cells[4 * v] < 0xFE for v in range(4))
            self.assertEqual(cpc.codes[4][24 + step], 233 if on else 144, step)

    # --- édition ---------------------------------------------------------------------
    def test_edit_fields(self):
        cpc = self.cpc
        self.key(KEY_SONG)
        self.key(SHIFT, UP)                                   # motif 01 -> 02
        self.assertEqual(self.song()[0][0], (1, 1, 0))
        self.key(RIGHT)
        for _ in range(20):
            self.key(SHIFT, UP)                               # répétitions : 16 au plus
        self.assertEqual(self.song()[0][0][1], 16)
        self.assertIn("x16", cpc.row(5))
        self.key(RIGHT)
        for _ in range(15):
            self.key(SHIFT, DOWN)                             # transposition : -12 au moins
        self.assertEqual(self.song()[0][0][2], 0xF4)
        self.assertIn("-12", cpc.row(5))
        self.assertIn("17 MESURES", cpc.row(21))

    def test_insert_delete_copy_loop(self):
        cpc = self.cpc
        self.key(KEY_SONG)
        self.key(DOWN)
        self.key(DOWN)                                        # FIN
        self.key(RETURN)                                      # ajoute le motif affiché
        self.assertEqual(self.song()[0], [(0, 1, 0), (1, 1, 0), (0, 1, 0)])
        self.assertEqual(self.var("sp_cur"), 3)               # toujours sur FIN
        self.key(UP)
        self.key(KEY_B)                                       # la boucle part de 02
        self.assertEqual(self.song()[1], 2)
        self.assertIn("RETOUR EN 02", cpc.row(8))
        self.key(UP)
        self.key(UP)
        self.key(COPY)                                        # double la position 00
        self.assertEqual(self.song(), ([(0, 1, 0), (0, 1, 0), (1, 1, 0), (0, 1, 0)], 3))
        self.assertEqual(self.var("sp_cur"), 1)
        self.key(DEL)                                         # ôte la copie
        self.assertEqual(self.song(), ([(0, 1, 0), (1, 1, 0), (0, 1, 0)], 2))
        self.key(DOWN)                                        # position 02
        self.key(DEL)                                         # ôte la position de la boucle
        self.assertEqual(self.song(), ([(0, 1, 0), (1, 1, 0)], 1))

    def test_scroll(self):
        cpc = self.cpc
        self.set_song([(i % 2, 1, 0) for i in range(20)])
        self.key(KEY_SONG)
        for _ in range(16):
            self.key(DOWN)
        self.assertEqual(self.var("sp_cur"), 16)
        self.assertEqual(self.var("sp_top"), 3)
        self.assertTrue(cpc.row(5).startswith("03"))
        self.assertTrue(cpc.row(18).startswith("16"))

    def test_mixer(self):
        cpc = self.cpc
        self.key(KEY_SONG)
        for _ in range(3):
            self.key(DOWN)                                    # 00, 01, FIN, puis le mixage
        self.assertEqual(self.var("sp_mix"), 1)
        self.key(RIGHT)                                       # voix B
        master = cpc.addr("smp_blk_src") + 5
        before = cpc.peek(master + 1)[0]
        self.key(SHIFT, DOWN)
        self.assertEqual(cpc.peek(master + 1)[0], before - 1)
        self.assertEqual(cpc.attr[19][16], (0, 1))            # « B » en inverse
        self.key(UP)
        self.assertEqual(self.var("sp_mix"), 0)

    # --- lecture -----------------------------------------------------------------------
    def play_until_pos(self, pos, limit=600):
        for _ in range(limit):
            self.cpc.frames(1)
            if self.var("song_pos") == pos:
                return
        self.fail("la position %d n'arrive pas" % pos)

    def test_play_song(self):
        cpc = self.cpc
        self.set_song([(0, 2, 0), (1, 1, 0), (2, 1, 0)], loop=1)
        self.key(KEY_SONG)
        self.key(SPACE)                                       # depuis la position 00
        self.assertEqual(self.var("song_live"), 1)
        self.assertIn("LECTURE SONG", cpc.row(2))
        self.assertEqual(cpc.codes[4][2], 246)                # ► sur la position jouée
        self.play_until_pos(1)                                # après 2 mesures
        self.assertEqual(self.var("cur_pat"), 1)
        self.assertEqual(cpc.codes[5][2], 246)
        self.play_until_pos(2)
        self.assertEqual(self.var("cur_pat"), 2)
        self.play_until_pos(1)                                # fin : la boucle
        self.key(SPACE)
        self.assertEqual(self.var("seq_playing"), 0)
        self.assertEqual(self.var("song_live"), 0)
        self.assertIn("ARRET", cpc.row(2))

    def test_next_pattern_prepared_in_advance(self):
        """Pendant la dernière répétition, le motif suivant est copié dans
        pat_ahead ; au changement de mesure, aucun échange de bloc."""
        cpc = self.cpc
        self.set_song([(0, 1, 0), (1, 1, 0)])
        self.key(KEY_SONG)
        self.key(SPACE)
        cpc.frames(3)
        self.assertEqual(self.var("next_id"), 1)
        ahead = cpc.word(cpc.addr("seq_pattern")) - PAT          # pat_ahead
        self.assertEqual(cpc.peek(ahead, PAT),
                         cpc.bank_peek(4, 0x4000 + FIXED + PAT, PAT))
        goto, done = cpc.addr("song_goto"), cpc.addr("seq_set_pattern")
        copy = cpc.addr("bank_copy")
        state = {"in": False, "copies": 0, "swaps": 0}
        orig = cpc.step

        def step():
            pc = cpc.m.pc
            if pc == goto:
                state["in"] = True
                state["swaps"] += 1
            elif pc == done:
                state["in"] = False
            elif pc == copy and state["in"]:
                state["copies"] += 1
            orig()
        cpc.step = step
        self.play_until_pos(1)
        cpc.step = orig
        self.assertEqual(self.var("cur_pat"), 1)
        self.assertGreaterEqual(state["swaps"], 1)
        self.assertEqual(state["copies"], 0, "le changement de motif a touché au bloc 4")

    def test_edited_pattern_stored_before_leaving(self):
        cpc = self.cpc
        self.set_song([(0, 1, 0), (1, 1, 0)])
        self.key(KEY_MOTIF)
        self.key(RETURN)                                      # une case change
        work = cpc.word(cpc.addr("seq_pattern"))
        edited = cpc.peek(work, PAT)
        self.assertEqual(self.var("pat_dirty"), 1)
        self.key(KEY_SONG)
        self.key(SPACE)
        self.play_until_pos(1)
        self.assertEqual(cpc.bank_peek(4, 0x4000 + FIXED, PAT), edited)
        self.assertEqual(self.var("pat_dirty"), 0)

    def test_motif_panel_loops(self):
        """Panneau MOTIF : le motif joué boucle, le morceau n'avance pas ; il
        reprend au retour dans SONG."""
        cpc = self.cpc
        self.set_song([(0, 1, 0), (1, 1, 0)])
        self.key(KEY_SONG)
        self.key(SPACE)
        self.key(KEY_MOTIF)
        trig = cpc.addr("seq_trigger")
        bars = []
        orig = cpc.step

        def step():
            if cpc.m.pc == trig and cpc.peek(cpc.addr("seq_step"))[0] == 0:
                bars.append(self.var("cur_pat"))
            orig()
        cpc.step = step
        for _ in range(400):                                  # plus de 3 mesures
            cpc.frames(1)
        cpc.step = orig
        self.assertGreaterEqual(len(bars), 3)
        self.assertEqual(set(bars), {0})                      # toujours le motif 1
        self.assertEqual(self.var("song_pos"), 0)
        self.assertEqual(self.var("seq_playing"), 1)
        self.assertIn("MOTIF:01", cpc.row(2))
        self.key(KEY_SONG)                                    # SONG : ça repart
        self.play_until_pos(1)
        self.assertEqual(self.var("cur_pat"), 1)

    def test_loop_toggle_and_stop_at_end(self):
        """B sur la position de la boucle la retire : FIN « ARRET », et la
        lecture s'arrête à la fin du morceau.  B de nouveau : la boucle."""
        cpc = self.cpc
        self.set_song([(0, 1, 0), (1, 1, 0)], loop=0)
        self.key(KEY_SONG)
        self.key(KEY_B)                                       # curseur sur 00
        self.assertEqual(self.song()[1], 0xFF)
        self.assertIn("FIN : ARRET", cpc.screen_text())
        self.key(SPACE)
        self.play_until_pos(1)
        for _ in range(400):
            cpc.frames(1)
            if not self.var("seq_playing"):
                break
        self.assertEqual(self.var("seq_playing"), 0)
        cpc.frames(2)
        self.assertIn("ARRET", cpc.row(2))
        self.key(KEY_B)
        self.assertEqual(self.song()[1], 0)
        self.assertIn("RETOUR EN 00", cpc.screen_text())

    def test_motif_name_in_status(self):
        """Ligne d'état : le numéro et le nom du motif (celui de son .PAT)."""
        cpc = self.cpc
        self.key(KEY_SONG)
        code = cpc.addr("pat_name_ptr")                       # ld l,a / ld h,0 / 3 x add
        self.assertEqual(cpc.peek(code + 6)[0], 0x11)         # hl,hl / ld de,pat_names
        cpc.poke(cpc.word(code + 7), b"NUINTRO ")             # le nom du motif 1
        self.key(KEY_MOTIF)
        self.assertIn("MOTIF:01 NUINTRO ", cpc.row(2))
        self.assertNotIn("VOIX SEPAREES", cpc.row(2))
        self.assertIn("f8 SAUVER f9 CHARGER", cpc.row(20))

    def test_transposition(self):
        cpc = self.cpc
        for tr, note, want in ((5, 40, 45), (-3, 40, 37), (12, 90, 95), (-12, 5, 0), (0, 7, 7)):
            cpc.poke(cpc.addr("song_transp"), [tr & 0xFF])
            cpc.call("song_trans_b", b=note, c=0x55)
            self.assertEqual((cpc.m.b, cpc.m.c), (want, 0x55), (tr, note))
        cpc.poke(cpc.addr("song_transp"), [0])

    def test_transposed_position_plays_higher(self):
        """Position transposée de +7 : les voix A, B, C jouent une quinte plus
        haut, la voix de bruit ne bouge pas."""
        cpc = self.cpc
        self.set_song([(0, 1, 7)])                            # le motif 1 (voix séparées)
        self.key(KEY_SONG)
        target = cpc.addr("snd_note_on")
        notes = []
        orig = cpc.step

        def step():
            if cpc.m.pc == target:
                notes.append((cpc.m.a, cpc.m.b))
            orig()
        cpc.step = step
        self.key(SPACE)
        cpc.frames(2)
        cpc.step = orig
        work = cpc.peek(cpc.word(cpc.addr("seq_pattern")), PAT)
        first = {v: work[4 + 4 * v] for v in range(4) if work[4 + 4 * v] < 0xFE}
        played = dict(notes[:len(first)])
        self.assertEqual(set(played), set(first))
        for v, n in first.items():
            self.assertEqual(played[v], n if v == 3 else n + 7, v)

    # --- .SNG version 3, noms des motifs ----------------------------------------------
    def test_save_load_v3(self):
        cpc = self.cpc
        self.set_song([(1, 3, 2), (0, 1, 0xFE)], loop=1)
        self.key(KEY_SONG)
        cpc.chars = typed("SUITE")
        self.key(KEY_SAVE)
        data = cpc.saved["SUITE.SNG"]
        n = data[SONG_SIZE3] | data[SONG_SIZE3 + 1] << 8      # version 4 : + la banque
        self.assertEqual(len(data), SONG_SIZE3 + 2 + n)
        self.assertEqual(data[4], 4)
        v3 = data[FIXED + 32 * PAT + 16:]
        self.assertEqual(v3[:8], bytes([2, 1, 1, 3, 2, 0, 1, 0xFE]))
        self.make_disk({"SUITE.SNG": data}, keep=("SEQ16.BIN",))
        self.set_song([(5, 1, 0)])
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertEqual(self.song(), ([(1, 3, 2), (0, 1, 0xFE)], 1))
        self.assertIn("x3", cpc.row(5))
        self.assertIn("+2", cpc.row(5))
        self.assertIn("-2", cpc.row(6))

    def test_load_v2_default_song(self):
        """Un .SNG version 2 : une position par motif qui a des notes."""
        cpc = self.cpc
        self.key(KEY_SONG)
        cpc.chars = typed("V2")
        self.key(KEY_SAVE)
        v2 = bytearray(cpc.saved["V2.SNG"][:FIXED + 32 * PAT + 16])
        v2[4] = 2
        o = FIXED + 5 * PAT                                   # le motif 6 reçoit des notes
        v2[o:o + PAT] = make_pattern(seed=2)
        self.make_disk({"V2.SNG": bytes(v2)}, keep=("SEQ16.BIN",))
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertIn("MORCEAU CHARGE", cpc.row(25))
        self.assertEqual(self.song(), ([(0, 1, 0), (1, 1, 0), (5, 1, 0)], 0))

    def test_pattern_names(self):
        cpc = self.cpc
        names = self.v3 + 2 + 64 * 3
        pat = make_pattern(seed=8)
        self.make_disk({"GROOVE.PAT": pat})
        self.key(KEY_MOTIF)
        self.key(CTRL, RIGHT)                                 # motif 2
        cpc.chars = [13]
        self.key(KEY_LOAD)                                    # f9 : GROOVE.PAT
        self.assertEqual(cpc.peek(names + 8, 8), b"GROOVE  ")
        self.key(CTRL, LEFT)                                  # motif 1, sans nom
        seen = []
        cpc.chars = [lambda: seen.append(cpc.row(25)) or 13]
        self.key(KEY_SAVE)                                    # f8 propose MOTIF-01
        self.assertIn("MOTIF-01", seen[0])
        self.assertIn("MOTIF-01.PAT", cpc.saved)
        self.assertEqual(cpc.peek(cpc.addr("fname"), 8), b"MORCEAU1")   # le morceau garde son nom
        self.key(KEY_SONG)
        self.assertIn("MOTIF-01", cpc.row(5))
        self.assertIn("GROOVE", cpc.row(6))


if __name__ == "__main__":
    unittest.main()
