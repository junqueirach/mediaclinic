# CLAUDE_RULES.md
## MediaClinic — Rules for AI-assisted editing
### Version: 0.19.4 (rewritten 2026-11-04 from the code; the v0.14.0 version covered only the settings subsystem)

This file is the guide for any Claude (or human) changing MediaClinic. Read it in full before any change. In the author's working
folder it adds to the family rules (`CLAUDE.md`: real data, snapshots, editing, builds) and never weakens them; the work order there is
the roadmap `IMPROVEMENTS_SHORT_TERM R1.md`. Those two files are not published.

Names below were checked against the v0.19.4 source. In the source the main file is `mediaclinic_v0_19_4.py`; on GitHub it is
`mediaclinic.py`. When a rule and the code disagree, stop and report it. Do not silently follow either.

---

## 1. Modules: do not cross these boundaries

| Module | What it holds | Forbidden |
|---|---|---|
| `mediaclinic_*.py` | The application: scanning, health rules, the window, dialogs, workers | Pure rules that can live in a module below |
| `settings_model.py` | Constants, defaults, tier tables, pure functions | Any I/O, tkinter, subprocess, logging |
| `settings_controller.py` | Settings and cache files, backups and Undo, FFmpeg and browser discovery | tkinter, any UI import |
| `settings_context.py` | `SettingsContext`, `run_async` | Business logic, UI code |
| `settings_dialog.py` | Settings window, `DialogBase`, `modal`, shared dialog parts | File access outside `run_async` |
| `collection_rules.py` | Movie collections | I/O, network, tkinter: pure functions only |
| `sort_engine.py` | The multi-level sort, presets | UI |
| `naming_catalog.py` | Every file name the media servers read | I/O beyond names given to it, UI |
| `folder_classifier.py` | What a folder is (movie, series, container…) | UI |
| `image_fix.py` | Image proportion and size calculations | UI |
| `export_list.py` | Movie list export | UI |
| `genre_data.py`, `help_text.py` | Data only | Logic that changes app state |

