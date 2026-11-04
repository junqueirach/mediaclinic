# =============================================================================
# help_text.py
# Metadata & MediaClinic — Help contents (structure markup, pure text)
# Version: 0.19.4                                              ### REWRITTEN v0.19.4 B74 ###
# Author:  Luiz Junqueira & Claude AI
#
# v0.19.4 B74 — the Help is written as STRUCTURE, not as pre-formatted text.
# Every paragraph and every bullet is ONE logical line (no hard line breaks):
# the Help window reflows it to its width.  The renderer (HelpDialog in the
# main script) does all indentation and alignment with Tk tag margins.
#
# Markup (one block per line; blank lines only separate blocks):
#   # Title                  the tab's heading (first line of every tab)
#   ## Section               a section heading
#   ### Sub-section          a smaller heading
#   - text                   bullet            -- text   second-level bullet
#   1. text                  numbered step (any number)
#   | key | description      a table row (rows in a row form one table)
#   > text                   a note            >! text   a warning
#   any other line           a paragraph
# Inline: **App label** (a menu entry, button or setting) and [[Ctrl+R]] (a key).
#
# HELP_TABS gives the tab order used by BOTH the Help window and the Help menu.
# The B10 fixed-width rules (72 characters, space indents) are retired.
# =============================================================================
import re

_BLOCK_RE = re.compile(r"^(#{1,3} |-- |- |\d+\. |\| |>! |> )")
_INLINE_RE = re.compile(r"\*\*(.+?)\*\*|\[\[(.+?)\]\]")


def parse(text):
    """[(kind, level, text, extra)] for one tab.  kind: title, h2, h3, p, bullet (level 1/2), step (extra=number),
    row (text=key, extra=description), note, warn."""
    out = []
    for raw in (text or "").splitlines():
        ln = raw.rstrip()
        if not ln.strip():
            continue
        if ln.startswith("### "):
            out.append(("h3", 0, ln[4:].strip(), None))
        elif ln.startswith("## "):
            out.append(("h2", 0, ln[3:].strip(), None))
        elif ln.startswith("# "):
            out.append(("title", 0, ln[2:].strip(), None))
        elif ln.startswith("-- "):
            out.append(("bullet", 2, ln[3:].strip(), None))
        elif ln.startswith("- "):
            out.append(("bullet", 1, ln[2:].strip(), None))
        elif ln.startswith("| "):
            parts = [p.strip() for p in ln[2:].split(" | ", 1)]
            out.append(("row", 0, parts[0], parts[1] if len(parts) > 1 else ""))
        elif ln.startswith(">! "):
            out.append(("warn", 0, ln[3:].strip(), None))
        elif ln.startswith("> "):
            out.append(("note", 0, ln[2:].strip(), None))
        else:
            m = re.match(r"^(\d+)\. (.*)$", ln)
            if m:
                out.append(("step", 0, m.group(2).strip(), m.group(1)))
            else:
                out.append(("p", 0, ln.strip(), None))
    return out


def inline(text):
    """[(segment, style)] with style None, "label" (**…**) or "key" ([[…]])."""
    out, pos = [], 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], None))
        out.append((m.group(1), "label") if m.group(1) is not None else (m.group(2), "key"))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], None))
    return out


def plain(text):
    """The text as the reader sees it (markup removed) — for searches and the coverage test."""
    out = []
    for kind, _lv, t, extra in parse(text):
        out.append("".join(s for s, _st in inline(t)))
        if kind == "row" and extra:
            out.append("".join(s for s, _st in inline(extra)))
    return "\n".join(out)


def format_errors(text):
    """Problems of one tab's markup: no title first, indented lines (indents come from the renderer, never from
    spaces), the old layout's markers, an unclosed ** or [[."""
    errs = []
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    if not lines or not lines[0].startswith("# "):
        errs.append("the tab does not start with its '# Title'")
    for ln in lines:
        if ln != ln.lstrip():
            errs.append(f"indented with spaces: {ln[:50]!r}")
        if ln.lstrip().startswith(("•", "─", "===")):
            errs.append(f"old layout marker: {ln[:50]!r}")
        if ln.count("**") % 2 or ln.count("[[") != ln.count("]]"):
            errs.append(f"unclosed ** or [[: {ln[:50]!r}")
        if ln.startswith("|") and not ln.startswith("| "):
            errs.append(f"table row without '| ': {ln[:50]!r}")
    return errs


TAB_START = """
# Getting Started

## What this app does
Metadata & MediaClinic audits and repairs Kodi, Jellyfin, Emby and Plex movie libraries. It scans your library folders, checks every artwork file, metadata file and video, and shows a colour-coded health table, so you see at a glance what is missing or broken. Most problems can be fixed from the same table.

## How a movie folder looks
One folder = one movie. A complete folder holds:
- the video, e.g. **Movie Name (2001).mkv** (or .mp4, .avi …)
- the Kodi metadata, **<video>.nfo** or **movie.nfo**
- **movie.xml**, the Emby / Jellyfin metadata (optional)
- **poster.jpg** (portrait, 2:3) and **fanart.jpg** (wide, 16:9)
- **folder.jpg**, an identical copy of the poster (optional: every server reads poster.jpg)
- extra backgrounds: **backdrop.jpg**, **backdrop1.jpg** … or Kodi's **<video>-fanart1.jpg** …
- external subtitles such as **Movie Name.pt.srt** (optional)
The Media Servers tab lists every name the servers read.

## First run
1. Click **Browse…** and choose your movie folder. Add more folders later with **Libraries…**.
2. Click **Full Scan** ([[F5]]). The table fills in phases: folders, images, metadata, then video — with FFprobe when the **FFprobe** switch in the status bar is On.
3. Each row shows the health of one movie: green = no rule triggered, yellow = warnings, red = errors.
4. Select a movie: the panel on the right shows its poster, its issues with a **Fix** button each, its files and the common actions.
5. The last scan is saved and restored at the next start.

## Quick-start checklist
- **Settings → Editor & FFmpeg**: set the FFmpeg folder (video analysis and backdrop extraction).
- **Settings → API Keys**: add the TMDB and OMDb keys (ratings, ID search and checks, artwork); a fanart.tv key adds more posters and backdrops.
- **Settings → Language**: the target language of the Language column (default PT).
- **Settings → Health Rules**: choose what counts as an error or a warning.
- To triage: sort by **Health** (Errors first), click the **Errors** counter, or tick **Problems only**.

## Status icons
| ⬤ | OK — present and valid
| ◐ | warning — conflict, wrong proportions, a minor issue
| ○ | missing
| ✕ | error — corrupt image, XML error, unreadable value

## Files the app writes
| settings.json | all settings (%APPDATA%\\MediaMetadataClinic)
| last_results.json | the last scan, restored at the start (same folder)
| ffprobe_cache.json | remembered FFprobe results (same folder)
| fanarttv_cache.json | fanart.tv answers, kept 7 days (no key inside)
| collections_cache.json | the TMDB collections (names in every language)
| not_duplicates.json | your "Not a duplicate" answers
| no_collection.json | the movies you marked "not in a collection"
| backup_cleanup_log.json | the backup runs the size cleanup removed (Backup History lists them)
| logs/app.log | the log next to the program; API keys are never written to it (**Help → Open Logs Folder**)
| backup/ | the automatic backups (same folder; moved there from the program folder once — an update keeps them)
"""

