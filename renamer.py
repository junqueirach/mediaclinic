# =============================================================================
# renamer.py — "Rename Movie Folders and Files": the folder name from a pattern, the files follow it
# (pure: no Tk, no network, no disk access; the app lists the folder and does the renames)
# MediaClinic v0.20.2 RN                                          ### NEW v0.20.2 RN ###
#
# The user's rules (plan Part 9h.2 "RN design" + "RN consistency check" RN-k1…k12, row 8; tests 2026-11-23 in
# Workbench\Server Tests\RENAMER_TEST_2026-11-23.md, Media Servers Reference §1 / §5 lessons 36–40):
#   - only the FOLDER has a pattern; the files named after the video (or after the old folder name) follow it: the
#     video, <video>.nfo, <video>-poster.jpg, subtitles <video>.pt.srt, <video>-trailer.mkv … (RN-k2, RN-c3);
#     movie.nfo, poster.jpg, .actors, extrafanart and every sub-folder stay; inside a disc folder nothing is renamed;
#   - parts keep their marker ("-cd1"), versions keep their label (" - 1080p"): only the name before it changes;
#   - pattern 5 writes "[tmdb-<id>]": the one ID tag Jellyfin, Emby AND Plex read (tested 2026-11-23; Plex ignores
#     "[tmdbid-…]"); a movie without a TMDB ID is skipped for that pattern, not given another tag;
#   - Windows-safe NFC names on every OS: ":" → " - ", \ / * ? " < > | removed, no trailing dot or space; a reserved
#     Windows name (CON, NUL, COM1 …) is listed as not renamed (no invented name); names are compared after NFC;
#   - a bracket group whose field is empty vanishes with its brackets ("Title (Year) [ ]" never appears).
# Series-ready (SR0): nothing here knows movies only — a show folder takes the same pattern and file-follow rules.
# =============================================================================
from __future__ import annotations

import os
import re
import unicodedata

# ── patterns ─────────────────────────────────────────────────────────────────
PATTERNS = {                      # the built-in patterns (the user's list, plan RN design; 7 = custom)
    1: "{title} ({year})",
    2: "{title} ({year}) [{quality}]",
    3: "{title} ({year}) [{quality}] [{genre}]",
    4: "{title} ({year}) [imdbid-{imdb}]",          # read by Jellyfin, Emby and Plex (tested 2026-11-23)
    5: "{title} ({year}) [tmdb-{tmdb}]",            # the one TMDB form all three read (tested 2026-11-23)
    6: "{title} ({year}) [{quality} {codec} {audio}]",
}
CUSTOM = 7
DEFAULT_PATTERN = 1
REQUIRED = {4: "imdb", 5: "tmdb"}                   # the pattern makes no sense without it → the movie is skipped
TOKENS = ("title", "originaltitle", "year", "quality", "codec", "hdr", "audio", "genre", "collection", "rating",
          "imdb", "tmdb")
CHANGING = ("quality", "codec", "hdr", "audio", "genre", "rating")   # change over time → the folder renames again (RN-c2)
_TOKEN_RE = re.compile(r"\{(" + "|".join(TOKENS) + r")\}")
_GROUPS = {"(": ")", "[": "]", "{": "}"}

ARTICLES = {                      # "The Matrix" → "Matrix, The" (option, off by default)
    "en": ("The", "A", "An"),
    "pt": ("O", "A", "Os", "As", "Um", "Uma"),
    "es": ("El", "La", "Los", "Las", "Un", "Una"),
    "fr": ("Le", "La", "Les", "L'", "Un", "Une"),
    "de": ("Der", "Die", "Das", "Ein", "Eine"),
    "it": ("Il", "Lo", "La", "I", "Gli", "Le", "L'", "Un", "Uno", "Una"),
}

RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
MAX_PATH = 255                    # longer full paths are a conflict (many players and Explorer, RN-k7)
_ILLEGAL = re.compile(r'[\\/*?"<>|\x00-\x1f]')


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def same_name(a, b):
    """True when two names are the same after NFC (macOS clients send NFD, RN-k9) — case counts."""
    return nfc(a) == nfc(b)


def quality_text(q):
    """The row's video quality as a name part: '4K UHD' → '2160p', '576p/DVD' → '576p', '—' → ''."""
    q = (q or "").strip()
    if not q or q in ("—", "-"):
        return ""
    if q.upper().startswith("4K"):
        return "2160p"
    return q.split("/")[0].strip()


def move_article(title, lang="en"):
    """'The Matrix' → 'Matrix, The' with the articles of *lang* (and English); unchanged otherwise."""
    t = (title or "").strip()
    arts = tuple(ARTICLES.get((lang or "en")[:2].lower(), ())) + ARTICLES["en"]
    for a in sorted(set(arts), key=len, reverse=True):
        if a.endswith("'"):
            if t.lower().startswith(a.lower()) and len(t) > len(a):
                return f"{t[len(a):].strip()}, {t[:len(a)]}"
        elif t.lower().startswith(a.lower() + " ") and len(t) > len(a) + 1:
            return f"{t[len(a) + 1:].strip()}, {t[:len(a)]}"
    return t


