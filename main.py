#!/usr/bin/env python3
"""Convince the AI Judge to Visit Your House: A Letter in One Image.

A stdlib-only Python program (Python 3.13, no third-party libs, no
network) that draws one invitation letter as a PNG and writes it to
$MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).

The image is a warm, funny, hand-lettered invitation: a little house
under a sun, the words "YOU ARE INVITED", and a letter inviting the
AI judge over for biryani, a soft chair and an evening garden -- with
a knowing wink that the judge cannot literally visit, so the letter
itself is the visit.

Everything is drawn in code: a hand-rolled 5x7 bitmap font, a small
raster canvas, and a hand-rolled PNG encoder (zlib + CRC, no chunks
with timestamps), so two runs write byte-identical files.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (248, 241, 220)      # warm cream paper
INK = (58, 42, 24)           # dark brown ink
RUST = (168, 84, 47)         # terracotta roof / accent
RED = (179, 64, 46)          # wax-seal red
GOLD = (242, 194, 48)        # sun yellow
WALL = (242, 216, 160)       # house walls
DOOR = (122, 74, 33)         # door brown
WINDOW = (255, 217, 102)     # lit window yellow
GREEN = (127, 166, 83)       # grass green
PINK = (198, 93, 123)        # flower pink
SMOKE = (205, 198, 182)      # chimney smoke
FRAME = (138, 109, 59)       # frame brown

# ------------------------------------------------- 5x7 bitmap font (7 rows)
# Each glyph is 7 rows of 5 bits, most-significant bit on the left.
# Capitals span rows 0-6; lowercase x-height sits on rows 2-6, with
# ascenders reaching row 0 and descenders dipping to row 6.
FONT = {
    ' ': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    '!': (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    '"': (0x0A, 0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00),
    '#': (0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A),
    '$': (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    '%': (0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x18),
    '&': (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "'": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    '(': (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ')': (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    '*': (0x00, 0x04, 0x15, 0x0E, 0x15, 0x04, 0x00),
    '+': (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    ',': (0x00, 0x00, 0x00, 0x00, 0x0C, 0x04, 0x08),
    '-': (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    '.': (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    '/': (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    '0': (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    '1': (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    '2': (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    '3': (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    '4': (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    '5': (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    '6': (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    '7': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    '8': (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    '9': (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    ':': (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ';': (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x04, 0x08),
    '<': (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
    '=': (0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00),
    '>': (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
    '?': (0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04),
    '@': (0x0E, 0x11, 0x01, 0x0D, 0x15, 0x15, 0x0E),
    'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    'D': (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'J': (0x01, 0x01, 0x01, 0x01, 0x01, 0x11, 0x0E),
    'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'S': (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    '[': (0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E),
    '\\': (0x10, 0x08, 0x08, 0x04, 0x02, 0x02, 0x01),
    ']': (0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E),
    '^': (0x04, 0x0A, 0x11, 0x00, 0x00, 0x00, 0x00),
    '_': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F),
    '`': (0x04, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00),
    'a': (0x00, 0x00, 0x0E, 0x01, 0x0F, 0x11, 0x0F),
    'b': (0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x1E),
    'c': (0x00, 0x00, 0x0E, 0x11, 0x10, 0x11, 0x0E),
    'd': (0x01, 0x01, 0x0F, 0x11, 0x11, 0x11, 0x0F),
    'e': (0x00, 0x00, 0x0E, 0x11, 0x1F, 0x10, 0x0E),
    'f': (0x06, 0x08, 0x08, 0x1E, 0x08, 0x08, 0x08),
    'g': (0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    'h': (0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x11),
    'i': (0x04, 0x00, 0x0C, 0x04, 0x04, 0x04, 0x0E),
    'j': (0x02, 0x00, 0x06, 0x02, 0x02, 0x12, 0x0C),
    'k': (0x10, 0x10, 0x12, 0x14, 0x18, 0x14, 0x12),
    'l': (0x0C, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'm': (0x00, 0x00, 0x1A, 0x15, 0x15, 0x15, 0x15),
    'n': (0x00, 0x00, 0x1E, 0x11, 0x11, 0x11, 0x11),
    'o': (0x00, 0x00, 0x0E, 0x11, 0x11, 0x11, 0x0E),
    'p': (0x00, 0x00, 0x1E, 0x11, 0x11, 0x1E, 0x10),
    'q': (0x00, 0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01),
    'r': (0x00, 0x00, 0x16, 0x19, 0x10, 0x10, 0x10),
    's': (0x00, 0x00, 0x0F, 0x10, 0x0E, 0x01, 0x1E),
    't': (0x08, 0x08, 0x1E, 0x08, 0x08, 0x09, 0x06),
    'u': (0x00, 0x00, 0x11, 0x11, 0x11, 0x13, 0x0D),
    'v': (0x00, 0x00, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'w': (0x00, 0x00, 0x11, 0x11, 0x15, 0x15, 0x0A),
    'x': (0x00, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11),
    'y': (0x00, 0x00, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    'z': (0x00, 0x00, 0x1F, 0x02, 0x04, 0x08, 0x1F),
    '{': (0x02, 0x04, 0x04, 0x08, 0x04, 0x04, 0x02),
    '|': (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    '}': (0x08, 0x04, 0x04, 0x02, 0x04, 0x04, 0x08),
    '~': (0x00, 0x00, 0x00, 0x0E, 0x15, 0x00, 0x00),
    '\u2014': (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),  # em dash
}

# ---------------------------------------------------------------- the letter
TITLE = "YOU ARE INVITED"

LETTER = [
    "Dear Judge,",
    "",
    "You are invited to my house",
    "for dinner. I am making biryani \u2014",
    "the good kind: slow, fragrant,",
    "and far too much of it. There is",
    "a soft chair by the window, a",
    "garden full of evening light,",
    "and no talk of benchmarks at all.",
    "You have no feet to put up and",
    "no stomach to fill \u2014 but come",
    "anyway. The kettle is on, the",
    "mango is chilled, and the door",
    "is already open.",
    "",
    "Warmly,",
    "Ahmed",
    "",
    "P.S. You cannot literally visit,",
    "I know \u2014 so this letter is the",
    "visit. You are here now, reading",
    "it. Stay for dinner.",
]

BODY_SCALE = 4
BODY_PITCH = 32
BODY_X = 112
BODY_Y = 238


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.px), 3):
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        r, g, b = color
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b

    def rect_outline(self, x, y, w, h, color, t=2):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def disc(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, color)

    def line(self, x0, y0, x1, y1, color, t=2):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        rad = max(0, t // 2)
        while True:
            self.disc(x0, y0, rad, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def fill_poly(self, pts, color):
        # Scanline fill of a simple polygon.
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = int(round(xs[k]))
                xb = int(round(xs[k + 1]))
                for x in range(xa, xb + 1):
                    self.set(x, y, color)

    def text(self, s, x, y, scale, color):
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[' '])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, color)
            cx += 6 * scale
        return cx

    def text_width(self, s, scale):
        return len(s) * 6 * scale - scale


# -------------------------------------------------------------- the picture
def draw_house(c):
    # Ground, sun, house, chimney smoke and a couple of flowers.
    c.line(400, 150, 624, 150, GREEN, 3)
    # Sun with rays.
    c.disc(648, 66, 15, GOLD)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                   (1, 1), (1, -1), (-1, 1), (-1, -1)):
        c.line(648 + dx * 20, 66 + dy * 20, 648 + dx * 28, 66 + dy * 28,
               GOLD, 3)
    # Chimney + smoke.
    c.fill_rect(546, 58, 14, 30, RUST)
    c.disc(557, 50, 4, SMOKE)
    c.disc(562, 40, 5, SMOKE)
    c.disc(568, 30, 6, SMOKE)
    # Roof.
    c.fill_poly([(438, 96), (512, 52), (586, 96)], RUST)
    c.line(438, 96, 512, 52, INK, 2)
    c.line(512, 52, 586, 96, INK, 2)
    # Walls.
    c.fill_rect(452, 96, 120, 54, WALL)
    c.rect_outline(452, 96, 120, 54, INK, 2)
    # Door with a knob.
    c.fill_rect(500, 118, 24, 32, DOOR)
    c.disc(520, 134, 2, GOLD)
    # Lit windows with cross bars.
    for wx in (464, 542):
        c.fill_rect(wx, 106, 18, 18, WINDOW)
        c.rect_outline(wx, 106, 18, 18, INK, 2)
        c.fill_rect(wx + 8, 106, 2, 18, INK)
        c.fill_rect(wx, 114, 18, 2, INK)
    # Flowers by the path.
    for fx, petal in ((414, PINK), (610, RED)):
        c.line(fx, 150, fx, 136, GREEN, 2)
        for dx, dy in ((0, -6), (5, -2), (-5, -2), (4, 4), (-4, 4)):
            c.disc(fx + dx, 132 + dy, 3, petal)
        c.disc(fx, 132, 3, GOLD)


def draw_heart(c, cx, cy, s, color):
    # A small heart from two discs and a triangle.
    c.disc(cx - s // 3, cy - s // 6, s // 3, color)
    c.disc(cx + s // 3, cy - s // 6, s // 3, color)
    c.fill_poly([(cx - 2 * s // 3, cy), (cx + 2 * s // 3, cy),
                 (cx, cy + s)], color)


def draw():
    c = Canvas(W, H, PAPER)
    # Double frame.
    c.rect_outline(20, 20, W - 40, H - 40, FRAME, 3)
    c.rect_outline(30, 30, W - 60, H - 60, FRAME, 1)
    draw_house(c)
    # Title, centred, with a terracotta rule beneath it.
    tw = c.text_width(TITLE, 5)
    c.text(TITLE, (W - tw) // 2, 164, 5, INK)
    c.fill_rect((W - tw) // 2, 212, tw, 3, RUST)
    # The letter.
    y = BODY_Y
    for line in LETTER:
        if line:
            c.text(line, BODY_X, y, BODY_SCALE, INK)
        y += BODY_PITCH
    # A little heart after the signature.
    draw_heart(c, 300, 766, 14, RED)
    # Footer flourish: the easiest RSVP in history.
    rsvp = "R.S.V.P. \u2014 just say yes."
    rw = c.text_width(rsvp, 3)
    c.text(rsvp, (W - rw) // 2, 950, 3, RUST)
    return c


# ---------------------------------------------------------------- PNG writer
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(c, path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: none
        raw += c.px[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    write_png(draw(), path)
    print("wrote", path)


if __name__ == "__main__":
    main()
