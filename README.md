# MediaClinic

**A library health tool for Plex, Kodi, Emby and Jellyfin users: scan your offline movie library, find broken or incomplete metadata and artwork, and fix them.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey) [![CI](https://github.com/junqueirach/mediaclinic/actions/workflows/ci.yml/badge.svg)](https://github.com/junqueirach/mediaclinic/actions/workflows/ci.yml)

<p align="center"><img src="docs/screenshots/mediaclinic.png" alt="MediaClinic screenshot" width="900"></p>

**Download for Windows:** get `MediaClinic-0.19.1-win64.zip` (about 19 MB) from the [latest release](https://github.com/junqueirach/mediaclinic/releases/latest). Unzip it to a folder you can write to (not `C:\Program Files`), open the `MediaClinic` folder and double-click `MediaClinic.exe`. No Python needed. The SHA-256 checksum is in the release notes.

> **Windows SmartScreen:** the file is not code-signed, so Windows may show "Windows protected your PC". Click **More info**, then **Run anyway**. You can also run the app from source (see Quick start) and read every line of the code first.

## How it works

<p align="center"><img src="docs/screenshots/how-it-works.png" alt="How it works" width="900"></p>

MediaClinic expects one subfolder per movie, the layout used by Plex, Kodi, Emby and Jellyfin. It checks Kodi `.nfo` and Emby/Jellyfin `movie.xml` files, so it also suits Plex libraries that use an NFO add-on. It checks every artwork file, metadata file and video, and shows one colour-coded health table, red for errors and yellow for warnings. From the same table you can repair the common problems in place.

## What it checks

| Area | Checks |
|---|---|
| Artwork | `poster.jpg`, `folder.jpg`, `fanart.jpg` (or the Kodi names `<video>-poster.jpg`, `<video>-fanart.jpg`, `.png`, `.tbn`) present, decodable (corrupt kept apart from too small), right proportions, minimum resolution tier (4K to 360p), minimum file size, file format matching the extension |
| Backdrops | `backdrop.jpg`, `backdrop1.jpg` and so on, plus Kodi extra fanart (`fanart1.jpg`, `extrafanart/`): count and average size |
| Metadata | `MovieName.nfo` or `movie.nfo` (Kodi) and `movie.xml` (Emby/Jellyfin) present and well-formed; every error is listed with its line and tag name. DVD and Blu-ray folders (`VIDEO_TS`, `BDMV`) count as one movie |
| Identity | IMDB and TMDB IDs across all NFO/XML tags: missing, empty, conflicting, or present in one file only; duplicate movies (same ID, or same title and year, in another folder, also across libraries); optional online check that the IDs point to the right film |
| Ratings, titles, year | Rating and votes (legacy tags and Kodi v17+ `<ratings>` blocks), NFO title against XML local title, missing year |
| Genres | Non-standard genres, synonyms, merged tags such as `Family/Fantasy`, translations from eight languages, genres present in only one of NFO and XML |
| Video (FFprobe) | Resolution class, audio tracks and languages (an undefined track takes its language from the NFO/XML), embedded subtitles, hard-coded subtitles you mark by hand, required language. One probe per video, cached |

Every check is a **health rule** you can switch on or off, or tune, in *Settings → Health Rules*.

## What it fixes

- **Normalize Genres** and **Normalize Sources**: written to both NFO and XML; movies without genres can get them from TMDb or OMDb after a preview
- **Sync Ratings** from TMDb and OMDb (you supply your own free API keys)
- **Verify IMDb/TMDb IDs** against TMDb (title in any translation, year ±1) with a sortable report
- **Auto Repair** for one movie, a selection or the whole library, with a dry-run preview: IDs, ratings, genres, year, titles and XML language; artwork is never touched
- **Fetch Poster, Fanart and Backdrops** from TMDB or fanart.tv with thumbnails, or pick **frames from the video** with FFmpeg; new files follow the folder's naming style (Kodi or Emby)
- **Enter ID…**: type an IMDb or TMDb ID by hand, check the film it points to, and write it to NFO and XML
- **Backup History / Undo**: every backup records what it changed, and a whole run can be restored
- **Copy poster.jpg → folder.jpg** where the two differ, for one movie, a selection or the whole library
- **Export Movie List** to CSV, text or Excel, with column presets (including *Identify*: IMDB and TMDB links plus outline) and the option to export only the filtered view
- **Several libraries** in one table (*Libraries…* dialog and library filter); an offline drive keeps its cached rows
- **Large libraries**: parallel scanning, clickable Errors/Warnings counters, *Problems only*, a column chooser, Library Statistics and a Duplicate Movies Report
- **Safe edits**: every NFO/XML is backed up silently and written atomically, TMDb/OMDb calls are rate-limited and retried, API keys are kept out of the log, with automatic backup folder maintenance; rows refresh automatically after each change
- Keyboard shortcuts, jump-to-letter, sortable columns, a Quick Scan that re-reads only what changed, remembered window sizes and positions, rotating logs

## Quick start

From the Windows download, just run `MediaClinic.exe`. From source:

```
pip install -r requirements.txt     # optional: pillow, openpyxl
python mediaclinic.py
```

Run it from the folder that contains the `settings_*.py` files. FFmpeg and FFprobe are optional but recommended (point *Settings → Tools* to their `bin` folder). Settings, your API keys and the last scan are stored in `%APPDATA%\MediaMetadataClinic\`, outside this repository; `logs/` and `backup/` are created next to the program. See [docs/help](docs/help) for the in-app help pages.

## Engineering notes

This project is the clearest example of working with an AI under a written contract:

- [`docs/CLAUDE_RULES.md`](docs/CLAUDE_RULES.md) defines module boundaries, the save chain, naming rules and a safety checklist that every AI-edited change must respect
- `settings_schema.json` plus `tests/settings_test_harness.py` check the settings subsystem after every change
- `tests/selftest_v0_19_1.py` builds a synthetic library (NFO, XML, generated JPEGs and a real 3-second MKV) and runs about 660 end-to-end checks, from health rules to Auto Repair and the export dialogs (TMDb calls are simulated); it runs in CI under a virtual display (a few Windows-only path checks are skipped on Linux) and never touches your real settings
- The code is split into model, controller, context, dialog, export, help and genre-data modules so the AI can edit one part without breaking another
- About 21,300 lines of Python in eight modules; 33 earlier versions in `archive/versions/`, starting from a 12 KB folder scanner
- Changes per version are in [CHANGELOG.md](CHANGELOG.md)

---

## How this was built

Built with **Claude (Anthropic)** as the coding partner. I wrote the requirements and the revision prompts, tested every build on real data, and decided what to fix next. The `archive/versions/` folder keeps every earlier release so the iteration history is visible.

**Security note:** the app stores any API keys you enter in a local settings file outside this repository. `.gitignore` excludes config and settings files so keys are never committed.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Bug reports and ideas are welcome through the issue templates.

## Licence

MIT. See [LICENSE](LICENSE). This product uses the TMDB API but is not endorsed or certified by TMDB. OMDb data is subject to the [OMDb API terms](https://www.omdbapi.com/legal.htm). FFmpeg is a separate download under its own license.

## Author

Luiz Junqueira - [junqueira.ch](https://www.junqueira.ch) - [LinkedIn](https://www.linkedin.com/in/luizjunqueira/)
