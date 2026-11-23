"""make_video.py : une vidéo de présentation de SEQ-16, tournée dans le CPC simulé.

Le vrai programme tourne dans tools/cpcsim.py ; le script appuie sur les
touches d'un scénario, filme l'écran (police de la ROM du CPC, comme
tools/snapshots.py) à chaque image de 50 Hz, et refait le son de l'AY à
partir des écritures dans ses registres (tools/ay_render.py).  ffmpeg
assemble le tout en MP4 (1344 x 864, 50 images/s), plus son affiche (PNG).

Le scénario suit SYNTH, la song synthwave d'usine : l'écran de chargement,
la song dans SONG, puis MOTIF (FX) et INST (sons composés, instruments)
pendant qu'elle joue, et STUDIO (disquette de démonstration) pour les samples.

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
KEY = dict(SPACE=47, SONG=13, MOTIF=14, INST=5, F4=20, DISK=12, MODE=4, F9=3, CTRL=23,
           SHIFT=21, RIGHT=1, LEFT=8, UP=0, DOWN=2)
UP_, DOWN_, LEFT_, RIGHT_, RET = 0xF0, 0xF1, 0xF2, 0xF3, 13

TEXT = {
    "en": dict(
        song=["SYNTH", "", "THE FACTORY SYNTHWAVE SONG", "", "F1 SONG : 64 POSITIONS"],
        fx=["F2 PATTERN", "", "4 VOICES, 16 STEPS", "7 EFFECTS PER STEP"],
        layered=["LAYERED SOUNDS", "", "ONE NOTE, FOUR VOICES", "EDITED ON F3 INST"],
        inst=["32 INSTRUMENTS", "", "ENVELOPES, ARPEGGIOS,", "VIBRATO, GLISSANDO"],
        studio=["SAMPLES", "", "DIGIDRUMS AND A VOICE", "INSIDE THE SONG"],
        end=["SEQ-16", "", "4-VOICE CHIPTUNE TRACKER", "FOR THE AMSTRAD CPC 6128", "",
             "ENGLISH - FRANCAIS - ESPANOL", "", "GITHUB.COM/CHRISTOPHECRUZ", "/CPC-SEQ-16"]),
    "fr": dict(
        song=["SYNTH", "", "LA SONG SYNTHWAVE D'USINE", "", "F1 SONG : 64 POSITIONS"],
        fx=["F2 MOTIF", "", "4 VOIX, 16 PAS", "7 EFFETS PAR PAS"],
        layered=["SONS COMPOSES", "", "UNE NOTE, QUATRE VOIX", "EDITES SUR F3 INST"],
        inst=["32 INSTRUMENTS", "", "ENVELOPPES, ARPEGES,", "VIBRATO, GLISSANDO"],
        studio=["SAMPLES", "", "DIGIDRUMS ET UNE VOIX", "DANS LE MORCEAU"],
        end=["SEQ-16", "", "SEQUENCEUR CHIPTUNE 4 VOIX", "POUR AMSTRAD CPC 6128", "",
             "FRANCAIS - ENGLISH - ESPANOL", "", "GITHUB.COM/CHRISTOPHECRUZ", "/CPC-SEQ-16"]),
    "es": dict(
        song=["SYNTH", "", "EL TEMA SYNTHWAVE DE FABRICA", "", "F1 TEMA : 64 POSICIONES"],
        fx=["F2 PATRON", "", "4 VOCES, 16 PASOS", "7 EFECTOS POR PASO"],
        layered=["SONIDOS DE 4 VOCES", "", "UNA NOTA, CUATRO VOCES", "EDITADOS EN F3 INST"],
        inst=["32 INSTRUMENTOS", "", "ENVOLVENTES, ARPEGIOS,", "VIBRATO, GLISSANDO"],
        studio=["SAMPLES", "", "DIGIDRUMS Y UNA VOZ", "DENTRO DEL TEMA"],
        end=["SEQ-16", "", "SECUENCIADOR CHIPTUNE", "DE 4 VOCES PARA AMSTRAD", "CPC 6128", "",
             "ESPANOL - ENGLISH - FRANCAIS", "", "GITHUB.COM/CHRISTOPHECRUZ", "/CPC-SEQ-16"]),
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
        self.pictures = {}               # clé -> image RGB toute faite
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

    def picture(self, rgb, seconds):
        """Une image RGB toute faite (l'écran de chargement), sans son."""
        key = ("image", len(self.pictures))
        self.pictures[key] = rgb
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


def loading_screen(lang):
    """L'écran de chargement (tools/gen_screen.py) au format des images du
    film : 320 x 200 (un pixel du mode 0 = 2 de large) et la bordure."""
    import gen_screen
    img = gen_screen.draw(lang)
    border = bytes(gen_screen.cpc_rgb(gen_screen.INKS[gen_screen.BORDER]))
    pal = [bytes(gen_screen.cpc_rgb(n)) for n in gen_screen.INKS]
    b = snapshots.BORDER_PX
    w = 320 + 2 * b
    lines = [border * w] * b
    for row in img:
        lines.append(border * b + b"".join(pal[c] * 2 for c in row) + border * b)
    lines += [border * w] * b
    return b"".join(lines)


def scenario(film, lang):
    """SYNTH, la song d'usine, de bout en bout : l'écran de chargement, la
    song dans SONG, puis MOTIF et INST pendant qu'elle joue ; enfin STUDIO
    (la disquette de démonstration) pour les samples."""
    cpc, T = film.cpc, TEXT[lang]
    demo = os.path.join(ROOT, "build", f"seq16-demo-{lang}.dsk")

    film.picture(loading_screen(lang), 4.0)     # RUN"SEQ16 : l'écran de chargement
    cpc.boot()                                  # le programme : MOTIF, SYNTH
    film.done_t = cpc.t // FRAME_US
    film.run(1.2)
    film.card(T["song"], 2.6)
    film.press(KEY["SONG"], wait=0.6)
    film.press(KEY["SPACE"])                    # SYNTH depuis la position 00
    film.run(12.0)                              # intro, couplets, refrain

    film.card(T["fx"], 2.0)                     # (la musique continue)
    film.press(KEY["MOTIF"], wait=0.6)          # MOTIF : le motif en cours boucle
    film.run(6.0)

    film.card(T["layered"], 2.2)
    film.press(KEY["INST"], wait=0.6)
    film.press(KEY["MODE"], wait=0.8)           # f6 : les sons composés
    for k in (KEY["DOWN"], KEY["DOWN"], KEY["DOWN"]):
        film.press(k, wait=0.35)                # voix B, instrument
    for _ in range(3):
        film.press(KEY["RIGHT"], wait=0.35)     # un autre instrument
    film.press(KEY["CTRL"], KEY["RIGHT"], wait=0.8)     # S2
    film.press(KEY["CTRL"], KEY["RIGHT"], wait=0.8)     # S3

    film.card(T["inst"], 2.0)
    film.press(KEY["MODE"], wait=0.6)           # f6 : les instruments
    for _ in range(4):
        film.press(KEY["CTRL"], KEY["RIGHT"], wait=0.55)
    for _ in range(5):
        film.press(KEY["DOWN"], wait=0.3)

    film.press(KEY["SONG"], wait=0.6)           # SONG : la song reprend
    film.run(12.0)                              # le refrain
    film.press(KEY["SPACE"], wait=0.4)          # arrêt

    film.card(T["studio"], 2.2)
    cpc.use_disk(demo)
    names = disk_names(demo, ".SNG")
    cpc.chars = film.chooser(pick(names, "STUDIO"), pause=0.3)
    film.press(KEY["F9"], wait=1.0)             # f9 : STUDIO et sa banque
    film.press(KEY["SPACE"])
    film.run(13.0)
    film.press(KEY["SPACE"], wait=0.4)
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
    cache.update(film.pictures)
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
    poster = os.path.join(out_dir, f"seq16-demo-{lang}.png")
    first = images[film.frames[0][0]]
    rows = [first[y * w * 3:(y + 1) * w * 3] for y in range(h)]
    big = b"".join(b"".join(row[x * 3:x * 3 + 3] * 2 for x in range(w)) * 2 for row in rows)
    snapshots.write_png(poster, w * 2, h * 2, big)
    print(f"OK : {os.path.relpath(mp4, ROOT)} ({len(film.frames) / 50:.1f} s, "
          f"{os.path.getsize(mp4) // 1024} Ko)")


if __name__ == "__main__":
    main()
