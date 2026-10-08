# =============================================================================
# Metadata & MediaClinic
# Version: 0.18.0
# Author:  Luiz Junqueira & Claude AI
# Contact: junqueira.ch@gmail.com
#
# CHANGELOG
# ---------
# v0.14.0 (current)                                         ### NEW v0.14.0 ###
#   - Architecture: settings subsystem split into four dedicated modules:
#       settings_model.py      — pure data, defaults, quality tiers
#       settings_controller.py — all non-UI logic (load/save, FFmpeg, browsers, backup)
#       settings_context.py    — SettingsContext dataclass + run_async() helper
#     settings_dialog.py retains UI only; _inject_globals() kept as shim
#   - FFmpeg test button and browser detection now run off the UI thread (run_async)
#   - Snapshot logic upgraded to structured dict (image_sizes sub-dict, genres list,
#     tag_pairs list-of-tuples); dict equality replaces string comparison
#   - New: settings_schema.json, CLAUDE_RULES.md, settings_test_harness.py
#   - Version bump to v0.14.0
# v0.13.1 (previous)                                        ### NEW v0.13.1 ###
#   - Fix: Changing only the browser no longer triggers a rescan prompt
#          (also fixed false-positive in tag_pairs change detection)
#   - New: Normalize Genres now splits merged genre tags on /, \, |, ,, ;
#          ("Family/Fantasy" → "Family" + "Fantasy"); writes one tag per genre
#   - New: Keyboard jump-to-letter — press A–Z or 0–9 in the table to jump
#          to the next movie whose name starts with that character
#          (cycles, case-insensitive, diacritics stripped)
#   - Version bump to v0.13.1
# v0.13.0 (previous)                                        ### NEW v0.13.0 ###
#   - Fix: Browser tab — selected radio button highlighted (filled circle,
#          accent color, row tint, "(selected)" suffix); unselected dimmed
#   - Fix: Settings dialog — all 10 tabs confirmed visible (Tools → Backup)
#   - Fix: Rescan popup (_offer_rescan) now centered on parent window with
#          proper padding; no more top-left corner placement
#   - Fix: Status bar (Movies / Warnings / Errors) always recalculated after
#          every scan path including Update Scan (no FFprobe)
#   - Fix: Help → About section now has a vertical scrollbar (consistent
#          with other Help tabs)
#   - Fix: NFO/XML error popup now includes an "Open File" button
#   - Fix: Settings save no longer freezes UI — wait_window() replaced with
#          non-blocking callback dialog throughout the save pipeline
#   - Fix: "Bkdrps" column and all Help references renamed to "Backdrops"
#   - Fix: Right-click menu items renamed:
#          "Re-validate (with FFprobe)" → "Update (with FFprobe)"
#          "Re-validate (no FFprobe)"   → "Update (no FFprobe)"
#   - Version bump to v0.13.0
# v0.12.0 (previous)                                        ### NEW v0.12.0 ###
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
import unicodedata  # v0.13.1 — strip diacritics for jump-to-letter

# PIL/Pillow — used for thumbnail display in Fetch Image dialogs ### NEW v0.16.0 ###
try:
    from PIL import Image as _PILImage, ImageTk as _PILImageTk
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False
# ── v0.14.0 settings subsystem ───────────────────────────────────────────────
# settings_model, settings_controller, and settings_context are imported so
# that the new modules are initialized and available as the application loads.
# The main script continues to own all live state (SETTINGS, FFMPEG_PATH, etc.)
# and passes it into settings_dialog via _sd_inject() exactly as before.
# No circular imports: none of these modules import from mediaclinic.py.
import settings_model       # noqa: F401  pure data — imported for module init
import settings_controller  # noqa: F401  non-UI logic — available for future direct use
import settings_context     # noqa: F401  SettingsContext dataclass + run_async helper
from settings_dialog import SettingsDialog, _inject_globals as _sd_inject

