# =============================================================================
# media_profiles.py
# Metadata & MediaClinic — what each media program reads, and the names a fix
# writes for the programs the user ticked (pure data)
# Version: 0.20.0                                              ### NEW v0.20.0 F3a-1 ###
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# F3 (roadmap Part 6, decisions 9f.6a and 9f.11): the user ticks the programs
# that play the library ("Which program plays your movies?"; more than one can
# be ticked).  This module turns that set into:
#   - the health mode underneath (v0.19.6 TR1b: "nfo" / "nfo_xml" / "xml");
#   - the names a fix writes (NFO, poster, fanart): a name EVERY ticked program
#     reads (Kodi + Infuse: <video>.nfo, poster.jpg, fanart.jpg);
#   - which fixes apply (the union of the programs' needs).
# Reading never depends on it: the scanner keeps accepting every known name
# (naming_catalog.py).  Only writing follows the profile.
#
# Sources: naming_catalog.py (F5.1, Kodi / Jellyfin / Emby / Plex) and the
# the user's Apple TV test of 2026-11-16 (Infuse; see below).  Entries not
# yet checked on a real server are listed in TO_VERIFY (F3.8 item 4).
#
# RULES (like settings_model.py and naming_catalog.py): pure data and pure
# helpers only — no I/O, no tkinter, no logging.
# Patterns: "{video}" = the video file name without extension.
# =============================================================================

PROGRAMS = ("kodi", "plex", "jellyfin", "emby", "infuse", "mb_mcm")
PROGRAM_LABEL = {"kodi": "Kodi", "plex": "Plex", "jellyfin": "Jellyfin", "emby": "Emby", "infuse": "Infuse",
                 "mb_mcm": "MediaBrowser / Media Center Master"}

# Not yet confirmed on the user's test servers / device (plan F3.8 item 4, 9f.11).
# Plex was in the "Kodi pack" (9f.11) until the server test of 2026-11-17: it reads no NFO, so its NFO list is empty
# (naming_catalog) and, with only Plex ticked, the NFO checks follow the user's answer (plex_nfo_checks).
TO_VERIFY = {
    "plex": "checked on a real Plex server 2026-11-17: local artwork (every usual name) yes, NFO and <set> no; kept "
            "with Kodi's names; only Plex ticked → the NFO / collection checks follow the user's answer (plex_nfo_checks)",
    "jellyfin": "checked on a real Jellyfin server 2026-11-17: as Emby (both NFO names, <set> in both forms, every usual "
                "artwork name); collections from <set> only with the library option 'Automatically add to collection'",
    "emby": "checked on a real Emby server 2026-11-17: <video>.nfo and movie.nfo read, <set> in both forms, every usual "
            "poster / fanart name (.jpg / .png), no stray image; a stack-name image (Movie.jpg for -cd1 / -cd2) not used",
}
# Infuse was checked on the user's Apple TV on 2026-11-16 (folder view, one video per folder; "Prefer local
# artwork" and "Prefer local metadata" on): plan_assets/run_0200/INFUSE_TEST_2026-11-16.md.  It reads
# <video>.nfo and ignores movie.nfo; posters <video>-poster > <video> and poster > folder; fanart <video>-fanart
# and fanart; logo.png.  With no recognised poster it shows ANY other image (stray) as the poster.  Multi-part
# files (-cd1 / -cd2) are separate items, each with its own <part>.jpg.

import naming_catalog as _nc                                   # pure data too (F5.1)


def _from_catalog(server):
    """The names a media server reads, from naming_catalog (the one table the scanner reads with)."""
    return {"metadata": ("nfo",),
            "nfo": tuple(p for p, s in _nc.NFO_NAMES if server in s),
            "poster": tuple(p for p, s in _nc.POSTER_NAMES if server in s),
            "fanart": tuple(p for p, s in _nc.FANART_NAMES if server in s),
            "folder": True, "backdrops": True, "set": True}


