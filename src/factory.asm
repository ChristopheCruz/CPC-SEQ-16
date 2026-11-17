; Fichier généré par tools/gen_factory.py - ne pas modifier à la main.
; Contenu d'usine du morceau, recopié en mémoire au démarrage.
; L'ordre et les tailles doivent suivre le bloc 'morceau' de song.asm.

factory:
; En-tête : signature, version, volume des voix A, B, C, N, voix muettes, réserve
        db "SQ16",2, 15,15,15,15, 0, 0,0,0,0,0,0

; Instruments : 16 octets chacun (voir sound.asm)
        db 255,  8, 10, 12, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ;  1 LEAD
        db 255, 16, 12, 24, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ;  2 BASS
        db   6,  2, 12,  4, 13,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ;  3 PAD
        db 255, 10,  0, 10, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ;  4 PLUCK
        db 255, 48,  0, 48, 12,  2,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0   ;  5 HAT
        db 255, 20,  0, 20, 15,  3, 10,  0,  0,  0,  0,  0,  0,  0,  0,  0   ;  6 SNARE
        db 255,  0, 15,255, 15,  4,  0,  8,  4,  0,  0,  0,  0,  0,  0,  0   ;  7 BUZZ
        db 255,  8, 11, 12, 15,  1,  0,  0,  0,  4,  7,  2,  0,  0,  0,  0   ;  8 ARP
        db 255,  8, 12, 10, 15,  1,  0,  0,  0,  0,  0,  0,  3, 32, 15,  0   ;  9 VIBRA
        db 255,  9,  0,  9, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  6   ; 10 LASER
        db 255,  4, 13,  4, 15,  9,  0,  0,  0,  0,  0,  0,  0,  0,  0,  8   ; 11 PORTA
        db 255, 28,  0, 28, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0, 24   ; 12 KICK
        db 255, 14,  0, 14, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  5   ; 13 TOM
        db 255, 30,  0, 30, 15,  2,  6,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 14 CLAP
        db 255,  0, 15, 40, 13,  1,  0,  0,  0, 12,  0,  1,  0,  0,  0,  0   ; 15 ORGAN
        db 255,  4,  0,  4, 15,  1,  0,  0,  0,  7, 12,  1,  0,  0,  0,  0   ; 16 BELL
        db 255,  8, 11, 12, 15,  1,  0,  0,  0,  3,  7,  2,  0,  0,  0,  0   ; 17 ARPMIN
        db 255, 12,  0, 12, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,248   ; 18 ZAP
        db 255,  0, 15, 20, 13,  1,  0,  0,  0,  0,  0,  0,  6,  8,  0,  0   ; 19 SIREN
        db 255,  0, 15,255, 15,  4,  0, 10,  5,  0,  0,  0,  0,  0,  0,  0   ; 20 BUZZTR
        db  40,  4,  9,  8, 12,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 21 SOFT
        db 255, 40,  6, 30, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 22 STAB
        db 255,  4,  0,  4, 13,  2,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 23 CYMBAL
        db 255,  0, 15, 20, 14,  1,  0,  0,  0,  0,  0,  0,  5, 20,  0,  0   ; 24 WOBBLE
        db 255,  8, 10, 12, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 25 USER1
        db 255,  8, 10, 12, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 26 USER2
        db 255,  8, 10, 12, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 27 USER3
        db 255,  8, 10, 12, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 28 USER4
        db 255,  8, 10, 12, 15, 16,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 29 DGKICK
        db 255,  8, 10, 12, 15, 16,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 30 DGSNAR
        db 255,  8, 10, 12, 15, 16,  2,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 31 DGHAT
        db 255,  8, 10, 12, 15, 16,  3,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 32 DGCLAP

; Noms des instruments : 6 caractères chacun
        db "LEAD  BASS  PAD   PLUCK "
        db "HAT   SNARE BUZZ  ARP   "
        db "VIBRA LASER PORTA KICK  "
        db "TOM   CLAP  ORGAN BELL  "
        db "ARPMINZAP   SIREN BUZZTR"
        db "SOFT  STAB  CYMBALWOBBLE"
        db "USER1 USER2 USER3 USER4 "
        db "DGKICKDGSNARDGHAT DGCLAP"

