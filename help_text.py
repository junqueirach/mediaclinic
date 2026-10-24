# =============================================================================
# help_text.py
# Metadata & MediaClinic — Help tab contents (pure text)
# Version: 0.19.3                                              ### MODIFIED v0.19.3 ###
# Author:  Luiz Junqueira & Claude AI
#
# The Help dialog in the main script renders these strings.  Moved out of the
# main script in v0.18.3.
#
# v0.19.1 — rewritten to one layout (B10) and reorganised (B9):
#   • section titles in capitals at the left margin
#   • body text indented by 2 spaces
#   • bullets as "  •  " with continuation lines aligned under the text
#   • key / description tables aligned in two columns
#   • lines at most 72 characters, one blank line between sections
# The Version History tab was removed; the history lives in the CHANGELOG at
# the top of the main script and in README.md.
# HELP_TABS gives the tab order used by BOTH the Help window and the Help
# menu, so the two can never drift apart.
# =============================================================================

SEP = "─" * 60


def _title(text):
    return f"  {text}\n{SEP}\n"


TAB_START = _title("Getting Started") + """
WHAT IS THIS APP?
  Metadata & MediaClinic audits and repairs KODI / Emby / Jellyfin
  movie libraries. It scans your library folders, checks every
  artwork file, metadata file and video, and shows a colour-coded
  health table so you see at a glance what is missing or broken.
  Most problems can be fixed from the same table.

LIBRARY LAYOUT
  One subfolder = one movie. Each movie folder should contain:
  •  MovieName.mkv (or .mp4, .avi …) — the video
  •  MovieName.nfo — KODI metadata (XML)
  •  movie.xml — Emby / Jellyfin metadata (XML)
  •  poster.jpg — portrait cover art, 2:3
  •  folder.jpg — identical copy of poster.jpg
  •  fanart.jpg — wide background art, 16:9
  •  backdrop.jpg, backdrop1.jpg … — extra backgrounds
  •  MovieName.pt.srt … — optional external subtitles

FIRST RUN
  1.  Click Browse… and choose your movie folder. Add more folders
      later with Libraries… (see the Scans & Libraries tab).
  2.  Click Full Scan. The table fills in phases: folders, images,
      metadata, then video (with FFprobe when the FFprobe switch,
      top right next to "FFmpeg ✓", is On).
  3.  Each row shows the health of one movie:
      green   no health rule triggered
      yellow  one or more warning rules triggered
      red     one or more error rules triggered
  4.  The last scan is saved and restored on the next start.

QUICK-START CHECKLIST
  •  Settings → Tools: set the FFmpeg folder (video analysis and
     backdrop extraction).
  •  Settings → API Keys: add TMDb and OMDb keys (ratings, ID
     search and verification, artwork); optional fanart.tv key
     for more posters and backdrops.
  •  Settings → Language: the Lang OK? target (default PT).
  •  Settings → Health Rules: choose what counts as an error or a
     warning.
  •  Sort by Health (first in the Sort by list: Errors first, one
     click → Warnings first), click the Errors counter, or tick
     "Problems only" to triage.

STATUS ICONS
  ⬤   OK — present and valid
  ◐   warning — conflict, wrong proportions, minor issue
  ○   missing
  ✕   error — corrupt image, XML parse error, unreadable value

AUTOMATIC BACKUPS
  Before the app changes a .nfo, .xml or image file, it copies the
  original to backup/backup_MovieName_DATE_TIME/ next to the
  program. Every NFO/XML write is atomic: a failed write never
  leaves a half-written file. Settings → Backup limits the size.
  Each backup folder has a manifest.json (where every file came
  from, which action made it). Tools → Backup History / Undo…
  lists the runs, newest first, and "Restore this run" puts the
  files back: your current files are backed up first (so an undo
  can be undone), files changed after the run are listed and can
  be skipped, and the rows are refreshed. Backups made before
  v0.19.1 have no manifest: restore those by hand.

FILES THE APP WRITES
  settings.json       all settings (%APPDATA%\\MediaMetadataClinic)
  last_results.json   the last scan, restored on start (same folder)
  ffprobe_cache.json  remembered FFprobe results (same folder)
  fanarttv_cache.json fanart.tv answers, kept 7 days (same
                      folder, no key inside)
  logs/app.log        rotating log next to the program (API keys
                      are never written to it); Help → Open logs
                      folder shows it. Every unexpected error is
                      written there too: attach it to a bug report.
  backup/             automatic backups next to the program
"""

