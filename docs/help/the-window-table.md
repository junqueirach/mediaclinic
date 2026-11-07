# The Window & Table

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
- **Hide ›** or `Ctrl+B` hides the panel; the slim **‹** strip at the right edge shows it again. Drag the divider to change its width; a double-click on the divider resets it. Both are remembered.

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
| Language | The top-level XML <Language>: the language for metadata downloads on Jellyfin and Emby. Empty is normal.
| Video, Video Size, Quality | container, size and resolution class.
| Audio | FFprobe audio tracks, e.g. EN (5.1), PT (2.0).
| Language OK | Y / N: the target language in audio or subtitles (the heading shows the code, e.g. "PT OK?").
| Subtitles | embedded tracks (FFprobe) and external files.
| Library | the library (root folder). Hidden by default.
| Collection | the movie's collection (NFO <set>). Hidden by default.
**Tools → Choose Columns…** shows or hides columns; the choice is kept. Drag a heading edge to resize a column, double-click a heading to fit it, or use **↔ Auto-size Columns**. **↺ Default Widths** puts every column back to its original width after a resize went wrong. In the grouped view the Year column widens for a collection's years ("1979–1986") and gets your width back when you ungroup. Widths, window sizes and positions are remembered.

## Filter
Type in the **Filter** box (`Ctrl+F`) to keep the movies whose name, year, genre, language, quality, health status, health reason or collection matches — "backdrops" lists every backdrop issue. `Esc` clears it.
- **Problems only** hides the green rows.
- The library box next to **Libraries…** shows one library or all of them.
- "n of m shown" counts the movies the filter keeps.

## Sorting
The sort row reads "Sort by [column] [direction]"; **+ then by** adds up to two more levels (✕ removes one). The direction is said in words — A → Z, Newest first, High → low, Worst first, Errors first … — click it to turn it round.
- Every column can be used, plus **Health** and **Number of issues** (the first two entries) and **Date added** (NFO <dateadded>, XML <DateAdded>, else the creation date of the video or the folder).
- Click a column heading to sort by it (again = reversed); Shift+click adds it as the next level. ▲1 / ▼2 in the headings show the levels.
- Empty values (no rating, no poster, no date) go last, unless a level asks for empty first (the preset Missing metadata does); equal values stay in Movie Name order.
- **★ Presets ▾**: Problems first, Worst artwork first, Missing metadata, Best rated, Biggest files, By library, By collection name (collection A → Z, then year, then movie name; movies without a collection last), and your own (**Save current sort as preset…**; rename or delete them in the same menu). `Ctrl+1` … `Ctrl+9` apply presets 1 to 9.
- **↺ Update View** sorts and filters again, so movies you just fixed move to their place.
- The sort is kept after a scan and after a restart.

## Duplicates
Movies that share an IMDb ID, a TMDB ID, or a title + year are a "Possible duplicate" (the same title + year with two different IMDb IDs are not: a remake or a namesake). Right-click → **✔ Not a duplicate…** remembers your answer in not_duplicates.json, so the warning stays gone; a new third copy is still found. **↺ Undo 'not a duplicate'** takes it back; **Tools → Manage 'Not a duplicate' marks…** lists every pair. **Tools → Duplicate Movies Report** lists them all.
