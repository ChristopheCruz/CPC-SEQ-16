; ============================================================================
; SEQ-16 - Copie des instruments et banques d'instruments (.INS)
;
; Ecran f2 :
;   COPY   copie l'instrument en cours (réglages et nom) dans un
;          presse-papiers
;   P      colle le presse-papiers dans l'instrument en cours
;   O      prend un son dans une banque .INS de la disquette : on choisit la
;          banque, puis l'un de ses 32 sons, qui remplace l'instrument en cours
; Ecran f3 :
;   I      sauve les 32 instruments et les 8 sons composés : NOM.INS
;   O      charge une banque .INS entière (les motifs ne changent pas)
;
; Une banque .INS a le même début qu'un morceau .SNG, sans les motifs :
;   en-tête "SQ16" (16 octets), 32 instruments, 32 noms, 8 sons composés,
;   soit SONG_FIXED = 848 octets.  On la sauve d'un seul tenant depuis
;   song_data ; au chargement, on saute l'en-tête : les volumes du mixage
;   ne changent pas.
;
; Le chargement lit le fichier octet par octet (CAS_IN_CHAR) : il n'y a pas
; la place de garder une copie du fichier en mémoire.  Pour choisir un son,
; on range les 32 noms de la banque dans la zone de travail SCRATCH (les
; tables des samples, refaites avant chaque écoute), puis on relit le
; fichier jusqu'au son choisi.
; ============================================================================

SCRATCH      equ SMP_LUT_HI     ; 512 octets de travail (zone haute)
smp_files    equ SCRATCH        ; liste des fichiers d'une extension (64 x 8) :
                                ; libre pendant le choix d'un fichier
INS_MSG_ROW  equ 25             ; écran f2 : ligne des messages
INS_FILE_LEN equ SONG_FIXED     ; taille d'une banque .INS

; --- Presse-papiers ----------------------------------------------------------
; COPY : l'instrument en cours va dans le presse-papiers
ins_copy:
        ld a,(cur_inst)
        call inst_ptr           ; HL = réglages de l'instrument
        ld de,clip
        ld bc,16
        ldir                    ; 16 octets de réglages
        ld a,(cur_inst)
        call inst_name_ptr      ; HL = son nom
        ld bc,6
        ldir                    ; puis 6 caractères de nom (DE suit)
        ld a,1
        ld (clip_ok),a          ; le presse-papiers est plein
        ld hl,txt_i_copied
        jp dsk_message

; P : le presse-papiers remplace l'instrument en cours
ins_paste:
        ld a,(clip_ok)
        or a
        ld hl,txt_i_noclip      ; rien n'a encore été copié
        jp z,dsk_message
        ld a,(cur_inst)
        call inst_ptr
        ex de,hl                ; DE = réglages de l'instrument
        ld hl,clip
        ld bc,16
        ldir
        ld a,(cur_inst)
        call inst_name_ptr
        ex de,hl                ; DE = son nom
        ld hl,clip+16
        ld bc,6
        ldir
        call ins_show_all       ; on affiche le nouvel instrument
        ld hl,txt_i_pasted
        jp dsk_message

; HL = réglages de l'instrument A (instruments + 16 x A)
inst_ptr:
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl               ; 16 octets par instrument
        ld bc,instruments
        add hl,bc
        ret

; HL = nom de l'instrument A (inst_names + 6 x A)
inst_name_ptr:
        ld l,a
        ld h,0
        ld b,h
        ld c,l
        add hl,hl               ; 2A
        add hl,bc               ; 3A
        add hl,hl               ; 6A
        ld bc,inst_names
        add hl,bc
        ret

; --- f2, O : prendre un son dans une banque ----------------------------------
; La routine est en zone haute (hizone.asm) : on vérifie d'abord qu'elle a
; bien été installée.
ins_take:
        ld a,(smp_ok)           ; zone haute installée ?
        or a
        ld hl,txt_i_nomem
        jp z,dsk_message        ; non : pas assez de mémoire
        jp ins_take_hi          ; oui : on y va

; --- f3, I : sauver les instruments ------------------------------------------
disk_save_ins:
        ld hl,txt_ext_ins       ; NOM.INS
        ld de,INS_FILE_LEN      ; en-tête, instruments, noms, sons composés
        ld bc,txt_i_saved
        jp save_file

