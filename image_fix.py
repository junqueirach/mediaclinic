# =============================================================================
# image_fix.py
# Metadata & MediaClinic — fix image proportions and size (Pillow pipeline)
# Version: 0.19.2                                              ### NEW v0.19.2 F4a ###
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# Roadmap Part 7 (F4).  Posters / folder images (2:3) and fanart (16:9) with
# wrong proportions or a low resolution are fixed in two steps:
#   1. the proportions, at the image's own scale (blur fill, solid fill,
#      centre / smart crop, or a small stretch);
#   2. a LANCZOS resize to a size of the app's own quality tiers — by
#      default the tier nearest to the corrected size (F4.3a), never one
#      the upscaling limits mark ✕ (F4.3b).
# An optional upscaler (F4b, Real-ESRGAN) is passed in as a function.
#
# RULES: no tkinter, no file or disk access (the caller opens and saves the
# images, makes the backup and refreshes the row); Pillow only.
# =============================================================================

import math

from PIL import Image, ImageFilter, ImageOps, ImageStat

from settings_model import POSTER_QUALITY_TIERS, FANART_QUALITY_TIERS, UPSCALE_LIMITS

RATIO = {"poster": 2 / 3, "folder": 2 / 3, "fanart": 16 / 9}
STRETCH_MAX = 0.03                      # a deviation up to 3 % is simply stretched (invisible)
METHODS = ("blur", "crop_smart", "crop_center", "solid", "stretch")
METHOD_LABEL = {
    "blur":        "Blur fill (keeps the whole image)",
    "crop_smart":  "Smart crop (keeps the most detailed part)",
    "crop_center": "Centre crop",
    "solid":       "Solid fill (edge colour)",
    "stretch":     "Stretch (only for a small deviation)",
}
DEFAULT_METHOD = {"poster": "blur", "folder": "blur", "fanart": "crop_smart"}
JPEG_QUALITY = 92

MARK = {"ok": "✓", "warn": "⚠", "no": "✕"}
INFO_LINE = ("Upscaling cannot recover detail that is not in the original. Small enlargements are fine; "
             "large ones look soft (plain) or artificial (AI). For a much bigger image, use "
             "\"Find a better one online\".")


def tiers(kind):
    """[(label, w, h)] best → worst for the kind (the Health Rules tiers)."""
    t = FANART_QUALITY_TIERS if kind == "fanart" else POSTER_QUALITY_TIERS
    return [(lbl, w, h) for lbl, w, h, _px, _sz in t]


def deviation(w, h, kind):
    """Relative deviation of w/h from the kind's ratio (0.05 = 5 %)."""
    return abs((w / h) / RATIO[kind] - 1) if w and h else 0.0


def effective_method(w, h, kind, method):
    """A deviation up to STRETCH_MAX is always stretched; 'stretch' is only
    allowed up to that limit (otherwise the kind's default is used)."""
    if deviation(w, h, kind) <= STRETCH_MAX:
        return "stretch"
    if method == "stretch" or method not in METHODS:
        return DEFAULT_METHOD[kind]
    return method


def corrected_size(w, h, kind, method):
    """(w, h) after step 1 (proportions fixed at the image's own scale)."""
    r = RATIO[kind]
    m = effective_method(w, h, kind, method)
    too_wide = (w / h) > r
    if m == "stretch":
        return max(1, round(h * r)), h
    if m in ("blur", "solid"):                           # bands are added
        return (w, max(1, round(w / r))) if too_wide else (max(1, round(h * r)), h)
    return (max(1, round(h * r)), h) if too_wide else (w, max(1, round(w / r)))   # crops remove the excess


def mark_for(factor, ai=False):
    """'ok' / 'warn' / 'no' for a scale factor (target height / corrected height)."""
    if factor <= 1.0001:
        return "ok"
    rec, top = UPSCALE_LIMITS["ai" if ai else "plain"]
    if factor <= rec + 1e-9:
        return "ok"
    if factor <= top + 1e-9:
        return "warn"
    return "no"


def _mark_text(mark, ai):
    if mark == "ok":
        return "✓ recommended"
    if mark == "warn":
        return "⚠ check the preview — AI may invent detail, smooth text and faces" if ai \
            else "⚠ not recommended — soft without AI"
    return "✕ too far from the original"


def size_options(kind, cw, ch, ai=False):
    """Every target size for an image whose corrected size is cw×ch:
    [{"key", "label", "w", "h", "factor", "mark"}] (tiers best → worst, then
    "Keep current size"), and the index of the default: the tier nearest to
    cw×ch (smallest |ln factor|) that is not ✕ / ⚠ (F4.3a)."""
    opts = []
    for lbl, w, h in tiers(kind):
        f = h / ch
        mk = mark_for(f, ai)
        opts.append({"key": lbl, "w": w, "h": h, "factor": f, "mark": mk,
                     "label": f"{lbl} {w}×{h} (×{f:.2f}) {_mark_text(mk, ai)}"})
    opts.append({"key": "keep", "w": cw, "h": ch, "factor": 1.0, "mark": "ok",
                 "label": f"Keep current size {cw}×{ch} (fix proportions only)"})
    good = [i for i, o in enumerate(opts[:-1]) if o["mark"] == "ok"]
    if good:
        default = min(good, key=lambda i: abs(math.log(opts[i]["factor"])))
    else:
        default = len(opts) - 1
    return opts, default


