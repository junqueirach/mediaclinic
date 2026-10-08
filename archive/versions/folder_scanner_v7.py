# =============================================================================
# Media and Metadata Clinic
# Version: 0.7.0
# Author:  Luiz Junqueira & Claude AI
# Contact: junqueira.ch@gmail.com
#
# VERSION CONTROL GUIDE
# ---------------------
# v1.0.0  — Major update / first stable release
# v1.1.0  — Medium changes / new features / bug fixes
# v1.0.1  — Small bug fixes / cosmetic patches
#
# CHANGELOG
# ---------
# v0.7.0  (current)
#   - Renamed to "Media and Metadata Clinic"
#   - Improved backdrop extractor: per-frame 60s timeout (user-configurable),
#     partial extraction recovery, descriptive result popup
#   - FFmpeg path validation now tests both ffmpeg AND ffprobe with --version
#   - Last scan session persisted in JSON (~AppData / ~/.config); no more .ini
#   - Column word-wrap toggle (on/off); double-click header auto-resizes column
#     (Subtitles column excluded from wrapping)
#   - New "Quality" column: 4K/1080p/720p/576p-DVD/480p/360p/SD
#   - "Update Scan" button to re-scan the previously scanned folder
#   - Help dialog: System Help, FFmpeg Help, About
#   - Extract Frames button greyed out when FFmpeg is absent
#   - Estimated remaining time shown during scan/update
#   - Sort menu: added Fanart size (sm→lg), Language (Z→A), PT OK?
#   - Secondary sort by Subfolder always applied after primary sort
#   - New "PT OK?" column: Y if Portuguese audio OR Portuguese subtitle present
#   - Page-Up / Page-Down / Home / End keyboard navigation in results table
# =============================================================================

import os
import csv
import json
import re
import struct
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import shutil
import webbrowser

# ── App identity ──────────────────────────────────────────────────────────────
APP_NAME    = "Media and Metadata Clinic"
APP_VERSION = "0.7.0"
APP_AUTHOR  = "Luiz Junqueira & Claude AI"
APP_EMAIL   = "junqueira.ch@gmail.com"

# ── Video / subtitle extensions ───────────────────────────────────────────────
VIDEO_EXTENSIONS    = {'.mkv', '.mp4', '.avi', '.m4v', '.wmv', '.mov', '.flv',
                       '.ts', '.m2ts', '.mpg', '.mpeg', '.divx', '.ogm', '.webm'}
SUBTITLE_EXTENSIONS = {'.srt', '.sub', '.ssa', '.ass', '.vtt', '.idx', '.sup'}

# Portuguese language tags (audio or subtitle)
PT_TAGS = {'por', 'pt', 'pt-br', 'pt-pt', 'portuguese', 'portugues',
           'pt_br', 'pt_pt', 'ptbr', 'ptpt'}

# ── Column indices ────────────────────────────────────────────────────────────
COL_SUBFOLDER  =  0
COL_POSTER     =  1;  COL_POSTER_SZ  =  2
COL_FOLDER     =  3;  COL_FOLDER_SZ  =  4
COL_FANART     =  5;  COL_FANART_SZ  =  6
COL_BACKDROPS  =  7
COL_NFO        =  8;  COL_NFO_OK     =  9
COL_XML        = 10;  COL_XML_OK     = 11
COL_LANGUAGE   = 12
COL_VID_EXT    = 13;  COL_VID_SIZE   = 14;  COL_QUALITY = 15
COL_PT_OK      = 16
COL_SUBS       = 17

STATUS_OK      = "✅"
STATUS_MISSING = "❌"
STATUS_ERROR   = "⚠️"

# ── Persistent storage (AppData / ~/.config) ──────────────────────────────────
def _get_config_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
    d = os.path.join(base, "MediaMetadataClinic")
    os.makedirs(d, exist_ok=True)
    return d

CONFIG_PATH = os.path.join(_get_config_dir(), "settings.json")

_DEFAULT_SETTINGS = {
    "ffmpeg_path": "",
    "last_folder":  "",
    "last_results": [],
    "wrap_columns": False,
    "extract_timeout": 60,
    "sort_option": "Subfolder (A→Z)",
}

def _load_settings():
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults so new keys always exist
            merged = dict(_DEFAULT_SETTINGS)
            merged.update(data)
            return merged
    except Exception:
        pass
    return dict(_DEFAULT_SETTINGS)

def _save_settings(s):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ── FFmpeg discovery & validation ─────────────────────────────────────────────
def _find_ffmpeg_ffprobe(custom_dir=""):
    """Locate ffmpeg and ffprobe. Returns (ffmpeg_path, ffprobe_path)."""
    exe = lambda d, n: (os.path.join(d, n + ".exe") if os.name == "nt" else os.path.join(d, n))

    if custom_dir and os.path.isdir(custom_dir):
        ff = exe(custom_dir, "ffmpeg")
        fp = exe(custom_dir, "ffprobe")
        # Fallback without .exe
        if not os.path.isfile(ff): ff = os.path.join(custom_dir, "ffmpeg")
        if not os.path.isfile(fp): fp = os.path.join(custom_dir, "ffprobe")
        if os.path.isfile(ff) and os.path.isfile(fp):
            return ff, fp

    return shutil.which("ffmpeg"), shutil.which("ffprobe")


