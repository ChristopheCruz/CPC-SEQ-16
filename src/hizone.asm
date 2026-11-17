; ============================================================================
; SEQ-16 - Routines de la zone haute (hors lecture des samples)
;
; Ces routines sont assemblées avec la routine de lecture des samples, pour
; leur adresse en zone haute, et recopiées avec elle par smp_install.  Leur
; source est ensuite recouverte par le morceau : elles ne prennent aucune
; place en mémoire basse, où il n'en reste presque plus.
; On ne les appelle que si smp_ok = 1 (zone haute bien installée).
; ============================================================================

; --- f2, O : prendre un son dans une banque ----------------------------------
; Appelée par ins_take (banks.asm), seulement si la zone haute est installée.
ins_take_hi:
        ld hl,txt_ext_ins       ; on choisit une banque .INS
        call choose_file        ; -> HL = nom complet, B = longueur
        jp nc,it_last           ; annulé ou erreur : on garde le message
        push hl                 ; on garde le nom pour la 2e lecture
        push bc
        call ins_open           ; ouvre la banque, saute son en-tête
        jp nc,it_fail2          ; HL = message d'erreur
        ld de,NB_INST*16        ; on saute les 32 instruments
        call cas_skip
        jp nc,it_err2
        ld hl,SCRATCH           ; et on range les 32 noms
        ld de,NB_INST*6
        call cas_read
        jp nc,it_err2
        call CAS_IN_CLOSE

        ld h,21                 ; on efface le panneau de droite
        ld d,39                 ; (colonnes 22 à 40, lignes 4 à 21)
        ld l,3
        ld e,20
        call TXT_WIN_ENABLE
        xor a
        call TXT_SET_PAPER
        call TXT_CLEAR_WINDOW
        ld h,0                  ; on rend tout l'écran au texte
        ld d,39
        ld l,0
        ld e,24
        call TXT_WIN_ENABLE
        ld hl,it_title          ; titre de la liste
        call print_list
        ld hl,SCRATCH           ; liste : les 32 noms de la banque,
        ld (ch_names),hl
        ld a,NB_INST
        ld (ch_count),a
        ld hl,6*256+16          ;   6 caractères, 16 lignes par colonne,
        ld (ch_rows),hl
        ld hl,5*256+23          ;   à partir de la colonne 23, ligne 5,
        ld (ch_col0),hl
        ld a,9                  ;   colonnes de 9 caractères
        ld (ch_colw),a
        call choose_run         ; -> Carry si RETURN, A = son choisi
        pop bc                  ; B, HL = nom de la banque
        pop hl
        jp nc,it_cancel
        ld (it_pick),a
        call ins_open           ; 2e lecture : jusqu'au son choisi
        jp nc,it_msg
        ld a,(it_pick)          ; on saute les sons qui le précèdent
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl               ; 16 octets par son
        ex de,hl
        call cas_skip
        jp nc,it_err
        ld a,(cur_inst)         ; ses 16 octets vont dans l'instrument
        call inst_ptr
        ld de,16
        call cas_read
        jp nc,it_err
        call CAS_IN_CLOSE
        ld a,(it_pick)          ; et son nom aussi
        call inst_name_ptr      ; HL = inst_names + 6 x son choisi
        ld bc,SCRATCH-inst_names
        add hl,bc               ; = SCRATCH + 6 x son choisi
        push hl
        ld a,(cur_inst)
        call inst_name_ptr
        ex de,hl                ; DE = nom de l'instrument en cours
        pop hl
        ld bc,6
        ldir
        ld hl,txt_i_took        ; « son chargé »
        jr it_msg
it_err2:
        pop bc                  ; on rend la pile
        pop hl
it_err:
        call CAS_IN_ABANDON
        ld hl,txt_m_error
        jr it_msg
it_fail2:
        pop bc                  ; on rend la pile (HL = message d'erreur)
        pop bc
        jr it_msg
it_cancel:
        ld hl,txt_m_none        ; annulé : pas de message
        jr it_msg
it_last:
        ld hl,(last_msg)        ; le message déjà affiché par choose_file
it_msg:
        push hl                 ; on redessine l'écran, puis le message
        call draw_screen
        pop hl
        jp dsk_message

it_title:
        db 23,4,1,0,"SONS DE LA BANQUE",0
        db #FF


txt_i_took:   db "SON PRIS DANS LA BANQUE",0