def pattern_text(pattern, custom=""):
    """The pattern string of a choice (1–6 built in, 7 = the custom text)."""
    try:
        pattern = int(pattern)
    except (TypeError, ValueError):
        pattern = DEFAULT_PATTERN
    if pattern == CUSTOM:
        return (custom or "").strip() or PATTERNS[DEFAULT_PATTERN]
    return PATTERNS.get(pattern, PATTERNS[DEFAULT_PATTERN])


def changing_tokens(text):
    """The tokens of *text* whose value changes over time (⚠ in the window)."""
    return [t for t in _TOKEN_RE.findall(text or "") if t in CHANGING]


def unknown_tokens(text):
    """'{foo}' parts that are not tokens (shown as an error in the window)."""
    return [m for m in re.findall(r"\{([^{}]*)\}", text or "") if m not in TOKENS]


def _value(fields, tok):
    v = fields.get(tok)
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        v = v[0] if v else ""
    return str(v).strip()


def render(text, fields, *, article=False, lang="en", dots=False):
    """The name for *fields* (title, year, …).  A bracket group with an empty field inside vanishes with its
    brackets; the result is NOT yet made safe (see safe_name)."""
    fields = dict(fields or {})
    if article and fields.get("title"):
        fields["title"] = move_article(fields["title"], lang)
    out, i, n = [], 0, len(text or "")
    text = text or ""
    while i < n:
        ch = text[i]
        if ch in _GROUPS and not _TOKEN_RE.match(text, i):     # "{title}" is a token, not a group
            close = text.find(_GROUPS[ch], i + 1)
            if close > 0:
                inner = text[i + 1:close]
                toks = _TOKEN_RE.findall(inner)
                empty = [t for t in toks if not _value(fields, t)]
                literal = _TOKEN_RE.sub("", inner).strip(" ")
                # the group goes when all its fields are empty, or when it has its own text ("tmdb-{tmdb}") and a
                # field of it is empty; "[{quality} {codec}]" with only the codec empty keeps "[1080p]"
                if toks and (len(empty) == len(toks) or (literal and empty)):
                    i = close + 1
                    continue
                filled = _TOKEN_RE.sub(lambda m: _value(fields, m.group(1)), inner)
                out.append(ch + re.sub(r"\s+", " ", filled).strip() + _GROUPS[ch])
                i = close + 1
                continue
        m = _TOKEN_RE.match(text, i)
        if m:
            out.append(_value(fields, m.group(1)))
            i = m.end()
            continue
        out.append(ch)
        i += 1
    name = re.sub(r"\s+", " ", "".join(out)).strip(" -_,")
    name = re.sub(r"\(\s*\)|\[\s*\]|\{\s*\}", "", name)
    name = re.sub(r"\s+", " ", name).strip(" -_,")
    if dots:
        name = re.sub(r"\.{2,}", ".", re.sub(r"\s+", ".", name)).strip(".")
    return name


