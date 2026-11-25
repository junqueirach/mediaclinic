# =============================================================================
# collection_gaps.py — "Collection Gaps": the movies of a TMDB collection the library lacks (pure: no Tk, no
# network, no files)
# MediaClinic v0.20.2 CG                                          ### NEW v0.20.2 CG ###
#
# The user's rules (2026-11-22):
#   - only TMDB collections are analysed (collection_rules.collection_kind == "tmdb"); the others are listed at the
#     end as "Ignored Collections (no TMDB ID)" with the reason (your own / mixed / no longer on TMDB / not checked);
#   - two lists per collection: Missing (released: a release date before today) and Announced, not released yet
#     (a later date or none; information only, not counted); "You have N of M" counts the released ones;
#   - titles in the library's TMDB language, the original title in brackets when it differs, the date as a control;
#   - matching: first by TMDB ID over the WHOLE library, then by title + year (±1) on the titles in the files;
#   - fixes: (a) the movie is there with the right ID but not in this collection → add it; (b) matched by title →
#     write TMDB ID (+ IMDb ID) + collection after the user's OK; (c) it is in another collection → move on a click;
#     no NFO → shown, no fix;
#   - an ignore list ("I don't want this one"): {collection id: [movie ids]}, left out of the lists, counted.
# Series-ready (SR3): a collection is a movie thing; nothing here knows Tk or files.
# =============================================================================
from __future__ import annotations

import datetime
import re

import collection_rules as _cr

FILE_STEM = "Collection Gaps"

# status of a missing movie
HAVE, NO_TAG, OTHER, TITLE, NO_NFO, ABSENT = "have", "no_tag", "other", "title", "no_nfo", "absent"


def parts_from(main):
    """[{"id", "title", "original_title", "date"}] from a TMDB /collection/{id} answer (collection_rules.part_info_from)."""
    return _cr.part_info_from(main)


def today_iso(today=None):
    return (today or datetime.date.today()).isoformat()


def released(part, today):
    """True when the part has a release date before *today* (ISO 'YYYY-MM-DD')."""
    d = part.get("date") or ""
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", d)) and d < today


def part_year(part):
    m = re.match(r"^(\d{4})", part.get("date") or "")
    return int(m.group(1)) if m else None


def shown_title(part):
    """'Title [Original title]' — the original in brackets only when it differs."""
    t, o = part.get("title") or "", part.get("original_title") or ""
    if o and _cr.norm_name(o) != _cr.norm_name(t):
        return f"{t} [{o}]" if t else o
    return t or o


def row_tmdb(row):
    try:
        v = int(str(row.get("source_tmdb_val") or "").strip())
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def row_year(row):
    m = re.match(r"^\s*(\d{4})", str(row.get("movie_year") or ""))
    return int(m.group(1)) if m else None


def file_titles(row):
    """The titles in the movie's files (NFO <title>, movie.xml <LocalTitle>, the shown name) as loose keys. TMDB's
    titles of the row are NOT used: they belong to its current ID, which may be the wrong one."""
    out = set()
    for t in (row.get("nfo_title"), row.get("xml_localtitle"), row.get("movie_name")):
        k = _cr.loose_title(t or "")
        if k:
            out.add(k)
    return out


def build_index(rows):
    """{"id": {tmdb id: [rows]}, "title": {loose title: [rows]}} over the whole library."""
    by_id, by_t = {}, {}
    for r in rows or ():
        i = row_tmdb(r)
        if i:
            by_id.setdefault(i, []).append(r)
        for k in file_titles(r):
            by_t.setdefault(k, []).append(r)
    return {"id": by_id, "title": by_t}


def _title_match(part, index, skip_ids, confirmed):
    y = part_year(part)
    if y is None:
        return None
    keys = {_cr.loose_title(part.get("title") or ""), _cr.loose_title(part.get("original_title") or "")} - {""}
    for k in sorted(keys):
        for r in index["title"].get(k) or ():
            ry, rid = row_year(r), row_tmdb(r)
            if ry is None or abs(ry - y) > 1:
                continue
            if rid in skip_ids:                                   # matched by ID to a part of this collection
                continue
            if rid and confirmed(r):                              # Verify IDs confirmed another film (a remake)
                continue
            return r
    return None


