# =============================================================================
# html_export.py
# MediaClinic — the HTML export (v0.20.1 TF7): one self-contained page with layouts and themes
# Author:  Luiz Junqueira & Claude AI
#
# One .html file that opens offline in any browser (PC, phone, TV): layouts Table + posters / Poster wall / Shelves /
# Catalogue / Checklist, themes Classic / Home Theater / Studio / Aurora / Glass / Cinema Gold, dark and light, search,
# filters, a detail view, a random pick, a stats line, media flags and a print stylesheet. The page's words are in the
# interface language.
#
# RULES (TF7, RV8–RV11)
#   • No tkinter. Reads the scan rows, the NFO / movie.xml text and the images; writes the page (and, in the "images
#     folder" mode, the images next to it).
#   • Every movie value goes into ONE JSON block (</script> cannot break out: <, >, & are \u-escaped); the page script
#     builds the HTML with esc() on every value. No script, style or URL is taken from movie data except image links
#     that are https (online mode) and the IMDb / TMDB IDs, which are checked by pattern.
#   • No external request when the page opens — no web fonts, no CDN — except in the "online links" image mode.
#   • File paths and folder names are not offered by default (the page may be shared): PRIVATE_FIELDS.
#   • Series-ready (SR2): a record is built from a row by movie_record(); a series export adds its own record builder
#     and reuses build_page().
# =============================================================================

import base64
import html
import io
import json
import os
import re
import shutil
import zlib
from urllib.parse import quote

import mc_i18n as _i18n

LAYOUTS = ("table", "wall", "shelves", "catalogue", "checklist")
THEMES = ("classic", "home", "studio", "aurora", "glass", "gold")
IMAGE_MODES = ("embed", "folder", "online", "none")
PRIVATE_FIELDS = ("path", "folder_name", "library")     # unticked for HTML and marked "private" in the Export window
NUM_KEYS = ("year", "rating", "votes", "backdrops")
POSTER_WIDTH = 300                                      # RV9: one embedded poster size (JPEG q 80, about 20–35 KB)
FANART_WIDTH = 1280                                     # images folder mode only (RV9: no embedded fanart)
EMBED_KB_PER_POSTER = 30
DEFAULTS = {"layout": "table", "theme": "classic", "title": "", "accent": "", "images": "embed",
            "plot": True, "cast": True, "ratings": True, "flags": True}
_ACCENT = re.compile(r"#[0-9a-fA-F]{6}")
_IMDB = re.compile(r"tt\d{5,10}")
_TMDB = re.compile(r"\d{1,9}")
_HTTPS = re.compile(r"https://[^\s\"'<>\\]+")


def options(prefs=None) -> dict:
    """The page options from the remembered choices; anything unknown falls back to DEFAULTS."""
    p = dict(prefs or {})
    o = dict(DEFAULTS)
    if p.get("layout") in LAYOUTS:
        o["layout"] = p["layout"]
    if p.get("theme") in THEMES:
        o["theme"] = p["theme"]
    if p.get("images") in IMAGE_MODES:
        o["images"] = p["images"]
    o["title"] = " ".join(str(p.get("title") or "").split())[:120]
    o["accent"] = p["accent"] if _ACCENT.fullmatch(str(p.get("accent") or "")) else ""
    for k in ("plot", "cast", "ratings", "flags"):
        if k in p:
            o[k] = bool(p[k])
    return o


