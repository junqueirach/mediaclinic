# Health & Fixing Issues

# Health & Fixing Issues

## How health works
Every condition that can turn a row red (errors) or yellow (warnings) is a rule in **Settings → Health Rules**, with a checkbox and sometimes a level or a threshold. **Tools → Recompute Health Status (no rescan)** applies changed rules at once (also done at every start).
- Hover the Movie Name for every reason of a movie; the selected-movie panel lists them too.
- **Tools → Health Status Report — All Movies** writes them all, with the most common issues first and the movies whose collection was not checked online.
- **Tools → Run Improvements Check — All Movies…** lists metadata that could be better (tag pairs of **Settings → NFO / XML**, file sizes).
- **Tools → Library Statistics**: health, quality, genres, decades, libraries.

## Fix issues
The right-click menu starts with the movie's name (or "N movies selected") and its number of issues, then **⚠ Fix issues**: the real problems of the selection, each linked to the action that fixes it — with several movies, how many movies have each problem (the action runs on just those). The selected-movie panel has the same list as **Fix** buttons.
| Poster / folder.jpg missing | Fetch Poster/Folder…
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
Also `Shift+F10` or the Menu key, at the selected row. An action that does not apply stays in its place, greyed, with the reason ("missing", "one movie only" …).
- **Repeat**: the last action again on the current selection (Settings → User Interface can hide this line).
- **Open Folder** (`Ctrl+O`), **Play Video**, **Edit NFO** (`Ctrl+E`).
- **Artwork**: open the images — the entry names the file found, e.g. **Open poster.jpg**, **Open folder.jpg**, **Open fanart.jpg** (greyed **Open poster** when there is none or several movies are selected); **Fetch Poster/Folder**, **Fetch Fanart**, **Fetch Backdrops**, **Replace All Backdrops**, **Extract Backdrop(s)**, **Copy poster.jpg → folder.jpg**, **Fix Image Proportions / Size…**.
- **Metadata**: **Open .nfo**, **Open movie.xml**, **[!] NFO errors** / **[!] XML errors**, **Make titles the same (NFO ↔ XML)…**, **Rename NFO for Kodi…**, **Collection ▸**, **Sync Ratings from IMDb / TMDB**, **Normalize Genres**, **Check Genres Against TMDB…**, **Remove online artwork links from the NFO…**, **Add Custom Genre(s) to Settings**.
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
| Language | the file the value came from (movie.xml or the NFO) in your editor
| Video, Quality | plays the video
| Subtitles | the subtitle tracks
| Library | the library folder
| Collection | the .nfo file in your editor

## Health rules worth knowing
- "Missing folder image" is off when the health mode is NFO only (every server shows poster.jpg without a folder.jpg); every preset turns it on in the modes with movie.xml. "Poster and folder image are different" is off by default.
- "Missing clear logo / disc art" (clearlogo.png, logo.png, disc.png, discart.png, cdart.png, also as <video>-clearlogo.png …) is on only in the Tight preset: Kodi's own skin hardly uses them, some other skins do. MediaClinic does not download them yet.
- "Not read by Infuse: movie.nfo (needs <video>.nfo)" — with programs ticked at the top of Health Rules, a warning when the NFO, the poster or the fanart has a name one of them does not read (Infuse, checked on an Apple TV with its "Prefer Local Artwork" and "Prefer Local Metadata" settings on, reads <video>.nfo, never movie.nfo; for artwork it reads <video>-poster.jpg, <video>.jpg, poster.jpg, folder.jpg, <video>-fanart.jpg and fanart.jpg, and with none of those it shows any other picture in the folder as the poster). Emby was checked on a real server: it reads <video>.nfo and movie.nfo, the NFO's collection and every usual poster and fanart name, so a Kodi-style folder works in Emby as it is. Jellyfin was checked too and reads the same; it makes collections from the NFO only when its library option "Automatically add to collection" is on (Dashboard → Libraries → Manage library; off by default) and two or more movies share the collection name. Plex was checked on a real server: it reads every usual poster and fanart name (poster, folder, cover, <video>, <video>-poster, fanart, backdrop, background, .jpg or .png) but no NFO and no collection from it; with only Plex ticked, a pop-up asks once whether to switch the NFO and collection checks off (change it later with the tick box under the programs). The ticks also switch off what those programs do not use: Infuse alone has no folder.jpg, extra backdrop or collection checks, and the Kodi-only NFO checks run only when Kodi is ticked. Fetch writes new artwork in the name every ticked program reads; when there is none it writes one file for each.
- **Rename Files for My Programs…** (right-click, ⚠ Fix issues, or Tools → **Rename Files for My Programs — All Movies…**) is the fix for that warning: it gives the NFO, the poster and the fanart the names every ticked program reads (e.g. movie.nfo → <video>.nfo for Infuse). A preview lists every rename first; a backup comes first and Backup History can undo it. The video is never renamed, an existing file is never overwritten, and a folder with two NFOs, a DVD / Blu-ray folder or a pair of programs with no common name is listed and left alone.
- **Convert movie.xml → NFO…** (right-click on a movie that has a movie.xml and no NFO, or Tools → **Convert movie.xml → NFO — All Movies without an NFO…**) is for a library moving from MediaBrowser / Media Center Master to Kodi, Plex, Jellyfin, Emby or Infuse: it makes an NFO from each movie.xml (titles, year, release date, runtime, plot, rating and votes, IDs, genres, studios, director, writers, actors, collection) in the name the ticked programs read (<video>.nfo when a program is ticked; movie.nfo when none is, or for a DVD / Blu-ray folder, a multi-part movie or a folder without a video). movie.xml is not changed; a preview comes first and Backup History can undo it (it removes the new NFOs).
- "NFO has online artwork links" is off in every preset. **Remove online artwork links from the NFO…** (right-click → the NFO part, or Tools → … — All Movies…) removes the web links (<thumb> / <fanart><thumb>) only for the artwork the folder has as a file; it counts them first, backs up each NFO and keeps actor images, collection artwork and every other tag.
- "NFO has an unescaped '&'": Kodi reads such an NFO, but Jellyfin may ignore the whole file. Auto Repair writes '&amp;'. An IMDb / TMDB ID only in <imdbid> / <tmdbid> is a warning too: Kodi reads <uniqueid>, so Auto Repair adds it (and keeps the other tags); a <premiered> date counts as the year. In movie.xml, an ID or the votes only in <IMDB_ID> / <TMDB> / <Votes> is a warning too: the old programs read <IMDbId> / <TMDbId> / <VoteCount>, and Auto Repair adds them. "ID tags written in the NFO" (under these NFO rules) chooses how an IMDb / TMDB ID is written: every tag style (<id>, <uniqueid>, <imdbid>, <id moviedb>, so every program finds it; the default) or <uniqueid> only (Kodi, Jellyfin and Emby read it). With <uniqueid> only, the ID tags the NFO already has are still corrected, no other ID tag and no empty placeholder tag is added; movie.xml is not affected.
- Content checks: IDs that are not valid, a year out of range, a runtime or votes that is not a number, a rating above 10, a tag written twice, an empty <title> / <plot> (on only in the Tight preset).
- "Title mismatch" names both local titles; "When Repair All cannot tell the right local title" chooses what Auto Repair does then.
- A missing ID: "Movie with ONE source only" and "Movie with NO source" can each be an error, a warning or off.
