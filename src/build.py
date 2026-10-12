"""Monta o vídeo completo: linha do tempo -> clipes renderizados + mixagem -> MP4 final.

uso: python3 src/build.py [layout|audio|video|final|all] [--preview]
"""
import sys
import json
import math
import hashlib
import subprocess
from pathlib import Path
from multiprocessing import Pool
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import timeline as TL  # noqa
from timeline import ALIGN, active_sections  # noqa

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / 'build'
FPS = 24
SR = 48000


# =============================================================== linha do tempo
def find_sentence(sid, txt):
    for i, s in enumerate(ALIGN[sid]['sents']):
        if s['text'].startswith(txt) or txt in s['text']:
            return i
    raise KeyError(f'{sid}: frase não encontrada: {txt}')


def layout():
    secs = []
    t = 0.0
    for s in active_sections():
        vid = s.get('narrated_as') or s['id']
        narrated = vid in ALIGN and not s.get('synthetic')
        if narrated:
            dur = s['lead'] + ALIGN[vid]['dur'] + s['tail']
            n0 = t + s['lead']
        else:
            dur = s['synthetic']
            n0 = t
        secs.append(dict(spec=s, vid=vid if narrated else None, t0=t, t1=t + dur, n0=n0))
        t += dur
    return secs, t


def resolve(m, sec):
    """marcador -> tempo absoluto."""
    if m[0] == 't':
        return sec['n0'] + m[1]
    if m[0] == 's':
        return sec['n0'] + ALIGN[sec['vid']]['sents'][m[1]]['t0'] + m[2]
    if m[0] == 'find':
        i = find_sentence(sec['vid'], m[1])
        return sec['n0'] + ALIGN[sec['vid']]['sents'][i]['t0'] + (m[2] if len(m) > 2 else 0)
    raise ValueError(m)


def is_marker(v):
    return isinstance(v, tuple) and len(v) >= 2 and v[0] in ('s', 't', 'find') and not isinstance(v[1], float) or (
        isinstance(v, tuple) and len(v) == 2 and v[0] == 't')


def resolve_kw(v, sec, shot_t0):
    if isinstance(v, tuple) and len(v) >= 2 and isinstance(v[0], str) and v[0] in ('s', 't', 'find'):
        return resolve(v, sec) - shot_t0
    if isinstance(v, list):
        return [resolve_kw(x, sec, shot_t0) for x in v]
    if isinstance(v, dict):
        return {k: resolve_kw(x, sec, shot_t0) for k, x in v.items()}
    return v


def build_shots(secs):
    shots = []
    for si, sec in enumerate(secs):
        sp = sec['spec']
        starts = [max(sec['t0'], resolve(m, sec)) for (m, *_r) in sp['shots']]
        starts[0] = sec['t0']
        for k, (m, name, kw, extra) in enumerate(sp['shots']):
            a = starts[k]
            b = starts[k + 1] if k + 1 < len(starts) else sec['t1']
            if b - a < 0.2:
                continue
            fx = []
            for (fm, kind, d, amt) in sp.get('fx', []):
                ft = resolve(fm, sec)
                if a - 1 <= ft < b:
                    fx.append((kind, ft - a, d, amt))
            texts = []
            for (m0, m1, txt, style) in sp.get('texts', []):
                x0, x1 = resolve(m0, sec), resolve(m1, sec)
                if x0 < b and x1 > a:
                    texts.append((x0 - a, x1 - a, txt, style))
            ch = sp.get('chapter')
            if ch and k == 0:
                texts.append((0.6, 5.0, ch, 'chapter'))
            first = k == 0
            last = k == len(sp['shots']) - 1
            shots.append(dict(i=len(shots), sec=sp['id'], name=name, kw=resolve_kw(dict(kw), sec, a), cam=extra.get('cam'),
                              t0=a, t1=b, fx=fx, texts=texts,
                              fade_in=0.6 if first else 0.1, fade_out=0.6 if last else 0.1))
    # quadros inteiros
    for s in shots:
        s['f0'] = int(round(s['t0'] * FPS))
        s['f1'] = int(round(s['t1'] * FPS))
    return shots


