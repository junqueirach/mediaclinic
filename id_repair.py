"""Wrong values in the IMDb / TMDB tags of an NFO or movie.xml (v0.20.1 T1, T2, T5 — the tester case "55 Days at
Peking": Emby wrote the TMDB number 27759 into <imdbid> and <uniqueid type="imdb">, while its own
<imdb id="tt0056800"> line in the same file holds the right IMDb ID).

Pure: no Tk, no network, no file access. The main file reads the files, asks TMDB when the file itself does not hold
the right ID, and writes the text this module returns (backup first, Undo).

- link_ids(text): the IDs in Emby's link lines <imdb id="tt…">…</imdb> / <tmdb id="…">…</tmdb>.
- diagnose(kind, bad, good, links, other_ids): what is wrong with each bad value (the user's rule 2026-11-19: "the TMDB
  number" only when the digits equal the file's TMDB ID; any other wrong value is "not a correct ID") and the right ID
  when the same file holds it.
- replace_ids(text, kind, bad, good, xml=False): the text with every bad value replaced by *good* in the ID tags that
  already exist directly inside the root element (an actor's, a set's or a producer's tag is never touched); no tag
  is ever added.

Series-ready (SR2): nothing here is movie-only; an episode NFO uses the same tags.
"""
import bisect
import re
from typing import Iterable, Optional

IMDB_RX = re.compile(r"^tt\d{7,9}$")
TMDB_RX = re.compile(r"^\d{1,9}$")
KINDS = ("imdb", "tmdb")

# the tags each kind lives in (lower-case names; attributes checked separately)
NFO_TAGS = {"imdb": ("imdbid", "uniqueid:imdb", "id:imdb", "id:"),
            "tmdb": ("tmdbid", "uniqueid:tmdb", "uniqueid:themoviedb", "id:tmdb", "id:themoviedb")}
XML_TAGS = {"imdb": ("IMDB", "IMDbId", "IMDB_ID"), "tmdb": ("TMDB", "TMDbId", "TMDB_ID")}
_LINK_URL = {"imdb": re.compile(r"imdb\.com/title/(tt\d{7,9})", re.I),
             "tmdb": re.compile(r"themoviedb\.org/movie/(\d{1,9})", re.I)}
