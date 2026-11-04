"""collection_rules.py — v0.19.4 B110: movie collections (Kodi / Jellyfin movie sets).

Pure functions only: no I/O, no Tk, no network.  The scan, the health rules, the fixes and the grouped view of
mediaclinic_v0_19_4.py call these; every rule is tested without files (selftest section "B110").

What media servers read (checked 2026-10-27, plan B110.3):
- Kodi reads the FIRST <set> of a movie NFO, in the old form <set>Name</set> or the Jarvis form
  <set><name>Name</name><overview>…</overview></set>; no name = no set.  Kodi groups by the NAME.
- Jellyfin reads both forms and the attribute tmdbcolid (the TMDB collection ID).
- Kodi's movie set information folder: <folder>\\<legal name>\\ with poster.* / fanart.* (kodi_legal_name).
"""
import html
import re
import unicodedata

# ── reading ────────────────────────────────────────────────────────────────────
_SET_RE = re.compile(r"<set(\s[^>]*)?(/>|>(.*?)</set\s*>)", re.S | re.I)
_ATTR_RE = re.compile(r"""tmdbcolid\s*=\s*["']\s*(\d+)\s*["']""", re.I)
_NAME_RE = re.compile(r"<name(?:\s[^>]*)?>(.*?)</name\s*>", re.S | re.I)
_OVER_RE = re.compile(r"<overview(?:\s[^>]*)?>(.*?)</overview\s*>", re.S | re.I)
XML_COLLECTION_TAGS = ()      # (unused) — movie.xml collections: XML_ID_TAGS / XML_NAME_TAGS below (fix 6)


def _text(s):
    return html.unescape(re.sub(r"\s+", " ", s or "")).strip()


def read_set(nfo_text):
    """The FIRST <set> of an NFO text (as Kodi) → {"name", "tmdbcolid", "overview", "count"} or None.
    count = how many <set> elements the file has (a 2nd one is ignored, as Kodi does).
    No name → None (Kodi: "no name, no set")."""
    if not nfo_text:
        return None
    found = list(_SET_RE.finditer(nfo_text))
    if not found:
        return None
    m = found[0]
    attrs, inner = m.group(1) or "", m.group(3)
    colid = None
    a = _ATTR_RE.search(attrs)
    if a:
        colid = int(a.group(1))
    if inner is None:                                  # <set/> or <set tmdbcolid="1"/>
        return None
    nm = _NAME_RE.search(inner)
    if nm:
        name = _text(nm.group(1))
        ov = _OVER_RE.search(inner)
        overview = _text(ov.group(1)) if ov else None
    elif "<" in inner:                                 # nested tags but no <name>
        return None
    else:
        name, overview = _text(inner), None
    if not name:
        return None
    return {"name": name, "tmdbcolid": colid, "overview": overview, "count": len(found)}


# ── names ──────────────────────────────────────────────────────────────────────
_QUOTES = str.maketrans({"‘": "'", "’": "'", "‚": "'", "′": "'", "`": "'", "´": "'",
                         "“": '"', "”": '"', "„": '"', "″": '"',
                         "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
                         "―": "-", "−": "-"})


def norm_name(name):
    """Comparison form (B110.6): Unicode NFC, case-folded, spaces collapsed, quotes and dashes unified.
    Accents are KEPT: "Coleção" and "Colecao" are different names for Kodi."""
    s = unicodedata.normalize("NFC", str(name or "")).translate(_QUOTES).casefold()
    return re.sub(r"\s+", " ", s).strip()


def group_key(row):
    """The grouping key of a row (Kodi groups by the name as written, case-folded) or None."""
    c = row.get("coll_nfo") if isinstance(row, dict) else None
    if not c or not c.get("name"):
        return None
    return norm_name(c["name"])


_ILLEGAL = re.compile(r'[/\\?:*"<>|]')


def kodi_legal_name(name):
    """Kodi's MakeLegalFileName(name, WIN32_COMPAT) for the set folder: / \\ ? : * " < > | → _,
    trailing dots and spaces removed; case and accents stay."""
    s = _ILLEGAL.sub("_", str(name or ""))
    return s.rstrip(". ")


# ── languages (B110.7) ─────────────────────────────────────────────────────────
LANG_NAMES = {"en": "English", "pt": "Portuguese", "es": "Spanish", "fr": "French", "de": "German",
              "it": "Italian", "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "ru": "Russian",
              "nl": "Dutch", "sv": "Swedish", "pl": "Polish", "tr": "Turkish"}


