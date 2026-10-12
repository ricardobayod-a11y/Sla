"""Primitivas de desenho procedurais (estilo silhueta cinematográfica)."""
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
PW, PH = 2208, 1242          # placa maior que o quadro para mover a câmera
SS = 2                       # supersampling das máscaras

FONT_DIR = '/usr/share/fonts'
FONTS = {
    'mono': '/usr/share/fonts/X11/Type1/c0419bt_.pfb',
    'serif': '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
    'serif_b': '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
    'sans': '/usr/share/fonts/opentype/inter/Inter-Regular.otf',
    'sans_b': '/usr/share/fonts/opentype/inter/Inter-Bold.otf',
    'sans_xb': '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf',
    'sans_l': '/usr/share/fonts/opentype/inter/Inter-Light.otf',
    'courier': '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
    'charter': '/usr/share/fonts/X11/Type1/c0648bt_.pfb',
}


def font(name, size):
    try:
        return ImageFont.truetype(FONTS[name], size)
    except Exception:
        return ImageFont.truetype(FONTS['serif'], size)


def rng(seed):
    return np.random.default_rng(seed)


# ---------------------------------------------------------------- ruído / gradientes
def fbm(h, w, scale=200, octaves=5, seed=0, persistence=0.5):
    r = rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    s = scale
    for _ in range(octaves):
        gh, gw = max(2, int(h / s) + 2), max(2, int(w / s) + 2)
        g = r.random((gh, gw)).astype(np.float32)
        up = cv2.resize(g, (int(gw * s), int(gh * s)), interpolation=cv2.INTER_CUBIC)[:h, :w]
        if up.shape != (h, w):
            up = cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
        out += amp * up
        tot += amp
        amp *= persistence
        s = max(2, s / 2)
    out /= tot
    out -= out.min()
    out /= max(1e-6, out.max())
    return out


def vgrad(h, w, stops):
    """stops: lista de (pos 0..1, (r,g,b))"""
    ys = np.linspace(0, 1, h, dtype=np.float32)
    img = np.zeros((h, w, 3), np.float32)
    pos = [p for p, _ in stops]
    for c in range(3):
        col = np.interp(ys, pos, [s[1][c] for s in stops]).astype(np.float32)
        img[:, :, c] = col[:, None]
    return img


def radial(h, w, cx, cy, r, power=2.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    return np.clip(1 - d, 0, 1) ** power


def col(c):
    return np.array(c, np.float32)


def comp(img, mask, color):
    m = mask[:, :, None]
    img *= (1 - m)
    img += m * col(color)
    return img


def add_glow(img, x, y, radius, color, strength=1.0):
    """brilho aditivo gaussiano (rápido, só na região)."""
    h, w = img.shape[:2]
    r = int(radius * 3)
    x0, x1 = max(0, int(x - r)), min(w, int(x + r))
    y0, y1 = max(0, int(y - r)), min(h, int(y + r))
    if x0 >= x1 or y0 >= y1:
        return img
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * radius * radius)) * strength
    img[y0:y1, x0:x1] += g[:, :, None] * col(color)[None, None, :]
    return img


