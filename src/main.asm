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

        org #3F00               ; (#3F00 et non #4000 : 256 octets de plus pour le programme)
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
KEY_F6    equ 4                 ; pavé numérique (matrice du clavier CPC)
KEY_F8    equ 11
KEY_F9    equ 3
KEY_B     equ 54                ; panneau SONG : la boucle part d'ici
KEY_RETURN equ 18
KEY_S     equ 60
KEY_L     equ 36
KEY_C     equ 62
KEY_N     equ 46
KEY_D     equ 61
KEY_COPY  equ 9
KEY_P     equ 27
KEY_O     equ 34
KEY_I     equ 35
KEY_E     equ 58
KEY_M     equ 38

GRID_ROW  equ 11                ; première voix de la grille (une ligne sur deux)
HEAD_ROW  equ 10                ; ligne des numéros de pas

start:
        jp boot                 ; les routines de bank.asm doivent être hors de
                                ; #4000-#7FFF : on les met tout au début
        include 'bank.asm'
        assert $ <= #4000

boot:
        ld a,1                  ; Mode 1 : 40 colonnes, 4 couleurs
        call SCR_SET_MODE
        ld bc,COL_BLEU*257
        call SCR_SET_BORDER
        ld a,3                  ; l'encre 3 devient orange
        ld bc,COL_ORANGE*257
        call SCR_SET_INK

        call bank_check         ; il faut les 128 Ko du 6128 (bank.asm)
        jr c,boot_6128
        ld hl,txt_need_6128     ; 464, ou 664 sans extension : on prévient,
        call print_str          ; et une touche ramène au BASIC
        call KM_WAIT_CHAR
        rst 0
