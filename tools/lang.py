"""lang.py : SEQ-16 en anglais et en espagnol.

Le source (src/*.asm) est écrit en français. Ce script en fait une copie
par langue dans build/lang/<code>/, où chaque texte affiché est remplacé
par sa traduction, puis l'assemble et fabrique la disquette de la langue :

    build/seq16.dsk       français (build.bat)
    build/seq16-en.dsk    anglais
    build/seq16-es.dsk    espagnol

Règle : une traduction n'est jamais plus longue que le texte français ;
elle est complétée par des espaces jusqu'à la même longueur. Le programme
a donc exactement la même taille et les mêmes adresses dans les trois
langues (la mémoire du CPC est pleine, et les textes sont placés à des
colonnes fixes de l'écran). Les touches (S, L, O…), les noms de fichiers
et les signatures ne sont pas traduits.

Le jeu de caractères du CPC n'a pas de lettres accentuées : l'espagnol
est écrit en majuscules sans accents (ANADIDO pour AÑADIDO).

    python tools/lang.py --check               vérifie les traductions
    python tools/lang.py en es --rasm tools\\rasm.exe
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGS = ("en", "es")

# Français -> (anglais, espagnol). L'ordre suit l'écran.
TEXTS = {
    # --- onglets et écran f1 (séquenceur) ---
    "PAS": ("STP", "PAS"),
    "ESPACE": ("SPACE", "ESPAC."),
    "LIRE": ("PLAY", "TOCA"),
    "MODE": ("MODE", "MODO"),
    "MUET": ("MUTE", "MUDO"),
    "ARRET": ("STOP", "PARAR"),
    "OCTAVE": ("OCTAVE", "OCTAVA"),
    "MOTIF": ("PATT.", "PATR."),
    "SAUVER": ("SAVE", "GRABAR"),
    "1 FOIS": ("ONCE", "1 VEZ"),
    "SANS EFFET": ("NO EFFECT", "SIN EFECTO"),
    "MONTE": ("UP", "SUBE"),
    "DESCEND": ("DOWN", "BAJA"),
    "ARPEGE": ("ARPEG.", "ARPEG."),
    "REPETE": ("REPEAT", "REPITE"),
    "COUPE": ("CUT", "CORTA"),
    "RETARD": ("DELAY", "DEMORA"),
    "VIBRATO": ("VIBRATO", "VIBRATO"),
    "SON COMPOSE  ": ("LAYERED SOUND", "SONIDO 4 VOC."),
    "LECTURE": ("PLAY", "TOCAR"),
    "ARRET  ": ("STOP", "PARAR"),
    "SON   :": ("SOUND :", "SONIDO:"),
    "MUET ": ("MUTE ", "MUDO "),
    # --- écran f2 (instrument) ---
    "OUI ": ("YES ", "SI  "),
    "NON ": ("NO  ", "NO  "),
    "ATTAQUE        ": ("ATTACK", "ATAQUE"),
    "DECLIN         ": ("DECAY", "CAIDA"),
    "TENUE          ": ("SUSTAIN", "SOSTEN"),
    "RELACHE        ": ("RELEASE", "LIBERACION"),
    "VOLUME         ": ("VOLUME", "VOLUMEN"),
    "TON            ": ("TONE", "TONO"),
    "BRUIT          ": ("NOISE", "RUIDO"),
    "  PERIODE      ": ("  PERIOD", "  PERIODO"),
    "ENV. MATERIELLE": ("HARDWARE ENV.", "ENV. HARDWARE"),
    "  FORME        ": ("  SHAPE", "  FORMA"),
    "  DIVISION     ": ("  DIVIDER", "  DIVISION"),
    "ARPEGE NOTE 2  ": ("ARPEGGIO NOTE 2", "ARPEGIO NOTA 2"),
    "ARPEGE NOTE 3  ": ("ARPEGGIO NOTE 3", "ARPEGIO NOTA 3"),
    "  VITESSE      ": ("  SPEED", "  VELOCIDAD"),
    "VIBRATO PROF.  ": ("VIBRATO DEPTH", "VIBRATO PROF."),
    "  ATTENTE      ": ("  DELAY", "  ESPERA"),
    "INSTRUMENT :": ("INSTRUMENT :", "INSTRUMENTO:"),
    "ENVELOPPE": ("ENVELOPE", "ENVOLV."),
    "TOUCHE TENUE": ("KEY HELD", "TECLA ABAJO"),
    "PUIS LACHEE": ("THEN LET GO", "Y SOLTADA"),
    "REGLAGE": ("SETTING", "AJUSTE"),
    "VALEUR": ("VALUE", "VALOR"),
    "PAR 10": ("BY 10", "POR 10"),
    "ESSAI": ("TRY", "OIR"),
    "COPIER": ("COPY", "COPIAR"),
    "COLLER": ("PASTE", "PEGAR"),
    "SON BANQUE": ("BANK SOUND", "SON. BANCO"),
    "SON": ("SND", "SON"),
    "INSTRUMENT COPIE (P : COLLER)": ("INSTRUMENT COPIED (P: PASTE)", "INSTRUMENTO COPIADO (P:PEGAR)"),
    "INSTRUMENT COLLE": ("INSTR. PASTED", "INSTR. PEGADO"),
    "RIEN A COLLER : COPY D'ABORD": ("NOTHING TO PASTE: COPY FIRST", "NADA QUE PEGAR: COPY ANTES"),
    "SONS DE LA BANQUE": ("SOUNDS IN BANK", "SONIDOS DEL BANCO"),
    "SON PRIS DANS LA BANQUE": ("SOUND TAKEN FROM BANK", "SONIDO TOMADO DEL BANCO"),
    # --- écran f3 (mixage et disque) ---
    "MIXAGE": ("MIXER", "MEZCLA"),
    "DISQUE": ("DISK", "DISCO"),
    "CHARGER": ("LOAD", "CARGAR"),
    "NOUVEAU": ("NEW", "NUEVO"),
    "ESC MAINTENUE 1 SECONDE : QUITTER": ("HOLD ESC 1 SECOND: QUIT", "ESC PULSADA 1 SEGUNDO: SALIR"),
    " VOIX ": ("VOICE ", " VOZ  "),
    "MORCEAU1": ("SONG1", "TEMA1"),
    "TAPE LE NOM, PUIS RETURN": ("TYPE NAME, THEN RETURN", "NOMBRE, LUEGO RETURN"),
    "SAUVEGARDE EN COURS...": ("SAVING...", "GRABANDO..."),
    "MORCEAU SAUVE": ("SONG SAVED", "TEMA GRABADO"),
    "CHARGEMENT EN COURS...": ("LOADING...", "CARGANDO..."),
    "MORCEAU CHARGE": ("SONG LOADED", "TEMA CARGADO"),
    "ERREUR DISQUE (DISQUETTE ? NOM ?)": ("DISK ERROR (DISK? NAME?)", "ERROR DE DISCO (DISCO? NOMBRE?)"),
    "SEQ-16 : IL FAUT UN CPC 6128": ("SEQ-16 NEEDS A CPC 6128", "SEQ-16 NECESITA UN CPC 6128"),
    "CE FICHIER N'EST PAS UN MORCEAU SEQ-16": ("THIS FILE IS NOT A SEQ-16 SONG", "ESTE FICHERO NO ES UN TEMA SEQ-16"),
    "DONNE D'ABORD UN NOM (RETURN)": ("ENTER A NAME FIRST (RETURN)", "PRIMERO UN NOMBRE (RETURN)"),
    "N A NOUVEAU : TOUT EFFACER ?": ("N AGAIN: ERASE EVERYTHING?", "N OTRA VEZ: BORRAR TODO?"),
    "NOUVEAU MORCEAU": ("NEW SONG", "TEMA NUEVO"),
    "PAS ASSEZ DE MEMOIRE": ("NOT ENOUGH MEMORY", "MEMORIA INSUFICIENTE"),
    "MOTIF SAUVE (.PAT)": ("PATTERN SAVED", "PATRON GRABADO"),
    "MOTIF CHARGE": ("PATT. LOADED", "PATRON LEIDO"),
    "CE FICHIER N'EST PAS UN MOTIF .PAT": ("THIS FILE IS NOT A .PAT PATTERN", "ESTE FICHERO NO ES UN PATRON .PAT"),
    "INSTRUMENTS SAUVES (.INS)": ("INSTRUMENTS SAVED (.INS)", "INSTRUMENTOS GRABADOS"),
    "INSTRUMENTS CHARGES": ("INSTRUMENTS LOADED", "INSTRUM. CARGADOS"),
    "CE FICHIER N'EST PAS UNE BANQUE .INS": ("THIS FILE IS NOT AN .INS BANK", "ESTE FICHERO NO ES UN BANCO .INS"),
    "BANQUE DE SAMPLES SAUVEE (.SMP)": ("SAMPLE BANK SAVED (.SMP)", "BANCO DE SAMPLES GRABADO"),
    "MORCEAU ET BANQUE DE SAMPLES CHARGES": ("SONG AND SAMPLE BANK LOADED", "TEMA Y BANCO DE SAMPLES CARGADOS"),
    "MORCEAU CHARGE (BANQUE .SMP ABSENTE)": ("SONG LOADED (.SMP BANK MISSING)", "TEMA CARGADO (FALTA EL .SMP)"),
    # --- écran f4 (sampler) ---
    "BANQUE :": ("BANK   :", "BANCO  :"),
    "MEMOIRE:": ("MEMORY :", "MEMORIA:"),
    "N  NOM   DUREE": ("N  NAME  TIME", "N  NOMB. DUR."),
    "REGLAGES": ("SETTINGS", "AJUSTES"),
    "FREQUENCE": ("FREQUENCY", "FRECUENC."),
    "DECIMATION": ("DECIMATION", "DECIMACION"),
    "COURBE": ("CURVE", "CURVA"),
    "PERIODE": ("PERIOD", "PERIODO"),
    "ECOUTER": ("LISTEN", "ESCUCHA"),
    "HAUTEUR": ("PITCH", "ALTURA"),
    "f8 SAUVER f9 CHARGER O PRENDRE 1 SAMPLE": ("f8 SAVE  f9 LOAD   O TAKE 1 SAMPLE", "f8 GRABAR f9 CARGAR O TOMAR 1 SAMPLE"),
    "CHARGEMENT DE DRUMS.SMP...": ("LOADING DRUMS.SMP...", "CARGANDO DRUMS.SMP..."),
    "BANQUE CHARGEE": ("BANK LOADED", "BANCO CARGADO"),
    "BANQUE TROP GRANDE POUR LA MEMOIRE": ("BANK TOO BIG FOR MEMORY", "BANCO DEMASIADO GRANDE"),
    "CE FICHIER N'EST PAS UNE BANQUE .SMP": ("THIS FILE IS NOT AN .SMP BANK", "ESTE FICHERO NO ES UN BANCO .SMP"),
    "AUCUNE BANQUE : f9 POUR EN CHARGER": ("NO BANK: f9 TO LOAD ONE", "SIN BANCO: f9 PARA CARGAR UNO"),
    # panneaux (lot 2) : un seul texte pour les 5 onglets, '|' = début d'onglet
    "|1SONG|2MOTIF|3INST|4SAMPLE|5DISQUE": ("|1SONG|2PATTERN|3INST|4SAMPLE|5DISK", "|1TEMA|2PATRON|3INST|4SAMPLE|5DISCO"),
    "FICHIER :": ("FILE :", "FICHERO:"),
    "DEJA SUR LA DISQUETTE : RETURN REMPLACE": ("ALREADY ON DISK: RETURN REPLACES IT", "YA EN EL DISCO: RETURN LO REEMPLAZA"),
    # panneau MOTIF (lot 3) : grille de 16 pas, panneau de la note, pinceau
    "SON": ("LAY", "SON"),
    " PAS ": (" STP ", " PAS "),
    "VOIX ": ("LANE ", "VOZ  "),
    " EDITION ": (" EDITING ", " EDICION "),
    "NOTE:": ("NOTE:", "NOTA:"),
    "SON:": ("LAY:", "SON:"),
    "VERROU": ("LOCKED", "BLOQ. "),
    "COUCHES DU SON S": ("LAYERS, SOUND S", "CAPAS DEL SON S"),
    "   VOIX INSTRUMENT  DECAL. VOL": ("   LANE INSTRUMENT  SHIFT  VOL", "   VOZ  INSTRUMENTO DESPL. VOL"),
    "MOTIF:": ("PATT.:", "PATR.:"),
    "PINCEAU": ("BRUSH", "PINCEL"),
    "PAS/VOIX": ("STP/LANE", "PASO/VOZ"),
    "VIDER": ("CLEAR", "VACIA"),
    "NOTE": ("NOTE", "NOTA"),
    "PRENDRE": ("PICK", "TOMAR"),
    "EDITER": ("EDIT", "EDITAR"),
    # panneau SONG (lot 4) : l'enchaînement des motifs
    "MOTIF-": ("PATT-", "PATR-"),
    # panneau DISQUE (lot 5)
    "DISQUE :": ("DISK :", "DISCO :"),
    "TYPE": ("TYPE", "TIPO"),
    "CHOISIR": ("CHOOSE", "ELEGIR"),
    "EFFACER": ("DELETE", "BORRAR"),
    "RENOMMER": ("RENAME", "RENOMBRA"),
    "SAUVER LE MORCEAU (.SNG)": ("SAVE THE SONG (.SNG)", "GRABAR EL TEMA (.SNG)"),
    "1 SECONDE : QUITTER": ("1 SECOND: QUIT", "1 SEGUNDO: SALIR"),
    "  ENTER : DANS ": ("  ENTER: INTO ", "  ENTER: EN "),
    "K LIBRES  ": ("K FREE  ", "K LIBRES  "),
    " FICHIERS": (" FILES", " FICHEROS"),
    "DEL A NOUVEAU : EFFACER CE FICHIER": ("DEL AGAIN: DELETE THIS FILE", "DEL OTRA VEZ: BORRAR EL FICHERO"),
    "FICHIER EFFACE": ("FILE DELETED", "BORRADO"),
    "FICHIER RENOMME": ("FILE RENAMED", "FICHERO RENOMB."),
    "RELIRE": ("RELOAD", "RELEER"),
    "SONG:": ("SONG:", "TEMA:"),
    "POS MOTIF       REP TR. APERCU": ("POS PATTERN     REP TR. VIEW", "POS PATRON      REP TR. VISTA"),
    "DUREE": ("TIME", "DURAC"),
    "POSITIONS": ("POSITIONS", "POSICION."),
    "POSITION": ("POSITION", "POSICION"),
    "CHAMP": ("FIELD", "CAMPO"),
    "INSERER": ("INSERT", "INSERTA"),
    "OTER": ("CUT", "QUIT"),
    "DOUBLER": ("DOUBLE", "DUPLICA"),
    "BOUCLE": ("LOOP", "BUCLE"),
    "LECTURE SONG ": ("PLAY SONG", "TOCA TEMA"),
    "LECTURE MOTIF": ("PLAY PATTERN", "TOCA PATRON"),
    "ARRET        ": ("STOP", "PARADO"),
    "-- FIN : RETOUR EN ": ("-- END: BACK TO", "-- FIN: VUELTA A"),
    "-- FIN : ARRET --       ": ("-- END: STOP --", "-- FIN: PARAR --"),
    "MESURES": ("BARS", "COMPAS."),
    "64 POSITIONS AU PLUS": ("64 POSITIONS AT MOST", "MAXIMO 64 POSICIONES"),
    "ECOUTE... (ESPACE : ARRET)": ("PLAYING... (SPACE: STOP)", "SONANDO (ESPACIO: PARAR)"),
    "PAS ASSEZ DE MEMOIRE POUR LES SAMPLES": ("NOT ENOUGH MEMORY FOR SAMPLES", "MEMORIA INSUFICIENTE PARA SAMPLES"),
    "LECTURE DU CATALOGUE...": ("READING CATALOG...", "LEYENDO CATALOGO..."),
    "CATALOGUE ILLISIBLE (AMSDOS ABSENT ?)": ("CATALOG UNREADABLE (NO AMSDOS?)", "CATALOGO ILEGIBLE (SIN AMSDOS?)"),
    "AUCUN FICHIER DE CE TYPE SUR LA DISQUETTE": ("NO FILE OF THIS TYPE ON THE DISK", "NINGUN FICHERO DE ESTE TIPO EN EL DISCO"),
    "FLECHES PUIS RETURN (ESC : ANNULER)": ("ARROWS THEN RETURN (ESC: CANCEL)", "FLECHAS Y RETURN (ESC: CANCELAR)"),
    "LA BANQUE A DEJA 16 SAMPLES": ("BANK ALREADY HAS 16 SAMPLES", "BANCO LLENO (16 SAMPLES)"),
    "SAMPLE AJOUTE A LA BANQUE": ("SAMPLE ADDED TO BANK", "SAMPLE ANADIDO AL BANCO"),
    # --- courbes des samples (smptables.asm, 8 caractères) ---
    "LINEAIRE": ("LINEAR", "LINEAL"),
    "SATUREE ": ("CLIPPED", "SATURADA"),
    "REPLIEE ": ("FOLDED", "PLEGADA"),
    "INVERSEE": ("INVERTED", "INVERSA"),
}

# Textes à laisser tels quels : signatures de fichiers, extensions, noms de
# fichiers, touches, unités, mots identiques dans les trois langues.
KEEP = {
    "SEQ16", "SQ16", "SQSM", ".SNG", ".INS", ".SMP", ".PAT", "DRUMS.SMP", "DRUMS   ",
    "ABCN", "4321", "C-C#D-D#E-F-F#G-G#A-A#B-", "--------", "------",
    "INSTR.:", "INSTR.", "OCT:", "BPM:",
    "SHIFT ", "CTRL  ", "COPY", "RETURN", "DEL", "TAB", "CAPS", "PIANO",
    "f5", "f6", "f7", "f8", "f9", "MS", " HZ", " NOP", " BITS ", "BITS", "SAMPLE", "LOG     ",
    "  SAMPLE ", "  SAMPLE       ", "GLISSANDO      ", "PORTAMENTO     ",
    "DIGIDRUM       ", "-       ",
    "CDEFGAB", "OCT", "INS:", "VOL:", "FX:", "ENTER", "ON/OFF", "CLR", "SHIFT", "CTRL",
    "BPM", "INS", "---  ", "f8 f9", " --", "ER", "RE", "ESC",
}

_QUOTED = re.compile(r'"([^"]*)"')
_DB = re.compile(r"\b(db|defb|defm)\b", re.I)


def _code_part(line):
    """La partie code d'une ligne (sans le commentaire ; hors guillemets)."""
    quoted = False
    for i, ch in enumerate(line):
        if ch == '"':
            quoted = not quoted
        elif ch == ";" and not quoted:
            return line[:i], line[i:]
    return line, ""


