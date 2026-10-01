# CLAUDE_RULES.md
## MediaClinic — Rules for AI-assisted Editing of the Settings Subsystem
### Version: 0.14.0

This file is the authoritative guide for any Claude (or human) editing
`settings_model.py`, `settings_controller.py`, `settings_context.py`, or
`settings_dialog.py`.  Read it in full before making any change.

---

## 1. Module Responsibilities (Do Not Cross These Boundaries)

| Module | Allowed | Forbidden |
|---|---|---|
| `settings_model.py` | Pure data: constants, defaults, tier tables, pure functions | Any I/O, tkinter, subprocess, os, logging |
| `settings_controller.py` | Filesystem, subprocess, JSON, shutil | tkinter, any UI import |
| `settings_context.py` | Dataclass definition, `run_async` helper | Business logic, UI code |
| `settings_dialog.py` | tkinter UI only | Direct filesystem access outside `run_async` calls |

---

## 2. The Save Chain — Never Break This

The save chain in `_save_close()` must always execute in this exact order:

1. Gather all widget values into `ctx.settings`
2. Call `ctx.refresh_ffmpeg()`
3. Call `ctx.save_settings(ctx.settings)`
4. Log "Settings saved"
5. Call `self.destroy()`  ← dialog must close BEFORE anything else
6. Schedule `parent._on_settings_changed()` via `parent.after(0, …)`
7. If `changed["any"]`: schedule `self._offer_rescan(parent)` via `parent.after(0, …)`

**Never** use `wait_window()`, `time.sleep()`, or any blocking call here.
**Never** reorder steps 5–7.

---

## 3. The Tab Registry — Never Remove or Rename Tabs

```python
_TAB_REGISTRY = [
    (0,  "Tools",           "_build_tools_tab"),
    (1,  "API Keys",        "_build_api_keys_tab"),
    (2,  "Browser",         "_build_browser_tab"),
    (3,  "Language",        "_build_language_tab"),
    (4,  "Improvements",    "_build_improvements_tab"),
    (5,  "Image Sizes",     "_build_image_sizes_tab"),
    (6,  "Genres",          "_build_genres_tab"),
    (7,  "NFO / XML",       "_build_tags_tab"),
    (8,  "User Interface",  "_build_ui_prefs_tab"),
    (9,  "Backup",          "_build_backup_tab"),
]
```

To add a tab: append to the list with the next index.  Never change existing indices.

---

## 4. Widget Variable Names — Never Rename

The following `self._*_var` names are read by `_save_close()` and `_rescan_changed()`.
Renaming any of them silently breaks the save pipeline:

`_editor_var`, `_ffmpeg_var`, `_scraper_var`, `_tmdb_var`, `_omdb_var`,
`_browser_var`, `_lang_var`, `_ic_vars`, `_max_nfo_kb_var`, `_max_xml_kb_var`,
`_min_backdrops_var`, `_min_poster_kb_var`, `_min_folder_kb_var`, `_min_fanart_kb_var`,
`_backdrop_count_var`, `_meta_src_var`, `_poster_ql_var`, `_folder_ql_var`,
`_fanart_ql_var`, `_fanart_168_var`, `_poster_34_var`, `_show_header_tips_var`,
`_alt_rows_var`, `_show_image_size_var`, `_compact_mode_var`, `_dark_theme_var`,
`_auto_fit_var`, `_max_backup_mb_var`, `_genres_text`, `_tags_text`

---

## 5. JSON Structure — Never Change Key Names

The key names in `settings.json` are defined in `settings_model.DEFAULT_SETTINGS`
and validated by `settings_schema.json`.  Do not rename, remove, or change the
type of any existing key.  To add a new setting:

1. Add the key with its default to `settings_model.DEFAULT_SETTINGS`
2. Add it to `settings_schema.json`
3. Read it in the relevant tab builder
4. Write it back in `_save_close()`

---

## 6. Blocking Operations — Always Use `run_async`

These operations **must** always be called via `run_async(fn, callback, root)`:

- `ctx.ffmpeg_finder(path)` — calls subprocess
- `ctx.ffmpeg_tester(ff, fp)` — calls subprocess
- `ctx.detect_browsers()` — filesystem stat scan
- `ctx.clean_backup(folder)` — filesystem walk
- Any `urllib.request` / network call

`run_async` is imported from `settings_context.py`.  Never use
`threading.Thread(...)` directly in `settings_dialog.py` for new code.

---

## 7. Snapshot Rules — Never Add Browser to the Snapshot

`_take_rescan_snapshot()` captures the settings that affect scan results.
`default_browser` must **never** appear in the snapshot — changing only
the browser must never trigger a rescan offer.

The snapshot structure must remain:
```python
{
    "image_sizes": { ... },   # dict of quality/proportion settings
    "language":    "PT",      # scalar ISO code
    "genres":      [...],     # list of stripped strings
    "tag_pairs":   [...],     # list of 4-tuples
}
```

Comparison is `snapshot != new_snapshot` — pure dict equality, no strings.

---

## 8. `_inject_globals` — Keep as Shim

`_inject_globals()` must stay as a compatibility shim.  Its signature must
not change.  It must continue to populate all the module-level `_*` globals
AND build a `SettingsContext` stored as `_ctx`.

The call site in `mediaclinic.py` (the `_sd_inject(...)` call) must not change.

---

## 9. `_offer_rescan` — Never Make Blocking

`_offer_rescan()` creates a `tk.Toplevel` with three buttons.
It must never use `wait_window()`.  It must never block.
The dialog is destroyed by the button callbacks, not by the caller.

---

## 10. Safety Checklist (run before every commit)

- [ ] No infinite loops
- [ ] No UI freezes (no blocking on main thread)
- [ ] No `wait_window()` or `time.sleep()` anywhere in settings subsystem
- [ ] No broken callbacks
- [ ] Snapshot logic: browser change does NOT set `changed["any"] = True`
- [ ] Browser highlight: `_update_browser_highlight` still fires on `_browser_var` write
- [ ] Save chain: `destroy()` comes before `after(0, …)` callbacks
- [ ] No renamed widget variables
- [ ] No changed JSON key names
- [ ] `_inject_globals` signature unchanged
- [ ] `settings_test_harness.py` runs without exception
