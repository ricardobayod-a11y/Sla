"""Cenas do vídeo. Cada cena monta uma placa estática e anima por cima."""
import math
import numpy as np
import cv2
from art import *  # noqa

NIGHT_SKY = [(0, (0.006, 0.009, 0.02)), (0.55, (0.03, 0.045, 0.075)), (1, (0.06, 0.085, 0.11))]
FAR, MID, NEAR = (0.032, 0.045, 0.062), (0.016, 0.022, 0.032), (0.004, 0.005, 0.008)
FOG = (0.11, 0.14, 0.17)
TORCH = (1.0, 0.52, 0.16)
RED = (1.0, 0.07, 0.04)
WARM = (1.0, 0.72, 0.38)


class Scene:
    cam = dict(z0=1.0, z1=1.07, x0=0.5, y0=0.5, x1=0.5, y1=0.5, shake=0.0)
    fog_amount = 0.0
    fog_speed = 12.0
    fog_band = (0.45, 0.85)

    def __init__(self, seed=0, **kw):
        self.seed = seed
        self.kw = kw
        self.plate = np.zeros((PH, PW, 3), np.float32)
        self.build(**kw)
        if self.fog_amount > 0:
            self._fog = fbm(PH, PW + 600, scale=260, octaves=4, seed=seed + 99)
            ys = np.linspace(0, 1, PH, dtype=np.float32)[:, None]
            a, b = self.fog_band
            band = np.clip((ys - a) / 0.12, 0, 1) * np.clip((b + 0.25 - ys) / 0.25, 0, 1)
            self._fog = np.clip((self._fog - 0.35) * 1.8, 0, 1) * band * self.fog_amount

    def build(self, **kw):
        pass

    def dyn(self, img, lt, dur):
        pass

    def draw(self, lt, dur):
        img = self.plate.copy()
        if self.fog_amount > 0:
            off = int((lt * self.fog_speed) % 600)
            f = self._fog[:, off:off + PW][:, :, None]
            img *= (1 - f * 0.85)
            img += f * col(FOG)
        self.dyn(img, lt, dur)
        return img


def night_base(seed, horizon=0.62, moon=(0.78, 0.18), stars=True, layers=3, araucarias=True):
    img = vgrad(PH, PW, NIGHT_SKY)
    clouds = fbm(PH, PW, 320, 5, seed + 1)
    ys = np.linspace(0, 1, PH, dtype=np.float32)[:, None]
    img += (np.clip(clouds - 0.45, 0, 1) * 0.06 * (1 - ys))[:, :, None] * col((0.6, 0.7, 0.85))
    if stars:
        r = rng(seed + 2)
        for _ in range(260):
            x, y = r.uniform(0, PW), r.uniform(0, PH * horizon * 0.9)
            b = r.uniform(0.05, 0.4) * (1 - y / (PH * horizon))
            if 0 <= int(y) < PH and 0 <= int(x) < PW:
                img[int(y), int(x)] += b
    if moon:
        mx, my = moon[0] * PW, moon[1] * PH
        add_glow(img, mx, my, 160, (0.25, 0.3, 0.38), 0.6)
        add_glow(img, mx, my, 50, (0.4, 0.45, 0.5), 0.6)
        m = Mask().circle(mx, my, 34).get(0.6)
        moonc = fbm(PH, PW, 18, 3, seed + 3) * 0.15 + 0.78
        img = img * (1 - m[:, :, None]) + (m * moonc)[:, :, None] * col((0.85, 0.88, 0.92))
        # nuvem passando na frente
        cm = np.clip(fbm(PH, PW, 120, 4, seed + 4) - 0.55, 0, 1) * 2.5 * radial(PH, PW, mx, my, 260, 1.0)
        img = img * (1 - cm[:, :, None] * 0.7) + cm[:, :, None] * 0.7 * col((0.05, 0.06, 0.08))
    hy = PH * horizon
    for i, (c, top, blob, dens) in enumerate([(FAR, hy - 120, 55, 1.2), (MID, hy - 40, 80, 1.0), (NEAR, hy + 120, 120, 0.9)][:layers]):
        mk = Mask()
        canopy(mk, hy + 60 + i * 120, top, -40, PW + 40, seed + 10 + i, blob=blob, density=dens)
        if araucarias and i < 2:
            r = rng(seed + 20 + i)
            for _ in range(3 + i):
                araucaria(mk, r.uniform(0, PW), hy + 40 + i * 110, r.uniform(260, 420) * (1 + i * 0.4), seed + 30 + i, 0.9 + i * 0.5)
        comp(img, mk.get(), c)
        # neblina entre camadas
        fy = np.clip(1 - np.abs(ys - (hy + 80 + i * 120) / PH) / 0.09, 0, 1)
        img += (fy * 0.035 * (1 - i * 0.3))[:, :, None] * col(FOG)
    return img


# =================================================================== exteriores
class TowerNight(Scene):
    """plano geral: torre acima da mata."""
    fog_amount = 0.55
    fog_band = (0.42, 0.9)

    def build(self, cabin_lit=True, ring=False, side=0.42, scale=0.85, moon=(0.8, 0.16), cam=None, lights_out=None, figures=False):
        self.cam = cam or dict(z0=1.0, z1=1.1, x0=0.5, y0=0.55, x1=0.5, y1=0.5)
        img = night_base(self.seed, horizon=0.66, moon=moon)
        cx = PW * side
        base_y = PH * 0.78
        top = PH * (0.78 - 0.66 * scale)
        mk = Mask()
        self.t = tower(mk, cx, base_y, top, 230 * scale, 60 * scale, cabin_frac=0.52, thick=scale)  # noqa
        tm = mk.get()
        comp(img, tm, (0.008, 0.009, 0.013))
        # luar no contorno
        edge = np.clip(cv2.GaussianBlur(tm, (0, 0), 2) - tm, 0, 1)
        img += edge[:, :, None] * col((0.12, 0.14, 0.18)) * 1.5
        # mata da frente cobrindo a base
        mk2 = Mask()
        canopy(mk2, PH * 0.98, PH * 0.74, -40, PW + 40, self.seed + 77, blob=110, density=1.1)
        self.front = mk2.get()
        self.cabin_lit = cabin_lit
        self.ring = ring
        self.lights_out = lights_out
        self.figures = figures
        self.base = img
        self.plate = img.copy()
        if cabin_lit:
            self._lit(self.plate, 1.0)
        comp(self.plate, self.front, (0.003, 0.004, 0.006))
        self.plate_dark = img.copy()
        comp(self.plate_dark, self.front, (0.003, 0.004, 0.006))
        r = rng(self.seed + 5)
        bx, by = self.t['base']
        self.ring_pts = [(bx + math.cos(a) * 260 * scale, by + 30 + math.sin(a) * 60 * scale) for a in np.linspace(0, 2 * math.pi, 11, endpoint=False)]
        self.ph = r.uniform(0, 6, 20)

    def _lit(self, img, k):
        for (x0, y0, x1, y1) in self.t['windows']:
            m = Mask().rect(x0, y0, x1, y1).get(0.8)
            img += m[:, :, None] * col(WARM) * 0.9 * k
            add_glow(img, (x0 + x1) / 2, (y0 + y1) / 2, 60, WARM, 0.18 * k)

    def dyn(self, img, lt, dur):
        out = self.lights_out is not None and lt >= self.lights_out
        if out:
            img[:] = self.plate_dark
            if self.fog_amount > 0:
                off = int((lt * self.fog_speed) % 600)
                f = self._fog[:, off:off + PW][:, :, None]
                img *= (1 - f * 0.85)
                img += f * col(FOG) * 0.6
        else:
            lx, ly = self.t['light']
            blink = 0.5 + 0.5 * math.sin(lt * 2 * math.pi / 1.6)
            blink = blink ** 3
            add_glow(img, lx, ly, 10, RED, 1.2 * blink + 0.15)
            add_glow(img, lx, ly, 70, RED, 0.18 * blink)
        if self.ring:
            for i, (x, y) in enumerate(self.ring_pts):
                fl = 0.75 + 0.25 * math.sin(lt * 9 + self.ph[i]) * math.sin(lt * 5.3 + self.ph[i] * 2)
                add_glow(img, x, y, 7, TORCH, 1.4 * fl)
                add_glow(img, x, y, 45, TORCH, 0.12 * fl)


class TowerUp(Scene):
    """contra-plongée: olhando a torre de baixo."""
    fog_amount = 0.25
    fog_band = (0.0, 0.5)

    def build(self, dusk=False, cam=None):
        self.cam = cam or dict(z0=1.12, z1=1.0, x0=0.5, y0=0.62, x1=0.5, y1=0.42)
        if dusk:
            img = vgrad(PH, PW, [(0, (0.05, 0.05, 0.1)), (0.6, (0.22, 0.12, 0.12)), (1, (0.45, 0.22, 0.12))])
        else:
            img = vgrad(PH, PW, [(0, (0.01, 0.012, 0.025)), (1, (0.05, 0.07, 0.1))])
        cl = fbm(PH, PW, 300, 5, self.seed)
        img += (np.clip(cl - 0.4, 0, 1) * 0.12)[:, :, None] * (col((0.5, 0.3, 0.3)) if dusk else col((0.4, 0.5, 0.6)))
        mk = Mask()
        cx = PW * 0.5
        # perspectiva forte: base larguíssima
        self.t = tower(mk, cx, PH * 1.6, PH * 0.06, 1700, 120, cabin_frac=0.62, thick=2.4)
        comp(img, mk.get(), (0.01, 0.01, 0.014))
        mk2 = Mask()
        tall_tree(mk2, PW * 0.05, PH * 1.05, PH * 1.1, self.seed + 1, 2.0, 0.08)
        tall_tree(mk2, PW * 0.97, PH * 1.05, PH * 1.0, self.seed + 2, 2.0, -0.1)
        canopy(mk2, PH * 1.1, PH * 0.88, -40, PW + 40, self.seed + 3, blob=150)
        comp(img, mk2.get(), (0.003, 0.004, 0.005))
        self.plate = img

    def dyn(self, img, lt, dur):
        lx, ly = self.t['light']
        if 0 <= ly < PH:
            b = (0.5 + 0.5 * math.sin(lt * 2 * math.pi / 1.6)) ** 3
            add_glow(img, lx, ly, 18, RED, 1.2 * b + 0.15)
            add_glow(img, lx, ly, 120, RED, 0.15 * b)