def texts_in_source():
    """{texte: [fichier:ligne]} pour tous les textes des lignes db."""
    found = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "src", "*.asm"))):
        with open(path, encoding="latin-1") as fh:
            for n, line in enumerate(fh, 1):
                code, _ = _code_part(line)
                if not _DB.search(code):
                    continue
                for m in _QUOTED.finditer(code):
                    found.setdefault(m.group(1), []).append(f"{os.path.basename(path)}:{n}")
    return found


def problems():
    """Liste des erreurs de traduction (vide si tout va bien)."""
    errs = []
    src = texts_in_source()
    for fr, trans in TEXTS.items():
        if fr not in src:
            errs.append(f"texte absent du source : {fr!r}")
        for code, tr in zip(LANGS, trans):
            if len(tr) > len(fr):
                errs.append(f"{code} trop long ({len(tr)} > {len(fr)}) : {fr!r} -> {tr!r}")
            if '"' in tr or any(ord(c) > 126 for c in tr):
                errs.append(f"{code} caractère interdit : {tr!r}")
    for fr, locs in src.items():
        if fr in TEXTS or fr in KEEP:
            continue
        if not any(c.isalpha() for c in fr) or len(fr.strip()) <= 1:
            continue           # touches (S, L…), blancs, séparateurs
        errs.append(f"texte non traduit : {fr!r} ({', '.join(locs[:2])})")
    return errs


