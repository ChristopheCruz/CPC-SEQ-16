; ============================================================================
; SEQ-16 - Moteur de son
;
; Quatre voix : trois voies de ton (A, B, C) et une voix de bruit (N).
; Chaque voix joue une note avec un instrument.
; Un instrument décrit : une enveloppe de volume ADSR, le mélange ton/bruit,
; l'enveloppe matérielle du circuit (son "buzzer"), un arpège, un vibrato
; et un glissando ou un portamento.
;
; Mode d'emploi, depuis le programme principal :
;   call snd_init       une fois au démarrage (et pour tout couper)
;   call snd_note_on    A = voix (0-2 = A, B, C ; 3 = bruit),
;                       B = note (0-95), ou période du bruit (0-31) pour
;                       la voix 3, C = instrument
;                       En sortie, IX pointe sur la voix : on peut alors
;                       changer son volume avec  ld (ix+CH_VOL),valeur
;   call snd_note_off   A = voix : la note passe en relâche
;   call snd_frame      50 fois par seconde : fait vivre les enveloppes
;                       et envoie le résultat au circuit sonore
;
; Le moteur utilise des données fournies par le morceau (song.asm) :
;   instruments   la table des instruments, 16 octets chacun
;   snd_master    4 octets : volume général des voix A, B, C, N (0 à 15)
;   snd_mute      1 octet  : bits 0 à 3 = voix A, B, C, N muettes
; ============================================================================

; --- Une voix : 16 octets ----------------------------------------------------
CH_NOTE    equ 0        ; note jouée (0 à 95)
CH_INSL    equ 1        ; adresse de l'instrument (octet bas)
CH_INSH    equ 2        ; adresse de l'instrument (octet haut)
CH_PHASE   equ 3        ; 0 = silence, 1 = attaque, 2 = déclin,
                        ; 3 = tenue, 4 = relâche
CH_LEVEL   equ 4        ; niveau de l'enveloppe, de 0 à 255
CH_OUT     equ 5        ; volume envoyé au circuit : 0 à 15, ou 16 = enveloppe
                        ; matérielle
