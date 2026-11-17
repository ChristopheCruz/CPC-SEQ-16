; ============================================================================
; SEQ-16 - Etapes 6 et 9 : instruments, mixage et disquette
;          + samples, phase 2 : lecture des samples, écran f4
;
; Quatre écrans : f1 = le séquenceur (édition de la grille), f2 = l'éditeur
; d'instrument (ADSR, bruit, enveloppe matérielle, arpège, vibrato,
; glissando), f3 = mixage des 4 voix et sauvegarde sur disquette,
; f4 = Sample Composer (écoute et grain des samples).
;
; Lancement sur le CPC :  RUN"SEQ16
; ============================================================================

        org #4000
        run start

        include 'firmware.asm'

KEY_SPACE equ 47
KEY_LEFT  equ 8
KEY_RIGHT equ 1
KEY_F5    equ 12
KEY_DEL   equ 79
KEY_CLR   equ 16
KEY_SHIFT equ 21
KEY_CTRL  equ 23
KEY_TAB   equ 68
KEY_CAPS  equ 70
KEY_F1    equ 13
KEY_F2    equ 14
KEY_F3    equ 5
KEY_F4    equ 20
KEY_F7    equ 10
KEY_RETURN equ 18
KEY_S     equ 60
KEY_L     equ 36
KEY_C     equ 62
KEY_N     equ 46
KEY_D     equ 61

GRID_ROW  equ 6                 ; première ligne écran de la grille
HEAD_ROW  equ 5                 ; ligne des numéros de pas

