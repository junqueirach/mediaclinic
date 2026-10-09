# =============================================================================
# help_text.py
# Metadata & MediaClinic — Help tab contents (pure text)
# Version: 0.18.3                                              ### NEW v0.18.3 ###
# Author:  Luiz Junqueira & Claude AI
#
# The Help dialog in the main script renders these strings.  Moved out of the
# main script in v0.18.3 and refreshed so every shortcut, menu entry and
# settings tab described here matches the code.
# =============================================================================

SEP = "─────────────────────────────────────────"

TAB_START = f"""{SEP}
  Metadata & MediaClinic  -  Getting Started
{SEP}

WHAT IS THIS APP?
  Metadata & MediaClinic is a KODI / Emby / Jellyfin media library
  auditor and repair tool. It scans a root media folder, checks every
  artwork file, metadata file, and video, then presents a colour-coded
  health table so you can see at a glance what is missing or broken.

  One subfolder = one movie. Each subfolder should contain:
    • poster.jpg       - portrait cover art (2:3 ratio)
    • folder.jpg       - identical copy of poster.jpg for KODI
    • fanart.jpg       - wide background art (16:9 ratio)
    • backdrop.jpg, backdrop1.jpg ...  - scene frames
    • MovieName.nfo    - KODI metadata in XML format
    • movie.xml        - Emby/Jellyfin metadata in XML format
    • MovieName.mkv    (or .mp4, .avi, etc.)

{SEP}
FIRST RUN
{SEP}

  1. Click  Browse...  and select your root media folder.
  2. Click  Full Scan.
     The table fills in phases: subfolders first, then images,
     then metadata, then video (with FFprobe if enabled).
  3. Each row shows the health of one movie:
       GREEN row   - no health rule triggered
       YELLOW row  - one or more warning rules triggered
       RED row     - one or more error rules triggered
     Which conditions count as error or warning is configurable in
     Settings → Health Rules.
  4. Your last scan is saved automatically and restored on startup.
     Quick Scan re-reads only folders that were added, removed, or
     whose files changed since the last scan.

{SEP}
QUICK-START CHECKLIST
{SEP}

  • Set your FFmpeg path in Settings → Tools
    (enables video analysis and backdrop extraction)

  • Add TMDb and/or OMDb API keys in Settings → API Keys
    (enables online ratings sync, source search and image fetching)

  • Configure your preferred browser in Settings → Browser

  • Set the "Lang OK?" language target in Settings → Language
    (default: PT - Portuguese)

  • Run a scan, sort by "Health (Errors 1st)" to triage problems,
    or type in the Filter box to narrow the table.

{SEP}
STATUS ICONS
{SEP}

  ⬤   OK / valid / present
  ◐   Warning - conflict, proportion mismatch, or minor issue
  ○   File missing
  ✕   Error - parse error or corrupt data

{SEP}
AUTOMATIC BACKUPS
{SEP}

  Whenever the app modifies a .nfo, .xml or image file it creates a
  silent backup before writing. Backups go in:

    backup/backup_MovieName_YYYY-MM-DD_HH-MM-SS/

  No popup is shown. Check logs/app.log for a full backup record.
  Settings → Backup limits the total size of the backup folder.

{SEP}
FILES THE APP WRITES
{SEP}

  settings.json        - all settings (in %APPDATA%\\MediaMetadataClinic)
  last_results.json    - the last scan, restored on startup (same folder)
  logs/app.log         - rotating log next to the program
  backup/              - automatic backups next to the program
"""