CH_TIME    equ 6        ; nombre d'images depuis le début de la note (max 255)
CH_ARPCNT  equ 7        ; arpège : images passées sur le pas en cours
CH_ARPSTEP equ 8        ; arpège : pas en cours (0, 1 ou 2)
CH_VIBPH   equ 9        ; vibrato : position dans l'oscillation (0 à 255)
CH_OFFL    equ 10       ; décalage de hauteur dû au glissando (octet bas)
CH_OFFH    equ 11       ;   "                                 (octet haut)
CH_PERL    equ 12       ; dernière période envoyée au circuit (octet bas)
CH_PERH    equ 13       ;   "                                 (octet haut)
CH_VOL     equ 14       ; volume de la note, de 0 à 15 (par défaut : celui
                        ; de l'instrument)
CH_SIZE    equ 16       ; (l'octet 15 est en réserve)

; --- Un instrument : 16 octets (format définitif) -----------------------------
INS_ATTACK   equ 0      ; vitesse de montée par image (255 = immédiat)
INS_DECAY    equ 1      ; vitesse de descente vers la tenue
INS_SUSTAIN  equ 2      ; niveau de tenue, de 0 à 15
INS_RELEASE  equ 3      ; vitesse de descente après le relâchement
INS_VOLUME   equ 4      ; volume général de l'instrument, de 0 à 15
INS_FLAGS    equ 5      ; bit 0 = ton, bit 1 = bruit,
                        ; bit 2 = enveloppe matérielle (son "buzzer"),
                        ; bit 3 = portamento (la note glisse depuis la
                        ;         précédente, à la vitesse INS_SLIDE)
INS_NOISE    equ 6      ; période du bruit, de 0 (aigu) à 31 (grave)
INS_EGSHAPE  equ 7      ; forme de l'enveloppe matérielle (8, 10, 12 ou 14)
INS_EGSHIFT  equ 8      ; période d'enveloppe = période de la note divisée
                        ; par 2 puissance INS_EGSHIFT (4 = même note)
INS_ARP1     equ 9      ; arpège : 2e note, en demi-tons au-dessus (0 = aucun)
INS_ARP2     equ 10     ; arpège : 3e note, en demi-tons au-dessus (0 = aucune)
INS_ARPSPEED equ 11     ; arpège : nombre d'images par note
INS_VIBDEPTH equ 12     ; vibrato : profondeur de 0 (aucun) à 6 (très large)
INS_VIBSPEED equ 13     ; vibrato : vitesse (32 = environ 6 battements/s)
INS_VIBDELAY equ 14     ; vibrato : attente en images avant de commencer
INS_SLIDE    equ 15     ; glissando : variation de période par image
                        ; (positif = le son descend, négatif = il monte)
INS_SIZE     equ 16

; ----------------------------------------------------------------------------
; Mise à zéro : tout est coupé
; ----------------------------------------------------------------------------
snd_init:
        ld hl,channels          ; efface les 4 voix
        ld b,4*CH_SIZE
        xor a
sin_clear:
        ld (hl),a
        inc hl
        djnz sin_clear
        ld ix,channels          ; chaque voix pointe sur le 1er instrument
        ld hl,instruments
        ld de,CH_SIZE
        ld b,4
sin_ins:
        ld (ix+CH_INSL),l
        ld (ix+CH_INSH),h
        add ix,de
        djnz sin_ins
        ld hl,ay_regs           ; efface l'image des registres du circuit
        ld b,14
        xor a
sin_regs:
        ld (hl),a
        inc hl
        djnz sin_regs
        ld a,%00111111          ; mixeur : tout fermé
        ld (ay_mixer),a
        ld a,#FF
        ld (eg_trigger),a       ; pas de forme d'enveloppe en attente
        ld (eg_owner),a         ; aucune voie ne pilote l'enveloppe matérielle
        jp snd_write

; ----------------------------------------------------------------------------
; Début d'une note.  A = voie (0-2), B = note (0-95), C = numéro d'instrument
; ----------------------------------------------------------------------------
snd_note_on:
        ld (sno_chan),a
        call snd_chan_ix        ; IX = la voie
        ld l,c                  ; HL = instruments + 16 x numéro
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,instruments
        add hl,de
        push hl                 ; on garde l'adresse de l'instrument
        ld de,INS_FLAGS
        add hl,de
        ld a,(hl)
        ld (sno_flags),a
        bit 4,a                 ; digidrum ? (drapeau 4)
        jr z,sno_tone
        pop hl                  ; HL = instrument
        ld (ix+CH_PHASE),0      ; la voix se tait : le sample prend sa voie
        ld a,(smp_ok)           ; pas de zone haute : pas de sample
        or a
        ret z
        jp dg_queue             ; on met le sample en attente (hizone.asm)
sno_tone:

        xor a                   ; par défaut : pas de décalage de hauteur
        ld (ix+CH_OFFL),a
        ld (ix+CH_OFFH),a
        ld a,(sno_flags)
        bit 3,a                 ; portamento ?
        jr z,sno_no_porta
        ld a,(ix+CH_PHASE)
        or a
        jr z,sno_no_porta       ; la voie était muette : rien d'où glisser
        ld l,b                  ; décalage = ancienne période - nouvelle
        ld h,0
        add hl,hl
        ld de,note_periods
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)               ; DE = période de la nouvelle note
        ld l,(ix+CH_PERL)
        ld h,(ix+CH_PERH)
        or a
        sbc hl,de
        ld (ix+CH_OFFL),l
        ld (ix+CH_OFFH),h
sno_no_porta:
        pop hl                  ; HL = instrument
        push hl
        ld de,INS_VOLUME        ; volume de la note = volume de l'instrument
        add hl,de
        ld a,(hl)
        ld (ix+CH_VOL),a
        pop hl
        ld (ix+CH_NOTE),b
        ld (ix+CH_INSL),l
        ld (ix+CH_INSH),h
        ld (ix+CH_PHASE),1      ; l'enveloppe repart de l'attaque
        xor a
        ld (ix+CH_LEVEL),a
        ld (ix+CH_TIME),a
        ld (ix+CH_ARPCNT),a
        ld (ix+CH_ARPSTEP),a
        ld (ix+CH_VIBPH),a
        ld a,(sno_chan)
        cp 3
        ret z                   ; voix de bruit : rien d'autre à préparer

        ld a,(sno_flags)        ; si l'instrument utilise le bruit,
        bit 1,a                 ; il impose sa période de bruit
        jr z,sno_no_noise
        push hl
        ld de,INS_NOISE
        add hl,de
        ld a,(hl)
        ld (ay_noise),a
        pop hl
sno_no_noise:
        ld a,(sno_flags)        ; enveloppe matérielle ?
        bit 2,a
        jr z,sno_no_eg
        ld de,INS_EGSHAPE
        add hl,de
        ld a,(hl)
        ld (eg_trigger),a       ; la forme sera envoyée à la prochaine image
        ld a,(sno_chan)
        ld (eg_owner),a         ; cette voie pilote la période d'enveloppe
        ret
sno_no_eg:
        ld a,(eg_owner)         ; si cette voie pilotait l'enveloppe,
        ld e,a                  ; elle ne la pilote plus
        ld a,(sno_chan)
        cp e
        ret nz
        ld a,#FF
        ld (eg_owner),a
        ret

; ----------------------------------------------------------------------------
; Fin d'une note.  A = voie (0-2).  L'enveloppe passe en relâche.
; ----------------------------------------------------------------------------
snd_note_off:
        call snd_chan_ix
        ld a,(ix+CH_PHASE)
        or a
        ret z                   ; la voie était déjà silencieuse
        ld (ix+CH_PHASE),4
        ret

; A = bit correspondant à la voix A (0-3) : 1, 2, 4 ou 8
chan_mask:
        ld b,a
        inc b
        ld a,1
cm_loop:
        dec b
        ret z
        add a,a
        jr cm_loop

; IX = adresse de la voix A (0-3)
snd_chan_ix:
        ld ix,channels
        or a
        ret z
        ld de,CH_SIZE
sci_loop:
        add ix,de
        dec a
        jr nz,sci_loop
        ret

; ----------------------------------------------------------------------------
; A appeler une fois par image
; ----------------------------------------------------------------------------
snd_frame:
        ld a,%00111111          ; on repart d'un mixeur fermé
        ld (ay_mixer),a
        ld ix,channels
        xor a
sf_loop:
        ld (sf_chan),a
        call sf_envelope        ; fait avancer l'enveloppe de la voie
        call sf_pitch           ; calcule la hauteur (arpège, glissando, vibrato)
        call sf_output          ; prépare les registres de la voie
        ld de,CH_SIZE
        add ix,de
        ld a,(sf_chan)
        inc a
        cp 3
        jr nz,sf_loop
        call sf_noise_voice     ; la voix de bruit se loge sur une voie
        jp snd_write

; --- Voix de bruit ------------------------------------------------------------
; Le circuit n'a qu'un générateur de bruit, sans volume propre : le bruit doit
; passer par une des voies A, B ou C.  On choisit une voie muette s'il y en a
; une ; sinon le bruit s'ajoute à la voie C.
sf_noise_voice:
        ld ix,channels+3*CH_SIZE
        call sf_envelope
        ld a,(ix+CH_OUT)
        or a
        ret z                   ; la voix de bruit est muette
        cp 16
        jr c,snv_vol
        ld a,15
snv_vol:
        ld c,a
        ld a,(snd_mute)
        bit 3,a
        ret nz                  ; la voix de bruit est muette
        ld a,(snd_master+3)     ; volume final = volume x volume général
        add a,a
        add a,a
        add a,a
        add a,a
        or c
        ld e,a
        ld d,0
        ld hl,vol_table
        add hl,de
        ld a,(hl)
        or a
        ret z
        ld b,a                  ; B = volume du bruit
        ld a,(ix+CH_NOTE)
        and 31
        ld (ay_noise),a         ; période du bruit
        ld hl,ay_regs+10        ; cherche une voie muette : C, puis B, puis A
        ld c,%00100000          ; C = bit de bruit de la voie testée
        ld d,3
snv_find:
        ld a,(hl)
        or a
        jr z,snv_host
        dec hl
        srl c
        dec d
        jr nz,snv_find
        ld hl,ay_regs+10        ; aucune voie muette : on passe par la voie C
        ld c,%00100000
        ld a,(hl)
        cp b
        jr nc,snv_mix           ; la voie C est déjà au moins aussi forte
snv_host:
        ld (hl),b
snv_mix:
        ld a,c                  ; ouvre le bruit sur la voie choisie
        cpl
        ld hl,ay_mixer
        and (hl)
        ld (hl),a
        ret

; --- Enveloppe ADSR d'une voie (IX) ------------------------------------------
sf_envelope:
        ld l,(ix+CH_INSL)
        ld h,(ix+CH_INSH)       ; HL = instrument (pointe sur INS_ATTACK)
        ld a,(ix+CH_PHASE)
        or a
        jr z,se_off
        dec a
        jr z,se_attack
        dec a
        jr z,se_decay
        dec a
        jr z,se_done            ; tenue : le niveau ne bouge pas

        inc hl                  ; --- relâche ---
        inc hl
        inc hl                  ; HL -> INS_RELEASE
        ld a,(ix+CH_LEVEL)
        sub (hl)
        jr c,se_end             ; passé sous zéro : la note est finie
        jr z,se_end
        ld (ix+CH_LEVEL),a
        jr se_done
se_end:
        ld (ix+CH_PHASE),0
se_off:
        ld (ix+CH_LEVEL),0
        jr se_done

se_attack:                      ; --- attaque ---
        ld a,(ix+CH_LEVEL)
        add a,(hl)              ; HL -> INS_ATTACK
        jr nc,se_att_store
        ld a,255                ; sommet atteint : on passe au déclin
        ld (ix+CH_PHASE),2
se_att_store:
        ld (ix+CH_LEVEL),a
        jr se_done

se_decay:                       ; --- déclin ---
        inc hl                  ; HL -> INS_DECAY
        ld a,(ix+CH_LEVEL)
        sub (hl)
        inc hl                  ; HL -> INS_SUSTAIN (INC ne touche pas Carry)
        jr c,se_dec_end         ; passé sous zéro : on se pose sur la tenue
        ld e,a                  ; E = nouveau niveau
        call se_target          ; A = niveau de tenue visé (0 à 255)
        cp e
        jr nc,se_dec_land       ; niveau <= tenue : on s'y pose
        ld (ix+CH_LEVEL),e      ; sinon on continue de descendre
        jr se_done
se_dec_end:
        call se_target
se_dec_land:
        ld (ix+CH_LEVEL),a
        ld (ix+CH_PHASE),3

se_done:                        ; volume final = niveau x volume de la note
        ld a,(ix+CH_VOL)
        add a,a
        add a,a
        add a,a
        add a,a                 ; A = 16 x volume d'instrument
        ld e,a
        ld a,(ix+CH_LEVEL)
        rrca
        rrca
        rrca
        rrca
        and 15                  ; A = niveau ramené de 0 à 15
        or e
        ld e,a
        ld d,0
        ld hl,vol_table
        add hl,de
        ld a,(hl)
        or a
        jr z,se_store           ; muet : on laisse 0
        ld c,a
        ld l,(ix+CH_INSL)
        ld h,(ix+CH_INSH)
        ld de,INS_FLAGS
        add hl,de
        bit 2,(hl)              ; enveloppe matérielle ?
        ld a,c
        jr z,se_store
        ld a,16                 ; 16 = "volume piloté par l'enveloppe du circuit"
se_store:
        ld (ix+CH_OUT),a
        ret

; A = 17 x (HL), soit le niveau de tenue (0-15) ramené de 0 à 255
se_target:
        ld a,(hl)
        ld d,a
        add a,a
        add a,a
        add a,a
        add a,a
        add a,d
        ret

; --- Hauteur d'une voie (IX) : arpège, glissando, vibrato ---------------------
sf_pitch:
        ld a,(ix+CH_PHASE)
        or a
        ret z                   ; voie muette : rien à calculer
        ld a,(ix+CH_TIME)       ; âge de la note, bloqué à 255
        inc a
        jr z,sp_time_max
        ld (ix+CH_TIME),a
sp_time_max:
        ld l,(ix+CH_INSL)
        ld h,(ix+CH_INSH)
        ld (sp_ins),hl

        ld de,INS_ARP1          ; --- arpège ---
        add hl,de
        ld b,(hl)               ; B = 2e note de l'arpège
        inc hl
        ld c,(hl)               ; C = 3e note
        inc hl
        ld d,(hl)               ; D = images par note
        ld e,0                  ; E = demi-tons à ajouter maintenant
        ld a,b
        or c
        jr z,sp_arp_done        ; pas d'arpège
        ld a,(ix+CH_ARPSTEP)
        or a
        jr z,sp_arp_adv         ; pas 0 : la note elle-même
        dec a
        ld e,b                  ; pas 1 (LD ne modifie pas les drapeaux)
        jr z,sp_arp_adv
        ld e,c                  ; pas 2
sp_arp_adv:
        ld a,(ix+CH_ARPCNT)     ; prépare le pas de l'image suivante
        inc a
        cp d
        jr c,sp_arp_keep
        ld a,(ix+CH_ARPSTEP)
        inc a
        ld h,a
        ld a,c
        or a
        ld a,3                  ; 3 notes si la 3e existe, sinon 2
        jr nz,sp_arp_n
        ld a,2
sp_arp_n:
        cp h
        jr nz,sp_arp_step
        ld h,0                  ; on reboucle
sp_arp_step:
        ld (ix+CH_ARPSTEP),h
        xor a
sp_arp_keep:
        ld (ix+CH_ARPCNT),a
sp_arp_done:
        ld a,(ix+CH_NOTE)
        add a,e
        cp 96
        jr c,sp_note_ok
        ld a,95                 ; on ne dépasse pas la dernière note
sp_note_ok:
        ld l,a
        ld h,0
        add hl,hl
        ld de,note_periods
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)               ; DE = période de la note
        ld l,(ix+CH_OFFL)
        ld h,(ix+CH_OFFH)
        add hl,de               ; + décalage du glissando
        push hl
        call sp_slide           ; fait évoluer le décalage pour la suite
        pop hl
        call sp_vibrato         ; + vibrato

        bit 7,h                 ; on borne la période entre 1 et 4095
        jr z,sp_not_neg
        ld hl,1