class Road(Scene):
    """estrada de terra no meio da mata, caminhonete."""
    fog_amount = 0.35
    fog_band = (0.35, 0.75)

    def build(self, truck=True, gate=False, dawn=False, cam=None, person=False):
        self.cam = cam or dict(z0=1.0, z1=1.12, x0=0.5, y0=0.55, x1=0.5, y1=0.55)
        if dawn:
            sky = [(0, (0.12, 0.12, 0.16)), (0.5, (0.45, 0.3, 0.25)), (1, (0.75, 0.45, 0.25))]
        else:
            sky = [(0, (0.12, 0.15, 0.15)), (1, (0.3, 0.34, 0.32))]
        img = vgrad(PH, PW, sky)
        hy = PH * 0.5
        vx = PW * 0.5
        # chão
        ground = vgrad(PH, PW, [(0, (0.05, 0.06, 0.05)), (1, (0.09, 0.08, 0.06))])
        gm = np.zeros((PH, PW), np.float32)
        gm[int(hy):] = 1
        img = img * (1 - gm[:, :, None]) + ground * gm[:, :, None]
        road = Mask().poly([(vx - 30, hy), (vx + 30, hy), (PW * 0.95, PH), (PW * 0.05, PH)]).get(2)
        tex = fbm(PH, PW, 30, 4, self.seed + 5)[:, :, None]
        rc = (col((0.2, 0.16, 0.12)) * (0.7 + 0.5 * tex)) * (0.6 if not dawn else 1.0)
        img = img * (1 - road[:, :, None]) + rc * road[:, :, None]
        # sulcos das rodas
        for dx in (-0.22, 0.22):
            m = Mask().poly([(vx + dx * 60 - 3, hy), (vx + dx * 60 + 3, hy), (vx + dx * PW * 0.9 + 40, PH), (vx + dx * PW * 0.9 - 40, PH)]).get(3)
            img *= (1 - m[:, :, None] * 0.35)
        # paredes de mata dos dois lados
        for side in (-1, 1):
            mk = Mask()
            r = rng(self.seed + side + 7)
            for i in range(26):
                f = i / 25
                x = vx + side * (60 + f ** 1.6 * PW * 0.62)
                yb = hy + f ** 1.6 * PH * 0.55
                hh = 120 + f ** 1.5 * 1500
                tall_tree(mk, x + r.normal(0, 30 * f + 5), yb, hh, self.seed + i * 3 + side, 0.3 + f * 2.2, side * r.uniform(0.0, 0.06))
            pts = [(vx + side * 40, hy - 60), (vx + side * PW * 0.8, -50), (vx + side * PW, -50), (vx + side * PW, PH), (vx + side * PW * 0.7, PH)]
            mk.poly([(vx + side * 70, hy + 5), (vx + side * PW * 0.72, PH), (vx + side * PW, PH), (vx + side * PW, hy - 200), (vx + side * 80, hy - 140)])
            comp(img, mk.get(), (0.02, 0.028, 0.025) if not dawn else (0.04, 0.035, 0.04))
        # raios de luz
        rays = np.zeros((PH, PW), np.float32)
        r = rng(self.seed + 50)
        for _ in range(7):
            x = r.uniform(PW * 0.3, PW * 0.7)
            m = Mask().poly([(x - 10, 0), (x + 25, 0), (x + 260, PH), (x + 120, PH)]).get(25)
            rays += m * r.uniform(0.3, 1)
        img += (rays * 0.06)[:, :, None] * (col((1, 0.9, 0.7)) if not dawn else col((1, 0.7, 0.4)))
        if gate:
            mk = Mask()
            gx, gy = PW * 0.25, PH * 0.83
            mk.rect(gx - 14, gy - 300, gx + 14, gy + 30)
            for i in range(5):
                y = gy - 250 + i * 55
                mk.line(gx, y, gx + 620, y + 160 + i * 18, 18)
            mk.line(gx, gy - 260, gx + 600, gy + 60, 14)
            comp(img, mk.get(), (0.05, 0.045, 0.035))
            moss = np.clip(fbm(PH, PW, 12, 3, 9) - 0.5, 0, 1) * 2 * mk.get()
            img += moss[:, :, None] * col((0.05, 0.12, 0.03))
        self.truck = truck
        if truck:
            mk = Mask()
            tx, ty, s = vx, PH * 0.86, 1.0
            mk.rect(tx - 330, ty - 260, tx + 330, ty)               # caçamba
            mk.poly([(tx - 270, ty - 260), (tx - 230, ty - 430), (tx + 230, ty - 430), (tx + 270, ty - 260)])  # cabine
            mk.rect(tx - 350, ty - 40, tx + 350, ty + 10)
            mk.rect(tx - 320, ty, tx - 200, ty + 70)
            mk.rect(tx + 200, ty, tx + 320, ty + 70)
            comp(img, mk.get(), (0.025, 0.025, 0.028))
            win = Mask().poly([(tx - 220, ty - 270), (tx - 195, ty - 405), (tx + 195, ty - 405), (tx + 220, ty - 270)]).get(1)
            img = img * (1 - win[:, :, None] * 0.5) + win[:, :, None] * 0.5 * col((0.12, 0.13, 0.13))
            hm = Mask()
            man(hm, tx - 100, ty - 270, 150, 'stand')
            man(hm, tx + 100, ty - 270, 160, 'stand')
            img *= 1 - hm.get()[:, :, None] * win[:, :, None] * 0.9
            self.tl = [(tx - 300, ty - 150), (tx + 300, ty - 150)]
        if person:
            mk = Mask()
            man(mk, PW * 0.42, PH * 0.9, 260, 'crouch')
            comp(img, mk.get(), (0.02, 0.02, 0.02))
        self.plate = img
        self.dawn = dawn

    def dyn(self, img, lt, dur):
        if self.truck:
            for x, y in self.tl:
                add_glow(img, x, y, 14, (1, 0.05, 0.03), 1.0)
                add_glow(img, x, y, 60, (1, 0.05, 0.03), 0.15)
        if self.dawn and not self.truck:
            k = min(1, lt / 3)
            for dx in (-60, 60):
                add_glow(img, PW * 0.5 + dx * (0.3 + k), PH * 0.53 + 20 * k, 10 + 20 * k, (1, 0.95, 0.8), 1.2)
                add_glow(img, PW * 0.5 + dx * (0.3 + k), PH * 0.53 + 20 * k, 90 + 90 * k, (1, 0.9, 0.7), 0.12 * k)


class Trail(Scene):
    """trilha estreita, crepúsculo, topo da torre aparecendo."""
    fog_amount = 0.3
    fog_band = (0.5, 0.95)

    def build(self, cam=None):
        self.cam = cam or dict(z0=1.08, z1=1.0, x0=0.5, y0=0.62, x1=0.5, y1=0.4)
        img = vgrad(PH, PW, [(0, (0.06, 0.05, 0.1)), (0.45, (0.3, 0.14, 0.14)), (0.7, (0.55, 0.25, 0.12)), (1, (0.2, 0.1, 0.06))])
        mk = Mask()
        self.t = tower(mk, PW * 0.6, PH * 0.75, PH * 0.05, 300, 80, cabin_frac=0.5, thick=1.1)
        comp(img, mk.get(), (0.04, 0.025, 0.03))
        mk = Mask()
        canopy(mk, PH * 0.9, PH * 0.6, -40, PW + 40, self.seed + 3, blob=90)
        comp(img, mk.get(), (0.035, 0.02, 0.025))
        mk = Mask()
        for x, h, s in [(PW * 0.08, PH * 1.2, 2.2), (PW * 0.25, PH * 1.0, 1.5), (PW * 0.84, PH * 1.1, 2.0), (PW * 0.97, PH * 1.2, 2.5)]:
            tall_tree(mk, x, PH * 1.05, h, int(x), s)
        mk.poly([(0, PH * 0.92), (PW * 0.42, PH * 0.86), (PW * 0.58, PH * 0.86), (PW, PH * 0.92), (PW, PH), (0, PH)])
        vines(mk, 0, PW, 0, 4, 12)
        comp(img, mk.get(), (0.008, 0.006, 0.008))
        path = Mask().poly([(PW * 0.47, PH * 0.86), (PW * 0.53, PH * 0.86), (PW * 0.7, PH), (PW * 0.3, PH)]).get(4)
        img += path[:, :, None] * col((0.06, 0.035, 0.025))
        mk = Mask()
        man(mk, PW * 0.49, PH * 0.9, 110, 'stand')
        man(mk, PW * 0.53, PH * 0.905, 118, 'stand')
        comp(img, mk.get(), (0.005, 0.004, 0.005))
        self.plate = img

    def dyn(self, img, lt, dur):
        lx, ly = self.t['light']
        b = (0.5 + 0.5 * math.sin(lt * 2 * math.pi / 1.6)) ** 3
        add_glow(img, lx, ly, 9, RED, 1.2 * b + 0.15)