TAB_TABLE = _title("Table & Columns") + """
COLUMNS
  Movie Name    NFO <title>, then XML <LocalTitle>, original
                titles, folder name. Hover shows the folder, its
                library, the date added and every health reason
                (errors ✕, warnings ⚠). Double-click opens the
                folder.
  Year          NFO <year> or XML <ProductionYear>.
  Genres        NFO <genre> tags; when the NFO has none, the XML
                <Genres> are shown (the tooltip names the source).
  Rating        NFO <rating> (or the Kodi <ratings> block), XML
                <IMDBrating> / <Rating>. Hover: value, votes,
                source.
  Votes         NFO <votes>, XML <Votes> / <VoteCount>.
  Source        IMDb and TMDb IDs across all NFO/XML tags.
                ⬤ all agree   ◐ partial or conflict   ○ missing
                (also when all its tags are empty placeholders)
                ✕ some tags filled, some empty. Hover shows the
                last Verify IDs result. Double-click opens IMDb or
                TMDb.
  Poster        poster.jpg status and quality tier (2:3).
  Folder        folder.jpg status and quality tier.
  Fanart        fanart.jpg status and quality tier (16:9).
  Backdrops     number of backdrop images; hover: average size.
  .nfo / .xml   metadata file status. Hover lists the errors with
                the exact line and tag names, e.g. "Line 12:
                `<plot>` opened here is never closed (expected
                `</plot>` before `</movie>` on line 40)" — the
                first 5, then "n more"; an unescaped & is shown
                as a note only. Double-click opens the file in
                your editor.
  Language      XML <Language>.
  Video         container and size; Quality: resolution class.
  Audio         FFprobe audio tracks, e.g. EN (5.1), PT (2.0).
  Lang OK?      Y / N: target language in audio or subtitles.
  Subtitles     embedded tracks (FFprobe) and external files.
  Library       the library (root folder). Hidden by default:
                Tools → Choose Columns….

FILTER AND VIEW
  Type in the Filter box (Ctrl+F) to keep only movies whose name,
  year, genre, language, quality, health status or any health
  reason matches — "backdrops" lists every backdrop issue. Esc
  clears it.
  •  "Problems only" hides green rows.
  •  Click the Errors or Warnings counter to show only those rows;
     click again (or click Movies) to show everything.
  •  The library box next to Libraries… shows one library or all.
  •  Tools → Choose Columns… hides columns; the choice is kept.

SORTING
  The sort row: "Sort by [column] [direction]", then up to two
  more levels with "+ then by" (✕ removes one). The direction is
  said in words: A → Z, Newest first, High → low, Worst first,
  Most first, Errors first … Click it to turn it round.
  •  Every column can be used, plus Health and Number of issues
     (the first two entries of the list) and Date added (NFO
     <dateadded>, XML <DateAdded>, else the creation date of the
     video file or the folder). Health: Errors first → Warnings
     first → OK first.
  •  Click a column heading to sort by it (again = reversed);
     Shift+click adds it as the next level. ▲1 / ▼2 in the
     heading show the levels. A double-click only auto-sizes.
  •  Empty values (no rating, no poster, no date) always go last;
     equal values stay in Movie Name order, A → Z.
  •  ★ Presets: Problems first, Worst artwork first, Missing
     metadata, Best rated, Biggest files, By library, and your
     own ("Save current sort as preset…"). Ctrl+1 … Ctrl+9 apply
     presets 1 to 9.
  •  "↺ Update View" (after the last level) sorts and filters the
     list again, so movies you just fixed move to their place.
  •  The sort is kept after a scan and after a restart.

DUPLICATES
  Movies that share an IMDb ID, a TMDb ID, or a title + year are
  "Possible duplicate" (same title + year with two different
  IMDb IDs are not: a remake or a namesake). Right-click →
  "✔ Not a duplicate…" (right below the movie name) remembers
  your answer in not_duplicates.json, so the warning stays gone;
  a new third copy is still found. "↺ Undo 'not a duplicate'"
  takes it back; Tools → Manage 'Not a duplicate' marks… lists
  every pair.

IMAGE QUALITY TIERS
  Poster / Folder (2:3):  4K 2000×3000 · 1440p 1500×2250
                          1080p 1000×1500 · 720p 666×1000
                          540p 540×810 · 480p 480×720 · 360p
  Fanart (16:9):          4K 3840×2160 · 1440p 2560×1440
                          1080p 1920×1080 · 720p 1280×720
                          540p 960×540 · 480p 854×480 · 360p
  ±5 % tolerance. The minimum tier is one setting, shown in both
  Settings → Health Rules and Settings → Image Sizes. Images below
  it are warnings. "Corrupt" (✕) means the file cannot be decoded:
  no JPEG/PNG signature, truncated data or 0 bytes. A PNG named
  poster.jpg is still read and gets an "extension mismatch"
  warning.

COLUMN WIDTHS AND WINDOWS
  Drag a header edge to resize one column; double-click a header
  to fit it. Widths, window sizes and positions (and whether the
  main window was maximised) are remembered.
"""

