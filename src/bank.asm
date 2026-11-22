; ============================================================================
; SEQ-16 - La mémoire supplémentaire du 6128 (64 Ko de plus)
;
; Le 6128 montre ses 4 blocs supplémentaires de 16 Ko, un à la fois, à la
; place de la mémoire #4000-#7FFF : on écrit #C4 à #C7 sur le port #7Fxx
; (#C0 = mémoire normale).  Le programme occupe lui-même #3F00-#7FFF :
; pendant qu'un bloc est montré, seul le code de ce fichier, assemblé en
; #3F00-#3FFF, peut tourner, et il ne copie que vers ou depuis des adresses
; hors de #4000-#7FFF.
;
; Bloc 4 : l'image du morceau, octet pour octet comme dans un fichier .SNG
;   BANK_SONG   en-tête, instruments, noms, sons composés (SONG_FIXED octets)
;   BANK_PATS   les 32 motifs (PAT_SIZE octets chacun)
;   BANK_V2     bloc v2 (SONG_EXTRA octets)
;   BANK_V3     bloc v3 : l'enchaînement (SONG_V3_LEN octets)
; La mémoire principale garde la copie de travail de l'en-tête, des
; instruments, des noms et des sons (le moteur les lit à chaque image), le
; bloc v2, et le motif affiché et joué (pat_work).  L'image du bloc 4 n'est
; à jour qu'après song_to_bank (avant une sauvegarde).
;
; Attention : bank_copy ne copie qu'entre le bloc et une adresse HORS de
; #4000-#7FFF (pat_work, io_buffer).  Pour song_data et song_v2, qui sont
; dans la fenêtre, bank_put et bank_get (song.asm) passent par io_buffer.
;
; Interruptions : le firmware ne garde aucun code à nous dans
; #4000-#7FFF (pas d'événement), mais les copies se font quand même
; interruptions coupées.  Pendant une lecture ou une écriture de fichier,
; elles restent permises (AMSDOS en a besoin) : seuls le firmware et AMSDOS
; tournent alors, en ROM et en mémoire haute.
; ============================================================================

RAM_NORMAL equ #C0              ; #4000-#7FFF : la mémoire normale
RAM_SONG   equ #C4              ; #4000-#7FFF : le bloc 4 (le morceau)
BANK_SONG  equ #4000
BANK_PATS  equ BANK_SONG+SONG_FIXED
BANK_V2    equ BANK_PATS+NB_PAT*PAT_SIZE
BANK_V3    equ BANK_V2+SONG_EXTRA

; Bloc 5 : le morceau d'usine (rangé au démarrage, relu par N N) : les 32
; motifs aux mêmes adresses que dans le bloc 4, puis song_data
RAM_FACT   equ #C5
B5_SONG    equ BANK_V3+SONG_V3_LEN

; Copie BC octets de HL vers DE, le bloc A étant montré en #4000-#7FFF.
; Toujours appelée interruptions permises (boucle principale, lecture et
; écriture de fichier) : elle les rend permises en sortant.  (Pas de
; « ld a,i » pour retrouver leur état : sur Z80, une interruption reçue
; pendant cette instruction fait croire qu'elles étaient coupées, et elles
; le restaient ; AMSDOS en a besoin.)
bank_copy:
        di
        push bc
        ld b,#7F
        out (c),a               ; on montre le bloc
        pop bc
        ldir
        ld bc,#7F00+RAM_NORMAL  ; et on remet la mémoire normale
        out (c),c
        ei
        ret

; Comme CAS_IN_DIRECT, mais HL est une adresse du bloc 4
bank_cas_in:
        push bc
        ld bc,#7F00+RAM_SONG
        out (c),c
        pop bc
        call CAS_IN_DIRECT
        jr bank_normal

; Comme CAS_OUT_DIRECT, mais HL est une adresse du bloc 4
bank_cas_out:
        push bc
        ld bc,#7F00+RAM_SONG
        out (c),c
        pop bc
        call CAS_OUT_DIRECT
; Remet la mémoire normale ; garde tous les registres et les drapeaux
bank_normal:
        push bc
        ld bc,#7F00+RAM_NORMAL
        out (c),c
        pop bc
        ret

; Le CPC a-t-il la mémoire supplémentaire ?  -> Carry = 1 si oui.
; Sur un 464, ou un 664 sans extension, le port ne change rien : l'octet
; écrit « dans le bloc 4 » arrive dans le programme, en #4000.  On le voit,
; et on remet l'octet du programme.
bank_check:
        di
        ld hl,BANK_SONG
        ld c,(hl)               ; C = octet du programme en #4000
        ld b,#7F
        ld a,RAM_SONG
        out (c),a
        ld a,c
        cpl
        ld (hl),a               ; une autre valeur, dans le bloc 4
        ld a,RAM_NORMAL
        out (c),a
        ld a,(hl)
        cp c                    ; Z : le programme n'a pas bougé
        ld (hl),c               ; (sinon on le répare)
        ei
        scf
        ret z
        or a                    ; Carry = 0 : pas de mémoire supplémentaire
        ret
