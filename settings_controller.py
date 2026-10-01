# =============================================================================
# settings_controller.py
# Metadata & MediaClinic — Settings Business Logic
# Version: 0.14.0
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# All non-UI logic that the settings subsystem needs:
#   - Persistent storage (load / save JSON)
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

import json
import os
import re
import shutil
import subprocess
import time
import webbrowser

from settings_model import DEFAULT_SETTINGS


# ── Persistent storage ────────────────────────────────────────────────────────

def get_config_dir():
    """Return (and create if necessary) the platform config directory."""
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get(
            "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
    d = os.path.join(base, "MediaMetadataClinic")
    os.makedirs(d, exist_ok=True)
    return d


CONFIG_PATH = os.path.join(get_config_dir(), "settings.json")


def load_settings():
    """
    Load settings from CONFIG_PATH, deep-merge with DEFAULT_SETTINGS,
    and return the resulting dict.  Returns a copy of DEFAULT_SETTINGS
    on any read or parse error.
    """
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            # Deep-merge improve_checks sub-dict
            if "improve_checks" in data:
                ic = dict(DEFAULT_SETTINGS["improve_checks"])
                ic.update(data["improve_checks"])
                data["improve_checks"] = ic
            merged.update(data)
            return merged
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    """Persist *settings* dict to CONFIG_PATH as JSON.  Silent on error."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


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
                [path, "-version"], capture_output=True, text=True, timeout=10,
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