TAB_SCANS = _title("Scans & Libraries") + """
SCANS
  Full Scan     re-reads every movie of the libraries in scope.
  Quick Scan    reads only movies that were added, removed or
                changed since the last scan.
  FFprobe       the switch top right ("FFmpeg ✓ | FFprobe On"):
                when On, scans also read video resolution,
                audio tracks and embedded subtitles. A scan without
                FFprobe keeps the previous FFprobe data.
  Cancel / Esc  stops a running scan.
  Folders that are not movies (TV series, folders of folders …)
  get no row: see IGNORED FOLDERS.

IGNORED FOLDERS
  A scan adds a row only for movie folders. These are not added:
  •  TV series: tvshow.nfo, Season folders or episode files
     (S01E02, 1x02). Series support is planned.
  •  Folders holding other movie folders: the library is one
     level too high. Add the inner folders as libraries.
  •  Folders with several separate videos: give each movie its
     own folder.
  •  Folders with no video, NFO or XML (empty, pictures only).
  •  System folders ($RECYCLE.BIN, @eaDir …) and folders that
     could not be read.
  A folder with movie metadata (movie.nfo, movie.xml) is always
  a movie, and so is a folder with one video and no NFO. A movie
  with an NFO/XML but no video stays in the table ("Missing video
  file") and is also listed in the report.
  Videos lying directly in a library folder are listed too.
  After a scan the Ignored folders window opens when something
  was left out: filter, sort by a column, double-click to open
  the folder, Export to TXT… or Copy all. Turn it off with "Show
  this window after a scan". Tools → Ignored Folders of the Last
  Scan… opens it at any time; the status bar shows "n folders
  not added — View".

UPDATING SINGLE MOVIES
  Right-click → Update (no FFprobe) re-reads one movie (or the
  selection); Update (with FFprobe) also re-probes the video.
  After every repair, sync, fetch, extract or delete the affected
  rows refresh automatically, without FFprobe — no manual Update
  is needed.

LIBRARIES
  You can scan several root folders. Browse… adds one folder;
  Libraries… adds, removes and orders them. After the list
  changes the app offers Full Scan, Quick Scan or Not now.
  •  All libraries share one table; the Library column and the
     Movie Name tooltip show where a movie lives.
  •  The library box chooses what the table shows and what Full
     and Quick Scan cover ("All libraries" or one of them); each
     entry shows its number of movies.
  •  The folder box at the top always lists every library. With
     a filter the shown one is marked ▶ ("showing 1 of n"), and
     the status bar says how many libraries are hidden: click
     "show all" to see them again. Click the folder box to open
     Libraries….
  •  Duplicates are found across libraries.
  •  A library that cannot be reached (for example an unplugged
     network share) keeps its last scan, is skipped by scans and
     is shown as "(offline)".

MOVIES THAT DISAPPEAR
  When a movie folder was deleted, Update or the automatic
  refresh removes its row (its duplicate twin loses the warning).
  Right-click → Remove from list drops rows without touching any
  file; the next scan brings back movies that still exist.

STARTUP
  The last scan is loaded from last_results.json in the
  background ("⏳ Loading last scan…") and the health rules are
  applied again, so changed rules never leave old reasons behind.
  A big library is put into the table 50 rows at a time, so the
  window answers at once.
"""