; --- f3, O : charger une banque d'instruments entière ------------------------
disk_load_ins:
        ld hl,txt_ext_ins       ; on choisit une banque .INS
        call choose_file
        ret nc                  ; annulé ou erreur : message déjà affiché
        push hl
        push bc
        ld hl,txt_m_loading     ; « chargement en cours »
        call dsk_message
        pop bc
        pop hl
        call ins_open           ; ouvre la banque, saute son en-tête
        jp nc,dsk_message       ; HL = message d'erreur
        ld hl,instruments       ; instruments, noms et sons composés
        ld de,INS_FILE_LEN-16
        call cas_read
        jr nc,dli_err
        call CAS_IN_CLOSE
        call snd_init           ; les voix repartent des nouveaux sons
        ld hl,txt_i_loaded
        jp dsk_message
dli_err:
        call CAS_IN_ABANDON
        jp disk_error

; --- f3, M : sauver le motif affiché (NOM.PAT, 260 octets) -------------------
disk_save_pat:
        ld hl,pat_work          ; le motif affiché
        ld (sf_addr),hl
        ld hl,txt_ext_pat
        ld de,PAT_SIZE
        ld bc,txt_p_saved
        jp save_block_main

; --- f3, P : charger un motif .PAT à la place du motif affiché ----------------
; Le fichier doit faire exactement PAT_SIZE octets ; un mode inconnu devient
; « voix séparées ».  Le motif garde son tempo (octet 1 du fichier).
disk_load_pat:
        ld hl,txt_ext_pat       ; on choisit un motif sur la disquette
        call choose_file        ; (coupe aussi le son)
        ret nc
        ld (dlp_name),de        ; son nom (8 caractères)
        push hl
        push bc
        ld hl,txt_m_loading
        call dsk_message
        pop bc
        pop hl
        ld de,io_buffer
        call CAS_IN_OPEN        ; -> BC = taille du fichier
        jp nc,disk_error
        ld hl,PAT_SIZE
        or a
        sbc hl,bc
        jr nz,dlp_bad
        ld hl,pat_work          ; à la place du motif affiché
        push hl
        call CAS_IN_DIRECT
        pop hl
        jr nc,dlp_abandon
        ld a,(hl)               ; mode : 0 ou 1
        cp 2
        jr c,dlp_mode
        ld (hl),0
dlp_mode:
        call seq_set_pattern    ; le séquenceur prend le motif et son tempo
        call CAS_IN_CLOSE
        ld a,(cur_pat)          ; le motif prend le nom de son fichier
        call pat_name_ptr       ; (panneau SONG)
        ex de,hl
        ld hl,(dlp_name)
        ld b,8
dlp_nm:
        ld a,(hl)
        cp ' '+1
        jr nc,dlp_nc
        ld a,' '
dlp_nc:
        ld (de),a
        inc hl
        inc de
        djnz dlp_nm
        ld hl,txt_p_loaded
        jp dsk_message
dlp_bad:
        call CAS_IN_ABANDON
        ld hl,txt_p_bad
        jp dsk_message
dlp_abandon:
        call CAS_IN_ABANDON
        jp disk_error

; --- Lecture d'une banque, octet par octet -----------------------------------
; Ouvre la banque HL (nom), B (longueur) et lit son en-tête.
; Sortie : Carry = 1, le fichier est ouvert, prêt à lire les instruments.
;          Carry = 0, le fichier est fermé, HL = message d'erreur.
ins_open:
        ld de,io_buffer
        call CAS_IN_OPEN        ; -> BC = taille du fichier
        ld hl,txt_m_error
        ret nc                  ; fichier absent, disquette illisible
        ld hl,INS_FILE_LEN      ; la taille doit être exactement la bonne
        or a
        sbc hl,bc
        jr nz,io_bad
        ld hl,song_sig          ; puis la signature "SQ16"
        ld b,4
io_sig:
        call CAS_IN_CHAR
        jr nc,io_err
        cp (hl)
        jr nz,io_bad
        inc hl
        djnz io_sig
        ld de,12                ; le reste de l'en-tête ne sert pas
        call cas_skip
        ret c                   ; tout va bien
io_err:
        call CAS_IN_ABANDON
        ld hl,txt_m_error
        or a
        ret
io_bad:
        call CAS_IN_ABANDON
        ld hl,txt_i_bad
        or a                    ; Carry = 0
        ret

