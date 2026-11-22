"""Tests de l'éditeur de banques : smp_model.py (sans écran) et smp_gui.py.

Lancer :  python -m unittest tools.test_smp_gui
     ou :  python tools/test_smp_gui.py

Les tests de l'interface sont sautés s'il n'y a pas d'écran (ou pas de Tk).
La disquette build/seq16-fr.dsk n'est jamais modifiée : on travaille sur une copie.
"""
import math
import os
import shutil
import struct
import sys
import tempfile
import unittest
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import amsdsk      # noqa: E402
import smp_model   # noqa: E402
import wav2smp     # noqa: E402
from smp_model import BankError, BankModel  # noqa: E402
from cpc_dsk import i18n  # noqa: E402

# L'éditeur (dans CPC DISK) suit la langue du système : ces tests
# vérifient les textes français.
i18n.set_language("fr")

ROOT = os.path.join(HERE, "..")


def read(path):
    """Contenu d'un fichier (fermé aussitôt)."""
    with open(path, "rb") as f:
        return f.read()


def sine(freq, seconds, rate=22050, amp=0.7):
    """Sinus de test (liste de flottants)."""
    return [amp * math.sin(2 * math.pi * freq * i / rate) for i in range(int(seconds * rate))]


class ModelBase(unittest.TestCase):
    """Dossier temporaire avec deux WAV de synthèse."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.wav = os.path.join(self.tmp, "kick drum.wav")      # nom à nettoyer
        # silence + sinus + silence : pour vérifier --trim
        wav2smp.write_wav(self.wav, [0.0] * 2000 + sine(220, 0.4) + [0.0] * 3000, 22050)
        self.wav2 = os.path.join(self.tmp, "boucle.wav")
        wav2smp.write_wav(self.wav2, sine(110, 1.0, rate=16000), 16000)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def cli_bank(self, *args):
        """Banque produite par la ligne de commande wav2smp (référence)."""
        out = os.path.join(self.tmp, "CLI.SMP")
        wav2smp.main(list(args) + ["--no-preview", "-o", out])
        return read(out)


class TestModel(ModelBase):
    def test_add_settings_build_parse(self):
        """WAV ajouté, réglages changés, banque relue : noms, code, drapeaux, taille."""
        m = BankModel()
        i = m.add_wav(self.wav)
        self.assertEqual(m.items[i].name, "KICKDR")             # clean_name, 6 car.
        self.assertEqual(m.items[i].code, 125)                  # 8 000 Hz par défaut
        m.update(i, name="bd 1", rate=6250, bits=3, decim=2, curve=2,
                 drive=2.0, trim=True, dither="noise")
        j = m.add_wav(self.wav2, name="loop")
        m.update(j, code=100, curve=0)
        raw = m.build()
        bank = wav2smp.parse_bank(raw)
        self.assertEqual([s.name for s in bank], ["BD1", "LOOP"])
        a, b = bank
        self.assertEqual(a.code, 160)                           # 1 000 000 / 6250
        self.assertEqual((a.decim, a.bits), (2, 3))
        self.assertEqual(a.flags, 2 << 4)                       # courbe saturée
        self.assertEqual(a.loop, wav2smp.NO_LOOP)
        self.assertTrue(all(c & 1 == 0 for c in wav2smp.unpack(a.data)))  # 3 bits
        # trim : 0,4 s de son utile à 6 250 Hz -> 2 500 échantillons
        self.assertAlmostEqual(len(a.data), 1250, delta=2)
        self.assertEqual((b.code, b.flags, b.bits, b.decim), (100, 0, 4, 1))
        self.assertEqual(len(b.data), 5000)                     # 1 s à 10 kHz
        self.assertEqual(wav2smp.data_size(raw), len(a.data) + len(b.data))
        self.assertEqual(m.used_bytes(), len(a.data) + len(b.data))
        self.assertTrue(m.fits())

    def test_same_bytes_as_cli(self):
        """Mêmes réglages -> banque identique à celle de wav2smp (4 bits)."""
        m = BankModel()
        m.add_wav(self.wav, rate=6250, drive=1.5, trim=True, clean=True,
                  dither="noise", decim=3)
        self.assertEqual(m.build(), self.cli_bank(
            self.wav, "--rate", "6250", "--drive", "1.5", "--trim", "--clean",
            "--dither", "noise", "--decim", "3"))

    def test_bits_written_in_entry(self):
        """--bits : mêmes données que wav2smp, mais la fiche dit aussi les bits."""
        m = BankModel()
        m.add_wav(self.wav, bits=2)
        raw, cli = m.build(), self.cli_bank(self.wav, "--bits", "2")
        self.assertEqual(wav2smp.parse_bank(raw)[0].data, wav2smp.parse_bank(cli)[0].data)
        self.assertEqual(raw[16 + 15] >> 3 & 3, 2)              # 2 bits dans la fiche
        self.assertEqual(cli[16 + 15] >> 3 & 3, 0)              # wav2smp : « 4 bits »
        self.assertEqual(raw[:31] + raw[32:], cli[:31] + cli[32:])  # seul écart

    def test_slices_like_cli(self):
        """Découpage en 4 : mêmes noms et mêmes données que --slice 4."""
        m = BankModel()
        m.add_wav(self.wav2)
        first = m.set_slices(0, 4)
        self.assertEqual(first, 0)
        self.assertEqual([it.name for it in m.items], ["BOUC00", "BOUC01", "BOUC02", "BOUC03"])
        self.assertEqual(m.build(), self.cli_bank(self.wav2, "--slice", "4"))
        m.set_slices(2, 1)                                      # regroupe
        self.assertEqual([it.name for it in m.items], ["BOUCLE"])
        with self.assertRaises(BankError):
            m.set_slices(0, 17)

    def test_header_only_change_keeps_data(self):
        """Décimation et courbe ne reconvertissent pas ; la fréquence si."""
        m = BankModel()
        m.add_wav(self.wav)
        data = m.items[0].data
        m.update(0, decim=8, curve=4)
        self.assertIs(m.items[0].data, data)
        m.update(0, rate=4000)
        self.assertEqual(m.items[0].code, 250)
        self.assertLess(len(m.items[0].data), len(data))

    def test_reopened_bank_is_header_only(self):
        """Banque relue : pas de WAV ; seuls les réglages de fiche bougent."""
        src = BankModel()
        src.add_wav(self.wav, bits=2)
        path = os.path.join(self.tmp, "A.SMP")
        src.save(path)
        m = BankModel()
        m.open_bank(path)
        it = m.items[0]
        self.assertFalse(it.has_source)
        self.assertIsNone(m.original(0))
        self.assertIsNone(m.original_wav(0))
        self.assertEqual(it.bits, 2)
        data = it.data
        m.update(0, name="neuf", code=200, bits=4, decim=6, curve=3,
                 drive=1.0, trim=False)                         # valeurs inchangées : permis
        self.assertEqual(it.data, data)                         # données intactes
        with self.assertRaises(BankError):
            m.update(0, drive=3.0)
        with self.assertRaises(BankError):
            m.set_slices(0, 2)
        back = wav2smp.parse_bank(m.build())[0]
        self.assertEqual((back.name, back.code, back.bits, back.decim, back.flags >> 4),
                         ("NEUF", 200, 4, 6, 3))

    def test_reopen_factory_bank_unchanged(self):
        """Ouvrir puis réécrire DRUMS.SMP donne le même fichier."""
        path = os.path.join(ROOT, "samples", "DRUMS.SMP")
        m = BankModel()
        m.open_bank(path)
        self.assertEqual(m.build(), read(path))
        self.assertFalse(m.dirty)

    def test_over_limit_refused(self):
        """Au-delà de 16 064 octets : save et add_to_dsk refusent, rien n'est écrit."""
        long_wav = os.path.join(self.tmp, "long.wav")
        wav2smp.write_wav(long_wav, sine(300, 4.5, rate=8000), 8000)   # 18 000 oct.
        m = BankModel()
        m.add_wav(long_wav)
        self.assertGreater(m.used_bytes(), wav2smp.BANK_MAX_MAIN)
        self.assertFalse(m.fits())
        out = os.path.join(self.tmp, "TROP.SMP")
        with self.assertRaises(BankError) as cm:
            m.save(out)
        self.assertIn("16064", cm.exception.args[0].replace(" ", ""))
        self.assertFalse(os.path.exists(out))
        dsk = os.path.join(self.tmp, "t.dsk")
        shutil.copy(os.path.join(ROOT, "build", "seq16-fr.dsk"), dsk)
        before = read(dsk)
        with self.assertRaises(BankError):
            m.add_to_dsk(dsk, "TROP.SMP")
        self.assertEqual(read(dsk), before)
        m.update(0, rate=10000)                                 # 4,5 s à 10 kHz : encore trop
        self.assertFalse(m.fits())
        m.update(0, rate=4000)                                  # 9 000 octets : tient
        self.assertTrue(m.fits())
        m.save(out)
        self.assertTrue(os.path.exists(out))

    def test_limits_and_errors(self):
        """16 samples au plus, banque vide refusée, réglages invalides refusés."""
        m = BankModel()
        with self.assertRaises(BankError):
            m.build()
        self.assertEqual(m.used_bytes(), 0)
        for _ in range(16):
            m.add_wav(self.wav)
        with self.assertRaises(BankError):
            m.add_wav(self.wav)
        self.assertEqual(len(m), 16)
        for bad in (dict(bits=5), dict(decim=5), dict(curve=9), dict(code=61),
                    dict(rate=20000), dict(dither="x"), dict(volume=3)):
            with self.assertRaises(BankError, msg=bad):
                m.update(0, **bad)
        self.assertEqual(m.items[0].code, 125)                  # rien n'a bougé
        with self.assertRaises(BankError):
            m.add_wav(os.path.join(self.tmp, "absent.wav"))
        notsmp = os.path.join(self.tmp, "x.smp")
        with open(notsmp, "wb") as f:
            f.write(b"pas une banque")
        with self.assertRaises(BankError):
            m.open_bank(notsmp)

    def test_move_remove(self):
        m = BankModel()
        m.add_wav(self.wav, name="A")
        m.add_wav(self.wav, name="B")
        m.add_wav(self.wav, name="C")
        self.assertEqual(m.move(2, -1), 1)
        self.assertEqual([it.name for it in m.items], ["A", "C", "B"])
        self.assertEqual(m.move(0, -1), 0)                      # déjà en tête
        m.remove(0)
        self.assertEqual([it.name for it in m.items], ["C", "B"])

    def test_preview_wavs(self):
        """WAV d'écoute en mémoire : bonne fréquence, bonne longueur."""
        m = BankModel()
        m.add_wav(self.wav, rate=8000)
        import io
        with wave.open(io.BytesIO(m.rendered_wav(0))) as w:
            self.assertEqual(w.getframerate(), 8000)
            self.assertEqual(w.getnframes(), 2 * len(m.items[0].data))
        with wave.open(io.BytesIO(m.original_wav(0))) as w:
            self.assertEqual(w.getframerate(), 22050)
        sig, rate = m.rendered(0)
        codes = wav2smp.unpack(m.items[0].data)
        self.assertEqual(sig, wav2smp.render(codes, 1, 4, wav2smp.CURVE_LOG))

    def test_dsk_name(self):
        self.assertEqual(smp_model.dsk_name("/x/ma banque.smp"), "MABANQUE.SMP")
        self.assertEqual(smp_model.dsk_name("TRES_LONG_NOM.SMP"), "TRESLONG.SMP")
        self.assertEqual(smp_model.dsk_name("voix"), "VOIX.SMP")
        self.assertEqual(smp_model.dsk_name("é.smp"), "BANQUE.SMP")


