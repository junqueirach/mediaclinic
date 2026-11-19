# =============================================================================
# actors.py — Kodi actor photos in ".actors" (pure: no Tk, no network)
# MediaClinic v0.20.1 AC1–AC6                                    ### NEW v0.20.1 AC ###
#
# Kodi's rules (read in Kodi's source 2026-11-17, plan Part 9g):
#   * ".actors" sits next to the NFO (in a disc folder: next to the NFO in VIDEO_TS / BDMV);
#     a flat folder of several movies shares one ".actors".
#   * File name: the actor's <name> exactly as in the NFO with spaces → "_" and NOTHING else changed (Kodi 20
#     VideoInfoScanner::FetchActorThumbs, read again 2026-11-19: no MakeLegalFileName there); extensions .jpg, .png,
#     .tbn. The match is an exact, case-sensitive compare of the name without its extension, so "Robert Downey Jr."
#     needs "Robert_Downey_Jr..jpg" (two dots). A name with a character no file name can hold (: ? / …) never matches.
#   * A local file wins over the <actor><thumb> URL; the URL is the fallback. Kodi reads either only when its
#     setting "actor thumbnails" is on. Plex, Emby, Jellyfin and Infuse do not read ".actors".
#
# Series-ready (plan rule SR3): nothing here knows movies — an episode / show NFO has the same <actor> blocks.
# =============================================================================
from __future__ import annotations

import difflib
import re
from typing import Iterable, Optional

ACTORS_DIR = ".actors"
PHOTO_EXTS = (".jpg", ".png", ".tbn")
_ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def kodi_file_stem(name: str) -> str:
    """The file name Kodi looks for, without the extension: 'Tom Hanks' → 'Tom_Hanks'. Only spaces change — a final
    dot stays ('Sally Field.' → 'Sally_Field.', so the file is 'Sally_Field..jpg')."""
    return str(name or "").strip().replace(" ", "_")


def storable(stem: str) -> bool:
    """False for a name no Windows / SMB file can have (a colon, ?, *, a slash, quotes …): Kodi can never find a local photo for it,
    so none is downloaded (Kodi then uses the NFO's link)."""
    return bool(stem) and not _ILLEGAL.search(stem)


def read_actors(nfo_text: str) -> list:
    """[(name, thumb_url_or_'')] of the <actor> blocks directly inside the NFO, in order; empty names skipped."""
    out = []
    for blk in re.findall(r"<actor\b[^>]*>(.*?)</actor\s*>", nfo_text or "", flags=re.IGNORECASE | re.DOTALL):
        m = re.search(r"<name\b[^>]*>(.*?)</name\s*>", blk, flags=re.IGNORECASE | re.DOTALL)
        name = _unescape((m.group(1) if m else "").strip())
        if not name:
            continue
        t = re.search(r"<thumb\b[^>]*>(.*?)</thumb\s*>", blk, flags=re.IGNORECASE | re.DOTALL)
        out.append((name, _unescape((t.group(1) if t else "").strip())))
    return out


def _unescape(s: str) -> str:
    """XML text → plain text: CDATA unwrapped, every entity decoded (&#39; too — "Lupita Nyong&#39;o")."""
    import html
    s = s.strip()
    if s.startswith("<![CDATA[") and s.endswith("]]>"):
        return s[9:-3].strip()
    return html.unescape(s)


def photo_files(names: Iterable[str]) -> dict:
    """{stem: file name} of the image files in an ".actors" folder listing."""
    out = {}
    for n in names or ():
        stem, dot, ext = str(n).rpartition(".")
        if dot and ("." + ext.lower()) in PHOTO_EXTS:
            out.setdefault(stem, n)
    return out


def actors_state(actors: list, listing: Optional[Iterable[str]]) -> dict:
    """The Actors column (AC1) for one movie.

    state: "none" (no <actor> in the NFO) / "links" (photos only as URLs, or some actors without any photo)
           / "local" (every actor that has a photo has it in .actors) — mixed cases get the lowest state of the
           actors that have a photo; counts: local, links, nophoto, total; mismatches (AC5): [(file, expected file)]
           for a photo Kodi will never match but that is close to an actor's name; orphans (AC6): photo files that
           match no actor."""
    files = photo_files(listing or ())
    local = links = nophoto = 0
    expected = {}
    for name, url in actors:
        stem = kodi_file_stem(name)
        expected[stem] = name
        if stem in files:
            local += 1
        elif url:
            links += 1
        else:
            nophoto += 1
    total = len(actors)
    if not total:
        state = "none"
    elif links or (local == 0):
        state = "links" if (links or local) else "none"
    else:
        state = "local"
    mismatches, orphans = [], []
    missing = [s for s in expected if s not in files]
    for stem, fname in files.items():
        if stem in expected:
            continue
        near = _near(stem, missing)
        if near:
            ext = fname.rpartition(".")[2]
            mismatches.append((fname, f"{near}.{ext}"))
        else:
            orphans.append(fname)
    return {"state": state, "local": local, "links": links, "nophoto": nophoto, "total": total,
            "mismatches": sorted(mismatches), "orphans": sorted(orphans)}


def _near(stem: str, candidates: list) -> Optional[str]:
    """The expected stem a file was meant for: same letters ignoring case / spaces / '_' / '-', else a close spelling."""
    key = re.sub(r"[\s_\-.]+", "", stem).lower()
    for c in candidates:
        if re.sub(r"[\s_\-.]+", "", c).lower() == key:
            return c
    m = difflib.get_close_matches(stem.replace("_", " ").lower(), [c.replace("_", " ").lower() for c in candidates], n=1, cutoff=0.88)
    if m:
        return next(c for c in candidates if c.replace("_", " ").lower() == m[0])
    return None


def full_size_url(url: str) -> str:
    """A TMDB image link in its full size: …/t/p/w185/x.jpg → …/t/p/original/x.jpg (scrapers often store a small
    size; the preview promises full size). Any other link is returned as it is."""
    return re.sub(r"(image\.tmdb\.org/t/p/)(?:w\d+|h\d+)(?:_and_h\d+_\w+)?/", r"\1original/", url, flags=re.IGNORECASE)


def download_plan(actors: list, listing: Optional[Iterable[str]]) -> list:
    """AC3: [(name, url, file name)] for the actors whose photo is not in .actors yet and who have a URL — never an
    existing photo (any extension). The extension follows the URL (.png stays .png), else .jpg."""
    files = photo_files(listing or ())
    out = []
    for name, url in actors:
        stem = kodi_file_stem(name)
        if stem in files or not storable(stem) or not url or not re.match(r"https?://", url, re.IGNORECASE):
            continue
        ext = ".png" if url.lower().split("?")[0].endswith(".png") else ".jpg"
        out.append((name, full_size_url(url), stem + ext))
    return out
