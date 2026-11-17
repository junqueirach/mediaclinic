# =============================================================================
# export_list.py
# Metadata & MediaClinic — Movie List Export (pure logic, no tkinter)
# Version: 0.19.0                                              ### MODIFIED v0.19.0 — Library field ###
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# Turn scan-result row dicts into a file: CSV (comma or semicolon), tab-
# separated text, a plain text list, or an Excel workbook (openpyxl).
# Field selection and presets live here so the dialog in the main script is
# UI only and this module can be unit-tested headlessly.
#
# RULES
# -----
#   • NO tkinter import.  Pure functions only.
#   • CSV/TSV always go through the csv module, so commas, quotes and newlines
#     inside movie names are quoted correctly and never break the file.
#   • CSV is written with a UTF-8 BOM so Excel detects accented characters.
# =============================================================================

import base64                                                    ### NEW v0.20.0 I38 ###
import csv
import html
import io
import os
import re
import mc_i18n as _i18n                                           ### NEW v0.20.0 UI1d — headings and cell words (UI-D2) ###

# Status symbols (must match STATUS_* in the main script)
_STATUS_TEXT = {"⬤": "OK", "◐": "Warning", "○": "Missing", "✕": "Error"}


def _status_text(sym):
    return _STATUS_TEXT.get(sym, str(sym) if sym else "")


def _img_cell(row, key):
    if not row.get(f"{key}_exists"):
        return _i18n.t("ex.st.Missing")
    st = _status_text(row.get(f"{key}_status"))
    q  = row.get(f"{key}_quality", "—")
    return f"{st} {q}".strip() if q and q != "—" else st


def _file_status(row, key):
    if key == "xml" and row.get("xml_used") is False:                # v0.19.6 TR1: movie.xml off / NFO-only library
        return _i18n.t("ex.st.Not used")
    if key == "nfo" and row.get("nfo_used") is False:                # v0.19.6 TR1b: health mode "movie.xml only"
        return _i18n.t("ex.st.Not used")
    if not row.get(f"{key}_exists"):
        return _i18n.t("ex.st.Missing")
    return _i18n.t("ex.st.Error") if row.get(f"{key}_errors") else _i18n.t("ex.st.OK")


def _errors_text(row, key):
    return "; ".join(f"L{e.get('line', 0)}: {e.get('message', '')}"
                     for e in row.get(f"{key}_errors", []) or [])


def _audio_text(row):
    tracks = sorted(row.get("audio_tracks", []) or [],
                    key=lambda t: t.get("language", ""))
    return ", ".join(f"{t.get('language', '')} ({t.get('channels')})"
                     if t.get("channels") else t.get("language", "")
                     for t in tracks)


def _votes_text(row):
    v = row.get("votes_int", 0) or 0
    return str(int(v)) if v else ""


# ── Outline / plot read from the files at export time (v0.18.4) ─────────────
_TEXT_CACHE = {}


def _file_text(path):
    """Text of *path* (BOM stripped); '' if absent.  Cached by path for the
    duration of one export (export_rows clears the cache), so every NFO/XML
    is opened at most once even when Outline and Plot are both selected."""
    if not path:
        return ""
    key = path
    hit = _TEXT_CACHE.get(key)
    if hit is not None:
        return hit
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            txt = f.read()
    except OSError:
        txt = ""
    if txt.startswith("\ufeff"):
        txt = txt[1:]
    if len(_TEXT_CACHE) > 2000:
        _TEXT_CACHE.clear()
    _TEXT_CACHE[key] = txt
    return txt


def _first_tag(row, nfo_tags, xml_tags):
    """First non-empty <tag> text found in the NFO (then XML), cleaned for a cell."""
    for key, tags in (("nfo", nfo_tags), ("xml", xml_tags)):
        if not row.get(f"{key}_exists"):
            continue
        txt = _file_text(row.get(f"{key}_path"))
        for tag in tags:
            m = re.search(rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}\s*>", txt, re.I | re.S)
            if m:
                val = html.unescape(m.group(1)).strip()
                if val.startswith("<![CDATA[") and val.endswith("]]>"):
                    val = val[9:-3].strip()
                val = " ".join(val.split())
                if val:
                    return val
    return ""


def _imdb_link(row):
    v = (row.get("source_imdb_val") or "").strip()
    return f"https://www.imdb.com/title/{v}/" if v else ""


def _tmdb_link(row):
    v = (row.get("source_tmdb_val") or "").strip()
    return f"https://www.themoviedb.org/movie/{v}" if v else ""


