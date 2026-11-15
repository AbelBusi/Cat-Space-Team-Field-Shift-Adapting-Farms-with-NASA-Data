"""Draws Sprout, the alien cat guide, as pixel art and writes web/src/cat/sprites.js.

Sprout is an original character: a green alien cat sitting on the ground, with long ear tufts, fluffy cheeks and chest,
a big curled tail and two antennae with glowing tips. The body is built from simple shapes (ellipses, triangles, a
curve for the tail); each layer gets an inner outline and light from the top left, so later layers (head over body,
paw over chest) draw their own edge. Faces are small hand-drawn stamps, one per mood.

Usage: python draw_sprout.py ../web/src/cat/sprites.js [preview.png]
"""
import json
import math
import sys

W, H = 48, 50
PALETTE = {"o": "#1E3A14", "g": "#7FCF4A", "G": "#58A333", "l": "#B4EC7E", "p": "#4E8F2C", "a": "#2C5A1C",
           "y": "#FFE45C", "Y": "#E3B21E", "w": "#FFFFFF", "e": "#0E0F14", "r": "#B8434F", "b": "#F49AA6",
           "s": "#8FD3FF", "c": "#D6F5B0", "i": "#2E6E86", "m": "#8C9BC4", "f": "#F2A541", "v": "#1E2A52", "n": "#F2E8D5", "t": "#4FC1B6"}


def ellipse(cx, cy, rx, ry):
    return {(x, y) for x in range(W) for y in range(H) if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1}


def polygon(pts):
    out = set()
    for y in range(H):
        for x in range(W):
            px, py, hit = x + .5, y + .5, False
            for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
                if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
                    hit = not hit
            if hit:
                out.add((x, y))
    return out


def tube(path, r0, r1):
    """A thick curve: discs along a quadratic Bézier, radius going from r0 to r1."""
    (x0, y0), (x1, y1), (x2, y2) = path
    out = set()
    for k in range(41):
        t = k / 40
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * x1 + t * t * x2
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * y1 + t * t * y2
        out |= ellipse(x, y, r0 + (r1 - r0) * t, r0 + (r1 - r0) * t)
    return out


def mirror(pts):
    return [(44 - x, y) for x, y in pts]


