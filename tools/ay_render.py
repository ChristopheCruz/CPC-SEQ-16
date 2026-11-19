"""ay_render.py : le son de l'AY-3-8912 du CPC, à partir des écritures.

Le CPC simulé (tools/cpcsim.py) note chaque écriture dans un registre de
l'AY avec son instant, en µs (cpc.ay_writes).  Ce module en refait le son :
voies carrées A, B et C, bruit, enveloppe, mélangeur, volumes (table du DAC
de l'AY, celle d'Ayumi) ; les samples des digidrums ne sont que des
écritures rapides du volume : ils sortent tels quels.

Horloge de l'AY sur CPC : 1 MHz.  Le calcul se fait au rythme interne de
l'AY (un pas toutes les 8 µs, 125 kHz), puis le son est ramené à 44,1 kHz.
Stéréo du CPC : A à gauche, C à droite, B au milieu.

    pcm = render(cpc.ay_writes, duree_us)     # tableau (n, 2) en float32
    write_wav("son.wav", pcm)

Il faut numpy.
"""
import wave

import numpy as np

TICK = 8                      # µs par pas de l'AY (1 MHz / 8)
RATE = 44100
# Table du DAC de l'AY (Ayumi, Peter Sovietov, licence MIT)
DAC = np.array([0.0, 0.00999465934234, 0.01445029373620, 0.02105745021740,
                0.03070115205620, 0.04554818036160, 0.06449988555730, 0.10736629282100,
                0.12658884565500, 0.20498970016000, 0.29221026932200, 0.37283894102400,
                0.49253070878200, 0.63532463569100, 0.80558480201400, 1.0], dtype=np.float32)


def _lfsr():
    """Suite du bruit de l'AY : registre à décalage de 17 bits."""
    out = np.empty(131071, dtype=np.uint8)
    r = 1
    for i in range(131071):
        bit = (r ^ (r >> 3)) & 1
        r = (r >> 1) | (bit << 16)
        out[i] = r & 1
    return out


NOISE = _lfsr()


def _env_levels(shape, k):
    """Niveau (0-15) de l'enveloppe après k pas depuis son départ."""
    att = bool(shape & 4)
    if not shape & 8:                         # formes 0 à 7 : une rampe, puis 0
        first = k if att else 15 - k
        return np.where(k < 16, first, 0)
    alt, hold = bool(shape & 2), bool(shape & 1)
    cycle, pos = k // 16, k % 16
    if hold:
        first = pos if att else 15 - pos
        final = 15 if att ^ alt else 0
        return np.where(k < 16, first, final)
    up = (cycle % 2 == 1) & alt
    up = up ^ att
    return np.where(up, pos, 15 - pos)


class AY:
    def __init__(self):
        self.r = [0] * 16
        self.r[7] = 0x3F
        self.tone_pos = [0, 0, 0]
        self.tone_bit = [0, 0, 0]
        self.noise_pos = 0
        self.noise_idx = 0
        self.env_pos = 0
        self.env_k = 0

    def write(self, reg, val):
        self.r[reg] = val & 0xFF
        if reg == 13:                         # nouvelle forme : l'enveloppe repart
            self.env_pos = 0
            self.env_k = 0

    def run(self, n):
        """n pas de 8 µs : renvoie (gauche, droite) en float32."""
        r = self.r
        k = np.arange(n, dtype=np.int64)
        # bruit
        np_ = max(1, r[6] & 31) * 2
        steps = (self.noise_pos + k) // np_
        noise = NOISE[(self.noise_idx + steps) % 131071]
        tot = self.noise_pos + n
        self.noise_idx = (self.noise_idx + tot // np_) % 131071
        self.noise_pos = tot % np_
        # enveloppe
        ep = max(1, r[11] | (r[12] << 8)) * 2
        esteps = self.env_k + (self.env_pos + k) // ep
        env = _env_levels(r[13] & 15, esteps)
        tot = self.env_pos + n
        self.env_k += tot // ep
        self.env_pos = tot % ep
        if self.env_k > 1 << 20:              # (formes répétées : on garde la phase)
            self.env_k = 16 + self.env_k % 32
        chans = []
        for c in range(3):
            tp = max(1, r[2 * c] | ((r[2 * c + 1] & 15) << 8))
            idx = self.tone_pos[c] + k
            tone = (self.tone_bit[c] ^ ((idx // tp) & 1)).astype(np.uint8)
            tot = self.tone_pos[c] + n
            self.tone_bit[c] ^= (tot // tp) & 1
            self.tone_pos[c] = tot % tp
            tdis = (r[7] >> c) & 1
            ndis = (r[7] >> (c + 3)) & 1
            gate = (tone | tdis) & (noise | ndis)
            v = r[8 + c]
            level = env if v & 16 else np.full(n, v & 15)
            chans.append(DAC[level] * gate)
        a, b, cc = chans
        left, right = a + 0.6 * b, cc + 0.6 * b
        # un peu de chaque côté dans l'autre : sur CPC, A n'est qu'à gauche et
        # C qu'à droite (un sample joué sur A ne s'entendrait que d'une oreille)
        return 0.7 * left + 0.3 * right, 0.7 * right + 0.3 * left


def render(writes, duration_us, rate=RATE):
    """Son stéréo (n, 2) des écritures [(instant µs, registre, valeur)]."""
    ay = AY()
    total = duration_us // TICK
    left = np.zeros(total, dtype=np.float32)
    right = np.zeros(total, dtype=np.float32)
    pos = 0
    for t, reg, val in sorted(writes, key=lambda w: w[0]):
        tick = min(total, t // TICK)
        if tick > pos:
            l_, r_ = ay.run(tick - pos)
            left[pos:tick], right[pos:tick] = l_, r_
            pos = tick
        if reg < 16:
            ay.write(reg, val)
    if pos < total:
        l_, r_ = ay.run(total - pos)
        left[pos:], right[pos:] = l_, r_
    out = np.stack([_resample(left, rate), _resample(right, rate)], axis=1)
    out -= _dc(out)                            # l'AY ne sort que du positif
    peak = float(np.abs(out).max()) or 1.0
    return (out * (0.85 / peak)).astype(np.float32)


def _resample(x, rate):
    """125 kHz -> rate, en moyennant (filtre en créneau)."""
    src = 1_000_000 / TICK
    n = int(len(x) * rate / src)
    cs = np.concatenate([[0.0], np.cumsum(x, dtype=np.float64)])
    edges = np.arange(n + 1) * (src / rate)
    vals = np.interp(edges, np.arange(len(cs)), cs)
    return (np.diff(vals) / (src / rate)).astype(np.float32)


def moving_average(x, width):
    """Moyenne glissante centrée de x sur width échantillons (somme cumulée :
    rapide quelle que soit la largeur)."""
    cs = np.concatenate([[0.0], np.cumsum(x, dtype=np.float64)])
    n = len(x)
    lo = np.clip(np.arange(n) - width // 2, 0, n)
    hi = np.clip(np.arange(n) + (width - width // 2), 0, n)
    return ((cs[hi] - cs[lo]) / np.maximum(hi - lo, 1)).astype(np.float32)


def _dc(x, width=4410):
    """Moyenne glissante (0,1 s) : la composante continue à retirer."""
    return np.stack([moving_average(x[:, i], width) for i in range(2)], axis=1)


def write_wav(path, pcm, rate=RATE):
    data = (np.clip(pcm, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())