def lang_name(code):
    return LANG_NAMES.get((code or "").split("-")[0].lower(), code or "?")


def langs_matching(text, by_lang):
    """The languages whose text in *by_lang* {lang: text} equals *text* (normalised).
    An empty translation never matches (unknown for that language)."""
    t = norm_name(text)
    if not t:
        return set()
    return {(lg or "").split("-")[0].lower() for lg, v in (by_lang or {}).items() if v and norm_name(v) == t}


def language_decision(title_langs, coll_langs):
    """('warn', title_lang, coll_lang) | ('ok', None, None) | ('unknown', None, None)."""
    a, b = set(title_langs or ()), set(coll_langs or ())
    if not a or not b:
        return ("unknown", None, None)
    if a & b:
        return ("ok", None, None)
    return ("warn", sorted(a)[0], sorted(b)[0])


# ── one name per collection (v0.19.4 review fix 5) ─────────────────────────────
def _tm_id(row):
    tm = row.get("coll_tmdb") or {}
    try:
        return int(tm["id"]) if tm.get("id") else None
    except (TypeError, ValueError):
        return None


def loose_title(s):
    """Title comparison key: norm_name without accents, punctuation and spaces."""
    return re.sub(r"[\W_]+", "", strip_accents(norm_name(s)))


def local_title(row):
    """The movie's local title: NFO <title>; XML <LocalTitle> when the NFO has none (the NFO wins)."""
    return (row.get("nfo_title") or "").strip() or (row.get("xml_localtitle") or "").strip()


def title_lang(row, lib_lang="en"):
    """The language of the local title (v0.19.4 fix 9): "en" when it reads as English (also when it is the same
    in English and another language), another code when it is that language's TMDB title, None when unknown."""
    t = loose_title(local_title(row))
    if not t:
        return None
    langs = {(lg or "").split("-")[0].lower() for lg, v in (row.get("tmdb_titles") or {}).items()
             if v and loose_title(v) == t}
    tm = row.get("coll_tmdb") or {}
    if tm.get("tl") and tm["tl"] == t:          # title_langs were computed from this same local title
        langs |= {(x or "").split("-")[0].lower() for x in (row.get("title_langs") or []) if x}
    langs.discard("")
    if not langs:
        return None
    if "en" in langs:
        return "en"
    lg0 = (lib_lang or "en").split("-")[0].lower()
    return lg0 if lg0 in langs else sorted(langs)[0]


def chosen_names(rows, coll_cache, lib_lang="en", fixed="auto"):
    """{TMDB collection id: (name, overview, language)} — ONE name for each collection, used by the rule, the
    Fix and Auto Repair.  v0.19.4 fix 9 (the user): the English name, unless most of its movies have their local
    title in one other language — then that language's name.  A movie whose title language is unknown counts as
    English; a tie is English.  When TMDB has no name in that language: English (never the library language — fix 10).
    No name in either: the one name the NFOs already use (unless it is another language's TMDB name), else
    (None, None, "en") = unknown: no name warning, the Fix asks for Check Collections Online."""
    votes, written = {}, {}
    for r in rows:
        cid = _tm_id(r)
        if cid:
            lg = title_lang(r, lib_lang) or "en"
            v = votes.setdefault(cid, {})
            v[lg] = v.get(lg, 0) + 1
            nm = ((r.get("coll_nfo") or {}).get("name") or "").strip()
            if nm:
                written.setdefault(cid, {})[norm_name(nm)] = nm
    out = {}
    for cid, v in votes.items():
        entry = (coll_cache or {}).get(str(cid)) or {}
        names, ovs = entry.get("names") or {}, entry.get("overviews") or {}
        # v0.19.4 P4 (user decision 3): a language wins only with MORE THAN HALF of the collection's movies (unknown
        # titles count as English), else English; never a second language by votes.  A fixed language from Settings
        # ("Collection name language") replaces the vote.
        fx = (fixed or "auto").split("-")[0].lower()
        if fx and fx != "auto":
            order = [fx, "en"]
        else:
            total = sum(v.values())
            top = max(sorted(v), key=lambda lg: v[lg])
            order = [top, "en"] if (top != "en" and v[top] * 2 > total) else ["en"]
        pick = next((lg for lg in order if names.get(lg)), None)
        if pick:
            out[cid] = (names[pick], ovs.get(pick), pick)
            continue
        w = written.get(cid) or {}
        others = {norm_name(x) for x in names.values() if x}
        if len(w) == 1 and next(iter(w)) not in others:
            out[cid] = (next(iter(w.values())), None, order[0])
        else:
            out[cid] = (None, None, order[0])
    return out


