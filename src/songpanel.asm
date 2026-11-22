; ============================================================================
; SEQ-16 - Panneau SONG : l'enchaînement des motifs (lot 4 du plan)
;
; Le morceau garde jusqu'à 64 positions (bloc v3, voir song.asm) :
;   motif (0-31), répétitions (1-16), transposition (-12 à +12 demi-tons,
;   sur les voix A, B, C ; le bruit ne bouge pas), et une position de
;   boucle : à la fin, la lecture y revient.
;
; Écran (lignes) :
;   2      nom du morceau, tempo, état
;   4      titres des colonnes
;   5-18   les positions (14 visibles, la liste défile), puis « FIN »
;          POS ►/↑ MOTIF NOM REP TR. APERCU (un ■ par pas qui a une note)
;   20     mixage : volume des voix A, B, C, N
;   21     durée (mesures, minutes) et nombre de positions
;   22-24  aide ; 25 : messages
;
; Touches : ↑↓ position (sous FIN : le mixage), ←→ champ (ou voix du
; mixage), SHIFT ↑↓ valeur, ENTER insérer, DEL ôter, COPY doubler, B la
; boucle part d'ici, ESPACE lit le morceau depuis le curseur.
; ============================================================================

SONG_POS_MAX equ 64
SP_ROW0      equ 5
SP_ROWS      equ 14
SP_MIX_ROW   equ 20
SP_DUR_ROW   equ 21

; HL = la position A
song_pos_ptr:
        ld l,a
        ld h,0
        ld e,l
        ld d,h
        add hl,hl
        add hl,de               ; 3 octets par position
        ld de,song_list
        add hl,de
        ret

; HL = le nom (8 caractères) du motif A
pat_name_ptr:
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,pat_names
        add hl,de
        ret

; --- Lecture du morceau ------------------------------------------------------------
; Fin d'une mesure, en mode morceau (appelé par seq_frame) : on rejoue le
; motif, ou on passe à la position suivante (la boucle à la fin).
; Panneau MOTIF : le motif affiché boucle, le morceau n'avance pas (on
; change de motif soi-même, CTRL flèches) ; il reprend au retour dans SONG.
song_bar:
        ld a,(song_live)
        or a
        ret z
        ld a,(screen)
        or a
        ret z                   ; MOTIF : le motif en cours boucle
        ld hl,song_rep
        dec (hl)
        ret nz                  ; encore une fois
        ld a,(song_pos)
        inc a
        ld hl,song_len
        cp (hl)
        jr c,song_goto
        ld a,(song_loop)        ; fin du morceau : retour à la boucle
        ; continue dans song_goto

; La lecture passe à la position A : son motif (celui qu'on quitte retourne
; dans le bloc 4), ses répétitions, sa transposition.  Ne dessine rien :
; song_changed demande à la boucle principale de mettre l'écran à jour.
song_goto:
        ld (song_pos),a
        call song_pos_ptr
        ld a,(hl)               ; motif
        inc hl
        ld c,(hl)               ; répétitions
        inc hl
        ld b,(hl)               ; transposition
        ld (song_rep),bc        ; C -> song_rep, B -> song_transp
        ld hl,cur_pat
        cp (hl)
        jr z,sg_same
        ld b,a
        ld a,(pat_dirty)        ; le motif quitté n'est rangé dans le bloc 4
        or a                    ; que s'il a été modifié
        jr z,sg_clean
        push bc
        call pat_store
        pop bc
sg_clean:
        ld a,b
        ld (cur_pat),a
        ld hl,next_id           ; déjà préparé dans pat_ahead ?
        cp (hl)
        jr nz,sg_fetch
        ld hl,pat_ahead         ; oui : une simple copie en mémoire principale
        ld de,pat_work          ; (pas de bloc, interruptions permises)
        ld bc,PAT_SIZE
        ldir
        xor a
        ld (pat_dirty),a
        ld hl,pat_work
        jr sg_set
sg_fetch:
        call pat_fetch          ; non : depuis le bloc 4
sg_set:
        ld a,#FF
        ld (next_id),a
        call seq_set_pattern    ; son tempo
        ld hl,(seq_pattern)     ; son composé : une seule voix
        ld a,(hl)
        or a
        jr z,sg_same
        xor a
        ld (cur_l),a
sg_same:
        ld a,1
        ld (song_changed),a
        ret

