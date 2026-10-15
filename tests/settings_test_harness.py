# =============================================================================
# settings_test_harness.py
# Metadata & MediaClinic — Settings Subsystem Test Harness
# Version: 0.19.1  (12 tabs; T09 pumps a real mainloop; T13–T15 added in v0.19.1 I9, T16 in B24)
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
                  "folder_optional_with_kodi_poster", "nfo_name_not_kodi")            # v0.19.1 B23
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
