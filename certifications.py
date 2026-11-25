# =============================================================================
# certifications.py — the age ratings (certifications) of a movie's NFO / movie.xml (pure: no Tk, no network,
# no files)
# MediaClinic v0.20.2 CR                                          ### NEW v0.20.2 CR ###
#
# The user's rules (plan Part 9h.2 + row 7, 2026-11-19 / 2026-11-22):
#   - the user's countries, in their order, and a maximum for list tags; values of other countries are removed;
#   - a value is kept from the file when it is for an accepted country, else taken from TMDB (release_dates), OMDb's
#     "Rated" as the US value; none of the accepted countries → the US rating, and the user is told;
#   - nothing anywhere → the tag stays / becomes blank and the user is told ("no certification in TMDB and IMDb");
#     only values of countries not accepted in the file and nothing online → the user chooses: keep or blank;
#   - every tag of the topic the file has is written in its own style (one value / a list up to the max); a missing
#     tag is ADDED only for the tags the programs read (NFO <mpaa>, movie.xml <ContentRating>), as "CC:value";
#   - TMDB: theatrical first (type 3), then limited (2), digital (4), physical (5), TV (6), premiere (1); the earliest.
# Jellyfin (LocalizationManager.GetRatingScore, read 2026-11-22) reads "PG-13", "Rated PG-13", "US:PG-13", "BR-12",
# "FSK 12"; of a list only the FIRST value.
# Series-ready (SR0): a TV show's NFO has <mpaa> too; nothing here knows movies only.
# =============================================================================
from __future__ import annotations

import re
from xml.sax.saxutils import escape

NFO_TAGS = ("mpaa", "certification")
XML_TAGS = ("ContentRating", "MPAARating", "certification", "FullCertifications", "FormalMPAA")
SINGLE = {("nfo", "mpaa"), ("xml", "ContentRating"), ("xml", "MPAARating")}     # one value (programs read one)
LIST = {("xml", "FullCertifications"), ("xml", "FormalMPAA")}                  # "US: R; DE: 16; …" up to the max
ADDABLE = (("nfo", "mpaa"), ("xml", "ContentRating"))                          # added when missing (the user, 2026-11-22)
TYPE_ORDER = (3, 2, 4, 5, 6, 1)

US_RATINGS = {"G", "PG", "PG-13", "R", "NC-17", "NR", "NOT RATED", "UNRATED", "X", "M", "GP",
              "TV-Y", "TV-Y7", "TV-Y7-FV", "TV-G", "TV-PG", "TV-14", "TV-MA"}
DEFAULT_COUNTRY = {"pt_BR": "BR", "pt": "BR", "es": "ES", "en": "US"}

_SPLIT = re.compile(r"\s*;\s*|\s+/\s+|\s*\|\s*")
_ITEM = re.compile(r"^(?P<cc>[A-Za-z]{2})(?P<sep>\s*:\s*|-)(?P<val>.+)$")
_RATED = re.compile(r"^rated\s*:?\s*(?P<val>.+)$", re.IGNORECASE)


def default_countries(ui_lang):
    """The default list: the app language's country and US (PT-BR → BR, US; ES → ES, US; EN → US)."""
    c = DEFAULT_COUNTRY.get(ui_lang or "en") or DEFAULT_COUNTRY.get((ui_lang or "en").split("_")[0], "US")
    return [c] if c == "US" else [c, "US"]


def clean_countries(v):
    """A typed list ("br, US de") → ["BR", "US", "DE"] (two letters, no repeats, order kept)."""
    if isinstance(v, str):
        v = re.split(r"[\s,;/]+", v)
    out = []
    for x in v or ():
        x = str(x or "").strip().upper()
        if re.fullmatch(r"[A-Z]{2}", x) and x not in out:
            out.append(x)
    return out


def blank(text):
    """True for an empty value; Emby's U+2800 braille blank counts as empty (CR-c5)."""
    return not (text or "").replace("⠀", "").strip()


