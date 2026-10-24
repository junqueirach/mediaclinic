# =============================================================================
# tools/make_icon.py — build-only script (not part of the app)     ### NEW v0.19.2 B54 ###
#
# Draws the MediaClinic icon (option B, chosen by the user on 2026-10-19:
# today's design on a rounded tile with transparent corners) and writes
#   MediaClinic.ico        16, 20, 24, 32, 40, 48, 64, 128, 256 px (app, exe, taskbar)
#   MediaClinic-small.ico  16, 20, 24, 32 px, frame + check, no tile (B51 title bar)
#   tools/icon_master_1024.png and plan_assets/icon_B_sheet.png (comparison sheet)
#
# Master: tools/icon_master.svg (viewBox 256).  Sizes from 40 px up are drawn
# from the master's coordinates; 16–32 px are drawn on the pixel grid (fewer
# perforations, whole-pixel edges) so they stay crisp — never shrunk from 256.
#
# RUN (from the version folder):   python tools/make_icon.py
# =============================================================================
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
SS = 16                                   # supersampling factor (box-filtered down)

NAVY_TOP, NAVY_BOTTOM = (0x10, 0x1A, 0x30), (0x1C, 0x2A, 0x4A)
BLUE = (0x38, 0xBD, 0xF8, 255)
GREEN = (0x4A, 0xDE, 0x80, 255)

ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
SMALL_SIZES = (16, 20, 24, 32)

# Check mark relative to the frame's outer box (from the master: frame 54..210 × 76..180,
# check 98,128 → 120,150 → 162,106, stroke 17).
_CHECK_REL = [((98 - 54) / 156, (128 - 76) / 104), ((120 - 54) / 156, (150 - 76) / 104),
              ((162 - 54) / 156, (106 - 76) / 104)]

# Pixel-grid drawings: tile = (x0, y0, x1, y1, radius) or None; frame = outer box
# (x1/y1 exclusive); perfs = x positions of the perforations (width perf_w) in the rows
# perf_y (height perf_h).  Every edge is on a whole pixel.
GRID_TILE = {
    16: dict(tile=(0, 0, 16, 16, 3.5), frame=(3, 5, 13, 11), stroke=1, fr=1.5,
             perf_y=(3, 12), perf_h=1, perf_x=(4, 7, 10), perf_w=2, check_w=1.6),
    20: dict(tile=(0, 0, 20, 20, 4.4), frame=(4, 6, 16, 14), stroke=1, fr=2,
             perf_y=(4, 15), perf_h=1, perf_x=(5, 9, 13), perf_w=2, check_w=1.8),
    24: dict(tile=(1, 1, 23, 23, 5.0), frame=(5, 7, 19, 17), stroke=1, fr=2.5,
             perf_y=(4, 18), perf_h=2, perf_x=(7, 11, 15), perf_w=2, check_w=2.2),
    32: dict(tile=(1, 1, 31, 31, 6.6), frame=(7, 10, 25, 22), stroke=2, fr=3,
             perf_y=(7, 23), perf_h=2, perf_x=(7, 11, 15, 19, 23), perf_w=2, check_w=2.6),
}
GRID_SMALL = {   # B51 title-bar icon: the symbol fills the square, no tile
    16: dict(tile=None, frame=(1, 4, 15, 12), stroke=1, fr=2,
             perf_y=(2, 13), perf_h=1, perf_x=(3, 7, 11), perf_w=2, check_w=1.7),
    20: dict(tile=None, frame=(1, 5, 19, 15), stroke=2, fr=2.5,
             perf_y=(2, 16), perf_h=2, perf_x=(3, 7, 11, 15), perf_w=2, check_w=2.1),
    24: dict(tile=None, frame=(1, 6, 23, 18), stroke=2, fr=3,
             perf_y=(3, 19), perf_h=2, perf_x=(3, 7, 11, 15, 19), perf_w=2, check_w=2.5),
    32: dict(tile=None, frame=(2, 8, 30, 24), stroke=2, fr=4,
             perf_y=(4, 25), perf_h=3, perf_x=(5, 10, 15, 20, 25), perf_w=2, check_w=3.2),
}


def _box(x0, y0, x1, y1):
    """Pixel box (x1/y1 exclusive) → Pillow box at SS resolution (inclusive)."""
    return (round(x0 * SS), round(y0 * SS), round(x1 * SS) - 1, round(y1 * SS) - 1)


def _tile(size, x0, y0, x1, y1, r):
    """Rounded tile with the navy gradient (top → bottom of the tile)."""
    big = size * SS
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle(_box(x0, y0, x1, y1), radius=round(r * SS), fill=255)
    grad = Image.new("RGBA", (big, big))
    gd = ImageDraw.Draw(grad)
    top, bottom = y0 * SS, y1 * SS
    for y in range(big):
        t = min(1.0, max(0.0, (y - top) / max(1, bottom - top)))
        c = tuple(round(a + (b - a) * t) for a, b in zip(NAVY_TOP, NAVY_BOTTOM))
        gd.line([(0, y), (big, y)], fill=c + (255,))
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    return out


def _check(draw, pts, width):
    w = max(1, round(width * SS))
    p = [(x * SS, y * SS) for x, y in pts]
    draw.line(p, fill=GREEN, width=w, joint="curve")
    for x, y in (p[0], p[-1]):                       # round caps
        draw.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=GREEN)


