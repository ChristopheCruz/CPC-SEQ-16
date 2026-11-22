; ============================================================================
; SEQ-16 - Séquenceur : lecture d'un motif de 16 pas
;
; Un motif occupe 260 octets :
;   octet 0      mode : 0 = voix séparées, 1 = son composé
;   octet 1      tempo en BPM (battements par minute, 4 pas par battement)
;   octets 2-3   réserve
;   puis 16 pas de 16 octets.  Chaque pas contient 4 cases de 4 octets,
;   une par voix (A, B, C, bruit) :
;       note         0-95 = note (ou période 0-31 pour la voix de bruit),
;                    #FF = rien (la note précédente continue),
;                    #FE = arrêt de la note
;       instrument   numéro d'instrument ; en mode son composé, numéro du son
;       volume       0-15, ou #FF = volume de l'instrument
;       effet        FX : 0 = aucun ; #1x à #7x (voir fx_time, sound.asm)
;   En mode son composé, seule la première case de chaque pas est utilisée.
;
; Un son composé occupe 16 octets : 4 voix de 3 octets, puis 4 en réserve.
;       décalage     en demi-tons par rapport à la note du pas
;                    (pour la voix de bruit : période du bruit, 0-31)
;       instrument   numéro d'instrument, ou #FF = voix non utilisée
;       volume       0-15, ou #FF = volume de l'instrument
;
; Mode d'emploi :
;   ld hl,motif : call seq_set_pattern
;   call seq_start / call seq_stop
;   call seq_frame      une fois par image, AVANT snd_frame
;   call seq_play_son   B = note, C = son : joue un son composé tout de suite
;   xor a : call sst_off     relâche les 4 voix
; ============================================================================

PAT_MODE   equ 0
PAT_BPM    equ 1
PAT_HEADER equ 4
PAT_SIZE   equ PAT_HEADER+16*16
NOTE_NONE  equ #FF
NOTE_OFF   equ #FE

; Choisit le motif à jouer.  HL = adresse du motif
seq_set_pattern:
        ld (seq_pattern),hl
        inc hl
        ld a,(hl)
        ld (seq_bpm),a
        ret

seq_start:
        xor a
        ld (sq_end),a
        ld (seq_step),a
        ld hl,SEQ_BEAT          ; le premier pas part tout de suite
        ld (seq_acc),hl
        ld a,1
        ld (seq_playing),a
        ret

seq_stop:
        xor a
        ld (sq_end),a
        ld (seq_playing),a
        ld (song_live),a        ; (fin de la lecture du morceau)
        ld (song_transp),a
sst_off:                        ; relâche les 4 voix
        push af
        call snd_note_off
        pop af
        inc a
        cp 4
        jr nz,sst_off
        ret

; A appeler une fois par image.
;
; Tempo : à 50 images par seconde et 4 pas par battement, un pas dure
; 750 / BPM images.  Ce n'est presque jamais un nombre entier : on ajoute donc
; le BPM à un compteur à chaque image, et un pas est joué chaque fois que le
; compteur atteint 750.  Le tempo est exact en moyenne, à une image près.
SEQ_BEAT equ 750

seq_frame:
        ld a,(seq_playing)
        or a
        ret z
        ld hl,(seq_acc)         ; le compteur a-t-il atteint un pas entier ?
        ld de,SEQ_BEAT
        or a
        sbc hl,de
        jr c,sq_wait            ; pas encore
        ld (seq_acc),hl         ; oui : on garde le reste, pour rester exact
        ld a,(sq_end)           ; « 1 FOIS », ou fin d'un morceau sans
        or a                    ; boucle : on s'arrête à l'heure où le pas
        jr nz,seq_end           ; suivant aurait été joué
        call seq_trigger        ; on joue les notes du pas
        xor a                   ; (les autres notes : sans effet)
        ld (sno_fx),a
        ld a,(seq_step)
        inc a
        and 15
        ld (seq_step),a
        call z,bar_end          ; fin de la mesure
sq_wait:
        ld hl,(seq_acc)         ; à chaque image, le compteur avance du tempo
        ld a,(seq_bpm)
        ld e,a
        ld d,0
        add hl,de
        ld (seq_acc),hl
        ret

; Fin de la mesure : panneau MOTIF en « 1 FOIS », la lecture s'arrêtera au
; prochain pas ; sinon le morceau passe à la position suivante (song_bar,
; songpanel.asm ; en MOTIF, il ne fait rien : le motif boucle)
bar_end:
        ld a,(screen)
        or a
        jp nz,song_bar
        ld a,(pat_once)
        or a
        ret z                   ; BOUCLE
        ld (sq_end),a
        ret

