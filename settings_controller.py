# =============================================================================
# settings_controller.py
# Metadata & MediaClinic — Settings Business Logic
# Version: 0.19.4                                              ### MODIFIED v0.19.4 ###
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
import logging                                                   ### NEW v0.19.2 B36 ###
import os
import re
import shutil
import subprocess
import threading                                                 ### NEW v0.19.1 I1 ###
import time
import webbrowser

from settings_model import DEFAULT_SETTINGS

_log = logging.getLogger("MediaClinic")                          ### NEW v0.19.2 B36 ###


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
IGNORED_CACHE_PATH = os.path.join(get_config_dir(), "last_ignored.json")  ### NEW v0.19.2 B53 ###
NOT_DUP_PATH = os.path.join(get_config_dir(), "not_duplicates.json")       ### NEW v0.19.3 B64 ###
COLLECTIONS_CACHE_PATH = os.path.join(get_config_dir(), "collections_cache.json")   ### NEW v0.19.4 B110b ###
NO_COLL_PATH = os.path.join(get_config_dir(), "no_collection.json")       ### NEW v0.19.4 fix 3b ###
_NO_COLL_LOCK = threading.Lock()                                            ### NEW v0.19.4 fix 3b ###


def load_no_collection(logger=None):                              ### NEW v0.19.4 fix 3b ###
    """The movies the user marked "not in a collection": [{"path", "tmdb", "name", "when"}] ([] when absent).
    A file that cannot be read is kept as no_collection.json.corrupt-<date> and the list starts empty."""
    with _NO_COLL_LOCK:
        if not os.path.isfile(NO_COLL_PATH):
            return []
        try:
            with open(NO_COLL_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            movies = data.get("movies") if isinstance(data, dict) else None
            if not isinstance(movies, list):
                raise ValueError("no 'movies' list")
            return [m for m in movies if isinstance(m, dict) and (m.get("path") or m.get("tmdb"))]
        except Exception as e:
            dst = f"{NO_COLL_PATH}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}"
            try:
                shutil.copy2(NO_COLL_PATH, dst)
            except Exception:
                pass
            if logger:
                logger.warning(f"no_collection.json could not be read ({e}) — kept as {os.path.basename(dst)}; "
                               "the 'not in a collection' marks start empty")
            return []


def save_no_collection(movies):                                    ### NEW v0.19.4 fix 3b ###
    """Write the marks atomically (temp file + os.replace) under a lock."""
    with _NO_COLL_LOCK:
        try:
            tmp = NO_COLL_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "movies": list(movies)}, f, ensure_ascii=False, indent=1)
            os.replace(tmp, NO_COLL_PATH)
            return True
        except Exception:
            return False
_COLL_LOCK = threading.Lock()                                               ### NEW v0.19.4 B110b ###


def load_collections_cache():                                    ### NEW v0.19.4 B110b ###
    """{str(TMDB collection id): {"names", "overviews", "parts", "when"}}; {} when missing.  A file that cannot
    be read is kept as .corrupt-<date> (never overwritten by the next save)."""
    with _COLL_LOCK:
        try:
            if not os.path.isfile(COLLECTIONS_CACHE_PATH):
                return {}
            with open(COLLECTIONS_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            raise ValueError("not an object")
        except Exception as ex:
            try:
                dst = f"{COLLECTIONS_CACHE_PATH}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}"
                shutil.copy2(COLLECTIONS_CACHE_PATH, dst)
                os.remove(COLLECTIONS_CACHE_PATH)
                _log.warning(f"collections_cache.json could not be read ({ex}) — kept as {os.path.basename(dst)}")
            except Exception:
                pass
            return {}


def save_collections_cache(data):                                ### NEW v0.19.4 B110b ###
    """Atomic, locked save.  Returns True on success."""
    with _COLL_LOCK:
        try:
            tmp = COLLECTIONS_CACHE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, COLLECTIONS_CACHE_PATH)
            return True
        except Exception as ex:
            _log.warning(f"collections_cache.json not saved: {ex}")
            return False
_NOT_DUP_LOCK = threading.Lock()                                          ### NEW v0.19.3 B64 ###


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


_FFPROBE_SAVE_LOCK = threading.Lock()                           ### NEW v0.19.4 B93 ###


def save_ffprobe_cache(cache):                                  ### NEW v0.19.1 I5 ###
    """Atomic write (temp file + replace).  Worker threads only.
    ### MODIFIED v0.19.4 B93 ### under a lock, with a temp file of its own:
    two flushes at once used to collide on one ".tmp"."""
    with _FFPROBE_SAVE_LOCK:
        tmp = f"{FFPROBE_CACHE_PATH}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp, FFPROBE_CACHE_PATH)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass

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
    _save_json_atomic(FANARTTV_CACHE_PATH, keep, ensure_ascii=False, separators=(",", ":"))   # P2 (F12)

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


### NEW v0.19.2 B36 — a settings.json that exists but cannot be read is kept ###
# load_settings() copies it to settings.json.corrupt-YYYYMMDD-HHMMSS before the
# defaults are used, and records the copy here; the App tells the user once.
SETTINGS_LOAD_PROBLEM = {"corrupt_copy": None, "error": ""}


def _keep_corrupt_settings(err):                                ### NEW v0.19.2 B36 ###
    """Copy the unreadable settings.json aside (never overwritten by the next save)."""
    dst = f"{CONFIG_PATH}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}"
    try:
        shutil.copy2(CONFIG_PATH, dst)
    except Exception as e:
        _log.error(f"settings.json could not be read ({err}) and could not be copied aside: {e}")
        dst = None
    else:
        _log.error(f"settings.json could not be read ({err}); kept as {dst}; defaults in use")
    SETTINGS_LOAD_PROBLEM.update(corrupt_copy=dst, error=str(err))


