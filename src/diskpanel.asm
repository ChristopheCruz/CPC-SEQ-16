; ============================================================================
; SEQ-16 - Panneau DISQUE (f5) : le catalogue (lot 5 du plan)
;
;   ligne  2      place libre et nombre de fichiers de la disquette
;   ligne  4      type affiché : SNG, PAT, INS, SMP (TAB passe au suivant)
;   lignes 6-17   les fichiers de ce type (4 colonnes de 12, pages de 48)
;   ligne  19     le fichier choisi, et le panneau où ENTER le charge
;   lignes 21-23  aide ; ligne 25 : messages
;
; Touches : flèches (choisir), TAB (type), ENTER (charger dans son panneau,
; qui s'affiche), C (relire la disquette), DEL deux fois (effacer, |ERA), COPY
; (renommer, |REN), N deux fois (nouveau morceau), f8 (sauver le morceau),
; ESPACE (écouter le motif).
; ============================================================================

DK_ROW0  equ 6
DK_ROWS  equ 12
DK_PAGE  equ 48
DK_INFO_ROW  equ 19

; --- Dessin -------------------------------------------------------------------------
ds_disk:
        ld hl,dsk_text
        call print_list
        call dk_types           ; la barre des types
        jp dk_rescan            ; lit le catalogue, puis la liste

; La barre des types (ligne 4) : le type affiché en jaune inversé
dk_types:
        ld hl,256*1+4
        call TXT_SET_CURSOR
        ld b,0
dkt_loop:
        push bc
        ld a,(dk_type)
        cp b
        ld bc,2*256+0
        jr nz,dkt_col
        ld bc,0*256+1
dkt_col:
        call colors
        pop bc
        push bc
        ld a,' '
        call txt_out
        ld a,b
        call dk_ext             ; HL = ".SNG"...
        inc hl
        ld b,3
        call print_n
        ld a,' '
        call txt_out
        xor a
        call TXT_SET_PAPER
        ld a,' '
        call txt_out
        pop bc
        inc b
        ld a,b
        cp 4
        jr nz,dkt_loop
        ret

; HL = extension du type A (0 SNG, 1 PAT, 2 INS, 3 SMP)
dk_ext:
        add a,a
        ld e,a
        ld d,0
        ld hl,dk_exts
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ret

dk_exts:  dw txt_ext,txt_ext_pat,txt_ext_ins,txt_ext_smp
dk_panels: db 4,0,1,3           ; écran qui reçoit chaque type

; Relit le catalogue (fichiers du type affiché), puis dessine la liste
dk_rescan:
        call silence
        ld a,(dk_type)
        call dk_ext
        ld (scan_ext),hl
        call smp_scan_dir       ; -> A = 0 si le catalogue a été lu
        or a
        jr z,dkr_ok
        xor a
        ld (smp_nfiles),a
        ld hl,txt_m_error
        call dsk_message
dkr_ok:
        xor a
        ld (smp_pick),a
        ld (ch_top),a
        call dk_setup
        call dk_header
        ; continue dans dk_draw_list

; La page affichée de la liste (lignes effacées, puis les noms)
dk_draw_list:
        ld l,DK_ROW0
        ld b,DK_ROWS
        call blank_rows
        ld a,(smp_nfiles)
        or a
        jr z,dk_info
        xor a
dkl_loop:
        push af
        call choose_draw
        pop af
        inc a
        ld hl,smp_nfiles
        cp (hl)
        jr nz,dkl_loop
        ; continue dans dk_info

; Ligne 19 : le fichier choisi, et le panneau où ENTER le charge
dk_info:
        ld l,DK_INFO_ROW
        ld b,1
        call blank_rows
        ld a,(smp_nfiles)
        or a
        ld hl,txt_s_nofile      ; aucun fichier de ce type
        jr z,dki_msg
        ld hl,256*1+DK_INFO_ROW
        call TXT_SET_CURSOR
        call dk_fullname        ; HL = "NOM.EXT", B = longueur
        push hl
        push bc
        ld a,1
        call TXT_SET_PEN
        pop bc
        pop hl
        call print_n
        ld a,2
        call TXT_SET_PEN
        ld hl,txt_dk_goes       ; "  ENTER : DANS "
        call print_trim
        ld a,3
        call TXT_SET_PEN
        ld a,(dk_type)          ; le nom du panneau, pris dans la barre
        ld e,a
        ld d,0
        ld hl,dk_panels
        add hl,de
        ld a,(hl)
        jp dk_tab_name
dki_msg:
        jp dsk_message

; Écrit le texte HL sans ses espaces de fin, puis un seul espace : une
; traduction plus courte est complétée d'espaces jusqu'à la longueur du
; français, ils feraient un trou avant ce qui suit
print_trim:
        ld b,0                  ; B = espaces en attente
ptr_loop:
        ld a,(hl)
        inc hl
        or a
        jr z,ptr_end
        cp ' '
        jr nz,ptr_char
        inc b
        jr ptr_loop
ptr_char:
        ld c,a
ptr_space:
        ld a,b                  ; les espaces avant ce caractère
        or a
        jr z,ptr_put
        ld a,' '
        call txt_out
        dec b
        jr ptr_space
ptr_put:
        ld a,c
        call txt_out
        jr ptr_loop
ptr_end:
        ld a,' '
        jp txt_out

; Écrit le nom de l'onglet de l'écran A ("2MOTIF"...), pris dans txt_tabs
dk_tab_name:
        ld hl,tab_screens       ; B = numéro de l'onglet de cet écran
        ld b,0
dtn_idx:
        cp (hl)
        jr z,dtn_found
        inc hl
        inc b
        jr dtn_idx
dtn_found:
        inc b                   ; on saute B + 1 caractères '|'
        ld hl,txt_tabs
dtn_skip:
        ld a,(hl)
        inc hl
        cp '|'
        jr nz,dtn_skip
        djnz dtn_skip
dtn_print:
        ld a,(hl)
        or a
        ret z
        cp '|'
        ret z
        call txt_out
        inc hl
        jr dtn_print

; HL = nom complet du fichier choisi ("NOM.EXT"), B = longueur ; DE = son nom
; sur 8 caractères
dk_fullname:
        ld a,(smp_pick)
        call choose_name
        push hl
        ld de,(scan_ext)
        call make_fname
        pop de
        ret

; Les réglages de choose_draw pour cette liste
dk_setup:
        ld hl,smp_files
        ld (ch_names),hl
        ld a,(smp_nfiles)
        ld (ch_count),a
        ld hl,8*256+DK_ROWS     ; ch_rows puis ch_len
        ld (ch_rows),hl
        ld hl,DK_ROW0*256+1     ; ch_col0 puis ch_row0
        ld (ch_col0),hl
        ld hl,DK_PAGE*256+10    ; ch_colw puis ch_page
        ld (ch_colw),hl
        ret

; Ligne 2 : place libre et nombre de fichiers (comptés par smp_scan_dir)
dk_header:
        ld hl,256*11+2
        call TXT_SET_CURSOR
        ld bc,3*256+0
        call colors
        ld a,(dir_cap)          ; blocs de 1 Ko : capacité - utilisés
        ld l,a
        ld h,0
        ld de,(dir_blocks)
        or a
        sbc hl,de
        jr nc,dkh_free
        ld hl,0
dkh_free:
        call print_dec16
        ld a,2
        call TXT_SET_PEN
        ld hl,txt_dk_free       ; "K LIBRES  "
        call print_str
        ld a,3
        call TXT_SET_PEN
        ld a,(dir_files)
        call print_dec2
        ld a,2
        call TXT_SET_PEN
        ld hl,txt_dk_files      ; " FICHIERS"
        jp print_str

; --- Touches -------------------------------------------------------------------------
dsk_cmd:
        ld a,(rc_index)
        cp 2
        jr z,dkc_keep           ; DEL : la confirmation reste armée
        xor a
        ld (dk_del_armed),a
dkc_keep:
        ld a,(rc_index)
        cp 15
        jr z,dkc_new
        xor a                   ; une autre touche que N : on désarme
        ld (new_armed),a
dkc_new:
        ld a,(rc_index)
        or a
        jp z,cmd_play           ; ESPACE : écouter le motif
        cp 2
        jp z,dk_delete          ; DEL
        cp 4
        jr z,dk_next_type       ; TAB
        cp 6
        jr z,dkn_left
        cp 7
        jr z,dkn_right
        cp 8
        jr z,dkn_up
        cp 9
        jr z,dkn_down
        cp 11
        jp z,dk_load            ; ENTER
        cp 14
        jp z,dk_rescan          ; C : relire la disquette (après un échange)
        cp 15
        jp z,disk_new           ; N (deux fois)
        cp 17
        jp z,dk_rename          ; COPY
        ret

dk_next_type:
        ld a,(dk_type)
        inc a
        and 3
        ld (dk_type),a
        call dk_types
        jp dk_rescan

dkn_up:
        ld a,(smp_pick)
        or a
        ret z
        dec a
        jr dk_move
dkn_down:
        ld a,(smp_pick)
        inc a
        ld hl,smp_nfiles
        cp (hl)
        ret nc
        jr dk_move
dkn_left:
        ld a,(smp_pick)
        sub DK_ROWS
        ret c
        jr dk_move
dkn_right:
        ld a,(smp_pick)
        add a,DK_ROWS
        ld hl,smp_nfiles
        cp (hl)
        ret nc
; Le curseur va sur le fichier A
dk_move:
        ld hl,smp_pick
        ld b,(hl)
        ld (hl),a
        push bc
        call ch_set_top         ; une autre page ?
        pop bc
        jp nz,dk_draw_list
        ld a,b
        call choose_draw        ; l'ancien redevient normal
        ld a,(smp_pick)
        call choose_draw
        jp dk_info

; ENTER : charge le fichier choisi dans son panneau, qui s'affiche
dk_load:
        ld a,(smp_nfiles)
        or a
        ret z
        call silence
        call dk_fullname        ; HL, B, DE : comme choose_file
        ld a,(dk_type)
        or a
        jr z,dkl_song
        dec a
        jr z,dkl_pat
        dec a
        jr z,dkl_ins
        call disk_load_bank_named
        jr dkl_show
dkl_song:
        call load_song_named
        jr dkl_show
dkl_pat:
        call disk_load_pat_named
        jr dkl_show
dkl_ins:
        call disk_load_ins_named
dkl_show:
        ld a,(dk_type)          ; le panneau de ce type
        ld e,a
        ld d,0
        ld hl,dk_panels
        add hl,de
        ld a,(hl)
        ld (screen),a
        call draw_screen
        ld hl,(last_msg)
        jp dsk_message

; DEL : une première fois, on demande ; une seconde, on efface (|ERA)
dk_delete:
        ld a,(smp_nfiles)
        or a
        ret z
        ld a,(dk_del_armed)
        or a
        jr nz,dkd_go
        inc a
        ld (dk_del_armed),a
        ld hl,txt_dk_confirm    ; "DEL A NOUVEAU : EFFACER CE FICHIER"
        jp dsk_message
dkd_go:
        xor a
        ld (dk_del_armed),a
        call silence
        call dk_fullname        ; HL = nom, B = longueur
        ld (dk_desc+1),hl       ; descripteur de chaîne : longueur, adresse
        ld a,b
        ld (dk_desc),a
        ld hl,dk_desc
        ld (dk_params),hl
        ld hl,rsx_era_name
        ld a,1                  ; un paramètre
        call dk_rsx
        jr nc,dkd_fail
        call dk_rescan
        ld hl,txt_dk_erased
        jp dsk_message
dkd_fail:
        ld hl,txt_m_error
        jp dsk_message

; COPY : renomme le fichier choisi (|REN,"nouveau","ancien")
dk_rename:
        ld a,(smp_nfiles)
        or a
        ret z
        call silence
        ld a,(smp_pick)         ; le nouveau nom part de l'ancien
        call choose_name
        ld de,dk_newname
        ld b,NAME_LEN
dkr_copy:
        ld a,(hl)
        cp ' '+1
        jr nc,dkr_c
        ld a,' '
dkr_c:
        ld (de),a
        inc hl
        inc de
        djnz dkr_copy
        ld hl,txt_m_file        ; « FICHIER : » et la saisie (RETURN, ESC)
        call dsk_message
        ld hl,256*11+DSK_MSG_ROW
        ld de,dk_newname
        ld bc,(scan_ext)
        call name_edit
        jr nc,dkr_cancel
        ld hl,dk_newname        ; nouveau nom complet -> dk_newfull
        ld de,(scan_ext)
        call make_fname
        ld de,dk_newfull
        ld c,b
        ld b,0
        push bc
        ldir
        pop bc
        ld a,c
        cp 5
        jr c,dkr_cancel         ; nom vide
        ld (dk_desc2),a         ; 2e descripteur : le nouveau nom
        ld hl,dk_newfull
        ld (dk_desc2+1),hl
        call dk_fullname        ; 1er : l'ancien nom
        ld (dk_desc+1),hl
        ld a,b
        ld (dk_desc),a
        ld hl,dk_desc           ; IX+0 : le dernier paramètre (l'ancien nom),
        ld (dk_params),hl       ; IX+2 : le premier (le nouveau)
        ld hl,dk_desc2
        ld (dk_params+2),hl
        ld hl,rsx_ren_name
        ld a,2
        call dk_rsx
        jr nc,dkd_fail
        call dk_rescan
        ld hl,txt_dk_renamed
        jp dsk_message
dkr_cancel:
        call dk_info
        ld hl,txt_m_none
        jp dsk_message

; Appelle la commande d'AMSDOS nommée en HL (|ERA, |REN) : A = nombre de
; paramètres, rangés dans dk_params (IX).  -> Carry = 1 si elle existe.
dk_rsx:
        ld (dk_nparams),a
        call KL_FIND_COMMAND    ; -> HL = adresse, C = ROM
        ret nc
        ld (dk_far),hl
        ld a,c
        ld (dk_far+2),a
        push ix
        ld ix,dk_params
        ld a,(dk_nparams)
        rst #18                 ; appel lointain
        dw dk_far
        pop ix
        scf
        ret

rsx_era_name: db "ER","A"+#80
rsx_ren_name: db "RE","N"+#80

dsk_text:
        db 1,2,2,0,  "DISQUE :",0
        db 30,4,3,0, "TAB",0
        db 34,4,2,0, "TYPE",0
        db 1,21,3,0, 240,241,242,243,0
        db 6,21,2,0, "CHOISIR",0
        db 15,21,3,0,"ENTER",0
        db 21,21,2,0,"CHARGER",0
        db 30,21,3,0,"N",0
        db 32,21,2,0,"NOUVEAU",0
        db 30,22,3,0,"C",0
        db 32,22,2,0,"RELIRE",0
        db 1,22,3,0, "DEL",0
        db 5,22,2,0, "EFFACER",0
        db 14,22,3,0,"COPY",0
        db 19,22,2,0,"RENOMMER",0
        db 1,23,3,0, "f8",0
        db 4,23,2,0, "SAUVER LE MORCEAU (.SNG)",0
        db 1,24,3,0, "ESC",0
        db 5,24,2,0, "1 SECONDE : QUITTER",0
        db #FF

txt_dk_goes:    db "  ENTER : DANS ",0
txt_dk_free:    db "K LIBRES  ",0
txt_dk_files:   db " FICHIERS",0
txt_dk_confirm: db "DEL A NOUVEAU : EFFACER CE FICHIER",0
txt_dk_erased:  db "FICHIER EFFACE",0
txt_dk_renamed: db "FICHIER RENOMME",0

dk_type:      db 0              ; type affiché (0 SNG, 1 PAT, 2 INS, 3 SMP)
dk_del_armed: db 0              ; 1 = DEL a déjà été appuyée une fois
dk_nparams:   db 0
dk_far:       ds 3              ; adresse lointaine de la commande AMSDOS
dk_params:    ds 4              ; paramètres (IX) : adresses des descripteurs
dk_desc:      ds 3              ; descripteur : longueur, adresse
dk_desc2:     ds 3
dk_newname:   ds NAME_LEN
dk_newfull:   ds 13