# ── Field registry: (key, column header, getter(row) -> str) ─────────────────
EXPORT_FIELDS = [
    ("movie_name",    "Movie Name",     lambda r: r.get("movie_name") or r.get("subfolder", "")),
    ("year",          "Year",           lambda r: "" if r.get("movie_year", "-") in ("-", None) else str(r.get("movie_year"))),
    ("genres",        "Genres",         lambda r: "" if r.get("genre_display", "—") == "—" else r.get("genre_display", "")),
    ("rating",        "Rating",         lambda r: "" if r.get("rating_str", "-") == "-" else r.get("rating_str", "")),
    ("votes",         "Votes",          _votes_text),
    ("imdb_id",       "IMDb ID",        lambda r: r.get("source_imdb_val") or ""),
    ("tmdb_id",       "TMDB ID",        lambda r: r.get("source_tmdb_val") or ""),
    ("imdb_link",     "IMDb Link",      _imdb_link),                                   # v0.18.4
    ("tmdb_link",     "TMDB Link",      _tmdb_link),                                   # v0.18.4
    ("outline",       "Outline",        lambda r: _first_tag(r, ["outline"], ["Outline", "Tagline"])),   # v0.18.4
    ("plot",          "Plot",           lambda r: _first_tag(r, ["plot"], ["Overview", "Plot", "Description"])),  # v0.18.4
    ("poster",        "Poster",         lambda r: _img_cell(r, "poster")),
    ("folder_img",    "Folder",         lambda r: _img_cell(r, "folder")),
    ("fanart",        "Fanart",         lambda r: _img_cell(r, "fanart")),
    ("backdrops",     "Backdrops",      lambda r: str(r.get("backdrop_count", 0))),
    ("nfo",           "NFO",            lambda r: _file_status(r, "nfo")),
    ("nfo_errors",    "NFO Errors",     lambda r: _errors_text(r, "nfo")),
    ("xml",           "XML",            lambda r: _file_status(r, "xml")),
    ("xml_errors",    "XML Errors",     lambda r: _errors_text(r, "xml")),
    ("language",      "Language",       lambda r: "" if r.get("language", "—") == "—" else r.get("language", "")),
    ("video_ext",     "Video",          lambda r: "" if r.get("video_count", 0) == 0 else r.get("video_ext", "")),
    ("video_size",    "Video Size",     lambda r: "" if r.get("video_count", 0) == 0 else r.get("video_size", "")),
    ("video_quality", "Video Quality",  lambda r: "" if r.get("video_quality", "—") in ("—", "-") else r.get("video_quality", "")),
    ("audio",         "Audio",          _audio_text),
    ("lang_ok",       "Lang OK?",       lambda r: "" if r.get("lang_ok", "—") == "—" else r.get("lang_ok", "")),
    ("subtitles",     "Subtitles",      lambda r: "" if r.get("subs_summary", "—") == "—" else r.get("subs_summary", "")),
    ("health",        "Health",         lambda r: _health_text(r.get("health_status") or "")),
    ("health_reasons","Health Reasons", lambda r: "; ".join(REASON_TEXT[0](x) for x in (r.get("health_reasons", []) or []))),
    ("library",       "Library",        lambda r: r.get("library_root") or os.path.dirname(r.get("subfolder_path", "") or "")),   # v0.19.0
    ("collection",    "Collection",     lambda r: ((r.get("coll_nfo") or {}).get("name") or "")),   # v0.19.4 B110a
    ("folder_name",   "Folder Name",    lambda r: r.get("subfolder", "")),
    ("path",          "Path",           lambda r: r.get("subfolder_path", "")),
]

_FIELD_MAP = {k: (label, fn) for k, label, fn in EXPORT_FIELDS}
_EN_STATUS = dict(_STATUS_TEXT)                                    ### NEW v0.20.0 UI1d ###
ALL_FIELD_KEYS = [k for k, _, _ in EXPORT_FIELDS]

PRESETS = {
    "Basic":    ["movie_name", "year"],
    "Identify": ["movie_name", "year", "imdb_link", "tmdb_link", "outline"],        # v0.18.4
    "Standard": ["movie_name", "year", "genres", "rating", "votes",
                 "video_quality", "health"],
    "All":      list(ALL_FIELD_KEYS),
}

# (format id, label shown in dialog, default extension)
FORMATS = [
    ("csv_comma",     "CSV — comma separated (default)",                 ".csv"),
    ("csv_semicolon", "CSV — semicolon separated (Excel in CH/DE/PT/FR locales)", ".csv"),
    ("tsv",           "Tab-separated text (.txt)",                       ".txt"),
    ("txt",           "Plain text list — one movie per line (.txt)",      ".txt"),
    ("xlsx",          "Excel workbook (.xlsx)",                          ".xlsx"),
    ("html",          "HTML page — one file for any browser (.html)",    ".html"),   # v0.20.0 I38
]
_FORMAT_EXT = {f: ext for f, _, ext in FORMATS}


