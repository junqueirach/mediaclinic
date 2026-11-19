# Collections

# Collections

## What a collection is
A collection (Kodi calls it a movie set) groups the movies of a saga — "Harry Potter Collection", "The Matrix Collection".
- The NFO holds it as <set><name>…</name></set>. Kodi groups movies by that **name**, so two spellings make two sets.
- Jellyfin also reads the TMDB collection ID (<set tmdbcolid="…">).
- movie.xml holds the same collection (TMDbCollectionId, CollectionName); MediaClinic reads and writes both files.

## The Collection column and the grouped view
- The **Collection** column (hidden by default, Tools → Choose Columns…) shows the name; the Filter box finds it.
- **Group by collection** (`Alt+G`; next to the sort buttons, or Settings → NFO / XML → Collections; off by default) shows each collection as one row — "Harry Potter Collection (8)", the year span, the worst health colour — with its movies under it. Movies without a collection stay single, in your sort order.
- Where a collection row sits: under a text column (Movie Name, Genres…) it sorts by the collection's name; under any other column it stays where its first movie sits.
- A click selects a collection row; its ▸ arrow, a double-click or `+` / `-` open or close it. Open collections stay open while the app runs.
- Selecting a collection row means its movies for every action ("8 movies selected"); `Ctrl+A` selects every movie, also inside closed collections.