sp_not_neg:
        ld a,h
        cp 16
        jr c,sp_not_big
        ld hl,4095
sp_not_big:
        ld a,h
        or l
        jr nz,sp_store
        inc l
sp_store:
        ld (ix+CH_PERL),l
        ld (ix+CH_PERH),h
        ret

; Glissando : fait évoluer le décalage de hauteur de la voie (IX)
sp_slide:
        ld hl,(sp_ins)
        ld de,INS_SLIDE
        add hl,de
        ld a,(hl)
        or a
        ret z                   ; pas de glissando
        ld c,a
        ld hl,(sp_ins)
        ld de,INS_FLAGS
        add hl,de
        bit 3,(hl)
        jr nz,sp_porta
        ld e,c                  ; glissando continu : décalage += vitesse
        ld d,0
        bit 7,c
        jr z,sp_sl_pos
        dec d                   ; vitesse négative : on étend le signe
sp_sl_pos:
        ld l,(ix+CH_OFFL)
        ld h,(ix+CH_OFFH)
        add hl,de
        jr sp_off_store
sp_porta:                       ; portamento : le décalage revient vers 0
        ld a,c
        bit 7,a
        jr z,sp_po_abs
        neg
sp_po_abs:
        ld e,a
        ld d,0                  ; DE = vitesse
        ld l,(ix+CH_OFFL)
        ld h,(ix+CH_OFFH)
        ld a,h
        or l
        ret z                   ; déjà arrivé
        bit 7,h
        jr nz,sp_po_neg
        or a                    ; décalage positif : on le réduit
        sbc hl,de
        jr nc,sp_off_store
        ld hl,0                 ; on a dépassé : arrivé
        jr sp_off_store