; Sons composés : pour chaque voix  décalage, instrument, volume ; puis 4 octets de réserve
        db   0,  0,#FF,   3,  0,#FF,   7,  0,#FF,   0,#FF,#FF, 0,0,0,0   ; accord mineur
        db   0,  0,#FF,   4,  0,#FF,   7,  0,#FF,   0,#FF,#FF, 0,0,0,0   ; accord majeur
        db   0,  1,#FF,  12,  3,#FF,   0,#FF,#FF,  12,  5,#FF, 0,0,0,0   ; basse + percussion
        db   0,  0,#FF,   7,  0,#FF,  12,  0,#FF,   0,#FF,#FF, 0,0,0,0   ; quinte + octave
        db   0,  1,#FF,  12,  0,#FF,  24,  3,#FF,   0,#FF,#FF, 0,0,0,0   ; trois octaves
        db   0,  2,#FF,   5,  2,#FF,   7,  2,#FF,   0,#FF,#FF, 0,0,0,0   ; accord sus4
        db   0, 20,#FF,   3, 20,#FF,  10, 20,#FF,   0,#FF,#FF, 0,0,0,0   ; accord mineur 7
        db   0, 11,#FF,   0,#FF,#FF,   0,#FF,#FF,   1,  4,#FF, 0,0,0,0   ; grosse caisse + hat

; Les 2 motifs de démonstration, case par case : numéro de case
; (motif x 64 + pas x 4 + voix), note, instrument ; volume #FF, effet 0.
; #80 + motif : en-tête (mode, tempo).  #FF : fin.
factory_cells:

; Motif 1 : voix séparées
        db #80,0,125   ; en-tête : mode, tempo
        db   0, 24,  1   ; pas 0, voix 0
        db   1, 48,  0   ; pas 0, voix 1
        db   3, 31,  5   ; pas 0, voix 3
        db   4,254,  0   ; pas 1, voix 0
        db   9, 51,  0   ; pas 2, voix 1
        db  10, 43,  3   ; pas 2, voix 2
        db  11,  1,  4   ; pas 2, voix 3
        db  12, 24,  1   ; pas 3, voix 0
        db  13, 55,  0   ; pas 3, voix 1
        db  16,254,  0   ; pas 4, voix 0
        db  19, 12,  5   ; pas 4, voix 3
        db  24, 27,  1   ; pas 6, voix 0
        db  25, 58,  0   ; pas 6, voix 1
        db  26, 43,  3   ; pas 6, voix 2
        db  27,  1,  4   ; pas 6, voix 3
        db  28,254,  0   ; pas 7, voix 0
        db  32, 24,  1   ; pas 8, voix 0
        db  33, 55,  0   ; pas 8, voix 1
        db  35, 31,  5   ; pas 8, voix 3
        db  36,254,  0   ; pas 9, voix 0
        db  42, 44,  3   ; pas A, voix 2
        db  43,  1,  4   ; pas A, voix 3
        db  44, 29,  1   ; pas B, voix 0
        db  45, 53,  0   ; pas B, voix 1
        db  48,254,  0   ; pas C, voix 0
        db  49, 51,  0   ; pas C, voix 1
        db  51, 12,  5   ; pas C, voix 3
        db  56, 31,  1   ; pas E, voix 0
        db  57, 50,  0   ; pas E, voix 1
        db  58, 43,  3   ; pas E, voix 2
        db  59,  1,  4   ; pas E, voix 3
        db  60,254,  0   ; pas F, voix 0

; Motif 2 : son composé
        db #81,1,125   ; en-tête : mode, tempo
        db  64, 36,  0   ; pas 0, voix 0
        db  76,254,  0   ; pas 3, voix 0
        db  80, 36,  2   ; pas 4, voix 0
        db  88, 39,  1   ; pas 6, voix 0
        db  92,254,  0   ; pas 7, voix 0
        db  96, 41,  0   ; pas 8, voix 0
        db 108,254,  0   ; pas B, voix 0
        db 112, 43,  1   ; pas C, voix 0
        db 120, 43,  2   ; pas E, voix 0
        db 124,254,  0   ; pas F, voix 0
        db #FF
