; ============================================================================
; SEQ-16 - Panneau MOTIF : la grille de 16 pas et le panneau de la note
; (lot 3 du plan, voir PLAN.md et plan/img/1_edition.png)
;
;   ligne  2      motif, mode, tempo, état
;   lignes 4-8    panneau de la note du curseur : titre (pas, voix), clavier
;                 de 2 octaves (l'octave de saisie), NOTE, INS, VOL, FX
;   ligne  10     numéros des pas
;   lignes 11-17  une ligne par voix (11, 13, 15, 17) ; en son composé, la
;                 voix SON en ligne 11 et les couches du son en lignes 13-18
;   ligne  19     le pinceau : la note que pose ENTER
;   lignes 21-24  aide ; ligne 25 : messages
;
; Une case = 2 colonnes, les 16 pas groupés par temps (colonne
; 6 + 2 x pas + pas / 4).  Premier caractère : ■ note (orange sur la voix
; de bruit), · vide (jaune sur les temps), X arrêt, ─ note tenue jusqu'à son
; arrêt ; second caractère : la suite du trait de durée, ou ◄ sous le
; curseur.  Le pas joué s'allume (bloc plein jaune) ; le curseur met en
; inverse le numéro de son pas et la lettre de sa voix.
; ============================================================================

STATUS_ROW equ 2
BOX_TOP    equ 4
KEYS_ROW   equ 5                ; touches noires ; les blanches en dessous
PANEL_ROW  equ 7
BOX_BOT    equ 8
LAYER_ROW  equ 13
BRUSH_ROW  equ 19
KEYS_COL   equ 3

CH_ON      equ 233              ; ■
CH_FULL    equ 143              ; bloc plein
CH_DOT     equ 144              ; ·
CH_HOLD    equ 154              ; ─
CH_OFF     equ 203              ; X
CH_MARK    equ 247              ; ◄
CH_BRUSH    equ 237              ; ♪

; --- Petites aides --------------------------------------------------------------
; B = encre, C = fond
colors:
        ld a,c
        push bc
        call TXT_SET_PAPER
        pop bc
        ld a,b
        jp TXT_SET_PEN

; Affiche B fois le caractère A
out_rep:
        call TXT_OUTPUT
        djnz out_rep
        ret

; Efface B lignes de 40 colonnes à partir de la ligne L
blank_rows:
        push bc
        push hl
        ld h,1
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        ld a,' '
        ld b,40
        call out_rep
        call snd_tick           ; la musique continue pendant le dessin
        pop hl
        pop bc
        inc l
        djnz blank_rows
        ret

; NZ en son composé
is_layered:
        ld hl,(seq_pattern)
        ld a,(hl)
        or a
        ret

; Z si la voix dg_l est la voix de bruit (voix séparées, voix 3)
lane_is_noise:
        call is_layered
        ret nz
        ld a,(dg_l)
        cp 3
        ret

; A = pas -> A = colonne (6 + 2 x pas + pas / 4)
step_col:
        ld c,a
        srl a
        srl a
        add a,c
        add a,c
        add a,6
        ret

; A = voix -> A = ligne
lane_row:
        add a,a
        add a,GRID_ROW
        ret

; A = note (0-95) -> nom sur 2 caractères ("C ", "C#") et octave
print_note:
        call split_note         ; A = 0-11, D = octave
        push de
        add a,a
        ld e,a
        ld d,0
        ld hl,note_names
        add hl,de
        ld a,(hl)
        call TXT_OUTPUT
        inc hl
        ld a,(hl)
        cp '-'
        jr nz,pn_sharp
        ld a,' '
pn_sharp:
        call TXT_OUTPUT
        pop de
        ld a,d
        add a,'0'
        jp TXT_OUTPUT

; A (0-255) en 2 chiffres hexadécimaux
print_hex2:
        push af
        rrca
        rrca
        rrca
        rrca
        and 15
        call print_hex1
        pop af
        and 15
        jp print_hex1

; A = instrument -> "01 LEAD  " (numéro et nom de 6 caractères)
print_inst:
        push af
        inc a
        call print_dec2
        ld a,' '
        call TXT_OUTPUT
        pop af
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

; Pendant un long affichage, la boucle principale ne tourne pas : si une
; image (6 tops de 1/300 s) s'est écoulée depuis le dernier tour de son, on
; en joue un ici.  Ne touche pas à l'écran ; les registres ne sont pas gardés.
snd_tick:
        call KL_TIME_PLEASE     ; L = temps, en 1/300 s
        ld a,(tick_last)
        ld b,a
        ld a,l
        sub b
        cp 6
        ret c                   ; pas encore une image
        ld a,b
        add a,6
        ld (tick_last),a
        ld a,1
        ld (sc_ticked),a
        call seq_frame
        jp snd_frame

; Boucle principale : un tour de séquenceur et de son par image écoulée
; depuis le dernier (jusqu'à 10 ; au-delà, après un accès disque par
; exemple, on repart de maintenant).  Un long dessin ne ralentit plus le
; tempo : les images passées sont rattrapées.  Si moins d'une image s'est
; écoulée, on joue quand même un tour, sauf si snd_tick l'a déjà fait.
snd_catchup:
        call KL_TIME_PLEASE     ; L = temps, en 1/300 s
        ld a,(tick_last)
        ld b,a
        ld a,l
        sub b                   ; A = tops écoulés
        cp 6
        jr c,sc_short
        cp 61
        jr nc,sc_resync         ; trop : on repart de maintenant
sc_loop:
        sub 6
        ld (sc_left),a
        ld a,(tick_last)
        add a,6
        ld (tick_last),a
        call seq_frame
        call snd_frame
        ld a,(sc_left)
        cp 6
        jr nc,sc_loop
        ret
sc_short:
        ld a,(sc_ticked)
        or a
        ret nz                  ; snd_tick a déjà joué cette image
sc_resync:
        ld a,l
        ld (tick_last),a
        call seq_frame
        jp snd_frame

sc_ticked: db 0                 ; 1 = snd_tick a joué pendant ce tour
sc_left:   db 0

; A = note (0-95) -> A = note dans l'octave (0-11), D = octave (0-7)
split_note:
        ld d,0
sn_loop:
        cp 12
        ret c
        sub 12
        inc d
        jr sn_loop

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

; Carry = 1 si un trait de durée part de la droite de la case (dg_l, dg_s) :
; la dernière case non vide jusqu'ici est une note, et la prochaine case non
; vide après est son arrêt
cell_tail:
        call cell_ptr
        push hl
        ld a,(dg_s)
        inc a
        ld b,a
        ld de,-16
ct_back:
        ld a,(hl)
        cp NOTE_NONE
        jr nz,ct_found
        add hl,de
        djnz ct_back
        pop hl
        or a                    ; rien avant
        ret
ct_found:
        pop hl
        cp NOTE_OFF
        jr nc,ct_no             ; un arrêt : pas de note tenue
        ld a,(dg_s)
        ld b,a
        ld a,15
        sub b
        jr z,ct_no              ; dernier pas
        ld b,a
        ld de,16
ct_fwd:
        add hl,de
        ld a,(hl)
        cp NOTE_NONE
        jr nz,ct_next
        djnz ct_fwd
ct_no:
        or a
        ret
ct_next:
        cp NOTE_OFF
        scf
        ret z
        or a
        ret

; --- Une case -------------------------------------------------------------------
; Z si (dg_l, dg_s) est la case du curseur
is_cursor_cell:
        ld a,(dg_l)
        ld hl,cur_l
        cp (hl)
        ret nz
        ld a,(dg_s)
        ld hl,cur_s
        cp (hl)
        ret

draw_cell:
        ld a,(dg_l)
        call lane_row
        ld l,a
        ld a,(dg_s)
        call step_col
        ld h,a
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        call lane_is_noise      ; couleur de la voix : cyan, orange (bruit)
        ld a,2
        jr nz,dce_lane
        ld a,3
dce_lane:
        ld (dc_pen),a
        call cell_tail
        ld a,0
        rla
        ld (dc_tail),a          ; 1 = trait de durée à droite
        call cell_ptr
        ld a,(hl)
        cp NOTE_OFF
        jr z,dce_off
        jr c,dce_note
        ld a,(dc_tail)          ; vide : la note précédente tient encore ?
        or a
        jr z,dce_dot
        ld a,(dc_pen)
        ld c,CH_HOLD
        jr dce_put
dce_dot:
        ld a,(dg_s)             ; point jaune sur les temps, cyan ailleurs
        and 3
        ld a,1
        jr z,dce_dot_pen
        ld a,2
dce_dot_pen:
        ld c,CH_DOT
        jr dce_put
dce_off:
        ld a,3
        ld c,CH_OFF
        jr dce_put
dce_note:
        ld c,CH_ON
        ld a,(dg_s)             ; le pas joué s'allume
        ld hl,shown_pos
        cp (hl)
        ld a,(dc_pen)
        jr nz,dce_put
        ld c,CH_FULL
        ld a,1
dce_put:                        ; A = encre, C = caractère
        ld b,a
        call is_cursor_cell
        ld a,b
        jr nz,dce_pen1
        ld a,1                  ; sous le curseur : jaune
dce_pen1:
        push bc
        call TXT_SET_PEN
        pop bc
        ld a,c
        call TXT_OUTPUT
        call is_cursor_cell     ; second caractère
        jr nz,dce_second
        ld a,1
        call TXT_SET_PEN
        ld a,CH_MARK
        call TXT_OUTPUT
        jr dce_gap
dce_second:
        call dce_tail_char
dce_gap:                        ; la colonne entre deux temps
        ld a,(dg_s)
        cp 15
        ret z
        and 3
        cp 3
        ret nz
dce_tail_char:                  ; trait (ou espace), couleur de la voix
        ld a,(dc_pen)
        call TXT_SET_PEN
        ld a,(dc_tail)
        or a
        ld a,' '
        jr z,dce_tc_out
        ld a,CH_HOLD
dce_tc_out:
        jp TXT_OUTPUT

; --- Une voix, la grille -----------------------------------------------------------
; La voix dg_l : son nom et ses 16 cases
draw_lane:
        call draw_label
        xor a
dln_step:
        ld (dg_s),a
        call draw_cell
        ld a,(dg_s)             ; tous les 4 pas, un tour de son en retard
        and 3
        cp 3
        call z,snd_tick
        ld a,(dg_s)
        inc a
        cp 16
        jr nz,dln_step
        ret

; Les numéros des pas et toutes les voix.  Si le mode a changé, on efface
; les lignes qui ne seront pas redessinées.
draw_grid:
        call draw_heads
        call is_layered
        ld hl,mode_shown
        cp (hl)
        jr z,dgr_go
        ld (hl),a
        ld a,#FF
        ld (layers_shown),a     ; les couches seront redessinées
        call is_layered
        jr nz,dgr_clear_comp
        ld l,GRID_ROW+1         ; voix séparées : lignes 12, 14, 16, 18
        ld b,4
dgr_clear:
        push bc
        push hl
        ld b,1
        call blank_rows
        pop hl
        pop bc
        inc l
        inc l
        djnz dgr_clear
        jr dgr_go
dgr_clear_comp:
        ld l,GRID_ROW+1         ; son composé : ligne 12 (puis les couches)
        ld b,1
        call blank_rows
dgr_go:
        xor a
dgr_lane:
        ld (dg_l),a
        call draw_lane
        call snd_tick           ; la musique continue pendant le dessin
        call is_layered
        ret nz                  ; son composé : une seule voix
        ld a,(dg_l)
        inc a
        cp 4
        jr nz,dgr_lane
        ret

; Nom de la voix dg_l (colonnes 1 à 5) : jaune, orange si elle est muette,
; en inverse si le curseur y est
draw_label:
        ld a,(dg_l)
        call lane_row
        ld l,a
        ld h,1
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        ld a,' '
        call TXT_OUTPUT
        call is_layered         ; voix muette ? (son composé : la voix A)
        ld a,0
        jr nz,dlb_mask
        ld a,(dg_l)
dlb_mask:
        call chan_mask
        ld hl,snd_mute
        and (hl)
        ld b,1                  ; B = encre : jaune,
        jr z,dlb_audible
        ld b,3                  ;   orange si muette
dlb_audible:
        ld c,0
        ld a,(dg_l)
        ld hl,cur_l
        cp (hl)
        jr nz,dlb_colors
        ld c,b                  ; voix du curseur : en inverse
        ld b,0
dlb_colors:
        call colors
        call is_layered
        jr nz,dlb_son
        ld a,(dg_l)
        ld e,a
        ld d,0
        ld hl,lane_letters
        add hl,de
        ld a,(hl)
        call TXT_OUTPUT
        ld b,3
        jr dlb_pad
dlb_son:
        ld hl,txt_lab_son       ; "SON"
        call print_str
        ld b,1
dlb_pad:
        push bc
        xor a
        call TXT_SET_PAPER
        pop bc
        ld a,' '
        jp out_rep

lane_letters: db "ABCN"
txt_lab_son:  db "SON",0

; --- Numéros des pas ------------------------------------------------------------
draw_heads:
        xor a
dhs_loop:
        push af
        call draw_head
        pop af
        inc a
        cp 8
        jr nz,dhs_next
        push af
        call snd_tick           ; à mi-chemin, un tour de son
        pop af
dhs_next:
        cp 16
        jr nz,dhs_loop
        jp snd_tick

; Numéro du pas A : orange en inverse sur 2 colonnes si c'est le pas joué,
; jaune en inverse si c'est le pas du curseur, sinon jaune sur les temps
draw_head:
        ld (dh_step),a
        call step_col
        ld h,a
        ld l,HEAD_ROW
        call TXT_SET_CURSOR
        ld a,(dh_step)
        ld hl,shown_pos
        cp (hl)
        ld bc,0*256+3           ; pas joué : bleu sur orange
        jr z,dh_print
        ld hl,cur_s
        cp (hl)
        ld bc,0*256+1           ; pas du curseur : bleu sur jaune
        jr z,dh_print
        and 3
        ld bc,1*256+0           ; un temps : jaune
        jr z,dh_print
        ld bc,2*256+0           ; ailleurs : cyan
dh_print:
        push bc
        call colors
        ld a,(dh_step)
        call print_hex1
        pop bc
        ld a,c                  ; la 2e colonne : orange seulement pour le
        cp 3                    ; pas joué
        jr z,dh_second
        xor a
        call TXT_SET_PAPER
dh_second:
        ld a,' '
        call TXT_OUTPUT
        xor a
        jp TXT_SET_PAPER

; --- Repère du pas joué -----------------------------------------------------------
show_playhead:
        ld a,(seq_playing)
        or a
        jr z,hide_playhead
        ld a,(seq_pos)
        ld hl,shown_pos
        cp (hl)
        ret z                   ; déjà au bon endroit
        ld b,(hl)
        ld (hl),a
        ld a,b
        call draw_column        ; l'ancien pas s'éteint
        ld a,(shown_pos)
        jr draw_column          ; le nouveau s'allume
hide_playhead:
        ld a,(shown_pos)
        cp #FF
        ret z
        ld b,a
        ld a,#FF
        ld (shown_pos),a
        ld a,b
        ; continue dans draw_column

; Le pas A : son numéro et ses cases
draw_column:
        cp #FF
        ret z
        ld (dg_s),a
        call draw_head
        xor a
dcl_lane:
        ld (dg_l),a
        call draw_cell
        call is_layered
        ret nz
        ld a,(dg_l)
        inc a
        cp 4
        jr nz,dcl_lane
        ret

; --- Curseur -------------------------------------------------------------------
; Redessine la voix du curseur (les traits de durée ont pu changer) et le
; panneau, après une modification de la case
draw_cursor_cell:
        ld a,1                  ; une case a changé : le motif est à ranger
        ld (pat_dirty),a
        ld a,(cur_l)
        ld (dg_l),a
        call draw_lane
        jp draw_panel

; Déplace le curseur en voix B, pas C
move_cursor:
        ld a,(cur_l)
        ld (mc_l),a
        ld a,(cur_s)
        ld (mc_s),a
        ld a,b
        ld (cur_l),a
        ld a,c
        ld (cur_s),a
        ld a,(mc_l)             ; l'ancienne case, son pas, sa voix
        ld (dg_l),a
        ld a,(mc_s)
        ld (dg_s),a
        call draw_cell
        call draw_label
        ld a,(mc_s)
        call draw_head
        ld a,(cur_l)            ; la nouvelle
        ld (dg_l),a
        ld a,(cur_s)
        ld (dg_s),a
        call draw_cell
        call draw_label
        ld a,(cur_s)
        call draw_head
        call draw_panel
        call pickup_inst
        jp preview_cell

; --- Ligne d'état ------------------------------------------------------------------
show_pattern:                   ; numéro du motif et son nom (celui de son
        ld hl,256*7+STATUS_ROW  ; fichier .PAT) ; le type se voit au cadre
        call TXT_SET_CURSOR     ; (VOIX A... ou SON COMPOSE) et à la grille
        ld bc,3*256+0
        call colors
        ld a,(cur_pat)
        inc a
        call print_dec2
        ld a,' '
        call TXT_OUTPUT
        ld a,(cur_pat)
        call pat_name_ptr       ; HL = nom (8 caractères)
        ld b,8
spn_char:
        ld a,(hl)
        cp ' '+1                ; les 0 de fin de nom : des espaces
        jr nc,spn_put
        ld a,' '
spn_put:
        call TXT_OUTPUT         ; (garde les registres)
        inc hl
        djnz spn_char
        ld a,' '                ; jusqu'à BPM
        ld b,5
        jp out_rep

show_speed:
        ld hl,256*29+STATUS_ROW
        call TXT_SET_CURSOR
        ld bc,3*256+0
        call colors
        ld a,(seq_bpm)
        jp print_dec3

show_state:
        ld a,(screen)
        or a
        ret nz
        ld hl,256*33+STATUS_ROW
        call TXT_SET_CURSOR
        ld a,(seq_playing)
        or a
        jr nz,sst_play
        ld bc,2*256+0
        call colors
        ld a,CH_ON
        call TXT_OUTPUT
        ld hl,txt_stop
        jp print_str
sst_play:
        ld bc,1*256+0
        call colors
        ld a,246                ; ►
        call TXT_OUTPUT
        ld hl,txt_play
        jp print_str

; Octave de saisie : le clavier du panneau (écran Instrument : sa valeur)
show_octave:
        ld a,(screen)
        or a
        jp z,draw_panel
        ld hl,#2502             ; instrument : colonne 37, ligne 2
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PEN
        ld a,(cur_oct)
        add a,'0'
        jp TXT_OUTPUT

; --- Le pinceau (ligne 19) -----------------------------------------------------------
; La note que pose ENTER (sur la voix de bruit : sa période) et l'instrument
; (ou le son composé) de saisie ; « VERROU » si CAPS LOCK le fige.
show_inst:
        ld a,(screen)
        or a
        ret nz
        ld hl,256*9+BRUSH_ROW
        call TXT_SET_CURSOR
        ld bc,3*256+0
        call colors
        ld a,CH_BRUSH
        call TXT_OUTPUT
        ld a,' '
        call TXT_OUTPUT
        ld a,(cur_l)
        ld (dg_l),a
        call lane_is_noise
        jr nz,sb_note
        ld a,'B'                ; bruit : "BR" et la période
        call TXT_OUTPUT
        ld a,'R'
        call TXT_OUTPUT
        ld a,(brush_noise)
        call print_hex2
        jr sb_ins
sb_note:
        ld a,(brush_note)
        call print_note
        ld a,' '
        call TXT_OUTPUT
sb_ins:
        ld hl,256*16+BRUSH_ROW
        call TXT_SET_CURSOR
        ld a,2
        call TXT_SET_PEN
        call is_layered
        jr nz,sb_son
        ld hl,txt_f_ins
        call print_str
        ld a,3
        call TXT_SET_PEN
        ld a,(cur_inst)
        call print_inst
        jr sb_lock
sb_son:
        ld hl,txt_f_son
        call print_str
        ld a,3
        call TXT_SET_PEN
        ld a,'S'
        call TXT_OUTPUT
        ld a,(cur_son)
        add a,'1'
        call TXT_OUTPUT
        ld a,' '
        ld b,7
        call out_rep
sb_lock:
        ld hl,256*31+BRUSH_ROW
        call TXT_SET_CURSOR
        ld a,(inst_lock)
        or a
        jr z,sb_free
        ld bc,0*256+3           ; verrouillé : bleu sur orange
        call colors
        ld hl,txt_lock
        call print_str
        xor a
        jp TXT_SET_PAPER
sb_free:
        ld hl,txt_nolock
        jp print_str

; La note du pinceau suit la dernière note posée (A), selon la voix
set_brush:
        push af
        ld a,(cur_l)
        ld (dg_l),a
        call lane_is_noise
        pop bc                  ; B = la note
        ld a,b
        jr z,stb_noise
        ld (brush_note),a
        jp show_inst
stb_noise:
        ld (brush_noise),a
        jp show_inst

; --- Le panneau de la note (lignes 4 à 8) --------------------------------------------
; Le cadre (une fois, en dessinant l'écran)
draw_box:
        ld a,#FF                ; tout sera redessiné
        ld (title_shown),a
        ld (keys_shown),a
        ld (mode_shown),a
        ld (layers_shown),a
        ld l,BOX_TOP
        call box_line
        ld l,KEYS_ROW
db_side:
        push hl
        ld h,1
        call TXT_SET_CURSOR
        ld a,149                ; │
        call TXT_OUTPUT
        pop hl
        push hl
        ld h,40
        call TXT_SET_CURSOR
        ld a,149
        call TXT_OUTPUT
        pop hl
        inc l
        ld a,l
        cp BOX_BOT
        jr nz,db_side
        ld hl,256*1+BOX_BOT
        call TXT_SET_CURSOR
        ld a,147                ; └
        call TXT_OUTPUT
        ld a,CH_HOLD
        ld b,38
        call out_rep
        ld a,153                ; ┘
        jp TXT_OUTPUT

; Ligne du haut du cadre (ligne L)
box_line:
        ld h,1
        call TXT_SET_CURSOR
        ld bc,2*256+0
        call colors
        ld a,150                ; ┌
        call TXT_OUTPUT
        ld a,CH_HOLD
        ld b,38
        call out_rep
        ld a,156                ; ┐
        jp TXT_OUTPUT

draw_panel:
        ld a,(screen)
        or a
        ret nz
        call panel_title
        call snd_tick
        call draw_keys
        call snd_tick
        call draw_fields
        call is_layered
        ret z
        jp draw_layers

; Titre : « PAS 3 ─ VOIX B » (ou « ─ SON COMPOSE »), et « EDITION » quand TAB
; a fait passer le curseur dans le panneau.  Seulement s'il a changé.
panel_title:
        ld a,(cur_l)            ; clé : pas + 16 x voix + 64 x édition
        add a,a                 ;       + 128 x son composé
        add a,a
        add a,a
        add a,a
        ld hl,cur_s
        add a,(hl)
        ld b,a
        ld a,(grid_edit)
        or a
        jr z,pt_key
        ld a,64
        add a,b
        ld b,a
pt_key:
        call is_layered
        ld a,b
        jr z,pt_key2
        or 128
pt_key2:
        ld hl,title_shown
        cp (hl)
        ret z
        ld b,(hl)               ; B = ce qui était affiché
        ld (hl),a
        xor b
        and #C0                 ; même mode et même état d'édition : le titre
        jr nz,pt_border         ; a la même longueur, on ne réécrit que lui
        ld a,b
        inc a
        jr nz,pt_text           ; (#FF : rien n'était affiché)
pt_border:
        ld l,BOX_TOP
        call box_line
        call snd_tick
pt_text:
        ld hl,256*3+BOX_TOP
        call TXT_SET_CURSOR
        ld bc,1*256+0
        call colors
        ld hl,txt_t_step        ; " PAS "
        call print_str
        ld a,(cur_s)
        call print_hex1
        ld a,' '
        call TXT_OUTPUT
        ld a,CH_HOLD
        call TXT_OUTPUT
        ld a,' '
        call TXT_OUTPUT
        call is_layered
        jr nz,pt_son
        ld hl,txt_t_voice       ; "VOIX "
        call print_str
        ld a,(cur_l)
        ld e,a
        ld d,0
        ld hl,lane_letters
        add hl,de
        ld a,(hl)
        call TXT_OUTPUT
        ld a,' '
        call TXT_OUTPUT
        jr pt_edit
pt_son:
        ld hl,txt_comp
        call print_str
pt_edit:
        ld a,(grid_edit)
        or a
        ret z
        ld hl,256*29+BOX_TOP
        call TXT_SET_CURSOR
        ld bc,0*256+1           ; bleu sur jaune
        call colors
        ld hl,txt_t_edit        ; " EDITION "
        call print_str
        xor a
        jp TXT_SET_PAPER

; Index (0-23) de la note du curseur sur le clavier, ou #FF
key_highlight:
        ld a,#FF
        ld (dk_hl),a
        ld a,(cur_l)
        ld (dg_l),a
        call lane_is_noise
        ret z                   ; bruit : rien sur le clavier
        call cursor_ptr
        ld a,(hl)
        cp NOTE_OFF
        ret nc                  ; pas de note
        ld b,a
        ld a,(cur_oct)          ; 12 x octave de saisie
        ld c,a
        add a,a
        add a,c
        add a,a
        add a,a
        ld c,a
        ld a,b
        sub c
        ret c                   ; plus grave que le clavier
        cp 24
        ret nc                  ; plus aigu
        ld (dk_hl),a
        ret

; Clavier de 2 octaves : chaque blanche fait 2 colonnes, [lettre][│] ;
; la noire est un bloc plein posé sur le │, entre les deux blanches.
; Seulement si la note ou l'octave ont changé.
draw_keys:
        call key_highlight
        ld a,(cur_oct)
        add a,a
        add a,a
        add a,a
        add a,a
        add a,a                 ; clé : 32 x octave + note (ou 31)
        ld b,a
        ld a,(dk_hl)
        and 31
        or b
        ld hl,keys_shown
        cp (hl)
        ret z
        ld (hl),a
        ld hl,256*KEYS_COL+KEYS_ROW+1   ; ligne des blanches
        call TXT_SET_CURSOR
        xor a
dk_low:
        ld (dk_w),a
        call dk_white           ; A = demi-ton de la blanche, E = rang (0-6)
        ld hl,dk_hl
        cp (hl)
        ld a,2                  ; fond cyan,
        jr nz,dk_low_p
        ld a,1                  ;   jaune si c'est la note
dk_low_p:
        ld (dk_paper),a
        push de
        call TXT_SET_PAPER
        xor a
        call TXT_SET_PEN
        pop de
        ld hl,wk_letters
        add hl,de
        ld a,(hl)
        call TXT_OUTPUT
        ld a,(dk_w)
        cp 13
        jr z,dk_low_last
        ld a,2
        call TXT_SET_PAPER
        ld a,149                ; │
        jr dk_low_out
dk_low_last:
        ld a,' '
dk_low_out:
        call TXT_OUTPUT
        ld a,(dk_w)
        inc a
        cp 14
        jr nz,dk_low
        call snd_tick                   ; entre les deux lignes
        ld hl,256*KEYS_COL+KEYS_ROW     ; ligne des noires
        call TXT_SET_CURSOR
        xor a
dk_up:
        ld (dk_w),a
        call dk_white
        ld (dk_semi),a
        ld hl,dk_hl
        cp (hl)
        ld a,2
        jr nz,dk_up_p
        ld a,1
dk_up_p:
        ld (dk_paper),a
        push de
        call TXT_SET_PAPER
        pop de
        ld a,' '
        call TXT_OUTPUT
        ld hl,wk_black
        add hl,de
        ld a,(hl)
        or a
        jr z,dk_up_white
        ld a,(dk_semi)          ; une noire : jaune si c'est la note
        inc a
        ld hl,dk_hl
        cp (hl)
        ld a,0
        jr nz,dk_up_pen
        ld a,1
dk_up_pen:
        call TXT_SET_PEN
        ld a,2
        call TXT_SET_PAPER
        ld a,CH_FULL
        jr dk_up_out
dk_up_white:
        ld a,(dk_w)
        cp 13
        ld a,' '                ; dernière blanche : son fond
        jr z,dk_up_out
        xor a
        call TXT_SET_PEN
        ld a,2
        call TXT_SET_PAPER
        ld a,149
dk_up_out:
        call TXT_OUTPUT
        ld a,(dk_w)
        inc a
        cp 14
        jr nz,dk_up
        ld hl,256*(KEYS_COL+29)+KEYS_ROW        ; « OCT » et les 2 octaves
        call TXT_SET_CURSOR
        ld bc,2*256+0
        call colors
        ld hl,txt_k_oct
        call print_str
        ld hl,256*(KEYS_COL+29)+KEYS_ROW+1
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PEN
        ld a,(cur_oct)
        add a,'0'
        call TXT_OUTPUT
        ld a,'-'
        call TXT_OUTPUT
        ld a,(cur_oct)
        add a,'1'
        jp TXT_OUTPUT

; dk_w (0-13) -> A = demi-ton (0-23) de cette blanche, E = rang dans l'octave
dk_white:
        ld a,(dk_w)
        ld c,0
        cp 7
        jr c,dkw_low
        sub 7
        ld c,12
dkw_low:
        ld e,a
        ld d,0
        ld hl,wk_semis
        add hl,de
        ld a,(hl)
        add a,c
        ret

wk_semis:   db 0,2,4,5,7,9,11
wk_black:   db 1,1,0,1,1,1,0    ; une noire à droite de cette blanche
wk_letters: db "CDEFGAB"

; Ligne 7 : NOTE, INS (ou SON), VOL, FX de la case du curseur.  En mode
; édition (TAB), le champ choisi est en jaune inversé.
draw_fields:
        ld hl,256*3+PANEL_ROW
        call TXT_SET_CURSOR
        ld bc,2*256+0
        call colors
        ld hl,txt_f_note        ; "NOTE:"
        call print_str
        call cursor_ptr         ; (dg_l = voix du curseur)
        ld (df_cell),hl
        xor a
        call df_colors
        ld hl,(df_cell)
        ld a,(hl)
        cp NOTE_NONE
        jr z,df_empty
        cp NOTE_OFF
        jr z,df_off
        call lane_is_noise
        jr z,df_noise
        ld hl,(df_cell)
        ld a,(hl)
        call print_note
        ld a,' '
        ld b,2
        call out_rep
        jr df_ins
df_noise:
        ld a,'B'
        call TXT_OUTPUT
        ld a,'R'
        call TXT_OUTPUT
        ld hl,(df_cell)
        ld a,(hl)
        call print_hex2
        ld a,' '
        call TXT_OUTPUT
        jr df_ins
df_off:
        ld hl,txt_f_off         ; "ARRET"
        call print_str
        jr df_blank_rest
df_empty:
        ld hl,txt_f_none        ; "---  "
        call print_str
df_blank_rest:                  ; ni instrument, ni volume
        xor a
        call TXT_SET_PAPER
        ld a,' '
        ld b,27
        jp out_rep
df_ins:
        ld bc,2*256+0
        call colors
        ld a,' '
        call TXT_OUTPUT
        call is_layered
        ld hl,txt_f_ins
        jr z,df_ins_lab
        ld hl,txt_f_son
df_ins_lab:
        call print_str
        ld a,1
        call df_colors
        ld hl,(df_cell)
        inc hl
        ld a,(hl)
        ld (df_ins_n),a
        call is_layered
        jr nz,df_son
        ld a,(df_ins_n)
        call print_inst
        jr df_vol
df_son:
        ld a,'S'
        call TXT_OUTPUT
        ld a,(df_ins_n)
        add a,'1'
        call TXT_OUTPUT
        ld a,' '
        ld b,7
        call out_rep
df_vol:
        call snd_tick           ; au milieu de la ligne, un tour de son
        ld bc,2*256+0
        call colors
        ld a,' '
        call TXT_OUTPUT
        ld hl,txt_f_vol         ; "VOL:"
        call print_str
        ld a,2
        call df_colors
        ld hl,(df_cell)
        inc hl
        inc hl
        ld a,(hl)
        cp #FF
        jr z,df_vol_def
        call print_hex1
        jr df_fx
df_vol_def:
        ld a,'-'                ; volume de l'instrument
        call TXT_OUTPUT
df_fx:
        ld bc,2*256+0
        call colors
        ld a,' '
        call TXT_OUTPUT
        ld hl,txt_f_fx          ; "FX:"
        call print_str
        ld a,3
        call TXT_SET_PEN
        ld hl,(df_cell)
        inc hl
        inc hl
        inc hl
        ld a,(hl)
        or a
        jr z,df_fx_none
        call print_hex2
        jr dfd_end
df_fx_none:
        ld a,'-'
        call TXT_OUTPUT
        call TXT_OUTPUT
dfd_end:
        ld a,' '
        jp TXT_OUTPUT

; Couleurs du champ A (0 NOTE, 1 INS, 2 VOL) : jaune inversé s'il est choisi
; en mode édition, orange sinon
df_colors:
        ld b,a
        ld a,(grid_edit)
        or a
        jr z,dfc_normal
        ld a,(grid_field)
        cp b
        jr nz,dfc_normal
        ld bc,0*256+1
        jp colors
dfc_normal:
        ld bc,3*256+0
        jp colors

; --- Son composé : les 4 couches du son de la case (ou du son de saisie) -----------
draw_layers:
        call cursor_ptr
        ld a,(hl)
        cp NOTE_OFF
        ld a,(cur_son)
        jr nc,dly_son
        inc hl
        ld a,(hl)
dly_son:
        cp NB_SONS
        jr c,dly_ok
        xor a
dly_ok:
        ld hl,layers_shown
        cp (hl)
        ret z
        ld (hl),a
        ld (dly_n),a
        call snd_tick
        ld l,LAYER_ROW
        ld b,6
        call blank_rows
        ld hl,256*1+LAYER_ROW
        call TXT_SET_CURSOR
        ld bc,1*256+0
        call colors
        ld hl,txt_layers        ; "COUCHES DU SON S"
        call print_str
        ld a,(dly_n)
        add a,'1'
        call TXT_OUTPUT
        call snd_tick
        ld hl,256*1+LAYER_ROW+1
        call TXT_SET_CURSOR
        ld a,2
        call TXT_SET_PEN
        ld hl,txt_layers_head
        call print_str
        ld a,(dly_n)            ; HL = sons + 16 x numéro
        add a,a
        add a,a
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,sons
        add hl,de
        ld (dly_ptr),hl
        xor a
dly_voice:
        ld (dly_v),a
        add a,LAYER_ROW+2
        ld (dly_row),a
        ld l,a
        ld h,4
        call TXT_SET_CURSOR
        ld a,1
        call TXT_SET_PEN
        ld a,(dly_v)
        ld e,a
        ld d,0
        ld hl,lane_letters
        add hl,de
        ld a,(hl)
        call TXT_OUTPUT
        ld a,(dly_row)
        ld l,a
        ld h,9
        call TXT_SET_CURSOR
        ld a,3
        call TXT_SET_PEN
        ld hl,(dly_ptr)
        inc hl
        ld a,(hl)               ; instrument
        cp #FF
        jr nz,dly_used
        ld a,'-'                ; voix non utilisée par ce son
        call TXT_OUTPUT
        call TXT_OUTPUT
        jr dly_next
dly_used:
        call print_inst
        ld a,(dly_row)
        ld l,a
        ld h,21
        call TXT_SET_CURSOR
        ld hl,(dly_ptr)
        ld a,(hl)               ; décalage (ou période du bruit)
        ld c,a
        ld a,(dly_v)
        cp 3
        jr nz,dly_offset
        ld a,'B'
        call TXT_OUTPUT
        ld a,'R'
        call TXT_OUTPUT
        ld a,c
        call print_hex2
        jr dly_vol
dly_offset:
        ld a,c
        or a
        ld b,' '
        jr z,dly_sign
        ld b,'+'
        bit 7,a
        jr z,dly_sign
        neg
        ld b,'-'
dly_sign:
        ld c,a
        ld a,b
        call TXT_OUTPUT
        ld a,c
        call print_dec2
dly_vol:
        ld a,(dly_row)
        ld l,a
        ld h,29
        call TXT_SET_CURSOR
        ld hl,(dly_ptr)
        inc hl
        inc hl
        ld a,(hl)
        cp #FF
        jr z,dly_vol_def
        call print_hex1
        jr dly_next
dly_vol_def:
        ld a,'-'
        call TXT_OUTPUT
dly_next:
        call snd_tick
        ld hl,(dly_ptr)
        ld de,3
        add hl,de
        ld (dly_ptr),hl
        ld a,(dly_v)
        inc a
        cp 4
        jp nz,dly_voice
        ret

; --- Ecran entier ------------------------------------------------------------------
redraw_all:
        ld a,#FF                ; le repère du pas joué sera remis au prochain tour
        ld (shown_pos),a
        call show_pattern
        call show_state
        call snd_tick           ; la musique continue pendant le dessin : un
        call show_speed         ; tour au plus toutes les 20 ms environ, pour
        call draw_grid          ; qu'aucun pas ne soit en retard (mode
        call draw_panel         ; morceau : ce dessin suit le changement de
        call snd_tick           ; motif, juste avant le pas 0)
        call show_inst
        call snd_tick
        jp pickup_inst          ; l'instrument de saisie suit la note du curseur

; --- Touches propres à la grille ---------------------------------------------------
; ENTER : allume la case (le pinceau) ou l'éteint
cmd_toggle:
        call cursor_ptr
        ld a,(hl)
        cp NOTE_NONE
        jp nz,cmd_del           ; note ou arrêt : on vide
        push hl
        call lane_is_noise
        ld a,(brush_note)
        jr nz,ctg_note
        ld a,(brush_noise)
ctg_note:
        ld (en_note),a
        call inst_var           ; HL = instrument (ou son) de saisie
        ld a,(hl)
        ld (en_ins),a
        pop hl
        ld a,(en_note)
        ld (hl),a
        inc hl
        ld a,(en_ins)
        ld (hl),a
        inc hl
        ld (hl),#FF             ; volume de l'instrument
        inc hl
        ld (hl),0
        call draw_cursor_cell
        jp ce_listen

; COPY : la note et l'instrument de la case deviennent le pinceau
cmd_pick:
        call cursor_ptr
        ld a,(hl)
        cp NOTE_OFF
        ret nc                  ; pas de note ici
        push hl
        call set_brush
        pop hl
        inc hl
        ld c,(hl)
        call inst_var           ; HL = variable, B = nombre de valeurs
        ld a,c
        cp b
        ret nc
        ld (hl),a
        jp show_inst

; TAB : la grille <-> le panneau de la note
cmd_edit:
        ld a,(grid_edit)
        xor 1
        ld (grid_edit),a
        jp draw_panel

; Z si on est en mode édition, sans SHIFT ni CTRL (les flèches modifient
; alors le panneau)
edit_plain:
        ld a,(grid_edit)
        xor 1
        ret nz
        ld a,(mod_shift)
        ld hl,mod_ctrl
        or (hl)
        ret

edit_left:
        ld a,(grid_field)
        or a
        ret z
        dec a
        jr edit_field
edit_right:
        ld a,(grid_field)
        cp 2
        ret nc
        inc a
edit_field:
        ld (grid_field),a
        jp draw_fields

; Haut / bas en mode édition : la valeur du champ choisi
edit_up:
        call cursor_ptr
        ld a,(hl)
        cp NOTE_OFF
        ret nc                  ; pas de note : rien à modifier
        ld a,(grid_field)
        or a
        jr nz,eu_ins
        call lane_is_noise      ; note + 1 (période du bruit : jusqu'à 31)
        ld b,95
        jr nz,eu_note
        ld b,31
eu_note:
        call cursor_ptr
        ld a,(hl)
        cp b
        ret nc
        inc (hl)
        jr edit_done
eu_ins:
        dec a
        jr nz,eu_vol
        call inst_var           ; B = nombre d'instruments (ou de sons)
        call cursor_ptr
        inc hl
        ld a,(hl)
        inc a
        cp b
        ret nc
        ld (hl),a
        jr edit_done
eu_vol:
        call cursor_ptr
        inc hl
        inc hl
        ld a,(hl)
        cp 15
        ret z
        inc a                   ; "-" (#FF) -> 0, puis jusqu'à 15
        ld (hl),a
        jr edit_done

edit_down:
        call cursor_ptr
        ld a,(hl)
        cp NOTE_OFF
        ret nc
        ld a,(grid_field)
        or a
        jr nz,ed_ins
        call cursor_ptr
        ld a,(hl)
        or a
        ret z
        dec (hl)
        jr edit_done
ed_ins:
        dec a
        jr nz,ed_vol
        call cursor_ptr
        inc hl
        ld a,(hl)
        or a
        ret z
        dec (hl)
        jr edit_done
ed_vol:
        call cursor_ptr
        inc hl
        inc hl
        ld a,(hl)
        cp #FF
        ret z
        dec a                   ; 0 -> "-" (#FF)
        ld (hl),a
edit_done:
        call draw_cursor_cell
; Fait entendre brièvement la case du curseur
ce_listen:
        ld a,(seq_playing)
        or a
        ret nz
        call cursor_ptr
        ld a,(hl)
        ld (en_note),a
        inc hl
        ld a,(hl)
        ld (en_ins),a
        ld a,#FF
        ld (aud_key),a
        ld a,12                 ; un quart de seconde
        ld (aud_timer),a
        jp audition

; --- Textes --------------------------------------------------------------------
txt_t_step:      db " PAS ",0
txt_t_voice:     db "VOIX ",0
txt_t_edit:      db " EDITION ",0
txt_k_oct:       db "OCT",0
txt_f_note:      db "NOTE:",0
txt_f_ins:       db "INS:",0
txt_f_son:       db "SON:",0
txt_f_vol:       db "VOL:",0
txt_f_fx:        db "FX:",0
txt_f_off:       db "ARRET",0
txt_f_none:      db "---  ",0
txt_lock:        db "VERROU",0
txt_nolock:      db "      ",0
txt_layers:      db "COUCHES DU SON S",0
txt_layers_head: db "   VOIX INSTRUMENT  DECAL. VOL",0

; --- Variables -------------------------------------------------------------------
brush_note:   db 36             ; pinceau : note (DO 3),
brush_noise:  db 1              ;   période sur la voix de bruit
grid_edit:    db 0              ; 1 = TAB : les flèches modifient le panneau
grid_field:   db 0              ;   champ choisi (0 NOTE, 1 INS, 2 VOL)
dc_pen:       db 0
dc_tail:      db 0
mc_l:         db 0
mc_s:         db 0
title_shown:  db #FF            ; ce qui est déjà affiché (#FF : rien)
keys_shown:   db #FF
mode_shown:   db #FF
layers_shown: db #FF
dk_hl:        db #FF
dk_w:         db 0
dk_semi:      db 0
dk_paper:     db 0
df_cell:      dw 0
df_ins_n:     db 0
dly_n:        db 0
dly_v:        db 0
dly_row:      db 0
dly_ptr:      dw 0
