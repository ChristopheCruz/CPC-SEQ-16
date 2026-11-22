"""cpcsim.py : un CPC simplifié autour du simulateur Z80 « z80 » (PyPI).

Rôle
----
Faire tourner le vrai binaire SEQ16.BIN sur PC pour le tester sans émulateur :

- le firmware est SIMULÉ : chaque routine utilisée (TXT_*, KM_TEST_KEY,
  CAS_*, ...) est remplacée par une fonction Python qui fait le travail et
  MODIFIE LES REGISTRES COMME LE VRAI FIRMWARE (ceux que la documentation
  déclare « corrompus » reçoivent des valeurs bidon), pour que les bogues de
  registres se voient ;
- le PPI 8255 et l'AY-3-8912 sont modélisés : chaque écriture dans un
  registre de l'AY est notée avec son instant, en NOP ;
- les durées des instructions sont comptées en NOP, avec la table propre au
  CPC (chaque instruction dure un nombre entier de NOP de 1 µs ; sources :
  tables de durées CPC publiées sur CPCWiki).  Dans les zones « strictes »
  (la routine de lecture), une instruction absente de la table arrête tout :
  on ne devine pas une durée ;
- l'écran texte (40 x 25) est gardé en mémoire pour vérifier l'affichage ;
- les fichiers de la disquette viennent d'un dictionnaire {nom: octets}.

Mode d'emploi (voir tools/test_player.py)
-----------------------------------------
    cpc = CPC.from_build()             # build/seq16-fr.dsk + build/seq16.sym
    cpc.files["DRUMS.SMP"] = open(...).read()
    cpc.boot()                         # jusqu'à la boucle principale
    cpc.frames(3, keys={KEY_SAMPLE})   # 3 images avec f4 enfoncée
    cpc.screen_text()                  # ce qu'il y a à l'écran
    cpc.ay_writes                      # [(instant NOP, registre, valeur), ...]

Nécessite :  pip install z80
"""
import os
import struct
import sys

import z80

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import amsdsk  # noqa: E402

# Numéros de touches du CPC (positions)
KEY_UP, KEY_RIGHT, KEY_DOWN, KEY_LEFT = 0, 1, 2, 8
# Panneaux de la v1.0 : f1 MOTIF, f2 SONG, f3 INST, f4 SAMPLE, f5 DISQUE ;
# f6 mode, f8 sauver, f9 charger (matrice du clavier CPC)
KEY_MOTIF, KEY_SONG, KEY_INST, KEY_SAMPLE, KEY_DISK = 14, 13, 5, 20, 12
KEY_MODE, KEY_SAVE, KEY_LOAD = 4, 11, 3
KEY_SPACE, KEY_SHIFT, KEY_CTRL, KEY_ESC = 47, 21, 23, 66
KEY_D, KEY_RETURN = 61, 18
PIANO_KEYS = [71, 60, 63, 61, 62, 55, 52, 54, 44, 46, 45, 38,
              67, 65, 59, 57, 58, 50, 49, 51, 48, 43, 41, 42]

# Adresses du firmware (voir src/firmware.asm)
FW = {
    0xBB06: "KM_WAIT_CHAR", 0xBB09: "KM_READ_CHAR", 0xBB1E: "KM_TEST_KEY",
    0xBB5A: "TXT_OUTPUT", 0xBB75: "TXT_SET_CURSOR", 0xBB66: "TXT_WIN_ENABLE",
    0xBB6C: "TXT_CLEAR_WINDOW", 0xBB81: "TXT_CUR_ON", 0xBB84: "TXT_CUR_OFF",
    0xBB90: "TXT_SET_PEN", 0xBB96: "TXT_SET_PAPER", 0xBC0E: "SCR_SET_MODE",
    0xBC32: "SCR_SET_INK", 0xBC38: "SCR_SET_BORDER", 0xBC77: "CAS_IN_OPEN",
    0xBC7A: "CAS_IN_CLOSE", 0xBC7D: "CAS_IN_ABANDON", 0xBC83: "CAS_IN_DIRECT", 0xBC80: "CAS_IN_CHAR",
    0xBC8C: "CAS_OUT_OPEN", 0xBC8F: "CAS_OUT_CLOSE", 0xBC92: "CAS_OUT_ABANDON",
    0xBC98: "CAS_OUT_DIRECT", 0xBC95: "CAS_OUT_CHAR", 0xBC9B: "CAS_CATALOG", 0xBCCE: "KL_INIT_BACK",
    0xBD0D: "KL_TIME_PLEASE", 0xBD19: "MC_WAIT_FLYBACK", 0xBD34: "MC_SOUND_REGISTER",
    0xBCD4: "KL_FIND_COMMAND",
}
FAKE_READ_SECTOR = 0xC0F0          # adresse fictive de la commande AMSDOS #84
FAKE_ERA = 0xC0F2                  # |ERA,"nom"
FAKE_REN = 0xC0F4                  # |REN,"nouveau","ancien"
JUNK = 0xA5                       # valeur des registres « corrompus »
HIMEM_6128 = 0xA67B               # plus haute adresse libre après AMSDOS (6128)

