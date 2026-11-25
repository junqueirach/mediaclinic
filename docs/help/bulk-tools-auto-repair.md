# Bulk Tools & Auto Repair

# Bulk Tools & Auto Repair

## The Tools menu
**Tools ▾** is in the Movies toolbar. Some tools are at the top level; the others are grouped in submenus (new in v0.20.1).
| Export Movie List… | CSV, TSV, text, Excel or an HTML page (`Ctrl+Shift+E`, also the **Export…** button)
| Reports ▸ | Library Statistics, Health Status Report, Duplicate Movies Report, Run Improvements Check…, Ignored Folders of the Last Scan…
| Auto Repair — All Movies… | every safe fix in one go (below)
| Fix one issue — All Movies… | one automatic fix on every movie that needs it (below)
| IDs ▸ | Fix Wrong IMDb / TMDB IDs…, Add <uniqueid> for Kodi…, Normalize Sources…, Search Sources…, Verify IMDb/TMDB IDs…
| Ratings & Genres ▸ | Sync Ratings Online…, Normalize Genres…, Check Genres Against TMDB…, Apply My Certification Settings…
| Collections ▸ | Check All Collections Online…, Fix All Collections…, Create All Collection Folders…, Check / Write set.nfo…, Create / Edit set.nfo…, Collection Gaps…
| NFO & File Names ▸ | Rename NFOs for Kodi…, Rename Files for My Programs…, Rename Movie Folders and Files…, Convert movie.xml → NFO…, Remove online artwork links from NFOs…
| Artwork ▸ | Fix Image Proportions / Size…, Replace Low-Resolution Posters…, Review Posters One by One…, Copy poster.jpg → folder.jpg…, Download Actor Photos…, Convert extrafanart → fanart1, 2…, Delete extrafanart Subfolders…
| Backup History / Undo… | every run that changed files (Backups & Undo tab)
| Scan Results ▸ | Save Scan Results…, Open Scan Results…, Recompute Health Status (no rescan), Refresh Icons (`Ctrl+I`)
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
- Where: **Tools → Auto Repair — All Movies…**, or Right-click → Check & Repair → **Auto Repair** for the selected movies (`Alt+A`).
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
**Tools → Export Movie List…** (`Ctrl+Shift+E`) or the **Export…** button.
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