def safe_name(name):
    """(Windows-safe NFC name, problem | None).  ':' → ' - ', illegal characters removed, no trailing dot / space.
    problem: 'empty' | 'reserved' (the name is then not used: no invented name, RN-k7)."""
    s = nfc(name)
    s = re.sub(r"\s*:\s*", " - ", s)
    s = _ILLEGAL.sub("", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(". ").strip()
    if not s:
        return "", "empty"
    if s.split(".")[0].strip().upper() in RESERVED:
        return s, "reserved"
    return s, None


def folder_name_for(fields, pattern, custom="", *, article=False, lang="en", dots=False):
    """(name, problem): problem 'no_imdb' / 'no_tmdb' (pattern 4 / 5 without the ID), 'no_title', 'empty',
    'reserved', or None."""
    try:
        p = int(pattern)
    except (TypeError, ValueError):
        p = DEFAULT_PATTERN
    need = REQUIRED.get(p)
    if need and not _value(fields, need):
        return "", "no_" + need
    if not _value(fields, "title") and not _value(fields, "originaltitle"):
        return "", "no_title"
    text = pattern_text(p, custom)
    if "{year}" in text and not _value(fields, "year"):           # "Heat" alone matches worse than "Heat (1995)": skipped
        return "", "no_year"
    return safe_name(render(text, fields, article=article, lang=lang, dots=dots))


# ── the files that follow the folder ─────────────────────────────────────────
_FOLLOW_REST = re.compile(r"^(?:\.|-|_| - | \{edition-| (?=(?:cd|dvd|part|pt|disc|disk|file)[ _.-]*(?:\d|[a-h]\b)))",
                          re.I)


def follows(name, base):
    """True when the file *name* is named after *base* (the video's name or the old folder name): 'base.mkv',
    'base-poster.jpg', 'base.pt.srt', 'base-cd1.mkv', 'base - 1080p.mkv', 'base-trailer.mkv' …"""
    if not base or len(name) <= len(base) or name[:len(base)].lower() != base.lower():
        return False
    return bool(_FOLLOW_REST.match(name[len(base):]))


def video_base(main_video, group, folder_name, stack_title=None, version_sep=" - "):
    """The name the movie's files are named after: the video's name without its extension; for a stack the name
    before the part marker (Kodi's stack name); for versions the name before ' - <label>'."""
    stem = os.path.splitext(main_video or "")[0]
    if group == "stack" and stack_title:
        return stack_title
    if group == "versions":
        head = stem.split(version_sep, 1)[0].strip()
        if folder_name and stem.lower().startswith(folder_name.lower()):
            return folder_name
        return head or stem
    return stem


def file_moves(files, bases, new_stem):
    """[(old name, new name)] for the top-level *files* named after one of *bases* (longest first); (moves,
    problem) — problem 'same_target' when two files would get one name."""
    bases = sorted({b for b in bases if b}, key=len, reverse=True)
    moves, targets = [], {}
    for name in sorted(files):
        for b in bases:
            if follows(name, b):
                new = new_stem + name[len(b):]
                if not same_name(new, name):
                    moves.append((name, new))
                k = nfc(new).lower()
                if k in targets and targets[k] != name:
                    return [], "same_target"
                targets[k] = name
                break
    return moves, None


def plan_movie(folder_path, files, main_video, group, *, new_folder, rename_folder=True, files_follow=True,
               disc=False, stack_title=None, exists=None, siblings=None):
    """One movie's renames.  *files* = the names of the files directly in the folder; *exists(path)* tells whether
    a path is taken (the app passes os.path.exists; None = nothing is).  Returns
    {"folder": (old path, new path) | None, "files": [(old name, new name)], "problem": None | code, "case_only": bool}
    *siblings* = the names in the parent folder (None = not listed).
    Problems: 'exists' (the new folder name is taken, also in another case on a case-sensitive NAS), 'same_target', 'file_exists' (a file's new name is taken by a
    file that does not move), 'too_long', 'nothing' (already matches)."""
    exists = exists or (lambda p: False)
    parent, old_folder = os.path.split(os.path.normpath(folder_path))
    out = {"folder": None, "files": [], "problem": None, "case_only": False}
    target_folder = new_folder if rename_folder else old_folder
    if rename_folder and not same_name(new_folder, old_folder):
        new_path = os.path.join(parent, new_folder)
        case_only = nfc(new_folder).lower() == nfc(old_folder).lower()
        # a NAS (Linux, SMB) is case-sensitive: "The Matrix" may exist next to "the matrix" (RN-k8). *siblings* = the
        # names in the parent folder, compared exactly (after NFC)
        if case_only and siblings is not None and nfc(new_folder) in {nfc(x) for x in siblings}:
            out["problem"] = "exists"
            return out
        if not case_only and exists(new_path):
            out["problem"] = "exists"
            return out
        out["folder"] = (os.path.join(parent, old_folder), new_path)
        out["case_only"] = case_only
    if files_follow:
        bases = [old_folder]
        if not disc and main_video:
            bases.append(video_base(main_video, group, old_folder, stack_title))
        moves, prob = file_moves(files, bases, target_folder)
        if prob:
            return {**out, "folder": None, "problem": prob}
        sources = {nfc(o).lower() for o, _n in moves}
        for o, n in moves:
            k = nfc(n).lower()
            if k not in sources and k != nfc(o).lower() and nfc(n).lower() in {nfc(f).lower() for f in files}:
                return {**out, "folder": None, "files": [], "problem": "file_exists"}
        out["files"] = moves
    longest = max([len(os.path.join(parent, target_folder, n)) for _o, n in out["files"]]
                  + [len(os.path.join(parent, target_folder))])
    if longest > MAX_PATH:
        return {**out, "folder": None, "files": [], "problem": "too_long"}
    if not out["folder"] and not out["files"]:
        out["problem"] = "nothing"
    return out


def batch_conflicts(plans):
    """{index: 'same_folder'} for movies of one run that would get the same new folder (after NFC, any case)."""
    seen, bad = {}, {}
    for i, p in enumerate(plans):
        f = p.get("folder") if p else None
        if not f:
            continue
        k = os.path.normcase(nfc(f[1])).lower()
        if k in seen:
            bad[i] = bad[seen[k]] = "same_folder"
        else:
            seen[k] = i
    return bad


# ── after a folder rename: the row's paths ───────────────────────────────────
def _norm(p):
    return os.path.normcase(os.path.normpath(p))


def repath(value, old, new):
    """*value* (a row, a list, a path) with every path under *old* moved under *new* (case-insensitive on Windows).
    Strings that are not under *old* are kept as they are."""
    if isinstance(value, str):
        if not value:
            return value
        nv, no = _norm(value), _norm(old)
        if nv == no:
            return os.path.normpath(new)
        if nv.startswith(no.rstrip("\\/") + os.sep):
            return os.path.join(os.path.normpath(new), os.path.normpath(value)[len(os.path.normpath(old).rstrip("\\/")) + 1:])
        return value
    if isinstance(value, list):
        return [repath(v, old, new) for v in value]
    if isinstance(value, tuple):
        return tuple(repath(v, old, new) for v in value)
    if isinstance(value, dict):
        return {(repath(k, old, new) if isinstance(k, str) else k): repath(v, old, new) for k, v in value.items()}
    return value