# =============================================================== vídeo
TEXT_STYLES = {
    'caption': dict(fn='serif', size=46, y=930, color=(0.88, 0.85, 0.8)),
    'center_small': dict(fn='serif', size=58, y=400, color=(0.88, 0.85, 0.8)),
    'center_small2': dict(fn='serif', size=58, y=520, color=(0.88, 0.85, 0.8)),
    'center_small3': dict(fn='serif', size=58, y=640, color=(0.95, 0.4, 0.35)),
    'chapter': dict(fn='sans_l', size=40, y=930, color=(0.85, 0.8, 0.75)),
}


def render_shot(shot):
    import scenes
    from render import camera, post, Writer, overlay_text
    out = BUILD / 'shots' / f"{shot['i']:03d}.mp4"
    key = hashlib.md5(json.dumps({k: v for k, v in shot.items() if k not in ('i',)}, sort_keys=True, default=str).encode()
                      + (Path(scenes.__file__).read_bytes())).hexdigest()
    stamp = out.with_suffix('.key')
    if out.exists() and stamp.exists() and stamp.read_text() == key:
        return shot['i'], 'cache'
    kw = dict(shot['kw'])
    seed = kw.pop('seed', shot['i'])
    if shot['cam']:
        kw['cam'] = shot['cam']
    sc = scenes.SCENES[shot['name']](seed=seed, **kw)
    cam = sc.cam
    n = shot['f1'] - shot['f0']
    dur = n / FPS
    w = Writer(out)
    for j in range(n):
        lt = j / FPS
        img = sc.draw(lt, dur)
        f = camera(img, lt, dur, cam, shot['f0'] + j)
        fx = {}
        for (kind, ft, d, amt) in shot['fx']:
            if ft <= lt < ft + d:
                if kind == 'glitch':
                    fx['glitch'] = amt
                elif kind == 'flash':
                    fx['flash'] = amt * (1 - (lt - ft) / d)
        fr = post(f, shot['f0'] + j, fx).astype(np.float32)
        for (x0, x1, txt, style) in shot['texts']:
            if x0 <= lt < x1:
                st = TEXT_STYLES[style]
                a = min(1, (lt - x0) / 0.6, (x1 - lt) / 0.6)
                if style == 'chapter':
                    items = [(txt, (110, st['y']), st['fn'], st['size'], st['color'], 1.0, 'ls')]
                    fr = overlay_text(fr, [(('—' * 3), (110, st['y'] - 70), 'sans_l', 30, (0.7, 0.15, 0.12), 1.0, 'ls')] + items, a)
                else:
                    items = [(txt, (962, st['y'] + 3), st['fn'], st['size'], (0, 0, 0), 0.8, 'mm'),
                             (txt, (960, st['y']), st['fn'], st['size'], st['color'], 1.0, 'mm')]
                    fr = overlay_text(fr, items, a)
        fi = min(1, lt / shot['fade_in']) if shot['fade_in'] else 1
        fo = min(1, (dur - lt) / shot['fade_out']) if shot['fade_out'] else 1
        k = min(fi, fo)
        if k < 1:
            fr *= max(0, k) ** 1.5
        w.write(np.clip(fr, 0, 255).astype(np.uint8))
    w.close()
    stamp.write_text(key)
    return shot['i'], 'ok'


def video(shots, workers=4, only=None):
    (BUILD / 'shots').mkdir(parents=True, exist_ok=True)
    todo = [s for s in shots if only is None or s['i'] in only]
    todo.sort(key=lambda s: -(s['f1'] - s['f0']))
    with Pool(workers) as p:
        for i, st in p.imap_unordered(render_shot, todo):
            print(f'shot {i:03d} {st}', flush=True)
    lst = BUILD / 'shots' / 'list.txt'
    lst.write_text(''.join(f"file '{s['i']:03d}.mp4'\n" for s in shots))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(BUILD / 'video.mp4')], check=True)


