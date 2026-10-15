# =============================================================================
# settings_controller.py
# Metadata & MediaClinic — Settings Business Logic
# Version: 0.19.1                                              ### MODIFIED v0.19.1 ###
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# All non-UI logic that the settings subsystem needs:
#   - Persistent storage (load / save JSON)
#   - Scan-results cache file (last_results.json)              ### NEW v0.18.3 ###
#   - FFmpeg / FFprobe discovery and testing
#   - Notepad++ discovery
#   - Browser detection
#   - Backup creation and cleanup
#   - refresh_ffmpeg_paths (updates caller-supplied mutable state)
#
# RULES (enforced by CLAUDE_RULES.md)
# ------------------------------------
#   • NO imports of tkinter or any UI module
#   • NO references to the global SETTINGS dict — callers pass settings in
#   • Every function is independently testable without a running Tk window
#   • Blocking I/O (subprocess, filesystem walk) lives here and ONLY here;
#     callers must use run_async() from settings_context.py to invoke these
#     from a UI thread
#
# CONSUMERS
# ---------
#   mediaclinic.py      — calls load_settings, save_settings, backup helpers
#   settings_context.py — wraps these functions as SettingsContext callables
# =============================================================================

import copy                                                      ### NEW v0.18.3 ###
import json
import os
import re
import shutil
import subprocess
import threading                                                 ### NEW v0.19.1 I1 ###
import time
import webbrowser

from settings_model import DEFAULT_SETTINGS


# ── Persistent storage ────────────────────────────────────────────────────────

def get_config_dir():
    """Return (and create if necessary) the platform config directory.
    The MEDIACLINIC_CONFIG_DIR environment variable overrides the default
    location (used by the self-test so it never touches real settings).
    ### MODIFIED v0.18.3 ###
    """
    override = os.environ.get("MEDIACLINIC_CONFIG_DIR", "").strip()
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get(
            "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
    d = os.path.join(base, "MediaMetadataClinic")
    os.makedirs(d, exist_ok=True)
    return d


CONFIG_PATH        = os.path.join(get_config_dir(), "settings.json")
RESULTS_CACHE_PATH = os.path.join(get_config_dir(), "last_results.json")   ### NEW v0.18.3 ###
FFPROBE_CACHE_PATH = os.path.join(get_config_dir(), "ffprobe_cache.json")  ### NEW v0.19.1 I5 ###


def load_ffprobe_cache():                                       ### NEW v0.19.1 I5 ###
    """{normcase path: {"size", "mtime_ns", "data"}} — {} when missing or
    corrupt (a broken cache is simply ignored and rebuilt)."""
    try:
        with open(FFPROBE_CACHE_PATH, "r", encoding="utf-8") as f:
            c = json.load(f)
        if isinstance(c, dict):
            return {k: v for k, v in c.items()
                    if isinstance(v, dict) and "size" in v and "mtime_ns" in v and isinstance(v.get("data"), dict)}
    except Exception:
        pass
    return {}


def save_ffprobe_cache(cache):                                  ### NEW v0.19.1 I5 ###
    """Atomic write (temp file + replace).  Worker threads only."""
    tmp = FFPROBE_CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, FFPROBE_CACHE_PATH)

FANARTTV_CACHE_PATH = os.path.join(get_config_dir(), "fanarttv_cache.json")  ### NEW v0.19.1 I10 ###
FANARTTV_CACHE_DAYS = 7


def load_fanarttv_cache():                                      ### NEW v0.19.1 I10 ###
    """{"tmdb:603" | "imdb:tt…": {"t": epoch, "data": {...}}} — {} when
    missing or corrupt.  Holds fanart.tv answers only, never a key."""
    try:
        with open(FANARTTV_CACHE_PATH, "r", encoding="utf-8") as f:
            c = json.load(f)
        if isinstance(c, dict):
            return {k: v for k, v in c.items()
                    if isinstance(v, dict) and isinstance(v.get("t"), (int, float)) and isinstance(v.get("data"), dict)}
    except Exception:
        pass
    return {}