# --- durées des instructions sur CPC, en NOP -------------------------------
# Instructions sans préfixe.  None = dépend du saut (voir COND).
MAIN = {}
for op in range(0x40, 0x80):      # LD r,r'
    MAIN[op] = 2 if (op & 7) == 6 or ((op >> 3) & 7) == 6 else 1
MAIN[0x76] = 1                    # HALT
for op in range(0x80, 0xC0):      # ADD/ADC/SUB/SBC/AND/XOR/OR/CP r
    MAIN[op] = 2 if (op & 7) == 6 else 1
MAIN.update({
    0x00: 1, 0x08: 1, 0x18: 3,
    0x01: 3, 0x11: 3, 0x21: 3, 0x31: 3, 0x09: 3, 0x19: 3, 0x29: 3, 0x39: 3,
    0x02: 2, 0x12: 2, 0x0A: 2, 0x1A: 2, 0x22: 5, 0x2A: 5, 0x32: 4, 0x3A: 4,
    0x03: 2, 0x13: 2, 0x23: 2, 0x33: 2, 0x0B: 2, 0x1B: 2, 0x2B: 2, 0x3B: 2,
    0x34: 3, 0x35: 3, 0x36: 3,
    0x07: 1, 0x0F: 1, 0x17: 1, 0x1F: 1, 0x27: 1, 0x2F: 1, 0x37: 1, 0x3F: 1,
    0xC9: 3, 0xD9: 1, 0xE9: 1, 0xF9: 2, 0xC3: 3, 0xCD: 5,
    0xD3: 3, 0xDB: 3, 0xE3: 6, 0xEB: 1, 0xF3: 1, 0xFB: 1,
})
for r in range(8):
    if r != 6:
        MAIN[0x04 + 8 * r] = 1    # INC r
        MAIN[0x05 + 8 * r] = 1    # DEC r
        MAIN[0x06 + 8 * r] = 2    # LD r,n
for op in (0xC1, 0xD1, 0xE1, 0xF1):
    MAIN[op] = 3                  # POP
for op in (0xC5, 0xD5, 0xE5, 0xF5):
    MAIN[op] = 4                  # PUSH
for op in range(0xC6, 0x100, 8):
    MAIN[op] = 2                  # ALU n
for op in range(0xC7, 0x100, 8):
    MAIN[op] = 4                  # RST
for op in range(0xC2, 0x100, 8):
    MAIN[op] = 3                  # JP cc,nn (3 NOP, pris ou non)
# Sauts conditionnels : (longueur, NOP si pris, NOP si non pris)
COND = {0x10: (2, 4, 3), 0x20: (2, 3, 2), 0x28: (2, 3, 2), 0x30: (2, 3, 2),
        0x38: (2, 3, 2)}
for op in range(0xC0, 0x100, 8):
    COND[op] = (1, 4, 2)          # RET cc
for op in range(0xC4, 0x100, 8):
    COND[op] = (3, 5, 3)          # CALL cc

ED = {0x44: 2, 0x46: 2, 0x56: 2, 0x5E: 2, 0x47: 3, 0x4F: 3, 0x57: 3, 0x5F: 3,
      0x45: 4, 0x4D: 4, 0x67: 5, 0x6F: 5, 0xA0: 5, 0xA8: 5, 0xA1: 4, 0xA9: 4,
      0xA3: 5, 0xAB: 5, 0xA2: 5, 0xAA: 5}
for r in range(8):
    ED[0x40 + 8 * r] = 4          # IN r,(C)
    ED[0x41 + 8 * r] = 4          # OUT (C),r   (#71 = OUT (C),0)
