# Images

# Images

## Poster, folder and fanart
**Fetch Poster/Folder…** shows your image next to the TMDB (and fanart.tv) posters; **Use This** downloads the full size to the poster (and folder.jpg when the folder uses one) after a backup. **Fetch Fanart…** does the same for the fanart. **Copy poster.jpg → folder.jpg** fixes folders whose folder.jpg differs; **Tools → Copy poster.jpg → folder.jpg — All Movies with Differences…** shows a preview first.
- A download is checked before it replaces anything: a page that is not a picture, or a picture cut off, never replaces a good file.
- The Fetch windows close with **Done** (or `Esc`); images applied before are kept. While a download runs, Done shows "Finishing…".

## Quality tiers
| Poster / Folder (2:3) | 4K 2000×3000 · 1440p 1500×2250 · 1080p 1000×1500 · 720p 666×1000 · 540p 540×810 · 480p 480×720 · 360p
| Fanart (16:9) | 4K 3840×2160 · 1440p 2560×1440 · 1080p 1920×1080 · 720p 1280×720 · 540p 960×540 · 480p 854×480 · 360p
±5 % tolerance. The minimum tier is one setting (Settings → Health Rules and Settings → Image Sizes); images below it are warnings. Proportions: poster and folder 2:3 (3:4 optional), fanart 16:9 (3:2 optional). "Corrupt" (✕) means the scan found a bad header or end of the file. A file damaged in the middle can pass the scan; Fix Image or Copy poster then says it cannot be read. A PNG named poster.jpg is read and gets an "extension mismatch" warning.

## Backdrops
| Extract Backdrop(s) | FFmpeg frames spread over the film
| Fetch Backdrops | pick TMDB / fanart.tv backdrops; replace a file or save a new one
| Replace All Backdrops | choose the source and how many (it starts at the number you have); the highest resolution first, a failed download is replaced by the next image; a backup first
**Tools → Delete extrafanart Subfolders — All Movies…** removes the extrafanart folders (a backup first). Jellyfin and Emby use them as extra backdrops; Kodi and Plex do not read them. The health rules flag too few backdrops and very small ones.

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
Right-click → Artwork → **Fix Image Proportions / Size…** fixes a poster, folder image or fanart with wrong proportions or a low resolution, with a before / after view.
- **Method**: Blur fill keeps the whole image and fills the empty bands with a blurred copy (posters); Smart crop keeps the most detailed part (fanart); Centre crop; Solid fill. Up to 3 % is simply stretched.
- **Size**: the tier nearest to the image, with its factor and a mark — ✓ recommended, ⚠ soft, ✕ too far (not offered). "Keep current size" fixes the proportions only. For a much bigger image use **Find a better one online**.
- **AI upscale** (optional): **Download upscaler (about 45 MB)…** installs Real-ESRGAN (checked against its SHA-256) and tests it once; it needs a Vulkan graphics card. ×2 is recommended, up to ×4 allowed — check the preview: AI may invent detail.
- "Also copy the result to folder.jpg" (ticked by default) keeps poster and folder the same picture. Every file is backed up first.
- Several movies, or **Tools → Fix Image Proportions / Size — All Movies with Image Warnings…**: a preview lists every image and its fix; only ✓ sizes are used. You can minimise the window while it runs; **■ Stop** stops it.
