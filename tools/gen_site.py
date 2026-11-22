"""gen_site.py : le contenu des pages du site (docs/), en trois langues.

Réécrit, dans les six pages (accueil et manuel, en anglais, français et
espagnol), le menu, la description et tout le contenu (<main>) ; l'en-tête
et le pied de page restent ceux des fichiers.  Les textes de l'écran du CPC
sont écrits en français et pris dans les traductions de tools/lang.py pour
l'anglais et l'espagnol : le site cite exactement ce que chaque disquette
affiche.  Les captures viennent de tools/snapshots.py.

    python tools/gen_site.py
"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lang  # noqa: E402

GH = "https://github.com/ChristopheCruz/CPC-SEQ-16"
REL = GH + "/releases/latest"
RAW = GH + "/raw/main/build/"
PAGES = {   # langue : (accueil, manuel, préfixe des chemins)
    "en": ("docs/index.html", "docs/manual.html", ""),
    "fr": ("docs/fr/index.html", "docs/fr/manuel.html", "../"),
    "es": ("docs/es/index.html", "docs/es/manual.html", "../"),
}
L = "fr"                                   # langue en cours
# Textes de l'écran identiques dans les trois langues (noms, sigles)
UNTRANSLATED = {"INST", "SAMPLE", "REP", "TR.", "VOLUME", "DIGIDRUM", "GLISSANDO", "PORTAMENTO",
                "VIBRATO", "VIBRATO PROF.", "--", "FX:", "ON/OFF", "NOTE", "OCT", "INS", "BPM", "TYPE", "VERROU", "LOG"}


def S(fr):
    """Un texte de l'écran (en jaune), dans la langue en cours."""
    text = fr
    if L != "fr":
        tr = lang.TEXTS.get(fr)
        if tr is None:
            tr = next((v for k, v in lang.TEXTS.items() if k.strip() == fr.strip()), None)
        if tr is not None:
            text = tr[0 if L == "en" else 1]
        elif any(c.isalpha() for c in fr) and fr not in lang.KEEP and fr.strip() not in UNTRANSLATED:
            raise SystemExit("gen_site : texte d'écran sans traduction : %r" % fr)
    return '<samp class="scr">%s</samp>' % html.escape(text.strip())


def K(*keys):
    """Des touches : K("CTRL", "←/→") ; f1 à f9 sont des touches de fonction."""
    out = []
    for k in keys:
        if "/" in k and len(k) == 3:
            out.append("<kbd>%s</kbd>/<kbd>%s</kbd>" % (k[0], k[2]))
        elif re.fullmatch(r"f\d", k):
            out.append('<kbd class="fn">%s</kbd>' % k)
        else:
            out.append("<kbd>%s</kbd>" % html.escape(k))
    return " + ".join(out)


def table(label, head, rows):
    th = "".join('<th scope="col">%s</th>' % h for h in head)
    body = ""
    for r in rows:
        body += "<tr>" + "".join('<td data-label="%s">%s</td>' % (html.escape(h, quote=True), c)
                                 for h, c in zip(head, r)) + "</tr>"
    return ('<div class="table-wrap" role="region" aria-label="%s" tabindex="0"><table><thead><tr>%s'
            '</tr></thead><tbody>%s</tbody></table></div>\n' % (html.escape(label, quote=True), th, body))


def img(p, name, alt, lazy=True):
    extra = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high" decoding="async"'
    return ('<div class="crt"><img src="%sassets/img/%s/%s" width="672" height="432" alt="%s"%s></div>'
            % (p, L, name, html.escape(alt, quote=True), extra))


def fig(p, name, alt, title, text):
    return ('<figure class="crt-fig">%s<figcaption><strong>%s</strong>%s</figcaption></figure>\n'
            % (img(p, name, alt), title, text))


def section(sid, title, body):
    return ('<section id="%s" aria-labelledby="%s-h">\n<div class="wrap">\n<h2 id="%s-h">%s</h2>\n%s</div>\n</section>\n\n'
            % (sid, sid, sid, title, body))


# Les textes : un dictionnaire par langue ; chaque fonction ci-dessous les
# assemble.  Les touches et les textes de l'écran sont communs.
T = {}

T["fr"] = dict(
    man_title="Manuel de SEQ-16 · chaque panneau, chaque touche",
    man_desc="Manuel de SEQ-16 : les panneaux f1 SONG, f2 MOTIF, f3 INST, f4 SAMPLE et f5 DISQUE, leurs touches, les 7 effets des pas, les sons composés, les fichiers, les banques de sons, les samples et les digidrums.",
    og_alt="Le panneau SONG de SEQ-16 sur Amstrad CPC : un morceau en lecture",
    desc="SEQ-16 est un séquenceur chiptune 4 voix (3 tons + bruit) pour Amstrad CPC 6128, écrit en assembleur Z80 : motifs de 16 pas enchaînés en morceau, 7 effets par pas, sons composés, sampler et digidrums, 13 banques d'instruments, 9 banques de samples et une disquette de démonstration.",
    nav_home=[("#video", "Vidéo"), ("#features", "Fonctions"), ("#screens", "Panneaux"), ("#download", "Télécharger"),
              ("MAN", "Manuel"), ("#pc", "Sur PC"), ("#dev", "Développeurs"), ("#thanks", "Remerciements")],
    nav_man=[("HOME", "Accueil"), ("#start", "Démarrer"), ("#f1", "f1"), ("#f2", "f2"), ("#f3", "f3"), ("#f4", "f4"),
             ("#f5", "f5"), ("#fx", "FX"), ("#files", "Fichiers"), ("#samples", "Samples"), ("#limits", "Limites")],
    tag="SÉQUENCEUR CHIPTUNE · AMSTRAD CPC 6128",
    lead="Un séquenceur chiptune 4 voix (3 tons + bruit) pour Amstrad CPC 6128, écrit en assembleur Z80.",
    intro="32 motifs de 16 pas enchaînés en morceau (64 positions, répétitions, transposition, boucle), 32 instruments, 8 sons composés, 7 effets par pas. Et un sampler qui joue de vrais sons enregistrés sur la puce sonore du CPC, avec un grain réglable en direct : la dégradation du son est recherchée.",
    dl="Télécharger", dl_small="seq16-fr.dsk · version française", all_disks="Toutes les disquettes", last="dernière release",
    then="Puis, sur le CPC (réglé en 6128 dans un émulateur) :", ready_label='Tape RUN"SEQ16 puis RETURN',
    hero_alt="Le panneau SONG de SEQ-16 : un morceau en lecture",
    features_h="Fonctions",
    features=[("Morceaux", "Le panneau SONG enchaîne les motifs : 64 positions, répétitions, transposition, boucle, mixage des voix."),
              ("Motifs", "32 motifs de 16 pas sur 4 voix (A, B, C et bruit N) : note, instrument, volume et effet à chaque pas."),
              ("7 effets par pas", "Monte, descend, arpège, répète, coupe, retard, vibrato : notés en hexadécimal comme dans les trackers."),
              ("Instruments", "32 instruments : enveloppe dessinée en direct, bruit, enveloppe matérielle, arpège, vibrato, glissando, portamento."),
              ("Sons composés", "Une seule note joue jusqu'à 4 instruments à la fois ; les 8 sons composés s'éditent voix par voix."),
              ("Sampler", "Le panneau SAMPLE joue des sons enregistrés (batterie, voix…) avec fréquence, décimation, bits et courbe réglables."),
              ("Digidrums", "Des samples déclenchés au pas comme une note ; un morceau .SNG emporte sa banque de samples."),
              ("Banques et motifs", "13 banques d'instruments (416 sons), 9 banques de samples, 125 motifs d'usine et une disquette de démonstration."),
              ("Vraie machine", "Tourne sur un vrai CPC 6128 (avec un lecteur Gotek) ou dans un émulateur, en français, anglais ou espagnol.")],
    screens_h="Les cinq panneaux",
    screens_intro="Cinq panneaux, à choisir avec les touches de fonction du pavé numérique ; dans chacun, {f8} sauve et {f9} charge.",
    screens_note="Les captures montrent la version française (<code>seq16-fr.dsk</code>), avec le morceau ARCADE de la disquette de démonstration.",
    shots=[("song.png", "f1 · SONG", "L'enchaînement des motifs : positions, répétitions, transposition, boucle, mixage."),
           ("pattern-split.png", "f2 · MOTIF, voix séparées", "Les voix A, B, C et N sur 16 pas ; en haut, la note du curseur et son effet."),
           ("pattern-layered.png", "f2 · MOTIF, son composé", "Une seule ligne qui joue un son composé ; ses couches dessous."),
           ("pattern-fx.png", "f2 · Un effet (FX)", "TAB : le panneau du pas s'édite ; ici l'effet ARPEGE (37)."),
           ("instrument.png", "f3 · INST, instruments", "Enveloppe dessinée en direct et tous les réglages du son."),
           ("layered-sounds.png", "f3 · INST, sons composés", "f6 : les 8 sons composés, voix par voix."),
           ("sampler.png", "f4 · SAMPLE", "La banque de samples et le grain du sample choisi."),
           ("disk.png", "f5 · DISQUE", "Le catalogue par type ; ENTER charge le fichier dans son panneau.")],
    playing=("pattern-playing.png", "f2 · En lecture", "Le pas joué est suivi à l'écran ; la musique ne s'interrompt pas pendant les dessins."),
    download_h="Télécharger",
    download_intro='Les disquettes du programme sont sur la page de la <a href="%s">dernière release</a> ; la démonstration est dans le dossier <code>build/</code> du dépôt. Chaque image <code>.dsk</code> est une disquette CPC standard.' % REL,
    disk_h=("Disquette", "Contenu"),
    disks=[("seq16-fr.dsk", REL + "/download/seq16-fr.dsk", "SEQ-16 en français, avec les 13 banques d'instruments et 8 des 9 banques de samples (<code>CHIFFRES</code> : sur <code>seq16-samples.dsk</code>)"),
           ("seq16-en.dsk", REL + "/download/seq16-en.dsk", "SEQ-16 en anglais (English version), mêmes banques"),
           ("seq16-es.dsk", REL + "/download/seq16-es.dsk", "SEQ-16 en espagnol (versión en español), mêmes banques"),
           ("seq16-demo-fr.dsk", RAW + "seq16-demo-fr.dsk", "<strong>démonstration</strong> : SEQ-16 en français et deux morceaux, ARCADE (son composé, les 7 effets) et STUDIO (samples, voix) ; aussi <a href='%sseq16-demo-en.dsk'>-en</a> et <a href='%sseq16-demo-es.dsk'>-es</a>" % (RAW, RAW)),
           ("seq16-inst.dsk", REL + "/download/seq16-inst.dsk", "banques seules : les 13 banques d'instruments <code>.INS</code> (sans le programme)"),
           ("seq16-samples.dsk", REL + "/download/seq16-samples.dsk", "banques seules : les 9 banques de samples <code>.SMP</code> (sans le programme)"),
           ("seq16-motifs-mono.dsk", REL + "/download/seq16-motifs-mono.dsk", "62 motifs d'usine <strong>mono</strong> (son composé) — panneau MOTIF, f9"),
           ("seq16-motifs-poly.dsk", REL + "/download/seq16-motifs-poly.dsk", "63 motifs d'usine <strong>poly</strong> (voix séparées) — panneau MOTIF, f9")],
    same="Même programme, mêmes fichiers, mêmes touches dans les trois langues : seuls les textes de l'écran changent. Avec une disquette de banques ou de motifs, change de disquette, puis {f9} dans le panneau correspondant (ou le panneau {f5} DISQUE).",
    emu_h="Dans un émulateur",
    emu=["Télécharge <code>seq16-fr.dsk</code>.", "Insère la disquette dans un émulateur (WinAPE, Caprice32, ACE-DL, RetroVirtualMachine…) réglé en <strong>CPC 6128</strong>.", "Tape <code>RUN\"SEQ16</code> puis <kbd>RETURN</kbd>."],
    quit="Pour quitter, maintiens <kbd>ESC</kbd> une seconde. Un simple appui ne suffit pas, pour ne pas perdre son travail par erreur.",
    gotek_h="Sur un vrai CPC avec un Gotek",
    gotek="Copie <code>seq16-fr.dsk</code> sur la clé USB d'un lecteur Gotek (firmware FlashFloppy ou HxC), puis tape <code>RUN\"SEQ16</code> sur le CPC. L'outil compagnon <a href=\"#pc\">CPC DISK</a> prépare la clé USB du Gotek.",
    read_manual="Lire le manuel",
    dev_build="Lance <code>build.bat</code> (il faut Python 3) : il assemble <code>src/main.asm</code> et fabrique les disquettes des trois langues avec toutes les banques, les disquettes de motifs, les morceaux de test et la démonstration (<code>build\\seq16-demo-fr.dsk</code>). <code>tools/snapshots.py</code> refait les captures, <code>tools/gen_site.py</code> ce site.",
)