; Boucle principale : pendant la dernière répétition d'une position, le
; motif de la position suivante est copié du bloc 4 dans pat_ahead.  Au
; changement de mesure, song_goto n'a plus qu'à le recopier dans pat_work.
song_prefetch:
        ld a,(song_live)
        or a
        ret z
        ld a,(screen)           ; MOTIF : le morceau n'avance pas
        or a
        ret z
        ld a,(song_rep)
        dec a
        ret nz                  ; pas encore la dernière répétition
        ld a,(song_pos)         ; position suivante (la boucle à la fin)
        inc a
        ld hl,song_len
        cp (hl)
        jr c,spf_pos
        ld a,(song_loop)
spf_pos:
        call song_pos_ptr
        ld a,(hl)               ; son motif
        ld hl,cur_pat
        cp (hl)
        ret z                   ; le même : rien à copier
        ld hl,next_id
        cp (hl)
        ret z                   ; déjà prêt
        ld (hl),a
        call pat_addr
        ld de,pat_ahead
        ld bc,PAT_SIZE
        ld a,RAM_SONG
        jp bank_copy

; B = note -> B + transposition du morceau (bornée de 0 à 95).  Garde C.
song_trans_b:
        ld a,(song_transp)
        or a
        ret z
        jp m,stb_down
        add a,b
        cp 96
        jr c,stb_set
        ld a,95
        jr stb_set
stb_down:
        add a,b
        jr c,stb_set
        xor a
stb_set:
        ld b,a
        ret

; Boucle principale : la lecture a changé de position
song_follow:
        xor a
        ld (song_changed),a
        ld a,(screen)
        or a
        jp z,redraw_all         ; MOTIF suit le motif joué
        cp 4
        ret nz
        call sp_status
        jp sp_show_pos

; --- Morceau par défaut ----------------------------------------------------------
; Une position par motif qui a au moins une note (morceaux d'usine et
; anciens .SNG, sans bloc v3), noms vides
song_default:
        xor a
        ld (song_len),a
        ld (song_loop),a
        ld hl,pat_names
        ld bc,NB_PAT*8
sd_clear:
        ld (hl),' '
        inc hl
        dec bc
        ld a,b
        or c
        jr nz,sd_clear
        ld c,0
sd_loop:
        push bc
        ld a,c
        call pat_addr           ; le motif, du bloc 4 vers io_buffer
        ld de,io_buffer
        ld bc,PAT_SIZE
        ld a,RAM_SONG
        call bank_copy
        call pat_used
        pop bc
        jr z,sd_next
        ld a,(song_len)
        call song_pos_ptr
        ld (hl),c
        inc hl
        ld (hl),1
        inc hl
        ld (hl),0
        ld hl,song_len
        inc (hl)
sd_next:
        inc c
        ld a,c
        cp NB_PAT
        jr nz,sd_loop
        ld a,(song_len)
        or a
        ret nz
        ld hl,song_list         ; aucune note : le motif 1, une fois
        ld (hl),0
        inc hl
        ld (hl),1
        inc hl
        ld (hl),0
        ld a,1
        ld (song_len),a
        ret

; NZ si le motif rangé dans io_buffer a au moins une note
pat_used:
        ld hl,io_buffer+PAT_HEADER
        ld de,4
        ld b,64
pu_loop:
        ld a,(hl)
        cp NOTE_OFF
        jr c,pu_yes
        add hl,de
        djnz pu_loop
        xor a
        ret
pu_yes:
        ld a,1
        or a
        ret

; Remet dans les bornes un bloc v3 relu sur la disquette
song_sanitize:
        ld a,(song_len)
        cp SONG_POS_MAX+1
        jr c,ss_len
        ld a,SONG_POS_MAX
        ld (song_len),a
ss_len:
        ld b,a
        ld a,(song_loop)
        cp b
        jr c,ss_loop
        xor a
        ld (song_loop),a
ss_loop:
        ld a,b
        or a
        jp z,song_default       ; aucune position : on en refait
        ld hl,song_list
ss_pos:
        ld a,(hl)
        and NB_PAT-1
        ld (hl),a
        inc hl
        ld a,(hl)               ; répétitions : 1 à 16
        or a
        jr nz,ss_rep1
        inc a
ss_rep1:
        cp 17
        jr c,ss_rep2
        ld a,16
ss_rep2:
        ld (hl),a
        inc hl
        ld a,(hl)               ; transposition : -12 à +12
        add a,12
        cp 25
        jr c,ss_tr
        ld (hl),0
ss_tr:
        inc hl
        djnz ss_pos
        ret

