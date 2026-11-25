# Getting Started

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
2. Click **Full Scan** (`F5`). The table fills in phases: folders, images, metadata, then video — with FFprobe when the **FFprobe** switch in the status bar is On.
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
| settings.json | all settings (%APPDATA%\MediaMetadataClinic)
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
