"""Changer de motif pendant la lecture (f1, CTRL + gauche/droite).

La lecture ne s'arrête plus, et le son continue pendant que la grille est
redessinée (environ 5 images) : snd_tick joue les tours de son en retard.
Lancement :  python -m unittest tools.test_switch   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402

cpcsim = test_player.cpcsim
KEY_SPACE, KEY_CTRL, KEY_RIGHT, KEY_LEFT = 47, 23, 1, 8
FRAME = 20_000                            # une image de 50 Hz, en µs


if cpcsim is not None:
    class RealTimeCPC(cpcsim.CPC):
        """Le temps d'un vrai CPC : l'attente du balayage dure jusqu'au top
        suivant de 20 ms (dans le simulateur de base, elle ne prend rien)."""
        def fw_MC_WAIT_FLYBACK(self):
            self.frame += 1
            self.t = (self.t // FRAME + 1) * FRAME


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class SwitchTest(unittest.TestCase):
    def setUp(self):
        self.cpc = RealTimeCPC.from_build()
        self.cpc.boot()
        self.cpc.frames(1, keys={KEY_SPACE})      # lecture du motif 1
        self.cpc.frames(20)

    def peek(self, name):
        return self.cpc.peek(self.cpc.addr(name))[0]

    def switch(self, key):
        """Un appui de CTRL + flèche ; renvoie les écritures de l'AY pendant
        le tour de boucle où la grille est redessinée."""
        n = len(self.cpc.ay_writes)
        t0 = self.cpc.t
        self.cpc.frames(1, keys={KEY_CTRL, key})
        return [w for w in self.cpc.ay_writes[n:] if w[0] >= t0], self.cpc.t - t0

    def test_playback_continues(self):
        self.assertEqual(self.peek("seq_playing"), 1)
        self.switch(KEY_RIGHT)
        self.assertEqual(self.peek("cur_pat"), 1)
        self.assertEqual(self.peek("seq_playing"), 1)
        self.assertIn("PLAY", self.cpc.screen_text().replace("LECTURE", "PLAY"))
        self.switch(KEY_LEFT)                     # retour au motif 1, toujours en lecture
        self.assertEqual(self.peek("cur_pat"), 0)
        self.assertEqual(self.peek("seq_playing"), 1)

    def test_sound_keeps_running_while_redrawing(self):
        writes, duration = self.switch(KEY_RIGHT)
        self.assertGreater(duration, 3 * FRAME)   # le dessin dure plusieurs images
        frames = {t // FRAME for t, _, _ in writes}
        # au moins un tour de son par image écoulée (à une près)
        self.assertGreaterEqual(len(frames), duration // FRAME - 1)

    def test_tempo_kept_across_switch(self):
        """Le séquenceur avance au même rythme avec ou sans changement :
        snd_tick rattrape les images passées à dessiner."""
        cpc = self.cpc
        step0 = self.peek("seq_step")
        t0 = cpc.t
        self.switch(KEY_RIGHT)
        self.switch(KEY_LEFT)
        while cpc.t - t0 < 50 * FRAME:            # une seconde en tout
            cpc.frames(1)
        steps = (self.peek("seq_step") - step0) % 16
        # 125 BPM, 4 pas par temps : 8,3 pas par seconde
        self.assertIn(steps, (7, 8, 9))


if __name__ == "__main__":
    unittest.main()