TAB_WINDOW = """
# The Window & Table

## The window
- **The header** (top): the **Movies** and **Series** parts, **Backup History / Undo…**, **Settings ▾**, **Help ▾** and **About**. Series support comes in v0.22; the Series part shows what is planned and the folders the last scan did not add.
- **The Movies toolbar**: **Libraries…**, **Browse…**, the library box, **Full Scan**, **Quick Scan**, **Tools ▾**, **Export…** and **•••** (**Clear All…**, **Save Scan Results…**, **Open Scan Results…**).
- **The sort row**, the **Filter** box and the colour legend, then the table.
- **The selected-movie panel** on the right of the table (next section).
- **The status bar** (bottom): the counters (click **Errors** or **Warnings** to show only those rows), the selection count, the last action, and the **FFmpeg ✓ | FFprobe** switch.

## The selected-movie panel
Select one movie and the panel shows its poster, year, genres, rating, library and a health badge; then **ISSUES** (every health reason), **FIXES** (each fixable problem with its **Fix** button), **FILES** (NFO, XML, poster, folder, fanart, video: ✓ or ✕) and **ACTIONS** (**Open Folder**, **Edit NFO**, **Fetch Poster…**, **Search Sources**, **Update**). **All actions ▾** opens the full right-click menu.
- Several movies selected: "N movies selected", the actions that work on several, and the fixes with how many movies have each problem.
- A collection row (grouped view) shows the collection panel (Collections tab).
- **Hide ›** or [[Ctrl+B]] hides the panel; the slim **‹** strip at the right edge shows it again. Drag the divider to change its width; a double-click on the divider resets it. Both are remembered.

## Columns
| Movie Name | NFO <title>, then XML <LocalTitle>, original titles, the folder name. Hover: the folder, its library, the date added and every health reason. Double-click opens the folder.
| Year | NFO <year> or XML <ProductionYear>.
| Genres | NFO <genre> tags; when the NFO has none, the XML <Genres> (the tooltip names the source).
| Rating | NFO <rating> (or Kodi's <ratings> block), XML <IMDBrating> / <Rating>. Hover: value, votes, source.
| Votes | NFO <votes>, XML <Votes> / <VoteCount>.
| Source | the IMDb and TMDB IDs of every tag: ⬤ all agree, ◐ partial or conflict, ○ missing, ✕ some tags filled and some empty. Hover shows the last Verify IDs result; double-click opens IMDb or TMDB.
| Poster, Folder, Fanart | status and quality tier of each image (Images tab).
| Backdrops | the number of backdrop images; hover: their average size.
| .nfo / .xml | the metadata file status. Hover lists the errors with the line and the tag names (the first 5); double-click opens the file in your editor.
| Language | XML <Language>.
| Video, Video Size, Quality | container, size and resolution class.
| Audio | FFprobe audio tracks, e.g. EN (5.1), PT (2.0).
| Language OK | Y / N: the target language in audio or subtitles (the heading shows the code, e.g. "PT OK?").
| Subtitles | embedded tracks (FFprobe) and external files.
| Library | the library (root folder). Hidden by default.
| Collection | the movie's collection (NFO <set>). Hidden by default.
**Tools → Choose Columns…** shows or hides columns; the choice is kept. Drag a heading edge to resize a column, double-click a heading to fit it, or use **↔ Auto-size Columns**. **↺ Default Widths** puts every column back to its original width after a resize went wrong. In the grouped view the Year column widens for a collection's years ("1979–1986") and gets your width back when you ungroup. Widths, window sizes and positions are remembered.

## Filter
Type in the **Filter** box ([[Ctrl+F]]) to keep the movies whose name, year, genre, language, quality, health status, health reason or collection matches — "backdrops" lists every backdrop issue. [[Esc]] clears it.
- **Problems only** hides the green rows.
- The library box next to **Libraries…** shows one library or all of them.
- "n of m shown" counts the movies the filter keeps.

## Sorting
The sort row reads "Sort by [column] [direction]"; **+ then by** adds up to two more levels (✕ removes one). The direction is said in words — A → Z, Newest first, High → low, Worst first, Errors first … — click it to turn it round.
- Every column can be used, plus **Health** and **Number of issues** (the first two entries) and **Date added** (NFO <dateadded>, XML <DateAdded>, else the creation date of the video or the folder).
- Click a column heading to sort by it (again = reversed); Shift+click adds it as the next level. ▲1 / ▼2 in the headings show the levels.
- Empty values (no rating, no poster, no date) always go last; equal values stay in Movie Name order.
- **★ Presets ▾**: Problems first, Worst artwork first, Missing metadata, Best rated, Biggest files, By library, By collection name (collection A → Z, then year, then movie name; movies without a collection last), and your own (**Save current sort as preset…**; rename or delete them in the same menu). [[Ctrl+1]] … [[Ctrl+9]] apply presets 1 to 9.
- **↺ Update View** sorts and filters again, so movies you just fixed move to their place.
- The sort is kept after a scan and after a restart.

## Duplicates
Movies that share an IMDb ID, a TMDB ID, or a title + year are a "Possible duplicate" (the same title + year with two different IMDb IDs are not: a remake or a namesake). Right-click → **✔ Not a duplicate…** remembers your answer in not_duplicates.json, so the warning stays gone; a new third copy is still found. **↺ Undo 'not a duplicate'** takes it back; **Tools → Manage 'Not a duplicate' marks…** lists every pair. **Tools → Duplicate Movies Report** lists them all.
"""