sp_po_neg:
        add hl,de               ; décalage négatif : on le remonte
        bit 7,h
        jr nz,sp_off_store
        ld hl,0                 ; on a dépassé : arrivé
sp_off_store:
        ld (ix+CH_OFFL),l
        ld (ix+CH_OFFH),h
        ret

; Vibrato : HL = période, renvoie HL = période modulée
sp_vibrato:
        push hl
        ld hl,(sp_ins)
        ld de,INS_VIBDEPTH
        add hl,de
        ld b,(hl)               ; B = profondeur
        inc hl
        ld c,(hl)               ; C = vitesse
        inc hl
        ld d,(hl)               ; D = attente
        pop hl
        ld a,b
        or a
        ret z                   ; pas de vibrato
        cp 7
        jr c,sp_vib_depth
        ld b,6                  ; profondeur maximale
sp_vib_depth:
        ld a,(ix+CH_TIME)
        cp d
        ret c                   ; trop tôt
        ld a,(ix+CH_VIBPH)
        add a,c
        ld (ix+CH_VIBPH),a
        bit 7,a                 ; onde en triangle, de -64 à +63
        jr z,sp_vib_up
        cpl
sp_vib_up:
        sub 64
        ld e,a
        ld a,7
        sub b
        ld b,a                  ; B = nombre de divisions par 2 (1 à 6)
        ld a,e
