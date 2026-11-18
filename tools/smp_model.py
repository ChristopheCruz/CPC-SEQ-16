"""smp_model.py : le modèle (sans interface) de l'éditeur de banques smp_gui.py.

Rôle
----
Garde la liste des samples d'une banque .SMP en cours d'édition, avec les
réglages de conversion de chacun, et fait tout le travail : conversion des
WAV, rendu « CPC » pour l'écoute, assemblage de la banque, contrôle de la
place, sauvegarde et ajout à une disquette.

Aucun appel à tkinter ici : le module se teste sans écran
(voir tools/test_smp_gui.py).

Tous les calculs passent par wav2smp.py (mêmes fonctions que la ligne de
commande) : avec les mêmes réglages, la banque est identique octet pour octet
à celle de wav2smp.py, sauf un point : le réglage BITS est aussi écrit dans
la fiche (bits 3-4 de l'octet 15). wav2smp.py ne l'écrit pas (la fiche dit
toujours « 4 bits ») ; les données sont réduites dans les deux cas, et le
masque appliqué une deuxième fois à la lecture ne change rien.

Deux sortes de samples :
  - venu d'un WAV : tous les réglages sont modifiables, chaque changement
    relance la conversion depuis le WAV d'origine ;
  - relu dans une banque .SMP : il n'y a plus de WAV. Seuls le nom, la
    fréquence, les bits, la décimation et la courbe se modifient ; ils ne
    touchent que la fiche, pas les données (comme sur l'écran f4 du CPC).
"""
import io
import os
import sys
import wave
import array

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amsdsk      # noqa: E402
import wav2smp     # noqa: E402

# Fréquences proposées dans l'interface (Hz) ; tout code de 62 à 250 reste
# possible.
RATE_PRESETS = [4000, 5000, 6250, 8000, 10000, 12500, 16000]
BITS_CHOICES = [4, 3, 2, 1]
DITHERS = ["none", "noise"]
MAX_SLICES = wav2smp.MAX_SAMPLES
# Réglages qui ne changent que la fiche : seuls permis sans WAV d'origine.
HEADER_KEYS = {"name", "code", "rate", "bits", "decim", "curve"}
# Réglages qui demandent une reconversion depuis le WAV.
SOURCE_KEYS = {"drive", "trim", "clean", "dither"}


class BankError(Exception):
    """Erreur « métier » à montrer telle quelle à l'utilisateur (en français)."""


def wav_bytes(samples, rate):
    """Flottants -1..1 -> fichier WAV mono 16 bits complet, en mémoire (bytes)."""
    a = array.array("h", (max(-32767, min(32767, int(round(v * 32767))))
                          for v in samples))
    if sys.byteorder == "big":
        a.byteswap()                            # le WAV est petit-boutiste
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(round(rate)))
        w.writeframes(a.tobytes())
    return buf.getvalue()


def dsk_name(path):
    """Nom AMSDOS 8.3 tiré d'un nom de fichier : 'ma banque.smp' -> 'MABANQUE.SMP'."""
    stem, ext = os.path.splitext(os.path.basename(path))
    base = "".join(c for c in stem.upper() if c.isalnum() and c.isascii())[:8]
    ext = "".join(c for c in ext.upper() if c.isalnum() and c.isascii())[:3]
    return "%s.%s" % (base or "BANQUE", ext or "SMP")


class Item:
    """Un sample de la banque et ses réglages.

    path      : WAV d'origine, ou None si le sample vient d'une banque .SMP
    part      : (k, n) = tranche k sur n du WAV (découpage --slice)
    group     : identifiant commun aux tranches d'un même découpage
    code      : durée d'un échantillon en NOP (62 à 250)
    loop      : point de boucle de la fiche (#FFFF = aucun)
    extra     : drapeaux de la fiche hors courbe (bits 0-3), conservés
    data      : données compressées (2 échantillons par octet)
    """

    def __init__(self, name, path=None, part=(0, 1), group=0,
                 code=125, drive=1.0, trim=False, clean=False, dither="none",
                 bits=4, decim=1, curve=wav2smp.CURVE_LOG,
                 loop=wav2smp.NO_LOOP, extra=0, data=b""):
        self.name = wav2smp.clean_name(name)
        self.path = path
        self.part = part
        self.group = group
        self.code = code
        self.drive = drive
        self.trim = trim
        self.clean = clean
        self.dither = dither
        self.bits = bits
        self.decim = decim
        self.curve = curve
        self.loop = loop
        self.extra = extra
        self.data = bytes(data)

    @property
    def has_source(self):
        """Vrai si le sample a encore son WAV d'origine (reconversion possible)."""
        return self.path is not None

    @property
    def rate(self):
        """Fréquence de lecture en Hz (1 000 000 / code)."""
        return wav2smp.code_to_rate(self.code)

    @property
    def seconds(self):
        """Durée du sample sur le CPC, en secondes."""
        return 2 * len(self.data) / self.rate

    def settings(self):
        """Dictionnaire des réglages (pour remplir l'interface)."""
        return dict(name=self.name, code=self.code, drive=self.drive,
                    trim=self.trim, clean=self.clean, dither=self.dither,
                    bits=self.bits, decim=self.decim, curve=self.curve,
                    slices=self.part[1])

    def to_sample(self):
        """Item -> wav2smp.Sample, tel qu'il sera écrit dans la fiche."""
        flags = (self.extra & 0x0F) | (self.curve << 4)
        return wav2smp.Sample(self.name, self.data, self.code, self.loop,
                              flags, self.decim, self.bits)


