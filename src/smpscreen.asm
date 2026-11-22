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
; f3, puis D : on choisit parmi les fichiers .SMP de la disquette.
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
        call txt_out
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
        call txt_out
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
        call txt_out
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
        call txt_out
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
        call txt_out
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
        cp 19
        jr z,smp_take           ; O : prendre un sample dans une banque
        ret

; O : la routine est en zone haute ; il faut une banque en mémoire
smp_take:
        ld a,(smp_count)
        or a
        ld hl,txt_s_nobank
        jp z,smp_message
        jp smp_take_hi

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

; --- Choix d'une banque depuis l'écran f3 (touche D) -------------------------
; On lit le catalogue de la disquette (répertoire AMSDOS) et on affiche les
; fichiers .SMP en bas de l'écran : flèches pour choisir, RETURN pour charger,
; ESC pour annuler.  Le champ NOM reste celui du morceau (.SNG).
CHOOSE_ROW  equ 19              ; première ligne de la liste des fichiers
CHOOSE_ROWS equ 6               ; 6 lignes x 4 colonnes de 10 caractères :
CHOOSE_PAGE equ 24              ;   24 noms par page
MAX_FILES   equ 64              ; tout le catalogue AMSDOS

disk_load_bank:
        ld hl,txt_ext_smp       ; on choisit parmi les fichiers .SMP
        call choose_file        ; -> Carry si choisi, HL = nom complet,
        ret nc                  ;    B = sa longueur, DE = nom sur 8 caractères
disk_load_bank_named:           ; (le fichier déjà choisi : panneau DISQUE)
        push de                 ; on garde le nom pour la banque
        push bc                 ; et le nom complet pour le chargement
        push hl
        ld hl,txt_m_loading     ; « chargement en cours »
        call dsk_message
        pop hl                  ; HL = nom complet
        pop bc                  ; B = sa longueur
        call smp_load_bank      ; -> A = résultat
        pop hl                  ; HL = nom choisi (8 caractères)
        push af
        or a
        jr nz,dlb_msg           ; échec : la banque ne change pas de nom
        call smp_set_name       ; la banque prend ce nom
        xor a                   ; on revient au premier sample
        ld (cur_smp),a
dlb_msg:
        pop af
        call smp_load_text      ; HL = message pour ce résultat
        jp dsk_message

; ----------------------------------------------------------------------------
; Choix d'un fichier de la disquette.  HL = extension (".SMP", ".INS"...)
; On lit le catalogue, on affiche les fichiers de cette extension en bas de
; l'écran (lignes 19 à 24) et on laisse choisir avec les flèches.
; Sortie : Carry = 1 si un fichier a été choisi.  HL = nom complet
;          (smp_fname, "NOM.EXT"), B = sa longueur, DE = nom sur 8 caractères.
;          Carry = 0 : annulé, ou erreur (le message est déjà affiché).
; ----------------------------------------------------------------------------
choose_file:
        ld (scan_ext),hl        ; extension cherchée dans le catalogue
        call silence            ; plus de son pendant l'accès disque
        ld hl,txt_s_reading     ; « lecture du catalogue »
        call dsk_message
        call smp_scan_dir       ; -> A = 0 si le catalogue a été lu
        or a
        jr z,cf_scanned
        ld hl,txt_s_nocat       ; 4 : pas d'AMSDOS
        cp 4
        jr z,cf_fail
        ld hl,txt_m_error       ; 1 : disquette illisible
cf_fail:
        call dsk_message        ; on explique pourquoi
        or a                    ; Carry = 0 : rien de choisi
        ret
cf_scanned:
        ld a,(smp_nfiles)       ; aucun fichier de cette extension ?
        or a
        ld hl,txt_s_nofile
        jr z,cf_fail
        ld hl,smp_files         ; liste : les noms de 8 caractères,
        ld (ch_names),hl
        ld (ch_count),a         ;   leur nombre,
        ld hl,8*256+CHOOSE_ROWS ;   8 caractères par nom, 6 lignes,
        ld (ch_rows),hl         ;   (ch_rows puis ch_len)
        ld hl,CHOOSE_ROW*256+1  ;   colonne 1, ligne 19,
        ld (ch_col0),hl         ;   (ch_col0 puis ch_row0)
        ld hl,CHOOSE_PAGE*256+10  ; colonnes de 10 caractères, 24 noms par
        ld (ch_colw),hl           ;   page (ch_colw puis ch_page)
        call choose_clear       ; bas de l'écran effacé
        call choose_run         ; -> Carry si RETURN, A = fichier choisi
        push af
        ld a,255                ; les autres listes : une seule page
        ld (ch_page),a
        call choose_clear       ; on efface la liste
        pop af
        jr c,cf_chosen
        ld hl,txt_m_none        ; annulé : message effacé
        jr cf_fail
