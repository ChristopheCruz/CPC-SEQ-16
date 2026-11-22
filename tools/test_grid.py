"""Tests du panneau MOTIF (lot 3 du plan) : une case par pas, panneau de la
note en haut, pinceau, ENTER, COPY, TAB, piano.

On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py).
Lancement :  python -m unittest tools.test_grid   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402

cpcsim = test_player.cpcsim
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 8
RETURN, COPY, TAB, CLR, DEL, CAPS, SPACE, MODE = 18, 9, 68, 16, 79, 70, 47, 4
SHIFT = 21
PIANO_C = 71                              # 1re touche du piano (DO)
ON, FULL, DOT, HOLD, OFF, MARK = 233, 143, 144, 154, 203, 247
NONE, NOTE_OFF = 0xFF, 0xFE


def col(step):
    """Colonne (1 à 40) du 1er caractère de la case du pas."""
    return 6 + 2 * step + step // 4


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class GridTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cpc = cpcsim.CPC.from_build()
        cpc.boot()
        test_player.demo_song(cpc)               # contenu connu (pas SYNTH)
        cls.base = cpc

    def setUp(self):
        self.cpc = test_player.PlayerTest._clone(self.base)

    def key(self, *keys):
        self.cpc.frames(1, keys=set(keys))
        self.cpc.frames(1)

    def code(self, row, column):
        return self.cpc.codes[row - 1][column - 1]

    def attr(self, row, column):
        return self.cpc.attr[row - 1][column - 1]

    def cell(self, lane, step):
        p = self.cpc.word(self.cpc.addr("seq_pattern")) + 4 + 16 * step + 4 * lane
        return list(self.cpc.peek(p, 4))

    def set_cell(self, lane, step, data):
        p = self.cpc.word(self.cpc.addr("seq_pattern")) + 4 + 16 * step + 4 * lane
        self.cpc.poke(p, bytes(data))

    def var(self, name):
        return self.cpc.peek(self.cpc.addr(name))[0]

    def goto(self, lane, step):
        for _ in range(self.var("cur_l")):
            self.key(UP)
        for _ in range(lane):
            self.key(DOWN)
        while self.var("cur_s") != step:
            self.key(RIGHT)

    # --- la grille -------------------------------------------------------------
    def test_layout(self):
        cpc = self.cpc
        self.assertEqual(cpc.row(10).rstrip(), "PAS  0 1 2 3  4 5 6 7  8 9 A B  C D E F")
        self.assertIn("PAS 0", cpc.row(4))
        self.assertIn("VOIX A", cpc.row(4))
        self.assertIn("NOTE:C 2   INS:02 BASS", cpc.row(7))
        self.assertTrue(cpc.row(19).startswith("PINCEAU"))
        self.assertEqual([cpc.row(r)[1] for r in (11, 13, 15, 17)], list("ABCN"))
        for r in (12, 14, 16, 18):
            self.assertEqual(cpc.row(r).strip(), "")

    def test_cells(self):
        """Motif de démonstration, voix A : note, arrêt, vide, note tenue."""
        self.goto(1, 0)                           # curseur ailleurs
        r = 11
        self.assertEqual(self.code(r, col(0)), ON)
        self.assertEqual(self.code(r, col(0) + 1), HOLD)      # tenue jusqu'à
        self.assertEqual(self.code(r, col(1)), OFF)           # son arrêt
        self.assertEqual(self.code(r, col(2)), DOT)
        self.assertEqual(self.attr(r, col(4))[0], 3)          # arrêt : orange
        self.assertEqual((self.code(15, col(0)), self.attr(15, col(0))[0]), (DOT, 1))  # vide sur un temps : jaune
        self.assertEqual((self.code(15, col(1)), self.attr(15, col(1))[0]), (DOT, 2))  # ailleurs : cyan
        self.assertEqual(self.code(r, col(3) + 1), HOLD)
        self.assertEqual(self.code(r, col(3) + 2), HOLD)      # colonne entre deux temps
        self.assertEqual(self.attr(17, col(0))[0], 3)         # bruit : orange

    def test_cursor_crosshair(self):
        cpc = self.cpc
        self.goto(1, 3)
        self.assertEqual(self.code(13, col(3)), ON)
        self.assertEqual(self.attr(13, col(3))[0], 1)          # case en jaune
        self.assertEqual(self.code(13, col(3) + 1), MARK)      # ◄
        self.assertEqual(self.attr(10, col(3)), (0, 1))        # numéro en inverse
        self.assertEqual(self.attr(13, 2), (0, 1))             # lettre en inverse
        self.assertEqual(self.attr(11, 2), (1, 0))             # les autres normales
        self.assertIn("PAS 3", cpc.row(4))
        self.assertIn("VOIX B", cpc.row(4))
        self.assertIn("NOTE:G 4", cpc.row(7))

    def test_keyboard_highlight(self):
        """G4 avec l'octave de saisie 3 : la blanche G de la 2e octave."""
        self.goto(1, 3)
        g2 = 3 + 2 * (7 + 4)                       # colonne de la lettre G (2e octave)
        self.assertEqual(self.code(6, g2), ord("G"))
        self.assertEqual(self.attr(6, g2)[1], 1)   # fond jaune
        self.assertEqual(self.attr(6, 3)[1], 2)    # les autres : cyan
        self.goto(1, 6)                            # A#4 : une noire
        a_sharp = 3 + 2 * (7 + 5) + 1
        self.assertEqual(self.code(5, a_sharp), FULL)
        self.assertEqual(self.attr(5, a_sharp)[0], 1)

    # --- ENTER, COPY ---------------------------------------------------------------
    def test_enter_toggles_with_brush(self):
        self.goto(1, 4)                            # vide
        self.assertEqual(self.cell(1, 4)[0], NONE)
        self.key(RETURN)
        brush = self.var("brush_note")
        self.assertEqual(self.cell(1, 4), [brush, self.var("cur_inst"), 0xFF, 0])
        self.assertEqual(self.code(13, col(4)), ON)
        self.key(RETURN)                           # éteint
        self.assertEqual(self.cell(1, 4)[0], NONE)
        self.assertEqual(self.code(13, col(4)), DOT)

    def test_enter_noise_lane(self):
        self.goto(3, 1)
        self.key(RETURN)
        self.assertEqual(self.cell(3, 1)[0], self.var("brush_noise"))

    def test_copy_picks_brush(self):
        cpc = self.cpc
        self.goto(1, 3)                            # G4, instrument 01 LEAD
        self.key(COPY)
        self.assertEqual(self.var("brush_note"), self.cell(1, 3)[0])
        self.assertEqual(self.var("cur_inst"), self.cell(1, 3)[1])
        self.assertIn("G 4", cpc.row(19))
        self.goto(1, 4)
        self.key(RETURN)
        self.assertEqual(self.cell(1, 4)[:2], self.cell(1, 3)[:2])

    def test_piano_note_brush_and_advance(self):
        self.goto(0, 2)
        self.key(PIANO_C)
        note = 12 * self.var("cur_oct")
        self.assertEqual(self.cell(0, 2)[0], note)
        self.assertEqual(self.var("brush_note"), note)
        self.assertEqual(self.var("cur_s"), 3)     # le curseur a avancé

    # --- CLR, DEL ------------------------------------------------------------------
    def test_clr_draws_hold_line(self):
        self.goto(2, 3)                            # voix C : note en 2, vide en 3
        self.goto(2, 4)
        self.key(CLR)                              # arrêt en 4
        self.assertEqual(self.cell(2, 4)[0], NOTE_OFF)
        self.assertEqual(self.var("cur_s"), 5)
        self.assertEqual(self.code(15, col(2) + 1), HOLD)     # la note du pas 2
        self.assertEqual(self.code(15, col(3)), HOLD)         # tient jusqu'en 4
        self.assertEqual(self.code(15, col(4)), OFF)

    # --- TAB : modifier la note ------------------------------------------------------
    def test_tab_edit_fields(self):
        cpc = self.cpc
        self.goto(1, 3)
        before = self.cell(1, 3)
        self.key(TAB)
        self.assertIn("EDITION", cpc.row(4))
        self.key(UP)                               # NOTE + 1
        self.assertEqual(self.cell(1, 3)[0], before[0] + 1)
        self.assertEqual(self.var("cur_s"), 3)     # le curseur ne bouge pas
        self.key(RIGHT)                            # champ INS
        self.key(UP)
        self.assertEqual(self.cell(1, 3)[1], before[1] + 1)
        self.key(RIGHT)                            # champ VOL : - -> 0 -> 1
        self.key(UP)
        self.key(UP)
        self.assertEqual(self.cell(1, 3)[2], 1)
        self.assertIn("VOL:1", cpc.row(7))
        self.key(DOWN)
        self.key(DOWN)
        self.assertEqual(self.cell(1, 3)[2], 0xFF)
        self.assertIn("VOL:-", cpc.row(7))
        self.key(TAB)
        self.assertNotIn("EDITION", cpc.row(4))
        self.key(RIGHT)                            # les flèches déplacent à nouveau
        self.assertEqual(self.var("cur_s"), 4)

    def test_tab_edit_empty_cell(self):
        self.goto(1, 4)
        self.key(TAB)
        self.key(UP)
        self.assertEqual(self.cell(1, 4)[0], NONE)

    # --- lecture -------------------------------------------------------------------
    def test_playing_step_lights_up(self):
        cpc = self.cpc
        self.goto(1, 15)
        self.key(SPACE)
        for _ in range(40):
            cpc.frames(1)
            pos = self.var("shown_pos")
            if pos != 0xFF and self.cell(2, pos)[0] < NOTE_OFF:
                break
        self.assertEqual(self.code(15, col(pos)), FULL)       # la note jouée s'allume
        self.assertEqual(self.attr(10, col(pos)), (0, 3))     # son numéro en orange
        self.key(SPACE)
        self.assertEqual(self.var("shown_pos"), 0xFF)
        self.assertEqual(self.code(15, col(pos)), ON)

    # --- son composé, verrou ---------------------------------------------------------
    def test_layered(self):
        cpc = self.cpc
        self.key(MODE)
        self.assertIn("SON COMPOSE", cpc.row(4))            # titre du cadre
        self.assertIn("SON", cpc.row(11)[:5])
        self.assertIn("COUCHES DU SON S", cpc.row(13))
        self.assertEqual([cpc.row(r)[3] for r in (15, 16, 17, 18)], list("ABCN"))
        self.assertIn("SON:S", cpc.row(19))
        self.key(MODE)
        self.assertEqual(cpc.row(13)[1], "B")      # retour : la voix B revient
        self.assertEqual(cpc.row(14).strip(), "")

    def test_caps_lock_shown(self):
        cpc = self.cpc
        self.key(CAPS)
        self.assertIn("VERROU", cpc.row(19))
        self.key(CAPS)
        self.assertNotIn("VERROU", cpc.row(19))


if __name__ == "__main__":
    unittest.main()