; --- Dessin du panneau -----------------------------------------------------------
ds_song:
        ld hl,song_text
        call print_list
        ld a,#FF
        ld (sp_shown_pos),a
        call sp_status
        call sp_draw_list
        call sp_draw_mixer
        jp sp_draw_duration

; Ligne 2 : nom, tempo, état
sp_status:
        ld hl,256*6+2
        call TXT_SET_CURSOR
        ld bc,3*256+0
        call colors
        ld hl,fname
        ld b,NAME_LEN
        call print_n
        ld hl,256*20+2
        call TXT_SET_CURSOR
        ld a,(seq_bpm)
        call print_dec3
        ld hl,256*25+2
        call TXT_SET_CURSOR
        ld a,(seq_playing)
        or a
        jr z,sps_stop
        ld a,1
        call TXT_SET_PEN
        ld a,246                ; ►
        call TXT_OUTPUT
        ld a,(song_live)
        or a
        ld hl,txt_sp_song
        jp nz,print_str
        ld hl,txt_sp_pat
        jp print_str
sps_stop:
        ld a,2
        call TXT_SET_PEN
        ld a,CH_ON
        call TXT_OUTPUT
        ld hl,txt_sp_stop
        jp print_str

; Les 14 lignes visibles
sp_draw_list:
        ld a,(sp_top)
        ld b,SP_ROWS
spl_list_loop:
        push af
        push bc
        call sp_draw_row
        call snd_tick
        pop bc
        pop af
        inc a
        djnz spl_list_loop
        ret

; Ligne de la position A (si elle est visible)
sp_draw_row:
        ld (spr_i),a
        ld hl,sp_top
        sub (hl)
        ret c
        cp SP_ROWS
        ret nc
        add a,SP_ROW0
        ld l,a
        ld h,1
        call TXT_SET_CURSOR
        xor a
        call TXT_SET_PAPER
        ld a,(spr_i)
        ld hl,song_len
        cp (hl)
        jr c,spr_pos
        jr z,spr_fin
        ld a,' '                ; après FIN : vide
        ld b,40
        jp out_rep
spr_fin:
        ld a,2
        call TXT_SET_PEN
        ld a,(spr_i)
        call print_dec2
        ld a,' '
        ld b,2
        call out_rep
        call spr_cursor         ; Z : le curseur est sur FIN
        ld bc,2*256+0
        jr nz,spr_fin_c
        ld bc,0*256+1
spr_fin_c:
        call colors
        ld hl,txt_sp_end        ; "-- FIN : RETOUR EN "
        call print_str
        ld a,(song_loop)
        call print_dec2
        ld hl,txt_sp_end2       ; " --"
        call print_str
        xor a
        call TXT_SET_PAPER
        ld a,' '
        ld b,12
        jp out_rep

spr_pos:
        ld a,2                  ; numéro de la position
        call TXT_SET_PEN
        ld a,(spr_i)
        call print_dec2
        call spr_marker
        ld a,' '
        call TXT_OUTPUT
        ld a,(spr_i)
        call song_pos_ptr
        ld (spr_ptr),hl
        xor a                   ; champ 0 : motif et nom
        call spr_colors
        ld hl,(spr_ptr)
        ld a,(hl)
        ld (spr_pat),a
        inc a
        call print_dec2
        ld a,' '
        call TXT_OUTPUT
        ld a,(spr_pat)
        call pat_name_ptr
        ld b,8
spr_name:
        ld a,(hl)
        cp ' '
        jr nc,spr_name_c
        ld a,' '
spr_name_c:
        call TXT_OUTPUT
        inc hl
        djnz spr_name
        call spr_gap
        ld a,1                  ; champ 1 : répétitions
        call spr_colors
        ld a,'x'
        call TXT_OUTPUT
        ld hl,(spr_ptr)
        inc hl
        ld a,(hl)
        call print_small        ; 1 ou 2 chiffres, complété à 2
        call spr_gap
        ld a,2                  ; champ 2 : transposition
        call spr_colors
        ld hl,(spr_ptr)
        inc hl
        inc hl
        ld a,(hl)
        or a
        ld b,' '
        jr z,spr_sign
        ld b,'+'
        jp p,spr_sign
        neg
        ld b,'-'
spr_sign:
        ld c,a
        ld a,b
        call TXT_OUTPUT
        ld a,c
        call print_small
        call spr_gap
        jp spr_preview

; Marqueur après le numéro : ► position jouée, ↑ départ de la boucle
spr_marker:
        ld a,(spr_i)
        ld hl,sp_shown_pos
        cp (hl)
        jr nz,spm_loop
        ld a,3
        call TXT_SET_PEN
        ld a,246
        jp TXT_OUTPUT