TAB_ACTIONS = _title("Actions & Tools") + """
DOUBLE-CLICK
  Movie Name      the movie folder
  Genres          the .nfo file in your editor
  Rating, Votes   the .nfo file in your editor
  Source          choose IMDb or TMDb website
  Images          poster, folder or fanart in your viewer
  Backdrops       the first backdrop
  .nfo / .xml     the file in your editor (also when it has errors)
  Language        movie.xml in your editor
  Video, Quality  plays the video
  Subtitles       subtitle tracks
  Library         the library folder

RIGHT-CLICK MENU (also Shift+F10 or the Menu key)
  The first line names the movie (or "N movies selected") and the
  number of issues.
  •  ⚠ Fix issues: the selection's real problems, each linked to
     the action that fixes it (with several movies: how many
     movies have each problem; the action runs on just those).
  •  Repeat: the last action again, on the current selection
     (Settings → User Interface can hide this line).
  •  Open Folder (Ctrl+O), Play Video, Edit NFO (Ctrl+E).
  •  Artwork: open the images; Fetch Poster/Folder, Fanart,
     Backdrops; Replace All Backdrops; Extract Backdrop(s); Copy
     poster.jpg → folder.jpg; Fix image proportions / size.
  •  Metadata: open .nfo / movie.xml, "[!] errors" (all parse
     errors of a broken file), Sync Ratings, Normalize Genres,
     Add Custom Genre(s).
  •  IDs & Sources: Search Sources, Verify IMDb/TMDb IDs,
     Normalize Sources, Copy Movie Name.
  •  Video & Subtitles: Subtitles…, Hard-coded subtitles…,
     Extract Backdrop(s).
  •  Open online: IMDb, TMDb, Fanart.tv, OpenSubtitles.org, Open
     in Scraper.
  •  Check & Repair: Health Status Report, Run Improvements
     Check, Auto Repair.
  •  Update: no FFprobe (Ctrl+R), with FFprobe (Ctrl+Shift+R),
     Refresh Icons; Remove from list.
  An action that does not apply stays in its place, greyed, with
  the reason (for example "missing" or "one movie only").

RIGHT-CLICK — SEVERAL MOVIES
  Select with Ctrl+click, Shift+click, Shift+arrows or
  Shift+PageUp / PageDown / Home / End. The same menu runs the
  batch versions. Longer runs show a progress window with
  Cancel.

TOOLS MENU
  Export Movie List…        CSV, TSV, text or Excel
  Choose Columns…           show or hide columns
  Ignored Folders…          folders the last scan did not add
  Fix Image Proportions / Size — All Movies with image warnings
  Library Statistics        health, quality, genres, decades
  Duplicate Movies Report   same ID or title + year elsewhere
  Recompute Health Status   re-apply the rules, no rescan
  Save / Open Scan Results  a full scan to or from a file
  All-movies versions of Sync Ratings, Normalize Sources, Search
  Sources, Verify IDs, Normalize Genres, Auto Repair,
  Improvements Check and Health Report; Copy poster.jpg →
  folder.jpg; Delete extrafanart subfolders.

VERIFY IMDB/TMDB IDS
  Checks on TMDb that the IDs in the NFO/XML belong to the movie
  (any title language or alternative title, year ±1). Results:
  OK, IMDb and TMDb point to different films, ID belongs to
  another film, ID does not exist, NFO and XML disagree, no IDs.
  The report sorts by any column and saves to .txt or .csv.
  Nothing is written until you press Fix….

AUTO REPAIR
  Applies every safe fix in one go: IDs (exact title + year
  automatically, otherwise a chooser), ratings, genres, year,
  titles, XML language, IDs like "tt0133093/" and tags written
  twice. Artwork is never touched. A backup is made first and a
  summary lists fixed, skipped and still failing movies. "All
  Movies" offers a dry-run preview.
  •  Local title: when NFO <title> and XML <LocalTitle> differ,
     the side that is the original title, or that does not match
     the folder name, gets the other one. Otherwise the NFO title
     is kept (Settings → Health Rules can make it "skip and
     report"). Right-click → Metadata → "Make titles the same…"
     lets you choose for one movie.
  •  NFO named after the folder (Kodi does not read it): renamed
     to "<video>.nfo", or "movie.nfo" for a DVD / Blu-ray folder,
     a multi-part movie or several versions. Always the last step;
     the video itself is never renamed.

RENAME NFO FOR KODI
  Kodi reads "<video file name>.nfo" or "movie.nfo", not an NFO
  named after the folder. ⚠ Fix issues → "Rename NFO for Kodi…"
  offers both names (the recommended one selected); Tools →
  "Rename NFOs for Kodi — All Movies…" shows a preview first.
  movie.nfo: Kodi reads it when the source is set to "Movies are
  in separate folders that match the movie title"; Jellyfin and
  Emby always read it. A name that already exists is never
  overwritten. Backup History / Undo puts the old name back.

PREVIEWS
  Normalize Sources, Normalize Genres and Sync Ratings for all
  movies, and Copy poster.jpg → folder.jpg for several, first
  show what will change. Closing the preview writes nothing.
  Sync Ratings fetches the ratings first and then shows current
  → new for every movie.

EXPORT MOVIE LIST
  Tools → Export Movie List… (Export… button, Ctrl+Shift+E).
  •  Columns: Basic, Identify (links + outline), Standard, All, or
     your own choice.
  •  Rows: all movies or the current filtered view.
  •  Formats: CSV comma (default), CSV semicolon (Excel in
     CH/DE/PT/FR), tab-separated, plain list, Excel .xlsx.
"""