class FogSea(Scene):
    """amanhecer: mar de neblina visto da torre."""
    fog_amount = 0.6
    fog_speed = 6
    fog_band = (0.5, 1.0)

    def build(self, cam=None, evening=False):
        self.cam = cam or dict(z0=1.0, z1=1.08, x0=0.45, y0=0.5, x1=0.55, y1=0.5)
        if evening:
            img = vgrad(PH, PW, [(0, (0.08, 0.08, 0.14)), (0.5, (0.4, 0.22, 0.2)), (0.62, (0.8, 0.45, 0.25)), (1, (0.5, 0.45, 0.45))])
        else:
            img = vgrad(PH, PW, [(0, (0.25, 0.32, 0.42)), (0.5, (0.65, 0.62, 0.6)), (0.62, (0.95, 0.8, 0.62)), (1, (0.7, 0.72, 0.74))])
        add_glow(img, PW * 0.35, PH * 0.58, 220, (1, 0.85, 0.6), 0.35)
        add_glow(img, PW * 0.35, PH * 0.58, 50, (1, 0.95, 0.8), 0.6)
        mk = Mask()
        canopy(mk, PH * 0.7, PH * 0.6, -40, PW + 40, self.seed + 1, blob=40, density=0.6)
        comp(img, mk.get(), (0.35, 0.38, 0.42) if not evening else (0.25, 0.2, 0.25))
        fog = fbm(PH, PW, 200, 5, self.seed + 2)
        ys = np.linspace(0, 1, PH, dtype=np.float32)[:, None]
        band = np.clip((ys - 0.6) / 0.08, 0, 1)
        fa = np.clip(0.55 + fog * 0.6, 0, 1) * band
        fc = col((0.85, 0.84, 0.84)) if not evening else col((0.6, 0.45, 0.42))
        img = img * (1 - fa[:, :, None]) + fa[:, :, None] * fc
        mk = Mask()
        r = rng(self.seed)
        for i in range(14):
            araucaria(mk, r.uniform(0, PW), PH * 0.8, r.uniform(120, 260), i, r.uniform(0.4, 0.8))
        comp(img, mk.get(), (0.3, 0.33, 0.36) if not evening else (0.2, 0.15, 0.18))
        # guarda-corpo da cabine no primeiro plano
        mk = Mask()
        mk.rect(0, PH * 0.88, PW, PH * 0.9)
        mk.rect(0, PH * 0.97, PW, PH)
        for i in range(12):
            mk.rect(i * PW / 11 - 6, PH * 0.88, i * PW / 11 + 6, PH)
        comp(img, mk.get(), (0.05, 0.05, 0.055))
        self.plate = img


# =================================================================== interiores
class Cabin(Scene):
    """cabine por dentro: parede de tábuas, janela, mesa, rádio, cama."""

    def build(self, lamp=True, pose=None, window_torches=0, flicker=False, cam=None, moon=True, items=True, door=False):
        self.cam = cam or dict(z0=1.0, z1=1.07, x0=0.5, y0=0.5, x1=0.5, y1=0.5)
        wall = vgrad(PH, PW, [(0, (0.09, 0.065, 0.045)), (1, (0.05, 0.035, 0.025))])
        tex = fbm(PH, PW, 6, 3, self.seed)
        planks = (np.sin(np.linspace(0, PW / 95 * 2 * np.pi, PW)) > 0.985).astype(np.float32)[None, :]
        wall *= (0.75 + 0.35 * tex[:, :, None])
        wall *= (1 - planks[:, :, None] * 0.6)
        grain = fbm(PH, PW, 3, 2, self.seed + 1)
        wall *= (0.9 + 0.15 * grain[:, :, None])
        img = wall
        # janela
        wx0, wy0, wx1, wy1 = PW * 0.18, PH * 0.16, PW * 0.52, PH * 0.56
        self.win = (wx0, wy0, wx1, wy1)
        sub = night_base(self.seed + 7, horizon=0.55, moon=(0.75, 0.2) if moon else None, araucarias=True)
        sub = cv2.resize(sub, (int(wx1 - wx0), int(wy1 - wy0)), interpolation=cv2.INTER_AREA)
        img[int(wy0):int(wy0) + sub.shape[0], int(wx0):int(wx0) + sub.shape[1]] = sub
        mk = Mask()
        t = 18
        mk.rect(wx0 - t, wy0 - t, wx1 + t, wy0 + 4)
        mk.rect(wx0 - t, wy1 - 4, wx1 + t, wy1 + t)
        mk.rect(wx0 - t, wy0, wx0 + 4, wy1)
        mk.rect(wx1 - 4, wy0, wx1 + t, wy1)
        mk.rect((wx0 + wx1) / 2 - 6, wy0, (wx0 + wx1) / 2 + 6, wy1)
        mk.rect(wx0, (wy0 + wy1) / 2 - 5, wx1, (wy0 + wy1) / 2 + 5)
        comp(img, mk.get(), (0.035, 0.024, 0.016))
        # chão
        fl = Mask().poly([(0, PH * 0.82), (PW, PH * 0.82), (PW, PH), (0, PH)]).get()
        comp(img, fl, (0.03, 0.022, 0.016))
        mk = Mask()
        if items:
            # mesa sob a janela
            mk.rect(PW * 0.14, PH * 0.6, PW * 0.58, PH * 0.635)
            mk.rect(PW * 0.16, PH * 0.635, PW * 0.175, PH * 0.88)
            mk.rect(PW * 0.545, PH * 0.635, PW * 0.56, PH * 0.88)
            # rádio
            mk.rect(PW * 0.4, PH * 0.52, PW * 0.53, PH * 0.6)
            mk.line(PW * 0.51, PH * 0.52, PW * 0.53, PH * 0.38, 4)
            # caderno, lanterna
            mk.poly([(PW * 0.24, PH * 0.596), (PW * 0.33, PH * 0.59), (PW * 0.335, PH * 0.6), (PW * 0.245, PH * 0.604)])
            mk.rect(PW * 0.35, PH * 0.578, PW * 0.385, PH * 0.6)
            # prateleiras com latas
            for k in range(3):
                y = PH * (0.22 + k * 0.13)
                mk.rect(PW * 0.64, y, PW * 0.8, y + 10)
                for j in range(7):
                    x = PW * 0.65 + j * 42
                    mk.rect(x, y - 48, x + 30, y)
            # cama
            mk.rect(PW * 0.62, PH * 0.66, PW * 1.02, PH * 0.74)
            mk.rect(PW * 0.62, PH * 0.74, PW * 0.635, PH * 0.84)
            mk.ellipse(PW * 0.95, PH * 0.645, 90, 28)
            mk.rect(PW * 0.6, PH * 0.48, PW * 0.615, PH * 0.84)
        if door:
            mk.rect(PW * 0.84, PH * 0.12, PW * 0.99, PH * 0.82)
        if pose == 'sit':
            man(mk, PW * 0.3, PH * 0.83, 420, 'sit', face=1)
        elif pose == 'lie':
            man(mk, PW * 0.82, PH * 0.66, 520, 'lie')
        elif pose == 'crouch':
            man(mk, PW * 0.08, PH * 0.86, 520, 'crouch')
        elif pose == 'window':
            man(mk, PW * 0.36, PH * 0.9, 640, 'stand')
        comp(img, mk.get(), (0.012, 0.009, 0.007))
        # luz da lâmpada
        self.lamp = (PW * 0.5, PH * 0.07)
        light = radial(PH, PW, self.lamp[0], self.lamp[1] + 250, 1300, 1.4)
        self.lit = img * (0.25 + 1.6 * light[:, :, None]) * col((1.0, 0.85, 0.65))
        moonl = radial(PH, PW, (wx0 + wx1) / 2, PH * 0.7, 900, 1.6)
        self.dark = img * (0.08 + 0.35 * moonl[:, :, None]) * col((0.55, 0.7, 1.0))
        # a janela continua com a cor da noite
        wm = Mask().rect(wx0 + 4, wy0 + 4, wx1 - 4, wy1 - 4).get()[:, :, None]
        self.lit = self.lit * (1 - wm) + img * wm
        self.dark = self.dark * (1 - wm) + img * wm
        mk = Mask().line(self.lamp[0], 0, self.lamp[0], self.lamp[1], 3).ellipse(self.lamp[0], self.lamp[1] + 12, 16, 22).get()
        self.bulb = mk
        self.lamp_on = lamp
        self.flicker = flicker
        self.window_torches = window_torches
        self.plate = self.lit if lamp else self.dark
        r = rng(3)
        self.tp = [(wx0 + (wx1 - wx0) * r.uniform(0.15, 0.85), wy0 + (wy1 - wy0) * r.uniform(0.62, 0.8)) for _ in range(11)]
        self.ph = r.uniform(0, 6, 11)

    def dyn(self, img, lt, dur):
        on = self.lamp_on
        if isinstance(on, (int, float)) and not isinstance(on, bool):
            on = lt < on  # apaga em lt
        k = 1.0
        if self.flicker:
            k = 0.75 + 0.25 * math.sin(lt * 31) * math.sin(lt * 7.7)
            if (lt * 3.1) % 4 < 0.15:
                k *= 0.3
        if on:
            if k != 1.0:
                img[:] = self.dark + (self.lit - self.dark) * k
            else:
                img[:] = self.lit
            comp(img, self.bulb, (1.0, 0.9, 0.7))
            add_glow(img, self.lamp[0], self.lamp[1] + 14, 30, WARM, 1.2 * k)
            add_glow(img, self.lamp[0], self.lamp[1] + 14, 180, WARM, 0.12 * k)
        else:
            img[:] = self.dark
            comp(img, self.bulb, (0.02, 0.02, 0.02))
        for i in range(self.window_torches):
            x, y = self.tp[i]
            fl = 0.7 + 0.3 * math.sin(lt * 8 + self.ph[i])
            add_glow(img, x, y, 3, TORCH, 1.5 * fl)
            add_glow(img, x, y, 14, TORCH, 0.15 * fl)