spm_loop:
        ld hl,song_loop
        cp (hl)
        ld a,' '
        jp nz,TXT_OUTPUT
        ld a,1
        call TXT_SET_PEN
        ld a,240                ; ↑
        jp TXT_OUTPUT

; Un espace sur fond bleu
spr_gap:
        xor a
        call TXT_SET_PAPER
        ld a,' '
        jp TXT_OUTPUT

; Z si la ligne spr_i porte le curseur
spr_cursor:
        ld a,(sp_mix)
        or a
        ret nz
        ld a,(spr_i)
        ld hl,sp_cur
        cp (hl)
        ret

; Couleurs du champ A de la ligne : orange ; sur la ligne du curseur, jaune,
; et le champ choisi en jaune inversé
spr_colors:
        ld c,a
        call spr_cursor
        ld b,3
        jr nz,spc_set0
        ld a,(sp_field)
        cp c
        ld b,1
        jr nz,spc_set0
        ld bc,0*256+1
        jp colors
spc_set0:
        ld c,0
        jp colors

; A (0-99) : 1 ou 2 chiffres, puis un espace si un seul
print_small:
        cp 10
        jr nc,ps_two
        add a,'0'
        call TXT_OUTPUT
        ld a,' '
        jp TXT_OUTPUT
ps_two:
        jp print_dec2

; Aperçu : un ■ par pas qui a au moins une note (16 colonnes)
spr_preview:
        ld a,(spr_pat)
        ld hl,cur_pat
        cp (hl)
        ld hl,pat_work          ; le motif affiché : sa version de travail
        jr z,spv_src
        call pat_addr
        ld de,io_buffer
        ld bc,PAT_SIZE
        ld a,RAM_SONG
        call bank_copy
        ld hl,io_buffer
spv_src:
        ld a,(hl)
        ld (spv_mode),a         ; son composé : seule la 1re voix compte
        ld de,PAT_HEADER
        add hl,de
        ld (spv_ptr),hl
        xor a
spv_step:
        ld (spv_s),a
        ld hl,(spv_ptr)
        ld b,4
        ld a,(spv_mode)
        or a
        jr z,spv_cells
        ld b,1
spv_cells:
        ld a,(hl)
        cp NOTE_OFF
        jr c,spv_on
        inc hl
        inc hl
        inc hl
        inc hl
        djnz spv_cells
        ld a,(spv_s)            ; rien : point jaune sur les temps
        and 3
        ld a,1
        jr z,spv_dot
        ld a,2
spv_dot:
        call TXT_SET_PEN
        ld a,CH_DOT
        jr spv_out
spv_on:
        ld a,2
        call TXT_SET_PEN
        ld a,CH_ON
spv_out:
        call TXT_OUTPUT
        ld hl,(spv_ptr)
        ld de,16
        add hl,de
        ld (spv_ptr),hl
        ld a,(spv_s)
        inc a
        cp 16
        jr nz,spv_step
        ret

; Position jouée : redessine l'ancienne et la nouvelle ligne
sp_show_pos:
        ld a,(seq_playing)
        or a
        ld a,#FF
        jr z,ssp_new
        ld a,(song_live)
        or a
        ld a,#FF
        jr z,ssp_new
        ld a,(song_pos)
ssp_new:
        ld hl,sp_shown_pos
        cp (hl)
        ret z
        ld b,(hl)
        ld (hl),a
        push af
        ld a,b
        cp #FF
        call nz,sp_draw_row
        call snd_tick           ; la musique continue entre les deux lignes
        pop af
        cp #FF
        ret z
        jp sp_draw_row

; Ligne 20 : le mixage (volume général de chaque voix)
sp_draw_mixer:
        xor a
sdm_voice:
        ld (sdm_v),a
        add a,a
        add a,a
        add a,a
        add a,9                 ; colonne 9 + 8 x voix
        ld h,a
        ld l,SP_MIX_ROW
        call TXT_SET_CURSOR
        ld a,(sp_mix)           ; voix choisie : en inverse
        or a
        jr z,sdm_normal
        ld a,(sdm_v)
        ld hl,sp_voice
        cp (hl)
        jr nz,sdm_normal
        ld bc,0*256+1
        jr sdm_col
sdm_normal:
        ld bc,1*256+0
