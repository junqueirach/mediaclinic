# =============================================================================
# settings_dialog.py
# Metadata & MediaClinic — Settings UI Module
# Version: 0.13.1                                              ### NEW v0.13.1 ###
# v0.13.1 — Fix: changing only the browser no longer triggers a rescan prompt.
#            Root cause was a tag_pairs false-positive in _rescan_changed: the
#            snapshot captured str(self._s.get("tag_pairs","")) while the
#            compare side captured str(_parse_tags_text()) after the text widget
#            was loaded from _DEFAULT_TAG_PAIRS — these two stringified differently
#            even when nothing had changed, so any save offered a rescan.
#            Snapshot and compare now both use the same _parse_tags_text() path.
#            Added an explicit guard so browser-only changes are never offered.
# v0.13.0                                                      ### NEW v0.13.0 ###
# v0.13.0 — Browser tab: selected radio visually highlighted (filled icon,
#            accent color, row tint, '(selected)' suffix), unselected dimmed
#            Rescan popup centered on parent with proper padding (no wait_window)
#            All tabs confirmed visible (Tools → Backup)
# v0.11.1 — Rescan offer after Image Sizes / Language / Genres / Tags save
#            Fixed _rescan_changed snapshot; version bump
# v0.11.0 — Version bump; quality tier tables injected from main module
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# This module contains the SettingsDialog class, extracted from the main
# application file as part of Phase B architecture refactoring.
#
# USAGE
#   from settings_dialog import SettingsDialog
#   SettingsDialog(parent_window, tab=0)
#
# DEPENDENCIES
# ------------
# This module imports shared globals from the main application at runtime.
# It must reside in the same folder as folder_scanner.py.
# It does NOT use sys.path manipulation or package structure.
#
# SHARED GLOBALS REQUIRED FROM MAIN MODULE (injected via _inject_globals)
# -----------------------------------------------------------------------
#   APP_NAME            str
#   SETTINGS            dict   (live reference — mutated directly)
#   _DEFAULT_SETTINGS   dict
#   DEFAULT_TAG_PAIRS   list
#   WORLD_LANGUAGES     list
#   logger              logging.Logger
#   _find_ffmpeg_ffprobe    callable
#   _find_notepadpp         callable
#   _test_ffmpeg            callable
#   _save_settings          callable
#   refresh_ffmpeg_paths    callable
#   detect_installed_browsers   callable
#   open_url_with_browser   callable
#
# TAB REGISTRY (tab index → builder method)
# -----------------------------------------
#   0  Tools          _build_tools_tab
#   1  API Keys       _build_api_keys_tab
#   2  Browser        _build_browser_tab
#   3  Language OK?   _build_language_tab
#   4  Improvements   _build_improvements_tab
#   5  Image Sizes    _build_image_sizes_tab
#   6  Genres         _build_genres_tab
#   7  NFO-XML Tags   _build_tags_tab
#
# VALIDATION HOOKS
# ----------------
# Each tab may call optional validation before save.
# The save/apply callback chain:
#   _save_close()
#     → gather all widget values
#     → call refresh_ffmpeg_paths()
#     → call _save_settings(SETTINGS)
#     → call parent._on_settings_changed() if available
#     → destroy()
#
# SERIES MODE PLACEHOLDER
# -----------------------
# TODO (Phase C): Add a "Series" settings tab for series-specific options
# such as episode naming patterns, season folder structure, and series
# metadata source preferences.
#
# =============================================================================

import json
import re
import threading
import copy                                                          ### ADDED_BY_CLAUDE_v18.2 ###
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
from settings_context import SettingsContext, run_async   # NEW v0.14.0
from settings_model import (                                         ### ADDED_BY_CLAUDE_v18.2 ###
    VIDEO_QUALITY_LEVELS, POSTER_QUALITY_LEVELS, FANART_QUALITY_LEVELS,
    AUDIO_LANGUAGES, SUBTITLE_LANGUAGES,
)


# ── Legacy quality tier name migration (v0.16.1) ─────────────────────────────
# Maps old labels to new labels. Applied on settings load so comboboxes
# never show empty/invalid values after upgrading from v0.16.0 or earlier.
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

# ── Module-level globals (populated by _inject_globals at import time) ────────
# These are set by the main module after import so that settings_dialog.py
# can share live state without circular imports.

_APP_NAME          = "Metadata & MediaClinic"
_SETTINGS          = {}
_DEFAULT_SETTINGS  = {}
_DEFAULT_TAG_PAIRS = []
_WORLD_LANGUAGES   = []
_logger            = None
### NEW v0.11.0 — image quality tier tables injected from main module ###
_POSTER_QUALITY_TIERS = []
_FANART_QUALITY_TIERS = []

_find_ffmpeg_ffprobe   = None
_find_notepadpp        = None
_test_ffmpeg           = None
_save_settings_fn      = None
_refresh_ffmpeg_paths  = None
_detect_browsers       = None
_open_url              = None
### NEW v0.12.0 — backup maintenance globals ###
_clean_backup_fn       = None
_BACKUP_ROOT_PATH      = None

### NEW v0.14.0 — SettingsContext built by _inject_globals; used by dialog ###
_ctx: "SettingsContext | None" = None


def _inject_globals(
    app_name, settings, default_settings, default_tag_pairs, world_languages,
    logger, fn_find_ffmpeg, fn_find_notepadpp, fn_test_ffmpeg, fn_save_settings,
    fn_refresh_ffmpeg, fn_detect_browsers, fn_open_url,
    poster_quality_tiers=None, fanart_quality_tiers=None,  ### NEW v0.11.0 ###
    fn_clean_backup=None, backup_root=None,                ### NEW v0.12.0 ###
):
    """
    Called once by the main module after import to inject all shared state.
    Using injection (instead of module-level imports) prevents circular
    imports and keeps the dependency direction: main → settings_dialog.
    """
    global _APP_NAME, _SETTINGS, _DEFAULT_SETTINGS, _DEFAULT_TAG_PAIRS
    global _WORLD_LANGUAGES, _logger
    global _find_ffmpeg_ffprobe, _find_notepadpp, _test_ffmpeg
    global _save_settings_fn, _refresh_ffmpeg_paths, _detect_browsers, _open_url
    global _POSTER_QUALITY_TIERS, _FANART_QUALITY_TIERS  ### NEW v0.11.0 ###
    global _clean_backup_fn, _BACKUP_ROOT_PATH           ### NEW v0.12.0 ###

    _APP_NAME          = app_name
    _SETTINGS          = settings
    _DEFAULT_SETTINGS  = default_settings
    _DEFAULT_TAG_PAIRS = default_tag_pairs
    _WORLD_LANGUAGES   = world_languages
    _logger            = logger

    # Migrate legacy quality tier labels to new v0.16.1 names  ### NEW v0.16.1 ###
    for _qkey in ("poster_quality_level", "folder_quality_level", "fanart_quality_level"):
        _old = settings.get(_qkey, "")
        if _old in _LEGACY_QUALITY_MAP:
            settings[_qkey] = _LEGACY_QUALITY_MAP[_old]

    _find_ffmpeg_ffprobe  = fn_find_ffmpeg
    _find_notepadpp       = fn_find_notepadpp
    _test_ffmpeg          = fn_test_ffmpeg
    _save_settings_fn     = fn_save_settings
    _refresh_ffmpeg_paths = fn_refresh_ffmpeg
    _detect_browsers      = fn_detect_browsers
    _open_url             = fn_open_url
    ### NEW v0.11.0 ###
    if poster_quality_tiers is not None:
        _POSTER_QUALITY_TIERS[:] = poster_quality_tiers
    if fanart_quality_tiers is not None:
        _FANART_QUALITY_TIERS[:] = fanart_quality_tiers
    ### NEW v0.12.0 ###
    if fn_clean_backup is not None:
        _clean_backup_fn = fn_clean_backup
    if backup_root is not None:
        _BACKUP_ROOT_PATH = backup_root

    ### NEW v0.14.0 — build and cache a SettingsContext from the injected values ###
    global _ctx
    _ctx = SettingsContext(
        app_name             = app_name,
        settings             = settings,
        defaults             = default_settings,
        tag_pairs            = default_tag_pairs,
        world_languages      = world_languages,
        logger               = logger,
        ffmpeg_finder        = fn_find_ffmpeg,
        notepadpp_finder     = fn_find_notepadpp,
        ffmpeg_tester        = fn_test_ffmpeg,
        save_settings        = fn_save_settings,
        refresh_ffmpeg       = fn_refresh_ffmpeg,
        detect_browsers      = fn_detect_browsers,
        open_url             = fn_open_url,
        poster_quality_tiers = list(poster_quality_tiers or []),
        fanart_quality_tiers = list(fanart_quality_tiers or []),
        clean_backup         = fn_clean_backup,
        backup_root          = backup_root or "",
    )


# ══════════════════════════════════════════════════════════════════════════════
# SettingsDialog
# ══════════════════════════════════════════════════════════════════════════════