def relabel():                                                   ### NEW v0.20.0 UI1d ###
    """Headings, status words and format names in the interface language (the main script calls it at start);
    field keys, preset names (stored) and the movie data never change."""
    EXPORT_FIELDS[:] = [(k, _i18n.t("ex.col." + k) if _i18n.has("ex.col." + k) else lbl, fn) for k, lbl, fn in EXPORT_FIELDS]
    _FIELD_MAP.clear()
    _FIELD_MAP.update({k: (label, fn) for k, label, fn in EXPORT_FIELDS})
    FORMATS[:] = [(f, _i18n.t("ex.fmt." + f) if _i18n.has("ex.fmt." + f) else lbl, ext) for f, lbl, ext in FORMATS]
    for sym, word in _EN_STATUS.items():
        _STATUS_TEXT[sym] = _i18n.t("ex.st." + word)


def preset_label(name):                                          ### NEW v0.20.0 UI1d ###
    """A preset's shown name ("Basic" → "Básico"); the stored name stays English."""
    return _i18n.t("ex.preset." + name) if _i18n.has("ex.preset." + name) else name


def _health_text(status):
    return _i18n.t("ex.health." + status) if _i18n.has("ex.health." + status) else status.capitalize()


REASON_TEXT = [str]                                               # the main script puts reason_text here (UI1c templates)


def xlsx_available():
    """True when openpyxl can be imported (optional dependency)."""
    try:
        import openpyxl  # noqa: F401
        return True
    except Exception:
        return False


def default_extension(fmt):
    return _FORMAT_EXT.get(fmt, ".txt")


def build_table(rows, field_keys):
    """Return (headers, data) where data is a list of lists of strings."""
    keys = [k for k in field_keys if k in _FIELD_MAP] or ["movie_name"]
    headers = [_FIELD_MAP[k][0] for k in keys]
    data = []
    _TEXT_CACHE.clear()          # each NFO/XML is opened at most once per table build
    try:
        for r in rows:
            line = []
            for k in keys:
                try:
                    v = _FIELD_MAP[k][1](r)
                except Exception:
                    v = ""
                line.append("" if v is None else str(v))
            data.append(line)
    finally:
        _TEXT_CACHE.clear()
    return headers, data


def _txt_line(keys, values):
    """Plain-text rendering: 'Name (Year)' when both present, else ' | ' join."""
    pairs = dict(zip(keys, values))
    name = pairs.get("movie_name", "")
    year = pairs.get("year", "")
    rest = [v for k, v in zip(keys, values)
            if k not in ("movie_name", "year") and v]
    head = f"{name} ({year})" if name and year else (name or year)
    return " | ".join([head] + rest) if head else " | ".join(rest)


_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _no_formula(v):                                              ### NEW v0.20.0 AU8 (pre-build audit) ###
    """A CSV / TSV cell Excel would run as a formula (a title or plot from a downloaded NFO that starts with
    '=', '+', '-', '@') gets a leading apostrophe; numbers and a lone '-' stay as they are."""
    if isinstance(v, str) and len(v) > 1 and v.startswith(_FORMULA_START):
        try:
            float(v.replace(",", "."))
            return v
        except ValueError:
            return "'" + v
    return v


def _xl_text(v):                                                 # v0.20.0 AU8: one control character aborted the .xlsx
    if isinstance(v, str):
        try:
            from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
            return ILLEGAL_CHARACTERS_RE.sub("", v)
        except ImportError:
            return v
    return v


