# =============================================================================
# Metadata & MediaClinic
# Version: 9.0
# Author:  Luiz Junqueira & Claude AI
# Contact: junqueira.ch@gmail.com
#
# CHANGELOG
# ---------
# v9.0  (current)
#   PHASE 3 — Data Features
#   - Online Ratings Sync: fetch from TMDb (API key) and OMDb/IMDb (API key)
#     Side-by-side comparison dialog; "apply to all" batch option
#     Writes updated rating/votes to ALL matching tags in XML and NFO
#     Threaded — never freezes the UI; timeouts and graceful error handling
#     Right-click single movie or batch (multi-select)
#   - Genre column: reads <genre> from NFO, shows joined list and 🟢/🟡/🔴 status
#     Normalize Genres action: trims, fixes caps, maps synonyms, removes dupes
#     Single, multi, or all movies (confirms before all); writes NFO + XML
#   - Malformed XML/NFO fallback parser: regex extraction when ET fails,
#     recovers imdbid, tmdbid, title, year, rating, votes, language, genre
#   - Improvements report now appends scan errors at the bottom in red
#   PHASE 2 — Settings Expansion
#   - Settings → API Keys tab: TMDb and OMDb API keys with validation + Help
#   - Settings → Tools: fields auto-populate with detected tools on open
#   - Settings → Browser: detect installed browsers, choose default for all links
#   - Settings → Image Sizes: configure minimum KB for poster/folder/fanart
#   - Settings → Genres: editable standard genre list (TMDb-based)
#   - Settings → Backdrop Count: spinner for how many frames to extract (default 10)
#   - Settings → Video Scraper: clarified as future feature, metadata source picker
#   - All external links (IMDB, TMDb, OpenSubtitles) use selected default browser
#   PHASE 1 — Foundation & Quick Wins
#   - Sort combo now auto-updates table without clicking "Update Sort" button
#   - Notepad++ bug fixed: file path comes BEFORE -lxml flag, no stray dialogs
#   - Notepad++ not configured → falls back to system default editor (no prompt)
#   - NFO/XML filename click ALWAYS opens file for editing; OK? marker shows errors
#   - Column header tooltips explaining each column
#   - Icon replacement: all status columns now show 🟢/🟡/🔴 instead of text
#   - Cell tooltips enriched with file name, size, dimensions, ratio, errors
#   - Right-click menu: "Improvements" renamed to "Run Improvements Check"
#   - Image proportion mismatch downgraded from Error → Warning (🟡)
#   - Re-validate FFmpeg Metadata (single movie) added to right-click menu
#   - OpenSubtitles.org right-click option added
# v0.8.0
#   - Settings menu, Improvements health-check, IMDB/TMDb links, Copy Movie Name,
#     Auto-size Columns, FFprobe checkbox, configurable language column,
#     phased scan, smooth backdrop progress, Shift+select, image error details,
#     & suppressed in validator, quality fix.
# =============================================================================

import os
import csv
import json
import re
import struct
import subprocess
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import shutil
import tkinter.font as tk_font

# ── App identity ──────────────────────────────────────────────────────────────
APP_NAME    = "Metadata & MediaClinic"
APP_VERSION = "9.0"
APP_AUTHOR  = "Luiz Junqueira & Claude AI"
APP_EMAIL   = "junqueira.ch@gmail.com"

# ── File extensions ───────────────────────────────────────────────────────────
VIDEO_EXTENSIONS    = {'.mkv', '.mp4', '.avi', '.m4v', '.wmv', '.mov', '.flv',
                       '.ts', '.m2ts', '.mpg', '.mpeg', '.divx', '.ogm', '.webm'}
SUBTITLE_EXTENSIONS = {'.srt', '.sub', '.ssa', '.ass', '.vtt', '.idx', '.sup'}

# ── 30 most-used world languages (ISO 639-1 + common label) ──────────────────
WORLD_LANGUAGES = [
    ("ZH", "Chinese"),    ("ES", "Spanish"),    ("EN", "English"),
    ("HI", "Hindi"),      ("AR", "Arabic"),     ("PT", "Portuguese"),
    ("BN", "Bengali"),    ("RU", "Russian"),    ("JA", "Japanese"),
    ("PA", "Punjabi"),    ("DE", "German"),     ("KO", "Korean"),
    ("FR", "French"),     ("TE", "Telugu"),     ("MR", "Marathi"),
    ("TR", "Turkish"),    ("TA", "Tamil"),      ("VI", "Vietnamese"),
    ("IT", "Italian"),    ("UR", "Urdu"),       ("FA", "Persian"),
    ("PL", "Polish"),     ("NL", "Dutch"),      ("UK", "Ukrainian"),
    ("MS", "Malay"),      ("SV", "Swedish"),    ("DA", "Danish"),
    ("FI", "Finnish"),    ("NO", "Norwegian"),  ("EL", "Greek"),
]

# Build language lookup sets for each ISO code
# e.g. "PT" → {'por','pt','pt-br','pt-pt','portuguese','portugues','ptbr','ptpt','pt_br','pt_pt'}
_LANG_ALIASES = {
    "ZH": {"zho","zh","chi","chinese","mandarin","cantonese","zh-cn","zh-tw","zhs","zht"},
    "ES": {"spa","es","esp","spanish","español","espanol"},
    "EN": {"eng","en","english"},
    "HI": {"hin","hi","hindi"},
    "AR": {"ara","ar","arabic"},
    "PT": {"por","pt","pt-br","pt-pt","portuguese","portugues","pt_br","pt_pt","ptbr","ptpt"},
    "BN": {"ben","bn","bengali"},
    "RU": {"rus","ru","russian"},
    "JA": {"jpn","ja","jp","japanese"},
    "PA": {"pan","pa","punjabi"},
    "DE": {"ger","deu","de","german","deutsch"},
    "KO": {"kor","ko","korean"},
    "FR": {"fre","fra","fr","french","français","francais"},
    "TE": {"tel","te","telugu"},
    "MR": {"mar","mr","marathi"},
    "TR": {"tur","tr","turkish"},
    "TA": {"tam","ta","tamil"},
    "VI": {"vie","vi","vietnamese"},
    "IT": {"ita","it","italian","italiano"},
    "UR": {"urd","ur","urdu"},
    "FA": {"fas","per","fa","persian","farsi"},
    "PL": {"pol","pl","polish"},
    "NL": {"nld","dut","nl","dutch","nederlands"},
    "UK": {"ukr","uk","ukrainian"},
    "MS": {"msa","ms","malay","malaysian"},
    "SV": {"swe","sv","swedish","svenska"},
    "DA": {"dan","da","danish","dansk"},
    "FI": {"fin","fi","finnish","suomi"},
    "NO": {"nor","no","norwegian","norsk"},
    "EL": {"ell","gre","el","greek"},
}

def is_target_lang(tag, iso_code):
    """Return True if the language tag matches the given ISO-639-1 code."""
    return tag.strip().lower() in _LANG_ALIASES.get(iso_code.upper(), set())

# ── Column indices ────────────────────────────────────────────────────────────
COL_SUBFOLDER =  0
COL_POSTER    =  1;  COL_POSTER_SZ =  2
COL_FOLDER    =  3;  COL_FOLDER_SZ =  4
COL_FANART    =  5;  COL_FANART_SZ =  6
COL_BACKDROPS =  7
COL_NFO       =  8;  COL_NFO_OK   =  9
COL_XML       = 10;  COL_XML_OK   = 11
COL_LANGUAGE  = 12
COL_VID_EXT   = 13;  COL_VID_SIZE = 14;  COL_QUALITY = 15
COL_LANG_OK   = 16
COL_SUBS      = 17
COL_GENRE     = 18   # Phase 3 — Genre column

STATUS_OK      = "🟢"
STATUS_WARN    = "🟡"
STATUS_MISSING = "🔴"
STATUS_ERROR   = "🔴"

# ── Default NFO→XML tag comparison pairs ─────────────────────────────────────
DEFAULT_TAG_PAIRS = [
    # (nfo_path, xml_path, label, numeric_tolerance_pct)
    # nfo_path: dot-separated path from root, e.g. "title" or "fileinfo.streamdetails.video.width"
    # xml_path: dot-separated path from root
    ("title",                               "LocalTitle",                  "Title",            0),
    ("originaltitle",                       "OriginalTitle",               "Original Title",   0),
    ("year",                                "ProductionYear",              "Year",             0),
    ("releasedate",                         "ReleaseDate",                 "Release Date",     0),
    ("releasedate",                         "PremiereDate",                "Premiere Date",    0),
    ("votes",                               "Votes",                       "Votes",            5),
    ("rating",                              "IMDBrating",                  "Rating (IMDB)",    5),
    ("rating",                              "Rating",                      "Rating",           5),
    ("id",                                  "IMDB_ID",                     "IMDB ID",          0),
    ("id",                                  "IMDB",                        "IMDB",             0),
    ("imdbid",                              "IMDB_ID",                     "IMDb ID",          0),
    ("imdbid",                              "IMDB",                        "IMDb",             0),
    ("tmdbid",                              "TMDbId",                      "TMDb ID",          0),
    ("tmdbid",                              "TMDB",                        "TMDb",             0),
    ("tmdbid",                              "TMDB_ID",                     "TMDb ID2",         0),
    ("country",                             "Country",                     "Country",          0),
    ("runtime",                             "RunningTime",                 "Runtime",          5),
    ("runtime",                             "Runtime",                     "Runtime2",         5),
    ("plot",                                "Overview",                    "Plot/Overview",    0),
    ("plot",                                "Synopsis",                    "Plot/Synopsis",    0),
    ("plot",                                "Plot",                        "Plot",             0),
    ("plot",                                "Description",                 "Plot/Desc",        0),
    ("outline",                             "Outline",                     "Outline",          0),
    ("genre",                               "Genres.Genre",                "Genre",            0),
    ("studio",                              "Studios.Studio",              "Studio",           0),
    ("director",                            "Director",                    "Director",         0),
    ("fileinfo.streamdetails.audio.channels",    "MediaInfo.Audio.Channels",   "Audio Channels",   5),
    ("fileinfo.streamdetails.audio.codec",       "MediaInfo.Audio.Codec",      "Audio Codec",      0),
    ("fileinfo.streamdetails.video.codec",       "MediaInfo.Video.Codec",      "Video Codec",      0),
    ("fileinfo.streamdetails.video.durationinseconds", "MediaInfo.Video.DurationSeconds", "Duration", 5),
    ("fileinfo.streamdetails.video.language",    "MediaInfo.Audio.Language",   "Video Language",   0),
    ("fileinfo.streamdetails.video.scantype",    "MediaInfo.Video.ScanType",   "Scan Type",        0),
    ("fileinfo.streamdetails.video.height",      "MediaInfo.Video.Height",     "Video Height",     0),
    ("fileinfo.streamdetails.video.width",       "MediaInfo.Video.Width",      "Video Width",      0),
]

# ── XML standalone ↔ MediaInfo cross-check pairs ─────────────────────────────
# (standalone_xpath, mediainfo_xpath, label, tolerance_pct)
XML_INTERNAL_PAIRS = [
    ("VideoHeight",     "MediaInfo.Video.Height",        "VideoHeight vs MediaInfo",   0),
    ("VideoWidth",      "MediaInfo.Video.Width",         "VideoWidth vs MediaInfo",    0),
    ("VideoCodec",      "MediaInfo.Video.Codec",         "VideoCodec vs MediaInfo",    0),
    ("AudioChannels",   "MediaInfo.Audio.Channels",      "AudioChannels vs MediaInfo", 5),
    ("AudioCodec",      "MediaInfo.Audio.Codec",         "AudioCodec vs MediaInfo",    0),
    ("Runtime",         "MediaInfo.Video.Duration",      "Runtime vs MediaInfo",       5),
    ("RunningTime",     "MediaInfo.Video.Duration",      "RunningTime vs MediaInfo",   5),
]

# ── Persistent storage ────────────────────────────────────────────────────────
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
    "ffmpeg_path":        "",
    "text_editor":        "",          # path to preferred text editor exe
    "scraper_path":       "",          # path to video scraper exe
    "last_folder":        "",
    "last_results":       [],
    "sort_option":        "Subfolder (A→Z)",
    "extract_timeout":    60,
    "use_ffprobe":        True,        # ffprobe checkbox
    "lang_ok_code":       "PT",        # language for "OK?" column
    # Improvement thresholds
    "improve_checks": {
        "large_xml":      True,
        "nfo_xml_diff":   True,
        "ffprobe_diff":   True,
        "poster_folder":  True,
        "proportions":    True,
        "backdrops":      True,
    },
    "max_nfo_kb":         50,
    "max_xml_kb":         25,
    "min_backdrops":      5,
    "tag_pairs":          None,        # None = use DEFAULT_TAG_PAIRS
    # Phase 2 — API keys
    "tmdb_api_key":       "",
    "omdb_api_key":       "",
    # Phase 2 — Browser
    "default_browser":    "",          # path to browser exe; "" = system default
    # Phase 2 — Image minimum sizes (KB); 0 = skip check
    "min_poster_kb":      100,
    "min_folder_kb":      100,
    "min_fanart_kb":      200,
    # Phase 2 — Backdrop extraction count
    "backdrop_count":     10,
    # Phase 2 — Genre list (one per line; stored as newline-joined string)
    "genre_list":         (
        "Action\nAdventure\nAnimation\nComedy\nCrime\nDocumentary\nDrama\n"
        "Family\nFantasy\nHistory\nHorror\nMusic\nMystery\nRomance\n"
        "Science Fiction\nThriller\nWar\nWestern"
    ),
    # Phase 2 — Metadata source (future scraper target)
    "metadata_source":    "tmdb",      # "tmdb" | "omdb"
}

def _load_settings():
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(_DEFAULT_SETTINGS)
            # Deep merge improve_checks
            if "improve_checks" in data:
                ic = dict(_DEFAULT_SETTINGS["improve_checks"])
                ic.update(data["improve_checks"])
                data["improve_checks"] = ic
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
    exe = lambda d, n: (os.path.join(d, n + ".exe") if os.name == "nt"
                        else os.path.join(d, n))
    if custom_dir and os.path.isdir(custom_dir):
        ff = exe(custom_dir, "ffmpeg");  fp = exe(custom_dir, "ffprobe")
        if not os.path.isfile(ff): ff = os.path.join(custom_dir, "ffmpeg")
        if not os.path.isfile(fp): fp = os.path.join(custom_dir, "ffprobe")
        if os.path.isfile(ff) and os.path.isfile(fp):
            return ff, fp
    return shutil.which("ffmpeg"), shutil.which("ffprobe")

