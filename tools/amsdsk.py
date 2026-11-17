"""amsdsk.py : ajouter ou relire un fichier dans une disquette CPC (.dsk).

Rôle
----
RASM fabrique build/seq16.dsk avec le programme SEQ16.BIN. Ce module ajoute
d'autres fichiers sur la même disquette (par exemple la banque DRUMS.SMP),
sans passer par un éditeur de disquettes.

Format géré
-----------
- Image « EXTENDED CPC DSK » (celle que produit RASM) ou « MV - CPC » standard.
- Format AMSDOS « DATA » : 9 secteurs de 512 octets par piste, numérotés
  #C1 à #C9, une seule face.
- Blocs de 1 Ko (2 secteurs). Les blocs 0 et 1 forment le catalogue :
  64 entrées de 32 octets. 180 blocs en tout (40 pistes).
- Chaque fichier reçoit un en-tête AMSDOS de 128 octets (fichier binaire,
  type 2), comme ceux qu'écrit le CPC lui-même.

Mode d'emploi
-------------
    python tools/amsdsk.py build/seq16.dsk samples/DRUMS.SMP     # ajoute
    python tools/amsdsk.py build/seq16.dsk --list                 # catalogue

Depuis Python :  add_file(chemin_dsk, "DRUMS.SMP", données)
                 read_file(chemin_dsk, "DRUMS.SMP") -> données (sans en-tête)
"""
import argparse
import os
import struct
import sys

SECT_SIZE = 512
SECT_PER_TRACK = 9
FIRST_ID = 0xC1
BLOCK_SIZE = 1024
NB_BLOCKS = 180          # format DATA : 40 pistes x 9 secteurs / 2
DIR_ENTRIES = 64
DIR_BLOCKS = 2


class Disk:
    """Une image .dsk chargée en mémoire, accès par secteur logique."""

    def __init__(self, raw):
        self.raw = bytearray(raw)
        sig = bytes(self.raw[:8])
        if sig == b"EXTENDED":
            self.extended = True
        elif sig == b"MV - CPC":
            self.extended = False
        else:
            raise ValueError("ce fichier n'est pas une image .dsk de CPC")
        self.nb_tracks = self.raw[0x30]
        self.nb_sides = self.raw[0x31]
        if self.nb_sides != 1:
            raise ValueError("seules les disquettes une face sont gérées")
        # Position de chaque piste dans le fichier
        self.track_off = []
        off = 0x100
        for t in range(self.nb_tracks):
            if self.extended:
                size = self.raw[0x34 + t] * 256
            else:
                size = struct.unpack_from("<H", self.raw, 0x32)[0]
            self.track_off.append(off if size else None)
            off += size
        # Position de chaque secteur (piste, numéro) dans le fichier
        self.sect_off = {}
        for t, toff in enumerate(self.track_off):
            if toff is None:
                continue
            if bytes(self.raw[toff:toff + 10]) != b"Track-Info":
                raise ValueError("piste %d illisible" % t)
            nb = self.raw[toff + 0x15]
            data = toff + 0x100
            for s in range(nb):
                info = toff + 0x18 + 8 * s
                sid = self.raw[info + 2]
                if self.extended:
                    length = struct.unpack_from("<H", self.raw, info + 6)[0]
                else:
                    length = 128 << self.raw[info + 3]
                self.sect_off[(t, sid)] = data
                data += length
        if (0, FIRST_ID) not in self.sect_off:
            raise ValueError("disquette au format DATA (#C1) attendue")

    def _sector(self, logical):
        """Décalage dans le fichier du secteur logique n (0 = piste 0, #C1)."""
        t, s = divmod(logical, SECT_PER_TRACK)
        key = (t, FIRST_ID + s)
        if key not in self.sect_off:
            raise ValueError("secteur absent : piste %d, #%02X" % key)
        return self.sect_off[key]

    def read_block(self, b):
        out = bytearray()
        for k in range(2):
            off = self._sector(2 * b + k)
            out += self.raw[off:off + SECT_SIZE]
        return out

    def write_block(self, b, data):
        data = bytes(data).ljust(BLOCK_SIZE, b"\x1a")
        for k in range(2):
            off = self._sector(2 * b + k)
            self.raw[off:off + SECT_SIZE] = data[k * SECT_SIZE:(k + 1) * SECT_SIZE]

    # --- catalogue ---------------------------------------------------------
    def read_dir(self):
        d = self.read_block(0) + self.read_block(1)
        return [bytearray(d[i * 32:(i + 1) * 32]) for i in range(DIR_ENTRIES)]

    def write_dir(self, entries):
        d = b"".join(bytes(e) for e in entries)
        self.write_block(0, d[:BLOCK_SIZE])
        self.write_block(1, d[BLOCK_SIZE:])

    def max_blocks(self):
        """Nombre de blocs réellement présents sur l'image (au plus 180)."""
        n = 0
        while n < NB_BLOCKS:
            try:
                self._sector(2 * n + 1)
            except ValueError:
                break
            n += 1
        return n