start:
        ld a,1                  ; Mode 1 : 40 colonnes, 4 couleurs
        call SCR_SET_MODE
        ld bc,COL_BLEU*257
        call SCR_SET_BORDER
        ld a,3                  ; l'encre 3 devient orange
        ld bc,COL_ORANGE*257
        call SCR_SET_INK

        ld c,7                  ; RUN" d'un fichier binaire réinitialise le
        ld de,#0040             ; système sans réveiller le lecteur de
        ld hl,#ABFF             ; disquette : on relance AMSDOS (ROM 7),
        call KL_INIT_BACK       ; sinon les sauvegardes iraient sur cassette
        call smp_install        ; DE, HL = mémoire libre : on installe la
                                ; routine de lecture des samples
        ld a,#FF                ; AMSDOS : pas de message d'erreur disque à
        ld (#BE78),a            ; l'écran, c'est le programme qui les affiche
        call init_song          ; morceau d'usine
        call snd_init
        ld hl,patterns          ; motif 1
        call seq_set_pattern
        call draw_screen        ; affiche le séquenceur

; ----------------------------------------------------------------------------
; Boucle principale : un tour par image, 50 tours par seconde
; ----------------------------------------------------------------------------
main_loop:
        call MC_WAIT_FLYBACK
        halt
        halt

        call read_screen_keys   ; f1 / f2 : changement d'écran
        call read_cmd           ; touches de commande
        call read_piano         ; touches du piano
        call aud_release        ; fin de l'écoute quand la touche est lâchée
        call seq_frame          ; le séquenceur déclenche les notes du pas
        call snd_frame          ; le moteur de son les fait vivre
        ld a,(screen)
        or a
        call z,show_playhead    ; repère du pas en cours (écran séquenceur)

        ld a,KEY_ESC            ; ESC maintenue une seconde : on quitte
        call KM_TEST_KEY
        ld a,0
        jr z,ml_esc
        ld a,(esc_count)
        inc a
ml_esc:
        ld (esc_count),a
        cp 50
        jr c,main_loop

        call snd_init           ; silence, puis redémarrage du CPC
        rst 0

; ----------------------------------------------------------------------------
; Ecrans : f1 = séquenceur, f2 = instrument, f3 = disque, f4 = samples
; ----------------------------------------------------------------------------
read_screen_keys:
        ld a,KEY_F1
        call KM_TEST_KEY
        ld a,0                  ; (LD ne modifie pas les drapeaux)
        jr nz,rsk_go
        ld a,KEY_F2
        call KM_TEST_KEY
        ld a,1
        jr nz,rsk_go
        ld a,KEY_F3
        call KM_TEST_KEY
        ld a,2
        jr nz,rsk_go
        ld a,KEY_F4
        call KM_TEST_KEY
        ld a,3
        ret z
rsk_go:
        ld hl,screen
        cp (hl)
        ret z                   ; on y est déjà
        ld (hl),a
        ; continue dans draw_screen

; Efface l'écran et dessine l'écran en cours
draw_screen:
        ld a,1
        call SCR_SET_MODE       ; repasser en Mode 1 efface l'écran
        ld a,#FF
        ld (shown_pos),a
        call draw_title
        ld a,(screen)
        or a
        jr z,ds_sequencer
        dec a
        jr z,ds_instrument
        dec a
        jp nz,ds_sample         ; écran 3 : samples (smpscreen.asm)
        ld hl,dsk_text          ; écran 2 : mixage et disquette
        call print_list
        xor a
        call TXT_SET_PAPER
        jp dsk_show_all
ds_sequencer:
        ld hl,screen_text
        call print_list
        xor a
        call TXT_SET_PAPER
        jp redraw_all
ds_instrument:
        ld hl,ins_text
        call print_list
        xor a
        call TXT_SET_PAPER
        jp ins_show_all

; Bandeau du haut : nom du programme et onglets, l'écran en cours en orange
draw_title:
        ld hl,#0101
        call TXT_SET_CURSOR
        ld a,1
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        ld hl,txt_title
        call print_str
        xor a
        call dt_colors
        ld hl,txt_tab1
        call print_str
        ld a,1
        call dt_colors
        ld hl,txt_tab2
        call print_str
        ld a,2
        call dt_colors
        ld hl,txt_tab3
        call print_str
        ld a,3
        call dt_colors
        ld hl,txt_tab4
        call print_str
        xor a
        jp TXT_SET_PAPER
dt_colors:                      ; A = numéro de l'onglet à écrire
        ld hl,screen
        cp (hl)
        jr nz,dt_other
        ld a,3                  ; onglet de l'écran en cours
        call TXT_SET_PAPER
        xor a
        jp TXT_SET_PEN
dt_other:
        xor a
        call TXT_SET_PAPER
        ld a,2
        jp TXT_SET_PEN

txt_title: db "SEQ16",0          ; 5 + 7 + 8 + 10 + 10 = 40 colonnes
txt_tab1:  db " f1 SEQ",0
txt_tab2:  db " f2 INST",0
txt_tab3:  db " f3 DISQUE",0
txt_tab4:  db " f4 SAMPLE",0

; ----------------------------------------------------------------------------
; Touches de commande
; Un appui = une action.  Les flèches se répètent si on les garde enfoncées.
; ----------------------------------------------------------------------------
read_cmd:
        ld hl,cmd_table
        xor a
rc_loop:
        ld (rc_index),a
        ld a,(hl)
        push hl
        call KM_TEST_KEY
        pop hl
        jr nz,rc_found
        inc hl
        ld a,(rc_index)
        inc a
        cp 17
        jr nz,rc_loop
        ld a,#FF                ; aucune touche de commande
        ld (cmd_last),a
        ret
rc_found:
        ld a,(rc_index)
        ld hl,cmd_last
        cp (hl)
        jr z,rc_same
        ld (hl),a               ; nouvelle touche : action immédiate
        xor a
        ld (cmd_count),a
        jr rc_act
rc_same:
        cp 6
        ret c                   ; seules les flèches (6 à 9) se répètent
        cp 10
        ret nc
        ld a,(cmd_count)
        inc a
        ld (cmd_count),a
        cp 14
        ret c                   ; attente avant la répétition
        ld a,11                 ; puis une action toutes les 3 images
        ld (cmd_count),a
rc_act:
        ld a,KEY_SHIFT          ; SHIFT ou CTRL enfoncée ?
        call KM_TEST_KEY
        ld a,0                  ; (LD ne modifie pas les drapeaux)
        jr z,rc_shift
        inc a
rc_shift:
        ld (mod_shift),a
        ld a,KEY_CTRL
        call KM_TEST_KEY
        ld a,0
        jr z,rc_ctrl
        inc a
rc_ctrl:
        ld (mod_ctrl),a
        ld a,(screen)
        or a
        jr z,rc_seq
        dec a
        jp z,ins_cmd            ; écran Instrument : ses propres commandes
        dec a
        jp z,dsk_cmd            ; écran Disque : ses propres commandes
        jp smp_cmd              ; écran Samples : ses propres commandes
rc_seq:
        ld a,(rc_index)
        cp 10
        jp z,cmd_mute           ; f7 : muet / son
        ret nc                  ; les autres touches ne servent pas ici
        or a
        jp z,cmd_play
        dec a
        jp z,cmd_mode
        dec a
        jp z,cmd_del
        dec a
        jp z,cmd_clr
        dec a
        jp z,cmd_clr            ; TAB fait la même chose que CLR
        dec a
        jp z,cmd_lock
        dec a
        jp z,cmd_left
        dec a
        jp z,cmd_right
        dec a
        jp z,cmd_up
        jp cmd_down

cmd_table:
        db KEY_SPACE,KEY_F5,KEY_DEL,KEY_CLR,KEY_TAB,KEY_CAPS   ; 0 à 5
        db KEY_LEFT,KEY_RIGHT,KEY_UP,KEY_DOWN                  ; 6 à 9
        db KEY_F7,KEY_RETURN,KEY_S,KEY_L,KEY_C,KEY_N           ; 10 à 15
        db KEY_D                                               ; 16

; --- ESPACE : lecture / arrêt ---
cmd_play:
        ld a,(seq_playing)
        or a
        jr nz,cp_stop
        call seq_start
        jp show_state
cp_stop:
        call seq_stop
        jp show_state

; --- f5 : voix séparées <-> son composé ---
cmd_mode:
        call seq_stop
        ld hl,(seq_pattern)
        ld a,(hl)
        xor 1
        ld (hl),a
        xor a
        ld (cur_l),a            ; le curseur revient sur la première voix
        jp redraw_all

; --- DEL : efface la case ---
cmd_del:
        call cursor_ptr
        ld (hl),NOTE_NONE
        inc hl
        ld (hl),0
        inc hl
        ld (hl),#FF
        inc hl
        ld (hl),0
        jp draw_cursor_cell

; --- f7 : rend muette (ou à nouveau audible) la voix du curseur ---
; En son composé, les 4 voix ensemble.
cmd_mute:
        ld hl,(seq_pattern)
        ld a,(hl)
        or a
        jr nz,cm_all
        ld a,(cur_l)
        call chan_mask
        ld hl,snd_mute
        xor (hl)
        ld (hl),a
        ld a,(cur_l)
        ld (dg_l),a
        jp draw_label
cm_all:
        ld a,(snd_mute)         ; tout muet si la voix A sonne, sinon tout audible
        and 1
        ld a,15
        jr z,cm_set
        xor a
cm_set:
        ld (snd_mute),a
        xor a
        ld (dg_l),a
        jp draw_label

; --- CAPS LOCK : verrouille l'instrument (ou le son) de saisie ---
; Verrouillé, il ne change plus quand le curseur passe sur une note existante.
cmd_lock:
        ld a,(inst_lock)
        xor 1
        ld (inst_lock),a
        jp show_inst

; --- CLR ou TAB : arrêt de note, puis pas suivant ---
cmd_clr:
        call cursor_ptr
        ld (hl),NOTE_OFF
        inc hl
        ld (hl),0
        inc hl
        ld (hl),#FF
        inc hl
        ld (hl),0
        jp cursor_next

; --- Flèches ---
cmd_left:
        ld a,(mod_shift)
        or a
        jp nz,inst_prev
        ld a,(mod_ctrl)
        or a
        jp nz,pat_prev
        ld a,(cur_l)            ; pas précédent
        ld b,a
        ld a,(cur_s)
        dec a
        and 15
        ld c,a
        jp move_cursor
cmd_right:
        ld a,(mod_shift)
        or a
        jp nz,inst_next
        ld a,(mod_ctrl)
        or a
        jp nz,pat_next
cursor_next:                    ; pas suivant
        ld a,(cur_l)
        ld b,a
        ld a,(cur_s)
        inc a
        and 15
        ld c,a
        jp move_cursor
cmd_up:
        ld a,(mod_shift)
        or a
        jp nz,oct_up
        ld a,(mod_ctrl)
        or a
        jp nz,speed_faster
        ld a,(cur_l)            ; voix précédente
        or a
        ret z
        dec a
        jr cmd_lane
cmd_down:
        ld a,(mod_shift)
        or a
        jp nz,oct_down
        ld a,(mod_ctrl)
        or a
        jp nz,speed_slower
        ld hl,(seq_pattern)     ; voix suivante (une seule en son composé)
        ld a,(hl)
        or a
        ret nz
        ld a,(cur_l)
        cp 3
        ret nc
        inc a
cmd_lane:
        ld b,a
        ld a,(cur_s)
        ld c,a
        jp move_cursor

; --- SHIFT + gauche/droite : instrument (ou son composé) ---
inst_prev:
        call inst_var           ; HL = variable, B = nombre de valeurs
        ld a,(hl)
        or a
        ret z
        dec (hl)
        jr inst_apply
inst_next:
        call inst_var
        ld a,(hl)
        inc a
        cp b
        ret nc
        ld (hl),a
        ; continue dans inst_apply

; L'instrument de saisie vient de changer : s'il y a une note sous le curseur,
; elle prend ce nouvel instrument et on la fait entendre un court instant.
inst_apply:
        call show_inst
        call cursor_ptr
        ld a,(hl)
        cp NOTE_OFF
        ret nc                  ; pas de note sous le curseur
        ld (en_note),a
        inc hl
        push hl
        call inst_var
        ld a,(hl)
        pop hl
        ld (hl),a
        ld (en_ins),a
        call draw_cursor_cell
        ld a,(seq_playing)
        or a
        ret nz                  ; pendant la lecture, on n'ajoute pas de son
        ld a,#FF
        ld (aud_key),a
        ld a,20                 ; écoute courte : 20 images, soit 0,4 seconde
        ld (aud_timer),a
        jp audition
inst_var:
        ld hl,(seq_pattern)
        ld a,(hl)
        or a
        ld hl,cur_inst
        ld b,NB_INST
        ret z
        ld hl,cur_son
        ld b,NB_SONS
        ret

; --- CTRL + gauche/droite : motif ---
pat_prev:
        ld a,(cur_pat)
        or a
        ret z
        dec a
        jp select_pattern
pat_next:
        ld a,(cur_pat)
        inc a
        cp NB_PAT
        ret nc
        jp select_pattern

; --- SHIFT + haut/bas : octave (1 à 6) ---
oct_up:
        ld a,(cur_oct)
        cp 6
        ret nc
        inc a
        jr oct_set
oct_down:
        ld a,(cur_oct)
        cp 2
        ret c
        dec a
oct_set:
        ld (cur_oct),a
        jp show_octave

; --- CTRL + haut/bas : tempo, de 40 à 240 BPM ---
speed_faster:
        ld a,(seq_bpm)
        cp 240
        ret nc
        inc a
        jr speed_set
speed_slower:
        ld a,(seq_bpm)
        cp 41
        ret c
        dec a
speed_set:
        ld (seq_bpm),a
        ld hl,(seq_pattern)     ; le tempo est mémorisé dans le motif
        inc hl
        ld (hl),a
        jp show_speed

; ----------------------------------------------------------------------------
; Curseur
; ----------------------------------------------------------------------------
; HL = adresse, dans le motif, de la case sous le curseur
cursor_ptr:
        ld a,(cur_l)
        ld (dg_l),a
        ld a,(cur_s)
        ld (dg_s),a
        jp cell_ptr

; Redessine la case sous le curseur
draw_cursor_cell:
        ld a,(cur_l)
        ld (dg_l),a
        ld a,(cur_s)
        ld (dg_s),a
        jp draw_cell_full

; Déplace le curseur en voix B, pas C
move_cursor:
        ld a,(cur_l)            ; on retient l'ancienne case
        ld (dg_l),a
        ld a,(cur_s)
        ld (dg_s),a
        ld a,b
        ld (cur_l),a
        ld a,c
        ld (cur_s),a
        call draw_cell_full     ; l'ancienne case redevient normale
        call draw_cursor_cell   ; la nouvelle est mise en évidence
        call pickup_inst
        ; continue dans preview_cell

; Fait entendre brièvement la note sous le curseur, quand on se déplace
; (pas pendant la lecture, ni juste après avoir posé une note au piano)
preview_cell:
        ld a,(seq_playing)
        or a
        ret nz
        ld a,(aud_key)
        cp #FF
        ret nz
        call cursor_ptr
        ld a,(hl)
        cp NOTE_OFF
        ret nc                  ; pas de note ici
        ld (en_note),a
        inc hl
        ld a,(hl)
        ld (en_ins),a
        ld a,12                 ; un quart de seconde
        ld (aud_timer),a
        jp audition

; Si le curseur est sur une note, son instrument (ou son composé) devient
; l'instrument de saisie, sauf si celui-ci est verrouillé (CAPS LOCK).
pickup_inst:
        ld a,(inst_lock)
        or a
        ret nz
        call cursor_ptr
        ld a,(hl)
        cp NOTE_OFF
        ret nc                  ; pas de note ici
        inc hl
        ld c,(hl)               ; C = instrument de la note
        call inst_var           ; HL = variable, B = nombre de valeurs
        ld a,c
        cp b
        ret nc                  ; numéro inconnu dans ce mode : on ne touche à rien
        cp (hl)
        ret z                   ; c'est déjà le bon
        ld (hl),a
        jp show_inst

; ----------------------------------------------------------------------------
; Piano : saisie d'une note sous le curseur, avec écoute immédiate
; ----------------------------------------------------------------------------
read_piano:
        ld a,(screen)
        cp 2
        ret z                   ; écran Disque : les lettres servent aux commandes
        ld hl,piano_keys
        xor a
rp_loop:
        ld (rp_index),a
        ld a,(hl)
        push hl
        call KM_TEST_KEY
        pop hl
        jr nz,rp_found
        inc hl
        ld a,(rp_index)
        inc a
        cp 24
        jr nz,rp_loop
        ld a,#FF                ; aucune touche du piano
        ld (piano_last),a
        ret
rp_found:
        ld a,(rp_index)
        ld hl,piano_last
        cp (hl)
        ret z                   ; touche déjà prise en compte
        ld (hl),a
        ld (aud_key),a
        ld a,(screen)
        cp 3
        jp z,smp_piano          ; écran Samples : le sample à cette hauteur
        or a
        jp nz,ins_piano         ; écran Instrument : simple essai du son

        ld hl,(seq_pattern)     ; valeur à écrire dans la case
        ld a,(hl)
        or a
        jr nz,rp_note           ; son composé : une vraie note
        ld a,(cur_l)
        cp 3
        jr nz,rp_note
        ld a,(rp_index)         ; voix de bruit : la touche choisit la période,
        ld b,a                  ; de 31 (grave, à gauche) à 8 (aigu, à droite)
        ld a,31
        sub b
        jr rp_write
rp_note:
        call calc_note
rp_write:
        ld (en_note),a
        call cursor_ptr
        ld a,(en_note)
        ld (hl),a               ; note
        inc hl
        push hl
        call inst_var           ; HL = instrument ou son en cours
        ld a,(hl)
        pop hl
        ld (hl),a               ; instrument (ou son composé)
        ld (en_ins),a
        inc hl
        ld (hl),#FF             ; volume de l'instrument
        inc hl
        ld (hl),0

        xor a
        ld (aud_timer),a
        call audition           ; écoute immédiate
        jp cursor_next

; A = note correspondant à la touche du piano rp_index, à l'octave de saisie
calc_note:
        ld a,(cur_oct)          ; note = 12 x octave + touche
        ld d,a
        add a,a
        add a,d
        add a,a
        add a,a
        ld b,a
        ld a,(rp_index)
        add a,b
        cp 96
        ret c
        ld a,95
        ret

; Fait entendre la note en_note avec l'instrument (ou le son) en_ins,
; sur la voix du curseur
audition:
        ld hl,(seq_pattern)
        ld a,(hl)
        or a
        jr nz,au_son
        ld a,(en_note)
        ld b,a
        ld a,(en_ins)
        ld c,a
        ld a,(cur_l)
        ld (aud_voice),a
        jp snd_note_on
au_son:
        ld a,#80                ; #80 = les 4 voix
        ld (aud_voice),a
        ld a,(en_note)
        ld b,a
        ld a,(en_ins)
        ld c,a
        jp seq_play_son

; Fin de l'écoute : quand la touche du piano est lâchée, ou à la fin du
; délai pour une écoute courte.  Pendant la lecture, le séquenceur s'en charge.
aud_release:
        ld a,(aud_key)
        cp #FF
        jr z,ar_timer
        ld e,a
        ld d,0
        ld hl,piano_keys
        add hl,de
        ld a,(hl)
        call KM_TEST_KEY
        ret nz                  ; toujours enfoncée
        ld a,#FF
        ld (aud_key),a
        jr ar_off
ar_timer:
        ld a,(aud_timer)
        or a
        ret z
        dec a
        ld (aud_timer),a
        ret nz
ar_off:
        ld a,(screen)           ; sur l'écran Instrument, l'essai s'arrête
        or a                    ; toujours quand on lâche la touche
        jr nz,ar_do
        ld a,(seq_playing)
        or a
        ret nz
ar_do:
        ld a,(aud_voice)
        bit 7,a
        jp z,snd_note_off
        xor a
        jp sst_off

; Touches du piano, dans l'ordre des notes (DO, DO#, RE, RE#, MI, FA, ...).
piano_keys:
        db 71,60,63,61,62,55,52,54,44,46,45,38      ; rangées du bas / milieu
        db 67,65,59,57,58,50,49,51,48,43,41,42      ; rangées du haut / chiffres

; ----------------------------------------------------------------------------
; Motifs
; ----------------------------------------------------------------------------
; Choix du motif.  A = 0 à 31
select_pattern:
        ld (cur_pat),a
        call seq_stop
        ld a,(cur_pat)
        call pat_addr
        call seq_set_pattern
        ld hl,(seq_pattern)     ; en son composé, une seule voix
        ld a,(hl)
        or a
        jr z,redraw_all
        xor a
        ld (cur_l),a
        ; continue dans redraw_all

redraw_all:
        call hide_playhead
        call show_pattern
        call show_state
        call show_speed
        call show_octave
        call show_inst
        call draw_heads
        call draw_grid
        jp pickup_inst          ; l'instrument de saisie suit la note du curseur

; ----------------------------------------------------------------------------
; Affichage des informations
; ----------------------------------------------------------------------------
show_pattern:                   ; numéro du motif et mode
        ld hl,#0802             ; colonne 8, ligne 2
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PEN
        ld a,(cur_pat)
        inc a
        call print_dec2
        ld a,' '
        call TXT_OUTPUT
        ld hl,(seq_pattern)
        ld a,(hl)
        or a
        ld hl,txt_sep
        jp z,print_str
        ld hl,txt_comp
        jp print_str

show_state:
        ld a,(screen)
        or a
        ret nz                  ; rien à afficher sur l'écran Instrument
        ld hl,#2102             ; colonne 33, ligne 2
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PEN
        ld a,(seq_playing)
        or a
        ld hl,txt_stop
        jp z,print_str
        ld hl,txt_play
        jp print_str

show_speed:
        ld hl,#0503             ; colonne 5, ligne 3
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PEN
        ld a,(seq_bpm)
        ; continue dans print_dec3

; Affiche A (0 à 255) sur 3 chiffres
print_dec3:
        ld c,'0'
pd3_hundreds:
        cp 100
        jr c,pd3_out
        sub 100
        inc c
        jr pd3_hundreds
pd3_out:
        push af
        ld a,c
        call TXT_OUTPUT
        pop af
        jp print_dec2

show_octave:
        ld hl,#1403             ; séquenceur : colonne 20, ligne 3
        ld a,(screen)
        or a
        jr z,so_pos
        ld hl,#2502             ; instrument : colonne 37, ligne 2
so_pos:
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PEN
        ld a,(cur_oct)
        add a,'0'
        jp TXT_OUTPUT

; Instrument de saisie (voix séparées) ou son composé de saisie.
; Verrouillé, il s'affiche en orange inversé.
show_inst:
        ld hl,#1703             ; colonne 23, ligne 3
        call TXT_SET_CURSOR
        ld a,2
        call TXT_SET_PEN
        ld hl,(seq_pattern)
        ld a,(hl)
        or a
        ld hl,txt_inst
        jr z,si_label
        ld hl,txt_son
si_label:
        call print_str
        ld a,(inst_lock)
        or a
        jr z,si_free
        ld a,3                  ; verrouillé : fond orange, texte bleu
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        jr si_value
si_free:
        ld a,3
        call TXT_SET_PEN
si_value:
        ld hl,(seq_pattern)
        ld a,(hl)
        or a
        jr nz,si_son
        ld a,(cur_inst)
        inc a
        call print_dec2
        ld a,' '
        call TXT_OUTPUT
        ld a,(cur_inst)         ; nom : 6 caractères par instrument
        ld e,a
        add a,a
        add a,e
        add a,a
        ld e,a
        ld d,0
        ld hl,inst_names
        add hl,de
        ld b,6
        call print_n
        jr si_end
si_son:
        ld a,'S'
        call TXT_OUTPUT
        ld a,(cur_son)
        add a,'1'
        call TXT_OUTPUT
si_end:
        xor a
        call TXT_SET_PAPER
        ld hl,(seq_pattern)     ; en son composé, on efface la fin de la zone
        ld a,(hl)
        or a
        ret z
        ld hl,txt_pad
        jp print_str

; Affiche le texte pointé par HL, terminé par 0
print_str:
        ld a,(hl)
        inc hl
        or a
        ret z
        call TXT_OUTPUT
        jr print_str

; Affiche B caractères à partir de HL (HL avance)
print_n:
        ld a,(hl)
        call TXT_OUTPUT
        inc hl
        djnz print_n
        ret

; Affiche A (0 à 99) sur 2 chiffres
print_dec2:
        ld c,'0'
pd_tens:
        cp 10
        jr c,pd_out
        sub 10
        inc c
        jr pd_tens
pd_out:
        push af
        ld a,c
        call TXT_OUTPUT
        pop af
        add a,'0'
        jp TXT_OUTPUT

; Affiche A (0 à 15) sur 1 chiffre hexadécimal
print_hex1:
        cp 10
        jr c,ph_digit
        add a,7                 ; de '9' à 'A'
ph_digit:
        add a,'0'
        jp TXT_OUTPUT

txt_sep:  db "VOIX SEPAREES",0
txt_comp: db "SON COMPOSE  ",0
txt_play: db "LECTURE",0
txt_stop: db "ARRET  ",0
txt_inst: db "INSTR.:",0
txt_son:  db "SON   :",0
txt_pad:  db "       ",0

; ----------------------------------------------------------------------------
; Ligne des numéros de pas, et repère du pas en cours de lecture
; ----------------------------------------------------------------------------
draw_heads:                     ; les 16 numéros, sans repère
        xor a
dhs_loop:
        ld (dh_step),a
        xor a
        ld (dh_hi),a
        call draw_head
        ld a,(dh_step)
        inc a
        cp 16
        jr nz,dhs_loop
        ret

; Dessine le numéro du pas dh_step ; dh_hi = 1 pour le mettre en évidence
draw_head:
        ld a,(dh_step)
        add a,a
        add a,7                 ; les pas commencent colonne 7, 2 colonnes chacun
        ld h,a
        ld l,HEAD_ROW
        call TXT_SET_CURSOR
        ld a,(dh_hi)
        or a
        jr z,dh_normal
        ld a,3                  ; repère : fond orange, texte bleu
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        jr dh_print
dh_normal:
        xor a
        call TXT_SET_PAPER
        ld a,(dh_step)          ; un temps sur quatre en jaune, les autres en cyan
        and 3
        ld a,1
        jr z,dh_pen
        ld a,2
dh_pen:
        call TXT_SET_PEN
dh_print:
        ld a,(dh_step)
        call print_hex1
        ld a,' '
        call TXT_OUTPUT
        xor a
        jp TXT_SET_PAPER

show_playhead:
        ld a,(seq_playing)
        or a
        jr z,hide_playhead
        ld a,(seq_pos)
        ld hl,shown_pos
        cp (hl)
        ret z                   ; le repère est déjà au bon endroit
        call hide_playhead
        ld a,(seq_pos)
        ld (shown_pos),a
        ld (dh_step),a
        ld a,1
        ld (dh_hi),a
        jp draw_head

hide_playhead:
        ld a,(shown_pos)
        cp #FF
        ret z
        ld (dh_step),a
        xor a
        ld (dh_hi),a
        ld a,#FF
        ld (shown_pos),a
        jp draw_head

; ----------------------------------------------------------------------------
; La grille : 4 voix de 16 pas, chaque case sur 2 colonnes et 3 lignes
;   ligne 1 : nom de la note        (voix de bruit : "BR")
;   ligne 2 : octave                (voix de bruit : période du bruit)
;   ligne 3 : numéro d'instrument   (son composé : numéro du son)
; La case sous le curseur est en jaune.
; ----------------------------------------------------------------------------
draw_grid:
        xor a
dg_lane:
        ld (dg_l),a
        call draw_label
        xor a
dg_line:
        ld (dg_n),a
        ld a,(dg_l)             ; ligne écran = GRID_ROW + 4 x voix + ligne
        add a,a
        add a,a
        add a,GRID_ROW
        ld b,a
        ld a,(dg_n)
        add a,b
        ld l,a
        ld h,7                  ; colonne 7
        call TXT_SET_CURSOR
        xor a
dg_step:
        ld (dg_s),a
        call draw_cell
        ld a,(dg_s)
        inc a
        cp 16
        jr nz,dg_step
        ld a,(dg_n)
        inc a
        cp 3
        jr nz,dg_line
        ld a,(dg_l)
        inc a
        cp 4
        jr nz,dg_lane
        xor a
        jp TXT_SET_PAPER

; Redessine les 3 lignes de la case (voix dg_l, pas dg_s)
draw_cell_full:
        xor a
dcf_loop:
        ld (dg_n),a
        ld a,(dg_s)
        add a,a
        add a,7
        ld h,a                  ; colonne
        ld a,(dg_l)
        add a,a
        add a,a
        add a,GRID_ROW
        ld l,a
        ld a,(dg_n)
        add a,l
        ld l,a                  ; ligne
        call TXT_SET_CURSOR
        call draw_cell
        ld a,(dg_n)
        inc a
        cp 3
        jr nz,dcf_loop
        xor a
        jp TXT_SET_PAPER

; HL = adresse, dans le motif, de la case (voix dg_l, pas dg_s)
cell_ptr:
        ld a,(dg_s)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl               ; 16 octets par pas
        ld a,(dg_l)
        add a,a
        add a,a                 ; 4 octets par voix
        ld e,a
        ld d,0
        add hl,de
        ld de,(seq_pattern)
        add hl,de
        ld de,PAT_HEADER
        add hl,de
        ret

; Dessine, à la position du curseur texte, les 2 caractères d'une ligne de
; case (voix dg_l, pas dg_s, ligne dg_n)
draw_cell:
        call cell_ptr
        ld a,(hl)
        ld (dc_note),a
        inc hl
        ld a,(hl)
        ld (dc_ins),a
        ld hl,(seq_pattern)
        ld a,(hl)
        ld (dc_mode),a

        ld c,0                  ; état : 0 = voix non utilisée
        or a
        jr z,dc_st_used
        ld a,(dg_l)             ; son composé : seule la 1re voix sert
        or a
        jr nz,dc_st_done
dc_st_used:
        ld c,1                  ; 1 = case vide
        ld a,(dc_note)
        cp NOTE_NONE
        jr z,dc_st_done
        ld c,2                  ; 2 = arrêt de note
        cp NOTE_OFF
        jr z,dc_st_done
        ld c,3                  ; 3 = note
dc_st_done:
        ld a,c
        ld (dc_state),a

        ld a,(dg_l)             ; --- couleurs ---
        ld hl,cur_l
        cp (hl)
        jr nz,dc_not_cursor
        ld a,(dg_s)
        ld hl,cur_s
        cp (hl)
        jr nz,dc_not_cursor
        ld a,1                  ; sous le curseur : fond jaune, texte bleu
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        jr dc_text
dc_not_cursor:
        ld a,(dc_state)
        cp 3
        jr z,dc_col_note
        xor a                   ; pas de note : fond bleu
        call TXT_SET_PAPER
        ld a,(dc_state)
        cp 2
        ld a,3                  ; arrêt de note : orange
        jr z,dc_set_pen
        ld a,(dg_s)             ; vide : jaune sur les temps, cyan ailleurs
        and 3
        ld a,1
        jr z,dc_set_pen
        ld a,2
dc_set_pen:
        call TXT_SET_PEN
        jr dc_text
dc_col_note:
        call dc_is_noise        ; note : un "bouton" cyan, orange pour le bruit
        ld a,2
        jr nz,dc_set_paper
        ld a,3
dc_set_paper:
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN

dc_text:                        ; --- texte ---
        ld a,(dc_state)
        cp 3
        jr z,dc_note_text
        ld a,(dg_n)             ; sans note : seule la 1re ligne porte un signe
        or a
        jr nz,dc_spaces
        ld a,(dc_state)
        cp 1
        jr z,dc_dot
        cp 2
        jr nz,dc_spaces
        ld a,'-'                ; arrêt de note
        call TXT_OUTPUT
        ld a,'-'
        jp TXT_OUTPUT
dc_dot:
        ld a,'.'                ; case vide
        call TXT_OUTPUT
        ld a,' '
        jp TXT_OUTPUT
dc_spaces:
        ld a,' '
        call TXT_OUTPUT
        ld a,' '
        jp TXT_OUTPUT

dc_note_text:
        ld a,(dg_n)
        or a
        jr z,dc_line1
        dec a
        jr z,dc_line2
        ld a,(dc_mode)          ; ligne 3 : instrument, ou numéro du son
        or a
        jr nz,dc_son
        ld a,(dc_ins)
        inc a
        jp print_dec2
dc_son:
        ld a,'S'
        call TXT_OUTPUT
        ld a,(dc_ins)
        add a,'1'
        jp TXT_OUTPUT
dc_line1:                       ; ligne 1 : nom de la note
        call dc_is_noise
        jr nz,dc_name
        ld a,'B'
        call TXT_OUTPUT
        ld a,'R'
        jp TXT_OUTPUT
dc_name:
        ld a,(dc_note)
        call split_note         ; A = note dans l'octave (0-11)
        add a,a
        ld e,a
        ld d,0
        ld hl,note_names
        add hl,de
        ld a,(hl)
        call TXT_OUTPUT
        inc hl
        ld a,(hl)
        cp '-'                  ; "C-" s'affiche "C ", "C#" reste "C#"
        jr nz,dc_name2
        ld a,' '
dc_name2:
        jp TXT_OUTPUT
dc_line2:                       ; ligne 2 : octave, ou période du bruit
        call dc_is_noise
        jr nz,dc_octave
        ld a,(dc_note)
        rrca
        rrca
        rrca
        rrca
        and 15
        call print_hex1
        ld a,(dc_note)
        and 15
        jp print_hex1
dc_octave:
        ld a,'o'
        call TXT_OUTPUT
        ld a,(dc_note)
        call split_note
        ld a,d
        add a,'0'
        jp TXT_OUTPUT

; Z si la case en cours est sur la voix de bruit (voix 3 en voix séparées)
dc_is_noise:
        ld a,(dc_mode)
        or a
        ret nz
        ld a,(dg_l)
        cp 3
        ret

; A = note (0-95)  ->  A = note dans l'octave (0-11), D = octave (0-7)
split_note:
        ld d,0
sn_loop:
        cp 12
        ret c
        sub 12
        inc d
        jr sn_loop

; Nom de la voix dg_l, à gauche de la grille (2 lignes de 5 caractères)
draw_label:
        xor a
        call TXT_SET_PAPER
        ld hl,(seq_pattern)
        ld a,(hl)
        or a
        ld hl,lab_sep
        jr z,dl_table
        ld hl,lab_comp
dl_table:
        ld a,(dg_l)             ; 10 caractères par voix
        ld e,a
        add a,a
        add a,a
        add a,e
        add a,a
        ld e,a
        ld d,0
        add hl,de
        ld (dl_text),hl
        ld a,(dg_l)
        add a,a
        add a,a
        add a,GRID_ROW
        ld (dl_row),a
        ld l,a
        ld h,1
        call TXT_SET_CURSOR
        ld a,1
        call TXT_SET_PEN
        ld hl,(dl_text)
        ld b,5
        call print_n
        ld (dl_text),hl
        ld a,(dl_row)
        inc a
        ld l,a
        ld h,1
        call TXT_SET_CURSOR
        ld hl,(seq_pattern)     ; voix muette ?
        ld a,(hl)
        or a
        ld a,0                  ; son composé : on regarde la voix A
        jr nz,dl_mute
        ld a,(dg_l)
dl_mute:
        call chan_mask
        ld hl,snd_mute
        and (hl)
        jr z,dl_normal
        ld a,3
        call TXT_SET_PEN
        ld hl,txt_muet
        jp print_str
dl_normal:
        ld a,2
        call TXT_SET_PEN
        ld hl,(dl_text)
        ld b,5
        jp print_n

txt_muet: db "MUET ",0

lab_sep:
        db "A    TON  ","B    TON  ","C    TON  ","N    BRUIT"
lab_comp:
        db "SON  4 V. ","          ","          ","          "

; Affiche une liste de textes.
; Chaque élément : colonne, ligne, encre, fond, texte, 0.   Fin de liste : #FF.
print_list:
        ld a,(hl)
        cp #FF
        ret z
        ld d,a                  ; D = colonne
        inc hl
        ld e,(hl)               ; E = ligne
        inc hl
        ld a,(hl)               ; encre
        inc hl
        push hl
        push de
        call TXT_SET_PEN
        pop de
        pop hl
        ld a,(hl)               ; fond
        inc hl
        push hl
        push de
        call TXT_SET_PAPER
        pop hl                  ; HL = colonne / ligne
        call TXT_SET_CURSOR
        pop hl
pl_char:
        ld a,(hl)
        inc hl
        or a
        jr z,print_list
        call TXT_OUTPUT
        jr pl_char


; ============================================================================
; ECRAN INSTRUMENT
; ============================================================================
NB_FIELDS equ 19                ; nombre de réglages
FIELD_ROW equ 4                 ; ligne écran du premier réglage
FLD_SIZE  equ 19                ; taille d'une fiche de réglage
ENV_COL   equ 24                ; position du dessin de l'enveloppe
ENV_ROW   equ 5

; --- Commandes ---------------------------------------------------------------
ins_cmd:
        ld a,(rc_index)
        or a
        jp z,cmd_play           ; ESPACE : lecture / arrêt du motif
        cp 6
        jr z,ins_left
        cp 7
        jr z,ins_right
        cp 8
        jr z,ins_up
        cp 9
        jr z,ins_down
        ret

ins_up:
        ld a,(mod_shift)
        or a
        jp nz,oct_up
        ld a,(cur_field)        ; réglage précédent
        or a
        ret z
        dec a
        jr ins_field
ins_down:
        ld a,(mod_shift)
        or a
        jp nz,oct_down
        ld a,(cur_field)        ; réglage suivant
        cp NB_FIELDS-1
        ret nc
        inc a
ins_field:
        ld hl,cur_field
        ld b,(hl)               ; B = ancien réglage
        ld (hl),a
        ld a,b
        call ins_draw_field     ; l'ancien redevient normal
        ld a,(cur_field)
        jp ins_draw_field       ; le nouveau est mis en évidence

ins_left:
        ld a,(mod_ctrl)
        or a
        jr nz,ins_prev
        xor a                   ; 0 = diminuer
        jr ins_change
ins_right:
        ld a,(mod_ctrl)
        or a
        jr nz,ins_next
        ld a,1                  ; 1 = augmenter
        jr ins_change

ins_prev:                       ; CTRL + gauche : instrument précédent
        ld a,(cur_inst)
        or a
        ret z
        dec a
        ld (cur_inst),a
        jp ins_show_all
ins_next:                       ; CTRL + droite : instrument suivant
        ld a,(cur_inst)
        inc a
        cp NB_INST
        ret nc
        ld (cur_inst),a
        jp ins_show_all

; Modifie le réglage en cours.  A = 0 pour diminuer, 1 pour augmenter.
; Le pas est de 1, ou de 10 avec SHIFT.
ins_change:
        ld (ic_dir),a
        ld a,(mod_shift)
        or a
        ld a,1
        jr z,ic_step_set
        ld a,10
ic_step_set:
        ld (ic_step),a
        ld a,(cur_field)
        ld (df_i),a
        call field_ptr          ; lit la fiche du réglage
        call field_value_ptr    ; HL = octet de l'instrument
        ld a,(f_type)
        dec a
        jr nz,ic_number
        ld a,(f_min)            ; OUI / NON : on inverse le bit
        xor (hl)
        ld (hl),a
        jr ic_done
ic_number:
        ld a,(f_type)
        cp 2
        ld a,(hl)
        jr nz,ic_value
        xor #80                 ; valeur signée : on la décale de 128 pour la
ic_value:                       ; traiter comme une valeur de 0 à 255
        ld b,a                  ; B = valeur actuelle
        ld a,(ic_step)
        ld c,a
        ld a,(ic_dir)
        or a
        ld a,b
        jr z,ic_dec
        add a,c                 ; augmenter, sans dépasser le maximum
        jr c,ic_max
        ld b,a
        ld a,(f_max)
        cp b
        jr c,ic_store           ; maximum dépassé : A = maximum
        ld a,b
        jr ic_store
ic_max:
        ld a,(f_max)
        jr ic_store
ic_dec:
        sub c                   ; diminuer, sans passer sous le minimum
        jr c,ic_min
        ld b,a
        ld a,(f_min)
        cp b
        jr nc,ic_store          ; minimum atteint ou dépassé : A = minimum
        ld a,b
        jr ic_store
ic_min:
        ld a,(f_min)
ic_store:
        ld b,a
        ld a,(f_type)
        cp 2
        ld a,b
        jr nz,ic_write
        xor #80                 ; retour à la valeur signée
ic_write:
        ld (hl),a
ic_done:
        ld a,(cur_field)
        call ins_draw_field
        ld a,(cur_field)
        cp 4
        ret nc
        jp ins_draw_env         ; l'ADSR a changé : on redessine la courbe

; --- Piano : essai de l'instrument sur la voie A -------------------------------
ins_piano:
        call calc_note
        ld (en_note),a
        ld b,a
        ld a,(cur_inst)
        ld (en_ins),a
        ld c,a
        xor a
        ld (aud_timer),a
        ld (aud_voice),a
        jp snd_note_on          ; A = 0 : voie A

; --- Affichage ---------------------------------------------------------------
ins_show_all:
        ld hl,#0E02             ; colonne 14, ligne 2 : numéro et nom
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PEN
        ld a,(cur_inst)
        inc a
        call print_dec2
        ld a,' '
        call TXT_OUTPUT
        ld a,(cur_inst)         ; 6 caractères par nom
        ld e,a
        add a,a
        add a,e
        add a,a
        ld e,a
        ld d,0
        ld hl,inst_names
        add hl,de
        ld b,6
        call print_n
        call show_octave
        xor a
isa_loop:
        push af
        call ins_draw_field
        pop af
        inc a
        cp NB_FIELDS
        jr nz,isa_loop
        jp ins_draw_env

; Dessine la ligne du réglage A : son nom, puis sa valeur
ins_draw_field:
        ld (df_i),a
        call field_ptr          ; HL = nom du réglage
        ld (df_text),hl
        ld a,(df_i)
        add a,FIELD_ROW
        ld l,a
        ld h,1
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        ld a,2
        call TXT_SET_PEN
        ld hl,(df_text)
        ld b,15
        call print_n
        ld a,' '
        call TXT_OUTPUT
        ld a,(df_i)             ; le réglage en cours : valeur en jaune inversé
        ld hl,cur_field
        cp (hl)
        jr nz,df_normal
        ld a,1
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        jr df_value
df_normal:
        ld a,3
        call TXT_SET_PEN
df_value:
        call field_value_ptr    ; HL = octet de l'instrument
        ld a,(hl)
        ld (df_val),a
        ld a,(f_type)
        or a
        jr z,df_byte
        dec a
        jr z,df_flag
        ld a,(df_val)           ; valeur signée : signe puis 3 chiffres
        bit 7,a
        jr z,df_plus
        neg
        ld (df_val),a
        ld a,'-'
        jr df_sign
df_plus:
        ld a,'+'
df_sign:
        call TXT_OUTPUT
        ld a,(df_val)
        call print_dec3
        jr df_end
df_flag:
        ld a,(f_min)            ; OUI / NON selon le bit
        ld b,a
        ld a,(df_val)
        and b
        ld hl,txt_oui
        jr nz,df_flag_print
        ld hl,txt_non
df_flag_print:
        call print_str
        jr df_end
df_byte:
        ld a,(df_val)
        call print_dec3
        ld a,' '
        call TXT_OUTPUT
df_end:
        xor a
        jp TXT_SET_PAPER

txt_oui: db "OUI ",0
txt_non: db "NON ",0

; Lit la fiche du réglage df_i dans f_type, f_off, f_min, f_max.
; En sortie, HL pointe sur son nom (15 caractères).
field_ptr:
        ld a,(df_i)
        ld l,a
        ld h,0
        ld d,h
        ld e,l
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl               ; x16
        add hl,de
        add hl,de
        add hl,de               ; x19
        ld de,fields
        add hl,de
        ld a,(hl)
        ld (f_type),a
        inc hl
        ld a,(hl)
        ld (f_off),a
        inc hl
        ld a,(hl)
        ld (f_min),a
        inc hl
        ld a,(hl)
        ld (f_max),a
        inc hl
        ret

; HL = adresse, dans l'instrument en cours, de l'octet du réglage lu par
; field_ptr (pour un réglage OUI/NON : l'octet des drapeaux)
field_value_ptr:
        ld a,(cur_inst)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl               ; 16 octets par instrument
        ld de,instruments
        add hl,de
        ld a,(f_type)
        dec a
        ld a,INS_FLAGS
        jr z,fvp_add
        ld a,(f_off)
fvp_add:
        ld e,a
        ld d,0
        add hl,de
        ret

; Les réglages.  Chaque fiche : type, octet de l'instrument, minimum, maximum,
; nom sur 15 caractères.
;   type 0 = nombre ; type 1 = OUI/NON (le "minimum" est alors le bit du
;   drapeau) ; type 2 = nombre avec signe
fields:
        db 0,INS_ATTACK,0,255,   "ATTAQUE        "
        db 0,INS_DECAY,0,255,    "DECLIN         "
        db 0,INS_SUSTAIN,0,15,   "TENUE          "
        db 0,INS_RELEASE,0,255,  "RELACHE        "
        db 0,INS_VOLUME,0,15,    "VOLUME         "
        db 1,0,1,0,              "TON            "
        db 1,0,2,0,              "BRUIT          "
        db 0,INS_NOISE,0,31,     "  PERIODE      "
        db 1,0,4,0,              "ENV. MATERIELLE"
        db 0,INS_EGSHAPE,8,15,   "  FORME        "
        db 0,INS_EGSHIFT,0,7,    "  DIVISION     "
        db 0,INS_ARP1,0,24,      "ARPEGE NOTE 2  "
        db 0,INS_ARP2,0,24,      "ARPEGE NOTE 3  "
        db 0,INS_ARPSPEED,1,15,  "  VITESSE      "
        db 0,INS_VIBDEPTH,0,6,   "VIBRATO PROF.  "
        db 0,INS_VIBSPEED,0,255, "  VITESSE      "
        db 0,INS_VIBDELAY,0,255, "  ATTENTE      "
        db 2,INS_SLIDE,0,255,    "GLISSANDO      "
        db 1,0,8,0,              "PORTAMENTO     "

; --- Dessin de l'enveloppe ADSR ----------------------------------------------
; On fait tourner le vrai calcul d'enveloppe du moteur sur une voix de travail,
; touche tenue pendant 10 colonnes puis lâchée, et on dessine le niveau obtenu
; sur 16 colonnes.  L'échelle de temps s'adapte pour que l'attaque et le déclin
; tiennent dans les 8 premières colonnes.
ins_draw_env:
        call env_reset          ; 1er passage : durée de l'attaque + déclin
        ld b,0
ide_measure:
        push bc
        ld ix,env_tmp
        call sf_envelope
        pop bc
        inc b
        jr z,ide_cap
        ld a,(env_tmp+CH_PHASE)
        cp 3
        jr nz,ide_measure
        jr ide_scale
ide_cap:
        ld b,255
ide_scale:
        ld a,b                  ; images par colonne = durée / 8 + 1
        rrca
        rrca
        rrca
        and 31
        inc a
        ld (env_step),a

        call env_reset          ; 2e passage : hauteur de chaque colonne
        ld hl,env_h
        ld c,0                  ; C = colonne
ide_col:
        ld a,c
        cp 10
        jr nz,ide_run
        ld a,(env_tmp+CH_PHASE) ; colonne 10 : on lâche la touche
        or a
        jr z,ide_run
        ld a,4
        ld (env_tmp+CH_PHASE),a
ide_run:
        ld a,(env_step)
        ld b,a
ide_frames:
        push bc
        push hl
        ld ix,env_tmp
        call sf_envelope
        pop hl
        pop bc
        djnz ide_frames
        ld a,(env_tmp+CH_LEVEL) ; hauteur de 0 à 8 demi-cases
        or a
        jr z,ide_height
        rlca
        rlca
        rlca
        and 7
        inc a
ide_height:
        ld (hl),a
        inc hl
        inc c
        ld a,c
        cp 16
        jr nz,ide_col

        ld b,3                  ; dessin : 4 lignes, de haut (B = 3) en bas
ide_row:
        push bc
        ld a,ENV_ROW+3
        sub b
        ld l,a
        ld h,ENV_COL
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        ld a,2                  ; touche tenue : cyan
        call TXT_SET_PEN
        pop bc
        ld hl,env_h
        ld c,0
ide_cell:
        ld a,c
        cp 10
        jr nz,ide_char
        push bc
        push hl
        ld a,3                  ; touche lâchée : orange
        call TXT_SET_PEN
        pop hl
        pop bc
ide_char:
        ld a,b                  ; cette ligne couvre les demi-cases 2B+1, 2B+2
        add a,a
        inc a
        ld d,a                  ; D = 2B+1
        ld a,(hl)
        cp d
        ld e,' '
        jr c,ide_out            ; trop bas : vide
        ld e,140                ; caractère 140 = demi-bloc du bas
        jr z,ide_out
        ld e,143                ; caractère 143 = bloc plein
ide_out:
        ld a,e
        call TXT_OUTPUT
        inc hl
        inc c
        ld a,c
        cp 16
        jr nz,ide_cell
        ld a,b
        or a
        ret z
        dec b
        jr ide_row

; Prépare la voix de travail : instrument en cours, début de note
env_reset:
        ld hl,env_tmp
        ld b,CH_SIZE
        xor a
er_clear:
        ld (hl),a
        inc hl
        djnz er_clear
        ld a,(cur_inst)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,instruments
        add hl,de
        ld (env_tmp+CH_INSL),hl
        ld a,1
        ld (env_tmp+CH_PHASE),a
        ld a,15
        ld (env_tmp+CH_VOL),a
        ret

ins_text:
        db 1,2,2,0,   "INSTRUMENT :",0
        db 33,2,2,0,  "OCT:",0
        db ENV_COL,4,1,0, "ENVELOPPE",0
        db ENV_COL,10,2,0,"TOUCHE TENUE",0
        db ENV_COL,11,3,0,"PUIS LACHEE",0
        db ENV_COL,13,3,0,240,241,0
        db ENV_COL+3,13,2,0,"REGLAGE",0
        db ENV_COL,14,3,0,242,243,0
        db ENV_COL+3,14,2,0,"VALEUR",0
        db ENV_COL,15,3,0,"SHIFT ",242,243,0
        db ENV_COL+9,15,2,0,"PAR 10",0
        db ENV_COL,16,3,0,"CTRL  ",242,243,0
        db ENV_COL+9,16,2,0,"INSTR.",0
        db ENV_COL,17,3,0,"SHIFT ",240,241,0
        db ENV_COL+9,17,2,0,"OCTAVE",0
        db ENV_COL,19,3,0,"PIANO",0
        db ENV_COL+6,19,2,0,"ESSAI",0
        db ENV_COL,20,3,0,"ESPACE",0
        db ENV_COL+7,20,2,0,"LECTURE",0
        db #FF


; ============================================================================
; ECRAN MIXAGE ET DISQUE
; ============================================================================
DSK_VOICE_ROW equ 5             ; ligne de la voix A
DSK_NAME_ROW  equ 11            ; ligne du nom de fichier
DSK_MSG_ROW   equ 17            ; ligne des messages
NAME_LEN      equ 8

; --- Commandes ---------------------------------------------------------------
dsk_cmd:
        ld a,(rc_index)
        or a
        jp z,cmd_play           ; ESPACE : écouter le motif pendant le mixage
        cp 6
        jr z,dc_left
        cp 7
        jr z,dc_right
        cp 8
        jr z,dc_up
        cp 9
        jr z,dc_down
        cp 10
        jp z,dc_mute            ; f7
        cp 11
        jp z,dc_return
        cp 12
        jp z,disk_save          ; S
        cp 13
        jp z,disk_load          ; L
        cp 14
        jp z,disk_catalog       ; C
        cp 15
        jp z,disk_new           ; N
        cp 16
        jp z,disk_load_bank     ; D : banque de samples (smpscreen.asm)
        ret

dc_up:
        ld a,(dsk_row)
        or a
        ret z
        dec a
        jr dc_row
dc_down:
        ld a,(dsk_row)
        cp 4
        ret nc
        inc a
dc_row:
        ld hl,dsk_row
        ld b,(hl)
        ld (hl),a
        ld a,b
        call dsk_draw_row       ; l'ancienne ligne redevient normale
        ld a,(dsk_row)
        jp dsk_draw_row

dc_left:                        ; volume -1
        ld b,#FF
        jr dc_vol
dc_right:                       ; volume +1
        ld b,1
dc_vol:
        ld a,(dsk_row)
        cp 4
        ret nc                  ; ligne du nom : rien à régler
        ld e,a
        ld d,0
        ld hl,snd_master
        add hl,de
        ld a,(hl)
        add a,b
        cp 16
        ret nc                  ; hors de 0 à 15
        ld (hl),a
        ld a,(dsk_row)
        jp dsk_draw_row

dc_mute:
        ld a,(dsk_row)
        cp 4
        ret nc
dc_mute_go:
        call chan_mask
        ld hl,snd_mute
        xor (hl)
        ld (hl),a
        ld a,(dsk_row)
        jp dsk_draw_row

dc_return:                      ; RETURN : muet sur une voix, saisie du nom
        ld a,(dsk_row)
        cp 4
        jr c,dc_mute_go
        jp edit_name

; --- Affichage ---------------------------------------------------------------
dsk_show_all:
        xor a
dsa_loop:
        push af
        call dsk_draw_row
        pop af
        inc a
        cp 5
        jr nz,dsa_loop
        ret

; Dessine la ligne A : une voix (0 à 3) ou le nom de fichier (4)
dsk_draw_row:
        ld (dr_row),a
        cp 4
        jp z,dsk_draw_name
        add a,DSK_VOICE_ROW
        ld l,a
        ld h,1
        call TXT_SET_CURSOR
        call dr_select_colors
        ld hl,txt_voix
        call print_str
        ld a,(dr_row)
        ld e,a
        ld d,0
        ld hl,voice_letters
        add hl,de
        ld a,(hl)
        call TXT_OUTPUT
        ld a,' '
        call TXT_OUTPUT
        xor a
        call TXT_SET_PAPER
        ld a,' '
        call TXT_OUTPUT
        ld a,(dr_row)           ; C = volume
        ld e,a
        ld d,0
        ld hl,snd_master
        add hl,de
        ld c,(hl)
        ld a,1
        call TXT_SET_PEN
        ld b,15                 ; barre de 15 caractères
ddr_bar:
        ld a,c
        or a
        ld a,' '
        jr z,ddr_out
        dec c
        ld a,140                ; demi-bloc du bas : les 4 barres restent séparées
ddr_out:
        push bc
        call TXT_OUTPUT
        pop bc
        djnz ddr_bar
        ld a,' '
        call TXT_OUTPUT
        ld a,3
        call TXT_SET_PEN
        ld a,(dr_row)
        ld e,a
        ld d,0
        ld hl,snd_master
        add hl,de
        ld a,(hl)
        call print_dec2
        ld a,' '
        call TXT_OUTPUT
        ld a,(dr_row)
        call chan_mask
        ld hl,snd_mute
        and (hl)
        ld hl,txt_muet
        jr nz,ddr_state
        ld hl,txt_sonne
ddr_state:
        jp print_str

; Ligne du nom de fichier
dsk_draw_name:
        ld hl,256*7+DSK_NAME_ROW
        call TXT_SET_CURSOR
        call dr_select_colors
        ld hl,fname
        ld b,NAME_LEN
        call print_n
        xor a
        call TXT_SET_PAPER
        ld a,3
        call TXT_SET_PEN
        ld hl,txt_ext
        jp print_str

; Couleurs d'une ligne : jaune inversé si c'est la ligne choisie
dr_select_colors:
        ld a,(dr_row)
        ld hl,dsk_row
        cp (hl)
        jr nz,drs_normal
        ld a,1
        call TXT_SET_PAPER
        xor a
        jp TXT_SET_PEN
drs_normal:
        xor a
        call TXT_SET_PAPER
        ld a,2
        jp TXT_SET_PEN

; Affiche un message sur la ligne des messages.  HL = texte
dsk_message:
        push hl
        ld hl,256*1+DSK_MSG_ROW
msg_row:                        ; HL = position, texte sur la pile
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        ld a,3
        call TXT_SET_PEN
        pop hl
        ld b,40
dm_loop:
        ld a,(hl)
        or a
        jr z,dm_pad
        inc hl
        push bc
        push hl
        call TXT_OUTPUT
        pop hl
        pop bc
        djnz dm_loop
        ret
dm_pad:
        ld a,' '                ; on efface la fin de la ligne
        push bc
        call TXT_OUTPUT
        pop bc
        dec b
        ld a,b
        cp 1
        jr nz,dm_pad
        ret

; --- Saisie du nom de fichier ------------------------------------------------
edit_name:
        call silence
        ld hl,txt_m_name
        call dsk_message
en_flush:                       ; on vide les frappes en attente
        call KM_READ_CHAR
        jr c,en_flush
        ld hl,fname             ; position = longueur actuelle du nom
        ld b,0
en_len:
        ld a,(hl)
        cp ' '
        jr z,en_loop_init
        inc hl
        inc b
        ld a,b
        cp NAME_LEN
        jr nz,en_len
en_loop_init:
        ld a,b
        ld (name_pos),a
        ld a,1                  ; la première lettre tapée remplace tout le nom
        ld (name_fresh),a
en_loop:
        call dsk_draw_name
        ld a,(name_pos)         ; curseur de saisie
        add a,7
        ld h,a
        ld l,DSK_NAME_ROW
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        ld a,(name_pos)
        cp NAME_LEN
        jr nc,en_wait
        ld e,a
        ld d,0
        ld hl,fname
        add hl,de
        ld a,(hl)
        call TXT_OUTPUT
en_wait:
        xor a
        call TXT_SET_PAPER
        call KM_WAIT_CHAR       ; attend une frappe (le son est coupé)
        cp 13
        jr z,en_done            ; RETURN : fini
        cp #FC
        jr z,en_esc             ; ESC : fini aussi
        cp 127
        jr z,en_del             ; DEL : efface le dernier caractère
        cp 'a'
        jr c,en_check
        cp 'z'+1
        jp nc,en_loop
        sub 32                  ; minuscule -> majuscule
en_check:
        cp '-'
        jr z,en_add
        cp '0'
        jp c,en_loop
        cp '9'+1
        jr c,en_add
        cp 'A'
        jp c,en_loop
        cp 'Z'+1
        jp nc,en_loop
en_add:
        ld c,a
        ld a,(name_fresh)
        or a
        jr z,en_add_go
        xor a
        ld (name_fresh),a
        ld (name_pos),a
        ld hl,fname             ; nouveau nom : on efface l'ancien
        ld b,NAME_LEN
en_clear:
        ld (hl),' '
        inc hl
        djnz en_clear
en_add_go:
        ld a,(name_pos)
        cp NAME_LEN
        jp nc,en_loop           ; nom plein
        ld e,a
        ld d,0
        ld hl,fname
        add hl,de
        ld (hl),c
        inc a
        ld (name_pos),a
        jp en_loop
en_del:
        xor a                   ; DEL : on corrige le nom au lieu de le remplacer
        ld (name_fresh),a
        ld a,(name_pos)
        or a
        jp z,en_loop
        dec a
        ld (name_pos),a
        ld e,a
        ld d,0
        ld hl,fname
        add hl,de
        ld (hl),' '
        jp en_loop
en_esc:
        ld a,KEY_ESC            ; on attend qu'ESC soit relâchée, pour ne pas
        call KM_TEST_KEY        ; qu'elle compte comme "quitter"
        jr nz,en_esc
en_done:
        call dsk_draw_name
        ld hl,txt_m_none
        jp dsk_message

; --- Sauvegarde --------------------------------------------------------------
disk_save:
        call silence
        call build_filename
        ret nc                  ; nom vide
        ld hl,txt_m_saving
        call dsk_message
        ld a,(fname_len)
        ld b,a
        ld hl,fname_full
        ld de,io_buffer
        call CAS_OUT_OPEN
        jr nc,disk_error
        ld hl,song_data
        ld de,SONG_SIZE
        ld bc,0
        ld a,2                  ; fichier binaire
        call CAS_OUT_DIRECT
        jr nc,ds_abandon
        call CAS_OUT_CLOSE
        jr nc,disk_error
        ld hl,txt_m_saved
        jp dsk_message
ds_abandon:
        call CAS_OUT_ABANDON
disk_error:
        ld hl,txt_m_error
        jp dsk_message

; --- Chargement --------------------------------------------------------------
disk_load:
        call silence
        call build_filename
        ret nc
        ld hl,txt_m_loading
        call dsk_message
        ld a,(fname_len)
        ld b,a
        ld hl,fname_full
        ld de,io_buffer
        call CAS_IN_OPEN
        jr nc,disk_error
        ld hl,SONG_SIZE         ; la taille doit être exactement la bonne
        or a
        sbc hl,bc
        jr nz,dl_bad
        ld hl,song_data
        call CAS_IN_DIRECT
        jr nc,dl_abandon
        call CAS_IN_CLOSE
        ld hl,song_data         ; signature "SQ16" ?
        ld de,song_sig
        ld b,4
dl_sig:
        ld a,(de)
        cp (hl)
        jr nz,dl_corrupt
        inc hl
        inc de
        djnz dl_sig
        call song_loaded
        ld hl,txt_m_loaded
        jp dsk_message
dl_bad:
        call CAS_IN_ABANDON
        ld hl,txt_m_bad
        jp dsk_message
dl_abandon:
        call CAS_IN_ABANDON
        jr disk_error
dl_corrupt:                     ; contenu illisible : on repart du morceau d'usine
        call init_song
        call song_loaded
        ld hl,txt_m_bad
        jp dsk_message

song_sig: db "SQ16"

; Le morceau vient de changer : on repart du motif 1 et on met tout à jour
song_loaded:
        xor a
        ld (cur_pat),a
        ld (cur_l),a
        ld (cur_s),a
        call pat_addr
        call seq_set_pattern
        call snd_init
        jp dsk_show_all

; --- Catalogue ---------------------------------------------------------------
disk_catalog:
        call silence
        ld h,0                  ; fenêtre de texte : lignes 19 à 25
        ld d,39
        ld l,18
        ld e,24
        call TXT_WIN_ENABLE
        call TXT_CLEAR_WINDOW
        ld a,2
        call TXT_SET_PEN
        ld de,io_buffer
        call CAS_CATALOG
        push af
        ld h,0                  ; on rend tout l'écran au texte
        ld d,39
        ld l,0
        ld e,24
        call TXT_WIN_ENABLE
        pop af
        ld hl,txt_m_none        ; (le résultat de CAS_CATALOG n'est pas fiable :
        jp dsk_message          ;  on ne signale pas d'erreur)

; --- Nouveau morceau (deux appuis sur N) -------------------------------------
disk_new:
        ld a,(new_armed)
        or a
        jr nz,dn_go
        inc a
        ld (new_armed),a
        ld hl,txt_m_confirm
        jp dsk_message
dn_go:
        xor a
        ld (new_armed),a
        call silence
        call init_song
        call song_loaded
        ld hl,txt_m_new
        jp dsk_message

; Coupe la lecture et le son (avant un accès disque ou une saisie)
silence:
        xor a
        ld (new_armed),a
        call seq_stop
        jp snd_init

; Construit fname_full = nom sans espaces + ".SNG".  NC si le nom est vide.
; build_filename_ext : pareil avec l'extension pointée par HL (4 caractères).
build_filename:
        ld hl,txt_ext
build_filename_ext:
        ld (bf_ext_ptr),hl
        ld hl,fname
        ld de,fname_full
        ld b,NAME_LEN
        ld c,0                  ; C = longueur
bf_loop:
        ld a,(hl)
        cp ' '
        jr z,bf_skip
        ld (de),a
        inc de
        inc c
bf_skip:
        inc hl
        djnz bf_loop
        ld a,c
        or a
        jr z,bf_empty
        ld hl,(bf_ext_ptr)
        ld b,4
bf_ext:
        ld a,(hl)
        ld (de),a
        inc hl
        inc de
        inc c
        djnz bf_ext
        ld a,c
        ld (fname_len),a
        scf
        ret
bf_empty:
        ld hl,txt_m_noname
        call dsk_message
        or a                    ; NC
        ret

voice_letters: db "ABCN"
txt_voix:     db " VOIX ",0
txt_sonne:    db "    ",0
txt_ext:      db ".SNG",0
txt_m_none:   db 0
txt_m_name:   db "TAPE LE NOM, PUIS RETURN",0
txt_m_saving: db "SAUVEGARDE EN COURS...",0
txt_m_saved:  db "MORCEAU SAUVE",0
txt_m_loading: db "CHARGEMENT EN COURS...",0
txt_m_loaded: db "MORCEAU CHARGE",0
txt_m_error:  db "ERREUR DISQUE (DISQUETTE ? NOM ?)",0
txt_m_bad:    db "CE FICHIER N'EST PAS UN MORCEAU SEQ-16",0
txt_m_noname: db "DONNE D'ABORD UN NOM (RETURN)",0
txt_m_confirm: db "N A NOUVEAU : TOUT EFFACER ?",0
txt_m_new:    db "NOUVEAU MORCEAU",0

dsk_text:
        db 1,3,1,0,  "MIXAGE",0
        db 9,3,2,0,  "VOLUME DE CHAQUE VOIX",0
        db 1,10,1,0, "DISQUE",0
        db 1,DSK_NAME_ROW,2,0,"NOM :",0
        db 1,13,3,0, "S",0
        db 3,13,2,0, "SAUVER",0
        db 12,13,3,0,"L",0
        db 14,13,2,0,"CHARGER",0
        db 24,13,3,0,"C",0
        db 26,13,2,0,"CATALOGUE",0
        db 1,14,3,0, "N",0
        db 3,14,2,0, "NOUVEAU",0
        db 12,14,3,0,"RETURN",0
        db 19,14,2,0,"MUET (OU NOM)",0
        db 1,16,3,0, "D",0
        db 3,16,2,0, "CHARGER LA BANQUE NOM.SMP",0
        db 1,15,3,0, 240,241,0
        db 4,15,2,0, "CHOIX",0
        db 12,15,3,0,242,243,0
        db 15,15,2,0,"VOLUME",0
        db 24,15,3,0,"f7",0
        db 27,15,2,0,"MUET",0
        db 1,25,3,0, "ESC MAINTENUE 1 SECONDE : QUITTER",0
        db #FF

; Les caractères 240 à 243 du CPC sont les flèches haut, bas, gauche, droite.
screen_text:
        db 1,2,2,0,  "MOTIF :",0
        db 27,2,2,0, "ETAT :",0
        db 1,3,2,0,  "BPM:",0
        db 13,3,2,0, "OCTAVE:",0
        db 1,HEAD_ROW,2,0, "PAS",0
        db 1,22,3,0, 242,243,240,241,0
        db 6,22,2,0, "CURSEUR",0
        db 14,22,3,0,"ESPACE",0
        db 21,22,2,0,"LIRE",0
        db 26,22,3,0,"f5",0
        db 29,22,2,0,"MODE",0
        db 34,22,3,0,"f7",0
        db 37,22,2,0,"MUET",0
        db 1,23,3,0, "DEL",0
        db 5,23,2,0, "EFFACER",0
        db 14,23,3,0,"TAB",0
        db 18,23,2,0,"ARRET",0
        db 25,23,3,0,"CAPS",0
        db 30,23,2,0,"VERROU SON",0
        db 1,24,3,0, "SHIFT ",240,241,0
        db 10,24,2,0,"OCTAVE",0
        db 20,24,3,0,"SHIFT ",242,243,0
        db 29,24,2,0,"INSTRUMENT",0
        db 1,25,3,0, "CTRL  ",240,241,0
        db 10,25,2,0,"TEMPO",0
        db 20,25,3,0,"CTRL  ",242,243,0
        db 29,25,2,0,"MOTIF",0
        db #FF

        include 'sound.asm'
        include 'seq.asm'
        include 'song.asm'
        include 'tables.asm'
        include 'factory.asm'
        include 'smpscreen.asm'
        include 'smptables.asm'
        include 'sample.asm'

; ----------------------------------------------------------------------------
; Variables du programme
; ----------------------------------------------------------------------------
screen:     db 0                ; écran en cours : 0 = séquenceur, 1 = instrument,
                                ; 2 = mixage et disquette, 3 = samples
esc_count:  db 0                ; nombre d'images où ESC est restée enfoncée
cur_field:  db 0                ; écran Instrument : réglage en cours
df_i:       db 0
df_text:    dw 0
df_val:     db 0
f_type:     db 0
f_off:      db 0
f_min:      db 0
f_max:      db 0
ic_dir:     db 0
ic_step:    db 0
env_step:   db 0
env_h:      ds 16               ; hauteur des 16 colonnes de l'enveloppe
env_tmp:    ds 16               ; voix de travail pour dessiner l'enveloppe
cur_pat:    db 0                ; motif affiché (0 à 31)
cur_l:      db 0                ; curseur : voix (0 à 3)
cur_s:      db 0                ; curseur : pas (0 à 15)
cur_oct:    db 3                ; octave de saisie (1 à 6)
cur_inst:   db 0                ; instrument de saisie
cur_son:    db 0                ; son composé de saisie
cmd_last:   db #FF              ; touche de commande enfoncée (#FF = aucune)
cmd_count:  db 0                ; compteur pour la répétition des flèches
mod_shift:  db 0
mod_ctrl:   db 0
rc_index:   db 0
rp_index:   db 0
piano_last: db #FF              ; touche du piano enfoncée (#FF = aucune)
aud_key:    db #FF              ; touche dont on écoute la note
aud_voice:  db 0                ; voix de l'écoute (#80 = les 4)
aud_timer:  db 0                ; images restantes pour une écoute courte
inst_lock:  db 0                ; 1 = instrument de saisie verrouillé
en_note:    db 0
en_ins:     db 0
shown_pos:  db #FF              ; pas mis en évidence (#FF = aucun)
dh_step:    db 0
dh_hi:      db 0
dg_l:       db 0                ; dessin de la grille : voix,
dg_s:       db 0                ;   pas,
dg_n:       db 0                ;   ligne de la case
dc_note:    db 0
dc_ins:     db 0
dc_mode:    db 0
dc_state:   db 0
dl_text:    dw 0
dl_row:     db 0
dsk_row:    db 0                ; écran Disque : ligne choisie (0-3 voix, 4 nom)
dr_row:     db 0
name_pos:   db 0
name_fresh: db 0
new_armed:  db 0
fname:      db "MORCEAU1"        ; nom de fichier, complété par des espaces
fname_full: ds 13
fname_len:  db 0
bf_ext_ptr: dw 0                ; extension du nom de fichier (.SNG ou .SMP)
cur_smp:    db 0                ; écran Samples : sample choisi
smp_field:  db 0                ;   réglage en cours
smp_tried:  db 0                ;   1 = DRUMS.SMP a déjà été essayé
smp_name:   db "--------"       ;   nom de la banque chargée
sdr_i:      db 0
sdr_ms:     dw 0
sdf_i:      db 0
sc_dir:     db 0

end_of_program:

; ----------------------------------------------------------------------------
; Le morceau, juste après le programme (il n'est pas dans SEQ16.BIN : il est
; rempli au démarrage, puis sauvé et chargé à part, en fichier .SNG)
; ----------------------------------------------------------------------------
song_data   equ end_of_program
snd_master  equ song_data+5     ; volume général des voix A, B, C, N
snd_mute    equ song_data+9     ; voix muettes (bits 0 à 3)
instruments equ song_data+16
inst_names  equ instruments+NB_INST*16
sons        equ inst_names+NB_INST*6
patterns    equ sons+NB_SONS*16
song_end    equ patterns+NB_PAT*PAT_SIZE
io_buffer   equ song_end        ; 2 Ko de travail pour AMSDOS
        assert io_buffer+2048 < #A000
        print "fin du programme=",{hex}end_of_program," io_buffer=",{hex}io_buffer," banque=",BANK_MAX," zone haute=",{hex}smp_blk_end
        assert BANK_MAX >= 2048         ; la banque d'usine DRUMS.SMP doit tenir

        save 'SEQ16.BIN',start,end_of_program-start,DSK,'build/seq16.dsk'