T["en"] = dict(
    man_title="SEQ-16 user manual · every panel, every key",
    man_desc="SEQ-16 user manual: the f1 SONG, f2 PATTERN, f3 INST, f4 SAMPLE and f5 DISK panels, their keys, the 7 per-step effects, layered sounds, files, sound banks, samples and digidrums.",
    og_alt="The SEQ-16 SONG panel on an Amstrad CPC: a song playing",
    desc="SEQ-16 is a 4-voice chiptune sequencer (3 tones + noise) for the Amstrad CPC 6128, written in Z80 assembly: 16-step patterns chained into songs, 7 per-step effects, layered sounds, sampler and digidrums, 13 instrument banks, 9 sample banks and a demo disk.",
    nav_home=[("#video", "Video"), ("#features", "Features"), ("#screens", "Panels"), ("#download", "Download"),
              ("MAN", "Manual"), ("#pc", "On PC"), ("#dev", "Developers"), ("#thanks", "Thanks")],
    nav_man=[("HOME", "Home"), ("#start", "Start"), ("#f1", "f1"), ("#f2", "f2"), ("#f3", "f3"), ("#f4", "f4"),
             ("#f5", "f5"), ("#fx", "FX"), ("#files", "Files"), ("#samples", "Samples"), ("#limits", "Limits")],
    tag="CHIPTUNE SEQUENCER · AMSTRAD CPC 6128",
    lead="A 4-voice chiptune sequencer (3 tones + noise) for the Amstrad CPC 6128, written in Z80 assembly.",
    intro="32 patterns of 16 steps chained into a song (64 positions, repeats, transposition, loop), 32 instruments, 8 layered sounds, 7 per-step effects. And a sampler that plays real recorded sounds on the CPC sound chip, with a grain you can tweak live: the degraded sound is the goal.",
    dl="Download", dl_small="seq16-en.dsk · English version", all_disks="All disks", last="latest release",
    then="Then, on the CPC (set to 6128 in an emulator):", ready_label='Type RUN"SEQ16 then RETURN',
    hero_alt="The SEQ-16 SONG panel: a song playing",
    features_h="Features",
    features=[("Songs", "The SONG panel chains the patterns: 64 positions, repeats, transposition, loop, voice mixer."),
              ("Patterns", "32 patterns of 16 steps on 4 voices (A, B, C and noise N): note, instrument, volume and effect on every step."),
              ("7 per-step effects", "Up, down, arpeggio, repeat, cut, delay, vibrato: written in hexadecimal as in trackers."),
              ("Instruments", "32 instruments: live envelope drawing, noise, hardware envelope, arpeggio, vibrato, glissando, portamento."),
              ("Layered sounds", "A single note plays up to 4 instruments at once; the 8 layered sounds are edited voice by voice."),
              ("Sampler", "The SAMPLE panel plays recorded sounds (drums, voices…) with adjustable frequency, decimation, bits and curve."),
              ("Digidrums", "Samples triggered on a step like a note; a .SNG song carries its sample bank."),
              ("Banks and patterns", "13 instrument banks (416 sounds), 9 sample banks, 125 factory patterns and a demo disk."),
              ("Real machine", "Runs on a real CPC 6128 (with a Gotek drive) or in an emulator, in English, French or Spanish.")],
    screens_h="The five panels",
    screens_intro="Five panels, picked with the function keys on the numeric keypad; in each one, {f8} saves and {f9} loads.",
    screens_note="The screenshots show the English version (<code>seq16-en.dsk</code>), with the ARCADE song from the demo disk.",
    shots=[("song.png", "f1 · SONG", "The chain of patterns: positions, repeats, transposition, loop, mixer."),
           ("pattern-split.png", "f2 · PATTERN, split voices", "Voices A, B, C and N over 16 steps; at the top, the cursor note and its effect."),
           ("pattern-layered.png", "f2 · PATTERN, layered sound", "A single line playing a layered sound; its layers below."),
           ("pattern-fx.png", "f2 · An effect (FX)", "TAB: the step panel becomes editable; here the ARPEG. effect (37)."),
           ("instrument.png", "f3 · INST, instruments", "Live envelope drawing and every sound setting."),
           ("layered-sounds.png", "f3 · INST, layered sounds", "f6: the 8 layered sounds, voice by voice."),
           ("sampler.png", "f4 · SAMPLE", "The sample bank and the grain of the chosen sample."),
           ("disk.png", "f5 · DISK", "The catalogue by type; ENTER loads the file into its panel.")],
    playing=("pattern-playing.png", "f2 · Playing", "The played step is followed on screen; the music never stops while the screen is redrawn."),
    download_h="Download",
    download_intro='The program disks are on the <a href="%s">latest release</a> page; the demo is in the repository\'s <code>build/</code> folder. Each <code>.dsk</code> image is a standard CPC disk.' % REL,
    disk_h=("Disk", "Content"),
    disks=[("seq16-en.dsk", REL + "/download/seq16-en.dsk", "SEQ-16 in English, with the 13 instrument banks and 8 of the 9 sample banks (<code>CHIFFRES</code>: on <code>seq16-samples.dsk</code>)"),
           ("seq16-fr.dsk", REL + "/download/seq16-fr.dsk", "SEQ-16 in French (version française), same banks"),
           ("seq16-es.dsk", REL + "/download/seq16-es.dsk", "SEQ-16 in Spanish (versión en español), same banks"),
           ("seq16-demo-en.dsk", RAW + "seq16-demo-en.dsk", "<strong>demo</strong>: SEQ-16 in English and two songs, ARCADE (layered sound, all 7 effects) and STUDIO (samples, voice); also <a href='%sseq16-demo-fr.dsk'>French</a> and <a href='%sseq16-demo-es.dsk'>-es</a>" % (RAW, RAW)),
           ("seq16-inst.dsk", REL + "/download/seq16-inst.dsk", "banks only: the 13 <code>.INS</code> instrument banks (without the program)"),
           ("seq16-samples.dsk", REL + "/download/seq16-samples.dsk", "banks only: the 9 <code>.SMP</code> sample banks (without the program)"),
           ("seq16-motifs-mono.dsk", REL + "/download/seq16-motifs-mono.dsk", "62 <strong>mono</strong> factory patterns (layered sound) — PATTERN panel, f9"),
           ("seq16-motifs-poly.dsk", REL + "/download/seq16-motifs-poly.dsk", "63 <strong>poly</strong> factory patterns (split voices) — PATTERN panel, f9")],
    same="Same program, same files, same keys in all three languages: only the screen texts change. With a bank or pattern disk, change disks, then {f9} in the matching panel (or the {f5} DISK panel).",
    emu_h="In an emulator",
    emu=["Download <code>seq16-en.dsk</code>.", "Put the disk in an emulator (WinAPE, Caprice32, ACE-DL, RetroVirtualMachine…) set to <strong>CPC 6128</strong>.", "Type <code>RUN\"SEQ16</code> then <kbd>RETURN</kbd>."],
    quit="To quit, hold <kbd>ESC</kbd> for one second. A single press is not enough, so you cannot lose your work by mistake.",
    gotek_h="On a real CPC with a Gotek",
    gotek="Copy <code>seq16-en.dsk</code> to the USB stick of a Gotek drive (FlashFloppy or HxC firmware), then type <code>RUN\"SEQ16</code> on the CPC. The companion tool <a href=\"#pc\">CPC DISK</a> prepares the Gotek's USB stick.",
    read_manual="Read the manual",
    dev_build="Run <code>build.bat</code> (Python 3 is needed): it assembles <code>src/main.asm</code> and builds the disks in all three languages with every bank, the pattern disks, the test songs and the demo (<code>build\\seq16-demo-fr.dsk</code>). <code>tools/snapshots.py</code> redoes the screenshots, <code>tools/gen_site.py</code> this website.",
)

