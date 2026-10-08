# =============================================================================
# Metadata & MediaClinic
# Version: 0.12.0
# Author:  Luiz Junqueira & Claude AI
# Contact: junqueira.ch@gmail.com
#
# CHANGELOG
# ---------
# v0.12.0 (current)                                         ### NEW v0.12.0 ###
#   - New: Poster/Folder 3:4 acceptance toggle in Image Sizes settings
#   - Fix: Proportion description text updated dynamically for all toggle combos
#   - New: Poster/Folder/Fanart columns merged (icon + quality label in one cell)
#          Separate Quality and Size columns removed; full details in tooltip
#   - New: Backup Folder Maintenance section in new Settings "Backup" tab
#          - Max backup folder size (MB) with auto-cleanup of oldest backups
#          - "Delete all backup folders" button with confirmation
#          - clean_backup_folder_if_needed() called after each backup + at startup
#   - New: Settings dialog tab labels fixed (full visible text, no truncation)
#          New "User Interface" tab (4 settings) and "Backup" tab added
#   - Fix: Alternating row colors updated for better contrast
#   - Fix: Right-click menu "Re-validate" items renamed: FFMPEG → FFprobe
#          "Re-validate (with FFprobe)" always visible and always enabled
#   - Fix: "Re-validate (with FFprobe)" now performs full column revalidation
#   - New: Rating column between Genres and Poster
#          Extracts from NFO <rating> / XML <IMDBrating> / XML <Rating>
#          Conflict detection, missing/error icons, numeric sorting
#   - Fix: Custom genres now correctly show warning icon (◐)
#   - New: Right-click "Add Custom Genre(s)" adds custom genres to settings list
#   - Version bump to v0.12.0
# v0.11.1 (previous)
#   - Fix: CRITICAL — _on_settings_changed froze UI by calling get_image_wh()
#          for every movie × 3 images on the main thread. Now uses cached dims.
#   - Fix: CRITICAL — get_jpeg_dimensions infinite loop on corrupt JPEG.
#          Added max-iteration guard (2000 segments).
#   - New: After saving Image Sizes settings, offer Update Scan (no/with FFprobe)
#   - New: Same offer for Language OK?, Genres, NFO-XML Tags tab saves
#   - Version bump to v0.11.1
#   - Fix: XML Genre indentation preserved on normalize (mirrors original tabs)
#   - New: Automatic backup of NFO/XML before any write (silent, logged)
#   - Fix: FFprobe data persists across no-FFprobe re-validates/scans
#   - New: Help menu moved to last position (Settings / Tools / Help)
#   - New: F1 global shortcut opens Help from anywhere in the app
#   - New: VidSize column renamed to "Video Size"
#   - New: Image Quality columns (Poster Quality, Folder Quality, Fanart Quality)
#   - New: Quality classification is resolution-tier based (±5% tolerance)
#   - New: Fanart 16:8 acceptance toggle in Image Sizes settings
#   - New: "Show image size?" toggle in User Interface settings
#   - New: Sort menu redesigned — quality-based sorts, column order, Folder Quality
#   - New: check_image_health uses pixel-based validation
#   - New: Image Sizes settings tab fully redesigned with resolution dropdowns
#   - Version bump to v0.11.0
# v0.10.5 (previous)
#   - Sort: Genre (A-Z) and Genre (Z-A) added
#   - Fix: write_genres_to_nfo/xml preserves original line position
#          and indentation of existing <genre> tags (one-for-one)
#   - Fix: classify_genres ◐ false-positive for correctly-spelled genres
#   - Update: column header tooltip texts revised
#   - New: "User Interface" tab in Settings with header tooltip toggle
# v0.10.4
#   - Item 1: Larger status symbols (⬤ ◐ ○ ✕) via wider BMP chars
#   - Item 2: Re-validate (with FFMPEG) in right-click, single + multi
#   - Item 3: NFO+NFO OK? and XML+XML OK? merged into unified columns
# v0.10.3
#   - Fix: Status icons replaced with BMP Unicode symbols
#   - Fix: Emoji cleaned from all tooltips and help text
# v0.10.2
#   - Fix: Year column moved between Movie Name and Genres
#   - Fix: Status icons replaced with colored Unicode squares
#   - Fix: HTML entity decoding in movie title extraction
# v0.10.1
#   PHASE B - Internal architecture refactoring (no user-visible changes):
#   - Centralized column definitions (COLUMN_MODEL)
#   - Double-click dispatch table (DBLCLICK_ACTIONS)
#   - SettingsDialog extracted to settings_dialog.py
#   - Unified tooltip, sort, and right-click logic refs
#   - Series mode architecture placeholders
#   - All ### NEW v0.10.0 ### markers cleaned up
# v0.10.0
#   PHASE A - All Phase A bug fixes and improvements:
#   Settings tab fix, emoji icons, column tooltip isolation,
#   Genre freeze fix, Genre→2nd column, Subfolder→MovieName+Year,
#   Clear All button, Extract Backdrop alignment, alternating rows,
#   richer status bar, keyboard shortcuts, NFO/XML pre-validation,
#   Series tab stub, rotating log, Open Folder menu, Refresh Icons,
#   re-validate function renames, Help rewrite for new features.
# v0.9.0  — Help & About rebuild (was labelled v9.0)
#   PHASE 4 — Help & About rebuild
#   - Complete help rewrite covering all v9.0 features across 6 tabs:
#     Getting Started, Table & Columns, Actions, Settings, Tools & APIs, About
#   PHASE 3 — Data Features
#   - Online Ratings Sync (TMDb + OMDb), side-by-side dialog, batch apply-to-all
#   - Genre column + Normalize Genres action; writes NFO + XML
#   - Malformed XML/NFO fallback regex parser for ID/tag extraction
#   - Improvements report appends scan errors in red at the bottom
#   PHASE 2 — Settings Expansion
#   - API Keys (TMDb + OMDb) with validation and click-to-get-key links
#   - Browser selection with auto-detection of installed browsers
#   - Tools auto-fill (Notepad++, FFmpeg detected on open)
#   - Image minimum sizes (per-image KB thresholds, 0 = skip)
#   - Genre list editable in Settings (TMDb standard + custom)
#   - Backdrop count setting (default 10, configurable per extraction)
#   - Video Scraper clarified as future feature with metadata source picker
#   - All external URLs routed through selected default browser
#   PHASE 1 — Foundation & Quick Wins
#   - Sort auto-updates on combo change (no button click needed)
#   - Notepad++ -lxml bug fixed; filepath before flag; no "create file?" dialog
#   - NFO/XML filename click always opens editor; OK? shows errors
#   - Column header tooltips and enriched cell tooltips
#   - Icons: status symbols everywhere; proportion mismatch downgraded to warning
#   - Re-validate FFmpeg Metadata right-click (single movie)
#   - OpenSubtitles.org right-click; Run Improvements Check rename
# v0.8.0  — Phased scan, Improvements engine, IMDB/TMDb links, Auto-size,
#            FFprobe checkbox, language column, backdrop progress, Shift+select
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
import logging
import logging.handlers
import html  # v0.10.2 — HTML entity decoding
from settings_dialog import SettingsDialog as SettingsDialog, _inject_globals as _sd_inject

# ── App identity ──────────────────────────────────────────────────────────────
APP_NAME    = "Metadata & MediaClinic"
APP_VERSION = "0.12.0"  ### NEW v0.12.0 ###
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

# ══════════════════════════════════════════════════════════════════════════════
# COLUMN MODEL  (Phase B — centralized column definitions)
# ══════════════════════════════════════════════════════════════════════════════
#
# Each entry is a dict with the following keys:
#   id          str   — internal Treeview column id
#   label       str   — display header label (may use SETTINGS for dynamic labels)
#   width       int   — default pixel width
#   anchor      str   — "w" | "center"
#   stretch     bool  — whether column stretches with window
#   header_tip  str   — tooltip shown when hovering the column header
#   dblclick    str   — action tag dispatched by _dblclick()
#                       valid tags: "open_folder" | "open_image_poster" |
#                       "open_image_folder" | "open_image_fanart" |
#                       "open_backdrop" | "open_nfo" | "open_nfo_or_errors" |
#                       "open_xml" | "open_xml_or_errors" | "open_xml_lang" |
#                       "play_video" | "show_subtitles" | "open_nfo_genre" | "none"
#
# SERIES MODE PLACEHOLDER (Phase C):
#   A separate SERIES_COLUMN_MODEL list will be defined here for Phase C.
#   It will follow the same structure but with episode-specific columns:
#   show_name, season, episode_number, episode_title, air_date, etc.
#   TODO (Phase C): define SERIES_COLUMN_MODEL = [...]
#
# The COLUMN_MODEL is the single source of truth for:
#   - column id list passed to ttk.Treeview
#   - heading labels and widths
#   - header tooltip text
#   - double-click action dispatch
#   - COL_* index constants (derived below)
#
# NOTE: "label" for lang_ok is dynamic — substituted at build time using
# SETTINGS["lang_ok_code"]. It is stored as the placeholder "LANG_OK_LABEL"
# and resolved inside _build_ui().

COLUMN_MODEL = [
    # id            label           width  anchor    stretch  dblclick
    {"id": "movie_name", "label": "Movie Name",    "width": 240, "anchor": "w",      "stretch": True,
     "header_tip": "Movie title extracted from the NFO/XML metadata.",
     "dblclick": "open_folder"},
    {"id": "year",       "label": "Year",            "width":  52, "anchor": "center", "stretch": False,
     "header_tip": "Production year from NFO <year> or XML <ProductionYear>.",
     "dblclick": "none"},
    {"id": "genre",      "label": "Genres",         "width": 140, "anchor": "w",      "stretch": True,
     "header_tip": "Genres listed in the NFO <genre> tags.",
     "dblclick": "open_nfo_genre"},
    ### NEW v0.12.0 — Rating column (between Genres and Poster) ###
    {"id": "rating",     "label": "Rating",          "width":  80, "anchor": "center", "stretch": False,
     "header_tip": "Rating extracted from NFO <rating> or XML <IMDBrating>/<Rating>.",
     "dblclick": "open_nfo"},
    ### NEW v0.12.0 — Merged Poster column (icon + quality label) ###
    {"id": "poster",     "label": "Poster",          "width": 130, "anchor": "center", "stretch": False,
     "header_tip": "Status and quality tier of poster.jpg. Hover for dimensions, size, and ratio.",
     "dblclick": "open_image_poster"},
    ### NEW v0.12.0 — Merged Folder column (icon + quality label) ###
    {"id": "folder",     "label": "Folder",          "width": 130, "anchor": "center", "stretch": False,
     "header_tip": "Status and quality tier of folder.jpg. Should be an identical copy of poster.jpg.",
     "dblclick": "open_image_folder"},
    ### NEW v0.12.0 — Merged Fanart column (icon + quality label) ###
    {"id": "fanart",     "label": "Fanart",          "width": 130, "anchor": "center", "stretch": False,
     "header_tip": "Status and quality tier of fanart.jpg. Hover for dimensions, size, and ratio.",
     "dblclick": "open_image_fanart"},
    {"id": "backdrops",  "label": "Bkdrps",          "width":  52, "anchor": "center", "stretch": False,
     "header_tip": "Number of backdrop images (backdrop.jpg) found in the folder.",
     "dblclick": "open_backdrop"},
    {"id": "nfo",        "label": ".nfo",            "width":  52, "anchor": "center", "stretch": False,
     "header_tip": "Status of the .nfo metadata file.",
     "dblclick": "open_nfo_unified"},
    {"id": "xml",        "label": ".xml",            "width":  52, "anchor": "center", "stretch": False,
     "header_tip": "Status of the movie.xml metadata file.",
     "dblclick": "open_xml_unified"},
    {"id": "language",   "label": "Language",        "width":  82, "anchor": "center", "stretch": False,
     "header_tip": "Language value from the XML <Language> element.",
     "dblclick": "open_xml_lang"},
    {"id": "vid_ext",    "label": "Video",           "width":  52, "anchor": "center", "stretch": False,
     "header_tip": "Video container format (MKV, MP4, AVI, etc.).",
     "dblclick": "play_video"},
    {"id": "vid_size",   "label": "Video Size",      "width":  74, "anchor": "center", "stretch": False,
     "header_tip": "Video file size on disk.",
     "dblclick": "play_video"},
    {"id": "quality",    "label": "Quality",         "width":  74, "anchor": "center", "stretch": False,
     "header_tip": "Video resolution class determined by FFprobe.",
     "dblclick": "play_video"},
    {"id": "lang_ok",    "label": "LANG_OK_LABEL",   "width":  58, "anchor": "center", "stretch": False,
     "header_tip": "Checks whether the target language audio or subtitle track is present.",
     "dblclick": "none"},
    {"id": "subs",       "label": "Subtitles",       "width": 180, "anchor": "w",      "stretch": True,
     "header_tip": "Subtitle tracks found, either external .srt files or internal tracks detected by FFprobe.",
     "dblclick": "show_subtitles"},
]

# ── Image size columns are now embedded in tooltip only (v0.12.0) ─────────────
# The separate poster_ql, poster_sz, folder_ql, folder_sz, fanart_ql, fanart_sz
# columns were removed in v0.12.0. Each image type now uses a single merged
# column (icon + quality label). Full details remain in the cell tooltip.
_SIZE_ONLY_COLUMNS = set()  ### NEW v0.12.0 — no more separate size columns ###

# ── Column index constants derived from COLUMN_MODEL ─────────────────────────
_COL_IDX = {c["id"]: i for i, c in enumerate(COLUMN_MODEL)}
COL_MOVIE_NAME = _COL_IDX["movie_name"]
COL_GENRE = _COL_IDX["genre"]
COL_RATING = _COL_IDX["rating"]   ### NEW v0.12.0 ###
COL_POSTER = _COL_IDX["poster"]
COL_FOLDER = _COL_IDX["folder"]
COL_FANART = _COL_IDX["fanart"]
COL_BACKDROPS = _COL_IDX["backdrops"]
COL_NFO = _COL_IDX["nfo"]
COL_XML = _COL_IDX["xml"]
COL_LANGUAGE = _COL_IDX["language"]
COL_VID_EXT = _COL_IDX["vid_ext"]
COL_VID_SIZE = _COL_IDX["vid_size"]
COL_QUALITY = _COL_IDX["quality"]
COL_LANG_OK = _COL_IDX["lang_ok"]
COL_SUBS = _COL_IDX["subs"]
COL_YEAR = _COL_IDX["year"]
COL_XML = _COL_IDX["xml"]
COL_LANGUAGE = _COL_IDX["language"]
COL_VID_EXT = _COL_IDX["vid_ext"]
COL_VID_SIZE = _COL_IDX["vid_size"]
COL_QUALITY = _COL_IDX["quality"]
COL_LANG_OK = _COL_IDX["lang_ok"]
COL_SUBS = _COL_IDX["subs"]
COL_YEAR = _COL_IDX["year"]

# ── SORT_OPTIONS references COLUMN_MODEL ids ──────────────────────────────────

# v0.10.3 — BMP Unicode symbols: render correctly in Windows GDI/Segoe UI
#           Row background (green/yellow/red) gives color context per row.
#           Cell symbols give per-cell status signal without color dependency.
# v0.10.4 — Larger symbols: ⬤ (U+2B24) replaces ● for ~25% more visual weight
STATUS_OK      = "⬤"   # U+2B24 BLACK LARGE CIRCLE  — present / valid / ok
STATUS_WARN    = "◐"   # U+25D0 HALF BLACK CIRCLE   — warning / proportion issue
STATUS_MISSING = "○"   # U+25CB WHITE CIRCLE        — file missing / absent
STATUS_ERROR   = "✕"   # U+2715 MULTIPLICATION X    — parse error / corrupt

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
    "sort_option":        "Movie Name (A-Z)",
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
    # v0.10.0 — UI preferences
    "alternating_rows":   True,
    "show_header_tips":   True,    # v0.10.5 — show column header tooltips
    # v0.11.0 — Image quality resolution tiers               ### NEW v0.11.0 ###
    "poster_quality_level":  "Standard (HD)",   # default poster/folder quality minimum
    "folder_quality_level":  "Standard (HD)",
    "fanart_quality_level":  "Full HD",
    "fanart_accept_168":     False,             # accept 16:8 (≈1.50) ratio as valid
    "poster_accept_34":      False,             # NEW v0.12.0 accept 3:4 (0.75) ratio as valid
    "show_image_size":       False,             # show Size columns alongside Quality columns
    # Phase 2 — Genre list (one per line; stored as newline-joined string)
    "genre_list":         (
        "Action\nAdventure\nAnimation\nComedy\nCrime\nDocumentary\nDrama\n"
        "Family\nFantasy\nHistory\nHorror\nMusic\nMystery\nRomance\n"
        "Science Fiction\nThriller\nWar\nWestern"
    ),
    # Phase 2 — Metadata source (future scraper target)
    "metadata_source":    "tmdb",      # "tmdb" | "omdb"
    # v0.12.0 — Backup folder maintenance                   ### NEW v0.12.0 ###
    "max_backup_size_mb":    500,       # auto-delete oldest backups above this MB limit
    "backup_cleanup_enabled": True,     # reserved for future use
    # v0.12.0 — UI preferences (extended)                   ### NEW v0.12.0 ###
    "compact_mode":          False,     # reduce row height
    "dark_theme":            True,      # dark theme (toggle placeholder)
    "auto_fit_columns":      True,      # auto-fit column widths on load
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