class Mask:
    """Máscara desenhada com supersampling e antialias."""

    def __init__(self, w=PW, h=PH):
        self.w, self.h = w, h
        self.m = np.zeros((h * SS, w * SS), np.uint8)

    def poly(self, pts, v=255):
        p = (np.array(pts, np.float32) * SS).astype(np.int32)
        cv2.fillPoly(self.m, [p], v, lineType=cv2.LINE_AA)
        return self

    def circle(self, x, y, r, v=255):
        cv2.circle(self.m, (int(x * SS), int(y * SS)), max(1, int(r * SS)), v, -1, cv2.LINE_AA)
        return self

    def ellipse(self, x, y, rx, ry, ang=0, v=255):
        cv2.ellipse(self.m, (int(x * SS), int(y * SS)), (max(1, int(rx * SS)), max(1, int(ry * SS))), ang, 0, 360, v, -1, cv2.LINE_AA)
        return self

    def line(self, x0, y0, x1, y1, t, v=255):
        cv2.line(self.m, (int(x0 * SS), int(y0 * SS)), (int(x1 * SS), int(y1 * SS)), v, max(1, int(t * SS)), cv2.LINE_AA)
        return self

    def arc(self, x, y, rx, ry, a0, a1, t, ang=0, v=255):
        cv2.ellipse(self.m, (int(x * SS), int(y * SS)), (max(1, int(rx * SS)), max(1, int(ry * SS))), ang, a0, a1, v, max(1, int(t * SS)), cv2.LINE_AA)
        return self

    def rect(self, x0, y0, x1, y1, v=255):
        cv2.rectangle(self.m, (int(x0 * SS), int(y0 * SS)), (int(x1 * SS), int(y1 * SS)), v, -1, cv2.LINE_AA)
        return self

    def get(self, blur=0):
        m = cv2.resize(self.m, (self.w, self.h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        if blur:
            m = cv2.GaussianBlur(m, (0, 0), blur)
        return m


# ---------------------------------------------------------------- vegetação
def canopy(mk, base_y, top_y, x0, x1, seed, blob=60, density=1.0, jag=0.35):
    """linha de copas de mata atlântica: muitos círculos irregulares + troncos."""
    r = rng(seed)
    x = x0 - blob
    while x < x1 + blob:
        hgt = r.uniform(0.55, 1.0)
        ty = base_y - (base_y - top_y) * hgt
        bw = blob * r.uniform(0.7, 1.5)
        # tronco
        mk.poly([(x - bw * 0.06, base_y + 5), (x - bw * 0.03, ty + bw * 0.5), (x + bw * 0.03, ty + bw * 0.5), (x + bw * 0.06, base_y + 5)])
        # copa
        for _ in range(int(7 * density)):
            cx = x + r.normal(0, bw * 0.45)
            cy = ty + abs(r.normal(0, bw * 0.35))
            rr = bw * r.uniform(0.25, 0.55)
            mk.circle(cx, cy, rr)
        # galhos espetados
        for _ in range(int(3 * jag * 3)):
            a = r.uniform(-2.6, -0.5)
            L = bw * r.uniform(0.4, 0.9)
            sx, sy = x + r.normal(0, bw * 0.2), ty + bw * 0.2
            mk.line(sx, sy, sx + math.cos(a) * L, sy + math.sin(a) * L, max(1.5, bw * 0.03))
        x += bw * r.uniform(0.55, 1.0) / density
    mk.rect(x0 - 50, base_y, x1 + 50, mk.h + 10)


def araucaria(mk, x, base_y, height, seed, scale=1.0):
    """pinheiro-do-paraná (silhueta em candelabro)."""
    r = rng(seed)
    top = base_y - height
    tw = 6 * scale
    mk.poly([(x - tw, base_y), (x - tw * 0.5, top), (x + tw * 0.5, top), (x + tw, base_y)])
    tiers = 5
    for i in range(tiers):
        ty = top + i * height * 0.07
        span = (90 + i * 22) * scale * r.uniform(0.85, 1.15)
        for side in (-1, 1):
            ex = x + side * span
            ey = ty - 18 * scale
            mk.line(x, ty + 25 * scale, ex, ey, 4 * scale)
            mk.ellipse(ex - side * span * 0.15, ey - 6 * scale, span * 0.32, 16 * scale)
    mk.ellipse(x, top - 6 * scale, 110 * scale, 26 * scale)


def tall_tree(mk, x, base_y, height, seed, scale=1.0, lean=0.0):
    r = rng(seed)
    top = base_y - height
    tw = 14 * scale
    mk.poly([(x - tw, base_y + 5), (x - tw * 0.4 + lean * height, top + 40), (x + tw * 0.4 + lean * height, top + 40), (x + tw, base_y + 5)])
    for _ in range(9):
        a = r.uniform(-2.8, -0.3)
        L = r.uniform(60, 180) * scale
        sy = top + r.uniform(30, height * 0.45)
        sx = x + lean * (base_y - sy)
        ex, ey = sx + math.cos(a) * L, sy + math.sin(a) * L
        mk.line(sx, sy, ex, ey, r.uniform(2, 6) * scale)
        for _ in range(3):
            mk.circle(ex + r.normal(0, 20 * scale), ey + r.normal(0, 14 * scale), r.uniform(14, 36) * scale)


def vines(mk, x0, x1, y0, seed, n=8):
    r = rng(seed)
    for _ in range(n):
        x = r.uniform(x0, x1)
        L = r.uniform(80, 400)
        pts = []
        for i in range(12):
            yy = y0 + L * i / 11
            pts.append((x + math.sin(i * 0.9 + r.random() * 6) * 6, yy))
        for a, b in zip(pts, pts[1:]):
            mk.line(a[0], a[1], b[0], b[1], 2)


# ---------------------------------------------------------------- torre
def tower(mk, cx, base_y, top_y, base_w, top_w, cabin_frac=0.5, seed=0, cabin=True, thick=1.0):
    """torre treliçada. devolve dict com posições importantes."""
    def xl(y):
        f = (base_y - y) / (base_y - top_y)
        return cx - (base_w + (top_w - base_w) * f) / 2

    def xr(y):
        return 2 * cx - xl(y)

    t = 5 * thick
    # pernas
    mk.line(xl(base_y), base_y, xl(top_y), top_y, t * 1.6)
    mk.line(xr(base_y), base_y, xr(top_y), top_y, t * 1.6)
    mk.line(cx, base_y, cx, top_y, t * 0.6)
    # travessas em X
    n = 14
    ys = [base_y - (base_y - top_y) * i / n for i in range(n + 1)]
    for a, b in zip(ys, ys[1:]):
        mk.line(xl(a), a, xr(b), b, t * 0.55)
        mk.line(xr(a), a, xl(b), b, t * 0.55)
        mk.line(xl(b), b, xr(b), b, t * 0.8)
    # escada (lateral direita)
    sx = xr(base_y) + 14 * thick
    info = {}
    cab_y = base_y - (base_y - top_y) * cabin_frac
    if cabin:
        cw = (xr(cab_y) - xl(cab_y)) + 150 * thick
        ch = 120 * thick
        x0, x1 = cx - cw / 2, cx + cw / 2
        y0, y1 = cab_y - ch, cab_y
        mk.rect(x0, y0, x1, y1)
        mk.poly([(x0 - 18 * thick, y0 + 4), (cx, y0 - 34 * thick), (x1 + 18 * thick, y0 + 4)])  # telhado
        mk.rect(x0 - 26 * thick, y1, x1 + 26 * thick, y1 + 9 * thick)  # passarela
        for i in range(9):  # guarda-corpo
            xx = x0 - 26 * thick + i * (cw + 52 * thick) / 8
            mk.line(xx, y1, xx, y1 + 36 * thick, 2.5 * thick)
        mk.line(x0 - 26 * thick, y1 + 36 * thick, x1 + 26 * thick, y1 + 36 * thick, 3 * thick)
        # janelas (devolvidas pra iluminação)
        ww = cw * 0.22
        info['windows'] = [(x0 + cw * 0.12, y0 + ch * 0.25, x0 + cw * 0.12 + ww, y0 + ch * 0.7),
                           (x1 - cw * 0.12 - ww, y0 + ch * 0.25, x1 - cw * 0.12, y0 + ch * 0.7)]
        info['cabin'] = (x0, y0, x1, y1)
        # escada em zigue-zague até a cabine
        steps = 9
        for i in range(steps):
            ya = base_y - (base_y - y1) * i / steps
            yb = base_y - (base_y - y1) * (i + 1) / steps
            xa = xr(ya) + 10 * thick if i % 2 == 0 else xr(ya) + 60 * thick
            xb = xr(yb) + 60 * thick if i % 2 == 0 else xr(yb) + 10 * thick
            mk.line(xa, ya, xb, yb, 3.5 * thick)
            mk.line(xa, ya - 26 * thick, xb, yb - 26 * thick, 1.6 * thick)
    # antenas no topo
    mk.line(cx, top_y, cx, top_y - 130 * thick, 4 * thick)
    mk.rect(cx - 30 * thick, top_y - 70 * thick, cx - 18 * thick, top_y - 10 * thick)
    mk.rect(cx + 18 * thick, top_y - 90 * thick, cx + 30 * thick, top_y - 20 * thick)
    mk.ellipse(cx - 46 * thick, top_y - 40 * thick, 16 * thick, 22 * thick)
    info['light'] = (cx, top_y - 134 * thick)
    info['base'] = (cx, base_y)
    return info


# ---------------------------------------------------------------- figuras
def hooded(mk, x, feet_y, h, arms_up=False, seed=0, lean=0.0, width=1.0, torch=None):
    """figura encapuzada. devolve posição da cabeça (pra olhos) e da tocha."""
    r = rng(seed)
    w = h * 0.33 * width
    head_y = feet_y - h
    sh_y = head_y + h * 0.2
    lx = lean * h
    body = [(x - w * 0.55, feet_y), (x - w * 0.42 + lx * 0.5, sh_y + h * 0.1), (x - w * 0.28 + lx, sh_y),
            (x - w * 0.18 + lx, head_y + h * 0.05), (x + lx, head_y - h * 0.035),
            (x + w * 0.18 + lx, head_y + h * 0.05), (x + w * 0.28 + lx, sh_y),
            (x + w * 0.42 + lx * 0.5, sh_y + h * 0.1), (x + w * 0.55, feet_y)]
    # barra do manto irregular
    hem = [(x + w * 0.55 - i * w * 1.1 / 6, feet_y + r.uniform(-3, 4) * h / 200) for i in range(7)]
    mk.poly(body + hem[1:-1])
    if arms_up:
        for s in (-1, 1):
            ax, ay = x + s * w * 0.3 + lx, sh_y + h * 0.05
            hx, hy = x + s * w * 0.95 + lx, head_y - h * 0.32
            mk.poly([(ax - s * w * 0.1, ay + h * 0.12), (ax + s * w * 0.06, ay - h * 0.02), (hx + s * w * 0.12, hy), (hx - s * w * 0.05, hy + h * 0.04)])
            mk.circle(hx + s * w * 0.04, hy - h * 0.01, h * 0.03)
    tp = None
    if torch is not None:
        s = torch
        hx, hy = x + s * w * 0.62 + lx, sh_y + h * 0.18
        mk.poly([(x + s * w * 0.3 + lx, sh_y + h * 0.05), (x + s * w * 0.42 + lx, sh_y + h * 0.02), (hx + s * w * 0.06, hy), (hx - s * w * 0.04, hy + h * 0.06)])
        mk.line(hx, hy + h * 0.12, hx + s * w * 0.12, hy - h * 0.28, max(2, h * 0.022))
        tp = (hx + s * w * 0.12, hy - h * 0.3)
    return {'head': (x + lx, head_y + h * 0.1), 'torch': tp, 'eyes_dx': w * 0.075}


def man(mk, x, feet_y, h, pose='stand', seed=0, face=1):
    """silhueta do Daniel: stand, sit, crouch, lie, run, climb."""
    s = h / 100.0
    if pose == 'stand':
        mk.ellipse(x, feet_y - 92 * s, 7 * s, 8.5 * s)
        mk.poly([(x - 12 * s, feet_y - 82 * s), (x + 12 * s, feet_y - 82 * s), (x + 10 * s, feet_y - 45 * s), (x - 10 * s, feet_y - 45 * s)])
        mk.poly([(x - 9 * s, feet_y - 46 * s), (x - 1 * s, feet_y - 46 * s), (x - 3 * s, feet_y), (x - 9 * s, feet_y)])
        mk.poly([(x + 1 * s, feet_y - 46 * s), (x + 9 * s, feet_y - 46 * s), (x + 9 * s, feet_y), (x + 3 * s, feet_y)])
        mk.poly([(x - 12 * s, feet_y - 80 * s), (x - 16 * s, feet_y - 50 * s), (x - 12 * s, feet_y - 49 * s), (x - 9 * s, feet_y - 75 * s)])
        mk.poly([(x + 12 * s, feet_y - 80 * s), (x + 16 * s, feet_y - 50 * s), (x + 12 * s, feet_y - 49 * s), (x + 9 * s, feet_y - 75 * s)])
    elif pose == 'sit':  # sentado de lado, olhando pra frente (face=1 direita)
        f = face
        mk.ellipse(x + f * 4 * s, feet_y - 70 * s, 7 * s, 8.5 * s)
        mk.poly([(x - 10 * s, feet_y - 60 * s), (x + 10 * s, feet_y - 60 * s), (x + 9 * s, feet_y - 25 * s), (x - 11 * s, feet_y - 25 * s)])
        mk.poly([(x - 8 * s, feet_y - 30 * s), (x + f * 30 * s, feet_y - 30 * s), (x + f * 30 * s, feet_y - 20 * s), (x - 8 * s, feet_y - 20 * s)])
        mk.poly([(x + f * 24 * s, feet_y - 30 * s), (x + f * 32 * s, feet_y - 30 * s), (x + f * 32 * s, feet_y), (x + f * 25 * s, feet_y)])
        mk.poly([(x + f * 6 * s, feet_y - 56 * s), (x + f * 24 * s, feet_y - 46 * s), (x + f * 26 * s, feet_y - 50 * s), (x + f * 8 * s, feet_y - 60 * s)])
    elif pose == 'crouch':
        mk.ellipse(x, feet_y - 50 * s, 7 * s, 8.5 * s)
        mk.ellipse(x, feet_y - 25 * s, 16 * s, 24 * s)
        mk.ellipse(x + 8 * s, feet_y - 12 * s, 14 * s, 12 * s)
    elif pose == 'lie':
        mk.ellipse(x - 40 * s, feet_y - 10 * s, 8 * s, 7 * s)
        mk.ellipse(x, feet_y - 8 * s, 34 * s, 9 * s)
    elif pose == 'run':
        mk.ellipse(x + 8 * s, feet_y - 90 * s, 7 * s, 8.5 * s)
        mk.poly([(x - 6 * s, feet_y - 80 * s), (x + 12 * s, feet_y - 82 * s), (x + 4 * s, feet_y - 45 * s), (x - 12 * s, feet_y - 46 * s)])
        mk.poly([(x - 10 * s, feet_y - 48 * s), (x - 2 * s, feet_y - 46 * s), (x + 18 * s, feet_y - 22 * s), (x + 14 * s, feet_y - 1 * s), (x + 8 * s, feet_y - 4 * s), (x + 10 * s, feet_y - 20 * s)])
        mk.poly([(x - 4 * s, feet_y - 46 * s), (x - 12 * s, feet_y - 44 * s), (x - 26 * s, feet_y - 22 * s), (x - 34 * s, feet_y - 20 * s), (x - 32 * s, feet_y - 14 * s), (x - 20 * s, feet_y - 16 * s)])
        mk.poly([(x + 8 * s, feet_y - 78 * s), (x + 26 * s, feet_y - 62 * s), (x + 24 * s, feet_y - 58 * s), (x + 4 * s, feet_y - 70 * s)])
        mk.poly([(x - 4 * s, feet_y - 78 * s), (x - 22 * s, feet_y - 66 * s), (x - 20 * s, feet_y - 62 * s), (x - 2 * s, feet_y - 70 * s)])


def bell_shape(mk, x, y, size, ang=0.0):
    """sino pendurado (ang em radianos, pivô no topo)."""
    pts = []
    prof = [(0, 0.0), (0.12, 0.18), (0.2, 0.35), (0.25, 0.6), (0.32, 0.82), (0.45, 0.95), (0.47, 1.0)]
    for px, py in prof:
        pts.append((px, py))
    full = [(-px, py) for px, py in reversed(pts)] + pts
    ca, sa = math.cos(ang), math.sin(ang)
    out = []
    for px, py in full:
        X, Y = px * size, py * size + size * 0.12
        out.append((x + X * ca - Y * sa, y + X * sa + Y * ca))
    mk.poly(out)
    mk.circle(x, y + size * 0.06, size * 0.07)
    cx, cy = 0, size * 1.12
    mk.circle(x + cx * ca - cy * sa, y + cx * sa + cy * ca, size * 0.08)


# ---------------------------------------------------------------- texto
def text_layer(w, h, items):
    """items: (texto, (x,y), fonte, tamanho, cor rgb 0..1, alpha, anchor, jitter)
    devolve (rgb float, alpha float)"""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for it in items:
        txt, (x, y), fn, size, c, a = it[:6]
        anchor = it[6] if len(it) > 6 else 'la'
        jitter = it[7] if len(it) > 7 else 0
        f = font(fn, size)
        rgba = tuple(int(v * 255) for v in c) + (int(a * 255),)
        if jitter:
            r = rng(hash(txt) % 1000)
            cx = x
            for ch in txt:
                d.text((cx, y + r.normal(0, jitter)), ch, font=f, fill=rgba)
                cx += d.textlength(ch, font=f) * (1 + r.normal(0, 0.03))
        else:
            d.text((x, y), txt, font=f, fill=rgba, anchor=anchor)
    arr = np.asarray(im).astype(np.float32) / 255
    return arr[:, :, :3], arr[:, :, 3]


def textlen(txt, fn, size):
    f = font(fn, size)
    return f.getlength(txt)