T["es"] = dict(
    man_title="Manual de SEQ-16 · cada panel, cada tecla",
    man_desc="Manual de SEQ-16: los paneles f1 TEMA, f2 PATRON, f3 INST, f4 SAMPLE y f5 DISCO, sus teclas, los 7 efectos por paso, los sonidos de 4 voces, los ficheros, los bancos de sonidos, los samples y los digidrums.",
    og_alt="El panel TEMA de SEQ-16 en un Amstrad CPC: un tema sonando",
    desc="SEQ-16 es un secuenciador chiptune de 4 voces (3 tonos + ruido) para Amstrad CPC 6128, escrito en ensamblador Z80: patrones de 16 pasos encadenados en temas, 7 efectos por paso, sonidos de 4 voces, sampler y digidrums, 13 bancos de instrumentos, 9 bancos de samples y un disco de demostración.",
    nav_home=[("#video", "Vídeo"), ("#features", "Funciones"), ("#screens", "Paneles"), ("#download", "Descargar"),
              ("MAN", "Manual"), ("#pc", "En PC"), ("#dev", "Desarrolladores"), ("#thanks", "Agradecimientos")],
    nav_man=[("HOME", "Inicio"), ("#start", "Empezar"), ("#f1", "f1"), ("#f2", "f2"), ("#f3", "f3"), ("#f4", "f4"),
             ("#f5", "f5"), ("#fx", "FX"), ("#files", "Ficheros"), ("#samples", "Samples"), ("#limits", "Límites")],
    tag="SECUENCIADOR CHIPTUNE · AMSTRAD CPC 6128",
    lead="Un secuenciador chiptune de 4 voces (3 tonos + ruido) para Amstrad CPC 6128, escrito en ensamblador Z80.",
    intro="32 patrones de 16 pasos encadenados en un tema (64 posiciones, repeticiones, transposición, bucle), 32 instrumentos, 8 sonidos de 4 voces, 7 efectos por paso. Y un sampler que toca sonidos grabados de verdad en el chip de sonido del CPC, con un grano que se ajusta en directo: el sonido degradado es lo que se busca.",
    dl="Descargar", dl_small="seq16-es.dsk · versión en español", all_disks="Todos los discos", last="última release",
    then="Luego, en el CPC (configurado como 6128 en un emulador):", ready_label='Escribe RUN"SEQ16 y RETURN',
    hero_alt="El panel TEMA de SEQ-16: un tema sonando",
    features_h="Funciones",
    features=[("Temas", "El panel TEMA encadena los patrones: 64 posiciones, repeticiones, transposición, bucle, mezcla de las voces."),
              ("Patrones", "32 patrones de 16 pasos en 4 voces (A, B, C y ruido N): nota, instrumento, volumen y efecto en cada paso."),
              ("7 efectos por paso", "Sube, baja, arpegio, repite, corta, demora, vibrato: escritos en hexadecimal como en los trackers."),
              ("Instrumentos", "32 instrumentos: envolvente dibujada en directo, ruido, envolvente hardware, arpegio, vibrato, glissando, portamento."),
              ("Sonidos de 4 voces", "Una sola nota toca hasta 4 instrumentos a la vez; los 8 sonidos se editan voz por voz."),
              ("Sampler", "El panel SAMPLE toca sonidos grabados (batería, voces…) con frecuencia, decimación, bits y curva ajustables."),
              ("Digidrums", "Samples disparados en un paso como una nota; un tema .SNG lleva consigo su banco de samples."),
              ("Bancos y patrones", "13 bancos de instrumentos (416 sonidos), 9 bancos de samples, 125 patrones de fábrica y un disco de demostración."),
              ("Máquina real", "Funciona en un CPC 6128 de verdad (con una disquetera Gotek) o en un emulador, en español, francés o inglés.")],
    screens_h="Los cinco paneles",
    screens_intro="Cinco paneles, que se eligen con las teclas de función del teclado numérico; en cada uno, {f8} graba y {f9} carga.",
    screens_note="Las capturas muestran la versión en español (<code>seq16-es.dsk</code>), con el tema ARCADE del disco de demostración.",
    shots=[("song.png", "f1 · TEMA", "El encadenamiento de los patrones: posiciones, repeticiones, transposición, bucle, mezcla."),
           ("pattern-split.png", "f2 · PATRON, voces sueltas", "Las voces A, B, C y N en 16 pasos; arriba, la nota del cursor y su efecto."),
           ("pattern-layered.png", "f2 · PATRON, sonido de 4 voces", "Una sola línea que toca un sonido de 4 voces; sus capas debajo."),
           ("pattern-fx.png", "f2 · Un efecto (FX)", "TAB: el panel del paso se edita; aquí el efecto ARPEG. (37)."),
           ("instrument.png", "f3 · INST, instrumentos", "La envolvente dibujada en directo y todos los ajustes del sonido."),
           ("layered-sounds.png", "f3 · INST, sonidos de 4 voces", "f6: los 8 sonidos de 4 voces, voz por voz."),
           ("sampler.png", "f4 · SAMPLE", "El banco de samples y el grano del sample elegido."),
           ("disk.png", "f5 · DISCO", "El catálogo por tipo; ENTER carga el fichero en su panel.")],
    playing=("pattern-playing.png", "f2 · Sonando", "El paso que suena se sigue en pantalla; la música no se para mientras se redibuja la pantalla."),
    download_h="Descargar",
    download_intro='Los discos del programa están en la página de la <a href="%s">última release</a>; la demostración está en la carpeta <code>build/</code> del repositorio. Cada imagen <code>.dsk</code> es un disco de CPC normal.' % REL,
    disk_h=("Disco", "Contenido"),
    disks=[("seq16-es.dsk", REL + "/download/seq16-es.dsk", "SEQ-16 en español, con los 13 bancos de instrumentos y 8 de los 9 bancos de samples (<code>CHIFFRES</code>: en <code>seq16-samples.dsk</code>)"),
           ("seq16-fr.dsk", REL + "/download/seq16-fr.dsk", "SEQ-16 en francés (version française), mismos bancos"),
           ("seq16-en.dsk", REL + "/download/seq16-en.dsk", "SEQ-16 en inglés (English version), mismos bancos"),
           ("seq16-demo-es.dsk", RAW + "seq16-demo-es.dsk", "<strong>demostración</strong>: SEQ-16 en español y dos temas, ARCADE (sonido de 4 voces, los 7 efectos) y STUDIO (samples, voz); también en <a href='%sseq16-demo-fr.dsk'>francés</a> y <a href='%sseq16-demo-en.dsk'>-en</a>" % (RAW, RAW)),
           ("seq16-inst.dsk", REL + "/download/seq16-inst.dsk", "solo bancos: los 13 bancos de instrumentos <code>.INS</code> (sin el programa)"),
           ("seq16-samples.dsk", REL + "/download/seq16-samples.dsk", "solo bancos: los 9 bancos de samples <code>.SMP</code> (sin el programa)"),
           ("seq16-motifs-mono.dsk", REL + "/download/seq16-motifs-mono.dsk", "62 patrones de fábrica <strong>mono</strong> (sonido de 4 voces) — panel PATRON, f9"),
           ("seq16-motifs-poly.dsk", REL + "/download/seq16-motifs-poly.dsk", "63 patrones de fábrica <strong>poly</strong> (voces sueltas) — panel PATRON, f9")],
    same="Mismo programa, mismos ficheros, mismas teclas en los tres idiomas: solo cambian los textos de la pantalla. Con un disco de bancos o de patrones, cambia de disco y luego {f9} en el panel correspondiente (o el panel {f5} DISCO).",
    emu_h="En un emulador",
    emu=["Descarga <code>seq16-es.dsk</code>.", "Mete el disco en un emulador (WinAPE, Caprice32, ACE-DL, RetroVirtualMachine…) configurado como <strong>CPC 6128</strong>.", "Escribe <code>RUN\"SEQ16</code> y <kbd>RETURN</kbd>."],
    quit="Para salir, mantén <kbd>ESC</kbd> pulsada un segundo. Una pulsación sola no basta, para no perder el trabajo por error.",
    gotek_h="En un CPC de verdad con un Gotek",
    gotek="Copia <code>seq16-es.dsk</code> en la memoria USB de una disquetera Gotek (firmware FlashFloppy o HxC) y escribe <code>RUN\"SEQ16</code> en el CPC. La herramienta compañera <a href=\"#pc\">CPC DISK</a> prepara la memoria USB del Gotek.",
    read_manual="Leer el manual",
    dev_build="Lanza <code>build.bat</code> (hace falta Python 3): ensambla <code>src/main.asm</code> y fabrica los discos de los tres idiomas con todos los bancos, los discos de patrones, los temas de prueba y la demostración (<code>build\\seq16-demo-fr.dsk</code>). <code>tools/snapshots.py</code> rehace las capturas, <code>tools/gen_site.py</code> esta web.",
)


def fill(text):
    return text.replace("{f8}", K("f8")).replace("{f9}", K("f9")).replace("{f5}", K("f5"))


def nav(items, home, man):
    out = []
    for href, label in items:
        href = {"MAN": man, "HOME": home}.get(href, href)
        out.append('<li><a href="%s">%s</a></li>' % (href, label))
    return '<ul class="nav" id="nav">' + "".join(out) + "</ul>"


# ============================================================================
# Accueil : on remplace l'introduction, les fonctions, les panneaux, les
# disquettes et la ligne build.bat ; le reste (vidéo, CPC DISK, remerciements)
# reste celui de la page.
# ============================================================================
def home(path, p, man):
    t = T[L]
    s = open(path, encoding="utf-8").read()
    hero = ('<div>\n<p class="tag">%s</p>\n<h1 id="top-title">SEQ-16</h1>\n<p class="lead">%s</p>\n<p>%s</p>\n'
            '<div class="actions">\n<a class="btn" href="%s">%s<small>%s</small></a>\n'
            '<a class="btn ghost" href="%s">%s<small>%s</small></a>\n</div>\n<p class="muted">%s</p>\n'
            '<p class="ready" aria-label=\'%s\'>Ready<br>RUN"SEQ16<br><span class="cursor" aria-hidden="true"></span></p>\n</div>\n'
            '<figure class="crt-fig">%s</figure>\n'
            % (t["tag"], t["lead"], t["intro"], t["disks"][0][1], t["dl"], t["dl_small"], REL, t["all_disks"],
               t["last"], t["then"], t["ready_label"], img(p, "song.png", t["hero_alt"], lazy=False)))
    s = re.sub(r'(<div class="wrap hero-grid">\n).*?(\n</div>\n</section>)', lambda m: m.group(1) + hero + m.group(2),
               s, count=1, flags=re.S)
    feats = "".join('<li class="card"><h3>%s</h3><p>%s</p></li>\n' % f for f in t["features"])
    s = re.sub(r'<section id="features".*?</section>\n+',
               lambda m: section("features", t["features_h"], '<ul class="grid">\n%s</ul>\n' % feats), s, count=1, flags=re.S)
    gallery = "".join(fig(p, n, title, title, text) for n, title, text in t["shots"])
    n, title, text = t["playing"]
    screens = ('<p>%s</p>\n<p class="note">%s</p>\n<div class="gallery">\n%s</div>\n<figure>\n%s\n<figcaption><strong>%s</strong>%s</figcaption>\n</figure>\n'
               % (fill(t["screens_intro"]), t["screens_note"], gallery, img(p, n, title), title, text))
    s = re.sub(r'<section id="screens".*?</section>\n+', lambda m: section("screens", t["screens_h"], screens),
               s, count=1, flags=re.S)
    rows = [('<a href="%s"><code>%s</code></a>' % (url, name), what) for name, url, what in t["disks"]]
    dl = ("<p>%s</p>\n%s\n<p>%s</p>\n<div class=\"split\">\n<div>\n<h3 id=\"emulator\">%s</h3>\n<ol class=\"steps\">\n%s</ol>\n<p>%s</p>\n</div>\n"
          "<div>\n<h3 id=\"gotek\">%s</h3>\n<p>%s</p>\n</div>\n</div>\n<p><a class=\"btn ghost\" href=\"%s\">%s</a></p>\n"
          % (t["download_intro"], table(t["disk_h"][0], t["disk_h"], rows), fill(t["same"]), t["emu_h"],
             "".join("<li>%s</li>\n" % x for x in t["emu"]), t["quit"], t["gotek_h"], t["gotek"], man, t["read_manual"]))
    s = re.sub(r'<section id="download".*?</section>\n+', lambda m: section("download", t["download_h"], dl),
               s, count=1, flags=re.S)
    s = re.sub(r'<li>(Lance|Run|Lanza) <code>build\.bat</code>.*?</li>', lambda m: "<li>%s</li>" % t["dev_build"],
               s, count=1, flags=re.S)
    return s


# ============================================================================
# Manuel : tout le contenu est réécrit
# ============================================================================
def fx_rows(names, what):
    codes = ["1x", "2x", "3x", "4x", "5x", "6x", "7x"]
    ex = ["14", "2C", "37", "43", "52", "62", "73"]
    return [("<code>%s</code>" % c, S(n), w, "<code>%s</code>" % e) for c, n, w, e in zip(codes, names, what, ex)]


FX_FR = ["MONTE", "DESCEND", "ARPEGE", "REPETE", "COUPE", "RETARD", "VIBRATO"]


def common_shot(p, name, alt):
    return '<figure class="crt-fig">%s</figure>\n' % img(p, name, alt)


def tr(fr, en, es):
    """La phrase dans la langue en cours."""
    return {"fr": fr, "en": en, "es": es}[L]


def ktable(label, rows):
    head = (tr("Touches", "Keys", "Teclas"), tr("À l'écran", "On screen", "En pantalla"), tr("Effet", "Action", "Acción"))
    return table(label, head, [(k, s, tr(*e)) for k, s, e in rows])