def load_settings():
    """
    Load settings from CONFIG_PATH, deep-merge with DEFAULT_SETTINGS,
    and return the resulting dict.  Returns a deep copy of DEFAULT_SETTINGS
    on any read or parse error.
    ### MODIFIED v0.18.3 — deep copy of defaults, health_rules deep-merge,
    legacy quality-label migration (all moved here from the main script) ###
    ### MODIFIED v0.19.2 B36 — an existing file that does not parse is copied
    aside first (SETTINGS_LOAD_PROBLEM) instead of being silently replaced ###
    """
    merged = copy.deepcopy(DEFAULT_SETTINGS)
    try:
        if os.path.isfile(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError(f"top level is {type(data).__name__}, not an object")
            except Exception as e:                               ### NEW v0.19.2 B36 ###
                _keep_corrupt_settings(e)
                sync_quality_mirrors(merged)
                return merged
            for sub in ("improve_checks", "health_rules"):
                if isinstance(data.get(sub), dict):
                    d = dict(DEFAULT_SETTINGS[sub])
                    d.update(data[sub])
                    data[sub] = d
            merged.update(data)
            reset_wrong_types(merged)                            ### NEW v0.19.4 B94c ###
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
            _run_settings_migrations(merged)                     ### NEW v0.19.2 B35 ###
        else:
            # first start: nothing to migrate — the new defaults already apply
            merged["settings_migrations"] = list(_MIGRATIONS)
    except Exception:
        pass
    sync_quality_mirrors(merged)                                 ### NEW v0.19.0 ###
    return merged


### NEW v0.19.4 B94c — a value of the wrong type is reset to its default on load ###
def _type_ok(default, value):
    if isinstance(default, bool):
        return isinstance(value, bool) or (type(value) is int and value in (0, 1))
    if isinstance(default, (int, float)):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if isinstance(default, str):
        return isinstance(value, str)
    if isinstance(default, list):
        return isinstance(value, list)
    if isinstance(default, dict):
        return isinstance(value, dict)
    return True


def _fix_type(default, value):
    """(ok, value): the value as the default's type, or ok=False to reset it."""
    if _type_ok(default, value):
        return True, (bool(value) if isinstance(default, bool) else value)
    if isinstance(default, str) and isinstance(value, list) and all(isinstance(x, str) for x in value):
        return True, "\n".join(value)                          # e.g. a genre list stored as a list
    return False, None


def reset_wrong_types(merged):
    """A key whose value has the wrong type (e.g. "health_rules": null, which
    broke every later save) gets its default back.  Each reset is logged and
    the status bar says so once (SETTINGS_MIGRATION_STATUS).  Returns the
    reset key names."""
    reset = []
    for k, dv in DEFAULT_SETTINGS.items():
        if dv is None or k not in merged:
            continue
        ok, v = _fix_type(dv, merged[k])
        if ok:
            merged[k] = v
        else:
            _log.warning(f"Settings: '{k}' had the wrong type ({type(merged[k]).__name__}) — reset to the default")
            merged[k] = copy.deepcopy(dv)
            reset.append(k)
    for sub in ("improve_checks", "health_rules"):
        d = merged.get(sub)
        if not isinstance(d, dict):
            continue
        for k, dv in DEFAULT_SETTINGS[sub].items():
            if dv is None or k not in d:
                continue
            ok, v = _fix_type(dv, d[k])
            if ok:
                d[k] = v
            else:
                _log.warning(f"Settings: '{sub}.{k}' had the wrong type ({type(d[k]).__name__}) — reset to the default")
                d[k] = copy.deepcopy(dv)
                reset.append(f"{sub}.{k}")
    if reset:
        SETTINGS_MIGRATION_STATUS.append(
            f"Settings: {len(reset)} value{'' if len(reset) == 1 else 's'} of the wrong type reset to the default "   # v0.19.4 B105
            f"({', '.join(reset[:3])}{' …' if len(reset) > 3 else ''}) — see logs\\app.log")
    return reset


### NEW v0.19.2 B35 — one-time settings migrations ###
# Every rule is written to settings.json on the first Save & Apply, so a new
# default alone never reaches an existing user.  A migration runs exactly once
# (marker in "settings_migrations"); a user who turns a rule on again later is
# never overridden.  The App shows the notice once, through after().
_MIGRATIONS = ("b35_folder_rules_off", "b55_library_filter_reset", "b110_collection_column_hidden")
SETTINGS_MIGRATION_NOTICES = []                                  # one message box each (B35)
SETTINGS_MIGRATION_STATUS = []                                   # one status-bar line each (B55)
B55_STATUS = "Library filter reset to 'All libraries' — every library is shown again"
B35_NOTICE = ("Two health rules are now off by default: 'Missing folder image' and "
              "'Poster and folder image are different' (no media server needs them). "
              "Turn them on again in Settings → Health Rules if you want them.")


def _run_settings_migrations(merged):
    done = [m for m in (merged.get("settings_migrations") or []) if isinstance(m, str)]
    todo = [m for m in _MIGRATIONS if m not in done]
    if not todo:
        return
    if "b35_folder_rules_off" in todo:
        hr = merged.get("health_rules")
        if isinstance(hr, dict):
            was_on = [k for k in ("missing_folder", "poster_folder_identical") if hr.get(k)]
            hr["missing_folder"] = False
            hr["poster_folder_identical"] = False
            if was_on:
                SETTINGS_MIGRATION_NOTICES.append(B35_NOTICE)
                _log.info(f"Settings migration b35_folder_rules_off: switched off {', '.join(was_on)}")
    if "b55_library_filter_reset" in todo:                       ### NEW v0.19.2 B55 ###
        # a filter saved by v0.19.1 (Browse… set it without the user choosing it)
        # hid every other library; reset it once, say so in the status bar
        libs = merged.get("library_folders") or []
        if merged.get("library_filter") and len(libs) > 1:
            merged["library_filter"] = ""
            SETTINGS_MIGRATION_STATUS.append(B55_STATUS)
            _log.info("Settings migration b55_library_filter_reset: library filter reset to all libraries")
    if "b110_collection_column_hidden" in todo:                  ### NEW v0.19.4 B110a — the new column starts hidden ###
        hc = merged.get("hidden_columns")
        if isinstance(hc, list) and "collection" not in hc:
            merged["hidden_columns"] = hc + ["collection"]
    merged["settings_migrations"] = done + todo
    save_settings(merged)                                        # once: the markers are on disk now


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


_SETTINGS_LOCK = threading.Lock()                                ### NEW v0.19.2 B36 ###


def save_settings(settings):
    """Persist *settings* dict to CONFIG_PATH as JSON.
    ### MODIFIED v0.19.2 B36 ### — atomic (temp file in the same folder +
    os.replace) under a lock, so a crash or two saves at once (Tk thread +
    a worker's API pause) never leave a truncated file.  Errors are logged,
    never raised.  Returns True on success."""
    with _SETTINGS_LOCK:
        tmp = f"{CONFIG_PATH}.{os.getpid()}.tmp"
        try:
            text = json.dumps(settings, ensure_ascii=False, indent=2)   # serialise first: a failure never touches the file
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, CONFIG_PATH)
            return True
        except Exception as e:
            _log.error(f"settings.json not saved: {e}")
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
            return False