class SettingsDialog(tk.Toplevel):
    """
    Full application settings dialog with tabbed UI.

    Tab registry (index → content):
        0  Tools          Editor, FFmpeg, Backdrop count, Scraper
        1  API Keys       TMDb and OMDb API key entry and validation
        2  Browser        Default browser selection
        3  Language OK?   Target language for the Lang OK? column
        4  Improvements   Toggle checks and set thresholds
        5  Image Sizes    Minimum KB per image type
        6  Genres         Editable genre list
        7  NFO-XML Tags   Tag comparison pairs for Improvements check 2.2

    Phase C TODO: Add tab 8 for Series-specific settings.

    Parameters
    ----------
    parent : tk.Widget
        Parent window (the main App instance).
    tab : int
        Tab index to select immediately on open (default 0).
        Used by the Settings menu to jump directly to the relevant tab.

    Save/apply callback chain:
        _save_close() gathers all widget values → saves to SETTINGS →
        calls refresh_ffmpeg_paths() → calls _save_settings() →
        calls parent._on_settings_changed() → destroys dialog.
    """

    # ── Tab builder registry ──────────────────────────────────────────────────
    # Maps tab index to (tab_label, builder_method_name).
    # Tab labels are full length — no truncation.             ### NEW v0.12.0 ###
    _TAB_REGISTRY = [
        (0,  "Tools",           "_build_tools_tab"),
        (1,  "API Keys",        "_build_api_keys_tab"),
        (2,  "Browser",         "_build_browser_tab"),
        (3,  "Language",        "_build_language_tab"),
        (4,  "Improvements",    "_build_improvements_tab"),
        (5,  "Image Sizes",     "_build_image_sizes_tab"),
        (6,  "Ratings",         "_build_ratings_tab"),
        (7,  "Genres",          "_build_genres_tab"),
        (8,  "NFO / XML",       "_build_tags_tab"),
        (9,  "User Interface",  "_build_ui_prefs_tab"),
        (10, "Health Rules",    "_build_health_rules_tab"),         ### ADDED_BY_CLAUDE_v18.2 ###
        (11, "Backup",          "_build_backup_tab"),               ### MODIFIED_BY_CLAUDE_v18.2 — was 10 ###
    ]

    def __init__(self, parent, tab=0, ctx=None):
        super().__init__(parent)
        # Store context — fall back to module-level _ctx for compatibility
        self._ctx = ctx if ctx is not None else _ctx
        self.title(f"Settings — {self._ctx.app_name if self._ctx else _APP_NAME}")
        self.geometry("920x660")   ### NEW v0.12.0 — wider to fit 10 tabs ###
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(True, True)
        self._parent      = parent
        self._initial_tab = tab

        ### NEW v0.14.0 — resolve all injected globals from ctx at init time ###
        # Tab builders use these instance attributes so they work correctly
        # whether ctx is passed directly OR populated via _inject_globals.
        _c = self._ctx
        self._s               = _c.settings             if _c else _SETTINGS
        self._defaults        = _c.defaults             if _c else _DEFAULT_SETTINGS
        self._tag_pairs_default = _c.tag_pairs          if _c else _DEFAULT_TAG_PAIRS
        self._langs           = _c.world_languages      if _c else _WORLD_LANGUAGES
        self._poster_tiers    = _c.poster_quality_tiers if _c else _POSTER_QUALITY_TIERS
        self._fanart_tiers    = _c.fanart_quality_tiers if _c else _FANART_QUALITY_TIERS
        self._open_url_fn     = _c.open_url             if _c else _open_url

        # ── Notebook ─────────────────────────────────────────────────────────
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=0, pady=0)
        style = ttk.Style()
        style.configure("TNotebook",     background="#1e1e2e", borderwidth=0)
        ### NEW v0.12.0 — reduced padding so all 10 tab labels fit without truncation ###
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4",
                        padding=[8, 5], font=("Helvetica", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", "#45475a")],
                  foreground=[("selected", "#89b4fa")])

        # ── Build all tabs from registry ──────────────────────────────────────
        for idx, label, method_name in self._TAB_REGISTRY:
            builder = getattr(self, method_name, None)
            if builder:
                builder(nb, label)

        # ── Snapshot rescan-relevant settings on open        ### NEW v0.11.1 ###
        # Used by _save_close to detect whether a rescan should be offered.
        self._rescan_snapshot = self._take_rescan_snapshot()

        # ── Bottom buttons ────────────────────────────────────────────────────
        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(6, 12))
        tk.Button(bf, text="  Save & Close  ", font=("Helvetica", 10, "bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._save_close).pack(side="left", padx=(0, 8))
        tk.Button(bf, text="  Cancel  ", font=("Helvetica", 10, "bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self.destroy).pack(side="left")

        # ── Jump to requested tab after UI is built ───────────────────────────
        self._nb = nb
        self.after(10, lambda: nb.select(min(self._initial_tab, len(nb.tabs()) - 1)))

    # ── Shared widget helpers ─────────────────────────────────────────────────

    @staticmethod
    def _section(parent, label):
        tk.Label(parent, text=label, font=("Helvetica", 11, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", padx=16, pady=(14, 2))

    @staticmethod
    def _note(parent, text):
        tk.Label(parent, text=text, font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086",
                 justify="left").pack(anchor="w", padx=16, pady=(0, 2))

    @staticmethod
    def _row(parent):
        r = tk.Frame(parent, bg="#1e1e2e"); r.pack(fill="x", padx=16, pady=2)
        return r

    def _file_entry_row(self, parent, var, title, filetypes):
        r = self._row(parent)
        tk.Entry(r, textvariable=var, font=("Consolas", 9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=50).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="Browse…", font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: self._browse_file(var, title, filetypes)
                  ).pack(side="left", padx=(6, 0))
        return r

    @staticmethod
    def _browse_file(var, title, filetypes):
        p = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if p: var.set(p)

    # ── Tab 0: Tools ──────────────────────────────────────────────────────────

    def _build_tools_tab(self, nb, label="Tools"):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=label)

        # Text editor
        self._section(f, "Text Editor (for NFO / XML files)")
        self._note(f, "Notepad++ is auto-detected. File path is passed BEFORE -lxml flag.\n"
                      "If left blank, falls back to OS default editor.")
        self._editor_var = tk.StringVar(value=self._s.get("text_editor", ""))
        r = self._file_entry_row(f, self._editor_var, "Select text editor",
                                 [("Executables", "*.exe"), ("All", "*.*")])
        ### MODIFIED_BY_CLAUDE_v18 — run notepadpp_finder on daemon thread to avoid blocking UI ###
        def _npp_done(npp):
            if npp and not self._editor_var.get():
                self._editor_var.set(npp)
        if self._ctx and self._ctx.notepadpp_finder:
            run_async(self._ctx.notepadpp_finder, callback=_npp_done, root=self)
        tk.Button(r, text="Test", font=("Helvetica", 9), bg="#45475a", fg="#a6e3a1",
                  relief="flat", cursor="hand2",
                  command=lambda: self._test_editor(self._editor_var)
                  ).pack(side="left", padx=(4, 0))

        # FFmpeg
        self._section(f, "FFmpeg / FFprobe")
        self._note(f, "Point to the folder containing ffmpeg.exe and ffprobe.exe.\n"
                      "Leave blank to use system PATH.")
        self._ffmpeg_var = tk.StringVar(value=self._s.get("ffmpeg_path", ""))
        if not self._ffmpeg_var.get() and self._ctx and self._ctx.ffmpeg_finder:
            ff, _ = self._ctx.ffmpeg_finder("")
            import os
            if ff: self._ffmpeg_var.set(os.path.dirname(ff))
        r = self._row(f)
        tk.Entry(r, textvariable=self._ffmpeg_var, font=("Consolas", 9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=50).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="Browse…", font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: self._ffmpeg_var.set(
                      filedialog.askdirectory(title="FFmpeg folder") or self._ffmpeg_var.get())
                  ).pack(side="left", padx=(6, 0))
        self._ff_status_lbl = tk.Label(r, text="", font=("Helvetica", 9),
                                       bg="#1e1e2e", fg="#a6adc8")
        self._ff_status_lbl.pack(side="left", padx=(8, 0))
        tk.Button(r, text="Test FFmpeg", font=("Helvetica", 9), bg="#45475a", fg="#f9e2af",
                  relief="flat", cursor="hand2",
                  command=self._test_ffmpeg_btn).pack(side="left", padx=(4, 0))

        # Backdrop count
        self._section(f, "Backdrop Extraction")
        self._note(f, "Default number of backdrop frames to extract per movie.")
        r = self._row(f)
        tk.Label(r, text="Default frame count:", font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=26, anchor="w").pack(side="left")
        self._backdrop_count_var = tk.IntVar(value=self._s.get("backdrop_count", 10))
        tk.Spinbox(r, from_=1, to=50, textvariable=self._backdrop_count_var, width=6,
                   font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                   buttonbackground="#45475a", relief="flat").pack(side="left")

        # Metadata source / scraper
        self._section(f, "Video Scraper / Metadata Source")
        self._note(f, "Choose the metadata source for ratings, votes, and IDs.\n"
                      "The scraper launch path remains available below.")
        r = self._row(f)
        tk.Label(r, text="Metadata source:", font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=20, anchor="w").pack(side="left")
        self._meta_src_var = tk.StringVar(value=self._s.get("metadata_source", "tmdb"))
        for val, lbl in [("tmdb", "TMDb (recommended)"), ("omdb", "IMDb via OMDb API")]:
            tk.Radiobutton(r, text=lbl, variable=self._meta_src_var, value=val,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(side="left", padx=(0, 16))
        tk.Label(f, text="  ⚙  Online metadata fetching will be enabled in a future update.",
                 font=("Helvetica", 9, "italic"), bg="#1e1e2e", fg="#6c7086"
                 ).pack(anchor="w", padx=16, pady=(2, 0))
        self._note(f, "\nScraper executable (optional — launched with movie folder as argument):")
        self._scraper_var = tk.StringVar(value=self._s.get("scraper_path", ""))
        self._file_entry_row(f, self._scraper_var, "Select scraper",
                             [("Executables", "*.exe"), ("All", "*.*")])

    def _test_editor(self, var):
        path = var.get().strip()
        if not path:
            messagebox.showwarning("Not set", "No editor path set.", parent=self); return
        import os
        if not os.path.isfile(path):
            messagebox.showerror("Not found", f"File not found:\n{path}", parent=self); return
        try:
            subprocess.Popen([path],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            messagebox.showinfo("Test", f"Editor launched:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Launch failed", str(e), parent=self)

    def _test_ffmpeg_btn(self):
        ### NEW v0.14.0 — subprocess runs on daemon thread; never blocks UI ###
        ctx = self._ctx
        if not ctx or not ctx.ffmpeg_finder or not ctx.ffmpeg_tester:
            return
        path = self._ffmpeg_var.get().strip()
        self._ff_status_lbl.configure(text="Testing…", fg="#a6adc8")

        def _work():
            ff, fp = ctx.ffmpeg_finder(path)
            return ctx.ffmpeg_tester(ff, fp)

        def _done(result):
            ff_ok, fp_ok, ff_msg, fp_msg = result
            if ff_ok and fp_ok:
                self._ff_status_lbl.configure(text="✓ Both OK", fg="#a6e3a1")
            else:
                msgs = []
                if not ff_ok: msgs.append(f"ffmpeg: {ff_msg}")
                if not fp_ok: msgs.append(f"ffprobe: {fp_msg}")
                self._ff_status_lbl.configure(
                    text="✗ " + " | ".join(msgs), fg="#f38ba8")

        run_async(_work, callback=_done, root=self)

    # ── Tab 1: API Keys ───────────────────────────────────────────────────────

    def _build_api_keys_tab(self, nb, label="API Keys"):
        outer = tk.Frame(nb, bg="#1e1e2e"); nb.add(outer, text=label)

        canvas = tk.Canvas(outer, bg="#1e1e2e", highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        f = tk.Frame(canvas, bg="#1e1e2e")
        canvas.create_window((0, 0), window=f, anchor="nw")
        f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # TMDb
        self._section(f, "TMDb API Key (The Movie Database)")
        self._note(f, "Required for fetching ratings and metadata from TMDb.\n"
                      "Your key is stored locally in settings.json and never shared.\n"
                      "Free key — no subscription required.")
        self._tmdb_var = tk.StringVar(value=self._s.get("tmdb_api_key", ""))
        r = self._row(f)
        self._tmdb_entry = tk.Entry(r, textvariable=self._tmdb_var, font=("Consolas", 9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=46, show="•")
        self._tmdb_entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="👁", font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2", width=2,
                  command=lambda: self._toggle_show(self._tmdb_entry)
                  ).pack(side="left", padx=(4, 0))
        tk.Button(r, text="Validate", font=("Helvetica", 9), bg="#45475a", fg="#f9e2af",
                  relief="flat", cursor="hand2",
                  command=self._validate_tmdb).pack(side="left", padx=(4, 0))
        self._tmdb_status = tk.Label(r, text="", font=("Helvetica", 9),
                                     bg="#1e1e2e", fg="#a6adc8")
        self._tmdb_status.pack(side="left", padx=(6, 0))

        r2 = self._row(f)
        tk.Label(r2, text="No key yet?", font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        lnk1 = tk.Label(r2, text=" ➜ Click here to get your free TMDb API key",
                         font=("Helvetica", 9, "underline"), bg="#1e1e2e", fg="#89b4fa",
                         cursor="hand2")
        lnk1.pack(side="left")
        lnk1.bind("<Button-1>", lambda e: self._open_url_fn("https://www.themoviedb.org/settings/api")
                  if self._open_url_fn else None)

        self._note(f, "\nHow to get a TMDb key:\n"
                      "  1. Create a free account at themoviedb.org\n"
                      "  2. Go to Settings → API (left sidebar)\n"
                      "  3. Click 'Request an API Key' → choose Developer\n"
                      "  4. Fill in the form and your key appears immediately\n"
                      "  5. Copy the 'API Key (v3 auth)' value here")

        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(12, 0))

        # OMDb
        self._section(f, "OMDb API Key (IMDb data via OMDb)")
        self._note(f, "Required for fetching IMDb ratings via the OMDb API.\n"
                      "Your key is stored locally and never shared.\n"
                      "Free tier: 1,000 requests/day.")
        self._omdb_var = tk.StringVar(value=self._s.get("omdb_api_key", ""))
        r = self._row(f)
        self._omdb_entry = tk.Entry(r, textvariable=self._omdb_var, font=("Consolas", 9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=46, show="•")
        self._omdb_entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="👁", font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2", width=2,
                  command=lambda: self._toggle_show(self._omdb_entry)
                  ).pack(side="left", padx=(4, 0))
        tk.Button(r, text="Validate", font=("Helvetica", 9), bg="#45475a", fg="#f9e2af",
                  relief="flat", cursor="hand2",
                  command=self._validate_omdb).pack(side="left", padx=(4, 0))
        self._omdb_status = tk.Label(r, text="", font=("Helvetica", 9),
                                     bg="#1e1e2e", fg="#a6adc8")
        self._omdb_status.pack(side="left", padx=(6, 0))

        r3 = self._row(f)
        tk.Label(r3, text="No key yet?", font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        lnk2 = tk.Label(r3, text=" ➜ Click here to get your free OMDb API key",
                         font=("Helvetica", 9, "underline"), bg="#1e1e2e", fg="#89b4fa",
                         cursor="hand2")
        lnk2.pack(side="left")
        lnk2.bind("<Button-1>", lambda e: self._open_url_fn("https://www.omdbapi.com/apikey.aspx")
                  if self._open_url_fn else None)

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
        def _worker():  # MODIFIED_BY_CLAUDE_v18 - migrated from threading.Thread to run_async
            import urllib.request, urllib.error, gzip as _gzip
            ok = False
            msg = "✗ Invalid or network error"
            try:
                url = f"https://api.themoviedb.org/3/configuration?api_key={key}"
                req = urllib.request.Request(url, headers={
                    "User-Agent": "MediaClinic/0.17.0",
                })
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw = resp.read()
                # Defensive gzip detection (no explicit Accept-Encoding sent)
                if len(raw) >= 2 and raw[0] == 0x1f and raw[1] == 0x8b:
                    try: raw = _gzip.decompress(raw)
                    except Exception: pass
                try:
                    data = json.loads(raw.decode("utf-8"))
                except UnicodeDecodeError:
                    data = json.loads(raw.decode("latin-1"))
                ok = "images" in data
                msg = "✓ Valid" if ok else "✗ Unexpected response"
            except urllib.error.HTTPError as e:
                try:
                    import gzip as _gzip2
                    raw = e.read()
                    if len(raw) > 1 and raw[0] == 0x1f and raw[1] == 0x8b:
                        raw = _gzip2.decompress(raw)
                    body = json.loads(raw)
                    detail = body.get("status_message", e.reason)
                except Exception:
                    detail = e.reason
                if e.code == 401:
                    msg = f"✗ Invalid key (HTTP 401): {detail}"
                elif e.code == 429:
                    msg = "✗ Rate limited (HTTP 429) — try again shortly"
                else:
                    msg = f"✗ HTTP {e.code}: {detail}"
            except urllib.error.URLError as e:
                r = str(e.reason)
                if "timed out" in r.lower():
                    msg = "✗ Timeout — TMDB unreachable"
                elif any(k in r.lower() for k in ("nodename","getaddrinfo","resolve")):
                    msg = "✗ No internet / DNS failure"
                else:
                    msg = f"✗ Network error: {r}"
            except Exception as e:
                msg = f"✗ Error: {type(e).__name__}: {e}"
            return (ok, msg)
        def _tmdb_done(result):
            ok, msg = result
            self._tmdb_status.configure(text=msg, fg="#a6e3a1" if ok else "#f38ba8")
        run_async(_worker, callback=_tmdb_done, root=self)

    def _validate_omdb(self):
        key = self._omdb_var.get().strip()
        if not key:
            self._omdb_status.configure(text="No key entered", fg="#f38ba8"); return
        self._omdb_status.configure(text="Testing…", fg="#a6adc8")
        self.update_idletasks()
        def _worker():  # MODIFIED_BY_CLAUDE_v18 - migrated from threading.Thread to run_async
            try:
                import urllib.request
                url = f"https://www.omdbapi.com/?apikey={key}&t=test&type=movie"
                req = urllib.request.Request(url, headers={"User-Agent": "MediaClinic/0.10.1"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read())
                ok = data.get("Response") != "False" or \
                     "Unauthorized" not in data.get("Error", "")
            except Exception:
                ok = False
            return ok
        def _omdb_done(ok):
            self._omdb_status.configure(
                text="✓ Valid" if ok else "✗ Invalid or network error",
                fg="#a6e3a1" if ok else "#f38ba8")
        run_async(_worker, callback=_omdb_done, root=self)

    # ── Tab 2: Browser ────────────────────────────────────────────────────────

    def _build_browser_tab(self, nb, label="Browser"):
        """Browser selection tab with enhanced visual radio button feedback.
        ### NEW v0.13.0 — selected option highlighted (filled icon, accent bg,
        '(selected)' suffix); unselected options dimmed. ###
        ### NEW v0.14.0 — browser detection runs on daemon thread via run_async ###
        """
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=label)

        self._section(f, "Default Browser for External Links")
        self._note(f, "Used when opening IMDB, TMDb, OpenSubtitles, or any other URL.\n"
                      "Leave on 'System Default' to let Windows decide.\n"
                      "Detected browsers are listed automatically.")

        self._browser_var = tk.StringVar(value=self._s.get("default_browser", ""))

        options_frame = tk.Frame(f, bg="#1e1e2e")
        options_frame.pack(anchor="w", padx=24, pady=(6, 0))

        # Store per-row widgets for dynamic update — populated by _build_radio_buttons
        _row_frames   = []   # highlight Frame per option
        _label_vars   = []   # StringVar for label text per option
        _radio_btns   = []   # Radiobutton widget per option
        _options_ref  = []   # mutable ref so _update_browser_highlight can read current options

        # Colors
        _BG_NORMAL   = "#1e1e2e"
        _BG_SELECTED = "#1a2e45"   # subtle blue tint for selected row
        _FG_SELECTED = "#89b4fa"   # accent blue
        _FG_DIM      = "#6c7086"   # dimmed gray for unselected

        def _update_browser_highlight(*_):
            """Refresh colors, icon, and label suffix for all radio options."""
            current = self._browser_var.get()
            for idx, (base_label, val) in enumerate(_options_ref):
                is_sel = (val == current)
                row_f   = _row_frames[idx]
                lv      = _label_vars[idx]
                rb      = _radio_btns[idx]
                if is_sel:
                    row_f.configure(bg=_BG_SELECTED)
                    lv.set(f"{base_label} (selected)")
                    rb.configure(
                        bg=_BG_SELECTED,
                        fg=_FG_SELECTED,
                        activebackground=_BG_SELECTED,
                        activeforeground=_FG_SELECTED,
                        selectcolor="#2a4a6e",
                    )
                    # Update all children of row_f to the selected background
                    for child in row_f.winfo_children():
                        try: child.configure(bg=_BG_SELECTED)
                        except Exception: pass
                else:
                    row_f.configure(bg=_BG_NORMAL)
                    lv.set(base_label)
                    rb.configure(
                        bg=_BG_NORMAL,
                        fg=_FG_DIM,
                        activebackground=_BG_NORMAL,
                        activeforeground="#cdd6f4",
                        selectcolor="#313244",
                    )
                    for child in row_f.winfo_children():
                        try: child.configure(bg=_BG_NORMAL)
                        except Exception: pass

        def _build_radio_buttons(options):
            """Build radio button widgets from an (label, value) list.
            Called on the main thread once browser detection completes.
            Widget variable names and highlight logic are identical to v0.13.1.
            """
            _options_ref.clear()
            _options_ref.extend(options)
            for base_label, val in options:
                row_f = tk.Frame(options_frame, bg=_BG_NORMAL)
                row_f.pack(fill="x", anchor="w", pady=1)

                lv = tk.StringVar(value=base_label)
                rb = tk.Radiobutton(
                    row_f,
                    textvariable=lv,
                    variable=self._browser_var,
                    value=val,
                    font=("Helvetica", 10),
                    bg=_BG_NORMAL, fg=_FG_DIM,
                    selectcolor="#313244",
                    activebackground=_BG_NORMAL,
                    activeforeground="#cdd6f4",
                    command=_update_browser_highlight,
                    indicatoron=True,
                )
                rb.pack(anchor="w", padx=6, pady=2)

                _row_frames.append(row_f)
                _label_vars.append(lv)
                _radio_btns.append(rb)

                # Show path label for named browsers
                if val:
                    tk.Label(row_f, text=f"   {val}",
                             font=("Consolas", 8), bg=_BG_NORMAL, fg="#45475a").pack(anchor="w")

        ### NEW v0.14.0 — detect browsers on daemon thread; populate on callback ###
        _detecting_lbl = tk.Label(options_frame,
                                  text="Detecting browsers…",
                                  font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086")
        _detecting_lbl.pack(anchor="w", pady=2)

        def _populate_browsers(detected):
            """Called on main thread after browser detection completes."""
            _detecting_lbl.destroy()
            options = [("System Default (recommended)", "")]
            for name, path in (detected or []):
                options.append((name, path))
            _build_radio_buttons(options)
            if not detected:
                tk.Label(options_frame,
                         text="No additional browsers detected in standard locations.",
                         font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086"
                         ).pack(anchor="w", pady=4)
            # Run initial highlight so the current saved value is shown correctly
            self._browser_var.trace_add("write", _update_browser_highlight)
            _update_browser_highlight()

        ctx = self._ctx
        if ctx and ctx.detect_browsers:
            run_async(ctx.detect_browsers, callback=_populate_browsers, root=self)
        else:
            _populate_browsers([])

        self._section(f, "Or Enter Browser Path Manually")
        self._note(f, "Browse to any browser executable not listed above.")
        r = self._row(f)
        tk.Entry(r, textvariable=self._browser_var, font=("Consolas", 9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=50).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="Browse…", font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: self._browse_file(self._browser_var, "Select browser",
                                                    [("Executables", "*.exe"), ("All", "*.*")])
                  ).pack(side="left", padx=(6, 0))
        tk.Button(r, text="Test", font=("Helvetica", 9), bg="#45475a", fg="#a6e3a1",
                  relief="flat", cursor="hand2",
                  command=self._test_browser).pack(side="left", padx=(4, 0))

    def _test_browser(self):
        import os
        p = self._browser_var.get().strip()
        if not p:
            messagebox.showinfo("System Default",
                                "Using system default browser — no path to test.", parent=self)
            return
        if not os.path.isfile(p):
            messagebox.showerror("Not found", f"File not found:\n{p}", parent=self); return
        try:
            subprocess.Popen([p, "https://www.themoviedb.org"],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            messagebox.showinfo("Test", f"Browser launched:\n{p}", parent=self)
        except Exception as e:
            messagebox.showerror("Launch failed", str(e), parent=self)

    # ── Tab 3: Language OK? ───────────────────────────────────────────────────

    def _build_language_tab(self, nb, label="Language"):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=label)

        tk.Label(f, text="Language OK? Column Target",
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(f, text="Select the language for the 'Lang OK?' column.\n"
                 "The column header and Y/N values will update automatically.\n"
                 "Sources checked: FFprobe audio, internal subtitles, external subtitles,\n"
                 "XML LanguageCode, XML Audio/Language, NFO video/language.",
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#a6adc8",
                 justify="left").pack(anchor="w", padx=16, pady=(0, 12))

        self._lang_var = tk.StringVar(value=self._s.get("lang_ok_code", "PT"))
        lang_frame = tk.Frame(f, bg="#1e1e2e"); lang_frame.pack(padx=16, fill="x")
        tk.Label(lang_frame, text="Language:", font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self._lang_combo = ttk.Combobox(lang_frame, textvariable=self._lang_var,
                                        values=[iso for iso, _ in self._langs],
                                        state="readonly", width=8, font=("Helvetica", 11))
        self._lang_combo.pack(side="left", padx=(8, 16))
        self._lang_desc = tk.Label(lang_frame, text="", font=("Helvetica", 10),
                                   bg="#1e1e2e", fg="#a6adc8")
        self._lang_desc.pack(side="left")
        self._lang_combo.bind("<<ComboboxSelected>>", self._update_lang_desc)
        self._update_lang_desc()

        tk.Label(f, text="\nAvailable languages:",
                 font=("Helvetica", 10, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16)
        grid_f = tk.Frame(f, bg="#1e1e2e"); grid_f.pack(padx=16, fill="x")
        for i, (iso, name) in enumerate(self._langs):
            r = i // 3; c = i % 3
            tk.Label(grid_f, text=f"{iso} — {name}",
                     font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086",
                     anchor="w", width=22).grid(row=r, column=c, sticky="w", pady=1)

    def _update_lang_desc(self, *_):
        code = self._lang_var.get().upper()
        for iso, name in self._langs:
            if iso == code:
                self._lang_desc.configure(text=f"→ {name}")
                return
        self._lang_desc.configure(text="")

    # ── Tab 4: Improvements ───────────────────────────────────────────────────

    def _build_improvements_tab(self, nb, label="Improvements"):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=label)

        tk.Label(f, text="Improvement Checks",
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16, 6))

        ic = self._s.get("improve_checks", self._defaults.get("improve_checks", {}))  ### FIX v0.15.0 ###
        self._ic_vars = {}
        checks_def = [
            ("large_xml",    "2.1  Large XML/NFO files (flag files above threshold)"),
            ("nfo_xml_diff", "2.2  NFO ↔ XML data mismatches"),
            ("ffprobe_diff", "2.3  FFprobe vs NFO/XML metadata differences"),
            ("poster_folder","2.4  poster.jpg and folder.jpg size differences"),
            ("proportions",  "2.5  Image proportion and file size issues"),
            ("backdrops",    "2.6  Insufficient backdrops"),
        ]
        for key, label in checks_def:
            v = tk.BooleanVar(value=ic.get(key, True))
            self._ic_vars[key] = v
            tk.Checkbutton(f, text=label, variable=v,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(anchor="w", padx=24, pady=2)

        tk.Label(f, text="\nThresholds:", font=("Helvetica", 11, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", padx=16)

        def _spin_row(parent, label, varname, default, from_, to_):
            r = tk.Frame(parent, bg="#1e1e2e"); r.pack(anchor="w", padx=24, pady=2)
            tk.Label(r, text=label, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                     width=36, anchor="w").pack(side="left")
            v = tk.IntVar(value=self._s.get(varname, default))
            setattr(self, f"_{varname}_var", v)
            tk.Spinbox(r, from_=from_, to=to_, textvariable=v, width=6,
                       font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                       buttonbackground="#45475a", relief="flat").pack(side="left")
            return v

        _spin_row(f, "Max NFO file size (KB) before flagging:", "max_nfo_kb",  50, 1, 9999)
        _spin_row(f, "Max XML file size (KB) before flagging:", "max_xml_kb",  25, 1, 9999)
        # min_backdrops removed from UI in v0.18.2 — now lives in Health Rules tab ### MODIFIED_BY_CLAUDE_v18.2 ###

    # ── Tab 5: Image Sizes ────────────────────────────────────────────────────

    def _build_image_sizes_tab(self, nb, label="Image Sizes"):
        """Image quality and proportion settings.          ### NEW v0.11.0 ###"""

        outer = tk.Frame(nb, bg="#1e1e2e"); nb.add(outer, text=label)
        canvas = tk.Canvas(outer, bg="#1e1e2e", highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        f = tk.Frame(canvas, bg="#1e1e2e")
        canvas.create_window((0, 0), window=f, anchor="nw")
        f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # ── Proportion Checks ─────────────────────────────────────────────────
        self._section(f, "Proportion Checks")

        ### NEW v0.12.0 — poster/folder 3:4 acceptance toggle (above fanart 16:8) ###
        r_34 = self._row(f)
        tk.Label(r_34, text="Accept poster.jpg and folder.jpg also in 3:4 (0.75 ratio)?",
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=50, anchor="w").pack(side="left")
        self._poster_34_var = tk.StringVar(
            value="Yes" if self._s.get("poster_accept_34", False) else "No")
        poster_34_cb = ttk.Combobox(r_34, textvariable=self._poster_34_var,
                                    values=["Yes", "No"], state="readonly",
                                    width=6, font=("Helvetica", 10))
        poster_34_cb.pack(side="left", padx=(8, 0))
        poster_34_cb.bind("<<ComboboxSelected>>", self._update_proportion_text)

        # Fanart 16:8 acceptance toggle
        r0 = self._row(f)
        tk.Label(r0, text="Accept fanart.jpg also in 16:8 (1.50 ratio)?",
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=50, anchor="w").pack(side="left")
        self._fanart_168_var = tk.StringVar(
            value="Yes" if self._s.get("fanart_accept_168", False) else "No")
        fanart_168_cb = ttk.Combobox(r0, textvariable=self._fanart_168_var,
                                     values=["Yes", "No"], state="readonly",
                                     width=6, font=("Helvetica", 10))
        fanart_168_cb.pack(side="left", padx=(8, 0))
        fanart_168_cb.bind("<<ComboboxSelected>>", self._update_proportion_text)

        # Dynamic proportion description label
        self._prop_text_var = tk.StringVar()
        prop_lbl = tk.Label(f, textvariable=self._prop_text_var,
                            font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086",
                            justify="left", anchor="w")
        prop_lbl.pack(anchor="w", padx=16, pady=(2, 8))
        self._update_proportion_text()   # set initial text

        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(0, 4))

        # ── Minimum Image Quality (Resolution-driven) ─────────────────────────
        self._section(f, "Minimum Image Quality (Resolution-driven)")
        self._note(f,
            "Choose the minimum acceptable quality for each image type.\n"
            "Images below the selected tier are flagged as errors.\n"
            "Tolerance: ±5% to account for compression and aspect variations.")

        # ──────────── Poster / Folder ─────────────────────────────────────────
        tk.Label(f, text="POSTER / FOLDER  (2:3 portrait ratio)",
                 font=("Helvetica", 10, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(10, 2))

        poster_tiers = [t[0] for t in self._poster_tiers]
        # Info table for poster
        hdr_f = tk.Frame(f, bg="#1e1e2e"); hdr_f.pack(anchor="w", padx=24)
        for col, w in [("Quality", 18), ("Resolution", 14), ("Total Pixels", 14), ("Est. File Size", 16)]:
            tk.Label(hdr_f, text=col, font=("Consolas", 8, "bold"),
                     bg="#1e1e2e", fg="#89b4fa", width=w, anchor="w").pack(side="left")
        for label, mw, mh, tp, esz in self._poster_tiers:
            row_f = tk.Frame(f, bg="#1e1e2e"); row_f.pack(anchor="w", padx=24)
            tk.Label(row_f, text=label, font=("Consolas", 8),
                     bg="#1e1e2e", fg="#cdd6f4", width=18, anchor="w").pack(side="left")
            tk.Label(row_f, text=f"{mw}×{mh}", font=("Consolas", 8),
                     bg="#1e1e2e", fg="#a6adc8", width=14, anchor="w").pack(side="left")
            tk.Label(row_f, text=f"{tp/1_000_000:.1f}M", font=("Consolas", 8),
                     bg="#1e1e2e", fg="#a6adc8", width=14, anchor="w").pack(side="left")
            tk.Label(row_f, text=esz, font=("Consolas", 8),
                     bg="#1e1e2e", fg="#a6adc8", width=16, anchor="w").pack(side="left")

        r1 = self._row(f)
        tk.Label(r1, text="Minimum quality — poster.jpg:",
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=36, anchor="w").pack(side="left")
        self._poster_ql_var = tk.StringVar(
            value=self._s.get("poster_quality_level", "1080p"))
        ttk.Combobox(r1, textvariable=self._poster_ql_var,
                     values=poster_tiers, state="readonly",
                     width=18, font=("Helvetica", 10)).pack(side="left", padx=(8, 0))

        r2 = self._row(f)
        tk.Label(r2, text="Minimum quality — folder.jpg:",
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=36, anchor="w").pack(side="left")
        self._folder_ql_var = tk.StringVar(
            value=self._s.get("folder_quality_level", "1080p"))
        ttk.Combobox(r2, textvariable=self._folder_ql_var,
                     values=poster_tiers, state="readonly",
                     width=18, font=("Helvetica", 10)).pack(side="left", padx=(8, 0))

        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(10, 4))

        # ──────────── Fanart ──────────────────────────────────────────────────
        tk.Label(f, text="FANART  (16:9 or 16:8 landscape ratio)",
                 font=("Helvetica", 10, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(10, 2))

        fanart_tiers = [t[0] for t in self._fanart_tiers]
        hdr_f2 = tk.Frame(f, bg="#1e1e2e"); hdr_f2.pack(anchor="w", padx=24)
        for col, w in [("Quality", 22), ("Resolution", 14), ("Total Pixels", 14), ("Est. File Size", 16)]:
            tk.Label(hdr_f2, text=col, font=("Consolas", 8, "bold"),
                     bg="#1e1e2e", fg="#89b4fa", width=w, anchor="w").pack(side="left")
        for label, mw, mh, tp, esz in self._fanart_tiers:
            row_f = tk.Frame(f, bg="#1e1e2e"); row_f.pack(anchor="w", padx=24)
            tk.Label(row_f, text=label, font=("Consolas", 8),
                     bg="#1e1e2e", fg="#cdd6f4", width=22, anchor="w").pack(side="left")
            tk.Label(row_f, text=f"{mw}×{mh}", font=("Consolas", 8),
                     bg="#1e1e2e", fg="#a6adc8", width=14, anchor="w").pack(side="left")
            tk.Label(row_f, text=f"{tp/1_000_000:.1f}M", font=("Consolas", 8),
                     bg="#1e1e2e", fg="#a6adc8", width=14, anchor="w").pack(side="left")
            tk.Label(row_f, text=esz, font=("Consolas", 8),
                     bg="#1e1e2e", fg="#a6adc8", width=16, anchor="w").pack(side="left")

        r3 = self._row(f)
        tk.Label(r3, text="Minimum quality — fanart.jpg:",
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=36, anchor="w").pack(side="left")
        self._fanart_ql_var = tk.StringVar(
            value=self._s.get("fanart_quality_level", "1080p"))
        ttk.Combobox(r3, textvariable=self._fanart_ql_var,
                     values=fanart_tiers, state="readonly",
                     width=18, font=("Helvetica", 10)).pack(side="left", padx=(8, 0))

        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(10, 4))

        # ── Legacy KB minimums (kept for additional safety net) ───────────────
        self._section(f, "Legacy File Size Minimums (KB)")
        self._note(f,
            "Secondary check — files below this size are flagged as errors.\n"
            "Set to 0 to rely on resolution tiers only.")

        def _sz_row(parent, label, varname, default):
            r = tk.Frame(parent, bg="#1e1e2e"); r.pack(anchor="w", padx=24, pady=2)
            tk.Label(r, text=label, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                     width=34, anchor="w").pack(side="left")
            v = tk.IntVar(value=self._s.get(varname, default))
            setattr(self, f"_{varname}_var", v)
            tk.Spinbox(r, from_=0, to=9999, textvariable=v, width=6,
                       font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                       buttonbackground="#45475a", relief="flat").pack(side="left")
            tk.Label(r, text=" KB   (0 = skip check)", font=("Helvetica", 9),
                     bg="#1e1e2e", fg="#6c7086").pack(side="left", padx=(6, 0))

        _sz_row(f, "poster.jpg minimum size:", "min_poster_kb", 100)
        _sz_row(f, "folder.jpg minimum size:", "min_folder_kb", 100)
        _sz_row(f, "fanart.jpg minimum size:", "min_fanart_kb", 200)

    def _update_proportion_text(self, *_):
        """Update the dynamic proportion description based on both toggles.
        ### NEW v0.12.0 — 4 combinations based on fanart_accept_168 and poster_accept_34 ###
        """
        accept_168 = (self._fanart_168_var.get() == "Yes")
        accept_34  = (getattr(self, "_poster_34_var", None) and
                      self._poster_34_var.get() == "Yes")

        if not accept_168 and not accept_34:
            text = (
                "Wrong proportions are flagged as warnings, not errors.\n"
                "Acceptable proportions are:\n"
                " - Poster/Folder: 2:3 (~0.67 ratio)\n"
                " - Fanart: 16:9 (~1.78 ratio)"
            )
        elif accept_168 and not accept_34:
            text = (
                "Wrong proportions are flagged as warnings, not errors.\n"
                "Acceptable proportions are:\n"
                " - Poster/Folder: 2:3 (~0.67 ratio)\n"
                " - Fanart: 16:9 (~1.78 ratio) and 16:8 (~1.50 ratio)"
            )
        elif not accept_168 and accept_34:
            text = (
                "Wrong proportions are flagged as warnings, not errors.\n"
                "Acceptable proportions are:\n"
                " - Poster/Folder: 2:3 (~0.67 ratio) and 3:4 (0.75 ratio)\n"
                " - Fanart: 16:9 (~1.78 ratio)"
            )
        else:  # both Yes
            text = (
                "Wrong proportions are flagged as warnings, not errors.\n"
                "Acceptable proportions are:\n"
                " - Poster/Folder: 2:3 (~0.67 ratio) and 3:4 (0.75 ratio)\n"
                " - Fanart: 16:9 (~1.78 ratio) and 16:8 (~1.50 ratio)"
            )
        self._prop_text_var.set(text)

    # ── Tab 6: Genres ─────────────────────────────────────────────────────────
    # ── Tab 10: Ratings ─────────────────────────────────────────────────────── ### NEW v0.15.0 ###
    def _build_ratings_tab(self, nb, label="Ratings"):           ### NEW v0.15.0 ###
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=label)   ### NEW v0.15.0 ###
                                                                  ### NEW v0.15.0 ###
        tk.Label(f, text="Ratings Synchronization Options",      ### NEW v0.15.0 ###
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa" ### NEW v0.15.0 ###
                 ).pack(anchor="w", padx=16, pady=(16, 6))       ### NEW v0.15.0 ###
                                                                  ### NEW v0.15.0 ###
        tk.Label(f, text="These settings control the default behaviour of the Ratings Sync popup.", ### NEW v0.15.0 ###
                 bg="#1e1e2e", fg="#a6adc8", font=("Helvetica", 9) ### NEW v0.15.0 ###
                 ).pack(anchor="w", padx=16, pady=(0, 12))       ### NEW v0.15.0 ###
                                                                  ### NEW v0.15.0 ###
        apply_val = self._s.get("rating_apply_all_movies",       ### NEW v0.15.0 ###
                                 self._defaults.get("rating_apply_all_movies", False)) ### NEW v0.15.0 ###
        self._rating_apply_all_var = tk.BooleanVar(value=apply_val) ### NEW v0.15.0 ###
        tk.Checkbutton(f, text="Apply this choice to all remaining movies", ### NEW v0.15.0 ###
                       variable=self._rating_apply_all_var,      ### NEW v0.15.0 ###
                       bg="#1e1e2e", fg="#cdd6f4", activebackground="#1e1e2e", ### NEW v0.15.0 ###
                       selectcolor="#313244", font=("Helvetica", 10) ### NEW v0.15.0 ###
                       ).pack(anchor="w", padx=16, pady=(0, 6))  ### NEW v0.15.0 ###
                                                                  ### NEW v0.15.0 ###
        votes_val = self._s.get("rating_use_more_votes",         ### NEW v0.15.0 ###
                                 self._defaults.get("rating_use_more_votes", False)) ### NEW v0.15.0 ###
        self._rating_use_more_votes_var = tk.BooleanVar(value=votes_val) ### NEW v0.15.0 ###
        tk.Checkbutton(f, text="Use the source with more votes", ### NEW v0.15.0 ###
                       variable=self._rating_use_more_votes_var, ### NEW v0.15.0 ###
                       bg="#1e1e2e", fg="#cdd6f4", activebackground="#1e1e2e", ### NEW v0.15.0 ###
                       selectcolor="#313244", font=("Helvetica", 10) ### NEW v0.15.0 ###
                       ).pack(anchor="w", padx=16, pady=(0, 6))  ### NEW v0.15.0 ###


    def _build_genres_tab(self, nb, label="Genres"):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=label)

        self._section(f, "Standard Genre List")
        self._note(f, "One genre per line. Based on TMDb's official genre list.\n"
                      "Add your own custom genres — they will be treated as valid.\n"
                      "Blank lines are removed automatically on save.")

        fr = tk.Frame(f, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(4, 4))
        self._genres_text = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4",
                                    font=("Consolas", 10), relief="flat", padx=8, pady=6,
                                    width=30)
        sb_g = ttk.Scrollbar(fr, orient="vertical", command=self._genres_text.yview)
        self._genres_text.configure(yscrollcommand=sb_g.set)
        self._genres_text.pack(side="left", fill="both", expand=True)
        sb_g.pack(side="right", fill="y")

        raw = self._s.get("genre_list", self._defaults.get("genre_list", ""))  ### FIX v0.15.0 ###
        cleaned = "\n".join(g for g in raw.splitlines() if g.strip())
        self._genres_text.insert("1.0", cleaned)

        br = tk.Frame(f, bg="#1e1e2e"); br.pack(fill="x", padx=16, pady=(0, 4))
        tk.Button(br, text="Reset to TMDb defaults", font=("Helvetica", 9),
                  bg="#45475a", fg="#f38ba8", relief="flat", cursor="hand2",
                  command=self._reset_genres).pack(side="left")

    def _reset_genres(self):
        self._genres_text.delete("1.0", "end")
        self._genres_text.insert("1.0", self._defaults.get("genre_list", ""))  ### FIX v0.15.0 ###

    # ── Tab 7: NFO-XML Tags ───────────────────────────────────────────────────

    def _build_tags_tab(self, nb, label="NFO / XML"):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=label)

        tk.Label(f, text="NFO ↔ XML Tag Comparison Pairs",
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(f, text="Format: NFO_tag  →  XML_tag  (one pair per line, tab or spaces separated)\n"
                 "Use dot notation for nested tags: fileinfo.streamdetails.video.width\n"
                 "Add optional tolerance% at end: fileinfo.streamdetails.video.durationinseconds  "
                 "MediaInfo.Video.DurationSeconds  Duration  5",
                 font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086",
                 justify="left").pack(anchor="w", padx=16, pady=(0, 8))

        fr = tk.Frame(f, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(0, 4))
        self._tags_text = tk.Text(fr, wrap="none", bg="#313244", fg="#cdd6f4",
                                  font=("Consolas", 9), relief="flat", padx=8, pady=6)
        sb_v = ttk.Scrollbar(fr, orient="vertical",   command=self._tags_text.yview)
        sb_h = ttk.Scrollbar(fr, orient="horizontal", command=self._tags_text.xview)
        self._tags_text.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        self._tags_text.grid(row=0, column=0, sticky="nsew")
        sb_v.grid(row=0, column=1, sticky="ns")
        sb_h.grid(row=1, column=0, sticky="ew")
        fr.rowconfigure(0, weight=1); fr.columnconfigure(0, weight=1)

        pairs = self._s.get("tag_pairs") or self._tag_pairs_default
        lines = []
        for nfo_p, xml_p, label, tol in pairs:
            lines.append(f"{nfo_p}\t{xml_p}\t{label}\t{tol}")
        self._tags_text.insert("1.0", "\n".join(lines))

        br = tk.Frame(f, bg="#1e1e2e"); br.pack(fill="x", padx=16, pady=(0, 4))
        tk.Button(br, text="Reset to defaults", font=("Helvetica", 9),
                  bg="#45475a", fg="#f38ba8", relief="flat", cursor="hand2",
                  command=self._reset_tags).pack(side="left")

    def _reset_tags(self):
        self._tags_text.delete("1.0", "end")
        lines = [f"{nfo_p}\t{xml_p}\t{label}\t{tol}"
                 for nfo_p, xml_p, label, tol in self._tag_pairs_default]
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

    # ── Tab 8: User Interface  (v0.12.0)  ─────────────────────────────────────

    def _build_ui_prefs_tab(self, nb, label="User Interface"):
        """User Interface preferences tab — v0.12.0 replacement."""  ### NEW v0.12.0 ###
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=label)

        tk.Label(f, text="User Interface Settings",
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16, 4))

        # ── Show image size? ──────────────────────────────────────────────────
        self._section(f, "Image Size Columns")
        self._note(f, "When Yes, a Size column (file size in KB) is shown alongside\n"
                      "each Quality column for poster, folder, and fanart.\n"
                      "(Note: merged columns in v0.12.0 — this setting is reserved.)")
        r1 = self._row(f)
        tk.Label(r1, text="Show image size?", font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=28, anchor="w").pack(side="left")
        self._show_image_size_var = tk.BooleanVar(value=self._s.get("show_image_size", False))
        for val, lbl in [(True, "Yes"), (False, "No")]:
            tk.Radiobutton(r1, text=lbl, variable=self._show_image_size_var, value=val,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(side="left", padx=(0, 12))

        # ── Enable compact mode? ──────────────────────────────────────────────
        self._section(f, "Compact Mode")
        self._note(f, "When Yes, reduces vertical spacing between rows in the main table.")
        r2 = self._row(f)
        tk.Label(r2, text="Enable compact mode?", font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=28, anchor="w").pack(side="left")
        self._compact_mode_var = tk.BooleanVar(value=self._s.get("compact_mode", False))
        for val, lbl in [(True, "Yes"), (False, "No")]:
            tk.Radiobutton(r2, text=lbl, variable=self._compact_mode_var, value=val,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(side="left", padx=(0, 12))

        # ── Enable dark theme? ────────────────────────────────────────────────
        self._section(f, "Dark Theme")
        self._note(f, "Toggle between dark and light UI theme.\n"
                      "(Full theme switching will be implemented in a future update.)")
        r3 = self._row(f)
        tk.Label(r3, text="Enable dark theme?", font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=28, anchor="w").pack(side="left")
        self._dark_theme_var = tk.BooleanVar(value=self._s.get("dark_theme", True))
        for val, lbl in [(True, "Yes"), (False, "No")]:
            tk.Radiobutton(r3, text=lbl, variable=self._dark_theme_var, value=val,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(side="left", padx=(0, 12))

        # ── Auto-fit column widths? ───────────────────────────────────────────
        self._section(f, "Auto-fit Columns")
        self._note(f, "When Yes, columns automatically resize to fit content on load.")
        r4 = self._row(f)
        tk.Label(r4, text="Auto-fit column widths?", font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=28, anchor="w").pack(side="left")
        self._auto_fit_var = tk.BooleanVar(value=self._s.get("auto_fit_columns", True))
        for val, lbl in [(True, "Yes"), (False, "No")]:
            tk.Radiobutton(r4, text=lbl, variable=self._auto_fit_var, value=val,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(side="left", padx=(0, 12))

        # ── Alternating rows (kept from v0.11) ────────────────────────────────
        self._section(f, "Table Appearance")
        self._note(f, "Alternating row colors make it easier to follow rows across wide tables.")
        r5 = self._row(f)
        self._alt_rows_var = tk.BooleanVar(value=self._s.get("alternating_rows", True))
        tk.Checkbutton(r5, text="Alternating row colors",
                       variable=self._alt_rows_var,
                       font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left")

        r6 = self._row(f)
        self._show_header_tips_var = tk.BooleanVar(value=self._s.get("show_header_tips", True))
        tk.Checkbutton(r6, text="Show column header tooltips",
                       variable=self._show_header_tips_var,
                       font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left")

    # ── Tab 10: Health Rules  (v0.18.2) ─────────────────────────────────────── ### ADDED_BY_CLAUDE_v18.2 ###

    def _build_health_rules_tab(self, nb, label="Health Rules"):
        """Configurable health rule engine tab."""
        from settings_model import DEFAULT_SETTINGS

        outer = tk.Frame(nb, bg="#1e1e2e"); nb.add(outer, text=label)
        canvas = tk.Canvas(outer, bg="#1e1e2e", highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        f = tk.Frame(canvas, bg="#1e1e2e")
        canvas.create_window((0, 0), window=f, anchor="nw")
        f.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))

        # Mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        hr_defaults = DEFAULT_SETTINGS.get("health_rules", {})
        hr_current  = self._s.get("health_rules", {})

        # Four variable dicts — written back in _save_close
        self._hr_vars     = {}   # BooleanVar
        self._hr_int_vars = {}   # IntVar
        self._hr_flt_vars = {}   # DoubleVar
        self._hr_str_vars = {}   # StringVar

        # ── Helper: section header ─────────────────────────────────────────────
        def _section(text):
            tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=12, pady=(12, 0))
            tk.Label(f, text=text, font=("Helvetica", 11, "bold"),
                     bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", padx=14, pady=(4, 2))

        # ── Helper: plain checkbox row ─────────────────────────────────────────
        def _check_row(key, label_text):
            val = hr_current.get(key, hr_defaults.get(key, True))
            v   = tk.BooleanVar(value=val)
            self._hr_vars[key] = v
            tk.Checkbutton(f, text=label_text, variable=v,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(anchor="w", padx=22, pady=1)
            return v

        # ── Helper: checkbox + inline combobox ────────────────────────────────
        def _check_combo_row(bool_key, str_key, label_text, values, default_str,
                             combo_width=12):
            row = tk.Frame(f, bg="#1e1e2e"); row.pack(anchor="w", padx=22, pady=1)
            b_val = hr_current.get(bool_key, hr_defaults.get(bool_key, True))
            bv    = tk.BooleanVar(value=b_val)
            self._hr_vars[bool_key] = bv
            s_val = hr_current.get(str_key, hr_defaults.get(str_key, default_str))
            sv    = tk.StringVar(value=s_val)
            self._hr_str_vars[str_key] = sv
            cb = tk.Checkbutton(row, text=label_text, variable=bv,
                                font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                                selectcolor="#313244", activebackground="#1e1e2e",
                                activeforeground="#cdd6f4")
            cb.pack(side="left")
            combo = ttk.Combobox(row, textvariable=sv, values=values,
                                 state="readonly" if b_val else "disabled",
                                 width=combo_width, font=("Helvetica", 10))
            combo.pack(side="left", padx=(6, 0))

            def _update_combo_state(*_):
                combo.configure(state="readonly" if bv.get() else "disabled")
            bv.trace_add("write", _update_combo_state)
            return bv, sv

        # ── Helper: checkbox + spinbox (int) ──────────────────────────────────
        def _check_spin_int_row(bool_key, int_key, label_text, default_int,
                                from_, to_, width=4):
            row = tk.Frame(f, bg="#1e1e2e"); row.pack(anchor="w", padx=22, pady=1)
            b_val = hr_current.get(bool_key, hr_defaults.get(bool_key, True))
            bv    = tk.BooleanVar(value=b_val)
            self._hr_vars[bool_key] = bv
            i_val = hr_current.get(int_key, hr_defaults.get(int_key, default_int))
            iv    = tk.IntVar(value=i_val)
            self._hr_int_vars[int_key] = iv
            cb = tk.Checkbutton(row, text=label_text, variable=bv,
                                font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                                selectcolor="#313244", activebackground="#1e1e2e",
                                activeforeground="#cdd6f4")
            cb.pack(side="left")
            spin = tk.Spinbox(row, from_=from_, to=to_, textvariable=iv, width=width,
                              font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                              buttonbackground="#45475a", relief="flat")
            spin.pack(side="left", padx=(6, 0))

            def _upd(*_):
                spin.configure(state="normal" if bv.get() else "disabled")
            bv.trace_add("write", _upd)
            return bv, iv

        # ── Helper: checkbox + spinbox (float) ────────────────────────────────
        def _check_spin_flt_row(bool_key, flt_key, label_text, default_flt,
                                from_, to_, incr=0.1, width=5):
            row = tk.Frame(f, bg="#1e1e2e"); row.pack(anchor="w", padx=22, pady=1)
            b_val = hr_current.get(bool_key, hr_defaults.get(bool_key, True))
            bv    = tk.BooleanVar(value=b_val)
            self._hr_vars[bool_key] = bv
            f_val = hr_current.get(flt_key, hr_defaults.get(flt_key, default_flt))
            fv    = tk.DoubleVar(value=f_val)
            self._hr_flt_vars[flt_key] = fv
            cb = tk.Checkbutton(row, text=label_text, variable=bv,
                                font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                                selectcolor="#313244", activebackground="#1e1e2e",
                                activeforeground="#cdd6f4")
            cb.pack(side="left")
            spin = tk.Spinbox(row, from_=from_, to=to_, increment=incr,
                              textvariable=fv, width=width, format="%.1f",
                              font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                              buttonbackground="#45475a", relief="flat")
            spin.pack(side="left", padx=(6, 0))

            def _upd(*_):
                spin.configure(state="normal" if bv.get() else "disabled")
            bv.trace_add("write", _upd)
            return bv, fv

        # ── Helper: checkbox + language combobox ──────────────────────────────
        def _check_lang_row(bool_key, str_key, label_text, lang_list, default_code):
            row = tk.Frame(f, bg="#1e1e2e"); row.pack(anchor="w", padx=22, pady=1)
            b_val = hr_current.get(bool_key, hr_defaults.get(bool_key, True))
            bv    = tk.BooleanVar(value=b_val)
            self._hr_vars[bool_key] = bv
            s_val = hr_current.get(str_key, hr_defaults.get(str_key, default_code))
            sv    = tk.StringVar(value=s_val)
            self._hr_str_vars[str_key] = sv
            cb = tk.Checkbutton(row, text=label_text, variable=bv,
                                font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                                selectcolor="#313244", activebackground="#1e1e2e",
                                activeforeground="#cdd6f4")
            cb.pack(side="left")
            codes   = [code for code, _ in lang_list]
            names   = {code: name for code, name in lang_list}
            combo   = ttk.Combobox(row, textvariable=sv, values=codes,
                                   state="readonly" if b_val else "disabled",
                                   width=6, font=("Helvetica", 10))
            combo.pack(side="left", padx=(6, 0))
            name_lbl = tk.Label(row, text=names.get(s_val, ""),
                                font=("Helvetica", 10), bg="#1e1e2e", fg="#a6adc8")
            name_lbl.pack(side="left", padx=(6, 0))

            def _upd_combo(*_):
                combo.configure(state="readonly" if bv.get() else "disabled")
            def _upd_name(*_):
                name_lbl.configure(text=names.get(sv.get(), ""))
            bv.trace_add("write", _upd_combo)
            sv.trace_add("write", _upd_name)
            return bv, sv

        # ── Intro and reset button ─────────────────────────────────────────────
        tk.Label(f, text="Health Rules control which conditions affect each movie's\n"
                         "health status. Rules that are OFF are ignored and treated as OK.",
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 justify="left").pack(anchor="w", padx=14, pady=(14, 4))

        def _reset_defaults():
            hrd = hr_defaults
            for k, v in self._hr_vars.items():
                v.set(hrd.get(k, True))
            for k, v in self._hr_int_vars.items():
                v.set(hrd.get(k, 0))
            for k, v in self._hr_flt_vars.items():
                v.set(hrd.get(k, 0.0))
            for k, v in self._hr_str_vars.items():
                v.set(hrd.get(k, ""))

        tk.Button(f, text="  Reset to defaults  ",
                  font=("Helvetica", 9, "bold"), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=_reset_defaults).pack(anchor="w", padx=14, pady=(0, 8))

        # ── GROUP A: Critical Error Rules ──────────────────────────────────────
        _section("Critical Error Rules — mark movie as ERROR (red)")

        _check_row("missing_video_file", "Missing video file")
        _check_row("corrupt_nfo",        "Corrupt NFO file (XML parse error)")
        _check_row("missing_nfo",        "Missing NFO file")
        _check_row("corrupt_xml",        "Corrupt XML file (XML parse error)")
        _check_row("missing_xml",        "Missing XML file")
        _check_row("corrupt_poster",     "Corrupt poster image")
        _check_row("corrupt_fanart",     "Corrupt fanart image")
        _check_row("corrupt_folder",     "Corrupt folder image")
        _check_row("missing_imdb_id",    "Missing IMDB ID")
        _check_row("corrupt_imdb_id",    "IMDB ID conflict between NFO and XML")
        _check_row("missing_tmdb_id",    "Missing TMDb ID")
        _check_row("corrupt_tmdb_id",    "TMDb ID conflict between NFO and XML")
        _check_row("rating_conflict",    "Rating conflict between NFO and XML")
        _check_row("votes_conflict",     "Votes conflict between NFO and XML")
        _check_row("genre_missing",      "Missing genre information")
        _check_row("missing_movie_year", "Missing movie year in NFO/XML")
        _check_row("no_audio_tracks",    "No audio tracks detected")
        _check_combo_row("video_quality_minimum", "video_quality_minimum_level",
                         "Video quality below minimum:",
                         VIDEO_QUALITY_LEVELS, "720p", combo_width=12)

        # ── GROUP B: Warning Rules ─────────────────────────────────────────────
        _section("Warning Rules — mark movie as WARNING (yellow)  (default: OFF noted)")

        _check_row("multiple_video_files",   "Multiple video files in same folder  (default: OFF)")
        _check_row("missing_poster",         "Missing poster")
        _check_row("missing_fanart",         "Missing fanart")
        _check_row("missing_folder",         "Missing folder image")
        _check_row("poster_proportion",      "Poster has wrong proportions")
        _check_row("fanart_proportion",      "Fanart has wrong proportions")
        _check_row("folder_proportion",      "Folder image has wrong proportions")
        _check_combo_row("poster_folder_quality_minimum", "poster_folder_quality_level",
                         "Poster/folder quality below minimum:",
                         POSTER_QUALITY_LEVELS, "1080p", combo_width=10)
        _check_combo_row("fanart_quality_minimum", "fanart_quality_level_minimum",
                         "Fanart quality below minimum:",
                         FANART_QUALITY_LEVELS, "1080p", combo_width=10)
        _check_row("poster_folder_identical",  "Poster and folder image are different (different sizes)")
        _check_spin_int_row("insufficient_backdrops", "backdrop_min_count",
                            "Backdrop images below minimum:", 5, 1, 50, width=4)
        _check_spin_int_row("backdrop_too_small", "backdrop_min_avg_kb",
                            "Backdrop images suspiciously small (avg KB below):", 20, 1, 500, width=5)
        _check_row("missing_rating",     "Missing rating")
        _check_row("rating_warning",     "Rating present in one file only")
        _check_spin_flt_row("suspicious_rating", "suspicious_rating_threshold",
                            "Suspicious rating value (below):", 1.0, 0.0, 10.0, incr=0.1, width=5)
        _check_row("genre_warning",          "Genre issues detected (non-standard genres)")
        _check_row("missing_votes",          "Missing votes count")
        _check_row("votes_warning",          "Votes present in one file only")
        _check_row("lang_not_ok",            "Target language not found (Lang OK? column)")
        _check_row("missing_language_field", "Language field missing in XML")
        _check_row("nfo_xml_too_large",      "NFO or XML file too large (uses max KB from Improvements tab)")
        _check_lang_row("required_audio_language", "required_audio_language_code",
                        "Required audio language missing:", AUDIO_LANGUAGES, "ENG")
        _check_lang_row("required_subtitle_language", "required_subtitle_language_code",
                        "Required subtitle language missing:", SUBTITLE_LANGUAGES, "POR")
        _check_row("missing_movie_title",    "Missing movie title in NFO/XML")
        _check_row("title_mismatch",         "Title mismatch between NFO and XML")
        _check_row("folder_name_mismatch",   "Folder name doesn't match movie title  (default: OFF)")

        # bottom padding
        tk.Frame(f, bg="#1e1e2e", height=16).pack()

    # ── Tab 11: Backup  (v0.12.0)  ───────────────────────────────────────────── ### MODIFIED_BY_CLAUDE_v18.2 — was Tab 9 ###

    def _build_backup_tab(self, nb, label="Backup"):
        """Backup folder maintenance tab.                  ### NEW v0.12.0 ###
        ### NEW v0.14.0 — reads backup_root from self._ctx ###
        """
        import os, shutil as _shutil

        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=label)

        tk.Label(f, text="Backup Folder Maintenance",
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16, 4))

        self._section(f, "Automatic Cleanup")
        self._note(f,
            "When the total size of the backup folder exceeds the limit,\n"
            "the oldest backup subfolders (backup_*) are deleted automatically.\n"
            "The currently active backup folder is never deleted.\n"
            "Set to 0 to disable automatic cleanup.")

        r1 = self._row(f)
        tk.Label(r1, text="Maximum backup folder size (MB):",
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=34, anchor="w").pack(side="left")
        _s = self._ctx.settings if self._ctx else self._s
        self._max_backup_mb_var = tk.IntVar(value=_s.get("max_backup_size_mb", 500))
        tk.Spinbox(r1, from_=0, to=99999, textvariable=self._max_backup_mb_var, width=8,
                   font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                   buttonbackground="#45475a", relief="flat").pack(side="left")
        tk.Label(r1, text=" MB   (0 = disabled)", font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#6c7086").pack(side="left", padx=(6, 0))

        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(14, 8))

        self._section(f, "Manual Cleanup")
        self._note(f, "Delete ALL backup subfolders (backup_*) inside the backup folder.\n"
                      "The backup folder itself is kept. This action cannot be undone.")

        r2 = self._row(f)
        tk.Button(r2, text="  Delete all backup folders  ",
                  font=("Helvetica", 10, "bold"),
                  bg="#f38ba8", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._delete_all_backups).pack(side="left")

        # Show current backup folder path for reference
        backup_path = (self._ctx.backup_root if self._ctx else _BACKUP_ROOT_PATH) or ""
        if backup_path:
            tk.Label(f, text=f"Backup folder: {backup_path}",
                     font=("Consolas", 8), bg="#1e1e2e", fg="#45475a",
                     justify="left").pack(anchor="w", padx=16, pady=(12, 0))

    def _delete_all_backups(self):
        """Delete all backup_* subfolders inside the backup root.
        ### NEW v0.14.0 — reads backup_root from self._ctx ###
        ### MODIFIED_BY_CLAUDE_v18 — shutil.rmtree moved off main thread via run_async ###
        """
        import os, shutil as _shutil
        from tkinter import messagebox as _mb
        backup_root = (self._ctx.backup_root if self._ctx else _BACKUP_ROOT_PATH) or ""
        _log = (self._ctx.logger if self._ctx else _logger)
        if not backup_root or not os.path.isdir(backup_root):
            _mb.showinfo("No Backups", "Backup folder not found or empty.", parent=self)
            return
        if not _mb.askyesno("Delete All Backups",
                "Are you sure you want to delete ALL backup folders?\n"
                "This action cannot be undone.",
                icon="warning", parent=self):
            return

        def _do_delete():
            deleted = 0
            errors = []
            try:
                for entry in os.scandir(backup_root):
                    if entry.is_dir() and entry.name.startswith("backup_"):
                        try:
                            _shutil.rmtree(entry.path)
                            deleted += 1
                            if _log:
                                _log.info(f"Manual backup cleanup: removed {entry.path}")
                        except Exception as e:
                            errors.append(str(e))
            except Exception as e:
                errors.append(str(e))
            return (deleted, errors)

        def _done(result):
            deleted, errors = result
            msg = f"Deleted {deleted} backup folder(s)."
            if errors:
                msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:3])
            _mb.showinfo("Backups Deleted", msg, parent=self)

        run_async(_do_delete, callback=_done, root=self)

    # ── Rescan-offer helpers  (v0.11.1)                      ### NEW v0.11.1 ###
    # After the user saves settings in specific tabs, the application
    # offers to re-run a scan so the table reflects the new rules.
    # Tabs that trigger a rescan offer:
    #   • Image Sizes   (tab 5) — quality tiers, proportion rules, KB limits
    #   • Language OK?  (tab 3) — lang target changes the Lang OK? column
    #   • Genres        (tab 6) — genre list changes genre status
    #   • NFO-XML Tags  (tab 7) — tag pairs used by Improvements

    @staticmethod
    def _normalize_tag_pairs(value):
        """Convert tag_pairs (whatever shape it has in settings vs parser
        output) into a canonical list-of-4-tuples for comparison.

        Settings load may store tag_pairs as None, [], or a list of
        [nfo, xml, label, tol] lists.  _parse_tags_text() returns a list of
        (nfo, xml, label, tol) tuples, or None when the text is empty.
        Both must compare equal when semantically identical.

        ### NEW v0.13.1 — fixes false-positive in _rescan_changed ###
        """
        if not value:
            return []
        out = []
        try:
            for item in value:
                if not item or len(item) < 2:
                    continue
                nfo  = str(item[0]).strip()
                xml  = str(item[1]).strip()
                lbl  = str(item[2]).strip() if len(item) > 2 else nfo
                try:
                    tol = int(item[3]) if len(item) > 3 else 0
                except (TypeError, ValueError):
                    tol = 0
                out.append((nfo, xml, lbl, tol))
        except TypeError:
            return []
        return out

    def _take_rescan_snapshot(self):
        """
        Capture the current values of all rescan-relevant settings.
        Returns a structured dict.  Called once on dialog open; compared on save.

        ### NEW v0.14.0 — structured snapshot (image_sizes sub-dict, genres list,
        tag_pairs list-of-tuples) replacing flat key layout of v0.13.x. ###

        Note: 'default_browser' is intentionally NOT captured — changing
        the browser never requires a rescan (v0.13.1 behaviour preserved).
        """
        ctx = self._ctx
        s   = ctx.settings if ctx else self._s
        tag_src = s.get("tag_pairs") or (ctx.tag_pairs if ctx else self._tag_pairs_default)
        return {
            # Structured sub-dict: all image quality settings together
            "image_sizes": {
                "poster_quality_level": s.get("poster_quality_level", "1080p"),
                "folder_quality_level": s.get("folder_quality_level", "1080p"),
                "fanart_quality_level": s.get("fanart_quality_level", "1080p"),
                "fanart_accept_168":    s.get("fanart_accept_168", False),
                "poster_accept_34":     s.get("poster_accept_34",  False),
                "min_poster_kb":        s.get("min_poster_kb",     100),
                "min_folder_kb":        s.get("min_folder_kb",     100),
                "min_fanart_kb":        s.get("min_fanart_kb",     200),
            },
            # Scalar: language code
            "language": s.get("lang_ok_code", "PT"),
            # List of genre strings (normalised — no blank lines)
            "genres":   [g.strip() for g in
                         s.get("genre_list", "").splitlines() if g.strip()],
            # List of 4-tuples: tag comparison pairs (normalised)
            "tag_pairs": self._normalize_tag_pairs(tag_src),
            # v0.18.2 — health rules (full deep copy)          ### ADDED_BY_CLAUDE_v18.2 ###
            "health_rules": copy.deepcopy(s.get("health_rules", {})),
        }

    def _rescan_changed(self):
        """
        Compare current widget values against the snapshot taken on open.
        Returns a dict:
            {
              "image_sizes": bool,
              "language":    bool,
              "genres":      bool,
              "tags":        bool,
              "any":         bool,
            }
        ### NEW v0.14.0 — reads from structured snapshot sub-dicts ###
        """
        snap = self._rescan_snapshot
        changed = {}

        # Image Sizes — compare against snapshot["image_sizes"] sub-dict
        img_snap = snap.get("image_sizes", {})
        img = False
        if hasattr(self, "_poster_ql_var"):
            img |= self._poster_ql_var.get() != img_snap.get("poster_quality_level", "1080p")
        if hasattr(self, "_folder_ql_var"):
            img |= self._folder_ql_var.get() != img_snap.get("folder_quality_level", "1080p")
        if hasattr(self, "_fanart_ql_var"):
            img |= self._fanart_ql_var.get() != img_snap.get("fanart_quality_level", "1080p")
        if hasattr(self, "_fanart_168_var"):
            img |= (self._fanart_168_var.get() == "Yes") != img_snap.get("fanart_accept_168", False)
        if hasattr(self, "_poster_34_var"):
            img |= (self._poster_34_var.get() == "Yes") != img_snap.get("poster_accept_34", False)
        if hasattr(self, "_min_poster_kb_var"):
            img |= self._min_poster_kb_var.get() != img_snap.get("min_poster_kb", 100)
        if hasattr(self, "_min_folder_kb_var"):
            img |= self._min_folder_kb_var.get() != img_snap.get("min_folder_kb", 100)
        if hasattr(self, "_min_fanart_kb_var"):
            img |= self._min_fanart_kb_var.get() != img_snap.get("min_fanart_kb", 200)
        changed["image_sizes"] = img

        # Language OK?
        lang = False
        if hasattr(self, "_lang_var"):
            lang |= self._lang_var.get().upper() != snap.get("language", "PT").upper()
        changed["language"] = lang

        # Genres — compare as sorted lists of stripped strings
        genres = False
        if hasattr(self, "_genres_text"):
            raw = self._genres_text.get("1.0", "end")
            current_genres = [g.strip() for g in raw.splitlines() if g.strip()]
            genres |= current_genres != snap.get("genres", [])
        changed["genres"] = genres

        # Tags — compare normalised to snapshot
        tags = False
        if hasattr(self, "_tags_text"):
            try:
                current_tags = self._normalize_tag_pairs(self._parse_tags_text())
                tags |= current_tags != snap.get("tag_pairs", [])
            except Exception:
                pass
        changed["tags"] = tags

        # v0.18.2 — Health Rules                              ### ADDED_BY_CLAUDE_v18.2 ###
        hr_changed = False
        if hasattr(self, "_hr_vars"):
            snap_hr = snap.get("health_rules", {})
            curr_hr = {}
            for k, v in self._hr_vars.items():      curr_hr[k] = v.get()
            for k, v in self._hr_int_vars.items():  curr_hr[k] = v.get()
            for k, v in self._hr_flt_vars.items():  curr_hr[k] = round(v.get(), 2)
            for k, v in self._hr_str_vars.items():  curr_hr[k] = v.get()
            hr_changed = (curr_hr != snap_hr)
        changed["health_rules"] = hr_changed

        changed["any"] = any([img, lang, genres, tags, hr_changed])
        return changed

    def _offer_rescan(self, parent_app):
        """
        Show a non-blocking dialog offering to update the current scan.
        ### NEW v0.13.0 ###
        - Centered relative to the parent application window.
        - Non-blocking: uses WM_DELETE_WINDOW + button callbacks; no wait_window().
        - Buttons: Update Scan (no FFprobe) | Update Scan (with FFprobe) | Skip.
        """
        if not parent_app or not hasattr(parent_app, "_results") or not parent_app._results:
            return

        dlg = tk.Toplevel(parent_app)
        dlg.title("Update Scan?")
        dlg.configure(bg="#1e1e2e")
        dlg.transient(parent_app)
        dlg.grab_set()
        dlg.resizable(False, False)

        # ── Content ───────────────────────────────────────────────────────────
        outer = tk.Frame(dlg, bg="#1e1e2e")
        outer.pack(fill="both", expand=True, padx=20, pady=(20, 12))

        tk.Label(outer,
                 text="Settings that affect scan results have changed.\n"
                      "Would you like to update the current scan?",
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 justify="center").pack(pady=(0, 16))

        bf = tk.Frame(outer, bg="#1e1e2e"); bf.pack()

        def _choose(val):
            dlg.grab_release()
            dlg.destroy()
            if val == "no_ff":
                if hasattr(parent_app, "_update_scan_no_ff"):
                    parent_app._update_scan_no_ff()
                elif hasattr(parent_app, "_update_scan"):
                    parent_app._update_scan()
            elif val == "with_ff":
                if hasattr(parent_app, "_update_scan_with_ff"):
                    parent_app._update_scan_with_ff()
                elif hasattr(parent_app, "_scan"):
                    parent_app._scan()

        tk.Button(bf, text="  Update Scan (no FFprobe)  ",
                  font=("Helvetica", 10, "bold"), bg="#89b4fa", fg="#1e1e2e",
                  relief="flat", cursor="hand2",
                  command=lambda: _choose("no_ff")).pack(side="left", padx=(0, 6))
        tk.Button(bf, text="  Update Scan (with FFprobe)  ",
                  font=("Helvetica", 10, "bold"), bg="#a6e3a1", fg="#1e1e2e",
                  relief="flat", cursor="hand2",
                  command=lambda: _choose("with_ff")).pack(side="left", padx=(0, 6))
        tk.Button(bf, text="  Skip  ",
                  font=("Helvetica", 10, "bold"), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: _choose("skip")).pack(side="left")

        dlg.protocol("WM_DELETE_WINDOW", lambda: _choose("skip"))

        # ── Center on parent window ───────────────────────────────────────────
        dlg.update_idletasks()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        try:
            px = parent_app.winfo_x()
            py = parent_app.winfo_y()
            pw = parent_app.winfo_width()
            ph = parent_app.winfo_height()
            if pw > 0 and ph > 0:
                cx = px + (pw - dw) // 2
                cy = py + (ph - dh) // 2
            else:
                raise ValueError("parent not mapped")
        except Exception:
            # Fall back to screen center
            cx = (dlg.winfo_screenwidth()  - dw) // 2
            cy = (dlg.winfo_screenheight() - dh) // 2
        # Clamp to screen bounds
        cx = max(0, cx); cy = max(0, cy)
        dlg.geometry(f"{dw}x{dh}+{cx}+{cy}")

    def _offer_health_update(self, parent_app):                  ### ADDED_BY_CLAUDE_v18.2 ###
        """
        Show a non-blocking dialog offering an in-memory health recalculation.
        Modelled exactly on _offer_rescan — no wait_window(), non-blocking.
        """
        if not parent_app or not getattr(parent_app, "_results", None):
            return

        dlg = tk.Toplevel(parent_app)
        dlg.title("Update Health Status?")
        dlg.configure(bg="#1e1e2e")
        dlg.transient(parent_app)
        dlg.grab_set()
        dlg.resizable(False, False)

        outer = tk.Frame(dlg, bg="#1e1e2e")
        outer.pack(fill="both", expand=True, padx=20, pady=(20, 12))

        tk.Label(outer,
                 text="Health Rules have changed.\n\n"
                      "Would you like to update the health status of all\n"
                      "loaded movies using the new rules?\n\n"
                      "This does not require a re-scan. It uses the\n"
                      "existing scan data already in memory.",
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 justify="center").pack(pady=(0, 16))

        bf = tk.Frame(outer, bg="#1e1e2e"); bf.pack()

        def _choose(val):
            dlg.grab_release()
            dlg.destroy()
            if val == "update" and hasattr(parent_app, "_apply_health_rules_inplace"):
                parent_app._apply_health_rules_inplace()

        tk.Button(bf, text="  Update Health Status  ",
                  font=("Helvetica", 10, "bold"), bg="#a6e3a1", fg="#1e1e2e",
                  relief="flat", cursor="hand2",
                  command=lambda: _choose("update")).pack(side="left", padx=(0, 6))
        tk.Button(bf, text="  Skip  ",
                  font=("Helvetica", 10, "bold"), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: _choose("skip")).pack(side="left")

        dlg.protocol("WM_DELETE_WINDOW", lambda: _choose("skip"))

        # Center on parent window (same pattern as _offer_rescan)
        dlg.update_idletasks()
        dw = dlg.winfo_reqwidth(); dh = dlg.winfo_reqheight()
        try:
            px = parent_app.winfo_x(); py = parent_app.winfo_y()
            pw = parent_app.winfo_width(); ph = parent_app.winfo_height()
            if pw > 0 and ph > 0:
                cx = px + (pw - dw) // 2; cy = py + (ph - dh) // 2
            else:
                raise ValueError("parent not mapped")
        except Exception:
            cx = (dlg.winfo_screenwidth()  - dw) // 2
            cy = (dlg.winfo_screenheight() - dh) // 2
        cx = max(0, cx); cy = max(0, cy)
        dlg.geometry(f"{dw}x{dh}+{cx}+{cy}")

    # ── Save & Close ──────────────────────────────────────────────────────────

    def _save_close(self):
        """
        ### NEW v0.13.0 — fully non-blocking save pipeline ###
        ### NEW v0.14.0 — reads from self._ctx instead of module globals ###
        1. Gather all widget values
        2. Write into the shared settings dict (via self._ctx.settings)
        3. Detect which rescan-relevant tabs changed
        4. Refresh FFmpeg paths
        5. Persist to disk via self._ctx.save_settings
        6. Notify parent via _on_settings_changed callback
        7. Destroy dialog
        8. Schedule _offer_rescan via after(0) — non-blocking, no wait_window()
        """
        ctx = self._ctx
        _s  = ctx.settings if ctx else self._s   # live settings dict

        changed = self._rescan_changed()

        try:
            _s["text_editor"]      = self._editor_var.get().strip()
            _s["ffmpeg_path"]      = self._ffmpeg_var.get().strip()
            _s["scraper_path"]     = self._scraper_var.get().strip()
            _s["tmdb_api_key"]     = self._tmdb_var.get().strip()
            _s["omdb_api_key"]     = self._omdb_var.get().strip()
            _s["default_browser"]  = self._browser_var.get().strip()
            _s["lang_ok_code"]     = self._lang_var.get().upper()
            _s["improve_checks"]   = {k: v.get() for k, v in self._ic_vars.items()}
            _s["max_nfo_kb"]       = self._max_nfo_kb_var.get()
            _s["max_xml_kb"]       = self._max_xml_kb_var.get()
            # _s["min_backdrops"] intentionally not written — deprecated in v0.18.2, now in health_rules ### MODIFIED_BY_CLAUDE_v18.2 ###
            _s["min_poster_kb"]    = self._min_poster_kb_var.get()
            _s["min_folder_kb"]    = self._min_folder_kb_var.get()
            _s["min_fanart_kb"]    = self._min_fanart_kb_var.get()
            _s["backdrop_count"]   = self._backdrop_count_var.get()
            _s["metadata_source"]  = self._meta_src_var.get()
            if hasattr(self, "_poster_ql_var"):
                _s["poster_quality_level"] = self._poster_ql_var.get()
            if hasattr(self, "_folder_ql_var"):
                _s["folder_quality_level"] = self._folder_ql_var.get()
            if hasattr(self, "_fanart_ql_var"):
                _s["fanart_quality_level"] = self._fanart_ql_var.get()
            if hasattr(self, "_fanart_168_var"):
                _s["fanart_accept_168"] = (self._fanart_168_var.get() == "Yes")
            if hasattr(self, "_poster_34_var"):
                _s["poster_accept_34"] = (self._poster_34_var.get() == "Yes")
            if hasattr(self, "_show_header_tips_var"):
                _s["show_header_tips"] = self._show_header_tips_var.get()
            if hasattr(self, "_alt_rows_var"):
                _s["alternating_rows"] = self._alt_rows_var.get()
            if hasattr(self, "_show_image_size_var"):
                _s["show_image_size"] = self._show_image_size_var.get()
            if hasattr(self, "_compact_mode_var"):
                _s["compact_mode"] = self._compact_mode_var.get()
            if hasattr(self, "_dark_theme_var"):
                _s["dark_theme"] = self._dark_theme_var.get()
            if hasattr(self, "_auto_fit_var"):
                _s["auto_fit_columns"] = self._auto_fit_var.get()
            if hasattr(self, "_max_backup_mb_var"):
                _s["max_backup_size_mb"] = self._max_backup_mb_var.get()
            if hasattr(self, "_rating_apply_all_var"):                      ### NEW v0.15.0 ###
                _s["rating_apply_all_movies"] = self._rating_apply_all_var.get()  ### NEW v0.15.0 ###
            if hasattr(self, "_rating_use_more_votes_var"):                 ### NEW v0.15.0 ###
                _s["rating_use_more_votes"] = self._rating_use_more_votes_var.get()  ### NEW v0.15.0 ###

            # v0.18.2 — write back health rule variables         ### ADDED_BY_CLAUDE_v18.2 ###
            if hasattr(self, "_hr_vars"):
                hr = _s.setdefault("health_rules", {})
                for k, v in self._hr_vars.items():      hr[k] = v.get()
                for k, v in self._hr_int_vars.items():  hr[k] = v.get()
                for k, v in self._hr_flt_vars.items():  hr[k] = round(v.get(), 2)
                for k, v in self._hr_str_vars.items():  hr[k] = v.get()

            raw_genres = self._genres_text.get("1.0", "end")
            _s["genre_list"] = "\n".join(
                g.strip() for g in raw_genres.splitlines() if g.strip())

            parsed_tags = self._parse_tags_text()
            _s["tag_pairs"] = parsed_tags

            if ctx and ctx.refresh_ffmpeg:
                ctx.refresh_ffmpeg()
            elif _refresh_ffmpeg_paths:        # shim fallback
                _refresh_ffmpeg_paths()

            if ctx and ctx.save_settings:
                ctx.save_settings(_s)
            elif _save_settings_fn:            # shim fallback
                _save_settings_fn(_s)

            _log = (ctx.logger if ctx else _logger)
            if _log:
                _log.info("Settings saved")

        except Exception as e:
            _log = (ctx.logger if ctx else _logger)
            if _log:
                _log.error(f"Settings save error: {e}")
            messagebox.showerror("Save error", str(e), parent=self)
            return

        parent_app = self._parent if hasattr(self, "_parent") else None

        ### NEW v0.13.0 — destroy dialog FIRST, then schedule refresh ###
        self.destroy()

        if parent_app and hasattr(parent_app, "_on_settings_changed"):
            parent_app.after(0, parent_app._on_settings_changed)

        # v0.18.2 — two-track post-save scheduling              ### MODIFIED_BY_CLAUDE_v18.2 ###
        # Track 1: health-rules-only → offer in-memory recalculation, no re-scan
        if changed.get("health_rules") and parent_app and getattr(parent_app, "_results", None):
            parent_app.after(0, lambda: self._offer_health_update(parent_app))

        # Track 2: scan-relevant settings → offer re-scan
        _scan_relevant = any([
            changed.get("image_sizes"),
            changed.get("language"),
            changed.get("genres"),
            changed.get("tags"),
        ])
        if _scan_relevant and parent_app:
            parent_app.after(0, lambda: self._offer_rescan(parent_app))
        elif not _scan_relevant and not changed.get("health_rules"):
            _log = (ctx.logger if ctx else _logger)
            if _log:
                _log.info("Settings saved; no rescan-relevant changes — no prompt offered.")
