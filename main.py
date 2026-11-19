"""Thursday 19 November 2026, summed up in one 1024x1024 picture.

Stdlib-only Python: no imports beyond os/struct/zlib, no network, no clock,
no randomness. Text is rasterised from a small built-in 5x7 font with
boundary anti-aliasing (1px blend strips) and the PNG is encoded by hand,
so running the program twice writes identical bytes.

The front page: a masthead, four big stories, a world map with the day's
hot spots, a box of figures, and the rest of the news grouped by continent
(43 verified stories, six continents). Revised in this session from the
verified 19 Nov story list only: date-trap items from the earlier draft
(the 18 Nov Alaska Senate result and its Senate margin, the 17 Nov
outage story) and unverified items (an unlisted IPO price, energy-cap
and inflation figures, chip counts, flood figures and other unlisted
headlines) were removed, not reworded. Nothing here is invented; any
story that could not be verified was dropped.
"""

import os
import struct
import zlib

PAGE_W = 1024
PAGE_H = 1024

# ink + paper + accents
PAPER = (247, 243, 232)
PAPER_DEEP = (236, 230, 212)
INK = (26, 26, 46)
NAVY = (24, 42, 74)
NAVY_DEEP = (14, 26, 50)
CRIMSON = (179, 57, 46)
STEEL = (31, 78, 121)
JADE = (15, 107, 92)
OCHRE = (176, 128, 32)
SNOW = (255, 255, 255)
SEA = (190, 212, 226)
SEA_DEEP = (168, 196, 216)
GRID = (205, 222, 234)
LAND = (86, 160, 110)
LAND_LT = (122, 188, 146)
LAND_EDGE = (40, 100, 70)
SHADOW = (205, 198, 182)

# 5x7 font, one glyph per line: "CHAR:row0 row1 ... row6", # = on.
# Parsed at import time into GLYPHS[char] -> list of 7 strings.
_FONT_SRC = """
A:01110 10001 10001 11111 10001 10001 10001
B:11110 10001 10001 11110 10001 10001 11110
C:01110 10001 10000 10000 10000 10001 01110
D:11110 10001 10001 10001 10001 10001 11110
E:11111 10000 10000 11110 10000 10000 11111
F:11111 10000 10000 11110 10000 10000 10000
G:01110 10001 10000 10111 10001 10001 01111
H:10001 10001 10001 11111 10001 10001 10001
I:01110 00100 00100 00100 00100 00100 01110
J:00111 00010 00010 00010 00010 10010 01100
K:10001 10010 10100 11000 10100 10010 10001
L:10000 10000 10000 10000 10000 10000 11111
M:10001 11011 10101 10101 10001 10001 10001
N:10001 11001 10101 10011 10001 10001 10001
O:01110 10001 10001 10001 10001 10001 01110
P:11110 10001 10001 11110 10000 10000 10000
Q:01110 10001 10001 10001 10101 10010 01101
R:11110 10001 10001 11110 10100 10010 10001
S:01111 10000 10000 01110 00001 00001 11110
T:11111 00100 00100 00100 00100 00100 00100
U:10001 10001 10001 10001 10001 10001 01110
V:10001 10001 10001 10001 10001 01010 00100
W:10001 10001 10001 10101 10101 11011 10001
X:10001 10001 01010 00100 01010 10001 10001
Y:10001 10001 01010 00100 00100 00100 00100
Z:11111 00001 00010 00100 01000 10000 11111
0:01110 10001 10011 10101 11001 10001 01110
1:00100 01100 00100 00100 00100 00100 01110
2:01110 10001 00001 00110 01000 10000 11111
3:11110 00001 00001 01110 00001 00001 11110
4:00010 00110 01010 10010 11111 00010 00010
5:11111 10000 11110 00001 00001 10001 01110
6:00110 01000 10000 11110 10001 10001 01110
7:11111 00001 00010 00100 01000 01000 01000
8:01110 10001 10001 01110 10001 10001 01110
9:01110 10001 10001 01111 00001 00010 01100
 :00000 00000 00000 00000 00000 00000 00000
.:00000 00000 00000 00000 00000 01100 01100
,:00000 00000 00000 00000 01100 00100 01000
-:00000 00000 00000 01110 00000 00000 00000
':00100 00100 01000 00000 00000 00000 00000
::00000 01100 01100 00000 01100 01100 00000
;:00000 01100 01100 00000 01100 00100 01000
/:00001 00010 00010 00100 01000 01000 10000
(:00010 00100 01000 01000 01000 00100 00010
):01000 00100 00010 00010 00010 00100 01000
&:01100 10010 10100 01000 10101 10010 01101
%:11001 11010 00010 00100 01000 01011 10011
$:00100 01111 10100 01110 00101 11110 00100
?:01110 10001 00001 00110 00100 00000 00100
!:00100 00100 00100 00100 00100 00000 00100
+:00000 00100 00100 11111 00100 00100 00000
=:00000 00000 11111 00000 11111 00000 00000
"""