TAB_SCANS = """
# Scans & Libraries

## Scans
| Full Scan | re-reads every movie of the libraries in scope ([[F5]]).
| Quick Scan | reads only the movies that were added, removed or changed since the last scan (a changed NFO, image, subtitle or disc folder counts).
| FFprobe switch | in the status bar: when On, scans also read the video resolution, the audio tracks and the embedded subtitles. A scan without FFprobe keeps the previous FFprobe data.
| Cancel / Esc | stops a running scan; the movies read so far are kept.
A scan never writes to your files. While it runs, the actions that change files wait for it (the status bar says so).

## Libraries
You can scan several root folders. **Browse…** adds one folder; **Libraries…** adds, removes and orders them. After the list changes the app offers Full Scan, Quick Scan or Not now.
- All libraries share one table; the **Library** column and the Movie Name tooltip show where a movie lives.
- The library box chooses what the table shows and what the scans cover ("All libraries" or one of them).
- A library that cannot be reached (an unplugged network share) keeps its last scan, is skipped by scans and is shown as "(offline)". A movie folder that cannot be read for a moment keeps its row, marked "(not read)".
- Duplicates are found across libraries.

## Ignored folders
A scan adds a row only for movie folders. These are not added:
- TV series: tvshow.nfo, Season folders or episode files (S01E02, 1x02). Series support comes in v0.22.
- Folders holding other movie folders: the library is one level too high; add the inner folders as libraries.
- Folders with several separate videos: give each movie its own folder.
- Folders with no video, NFO or XML, system folders ($RECYCLE.BIN, @eaDir …) and folders that could not be read.
A folder with movie metadata is always a movie, and so is a folder with one video and no NFO. After a scan the **Ignored Folders of the Last Scan…** window opens when something was left out (filter, sort, double-click to open, **Export to TXT…**, **Copy All**); turn that off with "Show this window after a scan". **Tools → Ignored Folders of the Last Scan…** opens it at any time.

## Updating single movies
Right-click → **Update (no FFprobe)** ([[Ctrl+R]]) re-reads the movie or the selection; **Update (with FFprobe)** ([[Ctrl+Shift+R]]) also probes the video (one movie: a status line; several: a progress window with Cancel). After every repair, sync, fetch or delete the affected rows refresh by themselves.

## Movies that disappear
When a movie folder was deleted, Update or the automatic refresh removes its row. Right-click → **Remove from list** drops rows without touching any file; the next scan brings back movies that still exist.

## Saving and loading scans
- The last scan is saved in last_results.json and loaded in the background at the start ("⏳ Loading last scan…"); the health rules are applied again, so changed rules never leave old reasons behind.
- **••• → Save Scan Results…** / **Open Scan Results…** write a scan to a file or load one.
- **••• → Clear All…** ([[Ctrl+L]]) empties the table (it asks first; nothing on disk changes).
"""

TAB_HEALTH = """
# Health & Fixing Issues

## How health works
Every condition that can turn a row red (errors) or yellow (warnings) is a rule in **Settings → Health Rules**, with a checkbox and sometimes a level or a threshold. **Tools → Recompute Health Status (no rescan)** applies changed rules at once (also done at every start).
- Hover the Movie Name for every reason of a movie; the selected-movie panel lists them too.
- **Tools → Health Status Report — All Movies** writes them all, with the most common issues first and the movies whose collection was not checked online.
- **Tools → Run Improvements Check — All Movies…** lists metadata that could be better (tag pairs of **Settings → NFO / XML**, file sizes).
- **Tools → Library Statistics**: health, quality, genres, decades, libraries.

## Fix issues
The right-click menu starts with the movie's name (or "N movies selected") and its number of issues, then **⚠ Fix issues**: the real problems of the selection, each linked to the action that fixes it — with several movies, how many movies have each problem (the action runs on just those). The selected-movie panel has the same list as **Fix** buttons.
| Poster / folder image missing | Fetch Poster/Folder…
| Fanart missing | Fetch Fanart…
| Too few / small backdrops | Fetch Backdrops…
| Image proportions / size | Fix Image Proportions / Size…
| folder.jpg differs from the poster | Copy poster.jpg → folder.jpg
| NFO / XML errors | show the errors (every error with its line)
| Local title differs (NFO ↔ XML) | Make titles the same…
| Collection missing / different | Fix Collection… (Collections tab)
| Collection folder / artwork missing | Collection Artwork… (one collection) or Create Collection Folder… (several)
| Possible duplicate | Not a duplicate…
| Video quality below minimum | needs a better copy of the video (no automatic fix)
| NFO named after the folder | Rename NFO for Kodi…
| IMDb / TMDB ID missing | Search Sources…
| IDs in one file only / conflicting | Normalize Sources
| IDs not verified / wrong movie | Verify IMDb/TMDB IDs
| Rating / votes missing or wrong | Sync Ratings
| Audio track / language | Subtitles…
| Subtitle language missing | Hard-coded subtitles…
| Auto Repair can fix more | Auto Repair

## The right-click menu
Also [[Shift+F10]] or the Menu key, at the selected row. An action that does not apply stays in its place, greyed, with the reason ("missing", "one movie only" …).
- **Repeat**: the last action again on the current selection (Settings → User Interface can hide this line).
- **Open Folder** ([[Ctrl+O]]), **Play Video**, **Edit NFO** ([[Ctrl+E]]).
- **Artwork**: open the images — the entry names the file found, e.g. **Open poster.jpg**, **Open folder.jpg**, **Open fanart.jpg** (greyed **Open poster** when there is none or several movies are selected); **Fetch Poster/Folder**, **Fetch Fanart**, **Fetch Backdrops**, **Replace All Backdrops**, **Extract Backdrop(s)**, **Copy poster.jpg → folder.jpg**, **Fix Image Proportions / Size…**.
- **Metadata**: **Open .nfo**, **Open movie.xml**, **[!] NFO errors** / **[!] XML errors**, **Make titles the same (NFO ↔ XML)…**, **Rename NFO for Kodi…**, **Collection ▸**, **Sync Ratings from IMDb / TMDB**, **Normalize Genres**, **Add Custom Genre(s) to Settings**.
- **IDs & Sources**: **Search Sources**, **Verify IMDb/TMDB IDs**, **Normalize Sources**, **Copy Movie Name**.
- **Video & Subtitles**: **Subtitles…**, **Hard-coded subtitles…**.
- **Open online**: **Open on IMDb**, **Open on TMDB**, **Open on Fanart.tv**, **Open on OpenSubtitles.org**, **Open in Scraper**.
- **Check & Repair**: **Health Status Report**, **Run Improvements Check**, **Auto Repair**.
- **Update**: **Update (no FFprobe)**, **Update (with FFprobe)**; **Remove from list**.
Several movies: select with Ctrl+click, Shift+click, Shift+arrows or Shift+PageUp / PageDown / Home / End. The same menu runs the batch versions; longer runs show a progress window with Cancel.

## Double-click
| Movie Name | the movie folder
| Genres, Rating, Votes | the .nfo file in your editor
| Source | choose the IMDb or TMDB page
| Poster, Folder, Fanart | the image in your viewer
| Backdrops | the first backdrop
| .nfo / .xml | the file in your editor (also when it has errors)
| Language | movie.xml in your editor
| Video, Quality | plays the video
| Subtitles | the subtitle tracks
| Library | the library folder
| Collection | the .nfo file in your editor

## Health rules worth knowing
- "Missing folder image" and "Poster and folder image are different" are off by default: every server shows poster.jpg without a folder.jpg.
- "NFO has an unescaped '&'": Kodi reads such an NFO, but Jellyfin may ignore the whole file. Auto Repair writes '&amp;'.
- Content checks: IDs that are not valid, a year out of range, a runtime or votes that is not a number, a rating above 10, a tag written twice, an empty <title> / <plot> (off by default).
- "Title mismatch" names both local titles; "When Repair All cannot tell the right local title" chooses what Auto Repair does then.
- A missing ID: "Movie with ONE source only" and "Movie with NO source" can each be an error, a warning or off.
"""

