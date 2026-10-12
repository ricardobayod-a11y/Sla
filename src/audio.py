"""Síntese de trilha, ambiência e efeitos sonoros (48 kHz estéreo)."""
import numpy as np
from scipy import signal

SR = 48000
R = np.random.default_rng(7)


def t_(d):
    return np.arange(int(d * SR)) / SR


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


def env_adsr(n, a, d, s, r, sl=0.7):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sus = max(0, n - a - d - r)
    e = np.concatenate([np.linspace(0, 1, a, endpoint=False), np.linspace(1, sl, d, endpoint=False),
                        np.full(sus, sl), np.linspace(sl, 0, r)])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def lp(x, fc, order=2):
    b, a = signal.butter(order, min(fc, SR / 2 - 100) / (SR / 2), 'low')
    return signal.lfilter(b, a, x, axis=0)


def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'high')
    return signal.lfilter(b, a, x, axis=0)


def bp(x, f0, f1, order=2):
    b, a = signal.butter(order, [f0 / (SR / 2), min(f1, SR / 2 - 100) / (SR / 2)], 'band')
    return signal.lfilter(b, a, x, axis=0)


def noise(d):
    return R.normal(0, 1, int(d * SR))


def stereo(x, pan=0.0, width=0.0):
    l = x * np.sqrt(0.5 * (1 - pan))
    r = x * np.sqrt(0.5 * (1 + pan))
    if width:
        dly = int(0.012 * SR * width)
        r = np.concatenate([np.zeros(dly), r[:-dly]]) if dly else r
    return np.stack([l, r], 1)


_IR = {}


def reverb(x, size=2.5, wet=0.35, damp=4000, pre=0.02):
    key = (size, damp)
    if key not in _IR:
        n = int(size * SR)
        tt = np.arange(n) / SR
        irs = []
        for _ in range(2):
            ir = R.normal(0, 1, n) * np.exp(-tt * 6.9 / size)
            ir = lp(ir, damp)
            ir[:int(pre * SR)] = 0
            irs.append(ir / np.sqrt(np.sum(ir ** 2)))
        _IR[key] = np.stack(irs, 1)
    ir = _IR[key]
    if x.ndim == 1:
        x = stereo(x)
    out = np.zeros((len(x) + len(ir) - 1, 2))
    for c in range(2):
        out[:, c] = signal.fftconvolve(x[:, c], ir[:, c])
    dry = np.zeros_like(out)
    dry[:len(x)] = x
    return dry * (1 - wet) + out * wet * 0.9


# ======================================================================= efeitos
def bell(dist=0.0, f0=196.0, d=7.0):
    """sino de bronze: parciais inarmônicas. dist 0=perto, 1=longe."""
    tt = t_(d)
    partials = [(0.5, 1.0, 1.4), (1.0, 0.8, 1.0), (1.19, 0.6, 0.9), (1.5, 0.5, 0.75), (2.0, 0.45, 0.6), (2.51, 0.3, 0.45), (2.66, 0.25, 0.4), (3.01, 0.2, 0.3), (4.1, 0.12, 0.2)]
    x = np.zeros_like(tt)
    for ratio, amp, dec in partials:
        f = f0 * ratio
        beat = 1 + 0.004 * np.sin(2 * np.pi * 0.7 * tt)
        x += amp * np.sin(2 * np.pi * f * tt * beat + R.uniform(0, 6)) * np.exp(-tt / (dec * d * 0.35))
    strike = noise(0.03) * np.exp(-np.arange(int(0.03 * SR)) / (0.004 * SR))
    x[:len(strike)] += bp(strike, 800, 6000) * 0.6
    x *= np.minimum(1, tt / 0.002)
    if dist > 0:
        x = lp(x, 6000 - 5000 * dist)
    x = reverb(norm(x), size=3.5 + 2 * dist, wet=0.35 + 0.5 * dist)
    return norm(x, 0.9)


def boom(d=4.0, f=42):
    tt = t_(d)
    fr = f * (1 + 1.5 * np.exp(-tt * 6))
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt * 1.3)
    x += lp(noise(d), 200) * np.exp(-tt * 3) * 0.6
    x = reverb(x, 3.0, 0.3)
    return norm(x, 0.95)


def riser(d=5.0):
    tt = t_(d)
    n = noise(d)
    out = np.zeros_like(n)
    for k in range(8):
        seg = slice(int(k * len(n) / 8), int((k + 1) * len(n) / 8))
        f = 300 + 3000 * (k / 8) ** 2
        out[seg] = bp(n, f * 0.7, f * 1.4)[seg]
    sw = np.sin(2 * np.pi * np.cumsum(60 + 400 * (tt / d) ** 2) / SR) * 0.4
    x = (out + sw) * (tt / d) ** 2
    return norm(reverb(x, 2.0, 0.3), 0.8)


