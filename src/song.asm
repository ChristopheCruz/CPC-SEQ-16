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

; Remet le morceau dans son état d'usine : relu dans le bloc 5, où
; factory_save l'a rangé au démarrage (boot.asm)
init_song:
        ld hl,B5_SONG
        ld de,song_data
        ld bc,song_end-song_data
        ld a,RAM_FACT
        call bank_copy
        ld de,RAM_FACT*256+RAM_SONG
        ; continue dans pats_copy

; Copie les 32 motifs du bloc D vers le bloc E (aux mêmes adresses), un par
; un, par pat_work (hors de #4000-#7FFF)
pats_copy:
        ld (pcp_dst),de         ; pcp_dst = E, pcp_src = D
        xor a
pcp_loop:
        ld (pcp_n),a
        call pat_addr           ; HL = le motif, dans l'un ou l'autre bloc
        ld (pcp_addr),hl
        ld de,pat_work
        ld bc,PAT_SIZE
        ld a,(pcp_src)
        call bank_copy
        ld hl,pat_work
        ld de,(pcp_addr)
        ld bc,PAT_SIZE
        ld a,(pcp_dst)
        call bank_copy
        ld a,(pcp_n)
        inc a
        cp NB_PAT
        jr nz,pcp_loop
        ret

pcp_dst:  db 0
pcp_src:  db 0
pcp_n:    db 0
pcp_addr: dw 0

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
        push af
        xor a                   ; une copie fraîche : rien à ranger
        ld (pat_dirty),a
        pop af
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