sp_vib_shift:
        sra a
        djnz sp_vib_shift
        ld e,a                  ; DE = variation de période (avec son signe)
        ld d,0
        bit 7,a
        jr z,sp_vib_add
        dec d
sp_vib_add:
        add hl,de
        ret

; --- Registres d'une voie (IX), numéro de voie dans sf_chan -------------------
sf_output:
        ld a,(sf_chan)
        call chan_mask
        ld b,a
        ld a,(snd_mute)
        and b
        ld c,0                  ; C = volume final ; 0 si la voix est muette
        jr nz,so_vol
        ld a,(ix+CH_OUT)
        ld c,a
        or a
        jr z,so_vol
        cp 16
        jr nc,so_vol            ; enveloppe matérielle : pas de réglage possible
        ld a,(sf_chan)          ; volume final = volume x volume général
        ld e,a
        ld d,0
        ld hl,snd_master
        add hl,de
        ld a,(hl)
        add a,a
        add a,a
        add a,a
        add a,a
        or c
        ld e,a
        ld d,0
        ld hl,vol_table
        add hl,de
        ld c,(hl)
so_vol:
        ld a,(sf_chan)
        ld e,a
        ld d,0
        ld hl,ay_regs+8         ; registres 8, 9, 10 = volumes
        add hl,de
        ld (hl),c
        ld a,c
        or a
        ret z                   ; voie muette : son mixeur reste fermé

        ld a,(sf_chan)          ; période : registres 0-1, 2-3, 4-5
        add a,a
        ld l,a
        ld h,0
        ld bc,ay_regs
        add hl,bc
        ld a,(ix+CH_PERL)
        ld (hl),a
        inc hl
        ld a,(ix+CH_PERH)
        ld (hl),a

        ld l,(ix+CH_INSL)
        ld h,(ix+CH_INSH)
        ld (sp_ins),hl
        ld de,INS_FLAGS
        add hl,de
        ld b,(hl)               ; B = drapeaux de l'instrument

        bit 2,b                 ; enveloppe matérielle pilotée par cette voie ?
        jr z,so_mixer
        ld a,(eg_owner)
        ld c,a
        ld a,(sf_chan)
        cp c
        jr nz,so_mixer
        ld hl,(sp_ins)          ; période d'enveloppe = période de la note
        ld de,INS_EGSHIFT       ; divisée par 2 puissance INS_EGSHIFT
        add hl,de
        ld a,(hl)
        ld l,(ix+CH_PERL)
        ld h,(ix+CH_PERH)
        or a
        jr z,so_eg_store
        ld c,a                  ; C = nombre de divisions par 2
