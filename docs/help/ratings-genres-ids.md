# Ratings, Genres & IDs

# Ratings, Genres & IDs

## Ratings
**Sync Ratings** fetches the rating and the votes from TMDB and / or OMDb (IMDb data) and writes them to the NFO (<rating>, <votes>, Kodi <ratings>) and the XML (<IMDBrating>, <Rating>, <Votes>, <VoteCount>).
- The dialog shows both sources side by side. A rating of 0 or 0 votes counts as no data.
- Several movies: "Apply this choice to all remaining movies" or "Use the source with more votes" (equal votes → average); **Tools → Sync Ratings Online — All Movies…** fetches first and then shows current → new for every movie.
- When neither source has data, a second dialog asks once for typed values or Skip.
- When TMDB or OMDb cannot be reached, the movie is skipped and listed at the end — never treated as "no rating".
The defaults of the checkboxes: Settings → Ratings.
| ⬤ | found, NFO and XML agree
| ◐ | NFO and XML differ
| ○ | no tag found
| ✕ | the tag is not a number

## Genres
**Normalize Genres** fixes genres in both files: capitalisation, synonyms ("Sci-Fi" → "Science Fiction"), translations (PT, DE, FR, ES, IT, RU, ZH, AR), duplicates and merged tags ("Family/Fantasy"). It copies the genres to the file that has none and turns <Genres>/<Genre> in an NFO into Kodi <genre> tags. Movies without genres get them from TMDB (then OMDb), with a preview first. Genres not in Settings → Genres are "custom": keep or delete them, or Right-click → **Add Custom Genre(s) to Settings**. **Tools → Normalize Genres — All Movies…** previews every change.

## IMDb and TMDB IDs
- **Normalize Sources** fills missing tags, lets you choose between conflicting IDs (titles looked up on TMDB) and asks for an ID where there is none. When only one ID is known, every ID write leaves EMPTY tags for the other source (e.g. <tmdbid></tmdbid>), ready to fill by hand. Existing values are never blanked.
- **Search Sources** looks the movie up on TMDB by title + year (in English, your library language and the original title). Each movie shows the IDs its files hold now and, first, the film behind that ID. **Enter ID…** lets you type an IMDb (tt…) or TMDB ID, shows title, year and poster, then writes both IDs.
- Films on IMDb but not on TMDB: the first row reads "IMDb tt… — not on TMDB"; **Confirm IMDb** writes the IMDb ID and marks the movie "OK (IMDb only — not on TMDB)", so Verify IDs and Auto Repair stop looking for it.
- **Verify IMDb/TMDB IDs** checks on TMDB that the IDs belong to the movie (any title language, year ±1): OK, IMDb and TMDB point to different films, ID belongs to another film, ID does not exist, NFO and XML disagree, no IDs. The report sorts by any column and saves to .txt or .csv; nothing is written until you press **Fix…**. It also keeps the movie's TMDB collection (Collections tab).
- **Copy Movie Name** copies the title (it asks when the files hold several).

## Local titles
When NFO <title> and XML <LocalTitle> differ, Right-click → Metadata → **Make titles the same (NFO ↔ XML)…** lets you choose; Auto Repair gives the side that is the original title (or that does not match the folder) the other one.

## Audio, subtitles and language
- **Audio**: FFprobe tracks as LANGUAGE (CHANNELS); hover for codec and bitrate. A track FFprobe reports as UND takes the language from the NFO or the XML when it fits ("POR — from NFO"). Nothing is written.
- **Subtitles**: embedded tracks and external files (e.g. Movie.pt.srt, also in a Subs folder; forced and SDH flags are read). Right-click → **Subtitles…** opens for any movie; **🌐 Open on OpenSubtitles.org** searches it there.
- **Hard-coded subtitles…** marks burned-in subtitles (they cannot be detected): tick the language(s) or type an ISO 639-2 code. The app writes <tag>Hardsub POR</tag> to the NFO and <Tags><Tag>Hardsub POR</Tag></Tags> to the XML; the column shows "Hard: POR".
- The **Language OK** column is Y when the target language (Settings → Language) is in an audio track or a subtitle: read by FFprobe, a subtitle file, a hard-coded mark, or a stream written in the NFO (streamdetails) or movie.xml (MediaInfo). NFO <language> and XML <Language> / <LanguageCode> at the top level do not count: they are the language for metadata downloads.