### NEW v0.10.0 — Rotating log setup ###
def _setup_logging():
    """Configure rotating log file in logs/ subfolder next to the script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir    = os.path.join(script_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "app.log")
    handler  = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=1_048_576, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if not root.handlers:
        root.addHandler(handler)
    return log_path

LOG_PATH = _setup_logging()
logger   = logging.getLogger("MediaClinic")
logger.info("=== Metadata & MediaClinic v0.12.0 started ===")

# ══════════════════════════════════════════════════════════════════════════════
# Backup mechanism (v0.11.0)                                  ### NEW v0.11.0 ###
# ══════════════════════════════════════════════════════════════════════════════
# Rule: before any NFO or XML file is written/overwritten by the application,
#       a backup copy must be created first.  Backups are stored in:
#         <script_dir>/backup/backup_<MovieName>_<YYYY-MM-DD_HH-MM-SS>[_N]/
#       where MovieName is the first-column movie name with spaces replaced
#       by underscores.  If the same timestamp folder already exists a numeric
#       suffix (_2, _3 …) is appended.  The mechanism is completely silent in
#       the UI — only a log entry is written.

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKUP_ROOT = os.path.join(_SCRIPT_DIR, "backup")


def _make_backup(movie_name: str, *file_paths: str) -> str | None:
    """
    Create a timestamped backup of one or more NFO/XML files.

    Parameters
    ----------
    movie_name : str
        Movie name used in the folder name (spaces → underscores).
    *file_paths : str
        Absolute paths to files to back up.  Files that do not exist
        are silently skipped.

    Returns
    -------
    str | None
        The backup folder path created, or None if nothing was copied
        (all files were missing or an error occurred).
    """
    try:
        os.makedirs(_BACKUP_ROOT, exist_ok=True)
        # Build safe movie name slug (underscores, strip unsafe chars)
        safe_name = re.sub(r'[\\/:*?"<>|]', '', movie_name).strip()
        safe_name = re.sub(r'\s+', '_', safe_name)
        if not safe_name:
            safe_name = "unknown"
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        base_folder = os.path.join(_BACKUP_ROOT, f"backup_{safe_name}_{timestamp}")
        # Append counter suffix if folder already exists (same second)
        folder = base_folder
        counter = 2
        while os.path.exists(folder):
            folder = f"{base_folder}_{counter}"
            counter += 1
        # Only copy files that actually exist
        copied = []
        for fp in file_paths:
            if fp and os.path.isfile(fp):
                os.makedirs(folder, exist_ok=True)
                dest = os.path.join(folder, os.path.basename(fp))
                shutil.copy2(fp, dest)
                copied.append(os.path.basename(fp))
        if copied:
            logger.info(f"Backup created: {folder}  —  files: {', '.join(copied)}")
            clean_backup_folder_if_needed(folder)  ### NEW v0.12.0 ###
            return folder
        return None
    except Exception as e:
        logger.error(f"Backup failed for '{movie_name}': {e}")
        return None


def _make_batch_backup(movie_name: str, backup_folder_ref: list, *file_paths: str) -> str | None:
    """
    Variant for batch operations.  Creates a single shared backup folder
    for the whole batch and reuses it for subsequent calls in the same batch.

    Parameters
    ----------
    movie_name : str
        Used only for the initial folder name (first call in batch).
    backup_folder_ref : list
        A one-element list [folder_path_or_None] used as a mutable reference.
        Pass the same list for every call in the batch.
    *file_paths : str
        Files to back up in this call.

    Returns
    -------
    str | None
        The shared backup folder path.
    """
    try:
        if backup_folder_ref[0] is None:
            # First call: create the shared folder
            os.makedirs(_BACKUP_ROOT, exist_ok=True)
            safe_name = re.sub(r'[\\/:*?"<>|]', '', movie_name).strip()
            safe_name = re.sub(r'\s+', '_', safe_name)
            if not safe_name:
                safe_name = "batch"
            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            base_folder = os.path.join(_BACKUP_ROOT, f"backup_{safe_name}_{timestamp}")
            folder = base_folder
            counter = 2
            while os.path.exists(folder):
                folder = f"{base_folder}_{counter}"
                counter += 1
            backup_folder_ref[0] = folder
            logger.info(f"Batch backup folder created: {folder}")
        folder = backup_folder_ref[0]
        copied = []
        for fp in file_paths:
            if fp and os.path.isfile(fp):
                os.makedirs(folder, exist_ok=True)
                dest = os.path.join(folder, os.path.basename(fp))
                # Avoid overwriting if same filename already backed up
                if os.path.exists(dest):
                    base, ext = os.path.splitext(os.path.basename(fp))
                    idx = 2
                    while os.path.exists(dest):
                        dest = os.path.join(folder, f"{base}_{idx}{ext}")
                        idx += 1
                shutil.copy2(fp, dest)
                copied.append(os.path.basename(fp))
        if copied:
            logger.info(f"Batch backup — added to {folder}: {', '.join(copied)}")
        return folder
    except Exception as e:
        logger.error(f"Batch backup failed: {e}")
        return None


def clean_backup_folder_if_needed(active_folder: str = None):
    """
    Auto-delete oldest backup_* subfolders when total size exceeds the limit.
    ### NEW v0.12.0 ###

    Parameters
    ----------
    active_folder : str | None
        The backup folder just created (never deleted even if over limit).
        Pass None when calling at startup.
    """
    try:
        max_mb = SETTINGS.get("max_backup_size_mb", 500)
        if not max_mb or max_mb <= 0:
            return
        if not os.path.isdir(_BACKUP_ROOT):
            return
        max_bytes = max_mb * 1024 * 1024

        def _folder_size(path):
            total = 0
            try:
                for e in os.scandir(path):
                    if e.is_file():
                        try: total += e.stat().st_size
                        except Exception: pass
            except Exception:
                pass
            return total

        # Collect all backup_* subfolders
        backup_dirs = []
        for entry in os.scandir(_BACKUP_ROOT):
            if entry.is_dir() and entry.name.startswith("backup_"):
                try:
                    backup_dirs.append((entry.stat().st_ctime, entry.path))
                except Exception:
                    pass

        total_bytes = sum(_folder_size(p) for _, p in backup_dirs)
        if total_bytes <= max_bytes:
            return

        backup_dirs.sort(key=lambda x: x[0])  # oldest first
        for _, folder_path in backup_dirs:
            if total_bytes <= max_bytes:
                break
            if active_folder and os.path.abspath(folder_path) == os.path.abspath(active_folder):
                continue
            try:
                folder_size = _folder_size(folder_path)
                shutil.rmtree(folder_path)
                total_bytes -= folder_size
                logger.info(f"Backup cleanup: removed {folder_path} ({format_size(folder_size)})")
            except Exception as e:
                logger.error(f"Backup cleanup failed for {folder_path}: {e}")
    except Exception as e:
        logger.error(f"clean_backup_folder_if_needed error: {e}")


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




# ══════════════════════════════════════════════════════════════════════════════
# Image Quality Tier System  (v0.11.0)                        ### NEW v0.11.0 ###
# ══════════════════════════════════════════════════════════════════════════════
#
# Quality is resolution-driven.  Each tier is defined by a (width, height)
# minimum.  Classification always picks the HIGHEST tier AT OR BELOW the
# actual resolution (never above).
#
# POSTER / FOLDER  (2:3 portrait, sorted best→worst)
POSTER_QUALITY_TIERS = [
    # (label,           min_w, min_h,   total_px,  est_size_str)
    ("Ultra (4K)",      2000,  3000,    6_000_000, "1.5–3.0 MB"),
    ("Retina/QHD",      1500,  2250,    3_375_000, "800 KB–1.5 MB"),
    ("Standard (HD)",   1000,  1500,    1_500_000, "300–600 KB"),
    ("Optimized",        667,  1000,      667_000, "150–250 KB"),
    ("Thumbnail",        333,   500,      166_500, "30–60 KB"),
]

# FANART  (16:9 or 16:8 landscape, sorted best→worst)
FANART_QUALITY_TIERS = [
    # (label,              min_w, min_h,   total_px,  est_size_str)
    ("Ultra (4K)",         3840,  2160,    8_294_400, "2.5–5.0 MB"),
    ("Retina/QHD (1440p)", 2560,  1440,    3_686_400, "1.2–2.0 MB"),
    ("Full HD",            1920,  1080,    2_073_600, "500–900 KB"),
    ("HD Ready",           1280,   720,      921_600, "250–400 KB"),
]
# Tier label used when image is smaller than the lowest FANART tier
FANART_BELOW_LABEL = "Below HD Ready"

# Tolerance margin (±5%) applied to dimension comparisons
_IMG_QUALITY_TOLERANCE = 0.05


def classify_image_quality(width, height, image_type):
    """
    Classify image quality tier based on pixel dimensions.

    Parameters
    ----------
    width, height : int | None
        Actual image dimensions in pixels.
    image_type : str
        'poster', 'folder' (both use POSTER_QUALITY_TIERS) or 'fanart'.

    Returns
    -------
    str
        Tier label string.  "—" when dimensions are unavailable.
        For fanart images smaller than the lowest tier: FANART_BELOW_LABEL.
    """
    if not width or not height:
        return "—"
    tol = 1 - _IMG_QUALITY_TOLERANCE   # allow 5% below nominal
    if image_type in ("poster", "folder"):
        for label, mw, mh, _, _ in POSTER_QUALITY_TIERS:
            if width >= mw * tol and height >= mh * tol:
                return label
        return "Thumbnail"   # smaller than Thumbnail minimum
    elif image_type == "fanart":
        for label, mw, mh, _, _ in FANART_QUALITY_TIERS:
            if width >= mw * tol and height >= mh * tol:
                return label
        return FANART_BELOW_LABEL
    return "—"


def _poster_quality_sort_key(label):
    """Sort key for poster/folder quality (lower index = higher quality)."""
    order = {t[0]: i for i, t in enumerate(POSTER_QUALITY_TIERS)}
    # Missing file / unknown sorts as worst (highest index)
    return order.get(label, len(POSTER_QUALITY_TIERS) + 1)


def _fanart_quality_sort_key(label):
    """Sort key for fanart quality (lower index = higher quality)."""
    order = {t[0]: i for i, t in enumerate(FANART_QUALITY_TIERS)}
    order[FANART_BELOW_LABEL] = len(FANART_QUALITY_TIERS)
    # Missing file / unknown sorts as worst
    return order.get(label, len(FANART_QUALITY_TIERS) + 2)


def _poster_quality_sort_key_missing_last(r, key, high_to_low):
    """
    Sort helper that always puts missing files at the extreme end.
    high_to_low=True  → higher quality first  → missing = last (highest key)
    high_to_low=False → lower quality first   → missing = first (lowest key = -1)
    """
    val = r.get(key)
    if val is None or val == "—":
        return 9999 if high_to_low else -1
    return _poster_quality_sort_key(val)


def _fanart_quality_sort_key_missing_last(r, key, high_to_low):
    val = r.get(key)
    if val is None or val == "—":
        return 9999 if high_to_low else -1
    return _fanart_quality_sort_key(val)


# ── Inject shared globals into settings_dialog module ────────────────────────
# This must happen after SETTINGS, logger, and all helper functions are defined.
# settings_dialog.py reads these globals to build its UI without circular imports.
_sd_inject(
    app_name           = APP_NAME,
    settings           = SETTINGS,
    default_settings   = _DEFAULT_SETTINGS,
    default_tag_pairs  = DEFAULT_TAG_PAIRS,
    world_languages    = WORLD_LANGUAGES,
    logger             = logger,
    fn_find_ffmpeg     = _find_ffmpeg_ffprobe,
    fn_find_notepadpp  = _find_notepadpp,
    fn_test_ffmpeg     = _test_ffmpeg,
    fn_save_settings   = _save_settings,
    fn_refresh_ffmpeg  = refresh_ffmpeg_paths,
    fn_detect_browsers = detect_installed_browsers,
    fn_open_url        = open_url_with_browser,
    ### NEW v0.11.0 — image quality tier tables ###
    poster_quality_tiers = POSTER_QUALITY_TIERS,
    fanart_quality_tiers = FANART_QUALITY_TIERS,
    ### NEW v0.12.0 — backup cleanup function ###
    fn_clean_backup    = clean_backup_folder_if_needed,
    backup_root        = _BACKUP_ROOT,
)

def format_size(size_bytes):
    if size_bytes < 1024:        return f"{size_bytes} B"
    elif size_bytes < 1024**2:   return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:   return f"{size_bytes/(1024**2):.1f} MB"
    else:                        return f"{size_bytes/(1024**3):.2f} GB"

def get_jpeg_dimensions(filepath):
    """Parse JPEG dimensions from SOF marker.
    v0.11.1: added max-segment guard to prevent infinite loop on corrupt files.
    """                                                      ### NEW v0.11.1 ###
    try:
        with open(filepath, "rb") as f:
            if f.read(2) != b'\xff\xd8': return None, None
            _MAX_SEGMENTS = 2000   # safety guard — no valid JPEG has more ### NEW v0.11.1 ###
            for _ in range(_MAX_SEGMENTS):
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF: return None, None
                m = marker[1]
                # Skip fill bytes (0xFF padding)
                _fill_guard = 0
                while m == 0xFF:
                    b = f.read(1)
                    if len(b) < 1: return None, None
                    m = b[0]
                    _fill_guard += 1
                    if _fill_guard > 16: return None, None   # malformed padding ### NEW v0.11.1 ###
                if m in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
                    f.read(3); hw = f.read(4)
                    if len(hw) < 4: return None, None
                    return struct.unpack(">H", hw[2:4])[0], struct.unpack(">H", hw[0:2])[0]
                elif m in (0xD9, 0xDA):
                    return None, None   # EOI / SOS — no SOF found
                else:
                    d = f.read(2)
                    if len(d) < 2: return None, None
                    seg_len = struct.unpack(">H", d)[0]
                    if seg_len < 2: return None, None   # prevent seek(0,1) loop ### NEW v0.11.1 ###
                    f.seek(seg_len - 2, 1)
            return None, None   # exceeded segment limit
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
    Corruption issues → STATUS_ERROR (red)
    v0.11.0: validation is now pixel-based with ±5% tolerance.  ### NEW v0.11.0 ###
             Fanart 16:8 acceptance is controlled by settings.
             Size check uses KB threshold from settings (0 = skip).
    v0.12.0: poster/folder 3:4 acceptance controlled by settings. ### NEW v0.12.0 ###
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

    tol = _IMG_QUALITY_TOLERANCE   # ±5%

    if image_type in ('poster', 'folder'):
        # ── KB size check ─────────────────────────────────────────────────────
        min_kb = SETTINGS.get(f"min_{image_type}_kb", 100) if image_type == 'poster' \
                 else SETTINGS.get("min_folder_kb", 100)
        if min_kb > 0 and size_bytes < min_kb * 1024:
            size_issues.append(f"File size {size_bytes//1024} KB is below {min_kb} KB minimum")
        # ── Pixel-based minimum quality check ─────────────────────────────────
        if w and h:
            min_level = SETTINGS.get(f"{image_type}_quality_level", "Standard (HD)")
            for label, mw, mh, _, _ in POSTER_QUALITY_TIERS:
                if label == min_level:
                    if w < mw * (1 - tol) or h < mh * (1 - tol):
                        size_issues.append(
                            f"Resolution {w}×{h} is below minimum quality '{min_level}' "
                            f"({mw}×{mh})")
                    break
            # ── Proportion check 2:3 (and optionally 3:4) ────────────────────
            ratio = w / h
            accept_34 = SETTINGS.get("poster_accept_34", False)  ### NEW v0.12.0 ###
            ok_23 = (0.60 <= ratio <= 0.72)
            ok_34 = (0.70 <= ratio <= 0.80)
            if accept_34:
                if not (ok_23 or ok_34):
                    prop_issues.append(
                        f"Proportions {w}×{h} ({ratio:.2f}) — expected 2:3 (≈0.67) or 3:4 (≈0.75)")
            else:
                if not ok_23:
                    prop_issues.append(
                        f"Proportions {w}×{h} ({ratio:.2f}) — expected 2:3 portrait (≈0.67)")
    elif image_type == 'fanart':
        # ── KB size check ─────────────────────────────────────────────────────
        min_kb = SETTINGS.get("min_fanart_kb", 200)
        if min_kb > 0 and size_bytes < min_kb * 1024:
            size_issues.append(f"File size {size_bytes//1024} KB is below {min_kb} KB minimum")
        # ── Pixel-based minimum quality check ─────────────────────────────────
        if w and h:
            min_level = SETTINGS.get("fanart_quality_level", "Full HD")
            for label, mw, mh, _, _ in FANART_QUALITY_TIERS:
                if label == min_level:
                    if w < mw * (1 - tol) or h < mh * (1 - tol):
                        size_issues.append(
                            f"Resolution {w}×{h} is below minimum quality '{min_level}' "
                            f"({mw}×{mh})")
                    break
            # ── Proportion check 16:9 (and optionally 16:8) ──────────────────
            ratio = w / h
            accept_168 = SETTINGS.get("fanart_accept_168", False)
            ok_169 = (1.70 <= ratio <= 1.85)
            ok_168 = (1.45 <= ratio <= 1.55)
            if accept_168:
                if not (ok_169 or ok_168):
                    prop_issues.append(
                        f"Proportions {w}×{h} ({ratio:.2f}) — expected 16:9 (≈1.78) or 16:8 (≈1.50)")
            else:
                if not ok_169:
                    prop_issues.append(
                        f"Proportions {w}×{h} ({ratio:.2f}) — expected 16:9 landscape (≈1.78)")

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

### NEW v0.10.0 — fast pre-check before full XML parse ###
def _fast_precheck_xml(filepath):
    """
    Fast pre-check: file exists, non-zero, starts with < or BOM.
    Returns (ok: bool, reason: str).
    """
    if not os.path.isfile(filepath):
        return False, "File not found"
    try:
        size = os.path.getsize(filepath)
        if size == 0:
            return False, "File is empty (0 bytes)"
        with open(filepath, "rb") as f:
            head = f.read(min(64, size))
        # Allow BOM, XML declaration, or direct tag
        stripped = head.lstrip(b"\xef\xbb\xbf \t\r\n")
        if not stripped.startswith(b"<"):
            return False, "File does not appear to be XML (no < found near start)"
        return True, ""
    except Exception as e:
        return False, str(e)


def validate_xml_file(filepath, is_nfo=False):
    """Validate XML/NFO structure. Returns list of error dicts."""
    errors = []
    if not os.path.isfile(filepath): return errors
    ### NEW v0.10.0 — fast pre-check before heavy parse ###
    ok, reason = _fast_precheck_xml(filepath)
    if not ok:
        return [{"line": 0, "col": 0, "message": reason}]
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


### NEW v0.10.0 — extract display movie name with fallback chain ###
def get_movie_name_from_files(nfo_path, xml_path, subfolder_name):
    """
    Return best movie name with fallback priority:
    1. NFO <title>
    2. XML <LocalTitle>
    3. NFO <originaltitle>
    4. XML <OriginalTitle>
    5. Folder name (subfolder_name)
    v0.10.2: HTML entities decoded via html.unescape()
    """
    def _tag(fp, tag):
        if not fp or not os.path.isfile(fp): return ""
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if content.startswith("\ufeff"): content = content[1:]
            m = re.search(rf"<{tag}[^>]*>([^<]+)</{tag}>", content, re.IGNORECASE)
            if not m: return ""
            return html.unescape(m.group(1).strip())  # v0.10.2 — decode &amp; etc.
        except Exception: return ""
    for (fp, tag) in [
        (nfo_path, "title"),
        (xml_path, "LocalTitle"),
        (nfo_path, "originaltitle"),
        (xml_path, "OriginalTitle"),
    ]:
        v = _tag(fp, tag)
        if v: return v
    return subfolder_name


### NEW v0.10.0 — extract year with fallback ###
def get_movie_year_display(nfo_path, xml_path):
    """
    Return year string with fallback:
    1. NFO <year>
    2. XML <ProductionYear>
    3. "-"
    """
    def _tag(fp, tag):
        if not fp or not os.path.isfile(fp): return ""
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            m = re.search(rf"<{tag}[^>]*>([^<]+)</{tag}>", content, re.IGNORECASE)
            v = m.group(1).strip() if m else ""
            return v if re.match(r"^\d{4}$", v) else ""
        except Exception: return ""
    for (fp, tag) in [(nfo_path, "year"), (xml_path, "ProductionYear")]:
        v = _tag(fp, tag)
        if v: return v
    return "-"


def extract_rating_from_files(nfo_path, xml_path):
    """
    Extract movie rating from NFO and/or XML files.                ### NEW v0.12.0 ###

    Priority:
        1. NFO <rating>
        2. XML <IMDBrating>
        3. XML <Rating>

    Returns
    -------
    (rating_str, status, rating_value)
        rating_str  : display string e.g. "7.3" or "-"
        status      : STATUS_OK / STATUS_WARN / STATUS_ERROR / STATUS_MISSING
        rating_value: float for sorting, -1.0 when absent/invalid
    """
    def _try_float(s):
        try:
            return float(str(s).strip().replace(",", "."))
        except Exception:
            return None

    nfo_val = None
    xml_imdb_val = None
    xml_rating_val = None
    parse_error = False

    if nfo_path and os.path.isfile(nfo_path):
        try:
            with open(nfo_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            m = re.search(r'<rating[^>]*>([^<]*)</rating>', content, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                if raw:
                    val = _try_float(raw)
                    if val is not None:
                        nfo_val = val
                    else:
                        parse_error = True
        except Exception:
            parse_error = True

    if xml_path and os.path.isfile(xml_path):
        try:
            with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            for tag in ["IMDBrating", "Rating"]:
                m = re.search(rf'<{tag}[^>]*>([^<]*)</{tag}>', content, re.IGNORECASE)
                if m:
                    raw = m.group(1).strip()
                    if raw:
                        val = _try_float(raw)
                        if val is not None:
                            if tag.lower() == "imdbrating":
                                xml_imdb_val = val
                            else:
                                if xml_rating_val is None:
                                    xml_rating_val = val
                        else:
                            parse_error = True
        except Exception:
            parse_error = True

    if parse_error and nfo_val is None and xml_imdb_val is None and xml_rating_val is None:
        return "-", STATUS_ERROR, -1.0

    values = {}
    if nfo_val is not None:         values["nfo"] = nfo_val
    if xml_imdb_val is not None:    values["xml_imdb"] = xml_imdb_val
    if xml_rating_val is not None:  values["xml_rating"] = xml_rating_val

    if not values:
        return "-", STATUS_MISSING, -1.0

    primary = values.get("nfo", values.get("xml_imdb", values.get("xml_rating")))
    all_vals = list(values.values())
    has_conflict = len(all_vals) > 1 and any(abs(v - all_vals[0]) > 0.05 for v in all_vals[1:])

    rating_str = f"{primary:.1f}"
    status = STATUS_WARN if has_conflict else STATUS_OK
    return rating_str, status, primary


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
    """Extract all <genre> values from an NFO file. Returns list.
    v0.10.2: HTML entities decoded via html.unescape().
    """
    if not nfo_path or not os.path.isfile(nfo_path):
        return []
    root, fb = _safe_parse_xml(nfo_path)
    if root is not None:
        return [html.unescape(el.text.strip()) for el in root.iter('genre')
                if el.text and el.text.strip()]  # v0.10.2 — decode &amp; etc.
    return [html.unescape(g) for g in fb.get("genres", [])]  # v0.10.2

def classify_genres(genres):
    """
    Return (display_str, status) for the genre column.
    status: STATUS_OK / STATUS_WARN / STATUS_ERROR
    v0.12.0: custom genres (not in settings list after normalization) ### NEW v0.12.0 ###
             now correctly show STATUS_WARN instead of STATUS_OK.
    """
    if not genres:
        return "—", STATUS_ERROR   # missing = red
    valid = _get_valid_genres()
    display = "/".join(genres)
    for g in genres:
        lower = g.lower()
        # Check synonym map first — if it maps to a valid genre, it just needs normalizing
        canonical = _GENRE_SYNONYMS.get(lower)
        if canonical:
            # Synonym exists but genre hasn't been normalized yet → warn
            if canonical != g:
                return display, STATUS_WARN
        else:
            # No synonym — check if the genre (or its normalized form) is in the valid list
            normalized = normalize_genre(g)
            in_valid = (g in valid or
                        g.title() in valid or
                        normalized in valid or
                        normalized.lower() in {v.lower() for v in valid})
            if not in_valid:
                return display, STATUS_WARN
    # All genres are valid and correctly capitalized
    return display, STATUS_OK

def write_genres_to_nfo(nfo_path, genres):
    """
    Write normalized genres back to NFO file.
    v0.10.5: replaces tags one-for-one at their original line positions,
    preserving the original indentation of each <genre> tag.
    Extra new genres are inserted after the last existing genre tag.
    Surplus old tags (if new list is shorter) are removed.
    If no genre tags exist, inserts before </movie> or at end of file.
    """
    if not nfo_path or not os.path.isfile(nfo_path):
        return False, "NFO file not found"
    try:
        with open(nfo_path, "r", encoding="utf-8", errors="replace") as f:
            file_lines = f.readlines()

        # Locate all existing <genre> lines (line index + detected indent)
        genre_pattern = re.compile(r'(^[ \t]*)<genre>[^<]*</genre>\s*$',
                                   re.IGNORECASE)
        genre_line_indices = []   # list of (line_index, indent_str)
        for i, line in enumerate(file_lines):
            m = genre_pattern.match(line)
            if m:
                genre_line_indices.append((i, m.group(1)))

        if genre_line_indices:
            # Replace existing tags one-for-one
            new_idx = 0
            for pos, (line_i, indent) in enumerate(genre_line_indices):
                if new_idx < len(genres):
                    # Replace this line with the new genre, keeping indent
                    file_lines[line_i] = f"{indent}<genre>{genres[new_idx]}</genre>\n"
                    new_idx += 1
                else:
                    # More old tags than new genres — mark for removal
                    file_lines[line_i] = None

            # Remove lines marked for deletion
            file_lines = [l for l in file_lines if l is not None]

            # If new list is longer, insert extra genres after the last tag
            if new_idx < len(genres):
                # Find the new position of the last genre line after removals
                last_indent = genre_line_indices[min(new_idx, len(genre_line_indices)-1)][1]
                last_genre_line = f"{last_indent}<genre>{genres[new_idx-1]}</genre>\n"
                # Locate it in the (possibly modified) file_lines
                insert_at = None
                for i, l in enumerate(file_lines):
                    if l == last_genre_line:
                        insert_at = i + 1
                if insert_at is None:
                    # Fallback: insert before </movie>
                    for i, l in enumerate(file_lines):
                        if re.search(r'</movie>', l, re.IGNORECASE):
                            insert_at = i
                            break
                if insert_at is None:
                    insert_at = len(file_lines)
                extras = [f"{last_indent}<genre>{genres[j]}</genre>\n"
                          for j in range(new_idx, len(genres))]
                file_lines[insert_at:insert_at] = extras

        else:
            # No existing genre tags — insert before </movie> or at end
            indent = "\t"   # default indent (tab, matching typical NFO style)
            # Try to detect indentation from a nearby tag
            for line in file_lines:
                m = re.match(r'([ \t]+)<', line)
                if m:
                    indent = m.group(1)
                    break
            new_lines = [f"{indent}<genre>{g}</genre>\n" for g in genres]
            insert_at = None
            for i, line in enumerate(file_lines):
                if re.search(r'</movie>', line, re.IGNORECASE):
                    insert_at = i
                    break
            if insert_at is not None:
                file_lines[insert_at:insert_at] = new_lines
            else:
                file_lines.extend(new_lines)

        with open(nfo_path, "w", encoding="utf-8") as f:
            f.writelines(file_lines)
        return True, ""
    except Exception as e:
        return False, str(e)

def write_genres_to_xml(xml_path, genres):
    """
    Write normalized genres back to XML file, replacing <Genres><Genre>…</Genre></Genres>.
    v0.11.0 fix: mirrors the original indentation of <Genres> and <Genre> tags
    instead of hardcoding spaces, so the surrounding lines are not disturbed.
    """                                                              ### NEW v0.11.0 ###
    if not xml_path or not os.path.isfile(xml_path):
        return False, "XML file not found"
    try:
        with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
            file_lines = f.readlines()

        # ── Detect original indentation from the existing <Genres> block ──────
        # We look for the line containing <Genres> to get the outer indent,
        # and for any <Genre>…</Genre> line to get the inner indent.
        genres_indent = "\t"          # fallback outer indent
        genre_indent  = "\t\t"        # fallback inner indent
        genres_open_idx = None        # line index of <Genres>
        genres_close_idx = None       # line index of </Genres>

        for i, line in enumerate(file_lines):
            stripped = line.rstrip("\r\n")
            lstripped = stripped.lstrip()
            if re.search(r'<Genres\b[^>]*>', stripped, re.IGNORECASE) and genres_open_idx is None:
                genres_open_idx = i
                # Indent of <Genres …> itself
                genres_indent = stripped[:len(stripped) - len(lstripped)]
            if re.search(r'</Genres\s*>', stripped, re.IGNORECASE) and genres_open_idx is not None:
                genres_close_idx = i
            if genres_open_idx is not None and genres_close_idx is None:
                # Inside the block — look for an existing <Genre> line
                m = re.match(r'([ \t]*)<Genre>', stripped, re.IGNORECASE)
                if m:
                    genre_indent = m.group(1)

        # ── Build the replacement block lines (as strings with newlines) ───────
        block_lines = []
        block_lines.append(f"{genres_indent}<Genres>\n")
        for g in genres:
            block_lines.append(f"{genre_indent}<Genre>{g}</Genre>\n")
        block_lines.append(f"{genres_indent}</Genres>\n")

        if genres_open_idx is not None and genres_close_idx is not None:
            # Replace from <Genres> up to and including </Genres>
            new_lines = (file_lines[:genres_open_idx]
                         + block_lines
                         + file_lines[genres_close_idx + 1:])
        else:
            # No existing <Genres> block — insert before closing root tag
            content = "".join(file_lines)
            root_close = re.search(r'</\w+>\s*$', content)
            if root_close:
                insert_char = root_close.start()
                # Find the line index that contains that character
                char_count = 0
                insert_line = len(file_lines)
                for i, line in enumerate(file_lines):
                    char_count += len(line)
                    if char_count > insert_char:
                        insert_line = i
                        break
                new_lines = (file_lines[:insert_line]
                             + block_lines
                             + file_lines[insert_line:])
            else:
                new_lines = file_lines + block_lines

        with open(xml_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
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
    v0.11.0: backup created before writing.            ### NEW v0.11.0 ###
    """
    errors = []

    def _replace_tag(content, tag, value):
        """Replace <tag>old</tag> or add before closing root if missing."""
        pattern = rf'(<{tag}[^>]*>)[^<]*(</\s*{tag}\s*>)'
        if re.search(pattern, content, re.IGNORECASE):
            return re.sub(pattern, rf'\g<1>{value}\2', content,
                          flags=re.IGNORECASE)
        return content   # tag not found: leave as-is (don't inject new tags)

    # Backup before any writes                          ### NEW v0.11.0 ###
    _make_backup("rating_sync", nfo_path, xml_path)

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