def manual(p, home_url):
    piano = tr("Touches du piano", "Piano keys", "Teclas del piano")
    out = []
    # --- en-tête --------------------------------------------------------------------
    toc = [("#start", tr("Démarrer et quitter", "Starting and quitting", "Empezar y salir")),
           ("#f1", "f1 " + tr("SONG", "SONG", "TEMA")),
           ("#f2", "f2 " + tr("MOTIF", "PATTERN", "PATRON")), ("#f3", "f3 INST"), ("#f4", "f4 SAMPLE"),
           ("#f5", "f5 " + tr("DISQUE", "DISK", "DISCO")), ("#fx", tr("Effets des pas (FX)", "Per-step effects (FX)", "Efectos por paso (FX)")),
           ("#files", tr("Fichiers et messages", "Files and messages", "Ficheros y mensajes")),
           ("#banks", tr("Banques de sons", "Sound banks", "Bancos de sonidos")),
           ("#samples", tr("Samples pas à pas", "Samples step by step", "Samples paso a paso")),
           ("#digidrums", "Digidrums"), ("#limits", tr("Limites et suite", "Limits and roadmap", "Límites y lo que viene"))]
    out.append(
        '<section aria-labelledby="man-h" class="hero">\n<div class="wrap">\n<p class="tag">%s</p>\n<h1 id="man-h">%s</h1>\n'
        '<p class="lead">%s</p>\n<p>%s</p>\n<ul class="toc">\n%s</ul>\n</div>\n</section>\n\n'
        % (tr("MODE D'EMPLOI", "USER MANUAL", "MANUAL DE USO"), tr("Manuel de SEQ-16", "SEQ-16 manual", "Manual de SEQ-16"),
           tr("Chaque panneau et chaque touche de SEQ-16, avec les textes exactement tels que la disquette française (<code>seq16-fr.dsk</code>) les affiche.",
              "Every panel and every key of SEQ-16, with the texts exactly as the English disk (<code>seq16-en.dsk</code>) shows them.",
              "Cada panel y cada tecla de SEQ-16, con los textos tal cual los muestra el disco en español (<code>seq16-es.dsk</code>)."),
           tr("Les textes en jaune, comme %s, sont ceux de l'écran du CPC. Les touches sont dessinées comme des touches de clavier : %s veut dire : maintiens CTRL et appuie sur la flèche gauche ou droite.",
              "Texts in yellow, like %s, are the ones on the CPC screen. Keys are drawn like keyboard keys: %s means: hold CTRL and press the left or right arrow.",
              "Los textos en amarillo, como %s, son los de la pantalla del CPC. Las teclas se dibujan como teclas de teclado: %s quiere decir: mantén CTRL y pulsa la flecha izquierda o derecha.")
           % (S("BOUCLE"), K("CTRL", "←/→")),
           "".join('<li><a href="%s">%s</a></li>\n' % x for x in toc)))
    # --- démarrer ---------------------------------------------------------------------
    out.append(section("start", tr("Démarrer et quitter", "Starting and quitting", "Empezar y salir"),
        '<ol class="steps">\n<li>%s</li>\n<li>%s</li>\n<li>%s</li>\n</ol>\n<div class="callout"><p>%s</p></div>\n<p>%s</p>\n<p>%s</p>\n' % (
            tr("Insère <code>seq16-fr.dsk</code> dans le lecteur (ou dans un émulateur réglé en <strong>CPC 6128</strong>).",
               "Put <code>seq16-en.dsk</code> in the drive (or in an emulator set to <strong>CPC 6128</strong>).",
               "Mete <code>seq16-es.dsk</code> en la disquetera (o en un emulador configurado como <strong>CPC 6128</strong>)."),
            tr("Tape <code>RUN\"SEQ16</code> puis <kbd>RETURN</kbd>. L'écran de chargement s'affiche, puis le programme démarre sur le panneau MOTIF avec SYNTH, la song synthwave d'usine (aussi en fichier SYNTH.SNG sur la disquette).",
               "Type <code>RUN\"SEQ16</code> then <kbd>RETURN</kbd>. The loading screen shows, then the program starts on the PATTERN panel with SYNTH, the factory synthwave song (also on the disk as SYNTH.SNG).",
               "Escribe <code>RUN\"SEQ16</code> y <kbd>RETURN</kbd>. Aparece la pantalla de carga y el programa arranca en el panel PATRON con SYNTH, el tema synthwave de fábrica (también en el disco como SYNTH.SNG)."),
            tr("Choisis un panneau avec les touches de fonction du pavé numérique : %s. Dans chaque panneau, %s sauve et %s charge.",
               "Pick a panel with the function keys on the numeric keypad: %s. In every panel, %s saves and %s loads.",
               "Elige un panel con las teclas de función del teclado numérico: %s. En cada panel, %s graba y %s carga.")
            % (S("|1SONG|2MOTIF|3INST|4SAMPLE|5DISQUE").replace("|", " ").replace("<samp class=\"scr\"> ", "<samp class=\"scr\">"), K("f8"), K("f9")),
            tr("<strong>Pour quitter, maintiens <kbd>ESC</kbd> une seconde.</strong> Un simple appui ne suffit pas, pour ne pas perdre son travail par erreur.",
               "<strong>To quit, hold <kbd>ESC</kbd> for one second.</strong> A single press is not enough, so you cannot lose your work by mistake.",
               "<strong>Para salir, mantén <kbd>ESC</kbd> pulsada un segundo.</strong> Una pulsación sola no basta, para no perder el trabajo por error."),
            tr("Les sons par défaut restent dans le programme : au démarrage et après un nouveau morceau, on retrouve toujours les mêmes 32 instruments. Les instruments 25 à 28 (<code>USER1</code> à <code>USER4</code>) sont libres ; 29 à 32 sont les digidrums d'usine (<code>DGKICK</code>, <code>DGSNAR</code>, <code>DGHAT</code>, <code>DGCLAP</code>).",
               "The default sounds stay inside the program: at startup and after a new song, you always get the same 32 instruments. Instruments 25 to 28 (<code>USER1</code> to <code>USER4</code>) are free; 29 to 32 are the factory digidrums (<code>DGKICK</code>, <code>DGSNAR</code>, <code>DGHAT</code>, <code>DGCLAP</code>).",
               "Los sonidos por defecto están dentro del programa: al arrancar y después de un tema nuevo, siempre se tienen los mismos 32 instrumentos. Los instrumentos 25 a 28 (<code>USER1</code> a <code>USER4</code>) están libres; 29 a 32 son los digidrums de fábrica (<code>DGKICK</code>, <code>DGSNAR</code>, <code>DGHAT</code>, <code>DGCLAP</code>)."),
            tr("Pour découvrir le programme, la disquette de démonstration contient deux morceaux complets : ARCADE (sans sample, son composé, les 7 effets) et STUDIO (batterie en samples et voix). Panneau %s, %s, choisis le morceau, puis %s." % (K("f1"), K("f9"), K("ESPACE")),
               "To discover the program, the demo disk holds two complete songs: ARCADE (no samples, layered sound, all 7 effects) and STUDIO (sampled drums and voice). Panel %s, %s, pick the song, then %s." % (K("f1"), K("f9"), K("SPACE")),
               "Para descubrir el programa, el disco de demostración trae dos temas completos: ARCADE (sin samples, sonido de 4 voces, los 7 efectos) y STUDIO (batería de samples y voz). Panel %s, %s, elige el tema y luego %s." % (K("f1"), K("f9"), K("ESPACIO"))))))
    sp = K(tr("ESPACE", "SPACE", "ESPACIO"))
    # --- f1 SONG ------------------------------------------------------------------------
    rows = [(K("↑/↓"), S("POSITION"), ("choisir une position (sous la ligne FIN : le mixage)", "pick a position (below the END line: the mixer)", "elegir una posición (bajo la línea FIN: la mezcla)")),
            (K("←/→"), S("CHAMP"), ("choisir un champ : motif, répétitions, transposition (dans le mixage : la voix)", "pick a field: pattern, repeats, transposition (in the mixer: the voice)", "elegir un campo: patrón, repeticiones, transposición (en la mezcla: la voz)")),
            (K("SHIFT", "↑/↓"), S("VALEUR"), ("changer la valeur (dans le mixage : le volume de la voix)", "change the value (in the mixer: the voice volume)", "cambiar el valor (en la mezcla: el volumen de la voz)")),
            (K("ENTER"), S("INSERER"), ("insérer une position", "insert a position", "insertar una posición")),
            (K("DEL"), S("OTER"), ("ôter la position", "remove the position", "quitar la posición")),
            (K("COPY"), S("DOUBLER"), ("doubler la position", "double the position", "duplicar la posición")),
            (K("B"), S("BOUCLE"), ("la boucle part d'ici ; sur la position de la boucle, B la retire : la lecture s'arrête alors à la fin du morceau", "the loop starts here; on the loop position, B removes it: playback then stops at the end of the song", "el bucle empieza aquí; en la posición del bucle, B lo quita: la reproducción se para entonces al final del tema")),
            (sp, S("LIRE"), ("lire le morceau depuis le curseur / arrêter", "play the song from the cursor / stop", "tocar el tema desde el cursor / parar")),
            (K("f8") + " / " + K("f9"), S("DISQUE"), ("sauver / charger un morceau <code>.SNG</code>", "save / load a <code>.SNG</code> song", "grabar / cargar un tema <code>.SNG</code>"))]
    out.append(section("f1", "f1 · " + tr("SONG, le morceau", "SONG, the song", "TEMA, el tema"),
        '<div class="split wide-left">\n<div>\n<p>%s</p>\n<p>%s</p>\n</div>\n%s</div>\n%s<p>%s</p>\n' % (
            tr("Un morceau enchaîne jusqu'à 64 positions. Chaque ligne donne la position, le motif et son nom, les répétitions (%s, 1 à 16), la transposition (%s, −12 à +12 demi-tons, sauf le bruit) et un aperçu des pas. Le repère ► suit la position jouée, ↑ marque le départ de la boucle ; la ligne %s ferme la liste." % (S("REP"), S("TR."), S("-- FIN : RETOUR EN ")),
               "A song chains up to 64 positions. Each line gives the position, the pattern and its name, the repeats (%s, 1 to 16), the transposition (%s, −12 to +12 semitones, not the noise) and a view of the steps. The ► marker follows the played position, ↑ marks the start of the loop; the %s line closes the list." % (S("REP"), S("TR."), S("-- FIN : RETOUR EN ")),
               "Un tema encadena hasta 64 posiciones. Cada línea da la posición, el patrón y su nombre, las repeticiones (%s, 1 a 16), la transposición (%s, −12 a +12 semitonos, salvo el ruido) y una vista de los pasos. La marca ► sigue la posición que suena, ↑ marca el inicio del bucle; la línea %s cierra la lista." % (S("REP"), S("TR."), S("-- FIN : RETOUR EN "))),
            tr("En bas, %s règle le volume de chaque voix (sauvé avec le morceau) et %s donne la longueur du morceau. Sur le panneau MOTIF, le morceau n'avance pas : le motif affiché boucle ; au retour dans SONG, le morceau reprend." % (S("MIXAGE"), S("DUREE")),
               "At the bottom, %s sets the volume of each voice (saved with the song) and %s gives the song length. On the PATTERN panel, the song does not move on: the displayed pattern loops; back in SONG, the song carries on." % (S("MIXAGE"), S("DUREE")),
               "Abajo, %s ajusta el volumen de cada voz (se graba con el tema) y %s da la duración del tema. En el panel PATRON, el tema no avanza: el patrón que se ve se repite; al volver a TEMA, el tema sigue." % (S("MIXAGE"), S("DUREE"))),
            common_shot(p, "song.png", "f1 SONG"), ktable("f1", rows),
            tr("Le nom d'un motif est celui de son fichier <code>.PAT</code> : il apparaît dans SONG et sur la ligne d'état du panneau MOTIF.",
               "A pattern's name is the name of its <code>.PAT</code> file: it shows in SONG and on the PATTERN panel's status line.",
               "El nombre de un patrón es el de su fichero <code>.PAT</code>: aparece en TEMA y en la línea de estado del panel PATRON."))))
    # --- f2 MOTIF -----------------------------------------------------------------------
    rows = [(K("←/→") + " " + K("↑/↓"), S("PAS/VOIX"), ("déplacer le curseur ; on entend la note sur laquelle on arrive", "move the cursor; you hear the note you land on", "mover el cursor; se oye la nota a la que se llega")),
            (piano, S("NOTE"), ("poser une note avec l'instrument du pinceau, l'entendre, passer au pas suivant", "put a note with the brush instrument, hear it, move to the next step", "poner una nota con el instrumento del pincel, oírla, pasar al paso siguiente")),
            (K("ENTER"), S("ON/OFF"), ("allumer la case avec le pinceau, ou l'éteindre", "turn the cell on with the brush, or off", "encender la casilla con el pincel, o apagarla")),
            (K("DEL"), S("VIDER"), ("vider la case", "clear the cell", "vaciar la casilla")),
            (K("CLR"), S("ARRET"), ("arrêt de note", "note stop", "parada de nota")),
            (K("COPY"), S("PRENDRE"), ("la case devient le pinceau (note et instrument)", "the cell becomes the brush (note and instrument)", "la casilla pasa a ser el pincel (nota e instrumento)")),
            (K("TAB"), S("EDITER"), ("éditer le panneau du pas : %s choisit NOTE, INS, VOL puis les deux chiffres du FX, %s change la valeur" % (K("←/→"), K("↑/↓")), "edit the step panel: %s picks NOTE, INS, VOL then the two FX digits, %s changes the value" % (K("←/→"), K("↑/↓")), "editar el panel del paso: %s elige NOTA, INS, VOL y luego las dos cifras del FX, %s cambia el valor" % (K("←/→"), K("↑/↓")))),
            (K("CAPS LOCK"), S("VERROU"), ("verrouiller l'instrument du pinceau", "lock the brush instrument", "bloquear el instrumento del pincel")),
            (sp, S("LIRE"), ("lecture / arrêt", "play / stop", "tocar / parar")),
            (K("L"), S("BOUCLE") + " / " + S("1 FOIS"), ("le motif se répète, ou n'est joué qu'une fois", "the pattern repeats, or plays only once", "el patrón se repite, o se toca una sola vez")),
            (K("f6"), S("MODE"), ("voix séparées / son composé", "split voices / layered sound", "voces sueltas / sonido de 4 voces")),
            (K("f7"), S("MUET"), ("rendre muette (ou audible) la voix du curseur", "mute (or unmute) the cursor's voice", "silenciar (o volver a oír) la voz del cursor")),
            (K("SHIFT", "↑/↓"), S("OCT"), ("octave de saisie", "input octave", "octava de entrada")),
            (K("SHIFT", "←/→"), S("INS"), ("instrument du pinceau (et de la note sous le curseur)", "brush instrument (and the note under the cursor)", "instrumento del pincel (y de la nota bajo el cursor)")),
            (K("CTRL", "↑/↓"), S("BPM"), ("tempo en BPM", "tempo in BPM", "tempo en BPM")),
            (K("CTRL", "←/→"), S("MOTIF"), ("motif précédent / suivant (32 motifs) ; la musique continue", "previous / next pattern (32 patterns); the music goes on", "patrón anterior / siguiente (32 patrones); la música sigue")),
            (K("f8") + " / " + K("f9"), S("SAUVER") + " " + S("CHARGER"), ("sauver / charger le motif affiché (<code>.PAT</code>)", "save / load the displayed pattern (<code>.PAT</code>)", "grabar / cargar el patrón que se ve (<code>.PAT</code>)"))]
    out.append(section("f2", "f2 · " + tr("MOTIF, le séquenceur", "PATTERN, the sequencer", "PATRON, el secuenciador"),
        '<div class="split wide-left">\n<div>\n<p>%s</p>\n<p>%s</p>\n</div>\n%s</div>\n%s<div class="gallery">\n%s%s</div>\n' % (
            tr("En haut, la ligne d'état : le numéro et le nom du motif (%s), le tempo et l'état. Dessous, le panneau du pas : le pas et la voix du curseur, un clavier de 2 octaves, et la note, l'instrument, le volume et l'effet de la case (%s)." % (S("MOTIF:"), S("FX:")),
               "At the top, the status line: the pattern number and name (%s), the tempo and the state. Below, the step panel: the cursor's step and voice, a 2-octave keyboard, and the cell's note, instrument, volume and effect (%s)." % (S("MOTIF:"), S("FX:")),
               "Arriba, la línea de estado: el número y el nombre del patrón (%s), el tempo y el estado. Debajo, el panel del paso: el paso y la voz del cursor, un teclado de 2 octavas, y la nota, el instrumento, el volumen y el efecto de la casilla (%s)." % (S("MOTIF:"), S("FX:"))),
            tr("La grille : les voix A, B, C et N (bruit) sur 16 pas. Une note tenue est prolongée par un trait jusqu'à son arrêt ; une voix muette s'affiche en orange. En mode son composé, une seule ligne joue un son composé sur les 4 voix, et ses couches s'affichent sous la grille.",
               "The grid: voices A, B, C and N (noise) over 16 steps. A held note is drawn as a line up to its stop; a muted voice shows in orange. In layered-sound mode, a single line plays a layered sound on the 4 voices, and its layers show under the grid.",
               "La rejilla: las voces A, B, C y N (ruido) en 16 pasos. Una nota mantenida se prolonga con una raya hasta su parada; una voz silenciada se ve en naranja. En modo sonido de 4 voces, una sola línea toca un sonido en las 4 voces, y sus capas se ven bajo la rejilla."),
            common_shot(p, "pattern-split.png", "f2"), ktable("f2", rows),
            fig(p, "pattern-layered.png", "f2", tr("Son composé", "Layered sound", "Sonido de 4 voces"), tr("Une note, quatre voix.", "One note, four voices.", "Una nota, cuatro voces.")),
            fig(p, "pattern-playing.png", "f2", tr("En lecture", "Playing", "Sonando"), tr("Le pas joué est suivi à l'écran.", "The played step is followed on screen.", "El paso que suena se sigue en pantalla.")))))
    # --- f3 INST --------------------------------------------------------------------------
    rows = [(K("↑/↓"), S("REGLAGE"), ("choisir un réglage", "pick a setting", "elegir un ajuste")),
            (K("←/→"), S("VALEUR"), ("changer sa valeur", "change its value", "cambiar su valor")),
            (K("SHIFT", "←/→"), S("PAR 10"), ("changer la valeur par 10", "change the value by 10", "cambiar el valor de 10 en 10")),
            (K("CTRL", "←/→"), S("INSTR."), ("instrument précédent / suivant (32 instruments)", "previous / next instrument (32 instruments)", "instrumento anterior / siguiente (32 instrumentos)")),
            (K("SHIFT", "↑/↓"), S("OCTAVE"), ("octave d'essai", "test octave", "octava de prueba")),
            (piano, S("ESSAI"), ("essayer l'instrument", "try the instrument", "probar el instrumento")),
            (sp, S("LECTURE"), ("écouter le motif avec le son modifié", "hear the pattern with the changed sound", "oír el patrón con el sonido cambiado")),
            (K("f6"), S("MODE"), ("passer aux sons composés", "switch to the layered sounds", "pasar a los sonidos de 4 voces")),
            (K("COPY"), S("COPIER"), ("copier l'instrument (réglages et nom)", "copy the instrument (settings and name)", "copiar el instrumento (ajustes y nombre)")),
            (K("P"), S("COLLER"), ("coller : l'instrument copié remplace l'instrument affiché", "paste: the copied instrument replaces the displayed one", "pegar: el instrumento copiado sustituye al que se ve")),
            (K("O"), S("SON BANQUE"), ("prendre un son dans une banque <code>.INS</code> : la banque, puis l'un de ses 32 sons", "take one sound from an <code>.INS</code> bank: the bank, then one of its 32 sounds", "tomar un sonido de un banco <code>.INS</code>: el banco y luego uno de sus 32 sonidos")),
            (K("f8") + " / " + K("f9"), "", ("sauver / charger une banque d'instruments <code>.INS</code>", "save / load an <code>.INS</code> instrument bank", "grabar / cargar un banco de instrumentos <code>.INS</code>"))]
    settings = [("ATTAQUE", "0 – 255"), ("DECLIN", "0 – 255"), ("TENUE", "0 – 15"), ("RELACHE", "0 – 255"), ("VOLUME", "0 – 15"),
                ("TON", S("OUI") + " / " + S("NON")), ("BRUIT", S("OUI") + " / " + S("NON")), ("PERIODE", "0 – 31"),
                ("ENV. MATERIELLE", S("OUI") + " / " + S("NON")), ("FORME", "8 – 15"), ("DIVISION", "0 – 7"),
                ("ARPEGE NOTE 2", "0 – 24"), ("ARPEGE NOTE 3", "0 – 24"), ("VITESSE", "1 – 15"), ("VIBRATO PROF.", "0 – 6"),
                ("GLISSANDO", tr("valeur signée (<code>+008</code>)", "signed value (<code>+008</code>)", "valor con signo (<code>+008</code>)")),
                ("PORTAMENTO", S("OUI") + " / " + S("NON")), ("DIGIDRUM", S("OUI") + " / " + S("NON"))]
    srows = [(K("↑/↓"), S("REGLAGE"), ("choisir un champ : pour chaque voix, l'instrument, le décalage, le volume", "pick a field: for each voice, the instrument, the shift, the volume", "elegir un campo: para cada voz, el instrumento, el desplazamiento, el volumen")),
             (K("←/→"), S("VALEUR"), ("changer sa valeur (avec SHIFT : par 10)", "change its value (with SHIFT: by 10)", "cambiar su valor (con SHIFT: de 10 en 10)")),
             (K("CTRL", "←/→"), S("SON"), ("son composé précédent / suivant (S1 à S8)", "previous / next layered sound (S1 to S8)", "sonido anterior / siguiente (S1 a S8)")),
             (piano, S("ESSAI"), ("essayer le son composé", "try the layered sound", "probar el sonido"))]
    out.append(section("f3", "f3 · " + tr("INST, instruments et sons composés", "INST, instruments and layered sounds", "INST, instrumentos y sonidos de 4 voces"),
        '<div class="split wide-left">\n<div>\n<p>%s</p>\n</div>\n%s</div>\n%s<h3 id="f3-settings">%s</h3>\n%s<p>%s</p>\n<h3 id="f3-layers">%s</h3>\n'
        '<div class="split wide-left">\n<div>\n<p>%s</p>\n<p>%s</p>\n</div>\n%s</div>\n%s' % (
            tr("Le numéro et le nom de l'instrument (%s), l'octave d'essai, la liste des réglages à gauche et le dessin de l'%s à droite, mis à jour à chaque changement d'attaque, de déclin, de tenue ou de relâche. Changer d'instrument ne réécrit que les valeurs qui changent." % (S("INSTRUMENT :"), S("ENVELOPPE")),
               "The instrument number and name (%s), the test octave, the settings on the left and the %s drawing on the right, updated on every change of attack, decay, sustain or release. Changing instrument only rewrites the values that change." % (S("INSTRUMENT :"), S("ENVELOPPE")),
               "El número y el nombre del instrumento (%s), la octava de prueba, los ajustes a la izquierda y el dibujo de la %s a la derecha, que se actualiza con cada cambio de ataque, caída, sostenido o relajación. Cambiar de instrumento solo reescribe los valores que cambian." % (S("INSTRUMENT :"), S("ENVELOPPE"))),
            common_shot(p, "instrument.png", "f3"), ktable("f3", rows),
            tr("Les réglages", "Settings", "Los ajustes"),
            table(tr("Réglages", "Settings", "Ajustes"), (tr("Réglage", "Setting", "Ajuste"), tr("Valeurs", "Values", "Valores")),
                  [(S(n), v) for n, v in settings]),
            tr("Le réglage %s (le dernier) : à %s, l'instrument joue un sample au lieu d'une note ; la ligne %s devient %s suivie du nom du sample. Voir <a href=\"#digidrums\">Digidrums</a>." % (S("DIGIDRUM"), S("OUI"), S("PERIODE"), S("SAMPLE")),
               "The %s setting (the last one): set to %s, the instrument plays a sample instead of a note; the %s line becomes %s followed by the sample's name. See <a href=\"#digidrums\">Digidrums</a>." % (S("DIGIDRUM"), S("OUI"), S("PERIODE"), S("SAMPLE")),
               "El ajuste %s (el último): en %s, el instrumento toca un sample en vez de una nota; la línea %s pasa a ser %s seguida del nombre del sample. Ver <a href=\"#digidrums\">Digidrums</a>." % (S("DIGIDRUM"), S("OUI"), S("PERIODE"), S("SAMPLE"))),
            tr("Les sons composés (f6)", "Layered sounds (f6)", "Los sonidos de 4 voces (f6)"),
            tr("Un son composé joue jusqu'à 4 instruments à la fois, un par voix, à partir d'une seule note. %s affiche ses 4 voix : l'instrument (<code>--</code> : voix inutilisée, ou 01 à 32), le décalage (−24 à +24 demi-tons ; pour la voix N, la période du bruit <code>BR00</code> à <code>BR1F</code>) et le volume (<code>-</code> : celui de l'instrument, ou 0 à 15)." % S("COUCHES DU SON S"),
               "A layered sound plays up to 4 instruments at once, one per voice, from a single note. %s shows its 4 voices: the instrument (<code>--</code>: voice not used, or 01 to 32), the shift (−24 to +24 semitones; for voice N, the noise period <code>BR00</code> to <code>BR1F</code>) and the volume (<code>-</code>: the instrument's, or 0 to 15)." % S("COUCHES DU SON S"),
               "Un sonido de 4 voces toca hasta 4 instrumentos a la vez, uno por voz, a partir de una sola nota. %s muestra sus 4 voces: el instrumento (<code>--</code>: voz sin usar, o 01 a 32), el desplazamiento (−24 a +24 semitonos; para la voz N, el periodo del ruido <code>BR00</code> a <code>BR1F</code>) y el volumen (<code>-</code>: el del instrumento, o 0 a 15)." % S("COUCHES DU SON S")),
            tr("Le même tableau s'affiche sous la grille du panneau MOTIF en mode son composé.", "The same table shows under the PATTERN grid in layered-sound mode.", "La misma tabla se ve bajo la rejilla del panel PATRON en modo sonido de 4 voces."),
            common_shot(p, "layered-sounds.png", "f3 f6"), ktable("f3 f6", srows))))
    # --- f4 SAMPLE ------------------------------------------------------------------------
    rows = [(sp, S("ECOUTER"), ("écouter le sample choisi (encore : arrêt)", "hear the chosen sample (again: stop)", "escuchar el sample elegido (otra vez: parar)")),
            (piano, S("HAUTEUR"), ("le sample plus aigu ou plus grave (±12 demi-tons)", "the sample higher or lower (±12 semitones)", "el sample más agudo o más grave (±12 semitonos)")),
            (K("↑/↓"), S("REGLAGE"), ("choisir un réglage : fréquence, décimation, bits, courbe", "pick a setting: frequency, decimation, bits, curve", "elegir un ajuste: frecuencia, decimación, bits, curva")),
            (K("←/→"), S("VALEUR"), ("changer sa valeur (avec SHIFT : la fréquence par 10)", "change its value (with SHIFT: the frequency by 10)", "cambiar su valor (con SHIFT: la frecuencia de 10 en 10)")),
            (K("CTRL", "←/→"), S("SAMPLE"), ("sample précédent / suivant", "previous / next sample", "sample anterior / siguiente")),
            (K("O"), S("f8 SAUVER f9 CHARGER O PRENDRE 1 SAMPLE"), ("prendre un sample dans une autre banque (16 samples et 16 Ko au plus)", "take a sample from another bank (16 samples and 16 KB at most)", "tomar un sample de otro banco (16 samples y 16 KB como máximo)")),
            (K("f8") + " / " + K("f9"), "", ("sauver la banque (réglages et samples ajoutés compris) / charger une autre banque <code>.SMP</code>", "save the bank (settings and added samples included) / load another <code>.SMP</code> bank", "grabar el banco (con ajustes y samples añadidos) / cargar otro banco <code>.SMP</code>"))]
    curves = [("LOG", ("le rendu fidèle", "the faithful rendering", "el resultado fiel")),
              ("LINEAIRE", ("plus creux et distordu", "hollower and distorted", "más hueco y distorsionado")),
              ("SATUREE ", ("le signal ×2,5, écrêté", "the signal ×2.5, clipped", "la señal ×2,5, recortada")),
              ("REPLIEE ", ("le signal ×2,5, replié", "the signal ×2.5, folded", "la señal ×2,5, plegada")),
              ("INVERSEE", ("la forme d'onde retournée", "the waveform flipped", "la onda al revés"))]
    out.append(section("f4", "f4 · SAMPLE",
        '%s<p>%s</p>\n%s%s<div class="callout"><p>%s</p></div>\n' % (
            common_shot(p, "sampler.png", "f4"),
            tr("La banque de samples à gauche (%s, %s), les %s du sample choisi à droite. La première fois que l'on ouvre SAMPLE, la banque <code>DRUMS.SMP</code> se charge toute seule. Ici, la banque du morceau STUDIO, avec la voix <code>SEQ16</code>." % (S("BANQUE :"), S("MEMOIRE:"), S("REGLAGES")),
               "The sample bank on the left (%s, %s), the chosen sample's %s on the right. The first time you open SAMPLE, the <code>DRUMS.SMP</code> bank loads by itself. Here, the STUDIO song's bank, with the <code>SEQ16</code> voice." % (S("BANQUE :"), S("MEMOIRE:"), S("REGLAGES")),
               "El banco de samples a la izquierda (%s, %s), los %s del sample elegido a la derecha. La primera vez que se abre SAMPLE, el banco <code>DRUMS.SMP</code> se carga solo. Aquí, el banco del tema STUDIO, con la voz <code>SEQ16</code>." % (S("BANQUE :"), S("MEMOIRE:"), S("REGLAGES"))),
            ktable("f4", rows),
            table(tr("Courbes", "Curves", "Curvas"), (S("COURBE"), tr("Effet", "Effect", "Efecto")), [(S(c), tr(*e)) for c, e in curves]),
            tr("<strong>Pendant une écoute, l'écran ne répond plus</strong> : le processeur ne fait que jouer le sample, interruptions coupées.",
               "<strong>While a sample plays, the screen does not respond</strong>: the processor does nothing but play the sample, with interrupts off.",
               "<strong>Mientras suena un sample, la pantalla no responde</strong>: el procesador solo toca el sample, con las interrupciones cortadas."))))
    # --- f5 DISQUE ------------------------------------------------------------------------
    rows = [(K("←/→") + " " + K("↑/↓"), S("CHOISIR"), ("choisir un fichier", "pick a file", "elegir un fichero")),
            (K("TAB"), S("TYPE"), ("type suivant : SNG, PAT, INS, SMP", "next type: SNG, PAT, INS, SMP", "tipo siguiente: SNG, PAT, INS, SMP")),
            (K("ENTER"), S("CHARGER"), ("charger le fichier dans son panneau, qui s'affiche", "load the file into its panel, which then shows", "cargar el fichero en su panel, que se muestra")),
            (K("DEL"), S("EFFACER"), ("effacer le fichier (deux fois)", "delete the file (twice)", "borrar el fichero (dos veces)")),
            (K("COPY"), S("RENOMMER"), ("renommer le fichier", "rename the file", "renombrar el fichero")),
            (K("N"), S("NOUVEAU"), ("nouveau morceau (deux fois)", "new song (twice)", "tema nuevo (dos veces)")),
            (K("C"), S("RELIRE"), ("relire la disquette (après en avoir changé)", "read the disk again (after changing it)", "releer el disco (después de cambiarlo)")),
            (sp, "", ("écouter le motif", "hear the pattern", "escuchar el patrón")),
            (K("f8"), S("SAUVER LE MORCEAU (.SNG)"), ("sauver le morceau", "save the song", "grabar el tema"))]
    out.append(section("f5", "f5 · " + tr("DISQUE, le catalogue", "DISK, the catalogue", "DISCO, el catálogo"),
        '<div class="split wide-left">\n<div>\n<p>%s</p>\n<p>%s</p>\n</div>\n%s</div>\n%s' % (
            tr("Le catalogue de la disquette, par type de fichier : morceaux, motifs, instruments, samples. En haut, la place libre et le nombre de fichiers ; sous la liste, le fichier choisi et le panneau où %s le charge." % K("ENTER"),
               "The disk catalogue, by file type: songs, patterns, instruments, samples. At the top, the free space and the number of files; under the list, the chosen file and the panel %s loads it into." % K("ENTER"),
               "El catálogo del disco, por tipo de fichero: temas, patrones, instrumentos, samples. Arriba, el espacio libre y el número de ficheros; bajo la lista, el fichero elegido y el panel en el que %s lo carga." % K("ENTER")),
            tr("<strong>Sauver avec %s</strong> (dans n'importe quel panneau) : tape le nom (8 lettres ou chiffres au plus) sur la ligne des messages, puis %s ; %s annule. Si le fichier existe déjà, un second %s le remplace." % (K("f8"), K("RETURN"), K("ESC"), K("RETURN")),
               "<strong>Saving with %s</strong> (in any panel): type the name (8 letters or digits at most) on the message line, then %s; %s cancels. If the file already exists, a second %s replaces it." % (K("f8"), K("RETURN"), K("ESC"), K("RETURN")),
               "<strong>Grabar con %s</strong> (en cualquier panel): escribe el nombre (8 letras o cifras como máximo) en la línea de mensajes y %s; %s cancela. Si el fichero ya existe, un segundo %s lo sustituye." % (K("f8"), K("RETURN"), K("ESC"), K("RETURN"))),
            common_shot(p, "disk.png", "f5"), ktable("f5", rows))))
    # --- FX -------------------------------------------------------------------------------
    what = [tr("la note glisse vers l'aigu", "the note slides up", "la nota sube"),
            tr("la note glisse vers le grave", "the note slides down", "la nota baja"),
            tr("la note, puis la note + x demi-tons", "the note, then the note + x semitones", "la nota y la nota + x semitonos"),
            tr("la note est rejouée toutes les x images (1/50 s)", "the note plays again every x frames (1/50 s)", "la nota se repite cada x imágenes (1/50 s)"),
            tr("la note est relâchée après x images", "the note is released after x frames", "la nota se suelta tras x imágenes"),
            tr("la note part x images après le pas", "the note starts x frames after the step", "la nota empieza x imágenes después del paso"),
            tr("vibrato de profondeur x", "vibrato of depth x", "vibrato de profundidad x")]
    out.append(section("fx", tr("Les effets des pas (FX)", "Per-step effects (FX)", "Los efectos por paso (FX)"),
        '<p>%s</p>\n%s<ol class="steps">\n<li>%s</li>\n<li>%s</li>\n</ol>\n%s<p>%s</p>\n' % (
            tr("Chaque case d'un motif peut porter un effet, noté en hexadécimal : le premier chiffre choisit l'effet, le second sa force x (0 à F) ; %s : aucun effet." % S("--"),
               "Every cell of a pattern can carry an effect, written in hexadecimal: the first digit picks the effect, the second its strength x (0 to F); %s: no effect." % S("--"),
               "Cada casilla de un patrón puede llevar un efecto, escrito en hexadecimal: la primera cifra elige el efecto, la segunda su fuerza x (0 a F); %s: ningún efecto." % S("--")),
            table("FX", ("FX", tr("Effet", "Effect", "Efecto"), tr("Ce qui se passe", "What happens", "Lo que pasa"), tr("Exemple", "Example", "Ejemplo")),
                  fx_rows(FX_FR, what)),
            tr("Sur le panneau MOTIF, mets le curseur sur la case, puis %s." % K("TAB"), "On the PATTERN panel, put the cursor on the cell, then %s." % K("TAB"), "En el panel PATRON, pon el cursor en la casilla y luego %s." % K("TAB")),
            tr("Va sur le FX avec %s (le chiffre de l'effet, puis celui de la force) et change-le avec %s : le nom de l'effet s'affiche sur la ligne des messages." % (K("→"), K("↑/↓")),
               "Move to the FX with %s (the effect digit, then the strength digit) and change it with %s: the effect's name shows on the message line." % (K("→"), K("↑/↓")),
               "Ve al FX con %s (la cifra del efecto y luego la de la fuerza) y cámbialo con %s: el nombre del efecto aparece en la línea de mensajes." % (K("→"), K("↑/↓"))),
            common_shot(p, "pattern-fx.png", "FX"),
            tr("En son composé, l'effet vaut pour toutes les voix du son ; REPETE, COUPE et RETARD marchent aussi sur la voix de bruit. COUPE sur un digidrum raccourcit le sample (52 sur un KICK : 40 ms au lieu de 148), ce qui fait perdre moins de pas à la musique. Le morceau ARCADE de la disquette de démonstration utilise les 7 effets.",
               "In layered sound, the effect applies to all the voices of the sound; REPEAT, CUT and DELAY also work on the noise voice. CUT on a digidrum shortens the sample (52 on a KICK: 40 ms instead of 148), so the music loses fewer steps. The ARCADE song on the demo disk uses all 7 effects.",
               "Con sonido de 4 voces, el efecto vale para todas las voces del sonido; REPITE, CORTA y DEMORA también funcionan en la voz de ruido. CORTA en un digidrum acorta el sample (52 en un KICK: 40 ms en vez de 148), y la música pierde menos pasos. El tema ARCADE del disco de demostración usa los 7 efectos."))))
    # --- fichiers et messages -------------------------------------------------------------
    files = [("<code>.SNG</code>", tr("tout le morceau : 32 motifs et leurs noms, 32 instruments, 8 sons composés, mixage, enchaînement, et la banque de samples utilisée", "the whole song: 32 patterns and their names, 32 instruments, 8 layered sounds, mixer, chain, and the sample bank it uses", "todo el tema: 32 patrones y sus nombres, 32 instrumentos, 8 sonidos, mezcla, encadenamiento, y el banco de samples que usa"), tr("SONG", "SONG", "TEMA") + ", " + tr("DISQUE", "DISK", "DISCO")),
             ("<code>.PAT</code>", tr("un motif seul : mode, tempo, 16 pas", "one pattern: mode, tempo, 16 steps", "un patrón solo: modo, tempo, 16 pasos"), tr("MOTIF", "PATTERN", "PATRON")),
             ("<code>.INS</code>", tr("32 instruments, leurs noms et les 8 sons composés", "32 instruments, their names and the 8 layered sounds", "32 instrumentos, sus nombres y los 8 sonidos"), "INST"),
             ("<code>.SMP</code>", tr("une banque de samples (16 au plus, 16 Ko au plus) et leurs réglages", "a sample bank (16 at most, 16 KB at most) and their settings", "un banco de samples (16 como máximo, 16 KB como máximo) y sus ajustes"), "SAMPLE")]
    msgs = [("MORCEAU ET BANQUE DE SAMPLES CHARGES", ("le morceau et sa banque de samples sont chargés", "the song and its sample bank are loaded", "el tema y su banco de samples están cargados")),
            ("ERREUR DISQUE (DISQUETTE ? NOM ?)", ("pas de disquette, ou pas de fichier de ce nom ; suivi du code d'erreur d'AMSDOS et du nombre d'octets lus", "no disk, or no file with that name; followed by the AMSDOS error code and the number of bytes read", "no hay disco, o no hay fichero con ese nombre; seguido del código de error de AMSDOS y del número de bytes leídos")),
            ("CE FICHIER N'EST PAS UN MORCEAU SEQ-16", ("le fichier n'est pas un <code>.SNG</code> de SEQ-16", "the file is not a SEQ-16 <code>.SNG</code>", "el fichero no es un <code>.SNG</code> de SEQ-16")),
            ("N A NOUVEAU : TOUT EFFACER ?", ("appuie encore sur N pour commencer un nouveau morceau", "press N again to start a new song", "pulsa N otra vez para empezar un tema nuevo")),
            ("DEL A NOUVEAU : EFFACER CE FICHIER", ("appuie encore sur DEL pour effacer le fichier", "press DEL again to delete the file", "pulsa DEL otra vez para borrar el fichero")),
            ("FLECHES PUIS RETURN (ESC : ANNULER)", ("une liste de fichiers est ouverte", "a file list is open", "hay una lista de ficheros abierta")),
            ("AUCUN FICHIER DE CE TYPE SUR LA DISQUETTE", ("aucun fichier du bon type sur la disquette", "no file of the right type on the disk", "ningún fichero del tipo buscado en el disco")),
            ("BANQUE TROP GRANDE POUR LA MEMOIRE", ("la banque <code>.SMP</code> ne tient pas en mémoire", "the <code>.SMP</code> bank does not fit in memory", "el banco <code>.SMP</code> no cabe en la memoria")),
            ("LA BANQUE A DEJA 16 SAMPLES", ("touche O de SAMPLE : la banque est pleine", "key O in SAMPLE: the bank is full", "tecla O en SAMPLE: el banco está lleno")),
            ("PAS ASSEZ DE MEMOIRE POUR LES SAMPLES", ("les samples et les digidrums sont désactivés ; le reste fonctionne", "samples and digidrums are disabled; everything else works", "los samples y los digidrums están desactivados; lo demás funciona"))]
    out.append(section("files", tr("Fichiers et messages", "Files and messages", "Ficheros y mensajes"),
        '%s<p>%s</p>\n<h3 id="messages">%s</h3>\n%s' % (
            table(tr("Fichiers", "Files", "Ficheros"), (tr("Fichier", "File", "Fichero"), tr("Contenu", "Content", "Contenido"), tr("Panneau", "Panel", "Panel")), files),
            tr("Un <code>.SNG</code> emporte sa banque de samples : on peut le copier sur une autre disquette sans rien oublier. Les morceaux des anciens formats se chargent toujours ; si un fichier du même nom existe, AMSDOS garde l'ancien sous l'extension <code>.BAK</code>.",
               "A <code>.SNG</code> carries its sample bank: you can copy it to another disk without forgetting anything. Songs in older formats still load; if a file with the same name exists, AMSDOS keeps the old one as <code>.BAK</code>.",
               "Un <code>.SNG</code> lleva consigo su banco de samples: se puede copiar a otro disco sin olvidar nada. Los temas de formatos antiguos se siguen cargando; si existe un fichero con el mismo nombre, AMSDOS guarda el antiguo como <code>.BAK</code>."),
            tr("Les messages", "Messages", "Los mensajes"),
            table(tr("Messages", "Messages", "Mensajes"), (tr("Message", "Message", "Mensaje"), tr("Signification", "Meaning", "Significado")),
                  [(S(m), tr(*w)) for m, w in msgs]))))
    # --- banques ---------------------------------------------------------------------------
    out.append(section("banks", tr("Les banques de sons", "Sound banks", "Los bancos de sonidos"),
        '<p>%s</p>\n<ul>\n<li>%s</li>\n<li>%s</li>\n</ul>\n<p class="note">%s</p>\n' % (
            tr("La disquette contient 13 banques d'instruments <code>.INS</code> (416 sons : batterie, basses, leads, nappes, arpèges, effets, buzzer, claviers, chiptune, percussions, glissés, bruits, et <code>USINE</code>, les instruments par défaut) et 8 banques de samples <code>.SMP</code> (<code>DRUMS</code>, <code>VOIX</code>, <code>BATTERI2</code>, <code>PERCUS</code>, <code>EFFETS</code>, <code>BASSES</code>, <code>NOTES</code>, <code>MOTS</code> ; la 9e, <code>CHIFFRES</code>, est sur <code>seq16-samples.dsk</code>).",
               "The disk holds 13 <code>.INS</code> instrument banks (416 sounds: drums, basses, leads, pads, arpeggios, effects, buzzer, keyboards, chiptune, percussion, slides, noises, and <code>USINE</code>, the default instruments) and 8 <code>.SMP</code> sample banks (<code>DRUMS</code>, <code>VOIX</code>, <code>BATTERI2</code>, <code>PERCUS</code>, <code>EFFETS</code>, <code>BASSES</code>, <code>NOTES</code>, <code>MOTS</code>; the 9th, <code>CHIFFRES</code>, is on <code>seq16-samples.dsk</code>).",
               "El disco trae 13 bancos de instrumentos <code>.INS</code> (416 sonidos: batería, bajos, melodías, colchones, arpegios, efectos, buzzer, teclados, chiptune, percusión, deslizados, ruidos, y <code>USINE</code>, los instrumentos por defecto) y 8 bancos de samples <code>.SMP</code> (<code>DRUMS</code>, <code>VOIX</code>, <code>BATTERI2</code>, <code>PERCUS</code>, <code>EFFETS</code>, <code>BASSES</code>, <code>NOTES</code>, <code>MOTS</code>; el 9.º, <code>CHIFFRES</code>, está en <code>seq16-samples.dsk</code>)."),
            tr("<strong>Instruments</strong> : panneau INST, %s charge une banque entière, %s prend un seul son, %s sauve ses instruments." % (K("f9"), K("O"), K("f8")),
               "<strong>Instruments</strong>: INST panel, %s loads a whole bank, %s takes a single sound, %s saves your instruments." % (K("f9"), K("O"), K("f8")),
               "<strong>Instrumentos</strong>: panel INST, %s carga un banco entero, %s toma un solo sonido, %s graba tus instrumentos." % (K("f9"), K("O"), K("f8"))),
            tr("<strong>Samples</strong> : panneau SAMPLE, %s charge une banque, %s prend un seul sample, %s sauve la banque." % (K("f9"), K("O"), K("f8")),
               "<strong>Samples</strong>: SAMPLE panel, %s loads a bank, %s takes a single sample, %s saves the bank." % (K("f9"), K("O"), K("f8")),
               "<strong>Samples</strong>: panel SAMPLE, %s carga un banco, %s toma un solo sample, %s graba el banco." % (K("f9"), K("O"), K("f8"))),
            tr("Tous les sons sont synthétisés ou dits par espeak : aucun échantillon venu d'Internet. Le détail de chaque banque est dans le <a href=\"%s\">README</a>." % GH,
               "Every sound is synthesized or spoken by espeak: no sample taken from the Internet. The details of each bank are in the <a href=\"%s\">README</a>." % GH,
               "Todos los sonidos están sintetizados o dichos por espeak: ningún sample sacado de Internet. El detalle de cada banco está en el <a href=\"%s\">README</a>." % GH))))
    # --- samples ---------------------------------------------------------------------------
    steps = [tr("<strong>Ouvrir le sampler</strong> : %s. La première fois, <code>DRUMS.SMP</code> se charge toute seule." % K("f4"), "<strong>Open the sampler</strong>: %s. The first time, <code>DRUMS.SMP</code> loads by itself." % K("f4"), "<strong>Abrir el sampler</strong>: %s. La primera vez, <code>DRUMS.SMP</code> se carga solo." % K("f4")),
             tr("<strong>Écouter</strong> : %s choisit un sample, %s le joue ; les touches du piano le jouent plus aigu ou plus grave." % (K("CTRL", "←/→"), sp), "<strong>Listen</strong>: %s picks a sample, %s plays it; the piano keys play it higher or lower." % (K("CTRL", "←/→"), sp), "<strong>Escuchar</strong>: %s elige un sample, %s lo toca; las teclas del piano lo tocan más agudo o más grave." % (K("CTRL", "←/→"), sp)),
             tr("<strong>Salir le son</strong> : %s choisit un réglage, %s change sa valeur ; réécoute après chaque changement." % (K("↑/↓"), K("←/→")), "<strong>Dirty the sound</strong>: %s picks a setting, %s changes its value; listen again after each change." % (K("↑/↓"), K("←/→")), "<strong>Ensuciar el sonido</strong>: %s elige un ajuste, %s cambia su valor; vuelve a escuchar después de cada cambio." % (K("↑/↓"), K("←/→"))),
             tr("<strong>Changer de banque</strong> : %s, flèches, %s." % (K("f9"), K("RETURN")), "<strong>Change bank</strong>: %s, arrows, %s." % (K("f9"), K("RETURN")), "<strong>Cambiar de banco</strong>: %s, flechas, %s." % (K("f9"), K("RETURN"))),
             tr("<strong>Ajouter un sample</strong> d'une autre banque : %s, la banque, puis le sample." % K("O"), "<strong>Add a sample</strong> from another bank: %s, the bank, then the sample." % K("O"), "<strong>Añadir un sample</strong> de otro banco: %s, el banco y luego el sample." % K("O")),
             tr("<strong>Sauver la banque</strong>, avec ses réglages : %s." % K("f8"), "<strong>Save the bank</strong>, with its settings: %s." % K("f8"), "<strong>Grabar el banco</strong>, con sus ajustes: %s." % K("f8")),
             tr("<strong>Fabriquer ses propres sons</strong> sur le PC à partir de WAV, avec l'onglet SAMPLES SEQ-16 de <a href=\"%s#pc\">CPC DISK</a> ou <code>tools/wav2smp.py</code>." % home_url, "<strong>Make your own sounds</strong> on the PC from WAVs, with the SAMPLES SEQ-16 tab of <a href=\"%s#pc\">CPC DISK</a> or <code>tools/wav2smp.py</code>." % home_url, "<strong>Fabricar tus propios sonidos</strong> en el PC a partir de WAV, con la pestaña SAMPLES SEQ-16 de <a href=\"%s#pc\">CPC DISK</a> o <code>tools/wav2smp.py</code>." % home_url)]
    out.append(section("samples", tr("Les samples, pas à pas", "Samples, step by step", "Los samples, paso a paso"),
        '<p>%s</p>\n<ol class="steps">\n%s</ol>\n<div class="callout"><p>%s</p></div>\n' % (
            tr("Le CPC n'a pas de convertisseur numérique-analogique : il joue un sample en changeant très vite le volume d'une voie de l'AY, sur 16 niveaux. C'est ce qui donne le grain, et la dégradation est recherchée.",
               "The CPC has no digital-to-analogue converter: it plays a sample by changing the volume of an AY channel very fast, on 16 levels. That is where the grain comes from, and the degradation is the goal.",
               "El CPC no tiene convertidor digital-analógico: toca un sample cambiando muy rápido el volumen de un canal del AY, en 16 niveles. De ahí sale el grano, y la degradación es lo que se busca."),
            "".join("<li>%s</li>\n" % x for x in steps),
            tr("Une banque fait 16 Ko au plus (environ 4 secondes à 8 kHz) et contient 16 sons au plus.", "A bank holds 16 KB at most (about 4 seconds at 8 kHz) and 16 sounds at most.", "Un banco ocupa 16 KB como máximo (unos 4 segundos a 8 kHz) y contiene 16 sonidos como máximo."))))
    # --- digidrums -------------------------------------------------------------------------
    out.append(section("digidrums", tr("Les digidrums : des samples dans le morceau", "Digidrums: samples in the song", "Los digidrums: samples en el tema"),
        '<p>%s</p>\n<ol class="steps">\n<li>%s</li>\n<li>%s</li>\n<li>%s</li>\n</ol>\n<p>%s</p>\n<div class="callout"><p>%s</p></div>\n' % (
            tr("Un digidrum est un instrument qui joue un sample de la banque chargée au lieu d'une note. Les instruments d'usine 29 à 32 jouent les 4 sons de <code>DRUMS.SMP</code>.", "A digidrum is an instrument that plays a sample from the loaded bank instead of a note. Factory instruments 29 to 32 play the 4 sounds of <code>DRUMS.SMP</code>.", "Un digidrum es un instrumento que toca un sample del banco cargado en vez de una nota. Los instrumentos de fábrica 29 a 32 tocan los 4 sonidos de <code>DRUMS.SMP</code>."),
            tr("Panneau INST : mets %s à %s." % (S("DIGIDRUM"), S("OUI")), "INST panel: set %s to %s." % (S("DIGIDRUM"), S("OUI")), "Panel INST: pon %s en %s." % (S("DIGIDRUM"), S("OUI"))),
            tr("La ligne %s devient %s : choisis le numéro du sample (0 = le premier)." % (S("PERIODE"), S("SAMPLE")), "The %s line becomes %s: pick the sample number (0 = the first one)." % (S("PERIODE"), S("SAMPLE")), "La línea %s pasa a ser %s: elige el número del sample (0 = el primero)." % (S("PERIODE"), S("SAMPLE"))),
            tr("Le %s règle sa force. Pose-le comme une note : le DO de l'octave 4 le joue à sa hauteur d'origine, ±12 demi-tons." % S("VOLUME"), "%s sets its strength. Put it like a note: C in octave 4 plays it at its original pitch, ±12 semitones." % S("VOLUME"), "El %s ajusta su fuerza. Ponlo como una nota: el DO de la octava 4 lo toca a su altura original, ±12 semitonos." % S("VOLUME")),
            tr("La voix choisit la voie de l'AY (sur la voix N : la voie C) ; une voix muette ne joue pas ses digidrums.", "The voice picks the AY channel (on voice N: channel C); a muted voice does not play its digidrums.", "La voz elige el canal del AY (en la voz N: el canal C); una voz silenciada no toca sus digidrums."),
            tr("<strong>Un sample prend tout le processeur.</strong> Pendant qu'il joue, l'écran ne répond plus, le séquenceur s'arrête et les autres voix sont gelées ; ensuite, le tempo est rattrapé. Avec des sons courts (moins de 150 ms) cela ne s'entend presque pas ; un sample long coupe les autres sons le temps qu'il joue. Changer de sample (ou de hauteur, ou de volume) demande aussi de préparer ses tables, jusqu'à environ 300 ms.",
               "<strong>A sample takes the whole processor.</strong> While it plays, the screen does not respond, the sequencer stops and the other voices are frozen; afterwards, the tempo is caught up. With short sounds (under 150 ms) you can hardly hear it; a long sample cuts the other sounds while it plays. Changing sample (or pitch, or volume) also means preparing its tables, up to about 300 ms.",
               "<strong>Un sample ocupa todo el procesador.</strong> Mientras suena, la pantalla no responde, el secuenciador se para y las otras voces se congelan; después, se recupera el tempo. Con sonidos cortos (menos de 150 ms) casi no se nota; un sample largo corta los demás sonidos mientras suena. Cambiar de sample (o de altura, o de volumen) también obliga a preparar sus tablas, hasta unos 300 ms."))))
    # --- limites ---------------------------------------------------------------------------
    lim = [tr("<strong>Un CPC 6128 est nécessaire</strong> : les motifs sont rangés dans la mémoire supplémentaire.", "<strong>A CPC 6128 is required</strong>: the patterns are kept in the extra memory.", "<strong>Hace falta un CPC 6128</strong>: los patrones se guardan en la memoria adicional."),
           tr("<strong>Les banques de samples</strong> tiennent dans 16 064 octets (environ 4 secondes à 8 kHz), 16 samples au plus.", "<strong>Sample banks</strong> must fit in 16,064 bytes (about 4 seconds at 8 kHz), 16 samples at most.", "<strong>Los bancos de samples</strong> caben en 16.064 bytes (unos 4 segundos a 8 kHz), 16 samples como máximo."),
           tr("<strong>La liste des fichiers</strong> ne fonctionne que sur le lecteur A.", "<strong>The file list</strong> only works on drive A.", "<strong>La lista de ficheros</strong> solo funciona en la unidad A."),
           tr("<strong>Le firmware écrit lentement</strong> (environ 3,5 ms par caractère) : un écran complet met plus d'une seconde à se dessiner, mais la musique continue à l'heure pendant ce temps.", "<strong>The firmware writes slowly</strong> (about 3.5 ms per character): a full screen takes more than a second to draw, but the music keeps time meanwhile.", "<strong>El firmware escribe despacio</strong> (unos 3,5 ms por carácter): una pantalla completa tarda más de un segundo en dibujarse, pero la música sigue a tiempo mientras tanto."),
           tr("<strong>Un « toc »</strong> au début ou à la fin d'un sample est possible.", "<strong>A small \"click\"</strong> at the start or end of a sample is possible.", "<strong>Un pequeño «toc»</strong> al principio o al final de un sample es posible.")]
    todo = [tr("renommer les instruments ;", "renaming instruments;", "renombrar los instrumentos;"),
            tr("le copier-coller de blocs de pas ;", "copy / paste of step blocks;", "copiar / pegar bloques de pasos;"),
            tr("samples : tables gardées dans la mémoire supplémentaire, mode HACHÉ, finitions du panneau SAMPLE.", "samples: tables kept in the extra memory, CHOPPED mode, SAMPLE panel finishing touches.", "samples: tablas guardadas en la memoria adicional, modo TROCEADO, retoques del panel SAMPLE.")]
    out.append(section("limits", tr("Limites connues", "Known limits", "Límites conocidos"),
        '<ul>\n%s</ul>\n<h3 id="roadmap">%s</h3>\n<ul>\n%s</ul>\n<p>%s</p>\n' % (
            "".join("<li>%s</li>\n" % x for x in lim), tr("Pas encore là", "Not there yet", "Todavía no"),
            "".join("<li>%s</li>\n" % x for x in todo),
            tr("Les notes techniques complètes sont dans le <a href=\"%s\">README du dépôt</a>." % GH, "The full technical notes are in the <a href=\"%s\">repository README</a>." % GH, "Las notas técnicas completas están en el <a href=\"%s\">README del repositorio</a>." % GH))))
    return "".join(out)


