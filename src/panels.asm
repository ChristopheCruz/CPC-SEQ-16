; ============================================================================
; SEQ-16 - Les cinq panneaux : f8 sauver et f9 charger dans chacun, et le
; panneau SONG (lot 2 du plan, voir PLAN.md)
;
;   panneau        f8 sauve                  f9 charge
;   1 MOTIF        le motif affiché (.PAT)   un .PAT dans le motif affiché
;   2 SONG         le morceau (.SNG)         un morceau
;   3 INST         la banque (.INS)          une banque .INS
;   4 SAMPLE       la banque (.SMP)          une banque .SMP
;   5 DISQUE       le morceau (.SNG)         un morceau
;
; f8 demande le nom (saisie sur la ligne des messages, RETURN valide, ESC
; annule) ; si le fichier existe déjà, un second RETURN le remplace.  f9
; ouvre la liste des fichiers du bon type (choose_file).  Ensuite, sauf sur
; le panneau DISQUE, l'écran est redessiné (la liste a recouvert le bas) et
; le dernier message est réaffiché.
; ============================================================================

; --- f8 ----------------------------------------------------------------------
panel_save:
        call silence
        ld a,(screen)
        or a
        jr z,ps_pat
        dec a
        jr z,ps_ins
        dec a
        jr z,ps_song            ; DISQUE : le morceau
        dec a
        jr z,ps_smp
ps_song:                        ; SONG
        ld hl,txt_ext
        call ask_save
        call c,disk_save
        jr panel_done
ps_pat:
        ld hl,txt_ext_pat
        call ask_save
        call c,disk_save_pat
        jr panel_done
ps_ins:
        ld hl,txt_ext_ins
        call ask_save
        call c,disk_save_ins
        jr panel_done
ps_smp:
        ld a,(smp_count)        ; une banque est-elle chargée ?
        or a
        ld hl,txt_s_nobank
        jr z,ps_msg
        ld hl,txt_ext_smp       ; le nom est celui de la banque
        ld de,smp_name
        call ask_save_buf
        call c,smp_save_bank
        jr panel_done
ps_msg:
        call dsk_message
        jr panel_done

; --- f9 ----------------------------------------------------------------------
panel_load:
        call silence
        ld a,(screen)
        or a
        jr z,pl_pat
        dec a
        jr z,pl_ins
        dec a
        jr z,pl_song
        dec a
        jr z,pl_smp
pl_song:
        call load_song_chosen
        jr panel_done
pl_pat:
        call disk_load_pat
        jr panel_done
pl_ins:
        call disk_load_ins
        jr panel_done
pl_smp:
        ld a,(smp_ok)           ; il faut la zone haute
        or a
        ld hl,txt_s_nomem
        jr z,ps_msg
        call disk_load_bank
        ; continue dans panel_done

; Après f8 / f9 : on redessine l'écran (sauf DISQUE, qui se met à jour
; lui-même), puis on réaffiche le message
panel_done:
        ld a,(screen)
        cp 2
        ret z
        call draw_screen
        ld hl,(last_msg)
        ld a,(hl)               ; annulé (message vide) : l'écran reste intact
        or a
        ret z
        jp dsk_message

; Choisit un morceau dans la liste, puis le charge (disk_load)
load_song_chosen:
        ld hl,txt_ext
        call choose_file        ; -> DE = nom sur 8 caractères
        ret nc
        ex de,hl
        ld de,fname
        ld b,NAME_LEN
lsc_copy:
        ld a,(hl)
        cp ' '+1                ; les 0 de fin de nom deviennent des espaces
        jr nc,lsc_put
        ld a,' '
lsc_put:
        ld (de),a
        inc hl
        inc de
        djnz lsc_copy
        jp disk_load

; --- Le nom du fichier à sauver ------------------------------------------------
; HL = extension.  Saisie de fname (ask_save) ou du nom pointé par DE
; (ask_save_buf).  -> Carry = 1 : on peut sauver ; Carry = 0 : annulé.
ask_save:
        ld de,fname
ask_save_buf:
        push hl                 ; extension
        push de                 ; nom
        ld hl,txt_m_file        ; « FICHIER : » sur la ligne des messages
        call dsk_message
        ld a,(screen)
        cp 2
        ld l,DSK_MSG_ROW
        jr z,as_row
        ld l,INS_MSG_ROW
as_row:
        ld h,11                 ; le nom en colonne 11
        pop de
        pop bc                  ; BC = extension
        push bc
        push de
        call name_edit
        pop de
        pop bc
        jr nc,as_cancel
        ld h,d                  ; le fichier existe-t-il déjà ?
        ld l,e
        ld d,b
        ld e,c
        call make_fname         ; -> HL = "NOM.EXT", B = longueur
        ld a,b
        cp 5
        jr c,as_noname          ; nom vide
        ld de,io_buffer
        call CAS_IN_OPEN
        ccf
        ret c                   ; absent : on sauve
        call CAS_IN_ABANDON
        ld hl,txt_m_exists      ; déjà là : RETURN remplace, sinon on annule
        call dsk_message
as_flush:
        call KM_READ_CHAR       ; (les frappes en attente ne comptent pas)
        jr c,as_flush
        call KM_WAIT_CHAR
        cp 13
        scf
        ret z
as_cancel:
        ld hl,txt_m_none
        call dsk_message
        or a
        ret
as_noname:
        ld hl,txt_m_noname
        call dsk_message
        or a
        ret

txt_m_file:   db "FICHIER :",0
txt_m_exists: db "DEJA SUR LA DISQUETTE : RETURN REMPLACE",0

; --- Panneau SONG -------------------------------------------------------------
; Pour l'instant : le nom du morceau, f8 et f9.  L'enchaînement des motifs
; arrive au lot 4.
ds_song:
        ld hl,song_text
        call print_list
        ld hl,256*11+4          ; le nom du morceau
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        ld a,3
        call TXT_SET_PEN
        ld hl,fname
        ld b,NAME_LEN
        call print_n
        xor a
        jp TXT_SET_PAPER

song_cmd:
        ld a,(rc_index)
        or a
        jp z,cmd_play           ; ESPACE : lecture / arrêt du motif
        ret

song_text:
        db 1,4,2,0,"MORCEAU :",0
        db 1,7,2,0,"L'ENCHAINEMENT DES MOTIFS ARRIVE",0
        db 1,8,2,0,"DANS LA PROCHAINE VERSION.",0
        db 1,11,3,0,"f8",0
        db 4,11,2,0,"SAUVER LE MORCEAU (.SNG)",0
        db 1,12,3,0,"f9",0
        db 4,12,2,0,"CHARGER UN MORCEAU",0
        db 1,14,3,0,"ESPACE",0
        db 8,14,2,0,"LIRE LE MOTIF",0
        db #FF
