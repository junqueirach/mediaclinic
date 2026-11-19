# =============================================================================
# set_nfo.py — Kodi's set.nfo for a movie collection (pure: no Tk, no network, no files)
# MediaClinic v0.20.1 CF2                                        ### NEW v0.20.1 CF2 ###
#
# Kodi (source xbmc/video/tags/SetTagLoaderNFO.cpp + SetInfoTag.cpp, read 2026-11-17) reads
# <Movie set information folder>\<set name>\set.nfo — root <set>, tags <title>, <originaltitle>, <sorttitle>,
# <overview>, <art> — when a movie of that set is scanned.
# The user's answers (2026-11-17): a mistake = a missing / empty <title> or <overview>, a <title> that differs from
# the collection name in the movies' NFOs (Kodi matches by that name), or an overview in another language than the
# setting; text that only differs from TMDB's wording is shown, not flagged. Empty / missing tags are filled
# automatically; for differing text the user chooses "Use TMDB's" per collection. The overview in the app's TMDB
# language, English when TMDB has none.
# Series-ready (SR3): a set.nfo is collection-only by nature (movies); nothing here knows rows.
# =============================================================================
from __future__ import annotations

import re
from typing import Optional
from xml.sax.saxutils import escape

FILE_NAME = "set.nfo"
TAGS = ("title", "originaltitle", "sorttitle", "overview")


def build(title: str, overview: str = "", originaltitle: str = "", sorttitle: str = "") -> str:
    """A new set.nfo (UTF-8 text, LF): root <set>, only the tags that have a value plus <title>."""
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>', "<set>", f"  <title>{escape(title or '')}</title>"]
    for tag, val in (("originaltitle", originaltitle), ("sorttitle", sorttitle), ("overview", overview)):
        if (val or "").strip():
            lines.append(f"  <{tag}>{escape(val.strip())}</{tag}>")
    lines.append("</set>")
    return "\n".join(lines) + "\n"


def read(text: Optional[str]) -> Optional[dict]:
    """{tag: text} of a set.nfo ('' for an empty / missing tag); None when it is not a <set> document."""
    if not text or not re.search(r"<set\b", text, re.IGNORECASE):
        return None
    out = {}
    for tag in TAGS:
        m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}\s*>", text, re.IGNORECASE | re.DOTALL)
        v = (m.group(1) if m else "").strip()
        out[tag] = (v.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")
                    .replace("&amp;", "&"))
    return out


def check(existing: Optional[dict], name: str, overviews: dict, lang: str) -> dict:
    """The findings for one collection.

    existing = read(set.nfo) or None (no file); name = the collection name in the movies' NFOs; overviews = TMDB's
    {lang: overview}; lang = the app's TMDB language ('pt-BR' → 'pt').
    Returns {"mistakes": [codes], "notes": [codes], "want_overview": text}: mistakes "missing", "no_title", "no_overview",
    "title_differs", "other_language"; notes "overview_differs" (TMDB's wording differs — shown, not flagged)."""
    lg = (lang or "en").split("-")[0].lower()
    want = (overviews or {}).get(lg) or (overviews or {}).get("en") or ""
    if existing is None:
        return {"mistakes": ["missing"], "notes": [], "want_overview": want}
    mistakes, notes = [], []
    if not existing.get("title"):
        mistakes.append("no_title")
    elif _norm(existing["title"]) != _norm(name):
        mistakes.append("title_differs")
    ov = existing.get("overview") or ""
    if not ov:
        mistakes.append("no_overview")
    else:
        others = {k: v for k, v in (overviews or {}).items() if k != lg and v}
        if lg in (overviews or {}) and any(_norm(ov) == _norm(v) for v in others.values()):
            mistakes.append("other_language")
        elif want and _norm(ov) != _norm(want):
            notes.append("overview_differs")
    return {"mistakes": mistakes, "notes": notes, "want_overview": want}


def fill(text: str, title: str, overview: str) -> str:
    """The existing set.nfo with ONLY its empty / missing <title> and <overview> filled (other text untouched)."""
    cur = read(text) or {}
    out = text
    for tag, val in (("title", title), ("overview", overview)):
        if cur.get(tag) or not (val or "").strip():
            continue
        if re.search(rf"<{tag}\b[^>]*/>", out, re.IGNORECASE):
            out = re.sub(rf"<{tag}\b[^>]*/>", f"<{tag}>{escape(val.strip())}</{tag}>", out, count=1, flags=re.IGNORECASE)
        elif re.search(rf"<{tag}\b[^>]*>\s*</{tag}\s*>", out, re.IGNORECASE):
            out = re.sub(rf"(<{tag}\b[^>]*>)\s*(</{tag}\s*>)", lambda m: m.group(1) + escape(val.strip()) + m.group(2),
                         out, count=1, flags=re.IGNORECASE)
        else:
            out = re.sub(r"(\s*)</set\s*>", lambda m: f"\n  <{tag}>{escape(val.strip())}</{tag}>{m.group(1)}</set>", out,
                         count=1, flags=re.IGNORECASE)
    return out


def replace_tag(text: str, tag: str, value: str) -> str:
    """"Use TMDB's": the tag's text replaced (the tag added when missing); other text untouched."""
    if re.search(rf"<{tag}\b[^>]*>.*?</{tag}\s*>", text, re.IGNORECASE | re.DOTALL):
        return re.sub(rf"(<{tag}\b[^>]*>).*?(</{tag}\s*>)", lambda m: m.group(1) + escape(value.strip()) + m.group(2),
                      text, count=1, flags=re.IGNORECASE | re.DOTALL)
    return fill(text, value if tag == "title" else "", value if tag == "overview" else "")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()
