"""Format des banques d'instruments SEQ-16 (.INS).

Une banque .INS est le début d'un morceau .SNG, sans les motifs :

    en-tête         16 octets : "SQ16", version 1, volumes A B C N, voix
                    muettes, 6 octets de réserve
    instruments     32 x 16 octets (format de src/sound.asm)
    noms            32 x 6 caractères
    sons composés    8 x 16 octets

soit 848 octets (SONG_FIXED dans src/song.asm).  Le programme la sauve d'un
seul tenant (f3, touche I) et la relit en sautant l'en-tête (f3, touche O ;
f2, touche O pour un seul son).

Les octets d'un instrument (src/sound.asm) :

    0 attaque (255 = immédiat)      1 déclin           2 tenue (0-15)
    3 relâche                       4 volume (0-15)    5 drapeaux
    6 période du bruit (0-31)       7 forme de l'enveloppe matérielle
    8 division de l'enveloppe       9 arpège note 2   10 arpège note 3
   11 vitesse de l'arpège          12 vibrato prof.   13 vibrato vitesse
   14 vibrato attente              15 glissando (signé)

Drapeaux : bit 0 ton, bit 1 bruit, bit 2 enveloppe matérielle, bit 3
portamento.
"""

NB_INST = 32                     # instruments par banque
NB_SONS = 8                      # sons composés par banque
INS_LEN = 16                     # octets par instrument
NAME_LEN = 6                     # caractères par nom
HEADER = b"SQ16"                 # signature commune avec les morceaux
INS_FILE_LEN = 16 + NB_INST * INS_LEN + NB_INST * NAME_LEN + NB_SONS * 16   # 848

TON, BRUIT, ENV, PORTA = 1, 2, 4, 8          # bits des drapeaux

# Sons composés par défaut (ceux du programme) : décalage, instrument,
# volume pour chacune des 4 voix, puis 4 octets de réserve.  #FF = voix
# libre / volume de l'instrument.
SONS_USINE = [
    bytes([0, 0, 0xFF, 3, 0, 0xFF, 7, 0, 0xFF, 0, 0xFF, 0xFF, 0, 0, 0, 0]),
    bytes([0, 0, 0xFF, 4, 0, 0xFF, 7, 0, 0xFF, 0, 0xFF, 0xFF, 0, 0, 0, 0]),
    bytes([0, 1, 0xFF, 12, 3, 0xFF, 0, 0xFF, 0xFF, 12, 5, 0xFF, 0, 0, 0, 0]),
    bytes([0, 0, 0xFF, 7, 0, 0xFF, 12, 0, 0xFF, 0, 0xFF, 0xFF, 0, 0, 0, 0]),
    bytes([0, 1, 0xFF, 12, 0, 0xFF, 24, 3, 0xFF, 0, 0xFF, 0xFF, 0, 0, 0, 0]),
    bytes([0, 2, 0xFF, 5, 2, 0xFF, 7, 2, 0xFF, 0, 0xFF, 0xFF, 0, 0, 0, 0]),
    bytes([0, 20, 0xFF, 3, 20, 0xFF, 10, 20, 0xFF, 0, 0xFF, 0xFF, 0, 0, 0, 0]),
    bytes([0, 11, 0xFF, 0, 0xFF, 0xFF, 0, 0xFF, 0xFF, 1, 4, 0xFF, 0, 0, 0, 0]),
]


def clean_name(name):
    """Nom affichable sur le CPC : 6 caractères, majuscules, chiffres, '-'."""
    out = "".join(c for c in name.upper() if c.isalnum() or c in "-")
    return out[:NAME_LEN].ljust(NAME_LEN)


def build_ins_bank(sounds, sons=None, volumes=(15, 15, 15, 15)):
    """Construit une banque .INS.

    sounds : liste de (nom, 16 octets) ; complétée jusqu'à 32 par des sons
    silencieux nommés "-".  sons : 8 sons composés de 16 octets (par défaut
    ceux du programme).
    """
    if len(sounds) > NB_INST:
        raise ValueError(f"{len(sounds)} sons : 32 au plus par banque")
    sounds = list(sounds) + [("-", bytes(INS_LEN))] * (NB_INST - len(sounds))
    sons = list(sons or SONS_USINE)
    if len(sons) != NB_SONS:
        raise ValueError("il faut 8 sons composés")
    head = HEADER + bytes([1]) + bytes(volumes) + bytes(7)
    data = bytearray(head)
    for name, ins in sounds:
        ins = bytes(ins)
        if len(ins) != INS_LEN:
            raise ValueError(f"{name} : un instrument fait 16 octets")
        data += ins
    for name, _ in sounds:
        data += clean_name(name).encode("ascii")
    for s in sons:
        if len(s) != 16:
            raise ValueError("un son composé fait 16 octets")
        data += bytes(s)
    assert len(data) == INS_FILE_LEN
    return bytes(data)


def parse_ins_bank(data):
    """Relit une banque .INS -> (liste de (nom, 16 octets), sons composés)."""
    if len(data) != INS_FILE_LEN or data[:4] != HEADER:
        raise ValueError("ce n'est pas une banque .INS de SEQ-16")
    ins0 = 16
    names0 = ins0 + NB_INST * INS_LEN
    sons0 = names0 + NB_INST * NAME_LEN
    sounds = []
    for i in range(NB_INST):
        name = data[names0 + i * NAME_LEN:names0 + (i + 1) * NAME_LEN].decode("ascii")
        sounds.append((name, data[ins0 + i * INS_LEN:ins0 + (i + 1) * INS_LEN]))
    sons = [data[sons0 + i * 16:sons0 + (i + 1) * 16] for i in range(NB_SONS)]
    return sounds, sons