def save_fanarttv_cache(cache):                                 ### NEW v0.19.1 I10 ###
    """Atomic write; entries older than FANARTTV_CACHE_DAYS are dropped."""
    import time as _t
    limit = _t.time() - FANARTTV_CACHE_DAYS * 86400
    keep = {k: v for k, v in cache.items() if v.get("t", 0) >= limit}
    tmp = FANARTTV_CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, FANARTTV_CACHE_PATH)

# Legacy quality tier name migration (v0.16.1) — single copy lives here now.
_LEGACY_QUALITY_MAP = {                                          ### MOVED v0.18.3 ###
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


def load_settings():
    """
    Load settings from CONFIG_PATH, deep-merge with DEFAULT_SETTINGS,
    and return the resulting dict.  Returns a deep copy of DEFAULT_SETTINGS
    on any read or parse error.
    ### MODIFIED v0.18.3 — deep copy of defaults, health_rules deep-merge,
    legacy quality-label migration (all moved here from the main script) ###
    """
    merged = copy.deepcopy(DEFAULT_SETTINGS)
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return merged
            for sub in ("improve_checks", "health_rules"):
                if isinstance(data.get(sub), dict):
                    d = dict(DEFAULT_SETTINGS[sub])
                    d.update(data[sub])
                    data[sub] = d
            merged.update(data)
            # v0.19.0 — first run after the upgrade: the single root folder
            # becomes the first library; the new Library column starts hidden.
            if "library_folders" not in data:                     ### NEW v0.19.0 ###
                lf = (data.get("last_folder") or "").strip()
                merged["library_folders"] = [os.path.normpath(lf)] if lf else []   ### normpath v0.19.1 ###
                hc = list(merged.get("hidden_columns") or [])
                if "library" not in hc:
                    hc.append("library")
                merged["hidden_columns"] = hc
            # v0.19.1 — library paths are stored Windows-style (z:/x → z:\\x)  ### NEW v0.19.1 ###
            if isinstance(merged.get("library_folders"), list):
                merged["library_folders"] = [os.path.normpath(x.strip()) for x in merged["library_folders"]
                                             if isinstance(x, str) and x.strip()]
            if isinstance(merged.get("library_filter"), str) and merged["library_filter"].strip():
                merged["library_filter"] = os.path.normpath(merged["library_filter"].strip())
            for qkey in ("poster_quality_level", "folder_quality_level",
                         "fanart_quality_level"):
                if merged.get(qkey) in _LEGACY_QUALITY_MAP:
                    merged[qkey] = _LEGACY_QUALITY_MAP[merged[qkey]]
    except Exception:
        pass
    sync_quality_mirrors(merged)                                 ### NEW v0.19.0 ###
    return merged


def sync_quality_mirrors(settings):
    """
    v0.19.0: the minimum image quality has ONE authoritative source — the
    Health Rules keys (poster_folder_quality_level, fanart_quality_level_minimum).
    The older Image Sizes keys (poster_quality_level, folder_quality_level,
    fanart_quality_level) are kept in settings.json for compatibility and are
    rewritten here to mirror the Health Rules values.  Returns True when a
    mirror was changed.                                          ### NEW v0.19.0 ###
    """
    try:
        hr = settings.get("health_rules")
        if not isinstance(hr, dict):
            return False
        pf = hr.get("poster_folder_quality_level") or "1080p"
        fa = hr.get("fanart_quality_level_minimum") or "1080p"
        changed = False
        for key, val in (("poster_quality_level", pf), ("folder_quality_level", pf),
                         ("fanart_quality_level", fa)):
            if settings.get(key) != val:
                settings[key] = val
                changed = True
        return changed
    except Exception:
        return False


def save_settings(settings):
    """Persist *settings* dict to CONFIG_PATH as JSON.  Silent on error."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── Scan-results cache (v0.18.3) ──────────────────────────────────────────────
# The full scan-result list used to live inside settings.json ("last_results"),
# which made that file several MB and slowed every settings save.  It now has
# its own file next to settings.json.

def load_results_cache():
    """Return the cached scan-result list, or [] when absent/unreadable."""  ### NEW v0.18.3 ###
    try:
        if os.path.isfile(RESULTS_CACHE_PATH):
            with open(RESULTS_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_results_cache(results):
    """Persist the scan-result list.  Returns True on success."""  ### NEW v0.18.3 ###
    try:
        tmp = RESULTS_CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, default=str)
        os.replace(tmp, RESULTS_CACHE_PATH)
        return True
    except Exception:
        return False


def migrate_results_from_settings(settings):
    """
    One-time migration: move settings["last_results"] (pre-v0.18.3) into the
    results cache file.  Returns True when a migration happened.
    """                                                           ### NEW v0.18.3 ###
    old = settings.get("last_results")
    if isinstance(old, list) and old:
        # Keep a copy of the pre-migration settings.json so v0.18.2 can still be
        # started from it if ever needed (it expects the rows inside).
        try:
            bak = CONFIG_PATH + ".pre-v0.18.3.bak"
            if not os.path.isfile(bak) and os.path.isfile(CONFIG_PATH):
                shutil.copy2(CONFIG_PATH, bak)
        except Exception:
            pass
        if not os.path.isfile(RESULTS_CACHE_PATH):
            save_results_cache(old)
        settings["last_results"] = []
        save_settings(settings)
        return True
    return False


# ── FFmpeg discovery & validation ─────────────────────────────────────────────

def find_ffmpeg_ffprobe(custom_dir=""):
    """
    Locate ffmpeg and ffprobe executables.

    Checks *custom_dir* first (if a valid directory), then falls back
    to PATH via shutil.which.

    Returns
    -------
    (ffmpeg_path, ffprobe_path) : tuple[str|None, str|None]
    """
    exe = (lambda d, n: os.path.join(d, n + ".exe") if os.name == "nt"
           else os.path.join(d, n))
    if custom_dir and os.path.isdir(custom_dir):
        ff = exe(custom_dir, "ffmpeg")
        fp = exe(custom_dir, "ffprobe")
        if not os.path.isfile(ff):
            ff = os.path.join(custom_dir, "ffmpeg")
        if not os.path.isfile(fp):
            fp = os.path.join(custom_dir, "ffprobe")
        if os.path.isfile(ff) and os.path.isfile(fp):
            return ff, fp
    return shutil.which("ffmpeg"), shutil.which("ffprobe")


def test_ffmpeg(ff_path, fp_path):
    """
    Run ``ffmpeg -version`` and ``ffprobe -version`` to verify both tools.

    Returns
    -------
    (ff_ok, fp_ok, ff_msg, fp_msg) : tuple[bool, bool, str, str]

    NOTE: This function calls subprocess and may block for up to 10 s.
    Always call via run_async() from a UI thread.
    """
    def _run(path):
        if not path or not os.path.isfile(path):
            return False, "Executable not found"
        try:
            r = subprocess.run(
                [path, "-version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0 and (
                    "ffmpeg" in r.stdout.lower() or "ffprobe" in r.stdout.lower()):
                return True, "OK"
            return False, f"Unexpected output (exit {r.returncode})"
        except subprocess.TimeoutExpired:
            return False, "Timed out"
        except Exception as e:
            return False, str(e)

    ff_ok, ff_msg = _run(ff_path)
    fp_ok, fp_msg = _run(fp_path)
    return ff_ok, fp_ok, ff_msg, fp_msg


def refresh_ffmpeg_paths(settings, ffmpeg_holder):
    """
    Re-discover FFmpeg/FFprobe and update *ffmpeg_holder* in-place.

    Parameters
    ----------
    settings : dict
        Live settings dict (reads "ffmpeg_path" key).
    ffmpeg_holder : list[str|None, str|None]
        Two-element list [ffmpeg_path, ffprobe_path] to update in place.
        Callers initialise this as [None, None] and read from it.
    """
    ff, fp = find_ffmpeg_ffprobe(settings.get("ffmpeg_path", ""))
    ffmpeg_holder[0] = ff
    ffmpeg_holder[1] = fp


# ── Notepad++ discovery ───────────────────────────────────────────────────────

def find_notepadpp():
    """
    Try common Notepad++ install locations on Windows.
    Returns path string or None.
    """
    candidates = [
        r"C:\Program Files\Notepad++\notepad++.exe",
        r"C:\Program Files (x86)\Notepad++\notepad++.exe",
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Programs", "Notepad++", "notepad++.exe"),
        os.path.join(
            os.environ.get("PROGRAMFILES", ""), "Notepad++", "notepad++.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return shutil.which("notepad++")


# ── Browser detection ─────────────────────────────────────────────────────────

_KNOWN_BROWSERS_WIN = [
    ("Google Chrome", [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            r"Google\Chrome\Application\chrome.exe"),
    ]),
    ("Mozilla Firefox", [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ]),
    ("Microsoft Edge", [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.join(
            os.environ.get("PROGRAMFILES", ""),
            r"Microsoft\Edge\Application\msedge.exe"),
    ]),
    ("Brave", [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            r"BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]),
    ("Opera", [
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""), r"Programs\Opera\opera.exe"),
        r"C:\Program Files\Opera\opera.exe",
    ]),
    ("Vivaldi", [
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            r"Vivaldi\Application\vivaldi.exe"),
    ]),
]


def detect_installed_browsers():
    """
    Scan standard locations for known browsers on Windows.

    Returns
    -------
    list[tuple[str, str]]
        (display_name, exe_path) pairs for browsers actually found.
        Empty on non-Windows.

    NOTE: Performs filesystem stat calls.  Call via run_async() from a UI thread.
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


def open_url_with_browser(url, settings):
    """
    Open *url* in the user's configured browser (from *settings*),
    falling back to the system default via webbrowser if none is set.
    """
    browser_path = settings.get("default_browser", "").strip()
    if browser_path and os.path.isfile(browser_path):
        try:
            subprocess.Popen(
                [browser_path, url],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return
        except Exception:
            pass
    webbrowser.open(url)


# ── Backup helpers ────────────────────────────────────────────────────────────

def get_backup_root(script_dir):
    """Return the backup root directory path (not created here)."""
    return os.path.join(script_dir, "backup")


def _make_backup_folder_path(backup_root, name, fallback="unknown"):
    """
    Build a unique timestamped backup folder path under *backup_root*.
    ADDED_BY_CLAUDE_v18 — extracted from make_backup / make_batch_backup to
    eliminate duplicated folder-name generation logic.
    """
    safe = re.sub(r'[\\/:*?"<>|]', '', name).strip()
    safe = re.sub(r'\s+', '_', safe) or fallback
    timestamp   = time.strftime("%Y-%m-%d_%H-%M-%S")
    base_folder = os.path.join(backup_root, f"backup_{safe}_{timestamp}")
    folder = base_folder
    counter = 2
    while os.path.exists(folder):
        folder = f"{base_folder}_{counter}"
        counter += 1
    return folder


# ── v0.19.1 I1: backup manifest + restore ("Undo the last batch") ────────────
# Every backup folder gets a manifest.json:
#   {"version": 1, "created": "YYYY-MM-DD HH:MM:SS", "action": "Ratings Sync",
#    "run_id": "...", "files": [{"original": abs path, "backup": name in the
#    folder, "size", "mtime",                 (the original BEFORE the change)
#    "after_size", "after_mtime"}]}           (the file as the run left it)
# The action label comes from a thread-local context (backup_action), so the
# backup functions keep their signatures.  "after_*" is filled by
# note_written(paths), which the app calls from _schedule_refresh after every
# change; Backup History uses it to warn about files changed since the run.
MANIFEST_NAME = "manifest.json"
_BK_CTX = threading.local()
_MF_LOCK = threading.RLock()
_OPEN_MANIFESTS = {}          # backup folder -> manifest dict (this session)
_RUN_SEQ = [0]


class backup_action:                                            ### NEW v0.19.1 I1 ###
    """with backup_action("Ratings Sync"): …  — labels the backups made in
    this thread (one run id per with-block)."""
    def __init__(self, action):
        self.action = action

    def __enter__(self):
        self._prev = (getattr(_BK_CTX, "action", None), getattr(_BK_CTX, "run_id", None))
        _RUN_SEQ[0] += 1
        _BK_CTX.action = self.action
        _BK_CTX.run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{_RUN_SEQ[0]}"
        return self

    def __exit__(self, *exc):
        _BK_CTX.action, _BK_CTX.run_id = self._prev
        return False


def current_backup_action():                                    ### NEW v0.19.1 I1 ###
    return getattr(_BK_CTX, "action", None) or "Edit"


def read_manifest(folder):                                      ### NEW v0.19.1 I1 ###
    try:
        with open(os.path.join(folder, MANIFEST_NAME), "r", encoding="utf-8") as f:
            m = json.load(f)
        return m if isinstance(m, dict) and isinstance(m.get("files"), list) else None
    except Exception:
        return None


def _write_manifest(folder, m):
    tmp = os.path.join(folder, MANIFEST_NAME + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=1, ensure_ascii=False)
    os.replace(tmp, os.path.join(folder, MANIFEST_NAME))


def _manifest_add(folder, original, backup_path, logger=None):  ### NEW v0.19.1 I1 ###
    """Record one backed-up file; the FIRST backup of an original in a folder
    is its pre-run state, later ones are not listed again."""
    try:
        with _MF_LOCK:
            m = _OPEN_MANIFESTS.get(folder) or read_manifest(folder) or {
                "version": 1, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action": current_backup_action(),
                "run_id": getattr(_BK_CTX, "run_id", None) or os.path.basename(folder),
                "files": []}
            orig = os.path.abspath(original)
            if any(os.path.normcase(f["original"]) == os.path.normcase(orig) for f in m["files"]):
                return
            st = os.stat(backup_path)
            m["files"].append({"original": orig, "backup": os.path.basename(backup_path),
                               "size": st.st_size, "mtime": st.st_mtime})
            _write_manifest(folder, m)
            _OPEN_MANIFESTS[folder] = m
    except Exception as e:
        if logger:
            logger.warning(f"Backup manifest not written in {folder}: {e}")


def note_written(paths):                                        ### NEW v0.19.1 I1 ###
    """After a change: remember how the run left every backed-up file under
    *paths* (files or movie folders) — size + mtime — so a later restore can
    warn when the file was changed again afterwards."""
    if not paths:
        return
    roots = [os.path.normcase(os.path.abspath(p)).rstrip("\\/") for p in paths if p]
    with _MF_LOCK:
        for folder, m in list(_OPEN_MANIFESTS.items()):
            changed = False
            for f in m["files"]:
                o = os.path.normcase(f["original"])
                if any(o == r or o.startswith(r + os.sep) for r in roots) and os.path.isfile(f["original"]):
                    st = os.stat(f["original"])
                    if f.get("after_mtime") != st.st_mtime or f.get("after_size") != st.st_size:
                        f["after_mtime"], f["after_size"] = st.st_mtime, st.st_size
                        changed = True
            if changed:
                try:
                    _write_manifest(folder, m)
                except Exception:
                    pass


def file_changed_since_run(entry):                              ### NEW v0.19.1 I1 ###
    """True / False / None (unknown: the run's result was never recorded)."""
    if "after_mtime" not in entry:
        return None
    try:
        st = os.stat(entry["original"])
    except OSError:
        return True
    return abs(st.st_mtime - entry["after_mtime"]) > 0.001 or st.st_size != entry.get("after_size")


def list_backup_runs(backup_root):                              ### NEW v0.19.1 I1 ###
    """All backup folders, newest first: {folder, name, created, action,
    run_id, files, movies, legacy}.  Folders made before v0.19.1 have no
    manifest → legacy (manual restore only).  Worker threads only."""
    runs = []
    try:
        entries = [e for e in os.scandir(backup_root) if e.is_dir() and e.name.startswith("backup_")]
    except OSError:
        return runs
    for e in entries:
        m = read_manifest(e.path)
        if m:
            files = m["files"]
            runs.append({"folder": e.path, "name": e.name, "created": m.get("created", ""),
                         "action": m.get("action", "Edit"), "run_id": m.get("run_id", e.name),
                         "files": files, "legacy": False,
                         "movies": len({os.path.dirname(f["original"]) for f in files})})
        else:
            try:
                n = sum(1 for _ in os.scandir(e.path))
                mt = re.search(r"_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})(?:_\d+)?$", e.name)
                created = (f"{mt.group(1)} {mt.group(2)}:{mt.group(3)}:{mt.group(4)}" if mt   # the folder name has the date
                           else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.stat().st_mtime)))
            except OSError:
                n, created = 0, ""
            runs.append({"folder": e.path, "name": e.name, "created": created, "action": "—",
                         "run_id": e.name, "files": [], "legacy": True, "movies": 0, "n_files": n})
    runs.sort(key=lambda r: (r["created"], r["name"]), reverse=True)
    return runs


