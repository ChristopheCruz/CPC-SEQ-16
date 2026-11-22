; ============================================================================
; SEQ-16 - Le chargeur : l'écran de chargement, puis le programme
;
; Sur la disquette, sous le nom SEQ16 (sans extension) : RUN"SEQ16 cherche
; d'abord le nom sans extension, puis .BAS, puis .BIN ; c'est donc ce
; chargeur qui part.  (RUN"SEQ16.BIN lance toujours le programme seul.)
;
;   1. relance AMSDOS (RUN" d'un binaire a tout réinitialisé, comme pour
;      le programme : voir boot_6128 dans main.asm) ;
;   2. toutes les encres en noir, mode 0, SEQ16.SCR lu en #4000 puis
;      décompressé dans la mémoire écran (#C000, ld_unlz) : l'image apparaît
;      d'un coup avec sa palette (16 Ko d'écran, 2,5 Ko sur la disquette) ;
;   3. charge SEQ16.BIN en #3F00 pendant qu'on regarde l'image ;
;   4. le lance par MC_START_PROGRAM, exactement comme RUN" : le firmware
;      repart de zéro, le programme fait son démarrage habituel (et pose ses
;      propres couleurs, mode 1).
; Pas d'écran (fichier absent) : on charge le programme quand même.
;
; Assemblé à part (build.bat : build/loader.bin), en #A400 : sous la zone
; réservée par AMSDOS (#A67C), au-dessus de SEQ16.BIN (#3F00-#9xxx) et loin
; de l'écran.  Tampon d'AMSDOS en #1000 (mémoire basse, libre ici).
; tools/gen_screen.py le met sur les disquettes avec l'écran.
; ============================================================================

        include 'firmware.asm'

PROG_ADDR equ #3F00             ; SEQ16.BIN : chargé et lancé ici (START)
PACK_ADDR equ #4000             ; l'écran compressé (SEQ16.BIN l'écrase ensuite)
BUF_ADDR  equ #1000             ; 2 Ko de travail pour AMSDOS

        org #A400
loader:
        ld c,7                  ; AMSDOS (ROM 7), comme le programme
        ld de,#0040
        ld hl,#ABFF
        call KL_INIT_BACK
        ld a,#FF                ; pas de message d'erreur disque à l'écran
        ld (#BE78),a
        xor a                   ; toutes les encres en noir
ld_black:
        push af
        ld bc,0
        call SCR_SET_INK
        pop af
        inc a
        cp 16
        jr nz,ld_black
        ld bc,0
        call SCR_SET_BORDER
        xor a
        call SCR_SET_MODE       ; mode 0 (l'écran est effacé)
        ld hl,name_scr          ; l'écran de chargement
        ld b,9
        ld de,BUF_ADDR
        call CAS_IN_OPEN
        jr nc,ld_prog           ; pas d'écran : le programme quand même
        ld hl,PACK_ADDR
        call CAS_IN_DIRECT
        call CAS_IN_CLOSE
        ld hl,PACK_ADDR
        ld de,#C000
        call ld_unlz            ; décompressé dans la mémoire écran
        ld hl,loader_inks       ; sa palette : l'image apparaît
        xor a
ld_ink:
        push af
        push hl
        ld b,(hl)
        ld c,b
        call SCR_SET_INK
        pop hl
        pop af
        inc hl
        inc a
        cp 16
        jr nz,ld_ink
        ld b,(hl)               ; la bordure
        ld c,b
        call SCR_SET_BORDER
ld_prog:
        ld hl,name_bin          ; le programme
        ld b,9
        ld de,BUF_ADDR
        call CAS_IN_OPEN
        jr nc,ld_fail
        ld hl,PROG_ADDR
        call CAS_IN_DIRECT
        call CAS_IN_CLOSE
        ld hl,PROG_ADDR         ; lancé comme par RUN" : tout est remis à
        ld c,#FF                ; zéro (C = #FF : pas de ROM)
        jp MC_START_PROGRAM
ld_fail:
        rst 0                   ; pas de programme : retour au BASIC

; Décompresse HL vers DE (#C000) jusqu'au bout de la mémoire (DE revient à
; 0).  Jetons (voir tools/gen_screen.py, lz_pack) :
;   c < 128   : c + 1 octets bruts
;   c >= 128  : c - 125 octets copiés depuis DE - d (d : 2 octets qui suivent)
ld_unlz:
        ld a,(hl)
        inc hl
        bit 7,a
        jr nz,lzu_copy
        inc a                   ; octets bruts
        ld c,a
        ld b,0
        ldir
        jr lzu_next
lzu_copy:
        sub 125                 ; A = longueur (3 à 130)
        ld c,a
        ld b,0
        ld a,(hl)               ; d
        inc hl
        push hl                 ; (la suite des jetons)
        ld h,(hl)
        ld l,a
        ld a,e                  ; HL = DE - d : ce qui est déjà écrit
        sub l
        ld l,a
        ld a,d
        sbc a,h
        ld h,a
        ldir
        pop hl
        inc hl
lzu_next:
        ld a,d
        or e
        jr nz,ld_unlz
        ret

name_scr: db "SEQ16.SCR"
name_bin: db "SEQ16.BIN"
        include 'loader_inks.asm'
loader_end:
        assert loader_end <= #A67C