def hit(d=3.0):
    """impacto de susto: sub + metal + ruído."""
    tt = t_(d)
    x = np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 2.5)
    for f in (311, 466, 740, 1180, 1870):
        x += 0.25 * np.sin(2 * np.pi * f * tt + R.uniform(0, 6)) * np.exp(-tt * 3)
    nn = noise(d) * np.exp(-tt * 18)
    x += hp(nn, 1500) * 0.8
    return norm(reverb(x, 3.0, 0.35), 0.95)


def whoosh(d=1.6):
    tt = t_(d)
    e = np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 2
    n = noise(d)
    out = np.zeros_like(n)
    blocks = 16
    for k in range(blocks):
        seg = slice(int(k * len(n) / blocks), int((k + 1) * len(n) / blocks))
        f = 400 + 2000 * np.sin(np.pi * k / blocks)
        out[seg] = bp(n, f * 0.6, f * 1.6)[seg]
    return norm(stereo(out * e, 0, 1), 0.7)


def metal_step(d=2.5, f0=None):
    """passo na escada de ferro (clang)."""
    tt = t_(d)
    f0 = f0 or R.uniform(180, 240)
    x = np.zeros_like(tt)
    for ratio, amp, dec in [(1, 1, 0.5), (2.76, 0.6, 0.35), (5.4, 0.4, 0.2), (8.93, 0.3, 0.12), (13.3, 0.2, 0.08)]:
        x += amp * np.sin(2 * np.pi * f0 * ratio * tt + R.uniform(0, 6)) * np.exp(-tt / dec)
    thud = lp(noise(0.08), 300) * np.exp(-np.arange(int(0.08 * SR)) / (0.015 * SR))
    x[:len(thud)] += thud * 2
    x *= np.minimum(1, tt / 0.001)
    return norm(reverb(x, 2.5, 0.4), 0.85)


def footsteps_leaves(d=3.0, rate=2.2, run=False):
    out = np.zeros(int(d * SR))
    k = 0.0
    while k < d - 0.3:
        n = noise(0.25 if not run else 0.15)
        e = np.exp(-np.arange(len(n)) / (0.04 * SR))
        s = bp(n * e, 300, 4000) * R.uniform(0.5, 1)
        i = int(k * SR)
        out[i:i + len(s)] += s[:len(out) - i]
        k += 1 / rate + R.normal(0, 0.03)
    return norm(out, 0.6)


def heartbeat(d=8.0, bpm=70):
    out = np.zeros(int(d * SR))
    per = 60 / bpm
    k = 0.2
    while k < d - 0.5:
        for off, a in ((0, 1.0), (0.28, 0.7)):
            tt = t_(0.25)
            s = np.sin(2 * np.pi * 50 * tt) * np.exp(-tt * 22) * a
            i = int((k + off) * SR)
            out[i:i + len(s)] += s[:len(out) - i]
        k += per
    return norm(lp(out, 180), 0.9)


def static(d=3.0, crackle=True):
    n = noise(d)
    x = bp(n, 400, 5000) * 0.5
    if crackle:
        c = (R.random(len(n)) < 0.0008).astype(float) * R.normal(0, 3, len(n))
        x += hp(c, 1500)
    am = 0.7 + 0.3 * np.sin(2 * np.pi * 7 * t_(d) + 0.5 * np.sin(2 * np.pi * 0.3 * t_(d)))
    return norm(x * am, 0.6)


def radio_click():
    tt = t_(0.12)
    x = hp(noise(0.12), 2000) * np.exp(-tt * 80) + np.sin(2 * np.pi * 1200 * tt) * np.exp(-tt * 60) * 0.5
    return norm(x, 0.6)


def generator(d=10.0, die_at=None):
    tt = t_(d)
    f = np.full_like(tt, 30.0)
    amp = np.ones_like(tt)
    if die_at is not None:
        m = tt > die_at
        f[m] = 30 * np.exp(-(tt[m] - die_at) * 0.9)
        amp[m] = np.exp(-(tt[m] - die_at) * 1.2)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(k * ph) / k for k in range(1, 9)) * 0.6
    x += lp(noise(d), 400) * 0.3
    x *= 1 + 0.3 * np.sin(ph * 0.5)
    return norm(lp(x * amp, 1200), 0.6)


def lamp_off():
    tt = t_(0.6)
    x = hp(noise(0.6), 3000) * np.exp(-tt * 40) * 0.6 + np.sin(2 * np.pi * 120 * tt) * np.exp(-tt * 9) * 0.4
    return norm(x, 0.6)


def flashlight_click():
    tt = t_(0.08)
    x = hp(noise(0.08), 2500) * np.exp(-tt * 200) + np.sin(2 * np.pi * 3000 * tt) * np.exp(-tt * 150) * 0.3
    return norm(x, 0.7)