sdm_col:
        call colors
        ld a,(sdm_v)
        ld e,a
        ld d,0
        ld hl,lane_letters
        add hl,de
        ld a,(hl)
        call TXT_OUTPUT
        ld bc,3*256+0
        call colors
        ld a,' '
        call TXT_OUTPUT
        ld a,(sdm_v)
        ld e,a
        ld d,0
        ld hl,snd_master
        add hl,de
        ld a,(hl)
        ld (sdm_vol),a
        call print_hex1
        ld a,' '
        call TXT_OUTPUT
        ld a,(sdm_vol)          ; barre : (volume x 3 + 7) / 15 blocs
        ld c,a
        add a,a
        add a,c
        add a,7
        ld c,0
sdm_div:
        sub 15
        jr c,sdm_bar
        inc c
        jr sdm_div
sdm_bar:
        ld a,2
        call TXT_SET_PEN
        ld b,3                  ; 3 blocs, puis un espace avant la voix suivante
sdm_block:
        ld a,c
        or a
        ld a,' '
        jr z,sdm_put
        dec c
        ld a,CH_FULL
sdm_put:
        call TXT_OUTPUT
        djnz sdm_block
        ld a,' '
        call TXT_OUTPUT
        ld a,(sdm_v)
        inc a
        cp 4
        jp nz,sdm_voice
        ret

; Ligne 21 : durée et nombre de positions.  Chaque motif garde son tempo :
; une mesure (16 pas) dure 12000 / BPM images.
sp_draw_duration:
        ld hl,0
        ld (dur_bars),hl
        ld (dur_frames),hl
        xor a
        ld (dur_frames+2),a
        ld a,(song_len)
        or a
        jr z,sdd_show
        xor a
sdd_pos:
        ld (sdd_i),a
        call song_pos_ptr
        ld a,(hl)               ; motif
        inc hl
        ld c,(hl)               ; répétitions
        ld b,0
        push bc
        ld hl,(dur_bars)
        add hl,bc
        ld (dur_bars),hl
        call pattern_bpm            ; A = tempo du motif
        ld c,a
        ld hl,12000
        call div16_8            ; HL = images par mesure
        pop bc                  ; C = répétitions
sdd_mul:
        push hl
        ld de,(dur_frames)
        add hl,de
        ld (dur_frames),hl
        jr nc,sdd_nc
        ld hl,dur_frames+2
        inc (hl)
sdd_nc:
        pop hl
        dec c
        jr nz,sdd_mul
        ld a,(sdd_i)
        inc a
        ld hl,song_len
        cp (hl)
        jr nz,sdd_pos
sdd_show:
        ld hl,256*7+SP_DUR_ROW
        call TXT_SET_CURSOR
        ld bc,3*256+0
        call colors
        ld hl,(dur_bars)
        call print_dec16
        ld a,' '
        call TXT_OUTPUT
        ld a,2
        call TXT_SET_PEN
        ld hl,txt_sp_bars       ; "MESURES"
        call print_str
        ld a,' '
        call TXT_OUTPUT
        ld a,3
        call TXT_SET_PEN
        ld hl,(dur_frames)      ; secondes = images / 50
        ld a,(dur_frames+2)
        ld e,a
        ld c,50
        call div24_8
        ld c,60                 ; minutes et secondes
        call div16_8
        push af
        call print_dec16
        ld a,':'
        call TXT_OUTPUT
        pop af
        call print_dec2
        ld a,' '
        ld b,4
        call out_rep
        ld hl,256*36+SP_DUR_ROW
        call TXT_SET_CURSOR
        ld a,(song_len)
        call print_dec2
        ld a,'/'
        call TXT_OUTPUT
        ld a,SONG_POS_MAX
        jp print_dec2

; A = tempo du motif A (celui du bloc 4, ou de pat_work pour le motif affiché)
pattern_bpm:
        ld hl,cur_pat
        cp (hl)
        jr nz,pb_bank
        ld a,(pat_work+PAT_BPM)
        jr pb_check
pb_bank:
        call pat_addr
        ld de,io_buffer
        ld bc,2
        ld a,RAM_SONG
        call bank_copy
        ld a,(io_buffer+PAT_BPM)
pb_check:
        cp 40                   ; (un tempo nul ne doit pas diviser)
        ret nc
        ld a,40
        ret

; HL = HL / C, A = reste
div16_8:
        xor a
        ld b,16
d168_loop:
        add hl,hl
        rla
        jr c,d168_sub
        cp c
        jr c,d168_next
d168_sub:
        sub c
        inc l
d168_next:
        djnz d168_loop
        ret

; E:HL = E:HL / C, A = reste
div24_8:
        xor a
        ld b,24
d248_loop:
        add hl,hl
        rl e
        rla
        jr c,d248_sub
        cp c
        jr c,d248_next
