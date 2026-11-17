; ============================================================================
; SEQ-16 - Le morceau : tout ce qui est sauvegardé sur disquette
;
; Le morceau est un seul bloc de mémoire, placé juste après le programme.
; On le sauve et on le charge d'un seul tenant (fichier .SNG).
;
;   en-tête       16 octets : "SQ16", version, volume des 4 voix, voix muettes
;   instruments   32 x 16 octets
;   noms          32 x 6 caractères
;   sons composés  8 x 16 octets
;   motifs        32 x 260 octets
; ============================================================================

NB_INST equ 32                  ; nombre d'instruments
NB_SONS equ 8                   ; nombre de sons composés
NB_PAT  equ 32                  ; nombre de motifs

SONG_FIXED equ 16+NB_INST*16+NB_INST*6+NB_SONS*16    ; tout sauf les motifs
SONG_SIZE  equ SONG_FIXED+NB_PAT*PAT_SIZE

; Remet le morceau dans son état d'usine
init_song:
        ld hl,factory           ; en-tête, instruments, noms, sons composés
        ld de,song_data
        ld bc,SONG_FIXED
        ldir
        ld hl,patterns          ; tous les motifs vides, en voix séparées,
        ld c,NB_PAT             ; à 125 BPM
is_pat:
        ld (hl),0               ; mode
        inc hl
        ld (hl),125             ; tempo
        inc hl
        ld (hl),0
        inc hl
        ld (hl),0
        inc hl
        ld b,64                 ; 16 pas x 4 voix
is_cell:
        ld (hl),NOTE_NONE
        inc hl
        ld (hl),0
        inc hl
        ld (hl),#FF
        inc hl
        ld (hl),0
        inc hl
        djnz is_cell
        dec c
        jr nz,is_pat
        ld hl,factory_patterns  ; puis les 2 motifs de démonstration
        ld de,patterns
        ld bc,2*PAT_SIZE
        ldir
        ret

; HL = adresse du motif numéro A (0 à 31)
pat_addr:
        ld hl,patterns
        or a
        ret z
        ld de,PAT_SIZE
pa_loop:
        add hl,de
        dec a
        jr nz,pa_loop
        ret