# ── App identity ──────────────────────────────────────────────────────────────
APP_NAME    = "Metadata & MediaClinic"
APP_VERSION = "0.18.0"  ### NEW v0.18.0 ###
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
    {"id": "movie_name", "label": "Movie Name",    "width": 240, "anchor": "w",      "stretch": False,  ### FIX v0.17.3 — was True, caused column redistribution on resize ###
     "header_tip": "Movie title extracted from the NFO/XML metadata.",
     "dblclick": "open_folder"},
    {"id": "year",       "label": "Year",            "width":  52, "anchor": "center", "stretch": False,
     "header_tip": "Production year from NFO <year> or XML <ProductionYear>.",
     "dblclick": "none"},
    {"id": "genre",      "label": "Genres",         "width": 140, "anchor": "w",      "stretch": False,  ### FIX v0.17.3 ###
     "header_tip": "Genres listed in the NFO <genre> tags.",
     "dblclick": "open_nfo_genre"},
    ### NEW v0.12.0 — Rating column (between Genres and Poster) ###
    {"id": "rating",     "label": "Rating",          "width":  80, "anchor": "center", "stretch": False,
     "header_tip": "Rating extracted from NFO <rating> or XML <IMDBrating>/<Rating>.",
     "dblclick": "open_nfo"},
    ### NEW v0.16.0 — Votes column (between Rating and Source) ###
    {"id": "votes",      "label": "Votes",            "width":  90, "anchor": "center", "stretch": False,
     "header_tip": "Vote count from NFO <votes> or XML <Votes>/<VoteCount>. ⬤=match ◐=differ ○=missing ✕=error",
     "dblclick": "open_nfo"},
    ### NEW v0.16.0 — Source column (between Votes and Poster) ###
    {"id": "source",     "label": "Source",           "width": 140, "anchor": "center", "stretch": False,
     "header_tip": "IMDB and TMDB IDs found across all tags. ⬤=all agree ◐=partial ○=missing ✕=error. Double-click to open website.",
     "dblclick": "open_source_choice"},
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
    {"id": "backdrops",  "label": "Backdrops",       "width":  70, "anchor": "center", "stretch": False,
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
    ### NEW v0.15.0 — Audio column (between Quality and Lang OK?) ###
    {"id": "audio",      "label": "Audio",            "width": 120, "anchor": "w",      "stretch": False,
     "header_tip": "Audio tracks detected by FFprobe (language and channel layout). Only populated during FFprobe scans.",
     "dblclick": "none"},
    {"id": "lang_ok",    "label": "LANG_OK_LABEL",   "width":  58, "anchor": "center", "stretch": False,
     "header_tip": "Checks whether the target language audio or subtitle track is present.",
     "dblclick": "none"},
    {"id": "subs",       "label": "Subtitles",       "width": 180, "anchor": "w",      "stretch": False,  ### FIX v0.17.3 ###
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
COL_VOTES  = _COL_IDX["votes"]    ### NEW v0.16.0 ###
COL_SOURCE = _COL_IDX["source"]   ### NEW v0.16.0 ###
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
COL_AUDIO = _COL_IDX["audio"]                                  ### NEW v0.15.0 ###
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
    "poster_quality_level":  "1080p",   # default poster/folder quality minimum  ### v0.16.1 ###
    "folder_quality_level":  "1080p",
    "fanart_quality_level":  "1080p",
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
    # v0.18.0 — Column width persistence                    ### NEW v0.18.0 ###
    "column_widths":         {},        # {col_id: pixel_width} saved on close
}

def _load_settings():
    # Legacy quality tier name migration  ### NEW v0.16.1 ###
    _LEGACY_QUALITY_MAP = {
        "Ultra (4K)":         "4K",
        "Retina/QHD":         "1440p",
        "Retina/QHD (1440p)": "1440p",
        "Standard (HD)":      "1080p",
        "Full HD":            "1080p",
        "Optimized":          "720p",
        "HD Ready":           "720p",
        "Thumbnail":          "360p",
        "Below HD Ready":     "360p",
    }
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
            # Migrate legacy quality labels silently
            for qkey in ("poster_quality_level", "folder_quality_level",
                         "fanart_quality_level"):
                if merged.get(qkey) in _LEGACY_QUALITY_MAP:
                    merged[qkey] = _LEGACY_QUALITY_MAP[merged[qkey]]
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
logger.info("=== Metadata & MediaClinic v0.13.1 started ===")

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
# Image Quality Tier System  (updated v0.16.1)                ### NEW v0.16.1 ###
# ══════════════════════════════════════════════════════════════════════════════
# 7-tier system for poster/folder and fanart. Lowest tier (360p) absorbs all
# images below its threshold. FANART_BELOW_LABEL removed.

POSTER_QUALITY_TIERS = [
    # (label,   min_w, min_h,  total_px,  est_size_str)
    ("4K",      2000,  3000,  6_000_000, "1.5–3.0 MB"),
    ("1440p",   1500,  2250,  3_375_000, "800 KB–1.5 MB"),
    ("1080p",   1000,  1500,  1_500_000, "300–600 KB"),
    ("720p",     666,  1000,    666_000, "150–250 KB"),
    ("540p",     540,   810,    437_400, "120–150 KB"),
    ("480p",     480,   720,    345_600, "70–120 KB"),
    ("360p",     360,   540,    194_400, "40–70 KB"),
]

FANART_QUALITY_TIERS = [
    # (label,   min_w, min_h,  total_px,  est_size_str)
    ("4K",      3840,  2160,  8_294_400, "2.0–4.5 MB"),
    ("1440p",   2560,  1440,  3_686_400, "1.0–2.0 MB"),
    ("1080p",   1920,  1080,  2_073_600, "400–800 KB"),
    ("720p",    1280,   720,    921_600, "200–350 KB"),
    ("540p",     960,   540,    518_400, "130–180 KB"),
    ("480p",     854,   480,    409_920, "80–130 KB"),
    ("360p",     640,   360,    230_400, "40–75 KB"),
]

# Tolerance margin (±5%)
_IMG_QUALITY_TOLERANCE = 0.05


def classify_image_quality(width, height, image_type):
    """Classify image quality. Lowest tier (360p) absorbs all images below it."""
    if not width or not height:
        return "—"
    tol = 1 - _IMG_QUALITY_TOLERANCE
    if image_type in ("poster", "folder"):
        for label, mw, mh, _, _ in POSTER_QUALITY_TIERS:
            if width >= mw * tol and height >= mh * tol:
                return label
        return "360p"
    elif image_type == "fanart":
        for label, mw, mh, _, _ in FANART_QUALITY_TIERS:
            if width >= mw * tol and height >= mh * tol:
                return label
        return "360p"
    return "—"


def _poster_quality_sort_key(label):
    order = {t[0]: i for i, t in enumerate(POSTER_QUALITY_TIERS)}
    return order.get(label, len(POSTER_QUALITY_TIERS) + 1)


def _fanart_quality_sort_key(label):
    order = {t[0]: i for i, t in enumerate(FANART_QUALITY_TIERS)}
    return order.get(label, len(FANART_QUALITY_TIERS) + 1)


def _poster_quality_sort_key_missing_last(r, key, high_to_low):
    val = r.get(key)
    if val is None or val == "—":
        return 9999 if high_to_low else -1
    return _poster_quality_sort_key(val)


def _fanart_quality_sort_key_missing_last(r, key, high_to_low):
    val = r.get(key)
    if val is None or val == "—":
        return 9999 if high_to_low else -1
    return _fanart_quality_sort_key(val)


def _sources_sort_key(r, errors_first=True):                   ### NEW v0.17.0 ###
    """
    Sort key for the Sources column.
    Uses the worst (lowest-ranked) status across IMDB and TMDB.
    errors_first=True  → ✕ sorts first (priority 0)
    errors_first=False → ⬤ sorts first (priority 0)
    """
    if errors_first:
        priority = {STATUS_ERROR: 0, STATUS_MISSING: 1, STATUS_WARN: 2, STATUS_OK: 3}
    else:
        priority = {STATUS_OK: 0, STATUS_WARN: 1, STATUS_MISSING: 2, STATUS_ERROR: 3}
    imdb_p = priority.get(r.get("source_imdb_status", STATUS_MISSING), 2)
    tmdb_p = priority.get(r.get("source_tmdb_status", STATUS_MISSING), 2)
    return min(imdb_p, tmdb_p)   # worst of the two


def _lang_ok_sort_key(val):                                     ### NEW v0.15.0 — fix inverted sort ###
    """Sort key: Y=0 (best, sorts first), N=1, —=2 (no video)."""
    return {"Y": 0, "N": 1}.get(val, 2)


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



def _accent_insensitive_name(r):                                ### NEW v0.15.0 — accent-insensitive sort ###
    """Sort key: NFD-normalised, lower-case movie name for accent-insensitive A-Z sort."""
    import unicodedata
    name = r.get("movie_name", "") or ""
    return unicodedata.normalize("NFD", name).lower()

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
            min_level = SETTINGS.get(f"{image_type}_quality_level", "1080p")  ### v0.16.1 ###
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
            min_level = SETTINGS.get("fanart_quality_level", "1080p")  ### v0.16.1 ###
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

def count_backdrops(sub_path):                                   ### NEW v0.15.0 — returns avg_bytes ###
    ### UPDATED v0.18.0 — scan all backdrop*.jpg; no longer stops at first gap ###
    paths = []
    try:
        for entry in os.scandir(sub_path):
            if not entry.is_file():
                continue
            name = entry.name.lower()
            if name == "backdrop.jpg":
                paths.append(entry.path)
            elif re.match(r'^backdrop\d+\.jpg$', name):
                paths.append(entry.path)
    except OSError:
        pass
    # Sort deterministically: backdrop.jpg first, then backdrop1.jpg, backdrop2.jpg…
    def _sort_key(p):
        n = os.path.basename(p).lower()
        if n == "backdrop.jpg":
            return -1
        m = re.match(r'^backdrop(\d+)\.jpg$', n)
        return int(m.group(1)) if m else 9999
    paths.sort(key=_sort_key)
    count = len(paths)
    total_bytes = sum(os.path.getsize(p) for p in paths if os.path.isfile(p))
    avg_bytes = (total_bytes // count) if count > 0 else 0          ### NEW v0.15.0 ###
    return count, paths, avg_bytes                                   ### NEW v0.15.0 ###

def next_backdrop_number(sub_path):
    ### UPDATED v0.18.0 — find first unused slot even when numbers have gaps ###
    if not os.path.isfile(os.path.join(sub_path, "backdrop.jpg")):
        return 0
    used = set()
    try:
        for entry in os.scandir(sub_path):
            if not entry.is_file():
                continue
            m = re.match(r'^backdrop(\d+)\.jpg$', entry.name.lower())
            if m:
                used.add(int(m.group(1)))
    except OSError:
        pass
    i = 1
    while i in used:
        i += 1
    return i

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
def scan_audio_tracks(video_path):                              ### NEW v0.15.0 ###
    """
    Extract audio tracks from video_path using ffprobe.
    Returns list of dicts: [{language, codec, channels, bitrate}, ...]
    Only runs if FFPROBE_PATH is available.
    """
    if not video_path or not FFPROBE_PATH or not SETTINGS.get("use_ffprobe", True):
        return []
    try:
        proc = subprocess.run(
            [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "a", video_path],
            capture_output=True, text=True, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if proc.returncode != 0 or not proc.stdout.strip():
            return []
        tracks = []
        for stream in json.loads(proc.stdout).get("streams", []):
            tags    = stream.get("tags", {})
            lang    = (tags.get("language") or tags.get("LANGUAGE") or
                       tags.get("lang") or "und").upper()
            codec   = (stream.get("codec_name") or "").upper()
            # Channels
            ch_layout = stream.get("channel_layout", "")
            channels_int = stream.get("channels", 0)
            if ch_layout:
                _ch_map = {"mono": "1.0", "stereo": "2.0",
                           "2.1": "2.1", "3.0": "3.0",
                           "4.0": "4.0", "5.0": "5.0",
                           "5.1": "5.1", "6.0": "6.0",
                           "6.1": "6.1", "7.0": "7.0",
                           "7.1": "7.1"}
                channels = _ch_map.get(ch_layout.lower(), ch_layout)
            elif channels_int:
                _int_map = {1:"1.0",2:"2.0",3:"2.1",4:"4.0",5:"5.0",6:"5.1",
                            7:"6.1",8:"7.1"}
                channels = _int_map.get(channels_int, str(channels_int))
            else:
                channels = ""
            # Bitrate (kbps)
            br_raw = stream.get("bit_rate") or stream.get("BIT_RATE")
            try:
                bitrate = int(int(br_raw) / 1000) if br_raw else None
            except Exception:
                bitrate = None
            tracks.append({
                "language": lang, "codec": codec,
                "channels": channels, "bitrate": bitrate})
        return tracks
    except Exception:
        return []



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


def extract_rating_from_files(nfo_path, xml_path):              ### NEW v0.15.0 — adds votes + source ###
    """
    Extract movie rating and votes from NFO and/or XML files.

    Rating priority:  1. NFO <rating>   2. XML <IMDBrating>   3. XML <Rating>
    Votes priority:   1. NFO <votes>    2. XML <Votes>         3. XML <VoteCount>

    Returns
    -------
    (rating_str, status, rating_value, votes_int, votes_source_tag, rating_source_tag)
        rating_str       : display string e.g. "7.3" or "-"
        status           : STATUS_OK / STATUS_WARN / STATUS_ERROR / STATUS_MISSING
        rating_value     : float for sorting, -1.0 when absent/invalid
        votes_int        : int number of votes (0 if missing)
        votes_source_tag : string describing votes source e.g. "nfo_votes" / "xml_Votes" / "xml_VoteCount" / ""
        rating_source_tag: string describing rating source e.g. "nfo_rating" / "xml_IMDBrating" / "xml_Rating" / ""
    """
    def _try_float(s):
        try:
            return float(str(s).strip().replace(",", "."))
        except Exception:
            return None

    def _try_int(s):
        try:
            v = str(s).strip().replace(",", "").replace(".", "")
            return int(v)
        except Exception:
            return None

    nfo_val = None
    nfo_votes = None
    xml_imdb_val = None
    xml_rating_val = None
    xml_votes_val = None       # from <Votes>
    xml_votecount_val = None   # from <VoteCount>
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
            mv = re.search(r'<votes[^>]*>([^<]*)</votes>', content, re.IGNORECASE)
            if mv:
                raw_v = mv.group(1).strip()
                if raw_v:
                    iv = _try_int(raw_v)
                    if iv is not None:
                        nfo_votes = iv
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
            # Votes from XML
            mv = re.search(r'<Votes[^>]*>([^<]*)</Votes>', content)
            if mv:
                raw_v = mv.group(1).strip()
                if raw_v:
                    iv = _try_int(raw_v)
                    if iv is not None:
                        xml_votes_val = iv
            mvc = re.search(r'<VoteCount[^>]*>([^<]*)</VoteCount>', content)
            if mvc:
                raw_v = mvc.group(1).strip()
                if raw_v:
                    iv = _try_int(raw_v)
                    if iv is not None:
                        xml_votecount_val = iv
        except Exception:
            parse_error = True

    if parse_error and nfo_val is None and xml_imdb_val is None and xml_rating_val is None:
        return "-", STATUS_ERROR, -1.0, 0, "", ""

    values = {}
    if nfo_val is not None:         values["nfo"] = nfo_val
    if xml_imdb_val is not None:    values["xml_imdb"] = xml_imdb_val
    if xml_rating_val is not None:  values["xml_rating"] = xml_rating_val

    if not values:
        return "-", STATUS_MISSING, -1.0, 0, "", ""

    # Determine primary rating and source
    if "nfo" in values:
        primary = values["nfo"]; rating_source = "nfo_rating"
    elif "xml_imdb" in values:
        primary = values["xml_imdb"]; rating_source = "xml_IMDBrating"
    else:
        primary = values["xml_rating"]; rating_source = "xml_Rating"

    all_vals = list(values.values())
    has_conflict = len(all_vals) > 1 and any(abs(v - all_vals[0]) > 0.05 for v in all_vals[1:])

    # Determine votes (priority: nfo_votes > xml_votes > xml_votecount)
    # Check for votes conflict
    existing_votes = {}
    if nfo_votes is not None:        existing_votes["nfo_votes"] = nfo_votes
    if xml_votes_val is not None:    existing_votes["xml_Votes"] = xml_votes_val
    if xml_votecount_val is not None: existing_votes["xml_VoteCount"] = xml_votecount_val

    votes_conflict = (len(existing_votes) > 1 and
                      len(set(existing_votes.values())) > 1)

    # Choose votes by priority
    if nfo_votes is not None:
        chosen_votes = nfo_votes; votes_source = "nfo_votes"
    elif xml_votes_val is not None:
        chosen_votes = xml_votes_val; votes_source = "xml_Votes"
    elif xml_votecount_val is not None:
        chosen_votes = xml_votecount_val; votes_source = "xml_VoteCount"
    else:
        chosen_votes = 0; votes_source = ""

    # v0.16.0: Rating status reflects ONLY rating conflict — votes conflict moved to Votes column
    status = STATUS_WARN if has_conflict else STATUS_OK  ### NEW v0.16.0 ###

    rating_str = f"{primary:.1f}"
    return rating_str, status, primary, chosen_votes, votes_source, rating_source


def extract_votes_from_files(nfo_path, xml_path):          ### NEW v0.16.0 ###
    """
    Extract vote count from NFO and XML with conflict detection.
    Priority: 1) NFO <votes>   2) XML <Votes>   3) XML <VoteCount>
    Conflict checked only between NFO <votes> and XML <Votes>.
    Returns (votes_int, status, source_tag).
    """
    def _parse_votes(s):
        try:
            v = re.sub(r'[^\d]', '', str(s).strip())
            return int(v) if v else None
        except Exception:
            return None

    nfo_votes = None
    xml_votes = None
    xml_votecount = None
    parse_error = False

    if nfo_path and os.path.isfile(nfo_path):
        try:
            with open(nfo_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            m = re.search(r'<votes[^>]*>([^<]*)</votes>', content, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                if raw:
                    iv = _parse_votes(raw)
                    if iv is not None: nfo_votes = iv
                    else: parse_error = True
        except Exception:
            parse_error = True

    if xml_path and os.path.isfile(xml_path):
        try:
            with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            mv = re.search(r'<Votes[^>]*>([^<]*)</Votes>', content)
            if mv:
                raw = mv.group(1).strip()
                if raw:
                    iv = _parse_votes(raw)
                    if iv is not None: xml_votes = iv
                    else: parse_error = True
            mvc = re.search(r'<VoteCount[^>]*>([^<]*)</VoteCount>', content)
            if mvc:
                raw = mvc.group(1).strip()
                if raw:
                    iv = _parse_votes(raw)
                    if iv is not None: xml_votecount = iv
                    else: parse_error = True
        except Exception:
            parse_error = True

    conflict = (nfo_votes is not None and xml_votes is not None
                and nfo_votes != xml_votes)

    if nfo_votes is not None:
        chosen = nfo_votes; src = "nfo_votes"
    elif xml_votes is not None:
        chosen = xml_votes; src = "xml_Votes"
    elif xml_votecount is not None:
        chosen = xml_votecount; src = "xml_VoteCount"
    else:
        chosen = 0; src = ""

    if parse_error and chosen == 0:
        return 0, STATUS_ERROR, ""
    if chosen == 0 and not parse_error:
        return 0, STATUS_MISSING, ""
    if conflict:
        return chosen, STATUS_WARN, src
    return chosen, STATUS_OK, src


def extract_source_ids_from_files(nfo_path, xml_path):     ### NEW v0.16.0 ###
    """
    Extract IMDB and TMDB IDs from all 12 authoritative tags.

    XML: IMDB → <IMDB>, <IMDbId>, <IMDB_ID>
         TMDB → <TMDB>, <TMDbId>, <TMDB_ID>
    NFO: IMDB → <id>, <imdbid>, <id moviedb="imdb">
         TMDB → <tmdbid>, <id moviedb="tmdb">, <id moviedb="themoviedb">

    Icon per source:
        STATUS_OK      all found tags agree
        STATUS_WARN    tags disagree or some missing but at least one valid
        STATUS_MISSING none found
        STATUS_ERROR   any tag present but unreadable

    Returns dict: imdb_val, imdb_status, imdb_all_vals,
                  tmdb_val, tmdb_status, tmdb_all_vals
    """
    imdb_xml = []; tmdb_xml = []
    imdb_nfo = []; tmdb_nfo = []
    imdb_error = False; tmdb_error = False

    # ── XML ──────────────────────────────────────────────────────────────────
    if xml_path and os.path.isfile(xml_path):
        try:
            with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            clean = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)
            root = ET.fromstring(clean)
            for tag in ["IMDB", "IMDbId", "IMDB_ID"]:
                el = root.find(tag)
                if el is not None:
                    txt = (el.text or "").strip()
                    if txt: imdb_xml.append(txt)
                    else: imdb_error = True
            for tag in ["TMDB", "TMDbId", "TMDB_ID"]:
                el = root.find(tag)
                if el is not None:
                    txt = (el.text or "").strip()
                    if txt: tmdb_xml.append(txt)
                    else: tmdb_error = True
        except Exception:
            imdb_error = True; tmdb_error = True

    # ── NFO ──────────────────────────────────────────────────────────────────
    if nfo_path and os.path.isfile(nfo_path):
        try:
            with open(nfo_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            clean = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)
            root_nfo = ET.fromstring(clean)
            for el in root_nfo.findall("id"):
                mdb = el.get("moviedb", "")
                txt = (el.text or "").strip()
                if mdb.lower() == "imdb":
                    if txt: imdb_nfo.append(txt)
                    else: imdb_error = True
                elif mdb.lower() in ("tmdb", "themoviedb"):
                    if txt: tmdb_nfo.append(txt)
                    else: tmdb_error = True
                elif not mdb and txt.startswith("tt"):
                    imdb_nfo.append(txt)
            for el in root_nfo.findall("imdbid"):
                txt = (el.text or "").strip()
                if txt: imdb_nfo.append(txt)
                else: imdb_error = True
            for el in root_nfo.findall("tmdbid"):
                txt = (el.text or "").strip()
                if txt: tmdb_nfo.append(txt)
                else: tmdb_error = True
        except Exception:
            # Malformed NFO — regex fallback
            try:
                with open(nfo_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                m = re.search(r'<imdbid[^>]*>([^<]+)</imdbid>', content, re.IGNORECASE)
                if m: imdb_nfo.append(m.group(1).strip())
                m = re.search(r'<tmdbid[^>]*>([^<]+)</tmdbid>', content, re.IGNORECASE)
                if m: tmdb_nfo.append(m.group(1).strip())
                for m in re.finditer(
                        r'<id[^>]*moviedb=["\']?imdb["\']?[^>]*>([^<]+)</id>',
                        content, re.IGNORECASE):
                    imdb_nfo.append(m.group(1).strip())
                for m in re.finditer(
                        r'<id[^>]*moviedb=["\']?(?:tmdb|themoviedb)["\']?[^>]*>([^<]+)</id>',
                        content, re.IGNORECASE):
                    tmdb_nfo.append(m.group(1).strip())
            except Exception:
                imdb_error = True; tmdb_error = True

    def _dedup(lst):
        seen = set(); out = []
        for v in lst:
            if v and v not in seen: seen.add(v); out.append(v)
        return out

    imdb_all = _dedup(imdb_xml + imdb_nfo)
    tmdb_all = _dedup(tmdb_xml + tmdb_nfo)

    # ── Classify IMDB ─────────────────────────────────────────────────────────
    # STATUS_WARN when:
    #   (a) values found but they disagree, OR
    #   (b) value found in one source but the other source file exists and has no tag
    #       (i.e. present in XML but absent in NFO, or vice-versa)         ### FIX v0.16.0 ###
    imdb_partial = (
        (bool(imdb_xml) and not imdb_nfo and nfo_path and os.path.isfile(nfo_path)) or
        (bool(imdb_nfo) and not imdb_xml and xml_path and os.path.isfile(xml_path))
    )

    if imdb_error:
        imdb_val    = imdb_all[0] if imdb_all else None
        imdb_status = STATUS_ERROR
    elif not imdb_all:
        imdb_val    = None
        imdb_status = STATUS_MISSING
    elif len(set(imdb_all)) > 1 or imdb_partial:   ### FIX v0.16.0 — partial triggers WARN ###
        imdb_val    = imdb_all[0]
        imdb_status = STATUS_WARN
    else:
        imdb_val    = imdb_all[0]
        imdb_status = STATUS_OK

    # ── Classify TMDB ─────────────────────────────────────────────────────────
    tmdb_partial = (
        (bool(tmdb_xml) and not tmdb_nfo and nfo_path and os.path.isfile(nfo_path)) or
        (bool(tmdb_nfo) and not tmdb_xml and xml_path and os.path.isfile(xml_path))
    )

    if tmdb_error:
        tmdb_val    = tmdb_all[0] if tmdb_all else None
        tmdb_status = STATUS_ERROR
    elif not tmdb_all:
        tmdb_val    = None
        tmdb_status = STATUS_MISSING
    elif len(set(tmdb_all)) > 1 or tmdb_partial:   ### FIX v0.16.0 — partial triggers WARN ###
        tmdb_val    = tmdb_all[0]
        tmdb_status = STATUS_WARN
    else:
        tmdb_val    = tmdb_all[0]
        tmdb_status = STATUS_OK

    return {
        "imdb_val": imdb_val, "imdb_status": imdb_status, "imdb_all_vals": imdb_all,
        "tmdb_val": tmdb_val, "tmdb_status": tmdb_status, "tmdb_all_vals": tmdb_all,
    }



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

### NEW v0.16.0 — multilingual genre translation dictionary ###
# Covers PT, DE, FR, ES, IT, RU, ZH (Mandarin), AR
# Maps foreign-language genre names (lowercase) → English canonical name
_GENRE_TRANSLATIONS = {
    # Portuguese
    "ação": "Action", "accao": "Action", "acao": "Action",
    "aventura": "Adventure", "animação": "Animation", "animacao": "Animation",
    "comédia": "Comedy", "comedia": "Comedy", "crime": "Crime",
    "documentário": "Documentary", "documentario": "Documentary",
    "drama": "Drama", "família": "Family", "familia": "Family",
    "fantasia": "Fantasy", "história": "History", "historia": "History",
    "terror": "Horror", "horror": "Horror", "música": "Music", "musica": "Music",
    "mistério": "Mystery", "misterio": "Mystery",
    "romance": "Romance", "romântico": "Romance", "romantico": "Romance",
    "ficção científica": "Science Fiction", "ficcao cientifica": "Science Fiction",
    "fc": "Science Fiction", "suspense": "Thriller", "guerra": "War",
    "faroeste": "Western", "ocidental": "Western",
    # German
    "aktion": "Action", "abenteuer": "Adventure",
    "animation": "Animation", "komödie": "Comedy", "komodie": "Comedy",
    "kriminalfilm": "Crime", "krimi": "Crime", "dokumentarfilm": "Documentary",
    "doku": "Documentary", "familie": "Family", "fantasie": "Fantasy",
    "geschichte": "History", "horror": "Horror", "musik": "Music",
    "geheimnis": "Mystery", "liebesfilm": "Romance", "romantik": "Romance",
    "wissenschaftliche fiktion": "Science Fiction", "science-fiction": "Science Fiction",
    "thriller": "Thriller", "krieg": "War", "western": "Western",
    # French
    "action": "Action", "aventure": "Adventure",
    "comédie": "Comedy", "comedie": "Comedy", "policier": "Crime",
    "documentaire": "Documentary", "drame": "Drama", "famille": "Family",
    "fantastique": "Fantasy", "histoire": "History", "horreur": "Horror",
    "musique": "Music", "mystère": "Mystery", "mystere": "Mystery",
    "romance": "Romance", "science-fiction": "Science Fiction",
    "sf": "Science Fiction", "guerre": "War", "western": "Western",
    # Spanish
    "acción": "Action", "accion": "Action", "aventura": "Adventure",
    "animación": "Animation", "animacion": "Animation",
    "comedia": "Comedy", "crimen": "Crime", "documental": "Documentary",
    "drama": "Drama", "familia": "Family", "fantasía": "Fantasy", "fantasia": "Fantasy",
    "historia": "History", "terror": "Horror", "música": "Music", "musica": "Music",
    "misterio": "Mystery", "romance": "Romance", "ciencia ficción": "Science Fiction",
    "ciencia ficcion": "Science Fiction", "suspenso": "Thriller", "guerra": "War",
    "vaquero": "Western",
    # Italian
    "azione": "Action", "avventura": "Adventure", "animazione": "Animation",
    "commedia": "Comedy", "crimine": "Crime", "documentario": "Documentary",
    "dramma": "Drama", "famiglia": "Family", "fantasia": "Fantasy",
    "storia": "History", "orrore": "Horror", "musica": "Music",
    "mistero": "Mystery", "romantico": "Romance", "fantascienza": "Science Fiction",
    "thriller": "Thriller", "guerra": "War", "western": "Western",
    # Russian (transliterated)
    "боевик": "Action", "boyevik": "Action", "приключения": "Adventure",
    "priklyucheniya": "Adventure", "мультфильм": "Animation",
    "комедия": "Comedy", "komediya": "Comedy", "криминал": "Crime",
    "dokumentalny": "Documentary", "драма": "Drama", "drama": "Drama",
    "семейный": "Family", "фэнтези": "Fantasy", "история": "History",
    "ужасы": "Horror", "uzhasy": "Horror", "музыка": "Music",
    "мистика": "Mystery", "mistika": "Mystery", "мелодрама": "Romance",
    "melodrama": "Romance", "фантастика": "Science Fiction",
    "fantastika": "Science Fiction", "триллер": "Thriller", "война": "War",
    "voyna": "War", "вестерн": "Western",
    # Chinese/Mandarin (common pinyin and hanzi)
    "动作": "Action", "dongzuo": "Action", "冒险": "Adventure",
    "maoxian": "Adventure", "动画": "Animation", "donghua": "Animation",
    "喜剧": "Comedy", "xiju": "Comedy", "犯罪": "Crime", "fanzui": "Crime",
    "纪录片": "Documentary", "jilupian": "Documentary",
    "剧情": "Drama", "juqing": "Drama", "家庭": "Family", "jiating": "Family",
    "奇幻": "Fantasy", "qihuan": "Fantasy", "历史": "History", "lishi": "History",
    "恐怖": "Horror", "kongbu": "Horror", "音乐": "Music", "yinyue": "Music",
    "悬疑": "Mystery", "xuanyi": "Mystery", "爱情": "Romance", "aiqing": "Romance",
    "科幻": "Science Fiction", "kehuan": "Science Fiction",
    "惊悚": "Thriller", "jingsong": "Thriller", "战争": "War", "zhanzheng": "War",
    "西部": "Western", "xibu": "Western",
    # Arabic (transliterated common terms)
    "اكشن": "Action", "akshun": "Action", "مغامرة": "Adventure",
    "mughamara": "Adventure", "كوميديا": "Comedy", "kumidya": "Comedy",
    "جريمة": "Crime", "jarima": "Crime", "وثائقي": "Documentary",
    "wathaiqi": "Documentary", "دراما": "Drama", "drama": "Drama",
    "عائلي": "Family", "ailiy": "Family", "خيال": "Fantasy", "khayal": "Fantasy",
    "تاريخي": "History", "tarikhi": "History", "رعب": "Horror", "ruub": "Horror",
    "موسيقى": "Music", "musiqa": "Music", "غموض": "Mystery", "ghumud": "Mystery",
    "رومانسي": "Romance", "rumansiy": "Romance",
    "خيال علمي": "Science Fiction", "khayal ilmi": "Science Fiction",
    "إثارة": "Thriller", "ithara": "Thriller", "حرب": "War", "harb": "War",
    "غربي": "Western", "gharbi": "Western",
}

def normalize_genre(raw):
    """Normalize a single genre string to its canonical form.
    ### NEW v0.16.0 — translation lookup added before synonym map ###
    """
    s = raw.strip()
    lower = s.lower()
    # Step 0: check translation dict first (foreign language → English)  ### NEW v0.16.0 ###
    if lower in _GENRE_TRANSLATIONS:
        return _GENRE_TRANSLATIONS[lower]
    # Step 1: check synonym map (case-insensitive)
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

### NEW v0.13.1 — Split merged genre tags on /, \, |, ,, ; ###
# Regex matches any combo of these separators, possibly repeated with whitespace.
_GENRE_SEPARATORS_RE = re.compile(r'[\/\\|,;]+')

def split_merged_genre(raw):
    """Split a genre string that may contain merged genres into a list.

    Examples:
        "Family/Fantasy"          -> ["Family", "Fantasy"]
        "Family///Action"         -> ["Family", "Action"]   (collapse repeats)
        "Drama, Romance"          -> ["Drama", "Romance"]
        "Family|Action;Comedy"    -> ["Family", "Action", "Comedy"]
        "Drama"                   -> ["Drama"]              (no separators)
        ""                        -> []

    Empty pieces and pure-whitespace pieces are dropped.  No normalization
    (synonym mapping, case) is applied here — callers do that next.
    """
    if not raw:
        return []
    parts = _GENRE_SEPARATORS_RE.split(raw)
    return [p.strip() for p in parts if p and p.strip()]

def normalize_genre_list(genres):
    r"""
    Normalize a list of genre strings.
    Returns (normalized_list, changed: bool).

    ### NEW v0.13.1 ###
    Each input string is FIRST split on /, \, |, ,, ; (merged-tag splitter),
    then each resulting piece is passed through normalize_genre() (synonym
    map + canonical case).  Duplicates are removed preserving first
    occurrence.  Unknown/custom pieces are kept as-is so the row's warning
    icon still surfaces them to the user.

    Examples:
        ["Family/Fantasy"]                  -> ["Family", "Fantasy"]
        ["Sci-Fi/Action"]                   -> ["Science Fiction", "Action"]
        ["Drama", "Drama/Romance"]          -> ["Drama", "Romance"]   (dedup)
        ["Action", "Adventure"]             -> ["Action", "Adventure"] (unchanged)
    """
    seen = set()
    result = []
    for raw in genres:
        # Step 1: split merged tags into individual pieces
        pieces = split_merged_genre(raw) if raw else []
        if not pieces:
            continue
        # Step 2: normalize each piece (synonym map + canonical case)
        for p in pieces:
            n = normalize_genre(p)
            if not n:
                continue
            # Step 3: dedup, preserving first occurrence (case-insensitive)
            key = n.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(n)
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
    r"""
    Return (display_str, status) for the genre column.
    status: STATUS_OK / STATUS_WARN / STATUS_ERROR
    v0.12.0: custom genres (not in settings list after normalization) ### NEW v0.12.0 ###
             now correctly show STATUS_WARN instead of STATUS_OK.
    v0.13.1: a single tag containing separators (/, \, |, ,, ;) is treated as
             a merged-genre tag and produces STATUS_WARN, so the user is
             prompted to run Normalize Genres which will split it.
    """
    if not genres:
        return "—", STATUS_ERROR   # missing = red
    valid = _get_valid_genres()
    display = "/".join(genres)
    for g in genres:
        ### NEW v0.13.1 — merged-genre tag: warn so user normalizes ###
        if _GENRE_SEPARATORS_RE.search(g):
            return display, STATUS_WARN
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

def _tmdb_fetch_json(url, timeout=15):                         ### NEW v0.17.0-bug2, FIX v0.17.2 ###
    """
    Fetch a TMDB API URL and return the decoded JSON dict.
    Does NOT request gzip to avoid double-decompression on platforms where
    urllib auto-decompresses.  If the response happens to be gzip anyway,
    we decompress defensively.
    """
    import urllib.request, gzip as _gzip
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MediaClinic/0.17.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    # Detect gzip by magic bytes — decompress only if really gzip
    if len(raw) >= 2 and raw[0] == 0x1f and raw[1] == 0x8b:
        try:
            raw = _gzip.decompress(raw)
        except Exception:
            pass   # already decompressed by urllib or not actually gzip
    # Try UTF-8 first, fall back to latin-1
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("latin-1"))


def _tmdb_error_message(exc):                                  ### NEW v0.17.0-bug2 ###
    """Convert a urllib/network exception into a human-readable TMDB error string."""
    import urllib.error as _ue
    if isinstance(exc, _ue.HTTPError):
        try:
            import json as _j
            body = _j.loads(exc.read())
            reason = body.get("status_message", str(exc))
        except Exception:
            reason = f"{exc.reason}"
        if exc.code == 401:
            return (f"TMDB API key invalid or expired (HTTP 401).\n"
                    f"Go to Settings → API Keys and verify your key.\n"
                    f"Detail: {reason}")
        if exc.code == 404:
            return (f"Movie not found on TMDB (HTTP 404).\n"
                    f"The TMDB ID in your file may be incorrect.\n"
                    f"Detail: {reason}")
        if exc.code == 429:
            return "TMDB rate limit reached (HTTP 429). Wait a moment and try again."
        return f"TMDB returned HTTP {exc.code}: {reason}"
    if isinstance(exc, _ue.URLError):
        r = str(exc.reason)
        if "SSL" in r or "certificate" in r.lower():
            return "Network error: SSL certificate problem — check your internet connection."
        if "timed out" in r.lower():
            return "Network error: Connection timed out — TMDB may be temporarily unreachable."
        if any(k in r.lower() for k in ("nodename", "getaddrinfo", "name or service", "resolve")):
            return ("Network error: Cannot resolve api.themoviedb.org.\n"
                    "Check that you have an active internet connection.")
        return f"Network error connecting to TMDB: {r}"
    return f"Unexpected error: {type(exc).__name__}: {exc}"


def _tmdb_download_image(url, dest_path, retries=2):           ### NEW v0.18.0 ###
    """
    Download a TMDB image URL to dest_path using urllib with manual retry logic.

    Uses short timeouts (connect=3s, read=10s) and exponential backoff between
    retries (0.5s, 1.0s).  Catches ConnectionResetError / WinError 10054 and
    retries automatically.  Does NOT require the 'requests' library.

    Parameters
    ----------
    url : str
        Full TMDB image URL (original or thumbnail).
    dest_path : str
        Absolute path where the downloaded bytes should be written.
    retries : int
        Number of retry attempts after the first try (default 2 → up to 3 total).

    Returns
    -------
    (True, None)   on success
    (False, str)   on failure, where str is a human-readable error message
    """
    import urllib.request, urllib.error, time as _time, socket as _socket

    _CONNECT_TIMEOUT = 3    # seconds to establish connection
    _READ_TIMEOUT    = 10   # seconds to read the full response
    _BACKOFF         = [0.5, 1.0]  # wait before retry 1 and retry 2

    last_err = "Unknown error"
    for attempt in range(retries + 1):
        if attempt > 0:
            wait = _BACKOFF[min(attempt - 1, len(_BACKOFF) - 1)]
            _time.sleep(wait)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "MediaClinic/0.18.0"})
            with urllib.request.urlopen(req,
                    timeout=_CONNECT_TIMEOUT + _READ_TIMEOUT) as resp:
                data = resp.read()
            with open(dest_path, "wb") as fout:
                fout.write(data)
            return True, None

        except ConnectionResetError as e:
            # WinError 10054 and other connection resets — always retry
            last_err = f"Connection reset by TMDB server (will retry): {e}"
            logger.warning(f"_tmdb_download_image attempt {attempt+1}: {last_err}")
            continue

        except OSError as e:
            # Catch WinError 10054 on Windows where it surfaces as OSError
            err_str = str(e)
            if "10054" in err_str or "connection" in err_str.lower():
                last_err = f"Connection reset (WinError): {e}"
                logger.warning(f"_tmdb_download_image attempt {attempt+1}: {last_err}")
                continue
            # Other OS errors (disk full, permission) — do not retry
            last_err = f"File write error: {e}"
            logger.error(f"_tmdb_download_image: {last_err}")
            return False, last_err

        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                last_err = f"HTTP {e.code} from TMDB (will retry)"
                logger.warning(f"_tmdb_download_image attempt {attempt+1}: {last_err}")
                continue
            # Non-retryable HTTP error
            last_err = _tmdb_error_message(e)
            return False, last_err

        except urllib.error.URLError as e:
            last_err = _tmdb_error_message(e)
            # Timeout errors are worth retrying; others (DNS) are not
            if "timed out" in str(e.reason).lower():
                logger.warning(f"_tmdb_download_image attempt {attempt+1}: timeout")
                continue
            return False, last_err

        except Exception as e:
            last_err = f"Unexpected download error: {type(e).__name__}: {e}"
            logger.error(f"_tmdb_download_image: {last_err}")
            return False, last_err

    return False, last_err


def _fetch_tmdb_rating(tmdb_id, api_key):
    """
    Fetch rating and vote count from TMDb.
    Returns (rating_str, votes_str) or (None, None) on failure.
    """
    if not tmdb_id or not api_key:
        return None, None
    try:
        url = (f"https://api.themoviedb.org/3/movie/{tmdb_id}"
               f"?api_key={api_key}&language=en-US")
        data = _tmdb_fetch_json(url, timeout=10)              ### FIX v0.17.0-bug2 ###
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

    bc, bp, bc_avg_bytes = count_backdrops(sub_path)  ### NEW v0.15.0 ###

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
    # Audio tracks (v0.15.0)                                   ### NEW v0.15.0 ###
    audio_tracks = []
    if use_ffprobe and vi["video_path"] and FFPROBE_PATH:
        audio_tracks = scan_audio_tracks(vi["video_path"])

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
    rating_str, rating_status, rating_value, rating_votes, rating_votes_src, rating_src = (  ### NEW v0.15.0 ###
        extract_rating_from_files(nfo_path if ne else None, xml_path if xe else None))

    # Votes extraction (v0.16.0)                          ### NEW v0.16.0 ###
    votes_int, votes_status, votes_src = extract_votes_from_files(
        nfo_path if ne else None, xml_path if xe else None)

    # Source IDs extraction (v0.16.0)                     ### NEW v0.16.0 ###
    src_ids = extract_source_ids_from_files(
        nfo_path if ne else None, xml_path if xe else None)

    has_err = (ns == STATUS_ERROR or xs == STATUS_ERROR or pc or fc or flc
               or src_ids["imdb_status"] == STATUS_ERROR         ### NEW v0.16.0 ###
               or src_ids["tmdb_status"] == STATUS_ERROR)        ### NEW v0.16.0 ###
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
        "backdrop_count": bc, "backdrop_paths": bp, "backdrop_avg_bytes": bc_avg_bytes,  ### NEW v0.15.0 ###
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
        "audio_tracks": audio_tracks,                           ### NEW v0.15.0 ###
        "lang_ok": lang_ok,
        "genres": genres, "genre_display": genre_display, "genre_status": genre_status,
        "rating_str": rating_str, "rating_status": rating_status,   ### NEW v0.12.0 ###
        "rating_value": rating_value,                                ### NEW v0.12.0 ###
        "rating_votes": rating_votes, "rating_votes_src": rating_votes_src,  ### NEW v0.15.0 ###
        "rating_src": rating_src,                                    ### NEW v0.15.0 ###
        "votes_int": votes_int, "votes_status": votes_status,        ### NEW v0.16.0 ###
        "votes_src": votes_src,                                      ### NEW v0.16.0 ###
        "source_imdb_val": src_ids["imdb_val"],                      ### NEW v0.16.0 ###
        "source_imdb_status": src_ids["imdb_status"],                ### NEW v0.16.0 ###
        "source_imdb_all": src_ids["imdb_all_vals"],                 ### NEW v0.16.0 ###
        "source_tmdb_val": src_ids["tmdb_val"],                      ### NEW v0.16.0 ###
        "source_tmdb_status": src_ids["tmdb_status"],                ### NEW v0.16.0 ###
        "source_tmdb_all": src_ids["tmdb_all_vals"],                 ### NEW v0.16.0 ###
        "row_health": health,
    }

# ── JSON persistence helpers ───────────────────────────────────────────────────
def _results_to_json(results):
    return results

def _results_from_json(data):
    defaults = {
        "video_width": None, "video_height": None, "video_quality": "—",
        "lang_ok": "—", "pt_ok": "—", "backdrop_paths": [],
        "backdrop_avg_bytes": 0,  ### NEW v0.15.0 ###
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
        "rating_votes": 0, "rating_votes_src": "", "rating_src": "",   ### NEW v0.15.0 ###
        "audio_tracks": [],                                              ### FIX v0.15.0 ###
        # v0.16.0 — votes and source                         ### NEW v0.16.0 ###
        "votes_int": 0, "votes_status": STATUS_MISSING, "votes_src": "",
        "source_imdb_val": None, "source_imdb_status": STATUS_MISSING, "source_imdb_all": [],
        "source_tmdb_val": None, "source_tmdb_status": STATUS_MISSING, "source_tmdb_all": [],
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
    "Movie Name (A-Z)":           (_accent_insensitive_name, False),  ### NEW v0.15.0 — accent-insensitive ###
    "Movie Name (Z-A)":           (_accent_insensitive_name, True),   ### NEW v0.15.0 — accent-insensitive ###
    "Year (older first)":         (lambda r: r.get("movie_year","-"),        False),
    "Year (newer first)":         (lambda r: r.get("movie_year","-"),        True),
    "Genre (A-Z)":                (lambda r: r.get("genre_display","").lower(), False),
    "Genre (Z-A)":                (lambda r: r.get("genre_display","").lower(), True),
    ### NEW v0.12.0 — Rating sort options ###
    "Rating (high→low)":          (lambda r: r.get("rating_value", -1.0),   True),
    "Rating (low→high)":          (lambda r: r.get("rating_value", -1.0),   False),
    ### NEW v0.16.0 — Votes sort options ###
    "Votes (high→low)":           (lambda r: r.get("votes_int", 0),         True),
    "Votes (low→high)":           (lambda r: r.get("votes_int", 0),         False),
    ### NEW v0.17.0 — Sources sort options (worst-of-two status) ###
    "Sources (Errors 1st)":       (lambda r: _sources_sort_key(r, errors_first=True),  False),
    "Sources (OK 1st)":           (lambda r: _sources_sort_key(r, errors_first=False), False),
    # Poster Quality (replaces Poster Size)
    "Poster Quality (high→low)":  (lambda r: _poster_quality_sort_key_missing_last(r, "poster_quality", True),  False),  ### FIX v0.15.0 ###
    "Poster Quality (low→high)":  (lambda r: _poster_quality_sort_key_missing_last(r, "poster_quality", False), True),   ### FIX v0.15.0 ###
    # Folder Quality (new)
    "Folder Quality (high→low)":  (lambda r: _poster_quality_sort_key_missing_last(r, "folder_quality", True),  False),  ### FIX v0.15.0 ###
    "Folder Quality (low→high)":  (lambda r: _poster_quality_sort_key_missing_last(r, "folder_quality", False), True),   ### FIX v0.15.0 ###
    # Fanart Quality (replaces Fanart Size)
    "Fanart Quality (high→low)":  (lambda r: _fanart_quality_sort_key_missing_last(r, "fanart_quality", True),  False),  ### FIX v0.15.0 ###
    "Fanart Quality (low→high)":  (lambda r: _fanart_quality_sort_key_missing_last(r, "fanart_quality", False), True),   ### FIX v0.15.0 ###
    # Backdrops — repositioned here v0.17.0-bug4
    "Backdrops (most)":           (lambda r: r["backdrop_count"],      True),
    "Backdrops (fewest)":         (lambda r: r["backdrop_count"],      False),
    # Language — repositioned after Backdrops v0.18.0             ### NEW v0.18.0 ###
    "Language (A→Z)":             (lambda r: r["language"].lower(),    False),
    "Language (Z→A)":             (lambda r: r["language"].lower(),    True),
    # Video Quality                                                  ### NEW v0.18.0 — renamed from "Quality" ###
    "Video Quality (best first)":   (lambda r: _quality_sort_key(r.get("video_quality","—")), False),  ### NEW v0.18.0 — renamed from "Quality" ###
    "Video Quality (worst first)":  (lambda r: _quality_sort_key(r.get("video_quality","—")), True),   ### NEW v0.18.0 — renamed from "Quality" ###
    # Video Size
    "Video size (lg→sm)":         (lambda r: r["video_bytes"],         True),
    "Video size (sm→lg)":         (lambda r: r["video_bytes"],         False),
    # Lang OK?
    "Lang OK? (Y first)":         (lambda r: _lang_ok_sort_key(r.get("lang_ok","—")), False),  ### FIX v0.15.0 ###
    "Lang OK? (N first)":         (lambda r: _lang_ok_sort_key(r.get("lang_ok","—")), True),   ### FIX v0.15.0 ###
    # ── Multi-column sorts — always at the bottom ──────────────────────────
    "Health (Errors 1st)":        (lambda r: {"red":0,"yellow":1,"green":2}.get(r["row_health"],1), False),  ### NEW v0.16.0 — renamed ###
    "Health (Warning 1st)":       (lambda r: {"yellow":0,"red":1,"green":2}.get(r["row_health"],1), False),  ### NEW v0.15.0 ###
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

def get_video_duration(video_path):                            ### UPDATED v0.17.0 — MP4/MKV fallback ###
    """
    Return video duration in seconds, or None on failure.
    Step 1: Standard JSON format probe.
    Step 2 (MP4/MKV): format=duration plain text.
    Step 3 (MP4/MKV): first video stream duration.
    Step 4 (MP4/MKV): estimate from frame count + frame rate.
    Returns (duration_float, estimated:bool).
    Callers that only need a float may use the first element.
    """
    if not FFPROBE_PATH or not SETTINGS.get("use_ffprobe", True): return None, False

    ext = os.path.splitext(video_path)[1].lower()
    _cflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def _run(cmd, timeout=20):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=timeout, creationflags=_cflags)
            return r.stdout.strip(), r.returncode
        except Exception:
            return "", -1

    # Step 1 — JSON format probe (all containers)
    out, rc = _run([FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
                    "-show_format", video_path])
    if rc == 0 and out:
        try:
            dur = float(json.loads(out).get("format", {}).get("duration", 0) or 0)
            if dur > 0:
                return dur, False
        except Exception:
            pass

    # Steps 2-4 only attempted for MP4 and MKV
    if ext not in (".mp4", ".mkv"):
        return None, False

    # Step 2 — plain-text format duration
    out, rc = _run([FFPROBE_PATH, "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path])
    if rc == 0 and out:
        try:
            dur = float(out.split()[0])
            if dur > 0:
                return dur, False
        except Exception:
            pass

    # Step 3 — first video stream duration
    out, rc = _run([FFPROBE_PATH, "-v", "quiet",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path])
    if rc == 0 and out:
        try:
            dur = float(out.split()[0])
            if dur > 0:
                return dur, False
        except Exception:
            pass

    # Step 4 — estimate from nb_frames / r_frame_rate
    out, rc = _run([FFPROBE_PATH, "-v", "quiet",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=nb_frames,r_frame_rate",
                    "-of", "csv=p=0",
                    video_path])
    if rc == 0 and out:
        try:
            parts = [p.strip() for p in out.split(",") if p.strip()]
            # csv output: nb_frames,r_frame_rate  (may be on separate lines)
            if len(parts) >= 2:
                nb_frames = int(parts[0])
                fps_parts = parts[1].split("/")
                if len(fps_parts) == 2:
                    fps = float(fps_parts[0]) / float(fps_parts[1])
                else:
                    fps = float(fps_parts[0])
                if nb_frames > 0 and fps > 0:
                    return nb_frames / fps, True
        except Exception:
            pass

    # Step 5 — try NFO <runtime> or XML <RunningTime> as last resort
    try:
        sub_dir = os.path.dirname(video_path)
        sub_name = os.path.basename(sub_dir)
        nfo_path = os.path.join(sub_dir, sub_name + ".nfo")
        xml_path = os.path.join(sub_dir, "movie.xml")
        runtime_min = None
        for fpath, tag in [(nfo_path, "runtime"), (xml_path, "RunningTime")]:
            if os.path.isfile(fpath):
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(65536)
                m = re.search(rf"<{tag}[^>]*>([0-9]+)</{tag}>", content, re.IGNORECASE)
                if m:
                    runtime_min = int(m.group(1))
                    break
        if runtime_min and runtime_min > 0:
            return float(runtime_min * 60), True
    except Exception:
        pass

    # All steps failed — return sentinel so caller can use a default estimate
    return None, False

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
        dur_result = get_video_duration(video)                 ### UPDATED v0.17.0 ###
        # get_video_duration now returns (float|None, estimated:bool)
        if isinstance(dur_result, tuple):
            duration, estimated = dur_result
        else:
            duration, estimated = dur_result, False            # legacy compatibility

        if not duration or duration <= 0:
            ext = os.path.splitext(video)[1].lower()
            if ext in (".mp4", ".mkv"):
                # Use a safe default estimate of 3600s and warn rather than abort
                duration  = 3600.0
                estimated = True
                self.after(0, lambda: self.status_var.set(
                    "⚠ FFprobe could not read duration — using 1-hour estimate."))
            else:
                self._finish_error("Cannot read video duration",
                    "FFprobe could not read the video length.\n\n"
                    "Possible causes:\n• Corrupt or incomplete file\n"
                    "• Unsupported container format\n"
                    "• File still being downloaded\n\n"
                    "Try playing the file in VLC to confirm it works.")
                return

        if estimated:
            self.after(0, lambda: self.status_var.set(
                "⚠ Duration estimated — extraction may start at wrong timestamp."))

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
            ### UPDATED v0.18.0 — build file-range string correctly for all cases ###
            if n_ok == 1:
                only_fname = extracted[0][0]
                files_str = only_fname
            elif start_num == 0:
                # First file is backdrop.jpg, rest are backdrop1.jpg … backdropN.jpg
                last_num = n_ok - 1
                files_str = f"backdrop.jpg / backdrop1.jpg → backdrop{last_num}.jpg"
            else:
                files_str = f"backdrop{start_num}.jpg → backdrop{start_num + n_ok - 1}.jpg"
            msg = (f"Done! All {n_frames} frame(s) extracted!\n\n"
                   f"Saved to: {sub}\n"
                   f"Files: {files_str}")
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
        self.title(title); self.geometry("740x480"); self.configure(bg="#1e1e2e")
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
        ### NEW v0.13.0 — "Open File" button lets user open the file directly from the error popup ###
        def _open_file():
            if os.path.isfile(filepath):
                open_in_editor(filepath)
            else:
                messagebox.showwarning("File Not Found",
                                       f"Cannot open file — not found:\n{filepath}", parent=self)
        tk.Button(bf, text="  Open File  ", font=("Helvetica",10,"bold"),
                  bg="#f9e2af", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=_open_file).pack(side="left", padx=(0,8))
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

class RatingsCompareDialog(tk.Toplevel):                        ### NEW v0.15.0 — single-source + use-more-votes ###
    """
    Ratings Sync — Choose Source popup.
    Always shows dual-column TMDb vs OMDb/IMDb view.
    Missing source shows "Not Available" greyed out.
    """
    def __init__(self, parent, movie_name, tmdb_r, tmdb_v, omdb_r, omdb_v,
                 default_apply_all=False, default_use_more_votes=False,
                 show_checkboxes=True):  ### FIX v0.15.0 — hide for single-movie ###
        super().__init__(parent)
        self.title("Ratings Sync — Choose Source")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)
        self.transient(parent); self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)  ### FIX v0.15.0 ###
        self.choice    = None    # "tmdb" | "omdb" | "cancel"
        self.apply_all = False
        self.use_more_votes = False

        tmdb_ok = (tmdb_r is not None)
        omdb_ok = (omdb_r is not None)

        # Auto-select by more votes if requested
        pre_choice = None
        if default_use_more_votes:
            if tmdb_ok and omdb_ok:
                try:
                    tv = int(str(tmdb_v).replace(",","")) if tmdb_v else 0
                    ov = int(str(omdb_v).replace(",","")) if omdb_v else 0
                    if tv > ov:   pre_choice = "tmdb"
                    elif ov > tv: pre_choice = "omdb"
                    else:         pre_choice = "average"
                except Exception:
                    pre_choice = None
            elif tmdb_ok: pre_choice = "tmdb"
            elif omdb_ok: pre_choice = "omdb"

        movie_label = movie_name[:60] + "…" if len(movie_name) > 60 else movie_name
        tk.Label(self, text=movie_label, bg="#1e1e2e", fg="#89b4fa",
                 font=("Helvetica", 10, "bold"), wraplength=460).pack(padx=16, pady=(14, 6))

        # Two-column table
        tbl = tk.Frame(self, bg="#1e1e2e"); tbl.pack(padx=16, pady=(0, 8))
        _hdr_fg = "#89b4fa"; _dim_fg = "#585b70"; _val_fg = "#cdd6f4"
        _bg_ok  = "#1e1e2e"; _bg_dim = "#181825"

        # Header row
        tk.Label(tbl, text="",      bg=_bg_ok, fg=_hdr_fg, font=("Consolas", 9, "bold"), width=10).grid(row=0, column=0, padx=4, pady=2)  ### FIX v0.15.0 ###
        tk.Label(tbl, text="TMDb",  bg=_bg_ok if tmdb_ok else _bg_dim,
                 fg=_hdr_fg if tmdb_ok else _dim_fg,
                 font=("Consolas", 9, "bold"), width=22).grid(row=0, column=1, padx=4, pady=2)
        tk.Label(tbl, text="OMDb/IMDb", bg=_bg_ok if omdb_ok else _bg_dim,
                 fg=_hdr_fg if omdb_ok else _dim_fg,
                 font=("Consolas", 9, "bold"), width=22).grid(row=0, column=2, padx=4, pady=2)

        # Rating row
        tmdb_r_disp = f"{float(tmdb_r):.1f}" if tmdb_ok else "Not Available"
        omdb_r_disp = f"{float(omdb_r):.1f}" if omdb_ok else "Not Available"
        tk.Label(tbl, text="Rating", bg=_bg_ok, fg=_val_fg, font=("Consolas", 9), width=10).grid(row=1, column=0, padx=4, pady=2)
        tk.Label(tbl, text=tmdb_r_disp, bg=_bg_ok if tmdb_ok else _bg_dim,
                 fg=_val_fg if tmdb_ok else _dim_fg,
                 font=("Consolas", 9), width=22).grid(row=1, column=1, padx=4, pady=2)
        tk.Label(tbl, text=omdb_r_disp, bg=_bg_ok if omdb_ok else _bg_dim,
                 fg=_val_fg if omdb_ok else _dim_fg,
                 font=("Consolas", 9), width=22).grid(row=1, column=2, padx=4, pady=2)

        # Votes row                                           ### UPDATED v0.17.0 — comma-formatted votes ###
        def _fmt_votes(v):
            if v is None: return "Not Available"
            try: return f"{int(str(v).replace(',','').replace('.','').strip()):,}"
            except Exception: return str(v)
        tmdb_v_disp = _fmt_votes(tmdb_v) if tmdb_ok else "Not Available"
        omdb_v_disp = _fmt_votes(omdb_v) if omdb_ok else "Not Available"
        tk.Label(tbl, text="Votes", bg=_bg_ok, fg=_val_fg, font=("Consolas", 9), width=10).grid(row=2, column=0, padx=4, pady=2)
        tk.Label(tbl, text=tmdb_v_disp, bg=_bg_ok if tmdb_ok else _bg_dim,
                 fg=_val_fg if tmdb_ok else _dim_fg,
                 font=("Consolas", 9), width=22).grid(row=2, column=1, padx=4, pady=2)
        tk.Label(tbl, text=omdb_v_disp, bg=_bg_ok if omdb_ok else _bg_dim,
                 fg=_val_fg if omdb_ok else _dim_fg,
                 font=("Consolas", 9), width=22).grid(row=2, column=2, padx=4, pady=2)

        # Checkboxes — only for multi-movie runs (C); mutually exclusive (E) ### FIX v0.15.0 ###
        self._apply_all_var  = tk.BooleanVar(value=default_apply_all)
        self._use_votes_var  = tk.BooleanVar(value=default_use_more_votes)
        if show_checkboxes:
            cbf = tk.Frame(self, bg="#1e1e2e"); cbf.pack(padx=16, pady=(0, 6), anchor="w")
            apply_all_cb = tk.Checkbutton(
                cbf, text="Apply this choice to all remaining movies",
                variable=self._apply_all_var, bg="#1e1e2e", fg="#cdd6f4",
                activebackground="#1e1e2e", selectcolor="#313244",
                font=("Helvetica", 9))
            apply_all_cb.pack(anchor="w")
            use_votes_cb = tk.Checkbutton(
                cbf, text="Use the source with more votes",
                variable=self._use_votes_var, bg="#1e1e2e", fg="#cdd6f4",
                activebackground="#1e1e2e", selectcolor="#313244",
                font=("Helvetica", 9))
            use_votes_cb.pack(anchor="w")
            # Mutual exclusion: checking one disables the other (E)     ### FIX v0.15.0 ###
            def _on_apply_all(*_):
                if self._apply_all_var.get():
                    self._use_votes_var.set(False)
                    use_votes_cb.config(state="disabled")
                else:
                    use_votes_cb.config(state="normal")
            def _on_use_votes(*_):
                if self._use_votes_var.get():
                    self._apply_all_var.set(False)
                    apply_all_cb.config(state="disabled")
                else:
                    apply_all_cb.config(state="normal")
            self._apply_all_var.trace_add("write", _on_apply_all)
            self._use_votes_var.trace_add("write", _on_use_votes)
            # Enforce initial state
            if default_apply_all:  _on_apply_all()
            if default_use_more_votes: _on_use_votes()

        # Pre-selection label
        if pre_choice == "average":
            tk.Label(self, text="(Equal votes — average will be used)",
                     bg="#1e1e2e", fg="#fab387", font=("Helvetica", 9)).pack()

        # Buttons                                              ### UPDATED v0.17.0 — added Type Values ###
        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(6, 14))
        tk.Button(bf, text="  Type Values  ", bg="#fab387", fg="#1e1e2e",  ### NEW v0.17.0 ###
                  relief="flat", cursor="hand2",
                  font=("Helvetica", 10, "bold"),
                  command=self._use_manual).pack(side="left", padx=(0, 6))
        tmdb_btn = tk.Button(bf, text="  Use TMDb  ", bg="#89b4fa" if tmdb_ok else "#45475a",
                             fg="#1e1e2e", relief="flat", cursor="hand2" if tmdb_ok else "arrow",
                             state="normal" if tmdb_ok else "disabled",
                             font=("Helvetica", 10, "bold"),
                             command=self._use_tmdb)
        tmdb_btn.pack(side="left", padx=(0, 6))
        omdb_btn = tk.Button(bf, text="  Use OMDb/IMDb  ", bg="#a6e3a1" if omdb_ok else "#45475a",
                             fg="#1e1e2e", relief="flat", cursor="hand2" if omdb_ok else "arrow",
                             state="normal" if omdb_ok else "disabled",
                             font=("Helvetica", 10, "bold"),
                             command=self._use_omdb)
        omdb_btn.pack(side="left", padx=(0, 6))
        tk.Button(bf, text="  Cancel  ", bg="#45475a", fg="#cdd6f4", relief="flat",
                  cursor="hand2", font=("Helvetica", 10),
                  command=self._cancel).pack(side="left")

        self._tmdb_r = tmdb_r; self._tmdb_v = tmdb_v
        self._omdb_r = omdb_r; self._omdb_v = omdb_v
        self._pre_choice = pre_choice
        self.manual_r = None                                   ### NEW v0.17.0 ###
        self.manual_v = None                                   ### NEW v0.17.0 ###
        self._movie_name = movie_name                          ### NEW v0.17.0 ###

        self.bind("<Escape>", lambda e: self._cancel())
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{px+(pw-w)//2}+{py+(ph-h)//2}")

    def _use_manual(self):                                     ### NEW v0.17.0 ###
        dlg = _TypeRatingsDialog(self, self._movie_name)
        self.wait_window(dlg)
        if dlg.result_r is not None and dlg.result_v is not None:
            self.manual_r = dlg.result_r
            self.manual_v = dlg.result_v
            self.choice = "manual"; self.apply_all = self._apply_all_var.get()
            self.use_more_votes = self._use_votes_var.get(); self.destroy()

    def _use_tmdb(self):
        self.choice = "tmdb"; self.apply_all = self._apply_all_var.get()
        self.use_more_votes = self._use_votes_var.get(); self.destroy()

    def _use_omdb(self):
        self.choice = "omdb"; self.apply_all = self._apply_all_var.get()
        self.use_more_votes = self._use_votes_var.get(); self.destroy()

    def _cancel(self):
        self.choice = "cancel"; self.apply_all = False; self.use_more_votes = False
        self.destroy()


class _TypeRatingsDialog(tk.Toplevel):                         ### NEW v0.17.0 ###
    """Small modal popup: user types a rating (0.0–10.0) and vote count."""

    def __init__(self, parent, movie_name):
        super().__init__(parent)
        self.title("Type Values")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)
        self.transient(parent); self.grab_set()
        self.result_r = None   # float | None
        self.result_v = None   # int   | None

        movie_label = movie_name[:60] + "…" if len(movie_name) > 60 else movie_name
        tk.Label(self, text=movie_label, bg="#1e1e2e", fg="#89b4fa",
                 font=("Helvetica", 10, "bold"), wraplength=360).pack(padx=20, pady=(14, 4))
        tk.Label(self, text="Enter rating and vote count to apply manually.",
                 bg="#1e1e2e", fg="#a6adc8",
                 font=("Helvetica", 9)).pack(padx=20, pady=(0, 8))

        gf = tk.Frame(self, bg="#1e1e2e"); gf.pack(padx=20, pady=4)
        tk.Label(gf, text="Rating (0.0 – 10.0):", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Helvetica", 9), anchor="e", width=20).grid(row=0, column=0, padx=(0,6), pady=6)
        self._r_var = tk.StringVar()
        tk.Entry(gf, textvariable=self._r_var, width=12,
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 font=("Consolas", 10), relief="flat").grid(row=0, column=1, pady=6)

        tk.Label(gf, text="Votes (integer):", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Helvetica", 9), anchor="e", width=20).grid(row=1, column=0, padx=(0,6), pady=6)
        self._v_var = tk.StringVar()
        tk.Entry(gf, textvariable=self._v_var, width=12,
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 font=("Consolas", 10), relief="flat").grid(row=1, column=1, pady=6)

        self._err_lbl = tk.Label(self, text="", bg="#1e1e2e", fg="#f38ba8",
                                  font=("Helvetica", 8))
        self._err_lbl.pack()

        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(4, 16))
        tk.Button(bf, text="  OK  ", bg="#a6e3a1", fg="#1e1e2e",
                  relief="flat", cursor="hand2",
                  font=("Helvetica", 10, "bold"),
                  command=self._ok).pack(side="left", padx=6)
        tk.Button(bf, text="  Cancel  ", bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  font=("Helvetica", 10),
                  command=self.destroy).pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{px+(pw-w)//2}+{py+(ph-h)//2}")

    def _ok(self):
        r_str = self._r_var.get().strip().replace(",", ".")
        v_str = self._v_var.get().strip().replace(",", "")
        try:
            r_val = float(r_str)
            if not (0.0 <= r_val <= 10.0):
                raise ValueError("out of range")
        except ValueError:
            self._err_lbl.configure(text="Rating must be a number between 0.0 and 10.0.")
            return
        try:
            v_val = int(v_str)
            if v_val < 0:
                raise ValueError("negative")
        except ValueError:
            self._err_lbl.configure(text="Votes must be a non-negative integer.")
            return
        self.result_r = r_val
        self.result_v = v_val
        self.destroy()


class CustomGenreDialog(tk.Toplevel):                           ### NEW v0.15.0 ###
    """Ask user whether to delete custom genres for a specific movie."""
    def __init__(self, parent, movie_name, custom_genres):
        super().__init__(parent)
        self.title("Custom Genres Found")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)
        self.transient(parent); self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._no)  ### FIX v0.15.0 ###
        self.delete_custom = None   # True = delete, False = keep
        movie_label = movie_name[:60] + "…" if len(movie_name) > 60 else movie_name
        tk.Label(self, text=f"Movie: {movie_label}",
                 bg="#1e1e2e", fg="#89b4fa", font=("Helvetica", 10, "bold"),
                 wraplength=380).pack(padx=16, pady=(14, 4))
        genre_list = ", ".join(custom_genres[:8])
        if len(custom_genres) > 8: genre_list += f" … (+{len(custom_genres)-8} more)"
        tk.Label(self, text=f"Custom genre(s) found:\n  {genre_list}",
                 bg="#1e1e2e", fg="#f38ba8", font=("Helvetica", 9),
                 wraplength=380, justify="left").pack(padx=16, pady=(0, 10))
        tk.Label(self, text="Delete the Custom Genre(s)?",
                 bg="#1e1e2e", fg="#cdd6f4", font=("Helvetica", 10)).pack(padx=16, pady=(0, 10))
        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(0, 14))
        tk.Button(bf, text="  Yes  ", bg="#f38ba8", fg="#1e1e2e", font=("Helvetica", 10, "bold"),
                  relief="flat", cursor="hand2",
                  command=self._yes).pack(side="left", padx=(0, 8))
        tk.Button(bf, text="  No  ", bg="#a6e3a1", fg="#1e1e2e", font=("Helvetica", 10, "bold"),
                  relief="flat", cursor="hand2",
                  command=self._no).pack(side="left")
        self.bind("<Return>", lambda e: self._no())
        self.bind("<Escape>", lambda e: self._no())
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{px+(pw-w)//2}+{py+(ph-h)//2}")

    def _yes(self): self.delete_custom = True;  self.destroy()
    def _no(self):  self.delete_custom = False; self.destroy()


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
    Full application help — rebuilt for v0.15.0.      ### NEW v0.15.0 ###
    Eight tabs covering all features and new v0.15.0 additions.
    """

    def __init__(self, parent, tab=0):          ### NEW v0.16.0 — tab parameter ###
        super().__init__(parent)
        self.title(f"Help — {APP_NAME}  v{APP_VERSION}")
        self.geometry("860x680")
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

        self._add_tab(nb, "🚀  Getting Started",   self._TAB_START)    ### NEW v0.15.0 ###
        self._add_tab(nb, "📊  Table & Columns",   self._TAB_TABLE)    ### NEW v0.15.0 ###
        self._add_tab(nb, "🖱  Actions & Tools",   self._TAB_ACTIONS)  ### NEW v0.15.0 ###
        self._add_tab(nb, "⭐  Ratings & Genres",      self._TAB_RATINGS)  ### NEW v0.15.0 ###
        self._add_tab(nb, "🎵  Audio & Images",    self._TAB_AUDIO)    ### NEW v0.15.0 ###
        self._add_tab(nb, "⚙️  Settings",        self._TAB_SETTINGS)
        self._add_tab(nb, "⌨  Shortcuts & Help",      self._TAB_SHORTCUTS)
        self._add_tab(nb, "📋  Version History",  self._TAB_VERSION)   ### NEW v0.16.0 ###
        self._add_about_tab(nb)

        # Select requested tab (0-based index)               ### NEW v0.16.0 ###
        tabs = nb.tabs()
        if 0 <= tab < len(tabs):
            nb.select(tabs[tab])

        tk.Button(self, text="  Close  ", font=("Helvetica",10,"bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self.destroy).pack(pady=(6,12))

    # ── Tab content strings ───────────────────────────────────────────────────────────────────────

    _TAB_START = """─────────────────────────────────────────
  Metadata & MediaClinic  -  Getting Started
─────────────────────────────────────────

WHAT IS THIS APP?
  Metadata & MediaClinic is a KODI / Emby / Jellyfin media library
  auditor and repair tool. It scans a root media folder, checks every
  artwork file, metadata file, and video, then presents a colour-coded
  health table so you can see at a glance what is missing or broken.

  One subfolder = one movie. Each subfolder should contain:
    • poster.jpg       - portrait cover art (2:3 ratio)
    • folder.jpg       - identical copy of poster.jpg for KODI
    • fanart.jpg       - wide background art (16:9 ratio)
    • backdrop.jpg, backdrop1.jpg ...  - scene frames
    • MovieName.nfo    - KODI metadata in XML format
    • movie.xml        - Emby/Jellyfin metadata in XML format
    • MovieName.mkv    (or .mp4, .avi, etc.)

─────────────────────────────────────────
FIRST RUN
─────────────────────────────────────────

  1. Click  Browse...  and select your root media folder.
  2. Click  Scan.
     The table fills in phases: subfolders first, then images,
     then metadata, then video (with FFprobe if enabled).
  3. Each row shows the health of one movie:
       GREEN row   - all key files present and valid
       YELLOW row  - one or more files missing, or warnings present
       RED row     - a file has a structural error
  4. Your last scan is saved automatically and restored on startup.

─────────────────────────────────────────
QUICK-START CHECKLIST
─────────────────────────────────────────

  • Set your FFmpeg path in Settings → Tools
    (enables video analysis and backdrop extraction)

  • Add TMDb and/or OMDb API keys in Settings → API Keys
    (enables online ratings sync)

  • Configure your preferred browser in Settings → Browser

  • Set the "Lang OK?" language target in Settings → Language OK?
    (default: PT - Portuguese)

  • Run a scan, sort by "Health (errors 1st)" to triage problems.

─────────────────────────────────────────
STATUS ICONS
─────────────────────────────────────────

  ⬤   OK / valid / present
  ◐   Warning - conflict, proportion mismatch, or minor issue
  ○   File missing
  ✕   Error - parse error or corrupt data

─────────────────────────────────────────
ROW COLOURS
─────────────────────────────────────────

  GREEN   - All required files present and valid; one video file.
  YELLOW  - Something missing or a non-blocking warning exists.
  RED     - Hard error: XML/NFO parse error, corrupt image, etc.

─────────────────────────────────────────
AUTOMATIC BACKUPS
─────────────────────────────────────────

  Whenever the app modifies a .nfo or .xml file it creates a silent
  backup before writing. Backups go in:

    backup/backup_MovieName_YYYY-MM-DD_HH-MM-SS/

  No popup is shown. Check logs/app.log for a full backup record.
"""

    _TAB_TABLE = """─────────────────────────────────────────
  Table & Columns
─────────────────────────────────────────

COLUMN REFERENCE

  Movie Name   - Title from NFO <title> or XML <Title>.
                 Double-click opens the movie folder.

  Year         - Year from NFO <year> or XML <ProductionYear>.

  Genres       - Genres from NFO <genre> tags. Double-click opens .nfo.
                 Hover shows each genre and its validation status.

  Rating       - Rating from NFO <rating>, XML <IMDBrating>, or <Rating>.
                 Icon: ⬤ OK, ◐ conflict. Hover shows Rating, Votes, Source.

  Poster       - Status and quality tier of poster.jpg (2:3 portrait).
                 Hover shows dimensions, size, ratio, quality tier.

  Folder       - Status and quality tier of folder.jpg.
                 Should be an identical copy of poster.jpg.

  Fanart       - Status and quality tier of fanart.jpg (16:9 landscape).
                 Hover shows dimensions, size, ratio, quality tier.

  Backdrops    - Count of backdrop images found. Hover shows count and
                 average file size in KB.

  .nfo         - Status of the .nfo metadata file.
  .xml         - Status of the movie.xml metadata file.

  Language     - Language from XML <Language>.

  Video        - Video container format (MKV, MP4, AVI, etc.).
  Video Size   - Video file size on disk.
  Quality      - Video resolution class (FFprobe).

  Audio        - Audio tracks from FFprobe.
                 Format: EN (5.1), PT (2.0)
                 Hover shows full per-track details.
                 Only populated during FFprobe scans.

  Lang OK?     - Y/N: target language audio or subtitle present.
                 Set target language in Settings → Language OK?.

  Subtitles    - Embedded tracks (FFprobe) and external .srt files.

─────────────────────────────────────────
IMAGE QUALITY TIERS
─────────────────────────────────────────

  Poster / Folder (2:3 portrait):
    4K      - 2000×3000 or above
    1440p   - 1500×2250 or above
    1080p   - 1000×1500 or above
    720p    - 666×1000 or above
    540p    - 540×810 or above
    480p    - 480×720 or above
    360p    - 360×540 or above (floor — absorbs all below)

  Fanart (16:9 landscape):
    4K      - 3840×2160 or above
    1440p   - 2560×1440 or above
    1080p   - 1920×1080 or above
    720p    - 1280×720 or above
    540p    - 960×540 or above
    480p    - 854×480 or above
    360p    - 640×360 or above (floor — absorbs all below)

─────────────────────────────────────────
HOVER TOOLTIPS
─────────────────────────────────────────

  Every column has a hover tooltip.
  Missing image files show:  Expected: C:\\Filmes\\Movie\\poster.jpg
  All "Expected:" paths use Windows-style backslashes.
"""

    _TAB_ACTIONS = """─────────────────────────────────────────
  Actions
─────────────────────────────────────────

DOUBLE-CLICK ACTIONS

  Column        Opens...
  ----------    -----------------------------------------------
  Movie Name    Movie folder in Windows Explorer
  Genres        .nfo file in your configured text editor
  Rating        .nfo file in your configured text editor
  Votes         .nfo file in your configured text editor
  Source        Popup to choose IMDB or TMDB website
  Poster        poster.jpg in your default image viewer
  Folder        folder.jpg in your default image viewer
  Fanart        fanart.jpg in your default image viewer
  Backdrops     First backdrop image
  NFO           Parse error dialog or editor
  XML           Parse error dialog or editor
  Language      movie.xml in editor
  Video         Plays the video
  Quality       Plays the video
  Subtitles     Subtitle tracks dialog

─────────────────────────────────────────
RIGHT-CLICK MENU (SINGLE MOVIE)
─────────────────────────────────────────

  Open Folder           - Open the movie folder in Windows Explorer
  Open poster.jpg       - Open poster.jpg in your image viewer
  Open folder.jpg       - Open folder.jpg in your image viewer
  Open fanart.jpg       - Open fanart.jpg in your image viewer
  Play video            - Play the movie in your default player
  Extract Backdrop(s)   - Extract backdrop frames from video
  Subtitles...          - Show subtitle tracks dialog
  Open .nfo             - Open the .nfo file in your editor
  Open movie.xml        - Open movie.xml in your editor
  Open on IMDB          - Open IMDB page in your browser
  Open on TMDb          - Open TMDb page in your browser
  Open on OpenSubtitles.org
  Copy Movie Name       - Copy the title to clipboard
  Open in Scraper       - Open folder in your configured scraper

  Run Improvements Check
  Sync Ratings          - Fetch rating/votes from TMDb + IMDb
  Normalize Sources     - Repair IMDB/TMDB tags in XML/NFO
  Search Sources        - Search TMDB online by title + year
  Normalize Genres      - Fix capitalisation, synonyms, duplicates
  Fetch Poster/Folder   - Compare and replace poster from TMDB
  Fetch Fanart          - Compare and replace fanart from TMDB
  ──────────────────
  Update (no FFprobe)   - Re-scan metadata without FFprobe
  Update (with FFprobe) - Full re-scan including video analysis
  Refresh Icons         - Redraw status icons

─────────────────────────────────────────
RIGHT-CLICK MENU (MULTI-SELECTION)
─────────────────────────────────────────

  Multi-selection batch versions appear for:
    Sync Ratings (N movies)
    Normalize Sources (N movies)
    Search Sources (N movies)
    Normalize Genres (N movies)
    Fetch Poster/Folder (N movies)
    Fetch Fanart (N movies)
    Update (no FFprobe) (N movies)
    Update (with FFprobe) (N movies)

  Select multiple rows with Ctrl+click or Shift+click.

─────────────────────────────────────────
TOOLS MENU (BATCH OPERATIONS)
─────────────────────────────────────────

  All batch operations run in a background thread. A progress window
  shows percentage complete. Press Cancel or ESC to stop at any time.
  All file modifications create silent backups before writing.

  Save Scan Results
    Save the current scan results to a JSON file.

  Open Scan Results
    Load a previously saved JSON scan file.
    On parse error, shows a popup and leaves current results unchanged.

  Sync Ratings Online — All Movies
    Fetches updated ratings from TMDb and/or OMDb for every scanned
    movie. Shows the Ratings Sync popup for each movie.

  Normalize Sources — All Movies
    Runs Normalize Sources for all movies with ◐ or ○ in the Source
    column. Backs up XML/NFO before writing.

  Search Sources — All Movies
    Searches TMDB for every movie using title + year.
    Shows grouped results popup with Export TXT option.

  Normalize Genres — All Movies
    Normalises genre tags in all movies. Asks confirmation first.

  Run Improvements Check — All Movies
    Analyses all movies for metadata issues. Saves a report to a
    user-chosen .txt file. Appends results incrementally.

  Refresh Icons — All Movies
    Redraws all status icons in the table.

  Delete All extrafanart Subfolders (legacy)
    Deletes the "extrafanart" subfolder from every movie folder.
    Creates a backup of folder contents before deleting.
    Asks confirmation before starting.
"""

    _TAB_RATINGS = """─────────────────────────────────────────
  Ratings Sync
─────────────────────────────────────────

OVERVIEW

  Ratings Sync fetches updated ratings and vote counts from TMDb
  and/or OMDb/IMDb and writes them to your NFO and XML files.

  Requires API keys in Settings → API Keys.

HOW TO SYNC

  Single movie:     Right-click → Sync Ratings from IMDb / TMDb
  Selected movies:  Right-click → Sync Ratings (N movies)
  All movies:       Tools → Sync Ratings Online - All Movies

─────────────────────────────────────────
RATINGS SYNC POPUP
─────────────────────────────────────────

  The popup always shows a dual-column comparison: TMDb vs OMDb/IMDb.
  Previously only shown when both sources had data; now always shown.

  If only one source has data:
    • The missing source shows "Not Available" in grey.
    • The button for the missing source is disabled.

  Rating: shown to one decimal place.
  Votes: shown as an integer.

  Checkbox: Apply this choice to all remaining movies
    Your selection is applied to all subsequent movies in the batch
    without asking again. Useful for large batch syncs.

  Checkbox: Use the source with more votes
    Automatically pre-selects the source with the higher vote count.
    Equal votes: uses the average of the two ratings.
    You can still override the pre-selection before confirming.

  These defaults can be set permanently in:
    Settings → Ratings → Ratings Synchronization Options

─────────────────────────────────────────
RATING HOVER TOOLTIP
─────────────────────────────────────────

  Hovering over the Rating cell shows:

    Rating: 7.3
    Votes: 42185
    Source: NFO (<rating>, <votes>)

  Source line examples:
    NFO (<rating>, <votes>)
    XML (<IMDBrating>, <Votes>)
    XML (<Rating>) and NFO (<votes>)
    XML (<IMDBrating>), no vote information found

  If multiple tags hold different values, the cell shows ◐ (warning)
  and the tooltip notes the conflict.

  Votes extraction priority:
    1. NFO <votes>
    2. XML <Votes>
    3. XML <VoteCount>

─────────────────────────────────────────
NORMALIZE GENRES
─────────────────────────────────────────

OVERVIEW

  Normalize Genres standardises genre tags across NFO and XML files:
    • Fixes capitalisation  (e.g. "action" → "Action")
    • Resolves synonyms     (e.g. "Sci-Fi" → "Science Fiction")
    • Removes duplicates
    • Splits merged tags    (e.g. "Family/Fantasy" → Family + Fantasy)
      Splitting uses: / \\ | , ;

HOW TO NORMALISE

  Single movie:   Right-click → Normalize Genres
  Multiple:       Right-click → Normalize Genres (N movies)
  All movies:     Tools → Normalize Genres - All Movies

CUSTOM GENRES

  A genre is standard only if it appears in the Standard Genre List
  (Settings → Genres). Any other genre is "custom".

  When custom genres are found for a movie, you are asked:

    Delete the Custom Genre(s)?  [Yes]  [No]

    Yes — removes custom genres; keeps normalised standard ones only.
    No  — keeps custom genres unchanged; normalises standard genres.

  This dialog appears once per movie. Each movie is processed
  independently (no shared state across multiple selections).

WHAT IS WRITTEN

  Normalised genres are written to both .nfo and movie.xml.
  A silent backup is created before any write.
"""

    _TAB_AUDIO = """─────────────────────────────────────────
  Audio Column
─────────────────────────────────────────

OVERVIEW

  The Audio column shows audio tracks detected by FFprobe.
  It is only populated during FFprobe-enabled scans.

COLUMN FORMAT

  Each track shows:  LANGUAGE (CHANNELS)
  Multiple tracks are comma-separated and sorted alphabetically.
  Languages are uppercase ISO codes.

  Examples:
    EN (5.1)
    EN (5.1), PT (2.0)
    EN (7.1), FR (5.1), DE (2.0)

HOVER TOOLTIP

  Audio Tracks: 2

  Track 1:
  Language: EN
  Codec: AC3
  Channels: 5.1
  Bitrate: 640 kbps

  Track 2:
  Language: PT
  Codec: AAC
  Channels: 2.0
  Bitrate: 192 kbps

  Missing bitrate shows: Bitrate: Unknown
  Missing language tag shows: Language: Unknown

NOTE
  Audio data is not updated during "Update (no FFprobe)" rescans.
  Use "Update (with FFprobe)" to refresh audio track information.

─────────────────────────────────────────
SUBTITLES
─────────────────────────────────────────

  The Subtitles column shows:
    • Embedded tracks detected by FFprobe  (Int: EN, PT ...)
    • External .srt files in the movie folder  (Ext: pt.srt ...)

  The Lang OK? column (Y/N) checks for the configured target language
  in audio streams, embedded subs, or external subs.

─────────────────────────────────────────
BACKDROPS & IMAGES
─────────────────────────────────────────

BACKDROP HOVER TOOLTIP

  Hovering the Backdrops cell now shows:
    Backdrops: N image files
    Average Size: Xkb

EXTRACTING BACKDROPS

  Right-click → Extract Backdrop(s) to extract frames from video.
  Requires FFmpeg in Settings → Tools.
  The extract count is set in Settings → Image Sizes.

IMAGE MISSING PATHS

  When an image is missing, the tooltip shows:
    Expected: C:\\Filmes\\MovieName\\poster.jpg
  All paths use Windows-style backslashes.

PROPORTION CHECKS

  Poster / Folder: expected 2:3 portrait ratio.
  Fanart:          expected 16:9 landscape ratio.
  ◐ indicates a proportion warning (non-blocking).

  Settings → Image Sizes → Accept 3:4 ratio (poster/folder)
  Settings → Image Sizes → Accept 16:8 ratio (fanart)

─────────────────────────────────────────
SORTING
─────────────────────────────────────────

  Use the Sort dropdown to re-order the table. Sort is stable.

  Movie Name sorts are accent-insensitive:  A, Á, Â all sort as A.

  Available sort options:
    Movie Name (A-Z) / (Z-A)
    Year (older first) / (newer first)
    Genre (A-Z) / (Z-A)
    Rating (high→low) / (low→high)
    Votes (high→low) / (low→high)
    Poster / Folder / Fanart Quality (high→low) / (low→high)
    Video size (lg→sm) / (sm→lg)
    Language (A→Z) / (Z→A)
    Quality (best first) / (worst first)
    Lang OK? (Y first) / (N first)
    Backdrops (most) / (fewest)
    Health (Errors 1st)   - RED rows at top
    Health (Warning 1st)  - YELLOW rows at top
    Health (OK 1st)       - GREEN rows at top
"""

    _TAB_SETTINGS = """─────────────────────────────────────────
  Settings Reference
─────────────────────────────────────────

TOOLS TAB

  Text Editor     - Path to your editor (e.g. Notepad++).
  FFmpeg path     - Folder containing ffmpeg.exe and ffprobe.exe.
                    Required for video analysis and backdrop extraction.
  Scraper path    - Path to your media scraper (optional).
  Extract timeout - Max seconds per backdrop extraction (5-600 s).
  Use FFprobe     - Enable/disable video analysis per scan.

─────────────────────────────────────────
API KEYS TAB
─────────────────────────────────────────

  TMDb API Key    - Required for TMDb ratings sync.
  OMDb API Key    - Required for OMDb/IMDb ratings sync.
  Metadata source - Choose TMDb or OMDb as the default source.

  Get a free TMDb key at: themoviedb.org/settings/api
  Get a free OMDb key at: omdbapi.com/apikey.aspx

─────────────────────────────────────────
BROWSER TAB
─────────────────────────────────────────

  Select your preferred browser for web links.
  Changing the browser does NOT trigger a rescan prompt.

─────────────────────────────────────────
LANGUAGE OK? TAB
─────────────────────────────────────────

  ISO 639-1 language code for the Lang OK? column. Default: PT.
  Y shown if target language found in: FFprobe audio, embedded subs,
  external .srt files, XML <Language>, or NFO language tags.

─────────────────────────────────────────
IMPROVEMENTS TAB
─────────────────────────────────────────

  Toggle improvement checks:
    • Large XML/NFO files     - flag files above size threshold
    • NFO <→ XML mismatches  - detect conflicting data
    • FFprobe vs NFO/XML      - detect resolution/codec discrepancies
    • poster.jpg vs folder.jpg - detect size differences
    • Image proportions       - flag non-standard aspect ratios
    • Insufficient backdrops  - flag too few backdrop frames

  Max NFO/XML size (KB) and Min backdrops count configured here.

─────────────────────────────────────────
IMAGE SIZES TAB
─────────────────────────────────────────

  Quality levels for poster/folder/fanart (minimum acceptable tier).
  Accept 16:8 ratio      - allow slightly wider fanart without warning.
  Accept 3:4 ratio       - allow 3:4 poster/folder without warning.
  Backdrop count         - how many backdrops to extract per movie.
  Min size (KB)          - flag files below this threshold.

─────────────────────────────────────────
RATINGS TAB
─────────────────────────────────────────

  Apply this choice to all remaining movies
    Default state for the "Apply to all" checkbox in the Ratings Sync
    popup. When on, your first choice is applied to all batch movies.

  Use the source with more votes
    Default for the "Use more votes" checkbox. When on, the source
    with the higher vote count is pre-selected. Equal votes: average.

─────────────────────────────────────────
GENRES TAB
─────────────────────────────────────────

  The Standard Genre List defines which genres are standard.
  Genres not in this list are treated as custom during Normalize Genres.
  "Reset to TMDb defaults" reloads the standard TMDb genre list.

─────────────────────────────────────────
NFO / XML TAGS TAB
─────────────────────────────────────────

  Defines NFO/XML tag pairs for the mismatch improvement check.
  Each pair: NFO dot-path, XML dot-path, human label, tolerance %.

─────────────────────────────────────────
USER INTERFACE TAB
─────────────────────────────────────────

  Show header tooltips, alternating rows, compact mode,
  dark theme, auto-fit columns, show image size in cells.

─────────────────────────────────────────
BACKUP TAB
─────────────────────────────────────────

  Max backup size (MB) - oldest backups deleted when limit exceeded.
  Set to 0 to disable automatic cleanup.
"""

    _TAB_SHORTCUTS = """─────────────────────────────────────────
  Keyboard Shortcuts
─────────────────────────────────────────

  F1              - Open Help
  F5              - Start Scan
  Ctrl+S          - Start Scan
  Ctrl+L          - Clear All results
  Ctrl+E          - Export results to CSV
  Ctrl+I          - Refresh All Icons
  Ctrl+A          - Select all rows
  Escape          - Cancel scan in progress

  A-Z, 0-9        - Jump to next movie starting with that character

  Double-click    - Action depends on column (see Actions & Tools tab)
  Right-click     - Context menu for selected row(s)
  Shift+click     - Select a range of rows
  Ctrl+click      - Add individual rows to selection

─────────────────────────────────────────
TROUBLESHOOTING
─────────────────────────────────────────

  Settings shows only a few tabs or tabs are empty
    Fixed in a previous version (broken _DEFAULTself reference).
    Ensure you are running the latest version.

  Audio column is empty
    Requires FFprobe. Enable "Use FFprobe" in Settings → Tools, then
    run "Update (with FFprobe)" on affected movies.

  Rating tooltip shows no Votes or Source
    The NFO/XML files may not contain vote tags.
    Run "Sync Ratings Online" to fetch and write the latest data.

  Backdrop extraction produces no files
    Ensure FFmpeg is configured in Settings → Tools.
    Increase "Extract timeout" for large video files.

  Genres not normalising correctly
    Check your Standard Genre List in Settings → Genres.
    Genres not in the list are treated as custom.

  Sort order looks wrong for accented characters
    Sorting is accent-insensitive: A, Á, Â all sort as A.

  Expected: paths show forward slashes
    Fixed in a previous version. All Expected: paths now use backslashes.

  Application log
    All operations logged to logs/app.log next to the script.
    Check for detailed errors and backup records.

─────────────────────────────────────────
CREDITS
─────────────────────────────────────────

  Metadata & MediaClinic is developed by Luiz Junqueira with Claude AI.
  Built to keep KODI / Emby / Jellyfin media libraries clean,
  complete, and metadata-perfect.

  Full version history: Help → Version History
"""

    ### NEW v0.16.0 — Version History tab (moved from _TAB_SHORTCUTS) ###
    _TAB_VERSION = """─────────────────────────────────────────
  Version History  —  Metadata & MediaClinic
─────────────────────────────────────────

  v0.17.0 - NEW: Fetcher Backdrops — download and manage TMDB backdrops per movie.
             NEW: Column resize no longer shrinks adjacent columns.
             FIX: Help tab titles and headers stripped of version numbers.
             NEW: Scan renamed Full Scan (Rebuild Library) with tooltip.
             NEW: Update Scan renamed Quick Scan (Update Library) with tooltip.
             NEW: Sort options Sources (Errors 1st) and Sources (OK 1st).
             NEW: Ratings Sync — Type Values button for manual rating/votes entry.
             NEW: Ratings Sync — opens even when no TMDB/IMDb ID present.
             NEW: Votes formatted with comma separators in Ratings Sync popup.
             NEW: Progress popup for batch operations (Tools menu + multi-select ≥10).
             NEW: Extrafanart deletion — preview list + backup + progress popup.
             FIX: Normalize Sources — TMDB ID tag insertion and IMDb bare <id> write.
             FIX: FFprobe duration fallback (MP4/MKV) — 4-step chain + default estimate.
             FIX: Shift+Up now correctly shrinks selection instead of resetting block.
             FIX: Jump-to-letter — relaxed focus guard so keypress fires reliably.

  v0.16.1 - NEW: Default sort always Movie Name (A-Z) on startup, scan, folder
                 open, and load scan results.
             FIX: Shift+Arrow selection rewritten to Windows Explorer behaviour.
                 Anchor stays fixed; only moving end changes. Shift+Up now
                 correctly shrinks selection instead of moving entire block.
             NEW: Image quality tiers updated to 7-tier system (4K → 360p).
                 Poster/folder: 4K/1440p/1080p/720p/540p/480p/360p.
                 Fanart: 4K/1440p/1080p/720p/540p/480p/360p.
                 360p absorbs all images below threshold (no more "Below" label).
             MIGRATE: Old tier labels auto-migrated on settings load:
                 Standard (HD) → 1080p, Full HD → 1080p, Retina/QHD → 1440p,
                 Ultra (4K) → 4K, Optimized → 720p, Thumbnail → 360p.
             VERSION: 0.16.0 → 0.16.1.

───────────────────────────────────────── (between Rating and Source).
                 Counts votes from NFO <votes> / XML <Votes> / <VoteCount>.
                 Icon: ⬤ match  ◐ conflict  ○ missing  ✕ error.
             NEW: Source column (IMDB + TMDB IDs across all 12 tags).
                 Double-click to open IMDB or TMDB website.
                 Red row if any source tag is unreadable.
             NEW: Right-click → Normalize Sources.
                 Case A: auto-fill missing tags when remaining agree.
                 Case B: popup to choose correct ID when tags disagree.
                 Case C: prompt to type ID when all tags missing.
                 Backs up XML/NFO before writing. Multi-selection supported.
             NEW: Right-click → Search Sources.
                 Queries TMDB search by title + year.
                 Extracts TMDB ID and IMDB ID from results.
                 Shows grouped popup with Export TXT option.
             NEW: Right-click → Fetch Poster/Folder.
                 Compares local poster with TMDB poster images.
                 Downloads at full TMDB resolution. Backs up existing files.
                 Grayed out when no TMDB API key or no TMDB ID.
             NEW: Right-click → Fetch Fanart.
                 Same as Fetch Poster/Folder but for fanart/backdrops.
             NEW: Tools → Save Scan Results / Open Scan Results.
                 Save and reload full scan to/from JSON.
             NEW: Tools → Normalize Sources — All Movies.
                 Runs Normalize Sources for all ◐ or ○ movies.
             NEW: Tools → Search Sources — All Movies.
                 Searches TMDB for every movie; grouped results popup.
             NEW: Normalize Genres — language intelligence.
                 Detects genres in PT, DE, FR, ES, IT, RU, ZH, AR
                 and translates to English before normalizing.
             FIX: Rating column — votes conflict removed from rating status.
                  Rating ◐ now means rating values differ (not votes).
             RENAME: "Health (errors 1st)" → "Health (Errors 1st)".
             SORT: Votes (high→low) and Votes (low→high) added.
             NEW: Help → Version History (this tab).
             VERSION: 0.15.0 → 0.16.0.

─────────────────────────────────────────

  v0.15.0 - Rating tooltip: Votes count and Source description.
             Audio column: FFprobe audio tracks with hover details.
             Normalize Genres: custom genre dialog per movie,
               per-movie isolation fix (no shared state).
             Backdrops tooltip: count and average file size.
             Expected: paths normalized to backslashes.
             Settings tabs bug fix (Improvements + Genres tabs).
             New Ratings Settings tab (sync defaults).
             Enhanced Ratings Sync popup: always dual-column,
               "Not Available" for missing source, "Use more votes".
             Tools menu redesigned with batch operations.
             Right-click: renamed image entries.
             Sort fixes: quality columns and Lang OK? were inverted.
             New "Health (Warning 1st)" sort option.
             Accent-insensitive movie name sorting.
             Help system fully rewritten.

  v0.14.0 - Settings subsystem split into 4 dedicated modules.
             FFmpeg test and browser detection run off UI thread.
             Snapshot logic upgraded to structured dict.
             New: settings_schema.json, CLAUDE_RULES.md, test harness.

  v0.13.1 - Browser change no longer triggers rescan prompt.
             Normalize Genres splits merged tags on / \\ | , ;.
             Keyboard jump-to-letter in table (A-Z / 0-9).

  v0.13.0 - Browser tab selected row visually highlighted.
             Rescan popup centered on parent window.
             Settings save no longer freezes UI (wait_window removed).
             NFO/XML error popup includes "Open File" button.
             Status bar always recalculated after every scan path.

  v0.12.0 - Poster/Folder/Fanart columns merged (icon + quality label).
             Rating column between Genres and Poster.
             Backup tab with auto-cleanup of oldest backups.
             3:4 ratio acceptance toggle for poster/folder.
             Right-click "Add Custom Genre(s)" to Settings.
             Compact mode and dark theme toggle in User Interface tab.

  v0.11.0 - Silent backup before any NFO/XML write.
             FFprobe data persists across no-FFprobe re-validates.
             Image quality tier system (resolution-based).
             Fanart 16:8 acceptance toggle.
             Help menu moved to last position; F1 opens Help globally.
             Sort menu redesigned: quality-based sorts, Folder Quality.

  v0.10.x - COLUMN_MODEL architecture (single source of truth).
             settings_dialog.py extracted from main file.
             Series tab stub added.
             All Phase A bug fixes: Genre column, Year column,
             Clear All button, alternating rows, richer status bar,
             keyboard shortcuts, NFO/XML pre-validation.

  v0.9.0  - Online Ratings Sync (TMDb + OMDb), side-by-side dialog.
             Genre column + Normalize Genres action.
             Improvements report with scan error appending.
             API Keys (TMDb + OMDb) with validation.
             Browser selection with auto-detection.
             Image minimum sizes (KB thresholds).
             Genre list editable in Settings.

  v0.8.0  - Settings menu, Improvements engine, IMDB/TMDb links.
             Auto-size columns, FFprobe checkbox, language column.
             Backdrop progress, Shift+select multi-selection.

  v0.7.0  - Quality column (576p/DVD), PT OK?, persistent sessions.

  v0.6.x  - Original release.
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
        t.tag_configure("hdr",  foreground="#89b4fa", font=("Helvetica",10,"bold"))
        t.tag_configure("sep",  foreground="#45475a")
        t.tag_configure("key",  foreground="#f9e2af")
        t.tag_configure("ok",   foreground="#a6e3a1")
        t.tag_configure("body", foreground="#cdd6f4")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("─"):
                t.insert("end", line + "\n", "sep")
            elif stripped and stripped == stripped.upper() and len(stripped) > 4 and not stripped.startswith("•"):
                t.insert("end", line + "\n", "hdr")
            elif stripped.startswith("•"):
                t.insert("end", line + "\n", "ok")
            elif "→" in line or "—" in line[:30]:
                t.insert("end", line + "\n", "key")
            else:
                t.insert("end", line + "\n", "body")
        t.configure(state="disabled")

    def _add_about_tab(self, nb):
        ### UPDATED v0.16.0 — About tab shows app identity only; version history moved to Version History tab ###
        frame = tk.Frame(nb, bg="#1e1e2e"); nb.add(frame, text="ℹ️  About")
        about = (
            f"  {APP_NAME}\n"
            f"  Version {APP_VERSION}\n\n"
            f"  Created by:  {APP_AUTHOR}\n"
            f"  Contact:     {APP_EMAIL}\n\n"
            "  ─────────────────────────────────────────\n\n"
            "  Built to keep KODI / Emby / Jellyfin media libraries\n"
            "  clean, complete, and metadata-perfect.\n\n"
            "  ─────────────────────────────────────────\n\n"
            "  What it does:\n\n"
            "  • Scans a root media folder (one subfolder = one movie)\n"
            "  • Validates artwork files: poster.jpg, folder.jpg, fanart.jpg\n"
            "  • Validates metadata files: .nfo (KODI) and movie.xml (Emby/Jellyfin)\n"
            "  • Detects parse errors in XML/NFO with clear explanations\n"
            "  • Shows video quality, audio tracks, and subtitle info via FFprobe\n"
            "  • Checks IMDB and TMDB source IDs across all metadata tags\n"
            "  • Normalizes genres, ratings, and source IDs with one click\n"
            "  • Fetches poster and fanart images directly from TMDB\n"
            "  • Saves and restores scan results between sessions\n\n"
            "  ─────────────────────────────────────────\n\n"
            "  Full version history:\n"
            "  Help → Version History\n\n"
            "  ─────────────────────────────────────────\n\n"
            "  Feedback and bug reports welcome at:\n"
            f"  {APP_EMAIL}\n"
        )
        fr = tk.Frame(frame, bg="#1e1e2e")
        fr.pack(fill="both", expand=True, padx=0, pady=0)
        fr.rowconfigure(0, weight=1)
        fr.columnconfigure(0, weight=1)
        t = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4",
                    font=("Helvetica", 10), relief="flat", padx=24, pady=20,
                    spacing1=2, spacing3=2, state="normal")
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        t.tag_configure("bullet", foreground="#a6e3a1")
        t.tag_configure("sep",    foreground="#45475a")
        t.tag_configure("hdr",    foreground="#89b4fa", font=("Helvetica",10,"bold"))
        t.tag_configure("body",   foreground="#cdd6f4")
        for line in about.splitlines():
            stripped = line.strip()
            if stripped.startswith("─"):
                t.insert("end", line + "\n", "sep")
            elif stripped.startswith("•"):
                t.insert("end", line + "\n", "bullet")
            elif stripped and stripped == stripped.upper() and len(stripped) > 3:
                t.insert("end", line + "\n", "hdr")
            else:
                t.insert("end", line + "\n", "body")
        t.configure(state="disabled")

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


