# Ratings, Genres & IDs

# Ratings, Genres & IDs

## Ratings
**Sync Ratings** fetches the rating and the votes from TMDB and / or OMDb (IMDb data) and writes them to the NFO (<rating>, <votes>, Kodi <ratings>) and the XML (<IMDBrating>, <Rating>, <Votes>, <VoteCount>).
- The dialog shows both sources side by side. A rating of 0 or 0 votes counts as no data.
- Several movies: "Apply this choice to all remaining movies" or "Use the source with more votes" (equal votes → average); **Tools → Ratings & Genres → Sync Ratings Online…** fetches first and then shows current → new for every movie.
- When neither source has data, a second dialog asks once for typed values or Skip.
- When TMDB or OMDb cannot be reached, the movie is skipped and listed at the end — never treated as "no rating".
The defaults of the checkboxes: Settings → Ratings.
| ⬤ | found, NFO and XML agree
| ◐ | NFO and XML differ
| ○ | no tag found
| ✕ | the tag is not a number

## Genres
**Normalize Genres** fixes genres in both files:
- Capitalisation, synonyms ("Sci-Fi" → "Science Fiction"), translations (PT, DE, FR, ES, IT, RU, ZH, AR), duplicates and merged tags ("Family/Fantasy").
- It copies the genres to the file that has none and turns <Genres>/<Genre> in an NFO into Kodi <genre> tags.
- Movies without genres get them from TMDB (then OMDb), with a preview first.
- Genres not in Settings → Genres are "custom": keep or delete them, or Right-click → **Add Custom Genre(s) to Settings**.
- **Tools → Ratings & Genres → Normalize Genres…** previews every change.
**Check Genres Against TMDB…** looks up on TMDB the movies that already have genres and an ID, and lists only those whose genres differ (file → TMDB).
- Where: Right-click → Metadata, or **Tools → Ratings & Genres → Check Genres Against TMDB…**.
- Nothing is ticked: each file keeps its genres unless you tick the movie.
- The ticked ones get TMDB's genres (backup first, Undo).
- It needs a TMDB API key.

## Renaming movie folders and files
> New in v0.20.2. Right-click → Metadata → **Rename Folder and Files…** (one movie or a selection) and Tools → NFO & File Names → **Rename Movie Folders and Files — All Movies…**.
The window shows your choices and five examples; they are saved (also in Settings → NFO / XML → Renamer). **Preview all…** lists every "old → new" first; nothing is renamed before you click **Rename**.
- **Only the folder has a pattern:** Title (Year) (default), Title (Year) [Quality], Title (Year) [Quality] [Genre], Title (Year) [IMDb ID], Title (Year) [TMDB ID], Title (Year) [Quality Codec Audio], or your own with fields like {title} ({year}) [{quality}]. A bracket group with an empty field disappears. Options: the original title, "Matrix, The", dots instead of spaces.
- **The files follow the folder:** the video and every file named after it (NFO, <video>-poster.jpg, subtitles, trailer) get the folder's name; parts keep "-cd1", versions keep " - 1080p". movie.nfo, poster.jpg, .actors, extrafanart and sub-folders stay; inside a DVD / Blu-ray folder nothing is renamed.
- The TMDB pattern writes [tmdb-603]: Jellyfin, Emby and Plex all match the movie by it (tested 2026-11-23; Plex ignores [tmdbid-603]). Kodi uses the NFO and finds names with bracket text too.
- Not renamed, with the reason: a name that is taken, two files that would get one name, a Windows-reserved name, a path that would be too long, a folder with several movies, a movie whose ID Verify IDs flagged (for the ID patterns).
- **Watched state:** Plex, Emby and Jellyfin keep it after a rename. **Kodi loses watched marks and resume points of renamed movies** (and shows them twice until Clean library): export them first (Kodi: Settings → Media → Library → Export library). The preview says so for your programs.
- Nothing is copied. Backup History / Undo renames every folder and file back; one movie is renamed completely or not at all.

