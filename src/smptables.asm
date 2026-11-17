; Fichier généré par tools/gen_smp_tables.py - ne pas modifier à la main.

; Courbes : code lu dans le sample -> code écrit dans le registre de volume.
smp_curves:
        db  0, 0, 0, 0, 0, 1, 1, 2, 2, 3, 4, 6, 7,10,12,15   ; lineaire
        db  0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,15   ; log
        db  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 9,12,14,15,15   ; saturee
        db 14,13,13,13,13,13,13,12,11, 9, 1, 9,12,14,14, 9   ; repliee
        db 15,15,15,15,15,15,15,14,14,14,13,13,12,11, 9, 0   ; inversee

; Hauteur : multiplicateur de la durée d'un échantillon (x/256),
; de -12 à +12 demi-tons.
smp_pitch:
        dw 512,483,456,431,406,384,362,342
        dw 323,304,287,271,256,242,228,215
        dw 203,192,181,171,161,152,144,136
        dw 128

smp_decims:
        db 1,2,3,4,6,8

; Masques pour 4, 3, 2 et 1 bits
smp_masks:
        db #F,#E,#C,#8

smp_bits_txt:
        db "4321"

smp_curve_names:
        db "LINEAIRE"
        db "LOG     "
        db "SATUREE "
        db "REPLIEE "
        db "INVERSEE"