def fall_roll(d=2.2):
    out = np.zeros(int(d * SR))
    for i, (k, a) in enumerate([(0, 1), (0.25, 0.7), (0.45, 0.5)]):
        s = metal_step(0.6, 900 + i * 200) * a
        j = int(k * SR)
        out[j:j + len(s)] += s[:len(out) - j, 0]
    roll = bp(noise(1.2), 500, 3000) * np.linspace(0.4, 0, int(1.2 * SR))
    out[int(0.55 * SR):int(0.55 * SR) + len(roll)] += roll * 0.5
    return norm(out, 0.7)


def creak(d=2.0, f0=180):
    tt = t_(d)
    f = f0 * (1 + 0.4 * np.sin(2 * np.pi * 0.6 * tt) + 0.05 * R.normal(0, 1, len(tt)).cumsum() / SR * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    pulses = (np.sin(ph) > 0.97).astype(float)
    x = bp(pulses, 300, 3500) + bp(noise(d), 800, 2000) * 0.05
    e = np.sin(np.pi * tt / d) ** 0.5
    return norm(reverb(x * e, 1.2, 0.2), 0.7)


def scrape(d=1.8):
    tt = t_(d)
    x = bp(noise(d), 150, 1200) * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * tt))
    x *= np.sin(np.pi * tt / d) ** 0.7
    return norm(x, 0.7)


def scream(d=2.5):
    tt = t_(d)
    f = 900 + 500 * np.sin(2 * np.pi * 3 * tt) * np.exp(-tt) + 300 * (tt / d)
    ph = 2 * np.pi * np.cumsum(f) / SR
    mod = np.sin(ph * 1.51) * 3
    x = np.sin(ph + mod) + 0.5 * np.sin(2.02 * ph + mod * 0.5)
    x += bp(noise(d), 1500, 6000) * 0.6
    e = np.minimum(1, tt / 0.05) * np.exp(-tt * 1.1)
    return norm(reverb(x * e, 2.5, 0.4), 0.85)


def breath(d=4.0, rate=0.9):
    tt = t_(d)
    e = np.clip(np.sin(2 * np.pi * rate * tt), 0, 1) ** 2
    x = bp(noise(d), 500, 3000) * e
    return norm(x, 0.45)


def truck(d=10.0):
    tt = t_(d)
    f = 34 + 3 * np.sin(2 * np.pi * 0.2 * tt)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(k * ph) / k ** 0.8 for k in range(1, 12))
    x += lp(noise(d), 300) * 0.8
    rattle = bp(noise(d), 1500, 4000) * (R.random(len(tt)) < 0.002).astype(float).cumsum() % 2 * 0.1
    return norm(lp(x, 900) + rattle, 0.6)


def phone_buzz():
    tt = t_(0.9)
    x = np.sin(2 * np.pi * 160 * tt) * ((tt % 0.45) < 0.3)
    return norm(lp(x * 0.8, 600), 0.4)


def chant(d=12.0, n=11, base=98.0):
    """canto grave: vozes masculinas em 'uuu/ooo' (síntese por formantes)."""
    tt = t_(d)
    out = np.zeros_like(tt)
    melody = np.array([0, 0, -2, 0, 1, 0, -2, -5]) * 1.0
    seg = 1.6
    idx = (tt / seg).astype(int) % len(melody)
    semis = melody[idx]
    k = int(0.25 * SR)
    semis = np.convolve(semis, np.ones(k) / k, 'same')
    for v in range(n):
        f = base * 2 ** ((semis + R.normal(0, 0.08)) / 12) * (1 + 0.003 * np.sin(2 * np.pi * R.uniform(4, 6) * tt + v))
        ph = 2 * np.pi * np.cumsum(f) / SR + R.uniform(0, 6)
        src = signal.sawtooth(ph) + 0.1 * R.normal(0, 1, len(tt))
        # formantes de "u" / "o"
        vo = (bp(src, 280, 420) * 1.0 + bp(src, 600, 900) * 0.5 + bp(src, 2300, 2700) * 0.08)
        out += vo * (0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * tt + v))
    e = np.minimum(1, tt / 1.5) * np.minimum(1, (d - tt) / 1.5)
    phrase = 0.65 + 0.35 * np.sin(2 * np.pi * tt / (seg * 4) - 1.2)
    return norm(reverb(out * e * phrase, 4.0, 0.45), 0.8)


