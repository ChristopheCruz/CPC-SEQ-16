; Fichier généré par tools/gen_factory.py - ne pas modifier à la main.
; Contenu d'usine du morceau, recopié en mémoire au démarrage.
; L'ordre et les tailles doivent suivre le bloc 'morceau' de song.asm.

factory:
; En-tête : signature, version, volume des voix A, B, C, N, voix muettes, réserve
        db "SQ16",1, 15,15,15,15, 0, 0,0,0,0,0,0

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
        db 255,  8, 10, 12, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 29 USER5
        db 255,  8, 10, 12, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 30 USER6
        db 255,  8, 10, 12, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 31 USER7
        db 255,  8, 10, 12, 15,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0   ; 32 USER8

; Noms des instruments : 6 caractères chacun
        db "LEAD  BASS  PAD   PLUCK "
        db "HAT   SNARE BUZZ  ARP   "
        db "VIBRA LASER PORTA KICK  "
        db "TOM   CLAP  ORGAN BELL  "
        db "ARPMINZAP   SIREN BUZZTR"
        db "SOFT  STAB  CYMBALWOBBLE"
        db "USER1 USER2 USER3 USER4 "
        db "USER5 USER6 USER7 USER8 "

; Sons composés : pour chaque voix  décalage, instrument, volume ; puis 4 octets de réserve
        db   0,  0,#FF,   3,  0,#FF,   7,  0,#FF,   0,#FF,#FF, 0,0,0,0   ; accord mineur
        db   0,  0,#FF,   4,  0,#FF,   7,  0,#FF,   0,#FF,#FF, 0,0,0,0   ; accord majeur
        db   0,  1,#FF,  12,  3,#FF,   0,#FF,#FF,  12,  5,#FF, 0,0,0,0   ; basse + percussion
        db   0,  0,#FF,   7,  0,#FF,  12,  0,#FF,   0,#FF,#FF, 0,0,0,0   ; quinte + octave
        db   0,  1,#FF,  12,  0,#FF,  24,  3,#FF,   0,#FF,#FF, 0,0,0,0   ; trois octaves
        db   0,  2,#FF,   5,  2,#FF,   7,  2,#FF,   0,#FF,#FF, 0,0,0,0   ; accord sus4
        db   0, 20,#FF,   3, 20,#FF,  10, 20,#FF,   0,#FF,#FF, 0,0,0,0   ; accord mineur 7
        db   0, 11,#FF,   0,#FF,#FF,   0,#FF,#FF,   1,  4,#FF, 0,0,0,0   ; grosse caisse + hat

; Les 2 motifs de démonstration (260 octets chacun)
factory_patterns:

; Motif 1 : voix séparées
        db 0,125,0,0
        db 24,1,#FF,0, 48,0,#FF,0, #FF,0,#FF,0, 31,5,#FF,0   ; pas 0
        db #FE,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 1
        db #FF,0,#FF,0, 51,0,#FF,0, 43,3,#FF,0, 1,4,#FF,0   ; pas 2
        db 24,1,#FF,0, 55,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 3
        db #FE,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, 12,5,#FF,0   ; pas 4
        db #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 5
        db 27,1,#FF,0, 58,0,#FF,0, 43,3,#FF,0, 1,4,#FF,0   ; pas 6
        db #FE,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 7
        db 24,1,#FF,0, 55,0,#FF,0, #FF,0,#FF,0, 31,5,#FF,0   ; pas 8
        db #FE,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 9
        db #FF,0,#FF,0, #FF,0,#FF,0, 44,3,#FF,0, 1,4,#FF,0   ; pas A
        db 29,1,#FF,0, 53,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas B
        db #FE,0,#FF,0, 51,0,#FF,0, #FF,0,#FF,0, 12,5,#FF,0   ; pas C
        db #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas D
        db 31,1,#FF,0, 50,0,#FF,0, 43,3,#FF,0, 1,4,#FF,0   ; pas E
        db #FE,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas F

; Motif 2 : son composé
        db 1,125,0,0
        db 36,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 0
        db #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 1
        db #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 2
        db #FE,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 3
        db 36,2,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 4
        db #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 5
        db 39,1,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 6
        db #FE,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 7
        db 41,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 8
        db #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas 9
        db #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas A
        db #FE,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas B
        db 43,1,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas C
        db #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas D
        db 43,2,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas E
        db #FE,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0, #FF,0,#FF,0   ; pas F
