# =============================================================================
# extra_art.py — extra artwork: the Extra art column, Kodi names, transparency, extrafanart
# MediaClinic v0.20.1 EA1, EA2, EA4, EA5                         ### NEW v0.20.1 EA ###
#
# The user, 2026-11-17: extra artwork is NEVER a warning or an error (Kodi itself hardly uses it) — information plus
# an optional fix. Source: the Kodi wiki page "Artwork types" (copy pasted by the user) and the Media Servers Reference.
#   * Kodi takes the file name as the art type: logo.png is the type "logo" (no longer used), disc.png / cdart.png
#     are "disc", thumb.jpg is "thumb" (episodes) — no skin shows them. Kodi wants clearlogo / discart / landscape.
#   * clearlogo, clearart, discart should be PNG with transparency; a JPG shows a black box.
#   * No skin for Kodi v20+ reads the extrafanart\ folder: fanart1, fanart2 … next to the video do.
# Pure apart from png_alpha(), which reads the first bytes of one file.
# Series-ready (SR3): nothing here knows movies (a show folder has the same kinds).
# =============================================================================
from __future__ import annotations

import os
import struct
from typing import Iterable, Optional

SKIN_KINDS = ("clearlogo", "clearart", "discart", "banner", "landscape", "keyart")   # the six Kodi movie skins use
KODI_NAME = {"logo": "clearlogo", "disc": "discart", "cdart": "discart", "thumb": "landscape"}
TRANSPARENT_KINDS = ("clearlogo", "clearart", "discart")
# The extra-art names each program reads (Media Servers Reference; Plex / Infuse: not known → no rename offered)
READS = {
    "kodi": set(SKIN_KINDS),
    "jellyfin": {"clearlogo", "logo", "clearart", "disc", "cdart", "discart", "banner", "landscape", "thumb"},
    "emby": {"clearlogo", "logo", "clearart", "disc", "cdart", "banner", "landscape", "thumb"},
}


def kind_of(name: str, kinds: Iterable[str]) -> Optional[str]:
    """'clearlogo.png' / 'Movie (2001)-clearlogo.png' → 'clearlogo'; None when not an extra-art name."""
    stem = os.path.splitext(str(name))[0].lower()
    kinds = set(kinds)
    if stem in kinds:
        return stem
    tail = stem.rsplit("-", 1)[-1]
    return tail if tail in kinds else None


def png_alpha(path: str) -> Optional[bool]:
    """True when the PNG can be transparent (RGBA / grey + alpha, or a tRNS chunk), False when not, None when the
    file is not a readable PNG. Reads the header and the chunk list only (up to the first IDAT)."""
    try:
        with open(path, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n":
                return None
            while True:
                hdr = f.read(8)
                if len(hdr) < 8:
                    return None
                n, typ = struct.unpack(">I4s", hdr)
                if typ == b"IHDR":
                    data = f.read(n)
                    if len(data) < 10:
                        return None
                    if data[9] in (4, 6):                     # grey + alpha, RGBA
                        return True
                    f.seek(4, 1)
                    continue
                if typ == b"tRNS":
                    return True
                if typ in (b"IDAT", b"IEND"):
                    return False
                f.seek(n + 4, 1)
    except OSError:
        return None


def summary(names: Iterable[str], alpha: dict, programs: Iterable[str] = (), has_extrafanart: bool = False) -> dict:
    """The Extra art column for one movie: {"count", "kinds", "missing", "notes"}.

    count = how many of the six skin kinds the folder has (Kodi's names); notes = [(file, code, target)] with code
    "kodi_name" (a name Kodi does not read; target = the name it wants; offered as a rename only when allowed — see
    rename_allowed), "not_png" / "no_alpha" (a clear logo / clear art / disc art that cannot be transparent),
    "extrafanart" (the folder no current skin reads; target None)."""
    progs = tuple(programs)
    all_kinds = set(SKIN_KINDS) | set(KODI_NAME)
    have, notes = set(), []
    for n in sorted(names or ()):
        k = kind_of(n, all_kinds)
        if not k:
            continue
        kodi_k = KODI_NAME.get(k, k)
        if kodi_k in SKIN_KINDS:
            have.add(kodi_k)
        if k in KODI_NAME:
            stem, ext = os.path.splitext(n)
            target = stem[: len(stem) - len(k)] + KODI_NAME[k] + ext
            notes.append((n, "kodi_name", target))
        if kodi_k in TRANSPARENT_KINDS:
            if not n.lower().endswith(".png"):
                notes.append((n, "not_png", None))
            elif alpha.get(n) is False:
                notes.append((n, "no_alpha", None))
    if has_extrafanart:
        notes.append(("extrafanart", "extrafanart", None))
    return {"count": len(have), "kinds": sorted(have), "missing": [k for k in SKIN_KINDS if k not in have], "notes": notes,
            "renames": [(n, t) for n, c, t in notes if c == "kodi_name" and rename_allowed(kind_of(n, KODI_NAME), progs)]}


def rename_allowed(old_kind: Optional[str], programs: Iterable[str]) -> bool:
    """A Kodi-name rename only when Kodi is ticked and EVERY ticked program reads the new name (KN1 rule)."""
    progs = set(programs)
    new = KODI_NAME.get(old_kind or "")
    return bool(new) and "kodi" in progs and all(p in READS and new in READS[p] for p in progs)


def fanart_numbers_plan(extrafanart_files: Iterable[str], existing: Iterable[str], prefix: str = "") -> list:
    """EA5: [(file in extrafanart, new name)] — fanart1, fanart2 … (with the movie's '<video>-' prefix when the folder
    uses long names); a number already used next to the video is skipped, so nothing is overwritten."""
    taken = {str(e).lower() for e in existing}
    out, n = [], 1
    for f in sorted(extrafanart_files):
        ext = os.path.splitext(f)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            continue
        while True:
            cand = f"{prefix}fanart{n}{'.jpg' if ext == '.jpeg' else ext}"
            n += 1
            if cand.lower() not in taken and not any(t.startswith(f"{prefix}fanart{n - 1}.".lower()) for t in taken):
                break
        out.append((f, cand))
        taken.add(cand.lower())
    return out