TAB_IMAGES = """
# Images

## Poster, folder and fanart
**Fetch Poster/Folder…** shows your image next to the TMDB (and fanart.tv) posters; **Use This** downloads the full size to the poster (and folder.jpg when the folder uses one) after a backup. **Fetch Fanart…** does the same for the fanart. **Copy poster.jpg → folder.jpg** fixes folders whose folder.jpg differs; **Tools → Copy poster.jpg → folder.jpg — All Movies with Differences…** shows a preview first.
- A download is checked before it replaces anything: a page that is not a picture, or a picture cut off, never replaces a good file.
- The Fetch windows close with **Done** (or [[Esc]]); images applied before are kept. While a download runs, Done shows "Finishing…".

## Quality tiers
| Poster / Folder (2:3) | 4K 2000×3000 · 1440p 1500×2250 · 1080p 1000×1500 · 720p 666×1000 · 540p 540×810 · 480p 480×720 · 360p
| Fanart (16:9) | 4K 3840×2160 · 1440p 2560×1440 · 1080p 1920×1080 · 720p 1280×720 · 540p 960×540 · 480p 854×480 · 360p
±5 % tolerance. The minimum tier is one setting (Settings → Health Rules and Settings → Image Sizes); images below it are warnings. Proportions: poster and folder 2:3 (3:4 optional), fanart 16:9 (16:8 optional). "Corrupt" (✕) means the file cannot be decoded: no JPEG / PNG signature, cut-off data or 0 bytes. A PNG named poster.jpg is read and gets an "extension mismatch" warning.

## Backdrops
| Extract Backdrop(s) | FFmpeg frames spread over the film
| Fetch Backdrops | pick TMDB / fanart.tv backdrops; replace a file or save a new one
| Replace All Backdrops | choose the source and how many (it starts at the number you have); the highest resolution first, a failed download is replaced by the next image; a backup first
**Tools → Delete extrafanart Subfolders — All Movies…** removes Kodi's old extrafanart folders (a backup first). The health rules flag too few backdrops and very small ones.

## Frames from the movie
Fetch Fanart and Fetch Backdrops have a **🎞 Frames from movie** button (with FFmpeg set and a video in the folder).
- 10 frames from 10 %–90 % of the running time; black or flat frames are replaced by a nearby moment. **More frames** gives a new set.
- The frames keep the video's resolution and are marked when they are below the fanart minimum. They are temporary files, deleted when the window closes.
- No TMDB ID needed: without one, Fetch Fanart and Fetch Backdrops open on the movie's frames (or fanart.tv by IMDb ID).

## fanart.tv
With a fanart.tv key (Settings → API Keys) the Fetch windows and Replace All Backdrops get a **Source** choice: TMDB, fanart.tv or Both.
- Posters: your library language first, then images without text, then English.
- Backdrops: fanart.tv backgrounds (1920×1080); tick "include landscape thumbs" for the 1000×562 ones.
- fanart.tv gives no pixel size: "~1920×1080" is its usual size; the real size is checked after the download. Answers are kept 7 days.

## Fixing proportions and size
Right-click → Artwork → **Fix Image Proportions / Size…** fixes a poster, folder image or fanart with wrong proportions or a low resolution, with a before / after view.
- **Method**: Blur fill keeps the whole image and fills the empty bands with a blurred copy (posters); Smart crop keeps the most detailed part (fanart); Centre crop; Solid fill. Up to 3 % is simply stretched.
- **Size**: the tier nearest to the image, with its factor and a mark — ✓ recommended, ⚠ soft, ✕ too far (not offered). "Keep current size" fixes the proportions only. For a much bigger image use **Find a better one online**.
- **AI upscale** (optional): **Download upscaler (about 45 MB)…** installs Real-ESRGAN (checked against its SHA-256) and tests it once; it needs a Vulkan graphics card. ×2 is recommended, up to ×4 allowed — check the preview: AI may invent detail.
- "Also copy the result to folder.jpg" (ticked by default) keeps poster and folder the same picture. Every file is backed up first.
- Several movies, or **Tools → Fix Image Proportions / Size — All Movies with Image Warnings…**: a preview lists every image and its fix; only ✓ sizes are used. You can minimise the window while it runs; **■ Stop** stops it.
"""

