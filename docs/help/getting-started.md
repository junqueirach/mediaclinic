# Getting Started

# Getting Started

## What this app does
Metadata & MediaClinic audits and repairs Kodi, Jellyfin, Emby and Plex movie libraries. It scans your library folders, checks every artwork file, metadata file and video, and shows a colour-coded health table, so you see at a glance what is missing or broken. Most problems can be fixed from the same table.

## How a movie folder looks
One folder = one movie. A complete folder holds:
- the video, e.g. **Movie Name (2001).mkv** (or .mp4, .avi …)
- the Kodi metadata, **<video>.nfo** or **movie.nfo**
- **movie.xml**, a legacy format (optional): only Emby's XML plugin reads it, and Media Center Master writes it; Kodi, Jellyfin and Plex do not read it
- **poster.jpg** (portrait, 2:3) and **fanart.jpg** (wide, 16:9)
- **folder.jpg**, an identical copy of the poster (optional: every server reads poster.jpg)
- extra backgrounds: **backdrop.jpg**, **backdrop1.jpg** … or Kodi's **<video>-fanart1.jpg** …
- external subtitles such as **Movie Name.pt.srt** (optional)
The Media Servers tab lists every name the servers read.

## First run
1. Click **Browse…** and choose your movie folder. Add more folders later with **Libraries…**.
2. Click **Full Scan** (`F5`). The table fills in phases: folders, images, metadata, then video — with FFprobe when the **FFprobe** switch in the status bar is On.
3. Each row shows the health of one movie: green = no rule triggered, yellow = warnings, red = errors.
4. Select a movie: the panel on the right shows its poster, its issues with a **Fix** button each, its files and the common actions.
5. The last scan is saved and restored at the next start.
6. At the first start the app asks once: **Which program plays your movies?** This is the **health mode**: it decides which files MediaClinic checks and repairs.
- **Kodi, Jellyfin, Emby, Plex, Infuse…** (recommended): the .nfo files, as tinyMediaManager, Radarr or MediaElch make them. movie.xml is ignored (not read, not checked, not written; no .xml column).
- **The above + old Windows media centers** (MediaBrowser, Media Center Master): the NFO and movie.xml, every check and fix of both.
- **Only old Windows media centers**: movie.xml only. The NFO is ignored (not read, not checked, never written; no .nfo column). Title, year, rating, IDs and genres come from movie.xml, and the fixes write movie.xml. Collections, Rename NFO for Kodi and the **&** fix work on the NFO, so they are not offered.
Change it later in **Settings → Health Rules → Health mode**; the app then offers a new scan.
7. In the mode **The above + old Windows media centers**, a library where no movie has a movie.xml gets one more question after its scan: **NFO-only library?** **Yes, NFO only** switches the XML checks off for that library alone (no "Missing XML file" error, no NFO / XML comparison; the XML column shows —). Change it later in **Libraries…** with the **NFO only** button.

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
| backup/ | the automatic backups (same folder; moved there from the program folder once — an update keeps them)
