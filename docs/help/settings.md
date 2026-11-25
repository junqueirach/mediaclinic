# Settings

# Settings

**Settings ▾** in the header opens **All Settings…** or one of the tabs; `Ctrl+S` opens the Settings window and `F10` the Settings ▾ menu.
- **Save & Apply** writes settings.json; a field that is not valid is named and nothing is saved.
- Health rule and image size changes apply at once; Language, Genres or NFO / XML tag changes offer an update scan.
| Editor & FFmpeg | text editor, FFmpeg folder (**Test FFmpeg**; found by itself when it is on the PATH or in a usual install folder), backdrop frame count, parallel scanning (workers; FFprobe processes), optional scraper, "Remember FFprobe results" (each video probed once; a changed video is probed again)
| API Keys | TMDB, OMDb and fanart.tv keys with **Validate** buttons and links to get them; keys are never written to the log
| Browser | the browser for web links
| Language | your languages: the main ISO 639-1 code (default PT) and the others you add
| Improvements | the checks of the Improvements report and the NFO / XML maximum sizes
| Images & Artwork | the artwork language (Prefer / Only, images without text first), minimum quality tier (the same value as Health Rules), 3:4 and 3:2 acceptance, minimum file sizes
| Ratings | the defaults of the Ratings Sync tick boxes
| Genres | the standard genre list, one per line
| NFO / XML | the tag pairs of the Improvements Check; **Collections**: the collection folder (shown here, set in **Libraries…**) and **Group the movie table by collection**
| User Interface | **Interface language** (English, Português (Brasil), Español or Same as Windows; **Restart now** restarts in it), alternating row colours, header tooltips, compact mode, the Repeat line, the Ignored folders window after a scan, dark title bars, "Check for updates at start"
| Health Rules | **Health preset**, **Which programs play your movies?**, the rules in four sections and **Reset to defaults** (details below the table)
| Backup | the size limit, automatic deletion of the oldest backups, **Delete all backup folders**
Health Rules in detail:
- **Health preset** — Easy / Medium / Tight sets every rule at once; Custom after your own changes. A new user starts with Medium, and choosing a preset after your own changes asks first.
- **Which programs play your movies?** — tick every program you use. The ticks set the health mode: NFO only, NFO and movie.xml, or movie.xml only. A change between NFO and movie.xml offers a new scan.
- The rules are in four sections — **General**, **NFO**, **movie.xml** and **NFO ↔ movie.xml comparisons** — each rule with its tick box, threshold and level (error / warning).
- The sections the health mode does not use stay visible but greyed and cannot be changed; their settings are kept for when you switch back.