so_eg_shift:
        srl h
        rr l
        dec c
        jr nz,so_eg_shift
        jr nc,so_eg_store       ; arrondi : le dernier bit sorti compte
        inc hl
so_eg_store:
        ld a,h
        or l
        jr nz,so_eg_ok
        inc l                   ; jamais 0
so_eg_ok:
        ld (ay_regs+11),hl      ; registres 11-12 = période d'enveloppe

so_mixer:                       ; mixeur : ouvrir le ton et/ou le bruit
        ld a,(sf_chan)
        ld c,a
        ld a,1                  ; A = bit du ton de cette voie (1, 2 ou 4)
        inc c
so_shift:
        dec c
        jr z,so_got
        add a,a
        jr so_shift
so_got:
        ld d,a
        ld hl,ay_mixer
        bit 0,b
        jr z,so_noise
        cpl
        and (hl)
        ld (hl),a               ; ton ouvert (bit à 0)
so_noise:
        bit 1,b
        ret z
        ld a,d
        add a,a
        add a,a
        add a,a                 ; bit du bruit de cette voie (8, 16 ou 32)
        cpl
        and (hl)
        ld (hl),a               ; bruit ouvert
        ret

; --- Envoi des registres au circuit sonore ------------------------------------
snd_write:
        ld hl,ay_regs           ; registres 0 à 12, à chaque image
        xor a