def manual_main(p, home_url):
    return manual(p, home_url)



def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def pages():
    """{chemin : texte} des six pages, recalculées à partir des fichiers."""
    global L
    out = {}
    for code, (home_path, man_path, p) in PAGES.items():
        L = code
        home_file, man_file = os.path.join(ROOT, home_path), os.path.join(ROOT, man_path)
        man_url = os.path.basename(man_path) if code == "en" else "../%s/%s" % (code, os.path.basename(man_path))
        home_url = "index.html" if code == "en" else "../%s/index.html" % code
        t = T[code]
        s = home(home_file, p, man_url)
        s = re.sub(r'<ul class="nav" id="nav">.*?</ul>', lambda m: nav(t["nav_home"], home_url, man_url), s, count=1)
        s = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*(">)',
                   lambda m: m.group(1) + html.escape(t["desc"], quote=True) + m.group(2), s)
        s = re.sub(r'(<meta property="og:image:alt" content=")[^"]*(">)',
                   lambda x: x.group(1) + html.escape(t["og_alt"], quote=True) + x.group(2), s)
        out[home_path] = s
        m = open(man_file, encoding="utf-8").read()
        m = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*(">)',
                   lambda x: x.group(1) + html.escape(t["man_desc"], quote=True) + x.group(2), m)
        m = re.sub(r'(<meta property="og:image:alt" content=")[^"]*(">)',
                   lambda x: x.group(1) + html.escape(t["og_alt"], quote=True) + x.group(2), m)
        m = re.sub(r'<title>[^<]*</title>', lambda x: "<title>%s</title>" % html.escape(t["man_title"]), m, count=1)
        m = re.sub(r'(<meta property="og:title" content=")[^"]*(">)',
                   lambda x: x.group(1) + html.escape(t["man_title"], quote=True) + x.group(2), m)
        m = re.sub(r'<main id="main" tabindex="-1">.*?</main>',
                   lambda x: '<main id="main" tabindex="-1">\n\n%s</main>' % manual_main(p, home_url), m, count=1, flags=re.S)
        m = re.sub(r'<ul class="nav" id="nav">.*?</ul>', lambda x: nav(t["nav_man"], home_url, man_url), m, count=1)
        out[man_path] = m
    return out


def main():
    import shutil                          # l'aperçu des réseaux sociaux : SONG
    shutil.copy(os.path.join(ROOT, "snapshots", "en", "01_song.png"),
                os.path.join(ROOT, "docs", "assets", "img", "og-seq16.png"))
    for path, text in pages().items():
        write(os.path.join(ROOT, path), text)
        print("OK :", path)


if __name__ == "__main__":
    main()