TAB_RATINGS = _title("Ratings & Genres") + """
RATINGS SYNC
  Fetches rating and votes from TMDb and/or OMDb (IMDb data) and
  writes them to the NFO (<rating>, <votes>, Kodi <ratings>) and
  the XML (<IMDBrating>, <Rating>, <Votes>, <VoteCount>).
  •  The dialog shows both sources side by side. A rating of 0 or
     0 votes counts as no data.
  •  Several movies: "Apply this choice to all remaining movies"
     or "Use the source with more votes" (equal votes → average)
     is remembered for the run.
  •  When both sources have no data, a second dialog asks once
     for typed values or Skip, with "Apply this choice to all
     remaining movies with zero votes and no rating".
  •  When TMDb or OMDb cannot be reached (network, rate limit,
     invalid key) the movie is skipped and listed at the end —
     it is never treated as "no rating".
  Defaults for the checkboxes: Settings → Ratings.

RATING AND VOTES ICONS
  ⬤   found, NFO and XML agree
  ◐   NFO and XML differ (conflict rule)
  ○   no tag found
  ✕   tag exists but is not a number

NORMALIZE GENRES
  Fixes genres in both files:
  •  capitalisation ("action" → "Action"), synonyms ("Sci-Fi" →
     "Science Fiction"), translations (PT, DE, FR, ES, IT, RU,
     ZH, AR), duplicates, merged tags ("Family/Fantasy").
  •  Copies the genres to the file that has none and converts
     <Genres>/<Genre> in an NFO to Kodi <genre> tags.
  •  Movies without genres in either file get them from TMDb
     (then OMDb); you see a preview before anything is written.
  Genres not in Settings → Genres are "custom": you choose to
  keep or delete them, or Right-click → Add Custom Genre(s).

SOURCE IDS
  Normalize Sources fills tags that are missing, lets you choose
  between conflicting IDs (titles looked up on TMDb) and asks for
  an ID where there is none ("Skip all remaining" in batches).
  When only one ID is known, every ID write (Normalize Sources,
  Apply, Enter ID…, Fix…, Auto Repair) leaves EMPTY tags for the
  other source, e.g. <tmdbid></tmdbid>, ready to fill in by hand.
  Existing values are never blanked.
  Settings → Health Rules decides how a missing ID is reported:
  "Movie with ONE source only (IMDb or TMDb)" and "Movie with NO
  source" can each be error, warning or off (not reported).
  Search Sources looks the movie up on TMDb by title + year (in
  English, in your library language and with the original title).
  Each movie shows the IDs its files hold now ("Current: …") and,
  as the first row, the film behind that ID. When the right film
  is not listed, "Enter ID…" lets you type its IMDb (tt…) or TMDb
  ID, shows title, year and poster, then writes both IDs.
  Films that are on IMDb but not on TMDb: the first row reads
  "IMDb tt… — not on TMDb" (with the OMDb title when an OMDb key
  is set). "Confirm IMDb" (or Enter ID… with that IMDb ID) writes
  the IMDb ID, leaves empty TMDb tags and marks the movie
  "OK (IMDb only — not on TMDb)", so Verify IDs and Auto Repair
  stop looking for it on TMDb.
"""