_VAL = r"\s*<!\[CDATA\[[^\]]*\]\]>\s*|[^<]*"                      # a tag's value, plain or as CDATA
_TOKEN = re.compile(r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<![A-Za-z][^>]*>|<(/)?[\w:.-]+(?:\s[^<>]*?)?(/)?>", re.S)


def valid(kind: str, v) -> bool:
    v = str(v or "").strip()
    return bool(IMDB_RX.match(v) if kind == "imdb" else TMDB_RX.match(v))


def link_ids(text: str) -> dict:
    """{"imdb": [...], "tmdb": [...]} from Emby's link lines <imdb id="tt…">URL</imdb> / <tmdb id="…">URL</tmdb> (the id
    attribute, or the address inside the line), in file order, no repeats, valid IDs only. An address elsewhere in the
    file (a plot, a trailer, another film's link) is not taken: it need not be this movie's."""
    t = text or ""
    out = {"imdb": [], "tmdb": []}
    for k in KINDS:
        for m in re.finditer(rf"<{k}\b([^>]*)>([^<]*)</{k}\s*>", t, re.I):
            found = []
            a = re.search(r"""\bid\s*=\s*["']([^"']+)["']""", m.group(1), re.I)
            if a:
                found.append(a.group(1))
            u = _LINK_URL[k].search(m.group(2))
            if u:
                found.append(u.group(1))
            for v in found:
                v = v.strip()
                if valid(k, v) and v not in out[k]:
                    out[k].append(v)
    return out


def diagnose(kind: str, bad: Iterable[str], good: Iterable[str] = (), links: Iterable[str] = (),
             other_ids: Iterable[str] = ()) -> Optional[dict]:
    """None when *bad* is empty, else {"kind", "values", "why", "suggest", "from"}.

    *bad*: the values of this kind that are not valid IDs; *good*: the valid values of this kind in the files;
    *links*: the IDs of this kind in the link lines (link_ids); *other_ids*: the valid IDs of the OTHER kind.
    why: "tmdb_number" (an IMDb tag holds exactly the file's TMDB ID), "imdb_id" (a TMDB tag holds an IMDb ID),
    "invalid" (anything else: a typo, a mix). suggest: the right ID when the files hold it ("" = ask TMDB);
    from: "tag" (a valid tag of the same kind), "link" (the link line), ""."""
    bad = [str(v).strip() for v in bad if str(v or "").strip()]
    if not bad:
        return None
    others = {str(v).strip() for v in other_ids if v}
    v0 = bad[0]
    if kind == "imdb" and v0.isdigit() and v0 in others:
        why = "tmdb_number"
    elif kind == "tmdb" and IMDB_RX.match(v0):
        why = "imdb_id"
    else:
        why = "invalid"
    good = [g for g in (str(x).strip().strip("/\\ ") for x in good) if valid(kind, g)]   # 'tt0056800/' is tt0056800
    links = [g for g in links if valid(kind, g)]
    if good:
        sug, src = good[0], "tag"
    elif links:
        sug, src = links[0], "link"
    else:
        sug, src = "", ""
    return {"kind": kind, "values": bad, "why": why, "suggest": sug, "from": src}


def _root_test(text: str):
    """pos → True when *pos* is directly inside the root element (depth 1). Comments, CDATA and declarations are
    not tags; an empty <set /> opens nothing."""
    ends, depths, depth = [], [], 0
    for m in _TOKEN.finditer(text):
        if m.group(0).startswith(("<!", "<?")):
            continue
        if m.group(1):
            depth -= 1
        elif not m.group(2):
            depth += 1
        ends.append(m.end())
        depths.append(depth)

    def at_root(pos):
        i = bisect.bisect_right(ends, pos) - 1
        return i >= 0 and depths[i] == 1
    return at_root


def _bare(v: str) -> str:
    v = v.strip()
    return v[9:-3].strip() if v.startswith("<![CDATA[") and v.endswith("]]>") else v


def _tag_rx(spec: str, xml: bool):
    """A regex for one tag spec: 'imdbid', 'uniqueid:imdb' (type=), 'id:imdb' (moviedb=), 'id:' (plain <id>),
    or an XML tag name. Group 1 = the opening tag, 2 = the value, 3 = the closing tag."""
    if xml:
        return re.compile(rf"(<{spec}>)({_VAL})(</{spec}\s*>)")
    name, colon, attr = spec.partition(":")
    if not colon:
        return re.compile(rf"(<{name}(?:\s[^>]*)?>)({_VAL})(</{name}\s*>)", re.I)
    if name == "uniqueid":
        return re.compile(rf"(<uniqueid\b[^>]*\btype\s*=\s*[\"']{attr}[\"'][^>]*>)({_VAL})(</uniqueid\s*>)", re.I)
    if attr:
        return re.compile(rf"(<id\b[^>]*\bmoviedb\s*=\s*[\"']{attr}[\"'][^>]*>)({_VAL})(</id\s*>)", re.I)
    return re.compile(rf"(<id>)({_VAL})(</id\s*>)", re.I)                     # a plain <id> without attributes


def replace_ids(text: str, kind: str, bad: Iterable[str], good: str, xml: bool = False) -> tuple:
    """(new text, number of values replaced). Every tag of *kind* that already exists directly inside the root and
    holds one of the *bad* values (plain or CDATA) gets *good*; nothing else changes (no tag added, spacing and line
    endings kept). A plain <id> is changed only when it holds an IMDb-looking bad value ("tt…"): a plain numeric <id>
    is Kodi's default ID, often TMDB's own number. *good* must be a valid ID of *kind*."""
    if not valid(kind, good):
        raise ValueError(f"not a valid {kind} ID: {good!r}")
    bad = {str(v).strip() for v in bad if str(v or "").strip()}
    if not bad or not text:
        return text, 0
    n = 0
    for spec in (XML_TAGS if xml else NFO_TAGS)[kind]:
        rx = _tag_rx(spec, xml)
        at_root = _root_test(text)
        out, last = [], 0
        for m in rx.finditer(text):
            raw = m.group(2)
            val = _bare(raw)
            if val not in bad or not at_root(m.start()):
                continue
            if spec == "id:" and not val.lower().startswith("tt"):
                continue
            out.append(text[last:m.start(2)])
            out.append(raw[:len(raw) - len(raw.lstrip())] + good + raw[len(raw.rstrip()):])
            last = m.end(2)
            n += 1
        if out:
            text = "".join(out) + text[last:]
    return text, n