def analyse(cid, name, members, parts, index, ignored=(), today=None, has_nfo=None, confirmed=None, group_key=None):
    """One TMDB collection.  *members* = its rows (every spelling of its name); *parts* = parts_from(...);
    *index* = build_index(whole library); *ignored* = the movie ids the user does not want.
    Returns {"cid", "name", "have", "total", "missing": [item], "announced": [item], "ignored": [item]};
    item = {"part", "status", "row", "other"}: status HAVE / NO_TAG (a) / TITLE (b) / OTHER (c) / NO_NFO / ABSENT;
    "other" = the collection name the movie is in now (OTHER, and TITLE when it is in another one)."""
    today = today or today_iso()
    has_nfo = has_nfo or (lambda r: bool(r.get("nfo_exists")))
    confirmed = confirmed or (lambda r: False)
    group_key = group_key or _cr.group_key
    mine = {id(r) for r in members}
    part_ids = {p["id"] for p in parts}
    ign = {int(x) for x in ignored or ()}
    out = {"cid": cid, "name": name, "have": 0, "total": 0, "missing": [], "announced": [], "ignored": []}
    for p in parts:
        rows_id = (index["id"].get(p["id"]) or [])
        if any(id(r) in mine for r in rows_id):
            item = {"part": p, "status": HAVE, "row": next(r for r in rows_id if id(r) in mine), "other": None}
        elif rows_id:
            r = rows_id[0]
            g = group_key(r)
            st = NO_NFO if not has_nfo(r) else OTHER if g else NO_TAG
            item = {"part": p, "status": st, "row": r, "other": _cr_name(r) if g else None}
        else:
            r = _title_match(p, index, part_ids, confirmed)
            if r is None:
                item = {"part": p, "status": ABSENT, "row": None, "other": None}
            else:
                g = group_key(r)
                item = {"part": p, "status": NO_NFO if not has_nfo(r) else TITLE, "row": r,
                        "other": _cr_name(r) if g and id(r) not in mine else None}
        is_rel = released(p, today)
        if item["status"] == HAVE:                                # in the collection: counted (released only)
            if is_rel:
                out["total"] += 1
                out["have"] += 1
            continue
        if p["id"] in ign:                                        # the user does not want it: not listed, not counted
            out["ignored"].append(item)
        elif not is_rel:
            out["announced"].append(item)
        else:
            out["total"] += 1
            out["missing"].append(item)
    return out


def _cr_name(row):
    return ((row.get("coll_nfo") or {}).get("name") or "").strip() or None


# ── the ignore list ({"<collection id>": [movie ids]}) ──
def ignored_ids(data, cid):
    return {int(x) for x in ((data or {}).get(str(cid)) or []) if str(x).isdigit()}


def ignore(data, cid, pid):
    d = {k: list(v) for k, v in (data or {}).items()}
    lst = d.setdefault(str(cid), [])
    if int(pid) not in lst:
        lst.append(int(pid))
    return d


def unignore(data, cid, pid):
    d = {k: [x for x in v if int(x) != int(pid)] for k, v in (data or {}).items()}
    return {k: v for k, v in d.items() if v}


def clean_ignore(data):
    """A read file made safe: {str(int): sorted unique ints}; anything else dropped."""
    out = {}
    for k, v in (data or {}).items() if isinstance(data, dict) else ():
        if not str(k).isdigit() or not isinstance(v, list):
            continue
        ids = sorted({int(x) for x in v if isinstance(x, int) or (isinstance(x, str) and x.isdigit())})
        if ids:
            out[str(int(k))] = ids
    return out


# ── the report as text (Save as .txt) ──
def report_text(results, skipped, libraries, today, t, n_movies=0):
    """*results* = analyse() outputs; *skipped* = [(name, reason code)] (user / mixed / gone / not_checked / no_id);
    *t* = the translation function (mc_i18n.t)."""
    L = [t("cg.title"), t("cg.date", d=today), t("cg.libraries", libs=", ".join(libraries) or "—", n=n_movies),
         t("cg.libraries_note"), ""]
    for res in results:
        L.append(f"{res['name']}  (TMDB {res['cid']})")
        L.append("  " + t("cg.have", have=res["have"], total=res["total"]))
        if res["missing"]:
            L.append("  " + t("cg.missing") + ":")
            for it in res["missing"]:
                L.append(f"    - {shown_title(it['part'])} — {it['part']['date'] or t('cg.no_date')}"
                         + (f"  ({status_text(it, t)})" if it["status"] != ABSENT else ""))
        if res["announced"]:
            L.append("  " + t("cg.announced") + ":")
            for it in res["announced"]:
                L.append(f"    - {shown_title(it['part'])} — {it['part']['date'] or t('cg.no_date')}")
        if res["ignored"]:
            L.append("  " + t("cg.ignored_n", n=len(res["ignored"])))
        L.append("")
    if skipped:
        L.append(t("cg.skipped_head"))
        for nm, why in skipped:
            L.append(f"  - {nm} — {t('cg.why.' + why)}")
    return "\n".join(L).rstrip() + "\n"


def status_text(item, t):
    """What the library has of a missing movie (and what a fix does), in words."""
    r = item.get("row") or {}
    nm = r.get("movie_name") or r.get("subfolder") or "?"
    yr = r.get("movie_year")
    label = f"{nm} ({yr})" if yr and yr != "-" else nm
    if item["status"] == NO_TAG:
        return t("cg.st.no_tag", m=label)
    if item["status"] == OTHER:
        return t("cg.st.other", m=label, c=item.get("other") or "?")
    if item["status"] == TITLE:
        return t("cg.st.title", m=label)
    if item["status"] == NO_NFO:
        return t("cg.st.no_nfo", m=label)
    return ""