def translate_line(line, idx):
    code, comment = _code_part(line)
    if not _DB.search(code):
        return line

    def sub(m):
        fr = m.group(1)
        if fr in TEXTS:
            return '"' + TEXTS[fr][idx].ljust(len(fr)) + '"'
        return m.group(0)
    return _QUOTED.sub(sub, code) + comment


def make_source(code):
    """Copie traduite de src/ dans build/lang/<code>/ ; renvoie main.asm."""
    idx = LANGS.index(code)
    out = os.path.join(ROOT, "build", "lang", code)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    for path in glob.glob(os.path.join(ROOT, "src", "*.asm")):
        with open(path, encoding="latin-1") as fh:
            lines = [translate_line(line, idx) for line in fh]
        text = "".join(lines).replace("'build/seq16.dsk'", f"'build/seq16-{code}.dsk'")
        with open(os.path.join(out, os.path.basename(path)), "w", encoding="latin-1") as fh:
            fh.write(text)
    return os.path.join(out, "main.asm")


BANKS = (
    ["samples/" + n for n in ("DRUMS.SMP", "VOIX.SMP", "BATTERI2.SMP", "PERCUS.SMP",
                              "EFFETS.SMP", "BASSES.SMP", "NOTES.SMP", "CHIFFRES.SMP",
                              "MOTS.SMP")]
    + ["instruments/" + n for n in ("USINE.INS", "BATTERIE.INS", "BASSES.INS", "LEADS.INS",
                                    "NAPPES.INS", "ARPEGES.INS", "EFFETS.INS", "BUZZER.INS",
                                    "CLAVIERS.INS", "CHIPTUNE.INS", "PERCUS.INS",
                                    "GLISSES.INS", "BRUITS.INS")]
)


