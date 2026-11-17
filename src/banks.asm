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
