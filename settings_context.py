# =============================================================================
# settings_context.py
# Metadata & MediaClinic — Settings Context Object
# Version: 0.14.0
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# Defines SettingsContext — the single object that carries all shared state
# and callable dependencies into SettingsDialog, replacing the module-level
# global injection pattern used in v0.13.x.
#
# Also provides run_async(), a thin wrapper that moves any callable off the
# UI thread and optionally delivers its result back via root.after(0, …).
#
# RULES (enforced by CLAUDE_RULES.md)
# ------------------------------------
#   • SettingsContext is a plain dataclass — no methods, no logic
#   • run_async() must never be called with a callback unless root is also
#     supplied; omitting root with a callback raises ValueError immediately
#   • No tkinter imports at module level; root is accepted as a parameter
#     only inside run_async() so the module remains importable without Tk
# =============================================================================

import threading
from dataclasses import dataclass
from typing import Callable


@dataclass
class SettingsContext:
    """
    All shared state and injectable callables for SettingsDialog.

    Attributes
    ----------
    app_name : str
    settings : dict
        Live settings dict.  The dialog mutates this dict directly on Save.
    defaults : dict
        Read-only defaults (DEFAULT_SETTINGS from settings_model).
    tag_pairs : list
        Default NFO↔XML tag comparison pairs.
    world_languages : list[tuple[str, str]]
        ISO-639-1 code + display name pairs.
    logger : logging.Logger | None
    ffmpeg_finder : callable
        Signature: (custom_dir: str) -> (ffmpeg_path, ffprobe_path)
        NOTE: runs subprocess — always call via run_async from UI thread.
    notepadpp_finder : callable
        Signature: () -> str | None
    ffmpeg_tester : callable
        Signature: (ff_path, fp_path) -> (ff_ok, fp_ok, ff_msg, fp_msg)
        NOTE: runs subprocess — always call via run_async from UI thread.
    save_settings : callable
        Signature: (settings: dict) -> None
    refresh_ffmpeg : callable
        Signature: () -> None
        Refreshes the global FFMPEG_PATH / FFPROBE_PATH in the main module.
    detect_browsers : callable
        Signature: () -> list[tuple[str, str]]
        NOTE: filesystem scan — always call via run_async from UI thread.
    open_url : callable
        Signature: (url: str) -> None
    poster_quality_tiers : list
        From settings_model.POSTER_QUALITY_TIERS.
    fanart_quality_tiers : list
        From settings_model.FANART_QUALITY_TIERS.
    clean_backup : callable
        Signature: (active_folder: str | None) -> None
        NOTE: filesystem walk — always call via run_async from UI thread
        when called from a button handler.
    backup_root : str
        Absolute path to the backup root directory.
    """
    app_name:            str
    settings:            dict
    defaults:            dict
    tag_pairs:           list
    world_languages:     list
    logger:              object                  # logging.Logger | None
    ffmpeg_finder:       Callable
    notepadpp_finder:    Callable
    ffmpeg_tester:       Callable
    save_settings:       Callable
    refresh_ffmpeg:      Callable
    detect_browsers:     Callable
    open_url:            Callable
    poster_quality_tiers: list
    fanart_quality_tiers: list
    clean_backup:        Callable
    backup_root:         str


# ── run_async ─────────────────────────────────────────────────────────────────

def run_async(fn, callback=None, root=None):
    """
    Run *fn* on a daemon thread, optionally delivering its return value
    back to the Tk event loop via ``root.after(0, callback(result))``.

    Parameters
    ----------
    fn : callable
        Zero-argument callable.  Its return value is passed to *callback*.
    callback : callable | None
        Called on the main thread with fn()'s return value.
        Requires *root* to be supplied.
    root : tk.Widget | None
        Any Tk widget — used only for its .after() method.
        Required when *callback* is not None.

    Raises
    ------
    ValueError
        If *callback* is supplied without *root*.

    Example
    -------
    >>> run_async(
    ...     fn=lambda: find_ffmpeg_ffprobe(path),
    ...     callback=lambda result: status_label.configure(text=str(result)),
    ...     root=dialog,
    ... )
    """
    if callback is not None and root is None:
        raise ValueError("run_async: root must be supplied when callback is not None")

    def _worker():
        result = fn()
        if callback is not None:
            root.after(0, lambda: callback(result))

    threading.Thread(target=_worker, daemon=True).start()