class TestDsk(ModelBase):
    def setUp(self):
        super().setUp()
        self.real = os.path.join(ROOT, "build", "seq16-fr.dsk")
        self.dsk = os.path.join(self.tmp, "copie.dsk")
        shutil.copy(self.real, self.dsk)
        self.real_before = read(self.real)

    def tearDown(self):
        # La vraie disquette ne doit jamais bouger
        self.assertEqual(read(self.real), self.real_before)
        super().tearDown()

    def test_add_to_copy(self):
        """Ajout puis remplacement sur une copie de build/seq16-fr.dsk."""
        m = BankModel()
        m.add_wav(self.wav)
        name = smp_model.dsk_name("mes sons.smp")
        self.assertFalse(m.dsk_has(self.dsk, name))
        self.assertEqual(m.add_to_dsk(self.dsk, name), "MESSONS.SMP")
        self.assertTrue(m.dsk_has(self.dsk, name))
        self.assertEqual(amsdsk.read_file(self.dsk, name), m.build())
        m.update(0, rate=5000)                                  # remplace
        m.add_to_dsk(self.dsk, name)
        self.assertEqual(amsdsk.read_file(self.dsk, name), m.build())
        files = amsdsk.list_files(self.dsk)
        self.assertEqual(list(files).count("MESSONS.SMP"), 1)
        self.assertIn("SEQ16.BIN", files)
        self.assertEqual(amsdsk.read_file(self.dsk, "SEQ16.BIN"),
                         amsdsk.read_file(self.real, "SEQ16.BIN"))
        h = amsdsk.read_file(self.dsk, name, keep_header=True)[:128]
        self.assertEqual(struct.unpack("<H", h[67:69])[0], sum(h[:67]) & 0xFFFF)

    def test_bad_disk(self):
        bad = os.path.join(self.tmp, "x.dsk")
        with open(bad, "wb") as f:
            f.write(b"rien")
        m = BankModel()
        m.add_wav(self.wav)
        with self.assertRaises(BankError):
            m.dsk_has(bad, "A.SMP")
        with self.assertRaises(BankError):
            m.add_to_dsk(bad, "A.SMP")