# ── the collection rule (B110.6) ──────────────────────────────────────────────
def mismatch_reasons(row, coll_cache=None, spellings=None, chosen=None):
    """The 'Collection: …' warnings of one row (rule collection_mismatch).
    row["coll_nfo"]: what the NFO says; row["coll_tmdb"]: {"id", "name", …} from TMDB (id None = TMDB lists no
    collection; key missing = not checked).  coll_cache: {str(id): {"names": {lang: name}}}.
    spellings: {tmdb id or group key: set of names as written} across the library."""
    out = []
    nfo = row.get("coll_nfo") or None
    tm = row.get("coll_tmdb")
    if not nfo and row.get("coll_none"):                 # v0.19.4 fix 3b: the user said "not in a collection"
        return out
    if tm and not tm.get("id") and nfo and nfo.get("tmdbcolid"):   # v0.19.4 fix 3c: a link TMDB no longer has
        gone = tm.get("gone")
        try:
            same = gone is not None and int(gone) == int(nfo["tmdbcolid"])
        except (TypeError, ValueError):
            same = False
        out.append(f"Collection: '{nfo['name']}' (TMDB {nfo['tmdbcolid']}) "
                   + ("no longer exists on TMDB" if same else "is not listed by TMDB for this movie"))
    if tm and tm.get("id"):
        names = dict(((coll_cache or {}).get(str(tm["id"])) or {}).get("names") or {})
        if tm.get("name"):
            names.setdefault(tm.get("lang") or "xx", tm["name"])
        ch = (chosen or {}).get(int(tm["id"]))                    # v0.19.4 fix 5: the collection's one name
        if not nfo:
            out.append(f"Collection: missing (TMDB: '{(ch[0] if ch else None) or tm.get('name') or tm['id']}')")
        else:
            other_id = nfo.get("tmdbcolid") and int(nfo["tmdbcolid"]) != int(tm["id"])
            if ch and not ch[0]:                                  # fix 10: TMDB gave no name in that language
                same_name = True
            elif ch:
                same_name = norm_name(ch[0]) == norm_name(nfo["name"])
            else:
                same_name = any(norm_name(v) == norm_name(nfo["name"]) for v in names.values() if v)
            if other_id and same_name:                                # P4 (F6): only the ID differs
                out.append(f"Collection: NFO links TMDB collection {nfo['tmdbcolid']}, TMDB lists {tm['id']} for this movie")
            elif other_id or not same_name:
                out.append(f"Collection: NFO says '{nfo['name']}', TMDB says '{(ch[0] if ch else None) or tm.get('name') or tm['id']}'")
    if nfo and spellings:
        key = (tm or {}).get("id") or nfo.get("tmdbcolid") or norm_name(nfo["name"])
        others = {s: k for s, k in (spellings.get(key) or {}).items() if norm_name(s) != norm_name(nfo["name"])}
        if others:
            o = max(sorted(others), key=lambda s: others[s])
            n = sum(others.values())
            out.append(f"Collection: written as '{nfo['name']}' here and as '{o}' in {n} other movie{'' if n == 1 else 's'} "
                       "(Kodi shows two sets)")
    return out


def spellings_index(rows):
    """{tmdb id (or the NFO tmdbcolid, else the name key): {name as written: number of movies}}."""
    idx = {}
    for r in rows:
        nfo = r.get("coll_nfo")
        if not nfo or not nfo.get("name"):
            continue
        key = ((r.get("coll_tmdb") or {}).get("id")) or nfo.get("tmdbcolid") or norm_name(nfo["name"])
        d = idx.setdefault(key, {})
        d[nfo["name"]] = d.get(nfo["name"], 0) + 1
    return idx


# ── online data (B110.5) — TMDB answers in, plain data out ──────────────────────
CHECK_MAX_AGE_DAYS = 30