cf_chosen:
        call choose_name        ; HL = nom choisi (8 caractères)
        push hl
        ld de,(scan_ext)        ; nom sans espaces + extension
        call make_fname         ; -> HL = nom complet, B = longueur
        pop de                  ; DE = nom choisi (8 caractères)
        scf                     ; Carry = 1 : un fichier a été choisi
        ret

; Nom de fichier : HL = nom sur 8 caractères (espaces ou 0 à la fin),
; DE = extension (4 caractères, point compris).
; Sortie : HL = smp_fname ("NOM.EXT"), B = sa longueur.
make_fname:
        push de
        ld de,smp_fname
        ld b,8
        ld c,0                  ; C = longueur
mf_copy:
        ld a,(hl)
        cp ' '+1                ; les espaces (et les 0) ne comptent pas
        jr c,mf_skip
        ld (de),a
        inc de
        inc c
mf_skip:
        inc hl
        djnz mf_copy
        pop hl                  ; HL = extension
        ld b,4
mf_ext:
        ld a,(hl)
        ld (de),a
        inc hl
        inc de
        inc c
        djnz mf_ext
        ld b,c                  ; B = longueur
        ld hl,smp_fname
        ret

; ----------------------------------------------------------------------------
; Liste de choix, réglée par ch_names, ch_count, ch_len, ch_rows, ch_colw,
; ch_col0 et ch_row0.  Les noms sont rangés en colonnes de ch_rows lignes.
; Flèches haut / bas : nom précédent / suivant ; gauche / droite : colonne
; précédente / suivante ; RETURN : choisir ; ESC : annuler.
; Sortie : Carry = 1 et A = numéro choisi, ou Carry = 0 si ESC.
; ----------------------------------------------------------------------------
choose_run:
        xor a                   ; le premier nom est choisi, page 1
        ld (smp_pick),a
        ld (ch_top),a
cr_redraw:
        xor a
cr_draw:                        ; on affiche la page (choose_draw saute
                                ; les noms des autres pages)
        push af
        call choose_draw
        pop af
        inc a
        ld hl,ch_count
        cp (hl)
        jr nz,cr_draw
        ld hl,txt_s_choose      ; « flèches puis RETURN »
        call dsk_message
cr_flush:                       ; on vide les frappes en attente
        call KM_READ_CHAR
        jr c,cr_flush
cr_wait:
        call KM_WAIT_CHAR       ; attend une touche
        cp 13
        jr z,cr_ok              ; RETURN : choisi
        cp #FC
        jr z,cr_esc             ; ESC : on annule
        ld hl,smp_pick
        ld b,(hl)               ; B = choix actuel
        ld c,b                  ; C = nouveau choix
        cp #F0
        jr z,cr_up
        cp #F1
        jr z,cr_down
        cp #F2
        jr z,cr_left
        cp #F3
        jr z,cr_right
        jr cr_wait              ; autre touche : ignorée
cr_up:                          ; flèche haut : nom précédent
        ld a,b
        or a
        jr z,cr_wait
        dec c
        jr cr_move
cr_down:                        ; flèche bas : nom suivant
        ld a,(ch_count)
        dec a
        cp b
        jr z,cr_wait
        inc c
        jr cr_move
cr_left:                        ; flèche gauche : colonne précédente
        ld a,(ch_rows)
        ld c,a
        ld a,b
        sub c
        jr c,cr_wait
        ld c,a
        jr cr_move
cr_right:                       ; flèche droite : colonne suivante
        ld a,(ch_rows)
        add a,b
        ld hl,ch_count
        cp (hl)
        jr nc,cr_wait
        ld c,a
cr_move:
        ld a,c
        ld (smp_pick),a
        push bc
        call ch_set_top         ; le choix est-il sur une autre page ?
        pop bc
        jr z,cr_same_page
        call choose_clear       ; oui : on affiche la nouvelle page
        jr cr_redraw
cr_same_page:
        ld a,b
        call choose_draw        ; l'ancien redevient normal
        ld a,(smp_pick)
        call choose_draw        ; le nouveau en jaune inversé
        jr cr_wait
cr_ok:
        ld a,(smp_pick)         ; A = numéro choisi
        scf
        ret
cr_esc:
        ld a,KEY_ESC            ; on attend qu'ESC soit relâchée, pour ne pas
        call KM_TEST_KEY        ; qu'elle compte comme « quitter »
        jr nz,cr_esc
        or a                    ; Carry = 0 : annulé
        ret

; HL = nom numéro A de la liste (ch_names + A x ch_len)
choose_name:
        ld hl,(ch_names)
        or a
        ret z                   ; le premier : rien à ajouter
        ld b,a
        ld a,(ch_len)
        ld e,a
        ld d,0
cn_add:
        add hl,de               ; un nom plus loin
        djnz cn_add
        ret