TAB_RATINGS = """
# Ratings, Genres & IDs

## Ratings
**Sync Ratings** fetches the rating and the votes from TMDB and / or OMDb (IMDb data) and writes them to the NFO (<rating>, <votes>, Kodi <ratings>) and the XML (<IMDBrating>, <Rating>, <Votes>, <VoteCount>).
- The dialog shows both sources side by side. A rating of 0 or 0 votes counts as no data.
- Several movies: "Apply this choice to all remaining movies" or "Use the source with more votes" (equal votes → average); **Tools → Sync Ratings Online — All Movies…** fetches first and then shows current → new for every movie.
- When neither source has data, a second dialog asks once for typed values or Skip.
- When TMDB or OMDb cannot be reached, the movie is skipped and listed at the end — never treated as "no rating".
The defaults of the checkboxes: Settings → Ratings.
| ⬤ | found, NFO and XML agree
| ◐ | NFO and XML differ
| ○ | no tag found
| ✕ | the tag is not a number

## Genres
**Normalize Genres** fixes genres in both files: capitalisation, synonyms ("Sci-Fi" → "Science Fiction"), translations (PT, DE, FR, ES, IT, RU, ZH, AR), duplicates and merged tags ("Family/Fantasy"). It copies the genres to the file that has none and turns <Genres>/<Genre> in an NFO into Kodi <genre> tags. Movies without genres get them from TMDB (then OMDb), with a preview first. Genres not in Settings → Genres are "custom": keep or delete them, or Right-click → **Add Custom Genre(s) to Settings**. **Tools → Normalize Genres — All Movies…** previews every change.

## IMDb and TMDB IDs
- **Normalize Sources** fills missing tags, lets you choose between conflicting IDs (titles looked up on TMDB) and asks for an ID where there is none. When only one ID is known, every ID write leaves EMPTY tags for the other source (e.g. <tmdbid></tmdbid>), ready to fill by hand. Existing values are never blanked.
- **Search Sources** looks the movie up on TMDB by title + year (in English, your library language and the original title). Each movie shows the IDs its files hold now and, first, the film behind that ID. **Enter ID…** lets you type an IMDb (tt…) or TMDB ID, shows title, year and poster, then writes both IDs.
- Films on IMDb but not on TMDB: the first row reads "IMDb tt… — not on TMDB"; **Confirm IMDb** writes the IMDb ID and marks the movie "OK (IMDb only — not on TMDB)", so Verify IDs and Auto Repair stop looking for it.
- **Verify IMDb/TMDB IDs** checks on TMDB that the IDs belong to the movie (any title language, year ±1): OK, IMDb and TMDB point to different films, ID belongs to another film, ID does not exist, NFO and XML disagree, no IDs. The report sorts by any column and saves to .txt or .csv; nothing is written until you press **Fix…**. It also keeps the movie's TMDB collection (Collections tab).
- **Copy Movie Name** copies the title (it asks when the files hold several).

## Local titles
When NFO <title> and XML <LocalTitle> differ, Right-click → Metadata → **Make titles the same (NFO ↔ XML)…** lets you choose; Auto Repair gives the side that is the original title (or that does not match the folder) the other one.

## Audio, subtitles and language
- **Audio**: FFprobe tracks as LANGUAGE (CHANNELS); hover for codec and bitrate. A track FFprobe reports as UND takes the language from the NFO or the XML when it fits ("POR — from NFO"). Nothing is written.
- **Subtitles**: embedded tracks and external files (e.g. Movie.pt.srt, also in a Subs folder; forced and SDH flags are read). Right-click → **Subtitles…** opens for any movie; **🌐 Open on OpenSubtitles.org** searches it there.
- **Hard-coded subtitles…** marks burned-in subtitles (they cannot be detected): tick the language(s) or type an ISO 639-2 code. The app writes <tag>Hardsub POR</tag> to the NFO and <Tags><Tag>Hardsub POR</Tag></Tags> to the XML; the column shows "Hard: POR".
- The **Language OK** column is Y when the target language (Settings → Language) is in an audio track, a subtitle (also hard-coded), XML <Language> / <LanguageCode> or NFO <language>.
"""

TAB_BULK = """
# Bulk Tools & Auto Repair

## The Tools menu
| Export Movie List… | CSV, TSV, text or Excel ([[Ctrl+Shift+E]], also the **Export…** button)
| Choose Columns… | show or hide columns
| Ignored Folders of the Last Scan… | the folders the last scan did not add
| Library Statistics | health, quality, genres, decades, libraries
| Duplicate Movies Report | the same ID, or title + year, elsewhere
| Manage 'Not a duplicate' marks… | your answers, with Remove
| Recompute Health Status (no rescan) | the rules again, no file read
| Save / Open Scan Results… | a scan to or from a file (**Save Scan Results…**, **Open Scan Results…**)
| Backup History / Undo… | every run that changed files (Backups & Undo tab)
| Refresh Icons — All Movies | redraws every row ([[Ctrl+I]])
The "— All Movies" entries: **Sync Ratings Online — All Movies…**, **Normalize Sources — All Movies…**, **Search Sources — All Movies…**, **Verify IMDb/TMDB IDs — All Movies…**, **Check Collections Online — All Movies…**, **Fix Collections — All Movies…**, **Create Collection Folders — All…**, **Auto Repair — All Movies…**, **Normalize Genres — All Movies…**, **Run Improvements Check — All Movies…**, **Health Status Report — All Movies**, **Copy poster.jpg → folder.jpg — All Movies with Differences…**, **Fix Image Proportions / Size — All Movies with Image Warnings…**, **Rename NFOs for Kodi — All Movies with a folder-named NFO…**, **Delete extrafanart Subfolders — All Movies…**. They always cover every movie of every library; when a filter hides rows, the preview says "all N movies in all libraries (the filter shows M)".

## Previews before writing
The bulk tools first show what will change; closing the preview writes nothing, **▶ Run** (or its own name) writes. Every run makes one backup folder, can be cancelled ("Cancelled after k of n; m left out"), and ends with a summary that points to **Backup History / Undo**.

## Auto Repair
Applies every safe fix in one go. Artwork is never touched. A backup first; the summary lists fixed, skipped and still failing movies; **Auto Repair — All Movies…** offers a dry-run preview. The steps, in this order:
1. Escape '&' in the NFO (& → &amp;; Jellyfin ignores an NFO with a bare '&')
2. Resolve conflicting IMDb/TMDB IDs with TMDB
3. Look up IMDb/TMDB IDs on TMDB (exact title + year applies automatically, otherwise ask)
4. Copy the IMDb/TMDB ID to the other file
5. Sync rating and votes online (TMDB/OMDb)
6. Normalize genres and sync them between NFO and XML (custom genres kept)
7. Fill genres from TMDB (verified TMDB ID required)
8. Fill the year from TMDB (verified TMDB ID required)
9. Copy the title between NFO <title> and XML <LocalTitle>
10. Make the local title the same in NFO <title> and XML <LocalTitle>
11. Fill XML <Language> from NFO <language> / XML <LanguageCode>
12. Trim IDs like 'tt0133093/' and remove exact duplicate tags (NFO / XML)
13. Write the collection TMDB lists for the movie (NFO <set>; your own collections are kept)
14. Rename the folder-named NFO so Kodi reads it (<video>.nfo; movie.nfo for discs, multi-part, versions)

## Export Movie List
- Columns: Basic, Identify (links + outline), Standard, All, or your own choice (the Collection column too).
- Rows: all movies or the current filtered view (in the grouped view: the movies, never the collection rows).
- Formats: CSV comma, CSV semicolon (Excel in CH / DE / PT / FR), tab-separated, plain list, Excel .xlsx. A saved file offers "Open it now?".
"""

