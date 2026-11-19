; ============================================================================
; Adresses des routines du firmware du CPC (le "système" en ROM).
; On les appelle avec CALL ; elles marchent sur 464, 664 et 6128.
; ============================================================================

KM_WAIT_CHAR      equ #BB06   ; attend une frappe au clavier -> A = caractère
KM_READ_CHAR      equ #BB09   ; Carry si une frappe attend -> A = caractère
KM_TEST_KEY       equ #BB1E   ; A = numéro de touche -> NZ si elle est enfoncée
TXT_OUTPUT        equ #BB5A   ; affiche le caractère contenu dans A
TXT_SET_CURSOR    equ #BB75   ; H = colonne (1-40), L = ligne (1-25)
TXT_WIN_ENABLE    equ #BB66   ; H = colonne gauche, D = droite, L = haut, E = bas
TXT_CLEAR_WINDOW  equ #BB6C   ; efface la fenêtre de texte
TXT_CUR_ON        equ #BB81   ; montre le curseur de texte
TXT_CUR_OFF       equ #BB84   ; cache le curseur de texte
TXT_SET_PEN       equ #BB90   ; A = numéro d'encre pour le texte
TXT_SET_PAPER     equ #BB96   ; A = numéro d'encre pour le fond du texte
SCR_SET_MODE      equ #BC0E   ; A = mode écran (0, 1 ou 2)
SCR_SET_INK       equ #BC32   ; A = encre, B et C = couleur (deux fois la même)
SCR_SET_BORDER    equ #BC38   ; B et C = couleur de la bordure
; Disquette (AMSDOS).  Toutes renvoient Carry = 1 si tout s'est bien passé.
CAS_IN_OPEN       equ #BC77   ; B = longueur du nom, HL = nom, DE = tampon 2 Ko
                              ;   -> BC = longueur du fichier
CAS_IN_CLOSE      equ #BC7A
CAS_IN_CHAR       equ #BC80   ; -> A = octet suivant du fichier ouvert,
                              ; Carry = 0 à la fin (garde BC, DE, HL)
CAS_IN_ABANDON    equ #BC7D
CAS_IN_DIRECT     equ #BC83   ; HL = adresse où charger le fichier
CAS_OUT_OPEN      equ #BC8C   ; B = longueur du nom, HL = nom, DE = tampon 2 Ko
CAS_OUT_CLOSE     equ #BC8F
CAS_OUT_ABANDON   equ #BC92
CAS_OUT_DIRECT    equ #BC98   ; HL = adresse, DE = longueur, BC = 0, A = 2
CAS_CATALOG       equ #BC9B   ; DE = tampon 2 Ko : affiche le catalogue
KL_INIT_BACK      equ #BCCE   ; C = numéro de ROM, DE et HL = mémoire libre
KL_FIND_COMMAND   equ #BCD4   ; HL = nom d'une commande (RSX) -> Carry si
                              ;   trouvée, HL = adresse, C = numéro de ROM
KL_TIME_PLEASE    equ #BD0D   ; -> DEHL = temps écoulé, en 1/300 s
MC_WAIT_FLYBACK   equ #BD19   ; attend le début de l'image suivante (50 fois/s)
MC_SOUND_REGISTER equ #BD34   ; A = registre du circuit sonore AY, C = valeur

; Numéros de touches : ce sont des POSITIONS sur le clavier, pas des lettres.
; Ils sont donc identiques sur un clavier AZERTY et sur un clavier QWERTY.
KEY_UP    equ 0
KEY_DOWN  equ 2
KEY_ESC   equ 66

; Couleurs du CPC (numéros du firmware)
COL_BLEU   equ 1
COL_ORANGE equ 15
