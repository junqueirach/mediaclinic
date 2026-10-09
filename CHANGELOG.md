# Changelog

All notable changes to MediaClinic. Dates are release dates. Earlier versions are kept as complete files in `archive/versions/`; their notes are in the `CHANGELOG` block at the top of `mediaclinic.py` and in *Help → Version History* inside the app.

## v0.18.3 — 2026-10-09

First release with a ready-to-run Windows build (`MediaClinic-0.18.3-win64.zip`). Export, faster scans, many corrected health messages, and about 1,900 lines of duplicated or dead code removed.

### Added
- **Export Movie List…** (Tools menu, the **Export…** button, `Ctrl+Shift+E`): column presets Basic, Standard and All or a custom selection; all movies or only the current filtered and sorted view; CSV (comma, default), CSV (semicolon, for Excel in Swiss, German, Portuguese and French locales), tab-separated, plain `Name (Year)` list, or an Excel `.xlsx` workbook (needs `openpyxl`). New module `export_list.py`.
- Scan results now live in `last_results.json` next to `settings.json` instead of inside it, so the settings file shrinks from megabytes to kilobytes and a scan no longer rewrites it every few rows.
- Each NFO, XML and image header is read once per movie during a scan, which makes the metadata phase noticeably faster.
- Health rules **IMDB ID present in one file only** and **TMDB ID present in one file only**.
- Compact mode now reduces the row height; `Esc` cancels a running scan.
- Help text rewritten to match the real shortcuts and menus.
- Windows build: when frozen, `logs/` and `backup/` are created next to `MediaClinic.exe`.

### Fixed
- *Tools → Run Improvements Check — All Movies* failed with "name `_run_improvements_check` is not defined".
- The Settings menu opened the wrong tab (Ratings opened Health Rules, Genres opened Ratings, …); a Health Rules entry was added.
- Quick Scan never detected modified movies, and computed health before the FFprobe data was restored.
- *Update Scan (no/with FFprobe)* after a settings save both followed the FFprobe checkbox instead of the button pressed.
- Full Scan without FFprobe dropped the Audio column.
- Source, Rating and Votes health messages were swapped: "conflict" was shown for an empty tag while real conflicts were silent.
- Title mismatch compared all four title tags; it now compares only the NFO `<title>` with the XML `<LocalTitle>`.
- The TMDB image download never retried on 429, 5xx or timeout (exception handlers were in the wrong order).
- OMDb key validation accepted invalid keys.
- Scroll-wheel bindings leaked after closing the Search Sources window and the Health Rules tab.
- Column widths are restored even without a saved session; the start-up log line reported the wrong version.

### Changed
- About 1,900 lines removed from the main script: duplicated settings, backup and quality code is now imported from `settings_model.py` and `settings_controller.py`; the Help text moved to `help_text.py` and the genre tables to `genre_data.py`; dead code and series placeholders removed.
- Self-test (`tests/selftest_v0_18_3.py`, 98 checks) now runs in CI under a virtual display with FFmpeg installed.

## v0.18.2

- Configurable Health Rules engine (*Settings → Health Rules*) with error and warning groups, levels and thresholds; in-memory health update after saving.
- Health Status Report (right-click and Tools menu); filter bar above the table (`Ctrl+F`); required audio and subtitle language rules.

## v0.18.0

- Column widths persisted between sessions; Replace All Backdrops (backup, delete, re-download); Open on Fanart.tv; resilient TMDB image downloader with retries; backdrop counting tolerates numbering gaps.

## Earlier

See `archive/versions/` for every version since the first 12 KB folder scanner.
