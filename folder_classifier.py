# =============================================================================
# folder_classifier.py
# Metadata & MediaClinic — is a library sub-folder a movie folder? (pure)
# Version: 0.19.2                                              ### NEW v0.19.2 B53 ###
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# A library root may hold TV series, collections of movie folders, system
# folders or loose videos.  v0.19.1 turned every sub-folder into a movie row
# full of errors.  classify_folder() decides, from the directory listing the
# scan already made, whether a folder is a movie (a row) or is ignored (listed
# in the "Ignored folders" report with its reason).  The Series tab (F2) will
# reuse it.
#
# RULES (like settings_model.py / naming_catalog.py): pure data and pure
# helpers — no I/O, no tkinter, no logging.  The only disk access is the
# optional peek(path) callback, called for folders without a video at their
# top level, at most PEEK_MAX sub-folders, stopping at the first hit.
#
# The listing passed in is duck-typed (the main script's _FolderListing):
#   .path, .files {lower: (name, path, size, mtime)}, .dirs {lower: path},
#   .error (None or the OSError text).
# =============================================================================

import re

import naming_catalog as _nc

VIDEO_EXTS = {'.mkv', '.mp4', '.avi', '.m4v', '.wmv', '.mov', '.flv',      # = the main script's
              '.ts', '.m2ts', '.mpg', '.mpeg', '.divx', '.ogm', '.webm'}     # VIDEO_EXTENSIONS
PEEK_MAX = 20

SYSTEM_NAMES = {"$recycle.bin", "system volume information", "@eadir", ".@__thumb", "#recycle",
                "#snapshot", ".appledouble", "lost+found", ".trashes"}
SEASON_RE = re.compile(r"^(?:season|saison|staffel|temporada|series)[ ._-]*\d{1,3}$|^s\d{1,2}$|^specials$", re.I)
EPISODE_RE = re.compile(r"(?:^|[^a-z0-9])s\d{1,2}[ ._-]?e\d{1,3}(?:e\d{1,3})*(?![0-9])"
                        r"|(?:^|[^0-9a-z])\d{1,2}x\d{2,3}(?![0-9])", re.I)
SERIES_FILES = ("tvshow.nfo", "series.xml")
DISC_DIRS = ("video_ts", "bdmv")
DISC_FILES = ("video_ts.ifo", "index.bdmv")

# Kinds, in the order of the report (rule order a–i of the plan, B53)
KINDS = ("series", "container", "loose_videos", "no_media", "unreadable", "system", "metadata_only")
IGNORED_KINDS = ("series", "container", "loose_videos", "no_media", "unreadable", "system")
KIND_LABEL = {
    "series":        "TV series",
    "container":     "Holding other folders",
    "loose_videos":  "Several videos",
    "no_media":      "No media",
    "unreadable":    "Could not be read",
    "system":        "System",
    "metadata_only": "Metadata without video (kept)",
}
KIND_REASON = {
    "series":        "TV series (MediaClinic handles movies; the Series tab is planned)",
    "container":     "Holds other movie / series folders — this library may be one level too high",
    "loose_videos":  "Several separate videos, not one movie — give each movie its own folder",
    "no_media":      "No video, NFO or XML",
    "unreadable":    "Could not be read",
    "system":        "System / hidden folder",
    "metadata_only": "NFO/XML but no video — kept in the table (Missing video file)",
}
KIND_GROUP = {      # group headings of the TXT export
    "series":        "TV series ({n}) — MediaClinic handles movies; the Series tab is planned",
    "container":     "Holding other folders ({n}) — this library may be one level too high",
    "loose_videos":  "Several separate videos ({n}) — give each movie its own folder",
    "no_media":      "No video, NFO or XML ({n})",
    "unreadable":    "Could not be read ({n})",
    "system":        "System / hidden folders ({n})",
    "metadata_only": "Metadata without video ({n}) — kept in the table",
}
ROOT_VIDEOS_GROUP = "Videos directly in the library folder, not in their own folder ({n})"
_COUNT_WORD = {     # the counts line: "21 TV series · 9 holding other folders …"
    "series":        "{n} TV series",
    "container":     "{n} holding other folders",
    "loose_videos":  "{n} with several separate videos",
    "no_media":      "{n} with no video, NFO or XML",
    "unreadable":    "{n} could not be read",
    "system":        "{n} system folder{s}",
}


def _ext(name):
    i = name.rfind(".")
    return name[i:].lower() if i > 0 else ""


def _stem(name):
    i = name.rfind(".")
    return name[:i] if i > 0 else name


def _base(path):
    return re.split(r"[\\/]", path.rstrip("\\/"))[-1]


def is_disc(files, dirs):
    """DVD / Blu-ray structure (B23) from the names alone."""
    return any(d in dirs for d in DISC_DIRS) or any(f in files for f in DISC_FILES)