def estimate_bytes(n_posters: int, mode: str) -> int:
    """About how big the .html file gets (embedded posters dominate; the text is about 2 KB per movie)."""
    return n_posters * (EMBED_KB_PER_POSTER * 1024 * 4 // 3 if mode == "embed" else 0) + n_posters * 2048   # base64 = 4/3


# ── what the files say (NFO / movie.xml): runtime, director, cast, video codec, HDR, online image links ──────────
def _all(tag, text):
    return [" ".join(html.unescape(m).split()) for m in re.findall(rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}\s*>", text, re.I | re.S)]


def _clean(v):
    v = (v or "").strip()
    if v.startswith("<![CDATA[") and v.endswith("]]>"):
        v = v[9:-3].strip()
    return v


_VCODEC = {"hevc": "HEVC", "h265": "HEVC", "x265": "HEVC", "h264": "H.264", "avc": "H.264", "avc1": "H.264",
           "x264": "H.264", "av1": "AV1", "vp9": "VP9", "mpeg4": "MPEG-4", "xvid": "XviD", "divx": "DivX",
           "dx50": "DivX", "mpeg2video": "MPEG-2", "mpeg2": "MPEG-2", "vc1": "VC-1", "wvc1": "VC-1"}
_HDR = {"hdr10": "HDR10", "hdr10plus": "HDR10+", "hdr10+": "HDR10+", "dolbyvision": "Dolby Vision",
        "dolby vision": "Dolby Vision", "dv": "Dolby Vision", "hlg": "HLG"}
_ACODEC = {"EAC3": "E-AC3", "TRUEHD": "TrueHD", "DTS": "DTS", "AC3": "AC3", "AAC": "AAC", "FLAC": "FLAC",
           "OPUS": "Opus", "MP3": "MP3", "MP2": "MP2", "VORBIS": "Vorbis", "PCM_S16LE": "PCM", "PCM_S24LE": "PCM"}


def nfo_facts(text: str) -> dict:
    """Kodi NFO → {runtime, directors, cast, vcodec, hdr, poster_url, fanart_url, tagline} ('' / [] when absent)."""
    t = text or ""
    out = {"runtime": 0, "directors": [], "cast": [], "vcodec": "", "hdr": "", "poster_url": "", "fanart_url": "",
           "tagline": ""}
    m = re.search(r"<runtime>\s*(\d+)", t, re.I)
    out["runtime"] = int(m.group(1)) if m else 0
    out["directors"] = [d for d in (_clean(x) for x in _all("director", t)) if d][:3]
    for block in re.findall(r"<actor\b[^>]*>(.*?)</actor\s*>", t, re.I | re.S):
        n = _all("name", block)
        if n and _clean(n[0]):
            out["cast"].append(_clean(n[0]))
    out["cast"] = out["cast"][:12]
    sd = re.search(r"<streamdetails>(.*?)</streamdetails>", t, re.I | re.S)
    if sd:
        v = re.search(r"<video>(.*?)</video>", sd.group(1), re.I | re.S)
        if v:
            c = _all("codec", v.group(1))
            out["vcodec"] = _VCODEC.get((c[0] if c else "").lower(), (c[0] if c else "").upper())
            h = _all("hdrtype", v.group(1))
            out["hdr"] = _HDR.get((h[0] if h else "").lower(), "")
    for th in re.findall(r"<thumb\b([^>]*)>(.*?)</thumb\s*>", t, re.I | re.S):
        attrs, url = th[0].lower(), html.unescape(th[1]).strip()
        if 'aspect="poster"' in attrs and not out["poster_url"] and _HTTPS.fullmatch(url):
            out["poster_url"] = url
    fa = re.search(r"<fanart\b[^>]*>(.*?)</fanart\s*>", t, re.I | re.S)
    if fa:
        for url in _all("thumb", fa.group(1)):
            if _HTTPS.fullmatch(url):
                out["fanart_url"] = url
                break
    tg = _all("tagline", t)
    out["tagline"] = _clean(tg[0]) if tg else ""
    return out


def xml_facts(text: str) -> dict:
    """Emby / Jellyfin movie.xml → the same keys as nfo_facts (no codec, HDR or links there)."""
    t = text or ""
    out = {"runtime": 0, "directors": [], "cast": [], "vcodec": "", "hdr": "", "poster_url": "", "fanart_url": "",
           "tagline": ""}
    m = re.search(r"<RunningTime>\s*(\d+)", t, re.I)
    out["runtime"] = int(m.group(1)) if m else 0
    out["directors"] = [d for d in (_clean(x) for x in _all("Director", t)) if d][:3]
    for block in re.findall(r"<Person\b[^>]*>(.*?)</Person\s*>", t, re.I | re.S):
        ty = _all("Type", block)
        if ty and ty[0].lower() == "actor":
            n = _all("Name", block)
            if n and _clean(n[0]):
                out["cast"].append(_clean(n[0]))
    out["cast"] = out["cast"][:12]
    tg = _all("Tagline", t)
    out["tagline"] = _clean(tg[0]) if tg else ""
    return out


def audio_flag(tracks) -> str:
    """The best audio track as a badge text: 'DTS 5.1', 'TrueHD 7.1' ('' without probe data)."""
    best, best_ch = None, -1.0
    for tr in tracks or ():
        try:
            ch = float(str(tr.get("channels") or "0").split()[0])
        except ValueError:
            ch = 0.0
        if ch > best_ch:
            best, best_ch = tr, ch
    if not best:
        return ""
    codec = str(best.get("codec") or "").upper()
    name = _ACODEC.get(codec, codec.replace("_", " ").title() if codec else "")
    return " ".join(x for x in (name, str(best.get("channels") or "")) if x)


def _langs(items, key):
    out = []
    for it in items or ():
        v = str(it.get(key) or "").strip().upper()
        if v and v not in ("UND", "UNDEFINED", "ZXX", "MIS", "MUL") and v not in out:
            out.append(v)
    return out


# ── images ───────────────────────────────────────────────────────────────────
def _jpeg_bytes(path, width):
    """A JPEG of *path* at most *width* wide (q 80), or None."""
    if not path or not os.path.isfile(path):
        return None
    try:
        from PIL import Image
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((width, width * 3))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=80, optimize=True)
        return buf.getvalue()
    except Exception:
        return None



IMAGES_MARK = ".mediaclinic_export"                              # v0.20.2 PA9: written into every images folder
_OUR_IMAGE_RE = re.compile(r"^\d+f?\.(?:jpe?g|png|webp)$", re.I)


def images_folder_is_ours(folder):                               ### NEW v0.20.2 PA9 (audit) ###
    """True when *folder* holds only what an earlier export wrote (its mark, or only N.jpg / Nf.jpg): only such a
    folder is replaced.  A folder of the user's own with that name is never deleted."""
    try:
        names = os.listdir(folder)
    except OSError:
        return False
    if IMAGES_MARK in names:
        return True
    return all(_OUR_IMAGE_RE.match(n) and os.path.isfile(os.path.join(folder, n)) for n in names)


def _image_refs(row, i, mode, facts, img_dir, img_rel):
    """(poster src, fanart src) for one movie in *mode*: a data: URI, a relative path, an https link or ''."""
    if mode == "none":
        return "", ""
    if mode == "online":
        return facts.get("poster_url", ""), facts.get("fanart_url", "")
    p = row.get("poster_path") if row.get("poster_exists") else None
    if not p and row.get("folder_exists"):
        p = row.get("folder_path")
    if mode == "embed":
        b = _jpeg_bytes(p, POSTER_WIDTH)
        return ("data:image/jpeg;base64," + base64.b64encode(b).decode("ascii")) if b else "", ""
    poster = fanart = ""
    b = _jpeg_bytes(p, POSTER_WIDTH)
    if b:
        with open(os.path.join(img_dir, f"{i}.jpg"), "wb") as f:
            f.write(b)
        poster = f"{quote(img_rel)}/{i}.jpg"
    fb = _jpeg_bytes(row.get("fanart_path") if row.get("fanart_exists") else None, FANART_WIDTH)
    if fb:
        with open(os.path.join(img_dir, f"{i}f.jpg"), "wb") as f:
            f.write(fb)
        fanart = f"{quote(img_rel)}/{i}f.jpg"
    return poster, fanart


# ── one record per movie ─────────────────────────────────────────────────────
def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def movie_record(row, cells, opts, facts, poster="", fanart="", plot="") -> dict:
    """The page's data for one movie (short keys keep the file small). *cells* = the chosen columns' texts."""
    y = row.get("movie_year")
    rec = {"t": row.get("movie_name") or row.get("subfolder", ""), "y": int(y) if str(y or "").isdigit() else None,
           "g": [g for g in (row.get("genres") or []) if g] or
                ([] if row.get("genre_display", "—") in ("—", "", None) else [x.strip() for x in str(row["genre_display"]).split(",") if x.strip()]),
           "rt": facts.get("runtime") or 0,
           "col": (row.get("coll_nfo") or {}).get("name") or "",
           "c": cells}
    imdb, tmdb = str(row.get("source_imdb_val") or "").strip(), str(row.get("source_tmdb_val") or "").strip()
    if _IMDB.fullmatch(imdb):
        rec["imdb"] = imdb
    if _TMDB.fullmatch(tmdb):
        rec["tmdb"] = tmdb
    if opts.get("ratings"):
        r = _num(row.get("rating_str"))
        if r is not None:
            rec["r"] = round(r, 1)
        if row.get("votes_int"):
            rec["v"] = int(row["votes_int"])
    if opts.get("plot") and plot:
        rec["p"] = plot
    if opts.get("cast"):
        rec["d"] = facts.get("directors") or []
        rec["a"] = facts.get("cast") or []
    vq = str(row.get("video_quality") or "")
    rec["res"] = "" if vq in ("—", "-") else vq
    rec["al"] = _langs(row.get("audio_tracks"), "language")
    if opts.get("flags"):
        rec["vc"] = facts.get("vcodec") or ""
        rec["hdr"] = facts.get("hdr") or ""
        rec["au"] = audio_flag(row.get("audio_tracks"))
        rec["sl"] = _langs(list(row.get("subs_internal") or []) + list(row.get("subs_external") or []), "lang")
    if poster:
        rec["pi"] = poster
    if fanart:
        rec["fi"] = fanart
    return rec


def _json_for_script(obj) -> str:
    """JSON that is safe inside <script type="application/json">: no '</script>', no HTML comment, no U+2028."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return (s.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


UI_KEYS = ("search", "any_genre", "any_decade", "any_coll", "any_res", "any_audio", "any_rating", "rating_min",
           "random", "layout", "theme", "l_table", "l_wall", "l_shelves", "l_catalogue", "l_checklist",
           "th_classic", "th_home", "th_studio", "th_aurora", "th_glass", "th_gold", "light_dark", "flags",
           "posters", "ps_off", "ps_s", "ps_m", "ps_l", "columns", "shelf_by", "by_coll", "by_genre", "by_decade",
           "other", "stats", "hours", "in4k", "top", "director", "with", "min", "close", "print", "none", "imdb",
           "tmdb", "trailer", "collection", "decade")


def ui_labels() -> dict:
    return {k: _i18n.t("tf7.ui." + k) for k in UI_KEYS}


def page_chunks(records, headers, field_keys, opts, when="", app_version=""):
    """The page as an iterator of text pieces: the head, one piece per movie record, the tail. Writing it piece by piece
    keeps the memory small (6,000 embedded posters are about 250 MB of page). *records* may be an iterator."""
    lang = {"pt_BR": "pt-BR"}.get(_i18n.current(), _i18n.current())
    title = opts.get("title") or _i18n.t("ex.html.title")
    made = _i18n.t("ex.html.made", when=when, version=app_version) if when else ""
    # the viewer's choices (layout, theme, hidden columns) are remembered per export: another export, or the same
    # file exported again, opens with what the Export window chose
    page_id = format(zlib.crc32("\x1f".join([made, title, opts["layout"], opts["theme"], *field_keys]).encode("utf-8")), "08x")
    rest = {"h": headers, "k": list(field_keys), "num": [k in NUM_KEYS for k in field_keys],
            "L": ui_labels(), "o": {"layout": opts["layout"], "theme": opts["theme"], "flags": bool(opts.get("flags"))},
            "made": made, "lang": lang, "id": page_id}
    style = f' style="--accent:{opts["accent"]}"' if opts.get("accent") else ""
    parts = {"LANG": html.escape(lang, quote=True), "TITLE": html.escape(title, quote=True),
             "BODY_ATTR": f'class="t-{opts["theme"]}"{style}', "CSS": _CSS, "JS": _JS, "DATA": "\x00"}
    head, tail = re.sub(r"%%([A-Z_]+)%%", lambda m: parts[m.group(1)], _PAGE).split("\x00")   # one pass
    yield head + '{"m":['
    first = True
    for rec in records:
        yield ("" if first else ",") + _json_for_script(rec)
        first = False
    yield "]," + _json_for_script(rest)[1:] + tail


def build_page(records, headers, field_keys, opts, when="", app_version="") -> str:
    """The whole page as one text (pure). *headers* / *field_keys* = the Table layout's columns."""
    return "".join(page_chunks(records, headers, field_keys, opts, when, app_version))


def write_export(rows, field_keys, path, prefs=None, progress=None, cancelled=None, when=None, app_version="") -> int:
    """Write the page for *rows* to *path* (and, in the images folder mode, '<name>_images' next to it).
    progress(i) after each movie; cancelled() → True stops with RuntimeError. Nothing is half done: the page and the
    images are written under temporary names and take their places only at the end (an earlier export of the same
    name stays whole when this one is cancelled or fails; its images folder is replaced, never mixed)."""
    import export_list as _ex                                  # lazy: export_list imports this module
    opts = options(prefs)
    keys = [k for k in field_keys if k in _ex._FIELD_MAP] or ["movie_name"]
    if "movie_name" not in keys:                               # every layout needs the title; the table's phone rows too
        keys = ["movie_name"] + keys
    headers, data = _ex.build_table(rows, keys)
    img_dir = img_rel = img_tmp = None
    if opts["images"] == "folder":
        img_rel = os.path.splitext(os.path.basename(path))[0] + "_images"
        img_dir = os.path.join(os.path.dirname(os.path.abspath(path)), img_rel)
        img_tmp = img_dir + ".mctmp"
        if os.path.exists(img_dir) and not images_folder_is_ours(img_dir):   ### NEW v0.20.2 PA9 (audit) ###
            raise RuntimeError(_i18n.t("ex.html.images_taken", folder=img_dir))
        shutil.rmtree(img_tmp, ignore_errors=True)
        os.makedirs(img_tmp)
        open(os.path.join(img_tmp, IMAGES_MARK), "w", encoding="utf-8").write("MediaClinic HTML export images\n")
    with_health = "health" in keys

    def records():
        for i, (r, cells) in enumerate(zip(rows, data)):
            if cancelled and cancelled():
                raise RuntimeError(_i18n.t("ex.html.cancelled"))
            if r.get("nfo_exists"):
                facts = nfo_facts(_ex._file_text(r.get("nfo_path")))
            elif r.get("xml_exists"):
                facts = xml_facts(_ex._file_text(r.get("xml_path")))
            else:
                facts = nfo_facts("")
            plot = _ex._first_tag(r, ["plot"], ["Overview", "Plot", "Description"]) if opts.get("plot") else ""
            poster, fanart = _image_refs(r, i, opts["images"], facts, img_tmp, img_rel)
            rec = movie_record(r, cells, opts, facts, poster, fanart, plot)
            if with_health and r.get("health_status") in ("ok", "warning", "error"):
                rec["hs"] = r["health_status"]
            yield rec
            if progress:
                progress(i + 1)
    tmp = path + ".mctmp"
    _ex._TEXT_CACHE.clear()
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            for chunk in page_chunks(records(), headers, keys, opts, when or "", app_version):
                f.write(chunk)
        if img_tmp:
            shutil.rmtree(img_dir, ignore_errors=True)
            os.replace(img_tmp, img_dir)
        os.replace(tmp, path)
    except BaseException:
        if img_tmp:
            shutil.rmtree(img_tmp, ignore_errors=True)
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    finally:
        _ex._TEXT_CACHE.clear()
    return len(rows)


# ── the page ─────────────────────────────────────────────────────────────────
_CSS = r"""
:root{--bg:#11131a;--panel:#1b1e28;--text:#e8e8ee;--dim:#9aa0b0;--accent:#6aa9ff;--line:#2a2e3b;--card:#1f2330;--chip:#2a3042;
 --radius:10px;--font:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
body.light{--bg:#f4f5f8;--panel:#fff;--text:#1d2030;--dim:#5e6474;--line:#dde1ea;--card:#fff;--chip:#eceff5;--accent:#2563c9}
body.t-home{--bg:#0b1a2e;--panel:#10233d;--card:#132a49;--accent:#4fb3ff;--chip:#1b3a62;--line:#1d3557}
body.t-studio{--bg:#1c1d1f;--panel:#252628;--card:#2c2d30;--accent:#52b54b;--chip:#36383b;--radius:14px}
body.t-aurora{--bg:#101020;--panel:#17172e;--card:#1c1c38;--accent:#9b6bff;--chip:#29294d;--line:#2c2c52}
body.t-glass{--bg:#0e1116;--panel:rgba(255,255,255,.07);--card:rgba(255,255,255,.08);--accent:#ffffff;--chip:rgba(255,255,255,.12);--radius:18px;--line:rgba(255,255,255,.12)}
body.t-gold{--bg:#090909;--panel:#141414;--card:#181818;--accent:#f5b400;--chip:#262626;--line:#2a2a2a}
body.light.t-home{--bg:#e9f1fb;--panel:#fff;--card:#fff;--chip:#d7e6f8;--line:#c9dbf0;--accent:#1f6fb8}
body.light.t-studio{--bg:#eef3ee;--panel:#fff;--card:#fff;--chip:#dcebdb;--line:#d3e2d2;--accent:#2f8a29}
body.light.t-aurora{--bg:#f1eefc;--panel:#fff;--card:#fff;--chip:#e3dcfb;--line:#ddd5f7;--accent:#6b3fe0}
body.light.t-glass{--bg:#e9edf2;--panel:rgba(255,255,255,.75);--card:rgba(255,255,255,.85);--accent:#222;--chip:rgba(0,0,0,.06);--line:rgba(0,0,0,.1)}
body.light.t-gold{--bg:#faf6ea;--panel:#fff;--card:#fff;--chip:#f3e6bd;--line:#eadcb0;--accent:#a57800}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.4 var(--font)}
body.t-aurora:not(.light){background:linear-gradient(160deg,#101020,#181036 60%,#0f1830) fixed}
body.t-glass:not(.light){background:radial-gradient(1200px 600px at 20% -10%,#3a4a6a,transparent),radial-gradient(900px 500px at 110% 10%,#5a3a5a,transparent),var(--bg) fixed}
header{position:sticky;top:0;z-index:5;background:var(--panel);border-bottom:1px solid var(--line);padding:10px 16px;backdrop-filter:blur(12px)}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
h1{font-size:20px;margin:0 12px 0 0}
body.t-gold h1,body.t-gold h3{text-transform:uppercase;letter-spacing:.06em}
.stats,.dim{color:var(--dim);font-size:13px}
input,select,button{font:inherit;font-size:14px;color:var(--text);background:var(--chip);border:1px solid var(--line);border-radius:8px;padding:5px 9px;max-width:100%}
button{cursor:pointer}
button.on{background:var(--accent);color:#000;border-color:var(--accent)}
body.light button.on{color:#fff}
main{padding:16px}
.pz{position:relative;width:100%;aspect-ratio:2/3;border-radius:calc(var(--radius) - 4px);overflow:hidden;background:var(--chip);display:flex;align-items:center;justify-content:center;color:var(--dim);font-weight:700}
.pz img{width:100%;height:100%;object-fit:cover;display:block}
.flags{display:flex;gap:4px;flex-wrap:wrap;margin-top:4px}
.flag{font-size:10px;font-weight:700;padding:1px 5px;border-radius:4px;background:var(--chip);color:var(--text);border:1px solid var(--line);white-space:nowrap}
body.noflags .flags{display:none}
table{width:100%;border-collapse:collapse;background:var(--card)}   /* no overflow:hidden: it would hold the sticky headings */
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
th{position:sticky;top:var(--hh,100px);background:var(--panel);cursor:pointer;font-size:13px;color:var(--dim);user-select:none;white-space:nowrap}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.h-ok{color:#3fa34d}.h-warning{color:#c98a00}.h-error{color:#d64545}td a{color:var(--accent)}
td.p{width:1%}td.p .pz{width:var(--pw,44px)}
body.ps-off td.p,body.ps-off th.p{display:none}
body.ps-m{--pw:80px}body.ps-l{--pw:130px}
tbody tr{cursor:pointer}tbody tr:hover{background:var(--chip)}
.mob{display:none;color:var(--dim);font-size:12px}
#pv{position:fixed;display:none;width:220px;z-index:8;pointer-events:none;box-shadow:0 10px 30px #000a;border-radius:8px;overflow:hidden}
#pv img{width:100%;display:block}
.wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px}
body.t-gold .wall{grid-template-columns:repeat(auto-fill,minmax(180px,1fr))}
.tile{background:var(--card);border-radius:var(--radius);padding:6px;cursor:pointer;transition:transform .15s;position:relative}
.tile:hover{transform:translateY(-3px)}
body.t-aurora .tile:hover,body.t-glass .tile:hover{box-shadow:0 0 22px color-mix(in srgb,var(--accent) 45%,transparent)}
body.t-glass .tile .pz{box-shadow:0 8px 24px #0007}
.tile .t{font-size:13px;margin-top:6px;font-weight:600}.tile .s{font-size:12px;color:var(--dim)}
.tile .ov{position:absolute;inset:6px 6px auto 6px;aspect-ratio:2/3;border-radius:calc(var(--radius) - 4px);background:linear-gradient(0deg,#000d,transparent 55%);opacity:0;transition:opacity .15s;display:flex;flex-direction:column;justify-content:flex-end;padding:8px;color:#fff;font-size:13px}
.tile:hover .ov{opacity:1}
.shelf h3{margin:18px 0 8px;font-size:16px}
.strip{display:flex;gap:12px;overflow-x:auto;padding-bottom:6px;scroll-snap-type:x proximity}.strip .tile{min-width:140px;max-width:140px;scroll-snap-align:start}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}
.card{display:flex;gap:12px;background:var(--card);border-radius:var(--radius);padding:10px;cursor:pointer}
.card .pz{width:100px;min-width:100px}
.card h4{margin:0 0 4px;font-size:16px}.card p{margin:4px 0;font-size:13px;color:var(--dim)}
.check{columns:2;column-gap:28px;background:var(--card);padding:14px;border-radius:var(--radius)}
.check label{display:block;break-inside:avoid;padding:2px 0;font-size:14px}
#none{display:none;color:var(--dim);padding:20px 0}
#colsbox{position:absolute;z-index:7;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 12px;display:none;max-height:60vh;overflow:auto}
#colsbox label{display:block;font-size:13px;padding:2px 0;white-space:nowrap}
#detail{position:fixed;inset:0;background:rgba(0,0,0,.65);display:none;align-items:center;justify-content:center;z-index:9;padding:16px}
#detail .box{max-width:820px;width:100%;max-height:92vh;overflow:auto;border-radius:var(--radius);background:var(--panel);position:relative}
#detail .bg{height:200px;position:relative;overflow:hidden;background:var(--chip)}
#detail .bg .im{position:absolute;inset:-20px;background-size:cover;background-position:center}
#detail .bg .im.blur{filter:blur(18px) brightness(.7)}
#detail .bg .sh{position:absolute;inset:0;background:linear-gradient(0deg,var(--panel),transparent 70%)}
#detail .bg h2{position:absolute;left:16px;right:60px;bottom:6px;margin:0;font-size:26px;color:#fff;text-shadow:0 2px 8px #000}
body.light #detail .bg h2{color:var(--text);text-shadow:none}
#detail .in{display:flex;gap:16px;padding:0 16px 16px}#detail .in .pz{width:150px;min-width:150px;margin-top:-70px;box-shadow:0 6px 20px #0008}
#detail .x{position:absolute;z-index:2;right:10px;top:8px;font-size:22px;background:#0006;border:none;color:#fff;border-radius:50%;width:36px;height:36px;padding:0}
#detail a{color:var(--accent)}
#detail p{margin:6px 0}
footer{color:var(--dim);font-size:12px;padding:8px 16px 24px}
@media (max-width:700px){
 header{position:static}th{top:0}
 .check{columns:1}.cards{grid-template-columns:1fr}
 table thead{display:none}table,tbody,tr{display:block}tr{display:flex;gap:10px;align-items:flex-start;padding:6px 8px;border-bottom:1px solid var(--line)}
 td{border:none;padding:0;min-width:0}td.x{display:none}td.p{width:auto;flex:0 0 auto}td.p .pz{width:56px}.mob{display:block}
 input,select,button{font-size:13px;padding:4px 7px}#q{flex:1 1 100%}header{padding:8px 10px}main{padding:10px}
 #detail .in{flex-direction:column}#detail .in .pz{margin-top:8px;width:120px;min-width:120px}
 .wall{grid-template-columns:repeat(auto-fill,minmax(105px,1fr));gap:10px}
}
@media print{
 header .ctl,#detail,#pv,#colsbox,footer .noprint{display:none!important}
 header{position:static;border:none;background:none}
 body{background:#fff!important;color:#000;--text:#000;--dim:#444;--card:#fff;--panel:#fff;--line:#ccc;--chip:#eee}
 th{position:static}.tile,.card,table{background:#fff;break-inside:avoid}tr{break-inside:avoid}
 .strip{flex-wrap:wrap;overflow:visible}.tile:hover{transform:none}
 td.p .pz{width:36px}
}
"""

_JS = r"""
(function(){
"use strict";
var D=JSON.parse(document.getElementById("data").textContent),M=D.m,L=D.L;
function $(s){return document.querySelector(s)}
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function fmt(t,o){return String(t).replace(/\{(\w+)\}/g,function(_,k){return o[k]==null?"":o[k]})}
function num(n){try{return Number(n).toLocaleString(D.lang)}catch(e){return String(n)}}
var SK="mcx."+D.id+".";
var store={get:function(k){try{return localStorage.getItem(SK+k)}catch(e){return null}},
 set:function(k,v){try{localStorage.setItem(SK+k,v)}catch(e){}}};
var COL;try{COL=new Intl.Collator(D.lang,{numeric:true})}catch(e){COL={compare:function(a,b){return a<b?-1:a>b?1:0}}}
function cmp(a,b){return COL.compare(String(a),String(b))}
function plain(s){s=String(s).toLowerCase();try{s=s.normalize("NFD").replace(/[\u0300-\u036f]/g,"")}catch(e){}return s}
M.forEach(function(m,i){m.i=i});
var S={layout:store.get("layout")||D.o.layout,theme:store.get("theme")||D.o.theme,ps:store.get("ps")||"s",
 shelf:store.get("shelf")||"coll",sort:-1,dir:1,hide:{}};
try{JSON.parse(store.get("hide")||"[]").forEach(function(i){S.hide[i]=1})}catch(e){}
var body=document.body;
function setTheme(t){body.className=body.className.replace(/\bt-\w+/g,"").trim()+" t-"+t;S.theme=t;store.set("theme",t)}
var lm=store.get("mode");
if(lm?lm==="light":(window.matchMedia&&matchMedia("(prefers-color-scheme: light)").matches))body.classList.add("light");
if(!D.o.flags||store.get("flags")==="0")body.classList.add("noflags");
setTheme(S.theme);
// controls
function opt(v,t){return '<option value="'+esc(v)+'">'+esc(t)+'</option>'}
function uniq(a){var s=Object.create(null),o=[];a.forEach(function(x){if(x!==""&&x!=null&&!s[x]){s[x]=1;o.push(x)}});return o}
var genres=uniq([].concat.apply([],M.map(function(m){return m.g}))).sort(cmp);
var decades=uniq(M.map(function(m){return m.y?Math.floor(m.y/10)*10:""})).sort();
var colls=uniq(M.map(function(m){return m.col})).sort(cmp);
var ress=uniq(M.map(function(m){return m.res}));
var auds=uniq([].concat.apply([],M.map(function(m){return m.al||[]}))).sort();
$("#genre").innerHTML=opt("",L.any_genre)+genres.map(function(g){return opt(g,g)}).join("");
$("#decade").innerHTML=opt("",L.any_decade)+decades.map(function(d){return opt(d,fmt(L.decade,{d:d}))}).join("");
$("#coll").innerHTML=opt("",L.any_coll)+colls.map(function(c){return opt(c,c)}).join("");
$("#res").innerHTML=opt("",L.any_res)+ress.map(function(r){return opt(r,r)}).join("");
$("#aud").innerHTML=opt("",L.any_audio)+auds.map(function(a){return opt(a,a)}).join("");
$("#rat").innerHTML=opt("",L.any_rating)+[9,8,7,6,5].map(function(r){return opt(r,fmt(L.rating_min,{r:r}))}).join("");
if(!colls.length)$("#coll").style.display="none";
if(!auds.length)$("#aud").style.display="none";
if(!M.some(function(m){return m.r!=null}))$("#rat").style.display="none";
var LAY=[["table",L.l_table],["wall",L.l_wall],["shelves",L.l_shelves],["catalogue",L.l_catalogue],["checklist",L.l_checklist]];
$("#lays").innerHTML=LAY.map(function(l){return '<button data-l="'+l[0]+'">'+esc(l[1])+'</button>'}).join("");
$("#theme").innerHTML=["classic","home","studio","aurora","glass","gold"].map(function(t){return opt(t,L["th_"+t])}).join("");
$("#theme").value=S.theme;
$("#ps").innerHTML=[["off",L.ps_off],["s",L.ps_s],["m",L.ps_m],["l",L.ps_l]].map(function(p){return opt(p[0],p[1])}).join("");
$("#ps").value=S.ps;
$("#shelf").innerHTML=[["coll",L.by_coll],["genre",L.by_genre],["decade",L.by_decade]].map(function(p){return opt(p[0],p[1])}).join("");
$("#shelf").value=S.shelf;
$("#fl").classList.toggle("on",!body.classList.contains("noflags"));
if(!D.o.flags)$("#fl").style.display="none";
function setPs(){body.classList.remove("ps-off","ps-s","ps-m","ps-l");body.classList.add("ps-"+S.ps)}
setPs();
// filtering
function hay(m){return plain([m.t,m.y,m.col].concat(m.g,m.d||[],m.a||[]).join(" "))}
M.forEach(function(m){m.h=hay(m)});
function shown(){var q=plain($("#q").value).trim(),g=$("#genre").value,d=$("#decade").value,c=$("#coll").value,
 r=$("#res").value,a=$("#aud").value,rt=$("#rat").value;
 var qs=q?q.split(/\s+/):[];
 var L2=M.filter(function(m){return qs.every(function(w){return m.h.indexOf(w)>=0})&&(!g||m.g.indexOf(g)>=0)
  &&(!d||(m.y&&String(Math.floor(m.y/10)*10)===d))&&(!c||m.col===c)&&(!r||m.res===r)&&(!a||(m.al||[]).indexOf(a)>=0)
  &&(!rt||(m.r!=null&&m.r>=+rt))});
 if(S.layout==="table"&&S.sort>=0){var k=S.sort,isn=D.num[k];
  L2.sort(function(x,y){var a=x.c[k],b=y.c[k];if(isn){a=parseFloat(a);b=parseFloat(b);a=isNaN(a)?-1e18:a;b=isNaN(b)?-1e18:b;return (a-b)*S.dir}
   return cmp(a,b)*S.dir})}
 else if(S.layout!=="shelves")L2.sort(function(x,y){return cmp(x.t,y.t)});
 return L2}
var LINK={imdb_link:/^https:\/\/www\.imdb\.com\/title\/tt\d+\/$/,tmdb_link:/^https:\/\/www\.themoviedb\.org\/movie\/\d+$/};
// pieces
function pz(m){return '<div class="pz">'+(m.pi?'<img data-p="'+m.i+'" alt="">':esc((m.t||"?").charAt(0)))+'</div>'}
function flags(m){var f=[];if(m.res)f.push(m.res);if(m.hdr)f.push(m.hdr);if(m.vc)f.push(m.vc);if(m.au)f.push(m.au);
 (m.sl||[]).slice(0,4).forEach(function(s){f.push("CC "+s)});
 return f.length?'<div class="flags">'+f.map(function(x){return '<span class="flag">'+esc(x)+'</span>'}).join("")+'</div>':""}
function sub(m){return [m.y||"",m.r!=null?"★ "+m.r.toFixed(1):"",m.rt?m.rt+" "+L.min:""].filter(Boolean).join(" · ")}
function tile(m){return '<div class="tile" tabindex="0" data-i="'+m.i+'">'+pz(m)+'<div class="ov"><b>'+esc(m.t)+'</b><span>'+esc(sub(m))+'</span></div><div class="t">'+esc(m.t)+'</div><div class="s">'+esc(sub(m))+'</div>'+flags(m)+'</div>'}
function colCss(){var css="";Object.keys(S.hide).forEach(function(i){var n=+i+2;css+="#tb td:nth-child("+n+"),#tb th:nth-child("+n+"){display:none}"});$("#colcss").textContent=css}
function render(){var Ls=shown(),el=$("#main"),h="";
 var mins=0,k4=0,gc=Object.create(null);Ls.forEach(function(m){mins+=m.rt||0;if(/^(4K|2160p|UHD)$/i.test(m.res))k4++;m.g.forEach(function(g){gc[g]=(gc[g]||0)+1})});
 var top=Object.keys(gc).sort(function(a,b){return gc[b]-gc[a]}).slice(0,3);
 $("#stats").textContent=fmt(L.stats,{n:num(Ls.length),t:num(M.length)})+(mins?" · "+fmt(L.hours,{h:num(Math.round(mins/60))}):"")+(k4?" · "+fmt(L.in4k,{n:num(k4)}):"")+(top.length?" · "+L.top+": "+top.join(", "):"");
 $("#ps").style.display=S.layout==="table"?"":"none";$("#cols").style.display=S.layout==="table"?"":"none";
 $("#shelf").style.display=S.layout==="shelves"?"":"none";
 if(S.layout==="table"){var ti=D.k.indexOf("movie_name");
  h='<table id="tb"><thead><tr><th class="p"></th>'+D.h.map(function(t,i){return '<th data-k="'+i+'"'+(D.num[i]?' class="n"':'')+'>'+esc(t)+(S.sort===i?(S.dir>0?" ▲":" ▼"):"")+'</th>'}).join("")+'</tr></thead><tbody>'+
  Ls.map(function(m){return '<tr data-i="'+m.i+'"><td class="p">'+pz(m)+'</td>'+m.c.map(function(v,i){
   if(i===ti)return '<td><b>'+esc(v)+'</b><div class="mob">'+esc(sub(m))+(m.g.length?" · "+esc(m.g.join(", ")):"")+'</div>'+flags(m)+'</td>';
   if(LINK[D.k[i]]&&LINK[D.k[i]].test(v))return '<td class="x"><a target="_blank" rel="noopener noreferrer" href="'+esc(v)+'">'+esc(v)+'</a></td>';
   return '<td class="x'+(D.num[i]?" n":"")+(D.k[i]==="health"&&m.hs?" h-"+m.hs:"")+'">'+esc(v)+'</td>'}).join("")+'</tr>'}).join("")+'</tbody></table>'}
 else if(S.layout==="wall"){h='<div class="wall">'+Ls.map(tile).join("")+'</div>'}
 else if(S.layout==="shelves"){var G=Object.create(null),order=[];Ls.forEach(function(m){var ks=S.shelf==="genre"?(m.g.length?m.g:[L.other]):
   S.shelf==="decade"?[m.y?fmt(L.decade,{d:Math.floor(m.y/10)*10}):L.other]:[m.col||L.other];
   ks.forEach(function(k){if(!G[k]){G[k]=[];order.push(k)}G[k].push(m)})});
  order.sort(function(a,b){if(a===L.other)return 1;if(b===L.other)return -1;return S.shelf==="coll"?G[b].length-G[a].length||cmp(a,b):cmp(a,b)});
  h=order.map(function(k){var ms=G[k].slice().sort(function(a,b){return (a.y||0)-(b.y||0)||cmp(a.t,b.t)});
   return '<div class="shelf"><h3>'+esc(k)+' <span class="dim">'+num(ms.length)+'</span></h3><div class="strip">'+ms.map(tile).join("")+'</div></div>'}).join("")}
 else if(S.layout==="catalogue"){h='<div class="cards">'+Ls.map(function(m){return '<div class="card" data-i="'+m.i+'">'+pz(m)+'<div><h4>'+esc(m.t)+(m.y?" ("+m.y+")":"")+'</h4><p>'+esc([m.g.join(" · "),m.rt?m.rt+" "+L.min:"",m.r!=null?"★ "+m.r.toFixed(1):""].filter(Boolean).join(" · "))+'</p>'+
   (m.p?'<p>'+esc(m.p.length>320?m.p.slice(0,317)+"…":m.p)+'</p>':"")+((m.d&&m.d.length)?'<p>'+esc(L.director)+': '+esc(m.d.join(", "))+'</p>':"")+((m.a&&m.a.length)?'<p>'+esc(L.with)+': '+esc(m.a.slice(0,4).join(", "))+'</p>':"")+flags(m)+'</div></div>'}).join("")+'</div>'}
 else{h='<div class="check">'+Ls.map(function(m){return '<label><input type="checkbox"> '+esc(m.t)+(m.y?" ("+m.y+")":"")+'</label>'}).join("")+'</div>'}
 el.innerHTML=h;$("#none").style.display=Ls.length?"none":"block";
 colCss();lazy();
 document.documentElement.style.setProperty("--hh",$("header").offsetHeight+"px")}
var main=$("#main");
main.addEventListener("click",function(e){var th=e.target.closest("th[data-k]");
 if(th){var k=+th.dataset.k;S.dir=S.sort===k?-S.dir:1;S.sort=k;render();return}
 if(e.target.closest("input,a"))return;var x=e.target.closest("[data-i]");if(x)openD(+x.dataset.i)});
main.addEventListener("keydown",function(e){if(e.key!=="Enter")return;var x=e.target.closest("[data-i]");if(x&&!e.target.closest("input,a"))openD(+x.dataset.i)});
main.addEventListener("mouseover",function(e){var td=e.target.closest("td.p");if(!td){$("#pv").style.display="none";return}
 var m=M[+td.parentNode.dataset.i];if(!m||!m.pi)return;if(!$("#pv img")){$("#pv").innerHTML='<img alt="">'}$("#pv img").src=m.pi;$("#pv").style.display="block";mv(e)});
main.addEventListener("mousemove",function(e){if($("#pv").style.display==="block")mv(e)});
main.addEventListener("mouseleave",function(){$("#pv").style.display="none"});
window.addEventListener("beforeprint",function(){document.querySelectorAll("img[data-p]").forEach(function(im){if(!im.getAttribute("src"))im.src=M[+im.dataset.p].pi})});
function mv(e){var p=$("#pv"),x=e.clientX+18,y=e.clientY-60;if(x+230>innerWidth)x=e.clientX-240;if(y+340>innerHeight)y=innerHeight-340;p.style.left=x+"px";p.style.top=Math.max(4,y)+"px"}
var io=("IntersectionObserver" in window)?new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){var im=e.target;im.src=M[+im.dataset.p].pi;io.unobserve(im)}})},{rootMargin:"600px"}):null;
function lazy(){document.querySelectorAll("img[data-p]").forEach(function(im){if(io)io.observe(im);else im.src=M[+im.dataset.p].pi})}
function openD(i){var m=M[i],bg=m.fi||m.pi||"";
 var links=[];if(m.imdb)links.push('<a target="_blank" rel="noopener noreferrer" href="https://www.imdb.com/title/'+esc(m.imdb)+'/">'+esc(L.imdb)+'</a>');
 if(m.tmdb)links.push('<a target="_blank" rel="noopener noreferrer" href="https://www.themoviedb.org/movie/'+esc(m.tmdb)+'">'+esc(L.tmdb)+'</a>');
 links.push('<a target="_blank" rel="noopener noreferrer" href="https://www.youtube.com/results?search_query='+encodeURIComponent([m.t,m.y,"trailer"].filter(Boolean).join(" "))+'">'+esc(L.trailer)+'</a>');
 $("#dbg").innerHTML='<div class="im'+(m.fi?"":" blur")+'"></div><div class="sh"></div><h2></h2>';
 if(bg)$("#dbg .im").style.backgroundImage='url("'+bg.replace(/["\\]/g,"")+'")';
 $("#dbg h2").textContent=m.t;
 $("#din").innerHTML=pz(m)+'<div><p><b>'+esc(m.y||"")+'</b>'+(m.g.length?" · "+esc(m.g.join(" · ")):"")+(m.rt?" · "+m.rt+" "+esc(L.min):"")+(m.r!=null?" · ★ "+m.r.toFixed(1)+(m.v?' <span class="dim">('+num(m.v)+')</span>':""):"")+'</p>'+
  (m.col?'<p>'+esc(L.collection)+': '+esc(m.col)+'</p>':"")+(m.p?'<p>'+esc(m.p)+'</p>':"")+
  ((m.d&&m.d.length)?'<p>'+esc(L.director)+': '+esc(m.d.join(", "))+'</p>':"")+((m.a&&m.a.length)?'<p>'+esc(L.with)+': '+esc(m.a.join(", "))+'</p>':"")+
  flags(m)+'<p>'+links.join(" · ")+'</p></div>';
 if(m.pi){$("#din img").src=m.pi}
 $("#detail").style.display="flex";$("#dx").focus()}
function closeD(){$("#detail").style.display="none"}
$("#dx").onclick=closeD;$("#detail").onclick=function(e){if(e.target.id==="detail")closeD()};
document.addEventListener("keydown",function(e){if(e.key==="Escape"){closeD();$("#colsbox").style.display="none"}});
function setLayout(l){S.layout=l;store.set("layout",l);document.querySelectorAll("[data-l]").forEach(function(x){x.classList.toggle("on",x.dataset.l===l)});render()}
document.querySelectorAll("[data-l]").forEach(function(b){b.onclick=function(){setLayout(b.dataset.l)}});
$("#theme").onchange=function(e){setTheme(e.target.value)};
$("#mode").onclick=function(){body.classList.toggle("light");store.set("mode",body.classList.contains("light")?"light":"dark")};
$("#fl").onclick=function(){body.classList.toggle("noflags");var on=!body.classList.contains("noflags");$("#fl").classList.toggle("on",on);store.set("flags",on?"1":"0")};
$("#ps").onchange=function(e){S.ps=e.target.value;store.set("ps",S.ps);setPs()};
$("#shelf").onchange=function(e){S.shelf=e.target.value;store.set("shelf",S.shelf);render()};
$("#rnd").onclick=function(){var Ls=shown();if(Ls.length)openD(Ls[Math.floor(Math.random()*Ls.length)].i)};
$("#prt").onclick=function(){window.print()};
$("#cols").onclick=function(e){var b=$("#colsbox");if(b.style.display==="block"){b.style.display="none";return}
 b.innerHTML=D.h.map(function(t,i){return '<label><input type="checkbox" data-c="'+i+'"'+(S.hide[i]?"":" checked")+'> '+esc(t)+'</label>'}).join("");
 var r=e.target.getBoundingClientRect();b.style.left=Math.min(r.left,innerWidth-220)+"px";b.style.top=(r.bottom+window.scrollY+4)+"px";b.style.display="block";
 b.querySelectorAll("input").forEach(function(c){c.onchange=function(){var i=+c.dataset.c;if(c.checked)delete S.hide[i];else S.hide[i]=1;store.set("hide",JSON.stringify(Object.keys(S.hide)));colCss()}})};
document.addEventListener("click",function(e){var b=$("#colsbox");if(b.style.display==="block"&&!b.contains(e.target)&&e.target.id!=="cols")b.style.display="none"});
var qt=0;$("#q").addEventListener("input",function(){clearTimeout(qt);qt=setTimeout(render,M.length>800?180:0)});
["genre","decade","coll","res","aud","rat"].forEach(function(id){$("#"+id).addEventListener("input",render)});
[["q",L.search],["genre",L.any_genre],["decade",L.any_decade],["coll",L.collection],["rat",L.any_rating],["res",L.any_res],["aud",L.any_audio],["theme",L.theme]].forEach(function(p){$("#"+p[0]).setAttribute("aria-label",p[1])});
$("#q").placeholder=L.search;$("#rnd").textContent="🎲 "+L.random;$("#mode").textContent="☀ / ☾";$("#mode").title=L.light_dark;
$("#fl").textContent=L.flags;$("#cols").textContent=L.columns+" ▾";$("#prt").textContent="🖨 "+L.print;$("#dx").title=L.close;
$("#none").textContent=L.none;$("#lt").textContent=L.layout+":";$("#tt").textContent=L.theme+":";$("#made").textContent=D.made;
$("#ps").title=L.posters;$("#shelf").title=L.shelf_by;
setLayout(LAY.some(function(l){return l[0]===S.layout})?S.layout:"table");
window.addEventListener("resize",function(){document.documentElement.style.setProperty("--hh",$("header").offsetHeight+"px")});
})();
"""

_PAGE = """<!DOCTYPE html>
<html lang="%%LANG%%">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="MediaClinic">
<title>%%TITLE%%</title>
<style>%%CSS%%</style>
<style id="colcss"></style>
</head>
<body %%BODY_ATTR%%>
<header>
 <div class="row"><h1>%%TITLE%%</h1><span class="stats" id="stats"></span></div>
 <div class="row ctl" style="margin-top:8px">
  <input id="q" type="search" size="26" aria-label="search">
  <select id="genre" aria-label="genre"></select><select id="decade" aria-label="decade"></select>
  <select id="coll" aria-label="collection"></select><select id="rat" aria-label="rating"></select>
  <select id="res" aria-label="resolution"></select><select id="aud" aria-label="audio"></select>
  <button id="rnd" type="button"></button>
 </div>
 <div class="row ctl" style="margin-top:8px">
  <span class="stats" id="lt"></span><span id="lays" class="row"></span>
  <select id="ps"></select><select id="shelf"></select><button id="cols" type="button"></button>
  <span class="stats" id="tt"></span><select id="theme" aria-label="theme"></select>
  <button id="mode" type="button"></button><button id="fl" type="button"></button><button id="prt" type="button"></button>
 </div>
</header>
<div id="colsbox"></div>
<main id="main"></main>
<p id="none"></p>
<footer id="made"></footer>
<div id="pv"></div>
<div id="detail" role="dialog" aria-modal="true"><div class="box"><button class="x" id="dx" type="button">×</button><div class="bg" id="dbg"></div><div class="in" id="din"></div></div></div>
<script type="application/json" id="data">%%DATA%%</script>
<script>%%JS%%</script>
</body>
</html>
"""
