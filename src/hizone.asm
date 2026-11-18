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

; ============================================================================
; DIGIDRUMS (phase 4, mode BLOQUANT)
;
; Un instrument dont le drapeau 4 est mis joue un sample au lieu d'une note :
; l'octet du bruit (INS_NOISE) donne le numéro du sample, le volume (0 à 15)
; l'atténue.  snd_note_on ne démarre pas de note : il appelle dg_queue, qui
; met le sample en attente.  A la fin de l'image, la boucle principale
; appelle dg_play : le sample joue jusqu'au bout, interruptions coupées,
; puis on rattrape le tempo en appelant seq_frame autant de fois qu'il a
; duré d'images.  Pendant ce temps, les enveloppes des autres voix sont
; gelées (voulu, voir le README).
; ============================================================================

; Joue le sample en attente, puis rattrape le tempo du séquenceur.
dg_play:
        xor a
        ld (dg_debt),a          ; images à rattraper
dgp_play:
        xor a
        ld (dg_pending),a
        ld a,(dg_att)           ; atténuation (volume de l'instrument)
        ld (spr_att),a
        ld a,(dg_semi)
        ld b,a
        ld a,(dg_chan)
        ld c,a
        ld a,(dg_smp)
        call smp_prepare        ; tables et boucle prêtes ?
        jr nc,dgp_catch         ; sample absent : rien à jouer
        ld hl,(smp_v_len)       ; durée en images =
        ld de,(smp_v_period)    ;   octets x 2 x P NOP / 20 000 NOP,
        call dg_mul             ;   arrondie au-dessus
        ld de,10000             ; (A:HL = octets x P)
        ld b,0
dgp_count:
        inc b
        jr z,dgp_cap            ; plus de 255 images : on s'arrête là
        or a
        sbc hl,de
        sbc a,0
        jr c,dgp_counted        ; plus rien : B = nombre d'images
        ld c,a
        or h
        or l
        ld a,c
        jr nz,dgp_count
        jr dgp_counted
dgp_cap:
        dec b                   ; B = 255
dgp_counted:
        ld a,(dg_debt)          ; dette += durée (au plus 255)
        add a,b
        jr nc,dgp_debt
        ld a,255
dgp_debt:
        ld (dg_debt),a
        call smp_play           ; on joue (interruptions coupées)
dgp_catch:
        ld a,(dg_debt)          ; rattrapage : une image de séquenceur à la
        or a                    ; fois
        jr z,dgp_end
        dec a
        ld (dg_debt),a
        call seq_frame
        ld a,(dg_pending)       ; un autre digidrum vient de partir ?
        or a
        jr nz,dgp_play          ; on le joue tout de suite
        jr dgp_catch
dgp_end:
        xor a                   ; l'écoute sur f4 ne doit pas être atténuée
        ld (spr_att),a
        ret


; ============================================================================
; f4, O : prendre un sample dans une autre banque .SMP de la disquette
;
; On choisit la banque, puis l'un de ses samples (liste en bas de l'écran).
; Le sample est ajouté à la fin de la banque en mémoire, avec ses réglages.
; Ordre des opérations, pour ne rien abîmer si la lecture échoue :
;   1. les données du sample sont lues juste après la fin de la banque ;
;   2. toutes les données remontent de 16 octets ;
;   3. la nouvelle fiche prend la place libérée, après les autres fiches.
; Appelée par smp_take (smpscreen.asm) seulement s'il y a une banque.
; ============================================================================
smp_take_hi:
        ld a,(smp_count)        ; 16 samples au plus
        cp 16
        ld hl,txt_t_full
        jp nc,tk_msg
        ld hl,txt_ext_smp       ; on choisit une banque .SMP
        call choose_file        ; -> HL = nom complet, B = longueur
        jp nc,tk_last           ; annulé ou erreur : message déjà affiché
        push hl                 ; on garde le nom pour la 2e lecture
        push bc
        ld de,io_buffer
        call CAS_IN_OPEN
        jp nc,tk_err2
        ld hl,SCRATCH           ; en-tête de l'autre banque
        ld de,16
        call cas_read
        jp nc,tk_ab2
        ld a,(SCRATCH+5)        ; nombre de samples : 1 à 16
        or a
        jp z,tk_bad2
        cp 17
        jp nc,tk_bad2
        ld (tk_n),a
        ld l,a                  ; ses fiches : 16 octets chacune
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ex de,hl
        ld hl,SCRATCH+16
        call cas_read
        jp nc,tk_ab2
        call CAS_IN_CLOSE
        ld hl,SCRATCH+16        ; les noms (6 caractères), les uns après les
        ld de,SCRATCH+288       ; autres, pour la liste de choix
        ld a,(tk_n)
        ld b,a