TAB_TABLE = f"""{SEP}
  Table & Columns
{SEP}

COLUMN REFERENCE

  Movie Name   - Title from NFO <title>, then XML <LocalTitle>,
                 NFO <originaltitle>, XML <OriginalTitle>, folder name.
                 Double-click opens the movie folder.

  Year         - Year from NFO <year> or XML <ProductionYear>.

  Genres       - Genres from NFO <genre> tags. Double-click opens .nfo.
                 Hover shows each genre and its validation status.

  Rating       - Rating from NFO <rating>, XML <IMDBrating>, or <Rating>.
                 Icon: ⬤ OK, ◐ values differ, ○ missing, ✕ unreadable.
                 Hover shows Rating, Votes, Source.

  Votes        - Vote count from NFO <votes>, XML <Votes>, <VoteCount>.
                 ◐ means NFO <votes> and XML <Votes> differ.

  Source       - IMDB and TMDB IDs across all NFO/XML tags.
                 ⬤ all tags agree  ◐ partial or conflict  ○ missing
                 ✕ a tag exists but is empty or unreadable.
                 Double-click opens the IMDB or TMDB website.

  Poster       - Status and quality tier of poster.jpg (2:3 portrait).
  Folder       - Status and quality tier of folder.jpg (copy of poster).
  Fanart       - Status and quality tier of fanart.jpg (16:9 landscape).
                 Hover shows dimensions, size, ratio, quality tier.

  Backdrops    - Count of backdrop images. Hover shows average size.

  .nfo / .xml  - Status of the metadata files. Double-click shows
                 parse errors (with Open File) or opens the editor.

  Language     - Language from XML <Language>.

  Video        - Container format. Video Size - size on disk.
  Quality      - Video resolution class (FFprobe).
  Audio        - Audio tracks from FFprobe:  EN (5.1), PT (2.0)
  Lang OK?     - Y/N: target language audio or subtitle present.
  Subtitles    - Embedded tracks (FFprobe) and external .srt files.

{SEP}
FILTER BAR
{SEP}

  Type in the Filter box (Ctrl+F) to show only movies whose name,
  year, genre, language, video quality or health status
  (ok / warning / error) matches. Esc clears the filter.
  The status bar shows "N of M shown".

{SEP}
IMAGE QUALITY TIERS
{SEP}

  Poster / Folder (2:3 portrait):
    4K 2000×3000 · 1440p 1500×2250 · 1080p 1000×1500 · 720p 666×1000
    540p 540×810 · 480p 480×720 · 360p 360×540 (floor)

  Fanart (16:9 landscape):
    4K 3840×2160 · 1440p 2560×1440 · 1080p 1920×1080 · 720p 1280×720
    540p 960×540 · 480p 854×480 · 360p 640×360 (floor)

  ±5% tolerance. Minimum tiers are set in Settings → Image Sizes.

{SEP}
COLUMN WIDTHS
{SEP}

  Drag a header separator to resize one column (neighbours keep
  their width). Double-click a header to auto-size it.
  Widths are remembered between sessions.
"""

TAB_ACTIONS = f"""{SEP}
  Actions
{SEP}

DOUBLE-CLICK ACTIONS

  Movie Name    Movie folder in Windows Explorer
  Genres        .nfo file in your text editor
  Rating/Votes  .nfo file in your text editor
  Source        Popup to choose IMDB or TMDB website
  Poster/Folder/Fanart   The image in your image viewer
  Backdrops     First backdrop image
  .nfo / .xml   Parse-error dialog, or the file in your editor
  Language      movie.xml in your editor
  Video/Quality Plays the video
  Subtitles     Subtitle tracks dialog

{SEP}
RIGHT-CLICK MENU (SINGLE MOVIE)
{SEP}

  Open Folder · Open poster/folder/fanart.jpg · Play Video
  Extract Backdrop(s)   - Extract frames from the video (FFmpeg)
  Subtitles…            - Show subtitle tracks
  Open .nfo / movie.xml - Open in editor; "[!] errors" shows details
  Open on IMDb / TMDb / Fanart.tv / OpenSubtitles.org
  Copy Movie Name       - Copy the title to the clipboard
  Open in Scraper       - Launch your configured scraper

  Run Improvements Check · Health Status Report
  Sync Ratings          - Fetch rating/votes from TMDb and/or OMDb
  Normalize Sources     - Repair IMDB/TMDB tags in XML/NFO
  Search Sources        - Search TMDB online by title + year
  Normalize Genres      - Fix capitalisation, synonyms, duplicates
  Fetch Poster/Folder · Fetch Fanart · Fetch Backdrops
  Replace All Backdrops - Backup, delete, re-download all from TMDB
  Add Custom Genre(s)   - Add detected custom genres to Settings

  Update (no FFprobe)   - Re-read metadata and images; keeps the
                          previous FFprobe data; recomputes health
  Update (with FFprobe) - Full re-read including video analysis
  Refresh Icons

{SEP}
RIGHT-CLICK MENU (MULTI-SELECTION)
{SEP}

  Select rows with Ctrl+click, Shift+click or Shift+arrows.
  Batch versions appear for Improvements Check, Health Report,
  Sync Ratings, Normalize/Search Sources, Normalize Genres,
  Fetch Poster/Fanart/Backdrops, Extract Backdrops, and both
  Update commands. Ten or more movies show a progress window;
  Cancel or Esc stops the batch.

{SEP}
TOOLS MENU
{SEP}

  Export Movie List…         - CSV / TSV / text / Excel (see below)
  Save / Open Scan Results   - Full scan to and from a JSON file
  Sync Ratings Online — All Movies
  Normalize Sources — All Movies (only ◐ or ○ rows)
  Search Sources — All Movies
  Normalize Genres — All Movies
  Run Improvements Check — All Movies  (report saved to .txt)
  Health Status Report — All Movies
  Refresh Icons — All Movies
  Delete All extrafanart Subfolders (legacy) - preview + backup

{SEP}
EXPORT MOVIE LIST
{SEP}

  Tools → Export Movie List… (or the Export… button, Ctrl+Shift+E).

  Columns:  Basic (Name, Year), Standard, All, or tick your own.
  Rows:     All movies, or only the current filtered/sorted view.
  Formats:
    CSV (comma)      - default; movie names with commas are quoted
                       so they never break the file
    CSV (semicolon)  - for Excel in Swiss/German/Portuguese/French
                       locales, where comma CSV opens in one column
    Tab-separated    - .txt, pastes cleanly into spreadsheets
    Plain text list  - one "Movie Name (Year)" per line
    Excel .xlsx      - real workbook with a filter row (needs the
                       openpyxl package; greyed out if absent)
"""