## Certifications (age ratings)
> New in v0.20.2. Settings → Ratings → Certifications: your countries in order (default: the app language's country and US) and the most values a list keeps (default 3).
Right-click → Metadata → **Certifications…** (one movie or a selection) and Tools → Ratings & Genres → **Apply My Certification Settings — All Movies…** keep only your countries' age ratings, in your order. A preview comes first; a backup comes first; Backup History / Undo puts the files back.
- Every rating tag your files have is written in its own style: <mpaa>, movie.xml <ContentRating> and <MPAARating> get ONE value (Jellyfin and Emby read one; of a list Jellyfin uses only the first), <FullCertifications> / <FormalMPAA> a list up to your maximum, <certification> as it is now. Values of other countries are removed.
- A value your files lack comes from TMDB (theatrical release first), the US value also from OMDb. When none of your countries has one, the US rating is used and the preview says so. A missing tag is added only where the programs read it: <mpaa> in the NFO and <ContentRating> in movie.xml, written like "BR:12".
- No rating in TMDB and IMDb: the tag is left blank and the preview lists the movie. Only ratings of countries you don't accept and nothing online: you choose per movie (or for all) to keep the file's value or leave the tag blank.
- The health rule (on in the Tight preset) warns about a country you don't accept, more values than your maximum, or several values in <mpaa>. A missing rating is not a warning.

## IMDb and TMDB IDs
Which tool for which problem:
| An ID is missing, or is another film's | **Search Sources**
| An ID is not in every tag, or two IDs differ | **Normalize Sources**
| A field holds a wrong value | **Fix Wrong IMDb / TMDB IDs**
| An ID is only in <imdbid> / <tmdbid> | **Add <uniqueid> for Kodi** (Bulk Tools & Auto Repair tab)
| Are these the right film's IDs? | **Verify IMDb/TMDB IDs**
All five are in Right-click → IDs & Sources (the selected movies) and in **Tools → IDs** (all movies).

### Search Sources
Looks the movie up on TMDB by title + year (in English, your library language and the original title).
- Each movie shows the IDs its files hold now and, first, the film behind that ID.
- In **Choose the TMDB entry**, click anywhere on a movie's row to choose it (green border); a double-click applies it.
- **Enter ID…** lets you type an IMDb (tt…) or TMDB ID, shows title, year and poster, then writes both IDs. It also takes an IMDb or TMDB page address, or an IMDb number without tt.
- A wrong IMDb value next to a good TMDB ID is left out (the window says so) and TMDB's IMDb ID is used.
- Films on IMDb but not on TMDB: the first row reads "IMDb tt… — not on TMDB"; **Confirm IMDb** writes the IMDb ID and marks the movie "OK (IMDb only — not on TMDB)", so Verify IDs and Auto Repair stop looking for it.

### Normalize Sources
Fills missing tags, lets you choose between conflicting IDs (titles looked up on TMDB) and asks for an ID where there is none.
- When only one ID is known, every ID write leaves EMPTY tags for the other source (e.g. <tmdbid></tmdbid>), ready to fill by hand — not with **<uniqueid> only** (Settings → Health Rules → NFO).
- Existing values are never blanked.

### Fix Wrong IMDb / TMDB IDs
> New in v0.20.1: a wrong value in an ID field is ONE warning that says what is wrong and, when the file knows it, the right ID.
- For example "IMDb field holds the TMDB number (27759) — the IMDb ID is tt0056800" (Emby writes the right one in its <imdb id="tt…"> line; that line is read), or "IMDb field holds '0056800', which is not a correct IMDb ID — Fix looks the IMDb ID up on TMDB" (a typo, a mix). The same for a TMDB field that holds an IMDb ID.
- Where: the panel's **Fix**, Right-click → IDs & Sources → **Fix Wrong IMDb / TMDB IDs…** (one movie or the selection), **Tools → IDs → Fix Wrong IMDb / TMDB IDs…** (all movies); also in Fix one issue and Auto Repair.
- It replaces only the wrong values, in the ID tags the files already have (no tag added).
- The right ID comes from the same file first and from TMDB otherwise (only when title and year match).
- A preview comes first; the run is one entry in Backup History / Undo.
- Typing the movie's own TMDB number into an IMDb box is refused.

### Verify IMDb/TMDB IDs
Checks on TMDB that the IDs belong to the movie (any title language, year ±1). Nothing is written until you press **Fix…**; a greyed **Fix…** says why.
- The results: OK · IMDb and TMDB point to different films · ID belongs to another film · ID does not exist · NFO and XML disagree · no IDs · **a field holds a wrong ID**.
- **a field holds a wrong ID** (new in v0.20.1): the film is right but a tag holds something else — Fix writes the right ID, no title search.
- A bad result (another film, different films, an ID that does not exist) is also a warning, with Search Sources as its fix.
- The report sorts by any column and saves to .txt or .csv.
- Verify also keeps the movie's TMDB collection (Collections tab).

### Copy Movie Name
**Copy Movie Name** copies the title (it asks when the files hold several).

## Local titles
When NFO <title> and XML <LocalTitle> differ, Right-click → Metadata → **Make titles the same (NFO ↔ XML)…** lets you choose; Auto Repair gives the side that is the original title (or that does not match the folder) the other one.

## Audio, subtitles and language
- **Audio**: FFprobe tracks as LANGUAGE (CHANNELS); hover for codec and bitrate. A track FFprobe reports as UND takes the language from the NFO or the XML when it fits ("POR — from NFO"). Nothing is written.
- **Subtitles**: embedded tracks and external files (e.g. Movie.pt.srt, also in a Subs folder; forced and SDH flags are read). Right-click → **Subtitles…** opens for any movie; **🌐 Open on OpenSubtitles.org** searches it there.
- **Hard-coded subtitles…** marks burned-in subtitles (they cannot be detected): tick the language(s) or type an ISO 639-2 code. The app writes <tag>Hardsub POR</tag> to the NFO and <Tags><Tag>Hardsub POR</Tag></Tags> to the XML; the column shows "Hard: POR".
- The **Language OK** column is Y when the target language (Settings → Language) is in an audio track or a subtitle: read by FFprobe, a subtitle file, a hard-coded mark, or a stream written in the NFO (streamdetails) or movie.xml (MediaInfo). NFO <language> and XML <Language> / <LanguageCode> at the top level do not count: they are the language for metadata downloads.