# What each program reads.  "nfo" / "poster" / "fanart": the names it reads (the main poster / fanart; folder.jpg
# and the extra backdrops are their own kinds).  folder / backdrops / set: does it use folder.jpg, extra
# backdrops, the NFO's <set> (collections)?  Kodi, Plex, Jellyfin and Emby come from naming_catalog; Infuse from
# the Apple TV test; MediaBrowser / Media Center Master read movie.xml, folder.jpg and backdrop*.jpg only.
READS = {
    "kodi": _from_catalog("kodi"),
    "plex": _from_catalog("plex"),                                # artwork only: Plex reads no NFO (tested)
    "jellyfin": _from_catalog("jellyfin"),
    "emby": _from_catalog("emby"),
    "infuse": {"metadata": ("nfo",), "nfo": ("{video}.nfo",),          # movie.nfo is not read (Apple TV test)
               "poster": ("{video}-poster", "{video}", "poster", "folder"), "fanart": ("{video}-fanart", "fanart"),
               "folder": False, "backdrops": False, "set": False},
    "mb_mcm": {"metadata": ("xml",), "nfo": (), "poster": (), "fanart": (),
               "folder": True, "backdrops": True, "set": False},
}

# The programs whose name lists the "Not read by …" warning and the renamer judge a file by.  Kodi's own names
# have their own rules (nfo_name_not_kodi; stack, disc and .tbn names it also reads); Jellyfin, Emby and Plex wait
# for the user's test servers (TO_VERIFY, F3.8 item 4): until then a name is never called "not read" by them.
NAME_CHECKED = ("infuse",)

# The order a name is preferred in when more than one is read by every ticked program.
# ### MODIFIED v0.20.0 KN1 (user decision 2026-11-17, MEDIA_SERVERS_REFERENCE §4.1) ### the long names first: Kodi's
# docs recommend <video>.nfo / <video>-poster.jpg, they work with every Kodi source setting (movie.nfo and poster.jpg
# need "Movies are in separate folders…") and every other program reads them.  Only NEW files get these names: a folder
# whose own names every ticked program reads keeps them; with no video name (disc folder without one) the short names.
WRITE_PREFERENCE = {
    "nfo": ("{video}.nfo", "movie.nfo"),
    "poster": ("{video}-poster", "poster", "{video}"),
    "fanart": ("{video}-fanart", "fanart"),
}
KINDS = tuple(WRITE_PREFERENCE)


def clean_programs(programs):
    """The known program ids of *programs*, without repeats, in PROGRAMS order."""
    got = set(programs or ())
    return tuple(p for p in PROGRAMS if p in got)


def health_mode_for(programs):
    """The v0.19.6 health mode the ticked programs need: "xml" (MediaBrowser / Media Center Master alone),
    "nfo_xml" (it and an NFO program), "nfo" (NFO programs only), or None (nothing ticked: no change)."""
    ps = clean_programs(programs)
    if not ps:
        return None
    xml = any("xml" in READS[p]["metadata"] for p in ps)
    nfo = any("nfo" in READS[p]["metadata"] for p in ps)
    return "nfo_xml" if xml and nfo else ("xml" if xml else "nfo")


def write_name(kind, programs):
    """The name pattern a fix writes for *kind* ("nfo", "poster", "fanart") so that every ticked program that
    reads that kind of file reads it; None when nothing is ticked (keep the folder's own style, B23) or when no
    single name serves them all (see conflicts())."""
    ps = [p for p in clean_programs(programs) if READS[p][kind]]
    if not ps:
        return None
    common = set(READS[ps[0]][kind])
    for p in ps[1:]:
        common &= set(READS[p][kind])
    return next((n for n in WRITE_PREFERENCE[kind] if n in common), None)


def write_names(programs):
    """{kind: name pattern or None} for every kind."""
    return {k: write_name(k, programs) for k in KINDS}


def conflicts(programs):
    """The kinds for which the ticked programs share no name (each needs its own file)."""
    ps = clean_programs(programs)
    return tuple(k for k in KINDS if any(READS[p][k] for p in ps) and write_name(k, ps) is None)