def export_rows(rows, field_keys, fmt, path, posters=False, progress=None, cancelled=None, when=None, app_version=""):
    """
    Write *rows* (list of scan-result dicts) to *path* in format *fmt*.
    Returns the number of movies written.  Raises on I/O error or when
    fmt == 'xlsx' and openpyxl is unavailable.
    v0.20.0 I38: fmt 'html' — one page (posters: small thumbnails embedded; progress / cancelled for a worker).
    """
    if fmt == "html":
        page = html_page(rows, field_keys, posters=posters, progress=progress, cancelled=cancelled,
                         when=when, app_version=app_version)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(page)
        return len(rows)

    keys = [k for k in field_keys if k in _FIELD_MAP] or ["movie_name"]
    headers, data = build_table(rows, keys)

    if fmt in ("csv_comma", "csv_semicolon", "tsv"):
        delim = {"csv_comma": ",", "csv_semicolon": ";", "tsv": "\t"}[fmt]
        enc   = "utf-8-sig"                       # v0.20.0 AU8: TSV too (Excel garbled accents without the BOM)
        with open(path, "w", newline="", encoding=enc) as f:
            w = csv.writer(f, delimiter=delim, quotechar='"',
                           quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writerow(headers)
            w.writerows([[_no_formula(v) for v in row] for row in data])
        return len(data)

    if fmt == "txt":
        with open(path, "w", encoding="utf-8") as f:
            for values in data:
                f.write(_txt_line(keys, values) + "\n")
        return len(data)

    if fmt == "xlsx":
        import openpyxl
        from openpyxl.styles import Font
        from openpyxl.utils import get_column_letter
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Movies"
        ws.append(headers)
        for c in ws[1]:
            c.font = Font(bold=True)
        for values in data:
            out = []
            for k, v in zip(keys, values):
                if k in ("year", "votes", "backdrops") and v.isdigit():
                    out.append(int(v))
                elif k == "rating":
                    try:
                        out.append(float(v) if v else "")
                    except ValueError:
                        out.append(v)
                else:
                    out.append(_xl_text(v))
            ws.append(out)
            for c in ws[ws.max_row]:                       # v0.20.0 AU8: text that starts with '=' stays text
                if isinstance(c.value, str) and c.value.startswith("="):
                    c.data_type = "s"
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for i, h in enumerate(headers, 1):
            width = max([len(h)] + [len(str(row[i - 1])) for row in data[:500]])
            ws.column_dimensions[get_column_letter(i)].width = min(max(8, width + 2), 60)
        wb.save(path)
        return len(data)

    raise ValueError(f"Unknown export format: {fmt}")


# ── v0.20.0 I38: HTML page (tester TR3) — one self-contained file, optional poster thumbnails ──
HTML_THUMB_WIDTH = 120                     # pixels stored (shown at 60 × 90: sharp on a 200 % screen)
_NUM_KEYS = ("year", "rating", "votes", "backdrops")
_LINK_KEYS = ("imdb_link", "tmdb_link")


def pil_available():
    """True when Pillow can be imported (poster thumbnails need it)."""
    try:
        from PIL import Image  # noqa: F401
        return True
    except Exception:
        return False


def poster_data_uri(path, width=HTML_THUMB_WIDTH):
    """A small JPEG of the poster as a data: URI ("" when it cannot be read)."""
    if not path or not os.path.isfile(path):
        return ""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((width, width * 2))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=80, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


_HTML_CSS = """
:root{--bg:#ffffff;--fg:#1b1d22;--dim:#5f6570;--line:#d9dce2;--head:#f1f3f6;--link:#1a5fb4;--ok:#2e7d32;--warn:#a15c00;--err:#c62828;--hover:#f6f8fb}
@media (prefers-color-scheme:dark){:root{--bg:#16181d;--fg:#e6e8ec;--dim:#9aa1ad;--line:#2c3038;--head:#1f2229;--link:#8ab4f8;--ok:#81c784;--warn:#ffb74d;--err:#ef9a9a;--hover:#1c1f25}}
*{box-sizing:border-box}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
h1{font-size:20px;margin:0 0 4px}
.meta{color:var(--dim);margin:0 0 12px}
#q{width:100%;max-width:420px;padding:7px 10px;margin:0 0 12px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);font:inherit}
.wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{position:sticky;top:0;background:var(--head);cursor:pointer;white-space:nowrap;user-select:none}
th[aria-sort=ascending]::after{content:" \\25B2";font-size:10px}
th[aria-sort=descending]::after{content:" \\25BC";font-size:10px}
th.nosort{cursor:default}
tbody tr:hover{background:var(--hover)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td.poster{width:68px}
td.poster img{width:60px;height:90px;object-fit:cover;border-radius:3px;display:block}
a{color:var(--link)}
.h-ok{color:var(--ok)} .h-warning{color:var(--warn)} .h-error{color:var(--err)}
#none{display:none;color:var(--dim);padding:12px 0}
"""

_HTML_JS = """
(function(){
var t=document.getElementById('t'),b=t.tBodies[0],q=document.getElementById('q'),none=document.getElementById('none');
var rows=Array.prototype.slice.call(b.rows);
q.addEventListener('input',function(){var s=q.value.toLowerCase(),n=0;
rows.forEach(function(r){var on=!s||r.textContent.toLowerCase().indexOf(s)>=0;r.style.display=on?'':'none';if(on)n++;});
none.style.display=n?'none':'block';});
Array.prototype.forEach.call(t.tHead.rows[0].cells,function(th,i){if(th.classList.contains('nosort'))return;
th.addEventListener('click',function(){var asc=th.getAttribute('aria-sort')!=='ascending';
Array.prototype.forEach.call(t.tHead.rows[0].cells,function(o){o.removeAttribute('aria-sort');});
th.setAttribute('aria-sort',asc?'ascending':'descending');var num=th.dataset.num==='1';
rows.sort(function(a,c){var x=a.cells[i].dataset.v!==undefined?a.cells[i].dataset.v:a.cells[i].textContent,
y=c.cells[i].dataset.v!==undefined?c.cells[i].dataset.v:c.cells[i].textContent;
if(num){x=parseFloat(x);y=parseFloat(y);x=isNaN(x)?-1e18:x;y=isNaN(y)?-1e18:y;return asc?x-y:y-x;}
return asc?x.localeCompare(y):y.localeCompare(x);});
rows.forEach(function(r){b.appendChild(r);});});});
})();
"""


def _e(s):
    return html.escape("" if s is None else str(s), quote=True)


def html_page(rows, field_keys, posters=False, progress=None, cancelled=None, title=None, when=None, app_version=""):
    """The whole HTML page as text (pure apart from reading the posters).  *progress(i)* after each movie;
    *cancelled()* → True stops with RuntimeError (no file is written)."""
    keys = [k for k in field_keys if k in _FIELD_MAP] or ["movie_name"]
    headers, data = build_table(rows, keys)
    lang = {"pt_BR": "pt-BR"}.get(_i18n.current(), _i18n.current())
    title = title or _i18n.t("ex.html.title")
    meta = _i18n.tn("ex.html.count", len(data), as_text=_i18n.num(len(data)))
    if when:
        meta += " · " + _i18n.t("ex.html.made", when=when, version=app_version)
    out = ['<!DOCTYPE html>', f'<html lang="{_e(lang)}">', '<head>', '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           f'<title>{_e(title)}</title>', '<style>' + _HTML_CSS + '</style>', '</head>', '<body>',
           f'<h1>{_e(title)}</h1>', f'<p class="meta">{_e(meta)}</p>',
           f'<input id="q" type="search" placeholder="{_e(_i18n.t("ex.html.filter"))}" aria-label="{_e(_i18n.t("ex.html.filter"))}">',
           '<div class="wrap"><table id="t"><thead><tr>']
    if posters:
        out.append(f'<th class="nosort">{_e(_i18n.t("ex.html.poster"))}</th>')
    for k, h in zip(keys, headers):
        num_attr = ' data-num="1"' if k in _NUM_KEYS else ""
        out.append(f'<th{num_attr}>{_e(h)}</th>')
    out.append('</tr></thead><tbody>')
    for i, (r, values) in enumerate(zip(rows, data)):
        if cancelled and cancelled():
            raise RuntimeError(_i18n.t("ex.html.cancelled"))
        cells = []
        if posters:
            uri = poster_data_uri(r.get("poster_path")) if r.get("poster_exists") else ""
            img = ('<img src="' + uri + '" alt="" loading="lazy">') if uri else ""
            cells.append('<td class="poster">' + img + '</td>')
        for k, v in zip(keys, values):
            if k in _LINK_KEYS and v:
                cells.append(f'<td><a href="{_e(v)}" target="_blank" rel="noopener">{_e(v)}</a></td>')
            elif k in _NUM_KEYS:
                cells.append(f'<td class="num" data-v="{_e(v)}">{_e(v)}</td>')
            elif k == "health":
                cells.append(f'<td class="h-{_e(r.get("health_status") or "")}">{_e(v)}</td>')
            else:
                cells.append(f'<td>{_e(v)}</td>')
        out.append('<tr>' + ''.join(cells) + '</tr>')
        if progress:
            progress(i + 1)
    out += ['</tbody></table></div>', f'<p id="none">{_e(_i18n.t("ex.html.none"))}</p>',
            '<script>' + _HTML_JS + '</script>', '</body>', '</html>', '']
    return "\n".join(out)


def suggested_filename(fmt, folder_name=""):
    base = "movie_list"
    if folder_name:
        safe = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in folder_name).strip()
        if safe:
            base = f"movie_list_{safe.replace(' ', '_')}"
    return base + default_extension(fmt)


if __name__ == "__main__":
    print("Fields:", ", ".join(ALL_FIELD_KEYS))
    print("xlsx available:", xlsx_available())
    print(os.path.basename(__file__), "is a library module — see selftest_v0_18_3.py")
