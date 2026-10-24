# =============================================================================
# Metadata & MediaClinic — sort engine (pure: no Tk, no file access)
# Version: 0.19.3                                              ### NEW v0.19.3 B63 ###
#
# Up to three sort levels ("Sort by …, then by …"), each a column key and a
# direction.  The direction is shown in words that fit the column ("A → Z",
# "Newest first", "Worst first" …).  Rules:
#   - empty values (no rating, no poster, unknown quality, no date) always go
#     last, in both directions (unless a level asks for "empty first");
#   - the final tie-break is always Movie Name A → Z, then Year — never
#     reversed;
#   - mixed directions without negating strings: each row's keys are computed
#     once, then a stable sort per level from the last level to the first.
# The value functions come from the main script (they know the row fields),
# so the Series tab (F2) can pass its own columns later.
# =============================================================================

MAX_LEVELS = 3
MAX_USER_PRESETS = 20

# kind → [(direction id, label, reverse)] — the first one is the default
DIRECTIONS = {
    "text":     [("asc", "A → Z", False), ("desc", "Z → A", True)],
    "date":     [("newest", "Newest first", True), ("oldest", "Oldest first", False)],
    "number":   [("high", "High → low", True), ("low", "Low → high", False)],
    "quality":  [("worst", "Worst first", True), ("best", "Best first", False)],   # value: tier index, 0 = best
    "count":    [("most", "Most first", True), ("fewest", "Fewest first", False)],
    "size":     [("largest", "Largest first", True), ("smallest", "Smallest first", False)],
    "status":   [("errors", "Errors first", True), ("ok", "OK first", False)],     # value: 0 ok … 3 error
    "health":   [("errors", "Errors first", False), ("warnings", "Warnings first", False), ("ok", "OK first", False)],
    "presence": [("missing", "Missing first", False), ("present", "Present first", True)],   # value: 0 missing, 1 present
}

# (key, label, kind) — every table column once, in table order, then "More"
COLUMNS = [
    ("movie_name", "Movie Name", "text"),
    ("year", "Year", "date"),
    ("genre", "Genres", "text"),
    ("rating", "Rating", "number"),
    ("votes", "Votes", "number"),
    ("source", "Source", "status"),
    ("poster", "Poster quality", "quality"),
    ("folder", "Folder image quality", "quality"),
    ("fanart", "Fanart quality", "quality"),
    ("backdrops", "Backdrops", "count"),
    ("nfo", ".nfo", "status"),
    ("xml", ".xml", "status"),
    ("language", "Language", "text"),
    ("vid_ext", "Video (file type)", "text"),
    ("vid_size", "Video size", "size"),
    ("quality", "Video quality", "quality"),
    ("audio", "Audio", "text"),
    ("lang_ok", "Lang OK?", "presence"),
    ("subs", "Subtitles", "presence"),
    ("library", "Library", "text"),
]
MORE = [
    ("health", "Health", "health"),                                  # v0.19.3 B69 — short label, first in the list
    ("issues", "Number of issues", "count"),
    ("date_added", "Date added", "date"),
]
ALL_KEYS = COLUMNS + MORE
# ### NEW v0.19.3 B69 ### the order of the "Sort by" / "then by" lists: Health
# and Number of issues first (in sight without scrolling), then the columns
MENU_KEYS = ["health", "issues"] + [k for k, _l, _kd in COLUMNS] + ["date_added"]
KIND = {k: kind for k, _l, kind in ALL_KEYS}
LABEL = {k: lbl for k, lbl, _kd in ALL_KEYS}

DEFAULT_SPEC = [{"key": "movie_name", "dir": "asc"}]