def restore_backup_run(backup_root, folder, skip=(), logger=None):   ### NEW v0.19.1 I1 ###
    """Copy the files of one backup run back to where they came from.
    First the CURRENT files are backed up (action "Before undo — …"), so the
    undo can itself be undone.  Each file is written atomically (temp file in
    the same folder + os.replace).  *skip* = originals to leave alone.
    Returns (restored_paths, errors, safety_folder)."""
    m = read_manifest(folder)
    if not m:
        return [], ["No manifest — this backup can only be restored by hand."], None
    todo = [f for f in m["files"] if f["original"] not in set(skip)]
    ref = [None]
    with backup_action(f"Before undo — {m.get('action', 'Edit')} ({m.get('created', '')})"):
        for f in todo:
            if os.path.isfile(f["original"]):
                make_batch_backup(backup_root, "before_undo", ref, f["original"], logger=logger)
    restored, errors = [], []
    for f in todo:
        src = os.path.join(folder, f["backup"])
        dst = f["original"]
        tmp = dst + ".mcrestore"
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, tmp)           # copyfile: the restored file gets a new mtime
            os.replace(tmp, dst)
            restored.append(dst)
        except Exception as e:
            errors.append(f"{os.path.basename(dst)}: {e}")
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
    if logger:
        logger.info(f"Restored {len(restored)} file(s) from {folder} ({len(errors)} error(s))")
    return restored, errors, ref[0]


