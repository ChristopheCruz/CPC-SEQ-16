; ============================================================================
; SEQ-16 - Le morceau : tout ce qui est sauvegardé sur disquette
;
; Le fichier .SNG est l'image, octet pour octet, du bloc 4 de la mémoire
; supplémentaire (voir bank.asm) : on le sauve et on le charge d'un seul
; tenant.  En mémoire principale, il n'y a que la copie de travail de tout
; sauf les motifs, et le motif affiché (pat_work).
;
;   en-tête       16 octets : "SQ16", version, volume des 4 voix, voix muettes
;   instruments   32 x 16 octets
;   noms          32 x 6 caractères
;   sons composés  8 x 16 octets
;   motifs        32 x 260 octets
;   bloc v2       16 octets : mode de lecture des samples (0 = BLOQUANT),
;                 nom de la banque .SMP associée (8 caractères, 0 = aucune),
;                 7 octets de réserve
;   bloc v3       450 octets : l'enchaînement (panneau SONG, songpanel.asm)
;                 nombre de positions, position de la boucle,
;                 64 positions x (motif, répétitions, transposition),
;                 32 noms de motifs de 8 caractères
;
; Version 1 (avant les digidrums) : sans le bloc v2 ; version 2 : sans le
; bloc v3.  On les charge encore : les blocs absents prennent leurs valeurs
; par défaut (une position par motif utilisé).
; ============================================================================

NB_INST equ 32                  ; nombre d'instruments
NB_SONS equ 8                   ; nombre de sons composés
NB_PAT  equ 32                  ; nombre de motifs

SONG_FIXED equ 16+NB_INST*16+NB_INST*6+NB_SONS*16    ; tout sauf les motifs
SONG_EXTRA equ 16                ; taille du bloc v2
SONG_V1    equ SONG_FIXED+NB_PAT*PAT_SIZE   ; taille d'un morceau version 1
SONG_SIZE  equ SONG_V1+SONG_EXTRA           ; taille d'un morceau version 2
SONG_V3_LEN equ 2+64*3+NB_PAT*8             ; bloc v3 : 450 octets
SONG_SIZE3 equ SONG_SIZE+SONG_V3_LEN        ; taille d'un morceau version 3
SONG_VER   equ 4                ; version écrite dans l'en-tête (le fichier
                                ; garde aussi la banque de samples : sngio.asm)

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
        ld hl,io_buffer         ; 3 motifs vides, en voix séparées, à 125 BPM,
        ld c,3                  ; dans le tampon d'AMSDOS (libre ici) : les
is_pat:                         ; 2 de démonstration, puis un vide
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
        jr z,fc_end             ; fin de la liste
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
        push de                 ; (stage_addr écrase DE, et E est le numéro
        call stage_addr         ; de la case : sans cela, toutes les cases du
        pop de                  ; 2e motif tombaient sur la même)
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

fc_end:                         ; les 32 motifs vont dans le bloc 4 : les 2 de
        xor a                   ; démonstration, puis 30 fois le motif vide
fc_bank:
        push af
        cp 2
        jr c,fc_demo
        ld a,2
fc_demo:
        call stage_addr         ; HL = motif préparé
        pop af
        push af
        push hl
        call pat_addr           ; HL = sa place dans le bloc 4
        ex de,hl
        pop hl
        ld bc,PAT_SIZE
        ld a,RAM_SONG
        call bank_copy
        pop af
        inc a
        cp NB_PAT
        jr nz,fc_bank
        jp song_default         ; une position par motif utilisé

; HL = motif numéro A (0 à 2) préparé dans io_buffer par init_song
stage_addr:
        ld hl,io_buffer
        jr pa_add

; HL = adresse du motif numéro A (0 à 31) dans le bloc 4 (voir bank.asm)
pat_addr:
        ld hl,BANK_PATS
pa_add:
        or a
        ret z
        ld de,PAT_SIZE
pa_loop:
        add hl,de
        dec a
        jr nz,pa_loop
        ret

; Le motif numéro A (0 à 31) vient du bloc 4 dans pat_work.  -> HL = pat_work
pat_fetch:
        call pat_addr
        ld de,pat_work
        ld bc,PAT_SIZE
        ld a,RAM_SONG
        call bank_copy
        ld hl,pat_work
        ret

; pat_work retourne dans le bloc 4, à la place du motif cur_pat
pat_store:
        ld a,(cur_pat)
        call pat_addr
        ex de,hl
        ld hl,pat_work
        ld bc,PAT_SIZE
        ld a,RAM_SONG
        jp bank_copy

; Met à jour l'image du morceau dans le bloc 4, avant une sauvegarde : le
; motif affiché, l'en-tête, les instruments, les noms, les sons et le bloc v2
song_to_bank:
        ld a,SONG_VER           ; l'en-tête annonce la version écrite
        ld (song_data+4),a
        call pat_store
        ld hl,song_data
        ld de,BANK_SONG
        ld bc,SONG_FIXED
        call bank_put
        ld hl,song_v2
        ld de,BANK_V2
        ld bc,SONG_EXTRA
        call bank_put
        ld hl,song_v3           ; l'enchaînement
        ld de,BANK_V3
        ld bc,SONG_V3_LEN
        jp bank_put

; song_data et song_v2 sont en #4000-#7FFF, que cache le bloc 4 : on ne peut
; pas les copier directement avec bank_copy.  On passe par io_buffer (hors
; de la fenêtre, libre en dehors des lectures et écritures de fichier).
; BC <= 2048 octets.

; HL (mémoire principale, n'importe où) -> DE (bloc 4)
bank_put:
        push de
        push bc
        ld de,io_buffer
        ldir
        pop bc
        pop de
        ld hl,io_buffer
        ld a,RAM_SONG
        jp bank_copy

; HL (bloc 4) -> DE (mémoire principale, n'importe où)
bank_get:
        push de
        push bc
        ld de,io_buffer
        ld a,RAM_SONG
        call bank_copy
        pop bc
        pop de
        ld hl,io_buffer
        ldir
        ret