TAB_COLLECTIONS = """
# Collections

## What a collection is
A collection (Kodi calls it a movie set) groups the movies of a saga — "Harry Potter Collection", "The Matrix Collection". The NFO holds it as <set><name>…</name></set>; Kodi groups movies by that **name**, so two spellings make two sets. Jellyfin also reads the TMDB collection ID (<set tmdbcolid="…">). movie.xml holds the same collection (TMDbCollectionId, CollectionName); MediaClinic reads and writes both files.

## The Collection column and the grouped view
- The **Collection** column (hidden by default, Tools → Choose Columns…) shows the name; the Filter box finds it.
- **Group by collection** (next to the sort buttons, or Settings → NFO / XML → Collections; off by default) shows each collection as one row — "Harry Potter Collection (8)", the year span, the worst health colour — with its movies under it. Movies without a collection stay single, in your sort order.
- A click selects a collection row; its ▸ arrow, a double-click or [[+]] / [[-]] open or close it; open collections stay open while the app runs. The collection panel's **All actions ▾** shows the row's menu.
- Selecting a collection row means its movies for every action ("8 movies selected"); [[Ctrl+A]] selects every movie, also inside closed collections.
- Right-click a collection row: **Expand / Collapse**, **Select Its Movies**, **Fix Collection…**, **Rename / Join Collection…** (choose a collection in use to join it: its movies get its name and TMDB ID), **Create Collection Folder…**, **Collection Artwork…**, **Open Collection Folder**, **Open Collection on TMDB** (**Search Collection on TMDB** when the collection's TMDB ID is not known), **Check Collection Online**, **Expand All / Collapse All**. The panel shows the collection: its poster (from the collection folder), TMDB ID, years, folder, artwork, overview, its movies and the fixes, with **Artwork…**, **Open Poster**, **Open Fanart**, **Open Folder** and **TMDB** (the collection's page with its movies, or a TMDB search for the name).
- One collection, one name: Kodi shows one set per name, so a TMDB collection gets ONE name for all its movies — in English, unless MORE THAN HALF of its movies have their local title in one other language (NFO <title>; XML <LocalTitle> when the NFO has none) — then in that language. **Settings → NFO / XML → Collections → Collection name language** can fix one language for every collection instead (TMDB's name in it, else English). A title the app cannot match to a TMDB title counts as English. The library language is never used for the name; when TMDB has not given the English name yet, the name in your NFOs is kept and **Check Collections Online** fetches it. When NFO <title> and XML <LocalTitle> differ, the movie shows **Title mismatch** and its Fix asks which title to keep. The warning, **Fix Collection…** and Auto Repair use the same name, and **Fix Collection…** writes it to every movie of the collection (the preview lists them). When your own collection is written two ways, Fix writes the name most of its movies use. After any change the table is checked again, so a fixed warning goes away.

## Checking collections online
**Tools → Check Collections Online — All Movies…** (or Right-click → Metadata → Collection ▸ → **Check Collection Online**) asks TMDB which collection each movie belongs to — one request per movie, two per collection, again only after 30 days. **Verify IMDb/TMDB IDs** keeps the same data at no extra cost. Movies without a TMDB ID, or whose ID Verify IDs flagged, are skipped and counted. Scans and Recompute Health never go online.

## The collection rules
Three rules in Settings → Health Rules, all on by default, all warnings:
- **Collection missing or different**: TMDB lists a collection the NFO does not have, the NFO names another one, or one collection is written two ways in your library ("written as X here and as Y in 3 other movies — Kodi shows two sets").
- **Collection artwork**: the collection folder, its poster or its fanart is missing (only while a collection folder is set).
Your own collections ("Disney", "Oscar winners") are never warned about and never removed. A movie that was not checked online gets no "missing / different from TMDB" warning (its tooltip says so); a collection written two ways and a movie.xml that differs from the NFO are found by every scan.

## Fixing collections
Right-click → Metadata → **Collection ▸**:
- **Fix Collection…** writes the collection TMDB lists, under the collection's one name (see "One collection, one name" above), with its overview when the NFO has none. Several movies: a preview first. Also **Tools → Fix Collections — All Movies…** and the Auto Repair step.
- **Set Collection…** puts the selected movies in a collection: one in use, your own name, or a TMDB collection found with **Search TMDB** (its TMDB ID and name are written). With the tick it then makes the collection folder and opens **Collection Artwork…**. **Remove from Collection…** (asks first) is the only action that ever removes a <set>: it says the movies are **not in a collection**. MediaClinic remembers that (no_collection.json), so TMDB's collection is no longer suggested for them while their NFO has no <set>; it also works for a movie TMDB puts in a collection that you don't want. **Set Collection…** puts a movie in a collection again.
- A collection TMDB no longer has: when an NFO links a TMDB collection (tmdbcolid) that TMDB no longer lists for the movie, or that no longer exists, **Check Collections Online** gives the warning "Collection: '…' no longer exists on TMDB" (or "is not listed by TMDB for this movie"); **Fix** runs **Remove from Collection…**.
- **Update** re-reads the NFO: a movie whose <set> you changed moves to its new collection in the grouped view. movie.xml: every collection action writes the same collection into movie.xml (TMDbCollectionId and CollectionNumber = the TMDB collection ID, or 0 for none; CollectionName); Remove from Collection… sets the IDs to 0 and removes the name. An NFO-style <set> block inside movie.xml does not belong there and is removed. When movie.xml and the NFO say different collections, the warning "Collection: movie.xml says …" is fixed by **Sync Collection (NFO ↔ movie.xml)…** (the NFO's collection goes to movie.xml; an NFO without one takes movie.xml's). <JSONDump> is never changed.
Every NFO is backed up first; **Backup History / Undo** puts it back. Every other byte of the file stays as it was.

## The collection folder (collection artwork)
Kodi reads collection artwork from ONE folder you choose in Kodi: Settings → Media → Videos → **Movie set information folder**. Set the same folder in **Settings → NFO / XML → Collections → Collection folder** (the same share, e.g. \\\\NAS\\Movies\\Sets or Z:\\Sets).
- Each collection has a folder named like the collection, with / \\ ? : * " < > | written as _ (Kodi's rule), holding poster.jpg and fanart.jpg.
- **Create Collection Folder…** (Right-click, a collection row, or **Tools → Create Collection Folders — All…**) shows a preview, makes the folder and downloads the poster (library language first) and the fanart from TMDB. An existing file is never replaced. A missing TMDB API key, or a collection without a poster or fanart on TMDB, is listed in the result. Your own collections get the folder: choose their images with **Collection Artwork…**. Undo removes what the run created.
- **Collection Artwork…** (Right-click a movie or a collection row, the panel's **Artwork…**, or **Fix** on "Collection artwork: … missing" for one collection) shows the posters and fanart images of the collection's TMDB collection, or of **The movies of this collection** (their own poster / fanart). Without a known TMDB collection, **Search TMDB** finds one by name. The posters come 12 per page (4 per row) and the fanart images 9 per page (3 per row): **Next ›** and **‹ Previous** show the other pages, and a chosen image stays chosen. The window keeps the size you give it. Click one poster and one fanart image, then **Save to Folder**: the folder is made when missing; an existing image is replaced only after a backup, so Backup History can undo it.
- A folder that differs only in case is found (Windows, SMB); one that differs in accents is not the same folder for Kodi, and the warning names it.
- When a collection gets a new name (**Fix Collection…**, **Set Collection…**, **Rename / Join Collection…**, Auto Repair), its folder comes along: the files of the old folder move into the folder of the new name, and the empty old folder is removed. When both folders have a poster (or fanart), the old folder's image is kept and the other one goes to replaced\\ inside the folder — nothing is deleted. The folder stays where it is while another movie still uses the old name. Backup History / Undo puts everything back.
- A folder left under another TMDB name of the collection (from before) shows **Collection folder: images left in '…'**; its Fix **Move to the Collection Folder** moves the files the same way.
"""