def _add_btn_tooltip(widget, text):                            ### NEW v0.17.0 ###
    """Attach a simple hover tooltip to any tk.Button widget."""
    _tw = [None]
    def _show(e):
        if _tw[0]: return
        tw = tk.Toplevel(widget); tw.wm_overrideredirect(True)
        tw.configure(bg="#45475a")
        tw.wm_geometry(f"+{e.x_root+16}+{e.y_root+10}")
        tk.Label(tw, text=text, bg="#45475a", fg="#cdd6f4",
                 font=("Helvetica", 9), padx=8, pady=4,
                 wraplength=360, justify="left").pack()
        _tw[0] = tw
    def _hide(e=None):
        if _tw[0]: _tw[0].destroy(); _tw[0] = None
    widget.bind("<Enter>", _show)
    widget.bind("<Leave>", _hide)


# ══════════════════════════════════════════════════════════════════════════════
# NEW v0.16.0 — Source ID write helper
# ══════════════════════════════════════════════════════════════════════════════

def _write_source_id_to_files(nfo_path, xml_path, id_type, chosen_id):  ### FIXED v0.16.0 ###
    """
    Write chosen_id to ALL relevant tags for id_type in both NFO and XML.

    XML IMDB tags:  <IMDB>, <IMDbId>, <IMDB_ID>          (all three written/inserted)
    XML TMDB tags:  <TMDB>, <TMDbId>, <TMDB_ID>          (all three written/inserted)
    NFO IMDB tags:  <imdbid>, <id moviedb="imdb">         (both written/inserted)
    NFO TMDB tags:  <tmdbid>, <id moviedb="tmdb">         (both written/inserted)

    Returns (ok: bool, error_str: str).
    """
    errors = []

    def _detect_indent(file_lines):
        for line in file_lines:
            m = re.match(r'^([ \t]+)<', line)
            if m:
                return m.group(1)
        return "  "

    def _replace_tag_in_lines(file_lines, tag, value):
        """Replace <tag>…</tag> in place. Returns (lines, found)."""
        tag_re = re.compile(rf'(<{re.escape(tag)}[^>]*>)[^<]*(</\s*{re.escape(tag)}\s*>)',
                            re.IGNORECASE)
        for i, line in enumerate(file_lines):
            if tag_re.search(line):
                file_lines[i] = tag_re.sub(rf'\g<1>{value}\2', line)
                return file_lines, True
        return file_lines, False

    def _insert_tag_before_close(file_lines, tag, value, end_tags):
        """Insert <tag>value</tag> before the first matching end_tag."""
        indent = _detect_indent(file_lines)
        new_line = f"{indent}<{tag}>{value}</{tag}>\n"
        for end in end_tags:
            end_re = re.compile(rf'</{re.escape(end)}>', re.IGNORECASE)
            for i, line in enumerate(file_lines):
                if end_re.search(line):
                    file_lines.insert(i, new_line)
                    return file_lines
        file_lines.append(new_line)
        return file_lines

    def _replace_attr_tag(file_lines, attr_val, value):
        """Replace <id moviedb="attr_val">…</id> in place. Returns (lines, found)."""
        tag_re = re.compile(
            rf'(<id[^>]*moviedb=["\']?{re.escape(attr_val)}["\']?[^>]*>)[^<]*(</\s*id\s*>)',
            re.IGNORECASE)
        for i, line in enumerate(file_lines):
            if tag_re.search(line):
                file_lines[i] = tag_re.sub(rf'\g<1>{value}\2', line)
                return file_lines, True
        return file_lines, False

    # ── Write to XML ──────────────────────────────────────────────────────────
    if xml_path and os.path.isfile(xml_path):
        try:
            with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            if id_type == "IMDB":
                xml_tags = ["IMDB", "IMDbId", "IMDB_ID"]
            else:
                xml_tags = ["TMDB", "TMDbId", "TMDB_ID"]

            for tag in xml_tags:
                lines, found = _replace_tag_in_lines(lines, tag, chosen_id)
                if not found:
                    lines = _insert_tag_before_close(lines, tag, chosen_id, ["Item"])

            with open(xml_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            errors.append(f"XML: {e}")

    # ── Write to NFO ──────────────────────────────────────────────────────────
    if nfo_path and os.path.isfile(nfo_path):
        try:
            with open(nfo_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            if id_type == "IMDB":
                # Write <imdbid>
                lines, found = _replace_tag_in_lines(lines, "imdbid", chosen_id)
                if not found:
                    lines = _insert_tag_before_close(lines, "imdbid", chosen_id, ["movie"])
                # Write <id moviedb="imdb">
                lines, found = _replace_attr_tag(lines, "imdb", chosen_id)
                if not found:
                    indent = _detect_indent(lines)
                    new_line = f'{indent}<id moviedb="imdb">{chosen_id}</id>\n'
                    end_re = re.compile(r'</movie>', re.IGNORECASE)
                    inserted = False
                    for i, line in enumerate(lines):
                        if end_re.search(line):
                            lines.insert(i, new_line); inserted = True; break
                    if not inserted:
                        lines.append(new_line)
                # Write bare <id>ttXXXXXXX</id> (KODI plain IMDB tag)
                # Use [^<]* instead of tt\d+ so corrupt values like
                # "tt33384756/" are fully replaced.  ### FIX v0.17.0-bug1 ###
                bare_id_re = re.compile(r'(<id\s*>)[^<]*(</\s*id\s*>)', re.IGNORECASE)
                bare_found = False
                for i, line in enumerate(lines):
                    if bare_id_re.search(line):
                        lines[i] = bare_id_re.sub(rf'\g<1>{chosen_id}\2', line)
                        bare_found = True
                        break
                if not bare_found:                             ### FIX v0.17.0 — insert if missing ###
                    indent = _detect_indent(lines)
                    bare_line = f"{indent}<id>{chosen_id}</id>\n"
                    end_re = re.compile(r'</movie>', re.IGNORECASE)
                    inserted = False
                    for i, line in enumerate(lines):
                        if end_re.search(line):
                            lines.insert(i, bare_line); inserted = True; break
                    if not inserted:
                        lines.append(bare_line)
            else:
                # Write <tmdbid>
                lines, found = _replace_tag_in_lines(lines, "tmdbid", chosen_id)
                if not found:
                    lines = _insert_tag_before_close(lines, "tmdbid", chosen_id, ["movie"])
                # Write <id moviedb="tmdb"> or <id moviedb="themoviedb">
                lines, found_t  = _replace_attr_tag(lines, "tmdb", chosen_id)
                lines, found_t2 = _replace_attr_tag(lines, "themoviedb", chosen_id)
                if not found_t and not found_t2:
                    indent   = _detect_indent(lines)
                    new_line = f'{indent}<id moviedb="tmdb">{chosen_id}</id>\n'
                    end_re   = re.compile(r'</movie>', re.IGNORECASE)
                    inserted = False
                    for i, line in enumerate(lines):
                        if end_re.search(line):
                            lines.insert(i, new_line); inserted = True; break
                    if not inserted:
                        lines.append(new_line)

            with open(nfo_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            errors.append(f"NFO: {e}")

    if errors:
        return False, "; ".join(errors)
    return True, ""


def _write_both_source_ids(nfo_path, xml_path, imdb_id, tmdb_id):  ### NEW v0.16.0 ###
    """
    Write both IMDB and TMDB IDs to NFO and XML in one call.
    Backs up files before writing. Returns (ok, error_str).
    Skips whichever ID is None/empty.
    """
    errors = []
    if imdb_id:
        ok, err = _write_source_id_to_files(nfo_path, xml_path, "IMDB", imdb_id)
        if not ok: errors.append(err)
    if tmdb_id:
        ok, err = _write_source_id_to_files(nfo_path, xml_path, "TMDB", tmdb_id)
        if not ok: errors.append(err)
    if errors:
        return False, "; ".join(e for e in errors if e)
    return True, ""

# ══════════════════════════════════════════════════════════════════════════════
# NEW v0.16.0 — Normalize Sources helpers + dialogs
# ══════════════════════════════════════════════════════════════════════════════

def _lookup_id_info(id_type, id_val):                      ### NEW v0.16.0 ###
    """
    Look up movie title + year for an IMDB or TMDB ID via TMDB API.
    Returns (title_str, year_str) or (None, None) if unavailable.
    Must be called from a background thread (makes HTTP request).
    """
    import urllib.request
    key = SETTINGS.get("tmdb_api_key", "").strip()
    if not key or not id_val:
        return None, None
    try:
        if id_type == "TMDB":
            url = (f"https://api.themoviedb.org/3/movie/{id_val}"
                   f"?api_key={key}&language=en-US")
        else:
            url = (f"https://api.themoviedb.org/3/find/{id_val}"
                   f"?api_key={key}&external_source=imdb_id&language=en-US")
        data = _tmdb_fetch_json(url, timeout=8)               ### FIX v0.17.0-bug2 ###
        if id_type == "TMDB":
            title = data.get("title") or data.get("name") or ""
            year  = (data.get("release_date") or "")[:4]
        else:
            results = data.get("movie_results", [])
            if not results:
                return None, None
            title = results[0].get("title", "")
            year  = (results[0].get("release_date", "") or "")[:4]
        return (title.strip() or None), (year.strip() or None)
    except Exception:
        return None, None


class _SourceDisagreementDialog(tk.Toplevel):              ### UPDATED v0.16.0 ###
    """
    Case B popup: ID tags disagree — let user pick which ID is correct.
    Looks up title + year for each candidate ID via TMDB API and
    shows them alongside the ID so the user can identify the right one
    without opening a browser.
    """
    def __init__(self, parent, movie_name, id_type, values):
        super().__init__(parent)
        self.result_id = None
        self.cancelled = True
        self.title(f"Normalize {id_type} ID — Conflict")
        self.configure(bg="#1e1e2e")
        self.resizable(True, False)
        self.transient(parent)
        self.minsize(520, 200)

        # ── Header ────────────────────────────────────────────────────────────
        tk.Label(self,
                 text=movie_name,
                 font=("Helvetica", 11, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(padx=20, pady=(14, 2))
        tk.Label(self,
                 text=f"{id_type} IDs disagree across tags.  "
                      f"Select the correct ID:",
                 bg="#1e1e2e", fg="#a6adc8",
                 font=("Helvetica", 9)).pack(padx=20, pady=(0, 8))

        # ── Radio frame with ID + title/year lookup ───────────────────────────
        rf = tk.Frame(self, bg="#313244"); rf.pack(fill="x", padx=16, pady=4)
        self._var = tk.StringVar(value=values[0])
        color = "#f5c518" if id_type == "IMDB" else "#01d277"

        # Placeholder labels — filled in after async lookup
        self._row_labels = {}   # id_val → tk.Label for title/year

        for v in values:
            row = tk.Frame(rf, bg="#313244"); row.pack(fill="x", padx=4, pady=3)
            tk.Radiobutton(row, text=v,
                           variable=self._var, value=v,
                           bg="#313244", fg=color, selectcolor="#1e1e2e",
                           activebackground="#313244",
                           font=("Consolas", 10, "bold"),
                           width=14, anchor="w").pack(side="left", padx=(6, 4))
            lbl = tk.Label(row,
                           text="looking up…",
                           bg="#313244", fg="#6c7086",
                           font=("Helvetica", 9, "italic"), anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=4)
            self._row_labels[v] = lbl

        # ── Buttons ───────────────────────────────────────────────────────────
        def _open_sites():
            for v in values:
                if id_type == "IMDB":
                    open_url_with_browser(f"https://www.imdb.com/title/{v}")
                else:
                    open_url_with_browser(f"https://www.themoviedb.org/movie/{v}")

        sep = tk.Frame(self, bg="#45475a", height=1)
        sep.pack(fill="x", padx=16, pady=(8,0))

        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(8, 14))
        tk.Button(bf, text="Open Website(s)",
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  font=("Helvetica", 9), padx=8, pady=4,
                  command=_open_sites).pack(side="left", padx=6)
        tk.Button(bf, text="  OK  ",
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  font=("Helvetica", 9, "bold"), padx=12, pady=4,
                  command=self._ok).pack(side="left", padx=6)
        tk.Button(bf, text="  Skip  ",
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  font=("Helvetica", 9), padx=8, pady=4,
                  command=self.destroy).pack(side="left", padx=6)

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Kick off async lookups for each ID
        threading.Thread(
            target=self._lookup_all, args=(id_type, list(values)),
            daemon=True).start()

    def _lookup_all(self, id_type, values):
        for v in values:
            title, year = _lookup_id_info(id_type, v)
            if title:
                text = f"{title}  ({year})" if year else title
            else:
                text = "ID invalid or lookup failed"
            def _update(lbl=self._row_labels.get(v), t=text):
                if lbl and lbl.winfo_exists():
                    lbl.configure(
                        text=t,
                        fg="#cdd6f4" if "invalid" not in t else "#f38ba8",
                        font=("Helvetica", 9, "italic" if "invalid" in t else "normal"))
                    # Resize dialog to fit new content
                    self.update_idletasks()
            self.after(0, _update)

    def _ok(self):
        self.result_id = self._var.get()
        self.cancelled = False
        self.destroy()


class _SourceManualEntryDialog(tk.Toplevel):               ### NEW v0.16.0 ###
    """Case C popup: all tags missing — ask user to type an ID."""
    def __init__(self, parent, movie_name, id_type):
        super().__init__(parent)
        self.result_id = None
        self.cancelled = True
        self.title(f"Enter {id_type} ID")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)
        self.transient(parent)

        pad = dict(padx=20, pady=6)
        tk.Label(self, text=f"{movie_name}",
                 font=("Helvetica", 11, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(**pad)
        if id_type == "IMDB":
            example = "e.g.  tt0133093  (The Matrix)"
            hint = "IMDB IDs start with 'tt' followed by digits."
        else:
            example = "e.g.  603  (The Matrix)"
            hint = "TMDB IDs are numeric."
        tk.Label(self,
                 text=f"No {id_type} ID found.\n{hint}\n{example}",
                 bg="#1e1e2e", fg="#a6adc8",
                 font=("Helvetica", 10), justify="left").pack(**pad)

        self._entry_var = tk.StringVar()
        tk.Entry(self, textvariable=self._entry_var,
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 font=("Consolas", 11), width=24, relief="flat").pack(**pad)

        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(4, 16))
        tk.Button(bf, text="  OK  ", bg="#a6e3a1", fg="#1e1e2e",
                  relief="flat", cursor="hand2",
                  command=self._ok).pack(side="left", padx=6)
        tk.Button(bf, text="  Cancel  ", bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=self.destroy).pack(side="left", padx=6)
        self.bind("<Return>", lambda e: self._ok())

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _ok(self):
        v = self._entry_var.get().strip()
        if v:
            self.result_id = v
            self.cancelled = False
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# NEW v0.16.0 — Search Sources result dialog  (REBUILT v0.16.0 — Apply buttons)
# ══════════════════════════════════════════════════════════════════════════════

class _SearchSourcesResultDialog(tk.Toplevel):             ### REBUILT v0.16.0 ###
    """
    Scrollable popup showing grouped TMDB search results per movie.
    Each result row has:
      • Apply  — writes both IMDB+TMDB IDs to NFO/XML, re-validates row silently
      • Open IMDB / Open TMDB — open the website (greyed if no ID on that result)
    Export to TXT included.
    """
    _BTN   = dict(relief="flat", cursor="hand2", font=("Helvetica", 8, "bold"),
                  padx=6, pady=3)
    _C_BG  = "#1e1e2e"
    _C_ROW = "#252535"
    _C_HDR = "#313244"
    _C_SEP = "#45475a"
    _C_TXT = "#cdd6f4"
    _C_DIM = "#6c7086"
    _C_GRN = "#a6e3a1"
    _C_BLU = "#89b4fa"
    _C_YEL = "#f5c518"
    _C_RED = "#f38ba8"

    def __init__(self, parent, results, data_list):
        super().__init__(parent)
        self._parent_app = parent
        self._results    = results      # list of {movie_name, year, matches:[...]}
        self._data_list  = data_list    # parallel list of row dicts from scan
        self._photo_refs = []           # keep tk PhotoImage refs alive

        self.title("Search Sources — Results")
        self.configure(bg=self._C_BG)
        self.geometry("920x680")
        self.minsize(760, 480)
        self.transient(parent)

        # ── Header ────────────────────────────────────────────────────────────
        hf = tk.Frame(self, bg=self._C_BG); hf.pack(fill="x", padx=16, pady=(12,4))
        tk.Label(hf, text="Search Sources — Results",
                 font=("Helvetica", 13, "bold"),
                 bg=self._C_BG, fg=self._C_TXT).pack(side="left")
        tk.Label(hf, text=f"{len(results)} movie(s)  ·  click Apply to write IDs",
                 font=("Helvetica", 9), bg=self._C_BG, fg=self._C_DIM).pack(
                 side="left", padx=12)

        # ── Scrollable canvas ─────────────────────────────────────────────────
        outer = tk.Frame(self, bg=self._C_BG)
        outer.pack(fill="both", expand=True, padx=12, pady=4)
        outer.rowconfigure(0, weight=1); outer.columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(outer, bg=self._C_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._inner = tk.Frame(self._canvas, bg=self._C_BG)
        self._win_id = self._canvas.create_window((0, 0), window=self._inner,
                                                   anchor="nw")
        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>",
                              lambda e: self._canvas.yview_scroll(
                                  int(-1*(e.delta/120)), "units"))

        self._build_content()

        # ── Footer buttons ────────────────────────────────────────────────────
        bf = tk.Frame(self, bg=self._C_BG); bf.pack(pady=(4, 12))
        tk.Button(bf, text="  Export to TXT  ", bg=self._C_BLU, fg="#1e1e2e",
                  command=self._export_txt, **self._BTN).pack(side="left", padx=6)
        tk.Button(bf, text="  Close  ", bg=self._C_GRN, fg="#1e1e2e",
                  command=self.destroy, **self._BTN).pack(side="left", padx=6)

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _on_inner_configure(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self._canvas.itemconfig(self._win_id, width=e.width)

    def _build_content(self):
        for entry, row_data in zip(self._results, self._data_list):
            mn  = entry["movie_name"]
            yr  = entry.get("year", "")
            hdr = f"  {mn}  ({yr})" if yr and yr != "-" else f"  {mn}"

            # IDs already present in the scanned NFO/XML for this movie
            existing_imdb = (row_data.get("source_imdb_val") or "").strip()
            existing_tmdb = (row_data.get("source_tmdb_val") or "").strip()

            # Movie header row
            hrow = tk.Frame(self._inner, bg=self._C_HDR); hrow.pack(
                fill="x", padx=0, pady=(8,1))
            tk.Label(hrow, text=hdr,
                     font=("Helvetica", 10, "bold"),
                     bg=self._C_HDR, fg=self._C_BLU,
                     anchor="w").pack(side="left", padx=8, pady=5)

            matches = entry.get("matches", [])
            if not matches:
                nf = tk.Frame(self._inner, bg=self._C_ROW); nf.pack(fill="x", padx=2, pady=1)
                tk.Label(nf, text="   No results found on TMDB",
                         font=("Helvetica", 9, "italic"),
                         bg=self._C_ROW, fg=self._C_RED, anchor="w").pack(
                         side="left", padx=10, pady=6)
                continue

            for i, m in enumerate(matches):
                tmdb_id = m.get("tmdb_id", "")
                imdb_id = m.get("imdb_id", "")
                title   = m.get("title", "")
                yr2     = m.get("year", "")
                pop     = m.get("popularity", 0)

                row_bg    = self._C_ROW if i % 2 == 0 else "#2a2a3e"
                mrow = tk.Frame(self._inner, bg=row_bg); mrow.pack(
                    fill="x", padx=2, pady=1)

                # Rank badge
                badge_col = self._C_GRN if i == 0 else self._C_DIM
                tk.Label(mrow, text=f" #{i+1} ", font=("Consolas", 9, "bold"),
                         bg=row_bg, fg=badge_col, width=4,
                         anchor="center").pack(side="left", padx=(6,2), pady=6)

                # Title + year (normal colour)
                title_str = f"{title}  ({yr2})" if yr2 else title
                tk.Label(mrow, text=title_str,
                         font=("Consolas", 9), bg=row_bg, fg=self._C_TXT,
                         anchor="w").pack(side="left", padx=(4,0), pady=6)

                # TMDB ID — yellow if matches existing scanned value  ### FIX v0.16.0 ###
                tmdb_txt = f"   TMDB: {tmdb_id}" if tmdb_id else "   TMDB: —"
                tmdb_col = self._C_YEL if (tmdb_id and tmdb_id == existing_tmdb) \
                           else self._C_TXT
                tk.Label(mrow, text=tmdb_txt,
                         font=("Consolas", 9, "bold" if tmdb_col == self._C_YEL else "normal"),
                         bg=row_bg, fg=tmdb_col,
                         anchor="w").pack(side="left", padx=2, pady=6)

                # IMDB ID — yellow if matches existing scanned value  ### FIX v0.16.0 ###
                imdb_txt = f"   IMDB: {imdb_id}" if imdb_id else "   IMDB: —"
                imdb_col = self._C_YEL if (imdb_id and imdb_id == existing_imdb) \
                           else self._C_TXT
                tk.Label(mrow, text=imdb_txt,
                         font=("Consolas", 9, "bold" if imdb_col == self._C_YEL else "normal"),
                         bg=row_bg, fg=imdb_col,
                         anchor="w").pack(side="left", padx=2, pady=6)

                if pop:
                    tk.Label(mrow, text=f"   ⭐ {pop:.1f}",
                             font=("Consolas", 9), bg=row_bg, fg=self._C_DIM,
                             anchor="w").pack(side="left", padx=2, pady=6)

                # ── Action buttons (fixed-width, always same position) ─────────
                btn_frame = tk.Frame(mrow, bg=row_bg); btn_frame.pack(
                    side="right", padx=6, pady=4)

                # Open IMDB
                if imdb_id:
                    tk.Button(btn_frame, text="Open IMDB",
                              bg=self._C_YEL, fg="#1e1e2e", width=10,
                              command=lambda iid=imdb_id:
                                  open_url_with_browser(
                                      f"https://www.imdb.com/title/{iid}"),
                              **self._BTN).pack(side="left", padx=(0,3))
                else:
                    tk.Button(btn_frame, text="Open IMDB",
                              bg=self._C_SEP, fg=self._C_DIM, width=10,
                              state="disabled", **self._BTN).pack(side="left", padx=(0,3))

                # Open TMDB
                if tmdb_id:
                    tk.Button(btn_frame, text="Open TMDB",
                              bg="#01b4e4", fg="#1e1e2e", width=10,
                              command=lambda tid=tmdb_id:
                                  open_url_with_browser(
                                      f"https://www.themoviedb.org/movie/{tid}"),
                              **self._BTN).pack(side="left", padx=(0,6))
                else:
                    tk.Button(btn_frame, text="Open TMDB",
                              bg=self._C_SEP, fg=self._C_DIM, width=10,
                              state="disabled", **self._BTN).pack(side="left", padx=(0,6))

                # Apply
                tk.Button(btn_frame, text="✓ Apply",
                          bg=self._C_GRN, fg="#1e1e2e", width=9,
                          command=lambda rd=row_data, tid=tmdb_id, iid=imdb_id:
                              self._apply(rd, tid, iid),
                          **self._BTN).pack(side="left")

        # Bottom padding + legend                             ### FIX v0.16.0 ###
        tk.Frame(self._inner, bg=self._C_BG, height=6).pack()
        tk.Label(self._inner,
                 text="IMDB and TMDB IDs in yellow are the ones found in the .nfo/.xml file(s)",
                 font=("Helvetica", 8, "italic"),
                 bg=self._C_BG, fg=self._C_YEL).pack(pady=(2, 10))

    def _apply(self, row_data, tmdb_id, imdb_id):
        """Write both IDs to NFO/XML then re-validate the row silently."""
        nfo_path = row_data.get("nfo_path") if row_data.get("nfo_exists") else None
        xml_path = row_data.get("xml_path") if row_data.get("xml_exists") else None
        movie    = row_data.get("movie_name", row_data.get("subfolder", "?"))

        if not nfo_path and not xml_path:
            messagebox.showwarning("Apply",
                f"{movie}\nNo NFO or XML file found — nothing to write.")
            return

        _make_backup(movie,
                     *[p for p in [nfo_path, xml_path]
                       if p and os.path.isfile(p)])

        ok, err = _write_both_source_ids(nfo_path, xml_path, imdb_id, tmdb_id)
        if not ok:
            messagebox.showerror("Apply Failed", f"{movie}\n{err}")
            return

        # Re-validate silently
        self._parent_app.after(0, lambda rd=row_data:
                               self._parent_app._reval_by_path(rd))
        messagebox.showinfo("Applied",
            f"{movie}\n"
            f"TMDB: {tmdb_id or '—'}\n"
            f"IMDB: {imdb_id or '—'}\n"
            "Written to NFO and XML.")
        self.destroy()   ### FIX v0.16.0 — close the results dialog after apply ###

    def _export_txt(self):
        p = filedialog.asksaveasfilename(
            title="Export Search Results",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="search_sources_results.txt")
        if not p: return
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write("MediaClinic — Search Sources Results\n")
                f.write("=" * 60 + "\n\n")
                for entry in self._results:
                    mn  = entry["movie_name"]; yr = entry.get("year", "")
                    f.write(f"{mn} ({yr})\n" if yr and yr != "-" else f"{mn}\n")
                    matches = entry.get("matches", [])
                    if not matches:
                        f.write("  No results found.\n")
                    else:
                        for i, m in enumerate(matches):
                            tag = "[Best]" if i == 0 else f"[#{i+1}]  "
                            f.write(f"  {tag}  TMDB: {m.get('tmdb_id','')}  "
                                    f"IMDB: {m.get('imdb_id','—')}  "
                                    f"{m.get('title','')} ({m.get('year','')})\n")
                    f.write("\n")
            messagebox.showinfo("Export Complete", f"Saved to:\n{p}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))


def _friendly_ratio(w, h):                                 ### NEW v0.16.0 ###
    """
    Convert pixel dimensions to a human-friendly aspect ratio string.
    Covers common poster and fanart ratios with exact named values,
    falls back to reduced fraction or decimal for unusual sizes.
    """
    if not w or not h or h == 0:
        return "—"
    ratio = w / h
    # Named ratios — order matters (most specific first)
    named = [
        (2/3,    "2:3"),    # portrait poster
        (3/4,    "3:4"),    # alternate portrait
        (1/1,    "1:1"),    # square
        (4/3,    "4:3"),    # old TV / square-ish
        (3/2,    "3:2"),    # photo
        (16/10,  "16:10"),  # widescreen monitor
        (16/9,   "16:9"),   # standard widescreen fanart
        (16/8,   "16:8"),   # alternate wide
        (17/9,   "17:9"),
        (21/9,   "21:9"),   # ultrawide
        (2/1,    "2:1"),
    ]
    for target, label in named:
        if abs(ratio - target) < 0.015:
            return label
    # Fallback: reduce fraction via GCD
    from math import gcd
    g = gcd(int(w), int(h))
    rw, rh = int(w) // g, int(h) // g
    if rw <= 32 and rh <= 32:
        return f"{rw}:{rh}"
    return f"{ratio:.2f}"


# ══════════════════════════════════════════════════════════════════════════════
# NEW v0.16.0 — Fetch Image Dialog  (REBUILT v0.16.0 — actual thumbnails)
# ══════════════════════════════════════════════════════════════════════════════

class _BatchProgressDialog(tk.Toplevel):                       ### NEW v0.17.0 ###
    """
    Non-blocking modal progress window for long batch operations.

    Usage (from background thread):
        dlg = _BatchProgressDialog(parent, title="Processing Movies…", total=len(items))
        # In worker loop:
        if dlg.cancelled: break
        dlg.update(processed=i+1)
        # After loop:
        dlg.close()

    All UI updates are posted via parent.after() — safe to call from any thread.
    """

    _BG   = "#1e1e2e"
    _HDR  = "#313244"
    _TXT  = "#cdd6f4"
    _DIM  = "#6c7086"
    _GRN  = "#2d6e3f"
    _BAR  = "#313244"
    _RED  = "#f38ba8"

    def __init__(self, parent, title="Processing Movies…", total=0):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=self._BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self.cancelled = False
        self._total    = max(1, total)
        self._done     = 0
        self._times    = []          # rolling frame times for ETA
        self._t0       = time.time()
        self._closed   = False

        # Title label
        tk.Label(self, text=title,
                 bg=self._BG, fg=self._TXT,
                 font=("Helvetica", 11, "bold")).pack(padx=24, pady=(18, 6))

        # Progress canvas (like the scan bar)
        self._pbar = tk.Canvas(self, bg=self._BAR, height=22, width=400,
                               highlightthickness=0)
        self._pbar.pack(padx=24, pady=(0, 4))
        self._draw_bar(0)

        # Percentage + ETA
        self._pct_var = tk.StringVar(value="Processing…  0%")
        tk.Label(self, textvariable=self._pct_var,
                 bg=self._BG, fg=self._TXT,
                 font=("Helvetica", 10, "bold")).pack()

        self._eta_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self._eta_var,
                 bg=self._BG, fg=self._DIM,
                 font=("Helvetica", 9)).pack(pady=(2, 8))

        # Cancel button
        tk.Button(self, text="  Cancel ALL  ",
                  bg=self._RED, fg=self._BG,
                  relief="flat", cursor="hand2",
                  font=("Helvetica", 10, "bold"),
                  padx=10, pady=5,
                  command=self._on_cancel).pack(pady=(0, 16))

        self.bind("<Escape>", lambda e: self._on_cancel())

        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{px+(pw-w)//2}+{py+(ph-h)//2}")

    # ── internal ──────────────────────────────────────────────────────────────
    def _draw_bar(self, pct):
        c = self._pbar; c.delete("all")
        w = 400; h = 22
        c.create_rectangle(0, 0, w, h, fill=self._BAR, outline="")
        fw = int(w * pct / 100)
        if fw > 0:
            c.create_rectangle(0, 0, fw, h, fill=self._GRN, outline="")
        c.create_text(w // 2, h // 2, text=f"{pct}%",
                      fill=self._TXT, font=("Helvetica", 10, "bold"))

    @staticmethod
    def _fmt_eta(secs):
        secs = int(secs)
        if secs < 60:
            return f"{secs}s"
        return f"{secs // 60}m {secs % 60:02d}s"

    def _on_cancel(self):
        self.cancelled = True
        try:
            self._pct_var.set("Cancelling…")
            self._eta_var.set("")
        except Exception:
            pass

    # ── public API — safe to call from any thread ─────────────────────────────
    def update(self, processed):
        """Call after each item is processed."""
        if self._closed:
            return
        now = time.time()
        self._done = processed
        elapsed_item = now - (self._times[-1][0] if self._times else self._t0)
        self._times.append((now, elapsed_item))
        if len(self._times) > 10:
            self._times.pop(0)

        pct = int(processed / self._total * 100)

        # ETA via moving average
        avg_item = sum(t for _, t in self._times) / len(self._times)
        remaining = max(0, self._total - processed)
        eta_secs  = avg_item * remaining
        eta_str   = (f"Estimated time remaining: {self._fmt_eta(eta_secs)}"
                     if processed < self._total else "")

        def _ui(p=pct, e=eta_str, pr=processed, tot=self._total):
            if self._closed: return
            try:
                self._draw_bar(p)
                self._pct_var.set(f"Processing…  {p}%  ({pr}/{tot})")
                self._eta_var.set(e)
            except Exception:
                pass
        try:
            self.after(0, _ui)
        except Exception:
            pass

    def close(self):
        """Destroy the dialog from any thread."""
        if self._closed:
            return
        self._closed = True
        try:
            self.after(0, self.destroy)
        except Exception:
            pass


class _FetchImageDialog(tk.Toplevel):                      ### REBUILT v0.16.0 ###
    """
    Fetch Poster/Folder or Fetch Fanart.
    Poster mode:  4-column × 2-row grid (8 images per page), paginated.
    Fanart mode:  vertical scrollable list, 5 images per page, paginated.
    Both modes show actual thumbnails (PIL w500/w300) + friendly ratio labels.
    Navigation: ◀ Back  /  Show More ▶  buttons.
    """
    _POSTER_W, _POSTER_H = 160, 240    # thumbnail target 2:3 portrait
    _FANART_W, _FANART_H = 300, 169    # thumbnail target 16:9 landscape
    _LOCAL_MAX_W         = 200
    _LOCAL_MAX_H         = 260
    _POSTER_PAGE         = 8           # 4 cols × 2 rows
    _FANART_PAGE         = 5
    _TMDB_BASE_THUMB     = "https://image.tmdb.org/t/p/w500"
    _TMDB_FALLBACK_THUMB = "https://image.tmdb.org/t/p/w300"
    _TMDB_BASE_ORIG      = "https://image.tmdb.org/t/p/original"

    def __init__(self, parent, row_data, image_mode, tmdb_key, tmdb_id):
        super().__init__(parent)
        self.applied     = False
        self._row        = row_data
        self._mode       = image_mode
        self._key        = tmdb_key
        self._tmdb       = tmdb_id
        self._images     = []
        self._page       = 0
        self._photo_refs       = []   # TMDB thumbnail PhotoImages (cleared on page change)
        self._local_photo_refs = []   # local image PhotoImage (never cleared)

        is_poster = (image_mode == "poster")
        self._page_size = self._POSTER_PAGE if is_poster else self._FANART_PAGE
        title_str = "Fetch Poster / Folder" if is_poster else "Fetch Fanart"

        self.title(f"{title_str} — {row_data.get('movie_name', '')}")
        self.configure(bg="#1e1e2e")
        self.transient(parent)
        self.resizable(True, True)

        # ── Header ────────────────────────────────────────────────────────────
        tk.Label(self,
                 text=f"{title_str}  ·  "
                      f"{row_data.get('movie_name', '')}  ·  TMDB ID: {tmdb_id}",
                 font=("Helvetica", 10, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(pady=(10, 2))
        self._status_lbl = tk.Label(self, text="Loading TMDB images…",
                                     font=("Helvetica", 8),
                                     bg="#1e1e2e", fg="#6c7086")
        self._status_lbl.pack()

        # ── Body ──────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg="#1e1e2e")
        body.pack(fill="both", expand=True, padx=12, pady=6)

        # Left — local image panel
        lf = tk.Frame(body, bg="#313244", width=240)
        lf.pack(side="left", fill="y", padx=(0, 10))
        lf.pack_propagate(False)
        tk.Label(lf, text="Current Local Image",
                 font=("Helvetica", 9, "bold"),
                 bg="#313244", fg="#89b4fa").pack(pady=(10, 4))
        self._local_img_lbl  = tk.Label(lf, bg="#313244")
        self._local_img_lbl.pack(pady=4)
        self._local_info_lbl = tk.Label(lf, bg="#313244", fg="#a6adc8",
                                         font=("Helvetica", 8),
                                         wraplength=220, justify="center")
        self._local_info_lbl.pack(padx=8, pady=4)

        # Right — TMDB images panel
        rf = tk.Frame(body, bg="#1e1e2e")
        rf.pack(side="left", fill="both", expand=True)
        tk.Label(rf,
                 text="TMDB Images  (sorted by resolution, highest first)",
                 font=("Helvetica", 9, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(0, 4))

        # Scrollable canvas
        cf = tk.Frame(rf, bg="#1e1e2e")
        cf.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(cf, bg="#1e1e2e", highlightthickness=0)
        vsb = ttk.Scrollbar(cf, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._grid_frame = tk.Frame(self._canvas, bg="#1e1e2e")
        self._grid_win   = self._canvas.create_window(
            (0, 0), window=self._grid_frame, anchor="nw")
        self._grid_frame.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._grid_win, width=e.width))
        # Change 12: Scoped mouse-wheel bindings — activate on Enter, release on Leave ### NEW v0.18.0 ###
        self._canvas.bind("<Enter>",
            lambda e: self._canvas.bind_all("<MouseWheel>",
                lambda ev: self._canvas.yview_scroll(int(-1*(ev.delta/120)), "units")))
        self._canvas.bind("<Leave>",
            lambda e: self._canvas.unbind_all("<MouseWheel>"))
        # Linux scroll support                                                          ### NEW v0.18.0 ###
        self._canvas.bind("<Enter>",
            lambda e: (
                self._canvas.bind_all("<MouseWheel>",
                    lambda ev: self._canvas.yview_scroll(int(-1*(ev.delta/120)), "units")),
                self._canvas.bind_all("<Button-4>",
                    lambda ev: self._canvas.yview_scroll(-1, "units")),
                self._canvas.bind_all("<Button-5>",
                    lambda ev: self._canvas.yview_scroll(1, "units"))))
        self._canvas.bind("<Leave>",
            lambda e: (
                self._canvas.unbind_all("<MouseWheel>"),
                self._canvas.unbind_all("<Button-4>"),
                self._canvas.unbind_all("<Button-5>")))
        self._loading_lbl = tk.Label(self._grid_frame,
                                      text="Fetching from TMDB…",
                                      bg="#1e1e2e", fg="#6c7086",
                                      font=("Helvetica", 10, "italic"))
        self._loading_lbl.pack(pady=30)

        # ── Footer: pagination + cancel ───────────────────────────────────────
        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(4, 12))
        self._back_btn = tk.Button(bf, text="◀  Back",
                                    bg="#45475a", fg="#cdd6f4",
                                    relief="flat", cursor="hand2",
                                    font=("Helvetica", 9, "bold"),
                                    padx=10, pady=4,
                                    state="disabled",
                                    command=self._page_back)
        self._back_btn.pack(side="left", padx=6)
        self._more_btn = tk.Button(bf, text="Show More  ▶",
                                    bg="#45475a", fg="#cdd6f4",
                                    relief="flat", cursor="hand2",
                                    font=("Helvetica", 9, "bold"),
                                    padx=10, pady=4,
                                    state="disabled",
                                    command=self._page_more)
        self._more_btn.pack(side="left", padx=6)
        tk.Button(bf, text="  Cancel  ",
                  bg="#f38ba8", fg="#1e1e2e",
                  relief="flat", cursor="hand2",
                  font=("Helvetica", 9, "bold"),
                  padx=10, pady=4,
                  command=self.destroy).pack(side="left", padx=6)

        # ── Sizing ────────────────────────────────────────────────────────────
        # Poster: 4 cols × (160+button) ≈ 870px right + 240 left = ~1130
        # Fanart: 300px thumb + text right + 240 left = ~800
        if is_poster:
            self.geometry("1160x680")
        else:
            self.geometry("980x760")
        self.minsize(820, 500)

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        threading.Thread(target=self._load_local_image, daemon=True).start()
        threading.Thread(target=self._load_tmdb_images, daemon=True).start()

    # ── Local image ───────────────────────────────────────────────────────────
    def _load_local_image(self):
        if self._mode == "poster":
            path, exists, fname = (self._row.get("poster_path",""),
                                   self._row.get("poster_exists", False),
                                   "poster.jpg")
        else:
            path, exists, fname = (self._row.get("fanart_path",""),
                                   self._row.get("fanart_exists", False),
                                   "fanart.jpg")

        if not exists or not path or not os.path.isfile(path):
            self.after(0, lambda: self._local_info_lbl.configure(
                text=f"{fname}\n\n[Not found]"))
            return
        try:
            sz    = os.path.getsize(path)
            photo = self._load_photo(path, self._LOCAL_MAX_W, self._LOCAL_MAX_H)
            w, h  = get_image_wh(path)
            ratio = _friendly_ratio(w, h)
            info  = f"{fname}\n{w}×{h}  ({ratio})\n{format_size(sz)}"
            def _show(p=photo, t=info):
                self._local_photo_refs.append(p)   # FIX: separate list, never cleared
                self._local_img_lbl.configure(image=p)
                self._local_info_lbl.configure(text=t)
            self.after(0, _show)
        except Exception as ex:
            self.after(0, lambda: self._local_info_lbl.configure(
                text=f"{fname}\n\n[Preview error]"))

    # ── TMDB image list (async) ───────────────────────────────────────────────
    def _load_tmdb_images(self):
        key_name = "posters" if self._mode == "poster" else "backdrops"
        try:
            url = (f"https://api.themoviedb.org/3/movie/{self._tmdb}"
                   f"/images?api_key={self._key}")
            data = _tmdb_fetch_json(url, timeout=15)          ### FIX v0.17.0-bug2 ###
            imgs = data.get(key_name, [])
            imgs.sort(key=lambda x: x.get("width",0)*x.get("height",0),
                      reverse=True)
            self._images = imgs
        except Exception as e:
            err_msg = _tmdb_error_message(e)
            logger.warning(f"FetchImageDialog: {err_msg}")
            self._images = []
            self.after(0, lambda m=err_msg: (
                self._loading_lbl.configure(text=m, fg="#f38ba8"),
                self._status_lbl.configure(text="Load failed")))
            return

        self.after(0, lambda: self._status_lbl.configure(
            text=f"{len(self._images)} image(s) found — downloading thumbnails…"))
        self._render_page()

    # ── Pagination ────────────────────────────────────────────────────────────
    def _page_more(self):
        self._page += 1
        self._render_page()

    def _page_back(self):
        self._page = max(0, self._page - 1)
        self._render_page()

    def _render_page(self):
        if self._mode == "poster":
            threading.Thread(target=self._render_poster_grid, daemon=True).start()
        else:
            threading.Thread(target=self._render_fanart_list, daemon=True).start()

    # ── Thumbnail helpers ─────────────────────────────────────────────────────
    def _download_thumb(self, file_path):
        import urllib.request
        for base in (self._TMDB_BASE_THUMB, self._TMDB_FALLBACK_THUMB):
            try:
                req = urllib.request.Request(base + file_path,
                    headers={"User-Agent": "MediaClinic/0.17.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read()
            except Exception:
                continue
        return None

    def _load_photo(self, path_or_bytes, max_w, max_h):
        if isinstance(path_or_bytes, str):
            img = _PILImage.open(path_or_bytes)
        else:
            import io
            img = _PILImage.open(io.BytesIO(path_or_bytes))
        img = img.convert("RGB")
        img.thumbnail((max_w, max_h), _PILImage.LANCZOS)
        return _PILImageTk.PhotoImage(img)

    def _update_nav_buttons(self):
        start = self._page * self._page_size
        self._back_btn.configure(
            state="normal" if self._page > 0 else "disabled")
        self._more_btn.configure(
            state="normal"
            if start + self._page_size < len(self._images)
            else "disabled")

    # ── Poster grid — 4 columns × 2 rows ─────────────────────────────────────
    def _render_poster_grid(self):
        start = self._page * self._page_size
        page_imgs = self._images[start: start + self._page_size]
        photos = []
        for img in page_imgs:
            fp  = img.get("file_path", "")
            raw = self._download_thumb(fp) if fp else None
            photos.append((img, raw))

        def _build(ph=photos):
            if not self.winfo_exists(): return
            # Clear previous content
            for w in self._grid_frame.winfo_children():
                w.destroy()
            self._photo_refs.clear()

            if not ph:
                tk.Label(self._grid_frame,
                         text="No poster images found on TMDB.",
                         bg="#1e1e2e", fg="#f38ba8",
                         font=("Helvetica", 10)
                         ).grid(row=0, column=0, columnspan=4,
                                padx=20, pady=20)
                self._status_lbl.configure(text="No images")
                return

            count = 0
            total = start + len(ph)
            for idx, (img, raw) in enumerate(ph):
                r, c   = divmod(idx, 4)
                w2, h2 = img.get("width", 0), img.get("height", 0)
                sz     = img.get("file_size", 0)
                fp     = img.get("file_path", "")
                orig   = self._TMDB_BASE_ORIG + fp
                rank   = start + idx + 1
                ratio  = _friendly_ratio(w2, h2)

                cell = tk.Frame(self._grid_frame, bg="#252535", relief="flat")
                cell.grid(row=r, column=c, padx=5, pady=5, sticky="n")

                if raw and _PIL_AVAILABLE:
                    try:
                        photo = self._load_photo(raw,
                            self._POSTER_W, self._POSTER_H)
                        self._photo_refs.append(photo)
                        tk.Label(cell, image=photo,
                                 bg="#252535").pack(padx=4, pady=(6,2))
                        count += 1
                    except Exception:
                        tk.Label(cell, text="[Preview\nunavailable]",
                                 bg="#252535", fg="#6c7086",
                                 width=14, height=8,
                                 font=("Helvetica",8)).pack(padx=4, pady=(6,2))
                else:
                    tk.Label(cell,
                             text="[No PIL]" if not _PIL_AVAILABLE
                                  else "[Failed]",
                             bg="#252535", fg="#6c7086",
                             width=14, height=8,
                             font=("Helvetica",8)).pack(padx=4, pady=(6,2))

                sz_txt = f"  {format_size(sz)}" if sz else ""
                tk.Label(cell,
                         text=f"#{rank}  {w2}×{h2} ({ratio}){sz_txt}",
                         bg="#252535", fg="#a6adc8",
                         font=("Consolas", 7)).pack()
                tk.Button(cell, text="✓ Use This",
                          bg="#a6e3a1", fg="#1e1e2e",
                          relief="flat", cursor="hand2",
                          font=("Helvetica", 8, "bold"),
                          padx=6, pady=3,
                          command=lambda u=orig: self._apply_image(u)
                          ).pack(pady=(3,8))

            self._status_lbl.configure(
                text=f"Page {self._page+1}  ·  "
                     f"showing #{start+1}–{total} of {len(self._images)}  "
                     f"·  {count} previews")
            self._update_nav_buttons()
            self._canvas.yview_moveto(0)

        self.after(0, _build)

    # ── Fanart list — vertical, 5 per page ───────────────────────────────────
    def _render_fanart_list(self):
        start = self._page * self._page_size
        page_imgs = self._images[start: start + self._page_size]
        photos = []
        for img in page_imgs:
            fp  = img.get("file_path", "")
            raw = self._download_thumb(fp) if fp else None
            photos.append((img, raw))

        def _build(ph=photos):
            if not self.winfo_exists(): return
            for w in self._grid_frame.winfo_children():
                w.destroy()
            self._photo_refs.clear()

            if not ph:
                tk.Label(self._grid_frame,
                         text="No backdrop images found on TMDB.",
                         bg="#1e1e2e", fg="#f38ba8",
                         font=("Helvetica", 10)).pack(padx=20, pady=20)
                self._status_lbl.configure(text="No images")
                return

            count = 0
            total = start + len(ph)
            for idx, (img, raw) in enumerate(ph):
                w2, h2  = img.get("width", 0), img.get("height", 0)
                sz      = img.get("file_size", 0)
                fp      = img.get("file_path", "")
                orig    = self._TMDB_BASE_ORIG + fp
                rank    = start + idx + 1
                ratio   = _friendly_ratio(w2, h2)
                row_bg  = "#252535" if idx % 2 == 0 else "#2a2a3e"

                row_f = tk.Frame(self._grid_frame, bg=row_bg)
                row_f.pack(fill="x", padx=4, pady=5)

                thumb_lbl = tk.Label(row_f, bg=row_bg)
                thumb_lbl.pack(side="left", padx=(8,10), pady=6)

                if raw and _PIL_AVAILABLE:
                    try:
                        photo = self._load_photo(raw,
                            self._FANART_W, self._FANART_H)
                        self._photo_refs.append(photo)
                        thumb_lbl.configure(image=photo)
                        count += 1
                    except Exception:
                        thumb_lbl.configure(
                            text="[Preview\nunavailable]",
                            fg="#6c7086", font=("Helvetica",8),
                            width=22, height=7)
                else:
                    thumb_lbl.configure(
                        text="[No PIL]" if not _PIL_AVAILABLE else "[Failed]",
                        fg="#6c7086", font=("Helvetica",8),
                        width=22, height=7)

                info_f = tk.Frame(row_f, bg=row_bg)
                info_f.pack(side="left", fill="both", expand=True, pady=6)
                sz_txt = f"  ·  ~{format_size(sz)}" if sz else ""
                tk.Label(info_f,
                         text=f"#{rank}   {w2}×{h2} ({ratio}){sz_txt}",
                         bg=row_bg, fg="#cdd6f4",
                         font=("Consolas", 9), anchor="w"
                         ).pack(fill="x", padx=4, pady=(6,2))
                tk.Button(info_f, text="✓ Use This Fanart",
                          bg="#a6e3a1", fg="#1e1e2e",
                          relief="flat", cursor="hand2",
                          font=("Helvetica", 9, "bold"),
                          padx=10, pady=5,
                          command=lambda u=orig: self._apply_image(u)
                          ).pack(anchor="w", padx=4, pady=4)

            self._status_lbl.configure(
                text=f"Page {self._page+1}  ·  "
                     f"showing #{start+1}–{total} of {len(self._images)}  "
                     f"·  {count} previews")
            self._update_nav_buttons()
            self._canvas.yview_moveto(0)

        self.after(0, _build)

    # ── Apply selected image ──────────────────────────────────────────────────
    def _apply_image(self, image_url):                         ### UPDATED v0.18.0 — uses _tmdb_download_image ###
        movie = self._row.get("movie_name", self._row.get("subfolder","?"))
        sp    = self._row.get("subfolder_path", "")

        if self._mode == "poster":
            targets = [os.path.join(sp, "poster.jpg"),
                       os.path.join(sp, "folder.jpg")]
        else:
            targets = [os.path.join(sp, "fanart.jpg")]

        existing = [t for t in targets if os.path.isfile(t)]
        if existing:
            _make_backup(movie, *existing)

        self._status_lbl.configure(text="Downloading full resolution…")
        self.update_idletasks()

        def _worker():
            # Download to first target, then copy to additional targets
            primary = targets[0]
            ok, err = _tmdb_download_image(image_url, primary)
            if not ok:
                self.after(0, lambda m=err: (
                    messagebox.showerror("Download Failed", m),
                    self._status_lbl.configure(text="Download failed")))
                return
            # Copy to remaining targets (poster → folder.jpg)
            try:
                for extra in targets[1:]:
                    import shutil as _shutil
                    _shutil.copy2(primary, extra)
            except Exception as ce:
                logger.warning(f"_apply_image: could not copy to extra target: {ce}")
            self.applied = True
            logger.info(f"Fetched image for '{movie}': {image_url}")
            self.after(0, lambda: (
                messagebox.showinfo("Fetch Complete",
                    "Saved:\n" + "\n".join(os.path.basename(t) for t in targets)),
                self.destroy()))

        threading.Thread(target=_worker, daemon=True).start()





# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# NEW v0.17.0 / REBUILT v0.17.2 — Fetch Backdrop Dialog
# ══════════════════════════════════════════════════════════════════════════════

class _FetchBackdropDialog(tk.Toplevel):                       ### REBUILT v0.17.2 ###
    """
    Fetch Backdrops — download and manage TMDB backdrops for one movie.

    LEFT panel (scrollable):
      Shows existing local backdrop*.jpg files.
      Each row: thumbnail (top) + filename + "Replace with selected" button (below).
      Replace buttons are disabled until a TMDB image is selected on the right.
      Clicking Replace immediately downloads the selected TMDB backdrop and
      overwrites that local file (after backup).

    RIGHT panel (scrollable canvas, paginated):
      Shows TMDB backdrop thumbnails.  Click a row to select it (highlighted).

    Footer: only a Cancel button (no Apply — replaced by per-row Replace buttons).
    """

    _BG        = "#1e1e2e"
    _PANEL     = "#313244"
    _ROW_A     = "#252535"
    _ROW_B     = "#2a2a3e"
    _SEL_BG    = "#1c3a4a"
    _TXT       = "#cdd6f4"
    _DIM       = "#6c7086"
    _GRN       = "#a6e3a1"
    _BLU       = "#89b4fa"
    _RED       = "#f38ba8"
    _ORG       = "#fab387"
    _PAGE_SIZE = 5
    _THUMB_W   = 300
    _THUMB_H   = 169    # 16:9
    _LOC_W     = 240
    _LOC_H     = 135
    _TMDB_BASE_THUMB = "https://image.tmdb.org/t/p/w500"
    _TMDB_BASE_ORIG  = "https://image.tmdb.org/t/p/original"

    def __init__(self, parent, row_data, tmdb_key, tmdb_id):
        super().__init__(parent)
        self.applied  = False
        self._row     = row_data
        self._key     = tmdb_key
        self._tmdb    = tmdb_id
        self._images  = []          # TMDB backdrop dicts
        self._local   = []          # list of (filename, abs_path)
        self._page_r  = 0           # TMDB page index
        self._sel_idx = None        # currently selected TMDB image index
        self._photo_local = []      # PhotoImage refs — local
        self._photo_tmdb  = []      # PhotoImage refs — TMDB
        self._replace_btns = {}     # fname → tk.Button
        self._dismissed   = set()   # filenames closed by user — never shown again

        movie_name = row_data.get("movie_name", row_data.get("subfolder", "?"))
        self.title(f"Fetch Backdrops — {movie_name}")
        self.configure(bg=self._BG)
        self.transient(parent)
        self.resizable(True, True)
        self.geometry("1140x760")
        self.minsize(860, 540)

        # ── Header ────────────────────────────────────────────────────────────
        tk.Label(self,
                 text=f"Fetch Backdrops  ·  {movie_name}  ·  TMDB ID: {tmdb_id}",
                 font=("Helvetica", 10, "bold"), bg=self._BG, fg=self._TXT
                 ).pack(pady=(10, 2))
        self._status_lbl = tk.Label(self, text="Loading…",
                                    font=("Helvetica", 8), bg=self._BG, fg=self._DIM)
        self._status_lbl.pack()

        # ── Body ──────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=self._BG)
        body.pack(fill="both", expand=True, padx=12, pady=6)

        # ── LEFT — local backdrops (scrollable) ───────────────────────────────
        left_outer = tk.Frame(body, bg=self._PANEL, width=310)
        left_outer.pack(side="left", fill="y", padx=(0, 10))
        left_outer.pack_propagate(False)

        tk.Label(left_outer, text="Local Backdrops",
                 font=("Helvetica", 9, "bold"), bg=self._PANEL, fg=self._BLU
                 ).pack(pady=(8, 2))
        tk.Label(left_outer,
                 text="Select a TMDB image on the right,\nthen click Replace to overwrite a local file.",
                 bg=self._PANEL, fg=self._DIM,
                 font=("Helvetica", 8), wraplength=280, justify="center"
                 ).pack(padx=6, pady=(0, 6))

        # Scrollable canvas for local list
        lc_frame = tk.Frame(left_outer, bg=self._PANEL)
        lc_frame.pack(fill="both", expand=True)
        lc_frame.columnconfigure(0, weight=1)
        lc_frame.rowconfigure(0, weight=1)

        self._lcanvas = tk.Canvas(lc_frame, bg=self._PANEL, highlightthickness=0)
        l_vsb = ttk.Scrollbar(lc_frame, orient="vertical", command=self._lcanvas.yview)
        self._lcanvas.configure(yscrollcommand=l_vsb.set)
        l_vsb.grid(row=0, column=1, sticky="ns")
        self._lcanvas.grid(row=0, column=0, sticky="nsew")

        self._local_frame = tk.Frame(self._lcanvas, bg=self._PANEL)
        self._lcanvas_win = self._lcanvas.create_window(
            (0, 0), window=self._local_frame, anchor="nw")
        self._local_frame.bind("<Configure>",
            lambda e: self._lcanvas.configure(scrollregion=self._lcanvas.bbox("all")))
        self._lcanvas.bind("<Configure>",
            lambda e: self._lcanvas.itemconfig(self._lcanvas_win, width=e.width))
        self._lcanvas.bind("<Enter>",
            lambda e: (
                self._lcanvas.bind_all("<MouseWheel>", self._on_lwheel),
                self._lcanvas.bind_all("<Button-4>",
                    lambda ev: self._lcanvas.yview_scroll(-1, "units")),   ### NEW v0.18.0 ###
                self._lcanvas.bind_all("<Button-5>",
                    lambda ev: self._lcanvas.yview_scroll(1, "units"))))   ### NEW v0.18.0 ###
        self._lcanvas.bind("<Leave>",
            lambda e: (
                self._lcanvas.unbind_all("<MouseWheel>"),
                self._lcanvas.unbind_all("<Button-4>"),                    ### NEW v0.18.0 ###
                self._lcanvas.unbind_all("<Button-5>")))

        # Footer label inside left panel
        tk.Label(left_outer,
                 text="(No local backdrops → download creates a new file)",
                 bg=self._PANEL, fg=self._DIM,
                 font=("Helvetica", 7), wraplength=280, justify="center"
                 ).pack(padx=6, pady=(2, 6))

        # ── RIGHT — TMDB backdrops (scrollable canvas, paginated) ─────────────
        rf = tk.Frame(body, bg=self._BG)
        rf.pack(side="left", fill="both", expand=True)
        tk.Label(rf, text="TMDB Backdrops  (sorted by resolution, highest first)",
                 font=("Helvetica", 9, "bold"), bg=self._BG, fg=self._BLU
                 ).pack(pady=(0, 4))

        cf = tk.Frame(rf, bg=self._BG); cf.pack(fill="both", expand=True)
        cf.columnconfigure(0, weight=1); cf.rowconfigure(0, weight=1)
        self._canvas = tk.Canvas(cf, bg=self._BG, highlightthickness=0)
        r_vsb = ttk.Scrollbar(cf, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=r_vsb.set)
        r_vsb.grid(row=0, column=1, sticky="ns")
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._grid_frame = tk.Frame(self._canvas, bg=self._BG)
        self._grid_win   = self._canvas.create_window(
            (0, 0), window=self._grid_frame, anchor="nw")
        self._grid_frame.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._grid_win, width=e.width))
        self._canvas.bind("<Enter>",
            lambda e: (
                self._canvas.bind_all("<MouseWheel>", self._on_rwheel),
                self._canvas.bind_all("<Button-4>",
                    lambda ev: self._canvas.yview_scroll(-1, "units")),    ### NEW v0.18.0 ###
                self._canvas.bind_all("<Button-5>",
                    lambda ev: self._canvas.yview_scroll(1, "units"))))    ### NEW v0.18.0 ###
        self._canvas.bind("<Leave>",
            lambda e: (
                self._canvas.unbind_all("<MouseWheel>"),
                self._canvas.unbind_all("<Button-4>"),                     ### NEW v0.18.0 ###
                self._canvas.unbind_all("<Button-5>")))

        tk.Label(rf, text="Click a TMDB backdrop to select it.",
                 bg=self._BG, fg=self._DIM, font=("Helvetica", 8)
                 ).pack(anchor="w", padx=4, pady=(4, 0))

        # Right pagination
        rnav = tk.Frame(rf, bg=self._BG); rnav.pack(pady=(4, 0))
        self._r_back = tk.Button(rnav, text="◀ Back",
                                 bg="#45475a", fg=self._TXT, relief="flat",
                                 cursor="hand2", font=("Helvetica", 8),
                                 padx=6, pady=3, state="disabled",
                                 command=self._tmdb_back)
        self._r_back.pack(side="left", padx=3)
        self._r_more = tk.Button(rnav, text="Show More ▶",
                                 bg="#45475a", fg=self._TXT, relief="flat",
                                 cursor="hand2", font=("Helvetica", 8),
                                 padx=6, pady=3, state="disabled",
                                 command=self._tmdb_more)
        self._r_more.pack(side="left", padx=3)

        # ── Footer ────────────────────────────────────────────────────────────
        sep = tk.Frame(self, bg="#45475a", height=1)
        sep.pack(fill="x", padx=12, pady=(4, 0))
        bf = tk.Frame(self, bg=self._BG); bf.pack(pady=(8, 12))
        # "Download as New" button — always available once a TMDB image is selected
        self._new_btn = tk.Button(bf, text="  Download as New File  ",
                                  bg=self._BLU, fg="#1e1e2e", relief="flat",
                                  cursor="hand2", font=("Helvetica", 10, "bold"),
                                  padx=10, pady=5, state="disabled",
                                  command=self._download_new)
        self._new_btn.pack(side="left", padx=6)
        tk.Button(bf, text="  Cancel  ",
                  bg="#45475a", fg=self._TXT, relief="flat",
                  cursor="hand2", font=("Helvetica", 10, "bold"),
                  padx=10, pady=5,
                  command=self.destroy).pack(side="left", padx=6)

        # Position dialog
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")

        threading.Thread(target=self._load_local, daemon=True).start()
        threading.Thread(target=self._load_tmdb,  daemon=True).start()

    # ── Scroll helpers ────────────────────────────────────────────────────────
    def _on_lwheel(self, e):
        self._lcanvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _on_rwheel(self, e):
        self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ── Local backdrops ───────────────────────────────────────────────────────
    def _load_local(self):
        sp = self._row.get("subfolder_path", "")
        local = []
        try:
            if os.path.isdir(sp):
                for fname in sorted(os.listdir(sp)):
                    if re.match(r'^backdrop\d*\.jpg$', fname, re.IGNORECASE):
                        local.append((fname, os.path.join(sp, fname)))
        except Exception:
            pass
        self._local = [(f, p) for f, p in local if f not in self._dismissed]
        self.after(0, self._render_local)

    def _render_local(self):
        if not self.winfo_exists():
            return
        for w in self._local_frame.winfo_children():
            w.destroy()
        self._photo_local.clear()
        self._replace_btns.clear()

        if not self._local:
            tk.Label(self._local_frame,
                     text="No local backdrops found.\nA new file will be created\nwhen you download.",
                     bg=self._PANEL, fg=self._DIM,
                     font=("Helvetica", 9), justify="center").pack(pady=20, padx=10)
        else:
            for fname, fpath in self._local:
                row_f = tk.Frame(self._local_frame, bg=self._ROW_A)
                row_f.pack(fill="x", padx=4, pady=4)

                # Thumbnail at top of card — no width= set; PIL thumbnail controls size ### FIX v0.17.3 ###
                thumb_lbl = tk.Label(row_f, bg=self._ROW_A)
                thumb_lbl.pack(pady=(6, 2), padx=6)
                if _PIL_AVAILABLE and os.path.isfile(fpath):
                    try:
                        img = _PILImage.open(fpath)
                        img.thumbnail((self._LOC_W, self._LOC_H), _PILImage.LANCZOS)
                        photo = _PILImageTk.PhotoImage(img)
                        self._photo_local.append(photo)
                        thumb_lbl.configure(image=photo)
                    except Exception:
                        thumb_lbl.configure(text="[Preview\nunavailable]",
                                            fg=self._DIM, font=("Helvetica", 7))
                else:
                    thumb_lbl.configure(
                        text="[No PIL]" if not _PIL_AVAILABLE else "[Missing]",
                        fg=self._DIM, font=("Helvetica", 7))

                # Filename + pixel dimensions below thumbnail
                dims = get_image_dimensions(fpath)
                name_text = f"{fname} ({dims})" if dims else fname
                tk.Label(row_f, text=name_text,
                         bg=self._ROW_A, fg=self._TXT,
                         font=("Consolas", 8), anchor="center"
                         ).pack(fill="x", padx=6, pady=(0, 2))

                # Button row: Replace + Close side by side
                btn_row = tk.Frame(row_f, bg=self._ROW_A)
                btn_row.pack(fill="x", padx=8, pady=(0, 6))
                # Replace button — greyed out until TMDB selection
                btn = tk.Button(btn_row,
                                text="Replace",
                                bg="#45475a", fg=self._DIM,
                                relief="flat", cursor="arrow",
                                font=("Helvetica", 8, "bold"),
                                padx=6, pady=3,
                                state="disabled",
                                command=lambda fn=fname, fp=fpath: self._replace_local(fn, fp))
                btn.pack(side="left", fill="x", expand=True, padx=(0, 2))
                self._replace_btns[fname] = btn
                # Close button — always active, removes this card from the panel
                tk.Button(btn_row,
                          text="Close",
                          bg="#45475a", fg=self._TXT,
                          relief="flat", cursor="hand2",
                          font=("Helvetica", 8),
                          padx=6, pady=3,
                          command=lambda fn=fname: self._dismiss_local(fn)
                          ).pack(side="left", padx=(2, 0))

        # Activate buttons if a TMDB image is already selected
        if self._sel_idx is not None:
            self._activate_replace_buttons()

    def _activate_replace_buttons(self):
        """Enable all Replace buttons (called after a TMDB image is selected)."""
        for btn in self._replace_btns.values():
            try:
                btn.configure(state="normal", bg=self._ORG,
                              fg="#1e1e2e", cursor="hand2")
            except Exception:
                pass

    def _deactivate_replace_buttons(self):
        for btn in self._replace_btns.values():
            try:
                btn.configure(state="disabled", bg="#45475a",
                              fg=self._DIM, cursor="arrow")
            except Exception:
                pass

    # ── TMDB backdrops ────────────────────────────────────────────────────────
    def _load_tmdb(self):
        try:
            url = (f"https://api.themoviedb.org/3/movie/{self._tmdb}"
                   f"/images?api_key={self._key}")
            data = _tmdb_fetch_json(url, timeout=15)
            imgs = data.get("backdrops", [])
            imgs.sort(key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True)
            self._images = imgs
        except Exception as e:
            err_msg = _tmdb_error_message(e)
            logger.warning(f"FetchBackdropDialog: {err_msg}")
            self._images = []
            self.after(0, lambda m=err_msg: self._status_lbl.configure(
                text=m, fg=self._RED))
            return
        self.after(0, lambda: self._status_lbl.configure(
            text=f"{len(self._images)} TMDB backdrop(s) found."))
        self.after(0, self._render_tmdb)

    def _render_tmdb(self):
        if not self.winfo_exists():
            return
        for w in self._grid_frame.winfo_children():
            w.destroy()
        self._photo_tmdb.clear()

        start = self._page_r * self._PAGE_SIZE
        page  = self._images[start: start + self._PAGE_SIZE]

        if not page:
            tk.Label(self._grid_frame, text="No TMDB backdrops found.",
                     bg=self._BG, fg=self._RED,
                     font=("Helvetica", 10)).pack(padx=20, pady=20)
            return

        for idx, img in enumerate(page):
            global_idx = start + idx
            fp   = img.get("file_path", "")
            w2   = img.get("width", 0); h2 = img.get("height", 0)
            sz   = img.get("file_size", 0)
            rank = global_idx + 1
            is_sel = (self._sel_idx == global_idx)
            row_bg = self._SEL_BG if is_sel else (self._ROW_A if idx % 2 == 0 else self._ROW_B)
            bdr_c  = "#89b4fa" if is_sel else row_bg

            row_f = tk.Frame(self._grid_frame, bg=row_bg,
                             highlightbackground=bdr_c, highlightthickness=2 if is_sel else 0,
                             cursor="hand2")
            row_f.pack(fill="x", padx=4, pady=5)
            row_f.bind("<Button-1>", lambda e, gi=global_idx: self._select_tmdb(gi))

            thumb_lbl = tk.Label(row_f, bg=row_bg, cursor="hand2")
            thumb_lbl.pack(side="left", padx=(8, 10), pady=6)
            thumb_lbl.bind("<Button-1>", lambda e, gi=global_idx: self._select_tmdb(gi))

            info_f = tk.Frame(row_f, bg=row_bg, cursor="hand2")
            info_f.pack(side="left", fill="both", expand=True, pady=6)
            info_f.bind("<Button-1>", lambda e, gi=global_idx: self._select_tmdb(gi))

            sz_txt = f"  ·  ~{format_size(sz)}" if sz else ""
            ratio  = _friendly_ratio(w2, h2)
            tk.Label(info_f,
                     text=f"#{rank}   {w2}×{h2} ({ratio}){sz_txt}",
                     bg=row_bg, fg=self._TXT,
                     font=("Consolas", 9), anchor="w",
                     cursor="hand2").pack(fill="x", padx=4, pady=(6, 2))
            if is_sel:
                tk.Label(info_f, text="✓  Selected — use Replace buttons on the left",
                         bg=row_bg, fg=self._GRN,
                         font=("Helvetica", 8, "bold"), anchor="w").pack(fill="x", padx=4)

            def _load_thumb(fl=fp, lbl=thumb_lbl, rbg=row_bg, gi=global_idx):
                import urllib.request, io
                try:
                    req = urllib.request.Request(
                        self._TMDB_BASE_THUMB + fl,
                        headers={"User-Agent": "MediaClinic/0.17.0"})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        raw = resp.read()
                    if _PIL_AVAILABLE:
                        img_pil = _PILImage.open(io.BytesIO(raw))
                        img_pil.thumbnail((self._THUMB_W, self._THUMB_H),
                                          _PILImage.LANCZOS)
                        photo = _PILImageTk.PhotoImage(img_pil)
                        self._photo_tmdb.append(photo)
                        def _set(l=lbl, p=photo):
                            if l.winfo_exists(): l.configure(image=p)
                        self.after(0, _set)
                except Exception:
                    pass
            threading.Thread(target=_load_thumb, daemon=True).start()

        total = len(self._images)
        self._r_back.configure(state="normal" if self._page_r > 0 else "disabled")
        self._r_more.configure(
            state="normal" if start + self._PAGE_SIZE < total else "disabled")
        self._canvas.yview_moveto(0)

    def _select_tmdb(self, global_idx):
        self._sel_idx = global_idx
        self._new_btn.configure(state="normal")
        self._activate_replace_buttons()
        self._render_tmdb()

    def _tmdb_back(self):
        self._page_r = max(0, self._page_r - 1)
        self._render_tmdb()

    def _tmdb_more(self):
        self._page_r += 1
        self._render_tmdb()

    # ── Download actions ──────────────────────────────────────────────────────
    def _get_selected_image_url(self):
        """Return the original-size URL of the currently selected TMDB backdrop."""
        if self._sel_idx is None or self._sel_idx >= len(self._images):
            return None
        return self._TMDB_BASE_ORIG + self._images[self._sel_idx].get("file_path", "")

    def _download_to(self, target_path, on_done):
        """Download selected TMDB image to target_path using resilient downloader."""  ### UPDATED v0.18.0 ###
        url = self._get_selected_image_url()
        if not url:
            on_done(False, "No TMDB image selected.")
            return
        self._status_lbl.configure(text="Downloading…")
        self.update_idletasks()

        def _worker():
            ok, err = _tmdb_download_image(url, target_path)
            if ok:
                self.applied = True
            self.after(0, lambda: on_done(ok, target_path if ok else err))

        threading.Thread(target=_worker, daemon=True).start()

    def _replace_local(self, fname, fpath):
        """Replace a specific local file with the selected TMDB backdrop."""
        if self._sel_idx is None:
            messagebox.showwarning("No Selection",
                "Please click a TMDB backdrop on the right first.")
            return
        sp    = self._row.get("subfolder_path", "")
        movie = self._row.get("movie_name", self._row.get("subfolder", "?"))
        if os.path.isfile(fpath):
            _make_backup(movie, fpath)

        def _done(ok, msg):
            if ok:
                self._status_lbl.configure(text=f"Replaced: {fname}")
                messagebox.showinfo("Done", f"Replaced:\n{fname}")
                self._load_local_and_refresh()
            else:
                self._status_lbl.configure(text="Download failed.")
                messagebox.showerror("Download Failed", msg)

        self._download_to(fpath, _done)

    def _download_new(self):
        """Download selected TMDB backdrop as a new backdropN.jpg file."""
        if self._sel_idx is None:
            messagebox.showwarning("No Selection",
                "Please click a TMDB backdrop on the right first.")
            return
        sp    = self._row.get("subfolder_path", "")
        n     = next_backdrop_number(sp)
        fname = "backdrop.jpg" if n == 0 else f"backdrop{n}.jpg"
        fpath = os.path.join(sp, fname)

        def _done(ok, msg):
            if ok:
                self._status_lbl.configure(text=f"Saved: {fname}")
                messagebox.showinfo("Done", f"Saved as:\n{fname}")
                self._load_local_and_refresh()
            else:
                self._status_lbl.configure(text="Download failed.")
                messagebox.showerror("Download Failed", msg)

        self._download_to(fpath, _done)

    def _load_local_and_refresh(self):
        """Reload the local file list after a download."""
        threading.Thread(target=self._load_local, daemon=True).start()

    def _dismiss_local(self, fname):
        """Remove a local backdrop card from the panel without deleting the file.
        The dismissal is permanent for this session — refresh won't bring it back."""
        self._dismissed.add(fname)
        self._local = [(f, p) for f, p in self._local if f != fname]
        self._render_local()

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
        self._scan_label    = "Full Scan"                      ### NEW v0.17.0 ###
        self._use_ffprobe = tk.BooleanVar(value=SETTINGS.get("use_ffprobe", True))
        ### NEW v0.13.0 — track lang code so _on_settings_changed only re-runs
        # the expensive compute_lang_ok loop when the target language changed.
        self._last_lang_iso = SETTINGS.get("lang_ok_code", "PT")
        # FIX v0.16.0 — cache FFmpeg test result so _rclick never blocks the UI.
        # None = not yet tested; (ff_ok, fp_ok) after first async test completes.
        self._ffmpeg_status = None   ### FIX v0.16.0 ###
        self._sel_anchor    = None   ### NEW v0.16.1 — Shift+Arrow anchor index ###
        self._sel_active_idx = None  ### NEW v0.17.0 — Shift+Arrow active (moving) end ###
        self._build_ui()
        self._update_extract_btn_state()
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)   ### NEW v0.18.0 — save column widths on close ###
        self.after(200, self._restore_last_session)
        threading.Thread(target=self._async_test_ffmpeg, daemon=True).start()  ### FIX v0.16.0 ###

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
        settings_menu.add_command(label="⭐  Ratings",                     ### NEW v0.15.0 ###
                                  command=lambda: SettingsDialog(self, tab=10))
        settings_menu.add_command(label="🎬  Genres",
                                  command=lambda: SettingsDialog(self, tab=6))
        settings_menu.add_command(label="🏷  NFO-XML Tags",
                                  command=lambda: SettingsDialog(self, tab=7))
        ### NEW v0.13.0 — synchronize menubar with all dialog tabs ###
        settings_menu.add_command(label="🎨  User Interface",
                                  command=lambda: SettingsDialog(self, tab=8))
        settings_menu.add_command(label="💾  Backup",
                                  command=lambda: SettingsDialog(self, tab=9))

        tools_menu = tk.Menu(menubar, tearoff=0, bg="#313244", fg="#cdd6f4",  ### NEW v0.15.0 — redesigned ###
                             activebackground="#585b70", activeforeground="#cdd6f4")
        menubar.add_cascade(label="Tools", menu=tools_menu)
        ### NEW v0.16.0 — Save/Open Scan Results (first, separated by divider) ###
        tools_menu.add_command(label="💾  Save Scan Results",
                               command=self._save_scan_results)
        tools_menu.add_command(label="📂  Open Scan Results",
                               command=self._open_scan_results)
        tools_menu.add_separator()
        tools_menu.add_command(label="⭐  Sync Ratings Online — All Movies",  ### NEW v0.15.0 ###
                               command=self._sync_ratings_all)
        ### NEW v0.16.0 — Normalize Sources All Movies ###
        tools_menu.add_command(label="🔗  Normalize Sources — All Movies",
                               command=self._normalize_sources_all)
        ### NEW v0.16.0 — Search Sources All Movies ###
        tools_menu.add_command(label="🔎  Search Sources — All Movies",
                               command=self._search_sources_all)
        tools_menu.add_command(label="🎬  Normalize Genres — All Movies",
                               command=self._normalize_genres_all)
        tools_menu.add_command(label="🔍  Run Improvements Check — All Movies",  ### NEW v0.15.0 ###
                               command=self._run_improvements_all)
        tools_menu.add_command(label="🔁  Refresh Icons — All Movies",          ### NEW v0.15.0 ###
                               command=self._refresh_icons)
        tools_menu.add_separator()
        tools_menu.add_command(label="🗑  Delete All extrafanart Subfolders (legacy)",  ### NEW v0.15.0 ###
                               command=self._delete_extrafanart_all)

        ### NEW v0.11.0 — Help menu last; F1 opens help globally ###
        help_menu = tk.Menu(menubar, tearoff=0, bg="#313244", fg="#cdd6f4",
                            activebackground="#585b70", activeforeground="#cdd6f4")
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="📖  Help…  (F1)", command=lambda: HelpDialog(self))
        ### NEW v0.16.0 — Version History in its own Help menu entry ###
        help_menu.add_command(label="📋  Version History…",
                              command=lambda: HelpDialog(self, tab=7))

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
        self.scan_btn = tk.Button(picker, text="  Full Scan  ", bg="#a6e3a1", fg="#1e1e2e",
                                  command=self._scan, **btn_kw)
        self.scan_btn.pack(side="left", padx=(6,0))
        _add_btn_tooltip(self.scan_btn,                                    ### NEW v0.17.0 ###
            "Full Scan (Rebuild Library)\n"
            "Performs a complete rebuild of the library.\n"
            "Re-reads all folders, metadata, images, and warnings.")
        self.update_btn = tk.Button(picker, text="  Quick Scan  ", bg="#89dceb", fg="#1e1e2e",
                                    command=self._update_scan, **btn_kw)
        self.update_btn.pack(side="left", padx=(6,0))
        _add_btn_tooltip(self.update_btn,                                  ### NEW v0.17.0 ###
            "Quick Scan (Update Library)\n"
            "Updates only movies that were added, removed, or modified.\n"
            "Much faster than a Full Scan.")
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
        self.tree.bind("<Button-1>",   self._reset_sel_anchor, add="+")  ### NEW v0.16.1 ###

        ### NEW v0.17.0 — Custom column resize: only active column changes width ###
        self._col_resize_state = {}   # {col_id: (start_x, start_w)}
        self._col_resize_just_ended = False  ### FIX v0.17.2-bug3 — suppress dblclick guard after drag ###
        self.tree.bind("<Button-1>",   self._col_resize_start, add="+")
        self.tree.bind("<B1-Motion>",  self._col_resize_drag,  add="+")
        self.tree.bind("<ButtonRelease-1>", self._col_resize_end, add="+")

        ### NEW v0.13.1 — Jump-to-letter (A–Z / 0–9) when Treeview has focus ###
        # State for cycling on repeat keys (same char pressed again advances).
        self._jump_last_char  = None
        self._jump_last_iid   = None
        self._jump_index      = {}   # char → int index for cycling  ### NEW v0.17.2 ###
        # Bind DIRECTLY to the tree widget so Tk routes the event only
        # when the tree (or its internal child) has focus.
        # Also bind to the App root with a strict widget check as belt-and-braces.
        self.tree.bind("<KeyPress>", self._kb_jump_to_letter, add="+")  ### NEW v0.17.2 ###
        self.bind("<KeyPress>", self._kb_jump_to_letter, add="+")       ### NEW v0.17.2 ###
        # Ensure tree gets Tk focus whenever the user clicks a row
        self.tree.bind("<Button-1>", lambda e: self.tree.focus_set(), add="+")  ### NEW v0.17.2 ###

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
        ### FIX v0.17.2-bug3 — skip auto-size if a resize drag just finished ###
        if self._col_resize_just_ended:
            self._col_resize_just_ended = False
            return
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

    ### NEW v0.13.1 — Jump-to-letter / digit on the Movie Name column ###
    @staticmethod
    def _strip_diacritics(s):
        """ASCII-fold a string for case-insensitive prefix matching.
        'Ångström' -> 'Angstrom', 'Abril Despedaçado' -> 'Abril Despedacado'.
        """
        if not s:
            return ""
        nfkd = unicodedata.normalize("NFKD", s)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    ### NEW v0.17.2 — Jump-to-Letter Final Fix ###
    def _kb_jump_to_letter(self, event):
        """Jump selection to the next row whose movie name starts with the
        pressed key (A–Z, a–z, 0–9).  Cycles per-character on repeat press.

        Strategy (v0.17.2):
        - Bound to BOTH self.tree and self (App root) to cover all focus cases.
        - Guard: skip if any text-input widget (Entry/Text/Combobox/Spinbox) has focus.
        - Use event.keysym as primary char source (works even when event.char is empty).
        - Per-character index dict for cycling (spec-compliant state management).
        """
        # ── Guard 1: skip if fired from a text-input widget ───────────────────
        # This preserves normal typing in search boxes, spinboxes, etc.
        try:
            focused = self.focus_get()
            if focused is not None:
                cls = focused.__class__.__name__
                if cls in ("Entry", "Text", "Spinbox") or \
                        isinstance(focused, (tk.Entry, tk.Text, tk.Spinbox)):
                    return
                # Also skip ttk Entry/Combobox
                try:
                    import tkinter.ttk as _ttk
                    if isinstance(focused, (_ttk.Entry, _ttk.Combobox, _ttk.Spinbox)):
                        return
                except Exception:
                    pass
        except Exception:
            pass

        # ── Guard 2: skip modifier combos (Ctrl, Alt, Cmd) ───────────────────
        # Do NOT include 0x8 — on Windows this is NumLock/Mod1 and is set
        # on plain letter keypresses, blocking all jump-to-letter input.  ### FIX v0.17.3 ###
        modifier_mask = 0x4 | 0x20000  # Ctrl | Alt only
        if event.state & modifier_mask:
            return

        # ── Guard 3: skip if no data is loaded ───────────────────────────────
        if not self._results:
            return

        # ── Resolve the character ─────────────────────────────────────────────
        # Use keysym first (always populated), fall back to event.char
        # keysym for letters: "a".."z", "A".."Z", digits: "0".."9"
        ch = ""
        ks = event.keysym or ""
        if len(ks) == 1 and (ks.isalpha() or ks.isdigit()):
            ch = ks
        elif event.char and len(event.char) == 1 and \
                (event.char.isalpha() or event.char.isdigit()):
            ch = event.char

        if not ch:
            return

        target = self._strip_diacritics(ch).upper()
        if not target or not (target.isalpha() or target.isdigit()):
            return

        # ── Build match list ──────────────────────────────────────────────────
        children = self.tree.get_children()
        if not children:
            return "break"

        matches = []
        for iid in children:
            d = self._item_map.get(iid)
            if not d:
                continue
            name = (d.get("movie_name") or d.get("subfolder") or "").lstrip()
            folded = self._strip_diacritics(name).upper().lstrip()
            if folded and folded[0] == target:
                matches.append(iid)

        if not matches:
            return "break"

        # ── Per-char cycling index ────────────────────────────────────────────
        if target != self._jump_last_char:
            # Different key pressed → reset this char's index
            self._jump_index[target] = 0
            self._jump_last_char = target
        else:
            # Same key → advance
            cur = self._jump_index.get(target, 0)
            self._jump_index[target] = (cur + 1) % len(matches)

        idx = self._jump_index.get(target, 0)
        if idx >= len(matches):
            idx = 0
            self._jump_index[target] = 0
        next_iid = matches[idx]

        # ── Apply ─────────────────────────────────────────────────────────────
        self.tree.selection_set(next_iid)
        self.tree.focus(next_iid)
        self.tree.see(next_iid)
        self._jump_last_iid = next_iid
        return "break"
    ### END v0.17.2 — Jump-to-Letter Final Fix ###

    def _shift_up(self, event):                                ### REWRITTEN v0.17.0 ###
        """Shift+Up: shrink bottom of selection toward anchor, or extend above anchor."""
        children = list(self.tree.get_children())
        if not children: return "break"
        sel = self.tree.selection()
        if not sel: return "break"

        # Initialise anchor on first Shift press — anchor stays at the clicked row
        if self._sel_anchor is None:
            self._sel_anchor = children.index(sel[0])
        if self._sel_active_idx is None:
            self._sel_active_idx = children.index(sel[-1])

        anchor = self._sel_anchor
        new_active = max(0, self._sel_active_idx - 1)
        self._sel_active_idx = new_active

        # Continuous range between anchor and new active end
        lo = min(anchor, new_active)
        hi = max(anchor, new_active)
        self.tree.selection_set(children[lo:hi + 1])
        self.tree.see(children[new_active])
        return "break"

    def _shift_down(self, event):                              ### REWRITTEN v0.17.0 ###
        """Shift+Down: extend bottom of selection downward from anchor."""
        children = list(self.tree.get_children())
        if not children: return "break"
        sel = self.tree.selection()
        if not sel: return "break"

        if self._sel_anchor is None:
            self._sel_anchor = children.index(sel[0])
        if self._sel_active_idx is None:
            self._sel_active_idx = children.index(sel[-1])

        anchor = self._sel_anchor
        new_active = min(len(children) - 1, self._sel_active_idx + 1)
        self._sel_active_idx = new_active

        lo = min(anchor, new_active)
        hi = max(anchor, new_active)
        self.tree.selection_set(children[lo:hi + 1])
        self.tree.see(children[new_active])
        return "break"

    def _reset_sel_anchor(self, event=None):                   ### NEW v0.16.1 ###
        """Reset anchor on plain single click so next Shift starts fresh."""
        self._sel_anchor     = None
        self._sel_active_idx = None                            ### NEW v0.17.0 ###

    # ── Custom column resize ──────────────────────────────────────────────────
    def _col_resize_start(self, event):                        ### FIX v0.17.0-bug3 ###
        """On Button-1 on a separator: snapshot ALL column widths as baseline."""
        region = self.tree.identify_region(event.x, event.y)
        if region != "separator":
            self._col_resize_state = {}
            return
        col_id = self.tree.identify_column(event.x)
        if not col_id:
            self._col_resize_state = {}
            return
        try:
            col_idx  = int(col_id.lstrip("#")) - 1
            all_cols = self.tree.cget("columns")
            col_name = all_cols[col_idx]
        except Exception:
            self._col_resize_state = {}
            return
        # Snapshot widths BEFORE built-in handler runs
        snapshot = {c: self.tree.column(c, "width") for c in all_cols}
        self._col_resize_state = {
            "col":      col_name,
            "start_x":  event.x,
            "start_w":  snapshot[col_name],
            "snapshot": snapshot,
            "all_cols": all_cols,
        }

    def _col_resize_drag(self, event):                         ### FIX v0.17.0-bug3 ###
        """On every B1-Motion: built-in has just modified adjacent columns.
        Restore all OTHER columns to their pre-drag widths so only the
        target column changes size."""
        st = self._col_resize_state
        if not st:
            return
        col      = st["col"]
        dx       = event.x - st["start_x"]
        new_w    = max(30, st["start_w"] + dx)
        snapshot = st["snapshot"]
        # Restore every column EXCEPT the target to its pre-drag width
        for c, w in snapshot.items():
            if c != col:
                try:
                    self.tree.column(c, width=w)
                except Exception:
                    pass
        # Set the target column to the dragged width
        self.tree.column(col, width=new_w)

    def _col_resize_end(self, event):                          ### FIX v0.17.0-bug3 ###
        """On mouse-up: apply the final width, clear state."""
        st = self._col_resize_state
        self._col_resize_state = {}
        if not st:
            return
        # Signal _on_header_dblclick_guard to skip its next invocation
        # (the heading command fires immediately after this on drag-release)
        self._col_resize_just_ended = True              ### FIX v0.17.2-bug3 ###
        col   = st["col"]
        dx    = event.x - st["start_x"]
        new_w = max(30, st["start_w"] + dx)
        snapshot = st["snapshot"]
        # Final correction: restore all others, set target
        for c, w in snapshot.items():
            if c != col:
                try:
                    self.tree.column(c, width=w)
                except Exception:
                    pass
        self.tree.column(col, width=new_w)

    # ── FFmpeg status bar ──────────────────────────────────────────────────────
    def _async_test_ffmpeg(self):                              ### FIX v0.16.0 ###
        """Run FFmpeg test off the main thread, then update the status widget."""
        ff_ok, fp_ok, ff_msg, fp_msg = _test_ffmpeg(FFMPEG_PATH, FFPROBE_PATH)
        self._ffmpeg_status = (ff_ok, fp_ok)
        self.after(0, lambda: self._build_ffmpeg_status(self._ff_frame))

    def _build_ffmpeg_status(self, parent):
        for w in parent.winfo_children(): w.destroy()
        # FIX v0.16.0 — never call _test_ffmpeg on the main thread.
        # Use cached result; show "Checking…" placeholder until it arrives.
        if self._ffmpeg_status is None:
            tk.Label(parent, text="FFmpeg…", font=("Helvetica",9,"bold"),
                     bg="#1e1e2e", fg="#6c7086").pack(side="left")
            return
        ff_ok, fp_ok = self._ffmpeg_status
        if ff_ok and fp_ok:
            lbl = tk.Label(parent, text="FFmpeg ✓", font=("Helvetica",9,"bold"),
                           bg="#1e1e2e", fg="#a6e3a1", cursor="hand2")
            lbl.pack(side="left")
            self._ff_tip = None
            ff_dir = os.path.dirname(FFMPEG_PATH) if FFMPEG_PATH else ""
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
        """Called by SettingsDialog on save — fully non-blocking.
        ### NEW v0.13.0 — UI freeze fix ###

        - Skip _build_ffmpeg_status() entirely on post-save refresh.
          That call ran two `subprocess.run(timeout=10)` ffprobe/ffmpeg version
          checks on the main thread, freezing the UI for up to 20 seconds.
          FFmpeg status is only refreshed when the user clicks "Test FFmpeg"
          inside the Settings dialog.
        - Skip the per-movie compute_lang_ok() loop unless the target language
          code actually changed.  That loop calls ffprobe per movie
          (timeout=20s each) and could freeze the UI for minutes on a
          large library.
        - Heavy work (per-movie quality reclassification, refresh_table)
          is scheduled with self.after(0, ...) so it runs AFTER the Settings
          dialog has fully destroyed.  This guarantees the dialog never
          appears stuck and the UI stays responsive.
        """
        iso = SETTINGS.get("lang_ok_code", "PT")
        self.tree.heading("lang_ok", text=f"{iso} OK?")

        # FIX v0.16.0 — invalidate cached FFmpeg status and re-test off-thread  ### FIX v0.16.0 ###
        # This handles the case where the user changed the FFmpeg path in Settings.
        self._ffmpeg_status = None
        self._build_ffmpeg_status(self._ff_frame)   # shows "FFmpeg…" placeholder
        threading.Thread(target=self._async_test_ffmpeg, daemon=True).start()

        # Capture whether the language code actually changed so we only
        # run the (potentially heavy) compute_lang_ok loop when needed.
        prev_iso = getattr(self, "_last_lang_iso", iso)
        lang_changed = (prev_iso != iso)
        self._last_lang_iso = iso

        # ── Deferred heavy work — runs after the Settings dialog is gone ──
        def _post_save_refresh():
            # 1. Re-evaluate lang_ok ONLY if the target language changed.
            #    compute_lang_ok() calls ffprobe per row (timeout=20s each),
            #    which would freeze the UI on a large library if always run.
            if lang_changed:
                for r in self._results:
                    try:
                        r["lang_ok"] = compute_lang_ok(
                            r.get("video_path"), r.get("subs_internal", []),
                            r.get("subs_external", []),
                            r.get("nfo_path") if r.get("nfo_exists") else None,
                            r.get("xml_path") if r.get("xml_exists") else None,
                            iso_code=iso)
                    except Exception:
                        pass

            # 2. Recompute image quality tiers using CACHED dims — zero disk I/O
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
            self._update_extract_btn_state()
            self._update_stats()

        # Schedule deferred refresh — runs AFTER the Settings dialog destroys
        self.after(0, _post_save_refresh)
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

        ### NEW v0.12.0 — Rating tooltip ### UPDATED v0.15.0 — votes + source ###
        if ci == COL_RATING:
            rs  = d.get("rating_str", "-")
            st  = d.get("rating_status", STATUS_MISSING)
            votes = d.get("rating_votes", 0)
            vsrc  = d.get("rating_votes_src", "")
            rsrc  = d.get("rating_src", "")
            if st == STATUS_MISSING:
                return "Rating: not found\nSources checked: NFO <rating>, XML <IMDBrating>, XML <Rating>"
            if st == STATUS_ERROR:
                return "Rating: parsing error — tag exists but value is non-numeric or malformed"
            # Build source description                          ### NEW v0.15.0 ###
            _rtag_map = {"nfo_rating": "<rating>", "xml_IMDBrating": "<IMDBrating>", "xml_Rating": "<Rating>"}
            _vtag_map = {"nfo_votes": "<votes>", "xml_Votes": "<Votes>", "xml_VoteCount": "<VoteCount>"}
            _rfile = "NFO" if rsrc.startswith("nfo") else "XML"
            _vfile = "NFO" if vsrc.startswith("nfo") else ("XML" if vsrc else "")
            _rtag  = _rtag_map.get(rsrc, rsrc)
            _vtag  = _vtag_map.get(vsrc, "")
            if not vsrc:
                src_str = f"{_rfile} ({_rtag}), no vote information found"
            elif _rfile == _vfile:
                if rsrc.startswith("nfo") and vsrc.startswith("nfo"):
                    src_str = f"NFO ({_rtag}, {_vtag})"
                else:
                    src_str = f"XML ({_rtag}, {_vtag})"
            else:
                src_str = f"{_rfile} ({_rtag}) and {_vfile} ({_vtag})"
            lines = [f"Rating: {rs}", f"Votes: {votes}", f"Source: {src_str}"]
            if st == STATUS_WARN:
                lines.append("(conflict — multiple sources differ)")
            return "\n".join(lines)

        ### NEW v0.16.0 — Votes tooltip ###
        if ci == COL_VOTES:
            vs  = d.get("votes_status", STATUS_MISSING)
            vi  = d.get("votes_int", 0)
            src = d.get("votes_src", "")
            _vtag_map = {"nfo_votes": "NFO <votes>", "xml_Votes": "XML <Votes>",
                         "xml_VoteCount": "XML <VoteCount>"}
            if vs == STATUS_MISSING:
                return "Votes: not found\nSources checked: NFO <votes>, XML <Votes>, XML <VoteCount>"
            if vs == STATUS_ERROR:
                return "Votes: parse error — tag exists but value is non-numeric or malformed"
            lines = [f"Votes: {vi:,}", f"Source: {_vtag_map.get(src, src)}"]
            if vs == STATUS_WARN:
                lines.append("(conflict — NFO <votes> and XML <Votes> differ)")
            return "\n".join(lines)

        ### NEW v0.16.0 — Source tooltip ###
        if ci == COL_SOURCE:
            imdb_v = d.get("source_imdb_val")
            tmdb_v = d.get("source_tmdb_val")
            imdb_st = d.get("source_imdb_status", STATUS_MISSING)
            tmdb_st = d.get("source_tmdb_status", STATUS_MISSING)
            imdb_all = d.get("source_imdb_all", [])
            tmdb_all = d.get("source_tmdb_all", [])
            lines = []
            if imdb_st == STATUS_ERROR:
                lines.append("IMDB: ✕ parse error")
            elif imdb_v:
                lines.append(f"IMDB: {imdb_v}")
                if len(imdb_all) > 1:
                    lines.append(f"  (conflict: {', '.join(imdb_all)})")
            else:
                lines.append("IMDB: Not Available")
            if tmdb_st == STATUS_ERROR:
                lines.append("TMDB: ✕ parse error")
            elif tmdb_v:
                lines.append(f"TMDB: {tmdb_v}")
                if len(tmdb_all) > 1:
                    lines.append(f"  (conflict: {', '.join(tmdb_all)})")
            else:
                lines.append("TMDB: Not Available")
            lines.append("Double-click to open on IMDB or TMDB website")
            return "\n".join(lines)

        # Poster column (merged — v0.12.0)
        if ci == COL_POSTER:
            if not d["poster_exists"]:
                _ep = d['poster_path'].replace("/", "\\")  ### NEW v0.15.0 ###
                return f"poster.jpg\n[MISSING]\nExpected: {_ep}"
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
                _ep = d['folder_path'].replace("/", "\\")  ### NEW v0.15.0 ###
                return f"folder.jpg\n[MISSING]\nExpected: {_ep}"
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
                _ep = d['fanart_path'].replace("/", "\\")  ### NEW v0.15.0 ###
                return f"fanart.jpg\n[MISSING]\nExpected: {_ep}"
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

        # Backdrops                                              ### NEW v0.15.0 — count + avg size ###
        if ci == COL_BACKDROPS:
            bc = d["backdrop_count"]
            if bc == 0:
                return "Backdrops: none found\nRight-click - Extract Backdrop(s) to generate"
            avg_kb = round(d.get("backdrop_avg_bytes", 0) / 1024)  ### NEW v0.15.0 ###
            return f"Backdrops: {bc} image files\nAverage Size: {avg_kb}kb"  ### NEW v0.15.0 ###

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

        # Audio tracks                                         ### FIX v0.15.0 ###
        if ci == COL_AUDIO:
            tracks = d.get("audio_tracks", [])
            if not tracks:
                return "Audio Tracks: 0\nNo audio track data — run scan with FFprobe enabled"
            lines = [f"Audio Tracks: {len(tracks)}"]
            for idx, t in enumerate(
                    sorted(tracks, key=lambda x: x.get("language", "")), 1):
                lang = t.get("language") or "Unknown"
                codec = t.get("codec") or "Unknown"
                channels = t.get("channels") or "Unknown"
                br = t.get("bitrate")
                bitrate_str = f"{br} kbps" if br is not None else "Unknown"
                if idx > 1:
                    lines.append("")
                lines.append(f"Track {idx}:")
                lines.append(f"  Language: {lang}")
                lines.append(f"  Codec: {codec}")
                lines.append(f"  Channels: {channels}")
                lines.append(f"  Bitrate: {bitrate_str}")
            return "\n".join(lines)

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

        ### NEW v0.16.0 — Source column double-click: popup to choose IMDB or TMDB ###
        def _open_source_choice(app, d):
            imdb_v = d.get("source_imdb_val")
            tmdb_v = d.get("source_tmdb_val")
            if not imdb_v and not tmdb_v:
                messagebox.showinfo("Source IDs", "No IMDB or TMDB ID found for this movie.")
                return
            dlg = tk.Toplevel(app)
            dlg.title("Open Source Website")
            dlg.configure(bg="#1e1e2e")
            dlg.resizable(False, False)
            dlg.transient(app)
            tk.Label(dlg, text="Open on which website?",
                     font=("Helvetica", 11, "bold"), bg="#1e1e2e", fg="#cdd6f4",
                     pady=12).pack(padx=24)
            btn_kw = dict(font=("Helvetica", 10, "bold"), relief="flat",
                          cursor="hand2", padx=16, pady=6)
            bf = tk.Frame(dlg, bg="#1e1e2e"); bf.pack(padx=24, pady=(0,16))
            if imdb_v:
                url_i = f"https://www.imdb.com/title/{imdb_v}"
                tk.Button(bf, text=f"IMDB  ({imdb_v})", bg="#f5c518", fg="#1e1e2e",
                          command=lambda u=url_i: (open_url_with_browser(u), dlg.destroy()),
                          **btn_kw).pack(side="left", padx=(0,8))
            else:
                tk.Button(bf, text="IMDB (not found)", state="disabled",
                          bg="#45475a", fg="#6c7086", **btn_kw).pack(side="left", padx=(0,8))
            if tmdb_v:
                url_t = f"https://www.themoviedb.org/movie/{tmdb_v}"
                tk.Button(bf, text=f"TMDB  ({tmdb_v})", bg="#01d277", fg="#1e1e2e",
                          command=lambda u=url_t: (open_url_with_browser(u), dlg.destroy()),
                          **btn_kw).pack(side="left")
            else:
                tk.Button(bf, text="TMDB (not found)", state="disabled",
                          bg="#45475a", fg="#6c7086", **btn_kw).pack(side="left")
            tk.Button(bf, text="Cancel", bg="#45475a", fg="#cdd6f4",
                      command=dlg.destroy, **btn_kw).pack(side="left", padx=(16,0))
            dlg.update_idletasks()
            x = app.winfo_rootx() + (app.winfo_width() - dlg.winfo_width()) // 2
            y = app.winfo_rooty() + (app.winfo_height() - dlg.winfo_height()) // 2
            dlg.geometry(f"+{x}+{y}")

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
            "open_source_choice": _open_source_choice,   ### NEW v0.16.0 ###
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
    def _rclick(self, e):                                      ### UPDATED v0.18.0 — reorganized into 5 sections ###
        if self._scanning: return
        iid = self.tree.identify_row(e.y)
        if not iid: return
        if iid not in self.tree.selection():
            self.tree.selection_set(iid)
        d = self._item_map.get(iid)
        if not d: return
        sel_iids = self.tree.selection()
        sel_data = [self._item_map[i] for i in sel_iids if i in self._item_map]
        multi    = len(sel_data) > 1

        m = self._ctx; m.delete(0, "end")

        # ── SECTION 1 — File Access & Artwork (single-movie only) ────────────
        if not multi:
            m.add_command(label="📂  Open Folder",
                          command=lambda: os_open(d["subfolder_path"]))
            m.add_separator()
            for lb, ke, kp in [("🖼  Open poster.jpg",  "poster_exists", "poster_path"),
                                ("🖼  Open folder.jpg",  "folder_exists", "folder_path"),
                                ("🖼  Open fanart.jpg",  "fanart_exists", "fanart_path")]:
                if d[ke]:  m.add_command(label=lb, command=lambda p=d[kp]: os_open(p))
                else:      m.add_command(label=lb + " (missing)", state="disabled")

            # FIX v0.16.0 — use cached FFmpeg status; never block _rclick
            ff_ok = self._ffmpeg_status[0] if self._ffmpeg_status else False
            if d["video_path"]:
                if ff_ok:
                    m.add_command(label="🎞  Extract Backdrop(s)",
                                  command=lambda: self._do_extract(d))
                m.add_command(label="🎬  Play Video",
                              command=lambda: os_open(d["video_path"]))
            else:
                m.add_command(label="🎬  Video (missing)", state="disabled")
            if d.get("subs_internal") or d.get("subs_external"):
                m.add_command(label="💬  Subtitles…",
                              command=lambda: SubtitleDialog(self, d["subfolder"], d))

            # ── SECTION 2 — Metadata Files ───────────────────────────────────
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

            # ── SECTION 3 — Online Resources ─────────────────────────────────
            m.add_separator()
            imdb_id = d.get("source_imdb_val")
            tmdb_id = d.get("source_tmdb_val")
            if imdb_id:
                url = f"https://www.imdb.com/title/{imdb_id}"
                m.add_command(label="🌐  Open on IMDb",
                              command=lambda u=url: open_url_with_browser(u))
            else:
                m.add_command(label="🌐  Open on IMDb (ID not found)", state="disabled")
            if tmdb_id:
                url = f"https://www.themoviedb.org/movie/{tmdb_id}"
                m.add_command(label="🌐  Open on TMDb",
                              command=lambda u=url: open_url_with_browser(u))
            else:
                m.add_command(label="🌐  Open on TMDb (ID not found)", state="disabled")
            # Open on Fanart.tv — disabled when no TMDB ID          ### NEW v0.18.0 ###
            if tmdb_id:
                m.add_command(label="🌐  Open on Fanart.tv",
                              command=lambda: self._open_fanart_tv(d))
            else:
                m.add_command(label="🌐  Open on Fanart.tv (ID not found)", state="disabled")
            m.add_command(label="🌐  Open on OpenSubtitles.org",
                          command=lambda: self._open_opensubtitles(d))
            m.add_command(label="📋  Copy Movie Name",
                          command=lambda: self._copy_movie_name(d))
            if SETTINGS.get("scraper_path", ""):
                m.add_command(label="🎬  Open in Scraper",
                              command=lambda: open_with_scraper(d["subfolder_path"]))

        # ── SECTION 4 — Maintenance & Metadata Operations ────────────────────
        m.add_separator()
        label_sel = f"🔍  Run Improvements Check ({len(sel_data)} movies)" if multi \
                    else "🔍  Run Improvements Check"
        m.add_command(label=label_sel,
                      command=lambda dd=sel_data: self._run_improvements_on(dd))

        label_sync = f"⭐  Sync Ratings ({len(sel_data)} movies)" if multi \
                     else "⭐  Sync Ratings from IMDb / TMDb"
        m.add_command(label=label_sync,
                      command=lambda dd=sel_data: self._sync_ratings(dd))

        label_nsrc = f"🔗  Normalize Sources ({len(sel_data)} movies)" if multi \
                     else "🔗  Normalize Sources"
        m.add_command(label=label_nsrc,
                      command=lambda dd=sel_data: self._normalize_sources_for(dd))

        label_ssrc = f"🔎  Search Sources ({len(sel_data)} movies)" if multi \
                     else "🔎  Search Sources"
        m.add_command(label=label_ssrc,
                      command=lambda dd=sel_data: self._search_sources_for(dd))

        label_genre = f"🎬  Normalize Genres ({len(sel_data)} movies)" if multi \
                      else "🎬  Normalize Genres"
        m.add_command(label=label_genre,
                      command=lambda dd=sel_data: self._normalize_genres_for(dd))

        _tmdb_key_set = bool(SETTINGS.get("tmdb_api_key", "").strip())
        _has_tmdb_id  = any(dd.get("source_tmdb_val") for dd in sel_data)
        _tip = " (no TMDB API key)" if not _tmdb_key_set else " (no TMDB ID found)"

        label_fp = f"🖼  Fetch Poster/Folder ({len(sel_data)} movies)" if multi \
                   else "🖼  Fetch Poster/Folder"
        if _tmdb_key_set and _has_tmdb_id:
            m.add_command(label=label_fp,
                          command=lambda dd=sel_data: self._fetch_poster_folder(dd))
        else:
            m.add_command(label=label_fp + _tip, state="disabled")

        label_ff2 = f"🎨  Fetch Fanart ({len(sel_data)} movies)" if multi \
                    else "🎨  Fetch Fanart"
        if _tmdb_key_set and _has_tmdb_id:
            m.add_command(label=label_ff2,
                          command=lambda dd=sel_data: self._fetch_fanart(dd))
        else:
            m.add_command(label=label_ff2 + _tip, state="disabled")

        label_fb = f"🖼  Fetch Backdrops ({len(sel_data)} movies)" if multi \
                   else "🖼  Fetch Backdrops"
        if _tmdb_key_set and _has_tmdb_id:
            m.add_command(label=label_fb,
                          command=lambda dd=sel_data: self._fetch_backdrops(dd))
        else:
            m.add_command(label=label_fb + _tip, state="disabled")

        # Replace All Backdrops — single movie only (folder + TMDB ID required) ### NEW v0.18.0 ###
        if not multi:
            _can_replace = (_tmdb_key_set and _has_tmdb_id
                            and os.path.isdir(d.get("subfolder_path", "")))
            if _can_replace:
                m.add_command(label="🔄  Replace All Backdrops",
                              command=lambda: self._replace_all_backdrops(d))
            else:
                m.add_command(label="🔄  Replace All Backdrops" + _tip, state="disabled")

        # Add Custom Genre(s) — when custom genres detected    ### NEW v0.12.0 ###
        custom_genres = self._collect_custom_genres(sel_data)
        if custom_genres:
            m.add_command(label=f"➕  Add Custom Genre(s) to Settings ({len(custom_genres)})",
                          command=lambda cg=custom_genres, dd=sel_data:
                              self._add_custom_genres(cg, dd))

        # ── SECTION 5 — Update & Refresh ─────────────────────────────────────
        m.add_separator()
        # Multi-only: Extract Backdrop(s)
        if multi:
            ff_ok = self._ffmpeg_status[0] if self._ffmpeg_status else False
            if ff_ok:
                m.add_command(label=f"🎞  Extract Backdrop(s) ({len(sel_data)} movies)",
                              command=lambda dd=sel_data: self._extract_multi(dd))

        if multi:
            m.add_command(label=f"🔄  Update (no FFprobe) ({len(sel_data)} movies)",
                          command=lambda dd=sel_data, ii=list(self.tree.selection()):
                              self._reval_multi_no_ffmpeg(ii, dd))
        else:
            m.add_command(label="🔄  Update (no FFprobe)",
                          command=lambda: self._reval_no_ffmpeg(iid, d))

        if multi:
            m.add_command(label=f"🔬  Update (with FFprobe) ({len(sel_data)} movies)",
                          command=lambda dd=sel_data, ii=list(self.tree.selection()):
                              self._reval_multi_ffmpeg(ii, dd))
        else:
            m.add_command(label="🔬  Update (with FFprobe)",
                          command=lambda: self._reval_ffmpeg(iid, d))

        m.add_command(label="🔁  Refresh Icons",
                      command=lambda: self._refresh_icons())

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
        # FIX v0.16.0 — use cached FFmpeg status; never block on main thread  ### FIX v0.16.0 ###
        ff_ok = self._ffmpeg_status[0] if self._ffmpeg_status else False
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
        self._incremental_save(self._results)                  ### NEW v0.18.0 ###
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
            "audio_tracks":   data.get("audio_tracks", []),  ### FIX v0.15.0 ###
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
        self._incremental_save(self._results)                  ### NEW v0.18.0 — persist updated row ###
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
        self._incremental_save(self._results)                  ### NEW v0.18.0 ###
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
                    self._incremental_save(self._results)      ### NEW v0.18.0 ###
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
                self._incremental_save(self._results)          ### NEW v0.18.0 ###
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
        # Show progress dialog immediately for ≥10 movies          ### NEW v0.17.0 ###
        prog = None
        if len(data_list) >= 10:
            prog = _BatchProgressDialog(self, "Processing Movies… (Ratings Sync)",
                                        total=len(data_list))
        threading.Thread(target=self._sync_ratings_worker,
                         args=(data_list, tmdb_key, omdb_key, prog), daemon=True).start()

    def _sync_ratings_worker(self, data_list, tmdb_key, omdb_key, prog=None):  ### UPDATED v0.17.0 ###
        """
        Background worker for ratings sync.
        apply_choice:     "tmdb"/"omdb"/"cancel_all" — same choice for all remaining.
        apply_votes_mode: True — auto-pick source with more votes, no dialog.
        The two modes are mutually exclusive (checkbox E).
        Checkboxes hidden when data_list has only 1 movie (C).
        """                                                          ### FIX v0.15.0 ###
        apply_choice     = None   # set when "Apply to all" is checked
        apply_votes_mode = False  # set when "Use more votes" is checked
        multi = len(data_list) > 1   # show checkboxes only for multi-movie runs

        def _auto_by_votes(tr, tv, or_, ov):
            """Pick source with more votes; fallback to whichever source exists."""
            if tr is not None and or_ is not None:
                try:
                    tv_int = int(str(tv).replace(",", "")) if tv else 0
                    ov_int = int(str(ov).replace(",", "")) if ov else 0
                    if tv_int > ov_int:
                        return tr, tv, "TMDb"
                    elif ov_int > tv_int:
                        return or_, ov, "OMDb/IMDb"
                    else:
                        avg_r = (float(tr) + float(or_)) / 2
                        return f"{avg_r:.1f}", str(max(tv_int, ov_int)), "TMDb+OMDb average"
                except Exception:
                    return tr, tv, "TMDb"
            elif tr is not None:
                return tr, tv, "TMDb"
            else:
                return or_, ov, "OMDb/IMDb"

        for _idx, d in enumerate(data_list):                   ### UPDATED v0.17.0 ###
            if prog and prog.cancelled:                        ### NEW v0.17.0 ###
                break
            name = d["subfolder"]
            nfo_path = d.get("nfo_path") if d.get("nfo_exists") else None
            xml_path = d.get("xml_path") if d.get("xml_exists") else None
            imdb_id, tmdb_id = get_movie_ids_robust(nfo_path, xml_path)

            # Fetch from both sources
            tmdb_r, tmdb_v = _fetch_tmdb_rating(tmdb_id, tmdb_key) if tmdb_key else (None, None)
            omdb_r, omdb_v = _fetch_omdb_rating(imdb_id, omdb_key) if omdb_key else (None, None)

            ### NEW v0.18.0 — treat zero rating or zero votes as "no valid data" ###
            tmdb_valid = tmdb_r is not None
            omdb_valid = omdb_r is not None
            if tmdb_valid:
                try:
                    _tv_int = int(str(tmdb_v or "0").replace(",", "")) if tmdb_v is not None else 0
                    if float(tmdb_r) == 0.0 or _tv_int == 0:
                        tmdb_valid = False
                except (ValueError, TypeError):
                    pass
            if omdb_valid:
                try:
                    _ov_int = int(str(omdb_v or "0").replace(",", "")) if omdb_v is not None else 0
                    if float(omdb_r) == 0.0 or _ov_int == 0:
                        omdb_valid = False
                except (ValueError, TypeError):
                    pass

            both = tmdb_valid and omdb_valid
            one  = tmdb_valid != omdb_valid
            none = (not tmdb_valid) and (not omdb_valid)

            chosen_r = chosen_v = None
            source_used = ""

            if apply_choice is not None:
                # ── "Apply same choice to all" mode (B/D) ────────────────────
                if apply_choice == "tmdb":
                    chosen_r, chosen_v, source_used = (
                        tmdb_r or omdb_r, tmdb_v or omdb_v, "TMDb")
                elif apply_choice == "omdb":
                    chosen_r, chosen_v, source_used = (
                        omdb_r or tmdb_r, omdb_v or tmdb_v, "OMDb/IMDb")
                else:
                    continue   # "cancel_all"

            elif apply_votes_mode and (both or one):
                # ── "Use source with more votes" mode — no dialog (A/D) ──────
                chosen_r, chosen_v, source_used = _auto_by_votes(
                    tmdb_r, tmdb_v, omdb_r, omdb_v)

            elif both or one:
                # ── Show dialog for this movie ────────────────────────────────
                def_apply = SETTINGS.get("rating_apply_all_movies", False)
                def_votes  = SETTINGS.get("rating_use_more_votes",   False)
                result = {"choice": None, "apply_all": False, "use_more_votes": False,
                          "manual_r": None, "manual_v": None}  ### NEW v0.17.0 ###
                def _ask(d=d, tr=tmdb_r, tv=tmdb_v, or_=omdb_r, ov=omdb_v, res=result,
                         dap=def_apply, duv=def_votes, show_cb=multi):
                    dlg = RatingsCompareDialog(
                        self, d["subfolder"], tr, tv, or_, ov,
                        default_apply_all=dap,
                        default_use_more_votes=duv,
                        show_checkboxes=show_cb)               ### FIX v0.15.0 ###
                    self.wait_window(dlg)
                    res["choice"]         = dlg.choice
                    res["apply_all"]      = dlg.apply_all
                    res["use_more_votes"] = dlg.use_more_votes
                    res["manual_r"]       = dlg.manual_r      ### NEW v0.17.0 ###
                    res["manual_v"]       = dlg.manual_v      ### NEW v0.17.0 ###
                self.after(0, _ask)
                while result["choice"] is None:
                    time.sleep(0.05)
                if result["choice"] == "cancel":
                    continue

                # apply_all and use_votes are mutually exclusive (E)  ### FIX v0.15.0 ###
                if result["apply_all"]:
                    apply_choice = result["choice"]       # carry forward for all remaining
                elif result["use_more_votes"] and multi:
                    apply_votes_mode = True               # carry forward for all remaining

                # Resolve chosen source for the current movie
                if result["choice"] == "manual":           ### NEW v0.17.0 ###
                    chosen_r = str(result["manual_r"])
                    chosen_v = str(result["manual_v"])
                    source_used = "manual"
                elif result["use_more_votes"] and both:
                    chosen_r, chosen_v, source_used = _auto_by_votes(
                        tmdb_r, tmdb_v, omdb_r, omdb_v)
                else:
                    if result["choice"] == "tmdb":
                        chosen_r, chosen_v, source_used = tmdb_r, tmdb_v, "TMDb"
                    else:
                        chosen_r, chosen_v, source_used = omdb_r, omdb_v, "OMDb/IMDb"

            elif none:
                # ── Neither source returned data — show dialog (Type Values always available) ###
                ### NEW v0.17.0 — open RatingsCompareDialog even with no IDs, TMDb/OMDb disabled ###
                result = {"choice": None, "manual_r": None, "manual_v": None}
                def _ask_none(n=name, res=result, show_cb=multi):
                    dlg = RatingsCompareDialog(
                        self, n, None, None, None, None,
                        default_apply_all=False,
                        default_use_more_votes=False,
                        show_checkboxes=show_cb)
                    self.wait_window(dlg)
                    res["choice"]   = dlg.choice
                    res["manual_r"] = dlg.manual_r
                    res["manual_v"] = dlg.manual_v
                self.after(0, _ask_none)
                while result["choice"] is None:
                    time.sleep(0.05)
                if result["choice"] != "manual" or result["manual_r"] is None:
                    continue
                chosen_r = str(result["manual_r"])
                chosen_v = str(result["manual_v"])
                source_used = "manual"

            if chosen_r and chosen_v:
                errors = write_rating_to_files(nfo_path, xml_path, chosen_r, chosen_v)
                if errors:
                    self.after(0, lambda n=name, errs=errors:
                        messagebox.showerror("Write Error",
                            f"{n}\nFailed to write ratings:\n" + "\n".join(errs)))
                else:
                    self.after(0, lambda iid_data=d: self._reval_by_path(d))

            if prog:                                            ### NEW v0.17.0 ###
                prog.update(_idx + 1)

        if prog:
            prog.close()                                       ### NEW v0.17.0 ###
        self._incremental_save(self._results)                  ### NEW v0.18.0 ###
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

    def _run_improvements_all(self):                            ### NEW v0.15.0 ###
        """Run improvements check for ALL movies with progress window."""
        if not self._results:
            messagebox.showinfo("No data", "Run a scan first."); return
        if not messagebox.askyesno("Run Improvements Check — All Movies",
                f"Run improvements check for ALL {len(self._results)} movies?\n"
                "Results will be saved to a file you choose.\n\nContinue?",
                icon="question"):
            return
        from tkinter import filedialog
        out_path = filedialog.asksaveasfilename(
            title="Save Improvements Report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not out_path:
            return
        self._run_improvements_batch(list(self._results), out_path)

    def _run_improvements_batch(self, data_list, out_path):     ### NEW v0.15.0 ###
        """Run improvements check for a list of movies, writing results to file."""
        prog_win = tk.Toplevel(self)
        prog_win.title("Improvements Check — All Movies")
        prog_win.configure(bg="#1e1e2e")
        prog_win.resizable(False, False)
        prog_win.transient(self)
        prog_win.geometry("420x160")
        cancel_flag = [False]

        tk.Label(prog_win, text="Running Improvements Check…",
                 bg="#1e1e2e", fg="#cdd6f4", font=("Helvetica", 11)).pack(pady=(20, 6))
        prog_var = tk.IntVar(value=0)
        progress = ttk.Progressbar(prog_win, variable=prog_var, maximum=len(data_list),
                                   length=360)
        progress.pack(pady=4)
        status_lbl = tk.Label(prog_win, text="Starting…", bg="#1e1e2e", fg="#a6adc8",
                              font=("Helvetica", 9))
        status_lbl.pack(pady=4)
        tk.Button(prog_win, text="  Cancel  ", bg="#f38ba8", fg="#1e1e2e",
                  relief="flat", cursor="hand2",
                  command=lambda: cancel_flag.__setitem__(0, True)).pack(pady=6)
        prog_win.bind("<Escape>", lambda e: cancel_flag.__setitem__(0, True))

        def _worker():
            try:
                with open(out_path, "w", encoding="utf-8") as fout:
                    fout.write(f"MediaClinic Improvements Report — {len(data_list)} movie(s)\n")
                    fout.write("=" * 60 + "\n\n")
                    for i, d in enumerate(data_list):
                        if cancel_flag[0]:
                            fout.write("\n[Cancelled by user]\n")
                            break
                        name = d.get("movie_name", d["subfolder"])
                        self.after(0, lambda n=name, idx=i: (
                            status_lbl.configure(text=f"{n[:45]}…" if len(n)>45 else n),
                            prog_var.set(idx + 1)))
                        issues = _run_improvements_check(d)
                        if issues:
                            fout.write(f"Movie: {name}\n")
                            for issue in issues:
                                fout.write(f"  {issue}\n")
                            fout.write("\n")
                self.after(0, lambda: (
                    prog_win.destroy(),
                    messagebox.showinfo("Improvements Check Complete",
                        f"Report saved to:\n{out_path}")))
            except Exception as ex:
                self.after(0, lambda: (
                    prog_win.destroy(),
                    messagebox.showerror("Error", f"Improvements check failed:\n{ex}")))

        threading.Thread(target=_worker, daemon=True).start()

    def _delete_extrafanart_all(self):                         ### REVISED v0.17.0 ###
        """Delete all extrafanart subfolders — with preview, backup, and progress popup."""
        if not self._results:
            messagebox.showinfo("No data", "Run a scan first."); return

        # ── Step 1: scan for extrafanart folders ─────────────────────────────
        ef_targets = []   # list of (movie_name, ef_path)
        for d in self._results:
            sp = d.get("subfolder_path", "")
            ef = os.path.join(sp, "extrafanart")
            if os.path.isdir(ef):
                ef_targets.append((d.get("movie_name", d["subfolder"]), ef))

        if not ef_targets:
            messagebox.showinfo("No extrafanart", "No extrafanart subfolders found."); return

        # ── Step 2: show preview popup ────────────────────────────────────────
        preview = tk.Toplevel(self)
        preview.title("Extrafanart Subfolders to Delete")
        preview.configure(bg="#1e1e2e")
        preview.resizable(True, True)
        preview.transient(self)
        preview.geometry("560x480")
        preview.grab_set()

        tk.Label(preview,
                 text=f"Extrafanart Subfolders to Delete  ({len(ef_targets)} found)",
                 bg="#1e1e2e", fg="#cdd6f4",
                 font=("Helvetica", 11, "bold")).pack(padx=16, pady=(14, 4))
        tk.Label(preview,
                 text="All deleted content will be copied to the application's backup folder\n"
                      "before deletion. This operation cannot be undone from within the app.",
                 bg="#1e1e2e", fg="#fab387",
                 font=("Helvetica", 9), justify="center").pack(padx=16, pady=(0, 8))

        # Scrollable list
        lf = tk.Frame(preview, bg="#1e1e2e"); lf.pack(fill="both", expand=True, padx=14, pady=4)
        lf.rowconfigure(0, weight=1); lf.columnconfigure(0, weight=1)
        canvas = tk.Canvas(lf, bg="#1e1e2e", highlightthickness=0)
        vsb = ttk.Scrollbar(lf, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        canvas.grid(row=0, column=0, sticky="nsew")
        inner = tk.Frame(canvas, bg="#1e1e2e")
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        for name, ef in ef_targets:
            row_f = tk.Frame(inner, bg="#252535"); row_f.pack(fill="x", padx=2, pady=1)
            tk.Label(row_f, text=f"  {name}",
                     bg="#252535", fg="#cdd6f4",
                     font=("Helvetica", 9, "bold"), anchor="w").pack(fill="x", padx=4, pady=(3, 0))
            tk.Label(row_f, text=f"    {os.path.basename(ef)}\\",
                     bg="#252535", fg="#6c7086",
                     font=("Consolas", 8), anchor="w").pack(fill="x", padx=4, pady=(0, 3))

        # Buttons
        confirmed = [False]
        def _confirm():
            confirmed[0] = True; preview.destroy()
        def _cancel_preview():
            preview.destroy()

        sep = tk.Frame(preview, bg="#45475a", height=1); sep.pack(fill="x", padx=14, pady=(6, 0))
        bf = tk.Frame(preview, bg="#1e1e2e"); bf.pack(pady=(8, 14))
        tk.Button(bf, text="  Confirm Deletion  ",
                  bg="#f38ba8", fg="#1e1e2e",
                  relief="flat", cursor="hand2",
                  font=("Helvetica", 10, "bold"),
                  command=_confirm).pack(side="left", padx=6)
        tk.Button(bf, text="  Cancel  ",
                  bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  font=("Helvetica", 10),
                  command=_cancel_preview).pack(side="left", padx=6)
        preview.bind("<Escape>", lambda e: _cancel_preview())

        preview.update_idletasks()
        pw, ph = self.winfo_width(), self.winfo_height()
        px, py = self.winfo_x(), self.winfo_y()
        w, h = preview.winfo_reqwidth(), preview.winfo_reqheight()
        preview.geometry(f"+{px+(pw-w)//2}+{py+(ph-h)//2}")
        self.wait_window(preview)

        if not confirmed[0]:
            return

        # ── Step 3: delete with backup and progress ───────────────────────────
        prog = _BatchProgressDialog(self, "Deleting extrafanart Subfolders…",
                                    total=len(ef_targets))

        def _worker():
            deleted = 0; errors = []
            for idx, (name, ef_path) in enumerate(ef_targets):
                if prog.cancelled:
                    break
                if not os.path.isdir(ef_path):
                    prog.update(idx + 1)
                    continue
                try:
                    # Backup entire extrafanart folder contents before deletion
                    bk_files = [os.path.join(ef_path, f)
                                 for f in os.listdir(ef_path)
                                 if os.path.isfile(os.path.join(ef_path, f))]
                    if bk_files:
                        _make_backup(name, *bk_files)
                    shutil.rmtree(ef_path)
                    deleted += 1
                    logger.info(f"Deleted extrafanart: {ef_path}")
                except Exception as ex:
                    errors.append(f"{name}: {ex}")
                    logger.error(f"extrafanart delete error ({name}): {ex}")
                prog.update(idx + 1)

            prog.close()
            self.after(0, lambda: messagebox.showinfo(
                "Delete Complete",
                f"Deleted {deleted} extrafanart folder(s)."
                + (f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:5])
                   if errors else "")))

        threading.Thread(target=_worker, daemon=True).start()


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
    def _sync_ratings_all(self):                                ### NEW v0.15.0 ###
        """Sync ratings for ALL movies — asks confirmation first."""
        if not self._results:
            messagebox.showinfo("No data", "Run a scan first."); return
        if not messagebox.askyesno("Sync Ratings Online — All Movies",
                f"This will sync ratings for ALL {len(self._results)} movies.\n"
                "Requires TMDb and/or OMDb API keys.\n\nContinue?",
                icon="warning"):
            return
        self._sync_ratings(list(self._results))


    def _normalize_genres_for(self, data_list, confirm_all=False):  ### NEW v0.15.0 — per-movie isolation + custom genre dialog ###
        """Normalize genres for given data_list. confirm_all=True means user already confirmed."""
        if not data_list:
            return
        prog = None                                            ### NEW v0.17.0 ###
        if len(data_list) >= 10:
            prog = _BatchProgressDialog(self, "Processing Movies… (Normalize Genres)",
                                        total=len(data_list))
        threading.Thread(
            target=self._normalize_genres_worker,
            args=(list(data_list), prog),                      ### NEW v0.17.0 ###
            daemon=True).start()

    def _normalize_genres_worker(self, data_list, prog=None):   ### UPDATED v0.17.0 ###
        """Worker thread: normalizes genres per movie, shows custom-genre dialog per movie."""
        changed = 0
        errors  = []
        backup_ref = [None]

        for _idx, d in enumerate(data_list):                  ### UPDATED v0.17.0 ###
            if prog and prog.cancelled:                       ### NEW v0.17.0 ###
                break
            # Each movie gets its OWN fresh genre read — no shared state ### NEW v0.15.0 ###
            nfo_path = d.get("nfo_path") if d.get("nfo_exists") else None
            xml_path = d.get("xml_path") if d.get("xml_exists") else None

            movie_genres = get_genres_from_nfo(nfo_path)   # fresh per-movie read  ### NEW v0.15.0 ###
            if not movie_genres:
                continue

            valid_genres = _get_valid_genres()
            def _is_splittable(g, valid):                          ### FIX v0.15.0 ###
                """Return True if g is made up entirely of valid genres joined by /|\\,;"""  ### FIX v0.15.0 ###
                parts = [p.strip() for p in re.split(r'[/|,;]', g) if p.strip()]
                if len(parts) < 2: return False
                vl = {v.lower() for v in valid}
                return all(
                    p in valid or p.title() in valid
                    or normalize_genre(p) in valid
                    or normalize_genre(p).lower() in vl
                    for p in parts)
            custom = [g for g in movie_genres
                      if g not in valid_genres
                      and g.title() not in valid_genres
                      and normalize_genre(g) not in valid_genres
                      and normalize_genre(g).lower() not in {v.lower() for v in valid_genres}
                      and not _is_splittable(g, valid_genres)]  ### FIX v0.15.0 — splittable genres are not custom ###

            delete_custom = False
            if custom:
                result = {"delete": None}
                movie_name = d.get("movie_name", d.get("subfolder", "?"))
                def _ask(mn=movie_name, cg=list(custom), res=result):
                    dlg = CustomGenreDialog(self, mn, cg)
                    self.wait_window(dlg)
                    res["delete"] = dlg.delete_custom if dlg.delete_custom is not None else False
                self.after(0, _ask)
                while result["delete"] is None:
                    time.sleep(0.05)
                delete_custom = result["delete"]

            if delete_custom:
                # Keep only standard genres from this movie's list
                filtered = [g for g in movie_genres if g not in custom]
            else:
                filtered = list(movie_genres)

            normalized, did_change = normalize_genre_list(filtered)
            # Always write if custom genres were deleted, even if normalized list unchanged
            if not did_change and not (delete_custom and custom):
                continue

            movie_name_b = d.get("movie_name", d.get("subfolder", "unknown"))
            _make_batch_backup(movie_name_b, backup_ref, nfo_path, xml_path)
            ok_nfo, err_nfo = write_genres_to_nfo(nfo_path, normalized)
            ok_xml, err_xml = write_genres_to_xml(xml_path, normalized)
            if ok_nfo or ok_xml:
                changed += 1
                d["genres"]        = normalized
                d["genre_display"] = "/".join(normalized)
                d["genre_status"]  = classify_genres(normalized)[1]
            if err_nfo: errors.append(f"{d['subfolder']}: {err_nfo}")
            if err_xml: errors.append(f"{d['subfolder']}: {err_xml}")
            if prog:                                           ### NEW v0.17.0 ###
                prog.update(_idx + 1)

        if prog:
            prog.close()                                      ### NEW v0.17.0 ###
        def _done():
            self._refresh_table()
            self._incremental_save(self._results)              ### NEW v0.18.0 ###
            msg = f"Normalized genres in {changed} movie(s)."
            if errors:
                msg += "\n\nErrors:\n" + "\n".join(errors[:5])
            messagebox.showinfo("Normalize Genres", msg)
        self.after(0, _done)

    # ══════════════════════════════════════════════════════════════════════════
    # NEW v0.16.0 — Save / Open Scan Results
    # ══════════════════════════════════════════════════════════════════════════

    def _save_scan_results(self):                              ### NEW v0.16.0 ###
        """Save current scan results to a JSON file chosen by the user."""
        if not self._results:
            messagebox.showinfo("Save Scan Results", "Run a scan first."); return
        p = filedialog.asksaveasfilename(
            title="Save Scan Results",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="scan_results.json")
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self._results, f, ensure_ascii=False, indent=2, default=str)
            messagebox.showinfo("Save Scan Results",
                                f"Saved {len(self._results)} movies to:\n{p}")
            logger.info(f"Scan results saved: {p}")
        except Exception as e:
            messagebox.showerror("Save Failed", str(e))

    def _open_scan_results(self):                              ### NEW v0.16.0 ###
        """Load scan results from a JSON file, replacing current results."""
        p = filedialog.askopenfilename(
            title="Open Scan Results",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not p:
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("File does not contain a list of scan results.")
            loaded = _results_from_json(data)
        except Exception as e:
            messagebox.showerror("Open Failed",
                                 f"Could not parse scan results file:\n{e}\n\n"
                                 "Current scan results are unchanged.")
            return
        self._results = loaded
        self._item_map.clear()
        for r in self.tree.get_children():
            self.tree.delete(r)
        self._apply_default_sort()                             ### NEW v0.16.1 ###
        self._update_stats()
        messagebox.showinfo("Open Scan Results",
                            f"Loaded {len(loaded)} movies from:\n{p}")
        logger.info(f"Scan results loaded: {p}")

    # ══════════════════════════════════════════════════════════════════════════
    # NEW v0.16.0 — Normalize Sources
    # ══════════════════════════════════════════════════════════════════════════

    def _normalize_sources_for(self, data_list):               ### NEW v0.16.0 ###
        """Launch Normalize Sources for given data_list in a background thread."""
        if not data_list:
            return
        prog = None                                            ### NEW v0.17.0 ###
        if len(data_list) >= 10:
            prog = _BatchProgressDialog(self, "Processing Movies… (Normalize Sources)",
                                        total=len(data_list))
        threading.Thread(
            target=self._normalize_sources_worker,
            args=(list(data_list), prog),                     ### NEW v0.17.0 ###
            daemon=True).start()

    def _normalize_sources_all(self):                          ### NEW v0.16.0 ###
        """Normalize Sources for all movies with ◐ or ○ in Source column."""
        if not self._results:
            messagebox.showinfo("No data", "Run a scan first."); return
        targets = [r for r in self._results
                   if r.get("source_imdb_status") in (STATUS_WARN, STATUS_MISSING)
                   or r.get("source_tmdb_status") in (STATUS_WARN, STATUS_MISSING)]
        if not targets:
            messagebox.showinfo("Normalize Sources — All Movies",
                                "No movies with missing or conflicting source IDs found."); return
        if not messagebox.askyesno("Normalize Sources — All Movies",
                f"This will process {len(targets)} movie(s) with missing or conflicting\n"
                "IMDB/TMDB IDs.\n\nContinue?", icon="warning"):
            return
        self._normalize_sources_for(targets)

    def _normalize_sources_worker(self, data_list, prog=None):  ### UPDATED v0.17.0 ###
        """
        Worker thread: normalize IMDB/TMDB source tags for each movie.
        Case A: tags present but some missing, all agree → auto-fill silently.
        Case B: tags disagree → popup to pick correct ID.
        Case C: all tags missing → popup to type an ID.
        Skips movie on cancel or window-close.
        """
        import time as _time
        changed = 0; errors = []
        backup_ref = [None]

        for _idx, d in enumerate(data_list):                  ### UPDATED v0.17.0 ###
            if prog and prog.cancelled:                       ### NEW v0.17.0 ###
                break
            nfo_path   = d.get("nfo_path") if d.get("nfo_exists") else None
            xml_path   = d.get("xml_path") if d.get("xml_exists") else None
            movie_name = d.get("movie_name", d.get("subfolder", "?"))

            src      = extract_source_ids_from_files(nfo_path, xml_path)
            imdb_all = src["imdb_all_vals"]
            tmdb_all = src["tmdb_all_vals"]

            for id_type, all_vals, status in [
                ("IMDB", imdb_all, src["imdb_status"]),
                ("TMDB", tmdb_all, src["tmdb_status"]),
            ]:
                chosen_id = None

                if status == STATUS_OK:
                    continue

                elif status == STATUS_MISSING:
                    # Case C — ask user to type ID
                    result = {"id": None, "done": False}
                    def _ask_c(mn=movie_name, it=id_type, res=result):
                        dlg = _SourceManualEntryDialog(self, mn, it)
                        # FIX: closing window via [X] must set done flag   ### FIX v0.16.0 ###
                        dlg.protocol("WM_DELETE_WINDOW",
                                     lambda: (setattr(dlg, 'cancelled', True),
                                              dlg.destroy()))
                        self.wait_window(dlg)
                        res["id"]   = dlg.result_id
                        res["done"] = True
                    self.after(0, _ask_c)
                    # Wait for dialog to finish — bounded by 10 min safety timeout
                    deadline = _time.time() + 600
                    while not result["done"] and _time.time() < deadline:
                        _time.sleep(0.05)
                    if not result["id"]:
                        continue
                    chosen_id = result["id"].strip()

                elif status == STATUS_WARN and len(set(all_vals)) > 1:
                    # Case B — show disagreement popup
                    result = {"id": None, "done": False}
                    def _ask_b(mn=movie_name, it=id_type,
                               vals=list(all_vals), res=result):
                        dlg = _SourceDisagreementDialog(self, mn, it, vals)
                        dlg.protocol("WM_DELETE_WINDOW",
                                     lambda: (setattr(dlg, 'cancelled', True),
                                              dlg.destroy()))
                        self.wait_window(dlg)
                        res["id"]   = dlg.result_id
                        res["done"] = True
                    self.after(0, _ask_b)
                    deadline = _time.time() + 600
                    while not result["done"] and _time.time() < deadline:
                        _time.sleep(0.05)
                    if not result["id"]:
                        continue
                    chosen_id = result["id"].strip()

                elif status == STATUS_WARN and len(set(all_vals)) == 1:
                    # Case A — auto-fill silently
                    chosen_id = all_vals[0]

                if not chosen_id:
                    continue

                _make_batch_backup(movie_name, backup_ref, nfo_path, xml_path)
                ok, err = _write_source_id_to_files(
                    nfo_path, xml_path, id_type, chosen_id)
                if ok:
                    changed += 1
                elif err:
                    errors.append(f"{movie_name} ({id_type}): {err}")

            self.after(0, lambda dd=d: self._reval_by_path(dd))
            if prog:                                           ### NEW v0.17.0 ###
                prog.update(_idx + 1)

        if prog:
            prog.close()                                      ### NEW v0.17.0 ###
        def _done():
            self._incremental_save(self._results)              ### NEW v0.18.0 ###
            msg = f"Normalize Sources: updated {changed} ID(s)."
            if errors:
                msg += "\n\nErrors:\n" + "\n".join(errors[:5])
            messagebox.showinfo("Normalize Sources", msg)
        self.after(0, _done)

    # ══════════════════════════════════════════════════════════════════════════
    # NEW v0.16.0 — Search Sources
    # ══════════════════════════════════════════════════════════════════════════

    def _search_sources_for(self, data_list):                  ### NEW v0.16.0 ###
        """Search TMDB for each movie in data_list and show results popup."""
        tmdb_key = SETTINGS.get("tmdb_api_key", "").strip()
        if not tmdb_key:
            messagebox.showwarning("Search Sources",
                "No TMDb API key configured.\nGo to Settings → API Keys."); return
        threading.Thread(
            target=self._search_sources_worker,
            args=(list(data_list), tmdb_key, False),
            daemon=True).start()

    def _search_sources_all(self):                             ### NEW v0.16.0 ###
        """Search Sources for ALL movies regardless of Source column icon."""
        if not self._results:
            messagebox.showinfo("No data", "Run a scan first."); return
        tmdb_key = SETTINGS.get("tmdb_api_key", "").strip()
        if not tmdb_key:
            messagebox.showwarning("Search Sources — All Movies",
                "No TMDb API key configured.\nGo to Settings → API Keys."); return
        if not messagebox.askyesno("Search Sources — All Movies",
                f"Search TMDB for ALL {len(self._results)} movies?\n"
                "This may take a while.\n\nContinue?", icon="question"):
            return
        threading.Thread(
            target=self._search_sources_worker,
            args=(list(self._results), tmdb_key, True),
            daemon=True).start()

    def _search_sources_worker(self, data_list, tmdb_key, show_all_results): ### NEW v0.16.0 ###
        """
        Background: query TMDB search for each movie using title + year.
        Collect results, then show SearchSourcesResultDialog.
        """
        import urllib.parse
        results = []   # list of dicts: {movie_name, year, tmdb_matches}

        for d in data_list:
            movie_name = d.get("movie_name", d.get("subfolder", "?"))
            year = d.get("movie_year", "")
            matches = []
            try:
                query = urllib.parse.quote(movie_name)
                yr_param = f"&year={year}" if year and year != "-" else ""
                url = (f"https://api.themoviedb.org/3/search/movie"
                       f"?api_key={tmdb_key}&query={query}{yr_param}&language=en-US")
                data = _tmdb_fetch_json(url, timeout=10)      ### FIX v0.17.0-bug2 ###
                for item in data.get("results", [])[:5]:
                    tid = str(item.get("id", ""))
                    # Fetch external IDs (includes imdb_id)
                    imdb_id = ""
                    try:
                        eurl = (f"https://api.themoviedb.org/3/movie/{tid}"
                                f"/external_ids?api_key={tmdb_key}")
                        edata = _tmdb_fetch_json(eurl, timeout=8)  ### FIX v0.17.0-bug2 ###
                        imdb_id = edata.get("imdb_id", "") or ""
                    except Exception:
                        pass
                    matches.append({
                        "tmdb_id": tid,
                        "imdb_id": imdb_id,
                        "title":   item.get("title", ""),
                        "year":    (item.get("release_date", "")[:4]
                                    if item.get("release_date") else ""),
                        "popularity": item.get("popularity", 0),
                    })
            except Exception as e:
                logger.warning(f"Search Sources: TMDB search failed for '{movie_name}': {e}")

            results.append({
                "movie_name": movie_name,
                "year":       year,
                "matches":    matches,
            })

        def _show():
            _SearchSourcesResultDialog(self, results, data_list)
        self.after(0, _show)

    # ══════════════════════════════════════════════════════════════════════════
    # NEW v0.16.0 — Fetch Poster/Folder and Fetch Fanart
    # ══════════════════════════════════════════════════════════════════════════

    def _fetch_poster_folder(self, data_list):                 ### NEW v0.16.0 ###
        """Launch Fetch Poster/Folder dialog for each movie in data_list."""
        tmdb_key = SETTINGS.get("tmdb_api_key", "").strip()
        if not tmdb_key:
            messagebox.showwarning("Fetch Poster/Folder",
                "No TMDb API key configured.\nGo to Settings → API Keys."); return
        for d in data_list:
            tmdb_id = d.get("source_tmdb_val")
            if not tmdb_id:
                messagebox.showwarning("Fetch Poster/Folder",
                    f"{d.get('movie_name', d['subfolder'])}\n"
                    "No TMDB ID found — cannot fetch images.\n"
                    "Run 'Normalize Sources' or 'Search Sources' first.")
                continue
            dlg = _FetchImageDialog(self, d, "poster", tmdb_key, tmdb_id)
            self.wait_window(dlg)
            if dlg.applied:
                self._reval_by_path(d)

    def _fetch_fanart(self, data_list):                        ### NEW v0.16.0 ###
        """Launch Fetch Fanart dialog for each movie in data_list."""
        tmdb_key = SETTINGS.get("tmdb_api_key", "").strip()
        if not tmdb_key:
            messagebox.showwarning("Fetch Fanart",
                "No TMDb API key configured.\nGo to Settings → API Keys."); return
        for d in data_list:
            tmdb_id = d.get("source_tmdb_val")
            if not tmdb_id:
                messagebox.showwarning("Fetch Fanart",
                    f"{d.get('movie_name', d['subfolder'])}\n"
                    "No TMDB ID found — cannot fetch images.\n"
                    "Run 'Normalize Sources' or 'Search Sources' first.")
                continue
            dlg = _FetchImageDialog(self, d, "fanart", tmdb_key, tmdb_id)
            self.wait_window(dlg)
            if dlg.applied:
                self._reval_by_path(d)

    def _fetch_backdrops(self, data_list):                     ### NEW v0.17.0 ###
        """Launch Fetch Backdrops dialog for each movie in data_list."""
        tmdb_key = SETTINGS.get("tmdb_api_key", "").strip()
        if not tmdb_key:
            messagebox.showwarning("Fetch Backdrops",
                "No TMDb API key configured.\nGo to Settings → API Keys."); return
        for d in data_list:
            tmdb_id = d.get("source_tmdb_val")
            if not tmdb_id:
                messagebox.showwarning("Fetch Backdrops",
                    f"{d.get('movie_name', d['subfolder'])}\n"
                    "No TMDB ID found — cannot fetch backdrops.\n"
                    "Run 'Normalize Sources' or 'Search Sources' first.")
                continue
            dlg = _FetchBackdropDialog(self, d, tmdb_key, tmdb_id)
            self.wait_window(dlg)
            if dlg.applied:
                self._reval_by_path(d)

    def _replace_all_backdrops(self, d):                       ### NEW v0.18.0 ###
        """
        Replace All Backdrops for a single movie:
          1. Backup all existing backdrop*.jpg files
          2. Delete originals
          3. Download ALL TMDB backdrops sequentially
          4. Show progress popup if >15s elapsed
          5. Show final summary dialog
        All work runs in a background thread.
        """
        tmdb_key = SETTINGS.get("tmdb_api_key", "").strip()
        tmdb_id  = d.get("source_tmdb_val")
        sp       = d.get("subfolder_path", "")
        movie    = d.get("movie_name", d.get("subfolder", "?"))

        if not tmdb_key:
            messagebox.showwarning("Replace All Backdrops",
                "No TMDb API key configured.\nGo to Settings → API Keys.")
            return
        if not tmdb_id:
            messagebox.showwarning("Replace All Backdrops",
                f"{movie}\nNo TMDB ID found.\nRun 'Normalize Sources' first.")
            return
        if not os.path.isdir(sp):
            messagebox.showerror("Replace All Backdrops", f"Folder not found:\n{sp}")
            return

        # Progress popup (created on main thread, shown only after 15s)
        _prog_win    = [None]
        _prog_var    = [None]
        _prog_label  = [None]
        _start_time  = [None]
        _cancelled   = [False]

        def _show_progress(pct, eta_str):
            if _prog_win[0] is None:
                w = tk.Toplevel(self)
                w.title("Replace All Backdrops")
                w.configure(bg="#1e1e2e")
                w.resizable(False, False)
                w.transient(self)
                tk.Label(w, text=f"Processing backdrops… please wait",
                         bg="#1e1e2e", fg="#cdd6f4",
                         font=("Helvetica", 10, "bold")).pack(pady=(18, 6), padx=20)
                pv = tk.StringVar(value="0%")
                tk.Label(w, textvariable=pv,
                         bg="#1e1e2e", fg="#a6e3a1",
                         font=("Helvetica", 12, "bold")).pack()
                lv = tk.StringVar(value="")
                tk.Label(w, textvariable=lv,
                         bg="#1e1e2e", fg="#6c7086",
                         font=("Helvetica", 8)).pack(pady=(2, 16), padx=20)
                tk.Button(w, text="Cancel",
                          bg="#f38ba8", fg="#1e1e2e",
                          relief="flat", cursor="hand2",
                          font=("Helvetica", 9, "bold"),
                          command=lambda: _cancelled.__setitem__(0, True)
                          ).pack(pady=(0, 14))
                w.update_idletasks()
                wx = self.winfo_rootx() + (self.winfo_width()  - w.winfo_width())  // 2
                wy = self.winfo_rooty() + (self.winfo_height() - w.winfo_height()) // 2
                w.geometry(f"+{wx}+{wy}")
                _prog_win[0]   = w
                _prog_var[0]   = pv
                _prog_label[0] = lv
            _prog_var[0].set(f"{int(pct)}%")
            _prog_label[0].set(eta_str)
            try:
                _prog_win[0].update_idletasks()
            except tk.TclError:
                pass

        def _close_progress():
            if _prog_win[0]:
                try:
                    _prog_win[0].destroy()
                except tk.TclError:
                    pass
                _prog_win[0] = None

        def _worker():
            _start_time[0] = time.time()
            backup_count   = 0
            download_count = 0
            delete_count   = 0
            backup_bytes   = 0
            download_bytes = 0
            fail_reason    = None

            # ── STEP 1: Collect existing backdrops ───────────────────────────
            existing_paths = []
            try:
                for entry in os.scandir(sp):
                    if not entry.is_file():
                        continue
                    n = entry.name.lower()
                    if n == "backdrop.jpg" or re.match(r'^backdrop\d+\.jpg$', n):
                        existing_paths.append(entry.path)
            except OSError as e:
                fail_reason = f"Cannot read movie folder: {e}"

            if fail_reason:
                self.after(0, lambda m=fail_reason: (
                    _close_progress(),
                    messagebox.showerror("Replace All Backdrops — Failed",
                                         f"Reason: {m}")))
                return

            total_existing = len(existing_paths)

            # ── STEP 2: Fetch TMDB image list ────────────────────────────────
            try:
                url = (f"https://api.themoviedb.org/3/movie/{tmdb_id}"
                       f"/images?api_key={tmdb_key}")
                data = _tmdb_fetch_json(url, timeout=15)
                tmdb_imgs = data.get("backdrops", [])
                tmdb_imgs.sort(key=lambda x: x.get("width", 0) * x.get("height", 0),
                               reverse=True)
            except Exception as e:
                fail_reason = _tmdb_error_message(e)
                self.after(0, lambda m=fail_reason: (
                    _close_progress(),
                    messagebox.showerror("Replace All Backdrops — Failed",
                                         f"Reason: {m}")))
                return

            if not tmdb_imgs:
                self.after(0, lambda: (
                    _close_progress(),
                    messagebox.showwarning("Replace All Backdrops",
                        f"{movie}\nTMDB returned 0 backdrops. Nothing to download.")))
                return

            total_steps = total_existing + total_existing + len(tmdb_imgs)
            completed   = [0]

            def _update_progress():
                if _cancelled[0]:
                    return
                elapsed = time.time() - _start_time[0]
                pct = (completed[0] / max(total_steps, 1)) * 100
                if completed[0] > 0 and elapsed > 0:
                    rate = elapsed / completed[0]
                    remaining = rate * (total_steps - completed[0])
                    if remaining > 60:
                        eta = f"ETA: {int(remaining // 60)}m {int(remaining % 60)}s"
                    elif remaining > 0:
                        eta = f"ETA: {int(remaining)}s"
                    else:
                        eta = "Almost done…"
                else:
                    eta = ""
                if elapsed > 15:
                    self.after(0, lambda p=pct, e=eta: _show_progress(p, e))

            # ── STEP 3: Backup all existing backdrops ────────────────────────
            if existing_paths:
                backup_folder_ref = []
                for p in existing_paths:
                    if _cancelled[0]:
                        break
                    try:
                        _make_batch_backup(movie, backup_folder_ref, p)
                        backup_count  += 1
                        backup_bytes  += os.path.getsize(p)
                        completed[0]  += 1
                        _update_progress()
                    except Exception as e:
                        fail_reason = f"Backup failed for {os.path.basename(p)}: {e}"
                        break

                if fail_reason:
                    self.after(0, lambda m=fail_reason: (
                        _close_progress(),
                        messagebox.showerror("Replace All Backdrops — Failed",
                                             f"Reason: {m}")))
                    return

            if _cancelled[0]:
                self.after(0, lambda: (_close_progress(),
                    messagebox.showinfo("Replace All Backdrops", "Cancelled by user.")))
                return

            # ── STEP 4: Delete originals ─────────────────────────────────────
            for p in existing_paths:
                try:
                    if os.path.isfile(p):
                        os.remove(p)
                        delete_count += 1
                    completed[0] += 1
                    _update_progress()
                except OSError as e:
                    logger.warning(f"_replace_all_backdrops: could not delete {p}: {e}")

            # ── STEP 5: Download all TMDB backdrops ──────────────────────────
            for i, img in enumerate(tmdb_imgs):
                if _cancelled[0]:
                    break
                fp  = img.get("file_path", "")
                if not fp:
                    completed[0] += 1
                    _update_progress()
                    continue
                url      = "https://image.tmdb.org/t/p/original" + fp
                fname    = "backdrop.jpg" if i == 0 else f"backdrop{i}.jpg"
                dest     = os.path.join(sp, fname)
                ok, err  = _tmdb_download_image(url, dest)
                if ok:
                    download_count += 1
                    try:
                        download_bytes += os.path.getsize(dest)
                    except OSError:
                        pass
                else:
                    logger.warning(f"_replace_all_backdrops: failed to download {fname}: {err}")
                completed[0] += 1
                _update_progress()

            # ── STEP 6: Finish ───────────────────────────────────────────────
            avg_backup   = (backup_bytes   // backup_count)   if backup_count   > 0 else 0
            avg_download = (download_bytes // download_count) if download_count > 0 else 0

            def _finish():
                _close_progress()
                if _cancelled[0]:
                    messagebox.showinfo("Replace All Backdrops", "Cancelled by user.")
                    return
                msg = (f"Replace All Backdrops — Completed Successfully\n\n"
                       f"Backups created:               {backup_count} file(s)"
                       + (f" (avg {avg_backup // 1024} KB)" if avg_backup else "") + "\n"
                       f"Backdrops deleted:             {delete_count} file(s)\n"
                       f"Backdrops downloaded (TMDB):   {download_count} file(s)"
                       + (f" (avg {avg_download // 1024} KB)" if avg_download else ""))
                messagebox.showinfo("Replace All Backdrops", msg)
                self._reval_by_path(d)

            self.after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _open_fanart_tv(self, d):                              ### NEW v0.18.0 ###
        """Open the selected movie's Fanart.tv page using its TMDB ID."""
        tmdb_id = d.get("source_tmdb_val")
        if not tmdb_id:
            messagebox.showinfo("Fanart.tv — Movie ID not available",
                "No TMDB ID found for this movie.\n"
                "Run 'Normalize Sources' or 'Search Sources' first.",
                parent=self)
            return
        try:
            int(tmdb_id)  # validate it's numeric
        except (ValueError, TypeError):
            messagebox.showwarning("Invalid TMDB ID",
                f"The TMDB ID '{tmdb_id}' appears invalid.\n"
                "Please verify the metadata for this movie.",
                parent=self)
            return
        url = f"https://fanart.tv/movie/{tmdb_id}/"
        try:
            open_url_with_browser(url)
        except Exception as e:
            messagebox.showerror("Unable to open Fanart.tv",
                f"Could not open the browser:\n{e}", parent=self)

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
        # FIX v0.16.0 — use cached FFmpeg status; never block on main thread  ### FIX v0.16.0 ###
        ff_ok = self._ffmpeg_status[0] if self._ffmpeg_status else False
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
        self._scan_label = "Quick Scan"                        ### NEW v0.17.0 ###
        self._start_quick_scan(folder)                         ### FIX v0.17.0-bugB ###

    def _start_quick_scan(self, folder):                       ### NEW v0.17.0-bugB, FIX v0.17.2 ###
        """Quick Scan: re-scan only subfolders that changed since the last scan.
        All heavy work (mtime reads, re-scan) runs in a background thread.
        The main thread only sets up UI state and spawns the thread.
        """
        try:
            entries = sorted([e for e in os.scandir(folder) if e.is_dir()],
                             key=lambda e: e.name.lower())
        except PermissionError:
            messagebox.showerror("Error", f"Cannot access: {folder}"); return
        if not entries:
            messagebox.showinfo("Empty", "No subfolders found."); return

        # Capture prior results BEFORE touching UI (still on main thread, fast)
        prior_by_path = {r["subfolder_path"]: r for r in self._results}
        prior_for_ff  = list(self._results)

        # Set up UI state immediately (no heavy work on main thread)
        self._scanning = True; self._cancel_scan = False
        self.scan_btn.configure(state="disabled")
        self.update_btn.configure(state="disabled")
        self.cancel_btn.pack(side="left", padx=(6, 0))
        self.pbar_canvas.pack(side="left", fill="x", expand=True)
        self.pbar_label.pack(side="left", padx=(8, 0))
        self._draw_scan_progress(0, "Quick Scan — detecting changes…")

        def worker():
            # ── Phase A: compute prior mtimes (background, can be slow) ────────
            prior_mtimes = {}
            for r in prior_for_ff:
                sp = r.get("subfolder_path", "")
                if not sp:
                    continue
                try:
                    files = [os.path.join(sp, fn) for fn in os.listdir(sp)
                             if os.path.isfile(os.path.join(sp, fn))]
                    prior_mtimes[sp] = max(
                        (os.path.getmtime(f) for f in files), default=0)
                except Exception:
                    prior_mtimes[sp] = 0

            if self._cancel_scan:
                self.after(0, lambda: self._scan_done(prior_for_ff)); return

            # ── Phase B: detect changed / new subfolders ────────────────────
            current_paths   = {e.path for e in entries}
            changed_entries = []
            for entry in entries:
                if entry.path not in prior_by_path:
                    changed_entries.append(entry)   # new
                    continue
                try:
                    files = [os.path.join(entry.path, fn)
                             for fn in os.listdir(entry.path)
                             if os.path.isfile(os.path.join(entry.path, fn))]
                    mtime_now = max((os.path.getmtime(f) for f in files), default=0)
                except Exception:
                    mtime_now = 0
                if mtime_now != prior_mtimes.get(entry.path, -1):
                    changed_entries.append(entry)   # modified

            n_changed = len(changed_entries)
            n_total   = len(entries)
            n_removed = max(0, len(prior_by_path) - len(current_paths & set(prior_by_path.keys())))
            logger.info(f"Quick Scan: {n_changed}/{n_total} changed, {n_removed} removed")

            if n_changed == 0 and current_paths == set(prior_by_path.keys()):
                self.after(0, lambda: (
                    self._scan_done(prior_for_ff),
                    messagebox.showinfo("Quick Scan",
                                        "No changes detected — library is up to date.")))
                return

            self.after(0, lambda nc=n_changed, nr=n_removed:
                self._draw_scan_progress(0,
                    f"Quick Scan — {nc} changed, {nr} removed"))

            # ── Phase C: rescan changed/new subfolders only ─────────────────
            rescanned = {}
            for i, entry in enumerate(changed_entries):
                if self._cancel_scan:
                    break
                pct = int((i + 1) / max(n_changed, 1) * 90)
                self.after(0, lambda p=pct, n=entry.name:
                    self._draw_scan_progress(p, f"Quick Scan — {n[:45]}"))
                try:
                    r = scan_one_subfolder(entry.path, entry.name,
                                           use_ffprobe=False)
                    # Preserve FFprobe data from prior scan
                    for rd in prior_for_ff:
                        if rd.get("subfolder_path") == entry.path:
                            for key in ("video_width", "video_height", "video_quality",
                                        "subs_internal", "subs_external", "subs_summary",
                                        "lang_ok", "audio_tracks"):
                                if rd.get(key) is not None:
                                    r[key] = rd[key]
                            break
                    rescanned[entry.path] = r
                except Exception as ex:
                    logger.error(f"Quick Scan error for {entry.name}: {ex}")

            # ── Phase D: rebuild full results list in folder order ──────────
            new_results = []
            for entry in entries:
                if entry.path in rescanned:
                    new_results.append(rescanned[entry.path])
                elif entry.path in prior_by_path:
                    new_results.append(prior_by_path[entry.path])
                # deleted subfolders are dropped

            self.after(0, lambda r=new_results: self._scan_done(r))

        threading.Thread(target=worker, daemon=True).start()

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
        self._scan_label = "Full Scan"                         ### NEW v0.17.0 ###
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

        _prior_results_for_ffprobe = list(self._results)  ### FIX v0.17.0-bugA ###
        self._results = []; self._item_map.clear()
        for r in self.tree.get_children(): self.tree.delete(r)

        self._scanning = True; self._cancel_scan = False
        logger.info(f"{getattr(self, '_scan_label', 'Scan')} started: {folder}")  ### NEW v0.17.0 ###
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
            ### FIX v0.17.0-bugA — use captured list; self._results was cleared before worker started ###
            _prior_ffprobe = {}
            for rd in _prior_results_for_ffprobe:
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
                    # v0.15.0 — new fields                               ### FIX v0.15.0 ###
                    "rating_votes":0,"rating_votes_src":"","rating_src":"",
                    "backdrop_avg_bytes":0,"audio_tracks":[],
                    # v0.16.0 — votes and source (filled in Phase 3)  ### NEW v0.16.0 ###
                    "votes_int":0,"votes_status":STATUS_MISSING,"votes_src":"",
                    "source_imdb_val":None,"source_imdb_status":STATUS_MISSING,"source_imdb_all":[],
                    "source_tmdb_val":None,"source_tmdb_status":STATUS_MISSING,"source_tmdb_all":[],
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

                bc, bp, bc_avg = count_backdrops(sub)              ### FIX v0.15.0 ###
                row["backdrop_count"] = bc; row["backdrop_paths"] = bp
                row["backdrop_avg_bytes"] = bc_avg                 ### FIX v0.15.0 ###
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
                rs, rst, rv, rv_votes, rv_votes_src, rv_src = (      ### FIX v0.15.0 ###
                    extract_rating_from_files(nfo_p_r, xml_p_r))
                row["rating_str"]        = rs
                row["rating_status"]     = rst
                row["rating_value"]      = rv
                row["rating_votes"]      = rv_votes                  ### FIX v0.15.0 ###
                row["rating_votes_src"]  = rv_votes_src              ### FIX v0.15.0 ###
                row["rating_src"]        = rv_src                    ### FIX v0.15.0 ###
                # Votes extraction (v0.16.0)                         ### NEW v0.16.0 ###
                vi_int, vi_st, vi_src = extract_votes_from_files(nfo_p_r, xml_p_r)
                row["votes_int"]    = vi_int
                row["votes_status"] = vi_st
                row["votes_src"]    = vi_src
                # Source IDs extraction (v0.16.0)                    ### NEW v0.16.0 ###
                src_ids = extract_source_ids_from_files(nfo_p_r, xml_p_r)
                row["source_imdb_val"]    = src_ids["imdb_val"]
                row["source_imdb_status"] = src_ids["imdb_status"]
                row["source_imdb_all"]    = src_ids["imdb_all_vals"]
                row["source_tmdb_val"]    = src_ids["tmdb_val"]
                row["source_tmdb_status"] = src_ids["tmdb_status"]
                row["source_tmdb_all"]    = src_ids["tmdb_all_vals"]
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
                # Audio tracks (v0.15.0)                            ### FIX v0.15.0 ###
                if use_ff and vi["video_path"] and FFPROBE_PATH:
                    audio_tracks = scan_audio_tracks(vi["video_path"])
                else:
                    audio_tracks = row.get("audio_tracks", [])
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
                    "audio_tracks": audio_tracks,                   ### FIX v0.15.0 ###
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

    def _apply_default_sort(self):                             ### NEW v0.16.1 ###
        """Reset sort to Movie Name (A-Z) and refresh table. No UI freeze."""
        self.sort_var.set("Movie Name (A-Z)")
        self._refresh_table()

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
        self._apply_default_sort()                             ### NEW v0.16.1 ###
        SETTINGS["last_folder"]  = self._folder
        SETTINGS["last_results"] = _results_to_json(results)
        self.after(50, self.tree.focus_set)                    ### NEW v0.17.0 — restore keyboard focus for jump-to-letter ###
        self._jump_last_char = None                            ### NEW v0.17.0 — reset jump state after scan ###
        self._jump_last_iid  = None
        self._jump_index     = {}                              ### NEW v0.17.2 ###
        SETTINGS["sort_option"]  = self.sort_var.get()
        _save_settings(SETTINGS)
        ### NEW v0.10.0 — update status bar on scan complete ###
        try:
            _warn = sum(1 for r in results if r["row_health"] == "yellow")
            _err  = sum(1 for r in results if r["row_health"] == "red")
            _label = getattr(self, "_scan_label", "Scan")     ### NEW v0.17.0 ###
            self._update_status_bar(len(results), _warn, _err,
                                    f"{_label} complete", self.sort_var.get())
            logger.info(f"{_label} complete: {len(results)} movies, {_warn} warnings, {_err} errors")
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
        self._update_stats()
        self._apply_default_sort()                             ### NEW v0.16.1 ###
        # Restore saved column widths (after table is populated)  ### NEW v0.18.0 ###
        self._restore_column_widths()
        # Run backup cleanup in background at startup  ### NEW v0.12.0 ###
        threading.Thread(target=clean_backup_folder_if_needed, daemon=True).start()

    def _restore_column_widths(self):                          ### NEW v0.18.0 ###
        """Apply persisted column widths from SETTINGS["column_widths"]."""
        saved = SETTINGS.get("column_widths", {})
        if not saved:
            return
        for col_id, width in saved.items():
            try:
                w = int(width)
                if w > 0:
                    self.tree.column(col_id, width=w)
            except (tk.TclError, ValueError, KeyError):
                pass   # column may not exist; silently skip

    def _on_app_close(self):                                   ### NEW v0.18.0 ###
        """Save column widths and current results, then destroy the window."""
        # Capture current column widths from the treeview
        widths = {}
        try:
            for col in self.tree["columns"]:
                w = self.tree.column(col, "width")
                if w and int(w) > 0:
                    widths[col] = int(w)
        except Exception:
            pass
        SETTINGS["column_widths"] = widths
        # Also persist current results so nothing is lost on close
        if self._results:
            SETTINGS["last_folder"]  = self._folder
            SETTINGS["last_results"] = _results_to_json(self._results)
        _save_settings(SETTINGS)
        self.destroy()

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
        ### NEW v0.13.0 — always recalculate errors/warnings for status bar ###
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

        # Votes cell format: "icon count" e.g. "⬤ 12,345" / "◐ 8,000" / "○ -" / "✕ -"  ### NEW v0.16.0 ###
        def votes_cell(votes_int, votes_status):
            if votes_status == STATUS_MISSING:
                return f"{STATUS_MISSING} -"
            if votes_status == STATUS_ERROR:
                return f"{STATUS_ERROR} -"
            return f"{votes_status} {votes_int:,}"

        # Source cell format: "⬤ IMDB - ⬤ TMDB"                           ### NEW v0.16.0 ###
        def source_cell(imdb_status, tmdb_status):
            return f"{imdb_status} IMDB  {tmdb_status} TMDB"

        return (
            r.get("movie_name", r["subfolder"]),               # COL_MOVIE_NAME
            r.get("movie_year", "-"),                          # COL_YEAR
            r.get("genre_status", STATUS_ERROR) + " " + r.get("genre_display", "-"),  # COL_GENRE
            rating_cell(r.get("rating_str", "-"), r.get("rating_status", STATUS_MISSING)),  # COL_RATING
            votes_cell(r.get("votes_int", 0), r.get("votes_status", STATUS_MISSING)),       # COL_VOTES  ### NEW v0.16.0 ###
            source_cell(r.get("source_imdb_status", STATUS_MISSING),                        # COL_SOURCE ### NEW v0.16.0 ###
                        r.get("source_tmdb_status", STATUS_MISSING)),
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
            ", ".join(                                                                 # COL_AUDIO ### NEW v0.15.0 ###
                (f"{t['language']} ({t['channels']})" if t.get('channels') else t['language'])
                for t in sorted(r.get("audio_tracks", []), key=lambda x: x.get("language",""))
            ),
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
               row.get("rating_status") == STATUS_ERROR or             ### NEW v0.12.0 ###
               row.get("source_imdb_status") == STATUS_ERROR or        ### NEW v0.16.0 ###
               row.get("source_tmdb_status") == STATUS_ERROR)          ### NEW v0.16.0 ###
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