def _test_ffmpeg(ff_path, fp_path):
    def _run(path):
        if not path or not os.path.isfile(path):
            return False, "Executable not found"
        try:
            r = subprocess.run(
                [path, "-version"], capture_output=True, text=True, timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0 and ("ffmpeg" in r.stdout.lower() or
                                       "ffprobe" in r.stdout.lower()):
                return True, "OK"
            return False, f"Unexpected output (exit {r.returncode})"
        except subprocess.TimeoutExpired:
            return False, "Timed out"
        except Exception as e:
            return False, str(e)
    ff_ok, ff_msg = _run(ff_path)
    fp_ok, fp_msg = _run(fp_path)
    return ff_ok, fp_ok, ff_msg, fp_msg

SETTINGS = _load_settings()
FFMPEG_PATH, FFPROBE_PATH = _find_ffmpeg_ffprobe(SETTINGS.get("ffmpeg_path", ""))

def refresh_ffmpeg_paths():
    global FFMPEG_PATH, FFPROBE_PATH
    FFMPEG_PATH, FFPROBE_PATH = _find_ffmpeg_ffprobe(SETTINGS.get("ffmpeg_path", ""))

# ── Text editor opener ────────────────────────────────────────────────────────
def _find_notepadpp():
    """Try common Notepad++ install locations on Windows."""
    candidates = [
        r"C:\Program Files\Notepad++\notepad++.exe",
        r"C:\Program Files (x86)\Notepad++\notepad++.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Notepad++", "notepad++.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Notepad++", "notepad++.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return shutil.which("notepad++")

def open_in_editor(filepath):
    """
    Open a file in the configured text editor.
    For NFO/XML files with Notepad++: notepad++.exe "path\\file.xml" -lxml
    (file path MUST come before -lxml — putting it after causes Notepad++ to
    show a 'Create new file?' dialog treating the path as a language tag).
    Falls back to OS default handler — no intermediate Notepad with -l flag.
    """
    editor = SETTINGS.get("text_editor", "").strip()
    ext = os.path.splitext(filepath)[1].lower()
    is_markup = ext in (".xml", ".nfo")

    def _launch_npp(npp_path):
        """Launch Notepad++ with filepath FIRST, then -lxml (correct order)."""
        try:
            cmd = [npp_path, filepath, "-lxml"] if is_markup else [npp_path, filepath]
            subprocess.Popen(cmd,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return True
        except Exception:
            return False

    # 1. Use configured editor if set
    if editor and os.path.isfile(editor):
        if is_markup and "notepad++" in editor.lower():
            if _launch_npp(editor):
                return
        else:
            try:
                subprocess.Popen([editor, filepath],
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                return
            except Exception:
                pass

    # 2. Auto-detect Notepad++ on Windows
    if os.name == "nt" and is_markup:
        npp = _find_notepadpp()
        if npp and _launch_npp(npp):
            return

    # 3. Fall back to OS default (no prompts)
    try:
        if os.name == "nt":
            os.startfile(filepath)
        else:
            try:   subprocess.Popen(["xdg-open", filepath])
            except FileNotFoundError: subprocess.Popen(["open", filepath])
    except Exception as e:
        messagebox.showerror("Cannot open", str(e))


def os_open(path):
    """Open any file/folder with default OS handler."""
    try:
        if os.name == "nt":
            os.startfile(path)
        else:
            try:   subprocess.Popen(["xdg-open", path])
            except FileNotFoundError: subprocess.Popen(["open", path])
    except Exception as e:
        messagebox.showerror("Cannot open", str(e))

def open_with_scraper(folder_path):
    """Launch the configured scraper with the movie folder as argument."""
    scraper = SETTINGS.get("scraper_path", "").strip()
    if not scraper or not os.path.isfile(scraper):
        messagebox.showwarning("Scraper Not Set",
                               "No scraper configured.\n"
                               "Go to Settings → Scraper to select your scraper executable.")
        return
    try:
        subprocess.Popen([scraper, folder_path],
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        messagebox.showerror("Cannot launch scraper", str(e))


# ── Browser helpers ───────────────────────────────────────────────────────────

_KNOWN_BROWSERS_WIN = [
    # (display_name, candidate_paths...)
    ("Google Chrome",    [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA",""), r"Google\Chrome\Application\chrome.exe"),
    ]),
    ("Mozilla Firefox",  [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ]),
    ("Microsoft Edge",   [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.join(os.environ.get("PROGRAMFILES",""),  r"Microsoft\Edge\Application\msedge.exe"),
    ]),
    ("Brave",            [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.join(os.environ.get("LOCALAPPDATA",""), r"BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]),
    ("Opera",            [
        os.path.join(os.environ.get("LOCALAPPDATA",""), r"Programs\Opera\opera.exe"),
        r"C:\Program Files\Opera\opera.exe",
    ]),
    ("Vivaldi",          [
        os.path.join(os.environ.get("LOCALAPPDATA",""), r"Vivaldi\Application\vivaldi.exe"),
    ]),
]


def detect_installed_browsers():
    """
    Scan standard locations for known browsers on Windows.
    Returns list of (display_name, exe_path) tuples for browsers actually found.
    """
    found = []
    if os.name != "nt":
        return found
    for name, candidates in _KNOWN_BROWSERS_WIN:
        for path in candidates:
            if path and os.path.isfile(path):
                found.append((name, path))
                break
    return found


def open_url_with_browser(url):
    """
    Open a URL in the user's configured browser.
    Falls back to the system default (webbrowser module) if none configured.
    """
    browser_path = SETTINGS.get("default_browser", "").strip()
    if browser_path and os.path.isfile(browser_path):
        try:
            subprocess.Popen([browser_path, url],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return
        except Exception:
            pass
    # System default fallback
    webbrowser.open(url)



def format_size(size_bytes):
    if size_bytes < 1024:        return f"{size_bytes} B"
    elif size_bytes < 1024**2:   return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:   return f"{size_bytes/(1024**2):.1f} MB"
    else:                        return f"{size_bytes/(1024**3):.2f} GB"

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

def get_image_wh(filepath):
    """Return (width, height) integers or (None, None)."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.jpg', '.jpeg'):
        return get_jpeg_dimensions(filepath)
    if ext == '.png':
        return get_png_dimensions(filepath)
    return None, None

def is_valid_jpeg(filepath):
    try:
        if os.path.getsize(filepath) == 0: return False
        with open(filepath, "rb") as f: return f.read(2) == b'\xff\xd8'
    except Exception: return False

def classify_quality(width, height):
    if width is None or height is None:
        return "—"
    if not width or not height:
        return "—"
    long_side  = max(width, height)
    short_side = min(width, height)
    # For HD: use long_side (width) — 1920x1040 long=1920 → 1080p ✓
    # For SD: use short_side (height in landscape) — 720x576 short=576 → 576p ✓
    if long_side  >= 3840: return "4K UHD"
    if long_side  >= 2560: return "1440p"
    if long_side  >= 1920: return "1080p"
    if long_side  >= 1280: return "720p"
    if short_side >= 576:  return "576p/DVD"
    if short_side >= 480:  return "480p"
    if short_side >= 360:  return "360p"
    if short_side >= 240:  return "240p"
    return "SD"

def _quality_sort_key(label):
    order = {"4K UHD":0,"1440p":1,"1080p":2,"720p":3,
             "576p/DVD":4,"480p":5,"360p":6,"240p":7,"SD":8,"—":9}
    return order.get(label, 9)

# ── Image health check ────────────────────────────────────────────────────────
def check_image_health(filepath, image_type):
    """
    Returns (status, description) where status is STATUS_OK / STATUS_WARN / STATUS_ERROR.
    image_type: 'poster', 'folder', or 'fanart'
    Proportion mismatches → STATUS_WARN (yellow)
    Size / corruption issues → STATUS_ERROR (red)
    Minimum size = 0 in settings → size check skipped entirely.
    """
    if not os.path.isfile(filepath):
        return STATUS_MISSING, "File missing"

    size_bytes = os.path.getsize(filepath)
    if size_bytes == 0:
        return STATUS_ERROR, "File is empty (0 bytes)"

    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.jpg', '.jpeg') and not is_valid_jpeg(filepath):
        return STATUS_ERROR, "Invalid JPEG header — file may be corrupt"

    w, h = get_image_wh(filepath)
    size_issues = []
    prop_issues = []

    if image_type in ('poster', 'folder'):
        min_kb = SETTINGS.get(f"min_{image_type}_kb", 100) if image_type == 'poster' \
                 else SETTINGS.get("min_folder_kb", 100)
        if min_kb > 0 and size_bytes < min_kb * 1024:
            size_issues.append(f"File size {size_bytes//1024} KB is below {min_kb} KB minimum")
        if w and h:
            ratio = w / h
            if not (0.60 <= ratio <= 0.72):
                prop_issues.append(f"Proportions {w}×{h} ({ratio:.2f}) — expected 2:3 portrait (≈0.67)")
    elif image_type == 'fanart':
        min_kb = SETTINGS.get("min_fanart_kb", 200)
        if min_kb > 0 and size_bytes < min_kb * 1024:
            size_issues.append(f"File size {size_bytes//1024} KB is below {min_kb} KB minimum")
        if w and h:
            ratio = w / h
            if not (1.70 <= ratio <= 1.85):
                prop_issues.append(f"Proportions {w}×{h} ({ratio:.2f}) — expected 16:9 landscape (≈1.78)")

    if size_issues:
        all_issues = size_issues + prop_issues
        return STATUS_ERROR, "; ".join(all_issues)
    if prop_issues:
        return STATUS_WARN, "; ".join(prop_issues)
    return STATUS_OK, ""

# ══════════════════════════════════════════════════════════════════════════════
# Backdrop helpers
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
    for i in range(1, 200):
        if not os.path.isfile(os.path.join(sub_path, f"backdrop{i}.jpg")):
            return i
    return 1

# ══════════════════════════════════════════════════════════════════════════════
# Video / subtitle / language helpers
# ══════════════════════════════════════════════════════════════════════════════

def scan_video_files(sub_path):
    videos = []
    try:
        for f in os.scandir(sub_path):
            if f.is_file() and os.path.splitext(f.name)[1].lower() in VIDEO_EXTENSIONS:
                videos.append(f)
    except PermissionError: pass
    if not videos:
        return {"video_count":0,"video_files":[],"video_ext":"—",
                "video_path":None,"video_bytes":0,"video_size":"—",
                "video_width":None,"video_height":None,"video_quality":"—"}
    videos.sort(key=lambda e: e.stat().st_size, reverse=True)
    main = videos[0]; ext = os.path.splitext(main.name)[1].lower()
    # Quality determined later when ffprobe runs (phased scan)
    return {"video_count":len(videos),"video_files":[v.name for v in videos],
            "video_ext":ext.lstrip('.').upper(),"video_path":main.path,
            "video_bytes":main.stat().st_size,"video_size":format_size(main.stat().st_size),
            "video_width":None,"video_height":None,"video_quality":"—"}

def _get_video_resolution(video_path):
    """Return (width, height) of first video stream, or (None, None)."""
    if not FFPROBE_PATH or not SETTINGS.get("use_ffprobe", True):
        return None, None
    try:
        r = subprocess.run(
            [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "v:0", video_path],
            capture_output=True, text=True, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode == 0 and r.stdout.strip():
            streams = json.loads(r.stdout).get("streams", [])
            if streams:
                w = streams[0].get("width"); h = streams[0].get("height")
                if w and h: return int(w), int(h)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        pass
    return None, None

def _get_ffprobe_full(video_path):
    """Return full ffprobe JSON dict (format + streams), or {}."""
    if not FFPROBE_PATH or not SETTINGS.get("use_ffprobe", True):
        return {}
    try:
        r = subprocess.run(
            [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", video_path],
            capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except Exception:
        pass
    return {}

def scan_subtitles(sub_path, video_path):
    result = {"subs_internal":[],"subs_external":[],"subs_summary":"—"}
    try:
        for f in os.scandir(sub_path):
            if f.is_file() and os.path.splitext(f.name)[1].lower() in SUBTITLE_EXTENSIONS:
                parts = os.path.splitext(f.name)[0].rsplit('.', 1)
                lang = parts[-1] if len(parts) > 1 and len(parts[-1]) <= 20 else "unknown"
                result["subs_external"].append({"lang": lang, "file": f.name})
    except PermissionError: pass
    if video_path and FFPROBE_PATH and SETTINGS.get("use_ffprobe", True):
        try:
            proc = subprocess.run(
                [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-select_streams", "s", video_path],
                capture_output=True, text=True, timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if proc.returncode == 0 and proc.stdout.strip():
                for stream in json.loads(proc.stdout).get("streams", []):
                    tags = stream.get("tags", {})
                    result["subs_internal"].append({
                        "lang":  tags.get("language") or tags.get("LANGUAGE") or "und",
                        "title": tags.get("title")    or tags.get("TITLE")    or ""})
        except Exception: pass
    parts = []
    if result["subs_internal"]:
        parts.append(f"Int: {', '.join(s['lang'] for s in result['subs_internal'])}")
    if result["subs_external"]:
        parts.append(f"Ext: {', '.join(s['lang'] for s in result['subs_external'])}")
    result["subs_summary"] = " | ".join(parts) if parts else ("None" if video_path else "—")
    return result

def compute_lang_ok(video_path, subs_internal, subs_external, nfo_path, xml_path, iso_code="PT"):
    """
    Y  — target language audio OR subtitle is present (ffprobe + XML + NFO)
    N  — video present but no target language found
    —  — no video file
    """
    if not video_path:
        return "—"

    # 1. FFprobe audio streams
    if FFPROBE_PATH and SETTINGS.get("use_ffprobe", True):
        try:
            r = subprocess.run(
                [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-select_streams", "a", video_path],
                capture_output=True, text=True, timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0 and r.stdout.strip():
                for stream in json.loads(r.stdout).get("streams", []):
                    tags = stream.get("tags", {})
                    lang = tags.get("language") or tags.get("LANGUAGE") or ""
                    if is_target_lang(lang, iso_code):
                        return "Y"
        except Exception: pass

    # 2. Internal subtitles (ffprobe)
    for s in subs_internal:
        if is_target_lang(s.get("lang", ""), iso_code):
            return "Y"

    # 3. External subtitle files
    for s in subs_external:
        if is_target_lang(s.get("lang", ""), iso_code):
            return "Y"

    # 4. XML: LanguageCode tag
    if xml_path and os.path.isfile(xml_path):
        try:
            with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            for m in re.finditer(r'<LanguageCode>([^<]+)</LanguageCode>', content, re.IGNORECASE):
                if is_target_lang(m.group(1).strip(), iso_code): return "Y"
            # XML Audio/Language
            for m in re.finditer(r'<Language>([^<]+)</Language>', content, re.IGNORECASE):
                if is_target_lang(m.group(1).strip(), iso_code): return "Y"
        except Exception: pass

    # 5. NFO: streamdetails/video/language
    if nfo_path and os.path.isfile(nfo_path):
        try:
            with open(nfo_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            for m in re.finditer(r'<language>([^<]+)</language>', content, re.IGNORECASE):
                if is_target_lang(m.group(1).strip(), iso_code): return "Y"
        except Exception: pass

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

# ══════════════════════════════════════════════════════════════════════════════
# XML / NFO parsing helpers
# ══════════════════════════════════════════════════════════════════════════════

def _is_url_only_nfo(content):
    s = content.strip()
    return '\n' not in s and s.startswith(('http://', 'https://'))

def validate_xml_file(filepath, is_nfo=False):
    """Validate XML/NFO structure. Returns list of error dicts."""
    errors = []
    if not os.path.isfile(filepath): return errors
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return [{"line":0,"col":0,"message":f"Cannot read: {e}"}]
    if not content.strip(): return [{"line":1,"col":0,"message":"File is empty"}]
    if is_nfo and _is_url_only_nfo(content): return errors
    if content.startswith('\ufeff'): content = content[1:]

    # Strip & / &amp; for parse — do NOT report as error (KODI-safe)
    parse_content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)

    try:
        ET.fromstring(parse_content)
    except ET.ParseError as e:
        line, col = e.position if hasattr(e, 'position') else (0, 0)
        raw_msg = str(e)
        src_lines = content.splitlines()
        if 0 < line <= len(src_lines):
            offending = src_lines[line - 1]
            if "mismatched tag" in raw_msg:
                raw_msg = (f"Mismatched tag at line {line} — "
                           "likely caused by a broken tag earlier in the file")
        # Filter out & errors entirely
        if "undefined entity" not in raw_msg.lower():
            errors.append({"line":line,"col":col,"message":raw_msg})

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
                    for pk in range(ln, min(ln+5, len(lines))):
                        pl = lines[pk]
                        if '>' in pl:
                            gp = pl.index('>'); lp = pl.find('<')
                            if lp == -1 or gp < lp: ml = True
                            break
                        if '<' in pl: break
                if not ml and not any(e["line"] == ln for e in errors):
                    errors.append({"line":ln,"col":lt.index(f"<{b}")+1,
                                   "message":f"Malformed tag '<{b}…' — missing '>'"})
        stripped = lt.rstrip()
        if re.search(r'</[A-Za-z_][\w.\-]*\s*$', stripped) and not stripped.endswith('>'):
            if not any(e["line"] == ln for e in errors):
                errors.append({"line":ln,"col":len(stripped),
                               "message":"Closing tag missing '>'"})
    seen = set(); unique = []
    for e in errors:
        k = (e["line"], e["message"][:60])
        if k not in seen: seen.add(k); unique.append(e)
    unique.sort(key=lambda e: (e["line"], e["col"]))
    return unique

def _parse_xml_to_dict(filepath):
    """
    Parse an XML/NFO file into a flat+nested dict for tag comparison.
    Returns {} on failure.
    """
    if not filepath or not os.path.isfile(filepath): return {}
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if content.startswith('\ufeff'): content = content[1:]
        # Normalise & so ET doesn't choke
        content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)
        root = ET.fromstring(content)
        return root
    except Exception:
        return None

def _xpath_get(root, dotpath):
    """
    Get values from an ET Element using dot-separated path.
    Returns list of non-empty string values found.
    Returns [] if nothing found.
    """
    if root is None: return []
    parts = dotpath.split('.')
    def _recurse(el, remaining):
        if not remaining:
            txt = (el.text or "").strip()
            return [txt] if txt else []
        tag = remaining[0]
        results = []
        for child in el:
            if child.tag.lower() == tag.lower():
                results.extend(_recurse(child, remaining[1:]))
        return results
    return _recurse(root, parts)

def _get_nfo_id_by_moviedb(root, moviedb_val):
    """Return <id moviedb='X'> value from NFO root."""
    if root is None: return []
    results = []
    for el in root.iter('id'):
        if el.get('moviedb', '').lower() == moviedb_val.lower():
            txt = (el.text or "").strip()
            if txt: results.append(txt)
    return results

def _norm_val(v):
    """Normalise a value for comparison: lowercase, strip spaces."""
    return str(v).strip().lower()

def _norm_numeric(v):
    """Extract numeric float from string, or None."""
    try:
        # Handle "5.1" channels → 6 mapping
        if str(v).strip() == "5.1": return 6.0
        if str(v).strip() == "7.1": return 8.0
        if str(v).strip() == "2.0": return 2.0
        return float(re.sub(r'[^\d.]', '', str(v)))
    except Exception: return None

def _vals_match(vals_a, vals_b, tol_pct=0):
    """
    Return True if any value in vals_a matches any value in vals_b.
    Numeric comparison uses tol_pct tolerance.
    Text comparison is case-insensitive.
    """
    if not vals_a or not vals_b: return True   # missing → skip check
    for a in vals_a:
        for b in vals_b:
            if tol_pct > 0:
                na = _norm_numeric(a); nb = _norm_numeric(b)
                if na is not None and nb is not None and nb != 0:
                    if abs(na - nb) / nb * 100 <= tol_pct:
                        return True
                    continue
            if _norm_val(a) == _norm_val(b):
                return True
    return False

def get_movie_ids_from_xml(xml_path):
    """Extract IMDB and TMDb IDs from movie.xml. Returns (imdb_id, tmdb_id)."""
    if not xml_path or not os.path.isfile(xml_path):
        return None, None
    try:
        with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if content.startswith('\ufeff'): content = content[1:]
        content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)
        root = ET.fromstring(content)
    except Exception:
        return None, None

    imdb_tags = ['IMDB', 'IMDbId', 'IMDB_ID']
    tmdb_tags = ['TMDbId', 'TMDB', 'TMDB_ID']
    imdb_id = None; tmdb_id = None
    for tag in imdb_tags:
        el = root.find(tag)
        if el is not None and el.text and el.text.strip():
            imdb_id = el.text.strip(); break
    for tag in tmdb_tags:
        el = root.find(tag)
        if el is not None and el.text and el.text.strip():
            tmdb_id = el.text.strip(); break
    return imdb_id, tmdb_id


def get_movie_year_from_files(nfo_path, xml_path):
    """Extract production year from NFO (<year>) or XML (<ProductionYear>)."""
    for filepath, tags in [(nfo_path, ['year']), (xml_path, ['ProductionYear'])]:
        if not filepath or not os.path.isfile(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            content_clean = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)
            root = ET.fromstring(content_clean)
            for tag in tags:
                el = root.find(tag)
                if el is not None:
                    txt = (el.text or "").strip()
                    if txt and re.match(r'^\d{4}$', txt):
                        return txt
        except Exception:
            pass
    return None


def build_opensubtitles_url(title, year=None):
    """Build an OpenSubtitles search URL from title and optional year."""
    if not title:
        return None
    safe_title = re.sub(r'[^\w\s\-]', '', title)
    safe_title = re.sub(r'\s+', '-', safe_title.strip())
    safe_title = re.sub(r'-+', '-', safe_title)
    if year:
        return (f"https://www.opensubtitles.org/en/search2/sublanguageid-all"
                f"/moviename-{safe_title}/movieyear-{year}")
    return (f"https://www.opensubtitles.org/en/search2/sublanguageid-all"
            f"/moviename-{safe_title}")


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Fallback XML parser (item 15)
# ══════════════════════════════════════════════════════════════════════════════

def _regex_extract_tag(content, tag, default=""):
    """Extract first occurrence of <tag>value</tag> case-insensitively."""
    m = re.search(rf'<{tag}[^>]*>([^<]*)</{tag}>', content, re.IGNORECASE)
    return m.group(1).strip() if m else default

def _regex_extract_all_tags(content, tag):
    """Extract all occurrences of <tag>value</tag>."""
    return [m.group(1).strip()
            for m in re.finditer(rf'<{tag}[^>]*>([^<]*)</{tag}>', content, re.IGNORECASE)
            if m.group(1).strip()]

def _safe_parse_xml(filepath):
    """
    Try ET.fromstring first; on failure fall back to regex extraction.
    Returns (root_or_None, fallback_dict).
    fallback_dict is populated when ET fails; root is None in that case.
    """
    if not filepath or not os.path.isfile(filepath):
        return None, {}
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return None, {}

    if content.startswith('\ufeff'):
        content = content[1:]
    clean = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)

    try:
        root = ET.fromstring(clean)
        return root, {}
    except ET.ParseError:
        pass

    # Fallback: regex extraction of the most important tags
    fb = {
        "imdbid":   _regex_extract_tag(content, "imdbid") or
                    _regex_extract_tag(content, "IMDB_ID") or
                    _regex_extract_tag(content, "IMDB"),
        "tmdbid":   _regex_extract_tag(content, "tmdbid") or
                    _regex_extract_tag(content, "TMDbId") or
                    _regex_extract_tag(content, "TMDB"),
        "title":    _regex_extract_tag(content, "title") or
                    _regex_extract_tag(content, "LocalTitle"),
        "year":     _regex_extract_tag(content, "year") or
                    _regex_extract_tag(content, "ProductionYear"),
        "rating":   _regex_extract_tag(content, "rating") or
                    _regex_extract_tag(content, "IMDBrating") or
                    _regex_extract_tag(content, "Rating"),
        "votes":    _regex_extract_tag(content, "votes") or
                    _regex_extract_tag(content, "Votes") or
                    _regex_extract_tag(content, "VoteCount"),
        "language": _regex_extract_tag(content, "language") or
                    _regex_extract_tag(content, "Language"),
        "genres":   _regex_extract_all_tags(content, "genre"),
    }
    return None, fb


def get_movie_ids_robust(nfo_path, xml_path):
    """
    Extract IMDb and TMDb IDs from NFO and/or XML, with fallback parser.
    Returns (imdb_id, tmdb_id) — first non-empty value wins.
    """
    imdb_id = tmdb_id = None

    for filepath, is_nfo in [(nfo_path, True), (xml_path, False)]:
        if not filepath or not os.path.isfile(filepath):
            continue
        root, fb = _safe_parse_xml(filepath)

        if root is not None:
            if is_nfo:
                # NFO: <imdbid>, <id moviedb="imdb">, <id>tt…</id>
                for tag in ['imdbid']:
                    el = root.find(tag)
                    if el is not None and el.text and el.text.strip():
                        imdb_id = imdb_id or el.text.strip()
                for el in root.iter('id'):
                    v = (el.text or "").strip()
                    mdb = el.get('moviedb', '')
                    if mdb.lower() == 'imdb' and v:
                        imdb_id = imdb_id or v
                    elif mdb.lower() in ('tmdb', 'themoviedb') and v:
                        tmdb_id = tmdb_id or v
                    elif not mdb and v.startswith('tt'):
                        imdb_id = imdb_id or v
                for tag in ['tmdbid']:
                    el = root.find(tag)
                    if el is not None and el.text and el.text.strip():
                        tmdb_id = tmdb_id or el.text.strip()
            else:
                # XML
                for tag in ['IMDB', 'IMDbId', 'IMDB_ID']:
                    el = root.find(tag)
                    if el is not None and el.text and el.text.strip():
                        imdb_id = imdb_id or el.text.strip(); break
                for tag in ['TMDbId', 'TMDB', 'TMDB_ID']:
                    el = root.find(tag)
                    if el is not None and el.text and el.text.strip():
                        tmdb_id = tmdb_id or el.text.strip(); break
        else:
            imdb_id = imdb_id or fb.get("imdbid") or None
            tmdb_id = tmdb_id or fb.get("tmdbid") or None

    return imdb_id, tmdb_id


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Genre helpers (item 13)
# ══════════════════════════════════════════════════════════════════════════════

# Synonym → canonical name mapping (TMDb authoritative)
_GENRE_SYNONYMS = {
    "sci-fi": "Science Fiction", "scifi": "Science Fiction",
    "sci fi": "Science Fiction", "science-fiction": "Science Fiction",
    "sf": "Science Fiction",
    "docu": "Documentary", "docs": "Documentary",
    "romance": "Romance", "romantic": "Romance",
    "musical": "Music",
    "biopic": "History", "bio": "History",
    "suspense": "Thriller",
    "sport": "Action", "sports": "Action",
    "animation": "Animation", "animated": "Animation",
    "action & adventure": "Action",
    "kids": "Family", "children": "Family",
}

def _get_valid_genres():
    """Return set of valid genres from settings (lowercase)."""
    raw = SETTINGS.get("genre_list", _DEFAULT_SETTINGS["genre_list"])
    return {g.strip() for g in raw.splitlines() if g.strip()}

def normalize_genre(raw):
    """Normalize a single genre string to its canonical form."""
    s = raw.strip()
    # Check synonym map (case-insensitive)
    lower = s.lower()
    if lower in _GENRE_SYNONYMS:
        return _GENRE_SYNONYMS[lower]
    # Title-case it and see if it matches a known genre
    title = s.title()
    valid = _get_valid_genres()
    for g in valid:
        if g.lower() == lower:
            return g.title() if g == g.lower() else g
    # Otherwise return title-cased version
    return title

def normalize_genre_list(genres):
    """
    Normalize a list of genre strings.
    Returns (normalized_list, changed: bool).
    """
    seen = set()
    result = []
    for g in genres:
        n = normalize_genre(g)
        if n and n not in seen:
            seen.add(n)
            result.append(n)
    changed = result != [normalize_genre(g) for g in genres[:len(result)]] or \
              len(result) != len(genres)
    return result, (result != genres)

def get_genres_from_nfo(nfo_path):
    """Extract all <genre> values from an NFO file. Returns list."""
    if not nfo_path or not os.path.isfile(nfo_path):
        return []
    root, fb = _safe_parse_xml(nfo_path)
    if root is not None:
        return [el.text.strip() for el in root.iter('genre')
                if el.text and el.text.strip()]
    return fb.get("genres", [])

def classify_genres(genres):
    """
    Return (display_str, status) for the genre column.
    status: STATUS_OK / STATUS_WARN / STATUS_ERROR
    """
    if not genres:
        return "—", STATUS_ERROR   # missing = red
    valid = _get_valid_genres()
    display = "/".join(genres)
    issues = []
    for g in genres:
        lower = g.lower()
        # check synonym or valid list
        canonical = _GENRE_SYNONYMS.get(lower)
        if canonical:
            issues.append(g)  # known synonym → warning
        elif g not in valid and g.title() not in valid:
            # not in list at all → might be custom or invalid
            pass   # custom genres are OK, don't flag
    # Check for capitalisation/spacing issues
    for g in genres:
        if g != normalize_genre(g):
            issues.append(g)
            break
    if issues:
        return display, STATUS_WARN
    return display, STATUS_OK

def write_genres_to_nfo(nfo_path, genres):
    """
    Write normalized genres back to NFO file, replacing all <genre> tags.
    Preserves all other content.
    """
    if not nfo_path or not os.path.isfile(nfo_path):
        return False, "NFO file not found"
    try:
        with open(nfo_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        # Remove all existing <genre> tags
        content_no_genres = re.sub(
            r'\s*<genre>[^<]*</genre>', '', content, flags=re.IGNORECASE)
        # Find insertion point: after <plot> or <year> or before </movie>
        new_genre_block = "\n".join(f"  <genre>{g}</genre>" for g in genres)
        # Insert before </movie> closing tag (or at end of root element)
        if re.search(r'</movie>', content_no_genres, re.IGNORECASE):
            result = re.sub(
                r'(</movie>)',
                f"{new_genre_block}\n\\1",
                content_no_genres, count=1, flags=re.IGNORECASE)
        else:
            # Append before the last closing tag
            result = content_no_genres.rstrip() + "\n" + new_genre_block + "\n"
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(result)
        return True, ""
    except Exception as e:
        return False, str(e)

def write_genres_to_xml(xml_path, genres):
    """
    Write normalized genres back to XML file, replacing <Genres><Genre>…</Genre></Genres>.
    """
    if not xml_path or not os.path.isfile(xml_path):
        return False, "XML file not found"
    try:
        with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        new_genres_block = (
            "  <Genres>\n" +
            "\n".join(f"    <Genre>{g}</Genre>" for g in genres) +
            "\n  </Genres>"
        )
        # Replace existing <Genres>…</Genres> block if present
        if re.search(r'<Genres>', content, re.IGNORECASE):
            result = re.sub(
                r'<Genres>.*?</Genres>',
                new_genres_block,
                content, count=1, flags=re.IGNORECASE | re.DOTALL)
        else:
            # Insert before closing root tag
            root_close = re.search(r'</\w+>\s*$', content)
            if root_close:
                result = content[:root_close.start()] + new_genres_block + "\n" + content[root_close.start():]
            else:
                result = content.rstrip() + "\n" + new_genres_block + "\n"
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(result)
        return True, ""
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Online Ratings Sync (item 2)
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_tmdb_rating(tmdb_id, api_key):
    """
    Fetch rating and vote count from TMDb.
    Returns (rating_str, votes_str) or (None, None) on failure.
    """
    if not tmdb_id or not api_key:
        return None, None
    try:
        import urllib.request
        url = (f"https://api.themoviedb.org/3/movie/{tmdb_id}"
               f"?api_key={api_key}&language=en-US")
        req = urllib.request.Request(url, headers={"User-Agent": "MediaClinic/9.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        rating = data.get("vote_average")
        votes  = data.get("vote_count")
        if rating is not None and votes is not None:
            return f"{rating:.1f}", str(int(votes))
    except Exception:
        pass
    return None, None

def _fetch_omdb_rating(imdb_id, api_key):
    """
    Fetch rating and vote count from OMDb (IMDb data).
    Returns (rating_str, votes_str) or (None, None) on failure.
    """
    if not imdb_id or not api_key:
        return None, None
    try:
        import urllib.request
        url = f"https://www.omdbapi.com/?apikey={api_key}&i={imdb_id}&type=movie"
        req = urllib.request.Request(url, headers={"User-Agent": "MediaClinic/9.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get("Response") == "True":
            rating = data.get("imdbRating")
            votes  = data.get("imdbVotes", "").replace(",", "")
            if rating and rating != "N/A" and votes:
                return rating, votes
    except Exception:
        pass
    return None, None

def write_rating_to_files(nfo_path, xml_path, rating, votes):
    """
    Write rating and votes to all matching tags in NFO and XML.
    NFO: <rating>, <votes>
    XML: <IMDBrating>, <Rating>, <Votes>, <VoteCount>
    Preserves all other content.
    """
    errors = []

    def _replace_tag(content, tag, value):
        """Replace <tag>old</tag> or add before closing root if missing."""
        pattern = rf'(<{tag}[^>]*>)[^<]*(</\s*{tag}\s*>)'
        if re.search(pattern, content, re.IGNORECASE):
            return re.sub(pattern, rf'\g<1>{value}\2', content,
                          flags=re.IGNORECASE)
        return content   # tag not found: leave as-is (don't inject new tags)

    # NFO
    if nfo_path and os.path.isfile(nfo_path):
        try:
            with open(nfo_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            content = _replace_tag(content, "rating", rating)
            content = _replace_tag(content, "votes",  votes)
            with open(nfo_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            errors.append(f"NFO write error: {e}")

    # XML
    if xml_path and os.path.isfile(xml_path):
        try:
            with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            for tag in ["IMDBrating", "Rating"]:
                content = _replace_tag(content, tag, rating)
            for tag in ["Votes", "VoteCount"]:
                content = _replace_tag(content, tag, votes)
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            errors.append(f"XML write error: {e}")

    return errors

def get_movie_titles_from_files(nfo_path, xml_path):
    """
    Return list of unique non-empty movie titles found in NFO and XML.
    NFO: <title>, <originaltitle>
    XML: <LocalTitle>, <OriginalTitle>
    """
    titles = []

    def _extract_text(filepath, tags):
        if not filepath or not os.path.isfile(filepath): return
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if content.startswith('\ufeff'): content = content[1:]
            content_clean = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)
            root = ET.fromstring(content_clean)
            for tag in tags:
                el = root.find(tag)
                if el is not None:
                    txt = (el.text or "").strip()
                    if txt and txt not in titles:
                        titles.append(txt)
        except Exception: pass

    _extract_text(nfo_path,  ['title', 'originaltitle'])
    _extract_text(xml_path,  ['LocalTitle', 'OriginalTitle'])
    return titles

# ══════════════════════════════════════════════════════════════════════════════
# Scanning
# ══════════════════════════════════════════════════════════════════════════════

def scan_one_subfolder(sub_path, sub_name, use_ffprobe=None):
    """Full scan of a single subfolder. Returns result dict."""
    if use_ffprobe is None:
        use_ffprobe = SETTINGS.get("use_ffprobe", True)

    poster_path = os.path.join(sub_path, "poster.jpg")
    fanart_path = os.path.join(sub_path, "fanart.jpg")
    folder_path = os.path.join(sub_path, "folder.jpg")

    pe  = os.path.isfile(poster_path)
    fe  = os.path.isfile(fanart_path)
    fle = os.path.isfile(folder_path)
    pb  = os.path.getsize(poster_path)  if pe  else 0
    fb  = os.path.getsize(fanart_path)  if fe  else 0
    flb = os.path.getsize(folder_path)  if fle else 0
    pd  = get_image_dimensions(poster_path) if pe  else None
    fd  = get_image_dimensions(fanart_path) if fe  else None
    fld = get_image_dimensions(folder_path) if fle else None

    # Detailed health check for images
    ps_status, ps_desc   = check_image_health(poster_path, 'poster') if pe else (STATUS_MISSING, "")
    fs_status, fs_desc   = check_image_health(fanart_path, 'fanart') if fe else (STATUS_MISSING, "")
    fls_status, fls_desc = check_image_health(folder_path, 'folder') if fle else (STATUS_MISSING, "")

    # Only STATUS_ERROR (not STATUS_WARN) counts as corrupt for row health
    pc  = ps_status  == STATUS_ERROR
    fc  = fs_status  == STATUS_ERROR
    flc = fls_status == STATUS_ERROR

    bc, bp = count_backdrops(sub_path)

    nfo_path = os.path.join(sub_path, sub_name + ".nfo")
    ne  = os.path.isfile(nfo_path)
    nb  = os.path.getsize(nfo_path) if ne else 0
    nerr = validate_xml_file(nfo_path, is_nfo=True) if ne else []

    xml_path = os.path.join(sub_path, "movie.xml")
    xe  = os.path.isfile(xml_path)
    xb  = os.path.getsize(xml_path) if xe else 0
    xerr = validate_xml_file(xml_path, is_nfo=False) if xe else []
    lang = extract_language_from_xml(xml_path) if xe else "—"

    ns = (STATUS_ERROR if nerr else STATUS_OK) if ne else STATUS_MISSING
    xs = (STATUS_ERROR if xerr else STATUS_OK) if xe else STATUS_MISSING

    vi = scan_video_files(sub_path)

    # ffprobe for resolution (if enabled)
    if use_ffprobe and vi["video_path"] and FFPROBE_PATH:
        w, h = _get_video_resolution(vi["video_path"])
        vi["video_width"]   = w
        vi["video_height"]  = h
        vi["video_quality"] = classify_quality(w, h)

    si = scan_subtitles(sub_path, vi["video_path"])

    iso = SETTINGS.get("lang_ok_code", "PT")
    lang_ok = compute_lang_ok(vi["video_path"], si["subs_internal"], si["subs_external"],
                               nfo_path if ne else None,
                               xml_path if xe else None,
                               iso_code=iso)

    vs = (STATUS_MISSING if vi["video_count"] == 0
          else STATUS_ERROR if vi["video_count"] > 1 else STATUS_OK)

    # Genre (Phase 3)
    genres = get_genres_from_nfo(nfo_path if ne else None)
    genre_display, genre_status = classify_genres(genres)

    has_err = (ns == STATUS_ERROR or xs == STATUS_ERROR or pc or fc or flc)
    health  = ("red"    if has_err
               else "green" if (pe and fe and fle and
                                 ns == STATUS_OK and xs == STATUS_OK and
                                 vi["video_count"] == 1)
               else "yellow")

    return {
        "subfolder": sub_name, "subfolder_path": sub_path,
        "poster_exists": pe, "poster_path": poster_path,
        "poster_bytes": pb, "poster_size": format_size(pb) if pe else "—",
        "poster_dim": pd, "poster_corrupt": pc, "poster_desc": ps_desc,
        "poster_status": ps_status,
        "fanart_exists": fe, "fanart_path": fanart_path,
        "fanart_bytes": fb, "fanart_size": format_size(fb) if fe else "—",
        "fanart_dim": fd, "fanart_corrupt": fc, "fanart_desc": fs_desc,
        "fanart_status": fs_status,
        "folder_exists": fle, "folder_path": folder_path,
        "folder_bytes": flb, "folder_size": format_size(flb) if fle else "—",
        "folder_dim": fld, "folder_corrupt": flc, "folder_desc": fls_desc,
        "folder_status": fls_status,
        "backdrop_count": bc, "backdrop_paths": bp,
        "nfo_exists": ne, "nfo_path": nfo_path,
        "nfo_bytes": nb, "nfo_size": format_size(nb) if ne else "—",
        "nfo_status": ns, "nfo_errors": nerr,
        "xml_exists": xe, "xml_path": xml_path,
        "xml_bytes": xb, "xml_size": format_size(xb) if xe else "—",
        "xml_status": xs, "xml_errors": xerr,
        "language": lang,
        "video_count": vi["video_count"], "video_files": vi["video_files"],
        "video_ext": vi["video_ext"], "video_path": vi["video_path"],
        "video_bytes": vi["video_bytes"], "video_size": vi["video_size"],
        "video_width": vi["video_width"], "video_height": vi["video_height"],
        "video_quality": vi["video_quality"], "video_status": vs,
        "subs_internal": si["subs_internal"], "subs_external": si["subs_external"],
        "subs_summary": si["subs_summary"],
        "lang_ok": lang_ok,
        "genres": genres, "genre_display": genre_display, "genre_status": genre_status,
        "row_health": health,
    }

# ── JSON persistence helpers ───────────────────────────────────────────────────
def _results_to_json(results):
    return results

def _results_from_json(data):
    defaults = {
        "video_width": None, "video_height": None, "video_quality": "—",
        "lang_ok": "—", "pt_ok": "—", "backdrop_paths": [],
        "folder_exists": False, "folder_path": "", "folder_bytes": 0,
        "folder_size": "—", "folder_dim": None, "folder_corrupt": False,
        "folder_desc": "", "poster_desc": "", "fanart_desc": "",
        "poster_status": STATUS_MISSING, "fanart_status": STATUS_MISSING,
        "folder_status": STATUS_MISSING,
        "genres": [], "genre_display": "—", "genre_status": STATUS_ERROR,
    }
    out = []
    for r in data:
        row = dict(defaults)
        row.update(r)
        # Migrate old pt_ok → lang_ok if needed
        if "pt_ok" in row and "lang_ok" not in row:
            row["lang_ok"] = row["pt_ok"]
        out.append(row)
    return out

# ── Sort options ───────────────────────────────────────────────────────────────
SORT_OPTIONS = {
    "Subfolder (A→Z)":       (lambda r: r["subfolder"].lower(),   False),
    "Subfolder (Z→A)":       (lambda r: r["subfolder"].lower(),   True),
    "Poster size (lg→sm)":   (lambda r: r["poster_bytes"],        True),
    "Poster size (sm→lg)":   (lambda r: r["poster_bytes"],        False),
    "Fanart size (lg→sm)":   (lambda r: r["fanart_bytes"],        True),
    "Fanart size (sm→lg)":   (lambda r: r["fanart_bytes"],        False),
    "Video size (lg→sm)":    (lambda r: r["video_bytes"],         True),
    "Video size (sm→lg)":    (lambda r: r["video_bytes"],         False),
    "Language (A→Z)":        (lambda r: r["language"].lower(),    False),
    "Language (Z→A)":        (lambda r: r["language"].lower(),    True),
    "Quality (best first)":  (lambda r: _quality_sort_key(r.get("video_quality","—")), False),
    "Quality (worst first)": (lambda r: _quality_sort_key(r.get("video_quality","—")), True),
    "Lang OK? (Y first)":    (lambda r: r.get("lang_ok","—"),     False),
    "Lang OK? (N first)":    (lambda r: r.get("lang_ok","—"),     True),
    "Backdrops (most)":      (lambda r: r["backdrop_count"],      True),
    "Backdrops (fewest)":    (lambda r: r["backdrop_count"],      False),
    "Health (errors 1st)":   (lambda r: {"red":0,"yellow":1,"green":2}.get(r["row_health"],1), False),
    "Health (OK 1st)":       (lambda r: {"green":0,"yellow":1,"red":2}.get(r["row_health"],1), False),
}

# ══════════════════════════════════════════════════════════════════════════════
# Improvements engine
# ══════════════════════════════════════════════════════════════════════════════

def run_improvements(data_list, checks=None):
    """
    Run all enabled improvement checks on a list of row dicts.
    Returns a list of (movie_name, [issue_string, ...]) tuples.
    """
    if checks is None:
        checks = SETTINGS.get("improve_checks", _DEFAULT_SETTINGS["improve_checks"])

    max_xml_kb  = SETTINGS.get("max_xml_kb",  25)
    max_nfo_kb  = SETTINGS.get("max_nfo_kb",  50)
    min_bk      = SETTINGS.get("min_backdrops", 5)
    tag_pairs   = SETTINGS.get("tag_pairs") or DEFAULT_TAG_PAIRS

    results = []
    for d in data_list:
        issues = []
        name = d["subfolder"]

        # ── 2.1  Large XML ────────────────────────────────────────────────────
        if checks.get("large_xml", True):
            if d["xml_exists"] and d["xml_bytes"] > max_xml_kb * 1024:
                issues.append(
                    f"[Large XML] movie.xml is {d['xml_bytes']//1024} KB "
                    f"(threshold: {max_xml_kb} KB). "
                    "Large XML files may contain stale or duplicate data — consider reviewing.")
            if d["nfo_exists"] and d["nfo_bytes"] > max_nfo_kb * 1024:
                issues.append(
                    f"[Large NFO] {os.path.basename(d['nfo_path'])} is "
                    f"{d['nfo_bytes']//1024} KB "
                    f"(threshold: {max_nfo_kb} KB). Review for excess data.")

        # ── 2.2  NFO ↔ XML mismatch ───────────────────────────────────────────
        if checks.get("nfo_xml_diff", True) and d["nfo_exists"] and d["xml_exists"]:
            nfo_root = _parse_xml_to_dict(d["nfo_path"])
            xml_root = _parse_xml_to_dict(d["xml_path"])
            if nfo_root is not None and xml_root is not None:
                for nfo_path_str, xml_path_str, label, tol in tag_pairs:
                    # Special handling for id with moviedb attribute
                    if nfo_path_str.startswith("id") and "moviedb" in nfo_path_str:
                        pass  # handled below
                    # Get NFO values
                    nfo_vals = _xpath_get(nfo_root, nfo_path_str)
                    # Special: <id moviedb="imdb"> and <id moviedb="tmdb">
                    if not nfo_vals and nfo_path_str == "id":
                        nfo_vals = [v for el in nfo_root.iter('id')
                                    if not el.get('moviedb')
                                    for v in [(el.text or "").strip()] if v]
                    # Get XML values
                    xml_vals = _xpath_get(xml_root, xml_path_str)
                    if not nfo_vals or not xml_vals: continue
                    if not _vals_match(nfo_vals, xml_vals, tol):
                        nv = ", ".join(nfo_vals[:3])
                        xv = ", ".join(xml_vals[:3])
                        issues.append(
                            f"[NFO↔XML Mismatch] {label}: "
                            f"NFO='{nv}' vs XML='{xv}'")

                # Check XML standalone tags vs MediaInfo block
                for standalone, mi_path, mi_label, mi_tol in XML_INTERNAL_PAIRS:
                    sa_vals = _xpath_get(xml_root, standalone)
                    mi_vals = _xpath_get(xml_root, mi_path)
                    if not sa_vals or not mi_vals: continue
                    if not _vals_match(sa_vals, mi_vals, mi_tol):
                        sv = ", ".join(sa_vals[:2]); mv = ", ".join(mi_vals[:2])
                        issues.append(
                            f"[XML Internal] {mi_label}: "
                            f"standalone='{sv}' vs MediaInfo='{mv}'")

        # ── 2.3  FFprobe vs NFO/XML ───────────────────────────────────────────
        if (checks.get("ffprobe_diff", True) and d.get("video_path") and
                d["video_width"] and d["video_height"] and
                FFPROBE_PATH and SETTINGS.get("use_ffprobe", True)):
            probe = _get_ffprobe_full(d["video_path"])
            if probe:
                streams = probe.get("streams", [])
                v_streams = [s for s in streams if s.get("codec_type") == "video"]
                a_streams = [s for s in streams if s.get("codec_type") == "audio"]
                fmt       = probe.get("format", {})

                if v_streams:
                    vst = v_streams[0]
                    fp_w = vst.get("width"); fp_h = vst.get("height")
                    fp_dur = float(fmt.get("duration", 0) or 0)
                    fp_codec = (vst.get("codec_name") or "").lower()

                    # Compare with NFO fileinfo
                    if d["nfo_exists"]:
                        nfo_root = _parse_xml_to_dict(d["nfo_path"])
                        if nfo_root is not None:
                            nfo_w = _xpath_get(nfo_root, "fileinfo.streamdetails.video.width")
                            nfo_h = _xpath_get(nfo_root, "fileinfo.streamdetails.video.height")
                            nfo_dur = _xpath_get(nfo_root, "fileinfo.streamdetails.video.durationinseconds")
                            nfo_codec = _xpath_get(nfo_root, "fileinfo.streamdetails.video.codec")
                            if fp_w and nfo_w:
                                if not _vals_match(nfo_w, [str(fp_w)], 0):
                                    issues.append(
                                        f"[FFprobe vs NFO] Video width: "
                                        f"FFprobe={fp_w} vs NFO={nfo_w[0]}")
                            if fp_h and nfo_h:
                                if not _vals_match(nfo_h, [str(fp_h)], 0):
                                    issues.append(
                                        f"[FFprobe vs NFO] Video height: "
                                        f"FFprobe={fp_h} vs NFO={nfo_h[0]}")
                            if fp_dur and nfo_dur:
                                if not _vals_match(nfo_dur, [str(int(fp_dur))], 5):
                                    issues.append(
                                        f"[FFprobe vs NFO] Duration: "
                                        f"FFprobe={int(fp_dur)}s vs NFO={nfo_dur[0]}s")
                            if fp_codec and nfo_codec:
                                if _norm_val(fp_codec) not in _norm_val(nfo_codec[0]) and \
                                   _norm_val(nfo_codec[0]) not in _norm_val(fp_codec):
                                    issues.append(
                                        f"[FFprobe vs NFO] Video codec: "
                                        f"FFprobe={fp_codec} vs NFO={nfo_codec[0]}")

                    if d["xml_exists"] and v_streams:
                        xml_root = _parse_xml_to_dict(d["xml_path"])
                        if xml_root is not None:
                            xml_w = _xpath_get(xml_root, "VideoWidth") or _xpath_get(xml_root, "MediaInfo.Video.Width")
                            xml_h = _xpath_get(xml_root, "VideoHeight") or _xpath_get(xml_root, "MediaInfo.Video.Height")
                            xml_dur = _xpath_get(xml_root, "MediaInfo.Video.DurationSeconds") or _xpath_get(xml_root, "VideoLengthSeconds")
                            if fp_w and xml_w:
                                if not _vals_match(xml_w, [str(fp_w)], 0):
                                    issues.append(
                                        f"[FFprobe vs XML] Video width: "
                                        f"FFprobe={fp_w} vs XML={xml_w[0]}")
                            if fp_h and xml_h:
                                if not _vals_match(xml_h, [str(fp_h)], 0):
                                    issues.append(
                                        f"[FFprobe vs XML] Video height: "
                                        f"FFprobe={fp_h} vs XML={xml_h[0]}")
                            if fp_dur and xml_dur:
                                if not _vals_match(xml_dur, [str(int(fp_dur))], 5):
                                    issues.append(
                                        f"[FFprobe vs XML] Duration: "
                                        f"FFprobe={int(fp_dur)}s vs XML={xml_dur[0]}s")

        # ── 2.4  poster.jpg vs folder.jpg different sizes ─────────────────────
        if checks.get("poster_folder", True):
            if d["poster_exists"] and d["folder_exists"]:
                pw, ph = get_image_wh(d["poster_path"])
                fw, fh = get_image_wh(d["folder_path"])
                if pw and ph and fw and fh:
                    if pw != fw or ph != fh:
                        issues.append(
                            f"[Image Size] poster.jpg ({pw}×{ph}) and "
                            f"folder.jpg ({fw}×{fh}) have different dimensions — "
                            "they should be identical copies.")
                if abs(d["poster_bytes"] - d["folder_bytes"]) > 1024:
                    issues.append(
                        f"[Image Size] poster.jpg ({format_size(d['poster_bytes'])}) "
                        f"and folder.jpg ({format_size(d['folder_bytes'])}) "
                        "differ in file size — they may not be the same image.")

        # ── 2.5  Proportions & file size ─────────────────────────────────────
        if checks.get("proportions", True):
            for img_type, exists, path, sz, desc in [
                ("poster",  d["poster_exists"],  d["poster_path"],  d["poster_bytes"],  d.get("poster_desc","")),
                ("folder",  d["folder_exists"],  d["folder_path"],  d["folder_bytes"],  d.get("folder_desc","")),
                ("fanart",  d["fanart_exists"],  d["fanart_path"],  d["fanart_bytes"],  d.get("fanart_desc","")),
            ]:
                if exists and desc:
                    issues.append(f"[Image Quality] {os.path.basename(path)}: {desc}")

        # ── 2.6  Minimum backdrops ────────────────────────────────────────────
        if checks.get("backdrops", True):
            bc = d["backdrop_count"]
            if bc < min_bk:
                issues.append(
                    f"[Backdrops] Only {bc} backdrop(s) found "
                    f"(minimum recommended: {min_bk}). "
                    "Use 'Extract 10 backdrop frames' to add more.")

        if issues:
            results.append((name, issues))

    return results

def format_improvements_report(results, error_rows=None):
    """
    Format improvements results as a readable text report.
    error_rows: list of (movie_name, [error_string, ...]) for scan errors — shown in red.
    """
    if not results and not error_rows:
        return "✅  No improvements needed — all checks passed!\n"
    lines = []
    if results:
        lines.append(f"Improvement Report — {len(results)} movie(s) with findings\n")
        lines.append("=" * 60 + "\n")
        for name, issues in results:
            lines.append(f"\n📁  {name}\n")
            lines.append("─" * 50 + "\n")
            for iss in issues:
                lines.append(f"  • {iss}\n")
        lines.append("\n" + "=" * 60 + "\n")
        lines.append(f"Total improvement issues: {sum(len(v) for _, v in results)}\n")
    else:
        lines.append("✅  No improvement issues found.\n\n")

    # Append scan errors (item 3)
    if error_rows:
        lines.append("\n" + "=" * 60 + "\n")
        lines.append(f"SCAN ERRORS — {sum(len(v) for _, v in error_rows)} error(s) in {len(error_rows)} movie(s)\n")
        lines.append("=" * 60 + "\n")
        for name, errs in error_rows:
            lines.append(f"\n📁  {name}\n")
            lines.append("─" * 50 + "\n")
            for err in errs:
                lines.append(f"  ✖ {err}\n")

    return "".join(lines)

# ══════════════════════════════════════════════════════════════════════════════
# Frame extraction helpers
# ══════════════════════════════════════════════════════════════════════════════

def get_video_duration(video_path):
    if not FFPROBE_PATH or not SETTINGS.get("use_ffprobe", True): return None
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
        return False, stderr_tail or f"FFmpeg exit {r.returncode}"
    except subprocess.TimeoutExpired:
        return False, f"Extraction timed out after {timeout_sec}s"
    except Exception as e:
        return False, str(e)

# ══════════════════════════════════════════════════════════════════════════════
# Dialogs
# ══════════════════════════════════════════════════════════════════════════════

class FrameExtractionDialog(tk.Toplevel):
    """Progress dialog for extracting backdrop frames — smooth animation."""

    def __init__(self, parent, video_path, sub_path, timeout_sec=60):
        super().__init__(parent)
        self.title("Extract Backdrop(s)…")
        self.geometry("540x360")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._video_path  = video_path
        self._sub_path    = sub_path
        self._timeout_sec = timeout_sec
        self._cancelled   = False
        self._extracted   = []
        self._pct_target  = 0       # target for smooth animation
        self._pct_current = 0       # current animated value

        tk.Label(self, text="🎬  Extracting backdrop frames…",
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#cdd6f4"
                 ).pack(pady=(16, 2))
        tk.Label(self, text=os.path.basename(video_path),
                 font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086").pack(pady=(0, 8))

        self.status_var = tk.StringVar(value="Preparing…")
        tk.Label(self, textvariable=self.status_var, font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#a6adc8", wraplength=500).pack()

        self.eta_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.eta_var, font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#6c7086").pack()

        pf = tk.Frame(self, bg="#1e1e2e"); pf.pack(fill="x", padx=30, pady=(8, 4))
        self.pbar_canvas = tk.Canvas(pf, height=24, bg="#313244",
                                     highlightthickness=0, relief="flat")
        self.pbar_canvas.pack(fill="x")
        self._draw_progress(0)

        # Controls row
        ctrl = tk.Frame(self, bg="#1e1e2e"); ctrl.pack(pady=(6, 0))

        # Backdrop count spinner (item 14)
        tk.Label(ctrl, text="Backdrops to extract:", font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left", padx=(0, 4))
        self._count_var = tk.IntVar(value=SETTINGS.get("backdrop_count", 10))
        tk.Spinbox(ctrl, from_=1, to=50, textvariable=self._count_var,
                   width=4, font=("Helvetica", 9),
                   bg="#313244", fg="#cdd6f4", buttonbackground="#45475a",
                   relief="flat").pack(side="left", padx=(0, 18))

        tk.Label(ctrl, text="Per-frame timeout (s):", font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        self._timeout_var = tk.IntVar(value=timeout_sec)
        tk.Spinbox(ctrl, from_=10, to=300, textvariable=self._timeout_var,
                   width=5, font=("Helvetica", 9),
                   bg="#313244", fg="#cdd6f4", buttonbackground="#45475a",
                   relief="flat").pack(side="left", padx=(6, 0))

        tk.Button(self, text="  Cancel  ", font=("Helvetica", 10, "bold"),
                  bg="#f38ba8", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._on_cancel).pack(pady=(10, 16))

        self.after(150, self._start)
        self.after(50, self._animate_progress)

    def _draw_progress(self, pct):
        c = self.pbar_canvas; c.delete("all")
        w = c.winfo_width() or 480; h = 24
        c.create_rectangle(0, 0, w, h, fill="#313244", outline="")
        fw = int(w * pct / 100)
        if fw > 0:
            c.create_rectangle(0, 0, fw, h, fill="#2d6e3f", outline="")
        c.create_text(w//2, h//2, text=f"{int(pct)}%",
                      fill="#cdd6f4", font=("Helvetica", 10, "bold"))

    def _animate_progress(self):
        """Smoothly animate progress bar at ~20fps."""
        if self._pct_current < self._pct_target:
            step = max(0.5, (self._pct_target - self._pct_current) * 0.15)
            self._pct_current = min(self._pct_target, self._pct_current + step)
            self._draw_progress(self._pct_current)
        try:
            self.after(50, self._animate_progress)
        except Exception:
            pass

    def _on_cancel(self):
        self._cancelled = True
        self.status_var.set("Cancelling… (waiting for current frame)")

    def _start(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        video      = self._video_path
        sub        = self._sub_path
        t_limit    = max(10, self._timeout_var.get())
        n_frames   = max(1, min(50, self._count_var.get()))   # item 14: configurable count

        self.after(0, lambda: self.status_var.set("Reading video duration…"))
        duration = get_video_duration(video)

        if not duration or duration <= 0:
            self._finish_error("Cannot read video duration",
                "FFprobe could not read the video length.\n\n"
                "Possible causes:\n• Corrupt or incomplete file\n"
                "• Unsupported container format\n"
                "• File still being downloaded\n\n"
                "Try playing the file in VLC to confirm it works.")
            return

        if duration < 20:
            self._finish_error("Video too short",
                f"Video is only {duration:.0f}s — need at least 20s for extraction.")
            return

        if duration < 120:
            start_sec = 2; end_sec = duration - 2
        elif duration < 600:
            start_sec = duration * 0.05; end_sec = duration * 0.95
        else:
            start_sec = 300; end_sec = duration - 300

        if end_sec <= start_sec:
            end_sec = duration * 0.9; start_sec = duration * 0.1

        divisor    = max(1, n_frames - 1) if n_frames > 1 else 1
        interval   = (end_sec - start_sec) / divisor if end_sec > start_sec else 1
        timestamps = [start_sec + i * interval for i in range(n_frames)]
        start_num  = next_backdrop_number(sub)
        extracted  = []; failed = []
        frame_times = []

        for i, ts in enumerate(timestamps):
            if self._cancelled: break
            num   = start_num + i
            fname = ("backdrop.jpg" if num == 0 else f"backdrop{num}.jpg")
            out_p = os.path.join(sub, fname)
            mins  = int(ts // 60); secs_r = int(ts % 60)

            pct_per_frame = 100.0 / n_frames
            self._pct_target = int(i * pct_per_frame)

            self.after(0, lambda i=i, m=mins, s=secs_r, fn=fname, n=n_frames:
                       self.status_var.set(f"Frame {i+1}/{n}  at {m}:{s:02d}  →  {fn}"))

            t0 = time.time()
            ok, err_msg = extract_single_frame(video, ts, out_p, timeout_sec=t_limit)
            elapsed = time.time() - t0
            frame_times.append(elapsed)

            self._pct_target = int((i + 1) * pct_per_frame)

            if ok:
                extracted.append((fname, out_p))
            else:
                failed.append((i+1, f"{mins}:{secs_r:02d}", fname, err_msg))

            # ETA
            if frame_times:
                avg = sum(frame_times) / len(frame_times)
                remaining = avg * (n_frames - i - 1)
                if remaining > 60:
                    eta = f"ETA: {int(remaining//60)}m {int(remaining%60)}s"
                elif remaining > 0:
                    eta = f"ETA: {int(remaining)}s"
                else:
                    eta = "Almost done…"
                self.after(0, lambda e=eta: self.eta_var.set(e))

        self._extracted = [p for _, p in extracted]
        self._pct_target = 100

        if self._cancelled:
            for _, p in extracted:
                try: os.remove(p)
                except OSError: pass
            self.after(0, lambda: (
                self.status_var.set("Cancelled."),
                messagebox.showinfo("Cancelled",
                    "Extraction cancelled. Partial files removed.", parent=self),
                self.destroy()))
            return

        n_ok = len(extracted); n_bad = len(failed)
        if n_bad == 0:
            msg = (f"✅  All {n_frames} frame(s) extracted!\n\n"
                   f"Saved to: {sub}\n"
                   f"Files: backdrop.jpg / backdrop{start_num}.jpg → backdrop{start_num+n_ok-1}.jpg")
            self.after(0, lambda: (messagebox.showinfo("Done", msg, parent=self), self.destroy()))
        elif n_ok == 0:
            detail = "\n".join(f"  Frame {fi} at {ts}: {em}" for fi,ts,_,em in failed[:5])
            msg = (f"❌  No frames extracted.\n\nAll {n_frames} failed:\n{detail}\n\n"
                   "• Check the video codec is supported by your FFmpeg build\n"
                   "• Increase the per-frame timeout for large files\n"
                   "• Verify the file plays in VLC")
            self.after(0, lambda: (messagebox.showerror("Failed", msg, parent=self), self.destroy()))
        else:
            detail = "\n".join(f"  Frame {fi} at {ts}: {em}" for fi,ts,_,em in failed[:3])
            msg = (f"⚠️  {n_ok}/{n_frames} frames saved.\n\nFailed ({n_bad}):\n{detail}\n\n"
                   "Saved frames are usable. Failed frames may be damaged sections.")
            self.after(0, lambda: (messagebox.showwarning("Partial", msg, parent=self), self.destroy()))

    def _finish_error(self, title, message):
        self.after(0, lambda: (messagebox.showerror(title, message, parent=self), self.destroy()))


class ImprovementsDialog(tk.Toplevel):
    """Pop-up showing improvement findings with copy/save options."""

    def __init__(self, parent, report_text, movie_count):
        super().__init__(parent)
        self.title(f"🔍  Improvements — {movie_count} movie(s)")
        self.geometry("780x560")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(True, True)

        tk.Label(self, text="🔍  Improvement Findings",
                 font=("Helvetica", 13, "bold"), bg="#1e1e2e", fg="#f9e2af"
                 ).pack(anchor="w", padx=16, pady=(14, 2))

        fr = tk.Frame(self, bg="#1e1e2e")
        fr.pack(fill="both", expand=True, padx=16, pady=(4, 6))
        self._txt = t = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4",
                                font=("Consolas", 10), relief="flat", padx=10, pady=10)
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Colour tags
        t.tag_configure("h",      foreground="#89b4fa", font=("Consolas",10,"bold"))
        t.tag_configure("mv",     foreground="#a6e3a1", font=("Consolas",10,"bold"))
        t.tag_configure("mv_err", foreground="#f38ba8", font=("Consolas",10,"bold"))
        t.tag_configure("iss",    foreground="#f9e2af")
        t.tag_configure("err",    foreground="#f38ba8")   # scan errors in red
        t.tag_configure("ok",     foreground="#a6e3a1")
        t.tag_configure("sep",    foreground="#45475a")

        self._raw = report_text
        self._render(report_text)

        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(4, 12))
        tk.Button(bf, text="  📋 Copy to Clipboard  ",
                  font=("Helvetica", 10, "bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._copy).pack(side="left", padx=(0, 8))
        tk.Button(bf, text="  💾 Save to .txt  ",
                  font=("Helvetica", 10, "bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._save).pack(side="left", padx=(0, 8))
        tk.Button(bf, text="  Close  ",
                  font=("Helvetica", 10, "bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self.destroy).pack(side="left")

    def _render(self, text):
        t = self._txt
        t.configure(state="normal"); t.delete("1.0", "end")
        in_errors_section = False
        for line in text.splitlines():
            if "SCAN ERRORS" in line:
                in_errors_section = True
            if line.startswith("="):
                t.insert("end", line + "\n", "sep")
            elif line.startswith("─"):
                t.insert("end", line + "\n", "sep")
            elif line.startswith("📁"):
                tag = "mv_err" if in_errors_section else "mv"
                t.insert("end", line + "\n", tag)
            elif line.startswith("✅"):
                t.insert("end", line + "\n", "ok")
            elif in_errors_section and (line.strip().startswith("✖") or line.strip().startswith("•")):
                t.insert("end", line + "\n", "err")
            elif line.strip().startswith("•"):
                t.insert("end", line + "\n", "iss")
            elif line.startswith("Improvement Report") or line.startswith("Total") or line.startswith("SCAN ERRORS"):
                t.insert("end", line + "\n", "h")
            else:
                t.insert("end", line + "\n")
        t.configure(state="disabled")

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self._raw)
        messagebox.showinfo("Copied", "Report copied to clipboard.", parent=self)

    def _save(self):
        p = filedialog.asksaveasfilename(
            parent=self, title="Save Report",
            defaultextension=".txt",
            filetypes=[("Text files","*.txt"),("All","*.*")],
            initialfile="improvements_report.txt")
        if not p: return
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self._raw)
            messagebox.showinfo("Saved", f"Report saved to:\n{p}", parent=self)
        except Exception as e:
            messagebox.showerror("Save failed", str(e), parent=self)


class SubtitleDialog(tk.Toplevel):
    def __init__(self, parent, name, data):
        super().__init__(parent)
        self.title(f"Subtitles — {name}"); self.geometry("640x420")
        self.configure(bg="#1e1e2e"); self.transient(parent); self.grab_set()
        tk.Label(self, text=f"Subtitles — {name}", font=("Helvetica", 13, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", padx=16, pady=(14, 2))
        if data.get("video_path"):
            tk.Label(self, text=f"Video: {os.path.basename(data['video_path'])}",
                     font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086").pack(anchor="w", padx=16)
        fr = tk.Frame(self, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(6,6))
        t  = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4",
                     font=("Consolas",10), relief="flat", padx=10, pady=10)
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        for tag, fg_c, bold in [("h","#89b4fa",True),("l","#a6e3a1",False),
                                 ("d","#a6adc8",False),("s","#45475a",False),("n","#f38ba8",False)]:
            kw = {"foreground": fg_c}
            if bold: kw["font"] = ("Consolas", 10, "bold")
            t.tag_configure(tag, **kw)
        t.insert("end", "  EMBEDDED SUBTITLES  ", "h")
        t.insert("end", f"  {'(via ffprobe)' if FFPROBE_PATH else '(ffprobe not found)'}\n",
                 "d" if FFPROBE_PATH else "n")
        if data.get("subs_internal"):
            for i, s in enumerate(data["subs_internal"], 1):
                tl = f'  "{s["title"]}"' if s.get("title") else ""
                t.insert("end", f"    {i}. ", "d"); t.insert("end", s["lang"], "l")
                t.insert("end", f"{tl}\n", "d")
        elif FFPROBE_PATH:
            t.insert("end", "    None found\n", "n")
        t.insert("end", "\n  " + "─"*50 + "\n\n", "s")
        t.insert("end", "  EXTERNAL FILES\n", "h")
        if data.get("subs_external"):
            for i, s in enumerate(data["subs_external"], 1):
                t.insert("end", f"    {i}. ", "d"); t.insert("end", s["lang"], "l")
                t.insert("end", f'  →  {s["file"]}\n', "d")
        else:
            t.insert("end", "    None found\n", "n")
        t.configure(state="disabled")
        tk.Button(self, text="  Close  ", font=("Helvetica", 10, "bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self.destroy).pack(pady=(4,14))


class ErrorDialog(tk.Toplevel):
    def __init__(self, parent, title, filepath, errors):
        super().__init__(parent)
        self.title(title); self.geometry("740x440"); self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        tk.Label(self, text=title, font=("Helvetica", 13, "bold"),
                 bg="#1e1e2e", fg="#f38ba8").pack(anchor="w", padx=16, pady=(14,2))
        tk.Label(self, text=filepath, font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086",
                 wraplength=700, justify="left").pack(anchor="w", padx=16, pady=(0,10))
        fr = tk.Frame(self, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(0,6))
        t  = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4",
                     font=("Consolas",10), relief="flat", padx=10, pady=10)
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        t.tag_configure("eh", foreground="#f38ba8", font=("Consolas",10,"bold"))
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
        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(4,14))
        tk.Button(bf, text="  Open in editor  ", font=("Helvetica",10,"bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=lambda: open_in_editor(filepath)).pack(side="left", padx=(0,8))
        tk.Button(bf, text="  Close  ", font=("Helvetica",10,"bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self.destroy).pack(side="left")


class CopyMovieNameDialog(tk.Toplevel):
    """Show multiple movie name options and let user pick one to copy."""
    def __init__(self, parent, titles):
        super().__init__(parent)
        self.title("Copy Movie Name")
        self.geometry("480x280")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()

        tk.Label(self, text="Multiple movie names found.\nSelect one to copy:",
                 font=("Helvetica", 11), bg="#1e1e2e", fg="#cdd6f4",
                 justify="center").pack(pady=(16, 8))

        self._var = tk.StringVar(value=titles[0] if titles else "")
        for t in titles:
            tk.Radiobutton(self, text=t, variable=self._var, value=t,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(anchor="w", padx=30)

        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(12,12))
        tk.Button(bf, text="  Copy  ", font=("Helvetica",10,"bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._copy).pack(side="left", padx=(0,8))
        tk.Button(bf, text="  Cancel  ", font=("Helvetica",10,"bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self.destroy).pack(side="left")

    def _copy(self):
        val = self._var.get()
        if val:
            self.clipboard_clear()
            self.clipboard_append(val)
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 Dialogs — Ratings Compare / Manual Entry
# ══════════════════════════════════════════════════════════════════════════════

class RatingsCompareDialog(tk.Toplevel):
    """Side-by-side comparison of TMDb vs OMDb/IMDb ratings with Apply-to-All option."""

    def __init__(self, parent, movie_name, tmdb_r, tmdb_v, omdb_r, omdb_v):
        super().__init__(parent)
        self.title("Ratings Sync — Choose Source")
        self.geometry("500x320")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(False, False)

        self.choice    = None    # "tmdb" | "omdb" | "cancel"
        self.apply_all = False

        tk.Label(self, text=f"🎬  {movie_name}",
                 font=("Helvetica",11,"bold"), bg="#1e1e2e", fg="#cdd6f4"
                 ).pack(pady=(14,2))
        tk.Label(self, text="Two sources returned ratings. Which one should be saved?",
                 font=("Helvetica",10), bg="#1e1e2e", fg="#a6adc8"
                 ).pack(pady=(0,10))

        # Comparison table
        tbl = tk.Frame(self, bg="#313244"); tbl.pack(padx=24, fill="x")
        def _hdr(text, col):
            tk.Label(tbl, text=text, font=("Helvetica",10,"bold"),
                     bg="#45475a", fg="#89b4fa", padx=12, pady=6,
                     anchor="center").grid(row=0, column=col, sticky="ew", padx=1, pady=1)
        def _cell(text, row, col, hi=False):
            tk.Label(tbl, text=text, font=("Consolas",11),
                     bg="#313244" if not hi else "#2d3b2d",
                     fg="#cdd6f4" if not hi else "#a6e3a1",
                     padx=12, pady=8, anchor="center"
                     ).grid(row=row, column=col, sticky="ew", padx=1, pady=1)
        _hdr("", 0); _hdr("TMDb", 1); _hdr("OMDb / IMDb", 2)
        _cell("Rating", 1, 0); _cell(tmdb_r or "—", 1, 1); _cell(omdb_r or "—", 1, 2)
        _cell("Votes",  2, 0); _cell(tmdb_v or "—", 2, 1); _cell(omdb_v or "—", 2, 2)
        tbl.columnconfigure(0, weight=1); tbl.columnconfigure(1, weight=2); tbl.columnconfigure(2, weight=2)

        # Apply to all checkbox
        self._apply_all_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text="Apply this choice to all remaining movies",
                       variable=self._apply_all_var,
                       font=("Helvetica",9), bg="#1e1e2e", fg="#a6adc8",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(pady=(10,0))

        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(8,14))
        tk.Button(bf, text="  Use TMDb  ", font=("Helvetica",10,"bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=lambda: self._choose("tmdb")).pack(side="left", padx=(0,8))
        tk.Button(bf, text="  Use OMDb / IMDb  ", font=("Helvetica",10,"bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=lambda: self._choose("omdb")).pack(side="left", padx=(0,8))
        tk.Button(bf, text="  Cancel  ", font=("Helvetica",10,"bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=lambda: self._choose("cancel")).pack(side="left")
        self.protocol("WM_DELETE_WINDOW", lambda: self._choose("cancel"))

    def _choose(self, source):
        self.choice    = source
        self.apply_all = self._apply_all_var.get()
        self.destroy()


class ManualRatingDialog(tk.Toplevel):
    """Ask user to enter rating and votes manually when no API returned data."""

    def __init__(self, parent, movie_name):
        super().__init__(parent)
        self.title("Ratings Sync — Manual Entry")
        self.geometry("420x240")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(False, False)

        self.rating = None
        self.votes  = None

        tk.Label(self, text=f"🎬  {movie_name}",
                 font=("Helvetica",11,"bold"), bg="#1e1e2e", fg="#cdd6f4"
                 ).pack(pady=(14,2))
        tk.Label(self, text="Neither TMDb nor OMDb returned valid data.\nEnter values manually or Cancel to skip.",
                 font=("Helvetica",10), bg="#1e1e2e", fg="#a6adc8",
                 justify="center").pack(pady=(0,12))

        f = tk.Frame(self, bg="#1e1e2e"); f.pack(padx=30)
        tk.Label(f, text="Rating (e.g. 7.5):", font=("Helvetica",10),
                 bg="#1e1e2e", fg="#cdd6f4", width=20, anchor="w").grid(row=0, column=0, pady=4)
        self._rating_var = tk.StringVar()
        tk.Entry(f, textvariable=self._rating_var, font=("Consolas",10),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=12).grid(row=0, column=1, pady=4, padx=(8,0))
        tk.Label(f, text="Votes:", font=("Helvetica",10),
                 bg="#1e1e2e", fg="#cdd6f4", width=20, anchor="w").grid(row=1, column=0, pady=4)
        self._votes_var = tk.StringVar()
        tk.Entry(f, textvariable=self._votes_var, font=("Consolas",10),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=12).grid(row=1, column=1, pady=4, padx=(8,0))

        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(10,14))
        tk.Button(bf, text="  Save  ", font=("Helvetica",10,"bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._save).pack(side="left", padx=(0,8))
        tk.Button(bf, text="  Cancel (skip)  ", font=("Helvetica",10,"bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self._cancel).pack(side="left")
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _save(self):
        self.rating = self._rating_var.get().strip()
        self.votes  = self._votes_var.get().strip() or "0"
        self.destroy()

    def _cancel(self):
        self.rating = ""   # empty string signals "skip"
        self.votes  = ""
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# Settings Dialog
# ══════════════════════════════════════════════════════════════════════════════

class SettingsDialog(tk.Toplevel):
    """Full settings dialog with tabs — Phase 2 expanded."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title(f"Settings — {APP_NAME}")
        self.geometry("860x640")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(True, True)
        self._parent = parent

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=0, pady=0)
        style = ttk.Style()
        style.configure("TNotebook",     background="#1e1e2e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4",
                        padding=[12,6], font=("Helvetica",10))
        style.map("TNotebook.Tab",
                  background=[("selected","#45475a")],
                  foreground=[("selected","#89b4fa")])

        self._build_tools_tab(nb)
        self._build_api_keys_tab(nb)
        self._build_browser_tab(nb)
        self._build_language_tab(nb)
        self._build_improvements_tab(nb)
        self._build_image_sizes_tab(nb)
        self._build_genres_tab(nb)
        self._build_tags_tab(nb)

        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(6,12))
        tk.Button(bf, text="  Save & Close  ", font=("Helvetica",10,"bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._save_close).pack(side="left", padx=(0,8))
        tk.Button(bf, text="  Cancel  ", font=("Helvetica",10,"bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self.destroy).pack(side="left")

    # ── Shared widget helpers ─────────────────────────────────────────────────
    @staticmethod
    def _section(parent, label):
        tk.Label(parent, text=label, font=("Helvetica",11,"bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", padx=16, pady=(14,2))

    @staticmethod
    def _note(parent, text):
        tk.Label(parent, text=text, font=("Helvetica",9), bg="#1e1e2e", fg="#6c7086",
                 justify="left").pack(anchor="w", padx=16, pady=(0,2))

    @staticmethod
    def _row(parent):
        r = tk.Frame(parent, bg="#1e1e2e"); r.pack(fill="x", padx=16, pady=2)
        return r

    def _file_entry_row(self, parent, var, title, filetypes):
        r = self._row(parent)
        tk.Entry(r, textvariable=var, font=("Consolas",9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=50).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="Browse…", font=("Helvetica",9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: self._browse_file(var, title, filetypes)
                  ).pack(side="left", padx=(6,0))
        return r

    @staticmethod
    def _browse_file(var, title, filetypes):
        p = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if p: var.set(p)

    # ── Tools tab ─────────────────────────────────────────────────────────────
    def _build_tools_tab(self, nb):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text="🔧  Tools")

        # ── Text editor ──────────────────────────────────────────────────────
        self._section(f, "Text Editor (for NFO / XML files)")
        self._note(f, "Notepad++ is auto-detected. File path is passed BEFORE -lxml flag.\n"
                      "If left blank, falls back to OS default editor.")
        self._editor_var = tk.StringVar(value=SETTINGS.get("text_editor",""))
        r = self._file_entry_row(f, self._editor_var, "Select text editor",
                                  [("Executables","*.exe"),("All","*.*")])
        # Auto-fill: detect Notepad++
        npp = _find_notepadpp()
        if npp and not self._editor_var.get():
            self._editor_var.set(npp)
        tk.Button(r, text="Test", font=("Helvetica",9), bg="#45475a", fg="#a6e3a1",
                  relief="flat", cursor="hand2",
                  command=lambda: self._test_editor(self._editor_var)
                  ).pack(side="left", padx=(4,0))

        # ── FFmpeg ───────────────────────────────────────────────────────────
        self._section(f, "FFmpeg / FFprobe")
        self._note(f, "Point to the folder containing ffmpeg.exe and ffprobe.exe.\n"
                      "Leave blank to use system PATH.")
        self._ffmpeg_var = tk.StringVar(value=SETTINGS.get("ffmpeg_path",""))
        # Auto-fill: detect from PATH if field is empty
        if not self._ffmpeg_var.get():
            ff, _ = _find_ffmpeg_ffprobe("")
            if ff: self._ffmpeg_var.set(os.path.dirname(ff))
        r = self._row(f)
        tk.Entry(r, textvariable=self._ffmpeg_var, font=("Consolas",9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=50).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="Browse…", font=("Helvetica",9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: self._ffmpeg_var.set(
                      filedialog.askdirectory(title="FFmpeg folder") or self._ffmpeg_var.get())
                  ).pack(side="left", padx=(6,0))
        self._ff_status_lbl = tk.Label(r, text="", font=("Helvetica",9),
                                       bg="#1e1e2e", fg="#a6adc8")
        self._ff_status_lbl.pack(side="left", padx=(8,0))
        tk.Button(r, text="Test FFmpeg", font=("Helvetica",9), bg="#45475a", fg="#f9e2af",
                  relief="flat", cursor="hand2",
                  command=self._test_ffmpeg_btn).pack(side="left", padx=(4,0))

        # ── Backdrop count ────────────────────────────────────────────────────
        self._section(f, "Backdrop Extraction")
        self._note(f, "Default number of backdrop frames to extract per movie.")
        r = self._row(f)
        tk.Label(r, text="Default frame count:", font=("Helvetica",10),
                 bg="#1e1e2e", fg="#cdd6f4", width=26, anchor="w").pack(side="left")
        self._backdrop_count_var = tk.IntVar(value=SETTINGS.get("backdrop_count", 10))
        tk.Spinbox(r, from_=1, to=50, textvariable=self._backdrop_count_var, width=6,
                   font=("Helvetica",10), bg="#313244", fg="#cdd6f4",
                   buttonbackground="#45475a", relief="flat").pack(side="left")

        # ── Video Scraper / Metadata Source ───────────────────────────────────
        self._section(f, "Video Scraper / Metadata Source")
        self._note(f, "Choose the metadata source for ratings, votes, and IDs.\n"
                      "The scraper launch path remains available below.")
        r = self._row(f)
        tk.Label(r, text="Metadata source:", font=("Helvetica",10),
                 bg="#1e1e2e", fg="#cdd6f4", width=20, anchor="w").pack(side="left")
        self._meta_src_var = tk.StringVar(value=SETTINGS.get("metadata_source","tmdb"))
        for val, lbl in [("tmdb","TMDb (recommended)"), ("omdb","IMDb via OMDb API")]:
            tk.Radiobutton(r, text=lbl, variable=self._meta_src_var, value=val,
                           font=("Helvetica",10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(side="left", padx=(0,16))
        # Future feature note
        tk.Label(f, text="  ⚙  Online metadata fetching will be enabled in a future update.",
                 font=("Helvetica",9,"italic"), bg="#1e1e2e", fg="#6c7086"
                 ).pack(anchor="w", padx=16, pady=(2,0))

        self._note(f, "\nScraper executable (optional — launched with movie folder as argument):")
        self._scraper_var = tk.StringVar(value=SETTINGS.get("scraper_path",""))
        self._file_entry_row(f, self._scraper_var, "Select scraper",
                              [("Executables","*.exe"),("All","*.*")])

    def _test_editor(self, var):
        path = var.get().strip()
        if not path:
            messagebox.showwarning("Not set", "No editor path set.", parent=self); return
        if not os.path.isfile(path):
            messagebox.showerror("Not found", f"File not found:\n{path}", parent=self); return
        try:
            subprocess.Popen([path],
                             creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            messagebox.showinfo("Test", f"Editor launched:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Launch failed", str(e), parent=self)

    def _test_ffmpeg_btn(self):
        path = self._ffmpeg_var.get().strip()
        ff, fp = _find_ffmpeg_ffprobe(path)
        ff_ok, fp_ok, ff_msg, fp_msg = _test_ffmpeg(ff, fp)
        if ff_ok and fp_ok:
            self._ff_status_lbl.configure(text="✓ Both OK", fg="#a6e3a1")
        else:
            msgs = []
            if not ff_ok: msgs.append(f"ffmpeg: {ff_msg}")
            if not fp_ok: msgs.append(f"ffprobe: {fp_msg}")
            self._ff_status_lbl.configure(text="✗ " + " | ".join(msgs), fg="#f38ba8")

    # ── API Keys tab ──────────────────────────────────────────────────────────
    def _build_api_keys_tab(self, nb):
        outer = tk.Frame(nb, bg="#1e1e2e"); nb.add(outer, text="🔑  API Keys")

        # Scrollable inner frame
        canvas = tk.Canvas(outer, bg="#1e1e2e", highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        f = tk.Frame(canvas, bg="#1e1e2e")
        canvas.create_window((0,0), window=f, anchor="nw")
        f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # ── TMDb ─────────────────────────────────────────────────────────────
        self._section(f, "TMDb API Key (The Movie Database)")
        self._note(f, "Required for fetching ratings and metadata from TMDb.\n"
                      "Your key is stored locally in settings.json and never shared.\n"
                      "Free key — no subscription required.")
        self._tmdb_var = tk.StringVar(value=SETTINGS.get("tmdb_api_key",""))
        r = self._row(f)
        self._tmdb_entry = tk.Entry(r, textvariable=self._tmdb_var, font=("Consolas",9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=46, show="•")
        self._tmdb_entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="👁", font=("Helvetica",9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2", width=2,
                  command=lambda: self._toggle_show(self._tmdb_entry)
                  ).pack(side="left", padx=(4,0))
        tk.Button(r, text="Validate", font=("Helvetica",9), bg="#45475a", fg="#f9e2af",
                  relief="flat", cursor="hand2",
                  command=self._validate_tmdb).pack(side="left", padx=(4,0))
        self._tmdb_status = tk.Label(r, text="", font=("Helvetica",9),
                                     bg="#1e1e2e", fg="#a6adc8")
        self._tmdb_status.pack(side="left", padx=(6,0))

        # Get key link
        r2 = self._row(f)
        tk.Label(r2, text="No key yet?", font=("Helvetica",9),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        lnk1 = tk.Label(r2, text=" ➜ Click here to get your free TMDb API key",
                         font=("Helvetica",9,"underline"), bg="#1e1e2e", fg="#89b4fa",
                         cursor="hand2")
        lnk1.pack(side="left")
        lnk1.bind("<Button-1>", lambda e: open_url_with_browser(
            "https://www.themoviedb.org/settings/api"))

        self._note(f, "\nHow to get a TMDb key:\n"
                      "  1. Create a free account at themoviedb.org\n"
                      "  2. Go to Settings → API (left sidebar)\n"
                      "  3. Click 'Request an API Key' → choose Developer\n"
                      "  4. Fill in the form and your key appears immediately\n"
                      "  5. Copy the 'API Key (v3 auth)' value here")

        # separator
        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(12,0))

        # ── OMDb (IMDb via OMDb) ──────────────────────────────────────────────
        self._section(f, "OMDb API Key (IMDb data via OMDb)")
        self._note(f, "Required for fetching IMDb ratings via the OMDb API.\n"
                      "Your key is stored locally and never shared.\n"
                      "Free tier: 1,000 requests/day.")
        self._omdb_var = tk.StringVar(value=SETTINGS.get("omdb_api_key",""))
        r = self._row(f)
        self._omdb_entry = tk.Entry(r, textvariable=self._omdb_var, font=("Consolas",9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=46, show="•")
        self._omdb_entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="👁", font=("Helvetica",9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2", width=2,
                  command=lambda: self._toggle_show(self._omdb_entry)
                  ).pack(side="left", padx=(4,0))
        tk.Button(r, text="Validate", font=("Helvetica",9), bg="#45475a", fg="#f9e2af",
                  relief="flat", cursor="hand2",
                  command=self._validate_omdb).pack(side="left", padx=(4,0))
        self._omdb_status = tk.Label(r, text="", font=("Helvetica",9),
                                     bg="#1e1e2e", fg="#a6adc8")
        self._omdb_status.pack(side="left", padx=(6,0))

        r3 = self._row(f)
        tk.Label(r3, text="No key yet?", font=("Helvetica",9),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        lnk2 = tk.Label(r3, text=" ➜ Click here to get your free OMDb API key",
                         font=("Helvetica",9,"underline"), bg="#1e1e2e", fg="#89b4fa",
                         cursor="hand2")
        lnk2.pack(side="left")
        lnk2.bind("<Button-1>", lambda e: open_url_with_browser(
            "https://www.omdbapi.com/apikey.aspx"))

        self._note(f, "\nHow to get an OMDb key:\n"
                      "  1. Go to omdbapi.com/apikey.aspx\n"
                      "  2. Choose 'FREE' (1,000 req/day) and fill in your email\n"
                      "  3. Check your inbox for the activation email\n"
                      "  4. Click the activation link and copy your key here")

    @staticmethod
    def _toggle_show(entry):
        entry.configure(show="" if entry.cget("show") == "•" else "•")

    def _validate_tmdb(self):
        key = self._tmdb_var.get().strip()
        if not key:
            self._tmdb_status.configure(text="No key entered", fg="#f38ba8"); return
        self._tmdb_status.configure(text="Testing…", fg="#a6adc8")
        self.update_idletasks()
        def _worker():
            try:
                import urllib.request
                url = f"https://api.themoviedb.org/3/configuration?api_key={key}"
                req = urllib.request.Request(url, headers={"User-Agent": "MediaClinic/9.0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read())
                ok = "images" in data
            except Exception as e:
                ok = False
            def _apply():
                if ok:
                    self._tmdb_status.configure(text="✓ Valid", fg="#a6e3a1")
                else:
                    self._tmdb_status.configure(text="✗ Invalid or network error", fg="#f38ba8")
            self.after(0, _apply)
        threading.Thread(target=_worker, daemon=True).start()

    def _validate_omdb(self):
        key = self._omdb_var.get().strip()
        if not key:
            self._omdb_status.configure(text="No key entered", fg="#f38ba8"); return
        self._omdb_status.configure(text="Testing…", fg="#a6adc8")
        self.update_idletasks()
        def _worker():
            try:
                import urllib.request
                url = f"https://www.omdbapi.com/?apikey={key}&t=test&type=movie"
                req = urllib.request.Request(url, headers={"User-Agent": "MediaClinic/9.0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read())
                # OMDb returns Response=False with error when key is bad
                ok = data.get("Response") != "False" or "Unauthorized" not in data.get("Error","")
            except Exception:
                ok = False
            def _apply():
                if ok:
                    self._omdb_status.configure(text="✓ Valid", fg="#a6e3a1")
                else:
                    self._omdb_status.configure(text="✗ Invalid or network error", fg="#f38ba8")
            self.after(0, _apply)
        threading.Thread(target=_worker, daemon=True).start()

    # ── Browser tab ───────────────────────────────────────────────────────────
    def _build_browser_tab(self, nb):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text="🌐  Browser")

        self._section(f, "Default Browser for External Links")
        self._note(f, "Used when opening IMDB, TMDb, OpenSubtitles, or any other URL.\n"
                      "Leave on 'System Default' to let Windows decide.\n"
                      "Detected browsers are listed automatically.")

        self._browser_var = tk.StringVar(value=SETTINGS.get("default_browser",""))

        # Detect installed browsers
        detected = detect_installed_browsers()

        options_frame = tk.Frame(f, bg="#1e1e2e"); options_frame.pack(anchor="w", padx=24, pady=(6,0))

        # System default option
        tk.Radiobutton(options_frame, text="System Default (recommended)",
                       variable=self._browser_var, value="",
                       font=("Helvetica",10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(anchor="w", pady=2)

        if detected:
            for name, path in detected:
                tk.Radiobutton(options_frame, text=f"{name}",
                               variable=self._browser_var, value=path,
                               font=("Helvetica",10), bg="#1e1e2e", fg="#cdd6f4",
                               selectcolor="#313244", activebackground="#1e1e2e",
                               activeforeground="#cdd6f4").pack(anchor="w", pady=2)
                tk.Label(options_frame, text=f"   {path}",
                         font=("Consolas",8), bg="#1e1e2e", fg="#45475a").pack(anchor="w")
        else:
            tk.Label(options_frame, text="No additional browsers detected in standard locations.",
                     font=("Helvetica",9), bg="#1e1e2e", fg="#6c7086").pack(anchor="w", pady=4)

        # Manual path entry
        self._section(f, "Or Enter Browser Path Manually")
        self._note(f, "Browse to any browser executable not listed above.")
        r = self._row(f)
        tk.Entry(r, textvariable=self._browser_var, font=("Consolas",9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=50).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="Browse…", font=("Helvetica",9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: self._browse_file(self._browser_var, "Select browser",
                                                    [("Executables","*.exe"),("All","*.*")])
                  ).pack(side="left", padx=(6,0))
        tk.Button(r, text="Test", font=("Helvetica",9), bg="#45475a", fg="#a6e3a1",
                  relief="flat", cursor="hand2",
                  command=self._test_browser).pack(side="left", padx=(4,0))

    def _test_browser(self):
        p = self._browser_var.get().strip()
        if not p:
            messagebox.showinfo("System Default",
                                "Using system default browser — no path to test.", parent=self)
            return
        if not os.path.isfile(p):
            messagebox.showerror("Not found", f"File not found:\n{p}", parent=self); return
        try:
            subprocess.Popen([p, "https://www.themoviedb.org"],
                             creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            messagebox.showinfo("Test", f"Browser launched:\n{p}", parent=self)
        except Exception as e:
            messagebox.showerror("Launch failed", str(e), parent=self)

    # ── Language tab ──────────────────────────────────────────────────────────
    def _build_language_tab(self, nb):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text="🌍  Language OK?")

        tk.Label(f, text="Language OK? Column Target",
                 font=("Helvetica",12,"bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16,4))
        tk.Label(f, text="Select the language for the 'Lang OK?' column.\n"
                 "The column header and Y/N values will update automatically.\n"
                 "Sources checked: FFprobe audio, internal subtitles, external subtitles,\n"
                 "XML LanguageCode, XML Audio/Language, NFO video/language.",
                 font=("Helvetica",10), bg="#1e1e2e", fg="#a6adc8",
                 justify="left").pack(anchor="w", padx=16, pady=(0,12))

        self._lang_var = tk.StringVar(value=SETTINGS.get("lang_ok_code","PT"))
        lang_frame = tk.Frame(f, bg="#1e1e2e"); lang_frame.pack(padx=16, fill="x")
        tk.Label(lang_frame, text="Language:", font=("Helvetica",10),
                 bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self._lang_combo = ttk.Combobox(lang_frame, textvariable=self._lang_var,
                                        values=[iso for iso,_ in WORLD_LANGUAGES],
                                        state="readonly", width=8,
                                        font=("Helvetica",11))
        self._lang_combo.pack(side="left", padx=(8,16))
        self._lang_desc = tk.Label(lang_frame, text="", font=("Helvetica",10),
                                   bg="#1e1e2e", fg="#a6adc8")
        self._lang_desc.pack(side="left")
        self._lang_combo.bind("<<ComboboxSelected>>", self._update_lang_desc)
        self._update_lang_desc()

        tk.Label(f, text="\nAvailable languages:",
                 font=("Helvetica",10,"bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16)
        grid_f = tk.Frame(f, bg="#1e1e2e"); grid_f.pack(padx=16, fill="x")
        for i, (iso, name) in enumerate(WORLD_LANGUAGES):
            r = i // 3; c = i % 3
            tk.Label(grid_f, text=f"{iso} — {name}",
                     font=("Consolas",9), bg="#1e1e2e", fg="#6c7086",
                     anchor="w", width=22).grid(row=r, column=c, sticky="w", pady=1)

    def _update_lang_desc(self, *_):
        code = self._lang_var.get().upper()
        for iso, name in WORLD_LANGUAGES:
            if iso == code:
                self._lang_desc.configure(text=f"→ {name}")
                return
        self._lang_desc.configure(text="")

    # ── Improvements tab ──────────────────────────────────────────────────────
    def _build_improvements_tab(self, nb):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text="🔍  Improvements")

        tk.Label(f, text="Improvement Checks",
                 font=("Helvetica",12,"bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16,6))

        ic = SETTINGS.get("improve_checks", _DEFAULT_SETTINGS["improve_checks"])
        self._ic_vars = {}

        checks_def = [
            ("large_xml",    "2.1  Large XML/NFO files (flag files above threshold)"),
            ("nfo_xml_diff",  "2.2  NFO ↔ XML data mismatches"),
            ("ffprobe_diff",  "2.3  FFprobe vs NFO/XML metadata differences"),
            ("poster_folder", "2.4  poster.jpg and folder.jpg size differences"),
            ("proportions",   "2.5  Image proportion and file size issues"),
            ("backdrops",     "2.6  Insufficient backdrops"),
        ]
        for key, label in checks_def:
            v = tk.BooleanVar(value=ic.get(key, True))
            self._ic_vars[key] = v
            tk.Checkbutton(f, text=label, variable=v,
                           font=("Helvetica",10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(anchor="w", padx=24, pady=2)

        tk.Label(f, text="\nThresholds:", font=("Helvetica",11,"bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", padx=16)

        def _spin_row(parent, label, varname, default, from_, to_):
            r = tk.Frame(parent, bg="#1e1e2e"); r.pack(anchor="w", padx=24, pady=2)
            tk.Label(r, text=label, font=("Helvetica",10), bg="#1e1e2e", fg="#cdd6f4",
                     width=36, anchor="w").pack(side="left")
            v = tk.IntVar(value=SETTINGS.get(varname, default))
            setattr(self, f"_{varname}_var", v)
            tk.Spinbox(r, from_=from_, to=to_, textvariable=v, width=6,
                       font=("Helvetica",10), bg="#313244", fg="#cdd6f4",
                       buttonbackground="#45475a", relief="flat").pack(side="left")
            return v

        _spin_row(f, "Max NFO file size (KB) before flagging:",   "max_nfo_kb",  50,  1, 9999)
        _spin_row(f, "Max XML file size (KB) before flagging:",   "max_xml_kb",  25,  1, 9999)
        _spin_row(f, "Minimum backdrops required:",                "min_backdrops", 5, 1, 50)

    # ── Image Sizes tab ───────────────────────────────────────────────────────
    def _build_image_sizes_tab(self, nb):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text="🖼  Image Sizes")

        self._section(f, "Minimum Image File Sizes")
        self._note(f, "Files below the minimum are flagged as errors (🔴).\n"
                      "Set a value to 0 to skip the size check for that image type.")

        def _sz_row(parent, label, varname, default):
            r = tk.Frame(parent, bg="#1e1e2e"); r.pack(anchor="w", padx=24, pady=4)
            tk.Label(r, text=label, font=("Helvetica",10), bg="#1e1e2e", fg="#cdd6f4",
                     width=32, anchor="w").pack(side="left")
            v = tk.IntVar(value=SETTINGS.get(varname, default))
            setattr(self, f"_{varname}_var", v)
            tk.Spinbox(r, from_=0, to=9999, textvariable=v, width=6,
                       font=("Helvetica",10), bg="#313244", fg="#cdd6f4",
                       buttonbackground="#45475a", relief="flat").pack(side="left")
            tk.Label(r, text=" KB   (0 = skip check)", font=("Helvetica",9),
                     bg="#1e1e2e", fg="#6c7086").pack(side="left", padx=(6,0))

        _sz_row(f, "poster.jpg minimum size:",  "min_poster_kb", 100)
        _sz_row(f, "folder.jpg minimum size:",  "min_folder_kb", 100)
        _sz_row(f, "fanart.jpg minimum size:",  "min_fanart_kb", 200)

        self._section(f, "Proportion Checks")
        self._note(f, "Wrong proportions are flagged as warnings (🟡), not errors.\n"
                      "poster.jpg and folder.jpg: expected 2:3 portrait ratio (≈0.67)\n"
                      "fanart.jpg: expected 16:9 landscape ratio (≈1.78)")

    # ── Genres tab ────────────────────────────────────────────────────────────
    def _build_genres_tab(self, nb):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text="🎬  Genres")

        self._section(f, "Standard Genre List")
        self._note(f, "One genre per line. Based on TMDb's official genre list.\n"
                      "Add your own custom genres — they will be treated as valid.\n"
                      "Blank lines are removed automatically on save.")

        fr = tk.Frame(f, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(4,4))
        self._genres_text = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4",
                                     font=("Consolas",10), relief="flat", padx=8, pady=6,
                                     width=30)
        sb_g = ttk.Scrollbar(fr, orient="vertical", command=self._genres_text.yview)
        self._genres_text.configure(yscrollcommand=sb_g.set)
        self._genres_text.pack(side="left", fill="both", expand=True)
        sb_g.pack(side="right", fill="y")

        # Populate from settings (strip blank lines)
        raw = SETTINGS.get("genre_list", _DEFAULT_SETTINGS["genre_list"])
        cleaned = "\n".join(g for g in raw.splitlines() if g.strip())
        self._genres_text.insert("1.0", cleaned)

        br = tk.Frame(f, bg="#1e1e2e"); br.pack(fill="x", padx=16, pady=(0,4))
        tk.Button(br, text="Reset to TMDb defaults", font=("Helvetica",9),
                  bg="#45475a", fg="#f38ba8", relief="flat", cursor="hand2",
                  command=self._reset_genres).pack(side="left")

    def _reset_genres(self):
        self._genres_text.delete("1.0", "end")
        self._genres_text.insert("1.0", _DEFAULT_SETTINGS["genre_list"])

    # ── Tags tab ──────────────────────────────────────────────────────────────
    def _build_tags_tab(self, nb):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text="🏷  NFO-XML Tags")

        tk.Label(f, text="NFO ↔ XML Tag Comparison Pairs",
                 font=("Helvetica",12,"bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16,4))
        tk.Label(f, text="Format: NFO_tag  →  XML_tag  (one pair per line, tab or spaces separated)\n"
                 "Use dot notation for nested tags: fileinfo.streamdetails.video.width\n"
                 "Add optional tolerance% at end: fileinfo.streamdetails.video.durationinseconds  MediaInfo.Video.DurationSeconds  Duration  5",
                 font=("Helvetica",9), bg="#1e1e2e", fg="#6c7086",
                 justify="left").pack(anchor="w", padx=16, pady=(0,8))

        fr = tk.Frame(f, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(0,4))
        self._tags_text = tk.Text(fr, wrap="none", bg="#313244", fg="#cdd6f4",
                                  font=("Consolas",9), relief="flat", padx=8, pady=6)
        sb_v = ttk.Scrollbar(fr, orient="vertical",   command=self._tags_text.yview)
        sb_h = ttk.Scrollbar(fr, orient="horizontal", command=self._tags_text.xview)
        self._tags_text.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        self._tags_text.grid(row=0, column=0, sticky="nsew")
        sb_v.grid(row=0, column=1, sticky="ns")
        sb_h.grid(row=1, column=0, sticky="ew")
        fr.rowconfigure(0, weight=1); fr.columnconfigure(0, weight=1)

        pairs = SETTINGS.get("tag_pairs") or DEFAULT_TAG_PAIRS
        lines = []
        for nfo_p, xml_p, label, tol in pairs:
            lines.append(f"{nfo_p}\t{xml_p}\t{label}\t{tol}")
        self._tags_text.insert("1.0", "\n".join(lines))

        br = tk.Frame(f, bg="#1e1e2e"); br.pack(fill="x", padx=16, pady=(0,4))
        tk.Button(br, text="Reset to defaults", font=("Helvetica",9),
                  bg="#45475a", fg="#f38ba8", relief="flat", cursor="hand2",
                  command=self._reset_tags).pack(side="left")

    def _reset_tags(self):
        self._tags_text.delete("1.0", "end")
        lines = []
        for nfo_p, xml_p, label, tol in DEFAULT_TAG_PAIRS:
            lines.append(f"{nfo_p}\t{xml_p}\t{label}\t{tol}")
        self._tags_text.insert("1.0", "\n".join(lines))

    def _parse_tags_text(self):
        raw = self._tags_text.get("1.0", "end").strip()
        pairs = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = re.split(r'\t|  +', line)
            if len(parts) >= 2:
                nfo_p = parts[0].strip()
                xml_p = parts[1].strip()
                label = parts[2].strip() if len(parts) > 2 else nfo_p
                tol   = int(parts[3].strip()) if len(parts) > 3 else 0
                pairs.append((nfo_p, xml_p, label, tol))
        return pairs if pairs else None

    # ── Save ──────────────────────────────────────────────────────────────────
    def _save_close(self):
        SETTINGS["text_editor"]      = self._editor_var.get().strip()
        SETTINGS["ffmpeg_path"]      = self._ffmpeg_var.get().strip()
        SETTINGS["scraper_path"]     = self._scraper_var.get().strip()
        SETTINGS["tmdb_api_key"]     = self._tmdb_var.get().strip()
        SETTINGS["omdb_api_key"]     = self._omdb_var.get().strip()
        SETTINGS["default_browser"]  = self._browser_var.get().strip()
        SETTINGS["lang_ok_code"]     = self._lang_var.get().upper()
        SETTINGS["improve_checks"]   = {k: v.get() for k, v in self._ic_vars.items()}
        SETTINGS["max_nfo_kb"]       = self._max_nfo_kb_var.get()
        SETTINGS["max_xml_kb"]       = self._max_xml_kb_var.get()
        SETTINGS["min_backdrops"]    = self._min_backdrops_var.get()
        SETTINGS["min_poster_kb"]    = self._min_poster_kb_var.get()
        SETTINGS["min_folder_kb"]    = self._min_folder_kb_var.get()
        SETTINGS["min_fanart_kb"]    = self._min_fanart_kb_var.get()
        SETTINGS["backdrop_count"]   = self._backdrop_count_var.get()
        SETTINGS["metadata_source"]  = self._meta_src_var.get()
        # Genre list — strip blank lines
        raw_genres = self._genres_text.get("1.0", "end")
        SETTINGS["genre_list"] = "\n".join(
            g.strip() for g in raw_genres.splitlines() if g.strip())
        parsed_tags = self._parse_tags_text()
        SETTINGS["tag_pairs"] = parsed_tags

        refresh_ffmpeg_paths()
        _save_settings(SETTINGS)

        if hasattr(self._parent, "_on_settings_changed"):
            self._parent._on_settings_changed()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# Help Dialog
# ══════════════════════════════════════════════════════════════════════════════

class HelpDialog(tk.Toplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.title(f"Help — {APP_NAME}")
        self.geometry("760x580")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(True, True)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        style = ttk.Style()
        style.configure("TNotebook",     background="#1e1e2e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4",
                        padding=[12,6], font=("Helvetica",10))
        style.map("TNotebook.Tab",
                  background=[("selected","#45475a")],
                  foreground=[("selected","#89b4fa")])

        self._add_tab(nb, "📖  System Help",  self._SYS)
        self._add_tab(nb, "🔧  FFmpeg Help",  self._FF)
        self._add_about_tab(nb)

        tk.Button(self, text="  Close  ", font=("Helvetica",10,"bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self.destroy).pack(pady=(6,12))

    _SYS = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Metadata & MediaClinic  —  System Guide  v0.8
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT DOES THIS APP DO?
  Metadata & MediaClinic audits your KODI media library. It scans
  a root folder (one subfolder = one movie) and checks every piece
  of artwork and metadata, giving you a colour-coded health report.

GETTING STARTED
  1. Click Browse… and select your root media folder.
  2. Click Scan. The table fills in as each phase completes:
       Phase 1 — Subfolders listed
       Phase 2 — Poster / folder.jpg / fanart images
       Phase 3 — NFO and XML metadata files
       Phase 4 — Video files + FFprobe (resolution, quality, subs)
  3. Green row  = everything present and valid.
     Yellow row = something is missing (not necessarily an error).
     Red row    = a file has a structural error or bad image header.
  4. Your last scan is saved automatically and reloaded on startup.

COLUMNS EXPLAINED
  Subfolder   — movie folder name
  Poster / Size — poster.jpg status and file size
  Folder / Size — folder.jpg status and file size
  Fanart / Size — fanart.jpg status and file size
  Bkdrps      — number of backdrop.jpg files found
  .nfo / OK?  — NFO presence and XML validity
  .xml / OK?  — movie.xml presence and XML validity
  Language    — language read from XML <Language> tag
  Video / Size — video file extension and size
  Quality     — resolution class (4K / 1080p / 720p / etc.)
  Lang OK?    — Y if target language audio or subtitle is found
  Subtitles   — summary of embedded and external subtitle tracks

INTERACTING WITH ROWS
  Double-click   — opens the file for that column (image, video, NFO…)
  Right-click    — context menu with all actions for that row
  Shift+↑/↓     — extend selection to multiple rows
  Page Up/Down   — navigate 20 rows at a time
  Home / End     — jump to first / last row

DOUBLE-CLICK ACTIONS
  • Poster/Folder/Fanart columns  → opens the image
  • NFO/XML column (no errors)    → opens file in text editor
  • NFO/XML column (errors)       → shows error detail dialog
  • Video column                  → plays the video
  • Subtitles column              → opens subtitle detail dialog
  • Subfolder column              → opens the folder in Explorer

RIGHT-CLICK MENU
  Open subfolder        — open in Explorer/Finder
  poster / folder / fanart — open image file
  Play video            — play with default player
  Extract 10 backdrops  — extract frames via FFmpeg
  Subtitles…            — detailed subtitle info
  Open NFO / XML        — open in configured text editor
  NFO/XML errors        — show error details
  Open on IMDB          — open movie page on IMDB (reads XML for ID)
  Open on TMDb          — open movie page on TheMovieDB
  Copy Movie Name       — copies title to clipboard; shows picker if
                          NFO and XML have different titles
  Run Improvements      — health-check for this row (or all selected)
  Open in Scraper       — launch scraper with this movie's folder
  Re-validate           — re-scan this single row without full rescan

SCAN OPTIONS
  FFprobe checkbox      — uncheck to skip FFprobe (faster scan; leaves
                          quality/resolution/subtitles blank)
  Update Scan           — re-scan the same folder without browsing
  Update Sort button    — re-sort in memory without rescanning

AUTO-SIZE COLUMNS
  Click "Auto-size Columns" to fit all columns to their content width.

EXPORT CSV
  Exports the full results table to a CSV file.

IMPROVEMENTS (right-click)
  Runs configurable health checks on selected movie(s):
  • Large XML/NFO files
  • NFO ↔ XML data mismatches
  • FFprobe vs metadata differences
  • poster.jpg ≠ folder.jpg
  • Wrong image proportions or file size
  • Too few backdrop files
  Results appear in a popup with Copy and Save options.
  Configure which checks run, and set thresholds, in Settings.

SETTINGS (menu bar)
  Tools         — text editor path, FFmpeg path, scraper path
  Language OK?  — choose which language to check in the Lang OK? column
  Improvements  — toggle checks on/off, set thresholds
  NFO-XML Tags  — edit the tag comparison pairs used in check 2.2
"""

    _FF = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FFmpeg & Compatible Tools
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHY DOES THIS APP USE FFMPEG?
  FFmpeg is a free, open-source multimedia framework. This app
  uses two of its tools:

  ffprobe  — reads video metadata: resolution, codec, duration,
             audio tracks, subtitle tracks.
  ffmpeg   — extracts JPEG frames from video for backdrop images.

WITHOUT FFMPEG:
  • Video quality column shows "—"
  • Embedded subtitle tracks not listed
  • Extract Frames button is disabled

HOW TO INSTALL FFMPEG ON WINDOWS:
  1. Go to  https://ffmpeg.org/download.html
  2. Under "Windows builds" click "gyan.dev" or "BtbN".
  3. Download the "ffmpeg-release-essentials.zip".
  4. Extract to a permanent folder, e.g.  C:\\Tools\\ffmpeg\\
  5. Inside you'll find a "bin" subfolder with ffmpeg.exe +
     ffprobe.exe.
  6. In Settings → Tools, set the FFmpeg path to that "bin" folder.
  7. Click "Test FFmpeg" — both should show green.

FFPROBE CHECKBOX:
  The "FFprobe" checkbox next to the Scan buttons lets you skip
  FFprobe during scans. This is useful for large libraries where
  you want a fast re-scan to check for new files without waiting
  for every video to be analysed.
  When unchecked, Quality shows "—" and Lang OK? only uses
  XML/NFO sources.

COMPATIBLE VIDEO SCRAPERS:
  The app can launch a configured scraper with the movie folder
  path as an argument. Compatible scrapers include:

  • tinyMediaManager (https://www.tinymediamanager.org/)
    — leading open-source scraper; supports NFO + XML output;
      pass folder with: tinyMediaManager.exe "C:\\Movies\\MovieName"

  • Ember Media Manager (https://www.embermm.com/)
    — Windows-only; excellent artwork scraper for KODI libraries.

  • MediaElch (https://www.kvibes.de/mediaelch/)
    — cross-platform; supports KODI NFO format natively.

  Set the scraper path in Settings → Tools. The app passes the
  full movie folder path as the first argument.

BACKDROP EXTRACTION:
  When you right-click → Extract 10 backdrop frames, the app:
  1. Reads video duration with ffprobe.
  2. Spreads 10 timestamps evenly across the movie.
  3. Calls ffmpeg to extract one JPEG frame per timestamp.
  4. Saves as backdrop.jpg, backdrop1.jpg … backdrop9.jpg.
  A smooth progress bar with ETA keeps you informed.
  You can set the per-frame timeout in the extraction dialog.
"""

    def _add_tab(self, nb, label, text):
        frame = tk.Frame(nb, bg="#1e1e2e"); nb.add(frame, text=label)
        t = tk.Text(frame, wrap="word", bg="#313244", fg="#cdd6f4",
                    font=("Helvetica",10), relief="flat", padx=14, pady=12,
                    spacing1=2, spacing3=2)
        sb = ttk.Scrollbar(frame, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        t.insert("end", text); t.configure(state="disabled")

    def _add_about_tab(self, nb):
        frame = tk.Frame(nb, bg="#1e1e2e"); nb.add(frame, text="ℹ️  About")
        about = (
            f"  {APP_NAME}\n"
            f"  Version {APP_VERSION}\n\n"
            f"  Created by:  {APP_AUTHOR}\n"
            f"  Contact:     {APP_EMAIL}\n\n"
            "  ────────────────────────────────────────\n\n"
            "  Built to keep KODI media libraries clean,\n"
            "  complete, and metadata-perfect.\n\n"
            "  ────────────────────────────────────────\n\n"
            "  VERSION HISTORY\n\n"
            "  v0.8.0  — Settings menu, Improvements health-check,\n"
            "             IMDB/TMDb links, Copy Movie Name, Auto-size\n"
            "             Columns, FFprobe checkbox, configurable\n"
            "             language column, phased scan, smooth backdrop\n"
            "             progress, Shift+select, image error details,\n"
            "             & suppressed in validator, quality fix.\n\n"
            "  v0.7.0  — Quality column, PT OK?, persistent sessions,\n"
            "             ffmpeg validation, improved extraction, Help.\n\n"
            "  v0.6.x  — Previous release (folder_scanner_v6).\n\n"
            "  ────────────────────────────────────────\n\n"
            "  Feedback and bug reports welcome at:\n"
            f"  {APP_EMAIL}\n"
        )
        tk.Label(frame, text=about, font=("Helvetica",10),
                 bg="#1e1e2e", fg="#cdd6f4", justify="left",
                 anchor="nw", padx=24, pady=20).pack(fill="both", expand=True)


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
                 font=("Consolas",9,"bold"), padx=8, pady=4,
                 wraplength=420, justify="left").pack()

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
        self.geometry("1600x760"); self.minsize(1200, 560)
        self.configure(bg="#1e1e2e")
        self._item_map    = {}
        self._results     = []
        self._folder      = None
        self._scanning    = False
        self._cancel_scan = False
        self._use_ffprobe = tk.BooleanVar(value=SETTINGS.get("use_ffprobe", True))
        self._build_ui()
        self._update_extract_btn_state()
        self.after(200, self._restore_last_session)

    # ── Build UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Menu bar
        menubar = tk.Menu(self, bg="#313244", fg="#cdd6f4",
                          activebackground="#585b70", activeforeground="#cdd6f4")
        self.configure(menu=menubar)
        settings_menu = tk.Menu(menubar, tearoff=0, bg="#313244", fg="#cdd6f4",
                                activebackground="#585b70", activeforeground="#cdd6f4")
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="⚙️  All Settings…",
                                  command=lambda: SettingsDialog(self))
        settings_menu.add_separator()
        settings_menu.add_command(label="🔧  Tools (Editor / FFmpeg / Backdrop)",
                                  command=lambda: SettingsDialog(self))
        settings_menu.add_command(label="🔑  API Keys (TMDb / OMDb)",
                                  command=lambda: SettingsDialog(self))
        settings_menu.add_command(label="🌐  Browser Selection",
                                  command=lambda: SettingsDialog(self))
        settings_menu.add_command(label="🌍  Language OK?",
                                  command=lambda: SettingsDialog(self))
        settings_menu.add_command(label="🔍  Improvements",
                                  command=lambda: SettingsDialog(self))
        settings_menu.add_command(label="🖼  Image Sizes",
                                  command=lambda: SettingsDialog(self))
        settings_menu.add_command(label="🎬  Genres",
                                  command=lambda: SettingsDialog(self))
        settings_menu.add_command(label="🏷  NFO-XML Tags",
                                  command=lambda: SettingsDialog(self))

        help_menu = tk.Menu(menubar, tearoff=0, bg="#313244", fg="#cdd6f4",
                            activebackground="#585b70", activeforeground="#cdd6f4")
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="📖  Help…", command=lambda: HelpDialog(self))

        tools_menu = tk.Menu(menubar, tearoff=0, bg="#313244", fg="#cdd6f4",
                             activebackground="#585b70", activeforeground="#cdd6f4")
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="🎬  Normalize Genres — All Movies",
                               command=self._normalize_genres_all)
        tools_menu.add_command(label="⭐  Sync Ratings — Selected Movies",
                               command=self._sync_ratings_selected)

        # ── Header row ────────────────────────────────────────────────────────
        header = tk.Frame(self, bg="#1e1e2e")
        header.pack(fill="x", padx=20, pady=(14,4))

        tk.Label(header, text=f"🎬  {APP_NAME}",
                 font=("Helvetica",17,"bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(side="left")

        right_hdr = tk.Frame(header, bg="#1e1e2e"); right_hdr.pack(side="right")
        self._ff_frame = tk.Frame(right_hdr, bg="#1e1e2e")
        self._ff_frame.pack(side="left")
        self._build_ffmpeg_status(self._ff_frame)

        # ── Picker row ────────────────────────────────────────────────────────
        picker = tk.Frame(self, bg="#1e1e2e"); picker.pack(fill="x", padx=20, pady=(0,6))
        self.folder_var = tk.StringVar(value="No folder selected")
        tk.Label(picker, textvariable=self.folder_var,
                 font=("Helvetica",10), bg="#313244", fg="#a6adc8",
                 anchor="w", padx=10, pady=6, relief="flat"
                 ).pack(side="left", fill="x", expand=True, ipady=2)

        btn_kw = dict(font=("Helvetica",10,"bold"), relief="flat", cursor="hand2")
        tk.Button(picker, text="  Browse…  ", bg="#89b4fa", fg="#1e1e2e",
                  command=self._browse, **btn_kw).pack(side="left", padx=(8,0))
        self.scan_btn = tk.Button(picker, text="  Scan  ", bg="#a6e3a1", fg="#1e1e2e",
                                  command=self._scan, **btn_kw)
        self.scan_btn.pack(side="left", padx=(6,0))
        self.update_btn = tk.Button(picker, text="  Update Scan  ", bg="#89dceb", fg="#1e1e2e",
                                    command=self._update_scan, **btn_kw)
        self.update_btn.pack(side="left", padx=(6,0))
        self.cancel_btn = tk.Button(picker, text="  Cancel  ", bg="#f38ba8", fg="#1e1e2e",
                                    command=self._cancel, **btn_kw)
        self.extract_btn = tk.Button(picker, text="  Extract Frames  ", bg="#fab387",
                                     fg="#1e1e2e", command=self._extract_frames, **btn_kw)
        self.extract_btn.pack(side="left", padx=(6,0))
        tk.Button(picker, text="  Export CSV  ", bg="#cba6f7", fg="#1e1e2e",
                  command=self._export_csv, **btn_kw).pack(side="left", padx=(6,0))

        # FFprobe checkbox
        tk.Checkbutton(picker, text="FFprobe", variable=self._use_ffprobe,
                       command=self._on_ffprobe_toggle,
                       font=("Helvetica",9), bg="#1e1e2e", fg="#a6adc8",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left", padx=(10,0))

        # ── Sort row ──────────────────────────────────────────────────────────
        sr = tk.Frame(self, bg="#1e1e2e"); sr.pack(fill="x", padx=20, pady=(0,2))
        tk.Label(sr, text="Sort:", font=("Helvetica",10),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        self.sort_var = tk.StringVar(value=SETTINGS.get("sort_option","Subfolder (A→Z)"))
        self._sort_combo = ttk.Combobox(sr, textvariable=self.sort_var,
                                        values=list(SORT_OPTIONS.keys()),
                                        state="readonly", width=28, font=("Helvetica",10))
        self._sort_combo.pack(side="left", padx=(6,0))
        # Item 1: auto-update table when sort changes — no button click needed
        self._sort_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_table())
        tk.Button(sr, text=" ↺ Update Sort ", font=("Helvetica",9,"bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self._refresh_table).pack(side="left", padx=(6,0))
        tk.Button(sr, text=" ⟺ Auto-size Columns ", font=("Helvetica",9,"bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self._auto_size_all).pack(side="left", padx=(6,0))

        # Legend
        lg = tk.Frame(sr, bg="#1e1e2e"); lg.pack(side="right")
        for c, lbl in [("#a6e3a1","All OK"),("#f9e2af","Missing"),("#f38ba8","Errors")]:
            tk.Label(lg, text="■", font=("Helvetica",12), bg="#1e1e2e", fg=c
                     ).pack(side="left", padx=(10,0))
            tk.Label(lg, text=lbl, font=("Helvetica",9), bg="#1e1e2e", fg="#a6adc8"
                     ).pack(side="left", padx=(2,0))

        # ── Progress bar ──────────────────────────────────────────────────────
        self.progress_frame = tk.Frame(self, bg="#1e1e2e")
        self.progress_frame.pack(fill="x", padx=20, pady=(0,2))
        self.pbar_canvas = tk.Canvas(self.progress_frame, height=22,
                                     bg="#313244", highlightthickness=0)
        self.pbar_label  = tk.Label(self.progress_frame, text="",
                                    font=("Helvetica",9), bg="#1e1e2e", fg="#6c7086")

        # ── Stats ──────────────────────────────────────────────────────────────
        self.stats_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.stats_var,
                 font=("Helvetica",9), bg="#1e1e2e", fg="#6c7086"
                 ).pack(anchor="w", padx=22)

        # ── Table ──────────────────────────────────────────────────────────────
        tf = tk.Frame(self, bg="#1e1e2e")
        tf.pack(fill="both", expand=True, padx=20, pady=(4,16))

        style = ttk.Style(self); style.theme_use("clam")
        style.configure("Treeview", background="#313244", foreground="#cdd6f4",
                        fieldbackground="#313244", rowheight=26,
                        font=("Helvetica",10))
        style.configure("Treeview.Heading", background="#45475a", foreground="#89b4fa",
                        font=("Helvetica",10,"bold"), relief="flat")
        style.map("Treeview",
                  background=[("selected","#585b70")],
                  foreground=[("selected","#cdd6f4")])

        cols = ("subfolder","poster","poster_sz","folder","folder_sz",
                "fanart","fanart_sz","backdrops","nfo","nfo_ok","xml","xml_ok",
                "language","vid_ext","vid_size","quality","lang_ok","subs","genre")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                 selectmode="extended")   # extended for shift-select

        iso = SETTINGS.get("lang_ok_code", "PT")
        lang_ok_label = f"{iso} OK?"

        col_defs = [
            ("subfolder", "Subfolder",  240, "w",      True),
            ("poster",    "Poster",      56, "center", False),
            ("poster_sz", "Size",        72, "center", False),
            ("folder",    "Folder",      56, "center", False),
            ("folder_sz", "Size",        72, "center", False),
            ("fanart",    "Fanart",      56, "center", False),
            ("fanart_sz", "Size",        72, "center", False),
            ("backdrops", "Bkdrps",      52, "center", False),
            ("nfo",       ".nfo",        44, "center", False),
            ("nfo_ok",    "OK?",         40, "center", False),
            ("xml",       ".xml",        44, "center", False),
            ("xml_ok",    "OK?",         40, "center", False),
            ("language",  "Language",    82, "center", False),
            ("vid_ext",   "Video",       52, "center", False),
            ("vid_size",  "Vid Size",    74, "center", False),
            ("quality",   "Quality",     74, "center", False),
            ("lang_ok",   lang_ok_label, 58, "center", False),
            ("subs",      "Subtitles",  180, "w",      True),
            ("genre",     "Genres",     160, "w",      True),
        ]
        for cid, h, w, a, s in col_defs:
            self.tree.heading(cid, text=h,
                              command=lambda c=cid: self._on_header_dblclick_guard(c))
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

        self.tree.bind("<Double-1>",       self._dblclick)
        self.tree.bind("<Button-3>",       self._rclick)
        self.tree.bind("<Button-2>",       self._rclick)
        # Keyboard navigation
        for key in ("<Prior>","<Next>","<Home>","<End>"):
            self.tree.bind(key, self._kb_navigate)
        # Shift+Arrow multi-select
        self.tree.bind("<Shift-Up>",   self._shift_up)
        self.tree.bind("<Shift-Down>", self._shift_down)

        self._ctx = tk.Menu(self, tearoff=0, bg="#313244", fg="#cdd6f4",
                            activebackground="#585b70", activeforeground="#cdd6f4",
                            font=("Helvetica",10))
        TreeviewTooltip(self.tree, self._tooltip)
        self._add_header_tooltips()   # item 8: column header tooltips

        # Header double-click state tracker
        self._hdr_click_time = {}

    # ── Column header double-click (auto-size) ────────────────────────────────
    def _on_header_dblclick_guard(self, col_id):
        now = time.time()
        last = self._hdr_click_time.get(col_id, 0)
        if now - last < 0.35:
            self._auto_size_col(col_id)
        self._hdr_click_time[col_id] = now

    def _auto_size_col(self, col_id):
        font_obj = tk_font.Font(font=("Helvetica",10))
        hdr  = self.tree.heading(col_id)["text"]
        maxw = font_obj.measure(hdr) + 24
        cols = list(self.tree["columns"])
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, "values")
            try:
                idx  = cols.index(col_id)
                cell = str(vals[idx]).split("\n")[0] if idx < len(vals) else ""
                w    = font_obj.measure(cell) + 24
                if w > maxw: maxw = w
            except (ValueError, IndexError): pass
        self.tree.column(col_id, width=min(maxw, 800))

    def _auto_size_all(self):
        for col_id in self.tree["columns"]:
            self._auto_size_col(col_id)

    # ── Keyboard navigation ───────────────────────────────────────────────────
    def _kb_navigate(self, event):
        children = self.tree.get_children()
        if not children: return
        sel = self.tree.selection()
        if not sel:
            first = children[0]
            self.tree.selection_set(first); self.tree.see(first); return
        cur_idx = list(children).index(sel[-1])
        key = event.keysym
        if key == "Prior":  new_idx = max(0, cur_idx - 20)
        elif key == "Next": new_idx = min(len(children)-1, cur_idx+20)
        elif key == "Home": new_idx = 0
        elif key == "End":  new_idx = len(children)-1
        else: return
        target = children[new_idx]
        self.tree.selection_set(target); self.tree.see(target)
        return "break"

    def _shift_up(self, event):
        children = self.tree.get_children()
        if not children: return
        sel = self.tree.selection()
        if not sel: return
        cur_idx = list(children).index(sel[0])
        if cur_idx > 0:
            new = children[cur_idx - 1]
            self.tree.selection_add(new); self.tree.see(new)
        return "break"

    def _shift_down(self, event):
        children = self.tree.get_children()
        if not children: return
        sel = self.tree.selection()
        if not sel: return
        cur_idx = list(children).index(sel[-1])
        if cur_idx < len(children)-1:
            new = children[cur_idx + 1]
            self.tree.selection_add(new); self.tree.see(new)
        return "break"

    # ── FFmpeg status bar ──────────────────────────────────────────────────────
    def _build_ffmpeg_status(self, parent):
        for w in parent.winfo_children(): w.destroy()
        ff_ok, fp_ok, ff_msg, fp_msg = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
        if ff_ok and fp_ok:
            lbl = tk.Label(parent, text="FFmpeg ✓", font=("Helvetica",9,"bold"),
                           bg="#1e1e2e", fg="#a6e3a1", cursor="hand2")
            lbl.pack(side="left")
            self._ff_tip = None
            ff_dir = os.path.dirname(FFMPEG_PATH)
            def _show(e):
                self._ff_tip = tw = tk.Toplevel(parent); tw.wm_overrideredirect(True)
                tw.wm_geometry(f"+{e.x_root+10}+{e.y_root+15}"); tw.configure(bg="#45475a")
                tk.Label(tw, text=f"Path: {ff_dir}\nClick to open Settings",
                         bg="#45475a", fg="#cdd6f4", font=("Consolas",9), padx=8, pady=4).pack()
            def _hide(e):
                if self._ff_tip: self._ff_tip.destroy(); self._ff_tip = None
            lbl.bind("<Enter>", _show); lbl.bind("<Leave>", _hide)
            lbl.bind("<Button-1>", lambda e: SettingsDialog(self))
        else:
            if not ff_ok and not fp_ok:
                status_text = "FFmpeg ✗"; fg = "#f38ba8"
            elif not ff_ok:
                status_text = "ffmpeg ✗"; fg = "#fab387"
            else:
                status_text = "ffprobe ✗"; fg = "#fab387"
            tk.Label(parent, text=status_text, font=("Helvetica",9,"bold"),
                     bg="#1e1e2e", fg=fg).pack(side="left", padx=(0,4))
            tk.Button(parent, text="Set path", font=("Helvetica",8),
                      bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                      command=lambda: SettingsDialog(self)).pack(side="left", padx=(0,4))
            tk.Button(parent, text="Download", font=("Helvetica",8),
                      bg="#45475a", fg="#89b4fa", relief="flat", cursor="hand2",
                      command=lambda: webbrowser.open("https://ffmpeg.org/download.html")
                      ).pack(side="left", padx=(0,4))

    def _update_extract_btn_state(self):
        ff_ok, fp_ok, _, _ = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
        if ff_ok and fp_ok:
            self.extract_btn.configure(state="normal", bg="#fab387",
                                       cursor="hand2", fg="#1e1e2e")
        else:
            self.extract_btn.configure(state="disabled", bg="#45475a",
                                       cursor="", fg="#6c7086")

    def _on_ffprobe_toggle(self):
        SETTINGS["use_ffprobe"] = self._use_ffprobe.get()
        _save_settings(SETTINGS)

    # ── Settings changed callback ─────────────────────────────────────────────
    def _on_settings_changed(self):
        """Called by SettingsDialog on save — refresh column header + lang values."""
        iso = SETTINGS.get("lang_ok_code", "PT")
        self.tree.heading("lang_ok", text=f"{iso} OK?")
        # Re-evaluate lang_ok for all results in memory
        for r in self._results:
            r["lang_ok"] = compute_lang_ok(
                r.get("video_path"), r.get("subs_internal",[]),
                r.get("subs_external",[]),
                r.get("nfo_path") if r.get("nfo_exists") else None,
                r.get("xml_path") if r.get("xml_exists") else None,
                iso_code=iso)
        self._refresh_table()
        self._build_ffmpeg_status(self._ff_frame)
        self._update_extract_btn_state()

    # ── Column header tooltips (item 8) ───────────────────────────────────────
    _COL_HEADER_TIPS = {
        "subfolder":  "Movie folder name. Double-click to open the folder in Explorer.",
        "poster":     "poster.jpg — 🟢 OK  🟡 Proportion warning  🔴 Error/Missing\nExpected: portrait 2:3 ratio, ≥ 100 KB.",
        "poster_sz":  "poster.jpg file size. Double-click the icon to open the image.",
        "folder":     "folder.jpg — 🟢 OK  🟡 Proportion warning  🔴 Error/Missing\nShould be identical to poster.jpg for KODI compatibility.",
        "folder_sz":  "folder.jpg file size.",
        "fanart":     "fanart.jpg — 🟢 OK  🟡 Proportion warning  🔴 Error/Missing\nExpected: landscape 16:9 ratio, ≥ 200 KB.",
        "fanart_sz":  "fanart.jpg file size.",
        "backdrops":  "Number of backdrop.jpg frames found in the folder.\nRight-click → Extract Backdrop(s) to generate more.",
        "nfo":        ".nfo metadata file — 🟢 present  🔴 missing.\nDouble-click to open in editor.",
        "nfo_ok":     "NFO XML validity — 🟢 valid  🔴 has errors.\nDouble-click to see error details.",
        "xml":        "movie.xml metadata file — 🟢 present  🔴 missing.\nDouble-click to open in editor.",
        "xml_ok":     "XML validity — 🟢 valid  🔴 has errors.\nDouble-click to see error details.",
        "language":   "Language tag from movie.xml <Language> element.",
        "vid_ext":    "Video file format (MKV, MP4, AVI…). 🔴 = no video found.\nDouble-click to play.",
        "vid_size":   "Video file size on disk.",
        "quality":    "Video resolution class from FFprobe.\n4K UHD / 1080p / 720p / 576p / 480p / SD\n'—' means FFprobe is disabled or no video.",
        "lang_ok":    "Checks whether the target language audio or subtitle is present.\nY = found  N = not found  — = no video.\nConfigure target language in Settings → Language OK?",
        "subs":       "Subtitle tracks found.\nInt: = embedded in video (via FFprobe)\nExt: = external subtitle files in the folder.",
        "genre":      "Movie genres from NFO <genre> tags.\n🟢 All genres match standard list\n🟡 Capitalisation or synonym issues detected\n🔴 No genre found\nRight-click → Normalize Genres to fix.",
    }

    def _add_header_tooltips(self):
        """Bind Motion events on column headings to show tooltip text."""
        self._hdr_tip_win = None
        self._hdr_tip_col = None

        def _on_header_motion(event):
            col_id = self.tree.identify_column(event.x)
            region = self.tree.identify_region(event.x, event.y)
            if region != "heading":
                _hide_header_tip()
                return
            if col_id:
                idx = int(col_id.lstrip("#")) - 1
                cols = self.tree["columns"]
                if 0 <= idx < len(cols):
                    cname = cols[idx]
                    tip_text = self._COL_HEADER_TIPS.get(cname)
                    if tip_text and cname != self._hdr_tip_col:
                        _hide_header_tip()
                        self._hdr_tip_col = cname
                        tw = tk.Toplevel(self.tree)
                        tw.wm_overrideredirect(True)
                        tw.wm_geometry(f"+{event.x_root+14}+{event.y_root+20}")
                        tw.configure(bg="#181825")
                        tk.Label(tw, text=tip_text, bg="#181825", fg="#cdd6f4",
                                 font=("Consolas", 9), padx=10, pady=6,
                                 wraplength=420, justify="left").pack()
                        self._hdr_tip_win = tw
                    return
            _hide_header_tip()

        def _hide_header_tip(event=None):
            if self._hdr_tip_win:
                self._hdr_tip_win.destroy()
                self._hdr_tip_win = None
            self._hdr_tip_col = None

        self.tree.bind("<Motion>", _on_header_motion, add=True)
        self.tree.bind("<Leave>",  _hide_header_tip,  add=True)

    # ── Cell tooltips (item 19) ────────────────────────────────────────────────
    def _tooltip(self, iid, ci):
        d = self._item_map.get(iid)
        if not d: return None

        def _sz(b):
            return format_size(b) if b else "—"

        # Poster columns
        if ci in (COL_POSTER, COL_POSTER_SZ):
            if not d["poster_exists"]:
                return f"poster.jpg\n⛔ File missing\nExpected: {d['poster_path']}"
            lines = [f"poster.jpg", f"Size: {d['poster_size']}"]
            if d.get("poster_dim"): lines.append(f"Dimensions: {d['poster_dim']}")
            w, h = get_image_wh(d["poster_path"])
            if w and h:
                ratio = w / h
                ok = "✅ OK" if 0.60 <= ratio <= 0.72 else "🟡 Not 2:3 portrait"
                lines.append(f"Ratio: {ratio:.2f}  {ok}")
            if d.get("poster_desc"): lines.append(f"⚠️ {d['poster_desc']}")
            return "\n".join(lines)

        # Folder columns
        if ci in (COL_FOLDER, COL_FOLDER_SZ):
            if not d["folder_exists"]:
                return f"folder.jpg\n⛔ File missing\nExpected: {d['folder_path']}"
            lines = [f"folder.jpg", f"Size: {d['folder_size']}"]
            if d.get("folder_dim"): lines.append(f"Dimensions: {d['folder_dim']}")
            w, h = get_image_wh(d["folder_path"])
            if w and h:
                ratio = w / h
                ok = "✅ OK" if 0.60 <= ratio <= 0.72 else "🟡 Not 2:3 portrait"
                lines.append(f"Ratio: {ratio:.2f}  {ok}")
            if d.get("folder_desc"): lines.append(f"⚠️ {d['folder_desc']}")
            return "\n".join(lines)

        # Fanart columns
        if ci in (COL_FANART, COL_FANART_SZ):
            if not d["fanart_exists"]:
                return f"fanart.jpg\n⛔ File missing\nExpected: {d['fanart_path']}"
            lines = [f"fanart.jpg", f"Size: {d['fanart_size']}"]
            if d.get("fanart_dim"): lines.append(f"Dimensions: {d['fanart_dim']}")
            w, h = get_image_wh(d["fanart_path"])
            if w and h:
                ratio = w / h
                ok = "✅ OK" if 1.70 <= ratio <= 1.85 else "🟡 Not 16:9 landscape"
                lines.append(f"Ratio: {ratio:.2f}  {ok}")
            if d.get("fanart_desc"): lines.append(f"⚠️ {d['fanart_desc']}")
            return "\n".join(lines)

        # Backdrops
        if ci == COL_BACKDROPS:
            bc = d["backdrop_count"]
            if bc == 0:
                return "Backdrops: none found\nRight-click → Extract Backdrop(s) to generate"
            paths_preview = "\n".join(f"  {os.path.basename(p)}" for p in d["backdrop_paths"][:5])
            more = f"\n  … and {bc-5} more" if bc > 5 else ""
            return f"Backdrops: {bc} file(s)\n{paths_preview}{more}"

        # NFO
        if ci == COL_NFO:
            if not d["nfo_exists"]:
                return f".nfo file\n⛔ Missing\nExpected: {os.path.basename(d['nfo_path'])}"
            lines = [f"{os.path.basename(d['nfo_path'])}", f"Size: {d['nfo_size']}"]
            if d["nfo_errors"]:
                lines.append(f"⚠️ {len(d['nfo_errors'])} XML error(s) — click OK? for details")
            else:
                lines.append("✅ XML valid")
            return "\n".join(lines)

        # NFO OK?
        if ci == COL_NFO_OK:
            if not d["nfo_exists"]: return "NFO not present"
            if d["nfo_errors"]:
                errs = d["nfo_errors"][:3]
                lines = [f"⚠️ {len(d['nfo_errors'])} error(s) in NFO:"]
                for e in errs:
                    lines.append(f"  Line {e['line']}: {e['message']}")
                if len(d["nfo_errors"]) > 3:
                    lines.append(f"  … {len(d['nfo_errors'])-3} more")
                lines.append("Double-click OK? to see full error list")
                return "\n".join(lines)
            return "✅ NFO is valid XML"

        # XML
        if ci == COL_XML:
            if not d["xml_exists"]:
                return "movie.xml\n⛔ Missing"
            lines = [f"movie.xml", f"Size: {d['xml_size']}"]
            if d["xml_errors"]:
                lines.append(f"⚠️ {len(d['xml_errors'])} XML error(s) — click OK? for details")
            else:
                lines.append("✅ XML valid")
            return "\n".join(lines)

        # XML OK?
        if ci == COL_XML_OK:
            if not d["xml_exists"]: return "XML not present"
            if d["xml_errors"]:
                errs = d["xml_errors"][:3]
                lines = [f"⚠️ {len(d['xml_errors'])} error(s) in movie.xml:"]
                for e in errs:
                    lines.append(f"  Line {e['line']}: {e['message']}")
                if len(d["xml_errors"]) > 3:
                    lines.append(f"  … {len(d['xml_errors'])-3} more")
                lines.append("Double-click OK? to see full error list")
                return "\n".join(lines)
            return "✅ movie.xml is valid XML"

        # Video / Quality / Size
        if ci == COL_VID_EXT:
            if not d.get("video_path"):
                return "No video file found in this folder"
            vfiles = d.get("video_files", [])
            lines = [f"Video: {d['video_ext']}  ({d['video_size']})"]
            if len(vfiles) > 1:
                lines.append(f"⚠️ {len(vfiles)} video files found (expected 1):")
                for vf in vfiles[:4]: lines.append(f"  {vf}")
            else:
                lines.append(f"  {os.path.basename(d['video_path'])}")
            return "\n".join(lines)

        if ci == COL_VID_SIZE:
            if not d.get("video_path"): return None
            return f"Video file size: {d['video_size']}\n{os.path.basename(d['video_path'])}"

        if ci == COL_QUALITY:
            if d.get("video_width") and d.get("video_height"):
                return (f"Resolution: {d['video_width']}×{d['video_height']} px\n"
                        f"Quality class: {d.get('video_quality','—')}")
            return "Quality: FFprobe not run or no video"

        # Lang OK
        if ci == COL_LANG_OK:
            v = d.get("lang_ok", "—")
            iso = SETTINGS.get("lang_ok_code", "PT")
            lang_name = next((n for c, n in WORLD_LANGUAGES if c == iso), iso)
            if v == "Y":
                return f"✅ {lang_name} audio or subtitle found"
            if v == "N":
                return (f"🔴 No {lang_name} audio or subtitle found\n"
                        f"Checked: FFprobe audio, embedded subs, external subs, XML tags, NFO tags")
            return "— No video file — cannot determine language"

        # Subtitles
        if ci == COL_SUBS:
            lines = []
            if d.get("subs_internal"):
                lines.append(f"Embedded ({len(d['subs_internal'])} track(s)):")
                for s in d["subs_internal"][:5]:
                    tl = f' "{s["title"]}"' if s.get("title") else ""
                    lines.append(f"  {s['lang']}{tl}")
            if d.get("subs_external"):
                lines.append(f"External ({len(d['subs_external'])} file(s)):")
                for s in d["subs_external"][:5]:
                    lines.append(f"  {s['lang']} → {s['file']}")
            return "\n".join(lines) if lines else "No subtitles found"

        # Genre (Phase 3)
        if ci == COL_GENRE:
            genres = d.get("genres", [])
            if not genres:
                return "No <genre> tags found in NFO\nRight-click → Normalize Genres"
            valid = _get_valid_genres()
            lines = [f"{len(genres)} genre(s):"]
            for g in genres:
                n = normalize_genre(g)
                ok = "✅" if g == n else f"🟡 → {n}"
                in_list = g in valid or g.title() in valid or n in valid
                lines.append(f"  {g}  {ok}" + ("" if in_list else "  (custom)"))
            return "\n".join(lines)

        return None

    # ── Double-click ───────────────────────────────────────────────────────────
    def _dblclick(self, e):
        if self._scanning: return
        region = self.tree.identify_region(e.x, e.y)
        if region == "heading":
            col_id = self.tree.identify_column(e.x)
            if col_id:
                cols = self.tree["columns"]
                idx  = int(col_id.lstrip("#")) - 1
                if 0 <= idx < len(cols):
                    self._auto_size_col(cols[idx])
            return
        iid = self.tree.identify_row(e.y); cid = self.tree.identify_column(e.x)
        if not iid or not cid: return
        ci = int(cid.lstrip("#")) - 1; d = self._item_map.get(iid)
        if not d: return
        if ci in (COL_POSTER, COL_POSTER_SZ):
            os_open(d["poster_path"]) if d["poster_exists"] else messagebox.showinfo("Missing","poster.jpg not found.")
        elif ci in (COL_FOLDER, COL_FOLDER_SZ):
            os_open(d["folder_path"]) if d["folder_exists"] else messagebox.showinfo("Missing","folder.jpg not found.")
        elif ci in (COL_FANART, COL_FANART_SZ):
            os_open(d["fanart_path"]) if d["fanart_exists"] else messagebox.showinfo("Missing","fanart.jpg not found.")
        elif ci == COL_BACKDROPS:
            os_open(d["backdrop_paths"][0]) if d["backdrop_count"] > 0 else messagebox.showinfo("Missing","No backdrops.")
        elif ci == COL_NFO:
            # Filename column: ALWAYS open for editing if file exists
            if not d["nfo_exists"]: messagebox.showinfo("Missing", f"Expected: {os.path.basename(d['nfo_path'])}")
            else:                   open_in_editor(d["nfo_path"])
        elif ci == COL_NFO_OK:
            # OK? column: show errors if any, else open editor
            if not d["nfo_exists"]: messagebox.showinfo("Missing", f"Expected: {os.path.basename(d['nfo_path'])}")
            elif d["nfo_errors"]:   ErrorDialog(self, f"NFO Errors — {d['subfolder']}", d["nfo_path"], d["nfo_errors"])
            else:                   open_in_editor(d["nfo_path"])
        elif ci == COL_XML:
            # Filename column: ALWAYS open for editing if file exists
            if not d["xml_exists"]: messagebox.showinfo("Missing", "movie.xml not found.")
            else:                   open_in_editor(d["xml_path"])
        elif ci == COL_XML_OK:
            # OK? column: show errors if any, else open editor
            if not d["xml_exists"]: messagebox.showinfo("Missing", "movie.xml not found.")
            elif d["xml_errors"]:   ErrorDialog(self, f"XML Errors — {d['subfolder']}", d["xml_path"], d["xml_errors"])
            else:                   open_in_editor(d["xml_path"])
        elif ci == COL_LANGUAGE:
            if d["xml_exists"]: open_in_editor(d["xml_path"])
        elif ci in (COL_VID_EXT, COL_VID_SIZE, COL_QUALITY):
            os_open(d["video_path"]) if d["video_path"] else messagebox.showinfo("Missing","No video.")
        elif ci == COL_SUBS:
            SubtitleDialog(self, d["subfolder"], d)
        elif ci == COL_SUBFOLDER:
            os_open(d["subfolder_path"])

    # ── Right-click context menu ───────────────────────────────────────────────
    def _rclick(self, e):
        if self._scanning: return
        iid = self.tree.identify_row(e.y)
        if not iid: return
        # If the clicked row is not in selection, replace selection
        if iid not in self.tree.selection():
            self.tree.selection_set(iid)
        d = self._item_map.get(iid)
        if not d: return
        sel_iids = self.tree.selection()
        sel_data = [self._item_map[i] for i in sel_iids if i in self._item_map]
        multi    = len(sel_data) > 1

        m = self._ctx; m.delete(0, "end")
        if not multi:
            m.add_command(label="📂  Open subfolder",
                          command=lambda: os_open(d["subfolder_path"]))
            m.add_separator()
            for lb, ke, kp in [("🖼  poster","poster_exists","poster_path"),
                                ("🖼  folder.jpg","folder_exists","folder_path"),
                                ("🖼  fanart","fanart_exists","fanart_path")]:
                if d[ke]:  m.add_command(label=lb, command=lambda p=d[kp]: os_open(p))
                else:      m.add_command(label=lb+" (missing)", state="disabled")
            if d["backdrop_count"]:
                m.add_command(label=f"🖼  Backdrops ({d['backdrop_count']})",
                              command=lambda: os_open(d["backdrop_paths"][0]))
            m.add_separator()
            if d["video_path"]:
                m.add_command(label="🎬  Play video",
                              command=lambda: os_open(d["video_path"]))
                ff_ok, fp_ok, _, _ = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
                if ff_ok:
                    m.add_command(label="🎞️  Extract Backdrop(s)",
                                  command=lambda: self._do_extract(d))
            else:
                m.add_command(label="🎬  Video (missing)", state="disabled")
            if d.get("subs_internal") or d.get("subs_external"):
                m.add_command(label="💬  Subtitles…",
                              command=lambda: SubtitleDialog(self, d["subfolder"], d))
            m.add_separator()
            if d["nfo_exists"]:
                m.add_command(label="📝  Open .nfo",
                              command=lambda: open_in_editor(d["nfo_path"]))
                if d["nfo_errors"]:
                    m.add_command(label=f"⚠️  NFO errors ({len(d['nfo_errors'])})",
                                  command=lambda: ErrorDialog(
                                      self, f"NFO — {d['subfolder']}", d["nfo_path"], d["nfo_errors"]))
            if d["xml_exists"]:
                m.add_command(label="📝  Open movie.xml",
                              command=lambda: open_in_editor(d["xml_path"]))
                if d["xml_errors"]:
                    m.add_command(label=f"⚠️  XML errors ({len(d['xml_errors'])})",
                                  command=lambda: ErrorDialog(
                                      self, f"XML — {d['subfolder']}", d["xml_path"], d["xml_errors"]))
            m.add_separator()
            # IMDB / TMDb
            imdb_id, tmdb_id = get_movie_ids_robust(
                d.get("nfo_path") if d.get("nfo_exists") else None,
                d.get("xml_path") if d.get("xml_exists") else None)
            if imdb_id:
                url = f"https://www.imdb.com/title/{imdb_id}"
                m.add_command(label="🌐  Open on IMDB",
                              command=lambda u=url: open_url_with_browser(u))
            else:
                m.add_command(label="🌐  Open on IMDB (ID not found)", state="disabled")
            if tmdb_id:
                url = f"https://www.themoviedb.org/movie/{tmdb_id}"
                m.add_command(label="🌐  Open on TMDb",
                              command=lambda u=url: open_url_with_browser(u))
            else:
                m.add_command(label="🌐  Open on TMDb (ID not found)", state="disabled")
            # Item 16: OpenSubtitles
            m.add_separator()
            m.add_command(label="🌐  Open on OpenSubtitles.org",
                          command=lambda: self._open_opensubtitles(d))
            m.add_separator()
            m.add_command(label="📋  Copy Movie Name",
                          command=lambda: self._copy_movie_name(d))
            if SETTINGS.get("scraper_path",""):
                m.add_command(label="🎬  Open in Scraper",
                              command=lambda: open_with_scraper(d["subfolder_path"]))
            m.add_separator()

        # Multi-selection options
        # Item 11: renamed from "Improvements" to "Run Improvements Check"
        label_sel = f"🔍  Run Improvements Check ({len(sel_data)} movies)" if multi \
                    else "🔍  Run Improvements Check"
        m.add_command(label=label_sel,
                      command=lambda dd=sel_data: self._run_improvements_on(dd))
        # Phase 3: Ratings Sync
        label_sync = f"⭐  Sync Ratings ({len(sel_data)} movies)" if multi \
                     else "⭐  Sync Ratings from IMDb / TMDb"
        m.add_command(label=label_sync,
                      command=lambda dd=sel_data: self._sync_ratings(dd))
        # Phase 3: Normalize Genres
        label_genre = f"🎬  Normalize Genres ({len(sel_data)} movies)" if multi \
                      else "🎬  Normalize Genres"
        m.add_command(label=label_genre,
                      command=lambda dd=sel_data: self._normalize_genres_for(dd))
        if multi:
            ff_ok, _, _, _ = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
            if ff_ok:
                m.add_command(label=f"🎞️  Extract Backdrop(s) ({len(sel_data)} movies)",
                              command=lambda dd=sel_data: self._extract_multi(dd))
        if not multi:
            m.add_command(label="🔄  Re-validate (full rescan this row)",
                          command=lambda: self._reval(iid, d))
            # Item 17: Re-validate FFmpeg only
            if d.get("video_path") and FFPROBE_PATH and SETTINGS.get("use_ffprobe", True):
                m.add_command(label="🔬  Re-validate FFmpeg Metadata",
                              command=lambda: self._reval_ffmpeg(iid, d))
        m.tk_popup(e.x_root, e.y_root)

    def _copy_movie_name(self, d):
        titles = get_movie_titles_from_files(
            d.get("nfo_path") if d.get("nfo_exists") else None,
            d.get("xml_path") if d.get("xml_exists") else None)
        if not titles:
            messagebox.showinfo("Copy Movie Name",
                                "No title found in NFO or XML.", parent=self)
            return
        unique = list(dict.fromkeys(titles))  # preserve order, deduplicate
        if len(unique) == 1:
            self.clipboard_clear(); self.clipboard_append(unique[0])
            # No popup needed — silent copy
        else:
            CopyMovieNameDialog(self, unique)

    def _run_improvements_on(self, data_list):
        checks = SETTINGS.get("improve_checks", _DEFAULT_SETTINGS["improve_checks"])
        results = run_improvements(data_list, checks)
        # Collect scan errors (item 3)
        error_rows = []
        for d in data_list:
            errs = []
            for e in d.get("nfo_errors", []):
                errs.append(f"NFO Line {e['line']}: {e['message']}")
            for e in d.get("xml_errors", []):
                errs.append(f"XML Line {e['line']}: {e['message']}")
            if errs:
                error_rows.append((d["subfolder"], errs))
        report = format_improvements_report(results, error_rows)
        ImprovementsDialog(self, report, len(data_list))

    def _extract_multi(self, data_list):
        ff_ok, fp_ok, _, _ = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
        if not ff_ok:
            messagebox.showerror("FFmpeg missing", "FFmpeg not available."); return
        for d in data_list:
            if d.get("video_path"):
                timeout = SETTINGS.get("extract_timeout", 60)
                dlg = FrameExtractionDialog(self, d["video_path"], d["subfolder_path"],
                                            timeout_sec=timeout)
                self.wait_window(dlg)

    def _reval(self, iid, data):
        sp, sn = data["subfolder_path"], data["subfolder"]
        if not os.path.isdir(sp): messagebox.showerror("Error","Folder gone."); return
        r = scan_one_subfolder(sp, sn)
        self._item_map[iid] = r
        for i, o in enumerate(self._results):
            if o["subfolder_path"] == sp: self._results[i] = r; break
        tag = r["row_health"] + ("_odd" if self.tree.index(iid) % 2 else "")
        self.tree.item(iid, values=self._rv(r), tags=(tag,))
        self._update_stats()

    def _reval_ffmpeg(self, iid, data):
        """Item 17 — Re-run FFprobe only for the selected row."""
        if not FFPROBE_PATH or not SETTINGS.get("use_ffprobe", True):
            messagebox.showwarning("FFprobe Unavailable",
                                   "FFprobe is not available or is disabled.\n"
                                   "Enable it with the FFprobe checkbox and set the path in Settings.")
            return
        vp = data.get("video_path")
        if not vp or not os.path.isfile(vp):
            messagebox.showinfo("No Video", "No video file found for this movie.")
            return

        def _worker():
            w, h = _get_video_resolution(vp)
            q = classify_quality(w, h)
            si = scan_subtitles(data["subfolder_path"], vp)
            iso = SETTINGS.get("lang_ok_code", "PT")
            lo = compute_lang_ok(vp, si["subs_internal"], si["subs_external"],
                                 data.get("nfo_path") if data.get("nfo_exists") else None,
                                 data.get("xml_path") if data.get("xml_exists") else None,
                                 iso_code=iso)
            def _apply():
                data["video_width"]    = w
                data["video_height"]   = h
                data["video_quality"]  = q
                data["subs_internal"]  = si["subs_internal"]
                data["subs_external"]  = si["subs_external"]
                data["subs_summary"]   = si["subs_summary"]
                data["lang_ok"]        = lo
                data["row_health"]     = _compute_health(data)
                tag = data["row_health"] + ("_odd" if self.tree.index(iid) % 2 else "")
                self.tree.item(iid, values=self._rv(data), tags=(tag,))
                self._update_stats()
                messagebox.showinfo("FFprobe Done",
                                    f"FFprobe re-validated:\n"
                                    f"Resolution: {w}×{h}  Quality: {q}\n"
                                    f"Lang OK: {lo}")
            self.after(0, _apply)

        threading.Thread(target=_worker, daemon=True).start()

    def _open_opensubtitles(self, d):
        """Item 16 — Open movie page on OpenSubtitles.org."""
        titles = get_movie_titles_from_files(
            d.get("nfo_path") if d.get("nfo_exists") else None,
            d.get("xml_path") if d.get("xml_exists") else None)
        title = titles[0] if titles else None
        year  = get_movie_year_from_files(
            d.get("nfo_path") if d.get("nfo_exists") else None,
            d.get("xml_path") if d.get("xml_exists") else None)

        if not title:
            messagebox.showwarning("OpenSubtitles",
                                   "Could not find movie title in NFO or XML.\n"
                                   "Cannot build search URL.")
            return

        url = build_opensubtitles_url(title, year)
        if url:
            open_url_with_browser(url)
        else:
            messagebox.showerror("OpenSubtitles", "Failed to build URL.")

    # ── Extract frames ─────────────────────────────────────────────────────────
    # ── Online Ratings Sync (item 2) ───────────────────────────────────────────
    def _sync_ratings(self, data_list):
        """Launch ratings sync for one or more movies in a background thread."""
        tmdb_key = SETTINGS.get("tmdb_api_key", "").strip()
        omdb_key = SETTINGS.get("omdb_api_key", "").strip()
        if not tmdb_key and not omdb_key:
            messagebox.showwarning("No API Keys",
                "No TMDb or OMDb API keys are configured.\n"
                "Go to Settings → API Keys to add them.")
            return
        # Run in thread; handle each movie sequentially with optional "apply to all"
        threading.Thread(target=self._sync_ratings_worker,
                         args=(data_list, tmdb_key, omdb_key), daemon=True).start()

    def _sync_ratings_worker(self, data_list, tmdb_key, omdb_key):
        apply_choice = None   # None = ask each time; set to tuple once "apply to all" selected
        for d in data_list:
            name = d["subfolder"]
            nfo_path = d.get("nfo_path") if d.get("nfo_exists") else None
            xml_path = d.get("xml_path") if d.get("xml_exists") else None
            imdb_id, tmdb_id = get_movie_ids_robust(nfo_path, xml_path)

            # Fetch from both sources
            tmdb_r, tmdb_v = _fetch_tmdb_rating(tmdb_id, tmdb_key) if tmdb_key else (None, None)
            omdb_r, omdb_v = _fetch_omdb_rating(imdb_id, omdb_key) if omdb_key else (None, None)

            both = (tmdb_r is not None) and (omdb_r is not None)
            one  = (tmdb_r is not None) != (omdb_r is not None)
            none = (tmdb_r is None) and (omdb_r is None)

            chosen_r = chosen_v = None
            source_used = ""

            if apply_choice is not None:
                # "Apply to all" was set in a previous iteration
                if apply_choice == "tmdb":
                    chosen_r, chosen_v, source_used = tmdb_r or omdb_r, tmdb_v or omdb_v, "TMDb"
                elif apply_choice == "omdb":
                    chosen_r, chosen_v, source_used = omdb_r or tmdb_r, omdb_v or tmdb_v, "OMDb/IMDb"
                else:
                    continue   # "cancel all"
            elif both:
                # Ask user to compare
                result = {"choice": None, "apply_all": False}
                def _ask(d=d, tr=tmdb_r, tv=tmdb_v, or_=omdb_r, ov=omdb_v, res=result):
                    dlg = RatingsCompareDialog(self, d["subfolder"], tr, tv, or_, ov)
                    self.wait_window(dlg)
                    res["choice"]    = dlg.choice
                    res["apply_all"] = dlg.apply_all
                self.after(0, _ask)
                # Wait for dialog to close
                while result["choice"] is None:
                    time.sleep(0.05)
                if result["choice"] == "cancel":
                    continue
                if result["apply_all"]:
                    apply_choice = result["choice"]
                if result["choice"] == "tmdb":
                    chosen_r, chosen_v, source_used = tmdb_r, tmdb_v, "TMDb"
                else:
                    chosen_r, chosen_v, source_used = omdb_r, omdb_v, "OMDb/IMDb"
            elif one:
                # Auto-select the one that returned data
                if tmdb_r is not None:
                    chosen_r, chosen_v, source_used = tmdb_r, tmdb_v, "TMDb"
                else:
                    chosen_r, chosen_v, source_used = omdb_r, omdb_v, "OMDb/IMDb"
                self.after(0, lambda n=name, s=source_used:
                    messagebox.showinfo("Ratings Sync",
                        f"{n}\nOnly {s} returned data — used automatically."))
            elif none:
                # Ask user to enter manually
                result = {"rating": None, "votes": None}
                def _ask_manual(n=name, res=result):
                    dlg = ManualRatingDialog(self, n)
                    self.wait_window(dlg)
                    res["rating"] = dlg.rating
                    res["votes"]  = dlg.votes
                self.after(0, _ask_manual)
                while result["rating"] is None and result["votes"] is None:
                    time.sleep(0.05)
                if not result["rating"]:
                    continue
                chosen_r, chosen_v, source_used = result["rating"], result["votes"] or "0", "manual"

            if chosen_r and chosen_v:
                errors = write_rating_to_files(nfo_path, xml_path, chosen_r, chosen_v)
                if errors:
                    self.after(0, lambda n=name, errs=errors:
                        messagebox.showerror("Write Error",
                            f"{n}\nFailed to write ratings:\n" + "\n".join(errs)))
                else:
                    # Re-validate the row
                    self.after(0, lambda iid_data=d: self._reval_by_path(d))

        self.after(0, lambda: messagebox.showinfo("Ratings Sync Complete",
            f"Ratings sync finished for {len(data_list)} movie(s)."))

    def _reval_by_path(self, d):
        """Re-validate a row by matching subfolder_path."""
        sp = d.get("subfolder_path")
        for iid, rd in self._item_map.items():
            if rd.get("subfolder_path") == sp:
                self._reval(iid, rd)
                return

    def _normalize_genres_all(self):
        """Normalize genres for ALL movies — asks confirmation first."""
        if not self._results:
            messagebox.showinfo("No data", "Run a scan first."); return
        if not messagebox.askyesno("Normalize Genres — All Movies",
            f"This will normalize genres in ALL {len(self._results)} movies.\n"
            "Changes will be written to NFO and XML files.\n\nContinue?",
            icon="warning"):
            return
        self._normalize_genres_for(self._results, confirm_all=True)

    def _sync_ratings_selected(self):
        """Sync ratings for currently selected rows, or show warning if none."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection",
                "Select one or more movies first, then use\n"
                "right-click → Sync Ratings, or select all movies.")
            return
        data_list = [self._item_map[i] for i in sel if i in self._item_map]
        self._sync_ratings(data_list)

    # ── Normalize Genres (item 13) ─────────────────────────────────────────────
    def _normalize_genres_for(self, data_list, confirm_all=False):
        """Normalize genres for given data_list. confirm_all=True means user confirmed."""
        if not data_list:
            return
        changed = 0
        errors  = []
        for d in data_list:
            nfo_path = d.get("nfo_path") if d.get("nfo_exists") else None
            xml_path = d.get("xml_path") if d.get("xml_exists") else None
            genres = get_genres_from_nfo(nfo_path)
            if not genres:
                continue
            normalized, did_change = normalize_genre_list(genres)
            if not did_change:
                continue
            ok_nfo, err_nfo = write_genres_to_nfo(nfo_path, normalized)
            ok_xml, err_xml = write_genres_to_xml(xml_path, normalized)
            if ok_nfo or ok_xml:
                changed += 1
                d["genres"]        = normalized
                d["genre_display"] = "/".join(normalized)
                d["genre_status"]  = classify_genres(normalized)[1]
            if err_nfo: errors.append(f"{d['subfolder']}: {err_nfo}")
            if err_xml: errors.append(f"{d['subfolder']}: {err_xml}")

        # Refresh all affected rows
        self._refresh_table()
        msg = f"Normalized genres in {changed} movie(s)."
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors[:5])
        messagebox.showinfo("Normalize Genres", msg)

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
                                 "FFmpeg not available. Set path in Settings."); return
        if not d.get("video_path"):
            messagebox.showwarning("No video","No video file in this folder."); return
        timeout = SETTINGS.get("extract_timeout", 60)
        dlg = FrameExtractionDialog(self, d["video_path"], d["subfolder_path"],
                                    timeout_sec=timeout)
        self.wait_window(dlg)
        SETTINGS["extract_timeout"]  = dlg._timeout_var.get()
        SETTINGS["backdrop_count"]   = dlg._count_var.get()   # item 14: persist count
        _save_settings(SETTINGS)
        sel = self.tree.selection()
        if sel and sel[0] in self._item_map:
            self._reval(sel[0], self._item_map[sel[0]])

    # ── Browse / Scan / Update / Cancel ───────────────────────────────────────
    def _browse(self):
        if self._scanning: return
        p = filedialog.askdirectory(title="Select root folder")
        if p:
            self._folder = p; self.folder_var.set(p); self.stats_var.set("")
            self._results = []; self._item_map.clear()
            for r in self.tree.get_children(): self.tree.delete(r)

    def _update_scan(self):
        if self._scanning: return
        folder = self._folder or SETTINGS.get("last_folder", "")
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No folder","No folder to update. Browse first."); return
        self._folder = folder; self.folder_var.set(folder)
        self._start_scan(folder)

    def _scan(self):
        if self._scanning: return
        if not self._folder:
            messagebox.showwarning("No folder","Select a folder first."); return
        self._start_scan(self._folder)

    def _cancel(self):
        self._cancel_scan = True
        self.pbar_label.configure(text="Cancelling…")

    def _draw_scan_progress(self, pct, text):
        c = self.pbar_canvas; c.delete("all")
        w = c.winfo_width() or 400; h = 22
        c.create_rectangle(0, 0, w, h, fill="#313244", outline="")
        fw = int(w * pct / 100)
        if fw > 0:
            c.create_rectangle(0, 0, fw, h, fill="#2d6e3f", outline="")
        c.create_text(w//2, h//2, text=f"{pct}%",
                      fill="#cdd6f4", font=("Helvetica",10,"bold"))
        self.pbar_label.configure(text=text)

    def _start_scan(self, folder):
        try:
            entries = sorted([e for e in os.scandir(folder) if e.is_dir()],
                             key=lambda e: e.name.lower())
        except PermissionError:
            messagebox.showerror("Error", f"Cannot access: {folder}"); return
        if not entries:
            messagebox.showinfo("Empty","No subfolders found."); return

        self._results = []; self._item_map.clear()
        for r in self.tree.get_children(): self.tree.delete(r)

        self._scanning = True; self._cancel_scan = False
        self.scan_btn.configure(state="disabled")
        self.update_btn.configure(state="disabled")
        self.cancel_btn.pack(side="left", padx=(6,0))
        self.pbar_canvas.pack(side="left", fill="x", expand=True)
        self.pbar_label.pack(side="left", padx=(8,0))
        self._draw_scan_progress(0, "Starting…")

        use_ff = self._use_ffprobe.get()
        total  = len(entries)
        t0     = [time.time()]

        def _eta_str(done, total, elapsed):
            if done == 0: return ""
            avg = elapsed / done
            rem = avg * (total - done)
            if rem > 60: return f"{int(rem//60)}m {int(rem%60)}s remaining"
            return f"{int(rem)}s remaining"

        def _insert_or_update(r, idx):
            """Insert a new row or update an existing one in the table."""
            tag = r["row_health"] + ("_odd" if idx % 2 else "")
            # Check if row already exists
            for iid, rd in self._item_map.items():
                if rd.get("subfolder_path") == r["subfolder_path"]:
                    self._item_map[iid] = r
                    self.tree.item(iid, values=self._rv(r), tags=(tag,))
                    return
            iid = self.tree.insert("", "end", values=self._rv(r), tags=(tag,))
            self._item_map[iid] = r

        def worker():
            results_partial = []

            # ── Phase 1: list subfolders ──────────────────────────────────────
            self.after(0, lambda: self._draw_scan_progress(0, "Phase 1/4 — Listing subfolders…"))
            stubs = []
            for entry in entries:
                stubs.append({
                    "subfolder": entry.name, "subfolder_path": entry.path,
                    "poster_exists":False,"poster_path":os.path.join(entry.path,"poster.jpg"),
                    "poster_bytes":0,"poster_size":"—","poster_dim":None,"poster_corrupt":False,
                    "poster_desc":"","poster_status":STATUS_MISSING,
                    "fanart_exists":False,"fanart_path":os.path.join(entry.path,"fanart.jpg"),
                    "fanart_bytes":0,"fanart_size":"—","fanart_dim":None,"fanart_corrupt":False,
                    "fanart_desc":"","fanart_status":STATUS_MISSING,
                    "folder_exists":False,"folder_path":os.path.join(entry.path,"folder.jpg"),
                    "folder_bytes":0,"folder_size":"—","folder_dim":None,"folder_corrupt":False,
                    "folder_desc":"","folder_status":STATUS_MISSING,
                    "backdrop_count":0,"backdrop_paths":[],
                    "nfo_exists":False,"nfo_path":os.path.join(entry.path,entry.name+".nfo"),
                    "nfo_bytes":0,"nfo_size":"—","nfo_status":STATUS_MISSING,"nfo_errors":[],
                    "xml_exists":False,"xml_path":os.path.join(entry.path,"movie.xml"),
                    "xml_bytes":0,"xml_size":"—","xml_status":STATUS_MISSING,"xml_errors":[],
                    "language":"—","video_count":0,"video_files":[],"video_ext":"—",
                    "video_path":None,"video_bytes":0,"video_size":"—",
                    "video_width":None,"video_height":None,"video_quality":"—","video_status":STATUS_MISSING,
                    "subs_internal":[],"subs_external":[],"subs_summary":"—","lang_ok":"—",
                    "genres":[],"genre_display":"—","genre_status":STATUS_ERROR,
                    "row_health":"yellow",
                })
            results_partial = list(stubs)
            self.after(0, lambda r=list(results_partial): self._phase_update(r, "Phase 1/4 complete — subfolders listed"))

            if self._cancel_scan:
                self.after(0, lambda: self._scan_done(results_partial)); return

            # ── Phase 2: images ───────────────────────────────────────────────
            for i, (entry, row) in enumerate(zip(entries, results_partial)):
                if self._cancel_scan: break
                pct = int((i+1)/total * 25)
                eta = _eta_str(i+1, total, time.time()-t0[0])
                self.after(0, lambda p=pct, e=eta: self._draw_scan_progress(
                    p, f"Phase 2/4 — Images {p}%  {e}"))

                sub = entry.path
                for img, key, itype in [("poster.jpg","poster","poster"),
                                         ("folder.jpg","folder","folder"),
                                         ("fanart.jpg","fanart","fanart")]:
                    p_img = os.path.join(sub, img)
                    exists = os.path.isfile(p_img)
                    row[f"{key}_exists"] = exists
                    if exists:
                        sz = os.path.getsize(p_img)
                        row[f"{key}_bytes"] = sz
                        row[f"{key}_size"]  = format_size(sz)
                        row[f"{key}_dim"]   = get_image_dimensions(p_img)
                        st, desc = check_image_health(p_img, itype)
                        row[f"{key}_status"]  = st
                        row[f"{key}_corrupt"] = (st == STATUS_ERROR)
                        row[f"{key}_desc"]    = desc
                    else:
                        row[f"{key}_status"] = STATUS_MISSING

                bc, bp = count_backdrops(sub)
                row["backdrop_count"] = bc; row["backdrop_paths"] = bp
                row["row_health"] = _compute_health(row)
                # incremental save every 10 rows
                if i % 10 == 0:
                    self.after(0, lambda r=list(results_partial):
                               self._incremental_save(r))

            self.after(0, lambda r=list(results_partial):
                       self._phase_update(r, "Phase 2/4 complete — images scanned"))
            if self._cancel_scan:
                self.after(0, lambda: self._scan_done(results_partial)); return

            # ── Phase 3: NFO / XML ─────────────────────────────────────────────
            for i, (entry, row) in enumerate(zip(entries, results_partial)):
                if self._cancel_scan: break
                pct = 25 + int((i+1)/total * 25)
                eta = _eta_str(i+1, total, time.time()-t0[0])
                self.after(0, lambda p=pct, e=eta: self._draw_scan_progress(
                    p, f"Phase 3/4 — Metadata {p}%  {e}"))

                sub = entry.path; sn = entry.name
                nfo_path = os.path.join(sub, sn+".nfo")
                xml_path = os.path.join(sub, "movie.xml")
                ne = os.path.isfile(nfo_path); xe = os.path.isfile(xml_path)
                row["nfo_exists"] = ne; row["nfo_path"] = nfo_path
                if ne:
                    nb = os.path.getsize(nfo_path); nerr = validate_xml_file(nfo_path, True)
                    row["nfo_bytes"] = nb; row["nfo_size"] = format_size(nb); row["nfo_errors"] = nerr
                    row["nfo_status"] = (STATUS_ERROR if nerr else STATUS_OK)
                row["xml_exists"] = xe; row["xml_path"] = xml_path
                if xe:
                    xb = os.path.getsize(xml_path); xerr = validate_xml_file(xml_path, False)
                    row["xml_bytes"] = xb; row["xml_size"] = format_size(xb); row["xml_errors"] = xerr
                    row["xml_status"] = (STATUS_ERROR if xerr else STATUS_OK)
                    row["language"] = extract_language_from_xml(xml_path)
                # Genre extraction from NFO (Phase 3)
                if ne:
                    genres = get_genres_from_nfo(nfo_path)
                    gd, gs = classify_genres(genres)
                    row["genres"] = genres
                    row["genre_display"] = gd
                    row["genre_status"]  = gs
                row["row_health"] = _compute_health(row)
                if i % 10 == 0:
                    self.after(0, lambda r=list(results_partial):
                               self._incremental_save(r))

            self.after(0, lambda r=list(results_partial):
                       self._phase_update(r, "Phase 3/4 complete — metadata scanned"))
            if self._cancel_scan:
                self.after(0, lambda: self._scan_done(results_partial)); return

            # ── Phase 4: video + ffprobe ───────────────────────────────────────
            for i, (entry, row) in enumerate(zip(entries, results_partial)):
                if self._cancel_scan: break
                pct = 50 + int((i+1)/total * 50)
                eta = _eta_str(i+1, total, time.time()-t0[0])
                self.after(0, lambda p=pct, e=eta: self._draw_scan_progress(
                    p, f"Phase 4/4 — Video{'+FFprobe' if use_ff else ''} {p}%  {e}"))

                sub = entry.path
                vi  = scan_video_files(sub)
                if use_ff and vi["video_path"] and FFPROBE_PATH:
                    w, h = _get_video_resolution(vi["video_path"])
                    vi["video_width"] = w; vi["video_height"] = h
                    vi["video_quality"] = classify_quality(w, h)
                si = scan_subtitles(sub, vi["video_path"])
                iso = SETTINGS.get("lang_ok_code","PT")
                nfo_p = row["nfo_path"] if row["nfo_exists"] else None
                xml_p = row["xml_path"] if row["xml_exists"] else None
                lo = compute_lang_ok(vi["video_path"], si["subs_internal"],
                                     si["subs_external"], nfo_p, xml_p, iso)
                vs = (STATUS_MISSING if vi["video_count"]==0
                      else STATUS_ERROR if vi["video_count"]>1 else STATUS_OK)
                row.update({
                    "video_count":vi["video_count"],"video_files":vi["video_files"],
                    "video_ext":vi["video_ext"],"video_path":vi["video_path"],
                    "video_bytes":vi["video_bytes"],"video_size":vi["video_size"],
                    "video_width":vi["video_width"],"video_height":vi["video_height"],
                    "video_quality":vi["video_quality"],"video_status":vs,
                    "subs_internal":si["subs_internal"],"subs_external":si["subs_external"],
                    "subs_summary":si["subs_summary"],"lang_ok":lo,
                })
                row["row_health"] = _compute_health(row)
                if i % 5 == 0:
                    self.after(0, lambda r=list(results_partial):
                               self._incremental_save(r))

            self.after(0, lambda: self._scan_done(list(results_partial)))

        threading.Thread(target=worker, daemon=True).start()

    def _phase_update(self, results, msg):
        """Bulk-refresh table after a scan phase completes."""
        self._results = results
        # Update all rows
        existing_paths = {rd.get("subfolder_path"): iid for iid, rd in self._item_map.items()}
        for idx, r in enumerate(results):
            path = r["subfolder_path"]
            tag  = r["row_health"] + ("_odd" if idx % 2 else "")
            if path in existing_paths:
                iid = existing_paths[path]
                self._item_map[iid] = r
                self.tree.item(iid, values=self._rv(r), tags=(tag,))
            else:
                iid = self.tree.insert("", "end", values=self._rv(r), tags=(tag,))
                self._item_map[iid] = r
        self._update_stats()
        self.pbar_label.configure(text=msg)

    def _incremental_save(self, results):
        SETTINGS["last_folder"]  = self._folder
        SETTINGS["last_results"] = _results_to_json(results)
        _save_settings(SETTINGS)

    def _scan_done(self, results):
        self._scanning = False
        self.scan_btn.configure(state="normal")
        self.update_btn.configure(state="normal")
        self.cancel_btn.pack_forget()
        self.pbar_canvas.pack_forget()
        self.pbar_label.pack_forget()
        self._results = results
        if not results:
            self.stats_var.set("Cancelled or empty."); return
        self._phase_update(results, "")
        self._update_stats()
        self._refresh_table()
        SETTINGS["last_folder"]  = self._folder
        SETTINGS["last_results"] = _results_to_json(results)
        SETTINGS["sort_option"]  = self.sort_var.get()
        _save_settings(SETTINGS)

    def _restore_last_session(self):
        last_folder  = SETTINGS.get("last_folder","")
        last_results = SETTINGS.get("last_results",[])
        if not last_folder or not last_results: return
        if not os.path.isdir(last_folder): return
        self._folder = last_folder
        self.folder_var.set(last_folder)
        self._results = _results_from_json(last_results)
        self._update_stats(); self._refresh_table()

    # ── Stats ──────────────────────────────────────────────────────────────────
    def _update_stats(self):
        t   = len(self._results)
        pc  = sum(1 for r in self._results if r["poster_exists"])
        fc  = sum(1 for r in self._results if r["folder_exists"])
        ac  = sum(1 for r in self._results if r["fanart_exists"])
        nc  = sum(1 for r in self._results if r["nfo_exists"])
        ne  = sum(1 for r in self._results if r.get("nfo_errors"))
        xc  = sum(1 for r in self._results if r["xml_exists"])
        xe  = sum(1 for r in self._results if r.get("xml_errors"))
        vc  = sum(1 for r in self._results if r["video_count"] == 1)
        iso = SETTINGS.get("lang_ok_code","PT")
        lk  = sum(1 for r in self._results if r.get("lang_ok") == "Y")
        self.stats_var.set("  •  ".join([
            f"{t} folders", f"poster:{pc}/{t}", f"folder:{fc}/{t}",
            f"fanart:{ac}/{t}", f"nfo:{nc}/{t}({ne}err)",
            f"xml:{xc}/{t}({xe}err)", f"video:{vc}/{t}",
            f"{iso}-OK:{lk}/{t}"
        ]))

    # ── Row values ─────────────────────────────────────────────────────────────
    def _rv(self, r):
        def img_icon(exists, status):
            """Return the status icon for an image column."""
            if not exists:
                return STATUS_MISSING   # 🔴
            return status               # STATUS_OK=🟢, STATUS_WARN=🟡, STATUS_ERROR=🔴
        return (
            r["subfolder"],
            img_icon(r["poster_exists"], r.get("poster_status", STATUS_MISSING)),
            r["poster_size"],
            img_icon(r["folder_exists"], r.get("folder_status", STATUS_MISSING)),
            r["folder_size"],
            img_icon(r["fanart_exists"], r.get("fanart_status", STATUS_MISSING)),
            r["fanart_size"],
            str(r["backdrop_count"]) if r["backdrop_count"] > 0 else "—",
            STATUS_OK if r["nfo_exists"] else STATUS_MISSING,
            r["nfo_status"],
            STATUS_OK if r["xml_exists"] else STATUS_MISSING,
            r["xml_status"],
            r["language"],
            r["video_ext"] if r["video_count"] > 0 else STATUS_MISSING,
            r["video_size"],
            r.get("video_quality", "—"),
            r.get("lang_ok", "—"),
            r["subs_summary"],
            # Phase 3: Genre — icon + display text
            r.get("genre_status", STATUS_ERROR) + " " + r.get("genre_display", "—"),
        )

    # ── Refresh table ──────────────────────────────────────────────────────────
    def _refresh_table(self):
        if not self._results: return
        for r in self.tree.get_children(): self.tree.delete(r)
        self._item_map.clear()

        sort_name = self.sort_var.get()
        kf, rev   = SORT_OPTIONS.get(sort_name, SORT_OPTIONS["Subfolder (A→Z)"])

        def sort_key(r):
            return (kf(r), r["subfolder"].lower())

        sorted_results = sorted(self._results, key=sort_key, reverse=rev)
        for i, r in enumerate(sorted_results):
            tag = r["row_health"] + ("_odd" if i % 2 else "")
            iid = self.tree.insert("", "end", values=self._rv(r), tags=(tag,))
            self._item_map[iid] = r

    # ── Export CSV ─────────────────────────────────────────────────────────────
    def _export_csv(self):
        if self._scanning: return
        if not self._results: messagebox.showinfo("Empty","Scan first."); return
        p = filedialog.asksaveasfilename(
            title="Export CSV", defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile="scan_results.csv")
        if not p: return
        def _st(s): return "OK" if s==STATUS_OK else ("Error" if s==STATUS_ERROR else "Missing")
        try:
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                iso = SETTINGS.get("lang_ok_code","PT")
                w.writerow(["Subfolder","Path","poster.jpg","Poster Size","Poster Dim",
                             "folder.jpg","Folder Size","Folder Dim",
                             "fanart.jpg","Fanart Size","Fanart Dim","Backdrops",
                             ".nfo","NFO Valid","NFO Errors","movie.xml","XML Valid","XML Errors",
                             "Language","Video Files","Video Ext","Video Size","Quality",
                             f"{iso} OK?","Embedded Subs","External Subs","Health"])
                for r in self._results:
                    w.writerow([
                        r["subfolder"], r["subfolder_path"],
                        "Y" if r["poster_exists"] else "N", r["poster_size"], r["poster_dim"] or "—",
                        "Y" if r["folder_exists"] else "N", r["folder_size"], r["folder_dim"] or "—",
                        "Y" if r["fanart_exists"] else "N", r["fanart_size"], r["fanart_dim"] or "—",
                        r["backdrop_count"],
                        "Y" if r["nfo_exists"] else "N", _st(r["nfo_status"]),
                        "; ".join(f"L{e['line']}:{e['message']}" for e in r["nfo_errors"]) or "",
                        "Y" if r["xml_exists"] else "N", _st(r["xml_status"]),
                        "; ".join(f"L{e['line']}:{e['message']}" for e in r["xml_errors"]) or "",
                        r["language"], r["video_count"], r["video_ext"], r["video_size"],
                        r.get("video_quality","—"), r.get("lang_ok","—"),
                        ", ".join(s["lang"] for s in r["subs_internal"]) or "None",
                        ", ".join(f'{s["lang"]}({s["file"]})' for s in r["subs_external"]) or "None",
                        r["row_health"],
                    ])
            messagebox.showinfo("Exported", f"Saved {len(self._results)} rows to:\n{p}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))


# ── Health helper (used during phased scan) ───────────────────────────────────
def _compute_health(row):
    # Only STATUS_ERROR (🔴) makes a row red — STATUS_WARN (🟡) does not
    has_err = (row.get("nfo_status") == STATUS_ERROR or
               row.get("xml_status") == STATUS_ERROR or
               row.get("poster_status", STATUS_MISSING) == STATUS_ERROR or
               row.get("fanart_status", STATUS_MISSING) == STATUS_ERROR or
               row.get("folder_status", STATUS_MISSING) == STATUS_ERROR)
    # Yellow if any file is missing OR has a warning
    has_warn = (not row.get("poster_exists") or
                not row.get("fanart_exists") or
                not row.get("folder_exists") or
                row.get("poster_status", STATUS_MISSING) == STATUS_WARN or
                row.get("fanart_status", STATUS_MISSING) == STATUS_WARN or
                row.get("folder_status", STATUS_MISSING) == STATUS_WARN or
                row.get("nfo_status") == STATUS_MISSING or
                row.get("xml_status") == STATUS_MISSING or
                row.get("video_count", 0) != 1)
    if has_err:   return "red"
    if has_warn:  return "yellow"
    return "green"


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