class BankModel:
    """La banque en cours d'édition : une liste d'Item (16 au plus)."""

    def __init__(self):
        self.items = []
        self.dirty = False                      # modifié depuis la sauvegarde
        self._wavs = {}                         # cache : chemin -> (flottants, Hz)
        self._next_group = 1

    # --- lecture des sources -----------------------------------------------
    def _read(self, path):
        """Lit un WAV une seule fois (cache)."""
        if path not in self._wavs:
            try:
                self._wavs[path] = wav2smp.read_wav(path)
            except (OSError, EOFError, wave.Error, ValueError) as e:
                raise BankError("WAV illisible : %s\n%s" % (path, e))
        return self._wavs[path]

    def source(self, i):
        """Tranche du WAV d'origine qui sert à la conversion, après --trim et
        --slice, avant normalisation : (flottants, Hz), ou None sans WAV."""
        it = self.items[i]
        if not it.has_source:
            return None
        x, sr = self._read(it.path)
        if it.trim:
            x = wav2smp.trim(x)
        k, n = it.part
        if n > 1:                               # même découpage que wav2smp
            size = len(x) // n
            x = x[k * size:(k + 1) * size]
        return x, sr

    def _convert(self, it, i):
        """(Re)calcule les données d'un item venu d'un WAV."""
        x, sr = self.source(i)
        if not x:
            raise BankError("%s : le son est vide" % os.path.basename(it.path))
        s = wav2smp.convert(x, sr, it.name, wav2smp.code_to_rate(it.code),
                            it.drive, it.clean, it.bits, it.dither, it.decim)
        it.data = s.data

    # --- liste ---------------------------------------------------------------
    def __len__(self):
        return len(self.items)

    def _room(self, n):
        """Refuse d'aller au-delà de 16 samples."""
        if len(self.items) + n > wav2smp.MAX_SAMPLES:
            raise BankError("Une banque contient %d samples au plus."
                            % wav2smp.MAX_SAMPLES)

    def add_wav(self, path, name=None, **settings):
        """Ajoute un WAV en fin de banque. Réglages facultatifs : code ou rate,
        drive, trim, clean, dither, bits, decim, curve. Renvoie l'indice."""
        self._room(1)
        self._read(path)                        # erreur tout de suite si illisible
        base = os.path.splitext(os.path.basename(path))[0]
        it = Item(name or base, path=path, group=self._take_group())
        self.items.append(it)
        i = len(self.items) - 1
        try:
            self._apply(it, settings)
            self._convert(it, i)
        except Exception:
            self.items.pop()                    # rien n'est ajouté en cas d'erreur
            raise
        self.dirty = True
        return i

    def _take_group(self):
        """Nouvel identifiant de groupe de tranches."""
        self._next_group += 1
        return self._next_group

    def remove(self, i):
        """Retire le sample i."""
        del self.items[i]
        self.dirty = True

    def move(self, i, delta):
        """Déplace le sample i de delta places (-1 = monter). Renvoie le nouvel
        indice."""
        j = max(0, min(len(self.items) - 1, i + delta))
        if j != i:
            self.items.insert(j, self.items.pop(i))
            self.dirty = True
        return j

    def clear(self):
        """Vide la banque."""
        self.items = []
        self.dirty = False

    # --- réglages ------------------------------------------------------------
    def _apply(self, it, settings):
        """Vérifie et range les réglages dans l'item (sans reconvertir)."""
        for key, v in settings.items():
            if key == "name":
                it.name = wav2smp.clean_name(v)
            elif key == "rate":
                v = float(v)
                if not 4000 <= v <= 16200:      # mêmes bornes que wav2smp --rate
                    raise BankError("La fréquence va de 4 000 à 16 000 Hz.")
                it.code = wav2smp.rate_to_code(v)
            elif key == "code":
                v = int(v)
                if not wav2smp.CODE_MIN <= v <= wav2smp.CODE_MAX:
                    raise BankError("La période va de %d à %d NOP."
                                    % (wav2smp.CODE_MIN, wav2smp.CODE_MAX))
                it.code = v
            elif key == "drive":
                v = float(v)
                if not 0 < v <= 64:
                    raise BankError("Le drive va de 0,1 à 64 (1 = aucun gain).")
                it.drive = v
            elif key in ("trim", "clean"):
                setattr(it, key, bool(v))
            elif key == "dither":
                if v not in DITHERS:
                    raise BankError("Tramage inconnu : %s" % v)
                it.dither = v
            elif key == "bits":
                if int(v) not in BITS_CHOICES:
                    raise BankError("Bits : 4, 3, 2 ou 1.")
                it.bits = int(v)
            elif key == "decim":
                if int(v) not in wav2smp.DECIMS:
                    raise BankError("Décimation : 1, 2, 3, 4, 6 ou 8.")
                it.decim = int(v)
            elif key == "curve":
                if not 0 <= int(v) < len(wav2smp.CURVES):
                    raise BankError("Courbe inconnue : %s" % v)
                it.curve = int(v)
            else:
                raise BankError("Réglage inconnu : %s" % key)

    def update(self, i, **settings):
        """Change des réglages du sample i et reconvertit si besoin.
        Sans WAV d'origine, seuls name, code/rate, bits, decim et curve sont
        permis (ils ne touchent que la fiche)."""
        it = self.items[i]
        if not it.has_source:
            bad = [k for k, v in settings.items()
                   if k not in HEADER_KEYS and getattr(it, k, None) != v]
            if bad:
                raise BankError("Sample relu dans une banque : pas de WAV "
                                "d'origine, impossible de changer %s."
                                % ", ".join(bad))
            settings = {k: v for k, v in settings.items() if k in HEADER_KEYS}
        before = it.settings()
        backup = dict(vars(it))
        try:
            self._apply(it, settings)
            if it.has_source and self._needs_convert(before, it):
                self._convert(it, i)
        except Exception:
            vars(it).update(backup)             # réglages d'avant en cas d'erreur
            raise
        if it.settings() != before:
            self.dirty = True

    @staticmethod
    def _needs_convert(before, it):
        """Vrai si un réglage qui change les données a bougé (tout sauf le nom,
        la décimation et la courbe, qui ne sont que dans la fiche)."""
        after = it.settings()
        return any(before[k] != after[k]
                   for k in ("code", "drive", "trim", "clean", "dither", "bits"))

    def set_slices(self, i, n):
        """Découpe le WAV du sample i en n tranches égales (comme --slice n).
        Les autres tranches du même découpage sont remplacées. Noms : 4
        premières lettres + numéro, comme wav2smp. n = 1 : WAV entier.
        Renvoie l'indice de la première tranche."""
        it = self.items[i]
        if not it.has_source:
            raise BankError("Sample relu dans une banque : pas de WAV "
                            "d'origine à découper.")
        n = int(n)
        if not 1 <= n <= MAX_SLICES:
            raise BankError("De 1 à %d tranches." % MAX_SLICES)
        same = [j for j, o in enumerate(self.items) if o.group == it.group]
        self._room(n - len(same))
        first = same[0]
        base = wav2smp.clean_name(os.path.splitext(os.path.basename(it.path))[0])
        group = self._take_group()
        new = []
        for k in range(n):
            name = base[:4] + "%02d" % k if n > 1 else base
            o = Item(name, path=it.path, part=(k, n), group=group)
            for key in ("code", "drive", "trim", "clean", "dither", "bits",
                        "decim", "curve"):
                setattr(o, key, getattr(it, key))
            new.append(o)
        old = list(self.items)
        self.items = [o for o in self.items if o.group != it.group]
        self.items[first:first] = new
        try:
            for k, o in enumerate(new):
                self._convert(o, first + k)
        except Exception:
            self.items = old                    # retour à la liste d'avant
            raise
        self.dirty = True
        return first

    # --- banques .SMP ----------------------------------------------------------
    def load_bank(self, raw, append=False):
        """Charge une banque (octets). Les samples n'ont plus de WAV d'origine."""
        try:
            bank = wav2smp.parse_bank(raw)
        except (ValueError, IndexError, KeyError, UnicodeDecodeError) as e:
            raise BankError("Ce fichier n'est pas une banque .SMP valide : %s" % e)
        if append:
            self._room(len(bank))
        else:
            self.items = []
        for s in bank:
            curve = (s.flags >> 4) & 7
            if curve >= len(wav2smp.CURVES):
                curve = wav2smp.CURVE_LOG
            self.items.append(Item(s.name, code=s.code, bits=s.bits,
                                   decim=s.decim, curve=curve, loop=s.loop,
                                   extra=s.flags & 0x0F, data=s.data))
        self.dirty = append

    def open_bank(self, path, append=False):
        """Ouvre un fichier .SMP (remplace la banque, ou l'ajoute à la fin)."""
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as e:
            raise BankError("Lecture impossible : %s" % e)
        self.load_bank(raw, append)

    def samples(self):
        """Liste de wav2smp.Sample, dans l'ordre de la banque."""
        return [it.to_sample() for it in self.items]

    def build(self):
        """Octets du fichier .SMP (sans contrôle de taille)."""
        if not self.items:
            raise BankError("La banque est vide.")
        return wav2smp.build_bank(self.samples())

    def used_bytes(self):
        """Taille de la zone de données, celle qui va dans la mémoire du CPC."""
        if not self.items:
            return 0
        return wav2smp.data_size(self.build())

    def fits(self):
        """Vrai si la banque tient dans la mémoire principale (16 320 octets)."""
        return self.used_bytes() <= wav2smp.BANK_MAX_MAIN

    def total_seconds(self):
        """Durée totale des samples, en secondes."""
        return sum(it.seconds for it in self.items)

    def checked_bytes(self):
        """Octets de la banque, après les contrôles : non vide, et pas plus de
        16 320 octets de données. Sinon BankError."""
        raw = self.build()
        size = wav2smp.data_size(raw)
        if size > wav2smp.BANK_MAX_MAIN:
            raise BankError("La banque fait %d octets : c'est %d de trop. Le "
                            "maximum est %d octets (mémoire principale du "
                            "CPC). Raccourcis un son, baisse la fréquence ou "
                            "retire un sample." % (size, size - wav2smp.BANK_MAX_MAIN,
                                                   wav2smp.BANK_MAX_MAIN))
        return raw

    def save(self, path):
        """Écrit la banque dans path (refusée si trop grande). Renvoie sa taille."""
        raw = self.checked_bytes()
        try:
            with open(path, "wb") as f:
                f.write(raw)
        except OSError as e:
            raise BankError("Écriture impossible : %s" % e)
        self.dirty = False
        return len(raw)

    # --- disquette -------------------------------------------------------------
    @staticmethod
    def dsk_has(dsk_path, name):
        """Vrai si la disquette contient déjà un fichier de ce nom AMSDOS."""
        try:
            return name.upper() in amsdsk.list_files(dsk_path)
        except (OSError, ValueError) as e:
            raise BankError("Disquette illisible : %s" % e)

    def add_to_dsk(self, dsk_path, name):
        """Écrit la banque sur la disquette sous le nom AMSDOS name (8.3) ;
        un fichier du même nom est remplacé. Renvoie le nom écrit."""
        raw = self.checked_bytes()
        name = name.upper()
        try:
            amsdsk.add_file(dsk_path, name, raw)
        except (OSError, ValueError) as e:
            raise BankError("Ajout à la disquette impossible : %s" % e)
        return name

    # --- écoute et dessin ------------------------------------------------------
    def original(self, i):
        """Son d'origine normalisé (avant drive) : (flottants, Hz), ou None."""
        src = self.source(i)
        if src is None:
            return None
        return wav2smp.normalize(src[0]), src[1]

    def rendered(self, i):
        """Rendu simulé du CPC (niveaux de l'AY, bits, décimation, courbe) :
        (flottants, Hz). Même calcul que les WAV d'écoute de wav2smp."""
        it = self.items[i]
        codes = wav2smp.unpack(it.data)
        return wav2smp.render(codes, it.decim, it.bits, it.curve), it.rate

    def original_wav(self, i):
        """WAV en mémoire du son d'origine, ou None sans WAV."""
        o = self.original(i)
        return None if o is None else wav_bytes(*o)

    def rendered_wav(self, i):
        """WAV en mémoire du rendu CPC."""
        return wav_bytes(*self.rendered(i))