for op in (0x42, 0x52, 0x62, 0x72, 0x4A, 0x5A, 0x6A, 0x7A):
    ED[op] = 4                    # SBC / ADC HL,rr
for op in (0x43, 0x53, 0x63, 0x73, 0x4B, 0x5B, 0x6B, 0x7B):
    ED[op] = 6                    # LD (nn),rr / LD rr,(nn)
ED_REPEAT = {0xB0: (6, 5), 0xB8: (6, 5), 0xB1: (6, 4), 0xB9: (6, 4),
             0xB3: (6, 5), 0xBB: (6, 5), 0xB2: (6, 5), 0xBA: (6, 5)}

# Préfixes DD / FD (IX, IY) : instructions qui utilisent (IX+d)
IDX_MEM = {0x34: 6, 0x35: 6, 0x36: 6, 0x86: 5, 0x8E: 5, 0x96: 5, 0x9E: 5,
           0xA6: 5, 0xAE: 5, 0xB6: 5, 0xBE: 5}
for r in range(8):
    if r != 6:
        IDX_MEM[0x46 + 8 * r] = 5         # LD r,(IX+d)
        IDX_MEM[0x70 + r] = 5             # LD (IX+d),r
IDX_OTHER = {0x21: 4, 0x22: 6, 0x2A: 6, 0x23: 3, 0x2B: 3, 0x09: 4, 0x19: 4,
             0x29: 4, 0x39: 4, 0xE1: 4, 0xE5: 5, 0xE9: 2, 0xF9: 3, 0xE3: 7}


class Timing(Exception):
    pass


def cpc_nops(mem, pc, new_pc):
    """Durée en NOP de l'instruction à pc ; new_pc = adresse après exécution
    (pour savoir si un saut conditionnel a été pris).  None si inconnue."""
    op = mem[pc]
    if op in COND:
        length, taken, not_taken = COND[op]
        return not_taken if new_pc == (pc + length) & 0xFFFF else taken
    if op == 0xCB:
        b1 = mem[(pc + 1) & 0xFFFF]
        if b1 & 7 == 6:
            return 3 if 0x40 <= b1 < 0x80 else 4
        return 2
    if op == 0xED:
        b1 = mem[(pc + 1) & 0xFFFF]
        if b1 in ED_REPEAT:
            again, last = ED_REPEAT[b1]
            return again if new_pc == pc else last
        return ED.get(b1)
    if op in (0xDD, 0xFD):
        b1 = mem[(pc + 1) & 0xFFFF]
        if b1 == 0xCB:
            b3 = mem[(pc + 3) & 0xFFFF]
            return 6 if 0x40 <= b3 < 0x80 else 7
        if b1 in IDX_MEM:
            return IDX_MEM[b1]
        if b1 in IDX_OTHER:
            return IDX_OTHER[b1]
        base = MAIN.get(b1)
        return None if base is None else base + 1   # IXH, IXL...
    return MAIN.get(op)


def read_symbols(path):
    syms = {}
    for line in open(path, encoding="latin-1"):
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("#"):
            syms[parts[0].upper()] = int(parts[1][1:], 16)
    return syms