TAB_RATINGS = f"""{SEP}
  Ratings Sync
{SEP}

  Fetches ratings and vote counts from TMDb and/or OMDb/IMDb and
  writes them to NFO (<rating>, <votes>) and XML (<IMDBrating>,
  <Rating>, <Votes>, <VoteCount>). Requires API keys.

  Single movie:     Right-click → Sync Ratings from IMDb / TMDb
  Selected movies:  Right-click → Sync Ratings (N movies)
  All movies:       Tools → Sync Ratings Online — All Movies

  The popup shows TMDb and OMDb/IMDb side by side. A source with
  no data shows "Not Available". Zero ratings or zero votes count
  as no data. "Type Values" lets you enter rating and votes by hand.

  Batch checkboxes:
    Apply this choice to all remaining movies
    Use the source with more votes (equal votes → average)
  Defaults for both live in Settings → Ratings.

{SEP}
RATING AND VOTES ICONS
{SEP}

  ⬤  value found, all sources agree
  ◐  values differ between NFO and XML (health: conflict rule)
  ○  no tag found
  ✕  tag exists but is not a number (health: unreadable rule)

{SEP}
NORMALIZE GENRES
{SEP}

  Standardises genre tags in NFO and XML:
    • capitalisation   ("action" → "Action")
    • synonyms         ("Sci-Fi" → "Science Fiction")
    • translations     (PT, DE, FR, ES, IT, RU, ZH, AR → English)
    • duplicates removed
    • merged tags split on / \\ | , ;  ("Family/Fantasy")

  Genres not in Settings → Genres are "custom". For each movie with
  custom genres you are asked whether to delete or keep them.
  Right-click → Add Custom Genre(s) adds them to the list instead.

{SEP}
SOURCE IDS
{SEP}

  Normalize Sources repairs IMDB/TMDB tags:
    Case A: tags disagree only by omission → missing tags filled in
    Case B: tags hold different IDs → choose the right one (titles
            are looked up on TMDB to help you decide)
    Case C: no ID anywhere → type one
  Search Sources queries TMDB by title + year and offers Apply.
"""

TAB_AUDIO = f"""{SEP}
  Audio, Subtitles & Images
{SEP}

AUDIO COLUMN
  Shows FFprobe audio tracks as LANGUAGE (CHANNELS), sorted
  alphabetically. Hover for codec and bitrate per track.
  Populated only by scans or updates that run FFprobe; a scan
  without FFprobe keeps the previous values.

SUBTITLES
  Embedded tracks (FFprobe) and external files in the folder.
  External files are tagged by the language suffix: Movie.pt.srt.

LANG OK?
  Y when the target language (Settings → Language) is found in
  audio streams, embedded subs, external subs, XML <Language> /
  <LanguageCode>, or NFO <language>.

{SEP}
BACKDROPS
{SEP}

  Extract Backdrop(s)   - FFmpeg frames evenly spread over the film
                          (count and timeout configurable in the popup)
  Fetch Backdrops       - Pick TMDB backdrops; replace a local file
                          or download as a new backdropN.jpg
  Replace All Backdrops - Backs up and deletes all local backdrops,
                          then downloads every TMDB backdrop
  Health rules flag too few backdrops and suspiciously small ones.

{SEP}
POSTER / FANART FETCH
{SEP}

  Fetch Poster/Folder shows the local image next to TMDB posters
  (highest resolution first). "Use This" downloads the original
  size to poster.jpg and copies it to folder.jpg, after a backup.
  Fetch Fanart does the same for fanart.jpg.

PROPORTION CHECKS
  Poster / Folder: 2:3 (optionally also 3:4).
  Fanart: 16:9 (optionally also 16:8).
  Wrong proportions are warnings, not errors.

{SEP}
SORTING
{SEP}

  Movie Name (accent-insensitive) · Year · Genre · Rating · Votes
  Sources · Poster / Folder / Fanart Quality · Backdrops · Language
  Video Quality · Video size · Lang OK? · Health (Errors / Warning /
  OK first). Sorting is stable; the filter is applied after sorting.
"""