# built-in presets, in menu order (Ctrl+1 … Ctrl+6)
BUILTIN_PRESETS = [
    {"name": "Problems first", "levels": [{"key": "health", "dir": "errors"}, {"key": "issues", "dir": "most"}]},
    {"name": "Worst artwork first", "levels": [{"key": "poster", "dir": "worst"}, {"key": "fanart", "dir": "worst"}]},
    {"name": "Missing metadata", "levels": [{"key": "source", "dir": "errors"},
                                            {"key": "rating", "dir": "low", "empty": "first"}]},
    {"name": "Best rated", "levels": [{"key": "rating", "dir": "high"}, {"key": "votes", "dir": "high"}]},
    {"name": "Biggest files", "levels": [{"key": "vid_size", "dir": "largest"}]},
    {"name": "By library", "levels": [{"key": "library", "dir": "asc"}, {"key": "movie_name", "dir": "asc"}]},
]

# the 37 texts of the old "Sort:" list (v0.11–v0.19.2) → one level
OLD_SORT_OPTIONS = {
    "Movie Name (A-Z)": ("movie_name", "asc"), "Movie Name (Z-A)": ("movie_name", "desc"),
    "Year (older first)": ("year", "oldest"), "Year (newer first)": ("year", "newest"),
    "Genre (A-Z)": ("genre", "asc"), "Genre (Z-A)": ("genre", "desc"),
    "Rating (high→low)": ("rating", "high"), "Rating (low→high)": ("rating", "low"),
    "Votes (high→low)": ("votes", "high"), "Votes (low→high)": ("votes", "low"),
    "Sources (Errors 1st)": ("source", "errors"), "Sources (OK 1st)": ("source", "ok"),
    "Poster Quality (high→low)": ("poster", "best"), "Poster Quality (low→high)": ("poster", "worst"),
    "Folder Quality (high→low)": ("folder", "best"), "Folder Quality (low→high)": ("folder", "worst"),
    "Fanart Quality (high→low)": ("fanart", "best"), "Fanart Quality (low→high)": ("fanart", "worst"),
    "Backdrops (most)": ("backdrops", "most"), "Backdrops (fewest)": ("backdrops", "fewest"),
    "Language (A→Z)": ("language", "asc"), "Language (Z→A)": ("language", "desc"),
    "Video Quality (best first)": ("quality", "best"), "Video Quality (worst first)": ("quality", "worst"),
    "Video size (lg→sm)": ("vid_size", "largest"), "Video size (sm→lg)": ("vid_size", "smallest"),
    "Lang OK? (Y first)": ("lang_ok", "present"), "Lang OK? (N first)": ("lang_ok", "missing"),
    "Health (Errors 1st)": ("health", "errors"), "Health (Warning 1st)": ("health", "warnings"),
    "Health (OK 1st)": ("health", "ok"),
}
_OLD_BY_LEVEL = {v: k for k, v in OLD_SORT_OPTIONS.items()}


def directions(key):
    return DIRECTIONS[KIND.get(key, "text")]


def default_dir(key):
    return directions(key)[0][0]


def dir_label(key, d):
    for did, lbl, _rev in directions(key):
        if did == d:
            return lbl
    return directions(key)[0][1]


def next_dir(key, d):
    """The direction after *d* (the button's click)."""
    ids = [did for did, _l, _r in directions(key)]
    return ids[(ids.index(d) + 1) % len(ids)] if d in ids else ids[0]


def _reverse(key, d):
    for did, _lbl, rev in directions(key):
        if did == d:
            return rev
    return directions(key)[0][2]


def clean_spec(spec):
    """A valid list of 1–3 levels (known keys, known directions, no key twice)."""
    out, seen = [], set()
    for lvl in spec or []:
        if not isinstance(lvl, dict):
            continue
        k = lvl.get("key")
        if k not in KIND or k in seen:
            continue
        d = lvl.get("dir")
        if d not in [did for did, _l, _r in directions(k)]:
            d = default_dir(k)
        item = {"key": k, "dir": d}
        if lvl.get("empty") == "first":
            item["empty"] = "first"
        out.append(item)
        seen.add(k)
        if len(out) == MAX_LEVELS:
            break
    return out or [dict(x) for x in DEFAULT_SPEC]


def spec_from_old(text):
    """The level for an old "Sort:" text (unknown → Movie Name A → Z)."""
    k, d = OLD_SORT_OPTIONS.get(str(text or ""), ("movie_name", "asc"))
    return [{"key": k, "dir": d}]