class WindowNorth(Scene):
    """olhando pela janela da cabine para a mata ao norte."""
    fog_amount = 0.45
    fog_band = (0.4, 0.95)

    def build(self, torches=0, mode='line', beam=None, reveal=None, cam=None, dark_room=True):
        self.cam = cam or dict(z0=1.0, z1=1.12, x0=0.5, y0=0.55, x1=0.5, y1=0.6)
        img = night_base(self.seed + 3, horizon=0.5, moon=(0.2, 0.15))
        mk = Mask()
        canopy(mk, PH * 0.92, PH * 0.62, -40, PW + 40, self.seed + 9, blob=100, density=1.1)
        self.near = mk.get()
        self.bg = img
        # moldura da janela (em primeiro plano)
        fm = Mask()
        fm.rect(0, 0, PW, PH * 0.08)
        fm.rect(0, PH * 0.9, PW, PH)
        fm.rect(0, 0, PW * 0.06, PH)
        fm.rect(PW * 0.94, 0, PW, PH)
        fm.rect(PW * 0.495, 0, PW * 0.505, PH)
        fm.rect(0, PH * 0.47, PW, PH * 0.485)
        self.frame = fm.get(1.5)
        self.torches = torches
        self.mode = mode
        self.beam = beam
        self.reveal = reveal  # lista de tempos para acender cada tocha
        r = rng(self.seed + 4)
        n = 11
        if mode == 'line':
            self.tp = [(PW * (0.28 + 0.045 * i) + r.normal(0, 8), PH * (0.6 + 0.012 * i) + r.normal(0, 6)) for i in range(n)]
        else:
            cx, cy = PW * 0.62, PH * 0.68
            self.tp = [(cx + math.cos(a) * 120, cy + math.sin(a) * 28) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
        self.ph = r.uniform(0, 6, n)
        self.plate = img

    def dyn(self, img, lt, dur):
        n = self.torches
        if self.reveal is not None:
            n = sum(1 for t in self.reveal if lt >= t)
        drift = lt * 6 if self.mode == 'line' else 0
        for i in range(n):
            x, y = self.tp[i]
            fl = 0.7 + 0.3 * math.sin(lt * 8 + self.ph[i]) * math.sin(lt * 3.3 + self.ph[i])
            add_glow(img, x + drift, y + drift * 0.15, 3.5, TORCH, 1.6 * fl)
            add_glow(img, x + drift, y + drift * 0.15, 20, TORCH, 0.2 * fl)
        if self.beam is not None and lt >= self.beam[0] and lt < self.beam[1]:
            k = min(1, (lt - self.beam[0]) * 8)
            bm = Mask().poly([(PW * 0.5, PH * 1.05), (PW * 0.46, PH * 1.05), (PW * 0.2, PH * 0.45), (PW * 0.75, PH * 0.45)]).get(40)
            ns = fbm(PH, PW, 80, 3, int(lt * 3)) if False else 1
            img += (bm * 0.22 * k)[:, :, None] * col((0.9, 0.95, 1.0))
            add_glow(img, PW * 0.47, PH * 0.62, 180, (0.9, 0.95, 1), 0.08 * k)
        comp(img, self.near, NEAR)
        comp(img, self.frame, (0.006, 0.005, 0.005))


class Binoculars(Scene):
    """visão pelo binóculo: a seita na clareira."""
    fog_amount = 0.3
    fog_band = (0.3, 0.9)

    def build(self, arms_up=None, facing=False, symbol=True, chant=False, still=False, cam=None, mask=True):
        self.cam = cam or dict(z0=1.0, z1=1.06, x0=0.5, y0=0.5, x1=0.5, y1=0.5, shake=0.0 if still else 1.0)
        img = vgrad(PH, PW, [(0, (0.01, 0.015, 0.02)), (0.4, (0.02, 0.03, 0.035)), (1, (0.04, 0.035, 0.03))])
        mk = Mask()
        canopy(mk, PH * 0.45, PH * 0.05, -40, PW + 40, self.seed + 1, blob=140, density=1.2)
        comp(img, mk.get(), (0.008, 0.01, 0.012))
        # chão da clareira
        g = Mask().ellipse(PW * 0.5, PH * 0.7, PW * 0.55, PH * 0.3).get(30)
        gt = fbm(PH, PW, 20, 4, self.seed + 3)
        img += (g * (0.04 + 0.03 * gt))[:, :, None] * col((0.8, 0.6, 0.4))
        self.cx, self.cy = PW * 0.5, PH * 0.68
        self.rx, self.ry = PW * 0.3, PH * 0.17
        if symbol:
            sm = Mask()
            sm.ellipse(self.cx, self.cy, self.rx * 0.55, self.ry * 0.55)
            sm2 = Mask()
            sm2.ellipse(self.cx, self.cy, self.rx * 0.55 - 6, self.ry * 0.55 - 4)
            ring = np.clip(sm.get() - sm2.get(), 0, 1)
            lm = Mask()
            cx, cy, rx, ry = self.cx, self.cy, self.rx, self.ry
            lm.arc(cx, cy, rx * 0.3, ry * 0.3, 0, 360, 4)
            lm.line(cx, cy - ry * 0.52, cx, cy + ry * 0.52, 4)
            for k in range(3):  # três ganchos curvos
                a = k * 120 + 90
                ex, ey = cx + math.cos(math.radians(a)) * rx * 0.3, cy + math.sin(math.radians(a)) * ry * 0.3
                lm.arc(ex + math.cos(math.radians(a)) * rx * 0.1, ey + math.sin(math.radians(a)) * ry * 0.1, rx * 0.1, ry * 0.1, a + 180, a + 400, 4)
            lm.arc(cx, cy, rx * 0.16, ry * 0.07, 0, 360, 3)  # olho
            lm.circle(cx, cy, 6)
            for k in range(7):
                a = k * 2 * math.pi / 7
                lm.circle(cx + math.cos(a) * rx * 0.62, cy + math.sin(a) * ry * 0.62, 5)
            sym = np.clip(ring + lm.get(), 0, 1)
            self.sym = sym
            img = img * (1 - sym[:, :, None] * 0.6) + sym[:, :, None] * col((0.25, 0.03, 0.02))
        else:
            self.sym = None
        n = 11
        self.fig = []
        figs_mask = Mask()
        order = sorted(range(n), key=lambda i: math.sin(i * 2 * math.pi / n))
        self.torch_pts = []
        for i in order:
            a = i * 2 * math.pi / n + 0.3
            x = self.cx + math.cos(a) * self.rx
            y = self.cy + math.sin(a) * self.ry
            h = 230 * (1 + 0.25 * math.sin(a))
            info = hooded(figs_mask, x, y, h, seed=i)
            self.fig.append((info, h))
            # tocha cravada ao lado
            tx = x + 40 * (1 + 0.25 * math.sin(a))
            figs_mask.line(tx, y, tx, y - h * 0.75, 4)
            self.torch_pts.append((tx, y - h * 0.78, h))
        self.arms_up = arms_up
        lead = Mask()
        self.lead_info = hooded(lead, self.cx, self.cy + 10, 330, seed=77)
        lead_up = Mask()
        hooded(lead_up, self.cx, self.cy + 10, 330, arms_up=True, seed=77)
        self.lead = lead.get()
        self.lead_up = lead_up.get()
        self.figs = figs_mask.get()
        self.facing = facing
        self.chant = chant
        self.base = img
        if mask:
            bm = Mask(PW, PH)
            bm.circle(PW * 0.5 - 330, PH * 0.5, 560)
            bm.circle(PW * 0.5 + 330, PH * 0.5, 560)
            self.bmask = cv2.GaussianBlur(bm.get(), (0, 0), 25)
        else:
            self.bmask = None
        self.plate = img
        self.ph = rng(5).uniform(0, 6, 20)

    def dyn(self, img, lt, dur):
        # luz das tochas no chão
        flick = 0.85 + 0.15 * math.sin(lt * 7) * math.sin(lt * 3.1)
        light = np.zeros((PH, PW), np.float32)
        for i, (x, y, h) in enumerate(self.torch_pts):
            fl = 0.75 + 0.25 * math.sin(lt * 9 + self.ph[i])
            add_glow(img, x, y, 10 * h / 230, TORCH, 1.6 * fl)
            add_glow(img, x, y, 90 * h / 230, TORCH, 0.16 * fl)
        img += (img * 0.0)
        comp(img, self.figs, (0.006, 0.005, 0.005))
        up = self.arms_up is not None and lt >= self.arms_up
        comp(img, self.lead_up if up else self.lead, (0.004, 0.003, 0.003))
        if self.sym is not None and self.chant:
            pulse = 0.5 + 0.5 * math.sin(lt * 2.2)
            img += (self.sym * 0.25 * pulse)[:, :, None] * col((1, 0.1, 0.05))
        if self.facing:
            k = 1.0 if self.facing is True else min(1, max(0, (lt - self.facing) * 3))
            for (info, h) in self.fig:
                hx, hy = info['head']
                d = info['eyes_dx']
                for s in (-1, 1):
                    add_glow(img, hx + s * d, hy, 1.6 * h / 230, (1, 0.85, 0.6), 2.0 * k)
            hx, hy = self.lead_info['head']
            for s in (-1, 1):
                add_glow(img, hx + s * self.lead_info['eyes_dx'], hy, 2.2, (1, 0.85, 0.6), 2.2 * k)
        if self.bmask is not None:
            img *= self.bmask[:, :, None]


class TorchesRing(Scene):
    """da janela, olhando pra baixo: tochas em volta da torre."""
    fog_amount = 0.35
    fog_band = (0.3, 1.0)

    def build(self, lights_out=None, cam=None):
        self.cam = cam or dict(z0=1.0, z1=1.15, x0=0.5, y0=0.55, x1=0.5, y1=0.62)
        img = vgrad(PH, PW, [(0, (0.015, 0.02, 0.025)), (1, (0.03, 0.03, 0.03))])
        gt = fbm(PH, PW, 40, 4, self.seed)
        img *= (0.7 + 0.6 * gt[:, :, None])
        mk = Mask()
        r = rng(self.seed)
        for i in range(40):
            x, y = r.uniform(0, PW), r.uniform(0, PH)
            if abs(x - PW / 2) < 500 and abs(y - PH * 0.62) < 300:
                continue
            for _ in range(6):
                mk.circle(x + r.normal(0, 60), y + r.normal(0, 60), r.uniform(30, 90))
        comp(img, mk.get(), (0.006, 0.008, 0.01))
        # treliça convergindo para baixo (perspectiva)
        mk = Mask()
        vx, vy = PW * 0.5, PH * 0.62
        for sx, sy in [(-0.1, -0.2), (1.1, -0.2), (-0.1, 1.2), (1.1, 1.2)]:
            mk.line(sx * PW, sy * PH, vx + (sx - 0.5) * 60, vy + (sy - 0.5) * 40, 26)
        for k in range(1, 7):
            f = 1 - k / 7
            pts = [(vx + (sx - 0.5) * (60 + f * PW * 1.2), vy + (sy - 0.5) * (40 + f * PH * 1.4)) for sx, sy in [(0, 0), (1, 0), (1, 1), (0, 1)]]
            for a, b in zip(pts, pts[1:] + pts[:1]):
                mk.line(a[0], a[1], b[0], b[1], 4 + 12 * f)
        self.lattice = mk.get()
        self.vx, self.vy = vx, vy
        self.pts = [(vx + math.cos(a) * 330, vy + math.sin(a) * 210) for a in np.linspace(0, 2 * math.pi, 11, endpoint=False)]
        fm = Mask()
        for (x, y) in self.pts:
            hooded(fm, x + 25, y + 30, 70, seed=int(x))
        self.figs = fm.get()
        self.lights_out = lights_out
        self.plate = img
        self.ph = rng(2).uniform(0, 6, 11)

    def dyn(self, img, lt, dur):
        for i, (x, y) in enumerate(self.pts):
            fl = 0.75 + 0.25 * math.sin(lt * 9 + self.ph[i])
            add_glow(img, x, y, 6, TORCH, 1.8 * fl)
            add_glow(img, x, y, 60, TORCH, 0.2 * fl)
        comp(img, self.figs, (0.01, 0.006, 0.004))
        comp(img, self.lattice, (0.01, 0.01, 0.012))
        if self.lights_out is None or lt < self.lights_out:
            add_glow(img, PW * 0.5, -40, 500, WARM, 0.08)


class TowerBase(Scene):
    """pé da torre, manhã cinzenta: círculo, sino, bilhete."""
    fog_amount = 0.3
    fog_band = (0.2, 0.7)

    def build(self, cam=None, clean=False, police=False):
        self.cam = cam or dict(z0=1.0, z1=1.25, x0=0.5, y0=0.6, x1=0.55, y1=0.72)
        img = vgrad(PH, PW, [(0, (0.33, 0.36, 0.38)), (0.45, (0.42, 0.44, 0.44)), (0.5, (0.16, 0.15, 0.13)), (1, (0.12, 0.1, 0.08))])
        gt = fbm(PH, PW, 25, 5, self.seed)
        ys = np.linspace(0, 1, PH, dtype=np.float32)[:, None]
        g = (ys > 0.47)
        img += ((gt - 0.5) * 0.07 * g)[:, :, None]
        mk = Mask()
        canopy(mk, PH * 0.5, PH * 0.15, -40, PW + 40, self.seed + 1, blob=120, density=1.0)
        comp(img, mk.get(), (0.12, 0.14, 0.13))
        mk = Mask()
        # pernas da torre
        for (bx, tx) in [(PW * 0.18, PW * 0.36), (PW * 0.82, PW * 0.64)]:
            mk.line(bx, PH * 0.85, tx, -40, 34)
        mk.line(PW * 0.5, PH * 0.6, PW * 0.5, -40, 14)
        for k in range(5):
            y = PH * 0.85 - k * PH * 0.2
            f = k * 0.2
            x0 = PW * 0.18 + (PW * 0.36 - PW * 0.18) * f * 0.95
            x1 = PW * 0.82 - (PW * 0.82 - PW * 0.64) * f * 0.95
            mk.line(x0, y, x1, y - PH * 0.2, 10)
            mk.line(x1, y, x0, y - PH * 0.2, 10)
        # sapatas de concreto
        for bx in (PW * 0.18, PW * 0.82):
            mk.rect(bx - 60, PH * 0.83, bx + 60, PH * 0.9)
        # escada: primeiro degrau
        sx = PW * 0.62
        mk.line(sx, PH * 0.88, sx + 80, -40, 12)
        mk.line(sx + 140, PH * 0.88, sx + 220, -40, 12)
        for k in range(6):
            y = PH * 0.82 - k * 150
            mk.line(sx + k * 13, y, sx + 140 + k * 13, y, 12)
        # gerador
        mk.rect(PW * 0.25, PH * 0.7, PW * 0.4, PH * 0.84)
        mk.rect(PW * 0.27, PH * 0.66, PW * 0.3, PH * 0.7)
        comp(img, mk.get(), (0.05, 0.045, 0.04))
        self.step = (sx + 70, PH * 0.82)
        if not clean:
            cm = Mask().ellipse(PW * 0.5, PH * 0.86, PW * 0.42, PH * 0.1).get(1.2)
            cm2 = Mask().ellipse(PW * 0.5, PH * 0.86, PW * 0.42 - 14, PH * 0.1 - 5).get(1.2)
            ring = np.clip(cm - cm2, 0, 1) * (0.7 + 0.3 * fbm(PH, PW, 6, 3, 4))
            img = img * (1 - ring[:, :, None] * 0.85) + ring[:, :, None] * 0.85 * col((0.25, 0.02, 0.02))
            # sino no degrau
            bm = Mask()
            bx, by = self.step
            bm.line(bx, by - 100, bx, by - 40, 2)
            bell_shape(bm, bx, by - 42, 36)
            comp(img, bm.get(), (0.06, 0.05, 0.04))
            # bilhete
            pm = Mask().poly([(bx - 40, by + 8), (bx + 50, by + 3), (bx + 52, by + 40), (bx - 38, by + 45)]).get(0.7)
            comp(img, pm, (0.6, 0.57, 0.5))
            rgb, a = text_layer(PW, PH, [("HOJE", (bx - 30, by + 8), 'courier', 30, (0.25, 0.02, 0.02), 1.0, 'la', 1.5)])
            img = img * (1 - a[:, :, None]) + rgb * a[:, :, None]
        self.police = police
        if police:
            pm = Mask()
            px, py = PW * 0.12, PH * 0.62
            pm.rect(px - 180, py - 70, px + 180, py)
            pm.poly([(px - 110, py - 70), (px - 70, py - 130), (px + 80, py - 130), (px + 120, py - 70)])
            pm.rect(px - 40, py - 142, px + 40, py - 130)
            pm.circle(px - 110, py, 34)
            pm.circle(px + 110, py, 34)
            comp(img, pm.get(), (0.08, 0.08, 0.09))
            self.pl = (px, py - 138)
        img = img * 0.85
        self.plate = img

    def dyn(self, img, lt, dur):
        if self.police:
            x, y = self.pl
            b = (int(lt * 3) % 2)
            add_glow(img, x - 22, y, 14, (1, 0.1, 0.1), 1.2 * b)
            add_glow(img, x + 22, y, 14, (0.1, 0.3, 1), 1.2 * (1 - b))
            add_glow(img, x, y, 140, (1, 0.1, 0.1) if b else (0.1, 0.3, 1), 0.08)


class Radio(Scene):
    """close no rádio comunicador."""

    def build(self, dead=False, cam=None, dawn=True):
        self.cam = cam or dict(z0=1.0, z1=1.18, x0=0.5, y0=0.5, x1=0.52, y1=0.5)
        img = vgrad(PH, PW, [(0, (0.06, 0.05, 0.045)), (1, (0.03, 0.025, 0.02))])
        tex = fbm(PH, PW, 5, 3, 1)
        img *= (0.8 + 0.4 * tex[:, :, None])
        mk = Mask()
        x0, y0, x1, y1 = PW * 0.18, PH * 0.25, PW * 0.82, PH * 0.82
        mk.rect(x0, y0, x1, y1)
        comp(img, mk.get(), (0.05, 0.05, 0.048))
        # bordas
        e = Mask().rect(x0, y0, x1, y0 + 8).get()
        img += e[:, :, None] * 0.05
        # grade do alto-falante
        sp = Mask()
        for i in range(16):
            for j in range(10):
                sp.circle(x0 + 120 + i * 30, y0 + 140 + j * 30, 7)
        comp(img, sp.get(), (0.01, 0.01, 0.01))
        # visor
        self.disp = (x1 - 560, y0 + 110, x1 - 120, y0 + 260)
        dm = Mask().rect(*self.disp).get()
        comp(img, dm, (0.02, 0.05, 0.03))
        # botões
        bm = Mask()
        for i in range(3):
            bm.circle(x1 - 480 + i * 160, y1 - 140, 52)
        comp(img, bm.get(), (0.02, 0.02, 0.02))
        bm2 = Mask()
        for i in range(3):
            bm2.line(x1 - 480 + i * 160, y1 - 140, x1 - 480 + i * 160 + 30, y1 - 180, 6)
        comp(img, bm2.get(), (0.15, 0.15, 0.14))
        # microfone e fio
        mm = Mask()
        mm.ellipse(PW * 0.12, PH * 0.75, 90, 140, 15)
        pts = [(PW * 0.12 + 10, PH * 0.6)] + [(PW * 0.12 + 40 + k * 40, PH * 0.55 - 30 * math.sin(k)) for k in range(6)] + [(x0 + 10, y0 + 200)]
        for a, b in zip(pts, pts[1:]):
            mm.line(a[0], a[1], b[0], b[1], 8)
        comp(img, mm.get(), (0.015, 0.015, 0.015))
        if dawn:
            img += radial(PH, PW, PW * 0.9, 0, 1400, 1.5)[:, :, None] * col((0.18, 0.2, 0.25))
        self.dead = dead
        self.plate = img

    def dyn(self, img, lt, dur):
        x0, y0, x1, y1 = self.disp
        r = rng(int(lt * 24))
        k = 0.6 + 0.4 * r.random()
        if self.dead:
            k = 0.4 + 0.6 * (r.random() > 0.5)
        c = (0.25, 1.0, 0.45)
        rgb, a = text_layer(PW, PH, [("CH 07  146.520", (x0 + 30, y0 + 25), 'courier', 52, c, k), ("RX " + ("▮" * int(1 + 9 * r.random())), (x0 + 30, y0 + 90), 'courier', 40, c, k)])
        img[:] = img * (1 - a[:, :, None]) + rgb * a[:, :, None]
        add_glow(img, (x0 + x1) / 2, (y0 + y1) / 2, 160, c, 0.06 * k)
        led = 1 if (int(lt * 2) % 2 == 0) else 0.2
        add_glow(img, x1 - 40, y0 + 40, 6, (1, 0.1, 0.05), 1.5 * led)


class Paper(Scene):
    """papel das regras / caderno, com texto aparecendo."""

    def build(self, lines=(), times=(), kind='rules', title=None, cam=None, blank_after=None):
        self.cam = cam or dict(z0=1.0, z1=1.1, x0=0.5, y0=0.45, x1=0.5, y1=0.55)
        img = vgrad(PH, PW, [(0, (0.04, 0.03, 0.02)), (1, (0.02, 0.015, 0.01))])
        wood = fbm(PH, PW, 4, 3, 2)
        stripes = (np.sin(np.linspace(0, 60, PH))[:, None] * 0.5 + 0.5)
        img *= (0.7 + 0.3 * wood[:, :, None] + 0.1 * stripes[:, :, None])
        tex = fbm(PH, PW, 8, 4, 3)
        if kind == 'rules':
            px0, py0, px1, py1 = PW * 0.22, PH * 0.05, PW * 0.78, PH * 0.97
            pm = Mask().poly([(px0, py0 + 10), (px1, py0), (px1 + 8, py1), (px0 - 6, py1 - 6)]).get(1)
            paper = (col((0.72, 0.66, 0.54)) * (0.85 + 0.25 * tex[:, :, None]))
            img = img * (1 - pm[:, :, None]) + paper * pm[:, :, None]
            # dobras
            for f in (0.33, 0.66):
                y = py0 + (py1 - py0) * f
                m = Mask().line(px0, y, px1, y - 4, 3).get(3)
                img *= 1 - m[:, :, None] * 0.25
            self.x, self.y0, self.dy = px0 + 70, py0 + 70, 120
            self.fn, self.size = 'courier', 42
            self.color = (0.08, 0.06, 0.06)
        else:
            # caderno aberto
            pm = Mask().poly([(PW * 0.06, PH * 0.06), (PW * 0.94, PH * 0.06), (PW * 0.96, PH * 0.98), (PW * 0.04, PH * 0.98)]).get(1)
            paper = (col((0.68, 0.64, 0.55)) * (0.85 + 0.2 * tex[:, :, None]))
            img = img * (1 - pm[:, :, None]) + paper * pm[:, :, None]
            for k in range(22):
                y = PH * 0.14 + k * 50
                m = Mask().line(PW * 0.07, y, PW * 0.95, y, 1.5).get()
                img = img * (1 - m[:, :, None] * 0.5) + m[:, :, None] * 0.5 * col((0.35, 0.45, 0.6))
            m = Mask().line(PW * 0.5, PH * 0.06, PW * 0.5, PH * 0.98, 14).get(10)
            img *= 1 - m[:, :, None] * 0.5
            m = Mask().line(PW * 0.12, PH * 0.06, PW * 0.12, PH * 0.98, 2).get()
            img = img * (1 - m[:, :, None] * 0.6) + m[:, :, None] * 0.6 * col((0.7, 0.2, 0.2))
            self.x, self.y0, self.dy = PW * 0.14, PH * 0.14 - 42, 100
            self.fn, self.size = 'courier', 38
            self.color = (0.1, 0.1, 0.18)
        # luz amarelada
        img *= (0.35 + 0.9 * radial(PH, PW, PW * 0.45, PH * 0.3, 1500, 1.2))[:, :, None] * col((1, 0.88, 0.7))
        self.lines = list(lines)
        self.times = list(times) if times else [0] * len(lines)
        self.title = title
        self.base = img
        self.blank_after = blank_after
        self.layers = []
        for i, ln in enumerate(self.lines):
            if kind == 'rules':
                x, y = self.x, self.y0 + i * self.dy
            else:
                col_i = 0 if i < 5 else 1
                x = (PW * 0.14 if col_i == 0 else PW * 0.54)
                y = self.y0 + (i if col_i == 0 else i - 5) * self.dy * 1.0
            items = []
            for j, sub in enumerate(ln.split('\n')):
                items.append((sub, (x, y + j * 50), self.fn, self.size, self.color, 0.92, 'la', 2.0))
            rgb, a = text_layer(PW, PH, items)
            self.layers.append((rgb, a))
        self.plate = img

    def dyn(self, img, lt, dur):
        for (rgb, a), t in zip(self.layers, self.times):
            if lt >= t:
                k = min(1, (lt - t) * 2.5)
                ak = a[:, :, None] * k
                img[:] = img * (1 - ak) + rgb * ak * col((1, 0.9, 0.75))


class Phone(Scene):
    """celular na mão no escuro, com o anúncio."""

    def build(self, extra=None, extra_t=None, cam=None, notif=False):
        self.cam = cam or dict(z0=1.0, z1=1.12, x0=0.5, y0=0.5, x1=0.5, y1=0.46)
        img = np.zeros((PH, PW, 3), np.float32) + col((0.008, 0.008, 0.012))
        r = rng(4)
        for _ in range(14):  # bokeh
            add_glow(img, r.uniform(0, PW), r.uniform(0, PH), r.uniform(20, 70), (0.3, 0.35, 0.5), r.uniform(0.03, 0.08))
        x0, y0, x1, y1 = PW * 0.33, PH * 0.04, PW * 0.67, PH * 1.1
        body = Mask()
        body.rect(x0, y0, x1, y1)
        bmask = body.get(2)
        comp(img, bmask, (0.02, 0.02, 0.022))
        sx0, sy0, sx1, sy1 = x0 + 22, y0 + 22, x1 - 22, y1
        sc = Mask().rect(sx0, sy0, sx1, sy1).get(1)
        screen = vgrad(PH, PW, [(0, (0.07, 0.09, 0.08)), (1, (0.05, 0.07, 0.06))])
        img = img * (1 - sc[:, :, None]) + screen * sc[:, :, None]
        # barra do grupo
        bar = Mask().rect(sx0, sy0, sx1, sy0 + 120).get()
        comp(img, bar, (0.08, 0.2, 0.16))
        items = [("Vagas & Empregos — Região", (sx0 + 40, sy0 + 28), 'sans_b', 34, (0.95, 0.95, 0.95), 1),
                 ("1.248 participantes", (sx0 + 40, sy0 + 72), 'sans', 24, (0.8, 0.85, 0.8), 1)]
        # balão
        bx0, by0, bx1 = sx0 + 30, sy0 + 190, sx1 - 80
        lines = ["Precisa-se de VIGIA e OPERADOR", "para TORRE DE RETRANSMISSÃO.", "", "• Área rural", "• Regime de 15 dias",
                 "• Alimentação e alojamento inclusos", "• Salário acima da média", "", "Interessados ligar:", "(4X) 9 9XXX-XX17"]
        bh = 60 + len(lines) * 44
        bm = Mask().rect(bx0, by0, bx1, by0 + bh).get(1)
        comp(img, bm, (0.13, 0.16, 0.15))
        for i, ln in enumerate(lines):
            items.append((ln, (bx0 + 30, by0 + 30 + i * 44), 'sans_b' if i < 2 else 'sans', 31, (0.92, 0.94, 0.92), 1))
        items.append(("03:12", (bx1 - 90, by0 + bh - 40), 'sans', 22, (0.6, 0.65, 0.6), 1))
        rgb, a = text_layer(PW, PH, items)
        img = img * (1 - a[:, :, None]) + rgb * a[:, :, None]
        self.extra_layer = None
        if extra:
            ey = by0 + bh + 30
            em = Mask().rect(bx0, ey, bx1, ey + 150).get(1)
            rgb2, a2 = text_layer(PW, PH, [(extra[0], (bx0 + 30, ey + 28), 'sans_b', 31, (1.0, 0.45, 0.4), 1),
                                           (extra[1], (bx0 + 30, ey + 76), 'sans', 31, (0.92, 0.94, 0.92), 1)])
            self.extra_layer = (em, rgb2, a2)
        self.extra_t = extra_t or 0
        # mão (silhueta)
        hm = Mask()
        hm.ellipse(x0 - 10, PH * 0.85, 90, 260, -10)
        hm.ellipse(x1 + 20, PH * 0.75, 70, 110, 20)
        hm.ellipse(x1 + 25, PH * 0.9, 75, 110, 15)
        hm.ellipse(PW * 0.5, PH * 1.15, 360, 180)
        comp(img, hm.get(3), (0.04, 0.03, 0.03))
        img += radial(PH, PW, PW * 0.5, PH * 0.5, 1100, 2)[:, :, None] * col((0.1, 0.13, 0.12)) * 0.5
        self.plate = img

    def dyn(self, img, lt, dur):
        if self.extra_layer is not None and lt >= self.extra_t:
            k = min(1, (lt - self.extra_t) * 3)
            em, rgb, a = self.extra_layer
            comp(img, em * k, (0.16, 0.12, 0.12))
            ak = a[:, :, None] * k
            img[:] = img * (1 - ak) + rgb * ak


class Room(Scene):
    """quarto escuro, homem sentado na cama iluminado pelo celular."""

    def build(self, city=True, cam=None, phone=True, bell_window=False):
        self.cam = cam or dict(z0=1.0, z1=1.08, x0=0.45, y0=0.5, x1=0.55, y1=0.5)
        img = vgrad(PH, PW, [(0, (0.03, 0.035, 0.05)), (1, (0.015, 0.017, 0.025))])
        img += radial(PH, PW, PW * 0.7, PH * 0.35, 1100, 1.5)[:, :, None] * col((0.05, 0.06, 0.09))
        wx0, wy0, wx1, wy1 = PW * 0.55, PH * 0.12, PW * 0.88, PH * 0.6
        sub = vgrad(int(wy1 - wy0), int(wx1 - wx0), [(0, (0.02, 0.025, 0.05)), (1, (0.08, 0.07, 0.09))])
        if city:
            r = rng(9)
            hh, ww = sub.shape[:2]
            for i in range(14):
                bx = r.uniform(0, ww)
                bw = r.uniform(40, 110)
                bh = r.uniform(60, hh * 0.7)
                sub[int(hh - bh):, int(bx):int(bx + bw)] = col((0.015, 0.016, 0.02))
                for _ in range(int(bh * bw / 900)):
                    lx, ly = r.uniform(bx + 5, bx + bw - 10), r.uniform(hh - bh + 6, hh - 8)
                    if r.random() < 0.35 and int(ly) < hh and int(lx) < ww:
                        sub[int(ly):int(ly) + 6, int(lx):int(lx) + 5] = col((0.7, 0.55, 0.3)) * r.uniform(0.3, 1)
        img[int(wy0):int(wy0) + sub.shape[0], int(wx0):int(wx0) + sub.shape[1]] = sub
        mk = Mask()
        mk.rect(wx0 - 16, wy0 - 16, wx1 + 16, wy0)
        mk.rect(wx0 - 16, wy1, wx1 + 16, wy1 + 16)
        mk.rect(wx0 - 16, wy0, wx0, wy1)
        mk.rect(wx1, wy0, wx1 + 16, wy1)
        mk.rect((wx0 + wx1) / 2 - 6, wy0, (wx0 + wx1) / 2 + 6, wy1)
        comp(img, mk.get(), (0.005, 0.005, 0.007))
        # cama + homem sentado
        mk = Mask()
        mk.rect(PW * 0.05, PH * 0.72, PW * 0.6, PH * 0.84)
        mk.rect(PW * 0.05, PH * 0.6, PW * 0.08, PH * 0.84)
        man(mk, PW * 0.3, PH * 0.75, 560, 'sit', face=1)
        comp(img, mk.get(), (0.004, 0.004, 0.006))
        self.phone = phone
        self.pp = (PW * 0.3 + 0.26 * 560 * 0.95, PH * 0.75 - 0.5 * 560)
        self.bell_window = bell_window
        self.win = (wx0, wy0, wx1, wy1)
        self.plate = img

    def dyn(self, img, lt, dur):
        if self.phone:
            x, y = self.pp
            add_glow(img, x, y, 10, (0.8, 0.95, 1.0), 1.5)
            add_glow(img, x - 40, y - 60, 260, (0.4, 0.55, 0.7), 0.2)
            add_glow(img, x - 60, y - 140, 60, (0.4, 0.55, 0.7), 0.25)


class Bell(Scene):
    """sino balançando no escuro (plano simbólico)."""
    fog_amount = 0.5
    fog_band = (0.0, 1.0)

    def build(self, cam=None, swing=0.25, red=False):
        self.cam = cam or dict(z0=1.0, z1=1.1, x0=0.5, y0=0.5, x1=0.5, y1=0.5)
        img = np.zeros((PH, PW, 3), np.float32)
        img += radial(PH, PW, PW * 0.5, PH * 0.45, 1000, 1.5)[:, :, None] * col((0.05, 0.06, 0.08) if not red else (0.09, 0.02, 0.02))
        self.base = img
        self.swing = swing
        self.plate = img

    def dyn(self, img, lt, dur):
        ang = self.swing * math.sin(lt * 2.2) * math.exp(-lt * 0.05)
        mk = Mask()
        cx, cy = PW * 0.5, PH * 0.12
        mk.line(cx, -20, cx, cy, 6)
        bell_shape(mk, cx, cy, 520, ang)
        m = mk.get()
        edge = np.clip(cv2.GaussianBlur(m, (0, 0), 4) - m * 0.9, 0, 1)
        comp(img, m, (0.012, 0.011, 0.01))
        img += edge[:, :, None] * col((0.35, 0.3, 0.22)) * 0.6


class Stairs(Scene):
    """olhando escada abaixo, no escuro, figura subindo."""
    fog_amount = 0.3
    fog_band = (0.4, 1.0)

    def build(self, rise=(0, 1), cam=None, torch=True, figure=True):
        self.cam = cam or dict(z0=1.0, z1=1.15, x0=0.5, y0=0.5, x1=0.5, y1=0.55)
        img = vgrad(PH, PW, [(0, (0.01, 0.012, 0.018)), (1, (0.03, 0.03, 0.035))])
        mk = Mask()
        canopy(mk, PH * 1.0, PH * 0.4, -40, PW + 40, self.seed, blob=150, density=1.2)
        comp(img, mk.get(), (0.006, 0.008, 0.01))
        sm = Mask()
        vx, vy = PW * 0.52, PH * 1.25
        for k in range(18):
            f = k / 17
            y = PH * 0.05 + (f ** 1.4) * PH * 1.1
            w = 160 + f ** 1.3 * 900
            sm.line(vx - w / 2 + (1 - f) * 100, y, vx + w / 2 + (1 - f) * 100, y, 4 + 18 * f)
        for s in (-1, 1):
            pts = [(vx + s * (80 + (k / 17) ** 1.3 * 450) + (1 - k / 17) * 100, PH * 0.05 + ((k / 17) ** 1.4) * PH * 1.1) for k in range(18)]
            for a, b in zip(pts, pts[1:]):
                sm.line(a[0], a[1], b[0], b[1], 8 + 14 * (b[1] / PH))
            hand = [(p[0] + s * 60, p[1] - 140 * (p[1] / PH)) for p in pts]
            for a, b in zip(hand, hand[1:]):
                sm.line(a[0], a[1], b[0], b[1], 4 + 8 * (b[1] / PH))
        self.stairs = sm.get()
        comp(img, self.stairs, (0.004, 0.004, 0.005))
        edge = np.clip(cv2.GaussianBlur(self.stairs, (0, 0), 3) - self.stairs, 0, 1)
        img += edge[:, :, None] * col((0.08, 0.09, 0.12))
        self.rise = rise
        self.torch = torch
        self.figure = figure
        self.plate = img

    def dyn(self, img, lt, dur):
        if not self.figure:
            return
        p = self.rise[0] + (self.rise[1] - self.rise[0]) * min(1, lt / max(0.1, dur))
        y = PH * 0.2 + p * PH * 0.75
        h = 120 + p * 900
        mk = Mask()
        info = hooded(mk, PW * 0.55 + (1 - p) * 60, y + h * 0.4, h, seed=3, torch=1 if self.torch else None)
        m = mk.get()
        if self.torch and info['torch']:
            tx, ty = info['torch']
            fl = 0.8 + 0.2 * math.sin(lt * 9)
            add_glow(img, tx, ty, 10 + p * 30, TORCH, 1.5 * fl)
            add_glow(img, tx, ty, 160 + p * 300, TORCH, 0.15 * fl)
        comp(img, m, (0.004, 0.003, 0.003))
        comp(img, self.stairs * (1 - m), (0.004, 0.004, 0.005))


class Door(Scene):
    """porta da cabine; abre uma fresta; lanterna revela olhos."""

    def build(self, open_t=None, beam_t=None, eyes_t=None, cam=None, table=True):
        self.cam = cam or dict(z0=1.0, z1=1.12, x0=0.5, y0=0.5, x1=0.5, y1=0.5)
        wall = vgrad(PH, PW, [(0, (0.03, 0.022, 0.016)), (1, (0.018, 0.012, 0.01))])
        tex = fbm(PH, PW, 5, 3, 1)
        wall *= (0.8 + 0.4 * tex[:, :, None])
        self.dx0, self.dy0, self.dx1, self.dy1 = PW * 0.32, PH * 0.06, PW * 0.68, PH * 0.92
        door = Mask().rect(self.dx0, self.dy0, self.dx1, self.dy1).get()
        dtex = fbm(PH, PW, 4, 3, 2)
        planks = (np.sin(np.linspace(0, PW / 120 * 2 * np.pi, PW)) > 0.97).astype(np.float32)[None, :]
        dcol = col((0.06, 0.045, 0.03)) * (0.8 + 0.4 * dtex[:, :, None]) * (1 - planks[:, :, None] * 0.5)
        img = wall * (1 - door[:, :, None]) + dcol * door[:, :, None]
        hm = Mask().circle(self.dx1 - 60, PH * 0.52, 16).get()
        comp(img, hm, (0.15, 0.13, 0.1))
        if table:
            tm = Mask()
            tm.rect(PW * 0.22, PH * 0.66, PW * 0.78, PH * 0.7)
            tm.rect(PW * 0.24, PH * 0.7, PW * 0.26, PH * 1.0)
            tm.rect(PW * 0.74, PH * 0.7, PW * 0.76, PH * 1.0)
            self.table = tm.get()
        else:
            self.table = None
        self.open_t, self.beam_t, self.eyes_t = open_t, beam_t, eyes_t
        self.door_img = img
        self.plate = img * 0.25

    def dyn(self, img, lt, dur):
        beam = self.beam_t is not None and lt >= self.beam_t
        op = 0.0
        if self.open_t is not None and lt >= self.open_t:
            op = min(1, (lt - self.open_t) / 2.5)
        base = self.door_img * (1.3 if beam else 0.22)
        img[:] = base
        if op > 0:
            gap = 10 + op * 110
            gm = Mask().rect(self.dx1 - gap, self.dy0, self.dx1, self.dy1).get()
            comp(img, gm, (0.0, 0.0, 0.0))
            if beam:
                # rosto encapuzado na fresta
                fm = Mask()
                fx = self.dx1 - gap * 0.45
                hooded(fm, fx, PH * 1.2, PH * 0.95, seed=8, width=0.9)
                f = fm.get() * gm
                comp(img, f, (0.05, 0.04, 0.035))
                if self.eyes_t is not None and lt >= self.eyes_t:
                    for s in (-1, 1):
                        add_glow(img, fx + s * 22, PH * 0.38, 5, (1, 0.9, 0.55), 3.0)
                        add_glow(img, fx + s * 22, PH * 0.38, 30, (1, 0.8, 0.4), 0.35)
        if beam:
            img *= (0.3 + 1.4 * radial(PH, PW, PW * 0.58, PH * 0.42, 700, 1.3))[:, :, None]
        if self.table is not None:
            shift = -op * 40
            t = np.roll(self.table, int(shift), axis=1)
            comp(img, t, (0.01, 0.008, 0.006))


class Climb(Scene):
    """descendo pelo lado de fora da treliça."""
    fog_amount = 0.4
    fog_band = (0.3, 1.0)

    def build(self, cam=None):
        self.cam = cam or dict(z0=1.05, z1=1.0, x0=0.5, y0=0.35, x1=0.5, y1=0.65, shake=0.6)
        img = night_base(self.seed, horizon=0.85, moon=(0.85, 0.12), layers=2)
        mk = Mask()
        x0, x1 = PW * 0.3, PW * 0.72
        mk.line(x0, -50, x0 + 60, PH + 50, 30)
        mk.line(x1, -50, x1 - 60, PH + 50, 30)
        for k in range(6):
            y = -100 + k * 280
            mk.line(x0 + 10, y, x1 - 10, y + 280, 12)
            mk.line(x1 - 10, y, x0 + 10, y + 280, 12)
            mk.line(x0, y, x1, y, 16)
        self.lat = mk.get()
        comp(img, self.lat, (0.006, 0.006, 0.008))
        r = rng(4)
        self.tp = [(r.uniform(0, PW), PH * r.uniform(0.85, 0.98)) for _ in range(9)]
        self.plate = img

    def dyn(self, img, lt, dur):
        for i, (x, y) in enumerate(self.tp):
            fl = 0.7 + 0.3 * math.sin(lt * 8 + i)
            add_glow(img, x + math.sin(lt * 0.7 + i) * 40, y, 4, TORCH, 1.5 * fl)
            add_glow(img, x + math.sin(lt * 0.7 + i) * 40, y, 30, TORCH, 0.15 * fl)
        mk = Mask()
        p = min(1, lt / max(1, dur))
        cy = PH * (0.3 + 0.35 * p)
        cx = PW * 0.52
        # homem agarrado (de costas) nas barras
        mk.ellipse(cx, cy - 150, 34, 40)
        mk.ellipse(cx, cy, 70, 120)
        sw = math.sin(lt * 3.2)
        mk.line(cx - 50, cy - 80, cx - 140, cy - 220 + sw * 40, 26)
        mk.line(cx + 50, cy - 80, cx + 140, cy - 220 - sw * 40, 26)
        mk.line(cx - 30, cy + 100, cx - 90, cy + 250 - sw * 40, 30)
        mk.line(cx + 30, cy + 100, cx + 90, cy + 250 + sw * 40, 30)
        comp(img, mk.get(), (0.004, 0.004, 0.005))


class Run(Scene):
    """correndo pela mata: paralaxe rápida + tochas atrás."""

    def build(self, cam=None, torches=True):
        self.cam = cam or dict(z0=1.0, z1=1.0, x0=0.5, y0=0.5, x1=0.5, y1=0.5, shake=2.5)
        self.bg = night_base(self.seed, horizon=0.55, moon=None, layers=1, stars=False)
        self.layers = []
        for i, (c, n, s) in enumerate([(MID, 18, 1.0), (NEAR, 10, 2.2)]):
            mk = Mask(PW * 2, PH)
            r = rng(self.seed + i)
            for k in range(n):
                tall_tree(mk, r.uniform(0, PW * 2), PH * 1.05, PH * r.uniform(1.0, 1.4), k + i * 50, s, r.uniform(-0.05, 0.05))
            mk.rect(0, PH * (0.85 + 0.08 * i), PW * 2, PH)
            self.layers.append((mk.get(), c, 900 + i * 1500))
        self.torches = torches
        self.plate = self.bg

    def dyn(self, img, lt, dur):
        if self.torches:
            for i in range(6):
                x = PW * (0.15 + 0.14 * i) + math.sin(lt * 1.3 + i) * 80
                y = PH * 0.6 + math.sin(lt * 5 + i * 2) * 10
                add_glow(img, x, y, 4, TORCH, 1.5)
                add_glow(img, x, y, 40, TORCH, 0.15)
        for m, c, sp in self.layers:
            off = int((lt * sp) % PW)
            sl = m[:, off:off + PW]
            if sl.shape[1] < PW:
                sl = np.concatenate([sl, m[:, :PW - sl.shape[1]]], 1)
            comp(img, sl, c)


class Black(Scene):
    def build(self, red=None, cam=None):
        self.cam = cam or dict(z0=1.0, z1=1.0)
        self.red = red
        self.plate = np.zeros((PH, PW, 3), np.float32)

    def dyn(self, img, lt, dur):
        if self.red is not None:
            k = max(0, 1 - abs(lt - self.red) * 2)
            img += radial(PH, PW, PW / 2, PH / 2, 1200, 2)[:, :, None] * col((0.15, 0.0, 0.0)) * k


class Title(Scene):
    """cartela de título."""

    def build(self, text='A TORRE', sub='', cam=None, size=230):
        self.cam = cam or dict(z0=1.0, z1=1.06)
        img = np.zeros((PH, PW, 3), np.float32)
        img += radial(PH, PW, PW / 2, PH / 2, 1100, 2)[:, :, None] * col((0.05, 0.02, 0.02))
        items = [(text, (PW / 2, PH / 2 - 20), 'serif_b', size, (0.85, 0.82, 0.78), 1.0, 'mm')]
        if sub:
            items.append((sub, (PW / 2, PH / 2 + size * 0.62), 'sans_l', 44, (0.6, 0.55, 0.5), 1.0, 'mm'))
        rgb, a = text_layer(PW, PH, items)
        self.rgb, self.a = rgb, a
        self.base = img
        self.plate = img

    def dyn(self, img, lt, dur):
        k = min(1, lt / 1.2)
        fl = 1.0
        if 0.8 < lt < 1.4 or 2.6 < lt < 2.75:
            fl = 0.3 + 0.7 * ((int(lt * 30)) % 2)
        ak = self.a[:, :, None] * k * fl
        img[:] = img * (1 - ak) + self.rgb * ak
        # leve brilho vermelho
        img += cv2.GaussianBlur(self.a, (0, 0), 18)[:, :, None] * col((0.4, 0.03, 0.02)) * 0.6 * k * fl


class EndCard(Scene):
    def build(self, lines=(), cam=None):
        self.cam = cam or dict(z0=1.0, z1=1.03)
        img = np.zeros((PH, PW, 3), np.float32)
        items = []
        for i, (t, sz, c) in enumerate(lines):
            items.append((t, (PW / 2, PH * 0.32 + i * 130), 'sans_b' if i == 0 else 'sans_l', sz, c, 1.0, 'mm'))
        self.rgb, self.a = text_layer(PW, PH, items)
        self.plate = img

    def dyn(self, img, lt, dur):
        k = min(1, lt / 1.5)
        img[:] = self.rgb * self.a[:, :, None] * k


SCENES = {c.__name__: c for c in [TowerNight, TowerUp, Road, Trail, FogSea, Cabin, WindowNorth, Binoculars, TorchesRing,
                                   TowerBase, Radio, Paper, Phone, Room, Bell, Stairs, Door, Climb, Run, Black, Title, EndCard]}