def _is_movie_nfo_name(lower, folder_l, video_stems_l):
    return lower == "movie.nfo" or lower == f"{folder_l}.nfo" or any(lower == f"{v}.nfo" for v in video_stems_l)


def classify_folder(listing, peek=None, nfo_root=None, video_exts=None):
    """(kind, reason, detail) for one library sub-folder.

    kind: "movie" / "metadata_only" (both stay table rows) or one of
    IGNORED_KINDS.  peek(path) → a listing of a sub-folder (or None);
    nfo_root(path) → the root tag of an NFO ("movie", "tvshow" …) or None
    when unknown.  Both are optional; without them the classifier uses
    names only."""
    vx = video_exts or VIDEO_EXTS
    name = _base(listing.path)
    nl = name.lower()
    files = listing.files
    dirs = listing.dirs
    # a. system / hidden
    if nl in SYSTEM_NAMES or nl.startswith("."):
        return "system", KIND_REASON["system"], ""
    # b. unreadable
    err = getattr(listing, "error", None)
    if err:
        return "unreadable", f"Could not be read: {err}", ""
    videos = [(f[0], f[2]) for f in files.values() if _ext(f[0]) in vx]
    disc = is_disc(files, dirs)
    v_stems = [_stem(v[0]).lower() for v in videos]
    # series evidence (names only; used by c and d)
    ev = []
    for sf in SERIES_FILES:
        if sf in files:
            ev.append(files[sf][0])
    seasons = [d for d in dirs if SEASON_RE.match(_base(dirs[d]))]
    if seasons:
        ev.append(f"{len(seasons)} season folder{'s' if len(seasons) != 1 else ''}")
    episodes = [v for v in videos if EPISODE_RE.search(_stem(v[0]))]
    if len(episodes) >= 2:
        ev.append(f"{len(episodes)} episode files")
    # c. movie metadata always wins.  A "<folder>.nfo" / "<video>.nfo" is
    # opened (nfo_root) only when the folder also looks like a series — a
    # normal movie folder costs no extra file read.
    meta = []
    for low, f in files.items():
        if low == "movie.xml":
            meta.append(f[0])
        elif _ext(low) == ".nfo" and _is_movie_nfo_name(low, nl, v_stems):
            root = nfo_root(f[1]) if (nfo_root and ev and low != "movie.nfo") else None
            if root in (None, "movie"):
                meta.append(f[0])
    if meta:
        if not videos and not disc:
            return "metadata_only", KIND_REASON["metadata_only"], ", ".join(sorted(meta))
        return "movie", "", ""
    # d. TV series
    if ev:
        return "series", KIND_REASON["series"], " · ".join(ev)
    nfos_xml = [f[0] for f in files.values() if _ext(f[0]) in (".nfo", ".xml")]
    # e. container of other movie / series folders
    if not videos and not disc and peek is not None and dirs:
        subs = sorted((d for d in dirs if d not in _nc.EXTRA_FOLDERS and d != _nc.SUBS_DIR
                       and d not in SYSTEM_NAMES and not d.startswith(".")),
                      key=lambda d: d)
        hit = False
        for d in subs[:PEEK_MAX]:
            sub = peek(dirs[d])
            if sub is None:
                continue
            sf = sub.files
            if (any(_ext(f[0]) in vx for f in sf.values())
                    or any(_ext(k) == ".nfo" for k in sf) or "movie.xml" in sf
                    or is_disc(sf, sub.dirs) or any(SEASON_RE.match(_base(p)) for p in sub.dirs.values())):
                hit = True
                break
        if hit:
            names = [_base(dirs[d]) for d in subs]
            more = " …" if len(names) > 2 else ""
            return "container", KIND_REASON["container"], \
                f"e.g. {', '.join(names[:2])}{more} ({len(dirs)} sub-folder{'s' if len(dirs) != 1 else ''})"
    # f / g. videos
    if videos or disc:
        g = _nc.group_videos(videos, name) if videos else {"n_main": 1}
        if g["n_main"] >= 3:
            mains = [v[0] for v in sorted(videos) if v[0] not in g.get("kinds", {})]
            return "loose_videos", KIND_REASON["loose_videos"], ", ".join(mains[:3]) + (" …" if len(mains) > 3 else "")
        return "movie", "", ""
    # h. NFO / XML without a video (not named like a movie NFO): kept as a row
    if nfos_xml:
        return "metadata_only", KIND_REASON["metadata_only"], ", ".join(sorted(nfos_xml)[:3])
    # i. nothing a media server uses
    if not files:
        return "no_media", KIND_REASON["no_media"], "empty"
    exts = []
    for f in sorted(files.values()):
        e = _ext(f[0]) or "(no extension)"
        if e not in exts:
            exts.append(e)
    return "no_media", KIND_REASON["no_media"], \
        f"{len(files)} file{'s' if len(files) != 1 else ''}: {', '.join(exts[:4])}{' …' if len(exts) > 4 else ''}"


