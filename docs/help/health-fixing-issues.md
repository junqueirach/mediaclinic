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
Also `Shift+F10` or the Menu key, at the selected row. An action that does not apply stays in its place, greyed, with the reason ("missing", "one movie only" …).
- **Repeat**: the last action again on the current selection (Settings → User Interface can hide this line).
- **Open Folder** (`Ctrl+O`), **Play Video**, **Edit NFO** (`Ctrl+E`).
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
| Language | the file the value came from (movie.xml or the NFO) in your editor
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
