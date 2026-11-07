# Backups & Undo

# Backups & Undo

## Automatic backups
Before the app changes a .nfo, .xml or image file, it copies the original to backup\backup_<Movie>_<date>_<time>\ in %APPDATA%\MediaMetadataClinic (with the settings, so an update keeps them). One run (a batch, or one action on one movie) is one backup folder with a manifest.json (where every file came from, which action made it). Every NFO / XML write is atomic: a failed write never leaves a half-written file, and the file's encoding, BOM and line endings are kept.
> If a backup cannot be made, the change does not happen — the movie is reported as failed.

## Backup History / Undo
**Backup History / Undo…** (in the header and in Tools) lists the runs, newest first. **Restore this run** puts the files back:
- your current files are backed up first, so an undo can be undone;
- files changed after the run are listed and can be skipped;
- a renamed NFO gets its old name back, and files a run created (collection artwork) are removed;
- the rows refresh.
Runs removed by the size cleanup stay listed as "removed by the size cleanup".

## Size limit
Settings → Backup: the maximum size of the backup folder and "Delete the oldest backups automatically" (on by default). Runs of this session and of the last 14 days are never deleted automatically; the cleanup is written to a log. A run larger than the limit is announced before it starts. **Delete all backup folders** empties the folder.