; Affiche le nom A de la liste, en jaune inversé s'il est choisi.
; Colonne = ch_col0 + ch_colw x (A / ch_rows), ligne = ch_row0 + (A mod ch_rows).
choose_draw:
        ld (cd_i),a
        ld hl,ch_top            ; hors de la page affichée : rien
        sub (hl)
        ret c
        ld hl,ch_page
        cp (hl)
        ret nc
        ld hl,ch_rows
        ld c,(hl)               ; C = lignes par colonne
        ld b,0                  ; B = A / ch_rows, A = A modulo ch_rows
cd_div:
        cp c
        jr c,cd_pos
        sub c
        inc b
        jr cd_div
cd_pos:
        ld hl,ch_row0
        add a,(hl)
        ld l,a                  ; L = ligne
        ld a,(ch_col0)          ; colonne = ch_col0 + ch_colw x B
        inc b
cd_col:
        dec b
        jr z,cd_col_ok
        ld h,a
        ld a,(ch_colw)
        add a,h
        jr cd_col
cd_col_ok:
        ld h,a                  ; H = colonne
        call TXT_SET_CURSOR
        ld a,(cd_i)
        ld hl,smp_pick
        cp (hl)
        jr nz,cd_normal
        ld a,1                  ; choisi : fond jaune, texte bleu
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        jr cd_text
cd_normal:
        xor a                   ; les autres : fond bleu, texte orange
        call TXT_SET_PAPER
        ld a,3
        call TXT_SET_PEN
cd_text:
        ld a,(cd_i)
        call choose_name        ; HL = le nom
        ld a,(ch_len)
        ld b,a
        call print_n            ; on l'affiche
        xor a
        jp TXT_SET_PAPER

; Page du nom A : ch_top = A - (A modulo ch_page).  Z = 1 si elle ne change pas.
ch_set_top:
        ld b,a
        ld a,(ch_page)
        ld c,a
        ld a,b
cst_mod:
        sub c
        jr nc,cst_mod
        add a,c                 ; A = nom modulo ch_page
        neg
        add a,b                 ; A = premier nom de sa page
        ld hl,ch_top
        cp (hl)
        ld (hl),a               ; (LD ne touche pas aux drapeaux)
        ret

; Efface le bas de l'écran (lignes 19 à 25), là où s'affiche la liste
choose_clear:
        ld h,0                  ; fenêtre de texte : lignes 19 à 25
        ld d,39
        ld l,18
        ld e,24
        call TXT_WIN_ENABLE
        xor a
        call TXT_SET_PAPER
        call TXT_CLEAR_WINDOW
        ld h,0                  ; on rend tout l'écran au texte
        ld d,39
        ld l,0
        ld e,24
        call TXT_WIN_ENABLE
        ld hl,quit_line         ; la ligne 25 a été effacée : on la remet
        jp print_list

quit_line:
        db 1,25,3,0,"ESC MAINTENUE 1 SECONDE : QUITTER",0
        db #FF

; ----------------------------------------------------------------------------
; Lecture du catalogue : remplit smp_files (noms de 8 caractères) et
; smp_nfiles avec les fichiers de la disquette du lecteur A dont l'extension
; est celle pointée par scan_ext (".SMP", ".INS"...).
; Sortie : A = 0 tout va bien, 1 = erreur de lecture, 4 = AMSDOS absent.
;
; On lit les 4 secteurs du répertoire (64 entrées de 32 octets) avec la
; commande cachée d'AMSDOS « lecture de secteur » (#84) :
;   HL = tampon, E = lecteur (0 = A), D = piste, C = numéro de secteur.
; On la trouve avec KL_FIND_COMMAND, puis on l'appelle par RST #18 (appel
; « lointain » : la routine est dans la ROM d'AMSDOS).
; Format DATA : répertoire en piste 0, secteurs #C1 à #C4.
; Format SYSTEME (si DATA échoue) : piste 2, secteurs #41 à #44.
; ----------------------------------------------------------------------------
smp_scan_dir:
        xor a
        ld (smp_nfiles),a
        ld (dir_files),a        ; panneau DISQUE : fichiers et blocs utilisés
        ld hl,0
        ld (dir_blocks),hl
        ld a,178                ; format DATA : 178 blocs de 1 Ko
        ld (dir_cap),a
        xor a
        ld a,(rsx_found)        ; commande déjà trouvée ?
        or a
        jr nz,ssd_have
        ld hl,rsx_read_name
        call KL_FIND_COMMAND    ; -> HL = adresse, C = ROM
        ld a,4
        ret nc                  ; pas trouvée : pas d'AMSDOS
        ld (rsx_far),hl
        ld a,c
        ld (rsx_far+2),a
        ld a,1
        ld (rsx_found),a
