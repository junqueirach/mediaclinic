# =============================================================================
# help_text.py
# Metadata & MediaClinic — Help contents (structure markup, pure text)
# Version: 0.19.6                                              ### REWRITTEN v0.19.4 B74 ###
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

import mc_i18n as _i18n                                           ### NEW v0.20.0 UI1e ###

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

## New in v0.20.2
- **Rename Folder and Files…**: movie folders named from a pattern, the files follow, Undo renames back (Ratings, Genres & IDs tab).
- **Certifications…**: the age rating from your countries in your order, written in every rating tag your files have (Ratings, Genres & IDs tab).
- Collections: **Create / Edit set.nfo…** (Kodi 22 and later) and **Collection Gaps…**, the movies of a collection your library lacks (Collections tab).
- Emby and Jellyfin: theme videos in the backdrops folder count as backdrops, and the Kodi-only warnings (actor photos, votes, collection artwork) stay off when Kodi is not ticked.
- The rows of a library that cannot be reached are grey.
- With no program ticked the app asks once which programs you use; a new user starts with the Medium preset.
- **Help → Copy Diagnostic Info…** for a bug report, without paths or movie names (Troubleshooting tab).

## New in v0.20.1
- The Tools menu is grouped into submenus (Bulk Tools & Auto Repair tab).
- Posters: Replace Low-Resolution Posters, Review Posters One by One and an artwork language setting (Images tab).
- IDs: Fix Wrong IMDb / TMDB IDs and Add <uniqueid> for Kodi (Ratings, Genres & IDs tab).
- Auto Repair lets you untick steps; Fix one issue runs a single fix on all movies; long runs can be paused.
- Warnings say what is wrong and what to do, and every Fix leads to a tool that can solve it.
- Actors and Extra art columns, and actor photos for Kodi (Images tab).
- set.nfo for Kodi collections (Collections tab).
- Export: an HTML page with five layouts and six themes.
- More keyboard shortcuts (Shortcuts tab).
- Start-up shows the last list at once; closing the app stops what is running (it asks first).

## What this app does
Metadata & MediaClinic audits and repairs Kodi, Jellyfin, Emby and Plex movie libraries. It scans your library folders, checks every artwork file, metadata file and video, and shows a colour-coded health table, so you see at a glance what is missing or broken. Most problems can be fixed from the same table.

