; ============================================================================
; SEQ-16 - Ecran f4 : Sample Composer (phase 2, version minimale)
;
; On y voit la banque de samples chargée, on choisit un sample, on l'écoute
; et on règle son grain : fréquence, décimation, bits, courbe.  Les réglages
; sont gardés dans la fiche du sample, en mémoire ; ils ne changent pas les
; données (la sauvegarde de la banque viendra en phase 6).
;
; Touches :
;   ESPACE            écouter le sample choisi (ESPACE à nouveau : arrêt)
;   touches du piano  écouter le sample à cette hauteur (-12 à +11 demi-tons ;
;                     la rangée du haut, à partir de la touche du DO, joue la
;                     hauteur d'origine)
;   haut / bas        choisir un réglage
;   gauche / droite   changer sa valeur (avec SHIFT : par 10)
;   CTRL + g. / d.    sample précédent / suivant
;
; Au premier passage sur cet écran, le programme charge DRUMS.SMP (la banque
; d'usine) s'il n'y a pas encore de banque.  Pour une autre banque : écran
; f3, taper le nom, puis D.
;
; Pendant une écoute, plus rien ne bouge à l'écran : le processeur ne fait
; que jouer le sample, interruptions coupées.
; ============================================================================

SMP_LIST_ROW equ 5              ; première ligne de la liste des samples
SMP_FLD_ROW  equ 5              ; ligne du premier réglage
SMP_FLD_COL  equ 21             ; colonne des noms de réglages
SMP_VAL_COL  equ 32             ; colonne des valeurs
SMP_MSG_ROW  equ 22             ; ligne des messages
NB_SFIELDS   equ 4              ; fréquence, décimation, bits, courbe
SMP_CODE_MIN equ 62             ; durée d'un échantillon : 62 NOP = 16 kHz
SMP_CODE_MAX equ 250            ;   à 250 NOP = 4 kHz

; --- Affichage de l'écran entier ---------------------------------------------
ds_sample:
        ld hl,smp_text          ; textes fixes
        call print_list
        xor a
        call TXT_SET_PAPER
        ld a,(smp_ok)
        or a
        jr nz,dss_mem_ok
        ld hl,txt_s_nomem       ; la zone haute n'est pas libre : rien à faire
        call smp_message
        jp smp_show_all
dss_mem_ok:
        ld a,(smp_count)        ; pas encore de banque : on essaie DRUMS.SMP
        or a
        jp nz,smp_show_all
        ld a,(smp_tried)
        or a
        jp nz,smp_show_all      ; (une seule fois)
        inc a
        ld (smp_tried),a
        call silence
        ld hl,txt_s_loading
        call smp_message
        ld hl,txt_drums_file
        ld b,9                  ; "DRUMS.SMP" = 9 caractères
        call smp_load_bank
        push af
        or a
        jr nz,dss_failed
        ld hl,txt_drums_name    ; nom affiché de la banque
        call smp_set_name
dss_failed:
        pop af
        call smp_load_text      ; HL = message selon le résultat
        call smp_message
        ; continue dans smp_show_all

smp_show_all:
        call smp_show_bank
        call smp_draw_list
        xor a
ssa_loop:
        push af
        call smp_draw_field
        pop af
        inc a
        cp NB_SFIELDS
        jr nz,ssa_loop
        jp smp_draw_period

; Nom de la banque et mémoire utilisée / disponible
smp_show_bank:
        ld hl,#0A02             ; colonne 10, ligne 2
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PEN
        ld hl,smp_name
        ld b,8
        call print_n
        ld hl,#1D02             ; colonne 29, ligne 2 : utilisé / disponible
        call TXT_SET_CURSOR
        ld hl,0
        ld a,(smp_count)
        or a
        jr z,ssb_used
        ld hl,(smp_bank_len)
ssb_used:
        call print_u16
        ld a,'/'
        call TXT_OUTPUT
        ld hl,BANK_MAX
        jp print_u16

; Toute la liste (16 lignes)
smp_draw_list:
        xor a
sdl_loop:
        push af
        call smp_draw_row
        pop af
        inc a
        cp 16
        jr nz,sdl_loop
        ret

; Ligne A de la liste : numéro, nom, durée.  Le sample choisi en jaune inversé.
smp_draw_row:
        ld (sdr_i),a
        add a,SMP_LIST_ROW
        ld l,a
        ld h,1
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        ld a,(smp_count)
        ld b,a
        ld a,(sdr_i)
        cp b
        jr c,sdr_used
        ld b,16                 ; pas de sample ici : ligne vide
sdr_blank:
        ld a,' '
        call TXT_OUTPUT
        djnz sdr_blank
        ret
sdr_used:
        call smp_duration_ms    ; HL = durée en millisecondes
        ld (sdr_ms),hl
        ld a,(sdr_i)            ; couleurs
        ld hl,cur_smp
        cp (hl)
        jr nz,sdr_normal
        ld a,1                  ; sample choisi : fond jaune, texte bleu
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        jr sdr_text
sdr_normal:
        ld a,3
        call TXT_SET_PEN
sdr_text:
        ld a,(sdr_i)            ; numéro, à partir de 1
        inc a
        call print_dec2
        ld a,' '
        call TXT_OUTPUT
        ld a,(sdr_i)            ; nom : 6 caractères au début de la fiche
        call smp_entry
        ld b,6
        call print_n
        ld hl,(sdr_ms)          ; durée
        call print_u16
        ld hl,txt_ms
        call print_str
        xor a
        jp TXT_SET_PAPER

; Valeur du réglage A (0 = fréquence, 1 = décimation, 2 = bits, 3 = courbe)
smp_draw_field:
        ld (sdf_i),a
        add a,SMP_FLD_ROW
        ld l,a
        ld h,SMP_VAL_COL
        call TXT_SET_CURSOR
        ld a,(sdf_i)            ; le réglage en cours : jaune inversé
        ld hl,smp_field
        cp (hl)
        jr nz,sdf_normal
        ld a,1
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        jr sdf_value
sdf_normal:
        xor a
        call TXT_SET_PAPER
        ld a,3
        call TXT_SET_PEN
sdf_value:
        ld a,(smp_count)
        or a
        jr nz,sdf_have
        ld hl,txt_s_none_val    ; pas de banque : un tiret
        call print_str
        jr sdf_end
sdf_have:
        call smp_cur_ix         ; IX = fiche du sample choisi
        ld a,(sdf_i)
        or a
        jr z,sdf_freq
        dec a
        jr z,sdf_decim
        dec a
        jr z,sdf_bits
        ld a,(ix+SMPF_FLAGS)      ; courbe : bits 4-6
        rrca
        rrca
        rrca
        rrca
        and 7
        cp 5
        jr c,sdf_curve_ok
        ld a,1
sdf_curve_ok:
        add a,a                 ; 8 caractères par nom
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,smp_curve_names
        add hl,de
        ld b,8
        call print_n
        jr sdf_end
sdf_freq:
        ld a,(ix+SMPF_CODE)       ; fréquence = 1 000 000 / durée en NOP
        call smp_freq_hz
        call print_u16
        ld hl,txt_hz
        call print_str
        jr sdf_end
sdf_decim:
        ld a,(ix+SMPF_SET)        ; décimation : bits 0-2
        and 7
        ld e,a
        ld d,0
        ld hl,smp_decims
        add hl,de
        ld a,(hl)
        add a,'0'
        call TXT_OUTPUT
        ld hl,txt_s_pad7
        call print_str
        jr sdf_end
sdf_bits:
        ld a,(ix+SMPF_SET)        ; bits : bits 3-4
        rrca
        rrca
        rrca
        and 3
        ld e,a
        ld d,0
        ld hl,smp_bits_txt
        add hl,de
        ld a,(hl)
        call TXT_OUTPUT
        ld hl,txt_bits
        call print_str
sdf_end:
        xor a
        jp TXT_SET_PAPER

; Ligne d'information : durée d'un échantillon en NOP
smp_draw_period:
        ld hl,256*SMP_VAL_COL+SMP_FLD_ROW+NB_SFIELDS
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        ld a,3
        call TXT_SET_PEN
        ld a,(smp_count)
        or a
        ld hl,txt_s_none_val
        jp z,print_str
        call smp_cur_ix
        ld a,(ix+SMPF_CODE)
        call print_dec3
        ld hl,txt_nop
        jp print_str

; IX = fiche du sample choisi
smp_cur_ix:
        ld a,(cur_smp)
        call smp_entry
        push hl
        pop ix
        ret

; --- Commandes ---------------------------------------------------------------
smp_cmd:
        ld a,(rc_index)
        or a
        jp z,smp_listen         ; ESPACE : écouter
        cp 6
        jr z,smp_left
        cp 7
        jr z,smp_right
        cp 8
        jr z,smp_up
        cp 9
        jr z,smp_down
        ret

smp_up:
        ld a,(smp_field)        ; réglage précédent
        or a
        ret z
        dec a
        jr smp_set_field
smp_down:
        ld a,(smp_field)        ; réglage suivant
        cp NB_SFIELDS-1
        ret nc
        inc a
smp_set_field:
        ld hl,smp_field
        ld b,(hl)
        ld (hl),a
        ld a,b
        call smp_draw_field     ; l'ancien redevient normal
        ld a,(smp_field)
        jp smp_draw_field       ; le nouveau en jaune inversé

smp_left:
        ld a,(mod_ctrl)
        or a
        jr nz,smp_prev
        xor a                   ; 0 = diminuer
        jr smp_change
smp_right:
        ld a,(mod_ctrl)
        or a
        jr nz,smp_next
        ld a,1                  ; 1 = augmenter
        jr smp_change

smp_prev:                       ; CTRL + gauche : sample précédent
        ld a,(cur_smp)
        or a
        ret z
        dec a
        jr smp_select
smp_next:                       ; CTRL + droite : sample suivant
        ld a,(smp_count)
        ld b,a
        ld a,(cur_smp)
        inc a
        cp b
        ret nc
smp_select:
        ld hl,cur_smp
        ld b,(hl)
        ld (hl),a
        ld a,b
        call smp_draw_row       ; l'ancien redevient normal
        ld a,(cur_smp)
        call smp_draw_row
        jp smp_show_all_fields

; Change le réglage en cours.  A = 0 pour diminuer, 1 pour augmenter.
smp_change:
        ld (sc_dir),a
        ld a,(smp_count)
        or a
        ret z                   ; pas de banque
        call smp_cur_ix
        ld a,(smp_field)
        or a
        jr z,sc_freq
        dec a
        jr z,sc_decim
        dec a
        jr z,sc_bits
        ld a,(ix+SMPF_FLAGS)      ; courbe : 0 à 4, bits 4-6
        rrca
        rrca
        rrca
        rrca
        and 7
        ld b,4
        call sc_step
        add a,a
        add a,a
        add a,a
        add a,a
        ld b,a
        ld a,(ix+SMPF_FLAGS)
        and %10001111
        or b
        ld (ix+SMPF_FLAGS),a
        jr sc_done
sc_decim:
        ld a,(ix+SMPF_SET)        ; décimation : 0 à 5, bits 0-2
        and 7
        ld b,5
        call sc_step
        ld b,a
        ld a,(ix+SMPF_SET)
        and %11111000
        or b
        ld (ix+SMPF_SET),a
        jr sc_done
sc_bits:
        ld a,(ix+SMPF_SET)        ; bits : 0 à 3 (4, 3, 2, 1 bits), bits 3-4
        rrca
        rrca
        rrca
        and 3
        ld b,3
        call sc_step
        add a,a
        add a,a
        add a,a
        ld b,a
        ld a,(ix+SMPF_SET)
        and %11100111
        or b
        ld (ix+SMPF_SET),a
        jr sc_done
sc_freq:
        ld a,(mod_shift)        ; pas de 1 NOP, ou de 10 avec SHIFT
        or a
        ld c,1
        jr z,scf_step
        ld c,10
scf_step:
        ld a,(sc_dir)           ; plus aigu = échantillon plus court
        or a
        ld a,(ix+SMPF_CODE)
        jr z,scf_slower
        sub c                   ; plus rapide, pas sous SMP_CODE_MIN
        jr c,scf_min
        cp SMP_CODE_MIN
        jr nc,scf_store
scf_min:
        ld a,SMP_CODE_MIN
        jr scf_store
scf_slower:
        add a,c                 ; plus lent, pas au-dessus de SMP_CODE_MAX
        jr c,scf_max
        cp SMP_CODE_MAX+1
        jr c,scf_store
scf_max:
        ld a,SMP_CODE_MAX
scf_store:
        ld (ix+SMPF_CODE),a
        call smp_draw_period    ; la durée en NOP et celle du sample changent
        ld a,(cur_smp)
        call smp_draw_row
sc_done:
        ld a,(smp_field)
        jp smp_draw_field

; A = valeur de 0 à B, augmentée ou diminuée de 1 selon sc_dir, sans sortir
; de 0 à B
sc_step:
        ld c,a
        ld a,(sc_dir)
        or a
        ld a,c
        jr z,scs_down
        cp b
        ret nc                  ; déjà au maximum
        inc a
        ret
scs_down:
        or a
        ret z                   ; déjà à 0
        dec a
        ret

smp_show_all_fields:
        xor a
ssf_loop:
        push af
        call smp_draw_field
        pop af
        inc a
        cp NB_SFIELDS
        jr nz,ssf_loop
        jp smp_draw_period

; --- Ecoute ------------------------------------------------------------------
smp_listen:
        ld b,0                  ; hauteur d'origine
        jr sl_go
smp_piano:                      ; touche du piano : -12 à +11 demi-tons
        ld a,#FF                ; pas de « relâche » à gérer après l'écoute
        ld (aud_key),a
        ld a,(rp_index)
        sub 12
        ld b,a
sl_go:
        ld a,(smp_count)
        or a
        jr nz,sl_have
        ld hl,txt_s_nobank
        jp smp_message
sl_have:
        push bc
        ld hl,txt_s_playing     ; l'écran ne bougera plus pendant l'écoute
        call smp_message
        pop bc
        ld a,(cur_smp)
        ld c,0                  ; voie A
        call smp_play_sample
        ld hl,txt_m_none        ; message effacé
        jp smp_message

; --- Chargement depuis l'écran f3 (touche D) ---------------------------------
disk_load_bank:
        call silence
        ld hl,txt_ext_smp
        call build_filename_ext ; NOM.SMP
        ret nc
        ld hl,txt_m_loading
        call dsk_message
        ld a,(fname_len)
        ld b,a
        ld hl,fname_full
        call smp_load_bank
        push af
        or a
        jr nz,dlb_msg
        ld hl,fname             ; la banque prend le nom du champ NOM
        call smp_set_name
        xor a                   ; on revient au premier sample
        ld (cur_smp),a
dlb_msg:
        pop af
        call smp_load_text
        jp dsk_message

; HL = message pour le résultat A de smp_load_bank
smp_load_text:
        ld hl,txt_s_loaded
        or a
        ret z
        ld hl,txt_m_error
        dec a
        ret z
        ld hl,txt_s_big
        dec a
        ret z
        ld hl,txt_s_bad
        ret

; Nom de la banque (8 caractères) recopié depuis HL
smp_set_name:
        ld de,smp_name
        ld bc,8
        ldir
        ret

; Message sur la ligne des messages de l'écran f4.  HL = texte
smp_message:
        push hl
        ld hl,256*1+SMP_MSG_ROW
        jp msg_row

; Affiche HL (0 à 65535) sur 5 caractères, espaces devant
print_u16:
        ld b,0                  ; B = 1 dès qu'un chiffre a été écrit
        ld de,10000
        call pu_digit
        ld de,1000
        call pu_digit
        ld de,100
        call pu_digit
        ld de,10
        call pu_digit
        ld a,l                  ; les unités, toujours écrites
        add a,'0'
        jp TXT_OUTPUT
pu_digit:                       ; chiffre = combien de fois DE rentre dans HL
        ld a,'0'-1
pu_sub:
        inc a
        or a                    ; (Carry = 0 pour SBC)
        sbc hl,de
        jr nc,pu_sub
        add hl,de               ; une soustraction de trop : on la rend
        cp '0'
        jr nz,pu_out
        bit 0,b                 ; un 0 en tête s'écrit comme un espace
        jr nz,pu_print
        ld a,' '
        jr pu_print
pu_out:
        ld b,1
pu_print:
        push hl
        push de
        push bc
        call TXT_OUTPUT
        pop bc
        pop de
        pop hl
        ret

txt_drums_file: db "DRUMS.SMP"
txt_drums_name: db "DRUMS   "
txt_ext_smp:    db ".SMP",0
txt_ms:         db "MS",0
txt_hz:         db " HZ",0
txt_nop:        db " NOP",0
txt_bits:       db " BITS ",0
txt_s_pad7:     db "       ",0
txt_s_none_val: db "-       ",0
txt_s_loading:  db "CHARGEMENT DE DRUMS.SMP...",0
txt_s_loaded:   db "BANQUE CHARGEE",0
txt_s_big:      db "BANQUE TROP GRANDE POUR LA MEMOIRE",0
txt_s_bad:      db "CE FICHIER N'EST PAS UNE BANQUE .SMP",0
txt_s_nobank:   db "AUCUNE BANQUE : f3, NOM, PUIS D",0
txt_s_playing:  db "ECOUTE... (ESPACE : ARRET)",0
txt_s_nomem:    db "PAS ASSEZ DE MEMOIRE POUR LES SAMPLES",0

smp_text:
        db 1,2,2,0,  "BANQUE :",0
        db 21,2,2,0, "MEMOIRE:",0
        db 1,4,1,0,  "N  NOM   DUREE",0
        db SMP_FLD_COL,4,1,0, "REGLAGES",0
        db SMP_FLD_COL,5,2,0, "FREQUENCE",0
        db SMP_FLD_COL,6,2,0, "DECIMATION",0
        db SMP_FLD_COL,7,2,0, "BITS",0
        db SMP_FLD_COL,8,2,0, "COURBE",0
        db SMP_FLD_COL,9,2,0, "PERIODE",0
        db SMP_FLD_COL,12,3,0,"ESPACE",0
        db SMP_FLD_COL+9,12,2,0,"ECOUTER",0
        db SMP_FLD_COL,13,3,0,"PIANO",0
        db SMP_FLD_COL+9,13,2,0,"HAUTEUR",0
        db SMP_FLD_COL,14,3,0,240,241,0
        db SMP_FLD_COL+9,14,2,0,"REGLAGE",0
        db SMP_FLD_COL,15,3,0,242,243,0
        db SMP_FLD_COL+9,15,2,0,"VALEUR",0
        db SMP_FLD_COL,16,3,0,"SHIFT ",242,243,0
        db SMP_FLD_COL+9,16,2,0,"PAR 10",0
        db SMP_FLD_COL,17,3,0,"CTRL  ",242,243,0
        db SMP_FLD_COL+9,17,2,0,"SAMPLE",0
        db 1,24,3,0, "f3",0
        db 4,24,2,0, "NOM PUIS D : CHARGER UNE BANQUE",0
        db 1,25,3,0, "ESC MAINTENUE 1 SECONDE : QUITTER",0
        db #FF