ssd_have:
        ld d,0                  ; format DATA
        ld c,#C1
        call ssd_read4
        jr c,ssd_parse
        ld a,169                ; format SYSTEME : 169 blocs
        ld (dir_cap),a
        ld d,2
        ld c,#41
        call ssd_read4
        ld a,1
        ret nc
ssd_parse:
        ld hl,io_buffer         ; 64 entrées de 32 octets
        ld b,64
ssd_entry:
        push bc
        push hl
        ld a,(hl)               ; octet 0 = utilisateur (#E5 = effacée)
        cp 16
        jr nc,ssd_next
        call ssd_count          ; fichiers et blocs (tous les types)
        ld de,12                ; octet 12 = numéro d'extent : 0 seulement
        add hl,de               ; (un gros fichier a plusieurs entrées)
        ld a,(hl)
        or a
        jr nz,ssd_next
        pop hl
        push hl
        ld de,9                 ; octets 9 à 11 = extension (bit 7 = attribut)
        add hl,de
        ld de,(scan_ext)        ; extension cherchée (".SMP", ".INS"...)
        inc de                  ; sans le point
        ld b,3
ssd_ext:
        ld a,(hl)
        and #7F
        ex de,hl
        cp (hl)
        ex de,hl
        jr nz,ssd_next
        inc hl
        inc de
        djnz ssd_ext
        ld a,(smp_nfiles)       ; c'est un .SMP : on garde son nom
        cp MAX_FILES
        jr nc,ssd_next
        ld l,a                  ; HL = place du nom dans smp_files :
        ld h,0                  ;   smp_files + 8 x numéro (jusqu'à 504)
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,smp_files
        add hl,de
        ex de,hl
        pop hl
        push hl
        inc hl                  ; octets 1 à 8 = nom
        ld b,8
ssd_name:
        ld a,(hl)
        and #7F
        ld (de),a
        inc hl
        inc de
        djnz ssd_name
        ld hl,smp_nfiles
        inc (hl)
ssd_next:
        pop hl
        ld de,32                ; entrée suivante
        add hl,de
        pop bc
        djnz ssd_entry
        xor a
        ret

; Compte l'entrée HL (gardé) : un fichier de plus si c'est sa 1re entrée,
; et ses blocs (octets 16 à 31 non nuls)
ssd_count:
        push hl
        ld de,12
        add hl,de
        ld a,(hl)
        or a
        jr nz,ssc_blocks
        ld a,(dir_files)
        inc a
        ld (dir_files),a
ssc_blocks:
        pop hl
        push hl
        ld de,16
        add hl,de
        ld b,16
ssc_loop:
        ld a,(hl)
        or a
        jr z,ssc_next
        push hl
        ld hl,(dir_blocks)
        inc hl
        ld (dir_blocks),hl
        pop hl
ssc_next:
        inc hl
        djnz ssc_loop
        pop hl
        ret

dir_files:  db 0                ; catalogue : nombre de fichiers,
dir_blocks: dw 0                ;   blocs utilisés,
dir_cap:    db 178              ;   capacité (blocs de 1 Ko)

; Lit 4 secteurs consécutifs (piste D, à partir du secteur C) dans io_buffer.
; Carry = 1 si tout s'est bien passé.
ssd_read4:
        ld hl,io_buffer
        ld b,4
ssd_rd:
        push bc
        push de
        push hl
        ld e,0                  ; lecteur A
        rst #18                 ; appel lointain de la commande #84
        dw rsx_far
        pop hl
        pop de
        pop bc
        ret nc                  ; erreur de lecture
        inc h                   ; secteur suivant : 512 octets plus loin
        inc h
        inc c
        djnz ssd_rd
        scf
        ret

rsx_read_name: db #84           ; nom de la commande : un seul caractère,
                                ; bit 7 à 1 (dernier caractère du nom)

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
        jp txt_out
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
        call txt_out
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
txt_s_nobank:   db "AUCUNE BANQUE : f9 POUR EN CHARGER",0
txt_s_playing:  db "ECOUTE... (ESPACE : ARRET)",0
txt_s_nomem:    db "PAS ASSEZ DE MEMOIRE POUR LES SAMPLES",0
txt_s_reading:  db "LECTURE DU CATALOGUE...",0
txt_s_nocat:    db "CATALOGUE ILLISIBLE (AMSDOS ABSENT ?)",0
txt_s_nofile:   db "AUCUN FICHIER DE CE TYPE SUR LA DISQUETTE",0
txt_s_choose:   db "FLECHES PUIS RETURN (ESC : ANNULER)",0

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
        db 1,24,2,0, "f8 SAUVER f9 CHARGER O PRENDRE 1 SAMPLE",0
        db 1,25,3,0, "ESC MAINTENUE 1 SECONDE : QUITTER",0
        db #FF