def coll_from_movie(data, lang, when):
    """coll_tmdb from a /movie/{id} answer: {"id", "name", "lang", "when"}; {"id": None, "when"} = TMDB lists
    no collection for the movie; None = not a movie answer."""
    if not isinstance(data, dict) or not data.get("id"):
        return None
    b = data.get("belongs_to_collection")
    if not isinstance(b, dict) or not b.get("id"):
        return {"id": None, "when": when}
    return {"id": int(b["id"]), "name": (b.get("name") or "").strip(), "lang": lang, "when": when}


def title_langs_from(data, local_titles):
    """The languages whose TMDB title equals one of the local titles (B110.7 step 1): the translations plus the
    original title in the original language."""
    by = {}
    for tr in ((data or {}).get("translations") or {}).get("translations") or []:
        t = (tr.get("data") or {}).get("title")
        lg = (tr.get("iso_639_1") or "").lower()
        if t and lg:
            by.setdefault(lg, set()).add(norm_name(t))
    ot, ol = (data or {}).get("original_title"), ((data or {}).get("original_language") or "").lower()
    if ot and ol:
        by.setdefault(ol, set()).add(norm_name(ot))
    wanted = {norm_name(t) for t in (local_titles or []) if t}
    return sorted(lg for lg, ts in by.items() if ts & wanted)


def titles_by_lang(data):
    """{lang: TMDB title} from a /movie answer (translations + the original title); empty titles left out."""
    out = {}
    for tr in ((data or {}).get("translations") or {}).get("translations") or []:
        t = ((tr.get("data") or {}).get("title") or "").strip()
        lg = (tr.get("iso_639_1") or "").lower()
        if t and lg:
            out.setdefault(lg, t)
    ot, ol = ((data or {}).get("original_title") or "").strip(), ((data or {}).get("original_language") or "").lower()
    if ot and ol:
        out.setdefault(ol, ot)
    return out


def coll_cache_entry(main, translations, lang, when):
    """One collections_cache.json entry: names / overviews per language, the movie IDs TMDB lists as parts."""
    names, overviews = {}, {}
    for tr in (translations or {}).get("translations") or []:
        d = tr.get("data") or {}
        lg = (tr.get("iso_639_1") or "").lower()
        nm = (d.get("title") or d.get("name") or "").strip()
        if lg and nm:
            names.setdefault(lg, nm)
        if lg and (d.get("overview") or "").strip():
            overviews.setdefault(lg, d["overview"].strip())
    main = main if isinstance(main, dict) else {}
    lg0 = (lang or "").split("-")[0].lower()
    if lg0 and (main.get("name") or "").strip():
        names.setdefault(lg0, main["name"].strip())
    if lg0 and (main.get("overview") or "").strip():
        overviews.setdefault(lg0, main["overview"].strip())
    parts = sorted(int(p["id"]) for p in (main.get("parts") or []) if isinstance(p, dict) and p.get("id"))
    return {"names": names, "overviews": overviews, "parts": parts, "when": when}


def needs_check(row, now, days=CHECK_MAX_AGE_DAYS):
    """True when the row has no online collection data or it is older than *days*."""
    tm = row.get("coll_tmdb")
    return not tm or (now - float(tm.get("when") or 0)) > days * 86400


# ── the collection folder (B110.8) ─────────────────────────────────────────────
ART_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tbn")


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if not unicodedata.combining(c))


def match_folder(legal, names):
    """(found name, near) for the set folder *legal* among the folder *names*: near = None (exact), "case"
    (only the case differs: found on Windows / SMB), "accent" (only accents differ: NOT the folder, found name
    is the look-alike) or (None, None)."""
    if legal in names:
        return legal, None
    low = {n.casefold(): n for n in names}
    if legal.casefold() in low:
        return low[legal.casefold()], "case"
    plain = {strip_accents(n).casefold(): n for n in names}
    if strip_accents(legal).casefold() in plain:
        return plain[strip_accents(legal).casefold()], "accent"
    return None, None


def art_types(filenames):
    """{art type (lower case): file name} of the picture files of a set folder (folder.* maps to poster)."""
    out = {}
    for f in sorted(filenames):
        base, ext = f.rsplit(".", 1) if "." in f else (f, "")
        if "." + ext.lower() in ART_EXTS:
            out.setdefault(base.lower(), f)
    return out