def min_tier_note(kind, ch, min_label, ai_available=False):
    """The line shown when the Health Rules minimum tier needs more than the
    recommended plain enlargement (F4.3b), else ''."""
    t = {lbl: h for lbl, _w, h in tiers(kind)}
    if min_label not in t or not ch:
        return ""
    f = t[min_label] / ch
    if mark_for(f, False) == "ok":
        return ""
    ai_mark = mark_for(f, True)
    ai_txt = {"ok": "✓ with AI upscale", "warn": "⚠ even with AI upscale", "no": "✕ even with AI upscale"}[ai_mark]
    plain_txt = {"warn": "⚠ without it", "no": "✕ without it"}[mark_for(f, False)]
    return (f"Reaching {min_label} needs ×{f:.1f}. {ai_txt}, {plain_txt}. "
            "A better online image is recommended.")


# ── Step 1: proportions ───────────────────────────────────────────────────────

def _rgb(img):
    if img.mode in ("RGB",):
        return img
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (0, 0, 0))
        im = img.convert("RGBA")
        bg.paste(im, mask=im.split()[-1])
        return bg
    return img.convert("RGB")


def _edge_colour(img, too_wide):
    """Average colour of the edges the bands will touch."""
    w, h = img.size
    b = max(1, min(w, h) // 50)
    boxes = [(0, 0, w, b), (0, h - b, w, h)] if too_wide else [(0, 0, b, h), (w - b, 0, w, h)]
    means = [ImageStat.Stat(img.crop(bx)).mean for bx in boxes]
    return tuple(int(sum(m[i] for m in means) / len(means)) for i in range(3))


def _smart_offset(img, cw, ch):
    """Left/top of the crop window (cw×ch) with the most edge detail."""
    w, h = img.size
    scale = 256 / max(w, h) if max(w, h) > 256 else 1.0
    small = img.convert("L").resize((max(1, round(w * scale)), max(1, round(h * scale))))
    edges = small.filter(ImageFilter.FIND_EDGES)
    sw, sh = edges.size
    if cw < w:                                          # horizontal window
        win = max(1, round(cw * scale)); span = sw - win
        best = max(range(0, span + 1, max(1, span // 32 or 1)),
                   key=lambda x: ImageStat.Stat(edges.crop((x, 0, x + win, sh))).sum[0], default=0)
        return round(best / scale), 0
    win = max(1, round(ch * scale)); span = sh - win
    best = max(range(0, span + 1, max(1, span // 32 or 1)),
               key=lambda y: ImageStat.Stat(edges.crop((0, y, sw, y + win))).sum[0], default=0)
    return 0, round(best / scale)


def fix_ratio(img, kind, method):
    """Step 1: an image with the kind's proportions at the image's own scale."""
    img = _rgb(img)
    w, h = img.size
    m = effective_method(w, h, kind, method)
    cw, ch = corrected_size(w, h, kind, m)
    if (cw, ch) == (w, h):
        return img.copy()
    if m == "stretch":
        return img.resize((cw, ch), Image.LANCZOS)
    too_wide = (w / h) > RATIO[kind]
    if m in ("crop_center", "crop_smart"):
        if m == "crop_smart":
            x, y = _smart_offset(img, cw, ch)
        else:
            x, y = (w - cw) // 2, (h - ch) // 2
        x = min(max(0, x), w - cw); y = min(max(0, y), h - ch)
        return img.crop((x, y, x + cw, y + ch))
    if m == "solid":
        canvas = Image.new("RGB", (cw, ch), _edge_colour(img, too_wide))
    else:                                               # blur fill
        bg = ImageOps.fit(img, (cw, ch), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=max(cw, ch) / 40))
        canvas = Image.blend(bg, Image.new("RGB", (cw, ch), (0, 0, 0)), 0.25)
    canvas.paste(img, ((cw - w) // 2, (ch - h) // 2))
    return canvas


# ── Steps 2–4 ────────────────────────────────────────────────────────────────

def render(img, kind, method, target=None, upscale=None):
    """The fixed image: proportions (step 1), then — when the target is larger
    and *upscale* (original → enlarged original) is given — the original is
    upscaled and step 1 redone on it (step 3), then a LANCZOS resize to the
    exact target (step 4).  target = (w, h) or None (keep the corrected size)."""
    out = fix_ratio(img, kind, method)
    if target and upscale is not None and target[1] > out.size[1]:
        big = upscale(img)
        if big is not None:
            out = fix_ratio(big, kind, method)
    if target and tuple(target) != out.size:
        out = out.resize(tuple(target), Image.LANCZOS)
    return out


def batch_choice(kind, w, h, method, min_label, ai=False):
    """Batch mode (Tools → All Movies): (target (w, h) | None, note).  Only ✓
    targets are used; the target is the default tier, raised to the Health
    Rules minimum when that is still ✓.  None + note = skipped."""
    cw, ch = corrected_size(w, h, kind, method)
    opts, d = size_options(kind, cw, ch, ai)
    t = {o["key"]: o for o in opts}
    choice = opts[d]
    order = [lbl for lbl, _w, _h in tiers(kind)]
    if min_label in t and choice["key"] != "keep" and order.index(choice["key"]) > order.index(min_label):
        need = t[min_label]
        if need["mark"] == "ok":
            choice = need
        else:
            return None, f"skipped — needs ×{need['factor']:.1f}; fix it individually or find a better image"
    elif choice["key"] == "keep" and min_label in t and ch < t[min_label]["h"] * 0.95:
        need = t[min_label]
        if need["mark"] != "ok":
            return None, f"skipped — needs ×{need['factor']:.1f}; fix it individually or find a better image"
        choice = need
    return (choice["w"], choice["h"]), f"{METHOD_LABEL[effective_method(w, h, kind, method)].split(' (')[0]} → {choice['w']}×{choice['h']}"