boot_6128:
        ld c,7                  ; RUN" d'un fichier binaire réinitialise le
        ld de,#0040             ; système sans réveiller le lecteur de
        ld hl,#ABFF             ; disquette : on relance AMSDOS (ROM 7),
        call KL_INIT_BACK       ; sinon les sauvegardes iraient sur cassette
        call smp_install        ; DE, HL = mémoire libre : on installe la
                                ; routine de lecture des samples
        ld a,#FF                ; AMSDOS : pas de message d'erreur disque à
        ld (#BE78),a            ; l'écran, c'est le programme qui les affiche
        ld hl,boot_src+boot_len-1   ; le code du démarrage, dans le tampon
        ld de,BOOT_RUN+boot_len-1   ; d'AMSDOS (boot.asm) ; copié à reculons :
        ld bc,boot_len              ; la destination est plus haut que la
        lddr                        ; source, elles peuvent se chevaucher
        call factory_build      ; morceau d'usine
        call factory_save       ; gardé dans le bloc 5 (pour N N)
        call snd_init
        xor a                   ; motif 1
        call pat_fetch
        call seq_set_pattern
        call draw_screen        ; affiche le séquenceur

; ----------------------------------------------------------------------------
; Boucle principale : un tour par image, 50 tours par seconde
; ----------------------------------------------------------------------------
main_loop:
        call MC_WAIT_FLYBACK
        halt
        halt
        xor a
        ld (sc_ticked),a        ; snd_tick n'a pas encore joué ce tour-ci

        call read_screen_keys   ; f1 / f2 : changement d'écran
        call read_cmd           ; touches de commande
        call read_piano         ; touches du piano
        call aud_release        ; fin de l'écoute quand la touche est lâchée
        call snd_catchup        ; séquenceur et son : une image, ou toutes
                                ; celles qu'un long dessin a fait passer
        call song_prefetch      ; morceau : le motif suivant, à l'avance
        ld a,(dg_pending)       ; un digidrum attend ?
        or a
        call nz,dg_play         ; il joue, puis le tempo est rattrapé
        ld a,(song_changed)     ; le morceau a changé de position ?
        or a
        call nz,song_follow     ; l'écran suit (songpanel.asm)
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
; Cinq panneaux : f1 SONG, f2 MOTIF, f3 INST, f4 SAMPLE, f5 DISQUE.
; Numéro interne de l'écran (screen) : 0 = motif, 1 = instrument,
; 2 = disque, 3 = samples, 4 = song (les numéros d'avant la v1.0 restent).
; ----------------------------------------------------------------------------
read_screen_keys:
        ld hl,tab_keys
        ld b,5
rsk_loop:
        ld a,(hl)
        push hl
        push bc
        call KM_TEST_KEY
        pop bc
        pop hl
        jr nz,rsk_found
        inc hl
        djnz rsk_loop
        ret
rsk_found:
        ld de,tab_screens-tab_keys
        add hl,de
        ld a,(hl)               ; A = écran de ce panneau
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
        jp z,ds_disk            ; écran 2 : le panneau DISQUE (diskpanel.asm)
        dec a
        jp z,ds_sample          ; écran 3 : samples (smpscreen.asm)
        jp ds_song              ; écran 4 : song (panels.asm)
ds_sequencer:
        ld hl,screen_text
        call print_list
        call draw_box           ; cadre du panneau de la note (grid.asm)
        jp redraw_all
ds_instrument:
        ld a,(ins_son)
        or a
        ld hl,ins_text          ; instruments
        jr z,dsi_text
        ld hl,son_text          ; sons composés
dsi_text:
        call print_list
        ld hl,ins_common
        call print_list
        xor a
        call TXT_SET_PAPER
        ld a,(ins_son)
        or a
        jp z,ins_show_all
        call show_octave
        jp son_show_all

; Bandeau du haut : SEQ16 et les 5 onglets.  L'onglet du panneau en cours
; est en bleu sur orange ; les autres ont leur chiffre en orange et leur
; nom en cyan.  Dans txt_tabs, '|' commence un onglet (affiché en espace) :
; un seul texte, pour que chaque langue répartisse ses 35 caractères.
draw_title:
        ld hl,#0101
        call TXT_SET_CURSOR
        ld a,1
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        ld hl,txt_title
        call print_str
        ld hl,txt_tabs
        xor a
        ld (dt_tab),a
dt_loop:
        ld a,(hl)
        inc hl
        or a
        jr z,dt_end
        push hl
        cp '|'
        jr z,dt_tab_start
        ld c,a                  ; C = caractère à écrire
        ld a,(dt_state)         ; 1 = c'est le chiffre de l'onglet
        or a
        ld b,3                  ; chiffre : orange
        jr nz,dt_pen
        ld b,2                  ; lettres : cyan
dt_pen:
        xor a
        ld (dt_state),a
        ld a,(dt_on)            ; onglet en cours : tout en bleu
        or a
        ld a,b
        jr z,dt_setpen
        xor a
dt_setpen:
        push bc
        call TXT_SET_PEN
        pop bc
        ld a,c
        jr dt_put
dt_tab_start:                   ; '|' : un onglet commence
        ld a,(dt_tab)
        ld e,a
        inc a
        ld (dt_tab),a
        ld d,0
        ld hl,tab_screens
        add hl,de
        ld a,(screen)
        cp (hl)
        ld a,0
        jr nz,dt_paper
        ld a,3                  ; le panneau en cours : fond orange
dt_paper:
        ld (dt_on),a
        call TXT_SET_PAPER
        ld a,1
        ld (dt_state),a         ; le caractère suivant est le chiffre
        ld a,' '
dt_put:
        call txt_out
        pop hl
        jr dt_loop
dt_end:
        xor a
        jp TXT_SET_PAPER

dt_tab:      db 0               ; onglet suivant (0 à 4)
dt_on:       db 0               ; 3 = onglet du panneau en cours, 0 sinon
dt_state:    db 0               ; 1 = le prochain caractère est le chiffre
txt_title:   db "SEQ16",0       ; 5 + 35 = 40 colonnes
txt_tabs:    db "|1SONG|2MOTIF|3INST|4SAMPLE|5DISQUE",0
tab_keys:    db KEY_F1,KEY_F2,KEY_F3,KEY_F4,KEY_F5
tab_screens: db 4,0,1,3,2       ; écran de chaque onglet (SONG, MOTIF...)

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
        cp NB_CMDS
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
        ld a,(rc_index)         ; f8 / f9 : sauver / charger, dans tous les
        cp 23                   ; panneaux (panels.asm)
        jp z,panel_save
        cp 24
        jp z,panel_load
        ld a,(screen)
        or a
        jr z,rc_seq
        dec a
        jp z,ins_cmd            ; écran Instrument : ses propres commandes
        dec a
        jp z,dsk_cmd            ; écran Disque : ses propres commandes
        dec a
        jp z,smp_cmd            ; écran Samples : ses propres commandes
        jp song_cmd             ; panneau Song (panels.asm)
rc_seq:
        ld a,(rc_index)
        cp 11
        jp z,cmd_toggle         ; ENTER : allume / éteint la case (grid.asm)
        cp 17
        jp z,cmd_pick           ; COPY : la case devient le pinceau
        cp 13
        jp z,cmd_loop           ; L : BOUCLE <-> 1 FOIS
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
        jp z,cmd_edit           ; TAB : la grille <-> le panneau de la note
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
        db KEY_SPACE,KEY_F6,KEY_DEL,KEY_CLR,KEY_TAB,KEY_CAPS   ; 0 à 5
        db KEY_LEFT,KEY_RIGHT,KEY_UP,KEY_DOWN                  ; 6 à 9
        db KEY_F7,KEY_RETURN,KEY_S,KEY_L,KEY_C,KEY_N           ; 10 à 15
        db KEY_D,KEY_COPY,KEY_P,KEY_O,KEY_I,KEY_E              ; 16 à 21
        db KEY_M,KEY_F8,KEY_F9,KEY_B                           ; 22 à 25
NB_CMDS equ $-cmd_table         ; nombre de touches de commande

; --- L : le motif boucle, ou n'est joué qu'une fois ---
cmd_loop:
        ld hl,pat_once
        ld a,(hl)
        xor 1
        ld (hl),a
        ; continue dans show_loop

; Ligne 20 : « L BOUCLE » ou « L 1 FOIS » (le mode de lecture du motif)
show_loop:
        ld hl,256*25+20
        call TXT_SET_CURSOR
        ld bc,1*256+0
        call colors
        ld a,(pat_once)
        or a
        ld hl,txt_loop
        jp z,print_str
        ld hl,txt_once
        jp print_str

txt_loop: db "BOUCLE",0
txt_once: db "1 FOIS",0

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
        ld a,1
        ld (pat_dirty),a
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

; --- CLR : arrêt de note, puis pas suivant ---
cmd_clr:
        call cursor_ptr
        ld (hl),NOTE_OFF
        inc hl
        ld (hl),0
        inc hl
        ld (hl),#FF
        inc hl
        ld (hl),0
        call draw_cursor_cell   ; la voix entière (trait de durée)
        jp cursor_next

; --- Flèches ---
cmd_left:
        call edit_plain         ; mode édition (TAB) : champ précédent
        jp z,edit_left
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
        call edit_plain
        jp z,edit_right
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
        call edit_plain         ; mode édition : valeur + 1
        jp z,edit_up
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
        call edit_plain
        jp z,edit_down
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
        ld hl,pat_dirty         ; (le motif a changé : à ranger)
        ld (hl),1
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
        cp 4
        ret z                   ; panneau SONG aussi (B : la boucle)
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
        ld a,(en_note)          ; la note devient le pinceau
        call set_brush
        call draw_cursor_cell

        xor a
        ld (aud_timer),a
        call audition           ; écoute immédiate
        jp cursor_next          ; et le curseur avance d'un pas

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
select_pattern:                 ; (la lecture continue, au même pas)
        push af
        ld a,#FF                ; le motif préparé à l'avance n'est plus sûr
        ld (next_id),a
        call pat_store          ; le motif quitté retourne dans le bloc 4
        pop af
        ld (cur_pat),a
        call pat_fetch          ; et le nouveau vient dans pat_work
        call seq_set_pattern
        ld hl,(seq_pattern)     ; en son composé, une seule voix
        ld a,(hl)
        or a
        jp z,redraw_all
        xor a
        ld (cur_l),a
        jp redraw_all           ; (grid.asm)

; ----------------------------------------------------------------------------
; Affichage des informations
; ----------------------------------------------------------------------------
; Affiche le texte pointé par HL, terminé par 0
print_str:
        ld a,(hl)
        inc hl
        or a
        ret z
        call txt_out
        jr print_str

; Affiche B caractères à partir de HL (HL avance)
print_n:
        ld a,(hl)
        call txt_out
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
        call txt_out
        pop af
        add a,'0'
        jp txt_out

; Affiche A (0 à 15) sur 1 chiffre hexadécimal
print_hex1:
        cp 10
        jr c,ph_digit
        add a,7                 ; de '9' à 'A'
ph_digit:
        add a,'0'
        jp txt_out

txt_muet: db "MUET ",0
txt_comp: db "SON COMPOSE  ",0
txt_play: db "LECTURE",0
txt_stop: db "ARRET  ",0
txt_inst: db "INSTR.:",0
txt_son:  db "SON   :",0
txt_pad:  db "       ",0

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
        call txt_out
        jr pl_char


; ============================================================================
; ECRAN INSTRUMENT
; ============================================================================
NB_FIELDS equ 20                ; nombre de réglages
FLD_DIGI  equ 19                ; le réglage DIGIDRUM
FLD_NOISE equ 7                 ; la période du bruit (ou le sample)
FIELD_ROW equ 4                 ; ligne écran du premier réglage
FLD_SIZE  equ 19                ; taille d'une fiche de réglage
ENV_COL   equ 24                ; position du dessin de l'enveloppe
ENV_ROW   equ 5

; --- Commandes ---------------------------------------------------------------
ins_cmd:
        ld a,(rc_index)
        or a
        jp z,cmd_play           ; ESPACE : lecture / arrêt du motif
        dec a
        jr z,ins_mode           ; f6 : instruments <-> sons composés
        inc a
        ld b,a
        ld a,(ins_son)
        or a
        ld a,b
        jp nz,son_cmd
        cp 6
        jr z,ins_left
        cp 7
        jr z,ins_right
        cp 8
        jr z,ins_up
        cp 9
        jr z,ins_down
        cp 17
        jp z,ins_copy           ; COPY : copier l'instrument (banks.asm)
        cp 18
        jp z,ins_paste          ; P : le coller
        cp 19
        jp z,ins_take           ; O : prendre un son dans une banque
        ret

ins_mode:
        ld hl,ins_son
        ld a,(hl)
        xor 1
        ld (hl),a
        jp draw_screen

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
        ld hl,16                ; l'instrument affiché : 16 octets plus loin
        jr ins_show_values
ins_next:                       ; CTRL + droite : instrument suivant
        ld a,(cur_inst)
        inc a
        cp NB_INST
        ret nc
        ld (cur_inst),a
        ld hl,-16               ; l'instrument affiché : 16 octets avant
; L'instrument voisin (HL = sa distance, en octets) : son numéro, son nom, et
; seulement les valeurs qui changent ; l'enveloppe si l'ADSR change.  Les
; noms des réglages restent (sauf PERIODE / SAMPLE, redessiné en entier).
; Sur le vrai CPC, un caractère coûte environ 3,5 ms : un dessin complet
; (474 caractères) durait plus d'une seconde et demie.
ins_show_values:
        ld (isv_delta),hl
        call isa_name
        xor a
        ld (isv_env),a
isv_loop:
        ld (df_i),a
        cp FLD_NOISE
        jr z,isv_full
        call field_ptr
        call field_value_ptr    ; HL = la valeur du nouvel instrument
        ld a,(hl)
        ld de,(isv_delta)
        add hl,de               ; celle de l'instrument affiché
        cp (hl)
        jr z,isv_next           ; la même : rien à écrire
        ld a,(df_i)
        cp 4
        jr nc,isv_value
        ld a,1                  ; l'ADSR a changé
        ld (isv_env),a
isv_value:
        ld a,(df_i)
        call ins_draw_value
        jr isv_next
isv_full:
        call ins_draw_field     ; « PERIODE » ou le nom du sample
isv_next:
        ld a,(df_i)
        inc a
        cp NB_FIELDS
        jr nz,isv_loop
        ld a,(isv_env)
        or a
        ret z                   ; même ADSR : même courbe
        jp ins_draw_env

isv_delta: dw 0
isv_env:   db 0

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
        cp FLD_DIGI             ; DIGIDRUM : la ligne du bruit change de sens
        jp z,ins_show_all
        call ins_draw_field
        ld a,(cur_field)
        cp 4
        ret nc
        jp ins_draw_env         ; l'ADSR a changé : on redessine la courbe

; --- Piano : essai de l'instrument sur la voie A (ou du son composé) -----------
ins_piano:
        call calc_note
        ld b,a
        xor a
        ld (aud_timer),a
        ld a,(ins_son)
        or a
        jr nz,ip_son
        ld a,b
        ld (en_note),a
        ld a,(cur_inst)
        ld (en_ins),a
        ld c,a
        xor a
        ld (aud_voice),a
        jp snd_note_on          ; A = 0 : voie A
ip_son:
        ld a,#80                ; les 4 voix, relâchées ensemble
        ld (aud_voice),a
        ld a,(cur_sedit)
        ld c,a
        jp seq_play_son

; --- Sons composés (f6) : le tableau des 4 voix, comme en MOTIF -------------------
; Champ = 3 x voix + 0 instrument, 1 décalage (voix N : période du bruit),
; 2 volume.  Flèches haut / bas : champ ; gauche / droite : valeur (SHIFT :
; par 10) ; CTRL + gauche / droite : son S1 à S8.
SON_ROW equ 4                   ; titre du tableau ; les voix : lignes 6 à 9

son_cmd:
        cp 6
        jr z,son_left
        cp 7
        jr z,son_right
        cp 8
        jr z,son_up
        cp 9
        ret nz
        ld a,(mod_shift)        ; bas
        or a
        jp nz,oct_down
        ld a,(cur_sfld)
        cp 11
        ret nc
        inc a
        jr son_field
son_up:
        ld a,(mod_shift)
        or a
        jp nz,oct_up
        ld a,(cur_sfld)
        or a
        ret z
        dec a
son_field:                      ; le champ A : les lignes de l'ancien et du
        ld hl,cur_sfld          ; nouveau (une seule si même voix)
        ld b,(hl)
        ld (hl),a
        call fld_voice
        ld c,a                  ; C = voix du nouveau champ
        ld a,b
        call fld_voice
        cp c
        push bc
        call nz,son_draw_row
        pop bc
        ld a,c
        jr son_draw_row

son_left:
        ld a,(mod_ctrl)
        or a
        jr nz,son_prev
        xor a                   ; diminuer
        jr son_change
son_right:
        ld a,(mod_ctrl)
        or a
        jr nz,son_next
        ld a,1                  ; augmenter
        jr son_change
son_prev:
        ld a,(cur_sedit)
        or a
        ret z
        dec a
        jr son_set
son_next:
        ld a,(cur_sedit)
        inc a
        cp NB_SONS
        ret nc
son_set:
        ld (cur_sedit),a
; Le tableau entier (le son cur_sedit)
son_show_all:
        xor a
        call son_setup
        ld a,(cur_sedit)
        jp dly_draw

; A = champ -> A = sa voix (0 à 3)
fld_voice:
        ld d,#FF
fv_loop:
        inc d
        sub 3
        jr nc,fv_loop
        ld a,d
        ret

; La ligne de la voix A
son_draw_row:
        push af
        call son_setup
        ld a,1
        ld (dly_once),a
        pop af
        call dly_voice
        xor a
        ld (dly_once),a
        ret

; Prépare draw_layers pour la voix A du son cur_sedit : dly_ptr, dly_n,
; dly_base (SON_ROW) et dly_sel (cur_sfld)
son_setup:
        ld b,a
        add a,a
        add a,b
        ld c,a                  ; C = 3 x voix
        ld a,(cur_sedit)
        ld (dly_n),a
        add a,a
        add a,a
        add a,a
        add a,a
        add a,c
        ld e,a
        ld d,0
        ld hl,sons
        add hl,de
        ld (dly_ptr),hl
        ld a,(cur_sfld)
        ld h,a
        ld l,SON_ROW
        ld (dly_base),hl
        ret

; Change la valeur du champ cur_sfld.  A = 0 pour diminuer, 1 pour
; augmenter ; le pas est de 1, ou de 10 avec SHIFT.  Chaque genre de champ a
; un décalage dans la voix, un biais (la valeur + biais va de min à max) :
;   instrument  #FF (--), 0 à 31  -> 0 à 32
;   décalage    -24 à +24         -> 104 à 152
;   volume      #FF (-), 0 à 15   -> 0 à 16
;   période     0 à 31 (voix N)
son_change:
        ld (ic_dir),a
        ld a,(mod_shift)
        or a
        ld a,1
        jr z,snc_step
        ld a,10
snc_step:
        ld (ic_step),a
        ld a,(cur_sfld)
        call fld_voice
        ld (snc_v),a
        ld b,a
        add a,a
        add a,b
        ld b,a                  ; B = 3 x voix
        ld a,(cur_sfld)
        sub b                   ; A = champ dans la voix
        cp 1
        jr nz,snc_kind
        ld a,(snc_v)
        cp 3
        ld a,1
        jr nz,snc_kind
        ld a,3                  ; décalage de la voix N : sa période
snc_kind:
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,snc_tab
        add hl,de
        ld de,snc_off
        ld bc,4
        ldir                    ; snc_off, snc_bias, snc_min, snc_max
        ld a,(snc_v)            ; HL = sons + 16 x son + 3 x voix + décalage
        ld b,a
        add a,a
        add a,b
        ld hl,snc_off
        add a,(hl)
        ld e,a
        ld a,(cur_sedit)
        add a,a
        add a,a
        add a,a
        add a,a
        add a,e
        ld e,a
        ld d,0
        ld hl,sons
        add hl,de
        ld a,(snc_bias)
        ld c,a
        ld a,(hl)
        add a,c
        ld b,a                  ; B = valeur + biais
        ld a,(ic_step)
        ld e,a
        ld a,(ic_dir)
        or a
        ld a,b
        jr z,snc_dec
        add a,e                 ; augmenter, sans dépasser le maximum
        jr c,snc_top
        ld b,a
        ld a,(snc_max)
        cp b
        jr c,snc_store
        ld a,b
        jr snc_store
snc_top:
        ld a,(snc_max)
        jr snc_store
snc_dec:
        sub e                   ; diminuer, sans passer sous le minimum
        jr c,snc_bot
        ld b,a
        ld a,(snc_min)
        cp b
        jr nc,snc_store
        ld a,b
        jr snc_store
snc_bot:
        ld a,(snc_min)
snc_store:
        sub c                   ; on retire le biais
        ld (hl),a
        ld a,(snc_v)
        jp son_draw_row

;              décalage, biais, min, max
snc_tab:  db 1,1,0,32           ; instrument
          db 0,128,104,152      ; décalage (-24 à +24)
          db 2,1,0,16           ; volume
          db 0,0,0,31           ; période du bruit (voix N)
snc_off:  db 0
snc_bias: db 0
snc_min:  db 0
snc_max:  db 0
snc_v:    db 0
ins_son:  db 0                  ; panneau INST : 0 instruments, 1 sons composés
cur_sedit: db 0                 ; son composé affiché (0 à 7)
cur_sfld: db 0                  ; son champ choisi (0 à 11)

; --- Affichage ---------------------------------------------------------------
ins_show_all:
        call isa_name
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

; Ligne 2 : le numéro et le nom de l'instrument
isa_name:
        ld hl,#0E02             ; colonne 14, ligne 2 : numéro et nom
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PEN
        ld a,(cur_inst)
        inc a
        call print_dec2
        ld a,' '
        call txt_out
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
        jp print_n

; Seulement la valeur du réglage A (colonne 17 ; le nom est déjà affiché)
ins_draw_value:
        ld (df_i),a
        call field_ptr          ; lit la fiche du réglage
        ld a,(df_i)
        add a,FIELD_ROW
        ld l,a
        ld a,(f_type)           ; valeur signée : son signe en colonne 16,
        cp 2                    ; les chiffres alignés sur les autres
        ld h,17
        jr nz,idv_col
        dec h
idv_col:
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        jr idf_value

; Dessine la ligne du réglage A : son nom, puis sa valeur
ins_draw_field:
        ld (df_i),a
        call field_ptr          ; HL = nom du réglage
        ld (df_text),hl
        ld a,(df_i)             ; la période du bruit d'un digidrum est le
        cp FLD_NOISE            ; numéro de son sample
        call z,df_sample_label
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
        ld a,(f_type)           ; (valeur signée : le signe prend la place
        cp 2                    ; de l'espace, colonne 16)
        ld a,' '
        call nz,txt_out
idf_value:
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
        call txt_out
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
        call txt_out
df_end:
        xor a
        jp TXT_SET_PAPER

; Réglage 7 d'un digidrum : « SAMPLE » et le nom du sample, au lieu de
; « PERIODE ».  Change df_text.
df_sample_label:
        ld a,(cur_inst)
        call inst_ptr
        ld de,INS_FLAGS
        add hl,de
        bit 4,(hl)              ; digidrum ?
        ret z                   ; non : « PERIODE »
        ld hl,txt_dg_nosmp
        ld a,(smp_ok)           ; le nom du sample est lu en zone haute
        or a
        call nz,dg_label_hi
        ld (df_text),hl
        ret

txt_dg_nosmp: db "  SAMPLE       "
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
        db 1,0,16,0,             "DIGIDRUM       "

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
        call txt_out
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

ins_text:                       ; instruments seulement
        db 1,2,2,0,   "INSTRUMENT :",0
        db ENV_COL,4,1,0, "ENVELOPPE",0
        db ENV_COL,10,2,0,"TOUCHE TENUE",0
        db ENV_COL,11,3,0,"PUIS LACHEE",0
        db ENV_COL+9,16,2,0,"INSTR.",0
        db ENV_COL,22,3,0,"COPY",0
        db ENV_COL+5,22,2,0,"COPIER",0
        db ENV_COL,23,3,0,"P",0
        db ENV_COL+5,23,2,0,"COLLER",0
        db ENV_COL,24,3,0,"O",0
        db ENV_COL+5,24,2,0,"SON BANQUE",0
        db #FF
son_text:                       ; sons composés seulement
        db 1,2,2,0,   "SON COMPOSE  ",0
        db ENV_COL+9,16,2,0,"SON",0
        db #FF
ins_common:                     ; les deux
        db 33,2,2,0,  "OCT:",0
        db ENV_COL,13,3,0,240,241,0
        db ENV_COL+3,13,2,0,"REGLAGE",0
        db ENV_COL,14,3,0,242,243,0
        db ENV_COL+3,14,2,0,"VALEUR",0
        db ENV_COL,15,3,0,"SHIFT ",242,243,0
        db ENV_COL+9,15,2,0,"PAR 10",0
        db ENV_COL,16,3,0,"CTRL  ",242,243,0
        db ENV_COL,17,3,0,"SHIFT ",240,241,0
        db ENV_COL+9,17,2,0,"OCTAVE",0
        db ENV_COL,19,3,0,"PIANO",0
        db ENV_COL+6,19,2,0,"ESSAI",0
        db ENV_COL,20,3,0,"ESPACE",0
        db ENV_COL+7,20,2,0,"LECTURE",0
        db ENV_COL,21,3,0,"f6",0
        db ENV_COL+3,21,2,0,"MODE",0
        db #FF


; ============================================================================
; ECRAN MIXAGE ET DISQUE
; ============================================================================
DSK_VOICE_ROW equ 5             ; ligne de la voix A
DSK_NAME_ROW  equ 11            ; ligne du nom de fichier
DSK_MSG_ROW   equ 25            ; ligne des messages (comme les autres panneaux)
NAME_LEN      equ 8

; --- Commandes ---------------------------------------------------------------
; Affiche un message sur la ligne des messages (ligne 17 sur l'écran f3,
; ligne 25 sur l'écran f2).  HL = texte
dsk_message:
        ld (last_msg),hl        ; on garde le dernier message
        push hl
        ld a,(screen)
        cp 2                    ; écran f3 : ligne 17
        ld hl,256*1+DSK_MSG_ROW
        jr z,msg_row
        ld l,INS_MSG_ROW        ; écrans f2 et f4 : ligne 25
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
        call txt_out
        pop hl
        pop bc
        djnz dm_loop
        ret
dm_pad:
        ld a,' '                ; on efface la fin de la ligne
        push bc
        call txt_out
        pop bc
        dec b
        ld a,b
        cp 1
        jr nz,dm_pad
        ret

; --- Saisie du nom de fichier ------------------------------------------------
; Saisie d'un nom de NAME_LEN caractères (lettres, chiffres, '-').
; HL = position du nom à l'écran (colonne * 256 + ligne), DE = le nom,
; modifié sur place, BC = extension affichée après le nom.
; -> Carry = 1 : RETURN ; Carry = 0 : ESC (le nom garde ce qui a été tapé).
name_edit:
        ld (en_pos),hl
        ld (en_buf),de
        ld (en_ext),bc
en_flush:                       ; on vide les frappes en attente
        call KM_READ_CHAR
        jr c,en_flush
        ld hl,(en_buf)          ; position = longueur actuelle du nom
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
        call en_draw
        ld hl,(en_pos)          ; curseur de saisie
        ld a,(name_pos)
        add a,h
        ld h,a
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
        ld hl,(en_buf)
        add hl,de
        ld a,(hl)
        call txt_out
en_wait:
        xor a
        call TXT_SET_PAPER
        call KM_WAIT_CHAR       ; attend une frappe (le son est coupé)
        cp 13
        jp z,en_done            ; RETURN : fini
        cp #FC
        jp z,en_esc             ; ESC : annulé
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
        ld hl,(en_buf)          ; nouveau nom : on efface l'ancien
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
        ld hl,(en_buf)
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
        ld hl,(en_buf)
        add hl,de
        ld (hl),' '
        jp en_loop
en_esc:
        ld a,KEY_ESC            ; on attend qu'ESC soit relâchée, pour ne pas
        call KM_TEST_KEY        ; qu'elle compte comme "quitter"
        jr nz,en_esc
        call en_draw
        or a                    ; Carry = 0 : annulé
        ret
en_done:
        call en_draw
        scf                     ; Carry = 1 : nom validé
        ret

; Dessine le nom en cours de saisie (jaune inversé) et son extension
en_draw:
        ld hl,(en_pos)
        call TXT_SET_CURSOR
        ld a,1
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        ld hl,(en_buf)
        ld b,NAME_LEN
        call print_n
        xor a
        call TXT_SET_PAPER
        ld a,3
        call TXT_SET_PEN
        ld hl,(en_ext)
        jp print_str

; --- Sauvegarde --------------------------------------------------------------
disk_save:
        ld hl,song_bank         ; bloc v2 : la banque de samples utilisée
        ld b,8
dsv_clear:
        ld (hl),0
        inc hl
        djnz dsv_clear
        ld a,(smp_count)
        or a
        jr z,dsv_go             ; pas de banque : nom vide
        ld hl,smp_name
        ld de,song_bank
        ld bc,8
        ldir
dsv_go:
        call song_to_bank       ; l'image du morceau, à jour, dans le bloc 4
        jp sng_write            ; NOM.SNG : le morceau et ses samples (sngio.asm)
; Sauve le début du morceau.  HL = extension, DE = nombre d'octets depuis
; song_data, BC = message affiché si tout va bien.
save_file:
        push hl
        ld hl,song_data
        ld (sf_addr),hl
        pop hl
; Même chose, mais depuis l'adresse (sf_addr) : un motif seul, par exemple.
; (sf_bank) = 1 : l'adresse est dans le bloc 4 (remis à 0 ici).
save_block_main:
        xor a
        ld (sf_bank),a
save_block:
        ld (sf_size),de
        ld (sf_msg),bc
        push hl
        call silence
        pop hl
        call build_filename_ext ; nom + extension
        ret nc                  ; nom vide
        ld hl,txt_m_saving
        call dsk_message
        ld a,(fname_len)
        ld b,a
        ld hl,fname_full
        ld de,io_buffer
        call CAS_OUT_OPEN
        jp nc,disk_error
        ld a,(sf_bank)
        or a
        ld hl,(sf_addr)
        ld de,(sf_size)
        ld bc,0
        ld a,2                  ; fichier binaire
        jr z,ds_main
        call bank_cas_out       ; depuis le bloc 4
        jr ds_written
ds_main:
        call CAS_OUT_DIRECT
ds_written:
        jp nc,ds_abandon
        call CAS_OUT_CLOSE
        jp nc,disk_error
        ld hl,(sf_msg)
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
        ld hl,#FFFF             ; (code d'erreur : rien de lu, à l'ouverture)
        ld (sio_count),hl
        jp nc,sng_error
        xor a
        ld (dl_v4f),a
        ld hl,SONG_SIZE3        ; la taille doit être exactement la bonne :
        or a                    ; version 3...
        sbc hl,bc
        jr z,dl_size
        jr c,dl_v4              ; ... plus long : version 4, avec les samples
        ld hl,SONG_SIZE         ; ... version 2 (sans l'enchaînement)...
        or a
        sbc hl,bc
        jr z,dl_size
        ld hl,SONG_V1           ; ... ou version 1 (sans le bloc v2)
        or a
        sbc hl,bc
        jp nz,dl_bad
dl_size:
        ld hl,BANK_SONG         ; le fichier va tel quel dans le bloc 4
        call bank_cas_in
        jp nc,dl_abandon
        call CAS_IN_CLOSE
        jr dl_loaded
dl_v4:
        call sng_read           ; octet par octet : l'image, puis la banque
        ret nc                  ; (message déjà affiché)
        ld a,1
        ld (dl_v4f),a
dl_loaded:
        ld hl,BANK_SONG         ; puis l'en-tête, les instruments, les noms
        ld de,song_data         ; et les sons en mémoire principale
        ld bc,SONG_FIXED
        call bank_get
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
        ld a,(song_data+4)      ; version 1 : bloc v2 par défaut
        cp 2
        jr c,dl_v1
        ld hl,BANK_V2           ; version 2 ou 3 : le bloc v2 du fichier
        ld de,song_v2
        ld bc,SONG_EXTRA
        call bank_get
        jr dl_v3
dl_v1:
        ld hl,song_v2
        ld b,SONG_EXTRA
dl_clear:
        ld (hl),0
        inc hl
        djnz dl_clear
dl_v3:
        ld a,(song_data+4)      ; version 3 : l'enchaînement du fichier
        cp 3
        jr c,dl_old
        ld hl,BANK_V3
        ld de,song_v3
        ld bc,SONG_V3_LEN
        call bank_get
        call song_sanitize
        jr dl_ver
dl_old:
        call song_default       ; avant : une position par motif utilisé
dl_ver:
        ld a,SONG_VER
        ld (song_data+4),a
dl_v2:
        call song_loaded
        ld a,(dl_v4f)           ; version 4 : la banque était dans le fichier
        or a
        jr z,dl_bank_name
        ld hl,(sio_smp)
        ld a,h
        or l
        ld hl,txt_m_loaded
        jp z,dsk_message
        ld hl,txt_m_withbank
        jp dsk_message
dl_bank_name:
        ld a,(song_bank)        ; une banque de samples associée ?
        or a
        jr z,dl_done
        ld a,(smp_ok)
        or a
        jp nz,song_load_bank    ; oui : on la charge
dl_done:
        ld hl,txt_m_loaded
        jp dsk_message
dl_bad:
        call CAS_IN_ABANDON
        ld hl,txt_m_bad
        jp dsk_message
dl_abandon:
        call CAS_IN_ABANDON
        jp disk_error
dl_corrupt:                     ; contenu illisible : on repart du morceau d'usine
        call init_song
        call song_loaded
        ld hl,txt_m_bad
        jp dsk_message

song_sig: db "SQ16"

; Le morceau vient de changer : on repart du motif 1 et on met tout à jour
song_loaded:
        ld a,#FF                ; rien de préparé à l'avance
        ld (next_id),a
        xor a
        ld (sp_cur),a           ; panneau SONG : au début
        ld (sp_top),a
        ld (sp_mix),a
        ld (cur_pat),a
        ld (cur_l),a
        ld (cur_s),a
        call pat_fetch
        call seq_set_pattern
        jp snd_init

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
        ld hl,(bf_name)         ; fname, ou le nom d'un motif (panels.asm)
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


; Les caractères 240 à 243 du CPC sont les flèches haut, bas, gauche, droite.
screen_text:
        db 1,2,2,0,  "MOTIF:",0
        db 25,2,2,0, "BPM:",0
        db 1,HEAD_ROW,2,0, "PAS",0
        db 1,19,2,0, "PINCEAU",0
        db 1,20,3,0, "f8",0
        db 4,20,2,0, "SAUVER",0
        db 11,20,3,0,"f9",0
        db 14,20,2,0,"CHARGER",0
        db 23,20,3,0,"L",0
        db 1,21,3,0, 242,243,240,241,0
        db 6,21,2,0, "PAS/VOIX",0
        db 15,21,3,0,"ENTER",0
        db 21,21,2,0,"ON/OFF",0
        db 28,21,3,0,"DEL",0
        db 32,21,2,0,"VIDER",0
        db 1,22,3,0, "PIANO",0
        db 7,22,2,0, "NOTE",0
        db 15,22,3,0,"CLR",0
        db 19,22,2,0,"ARRET",0
        db 26,22,3,0,"COPY",0
        db 31,22,2,0,"PRENDRE",0
        db 1,23,3,0, "TAB",0
        db 5,23,2,0, "EDITER",0
        db 12,23,3,0,"ESPACE",0
        db 19,23,2,0,"LIRE",0
        db 25,23,3,0,"f6",0
        db 28,23,2,0,"MODE",0
        db 33,23,3,0,"f7",0
        db 36,23,2,0,"MUET",0
        db 1,24,3,0, "SHIFT",240,241,0
        db 9,24,2,0, "OCT",0
        db 13,24,3,0,242,243,0
        db 16,24,2,0,"INS",0
        db 20,24,3,0,"CTRL",240,241,0
        db 27,24,2,0,"BPM",0
        db 31,24,3,0,242,243,0
        db 34,24,2,0,"MOTIF",0
        db #FF

        include 'sound.asm'
        include 'seq.asm'
        include 'song.asm'
        include 'tables.asm'
        include 'smpscreen.asm'
        include 'banks.asm'
        include 'panels.asm'
        include 'grid.asm'
        include 'songpanel.asm'
        include 'sngio.asm'
        include 'diskpanel.asm'
        include 'smptables.asm'

; ----------------------------------------------------------------------------
; Variables du programme
; ----------------------------------------------------------------------------
screen:     db 0                ; écran en cours : 0 = séquenceur, 1 = instrument,
                                ; 2 = mixage et disquette, 3 = samples
esc_count:  db 0                ; nombre d'images où ESC est restée enfoncée
tick_last:  db 0                ; instant du dernier tour de son (1/300 s)
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
en_pos:     dw 0                ; name_edit : position du nom à l'écran,
en_buf:     dw 0                ;   le nom modifié,
en_ext:     dw 0                ;   l'extension affichée après
new_armed:  db 0
fname:      db "MORCEAU1"        ; nom de fichier, complété par des espaces
fname_full: ds 13
fname_len:  db 0
bf_ext_ptr: dw 0                ; extension du nom de fichier (.SNG ou .SMP)
cur_smp:    db 0                ; écran Samples : sample choisi
smp_field:  db 0                ;   réglage en cours
smp_tried:  db 0                ;   1 = DRUMS.SMP a déjà été essayé
smp_name:   db "--------"       ;   nom de la banque chargée
smp_nfiles: db 0                ;   leur nombre
smp_pick:   db 0                ;   celui qui est choisi
smp_fname:  ds 13               ;   nom complet "NOM.SMP"
cd_i:       db 0
rsx_found:  db 0                ; 1 = commande AMSDOS #84 trouvée
rsx_far:    ds 3                ;   son adresse (2 octets) et sa ROM (1 octet)
sdr_i:      db 0
sdr_ms:     dw 0
sdf_i:      db 0
sc_dir:     db 0
scan_ext:   dw 0                ; extension cherchée dans le catalogue
ch_names:   dw 0                ; liste de choix : adresse des noms,
ch_count:   db 0                ;   leur nombre,
ch_rows:    db 0                ;   lignes par colonne,
ch_len:     db 0                ;   caractères par nom (juste après ch_rows),
ch_col0:    db 0                ;   colonne de départ,
ch_row0:    db 0                ;   ligne de départ (juste après ch_col0),
ch_colw:    db 0                ;   largeur d'une colonne,
ch_page:    db 255              ;   noms par page (255 : une seule page),
ch_top:     db 0                ;   premier nom de la page affichée
last_msg:   dw txt_m_none       ; dernier message affiché
sf_size:    dw 0                ; save_file : nombre d'octets,
sf_msg:     dw 0                ;   message de réussite
sf_addr:    dw 0                ;   et adresse du premier octet (save_block)
sf_bank:    db 0                ;   1 = cette adresse est dans le bloc 4
bf_name:    dw fname            ; nom utilisé par build_filename
dl_v4f:     db 0                ; 1 = le morceau chargé était en version 4
txt_need_6128: db "SEQ-16 : IL FAUT UN CPC 6128",0
clip:       ds 22               ; presse-papiers : réglages (16) et nom (6)
clip_ok:    db 0                ;   1 = il contient un instrument
it_pick:    db 0                ; son choisi dans la banque
dg_pending: db 0                ; 1 = un digidrum attend d'être joué
dg_smp:     db 0                ;   son numéro de sample,
dg_chan:    db 0                ;   la voie de l'AY,
dg_semi:    db 0                ;   la hauteur (demi-tons),
dg_att:     db 0                ;   l'atténuation,
dg_fx:      db 0                ;   l'effet du pas (COUPE : dg_cut)
dg_debt:    db 0                ; images de séquenceur à rattraper

; La routine de lecture des samples est en dernier : la source de sa partie
; haute, recopiée en zone haute au démarrage, est ensuite recouverte par le
; morceau (voir song_data).
        include 'sample.asm'

; Puis le code et les données du démarrage (boot.asm), assemblés pour
; BOOT_RUN : recopiés là au démarrage, avant d'être recouverts par le morceau
BOOT_RUN equ #A000-2048                 ; io_buffer
boot_src:
        org BOOT_RUN,boot_src
        include 'boot.asm'
boot_end:
boot_len equ boot_end-BOOT_RUN
        assert boot_end <= #A000
        org boot_src+boot_len
        assert BOOT_RUN >= boot_src             ; (copie à reculons, voir boot_6128)

end_of_program:

; ----------------------------------------------------------------------------
; Le morceau en mémoire principale, juste après le programme (il n'est pas
; dans SEQ16.BIN : il est rempli au démarrage).  Les 32 motifs sont dans le
; bloc 4 de la mémoire supplémentaire (voir bank.asm) ; seul le motif
; affiché et joué est ici, dans pat_work.
; ----------------------------------------------------------------------------
song_data   equ smp_blk_src     ; le morceau recouvre la source de la zone
                                ; haute, déjà recopiée par smp_install
snd_master  equ song_data+5     ; volume général des voix A, B, C, N
snd_mute    equ song_data+9     ; voix muettes (bits 0 à 3)
instruments equ song_data+16
inst_names  equ instruments+NB_INST*16
sons        equ inst_names+NB_INST*6
song_v2     equ sons+NB_SONS*16 ; bloc v2 (voir song.asm)
song_mode   equ song_v2      ; mode de lecture des samples
song_bank   equ song_v2+1    ; nom de la banque .SMP (8 caractères)
song_v3     equ song_v2+SONG_EXTRA  ; bloc v3 : l'enchaînement (songpanel.asm)
song_len    equ song_v3             ;   nombre de positions
song_loop   equ song_v3+1           ;   position de la boucle
song_list   equ song_v3+2           ;   64 x (motif, répétitions, transposition)
pat_names   equ song_list+64*3      ;   32 noms de motifs de 8 caractères
song_end    equ song_v3+SONG_V3_LEN

; En haut de la mémoire principale, hors de #4000-#7FFF (bank_copy y copie
; pendant que le bloc 4 est montré) :
io_buffer   equ #A000-2048      ; 2 Ko de travail pour AMSDOS
pat_work    equ io_buffer-PAT_SIZE      ; le motif affiché et joué
pat_ahead   equ pat_work-PAT_SIZE       ; morceau : le motif suivant, à l'avance
mem_free    equ pat_ahead-song_end      ; place libre pour la suite
        assert song_end <= pat_ahead
        assert pat_work >= #8000
        print "fin du programme=",{hex}end_of_program," fin du morceau=",{hex}song_end," libre=",mem_free," banque=",BANK_MAX," zone haute=",{hex}smp_blk_end
        assert BANK_MAX >= 2048         ; la banque d'usine DRUMS.SMP doit tenir

        save 'SEQ16.BIN',start,end_of_program-start,DSK,'build/seq16-fr.dsk'
