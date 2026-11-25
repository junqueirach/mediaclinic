# Images

# Images

## Poster, folder and fanart
**Fetch Poster/Folder…** shows your image next to the TMDB (and fanart.tv) posters; **Use This** downloads the full size to the poster (and folder.jpg when the folder uses one) after a backup. **Fetch Fanart…** does the same for the fanart. **Copy poster.jpg → folder.jpg** fixes folders whose folder.jpg differs; **Tools → Artwork → Copy poster.jpg → folder.jpg…** shows a preview first.
- A download is checked before it replaces anything: a page that is not a picture, or a picture cut off, never replaces a good file.
- The Fetch windows close with **Done** (or `Esc`); images applied before are kept. While a download runs, Done shows "Finishing…".

## Quality tiers
| Poster / Folder (2:3) | 4K 2000×3000 · 1440p 1500×2250 · 1080p 1000×1500 · 720p 666×1000 · 540p 540×810 · 480p 480×720 · 360p
| Fanart (16:9) | 4K 3840×2160 · 1440p 2560×1440 · 1080p 1920×1080 · 720p 1280×720 · 540p 960×540 · 480p 854×480 · 360p
- ±5 % tolerance.
- The minimum tier is one setting (Settings → Health Rules and Settings → Images & Artwork); images below it are warnings.
- Proportions: poster and folder 2:3 (3:4 optional), fanart 16:9 (3:2 optional).
- "Corrupt" (✕) means the scan found a bad header or end of the file. A file damaged in the middle can pass the scan; Fix Image or Copy poster then says it cannot be read.
- A PNG named poster.jpg is read and gets an "extension mismatch" warning.

## Backdrops
| Extract Backdrop(s) | FFmpeg frames spread over the film
| Fetch Backdrops | pick TMDB / fanart.tv backdrops; replace a file or save a new one
| Replace All Backdrops | choose the source and how many (it starts at the number you have); the highest resolution first, a failed download is replaced by the next image; a backup first
**Tools → Artwork → Delete extrafanart Subfolders…** removes the extrafanart folders (a backup first). Jellyfin and Emby use them as extra backdrops; Kodi and Plex do not read them. The health rules flag too few backdrops (the main fanart counts as one) and very small ones. With Emby or Jellyfin ticked, a movie with videos in a backdrops folder (theme videos, which they play as moving backdrops) is not flagged for too few backdrops.

## Frames from the movie
Fetch Fanart and Fetch Backdrops have a **🎞 Frames from movie** button (with FFmpeg set and a video in the folder).
- 10 frames from 10 %–90 % of the running time; black or flat frames are replaced by a nearby moment. **More frames** gives a new set.
- The frames keep the video's resolution and are marked when they are below the fanart minimum. They are temporary files, deleted when the window closes.
- No TMDB ID needed: without one, Fetch Fanart and Fetch Backdrops open on the movie's frames (or fanart.tv by IMDb ID).

## fanart.tv
With a fanart.tv key (Settings → API Keys) the Fetch windows and Replace All Backdrops get a **Source** choice: TMDB, fanart.tv or Both.
- Posters: your library language first, then images without text, then English.
- Backdrops: fanart.tv backgrounds (1920×1080); tick "include landscape thumbs" for the 1000×562 ones.
- fanart.tv gives no pixel size: "~1920×1080" is its usual size; the real size is checked after the download. Answers are kept 7 days.

## Fixing proportions and size
Right-click → Artwork → **Fix Image Proportions / Size…** (`Alt+I`) fixes a poster, folder image or fanart with wrong proportions or a low resolution, with a before / after view. Every file is backed up first.
- **Method**: Blur fill keeps the whole image and fills the empty bands with a blurred copy (posters); Smart crop keeps the most detailed part (fanart); Centre crop; Solid fill. Up to 3 % is simply stretched.
- **Size**: the tier nearest to the image, with its factor and a mark — ✓ recommended, ⚠ soft, ✕ too far (not offered). "Keep current size" fixes the proportions only. For a much bigger image use **Find a better one online**.
- **AI upscale** (optional): **Download upscaler (about 45 MB)…** installs Real-ESRGAN (checked against its SHA-256) and tests it once; it needs a Vulkan graphics card. ×2 is recommended, up to ×4 allowed — check the preview: AI may invent detail.
- **folder.jpg**: "Also copy the result to folder.jpg" is ticked when folder.jpg is the same picture as the poster. When it is a different picture, "Also fix folder.jpg (a different picture: fixed on its own, not replaced)" is offered instead.
### Many images at once
Select several movies, or use **Tools → Artwork → Fix Image Proportions / Size…** for every movie with an image warning.
- A preview lists every image and its fix. Only ✓ sizes are used.
- When the AI upscaler is installed and tested, the bulk fix offers it: then sizes up to ×2 are used too (slower).
- You can minimise the window while it runs; **■ Stop** stops it.
- Skipped images are counted with the reason. For skipped posters the end message offers **Replace them online now…** and **Review them one by one…**.

