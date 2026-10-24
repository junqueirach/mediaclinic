# =============================================================================
# naming_catalog.py
# Metadata & MediaClinic — file names the media servers accept (pure data)
# Version: 0.19.2                                              ### NEW v0.19.2 F5 ###
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# Every file name Kodi, Jellyfin, Emby and Plex read for a movie in its own
# folder (roadmap Part 8, F5.1; checked against the official sources on
# 2026-10-15).  The scanner reads these tables through one resolver, so a new
# accepted name is one line here.  F3 (media server profiles) reuses them.
#
# RULES (like settings_model.py): pure data and pure helpers only —
# no I/O, no tkinter, no logging.
#
# Patterns: "{video}" = the video file name without extension, "{folder}" =
# the movie folder name.  Servers: "kodi", "jellyfin", "emby", "plex".
# =============================================================================

import re

SERVERS = ("kodi", "jellyfin", "emby", "plex")
SERVER_LABEL = {"kodi": "Kodi", "jellyfin": "Jellyfin", "emby": "Emby", "plex": "Plex"}

SOURCES = {
    "kodi": "Kodi source (xbmc/xbmc): utils/ArtUtils.cpp, video/tags/VideoTagLoaderNFO.cpp, "
            "settings/AdvancedSettings.cpp, video/VideoUtils.cpp",
    "jellyfin": "Jellyfin docs (Movies, Local .nfo metadata) + source: MovieNfoSaver.cs, "
                "LocalImageProvider.cs, NamingOptions.cs",
    "emby": "Emby support article 'Movie Naming'; NFO/XML plugins: forum posts by Emby staff",
    "plex": "Plex support: Local Media Assets – Movies; Local Files for Trailers and Extras; "
            "Naming and Organizing your Movie Media Files; Using NFO Metadata Files",
}
TO_VERIFY = ("Emby NFO names (no official list; same code origin as Jellyfin)",
             "Emby external subtitle names (no official article; treated like Jellyfin)")