def artwork_reasons(state):
    """The 'Collection artwork: …' warnings of one collection folder state (None = not checked → none)."""
    if state is None:
        return []
    if state.get("old_dir"):                                  # v0.19.4 fix 15: the images sit under an old name
        return [f"Collection folder: images left in '{state.get('old_name')}' (another name of this collection) — "
                f"Fix moves them to '{state.get('legal')}'"]
    if not state.get("dir"):
        near = f" (a folder '{state['near_name']}' exists — Kodi needs the same accents)" if state.get("near") == "accent" else ""
        return ["Collection artwork: folder missing" + near]
    return [f"Collection artwork: {t} missing" for t in ("poster", "fanart") if t not in (state.get("art") or {})]


def pick_image(images, kind, lib_lang="en"):
    """The TMDB image to download: poster → library language, no language, English, the rest; fanart → no
    language first; then the largest.  None when there is none."""
    lg0 = (lib_lang or "en").split("-")[0].lower()
    order = [lg0, "", "en"] if kind == "poster" else ["", lg0, "en"]

    def rank(i):
        lg = (i.get("iso_639_1") or "").lower()
        return (order.index(lg) if lg in order else len(order), -(i.get("width", 0) or 0) * (i.get("height", 0) or 0))
    imgs = [i for i in (images or []) if i.get("file_path")]
    return min(imgs, key=rank) if imgs else None


# ── the fix (B110.9) ───────────────────────────────────────────────────────────
def fix_target(row, cache, lib_lang="en", chosen=None):
    """(name, tmdbcolid, overview, None) to write, or (None, None, None, why) when the movie is skipped."""
    tm = row.get("coll_tmdb")
    if row.get("coll_none") and not row.get("coll_nfo"):   # v0.19.4 fix 3b
        return None, None, None, "you marked it as not in a collection"
    if not tm:
        return None, None, None, "not checked online — Check Collections Online first"
    if not tm.get("id"):
        return None, None, None, "TMDB lists no collection for this movie (your own collection is kept)"
    entry = (cache or {}).get(str(tm["id"])) or {}
    names, ovs = entry.get("names") or {}, entry.get("overviews") or {}
    order = [title_lang(row, lib_lang) or "en", "en"]             # fix 9 / fix 10: never the library language
    name = ov = None
    ch = (chosen or {}).get(int(tm["id"]))                        # v0.19.4 fix 5: the collection's one name
    if ch and not ch[0]:                                          # fix 10
        return None, None, None, "TMDB gave no English name for the collection — run Check Collections Online again"
    if ch:
        name, ov = ch[0], ch[1]
    for lg in ([] if ch else order):
        if names.get(lg):
            name, ov = names[lg], ovs.get(lg)
            break
    if not name:
        name = tm.get("name")
    if not name:
        return None, None, None, "TMDB has no name for the collection"
    nfo = row.get("coll_nfo") or {}
    if nfo and norm_name(nfo.get("name")) == norm_name(name) and nfo.get("tmdbcolid") in (tm["id"], None):
        return None, None, None, "already right"                 # P4 (decision 4): no TMDB ID in the NFO is right too
    return name, int(tm["id"]), ov, None


def same_collection(a, b):
    """True when two rows belong to the same collection (TMDB ID, else the NFO tmdbcolid, else the name key)."""
    ka = (a.get("coll_tmdb") or {}).get("id") or (a.get("coll_nfo") or {}).get("tmdbcolid")
    kb = (b.get("coll_tmdb") or {}).get("id") or (b.get("coll_nfo") or {}).get("tmdbcolid")
    if ka and kb:
        return int(ka) == int(kb)
    return bool(group_key(a)) and group_key(a) == group_key(b)


# ── the grouped view (B110.10) ────────────────────────────────────────────────
def group_rows(rows):
    """rows (already sorted / filtered, as view_rows returns them) → the top-level items in view order:
    ("movie", row) or ("coll", key, display name, [rows in order]).  A collection sits where its first movie
    sits; movies without a collection stay single (D10)."""
    out, seen = [], {}
    for r in rows:
        k = group_key(r)
        if k is None:
            out.append(("movie", r))
            continue
        if k in seen:
            seen[k][3].append(r)
            continue
        item = ("coll", k, r["coll_nfo"]["name"], [r])
        seen[k] = item
        out.append(item)
    return out