# ======================================================================= ambiência
def ambience_night(d, crickets=1.0, frogs=1.0, wind=1.0, seed=0):
    rr = np.random.default_rng(seed)
    tt = t_(d)
    out = np.zeros((len(tt), 2))
    if wind:
        w = lp(rr.normal(0, 1, len(tt)), 500) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * tt + 1))
        out += stereo(w * 0.35 * wind, 0, 1)
    if crickets:
        for c in range(4):
            f = rr.uniform(4200, 5600)
            chirp = (np.sin(2 * np.pi * rr.uniform(14, 22) * tt) > 0.3) * (np.sin(2 * np.pi * rr.uniform(0.4, 0.9) * tt + c) > -0.2)
            x = np.sin(2 * np.pi * f * tt) * chirp * rr.uniform(0.03, 0.06)
            out += stereo(lp(x, 7000), rr.uniform(-0.8, 0.8))
    if frogs:
        for c in range(3):
            per = rr.uniform(0.5, 1.2)
            gate = ((tt + c * 0.3) % per) < 0.08
            x = np.sin(2 * np.pi * rr.uniform(300, 600) * tt) * signal.square(2 * np.pi * 40 * tt) * gate
            x *= (np.sin(2 * np.pi * rr.uniform(0.03, 0.08) * tt + c) > 0)
            out += stereo(lp(x, 1500) * 0.035 * frogs, rr.uniform(-0.7, 0.7))
    return out


def ambience_day(d, seed=1):
    rr = np.random.default_rng(seed)
    tt = t_(d)
    out = stereo(lp(rr.normal(0, 1, len(tt)), 700) * 0.25, 0, 1)
    k = 0.5
    while k < d - 1:   # passarinhos esparsos
        n = int(rr.uniform(0.08, 0.2) * SR)
        f = rr.uniform(2500, 4500) * (1 + 0.3 * np.sin(np.linspace(0, rr.uniform(6, 20), n)))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(n) * 0.05
        i = int(k * SR)
        out[i:i + n] += stereo(x, rr.uniform(-0.8, 0.8))[:len(out) - i]
        k += rr.uniform(0.6, 3.0)
    return out


def ambience_room(d):
    tt = t_(d)
    x = lp(noise(d), 200) * 0.15 + np.sin(2 * np.pi * 50 * tt) * 0.01
    return stereo(x, 0, 1)


# ======================================================================= música
def drone(d, root=36.71, intensity=0.5, seed=0, minor=True, pulse=False, high=0.0):
    """pad sombrio: osciladores desafinados + filtro lento. root em Hz (D1≈36.7)."""
    rr = np.random.default_rng(seed)
    tt = t_(d)
    out = np.zeros((len(tt), 2))
    chord = [0, 7, 12, 15 if minor else 16, 19, 24]
    for i, s in enumerate(chord):
        f = root * 2 ** (s / 12)
        for k in range(3):
            det = 1 + rr.normal(0, 0.003)
            ph = 2 * np.pi * f * det * tt + rr.uniform(0, 6)
            x = signal.sawtooth(ph) * 0.5 + np.sin(ph) * 0.5
            amp = (1.0 if i < 2 else 0.5) * (0.6 + 0.4 * np.sin(2 * np.pi * rr.uniform(0.02, 0.07) * tt + rr.uniform(0, 6)))
            out += stereo(x * amp, rr.uniform(-0.7, 0.7))
    cutoff = 300 + 900 * intensity
    out = lp(out, cutoff)
    if high:
        # cordas agudas dissonantes (cluster)
        hs = np.zeros(len(tt))
        for s in (36, 37, 41):
            f = root * 2 ** (s / 12)
            hs += np.sin(2 * np.pi * f * tt * (1 + 0.002 * np.sin(2 * np.pi * 5 * tt))) * 0.3
        hs *= np.minimum(1, tt / 4)
        out += stereo(hs * high, 0, 1)
    if pulse:
        b = (np.sin(2 * np.pi * (pulse / 60) * tt) > 0.85).astype(float)
        p = lp(b, 120) * 6
        out += stereo(np.sin(2 * np.pi * root * tt) * p * 0.6)
    e = np.minimum(1, tt / 3) * np.minimum(1, (d - tt) / 3)
    out *= e[:, None]
    return out


def piano_motif(d, notes=(62, 65, 69, 68), every=4.0, seed=0):
    """notas de piano soltas e reverberadas (tema)."""
    rr = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    k = 1.0
    i = 0
    while k < d - 3:
        m = notes[i % len(notes)]
        f = 440 * 2 ** ((m - 69) / 12)
        tt = t_(3.5)
        x = sum((0.6 / h) * np.sin(2 * np.pi * f * h * tt * (1 + 0.0004 * h * h)) * np.exp(-tt * (1.2 + 0.6 * h)) for h in range(1, 7))
        x *= np.minimum(1, tt / 0.004)
        j = int(k * SR)
        out[j:j + len(x)] += x[:len(out) - j] * rr.uniform(0.7, 1.0)
        k += every * rr.uniform(0.85, 1.15)
        i += 1
    return reverb(out, 4.0, 0.55)
