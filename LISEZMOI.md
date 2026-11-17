# SEQ-16 — étape 6 : instruments, mixage et disquette

Trois écrans, à choisir avec les touches de fonction du pavé numérique :

| Touche | Écran |
|---|---|
| f1 | **Séquenceur** : l'édition des motifs |
| f2 | **Instrument** : le réglage des sons |
| f3 | **Disque** : le mixage des 4 voix et la sauvegarde |

Pour quitter, maintiens **ESC** une seconde (un simple appui ne quitte plus,
pour ne pas perdre son travail par erreur).

## Essayer tout de suite

La disquette déjà assemblée est dans `build/seq16.dsk`.
Sur le CPC, tape : `RUN"SEQ16`

## f1 — Séquenceur

| Touches | Effet |
|---|---|
| Flèches | déplacer le curseur ; on entend la note sur laquelle on arrive |
| Touches du piano | poser une note, l'entendre, passer au pas suivant |
| DEL | effacer la case |
| TAB (ou CLR) | arrêt de note (`--`) |
| CAPS LOCK | verrouiller l'instrument de saisie |
| ESPACE | lecture / arrêt |
| f5 | voix séparées / son composé |
| f7 | rendre muette (ou audible) la voix du curseur |
| SHIFT + haut/bas | octave de saisie |
| SHIFT + gauche/droite | instrument de saisie (et de la note sous le curseur) |
| CTRL + haut/bas | tempo en BPM |
| CTRL + gauche/droite | motif précédent / suivant (32 motifs) |

Une voix muette affiche `MUET` à gauche de la grille.

## f2 — Instrument

| Touches | Effet |
|---|---|
| Flèches haut/bas | choisir un réglage |
| Flèches gauche/droite | changer sa valeur (avec SHIFT : par 10) |
| CTRL + gauche/droite | instrument précédent / suivant (32 instruments) |
| SHIFT + haut/bas | octave d'essai |
| Touches du piano | essayer l'instrument |
| ESPACE | écouter le motif avec le son modifié |

Le dessin de l'enveloppe se met à jour à chaque changement d'attaque, de
déclin, de tenue ou de relâche. Les instruments 25 à 32 (`USER1` à
`USER8`) sont libres pour créer ses propres sons.

## f3 — Mixage et disque

| Touches | Effet |
|---|---|
| Flèches haut/bas | choisir une voix (A, B, C, N) ou le nom de fichier |
| Flèches gauche/droite | volume de la voix (0 à 15) |
| RETURN ou f7 | muet / audible (sur la ligne du nom : saisir le nom) |
| S | sauver le morceau |
| L | charger le morceau |
| C | afficher le catalogue de la disquette |
| N | nouveau morceau (appuyer deux fois) |
| ESPACE | écouter le motif pendant le réglage |

### Le nom de fichier

Descends sur la ligne `NOM`, appuie sur RETURN, tape le nom (8 lettres ou
chiffres au plus), puis RETURN. La première lettre tapée remplace l'ancien
nom ; DEL corrige. L'extension `.SNG` est ajoutée toute seule.

### Ce qui est sauvé

Le fichier `.SNG` contient **tout le morceau** : les 32 motifs, les 32
instruments et leurs noms, les 8 sons composés, les volumes et les voix
muettes. Il fait environ 9 Ko. Si un fichier du même nom existe, AMSDOS garde
l'ancien sous l'extension `.BAK`.

### Le volume des voix

Le circuit sonore du CPC envoie la voie A à gauche, la voie C à droite et la
voie B des deux côtés. Selon l'écoute (haut-parleur interne, une seule
oreillette, ampli branché sur une seule sortie), une voie peut paraître plus
forte que les autres : on l'équilibre ici, et le réglage est sauvé avec le
morceau.

## Ce qui n'est pas encore là

- Les sons composés ne se modifient pas encore à l'écran (étape 7).
- L'enchaînement des motifs en morceau (étape 8).
- Les noms d'instruments ne se changent pas encore.
- Copier-coller de blocs (étape 10).

## Réassembler (Windows)

Place `rasm.exe` dans `tools\` (dépôt `EdouardBERGE/rasm` sur GitHub, page
*Releases*), puis lance `build.bat`. Si tu modifies `tools/gen_factory.py`
(instruments et motifs d'usine), lance d'abord `python tools\gen_factory.py`.

## Les fichiers

| Fichier | Rôle |
|---|---|
| `src/main.asm` | les trois écrans, le curseur, la saisie, la disquette |
| `src/song.asm` | le morceau : organisation en mémoire, remise à zéro |
| `src/seq.asm` | le séquenceur : format du motif, lecture au tempo |
| `src/sound.asm` | le moteur de son (4 voix, volumes, voix muettes) |
| `src/factory.asm` | instruments, sons et motifs d'usine (fichier généré) |
| `src/tables.asm` | tables des notes et des volumes (fichier généré) |
| `src/firmware.asm` | les adresses des routines système du CPC utilisées |
| `tools/gen_factory.py`, `tools/gen_tables.py` | les scripts qui génèrent ces fichiers |
| `build.bat` | assemble et fabrique la disquette |
| `build/seq16.dsk` | la disquette prête à l'emploi |