## Replacing low-resolution posters
> New in v0.20.1.
**Tools → Artwork → Replace Low-Resolution Posters…** (all movies) or Right-click → Artwork → **Replace Low-Resolution Posters…** (the selected movies).
1. Choose a size under "Replace posters below": the Health Rules minimum is selected.
2. Look at the preview.
3. Every poster below the size — and every corrupt poster — gets the best online poster that reaches the size, from TMDB (and fanart.tv with a key).
- folder.jpg follows when it was the same picture.
- Movies without a poster are not changed.
- Pause and Cancel work. The run is one entry in Backup History / Undo.

## Reviewing posters one by one
> New in v0.20.1.
**Tools → Artwork → Review Posters One by One…**, Right-click → Artwork → **Review Posters One by One…**, or the end message of the bulk Fix Image Proportions / Size when it skipped posters.
1. Choose which posters (below a size and corrupt, wrong proportions, the selected movies, or the movies the Filter shows) and the size to reach.
2. One window per movie shows the poster now, the online posters in your artwork language order, and the result of the highlighted choice. The poster Replace Low-Resolution Posters would take is highlighted; sizes below the chosen one are shown in yellow.
| Use | writes the highlighted choice (folder.jpg follows when it was the same picture)
| Fix proportions, Upscale (AI) | show the result first; the AI upscaler (up to ×2) runs when you press Use
| Skip | leaves the movie as it is
| Back | shows the previous movie (its change stays; Undo it in Backup History)
| Stop | ends with a count
- The next movie's online posters load while you look at this one.
- Every change of the session is ONE entry in Backup History / Undo.
- The keys are in the Shortcuts tab.

## Artwork language
> New in v0.20.1.
**Settings → Images & Artwork → Artwork language** decides which online images come first everywhere: Fetch Poster/Folder, Fetch Fanart, Fetch Backdrops, Replace All Backdrops, Replace Low-Resolution Posters.
- The language is the library language (the OK? column's language) or a language you choose.
- **Prefer this language**: your language first, then images without text, English, the rest.
- **Only this language**: the Fetch windows then have a "Show all languages" box.
- **Fanart and backdrops: images without text first** is ticked by default.
- Each image in the Fetch windows shows its language (or "no text").

## After an image change: refresh your player
Kodi, Emby, Jellyfin, Plex and Infuse keep a copy of an image. After a replace, the end message says how each of your programs shows the new one:
| Kodi | open the movie's information and choose Refresh
| Emby, Jellyfin | Refresh metadata on the movie with "Replace existing images" ticked
| Plex | Refresh Metadata on the movie
| Infuse | refresh the movie's metadata

## Actor photos
> New in v0.20.1.
The **Actors** column shows where a movie's actor photos are:
| Local | photos in .actors next to the NFO — only Kodi reads them, with its setting "actor thumbnails" on
| Links | photos only as web links in the NFO, which the other programs use
| No info | no actors in the NFO
- **Download Actor Photos…** (**Tools → Artwork** for all movies, Right-click → Artwork for the selected ones) saves the linked photos at full size into .actors (created hidden, as Kodi does). An existing photo is never replaced and the NFO does not change.
- A photo Kodi would not match ("Tom Hanks.jpg" instead of "Tom_Hanks.jpg", another case, a near spelling) is marked ⓘ. Right-click → Artwork → **Rename actor photos for Kodi** fixes the names (Undo puts them back).
- Photos that match no actor are listed in the tooltip only.
- The Health rule "No actor information" is a warning, on only in the Tight preset. Actors without any photo are flagged only when Kodi is ticked: Emby, Jellyfin and Plex download the photos themselves.
- The votes checks ("Missing votes" and the other votes warnings) are skipped, and Auto Repair leaves the votes alone, when the only programs ticked are Emby, Jellyfin or Plex: none of them uses the vote count.
- The collection artwork rule runs only when Kodi is ticked (or nothing is): only Kodi reads artwork from a collection folder.
- The column is visible from the start only when Kodi is ticked (Tools → Choose Columns…).

## Extra artwork
> New in v0.20.1. Information only, never a warning.
The **Extra art** column says how many of clear logo, clear art, disc art, banner, landscape and key art the folder has. It shows ⓘ for:
- a name Kodi does not read (logo.png → clearlogo.png, disc.png / cdart.png → discart.png, thumb.jpg → landscape.jpg);
- a clear logo / clear art / disc art that is not a PNG with transparency;
- an extrafanart folder (no Kodi v20+ skin reads it).
| Rename extra artwork for Kodi | Right-click → Artwork. Offered only when every ticked program reads the new name; Undo puts the old name back.
| Convert extrafanart → fanart1, 2… | Right-click → Artwork, or **Tools → Artwork** for all movies. The images are copied; the extrafanart folder is kept.