Test-only, never bundled: `selftest_*.py`, `settings_test_harness.py`, `test_mediaclinic.py`, `settings_schema.json`, `tools\`, `plan_assets\`.

**A new module** must be added to the hidden imports in `Compile Exe.txt`. **A new data file** must be added to its `--add-data` list.

---

## 2. Threads: the rules that prevent freezes

Each rule here comes from a real freeze or crash.

1. **Only the Tk thread touches Tk.** A worker reaches the window only with `ui_post(fn, *args)`, and passes plain data.
2. **Never call `after()` from a worker.** `ui_post` puts the call on `_UI_QUEUE`; `App._drain_ui` hands each item to Tk as its own event every 25 ms.
3. **The queue must not run items itself inside its timer.** An item that opens a window and waits would stop the queue, and the call that closes
   that window would never run (the v0.19.4 "Update with FFprobe" hang). Keep `self.after(0, _ui_call, fn, args)`.
4. **The Tk thread must not wait for a worker that may need the Tk thread.** `Thread.start()` is such a wait: it blocks until the new thread runs.
   No Tcl call may happen on a thread before it has started.
5. **A Tk object's clean-up belongs on the Tk thread.** The garbage collector can run `__del__` on any thread. `_tk_del_on_ui_thread` sends it through the
   queue for `tk.Variable`, `tk.Image` and Pillow's `PhotoImage` / `BitmapImage`. Any new class with a `__del__` that calls Tcl needs the same wrapper.
   `_UI_QUEUE` stays a `SimpleQueue`: only its `put()` is safe inside a destructor.
6. **Use `threading.get_ident()`, not `current_thread()`,** in code that can run while a thread is starting.
7. **A long action that changes rows is an `_AppJobThread`,** so `_bg_wait_note` makes a scan wait for it. Batch tools use `_BatchJob`.
8. **Every action that reads or writes results checks `_busy()` first.**
9. **On close, cancel timers in Tcl** (`self.tk.call("after", "cancel", id)`), never with `after_cancel`.
10. **No `time.sleep()` and no blocking call on the Tk thread.** Blocking settings work goes through `run_async`.

---

## 3. Writing the user's files

1. **Backup first, always.** Every NFO, XML or image write is backed up before it happens. A failed backup stops the write.
2. **Write atomically:** `_atomic_write_text` for text; check an image (Pillow) before it replaces a file.
3. **Keep line endings and encoding** of an NFO or XML as found.
4. **Tell Undo what happened:** `note_created` for new files and folders, `note_renamed` for renames. `restore_backup_run` must be able to put everything back.
5. **Never overwrite:** an image Kodi does not read, or an image in a collection folder the user did not ask to replace.
6. **After a write, refresh the rows:** `_schedule_refresh(paths, need_ffprobe=False)`. `need_ffprobe=True` only if a video, audio or embedded subtitle changed.
7. **The user must see the result at once:** a row changes through `_row_replaced`, so the table row, its collection row and the panel all follow.
   Test what the app SHOWS after an action, not only the file on disk.
8. **Messages:** counts through `_n()` ("1 movie"); batch results end with `UNDO_HINT`.
9. **A fix and its rule must agree:** after a Fix, the warning is gone, and Fix again finds nothing. Test that whole loop.

---

## 4. Rows and scans

1. **Every row starts from `row_defaults()`.** `scan_one_subfolder` is the wrapper; the rest of the scan is in `_scan_one_subfolder`. A new row key goes into `row_defaults()`.
2. **A rescan keeps data through `carry_after_rescan`:** FFprobe data only for the same video, the ID check only while the IDs are unchanged.
3. **Health is computed by the rule functions in `HEALTH_RULES`,** never stored as truth. Cached reasons are not trusted (`finalize_results`).
4. **A failed or closed scan keeps the previous rows** (`merge_unfinished_rows`).
5. **An edited file is re-read from disk:** `forget_read_caches`, because a network drive can report an edited file with its old time and size.
6. **Window position and size** go through `_remember_window`. On purpose not for short questions and progress windows: they open with the app, so they stay in view when the main window moves to another monitor.

---

## 5. Collections

1. **One name per collection,** from `chosen_names`: English, unless more than half of its titles are in one other language; or the language fixed in `collection_name_lang`.
2. **The NFO `<set>` and `movie.xml` are written together.** The local title is read from the NFO `<title>`, else the XML `<LocalTitle>`.
3. **A renamed collection takes its folder along** (`migrate_collection_folder`), only when no movie uses the old name and every library is loaded.
4. **Pure rules go in `collection_rules.py`.**

---

## 6. Settings subsystem

**The save chain.** `_save_close` must keep this order:
1. Copy the live settings (`copy.deepcopy`). Each value goes into the copy; a bad value raises `SettingsFieldError`, and nothing is applied.
2. Detect changes (`_rescan_changed`).
3. Save, then copy into the live settings, then `refresh_ffmpeg`, then log "Settings saved". A failed save applies nothing and the window stays open.
4. `self.destroy()`: the dialog closes before anything below.
5. `parent_app.after(0, parent_app._on_settings_changed)`.
6. If the rules changed, apply them with `after(0, …)`.
7. If a rescan matters, `after(0, …)` the `_offer_rescan` window.

Never use `wait_window()` or `time.sleep()` here, and never reorder steps 4–7. `_offer_rescan` never blocks.

**Tabs.** `_TAB_REGISTRY` indices never change, and builder method names never change. To add a tab, append it with the next index. A label changes only with the user's approval.

**Blocking work** uses `run_async`, imported from `settings_context.py`, for subprocess, file walks and network. Known exception: the backup size measure uses its own thread
and polls for the result (no Tk in the worker).

**Rescan snapshot.** `_take_rescan_snapshot` never includes `default_browser`: changing only the browser must not offer a rescan. Comparison is plain equality.

**`_inject_globals`** stays as a compatibility shim. Its signature does not change.

**A new setting:** add it to `DEFAULT_SETTINGS` (`settings_model.py`) and to `settings_schema.json`, read it in the tab builder, and write it back in `_save_close`.

---

## 7. Names you must not change

**`settings.json` keys:** never rename, remove or change the type of an existing key. A key that goes away needs a migration and a test.

**Widget variables** read by `_save_close` and `_rescan_changed`: renaming one silently breaks saving.
`_editor_var`, `_ffmpeg_var`, `_scraper_var`, `_tmdb_var`, `_omdb_var`, `_browser_var`, `_lang_var`, `_ic_vars`, `_max_nfo_kb_var`, `_max_xml_kb_var`,
`_min_poster_kb_var`, `_min_folder_kb_var`, `_min_fanart_kb_var`, `_backdrop_count_var`, `_meta_src_var`, `_poster_ql_var`, `_folder_ql_var`, `_fanart_ql_var`, `_fanart_168_var`, `_poster_34_var`,
`_show_header_tips_var`, `_alt_rows_var`, `_show_image_size_var`, `_compact_mode_var`, `_dark_theme_var`, `_auto_fit_var`, `_max_backup_mb_var`, `_genres_text`, `_tags_text`, `_ffprobe_cache_var`,
`_fanarttv_var`, `_fanarttv_client_var`, `_ffmpeg_frame_timeout_var`, `_ffmpeg_run_budget_var`, `_ctx_repeat_var`, `_scan_ignored_report_var`, `_dark_title_var`, `_backup_cleanup_var`, `_coll_folder_var`,
`_group_coll_var`, `_hr_vars`, `_hr_str_vars`.

**Files in the config folder:** `settings.json`, `last_results.json` (`{schema, kind, rows}`; the old plain list is still read), `last_ignored.json`, `not_duplicates.json`, `collections_cache.json`,
`no_collection.json`.

**Visible labels approved by the user (B108, 2026-10-23); never change them without asking.** The main ones:
- "TMDB" and "IMDb" in every visible text (tag names and ID constants unchanged).
- Settings tabs: "Editor & FFmpeg", "API Keys", "Browser", "Language", "NFO / XML".
- An entry that opens a window ends with "…".
- "Fix Image Proportions / Size…", "Check for Updates…", "Open Logs Folder", "Copy Path", "Copy All Shown".
- Uncounted "(s)" labels keep their wording: "Extract Backdrop(s)", "Add Custom Genre(s) to Settings", "Open Website(s)", "Custom genre(s) found", ".nfo/.xml file(s)", "subtitle language(s)", "selected movie(s)".

---

## 8. Actions, menus and windows

1. **A menu entry or shortcut is an action:** `register_action`, listed in `TOOLS_MENU` or its menu. Do not build a separate path.
2. **Dialogs derive from `DialogBase`.** Esc does what the window's X does; a modal dialog goes through `modal`.
3. **Colours, fonts and sizes:** the colour tokens (`C_BG`, …) and `px()` for pixel sizes, so 125 % and 150 % work.
4. **Message boxes open on their window:** `parent=self`.
5. **A user-visible change** updates the Help (`help_text.py`), the README and the program's header CHANGELOG in the same step.
6. **From v0.20.0 on,** every new visible text also goes into the English, Portuguese (Brazil) and Spanish catalogs (Part 6a of the plan).

---

## 9. Tests

1. **After every change:** the full self-test and `settings_test_harness.py`, with `MEDIACLINIC_CONFIG_DIR` and `MEDIACLINIC_BACKUP_DIR` on temp folders and `PYTHONIOENCODING=utf-8`. Run with `python -u` so a hang shows the last check.
2. **Never edit a `.py` while its suite runs.**
3. **Read a failure before calling it a test problem.** A "hang on CI" in v0.19.4 was a real freeze in the app.
4. **A fixed bug gets a check that fails without the fix.** Prove it, as `q3f_del_freeze.py` did.
5. **Wait for the result, not a fixed time.** Requests go through the queue, so a fixed `sleep` is a race.
6. **Do not use the PC during a self-test:** keyboard and wheel checks need the test window to have focus.
7. **Synthetic clicks may not reach a window from a Claude session.** Drive it in-process; never report a click as tested if it did not arrive.
8. **A check that needs Windows** (Z:\ paths, backslashes, read-only files, the registry, window managers) needs a `sys.platform` guard: CI runs on Linux with Python 3.10 and 3.12.
9. **Python 3.10 stays supported:** no syntax newer than that.

---

## 10. Checklist before a change is done

- [ ] No Tk call from a worker; no new wait of the Tk thread for a worker
- [ ] No `wait_window()` or `time.sleep()` in the settings save path; no blocking on the Tk thread
- [ ] Backup before every write; Undo restores it; the row refreshes and the panel follows
- [ ] The rule's warning is gone after its Fix, and Fix again finds nothing
- [ ] New row keys in `row_defaults()`; new settings keys in `DEFAULT_SETTINGS` and the schema
- [ ] No renamed widget variable, settings key, tab index or approved label
- [ ] A browser change does not offer a rescan
- [ ] Save chain: `destroy()` comes before the `after(0, …)` callbacks
- [ ] New module or data file added to `Compile Exe.txt`
- [ ] Help, README and CHANGELOG updated if behaviour changed
- [ ] Self-test and harness run; every failure read and reported
