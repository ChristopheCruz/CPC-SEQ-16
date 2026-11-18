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
;   bloc v2       16 octets : mode de lecture des samples (0 = BLOQUANT),
;                 nom de la banque .SMP associée (8 caractères, 0 = aucune),
;                 7 octets de réserve
;
; Version 1 (avant les digidrums) : sans le bloc v2.  On la charge encore :
; le bloc v2 prend alors ses valeurs par défaut.
; ============================================================================

NB_INST equ 32                  ; nombre d'instruments
NB_SONS equ 8                   ; nombre de sons composés
NB_PAT  equ 32                  ; nombre de motifs

SONG_FIXED equ 16+NB_INST*16+NB_INST*6+NB_SONS*16    ; tout sauf les motifs
SONG_EXTRA equ 16                ; taille du bloc v2
SONG_V1    equ SONG_FIXED+NB_PAT*PAT_SIZE   ; taille d'un morceau version 1
SONG_SIZE  equ SONG_V1+SONG_EXTRA           ; taille d'un morceau version 2
SONG_VER   equ 2                ; version écrite dans l'en-tête

; Remet le morceau dans son état d'usine
init_song:
        ld hl,factory_rle       ; en-tête, instruments, noms, sons composés,
        ld de,song_data         ; compressés (voir factory.asm)
is_rle:
        ld a,(hl)
        inc hl
        or a
        jr nz,is_lit            ; octet ordinaire
        ld b,(hl)               ; 0, n : n zéros
        inc hl
        inc b
        dec b
        jr z,is_rle_end         ; 0, 0 : fin
is_zero:
        ld (de),a               ; (A = 0)
        inc de
        djnz is_zero
        jr is_rle
is_lit:
        ld (de),a
        inc de
        jr is_rle
is_rle_end:
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
        ld hl,song_v2        ; bloc v2 : mode BLOQUANT, pas de banque
        ld b,SONG_EXTRA
is_extra:
        ld (hl),0
        inc hl
        djnz is_extra
        ld hl,factory_cells     ; puis les 2 motifs de démonstration, case
fc_loop:                        ; par case (voir factory.asm)
        ld a,(hl)               ; A = numéro de case
        cp #FF
        ret z                   ; fin de la liste
        inc hl
        push hl
        ld e,a                  ; E = numéro (bit 7 : en-tête du motif)
        rlca
        rlca
        and 1                   ; A = motif (bit 6 du numéro)
        bit 7,e
        jr z,fc_cell
        ld a,e                  ; en-tête : motif = numéro - #80
        and #7F
fc_cell:
        call pat_addr           ; HL = début du motif
        bit 7,e
        jr nz,fc_put            ; en-tête : on écrit au début du motif
        ld a,e                  ; case : 4 + 4 x (numéro modulo 64)
        and 63
        inc a
        add a,a
        add a,a
        ld e,a
        ld d,0
        add hl,de
fc_put:
        ex de,hl                ; DE = destination
        pop hl                  ; HL = les 2 octets à écrire
        ldi                     ; note (ou mode)
        ldi                     ; instrument (ou tempo)
        jr fc_loop

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
