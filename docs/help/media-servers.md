# Media Servers

# Media Servers

## Kodi
MediaClinic reads every name Kodi uses and shows the file Kodi would pick, in Kodi's order:
| Poster | <video>-poster.jpg/.png, poster.jpg/.png, <video>.tbn, movie.tbn, <stack>-poster.jpg (a multi-part movie: Movie-poster.jpg for Movie-CD1.mkv)
| Fanart | <video>-fanart.jpg/.png, fanart.jpg/.png, <stack>-fanart.jpg
| NFO | movie.nfo, <video>.nfo, <stack>.nfo for a multi-part movie (Movie.nfo for Movie-CD1.mkv + Movie-CD2.mkv; Jellyfin reads movie.nfo instead), and the folder's only NFO whatever its name when it holds <movie> (a release-info .nfo is ignored)
| Extra fanart | fanart1.jpg…, <video>-fanart1.jpg… (the extrafanart folder is for Jellyfin and Emby)
<video> is the video's file name without its extension. The tooltips say which file was found. Fetch Poster/Folder, Fetch Fanart and Copy poster → folder write in the style the folder already uses: a Kodi folder gets <video>-poster.jpg. Copy poster → folder also makes a folder.jpg in a folder that has none. New backdrops follow the same rule.
- **Rename NFO for Kodi…**: Kodi reads "<video>.nfo" or "movie.nfo", not an NFO named after the folder (unless it is the only NFO). It offers both names (the recommended one selected); **Tools → NFO & File Names → Rename NFOs for Kodi…** shows a preview. A name that exists is never overwritten; Undo puts the old name back.
- DVD and Blu-ray folders: a VIDEO_TS or BDMV structure is the movie; VIDEO_TS-poster.jpg, VIDEO_TS.nfo, index-poster.jpg and index.nfo are read too. FFprobe and frames use the largest .VOB / .m2ts file.
- Collections: Kodi's movie set information folder — Collections tab.

## Jellyfin, Emby and Plex
The names the other servers read are found too, after Kodi's:
| Poster | <video>.jpg, cover, default, movie, <video>-cover…
| Fanart | backdrop, background, art
| Extra backdrops | backdrop-1, fanart-1, background-1, art-1
| Pictures | .jpg, .png, .jpeg, .webp, .gif, .bmp
- The poster, folder and fanart tooltips say which servers read the file found. folder.jpg alone counts as the poster (Plex, Jellyfin, Emby and Infuse use it; Kodi does not).
- NFO: Plex reads no NFO; Kodi reads movie.nfo first when "Movies are in separate folders" is on. Two NFOs the servers read (e.g. movie.nfo and <video>.nfo) are a warning: delete the one you do not need. mymovies.xml is shown in the XML tooltip: no current server reads it.
- Other videos are not "Multiple video files": trailers (-trailer), samples, extras (-featurette, -deleted …), the parts of a stack (cd1, part2) and versions ("Movie - 1080p"). The Video tooltip lists them.
