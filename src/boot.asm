; ============================================================================
; SEQ-16 - Le démarrage : ce qui ne sert qu'une fois
;
; Ce code et les données d'usine (factory.asm) sont rangés à la fin de
; SEQ16.BIN, mais assemblés pour tourner en BOOT_RUN, en haut du tampon
; d'AMSDOS (io_buffer, libre au démarrage, après les 3 motifs que
; factory_build y prépare).  Le démarrage les y recopie, construit le morceau
; d'usine, le range dans le bloc 5 (factory_save) ; le morceau (song_data)
; et le tampon les recouvrent ensuite.  init_song (song.asm) relit le bloc 5 :
; la mémoire principale ne garde ni ces données, ni ce code.
; ============================================================================

; Construit le morceau d'usine (une seule fois, au démarrage) : le bloc
; compressé de factory.asm, 3 motifs préparés dans io_buffer, puis les 32
; motifs dans le bloc 4
factory_build:
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
        jp pa_add


; Range le morceau d'usine (song_data et les 32 motifs) dans le bloc 5
factory_save:
        ld hl,song_data
        ld de,B5_SONG
        ld bc,song_end-song_data
        ld a,RAM_FACT
        call bank_copy
        ld de,RAM_SONG*256+RAM_FACT
        jp pats_copy

        include 'factory.asm'