TAB_SETTINGS = f"""{SEP}
  Settings Reference
{SEP}

TOOLS
  Text editor, FFmpeg folder (Test FFmpeg), default backdrop frame
  count, metadata source, optional scraper executable.

API KEYS
  TMDb and OMDb keys with Validate buttons and links to get them.

BROWSER
  Browser used for web links. Changing it never triggers a rescan.

LANGUAGE
  ISO 639-1 code for the Lang OK? column (default PT).

IMPROVEMENTS
  Toggles for the Improvements Check report and the NFO/XML
  maximum sizes (also used by the "too large" health rule).

IMAGE SIZES
  Minimum quality tier per image type, 3:4 and 16:8 acceptance,
  legacy minimum file sizes in KB.

RATINGS
  Defaults for the two batch checkboxes of the Ratings Sync popup.

GENRES
  The standard genre list (one per line). Anything else is custom.

NFO / XML
  Tag pairs compared by the Improvements Check (dot paths,
  optional tolerance %).

USER INTERFACE
  Alternating row colours, header tooltips, compact mode
  (smaller rows). Dark theme / auto-fit / image size are reserved.

HEALTH RULES
  Every condition that can turn a row red (error rules) or yellow
  (warning rules) has its own checkbox; some have a level or
  threshold. After saving, you are offered an in-memory update of
  the health status - no rescan needed. "Reset to defaults"
  restores the shipped rule set.

BACKUP
  Maximum backup folder size (oldest backups deleted first, 0 =
  unlimited) and a button to delete all backups.

AFTER SAVING
  Changes to Image Sizes, Language, Genres or NFO/XML tags offer an
  Update Scan (with or without FFprobe). Health rule changes offer a
  health status update. Browser-only changes offer nothing.
"""

TAB_SHORTCUTS = f"""{SEP}
  Keyboard Shortcuts
{SEP}

  F1 / Ctrl+H     - Open Help
  F5              - Full Scan
  Esc             - Cancel a running scan; clear the Filter box
  Ctrl+F          - Jump to the Filter box
  Ctrl+L          - Clear All results
  Ctrl+S          - Open Settings
  Ctrl+O          - Open the selected movie's folder
  Ctrl+E          - Open the selected movie's .nfo in the editor
  Ctrl+R          - Update selected movie (no FFprobe)
  Ctrl+Shift+R    - Update selected movie (with FFprobe)
  Ctrl+I          - Refresh all icons
  Ctrl+Shift+E    - Export Movie List…

  A-Z, 0-9        - Jump to the next movie starting with that
                    character (repeat the key to cycle)
  Page Up/Down, Home, End   - Move the selection
  Shift+Up/Down   - Extend or shrink the selection
  Double-click    - Action depends on the column
  Right-click     - Context menu for the selected row(s)

{SEP}
TROUBLESHOOTING
{SEP}

  Audio column is empty
    Requires FFprobe. Enable the FFprobe checkbox and run
    "Update (with FFprobe)" on the affected movies.

  Quick Scan says "No changes detected" after editing a file
    Quick Scan compares each folder's newest file time with the
    time recorded at the last scan. Run one Full Scan after
    upgrading to v0.18.3 so the times are recorded.

  Source column shows ✕ although the movie has an ID
    A tag exists but is empty (for example <TMDB></TMDB>).
    Normalize Sources fills it in.

  Backdrop extraction produces no files
    Check FFmpeg in Settings → Tools; raise the per-frame timeout.

  Excel opens the CSV in a single column
    Use Export Movie List → "CSV — semicolon separated", or .xlsx.

  Application log
    logs/app.log next to the program holds errors and backup records.

{SEP}
CREDITS
{SEP}

  Metadata & MediaClinic is developed by Luiz Junqueira with Claude AI.
  Built to keep KODI / Emby / Jellyfin media libraries clean,
  complete, and metadata-perfect.
"""