# =============================================================== áudio
def load_voice(vid):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(BUILD / 'voz' / f'{vid}.mp3'), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def sfx_lib():
    import audio as A
    L = {}

    def st(x, w=0.6):
        return A.stereo(x, 0, w) if x.ndim == 1 else x
    L['bell_far'] = A.bell(0.9)
    L['bell_far2'] = A.bell(0.7)
    L['bell_mid'] = A.bell(0.45)
    L['bell_close'] = A.bell(0.1, d=9)
    L['bell_tiny'] = A.bell(0.2, f0=780, d=3)
    L['hit'] = A.hit()
    L['hit_soft'] = A.hit(2.5) * 0.6
    L['boom'] = A.boom()
    L['boom_soft'] = A.boom(5, 36) * 0.6
    L['whoosh'] = A.whoosh()
    L['phone_buzz'] = st(A.phone_buzz())
    tt = A.t_(4.0)
    ring = (np.sin(2 * np.pi * 440 * tt) + np.sin(2 * np.pi * 480 * tt)) * ((tt % 2.0) < 1.0) * 0.3
    L['phone_ring'] = st(A.lp(ring, 3000))
    L['truck'] = st(A.truck(40.0), 1)
    L['steps_walk'] = st(A.footsteps_leaves(6.0, 1.8))
    steps = np.zeros(int(8 * SR))
    for k in range(12):
        s = A.metal_step(1.2)[:, 0] * 0.5
        j = int(k * 0.6 * SR)
        steps[j:j + len(s)] += s[:len(steps) - j]
    L['steps_climb'] = st(A.norm(steps, 0.7))
    steps = np.zeros(int(5 * SR))
    for k in range(18):
        s = A.metal_step(0.8)[:, 0] * 0.5
        j = int(k * 0.24 * SR)
        steps[j:j + len(s)] += s[:len(steps) - j]
    L['steps_run_metal'] = st(A.norm(steps, 0.7))
    pp = np.zeros(int(1.4 * SR))
    for k in range(9):
        b = A.bp(A.noise(0.12), 1500, 7000) * np.exp(-np.arange(int(0.12 * SR)) / (0.03 * SR))
        j = int(A.R.uniform(0, 1.2) * SR)
        pp[j:j + len(b)] += b[:len(pp) - j]
    L['paper'] = st(A.norm(pp, 0.5))
    L['generator_start'] = st(A.generator(6.0))
    L['generator'] = st(A.generator(9.0, die_at=6.0 + 0.3), 0.3)
    L['radio_click'] = st(A.radio_click())
    L['static'] = st(A.static(2.6))
    L['static_short'] = st(A.static(1.0))
    L['leaves'] = st(A.footsteps_leaves(3.0, 1.2))
    tt = A.t_(1.2)
    br = A.hp(A.noise(1.2), 800) * np.exp(-tt * 30) + np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 12)
    L['branch'] = A.reverb(A.norm(br, 0.8), 2.0, 0.35)
    L['heartbeat'] = st(A.heartbeat(10, 72), 0)
    L['book_close'] = st(A.norm(A.lp(A.noise(0.3), 400) * np.exp(-A.t_(0.3) * 25), 0.7))
    L['lamp_off'] = st(A.lamp_off())
    L['chant_long'] = A.chant(38.0)
    L['chant_close'] = A.chant(24.0, base=92.0)
    L['chant_short'] = A.chant(8.0)
    L['fall_roll'] = st(A.fall_roll())
    L['click'] = st(A.flashlight_click())
    L['riser'] = A.riser(4.0)
    L['riser_long'] = A.riser(8.0)
    L['scrape'] = st(A.scrape())
    L['metal_step'] = A.metal_step(3.0)
    L['creak'] = st(A.creak(2.0))
    L['scream'] = A.scream()
    wb = A.metal_step(1.5, 120)[:, 0]
    wb[:int(1.5 * SR)] += A.lp(A.noise(1.5), 300) * np.exp(-A.t_(1.5) * 8)
    L['window_bang'] = A.reverb(A.norm(wb, 0.8), 1.5, 0.3)
    L['run'] = st(A.footsteps_leaves(16.0, 3.6, run=True), 1)
    L['breath'] = st(A.breath(16.0, 1.4), 0.4)
    return L