def parse(text):
    """The values of one tag's text: [{"cc", "value", "style", "sep"}]; style "cc" (US:R, BR-12), "rated" (Rated R) or
    "bare" (R, 12); cc = the country (a bare / Rated US rating counts as US; an unknown bare value has cc None)."""
    if blank(text):
        return []
    out = []
    for raw in _SPLIT.split(text.replace("⠀", "").strip()):
        raw = raw.strip()
        if not raw:
            continue
        m = _RATED.match(raw)
        if m:
            v = m.group("val").strip()
            out.append({"cc": "US" if v.upper() in US_RATINGS else None, "value": v, "style": "rated", "sep": ""})
            continue
        if raw.upper() in US_RATINGS:                             # "PG-13" is not Papua New Guinea "13"
            out.append({"cc": "US", "value": raw, "style": "bare", "sep": ""})
            continue
        m = _ITEM.match(raw)
        if m:
            out.append({"cc": m.group("cc").upper(), "value": m.group("val").strip(), "style": "cc", "sep": m.group("sep")})
            continue
        if re.match(r"^FSK\s*\d+$", raw, re.IGNORECASE):
            out.append({"cc": "DE", "value": raw, "style": "bare", "sep": ""})
            continue
        out.append({"cc": None, "value": raw, "style": "bare", "sep": ""})
    return out


def list_sep(text):
    return " / " if re.search(r"\s/\s", text or "") else "; "


def fmt(cc, value, like=None):
    """One value in the style of *like* (a parse() item) — "CC:value" when there is no style to copy."""
    like = like or {"style": "cc", "sep": ":"}
    if like["style"] == "rated":
        return f"Rated {value}"
    if like["style"] == "bare":
        return value
    return f"{cc}{like.get('sep') or ':'}{value}"


def pick_tmdb(results):
    """{CC: certification} from TMDB /movie/{id}/release_dates "results": per country theatrical first (TYPE_ORDER),
    the earliest of that type, a non-empty certification."""
    out = {}
    for c in results or ():
        cc = (c.get("iso_3166_1") or "").upper()
        best = None
        for d in c.get("release_dates") or ():
            cert = (d.get("certification") or "").strip()
            if not cert:
                continue
            try:
                rank = TYPE_ORDER.index(int(d.get("type") or 0))
            except ValueError:
                rank = len(TYPE_ORDER)
            key = (rank, d.get("release_date") or "9999")
            if best is None or key < best[0]:
                best = (key, cert)
        if cc and best:
            out[cc] = best[1]
    return out


def omdb_us(rated):
    """OMDb's "Rated" as the US value ("N/A" / empty → None)."""
    r = (rated or "").strip()
    return None if not r or r.upper() == "N/A" else r


def file_values(tags):
    """{CC: value} of every value in the file's tags (the first one met wins), and whether there are values without a
    known country."""
    out, unknown = {}, False
    for _k, text in sorted((tags or {}).items()):
        for it in parse(text):
            if it["cc"]:
                out.setdefault(it["cc"], it["value"])
            else:
                unknown = True
    return out, unknown