seq_end:
        call seq_stop
        ld a,(screen)           ; le panneau SONG montre l'arrêt (MOTIF :
        cp 4                    ; hide_playhead s'en charge)
        ret nz
        ld a,1
        ld (song_changed),a
        ret

sq_end:   db 0                  ; 1 = la lecture s'arrête au prochain pas
pat_once: db 0                  ; panneau MOTIF : 0 = BOUCLE, 1 = 1 FOIS

; Joue les notes du pas courant
seq_trigger:
        ld a,(seq_step)
        ld (seq_pos),a          ; pour l'affichage : pas en cours de lecture
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl               ; 16 octets par pas
        ld de,(seq_pattern)
        add hl,de
        ld de,PAT_HEADER
        add hl,de               ; HL -> les 4 cases du pas
        ld de,(seq_pattern)
        ld a,(de)
        or a
        jr nz,st_comp

        xor a                   ; --- mode voix séparées ---
st_lane:
        ld (st_voice),a
        ld b,(hl)               ; B = note
        inc hl
        ld c,(hl)               ; C = instrument
        inc hl
        ld d,(hl)               ; D = volume
        inc hl
        ld a,(hl)               ; l'effet, pour snd_note_on
        ld (sno_fx),a
        inc hl
        push hl
        ld a,b
        cp NOTE_NONE
        jr z,st_next
        cp NOTE_OFF
        jr nz,st_on
        ld a,(st_voice)
        call snd_note_off
        jr st_next
st_on:
        ld a,(st_voice)         ; transposition du morceau (pas le bruit)
        cp 3
        call nz,song_trans_b
        push de
        ld a,(st_voice)
        call snd_note_on
        pop de
        ld a,d
        cp #FF
        jr z,st_next
        ld (ix+CH_VOL),a        ; volume propre à ce pas
st_next:
        pop hl
        ld a,(st_voice)
        inc a
        cp 4
        jr nz,st_lane
        ret

st_comp:                        ; --- mode son composé ---
        ld b,(hl)               ; B = note
        inc hl
        ld c,(hl)               ; C = numéro du son composé
        inc hl
        inc hl
        ld a,(hl)               ; l'effet : pour les 4 voix du son
        ld (sno_fx),a
        ld a,b
        cp NOTE_NONE
        ret z
        cp NOTE_OFF
        jr nz,st_comp_on
        xor a
        jp sst_off              ; arrêt : on relâche les 4 voix
st_comp_on:
        call song_trans_b       ; transposition du morceau

; Joue un son composé.  B = note, C = numéro du son
seq_play_son:
st_son:
        ld l,c                  ; HL = sons + 16 x numéro
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,sons
        add hl,de
        ld a,b
        ld (st_base),a
        xor a
st_sv:
        ld (st_voice),a
        ld b,(hl)               ; B = décalage (ou période du bruit)
        inc hl
        ld c,(hl)               ; C = instrument
        inc hl
        ld d,(hl)               ; D = volume
        inc hl
        push hl
        ld a,c
        cp #FF
        jr z,st_sv_next         ; voix non utilisée par ce son
        ld a,(st_voice)
        cp 3
        jr z,st_sv_go           ; voix de bruit : B est déjà la période
        ld a,(st_base)
        add a,b                 ; note = note du pas + décalage
        cp 96
        jr c,st_sv_note
        bit 7,b                 ; hors limites : on borne
        ld a,0                  ; (LD ne modifie pas les drapeaux)
        jr nz,st_sv_note
        ld a,95
st_sv_note:
        ld b,a
st_sv_go:
        push de
        ld a,(st_voice)
        call snd_note_on
        pop de
        ld a,d
        cp #FF
        jr z,st_sv_next
        ld (ix+CH_VOL),a
st_sv_next:
        pop hl
        ld a,(st_voice)
        inc a
        cp 4
        jr nz,st_sv
        ret

; --- Variables du séquenceur --------------------------------------------------
seq_pattern: dw 0               ; adresse du motif en cours
seq_bpm:     db 125             ; tempo en BPM
seq_playing: db 0               ; 1 = lecture en cours
seq_step:    db 0               ; prochain pas à jouer (0 à 15)
seq_acc:     dw 0               ; compteur de tempo
seq_pos:     db 0               ; dernier pas joué (pour l'affichage)
st_voice:    db 0
st_base:     db 0
