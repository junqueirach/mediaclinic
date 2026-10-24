# =============================================================================
# settings_test_harness.py
# Metadata & MediaClinic — Settings Subsystem Test Harness
# Version: 0.19.2  (12 tabs; T09 pumps a real mainloop; T13–T15 added in v0.19.1 I9, T16 in B24, T18 in v0.19.2 B28)
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# Verifies the settings subsystem works correctly without requiring a real
# media library or user interaction.  Runs headlessly using a hidden Tk root.
#
# WHAT IS TESTED
# --------------
#   1. SettingsContext can be instantiated with fake callables
#   2. Fake settings load and are well-formed
#   3. SettingsDialog opens without exception
#   4. All 11 tabs build without exception
#   5. Snapshot is taken on open (structured shape)
#   6. Simulated Save writes expected values into the settings dict
#   7. _rescan_changed() returns False (no changes) after a neutral save
#   8. _rescan_changed() returns True when a relevant setting is changed
#   9. Browser-only change does NOT set changed["any"] = True
#  10. No UI freeze: dialog opens, saves, and closes within 3 seconds
#  11. run_async delivers callback on main thread without deadlock
#  13. Image Sizes ↔ Health Rules quality combos mirror both ways   (v0.19.1)
#  14. The v0.19.0/v0.19.1 health-rule rows exist and save          (v0.19.1)
#  15. The window-memory hook is called by the dialog               (v0.19.1)
#  17. fanart.tv key block: link, save, key-only change = no rescan (v0.19.1 I10)
#
# RUN
# ---
#   python settings_test_harness.py
#
# Exit code 0 = all tests passed.
# =============================================================================

import os            # v0.19.2 B28 — T18 reads the schema next to this file
import sys
import threading
import time
import tkinter as tk
import traceback
import logging

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("TestHarness")

# ── Import subsystem ──────────────────────────────────────────────────────────
from settings_model import (
    DEFAULT_SETTINGS, DEFAULT_TAG_PAIRS, WORLD_LANGUAGES,
    POSTER_QUALITY_TIERS, FANART_QUALITY_TIERS,
)
from settings_context import SettingsContext, run_async
from settings_dialog import SettingsDialog, _inject_globals

# ══════════════════════════════════════════════════════════════════════════════
# Fake implementations
# ══════════════════════════════════════════════════════════════════════════════

def _fake_find_ffmpeg(custom_dir=""):
    return ("/fake/ffmpeg", "/fake/ffprobe")

def _fake_test_ffmpeg(ff, fp):
    return True, True, "OK", "OK"

def _fake_find_notepadpp():
    return None

def _fake_save_settings(s):
    pass  # no-op

def _fake_refresh_ffmpeg():
    pass  # no-op

def _fake_detect_browsers():
    return [("Fake Browser", "/fake/browser.exe")]

def _fake_open_url(url):
    pass

def _fake_clean_backup(active_folder=None):
    pass

# ── Build fake settings ───────────────────────────────────────────────────────
def _make_fake_settings():
    s = dict(DEFAULT_SETTINGS)
    s["text_editor"]   = ""
    s["ffmpeg_path"]   = ""
    s["lang_ok_code"]  = "PT"
    s["genre_list"]    = "Action\nComedy\nDrama"
    s["tag_pairs"]     = None
    return s

# ══════════════════════════════════════════════════════════════════════════════
# Test runner
# ══════════════════════════════════════════════════════════════════════════════

_PASS = []
_FAIL = []

def _check(name, condition, detail=""):
    if condition:
        _PASS.append(name)
        print(f"  [PASS] {name}")
    else:
        _FAIL.append(name)
        print(f"  [FAIL] {name}" + (f": {detail}" if detail else ""))