d248_sub:
        sub c
        inc l
d248_next:
        djnz d248_loop
        ret

; HL en décimal, sans zéros devant
print_dec16:
        ld de,10000
        ld b,0                  ; B = 1 dès le premier chiffre écrit
        call pd16_digit
        ld de,1000
        call pd16_digit
        ld de,100
        call pd16_digit
        ld de,10
        call pd16_digit
        ld a,l
        add a,'0'
        jp TXT_OUTPUT
pd16_digit:
        ld a,'0'-1
pd16_sub:
        inc a
        or a
        sbc hl,de
        jr nc,pd16_sub
        add hl,de
        cp '0'
        jr nz,pd16_out
        inc b
        dec b
        ret z                   ; zéro devant : rien
pd16_out:
        ld b,1
        jp TXT_OUTPUT

; --- Touches -------------------------------------------------------------------------
song_cmd:
        ld a,(rc_index)
        or a
        jp z,song_play          ; ESPACE
        cp 2
        jp z,song_del           ; DEL
        cp 6
        jp z,sp_left
        cp 7
        jp z,sp_right
        cp 8
        jp z,sp_up
        cp 9
        jp z,sp_down
        cp 11
        jp z,song_insert        ; ENTER
        cp 17
        jp z,song_dup           ; COPY
        cp 25
        jp z,song_set_loop      ; B
        ret

; ESPACE : lit le morceau depuis la position du curseur, ou arrête
song_play:
        ld a,(seq_playing)
        or a
        jr z,spl_start
        call seq_stop
        jr spl_show
spl_start:
        ld a,(song_len)
        or a
        ret z
        ld a,(sp_cur)
        ld hl,song_len
        cp (hl)
        jr c,spl_pos
        xor a                   ; sur FIN ou le mixage : depuis le début
spl_pos:
        ld b,a
        ld a,1
        ld (song_live),a
        ld a,b
        call song_goto
        call seq_start
spl_show:
        xor a
        ld (song_changed),a
        call sp_status
        jp sp_show_pos

sp_up:
        ld a,(mod_shift)
        or a
        ld a,1
        jp nz,sp_value
        ld a,(sp_mix)
        or a
        jr z,spu_list
        xor a                   ; du mixage à la ligne FIN
        ld (sp_mix),a
        call sp_draw_mixer
        ld a,(song_len)
        ld (sp_cur),a
        jr sp_moved
spu_list:
        ld a,(sp_cur)
        or a
        ret z
        ld b,a
        dec a
        ld (sp_cur),a
        ld a,b
        jr sp_moved_from

sp_down:
        ld a,(mod_shift)
        or a
        ld a,-1
        jp nz,sp_value
        ld a,(sp_mix)
        or a
        ret nz
        ld a,(sp_cur)
        ld hl,song_len
        cp (hl)
        jr c,spd_next
        ld a,1                  ; sous FIN : le mixage
        ld (sp_mix),a
        ld a,(sp_cur)
        call sp_draw_row
        jp sp_draw_mixer
spd_next:
        ld b,a
        inc a
        ld (sp_cur),a
        ld a,b
        jr sp_moved_from

; Le curseur a quitté la ligne A : on la redessine, puis la nouvelle (toute
; la liste si elle défile)
sp_moved_from:
        push af
        call sp_scroll
        pop bc
        jr nz,sp_moved          ; la liste a défilé
        ld a,b
        call sp_draw_row
        ld a,(sp_cur)
        jp sp_draw_row
sp_moved:
        call sp_scroll
        jp sp_draw_list

; Garde le curseur dans les 14 lignes visibles.  NZ si la liste a défilé.
sp_scroll:
        ld a,(sp_cur)
        ld hl,sp_top
        cp (hl)
        jr c,ssc_set            ; au-dessus : il devient la 1re ligne
        sub SP_ROWS-1
        jr c,ssc_same
        cp (hl)
        jr c,ssc_same
        jr z,ssc_same
ssc_set:
        ld (hl),a
        or 1                    ; NZ
        ret
ssc_same:
        xor a
        ret

sp_left:
        ld a,(sp_mix)
        or a
        jr nz,spl_mix
        ld a,(sp_field)
        or a
        ret z
        dec a
        jr sp_field_set
spl_mix:
        ld a,(sp_voice)
        or a
        ret z
        dec a
        ld (sp_voice),a
        jp sp_draw_mixer
sp_right:
        ld a,(sp_mix)
        or a
        jr nz,spr_mix
        ld a,(sp_field)
        cp 2
        ret nc
        inc a