TAB_BACKUPS = """
# Backups & Undo

## Automatic backups
Before the app changes a .nfo, .xml or image file, it copies the original to backup\\backup_<Movie>_<date>_<time>\\ in %APPDATA%\\MediaMetadataClinic (with the settings, so an update keeps them). One run (a batch, or one action on one movie) is one backup folder with a manifest.json (where every file came from, which action made it). Every NFO / XML write is atomic: a failed write never leaves a half-written file, and the file's encoding, BOM and line endings are kept.
> If a backup cannot be made, the change does not happen — the movie is reported as failed.

## Backup History / Undo
**Backup History / Undo…** (in the header and in Tools) lists the runs, newest first. **Restore this run** puts the files back:
- your current files are backed up first, so an undo can be undone;
- files changed after the run are listed and can be skipped;
- a renamed NFO gets its old name back, and files a run created (collection artwork) are removed;
- the rows refresh.
Runs removed by the size cleanup stay listed as "removed by the size cleanup".

## Size limit
Settings → Backup: the maximum size of the backup folder and "Delete the oldest backups automatically" (on by default). Runs of this session and of the last 14 days are never deleted automatically; the cleanup is written to a log. A run larger than the limit is announced before it starts. **Delete all backup folders** empties the folder.
"""

TAB_SERVERS = """
# Media Servers

## Kodi
MediaClinic reads every name Kodi uses and shows the file Kodi would pick, in Kodi's order:
| Poster | <video>-poster.jpg/.png, poster.jpg/.png, <video>.tbn, movie.tbn
| Fanart | <video>-fanart.jpg/.png, fanart.jpg/.png
| NFO | movie.nfo, <video>.nfo (an NFO named after the folder is not read)
| Extra fanart | fanart1.jpg…, <video>-fanart1.jpg…, the extrafanart folder
<video> is the video's file name without its extension. The tooltips say which file was found. Fetch Poster/Folder, Fetch Fanart and Copy poster → folder write in the style the folder already uses: a Kodi folder gets <video>-poster.jpg, and no folder.jpg unless one exists. New backdrops follow the same rule.
- **Rename NFO for Kodi…**: Kodi reads "<video>.nfo" or "movie.nfo", not an NFO named after the folder. It offers both names (the recommended one selected); **Tools → Rename NFOs for Kodi — All Movies with a folder-named NFO…** shows a preview. A name that exists is never overwritten; Undo puts the old name back.
- DVD and Blu-ray folders: a VIDEO_TS or BDMV structure is the movie; VIDEO_TS-poster.jpg, VIDEO_TS.nfo, index-poster.jpg and index.nfo are read too. FFprobe and frames use the largest .VOB / .m2ts file.
- Collections: Kodi's movie set information folder — Collections tab.

## Jellyfin, Emby and Plex
The names the other servers read are found too, after Kodi's:
| Poster | <video>.jpg, cover, default, movie, <video>-cover…
| Fanart | backdrop, background, art
| Extra backdrops | backdrop-1, fanart-1, background-1, art-1
| Pictures | .jpg, .png, .jpeg, .webp, .gif, .bmp
- The poster, folder and fanart tooltips say which servers read the file found. folder.jpg alone counts as the poster (all four servers use it).
- NFO: movie.nfo is read first. Two NFOs the servers read (e.g. movie.nfo and <video>.nfo) are a warning: delete the one you do not need. mymovies.xml is shown in the XML tooltip: no current server reads it.
- Other videos are not "Multiple video files": trailers (-trailer), samples, extras (-featurette, -deleted …), the parts of a stack (cd1, part2) and versions ("Movie - 1080p"). The Video tooltip lists them.
"""