def scan_one_subfolder(sub_path, sub_name, use_ffprobe=None, force_ffprobe=False):
    """Full scan of a single subfolder. Returns result dict.
    force_ffprobe=True runs FFprobe regardless of the global use_ffprobe setting.
    ### NEW v0.12.0 — force_ffprobe parameter added ###
    """
    if force_ffprobe:
        use_ffprobe = True
    elif use_ffprobe is None:
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

    # Rating extraction (v0.12.0)                         ### NEW v0.12.0 ###
    rating_str, rating_status, rating_value = extract_rating_from_files(
        nfo_path if ne else None, xml_path if xe else None)

    has_err = (ns == STATUS_ERROR or xs == STATUS_ERROR or pc or fc or flc)
    health  = ("red"    if has_err
               else "green" if (pe and fe and fle and
                                 ns == STATUS_OK and xs == STATUS_OK and
                                 vi["video_count"] == 1)
               else "yellow")

    # v0.10.0 — compute display name and year
    movie_name = get_movie_name_from_files(
        nfo_path if ne else None, xml_path if xe else None, sub_name)
    movie_year = get_movie_year_display(
        nfo_path if ne else None, xml_path if xe else None)

    ### NEW v0.11.0 — compute image quality tiers ###
    pw, ph = get_image_wh(poster_path) if pe else (None, None)
    flw, flh = get_image_wh(folder_path) if fle else (None, None)
    fw, fh   = get_image_wh(fanart_path) if fe else (None, None)

    return {
        "subfolder": sub_name, "subfolder_path": sub_path,
        "movie_name": movie_name, "movie_year": movie_year,
        "poster_exists": pe, "poster_path": poster_path,
        "poster_bytes": pb, "poster_size": format_size(pb) if pe else "—",
        "poster_dim": pd, "poster_corrupt": pc, "poster_desc": ps_desc,
        "poster_status": ps_status,
        "poster_quality": classify_image_quality(pw, ph, "poster") if pe else "—",  ### NEW v0.11.0 ###
        "fanart_exists": fe, "fanart_path": fanart_path,
        "fanart_bytes": fb, "fanart_size": format_size(fb) if fe else "—",
        "fanart_dim": fd, "fanart_corrupt": fc, "fanart_desc": fs_desc,
        "fanart_status": fs_status,
        "fanart_quality": classify_image_quality(fw, fh, "fanart") if fe else "—",  ### NEW v0.11.0 ###
        "folder_exists": fle, "folder_path": folder_path,
        "folder_bytes": flb, "folder_size": format_size(flb) if fle else "—",
        "folder_dim": fld, "folder_corrupt": flc, "folder_desc": fls_desc,
        "folder_status": fls_status,
        "folder_quality": classify_image_quality(flw, flh, "folder") if fle else "—",  ### NEW v0.11.0 ###
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
        "rating_str": rating_str, "rating_status": rating_status,   ### NEW v0.12.0 ###
        "rating_value": rating_value,                                ### NEW v0.12.0 ###
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
        "movie_name": "", "movie_year": "-",
        # v0.11.0 — image quality tiers                      ### NEW v0.11.0 ###
        "poster_quality": "—", "folder_quality": "—", "fanart_quality": "—",
        # v0.12.0 — rating                                   ### NEW v0.12.0 ###
        "rating_str": "-", "rating_status": STATUS_MISSING, "rating_value": -1.0,
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
# ── Sort options for Movies tab ──────────────────────────────────────────────
# SORT_OPTIONS keys are displayed in the sort combo box.
# Values: (key_function, reverse_flag)
# All key functions receive a row data dict and return a sortable value.
#
# v0.11.0: sort order matches column order (Movie Name, Year, Genres, Poster,
#          Folder, Fanart, …, Video Size, Quality, Lang OK?, Backdrops).
#          Poster/Folder/Fanart size sorts replaced with quality-based sorts.
#          Folder Quality sorts are new.
#          Health sorts remain at the bottom (multi-column).
#
# Phase B: SORT_OPTIONS references COLUMN_MODEL ids implicitly via lambdas.
# The sort combo is populated from list(SORT_OPTIONS.keys()).
#
# Phase C TODO: define SERIES_SORT_OPTIONS dict for the Series tab.
# The Series tab sort combo will be populated from SERIES_SORT_OPTIONS.
SORT_OPTIONS = {                                                 ### NEW v0.11.0 ###
    # ── Single-column sorts, ordered to match column order ──────────────────
    "Movie Name (A-Z)":           (lambda r: r.get("movie_name","").lower(), False),
    "Movie Name (Z-A)":           (lambda r: r.get("movie_name","").lower(), True),
    "Year (older first)":         (lambda r: r.get("movie_year","-"),        False),
    "Year (newer first)":         (lambda r: r.get("movie_year","-"),        True),
    "Genre (A-Z)":                (lambda r: r.get("genre_display","").lower(), False),
    "Genre (Z-A)":                (lambda r: r.get("genre_display","").lower(), True),
    ### NEW v0.12.0 — Rating sort options ###
    "Rating (high→low)":          (lambda r: r.get("rating_value", -1.0),   True),
    "Rating (low→high)":          (lambda r: r.get("rating_value", -1.0),   False),
    # Poster Quality (replaces Poster Size)
    "Poster Quality (high→low)":  (lambda r: _poster_quality_sort_key_missing_last(r, "poster_quality", True),  True),
    "Poster Quality (low→high)":  (lambda r: _poster_quality_sort_key_missing_last(r, "poster_quality", False), False),
    # Folder Quality (new)
    "Folder Quality (high→low)":  (lambda r: _poster_quality_sort_key_missing_last(r, "folder_quality", True),  True),
    "Folder Quality (low→high)":  (lambda r: _poster_quality_sort_key_missing_last(r, "folder_quality", False), False),
    # Fanart Quality (replaces Fanart Size)
    "Fanart Quality (high→low)":  (lambda r: _fanart_quality_sort_key_missing_last(r, "fanart_quality", True),  True),
    "Fanart Quality (low→high)":  (lambda r: _fanart_quality_sort_key_missing_last(r, "fanart_quality", False), False),
    # Video Size
    "Video size (lg→sm)":         (lambda r: r["video_bytes"],         True),
    "Video size (sm→lg)":         (lambda r: r["video_bytes"],         False),
    # Language / Quality / Lang OK? / Backdrops
    "Language (A→Z)":             (lambda r: r["language"].lower(),    False),
    "Language (Z→A)":             (lambda r: r["language"].lower(),    True),
    "Quality (best first)":       (lambda r: _quality_sort_key(r.get("video_quality","—")), False),
    "Quality (worst first)":      (lambda r: _quality_sort_key(r.get("video_quality","—")), True),
    "Lang OK? (Y first)":         (lambda r: r.get("lang_ok","—"),     False),
    "Lang OK? (N first)":         (lambda r: r.get("lang_ok","—"),     True),
    "Backdrops (most)":           (lambda r: r["backdrop_count"],      True),
    "Backdrops (fewest)":         (lambda r: r["backdrop_count"],      False),
    # ── Multi-column sorts — always at the bottom ──────────────────────────
    "Health (errors 1st)":        (lambda r: {"red":0,"yellow":1,"green":2}.get(r["row_health"],1), False),
    "Health (OK 1st)":            (lambda r: {"green":0,"yellow":1,"red":2}.get(r["row_health"],1), False),
}


# ══════════════════════════════════════════════════════════════════════════════
# SERIES MODE — Scanning pipeline placeholders (Phase B)
# ══════════════════════════════════════════════════════════════════════════════
#
# Phase C will implement full series scanning. The stubs below define the
# expected function signatures so that Phase C can fill them in without
# changing the call sites in App._start_scan_series().
#
# SERIES FOLDER STRUCTURE (expected for Phase C):
#   <root>/
#     ShowName (Year)/
#       Season 01/
#         ShowName S01E01.mkv
#         ShowName S01E01.nfo
#         ShowName S01E01-thumb.jpg
#         season01-poster.jpg
#         season01-landscape.jpg
#       Season 02/
#         ...
#       show.nfo          ← series-level NFO
#       poster.jpg        ← show poster
#       fanart.jpg        ← show fanart
#       banner.jpg        ← optional banner
#
# TODO (Phase C): implement the following stubs.

def scan_one_series(series_path, series_name):
    """
    Phase C placeholder — full scan of a single series folder.
    Returns a series result dict (structure TBD in Phase C).

    Expected keys (Phase C):
        series_name, series_path, show_nfo_exists, show_nfo_path,
        show_poster_exists, show_fanart_exists, season_count,
        episode_count, missing_episode_nfos, missing_thumbnails,
        genres, year, row_health
    """
    # TODO (Phase C): implement series scanning logic
    raise NotImplementedError("Series scanning not yet implemented (Phase C)")


def scan_one_season(season_path, season_number, series_name):
    """
    Phase C placeholder — scan a single season subfolder.
    Returns a season result dict.
    """
    # TODO (Phase C): implement season scanning logic
    raise NotImplementedError("Season scanning not yet implemented (Phase C)")


def scan_one_episode(episode_path, episode_name):
    """
    Phase C placeholder — scan a single episode file + sidecar files.
    Returns an episode result dict.
    """
    # TODO (Phase C): implement episode scanning logic
    raise NotImplementedError("Episode scanning not yet implemented (Phase C)")


# ── Series sort options placeholder ──────────────────────────────────────────
# TODO (Phase C): define SERIES_SORT_OPTIONS dict analogous to SORT_OPTIONS.
# SERIES_SORT_OPTIONS = {
#     "Show Name (A-Z)":   (lambda r: r.get("series_name","").lower(), False),
#     "Show Name (Z-A)":   (lambda r: r.get("series_name","").lower(), True),
#     "Year (older first)":(lambda r: r.get("year","-"),               False),
#     "Year (newer first)":(lambda r: r.get("year","-"),               True),
#     "Season count":      (lambda r: r.get("season_count",0),         True),
#     "Episode count":     (lambda r: r.get("episode_count",0),        True),
#     "Health (errors 1st)":(lambda r: {"red":0,"yellow":1,"green":2}.get(r.get("row_health","yellow"),1), False),
# }

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
        name = d.get("movie_name", d["subfolder"])  ### NEW v0.10.0 — use movie_name ###

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
        return "[OK] No improvements needed — all checks passed!\n"
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
        lines.append("[OK] No improvement issues found.\n\n")

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
            msg = (f"Done! All {n_frames} frame(s) extracted!\n\n"
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
            msg = (f"Partial: {n_ok}/{n_frames} frames saved.\n\nFailed ({n_bad}):\n{detail}\n\n"
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
            elif line.startswith("[OK]"):
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
        # v0.10.4 — Open in Editor button: opens file to allow correction
        tk.Button(bf, text="  Open in Editor to Fix  ", font=("Helvetica",10,"bold"),
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

# ══════════════════════════════════════════════════════════════════════════════
# SettingsDialog — moved to settings_dialog.py (Phase B)
# ══════════════════════════════════════════════════════════════════════════════
# SettingsDialog is imported at the top of this file:
#   from settings_dialog import SettingsDialog
# All settings UI code lives in settings_dialog.py.
# The class is available here under the same name with identical public API.
#
# Tab registry (for reference — authoritative copy is in settings_dialog.py):
#   0  Tools          Editor, FFmpeg, Backdrop, Scraper
#   1  API Keys       TMDb + OMDb key entry and validation
#   2  Browser        Default browser selection
#   3  Language OK?   Target language for Lang OK? column
#   4  Improvements   Check toggles and thresholds
#   5  Image Sizes    Minimum KB per image type
#   6  Genres         Editable genre list
#   7  NFO-XML Tags   Tag comparison pairs
# Phase C: tab 8 = Series settings

class HelpDialog(tk.Toplevel):
    """
    Full application help — rebuilt for v9.0.
    Six tabs: Getting Started · Table & Columns · Actions · Settings · Tools & APIs · About
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title(f"Help — {APP_NAME}  v{APP_VERSION}")
        self.geometry("820x640")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(True, True)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        style = ttk.Style()
        style.configure("TNotebook",     background="#1e1e2e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4",
                        padding=[10,5], font=("Helvetica",9))
        style.map("TNotebook.Tab",
                  background=[("selected","#45475a")],
                  foreground=[("selected","#89b4fa")])

        self._add_tab(nb, "🚀  Getting Started",   self._TAB_START)
        self._add_tab(nb, "📊  Table & Columns",    self._TAB_TABLE)
        self._add_tab(nb, "🖱  Actions",             self._TAB_ACTIONS)
        self._add_tab(nb, "⚙️  Settings",            self._TAB_SETTINGS)
        self._add_tab(nb, "🔧  Tools & APIs",        self._TAB_TOOLS)
        self._add_tab(nb, "⌨  Shortcuts",           self._TAB_SHORTCUTS)
        self._add_about_tab(nb)

        tk.Button(self, text="  Close  ", font=("Helvetica",10,"bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self.destroy).pack(pady=(6,12))

    # ── Tab content ────────────────────────────────────────────────────────────

    _TAB_START = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Metadata & MediaClinic  v0.12.0  -  Getting Started
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT IS THIS APP?
  Metadata & MediaClinic is a KODI media library auditor and repair
  tool. It scans a folder of movie subfolders, checks every piece of
  artwork and metadata, and gives you a colour-coded health table so
  you can see at a glance what is missing or broken — and fix it.

  One subfolder = one movie. Each subfolder should contain:
    • poster.jpg     — portrait cover art (2:3 ratio)
    • folder.jpg     — identical copy of poster.jpg for KODI
    • fanart.jpg     — wide background art (16:9 ratio)
    • backdrop.jpg, backdrop1.jpg …  — scene frames
    • MovieName.nfo  — KODI metadata in XML format
    • movie.xml      — Emby/Jellyfin metadata in XML format
    • MovieName.mkv  (or .mp4, .avi, etc.)

FIRST RUN
  1. Click  Browse…  and select your root media folder.
  2. Click  Scan.
     The table fills in phases — subfolders first, then images,
     then metadata, then video (with FFprobe if enabled).
  3. Each row shows the health of one movie:
       [GREEN row]  — all key files present and valid
       [YELLOW row] — one or more files missing or warnings present
       [RED row]    — a file has a structural error
  4. Your last scan is saved automatically and restored on startup.

QUICK-START CHECKLIST
  □  Set your FFmpeg path in Settings → Tools  (enables video analysis
     and backdrop extraction)
  □  Add your TMDb and/or OMDb API keys in Settings → API Keys
     (enables online ratings sync)
  □  Configure your preferred browser in Settings → Browser
  □  Set the "Lang OK?" language target in Settings → Language OK?
     (default: PT — Portuguese)
  □  Run a scan, sort by "Health (errors 1st)" to triage problems

ROW COLOURS AT A GLANCE
  [GREEN] All OK     — poster, folder, fanart, NFO, XML all present & valid,
                  exactly one video file
  [YELLOW] Warning  — something is missing but no hard errors; also shown
                  when image proportions are off (non-blocking)
  [RED] Error        — XML/NFO parse error, empty or corrupt image file,
                  or image below minimum size threshold

STATUS ICONS
  ⬤  OK / valid / present
  ◐  Warning — proportion mismatch or minor issue (non-blocking)
  ○/✕  Error or missing (action required)

AUTOMATIC BACKUPS
  Whenever the application modifies a .nfo or .xml file, it creates a
  backup copy automatically before writing. Backups are stored in the
  "backup" subfolder next to the application script, in timestamped
  subfolders named:
    backup_MovieName_YYYY-MM-DD_HH-MM-SS
  No popup is shown — backups are silent. Check the application log
  (logs/app.log) for a record of every backup created.
"""

    _TAB_TABLE = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Table & Columns  (v0.12.0)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COLUMN REFERENCE
  Movie Name      - Movie title extracted from NFO/XML. Double-click opens folder.

  Year            - Production year from NFO <year> or XML <ProductionYear>.

  Genres          - Genre list from NFO <genre> tags, e.g. "Drama/Thriller".
                    ⬤ All genres match standard list
                    ◐ Capitalisation or synonym issues (can be auto-fixed)
                    ○ No <genre> tags found in NFO

  Poster / Size   — poster.jpg presence and file size.
                    ⬤ OK  ◐ Proportion warning  ○/✕ Error/Missing
                    Expected: 2:3 portrait ratio (≈0.67).

  Folder / Size   — folder.jpg presence and file size. Should be an
                    identical copy of poster.jpg for KODI compatibility.

  Fanart / Size   — fanart.jpg presence and file size.
                    Expected: 16:9 landscape ratio (≈1.78).

  Bkdrps          — Count of backdrop.jpg, backdrop1.jpg … files found.
                    Shows "—" when none exist. Not an error column.

  .nfo            — Unified status column (v0.10.4):
                    ⬤ = present and valid XML
                    ○ = file missing
                    ✕ = present but has parse errors
                    Double-click → show errors (if any) then open in editor

  .xml            — Unified status column (v0.10.4):
                    Same symbol logic as .nfo above.

  Language        — Language tag read from movie.xml <Language> element.

  Video / Video Size — Video file format (MKV, MP4 …) and size on disk.
                    ○ = no video file found in the subfolder.

  Quality         — Video resolution class determined by FFprobe:
                    4K UHD / 1440p / 1080p / 720p / 576p/DVD / 480p / SD
                    Shows "—" when FFprobe is disabled or no video exists.
                    FFprobe results are retained across re-validations that
                    do not use FFprobe — they are only cleared when you
                    explicitly run Re-validate (with FFMPEG).

  Lang OK?        — Checks for a configured target language in:
                    FFprobe audio streams, embedded subtitles, external
                    subtitle files, XML tags, NFO tags.
                    Y = found  /  N = not found  /  — = no video
                    Configure target language in Settings → Language OK?

  Subtitles       — Summary of embedded (Int:) and external (Ext:) tracks.

SORTING
  Choose a sort order from the dropdown — the table updates instantly.
  Available sorts include movie name, year, genres, image sizes, video
  size, quality, language, backdrops, health, and Lang OK? status.
  The "Update Sort" button re-sorts without re-scanning.

COLUMN TOOLTIPS
  Hover over any column header for a description of what it means.
  Hover over any cell for detailed file information (size, dimensions,
  ratio, error summary, subtitle track list, etc.).

COLUMN WIDTH
  • Double-click a column header → auto-size that column.
  • Click "⟺ Auto-size Columns" → auto-size all columns at once.

EXPORT CSV
  The "Export CSV" button saves the entire table to a .csv file,
  including all metadata, error counts, subtitle tracks, and quality.

KEYBOARD NAVIGATION
  Page Up / Down  — move 20 rows at a time
  Home / End      — jump to first / last row
  Shift + ↑ / ↓  — extend the selection to multiple rows
"""

    _TAB_ACTIONS = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Actions — Double-click & Right-click
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOUBLE-CLICK ACTIONS
  Column          What happens
  --------------- --------------------------------------------------
  Movie Name      Opens the movie folder in Explorer (double-click)
  Year            Production year - no double-click action
  Poster/Size     Opens poster.jpg with default image viewer
  Folder/Size     Opens folder.jpg with default image viewer
  Fanart/Size     Opens fanart.jpg with default image viewer
  Backdrops       Opens first backdrop.jpg (if any exist)
  .nfo            Opens NFO in configured editor — always
  OK? (NFO)       Shows XML error dialog if errors; else opens editor
  .xml            Opens movie.xml in configured editor — always
  OK? (XML)       Shows XML error dialog if errors; else opens editor
  Language        Opens movie.xml in configured editor
  Video/Size      Plays the video with default media player
  Quality         Plays the video with default media player
  Subtitles       Opens the Subtitle Detail dialog
  Genres          Opens NFO in configured editor

RIGHT-CLICK MENU — Single movie
  📂 Open subfolder        - open in Explorer
  🖼  poster / folder / fanart - open image file
  🎬 Play video            - open with default player
  🎞️ Extract Backdrop(s)   - extract frames via FFmpeg (configurable count)
  💬 Subtitles…            - detailed embedded + external subtitle list
  📝 Open .nfo / movie.xml  - open in configured text editor
  [!] NFO / XML errors     - show parse error list with line numbers
  🌐 Open on IMDB          - open IMDb title page (reads ID from NFO/XML)
  🌐 Open on TMDb          - open TMDb movie page
  🌐 Open on OpenSubtitles - search OpenSubtitles using title + year
  📋 Copy Movie Name       - silent copy; picker shown if NFO/XML differ
  🎬 Open in Scraper       - launch configured scraper with movie folder
  🔍 Run Improvements Check - health-check popup with Copy/Save options
  ⭐ Sync Ratings           - fetch updated rating/votes from TMDb + IMDb
  🎬 Normalize Genres      - fix capitalisation, synonyms, duplicates
  🔄 Re-validate            - full rescan of this row without full scan
  🔬 Re-validate FFmpeg Metadata - re-run FFprobe only (fast, no rescan)

RIGHT-CLICK MENU — Multiple selected rows (Shift+click or Shift+↑↓)
  All single-movie options above, plus:
  🔍 Run Improvements Check (N movies) - batch health check
  ⭐ Sync Ratings (N movies)           - batch ratings sync
  🎬 Normalize Genres (N movies)       - batch genre normalisation
  🎞️ Extract Backdrop(s) (N movies)    - batch frame extraction

TOOLS MENU (menu bar)
  🎬 Normalize Genres — All Movies    - normalize all movies (asks confirmation)
  ⭐ Sync Ratings — Selected Movies   - quick access to ratings sync for selection

SCAN BUTTONS
  Browse…        - pick root media folder
  Scan           - full scan of selected folder
  Update Scan    - re-scan same folder (keeps folder selection)
  Cancel         - abort scan in progress; partial results are kept
  Extract Frames - extract backdrop frames (right-click for more options)
  Export CSV     - save table to .csv file
  FFprobe ☑     - uncheck to skip FFprobe (much faster; no quality/subs data)
  ↺ Update Sort  - re-sort table in memory
  ⟺ Auto-size Columns - fit all columns to content

IMPROVEMENTS HEALTH CHECK (right-click → Run Improvements Check)
  Runs six configurable checks and shows a popup report:
  1. Large XML / NFO files (above configured KB threshold)
  2. NFO ↔ XML data mismatches (compares all configured tag pairs)
  3. FFprobe vs NFO/XML metadata (resolution, duration, codec)
  4. poster.jpg ≠ folder.jpg (different dimensions or file size)
  5. Image proportion or size issues (also listed as warnings in table)
  6. Insufficient backdrop frames (below configured minimum)
  The report also appends any scan errors (XML parse errors) in red.
  Use the Copy and Save buttons to preserve the report.

BACKDROP EXTRACTION (right-click → Extract Backdrop(s))
  Opens a dialog showing:
  • The video filename being processed
  • A spinner to set how many frames to extract (default from Settings)
  • A per-frame timeout spinner
  • Animated progress bar with ETA
  Frames are saved as backdrop.jpg, backdrop1.jpg, backdrop2.jpg … in
  the movie folder. Existing backdrops are not overwritten — new ones
  are numbered from where the existing sequence ends.

RATINGS SYNC (right-click → Sync Ratings)
  Requires API keys in Settings → API Keys.
  For each selected movie the app:
  1. Reads IMDb ID (for OMDb) and TMDb ID from NFO/XML (with fallback parser)
  2. Fetches rating and vote count from TMDb and/or OMDb in a background thread
  3. If BOTH sources return data → shows a comparison dialog; you choose
     which to use, with an "Apply to All" option for batch runs
  4. If ONLY ONE source returns data → uses it automatically
  5. If NEITHER returns data → asks you to enter values manually
  6. Writes chosen rating and votes to all matching tags in NFO and XML

NORMALIZE GENRES (right-click → Normalize Genres)
  Reads all <genre> tags from NFO, applies normalisation:
  • Trims leading/trailing whitespace
  • Fixes capitalisation (e.g. "drama" → "Drama")
  • Maps synonyms to standard names (e.g. "Sci-Fi" → "Science Fiction")
  • Removes duplicate genres (preserves order)
  Writes back to NFO (<genre> tags) and XML (<Genres><Genre> block).
  The standard genre list is based on TMDb and is editable in Settings → Genres.
"""

    _TAB_SETTINGS = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Settings Reference
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Open Settings from: menu bar → Settings → All Settings…
(or choose a specific sub-menu to jump straight to that tab)

─────────────────────────────────────────────────────────────
🔧  TOOLS TAB
─────────────────────────────────────────────────────────────
Text Editor
  Path to the editor used when opening NFO and XML files.
  Notepad++ is auto-detected on open. If Notepad++ is found, files
  are opened with:  notepad++.exe "path\\file.ext" -lxml
  (file path comes first — this avoids the "create new file?" bug).
  If not set, falls back to the OS default application.

FFmpeg / FFprobe
  Path to the folder containing ffmpeg.exe and ffprobe.exe.
  Leave blank to use the system PATH. Auto-detects on open.
  Use "Test FFmpeg" to verify both executables are working.

Backdrop Extraction
  Default frame count (1–50, default 10). This value pre-fills the
  spinner in the extraction dialog. It is also saved when you change
  the spinner in the dialog itself.

Video Scraper / Metadata Source
  Choose the metadata source for ratings sync and future operations:
    TMDb (recommended) — The Movie Database, free API
    IMDb via OMDb API  — IMDb data via the OMDb wrapper, free tier
  Note: online metadata fetching is in development — ratings sync
  is available now; full scraping will be enabled in a future update.
  The scraper executable field allows you to launch an external
  scraper (e.g. tinyMediaManager) with the movie folder as argument.

─────────────────────────────────────────────────────────────
🔑  API KEYS TAB
─────────────────────────────────────────────────────────────
TMDb API Key
  Required for ratings sync using The Movie Database.
  Free — no subscription. Steps to get your key:
  1. Create a free account at themoviedb.org
  2. Go to Settings → API (left sidebar after login)
  3. Click "Request an API Key" → choose Developer
  4. Fill in the short form — key is issued immediately
  5. Copy the "API Key (v3 auth)" here
  Click "Validate" to test your key before saving.
  Click the blue link to go directly to the TMDb API page.
  Your key is stored locally in settings.json and never transmitted
  to any third party.

OMDb API Key (IMDb data)
  Required for fetching IMDb ratings via the OMDb API.
  Free tier: 1,000 requests per day. Steps:
  1. Go to omdbapi.com/apikey.aspx
  2. Choose FREE tier, enter your email
  3. Activate the key from the email you receive
  4. Paste the key here and click "Validate"

─────────────────────────────────────────────────────────────
🌐  BROWSER TAB
─────────────────────────────────────────────────────────────
  Choose which browser opens when you click external links
  (IMDB, TMDb, OpenSubtitles, API key pages).
  The app auto-detects Chrome, Firefox, Edge, Brave, Opera, Vivaldi
  from standard Windows install locations. Select one or choose
  "System Default" to let Windows decide. You can also type or
  browse to any browser executable manually.

─────────────────────────────────────────────────────────────
🌍  LANGUAGE OK? TAB
─────────────────────────────────────────────────────────────
  Choose the target language for the "Lang OK?" column.
  The column header updates to show the selected ISO code (e.g. "PT OK?").
  Checked sources (in priority order):
  1. FFprobe audio stream language tags
  2. Embedded subtitle tracks (via FFprobe)
  3. External subtitle files (language inferred from filename suffix)
  4. XML <LanguageCode> and <Language> tags
  5. NFO <language> tag inside <streamdetails>
  30 languages available including Chinese, Spanish, English,
  Portuguese, French, German, Japanese, and more.

─────────────────────────────────────────────────────────────
🔍  IMPROVEMENTS TAB
─────────────────────────────────────────────────────────────
  Toggle which checks run when you use "Run Improvements Check":
  2.1  Large XML/NFO  — flag files above the configured KB threshold
  2.2  NFO↔XML Mismatch — compare tag values across both files
  2.3  FFprobe vs Metadata — compare actual video properties vs stored
  2.4  Poster ≠ Folder — flag when poster.jpg and folder.jpg differ
  2.5  Proportions & Size — flag wrong image ratios or small files
  2.6  Insufficient Backdrops — flag when count is below minimum

  Thresholds:
  • Max NFO size before flagging as "Large" (default 50 KB)
  • Max XML size before flagging as "Large" (default 25 KB)
  • Minimum backdrop count required (default 5)

─────────────────────────────────────────────────────────────
🖼  IMAGE SIZES TAB
─────────────────────────────────────────────────────────────
  Set minimum file sizes (in KB) for each image type.
  Files below the minimum are flagged as errors (✕).
  Set to 0 to skip the size check for that image type.
  Defaults: poster.jpg 100 KB · folder.jpg 100 KB · fanart.jpg 200 KB

  Note: Wrong proportions are always a warning (◐), not an error,
  regardless of size settings:
  • poster.jpg / folder.jpg — expected 2:3 portrait (ratio ≈ 0.67)
  • fanart.jpg              — expected 16:9 landscape (ratio ≈ 1.78)

─────────────────────────────────────────────────────────────
🎬  GENRES TAB
─────────────────────────────────────────────────────────────
  The standard genre list used by "Normalize Genres".
  Based on TMDb's official genre list (18 genres).
  Add your own custom genres — one per line. They will be treated
  as valid during normalisation checks and will not be flagged.
  Blank lines are removed automatically on save.
  Click "Reset to TMDb defaults" to restore the original 18 genres.

─────────────────────────────────────────────────────────────
🏷  NFO-XML TAGS TAB
─────────────────────────────────────────────────────────────
  Defines the tag comparison pairs used in Improvements check 2.2
  (NFO ↔ XML mismatch). One pair per line, tab-separated:
    nfo_tag  xml_tag  Label  tolerance%
  Dot notation for nested tags:
    fileinfo.streamdetails.video.width   MediaInfo.Video.Width   Width  0
  Tolerance% allows numeric values to differ by that percentage
  without triggering a mismatch (useful for duration, channels).
  Click "Reset to defaults" to restore the built-in 34 pairs.
"""

    _TAB_TOOLS = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Tools & API Reference
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FFMPEG & FFPROBE
  FFmpeg is a free, open-source multimedia framework used by this
  app for two purposes:

  ffprobe  reads video stream metadata — resolution, codec, duration,
           audio languages, and embedded subtitle tracks. This powers
           the Quality column, Lang OK? column, and subtitle summary.

  ffmpeg   extracts individual JPEG frames from a video at evenly
           spaced timestamps. This powers the "Extract Backdrop(s)"
           feature.

  Without FFmpeg:
  • Quality column shows "—"
  • Embedded subtitle tracks are not listed
  • The Extract Frames button is disabled

  How to install FFmpeg on Windows:
  1. Go to https://ffmpeg.org/download.html
  2. Under "Windows builds" click gyan.dev or BtbN
  3. Download ffmpeg-release-essentials.zip
  4. Extract to a permanent folder, e.g. C:\\Tools\\ffmpeg\\
  5. Inside the "bin" subfolder you'll find ffmpeg.exe + ffprobe.exe
  6. In Settings → Tools, enter the path to that "bin" folder
  7. Click "Test FFmpeg" — both should show green ✓

  The "FFprobe" checkbox in the main toolbar lets you disable FFprobe
  for a scan. This makes scanning very fast — useful when you only
  want to check images and metadata. Quality and lang detection only
  use XML/NFO data when FFprobe is off.

NOTEPAD++ TEXT EDITOR
  Notepad++ is auto-detected when you open Settings → Tools.
  It is launched with:
    notepad++.exe "C:\\path\\to\\file.nfo" -lxml
  The file path must come BEFORE -lxml. Placing -lxml before the
  path causes Notepad++ to interpret the path as a new filename and
  show a "Create new file?" dialog — this bug is fixed in v9.0.
  If Notepad++ is not available, the file opens in the OS default
  application (usually Notepad on Windows).

TMDB API — THE MOVIE DATABASE
  Used by: Ratings Sync (fetch rating + votes)
  Free API key — no payment, no subscription.
  How to get your key:
  1. Create a free account at https://www.themoviedb.org
  2. After login, go to Settings → API (left sidebar)
  3. Click "Request an API Key" → choose Developer
  4. Fill in the brief application form
  5. Your key (v3 auth) appears immediately on the same page
  6. Paste it into Settings → API Keys → TMDb API Key
  7. Click "Validate" to confirm it works

  Your key is stored only in settings.json on your own machine.
  It is transmitted only to api.themoviedb.org when you use
  Ratings Sync. It is never stored on any server or shared.

OMDB API — IMDB DATA VIA OMDB
  Used by: Ratings Sync (fetch IMDb rating + vote count)
  Free tier: 1,000 requests per day.
  How to get your key:
  1. Go to https://www.omdbapi.com/apikey.aspx
  2. Select "FREE" (1,000 daily requests)
  3. Enter your email address and submit
  4. Check your inbox and click the activation link
  5. Your key will be shown — paste it into Settings → API Keys
  6. Click "Validate" to confirm it works

  Same privacy guarantee as TMDb — key stored locally only, sent
  only to www.omdbapi.com during Ratings Sync.

COMPATIBLE MEDIA SCRAPERS
  The "Video Scraper" setting in Settings → Tools allows you to
  launch an external scraper application with the movie folder path
  passed as an argument. Compatible scrapers include:

  tinyMediaManager  https://www.tinymediamanager.org/
    Leading open-source scraper. Supports KODI NFO + Emby XML output.
    Command: tinyMediaManager.exe "C:\\Movies\\MovieName"

  Ember Media Manager  https://www.embermm.com/
    Windows-only, excellent artwork scraper for KODI libraries.

  MediaElch  https://www.kvibes.de/mediaelch/
    Cross-platform, supports KODI NFO format natively.

  Set the executable path in Settings → Tools → Scraper. The app
  passes the full movie folder path as the first argument.

OPENSUBTITLES
  Right-click → Open on OpenSubtitles.org builds a search URL
  from the movie title and year extracted from NFO or XML:
    https://www.opensubtitles.org/en/search2/sublanguageid-all/
    moviename-{title}/movieyear-{year}
  If no year is found, falls back to title-only search.
  Opens in your configured default browser.
"""

    ### NEW v0.10.0 — Keyboard shortcuts help tab ###
    _TAB_SHORTCUTS = """\
KEYBOARD SHORTCUTS  (v0.11.0)
NAVIGATION
  Page Up / Down  - move 20 rows at a time
  Home / End      - jump to first / last row
  Shift + Up/Down - extend multi-row selection

SCAN ACTIONS
  F5              - Scan (start or re-scan current folder)
  Ctrl+L          - Clear All scan results (with confirmation)

FILE ACTIONS
  Ctrl+O          - Open Folder of selected movie in Explorer
  Ctrl+E          - Open NFO in editor (or launch editor if none selected)

VALIDATION
  Ctrl+R          - Re-validate selected row without FFMPEG
                    Checks images, NFO, XML, genres - fast, no video analysis
                    FFprobe data (quality, subs, lang) is PRESERVED.
  Ctrl+Shift+R    - Re-validate selected row with FFMPEG
                    Full re-validation including video resolution and subtitles

APPLICATION
  F1              - Open this Help window (works globally, even in dialogs)
  Ctrl+H          - Open this Help window (main window only)
  Ctrl+S          - Open Settings dialog

DEVELOPER TOOLS
  Ctrl+I          - Refresh All Icons
                    Forces the UI to redraw all status icons in the table
                    Useful if emoji colors appear faded or incorrect

TIPS
  - F1 works from anywhere in the app, including inside dialogs
  - Ctrl+R is safe to use frequently - it skips video analysis
    and preserves your previous FFprobe results (quality, subs, lang)
  - Use Ctrl+Shift+R only when you need updated resolution or subtitle data
  - Ctrl+I is a developer/debugging tool; not needed in normal use

MENU BAR ORDER (v0.11.0)
  Settings  →  Tools  →  Help
  The Help menu is now last, consistent with standard application layout.
"""

    def _add_tab(self, nb, label, text):
        frame = tk.Frame(nb, bg="#1e1e2e"); nb.add(frame, text=label)
        t = tk.Text(frame, wrap="word", bg="#313244", fg="#cdd6f4",
                    font=("Helvetica",10), relief="flat", padx=14, pady=12,
                    spacing1=2, spacing3=2)
        sb = ttk.Scrollbar(frame, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        # Syntax-highlight section headers and bullet lines
        t.tag_configure("hdr",  foreground="#89b4fa", font=("Helvetica",10,"bold"))
        t.tag_configure("sep",  foreground="#45475a")
        t.tag_configure("key",  foreground="#f9e2af")
        t.tag_configure("ok",   foreground="#a6e3a1")
        t.tag_configure("body", foreground="#cdd6f4")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("━"):
                t.insert("end", line + "\n", "sep")
            elif stripped.startswith("─"):
                t.insert("end", line + "\n", "sep")
            elif stripped and stripped == stripped.upper() and len(stripped) > 4 and not stripped.startswith("•"):
                # ALL-CAPS section headers
                t.insert("end", line + "\n", "hdr")
            elif stripped.startswith("•"):
                t.insert("end", line + "\n", "ok")
            elif "→" in line or "—" in line[:30]:
                t.insert("end", line + "\n", "key")
            else:
                t.insert("end", line + "\n", "body")
        t.configure(state="disabled")

    def _add_about_tab(self, nb):
        frame = tk.Frame(nb, bg="#1e1e2e"); nb.add(frame, text="ℹ️  About")
        about = (
            f"  {APP_NAME}\n"
            f"  Version {APP_VERSION}\n\n"
            f"  Created by:  {APP_AUTHOR}\n"
            f"  Contact:     {APP_EMAIL}\n\n"
            "  ────────────────────────────────────────────────\n\n"
            "  Built to keep KODI media libraries clean,\n"
            "  complete, and metadata-perfect.\n\n"
            "  ────────────────────────────────────────────────\n\n"
            "  VERSION HISTORY\n\n"
            "  v0.11.0 - XML genre indentation fix (mirrors original tabs),\n"    ### NEW v0.11.0 ###
            "           Automatic silent backup of NFO/XML before any write,\n"
            "           FFprobe data persists across no-FFprobe re-validates,\n"
            "           Help menu moved to last (Settings / Tools / Help),\n"
            "           F1 global shortcut for Help,\n"
            "           VidSize column renamed to Video Size.\n\n"
            "  v0.10.5 - Sort: Genre (A-Z) and Genre (Z-A) added,\n"
            "           Fix: write_genres_to_nfo/xml preserves indentation,\n"
            "           Fix: classify_genres false-positive fix,\n"
            "           New: User Interface tab in Settings.\n\n"
            "  v0.10.4 - Larger status symbols, Re-validate (with FFMPEG),\n"
            "           NFO+XML columns unified.\n\n"
            "  v0.10.1 - Phase B architecture refactoring:\n"
            "           COLUMN_MODEL (centralized column definitions),\n"
            "           DBLCLICK_ACTIONS dispatch table,\n"
            "           SettingsDialog extracted to settings_dialog.py,\n"
            "           Series mode scanning placeholders.\n\n"
            "  v0.10.0 - Settings tab fix, Movie Name + Year columns,\n"
            "           Genre moved to 2nd column, Clear All button,\n"
            "           keyboard shortcuts, rotating log, Series tab stub,\n"
            "           Refresh Icons, richer status bar, alternating rows,\n"
            "           re-validate rename, Help shortcuts tab.\n\n"
            "  v0.9.0  - Ratings Sync (TMDb + OMDb), Genre column,\n"
            "           Normalize Genres, fallback XML parser,\n"
            "           Improvements report includes errors,\n"
            "           API Keys settings, Browser selection,\n"
            "           Image size settings, Tools auto-fill,\n"
            "           Backdrop count setting, Scraper clarified,\n"
            "           Sort auto-update, Notepad++ -lxml fix,\n"
            "           NFO/XML click behaviour, header tooltips,\n"
            "           ⬤/◐/○/✕ status symbols, OpenSubtitles integration,\n"
            "           Re-validate FFmpeg, Genres tab in Settings,\n"
            "           Help fully rewritten (this document).\n\n"
            "  v0.8.0 — Settings menu, Improvements engine,\n"
            "           IMDB/TMDb links, Copy Movie Name,\n"
            "           Auto-size columns, FFprobe checkbox,\n"
            "           Language column, phased scan,\n"
            "           Backdrop progress with ETA, Shift+select.\n\n"
            "  v0.7.0 — Quality column, PT OK?, persistent sessions,\n"
            "           FFmpeg validation, extraction improvements.\n\n"
            "  v0.6.x — Original release.\n\n"
            "  ────────────────────────────────────────────────\n\n"
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
        self._item_map      = {}
        self._results       = []   # movies scan results
        self._series_results = []  # Phase C placeholder: series scan results
        self._folder        = None
        self._scanning      = False
        self._cancel_scan   = False
        self._use_ffprobe = tk.BooleanVar(value=SETTINGS.get("use_ffprobe", True))
        self._build_ui()
        self._update_extract_btn_state()
        self.after(200, self._restore_last_session)

    # ── Build UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Menu bar                                               ### NEW v0.11.0 — order: Settings / Tools / Help ###
        menubar = tk.Menu(self, bg="#313244", fg="#cdd6f4",
                          activebackground="#585b70", activeforeground="#cdd6f4")
        self.configure(menu=menubar)
        settings_menu = tk.Menu(menubar, tearoff=0, bg="#313244", fg="#cdd6f4",
                                activebackground="#585b70", activeforeground="#cdd6f4")
        menubar.add_cascade(label="Settings", menu=settings_menu)
        ### NEW v0.10.0 — Settings menu with tab index fix ###
        settings_menu.add_command(label="⚙️  All Settings…",
                                  command=lambda: SettingsDialog(self, tab=0))
        settings_menu.add_separator()
        settings_menu.add_command(label="🔧  Tools (Editor / FFmpeg / Backdrop)",
                                  command=lambda: SettingsDialog(self, tab=0))
        settings_menu.add_command(label="🔑  API Keys (TMDb / OMDb)",
                                  command=lambda: SettingsDialog(self, tab=1))
        settings_menu.add_command(label="🌐  Browser Selection",
                                  command=lambda: SettingsDialog(self, tab=2))
        settings_menu.add_command(label="🌍  Language OK?",
                                  command=lambda: SettingsDialog(self, tab=3))
        settings_menu.add_command(label="🔍  Improvements",
                                  command=lambda: SettingsDialog(self, tab=4))
        settings_menu.add_command(label="🖼  Image Sizes",
                                  command=lambda: SettingsDialog(self, tab=5))
        settings_menu.add_command(label="🎬  Genres",
                                  command=lambda: SettingsDialog(self, tab=6))
        settings_menu.add_command(label="🏷  NFO-XML Tags",
                                  command=lambda: SettingsDialog(self, tab=7))

        tools_menu = tk.Menu(menubar, tearoff=0, bg="#313244", fg="#cdd6f4",
                             activebackground="#585b70", activeforeground="#cdd6f4")
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="🎬  Normalize Genres - All Movies",
                               command=self._normalize_genres_all)
        tools_menu.add_command(label="⭐  Sync Ratings - Selected Movies",
                               command=self._sync_ratings_selected)
        tools_menu.add_separator()
        tools_menu.add_command(label="🔁  Refresh All Icons (Developer)",
                               command=self._refresh_icons)

        ### NEW v0.11.0 — Help menu last; F1 opens help globally ###
        help_menu = tk.Menu(menubar, tearoff=0, bg="#313244", fg="#cdd6f4",
                            activebackground="#585b70", activeforeground="#cdd6f4")
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="📖  Help…  (F1)", command=lambda: HelpDialog(self))

        ### NEW v0.10.0 — Top-level tab notebook for Movies / Series / future ###
        self._main_nb = ttk.Notebook(self)
        self._main_nb.pack(fill="both", expand=True)
        # Movies tab — main content frame
        self._movies_tab = tk.Frame(self._main_nb, bg="#1e1e2e")
        self._main_nb.add(self._movies_tab, text="🎬  Movies")
        # Series tab — stub (Under Development)
        self._series_tab = tk.Frame(self._main_nb, bg="#1e1e2e")
        self._main_nb.add(self._series_tab, text="📺  Series")
        tk.Label(self._series_tab,
                 text="\n\n\n     Under Development 👍 - Waiting for the tokens to reset!\n\n"
                      "     This tab will support TV series libraries in a future release.\n\n"
                      "     For now, please use the Movies tab for all your media.",
                 font=("Helvetica", 14), bg="#1e1e2e", fg="#6c7086",
                 justify="left").pack(anchor="nw", padx=40, pady=40)
        # Alias self to movies tab for all pack() calls below
        ### NEW v0.10.0 — all UI packed into _movies_tab frame ###
        _mt = self._movies_tab  # shorthand for the Movies tab frame

        # ── Header row ────────────────────────────────────────────────────────
        header = tk.Frame(_mt, bg="#1e1e2e")
        header.pack(fill="x", padx=20, pady=(14,4))

        tk.Label(header, text=f"🎬  {APP_NAME}",
                 font=("Helvetica",17,"bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(side="left")

        right_hdr = tk.Frame(header, bg="#1e1e2e"); right_hdr.pack(side="right")
        self._ff_frame = tk.Frame(right_hdr, bg="#1e1e2e")
        self._ff_frame.pack(side="left")
        self._build_ffmpeg_status(self._ff_frame)

        # ── Picker row ────────────────────────────────────────────────────────
        picker = tk.Frame(_mt, bg="#1e1e2e"); picker.pack(fill="x", padx=20, pady=(0,6))
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
        ### NEW v0.10.0 — Extract Frames button replaced by Clear All ###
        # self.extract_btn — removed v0.10.0
        self.clear_btn = tk.Button(picker, text="  Clear All  ", bg="#fab387",
                                   fg="#1e1e2e", command=self._clear_all, **btn_kw)
        self.clear_btn.pack(side="left", padx=(6,0))
        tk.Button(picker, text="  Export CSV  ", bg="#cba6f7", fg="#1e1e2e",
                  command=self._export_csv, **btn_kw).pack(side="left", padx=(6,0))

        # FFprobe checkbox
        tk.Checkbutton(picker, text="FFprobe", variable=self._use_ffprobe,
                       command=self._on_ffprobe_toggle,
                       font=("Helvetica",9), bg="#1e1e2e", fg="#a6adc8",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left", padx=(10,0))

        # ── Sort row ──────────────────────────────────────────────────────────
        sr = tk.Frame(_mt, bg="#1e1e2e"); sr.pack(fill="x", padx=20, pady=(0,2))
        tk.Label(sr, text="Sort:", font=("Helvetica",10),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        self.sort_var = tk.StringVar(value=SETTINGS.get("sort_option","Movie Name (A-Z)"))
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
        self.progress_frame = tk.Frame(_mt, bg="#1e1e2e")
        self.progress_frame.pack(fill="x", padx=20, pady=(0,2))
        self.pbar_canvas = tk.Canvas(self.progress_frame, height=22,
                                     bg="#313244", highlightthickness=0)
        self.pbar_label  = tk.Label(self.progress_frame, text="",
                                    font=("Helvetica",9), bg="#1e1e2e", fg="#6c7086")

        # ── Stats / Status bar ─────────────────────────────────────────────────
        ### NEW v0.10.0 — Richer status bar ###
        self.stats_var = tk.StringVar(value="")
        sb_frame = tk.Frame(_mt, bg="#252535")
        sb_frame.pack(fill="x", padx=0, pady=0)
        self._sb_movies  = tk.Label(sb_frame, text="  Movies: 0", font=("Helvetica",9,"bold"),
                                    bg="#252535", fg="#a6e3a1", anchor="w")
        self._sb_movies.pack(side="left", padx=(8,0))
        self._sb_warn    = tk.Label(sb_frame, text="  Warnings: 0", font=("Helvetica",9),
                                    bg="#252535", fg="#f9e2af", anchor="w")
        self._sb_warn.pack(side="left", padx=(12,0))
        self._sb_errors  = tk.Label(sb_frame, text="  Errors: 0", font=("Helvetica",9),
                                    bg="#252535", fg="#f38ba8", anchor="w")
        self._sb_errors.pack(side="left", padx=(12,0))
        self._sb_action  = tk.Label(sb_frame, text="", font=("Helvetica",9,"italic"),
                                    bg="#252535", fg="#89b4fa", anchor="w")
        self._sb_action.pack(side="left", padx=(16,0))
        self._sb_sort    = tk.Label(sb_frame, text="", font=("Helvetica",9),
                                    bg="#252535", fg="#6c7086", anchor="e")
        self._sb_sort.pack(side="right", padx=(0,12))
        # Legacy stats label (hidden but kept for internal use)
        tk.Label(_mt, textvariable=self.stats_var,
                 font=("Helvetica",8), bg="#1e1e2e", fg="#45475a"
                 ).pack(anchor="w", padx=22)

        # ── Table ──────────────────────────────────────────────────────────────
        tf = tk.Frame(_mt, bg="#1e1e2e")
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

        # ── Build Treeview from COLUMN_MODEL (Phase B — single source of truth) ──
        iso = SETTINGS.get("lang_ok_code", "PT")
        _lang_ok_label = f"{iso} OK?"
        cols = tuple(c["id"] for c in COLUMN_MODEL)
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                 selectmode="extended")
        for col in COLUMN_MODEL:
            label = _lang_ok_label if col["label"] == "LANG_OK_LABEL" else col["label"]
            self.tree.heading(col["id"], text=label,
                              command=lambda c=col["id"]: self._on_header_dblclick_guard(c))
            self.tree.column(col["id"], width=col["width"], anchor=col["anchor"],
                             stretch=col["stretch"], minwidth=30)
        ### NEW v0.11.0 — hide/show image Size columns based on settings ###
        self._apply_image_size_col_visibility()

        ### NEW v0.10.0 — alternating rows toggled by settings ###
        _alt = SETTINGS.get("alternating_rows", True)
        _row_colors = {                                    ### NEW v0.12.0 — improved contrast ###
            "green":      "#1e3a2f", "green_odd":  "#2f5f4a" if _alt else "#1e3a2f",
            "yellow":     "#3a351e", "yellow_odd": "#6b5f2e" if _alt else "#3a351e",
            "red":        "#3a1e1e", "red_odd":    "#6b2e2e" if _alt else "#3a1e1e",
        }
        for t in ["green","green_odd","yellow","yellow_odd","red","red_odd"]:
            self.tree.tag_configure(t, background=_row_colors[t])

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
        # Restore self back to App instance
        ### NEW v0.10.0 — Keyboard shortcuts ###
        self.bind("<F5>",                   lambda e: self._scan())
        self.bind("<Control-l>",            lambda e: self._clear_all())
        self.bind("<Control-L>",            lambda e: self._clear_all())
        self.bind("<Control-e>",            lambda e: self._open_editor_shortcut())
        self.bind("<Control-E>",            lambda e: self._open_editor_shortcut())
        self.bind("<Control-s>",            lambda e: SettingsDialog(self, tab=0))
        self.bind("<Control-S>",            lambda e: SettingsDialog(self, tab=0))
        self.bind("<Control-o>",            lambda e: self._open_folder_shortcut())
        self.bind("<Control-O>",            lambda e: self._open_folder_shortcut())
        self.bind("<Control-r>",            lambda e: self._reval_selected_no_ffmpeg())
        self.bind("<Control-R>",            lambda e: self._reval_selected_no_ffmpeg())
        self.bind("<Control-Shift-r>",      lambda e: self._reval_selected_ffmpeg())
        self.bind("<Control-Shift-R>",      lambda e: self._reval_selected_ffmpeg())
        self.bind("<Control-i>",            lambda e: self._refresh_icons())
        self.bind("<Control-I>",            lambda e: self._refresh_icons())
        self.bind("<Control-h>",            lambda e: HelpDialog(self))
        self.bind("<Control-H>",            lambda e: HelpDialog(self))
        ### NEW v0.11.0 — F1 opens Help globally (works even when dialogs have focus) ###
        self.bind_all("<F1>",               lambda e: HelpDialog(self))

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

    def _update_extract_btn_state(self):  ### NEW v0.10.0 — extract btn removed; kept as no-op ###
        pass  # extract_btn removed in v0.10.0 (replaced by clear_btn)

    def _on_ffprobe_toggle(self):
        SETTINGS["use_ffprobe"] = self._use_ffprobe.get()
        _save_settings(SETTINGS)

    ### NEW v0.12.0 — image size columns removed; method kept as no-op for compat ###
    def _apply_image_size_col_visibility(self):
        """Image size columns were removed in v0.12.0. No-op kept for call-site compat."""
        pass

    # ── Settings changed callback ─────────────────────────────────────────────
    @staticmethod
    def _parse_dim_str(dim_str):
        """
        Parse a cached dim string like '1920×1080' → (1920, 1080).
        Returns (None, None) for None or unparseable strings.
        v0.11.1: used to avoid re-reading disk in _on_settings_changed.
        """                                                  ### NEW v0.11.1 ###
        if not dim_str:
            return None, None
        try:
            # dim strings may use '×' (U+00D7) or 'x' as separator
            for sep in ('×', 'x', 'X'):
                if sep in dim_str:
                    parts = dim_str.split(sep)
                    return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            pass
        return None, None

    def _on_settings_changed(self):
        """Called by SettingsDialog on save — refresh UI without blocking the main thread.
        v0.11.1 fix: image quality is recomputed from already-cached dimension strings
        (poster_dim / folder_dim / fanart_dim) instead of re-reading JPEG headers
        from disk. This eliminates the freeze on large libraries.  ### NEW v0.11.1 ###
        v0.12.0: also recomputes image status (proportion checks) from cache. ### NEW v0.12.0 ###
        """
        iso = SETTINGS.get("lang_ok_code", "PT")
        self.tree.heading("lang_ok", text=f"{iso} OK?")
        # Re-evaluate lang_ok for all results in memory (fast — no disk reads)
        for r in self._results:
            r["lang_ok"] = compute_lang_ok(
                r.get("video_path"), r.get("subs_internal", []),
                r.get("subs_external", []),
                r.get("nfo_path") if r.get("nfo_exists") else None,
                r.get("xml_path") if r.get("xml_exists") else None,
                iso_code=iso)
        # Recompute image quality tiers using CACHED dims — zero disk I/O ### NEW v0.11.1 ###
        for r in self._results:
            if r.get("poster_exists"):
                pw, ph = self._parse_dim_str(r.get("poster_dim"))
                r["poster_quality"] = classify_image_quality(pw, ph, "poster")
            if r.get("folder_exists"):
                flw, flh = self._parse_dim_str(r.get("folder_dim"))
                r["folder_quality"] = classify_image_quality(flw, flh, "folder")
            if r.get("fanart_exists"):
                fw, fh = self._parse_dim_str(r.get("fanart_dim"))
                r["fanart_quality"] = classify_image_quality(fw, fh, "fanart")
        self._apply_image_size_col_visibility()
        self._refresh_table()
        self._build_ffmpeg_status(self._ff_frame)
        self._update_extract_btn_state()
        self._update_status_bar(len(self._results), 0, 0, "Settings saved", self.sort_var.get())
    # ── Column header tooltips — derived from COLUMN_MODEL (Phase B) ──────────
    # Tips are no longer a class-level dict literal. They are derived from
    # COLUMN_MODEL so that adding a column in one place updates tips automatically.
    @property
    def _COL_HEADER_TIPS(self):
        """Return header tip dict built from COLUMN_MODEL at access time."""
        return {col["id"]: col["header_tip"] for col in COLUMN_MODEL}

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
                    if tip_text and cname != self._hdr_tip_col \
                            and SETTINGS.get("show_header_tips", True):  # v0.10.5
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

        ### NEW v0.10.0 — add tooltip for COL_MOVIE_NAME and COL_YEAR ###
        if ci == COL_MOVIE_NAME:
            name = d.get("movie_name", d["subfolder"])
            folder = d["subfolder_path"]
            return f"Movie: {name}\nFolder: {os.path.basename(folder)}\nDouble-click to open folder"
        if ci == COL_YEAR:
            return f"Year: {d.get('movie_year', '-')}\nSource: NFO <year> or XML <ProductionYear>"

        ### NEW v0.12.0 — Rating tooltip ###
        if ci == COL_RATING:
            rs = d.get("rating_str", "-")
            st = d.get("rating_status", STATUS_MISSING)
            rv = d.get("rating_value", -1.0)
            if st == STATUS_MISSING:
                return "Rating: not found\nSources checked: NFO <rating>, XML <IMDBrating>, XML <Rating>"
            if st == STATUS_ERROR:
                return "Rating: parsing error — tag exists but value is non-numeric or malformed"
            if st == STATUS_WARN:
                return (f"Rating: {rs}  (conflict — multiple sources differ)\n"
                        "Sources: NFO <rating>, XML <IMDBrating>, XML <Rating>")
            return f"Rating: {rs}\nSource: NFO <rating> / XML <IMDBrating> / XML <Rating>"

        # Poster column (merged — v0.12.0)
        if ci == COL_POSTER:
            if not d["poster_exists"]:
                return f"poster.jpg\n[MISSING]\nExpected: {d['poster_path']}"
            lines = ["poster.jpg", f"Size: {d['poster_size']}"]
            if d.get("poster_dim"): lines.append(f"Dimensions: {d['poster_dim']}")
            w, h = get_image_wh(d["poster_path"])
            if w and h:
                ratio = w / h
                accept_34 = SETTINGS.get("poster_accept_34", False)
                if accept_34:
                    ok_str = "OK" if (0.60 <= ratio <= 0.72 or 0.70 <= ratio <= 0.80) else "! Not 2:3 or 3:4"
                    lines.append("Proportions: 2:3 or 3:4")
                else:
                    ok_str = "OK" if 0.60 <= ratio <= 0.72 else "! Not 2:3 portrait"
                    lines.append("Proportions: 2:3 portrait")
                lines.append(f"Ratio: {ratio:.2f}  {ok_str}")
            ql = d.get("poster_quality", "—")
            if ql != "—": lines.append(f"Quality: {ql}")
            if d.get("poster_desc"): lines.append(f"[!] {d['poster_desc']}")
            return "\n".join(lines)

        # Folder column (merged — v0.12.0)
        if ci == COL_FOLDER:
            if not d["folder_exists"]:
                return f"folder.jpg\n[MISSING]\nExpected: {d['folder_path']}"
            lines = ["folder.jpg", f"Size: {d['folder_size']}"]
            if d.get("folder_dim"): lines.append(f"Dimensions: {d['folder_dim']}")
            w, h = get_image_wh(d["folder_path"])
            if w and h:
                ratio = w / h
                accept_34 = SETTINGS.get("poster_accept_34", False)
                if accept_34:
                    ok_str = "OK" if (0.60 <= ratio <= 0.72 or 0.70 <= ratio <= 0.80) else "! Not 2:3 or 3:4"
                    lines.append("Proportions: 2:3 or 3:4")
                else:
                    ok_str = "OK" if 0.60 <= ratio <= 0.72 else "! Not 2:3 portrait"
                    lines.append("Proportions: 2:3 portrait")
                lines.append(f"Ratio: {ratio:.2f}  {ok_str}")
            ql = d.get("folder_quality", "—")
            if ql != "—": lines.append(f"Quality: {ql}")
            if d.get("folder_desc"): lines.append(f"[!] {d['folder_desc']}")
            return "\n".join(lines)

        # Fanart column (merged — v0.12.0)
        accept_168 = SETTINGS.get("fanart_accept_168", False)
        if ci == COL_FANART:
            if not d["fanart_exists"]:
                return f"fanart.jpg\n[MISSING]\nExpected: {d['fanart_path']}"
            lines = ["fanart.jpg", f"Size: {d['fanart_size']}"]
            if d.get("fanart_dim"): lines.append(f"Dimensions: {d['fanart_dim']}")
            w, h = get_image_wh(d["fanart_path"])
            if w and h:
                ratio = w / h
                if accept_168:
                    ok_ratio = (1.70 <= ratio <= 1.85) or (1.45 <= ratio <= 1.55)
                    prop_str = "16:9 (≈1.78) or 16:8 (≈1.50)"
                else:
                    ok_ratio = (1.70 <= ratio <= 1.85)
                    prop_str = "16:9 (≈1.78)"
                ok = "OK" if ok_ratio else f"! Not {prop_str}"
                lines.append(f"Proportions: {prop_str}")
                lines.append(f"Ratio: {ratio:.2f}  {ok}")
            ql = d.get("fanart_quality", "—")
            if ql != "—": lines.append(f"Quality: {ql}")
            if d.get("fanart_desc"): lines.append(f"[!] {d['fanart_desc']}")
            return "\n".join(lines)

        # Backdrops
        if ci == COL_BACKDROPS:
            bc = d["backdrop_count"]
            if bc == 0:
                return "Backdrops: none found\nRight-click - Extract Backdrop(s) to generate"
            paths_preview = "\n".join(f"  {os.path.basename(p)}" for p in d["backdrop_paths"][:5])
            more = f"\n  … and {bc-5} more" if bc > 5 else ""
            return f"Backdrops: {bc} file(s)\n{paths_preview}{more}"

        # NFO unified (v0.10.4)
        if ci == COL_NFO:
            if not d["nfo_exists"]:
                return f".nfo file\n[MISSING]\nExpected: {os.path.basename(d['nfo_path'])}\nDouble-click for details"
            lines = [f"{os.path.basename(d['nfo_path'])}", f"Size: {d['nfo_size']}"]
            if d["nfo_errors"]:
                lines.append(f"[!] {len(d['nfo_errors'])} parse error(s) found")
                errs = d["nfo_errors"][:3]
                for e in errs:
                    lines.append(f"  Line {e['line']}: {e['message']}")
                if len(d["nfo_errors"]) > 3:
                    lines.append(f"  ... {len(d['nfo_errors'])-3} more")
                lines.append("Double-click to see full error list and open file")
            else:
                lines.append("XML valid")
                lines.append("Double-click to open in editor")
            return "\n".join(lines)

        # XML unified (v0.10.4)
        if ci == COL_XML:
            if not d["xml_exists"]:
                return "movie.xml\n[MISSING]\nDouble-click for details"
            lines = ["movie.xml", f"Size: {d['xml_size']}"]
            if d["xml_errors"]:
                lines.append(f"[!] {len(d['xml_errors'])} parse error(s) found")
                errs = d["xml_errors"][:3]
                for e in errs:
                    lines.append(f"  Line {e['line']}: {e['message']}")
                if len(d["xml_errors"]) > 3:
                    lines.append(f"  ... {len(d['xml_errors'])-3} more")
                lines.append("Double-click to see full error list and open file")
            else:
                lines.append("XML valid")
                lines.append("Double-click to open in editor")
            return "\n".join(lines)

        # Video / Quality / Size
        if ci == COL_VID_EXT:
            if not d.get("video_path"):
                return "No video file found in this folder"
            vfiles = d.get("video_files", [])
            lines = [f"Video: {d['video_ext']}  ({d['video_size']})"]
            if len(vfiles) > 1:
                lines.append(f"[!] {len(vfiles)} video files found (expected 1):")
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
                return f"[Y] {lang_name} audio or subtitle found"
            if v == "N":
                return (f"[N] No {lang_name} audio or subtitle found\n"
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
                canonical = _GENRE_SYNONYMS.get(g.lower())
                in_valid = (g in valid or g.title() in valid or
                            n in valid or n.lower() in {v.lower() for v in valid})
                if canonical and canonical != g:
                    lines.append(f"  {g}  → needs normalizing")
                elif not in_valid:
                    lines.append(f"  {g}  (custom — not in Settings list)")
                else:
                    lines.append(f"  {g}  OK")
            return "\n".join(lines)

        return None

    # ══════════════════════════════════════════════════════════════════════════
    # DBLCLICK_ACTIONS — dispatch table (Phase B)
    # ══════════════════════════════════════════════════════════════════════════
    #
    # Maps the string action tag from COLUMN_MODEL["dblclick"] to a handler
    # callable. Each handler receives (self, d) where d is the row data dict.
    #
    # This table is the single place to define what happens on double-click.
    # _dblclick() reads col["dblclick"] from COLUMN_MODEL and dispatches here.
    #
    # Action tags defined here must match tags used in COLUMN_MODEL entries.
    #
    # SERIES MODE PLACEHOLDER (Phase C):
    #   A separate SERIES_DBLCLICK_ACTIONS dict will be added for Phase C.
    #   It will handle episode-specific actions: open episode NFO, play episode,
    #   open season folder, etc.
    #   TODO (Phase C): define SERIES_DBLCLICK_ACTIONS = {...}
    #
    @staticmethod
    def _get_dblclick_actions():
        """
        Return the dispatch table for double-click actions.
        Keys are action tag strings from COLUMN_MODEL["dblclick"].
        Values are callables: fn(app_instance, row_data_dict) -> None.
        """
        def _open_folder(app, d):
            os_open(d["subfolder_path"])

        def _open_image_poster(app, d):
            if d["poster_exists"]: os_open(d["poster_path"])
            else: messagebox.showinfo("Missing", "poster.jpg not found.")

        def _open_image_folder(app, d):
            if d["folder_exists"]: os_open(d["folder_path"])
            else: messagebox.showinfo("Missing", "folder.jpg not found.")

        def _open_image_fanart(app, d):
            if d["fanart_exists"]: os_open(d["fanart_path"])
            else: messagebox.showinfo("Missing", "fanart.jpg not found.")

        def _open_backdrop(app, d):
            if d["backdrop_count"] > 0: os_open(d["backdrop_paths"][0])
            else: messagebox.showinfo("Missing", "No backdrops.")

        def _open_nfo(app, d):
            if not d["nfo_exists"]:
                messagebox.showinfo("Missing", f"Expected: {os.path.basename(d['nfo_path'])}")
            else:
                open_in_editor(d["nfo_path"])

        def _open_nfo_or_errors(app, d):
            if not d["nfo_exists"]:
                messagebox.showinfo("Missing", f"Expected: {os.path.basename(d['nfo_path'])}")
            elif d["nfo_errors"]:
                ErrorDialog(app, f"NFO Errors - {d.get('movie_name', d['subfolder'])}",
                            d["nfo_path"], d["nfo_errors"])
            else:
                open_in_editor(d["nfo_path"])

        # v0.10.4 — unified: show errors first with Open button, else open editor
        def _open_nfo_unified(app, d):
            if not d["nfo_exists"]:
                messagebox.showinfo("Missing", f"Expected: {os.path.basename(d['nfo_path'])}")
            elif d["nfo_errors"]:
                ErrorDialog(app, f"NFO Errors - {d.get('movie_name', d['subfolder'])}",
                            d["nfo_path"], d["nfo_errors"])
            else:
                open_in_editor(d["nfo_path"])

        def _open_xml(app, d):
            if not d["xml_exists"]: messagebox.showinfo("Missing", "movie.xml not found.")
            else: open_in_editor(d["xml_path"])

        def _open_xml_or_errors(app, d):
            if not d["xml_exists"]: messagebox.showinfo("Missing", "movie.xml not found.")
            elif d["xml_errors"]:
                ErrorDialog(app, f"XML Errors - {d.get('movie_name', d['subfolder'])}",
                            d["xml_path"], d["xml_errors"])
            else:
                open_in_editor(d["xml_path"])

        # v0.10.4 — unified: show errors first with Open button, else open editor
        def _open_xml_unified(app, d):
            if not d["xml_exists"]: messagebox.showinfo("Missing", "movie.xml not found.")
            elif d["xml_errors"]:
                ErrorDialog(app, f"XML Errors - {d.get('movie_name', d['subfolder'])}",
                            d["xml_path"], d["xml_errors"])
            else:
                open_in_editor(d["xml_path"])

        def _open_xml_lang(app, d):
            if d["xml_exists"]: open_in_editor(d["xml_path"])

        def _play_video(app, d):
            if d.get("video_path"): os_open(d["video_path"])
            else: messagebox.showinfo("Missing", "No video.")

        def _show_subtitles(app, d):
            SubtitleDialog(app, d["subfolder"], d)

        def _open_nfo_genre(app, d):
            if d.get("nfo_exists"): open_in_editor(d["nfo_path"])

        def _none(app, d):
            pass  # no action for this column

        return {
            "open_folder":        _open_folder,
            "open_image_poster":  _open_image_poster,
            "open_image_folder":  _open_image_folder,
            "open_image_fanart":  _open_image_fanart,
            "open_backdrop":      _open_backdrop,
            "open_nfo":           _open_nfo,
            "open_nfo_or_errors": _open_nfo_or_errors,
            "open_nfo_unified":   _open_nfo_unified,   # v0.10.4
            "open_xml":           _open_xml,
            "open_xml_or_errors": _open_xml_or_errors,
            "open_xml_unified":   _open_xml_unified,   # v0.10.4
            "open_xml_lang":      _open_xml_lang,
            "play_video":         _play_video,
            "show_subtitles":     _show_subtitles,
            "open_nfo_genre":     _open_nfo_genre,
            "none":               _none,
            # Phase C TODO: add series-specific action tags here
        }

    # ── Double-click (Phase B — dispatches via DBLCLICK_ACTIONS) ─────────────
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
        ci  = int(cid.lstrip("#")) - 1
        d   = self._item_map.get(iid)
        if not d: return
        # Dispatch via COLUMN_MODEL + DBLCLICK_ACTIONS table (Phase B)
        if 0 <= ci < len(COLUMN_MODEL):
            tag     = COLUMN_MODEL[ci]["dblclick"]
            actions = self._get_dblclick_actions()
            handler = actions.get(tag, actions["none"])
            handler(self, d)

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
            ### NEW v0.10.0 — Open Folder (item 20) ###
            m.add_command(label="📂  Open Folder",
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
                    m.add_command(label="🎞  Extract Backdrop(s)",  ### NEW v0.10.0 fixed alignment ###
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
                    m.add_command(label=f"[!] NFO errors ({len(d['nfo_errors'])})",
                                  command=lambda dd=d: ErrorDialog(
                                      self, f"NFO - {dd.get('movie_name', dd['subfolder'])}", dd["nfo_path"], dd["nfo_errors"]))
            if d["xml_exists"]:
                m.add_command(label="📝  Open movie.xml",
                              command=lambda: open_in_editor(d["xml_path"]))
                if d["xml_errors"]:
                    m.add_command(label=f"[!] XML errors ({len(d['xml_errors'])})",
                                  command=lambda dd=d: ErrorDialog(
                                      self, f"XML - {dd.get('movie_name', dd['subfolder'])}", dd["xml_path"], dd["xml_errors"]))
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

        ### NEW v0.12.0 — Add Custom Genre(s) option ###
        custom_genres = self._collect_custom_genres(sel_data)
        if custom_genres:
            m.add_command(label=f"➕  Add Custom Genre(s) to Settings ({len(custom_genres)})",
                          command=lambda cg=custom_genres, dd=sel_data:
                              self._add_custom_genres(cg, dd))

        if multi:
            ff_ok, _, _, _ = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
            if ff_ok:
                m.add_command(label=f"🎞  Extract Backdrop(s) ({len(sel_data)} movies)",
                              command=lambda dd=sel_data: self._extract_multi(dd))
        # v0.10.4 — validation group: separator above + below, always visible
        m.add_separator()
        # Re-validate (no FFprobe) — works for single or multi  ### NEW v0.12.0 — renamed ###
        if multi:
            m.add_command(label=f"🔄  Re-validate (no FFprobe) ({len(sel_data)} movies)",
                          command=lambda dd=sel_data, ii=list(self.tree.selection()):
                              self._reval_multi_no_ffmpeg(ii, dd))
        else:
            m.add_command(label="🔄  Re-validate (no FFprobe)",
                          command=lambda: self._reval_no_ffmpeg(iid, d))
        # Re-validate (with FFprobe) — ALWAYS visible and enabled ### NEW v0.12.0 ###
        if multi:
            m.add_command(label=f"🔬  Re-validate (with FFprobe) ({len(sel_data)} movies)",
                          command=lambda dd=sel_data, ii=list(self.tree.selection()):
                              self._reval_multi_ffmpeg(ii, dd))
        else:
            m.add_command(label="🔬  Re-validate (with FFprobe)",
                          command=lambda: self._reval_ffmpeg(iid, d))
        # Refresh Icons
        m.add_command(label="🔁  Refresh Icons",
                      command=lambda: self._refresh_icons())
        m.add_separator()
        m.tk_popup(e.x_root, e.y_root)

    def _copy_movie_name(self, d):
        logger.info(f"Copy movie name: {d.get('movie_name', d['subfolder'])}")
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
                error_rows.append((d.get("movie_name", d["subfolder"]), errs))
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

    # v0.10.4 — batch re-validate (no FFMPEG) for multi-selection
    def _reval_multi_no_ffmpeg(self, iids, data_list):
        """Re-validate multiple selected rows without FFMPEG.
        v0.11.0: FFprobe data is preserved per-row.       ### NEW v0.11.0 ###
        """
        for iid, data in zip(iids, data_list):
            self._reval_no_ffmpeg(iid, data)
        self._update_stats()
        logger.info(f"Batch re-validate (no FFMPEG): {len(data_list)} movies")

    ### NEW v0.10.0 — _reval_no_ffmpeg: re-validate without FFMPEG ###
    def _reval_no_ffmpeg(self, iid, data):
        """Re-validate all columns that do not require FFMPEG.
        v0.11.0: FFprobe fields (video_width, video_height, video_quality,
        subs_internal, subs_external, subs_summary, lang_ok) are preserved
        from the previous scan — they are NOT cleared.        ### NEW v0.11.0 ###
        """
        sp, sn = data["subfolder_path"], data["subfolder"]
        if not os.path.isdir(sp): messagebox.showerror("Error","Folder gone."); return
        # Save the existing FFprobe-derived fields before re-scanning
        _ffprobe_fields = {                                 ### NEW v0.11.0 ###
            "video_width":    data.get("video_width"),
            "video_height":   data.get("video_height"),
            "video_quality":  data.get("video_quality", "—"),
            "subs_internal":  data.get("subs_internal", []),
            "subs_external":  data.get("subs_external", []),
            "subs_summary":   data.get("subs_summary", ""),
            "lang_ok":        data.get("lang_ok", "—"),
        }
        # Save ffprobe setting, temporarily disable it
        orig = SETTINGS.get("use_ffprobe", True)
        SETTINGS["use_ffprobe"] = False
        try:
            r = scan_one_subfolder(sp, sn)
        finally:
            SETTINGS["use_ffprobe"] = orig
        # Restore FFprobe-derived data so it is not lost ### NEW v0.11.0 ###
        r.update(_ffprobe_fields)
        r["row_health"] = _compute_health(r)
        self._item_map[iid] = r
        for i, o in enumerate(self._results):
            if o["subfolder_path"] == sp: self._results[i] = r; break
        tag = r["row_health"] + ("_odd" if self.tree.index(iid) % 2 else "")
        self.tree.item(iid, values=self._rv(r), tags=(tag,))
        self._update_stats()
        logger.info(f"Re-validated (no FFMPEG): {sn}")
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
        logger.info(f"Re-validated: {sn}")
    ### NEW v0.10.0 — Refresh Icons developer tool ###
    def _refresh_icons(self):
        """Force redraw of all emoji icons in the table."""
        for iid in self.tree.get_children():
            d = self._item_map.get(iid)
            if d:
                tag = d["row_health"] + ("_odd" if self.tree.index(iid) % 2 else "")
                self.tree.item(iid, values=self._rv(d), tags=(tag,))
        logger.info("Icons refreshed")
    def _reval_ffmpeg(self, iid, data):
        """Re-validate (with FFprobe) — full column revalidation, always runs FFprobe.
        ### NEW v0.12.0 — full revalidation (all columns), force_ffprobe=True,
                          does NOT depend on global use_ffprobe setting. ###
        """
        sp, sn = data["subfolder_path"], data["subfolder"]
        if not os.path.isdir(sp):
            messagebox.showerror("Error", "Folder gone."); return

        def _worker():
            try:
                r = scan_one_subfolder(sp, sn, force_ffprobe=True)
                def _apply():
                    self._item_map[iid] = r
                    for i, o in enumerate(self._results):
                        if o["subfolder_path"] == sp:
                            self._results[i] = r; break
                    tag = r["row_health"] + ("_odd" if self.tree.index(iid) % 2 else "")
                    self.tree.item(iid, values=self._rv(r), tags=(tag,))
                    self._update_stats()
                    name_disp = r.get("movie_name", r.get("subfolder", "?"))
                    messagebox.showinfo("Re-validate Done",
                                        f"{name_disp}\n"
                                        f"Quality: {r.get('video_quality','—')}  "
                                        f"Lang OK: {r.get('lang_ok','—')}")
                    logger.info(f"Re-validated (with FFprobe): {sn}")
                self.after(0, _apply)
            except Exception as e:
                logger.error(f"Re-validate (with FFprobe) error for {sn}: {e}")
                self.after(0, lambda: messagebox.showerror("Error",
                    f"Re-validation failed for {sn}:\n{e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _reval_multi_ffmpeg(self, iids, data_list):
        """Re-validate multiple rows with FFprobe — full revalidation. ### NEW v0.12.0 ###"""
        def _worker():
            done = 0
            for iid, data in zip(iids, data_list):
                sp, sn = data["subfolder_path"], data["subfolder"]
                if not os.path.isdir(sp):
                    continue
                try:
                    r = scan_one_subfolder(sp, sn, force_ffprobe=True)
                    def _apply(i=iid, d=r):
                        self._item_map[i] = d
                        for idx, o in enumerate(self._results):
                            if o["subfolder_path"] == d["subfolder_path"]:
                                self._results[idx] = d; break
                        tag = d["row_health"] + ("_odd" if self.tree.index(i) % 2 else "")
                        self.tree.item(i, values=self._rv(d), tags=(tag,))
                    self.after(0, _apply)
                    done += 1
                except Exception as e:
                    logger.error(f"FFprobe batch error for {sn}: {e}")
            def _finish(n=done):
                self._update_stats()
                messagebox.showinfo("FFprobe Done",
                                    f"Re-validated {n}/{len(data_list)} movie(s) with FFprobe.")
                logger.info(f"Batch re-validate (with FFprobe): {n}/{len(data_list)} done")
            self.after(0, _finish)
        threading.Thread(target=_worker, daemon=True).start()

    ### NEW v0.12.0 — Custom genre helpers ###
    def _collect_custom_genres(self, data_list):
        """Return sorted list of unique custom genres across all selected rows."""
        valid = _get_valid_genres()
        custom = set()
        for d in data_list:
            for g in d.get("genres", []):
                lower = g.lower()
                canonical = _GENRE_SYNONYMS.get(lower)
                if canonical:
                    continue  # synonym — normalizable, not truly custom
                normalized = normalize_genre(g)
                in_valid = (g in valid or
                            g.title() in valid or
                            normalized in valid or
                            normalized.lower() in {v.lower() for v in valid})
                if not in_valid:
                    custom.add(g)
        return sorted(custom)

    def _add_custom_genres(self, custom_genres, data_list):
        """Add custom genres to the settings genre list and refresh affected rows."""
        existing = SETTINGS.get("genre_list", _DEFAULT_SETTINGS["genre_list"])
        existing_set = {g.strip() for g in existing.splitlines() if g.strip()}
        new_genres = [g for g in custom_genres if g not in existing_set]
        if not new_genres:
            messagebox.showinfo("Add Custom Genres", "All custom genres are already in the list.")
            return
        updated = existing.rstrip() + "\n" + "\n".join(new_genres)
        SETTINGS["genre_list"] = "\n".join(g.strip() for g in updated.splitlines() if g.strip())
        _save_settings(SETTINGS)
        logger.info(f"Added custom genres to settings: {', '.join(new_genres)}")
        # Re-classify only the affected rows
        for iid, d in list(self._item_map.items()):
            if d not in data_list:
                continue
            genres = d.get("genres", [])
            gd, gs = classify_genres(genres)
            d["genre_display"] = gd
            d["genre_status"]  = gs
            tag = d["row_health"] + ("_odd" if self.tree.index(iid) % 2 else "")
            self.tree.item(iid, values=self._rv(d), tags=(tag,))
        messagebox.showinfo("Add Custom Genres",
                            f"Added {len(new_genres)} genre(s) to Settings:\n"
                            + ", ".join(new_genres))

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
        logger.info("Normalize genres: all movies requested")
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
        backup_ref = [None]   ### NEW v0.11.0 — shared batch backup folder ###
        for d in data_list:
            nfo_path = d.get("nfo_path") if d.get("nfo_exists") else None
            xml_path = d.get("xml_path") if d.get("xml_exists") else None
            genres = get_genres_from_nfo(nfo_path)
            if not genres:
                continue
            normalized, did_change = normalize_genre_list(genres)
            if not did_change:
                continue
            ### NEW v0.11.0 — backup before writing ###
            movie_name = d.get("movie_name", d.get("subfolder", "unknown"))
            _make_batch_backup(movie_name, backup_ref, nfo_path, xml_path)
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

    ### NEW v0.10.0 — Clear All button handler ###
    def _clear_all(self):
        """Clear all scan results from the table (Ctrl+L)."""
        if self._scanning: return
        if not self._results:
            messagebox.showinfo("Clear All", "Nothing to clear."); return
        if not messagebox.askyesno("Clear All",
                "Are you sure you want to clear the scan results?",
                icon="warning"):
            return
        self._results = []; self._item_map.clear()
        for r in self.tree.get_children(): self.tree.delete(r)
        self._update_status_bar(0, 0, 0, "Cleared", self.sort_var.get())
        logger.info("User cleared scan results")
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
    ### NEW v0.10.0 — keyboard shortcut helpers ###
    def _open_editor_shortcut(self):
        """Ctrl+E — open NFO of selected row in editor, or Notepad."""
        sel = self.tree.selection()
        if sel:
            d = self._item_map.get(sel[0])
            if d and d.get("nfo_exists"):
                open_in_editor(d["nfo_path"]); return
        # fallback: open notepad++/notepad
        editor = SETTINGS.get("text_editor","").strip()
        npp    = _find_notepadpp()
        target = editor if (editor and os.path.isfile(editor)) else (npp or "")
        if target:
            try:
                subprocess.Popen([target],
                                 creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            except Exception: pass
        else:
            try: subprocess.Popen(["notepad.exe"])
            except Exception: pass

    def _open_folder_shortcut(self):
        """Ctrl+O — open folder of selected row."""
        sel = self.tree.selection()
        if not sel: return
        d = self._item_map.get(sel[0])
        if d: os_open(d["subfolder_path"])

    def _reval_selected_no_ffmpeg(self):
        """Ctrl+R — re-validate selected row without FFMPEG."""
        sel = self.tree.selection()
        if not sel: return
        iid = sel[0]; d = self._item_map.get(iid)
        if d: self._reval_no_ffmpeg(iid, d)

    def _reval_selected_ffmpeg(self):
        """Ctrl+Shift+R — re-validate selected row with FFMPEG."""
        sel = self.tree.selection()
        if not sel: return
        iid = sel[0]; d = self._item_map.get(iid)
        if d: self._reval_ffmpeg(iid, d)

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

    ### NEW v0.11.1 — scan variants used by SettingsDialog._offer_rescan ###
    def _update_scan_no_ff(self):
        """Update scan without FFprobe — called after settings change.
        Preserves existing FFprobe data (video quality, subs, lang).
        """
        if self._scanning: return
        folder = self._folder or SETTINGS.get("last_folder", "")
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No folder", "No folder to update. Browse first."); return
        self._folder = folder; self.folder_var.set(folder)
        orig = SETTINGS.get("use_ffprobe", True)
        SETTINGS["use_ffprobe"] = False
        try:
            self._start_scan(folder)
        finally:
            SETTINGS["use_ffprobe"] = orig

    def _update_scan_with_ff(self):
        """Update scan with FFprobe — called after settings change.
        Refreshes all data including video resolution, audio streams, subs.
        """
        if self._scanning: return
        folder = self._folder or SETTINGS.get("last_folder", "")
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No folder", "No folder to update. Browse first."); return
        self._folder = folder; self.folder_var.set(folder)
        orig = SETTINGS.get("use_ffprobe", True)
        SETTINGS["use_ffprobe"] = True
        try:
            self._start_scan(folder)
        finally:
            SETTINGS["use_ffprobe"] = orig

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
        logger.info(f"Scan started: {folder}")
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
            ### NEW v0.11.0 — build lookup of existing FFprobe data by path ###
            _prior_ffprobe = {}
            for rd in self._results:
                sp = rd.get("subfolder_path")
                if sp and (rd.get("video_width") or rd.get("video_quality","—") != "—"):
                    _prior_ffprobe[sp] = {
                        "video_width":   rd.get("video_width"),
                        "video_height":  rd.get("video_height"),
                        "video_quality": rd.get("video_quality", "—"),
                        "subs_internal": rd.get("subs_internal", []),
                        "subs_external": rd.get("subs_external", []),
                        "subs_summary":  rd.get("subs_summary", ""),
                        "lang_ok":       rd.get("lang_ok", "—"),
                    }

            # ── Phase 1: list subfolders ──────────────────────────────────────
            self.after(0, lambda: self._draw_scan_progress(0, "Phase 1/4 — Listing subfolders…"))
            stubs = []
            for entry in entries:
                ### NEW v0.11.0 — seed stub with prior FFprobe data if available ###
                prior = _prior_ffprobe.get(entry.path, {})
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
                    "video_width":prior.get("video_width"),                         ### NEW v0.11.0 ###
                    "video_height":prior.get("video_height"),                       ### NEW v0.11.0 ###
                    "video_quality":prior.get("video_quality","—"),                 ### NEW v0.11.0 ###
                    "video_status":STATUS_MISSING,
                    "subs_internal":prior.get("subs_internal",[]),                  ### NEW v0.11.0 ###
                    "subs_external":prior.get("subs_external",[]),                  ### NEW v0.11.0 ###
                    "subs_summary":prior.get("subs_summary","—"),                   ### NEW v0.11.0 ###
                    "lang_ok":prior.get("lang_ok","—"),                             ### NEW v0.11.0 ###
                    "genres":[],"genre_display":"—","genre_status":STATUS_ERROR,
                    "movie_name": entry.name, "movie_year": "-",
                    "row_health":"yellow",
                    # v0.11.0 — image quality tiers (filled in Phase 2) ### NEW v0.11.0 ###
                    "poster_quality":"—","folder_quality":"—","fanart_quality":"—",
                    # v0.12.0 — rating (filled in Phase 3)               ### NEW v0.12.0 ###
                    "rating_str":"-","rating_status":STATUS_MISSING,"rating_value":-1.0,
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
                        ### NEW v0.11.0 — compute quality tier ###
                        iw, ih = get_image_wh(p_img)
                        row[f"{key}_quality"] = classify_image_quality(iw, ih, itype)
                    else:
                        row[f"{key}_status"]  = STATUS_MISSING
                        row[f"{key}_quality"] = "—"   ### NEW v0.11.0 ###

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
                # Rating extraction (v0.12.0)                ### NEW v0.12.0 ###
                nfo_p_r = nfo_path if ne else None
                xml_p_r = xml_path if xe else None
                rs, rst, rv = extract_rating_from_files(nfo_p_r, xml_p_r)
                row["rating_str"]    = rs
                row["rating_status"] = rst
                row["rating_value"]  = rv
                ### NEW v0.10.0 — extract movie name and year after metadata phase ###
                nfo_p2 = nfo_path if ne else None
                xml_p2 = xml_path if xe else None
                row["movie_name"] = get_movie_name_from_files(nfo_p2, xml_p2, sn)
                row["movie_year"] = get_movie_year_display(nfo_p2, xml_p2)
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
                else:
                    ### NEW v0.11.0 — preserve existing FFprobe data when not re-running ###
                    # If a prior scan stored FFprobe results, keep them.
                    vi["video_width"]   = row.get("video_width")
                    vi["video_height"]  = row.get("video_height")
                    vi["video_quality"] = row.get("video_quality", "—")
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
        ### NEW v0.10.0 — update status bar on scan complete ###
        try:
            _warn = sum(1 for r in results if r["row_health"] == "yellow")
            _err  = sum(1 for r in results if r["row_health"] == "red")
            self._update_status_bar(len(results), _warn, _err,
                                    "Scan complete", self.sort_var.get())
            logger.info(f"Scan complete: {len(results)} movies, {_warn} warnings, {_err} errors")
        except Exception: pass

    # ── Series mode scan hook (Phase C placeholder) ────────────────────────
    def _start_scan_series(self):
        """
        Phase C placeholder — start a series library scan.
        Will be called when the user clicks Scan inside the Series tab.
        TODO (Phase C): implement full series scanning pipeline analogous
        to _start_scan(), using scan_one_series() as the worker function.
        The results will populate self._series_results and a separate
        series Treeview widget inside self._series_tab.
        """
        # TODO (Phase C): implement
        messagebox.showinfo("Series Scan",
                            "Series scanning is not yet implemented.\n"
                            "This feature is coming in Phase C!")

    def _restore_last_session(self):
        last_folder  = SETTINGS.get("last_folder","")
        last_results = SETTINGS.get("last_results",[])
        if not last_folder or not last_results: return
        if not os.path.isdir(last_folder): return
        self._folder = last_folder
        self.folder_var.set(last_folder)
        self._results = _results_from_json(last_results)
        self._update_stats(); self._refresh_table()
        # Run backup cleanup in background at startup  ### NEW v0.12.0 ###
        threading.Thread(target=clean_backup_folder_if_needed, daemon=True).start()

    ### NEW v0.10.0 — Richer status bar update ###
    def _update_status_bar(self, total, warnings, errors, action, sort_name):
        """Update the richer status bar labels."""
        try:
            self._sb_movies.configure(text=f"  Movies: {total}")
            self._sb_warn.configure(text=f"  Warnings: {warnings}")
            self._sb_errors.configure(text=f"  Errors: {errors}")
            if action:
                self._sb_action.configure(text=f"  Last: {action}")
            self._sb_sort.configure(text=f"Sort: {sort_name}  ")
        except Exception:
            pass

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
            f"{t} movies", f"poster:{pc}/{t}", f"folder:{fc}/{t}",
            f"fanart:{ac}/{t}", f"nfo:{nc}/{t}({ne}err)",
            f"xml:{xc}/{t}({xe}err)", f"video:{vc}/{t}",
            f"{iso}-OK:{lk}/{t}"
        ]))
        ### NEW v0.10.0 — also update richer status bar ###
        _warn = sum(1 for r in self._results if r["row_health"] == "yellow")
        _err  = sum(1 for r in self._results if r["row_health"] == "red")
        self._update_status_bar(t, _warn, _err, "", self.sort_var.get())

    # ── Row values ─────────────────────────────────────────────────────────────
    def _rv(self, r):
        ### NEW v0.12.0 — merged image columns (icon + quality label in one cell) ###
        def img_cell(exists, status, quality):
            """Return merged cell: icon + quality label."""
            if not exists:
                return f"{STATUS_MISSING} Missing"
            if status == STATUS_ERROR:
                return f"{STATUS_ERROR} {quality if quality != '—' else 'Error'}"
            if status == STATUS_WARN:
                return f"{STATUS_WARN} {quality}"
            return f"{STATUS_OK} {quality}"

        # Rating cell format: "icon value" e.g. "⬤ 7.3" / "◐ 6.8" / "○ -" / "✕ -"
        def rating_cell(rating_str, rating_status):
            return f"{rating_status} {rating_str}"

        return (
            r.get("movie_name", r["subfolder"]),               # COL_MOVIE_NAME
            r.get("movie_year", "-"),                          # COL_YEAR
            r.get("genre_status", STATUS_ERROR) + " " + r.get("genre_display", "-"),  # COL_GENRE
            rating_cell(r.get("rating_str", "-"), r.get("rating_status", STATUS_MISSING)),  # COL_RATING
            img_cell(r["poster_exists"], r.get("poster_status", STATUS_MISSING), r.get("poster_quality", "—")),   # COL_POSTER
            img_cell(r["folder_exists"], r.get("folder_status", STATUS_MISSING), r.get("folder_quality", "—")),   # COL_FOLDER
            img_cell(r["fanart_exists"],  r.get("fanart_status",  STATUS_MISSING), r.get("fanart_quality",  "—")),  # COL_FANART
            str(r["backdrop_count"]) if r["backdrop_count"] > 0 else "-",             # COL_BACKDROPS
            (STATUS_ERROR if r["nfo_errors"] else STATUS_OK) if r["nfo_exists"] else STATUS_MISSING,  # COL_NFO
            (STATUS_ERROR if r["xml_errors"] else STATUS_OK) if r["xml_exists"] else STATUS_MISSING,  # COL_XML
            r["language"],                                                             # COL_LANGUAGE
            r["video_ext"] if r["video_count"] > 0 else STATUS_MISSING,               # COL_VID_EXT
            r["video_size"],                                                           # COL_VID_SIZE
            r.get("video_quality", "-"),                                               # COL_QUALITY
            r.get("lang_ok", "-"),                                                     # COL_LANG_OK
            r["subs_summary"],                                                         # COL_SUBS
        )

    # ── Refresh table ──────────────────────────────────────────────────────────
    def _refresh_table(self):
        if not self._results: return
        for r in self.tree.get_children(): self.tree.delete(r)
        self._item_map.clear()

        sort_name = self.sort_var.get()
        kf, rev   = SORT_OPTIONS.get(sort_name, SORT_OPTIONS["Movie Name (A-Z)"])
        def sort_key(r):
            return (kf(r), r.get("movie_name", r["subfolder"]).lower())
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
                ### NEW v0.10.0 — updated CSV headers for new columns ###
                w.writerow(["Movie Name","Year","Folder Name","Path",
                             "poster.jpg","Poster Size","Poster Dim",
                             "folder.jpg","Folder Size","Folder Dim",
                             "fanart.jpg","Fanart Size","Fanart Dim","Backdrops",
                             ".nfo","NFO Status","NFO Errors","movie.xml","XML Status","XML Errors",
                             "Language","Video Files","Video Ext","Video Size","Quality",
                             f"{iso} OK?","Embedded Subs","External Subs","Genre","Health"])
                for r in self._results:
                    w.writerow([
                        r.get("movie_name", r["subfolder"]), r.get("movie_year", "-"),
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
    # Only STATUS_ERROR (✕) makes a row red — STATUS_WARN (◐) does not
    has_err = (row.get("nfo_status") == STATUS_ERROR or
               row.get("xml_status") == STATUS_ERROR or
               row.get("poster_status", STATUS_MISSING) == STATUS_ERROR or
               row.get("fanart_status", STATUS_MISSING) == STATUS_ERROR or
               row.get("folder_status", STATUS_MISSING) == STATUS_ERROR or
               row.get("rating_status") == STATUS_ERROR)   ### NEW v0.12.0 ###
    # Yellow if any file is missing OR has a warning
    has_warn = (not row.get("poster_exists") or
                not row.get("fanart_exists") or
                not row.get("folder_exists") or
                row.get("poster_status", STATUS_MISSING) == STATUS_WARN or
                row.get("fanart_status", STATUS_MISSING) == STATUS_WARN or
                row.get("folder_status", STATUS_MISSING) == STATUS_WARN or
                row.get("nfo_status") == STATUS_MISSING or
                row.get("xml_status") == STATUS_MISSING or
                row.get("video_count", 0) != 1 or
                row.get("rating_status") == STATUS_MISSING)  ### NEW v0.12.0 ###
    if has_err:   return "red"
    if has_warn:  return "yellow"
    return "green"


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