def make_backup(backup_root, movie_name, *file_paths, logger=None):
    """
    Create a timestamped backup of one or more NFO/XML files.

    Parameters
    ----------
    backup_root : str
        Root backup directory (e.g. <script_dir>/backup).
    movie_name : str
        Used to name the backup folder (spaces → underscores).
    *file_paths : str
        Absolute paths to files to back up.  Missing files are skipped.
    logger : logging.Logger | None

    Returns
    -------
    str | None
        Backup folder path, or None if nothing was copied / error occurred.
    """
    try:
        os.makedirs(backup_root, exist_ok=True)
        folder = _make_backup_folder_path(backup_root, movie_name)  # MODIFIED_BY_CLAUDE_v18
        copied = []
        for fp in file_paths:
            if fp and os.path.isfile(fp):
                os.makedirs(folder, exist_ok=True)
                dest = os.path.join(folder, os.path.basename(fp))
                shutil.copy2(fp, dest)
                copied.append(os.path.basename(fp))
                _manifest_add(folder, fp, dest, logger)             ### NEW v0.19.1 I1 ###
        if copied:
            if logger:
                logger.info(f"Backup created: {folder}  —  files: {', '.join(copied)}")
            return folder
        return None
    except Exception as e:
        if logger:
            logger.error(f"Backup failed for '{movie_name}': {e}")
        return None