def run_all():
    root = tk.Tk()
    root.withdraw()

    fake_settings = _make_fake_settings()

    # ── Test 1: SettingsContext instantiation ─────────────────────────────────
    try:
        ctx = SettingsContext(
            app_name             = "TestApp",
            settings             = fake_settings,
            defaults             = dict(DEFAULT_SETTINGS),
            tag_pairs            = list(DEFAULT_TAG_PAIRS),
            world_languages      = list(WORLD_LANGUAGES),
            logger               = logger,
            ffmpeg_finder        = _fake_find_ffmpeg,
            notepadpp_finder     = _fake_find_notepadpp,
            ffmpeg_tester        = _fake_test_ffmpeg,
            save_settings        = _fake_save_settings,
            refresh_ffmpeg       = _fake_refresh_ffmpeg,
            detect_browsers      = _fake_detect_browsers,
            open_url             = _fake_open_url,
            poster_quality_tiers = list(POSTER_QUALITY_TIERS),
            fanart_quality_tiers = list(FANART_QUALITY_TIERS),
            clean_backup         = _fake_clean_backup,
            backup_root          = "/fake/backup",
        )
        _check("T01 SettingsContext instantiation", True)
    except Exception as e:
        _check("T01 SettingsContext instantiation", False, str(e))
        root.destroy()
        return

    # ── Test 2: _inject_globals shim ─────────────────────────────────────────
    try:
        _inject_globals(
            app_name           = "TestApp",
            settings           = fake_settings,
            default_settings   = dict(DEFAULT_SETTINGS),
            default_tag_pairs  = list(DEFAULT_TAG_PAIRS),
            world_languages    = list(WORLD_LANGUAGES),
            logger             = logger,
            fn_find_ffmpeg     = _fake_find_ffmpeg,
            fn_find_notepadpp  = _fake_find_notepadpp,
            fn_test_ffmpeg     = _fake_test_ffmpeg,
            fn_save_settings   = _fake_save_settings,
            fn_refresh_ffmpeg  = _fake_refresh_ffmpeg,
            fn_detect_browsers = _fake_detect_browsers,
            fn_open_url        = _fake_open_url,
            poster_quality_tiers = list(POSTER_QUALITY_TIERS),
            fanart_quality_tiers = list(FANART_QUALITY_TIERS),
            fn_clean_backup    = _fake_clean_backup,
            backup_root        = "/fake/backup",
        )
        _check("T02 _inject_globals shim (no exception)", True)
    except Exception as e:
        _check("T02 _inject_globals shim (no exception)", False, str(e))

    # ── Test 3: Dialog opens without exception ────────────────────────────────
    dlg = None
    try:
        dlg = SettingsDialog(root, tab=0, ctx=ctx)
        _check("T03 SettingsDialog opens", True)
    except Exception as e:
        _check("T03 SettingsDialog opens", False, str(e))
        root.destroy()
        return

    # Process pending events so all tabs build fully
    root.update()

    # ── Test 4: All 12 tabs exist ─────────────────────────────────────────────  ### MODIFIED_BY_CLAUDE_v18.2 ###
    try:
        tab_count = len(dlg._nb.tabs())
        _check("T04 All 12 tabs built", tab_count == 12,                         ### MODIFIED_BY_CLAUDE_v18.2 ###
               f"got {tab_count}")
    except Exception as e:
        _check("T04 All 10 tabs built", False, str(e))

    # ── Test 5: Snapshot is structured ───────────────────────────────────────
    try:
        snap = dlg._rescan_snapshot
        has_image_sizes = isinstance(snap.get("image_sizes"), dict)
        has_language    = isinstance(snap.get("language"), str)
        has_genres      = isinstance(snap.get("genres"), list)
        has_tag_pairs   = isinstance(snap.get("tag_pairs"), list)
        ok = has_image_sizes and has_language and has_genres and has_tag_pairs
        _check("T05 Snapshot is structured (4 typed sub-keys)", ok,
               f"image_sizes={has_image_sizes} language={has_language} "
               f"genres={has_genres} tag_pairs={has_tag_pairs}")
    except Exception as e:
        _check("T05 Snapshot is structured", False, str(e))

    # ── Test 6: _rescan_changed returns False with no changes ─────────────────
    try:
        changed = dlg._rescan_changed()
        _check("T06 No changes → changed['any'] is False",
               changed["any"] is False,
               f"got {changed}")
    except Exception as e:
        _check("T06 No changes → changed['any'] is False", False, str(e))

    # ── Test 7: Language change triggers rescan ───────────────────────────────
    try:
        original_lang = dlg._lang_var.get()
        new_lang = "DE" if original_lang != "DE" else "FR"
        dlg._lang_var.set(new_lang)
        changed = dlg._rescan_changed()
        dlg._lang_var.set(original_lang)   # restore
        _check("T07 Language change → changed['language'] is True",
               changed["language"] is True and changed["any"] is True,
               f"got {changed}")
    except Exception as e:
        _check("T07 Language change → changed['language'] is True", False, str(e))

    # ── Test 8: Browser-only change does NOT trigger rescan ──────────────────
    try:
        original_browser = dlg._browser_var.get()
        dlg._browser_var.set("/some/new/browser.exe")
        changed = dlg._rescan_changed()
        dlg._browser_var.set(original_browser)
        _check("T08 Browser change → changed['any'] is False",
               changed["any"] is False,
               f"got {changed}")
    except Exception as e:
        _check("T08 Browser change → changed['any'] is False", False, str(e))

    # ── Test 9: run_async delivers callback on main thread ────────────────────
    _async_result = []
    _async_done   = threading.Event()

    def _fake_work():
        time.sleep(0.05)
        return 42

    def _fake_callback(val):
        _async_result.append(val)
        _async_done.set()

    try:
        run_async(_fake_work, callback=_fake_callback, root=root)
        # v0.19.0: worker threads may only call root.after() while the main
        # thread is inside mainloop() (tkinter raises "main thread is not in
        # main loop" otherwise), so pump a real mainloop for up to 2 s.
        def _poll():
            if _async_done.is_set() or time.time() > _deadline:
                root.quit()
            else:
                root.after(10, _poll)
        _deadline = time.time() + 2.0
        root.after(10, _poll)
        root.mainloop()
        _check("T09 run_async delivers callback with correct value",
               _async_result == [42],
               f"got {_async_result}")
    except Exception as e:
        _check("T09 run_async delivers callback", False, str(e))

    # ── Test 10: run_async raises ValueError without root ────────────────────
    try:
        raised = False
        try:
            run_async(lambda: None, callback=lambda x: x, root=None)
        except ValueError:
            raised = True
        _check("T10 run_async(callback=…, root=None) raises ValueError", raised)
    except Exception as e:
        _check("T10 run_async ValueError guard", False, str(e))

    # ── Test 11: Simulated Save — no exception, settings written ─────────────
    try:
        save_ok = True
        try:
            dlg._lang_var.set("DE")
            dlg._save_close()
            root.update()
        except Exception as ex:
            save_ok = False
            traceback.print_exc()
        lang_written = (fake_settings.get("lang_ok_code") == "DE")
        _check("T11 Simulated Save — no exception, lang written to settings",
               save_ok and lang_written,
               f"save_ok={save_ok} lang_in_settings={fake_settings.get('lang_ok_code')}")
    except Exception as e:
        _check("T11 Simulated Save", False, str(e))

    # ── Test 12: Dialog is destroyed after Save ───────────────────────────────
    try:
        still_alive = False
        try:
            dlg.winfo_exists()
            still_alive = dlg.winfo_exists()
        except tk.TclError:
            still_alive = False
        _check("T12 Dialog destroyed after Save", not still_alive)
    except Exception as e:
        _check("T12 Dialog destroyed", False, str(e))

    # ── v0.19.1 I9: T13–T15 ──────────────────────────────────────────────────  ### NEW v0.19.1 I9 ###
    # health_rules is a nested dict: give the fake settings their own copy so a
    # save never writes into DEFAULT_SETTINGS.
    fake_settings["health_rules"] = dict(DEFAULT_SETTINGS["health_rules"])

    def _in_loop(fn, seconds=0.6):
        """Run fn inside a real mainloop and keep the loop running briefly, so
        the run_async workers the dialog starts (browser detection …) can
        deliver their callbacks instead of raising "main thread is not in
        main loop"."""
        box = {}
        end = time.time() + seconds
        def _tick():
            if time.time() > end: root.quit()
            else: root.after(20, _tick)
        def _start():
            try: box["r"] = fn()
            except Exception: box["e"] = traceback.format_exc()
            root.after(20, _tick)
        root.after(0, _start); root.mainloop()
        if "e" in box: raise RuntimeError(box["e"])
        return box.get("r")

    # ── Test 13: Image Sizes ↔ Health Rules quality combos are one setting ───
    dlg13 = None
    try:
        dlg13 = _in_loop(lambda: SettingsDialog(root, tab=5, ctx=ctx))
        hr = dlg13._hr_str_vars
        dlg13._fanart_ql_var.set("720p")
        a = hr["fanart_quality_level_minimum"].get() == "720p"
        hr["fanart_quality_level_minimum"].set("540p")
        b = dlg13._fanart_ql_var.get() == "540p"
        hr["poster_folder_quality_level"].set("720p")
        c = dlg13._poster_ql_var.get() == "720p" and dlg13._folder_ql_var.get() == "720p"
        dlg13._poster_ql_var.set("1080p")
        d = hr["poster_folder_quality_level"].get() == "1080p" and dlg13._folder_ql_var.get() == "1080p"
        _check("T13 Image Sizes ↔ Health Rules quality combos mirror both ways",
               a and b and c and d, f"fanart→hr={a} hr→fanart={b} hr→poster+folder={c} poster→hr+folder={d}")
    except Exception as e:
        _check("T13 quality mirror", False, traceback.format_exc())
    finally:
        try:
            if dlg13 is not None and dlg13.winfo_exists():
                dlg13.destroy()
        except tk.TclError:
            pass

    # ── Test 14: the v0.19.0 / v0.19.1 health-rule rows exist and save ───────
    _NEW_RULES = ("image_file_too_small", "image_format_mismatch",          # v0.19.0
                  "genre_only_in_xml", "genre_only_in_nfo", "genre_nfo_wrong_tags",   # v0.19.1
                  "folder_optional_with_kodi_poster", "nfo_name_not_kodi",            # v0.19.1 B23
                  "nfo_unescaped_amp",                                                # v0.19.2 B33
                  "multiple_nfo_files", "poster_missing_with_folder",                 # v0.19.2 F5
                  "id_format_invalid", "year_out_of_range", "numeric_field_invalid",  # v0.19.3 I8
                  "duplicate_single_tag", "empty_required_tag", "unexpected_root")
    try:
        dlg14 = _in_loop(lambda: SettingsDialog(root, tab=10, ctx=ctx))
        missing = [k for k in _NEW_RULES if k not in dlg14._hr_vars]
        for k in _NEW_RULES:
            if k in dlg14._hr_vars:
                dlg14._hr_vars[k].set(False)
        dlg14._save_close()
        root.update()
        saved = {k: fake_settings["health_rules"].get(k) for k in _NEW_RULES}
        _check("T14 v0.19 health-rule rows exist and their OFF state is saved",
               not missing and all(v is False for v in saved.values()),
               f"missing={missing} saved={saved}")
    except Exception as e:
        _check("T14 v0.19 health-rule rows", False, traceback.format_exc())

    # ── Test 16: B24 severity combos exist, save, and a change is a rule change ── ### NEW v0.19.1 B24 ###
    try:
        dlg16 = _in_loop(lambda: SettingsDialog(root, tab=10, ctx=ctx))
        hv = dlg16._hr_str_vars
        present = all(k in hv for k in ("single_source_level", "no_source_level"))
        defaults_ok = present and hv["single_source_level"].get() == "error" and hv["no_source_level"].get() == "error"
        hv["single_source_level"].set("warning"); hv["no_source_level"].set("off")
        ch = dlg16._rescan_changed()
        dlg16._save_close(); root.update()
        saved = (fake_settings["health_rules"].get("single_source_level"), fake_settings["health_rules"].get("no_source_level"))
        _check("T16 single-source / no-source severity combos exist, save and count as a rule change",
               present and defaults_ok and saved == ("warning", "off") and ch.get("health_rules") is True,
               f"present={present} defaults_ok={defaults_ok} saved={saved} changed={ch}")
    except Exception as e:
        _check("T16 severity combos", False, traceback.format_exc())

    # ── Test 25: B60 — Repair All's choice when the local title is unclear ───── ### NEW v0.19.3 B60 ###
    try:
        dlg25 = _in_loop(lambda: SettingsDialog(root, tab=10, ctx=ctx))
        hv25 = dlg25._hr_str_vars
        present25 = "title_sync_default" in hv25 and hv25["title_sync_default"].get() == "nfo"
        hv25["title_sync_default"].set("skip")
        dlg25._save_close(); root.update()
        _check("T25 'When Repair All cannot tell the right local title' exists (default: keep the NFO title) and saves",
               present25 and fake_settings["health_rules"].get("title_sync_default") == "skip",
               f"present={present25} saved={fake_settings['health_rules'].get('title_sync_default')}")
    except Exception as e:
        _check("T25 title_sync_default", False, traceback.format_exc())

    # ── Test 26: B63 — sort_spec / sort_presets survive Save & Apply ─────────── ### NEW v0.19.3 B63 ###
    try:
        fake_settings["sort_spec"] = [{"key": "rating", "dir": "high"}, {"key": "year", "dir": "newest"}]
        fake_settings["sort_presets"] = [{"name": "Mine", "levels": [{"key": "library", "dir": "asc"}]}]
        dlg26 = _in_loop(lambda: SettingsDialog(root, tab=9, ctx=ctx))
        dlg26._save_close(); root.update()
        _check("T26 sort_spec and sort_presets are kept by Save & Apply (no widget, not reset)",
               fake_settings.get("sort_spec") == [{"key": "rating", "dir": "high"}, {"key": "year", "dir": "newest"}]
               and fake_settings.get("sort_presets") == [{"name": "Mine", "levels": [{"key": "library", "dir": "asc"}]}],
               f"{fake_settings.get('sort_spec')} {fake_settings.get('sort_presets')}")
    except Exception as e:
        _check("T26 sort settings", False, traceback.format_exc())

    # ── Test 27: I12 — "Delete the oldest backups automatically" ─────────────── ### NEW v0.19.3 I12 ###
    try:
        dlg27 = _in_loop(lambda: SettingsDialog(root, tab=11, ctx=ctx))
        ok27 = hasattr(dlg27, "_backup_cleanup_var") and dlg27._backup_cleanup_var.get() is True
        dlg27._backup_cleanup_var.set(False)
        dlg27._save_close(); root.update()
        _check("T27 Backup tab: 'Delete the oldest backups automatically' (default ON) exists and saves",
               ok27 and fake_settings.get("backup_cleanup_enabled") is False, f"ok={ok27} saved={fake_settings.get('backup_cleanup_enabled')}")
        fake_settings["backup_cleanup_enabled"] = True
    except Exception as e:
        _check("T27 backup_cleanup_enabled", False, traceback.format_exc())

    # ── Test 15: the window-memory hook is called by the dialog ──────────────
    _hook_calls = []
    def _spy_hook(win, win_id, resizable):
        _hook_calls.append((win, win_id, resizable))
    try:
        SettingsDialog._remember_window_hook = staticmethod(_spy_hook)
        dlg15 = _in_loop(lambda: SettingsDialog(root, tab=0, ctx=ctx))
        _check("T15 window-memory hook called once with (dialog, 'SettingsDialog', True)",
               len(_hook_calls) == 1 and _hook_calls[0][0] is dlg15
               and _hook_calls[0][1:] == ("SettingsDialog", True),
               f"calls={[(c[1], c[2]) for c in _hook_calls]}")
        dlg15.destroy()
    except Exception as e:
        _check("T15 window-memory hook", False, traceback.format_exc())
    finally:
        try:
            del SettingsDialog._remember_window_hook
        except AttributeError:
            pass

    # ── Test 17: fanart.tv key block (v0.19.1 I10) ────────────────────────────   ### NEW v0.19.1 I10 ###
    _opened = []
    try:
        dlg17 = _in_loop(lambda: SettingsDialog(root, tab=1, ctx=ctx))
        dlg17._open_url_fn = _opened.append
        has_block = all(hasattr(dlg17, a) for a in ("_fanarttv_var", "_fanarttv_client_var", "_fanarttv_entry",
                                                     "_fanarttv_client_entry", "_fanarttv_status", "_fanarttv_link"))
        masked = has_block and dlg17._fanarttv_entry.cget("show") == "•" and dlg17._fanarttv_client_entry.cget("show") == "•"
        link_ok = has_block and "fanart.tv" in dlg17._fanarttv_link.cget("text")
        if has_block:
            dlg17._fanarttv_link.event_generate("<Button-1>"); root.update()
        _check("T17a fanart.tv block exists (masked key + client key) and its link opens the key page",
               has_block and masked and link_ok and _opened == ["https://fanart.tv/get-an-api-key/"],
               f"block={has_block} masked={masked} link={link_ok} opened={_opened}")
        dlg17._fanarttv_var.set("FAKEKEY123"); dlg17._fanarttv_client_var.set("VIPKEY456")
        ch = dlg17._rescan_changed()
        dlg17._save_close(); root.update()
        _check("T17b a key-only change → changed['any'] is False",
               ch["any"] is False, f"got {ch}")
        _check("T17c Save & Apply writes both fanart.tv keys",
               fake_settings.get("fanarttv_api_key") == "FAKEKEY123" and fake_settings.get("fanarttv_client_key") == "VIPKEY456",
               f"api={fake_settings.get('fanarttv_api_key')!r} client={fake_settings.get('fanarttv_client_key')!r}")
    except Exception as e:
        _check("T17 fanart.tv key block", False, traceback.format_exc())

    # ── Test 18: FFmpeg limits for "Frames from movie" (v0.19.2 B28) ─────────   ### NEW v0.19.2 B28 ###
    try:
        import json as _json18
        _schema18 = _json18.load(open(next(q for q in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings_schema.json"),
                                        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings_schema.json"))
                                  if os.path.isfile(q)),
                                      encoding="utf-8"))["properties"]
        _check("T18a new keys in DEFAULT_SETTINGS and the schema (20 s / 180 s)",
               DEFAULT_SETTINGS.get("ffmpeg_frame_timeout_sec") == 20 and DEFAULT_SETTINGS.get("ffmpeg_run_budget_sec") == 180
               and _schema18["ffmpeg_frame_timeout_sec"]["default"] == 20 and _schema18["ffmpeg_run_budget_sec"]["default"] == 180,
               f"defaults={DEFAULT_SETTINGS.get('ffmpeg_frame_timeout_sec')}/{DEFAULT_SETTINGS.get('ffmpeg_run_budget_sec')}")
        dlg18 = _in_loop(lambda: SettingsDialog(root, tab=0, ctx=ctx))
        has18 = hasattr(dlg18, "_ffmpeg_frame_timeout_var") and hasattr(dlg18, "_ffmpeg_run_budget_var")
        if has18:
            dlg18._ffmpeg_frame_timeout_var.set(45); dlg18._ffmpeg_run_budget_var.set(5000)
        ch18 = dlg18._rescan_changed()
        dlg18._save_close(); root.update()
        _check("T18b Tools tab spinboxes save the limits (clamped: 5000 → 1800); no rescan offered",
               has18 and fake_settings.get("ffmpeg_frame_timeout_sec") == 45 and fake_settings.get("ffmpeg_run_budget_sec") == 1800
               and ch18["any"] is False,
               f"has={has18} saved={fake_settings.get('ffmpeg_frame_timeout_sec')}/{fake_settings.get('ffmpeg_run_budget_sec')} ch={ch18}")
    except Exception as e:
        _check("T18 FFmpeg limits", False, traceback.format_exc())

    # ── Test 19: Esc / Cancel / [X] ask before discarding changes (v0.19.2 B44) ── ### NEW v0.19.2 B44 ###
    import settings_dialog as _sdmod
    _asked = []
    _answer = {"v": False}
    _orig_ask = _sdmod.messagebox.askyesno
    _sdmod.messagebox.askyesno = lambda *a, **k: (_asked.append(a[0] if a else k.get("title")) or _answer["v"])
    try:
        dlg19 = _in_loop(lambda: SettingsDialog(root, tab=1, ctx=ctx)); root.update()
        esc_bound = "_cancel_close" in dlg19.bind("<Escape>") or bool(dlg19.bind("<Escape>"))
        dlg19._cancel_close(); root.update()          # what Esc runs (synthetic key events need the focus)
        _check("T19a nothing changed → Esc (bound) closes without a question",
               esc_bound and not dlg19.winfo_exists() and not _asked, f"bound={esc_bound} exists={dlg19.winfo_exists()} asked={_asked}")
        before = dict(fake_settings)
        dlg19b = _in_loop(lambda: SettingsDialog(root, tab=1, ctx=ctx)); root.update()
        dlg19b._tmdb_var.set("CHANGED-B44")
        _answer["v"] = False; dlg19b._cancel_close(); root.update()
        stay = dlg19b.winfo_exists()
        _answer["v"] = True; dlg19b.tk.call(dlg19b.protocol("WM_DELETE_WINDOW")); root.update()
        _check("T19b a change → Cancel asks 'Discard your changes?'; No keeps the dialog, Yes ([X]) closes; nothing saved",
               stay and not dlg19b.winfo_exists() and _asked == ["Discard your changes?", "Discard your changes?"]
               and fake_settings.get("tmdb_api_key") == before.get("tmdb_api_key"),
               f"stay={stay} asked={_asked} tmdb={fake_settings.get('tmdb_api_key')!r}")
    except Exception as e:
        _check("T19 discard question", False, traceback.format_exc())
    finally:
        _sdmod.messagebox.askyesno = _orig_ask

    # ── Test 20: right-click "Repeat" setting (v0.19.2 B57) ───────────────────  ### NEW v0.19.2 B57 ###
    try:
        dlg20 = _in_loop(lambda: SettingsDialog(root, tab=9, ctx=ctx)); root.update()
        has20 = hasattr(dlg20, "_ctx_repeat_var") and dlg20._ctx_repeat_var.get() is True
        dlg20._ctx_repeat_var.set(False)
        ch20 = dlg20._rescan_changed()
        dlg20._save_close(); root.update()
        _check("T20 'Repeat: <last action>' checkbox (User Interface, default ON) saves OFF; key in defaults; no rescan",
               has20 and DEFAULT_SETTINGS.get("ctx_repeat_last") is True and fake_settings.get("ctx_repeat_last") is False and ch20["any"] is False,
               f"has={has20} saved={fake_settings.get('ctx_repeat_last')!r} ch={ch20}")
    except Exception as e:
        _check("T20 ctx_repeat_last", False, traceback.format_exc())

    # ── Test 22: "Show the Ignored folders window after a scan" (v0.19.2 B53) ─  ### NEW v0.19.2 B53 ###
    try:
        dlg22 = _in_loop(lambda: SettingsDialog(root, tab=9, ctx=ctx)); root.update()
        has22 = hasattr(dlg22, "_scan_ignored_report_var") and dlg22._scan_ignored_report_var.get() is True
        dlg22._scan_ignored_report_var.set(False)
        ch22 = dlg22._rescan_changed()
        dlg22._save_close(); root.update()
        _check("T22 'Ignored folders window after a scan' checkbox (User Interface, default ON) saves OFF; no rescan",
               has22 and DEFAULT_SETTINGS.get("scan_ignored_report") is True and fake_settings.get("scan_ignored_report") is False
               and ch22["any"] is False, f"has={has22} saved={fake_settings.get('scan_ignored_report')!r} ch={ch22}")
    except Exception as e:
        _check("T22 scan_ignored_report", False, traceback.format_exc())

    # ── Test 23: "Dark title bars" (v0.19.2 B51) ─────────────────────────────  ### NEW v0.19.2 B51 ###
    try:
        dlg23 = _in_loop(lambda: SettingsDialog(root, tab=9, ctx=ctx)); root.update()
        has23 = hasattr(dlg23, "_dark_title_var") and dlg23._dark_title_var.get() is True
        dlg23._dark_title_var.set(False)
        ch23 = dlg23._rescan_changed()
        dlg23._save_close(); root.update()
        _check("T23 'Dark title bars' checkbox (User Interface, default ON) saves OFF; no rescan",
               has23 and DEFAULT_SETTINGS.get("dark_title_bar") is True and fake_settings.get("dark_title_bar") is False
               and ch23["any"] is False, f"has={has23} saved={fake_settings.get('dark_title_bar')!r} ch={ch23}")
    except Exception as e:
        _check("T23 dark_title_bar", False, traceback.format_exc())

    # ── Test 24: "Check for updates at start" (v0.19.2 B50) ──────────────────  ### NEW v0.19.2 B50 ###
    try:
        dlg24 = _in_loop(lambda: SettingsDialog(root, tab=9, ctx=ctx)); root.update()
        has24 = hasattr(dlg24, "_check_updates_var") and dlg24._check_updates_var.get() is False
        dlg24._check_updates_var.set(True)
        ch24 = dlg24._rescan_changed()
        dlg24._save_close(); root.update()
        _check("T24 'Check for updates at start' checkbox (User Interface, default OFF) saves ON; no rescan",
               has24 and DEFAULT_SETTINGS.get("check_updates") is False and fake_settings.get("check_updates") is True
               and ch24["any"] is False, f"has={has24} saved={fake_settings.get('check_updates')!r} ch={ch24}")
    except Exception as e:
        _check("T24 check_updates", False, traceback.format_exc())

    # ── Test 21: Settings → Tools shows where FFmpeg was found (v0.19.2 B58) ──  ### NEW v0.19.2 B58 ###
    try:
        dlg21 = _in_loop(lambda: SettingsDialog(root, tab=0, ctx=ctx)); root.update()
        t21 = dlg21._ff_how_lbl.cget("text") if hasattr(dlg21, "_ff_how_lbl") else ""
        _check("T21 Tools tab shows 'FFmpeg: …' (where / how found) and has 'Search again'",
               t21.startswith("FFmpeg:") and hasattr(dlg21, "_ffmpeg_search_again"), f"label={t21!r}")
        dlg21.destroy()
    except Exception as e:
        _check("T21 FFmpeg found label", False, traceback.format_exc())

    # ── Teardown ──────────────────────────────────────────────────────────────
    try:
        root.destroy()
    except Exception:
        pass

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    total = len(_PASS) + len(_FAIL)
    print(f"Results: {len(_PASS)}/{total} passed")
    if _FAIL:
        print(f"Failed:  {', '.join(_FAIL)}")
    else:
        print("All tests passed.")
    print("=" * 60)
    return len(_FAIL) == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
