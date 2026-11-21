# =============================================================================
# settings_dialog.py
# Metadata & MediaClinic — Settings UI Module
# Version: 0.19.3                                              ### MODIFIED v0.19.3 ###
# v0.18.4 — Tools tab: Parallel Scanning section (scan_workers / ffprobe_workers);
#            Health Rules: duplicate_movie rule.
#            Fix: Save/Cancel bar packed at the bottom FIRST so it can never be
#            pushed off-screen by a tall tab (Tools grew past 660 px); tall tabs
#            scroll (_scrollable_tab); numeric fields tolerate blank spinboxes
#            (_num); 'Save & Apply' recomputes health automatically.
# v0.18.3 — Health Rules tab: scroll-wheel binding scoped to the tab (no global
#            leak after the dialog closes); new imdb/tmdb_id_partial rules;
#            rating/votes rule labels corrected; legacy quality map imported
#            from settings_controller (single copy).
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
# It must reside in the same folder as the main mediaclinic script.
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
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
from settings_context import SettingsContext, run_async   # NEW v0.14.0
import mc_i18n as _i18n                                     ### NEW v0.20.0 UI1a ###
from settings_model import (                                         ### ADDED_BY_CLAUDE_v18.2 ###
    VIDEO_QUALITY_LEVELS, POSTER_QUALITY_LEVELS, FANART_QUALITY_LEVELS,
    AUDIO_LANGUAGES, SUBTITLE_LANGUAGES,
    api_failure_text, classify_http_status, classify_network_reason,   # v0.19.1 B22
)


FANARTTV_KEY_URL = "https://fanart.tv/get-an-api-key/"           ### NEW v0.19.1 I10 ###


def _validate_failure_text(service_label, kind, other=""):        ### NEW v0.19.1 B22 ###
    """'✗ <message> <advice>' — the same texts the main window uses."""
    m, a = api_failure_text(service_label, kind, other)
    return f"✗ {m} {a}"


# ── Legacy quality tier name migration (v0.16.1) ─────────────────────────────
from settings_controller import _LEGACY_QUALITY_MAP                 ### MODIFIED v0.18.3 — single copy ###
from settings_controller import BACKUP_PROTECT_DAYS                 ### NEW v0.19.4 B75 ###


USER_AGENT = "MediaClinic"                                          ### NEW v0.19.4 B96d — set by the app to its own "MediaClinic/<version>" ###
_KEY_RE96 = re.compile(r"((?:api_?key|client_key)=)[^&\s\"'<>]+", re.IGNORECASE)   # I2's redaction rule


def redact_key_text(text, key=""):                                  ### NEW v0.19.4 B96d ###
    """A Validate message with the key hidden: api_key=… → api_key=***, and
    the key itself anywhere in the text."""
    text = _KEY_RE96.sub(r"\1***", str(text))
    return text.replace(key, "***") if key and len(key) >= 4 else text


def modal(dlg):                                                     ### NEW v0.19.4 B98 ###
    """Make *dlg* modal: it takes the grab, and when it is destroyed the grab
    goes back to the window that had it before (a batch progress window, the
    Settings window …).  Without this, a question asked during a batch took
    the grab for good and the main window became clickable mid-batch."""
    try:
        prev = dlg.grab_current()
    except tk.TclError:
        prev = None

    def _grab(tries=10):
        try:
            dlg.grab_set()
        except tk.TclError:                                         # not viewable yet
            if tries > 0:
                try:
                    dlg.after(50, lambda: _grab(tries - 1))
                except tk.TclError:
                    pass

    def _give_back(e):
        if e.widget is not dlg or prev is None or prev is dlg:
            return
        try:
            if prev.winfo_exists():
                prev.grab_set()
        except tk.TclError:
            pass
    _grab()
    dlg.bind("<Destroy>", _give_back, add="+")
    return dlg


class DialogBase(tk.Toplevel):                                      ### NEW v0.19.4 L4 / I15a ###
    """Every dialog of the app.  Esc does what the window's close button does
    (its WM_DELETE_WINDOW handler, else destroy); a class that binds its own
    <Escape> replaces this."""

    def __init__(self, parent=None, **kw):
        super().__init__(parent, **kw)
        self.bind("<Escape>", self._esc_default)

    def _esc_default(self, e=None):
        try:
            cmd = self.protocol("WM_DELETE_WINDOW")
            if cmd:
                self.tk.call(cmd)
            else:
                self.destroy()
        except tk.TclError:
            pass
        return "break"


def programs_info_text(programs, mode):                              ### NEW v0.20.0 F3a-2 / 6g ###
    """The line under the program tick boxes (Settings → Health Rules and the first-start window): the files checked
    and the names a fix writes for *programs* in health mode *mode* (or why there are none)."""
    import media_profiles as _mpf
    ps = _mpf.clean_programs(programs)
    lines = [_i18n.t("f3.files", mode=_i18n.t(f"f3.mode.{mode}"))]
    if not ps:
        lines.append(_i18n.t("f3.none"))
    else:
        ext = {"nfo": "", "poster": ".jpg", "fanart": ".jpg"}
        names = [_mpf.expand(n, "<video>") + ext[k] for k, n in _mpf.write_names(ps).items() if n]
        if names:
            lines.append(_i18n.t("f3.names", names=", ".join(names)))
        bad = _mpf.conflicts(ps)
        if bad:
            lines.append(_i18n.t("f3.conflict", kinds=", ".join(_i18n.t(f"f3.kind.{k}") for k in bad)))
    return "\n".join(lines)


class DialogFrame(DialogBase):                                       ### NEW v0.19.4 L4 / I15a ###
    """The one dialog frame: an optional heading, ``self.body`` and a button
    row packed first at the bottom (a tall body never pushes it out).
    ``add_button`` places buttons right-aligned in call order: add the main
    button last, it sits on the right and Enter runs it (not inside a Text)."""
    BG = "#1e1e2e"
    _KINDS = {"main": ("#89b4fa", "#1e1e2e"), "ok": ("#a6e3a1", "#1e1e2e"),
              "warn": ("#f9e2af", "#1e1e2e"), "danger": ("#f38ba8", "#1e1e2e"),
              "secondary": ("#45475a", "#cdd6f4")}

    def __init__(self, parent, title=None, heading=None, heading_fg="#89b4fa", geometry=None,
                 make_modal=True, resizable=True):
        super().__init__(parent)
        self.configure(bg=self.BG)
        if title:
            self.title(title)
        if geometry:
            self.geometry(geometry)
        try:
            self.transient(parent)
        except tk.TclError:
            pass
        self.resizable(resizable, resizable)
        self.buttons = tk.Frame(self, bg=self.BG)
        self.buttons.pack(side="bottom", fill="x", padx=16, pady=(4, 12))
        self._btn_row = tk.Frame(self.buttons, bg=self.BG)
        self._btn_row.pack(side="right")
        self.heading = None
        if heading:
            self.heading = tk.Label(self, text=heading, font=("Helvetica", 13, "bold"), bg=self.BG, fg=heading_fg)
            self.heading.pack(anchor="w", padx=16, pady=(14, 2))
        self.body = tk.Frame(self, bg=self.BG)
        self.body.pack(fill="both", expand=True)
        self.main_button = None
        self.bind("<Return>", self._on_return)
        if make_modal:
            modal(self)

    def add_button(self, text, command, kind="secondary", main=False):
        bg, fg = self._KINDS.get(kind, self._KINDS["secondary"])
        b = tk.Button(self._btn_row, text=f"  {text}  ", command=command, font=("Helvetica", 10, "bold"),
                      bg=bg, fg=fg, relief="flat", cursor="hand2")
        if self._btn_row.winfo_children()[:-1]:
            self._btn_row.winfo_children()[-2].pack_configure(padx=(0, 8))
        b.pack(side="left")
        if main:
            self.main_button = b
        return b

    def _on_return(self, e):
        if isinstance(e.widget, tk.Text) or self.main_button is None:
            return None
        try:
            if str(self.main_button.cget("state")) != "disabled":
                self.main_button.invoke()
        except tk.TclError:
            pass
        return "break"


### NEW v0.19.6 TR1b — the three health modes (the start question and Settings → Health Rules use the same words) ###
HEALTH_MODES = (
    ("nfo", "Kodi, Jellyfin, Emby, Plex, Infuse…", "recommended — most people choose this"),
    ("nfo_xml", "The above + old Windows media centers", "MediaBrowser, Media Center Master"),
    ("xml", "Only old Windows media centers", "MediaBrowser, Media Center Master"),
)
HEALTH_MODE_IDS = tuple(m[0] for m in HEALTH_MODES)
HEALTH_MODE_NOTE = ("Kodi, Jellyfin, Emby, Plex and Infuse read the .nfo files (made by tinyMediaManager, Radarr, MediaElch, …):\n"
                    "MediaClinic checks and repairs the NFO and ignores movie.xml. The old Windows media centers use movie.xml.\n"
                    "Changing the mode offers a new scan of the libraries.")
HEALTH_MODE_PATH = "Settings → Health Rules → Which programs play your movies?"   # v0.20.0 F3: the tick boxes replace the three buttons

### NEW v0.19.6 TR1c — the four sections of the Health Rules tab and the health modes that use each ###
HEALTH_RULE_SECTIONS = (
    ("general", "General rules", ("nfo", "nfo_xml", "xml"), "every program"),          # v0.20.0 F3: no mode numbers
    ("nfo", "NFO rules", ("nfo", "nfo_xml"), "programs that read the NFO"),
    ("xml", "movie.xml rules", ("nfo_xml", "xml"), "MediaBrowser / Media Center Master"),
    ("both", "NFO ↔ movie.xml comparisons", ("nfo_xml",), "NFO + movie.xml"),
)
HEALTH_RULE_SECTION_OFF = {
    "nfo": "Not used: only MediaBrowser / Media Center Master is ticked (movie.xml only). Tick a program that reads the NFO to use them.",
    "xml": "Not used: no ticked program reads movie.xml. Tick MediaBrowser / Media Center Master to use them.",
    "both": "They compare the NFO with movie.xml: used when MediaBrowser / Media Center Master and a program that reads the NFO are both ticked.",
}


_TAB_KEYS = {                                                    ### NEW v0.20.0 UI1d — the shown tab names ###
    "Editor & FFmpeg": "settings.tab.editor", "API Keys": "settings.tab.api_keys", "Browser": "settings.tab.browser",
    "Language": "settings.tab.language", "Improvements": "settings.tab.improvements",
    "Image Sizes": "settings.tab.image_sizes", "Ratings": "settings.tab.ratings", "Genres": "settings.tab.genres",
    "NFO / XML": "settings.tab.nfo_xml", "User Interface": "settings.tab.ui", "Health Rules": "settings.tab.health",
    "Backup": "settings.tab.backup"}


def tab_title(name):                                             ### NEW v0.20.0 UI1d ###
    """A tab's shown name in the interface language; the registry name (*name*) stays the id."""
    return _i18n.t(_TAB_KEYS[name]) if name in _TAB_KEYS else name


def parse_number(text):                                          ### NEW v0.20.0 UI1d (plan UI1 point 6) ###
    """A number typed in a box: "1.5" and "1,5" are both 1.5 (a comma is the decimal mark when there is no dot);
    settings.json stores the plain number.  Raises ValueError for text."""
    s = str(text).strip().replace(" ", "").replace(" ", "")
    ### NEW v0.20.0 AU7 (pre-build audit) ### a thousands separator: "2.000" in Portuguese / Spanish and "2,000" in
    # English were read as 2 — a backup size limit of 2 MB, and the cleanup then deleted the older backups
    _grp = "," if _i18n.current() == "en" else "."
    if re.fullmatch(rf"\d{{1,3}}(?:{re.escape(_grp)}\d{{3}})+", s):
        return float(s.replace(_grp, ""))
    if "," in s and "." not in s and s.count(",") == 1:
        s = s.replace(",", ".")
    return float(s)


def lang_name(iso, english):                                     ### NEW v0.20.0 UI1d ###
    """A language's name in the interface language ("PT" → "Português"); unknown codes keep the English name."""
    k = "lang." + str(iso).lower()
    if _i18n.current() == "en" and english != iso:              # English keeps each list's own wording ("Mandarin Chinese")
        return english
    return _i18n.t(k) if _i18n.has(k) else english


def shown_combo(parent, var, codes, label_of, **kw):             ### NEW v0.20.0 UI1d ###
    """A read-only combo box that shows label_of(code) while *var* keeps the code (what is saved never changes)."""
    labels = [label_of(c) for c in codes]
    shown = tk.StringVar(value=label_of(var.get()) if var.get() in codes else var.get())

    def _to_code(*_):
        s = shown.get()
        if s in labels and var.get() != codes[labels.index(s)]:
            var.set(codes[labels.index(s)])

    def _to_label(*_):
        if var.get() in codes and shown.get() != label_of(var.get()):
            shown.set(label_of(var.get()))
    shown.trace_add("write", _to_code)
    var.trace_add("write", _to_label)
    cb = ttk.Combobox(parent, textvariable=shown, values=labels, **kw)
    cb._mc_shown = shown
    return cb


_ISO3 = {"ENG": "en", "POR": "pt", "SPA": "es", "FRE": "fr", "GER": "de", "ITA": "it", "JPN": "ja", "KOR": "ko",
         "ZHO": "zh", "RUS": "ru", "ARA": "ar", "HIN": "hi", "NLD": "nl", "POL": "pl", "TUR": "tr"}   ### NEW v0.20.0 UI1d ###
_YESNO = lambda c: _i18n.t("set.opt.yes") if c == "Yes" else _i18n.t("set.opt.no")


def relabel():                                                   ### NEW v0.20.0 UI1d ###
    """The import-time texts of this module in the interface language (the main script calls it from
    _i18n_refresh); ids and the order stay the same."""
    g = globals()
    g["HEALTH_MODES"] = tuple((mid, _i18n.t(f"hm.{mid}"), _i18n.t(f"hm.{mid}.sub")) for mid, _t, _s in HEALTH_MODES)
    g["HEALTH_MODE_NOTE"] = _i18n.t("hm.note")
    g["HEALTH_MODE_PATH"] = _i18n.t("hm.path")
    g["HEALTH_RULE_SECTIONS"] = tuple((sid, _i18n.t(f"hr.sec.{sid}"), modes, _i18n.t(f"hr.sec.{sid}.modes"))
                                      for sid, _t, modes, _m in HEALTH_RULE_SECTIONS)
    for k in list(HEALTH_RULE_SECTION_OFF):
        HEALTH_RULE_SECTION_OFF[k] = _i18n.t(f"hr.off.{k}")
    g["SETTINGS_NOT_SAVED_TEXT"] = _i18n.t("set.not_saved")


def health_section_on(section, mode):
    """True when the rules of *section* are used in health *mode*."""
    return mode in next(s[2] for s in HEALTH_RULE_SECTIONS if s[0] == section)


def health_mode_of(settings):
    """The health mode in *settings*: one of HEALTH_MODE_IDS ("nfo" when missing or unknown)."""
    m = (settings or {}).get("health_mode")
    return m if m in HEALTH_MODE_IDS else "nfo"


class SettingsFieldError(ValueError):                               ### NEW v0.19.4 B94 ###
    """A value in the Settings window that cannot be saved: *field* names it,
    *widget* is focused; nothing is applied."""
    def __init__(self, field, widget, msg):
        super().__init__(f"{field}: {msg}")
        self.field, self.widget, self.msg = field, widget, msg


SETTINGS_NOT_SAVED_TEXT = ("settings.json could not be written (see logs\\app.log).\n\n"   ### NEW v0.19.4 B94a ###
                           "Nothing was changed. Your values are still in this window: "
                           "try Save & Apply again.")


def backup_usage_text(total_bytes, max_mb):                         ### NEW v0.19.4 B75 (D2) ###
    """Backup tab: the folder's size, and by how much the limit is passed."""
    mb = total_bytes / (1024 * 1024)
    if not isinstance(max_mb, (int, float)) or max_mb <= 0:
        return _i18n.t("uf.backup_folder_size_now_bcec", mb=format(mb, '.1f'))
    if mb <= max_mb:
        return _i18n.t("uf.backup_folder_size_now_21aa", mb=format(mb, '.1f'), max_mb=max_mb)
    return (_i18n.t("uf.backup_folder_size_now_689e", mb=format(mb, '.1f'), v=format(mb - max_mb, '.1f'), max_mb=max_mb, backup_protect_days=BACKUP_PROTECT_DAYS))

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


