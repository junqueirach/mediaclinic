# Bulk Tools & Auto Repair

# Bulk Tools & Auto Repair

## The Tools menu
| Export Movie List… | CSV, TSV, text or Excel (`Ctrl+Shift+E`, also the **Export…** button)
| Choose Columns… | show or hide columns
| Ignored Folders of the Last Scan… | the folders the last scan did not add
| Library Statistics | health, quality, genres, decades, libraries
| Duplicate Movies Report | the same ID, or title + year, elsewhere
| Manage 'Not a duplicate' marks… | your answers, with Remove
| Recompute Health Status (no rescan) | the rules again, no file read
| Save / Open Scan Results… | a scan to or from a file (**Save Scan Results…**, **Open Scan Results…**)
| Backup History / Undo… | every run that changed files (Backups & Undo tab)
| Refresh Icons — All Movies | redraws every row (`Ctrl+I`)
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
12. Trim IDs like 'tt0133093/' and remove exact duplicate tags (NFO / XML)
13. Write the collection TMDB lists for the movie (NFO <set>; your own collections are kept)
14. Rename the folder-named NFO so Kodi reads it (<video>.nfo; movie.nfo for discs, multi-part, versions)

## Export Movie List
- Columns: Basic, Identify (links + outline), Standard, All, or your own choice (the Collection column too).
- Rows: all movies or the current filtered view (in the grouped view: the movies, never the collection rows).
- Formats: CSV comma, CSV semicolon (Excel in CH / DE / PT / FR), tab-separated, plain list, Excel .xlsx. A saved file offers "Open it now?".
