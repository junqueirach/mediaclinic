# Scans & Libraries

# Scans & Libraries

## Scans
| Full Scan | re-reads every movie of the libraries in scope (`F5`).
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
- Movies can sit deeper: a folder that holds only other folders (Single Movies / HD / <movie>, Boxsets / <saga> / <movie>) is searched, down to 5 levels below the library. Every movie keeps its library in the Library column.

## Ignored folders
A scan adds a row only for movie folders. These are not added:
- TV series: tvshow.nfo, Season folders or episode files (S01E02, 1x02). Series support comes in v0.22.
- Folders of folders more than 5 levels below the library (shallower ones are searched for movies).
- Folders with several separate videos: give each movie its own folder.
- Folders with no video, NFO or XML, system folders ($RECYCLE.BIN, @eaDir …) and folders that could not be read.
A folder with movie metadata is always a movie, and so is a folder with one video and no NFO. After a scan the **Ignored Folders of the Last Scan…** window opens when something was left out (filter, sort, double-click to open, **Export to TXT…**, **Copy All**); turn that off with "Show this window after a scan". **Tools → Ignored Folders of the Last Scan…** opens it at any time.

## Updating single movies
Right-click → **Update (no FFprobe)** (`Ctrl+R`) re-reads the movie or the selection; **Update (with FFprobe)** (`Ctrl+Shift+R`) also probes the video (one movie: a status line; several: a progress window with Cancel). After every repair, sync, fetch or delete the affected rows refresh by themselves.

## Movies that disappear
When a movie folder was deleted, Update or the automatic refresh removes its row. Right-click → **Remove from list** drops rows without touching any file; the next scan brings back movies that still exist.

## Saving and loading scans
- The last scan is saved in last_results.json and loaded in the background at the start ("⏳ Loading last scan…"); the health rules are applied again, so changed rules never leave old reasons behind.
- **••• → Save Scan Results…** / **Open Scan Results…** write a scan to a file or load one.
- **••• → Clear All…** (`Ctrl+L`) empties the table (it asks first). No movie file changes; the saved last scan is emptied too, so the rows do not come back at the next start.