def year_span(rows):
    ys = sorted(str(r.get("movie_year")) for r in rows if str(r.get("movie_year") or "").isdigit())
    if not ys:
        return ""
    return ys[0] if ys[0] == ys[-1] else f"{ys[0]}–{ys[-1]}"


def worst_health(rows):
    order = {"error": 0, "warning": 1, "ok": 2}
    return min((r.get("health_status", "warning") for r in rows), key=lambda s: order.get(s, 1), default="ok")


# ── writing (B110.9) — the text change only; the caller does backup / atomic write ─────────────
def set_block(name, tmdbcolid=None, overview=None, indent="  ", nl="\n", overview_raw=None):
    """<set tmdbcolid="N"><name>…</name>[<overview>…</overview>]</set> (escaped).  *overview_raw*: an overview
    already written in the file, kept character for character (v0.19.4 P3, B20)."""
    attr = f' tmdbcolid="{int(tmdbcolid)}"' if tmdbcolid else ""
    inner = f"{indent}{indent}<name>{html.escape(name, quote=False)}</name>{nl}"
    if overview_raw:
        inner += f"{indent}{indent}<overview>{overview_raw}</overview>{nl}"
    elif overview:
        inner += f"{indent}{indent}<overview>{html.escape(overview, quote=False)}</overview>{nl}"
    return f"<set{attr}>{nl}{inner}{indent}</set>"


def replace_set_in_text(text, name, tmdbcolid=None, overview=None):
    """The NFO text with its first <set> replaced by character position (or inserted before </movie>);
    an existing non-empty <overview> is kept.  Every other character stays.  None if there is no </movie>."""
    nl = "\r\n" if "\r\n" in text else "\n"
    m = _SET_RE.search(text)
    if m:
        old = read_set(text)
        raw = None
        if old and old.get("overview"):
            # v0.19.4 P3 (F3): the overview stays only for the SAME collection (same TMDB id; without ids, the same
            # name) and as it was written (B20: paragraphs kept); another collection's overview is not carried over
            o_id, same = old.get("tmdbcolid"), False
            try:
                same = bool(o_id and tmdbcolid and int(o_id) == int(tmdbcolid))
            except (TypeError, ValueError):
                same = False
            if not (o_id and tmdbcolid):
                same = norm_name(old.get("name")) == norm_name(name)
            if same:
                mo = re.search(r"<overview\b[^>]*>(.*?)</overview\s*>", text[m.start():m.end()], re.S | re.I)
                raw = mo.group(1) if mo and mo.group(1).strip() else None
                overview = None if raw else old["overview"]
        ls = text.rfind("\n", 0, m.start()) + 1
        indent = re.match(r"[ \t]*", text[ls:m.start()]).group(0) or "  "
        return text[:m.start()] + set_block(name, tmdbcolid, overview, indent, nl, overview_raw=raw) + text[m.end():]
    end = re.search(r"</movie\s*>", text, re.I)
    if not end:
        return None
    ls = text.rfind("\n", 0, end.start()) + 1
    body_indent = "  "
    mi = re.search(r"\n([ \t]+)<", text)
    if mi:
        body_indent = mi.group(1)
    block = body_indent + set_block(name, tmdbcolid, overview, body_indent, nl) + nl
    if text[ls:end.start()].strip() == "":            # </movie> on its own line: the block goes on the line before
        return text[:ls] + block + text[ls:]
    return text[:end.start()] + nl + block + text[end.start():]


def remove_set_in_text(text):
    """The text without its first <set> block (and its line, when the block was alone on it)."""
    m = _SET_RE.search(text)
    if not m:
        return text
    ls = text.rfind("\n", 0, m.start()) + 1
    le = text.find("\n", m.end())
    le = len(text) if le < 0 else le + 1
    if text[ls:m.start()].strip() == "" and text[m.end():le].strip() == "":
        return text[:ls] + text[le:]
    return text[:m.start()] + text[m.end():]


# ── movie.xml (v0.19.4 review fix 6) — the user's <Title> files ─────────────────────────────────
XML_ID_TAGS = ("TMDbCollectionId", "CollectionNumber")
XML_NAME_TAGS = ("CollectionName", "TmdbCollectionName")


def _xml_tag_re(tag):
    return re.compile(rf"<{tag}(?:\s[^>]*)?(?:/>|>(.*?)</{tag}\s*>)", re.S)