## A collection row: its menu and its panel
Right-click a collection row, or use **All actions ▾** in its panel:
| Expand / Collapse | open or close this row; **Expand All / Collapse All** does it for every row
| Select Its Movies | opens the row and selects its movies
| Fix Collection… | see "Fixing collections" below
| Rename / Join Collection… | give a new name, or choose a collection in use to join it: its movies get its name and TMDB ID
| Create Collection Folder… | see "The collection folder" below
| Collection Artwork… | choose the collection's poster and fanart
| Open Collection Folder | opens the collection's folder
| Open Collection on TMDB | the collection's page (**Search Collection on TMDB** when the collection's TMDB ID is not known)
| Check Collection Online | asks TMDB about this collection's movies
The panel shows the collection: its poster (from the collection folder), TMDB ID, years, folder, artwork, overview, its movies and the fixes. Its buttons: **Artwork…**, **Fix Collection…**, **Open Poster**, **Open Fanart**, **Open Folder**, **TMDB** (the collection's page with its movies, or a TMDB search for the name), **Rename / Join…** and **Write set.nfo**.

## One collection, one name
Kodi shows one set per name, so a TMDB collection gets ONE name for all its movies.
- The name is in English, unless MORE THAN HALF of its movies have their local title in one other language (NFO <title>; XML <LocalTitle> when the NFO has none) — then in that language. A title the app cannot match to a TMDB title counts as English.
- **Settings → NFO / XML → Collections → Collection name language** can fix one language for every collection instead (TMDB's name in it, else English).
- The library language is never used for the name. When TMDB has not given the English name yet, the name in your NFOs is kept and **Check All Collections Online…** fetches it.
- The warning, **Fix Collection…** and Auto Repair use the same name. **Fix Collection…** writes it to every movie of the collection (the preview lists them).
- When your own collection is written two ways, Fix writes the name most of its movies use.
- When NFO <title> and XML <LocalTitle> differ, the movie shows **Title mismatch** and its Fix asks which title to keep.
- After any change the table is checked again, so a fixed warning goes away.

## Checking collections online
**Tools → Collections → Check All Collections Online…** (or Right-click → Metadata → Collection ▸ → **Check Collection Online**) asks TMDB which collection each movie belongs to.
- One request per movie, two per collection, again only after 30 days. **Verify IMDb/TMDB IDs** keeps the same data at no extra cost.
- Movies without a TMDB ID, or whose ID Verify IDs flagged, are skipped and counted.
- Scans and Recompute Health never go online.

## The collection rules
Three rules in Settings → Health Rules, all warnings:
| Collection missing or different | TMDB lists a collection the NFO does not have, the NFO names another one, or one collection is written two ways in your library ("written as X here and as Y in 3 other movies — Kodi shows two sets"). On in the Tight preset only.
| Collection folder / poster / fanart missing | the collection artwork rule: only while a collection folder is set. On in the Tight preset only.
| set.nfo missing or with a mistake | Kodi; only with a collection folder; shown on the collection, not on its movies. On in the Medium and Tight presets.
- Your own collections ("Disney", "Oscar winners") are never warned about and never removed.
- A name with no TMDB ID that matches none of TMDB's names counts as yours, also when TMDB lists the movie in a collection; only **Fix Collection…** on that movie, asked by you, replaces it.
- A movie that was not checked online gets no "missing / different from TMDB" warning (its tooltip says so).
- A collection written two ways and a movie.xml that differs from the NFO are found by every scan.

## set.nfo (Kodi's collection information)
> New in v0.20.1. Checked only with a collection folder set and Kodi ticked.
Each collection's folder should hold a set.nfo: title = the collection name in the NFOs, overview in the app's TMDB language.
- A collection whose set.nfo is missing or has a mistake (no title, no overview although TMDB has one, a title other than the name in the NFOs, an overview in another language) shows "⚠ set.nfo" on its row (Group by collection) and in its panel. The movies' own health is unchanged; the Health report lists these collections.
- Creating a collection folder writes its set.nfo at once.
- **Tools → Collections → Check / Write set.nfo…** (one collection: the **Write set.nfo** button in its panel) writes the missing files and fills empty tags. Where a text differs it shows both, and you tick "Use TMDB's" per collection.
- A backup comes first, and Backup History / Undo puts the old file back.

## Fixing collections
Right-click → Metadata → **Collection ▸**:
- **Fix Collection…** writes the collection TMDB lists, under the collection's one name (see "One collection, one name" above), with its overview when the NFO has none. Several movies: a preview first. Also **Tools → Collections → Fix All Collections…** and the Auto Repair step.
- **Set Collection…** puts the selected movies in a collection: one in use, your own name, or a TMDB collection found with **Search TMDB** (its TMDB ID and name are written). With its tick box ticked, it then makes the collection folder and opens **Collection Artwork…**.
- **Remove from Collection…** (asks first) is the only action that ever removes a <set>: it says the movies are **not in a collection**.
-- MediaClinic remembers that (no_collection.json), so TMDB's collection is no longer suggested for them while their NFO has no <set>.
-- It also works for a movie TMDB puts in a collection that you don't want.
-- **Set Collection…** puts a movie in a collection again.
- A collection TMDB no longer has: an NFO links a TMDB collection (tmdbcolid) that TMDB no longer lists for the movie, or that no longer exists.
-- **Check All Collections Online…** gives the warning "Collection: '…' no longer exists on TMDB" (or "is not listed by TMDB for this movie").
-- **Fix** runs **Remove from Collection…**.
- **Update** re-reads the NFO: a movie whose <set> you changed moves to its new collection in the grouped view.
In movie.xml:
- Every collection action writes the same collection into movie.xml (TMDbCollectionId and CollectionNumber = the TMDB collection ID, or 0 for none; CollectionName).
- Remove from Collection… sets the IDs to 0 and removes the name.
- An NFO-style <set> block inside movie.xml does not belong there and is removed.
- When movie.xml and the NFO say different collections, the warning "Collection: movie.xml says …" is fixed by **Sync Collection (NFO ↔ movie.xml)…**: the NFO's collection goes to movie.xml; an NFO without one takes movie.xml's.
- <JSONDump> is never changed.
Every NFO is backed up first; **Backup History / Undo** puts it back. Every other byte of the file stays as it was.

## The collection folder (collection artwork)
Kodi reads collection artwork from ONE folder you choose in Kodi: Settings → Media → Videos → **Movie set information folder**.
- Set the same folder in **Libraries…** → **Collection folder** (the same share, e.g. \\NAS\Movies\Sets or Z:\Sets).
- Settings → NFO / XML → Collections shows it; ticking **Group by collection** without one asks for it.
- Each collection has a folder named like the collection, with / \ ? : * " < > | written as _ (Kodi's rule), holding poster.jpg and fanart.jpg.
- **Create Collection Folder…** shows a preview, makes the folder and downloads the poster (library language first) and the fanart from TMDB.
-- Where: Right-click, a collection row, or **Tools → Collections → Create All Collection Folders…**.
-- An existing file is never replaced.
-- A missing TMDB API key, or a collection without a poster or fanart on TMDB, is listed in the result.
-- Your own collections get the folder: choose their images with **Collection Artwork…**.
-- Undo removes what the run created.
- **Collection Artwork…** shows the posters and fanart images of the collection's TMDB collection, or of **The movies of this collection** (their own poster / fanart).
-- Where: Right-click a movie or a collection row, the panel's **Artwork…**, or **Fix** on "Collection artwork: … missing" for one collection.
-- Without a known TMDB collection, **Search TMDB** finds one by name.
-- The posters come 12 per page (4 per row) and the fanart images 9 per page (3 per row): **Next ›** and **‹ Previous** show the other pages, and a chosen image stays chosen.
-- The window keeps the size you give it.
-- Click one poster and one fanart image, then **Save to Folder**: the folder is made when missing; an existing image is replaced only after a backup, so Backup History can undo it.
- A folder that differs only in case is found (Windows, SMB); one that differs in accents is not the same folder for Kodi, and the warning names it.
- When a collection gets a new name (**Fix Collection…**, **Set Collection…**, **Rename / Join Collection…**, Auto Repair), its folder comes along:
-- The files of the old folder move into the folder of the new name, and the empty old folder is removed.
-- When both folders have a poster (or fanart), the old folder's image is kept and the other one goes to replaced\ inside the folder — nothing is deleted.
-- The folder stays where it is while another movie still uses the old name.
-- Backup History / Undo puts everything back.
- A folder left under another TMDB name of the collection shows **Collection folder: images left in '…'**; its Fix **Move to the Collection Folder** moves the files the same way.