TAB_AUDIO = _title("Audio & Images") + """
AUDIO
  FFprobe audio tracks as LANGUAGE (CHANNELS); hover for codec and
  bitrate. Filled only by scans or updates that run FFprobe.
  FFprobe is always the primary source. A track it reports as UND
  (no language tag) takes the language from the NFO
  (<streamdetails><audio><language>, then <video><language>) or the
  XML (<Audio><Language>): matched by position, or used when only
  one language fits. Otherwise it stays UND. The tooltip then says
  e.g. "POR — from NFO (FFprobe: undefined)". Nothing is written.

SUBTITLES
  Embedded tracks (FFprobe) and external files in the folder.
  External files are recognised by the language suffix, e.g.
  Movie.pt.srt. Right-click → Subtitles… also opens for a movie
  without subtitles; "🌐 Open on OpenSubtitles.org" searches the
  movie there.
  Hard-coded (burned-in) subtitles are part of the picture and
  cannot be detected. Mark them with Right-click → Hard-coded
  subtitles… (one movie or a selection): tick the language(s) or
  type an ISO 639-2 code under "Other…". The app writes
  <tag>Hardsub POR</tag> to the NFO and <Tags><Tag>Hardsub
  POR</Tag></Tags> to the XML (other tags are kept); the column
  shows "Hard: POR", and Lang OK? and the "Required subtitle
  language" rule count it.

LANG OK?
  Y when the target language (Settings → Language) is found in an
  audio track, an embedded, external or hard-coded subtitle, XML
  <Language> / <LanguageCode> or NFO <language>.

BACKDROPS
  Extract Backdrop(s)    FFmpeg frames spread over the film
  Fetch Backdrops        pick TMDb / fanart.tv backdrops; replace
                         a file or save as a new backdropN.jpg
  Replace All Backdrops  choose the source and how many to
                         download (it starts at the number you
                         have now); the highest resolution comes
                         first and a failed download is replaced
                         by the next image. "Replace anyway" when
                         you would end up with fewer; backup
                         first.
  Health rules flag too few backdrops and very small ones.

FRAMES FROM THE MOVIE
  Fetch Fanart and Fetch Backdrops have a "🎞 Frames from movie"
  button (shown when FFmpeg is set and the movie has a video).
  •  10 frames from 10 %–90 % of the running time (no titles or
     end credits); black or flat frames are replaced by a nearby
     moment.
  •  "More frames" gives a new set.
  •  Use This / Replace / Download as New work as for online
     images; the frame keeps the video's resolution and is marked
     when it is below the fanart minimum quality.
  •  The frames are temporary files, deleted when the window
     closes.
  •  No TMDB ID needed: without one, Fetch Fanart and Fetch
     Backdrops open directly on the movie's frames (or fanart.tv
     by IMDb ID). Fetch Poster/Folder needs a TMDB ID, or an IMDb
     ID with a fanart.tv key. Replace All Backdrops needs a TMDB
     ID.

POSTER AND FANART
  Fetch Poster/Folder shows your image next to the TMDb posters;
  "Use This" downloads the full size to poster.jpg and folder.jpg
  after a backup. Fetch Fanart does the same for fanart.jpg.
  Copy poster.jpg → folder.jpg fixes folders that differ.
  The Fetch windows close with "Done" (or Esc): images applied
  before are kept. While a download runs, Done shows "Finishing…"
  and closes when it ends.

FANART.TV
  With a fanart.tv key (Settings → API Keys) the Fetch windows
  and Replace All Backdrops get a Source choice: TMDb, fanart.tv
  or Both (default Both; your choice is kept until you close the
  app). Each image shows its source, size and, for fanart.tv,
  its likes and language.
  •  Posters: your library language first (Settings → Language),
     then images without text, then English.
  •  Backdrops: fanart.tv backgrounds (1920×1080); tick "include
     landscape thumbs" for the smaller 1000×562 ones.
  •  fanart.tv gives no pixel size: "~1920×1080" is its usual
     size. The real size is checked after the download.
  •  The movie is found by TMDb ID, then by IMDb ID.
  •  Answers are kept 7 days in fanarttv_cache.json.
  Replace All Backdrops shows the count of each source and of
  both, and warns when the chosen one has fewer than you have.
  The optional VIP client key gets newer images sooner.

FIXING IMAGE PROPORTIONS AND SIZE
  Right-click → Images → Fix image proportions / size… fixes a
  poster, folder image or fanart with wrong proportions or a low
  resolution. The window shows the image before and after.
  •  Method: Blur fill keeps the whole image and fills the empty
     bands with a blurred copy (posters); Smart crop keeps the
     most detailed part (fanart); Centre crop; Solid fill. A
     deviation up to 3 % is simply stretched.
  •  Size: the quality tier nearest to the image (for example a
     700×1000 poster → 720p 666×1000). Each size shows its factor
     and a mark: ✓ recommended, ⚠ not recommended (soft), ✕ too
     far from the original (not offered). "Keep current size"
     fixes the proportions only.
  •  Upscaling cannot recover detail that is not in the original.
     Small enlargements are fine; large ones look soft (plain) or
     artificial (AI). For a much bigger image, use "Find a better
     one online" (it opens Fetch Poster/Folder or Fetch Fanart).
  •  AI upscale (optional): "Download upscaler (about 45 MB)…"
     installs Real-ESRGAN (checked against its SHA-256) and tests
     it once. Without a usable Vulkan graphics card it stays off
     ("Test again" retries). With it, ×2 is recommended and up to
     ×4 is allowed — always check the preview: AI may invent
     detail and smooth text and faces.
  The file found is overwritten in its own format (JPEG or PNG);
  a .webp / .gif / .bmp becomes the .jpg of the same name.
  •  "Also copy the result to folder.jpg" (poster) or "… to
     poster.jpg" (folder image), ticked by default: the fixed
     image is written as both files, so they stay the same
     picture. Untick it to change only the chosen file. Every
     file is backed up first (Backup History / Undo restores both).
  Several movies, or Tools → Fix Image Proportions / Size — All
  Movies: a preview lists every image and its fix; only ✓ sizes
  are used, the others are listed as skipped. A folder.jpg that
  needs a fix too gets the fixed poster ("+ copied to folder.jpg").
  •  While Apply runs you can minimise the window and keep
     working; when it ends the status bar says so, the taskbar
     button flashes and the result pop-up appears.
     "■ Stop" stops it (nothing changes).
  •  AI speed "gentle" (default) uses small tiles and the lowest
     priority, so the PC stays usable; "fast" uses everything. An
     upscaler that stops responding is stopped after 30 s and the
     plain resize is used.

KODI NAMING
  MediaClinic reads every name Kodi uses and shows the file Kodi
  would pick (Kodi's order):
  •  Poster: <video>-poster.jpg/.png, poster.jpg/.png,
     <video>.tbn, movie.tbn
  •  Fanart: <video>-fanart.jpg/.png, fanart.jpg/.png
  •  NFO: movie.nfo, <video>.nfo (and <folder>.nfo)
  •  Extra fanart counts as backdrops: fanart1.jpg…,
     <video>-fanart1.jpg…, the extrafanart folder
  <video> is the file name of the movie without its extension,
  as Kodi's library export writes it. The poster and fanart
  tooltips say which file was found. Fetch Poster/Folder, Fetch
  Fanart and Copy poster → folder write in the style the folder
  already uses: a Kodi folder gets <video>-poster.jpg, and no
  folder.jpg unless one exists. A .png is replaced by the .jpg of
  the same name (backed up first).
  New backdrops (Extract Backdrop(s), Fetch Backdrops, Replace All
  Backdrops) follow the same rule: <video>-fanart1.jpg, -fanart2…
  in a Kodi folder, backdrop.jpg, backdrop1.jpg… otherwise.
  DVD and Blu-ray folders: a VIDEO_TS (VIDEO_TS.IFO) or BDMV
  (index.bdmv) structure is the movie. Kodi's names next to it
  are read too: VIDEO_TS-poster.jpg, VIDEO_TS.nfo, index-poster.jpg,
  index.nfo, and poster.jpg / movie.nfo in the movie folder.
  FFprobe and frames use the largest .VOB / .m2ts file.
  Health Rules: "folder.jpg optional when a Kodi poster exists"
  and "NFO named after the folder, not read by Kodi" (both ON).

JELLYFIN, EMBY AND PLEX NAMES
  The names the other servers read are found too, after Kodi's:
  •  Poster: <video>.jpg, cover, default, movie, <video>-cover…
  •  Fanart: backdrop, background, art
  •  Extra backdrops: backdrop-1, fanart-1, background-1, art-1
  •  Pictures: .jpg, .png, .jpeg, .webp, .gif, .bmp
  The poster, folder and fanart tooltips say which servers read
  the file that was found. folder.jpg alone counts as the poster
  (all four servers use it); the rule "also when folder.jpg
  exists" (OFF) warns anyway.
  NFO: movie.nfo is read first. Two NFOs the servers read (e.g.
  movie.nfo and <video>.nfo) are a warning: delete the one you do
  not need. mymovies.xml is shown in the XML tooltip: no current
  server reads it.
  Other videos are not "Multiple video files": trailers
  (-trailer), samples, extras (-featurette, -deleted …), the parts
  of a stack (cd1, part2) and versions ("Movie - 1080p"). The
  Video tooltip lists them. Subtitle flags (forced, SDH) and the
  Subs folder next to the video are read.

PROPORTIONS
  Poster and folder 2:3 (3:4 optional), fanart 16:9 (16:8
  optional). Wrong proportions are warnings.

SORTING
  See Table & Columns → Sorting: up to three levels, every
  column, presets and heading clicks.
"""

