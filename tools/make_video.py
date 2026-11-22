"""make_video.py : une vidéo de présentation de SEQ-16, tournée dans le CPC simulé.

Le vrai programme tourne dans tools/cpcsim.py ; le script appuie sur les
touches d'un scénario, filme l'écran (police de la ROM du CPC, comme
tools/snapshots.py) à chaque image de 50 Hz, et refait le son de l'AY à
partir des écritures dans ses registres (tools/ay_render.py).  ffmpeg
assemble le tout en MP4 (1344 x 864, 50 images/s).

    python tools/make_video.py              # anglais : build/video/seq16-demo-en.mp4
    python tools/make_video.py fr           # français, es : espagnol

Il faut le paquet z80, numpy, ffmpeg, les disquettes de build/ et la ROM
OS6128.ROM pour la police (voir tools/snapshots.py).
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import ay_render  # noqa: E402
import cpcsim  # noqa: E402
import snapshots  # noqa: E402
from cpcsim import CPC  # noqa: E402

FRAME_US = 20_000                       # une image du CPC : 50 Hz
SPF = ay_render.RATE // 50              # 882 échantillons de son par image
KEY = dict(SPACE=47, F1=13, F2=14, F4=20, INST=5, DISK=12, MODE=4, CTRL=23, RIGHT=1, LEFT=8,
           UP=0, DOWN=2, P=27, D=61)
UP_, DOWN_, LEFT_, RIGHT_, RET = 0xF0, 0xF1, 0xF2, 0xF3, 13

TEXT = {
    "en": dict(
        title=["SEQ-16", "", "4-VOICE CHIPTUNE TRACKER", "FOR THE AMSTRAD CPC 6128", "",
               "Z80 ASSEMBLER - AY-3-8912"],
        split=["4 VOICES, 16 STEPS", "", "A, B, C : TONES", "N : NOISE"],
        layered=["LAYERED SOUNDS", "", "ONE NOTE, FOUR VOICES"],
        inst=["32 INSTRUMENTS", "", "ENVELOPES, ARPEGGIOS,", "VIBRATO, GLISSANDO"],
        sampler=["SAMPLER", "", "4-BIT SAMPLES", "ON THE AY VOLUME"],
        patterns=["125 FACTORY PATTERNS", "", "MONO AND POLY", "ON TWO DISKS"],
        digi=["DIGIDRUMS", "", "SAMPLES INSIDE THE SONG"],
        words=["AND IT TALKS..."],
        end=["SEQ-16", "", "ENGLISH - FRANCAIS - ESPANOL", "", "GITHUB.COM/CHRISTOPHECRUZ",
             "/CPC-SEQ-16"]),
    "fr": dict(
        title=["SEQ-16", "", "SEQUENCEUR CHIPTUNE 4 VOIX", "POUR AMSTRAD CPC 6128", "",
               "ASSEMBLEUR Z80 - AY-3-8912"],
        split=["4 VOIX, 16 PAS", "", "A, B, C : SONS", "N : BRUIT"],
        layered=["SONS COMPOSES", "", "UNE NOTE, QUATRE VOIX"],
        inst=["32 INSTRUMENTS", "", "ENVELOPPES, ARPEGES,", "VIBRATO, GLISSANDO"],
        sampler=["SAMPLER", "", "SAMPLES 4 BITS", "SUR LE VOLUME DE L'AY"],
        patterns=["125 MOTIFS D'USINE", "", "MONO ET POLY", "SUR DEUX DISQUETTES"],
        digi=["DIGIDRUMS", "", "DES SAMPLES DANS LE MORCEAU"],
        words=["ET IL PARLE..."],
        end=["SEQ-16", "", "FRANCAIS - ENGLISH - ESPANOL", "", "GITHUB.COM/CHRISTOPHECRUZ",
             "/CPC-SEQ-16"]),
    "es": dict(
        title=["SEQ-16", "", "SECUENCIADOR CHIPTUNE", "DE 4 VOCES PARA AMSTRAD", "CPC 6128", "",
               "ENSAMBLADOR Z80 - AY-3-8912"],
        split=["4 VOCES, 16 PASOS", "", "A, B, C : TONOS", "N : RUIDO"],
        layered=["SONIDOS DE 4 VOCES", "", "UNA NOTA, CUATRO VOCES"],
        inst=["32 INSTRUMENTOS", "", "ENVOLVENTES, ARPEGIOS,", "VIBRATO, GLISSANDO"],
        sampler=["SAMPLER", "", "SAMPLES DE 4 BITS", "CON EL VOLUMEN DEL AY"],
        patterns=["125 PATRONES DE FABRICA", "", "MONO Y POLI", "EN DOS DISQUETES"],
        digi=["DIGIDRUMS", "", "SAMPLES DENTRO DEL TEMA"],
        words=["Y HABLA..."],
        end=["SEQ-16", "", "ESPANOL - ENGLISH - FRANCAIS", "", "GITHUB.COM/CHRISTOPHECRUZ",
             "/CPC-SEQ-16"]),
}


class VideoCPC(CPC):
    """Le CPC simulé, avec le temps d'un vrai CPC : l'attente du balayage
    dure jusqu'au top suivant de 20 ms, et le catalogue AMSDOS s'affiche."""
    fw_CAS_CATALOG = snapshots.SnapCPC.fw_CAS_CATALOG
    dsk_path = None

    def fw_MC_WAIT_FLYBACK(self):
        self.frame += 1
        self.t = (self.t // FRAME_US + 1) * FRAME_US

    def use_disk(self, dsk):
        super().use_disk(dsk)
        self.dsk_path = dsk


class Film:
    """Les images du film : écrans du CPC (avec leur instant) ou cartons."""

    def __init__(self, cpc):
        self.cpc = cpc
        self.frames = []                 # (clé d'écran, image de son ou None)
        self.screens = {}                # clé -> (codes, attr)
        self.done_t = 0                  # images déjà filmées (indice en 20 ms)

    def _key(self, codes, attr):
        key = (tuple(tuple(r) for r in codes), tuple(tuple(r) for r in attr))
        self.screens.setdefault(key, ([r[:] for r in codes], [r[:] for r in attr]))
        return key

    def catch_up(self):
        """Filme les images écoulées depuis la dernière fois (écran actuel)."""
        cpc = self.cpc
        now = cpc.t // FRAME_US
        if now > self.done_t:
            key = self._key(cpc.codes, cpc.attr)
            for i in range(self.done_t, now):
                self.frames.append((key, i))
            self.done_t = now

    def run(self, seconds, keys=()):
        """Laisse tourner le programme (touches enfoncées pendant 2 images)."""
        n = round(seconds * 50)
        for i in range(n):
            self.cpc.frames(1, keys=set(keys) if i < 2 else set())
            self.catch_up()

    def press(self, *keys, wait=0.5):
        self.run(wait, keys)

    def still(self, seconds):
        """Images fixes de l'écran actuel, sans son (le CPC attend une touche)."""
        key = self._key(self.cpc.codes, self.cpc.attr)
        self.frames += [(key, None)] * round(seconds * 50)

    def card(self, lines, seconds=2.2):
        codes = [[32] * 40 for _ in range(25)]
        attr = [[(2, 0)] * 40 for _ in range(25)]
        top = 12 - len(lines) // 2
        for i, text in enumerate(lines):
            col = max(0, (40 - len(text)) // 2)
            pen = 1 if i == 0 else (3 if "GITHUB" in text or text.startswith("/") else 2)
            for j, ch in enumerate(text[:40]):
                codes[top + i][col + j] = ord(ch)
                attr[top + i][col + j] = (pen, 0)
        key = self._key(codes, attr)
        self.frames += [(key, None)] * round(seconds * 50)

    def chooser(self, keys, pause=0.25, first=1.2, last=0.8):
        """Clés pour la liste de choix (KM_WAIT_CHAR) : chaque frappe filme
        quelques images fixes de la liste, pour qu'on la voie bouger."""
        seq = []
        for i, k in enumerate(keys):
            secs = first if i == 0 else (last if k == RET else pause)

            def shot(k=k, secs=secs):
                self.still(secs)
                return k
            seq.append(shot)
        return seq


def pick(names, target):
    """Touches pour aller du premier nom de la liste à target (flèche bas)."""
    i = names.index(target)
    return [DOWN_] * i + [RET]


def disk_names(path, ext):
    import amsdsk
    return [n[:-4] for n in amsdsk.list_files(path) if n.endswith(ext)]


def scenario(film, lang):
    cpc, T = film.cpc, TEXT[lang]
    prog = os.path.join(ROOT, "build", f"seq16-{lang}.dsk")
    poly = os.path.join(ROOT, "build", "seq16-motifs-poly.dsk")
    mono = os.path.join(ROOT, "build", "seq16-motifs-mono.dsk")

    film.card(T["title"], 3.5)
    cpc.boot()
    film.done_t = cpc.t // FRAME_US
    film.run(1.0)
    film.card(T["split"])
    film.press(KEY["SPACE"])                    # le motif de démonstration
    film.run(7.5)
    film.card(T["inst"], 1.8)
    film.press(KEY["INST"])                       # la musique continue
    for _ in range(8):                          # on parcourt les réglages
        film.press(KEY["DOWN"], wait=0.45)
    film.run(1.5)
    film.press(KEY["F1"], wait=0.8)
    film.press(KEY["SPACE"], wait=0.3)          # arrêt

    film.card(T["sampler"])
    film.press(KEY["F4"], wait=1.2)             # DRUMS.SMP se charge
    for _ in range(4):                          # kick, snare, hat, clap
        film.press(KEY["SPACE"], wait=0.5)
        film.press(KEY["CTRL"], KEY["RIGHT"], wait=0.35)

    film.card(T["patterns"])
    cpc.use_disk(poly)                          # disquette des motifs poly
    film.press(KEY["DISK"], wait=0.8)
    names = disk_names(poly, ".PAT")
    cpc.chars = film.chooser([RIGHT_] * 4 + [LEFT_] * 4 + pick(names, "TECHNO01")[:-1] + [RET])
    film.press(KEY["P"], wait=0.8)
    film.press(KEY["F1"], wait=0.5)
    film.press(KEY["SPACE"])
    film.run(7.0)
    film.press(KEY["SPACE"], wait=0.3)

    film.card(T["digi"])
    film.press(KEY["DISK"], wait=0.6)
    cpc.chars = film.chooser(pick(names, "DIGIHOP1"), pause=0.08)
    film.press(KEY["P"], wait=0.8)
    film.press(KEY["F1"], wait=0.5)
    film.press(KEY["SPACE"])
    film.run(8.0)
    film.press(KEY["SPACE"], wait=0.3)

    film.card(T["layered"])
    cpc.use_disk(mono)                          # disquette des motifs mono
    names = disk_names(mono, ".PAT")
    for name, secs in (("POPCHRD1", 7.0), ("CHIPLD1", 7.0)):
        film.press(KEY["DISK"], wait=0.6)
        cpc.chars = film.chooser(pick(names, name), pause=0.12)
        film.press(KEY["P"], wait=0.8)
        film.press(KEY["F1"], wait=0.5)
        film.press(KEY["SPACE"])
        film.run(secs)
        film.press(KEY["SPACE"], wait=0.3)

    film.card(T["words"], 1.6)
    cpc.use_disk(prog)                          # la banque de mots
    film.press(KEY["DISK"], wait=0.6)
    banks = disk_names(prog, ".SMP")
    cpc.chars = film.chooser(pick(banks, "MOTS"), pause=0.2)
    film.press(KEY["D"], wait=1.0)
    film.press(KEY["F4"], wait=0.8)
    for word in range(14):                      # ALLEZ OUI NON ENCORE ... MUSIQ
        if word in (0, 7, 11, 12, 13):
            film.press(KEY["SPACE"], wait=0.6)
        film.press(KEY["CTRL"], KEY["RIGHT"], wait=0.12 if word not in (0, 7, 11, 12, 13) else 0.3)
    film.card(T["end"], 4.0)


def render_frames(film, font):
    """Images RGB 336 x 216 (bordure comprise), une par écran différent."""
    cache = {}
    border = bytes(snapshots.BORDER)
    w = 40 * 8 + 2 * snapshots.BORDER_PX
    glyph = {}

    def row_bytes(code, pen, paper, y):
        k = (code, pen, paper, y)
        if k not in glyph:
            bits = font[code * 8 + y]
            fg, bg = bytes(snapshots.INKS[pen & 3]), bytes(snapshots.INKS[paper & 3])
            glyph[k] = b"".join(fg if bits & (0x80 >> x) else bg for x in range(8))
        return glyph[k]
    for key, (codes, attr) in film.screens.items():
        lines = [border * w] * snapshots.BORDER_PX
        side = border * snapshots.BORDER_PX
        for r in range(25):
            for y in range(8):
                lines.append(side + b"".join(row_bytes(codes[r][c], *attr[r][c], y)
                                             for c in range(40)) + side)
        lines += [border * w] * snapshots.BORDER_PX
        cache[key] = b"".join(lines)
    return cache, w, 25 * 8 + 2 * snapshots.BORDER_PX


def level(pcm, target=0.16, max_gain=4.0, window=0.4):
    """Nivelle le son : un sample seul (une voie de l'AY, en 4 bits) sort bien
    moins fort que la musique sur trois voies.  Gain lissé, au plus x4, sans
    toucher aux silences ; puis on limite les crêtes."""
    rate = ay_render.RATE
    w = int(window * rate)
    mono = pcm.mean(axis=1)
    rms = np.sqrt(ay_render.moving_average(mono ** 2, w))
    gain = np.where(rms > 0.005, np.clip(target / np.maximum(rms, 1e-6), 1.0, max_gain), 1.0)
    gain = ay_render.moving_average(gain, w)                        # sans à-coups
    out = pcm * gain[:, None]
    peak = float(np.abs(out).max()) or 1.0
    return (out * (0.95 / peak)).astype(np.float32)


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    if cpcsim is None:
        raise SystemExit("paquet z80 absent (pip install z80)")
    font = snapshots.load_font(snapshots.find_rom())
    prog = os.path.join(ROOT, "build", f"seq16-{lang}.dsk")
    cpc = VideoCPC.from_build(prog)
    cpc.use_disk(prog)
    film = Film(cpc)
    scenario(film, lang)

    # le son : l'AY sur toute la durée, découpé image par image
    last = max([i for _, i in film.frames if i is not None] + [0]) + 1
    pcm = ay_render.render(cpc.ay_writes, last * FRAME_US)
    silence = np.zeros((SPF, 2), dtype=np.float32)
    chunks = []
    for _, i in film.frames:
        chunk = pcm[i * SPF:(i + 1) * SPF] if i is not None else silence
        if len(chunk) < SPF:
            chunk = np.concatenate([chunk, silence[:SPF - len(chunk)]])
        chunks.append(chunk)
    out_dir = os.path.join(ROOT, "build", "video")
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp()
    wav = os.path.join(tmp, "son.wav")
    ay_render.write_wav(wav, level(np.concatenate(chunks)))

    images, w, h = render_frames(film, font)
    mp4 = os.path.join(out_dir, f"seq16-demo-{lang}.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{w}x{h}", "-r", "50", "-i", "-", "-i", wav,
         "-vf", f"scale={w * 4}:{h * 4}:flags=neighbor", "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4],
        stdin=subprocess.PIPE)
    for key, _ in film.frames:
        ff.stdin.write(images[key])
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg a échoué")
    print(f"OK : {os.path.relpath(mp4, ROOT)} ({len(film.frames) / 50:.1f} s, "
          f"{os.path.getsize(mp4) // 1024} Ko)")


if __name__ == "__main__":
    main()
