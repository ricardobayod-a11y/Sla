"""Roteiro de montagem: cenas, efeitos, música e textos sincronizados por frase."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALIGN = json.loads((ROOT / 'build/align.json').read_text())


def S(i, off=0.0):
    return ('s', i, off)


def T(sec):
    return ('t', sec)


NOTE_ENTRIES = ["12/03 — Ouvi o sino de novo.\n         Mais perto.",
                "19/03 — Luzes na clareira do lado\n         norte. Contei onze.",
                "26/03 — Eles cantam. Não é português.\n         Não é nenhuma língua que eu conheça.",
                "02/04 — Acho que um deles olhou pra cá.",
                "09/04 — ELES SABEM."]
NOTE_NORMAL = ["02/03 — 18h. Gerador ok. Nada a relatar.", "03/03 — 18h. Gerador ok. Nada a relatar.",
               "04/03 — 18h. Gerador ok. Nada a relatar.", "05/03 — 18h. Gerador ok. Chuva.", "06/03 — 18h. Gerador ok. Nada a relatar."]
RULES = ["1. Fazer contato pelo rádio com a base\n   às 18h e às 6h. Sem falta.",
         "2. Manter o gerador ligado a noite inteira.\n   A luz vermelha do topo NUNCA pode apagar.",
         "3. Não descer da torre depois que o sol\n   se pôr. Por motivo nenhum.",
         "4. Se ouvir o SINO, apague as luzes da\n   cabine e fique longe das janelas.",
         "5. Não aponte a lanterna para a mata.\n   NUNCA."]
AD_EXTRA = ("Vaga reaberta.", "O último funcionário não completou o período.")

# ------------------------------------------------------------------ seções
# cada seção: shots [(marcador_inicio, Cena, kwargs, extra)], sfx [(marcador, nome, ganho, pan)],
# music dict, amb [(marcador, tipo)], texts [(m0, m1, texto, estilo)], fx [(m, tipo, dur, quant)]

SECTIONS = []


def sec(sid, **kw):
    kw['id'] = sid
    kw.setdefault('lead', 1.2)
    kw.setdefault('tail', 0.8)
    kw.setdefault('shots', [])
    kw.setdefault('sfx', [])
    kw.setdefault('amb', [])
    kw.setdefault('texts', [])
    kw.setdefault('fx', [])
    kw.setdefault('music', {})
    SECTIONS.append(kw)


sec('01', lead=2.5, tail=1.0,
    shots=[(T(-9), 'TowerNight', dict(seed=1), dict(cam=dict(z0=1.25, z1=1.0, x0=0.42, y0=0.45, x1=0.45, y1=0.5))),
           (S(2), 'WindowNorth', dict(seed=2), {}),
           (S(5), 'Binoculars', dict(seed=3, facing=True, still=True), dict(cam=dict(z0=1.1, z1=1.25))),
           (S(7), 'TowerNight', dict(seed=4, side=0.6), dict(cam=dict(z0=1.0, z1=1.12, x0=0.6, y0=0.5, x1=0.55, y1=0.45))),
           (S(9), 'Phone', dict(seed=5), {})],
    sfx=[(T(-2.0), 'bell_far', 0.5, -0.3), (S(1, 1.0), 'bell_far', 0.6, 0.2), (S(6, 0.0), 'hit', 0.8, 0), (S(9, 0.3), 'phone_buzz', 0.6, 0)],
    amb=[(T(-9), 'night')],
    fx=[(S(5, 0), 'glitch', 0.4, 0.6), (S(6, 0), 'flash', 0.15, 0.25)],
    music=dict(root=36.71, intensity=0.35, high=0.15))

sec('TITLE', synthetic=7.0, lead=0, tail=0,
    shots=[(T(0), 'Title', dict(text='A TORRE', sub='uma história de terror na mata'), {})],
    sfx=[(T(0.05), 'boom', 1.0, 0), (T(0.3), 'bell_mid', 0.7, 0)],
    amb=[(T(0), 'none')],
    music=dict(root=36.71, intensity=0.5, high=0.3))

sec('02', chapter='I.  O EMPREGO',
    shots=[(T(-9), 'Room', dict(seed=6), {}),
           (S(3, 1.5), 'Phone', dict(seed=7), dict(cam=dict(z0=1.0, z1=1.15, x0=0.5, y0=0.5, x1=0.5, y1=0.42))),
           (S(9), 'Phone', dict(seed=7), dict(cam=dict(z0=1.3, z1=1.45, x0=0.5, y0=0.62, x1=0.5, y1=0.64))),
           (S(12), 'Room', dict(seed=8), dict(cam=dict(z0=1.15, z1=1.25, x0=0.4, y0=0.45, x1=0.42, y1=0.45))),
           (S(17), 'Black', {}, {}),
           (S(22), 'Room', dict(seed=9), dict(cam=dict(z0=1.0, z1=1.08, x0=0.55, y0=0.5, x1=0.5, y1=0.5)))],
    texts=[(S(18), S(22), 'Você tem medo de ficar sozinho?', 'center_small'),
           (S(19), S(22), 'Você bebe?', 'center_small2'),
           (S(20), S(22), 'Você sabe guardar segredo?', 'center_small3')],
    sfx=[(S(3, 0.5), 'phone_buzz', 0.6, 0), (S(12, 0.6), 'phone_ring', 0.35, 0.2), (S(17, 0), 'whoosh', 0.4, 0)],
    amb=[(T(-9), 'room')],
    music=dict(root=36.71, intensity=0.25, piano=True))

sec('03', chapter='II.  A VIAGEM',
    shots=[(T(-9), 'Road', dict(seed=10), {}),
           (S(5), 'Road', dict(seed=11, truck=False), dict(cam=dict(z0=1.0, z1=1.2, x0=0.5, y0=0.5, x1=0.5, y1=0.48))),
           (S(8), 'Road', dict(seed=12, truck=False, gate=True), dict(cam=dict(z0=1.1, z1=1.0, x0=0.35, y0=0.6, x1=0.45, y1=0.55))),
           (S(9), 'Road', dict(seed=13), dict(cam=dict(z0=1.2, z1=1.3, x0=0.5, y0=0.5, x1=0.5, y1=0.5, shake=0.6))),
           (S(12), 'Trail', dict(seed=14), {}),
           (S(13), 'TowerUp', dict(seed=15, dusk=True), {})],
    sfx=[(T(-9), 'truck', 0.5, 0), (S(12, 0), 'steps_walk', 0.5, 0), (S(13, 0.6), 'boom_soft', 0.7, 0)],
    amb=[(T(-9), 'day')],
    music=dict(root=43.65, intensity=0.3, piano=True))

sec('04', chapter='III.  A TORRE',
    shots=[(T(-9), 'TowerUp', dict(seed=16, dusk=True), dict(cam=dict(z0=1.0, z1=1.12, x0=0.5, y0=0.3, x1=0.5, y1=0.55))),
           (S(3), 'TowerBase', dict(seed=17, clean=True), dict(cam=dict(z0=1.0, z1=1.15, x0=0.6, y0=0.6, x1=0.6, y1=0.4))),
           (S(6), 'Cabin', dict(seed=18), dict(cam=dict(z0=1.12, z1=1.0, x0=0.35, y0=0.5, x1=0.6, y1=0.5))),
           (S(7), 'Paper', dict(kind='notebook', lines=['LIVRO DE REGISTRO — TORRE 7']), dict(cam=dict(z0=1.0, z1=1.1, x0=0.4, y0=0.35, x1=0.4, y1=0.3))),
           (S(10), 'Cabin', dict(seed=19), dict(cam=dict(z0=1.3, z1=1.45, x0=0.35, y0=0.38, x1=0.35, y1=0.36))),
           (S(14), 'Paper', dict(kind='rules', lines=[]), dict(cam=dict(z0=1.0, z1=1.1))),
           (S(18), 'TowerNight', dict(seed=20), dict(cam=dict(z0=1.0, z1=1.1, x0=0.45, y0=0.5, x1=0.42, y1=0.5)))],
    sfx=[(S(4, 0.2), 'steps_climb', 0.4, 0.3), (S(14, 0.5), 'paper', 0.6, 0), (S(18, 0.2), 'steps_climb', 0.25, -0.3)],
    amb=[(T(-9), 'day'), (S(6), 'room'), (S(18), 'night')],
    music=dict(root=36.71, intensity=0.4, high=0.1))

sec('05', chapter='IV.  AS REGRAS', synthetic=34.0, lead=0, tail=0,
    shots=[(T(0), 'Cabin', dict(seed=21, pose='sit'), dict(cam=dict(z0=1.0, z1=1.1, x0=0.35, y0=0.5, x1=0.32, y1=0.5))),
           (T(5.0), 'Paper', dict(kind='rules', lines=RULES, times=[1.0, 6.0, 11.0, 16.0, 21.0]), dict(cam=dict(z0=1.0, z1=1.08, x0=0.5, y0=0.4, x1=0.5, y1=0.6)))],
    texts=[(T(0.6), T(4.6), 'Naquela primeira noite, Daniel abriu o papel.', 'caption'),
           (T(29.0), T(33.5), 'Que tipo de lugar precisa de uma regra dessas?', 'caption')],
    sfx=[(T(5.2), 'paper', 0.6, 0)],
    amb=[(T(0), 'room')],
    music=dict(root=36.71, intensity=0.45, high=0.15))

sec('05N', chapter='IV.  AS REGRAS', narrated_as='05',
    shots=[(T(-9), 'Cabin', dict(seed=21, pose='sit'), dict(cam=dict(z0=1.0, z1=1.1, x0=0.35, y0=0.5, x1=0.32, y1=0.5))),
           (('find', 'Um.'), 'Paper', dict(kind='rules', lines=RULES, times=[('find', 'Um.'), ('find', 'Dois.'), ('find', 'Três.'), ('find', 'Quatro.'), ('find', 'Cinco.')]),
            dict(cam=dict(z0=1.0, z1=1.08, x0=0.5, y0=0.4, x1=0.5, y1=0.6)))],
    sfx=[(('find', 'Um.'), 'paper', 0.6, 0)],
    amb=[(T(-9), 'room')],
    music=dict(root=36.71, intensity=0.45, high=0.15))

sec('06', chapter='',
    shots=[(T(-9), 'FogSea', dict(seed=22), {}),
           (S(5), 'TowerBase', dict(seed=23, clean=True), dict(cam=dict(z0=1.0, z1=1.12, x0=0.4, y0=0.6, x1=0.35, y1=0.65))),
           (S(6), 'Radio', dict(seed=24), {}),
           (S(8), 'FogSea', dict(seed=25, evening=True), dict(cam=dict(z0=1.08, z1=1.0, x0=0.55, y0=0.5, x1=0.45, y1=0.5))),
           (S(9), 'TowerNight', dict(seed=26), dict(cam=dict(z0=1.1, z1=1.0, x0=0.42, y0=0.5, x1=0.45, y1=0.5))),
           (S(12), 'WindowNorth', dict(seed=27), dict(cam=dict(z0=1.0, z1=1.18, x0=0.5, y0=0.6, x1=0.5, y1=0.68))),
           (S(13), 'Cabin', dict(seed=28, pose='sit'), {}),
           (S(15), 'Paper', dict(kind='notebook', lines=NOTE_NORMAL), dict(cam=dict(z0=1.0, z1=1.25, x0=0.35, y0=0.35, x1=0.35, y1=0.5)))],
    sfx=[(S(5, 0.3), 'generator_start', 0.4, 0), (S(6, -0.2), 'radio_click', 0.5, 0), (S(6, 0.0), 'static_short', 0.25, 0),
         (S(7, -0.2), 'radio_click', 0.5, 0), (S(12, 0.5), 'leaves', 0.6, -0.4), (S(12, 2.5), 'branch', 0.6, -0.5)],
    amb=[(T(-9), 'day'), (S(9), 'night')],
    music=dict(root=43.65, intensity=0.25, piano=True))

sec('07', chapter='V.  O CADERNO',
    shots=[(T(-9), 'Paper', dict(kind='notebook', lines=NOTE_ENTRIES, times=[('s', 0, 0), ('s', 3, 0), ('s', 6, 0), ('s', 10, 0), ('s', 12, 0)]),
            dict(cam=dict(z0=1.15, z1=1.3, x0=0.38, y0=0.3, x1=0.38, y1=0.55))),
           (S(14), 'Paper', dict(kind='notebook', lines=[]), dict(cam=dict(z0=1.0, z1=1.15, x0=0.7, y0=0.5, x1=0.72, y1=0.5))),
           (S(17), 'Cabin', dict(seed=29, pose='sit'), dict(cam=dict(z0=1.1, z1=1.2, x0=0.3, y0=0.5, x1=0.3, y1=0.5))),
           (S(18), 'WindowNorth', dict(seed=30), {}),
           (S(23), 'Cabin', dict(seed=31, lamp=False, pose='lie'), dict(cam=dict(z0=1.0, z1=1.1, x0=0.6, y0=0.55, x1=0.7, y1=0.6)))],
    sfx=[(S(13, 0), 'hit_soft', 0.6, 0), (S(13, 0.2), 'heartbeat', 0.5, 0), (S(17, 0.2), 'book_close', 0.6, 0)],
    fx=[(S(13, 0), 'flash', 0.12, 0.15)],
    amb=[(T(-9), 'night')],
    music=dict(root=36.71, intensity=0.45, high=0.25))

sec('08', chapter='VI.  O SINO',
    shots=[(T(-9), 'Cabin', dict(seed=32, lamp=False, pose='lie'), dict(cam=dict(z0=1.1, z1=1.2, x0=0.7, y0=0.6, x1=0.72, y1=0.6))),
           (S(2), 'Bell', dict(seed=33), {}),
           (S(6), 'Cabin', dict(seed=34, pose='sit', flicker=True), {}),
           (S(8), 'Bell', dict(seed=35, swing=0.35), dict(cam=dict(z0=1.15, z1=1.25))),
           (S(11), 'TowerNight', dict(seed=36, scale=0.6, side=0.5), dict(cam=dict(z0=1.0, z1=1.06))),
           (S(14), 'Bell', dict(seed=37, swing=0.45, red=True), dict(cam=dict(z0=1.25, z1=1.35))),
           (S(15), 'Paper', dict(kind='rules', lines=RULES), dict(cam=dict(z0=1.5, z1=1.65, x0=0.45, y0=0.38 + 0.0, x1=0.45, y1=0.4))),
           (S(16), 'Cabin', dict(seed=38, pose='crouch', lamp=('s', 16, 2.0)), {}),
           (S(17), 'Bell', dict(seed=39, swing=0.6), dict(cam=dict(z0=1.0, z1=1.2))),
           (S(19), 'Black', {}, {}),
           (S(20), 'WindowNorth', dict(seed=40), dict(cam=dict(z0=1.0, z1=1.06)))],
    sfx=[(S(2, 0.1), 'bell_far', 0.55, -0.5), (S(8, 0.05), 'bell_far2', 0.75, -0.3), (S(14, 0.05), 'bell_mid', 0.8, -0.2),
         (S(16, 2.0), 'lamp_off', 0.6, 0)] + [(S(17, 0.2 + 1.15 * k), 'bell_mid', 0.55, -0.2 + 0.05 * k) for k in range(7)],
    fx=[(S(8, 0), 'glitch', 0.25, 0.3), (S(14, 0), 'glitch', 0.3, 0.45)],
    amb=[(T(-9), 'night'), (S(19), 'silent')],
    music=dict(root=34.65, intensity=0.5, high=0.3))

sec('09', chapter='',
    shots=[(T(-9), 'Cabin', dict(seed=41, lamp=False, pose='window'), dict(cam=dict(z0=1.0, z1=1.1, x0=0.4, y0=0.5, x1=0.38, y1=0.45))),
           (S(2), 'WindowNorth', dict(seed=42, reveal=[('s', 4, 0), ('s', 7, 0), ('s', 8, 0), ('s', 8, 0.2), ('s', 9, 0), ('s', 9, 0.15), ('s', 9, 0.3), ('s', 9, 0.45), ('s', 10, 0), ('s', 10, 0.15), ('s', 10, 0.3)]),
            dict(cam=dict(z0=1.0, z1=1.35, x0=0.5, y0=0.55, x1=0.5, y1=0.6))),
           (S(13), 'WindowNorth', dict(seed=42, torches=11), dict(cam=dict(z0=1.5, z1=1.7, x0=0.42, y0=0.6, x1=0.5, y1=0.62))),
           (S(14), 'Cabin', dict(seed=43, lamp=False, pose='window'), dict(cam=dict(z0=1.2, z1=1.3, x0=0.35, y0=0.5, x1=0.35, y1=0.5, shake=0.8)))],
    sfx=[(S(14, 0.3), 'heartbeat', 0.6, 0)],
    amb=[(T(-9), 'silent_wind')],
    music=dict(root=34.65, intensity=0.55, high=0.3, pulse=60))

sec('10', chapter='VII.  A SEITA',
    shots=[(T(-9), 'Binoculars', dict(seed=44), {}),
           (S(4), 'Binoculars', dict(seed=44), dict(cam=dict(z0=1.1, z1=1.45, x0=0.5, y0=0.6, x1=0.5, y1=0.68))),
           (S(7), 'Binoculars', dict(seed=44, arms_up=('s', 8, 1.3), chant=True), dict(cam=dict(z0=1.2, z1=1.35, x0=0.5, y0=0.55, x1=0.5, y1=0.5))),
           (S(12), 'TowerNight', dict(seed=45), dict(cam=dict(z0=1.0, z1=1.08))),
           (S(13), 'Cabin', dict(seed=46, lamp=False, pose='window'), dict(cam=dict(z0=1.15, z1=1.25, x0=0.36, y0=0.5, x1=0.36, y1=0.48))),
           (S(14), 'Binoculars', dict(seed=44, arms_up=0, chant=True), dict(cam=dict(z0=1.6, z1=1.9, x0=0.5, y0=0.45, x1=0.5, y1=0.42))),
           (S(16), 'Binoculars', dict(seed=44, arms_up=0, chant=True), dict(cam=dict(z0=1.0, z1=1.2)))],
    sfx=[(S(9, -0.2), 'chant_long', 0.75, 0)],
    amb=[(T(-9), 'silent_wind')],
    music=dict(root=34.65, intensity=0.55, high=0.35))

sec('11', chapter='',
    shots=[(T(-9), 'Binoculars', dict(seed=44, arms_up=0, chant=True), dict(cam=dict(z0=1.2, z1=1.3))),
           (S(4), 'Binoculars', dict(seed=44, arms_up=0, chant=False, still=True), dict(cam=dict(z0=1.3, z1=1.32))),
           (S(6), 'Cabin', dict(seed=47, lamp=False, pose='window'), {}),
           (S(9), 'WindowNorth', dict(seed=48, torches=11, mode='circle', beam=(0.2, 7.0)), dict(cam=dict(z0=1.0, z1=1.1))),
           (S(11), 'Cabin', dict(seed=49, lamp=False, pose='crouch'), dict(cam=dict(z0=1.1, z1=1.0, shake=0.6))),
           (S(13), 'WindowNorth', dict(seed=48, torches=11, mode='circle'), dict(cam=dict(z0=1.2, z1=1.35, x0=0.6, y0=0.65, x1=0.6, y1=0.66))),
           (S(14), 'Binoculars', dict(seed=44, facing=('s', 17, 0), still=True), dict(cam=dict(z0=1.0, z1=1.18)))],
    sfx=[(S(7, 0), 'fall_roll', 0.8, 0.2), (S(9, 0), 'click', 0.8, 0), (S(9, 0.1), 'hit', 0.8, 0),
         (S(11, 1.4), 'click', 0.7, 0), (S(17, 0.0), 'hit', 1.0, 0), (S(17, 0.0), 'boom', 0.8, 0), (S(14, 0), 'riser_long', 0.5, 0)],
    fx=[(S(9, 0.05), 'flash', 0.25, 0.5), (S(17, 0), 'glitch', 0.6, 0.8), (S(17, 0), 'flash', 0.12, 0.3)],
    amb=[(T(-9), 'silent')],
    music=dict(root=34.65, intensity=0.5, high=0.2, mute=[('s', 4, 0), ('s', 13, 0)]))

sec('12', chapter='VIII.  ELES SABEM',
    shots=[(T(-9), 'Cabin', dict(seed=50, lamp=False, pose='crouch'), dict(cam=dict(z0=1.0, z1=1.08, x0=0.2, y0=0.6, x1=0.25, y1=0.6))),
           (S(1), 'Radio', dict(seed=51), {}),
           (S(6), 'Binoculars', dict(seed=44, facing=True, still=True), dict(cam=dict(z0=1.15, z1=1.25))),
           (S(9), 'Radio', dict(seed=51), dict(cam=dict(z0=1.1, z1=1.2, x0=0.45, y0=0.5, x1=0.48, y1=0.5))),
           (S(11), 'Radio', dict(seed=51), dict(cam=dict(z0=1.3, z1=1.5, x0=0.62, y0=0.35, x1=0.62, y1=0.35))),
           (S(15), 'Cabin', dict(seed=52, lamp=False, pose='sit'), {}),
           (S(16), 'Radio', dict(seed=51), dict(cam=dict(z0=1.5, z1=1.7, x0=0.3, y0=0.45, x1=0.3, y1=0.45))),
           (S(20), 'Black', {}, {})],
    sfx=[(S(0, 0), 'heartbeat', 0.5, 0), (S(2, -0.3), 'radio_click', 0.6, 0), (S(4, -0.1), 'static', 0.35, 0), (S(9, -0.1), 'static', 0.35, 0),
         (S(14, -0.4), 'static_short', 0.2, 0), (S(20, 0.4), 'radio_click', 0.7, 0)],
    amb=[(T(-9), 'day')],
    music=dict(root=36.71, intensity=0.45, high=0.2))

sec('13', chapter='',
    shots=[(T(-9), 'TowerBase', dict(seed=53, clean=True), dict(cam=dict(z0=1.0, z1=1.1, x0=0.35, y0=0.6, x1=0.35, y1=0.7))),
           (S(2), 'Stairs', dict(seed=54, figure=False, torch=False), {}),
           (S(3), 'TowerBase', dict(seed=55), dict(cam=dict(z0=1.0, z1=1.06))),
           (S(4), 'TowerBase', dict(seed=55), dict(cam=dict(z0=1.1, z1=1.3, x0=0.5, y0=0.72, x1=0.45, y1=0.78))),
           (S(6), 'TowerBase', dict(seed=55), dict(cam=dict(z0=1.4, z1=1.8, x0=0.6, y0=0.6, x1=0.65, y1=0.66))),
           (S(9), 'TowerBase', dict(seed=55), dict(cam=dict(z0=2.0, z1=2.4, x0=0.65, y0=0.68, x1=0.656, y1=0.69))),
           (S(12), 'TowerUp', dict(seed=56), dict(cam=dict(z0=1.0, z1=1.1, shake=0.8))),
           (S(13), 'Radio', dict(seed=57, dead=True), {}),
           (S(16), 'Cabin', dict(seed=57, lamp=False, pose='crouch'), dict(cam=dict(z0=1.0, z1=1.1, x0=0.2, y0=0.6, x1=0.2, y1=0.6))),
           (S(18), 'Radio', dict(seed=57, dead=True), dict(cam=dict(z0=1.4, z1=1.6, x0=0.62, y0=0.35, x1=0.62, y1=0.35))),
           (S(21), 'Radio', dict(seed=57, dead=True), dict(cam=dict(z0=1.3, z1=1.0)))],
    sfx=[(S(2, 0.2), 'steps_climb', 0.4, 0), (S(7, 0.1), 'bell_tiny', 0.6, 0.3), (S(11, 0.0), 'hit_soft', 0.8, 0),
         (S(12, 0.5), 'steps_run_metal', 0.45, 0), (S(13, -0.2), 'radio_click', 0.6, 0), (S(14, 0), 'static', 0.3, 0),
         (S(16, 0), 'static', 0.3, 0), (S(18, 0), 'static', 0.3, 0)],
    fx=[(S(11, 0), 'flash', 0.1, 0.2)],
    amb=[(T(-9), 'day')],
    music=dict(root=36.71, intensity=0.5, high=0.3))

sec('14', chapter='IX.  A NOITE',
    shots=[(T(-9), 'FogSea', dict(seed=58, evening=True), {}),
           (S(1), 'Door', dict(seed=59), dict(cam=dict(z0=1.0, z1=1.08))),
           (S(4), 'Cabin', dict(seed=60, pose='crouch'), {}),
           (S(5), 'TowerNight', dict(seed=61), {}),
           (S(6), 'Bell', dict(seed=62, red=True, swing=0.5), {}),
           (S(11), 'TorchesRing', dict(seed=63), {}),
           (S(16), 'TowerNight', dict(seed=64, ring=True, lights_out=('s', 17, 0.3)), dict(cam=dict(z0=1.0, z1=1.1))),
           (S(18), 'Cabin', dict(seed=65, pose='crouch', lamp=('s', 18, 0.3)), {}),
           (S(19), 'TowerNight', dict(seed=66, ring=True, cabin_lit=False, lights_out=('s', 19, 0.6)), dict(cam=dict(z0=1.7, z1=1.8, x0=0.42, y0=0.2, x1=0.42, y1=0.2))),
           (S(20), 'Black', dict(red=('s', 25, 0.1)), {}),
           (S(26), 'Stairs', dict(seed=67, figure=False, torch=False), dict(cam=dict(z0=1.0, z1=1.1))),
           (S(28), 'Stairs', dict(seed=67, rise=(0.0, 0.12)), {})],
    sfx=[(S(1, 0.4), 'scrape', 0.7, 0), (S(10, 0.0), 'bell_close', 0.9, 0), (S(16, -6), 'generator', 0.35, 0),
         (S(18, 0.3), 'lamp_off', 0.7, 0), (S(22, 0.1), 'metal_step', 0.9, 0), (S(25, 0.05), 'metal_step', 1.0, 0), (S(27, 0.05), 'metal_step', 1.0, 0),
         (S(28, 0.6), 'metal_step', 0.8, 0), (S(28, 2.2), 'metal_step', 0.8, 0)],
    fx=[(S(10, 0), 'glitch', 0.3, 0.5)],
    amb=[(T(-9), 'night'), (S(5), 'silent_wind'), (S(20), 'silent')],
    music=dict(root=34.65, intensity=0.6, high=0.4, pulse=70, mute=[('s', 20, 0), ('s', 28, 0)]))

sec('15', chapter='',
    shots=[(T(-9), 'Stairs', dict(seed=68, rise=(0.1, 0.3)), {}),
           (S(5), 'Cabin', dict(seed=69, lamp=False, pose='crouch'), dict(cam=dict(z0=1.1, z1=1.25, x0=0.15, y0=0.65, x1=0.15, y1=0.65))),
           (S(8), 'Stairs', dict(seed=68, rise=(0.35, 0.5)), {}),
           (S(10), 'TorchesRing', dict(seed=70, lights_out=0), dict(cam=dict(z0=1.1, z1=1.3))),
           (S(13), 'Stairs', dict(seed=68, rise=(0.55, 0.75)), {}),
           (S(15), 'Cabin', dict(seed=71, lamp=False, pose='crouch'), dict(cam=dict(z0=1.3, z1=1.45, x0=0.12, y0=0.7, x1=0.12, y1=0.7, shake=0.5))),
           (S(17), 'Paper', dict(kind='rules', lines=RULES), dict(cam=dict(z0=1.6, z1=1.75, x0=0.45, y0=0.83, x1=0.45, y1=0.84))),
           (S(19), 'Stairs', dict(seed=68, rise=(0.8, 0.95)), {}),
           (S(22), 'Door', dict(seed=72), dict(cam=dict(z0=1.0, z1=1.3)))],
    sfx=[(S(10, 0), 'chant_close', 0.4, 0), (S(24, 0), 'riser', 0.5, 0), (S(26, 0.3), 'hit', 0.9, 0)],
    stepsS=(T(-0.8), ('s', 22, -0.3), 1.7),
    fx=[(S(26, 0.3), 'glitch', 0.35, 0.6)],
    amb=[(T(-9), 'silent')],
    music=dict(root=34.65, intensity=0.8, high=0.55, pulse=95, mute=[('s', 23, 0), ('s', 26, 0.3)]))

sec('16', chapter='X.  A VERDADE',
    shots=[(T(-9), 'Door', dict(seed=73), dict(cam=dict(z0=1.1, z1=1.2))),
           (S(4), 'Cabin', dict(seed=74, lamp=False, pose='crouch'), dict(cam=dict(z0=1.0, z1=1.1, x0=0.2, y0=0.6, x1=0.2, y1=0.6))),
           (S(6), 'TowerNight', dict(seed=75, ring=True, cabin_lit=False, lights_out=0), dict(cam=dict(z0=1.3, z1=1.0))),
           (S(8), 'Phone', dict(seed=76), dict(cam=dict(z0=1.1, z1=1.2))),
           (S(15), 'Paper', dict(kind='notebook', lines=NOTE_ENTRIES), dict(cam=dict(z0=1.5, z1=1.7, x0=0.3, y0=0.48, x1=0.3, y1=0.5))),
           (S(20), 'Door', dict(seed=77, open_t=('s', 21, 0)), dict(cam=dict(z0=1.0, z1=1.15))),
           (S(23), 'Door', dict(seed=77, open_t=-10, beam_t=('s', 23, 0.3)), dict(cam=dict(z0=1.15, z1=1.3)))],
    sfx=[(S(0, 0), 'heartbeat', 0.5, 0), (S(20, 0), 'creak', 0.8, 0), (S(21, 0), 'scrape', 0.8, 0), (S(23, 0.3), 'click', 0.9, 0)],
    fx=[(S(23, 0.3), 'flash', 0.15, 0.4), (S(8, 0), 'glitch', 0.2, 0.3)],
    amb=[(T(-9), 'silent')],
    music=dict(root=34.65, intensity=0.7, high=0.45))

sec('17', chapter='',
    shots=[(T(-9), 'Door', dict(seed=78, open_t=-10, beam_t=-10, eyes_t=('s', 3, 0.6)), dict(cam=dict(z0=1.3, z1=1.6, x0=0.6, y0=0.45, x1=0.62, y1=0.4))),
           (S(5), 'Door', dict(seed=78, open_t=-10, beam_t=-10, eyes_t=-10), dict(cam=dict(z0=1.7, z1=1.4, x0=0.62, y0=0.4, x1=0.6, y1=0.45, shake=3.0))),
           (S(7), 'Climb', dict(seed=79), {}),
           (S(9), 'TowerNight', dict(seed=80, ring=True, cabin_lit=False, lights_out=0), dict(cam=dict(z0=1.0, z1=1.12, shake=0.6))),
           (S(12), 'Run', dict(seed=81), {}),
           (S(15), 'Bell', dict(seed=82, red=True, swing=0.7), dict(cam=dict(z0=1.0, z1=1.3, shake=1.0)))],
    sfx=[(S(5, 0.1), 'scream', 1.0, 0), (S(5, 0.1), 'hit', 0.9, 0), (S(7, 0.6), 'window_bang', 0.7, 0), (S(9, 0), 'bell_far', 0.6, 0),
         (S(10, 0), 'chant_short', 0.5, 0), (S(11, 0), 'steps_run_metal', 0.4, 0), (S(12, 0.5), 'run', 0.5, 0), (S(12, 0.5), 'breath', 0.4, 0)]
        + [(S(15, 0.1 + 1.0 * k), 'bell_mid', 0.6, 0) for k in range(5)],
    fx=[(S(5, 0.1), 'glitch', 1.0, 1.0), (S(5, 0.1), 'flash', 0.2, 0.6)],
    amb=[(T(-9), 'silent_wind'), (S(12), 'night')],
    music=dict(root=34.65, intensity=1.0, high=0.7, pulse=130))

sec('18', chapter='XI.  O AMANHECER',
    shots=[(T(-9), 'Run', dict(seed=83, torches=False), dict(cam=dict(shake=1.2))),
           (S(1), 'Road', dict(seed=84, truck=False, dawn=True, person=True), {}),
           (S(3), 'Room', dict(seed=85, city=True, phone=False), dict(cam=dict(z0=1.1, z1=1.2))),
           (S(4), 'TowerBase', dict(seed=86, clean=True, police=True), dict(cam=dict(z0=1.0, z1=1.1, x0=0.4, y0=0.6, x1=0.45, y1=0.6))),
           (S(8), 'TowerBase', dict(seed=86, clean=True, police=True), dict(cam=dict(z0=1.4, z1=1.6, x0=0.62, y0=0.68, x1=0.62, y1=0.7))),
           (S(11), 'Cabin', dict(seed=87, lamp=False, items=True), dict(cam=dict(z0=1.2, z1=1.3, x0=0.3, y0=0.55, x1=0.3, y1=0.55))),
           (S(13), 'Phone', dict(seed=88), dict(cam=dict(z0=1.3, z1=1.45, x0=0.5, y0=0.62, x1=0.5, y1=0.64))),
           (S(15), 'TowerNight', dict(seed=89, scale=0.55, side=0.5, cabin_lit=False), dict(cam=dict(z0=1.0, z1=1.08)))],
    sfx=[(S(0, 0), 'run', 0.4, 0), (S(1, 1.0), 'truck', 0.4, 0), (S(13, 0), 'static_short', 0.3, 0)],
    fx=[(S(13, 0.2), 'glitch', 0.3, 0.4)],
    amb=[(T(-9), 'day')],
    music=dict(root=43.65, intensity=0.3, piano=True))

sec('19', chapter='XII.  O FINAL', synthetic=40.0, lead=0, tail=0,
    shots=[(T(0), 'Room', dict(seed=90, city=True), dict(cam=dict(z0=1.0, z1=1.1))),
           (T(7.0), 'Phone', dict(seed=91, extra=AD_EXTRA, extra_t=7.0), dict(cam=dict(z0=1.0, z1=1.25, x0=0.5, y0=0.5, x1=0.5, y1=0.68))),
           (T(22.0), 'Room', dict(seed=92, city=True, phone=False), dict(cam=dict(z0=1.1, z1=1.25, x0=0.7, y0=0.4, x1=0.72, y1=0.38))),
           (T(32.0), 'Bell', dict(seed=93, red=True, swing=0.3), dict(cam=dict(z0=1.0, z1=1.25)))],
    texts=[(T(0.8), T(6.5), 'Meses depois. Outra cidade. Outro número.', 'caption'),
           (T(22.6), T(30.5), 'E naquela noite... do lado de fora da janela...', 'caption')],
    sfx=[(T(7.4), 'phone_buzz', 0.6, 0), (T(14.0), 'hit_soft', 0.8, 0), (T(28.5), 'bell_far', 0.7, 0.4), (T(32.0), 'bell_close', 0.9, 0)],
    fx=[(T(14.0), 'flash', 0.1, 0.2), (T(32.0), 'glitch', 0.4, 0.6)],
    amb=[(T(0), 'room'), (T(22), 'silent')],
    music=dict(root=34.65, intensity=0.5, high=0.35))

sec('19N', chapter='XII.  O FINAL', narrated_as='19',
    shots=[(T(-9), 'Room', dict(seed=90, city=True), dict(cam=dict(z0=1.0, z1=1.1))),
           (('find', 'Precisa-se'), 'Phone', dict(seed=91, extra=AD_EXTRA, extra_t=('find', 'Vaga reaberta')), dict(cam=dict(z0=1.0, z1=1.25, x0=0.5, y0=0.5, x1=0.5, y1=0.68))),
           (('find', 'E, naquela noite'), 'Room', dict(seed=92, city=True, phone=False), dict(cam=dict(z0=1.1, z1=1.25, x0=0.7, y0=0.4, x1=0.72, y1=0.38))),
           (('find', 'Um sino.'), 'Bell', dict(seed=93, red=True, swing=0.3), dict(cam=dict(z0=1.0, z1=1.25)))],
    sfx=[(('find', 'Vaga reaberta'), 'hit_soft', 0.8, 0), (('find', 'Um sino.'), 'bell_close', 0.9, 0)],
    amb=[(T(-9), 'room')],
    music=dict(root=34.65, intensity=0.5, high=0.35))

sec('20', synthetic=17.0, lead=0, tail=0,
    shots=[(T(0), 'EndCard', dict(lines=[('Gostou da história?', 90, (0.9, 0.86, 0.8)),
                                         ('Deixe seu like, inscreva-se e ative o sininho.', 50, (0.75, 0.72, 0.68)),
                                         ('Mas só esse sininho.', 50, (0.75, 0.72, 0.68)),
                                         ('Se ouvir qualquer outro... não olhe pela janela.', 46, (0.8, 0.25, 0.2))]), {})],
    sfx=[(T(11.0), 'bell_far', 0.6, 0)],
    amb=[(T(0), 'silent')],
    music=dict(root=36.71, intensity=0.3))

sec('20N', narrated_as='20',
    shots=[(T(-9), 'EndCard', dict(lines=[('Gostou da história?', 90, (0.9, 0.86, 0.8)),
                                          ('Deixe seu like, inscreva-se e ative o sininho.', 50, (0.75, 0.72, 0.68)),
                                          ('Mas só esse sininho.', 50, (0.75, 0.72, 0.68)),
                                          ('Se ouvir qualquer outro... não olhe pela janela.', 46, (0.8, 0.25, 0.2))]), {})],
    sfx=[(('find', 'Se ouvir qualquer outro'), 'bell_far', 0.6, 0)],
    amb=[(T(-9), 'silent')],
    music=dict(root=36.71, intensity=0.3))

ORDER = ['01', 'TITLE', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20']


def active_sections():
    """escolhe a versão narrada quando o áudio existe."""
    by = {s['id']: s for s in SECTIONS}
    out = []
    for k in ORDER:
        if (k + 'N') in by and k in ALIGN:
            out.append(by[k + 'N'])
        else:
            out.append(by[k])
    return out