# ── Scan-results cache (v0.18.3) ──────────────────────────────────────────────
# The full scan-result list used to live inside settings.json ("last_results"),
# which made that file several MB and slowed every settings save.  It now has
# its own file next to settings.json.

RESULTS_SCHEMA = 2                                               ### NEW v0.19.4 I19 — 1 = the plain list before v0.19.4 ###
RESULTS_CACHE_NOTES = []                                         ### NEW v0.19.4 B93 — status-bar notes (the app shows them once) ###


def _keep_corrupt_results(why):                                  ### NEW v0.19.4 B93 ###
    """last_results.json could not be read: keep a copy (".corrupt-<date>")
    before anything can overwrite it, log it and leave a status-bar note."""
    try:
        if not os.path.isfile(RESULTS_CACHE_PATH) or os.path.getsize(RESULTS_CACHE_PATH) == 0:
            return None
        dst = f"{RESULTS_CACHE_PATH}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(RESULTS_CACHE_PATH, dst)
        _log.warning(f"last_results.json could not be read ({why}) — kept as {os.path.basename(dst)}")
        RESULTS_CACHE_NOTES.append(f"The last scan could not be read (kept as {os.path.basename(dst)}) — run a Full Scan")
        return dst
    except Exception as e:
        _log.error(f"last_results.json could not be read ({why}) and no copy was made: {e}")
        return None


def load_results_cache():
    """Return the cached scan-result list, or [] when absent/unreadable.
    ### MODIFIED v0.19.4 B93 ### an unreadable file is kept as .corrupt-<date>."""  ### NEW v0.18.3 ###
    try:
        if os.path.isfile(RESULTS_CACHE_PATH):
            with open(RESULTS_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("rows"), list):   ### NEW v0.19.4 I19 — {schema, kind, rows} ###
                return data["rows"]
            if isinstance(data, list):                          # the form before v0.19.4
                return data
            _keep_corrupt_results("not a list")
    except Exception as e:
        _keep_corrupt_results(e)
    return []


def load_results_cache_stepwise():                                ### NEW v0.19.3 I4 ###
    """load_results_cache, but decoded one row at a time: each step is short,
    so another thread (the Tk window) gets the GIL in between.  Worker threads
    only.  [] when absent / unreadable."""
    try:
        if not os.path.isfile(RESULTS_CACHE_PATH):
            return []
        with open(RESULTS_CACHE_PATH, "r", encoding="utf-8") as f:
            text = f.read()
        dec = json.JSONDecoder()
        i, n = 0, len(text)
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            return []                                           # an empty file: nothing to keep
        if text[i] == "{":                                      ### NEW v0.19.4 I19 — {schema, kind, rows}: rows come last ###
            j = text.find('"rows"', i)
            k = text.find("[", j) if j >= 0 else -1
            if k < 0:
                _keep_corrupt_results("no rows")
                return []
            i = k
        if text[i] != "[":
            _keep_corrupt_results("not a list")                 ### NEW v0.19.4 B93 ###
            return []
        i += 1
        rows = []
        while True:
            while i < n and text[i] in " \t\r\n,":
                i += 1
            if i >= n:
                _keep_corrupt_results("truncated")              ### NEW v0.19.4 B93 ###
                return []                                       # truncated file
            if text[i] == "]":
                return rows
            obj, i = dec.raw_decode(text, i)
            rows.append(obj)
            if len(rows) % 200 == 0:
                time.sleep(0)                                   # let the Tk thread run
    except Exception as e:
        _keep_corrupt_results(e)                                ### NEW v0.19.4 B93 ###
        return []


_JSON_SAVE_LOCK = threading.RLock()                                ### NEW v0.19.4 P2 (F12) ###


def _save_json_atomic(path, data, **dump_kw):                   ### NEW v0.19.4 P2 (F12) ###
    """One lock for the cache files, a temp file per thread (two saves at once used to share one ".tmp" and
    could publish a half-written file), the temp file removed on failure.  Raises on failure."""
    with _JSON_SAVE_LOCK:
        tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, **dump_kw)
            os.replace(tmp, path)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass


def save_results_cache(results):
    """Persist the scan-result list.  Returns True on success."""  ### NEW v0.18.3 ###
    try:
        ### MODIFIED v0.19.4 I19 — {schema, kind, rows} (rows LAST: the row-by-row loader reads them) ###
        _save_json_atomic(RESULTS_CACHE_PATH, {"schema": RESULTS_SCHEMA, "kind": "movies", "rows": list(results)},
                          ensure_ascii=False, default=str)       # P2 (F12)
        return True
    except Exception as e:
        _log.warning(f"Results cache not saved: {e}")
        return False


def load_ignored():                                              ### NEW v0.19.2 B53 ###
    """The last "Ignored folders" report ({} when absent/unreadable)."""
    try:
        if os.path.isfile(IGNORED_CACHE_PATH):
            with open(IGNORED_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_ignored(data):                                          ### NEW v0.19.2 B53 ###
    """Persist the "Ignored folders" report next to the results cache.
    Returns True on success."""
    try:
        _save_json_atomic(IGNORED_CACHE_PATH, data or {}, ensure_ascii=False, default=str)   # P2 (F12)
        return True
    except Exception:
        return False


def load_not_duplicates(logger=None):                             ### NEW v0.19.3 B64 ###
    """The user's "not a duplicate" pairs ([] when absent).  A file that cannot
    be read is kept as not_duplicates.json.corrupt-<date> and the list starts
    empty (logged), like settings.json (B36)."""
    with _NOT_DUP_LOCK:
        if not os.path.isfile(NOT_DUP_PATH):
            return []
        try:
            with open(NOT_DUP_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            pairs = data.get("pairs") if isinstance(data, dict) else None
            if not isinstance(pairs, list):
                raise ValueError("no 'pairs' list")
            return [p for p in pairs if isinstance(p, dict) and p.get("a") and p.get("b")]
        except Exception as e:
            dst = f"{NOT_DUP_PATH}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}"
            try:
                shutil.copy2(NOT_DUP_PATH, dst)
            except Exception:
                pass
            if logger:
                logger.warning(f"not_duplicates.json could not be read ({e}) — kept as {os.path.basename(dst)}; "
                               "the 'not a duplicate' marks start empty")
            return []


def save_not_duplicates(pairs):                                  ### NEW v0.19.3 B64 ###
    """Write the pairs atomically (temp file + os.replace) under a lock."""
    with _NOT_DUP_LOCK:
        try:
            tmp = NOT_DUP_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "pairs": list(pairs)}, f, ensure_ascii=False, indent=1)
            os.replace(tmp, NOT_DUP_PATH)
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

### NEW v0.19.2 B58 — FFmpeg / FFprobe found like the other apps (family item X1) ###
# The old finder looked only in the Settings folder and in the PATH MediaClinic
# started with, so a fresh winget install or TranscriptLab's <Home>\bin (added
# to the user PATH) was missed until a restart.  Same search as RadioSave 0.4.0;
# every candidate must run "-version" (cached); ffprobe comes from the same
# folder as ffmpeg.
FFMPEG_FOUND = {"how": "", "dir": ""}                            # shown in Settings → Tools
_FF_OK_CACHE = {}
FFMPEG_GLOBS_WIN = [
    r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe",
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\*[Ff][Ff]mpeg*\*\bin\ffmpeg.exe",
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\*[Ff][Ff]mpeg*\bin\ffmpeg.exe",
    r"%PROGRAMFILES%\WinGet\Links\ffmpeg.exe",
    r"%USERPROFILE%\scoop\shims\ffmpeg.exe",
    r"%USERPROFILE%\scoop\apps\ffmpeg*\current\bin\ffmpeg.exe",
    r"%ProgramData%\chocolatey\bin\ffmpeg.exe",
    r"%ProgramFiles%\ffmpeg*\bin\ffmpeg.exe",
    r"%LOCALAPPDATA%\Programs\ffmpeg*\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\ffmpeg*\bin\ffmpeg.exe",
    r"%USERPROFILE%\Downloads\ffmpeg*\bin\ffmpeg.exe",
    r"%USERPROFILE%\Downloads\ffmpeg*\*\bin\ffmpeg.exe",
]
FFMPEG_DEEP_ROOTS_WIN = [r"%LOCALAPPDATA%\Microsoft\WinGet\Packages", r"%USERPROFILE%\scoop\apps",
                         r"%ProgramData%\chocolatey\lib", r"%USERPROFILE%\Downloads", r"%LOCALAPPDATA%\Programs"]


def _ff_exe(name):
    return name + ".exe" if os.name == "nt" else name