def make_batch_backup(backup_root, movie_name, backup_folder_ref,
                      *file_paths, logger=None):
    """
    Batch-operation variant: creates one shared folder for the whole batch
    and reuses it for subsequent calls (via *backup_folder_ref*).

    Parameters
    ----------
    backup_root : str
    movie_name : str
        Used only for the initial folder name (first call in batch).
    backup_folder_ref : list[str|None]
        One-element mutable list.  Pass the same list for every call.
    *file_paths : str
    logger : logging.Logger | None

    Returns
    -------
    str | None
        The shared backup folder path.
    """
    try:
        if backup_folder_ref[0] is None:
            os.makedirs(backup_root, exist_ok=True)
            folder = _make_backup_folder_path(backup_root, movie_name, fallback="batch")  # MODIFIED_BY_CLAUDE_v18
            backup_folder_ref[0] = folder
            if logger:
                logger.info(f"Batch backup folder created: {folder}")
        folder = backup_folder_ref[0]
        copied = []
        for fp in file_paths:
            if fp and os.path.isfile(fp):
                os.makedirs(folder, exist_ok=True)
                dest = os.path.join(folder, os.path.basename(fp))
                if os.path.exists(dest):
                    base, ext = os.path.splitext(os.path.basename(fp))
                    idx = 2
                    while os.path.exists(dest):
                        dest = os.path.join(folder, f"{base}_{idx}{ext}")
                        idx += 1
                shutil.copy2(fp, dest)
                copied.append(os.path.basename(fp))
                _manifest_add(folder, fp, dest, logger)             ### NEW v0.19.1 I1 ###
        if copied and logger:
            logger.info(
                f"Batch backup — added to {folder}: {', '.join(copied)}")
        return folder
    except Exception as e:
        if logger:
            logger.error(f"Batch backup failed: {e}")
        return None


