"""Tests du .SNG version 4 (src/sngio.asm, lot 5 du plan) : un seul fichier
qui garde le morceau ET sa banque de samples, écrit et relu octet par
octet avec un en-tête AMSDOS écrit par le programme.

On fait tourner le vrai SEQ16.BIN dans le simulateur (tools/cpcsim.py).
Lancement :  python -m unittest tools.test_sngio   (paquet z80 nécessaire)
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_player  # noqa: E402

cpcsim = test_player.cpcsim
KEY_SONG, KEY_SAMPLE, KEY_SAVE, KEY_LOAD = 13, 20, 11, 3
PAT = 260
FIXED = 16 + 32 * 16 + 32 * 6 + 8 * 16
SONG_SIZE3 = FIXED + 32 * PAT + 16 + 2 + 64 * 3 + 32 * 8
BANK = test_player.BANK
MSG = 25


def typed(text):
    return [ord(c) for c in text] + [13]


@unittest.skipIf(cpcsim is None, "paquet z80 absent (pip install z80)")
class SngV4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cpc = cpcsim.CPC.from_build()
        cpc.boot()
        cls.base = cpc

    def setUp(self):
        self.cpc = test_player.PlayerTest._clone(self.base)

    make_disk = test_player.PlayerTest.make_disk

    def key(self, *keys):
        self.cpc.frames(1, keys=set(keys))
        self.cpc.frames(1)

    def var(self, name):
        return self.cpc.peek(self.cpc.addr(name))[0]

    def save(self, name):
        self.key(KEY_SONG)
        self.cpc.chars = typed(name)
        self.key(KEY_SAVE)
        return self.cpc.saved[name + ".SNG"]

    def with_drums(self):
        self.key(KEY_SAMPLE)                      # f4 charge DRUMS.SMP
        self.assertEqual(self.var("smp_count"), 4)
        return self.cpc.word(self.cpc.addr("smp_bank_len"))

    def test_header(self):
        """L'en-tête AMSDOS écrit par le programme : nom, type binaire,
        longueurs, somme de contrôle des octets 0 à 66."""
        n = self.with_drums()
        data = self.save("AVEC")
        head = self.cpc.saved_headers["AVEC.SNG"]
        self.assertEqual(head[0], 0)                          # utilisateur 0
        self.assertEqual(head[1:12], b"AVEC    SNG")
        self.assertEqual(head[0x12], 2)                       # binaire
        self.assertEqual(head[0x17], 0xFF)
        total = SONG_SIZE3 + 2 + n
        self.assertEqual(len(data), total)
        for off in (0x13, 0x18, 0x40):
            self.assertEqual(head[off] | head[off + 1] << 8, total, hex(off))
        self.assertEqual(head[0x42], 0)
        self.assertEqual(head[0x43] | head[0x44] << 8, sum(head[:67]))

    def test_samples_travel_with_the_song(self):
        """La disquette n'a pas DRUMS.SMP : la banque revient du .SNG."""
        cpc = self.cpc
        n = self.with_drums()
        drums = cpc.peek(BANK, n)
        data = self.save("AVEC")
        self.assertEqual(data[4], 4)                          # version 4
        self.assertEqual(data[SONG_SIZE3:SONG_SIZE3 + 2], n.to_bytes(2, "little"))
        self.assertEqual(data[SONG_SIZE3 + 2:], drums)
        cpc.poke(BANK, bytes(n))                              # banque effacée
        cpc.poke(cpc.addr("smp_count"), [0])
        cpc.poke(cpc.addr("smp_name"), b"AUTRE   ")
        self.make_disk({"AVEC.SNG": data}, keep=("SEQ16.BIN",))
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertIn("MORCEAU ET BANQUE DE SAMPLES CHARGES", cpc.row(MSG))
        self.assertEqual(self.var("smp_count"), 4)
        self.assertEqual(cpc.peek(BANK, n), drums)
        self.assertEqual(cpc.word(cpc.addr("smp_bank_len")), n)
        self.assertEqual(cpc.peek(cpc.addr("smp_name"), 8), b"DRUMS   ")

    def test_song_without_bank(self):
        cpc = self.cpc
        cpc.poke(cpc.addr("smp_count"), [0])
        data = self.save("SANS")
        self.assertEqual(len(data), SONG_SIZE3 + 2)
        self.assertEqual(data[-2:], b"\x00\x00")
        self.make_disk({"SANS.SNG": data}, keep=("SEQ16.BIN",))
        before = cpc.peek(BANK, 64)
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertIn("MORCEAU CHARGE", cpc.row(MSG))
        self.assertEqual(cpc.peek(BANK, 64), before)          # rien d'écrasé

    def test_truncated_file_refused(self):
        cpc = self.cpc
        self.with_drums()
        data = self.save("COURT")
        self.make_disk({"COURT.SNG": data[:-100]}, keep=("SEQ16.BIN",))
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertNotIn("CHARGE", cpc.row(MSG))
        self.assertEqual(cpc.ram_block, 1)

    def test_read_error_shows_code_and_position(self):
        """Lecture interrompue (fin de fichier d'AMSDOS au 1000e octet) : le
        message donne le code d'erreur et le nombre d'octets lus."""
        cpc = self.cpc
        cpc.poke(cpc.addr("smp_count"), [0])
        data = self.save("CASSE")
        self.make_disk({"CASSE.SNG": data}, keep=("SEQ16.BIN",))
        orig = cpc.fw_CAS_IN_CHAR

        def broken():
            if cpc.cas_pos >= 1000:
                cpc.m.a = 0x0F                    # fin de fichier « dure »
                cpc.m.f = 0
                return
            orig()
        cpc.handlers = dict(cpc.handlers, CAS_IN_CHAR=broken)
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertIn("ERREUR DISQUE (DISQUETTE ? NOM ?) 0F03E8", cpc.row(MSG))
        self.assertIsNone(cpc.cas_in)             # fichier abandonné
        self.assertEqual(cpc.file_errors, [])

    def test_byte_1A_does_not_stop_loading(self):
        """AMSDOS signale chaque octet #1A comme une « fin douce » (Carry = 0,
        A = #1A), même dans un fichier binaire.  Sur le CPC, NUIT.SNG (un #1A
        au 861e octet) donnait « ERREUR DISQUE ... 1A035D »."""
        import amsdsk
        disk = os.path.join(HERE, "..", "build", "seq16-songs.dsk")
        for name, at in (("NUIT.SNG", 861), ("ROBOT.SNG", None)):
            cpc = test_player.PlayerTest._clone(self.base)
            self.cpc = cpc
            data = amsdsk.read_file(disk, name)
            self.assertIn(0x1A, data)
            if at is not None:
                self.assertEqual(data.index(0x1A), at)
            self.make_disk({name: data}, keep=("SEQ16.BIN",))
            self.key(KEY_SONG)
            cpc.chars = [13]
            self.key(KEY_LOAD)
            self.assertIn("CHARGE", cpc.row(MSG), name)
            self.assertNotIn("ERREUR", cpc.row(MSG), name)
            self.assertEqual(cpc.file_errors, [])

    def test_open_error_shows_code(self):
        cpc = self.cpc
        cpc.poke(cpc.addr("smp_count"), [0])
        cpc.poke(cpc.addr("fname"), b"ABSENT  ")
        load = cpc.addr("disk_load")
        cpc.m.pc = load                           # f9 sur un nom absent
        cpc.m.sp -= 2
        cpc.poke(cpc.m.sp, (cpc.addr("main_loop")).to_bytes(2, "little"))
        cpc.frames(2)
        self.assertRegex(cpc.row(MSG), r"ERREUR DISQUE \(DISQUETTE \? NOM \?\) ..FFFF")

    def test_loads_respect_amsdos_rules(self):
        """Sauver puis recharger : jamais deux fichiers ouverts, jamais
        CAS_IN_CHAR mélangé à CAS_IN_DIRECT (le simulateur le note)."""
        cpc = self.cpc
        self.with_drums()
        data = self.save("REGLES")
        self.make_disk({"REGLES.SNG": data}, keep=("SEQ16.BIN", "DRUMS.SMP"))
        for _ in range(2):
            cpc.chars = [13]
            self.key(KEY_LOAD)
            self.assertIn("CHARGES", cpc.row(MSG))
        self.assertEqual(cpc.file_errors, [])

    def test_old_v3_file_still_loads(self):
        cpc = self.cpc
        self.with_drums()
        data = bytearray(self.save("ANCIEN")[:SONG_SIZE3])
        data[4] = 3
        self.make_disk({"ANCIEN.SNG": bytes(data)}, keep=("SEQ16.BIN", "DRUMS.SMP"))
        cpc.chars = [13]
        self.key(KEY_LOAD)
        self.assertIn("MORCEAU", cpc.row(MSG))
        self.assertEqual(self.var("smp_count"), 4)             # par son nom (DRUMS.SMP)

    # --- la place sur la disquette (disk_room) ---------------------------------------
    def program_disk(self, free_k=None):
        """Une copie de la disquette du programme (25 K libres), où vont les
        fichiers écrits (avec NOM.BAK, comme AMSDOS).  free_k : un fichier
        de remplissage ne laisse que free_k K libres."""
        import amsdsk
        import shutil
        import tempfile
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        path = os.path.join(d, "t.dsk")
        shutil.copy(os.path.join(test_player.ROOT, "build", "seq16-fr.dsk"), path)
        cpc = self.cpc
        cpc.use_disk(path)
        if free_k is not None:
            fill = cpc.disk_free() // 1024 - free_k
            amsdsk.add_file(path, "PLEIN.BIN", bytes(fill * 1024 - 128))
            cpc.use_disk(path)
            self.assertEqual(cpc.disk_free(), free_k * 1024)
        cpc.write_disk = True
        return path

    def test_same_song_saved_again_and_again(self):
        """Sauver quatre fois LONG.SNG (10 K) sur la disquette du programme.
        AMSDOS n'efface LONG.BAK qu'à la fermeture : pendant l'écriture, la
        disquette garde LONG.BAK, l'ancien LONG.SNG et le nouveau.  En v1.0,
        la 3e sauvegarde manquait de place (ERREUR DISQUE) et la disquette
        gardait l'ancienne version.  LONG.BAK est maintenant effacé avant."""
        import amsdsk
        cpc = self.cpc
        cpc.poke(cpc.addr("smp_count"), [0])
        path = self.program_disk()
        pos0 = cpc.addr("smp_blk_src") + FIXED + 16 + 2       # motif de la position 00
        for i in range(4):
            cpc.poke(pos0, [i])
            self.save("LONG")
            self.assertIn("MORCEAU SAUVE", cpc.row(MSG), i)
            self.assertEqual(amsdsk.read_file(path, "LONG.SNG")[FIXED + 32 * PAT + 16 + 2], i)
        self.assertEqual(cpc.disk_full, [])
        self.assertEqual(cpc.rsx_log[-1], ("ERA", "LONG.BAK"))
        self.assertIn("LONG.BAK", amsdsk.list_files(path))     # la version d'avant

    def test_disk_full_message(self):
        """Pas assez de place, même sans .BAK : rien n'est écrit, le message
        dit la place libre."""
        cpc = self.cpc
        cpc.poke(cpc.addr("smp_count"), [0])
        self.program_disk(free_k=6)
        self.key(KEY_SONG)
        cpc.chars = typed("GROS")
        self.key(KEY_SAVE)
        self.assertEqual(cpc.row(MSG).strip(), "6 K LIBRES : DISQUETTE PLEINE")
        self.assertNotIn("GROS.SNG", cpc.saved)
        self.assertEqual(cpc.disk_full, [])                    # pas même essayé
        self.assertEqual(cpc.file_errors, [])

    def test_room_counts_blocks_of_1k(self):
        """disk_room : (octets + 128 d'en-tête) en blocs de 1 Ko."""
        cpc = self.cpc
        self.program_disk(free_k=1)
        name = cpc.addr("fname_full")
        cpc.poke(name, b"ESSAI.PAT")
        for size, ok in ((896, True), (897, False), (0, True)):
            cpc.call("disk_room", b=9, hl=name, de=size)
            self.assertEqual(bool(cpc.m.f & 1), ok, size)
        self.assertEqual(cpc.row(MSG).strip(), "1 K LIBRES : DISQUETTE PLEINE")

    def test_pattern_save_checks_room_too(self):
        """Les autres sauvegardes (motif, instruments, samples) aussi."""
        cpc = self.cpc
        self.program_disk(free_k=0)
        cpc.chars = typed("MOTIF9")
        cpc.call("disk_save_pat")
        self.assertEqual(cpc.row(MSG).strip(), "0 K LIBRES : DISQUETTE PLEINE")
        self.assertEqual(cpc.saved, {})


if __name__ == "__main__":
    unittest.main()
