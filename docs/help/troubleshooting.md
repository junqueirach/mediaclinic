# Troubleshooting

# Troubleshooting

## Common questions
### The Audio column is empty
Switch FFprobe On and run Update (with FFprobe).
### A health reason no longer applies
Tools → Recompute Health Status (no rescan) — also done at every start.
### Source shows ✕ although the movie has an ID
Some tags are empty (e.g. <TMDB></TMDB>) while others hold the ID; Normalize Sources fills them.
### Backdrop extraction makes no files
Check FFmpeg in Settings → Editor & FFmpeg (**Test FFmpeg**) and raise **Per-frame timeout** in the Extract Backdrop(s) window.
### Excel opens the CSV in one column
Export with "CSV — semicolon separated" or as .xlsx.
### Collections show no warning
Run **Tools → Check Collections Online — All Movies…** first (the rules need TMDB's collection data); the collection artwork rule needs the collection folder in Settings → NFO / XML.

## When TMDB or OMDb do not answer
IMDb is never asked directly: IMDb ratings come through OMDb, IMDb IDs through TMDB. The message names the cause and what to do.
- TMDB "too many requests": wait about a minute.
- OMDb daily limit (1,000 requests on a free key): try again in a few hours; TMDB still works.
- Key rejected: Settings → API Keys → Validate. No connection: check the internet and try again.
- In a batch the message comes once, with "Pause this run", "Continue with the other source" and "Cancel". A paused service shows "⚠ … paused" in the status bar (click it to see why or to end the pause); the next action asks "Try anyway?".
- A network error stops a run and keeps what was done; a file that cannot be written (locked, read-only) fails that movie only.

## Logs
**Help → Open Logs Folder** opens logs\ with app.log selected. Every unexpected error is written there (API keys never): attach it to a bug report.

## Updates
**Help → Check for Updates…** (or the button in About) asks GitHub for the latest release; nothing else is sent. A new version can be opened on GitHub or skipped. The Windows program can also download and install it: the package is checked against its SHA-256 and unpacked next to the current version, which is never changed. Your settings, results and backups are kept (they live in %APPDATA%). Settings → User Interface → "Check for updates at start" (off by default) checks once a day and only shows a link in the status bar.

## One window at a time
MediaClinic runs once: starting it again brings the running window to the front.