# ── Image extensions ─────────────────────────────────────────────────────────
# Reading order of the extensions for one name: the formats MediaClinic writes
# first (unchanged B23 behaviour), then the others the servers accept.
ART_EXTS = (".jpg", ".png", ".jpeg", ".webp", ".gif", ".bmp")
SERVER_ART_EXTS = {
    "kodi":     (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tbn"),
    "jellyfin": (".png", ".jpg", ".jpeg", ".webp", ".tbn", ".gif", ".svg"),
    "emby":     (".jpg", ".jpeg", ".png", ".gif", ".tbn"),
    "plex":     (".jpg", ".jpeg", ".png", ".tbn"),
}
EXT_FORMAT = {".jpg": "JPEG", ".jpeg": "JPEG", ".tbn": "JPEG", ".png": "PNG",
              ".webp": "WEBP", ".gif": "GIF", ".bmp": "BMP"}

# ── Poster / fanart / folder names, in reading order ─────────────────────────
# (pattern, servers that read it).  The Kodi names keep B23's order so a Kodi
# library resolves exactly as before; the Jellyfin / Emby / Plex names follow.
POSTER_NAMES = [
    ("{video}-poster",  ("kodi", "jellyfin", "emby")),
    ("poster",          ("kodi", "jellyfin", "emby", "plex")),
    ("{video}",         ("jellyfin", "emby", "plex")),
    ("{video}-cover",   ("jellyfin", "emby")),
    ("{video}-default", ("jellyfin", "emby")),
    ("{video}-movie",   ("jellyfin", "emby")),
    ("{video}-folder",  ("jellyfin",)),
    ("cover",           ("jellyfin", "emby", "plex")),
    ("default",         ("jellyfin", "emby", "plex")),
    ("movie",           ("jellyfin", "emby", "plex")),
]
POSTER_TBN = [("{video}.tbn", ("kodi",)), ("movie.tbn", ("kodi",))]   # legacy Kodi thumbnails
FOLDER_NAMES = [("folder", ("kodi", "jellyfin", "emby", "plex"))]
FANART_NAMES = [
    ("{video}-fanart",  ("kodi", "jellyfin", "plex")),
    ("fanart",          ("kodi", "jellyfin", "emby", "plex")),
    ("backdrop",        ("jellyfin", "emby", "plex")),
    ("background",      ("jellyfin", "emby", "plex")),
    ("art",             ("jellyfin", "emby", "plex")),
]
ART_NAMES = {"poster": POSTER_NAMES, "folder": FOLDER_NAMES, "fanart": FANART_NAMES}

# Extra backdrops (lower-case regex on the file name stem; "{video}" = the
# escaped lower-case video name).  The extrafanart sub-folder counts too.
BACKDROP_STEM_PATTERNS = (
    r"backdrop\d*",          # backdrop, backdrop1 … (Emby, Jellyfin; MediaClinic's own names)
    r"backdrop-\d+",         # Jellyfin
    r"fanart-?\d+",          # Kodi fanart1 …, Jellyfin / Emby fanart-1 …
    r"{video}-fanart\d+",    # Kodi "<video>-fanart1"
    r"background(?:-\d+)?",  # Jellyfin / Emby / Plex
    r"art-\d+",              # Jellyfin / Emby
)
EXTRAFANART_DIR = "extrafanart"

# Extra artwork: information only (user decision 2026-10-15, no health rules)
EXTRA_ART_KINDS = ("clearlogo", "logo", "landscape", "thumb", "banner", "disc", "cdart", "discart",
                   "clearart", "keyart", "characterart")

# ── Metadata files ────────────────────────────────────────────────────────────
# NFO reading order (user decision 2026-10-15): movie.nfo first — Kodi, Jellyfin
# and Emby read it first — then "<video>.nfo", then MediaClinic's "<folder>.nfo"
# (Jellyfin reads it for disc folders).  Disc NFOs come before all of them.
NFO_NAMES = [
    ("movie.nfo",    ("kodi", "jellyfin", "emby", "plex")),
    ("{video}.nfo",  ("kodi", "jellyfin", "emby", "plex")),
    ("{folder}.nfo", ("jellyfin",)),
]
DISC_NFO_NAMES = ("VIDEO_TS.nfo", "index.nfo")
XML_NAME = "movie.xml"                 # only reader: Emby's legacy XML plugin
OLD_XML_NAMES = ("mymovies.xml",)      # My Movies / MediaBrowser Classic: no current server reads it

# ── Other videos in the movie folder ─────────────────────────────────────────
_SEP = r"[-._ ]"
TRAILER_RE = re.compile(r"(?:^|" + _SEP + r")trailer\d*$|^movie-trailer$", re.I)
SAMPLE_RE = re.compile(r"(?:^|" + _SEP + r")sample\d*$", re.I)
EXTRA_SUFFIX_RE = re.compile(r"-(?:behindthescenes|deletedscene|deleted|featurette|interview|scene|clip|short|extra|other)\d*$", re.I)
EXTRA_FOLDERS = ("trailers", "sample", "samples", "extras", "extra", "specials", "shorts", "scenes", "featurettes",
                 "behind the scenes", "deleted scenes", "interviews", "clips", "other", "theme-music", "backdrops")
# multi-part (stack): "<name> cd1", "<name> - part 2", "<name>.disc3", "<name>-pt a", "<name> a"
STACK_RE = re.compile(r"^(?P<base>.*?)(?:" + _SEP + r"*(?:cd|dvd|part|pt|disc|disk|file)" + _SEP + r"*(?P<n>\d+|[a-h])"
                      r"|" + _SEP + r"+(?P<l>[a-h]))$", re.I)                # a bare letter needs a separator (Kodi)
EDITION_RE = re.compile(r"\{edition-[^}]+\}", re.I)                  # Plex editions
VERSION_SEP = " - "                                                  # Jellyfin / Emby "{folder} - 1080p"
VIDEO_KIND_LABEL = {"trailer": "trailer", "sample": "sample", "extra": "extra",
                    "part": "part", "version": "version"}

# ── External subtitles ───────────────────────────────────────────────────────
SUB_EXTS = (".srt", ".sub", ".idx", ".ass", ".ssa", ".smi", ".sami", ".vtt", ".sup", ".mks", ".utf",
            ".rt", ".aqt", ".jss")
SUB_FLAGS = {"forced": "forced", "foreign": "forced", "default": "default",
             "sdh": "hearing impaired", "cc": "hearing impaired", "hi": "hearing impaired"}
SUBS_DIR = "subs"                                                    # Kodi: Subs\ next to the video


def expand(pattern, video=None, folder=None):
    """'{video}-poster' → 'Movie (1999)-poster'; None when a needed part is missing."""
    if "{video}" in pattern and not video:
        return None
    if "{folder}" in pattern and not folder:
        return None
    return pattern.replace("{video}", video or "").replace("{folder}", folder or "")


def servers_text(servers):
    """('kodi', 'jellyfin') → 'Kodi, Jellyfin'."""
    return ", ".join(SERVER_LABEL[s] for s in SERVERS if s in servers)


def classify_video(stem):
    """Kind of a video file by its name alone: 'trailer' / 'sample' / 'extra' or
    None (a candidate main video).  Stacks and versions need the other names."""
    if TRAILER_RE.search(stem):
        return "trailer"
    if SAMPLE_RE.search(stem):
        return "sample"
    if EXTRA_SUFFIX_RE.search(stem):
        return "extra"
    return None


def stack_base(stem):
    """(base, part_key) when *stem* ends with a stack marker, else None."""
    m = STACK_RE.match(stem)
    if not m or not m.group("base").strip(" -._"):
        return None
    part = m.group("n") or m.group("l")
    return m.group("base").strip(" -._").lower(), (int(part) if part.isdigit() else ord(part.lower()) - 96)


def _stem(name):
    i = name.rfind(".")
    return name[:i] if i > 0 else name


def group_videos(videos, folder_name=""):
    """The main video and the others of one folder (F5 rules: trailers, samples,
    extras, the parts of a stack, versions / editions).
    videos: [(name, size)].  Returns {"main": name | None, "kinds": {name: kind},
    "n_main": movies that remain (2+ = really "Multiple video files"),
    "group": "stack" / "versions" / None}."""
    vids = sorted(videos, key=lambda f: f[1], reverse=True)
    kinds, mains = {}, []
    for f in vids:
        k = classify_video(_stem(f[0]))
        if k:
            kinds[f[0]] = k
        else:
            mains.append(f)
    group = None
    if len(mains) > 1:
        stems = [_stem(f[0]) for f in mains]
        sb = [stack_base(st) for st in stems]
        if all(sb) and len({b for b, _p in sb}) == 1:
            order = sorted(zip(sb, mains), key=lambda t: t[0][1])
            mains = [f for _b, f in order]
            for f in mains[1:]:
                kinds[f[0]] = "part"
            group = "stack"
        else:
            heads = {st.split(VERSION_SEP, 1)[0].strip().lower() for st in stems}
            folder = (folder_name or "").lower()
            same_head = len(heads) == 1 and any(VERSION_SEP in st for st in stems)
            plex_ed = (any(EDITION_RE.search(st) for st in stems)
                       and len({EDITION_RE.sub("", st).strip(" -").lower() for st in stems}) == 1)
            by_folder = bool(folder) and all(st.lower().startswith(folder + VERSION_SEP) or st.lower() == folder
                                             for st in stems)
            if same_head or plex_ed or by_folder:
                for f in mains[1:]:                       # sorted by size: the largest stays
                    kinds[f[0]] = "version"
                group = "versions"
    if not mains and vids:                                # only "extras": the largest is the movie
        mains = [vids[0]]
        kinds.pop(vids[0][0], None)
    return {"main": mains[0][0] if mains else None, "kinds": kinds,
            "n_main": 1 if group else len(mains), "group": group}


def parse_subtitle_name(stem, video_stem=None):
    """'Movie (1999).pt.forced' → ('pt', ['forced']).  The language is the first
    token after the video name that is not a flag ('hi' alone = Hindi)."""
    if video_stem and stem.lower().startswith(video_stem.lower()):
        tokens = [t for t in stem[len(video_stem):].split(".") if t]
    else:                                   # the first dot part is the name itself
        tokens = [t for t in stem.split(".") if t][1:]
    lang, flags = None, []
    for t in tokens:
        tl = t.lower()
        if tl in SUB_FLAGS and not (tl == "hi" and lang is None and len(tokens) == 1):
            flags.append(SUB_FLAGS[tl])
        elif lang is None and len(t) <= 20:
            lang = t
    return (lang or "unknown"), flags