def old_text_for(spec):
    """The old "Sort:" text of level 1, when there is one (kept for older versions)."""
    spec = clean_spec(spec)
    return _OLD_BY_LEVEL.get((spec[0]["key"], spec[0]["dir"]), "Movie Name (A-Z)")


def describe(spec, label=None):
    """"Sorted by Poster quality (worst first), then Rating (high → low), then Movie Name (A → Z)"."""
    label = label or LABEL
    soft = lambda t: t if len(t) > 1 and t[1] == " " else t[:1].lower() + t[1:]   # "A → Z" stays, "Worst first" → "worst first"
    parts = []
    for lvl in clean_spec(spec):
        txt = f"{label.get(lvl['key'], lvl['key'])} ({soft(dir_label(lvl['key'], lvl['dir']))}"
        if lvl.get("empty") == "first":
            txt += ", empty first"
        parts.append(txt + ")")
    if not any(l["key"] == "movie_name" for l in clean_spec(spec)):
        parts.append("Movie Name (A → Z)")
    return "Sorted by " + ", then ".join(parts) + " · empty values last"


def heading_marks(spec):
    """{key: "▲1" / "▼2" …} for the column headings."""
    out = {}
    for i, lvl in enumerate(clean_spec(spec), 1):
        out[lvl["key"]] = ("▼" if _reverse(lvl["key"], lvl["dir"]) else "▲") + str(i)
    return out


def click_heading(spec, key, shift=False):
    """The new spec after a click on a column heading.
    click: the column becomes level 1 (clicked again: reversed); the other
    levels follow.  Shift+click: added as the next level (or reversed when it
    is one already); a 4th replaces level 3."""
    spec = clean_spec(spec)
    if key not in KIND:
        return spec
    keys = [l["key"] for l in spec]
    if shift:
        if key in keys:
            i = keys.index(key)
            spec[i] = {"key": key, "dir": next_dir(key, spec[i]["dir"])}
            return spec
        if len(spec) >= MAX_LEVELS:
            spec = spec[:MAX_LEVELS - 1]
        return spec + [{"key": key, "dir": default_dir(key)}]
    if keys and keys[0] == key:
        spec[0] = {"key": key, "dir": next_dir(key, spec[0]["dir"])}
        return spec
    first = next((l for l in spec if l["key"] == key), None)
    lvl = {"key": key, "dir": first["dir"] if first else default_dir(key)}
    return clean_spec([lvl] + [l for l in spec if l["key"] != key])


def sort_rows(rows, spec, value_fns, name_key, year_key):
    """The rows in the order of *spec*.  value_fns[key](row, direction) gives a
    comparable value or None (empty).  name_key / year_key give the final
    tie-break (never reversed)."""
    out = sorted(rows, key=lambda r: (name_key(r), year_key(r)))
    for lvl in reversed(clean_spec(spec)):
        fn = value_fns.get(lvl["key"])
        if fn is None:
            continue
        d = lvl["dir"]
        vals = [(fn(r, d), r) for r in out]
        present = [(v, r) for v, r in vals if v is not None]
        empty = [r for v, r in vals if v is None]
        present.sort(key=lambda t: t[0], reverse=_reverse(lvl["key"], d))
        ordered = [r for _v, r in present]
        out = (empty + ordered) if lvl.get("empty") == "first" else (ordered + empty)
    return out


def valid_preset_name(name, presets, old=None):
    """'' when *name* can be used, otherwise the reason."""
    n = str(name or "").strip()
    if not n:
        return "Type a name."
    if len(n) > 40:
        return "At most 40 characters."
    taken = {p["name"].casefold() for p in BUILTIN_PRESETS} | {p["name"].casefold() for p in presets
                                                               if p.get("name") != old}
    if n.casefold() in taken:
        return "A preset with this name exists already."
    if old is None and len(presets) >= MAX_USER_PRESETS:
        return f"At most {MAX_USER_PRESETS} presets of your own."
    return ""