def amsdos_name(name):
    """'drums.smp' -> (b'DRUMS   ', b'SMP')"""
    base, _, ext = name.upper().partition(".")
    if not base or len(base) > 8 or len(ext) > 3:
        raise ValueError("nom AMSDOS invalide (8 + 3 caractères) : " + name)
    return base.ljust(8).encode("ascii"), ext.ljust(3).encode("ascii")


def amsdos_header(name, length, load=0x0000, entry=0x0000):
    """En-tête AMSDOS de 128 octets pour un fichier binaire (type 2)."""
    base, ext = amsdos_name(name)
    h = bytearray(128)
    h[1:9] = base
    h[9:12] = ext
    h[18] = 2                                   # binaire
    struct.pack_into("<H", h, 21, load)         # adresse de chargement
    struct.pack_into("<H", h, 24, length & 0xFFFF)
    struct.pack_into("<H", h, 26, entry)        # adresse d'exécution
    h[64] = length & 0xFF                       # longueur sur 24 bits
    h[65] = (length >> 8) & 0xFF
    h[66] = (length >> 16) & 0xFF
    struct.pack_into("<H", h, 67, sum(h[:67]) & 0xFFFF)   # somme de contrôle
    return bytes(h)


def _matches(entry, base, ext):
    return (entry[0] != 0xE5 and bytes(entry[1:9]) == base
            and bytes(b & 0x7F for b in entry[9:12]) == ext)


def add_file(dsk_path, name, data, load=0x0000):
    """Ajoute (ou remplace) un fichier binaire AMSDOS dans l'image .dsk."""
    disk = Disk(open(dsk_path, "rb").read())
    base, ext = amsdos_name(name)
    entries = disk.read_dir()
    for e in entries:                           # efface l'ancienne version
        if _matches(e, base, ext):
            e[0] = 0xE5
    used = set(range(DIR_BLOCKS))
    for e in entries:
        if e[0] != 0xE5:
            used.update(b for b in e[16:32] if b)
    payload = amsdos_header(name, len(data), load) + bytes(data)
    nb_blocks = -(-len(payload) // BLOCK_SIZE)
    free = [b for b in range(disk.max_blocks()) if b not in used]
    if nb_blocks > len(free):
        raise ValueError("disquette pleine : il faut %d Ko, il reste %d Ko"
                         % (nb_blocks, len(free)))
    blocks = free[:nb_blocks]
    for i, b in enumerate(blocks):
        disk.write_block(b, payload[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE])
    # Une entrée de catalogue (« extent ») couvre 16 blocs = 16 Ko
    records_total = -(-len(payload) // 128)
    free_entries = [e for e in entries if e[0] == 0xE5]
    nb_ext = -(-nb_blocks // 16)
    if nb_ext > len(free_entries):
        raise ValueError("catalogue plein (64 entrées)")
    for x in range(nb_ext):
        e = free_entries[x]
        e[:] = bytes(32)
        e[0] = 0                                # utilisateur 0
        e[1:9] = base
        e[9:12] = ext
        e[12] = x                               # numéro d'extent
        e[15] = min(128, records_total - 128 * x)
        part = blocks[16 * x:16 * (x + 1)]
        e[16:16 + len(part)] = bytes(part)
    disk.write_dir(entries)
    open(dsk_path, "wb").write(disk.raw)
    return len(payload)


def read_file(dsk_path, name, keep_header=False):
    """Relit un fichier ; renvoie les données sans l'en-tête AMSDOS."""
    disk = Disk(open(dsk_path, "rb").read())
    base, ext = amsdos_name(name)
    parts = sorted((e[12], e) for e in disk.read_dir() if _matches(e, base, ext))
    if not parts:
        raise FileNotFoundError(name + " absent de la disquette")
    raw = bytearray()
    for _, e in parts:
        chunk = bytearray()
        for b in e[16:32]:
            if b:
                chunk += disk.read_block(b)
        raw += chunk[:e[15] * 128]
    if keep_header:
        return bytes(raw)
    h = raw[:128]
    if struct.unpack_from("<H", h, 67)[0] == sum(h[:67]) & 0xFFFF:
        length = h[64] | h[65] << 8 | h[66] << 16
        return bytes(raw[128:128 + length])
    return bytes(raw)                           # fichier sans en-tête


def list_files(dsk_path):
    disk = Disk(open(dsk_path, "rb").read())
    files = {}
    for e in disk.read_dir():
        if e[0] == 0xE5:
            continue
        n = (bytes(e[1:9]).decode().strip() + "." +
             bytes(b & 0x7F for b in e[9:12]).decode().strip())
        files[n] = files.get(n, 0) + e[15] * 128
    return files


def main():
    p = argparse.ArgumentParser(description="Ajoute des fichiers à une disquette CPC")
    p.add_argument("dsk")
    p.add_argument("fichiers", nargs="*")
    p.add_argument("--list", action="store_true", help="affiche le catalogue")
    a = p.parse_args()
    for f in a.fichiers:
        n = add_file(a.dsk, os.path.basename(f), open(f, "rb").read())
        print("%s ajouté à %s (%d octets avec en-tête)" % (os.path.basename(f), a.dsk, n))
    if a.list or not a.fichiers:
        for n, size in list_files(a.dsk).items():
            print("  %-12s %6d octets" % (n, size))


if __name__ == "__main__":
    sys.exit(main())