def clean_backup_folder_if_needed(backup_root, settings, active_folder=None,
                                  logger=None):
    """
    Auto-delete oldest backup_* subfolders when total size exceeds the limit.

    Parameters
    ----------
    backup_root : str
    settings : dict
        Reads "max_backup_size_mb" (int, 0 = disabled).
    active_folder : str | None
        The backup folder just created — never deleted even if over limit.
    logger : logging.Logger | None

    NOTE: Performs filesystem walk.  Call via run_async() from a UI thread
    when triggered from a button; call directly from worker threads during
    scan/backup operations (already off the UI thread in those contexts).
    """
    try:
        max_mb = settings.get("max_backup_size_mb", 500)
        if not max_mb or max_mb <= 0:
            return
        if not os.path.isdir(backup_root):
            return
        max_bytes = max_mb * 1024 * 1024

        def _folder_size(path):
            total = 0
            try:
                for e in os.scandir(path):
                    if e.is_file():
                        try:
                            total += e.stat().st_size
                        except Exception:
                            pass
            except Exception:
                pass
            return total

        backup_dirs = []
        for entry in os.scandir(backup_root):
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
            if (active_folder and
                    os.path.abspath(folder_path) == os.path.abspath(active_folder)):
                continue
            try:
                folder_size = _folder_size(folder_path)
                shutil.rmtree(folder_path)
                total_bytes -= folder_size
                if logger:
                    logger.info(
                        f"Backup cleanup: removed {folder_path}")
            except Exception as e:
                if logger:
                    logger.error(f"Backup cleanup failed for {folder_path}: {e}")
    except Exception as e:
        if logger:
            logger.error(f"clean_backup_folder_if_needed error: {e}")