def _tk_root():
    """Fenêtre Tk cachée, ou None sans écran / sans tkinter."""
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        return root
    except Exception:  # noqa: BLE001 - pas d'écran
        return None


class TestGui(ModelBase):
    """Construction de la fenêtre et quelques actions, sans boîte de dialogue."""

    def setUp(self):
        super().setUp()
        self.root = _tk_root()
        if self.root is None:
            self.skipTest("pas d'écran disponible")
        import smp_gui
        self.gui = smp_gui
        self.app = smp_gui.SmpApp(self.root)

    def tearDown(self):
        self.app.player.close()
        self.root.destroy()
        super().tearDown()

    def pump(self):
        """Traite les événements Tk en attente."""
        self.root.update()

    def test_build_add_edit_theme(self):
        app = self.app
        app.add_wavs([self.wav, self.wav2])
        self.pump()
        self.assertEqual(len(app.tree.get_children()), 2)
        self.assertEqual(app._sel_index, 1)
        app.v_bits.set("2")                                     # réglage
        app.v_name.set("zz top")
        app._apply_now()
        it = app.model.items[1]
        self.assertEqual((it.bits, it.name), (2, "ZZTOP"))
        self.assertEqual(app.tree.item("1", "values")[1], "ZZTOP")
        app.v_hz.set("6250")                                    # fréquence en Hz
        app._hz_entered()
        app._apply_now()
        self.assertEqual(it.code, 160)
        app.v_slices.set("2")
        app.apply_slices()
        self.assertEqual(len(app.model), 3)
        app.move(-1)
        app.toggle_monitor()                                    # F3 : reconstruit
        self.pump()
        self.assertEqual(len(app.tree.get_children()), 3)
        app.remove()
        self.assertEqual(len(app.model), 2)

    def test_open_bank_disables_source_settings(self):
        app = self.app
        app.open_smp(os.path.join(ROOT, "samples", "DRUMS.SMP"))
        self.pump()
        self.assertEqual(len(app.tree.get_children()), 4)
        self.assertEqual(str(app._widgets_src[0].cget("state")), "disabled")
        self.assertIn("pas de WAV", app.note.cget("text"))
        self.assertFalse(app.b_play_src._enabled)
        self.assertTrue(app.b_save._enabled)

    def test_gauge_over_limit(self):
        long_wav = os.path.join(self.tmp, "long.wav")
        wav2smp.write_wav(long_wav, sine(300, 4.5, rate=8000), 8000)
        self.app.add_wavs([long_wav])
        self.pump()
        self.assertIn("TROP GRAND", self.app.gauge_lbl.cget("text"))
        self.assertFalse(self.app.b_save._enabled)


if __name__ == "__main__":
    unittest.main()