sp_field_set:
        ld (sp_field),a
        ld a,(sp_cur)
        jp sp_draw_row
spr_mix:
        ld a,(sp_voice)
        cp 3
        ret nc
        inc a
        ld (sp_voice),a
        jp sp_draw_mixer

; SHIFT ↑↓ : A = +1 ou -1 sur le champ choisi (ou le volume)
sp_value:
        ld (spv_dir),a
        ld a,(sp_mix)
        or a
        jr z,svl_pos
        ld a,(sp_voice)
        ld e,a
        ld d,0
        ld hl,snd_master
        add hl,de
        ld a,(spv_dir)
        add a,(hl)
        cp 16
        ret nc                  ; (0 - 1 = 255 : refusé aussi)
        ld (hl),a
        jp sp_draw_mixer
svl_pos:
        ld a,(sp_cur)
        ld hl,song_len
        cp (hl)
        ret nc                  ; FIN : rien à changer
        call song_pos_ptr
        ld a,(sp_field)
        ld e,a
        ld d,0
        add hl,de
        ld a,(spv_dir)
        add a,(hl)
        ld b,a
        ld a,(sp_field)
        or a
        jr nz,svl_rep
        ld a,b                  ; motif : 0 à 31
        cp NB_PAT
        ret nc
        jr svl_set
svl_rep:
        dec a
        jr nz,svl_tr
        ld a,b                  ; répétitions : 1 à 16
        or a
        ret z
        cp 17
        ret nc
        jr svl_set
svl_tr:
        ld a,b                  ; transposition : -12 à +12
        add a,12
        cp 25
        ret nc
        ld a,b
svl_set:
        ld (hl),a
        ld a,(sp_cur)
        call sp_draw_row
        jp sp_draw_duration

; ENTER : insère une position au curseur (une copie de celle du curseur ;
; sur FIN : le motif affiché, ajouté à la fin)
song_insert:
        ld a,(sp_cur)
        ld hl,song_len
        cp (hl)
        jr c,si_copy
        ld a,(cur_pat)          ; FIN : on ajoute le motif affiché
        ld (si_new),a
        ld a,1
        ld (si_new+1),a
        xor a
        ld (si_new+2),a
        ld a,(sp_cur)
        call song_insert_at
        ret nc
        ld hl,sp_cur            ; le curseur reste sur FIN
        inc (hl)
        jp song_redraw
si_copy:
        call si_take            ; la position du curseur
        ld a,(sp_cur)
        call song_insert_at
        ret nc
        jp song_redraw

; COPY : double la position du curseur (la copie vient juste après)
song_dup:
        ld a,(sp_cur)
        ld hl,song_len
        cp (hl)
        ret nc
        call si_take
        ld a,(sp_cur)
        inc a
        call song_insert_at
        ret nc
        ld hl,sp_cur
        inc (hl)
        jp song_redraw

; si_new <- la position du curseur
si_take:
        ld a,(sp_cur)
        call song_pos_ptr
        ld de,si_new
        ld bc,3
        ldir
        ret

; Insère si_new en position A.  -> Carry = 1 si c'est fait (64 au plus)
song_insert_at:
        ld c,a
        ld a,(song_len)
        cp SONG_POS_MAX
        jr c,sia_room
        ld hl,txt_sp_full
        call dsk_message
        or a
        ret
sia_room:
        ld b,a                  ; B = ancienne longueur
        ld a,(song_loop)        ; la boucle garde sa position
        cp c
        jr c,sia_loop
        ld a,b
        or a
        jr z,sia_loop           ; (morceau vide : la boucle reste à 0)
        ld hl,song_loop
        inc (hl)
sia_loop:
        ld a,b                  ; on décale les positions C .. fin
        sub c
        jr z,sia_put
        push bc
        ld l,a                  ; nombre d'octets = 3 x (longueur - C)
        ld h,0
        ld e,l
        ld d,h
        add hl,hl
        add hl,de
        push hl
        ld a,b                  ; dernière position + 3 octets
        call song_pos_ptr
        dec hl                  ; HL = dernier octet utilisé
        ld d,h
        ld e,l
        inc de
        inc de
        inc de
        pop bc
        lddr
        pop bc
sia_put:
        ld a,c
        call song_pos_ptr
        ex de,hl
        ld hl,si_new
        ld bc,3
        ldir
        ld hl,song_len
        inc (hl)
        scf
        ret

