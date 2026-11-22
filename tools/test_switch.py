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




if cpcsim is not None:
    class SlowTextCPC(RealTimeCPC):
        """Un CPC où écrire un caractère prend du temps, comme le vrai
        firmware : environ 3,5 ms.  Mesuré sur la machine avec le
        chronomètre des pas (PIXEL, panneau SONG : « MESURE 460 MS » avant
        txt_out, exactement ce que donne le simulateur à 3 500 µs)."""
        def fw_TXT_OUTPUT(self):
            self.t += 3500
            super().fw_TXT_OUTPUT()


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class SongTempoTest(unittest.TestCase):
    """Mode morceau : le changement de motif ne retarde plus les pas (le
    tempo suit le temps réel, et le motif suivant est prêt à l'avance)."""

    def steps(self, screen_key):
        cpc = SlowTextCPC.from_build()
        cpc.boot()
        v3 = cpc.addr("smp_blk_src") + 16 + 32 * 16 + 32 * 6 + 8 * 16 + 16
        cpc.poke(v3, bytes([2, 0, 0, 1, 0, 1, 1, 0]))      # motifs 1 et 2, en boucle
        cpc.frames(1, keys={14})                           # SONG
        cpc.frames(1)
        cpc.frames(1, keys={KEY_SPACE})
        cpc.frames(1)
        cpc.frames(1, keys={screen_key})
        cpc.frames(1)
        trig = cpc.addr("seq_trigger")
        times = []
        orig = cpc.step

        def step():
            if cpc.m.pc == trig:
                times.append((cpc.t, cpc.peek(cpc.addr("seq_step"))[0]))
            orig()
        cpc.step = step
        t0 = cpc.t
        while cpc.t - t0 < 6 * 1_000_000:
            cpc.frames(1)
        cpc.step = orig
        return [(b[0] - a[0], b[1] == 0) for a, b in zip(times, times[1:])]

    def test_bar_change_on_time(self):
        for screen_key in (14, 13):                        # SONG, puis MOTIF
            gaps = self.steps(screen_key)
            # 125 BPM : un pas = 6 images (120 ms), à une image près (plus un
            # caractère : le son ne reprend qu'entre deux), même au
            # changement de motif et pendant le dessin qui le suit
            self.assertTrue([g for g, bar in gaps if bar])
            for g, _ in gaps:
                self.assertLessEqual(g, 7 * FRAME + 3500, (screen_key, g))
                self.assertGreaterEqual(g, 5 * FRAME - 3500, (screen_key, g))

    def test_stopwatch_on_stop(self):
        """ESPACE arrête la lecture : la ligne 25 donne le plus court et le
        plus long écart entre deux pas, à part pour les débuts de mesure, en
        millisecondes - les mêmes que ceux mesurés par le simulateur."""
        import re
        cpc = SlowTextCPC.from_build()
        cpc.boot()
        v3 = cpc.addr("smp_blk_src") + 16 + 32 * 16 + 32 * 6 + 8 * 16 + 16
        cpc.poke(v3, bytes([2, 0, 0, 1, 0, 1, 1, 0]))      # motifs 1 et 2, en boucle
        cpc.frames(1, keys={14})                           # SONG
        cpc.frames(1)
        cpc.frames(1, keys={KEY_SPACE})
        cpc.frames(1)
        trig = cpc.addr("seq_trigger")
        times = []
        orig = cpc.step

        def step():
            if cpc.m.pc == trig:
                times.append((cpc.t, cpc.peek(cpc.addr("seq_step"))[0]))
            orig()
        cpc.step = step
        t0 = cpc.t
        while cpc.t - t0 < 5 * 1_000_000:
            cpc.frames(1)
        cpc.step = orig
        cpc.frames(1, keys={KEY_SPACE})                    # arrêt
        cpc.frames(1)
        row = cpc.row(25)
        m = re.match(r"PAS (\d+)-(\d+)  MESURE (\d+)-(\d+) MS", row)
        self.assertTrue(m, row)
        lo, hi, blo, bhi = map(int, m.groups())
        gaps = [((b[0] - a[0]) / 1000, b[1] == 0) for a, b in zip(times, times[1:])]
        steps = [g for g, bar in gaps if not bar]
        bars = [g for g, bar in gaps if bar]
        for shown, real in ((lo, min(steps)), (hi, max(steps)),
                            (blo, min(bars)), (bhi, max(bars))):
            self.assertLessEqual(abs(shown - real), 4, (row, shown, real))

    def test_real_song_bar_change(self):
        """PIXEL (150 BPM, un pas = 100 ms) de la disquette des morceaux,
        panneau SONG, au rythme réel du firmware : sur le CPC, le chronomètre
        donnait « PAS 100-100  MESURE 460-460 MS » (le dessin de la position
        retardait le pas 0).  Il faut des pas réguliers, mesures comprises."""
        import re
        disk = os.path.join(HERE, "..", "build", "seq16-songs.dsk")
        cpc = SlowTextCPC.from_build(disk)
        cpc.boot()
        cpc.frames(1, keys={14})                           # SONG
        cpc.frames(1)
        names = [n for n in cpc.files if n.endswith(".SNG")]
        cpc.chars = [0xF1] * names.index("PIXEL.SNG") + [13]
        cpc.frames(1, keys={3})                            # f9
        cpc.frames(1)
        self.assertIn("SONG:PIXEL", cpc.row(2))
        cpc.frames(1, keys={KEY_SPACE})
        cpc.frames(1)
        t0 = cpc.t
        while cpc.t - t0 < 12 * 1_000_000:                 # 7 mesures
            cpc.frames(1)
        cpc.frames(1, keys={KEY_SPACE})
        cpc.frames(1)
        m = re.match(r"PAS (\d+)-(\d+)  MESURE (\d+)-(\d+) MS", cpc.row(25))
        self.assertTrue(m, cpc.row(25))
        for v in map(int, m.groups()):
            self.assertLessEqual(abs(v - 100), 24, cpc.row(25))


if __name__ == "__main__":
    unittest.main()