def bind_wheel(toplevel, canvases, main=None):                    ### NEW v0.19.2 B29 ###
    """Mouse wheel for scrolled canvases, bound ONCE on *toplevel* (never with
    bind_all).  The Toplevel is in every child's bindtags, so the wheel works
    anywhere in the window — also over a thumbnail, label or button inside
    the canvas (the old <Enter>/<Leave> + bind_all pattern switched it off
    exactly there, because Tk sends <Leave> to the canvas when the pointer
    moves onto a child).  Scrolls the registered canvas under the pointer
    (found by walking up from winfo_containing), else *main*.  Calling it
    again for the same Toplevel adds canvases.  Used by the main script too."""
    reg = getattr(toplevel, "_mc_wheel", None)
    if reg is None:
        reg = {"canvases": [], "main": None}
        toplevel._mc_wheel = reg

        def _canvas_of(w):
            while w is not None:
                if w in reg["canvases"]:
                    return w
                w = getattr(w, "master", None)
            return None

        def _target(e):
            # Tk 8.6+ delivers the wheel to the widget under the pointer, so the
            # event's own widget comes first; winfo_containing is the fallback.
            w = e.widget if isinstance(getattr(e, "widget", None), tk.Misc) else None
            c = _canvas_of(w)
            if c is None:
                try:
                    c = _canvas_of(toplevel.winfo_containing(e.x_root, e.y_root))
                except (tk.TclError, KeyError):
                    c = None
            return c or reg["main"]

        def _scroll(e, units):
            c = _target(e)
            if c is not None:
                try:
                    c.yview_scroll(units, "units")
                except tk.TclError:
                    pass

        def _on_wheel(e):
            d = getattr(e, "delta", 0) or 0
            units = -int(d / 120) if abs(d) >= 120 else (-1 if d > 0 else 1 if d < 0 else 0)
            if units:
                _scroll(e, units)

        toplevel.bind("<MouseWheel>", _on_wheel, add="+")
        toplevel.bind("<Button-4>", lambda e: _scroll(e, -1), add="+")
        toplevel.bind("<Button-5>", lambda e: _scroll(e, 1), add="+")
    for c in canvases:
        if c is not None and c not in reg["canvases"]:
            reg["canvases"].append(c)
    if main is not None:
        reg["main"] = main
    return reg


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