# sons longos que passam por baixo da narração
SUSTAIN = {'bell': 0.55, 'chant': 0.45, 'run': 0.5, 'breath': 0.45, 'truck': 0.55, 'generator': 0.6,
           'heartbeat': 0.8, 'static': 0.7, 'steps': 0.7, 'riser': 0.7}


def place(buf, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    if pan:
        x = x * np.array([math.sqrt(1 - pan) if pan > 0 else 1, math.sqrt(1 + pan) if pan < 0 else 1])
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), len(buf) - i)
    if n > 0:
        buf[i:i + n] += x[:n] * gain


def mix(secs, total):
    import audio as A
    N = int((total + 1) * SR)
    voice = np.zeros((N, 2))
    music = np.zeros((N, 2))
    amb = np.zeros((N, 2))
    fx = np.zeros((N, 2))
    print('sfx...', flush=True)
    import pickle
    cache = BUILD / 'sfx.pkl'
    if cache.exists():
        L = pickle.loads(cache.read_bytes())
    else:
        L = sfx_lib()
        cache.write_bytes(pickle.dumps(L))
    amb_cache = {}

    def amb_seg(kind, d, seed):
        if kind == 'night':
            return A.ambience_night(d, 1.0, 1.0, 1.0, seed) * 0.9
        if kind == 'silent_wind':
            return A.ambience_night(d, 0, 0, 1.0, seed) * 0.8
        if kind == 'silent':
            return A.ambience_night(d, 0, 0, 0.45, seed) * 0.6
        if kind == 'day':
            return A.ambience_day(d, seed) * 1.0
        if kind == 'room':
            return A.ambience_room(d) * 1.0
        return np.zeros((int(d * SR), 2))

    print('voz/música/ambiência...', flush=True)
    for k, sec in enumerate(secs):
        sp = sec['spec']
        # voz
        if sec['vid']:
            v = load_voice(sec['vid'])
            v = A.hp(v, 70)
            rms = np.sqrt(np.mean(v[np.abs(v) > 0.01] ** 2))
            v = v * (0.12 / rms)
            v = np.tanh(v * 1.6) / 1.6
            vv = A.reverb(v, 0.6, 0.07, 6000)
            place(voice, vv, sec['n0'])
        # música
        m = sp.get('music', {})
        d = sec['t1'] - sec['t0'] + 3.0
        dr = A.drone(d, root=m.get('root', 36.71), intensity=m.get('intensity', 0.4), seed=k, high=m.get('high', 0.0), pulse=m.get('pulse', False))
        if m.get('piano'):
            dr += A.piano_motif(d, seed=k)[:len(dr)] * 0.6
        mutes = m.get('mute', [])
        if mutes:
            env = np.ones(len(dr))
            for a, b in zip(mutes[::2], mutes[1::2]):
                ia = int((resolve(a, sec) - sec['t0'] + 1.5) * SR)
                ib = int((resolve(b, sec) - sec['t0'] + 1.5) * SR)
                env[ia:ib] = 0.0
            env = np.convolve(env, np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
            dr *= env[:, None]
        place(music, dr, sec['t0'] - 1.5, 0.075 * (1 - 0.4 * m.get('intensity', 0.4)) * (1 - 0.3 * m.get('high', 0)))
        # ambiência
        segs = [(max(sec['t0'], resolve(mk, sec)), kind) for mk, kind in sp.get('amb', [])] or [(sec['t0'], 'silent')]
        segs[0] = (sec['t0'], segs[0][1])
        for j, (a, kind) in enumerate(segs):
            b = segs[j + 1][0] if j + 1 < len(segs) else sec['t1']
            dd = b - a + 1.0
            x = amb_seg(kind, dd, k * 10 + j)
            ramp = np.minimum(1, np.minimum(np.arange(len(x)) / (0.5 * SR), (len(x) - np.arange(len(x))) / (0.5 * SR)))
            place(amb, x * ramp[:, None], a - 0.5, 0.3)
        # efeitos
        for (mk, name, g, pan) in sp.get('sfx', []):
            for pre, mul in SUSTAIN.items():
                if name.startswith(pre):
                    g *= mul
            place(fx, L[name], resolve(mk, sec), g, pan)
        if sp.get('stepsS'):
            a, b, per = sp['stepsS']
            ta, tb = resolve(a, sec), resolve(b, sec)
            t = ta
            i = 0
            while t < tb:
                prog = (t - ta) / max(1, tb - ta)
                place(fx, L['metal_step'], t, 0.12 + 0.25 * prog, 0)
                t += per * (1 + 0.05 * math.sin(i))
                i += 1
    # ducking pela voz
    env = np.abs(voice[:, 0])
    w = int(0.3 * SR)
    env = np.convolve(env, np.ones(w) / w, 'same')
    env = env / (env.max() + 1e-9)
    duck = 1 - 0.7 * np.clip(env * 4, 0, 1)
    bg = (music * duck[:, None]) + amb * (0.4 + 0.6 * duck[:, None]) + fx * 0.6 * (0.55 + 0.45 * duck[:, None])
    for sec in secs:
        a, b = int(sec['t0'] * SR), int(sec['t1'] * SR)
        va = env[a:b] > 0.15
        if va.sum() > SR:
            rv = np.sqrt(np.mean(voice[a:b, 0][va] ** 2))
            rb = np.sqrt(np.mean(bg[a:b, 0][va] ** 2))
            print(f"  {sec['spec']['id']:>5} voz/fundo = {20 * np.log10(rv / (rb + 1e-9)):5.1f} dB", flush=True)
    master = voice + bg
    master = A.hp(master, 25)
    # normalização aproximada (-15 LUFS ~ RMS -18 dB) + limitador suave
    rms = np.sqrt(np.mean(master ** 2))
    master *= 10 ** (-17 / 20) / rms
    master = np.tanh(master * 1.1) / 1.1
    master *= 0.97 / np.max(np.abs(master))
    out = BUILD / 'mix.wav'
    from scipy.io import wavfile
    wavfile.write(out, SR, (master[:int(total * SR)] * 32767).astype(np.int16))
    print('mix ok', out, flush=True)


# =============================================================== final
def final(total):
    out = ROOT / 'saida' / 'A_Torre_video_final.mp4'
    out.parent.mkdir(exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(BUILD / 'video.mp4'), '-i', str(BUILD / 'mix.wav'), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', str(out)], check=True)
    print('final:', out, flush=True)


def chapters(secs):
    lines = []
    for s in secs:
        ch = s['spec'].get('chapter')
        if s['spec']['id'] == '01':
            lines.append(('0:00', 'Introdução'))
        elif ch:
            t = int(s['t0'])
            lines.append((f'{t // 60}:{t % 60:02d}', ch.split('.', 1)[1].strip().title()))
    return lines


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    secs, total = layout()
    shots = build_shots(secs)
    print(f'duração total: {total / 60:.1f} min, {len(shots)} planos', flush=True)
    (BUILD / 'layout.json').write_text(json.dumps(dict(total=total, chapters=chapters(secs),
                                                       sections=[dict(id=s['spec']['id'], t0=s['t0'], t1=s['t1']) for s in secs],
                                                       shots=shots), indent=1, ensure_ascii=False, default=str))
    if cmd in ('audio', 'all'):
        mix(secs, total)
    if cmd in ('video', 'all'):
        only = None
        if '--only' in sys.argv:
            only = set(int(x) for x in sys.argv[sys.argv.index('--only') + 1].split(','))
        video(shots, only=only)
    if cmd in ('final', 'all'):
        final(total)