# ── Report text ───────────────────────────────────────────────────────────────

def _fmt_n(n):
    return f"{n:,}"


def counts_by_kind(items):
    out = {}
    for it in items:
        out[it["kind"]] = out.get(it["kind"], 0) + 1
    return out


def summary_line(n_movies, items):
    """'Scan finished: 1,204 movies. 37 folders were not added: 21 TV series · …'"""
    c = counts_by_kind(items)
    n_ign = sum(v for k, v in c.items() if k in IGNORED_KINDS)
    head = f"Scan finished: {_fmt_n(n_movies)} movie{'s' if n_movies != 1 else ''}."
    if n_ign:
        parts = [_COUNT_WORD[k].format(n=_fmt_n(c[k]), s="s" if c[k] != 1 else "") for k in IGNORED_KINDS if c.get(k)]
        head += f" {_fmt_n(n_ign)} folder{'s were' if n_ign != 1 else ' was'} not added: " + " · ".join(parts) + "."
    else:
        head += " Every folder was added."
    if c.get("metadata_only"):
        n = c["metadata_only"]
        head += f" · {_fmt_n(n)} movie{'s' if n != 1 else ''} with NFO/XML but no video {'are' if n != 1 else 'is'} in the table."
    return head


def hint_line(items, root_videos=None, roots_all_ignored=()):
    """One hint when one kind dominates (more than half of the ignored folders)."""
    if roots_all_ignored:
        return "This looks like a single movie folder — choose its parent folder as the library."
    c = counts_by_kind([i for i in items if i["kind"] in IGNORED_KINDS and i["kind"] != "system"])
    total = sum(c.values())
    if not total:
        return ""
    k, n = max(c.items(), key=lambda t: t[1])
    if n * 2 <= total:
        return ""
    return {
        "series": "Most folders here are TV series. MediaClinic handles movies; series support is planned.",
        "container": "Your movies seem to be one level deeper. Add the folders listed below as libraries "
                     "(Settings → Libraries).",
        "loose_videos": "Several folders hold many separate videos. Give each movie its own folder.",
        "no_media": "Many folders hold no video, NFO or XML. Check that this is the right library folder.",
        "unreadable": "Many folders could not be read. Check the permissions of the library folder.",
    }.get(k, "")


def report_text(data, app_version="", movies=0, kept=()):
    """The TXT export / Copy all text (lines, CRLF added by the writer).
    data: {"scan_date", "scan_kind", "libraries", "items": [...], "root_videos": {root: [names]}}
    kept: the "metadata without video" items (rows in the table)."""
    items = [i for i in data.get("items", []) if i["kind"] in IGNORED_KINDS]
    kept = list(kept)
    lines = [f"MediaClinic {app_version} — folders not added as movies".replace("  ", " "),
             f"Scan: {data.get('scan_date', '')} ({data.get('scan_kind', 'Scan')}) · Libraries: "
             + "; ".join(data.get("libraries", [])),
             f"Movies added: {_fmt_n(movies)} · Folders not added: {_fmt_n(len(items))}", ""]
    for k in IGNORED_KINDS:
        grp = sorted((i for i in items if i["kind"] == k), key=lambda i: i["path"].lower())
        if not grp:
            continue
        lines.append(KIND_GROUP[k].format(n=_fmt_n(len(grp))))
        for i in grp:
            lines.append(f"  {i['path']}" + (f"    {i['detail']}" if i.get("detail") else "")
                         + (f"    ({i['reason']})" if k == "unreadable" and i.get("reason") else ""))
        lines.append("")
    rv = [(root, n) for root, names in sorted((data.get("root_videos") or {}).items()) for n in sorted(names)]
    if rv:
        lines.append(ROOT_VIDEOS_GROUP.format(n=_fmt_n(len(rv))))
        for root, n in rv:
            lines.append(f"  {root.rstrip(chr(92) + '/')}{chr(92)}{n}")
        lines.append("")
    if kept:
        lines.append(KIND_GROUP["metadata_only"].format(n=_fmt_n(len(kept))))
        for i in sorted(kept, key=lambda i: i["path"].lower()):
            lines.append(f"  {i['path']}" + (f"    {i['detail']}" if i.get("detail") else ""))
        lines.append("")
    return lines


def merge_items(old, new, scanned_roots, key=lambda p: p.lower()):
    """Ignored items after a scan of *scanned_roots*: the other libraries'
    items are kept, the scanned ones replaced (like _kept_rows)."""
    on = {key(r) for r in scanned_roots}
    return [i for i in old if key(i.get("library_root", "")) not in on] + list(new)
