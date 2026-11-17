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

; Met un sample en attente.  HL = instrument, B = note (ou période du bruit
; pour la voix N), sno_chan = voix (0 à 3).
dg_queue:
        ld a,(sno_chan)
        ld c,a                  ; C = voix
        ld d,a                  ; voix muette (bit de snd_mute) : rien
        inc d
        ld a,(snd_mute)
dgq_mute:
        rrca                    ; le bit de la voix finit dans Carry
        dec d
        jr nz,dgq_mute
        ret c
        ld a,c                  ; voie de l'AY : celle de la voix, et C
        cp 3                    ; pour la voix N
        jr c,dgq_chan
        ld a,2
dgq_chan:
        ld (dg_chan),a
        ld a,c                  ; hauteur : la note 48 (DO de la rangée du
        cp 3                    ; haut, octave 3) joue le sample tel quel
        ld a,0                  ; voix N : toujours la hauteur d'origine
        jr z,dgq_semi
        ld a,b
        cp 36                   ; on borne à -12 / +12 demi-tons
        jr nc,dgq_lo
        ld a,36
dgq_lo:
        cp 61
        jr c,dgq_hi
        ld a,60
dgq_hi:
        sub 48
dgq_semi:
        ld (dg_semi),a
        push hl
        ld de,INS_NOISE         ; numéro du sample
        add hl,de
        ld a,(hl)
        ld (dg_smp),a
        pop hl
        ld de,INS_VOLUME        ; atténuation = 15 - volume
        add hl,de
        ld a,15
        sub (hl)
        jr nc,dgq_att
        xor a
dgq_att:
        ld (dg_att),a
        ld a,1
        ld (dg_pending),a       ; la boucle principale le jouera
        ret

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

; A:HL = HL x DE (24 bits suffisent : 16 320 x 1 000 < 2^24)
dg_mul:
        ld b,h                  ; BC = multiplicande
        ld c,l
        ld hl,0
        xor a                   ; A:HL = résultat
        ld (dg_cnt),a
dgm_loop:
        add hl,hl               ; résultat x 2
        rla
        ex de,hl                ; bit suivant du multiplicateur (du haut)
        add hl,hl
        ex de,hl
        jr nc,dgm_next
        add hl,bc
        adc a,0
dgm_next:
        push af
        ld a,(dg_cnt)
        inc a
        ld (dg_cnt),a
        cp 16
        jr z,dgm_done
        pop af
        jr dgm_loop
dgm_done:
        pop af
        ret

; Ligne du réglage « bruit » d'un digidrum, sur l'écran f2 :
; HL = "  SAMPLE nomxxx" (15 caractères), le nom du sample choisi.
dg_label_hi:
        ld a,(cur_inst)
        call inst_ptr
        ld bc,INS_NOISE
        add hl,bc
        ld a,(hl)               ; A = numéro du sample
        ld hl,smp_count
        cp (hl)
        ld hl,txt_dg_none       ; absent de la banque (ou pas de banque)
        jr nc,dgl_copy
        call smp_entry          ; présent : HL = sa fiche (nom en tête)
dgl_copy:
        push hl
        ld hl,txt_dg_lab        ; "  SAMPLE "
        ld de,dg_lab
        ld bc,9
        ldir
        pop hl                  ; puis les 6 caractères du nom
        ld bc,6
        ldir
        ld hl,dg_lab
        ret

txt_dg_lab:  db "  SAMPLE "
txt_dg_none: db "------"
dg_lab:      ds 15              ; la ligne construite

dg_cnt:         db 0
