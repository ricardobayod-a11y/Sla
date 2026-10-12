"""Câmera + pós-processamento + escrita de clipes."""
import math
import subprocess
import numpy as np
import cv2
from art import W, H, PW, PH, rng, col, text_layer

FPS = 24

_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_d = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = np.clip(1.0 - 0.55 * np.clip(_d - 0.45, 0, 1.2) ** 1.6, 0.25, 1)[:, :, None].astype(np.float32)
_r = rng(123)
GRAIN = [(_r.normal(0, 1, (H // 2, W // 2)).astype(np.float32)) for _ in range(12)]
GRAIN = [cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)[:, :, None] for g in GRAIN]


def ease(x):
    x = min(1, max(0, x))
    return x * x * (3 - 2 * x)


def camera(img, lt, dur, cam, frame_i):
    z0, z1 = cam.get('z0', 1.0), cam.get('z1', 1.07)
    p = ease(lt / max(0.01, dur)) if cam.get('ease', True) else min(1, lt / max(0.01, dur))
    z = z0 + (z1 - z0) * p
    cx = (cam.get('x0', 0.5) + (cam.get('x1', cam.get('x0', 0.5)) - cam.get('x0', 0.5)) * p) * PW
    cy = (cam.get('y0', 0.5) + (cam.get('y1', cam.get('y0', 0.5)) - cam.get('y0', 0.5)) * p) * PH
    sh = cam.get('shake', 0.0)
    if sh:
        cx += sh * (6 * math.sin(lt * 1.7) + 3 * math.sin(lt * 5.3 + 1) + 1.5 * math.sin(lt * 13.1))
        cy += sh * (5 * math.sin(lt * 1.3 + 2) + 3 * math.sin(lt * 6.1) + 1.5 * math.sin(lt * 11.7 + 3))
    # janela visível em coordenadas da placa (zoom 1.0 = quadro 1920 dentro de 2208)
    vw, vh = W / z, H / z
    cx = min(max(cx, vw / 2), PW - vw / 2)
    cy = min(max(cy, vh / 2), PH - vh / 2)
    s = W / vw
    M = np.array([[s, 0, -(cx - vw / 2) * s], [0, s, -(cy - vh / 2) * s]], np.float32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def post(f, frame_i, fx):
    """fx: dict com grain, flicker, glitch, flash, exposure."""
    exp = fx.get('exposure', 1.0) * 1.3
    f *= exp
    fl = fx.get('flicker', 0)
    if fl:
        f *= 1 - fl * 0.5 * (0.5 + 0.5 * math.sin(frame_i * 1.7) * math.sin(frame_i * 0.37))
    f *= VIGNETTE
    # tonemap suave + leve tom frio nas sombras
    f = f / (1 + f * 0.35)
    f = np.clip(f, 0, None) ** 0.92
    g = fx.get('grain', 0.035)
    f += GRAIN[frame_i % len(GRAIN)] * g
    fl = fx.get('flash', 0)
    if fl:
        f += fl
    gl = fx.get('glitch', 0)
    if gl:
        r = rng(frame_i)
        shift = int(gl * 22)
        f[:, :, 0] = np.roll(f[:, :, 0], shift, axis=1)
        f[:, :, 2] = np.roll(f[:, :, 2], -shift, axis=1)
        for _ in range(int(gl * 8)):
            y = int(r.uniform(0, H - 40))
            hgt = int(r.uniform(4, 40))
            f[y:y + hgt] = np.roll(f[y:y + hgt], int(r.normal(0, 80 * gl)), axis=1)
    return np.clip(f * 255, 0, 255).astype(np.uint8)


class Writer:
    def __init__(self, path, fps=FPS):
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps),
                                   '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
                                   '-tune', 'grain', str(path)], stdin=subprocess.PIPE)

    def write(self, fr):
        self.p.stdin.write(fr.tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()


_text_cache = {}


def overlay_text(f, items, alpha):
    key = repr(items)
    if key not in _text_cache:
        _text_cache[key] = text_layer(W, H, items)
    rgb, a = _text_cache[key]
    a = a[:, :, None] * alpha
    return f * (1 - a) + rgb * 255 * a