TAB_SETTINGS = """
# Settings

**Settings ▾** in the header opens **All Settings…** or one of the tabs; [[Ctrl+S]] opens the Settings window and [[F10]] the Settings ▾ menu. **Save & Apply** writes settings.json; a field that is not valid is named and nothing is saved. Health rule and image size changes apply at once; Language, Genres or NFO / XML tag changes offer an update scan.
| Editor & FFmpeg | text editor, FFmpeg folder (**Test FFmpeg**; found by itself when it is on the PATH or next to the program), backdrop frame count, parallel scanning (workers; FFprobe processes), optional scraper, "Remember FFprobe results" (each video probed once; a changed video is probed again)
| API Keys | TMDB, OMDb and fanart.tv keys with **Validate** buttons and links to get them; keys are never written to the log
| Browser | the browser for web links
| Language | the ISO 639-1 code of the Language OK column (default PT)
| Improvements | the checks of the Improvements report and the NFO / XML maximum sizes
| Image Sizes | minimum quality tier (the same value as Health Rules), 3:4 and 16:8 acceptance, minimum file sizes
| Ratings | the defaults of the Ratings Sync checkboxes
| Genres | the standard genre list, one per line
| NFO / XML | the tag pairs of the Improvements Check; **Collections**: the collection folder and **Group the movie table by collection**
| User Interface | alternating row colours, header tooltips, compact mode, the Repeat line, the Ignored folders window after a scan, dark title bars, "Check for updates at start"
| Health Rules | every rule with its checkbox, level or threshold; **Reset to defaults**
| Backup | the size limit, automatic deletion of the oldest backups, **Delete all backup folders**
"""

TAB_SHORTCUTS = """
# Shortcuts

## Keyboard
| [[F1]], [[Ctrl+H]] | Help
| [[F5]] | Full Scan
| [[Esc]] | cancel a scan; clear the Filter box; close a window (Settings asks first if you changed something)
| [[Ctrl+F]] | go to the Filter box
| [[Ctrl+L]] | Clear All…
| [[Ctrl+S]] | Settings (all tabs)
| [[F10]] | the Settings ▾ menu
| [[Ctrl+B]] | hide / show the selected-movie panel
| [[Ctrl+O]] | open the selected movie's folder
| [[Ctrl+E]] | open the selected movie's .nfo (the status bar says when there is none)
| [[Ctrl+R]] | Update the selected movie(s) (no FFprobe)
| [[Ctrl+Shift+R]] | Update the selected movie(s) (with FFprobe)
| [[Ctrl+I]] | Refresh Icons — All Movies
| [[Ctrl+Shift+E]] | Export Movie List…
| [[Ctrl+1]] … [[Ctrl+9]] | sort presets 1 to 9
| [[Alt+S]], [[Alt+T]], [[Alt+H]] | the Settings, Tools and Help menus
The shortcuts of the movie table work while the Movies part is shown.

## Selection and moving
| A–Z, 0–9 | jump to the next movie with that letter (repeat to cycle)
| [[PageUp]], [[PageDown]] | one page; [[Home]] / [[End]]: first / last row
| [[Shift+Up]], [[Shift+Down]] | extend or shrink the selection
| [[Shift+PageUp]], [[Shift+PageDown]] | extend by one page
| [[Shift+Home]], [[Shift+End]] | extend to the first / last row
| [[Ctrl+A]] | select every shown movie (in the Filter box: the text)
| [[+]], [[-]] | open / close a collection row (grouped view)
| Double-click | the action of the column (Health & Fixing Issues tab)
| Right-click, [[Shift+F10]], Menu key | the menu of the selected movie(s)
With more than one movie selected the status bar shows "N selected".
"""

TAB_TROUBLE = """
# Troubleshooting

## Common questions
### The Audio column is empty
Switch FFprobe On and run Update (with FFprobe).
### A health reason no longer applies
Tools → Recompute Health Status (no rescan) — also done at every start.
### Source shows ✕ although the movie has an ID
Some tags are empty (e.g. <TMDB></TMDB>) while others hold the ID; Normalize Sources fills them.
### Backdrop extraction makes no files
Check FFmpeg in Settings → Editor & FFmpeg (**Test FFmpeg**) and raise the frame timeout.
### Excel opens the CSV in one column
Export with "CSV — semicolon separated" or as .xlsx.
### Collections show no warning
Run **Tools → Check Collections Online — All Movies…** first (the rules need TMDB's collection data); the collection artwork rule needs the collection folder in Settings → NFO / XML.

## When TMDB or OMDb do not answer
IMDb is never asked directly: IMDb ratings come through OMDb, IMDb IDs through TMDB. The message names the cause and what to do.
- TMDB "too many requests": wait about a minute.
- OMDb daily limit (1,000 requests on a free key): try again in a few hours; TMDB still works.
- Key rejected: Settings → API Keys → Validate. No connection: check the internet and try again.
- In a batch the message comes once, with "Pause this run", "Continue with the other source" and "Cancel". A paused service shows "⚠ … paused" in the status bar (click it to see why or to end the pause); the next action asks "Try anyway?".
- A network error stops a run and keeps what was done; a file that cannot be written (locked, read-only) fails that movie only.

## Logs
**Help → Open Logs Folder** opens logs\\ with app.log selected. Every unexpected error is written there (API keys never): attach it to a bug report.

## Updates
**Help → Check for Updates…** (or the button in About) asks GitHub for the latest release; nothing else is sent. A new version can be opened on GitHub or skipped. The Windows program can also download and install it: the package is checked against its SHA-256 and unpacked next to the current version, which is never changed. Your settings, results and backups are kept (they live in %APPDATA%). Settings → User Interface → "Check for updates at start" (off by default) checks once a day and only shows a link in the status bar.

## One window at a time
MediaClinic runs once: starting it again brings the running window to the front.
"""

# (menu / tab label, text) in display order.  The About tab is built by the
# main script and always comes last.
HELP_TABS = [
    ("🚀  Getting Started",        TAB_START),
    ("📊  The Window & Table",     TAB_WINDOW),
    ("🔄  Scans & Libraries",      TAB_SCANS),
    ("🩺  Health & Fixing Issues", TAB_HEALTH),
    ("🖼  Images",                 TAB_IMAGES),
    ("⭐  Ratings, Genres & IDs",  TAB_RATINGS),
    ("🛠  Bulk Tools & Auto Repair", TAB_BULK),
    ("🗂  Collections",            TAB_COLLECTIONS),
    ("🕘  Backups & Undo",         TAB_BACKUPS),
    ("📺  Media Servers",          TAB_SERVERS),
    ("⚙️  Settings",               TAB_SETTINGS),
    ("⌨  Shortcuts",               TAB_SHORTCUTS),
    ("🧰  Troubleshooting",        TAB_TROUBLE),
]
ABOUT_LABEL = "ℹ️  About"
