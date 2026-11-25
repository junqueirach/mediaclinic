# =============================================================================
# test_collection_gaps.py — pure tests of collection_gaps.py (v0.20.2 CG)
# RUN:  python -m pytest -q test_collection_gaps.py   (GitHub layout: tests/test_collection_gaps.py)
# =============================================================================
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.dirname(_HERE)):
    if os.path.isfile(os.path.join(_cand, "collection_gaps.py")):
        sys.path.insert(0, _cand)
        break

import collection_gaps as cg  # noqa: E402

TODAY = "2026-11-22"
MAIN = {"parts": [{"id": 1, "title": "Saga Um", "original_title": "Saga One", "release_date": "2001-05-01"},
                  {"id": 2, "title": "Saga Dois", "original_title": "Saga Two", "release_date": "2004-06-01"},
                  {"id": 3, "title": "Saga Três", "original_title": "Saga Three", "release_date": "2008-07-01"},
                  {"id": 4, "title": "Saga Quatro", "original_title": "Saga Four", "release_date": "2026-11-22"},  # today
                  {"id": 5, "title": "Saga Cinco", "original_title": "Saga Cinco", "release_date": ""},
                  {"id": 6, "title": "Saga Seis", "original_title": "Saga Six", "release_date": "2010-01-01"},
                  {"id": 7, "title": "Saga Sete", "original_title": "Saga Seven", "release_date": "2012-01-01"},
                  {"id": 8, "title": "Saga Oito", "original_title": "Saga Eight", "release_date": "2014-01-01"},
                  {"id": "x"}, {"title": "no id"}]}


def _row(name, year, tmdb=None, coll=None, nfo=True):
    return {"movie_name": name, "movie_year": str(year), "source_tmdb_val": str(tmdb or ""), "nfo_exists": nfo,
            "nfo_title": name, "coll_nfo": {"name": coll} if coll else None, "subfolder_path": f"/m/{name}"}


def test_parts_and_dates():
    p = cg.parts_from(MAIN)
    assert [x["id"] for x in p] == [1, 2, 3, 6, 7, 8, 4, 5]          # by date, no date last; bad entries dropped
    assert cg.released(p[0], TODAY) and not cg.released({"date": TODAY}, TODAY) and not cg.released({"date": ""}, TODAY)
    assert cg.released({"date": "2026-11-21"}, TODAY) and not cg.released({"date": "2027"}, TODAY)
    assert cg.shown_title(p[0]) == "Saga Um [Saga One]" and cg.shown_title({"title": "A", "original_title": "a"}) == "A"


def test_analyse_split_matching_and_fixes():
    members = [_row("Saga Um", 2001, 1, "Saga")]
    lib = members + [
        _row("Saga Dois", 2004, 2),                                   # (a) right ID, no collection
        _row("Saga Três", 2008, 3, "Another Saga"),                   # (c) in another collection
        _row("Saga Six", 2011, None),                                 # (b) title (original) + year ±1, no ID
        _row("Saga Sete", 2012, 999),                                 # (b) title + year, another ID
        _row("Saga Oito", 2014, 8, None, nfo=False),                  # no NFO: shown, no fix
        _row("Saga Dois", 1980, None),                                # same title, year too far: no match
    ]
    res = cg.analyse(10, "Saga", members, cg.parts_from(MAIN), cg.build_index(lib), today=TODAY)
    st = {it["part"]["id"]: it["status"] for it in res["missing"]}
    assert st == {2: cg.NO_TAG, 3: cg.OTHER, 6: cg.TITLE, 7: cg.TITLE, 8: cg.NO_NFO}
    assert res["have"] == 1 and res["total"] == 6
    assert [it["part"]["id"] for it in res["announced"]] == [4, 5]      # today and no date = announced
    assert next(it for it in res["missing"] if it["status"] == cg.OTHER)["other"] == "Another Saga"


def test_title_match_skips_rows_matched_by_id_and_confirmed_other_films():
    parts = [{"id": 1, "title": "Saga", "original_title": "Saga", "date": "2001-01-01"},
             {"id": 2, "title": "Saga", "original_title": "Saga", "date": "2002-01-01"}]
    one = _row("Saga", 2001, 1)                                       # has part 1's ID: never taken for part 2
    res = cg.analyse(10, "C", [], parts, cg.build_index([one]), today=TODAY)
    assert [(it["part"]["id"], it["status"]) for it in res["missing"]] == [(1, cg.NO_TAG), (2, cg.ABSENT)]
    remake = _row("Saga", 2002, 555)                                  # Verify IDs confirmed ID 555 (a remake)
    res = cg.analyse(10, "C", [], parts[1:], cg.build_index([remake]), today=TODAY, confirmed=lambda r: True)
    assert res["missing"][0]["status"] == cg.ABSENT


def test_ignore_list():
    d = cg.ignore({}, 10, 6)
    d = cg.ignore(d, 10, 6)
    assert d == {"10": [6]} and cg.ignored_ids(d, 10) == {6}
    res = cg.analyse(10, "Saga", [], cg.parts_from(MAIN), cg.build_index([]), ignored=cg.ignored_ids(d, 10), today=TODAY)
    assert 6 not in [it["part"]["id"] for it in res["missing"]] and [it["part"]["id"] for it in res["ignored"]] == [6]
    assert res["total"] == 5                                          # an ignored movie is not counted
    assert cg.unignore(d, 10, 6) == {}
    assert cg.clean_ignore({"10": [6, "7", "x", 6], "y": [1], "11": "no", "12": []}) == {"10": [6, 7]}
    assert cg.clean_ignore("bad") == {}


def test_report_text():
    t = lambda k, **kw: k + ("(" + ",".join(f"{a}={b}" for a, b in sorted(kw.items())) + ")" if kw else "")
    members = [_row("Saga Um", 2001, 1, "Saga")]
    res = cg.analyse(10, "Saga", members, cg.parts_from(MAIN), cg.build_index(members + [_row("Saga Dois", 2004, 2)]),
                     today=TODAY)
    txt = cg.report_text([res], [("Mine", "user"), ("Mix", "mixed")], ["Z:\\Filmes"], TODAY, t, n_movies=2)
    assert "Saga  (TMDB 10)" in txt and "cg.have(have=1,total=6)" in txt and "Saga Dois [Saga Two] — 2004-06-01" in txt
    assert "cg.st.no_tag(m=Saga Dois (2004))" in txt and "Saga Cinco — cg.no_date" in txt
    assert "Mine — cg.why.user" in txt and txt.endswith("\n")


def test_cache_entry_keeps_parts_and_staleness():
    import collection_rules as cr
    e = cr.coll_cache_entry({"parts": MAIN["parts"][:8]}, {"translations": []}, "pt-BR", 1000.0)
    assert e["parts"] == [1, 2, 3, 4, 5, 6, 7, 8] and e["lang"] == "pt-BR" and e["part_info"][0]["title"] == "Saga Um"
    now = 1000.0 + 5 * 86400
    assert not cr.gaps_entry_stale(e, "pt-BR", now) and not cr.gaps_entry_stale(e, "pt", now)
    assert cr.gaps_entry_stale(e, "en-US", now)                              # another language
    assert cr.gaps_entry_stale(e, "pt-BR", 1000.0 + 31 * 86400)              # older than 30 days
    assert cr.gaps_entry_stale({"names": {}, "parts": [1], "when": 1000.0}, "pt-BR", now)   # cached before v0.20.2
    assert cr.gaps_entry_stale({"names": {"en": "x"}, "overviews": {}}, "en", now)        # a Set Collection stub
    assert cr.gaps_entry_stale(None, "en", now)