TAB_SETTINGS = _title("Settings") + """
TOOLS
  Text editor, FFmpeg folder (Test FFmpeg), backdrop frame count,
  parallel scanning (workers, default 6; FFprobe processes,
  default 2), metadata source, optional scraper.
  "Remember FFprobe results" (ON): each video is probed once
  (one ffprobe call gives resolution, audio and subtitles) and
  the result is kept in ffprobe_cache.json next to settings.json.
  A scan with FFprobe of an unchanged video does not probe it
  again; a changed video (size or date) is probed again, and
  Update (with FFprobe) always probes.

API KEYS
  TMDb and OMDb keys with Validate buttons and links to get them.
  All online calls share one client with a rate limit and
  automatic retries.

BROWSER
  Browser for web links. Changing it never asks for a rescan.

LANGUAGE
  ISO 639-1 code for the Lang OK? column (default PT).

IMPROVEMENTS
  Checks of the Improvements report and the NFO/XML maximum
  sizes (also used by the "too large" health rule).

IMAGE SIZES
  Minimum quality tier (same value as Health Rules), 3:4 and 16:8
  acceptance, minimum file sizes in KB. Applied to the table at
  once, without a rescan.

RATINGS
  Defaults of the two checkboxes of the Ratings Sync dialog.

GENRES
  The standard genre list, one per line. Others are custom.

NFO / XML
  Tag pairs compared by the Improvements Check.

USER INTERFACE
  Alternating row colours, header tooltips, compact mode, the
  Repeat line of the right-click menu, whether the Ignored
  folders window opens after a scan, and dark title bars (on by
  default; applied to the open windows when you save).

HEALTH RULES
  Every condition that can turn a row red (errors) or yellow
  (warnings) has a checkbox; some have a level or threshold.
  Save & Apply recomputes the health at once. "Reset to
  defaults" restores the shipped rules.
  "Missing folder image" and "Poster and folder image are
  different" are off by default: Kodi, Jellyfin, Emby and Plex
  all show poster.jpg without a folder.jpg. Turn them on if you
  want them.
  "NFO has an unescaped '&'": Kodi reads such an NFO, but
  Jellyfin may ignore the whole file. Auto Repair writes '&amp;'
  (a backup is made first).
  Content checks of the NFO / XML: IDs that are not valid, a
  year out of range, a runtime / votes that is not a number or a
  rating above 10, a tag written twice, an empty <title> / <plot>
  (off by default) and an unexpected root element.
  "Title mismatch" names both local titles; "↳ When Repair All
  cannot tell the right local title" chooses what Auto Repair
  does then.

BACKUP
  Maximum backup folder size (oldest deleted first, 0 =
  unlimited), "Delete the oldest backups automatically" (on by
  default) and a button to delete all backups.

SAVE & APPLY
  Writes settings.json. Language, Genres or NFO/XML tag changes
  offer an Update Scan; health rule and Image Sizes changes apply
  at once. A blank number field is saved as its default.
"""