def plan(tags, countries, max_n, online=None, choice=None):
    """What to write for one movie.  *tags* = {"nfo:mpaa": text or None (None = no such tag), …} — every tag of the
    topic the files have; *online* = {CC: value} (TMDB + OMDb US) or None (not fetched); *choice* = "keep" / "blank"
    for the edge case.  Returns {"status", "values", "writes": {tag key: new text}, "us_fallback"}:
    status "ok" (nothing to change) / "change" / "none" (no value anywhere: blank, the user is told) /
    "ask" (only other countries' values in the file and nothing online: keep or blank)."""
    countries = clean_countries(countries) or ["US"]
    max_n = max(1, int(max_n or 1))
    have, _unknown = file_values(tags)
    online = online or {}
    vals = []
    for cc in countries:
        v = have.get(cc) or online.get(cc)
        if v:
            vals.append((cc, v))
    us_fb = False
    if not vals:
        v = have.get("US") or online.get("US")
        if v:
            vals, us_fb = [("US", v)], True
    out = {"status": "ok", "values": vals, "writes": {}, "us_fallback": us_fb}
    present = {k: t for k, t in (tags or {}).items() if t is not None}
    if not vals:
        has_vals = any(not blank(t) for t in present.values())
        if not has_vals:
            out["status"] = "none"
            return out
        if choice not in ("keep", "blank"):
            out["status"] = "ask"
            return out
        if choice == "keep":
            return out
        for k, t in present.items():
            if not blank(t):
                out["writes"][k] = ""
        out["status"] = "change" if out["writes"] else "ok"
        return out
    for k, t in present.items():
        where, tag = k.split(":", 1)
        items = parse(t)
        like = items[0] if items else None
        is_list = (where, tag) in LIST or ((where, tag) not in SINGLE and len(items) > 1)
        if is_list:
            new = list_sep(t).join(fmt(cc, v, _like_for(items, cc)) for cc, v in vals[:max_n])
        else:
            new = fmt(vals[0][0], vals[0][1], like)
        if new != (t or "").strip():
            out["writes"][k] = new
    for where, tag in ADDABLE:                                    # the file is there, the tag is not
        k = f"{where}:{tag}"
        if k in (tags or {}) and tags[k] is None:
            out["writes"][k] = fmt(vals[0][0], vals[0][1])
    out["status"] = "change" if out["writes"] else "ok"
    return out


def _like_for(items, cc):
    return next((it for it in items if it["cc"] == cc), items[0] if items else {"style": "cc", "sep": ": "})


def findings(tags, countries, max_n):
    """The health rule's findings from the files only: [("other_country", tag, cc) | ("too_many", tag, n) |
    ("several", tag, n)]."""
    countries = clean_countries(countries) or ["US"]
    out = []
    for k, t in sorted((tags or {}).items()):
        if t is None:
            continue
        where, tag = k.split(":", 1)
        items = parse(t)
        for it in items:
            if it["cc"] and it["cc"] not in countries:
                out.append(("other_country", tag, it["cc"]))
                break
        if (where, tag) in SINGLE and len(items) > 1:
            out.append(("several", tag, len(items)))
        elif (where, tag) not in SINGLE and len(items) > max(1, int(max_n or 1)):
            out.append(("too_many", tag, len(items)))
    return out


# ── reading and writing the tags in a file's text ──
def _tag_re(tag):
    return re.compile(rf"<{tag}\b[^>]*?(?:/>|>(?P<v>.*?)</{tag}\s*>)", re.IGNORECASE | re.DOTALL)


def read_tags(text, where):
    """{"<where>:<tag>": text ('' empty) or None (absent)} for the topic's tags of one file's text (a file that is
    not there: {})."""
    if text is None:
        return {}
    out = {}
    for tag in (NFO_TAGS if where == "nfo" else XML_TAGS):
        m = _tag_re(tag).search(text)
        if not m:
            out[f"{where}:{tag}"] = None
        else:
            v = m.group("v") or ""
            out[f"{where}:{tag}"] = (v.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
                                     .replace("&apos;", "'").replace("&amp;", "&")).strip()
    return out


def write_tag(text, tag, value):
    """The file's text with the first <tag> holding *value* (escaped; "" = an empty element); a missing tag is
    added before the root's closing tag, indented like the root's first child."""
    v = escape(value or "")
    rx = _tag_re(tag)
    m = rx.search(text)
    if m:
        return text[:m.start()] + f"<{tag}>{v}</{tag}>" + text[m.end():]
    root = re.search(r"<(movie|tvshow|episodedetails|Title|Item)\b[^>]*>", text)
    end = re.search(rf"</{root.group(1)}\s*>", text) if root else None
    if not end:
        raise ValueError("no root element to add the tag to")
    ind = re.search(r"\n([ \t]+)<", text[root.end():])
    ind = ind.group(1) if ind else "  "
    head = text[:end.start()].rstrip(" \t")
    if not head.endswith("\n"):
        head += "\n"
    return head + f"{ind}<{tag}>{v}</{tag}>\n" + text[end.start():]
