# Morceaux de test

Fabriqués par `tools/gen_songs.py` ; tous sur `build/seq16-songs.dsk`.

Charger un morceau : panneau SONG (f2), puis f9.  Passer d'un motif à l'autre : panneau MOTIF (f1), CTRL + flèches.  Le panneau SONG du lot 4 jouera l'ordre indiqué.

## NUIT : Nuit (synthwave, 112 BPM)

Am - F - C - G, basse en doubles croches, lead tenu avec vibrato.

- Fichiers : `NUIT.SNG`, `NUIT.INS`
- Instruments à lui : NUITLD, NUITBS, NUITPD, NUITPM
- À tester : notes tenues jusqu'à leur arrêt (traits ■──X), vibrato du lead, accords tenus (arpège rapide), 16 pas de charleston
- Ordre prévu : NUINTRO NUINTRO NUCOUPL NUCOUP2 NUCOUPL NUCOUP2 NUREFR NUREFR2 NUREFR NUREFR2 NUBREAK NUREFR NUREFR2 NUFIN

| Motif | N° | Contenu |
|---|---|---|
| `NUINTRO` | 01 | intro : nappe Am puis F, charleston qui monte |
| `NUCOUPL` | 02 | couplet 1 : Am - F |
| `NUCOUP2` | 03 | couplet 2 : C - G |
| `NUREFR` | 04 | refrain 1 : le lead entre (Am - F) |
| `NUREFR2` | 05 | refrain 2 : C - G, le lead redescend |
| `NUBREAK` | 06 | pont : le lead seul, une note par temps |
| `NUFIN` | 07 | fin : accord de la mineur tenu, puis arrêt |

## ROBOT : Robot (electro (digidrums), 125 BPM)

grosse caisse et caisse claire samplées, basse buzzer, zaps.

- Fichiers : `ROBOT.SNG`, `ROBOT.INS`, banque `DRUMS.SMP`
- Instruments à lui : ROBOBS, ROBOPL, ROBOLD, ROBOZP
- À tester : digidrums (la banque DRUMS se recharge avec le morceau), mode BLOQUANT et rattrapage du tempo, basse à enveloppe matérielle
- Ordre prévu : RBINTRO RBINTRO RBGROOV RBGROOV RBBASS RBBASS RBTHEME RBTHEME RBBREAK RBTHEME RBFIN

| Motif | N° | Contenu |
|---|---|---|
| `RBINTRO` | 01 | intro : digidrums seuls |
| `RBGROOV` | 02 | groove : digidrums + pluck syncopé |
| `RBBASS` | 03 | la basse buzzer entre |
| `RBTHEME` | 04 | thème en octaves sur la basse |
| `RBBREAK` | 05 | break : zaps et caisse claire |
| `RBFIN` | 06 | fin : un coup de grosse caisse et un zap |

## PIXEL : Pixel (chiptune, 150 BPM)

thème de jeu en do majeur, arpèges en doubles croches.

- Fichiers : `PIXEL.SNG`, `PIXEL.INS`
- Instruments à lui : PIXLD, PIXAR, PIXARM, PIXBS
- À tester : tempo rapide, arpèges d'instrument (accords en une voix), notes sur tous les pas
- Ordre prévu : PXINTRO PXTHEME PXTHEM2 PXTHEME PXTHEM2 PXPONT PXPONT PXTHEME PXFIN

| Motif | N° | Contenu |
|---|---|---|
| `PXINTRO` | 01 | intro : arpège do majeur seul |
| `PXTHEME` | 02 | thème : do - fa |
| `PXTHEM2` | 03 | thème, suite : sol - do |
| `PXPONT` | 04 | pont : la mineur - fa, arpèges |
| `PXFIN` | 05 | fin : niveau terminé |

## FUNKY : Funky (funk, 100 BPM)

basse funk en doubles croches, accords piqués, lead glissé.

- Fichiers : `FUNKY.SNG`, `FUNKY.INS`
- Instruments à lui : FKBASS, FKSTAB, FKSLID, FKCLAV
- À tester : basse sur les doubles croches, notes fantômes (volumes), glissando (PORTA), accords mineurs 7 en une voix
- Ordre prévu : FKINTRO FKGROOV FKGROOV FKRIFF FKRIFF FKBREAK FKGROOV FKRIFF FKFIN

| Motif | N° | Contenu |
|---|---|---|
| `FKINTRO` | 01 | intro : charleston et notes fantômes |
| `FKGROOV` | 02 | groove : basse + accords piqués |
| `FKRIFF` | 03 | riff : le lead glisse |
| `FKBREAK` | 04 | break : clavinet syncopé seul |
| `FKFIN` | 05 | fin : basse et accord |

## NAPPE : Nappe (ambient (son composé), 90 BPM)

accords des sons composés : mineur, majeur, sus4, mineur 7, batterie.

- Fichiers : `NAPPE.SNG`, `NAPPE.INS`
- Instruments à lui : DOUX, SIFFLE, CHORUS, HEROS
- À tester : mode son composé : une seule voix SON et les 4 couches du son affichées sous la grille ; sons 0, 1, 5, 6, 7
- Ordre prévu : NPINTRO NPACCO NPACCO2 NPACCO NPACCO2 NPRYTHM NPRYTHM NPFIN

| Motif | N° | Contenu |
|---|---|---|
| `NPINTRO` | 01 | intro : sus4 lents |
| `NPACCO` | 02 | accords lam7 - fa |
| `NPACCO2` | 03 | accords do - mi mineur |
| `NPRYTHM` | 04 | la grosse caisse du son 7 |
| `NPFIN` | 05 | fin : accord mineur tenu |