def uses(feature, programs):
    """True when at least one ticked program uses *feature* ("folder", "backdrops", "set"): the fix that
    writes it applies (the union of the programs' needs, 9f.11).  Nothing ticked: True (today's behaviour)."""
    ps = clean_programs(programs)
    return True if not ps else any(READS[p][feature] for p in ps)


def names_for_each(kind, programs):
    """Each ticked program's own first name for *kind*, without repeats (the files a fix writes when no single
    name serves them all: one per program, decision D-F3c-1 of 2026-11-16)."""
    out = []
    for p in clean_programs(programs):
        if READS[p][kind] and READS[p][kind][0] not in out:
            out.append(READS[p][kind][0])
    return tuple(out)


def _matches(kind, pattern, name, video):
    """True when the file *name* is *pattern* (images: any picture extension; NFO: the whole name)."""
    want = expand(pattern, video).lower()
    if kind == "nfo":
        return name.lower() == want
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return stem.lower() == want


def not_reading(kind, name, video, programs):
    """Every ticked program that reads *kind* but has no name in READS for a file called *name*."""
    if not name:
        return ()
    return tuple(p for p in clean_programs(programs)
                 if READS[p][kind] and not any(_matches(kind, pat, name, video) for pat in READS[p][kind]))


def read_by_all(kind, name, video, programs):
    """True when every ticked program that reads *kind* lists *name* (a fix may keep writing it)."""
    return not not_reading(kind, name, video, programs)


def unread_by(kind, name, video, programs):
    """The ticked programs the warning and the renamer may name for a file called *name* (e.g. Infuse for
    "movie.nfo"): only the programs in NAME_CHECKED (see there)."""
    return tuple(p for p in not_reading(kind, name, video, programs) if p in NAME_CHECKED)


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tbn")


def plan_renames(current, files, video, programs):
    """The renames that let every ticked program read the movie's NFO, poster and fanart (F3.10, pure: no I/O).
    *current* {"nfo" / "poster" / "fanart": the file name the scan uses, or None}; *files*: every file name in
    the movie folder; *video*: the video file name without extension ("" for a disc folder).
    Returns (moves, skipped): moves [(kind, src, dst)], skipped [(kind, src, why)] with why one of
    "conflict" (no single name serves every ticked program), "no_video" (the name needs the video's name),
    "several_nfo" (more than one .nfo: delete the extra one by hand first), "exists" (the new name is taken).
    Only a file a ticked program does not read is renamed; the video is never renamed; a .tbn poster becomes .jpg."""
    ps = clean_programs(programs)
    moves, skipped = [], []
    if not ps:
        return moves, skipped
    have = {f.lower() for f in files}
    taken = set(have)
    for kind in KINDS:
        src = (current or {}).get(kind)
        if not src or not unread_by(kind, src, video, ps):
            continue
        pat = write_name(kind, ps)
        if pat is None:
            skipped.append((kind, src, "conflict"))
            continue
        if "{video}" in pat and not video:
            skipped.append((kind, src, "no_video"))
            continue
        if kind == "nfo" and sum(1 for f in files if f.lower().endswith(".nfo")) > 1:
            skipped.append((kind, src, "several_nfo"))
            continue
        if kind == "nfo":
            dst = expand(pat, video)
        else:
            ext = src[src.rfind("."):].lower() if "." in src else ".jpg"
            dst = expand(pat, video) + (".jpg" if ext == ".tbn" else ext)
        if dst.lower() == src.lower():
            continue
        if dst.lower() in taken:
            skipped.append((kind, src, "exists"))
            continue
        taken.discard(src.lower())
        taken.add(dst.lower())
        moves.append((kind, src, dst))
    return moves, skipped


def expand(pattern, video):
    """The file name stem for *pattern* ("{video}-poster" → "Movie (2001)-poster")."""
    return pattern.replace("{video}", video or "")