TAB_SHORTCUTS = _title("Shortcuts") + """
UPDATES
  Help → Check for updates… (or the button in About) asks GitHub
  for the latest release; nothing else is sent. A new version
  can be opened on GitHub or skipped. The Windows exe can also
  download and install it: the package is checked against its
  SHA-256 and unpacked next to the current version, which is
  never changed; then the new version can be started. Your
  settings, results and backups are kept (they live in
  %APPDATA%). Settings → User Interface → "Check for updates at
  start" (off by default) checks once a day and only shows a
  link in the status bar.

MENUS
  Settings ▾, Tools ▾ and Help ▾ at the top of the window open
  the menus. Keyboard: Alt+S, Alt+T, Alt+H; F10 opens Settings;
  Esc closes a menu.

KEYBOARD
  F1, Ctrl+H          Help
  F5                  Full Scan
  Esc                 cancel a scan; clear the Filter box; close a
                      window (Settings asks first if you changed
                      something)
  Ctrl+F              go to the Filter box
  Ctrl+L              clear all results
  Ctrl+S              Settings
  Ctrl+O              open the selected movie's folder
  Ctrl+E              open the selected movie's .nfo
  Ctrl+R              Update selected movie (no FFprobe)
  Ctrl+Shift+R        Update selected movie (with FFprobe)
  Ctrl+I              refresh all icons
  Ctrl+Shift+E        Export Movie List…
  Ctrl+1 … Ctrl+9     sort presets 1 to 9
  Shift+click heading add a sort level

SELECTION
  A–Z, 0–9            jump to the next movie with that letter
                      (repeat to cycle)
  PageUp, PageDown    move one page; Home / End: first / last
  Shift+Up/Down       extend or shrink the selection
  Shift+PageUp/Down   extend by one page
  Shift+Home/End      extend to the first / last row
  Ctrl+A              select all visible (filtered) movies; in the
                      Filter box it selects the text
  With more than one movie selected the status bar shows
  "N selected".
  Double-click        action of the column (Actions & Tools)
  Right-click         menu for the selected movie(s)
  Shift+F10, Menu key the same menu, at the selected row

TROUBLESHOOTING
  Audio column is empty
      Tick FFprobe and run Update (with FFprobe).
  A health reason no longer applies
      Tools → Recompute Health Status (also done at every start).
  Source shows ✕ although the movie has an ID
      Some tags are empty, e.g. <TMDB></TMDB>, while others
      hold the ID; Normalize Sources fills them.
  Ratings Sync skipped movies that "could not be reached"
      TMDb/OMDb were offline, rate limited or the key is
      invalid; run it again later. Details are in logs/app.log.
  When TMDb or OMDb do not answer
      IMDb is never asked directly: IMDb ratings come through
      OMDb, IMDb IDs through TMDb. The message names the cause
      and what to do. TMDb "too many requests": wait about a
      minute. OMDb daily limit (1,000 requests on a free key):
      try again in a few hours or tomorrow; TMDb still works.
      Key rejected: Settings → API Keys → Validate. No
      connection / not responding: check the internet, try
      again in a few minutes.
      In a batch the message comes once, with "Pause this run",
      "Continue with the other source" and "Cancel". After a rate
      limit, a daily limit or repeated server errors the service
      is paused: the status bar shows "⚠ … paused" (click it to
      see why or to end the pause), the next action asks "Try
      anyway?", and the pause is kept when you restart.
  Backdrop extraction makes no files
      Check FFmpeg in Settings → Tools; raise the frame timeout.
  Excel opens the CSV in one column
      Export with "CSV — semicolon separated" or as .xlsx.
"""

# (menu / tab label, text) in display order.  The About tab is built by the
# main script and always comes last.
HELP_TABS = [
    ("🚀  Getting Started",   TAB_START),
    ("📊  Table & Columns",   TAB_TABLE),
    ("🔄  Scans & Libraries", TAB_SCANS),
    ("🖱  Actions & Tools",   TAB_ACTIONS),
    ("⭐  Ratings & Genres",  TAB_RATINGS),
    ("🎵  Audio & Images",    TAB_AUDIO),
    ("⚙️  Settings",          TAB_SETTINGS),
    ("⌨  Shortcuts",          TAB_SHORTCUTS),
]
ABOUT_LABEL = "ℹ️  About"
