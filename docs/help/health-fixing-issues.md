# Health & Fixing Issues

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
- the keyboard: `Alt+X`.
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
| Auto Repair can fix more | Auto Repair

## The right-click menu
Right-click a row, or press `Shift+F10` or the Menu key at the selected row. An action that does not apply stays in its place, greyed, with the reason ("missing", "one movie only" …).
- **At the top**: the movie's name and its issues, **✔ Not a duplicate…** (several movies: **Not duplicates of each other**), **Repeat** (the last action again on the current selection; Settings → User Interface can hide this line) and **⚠ Fix issues**.
- **Open Folder** (`Ctrl+O`), **Play Video**, **Edit NFO** (`Ctrl+E`).
- **Artwork**
-- Open: the entry names the file found, e.g. **Open poster.jpg**, **Open folder.jpg**, **Open fanart.jpg** (greyed **Open poster** when there is none or several movies are selected).
-- Get: **Fetch Poster/Folder**, **Fetch Fanart**, **Fetch Backdrops**, **Replace All Backdrops**, **Extract Backdrop(s)**.
-- Repair: **Copy poster.jpg → folder.jpg**, **Fix Image Proportions / Size…**, **Replace Low-Resolution Posters…**, **Review Posters One by One…**.
-- For Kodi: **Download Actor Photos…**; **Rename actor photos for Kodi**, **Rename extra artwork for Kodi** and **Convert extrafanart → fanart1, 2…** are shown only when the movie has such files.
- **Metadata**
-- Files: **Open .nfo**, **Open movie.xml**, **[!] NFO errors** / **[!] XML errors**.
-- Names: **Make titles the same (NFO ↔ XML)…**, **Rename NFO for Kodi…**, **Rename Files for My Programs…** (with programs ticked), **Convert movie.xml → NFO…** (a movie with a movie.xml and no NFO), **Remove online artwork links from the NFO…**.
-- **Collection ▸** (Collections tab).
-- Ratings and genres: **Sync Ratings from IMDb / TMDB**, **Normalize Genres**, **Check Genres Against TMDB…**, **Add Custom Genre(s) to Settings**.
- **IDs & Sources**: **Search Sources**, **Verify IMDb/TMDB IDs**, **Normalize Sources**, **Fix Wrong IMDb / TMDB IDs…**, **Add <uniqueid> for Kodi**, **Copy Movie Name**.
- **Video & Subtitles**: **Subtitles…**, **Hard-coded subtitles…**, **Extract Backdrop(s)**.
- **Open online**: **Open on IMDb**, **Open on TMDB**, **Open on Fanart.tv**, **Open on OpenSubtitles.org**, **Open in Scraper**.
- **Check & Repair**: **Health Status Report**, **Run Improvements Check**, **Auto Repair**.
- **Update**: **Update (no FFprobe)** (`Ctrl+R`), **Update (with FFprobe)** (`Ctrl+Shift+R`).
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