class CPC:
    def __init__(self, binary, symbols, load=None):
        self.m = z80.Z80Machine()
        self.mem = self.m.memory
        if load is None:                      # adresse de chargement : START
            load = symbols.get("START", 0x3F00)
        self.load = load
        self.m.set_memory_block(load, binary)
        self.sym = symbols
        self.t = 0                            # temps en NOP
        self.files = {}                       # disquette simulée
        self.saved = {}                       # fichiers écrits
        self.saved_headers = {}               # en-têtes écrits par le programme
        self.rsx_log = []                     # |ERA et |REN appelés
        self.keys = set()                     # touches enfoncées
        self.frame = 0
        self.strict = []                      # zones à durées vérifiées
        self.ay = [0] * 16                    # registres de l'AY
        self.ay_sel = 0
        self.ay_writes = []                   # (instant, registre, valeur)
        self.ay_selects = []                  # (instant, registre)
        self.ppi_a = 0xFF
        self.ppi_c = 0
        self.ppi_a_input = False
        self.ppi_ctrl = []                    # écritures sur #F7
        self.gate_array = []                  # écritures sur #7F
        self.ram_block = 1                    # bloc montré en #4000-#7FFF
                                              # (self.window : fenêtre de texte)
        self.blocks = {b: bytes(0x4000) for b in (4, 5, 6, 7)}   # 64 Ko de plus
        self.ram_configs = []                 # (instant, configuration)
        self.key_reads = 0
        self.on_key_read = None               # fonction appelée à chaque lecture
        self.chars = []                       # frappes rendues par KM_WAIT_CHAR
        self.disk = None                      # image .dsk (lecture de secteurs)
        self.sector_reads = []
        self.screen = [[" "] * 40 for _ in range(25)]
        self.codes = [[32] * 40 for _ in range(25)]   # codes bruts (flèches 240-243…)
        self.attr = [[(1, 0)] * 40 for _ in range(25)]
        self.cur = [1, 1]                     # colonne, ligne
        self.pen, self.paper = 1, 0
        self.fw_log = []
        self.cas_in = None
        self.cas_in_mode = None
        self.cas_out_open = False
        self.file_errors = []                 # ce qu'AMSDOS aurait refusé
        self.stopped = False
        self.di_spans = []                    # (début, fin) interruptions coupées
        self._di_since = None
        self.m.set_output_callback(self._out)
        self.m.set_input_callback(self._in)
        self.m.sp = 0xC000
        self.handlers = {name: getattr(self, "fw_" + name, None) for name in FW.values()}

    @classmethod
    def from_build(cls, dsk=None):
        dsk = dsk or os.path.join(ROOT, "build", "seq16-fr.dsk")
        binary = amsdsk.read_file(dsk, "SEQ16.BIN")
        syms = read_symbols(os.path.join(ROOT, "build", "seq16.sym"))
        cpc = cls(binary, syms)
        cpc.use_disk(dsk)
        return cpc

    def _rsx_string(self, k):
        """Paramètre k d'une commande RSX (IX+0 = le dernier) : une chaîne."""
        ix = self.m.ix
        desc = self.mem[ix + 2 * k] | self.mem[ix + 2 * k + 1] << 8
        n, addr = self.mem[desc], self.mem[desc + 1] | self.mem[desc + 2] << 8
        return bytes(self.mem[addr:addr + n]).decode("latin-1").upper()

    def _rsx_file(self, routine):
        """|ERA et |REN, sur l'image de la disquette (comme AMSDOS)."""
        path = self.disk_path
        if routine == FAKE_ERA:
            self.rsx_log.append(("ERA", self._rsx_string(0)))
            amsdsk.remove_file(path, self._rsx_string(0))
        else:
            old, new = self._rsx_string(0), self._rsx_string(1)
            self.rsx_log.append(("REN", new, old))
            data = amsdsk.read_file(path, old)
            amsdsk.remove_file(path, old)
            amsdsk.add_file(path, new, data)
        self.use_disk(path)
        self._corrupt("af", "bc", "de", "hl")
        self._carry(True)

    def use_disk(self, dsk):
        """Met cette image .dsk dans le lecteur A (fichiers et secteurs)."""
        self.disk_path = dsk
        self.disk = amsdsk.Disk(open(dsk, "rb").read())
        self.files = {n: amsdsk.read_file(dsk, n) for n in amsdsk.list_files(dsk)}

    def addr(self, name):
        return self.sym[name.upper()]

    # --- ports ---------------------------------------------------------------
    def _out(self, port, value):
        hi = (port >> 8) & 0xFF
        if hi == 0xF4:
            self.ppi_a = value
        elif hi == 0xF6:
            self.ppi_c = value
            func = value & 0xC0
            if func == 0xC0 and not self.ppi_a_input:
                self.ay_sel = self.ppi_a & 0x0F
                self.ay_selects.append((self.t, self.ay_sel))
            elif func == 0x80 and not self.ppi_a_input:
                self.ay[self.ay_sel] = self.ppi_a
                self.ay_writes.append((self.t, self.ay_sel, self.ppi_a))
        elif hi == 0xF7:
            self.ppi_ctrl.append((self.t, value))
            if value & 0x80:                  # mode : toutes les sorties à 0
                self.ppi_a_input = bool(value & 0x10)
                self.ppi_c = 0
            else:                             # mise à 1 / à 0 d'un bit de C
                bit = (value >> 1) & 7
                if value & 1:
                    self.ppi_c |= 1 << bit
                else:
                    self.ppi_c &= ~(1 << bit)
        elif hi == 0x7F:
            self.gate_array.append((self.t, value))
            if value & 0xC0 == 0xC0:          # configuration de la mémoire (6128)
                self._ram_config(value & 7)

    # --- mémoire du 6128 -----------------------------------------------------
    # Les configurations #C0 et #C4 à #C7 montrent en #4000-#7FFF la mémoire
    # normale ou l'un des 4 blocs de 16 Ko de la mémoire supplémentaire.  La
    # mémoire du Z80 simulé reste plate : on échange le contenu de la fenêtre.
    def _ram_config(self, cfg):
        if cfg not in (0, 4, 5, 6, 7):
            raise NotImplementedError(f"configuration mémoire #C{cfg} non simulée")
        target = 1 if cfg == 0 else cfg       # 1 = bloc normal de #4000
        if target == self.ram_block:
            return
        self.blocks[self.ram_block] = bytes(self.mem[0x4000:0x8000])
        self.m.set_memory_block(0x4000, self.blocks[target])
        self.ram_block = target
        self.ram_configs.append((self.t, cfg))

    def bank_peek(self, block, addr, n=1):
        """Lit le bloc supplémentaire 4 à 7, adresse vue en #4000-#7FFF."""
        if block == self.ram_block:
            return self.peek(addr, n)
        return bytes(self.blocks[block][addr - 0x4000:addr - 0x4000 + n])

    def bank_poke(self, block, addr, data):
        if block == self.ram_block:
            return self.poke(addr, data)
        b = bytearray(self.blocks[block])
        b[addr - 0x4000:addr - 0x4000 + len(data)] = bytes(data)
        self.blocks[block] = bytes(b)

    def _in(self, port):
        hi = (port >> 8) & 0xFF
        if hi == 0xF4 and self.ppi_a_input and (self.ppi_c & 0xC0) == 0x40 \
                and self.ay_sel == 14:
            self.key_reads += 1
            if self.on_key_read:
                self.on_key_read(self)
            row = self.ppi_c & 0x0F
            v = 0xFF
            for k in self.keys:
                if k // 8 == row:
                    v &= ~(1 << (k % 8))      # bit à 0 = touche enfoncée
            return v
        if hi == 0xF5:
            return 0xFE
        return 0xFF

    # --- exécution -----------------------------------------------------------
    def in_strict(self, pc):
        return any(a <= pc < b for a, b in self.strict)

    def step(self):
        m = self.m
        pc = m.pc
        if pc in FW:
            self._firmware(FW[pc])
            return
        op = self.mem[pc]
        if op == 0x76:                        # HALT : on n'attend pas
            m.pc = (pc + 1) & 0xFFFF
            self.t += 1
            return
        if op == 0xC7 and pc >= self.load:    # RST 0 : le programme quitte
            self.stopped = True
            return
        if op == 0xDF:                        # RST #18 : appel lointain
            self._far_call(pc)
            return
        was_on = m.iff1
        m.ticks_to_stop = 1
        m.run()
        n = cpc_nops(self.mem, pc, m.pc)
        if n is None:
            if self.in_strict(pc):
                raise Timing("durée inconnue : #%02X à #%04X" % (op, pc))
            n = 1
        self.t += n
        if was_on and not m.iff1:
            self._di_since = self.t
        elif not was_on and m.iff1 and self._di_since is not None:
            self.di_spans.append((self._di_since, self.t))
            self._di_since = None

    def run_until(self, target, limit=20_000_000):
        target = self.addr(target) if isinstance(target, str) else target
        n = 0
        while self.m.pc != target and not self.stopped:
            self.step()
            n += 1
            if n > limit:
                raise RuntimeError("trop long : PC = #%04X" % self.m.pc)

    def call(self, routine, a=None, b=None, c=None, limit=20_000_000):
        """Appelle une routine et rend la main à son RET."""
        m = self.m
        ret = 0x0000                          # adresse de retour fictive
        m.sp = (m.sp - 2) & 0xFFFF
        self.mem[m.sp] = ret & 0xFF
        self.mem[m.sp + 1] = ret >> 8
        if a is not None:
            m.a = a & 0xFF
        if b is not None:
            m.b = b & 0xFF
        if c is not None:
            m.c = c & 0xFF
        m.pc = self.addr(routine) if isinstance(routine, str) else routine
        self.run_until(ret, limit)

    def boot(self):
        self.m.iff1 = self.m.iff2 = 1        # le firmware tourne, interruptions ouvertes
        self.m.pc = self.addr("START")
        self.run_until("MAIN_LOOP")

    def frames(self, n=1, keys=()):
        """Fait tourner n tours de la boucle principale avec ces touches."""
        self.keys = set(keys)
        for _ in range(n):
            self.step()                       # sort de MAIN_LOOP
            self.run_until("MAIN_LOOP")

    # --- firmware simulé ---------------------------------------------------
    def _firmware(self, name):
        m = self.m
        self.fw_log.append(name)
        h = self.handlers.get(name)
        if h is None:
            raise RuntimeError("routine du firmware non simulée : " + name)
        h()
        lo, hi = self.mem[m.sp], self.mem[(m.sp + 1) & 0xFFFF]
        m.sp = (m.sp + 2) & 0xFFFF
        m.pc = lo | hi << 8
        self.t += 50                          # durée arbitraire

    def _corrupt(self, *regs):
        for r in regs:
            if r == "af":
                self.m.a = JUNK
                self.m.f = 0x00
            else:
                setattr(self.m, r, JUNK * 257 & 0xFFFF if len(r) == 2 else JUNK)

    def _set_flag(self, mask, on):
        self.m.f = (self.m.f | mask) if on else (self.m.f & ~mask & 0xFF)

    def _carry(self, on):
        self._set_flag(0x01, on)

    def _zero(self, on):
        self._set_flag(0x40, on)

    def fw_KM_TEST_KEY(self):
        k = self.m.a
        pressed = k in self.keys
        self.m.a = JUNK
        self.m.hl = JUNK * 257
        self.m.c = (0x20 if KEY_SHIFT in self.keys else 0) | (0x80 if KEY_CTRL in self.keys else 0)
        self._zero(not pressed)              # NZ = touche enfoncée

    def fw_KM_READ_CHAR(self):
        self._carry(False)
        self.m.a = JUNK

    def fw_KM_WAIT_CHAR(self):
        c = self.chars.pop(0) if self.chars else 13   # RETURN par défaut
        if callable(c):                       # une fonction : appelée au moment
            c = c()                           # de la frappe (pour regarder l'écran)
        self.m.a = c
        self._carry(True)

    def fw_KL_FIND_COMMAND(self):
        name = self.mem[self.m.hl]
        hl = self.m.hl
        word = bytes(self.mem[hl:hl + 3])
        fake = {b"ER" + bytes([0xC1]): FAKE_ERA, b"RE" + bytes([0xCE]): FAKE_REN}.get(word)
        if name == 0x84:                      # lecture de secteur d'AMSDOS
            self.m.hl = FAKE_READ_SECTOR
            self.m.c = 7
            self._carry(True)
        elif fake:
            self.m.hl = fake
            self.m.c = 7
            self._carry(True)
        else:
            self._carry(False)
        self.m.a = JUNK

    def _far_call(self, pc):
        """RST #18 suivi de l'adresse d'une adresse lointaine (3 octets)."""
        ptr = self.mem[pc + 1] | self.mem[pc + 2] << 8
        routine = self.mem[ptr] | self.mem[ptr + 1] << 8
        if routine in (FAKE_ERA, FAKE_REN):
            self._rsx_file(routine)
            self.m.pc = (pc + 3) & 0xFFFF
            return
        if routine != FAKE_READ_SECTOR:
            raise RuntimeError("appel lointain inconnu : #%04X" % routine)
        m = self.m
        track, sector, buf = m.d, m.c, m.hl
        self.sector_reads.append((m.e, track, sector))
        off = self.disk.sect_off.get((track, sector)) if self.disk else None
        if m.e != 0 or off is None:
            m.a = 0xFF                        # erreur
            self._carry(False)
        else:
            m.set_memory_block(buf, bytes(self.disk.raw[off:off + 512]))
            m.a = 0
            self._carry(True)
        m.pc = (pc + 3) & 0xFFFF
        self.t += 2000

    def fw_TXT_OUTPUT(self):                  # tous les registres préservés
        col, row = self.cur
        if col > 40:
            col, row = 1, row + 1
        if 1 <= row <= 25:
            self.screen[row - 1][col - 1] = chr(self.m.a) if 32 <= self.m.a < 127 else "#"
            self.codes[row - 1][col - 1] = self.m.a
            self.attr[row - 1][col - 1] = (self.pen, self.paper)
        self.cur = [col + 1, row]

    def fw_TXT_SET_CURSOR(self):
        self.cur = [self.m.h, self.m.l]
        self._corrupt("af", "hl")

    def fw_TXT_SET_PEN(self):
        self.pen = self.m.a & 3
        self._corrupt("af", "hl")

    def fw_TXT_SET_PAPER(self):
        self.paper = self.m.a & 3
        self._corrupt("af", "hl")

    def fw_TXT_WIN_ENABLE(self):
        # H, D = colonnes gauche et droite ; L, E = lignes haut et bas (0 à ...)
        m = self.m
        self.window = (min(m.h, m.d), max(m.h, m.d), min(m.l, m.e), max(m.l, m.e))
        self._corrupt("af", "bc", "de", "hl")

    def fw_TXT_CLEAR_WINDOW(self):
        left, right, top, bottom = getattr(self, "window", (0, 39, 0, 24))
        for r in range(top, min(bottom, 24) + 1):
            for c in range(left, min(right, 39) + 1):
                self.screen[r][c] = " "
                self.codes[r][c] = 32
                self.attr[r][c] = (self.pen, self.paper)
        self._corrupt("af", "bc", "de", "hl")

    def fw_TXT_CUR_ON(self):
        pass

    def fw_TXT_CUR_OFF(self):
        pass

    def fw_SCR_SET_MODE(self):
        self.screen = [[" "] * 40 for _ in range(25)]
        self.codes = [[32] * 40 for _ in range(25)]
        self.attr = [[(1, 0)] * 40 for _ in range(25)]
        self.cur = [1, 1]
        self._corrupt("af", "bc", "de", "hl")

    def fw_SCR_SET_INK(self):
        self._corrupt("af", "bc", "de", "hl")

    def fw_SCR_SET_BORDER(self):
        self._corrupt("af", "bc", "de", "hl")

    def fw_KL_INIT_BACK(self):
        self.m.de = self.m.de                 # AMSDOS se loge en haut
        self.m.hl = HIMEM_6128
        self._corrupt("af", "bc")

    def fw_KL_TIME_PLEASE(self):              # DEHL = temps en 1/300 s
        """Comme sur le CPC, le compteur avance par l'interruption à 300 Hz :
        le temps passé interruptions coupées (un digidrum) ne compte pas."""
        off = sum(b - a for a, b in self.di_spans)
        if self._di_since is not None:
            off += self.t - self._di_since
        ticks = (self.t - off) * 3 // 10_000
        self.m.de = (ticks >> 16) & 0xFFFF
        self.m.hl = ticks & 0xFFFF

    def fw_MC_WAIT_FLYBACK(self):             # tous les registres préservés
        self.frame += 1

    def fw_MC_SOUND_REGISTER(self):
        reg, val = self.m.a, self.m.c
        if reg < 16:
            self.ay[reg] = val
            self.ay_writes.append((self.t, reg, val))
        self._corrupt("af", "bc")

    def _name(self):
        n = self.m.b
        hl = self.m.hl
        return bytes(self.mem[hl:hl + n]).decode("latin-1").upper()

    def _file_error(self, what):
        """Ce qu'AMSDOS refuserait : noté dans file_errors (les tests le
        vérifient), et la routine échoue comme sur le CPC."""
        self.file_errors.append(what)
        if os.environ.get("CPCSIM_STRICT"):
            raise RuntimeError(what)
        self._corrupt("af", "bc", "de", "hl")
        self._carry(False)

    def fw_CAS_IN_OPEN(self):
        if self.cas_in is not None:           # AMSDOS : déjà ouvert
            self._file_error("CAS_IN_OPEN : un fichier est déjà ouvert en lecture")
            return
        name = self._name()
        data = self.files.get(name)
        if data is None:
            self._corrupt("af", "bc", "de", "hl")
            self._carry(False)
            return
        self.cas_in = data
        self.cas_in_mode = None               # ni CHAR ni DIRECT encore
        self.cas_pos = 0                      # CAS_IN_CHAR : prochain octet
        self.m.bc = len(data) & 0xFFFF
        self.m.de = 0
        self.m.hl = JUNK * 257
        self.m.a = 2
        self._carry(True)

    def fw_CAS_IN_DIRECT(self):
        if self.cas_in is None or self.cas_in_mode == "char":
            self._file_error("CAS_IN_DIRECT : fichier fermé ou déjà lu par CAS_IN_CHAR")
            return
        self.cas_in_mode = "direct"
        hl = self.m.hl
        data = self.cas_in
        self.m.set_memory_block(hl, data)
        self._corrupt("af", "bc", "de", "ix")
        self.m.hl = 0
        self._carry(True)

    def fw_CAS_IN_CHAR(self):
        """Octet suivant du fichier ouvert ; Carry = 0 à la fin.
        Comme sur le CPC : BC, DE et HL sont gardés, les drapeaux changent."""
        data = self.cas_in
        if data is not None and self.cas_in_mode == "direct":
            self._file_error("CAS_IN_CHAR après CAS_IN_DIRECT")
            data = None
        elif data is not None:
            self.cas_in_mode = "char"
        if data is None or self.cas_pos >= len(data):
            self.m.a = 0x0F                   # fin « dure »
            self.m.f = 0x00                   # Carry = 0, Z = 0
            return
        self.m.a = data[self.cas_pos]
        self.cas_pos += 1
        self.m.f = 0x00
        # Comme AMSDOS : l'octet #1A est signalé comme une « fin douce »
        # (Carry = 0, A = #1A), même dans un fichier binaire ; la lecture
        # peut continuer.  La vraie fin : Carry = 0, A = #0F.
        self._carry(self.m.a != 0x1A)

    def fw_CAS_IN_CLOSE(self):
        self.cas_in = None
        self._corrupt("af", "bc", "de", "hl")
        self._carry(True)

    def fw_CAS_IN_ABANDON(self):
        self.cas_in = None
        self._corrupt("af", "bc", "de", "hl")
        self._carry(True)

    def fw_CAS_OUT_OPEN(self):
        if self.cas_out_open:
            self._file_error("CAS_OUT_OPEN : un fichier est déjà ouvert en écriture")
            return
        self.cas_out_open = True
        self.cas_out = self._name()
        self.cas_out_chars = None             # octets écrits par CAS_OUT_CHAR
        self._corrupt("af", "bc", "de", "hl")
        self._carry(True)

    def fw_CAS_OUT_DIRECT(self):
        hl, de = self.m.hl, self.m.de
        self.saved[self.cas_out] = bytes(self.mem[hl:hl + de])
        self._corrupt("af", "bc", "de", "hl")
        self._carry(True)

    def fw_CAS_OUT_CHAR(self):
        """Un octet de plus dans le fichier ouvert (AF corrompu)."""
        if self.cas_out_chars is None:
            self.cas_out_chars = bytearray()
        self.cas_out_chars.append(self.m.a)
        self._corrupt("af")
        self._carry(True)

    def fw_CAS_OUT_CLOSE(self):
        """Comme AMSDOS : un fichier écrit octet par octet qui commence par un
        en-tête valide (somme des octets 0 à 66) est un fichier binaire ; ses
        données s'arrêtent à la longueur de l'en-tête.  saved = les données,
        saved_headers = l'en-tête écrit par le programme."""
        data = getattr(self, "cas_out_chars", None)
        if data is not None:
            data = bytes(data)
            head = data[:128]
            if len(head) == 128 and sum(head[:67]) == head[0x43] | head[0x44] << 8:
                n = head[0x40] | head[0x41] << 8 | head[0x42] << 16
                self.saved_headers[self.cas_out] = head
                self.saved[self.cas_out] = data[128:128 + n]
            else:
                self.saved[self.cas_out] = data
            self.cas_out_chars = None
        self.cas_out_open = False
        self._corrupt("af", "bc", "de", "hl")
        self._carry(True)

    def fw_CAS_OUT_ABANDON(self):
        self.cas_out_open = False
        self.cas_out_chars = None
        self._corrupt("af", "bc", "de", "hl")
        self._carry(True)

    def fw_CAS_CATALOG(self):
        if self.cas_in is not None:           # AMSDOS : lecture en cours
            self._file_error("CAS_CATALOG : un fichier est ouvert en lecture")
            return
        self._corrupt("af", "bc", "de", "hl")
        self._carry(True)

    # --- aides pour les tests ---------------------------------------------
    def screen_text(self):
        return "\n".join("".join(r) for r in self.screen)

    def row(self, n):
        return "".join(self.screen[n - 1])

    def peek(self, addr, n=1):
        return bytes(self.mem[addr:addr + n])

    def poke(self, addr, data):
        self.m.set_memory_block(addr, bytes(data))

    def word(self, addr):
        return struct.unpack("<H", self.peek(addr, 2))[0]