def build(code, rasm):
    """Assemble la langue et fabrique build/seq16-<code>.dsk avec les banques."""
    main = make_source(code)
    dsk = os.path.join(ROOT, "build", f"seq16-{code}.dsk")
    if os.path.exists(dsk):
        os.remove(dsk)
    res = subprocess.run([rasm, main, "-o", os.path.join("build", f"seq16-{code}"), "-s"],
                         cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(dsk):
        sys.stderr.write(res.stdout + res.stderr)
        raise SystemExit(f"*** ERREUR D'ASSEMBLAGE ({code}) ***")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import amsdsk
    for rel in BANKS:
        with open(os.path.join(ROOT, rel), "rb") as fh:
            amsdsk.add_file(dsk, os.path.basename(rel), fh.read())
    return dsk


def main():
    p = argparse.ArgumentParser(description="SEQ-16 en anglais et en espagnol")
    p.add_argument("langues", nargs="*", help="en, es (par défaut : les deux)")
    p.add_argument("--rasm", default=os.environ.get("RASM", os.path.join("tools", "rasm.exe")))
    p.add_argument("--check", action="store_true", help="vérifie seulement les traductions")
    a = p.parse_args()
    for code in a.langues:
        if code not in LANGS:
            p.error(f"langue inconnue : {code} (choix : {', '.join(LANGS)})")
    errs = problems()
    for e in errs:
        print("  " + e)
    if errs:
        raise SystemExit(f"*** {len(errs)} problème(s) de traduction ***")
    if a.check:
        print(f"Traductions OK : {len(TEXTS)} textes, langues {', '.join(LANGS)}.")
        return
    for code in a.langues or LANGS:
        print("OK :", build(code, a.rasm))


if __name__ == "__main__":
    main()