## How a movie folder looks
One folder = one movie. A complete folder holds:
- the video, e.g. **Movie Name (2001).mkv** (or .mp4, .avi …)
- the Kodi metadata, **<video>.nfo** or **movie.nfo**
- **movie.xml**, a legacy format (optional): only Emby's XML plugin reads it, and Media Center Master writes it; Kodi, Jellyfin and Plex do not read it
- **poster.jpg** (portrait, 2:3) and **fanart.jpg** (wide, 16:9)
- **folder.jpg**, an identical copy of the poster (optional: Plex, Jellyfin, Emby and Infuse read poster.jpg, and Kodi the poster's own name)
- extra backgrounds: **backdrop.jpg**, **backdrop1.jpg** … or Kodi's **<video>-fanart1.jpg** …
- external subtitles such as **Movie Name.pt.srt** (optional)
The Media Servers tab lists every name the servers read.

## First run
1. Click **Browse…** and choose your movie folder. Add more folders later with **Libraries…**.
2. Click **Full Scan** ([[F5]]). The table fills in phases: folders, images, metadata, then video — with FFprobe when the **FFprobe** switch in the status bar is On.
3. Each row shows the health of one movie: green = no rule triggered, yellow = warnings, red = errors.
4. Select a movie: the panel on the right shows its poster, its issues with a **Fix** button each, its files and the common actions.
5. The last scan is saved and restored at the next start.

## The welcome window
At the first start one window asks five things. Only **Start** saves the answers; closing the window brings it back at the next start.
| Language | pick it first: **Restart now** shows the window again in that language
| Movies folder | add it now, or later with **Browse…** or **Libraries…**
| Which programs play your movies? | tick every one you use. With nothing ticked every rule runs, also the ones only Kodi needs: Start asks once (**Tick my programs** / **Start anyway**). A user with nothing ticked sees this question once more in v0.20.2
| Strictness | Tight, Medium or Easy
| FFprobe | optional: nothing is included or downloaded for you; **Choose folder…** or **Download page**
Someone updating from an older version sees only the programs question once, with **Not now**.

## Which programs play your movies?
The ticked programs set the **health mode**: it decides which files MediaClinic checks and repairs.
| NFO only | Ticked: **Kodi, Plex, Jellyfin, Emby, Infuse** (any of them). MediaClinic works on the .nfo files, as tinyMediaManager, Radarr or MediaElch make them. movie.xml is ignored (not read, not checked, not written; no .xml column). Plex itself reads no NFO, only the artwork.
| NFO and movie.xml | Ticked: **One of them + MediaBrowser / Media Center Master**. The NFO and movie.xml, every check and fix of both.
| movie.xml only | Ticked: **MediaBrowser / Media Center Master alone**. The NFO is ignored (not read, not checked, never written; no .nfo column). Title, year, rating, IDs and genres come from movie.xml, and the fixes write movie.xml. Collections, Rename NFO for Kodi and the **&** fix work on the NFO, so they are not offered.
Change it later in **Settings → Health Rules → Which programs play your movies?**: tick every program you use (Kodi, Plex, Jellyfin, Emby, Infuse, MediaBrowser / Media Center Master).
- The line under the ticks shows the files checked and the names a fix writes.
- A fix writes a name every ticked program reads: <video>.nfo, <video>-poster.jpg and <video>-fanart.jpg. These are the names Kodi recommends; they work with every Kodi setting and are read by every other program too. (movie.nfo and poster.jpg work in Kodi only with the source setting "Movies are in separate folders that match the movie title".)
- A folder whose own names every ticked program reads keeps them.
- Nothing ticked keeps the mode as it was and each folder's own names.
- Reading never changes: every name these programs accept is still read.
- A library played by other programs gets its own choice in **Libraries… → Programs…** (it replaces that library's **NFO only** mark).
- A change between NFO and movie.xml offers a new scan.

## A library without movie.xml
In the mode **NFO and movie.xml**, a library where no movie has a movie.xml gets one more question after its scan: **NFO-only library?**
- **Yes, NFO only** switches the XML checks off for that library alone: no "Missing XML file" error, no NFO / XML comparison; the XML column shows —.
- Change it later in **Libraries…** with the **NFO only** button.

## Quick-start checklist
- **Settings → Editor & FFmpeg**: set the FFmpeg folder (video analysis and backdrop extraction).
- **Settings → API Keys**: add the TMDB and OMDb keys (ratings, ID search and checks, artwork); a fanart.tv key adds more posters and backdrops.
- **Settings → Language**: the target language of the Language column (default PT). The language of the app itself is **Settings → User Interface → Interface language** (English, Português (Brasil), Español or Same as Windows; **Restart now** restarts in it).
- **Settings → Health Rules**: choose what counts as an error or a warning. A **Health preset** (Easy / Medium / Tight) sets them all at once; a new user starts with Medium.
- To triage: sort by **Health** (Errors first), click the **Errors** counter, or tick **Problems only**.

## Status icons
| ⬤ | OK — present and valid
| ◐ | warning — conflict, wrong proportions, a minor issue
| ○ | missing
| ✕ | error — corrupt image, XML error, unreadable value
| — | not used — movie.xml in an NFO-only library, or the file the health mode does not use

## Files the app writes
| settings.json | all settings (%APPDATA%\\MediaMetadataClinic)
| last_results.json | the last scan, restored at the start (same folder)
| ffprobe_cache.json | remembered FFprobe results (same folder)
| fanarttv_cache.json | fanart.tv answers, kept 7 days (no key inside)
| collections_cache.json | the TMDB collections (names in every language)
| last_ignored.json | the folders the last scan did not add as movies (the Ignored folders report)
| not_duplicates.json | your "Not a duplicate" answers
| no_collection.json | the movies you marked "not in a collection"
| backup_cleanup_log.json | the backup runs the size cleanup removed (Backup History lists them)
| logs/app.log | the log next to the program; API keys are never written to it (**Help → Open Logs Folder**)
| backup/ | the automatic backups (same folder; an update keeps them)
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
Select one movie and the panel shows its poster, year, genres, rating, library and a health badge, then four parts:
- **ISSUES**: every health reason.
- **FIXES**: each fixable problem with its **Fix** button.
- **FILES**: NFO, XML, poster, folder, fanart, video (✓ or ✕).
- **ACTIONS**: **Open Folder**, **Edit NFO**, **Fetch Poster…**, **Search Sources**, **Update**.
- **All actions ▾** opens the full right-click menu.
- Several movies selected: "N movies selected", the actions that work on several, and the fixes with how many movies have each problem.
- A collection row (grouped view) shows the collection panel (Collections tab).
- **Hide ›** or [[Ctrl+B]] hides the panel; the slim **‹** strip at the right edge shows it again. Drag the divider to change its width; a double-click on the divider resets it. Both are remembered.

## Columns
| Movie Name | NFO <title>, then XML <LocalTitle>, original titles, the folder name. Hover: the folder, its library, the date added and every health reason. Double-click opens the folder. A multi-part movie (Movie-CD1.mkv + Movie-CD2.mkv) is shown as "Name — Part 1 + Part 2"; only the display changes, not the files.
| Year | NFO <year> or XML <ProductionYear>.
| Genres | NFO <genre> tags; when the NFO has none, the XML <Genres> (the tooltip names the source).
| Rating | NFO <rating> (or Kodi's <ratings> block), XML <IMDBrating> / <Rating>. Hover: value, votes, source.
| Votes | NFO <votes>, XML <Votes> / <VoteCount>.
| Source | the IMDb and TMDB IDs of every tag: ⬤ all agree, ◐ partial or conflict, ○ missing, ✕ some tags filled and some empty. Hover shows the last Verify IDs result; double-click opens IMDb or TMDB.
| Poster, Folder, Fanart | status and quality tier of each image (Images tab).
| Backdrops | the number of backdrop images; hover: their average size.
| .nfo / .xml | the metadata file status. Hover lists the errors with the line and the tag names (the first 5); double-click opens the file in your editor. The health mode hides the column of the file it does not use (.xml for Kodi, Jellyfin, Emby…; .nfo for movie.xml only); — means not used (an NFO-only library).
| Language | movie.xml's top-level <Language>: the language for metadata downloads. Without movie.xml: the NFO's top-level <language> (the same meaning), else the language of the first audio track. The tooltip names the source. Empty is normal.
| Video, Video Size, Quality | container, size and resolution class.
| Audio | FFprobe audio tracks, e.g. EN (5.1), PT (2.0).
| Language OK | Y / N: the target language in audio or subtitles (the heading shows the code, e.g. "PT OK?").
| Subtitles | embedded tracks (FFprobe) and external files.
| Library | the library (root folder). Hidden by default.
| Collection | the movie's collection (NFO <set>). Hidden by default.
**Tools → Choose Columns…** shows or hides columns; the choice is kept.
- Drag a heading edge to resize a column, double-click a heading to fit it, or use **↔ Auto-size Columns**.
- **↺ Default Widths** puts every column back to its original width after a resize went wrong.
- In the grouped view the Year column widens for a collection's years ("1979–1986") and gets your width back when you ungroup.
- Widths, window sizes and positions are remembered.

## Filter
Type in the **Filter** box ([[Ctrl+F]]) to keep the movies whose name, year, genre, language, quality, health status, health reason or collection matches — "backdrops" lists every backdrop issue. [[Esc]] clears it.
- **Problems only** hides the green rows.
- The library box next to **Libraries…** shows one library or all of them.
- "n of m shown" counts the movies the filter keeps.

## Sorting
The sort row reads "Sort by [column] [direction]"; **+ then by** adds up to two more levels (✕ removes one). The direction is said in words — A → Z, Newest first, High → low, Worst first, Errors first … — click it to turn it round.
- Every column can be used, plus **Health** and **Number of issues** (the first two entries) and **Date added** (NFO <dateadded>, XML <DateAdded>, else the creation date of the video or the folder).
- Click a column heading to sort by it (again = reversed); Shift+click adds it as the next level. ▲1 / ▼2 in the headings show the levels.
- Empty values (no rating, no poster, no date) go last, unless a level asks for empty first (the preset Missing metadata does); equal values stay in Movie Name order.
- **★ Presets ▾**: Problems first, Worst artwork first, Missing metadata, Best rated, Biggest files, By library, By collection name (collection A → Z, then year, then movie name; movies without a collection last), and your own (**Save current sort as preset…**; rename or delete them in the same menu). [[Ctrl+1]] … [[Ctrl+9]] apply presets 1 to 9.
- **↺ Update View** sorts and filters again, so movies you just fixed move to their place.
- The sort is kept after a scan and after a restart.

## Duplicates
Movies that share an IMDb ID, a TMDB ID, or a title + year are a "Possible duplicate". The same title + year with two different IMDb IDs are not: a remake or a namesake.
- Right-click → **✔ Not a duplicate…** remembers your answer in not_duplicates.json, so the warning stays gone; a new third copy is still found.
- **↺ Undo 'not a duplicate'** takes it back.
- **Tools → Manage 'Not a duplicate' marks…** lists every pair.
- **Tools → Reports → Duplicate Movies Report** lists them all.
"""

TAB_SCANS = """
# Scans & Libraries

## Scans
| Full Scan | re-reads every movie of the libraries in scope ([[F5]]).
| Quick Scan | reads only the movies that were added, removed or changed since the last scan (a changed NFO, image, subtitle or disc folder counts).
| FFprobe switch | in the status bar: when On, scans also read the video resolution, the audio tracks and the embedded subtitles. A scan without FFprobe keeps the previous FFprobe data.
| Cancel / Esc | stops a running scan; the movies read so far are kept.
A scan never writes to your files. While it runs, the actions that change files wait for it (the status bar says so).
- After an update, the movies saved by the older version are read again in the background: the list is shown first and can be used meanwhile (the status bar counts "k of n"). A scan or closing the app stops the re-read; it continues at the next start.

## Libraries
You can scan several root folders.
- **Browse…** adds one folder; **Libraries…** adds, removes and orders them.
- After the list changes the app offers Full Scan, Quick Scan or Not now.
- **Active / off** turns a library off without removing it:
-- it is not scanned (its drive is not touched);
-- its movies leave the table and the counters, but they are kept;
-- turned on again, they are back at once (a Quick Scan updates them).
- The collection folder part sets the one folder Kodi reads collection artwork from: **Choose…**, **Create…** (makes "Sets" next to the first library, after a yes) or **Clear**. Scans never list it as a movie or an ignored folder.
- All libraries share one table; the **Library** column and the Movie Name tooltip show where a movie lives.
- The library box chooses what the table shows and what the scans cover ("All libraries" or one of them).
- A library that cannot be reached (an unplugged network share) keeps its last scan, is skipped by scans and is shown as "(offline)", its movies in grey. A movie folder that cannot be read for a moment keeps its row, marked "(not read)".
- Duplicates are found across libraries.
- Movies can sit deeper: a folder that holds only other folders (Single Movies / HD / <movie>, Boxsets / <saga> / <movie>) is searched, down to 5 levels below the library. Every movie keeps its library in the Library column.

## Ignored folders
A scan adds a row only for movie folders. These are not added:
- TV series: tvshow.nfo, Season folders or episode files (S01E02, 1x02). Series support comes in v0.22.
- Folders of folders 5 levels below the library: their movies would sit deeper than the scan looks (5 levels). The row says how deep the folder is; add it as a library to include its movies.
- Folders with several separate videos: give each movie its own folder.
- Folders with no video, NFO or XML, system folders ($RECYCLE.BIN, @eaDir …) and folders that could not be read.
A folder with movie metadata is always a movie, and so is a folder with one video and no NFO. After a scan the **Ignored Folders of the Last Scan…** window opens when something was left out (filter, sort, double-click to open, **Export to TXT…**, **Copy All**); turn that off with "Show this window after a scan". **Tools → Reports → Ignored Folders of the Last Scan…** opens it at any time.

## Updating single movies
Right-click → **Update (no FFprobe)** ([[Ctrl+R]]) re-reads the movie or the selection; **Update (with FFprobe)** ([[Ctrl+Shift+R]]) also probes the video (one movie: a status line; several: a progress window with Cancel). After every repair, sync, fetch or delete the affected rows refresh by themselves.

## Movies that disappear
When a movie folder was deleted, Update or the automatic refresh removes its row. Right-click → **Remove from list** drops rows without touching any file; the next scan brings back movies that still exist.

## Closing MediaClinic
Closing the window while a scan or an action runs asks first, then stops it.
- A stopped scan: the folders it had not finished keep their previous results.
- A stopped action: the movie it was working on can be left with one file changed; **Backup History / Undo** can put it back.
- A stopped image fix changes nothing.
- The program then ends completely: nothing keeps reading from a network share after the window is gone.

## Saving and loading scans
- The last scan is saved in last_results.json and loaded in the background at the start ("⏳ Loading last scan…"); the health rules are applied again, so changed rules never leave old reasons behind.
- **••• → Save Scan Results…** / **Open Scan Results…** write a scan to a file or load one.
- **••• → Clear All…** ([[Ctrl+L]]) empties the table (it asks first). No movie file changes; the saved last scan is emptied too, so the rows do not come back at the next start.
"""

TAB_HEALTH = """
# Health & Fixing Issues

## How health works
Every condition that can turn a row red (errors) or yellow (warnings) is a rule in **Settings → Health Rules**, with a checkbox and sometimes a level or a threshold. **Tools → Scan Results → Recompute Health Status (no rescan)** applies changed rules at once (also done at every start).
- Hover the Movie Name for every reason of a movie; the selected-movie panel lists them too.
- **Tools → Reports → Health Status Report** writes them all, with the most common issues first and the movies whose collection was not checked online.
- **Tools → Reports → Run Improvements Check…** lists metadata that could be better (tag pairs of **Settings → NFO / XML**, file sizes).
- **Tools → Reports → Library Statistics**: health, quality, genres, decades, libraries.

## Fix issues
**⚠ Fix issues** lists the real problems of the selected movie(s), each linked to the action that fixes it. It is in three places:
- the right-click menu, right under the movie's name (or "N movies selected") and its number of issues;
- the selected-movie panel, as **Fix** buttons;
- the keyboard: [[Alt+X]].
With several movies selected, each line says how many movies have the problem, and the action runs on just those. A line without an automatic fix is greyed; "show the errors" and "find subtitles" work on one movie at a time.
| Poster / folder.jpg missing | Fetch Poster/Folder…
| Fanart missing | Fetch Fanart…
| Too few / small backdrops | Fetch Backdrops…
| Image proportions / size | Fix Image Proportions / Size…
| folder.jpg differs from the poster | Copy poster → folder.jpg
| NFO errors, XML errors | show the errors (every error with its line)
| Local title differs (NFO ↔ XML) | Make titles the same…
| Collection missing / different | Fix Collection… (Collections tab)
| Collection not on TMDB | gone or not listed there: Remove from Collection…
| Collection in movie.xml differs | Sync Collection (NFO ↔ movie.xml)…
| Collection folder / artwork missing | Collection Artwork… (one collection) or Create Collection Folder… (several)
| Collection images left in an old folder | Move to the Collection Folder
| Possible duplicate | Not a duplicate…
| Video quality below minimum | needs a better copy of the video (no automatic fix)
| NFO named after the folder | Rename NFO for Kodi…
| Online artwork links in the NFO | Remove online artwork links…
| A file a ticked program does not read | Rename Files for My Programs…
| ID only in <imdbid> / <tmdbid> | Add <uniqueid> for Kodi
| Actor photos only as links | Download Actor Photos
| Wrong value in an IMDb / TMDB field | Fix Wrong IDs…
| ID missing or of another film | Search Sources…
| ID not in every tag / two different IDs | Normalize Sources
| Rating / votes missing or wrong | Sync Ratings
| No NFO, only movie.xml | Convert movie.xml → NFO…
| Genres not standard / not in both files | Normalize Genres
| No genres | Fill Genres from TMDB
| Year missing or not valid | Fill the Year from TMDB
| FFprobe could not read the video | Update (with FFprobe)
| Poster below the minimum size | Replace Low-Resolution Posters…
| Language missing in audio and subtitles | find subtitles (OpenSubtitles)…
| Required subtitle missing | find subtitles (OpenSubtitles)…
| Subtitles burned into the picture | Hard-coded subtitles…
| Required audio language missing | needs another copy of the video (no automatic fix)
| Several of the fixes above, or one only Auto Repair does | Auto Repair

The Auto Repair line says how much it does: "Fix all 3 at once" or "Fix 3 of 5 at once" (it never changes images), with the fixes in brackets and each step in its tooltip; with several movies "Auto Repair — 5 fixes on 3 movies". It is first in the list. When it would only do the one fix already listed, it is not shown.

## The right-click menu
Right-click a row, or press [[Shift+F10]] or the Menu key at the selected row. An action that does not apply stays in its place, greyed, with the reason ("missing", "one movie only" …).
- **At the top**: the movie's name and its issues, **✔ Not a duplicate…** (several movies: **Not duplicates of each other**), **Repeat** (the last action again on the current selection; Settings → User Interface can hide this line) and **⚠ Fix issues**.
- **Open Folder** ([[Ctrl+O]]), **Play Video**, **Edit NFO** ([[Ctrl+E]]).
- **Artwork**
-- Open: the entry names the file found, e.g. **Open poster.jpg**, **Open folder.jpg**, **Open fanart.jpg** (greyed **Open poster** when there is none or several movies are selected).
-- Get: **Fetch Poster/Folder**, **Fetch Fanart**, **Fetch Backdrops**, **Replace All Backdrops**, **Extract Backdrop(s)**.
-- Repair: **Copy poster.jpg → folder.jpg**, **Fix Image Proportions / Size…**, **Replace Low-Resolution Posters…**, **Review Posters One by One…**.
-- For Kodi: **Download Actor Photos…**; **Rename actor photos for Kodi**, **Rename extra artwork for Kodi** and **Convert extrafanart → fanart1, 2…** are shown only when the movie has such files.
- **Metadata**
-- Files: **Open .nfo**, **Open movie.xml**, **[!] NFO errors** / **[!] XML errors**.
-- Names: **Make titles the same (NFO ↔ XML)…**, **Rename NFO for Kodi…**, **Rename Files for My Programs…** (with programs ticked), **Rename Folder and Files…**, **Convert movie.xml → NFO…** (a movie with a movie.xml and no NFO), **Remove online artwork links from the NFO…**.
-- **Collection ▸** (Collections tab).
-- Ratings and genres: **Sync Ratings from IMDb / TMDB**, **Normalize Genres**, **Check Genres Against TMDB…**, **Add Custom Genre(s) to Settings**.
- **IDs & Sources**: **Search Sources**, **Verify IMDb/TMDB IDs**, **Normalize Sources**, **Fix Wrong IMDb / TMDB IDs…**, **Add <uniqueid> for Kodi**, **Copy Movie Name**.
- **Video & Subtitles**: **Subtitles…**, **Hard-coded subtitles…**, **Extract Backdrop(s)**.
- **Open online**: **Open on IMDb**, **Open on TMDB**, **Open on Fanart.tv**, **Open on OpenSubtitles.org**, **Open in Scraper**.
- **Check & Repair**: **Health Status Report**, **Run Improvements Check**, **Auto Repair**.
- **Update**: **Update (no FFprobe)** ([[Ctrl+R]]), **Update (with FFprobe)** ([[Ctrl+Shift+R]]).
- **Remove from list**.
Several movies: select with Ctrl+click, Shift+click, Shift+arrows or Shift+PageUp / PageDown / Home / End. The same menu runs the batch versions; longer runs show a progress window with Cancel.

## Double-click
| Movie Name | the movie folder
| Genres, Rating, Votes | the .nfo file in your editor
| Source | choose the IMDb or TMDB page
| Poster, Folder, Fanart | the image in your viewer
| Backdrops | the first backdrop
| .nfo / .xml | the file in your editor (also when it has errors)
| Language | the file the value came from (movie.xml or the NFO) in your editor
| Video, Quality | plays the video
| Subtitles | the subtitle tracks
| Library | the library folder
| Collection | the .nfo file in your editor

## Health rules worth knowing
### File names your programs read
With programs ticked at the top of Settings → Health Rules, a warning appears when the NFO, the poster or the fanart has a name one of them does not read — for example "Not read by Infuse: movie.nfo (needs <video>.nfo)".
- The fix is **Rename Files for My Programs…**: right-click, ⚠ Fix issues, or **Tools → NFO & File Names → Rename Files for My Programs…** for all movies.
-- It gives the NFO, the poster and the fanart the names every ticked program reads (e.g. movie.nfo → <video>.nfo for Infuse).
-- A preview lists every rename first; a backup comes first and Backup History can undo it.
-- The video is never renamed and an existing file is never overwritten.
-- A folder with two NFOs, a DVD / Blu-ray folder or a pair of programs with no common name is listed and left alone.
- Fetch writes new artwork in the name every ticked program reads; when there is none it writes one file for each.
- The ticks also switch off what those programs do not use: Infuse alone has no folder.jpg, extra backdrop or collection checks, and the Kodi-only NFO checks run only when Kodi is ticked.
What each program reads (each was checked on a real server or device):
| Infuse | <video>.nfo, never movie.nfo. Artwork: <video>-poster.jpg, <video>.jpg, poster.jpg, folder.jpg, <video>-fanart.jpg and fanart.jpg; with none of those it shows any other picture in the folder as the poster. Checked on an Apple TV with "Prefer Local Artwork" and "Prefer Local Metadata" on.
| Emby | <video>.nfo and movie.nfo, the NFO's collection and every usual poster and fanart name: a Kodi-style folder works in Emby as it is.
| Jellyfin | the same as Emby. It makes collections from the NFO only when its library option "Automatically add to collection" is on (Dashboard → Libraries → Manage library; off by default) and two or more movies share the collection name.
| Plex | every usual poster and fanart name (poster, folder, cover, <video>, <video>-poster, fanart, backdrop, background, .jpg or .png), but no NFO and no collection from it.
> With only Plex ticked, a pop-up asks once whether to switch the NFO and collection checks off. Change it later with the tick box under the programs.

### Moving from movie.xml to NFO
**Convert movie.xml → NFO…** is for a library moving from MediaBrowser / Media Center Master to Kodi, Plex, Jellyfin, Emby or Infuse.
- Where: right-click on a movie that has a movie.xml and no NFO, or **Tools → NFO & File Names → Convert movie.xml → NFO…** for all movies without an NFO.
- It makes an NFO from each movie.xml: titles, year, release date, runtime, plot, rating and votes, IDs, genres, studios, director, writers, actors, collection.
- The NFO gets the name the ticked programs read: <video>.nfo when a program is ticked; movie.nfo when none is, or for a DVD / Blu-ray folder, a multi-part movie or a folder without a video.
- movie.xml is not changed. A preview comes first, and Backup History can undo it (it removes the new NFOs).

### Rules about the NFO
- "NFO has an unescaped '&'": Kodi reads such an NFO, but Jellyfin may ignore the whole file. Auto Repair writes '&amp;'.
- An IMDb / TMDB ID only in <imdbid> / <tmdbid> is a warning: Kodi reads <uniqueid>. **Add <uniqueid> for Kodi** (its Fix) or Auto Repair adds it and keeps the other tags.
- A <premiered> date counts as the year.
- "ID tags written in the NFO" (under these NFO rules) chooses how an IMDb / TMDB ID is written.
-- Every tag style (<id>, <uniqueid>, <imdbid>, <id moviedb>): for old programs that read only those tags; it also leaves empty tags for an ID that is not known yet.
-- <uniqueid> only — the default since v0.20.1 (Kodi, Jellyfin, Emby and Infuse read it; if you used an older version, your saved choice stays): the ID tags the NFO already has are still corrected, but no other ID tag and no empty placeholder tag is added. movie.xml is not affected.
- "NFO has online artwork links" is off in every preset. **Remove online artwork links from the NFO…** (right-click → Metadata, or **Tools → NFO & File Names → Remove online artwork links from NFOs…**) removes the web links (<thumb> / <fanart><thumb>) only for the artwork the folder has as a file.
-- It counts them first, backs up each NFO and keeps actor images, collection artwork and every other tag.
- Content checks: IDs that are not valid, a year out of range, a runtime or votes that is not a number, a rating above 10, a tag written twice, an empty <title> / <plot> (on only in the Tight preset).

### Rules about movie.xml
- An ID or the votes only in <IMDB_ID> / <TMDB> / <Votes> is a warning: the old programs read <IMDbId> / <TMDbId> / <VoteCount>, and Auto Repair adds them.

### Other rules
- "Missing folder image" is off when the health mode is NFO only (every server shows poster.jpg without a folder.jpg); every preset turns it on in the modes with movie.xml.
- "Poster and folder image are different" is off by default.
- "Title mismatch" names both local titles; "When Repair All cannot tell the right local title" chooses what Auto Repair does then.
- A missing ID: "Movie with ONE source only" and "Movie with NO source" can each be an error, a warning or off.
"""

TAB_IMAGES = """
# Images

## Poster, folder and fanart
**Fetch Poster/Folder…** shows your image next to the TMDB (and fanart.tv) posters; **Use This** downloads the full size to the poster (and folder.jpg when the folder uses one) after a backup. **Fetch Fanart…** does the same for the fanart. **Copy poster.jpg → folder.jpg** fixes folders whose folder.jpg differs; **Tools → Artwork → Copy poster.jpg → folder.jpg…** shows a preview first.
- A download is checked before it replaces anything: a page that is not a picture, or a picture cut off, never replaces a good file.
- The Fetch windows close with **Done** (or [[Esc]]); images applied before are kept. While a download runs, Done shows "Finishing…".

## Quality tiers
| Poster / Folder (2:3) | 4K 2000×3000 · 1440p 1500×2250 · 1080p 1000×1500 · 720p 666×1000 · 540p 540×810 · 480p 480×720 · 360p
| Fanart (16:9) | 4K 3840×2160 · 1440p 2560×1440 · 1080p 1920×1080 · 720p 1280×720 · 540p 960×540 · 480p 854×480 · 360p
- ±5 % tolerance.
- The minimum tier is one setting (Settings → Health Rules and Settings → Images & Artwork); images below it are warnings.
- Proportions: poster and folder 2:3 (3:4 optional), fanart 16:9 (3:2 optional).
- "Corrupt" (✕) means the scan found a bad header or end of the file. A file damaged in the middle can pass the scan; Fix Image or Copy poster then says it cannot be read.
- A PNG named poster.jpg is read and gets an "extension mismatch" warning.

## Backdrops
| Extract Backdrop(s) | FFmpeg frames spread over the film
| Fetch Backdrops | pick TMDB / fanart.tv backdrops; replace a file or save a new one
| Replace All Backdrops | choose the source and how many (it starts at the number you have); the highest resolution first, a failed download is replaced by the next image; a backup first
**Tools → Artwork → Delete extrafanart Subfolders…** removes the extrafanart folders (a backup first). Jellyfin and Emby use them as extra backdrops; Kodi and Plex do not read them. The health rules flag too few backdrops (the main fanart counts as one) and very small ones. With Emby or Jellyfin ticked, a movie with videos in a backdrops folder (theme videos, which they play as moving backdrops) is not flagged for too few backdrops.

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
Right-click → Artwork → **Fix Image Proportions / Size…** ([[Alt+I]]) fixes a poster, folder image or fanart with wrong proportions or a low resolution, with a before / after view. Every file is backed up first.
- **Method**: Blur fill keeps the whole image and fills the empty bands with a blurred copy (posters); Smart crop keeps the most detailed part (fanart); Centre crop; Solid fill. Up to 3 % is simply stretched.
- **Size**: the tier nearest to the image, with its factor and a mark — ✓ recommended, ⚠ soft, ✕ too far (not offered). "Keep current size" fixes the proportions only. For a much bigger image use **Find a better one online**.
- **AI upscale** (optional): **Download upscaler (about 45 MB)…** installs Real-ESRGAN (checked against its SHA-256) and tests it once; it needs a Vulkan graphics card. ×2 is recommended, up to ×4 allowed — check the preview: AI may invent detail.
- **folder.jpg**: "Also copy the result to folder.jpg" is ticked when folder.jpg is the same picture as the poster. When it is a different picture, "Also fix folder.jpg (a different picture: fixed on its own, not replaced)" is offered instead.
### Many images at once
Select several movies, or use **Tools → Artwork → Fix Image Proportions / Size…** for every movie with an image warning.
- A preview lists every image and its fix. Only ✓ sizes are used.
- When the AI upscaler is installed and tested, the bulk fix offers it: then sizes up to ×2 are used too (slower).
- You can minimise the window while it runs; **■ Stop** stops it.
- Skipped images are counted with the reason. For skipped posters the end message offers **Replace them online now…** and **Review them one by one…**.

## Replacing low-resolution posters
> New in v0.20.1.
**Tools → Artwork → Replace Low-Resolution Posters…** (all movies) or Right-click → Artwork → **Replace Low-Resolution Posters…** (the selected movies).
1. Choose a size under "Replace posters below": the Health Rules minimum is selected.
2. Look at the preview.
3. Every poster below the size — and every corrupt poster — gets the best online poster that reaches the size, from TMDB (and fanart.tv with a key).
- folder.jpg follows when it was the same picture.
- Movies without a poster are not changed.
- Pause and Cancel work. The run is one entry in Backup History / Undo.

## Reviewing posters one by one
> New in v0.20.1.
**Tools → Artwork → Review Posters One by One…**, Right-click → Artwork → **Review Posters One by One…**, or the end message of the bulk Fix Image Proportions / Size when it skipped posters.
1. Choose which posters (below a size and corrupt, wrong proportions, the selected movies, or the movies the Filter shows) and the size to reach.
2. One window per movie shows the poster now, the online posters in your artwork language order, and the result of the highlighted choice. The poster Replace Low-Resolution Posters would take is highlighted; sizes below the chosen one are shown in yellow.
| Use | writes the highlighted choice (folder.jpg follows when it was the same picture)
| Fix proportions, Upscale (AI) | show the result first; the AI upscaler (up to ×2) runs when you press Use
| Skip | leaves the movie as it is
| Back | shows the previous movie (its change stays; Undo it in Backup History)
| Stop | ends with a count
- The next movie's online posters load while you look at this one.
- Every change of the session is ONE entry in Backup History / Undo.
- The keys are in the Shortcuts tab.

## Artwork language
> New in v0.20.1.
**Settings → Images & Artwork → Artwork language** decides which online images come first everywhere: Fetch Poster/Folder, Fetch Fanart, Fetch Backdrops, Replace All Backdrops, Replace Low-Resolution Posters.
- The language is the library language (the OK? column's language) or a language you choose.
- **Prefer this language**: your language first, then images without text, English, the rest.
- **Only this language**: the Fetch windows then have a "Show all languages" box.
- **Fanart and backdrops: images without text first** is ticked by default.
- Each image in the Fetch windows shows its language (or "no text").

## After an image change: refresh your player
Kodi, Emby, Jellyfin, Plex and Infuse keep a copy of an image. After a replace, the end message says how each of your programs shows the new one:
| Kodi | open the movie's information and choose Refresh
| Emby, Jellyfin | Refresh metadata on the movie with "Replace existing images" ticked
| Plex | Refresh Metadata on the movie
| Infuse | refresh the movie's metadata

## Actor photos
> New in v0.20.1.
The **Actors** column shows where a movie's actor photos are:
| Local | photos in .actors next to the NFO — only Kodi reads them, with its setting "actor thumbnails" on
| Links | photos only as web links in the NFO, which the other programs use
| No info | no actors in the NFO
- **Download Actor Photos…** (**Tools → Artwork** for all movies, Right-click → Artwork for the selected ones) saves the linked photos at full size into .actors (created hidden, as Kodi does). An existing photo is never replaced and the NFO does not change.
- A photo Kodi would not match ("Tom Hanks.jpg" instead of "Tom_Hanks.jpg", another case, a near spelling) is marked ⓘ. Right-click → Artwork → **Rename actor photos for Kodi** fixes the names (Undo puts them back).
- Photos that match no actor are listed in the tooltip only.
- The Health rule "No actor information" is a warning, on only in the Tight preset. Actors without any photo are flagged only when Kodi is ticked: Emby, Jellyfin and Plex download the photos themselves.
- The votes checks ("Missing votes" and the other votes warnings) are skipped, and Auto Repair leaves the votes alone, when the only programs ticked are Emby, Jellyfin or Plex: none of them uses the vote count.
- The collection artwork rule runs only when Kodi is ticked (or nothing is): only Kodi reads artwork from a collection folder.
- The column is visible from the start only when Kodi is ticked (Tools → Choose Columns…).

## Extra artwork
> New in v0.20.1. Information only, never a warning.
The **Extra art** column says how many of clear logo, clear art, disc art, banner, landscape and key art the folder has. It shows ⓘ for:
- a name Kodi does not read (logo.png → clearlogo.png, disc.png / cdart.png → discart.png, thumb.jpg → landscape.jpg);
- a clear logo / clear art / disc art that is not a PNG with transparency;
- an extrafanart folder (no Kodi v20+ skin reads it).
| Rename extra artwork for Kodi | Right-click → Artwork. Offered only when every ticked program reads the new name; Undo puts the old name back.
| Convert extrafanart → fanart1, 2… | Right-click → Artwork, or **Tools → Artwork** for all movies. The images are copied; the extrafanart folder is kept.
"""

TAB_RATINGS = """
# Ratings, Genres & IDs

## Ratings
**Sync Ratings** fetches the rating and the votes from TMDB and / or OMDb (IMDb data) and writes them to the NFO (<rating>, <votes>, Kodi <ratings>) and the XML (<IMDBrating>, <Rating>, <Votes>, <VoteCount>).
- The dialog shows both sources side by side. A rating of 0 or 0 votes counts as no data.
- Several movies: "Apply this choice to all remaining movies" or "Use the source with more votes" (equal votes → average); **Tools → Ratings & Genres → Sync Ratings Online…** fetches first and then shows current → new for every movie.
- When neither source has data, a second dialog asks once for typed values or Skip.
- When TMDB or OMDb cannot be reached, the movie is skipped and listed at the end — never treated as "no rating".
The defaults of the checkboxes: Settings → Ratings.
| ⬤ | found, NFO and XML agree
| ◐ | NFO and XML differ
| ○ | no tag found
| ✕ | the tag is not a number

## Genres
**Normalize Genres** fixes genres in both files:
- Capitalisation, synonyms ("Sci-Fi" → "Science Fiction"), translations (PT, DE, FR, ES, IT, RU, ZH, AR), duplicates and merged tags ("Family/Fantasy").
- It copies the genres to the file that has none and turns <Genres>/<Genre> in an NFO into Kodi <genre> tags.
- Movies without genres get them from TMDB (then OMDb), with a preview first.
- Genres not in Settings → Genres are "custom": keep or delete them, or Right-click → **Add Custom Genre(s) to Settings**.
- **Tools → Ratings & Genres → Normalize Genres…** previews every change.
**Check Genres Against TMDB…** looks up on TMDB the movies that already have genres and an ID, and lists only those whose genres differ (file → TMDB).
- Where: Right-click → Metadata, or **Tools → Ratings & Genres → Check Genres Against TMDB…**.
- Nothing is ticked: each file keeps its genres unless you tick the movie.
- The ticked ones get TMDB's genres (backup first, Undo).
- It needs a TMDB API key.

## Renaming movie folders and files
> New in v0.20.2. Right-click → Metadata → **Rename Folder and Files…** (one movie or a selection) and Tools → NFO & File Names → **Rename Movie Folders and Files — All Movies…**.
The window shows your choices and five examples; they are saved (also in Settings → NFO / XML → Renamer). **Preview all…** lists every "old → new" first; nothing is renamed before you click **Rename**.
- **Only the folder has a pattern:** Title (Year) (default), Title (Year) [Quality], Title (Year) [Quality] [Genre], Title (Year) [IMDb ID], Title (Year) [TMDB ID], Title (Year) [Quality Codec Audio], or your own with fields like {title} ({year}) [{quality}]. A bracket group with an empty field disappears. Options: the original title, "Matrix, The", dots instead of spaces.
- **The files follow the folder:** the video and every file named after it (NFO, <video>-poster.jpg, subtitles, trailer) get the folder's name; parts keep "-cd1", versions keep " - 1080p". movie.nfo, poster.jpg, .actors, extrafanart and sub-folders stay; inside a DVD / Blu-ray folder nothing is renamed.
- The TMDB pattern writes [tmdb-603]: Jellyfin, Emby and Plex all match the movie by it (tested 2026-11-23; Plex ignores [tmdbid-603]). Kodi uses the NFO and finds names with bracket text too.
- Not renamed, with the reason: a name that is taken, two files that would get one name, a Windows-reserved name, a path that would be too long, a folder with several movies, a movie whose ID Verify IDs flagged (for the ID patterns).
- **Watched state:** Plex, Emby and Jellyfin keep it after a rename. **Kodi loses watched marks and resume points of renamed movies** (and shows them twice until Clean library): export them first (Kodi: Settings → Media → Library → Export library). The preview says so for your programs.
- Nothing is copied. Backup History / Undo renames every folder and file back; one movie is renamed completely or not at all.

## Certifications (age ratings)
> New in v0.20.2. Settings → Ratings → Certifications: your countries in order (default: the app language's country and US) and the most values a list keeps (default 3).
Right-click → Metadata → **Certifications…** (one movie or a selection) and Tools → Ratings & Genres → **Apply My Certification Settings — All Movies…** keep only your countries' age ratings, in your order. A preview comes first; a backup comes first; Backup History / Undo puts the files back.
- Every rating tag your files have is written in its own style: <mpaa>, movie.xml <ContentRating> and <MPAARating> get ONE value (Jellyfin and Emby read one; of a list Jellyfin uses only the first), <FullCertifications> / <FormalMPAA> a list up to your maximum, <certification> as it is now. Values of other countries are removed.
- A value your files lack comes from TMDB (theatrical release first), the US value also from OMDb. When none of your countries has one, the US rating is used and the preview says so. A missing tag is added only where the programs read it: <mpaa> in the NFO and <ContentRating> in movie.xml, written like "BR:12".
- No rating in TMDB and IMDb: the tag is left blank and the preview lists the movie. Only ratings of countries you don't accept and nothing online: you choose per movie (or for all) to keep the file's value or leave the tag blank.
- The health rule (on in the Tight preset) warns about a country you don't accept, more values than your maximum, or several values in <mpaa>. A missing rating is not a warning.

## IMDb and TMDB IDs
Which tool for which problem:
| An ID is missing, or is another film's | **Search Sources**
| An ID is not in every tag, or two IDs differ | **Normalize Sources**
| A field holds a wrong value | **Fix Wrong IMDb / TMDB IDs**
| An ID is only in <imdbid> / <tmdbid> | **Add <uniqueid> for Kodi** (Bulk Tools & Auto Repair tab)
| Are these the right film's IDs? | **Verify IMDb/TMDB IDs**
All five are in Right-click → IDs & Sources (the selected movies) and in **Tools → IDs** (all movies).

### Search Sources
Looks the movie up on TMDB by title + year (in English, your library language and the original title).
- Each movie shows the IDs its files hold now and, first, the film behind that ID.
- In **Choose the TMDB entry**, click anywhere on a movie's row to choose it (green border); a double-click applies it.
- **Enter ID…** lets you type an IMDb (tt…) or TMDB ID, shows title, year and poster, then writes both IDs. It also takes an IMDb or TMDB page address, or an IMDb number without tt.
- A wrong IMDb value next to a good TMDB ID is left out (the window says so) and TMDB's IMDb ID is used.
- Films on IMDb but not on TMDB: the first row reads "IMDb tt… — not on TMDB"; **Confirm IMDb** writes the IMDb ID and marks the movie "OK (IMDb only — not on TMDB)", so Verify IDs and Auto Repair stop looking for it.

### Normalize Sources
Fills missing tags, lets you choose between conflicting IDs (titles looked up on TMDB) and asks for an ID where there is none.
- When only one ID is known, every ID write leaves EMPTY tags for the other source (e.g. <tmdbid></tmdbid>), ready to fill by hand — not with **<uniqueid> only** (Settings → Health Rules → NFO).
- Existing values are never blanked.

### Fix Wrong IMDb / TMDB IDs
> New in v0.20.1: a wrong value in an ID field is ONE warning that says what is wrong and, when the file knows it, the right ID.
- For example "IMDb field holds the TMDB number (27759) — the IMDb ID is tt0056800" (Emby writes the right one in its <imdb id="tt…"> line; that line is read), or "IMDb field holds '0056800', which is not a correct IMDb ID — Fix looks the IMDb ID up on TMDB" (a typo, a mix). The same for a TMDB field that holds an IMDb ID.
- Where: the panel's **Fix**, Right-click → IDs & Sources → **Fix Wrong IMDb / TMDB IDs…** (one movie or the selection), **Tools → IDs → Fix Wrong IMDb / TMDB IDs…** (all movies); also in Fix one issue and Auto Repair.
- It replaces only the wrong values, in the ID tags the files already have (no tag added).
- The right ID comes from the same file first and from TMDB otherwise (only when title and year match).
- A preview comes first; the run is one entry in Backup History / Undo.
- Typing the movie's own TMDB number into an IMDb box is refused.

### Verify IMDb/TMDB IDs
Checks on TMDB that the IDs belong to the movie (any title language, year ±1). Nothing is written until you press **Fix…**; a greyed **Fix…** says why.
- The results: OK · IMDb and TMDB point to different films · ID belongs to another film · ID does not exist · NFO and XML disagree · no IDs · **a field holds a wrong ID**.
- **a field holds a wrong ID** (new in v0.20.1): the film is right but a tag holds something else — Fix writes the right ID, no title search.
- A bad result (another film, different films, an ID that does not exist) is also a warning, with Search Sources as its fix.
- The report sorts by any column and saves to .txt or .csv.
- Verify also keeps the movie's TMDB collection (Collections tab).

### Copy Movie Name
**Copy Movie Name** copies the title (it asks when the files hold several).

## Local titles
When NFO <title> and XML <LocalTitle> differ, Right-click → Metadata → **Make titles the same (NFO ↔ XML)…** lets you choose; Auto Repair gives the side that is the original title (or that does not match the folder) the other one.

## Audio, subtitles and language
- **Audio**: FFprobe tracks as LANGUAGE (CHANNELS); hover for codec and bitrate. A track FFprobe reports as UND takes the language from the NFO or the XML when it fits ("POR — from NFO"). Nothing is written.
- **Subtitles**: embedded tracks and external files (e.g. Movie.pt.srt, also in a Subs folder; forced and SDH flags are read). Right-click → **Subtitles…** opens for any movie; **🌐 Open on OpenSubtitles.org** searches it there.
- **Hard-coded subtitles…** marks burned-in subtitles (they cannot be detected): tick the language(s) or type an ISO 639-2 code. The app writes <tag>Hardsub POR</tag> to the NFO and <Tags><Tag>Hardsub POR</Tag></Tags> to the XML; the column shows "Hard: POR".
- The **Language OK** column is Y when the target language (Settings → Language) is in an audio track or a subtitle: read by FFprobe, a subtitle file, a hard-coded mark, or a stream written in the NFO (streamdetails) or movie.xml (MediaInfo). NFO <language> and XML <Language> / <LanguageCode> at the top level do not count: they are the language for metadata downloads.
"""

TAB_BULK = """
# Bulk Tools & Auto Repair

## The Tools menu
**Tools ▾** is in the Movies toolbar. Some tools are at the top level; the others are grouped in submenus (new in v0.20.1).
| Export Movie List… | CSV, TSV, text, Excel or an HTML page ([[Ctrl+Shift+E]], also the **Export…** button)
| Reports ▸ | Library Statistics, Health Status Report, Duplicate Movies Report, Run Improvements Check…, Ignored Folders of the Last Scan…
| Auto Repair — All Movies… | every safe fix in one go (below)
| Fix one issue — All Movies… | one automatic fix on every movie that needs it (below)
| IDs ▸ | Fix Wrong IMDb / TMDB IDs…, Add <uniqueid> for Kodi…, Normalize Sources…, Search Sources…, Verify IMDb/TMDB IDs…
| Ratings & Genres ▸ | Sync Ratings Online…, Normalize Genres…, Check Genres Against TMDB…, Apply My Certification Settings…
| Collections ▸ | Check All Collections Online…, Fix All Collections…, Create All Collection Folders…, Check / Write set.nfo…, Create / Edit set.nfo…, Collection Gaps…
| NFO & File Names ▸ | Rename NFOs for Kodi…, Rename Files for My Programs…, Rename Movie Folders and Files…, Convert movie.xml → NFO…, Remove online artwork links from NFOs…
| Artwork ▸ | Fix Image Proportions / Size…, Replace Low-Resolution Posters…, Review Posters One by One…, Copy poster.jpg → folder.jpg…, Download Actor Photos…, Convert extrafanart → fanart1, 2…, Delete extrafanart Subfolders…
| Backup History / Undo… | every run that changed files (Backups & Undo tab)
| Scan Results ▸ | Save Scan Results…, Open Scan Results…, Recompute Health Status (no rescan), Refresh Icons ([[Ctrl+I]])
| Choose Columns… | show or hide columns
| Manage 'Not a duplicate' marks… | your answers, with Remove
- Inside **IDs**, **Ratings & Genres**, **NFO & File Names** and **Artwork**, each entry works on all movies of all libraries (the line at the top of each submenu says so); inside **Collections**, on all collections. Review Posters One by One asks which posters first.
- When a filter hides rows, the preview says "all N movies in all libraries (the filter shows M)".
- Every tool keeps its keyboard shortcut and its right-click entry.
- Recompute Health Status applies the rules again without reading a file; Refresh Icons redraws every row.

### Full names
Some windows and messages show a tool's full name. They are the same tools:
| IDs | Fix Wrong IMDb / TMDB IDs — All Movies…, Add <uniqueid> for Kodi — All Movies…, Normalize Sources — All Movies…, Search Sources — All Movies…, Verify IMDb/TMDB IDs — All Movies…
| Ratings & Genres | Sync Ratings Online — All Movies…, Normalize Genres — All Movies…, Check Genres Against TMDB — All Movies…
| Reports | Health Status Report — All Movies, Run Improvements Check — All Movies…
| NFO & File Names | Rename NFOs for Kodi — All Movies with a folder-named NFO…, Rename Files for My Programs — All Movies…, Rename Movie Folders and Files — All Movies…, Convert movie.xml → NFO — All Movies without an NFO…, Remove online artwork links from NFOs — All Movies…
| Artwork | Fix Image Proportions / Size — All Movies with Image Warnings…, Replace Low-Resolution Posters — All Movies…, Copy poster.jpg → folder.jpg — All Movies with Differences…, Download Actor Photos — All Movies…, Convert extrafanart → fanart1, 2… — All Movies…, Delete extrafanart Subfolders — All Movies…
| Scan Results | Refresh Icons — All Movies

## Previews before writing
The bulk tools first show what will change. Closing the preview writes nothing; **▶ Run** (or its own name) writes.
- Every run makes one backup folder and ends with a summary that points to **Backup History / Undo**.
- Every run can be cancelled ("Cancelled after k of n; m left out").
- **⏸ Pause** / **▶ Resume** (new in v0.20.1) are in the progress window of Fix one issue, Add <uniqueid> for Kodi, Fix Wrong IMDb / TMDB IDs, Replace Low-Resolution Posters, Download Actor Photos and Convert extrafanart.

## Fix one issue — All Movies
**Tools → Fix one issue — All Movies…** runs ONE automatic fix on every movie that needs it, and nothing else (new in v0.20.1).
1. The window lists the issues one automatic fix can repair, with how many movies have each. The counts come from the last scan and the Health Rules that are on.
2. Pick one and press **Next…**: a preview comes first.
3. **▶ Run** writes. The run can be paused or cancelled and is ONE entry in Backup History / Undo.

## Add <uniqueid> for Kodi
Kodi reads an IMDb / TMDB ID only from a <uniqueid> line. This tool adds that line for every ID that is only in <imdbid> / <tmdbid> (new in v0.20.1).
- Where: **Tools → IDs → Add <uniqueid> for Kodi…** (all movies), or Right-click → IDs & Sources → **Add <uniqueid> for Kodi** (the selected movies).
- Nothing else in the NFO changes, and no internet is needed.
- A movie with two different IDs is left out: run Normalize Sources first.
- The run can be paused or cancelled and is ONE entry in Backup History / Undo.

## Auto Repair
Applies every safe fix in one go. Artwork is never touched.
- Where: **Tools → Auto Repair — All Movies…**, or Right-click → Check & Repair → **Auto Repair** for the selected movies ([[Alt+A]]).
- Before it runs: the window lists the steps this selection needs, each with a tick box and its number of movies. Untick what you do not want (new in v0.20.1).
- A preview (dry run) is offered for a selection too; for All Movies it is ticked from the start.
- A backup comes first. The summary lists fixed, skipped and still failing movies.
The steps, in this order:
1. Escape '&' in the NFO (& → &amp;; Jellyfin ignores an NFO with a bare '&')
2. Write the right IMDb / TMDB ID where a field holds a wrong value (same file first, then TMDB; no tags added)
3. Resolve conflicting IMDb/TMDB IDs with TMDB
4. Look up IMDb/TMDB IDs on TMDB (exact title + year applies automatically, otherwise ask)
5. Copy the IMDb/TMDB ID to the other file
6. Add <uniqueid> for the IDs Kodi cannot read (keeps <imdbid> / <tmdbid>)
7. Add the movie.xml tags the old programs read (<IMDbId>, <TMDbId>, <VoteCount>)
8. Sync rating and votes online (TMDB/OMDb)
9. Normalize genres and sync them between NFO and XML (custom genres kept)
10. Fill genres from TMDB (the TMDB ID is checked first)
11. Fill the year from TMDB (the TMDB ID is checked first)
12. Copy the title between NFO <title> and XML <LocalTitle>
13. Make the local title the same in NFO <title> and XML <LocalTitle>
14. Trim IDs like 'tt0133093/' and remove exact duplicate tags (NFO / XML)
15. Write the collection TMDB lists for the movie (NFO <set>; your own collections are kept)
16. Rename the folder-named NFO so Kodi reads it (<video>.nfo; movie.nfo for discs, multi-part, versions)

## Export Movie List
**Tools → Export Movie List…** ([[Ctrl+Shift+E]]) or the **Export…** button.
- Columns: Basic, Identify (links + outline), Standard, All, or your own choice (the Collection column too).
- Rows: all movies or the current filtered view (in the grouped view: the movies, never the collection rows).
- Formats: CSV comma, CSV semicolon (Excel in CH / DE / PT / FR), tab-separated, plain list, Excel .xlsx, HTML page. A saved file offers "Open it now?".

## The HTML page
> New in v0.20.1: one file that opens offline in any browser — PC, phone or TV.
### Five layouts (you switch them in the page)
| Table + posters | the columns you chose; click a heading to sort, Columns ▾ hides some; poster size off / small / medium / large; hover a poster to see it big; on a phone each row becomes a compact line
| Poster wall | a grid of posters
| Shelves | rows by collection, genre or decade
| Catalogue | a card per movie with plot, director and cast
| Checklist | a two-column list with tick boxes, good for printing
### In every layout
- Search (title, actor, director, year) and filters (genre, decade, collection, rating, resolution, audio language).
- A click opens the movie's details: fanart, plot, cast, links to IMDb / TMDB and a trailer search.
- **What should we watch?** picks a random movie from the filtered ones.
- A line with the number of movies, hours, 4K count and top genres.
- **Media flags**: resolution, HDR, video codec, audio, subtitles — from the scan and the NFO.
- Six **themes**: Classic, Home Theater, Studio, Aurora, Glass, Cinema Gold; light / dark; Print. Home Theater, Studio, Aurora and Glass take their look from popular media-center programs, without their names or logos.
- The page remembers the viewer's layout and theme.
### In the Export window
| Opens with | the layout the page starts with
| Theme, Title, Accent colour | the theme, your own title and accent colour
| Images | **Inside the page** (one file, about 30 KB per poster), **In a folder next to the page** (posters and fanart; send both), **Online links from the NFOs** (the images load from the internet when the page opens) or **None**
| Include | plot, director and cast, ratings, media flags
### Private columns
- **Path, Folder Name and Library are private** (🔒): choosing HTML unticks them, because the page may be shared; tick them again only for yourself. The ticks are remembered separately for HTML and for the other formats.
- Nothing else in the page asks the internet for anything, and no movie text can run as a script.
"""

TAB_COLLECTIONS = """
# Collections

## What a collection is
A collection (Kodi calls it a movie set) groups the movies of a saga — "Harry Potter Collection", "The Matrix Collection".
- The NFO holds it as <set><name>…</name></set>. Kodi groups movies by that **name**, so two spellings make two sets.
- Jellyfin also reads the TMDB collection ID (<set tmdbcolid="…">).
- movie.xml holds the same collection (TMDbCollectionId, CollectionName); MediaClinic reads and writes both files.

## The Collection column and the grouped view
- The **Collection** column (hidden by default, Tools → Choose Columns…) shows the name; the Filter box finds it.
- **Group by collection** ([[Alt+G]]; next to the sort buttons, or Settings → NFO / XML → Collections; off by default) shows each collection as one row — "Harry Potter Collection (8)", the year span, the worst health colour — with its movies under it. Movies without a collection stay single, in your sort order.
- Where a collection row sits: under a text column (Movie Name, Genres…) it sorts by the collection's name; under any other column it stays where its first movie sits.
- A click selects a collection row; its ▸ arrow, a double-click or [[+]] / [[-]] open or close it. Open collections stay open while the app runs.
- Selecting a collection row means its movies for every action ("8 movies selected"); [[Ctrl+A]] selects every movie, also inside closed collections.

## A collection row: its menu and its panel
Right-click a collection row, or use **All actions ▾** in its panel:
| Expand / Collapse | open or close this row; **Expand All / Collapse All** does it for every row
| Select Its Movies | opens the row and selects its movies
| Fix Collection… | see "Fixing collections" below
| Rename / Join Collection… | give a new name, or choose a collection in use to join it: its movies get its name and TMDB ID
| Create Collection Folder… | see "The collection folder" below
| Collection Artwork… | choose the collection's poster and fanart
| Open Collection Folder | opens the collection's folder
| Open Collection on TMDB | the collection's page (**Search Collection on TMDB** when the collection's TMDB ID is not known)
| Check Collection Online | asks TMDB about this collection's movies
The panel shows the collection: its poster (from the collection folder), TMDB ID, years, folder, artwork, overview, its movies and the fixes. Its buttons: **Artwork…**, **Fix Collection…**, **Open Poster**, **Open Fanart**, **Open Folder**, **TMDB** (the collection's page with its movies, or a TMDB search for the name), **Rename / Join…**, **Write set.nfo**, **Edit set.nfo…** (**Create set.nfo…** for your own collection) and **Refresh Collection** (reads the collection folder and its movies again, like Update on a movie).
While the app writes or reads files again, a ring turns on the poster of the movie or collection it is working on, a thin bar moves above the table and the status bar says what it does. It ends with **✓ Done** once the panel shows the new state, or **! Not done** with the reason. The panel's buttons are grey in the meantime.

## One collection, one name
Kodi shows one set per name, so a TMDB collection gets ONE name for all its movies.
- The name is in English, unless MORE THAN HALF of its movies have their local title in one other language (NFO <title>; XML <LocalTitle> when the NFO has none) — then in that language. A title the app cannot match to a TMDB title counts as English.
- **Settings → NFO / XML → Collections → Collection name language** can fix one language for every collection instead (TMDB's name in it, else English).
- The library language is never used for the name. When TMDB has not given the English name yet, the name in your NFOs is kept and **Check All Collections Online…** fetches it.
- The warning, **Fix Collection…** and Auto Repair use the same name. **Fix Collection…** writes it to every movie of the collection (the preview lists them).
- When your own collection is written two ways, Fix writes the name most of its movies use.
- When NFO <title> and XML <LocalTitle> differ, the movie shows **Title mismatch** and its Fix asks which title to keep.
- After any change the table is checked again, so a fixed warning goes away.

## Checking collections online
**Tools → Collections → Check All Collections Online…** (or Right-click → Metadata → Collection ▸ → **Check Collection Online**) asks TMDB which collection each movie belongs to.
- One request per movie, two per collection, again only after 30 days. **Verify IMDb/TMDB IDs** keeps the same data at no extra cost.
- Movies without a TMDB ID, or whose ID Verify IDs flagged, are skipped and counted.
- Scans and Recompute Health never go online.

## The collection rules
Three rules in Settings → Health Rules, all warnings:
| Collection missing or different | TMDB lists a collection the NFO does not have, the NFO names another one, or one collection is written two ways in your library ("written as X here and as Y in 3 other movies — Kodi shows two sets"). On in the Tight preset only.
| Collection folder / poster / fanart missing | the collection artwork rule: only while a collection folder is set and Kodi (or nothing) is ticked. On in the Tight preset only.
| set.nfo missing or with a mistake | Kodi; only with a collection folder; shown on the collection, not on its movies. On in the Medium and Tight presets.
- Your own collections ("Disney", "Oscar winners") are never warned about and never removed.
- A name with no TMDB ID that matches none of TMDB's names counts as yours, also when TMDB lists the movie in a collection; only **Fix Collection…** on that movie, asked by you, replaces it.
- A movie that was not checked online gets no "missing / different from TMDB" warning (its tooltip says so).
- A collection written two ways and a movie.xml that differs from the NFO are found by every scan.

## set.nfo (Kodi's collection information)
> New in v0.20.1. Checked only with a collection folder set and Kodi ticked.
Each collection's folder should hold a set.nfo: title = the collection name in the NFOs, overview in the app's TMDB language.
- A collection whose set.nfo is missing or has a mistake (no title, no overview although TMDB has one, a title other than the name in the NFOs, an overview in another language) shows "⚠ set.nfo" on its row (Group by collection) and in its panel. The movies' own health is unchanged; the Health report lists these collections.
- Creating a collection folder writes its set.nfo at once.
- **Fix Collection…** also takes care of set.nfo: after the names are written it reads the collection folder again and writes a missing set.nfo / fills empty tags. It says "Nothing to change" only when the names and set.nfo are both right. In the collection's panel, the set.nfo warning has a **Fix** button right beside it.
- **Tools → Collections → Check / Write set.nfo…** (one collection: the **Write set.nfo** button in its panel) writes the missing files and fills empty tags. Where a text differs it shows both, and you tick "Use TMDB's" per collection.
- **Create / Edit set.nfo…** (new in v0.20.2; Kodi 22 Piers and later read set.nfo) opens one collection's set.nfo in an editor: **Title** (locked: the collection name in your movies' NFOs, Kodi matches the set by it), **Original title** and **Overview**; other tags in the file (sort title, artwork) are kept. **Edit** is there for every collection that has a set.nfo. **Create** is offered for your own collections: those whose movies TMDB places in no collection, or in several different ones (a collection with one TMDB collection plus movies TMDB lists in none is still that TMDB collection). The collection's folder is made first when it is not there yet. Open it from the collection's panel (for your own collection without set.nfo the panel's **Create…** / **Fix** opens it), its right-click menu, or **Tools → Collections → Create / Edit set.nfo…** (choose the collection). An overview you type is never replaced by Write set.nfo or Fix all.
- A backup comes first, and Backup History / Undo puts the old file back.

## Collection Gaps
> New in v0.20.2. Tools → Collections → **Collection Gaps…** (every collection), or right-click a collection row (that collection, or the collection rows selected with it).
For each TMDB collection it lists the movies TMDB has that your library lacks: **Missing** (released: a release date before today; "You have N of M" counts these) and **Announced, not released yet** (a later date or none: information only). Titles are in the app's TMDB language, the original title in [brackets], with TMDB's release date. Movies never checked online are checked first, and the collections' movie lists are read again when they are older than 30 days (TMDB key needed; Cancel keeps what was fetched).
- A missing movie is looked for in the WHOLE library: first by TMDB ID, then by title + year (±1). The window offers the fix the library allows: **Add to collection** (right TMDB ID, no collection), **Move to this collection…** (it is in another collection; asks first), **Write TMDB ID + collection…** (found by title: shows your movie and TMDB's side by side and writes the TMDB ID, its IMDb ID and the collection only after your OK — a title match can be a remake). A movie without an NFO in use is shown with no fix. A backup comes first; Backup History / Undo puts the files back.
- **I don't want this one** leaves a movie out of the lists and the count (saved in collection_gaps_ignored.json next to the settings); **Show ignored** lists them with **Show it again**.
- At the end, **Ignored Collections (no TMDB ID)**: your own collections, mixed ones (movies of several TMDB collections), collections no longer on TMDB and those not checked online. A collection whose movies are in one TMDB collection, plus movies TMDB lists in none, is that TMDB collection.
- **Save as .txt…** saves the report ("Collection Gaps <date>.txt"). The report names the libraries it compared: a library that is not scanned is not compared, so its movies would show as missing.

## Fixing collections
Right-click → Metadata → **Collection ▸**:
- **Fix Collection…** writes the collection TMDB lists, under the collection's one name (see "One collection, one name" above), with its overview when the NFO has none. Several movies: a preview first. Also **Tools → Collections → Fix All Collections…** and the Auto Repair step.
- **Set Collection…** puts the selected movies in a collection: one in use, your own name, or a TMDB collection found with **Search TMDB** (its TMDB ID and name are written). With its tick box ticked, it then makes the collection folder and opens **Collection Artwork…**.
- **Remove from Collection…** (asks first) is the only action that ever removes a <set>: it says the movies are **not in a collection**.
-- MediaClinic remembers that (no_collection.json), so TMDB's collection is no longer suggested for them while their NFO has no <set>.
-- It also works for a movie TMDB puts in a collection that you don't want.
-- **Set Collection…** puts a movie in a collection again.
- A collection TMDB no longer has: an NFO links a TMDB collection (tmdbcolid) that TMDB no longer lists for the movie, or that no longer exists.
-- **Check All Collections Online…** gives the warning "Collection: '…' no longer exists on TMDB" (or "is not listed by TMDB for this movie").
-- **Fix** runs **Remove from Collection…**.
- **Update** re-reads the NFO: a movie whose <set> you changed moves to its new collection in the grouped view.
In movie.xml:
- Every collection action writes the same collection into movie.xml (TMDbCollectionId and CollectionNumber = the TMDB collection ID, or 0 for none; CollectionName).
- Remove from Collection… sets the IDs to 0 and removes the name.
- An NFO-style <set> block inside movie.xml does not belong there and is removed.
- When movie.xml and the NFO say different collections, the warning "Collection: movie.xml says …" is fixed by **Sync Collection (NFO ↔ movie.xml)…**: the NFO's collection goes to movie.xml; an NFO without one takes movie.xml's.
- <JSONDump> is never changed.
Every NFO is backed up first; **Backup History / Undo** puts it back. Every other byte of the file stays as it was.

## The collection folder (collection artwork)
Kodi reads collection artwork from ONE folder you choose in Kodi: Settings → Media → Videos → **Movie set information folder**.
- Set the same folder in **Libraries…** → **Collection folder** (the same share, e.g. \\\\NAS\\Movies\\Sets or Z:\\Sets).
- Settings → NFO / XML → Collections shows it; ticking **Group by collection** without one asks for it.
- Each collection has a folder named like the collection, with / \\ ? : * " < > | written as _ (Kodi's rule), holding poster.jpg and fanart.jpg.
- **Create Collection Folder…** shows a preview, makes the folder and downloads the poster (library language first) and the fanart from TMDB.
-- Where: Right-click, a collection row, or **Tools → Collections → Create All Collection Folders…**.
-- An existing file is never replaced.
-- A missing TMDB API key, or a collection without a poster or fanart on TMDB, is listed in the result.
-- Your own collections get the folder: choose their images with **Collection Artwork…**.
-- Undo removes what the run created.
- **Collection Artwork…** shows the posters and fanart images of the collection's TMDB collection, or of **The movies of this collection** (their own poster / fanart).
-- Where: Right-click a movie or a collection row, the panel's **Artwork…**, or **Fix** on "Collection artwork: … missing" for one collection.
-- Without a known TMDB collection, **Search TMDB** finds one by name.
-- The posters come 12 per page (4 per row) and the fanart images 9 per page (3 per row): **Next ›** and **‹ Previous** show the other pages, and a chosen image stays chosen.
-- The window keeps the size you give it.
-- Click one poster and one fanart image, then **Save to Folder**: the folder is made when missing; an existing image is replaced only after a backup, so Backup History can undo it.
- A folder that differs only in case is found (Windows, SMB); one that differs in accents is not the same folder for Kodi, and the warning names it.
- When a collection gets a new name (**Fix Collection…**, **Set Collection…**, **Rename / Join Collection…**, Auto Repair), its folder comes along:
-- The files of the old folder move into the folder of the new name, and the empty old folder is removed.
-- When both folders have a poster (or fanart), the old folder's image is kept and the other one goes to replaced\\ inside the folder — nothing is deleted.
-- The folder stays where it is while another movie still uses the old name.
-- Backup History / Undo puts everything back.
- A folder left under another TMDB name of the collection shows **Collection folder: images left in '…'**; its Fix **Move to the Collection Folder** moves the files the same way.
"""

TAB_BACKUPS = """
# Backups & Undo

## Automatic backups
Before the app changes a .nfo, .xml or image file, it copies the original to backup\\backup_<Movie>_<date>_<time>\\ in %APPDATA%\\MediaMetadataClinic (with the settings, so an update keeps them).
- One run (a batch, or one action on one movie) is one backup folder with a manifest.json (where every file came from, which action made it).
- Every NFO / XML write is atomic: a failed write never leaves a half-written file, and the file's encoding, BOM and line endings are kept.
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
| Poster | <video>-poster.jpg/.png, poster.jpg/.png, <video>.tbn, movie.tbn, <stack>-poster.jpg (a multi-part movie: Movie-poster.jpg for Movie-CD1.mkv)
| Fanart | <video>-fanart.jpg/.png, fanart.jpg/.png, <stack>-fanart.jpg
| NFO | movie.nfo, <video>.nfo, <stack>.nfo for a multi-part movie (Movie.nfo for Movie-CD1.mkv + Movie-CD2.mkv; Jellyfin reads movie.nfo instead), and the folder's only NFO whatever its name when it holds <movie> (a release-info .nfo is ignored)
| Extra fanart | fanart1.jpg…, <video>-fanart1.jpg… (the extrafanart folder is for Jellyfin and Emby)
<video> is the video's file name without its extension. The tooltips say which file was found. Fetch Poster/Folder, Fetch Fanart and Copy poster → folder write in the style the folder already uses: a Kodi folder gets <video>-poster.jpg. Copy poster → folder also makes a folder.jpg in a folder that has none. New backdrops follow the same rule.
- **Rename NFO for Kodi…**: Kodi reads "<video>.nfo" or "movie.nfo", not an NFO named after the folder (unless it is the only NFO). It offers both names (the recommended one selected); **Tools → NFO & File Names → Rename NFOs for Kodi…** shows a preview. A name that exists is never overwritten; Undo puts the old name back.
- DVD and Blu-ray folders: a VIDEO_TS or BDMV structure is the movie; VIDEO_TS-poster.jpg, VIDEO_TS.nfo, index-poster.jpg and index.nfo are read too. FFprobe and frames use the largest .VOB / .m2ts file.
- Collections: Kodi's movie set information folder — Collections tab.

## Jellyfin, Emby and Plex
The names the other servers read are found too, after Kodi's:
| Poster | <video>.jpg, cover, default, movie, <video>-cover…
| Fanart | backdrop, background, art
| Extra backdrops | backdrop-1, fanart-1, background-1, art-1
| Pictures | .jpg, .png, .jpeg, .webp, .gif, .bmp
- The poster, folder and fanart tooltips say which servers read the file found. folder.jpg alone counts as the poster (Plex, Jellyfin, Emby and Infuse use it; Kodi does not).
- NFO: Plex reads no NFO; Kodi reads movie.nfo first when "Movies are in separate folders" is on. Two NFOs the servers read (e.g. movie.nfo and <video>.nfo) are a warning: delete the one you do not need. mymovies.xml is shown in the XML tooltip: no current server reads it.
- Other videos are not "Multiple video files": trailers (-trailer), samples, extras (-featurette, -deleted …), the parts of a stack (cd1, part2) and versions ("Movie - 1080p"). The Video tooltip lists them.
"""

TAB_SETTINGS = """
# Settings

**Settings ▾** in the header opens **All Settings…** or one of the tabs; [[Ctrl+S]] opens the Settings window and [[F10]] the Settings ▾ menu.
- **Save & Apply** writes settings.json; a field that is not valid is named and nothing is saved.
- Health rule and image size changes apply at once; Language, Genres or NFO / XML tag changes offer an update scan.
| Editor & FFmpeg | text editor, FFmpeg folder (**Test FFmpeg**; found by itself when it is on the PATH or in a usual install folder), backdrop frame count, parallel scanning (workers; FFprobe processes), optional scraper, "Remember FFprobe results" (each video probed once; a changed video is probed again)
| API Keys | TMDB, OMDb and fanart.tv keys with **Validate** buttons and links to get them; keys are never written to the log
| Browser | the browser for web links
| Language | the ISO 639-1 code of the Language OK column (default PT)
| Improvements | the checks of the Improvements report and the NFO / XML maximum sizes
| Images & Artwork | the artwork language (Prefer / Only, images without text first), minimum quality tier (the same value as Health Rules), 3:4 and 3:2 acceptance, minimum file sizes
| Ratings | the defaults of the Ratings Sync tick boxes
| Genres | the standard genre list, one per line
| NFO / XML | the tag pairs of the Improvements Check; **Collections**: the collection folder (shown here, set in **Libraries…**) and **Group the movie table by collection**
| User Interface | **Interface language** (English, Português (Brasil), Español or Same as Windows; **Restart now** restarts in it), alternating row colours, header tooltips, compact mode, the Repeat line, the Ignored folders window after a scan, dark title bars, "Check for updates at start"
| Health Rules | **Health preset**, **Which programs play your movies?**, the rules in four sections and **Reset to defaults** (details below the table)
| Backup | the size limit, automatic deletion of the oldest backups, **Delete all backup folders**
Health Rules in detail:
- **Health preset** — Easy / Medium / Tight sets every rule at once; Custom after your own changes. A new user starts with Medium, and choosing a preset after your own changes asks first.
- **Which programs play your movies?** — tick every program you use. The ticks set the health mode: NFO only, NFO and movie.xml, or movie.xml only. A change between NFO and movie.xml offers a new scan.
- The rules are in four sections — **General**, **NFO**, **movie.xml** and **NFO ↔ movie.xml comparisons** — each rule with its tick box, threshold and level (error / warning).
- The sections the health mode does not use stay visible but greyed and cannot be changed; their settings are kept for when you switch back.
"""

TAB_SHORTCUTS = """
# Shortcuts

## General
| [[F1]], [[Ctrl+H]] | Help;  [[Ctrl+/]]: Help at this Shortcuts tab
| [[F5]] | Full Scan
| [[Esc]] | cancel a scan; clear the Filter box; close a window (Settings asks first if you changed something)
| [[Ctrl+F]] | go to the Filter box
| [[Alt+O]] | Problems only on / off
| [[Alt+G]] | Group by collection on / off
| [[Ctrl+L]] | Clear All…
| [[Ctrl+S]] | Settings (all tabs)
| [[F10]] | the Settings ▾ menu
| [[Alt+S]], [[Alt+T]], [[Alt+H]] | the Settings, Tools and Help menus
| [[Ctrl+B]] | hide / show the selected-movie panel
| [[Ctrl+I]] | Refresh Icons — All Movies
| [[Ctrl+Shift+E]] | Export Movie List…
| [[Ctrl+Z]] | Backup History / Undo, with the latest change selected (it asks before restoring)
| [[Ctrl+1]] … [[Ctrl+9]] | sort presets 1 to 9

## Working through problems
| [[F3]], [[Shift+F3]] | the next / previous movie with a warning or an error
| [[Alt+X]] | the ⚠ Fix issues menu of the selected movie
| [[Alt+A]] | Auto Repair for the selected movies (with a dry run)
Tip: F3, Alt+X, F3, Alt+X … fixes a library from the keyboard.

## The selected movie(s)
| [[Alt+P]] | Fetch Poster/Folder (several movies: one window after another)
| [[Alt+I]] | Fix Image Proportions / Size
| [[Alt+F]] | Fetch Fanart
| [[Alt+B]] | Fetch Backdrops
| [[Alt+R]] | Sync Ratings Online
| [[Alt+D]] | Search Sources (find missing IDs)
| [[Alt+V]] | Verify IMDb / TMDB IDs
| [[Ctrl+O]] | open the movie's folder
| [[Ctrl+E]] | open the movie's .nfo (the status bar says when there is none)
| [[Ctrl+R]] | Update (no FFprobe);  [[Ctrl+Shift+R]]: Update with FFprobe
| [[Ctrl+C]] | copy "Title (Year)", one per line;  [[Ctrl+Shift+C]]: copy the folder paths
The shortcuts of the movie table work while the Movies part is shown and the focus is not in a text box.

## In the Fetch windows
| Arrow keys | choose an image
| [[Enter]] | use it
| [[Ctrl+Enter]] | use it without the confirmation; the next selected movie's window opens
| [[Esc]] | close (Done)

## In Review Posters One by One
| Arrow keys, [[Home]], [[End]] | choose an online poster
| [[PageUp]], [[PageDown]] | the previous / next page of online posters
| [[Enter]], double-click | use the highlighted choice; the next movie opens
| [[S]] | skip this movie
| [[Backspace]] | back to the previous movie
| [[F]] | Fix proportions (the result is shown first)
| [[U]] | Upscale (AI) (the result is shown first)
| [[Esc]] | stop (asks once)

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
Tools → Scan Results → Recompute Health Status (no rescan) — also done at every start.
### Source shows ✕ although the movie has an ID
Some tags are empty (e.g. <TMDB></TMDB>) while others hold the ID; Normalize Sources fills them.
### Backdrop extraction makes no files
Check FFmpeg in Settings → Editor & FFmpeg (**Test FFmpeg**) and raise **Per-frame timeout** in the Extract Backdrop(s) window.
### Excel opens the CSV in one column
Export with "CSV — semicolon separated" or as .xlsx.
### Collections show no warning
Run **Tools → Collections → Check All Collections Online…** first (the rules need TMDB's collection data); the collection artwork rule needs the collection folder (Libraries…).

## When TMDB or OMDb do not answer
IMDb is never asked directly: IMDb ratings come through OMDb, IMDb IDs through TMDB. The message names the cause and what to do.
- TMDB "too many requests": wait about a minute.
- OMDb daily limit (1,000 requests on a free key): try again in a few hours; TMDB still works.
- Key rejected: Settings → API Keys → Validate. No connection: check the internet and try again.
- In a batch the message comes once, with "Pause this run", "Continue with the other source" and "Cancel". A paused service shows "⚠ … paused" in the status bar (click it to see why or to end the pause); the next action asks "Try anyway?".
- A network error stops a run and keeps what was done; a file that cannot be written (locked, read-only) fails that movie only; a read-only file is named and the app offers to clear read-only (one movie: then it tries again; a batch: one question, then run it again).

## Logs
**Help → Open Logs Folder** opens logs\\ with app.log selected. Every unexpected error is written there (API keys never): attach it to a bug report.
**Help → Copy Diagnostic Info…** shows a short report for a bug report: the version, the system, the preset, the programs ticked, the counts of each warning and the last warnings in app.log. It holds no folder names or paths. Click **Copy** and paste it into your message.

## Updates
**Help → Check for Updates…** (or the button in About) asks GitHub for the latest release; nothing else is sent.
- A new version can be opened on GitHub or skipped.
- The Windows program can also download and install it (a Linux build only opens the download page).
-- The package is checked against its SHA-256 and unpacked next to the current version, which is never changed.
-- Your settings, results and backups are kept (they live in %APPDATA%).
- Settings → User Interface → "Check for updates at start" (off by default) checks once a day and only shows a link in the status bar.

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


### NEW v0.20.0 UI1e — the Help in the interface language ###
# HELP_TABS above is the English Help (and the source of docs/help, tools/make_help_docs.py).  The Portuguese
# (Brazil) and Spanish Help live in help_pt_br.py / help_es.py with the SAME topics in the SAME order and the same
# markup line by line (the self-test compares them), so a topic index (open_help(tab=…), the Help menu, About =
# the last tab) means the same topic in every language.
def tabs(lang=None):
    """The Help topics [(label, text)] in the interface language (*lang*: "en", "pt_BR", "es"; default: current)."""
    lang = lang or _i18n.current()
    if lang == "pt_BR":
        import help_pt_br as _m
    elif lang == "es":
        import help_es as _m
    else:
        return HELP_TABS
    return _m.HELP_TABS


def about_label(lang=None):
    """The About tab's name in the interface language."""
    lang = lang or _i18n.current()
    if lang == "pt_BR":
        import help_pt_br as _m
    elif lang == "es":
        import help_es as _m
    else:
        return ABOUT_LABEL
    return _m.ABOUT_LABEL