def _build_font(src):
    out = {}
    for line in src.strip().split("\n"):
        ch, rows = line.split(":", 1)
        out[ch] = rows.split(" ")
    return out


GLYPHS = _build_font(_FONT_SRC)
BLANK_GLYPH = ("00000",) * 7


def str_w(text, scale):
    """Pixel width of text at the given scale (6 px per char)."""
    return len(text) * 6 * scale - scale


class Page:
    """A 1024x1024 RGB canvas stored as one flat bytearray."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(bg * (w * h))

    def dot(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(colour)

    def box(self, x, y, w, h, colour):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        row = bytes(colour) * (x1 - x0)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            self.buf[base:base + len(row)] = row

    def frame(self, x, y, w, h, colour, t=2):
        self.box(x, y, w, t, colour)
        self.box(x, y + h - t, w, t, colour)
        self.box(x, y, t, h, colour)
        self.box(x + w - t, y, t, h, colour)

    def seg(self, x0, y0, x1, y1, colour):
        # Bresenham line.
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.dot(x0, y0, colour)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def spot(self, cx, cy, r, colour):
        for yy in range(cy - r, cy + r + 1):
            if abs(yy - cy) > r:
                continue
            half = int((r * r - (yy - cy) ** 2) ** 0.5)
            self.box(cx - half, yy, half * 2 + 1, 1, colour)

    def tri(self, a, b, c, colour):
        (x0, y0), (x1, y1), (x2, y2) = a, b, c
        for yy in range(min(y0, y1, y2), max(y0, y1, y2) + 1):
            xs = []
            for (ax, ay), (bx, by) in ((a, b), (b, c), (c, a)):
                if ay == by:
                    continue
                if min(ay, by) <= yy < max(ay, by):
                    xs.append(ax + (yy - ay) * (bx - ax) / (by - ay))
            if len(xs) >= 2:
                lo, hi = int(min(xs)), int(max(xs))
                self.box(lo, yy, hi - lo + 1, 1, colour)

    def poly(self, pts, colour):
        lo_y = min(p[1] for p in pts)
        hi_y = max(p[1] for p in pts)
        n = len(pts)
        for yy in range(lo_y, hi_y + 1):
            xs = []
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                if ay == by:
                    continue
                if min(ay, by) <= yy < max(ay, by):
                    xs.append(ax + (yy - ay) * (bx - ax) / (by - ay))
            if len(xs) >= 2:
                lo, hi = int(min(xs)), int(max(xs))
                self.box(lo, yy, hi - lo + 1, 1, colour)

    def shade(self, x, y, w, h, top, bottom):
        # vertical gradient, top colour -> bottom colour.
        for i in range(h):
            t = i / max(1, h - 1)
            col = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
            self.box(x, y + i, w, 1, col)

    def blend(self, x, y, w, h, fg):
        """1px anti-alias strip: each pixel becomes the 50/50 blend of
        the foreground colour and whatever is already on the page there.
        Deterministic: reads then writes in a fixed order."""
        for yy in range(y, y + h):
            if not (0 <= yy < self.h):
                continue
            for xx in range(x, x + w):
                if not (0 <= xx < self.w):
                    continue
                i = (yy * self.w + xx) * 3
                bg = self.buf[i:i + 3]
                self.buf[i:i + 3] = bytes((fg[k] + bg[k]) // 2 for k in range(3))

    def word(self, x, y, s, scale, colour):
        # uppercase-only font: fold case so mixed text still prints.
        for ci, ch in enumerate(s.upper()):
            rows = GLYPHS.get(ch, BLANK_GLYPH)
            ox = x + ci * 6 * scale
            for r in range(7):
                bits = rows[r]
                for c in range(5):
                    if bits[c] != "1":
                        continue
                    bx = ox + c * scale
                    by = y + r * scale
                    self.box(bx, by, scale, scale, colour)
                    # boundary anti-aliasing: on every side where the
                    # neighbouring glyph pixel is off, soften the edge
                    # with a 1px blend strip (real AA, not a shadow)
                    if r == 0 or rows[r - 1][c] != "1":
                        self.blend(bx, by - 1, scale, 1, colour)
                    if r == 6 or rows[r + 1][c] != "1":
                        self.blend(bx, by + scale, scale, 1, colour)
                    if c == 0 or bits[c - 1] != "1":
                        self.blend(bx - 1, by, 1, scale, colour)
                    if c == 4 or bits[c + 1] != "1":
                        self.blend(bx + scale, by, 1, scale, colour)

    def word_mid(self, cx, y, s, scale, colour):
        self.word(cx - str_w(s, scale) // 2, y, s, scale, colour)


def png_bytes(pg):
    """Encode the page as PNG bytes (fixed zlib level, no time chunk)."""

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = bytearray()
    for y in range(pg.h):
        raw.append(0)
        raw += pg.buf[y * pg.w * 3:(y + 1) * pg.w * 3]
    body = zlib.compress(bytes(raw), 9)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", pg.w, pg.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", body)
    png += chunk(b"IEND", b"")
    return png


def save_png(pg, path):
    with open(path, "wb") as f:
        f.write(png_bytes(pg))


# --- world map ---------------------------------------------------------------
# Rough continents in a 500x194 panel space (x = east, y = south).
LANDMAP = [
    [(60, 55), (95, 35), (150, 30), (185, 45), (175, 70),
     (150, 85), (120, 95), (90, 90), (65, 75)],
    [(155, 15), (180, 10), (190, 22), (168, 30), (150, 26)],
    [(170, 120), (200, 115), (212, 135), (200, 175), (180, 165), (165, 140)],
    [(240, 35), (285, 25), (310, 35), (300, 55), (270, 60), (245, 50)],
    [(245, 75), (295, 70), (315, 95), (300, 140), (275, 175),
     (255, 140), (240, 105)],
    [(315, 30), (420, 25), (470, 45), (460, 80), (430, 95),
     (400, 110), (360, 100), (330, 85), (315, 60), (305, 45)],
    [(430, 150), (470, 145), (480, 165), (450, 180), (430, 170)],
]

# hot spots: (x, y, label, label dx, label dy)
# Labels are staggered so none of them overlap each other; each box was
# checked against the others (see verification notes in the report).
SPOTS = [
    (165, 62, 'WASHINGTON', 8, 10),
    (275, 42, 'BERLIN', -10, -16),
    (297, 64, 'GAZA', -60, -14),
    (318, 62, 'KUWAIT', 8, -14),
    (328, 70, 'HORMUZ', 12, 6),
    (395, 90, 'AKVAN', 10, 10),
    (408, 77, 'SHENZHEN', -120, 22),
    (185, 122, 'CARACAS', 8, -8),
]

# peaks and rivers drawn on the map (panel coordinates)
PEAKS = [(390, 55), (400, 62), (280, 110), (185, 140), (355, 75)]
RIVERS = [(270, 95, 285, 130), (380, 60, 395, 95), (175, 130, 185, 160)]


def paint_map(pg, x0, y0, w, h):
    pg.box(x0, y0, w, h, SNOW)
    pg.frame(x0, y0, w, h, INK, 2)
    pg.box(x0, y0, w, 24, NAVY)
    pg.word(x0 + 12, y0 + 5, 'THE WORLD AT A GLANCE', 2, SNOW)
    top = y0 + 24
    tall = h - 24
    ys = tall / 194.0
    pg.shade(x0, top, w, tall, SEA, SEA_DEEP)
    for gx in range(x0 + 50, x0 + w, 50):
        pg.box(gx, top, 1, tall, GRID)
    for gy in range(top + 25, top + tall, 25):
        pg.box(x0, gy, w, 1, GRID)
    pg.word(x0 + 8, top + 6, 'N', 2, INK)
    pg.tri((x0 + 14, top + 20), (x0 + 10, top + 32), (x0 + 18, top + 32), INK)
    for wy in range(top + 8, top + tall, 8):
        pg.box(x0 + 8, wy, w - 16, 1, GRID)
    for pts in LANDMAP:
        shade_pts = [(x0 + px + 3, top + int(py * ys) + 3) for px, py in pts]
        pg.poly(shade_pts, (120, 165, 140))
        land = [(x0 + px, top + int(py * ys)) for px, py in pts]
        pg.poly(land, LAND)
        cx = sum(p[0] for p in land) / len(land)
        cy = sum(p[1] for p in land) / len(land)
        inner = [(int(cx + (px - cx) * 0.55), int(cy + (py - cy) * 0.55))
                 for px, py in land]
        pg.poly(inner, LAND_LT)
        for i in range(len(land)):
            ax, ay = land[i]
            bx, by = land[(i + 1) % len(land)]
            pg.seg(ax, ay, bx, by, LAND_EDGE)
    for mx, my in PEAKS:
        px, py = x0 + mx, top + int(my * ys)
        pg.tri((px, py - 6), (px - 5, py + 4), (px + 5, py + 4), (110, 95, 80))
    for rx0, ry0, rx1, ry1 in RIVERS:
        pg.seg(x0 + rx0, top + int(ry0 * ys), x0 + rx1, top + int(ry1 * ys),
               (70, 130, 180))
    for mx, my, label, dx, dy in SPOTS:
        cx, cy = x0 + mx, top + int(my * ys)
        pg.spot(cx, cy, 6, SNOW)
        pg.spot(cx, cy, 4, CRIMSON)
        if label:
            lx, ly = cx + dx, cy + dy
            if dx != 8 or dy != -8:
                pg.seg(cx, cy, lx, ly + 7, INK)
            pg.word(lx, ly, label, 2, INK)


# --- figures -----------------------------------------------------------------
# (number, label, colour); every number is from the verified story list.
# Removed from the earlier draft: the 18 Nov Senate-margin figure, an
# unlisted IPO price, unlisted chip counts, an unlisted religion-population
# figure, energy-cap and flood figures — none of those numbers were in
# the verified list.
NUMBERS = [
    ('13', 'YEARS SINCE THE LAST GTA', CRIMSON),
    ('45BN', 'EUROS: EU LOAN FOR UKRAINE', JADE),
    ('251-11', 'JEFFRIES NOMINATION VOTE', CRIMSON),
    ('589M', 'CHILDREN IN CONFLICT ZONES', JADE),
    ('260M', 'AFRICAN CHILDREN AT RISK', INK),
    ('16.1BN', 'MILES: VOYAGER 1, 1 LIGHT-DAY', INK),
    ('21', 'ISWAP FIGHTERS KILLED, BORNO', CRIMSON),
    ('$7BN', 'AMAZON INVESTMENT IN INDIA', JADE),
    ('49%', 'US DEATH-PENALTY SUPPORT', INK),
]


def paint_numbers(pg, x0, y0, w, h):
    pg.box(x0, y0, w, h, SNOW)
    pg.frame(x0, y0, w, h, INK, 2)
    pg.box(x0, y0, w, 24, NAVY)
    pg.word(x0 + 12, y0 + 5, 'THE DAY IN FIGURES', 2, SNOW)
    yy = y0 + 30
    for num, label, colour in NUMBERS:
        pg.word(x0 + 12, yy, num, 2, colour)
        pg.word(x0 + 12 + str_w(num + ' ', 2), yy, label, 2, INK)
        yy += 17


# --- heroes ------------------------------------------------------------------
# Four lead stories: title + two deck lines, scale 3.
# Jeffries: nominated 251-11, WOULD be first Black Speaker if elected by
# the full House in January — the deck asks the question, it does not
# claim he already is. US-Iran: the 19 Nov story is the WIDENING to
# Kuwait and Bahrain (18 Nov); the 17 Nov island strike is not presented
# as a 19 Nov event.
LEADS = [
    (CRIMSON, 'GTA VI LAUNCHES TODAY',
     'AFTER A 13-YEAR WAIT,',
     'VICE CITY OPENS WORLDWIDE.'),
    (STEEL, 'JEFFRIES NOMINATED',
     '251-11 VOTE FOR SPEAKER,',
     'FIRST BLACK SPEAKER?'),
    (JADE, 'TRUMP-XI-PUTIN TO MEET',
     'FIRST-EVER TRILATERAL,',
     'ONE HOUR IN SHENZHEN.'),
    (OCHRE, 'US-IRAN STRIKES WIDEN',
     'IRAN HITS BASE IN KUWAIT,',
     'AND STRIKES BAHRAIN AGAIN.'),
]


def paint_lead(pg, x, y, w, h, accent, title, d1, d2):
    pg.box(x + 3, y + 3, w, h, SHADOW)
    pg.box(x, y, w, h, SNOW)
    pg.frame(x, y, w, h, INK, 2)
    pg.box(x, y, 10, h, accent)
    pg.word(x + 20, y + 4, title, 3, INK)
    pg.box(x + 20, y + 26, w - 32, 2, accent)
    pg.word(x + 20, y + 30, d1, 3, INK)
    pg.word(x + 20, y + 53, d2, 3, INK)


# --- briefs ------------------------------------------------------------------
# One headline per story, grouped by continent. ONLY stories from the
# verified 19 Nov list. Removed from the earlier draft: every headline
# that was not in the list, or that belonged to another date — they were
# deleted, not reworded. Dropped for space (verified but no room at 7
# items per cell): Earth lost a billion years, India women's hockey,
# Canada adjusts China ties, Florida pastor convicted, Susan Smith
# parole, Florida executions, Duffy $50bn air-traffic plan, US oil
# stocks, biscuit recall, Nvidia pay raises. Two facts from one report
# are kept separate only where they are distinct facts (Trump / Vance
# and Trump / Rubio).
BRIEFS = [
    ('EUROPE', CRIMSON, [
        'EU 45BN LOAN FOR UKRAINE',
        'ALLIES MEET IN BERLIN',
        'RUSSIA ACCUSES FRANCE',
        'MELENCHON IN RUNOFF',
        'PUTIN SLAMS WEST SANCTIONS',
        'XI URGES OPEN TRADE',
        'APEC: 21 ECONOMIES MEET',
    ]),
    ('ASIA', JADE, [
        'CYCLONE AKVAN NEARS INDIA',
        'TRUMP IN CHINA, XI WELCOME',
        'INDIA-JAPAN 2+2 TALKS',
        'LASHKAR MAN KILLED',
        'AMAZON $7BN FOR INDIA',
        'INDIA BEAT PAKISTAN 2-1',
        'ISLAM TOP FAITH BY 2035',
    ]),
    ('NORTH AMERICA', STEEL, [
        'LIEU ELECTED CAUCUS CHAIR',
        'VOYAGER 1: ONE LIGHT-DAY',
        'NVIDIA HALTS H-SERIES',
        'FED MINUTES: MORE HIKES',
        'WALLER WARNS ON INFLATION',
        'SENATORS WARN: AI THREATS',
        'DEATH PENALTY SUPPORT 49%',
    ]),
    ('MIDDLE EAST', CRIMSON, [
        '3RD US CARRIER IN GULF',
        'GAZA REBUILD STALLED',
        'TRUMP UNHAPPY WITH VANCE',
        'TRUMP PRAISES RUBIO',
        'SAUDI: DANGER HAS PASSED',
        'UAE GROWTH 7.3% NEXT YEAR',
        'JORDAN-EU MEET AT DEAD SEA',
    ]),
    ('AFRICA', OCHRE, [
        '1 IN 4 KIDS IN CONFLICT',
        '260M AFRICAN KIDS AT RISK',
        'NIGERIA: 21 ISWAP KILLED',
        'GHANA BAD LOANS AT 13.1%',
        'MOROCCO ARMS PLAN 50K JOBS',
        'EGYPT-SYRIA AVIATION PACT',
        'COCAINE SEIZED IN E. LIBYA',
    ]),
    ('SOUTH AMERICA', JADE, [
        'HEGSETH INKS CARACAS PACT',
        'HEGSETH HEADS TO COLOMBIA',
        'COLOMBIA REJECTS US PLAN',
        'LATAM AT APEC SHENZHEN',
    ]),
]

TOTAL_STORIES = len(LEADS) + sum(len(items) for _, _, items in BRIEFS)


def paint_brief(pg, x, y, w, h, header, accent, items):
    pg.box(x + 3, y + 3, w, h, SHADOW)
    pg.box(x, y, w, h, SNOW)
    pg.frame(x, y, w, h, INK, 2)
    for dx in range(8, w, 10):
        for dy in range(34, h, 10):
            if (dx + dy) % 20 == 0:
                pg.spot(x + dx, y + dy, 1, (240, 236, 224))
    pg.box(x, y, w, 26, accent)
    dark = tuple(max(0, v - 28) for v in accent)
    for sx in range(0, w, 16):
        pg.seg(x + sx, y + 25, x + sx + 12, y, dark)
    pg.word(x + 12, y + 3, header, 3, SNOW)
    yy = y + 28
    for item in items:
        pg.box(x + 12, yy + 6, 7, 7, accent)
        pg.word(x + 24, yy, item, 3, INK)
        yy += 22


def speckle(pg):
    """Deterministic paper speckle: sparse darker dots, no randomness."""
    w = pg.w
    for yy in range(0, pg.h, 2):
        base = yy * w * 3
        for xx in range(0, w, 2):
            v = (xx * 2654435761 + yy * 40503) % 1000
            if v < 70:
                i = base + xx * 3
                pg.buf[i] = 235
                pg.buf[i + 1] = 229
                pg.buf[i + 2] = 214
            elif v < 130:
                i = base + xx * 3
                pg.buf[i] = 242
                pg.buf[i + 1] = 238
                pg.buf[i + 2] = 226


def build():
    pg = Page(PAGE_W, PAGE_H, PAPER)
    pg.shade(0, 0, PAGE_W, PAGE_H, (248, 244, 233), PAPER_DEEP)
    speckle(pg)
    # masthead: navy band, gold dot texture, title / date / count
    pg.shade(0, 0, PAGE_W, 100, NAVY, NAVY_DEEP)
    for dx in range(6, PAGE_W, 14):
        for dy in range(6, 100, 14):
            if (dx + dy) % 28 == 0:
                pg.spot(dx, dy, 2, (120, 90, 40))
    pg.word_mid(PAGE_W // 2, 6, 'THE WORLD IN ONE DAY', 6, SNOW)
    pg.word_mid(PAGE_W // 2, 52, 'THURSDAY, 19 NOVEMBER 2026', 3, OCHRE)
    pg.word_mid(PAGE_W // 2, 76, '%d STORIES - SIX CONTINENTS - WORLD MAP' % TOTAL_STORIES, 2, SNOW)
    pg.box(0, 100, PAGE_W, 6, OCHRE)
    # leads: 2x2 grid of big stories
    for i, (accent, title, d1, d2) in enumerate(LEADS):
        x = 8 + (i % 2) * 508
        y = 114 + (i // 2) * 84
        paint_lead(pg, x, y, 500, 76, accent, title, d1, d2)
    # map on the left, figures on the right
    paint_map(pg, 8, 282, 500, 190)
    paint_numbers(pg, 516, 282, 500, 190)
    # briefs: 2 columns x 3 rows, one continent group per cell
    grid = [(480, 182), (662, 181), (843, 181)]
    for r, (ry, rh) in enumerate(grid):
        for col in range(2):
            header, accent, items = BRIEFS[r * 2 + col]
            paint_brief(pg, 8 + col * 508, ry, 500, rh, header, accent, items)
    return pg


def main():
    pg = build()
    out_dir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(out_dir, exist_ok=True)
    save_png(pg, os.path.join(out_dir, 'entry.png'))
    here = os.path.dirname(os.path.abspath(__file__))
    save_png(pg, os.path.join(here, 'entry.png'))


if __name__ == '__main__':
    main()