class SettingsDialog(DialogBase):
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
        (0,  "Editor & FFmpeg", "_build_tools_tab"),   ### MODIFIED v0.19.4 B108 b ###
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
        self.title(_i18n.t("set.settings_92d4", v=self._ctx.app_name if self._ctx else _APP_NAME))
        self.geometry("940x720")   ### MODIFIED v0.18.4 ###
        self.minsize(760, 480)     ### NEW v0.18.4 ###
        self.configure(bg="#1e1e2e")
        self.transient(parent); modal(self)                             ### MODIFIED v0.19.4 B98 ###
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

        # ── Bottom buttons — packed FIRST (side=bottom) so they stay visible
        #    whatever the height of the selected tab.           ### FIXED v0.18.4 ###
        bf = tk.Frame(self, bg="#1e1e2e")
        bf.pack(side="bottom", fill="x", pady=(6, 12))
        inner_bf = tk.Frame(bf, bg="#1e1e2e"); inner_bf.pack()
        tk.Button(inner_bf, text=_i18n.t("set.save_apply_2f67"), font=("Helvetica", 10, "bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._save_close).pack(side="left", padx=(0, 8))
        tk.Button(inner_bf, text=_i18n.t("set.cancel_2fee"), font=("Helvetica", 10, "bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self._cancel_close).pack(side="left")          ### MODIFIED v0.19.2 B44 — asks before discarding ###
        tk.Label(bf, text=_i18n.t("set.save_apply_writes_settings_539d"),
                 font=("Helvetica", 8), bg="#1e1e2e", fg="#6c7086").pack(pady=(4, 0))
        self.bind("<Escape>", lambda e: self._cancel_close())           ### MODIFIED v0.19.2 B44 ###
        self.protocol("WM_DELETE_WINDOW", self._cancel_close)           ### NEW v0.19.2 B44 — [X] too ###

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

        # v0.19.0 — keep the Image Sizes combos and the Health Rules combos in
        # step (one minimum-quality setting, two places to edit it).
        self._bind_quality_mirrors()                            ### NEW v0.19.0 ###

        # ── Snapshot rescan-relevant settings on open        ### NEW v0.11.1 ###
        # Used by _save_close to detect whether a rescan should be offered.
        self._rescan_snapshot = self._take_rescan_snapshot()
        self._widget_snapshot = self._widget_state()                  ### NEW v0.19.2 B44 — for "Discard your changes?" ###

        # ── Jump to requested tab after UI is built ───────────────────────────
        self._nb = nb
        self.after(10, lambda: nb.select(min(self._initial_tab, len(nb.tabs()) - 1)))
        self._fit_tab_row(nb)                                   ### NEW v0.19.6 TR8 ###

        # v0.19.0 — window size/position memory.  The hook is installed by the
        # main script (SettingsDialog._remember_window_hook); the harness and
        # any other host without it are unaffected.           ### NEW v0.19.0 ###
        _hook = getattr(self, "_remember_window_hook", None)
        if _hook:
            try:
                _hook(self, "SettingsDialog", True)
            except Exception:
                pass

    def tab_row_width(self, nb):                                ### NEW v0.19.6 TR8 ###
        """Pixels the notebook needs so that no tab name is cut off."""
        nb.update_idletasks()
        return int(nb.winfo_reqwidth())                         # ttk asks for the whole tab row

    def _fit_tab_row(self, nb):                                 ### NEW v0.19.6 TR8 ###
        """A wider system font (Linux draws "Helvetica" with DejaVu Sans) cut the tab names off
        at 940 px ("Languag", "NFO / XM"): open the window as wide as the tab row needs."""
        try:
            need = self.tab_row_width(nb)
            if need > 940:
                self.geometry(f"{min(need, self.winfo_screenwidth() - 40)}x720")
                self.minsize(min(need, self.winfo_screenwidth() - 40), 480)
        except (tk.TclError, ValueError):
            pass

    # ── v0.19.2 B58: where FFmpeg was found; "Search again" (deep, async) ─────
    @staticmethod
    def _ffmpeg_found_text():                                         ### NEW v0.19.2 B58 ###
        try:
            import settings_controller as _sctl
            how, d = _sctl.FFMPEG_FOUND.get("how"), _sctl.FFMPEG_FOUND.get("dir")
        except Exception:
            how, d = "", ""
        if not how:
            return _i18n.t("uf.ffmpeg_not_searched_yet_819b")
        return f"FFmpeg: {d}  ({how})" if d else _i18n.t("uf.ffmpeg_not_found_install_c78e")

    def _ffmpeg_search_again(self):                                   ### NEW v0.19.2 B58 ###
        if not (self._ctx and self._ctx.ffmpeg_finder):
            return
        self._ff_how_lbl.configure(text=_i18n.t("set.searching_1f68"))
        finder, path = self._ctx.ffmpeg_finder, self._ffmpeg_var.get().strip()
        def _work():
            try:
                return finder(path, deep=True)
            except TypeError:                                         # a finder without the deep option
                return finder(path)
        def _done(res):
            try:
                ff = res[0] if res else None
                if ff and not self._ffmpeg_var.get().strip():
                    import os as _os
                    self._ffmpeg_var.set(_os.path.dirname(ff))
                self._ff_how_lbl.configure(text=self._ffmpeg_found_text())
            except tk.TclError:
                pass
        run_async(_work, callback=_done, root=self)

    # ── v0.19.2 B44: Esc / Cancel / [X] ask before discarding changes ────────
    def _widget_state(self):                                          ### NEW v0.19.2 B44 ###
        """Every value the user can edit: all tk variables (also those kept in
        dicts such as _hr_vars) and the Text boxes (genres, tags), as raw
        strings — a blank number field never raises here."""
        st = {}
        def _raw(v):
            try:
                return str(v._tk.globalgetvar(v._name))
            except Exception:
                return None
        for name, val in list(vars(self).items()):
            if isinstance(val, tk.Variable):
                st[name] = _raw(val)
            elif isinstance(val, dict) and val and all(isinstance(x, tk.Variable) for x in val.values()):
                for k, x in val.items():
                    st[f"{name}[{k}]"] = _raw(x)
            elif isinstance(val, tk.Text):
                try:
                    st[name] = val.get("1.0", "end")
                except tk.TclError:
                    pass
        return st

    # ── v0.20.0 CF1 — the collection folder: shown in NFO / XML, set in the Libraries window ──
    def _show_coll_folder(self):
        cf = self._coll_folder_var.get()
        if hasattr(self, "_coll_folder_lbl"):
            self._coll_folder_lbl.configure(text=cf or _i18n.t("cf.none"), fg="#cdd6f4" if cf else "#f9e2af")

    def _coll_folder_from_app(self):
        """After the Libraries window or the prompt: the stored folder; not an unsaved change of this window."""
        if not hasattr(self.master, "_collection_folder"):
            return
        cf = self.master._collection_folder()
        self._coll_folder_var.set(cf)
        self._s["collection_folder"] = cf
        snap = getattr(self, "_widget_snapshot", None)
        if isinstance(snap, dict) and "_coll_folder_var" in snap:
            snap["_coll_folder_var"] = cf

    def _open_libraries_for_collections(self):
        if hasattr(self.master, "_open_libraries"):
            self.master._open_libraries(owner=self)
            try:
                self.grab_set()
            except tk.TclError:
                pass
            self._coll_folder_from_app()
            return
        p = filedialog.askdirectory(parent=self, title=_i18n.t("set.collection_folder_583e"))   # no app (the harness)
        if p:
            self._coll_folder_var.set(os.path.normpath(p))

    def _group_coll_ticked(self):
        if self._group_coll_var.get() and not self._coll_folder_var.get() and hasattr(self.master, "_ask_collection_folder"):
            self.master._ask_collection_folder(parent=self)
            try:
                self.grab_set()
            except tk.TclError:
                pass
            self._coll_folder_from_app()

    def _has_changes(self):                                           ### NEW v0.19.2 B44 ###
        snap = getattr(self, "_widget_snapshot", None)
        return snap is not None and self._widget_state() != snap

    def _cancel_close(self):                                          ### NEW v0.19.2 B44 ###
        """Esc / Cancel / [X]: unchanged → close; changed → ask (default No).
        Nothing is saved either way; Save & Apply is unchanged."""
        if self._has_changes() and not messagebox.askyesno(
                _i18n.t("set.discard_your_changes_945f"),
                _i18n.t("set.you_changed_settings_in_331e"), icon="warning", default="no", parent=self):
            return
        self.destroy()

    # ── Shared widget helpers ─────────────────────────────────────────────────

    @staticmethod
    def _num(var, default):
        """Value of a Tk numeric variable, or *default* when the spinbox is blank
        or holds text (v.get() raises TclError in that case).  ### NEW v0.18.4 ###
        ### MODIFIED v0.20.0 UI1d ### "1,5" is read as 1.5 (Portuguese / Spanish decimal comma)."""
        try:
            try:                                                  # v0.20.0 RV2: the typed text first — IntVar.get()
                v = var._tk.globalgetvar(var._name)               # read "2.000" as 2 without an error (PT / ES)
                if not isinstance(v, str):
                    v = var.get()
            except tk.TclError:                                   # a typed variable holding "1,5" or text
                v = str(var._tk.globalgetvar(var._name) or "")
            if isinstance(v, str):
                v = v.strip()
                if v == "":
                    return default
                f = parse_number(v)
                return f if isinstance(default, float) else int(f)
            return v
        except (tk.TclError, ValueError, TypeError, AttributeError):
            return default

    def _check_number_fields(self):                               ### NEW v0.19.5 SH-E9 ###
        """Text in a number box is refused by name, as Help says. A blank box still means the default."""
        _T = _i18n.t                                               # v0.20.0 AU23: the field names in the interface language
        fields = [(_T("au.f.max_nfo"), "_max_nfo_kb_var"), (_T("au.f.max_xml"), "_max_xml_kb_var"), (_T("au.f.min_poster"), "_min_poster_kb_var"),
                  (_T("au.f.min_folder"), "_min_folder_kb_var"), (_T("au.f.min_fanart"), "_min_fanart_kb_var"), (_T("au.f.backdrops"), "_backdrop_count_var"),
                  (_T("au.f.workers"), "_scan_workers_var"), (_T("au.f.sec_frame"), "_ffmpeg_frame_timeout_var"), (_T("au.f.sec_run"), "_ffmpeg_run_budget_var"),
                  (_T("au.f.ffprobe"), "_ffprobe_workers_var")]
        pairs = [(lbl, getattr(self, attr)) for lbl, attr in fields if hasattr(self, attr)]
        for src in ("_hr_int_vars", "_hr_flt_vars"):
            pairs += [(_i18n.t("au.f.rule", k=k), v) for k, v in getattr(self, src, {}).items()]
        for lbl, var in pairs:
            try:                                                  # v0.20.0 RV2: the typed text first (see _num)
                raw = self.tk.globalgetvar(str(var))
                if not isinstance(raw, str):
                    raw = var.get()
            except tk.TclError:                                   # a typed variable holding text; a blank one is fine
                raw = str(self.tk.globalgetvar(str(var)) or "")
            if isinstance(raw, str) and raw.strip():
                try:
                    parse_number(raw)                             # v0.20.0 UI1d: 1.5 and 1,5
                except ValueError:
                    raise SettingsFieldError(lbl, None, _i18n.t("au.not_number", v=raw.strip())) from None

    def _scrollable_tab(self, nb, label):
        """Add a tab whose content scrolls vertically (mouse wheel while the
        pointer is over it).  Returns the inner frame to pack widgets into.
        Replaces three copy-pasted canvas blocks.                ### NEW v0.18.4 ###"""
        outer = tk.Frame(nb, bg="#1e1e2e"); nb.add(outer, text=tab_title(label))
        canvas = tk.Canvas(outer, bg="#1e1e2e", highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        f = tk.Frame(canvas, bg="#1e1e2e")
        win = canvas.create_window((0, 0), window=f, anchor="nw")
        f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        bind_wheel(self, [canvas])                              ### MODIFIED v0.19.2 B29 — was <Enter>/<Leave> + bind_all ###
        return f

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
        tk.Button(r, text=_i18n.t("set.browse_1bd8"), font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: self._browse_file(var, title, filetypes)
                  ).pack(side="left", padx=(6, 0))
        return r

    def _browse_file(self, var, title, filetypes):              # v0.20.0 AU19: parent=self (it opened behind Settings)
        p = filedialog.askopenfilename(parent=self, title=title, filetypes=filetypes)
        if p: var.set(p)

    # ── Tab 0: Tools ──────────────────────────────────────────────────────────

    def _build_tools_tab(self, nb, label="Editor & FFmpeg"):   ### MODIFIED v0.19.4 B108 b ###
        f = self._scrollable_tab(nb, label)                    ### MODIFIED v0.18.4 ###

        # Text editor
        self._section(f, _i18n.t("set.text_editor_for_nfo_7468"))
        self._note(f, _i18n.t("set.notepad_is_auto_detected_1286"))
        self._editor_var = tk.StringVar(value=self._s.get("text_editor", ""))
        r = self._file_entry_row(f, self._editor_var, _i18n.t("set.select_text_editor_1d5d"),
                                 [("Executables", "*.exe"), ("All", "*.*")])
        ### MODIFIED_BY_CLAUDE_v18 — run notepadpp_finder on daemon thread to avoid blocking UI ###
        def _npp_done(npp):
            if npp and not self._editor_var.get():
                self._editor_var.set(npp)
                snap = getattr(self, "_widget_snapshot", None)     ### NEW v0.19.2 B44 — an auto-fill is not a user change ###
                if snap is not None:
                    snap["_editor_var"] = npp
        if self._ctx and self._ctx.notepadpp_finder:
            run_async(self._ctx.notepadpp_finder, callback=_npp_done, root=self)
        tk.Button(r, text=_i18n.t("set.test_0cbc"), font=("Helvetica", 9), bg="#45475a", fg="#a6e3a1",
                  relief="flat", cursor="hand2",
                  command=lambda: self._test_editor(self._editor_var)
                  ).pack(side="left", padx=(4, 0))

        # FFmpeg
        self._section(f, "FFmpeg / FFprobe")
        self._note(f, _i18n.t("set.point_to_the_folder_da55"))
        self._ffmpeg_var = tk.StringVar(value=self._s.get("ffmpeg_path", ""))
        _ff_found = tk.Label(f, text="", font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086", anchor="w")   # F18
        if not self._ffmpeg_var.get() and self._ctx and self._ctx.ffmpeg_finder:
            ### MODIFIED v0.19.4 (F18) — found in a worker and only SHOWN; the empty box stays empty (PATH / search) ###
            _finder = self._ctx.ffmpeg_finder

            def _found(res):
                import os
                try:
                    ff = (res or (None, None))[0]
                    _ff_found.configure(text=(_i18n.t("set.found_used_while_the_193a", ff=os.path.dirname(ff)) if ff
                                              else _i18n.t("set.ffmpeg_not_found_on_c84d")))
                except Exception:
                    pass
            run_async(lambda: _finder(""), callback=_found, root=self)
        r = self._row(f)
        tk.Entry(r, textvariable=self._ffmpeg_var, font=("Consolas", 9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=50).pack(side="left", fill="x", expand=True, ipady=4)
        _ff_found.pack(anchor="w", padx=16)                       # F18
        tk.Button(r, text=_i18n.t("set.browse_1bd8"), font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: self._ffmpeg_var.set(
                      filedialog.askdirectory(parent=self, title=_i18n.t("set.ffmpeg_folder_3cae")) or self._ffmpeg_var.get())
                  ).pack(side="left", padx=(6, 0))
        self._ff_status_lbl = tk.Label(r, text="", font=("Helvetica", 9),
                                       bg="#1e1e2e", fg="#a6adc8")
        self._ff_status_lbl.pack(side="left", padx=(8, 0))
        tk.Button(r, text=_i18n.t("set.test_ffmpeg_114b"), font=("Helvetica", 9), bg="#45475a", fg="#f9e2af",
                  relief="flat", cursor="hand2",
                  command=self._test_ffmpeg_btn).pack(side="left", padx=(4, 0))
        # NEW v0.19.2 B58 — where FFmpeg was found, and a deeper search
        r_how = self._row(f)
        self._ff_how_lbl = tk.Label(r_how, text=self._ffmpeg_found_text(), font=("Helvetica", 9),
                                    bg="#1e1e2e", fg="#a6adc8", anchor="w", justify="left")
        self._ff_how_lbl.pack(side="left")
        tk.Button(r_how, text=_i18n.t("set.search_again_3b30"), font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=self._ffmpeg_search_again).pack(side="left", padx=(8, 0))
        # NEW v0.19.1 I5 — FFprobe result cache
        self._ffprobe_cache_var = tk.BooleanVar(value=bool(self._s.get("ffprobe_cache_enabled", True)))
        tk.Checkbutton(f, text=_i18n.t("set.remember_ffprobe_results_ffprobe_189f"),
                       variable=self._ffprobe_cache_var, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(anchor="w", padx=22, pady=(4, 0))
        # NEW v0.19.2 B28 — limits for "Frames from movie" (FFmpeg runs in the background)
        self._note(f, _i18n.t("set.frames_from_movie_ffmpeg_0b5f"))
        r = self._row(f)
        tk.Label(r, text=_i18n.t("set.seconds_per_frame_f2c2"), font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=26, anchor="w").pack(side="left")
        self._ffmpeg_frame_timeout_var = tk.IntVar(value=self._s.get("ffmpeg_frame_timeout_sec", 20))
        tk.Spinbox(r, from_=5, to=300, textvariable=self._ffmpeg_frame_timeout_var, width=6,
                   font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                   buttonbackground="#45475a", relief="flat").pack(side="left")
        tk.Label(r, text=_i18n.t("set.seconds_per_run_4ef3"), font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self._ffmpeg_run_budget_var = tk.IntVar(value=self._s.get("ffmpeg_run_budget_sec", 180))
        tk.Spinbox(r, from_=30, to=1800, increment=30, textvariable=self._ffmpeg_run_budget_var, width=6,
                   font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                   buttonbackground="#45475a", relief="flat").pack(side="left", padx=(6, 0))

        # Backdrop count
        self._section(f, _i18n.t("set.backdrop_extraction_96e5"))
        self._note(f, _i18n.t("set.default_number_of_backdrop_4101"))
        r = self._row(f)
        tk.Label(r, text=_i18n.t("set.default_frame_count_7eaf"), font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=26, anchor="w").pack(side="left")
        self._backdrop_count_var = tk.IntVar(value=self._s.get("backdrop_count", 10))
        tk.Spinbox(r, from_=1, to=50, textvariable=self._backdrop_count_var, width=6,
                   font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                   buttonbackground="#45475a", relief="flat").pack(side="left")

        # Parallel scanning (v0.18.4)                                ### NEW v0.18.4 ###
        self._section(f, _i18n.t("set.parallel_scanning_c1b0"))
        self._note(f, _i18n.t("set.workers_used_by_full_7947"))
        r = self._row(f)
        tk.Label(r, text=_i18n.t("set.folder_image_metadata_workers_5976"), font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=max(32, len(_i18n.t("set.folder_image_metadata_workers_5976")) + 3),
                 anchor="w").pack(side="left")                                     # v0.20.0 UI1e
        self._scan_workers_var = tk.IntVar(value=self._s.get("scan_workers", 6))
        tk.Spinbox(r, from_=1, to=16, textvariable=self._scan_workers_var, width=5,
                   font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                   buttonbackground="#45475a", relief="flat").pack(side="left")
        tk.Label(r, text=_i18n.t("set.default_cfd0"), font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086").pack(side="left")
        r = self._row(f)
        tk.Label(r, text=_i18n.t("set.ffprobe_processes_in_parallel_779a"), font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=max(32, len(_i18n.t("set.folder_image_metadata_workers_5976")) + 3),
                 anchor="w").pack(side="left")                                     # v0.20.0 UI1e: the two boxes stay aligned
        self._ffprobe_workers_var = tk.IntVar(value=self._s.get("ffprobe_workers", 2))
        tk.Spinbox(r, from_=1, to=8, textvariable=self._ffprobe_workers_var, width=5,
                   font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                   buttonbackground="#45475a", relief="flat").pack(side="left")
        tk.Label(r, text=_i18n.t("set.default_28f9"), font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086").pack(side="left")

        # Metadata source / scraper
        self._section(f, _i18n.t("set.video_scraper_metadata_source_073a"))
        self._note(f, _i18n.t("set.scraper_executable_optional_launched_58c1"))
        self._scraper_var = tk.StringVar(value=self._s.get("scraper_path", ""))
        self._file_entry_row(f, self._scraper_var, _i18n.t("set.select_scraper_e674"),
                             [("Executables", "*.exe"), ("All", "*.*")])

    def _test_editor(self, var):
        path = var.get().strip()
        if not path:
            messagebox.showwarning(_i18n.t("set.not_set_9ba6"), _i18n.t("set.no_editor_path_set_b258"), parent=self); return
        import os
        if not os.path.isfile(path):
            messagebox.showerror(_i18n.t("set.not_found_9e07"), _i18n.t("set.file_not_found_ab28", path=path), parent=self); return
        try:
            subprocess.Popen([path],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            messagebox.showinfo(_i18n.t("set.test_0cbc"), _i18n.t("set.editor_launched_82cb", path=path), parent=self)
        except Exception as e:
            messagebox.showerror(_i18n.t("set.launch_failed_722c"), str(e), parent=self)

    def _test_ffmpeg_btn(self):
        ### NEW v0.14.0 — subprocess runs on daemon thread; never blocks UI ###
        ctx = self._ctx
        if not ctx or not ctx.ffmpeg_finder or not ctx.ffmpeg_tester:
            return
        path = self._ffmpeg_var.get().strip()
        self._ff_status_lbl.configure(text=_i18n.t("set.testing_1e97"), fg="#a6adc8")

        def _work():
            ff, fp = ctx.ffmpeg_finder(path)
            return ctx.ffmpeg_tester(ff, fp)

        def _done(result):
            ff_ok, fp_ok, ff_msg, fp_msg = result
            if ff_ok and fp_ok:
                self._ff_status_lbl.configure(text=_i18n.t("set.both_ok_db50"), fg="#a6e3a1")
            else:
                msgs = []
                if not ff_ok: msgs.append(f"ffmpeg: {ff_msg}")
                if not fp_ok: msgs.append(f"ffprobe: {fp_msg}")
                self._ff_status_lbl.configure(
                    text="✗ " + " | ".join(msgs), fg="#f38ba8")

        run_async(_work, callback=_done, root=self)

    # ── Tab 1: API Keys ───────────────────────────────────────────────────────

    def _build_api_keys_tab(self, nb, label="API Keys"):
        f = self._scrollable_tab(nb, label)                    ### MODIFIED v0.18.4 ###

        # TMDb
        self._section(f, _i18n.t("set.tmdb_api_key_the_8454"))
        self._note(f, _i18n.t("set.required_for_fetching_ratings_b38e"))
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
        tk.Button(r, text=_i18n.t("set.validate_ad3d"), font=("Helvetica", 9), bg="#45475a", fg="#f9e2af",
                  relief="flat", cursor="hand2",
                  command=self._validate_tmdb).pack(side="left", padx=(4, 0))
        self._tmdb_status = tk.Label(r, text="", font=("Helvetica", 9),
                                     bg="#1e1e2e", fg="#a6adc8",
                                     wraplength=380, justify="left")   # v0.19.1 B22 — longer messages
        self._tmdb_status.pack(side="left", padx=(6, 0))

        r2 = self._row(f)
        tk.Label(r2, text=_i18n.t("set.no_key_yet_6248"), font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        lnk1 = tk.Label(r2, text=_i18n.t("set.click_here_to_get_a347"),
                         font=("Helvetica", 9, "underline"), bg="#1e1e2e", fg="#89b4fa",
                         cursor="hand2")
        lnk1.pack(side="left")
        lnk1.bind("<Button-1>", lambda e: self._open_url_fn("https://www.themoviedb.org/settings/api")
                  if self._open_url_fn else None)

        self._note(f, _i18n.t("set.how_to_get_a_45a4"))

        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(12, 0))

        # OMDb
        self._section(f, _i18n.t("set.omdb_api_key_imdb_34e0"))
        self._note(f, _i18n.t("set.required_for_fetching_imdb_1254"))
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
        tk.Button(r, text=_i18n.t("set.validate_ad3d"), font=("Helvetica", 9), bg="#45475a", fg="#f9e2af",
                  relief="flat", cursor="hand2",
                  command=self._validate_omdb).pack(side="left", padx=(4, 0))
        self._omdb_status = tk.Label(r, text="", font=("Helvetica", 9),
                                     bg="#1e1e2e", fg="#a6adc8",
                                     wraplength=380, justify="left")   # v0.19.1 B22 — longer messages
        self._omdb_status.pack(side="left", padx=(6, 0))

        r3 = self._row(f)
        tk.Label(r3, text=_i18n.t("set.no_key_yet_6248"), font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        lnk2 = tk.Label(r3, text=_i18n.t("set.click_here_to_get_cedf"),
                         font=("Helvetica", 9, "underline"), bg="#1e1e2e", fg="#89b4fa",
                         cursor="hand2")
        lnk2.pack(side="left")
        lnk2.bind("<Button-1>", lambda e: self._open_url_fn("https://www.omdbapi.com/apikey.aspx")
                  if self._open_url_fn else None)

        self._note(f, _i18n.t("set.how_to_get_an_045b"))

        ### NEW v0.19.1 I10 — fanart.tv (second image source in the Fetch dialogs) ###
        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(12, 0))
        self._section(f, _i18n.t("set.fanart_tv_api_key_176a"))
        self._note(f, _i18n.t("set.optional_adds_fanart_tv_4864"))
        self._fanarttv_var = tk.StringVar(value=self._s.get("fanarttv_api_key", ""))
        r = self._row(f)
        self._fanarttv_entry = tk.Entry(r, textvariable=self._fanarttv_var, font=("Consolas", 9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=46, show="•")
        self._fanarttv_entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text="👁", font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2", width=2,
                  command=lambda: self._toggle_show(self._fanarttv_entry)
                  ).pack(side="left", padx=(4, 0))
        tk.Button(r, text=_i18n.t("set.validate_ad3d"), font=("Helvetica", 9), bg="#45475a", fg="#f9e2af",
                  relief="flat", cursor="hand2",
                  command=self._validate_fanarttv).pack(side="left", padx=(4, 0))
        self._fanarttv_status = tk.Label(r, text="", font=("Helvetica", 9),
                                         bg="#1e1e2e", fg="#a6adc8",
                                         wraplength=380, justify="left")
        self._fanarttv_status.pack(side="left", padx=(6, 0))

        r4 = self._row(f)
        tk.Label(r4, text=_i18n.t("set.no_key_yet_6248"), font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        self._fanarttv_link = tk.Label(r4, text=_i18n.t("set.click_here_to_get_68ae"),
                         font=("Helvetica", 9, "underline"), bg="#1e1e2e", fg="#89b4fa",
                         cursor="hand2")
        self._fanarttv_link.pack(side="left")
        self._fanarttv_link.bind("<Button-1>", lambda e: self._open_url_fn(FANARTTV_KEY_URL)
                                 if self._open_url_fn else None)
        self._note(f, _i18n.t("set.the_page_asks_you_cc7f"))

        tk.Label(f, text=_i18n.t("set.client_vip_key_1f71"), font=("Helvetica", 9, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(anchor="w", padx=24, pady=(8, 0))
        self._fanarttv_client_var = tk.StringVar(value=self._s.get("fanarttv_client_key", ""))
        r5 = self._row(f)
        self._fanarttv_client_entry = tk.Entry(r5, textvariable=self._fanarttv_client_var,
                 font=("Consolas", 9), bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=46, show="•")
        self._fanarttv_client_entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r5, text="👁", font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2", width=2,
                  command=lambda: self._toggle_show(self._fanarttv_client_entry)
                  ).pack(side="left", padx=(4, 0))
        self._note(f, _i18n.t("set.optional_only_for_fanart_ed90"))

    @staticmethod
    def _toggle_show(entry):
        entry.configure(show="" if entry.cget("show") == "•" else "•")

    def _validate_tmdb(self):
        key = self._tmdb_var.get().strip()
        if not key:
            self._tmdb_status.configure(text=_i18n.t("set.no_key_entered_42de"), fg="#f38ba8"); return
        self._tmdb_status.configure(text=_i18n.t("set.testing_1e97"), fg="#a6adc8")
        self.update_idletasks()
        def _worker():  # MODIFIED_BY_CLAUDE_v18 - migrated from threading.Thread to run_async
            import urllib.request, urllib.error, gzip as _gzip
            ok = False
            msg = _i18n.t("set.invalid_or_network_error_995c")
            try:
                url = f"https://api.themoviedb.org/3/configuration?api_key={key}"
                req = urllib.request.Request(url, headers={
                    "User-Agent": USER_AGENT,                   ### MODIFIED v0.19.4 B96d — was a fixed old version ###
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
                msg = _i18n.t("set.valid_3af4") if ok else _i18n.t("set.unexpected_response_a399")
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
                kind = classify_http_status(e.code, str(detail))      ### MODIFIED v0.19.1 B22 ###
                msg = (_validate_failure_text("TMDB", kind) if kind
                       else _i18n.t("set.http_b2f3", code=e.code, detail=detail))
            except urllib.error.URLError as e:
                msg = _validate_failure_text("TMDB", classify_network_reason(str(e.reason)))   ### MODIFIED v0.19.1 B22 ###
            except Exception as e:
                msg = _i18n.t("set.error_7162", name=type(e).__name__, e=e)
            return (ok, msg)
        def _tmdb_done(result):
            ok, msg = result
            msg = redact_key_text(msg, key)                     ### NEW v0.19.4 B96d ###
            self._tmdb_status.configure(text=msg, fg="#a6e3a1" if ok else "#f38ba8")
        run_async(_worker, callback=_tmdb_done, root=self)

    def _validate_fanarttv(self):                                  ### NEW v0.19.1 I10 ###
        key = self._fanarttv_var.get().strip()
        if not key:
            self._fanarttv_status.configure(text=_i18n.t("set.no_key_entered_42de"), fg="#f38ba8"); return
        self._fanarttv_status.configure(text=_i18n.t("set.testing_1e97"), fg="#a6adc8")
        self.update_idletasks()
        def _worker():
            import urllib.request, urllib.error
            lbl = "fanart.tv"
            try:
                url = f"https://webservice.fanart.tv/v3/movies/603?api_key={key}"
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})   ### MODIFIED v0.19.4 B96d ###
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read())
                if isinstance(data, dict) and (data.get("tmdb_id") or data.get("name")):
                    return True, "✓ " + _i18n.t("au.valid")
                return False, "✗ " + _i18n.t("au.unexpected")
            except urllib.error.HTTPError as e:
                try:
                    _b = json.loads(e.read() or b"{}")
                    detail = str(_b.get("error message") or _b.get("message") or "")
                except Exception:
                    detail = ""
                kind = classify_http_status(e.code, detail)
                return False, (_validate_failure_text(lbl, kind) if kind
                               else f"✗ HTTP {e.code}: {detail}")
            except urllib.error.URLError as e:
                return False, _validate_failure_text(lbl, classify_network_reason(str(e.reason)))
            except Exception as e:
                return False, "✗ " + _i18n.t("au.error_x", x=type(e).__name__)
        def _done(result):
            ok, msg = result
            msg = redact_key_text(msg, key)                     ### NEW v0.19.4 B96d ###
            self._fanarttv_status.configure(text=msg, fg="#a6e3a1" if ok else "#f38ba8")
        run_async(_worker, callback=_done, root=self)

    def _validate_omdb(self):
        key = self._omdb_var.get().strip()
        if not key:
            self._omdb_status.configure(text=_i18n.t("set.no_key_entered_42de"), fg="#f38ba8"); return
        self._omdb_status.configure(text=_i18n.t("set.testing_1e97"), fg="#a6adc8")
        self.update_idletasks()
        def _worker():  # MODIFIED_BY_CLAUDE_v18 - migrated from threading.Thread to run_async
            ### MODIFIED v0.19.1 B22 — the same messages + advice as the main window ###
            import urllib.request, urllib.error
            lbl = _i18n.t("uf.omdb_imdb_data_5eaf")
            try:
                url = f"https://www.omdbapi.com/?apikey={key}&t=test&type=movie"
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})   ### MODIFIED v0.19.4 B96d ###
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read())
                err = str(data.get("Error", "")).lower()
                if data.get("Response") == "False" and "limit" in err:
                    return False, _validate_failure_text(lbl, "daily_limit", _i18n.t("uf.tmdb_ratings_still_work_c20a"))
                if data.get("Response") == "False" and ("invalid api key" in err or "unauthorized" in err):
                    return False, _validate_failure_text(lbl, "invalid_key")
                return True, "✓ " + _i18n.t("au.valid")
            except urllib.error.HTTPError as e:
                try:
                    detail = str(json.loads(e.read() or b"{}").get("Error", ""))
                except Exception:
                    detail = ""
                kind = classify_http_status(e.code, detail)
                return False, (_validate_failure_text(lbl, kind, _i18n.t("uf.tmdb_ratings_still_work_c20a")) if kind
                               else f"✗ HTTP {e.code}: {detail}")
            except urllib.error.URLError as e:
                return False, _validate_failure_text(lbl, classify_network_reason(str(e.reason)))
            except Exception as e:
                return False, "✗ " + _i18n.t("au.error_x", x=type(e).__name__)
        def _omdb_done(result):
            ok, msg = result
            msg = redact_key_text(msg, key)                     ### NEW v0.19.4 B96d ###
            self._omdb_status.configure(text=msg, fg="#a6e3a1" if ok else "#f38ba8")
        run_async(_worker, callback=_omdb_done, root=self)

    # ── Tab 2: Browser ────────────────────────────────────────────────────────

    def _build_browser_tab(self, nb, label="Browser"):
        """Browser selection tab with enhanced visual radio button feedback.
        ### NEW v0.13.0 — selected option highlighted (filled icon, accent bg,
        '(selected)' suffix); unselected options dimmed. ###
        ### NEW v0.14.0 — browser detection runs on daemon thread via run_async ###
        """
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=tab_title(label))

        self._section(f, _i18n.t("set.default_browser_for_external_bc5d"))
        self._note(f, _i18n.t("set.used_when_opening_imdb_70e6"))

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
                    lv.set(base_label + _i18n.t("set.selected_suffix"))   # v0.20.0 UI1e
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
                                  text=_i18n.t("set.detecting_browsers_3208"),
                                  font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086")
        _detecting_lbl.pack(anchor="w", pady=2)

        def _populate_browsers(detected):
            """Called on main thread after browser detection completes."""
            _detecting_lbl.destroy()
            options = [(_i18n.t("set.browser_default"), "")]
            for name, path in (detected or []):
                options.append((name, path))
            _build_radio_buttons(options)
            if not detected:
                tk.Label(options_frame,
                         text=_i18n.t("set.no_additional_browsers_detected_71c7"),
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

        self._section(f, _i18n.t("set.or_enter_browser_path_abb9"))
        self._note(f, _i18n.t("set.browse_to_any_browser_7994"))
        r = self._row(f)
        tk.Entry(r, textvariable=self._browser_var, font=("Consolas", 9),
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 relief="flat", width=50).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(r, text=_i18n.t("set.browse_1bd8"), font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=lambda: self._browse_file(self._browser_var, "Select browser",
                                                    [("Executables", "*.exe"), ("All", "*.*")])
                  ).pack(side="left", padx=(6, 0))
        tk.Button(r, text=_i18n.t("set.test_0cbc"), font=("Helvetica", 9), bg="#45475a", fg="#a6e3a1",
                  relief="flat", cursor="hand2",
                  command=self._test_browser).pack(side="left", padx=(4, 0))

    def _test_browser(self):
        import os
        p = self._browser_var.get().strip()
        if not p:
            messagebox.showinfo(_i18n.t("set.system_default_750a"),
                                _i18n.t("set.using_system_default_browser_3771"), parent=self)
            return
        if not os.path.isfile(p):
            messagebox.showerror(_i18n.t("set.not_found_9e07"), _i18n.t("set.file_not_found_5730", p=p), parent=self); return
        try:
            subprocess.Popen([p, "https://www.themoviedb.org"],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            messagebox.showinfo(_i18n.t("set.test_0cbc"), _i18n.t("set.browser_launched_6346", p=p), parent=self)
        except Exception as e:
            messagebox.showerror(_i18n.t("set.launch_failed_722c"), str(e), parent=self)

    # ── Tab 3: Language OK? ───────────────────────────────────────────────────

    def _build_language_tab(self, nb, label="Language"):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=tab_title(label))

        tk.Label(f, text=_i18n.t("set.language_ok_column_target_95a6"),
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(f, text=_i18n.t("set.select_the_language_for_8c16"),
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#a6adc8",
                 justify="left").pack(anchor="w", padx=16, pady=(0, 12))

        self._lang_var = tk.StringVar(value=self._s.get("lang_ok_code", "PT"))
        lang_frame = tk.Frame(f, bg="#1e1e2e"); lang_frame.pack(padx=16, fill="x")
        tk.Label(lang_frame, text=_i18n.t("set.language_0885"), font=("Helvetica", 10),
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

        tk.Label(f, text=_i18n.t("set.available_languages_ab4e"),
                 font=("Helvetica", 10, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16)
        grid_f = tk.Frame(f, bg="#1e1e2e"); grid_f.pack(padx=16, fill="x")
        for i, (iso, name) in enumerate(self._langs):
            r = i // 3; c = i % 3
            tk.Label(grid_f, text=f"{iso} — {lang_name(iso, name)}",
                     font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086",
                     anchor="w", width=22).grid(row=r, column=c, sticky="w", pady=1)

    def _update_lang_desc(self, *_):
        code = self._lang_var.get().upper()
        for iso, name in self._langs:
            if iso == code:
                self._lang_desc.configure(text=f"→ {lang_name(iso, name)}")
                return
        self._lang_desc.configure(text="")

    # ── Tab 4: Improvements ───────────────────────────────────────────────────

    def _build_improvements_tab(self, nb, label="Improvements"):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=tab_title(label))

        tk.Label(f, text=_i18n.t("set.improvement_checks_58c3"),
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16, 6))

        ic = self._s.get("improve_checks", self._defaults.get("improve_checks", {}))  ### FIX v0.15.0 ###
        self._ic_vars = {}
        checks_def = [
            ("large_xml",    _i18n.t("set.ic.large_xml")),            # v0.20.0 UI1d
            ("nfo_xml_diff", _i18n.t("set.ic.nfo_xml_diff")),
            ("ffprobe_diff", _i18n.t("set.ic.ffprobe_diff")),
            ("poster_folder", _i18n.t("set.ic.poster_folder")),
            ("proportions",  _i18n.t("set.ic.proportions")),
            ("backdrops",    _i18n.t("set.ic.backdrops")),
        ]
        for key, label in checks_def:
            v = tk.BooleanVar(value=ic.get(key, True))
            self._ic_vars[key] = v
            tk.Checkbutton(f, text=label, variable=v,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(anchor="w", padx=24, pady=2)

        tk.Label(f, text=_i18n.t("set.thresholds_1f41"), font=("Helvetica", 11, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", padx=16)

        def _spin_row(parent, label, varname, default, from_, to_):
            r = tk.Frame(parent, bg="#1e1e2e"); r.pack(anchor="w", padx=24, pady=2)
            tk.Label(r, text=label, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                     width=max(36, len(label) + 3), anchor="w").pack(side="left")      # v0.20.0 UI1e: PT / ES are longer
            v = tk.IntVar(value=self._s.get(varname, default))
            setattr(self, f"_{varname}_var", v)
            tk.Spinbox(r, from_=from_, to=to_, textvariable=v, width=6,
                       font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                       buttonbackground="#45475a", relief="flat").pack(side="left")
            return v

        _spin_row(f, _i18n.t("set.max_nfo_file_size_0216"), "max_nfo_kb",  50, 1, 9999)
        _spin_row(f, _i18n.t("set.max_xml_file_size_c4b6"), "max_xml_kb",  25, 1, 9999)
        # min_backdrops removed from UI in v0.18.2 — now lives in Health Rules tab ### MODIFIED_BY_CLAUDE_v18.2 ###

    # ── Tab 5: Image Sizes ────────────────────────────────────────────────────

    def _build_artwork_language_section(self, f):                ### NEW v0.20.1 TF3 ###
        """Settings → Images & Artwork → Artwork language: language, Prefer / Only, textless backgrounds first."""
        import artwork_online as _ao
        self._section(f, _i18n.t("art.section"))
        lib_iso = str(self._s.get("lang_ok_code", "EN") or "EN")
        codes = ["library"] + [c for c, _n in _ao.LANGUAGES]
        cur = self._s.get("artwork_language", "library") or "library"
        if cur not in codes:
            codes.append(cur)
        self._art_lang_var = tk.StringVar(value=cur)
        r = self._row(f)
        tk.Label(r, text=_i18n.t("art.language"), bg="#1e1e2e", fg="#cdd6f4", width=36, anchor="w").pack(side="left")
        shown_combo(r, self._art_lang_var, codes,
                    lambda c: (_i18n.t("art.lang_library", name=_ao.language_name(lib_iso)) if c == "library"
                               else f"{_ao.language_name(c)} ({c})"),
                    state="readonly", width=40).pack(side="left", padx=(8, 0))
        self._art_mode_var = tk.StringVar(value=_ao.settings_mode(self._s))
        r2 = self._row(f)
        tk.Label(r2, text=_i18n.t("art.mode"), bg="#1e1e2e", fg="#cdd6f4", width=36, anchor="w").pack(side="left")
        for code in ("prefer", "only"):
            tk.Radiobutton(r2, text=_i18n.t("art.mode." + code), variable=self._art_mode_var, value=code, bg="#1e1e2e",
                           fg="#cdd6f4", selectcolor="#313244", activebackground="#1e1e2e").pack(side="left", padx=(8, 0))
        self._art_textless_var = tk.BooleanVar(value=_ao.settings_textless(self._s))
        r3 = self._row(f)
        tk.Checkbutton(r3, text=_i18n.t("art.textless"), variable=self._art_textless_var, bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e").pack(side="left")
        tk.Label(f, text=_i18n.t("art.hint"), bg="#1e1e2e", fg="#a6adc8", font=("Helvetica", 8), justify="left",
                 wraplength=640).pack(anchor="w", padx=16, pady=(2, 8))
        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(0, 4))

    def _build_image_sizes_tab(self, nb, label="Image Sizes"):
        """Image quality and proportion settings.          ### NEW v0.11.0 ###"""

        f = self._scrollable_tab(nb, label)                    ### MODIFIED v0.18.4 ###
        self._build_artwork_language_section(f)                 ### NEW v0.20.1 TF3 — at the top: the most used choice ###

        # ── Proportion Checks ─────────────────────────────────────────────────
        self._section(f, _i18n.t("set.proportion_checks_8879"))

        ### NEW v0.12.0 — poster/folder 3:4 acceptance toggle (above fanart 16:8) ###
        r_34 = self._row(f)
        tk.Label(r_34, text=_i18n.t("set.accept_poster_jpg_and_d329"),
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=50, anchor="w").pack(side="left")
        self._poster_34_var = tk.StringVar(
            value="Yes" if self._s.get("poster_accept_34", False) else "No")
        poster_34_cb = shown_combo(r_34, self._poster_34_var, ["Yes", "No"], _YESNO, state="readonly",   # v0.20.0 UI1d
                                    width=6, font=("Helvetica", 10))
        poster_34_cb.pack(side="left", padx=(8, 0))
        poster_34_cb.bind("<<ComboboxSelected>>", self._update_proportion_text)

        # Fanart 16:8 acceptance toggle
        r0 = self._row(f)
        tk.Label(r0, text=_i18n.t("set.accept_fanart_jpg_also_e829"),
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=50, anchor="w").pack(side="left")
        self._fanart_168_var = tk.StringVar(
            value="Yes" if self._s.get("fanart_accept_168", False) else "No")
        fanart_168_cb = shown_combo(r0, self._fanart_168_var, ["Yes", "No"], _YESNO, state="readonly",   # v0.20.0 UI1d
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
        self._section(f, _i18n.t("set.minimum_image_quality_resolution_39e8"))
        self._note(f,                                             ### MODIFIED v0.19.0 ###
            _i18n.t("set.choose_the_minimum_acceptable_af0c"))

        # ──────────── Poster / Folder ─────────────────────────────────────────
        tk.Label(f, text=_i18n.t("set.poster_folder_portrait_ratio_07ee"),
                 font=("Helvetica", 10, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(10, 2))

        poster_tiers = [t[0] for t in self._poster_tiers]
        # Info table for poster
        hdr_f = tk.Frame(f, bg="#1e1e2e"); hdr_f.pack(anchor="w", padx=24)
        for col, w in [(_i18n.t("set.tbl.quality"), 18), (_i18n.t("set.tbl.resolution"), 14), (_i18n.t("set.tbl.pixels"), 14), (_i18n.t("set.tbl.size"), 16)]:
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
        tk.Label(r1, text=_i18n.t("set.minimum_quality_poster_jpg_1dea"),
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=36, anchor="w").pack(side="left")
        _hr_now = self._s.get("health_rules") or {}                ### NEW v0.19.0 — Health Rules are authoritative ###
        self._poster_ql_var = tk.StringVar(
            value=_hr_now.get("poster_folder_quality_level") or self._s.get("poster_quality_level", "1080p"))
        ttk.Combobox(r1, textvariable=self._poster_ql_var,
                     values=poster_tiers, state="readonly",
                     width=18, font=("Helvetica", 10)).pack(side="left", padx=(8, 0))

        r2 = self._row(f)
        tk.Label(r2, text=_i18n.t("set.minimum_quality_folder_jpg_a8f9"),
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=36, anchor="w").pack(side="left")
        self._folder_ql_var = tk.StringVar(                         ### MODIFIED v0.19.0 — same value as poster ###
            value=_hr_now.get("poster_folder_quality_level") or self._s.get("folder_quality_level", "1080p"))
        ttk.Combobox(r2, textvariable=self._folder_ql_var,
                     values=poster_tiers, state="readonly",
                     width=18, font=("Helvetica", 10)).pack(side="left", padx=(8, 0))

        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(10, 4))

        # ──────────── Fanart ──────────────────────────────────────────────────
        tk.Label(f, text=_i18n.t("set.fanart_or_landscape_ratio_add3"),
                 font=("Helvetica", 10, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(10, 2))

        fanart_tiers = [t[0] for t in self._fanart_tiers]
        hdr_f2 = tk.Frame(f, bg="#1e1e2e"); hdr_f2.pack(anchor="w", padx=24)
        for col, w in [(_i18n.t("set.tbl.quality"), 22), (_i18n.t("set.tbl.resolution"), 14), (_i18n.t("set.tbl.pixels"), 14), (_i18n.t("set.tbl.size"), 16)]:
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
        tk.Label(r3, text=_i18n.t("set.minimum_quality_fanart_jpg_045c"),
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=36, anchor="w").pack(side="left")
        self._fanart_ql_var = tk.StringVar(                         ### MODIFIED v0.19.0 — mirrors Health Rules ###
            value=_hr_now.get("fanart_quality_level_minimum") or self._s.get("fanart_quality_level", "1080p"))
        ttk.Combobox(r3, textvariable=self._fanart_ql_var,
                     values=fanart_tiers, state="readonly",
                     width=18, font=("Helvetica", 10)).pack(side="left", padx=(8, 0))

        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(10, 4))

        # ── Legacy KB minimums (kept for additional safety net) ───────────────
        self._section(f, _i18n.t("set.legacy_file_size_minimums_043a"))
        self._note(f,
            _i18n.t("set.secondary_check_files_below_0ccc"))

        def _sz_row(parent, label, varname, default):
            r = tk.Frame(parent, bg="#1e1e2e"); r.pack(anchor="w", padx=24, pady=2)
            tk.Label(r, text=label, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                     width=max(34, len(label) + 3), anchor="w").pack(side="left")      # v0.20.0 UI1e
            v = tk.IntVar(value=self._s.get(varname, default))
            setattr(self, f"_{varname}_var", v)
            tk.Spinbox(r, from_=0, to=9999, textvariable=v, width=6,
                       font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                       buttonbackground="#45475a", relief="flat").pack(side="left")
            tk.Label(r, text=_i18n.t("set.kb_skip_check_86c6"), font=("Helvetica", 9),
                     bg="#1e1e2e", fg="#6c7086").pack(side="left", padx=(6, 0))

        _sz_row(f, _i18n.t("set.poster_jpg_minimum_size_bb70"), "min_poster_kb", 100)
        _sz_row(f, _i18n.t("set.folder_jpg_minimum_size_e524"), "min_folder_kb", 100)
        _sz_row(f, _i18n.t("set.fanart_jpg_minimum_size_e282"), "min_fanart_kb", 200)

    def _bind_quality_mirrors(self):                               ### NEW v0.19.0 ###
        """One minimum-quality setting shown in two tabs: the Image Sizes
        combos (_poster_ql_var, _folder_ql_var, _fanart_ql_var) and the Health
        Rules combos (_hr_str_vars['poster_folder_quality_level'] /
        ['fanart_quality_level_minimum']).  Any change is copied to the others;
        the equality guard prevents trace recursion."""
        hr = getattr(self, "_hr_str_vars", {})
        groups = [
            [v for v in (getattr(self, "_poster_ql_var", None),
                         getattr(self, "_folder_ql_var", None),
                         hr.get("poster_folder_quality_level")) if v is not None],
            [v for v in (getattr(self, "_fanart_ql_var", None),
                         hr.get("fanart_quality_level_minimum")) if v is not None],
        ]
        for group in groups:
            if len(group) < 2:
                continue
            master = group[-1].get() if group[-1].get() else group[0].get()
            for v in group:
                if v.get() != master:
                    v.set(master)
            def _make(src, others):
                def _sync(*_):
                    val = src.get()
                    for o in others:
                        if o.get() != val:
                            o.set(val)
                return _sync
            for v in group:
                v.trace_add("write", _make(v, [o for o in group if o is not v]))

    def _update_proportion_text(self, *_):
        """Update the dynamic proportion description based on both toggles.
        ### NEW v0.12.0 — 4 combinations based on fanart_accept_168 and poster_accept_34 ###
        """
        accept_168 = (self._fanart_168_var.get() == "Yes")
        accept_34  = (getattr(self, "_poster_34_var", None) and
                      self._poster_34_var.get() == "Yes")

        if not accept_168 and not accept_34:
            text = (
                _i18n.t("set.wrong_proportions_are_flagged_753e")
            )
        elif accept_168 and not accept_34:
            text = (
                _i18n.t("set.wrong_proportions_are_flagged_e99f")
            )
        elif not accept_168 and accept_34:
            text = (
                _i18n.t("set.wrong_proportions_are_flagged_b9c0")
            )
        else:  # both Yes
            text = (
                _i18n.t("set.wrong_proportions_are_flagged_daa4")
            )
        self._prop_text_var.set(text)

    # ── Tab 6: Genres ─────────────────────────────────────────────────────────
    # ── Tab 10: Ratings ─────────────────────────────────────────────────────── ### NEW v0.15.0 ###
    def _build_ratings_tab(self, nb, label="Ratings"):           ### NEW v0.15.0 ###
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=tab_title(label))   ### NEW v0.15.0 ###
                                                                  ### NEW v0.15.0 ###
        tk.Label(f, text=_i18n.t("set.ratings_synchronization_options_b8b3"),      ### NEW v0.15.0 ###
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa" ### NEW v0.15.0 ###
                 ).pack(anchor="w", padx=16, pady=(16, 6))       ### NEW v0.15.0 ###
                                                                  ### NEW v0.15.0 ###
        tk.Label(f, text=_i18n.t("set.these_settings_control_the_16aa"), ### NEW v0.15.0 ###
                 bg="#1e1e2e", fg="#a6adc8", font=("Helvetica", 9) ### NEW v0.15.0 ###
                 ).pack(anchor="w", padx=16, pady=(0, 12))       ### NEW v0.15.0 ###
                                                                  ### NEW v0.15.0 ###
        apply_val = self._s.get("rating_apply_all_movies",       ### NEW v0.15.0 ###
                                 self._defaults.get("rating_apply_all_movies", False)) ### NEW v0.15.0 ###
        self._rating_apply_all_var = tk.BooleanVar(value=apply_val) ### NEW v0.15.0 ###
        tk.Checkbutton(f, text=_i18n.t("set.apply_this_choice_to_0a3e"), ### NEW v0.15.0 ###
                       variable=self._rating_apply_all_var,      ### NEW v0.15.0 ###
                       bg="#1e1e2e", fg="#cdd6f4", activebackground="#1e1e2e", ### NEW v0.15.0 ###
                       selectcolor="#313244", font=("Helvetica", 10) ### NEW v0.15.0 ###
                       ).pack(anchor="w", padx=16, pady=(0, 6))  ### NEW v0.15.0 ###
                                                                  ### NEW v0.15.0 ###
        votes_val = self._s.get("rating_use_more_votes",         ### NEW v0.15.0 ###
                                 self._defaults.get("rating_use_more_votes", False)) ### NEW v0.15.0 ###
        self._rating_use_more_votes_var = tk.BooleanVar(value=votes_val) ### NEW v0.15.0 ###
        tk.Checkbutton(f, text=_i18n.t("set.use_the_source_with_5be2"), ### NEW v0.15.0 ###
                       variable=self._rating_use_more_votes_var, ### NEW v0.15.0 ###
                       bg="#1e1e2e", fg="#cdd6f4", activebackground="#1e1e2e", ### NEW v0.15.0 ###
                       selectcolor="#313244", font=("Helvetica", 10) ### NEW v0.15.0 ###
                       ).pack(anchor="w", padx=16, pady=(0, 6))  ### NEW v0.15.0 ###


    def _build_genres_tab(self, nb, label="Genres"):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=tab_title(label))

        self._section(f, _i18n.t("set.standard_genre_list_79c8"))
        self._note(f, _i18n.t("set.one_genre_per_line_5242"))

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
        tk.Button(br, text=_i18n.t("set.reset_to_tmdb_defaults_f247"), font=("Helvetica", 9),
                  bg="#45475a", fg="#f38ba8", relief="flat", cursor="hand2",
                  command=self._reset_genres).pack(side="left")

    def _reset_genres(self):
        self._genres_text.delete("1.0", "end")
        self._genres_text.insert("1.0", self._defaults.get("genre_list", ""))  ### FIX v0.15.0 ###

    # ── Tab 7: NFO-XML Tags ───────────────────────────────────────────────────

    def _build_tags_tab(self, nb, label="NFO / XML"):
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=tab_title(label))

        # v0.19.6 TR1b — whether movie.xml is used at all is the health mode (Health Rules tab)
        tk.Label(f, text=_i18n.t("set.movie_xml_is_used_239c", health_mode_path=HEALTH_MODE_PATH),
                 font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086", justify="left").pack(anchor="w", padx=16, pady=(12, 0))

        tk.Label(f, text=_i18n.t("set.nfo_xml_tag_comparison_4720"),
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(f, text=_i18n.t("set.format_nfo_tag_xml_e87f"),
                 font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086",
                 justify="left").pack(anchor="w", padx=16, pady=(0, 8))

        fr = tk.Frame(f, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(0, 4))
        self._tags_text = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4",   # v0.20.1 SN2: was "none"
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
        self._tags_reset_btn = tk.Button(br, text=_i18n.t("set.reset_to_defaults_21e2"), font=("Helvetica", 9),
                  bg="#45475a", fg="#f38ba8", relief="flat", cursor="hand2",
                  command=self._reset_tags)
        self._tags_reset_btn.pack(side="left")
        self._tags_note = tk.Label(br, text="", font=("Helvetica", 9, "italic"), bg="#1e1e2e", fg="#f9e2af")   # v0.19.6 TR1c
        self._tags_note.pack(side="left", padx=12)

        # ── NEW v0.19.4 B110g — Collections: Kodi's movie set information folder ──
        tk.Label(f, text=_i18n.t("set.collections_a9fc"), font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(10, 2))
        cr_ = tk.Frame(f, bg="#1e1e2e"); cr_.pack(fill="x", padx=16)
        tk.Label(cr_, text=_i18n.t("set.collection_folder_583e"), font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        ### MODIFIED v0.20.0 CF1 — shown here, set in the Libraries window (the user, 2026-11-15) ###
        self._coll_folder_var = tk.StringVar(value=self._s.get("collection_folder", ""))
        self._coll_folder_lbl = tk.Label(cr_, text="", font=("Consolas", 9), bg="#313244", fg="#cdd6f4", anchor="w", padx=6)
        self._coll_folder_lbl.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=3)
        tk.Button(cr_, text=_i18n.t("cf.libraries_btn"), font=("Helvetica", 9), bg="#45475a", fg="#cdd6f4", relief="flat",
                  cursor="hand2", command=self._open_libraries_for_collections).pack(side="left", padx=(6, 0))
        tk.Label(f, text=_i18n.t("cf.set_in_lib"), font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086", wraplength=720,
                 justify="left").pack(anchor="w", padx=16, pady=(2, 4))
        self._coll_folder_var.trace_add("write", lambda *_: self._show_coll_folder())
        self._show_coll_folder()
        self._group_coll_var = tk.BooleanVar(value=bool(self._s.get("group_by_collection", False)))   # NEW v0.19.4 B110h
        tk.Checkbutton(f, text=_i18n.t("set.group_the_movie_table_9afd"),
                       variable=self._group_coll_var, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e", activeforeground="#cdd6f4",
                       command=self._group_coll_ticked).pack(anchor="w", padx=12, pady=(0, 4))
        # ── NEW v0.19.4 P4 — the collection name's language ──
        lr_ = tk.Frame(f, bg="#1e1e2e"); lr_.pack(fill="x", padx=16, pady=(0, 2))
        tk.Label(lr_, text=_i18n.t("set.collection_name_language_e44d"), font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self._coll_lang_codes = ["auto", "en", "pt", "es", "fr", "de", "it", "nl", "sv", "pl", "tr", "ja", "ko", "zh", "ru"]
        _coll_lang_names = [lang_name(c, c) for c in self._coll_lang_codes]   # v0.20.0 UI1d: shown names; the code is saved
        self._coll_lang_names = _coll_lang_names
        _cur = str(self._s.get("collection_name_lang") or "auto").split("-")[0].lower()
        self._coll_lang_var = tk.StringVar(value=_coll_lang_names[self._coll_lang_codes.index(_cur)]
                                           if _cur in self._coll_lang_codes else _coll_lang_names[0])
        ttk.Combobox(lr_, textvariable=self._coll_lang_var, values=_coll_lang_names, state="readonly",
                     width=16).pack(side="left", padx=(8, 0))
        tk.Label(f, text=_i18n.t("set.automatic_the_english_name_2a6c"),
                 font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086", wraplength=720, justify="left"
                 ).pack(anchor="w", padx=16, pady=(0, 10))

    def _reset_tags(self):
        self._tags_text.delete("1.0", "end")
        lines = [f"{nfo_p}\t{xml_p}\t{label}\t{tol}"
                 for nfo_p, xml_p, label, tol in self._tag_pairs_default]
        self._tags_text.insert("1.0", "\n".join(lines))

    def _parse_tags_text(self):
        raw = self._tags_text.get("1.0", "end").strip()
        pairs = []
        for n, line in enumerate(raw.splitlines(), 1):                ### n: v0.19.4 B94 ###
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = re.split(r'\t|  +', line)
            if len(parts) >= 2:
                nfo_p = parts[0].strip()
                xml_p = parts[1].strip()
                label = parts[2].strip() if len(parts) > 2 else nfo_p
                try:                                                    ### NEW v0.19.4 B94b — the bad line is named ###
                    tol = int(parts[3].strip()) if len(parts) > 3 else 0
                except ValueError:
                    raise SettingsFieldError(
                        "Tag pairs", self._tags_text,
                        f"line {n}: the tolerance '{parts[3].strip()}' is not a whole number") from None
                pairs.append((nfo_p, xml_p, label, tol))
        return pairs if pairs else None

    # ── Tab 8: User Interface  (v0.12.0)  ─────────────────────────────────────

    def _build_ui_prefs_tab(self, nb, label="User Interface"):
        """User Interface preferences tab — v0.12.0 replacement."""  ### NEW v0.12.0 ###
        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=tab_title(label))

        tk.Label(f, text=_i18n.t("set.user_interface_settings_69c7"),
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16, 4))

        self._build_ui_language_box(f)                              ### NEW v0.20.0 UI1a ###

        # ── Show image size? ──────────────────────────────────────────────────
        self._section(f, _i18n.t("set.compact_mode_e9d2"))
        self._note(f, _i18n.t("set.when_yes_reduces_vertical_7752"))
        r2 = self._row(f)
        tk.Label(r2, text=_i18n.t("set.enable_compact_mode_bb2b"), font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#cdd6f4", width=28, anchor="w").pack(side="left")
        self._compact_mode_var = tk.BooleanVar(value=self._s.get("compact_mode", False))
        for val, lbl in [(True, _i18n.t("set.opt.yes")), (False, _i18n.t("set.opt.no"))]:
            tk.Radiobutton(r2, text=lbl, variable=self._compact_mode_var, value=val,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(side="left", padx=(0, 12))

        # ── Enable dark theme? ────────────────────────────────────────────────
        self._section(f, _i18n.t("set.right_click_menu_f16e"))
        self._note(f, _i18n.t("set.repeat_runs_the_last_0200"))
        r4b = self._row(f)
        self._ctx_repeat_var = tk.BooleanVar(value=bool(self._s.get("ctx_repeat_last", True)))   ### NEW v0.19.2 B57 ###
        tk.Checkbutton(r4b, text=_i18n.t("set.show_repeat_last_action_b2eb"),
                       variable=self._ctx_repeat_var, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left")

        # ── Title bars (v0.19.2 B51) ─────────────────────────────────────────
        self._section(f, _i18n.t("set.title_bars_b397"))
        self._note(f, _i18n.t("set.windows_draws_title_bars_daaf"))
        r4d = self._row(f)
        self._dark_title_var = tk.BooleanVar(value=bool(self._s.get("dark_title_bar", True)))   ### NEW v0.19.2 B51 ###
        tk.Checkbutton(r4d, text=_i18n.t("set.dark_title_bars_applied_2e15"),
                       variable=self._dark_title_var, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left")

        # ── Updates (v0.19.2 B50) ────────────────────────────────────────────
        self._section(f, _i18n.t("set.updates_9ac4"))
        self._note(f, _i18n.t("set.asks_github_for_the_2360"))
        r4e = self._row(f)
        self._check_updates_var = tk.BooleanVar(value=bool(self._s.get("check_updates", False)))   ### NEW v0.19.2 B50 ###
        tk.Checkbutton(r4e, text=_i18n.t("set.check_for_updates_at_2954"),
                       variable=self._check_updates_var, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left")

        # ── Ignored folders (v0.19.2 B53) ────────────────────────────────────
        self._section(f, _i18n.t("set.ignored_folders_70f8"))
        self._note(f, _i18n.t("set.folders_that_are_not_8d94"))
        r4c = self._row(f)
        self._scan_ignored_report_var = tk.BooleanVar(value=bool(self._s.get("scan_ignored_report", True)))   ### NEW v0.19.2 B53 ###
        tk.Checkbutton(r4c, text=_i18n.t("set.show_the_ignored_folders_ab4e"),
                       variable=self._scan_ignored_report_var, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left")

        # ── Alternating rows (kept from v0.11) ────────────────────────────────
        self._section(f, _i18n.t("set.table_appearance_ae18"))
        self._note(f, _i18n.t("set.alternating_row_colors_make_7fb1"))
        r5 = self._row(f)
        self._alt_rows_var = tk.BooleanVar(value=self._s.get("alternating_rows", True))
        tk.Checkbutton(r5, text=_i18n.t("set.alternating_row_colors_eecd"),
                       variable=self._alt_rows_var,
                       font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left")

        r6 = self._row(f)
        self._show_header_tips_var = tk.BooleanVar(value=self._s.get("show_header_tips", True))
        tk.Checkbutton(r6, text=_i18n.t("set.show_column_header_tooltips_d41c"),
                       variable=self._show_header_tips_var,
                       font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(side="left")

    # ── v0.20.0 UI1a: Interface language (saved at once, used from the next start) ──
    def ui_language_options(self, windows_code=None):
        """[(stored code or "", shown label)]: "Same as Windows (…)" first, then each language in its own name."""
        wc = windows_code or getattr(self._parent, "_windows_ui_code", None) or "en"
        same = _i18n.t("ui.lang.same_as_windows", name=_i18n.LANGUAGE_NAMES.get(wc, "English"))
        return [("", same)] + [(c, _i18n.LANGUAGE_NAMES[c]) for c in _i18n.LANGUAGES]

    def _build_ui_language_box(self, f):                            ### NEW v0.20.0 UI1a ###
        self._section(f, _i18n.t("set.interface_language_11e2"))
        r = self._row(f)
        tk.Label(r, text=_i18n.t("ui.lang.label"), font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=28, anchor="w").pack(side="left")
        opts = self.ui_language_options()
        stored = self._s.get("ui_language")
        cur = stored if isinstance(stored, str) and stored in _i18n.CATALOGS else ""   # v0.20.0 RV1
        self._ui_language_codes = [c for c, _l in opts]
        self._ui_language_var = tk.StringVar(value=dict(opts)[cur])
        cb = ttk.Combobox(r, textvariable=self._ui_language_var, values=[l for _c, l in opts], state="readonly",
                          width=30, font=("Helvetica", 10))
        cb.pack(side="left")
        self._ui_language_combo = cb
        r2 = self._row(f)
        self._ui_language_note = tk.Label(r2, text=_i18n.t("ui.lang.next_start"), font=("Helvetica", 9, "italic"),
                                          bg="#1e1e2e", fg="#a6adc8")
        self._ui_language_note.pack(side="left")
        self._ui_restart_btn = tk.Button(r2, text=f"  {_i18n.t('ui.lang.restart_now')}  ", font=("Helvetica", 9, "bold"),
                                         bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                                         command=self._ui_restart_now)
        self._ui_restart_btn.pack(side="left", padx=(10, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: self._ui_language_picked())

    def _ui_language_picked(self):                                  ### NEW v0.20.0 UI1a ###
        """Store the choice at once (the B36 atomic save); "Same as Windows" removes the key. Not an unsaved
        change for B44's discard question."""
        labels = list(self._ui_language_combo.cget("values"))
        try:
            code = self._ui_language_codes[labels.index(self._ui_language_var.get())]
        except ValueError:
            return None
        if code:
            self._s["ui_language"] = code
        else:
            self._s.pop("ui_language", None)
        save = (self._ctx.save_settings if self._ctx and getattr(self._ctx, "save_settings", None) else _save_settings_fn)
        try:
            if save:
                save(self._s)
        except Exception:
            pass
        snap = getattr(self, "_widget_snapshot", None)
        if snap is not None and "_ui_language_var" in snap:
            snap["_ui_language_var"] = self._ui_language_var.get()
        return code

    def _ui_restart_now(self):                                      ### NEW v0.20.0 UI1a ###
        fn = getattr(self._parent, "_restart_now", None)
        if callable(fn):
            return fn()
        return False

    # ── Tab 10: Health Rules  (v0.18.2) ─────────────────────────────────────── ### ADDED_BY_CLAUDE_v18.2 ###

    def _build_health_rules_tab(self, nb, label="Health Rules"):
        """Configurable health rule engine tab."""
        from settings_model import DEFAULT_SETTINGS

        f = self._scrollable_tab(nb, label)                    ### MODIFIED v0.18.4 ###

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

        # ── NEW v0.19.6 TR1b — Health mode (first: it decides which files the rules below look at) ──
        # ### MODIFIED v0.20.0 F3a-2 (the user's mock-up A, 2026-11-16) ### the programs as tick boxes replace the three
        # health-mode buttons: the ticks set the health mode (media_profiles.health_mode_for); nothing ticked keeps the
        # mode as it was.  _health_mode_var stays the one state the sections, the preset and Save read.
        import media_profiles as _mpf
        _section(_i18n.t("f3.title"))
        self._health_mode_initial = health_mode_of(self._s)
        self._health_mode_var = tk.StringVar(value=self._health_mode_initial)
        _have = set(_mpf.clean_programs(self._s.get("media_programs") or ()))
        self._program_vars = {p: tk.BooleanVar(value=p in _have) for p in _mpf.PROGRAMS}
        self._programs_initial = _mpf.clean_programs(_have)
        _pg = tk.Frame(f, bg="#1e1e2e")
        _pg.pack(anchor="w", padx=22, pady=(2, 0))
        for _i, _p in enumerate(_mpf.PROGRAMS):
            tk.Checkbutton(_pg, text=_mpf.PROGRAM_LABEL[_p], variable=self._program_vars[_p],
                           command=self._programs_changed, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e", activeforeground="#cdd6f4"
                           ).grid(row=_i // 4, column=_i % 4, columnspan=1 if _i < 4 else 2, sticky="w", padx=(0, 18))
        self._programs_info = tk.Label(f, text="", font=("Helvetica", 10), bg="#1e1e2e", fg="#a6e3a1", justify="left")
        self._programs_info.pack(anchor="w", padx=42, pady=(4, 0))
        tk.Label(f, text=_i18n.t("f3.note"), font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086",
                 justify="left").pack(anchor="w", padx=42, pady=(2, 4))
        # ### NEW v0.20.0 6h ### Plex reads no NFO: with only Plex ticked, its NFO / collection checks (asked once)
        self._plex_nfo_initial = self._s.get("plex_nfo_checks") or ""
        self._plex_nfo_var = tk.BooleanVar(value=self._plex_nfo_initial != "off")
        self._plex_nfo_cb = tk.Checkbutton(f, text=_i18n.t("px.set"), variable=self._plex_nfo_var, font=("Helvetica", 10),
                       bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4", disabledforeground="#6c7086")
        self._plex_nfo_cb.pack(anchor="w", padx=38, pady=(0, 4))
        self._health_mode_var.trace_add("write", lambda *_: self._programs_info_update())
        self._programs_info_update()

        # ── NEW v0.20.0 HP1d — Health preset (how strict): sets every rule below at once; "Custom" after a manual change.
        # What is shown always comes from the rule values (matching_health_preset), so it cannot drift from them.
        import settings_model as _smp
        _section(_i18n.t("hp.title"))
        self._health_preset_var = tk.StringVar(value=_smp.matching_health_preset(hr_current, self._health_mode_initial))
        self._hp_last, self._hp_busy = [self._health_preset_var.get()], [False]
        for _pid in ("easy", "medium", "tight", "custom"):
            tk.Radiobutton(f, text=f"{_i18n.t('hp.' + _pid)}   —   {_i18n.t('hp.' + _pid + '.d')}", value=_pid,
                           variable=self._health_preset_var, command=lambda p=_pid: self._health_preset_chosen(p),
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244",
                           activebackground="#1e1e2e", activeforeground="#cdd6f4").pack(anchor="w", padx=22, pady=1)

        # ── v0.19.6 TR1c: the current section and level (the rows below pack into it) ──
        self._hr_sections = {}
        _cur, _sec, _lvl = [f], [None], ["warning"]

        def _level_tag(row, key):
            if _sec[0]:
                self._hr_sections[_sec[0]]["keys"].append(key)
            tk.Label(row, text=_i18n.t("set.lvl." + _lvl[0]), font=("Helvetica", 9), bg="#1e1e2e",
                     fg="#f38ba8" if _lvl[0] == "error" else "#f9e2af").pack(side="right", padx=(8, 24))

        # ── Helper: plain checkbox row ─────────────────────────────────────────
        def _check_row(key, label_text):
            _row = tk.Frame(_cur[0], bg="#1e1e2e"); _row.pack(fill="x", padx=22, pady=1)   # v0.19.6 TR1c
            val = hr_current.get(key, hr_defaults.get(key, True))
            v   = tk.BooleanVar(value=val)
            self._hr_vars[key] = v
            _level_tag(_row, key)
            tk.Checkbutton(_row, text=label_text, variable=v,
                           font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                           selectcolor="#313244", activebackground="#1e1e2e",
                           activeforeground="#cdd6f4").pack(side="left")
            return v

        # ── Helper: checkbox + inline combobox ────────────────────────────────
        def _check_combo_row(bool_key, str_key, label_text, values, default_str,
                             combo_width=12):
            row = tk.Frame(_cur[0], bg="#1e1e2e"); row.pack(fill="x", padx=22, pady=1)
            b_val = hr_current.get(bool_key, hr_defaults.get(bool_key, True))
            bv    = tk.BooleanVar(value=b_val)
            self._hr_vars[bool_key] = bv
            _level_tag(row, bool_key)
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
            row = tk.Frame(_cur[0], bg="#1e1e2e"); row.pack(fill="x", padx=22, pady=1)
            b_val = hr_current.get(bool_key, hr_defaults.get(bool_key, True))
            bv    = tk.BooleanVar(value=b_val)
            self._hr_vars[bool_key] = bv
            _level_tag(row, bool_key)
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
            row = tk.Frame(_cur[0], bg="#1e1e2e"); row.pack(fill="x", padx=22, pady=1)
            b_val = hr_current.get(bool_key, hr_defaults.get(bool_key, True))
            bv    = tk.BooleanVar(value=b_val)
            self._hr_vars[bool_key] = bv
            _level_tag(row, bool_key)
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
            row = tk.Frame(_cur[0], bg="#1e1e2e"); row.pack(fill="x", padx=22, pady=1)
            b_val = hr_current.get(bool_key, hr_defaults.get(bool_key, True))
            bv    = tk.BooleanVar(value=b_val)
            self._hr_vars[bool_key] = bv
            _level_tag(row, bool_key)
            s_val = hr_current.get(str_key, hr_defaults.get(str_key, default_code))
            sv    = tk.StringVar(value=s_val)
            self._hr_str_vars[str_key] = sv
            cb = tk.Checkbutton(row, text=label_text, variable=bv,
                                font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                                selectcolor="#313244", activebackground="#1e1e2e",
                                activeforeground="#cdd6f4")
            cb.pack(side="left")
            codes   = [code for code, _ in lang_list]
            names   = {code: lang_name(_ISO3.get(code, code), name) for code, name in lang_list}   # v0.20.0 UI1d
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

        # ── Helper: severity combobox (error / warning / off) ─── ### NEW v0.19.1 B24 ###
        def _level_row(str_key, label_text, default_str):
            row = tk.Frame(_cur[0], bg="#1e1e2e"); row.pack(fill="x", padx=22, pady=1)
            s_val = hr_current.get(str_key, hr_defaults.get(str_key, default_str))
            if s_val not in ("error", "warning", "off"):
                s_val = default_str
            sv = tk.StringVar(value=s_val)
            self._hr_str_vars[str_key] = sv
            _sec[0] and self._hr_sections[_sec[0]]["keys"].append(str_key)
            tk.Label(row, text=label_text, font=("Helvetica", 10), bg="#1e1e2e",
                     fg="#cdd6f4").pack(side="left")
            shown_combo(row, sv, ["error", "warning", "off"], lambda c: _i18n.t("set.lvl." + c),   # v0.20.0 UI1d
                        state="readonly", width=12, font=("Helvetica", 10)).pack(side="left", padx=(6, 0))
            return sv

        # ── Helper: one value from a short list, shown by label ── ### NEW v0.19.3 B60 ###
        def _choice_row(str_key, label_text, options, default_str, width=18):   # width: v0.20.0 RD12
            row = tk.Frame(_cur[0], bg="#1e1e2e"); row.pack(fill="x", padx=22, pady=1)
            keys = [k for k, _l in options]
            s_val = hr_current.get(str_key, hr_defaults.get(str_key, default_str))
            if s_val not in keys:
                s_val = default_str
            sv = tk.StringVar(value=s_val)                 # the stored value ("nfo" …)
            self._hr_str_vars[str_key] = sv
            _sec[0] and self._hr_sections[_sec[0]]["keys"].append(str_key)
            shown = tk.StringVar(value=dict(options)[s_val])
            tk.Label(row, text=label_text, font=("Helvetica", 10), bg="#1e1e2e",
                     fg="#cdd6f4").pack(side="left")
            cb = ttk.Combobox(row, textvariable=shown, values=[l for _k, l in options],
                              state="readonly", width=width, font=("Helvetica", 10))
            cb.pack(side="left", padx=(6, 0))
            cb.bind("<<ComboboxSelected>>", lambda e: sv.set(keys[[l for _k, l in options].index(shown.get())]))
            sv.trace_add("write", lambda *_: shown.set(dict(options).get(sv.get(), shown.get())))
            return sv

        # ── Intro and reset button ─────────────────────────────────────────────
        tk.Label(f, text=_i18n.t("set.health_rules_control_which_5d03"),
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

        tk.Button(f, text=_i18n.t("set.reset_to_defaults_eba1"),
                  font=("Helvetica", 9, "bold"), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2",
                  command=_reset_defaults).pack(anchor="w", padx=14, pady=(0, 8))

        # ── v0.19.6 TR1c: four sections by file; a rule line names its level (error / warning) ──
        def _rules_section(sec):
            sid, title, _modes, which = next(s for s in HEALTH_RULE_SECTIONS if s[0] == sec)
            box = tk.Frame(f, bg="#1e1e2e"); box.pack(fill="x")
            tk.Frame(box, bg="#45475a", height=1).pack(fill="x", padx=12, pady=(12, 0))
            head = tk.Frame(box, bg="#1e1e2e"); head.pack(fill="x")
            tk.Label(head, text=title, font=("Helvetica", 11, "bold"), bg="#1e1e2e", fg="#89b4fa").pack(side="left", padx=14, pady=(4, 2))
            tk.Label(head, text=f"({which})", font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086").pack(side="right", padx=24)
            note = tk.Label(box, text="", font=("Helvetica", 9, "italic"), bg="#1e1e2e", fg="#f9e2af", justify="left")
            self._hr_sections[sec] = {"frame": box, "note": note, "head": head, "keys": []}   # the note is packed only when grayed
            _cur[0] = box
            _sec[0] = sec

        def _level(lv):
            _lvl[0] = lv

        def _sub(title):                                        ### NEW v0.19.6 TR1d — a topic inside a section ###
            tk.Label(_cur[0], text=title, font=("Helvetica", 10, "bold"), bg="#1e1e2e",
                     fg="#fab387").pack(anchor="w", padx=18, pady=(10, 1))

        _rules_section("general")
        _sub(_i18n.t("set.video_and_audio_02d4"))                                    # v0.19.6 TR1d
        _level("error")
        _check_row("missing_video_file", _i18n.t("set.missing_video_file_f2dc"))
        _check_row("no_audio_tracks",    _i18n.t("set.no_audio_tracks_detected_1b07"))
        _check_combo_row("video_quality_minimum", "video_quality_minimum_level",
                         _i18n.t("set.video_quality_below_minimum_50f7"),
                         VIDEO_QUALITY_LEVELS, "720p", combo_width=12)
        _level("warning")
        _check_row("multiple_video_files",   _i18n.t("set.multiple_video_files_in_1676"))
        _check_lang_row("required_audio_language", "required_audio_language_code",
                        _i18n.t("set.required_audio_language_missing_abf4"), AUDIO_LANGUAGES, "ENG")
        _check_lang_row("required_subtitle_language", "required_subtitle_language_code",
                        _i18n.t("set.required_subtitle_language_missing_ca1d"), SUBTITLE_LANGUAGES, "POR")
        _check_row("lang_not_ok",            _i18n.t("set.target_language_not_found_61ca"))
        _sub(_i18n.t("set.movie_ids_imdb_tmdb_4f07"))                                    # v0.19.6 TR1d
        _level("error")
        _check_row("missing_imdb_id",    _i18n.t("set.missing_imdb_id_no_5def"))
        _check_row("corrupt_imdb_id",    _i18n.t("set.imdb_id_conflict_between_4886"))
        _check_row("missing_tmdb_id",    _i18n.t("set.missing_tmdb_id_no_ef15"))
        # ### NEW v0.19.1 B24 ### how a missing ID is reported (when the boxes above are ticked)
        _level_row("single_source_level",
                   _i18n.t("set.movie_with_one_source_b62e"), "error")
        _level_row("no_source_level",
                   _i18n.t("set.movie_with_no_source_8cc9"), "error")
        _check_row("corrupt_tmdb_id",    _i18n.t("set.tmdb_id_conflict_between_0829"))
        _level("warning")
        _check_row("id_format_invalid",      _i18n.t("set.imdb_tmdb_id_not_f6f8"))
        _check_row("duplicate_movie",        _i18n.t("set.possible_duplicate_same_imdb_54b6"))  # NEW v0.18.4
        _sub(_i18n.t("set.title_year_and_genres_4e30"))                                    # v0.19.6 TR1d
        _level("error")
        _check_row("missing_movie_year", _i18n.t("set.missing_movie_year_in_8bbd"))
        _check_row("genre_missing",      _i18n.t("set.missing_genre_information_e201"))
        _level("warning")
        _check_row("missing_movie_title",    _i18n.t("set.missing_movie_title_in_b46d"))
        _check_row("year_out_of_range",      _i18n.t("set.year_out_of_range_f6e4"))
        _check_row("folder_name_mismatch",   _i18n.t("set.folder_name_doesn_t_dc1e"))
        _check_row("genre_warning",          _i18n.t("set.genre_issues_detected_non_36c9"))
        _sub(_i18n.t("set.rating_and_votes_d7ff"))                                    # v0.19.6 TR1d
        _level("error")
        _check_row("rating_conflict",    _i18n.t("set.rating_conflict_nfo_and_a4a4"))
        _level("warning")
        _check_row("missing_rating",     _i18n.t("set.missing_rating_3bc5"))
        _check_row("rating_warning",     _i18n.t("set.rating_tag_unreadable_non_e12a"))
        _check_spin_flt_row("suspicious_rating", "suspicious_rating_threshold",
                            _i18n.t("set.suspicious_rating_value_below_d943"), 1.0, 0.0, 10.0, incr=0.1, width=5)
        _check_row("missing_votes",          _i18n.t("set.missing_votes_count_7d34"))
        _check_row("votes_warning",          _i18n.t("set.votes_tag_unreadable_non_778c"))
        _sub(_i18n.t("set.images_poster_fanart_folder_bfdb"))                                    # v0.19.6 TR1d
        _level("error")
        _check_row("corrupt_poster",     _i18n.t("set.corrupt_poster_image_1247"))
        _check_row("corrupt_fanart",     _i18n.t("set.corrupt_fanart_image_9d2b"))
        _check_row("corrupt_folder",     _i18n.t("set.corrupt_folder_image_d416"))
        _level("warning")
        _check_row("missing_poster",         _i18n.t("set.missing_poster_6d24"))
        _check_row("poster_missing_with_folder",                              # NEW v0.19.2 F5
                   _i18n.t("set.also_when_folder_jpg_e5e2"))
        _check_row("missing_fanart",         _i18n.t("set.missing_fanart_c8a6"))
        _check_row("missing_folder",         _i18n.t("set.missing_folder_image_off_795e"))   # v0.19.2 B35
        _check_row("no_actor_info",          _i18n.t("ac.set.rule"))                         # v0.20.1 AC2
        _check_row("profile_names_unread",   _i18n.t("f3.set.names_unread"))                 # v0.20.0 F3c
        _check_row("folder_optional_with_kodi_poster",                        # NEW v0.19.1 B23
                   _i18n.t("set.folder_jpg_optional_when_4dbf"))
        _check_row("poster_proportion",      _i18n.t("set.poster_has_wrong_proportions_34dc"))
        _check_row("fanart_proportion",      _i18n.t("set.fanart_has_wrong_proportions_9429"))
        _check_row("folder_proportion",      _i18n.t("set.folder_image_has_wrong_fa26"))
        _check_combo_row("poster_folder_quality_minimum", "poster_folder_quality_level",
                         _i18n.t("set.poster_folder_quality_below_5700"),
                         POSTER_QUALITY_LEVELS, "1080p", combo_width=10)
        _check_combo_row("fanart_quality_minimum", "fanart_quality_level_minimum",
                         _i18n.t("set.fanart_quality_below_minimum_89f7"),
                         FANART_QUALITY_LEVELS, "1080p", combo_width=10)
        _check_row("image_file_too_small",   _i18n.t("set.image_file_below_minimum_7530"))   # NEW v0.19.0
        _check_row("image_format_mismatch",  _i18n.t("set.image_format_differs_from_18a4"))  # NEW v0.19.0
        _check_row("poster_folder_identical",  _i18n.t("set.poster_and_folder_image_cf5a"))   # v0.19.2 B35
        _sub(_i18n.t("set.backdrops_29d7"))                                    # v0.19.6 TR1d
        _level("warning")
        _check_spin_int_row("insufficient_backdrops", "backdrop_min_count",
                            _i18n.t("set.backdrop_images_below_minimum_b6fd"), 5, 1, 50, width=4)
        _check_spin_int_row("backdrop_too_small", "backdrop_min_avg_kb",
                            _i18n.t("set.backdrop_images_suspiciously_small_7744"), 20, 1, 500, width=5)
        _sub(_i18n.t("set.file_content_nfo_xml_ceae"))                                    # v0.19.6 TR1d
        _level("warning")
        # ### NEW v0.19.3 I8 ### content of the NFO / XML (warnings)
        _check_row("numeric_field_invalid",  _i18n.t("set.runtime_votes_not_a_ff7f"))
        _check_row("duplicate_single_tag",   _i18n.t("set.a_tag_that_belongs_7a13"))
        _check_row("empty_required_tag",     _i18n.t("set.empty_title_plot_overview_7b20"))
        _check_row("unexpected_root",        _i18n.t("set.nfo_root_is_not_7660"))
        _check_row("nfo_xml_too_large",      _i18n.t("set.nfo_or_xml_file_3caa"))

        _rules_section("nfo")
        _level("error")
        _check_row("missing_nfo",        _i18n.t("set.missing_nfo_file_181d"))
        _check_row("corrupt_nfo",        _i18n.t("set.corrupt_nfo_file_xml_2703"))
        _level("warning")
        _check_row("nfo_name_not_kodi",                                       # NEW v0.19.1 B23
                   _i18n.t("set.nfo_named_after_the_ff92"))
        _check_row("id_not_kodi", _i18n.t("kr.set.id_not_kodi"))             # NEW v0.20.0 KR1.1
        _choice_row("nfo_id_tags", _i18n.t("rd12.set.label"),                # NEW v0.20.0 RD12 (a tester)
                    (("all", _i18n.t("rd12.opt.all")), ("kodi", _i18n.t("rd12.opt.kodi"))), "all",
                    width=max(18, max(len(_i18n.t(k)) for k in ("rd12.opt.all", "rd12.opt.kodi")) + 2))
        _check_row("nfo_unescaped_amp",                                       # NEW v0.19.2 B33
                   _i18n.t("set.nfo_has_an_unescaped_f0c6"))
        _check_row("multiple_nfo_files",                                      # NEW v0.19.2 F5
                   _i18n.t("set.more_than_one_nfo_fc7b"))
        _check_row("nfo_online_art_links", _i18n.t("rd9.set"))                # NEW v0.20.0 RD9
        _check_row("genre_nfo_wrong_tags",   _i18n.t("set.nfo_uses_non_kodi_f853"))            # NEW v0.19.1
        _check_row("year_premiered_differ",  _i18n.t("set.nfo_year_and_the_8282"))
        _check_row("collection_mismatch",    _i18n.t("set.collection_missing_or_different_e522"))   # NEW v0.19.4 B110c
        _check_row("collection_artwork",     _i18n.t("set.collection_folder_poster_fanart_63a3"))   # NEW v0.19.4 B110g
        _check_row("collection_set_nfo",     _i18n.t("cf2.set.rule"))                                # NEW v0.20.1 CF2
        _rules_section("xml")
        _level("error")
        _check_row("missing_xml",        _i18n.t("set.missing_movie_xml_1aff"))
        _check_row("corrupt_xml",        _i18n.t("set.corrupt_movie_xml_xml_4e03"))
        _check_row("votes_conflict",     _i18n.t("set.votes_conflict_nfo_votes_26be"))
        _level("warning")                                                     # NEW v0.20.0 KR1.4
        _check_row("xml_tags_old_readers", _i18n.t("kr.set.xml_tags_old"))
        _rules_section("both")
        _level("warning")
        _check_row("imdb_id_partial",        _i18n.t("set.imdb_id_present_in_90a0"))   # NEW v0.18.3
        _check_row("tmdb_id_partial",        _i18n.t("set.tmdb_id_present_in_52a7"))   # NEW v0.18.3
        _check_row("genre_only_in_xml",      _i18n.t("set.genres_only_in_the_c198"))          # NEW v0.19.1
        _check_row("genre_only_in_nfo",      _i18n.t("set.genres_only_in_the_d7cf"))          # NEW v0.19.1
        _check_row("title_mismatch",         _i18n.t("set.title_mismatch_between_nfo_7545"))
        # ### NEW v0.19.3 B60 ### Repair All, when it cannot tell which local title is right
        _choice_row("title_sync_default", _i18n.t("set.when_repair_all_cannot_c45e"),
                    (("nfo", _i18n.t("set.title_keep_nfo")), ("skip", _i18n.t("set.title_skip"))), "nfo")

        # gray the sections the health mode does not use, at once when the mode changes (before Save)
        self._health_mode_var.trace_add("write", lambda *_: self._apply_health_sections())
        self._apply_health_sections()
        # v0.20.0 HP1d — a manual change shows "Custom"; a mode change keeps the preset's by-mode value (folder.jpg)
        for _m in (self._hr_vars, self._hr_int_vars, self._hr_flt_vars, self._hr_str_vars):
            for _v in _m.values():
                _v.trace_add("write", self._hp_sync)
        self._health_mode_var.trace_add("write", self._hp_mode_changed)
        self._hp_sync()

        # bottom padding
        tk.Frame(f, bg="#1e1e2e", height=16).pack()

    # ── v0.20.0 HP1d — health presets ──────────────────────────────────────────────────────────────────
    def _hp_rule_values(self):
        """The rule values the Health Rules widgets hold now (as they would be saved)."""
        hr = {k: v.get() for k, v in self._hr_vars.items()}
        for m, cast in ((self._hr_int_vars, int), (self._hr_flt_vars, lambda x: round(float(x), 2))):
            for k, v in m.items():
                try:
                    hr[k] = cast(v.get())
                except (ValueError, tk.TclError):
                    hr[k] = None
        hr.update({k: v.get() for k, v in self._hr_str_vars.items()})
        return hr

    def _hp_set(self, values):
        self._hp_busy[0] = True
        try:
            for k, v in values.items():
                for m in (self._hr_vars, self._hr_int_vars, self._hr_flt_vars, self._hr_str_vars):
                    if k in m:
                        m[k].set(v)
                        break
        finally:
            self._hp_busy[0] = False

    def _hp_sync(self, *_):
        if not hasattr(self, "_health_preset_var") or self._hp_busy[0]:
            return
        import settings_model as _smp
        p = _smp.matching_health_preset(self._hp_rule_values(), self._health_mode_var.get())
        if self._health_preset_var.get() != p:
            self._health_preset_var.set(p)
        self._hp_last[0] = p

    def _ticked_programs(self):                                    ### NEW v0.20.0 F3a-2 ###
        import media_profiles as _mpf
        return _mpf.clean_programs(p for p, v in getattr(self, "_program_vars", {}).items() if v.get())

    def _programs_changed(self):                                   ### NEW v0.20.0 F3a-2 ###
        """A tick changed: the health mode follows the ticked programs; nothing ticked gives back the mode the
        window opened with (today's behaviour for a user who never ticks)."""
        import media_profiles as _mpf
        m = _mpf.health_mode_for(self._ticked_programs()) or self._health_mode_initial
        if self._health_mode_var.get() != m:
            self._health_mode_var.set(m)                           # the sections, the preset and Save follow it
        self._programs_info_update()

    def _programs_info_update(self):                               ### NEW v0.20.0 F3a-2 ###
        """The line under the tick boxes: the files checked and the names a fix writes (or why there are none)."""
        import media_profiles as _mpf
        if not hasattr(self, "_programs_info"):
            return
        text = programs_info_text(self._ticked_programs(), self._health_mode_var.get())
        try:
            self._programs_info.configure(text=text)
            if hasattr(self, "_plex_nfo_cb"):                      # v0.20.0 AU22: it only applies with ONLY Plex ticked
                self._plex_nfo_cb.configure(state="normal" if list(self._ticked_programs()) == ["plex"] else "disabled")
        except tk.TclError:
            pass

    def _health_preset_chosen(self, preset):
        """Easy / Medium / Tight: every rule of the preset at once; own changes are replaced only after a yes."""
        import settings_model as _smp
        if preset not in _smp.HEALTH_PRESET_IDS:                 # "Custom" is shown, not chosen
            self._hp_sync()
            return
        mode = self._health_mode_var.get()
        if self._hp_last[0] == "custom" and not messagebox.askyesno(
                _i18n.t("hp.ask.t"), _i18n.t("hp.ask", preset=_i18n.t("hp." + preset)), parent=self):
            self._health_preset_var.set("custom")
            return
        self._hp_set(_smp.health_preset_values(preset, mode))
        self._hp_sync()

    def _hp_mode_changed(self, *_):
        """A preset follows the health mode (missing folder.jpg: Off in mode 1, On in modes 2 and 3)."""
        import settings_model as _smp
        prev = self._hp_last[0]
        if prev in _smp.HEALTH_PRESET_IDS:
            vals = _smp.health_preset_values(prev, self._health_mode_var.get())
            self._hp_set({k: v for k, v in vals.items() if k in _smp.HEALTH_PRESET_BY_MODE})
        self._hp_sync()

    def _apply_health_sections(self):                           ### NEW v0.19.6 TR1c ###
        """Gray the rule sections the chosen health mode does not use: visible, not clickable, their values kept
        (switching back shows them as they were). The NFO / XML tag pairs compare the two files: mode 2 only."""
        mode = self._health_mode_var.get()
        for sec, d in getattr(self, "_hr_sections", {}).items():
            on = health_section_on(sec, mode)
            d["note"].configure(text="" if on else HEALTH_RULE_SECTION_OFF.get(sec, ""))
            if on:
                d["note"].pack_forget()
            else:
                d["note"].pack(anchor="w", padx=22, after=d["head"])
            self._set_tree_state(d["frame"], on, skip=(d["note"],))
            if on:                                              # the combos / spinboxes follow their checkbox again
                for k in d["keys"]:
                    v = self._hr_vars.get(k)
                    if v is not None:
                        v.set(v.get())
        if hasattr(self, "_tags_text"):
            on = health_section_on("both", mode)
            self._tags_text.configure(state="normal" if on else "disabled", fg="#cdd6f4" if on else "#6c7086")
            if hasattr(self, "_tags_reset_btn"):
                self._tags_reset_btn.configure(state="normal" if on else "disabled")
            if hasattr(self, "_tags_note"):
                self._tags_note.configure(text="" if on else _i18n.t("set.used_in_health_mode_a487", health_mode_path=HEALTH_MODE_PATH))

    @staticmethod
    def _set_tree_state(w, on, skip=()):                        ### NEW v0.19.6 TR1c ###
        for c in w.winfo_children():
            if c in skip:
                continue
            cls = c.winfo_class()
            try:
                if cls in ("Checkbutton", "Radiobutton", "Button", "Spinbox"):
                    c.configure(state="normal" if on else "disabled")
                elif cls == "TCombobox":
                    c.configure(state="readonly" if on else "disabled")
                elif cls == "Label":
                    if not hasattr(c, "_mc_fg"):
                        c._mc_fg = c.cget("fg")
                    c.configure(fg=c._mc_fg if on else "#585b70")
            except tk.TclError:
                pass
            SettingsDialog._set_tree_state(c, on, skip)

    # ── Tab 11: Backup  (v0.12.0)  ───────────────────────────────────────────── ### MODIFIED_BY_CLAUDE_v18.2 — was Tab 9 ###

    def _build_backup_tab(self, nb, label="Backup"):
        """Backup folder maintenance tab.                  ### NEW v0.12.0 ###
        ### NEW v0.14.0 — reads backup_root from self._ctx ###
        """
        import os, shutil as _shutil

        f = tk.Frame(nb, bg="#1e1e2e"); nb.add(f, text=tab_title(label))

        tk.Label(f, text=_i18n.t("set.backup_folder_maintenance_058b"),
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#89b4fa"
                 ).pack(anchor="w", padx=16, pady=(16, 4))

        self._section(f, _i18n.t("set.automatic_cleanup_8b63"))
        self._note(f,
            _i18n.t("set.when_the_total_size_08d2", backup_protect_days=BACKUP_PROTECT_DAYS))

        r1 = self._row(f)
        tk.Label(r1, text=_i18n.t("set.maximum_backup_folder_size_a0a3"),
                 font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                 width=max(34, len(_i18n.t("set.maximum_backup_folder_size_a0a3")) + 3),
                 anchor="w").pack(side="left")                                      # v0.20.0 UI1e: ES is longer
        _s = self._ctx.settings if self._ctx else self._s
        self._max_backup_mb_var = tk.IntVar(value=_s.get("max_backup_size_mb", 500))
        tk.Spinbox(r1, from_=0, to=99999, textvariable=self._max_backup_mb_var, width=8,
                   font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
                   buttonbackground="#45475a", relief="flat").pack(side="left")
        tk.Label(r1, text=_i18n.t("set.mb_disabled_f7ae"), font=("Helvetica", 9),
                 bg="#1e1e2e", fg="#6c7086").pack(side="left", padx=(6, 0))
        # ### NEW v0.19.3 I12 ### the switch existed in settings.json but had no widget and no effect
        self._backup_cleanup_var = tk.BooleanVar(value=bool(_s.get("backup_cleanup_enabled", True)))
        tk.Checkbutton(f, text=_i18n.t("set.delete_the_oldest_backups_f2dd"),
                       variable=self._backup_cleanup_var, font=("Helvetica", 10), bg="#1e1e2e", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#1e1e2e",
                       activeforeground="#cdd6f4").pack(anchor="w", padx=22, pady=(4, 0))
        # ### NEW v0.19.4 B75 (D2) ### the folder's size, measured in a worker; the Tk thread polls
        self._backup_usage_lbl = tk.Label(f, text=_i18n.t("set.backup_folder_size_now_d9ea"), font=("Helvetica", 9),
                                          bg="#1e1e2e", fg="#a6adc8", justify="left")
        self._backup_usage_lbl.pack(anchor="w", padx=22, pady=(4, 0))
        _root_bk = (self._ctx.backup_root if self._ctx else _BACKUP_ROOT_PATH) or ""
        _size_box = []

        def _measure():                                     # worker: plain data only
            total = 0
            try:
                for _e in os.scandir(_root_bk):
                    if _e.is_dir() and _e.name.startswith("backup_"):
                        for _dp, _dn, _fn in os.walk(_e.path):
                            for _n in _fn:
                                try:
                                    total += os.path.getsize(os.path.join(_dp, _n))
                                except OSError:
                                    pass
            except OSError:
                pass
            _size_box.append(total)

        _timer_owner = self.master if self.master is not None else self

        def _poll():                                        # Tk thread
            try:
                if not self._backup_usage_lbl.winfo_exists():
                    return
                if not _size_box:
                    _timer_owner.after(200, _poll)
                    return
                self._backup_usage_lbl.configure(text=backup_usage_text(_size_box[0], self._max_backup_mb_var.get()))
            except (tk.TclError, ValueError):
                pass
        if _root_bk and os.path.isdir(_root_bk):
            threading.Thread(target=_measure, daemon=True).start()
            _timer_owner.after(200, _poll)
        else:
            self._backup_usage_lbl.configure(text=_i18n.t("set.backup_folder_size_now_5b36"))

        tk.Frame(f, bg="#45475a", height=1).pack(fill="x", padx=16, pady=(14, 8))

        self._section(f, _i18n.t("set.manual_cleanup_950c"))
        self._note(f, _i18n.t("set.delete_all_backup_subfolders_6308"))

        r2 = self._row(f)
        tk.Button(r2, text=_i18n.t("set.delete_all_backup_folders_fc7e"),
                  font=("Helvetica", 10, "bold"),
                  bg="#f38ba8", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._delete_all_backups).pack(side="left")

        # Show current backup folder path for reference
        backup_path = (self._ctx.backup_root if self._ctx else _BACKUP_ROOT_PATH) or ""
        if backup_path:
            tk.Label(f, text=_i18n.t("set.backup_folder_9be6", backup_path=backup_path),
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
            _mb.showinfo(_i18n.t("set.no_backups_266b"), _i18n.t("set.backup_folder_not_found_0092"), parent=self)
            return
        if not _mb.askyesno(_i18n.t("set.delete_all_backups_77c0"),
                _i18n.t("set.are_you_sure_you_b0cd"),
                icon="warning", parent=self):
            return
        try:                                                     ### NEW v0.19.4 P3 (F22) — this session's runs stay ###
            import settings_controller as _scx
            _open = {os.path.normcase(os.path.abspath(k)) for k in list(_scx._OPEN_MANIFESTS)}
        except Exception:
            _open = set()

        def _do_delete():
            deleted = 0
            errors = []
            try:
                for entry in os.scandir(backup_root):
                    if entry.is_dir() and entry.name.startswith("backup_") \
                            and os.path.normcase(os.path.abspath(entry.path)) not in _open:
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
            msg = _i18n.t("set.deleted_backup_folder_s_04bb", deleted=deleted)
            if errors:
                msg += _i18n.t("set.errors_a7d6", n=len(errors), join="\n".join(errors[:3]))
            _mb.showinfo(_i18n.t("set.backups_deleted_50f5"), msg, parent=self)

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
            img |= self._num(self._min_poster_kb_var, 100) != img_snap.get("min_poster_kb", 100)
        if hasattr(self, "_min_folder_kb_var"):
            img |= self._num(self._min_folder_kb_var, 100) != img_snap.get("min_folder_kb", 100)
        if hasattr(self, "_min_fanart_kb_var"):
            img |= self._num(self._min_fanart_kb_var, 200) != img_snap.get("min_fanart_kb", 200)
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
            curr_hr = {k: v for k, v in snap_hr.items() if k == "missing_language_field"}   # v0.19.5 B121: a retired key has no control
            for k, v in self._hr_vars.items():      curr_hr[k] = v.get()
            for k, v in self._hr_int_vars.items():  curr_hr[k] = self._num(v, snap_hr.get(k, 0))
            for k, v in self._hr_flt_vars.items():  curr_hr[k] = round(self._num(v, float(snap_hr.get(k, 0.0))), 2)
            for k, v in self._hr_str_vars.items():  curr_hr[k] = v.get()
            hr_changed = (curr_hr != snap_hr)
        # v0.20.0 6h — the program ticks and the Plex NFO tick switch rules on / off too (profile_rules_off)
        if hasattr(self, "_program_vars") and tuple(self._ticked_programs()) != getattr(self, "_programs_initial", ()):
            hr_changed = True
        if hasattr(self, "_plex_nfo_var") and self._plex_nfo_var.get() != (getattr(self, "_plex_nfo_initial", "") != "off"):
            hr_changed = True
        changed["health_rules"] = hr_changed

        # v0.19.6 TR1 — movie.xml on / off: health at once, then a new scan reads or drops the XML data
        changed["xml"] = (hasattr(self, "_health_mode_var")                  # v0.19.6 TR1b: the health mode
                          and self._health_mode_var.get() != getattr(self, "_health_mode_initial", "nfo"))
        changed["any"] = any([img, lang, genres, tags, hr_changed, changed["xml"]])
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
        dlg.title(_i18n.t("set.update_scan_c023"))
        dlg.configure(bg="#1e1e2e")
        dlg.transient(parent_app)
        modal(dlg)                                                  ### MODIFIED v0.19.4 B98 ###
        dlg.resizable(False, False)

        # ── Content ───────────────────────────────────────────────────────────
        outer = tk.Frame(dlg, bg="#1e1e2e")
        outer.pack(fill="both", expand=True, padx=20, pady=(20, 12))

        tk.Label(outer,
                 text=_i18n.t("set.settings_that_affect_scan_9a34"),
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

        tk.Button(bf, text=_i18n.t("set.update_scan_no_ffprobe_32a6"),
                  font=("Helvetica", 10, "bold"), bg="#89b4fa", fg="#1e1e2e",
                  relief="flat", cursor="hand2",
                  command=lambda: _choose("no_ff")).pack(side="left", padx=(0, 6))
        tk.Button(bf, text=_i18n.t("set.update_scan_with_ffprobe_866d"),
                  font=("Helvetica", 10, "bold"), bg="#a6e3a1", fg="#1e1e2e",
                  relief="flat", cursor="hand2",
                  command=lambda: _choose("with_ff")).pack(side="left", padx=(0, 6))
        tk.Button(bf, text=_i18n.t("set.skip_1908"),
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

    # ── Save & Close ──────────────────────────────────────────────────────────

    def _focus_field(self, widget):                                 ### NEW v0.19.4 B94b ###
        """Show the tab that holds *widget* and put the cursor in it."""
        try:
            child, p = widget, widget.master
            while p is not None and not isinstance(p, ttk.Notebook):
                child, p = p, p.master
            if p is not None:
                p.select(child)
            widget.focus_set()
        except (tk.TclError, AttributeError):
            pass

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
        live = ctx.settings if ctx else self._s  # live settings dict
        ### MODIFIED v0.19.4 B94b — every value goes into a COPY first; the live
        ### settings change only when all values are valid and the file was written ###
        _s = copy.deepcopy(live)

        changed = self._rescan_changed()

        try:
            self._check_number_fields()                             ### NEW v0.19.5 SH-E9 ###
            _s["text_editor"]      = self._editor_var.get().strip()
            _s["ffmpeg_path"]      = self._ffmpeg_var.get().strip()
            if hasattr(self, "_coll_folder_var"):                   # NEW v0.19.4 B110g
                _cf = self._coll_folder_var.get().strip()                   # F19: not found → ask
                if _cf and not os.path.isdir(_cf) and _cf != (self._s.get("collection_folder") or "") and not messagebox.askyesno(
                        _i18n.t("set.collection_folder_583e"), _i18n.t("set.the_collection_folder_was_6345", cf=_cf), parent=self):
                    raise SettingsFieldError("Collection folder", None, f"not found: {_cf}")
                _s["collection_folder"] = _cf
            if hasattr(self, "_group_coll_var"):                    # NEW v0.19.4 B110h
                _s["group_by_collection"] = bool(self._group_coll_var.get())
                _cln = self._coll_lang_var.get()                                       # NEW v0.19.4 P4
                _s["collection_name_lang"] = (self._coll_lang_codes[self._coll_lang_names.index(_cln)]
                                              if _cln in self._coll_lang_names else "auto")
            _s["scraper_path"]     = self._scraper_var.get().strip()
            _s["tmdb_api_key"]     = self._tmdb_var.get().strip()
            _s["omdb_api_key"]     = self._omdb_var.get().strip()
            if hasattr(self, "_fanarttv_var"):                  ### NEW v0.19.1 I10 — key only: no rescan ###
                _s["fanarttv_api_key"]    = self._fanarttv_var.get().strip()
                _s["fanarttv_client_key"] = self._fanarttv_client_var.get().strip()
            _s["default_browser"]  = self._browser_var.get().strip()
            _s["lang_ok_code"]     = self._lang_var.get().upper()
            _s["improve_checks"]   = {k: v.get() for k, v in self._ic_vars.items()}
            _num = self._num                                               ### v0.18.4 — blank-safe ###
            _s["max_nfo_kb"]       = max(1, _num(self._max_nfo_kb_var, 50))
            _s["max_xml_kb"]       = max(1, _num(self._max_xml_kb_var, 25))
            # _s["min_backdrops"] intentionally not written — deprecated in v0.18.2, now in health_rules ### MODIFIED_BY_CLAUDE_v18.2 ###
            _s["min_poster_kb"]    = max(0, _num(self._min_poster_kb_var, 100))
            _s["min_folder_kb"]    = max(0, _num(self._min_folder_kb_var, 100))
            _s["min_fanart_kb"]    = max(0, _num(self._min_fanart_kb_var, 200))
            _s["backdrop_count"]   = max(1, min(50, _num(self._backdrop_count_var, 10)))
            if hasattr(self, "_scan_workers_var"):                          ### NEW v0.18.4 ###
                _s["scan_workers"]    = max(1, min(16, _num(self._scan_workers_var, 6)))
            if hasattr(self, "_ffprobe_cache_var"):                         ### NEW v0.19.1 I5 ###
                _s["ffprobe_cache_enabled"] = bool(self._ffprobe_cache_var.get())
            if hasattr(self, "_ffmpeg_frame_timeout_var"):                  ### NEW v0.19.2 B28 ###
                _s["ffmpeg_frame_timeout_sec"] = max(5, min(300, _num(self._ffmpeg_frame_timeout_var, 20)))
                _s["ffmpeg_run_budget_sec"]    = max(30, min(1800, _num(self._ffmpeg_run_budget_var, 180)))
            if hasattr(self, "_ffprobe_workers_var"):
                _s["ffprobe_workers"] = max(1, min(8, _num(self._ffprobe_workers_var, 2)))
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
            if hasattr(self, "_art_lang_var"):                  ### NEW v0.20.1 TF3 ###
                _s["artwork_language"] = self._art_lang_var.get() or "library"
                _s["artwork_language_mode"] = self._art_mode_var.get() if self._art_mode_var.get() in ("prefer", "only") else "prefer"
                _s["artwork_textless_backgrounds"] = bool(self._art_textless_var.get())
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
            if hasattr(self, "_ctx_repeat_var"):                            ### NEW v0.19.2 B57 ###
                _s["ctx_repeat_last"] = bool(self._ctx_repeat_var.get())
            if hasattr(self, "_check_updates_var"):                         ### NEW v0.19.2 B50 ###
                _s["check_updates"] = bool(self._check_updates_var.get())
            if hasattr(self, "_dark_title_var"):                            ### NEW v0.19.2 B51 ###
                _s["dark_title_bar"] = bool(self._dark_title_var.get())
            if hasattr(self, "_scan_ignored_report_var"):                   ### NEW v0.19.2 B53 ###
                _s["scan_ignored_report"] = bool(self._scan_ignored_report_var.get())
            if hasattr(self, "_health_mode_var"):                           ### NEW v0.19.6 TR1b ###
                _s["health_mode"] = health_mode_of({"health_mode": self._health_mode_var.get()})
            if hasattr(self, "_program_vars"):                              ### NEW v0.20.0 F3a-2 ###
                _s["media_programs"] = list(self._ticked_programs())
            if hasattr(self, "_plex_nfo_var"):                              ### NEW v0.20.0 6h ###
                _pv = "on" if self._plex_nfo_var.get() else "off"
                if not (self._plex_nfo_initial == "" and _pv == "on"):     # untouched and never asked: stays ""
                    _s["plex_nfo_checks"] = _pv
            if hasattr(self, "_max_backup_mb_var"):
                _s["max_backup_size_mb"] = max(0, self._num(self._max_backup_mb_var, int(_s.get("max_backup_size_mb", 500) or 0)))   # F20
            if hasattr(self, "_backup_cleanup_var"):                        ### NEW v0.19.3 I12 ###
                _s["backup_cleanup_enabled"] = bool(self._backup_cleanup_var.get())
            if hasattr(self, "_rating_apply_all_var"):                      ### NEW v0.15.0 ###
                _s["rating_apply_all_movies"] = self._rating_apply_all_var.get()  ### NEW v0.15.0 ###
            if hasattr(self, "_rating_use_more_votes_var"):                 ### NEW v0.15.0 ###
                _s["rating_use_more_votes"] = self._rating_use_more_votes_var.get()  ### NEW v0.15.0 ###

            # v0.18.2 — write back health rule variables         ### ADDED_BY_CLAUDE_v18.2 ###
            if hasattr(self, "_hr_vars"):
                hr = _s.setdefault("health_rules", {})
                _hrd = self._defaults.get("health_rules", {})
                for k, v in self._hr_vars.items():      hr[k] = v.get()
                for k, v in self._hr_int_vars.items():  hr[k] = max(1, self._num(v, _hrd.get(k, 1)))
                for k, v in self._hr_flt_vars.items():  hr[k] = round(max(0.0, self._num(v, float(_hrd.get(k, 0.0)))), 2)
                for k, v in self._hr_str_vars.items():  hr[k] = v.get()
                if hasattr(self, "_health_preset_var"):          ### NEW v0.20.0 HP1d ###
                    _s["health_preset"] = self._health_preset_var.get()
                # v0.19.0 — Image Sizes quality keys are mirrors of the Health
                # Rules values (one authoritative source).   ### NEW v0.19.0 ###
                _s["poster_quality_level"] = _s["folder_quality_level"] = \
                    hr.get("poster_folder_quality_level") or _s.get("poster_quality_level", "1080p")
                _s["fanart_quality_level"] = \
                    hr.get("fanart_quality_level_minimum") or _s.get("fanart_quality_level", "1080p")

            raw_genres = self._genres_text.get("1.0", "end")
            _s["genre_list"] = "\n".join(
                g.strip() for g in raw_genres.splitlines() if g.strip())

            parsed_tags = self._parse_tags_text()
            _s["tag_pairs"] = parsed_tags

            ### MODIFIED v0.19.4 B94a — the save result is checked (False = not written) ###
            _saver = ctx.save_settings if (ctx and ctx.save_settings) else _save_settings_fn
            _ok = _saver(_s) if _saver else None
            _log = (ctx.logger if ctx else _logger)
            if _ok is False:
                if _log:
                    _log.error("Settings not saved — settings.json could not be written; nothing applied")
                messagebox.showerror(_i18n.t("set.settings_not_saved_79cb"), SETTINGS_NOT_SAVED_TEXT, parent=self)
                return
            live.update(_s)                                     ### NEW v0.19.4 B94b — applied only now ###

            if ctx and ctx.refresh_ffmpeg:
                ctx.refresh_ffmpeg()
            elif _refresh_ffmpeg_paths:        # shim fallback
                _refresh_ffmpeg_paths()

            if _log:
                _log.info("Settings saved")

        except SettingsFieldError as fe:                        ### NEW v0.19.4 B94b ###
            _log = (ctx.logger if ctx else _logger)
            if _log:
                _log.error(f"Settings not saved: {fe}")
            self._focus_field(fe.widget)
            messagebox.showerror(_i18n.t("set.settings_not_saved_79cb"), _i18n.t("set.nothing_was_changed_correct_9056", fe=fe), parent=self)
            return
        except Exception as e:
            _log = (ctx.logger if ctx else _logger)
            if _log:
                _log.error(f"Settings save error: {e}")
            messagebox.showerror(_i18n.t("set.save_error_3e90"), str(e), parent=self)
            return

        parent_app = self._parent if hasattr(self, "_parent") else None

        ### NEW v0.13.0 — destroy dialog FIRST, then schedule refresh ###
        self.destroy()

        if parent_app and hasattr(parent_app, "_on_settings_changed"):
            parent_app.after(0, parent_app._on_settings_changed)

        # Track 1: health rules changed → recompute health automatically, no
        # prompt and no re-scan (Save & Apply).                 ### MODIFIED v0.18.4 ###
        # v0.19.0: Image Sizes changes (quality tiers, KB minimums, proportion
        # toggles) are re-evaluated in place from the cached image facts, so
        # they follow the same track as the health rules and need no rescan.
        if changed.get("xml") and parent_app and hasattr(parent_app, "_apply_column_visibility"):   ### NEW v0.19.6 TR1 ###
            parent_app.after(0, parent_app._apply_column_visibility)
        if ((changed.get("health_rules") or changed.get("image_sizes") or changed.get("xml"))   ### MODIFIED v0.19.0; xml v0.19.6 ###
                and parent_app and hasattr(parent_app, "_apply_health_rules_inplace")):
            def _apply_rules_now():
                if getattr(parent_app, "_scanning", False):     ### NEW v0.19.4 B91 — wait until the scan ends ###
                    parent_app.after(500, _apply_rules_now)
                    return
                try:
                    if getattr(parent_app, "_results", None):
                        parent_app._apply_health_rules_inplace()
                        try:
                            parent_app._incremental_save(parent_app._results)
                            parent_app._sb_action.configure(text=_i18n.t("set.last_health_rules_applied_953a"))
                        except Exception:
                            pass
                    _lg = (ctx.logger if ctx else _logger)
                    if _lg:
                        _lg.info("Health rules changed — health status recomputed")
                except Exception as e:
                    _lg = (ctx.logger if ctx else _logger)
                    if _lg:
                        _lg.error(f"Applying health rules failed: {e}")
            parent_app.after(0, _apply_rules_now)

        # Track 2: scan-relevant settings → offer re-scan
        _scan_relevant = any([
            changed.get("language"),                                ### MODIFIED v0.19.0 — image_sizes handled in place ###
            changed.get("genres"),
            changed.get("tags"),
            changed.get("xml"),                                     ### NEW v0.19.6 TR1 ###
        ])
        if _scan_relevant and parent_app:
            parent_app.after(0, lambda: self._offer_rescan(parent_app))
        elif not _scan_relevant and not changed.get("health_rules") and not changed.get("image_sizes"):
            _log = (ctx.logger if ctx else _logger)
            if _log:
                _log.info("Settings saved; no rescan-relevant changes — no prompt offered.")