def paint(grid, mask, fill='g', light=True):
    """Fill a layer, outline its edge inside the shape, and shade it: light top-left, shadow bottom-right."""
    for x, y in mask:
        edge = any((x + dx, y + dy) not in mask for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            grid[y][x] = 'o'
        elif light and ((x + 1, y + 2) not in mask or (x + 2, y + 1) not in mask):
            grid[y][x] = 'G'
        elif light and fill == 'g' and ((x - 1, y - 1) not in mask or (x - 2, y - 2) not in mask) and (x - 1, y - 2) not in mask:
            grid[y][x] = 'l'
        else:
            grid[y][x] = fill


def body(pose='sit', tail='up'):
    g = [['.'] * W for _ in range(H)]
    # Tail behind everything: from the back, up along the right side.
    tails = {'up': [(31, 44), (45, 42), (40, 27)], 'wag': [(31, 44), (46, 38), (43, 26)]}
    paint(g, tube(tails[tail], 2.6, 4.2))
    tip = tails[tail][2]
    for x, y in ellipse(tip[0] - .5, tip[1] - .5, 2.2, 2.2):
        if g[y][x] not in 'o':
            g[y][x] = 'c'
    # Body, haunch and the fluffy chest.
    paint(g, ellipse(22, 35.5, 9.5, 10.5) | ellipse(28.5, 41, 7, 6) | ellipse(22, 45.5, 10, 2.5))
    # Long chest fur: a zigzag bib under the chin.
    chest = polygon([(14, 26), (30, 26), (29, 32), (27, 30), (26, 35), (24, 31), (22, 37), (20, 31), (18, 35), (17, 30), (15, 32)])
    for x, y in chest:
        if g[y][x] != 'o':
            g[y][x] = 'c' if (x + y) % 5 else 'l'
    # Front paws (one raised to wave in the 'wave' pose).
    paint(g, ellipse(25.5, 46, 2.8, 2.2))
    if pose == 'wave':
        paint(g, ellipse(12.5, 30, 2.8, 3.4) | polygon([(15, 37), (18, 35), (14, 31), (11, 32)]))
        for x, y in ((11, 28), (13, 28)):
            g[y][x] = 'o'
    else:
        paint(g, ellipse(18.5, 46, 2.8, 2.2))
    # Ears: tall triangles with a darker inside and a tuft at the tip.
    ear = [(10, 16), (17, 8), (6, 1)]
    for pts in (ear, mirror(ear)):
        paint(g, polygon(pts))
    for pts in ([(11, 13), (15, 9), (8, 4)], mirror([(11, 13), (15, 9), (8, 4)])):
        for x, y in polygon(pts):
            g[y][x] = 'p'
    # Head with fluffy cheeks.
    cheek = [(11, 17), (5, 20), (10, 21), (6, 24), (11, 24.5), (9, 27), (14, 26)]
    paint(g, ellipse(22, 17.5, 12.5, 10) | polygon(cheek) | polygon(mirror(cheek)))
    # Chin shadow over the chest.
    for x in range(W):
        for y in range(H - 1):
            if g[y][x] == 'o' and y > 24 and g[y + 1][x] in 'cl':
                g[y + 1][x] = 'G'
    return g


def antennae(g, kind='up'):
    """Two stalks from the top of the head with glowing tips."""
    shapes = {
        'up': [[(19, 8), (18, 4)], [(25, 8), (26, 4)]],
        'perk': [[(19, 8), (15, 3)], [(25, 8), (29, 3)]],
        'droop': [[(19, 8), (17, 5), (15, 5)], [(25, 8), (27, 5), (29, 5)]],
        'question': [[(19, 8), (18, 4)], [(25, 8), (26, 5), (28, 4)]],
    }[kind]
    for stalk in shapes:
        for (x0, y0), (x1, y1) in zip(stalk, stalk[1:]):
            n = max(abs(x1 - x0), abs(y1 - y0))
            for k in range(n + 1):
                x, y = round(x0 + (x1 - x0) * k / n), round(y0 + (y1 - y0) * k / n)
                if g[y][x] in '.o':
                    g[y][x] = 'a'
        tx, ty = stalk[-1]
        for dx, dy, c in ((0, -1, 'y'), (-1, -1, 'y'), (0, -2, 'w'), (-1, -2, 'y'), (1, -1, 'Y'), (0, 0, 'Y'), (-1, 0, 'y'), (1, -2, 'y')):
            if 0 <= ty + dy < H and 0 <= tx + dx < W:
                g[ty + dy][tx + dx] = c


# ---- Faces: stamps placed on the head. Eyes are centered at x 16 and 28, y 18; the mouth at x 22, y 23. ----
EYE = [".eee.", "ewwee", "eweee", "eeeee", "eeiie", ".eee."]       # big dark eye, white shine, a blue glint below
EYE_CLOSED_HAPPY = [".eee.", "e...e"]
EYE_LINE = ["eeeee"]
EYE_STAR = ["..y..", ".yyy.", "yywyy", ".yyy.", "y...y"]
EYE_WIDE = [".www.", "wwwww", "wweww", "wwwww", ".www."]            # tiny pupils: startled
EYE_LOOK_DOWN = [".....", ".eee.", "eweee", "eeiie", ".eee."]
EYE_HALF = ["eeeee", "eweee", "eeiie", ".eee."]
TEAR = ["s", "s"]
MOUTHS = {
    'w': ["e...e", ".e.e."],                 # the cat mouth, :3
    'smile': ["e....e", ".eeee."],
    'open': ["eeeee", "errre", "erbre", ".eee."],
    'big': ["eeeeeee", "errrrre", "errbbre", ".eeeee."],
    'o': [".ee.", "erre", ".ee."],
    'wavy': [".e..e.", "e.ee.e"],
    'frown': [".eeee.", "e....e"],
    'flat': ["eeee"],
    'small': [".e.", "e.e"],
}
FACES = {
    #           eyes (left, right)                 brows             mouth    blush antennae extras
    'neutral':  dict(eyes=(EYE, EYE), mouth='w', ant='up'),
    'happy':    dict(eyes=(EYE_CLOSED_HAPPY, EYE_CLOSED_HAPPY), mouth='open', blush=True, ant='up'),
    'excited':  dict(eyes=(EYE_STAR, EYE_STAR), mouth='big', blush=True, ant='perk'),
    'surprised': dict(eyes=(EYE_WIDE, EYE_WIDE), mouth='o', ant='perk'),
    'worried':  dict(eyes=(EYE, EYE), brows='worried', mouth='wavy', ant='droop'),
    'thinking': dict(eyes=(EYE_HALF, EYE), mouth='flat', ant='question'),
    'sad':      dict(eyes=(EYE, EYE), brows='worried', mouth='frown', tears=True, ant='droop'),
    'shy':      dict(eyes=(EYE_LOOK_DOWN, EYE_LOOK_DOWN), mouth='small', blush=True, ant='droop'),
    'determined': dict(eyes=(EYE_HALF, EYE_HALF), brows='angry', mouth='flat', ant='perk'),
    'sleepy':   dict(eyes=(EYE_LINE, EYE_LINE), mouth='o', ant='droop'),
}


def stamp(g, rows, x0, y0):
    for dy, row in enumerate(rows):
        for dx, c in enumerate(row):
            if c != '.':
                g[y0 + dy][x0 + dx] = c


def face(mood, talking=False, blink=False):
    """Only the face pixels, on a transparent sprite: drawn over the body."""
    f = FACES[mood]
    g = [['.'] * W for _ in range(H)]
    eyes = (EYE_LINE, EYE_LINE) if blink and f['eyes'][0] in (EYE, EYE_WIDE, EYE_LOOK_DOWN, EYE_HALF) else f['eyes']
    for rows, cx in zip(eyes, (16, 28)):
        stamp(g, rows, cx - 2, 18 - len(rows) // 2)
    if f.get('brows') == 'worried':
        stamp(g, ["..ee", "ee.."], 14, 12)
        stamp(g, ["ee..", "..ee"], 27, 12)
    if f.get('brows') == 'angry':
        stamp(g, ["ee..", "..ee"], 14, 13)
        stamp(g, ["..ee", "ee.."], 27, 13)
    if f.get('blush'):
        for cx in (12, 32):
            stamp(g, ["b.b", ".b."], cx - 1, 22)
    if f.get('tears') and not blink:
        stamp(g, TEAR, 14, 22)
        stamp(g, TEAR, 30, 22)
    stamp(g, ["rr"], 21, 22)                                               # nose
    m = MOUTHS['open' if talking and f['mouth'] in ('w', 'smile', 'flat', 'small', 'wavy', 'frown') else f['mouth']]
    stamp(g, m, 22 - len(m[0]) // 2, 24)
    return g


def ufo():
    """Sprout's ship, 40 × 18: a glass dome on a metal saucer with a row of campfire lights."""
    UW, UH = 40, 18
    g = [['.'] * UW for _ in range(UH)]
    inside = lambda cx, cy, rx, ry, x, y: ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1
    dome = {(x, y) for x in range(UW) for y in range(UH) if y < 9 and inside(20, 9, 9, 8, x, y)}
    disc = {(x, y) for x in range(UW) for y in range(UH) if inside(20, 11, 19.5, 4.5, x, y)}
    base = {(x, y) for x in range(UW) for y in range(UH) if y >= 13 and inside(20, 14, 7, 3.5, x, y)}
    for mask, fill, hi, lo in ((base, 'm', 'n', 'v'), (disc, 'm', 'n', 'v'), (dome, 't', 's', 'i')):
        for x, y in mask:
            edge = any((x + dx, y + dy) not in mask for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            g[y][x] = 'e' if edge else hi if (x - 2, y - 2) not in mask else lo if (x + 1, y + 2) not in mask else fill
    for x in range(4, 37, 4):                                   # the lights around the rim
        g[12][x] = 'f'
    g[16][19] = g[16][20] = 'y'                                 # the beam's eye
    return [''.join(r) for r in g]


def rows(g):
    return [''.join(r) for r in g]


def runs(lines):
    """Rows → horizontal runs of one color, [x, y, width, color]: compact, and one <rect> each in the page."""
    out = []
    for y, row in enumerate(lines):
        x = 0
        while x < len(row):
            w = 1
            while x + w < len(row) and row[x + w] == row[x]:
                w += 1
            if row[x] != '.':
                out.append([x, y, w, row[x]])
            x += w
    return out


def main(out, preview=None):
    bodies = {f'{pose}_{tail}': rows(body(pose, tail)) for pose in ('sit', 'wave') for tail in ('up', 'wag')}
    ants = {}
    for kind in ('up', 'perk', 'droop', 'question'):
        g = [['.'] * W for _ in range(H)]
        antennae(g, kind)
        ants[kind] = rows(g)
    faces = {m: {'face': rows(face(m)), 'talk': rows(face(m, talking=True)), 'blink': rows(face(m, blink=True)), 'ant': FACES[m]['ant']} for m in FACES}
    pack = lambda d: json.dumps(d, separators=(',', ':'))
    js = ["// Sprout, the alien cat guide: original pixel art, 48 × 50. Generated by pipeline/draw_sprout.py (draw there).",
          "// Each layer is a list of runs [x, y, width, color key]; colors live in PALETTE.",
          "// BODY: pose (sit, wave) × tail (up, wag). ANTENNAE: up, perk, droop, question. FACES: mood → face, talk, blink, ant.",
          f"export const SIZE = [{W}, {H}]",
          f"export const PALETTE = {json.dumps(PALETTE)}",
          f"export const BODY = {pack({k: runs(v) for k, v in bodies.items()})}",
          f"export const ANTENNAE = {pack({k: runs(v) for k, v in ants.items()})}",
          f"export const FACES = {pack({m: {k: (runs(v) if k != 'ant' else v) for k, v in f.items()} for m, f in faces.items()})}",
          "export const UFO_SIZE = [40, 18]",
          f"export const UFO = {pack(runs(ufo()))}", ""]
    open(out, 'w').write('\n'.join(js))
    if preview:
        from PIL import Image
        S, moods = 6, list(FACES)
        img = Image.new('RGB', ((W * S + 6) * len(moods), (H * S + 6) * 2), (11, 16, 38))
        for n, m in enumerate(moods):
            for r, pose in enumerate(('sit_up', 'wave_wag')):
                layers = [bodies[pose], ants[faces[m]['ant']], faces[m]['face']]
                for L in layers:
                    for y, row in enumerate(L):
                        for x, c in enumerate(row):
                            if c == '.':
                                continue
                            col = tuple(int(PALETTE[c][i:i + 2], 16) for i in (1, 3, 5))
                            for dy in range(S):
                                for dx in range(S):
                                    img.putpixel((n * (W * S + 6) + x * S + dx, r * (H * S + 6) + y * S + dy), col)
        img.save(preview)


if __name__ == '__main__':
    main(*sys.argv[1:])
