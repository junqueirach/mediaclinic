# Changelog

All notable changes to MediaClinic. Dates are release dates. Earlier versions are kept as complete files in `archive/versions/`; their notes are in the `CHANGELOG` block at the top of `mediaclinic.py` and in *Help → Version History* inside the app.

## v0.19.0 — 2026-10-13

Several libraries in one table, online checks of IMDb/TMDb IDs, an Auto Repair tool, and a clearer image status. Published as source only; the next Windows build comes with v0.19.1.

### Added
- **Several library folders**: *Libraries…* dialog, a library filter next to *Browse…* (it also limits Full and Quick Scan), one combined table with an optional *Library* column, duplicate detection across libraries, and a *Library* export field. A library that cannot be reached keeps its cached rows, is skipped by scans and shown as offline. The old single folder setting is migrated.
- **Verify IMDb/TMDb IDs** (*Tools → All Movies*, or right-click one movie or a selection): looks each film up on TMDb and compares title (any TMDb title or translation, accent-insensitive) and year (±1). Results (OK, different films, another film, not found, NFO/XML disagree, no IDs) appear in a sortable report you can save as .txt or .csv; the result is kept on the row and shown in the Source tooltip. Requests are limited to 40 per 10 seconds.
- **Auto Repair** (right-click, or *Tools → All Movies* with a dry-run preview): IDs (exact title and year applied automatically, otherwise a chooser with thumbnails), conflicting and partial IDs, ratings, genre normalisation (custom genres kept), genres and year from a verified TMDb ID, NFO/XML title copy and the XML language tag. Artwork is never touched. A backup is made before the first write, and a per-movie summary (fixed, skipped, still failing) can be saved.
- Health rules `image_file_too_small` and `image_format_mismatch`.
- *Apply this choice to all remaining movies* in the custom-genre dialog and *Skip all remaining* in the Normalize Sources ID dialog.
- Window size and position are remembered for the main window (including maximised), every dialog and Settings, and kept on the visible screen.
- Rows refresh automatically after every change, in the background and once per batch. Metadata and artwork changes refresh without FFprobe.

### Fixed
- Images below the minimum resolution or file size were reported as corrupt. The image status now separates missing, corrupt (cannot be decoded), too small, wrong proportions and wrong format for the extension; the format is detected from the file contents.
- One minimum image quality setting is used everywhere; cached rows are re-evaluated on load.
- Sync Ratings: the zero-votes choice can be applied to all remaining movies in the run, the primary source always wins where it has a valid value, *Type Values + Apply to all* no longer skips the remaining movies, and 0.0 / 0 is never written.
- Every NFO/XML write is atomic (temporary file, then replace), and missing tags are inserted before the real closing tag (a `movie.xml` with a `<Title>` root was damaged by the v0.18.x ID writer).
- *Normalize Genres* and *Delete extrafanart* now refresh the affected rows.

### Changed
- Self-test `tests/selftest_v0_19_0.py` with about 285 checks (was 129), run in CI under a virtual display. The maximised-window check runs on Windows only, because Tk on Linux has no "zoomed" state.
- Background dialogs use one event-based helper instead of polling.

## v0.18.4 — 2026-10-11

Faster scans on large and network libraries, new tools for finding problems in big catalogues, duplicate detection, and fixes for stale or incomplete health information.

### Added
- **Parallel scanning**: folders, metadata and images are read by several workers at once (*Settings → Tools*: `scan_workers`, default 6; `ffprobe_workers`, default 2), and each movie folder is listed only once per scan. This matters most on network shares.
- **Quick Scan** now probes changed movies with FFprobe when the FFprobe box is ticked.
- **Large-catalogue tools**: click the Errors or Warnings counter to filter the table, tick *Problems only*, filter by health reason, hide columns with *Tools → Choose Columns…*, and see *Tools → Library Statistics*.
- **Duplicate detection**: new health rule `duplicate_movie` (same ID, or same title and year, in another folder) and a *Duplicate Movies Report* in the Tools menu.
- **Copy poster.jpg → folder.jpg** where the two differ: right-click, for a selection, or for the whole library from the Tools menu. A backup is made first.
- **Export**: new fields IMDB Link, TMDB Link, Outline and Plot, and a new **Identify** preset (name, year, IMDB link, TMDB link, outline) so the reader of the file can recognise each movie.
- Kodi v17+ `<ratings>` blocks are read as well as the legacy flat rating tags.
- *Tools → Recompute Health Status*.

### Fixed
- *Update (no FFprobe)* did not re-read external subtitle files, so the subtitle and *Lang OK?* columns could stay out of date.
- Health status is recomputed whenever rows are loaded from the cache or a saved results file, so stale "title mismatch" reasons from v0.18.2 no longer appear.
- The Health Status Report dropped the warnings of movies that also had errors; it now lists both.
- Title comparison tolerates Unicode, HTML-entity and quote differences (for example `&amp;` against `&`, or curly against straight quotes).
- The source did not start on Python 3.10 and 3.11 (an f-string in the Duplicate Movies Report used a backslash escape, which only Python 3.12+ accepts). The Windows exe was not affected.

### Changed
- Self-test `tests/selftest_v0_18_4.py` with 129 checks (was 98), run in CI under a virtual display.
- The repository launcher `MediaClinic.bat` now starts `mediaclinic.py` from its own folder.

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
