"""Alinha frases do roteiro com o áudio da narração (detecção de pausas + DP)."""
import re, json, subprocess, sys
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SR = 48000

def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)

def sections():
    t = (ROOT / 'roteiro/narracao.txt').read_text()
    out = {}
    for s in re.split(r'^## ', t, flags=re.M)[1:]:
        head, body = s.split('\n', 1)
        out[head.split()[0]] = ' '.join(l.strip() for l in body.strip().splitlines())
    return out

def split_sentences(text):
    parts = re.findall(r'.+?(?:\.\.\.|[.!?])["”]?(?=\s|$)|.+$', text)
    return [p.strip() for p in parts if p.strip()]

def gaps(x, win=0.01, min_gap=0.22):
    n = int(SR * win)
    m = len(x) // n
    rms = np.sqrt((x[:m * n].reshape(m, n) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    thr = max(db.max() - 38, np.percentile(db, 20) + 6)
    sil = db < thr
    out, i = [], 0
    while i < m:
        if sil[i]:
            j = i
            while j < m and sil[j]:
                j += 1
            if (j - i) * win >= min_gap:
                out.append(((i * win), (j * win)))
            i = j
        else:
            i += 1
    return out, m * win

def align(sents, gl, dur):
    # speech start/end
    start = gl[0][1] if gl and gl[0][0] <= 0.02 else 0.0
    end = gl[-1][0] if gl and gl[-1][1] >= dur - 0.05 else dur
    inner = [g for g in gl if g[0] > start + 0.05 and g[1] < end - 0.05]
    L = np.array([len(s) for s in sents], float)
    cum = np.cumsum(L)[:-1] / L.sum()
    exp = start + cum * (end - start)
    K, G = len(exp), len(inner)
    mids = np.array([(a + b) / 2 for a, b in inner])
    w = np.array([b - a for a, b in inner])
    if K == 0:
        return [(start, end)]
    if G < K:
        # not enough gaps: fall back to expected times
        b = list(exp)
    else:
        INF = 1e18
        D = np.full((K + 1, G + 1), INF); D[0, :] = 0
        P = np.zeros((K + 1, G + 1), int)
        for k in range(1, K + 1):
            for g in range(k, G + 1):
                skip = D[k, g - 1]
                cost = D[k - 1, g - 1] + (mids[g - 1] - exp[k - 1]) ** 2 - 0.15 * w[g - 1]
                if cost < skip:
                    D[k, g] = cost; P[k, g] = 1
                else:
                    D[k, g] = skip; P[k, g] = 0
        b, k, g = [], K, G
        while k > 0:
            if P[k, g] == 1:
                b.append(mids[g - 1]); k -= 1
            g -= 1
        b = b[::-1]
    edges = [start] + list(b) + [end]
    return [(edges[i], edges[i + 1]) for i in range(len(sents))]

def main():
    secs = sections()
    res = {}
    for sid, text in secs.items():
        p = ROOT / f'build/voz/{sid}.mp3'
        if not p.exists():
            continue
        x = load(p)
        gl, dur = gaps(x)
        sents = split_sentences(text)
        spans = align(sents, gl, dur)
        res[sid] = {'dur': len(x) / SR, 'sents': [{'t0': round(a, 3), 't1': round(b, 3), 'text': s} for s, (a, b) in zip(sents, spans)]}
    (ROOT / 'build/align.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for sid, r in res.items():
        print(sid, round(r['dur'], 1), len(r['sents']))

if __name__ == '__main__':
    main()