tk_names:
        push bc
        ld bc,6
        ldir
        ld bc,10                ; fiche suivante
        add hl,bc
        pop bc
        djnz tk_names
        ld hl,SCRATCH+288       ; liste : ces noms,
        ld (ch_names),hl
        ld a,(tk_n)
        ld (ch_count),a
        ld hl,6*256+CHOOSE_ROWS ;   6 caractères, 6 lignes,
        ld (ch_rows),hl
        ld hl,CHOOSE_ROW*256+1  ;   en bas de l'écran,
        ld (ch_col0),hl
        ld a,9                  ;   colonnes de 9 caractères
        ld (ch_colw),a
        call choose_clear
        call choose_run         ; -> Carry si RETURN, A = sample choisi
        pop bc                  ; B, HL = nom de l'autre banque
        pop hl
        jp nc,tk_cancel
        push hl
        ld l,a                  ; IX = sa fiche
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,SCRATCH+16
        add hl,de
        push hl
        pop ix
        pop hl
        ld a,(ix+SMPF_BLOCK)    ; mémoire principale seulement
        or a
        jp nz,tk_bad
        push hl                 ; assez de place ? taille + 16 + longueur
        ld hl,(smp_bank_len)
        ld e,(ix+SMPF_LEN)
        ld d,(ix+SMPF_LEN+1)
        add hl,de
        ld de,16
        add hl,de
        ld de,BANK_MAX+1
        or a
        sbc hl,de
        pop hl
        ld de,txt_s_big
        jp nc,tk_msg_de
        ; --- 1. lecture des données, juste après la fin de la banque
        ld de,io_buffer
        call CAS_IN_OPEN
        jp nc,tk_err
        ld a,(tk_n)             ; on saute l'en-tête, les fiches et le début
        ld l,a                  ; des données : 16 + 16 x n + décalage
        ld h,0
        inc l
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld e,(ix+SMPF_OFF)
        ld d,(ix+SMPF_OFF+1)
        add hl,de
        ex de,hl
        call cas_skip
        jp nc,tk_ab
        ld hl,(smp_bank_end)    ; les données arrivent après la banque
        ld e,(ix+SMPF_LEN)
        ld d,(ix+SMPF_LEN+1)
        call cas_read
        jp nc,tk_ab
        call CAS_IN_CLOSE
        ; --- 2. toutes les données remontent de 16 octets
        ld hl,(smp_bank_end)    ; nombre d'octets = fin + longueur - données
        ld e,(ix+SMPF_LEN)
        ld d,(ix+SMPF_LEN+1)
        add hl,de
        push hl                 ; (fin des nouvelles données)
        ld de,(smp_data)
        or a
        sbc hl,de
        ld b,h
        ld c,l
        pop hl
        dec hl                  ; dernier octet
        ld d,h
        ld e,l
        inc de                  ; 16 octets plus haut
        ld a,16
tk_up16:
        inc de
        dec a
        jr nz,tk_up16
        dec de
        lddr
        ; --- 3. la nouvelle fiche, après les autres
        ld hl,(smp_bank_end)    ; son décalage : taille des anciennes données
        ld de,(smp_data)
        or a
        sbc hl,de
        ld (ix+SMPF_OFF),l
        ld (ix+SMPF_OFF+1),h
        push ix
        pop hl
        ld de,(smp_data)
        ld bc,16
        ldir
        ld hl,(smp_bank_len)    ; nouvelle taille
        ld e,(ix+SMPF_LEN)
        ld d,(ix+SMPF_LEN+1)
        add hl,de
        ld de,16
        add hl,de
        ld (smp_bank_len),hl
        ld a,(smp_count)        ; le nouveau sample devient le sample choisi
        ld (cur_smp),a
        inc a
        ld (BANK_START+5),a     ; un sample de plus dans l'en-tête
        call smp_check          ; nombre, début des données, fin de la banque
        ld hl,txt_t_added
        jr tk_msg
tk_ab2:
        call CAS_IN_ABANDON
tk_err2:
        pop bc
        pop hl
tk_err:
        ld hl,txt_m_error
        jr tk_msg
tk_ab:
        call CAS_IN_ABANDON
        jr tk_err
tk_bad2:
        call CAS_IN_ABANDON
        pop bc
        pop hl
tk_bad:
        ld hl,txt_s_bad
        jr tk_msg
tk_msg_de:
        ex de,hl
        jr tk_msg
tk_cancel:
        ld hl,txt_m_none
        jr tk_msg
tk_last:
        ld hl,(last_msg)
tk_msg:
        push hl                 ; on redessine l'écran, puis le message
        call draw_screen
        pop hl
        jp dsk_message

txt_t_full:  db "LA BANQUE A DEJA 16 SAMPLES",0
txt_t_added: db "SAMPLE AJOUTE A LA BANQUE",0
tk_n:        db 0