TAB_VERSION = f"""{SEP}
  Version History  —  Metadata & MediaClinic
{SEP}

  v0.18.3 - NEW: Export Movie List… (Tools menu, Export… button,
                 Ctrl+Shift+E): column presets, filtered view, CSV
                 comma/semicolon, tab-separated, plain text, Excel.
             NEW: Scan results stored in last_results.json instead of
                 settings.json (settings file shrinks from MB to KB;
                 scans no longer rewrite it every few rows).
             NEW: Each NFO/XML and image header is read once per movie
                 during a scan (metadata phase noticeably faster).
             NEW: Health rules "IMDB/TMDb ID present in one file only".
             NEW: Compact mode setting now reduces row height.
             NEW: Esc cancels a running scan.
             FIX: Tools → Run Improvements Check — All Movies failed
                 with "name '_run_improvements_check' is not defined".
             FIX: Settings menu opened the wrong tab (Ratings → Health
                 Rules, Genres → Ratings, …); Health Rules entry added.
             FIX: Quick Scan never detected modified movies, and
                 computed health before restoring FFprobe data.
             FIX: "Update Scan (no/with FFprobe)" after a settings save
                 both followed the FFprobe checkbox instead of the button.
             FIX: Full Scan without FFprobe dropped the Audio column.
             FIX: Source/Rating/Votes health messages were swapped
                 ("conflict" shown for an empty tag; real conflicts
                 were silent).
             FIX: Title mismatch compared all four title tags; now only
                 NFO <title> vs XML <LocalTitle>.
             FIX: TMDB image download never retried on 429/5xx/timeout
                 (exception handlers were in the wrong order).
             FIX: OMDb key validation accepted invalid keys.
             FIX: Scroll-wheel bindings leaked after closing the Search
                 Sources window and the Health Rules tab.
             FIX: Column widths restored even without a saved session;
                 startup log line reported the wrong version.
             CODE: ~1,900 lines removed from the main script — duplicated
                 settings/backup/quality code now imported from the
                 settings modules; Help text and genre tables moved to
                 help_text.py and genre_data.py; dead code removed.
             DOC: Help rewritten to match the actual shortcuts and menus.

  v0.18.2 - NEW: Configurable Health Rules engine (Settings → Health
                 Rules) with error and warning groups, levels and
                 thresholds; in-memory health update after save.
             NEW: Health Status Report (right-click and Tools menu).
             NEW: Filter bar above the table (Ctrl+F).
             NEW: Required audio / subtitle language rules.

  v0.18.0 - NEW: Column widths persisted between sessions.
             NEW: Replace All Backdrops (backup, delete, re-download).
             NEW: Open on Fanart.tv.
             NEW: Resilient TMDB image downloader with retries.
             NEW: Backdrop counting tolerates numbering gaps.
             FIX: Scroll wheel scoped to the window under the pointer.

  v0.17.x - NEW: Fetch Backdrops dialog (local vs TMDB, replace or add).
             NEW: Full Scan / Quick Scan naming with tooltips.
             NEW: Sources sort options; Type Values in Ratings Sync.
             NEW: Progress popup for batch operations (≥10 movies).
             NEW: Extrafanart deletion with preview and backup.
             FIX: Column resize no longer shrinks neighbours.
             FIX: Shift+Up/Down selection, jump-to-letter reliability.
             FIX: FFprobe duration fallback chain for MP4/MKV.

  v0.16.1 - Default sort Movie Name (A-Z); Shift+Arrow rewritten;
             7-tier image quality system with automatic migration.

  v0.16.0 - Votes and Source columns; Normalize Sources; Search
             Sources; Fetch Poster/Folder and Fetch Fanart; Save/Open
             Scan Results; multilingual genre translation.

  v0.15.0 - Audio column; rating tooltip with votes and source;
             per-movie custom genre dialog; Ratings settings tab;
             redesigned Tools menu; accent-insensitive sorting.

  v0.14.0 - Settings subsystem split into four modules; FFmpeg test
             and browser detection off the UI thread; test harness.

  v0.13.x - Browser-only change no longer prompts a rescan; merged
             genre splitting; jump-to-letter; non-blocking settings save.

  v0.12.0 - Merged image columns; Rating column; Backup tab; 3:4
             acceptance; Add Custom Genre(s).

  v0.11.0 - Silent backups before every write; image quality tiers;
             16:8 acceptance; F1 help.

  v0.10.x - COLUMN_MODEL architecture; settings_dialog.py extracted;
             status bar, shortcuts, NFO/XML pre-validation.

  v0.9.0  - Online Ratings Sync; Genre column; API keys; browser
             selection; improvements report.

  v0.8.0  - Settings menu, Improvements engine, IMDB/TMDb links,
             FFprobe checkbox, language column, multi-selection.

  v0.7.0 and earlier - original releases.
"""