def _test_ffmpeg(ff_path, fp_path):
    """
    Test that both ffmpeg and ffprobe actually run.
    Returns (ffmpeg_ok, ffprobe_ok, ffmpeg_msg, ffprobe_msg).
    """
    def _run(path):
        if not path or not os.path.isfile(path):
            return False, "Executable not found"
        try:
            r = subprocess.run(
                [path, "-version"],
                capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0 and ("ffmpeg" in r.stdout.lower() or "ffprobe" in r.stdout.lower()):
                return True, "OK"
            return False, f"Unexpected output (exit {r.returncode})"
        except subprocess.TimeoutExpired:
            return False, "Timed out during version check"
        except Exception as e:
            return False, str(e)

    ff_ok, ff_msg = _run(ff_path)
    fp_ok, fp_msg = _run(fp_path)
    return ff_ok, fp_ok, ff_msg, fp_msg


SETTINGS      = _load_settings()
FFMPEG_PATH, FFPROBE_PATH = _find_ffmpeg_ffprobe(SETTINGS.get("ffmpeg_path", ""))


def refresh_ffmpeg_paths():
    global FFMPEG_PATH, FFPROBE_PATH
    FFMPEG_PATH, FFPROBE_PATH = _find_ffmpeg_ffprobe(SETTINGS.get("ffmpeg_path", ""))


# ══════════════════════════════════════════════════════════════════════════════
# Utility helpers
# ══════════════════════════════════════════════════════════════════════════════

def format_size(size_bytes):
    if size_bytes < 1024:        return f"{size_bytes} B"
    elif size_bytes < 1024**2:   return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:   return f"{size_bytes/(1024**2):.1f} MB"
    else:                        return f"{size_bytes/(1024**3):.2f} GB"


def os_open(path):
    try:
        os.startfile(path)
    except AttributeError:
        try:   subprocess.Popen(["xdg-open", path])
        except FileNotFoundError: subprocess.Popen(["open", path])
    except Exception as e:
        messagebox.showerror("Cannot open", str(e))


def get_jpeg_dimensions(filepath):
    try:
        with open(filepath, "rb") as f:
            if f.read(2) != b'\xff\xd8': return None, None
            while True:
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF: return None, None
                m = marker[1]
                while m == 0xFF:
                    b = f.read(1)
                    if len(b) < 1: return None, None
                    m = b[0]
                if m in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
                    f.read(3); hw = f.read(4)
                    if len(hw) < 4: return None, None
                    return struct.unpack(">H", hw[2:4])[0], struct.unpack(">H", hw[0:2])[0]
                elif m in (0xD9, 0xDA): return None, None
                else:
                    d = f.read(2)
                    if len(d) < 2: return None, None
                    f.seek(struct.unpack(">H", d)[0] - 2, 1)
    except Exception: return None, None


def get_png_dimensions(filepath):
    try:
        with open(filepath, "rb") as f:
            if f.read(8)[:4] != b'\x89PNG': return None, None
            f.read(4)
            if f.read(4) != b'IHDR': return None, None
            d = f.read(8)
            if len(d) < 8: return None, None
            return struct.unpack(">I", d[0:4])[0], struct.unpack(">I", d[4:8])[0]
    except Exception: return None, None


def get_image_dimensions(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    w, h = (get_jpeg_dimensions(filepath) if ext in ('.jpg', '.jpeg')
            else get_png_dimensions(filepath) if ext == '.png' else (None, None))
    return f"{w}×{h}" if w and h and (w > 0 or h > 0) else None


def is_valid_jpeg(filepath):
    try:
        if os.path.getsize(filepath) == 0: return False
        with open(filepath, "rb") as f: return f.read(2) == b'\xff\xd8'
    except Exception: return False


def classify_quality(width, height):
    """Return a human-readable quality label from video dimensions."""
    if width is None or height is None:
        return "—"
    h = min(width, height)   # use shorter dimension (handles portrait video)
    if h >= 2160:  return "4K UHD"
    if h >= 1440:  return "1440p"
    if h >= 1080:  return "1080p"
    if h >= 720:   return "720p"
    if h >= 576:   return "576p/DVD"
    if h >= 480:   return "480p"
    if h >= 360:   return "360p"
    if h >= 240:   return "240p"
    return "SD"


def _quality_sort_key(label):
    """Lower = better quality."""
    order = {"4K UHD": 0, "1440p": 1, "1080p": 2, "720p": 3,
             "576p/DVD": 4, "480p": 5, "360p": 6, "240p": 7, "SD": 8, "—": 9}
    return order.get(label, 9)


def is_portuguese_lang(tag):
    """Return True if the language tag refers to Portuguese."""
    return tag.strip().lower() in PT_TAGS


# ══════════════════════════════════════════════════════════════════════════════
# Backdrop / Video / Subtitle / Language / XML helpers
# ══════════════════════════════════════════════════════════════════════════════

def count_backdrops(sub_path):
    count = 0; paths = []
    p = os.path.join(sub_path, "backdrop.jpg")
    if os.path.isfile(p): count += 1; paths.append(p)
    for i in range(1, 200):
        p = os.path.join(sub_path, f"backdrop{i}.jpg")
        if os.path.isfile(p): count += 1; paths.append(p)
        else: break
    return count, paths


def next_backdrop_number(sub_path):
    if not os.path.isfile(os.path.join(sub_path, "backdrop.jpg")):
        return 0
    highest = 0
    for i in range(1, 200):
        if os.path.isfile(os.path.join(sub_path, f"backdrop{i}.jpg")):
            highest = i
    if not os.path.isfile(os.path.join(sub_path, "backdrop.jpg")):
        return 0
    for i in range(1, 200):
        if not os.path.isfile(os.path.join(sub_path, f"backdrop{i}.jpg")):
            return i
    return 1


def scan_video_files(sub_path):
    videos = []
    try:
        for f in os.scandir(sub_path):
            if f.is_file() and os.path.splitext(f.name)[1].lower() in VIDEO_EXTENSIONS:
                videos.append(f)
    except PermissionError: pass
    if not videos:
        return {"video_count": 0, "video_files": [], "video_ext": "—",
                "video_path": None, "video_bytes": 0, "video_size": "—",
                "video_width": None, "video_height": None, "video_quality": "—"}
    videos.sort(key=lambda e: e.stat().st_size, reverse=True)
    main = videos[0]; ext = os.path.splitext(main.name)[1].lower()
    w, h = _get_video_resolution(main.path)
    return {"video_count": len(videos), "video_files": [v.name for v in videos],
            "video_ext": ext.lstrip('.').upper(), "video_path": main.path,
            "video_bytes": main.stat().st_size, "video_size": format_size(main.stat().st_size),
            "video_width": w, "video_height": h, "video_quality": classify_quality(w, h)}


def _get_video_resolution(video_path):
    """Return (width, height) of the first video stream, or (None, None)."""
    if not FFPROBE_PATH: return None, None
    try:
        r = subprocess.run(
            [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "v:0", video_path],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode == 0 and r.stdout.strip():
            streams = json.loads(r.stdout).get("streams", [])
            if streams:
                w = streams[0].get("width")
                h = streams[0].get("height")
                if w and h:
                    return int(w), int(h)
    except Exception: pass
    return None, None


def scan_subtitles(sub_path, video_path):
    result = {"subs_internal": [], "subs_external": [], "subs_summary": "—"}
    try:
        for f in os.scandir(sub_path):
            if f.is_file() and os.path.splitext(f.name)[1].lower() in SUBTITLE_EXTENSIONS:
                parts = os.path.splitext(f.name)[0].rsplit('.', 1)
                lang = parts[-1] if len(parts) > 1 and len(parts[-1]) <= 20 else "unknown"
                result["subs_external"].append({"lang": lang, "file": f.name})
    except PermissionError: pass
    if video_path and FFPROBE_PATH:
        try:
            proc = subprocess.run(
                [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-select_streams", "s", video_path],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if proc.returncode == 0 and proc.stdout.strip():
                for stream in json.loads(proc.stdout).get("streams", []):
                    tags = stream.get("tags", {})
                    result["subs_internal"].append({
                        "lang":  tags.get("language") or tags.get("LANGUAGE") or "und",
                        "title": tags.get("title")    or tags.get("TITLE")    or ""})
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, OSError): pass
    parts = []
    if result["subs_internal"]: parts.append(f"Int: {', '.join(s['lang'] for s in result['subs_internal'])}")
    if result["subs_external"]: parts.append(f"Ext: {', '.join(s['lang'] for s in result['subs_external'])}")
    result["subs_summary"] = " | ".join(parts) if parts else ("None" if video_path else "—")
    return result


def compute_pt_ok(video_path, subs_internal, subs_external):
    """
    Y  — audio is Portuguese OR any Portuguese subtitle is present (internal/external)
    N  — video present but no Portuguese audio or subtitle
    —  — no video file
    """
    if not video_path:
        return "—"

    # Check audio streams for Portuguese
    if FFPROBE_PATH:
        try:
            r = subprocess.run(
                [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-select_streams", "a", video_path],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0 and r.stdout.strip():
                for stream in json.loads(r.stdout).get("streams", []):
                    tags = stream.get("tags", {})
                    lang = tags.get("language") or tags.get("LANGUAGE") or ""
                    if is_portuguese_lang(lang):
                        return "Y"
        except Exception: pass

    # Check internal subtitles
    for s in subs_internal:
        if is_portuguese_lang(s.get("lang", "")):
            return "Y"

    # Check external subtitle files
    for s in subs_external:
        if is_portuguese_lang(s.get("lang", "")):
            return "Y"

    return "N"


def extract_language_from_xml(filepath):
    if not filepath or not os.path.isfile(filepath): return "—"
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        m = re.search(r'<Language>([^<]+)</Language>', content)
        if m:
            lang = m.group(1).strip()
            return lang if lang else "Unknown"
        if '<Language></Language>' in content or '<Language />' in content:
            return "Unknown"
        return "—"
    except Exception: return "—"


def _is_url_only_nfo(content):
    s = content.strip()
    return '\n' not in s and s.startswith(('http://', 'https://'))


def validate_xml_file(filepath, is_nfo=False):
    errors = []
    if not os.path.isfile(filepath): return errors
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return [{"line": 0, "col": 0, "message": f"Cannot read: {e}"}]
    if not content.strip(): return [{"line": 1, "col": 0, "message": "File is empty"}]
    if is_nfo and _is_url_only_nfo(content): return errors
    if content.startswith('\ufeff'): content = content[1:]
    try:
        ET.fromstring(content)
    except ET.ParseError as e:
        line, col = e.position if hasattr(e, 'position') else (0, 0)
        raw_msg = str(e); src_lines = content.splitlines()
        if 0 < line <= len(src_lines):
            offending = src_lines[line - 1]
            if re.search(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', offending):
                raw_msg = "Unescaped '&' (should be '&amp;'). Common in scraper files — won't break KODI"
            elif "mismatched tag" in raw_msg:
                raw_msg = f"mismatched tag at line {line} — likely caused by a broken tag earlier"
        errors.append({"line": line, "col": col, "message": raw_msg})
    lines = content.splitlines()
    for ln, lt in enumerate(lines, 1):
        sl = lt.strip()
        if sl.startswith('<?') or sl.startswith('<!--'): continue
        for b in re.findall(r'<([A-Za-z_][\w.\-]*)(?=[^>]*(?:<|$))', lt):
            seg = lt[lt.index(f"<{b}"):]
            at = seg[1:]; nlt = at.find('<'); ngt = at.find('>')
            if ngt == -1 or (nlt != -1 and nlt < ngt):
                ml = False
                if ngt == -1:
                    for pk in range(ln, min(ln + 5, len(lines))):
                        pl = lines[pk]
                        if '>' in pl:
                            gp = pl.index('>'); lp = pl.find('<')
                            if lp == -1 or gp < lp: ml = True
                            break
                        if '<' in pl: break
                if not ml and not any(e["line"] == ln for e in errors):
                    errors.append({"line": ln, "col": lt.index(f"<{b}")+1,
                                   "message": f"Malformed tag '<{b}…' — missing '>'"})
        stripped = lt.rstrip()
        if re.search(r'</[A-Za-z_][\w.\-]*\s*$', stripped) and not stripped.endswith('>'):
            if not any(e["line"] == ln for e in errors):
                errors.append({"line": ln, "col": len(stripped),
                               "message": "Closing tag missing '>'"})
        for tn, _ in re.findall(r'<([A-Za-z_][\w.\-]*)(?:\s[^>]*)?>([^<]*)/\1>', lt):
            if not any(e["line"] == ln for e in errors):
                errors.append({"line": ln, "col": lt.index(f"/{tn}>") + 1,
                               "message": f"'/{tn}>' missing '<' — should be '</{tn}>'"})
    seen = set(); unique = []
    for e in errors:
        k = (e["line"], e["message"][:60])
        if k not in seen: seen.add(k); unique.append(e)
    unique.sort(key=lambda e: (e["line"], e["col"]))
    return unique


# ══════════════════════════════════════════════════════════════════════════════
# Scanning
# ══════════════════════════════════════════════════════════════════════════════

def scan_one_subfolder(sub_path, sub_name):
    poster_path  = os.path.join(sub_path, "poster.jpg")
    fanart_path  = os.path.join(sub_path, "fanart.jpg")
    folder_path  = os.path.join(sub_path, "folder.jpg")

    pe  = os.path.isfile(poster_path);  fe  = os.path.isfile(fanart_path)
    fle = os.path.isfile(folder_path)
    pb  = os.path.getsize(poster_path)  if pe  else 0
    fb  = os.path.getsize(fanart_path)  if fe  else 0
    flb = os.path.getsize(folder_path)  if fle else 0
    pd  = get_image_dimensions(poster_path)  if pe  else None
    fd  = get_image_dimensions(fanart_path)  if fe  else None
    fld = get_image_dimensions(folder_path)  if fle else None
    pc  = pe  and not is_valid_jpeg(poster_path)
    fc  = fe  and not is_valid_jpeg(fanart_path)
    flc = fle and not is_valid_jpeg(folder_path)

    bc, bp = count_backdrops(sub_path)

    nfo_path = os.path.join(sub_path, sub_name + ".nfo")
    ne  = os.path.isfile(nfo_path);  nb  = os.path.getsize(nfo_path) if ne else 0
    nerr = validate_xml_file(nfo_path, is_nfo=True) if ne else []

    xml_path = os.path.join(sub_path, "movie.xml")
    xe   = os.path.isfile(xml_path);  xb  = os.path.getsize(xml_path) if xe else 0
    xerr = validate_xml_file(xml_path, is_nfo=False) if xe else []
    lang = extract_language_from_xml(xml_path) if xe else "—"

    ns = (STATUS_ERROR if nerr else STATUS_OK) if ne else STATUS_MISSING
    xs = (STATUS_ERROR if xerr else STATUS_OK) if xe else STATUS_MISSING

    vi  = scan_video_files(sub_path)
    si  = scan_subtitles(sub_path, vi["video_path"])
    pt  = compute_pt_ok(vi["video_path"], si["subs_internal"], si["subs_external"])

    vs      = (STATUS_MISSING if vi["video_count"] == 0
               else STATUS_ERROR if vi["video_count"] > 1 else STATUS_OK)
    has_err = ns == STATUS_ERROR or xs == STATUS_ERROR or pc or fc or flc
    health  = ("red"    if has_err
               else "green" if pe and fe and fle and ns == STATUS_OK
                               and xs == STATUS_OK and vi["video_count"] == 1
               else "yellow")

    return {
        "subfolder": sub_name, "subfolder_path": sub_path,
        "poster_exists":  pe,  "poster_path":  poster_path,
        "poster_bytes":   pb,  "poster_size":  format_size(pb) if pe else "—",
        "poster_dim":     pd,  "poster_corrupt": pc,
        "fanart_exists":  fe,  "fanart_path":  fanart_path,
        "fanart_bytes":   fb,  "fanart_size":  format_size(fb) if fe else "—",
        "fanart_dim":     fd,  "fanart_corrupt": fc,
        "folder_exists":  fle, "folder_path":  folder_path,
        "folder_bytes":   flb, "folder_size":  format_size(flb) if fle else "—",
        "folder_dim":     fld, "folder_corrupt": flc,
        "backdrop_count": bc,  "backdrop_paths": bp,
        "nfo_exists":  ne,  "nfo_path":    nfo_path,
        "nfo_bytes":   nb,  "nfo_size":    format_size(nb) if ne else "—",
        "nfo_status":  ns,  "nfo_errors":  nerr,
        "xml_exists":  xe,  "xml_path":    xml_path,
        "xml_bytes":   xb,  "xml_size":    format_size(xb) if xe else "—",
        "xml_status":  xs,  "xml_errors":  xerr,
        "language": lang,
        "video_count":   vi["video_count"],   "video_files":   vi["video_files"],
        "video_ext":     vi["video_ext"],     "video_path":    vi["video_path"],
        "video_bytes":   vi["video_bytes"],   "video_size":    vi["video_size"],
        "video_width":   vi["video_width"],   "video_height":  vi["video_height"],
        "video_quality": vi["video_quality"], "video_status":  vs,
        "subs_internal": si["subs_internal"], "subs_external": si["subs_external"],
        "subs_summary":  si["subs_summary"],
        "pt_ok": pt,
        "row_health": health,
    }


# ── Serialise / deserialise results for JSON storage ─────────────────────────
def _results_to_json(results):
    """Convert scan results list to a JSON-safe list."""
    return results  # already plain dicts with strings/ints/lists


def _results_from_json(data):
    """Restore results from JSON (add any missing keys for forward compat)."""
    defaults = {
        "video_width": None, "video_height": None, "video_quality": "—",
        "pt_ok": "—", "backdrop_paths": [],
        "folder_exists": False, "folder_path": "", "folder_bytes": 0,
        "folder_size": "—", "folder_dim": None, "folder_corrupt": False,
    }
    out = []
    for r in data:
        row = dict(defaults)
        row.update(r)
        out.append(row)
    return out


# ── Sort options ──────────────────────────────────────────────────────────────
# Each entry: (primary_key_fn, reverse)
# Secondary sort is always subfolder A→Z (applied in _refresh_table)
SORT_OPTIONS = {
    "Subfolder (A→Z)":        (lambda r: r["subfolder"].lower(),   False),
    "Subfolder (Z→A)":        (lambda r: r["subfolder"].lower(),   True),
    "Poster size (lg→sm)":    (lambda r: r["poster_bytes"],        True),
    "Poster size (sm→lg)":    (lambda r: r["poster_bytes"],        False),
    "Fanart size (lg→sm)":    (lambda r: r["fanart_bytes"],        True),
    "Fanart size (sm→lg)":    (lambda r: r["fanart_bytes"],        False),
    "Video size (lg→sm)":     (lambda r: r["video_bytes"],         True),
    "Video size (sm→lg)":     (lambda r: r["video_bytes"],         False),
    "Language (A→Z)":         (lambda r: r["language"].lower(),    False),
    "Language (Z→A)":         (lambda r: r["language"].lower(),    True),
    "Quality (best first)":   (lambda r: _quality_sort_key(r["video_quality"]), False),
    "Quality (worst first)":  (lambda r: _quality_sort_key(r["video_quality"]), True),
    "PT OK? (Y first)":       (lambda r: r["pt_ok"],               False),
    "PT OK? (N first)":       (lambda r: r["pt_ok"],               True),
    "Backdrops (most)":       (lambda r: r["backdrop_count"],      True),
    "Backdrops (fewest)":     (lambda r: r["backdrop_count"],      False),
    "Health (errors 1st)":    (lambda r: {"red":0,"yellow":1,"green":2}[r["row_health"]], False),
    "Health (OK 1st)":        (lambda r: {"green":0,"yellow":1,"red":2}[r["row_health"]], False),
}


# ══════════════════════════════════════════════════════════════════════════════
# Frame Extraction with FFmpeg
# ══════════════════════════════════════════════════════════════════════════════

def get_video_duration(video_path):
    """Return video duration in seconds, or None on failure."""
    if not FFPROBE_PATH: return None
    try:
        r = subprocess.run(
            [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
             "-show_format", video_path],
            capture_output=True, text=True, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode == 0:
            return float(json.loads(r.stdout).get("format", {}).get("duration", 0))
    except Exception: pass
    return None


def extract_single_frame(video_path, time_sec, output_path, timeout_sec=60):
    """
    Extract one JPEG frame at time_sec.
    Returns (success: bool, error_msg: str).
    """
    if not FFMPEG_PATH: return False, "FFmpeg not found"
    try:
        r = subprocess.run(
            [FFMPEG_PATH, "-y", "-ss", str(time_sec), "-i", video_path,
             "-frames:v", "1", "-q:v", "1", output_path],
            capture_output=True, text=True, timeout=timeout_sec,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            return True, ""
        stderr_tail = (r.stderr or "")[-300:].strip()
        return False, stderr_tail or f"FFmpeg exit code {r.returncode}"
    except subprocess.TimeoutExpired:
        # Kill any orphaned ffmpeg process gracefully
        return False, f"Extraction timed out after {timeout_sec}s — file may be very large or corrupt"
    except Exception as e:
        return False, str(e)


class FrameExtractionDialog(tk.Toplevel):
    """Progress dialog for extracting 10 frames from a video."""

    def __init__(self, parent, video_path, sub_path, timeout_sec=60):
        super().__init__(parent)
        self.title("Extracting Frames…")
        self.geometry("520x300")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._video_path  = video_path
        self._sub_path    = sub_path
        self._timeout_sec = timeout_sec
        self._cancelled   = False
        self._extracted   = []

        tk.Label(self, text="🎬  Extracting backdrop frames…",
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#cdd6f4"
                 ).pack(pady=(16, 2))
        tk.Label(self, text=os.path.basename(video_path),
                 font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086").pack(pady=(0, 8))

        self.status_var = tk.StringVar(value="Preparing…")
        tk.Label(self, textvariable=self.status_var, font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#a6adc8", wraplength=480).pack()

        pf = tk.Frame(self, bg="#1e1e2e"); pf.pack(fill="x", padx=30, pady=(8, 4))
        self.pbar_canvas = tk.Canvas(pf, height=24, bg="#313244",
                                     highlightthickness=0, relief="flat")
        self.pbar_canvas.pack(fill="x")
        self._draw_progress(0)

        # Timeout setting
        tf2 = tk.Frame(self, bg="#1e1e2e"); tf2.pack(pady=(4, 0))
        tk.Label(tf2, text="Per-frame timeout (s):", font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        self._timeout_var = tk.IntVar(value=timeout_sec)
        tk.Spinbox(tf2, from_=10, to=300, textvariable=self._timeout_var,
                   width=5, font=("Helvetica", 9),
                   bg="#313244", fg="#cdd6f4", buttonbackground="#45475a",
                   relief="flat").pack(side="left", padx=(6, 0))

        tk.Button(self, text="  Cancel  ", font=("Helvetica", 10, "bold"),
                  bg="#f38ba8", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._on_cancel).pack(pady=(10, 16))

        self.after(150, self._start)

    def _draw_progress(self, pct):
        c = self.pbar_canvas; c.delete("all")
        w = c.winfo_width() or 460; h = 24
        c.create_rectangle(0, 0, w, h, fill="#313244", outline="")
        fw = int(w * pct / 100)
        if fw > 0:
            c.create_rectangle(0, 0, fw, h, fill="#2d6e3f", outline="")
        c.create_text(w // 2, h // 2, text=f"{pct}%",
                      fill="#cdd6f4", font=("Helvetica", 10, "bold"))

    def _on_cancel(self):
        self._cancelled = True
        self.status_var.set("Cancelling… (waiting for current frame to finish)")

    def _start(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        video    = self._video_path
        sub      = self._sub_path
        t_limit  = max(10, self._timeout_var.get())

        # ── Step 1: read duration ──────────────────────────────────────────────
        self.after(0, lambda: self.status_var.set("Reading video duration…"))
        duration = get_video_duration(video)

        if not duration or duration <= 0:
            self._finish_error(
                "Cannot read video duration",
                "FFmpeg/ffprobe could not determine the length of this video file.\n\n"
                "Possible causes:\n"
                "• The video file is corrupt or incomplete\n"
                "• The container format is not supported\n"
                "• The file is still being copied / downloaded\n\n"
                "Try opening the file in your media player to verify it plays correctly."
            )
            return

        # ── Step 2: choose timestamps ──────────────────────────────────────────
        if duration < 120:          # < 2 min — very short
            if duration < 20:
                self._finish_error(
                    "Video too short for extraction",
                    f"The video is only {duration:.0f} seconds long.\n"
                    "Backdrop extraction needs at least 20 seconds of content.\n\n"
                    "If this is unexpected, the file may be corrupt."
                )
                return
            start_sec = 2
            end_sec   = duration - 2
        elif duration < 600:        # 2–10 min
            start_sec = duration * 0.05
            end_sec   = duration * 0.95
        else:                       # > 10 min (typical movie)
            start_sec = 300
            end_sec   = duration - 300

        if end_sec <= start_sec:
            end_sec = duration * 0.9
            start_sec = duration * 0.1

        interval   = (end_sec - start_sec) / 9 if end_sec > start_sec else 1
        timestamps = [start_sec + i * interval for i in range(10)]

        start_num  = next_backdrop_number(sub)
        extracted  = []
        failed     = []

        # ── Step 3: extract frames ─────────────────────────────────────────────
        for i, ts in enumerate(timestamps):
            if self._cancelled:
                break

            num   = start_num + i
            fname = f"backdrop{num}.jpg"
            out_p = os.path.join(sub, fname)
            mins  = int(ts // 60); secs_r = int(ts % 60)

            self.after(0, lambda i=i, m=mins, s=secs_r, fn=fname:
                       (self.status_var.set(f"Frame {i+1}/10  at {m}:{s:02d}  →  {fn}"),
                        self._draw_progress(int(i / 10 * 100))))

            ok, err_msg = extract_single_frame(video, ts, out_p, timeout_sec=t_limit)

            if ok:
                extracted.append((fname, out_p))
            else:
                failed.append((i + 1, f"{mins}:{secs_r:02d}", fname, err_msg))

        self._extracted = [p for _, p in extracted]

        # ── Step 4: report result ──────────────────────────────────────────────
        if self._cancelled:
            for _, p in extracted:
                try: os.remove(p)
                except OSError: pass
            self.after(0, lambda: (
                self.status_var.set("Cancelled — extracted files removed."),
                messagebox.showinfo(
                    "Extraction Cancelled",
                    "Backdrop extraction was cancelled.\n"
                    "Any partially extracted files have been removed.",
                    parent=self),
                self.destroy()))
            return

        self.after(0, lambda: self._draw_progress(100))

        n_ok  = len(extracted)
        n_bad = len(failed)

        if n_bad == 0:
            msg = (f"✅  All 10 frames extracted successfully!\n\n"
                   f"Files saved to:\n{sub}\n\n"
                   f"backdrop{start_num}.jpg  →  backdrop{start_num + n_ok - 1}.jpg")
            self.after(0, lambda: (
                messagebox.showinfo("Extraction Complete", msg, parent=self),
                self.destroy()))
        elif n_ok == 0:
            detail = "\n".join(f"  Frame {fi} at {ts}: {em}" for fi, ts, _, em in failed[:5])
            msg = (f"❌  No frames could be extracted.\n\n"
                   f"All 10 attempts failed. Details:\n{detail}\n\n"
                   f"Possible causes:\n"
                   f"• The video codec is not supported by your FFmpeg build\n"
                   f"• The video file is corrupt or partially downloaded\n"
                   f"• Increase the per-frame timeout if the video is very large\n"
                   f"• Try playing the file in VLC to confirm it's readable")
            self.after(0, lambda: (
                messagebox.showerror("Extraction Failed", msg, parent=self),
                self.destroy()))
        else:
            detail = "\n".join(f"  Frame {fi} at {ts}: {em}" for fi, ts, _, em in failed[:3])
            msg = (f"⚠️  Partial extraction: {n_ok}/10 frames saved.\n\n"
                   f"Successfully extracted: backdrop{start_num}.jpg … "
                   f"(see folder for full list)\n\n"
                   f"Failed frames ({n_bad}):\n{detail}\n\n"
                   f"The saved frames are usable. Failed frames may indicate\n"
                   f"damaged sections in the video file.")
            self.after(0, lambda: (
                messagebox.showwarning("Partial Extraction", msg, parent=self),
                self.destroy()))

    def _finish_error(self, title, message):
        self.after(0, lambda: (
            messagebox.showerror(title, message, parent=self),
            self.destroy()))


# ══════════════════════════════════════════════════════════════════════════════
# Dialogs
# ══════════════════════════════════════════════════════════════════════════════

class SubtitleDialog(tk.Toplevel):
    def __init__(self, parent, name, data):
        super().__init__(parent)
        self.title(f"Subtitles — {name}"); self.geometry("640x420")
        self.configure(bg="#1e1e2e"); self.transient(parent); self.grab_set()
        tk.Label(self, text=f"Subtitles — {name}", font=("Helvetica", 13, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", padx=16, pady=(14, 2))
        if data["video_path"]:
            tk.Label(self, text=f"Video: {os.path.basename(data['video_path'])}",
                     font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086").pack(anchor="w", padx=16, pady=(0, 10))
        fr = tk.Frame(self, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        t  = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4",
                     font=("Consolas", 10), relief="flat", padx=10, pady=10)
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        for tag, fg_c, bold in [("h","#89b4fa",True),("l","#a6e3a1",False),
                                 ("d","#a6adc8",False),("s","#45475a",False),("n","#f38ba8",False)]:
            kw = {"foreground": fg_c}
            if bold: kw["font"] = ("Consolas", 10, "bold")
            t.tag_configure(tag, **kw)
        t.insert("end", "  EMBEDDED SUBTITLES", "h")
        t.insert("end", f"  {'(via ffprobe)' if FFPROBE_PATH else '(ffprobe not found)'}\n",
                 "d" if FFPROBE_PATH else "n")
        if data["subs_internal"]:
            for i, s in enumerate(data["subs_internal"], 1):
                tl = f'  "{s["title"]}"' if s["title"] else ""
                t.insert("end", f"    {i}. ", "d")
                t.insert("end", s["lang"], "l")
                t.insert("end", f"{tl}\n", "d")
        elif FFPROBE_PATH: t.insert("end", "    None found\n", "n")
        t.insert("end", "\n  " + "─"*50 + "\n\n", "s")
        t.insert("end", "  EXTERNAL FILES\n", "h")
        if data["subs_external"]:
            for i, s in enumerate(data["subs_external"], 1):
                t.insert("end", f"    {i}. ", "d")
                t.insert("end", s["lang"], "l")
                t.insert("end", f'  →  {s["file"]}\n', "d")
        else: t.insert("end", "    None found\n", "n")
        t.configure(state="disabled")
        tk.Button(self, text="  Close  ", font=("Helvetica", 10, "bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self.destroy).pack(pady=(4, 14))


class ErrorDialog(tk.Toplevel):
    def __init__(self, parent, title, filepath, errors):
        super().__init__(parent)
        self.title(title); self.geometry("740x440"); self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        tk.Label(self, text=title, font=("Helvetica", 13, "bold"),
                 bg="#1e1e2e", fg="#f38ba8").pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(self, text=filepath, font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086",
                 wraplength=700, justify="left").pack(anchor="w", padx=16, pady=(0, 10))
        fr = tk.Frame(self, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        t  = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4",
                     font=("Consolas", 10), relief="flat", padx=10, pady=10)
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        t.tag_configure("eh", foreground="#f38ba8", font=("Consolas", 10, "bold"))
        t.tag_configure("ed", foreground="#fab387")
        t.tag_configure("sl", foreground="#a6adc8")
        t.tag_configure("sp", foreground="#45475a")
        sl = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                sl = f.readlines()
        except Exception: pass
        for i, e in enumerate(errors, 1):
            loc = f"Line {e['line']}" + (f", Col {e['col']}" if e["col"] else "")
            t.insert("end", f"  Error {i}:  ", "eh")
            t.insert("end", f"{loc}\n", "ed")
            t.insert("end", f"    {e['message']}\n", "ed")
            if 0 < e["line"] <= len(sl):
                t.insert("end", f"    → {sl[e['line']-1].rstrip()}\n", "sl")
            if i < len(errors):
                t.insert("end", "    " + "─"*60 + "\n", "sp")
        t.configure(state="disabled")
        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(4, 14))
        tk.Button(bf, text="  Open in editor  ", font=("Helvetica", 10, "bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=lambda: os_open(filepath)).pack(side="left", padx=(0, 8))
        tk.Button(bf, text="  Close  ", font=("Helvetica", 10, "bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self.destroy).pack(side="left")


class HelpDialog(tk.Toplevel):
    """Three-tab Help dialog: System Help, FFmpeg Help, About."""

    _SYSTEM_HELP = """\
What is Media and Metadata Clinic?

Media and Metadata Clinic is a tool designed to help you keep your movie library organised and healthy. It scans a root folder and looks inside each subfolder (which typically represents one movie or show) to check whether all the artwork and metadata files are present, correct, and complete.

What does it check?

For each subfolder it will verify:
  • poster.jpg    — the cover image used by KODI and other media players
  • folder.jpg    — an alternative cover image
  • fanart.jpg    — the wide background image
  • backdrop files — extracted video frames used as scene backgrounds
  • .nfo file     — the metadata file that KODI reads for titles, ratings, cast, etc.
  • movie.xml     — a supplementary metadata file
  • Video file    — whether exactly one video is present, and its size and quality
  • Subtitles     — both embedded (inside the video) and external subtitle files
  • PT OK?        — whether the content can be watched in Portuguese (audio or subtitle)

How do I use it?

  1. Click Browse… and select your root media folder.
  2. Click Scan to analyse all subfolders. Results appear in the table.
  3. Rows are colour-coded: green = all OK, yellow = something missing, red = errors found.
  4. Double-click any cell to open the corresponding file or folder.
  5. Right-click a row for more options, including backdrop frame extraction.
  6. Use Sort to reorder results by any column.
  7. Use Export CSV to save a full report.
  8. Click Update Scan to refresh the last scanned folder without browsing again.

Your last scan is automatically saved and reloaded next time you open the app.
"""

    _FFMPEG_HELP = """\
Why does this app need FFmpeg?

FFmpeg is a free and open-source multimedia tool. This app uses it for two things:

  1. Reading video information  — FFmpeg's companion tool "ffprobe" reads the video
     file to find its duration, resolution, and embedded subtitle tracks.

  2. Extracting backdrop frames — FFmpeg can pull a still image from any point in a
     video and save it as a JPEG. This is how the "Extract Frames" button works —
     it captures 10 frames spread across the movie and saves them as backdrop files
     (backdrop.jpg, backdrop1.jpg, …) in the same folder as the video.

Without FFmpeg:
  • Video resolution and quality (1080p, 4K, etc.) will not be detected.
  • Embedded subtitle tracks will not be listed.
  • The "Extract Frames" button will be disabled.

How to install FFmpeg on Windows:

  1. Go to  https://ffmpeg.org/download.html
  2. Under "Windows builds", click "Windows builds by BtbN" or "gyan.dev".
  3. Download the "ffmpeg-release-essentials.zip" (or similar full build).
  4. Extract the ZIP to a permanent folder, e.g.:  C:\\Tools\\ffmpeg\\
  5. Inside that folder you should find a "bin" subfolder containing
     ffmpeg.exe and ffprobe.exe.
  6. Back in this app, click "Set path" (or click the "FFmpeg ✗" label) and
     point it to that "bin" folder.
  7. The status indicator will turn green once both tools are verified.

Tip: If ffmpeg is already installed and in your system PATH, the app will find
it automatically — no manual path needed.
"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title(f"Help — {APP_NAME}")
        self.geometry("720x540")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(True, True)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        style = ttk.Style()
        style.configure("TNotebook",        background="#1e1e2e", borderwidth=0)
        style.configure("TNotebook.Tab",    background="#313244", foreground="#cdd6f4",
                        padding=[12, 6], font=("Helvetica", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", "#45475a")],
                  foreground=[("selected", "#89b4fa")])

        self._add_tab(nb, "📖  System Help", self._SYSTEM_HELP)
        self._add_tab(nb, "🔧  FFmpeg Help", self._FFMPEG_HELP)
        self._add_about_tab(nb)

        tk.Button(self, text="  Close  ", font=("Helvetica", 10, "bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self.destroy).pack(pady=(6, 12))

    def _add_tab(self, nb, label, text):
        frame = tk.Frame(nb, bg="#1e1e2e"); nb.add(frame, text=label)
        t  = tk.Text(frame, wrap="word", bg="#313244", fg="#cdd6f4",
                     font=("Helvetica", 10), relief="flat", padx=14, pady=12,
                     spacing1=2, spacing3=2)
        sb = ttk.Scrollbar(frame, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        t.insert("end", text); t.configure(state="disabled")

    def _add_about_tab(self, nb):
        frame = tk.Frame(nb, bg="#1e1e2e"); nb.add(frame, text="ℹ️  About")
        about_text = (
            f"{APP_NAME}\n"
            f"Version {APP_VERSION}\n\n"
            f"Created by:  {APP_AUTHOR}\n"
            f"Contact:     {APP_EMAIL}\n\n"
            "─────────────────────────────────────────\n\n"
            "Media and Metadata Clinic helps you keep your\n"
            "media library artwork and metadata clean,\n"
            "complete, and KODI-ready.\n\n"
            "─────────────────────────────────────────\n\n"
            "VERSION HISTORY\n\n"
            "  v0.7.0  — Current release\n"
            "             Full rewrite: quality column, PT OK?,\n"
            "             persistent sessions, improved extraction,\n"
            "             FFmpeg validation, Help system, and more.\n\n"
            "  v0.6.x  — Previous release (folder_scanner_v6)\n\n"
            "─────────────────────────────────────────\n\n"
            "This software is provided free of charge.\n"
            "Feedback and bug reports welcome at:\n"
            f"  {APP_EMAIL}\n"
        )
        lbl = tk.Label(frame, text=about_text, font=("Helvetica", 11),
                       bg="#1e1e2e", fg="#cdd6f4", justify="left",
                       anchor="nw", padx=24, pady=20)
        lbl.pack(fill="both", expand=True)
        # Make email clickable
        email_lbl = tk.Label(frame, text="", bg="#1e1e2e")
        email_lbl.pack()


# ══════════════════════════════════════════════════════════════════════════════
# Tooltip
# ══════════════════════════════════════════════════════════════════════════════

class TreeviewTooltip:
    def __init__(self, tree, fn):
        self.tree = tree; self.fn = fn; self.tw = None; self._lc = (None, None)
        tree.bind("<Motion>", self._m); tree.bind("<Leave>", self._h)

    def _m(self, e):
        i = self.tree.identify_row(e.y); c = self.tree.identify_column(e.x)
        if not i or not c: self._h(); return
        if (i, c) == self._lc: return
        self._lc = (i, c); t = self.fn(i, int(c.lstrip("#")) - 1)
        if t: self._s(e, t)
        else: self._h()

    def _s(self, e, t):
        self._h()
        self.tw = w = tk.Toplevel(self.tree); w.wm_overrideredirect(True)
        w.wm_geometry(f"+{e.x_root+16}+{e.y_root+10}"); w.configure(bg="#45475a")
        tk.Label(w, text=t, bg="#45475a", fg="#cdd6f4",
                 font=("Consolas", 9, "bold"), padx=8, pady=4).pack()

    def _h(self, e=None):
        if self.tw: self.tw.destroy(); self.tw = None
        self._lc = (None, None)


# ══════════════════════════════════════════════════════════════════════════════
# Main Application
# ══════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"🎬  {APP_NAME}  v{APP_VERSION}")
        self.geometry("1560x740"); self.minsize(1200, 560)
        self.configure(bg="#1e1e2e")
        self._item_map    = {}
        self._results     = []
        self._folder      = None
        self._scanning    = False
        self._cancel_scan = False
        self._wrap_on     = tk.BooleanVar(value=SETTINGS.get("wrap_columns", False))
        self._build_ui()
        self._update_extract_btn_state()
        # Auto-restore last session
        self.after(200, self._restore_last_session)

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header row ──────────────────────────────────────────────────────
        header = tk.Frame(self, bg="#1e1e2e")
        header.pack(fill="x", padx=20, pady=(16, 4))

        tk.Label(header, text=f"🎬  {APP_NAME}",
                 font=("Helvetica", 17, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(side="left")

        # Right side: Help + FFmpeg status
        right_hdr = tk.Frame(header, bg="#1e1e2e"); right_hdr.pack(side="right")
        tk.Button(right_hdr, text=" ❓ Help ", font=("Helvetica", 9, "bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=lambda: HelpDialog(self)
                  ).pack(side="left", padx=(0, 12))

        self._ff_frame = tk.Frame(right_hdr, bg="#1e1e2e")
        self._ff_frame.pack(side="left")
        self._build_ffmpeg_status(self._ff_frame)

        # ── Picker row ───────────────────────────────────────────────────────
        picker = tk.Frame(self, bg="#1e1e2e"); picker.pack(fill="x", padx=20, pady=(0, 6))
        self.folder_var = tk.StringVar(value="No folder selected")
        tk.Label(picker, textvariable=self.folder_var,
                 font=("Helvetica", 10), bg="#313244", fg="#a6adc8",
                 anchor="w", padx=10, pady=6, relief="flat"
                 ).pack(side="left", fill="x", expand=True, ipady=2)

        btn_kw = dict(font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2")
        tk.Button(picker, text="  Browse…  ",   bg="#89b4fa", fg="#1e1e2e",
                  command=self._browse, **btn_kw).pack(side="left", padx=(8, 0))
        self.scan_btn = tk.Button(picker, text="  Scan  ",   bg="#a6e3a1", fg="#1e1e2e",
                                  command=self._scan, **btn_kw)
        self.scan_btn.pack(side="left", padx=(6, 0))
        self.update_btn = tk.Button(picker, text="  Update Scan  ", bg="#89dceb", fg="#1e1e2e",
                                    command=self._update_scan, **btn_kw)
        self.update_btn.pack(side="left", padx=(6, 0))
        self.cancel_btn = tk.Button(picker, text="  Cancel  ", bg="#f38ba8", fg="#1e1e2e",
                                    command=self._cancel, **btn_kw)
        self.extract_btn = tk.Button(picker, text="  Extract Frames  ", bg="#fab387",
                                     fg="#1e1e2e", command=self._extract_frames, **btn_kw)
        self.extract_btn.pack(side="left", padx=(6, 0))
        tk.Button(picker, text="  Export CSV  ", bg="#cba6f7", fg="#1e1e2e",
                  command=self._export_csv, **btn_kw).pack(side="left", padx=(6, 0))

        # ── Sort + wrap toggle row ───────────────────────────────────────────
        sr = tk.Frame(self, bg="#1e1e2e"); sr.pack(fill="x", padx=20, pady=(0, 2))
        tk.Label(sr, text="Sort:", font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        self.sort_var = tk.StringVar(value=SETTINGS.get("sort_option", "Subfolder (A→Z)"))
        sm = ttk.Combobox(sr, textvariable=self.sort_var,
                          values=list(SORT_OPTIONS.keys()),
                          state="readonly", width=28, font=("Helvetica", 10))
        sm.pack(side="left", padx=(6, 0))
        sm.bind("<<ComboboxSelected>>", lambda _: self._refresh_table())

        tk.Checkbutton(sr, text="Wrap text", variable=self._wrap_on,
                       command=self._toggle_wrap,
                       font=("Helvetica", 9), bg="#1e1e2e", fg="#a6adc8",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left", padx=(16, 0))

        # Legend
        lg = tk.Frame(sr, bg="#1e1e2e"); lg.pack(side="right")
        for c, lbl in [("#a6e3a1","All OK"),("#f9e2af","Missing"),("#f38ba8","Errors")]:
            tk.Label(lg, text="■", font=("Helvetica", 12), bg="#1e1e2e", fg=c
                     ).pack(side="left", padx=(10, 0))
            tk.Label(lg, text=lbl, font=("Helvetica", 9), bg="#1e1e2e", fg="#a6adc8"
                     ).pack(side="left", padx=(2, 0))

        # ── Progress bar ─────────────────────────────────────────────────────
        self.progress_frame = tk.Frame(self, bg="#1e1e2e")
        self.progress_frame.pack(fill="x", padx=20, pady=(0, 2))
        self.pbar_canvas = tk.Canvas(self.progress_frame, height=22,
                                     bg="#313244", highlightthickness=0)
        self.pbar_label  = tk.Label(self.progress_frame, text="",
                                    font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086")

        # ── Stats ─────────────────────────────────────────────────────────────
        self.stats_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.stats_var,
                 font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086"
                 ).pack(anchor="w", padx=22)

        # ── Table ─────────────────────────────────────────────────────────────
        tf = tk.Frame(self, bg="#1e1e2e")
        tf.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        style = ttk.Style(self); style.theme_use("clam")
        style.configure("Treeview", background="#313244", foreground="#cdd6f4",
                        fieldbackground="#313244", rowheight=26,
                        font=("Helvetica", 10))
        style.configure("Treeview.Heading", background="#45475a", foreground="#89b4fa",
                        font=("Helvetica", 10, "bold"), relief="flat")
        style.map("Treeview",
                  background=[("selected", "#585b70")],
                  foreground=[("selected", "#cdd6f4")])

        cols = ("subfolder","poster","poster_sz","folder","folder_sz",
                "fanart","fanart_sz","backdrops","nfo","nfo_ok","xml","xml_ok",
                "language","vid_ext","vid_size","quality","pt_ok","subs")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="browse")

        # column id, header label, default width, anchor, stretch
        col_defs = [
            ("subfolder", "Subfolder",   240, "w",      True),
            ("poster",    "Poster",       56, "center", False),
            ("poster_sz", "Size",         72, "center", False),
            ("folder",    "Folder",       56, "center", False),
            ("folder_sz", "Size",         72, "center", False),
            ("fanart",    "Fanart",       56, "center", False),
            ("fanart_sz", "Size",         72, "center", False),
            ("backdrops", "Bkdrps",       52, "center", False),
            ("nfo",       ".nfo",         44, "center", False),
            ("nfo_ok",    "OK?",          40, "center", False),
            ("xml",       ".xml",         44, "center", False),
            ("xml_ok",    "OK?",          40, "center", False),
            ("language",  "Language",     82, "center", False),
            ("vid_ext",   "Video",        52, "center", False),
            ("vid_size",  "Vid Size",     74, "center", False),
            ("quality",   "Quality",      74, "center", False),
            ("pt_ok",     "PT OK?",       58, "center", False),
            ("subs",      "Subtitles",   180, "w",      True),
        ]
        for cid, h, w, a, s in col_defs:
            self.tree.heading(cid, text=h,
                              command=lambda c=cid: self._header_click(c))
            self.tree.column(cid, width=w, anchor=a, stretch=s, minwidth=30)

        for t in ["green","green_odd","yellow","yellow_odd","red","red_odd"]:
            bg = {"green":"#1e3a2f","green_odd":"#243d33",
                  "yellow":"#3a351e","yellow_odd":"#3d3824",
                  "red":"#3a1e1e","red_odd":"#3d2424"}[t]
            self.tree.tag_configure(t, background=bg)

        vsb = ttk.Scrollbar(tf, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tf.rowconfigure(0, weight=1); tf.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>",  self._dblclick)
        self.tree.bind("<Button-3>",  self._rclick)
        self.tree.bind("<Button-2>",  self._rclick)
        # Keyboard navigation
        for key in ("<Prior>","<Next>","<Home>","<End>"):
            self.tree.bind(key, self._kb_navigate)

        self._ctx = tk.Menu(self, tearoff=0, bg="#313244", fg="#cdd6f4",
                            activebackground="#585b70", activeforeground="#cdd6f4",
                            font=("Helvetica", 10))
        TreeviewTooltip(self.tree, self._tooltip)

    # ── Column auto-resize on header double-click ─────────────────────────────
    def _header_click(self, col_id):
        """Double-clicking a column header auto-sizes that column."""
        # We use a flag approach: single click does nothing special;
        # double-click auto-sizes. Bind only double-1 on the headings region.
        pass  # placeholder — actual double-click handled in _dblclick_header

    def _auto_size_column(self, col_id):
        """Set column width to fit the longest visible value (like Excel double-click)."""
        font_obj = tk.font.Font(font=("Helvetica", 10))
        heading  = self.tree.heading(col_id)["text"]
        max_w    = font_obj.measure(heading) + 20

        for iid in self.tree.get_children():
            vals  = self.tree.item(iid, "values")
            cols  = self.tree["columns"]
            try:
                idx = list(cols).index(col_id)
                cell_text = str(vals[idx]) if idx < len(vals) else ""
                w = font_obj.measure(cell_text) + 20
                if w > max_w:
                    max_w = w
            except (ValueError, IndexError):
                pass

        self.tree.column(col_id, width=min(max_w, 600))

    # ── Keyboard navigation in table ─────────────────────────────────────────
    def _kb_navigate(self, event):
        children = self.tree.get_children()
        if not children: return
        sel = self.tree.selection()
        if not sel:
            first = children[0]
            self.tree.selection_set(first)
            self.tree.see(first)
            return

        cur_idx = list(children).index(sel[0])
        key = event.keysym

        if key == "Prior":    # Page Up
            new_idx = max(0, cur_idx - 20)
        elif key == "Next":   # Page Down
            new_idx = min(len(children) - 1, cur_idx + 20)
        elif key == "Home":
            new_idx = 0
        elif key == "End":
            new_idx = len(children) - 1
        else:
            return

        target = children[new_idx]
        self.tree.selection_set(target)
        self.tree.see(target)
        return "break"

    # ── Wrap toggle ───────────────────────────────────────────────────────────
    def _toggle_wrap(self):
        SETTINGS["wrap_columns"] = self._wrap_on.get()
        _save_settings(SETTINGS)
        self._apply_wrap()

    def _apply_wrap(self):
        """Apply or remove word-wrap to all columns except Subtitles."""
        # Treeview doesn't natively support cell wrapping;
        # we simulate it by adjusting row height and truncating text is not possible.
        # What we CAN do: toggle the row height between normal and taller,
        # and use the 'wrap' style for text columns (subfolder only, not subs).
        # For a true wrap effect in Tkinter Treeview, a custom renderer is needed.
        # Best achievable: increase row height when wrap is on so
        # wrapped-looking text (via \n inserted) can show. We insert \n in cell values.
        if self._wrap_on.get():
            style = ttk.Style()
            style.configure("Treeview", rowheight=48)
        else:
            style = ttk.Style()
            style.configure("Treeview", rowheight=26)
        self._refresh_table()

    def _wrap_text(self, text, col_id, max_chars=25):
        """Insert newlines to simulate wrapping. Skip for 'subs' column."""
        if col_id == "subs": return text
        if not self._wrap_on.get(): return text
        if len(text) <= max_chars: return text
        # Simple greedy word wrap
        words  = text.split()
        lines  = []; line = ""
        for w in words:
            if len(line) + len(w) + 1 <= max_chars:
                line = (line + " " + w).strip()
            else:
                if line: lines.append(line)
                line = w
        if line: lines.append(line)
        return "\n".join(lines)

    # ── FFmpeg status bar ─────────────────────────────────────────────────────
    def _build_ffmpeg_status(self, parent):
        for w in parent.winfo_children():
            w.destroy()

        ff_ok, fp_ok, ff_msg, fp_msg = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)

        if ff_ok and fp_ok:
            # Both working — green
            lbl = tk.Label(parent, text="FFmpeg ✓", font=("Helvetica", 9, "bold"),
                           bg="#1e1e2e", fg="#a6e3a1", cursor="hand2")
            lbl.pack(side="left")
            self._ff_tip = None
            ff_dir = os.path.dirname(FFMPEG_PATH)
            def _show(e):
                self._ff_tip = tw = tk.Toplevel(parent); tw.wm_overrideredirect(True)
                tw.wm_geometry(f"+{e.x_root+10}+{e.y_root+15}"); tw.configure(bg="#45475a")
                tk.Label(tw, text=f"Path: {ff_dir}\nClick to change path",
                         bg="#45475a", fg="#cdd6f4", font=("Consolas", 9), padx=8, pady=4).pack()
            def _hide(e):
                if self._ff_tip: self._ff_tip.destroy(); self._ff_tip = None
            lbl.bind("<Enter>", _show); lbl.bind("<Leave>", _hide)
            lbl.bind("<Button-1>", lambda e: self._set_ffmpeg_path())
        else:
            # Partial or full failure
            if not ff_ok and not fp_ok:
                status_text = "FFmpeg ✗"; fg = "#f38ba8"
                detail = "Neither ffmpeg nor ffprobe could be found or run."
            elif not ff_ok:
                status_text = "ffmpeg ✗"; fg = "#fab387"
                detail = f"ffmpeg issue: {ff_msg}"
            else:
                status_text = "ffprobe ✗"; fg = "#fab387"
                detail = f"ffprobe issue: {fp_msg}"

            tk.Label(parent, text=status_text, font=("Helvetica", 9, "bold"),
                     bg="#1e1e2e", fg=fg).pack(side="left", padx=(0, 4))
            if detail:
                tip_lbl = tk.Label(parent, text="ⓘ", font=("Helvetica", 9),
                                   bg="#1e1e2e", fg="#6c7086", cursor="hand2")
                tip_lbl.pack(side="left", padx=(0, 6))
                self._ff_detail_tip = None
                def _show_detail(e, d=detail):
                    self._ff_detail_tip = tw = tk.Toplevel(parent)
                    tw.wm_overrideredirect(True)
                    tw.wm_geometry(f"+{e.x_root+10}+{e.y_root+15}")
                    tw.configure(bg="#45475a")
                    tk.Label(tw, text=d, bg="#45475a", fg="#cdd6f4",
                             font=("Consolas", 9), padx=8, pady=4,
                             wraplength=320, justify="left").pack()
                def _hide_detail(e):
                    if self._ff_detail_tip: self._ff_detail_tip.destroy(); self._ff_detail_tip = None
                tip_lbl.bind("<Enter>", _show_detail)
                tip_lbl.bind("<Leave>", _hide_detail)

            tk.Button(parent, text="Set path", font=("Helvetica", 8),
                      bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                      command=self._set_ffmpeg_path).pack(side="left", padx=(0, 4))
            tk.Button(parent, text="Download", font=("Helvetica", 8),
                      bg="#45475a", fg="#89b4fa", relief="flat", cursor="hand2",
                      command=lambda: webbrowser.open("https://ffmpeg.org/download.html")
                      ).pack(side="left", padx=(0, 4))

    def _set_ffmpeg_path(self):
        path = filedialog.askdirectory(title="Select folder containing ffmpeg / ffprobe")
        if not path: return
        ff = (os.path.join(path, "ffmpeg.exe") if os.name == "nt"
              else os.path.join(path, "ffmpeg"))
        if not os.path.isfile(ff):
            ff = os.path.join(path, "ffmpeg")   # try without extension
        if not os.path.isfile(ff):
            messagebox.showerror("Not found",
                                 f"ffmpeg executable not found in:\n{path}\n\n"
                                 "Make sure you select the folder that contains "
                                 "ffmpeg.exe and ffprobe.exe.")
            return
        SETTINGS["ffmpeg_path"] = path
        _save_settings(SETTINGS)
        refresh_ffmpeg_paths()

        ff_ok, fp_ok, ff_msg, fp_msg = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
        if ff_ok and fp_ok:
            self._build_ffmpeg_status(self._ff_frame)
            self._update_extract_btn_state()
            messagebox.showinfo("FFmpeg Ready",
                                f"✅  Both ffmpeg and ffprobe are working correctly.\n\nPath: {path}")
        else:
            self._build_ffmpeg_status(self._ff_frame)
            self._update_extract_btn_state()
            issues = []
            if not ff_ok: issues.append(f"ffmpeg: {ff_msg}")
            if not fp_ok: issues.append(f"ffprobe: {fp_msg}")
            messagebox.showwarning("FFmpeg Issue",
                                   f"The path was saved, but there are problems:\n\n"
                                   + "\n".join(issues) +
                                   "\n\nPlease ensure you have a complete, working FFmpeg build.")

    def _update_extract_btn_state(self):
        """Grey out Extract Frames when FFmpeg is not available or broken."""
        ff_ok, fp_ok, _, _ = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
        if ff_ok and fp_ok:
            self.extract_btn.configure(state="normal", bg="#fab387",
                                       cursor="hand2", fg="#1e1e2e")
        else:
            self.extract_btn.configure(state="disabled", bg="#45475a",
                                       cursor="", fg="#6c7086")

    # ── Tooltip ───────────────────────────────────────────────────────────────
    def _tooltip(self, iid, ci):
        d = self._item_map.get(iid)
        if not d: return None
        if ci == COL_POSTER_SZ  and d["poster_exists"]  and d["poster_dim"]:
            return f"Dimensions: {d['poster_dim']}"
        if ci == COL_FOLDER_SZ  and d["folder_exists"]  and d["folder_dim"]:
            return f"Dimensions: {d['folder_dim']}"
        if ci == COL_FANART_SZ  and d["fanart_exists"]  and d["fanart_dim"]:
            return f"Dimensions: {d['fanart_dim']}"
        if ci == COL_QUALITY and d.get("video_width"):
            return f"{d['video_width']}×{d['video_height']} px"
        if ci == COL_PT_OK:
            v = d.get("pt_ok", "—")
            if v == "Y":  return "Portuguese audio or subtitle available"
            if v == "N":  return "No Portuguese audio or subtitle found"
            return "No video — cannot determine"
        return None

    # ── Double-click ──────────────────────────────────────────────────────────
    def _dblclick(self, e):
        if self._scanning: return
        # Check if click is on header region (row == "")
        region = self.tree.identify_region(e.x, e.y)
        if region == "heading":
            col_id = self.tree.identify_column(e.x)
            if col_id:
                # Convert "#N" → column id string
                cols = self.tree["columns"]
                idx  = int(col_id.lstrip("#")) - 1
                if 0 <= idx < len(cols):
                    import tkinter.font as tk_font  # noqa
                    self._auto_size_column_by_idx(cols[idx])
            return

        iid = self.tree.identify_row(e.y); cid = self.tree.identify_column(e.x)
        if not iid or not cid: return
        ci  = int(cid.lstrip("#")) - 1; d = self._item_map.get(iid)
        if not d: return

        if ci in (COL_POSTER, COL_POSTER_SZ):
            os_open(d["poster_path"]) if d["poster_exists"] else messagebox.showinfo("Missing","poster.jpg not found.")
        elif ci in (COL_FOLDER, COL_FOLDER_SZ):
            os_open(d["folder_path"]) if d["folder_exists"] else messagebox.showinfo("Missing","folder.jpg not found.")
        elif ci in (COL_FANART, COL_FANART_SZ):
            os_open(d["fanart_path"]) if d["fanart_exists"] else messagebox.showinfo("Missing","fanart.jpg not found.")
        elif ci == COL_BACKDROPS:
            os_open(d["backdrop_paths"][0]) if d["backdrop_count"] > 0 else messagebox.showinfo("Missing","No backdrops.")
        elif ci in (COL_NFO, COL_NFO_OK):
            if not d["nfo_exists"]:   messagebox.showinfo("Missing", f"Expected: {os.path.basename(d['nfo_path'])}")
            elif d["nfo_errors"]:     ErrorDialog(self, f"NFO Errors — {d['subfolder']}", d["nfo_path"], d["nfo_errors"])
            else:                     os_open(d["nfo_path"])
        elif ci in (COL_XML, COL_XML_OK):
            if not d["xml_exists"]:   messagebox.showinfo("Missing","movie.xml not found.")
            elif d["xml_errors"]:     ErrorDialog(self, f"XML Errors — {d['subfolder']}", d["xml_path"], d["xml_errors"])
            else:                     os_open(d["xml_path"])
        elif ci == COL_LANGUAGE:
            if d["xml_exists"]: os_open(d["xml_path"])
        elif ci in (COL_VID_EXT, COL_VID_SIZE, COL_QUALITY):
            os_open(d["video_path"]) if d["video_path"] else messagebox.showinfo("Missing","No video.")
        elif ci == COL_SUBS:
            SubtitleDialog(self, d["subfolder"], d)
        elif ci == COL_SUBFOLDER:
            os_open(d["subfolder_path"])

    def _auto_size_column_by_idx(self, col_id):
        """Auto-size a column to fit its content (Excel-style double-click)."""
        import tkinter.font as tk_font
        font_obj = tk_font.Font(font=("Helvetica", 10))
        hdr_text = self.tree.heading(col_id)["text"]
        max_w    = font_obj.measure(hdr_text) + 24
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, "values")
            cols = list(self.tree["columns"])
            try:
                idx = cols.index(col_id)
                cell = str(vals[idx]) if idx < len(vals) else ""
                # Only measure first line if wrapped
                cell = cell.split("\n")[0]
                w = font_obj.measure(cell) + 24
                if w > max_w:
                    max_w = w
            except (ValueError, IndexError):
                pass
        self.tree.column(col_id, width=min(max_w, 800))

    # ── Right-click context menu ───────────────────────────────────────────────
    def _rclick(self, e):
        if self._scanning: return
        iid = self.tree.identify_row(e.y)
        if not iid: return
        self.tree.selection_set(iid); d = self._item_map.get(iid)
        if not d: return
        m = self._ctx; m.delete(0, "end")
        m.add_command(label="📂  Open subfolder", command=lambda: os_open(d["subfolder_path"]))
        m.add_separator()
        for lb, ke, kp in [("🖼 poster","poster_exists","poster_path"),
                            ("🖼 folder","folder_exists","folder_path"),
                            ("🖼 fanart","fanart_exists","fanart_path")]:
            if d[ke]: p = d[kp]; m.add_command(label=lb, command=lambda p=p: os_open(p))
            else:     m.add_command(label=lb + " (missing)", state="disabled")
        if d["backdrop_count"]:
            m.add_command(label=f"🖼  Backdrops ({d['backdrop_count']})",
                          command=lambda: os_open(d["backdrop_paths"][0]))
        m.add_separator()
        if d["video_path"]:
            m.add_command(label="🎬 Play video", command=lambda: os_open(d["video_path"]))
            ff_ok, fp_ok, _, _ = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
            if ff_ok:
                m.add_command(label="🎞️  Extract 10 backdrop frames",
                              command=lambda: self._do_extract(d))
        else:
            m.add_command(label="🎬 Video (missing)", state="disabled")
        if d["subs_internal"] or d["subs_external"]:
            m.add_command(label="💬 Subtitles…", command=lambda: SubtitleDialog(self, d["subfolder"], d))
        m.add_separator()
        if d["nfo_exists"]:
            m.add_command(label="📝 .nfo", command=lambda: os_open(d["nfo_path"]))
            if d["nfo_errors"]:
                m.add_command(label=f"⚠️ NFO errors ({len(d['nfo_errors'])})",
                              command=lambda: ErrorDialog(self, f"NFO — {d['subfolder']}", d["nfo_path"], d["nfo_errors"]))
        if d["xml_exists"]:
            m.add_command(label="📝 movie.xml", command=lambda: os_open(d["xml_path"]))
            if d["xml_errors"]:
                m.add_command(label=f"⚠️ XML errors ({len(d['xml_errors'])})",
                              command=lambda: ErrorDialog(self, f"XML — {d['subfolder']}", d["xml_path"], d["xml_errors"]))
        m.add_separator()
        m.add_command(label="🔄 Re-validate", command=lambda: self._reval(iid, d))
        m.tk_popup(e.x_root, e.y_root)

    def _reval(self, iid, data):
        sp, sn = data["subfolder_path"], data["subfolder"]
        if not os.path.isdir(sp): messagebox.showerror("Error","Folder gone."); return
        r = scan_one_subfolder(sp, sn); self._item_map[iid] = r
        for i, o in enumerate(self._results):
            if o["subfolder_path"] == sp: self._results[i] = r; break
        tag = r["row_health"] + ("_odd" if self.tree.index(iid) % 2 else "")
        self.tree.item(iid, values=self._rv(r), tags=(tag,))
        self._update_stats()

    # ── Extract frames ────────────────────────────────────────────────────────
    def _extract_frames(self):
        if self._scanning: return
        sel = self.tree.selection()
        if not sel: messagebox.showwarning("No selection","Select a row first."); return
        d = self._item_map.get(sel[0])
        if not d: return
        self._do_extract(d)

    def _do_extract(self, d):
        ff_ok, fp_ok, _, _ = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
        if not ff_ok:
            messagebox.showerror("FFmpeg missing",
                                 "FFmpeg is not available or not working.\n"
                                 "Use the FFmpeg status in the header to set the path or download it.")
            return
        if not d["video_path"]:
            messagebox.showwarning("No video","No video file in this subfolder."); return
        timeout = SETTINGS.get("extract_timeout", 60)
        dlg = FrameExtractionDialog(self, d["video_path"], d["subfolder_path"],
                                    timeout_sec=timeout)
        self.wait_window(dlg)
        # Update saved timeout preference
        SETTINGS["extract_timeout"] = dlg._timeout_var.get()
        _save_settings(SETTINGS)
        # Re-validate row after extraction
        sel = self.tree.selection()
        if sel:
            iid = sel[0]
            if iid in self._item_map:
                self._reval(iid, self._item_map[iid])

    # ── Browse / Scan / Update / Cancel ──────────────────────────────────────
    def _browse(self):
        if self._scanning: return
        p = filedialog.askdirectory(title="Select root folder")
        if p:
            self._folder = p; self.folder_var.set(p); self.stats_var.set("")
            self._results = []; self._item_map.clear()
            for r in self.tree.get_children(): self.tree.delete(r)

    def _update_scan(self):
        """Re-scan the same folder that was last scanned."""
        if self._scanning: return
        folder = self._folder or SETTINGS.get("last_folder", "")
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No folder",
                                   "No folder to update. Please use Browse… first.")
            return
        self._folder = folder
        self.folder_var.set(folder)
        self._start_scan(folder)

    def _draw_scan_progress(self, pct, text):
        c = self.pbar_canvas; c.delete("all")
        w = c.winfo_width() or 400; h = 22
        c.create_rectangle(0, 0, w, h, fill="#313244", outline="")
        fw = int(w * pct / 100)
        if fw > 0:
            c.create_rectangle(0, 0, fw, h, fill="#2d6e3f", outline="")
        c.create_text(w // 2, h // 2, text=f"{pct}%",
                      fill="#cdd6f4", font=("Helvetica", 10, "bold"))
        self.pbar_label.configure(text=text)

    def _scan(self):
        if self._scanning: return
        if not self._folder:
            messagebox.showwarning("No folder","Select a folder first."); return
        self._start_scan(self._folder)

    def _start_scan(self, folder):
        try:
            dirs = sorted([e for e in os.scandir(folder) if e.is_dir()],
                          key=lambda e: e.name.lower())
        except PermissionError:
            messagebox.showerror("Error", f"Cannot access: {folder}"); return
        if not dirs:
            messagebox.showinfo("Empty","No subfolders."); return

        self._results = []; self._item_map.clear()
        for r in self.tree.get_children(): self.tree.delete(r)

        self._scanning = True; self._cancel_scan = False
        self.scan_btn.configure(state="disabled")
        self.update_btn.configure(state="disabled")
        self.cancel_btn.pack(side="left", padx=(6, 0))
        self.pbar_canvas.pack(side="left", fill="x", expand=True)
        self.pbar_label.pack(side="left", padx=(8, 0))
        self._draw_scan_progress(0, "Starting…")

        total = len(dirs)
        _start_time = [time.time()]
        _done_count  = [0]

        def worker():
            results = []
            for i, entry in enumerate(dirs):
                if self._cancel_scan: break
                results.append(scan_one_subfolder(entry.path, entry.name))
                _done_count[0] = i + 1
                pct = int((i + 1) / total * 100)

                elapsed  = time.time() - _start_time[0]
                avg_time = elapsed / (i + 1)
                remaining = avg_time * (total - i - 1)
                if remaining > 60:
                    eta = f"{int(remaining // 60)}m {int(remaining % 60)}s remaining"
                elif remaining > 0:
                    eta = f"{int(remaining)}s remaining"
                else:
                    eta = "finishing…"

                label = f"Scanning {i+1}/{total} — {eta}"
                self.after(0, self._draw_scan_progress, pct, label)

            self.after(0, _done, results)

        def _done(results):
            self._scanning = False
            self.scan_btn.configure(state="normal")
            self.update_btn.configure(state="normal")
            self.cancel_btn.pack_forget()
            self.pbar_canvas.pack_forget()
            self.pbar_label.pack_forget()
            self._results = results
            if not results:
                self.stats_var.set("Cancelled or empty."); return
            self._update_stats(); self._refresh_table()
            # Persist session
            SETTINGS["last_folder"]  = folder
            SETTINGS["last_results"] = _results_to_json(results)
            SETTINGS["sort_option"]  = self.sort_var.get()
            _save_settings(SETTINGS)

        threading.Thread(target=worker, daemon=True).start()

    def _cancel(self):
        self._cancel_scan = True; self.pbar_label.configure(text="Cancelling…")

    def _restore_last_session(self):
        """Silently reload the last scan session from settings."""
        last_folder  = SETTINGS.get("last_folder", "")
        last_results = SETTINGS.get("last_results", [])
        if not last_folder or not last_results:
            return
        if not os.path.isdir(last_folder):
            return  # Folder no longer exists — skip silently
        self._folder = last_folder
        self.folder_var.set(last_folder)
        self._results = _results_from_json(last_results)
        self._update_stats()
        self._refresh_table()

    # ── Stats ─────────────────────────────────────────────────────────────────
    def _update_stats(self):
        t   = len(self._results)
        pc  = sum(1 for r in self._results if r["poster_exists"])
        fc  = sum(1 for r in self._results if r["folder_exists"])
        ac  = sum(1 for r in self._results if r["fanart_exists"])
        nc  = sum(1 for r in self._results if r["nfo_exists"])
        ne  = sum(1 for r in self._results if r["nfo_errors"])
        xc  = sum(1 for r in self._results if r["xml_exists"])
        xe  = sum(1 for r in self._results if r["xml_errors"])
        vc  = sum(1 for r in self._results if r["video_count"] == 1)
        ul  = sum(1 for r in self._results if r["language"] == "Unknown")
        pt  = sum(1 for r in self._results if r.get("pt_ok") == "Y")
        self.stats_var.set("  •  ".join(
            [f"{t} folders", f"poster:{pc}/{t}", f"folder:{fc}/{t}",
             f"fanart:{ac}/{t}", f"nfo:{nc}/{t}({ne}err)",
             f"xml:{xc}/{t}({xe}err)", f"video:{vc}/{t}",
             f"PT-OK:{pt}/{t}"]
            + ([f"unknown lang:{ul}"] if ul else [])))

    # ── Row values builder ────────────────────────────────────────────────────
    def _rv(self, r):
        def s(ex, cor): return STATUS_MISSING if not ex else (STATUS_ERROR if cor else STATUS_OK)
        subfolder_text = self._wrap_text(r["subfolder"], "subfolder", max_chars=30)
        return (
            subfolder_text,
            s(r["poster_exists"],  r["poster_corrupt"]),  r["poster_size"],
            s(r["folder_exists"],  r["folder_corrupt"]),  r["folder_size"],
            s(r["fanart_exists"],  r["fanart_corrupt"]),  r["fanart_size"],
            str(r["backdrop_count"]) if r["backdrop_count"] > 0 else "—",
            STATUS_OK if r["nfo_exists"] else STATUS_MISSING, r["nfo_status"],
            STATUS_OK if r["xml_exists"] else STATUS_MISSING, r["xml_status"],
            r["language"],
            r["video_ext"] if r["video_count"] > 0 else "✗",
            r["video_size"],
            r.get("video_quality", "—"),
            r.get("pt_ok", "—"),
            r["subs_summary"],
        )

    # ── Refresh table ─────────────────────────────────────────────────────────
    def _refresh_table(self):
        if not self._results: return
        for r in self.tree.get_children(): self.tree.delete(r)
        self._item_map.clear()

        sort_name = self.sort_var.get()
        kf, rev   = SORT_OPTIONS.get(sort_name, SORT_OPTIONS["Subfolder (A→Z)"])

        # Primary sort + secondary sort by Subfolder A→Z
        def sort_key(r):
            return (kf(r), r["subfolder"].lower())

        sorted_results = sorted(self._results, key=sort_key, reverse=rev)

        for i, r in enumerate(sorted_results):
            tag = r["row_health"] + ("_odd" if i % 2 else "")
            iid = self.tree.insert("", "end", values=self._rv(r), tags=(tag,))
            self._item_map[iid] = r

    # ── Export CSV ────────────────────────────────────────────────────────────
    def _export_csv(self):
        if self._scanning: return
        if not self._results: messagebox.showinfo("Empty","Scan first."); return
        p = filedialog.asksaveasfilename(
            title="Export", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="scan_results.csv")
        if not p: return

        def _st(s): return "OK" if s == STATUS_OK else ("Error" if s == STATUS_ERROR else "Missing")
        try:
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Subfolder","Path","poster.jpg","Poster Size","Poster Dim","Poster Corrupt",
                             "folder.jpg","Folder Size","Folder Dim","Folder Corrupt",
                             "fanart.jpg","Fanart Size","Fanart Dim","Fanart Corrupt","Backdrops",
                             ".nfo","NFO Valid","NFO Errors","movie.xml","XML Valid","XML Errors",
                             "Language","Video Files","Video Ext","Video Size","Quality","PT OK?",
                             "Embedded Subs","External Subs","Health"])
                for r in self._results:
                    w.writerow([
                        r["subfolder"], r["subfolder_path"],
                        "Y" if r["poster_exists"] else "N", r["poster_size"],
                        r["poster_dim"] or "—", "Y" if r["poster_corrupt"] else "N",
                        "Y" if r["folder_exists"] else "N", r["folder_size"],
                        r["folder_dim"] or "—", "Y" if r["folder_corrupt"] else "N",
                        "Y" if r["fanart_exists"] else "N", r["fanart_size"],
                        r["fanart_dim"] or "—", "Y" if r["fanart_corrupt"] else "N",
                        r["backdrop_count"],
                        "Y" if r["nfo_exists"] else "N", _st(r["nfo_status"]),
                        "; ".join(f"L{e['line']}:{e['message']}" for e in r["nfo_errors"]) or "",
                        "Y" if r["xml_exists"] else "N", _st(r["xml_status"]),
                        "; ".join(f"L{e['line']}:{e['message']}" for e in r["xml_errors"]) or "",
                        r["language"], r["video_count"], r["video_ext"], r["video_size"],
                        r.get("video_quality", "—"), r.get("pt_ok", "—"),
                        ", ".join(s["lang"] for s in r["subs_internal"]) or "None",
                        ", ".join(f'{s["lang"]}({s["file"]})' for s in r["subs_external"]) or "None",
                        r["row_health"],
                    ])
            messagebox.showinfo("Exported",
                                f"Saved {len(self._results)} rows to:\n{p}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import tkinter.font  # ensure available before auto-size methods run
    app = App()
    app.mainloop()