def ff_works(path):                                              ### NEW v0.19.2 B58 ###
    """True when *path* runs and answers '-version' (cached per path)."""
    if not path or not os.path.isfile(path):
        return False
    key = os.path.normcase(os.path.abspath(path))
    if key in _FF_OK_CACHE:
        return _FF_OK_CACHE[key]
    try:
        r = subprocess.run([path, "-hide_banner", "-version"], capture_output=True, timeout=20,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        ok = r.returncode == 0 and b" version " in (r.stdout or b"").lower()
    except Exception:
        ok = False
    _FF_OK_CACHE[key] = ok
    return ok


def forget_ffmpeg_cache():                                      ### NEW v0.19.2 B58 ###
    _FF_OK_CACHE.clear()


def live_path_dirs():                                            ### NEW v0.19.2 B58 ###
    """PATH as the registry has it NOW (HKCU + HKLM, read only) plus this
    process's PATH, so a new install is found without restarting."""
    dirs = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d.strip()]
    if os.name == "nt":
        try:
            import winreg
            for hive, key in ((winreg.HKEY_CURRENT_USER, r"Environment"),
                              (winreg.HKEY_LOCAL_MACHINE,
                               r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        val, _t = winreg.QueryValueEx(k, "Path")
                    dirs += [d for d in str(val).split(os.pathsep) if d.strip()]
                except OSError:
                    pass
        except ImportError:
            pass
    out, seen = [], set()
    for d in dirs:
        d = os.path.expandvars(d.strip().strip('"'))
        k = os.path.normcase(os.path.normpath(d))
        if d and k not in seen:
            seen.add(k); out.append(d)
    return out


def _iter_globs(patterns):
    import glob
    for p in patterns:
        for g in sorted(glob.glob(os.path.expandvars(os.path.expanduser(p)))):
            yield g


def find_ffmpeg_ffprobe(custom_dir="", deep=False):
    """
    Locate ffmpeg and ffprobe executables.

    ### REWRITTEN v0.19.2 B58 ### search order: the Settings folder (a file or a
    folder, also its bin\\) → shutil.which → the PATH read live from the
    registry → the known install folders (winget, scoop, Chocolatey, Program
    Files, C:\\ffmpeg*, Downloads) → with *deep* a depth-limited scan.  Both
    tools come from one folder and must answer "-version".  FFMPEG_FOUND
    records where and how.

    Returns
    -------
    (ffmpeg_path, ffprobe_path) : tuple[str|None, str|None]
    """
    ffn, fpn = _ff_exe("ffmpeg"), _ff_exe("ffprobe")

    def _pair(folder, how):
        if not folder:
            return None
        ff, fp = os.path.join(folder, ffn), os.path.join(folder, fpn)
        if ff_works(ff) and ff_works(fp):
            FFMPEG_FOUND.update(how=how, dir=folder)
            return ff, fp
        return None

    custom = os.path.expandvars(str(custom_dir or "").strip().strip('"'))
    if custom:
        base = os.path.dirname(custom) if os.path.isfile(custom) else custom
        for folder in (base, os.path.join(base, "bin")):
            hit = _pair(folder, "Settings folder")
            if hit:
                return hit
    w = shutil.which("ffmpeg")
    if w:
        hit = _pair(os.path.dirname(w), "PATH")
        if hit:
            return hit
    for d in live_path_dirs():
        hit = _pair(d, "PATH (registry)")
        if hit:
            return hit
    if os.name == "nt":
        for cand in _iter_globs(FFMPEG_GLOBS_WIN):
            hit = _pair(os.path.dirname(cand), "known install folder")
            if hit:
                return hit
        if deep:
            for root in _iter_globs(FFMPEG_DEEP_ROOTS_WIN):
                base_depth = root.rstrip(os.sep).count(os.sep)
                for cur, subdirs, files in os.walk(root):
                    if cur.count(os.sep) - base_depth >= 5:
                        subdirs[:] = []
                        continue
                    if ffn.lower() in (f.lower() for f in files):
                        hit = _pair(cur, "found by scan")
                        if hit:
                            return hit
    FFMPEG_FOUND.update(how="not found", dir="")
    return None, None


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
    """Return the backup root directory path (not created here).
    ### MODIFIED v0.19.2 B31 ### MEDIACLINIC_BACKUP_DIR overrides it (the
    self-test sets it, so its test backups never land in the program's
    backup\\ folder), like MEDIACLINIC_CONFIG_DIR for the settings."""
    override = os.environ.get("MEDIACLINIC_BACKUP_DIR", "").strip()
    ### MODIFIED v0.19.4 P5 (user decision 1) ### with the settings (%APPDATA%\MediaMetadataClinic\backup), not next
    ### to the program: an update installs the new version into a new folder, and Backup History / Undo lost every run
    return override or os.path.join(get_config_dir(), "backup")


def migrate_legacy_backups(old_root, new_root, logger=None):     ### NEW v0.19.4 P5 ###
    """Move the backup_* runs of the old place (<program folder>\\backup) to *new_root*, once: a run already there is
    left where it is (named in the log).  The old folder is removed when it is empty.  Returns (moved, problems).
    The caller never calls this while a test override is set (it would move real backups)."""
    if not old_root or not os.path.isdir(old_root):
        return 0, []
    if os.path.normcase(os.path.abspath(old_root)) == os.path.normcase(os.path.abspath(new_root)):
        return 0, []
    os.makedirs(new_root, exist_ok=True)
    moved, problems = 0, []
    for e in sorted(os.scandir(old_root), key=lambda x: x.name):
        if not (e.is_dir() and e.name.startswith("backup_")):
            continue
        dst = os.path.join(new_root, e.name)
        if os.path.exists(dst):
            problems.append(f"{e.name}: already in {new_root} — left in {old_root}")
            continue
        try:
            shutil.move(e.path, dst)
            moved += 1
        except Exception as ex:
            problems.append(f"{e.name}: {ex}")
    try:
        if not os.listdir(old_root):
            os.rmdir(old_root)
    except OSError:
        pass
    if logger and (moved or problems):
        logger.info(f"Backups: {moved} run(s) moved from {old_root} to {new_root}"
                    + (f"; not moved: {'; '.join(problems[:5])}" if problems else ""))
    return moved, problems


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
    is its pre-run state, later ones are not listed again.
    ### v0.19.4 B80 ### True when the manifest knows the file; False when it
    could not be written (the backup then does not count: Undo needs it)."""
    try:
        with _MF_LOCK:
            m = _OPEN_MANIFESTS.get(folder) or read_manifest(folder) or {
                "version": 1, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action": current_backup_action(),
                "run_id": getattr(_BK_CTX, "run_id", None) or os.path.basename(folder),
                "files": []}
            orig = os.path.abspath(original)
            if any(os.path.normcase(f["original"]) == os.path.normcase(orig) for f in m["files"]):
                return True
            st = os.stat(backup_path)
            m["files"].append({"original": orig, "backup": os.path.basename(backup_path),
                               "size": st.st_size, "mtime": st.st_mtime})
            _write_manifest(folder, m)
            _OPEN_MANIFESTS[folder] = m
        return True
    except Exception as e:
        if logger:
            logger.error(f"Backup manifest not written in {folder}: {e} — the backup does not count")   ### MODIFIED v0.19.4 B80 ###
        return False


def note_created(backup_root, movie_name, backup_folder_ref, path, made_dir=None, logger=None):   ### NEW v0.19.4 B110g ###
    """A file the run CREATED (there was no earlier version to back up): the run's manifest lists it, so Undo
    removes it, and the folder *made_dir* the run made when it is empty afterwards.  True when recorded."""
    try:
        if backup_folder_ref[0] is None:
            os.makedirs(backup_root, exist_ok=True)
            backup_folder_ref[0] = _make_backup_folder_path(backup_root, movie_name, fallback="batch")
        folder = backup_folder_ref[0]
        os.makedirs(folder, exist_ok=True)
        with _MF_LOCK:
            m = _OPEN_MANIFESTS.get(folder) or read_manifest(folder) or {
                "version": 1, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action": current_backup_action(),
                "run_id": getattr(_BK_CTX, "run_id", None) or os.path.basename(folder),
                "files": []}
            orig = os.path.abspath(path)
            if any(os.path.normcase(f["original"]) == os.path.normcase(orig) for f in m["files"]):
                return True
            st = os.stat(path)
            ent = {"original": orig, "backup": None, "created": True,
                   "made_dir": os.path.abspath(made_dir) if made_dir else None, "size": 0, "mtime": 0}
            if not os.path.isdir(path):                          # v0.19.4 P3: a folder's time changes with its files
                ent.update(after_mtime=st.st_mtime, after_size=st.st_size)
            m["files"].append(ent)
            _write_manifest(folder, m)
            _OPEN_MANIFESTS[folder] = m
        return True
    except Exception as e:
        if logger:
            logger.error(f"Backup manifest: created file not recorded ({path}): {e}")
        return False


def note_written(paths):                                        ### NEW v0.19.1 I1 ###
    """After a change: remember how the run left every backed-up file under
    *paths* (files or movie folders) — size + mtime — so a later restore can
    warn when the file was changed again afterwards.
    ### v0.19.4 B76 ### only the NEWEST run of this session that lists a file
    is updated: an older run keeps the state it left, so restoring it later
    still warns that a newer run (or a hand edit) changed the file."""
    if not paths:
        return
    roots = [os.path.normcase(os.path.abspath(p)).rstrip("\\/") for p in paths if p]
    with _MF_LOCK:
        newest = {}                                             # original → (folder, entry) of the newest run
        for folder, m in _OPEN_MANIFESTS.items():               # insertion order = the order the runs began
            for f in m["files"]:
                o = os.path.normcase(f["original"])
                if any(o == r or o.startswith(r + os.sep) for r in roots):
                    newest[o] = (folder, f)
        dirty = set()
        for _o, (folder, f) in newest.items():
            if os.path.isfile(f["original"]):
                st = os.stat(f["original"])
                if f.get("after_mtime") != st.st_mtime or f.get("after_size") != st.st_size:
                    f["after_mtime"], f["after_size"] = st.st_mtime, st.st_size
                    dirty.add(folder)
        for folder, m in list(_OPEN_MANIFESTS.items()):
            if folder in dirty:
                try:
                    _write_manifest(folder, m)
                except Exception:
                    pass


def note_renamed(original, new_path):                         ### NEW v0.19.3 B73 ###
    """After a rename (e.g. "<folder>.nfo" → "<video>.nfo"): mark the backed-up
    *original* of this session's runs as renamed, so Undo puts the old name
    back and removes the new one.  True when an entry was found."""
    orig = os.path.normcase(os.path.abspath(original))
    found = False
    rid = getattr(_BK_CTX, "run_id", None)                     # only this run's backup, not older runs
    with _MF_LOCK:
        _items = list(_OPEN_MANIFESTS.items())
        if not rid:                                             ### v0.19.4 (F11): no run → only the NEWEST run holding it ###
            _items = [it for it in _items if any(os.path.normcase(f["original"]) == orig for f in it[1]["files"])][-1:]
        for folder, m in _items:
            if rid and m.get("run_id") not in (rid, None):
                continue
            for f in m["files"]:
                if os.path.normcase(f["original"]) == orig:
                    f["renamed_to"] = os.path.abspath(new_path)
                    try:
                        st = os.stat(new_path)
                        f["after_mtime"], f["after_size"] = st.st_mtime, st.st_size
                    except OSError:
                        pass
                    try:
                        _write_manifest(folder, m)
                    except Exception:
                        pass
                    found = True
    return found


def file_changed_since_run(entry):                              ### NEW v0.19.1 I1 ###
    """True / False / None (unknown: the run's result was never recorded).
    ### v0.19.3 B73 ### a renamed file is checked under its new name."""
    if "after_mtime" not in entry:
        return None
    try:
        st = os.stat(entry.get("renamed_to") or entry["original"])
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
    ### NEW v0.19.4 B75 ### runs the size cleanup removed (their folder is gone)
    have = {r["name"] for r in runs}
    root = os.path.normcase(os.path.abspath(backup_root))
    for rec in read_cleanup_log():
        if os.path.normcase(str(rec.get("root", ""))) != root or rec["name"] in have:
            continue
        have.add(rec["name"])
        runs.append({"folder": None, "name": rec["name"], "created": rec.get("created", ""),
                     "action": rec.get("action", "—"), "run_id": rec["name"], "files": [],
                     "legacy": False, "removed": rec.get("removed", "?"),
                     "movies": rec.get("movies", 0), "n_files": rec.get("files")})
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
    restored, errors = [], []
    unsafe = set()                                              ### NEW v0.19.4 B80 ###
    with backup_action(f"Before undo — {m.get('action', 'Edit')} ({m.get('created', '')})"):
        for f in todo:
            ok = True
            if os.path.isfile(f["original"]):
                ok = make_batch_backup(backup_root, "before_undo", ref, f["original"], logger=logger) is not None
            _ren = f.get("renamed_to")                         ### NEW v0.19.3 B73 ###
            if ok and _ren and os.path.isfile(_ren) and os.path.normcase(_ren) != os.path.normcase(f["original"]):
                ok = make_batch_backup(backup_root, "before_undo", ref, _ren, logger=logger) is not None
            if not ok:                                         ### NEW v0.19.4 B80 — never overwrite without a safety copy ###
                unsafe.add(f["original"])
                errors.append(f"{os.path.basename(f['original'])}: not restored — the safety backup of the current file failed")
    todo = [f for f in todo if f["original"] not in unsafe]
    made_dirs = []                                              ### NEW v0.19.4 B110g ###
    for f in todo:
        dst = f["original"]
        if f.get("created"):                                    ### NEW v0.19.4 B110g — the run made this file: Undo removes it ###
            try:
                if os.path.isfile(dst):
                    os.remove(dst)
                if f.get("made_dir"):
                    made_dirs.append(f["made_dir"])
                restored.append(dst)
            except Exception as e:
                errors.append(f"{os.path.basename(dst)}: {e}")
            continue
        src = os.path.join(folder, f["backup"])
        tmp = dst + ".mcrestore"
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, tmp)           # copyfile: the restored file gets a new mtime
            os.replace(tmp, dst)
            restored.append(dst)
            _ren = f.get("renamed_to")                         ### NEW v0.19.3 B73 — the new name goes ###
            if _ren and os.path.normcase(_ren) != os.path.normcase(dst) and os.path.isfile(_ren):
                os.remove(_ren)
                ### NEW v0.19.4 P3 (F10) — undoing THIS undo must remove the restored name again ###
                with backup_action(f"Before undo — {m.get('action', 'Edit')} ({m.get('created', '')})"):
                    note_created(backup_root, "before_undo", ref, dst, None, logger=logger)
        except Exception as e:
            errors.append(f"{os.path.basename(dst)}: {e}")
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
    for md in sorted(set(made_dirs), key=lambda p: -len(p)):     ### NEW v0.19.4 B110g; P3 — deepest first ###
        try:
            if os.path.isdir(md) and not os.listdir(md):
                os.rmdir(md)
        except OSError as e:
            errors.append(f"{os.path.basename(md)}: {e}")
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
                if not _manifest_add(folder, fp, dest, logger):     ### MODIFIED v0.19.4 B80 — no manifest = no backup ###
                    return None
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
                if not _manifest_add(folder, fp, dest, logger):     ### MODIFIED v0.19.4 B80 — no manifest = no backup ###
                    return None
        if copied and logger:
            logger.info(
                f"Batch backup — added to {folder}: {', '.join(copied)}")
        return folder
    except Exception as e:
        if logger:
            logger.error(f"Batch backup failed: {e}")
        return None


### NEW v0.19.4 B75 (D2) — which runs the automatic size cleanup leaves alone ###
_SESSION_START = time.time()
BACKUP_PROTECT_DAYS = 14            # a constant (D2); a setting only if the user asks
BACKUP_CLEANUP_LOG_PATH = os.path.join(get_config_dir(), "backup_cleanup_log.json")
_CLEANUP_LOG_MAX = 300
_BK_NAME_DATE = re.compile(r"_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})(?:_\d+)?$")


def _run_created_ts(path, m=None):                               ### NEW v0.19.4 B75 ###
    """When a backup run was made (epoch seconds): the manifest's "created",
    else the date in the folder name, else the folder's mtime.  Not the
    folder's ctime: a copied or moved backup folder gets a new one."""
    if m is None:
        m = read_manifest(path)
    try:
        if m and m.get("created"):
            return time.mktime(time.strptime(m["created"], "%Y-%m-%d %H:%M:%S"))
    except (ValueError, OverflowError, TypeError):
        pass
    mt = _BK_NAME_DATE.search(os.path.basename(path))
    if mt:
        try:
            return time.mktime(time.strptime(f"{mt.group(1)} {mt.group(2)}:{mt.group(3)}:{mt.group(4)}",
                                             "%Y-%m-%d %H:%M:%S"))
        except (ValueError, OverflowError):
            pass
    try:
        return os.stat(path).st_mtime
    except OSError:
        return time.time()                                      # unknown → treated as new (kept)


def backup_run_protected(path, m=None, now=None):                ### NEW v0.19.4 B75 (D2) ###
    """True for a run of this session or one younger than BACKUP_PROTECT_DAYS:
    the automatic size cleanup never deletes it."""
    key = os.path.normcase(os.path.abspath(path))
    with _MF_LOCK:
        if any(os.path.normcase(os.path.abspath(f)) == key for f in _OPEN_MANIFESTS):
            return True
    created = _run_created_ts(path, m)
    now = time.time() if now is None else now
    return created >= _SESSION_START - 1 or now - created < BACKUP_PROTECT_DAYS * 86400


def read_cleanup_log():                                         ### NEW v0.19.4 B75 ###
    """The runs the size cleanup removed: [{root, name, created, action, files,
    movies, size, removed}], oldest first."""
    try:
        with open(BACKUP_CLEANUP_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [r for r in data if isinstance(r, dict) and r.get("name")] if isinstance(data, list) else []
    except Exception:
        return []


def _append_cleanup_log(records, logger=None):
    if not records:
        return
    try:
        with _MF_LOCK:
            data = (read_cleanup_log() + records)[-_CLEANUP_LOG_MAX:]
            os.makedirs(os.path.dirname(BACKUP_CLEANUP_LOG_PATH) or ".", exist_ok=True)
            tmp = BACKUP_CLEANUP_LOG_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, ensure_ascii=False)
            os.replace(tmp, BACKUP_CLEANUP_LOG_PATH)
    except Exception as e:
        if logger:
            logger.warning(f"Backup cleanup log not written: {e}")


def _tree_size(path):
    total = 0
    for dp, _dn, fn in os.walk(path):
        for n in fn:
            try:
                total += os.path.getsize(os.path.join(dp, n))
            except OSError:
                pass
    return total


def _fmt_mb(n):
    return f"{n / (1024 * 1024):.1f} MB"


def backup_run_size_warning(run_bytes, settings):               ### NEW v0.19.4 B75 (D2) ###
    """The warning shown before a run whose backup alone is larger than the
    size limit; None when it fits, or when the limit / the cleanup is off."""
    max_mb = settings.get("max_backup_size_mb", 500)
    if (not settings.get("backup_cleanup_enabled", True) or not isinstance(max_mb, (int, float))
            or isinstance(max_mb, bool) or max_mb <= 0 or run_bytes <= max_mb * 1024 * 1024):
        return None
    return (f"⚠ This run backs up {_fmt_mb(run_bytes)}, more than the backup size limit "
            f"({max_mb} MB, Settings → Backup).\nThe backup is kept anyway: backups from this session "
            f"and from the last {BACKUP_PROTECT_DAYS} days are never deleted automatically, so the "
            f"backup folder will be larger than the limit for a while.")


def clean_backup_folder_if_needed(backup_root, settings, active_folder=None,
                                  logger=None):
    """
    Auto-delete the oldest backup_* runs when the total size exceeds the limit.
    ### MODIFIED v0.19.4 B75 (D2) ### runs from this session and from the last
    BACKUP_PROTECT_DAYS days are never deleted (the limit can then be passed);
    every removed run goes into the cleanup log, so Backup History shows
    "removed by the size cleanup on <date>" instead of an Undo that cannot work.

    Parameters
    ----------
    backup_root : str
    settings : dict
        Reads "max_backup_size_mb" (int, 0 = disabled) and "backup_cleanup_enabled".
    active_folder : str | None
        The backup folder just created — never deleted even if over limit.
    logger : logging.Logger | None

    Returns {"total": bytes after, "limit": bytes, "removed": [folder names]},
    or None (cleanup off, no folder, error).

    NOTE: Performs filesystem walk.  Call via run_async() from a UI thread
    when triggered from a button; call directly from worker threads during
    scan/backup operations (already off the UI thread in those contexts).
    """
    try:
        if not settings.get("backup_cleanup_enabled", True):       ### NEW v0.19.3 I12 — the switch is honoured ###
            return None
        max_mb = settings.get("max_backup_size_mb", 500)
        if not max_mb or max_mb <= 0:
            return None
        if not os.path.isdir(backup_root):
            return None
        max_bytes = max_mb * 1024 * 1024

        runs = []
        for entry in os.scandir(backup_root):
            if entry.is_dir() and entry.name.startswith("backup_"):
                runs.append((entry.path, _tree_size(entry.path)))   # sub-folders too (v0.19.3 I12)
        total_bytes = sum(sz for _p, sz in runs)
        if total_bytes <= max_bytes:
            return {"total": total_bytes, "limit": max_bytes, "removed": []}

        info = []
        for folder_path, folder_size in runs:
            m = read_manifest(folder_path)
            info.append((_run_created_ts(folder_path, m), folder_path, folder_size, m))
        info.sort(key=lambda x: (x[0], x[1]))                  # oldest first
        now = time.time()
        removed, records = [], []
        for created, folder_path, folder_size, m in info:
            if total_bytes <= max_bytes:
                break
            if (active_folder and os.path.normcase(os.path.abspath(folder_path))
                    == os.path.normcase(os.path.abspath(active_folder))):
                continue
            if backup_run_protected(folder_path, m, now):       ### NEW v0.19.4 B75 (D2) ###
                continue
            try:
                shutil.rmtree(folder_path)
            except Exception as e:
                if logger:
                    logger.error(f"Backup cleanup failed for {folder_path}: {e}")
                continue
            total_bytes -= folder_size
            removed.append(os.path.basename(folder_path))
            files = m["files"] if m else []
            records.append({"root": os.path.abspath(backup_root), "name": os.path.basename(folder_path),
                            "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created)),
                            "action": m.get("action", "Edit") if m else "—",
                            "files": len(files) if m else None,
                            "movies": len({os.path.dirname(f.get("original", "")) for f in files}),
                            "size": folder_size, "removed": time.strftime("%Y-%m-%d %H:%M")})
            if logger:
                logger.info(f"Backup cleanup: removed {folder_path}")
        _append_cleanup_log(records, logger)
        if total_bytes > max_bytes and logger:
            logger.info(f"Backup cleanup: {_fmt_mb(total_bytes - max_bytes)} over the limit; the rest is "
                        f"protected (this session / the last {BACKUP_PROTECT_DAYS} days)")
        return {"total": total_bytes, "limit": max_bytes, "removed": removed}
    except Exception as e:
        if logger:
            logger.error(f"clean_backup_folder_if_needed error: {e}")
        return None