; Saute DE octets du fichier ouvert.  Carry = 0 si le fichier est trop court.
cas_skip:
        ld a,d
        or e
        scf
        ret z                   ; plus rien à sauter
        call CAS_IN_CHAR        ; (garde BC, DE et HL)
        ret nc
        dec de
        jr cas_skip

; Lit DE octets du fichier ouvert vers HL.  Carry = 0 si le fichier est trop
; court.
cas_read:
        ld a,d
        or e
        scf
        ret z                   ; tout est lu
        call CAS_IN_CHAR
        ret nc
        ld (hl),a
        inc hl
        dec de
        jr cas_read

txt_ext_ins:  db ".INS",0
txt_i_copied: db "INSTRUMENT COPIE (P : COLLER)",0
txt_i_pasted: db "INSTRUMENT COLLE",0
txt_i_noclip: db "RIEN A COLLER : COPY D'ABORD",0
txt_i_nomem:  db "PAS ASSEZ DE MEMOIRE",0
txt_i_saved:  db "INSTRUMENTS SAUVES (.INS)",0
txt_i_loaded: db "INSTRUMENTS CHARGES",0
txt_i_bad:    db "CE FICHIER N'EST PAS UNE BANQUE .INS",0
txt_ext_pat:  db ".PAT",0
dlp_name:     dw 0
txt_p_saved:  db "MOTIF SAUVE (.PAT)",0
txt_p_loaded: db "MOTIF CHARGE",0
txt_p_bad:    db "CE FICHIER N'EST PAS UN MOTIF .PAT",0

; ============================================================================
; Banque de samples : sauvegarde (f3, E) et banque associée à un morceau.
; On n'y arrive que si une banque est chargée ou si la zone haute est
; installée (tests faits par l'appelant).
; ============================================================================
; --- f3, E : sauver la banque de samples -------------------------------------
; Le fichier porte le nom de la banque (NOM.SMP).  Les réglages faits sur
; l'écran f4 sont dans les fiches, en mémoire : ils sont donc sauvés.
smp_save_bank:
        call silence
        ld hl,smp_name          ; nom de la banque
        ld de,txt_ext_smp
        call make_fname         ; -> HL = "NOM.SMP", B = longueur
        push hl
        push bc
        ld hl,txt_m_saving
        call dsk_message
        pop bc
        pop hl
        ld de,io_buffer
        call CAS_OUT_OPEN
        jp nc,disk_error
        ld hl,BANK_START        ; la banque entière, telle qu'en mémoire
        ld de,(smp_bank_len)
        ld bc,0
        ld a,2                  ; fichier binaire
        call CAS_OUT_DIRECT
        jp nc,ds_abandon
        call CAS_OUT_CLOSE
        jp nc,disk_error
        ld hl,txt_s_saved
        jp dsk_message

txt_s_saved: db "BANQUE DE SAMPLES SAUVEE (.SMP)",0

; --- Chargement d'un morceau v2 : sa banque de samples -----------------------
; Le morceau garde le nom de la banque utilisée (song_bank).  Si ce n'est
; pas celle qui est en mémoire, on la charge.  Sortie : message affiché.
song_load_bank:
        ld a,(smp_count)        ; déjà en mémoire ?
        or a
        jr z,sbh_load
        ld hl,song_bank
        ld de,smp_name
        ld b,8
sbh_cmp:
        ld a,(de)
        cp (hl)
        jr nz,sbh_load
        inc hl
        inc de
        djnz sbh_cmp
        ld hl,txt_m_loaded      ; oui : rien à faire
        jp dsk_message
sbh_load:
        ld hl,song_bank
        ld de,txt_ext_smp
        call make_fname         ; -> HL = "NOM.SMP", B = longueur
        call smp_load_bank      ; -> A = 0 si chargée
        or a
        ld hl,txt_m_nobank
        jp nz,dsk_message       ; absente : le morceau est quand même là
        ld hl,song_bank
        call smp_set_name       ; la banque prend ce nom
        xor a
        ld (cur_smp),a
        ld hl,txt_m_withbank
        jp dsk_message

txt_m_withbank: db "MORCEAU ET BANQUE DE SAMPLES CHARGES",0
txt_m_nobank:   db "MORCEAU CHARGE (BANQUE .SMP ABSENTE)",0

; ============================================================================
; Digidrums : mise en attente, durée, nom du sample (la lecture elle-même,
; dg_play, est en zone haute : hizone.asm).  On n'y arrive que si la zone
; haute est installée (tests faits par l'appelant).
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
