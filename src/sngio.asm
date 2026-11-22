; ============================================================================
; SEQ-16 - Le fichier .SNG version 4 : le morceau ET sa banque de samples,
; dans un seul fichier (lot 5 du plan, décision 8 : « tout ce qu'il faut
; pour rejouer le morceau »)
;
;   en-tête AMSDOS  128 octets, écrits par le programme : type binaire et
;                   longueur exacte (AMSDOS la relit, et la fin du fichier
;                   tombe au dernier octet de données)
;   image           SONG_SIZE3 octets : le morceau, comme un .SNG version 3
;                   (octet 4 de son en-tête : version 4)
;   longueur        2 octets : taille de la banque de samples (0 = aucune)
;   banque          la banque, telle qu'en mémoire en #0040
;
; AMSDOS n'écrit d'un coup (CAS OUT DIRECT) qu'un bloc de mémoire contigu ;
; le morceau est dans le bloc 4 et la banque en #0040 : on écrit donc
; octet par octet (CAS OUT CHAR), par paquets de 256 octets copiés du bloc 4
; dans SCRATCH, et on relit de même (CAS IN CHAR).  Les anciens .SNG
; (versions 1 à 3) se relisent d'un coup, comme avant.
; ============================================================================

SIO_CHUNK equ 256

; --- Écriture ---------------------------------------------------------------------
; Sauve NOM.SNG (nom : fname).  L'image du bloc 4 doit être à jour
; (song_to_bank).
sng_write:
        call silence
        ld hl,txt_ext
        call build_filename_ext ; -> fname_full ; NC : nom vide (message affiché)
        ret nc
        ld hl,txt_m_saving
        call dsk_message
        ld hl,0                 ; la banque de samples (s'il y en a une)
        ld a,(smp_count)
        or a
        jr z,sw_len
        ld hl,(smp_bank_len)
sw_len:
        ld (sio_smp),hl
        ld de,SONG_SIZE3+2
        add hl,de
        ld (sio_total),hl
        ld a,(fname_len)
        ld b,a
        ld hl,fname_full
        ld de,io_buffer
        call CAS_OUT_OPEN
        jp nc,disk_error
        call sw_header          ; l'en-tête AMSDOS
        jr nc,sw_fail
        ld hl,BANK_SONG         ; l'image du morceau, depuis le bloc 4
        ld bc,SONG_SIZE3
sw_song:
        call sio_chunk_len      ; DE = taille du paquet ; Z : fini
        jr z,sw_bank
        push hl
        push bc
        push de
        ld b,d
        ld c,e
        ld de,SCRATCH
        ld a,RAM_SONG
        call bank_copy
        pop bc                  ; BC = taille du paquet
        push bc
        ld hl,SCRATCH
        call cas_put_block
        pop de
        pop bc
        pop hl
        jr nc,sw_fail
        add hl,de               ; paquet suivant
        ld a,c
        sub e
        ld c,a
        ld a,b
        sbc a,d
        ld b,a
        jr sw_song
sw_bank:
        ld a,(sio_smp)          ; longueur de la banque, puis la banque
        call cas_put
        jr nc,sw_fail
        ld a,(sio_smp+1)
        call cas_put
        jr nc,sw_fail
        ld hl,BANK_START
        ld bc,(sio_smp)
        call cas_put_block
        jr nc,sw_fail
        call CAS_OUT_CLOSE
        jp nc,disk_error
        ld hl,txt_m_saved
        jp dsk_message
sw_fail:
        jp ds_abandon

; L'en-tête AMSDOS (128 octets) dans SCRATCH, puis dans le fichier :
; nom, type 2 (binaire), longueurs, somme de contrôle des octets 0 à 66
sw_header:
        ld hl,SCRATCH
        ld b,128
swh_zero:
        ld (hl),0
        inc hl
        djnz swh_zero
        ld hl,fname             ; nom (8 caractères, complété d'espaces)
        ld de,SCRATCH+1
        ld bc,NAME_LEN
        ldir
        ld hl,txt_ext+1         ; extension "SNG"
        ld bc,3
        ldir
        ld a,2
        ld (SCRATCH+#12),a      ; type : binaire
        ld a,#FF
        ld (SCRATCH+#17),a      ; premier bloc
        ld hl,(sio_total)
        ld (SCRATCH+#13),hl     ; longueur des données
        ld (SCRATCH+#18),hl     ; longueur logique
        ld (SCRATCH+#40),hl     ; longueur sur 24 bits (octet haut : 0)
        ld hl,SCRATCH
        ld de,0
        ld b,67
swh_sum:
        ld a,(hl)
        add a,e
        ld e,a
        jr nc,swh_nc
        inc d
swh_nc:
        inc hl
        djnz swh_sum
        ld (SCRATCH+#43),de     ; somme de contrôle
        ld hl,SCRATCH
        ld bc,128
        ; continue dans cas_put_block

; Écrit BC octets à partir de HL.  -> Carry = 0 : erreur de disque
cas_put_block:
        ld a,b
        or c
        scf
        ret z
        ld a,(hl)
        call cas_put
        ret nc
        inc hl
        dec bc
        jr cas_put_block

; Écrit l'octet A (garde BC, DE, HL).  -> Carry = 0 : erreur
cas_put:
        push bc
        push de
        push hl
        call CAS_OUT_CHAR
        pop hl
        pop de
        pop bc
        ret

; BC = octets qui restent -> DE = taille du prochain paquet (256 au plus) ;
; Z s'il ne reste rien
sio_chunk_len:
        ld a,b
        or c
        ret z
        ld de,SIO_CHUNK
        ld a,b
        or a
        jr nz,scl_full          ; 256 ou plus
        ld d,0
        ld e,c
scl_full:
        or 1                    ; NZ
        ret

; --- Lecture ------------------------------------------------------------------------
; Le fichier est ouvert (CAS IN OPEN), BC = sa longueur (> SONG_SIZE3) :
; l'image vers le bloc 4, puis la banque vers #0040.
; -> Carry = 1 si tout va bien (fichier fermé), Carry = 0 sinon (fichier
;    abandonné, message affiché)
sng_read:
        ld (sio_total),bc
        ld hl,0                 ; octets lus (pour le message d'erreur)
        ld (sio_count),hl
sr_start:
        ld hl,BANK_SONG
        ld (sio_dst),hl
        ld bc,SONG_SIZE3
sr_loop:
        call sio_chunk_len      ; DE = taille du paquet ; Z : fini
        jr z,sr_bank_len
        ld (sio_n),de
        push bc
        ld hl,SCRATCH           ; le paquet, du fichier vers SCRATCH
        ld b,d
        ld c,e
        call cas_get_block
        jr nc,sr_fail_pop
        ld hl,SCRATCH           ; puis vers le bloc 4
        ld de,(sio_dst)
        ld bc,(sio_n)
        ld a,RAM_SONG
        call bank_copy
        ld hl,(sio_dst)
        ld de,(sio_n)
        add hl,de
        ld (sio_dst),hl
        pop bc
        ld a,c
        sub e
        ld c,a
        ld a,b
        sbc a,d
        ld b,a
        jr sr_loop
sr_fail_pop:
        pop bc
        jr sr_fail
sr_bank_len:
        call cas_get            ; longueur de la banque
        jr nc,sr_fail
        ld (sio_smp),a
        call cas_get
        jr nc,sr_fail
        ld (sio_smp+1),a
        ld hl,(sio_smp)         ; cohérente avec la longueur du fichier ?
        ld de,SONG_SIZE3+2
        add hl,de
        ld de,(sio_total)
        or a
        sbc hl,de
        jr nz,sr_bad
        ld hl,BANK_MAX          ; et assez de place ?
        ld de,(sio_smp)
        or a
        sbc hl,de
        jr c,sr_bad
        ld a,d
        or e
        jr z,sr_close           ; pas de banque dans ce morceau
        ld a,(smp_ok)
        or a
        jr z,sr_close           ; pas de zone haute : samples désactivés
        xor a
        ld (smp_count),a        ; la banque en mémoire n'est plus valable
        ld hl,BANK_START
        ld bc,(sio_smp)
        call cas_get_block
        jr nc,sr_fail
        ld hl,(sio_smp)
        ld (smp_bank_len),hl
        call smp_check          ; -> A = 0 si elle est bonne
        or a
        jr nz,sr_close
        ld hl,BANK_V2+1         ; elle reprend son nom : celui du bloc v2 du
        ld de,SCRATCH           ; fichier, encore dans le bloc 4
        ld bc,8
        ld a,RAM_SONG
        call bank_copy
        ld hl,SCRATCH
        ld a,(hl)
        or a
        jr z,sr_close
        call smp_set_name
sr_close:
        call CAS_IN_CLOSE
        scf
        ret
sr_bad:
        call CAS_IN_ABANDON
        ld hl,txt_m_bad
        call dsk_message
        or a
        ret
sr_fail:
        push af                 ; A = code d'erreur d'AMSDOS
        call CAS_IN_ABANDON
        pop af
        call sng_error
        or a
        ret

; « ERREUR DISQUE (DISQUETTE ? NOM ?) » suivi du code d'erreur d'AMSDOS (A,
; 2 chiffres hexadécimaux) et du nombre d'octets lus (sio_count, 4 chiffres ;
; FFFF : à l'ouverture), pour savoir où et pourquoi le chargement a échoué.
sng_error:
        ld (sio_code),a
        ld hl,txt_m_error
        ld de,err_buf
serr_copy:
        ld a,(hl)
        ld (de),a
        or a
        jr z,serr_end
        inc hl
        inc de
        jr serr_copy
serr_end:
        ex de,hl                ; HL -> le 0 de fin
        ld (hl),' '
        inc hl
        ld a,(sio_code)
        call hex_put
        ld a,(sio_count+1)
        call hex_put
        ld a,(sio_count)
        call hex_put
        ld (hl),0
        ld hl,err_buf
        jp dsk_message

; A en 2 chiffres hexadécimaux vers HL (HL avance de 2)
hex_put:
        push af
        rrca
        rrca
        rrca
        rrca
        call hp_digit
        pop af
hp_digit:
        and 15
        add a,'0'
        cp '9'+1
        jr c,hp_put
        add a,7
hp_put:
        ld (hl),a
        inc hl
        ret

; Lit BC octets vers HL.  -> Carry = 0 : fin de fichier ou erreur
cas_get_block:
        ld a,b
        or c
        scf
        ret z
        call cas_get
        ret nc
        ld (hl),a
        inc hl
        dec bc
        jr cas_get_block

; A = octet suivant (garde BC, DE, HL).  -> Carry = 0 : fin ou erreur
cas_get:
        push bc
        push de
        push hl
        call CAS_IN_CHAR
        pop hl
        pop de
        pop bc
        ret nc
        push hl                 ; un octet de plus de lu
        ld hl,(sio_count)
        inc hl
        ld (sio_count),hl
        pop hl
        scf
        ret

sio_total: dw 0
sio_smp:   dw 0
sio_dst:   dw 0
sio_n:     dw 0
sio_count: dw 0                 ; octets lus (message d'erreur)
sio_code:  db 0                 ; code d'erreur d'AMSDOS
err_buf:   ds 41                ; le message d'erreur complet