sw_loop:
        ld c,(hl)
        push af
        push hl
        call MC_SOUND_REGISTER
        pop hl
        pop af
        inc hl
        inc a
        cp 13
        jr nz,sw_loop
        ld a,(eg_trigger)       ; registre 13 (forme d'enveloppe) : seulement
        cp #FF                  ; au début d'une note, car l'écrire relance
        ret z                   ; l'enveloppe
        ld c,a
        ld a,#FF
        ld (eg_trigger),a
        ld a,13
        jp MC_SOUND_REGISTER

; ----------------------------------------------------------------------------
; Variables du moteur
; ----------------------------------------------------------------------------
channels:  ds 4*CH_SIZE         ; les 4 voix : A, B, C et bruit
sf_chan:   db 0                 ; voie en cours de calcul
sp_ins:    dw 0                 ; instrument de la voie en cours de calcul
sno_chan:  db 0                 ; snd_note_on : voie demandée
sno_flags: db 0                 ; snd_note_on : drapeaux de l'instrument
eg_owner:  db #FF               ; voie qui pilote l'enveloppe matérielle
eg_trigger: db #FF              ; forme d'enveloppe à envoyer (#FF = aucune)
ay_regs:   ds 14                ; image des 14 registres du circuit sonore
ay_noise   equ ay_regs+6        ; registre 6 = période du bruit
ay_mixer   equ ay_regs+7        ; registre 7 = mixeur