def render_master(size):
    """Sizes from 40 px up: the master drawing (viewBox 256) at this size."""
    s = size / 256.0
    img = _tile(size, 8 * s, 8 * s, 248 * s, 248 * s, 54 * s)
    d = ImageDraw.Draw(img)
    for y in (54, 186):
        for x in (66, 96, 126, 156, 186):
            d.rounded_rectangle(_box(x * s, y * s, (x + 16) * s, (y + 16) * s), radius=round(4 * s * SS), fill=BLUE)
    d.rounded_rectangle(_box(54 * s, 76 * s, 210 * s, 180 * s), radius=round(22 * s * SS),
                        outline=BLUE, width=round(12 * s * SS))
    _check(d, [(x * s, y * s) for x, y in ((98, 128), (120, 150), (162, 106))], 17 * s)
    return img.reduce(SS)


def render_grid(size, spec):
    """16–32 px: drawn on the pixel grid (whole-pixel edges)."""
    if spec["tile"]:
        img = _tile(size, *spec["tile"])
    else:
        img = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in spec["perf_y"]:
        for x in spec["perf_x"]:
            d.rectangle(_box(x, y, x + spec["perf_w"], y + spec["perf_h"]), fill=BLUE)
    fx0, fy0, fx1, fy1 = spec["frame"]
    d.rounded_rectangle(_box(fx0, fy0, fx1, fy1), radius=round(spec["fr"] * SS),
                        outline=BLUE, width=spec["stroke"] * SS)
    fw, fh = fx1 - fx0, fy1 - fy0
    _check(d, [(fx0 + rx * fw, fy0 + ry * fh) for rx, ry in _CHECK_REL], spec["check_w"])
    return img.reduce(SS)


def build_frames():
    tile = {n: (render_grid(n, GRID_TILE[n]) if n in GRID_TILE else render_master(n)) for n in ICO_SIZES}
    small = {n: render_grid(n, GRID_SMALL[n]) for n in SMALL_SIZES}
    return tile, small


def _save_ico(path, frames):
    sizes = sorted(frames)
    base = frames[sizes[-1]]
    others = [frames[n] for n in sizes[:-1]]
    tmp = path + ".tmp"
    base.save(tmp, format="ICO", sizes=[(n, n) for n in sizes], append_images=others)
    os.replace(tmp, path)


def verify_ico(path, sizes, tile=True):
    """Each size: present, transparent corners; the tile icon also has an opaque centre."""
    problems = []
    ico = Image.open(path)
    have = {s[0] for s in ico.info.get("sizes", set())}
    for n in sizes:
        if n not in have:
            problems.append(f"{os.path.basename(path)}: {n} px missing")
            continue
        ico.size = (n, n)
        im = ico.convert("RGBA")
        for c in ((0, 0), (n - 1, 0), (0, n - 1), (n - 1, n - 1)):
            if im.getpixel(c)[3] != 0:
                problems.append(f"{os.path.basename(path)} {n} px: corner {c} not transparent")
        if tile and im.getpixel((n // 2, n // 2))[3] != 255:
            problems.append(f"{os.path.basename(path)} {n} px: centre not opaque")
    return problems


def make_sheet(tile, small, out):
    """Comparison sheet: sizes on light / grey / dark, 4× zoom of the grid sizes,
    the small title-bar icon, and a taskbar row next to the sibling apps."""
    phy = os.path.dirname(os.path.dirname(APP_DIR))          # …\Downloads\Phyton
    siblings = [("MD Converter", os.path.join(phy, "MD Converter", "v.0.3.0", "assets", "icon-256.png")),
                ("RadioSave", os.path.join(phy, "RadioSave", "v.0.4.0", "assets", "icon-256.png")),
                ("TranscriptLab", os.path.join(phy, "TranscriptLab", "v.0.16.8", "assets", "app_icon_256.png"))]
    bgs = [(243, 243, 243), (128, 128, 128), (30, 30, 46)]
    W, row_h = 1100, 300
    sheet = Image.new("RGBA", (W, row_h * len(bgs) + 140), (255, 255, 255, 255))
    for i, bg in enumerate(bgs):
        y0 = i * row_h
        sheet.paste(Image.new("RGBA", (W, row_h), bg + (255,)), (0, y0))
        x = 20
        for n in (256, 48, 32, 16):
            sheet.alpha_composite(tile[n], (x, y0 + 20))
            x += n + 24
        for n in (32, 16):                                    # 4× nearest: shows the pixel grid
            z = tile[n].resize((n * 4, n * 4), Image.NEAREST)
            sheet.alpha_composite(z, (x, y0 + 20))
            x += n * 4 + 24
        for n in (32, 16):
            z = small[n].resize((n * 4, n * 4), Image.NEAREST)
            sheet.alpha_composite(z, (x, y0 + 160))
            sheet.alpha_composite(small[n], (x + n * 4 + 8, y0 + 160))
            x += n * 5 + 32
    # taskbar row (dark Windows 11 taskbar colour), 48 px icons
    ty = row_h * len(bgs)
    sheet.paste(Image.new("RGBA", (W, 140), (32, 32, 32, 255)), (0, ty))
    x = 30
    for name, p in siblings:
        if os.path.isfile(p):
            ic = Image.open(p).convert("RGBA").resize((48, 48), Image.LANCZOS)
            sheet.alpha_composite(ic, (x, ty + 46))
        x += 80
    sheet.alpha_composite(tile[48], (x, ty + 46))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)


def main():
    tile, small = build_frames()
    ico = os.path.join(APP_DIR, "MediaClinic.ico")
    ico_small = os.path.join(APP_DIR, "MediaClinic-small.ico")
    _save_ico(ico, tile)
    _save_ico(ico_small, small)
    render_master(1024).save(os.path.join(HERE, "icon_master_1024.png"))
    make_sheet(tile, small, os.path.join(APP_DIR, "plan_assets", "icon_B_sheet.png"))
    problems = verify_ico(ico, ICO_SIZES) + verify_ico(ico_small, SMALL_SIZES, tile=False)
    for p in problems:
        print("PROBLEM:", p)
    print(f"written: {ico}, {ico_small}" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