; DEL : ôte la position du curseur
song_del:
        ld a,(sp_cur)
        ld hl,song_len
        cp (hl)
        ret nc
        ld c,a
        ld a,(hl)
        dec a
        ld (hl),a
        sub c                   ; positions qui remontent
        jr z,sdl_loopfix
        ld l,a
        ld h,0
        ld e,l
        ld d,h
        add hl,hl
        add hl,de
        push hl
        ld a,c
        call song_pos_ptr
        ld d,h
        ld e,l
        inc hl
        inc hl
        inc hl
        pop bc
        ldir
sdl_loopfix:
        ld a,(sp_cur)           ; la boucle : une position plus haut si elle
        ld c,a                  ; était après, et jamais au-delà de la fin
        ld hl,song_loop
        ld a,(hl)
        cp c
        jr c,sdl_lf2
        jr z,sdl_lf2
        dec (hl)
sdl_lf2:
        ld a,(song_len)
        or a
        jr z,sdl_lf3
        dec a
        cp (hl)
        jp nc,song_redraw
sdl_lf3:
        ld (hl),a
        ; continue dans song_redraw

song_redraw:
        call sp_scroll
        call sp_draw_list
        jp sp_draw_duration

; B : la boucle part de la position du curseur
song_set_loop:
        ld a,(sp_cur)
        ld hl,song_len
        cp (hl)
        ret nc
        ld (song_loop),a
        call sp_draw_list
        ld a,(song_len)         ; et la ligne FIN (« retour en »)
        jp sp_draw_row

; --- Textes ------------------------------------------------------------------
song_text:
        db 1,2,2,0,  "SONG:",0
        db 16,2,2,0, "BPM:",0
        db 1,4,2,0,  "POS MOTIF       REP TR. APERCU",0
        db 1,SP_MIX_ROW,1,0, "MIXAGE",0
        db 1,SP_DUR_ROW,2,0, "DUREE",0
        db 26,SP_DUR_ROW,2,0,"POSITIONS",0
        db 1,22,3,0, 240,241,0
        db 4,22,2,0, "POSITION",0
        db 14,22,3,0,242,243,0
        db 17,22,2,0,"CHAMP",0
        db 24,22,3,0,"SHIFT",240,241,0
        db 32,22,2,0,"VALEUR",0
        db 1,23,3,0, "ENTER",0
        db 7,23,2,0, "INSERER",0
        db 16,23,3,0,"DEL",0
        db 20,23,2,0,"OTER",0
        db 26,23,3,0,"COPY",0
        db 31,23,2,0,"DOUBLER",0
        db 1,24,3,0, "B",0
        db 3,24,2,0, "BOUCLE",0
        db 11,24,3,0,"ESPACE",0
        db 18,24,2,0,"LIRE",0
        db 24,24,3,0,"f8 f9",0
        db 30,24,2,0,"DISQUE",0
        db #FF

txt_sp_song:  db "LECTURE SONG ",0
txt_sp_pat:   db "LECTURE MOTIF",0
txt_sp_stop:  db "ARRET        ",0
txt_sp_end:   db "-- FIN : RETOUR EN ",0
txt_sp_end2:  db " --",0
txt_sp_bars:  db "MESURES",0
txt_sp_full:  db "64 POSITIONS AU PLUS",0

; --- Variables -------------------------------------------------------------------
song_live:    db 0              ; 1 = lecture du morceau (0 : le motif en boucle)
song_pos:     db 0              ;   position jouée,
song_rep:     db 0              ;   répétitions qui restent,
song_transp:  db 0              ;   transposition (suit song_rep)
song_changed: db 0              ; 1 = la lecture a changé de position
next_id:      db #FF            ; motif copié dans pat_ahead (#FF : aucun)
pat_dirty:    db 0              ; 1 = pat_work modifié depuis sa copie
sp_cur:       db 0              ; curseur : position (song_len = FIN)
sp_mix:       db 0              ;   1 = sur la ligne du mixage
sp_field:     db 0              ;   champ (0 motif, 1 répétitions, 2 transp.)
sp_voice:     db 0              ;   voix du mixage
sp_top:       db 0              ; 1re position visible
sp_shown_pos: db #FF            ; position marquée ► (#FF : aucune)
spr_i:        db 0
spr_pat:      db 0
spr_ptr:      dw 0
spv_mode:     db 0
spv_s:        db 0
spv_ptr:      dw 0
spv_dir:      db 0
sdm_v:        db 0
sdm_vol:      db 0
sdd_i:        db 0
dur_bars:     dw 0
dur_frames:   ds 3
si_new:       ds 3
