"""Tests des effets des pas (FX), src/sound.asm et src/grid.asm.

L'octet FX d'une case : chiffre haut = l'effet, chiffre bas = sa force x.
    1x MONTE    2x DESCEND  3x ARPEGE  4x REPETE
    5x COUPE    6x RETARD   7x VIBRATO
On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py) :
une note jouée par snd_note_on, puis snd_frame image par image.
Lancement :  python -m unittest tools.test_fx   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402
from test_patterns import make_pattern  # noqa: E402,F401

cpcsim = test_player.cpcsim
CH_PHASE, CH_LEVEL, CH_OUT, CH_TIME, CH_PERL, CH_FX = 3, 4, 5, 6, 12, 15
LEAD = 0                                   # attaque immédiate, sans arpège ni vibrato
NOTE = 48
KEY_TAB, KEY_RIGHT, KEY_UP, KEY_DOWN, KEY_SPACE = 68, 1, 0, 2, 47
MSG = 25


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class FxEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cpc = cpcsim.CPC.from_build()
        cpc.boot()
        cls.base = cpc

    def setUp(self):
        self.cpc = test_player.PlayerTest._clone(self.base)
        self.cpc.call("snd_init")

    def ch(self, voice, field):
        return self.cpc.peek(self.cpc.addr("channels") + 16 * voice + field)[0]

    def period(self, voice=0):
        a = self.cpc.addr("channels") + 16 * voice + CH_PERL
        return self.cpc.word(a)

    def note_period(self, n):
        return self.cpc.word(self.cpc.addr("note_periods") + 2 * n)

    def play(self, fx, frames, voice=0, note=NOTE, ins=LEAD):
        """Note avec l'effet fx ; renvoie, image par image, (période, niveau,
        phase, volume envoyé)."""
        cpc = self.cpc
        cpc.poke(cpc.addr("sno_fx"), [fx])
        cpc.call("snd_note_on", a=voice, b=note, c=ins)
        out = []
        for _ in range(frames):
            cpc.call("snd_frame")
            out.append((self.period(voice), self.ch(voice, CH_LEVEL),
                        self.ch(voice, CH_PHASE), self.ch(voice, CH_OUT)))
        return out

    def test_no_effect(self):
        rows = self.play(0, 10)
        self.assertEqual({p for p, *_ in rows}, {self.note_period(NOTE)})
        self.assertEqual(self.ch(0, CH_FX), 0)

    def test_up_and_down(self):
        base = self.note_period(NOTE)
        rows = self.play(0x14, 6)                        # MONTE, force 4
        self.assertEqual([p for p, *_ in rows], [base - 16 * k for k in range(6)])
        self.cpc.call("snd_init")
        rows = self.play(0x22, 6)                        # DESCEND, force 2
        self.assertEqual([p for p, *_ in rows], [base + 8 * k for k in range(6)])

    def test_arpeggio(self):
        rows = self.play(0x37, 8)                        # la note, puis + 7
        a, b = self.note_period(NOTE), self.note_period(NOTE + 7)
        # âge 1 à 8 : bit 1 de l'âge -> 2 images sur la note, 2 sur la quinte
        self.assertEqual([p for p, *_ in rows], [a, b, b, a, a, b, b, a])

    def test_repeat(self):
        rows = self.play(0x43, 9)                        # toutes les 3 images
        phases = [ph for _, _, ph, _ in rows]
        levels = [lv for _, lv, _, _ in rows]
        # l'attaque (2 images pour LEAD) repart aux âges 3, 6, 9 ; entre deux,
        # le déclin commence
        self.assertEqual(phases, [1, 2, 1, 2, 2, 1, 2, 2, 1], levels)
        self.assertEqual(levels[4], 247)
        self.assertEqual(levels[7], 247)

    def test_cut(self):
        rows = self.play(0x52, 5)                        # relâchée à 2 images
        self.assertEqual([ph for _, _, ph, _ in rows][:3], [1, 4, 4])

    def test_delay(self):
        rows = self.play(0x63, 6)                        # part à 3 images
        self.assertEqual([ph for _, _, ph, _ in rows][:3], [5, 5, 1])
        self.assertEqual([out for *_, out in rows][:2], [0, 0])
        self.assertGreater(rows[2][3], 0)                # l'âge 3 : on l'entend

    def test_delay_on_noise_voice(self):
        """La voix de bruit n'a pas de calcul de hauteur : son âge avance
        quand même (dans l'enveloppe), sinon RETARD attendrait toujours."""
        rows = self.play(0x62, 4, voice=3, note=5, ins=5)   # HAT
        self.assertEqual(rows[0][2], 5)                  # âge 1 : attend
        self.assertIn(rows[1][2], (1, 2))                # âge 2 : part
        self.assertGreater(self.ch(3, CH_TIME), 2)

    def test_vibrato(self):
        rows = self.play(0x73, 40)                       # LEAD n'a pas de vibrato
        periods = {p for p, *_ in rows}
        self.assertGreater(len(periods), 3)
        base = self.note_period(NOTE)
        self.assertLess(max(abs(p - base) for p in periods), base // 8)

    def test_other_notes_have_no_effect(self):
        """sno_fx ne vaut que pour la note du pas : le séquenceur le remet à 0
        après chaque pas (le piano, l'écoute d'une case : sans effet)."""
        cpc = self.cpc = test_player.PlayerTest._clone(self.base)
        pat = cpc.word(cpc.addr("seq_pattern"))
        cpc.poke(pat + 4 + 3, [0x52])                    # pas 0, voix A : COUPE 2
        cpc.frames(1, keys={KEY_SPACE})
        cpc.frames(2)
        self.assertEqual(self.ch(0, CH_FX), 0x52)
        self.assertEqual(cpc.peek(cpc.addr("sno_fx"))[0], 0)

    def test_layered_sound_gets_effect_on_all_voices(self):
        cpc = self.cpc = test_player.PlayerTest._clone(self.base)
        pat = cpc.word(cpc.addr("seq_pattern"))
        cell = bytes([NOTE, 0, 0xFF, 0x37])              # son S1, ARPEGE 7
        cpc.poke(pat, [1])                               # mode son composé
        cpc.poke(pat + 4, cell)
        cpc.frames(1, keys={KEY_SPACE})
        cpc.frames(2)
        for v in range(3):                               # S1 : A, B, C
            self.assertEqual(self.ch(v, CH_FX), 0x37, v)


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class FxEditTest(unittest.TestCase):
    """TAB : le panneau du pas ; ← → : NOTE, INS, VOL, puis les deux chiffres
    du FX (l'effet, sa force) ; ↑ ↓ : la valeur ; le nom de l'effet sur la
    ligne des messages."""

    def setUp(self):
        cpc = cpcsim.CPC.from_build()
        cpc.boot()
        self.cpc = cpc

    def key(self, *keys):
        self.cpc.frames(1, keys=set(keys))
        self.cpc.frames(1)

    def cell_fx(self):
        cpc = self.cpc
        return cpc.peek(cpc.word(cpc.addr("seq_pattern")) + 4 + 3)[0]

    def test_edit_effect_and_strength(self):
        cpc = self.cpc
        self.assertIn("FX:--", cpc.row(7))
        self.key(KEY_TAB)
        for _ in range(3):
            self.key(KEY_RIGHT)                          # NOTE -> INS -> VOL -> FX
        self.assertEqual(cpc.peek(cpc.addr("grid_field"))[0], 3)
        self.key(KEY_UP)                                 # effet 1 : MONTE
        self.assertEqual(self.cell_fx(), 0x10)
        self.assertIn("MONTE", cpc.row(MSG))
        self.assertIn("FX:10", cpc.row(7))
        col = cpc.row(7).index("FX:") + 3
        self.assertEqual(cpc.attr[6][col], (0, 1))       # le chiffre de l'effet
        for _ in range(5):
            self.key(KEY_UP)                             # jusqu'à 7 : VIBRATO
        self.assertEqual(self.cell_fx(), 0x60)
        self.key(KEY_UP)
        self.assertIn("VIBRATO", cpc.row(MSG))
        self.key(KEY_UP)                                 # pas plus de 7
        self.assertEqual(self.cell_fx(), 0x70)
        self.key(KEY_RIGHT)                              # la force
        self.assertEqual(cpc.attr[6][col + 1], (0, 1))
        for _ in range(3):
            self.key(KEY_UP)
        self.assertEqual(self.cell_fx(), 0x73)
        self.assertIn("FX:73", cpc.row(7))
        self.key(KEY_RIGHT)                              # (dernier champ)
        self.assertEqual(cpc.peek(cpc.addr("grid_field"))[0], 4)
        for _ in range(20):
            self.key(KEY_DOWN)
        self.assertEqual(self.cell_fx(), 0x70)           # force 0 au plus bas
        cpc.frames(1, keys={8})                          # gauche : l'effet
        cpc.frames(1)
        for _ in range(7):
            self.key(KEY_DOWN)
        self.assertEqual(self.cell_fx(), 0)              # plus d'effet
        self.assertIn("SANS EFFET", cpc.row(MSG))
        self.assertIn("FX:--", cpc.row(7))


if __name__ == "__main__":
    unittest.main()
