; ============================================================================
; SEQ-16 - Lecture des samples (phase 2)
;
; Le CPC n'a pas de convertisseur numérique-analogique : on joue un sample en
; écrivant très vite le REGISTRE DE VOLUME d'une voie de l'AY-3-8912 (16
; niveaux), après avoir fermé le ton et le bruit de cette voie dans le
; mixeur.  Le firmware est bien trop lent pour cela : la routine parle
; directement au PPI 8255, qui relie le processeur à l'AY.
;
;   port #F4xx = port A du PPI : la donnée envoyée à l'AY
;   port #F6xx = port C : bits 7-6 = commande de l'AY
;                #C0 = choisir un registre, #80 = écrire, #00 = repos
;   port #F7xx = registre de contrôle du PPI
;   (sur CPC, c'est l'octet HAUT de l'adresse qui choisit le port : on met
;    le port dans B et on écrit avec  out (c),registre)
;
; Mémoire
; -------
;   #A000-#A0FF  table « poids fort » : octet du sample -> valeur pour l'AY
;                de son échantillon des 4 bits du haut
;   #A100-#A1FF  table « poids faible » : idem pour les 4 bits du bas
;   #A200-...    la routine de lecture, recopiée ici au démarrage
;   #0040-#3FFF  la banque de samples (16 Ko, en mémoire principale).
;                Après RUN" d'un binaire, BASIC ne tourne plus : cette zone,
;                où vivent d'habitude les programmes BASIC, est libre.  Elle
;                marche sur tous les CPC (464, 664, 6128).
;   Plus tard (phase 3), les données pourront venir de la mémoire
;   supplémentaire du 6128, visible en #4000-#7FFF : c'est pourquoi tout ce
;   qui sert pendant la lecture (code, tables, variables) est au-dessus de
;   #8000.
;   La zone #A000-#A5FF est libre : AMSDOS, relancé par KL_INIT_BACK au
;   démarrage, se réserve la mémoire tout en haut (au-dessus de #A67B sur
;   6128).  On le vérifie au démarrage avec les adresses que renvoie
;   KL_INIT_BACK (plus basse et plus haute adresse libres) : si la place
;   manque, les samples sont désactivés.
;
; Mode d'emploi
; -------------
;   call smp_install       au démarrage, DE et HL = adresses renvoyées par
;                          KL_INIT_BACK
;   call smp_load_bank     HL = nom, B = longueur du nom : charge une banque
;                          -> A = 0 si tout va bien, 1 = erreur disque,
;                             2 = trop grande, 3 = pas une banque
;   call smp_play_sample   A = numéro du sample, B = demi-tons (-12 à +12),
;                          C = voie de l'AY (0 = A, 1 = B, 2 = C).
;                          Joue le sample jusqu'au bout, INTERRUPTIONS
;                          COUPÉES : tout le reste est figé pendant ce temps
;                          (les autres voies de l'AY continuent de sonner avec
;                          leurs derniers réglages).  ESPACE interrompt.
;
; Le grain : chaque sample a des réglages appliqués pendant la lecture, sans
; toucher aux données (fréquence, décimation, bits, courbe).  Ils sont
; préparés AVANT la lecture dans les deux tables de 256 octets et dans la
; boucle elle-même (durées d'attente), pour que la boucle ne fasse aucun
; calcul.
; ============================================================================

SMP_LUT_HI  equ #A000           ; table du poids fort (alignée sur 256 octets)
SMP_LUT_LO  equ #A100           ; table du poids faible
SMP_CODE    equ #A200           ; adresse d'exécution de la routine de lecture
SMP_TOP     equ #A600           ; la zone haute ne doit pas dépasser cette adresse
BANK_START  equ #0040           ; la banque : mémoire basse, libre après RUN"
BANK_END    equ #4000           ;   jusqu'au début du programme
BANK_MAX    equ BANK_END-BANK_START

; Fiche d'un sample dans la banque (voir tools/wav2smp.py)
SMPF_BLOCK  equ 6                 ; bloc de 16 Ko (0 en mémoire principale)
SMPF_OFF    equ 7                 ; décalage dans le bloc (2 octets)
SMPF_LEN    equ 9                 ; longueur en octets (2 octets)
SMPF_CODE   equ 11                ; durée d'un échantillon en NOP (62 à 250)
SMPF_LOOP   equ 12                ; point de boucle (2 octets)
SMPF_FLAGS  equ 14                ; bits 4-6 = courbe
SMPF_SET    equ 15                ; bits 0-2 = décimation, bits 3-4 = bits

; Durée d'une boucle de lecture, en NOP (voir le calcul dans smp_loop)
SMP_P_MIN equ 56                ; au plus vite : 56 NOP = 17,8 kHz
SMP_P_MAX equ 1000              ; au plus lent : 1000 NOP = 1 kHz
SMP_HI_FIX equ 36               ; NOP fixes entre l'écriture du poids fort et
                                ; celle du poids faible (hors attente)
SMP_LO_FIX equ 52               ; NOP fixes entre l'écriture du poids faible et
                                ; celle du poids fort suivant (hors attente)
SMP_KEY_FIX equ 163             ; idem quand le clavier est testé (mesuré au
                                ; simulateur, voir tools/test_player.py)

; ----------------------------------------------------------------------------
; Installation au démarrage.  DE = plus basse adresse libre, HL = plus haute
; (ce que renvoie KL_INIT_BACK).
; ----------------------------------------------------------------------------
smp_install:
        ld (smp_himem),hl       ; on les garde (pour les tests et le débogage)
        ld (smp_lomem),de
        xor a
        ld (smp_ok),a           ; samples désactivés tant qu'on n'a pas vérifié
        ld (smp_count),a        ; aucune banque chargée
        ex de,hl                ; la banque doit être libre dès BANK_START
        ld de,BANK_START+1
        or a
        sbc hl,de
        ret nc                  ; plus basse adresse libre > BANK_START : non
        ld hl,(smp_himem)
        ld de,SMP_TOP-1         ; la zone haute doit être libre jusqu'à SMP_TOP
        or a
        sbc hl,de
        ret c                   ; HL < SMP_TOP-1 : pas la place
        ld hl,smp_blk_src       ; on recopie la routine de lecture en SMP_CODE
        ld de,SMP_CODE
        ld bc,smp_blk_len
        ldir
        ld a,1
        ld (smp_ok),a
        ret

; ----------------------------------------------------------------------------
; Chargement d'une banque .SMP.  HL = nom du fichier, B = longueur du nom.
; Sortie : A = 0 tout va bien, 1 = erreur disque, 2 = trop grande,
;          3 = ce n'est pas une banque SEQ-16
; ----------------------------------------------------------------------------
smp_load_bank:
        xor a
        ld (smp_count),a        ; pendant le chargement, plus de banque valable
        ld de,io_buffer
        call CAS_IN_OPEN        ; -> BC = longueur du fichier
        ld a,1
        ret nc                  ; fichier introuvable ou disque absent
        ld (smp_bank_len),bc
        ld hl,BANK_MAX          ; assez de place ?
        or a
        sbc hl,bc
        jr c,slb_big
        ld hl,BANK_START
        call CAS_IN_DIRECT      ; on charge tout le fichier d'un coup
        jr nc,slb_disk
        call CAS_IN_CLOSE
        ld hl,BANK_START        ; signature "SQSM" ?
        ld de,smp_sig
        ld b,4
slb_sig:
        ld a,(de)
        cp (hl)
        jr nz,slb_bad
        inc hl
        inc de
        djnz slb_sig
        ld a,(hl)               ; version 1 ?
        cp 1
        jr nz,slb_bad
        inc hl
        ld a,(hl)               ; nombre de samples : 1 à 16
        or a
        jr z,slb_bad
        cp 17
        jr nc,slb_bad
        ld (smp_count),a
        ld l,a                  ; début des données = BANK_START+16+16 x nombre
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,BANK_START+16
        add hl,de
        ld (smp_data),hl
        ld hl,BANK_START        ; fin de la banque en mémoire
        ld de,(smp_bank_len)
        add hl,de
        ld (smp_bank_end),hl
        xor a                   ; A = 0 : tout va bien
        ret
slb_big:
        call CAS_IN_ABANDON
        ld a,2
        ret
slb_disk:
        call CAS_IN_ABANDON
        ld a,1
        ret
slb_bad:
        xor a
        ld (smp_count),a
        ld a,3
        ret

smp_sig: db "SQSM"

; HL = adresse de la fiche du sample A
smp_entry:
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl               ; 16 octets par fiche
        ld de,BANK_START+16
        add hl,de
        ret

; ----------------------------------------------------------------------------
; Joue un sample.  A = numéro, B = demi-tons (-12 à +12, avec signe),
; C = voie de l'AY (0, 1 ou 2).  Ne fait rien si c'est impossible.
; ----------------------------------------------------------------------------
smp_play_sample:
        call smp_prepare        ; prépare les tables et la boucle
        ret nc                  ; impossible (pas de banque, sample vide...)
        jp smp_play             ; puis on joue (routine en zone haute)

; Prépare tout ce dont la boucle de lecture a besoin.  Carry = 1 si on peut
; jouer.  Tous les registres sont modifiés.
smp_prepare:
        ld (spr_chan),bc        ; LD (nn),BC range C puis B : spr_chan = C
                                ; (voie), spr_semi = B (demi-tons)
        ld e,a
        ld a,(smp_ok)           ; zone haute installée ?
        or a
        ret z                   ; (Z -> on sort avec Carry = 0 grâce au OR)
        ld a,(smp_count)
        ld d,a
        ld a,e
        cp d
        ret nc                  ; numéro trop grand (ou aucune banque)
        call smp_entry
        push hl
        pop ix                  ; IX = fiche du sample

        ld a,(ix+SMPF_BLOCK)      ; phase 2 : seulement la mémoire principale
        or a
        ret nz                  ; (OR remet Carry à 0)
        ld l,(ix+SMPF_OFF)        ; adresse = début des données + décalage
        ld h,(ix+SMPF_OFF+1)
        ld de,(smp_data)
        add hl,de
        ld (smp_v_ptr),hl
        ld e,(ix+SMPF_LEN)        ; longueur
        ld d,(ix+SMPF_LEN+1)
        ld a,d
        or e
        ret z                   ; sample vide
        ld (smp_v_len),de
        add hl,de               ; la fin du sample doit être dans la banque
        ex de,hl
        ld hl,(smp_bank_end)
        or a
        sbc hl,de
        jr nc,spr_period        ; elle y est : on continue
spr_fail:
        or a                    ; Carry = 0 : impossible
        ret

spr_period:
        ; --- durée d'un échantillon : P = code x smp_pitch[demi-tons+12] / 256
        ld a,(spr_semi)
        add a,12                ; -12..+12 -> 0..24
        cp 25
        jr c,spr_semi_ok
        ld a,12                 ; hors limites : hauteur d'origine
spr_semi_ok:
        add a,a                 ; 2 octets par multiplicateur
        ld e,a
        ld d,0
        ld hl,smp_pitch
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl                ; HL = multiplicateur (x256)
        ld a,(ix+SMPF_CODE)       ; A = durée d'origine en NOP
        call mul16x8            ; A:HL = HL x A
        ld l,h                  ; on divise par 256 : HL = A:H
        ld h,a
        ld de,SMP_P_MIN         ; pas plus rapide que la boucle ne le permet
        or a
        sbc hl,de
        jr nc,spr_not_fast
        ld hl,0
spr_not_fast:
        add hl,de
        ld de,SMP_P_MAX+1       ; ni plus lent que SMP_P_MAX
        or a
        sbc hl,de
        jr c,spr_not_slow
        ld hl,-1
spr_not_slow:
        add hl,de               ; HL = P, durée d'un échantillon en NOP
        ld (smp_v_period),hl

        ; --- attentes : P = FIXE + 4 x K + R  (R = 0 à 3 NOP en plus)
        push hl
        ld de,SMP_HI_FIX
        or a
        sbc hl,de
        call smp_split          ; A = K, C = R
        ld (smp_k1+1),a         ; on modifie la boucle elle-même
        ld a,3
        sub c
        ld (smp_j1+1),a         ; on saute 3-R des 3 NOP qui suivent
        pop hl
        ld de,SMP_LO_FIX
        or a
        sbc hl,de
        call smp_split
        ld (smp_k2+1),a
        ld a,3
        sub c
        ld (smp_j2+1),a
        ld hl,(smp_v_period)    ; après un test du clavier : P - SMP_KEY_FIX,
        ld de,SMP_KEY_FIX+4     ; au moins 4 NOP (sinon l'accroc reste, plus
        or a                    ; court)
        sbc hl,de
        jr nc,spr_k3_ok
        ld hl,0
spr_k3_ok:
        ld de,4
        add hl,de
        call smp_split
        ld (smp_k3+1),a
        ld a,3
        sub c
        ld (smp_j3+1),a

        ; --- table de 16 valeurs : code lu -> masque de bits -> courbe
        ld a,(ix+SMPF_SET)        ; masque de bits : bits 3-4 des réglages
        rrca
        rrca
        rrca
        and 3
        ld e,a
        ld d,0
        ld hl,smp_masks
        add hl,de
        ld a,(hl)
        ld (spr_mask),a
        ld a,(ix+SMPF_FLAGS)      ; courbe : bits 4-6 des drapeaux
        rrca
        rrca
        rrca
        rrca
        and 7
        cp 5
        jr c,spr_curve_ok
        ld a,1                  ; courbe inconnue : rendu fidèle
spr_curve_ok:
        add a,a
        add a,a
        add a,a
        add a,a                 ; 16 octets par courbe
        ld e,a
        ld d,0
        ld hl,smp_curves
        add hl,de               ; HL = courbe choisie
        ld de,spr_t             ; spr_t[v] = courbe[v ET masque]
        ld b,0                  ; B = v, de 0 à 15
spr_t_loop:
        push hl
        ld a,(spr_mask)
        and b
        ld c,a
        ld a,b                  ; (on garde B)
        ld b,0
        add hl,bc
        ld b,a
        ld a,(hl)
        ld (de),a
        pop hl
        inc de
        inc b
        ld a,b
        cp 16
        jr nz,spr_t_loop

        ; --- les deux tables de 256 octets : pour chaque octet du sample,
        ;     la valeur de l'échantillon du haut et celle du bas
        ld hl,SMP_LUT_HI
spr_lut:
        ld a,l                  ; 4 bits du haut
        rrca
        rrca
        rrca
        rrca
        and #0F
        call spr_t_get
        ld (hl),a
        ld a,l                  ; 4 bits du bas
        and #0F
        call spr_t_get
        inc h                   ; table du poids faible : 256 octets plus loin
        ld (hl),a
        dec h
        inc l
        jr nz,spr_lut

        ; --- décimation : bits 0-2 des réglages
        ld a,(ix+SMPF_SET)
        and 7
        cp 6
        jr c,spr_dec_ok
        xor a                   ; valeur inconnue : pas de décimation
spr_dec_ok:
        ld e,a
        ld d,0
        ld hl,smp_decims
        add hl,de
        ld a,(hl)
        ld (smp_v_decim),a

        ; --- voie de l'AY : registre de volume, mixeur
        ld a,(spr_chan)
        and 3
        cp 3
        jr c,spr_chan_ok
        ld a,2                  ; voie N : c'est la voie C
spr_chan_ok:
        ld c,a
        add a,8                 ; registres 8, 9, 10 = volumes A, B, C
        ld (smp_v_reg),a
        ld e,a                  ; volume à remettre à la fin : celui du moteur
        ld d,0
        ld hl,ay_regs
        add hl,de
        ld a,(hl)
        ld (smp_v_volrest),a
        ld a,(ay_mixer)         ; mixeur à remettre à la fin
        ld (smp_v_mixrest),a
        ld b,c                  ; mixeur pendant la lecture : ton (bit 0-2) et
        ld a,%00001001          ; bruit (bits 3-5) de la voie fermés (à 1)
        inc b
spr_mix_shift:
        dec b
        jr z,spr_mix_done
        add a,a
        jr spr_mix_shift
spr_mix_done:
        ld hl,ay_mixer
        or (hl)
        ld (smp_v_mixplay),a
        scf                     ; Carry = 1 : on peut jouer
        ret

; A = spr_t[A]  (HL préservé)
spr_t_get:
        push hl
        ld e,a
        ld d,0
        ld hl,spr_t
        add hl,de
        ld a,(hl)
        pop hl
        ret

; HL = nombre de NOP à attendre (au moins 4) -> A = K = HL / 4, C = R = reste.
; La boucle d'attente dure 4 x K NOP (K de 1 à 255), plus R NOP.
smp_split:
        ld a,l
        and 3
        ld c,a                  ; C = R
        srl h
        rr l
        srl h
        rr l                    ; HL = HL / 4
        ld a,l
        or a
        ret nz
        inc a                   ; jamais 0 (la boucle ferait 256 tours)
        ret

; A:HL = HL x A  (multiplication 16 bits x 8 bits -> 24 bits).  BC, DE modifiés.
mul16x8:
        ex de,hl                ; DE = multiplicande
        ld hl,0                 ; C:HL = résultat
        ld c,0
        ld b,8                  ; 8 bits du multiplicateur, du haut vers le bas
m168_loop:
        add hl,hl               ; résultat x 2 (sur 24 bits)
        rl c
        rla                     ; bit suivant du multiplicateur -> Carry
        jr nc,m168_next
        add hl,de               ; bit à 1 : on ajoute le multiplicande
        jr nc,m168_next
        inc c
m168_next:
        djnz m168_loop
        ld a,c
        ret

; Durée en millisecondes du sample A -> HL (longueur x 2 x code / 1000)
smp_duration_ms:
        call smp_entry
        push hl
        pop ix                  ; IX = fiche du sample
        ld l,(ix+SMPF_LEN)
        ld h,(ix+SMPF_LEN+1)
        add hl,hl               ; 2 échantillons par octet (16 Ko max -> 32768)
        ld a,(ix+SMPF_CODE)
        call mul16x8            ; A:HL = nombre d'échantillons x durée (µs)
        ld de,1000
        jp div24

; Fréquence en Hz pour une durée de A NOP -> HL (1 000 000 / A)
smp_freq_hz:
        ld e,a
        ld d,0
        ld a,#0F                ; 1 000 000 = #0F4240
        ld hl,#4240
        ; continue dans div24

; Division 24 bits par 16 bits.  A:HL = dividende, DE = diviseur (non nul).
; Sortie : A:HL = quotient, BC modifié.
div24:
        ld (dv_n),hl
        ld (dv_n+2),a
        ld hl,0                 ; HL = reste
        ld b,24
dv_loop:
        push hl
        ld hl,dv_n              ; dividende x 2 : le bit du haut sort dans Carry
        sla (hl)
        inc hl
        rl (hl)
        inc hl
        rl (hl)
        pop hl                  ; (POP ne touche pas à Carry)
        adc hl,hl               ; reste = reste x 2 + ce bit
        or a
        sbc hl,de               ; le diviseur rentre-t-il ?
        jr nc,dv_fit
        add hl,de               ; non : on annule la soustraction
        jr dv_next
dv_fit:
        ld a,(dv_n)             ; oui : bit du quotient à 1
        or 1
        ld (dv_n),a
dv_next:
        djnz dv_loop
        ld hl,(dv_n)
        ld a,(dv_n+2)
        ret

; Variables (mémoire principale : elles ne servent pas pendant la lecture)
smp_ok:       db 0              ; 1 = routine installée en zone haute
smp_himem:    dw 0              ; plus haute adresse libre au démarrage
smp_lomem:    dw 0              ; plus basse adresse libre au démarrage
smp_count:    db 0              ; nombre de samples de la banque (0 = aucune)
smp_bank_len: dw 0              ; taille du fichier chargé
smp_bank_end: dw 0              ; adresse de fin de la banque
smp_data:     dw 0              ; adresse du début des données
spr_chan:     db 0              ; smp_prepare : voie de l'AY
spr_semi:     db 0              ;   demi-tons (juste après spr_chan)
spr_mask:     db 0              ;   masque de bits
spr_t:        ds 16             ;   les 16 valeurs, après bits et courbe
dv_n:         ds 3              ; div24 : dividende puis quotient

; ============================================================================
; ROUTINE DE LECTURE - recopiée en SMP_CODE (zone haute) par smp_install.
; Elle est assemblée pour son adresse d'exécution (ORG à deux adresses) :
; ses étiquettes valent leur place en zone haute.
; ============================================================================
smp_blk_src:
        org SMP_CODE,smp_blk_src

smp_play:
        di                      ; plus d'interruptions jusqu'à la fin
        exx                     ; le firmware a besoin des registres « bis »
        push bc                 ; (BC' surtout) : on les garde
        push de
        push hl
        exx
        ex af,af'
        push af
        ex af,af'
        ld a,(smp_v_mixplay)    ; mixeur : ton et bruit de la voie fermés,
        ld e,a                  ; la sortie de la voie vaut alors son volume
        ld a,7
        call smp_ay_wr
        ld a,(smp_v_reg)        ; on choisit le registre de volume une fois
        call smp_ay_sel         ; pour toutes

        ld de,(smp_v_len)       ; registres du jeu « bis » (après EXX) :
        ld a,(smp_v_decim)      ;   DE' = octets restants
        ld c,a                  ;   C'  = décimation
        ld b,1                  ;   B'  = compteur de décimation (1 : le
        ld h,128                ;         premier échantillon est lu tout de
        exx                     ;         suite) ; H' = octets avant le test
                                ;         du clavier (128 octets = 256 éch.)
        ld hl,(smp_v_ptr)       ; jeu normal : HL = données,
        ld d,SMP_LUT_HI/256     ;   D = page de la table du poids fort,
        xor a                   ;   E = octet lu, C = valeur jouée, B = port
        ld c,a
        ld (smp_v_armed),a      ; ESPACE n'arrête qu'après avoir été relâchée

; Boucle de lecture : un octet = 2 échantillons.  Durées en NOP (CPC).
; Entre deux écritures du volume, il s'écoule exactement P NOP :
;   poids fort -> poids faible : 36 + 4 x K1 + R1
;   poids faible -> poids fort : 52 + 4 x K2 + R2
smp_loop:
        ; --- échantillon des 4 bits du haut ---
        ld e,(hl)               ; 2  E = octet courant
        ld a,(de)               ; 2  A = sa valeur « poids fort » (table)
        exx                     ; 1  décimation : nouvel échantillon ?
        dec b                   ; 1
        jr nz,smp_h_keep        ; 3 si on garde, 2 sinon
        ld b,c                  ; 1  oui : compteur rechargé
        exx                     ; 1
        ld c,a                  ; 1  C = valeur à jouer
        jr smp_h_out            ; 3
smp_h_keep:
        exx                     ; 1  non : on rejoue la valeur précédente
        nop                     ; 1  (4 NOP pour que les deux chemins
        nop                     ; 1   durent pareil : 10 NOP)
        nop                     ; 1
        nop                     ; 1
smp_h_out:
        ld b,#F4                ; 2
        out (c),c               ; 4  port A = valeur
        ld b,#F6                ; 2
        ld a,#80                ; 2
        out (c),a               ; 4  écriture dans le registre de volume
        out (c),0               ; 4  repos
smp_k1: ld a,1                  ; 2  K1 (modifié par smp_prepare)
smp_w1: dec a                   ; 1  attente : 4 x K1 - 1 NOP
        jr nz,smp_w1            ; 3 / 2
smp_j1: jr smp_s1               ; 3  (décalage modifié : saute 3-R1 NOP)
smp_s1: nop                     ; R1 NOP sur ces 3
        nop
        nop
        ; --- échantillon des 4 bits du bas ---
        inc d                   ; 1  table du poids faible
        ld a,(de)               ; 2
        dec d                   ; 1
        exx                     ; 1  décimation, comme plus haut
        dec b                   ; 1
        jr nz,smp_l_keep        ; 3 / 2
        ld b,c                  ; 1
        exx                     ; 1
        ld c,a                  ; 1
        jr smp_l_out            ; 3
smp_l_keep:
        exx                     ; 1
        nop                     ; 1
        nop                     ; 1
        nop                     ; 1
        nop                     ; 1
smp_l_out:
        ld b,#F4                ; 2
        out (c),c               ; 4
        ld b,#F6                ; 2
        ld a,#80                ; 2
        out (c),a               ; 4  écriture dans le registre de volume
        out (c),0               ; 4
        inc hl                  ; 2  octet suivant
        exx                     ; 1
        dec h                   ; 1  256 échantillons joués ?
        jr z,smp_key            ; 2  (rarement : test du clavier)
smp_l_back:
        dec de                  ; 2  un octet de moins
        ld a,d                  ; 1
        or e                    ; 1
        exx                     ; 1  (EXX ne touche pas aux drapeaux)
        jr z,smp_end            ; 2  plus rien à jouer
smp_k2: ld a,1                  ; 2  K2 (modifié par smp_prepare)
smp_w2: dec a                   ; 1
        jr nz,smp_w2            ; 3 / 2
smp_j2: jr smp_s2               ; 3  (saute 3-R2 NOP)
smp_s2: nop
        nop
        nop
        jp smp_loop             ; 3

; Test de la touche ESPACE, toutes les 256 échantillons (jeu « bis » actif).
; Le firmware ne lit plus le clavier interruptions coupées : on lit la
; ligne 5 de la matrice du clavier par le registre 14 de l'AY.  Le temps
; passé ici est retiré de l'attente qui suit (K3, R3) : la cadence ne bouge
; pas, tant que l'échantillon dure au moins SMP_KEY_FIX + 4 NOP.  Les deux
; chemins de sortie durent pareil (13 NOP).
smp_key:
        ld h,128                ; prochain test dans 128 octets
        push bc
        ld bc,#F40E             ; registre 14 de l'AY (clavier)
        out (c),c
        ld bc,#F6C0             ; choisir ce registre
        out (c),c
        out (c),0               ; repos
        ld bc,#F792             ; port A du PPI en entrée
        out (c),c
        ld bc,#F645             ; lire la ligne 5 du clavier (#40 + ligne)
        out (c),c
        ld b,#F4
        in a,(c)                ; A = ligne 5 (bit à 0 = touche enfoncée)
        ld bc,#F782             ; port A de nouveau en sortie
        out (c),c
        ld bc,#F600             ; port C au repos
        out (c),c
        push af
        ld a,(smp_v_reg)        ; on rechoisit le registre de volume
        call smp_ay_sel
        pop af
        pop bc
        rla                     ; 1  bit 7 = ESPACE -> Carry (1 = relâchée)
        jr c,smp_key_up         ; 3 / 2
        ld a,(smp_v_armed)      ; 4  enfoncée : a-t-elle été relâchée avant ?
        or a                    ; 1
        jr nz,smp_key_stop      ; 2  oui : on arrête
        jr smp_l_back2          ; 3  non (encore l'appui du départ) : on continue
smp_key_up:
        ld a,1                  ; 2  relâchée : le prochain appui arrêtera
        ld (smp_v_armed),a      ; 4
        jr smp_l_back2          ; 3
smp_key_stop:
        exx
        jr smp_end

; Suite de la boucle après un test du clavier : attente raccourcie (K3, R3)
smp_l_back2:
        dec de                  ; 2  un octet de moins
        ld a,d                  ; 1
        or e                    ; 1
        exx                     ; 1
        jr z,smp_end            ; 2
smp_k3: ld a,1                  ; 2  K3 (modifié par smp_prepare)
smp_w3: dec a                   ; 1
        jr nz,smp_w3            ; 3 / 2
smp_j3: jr smp_s3               ; 3  (saute 3-R3 NOP)
smp_s3: nop
        nop
        nop
        jp smp_loop             ; 3

; Fin : on remet le mixeur et le volume du moteur, puis les interruptions.
smp_end:
        ld a,(smp_v_mixrest)
        ld e,a
        ld a,7
        call smp_ay_wr
        ld a,(smp_v_volrest)
        ld e,a
        ld a,(smp_v_reg)
        call smp_ay_wr
        ex af,af'               ; registres « bis » du firmware
        pop af
        ex af,af'
        exx
        pop hl
        pop de
        pop bc
        exx
        ei                      ; le firmware reprend la main
        ret

; Choisit le registre A de l'AY.  BC modifié.
smp_ay_sel:
        ld b,#F4
        out (c),a               ; port A = numéro du registre
        ld bc,#F6C0
        out (c),c               ; « choisir un registre »
        out (c),0               ; repos
        ret

; Écrit E dans le registre A de l'AY.  A, BC modifiés.
smp_ay_wr:
        call smp_ay_sel
        ld b,#F4
        out (c),e               ; port A = valeur
        ld bc,#F680
        out (c),c               ; « écrire »
        out (c),0               ; repos
        ret

; Variables de la lecture (zone haute)
smp_v_ptr:     dw 0             ; adresse des données
smp_v_len:     dw 0             ; longueur en octets
smp_v_period:  dw 0             ; durée d'un échantillon en NOP (pour info)
smp_v_decim:   db 1             ; décimation
smp_v_reg:     db 8             ; registre de volume (8, 9 ou 10)
smp_v_mixplay: db #3F           ; mixeur pendant la lecture
smp_v_mixrest: db #3F           ; mixeur à remettre à la fin
smp_v_volrest: db 0             ; volume à remettre à la fin
smp_v_armed:   db 0             ; 1 = ESPACE a été relâchée

smp_blk_end:
smp_blk_len equ smp_blk_end-SMP_CODE
        assert smp_blk_end <= SMP_TOP
        org smp_blk_src+smp_blk_len