def read_xml_collection(text):
    """{"name": str|None, "tmdbcolid": int|None, "stray": bool} of a movie.xml text (None without text).
    The id: the first non-zero of TMDbCollectionId, CollectionNumber, the stray <set>'s tmdbcolid."""
    if not text:
        return None
    vals = {}
    for tag in XML_ID_TAGS + XML_NAME_TAGS:
        m = _xml_tag_re(tag).search(text)
        vals[tag] = _text(m.group(1)) if m and m.group(1) is not None else None
    stray = read_set(text)
    name = vals["CollectionName"] or vals["TmdbCollectionName"] or (stray or {}).get("name") or None
    cid = None
    for v in (vals["TMDbCollectionId"], vals["CollectionNumber"], (stray or {}).get("tmdbcolid")):
        try:
            if v is not None and int(v) > 0:
                cid = int(v)
                break
        except (TypeError, ValueError):
            continue
    return {"name": name, "tmdbcolid": cid, "stray": bool(_SET_RE.search(text))}


def _remove_element_line(text, m):
    ls = text.rfind("\n", 0, m.start()) + 1
    le = text.find("\n", m.end())
    le = len(text) if le < 0 else le + 1
    if text[ls:m.start()].strip() == "" and text[m.end():le].strip() == "":
        return text[:ls] + text[le:]
    return text[:m.start()] + text[m.end():]


def xml_collection_text(text, name, tmdbcolid=None):
    """movie.xml text with the collection in its own tags (character position; every other character stays).
    name None = no collection: the ids 0, CollectionName / TmdbCollectionName removed.  A stray NFO-style <set>
    block is always removed.  None when there is no </Title>."""
    nl = "\r\n" if "\r\n" in text else "\n"
    for _i in range(5):                                   # the stray <set> blocks
        if not _SET_RE.search(text):
            break
        text = remove_set_in_text(text)
    esc = html.escape(name, quote=False) if name else None
    cid = str(int(tmdbcolid)) if tmdbcolid else "0"
    want = {"TMDbCollectionId": cid, "CollectionNumber": cid, "CollectionName": esc, "TmdbCollectionName": esc}
    missing = []
    for tag in XML_ID_TAGS + XML_NAME_TAGS:
        m = _xml_tag_re(tag).search(text)
        if m:
            if want[tag] is None:
                text = _remove_element_line(text, m)
            else:
                text = text[:m.start()] + f"<{tag}>{want[tag]}</{tag}>" + text[m.end():]
        elif name and tag != "TmdbCollectionName":
            missing.append(tag)
    if not missing:
        return text
    end = re.search(r"</Title\s*>", text)
    if not end:
        return None
    ind = "    "
    mi = re.search(r"\n([ \t]+)<", text)
    if mi:
        ind = mi.group(1)
    block = "".join(f"{ind}<{t}>{want[t]}</{t}>{nl}" for t in missing)
    anchor = None
    ends = [mm.end() for mm in (_xml_tag_re(tag).search(text) for tag in XML_ID_TAGS + XML_NAME_TAGS) if mm]
    if ends:                                              # after the last collection tag that is there
        anchor = text.find("\n", max(ends))
        anchor = len(text) if anchor < 0 else anchor + 1
    if anchor is None:
        ls = text.rfind("\n", 0, end.start()) + 1
        if text[ls:end.start()].strip() == "":
            return text[:ls] + block + text[ls:]
        return text[:end.start()] + nl + block + text[end.start():]
    return text[:anchor] + block + text[anchor:]


def xml_reasons(row):
    """'Collection: movie.xml …' — movie.xml and the NFO disagree (or movie.xml has the stray <set> block)."""
    x = row.get("coll_xml")
    if not row.get("xml_exists") or not x:
        return []
    out = []
    if x.get("stray"):
        out.append("Collection: movie.xml has an NFO-style <set> block (not a movie.xml tag)")
    nfo = row.get("coll_nfo") or {}
    nn, xn = nfo.get("name") or None, x.get("name") or None
    ni, xi = nfo.get("tmdbcolid"), x.get("tmdbcolid")
    if norm_name(nn or "") != norm_name(xn or "") or (ni and int(ni) != int(xi or 0)):
        out.append(f"Collection: movie.xml says '{xn or '(none)'}', the NFO says '{nn or '(none)'}'")
    return out
