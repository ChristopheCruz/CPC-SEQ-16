; ============================================================================
; SEQ-16 - Le démarrage : ce qui ne sert qu'une fois
;
; Ce code et les données d'usine (factory.asm : instruments, noms, sons
; composés ; factory_song.asm : SYNTH, la song synthwave) sont rangés à la
; fin de SEQ16.BIN, mais assemblés pour tourner en BOOT_RUN, dans le tampon
; d'AMSDOS (io_buffer, libre au démarrage).  Le démarrage les y recopie,
; construit le morceau d'usine, le range dans le bloc 5 (factory_save) ; le
; tampon les recouvre ensuite.  init_song (song.asm) relit le bloc 5 : la
; mémoire principale ne garde ni ces données, ni ce code.
; ============================================================================

; Construit le morceau d'usine (une seule fois, au démarrage)
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
        ld hl,song_v2           ; bloc v2 : mode BLOQUANT, pas de banque
        ld b,SONG_EXTRA
is_extra:
        ld (hl),0
        inc hl
        djnz is_extra
        di                      ; les 32 motifs de SYNTH, droit dans le bloc 4
        ld bc,#7F00+RAM_SONG    ; (ce code et ses données sont au-dessus de
        out (c),c               ; #8000 : rien à nous n'est caché)
        ld hl,factory_pats_lz
        ld de,BANK_PATS
        ld bc,NB_PAT*PAT_SIZE
        call fb_unlz
        ld bc,#7F00+RAM_NORMAL
        out (c),c
        ei
        ld hl,factory_v3_lz     ; l'enchaînement et les noms des motifs
        ld de,song_v3
        ld bc,SONG_V3_LEN
        ; continue dans fb_unlz

; Décompresse HL vers DE, BC octets en tout.  Jetons (tools/gen_screen.py,
; lz_pack) : c < 128 : c + 1 octets bruts ; c >= 128 : c - 125 octets copiés
; depuis DE - d (d : les 2 octets qui suivent).
fb_unlz:
        ex de,hl                ; fbu_end = DE + BC : la fin
        push hl
        add hl,bc
        ld (fbu_end),hl
        pop hl
        ex de,hl
fbu_token:
        ld a,(hl)
        inc hl
        bit 7,a
        jr nz,fbu_copy
        inc a                   ; octets bruts
        ld c,a
        ld b,0
        ldir
        jr fbu_next
fbu_copy:
        sub 125                 ; A = longueur (3 à 130)
        ld c,a
        ld b,0
        ld a,(hl)               ; d
        inc hl
        push hl
        ld h,(hl)
        ld l,a
        ld a,e                  ; HL = DE - d
        sub l
        ld l,a
        ld a,d
        sbc a,h
        ld h,a
        ldir
        pop hl
        inc hl
fbu_next:
        push hl                 ; arrivé à la fin ?
        ld hl,(fbu_end)
        or a
        sbc hl,de
        pop hl
        jr nz,fbu_token
        ret

fbu_end: dw 0

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
        include 'factory_song.asm'
