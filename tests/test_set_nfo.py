# =============================================================================
# test_set_nfo.py — pure tests of set_nfo.py (CF2)
# MediaClinic v0.20.1                                            ### NEW v0.20.1 CF2 ###
# RUN:  python -m pytest -q test_set_nfo.py   (GitHub layout: tests/test_set_nfo.py)
# =============================================================================
import os
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.dirname(_HERE)):
    if os.path.isfile(os.path.join(_cand, "set_nfo.py")):
        sys.path.insert(0, _cand)
        break

import set_nfo as sn  # noqa: E402

OV = {"pt": "A saga da família Corleone.", "en": "The saga of the Corleone family."}


def test_build_is_valid_xml_with_root_set():
    t = sn.build("O Poderoso Chefão — Coleção", "A & B", sorttitle="Poderoso")
    root = ET.fromstring(t.split("?>", 1)[1])
    assert root.tag == "set" and root.findtext("title") == "O Poderoso Chefão — Coleção"
    assert root.findtext("overview") == "A & B" and root.findtext("sorttitle") == "Poderoso"
    assert "<originaltitle>" not in t


def test_read():
    assert sn.read(None) is None and sn.read("<movie/>") is None
    r = sn.read("<set><title>X &amp; Y</title><overview/></set>")
    assert r["title"] == "X & Y" and r["overview"] == ""


def test_check():
    assert sn.check(None, "C", OV, "pt-BR")["mistakes"] == ["missing"]
    good = {"title": "C", "overview": OV["pt"]}
    assert sn.check(good, "C", OV, "pt-BR") == {"mistakes": [], "notes": [], "want_overview": OV["pt"]}
    assert sn.check({"title": "", "overview": ""}, "C", OV, "pt")["mistakes"] == ["no_title", "no_overview"]
    assert sn.check({"title": "C", "overview": ""}, "C", {}, "pt")["mistakes"] == []      # nothing to write yet: no mistake
    assert sn.check({"title": "Other", "overview": OV["pt"]}, "C", OV, "pt")["mistakes"] == ["title_differs"]
    assert sn.check({"title": "C", "overview": OV["en"]}, "C", OV, "pt")["mistakes"] == ["other_language"]
    r = sn.check({"title": "C", "overview": "My own text."}, "C", OV, "pt")
    assert r["mistakes"] == [] and r["notes"] == ["overview_differs"]
    assert sn.check(None, "C", {"en": "E"}, "de")["want_overview"] == "E"      # English when TMDB has none


def test_fill_only_gaps_and_replace():
    t = "<set>\n  <title>C</title>\n  <overview></overview>\n  <sorttitle>keep</sorttitle>\n</set>\n"
    f = sn.fill(t, "NEW", "Ov")
    assert "<title>C</title>" in f and "<overview>Ov</overview>" in f and "<sorttitle>keep</sorttitle>" in f
    g = sn.fill("<set>\n  <title>C</title>\n</set>\n", "C", "Ov")
    assert sn.read(g)["overview"] == "Ov" and g.strip().endswith("</set>")
    h = sn.replace_tag(f, "overview", "TMDB text")
    assert sn.read(h)["overview"] == "TMDB text" and "<sorttitle>keep</sorttitle>" in h


# ── v0.20.2 SE: the set.nfo editor (edit keeps <sorttitle> / <art>; entities, CDATA) ──   ### NEW v0.20.2 SE ###
KEEP = ('<?xml version="1.0" encoding="UTF-8"?>\n<set>\n    <title>Old</title>\n    <sorttitle>01 Saga</sorttitle>\n'
        '    <overview><![CDATA[Tom & <Jerry>]]></overview>\n    <art>\n      <poster>p.jpg</poster>\n    </art>\n</set>\n')


def test_read_entities_and_cdata():
    r = sn.read("<set><title>Am&#233;lie &amp; Co</title><overview><![CDATA[a & <b>]]> and &lt;c&gt;</overview></set>")
    assert r["title"] == "Amélie & Co" and r["overview"] == "a & <b> and <c>"


def test_edit_keeps_other_tags_and_untouched_fields():
    e = sn.edit(KEEP, "Saga", "Saga (orig)", "Tom & <Jerry>")       # overview unchanged → its CDATA stays as written
    assert "<![CDATA[Tom & <Jerry>]]>" in e and "<sorttitle>01 Saga</sorttitle>" in e and "<poster>p.jpg</poster>" in e
    v = sn.values(e)
    assert v == {"title": "Saga", "originaltitle": "Saga (orig)", "overview": "Tom & <Jerry>"}
    assert "\n    <originaltitle>Saga (orig)</originaltitle>\n</set>" in e          # added with <title>'s indent
    assert sn.edit(KEEP, "Old", "", "Tom & <Jerry>") == KEEP                       # nothing changed → same text


def test_edit_multiline_escape_and_clear():
    e = sn.edit(KEEP, "Old", "", "Line 1 & 2\n\nLine <3>")
    assert sn.read(e)["overview"] == "Line 1 & 2\n\nLine <3>" and "Line &lt;3&gt;" in e
    c = sn.edit(e, "Old", "", "")                                    # an emptied field: the tag goes, with its line
    assert "<overview" not in c and "<sorttitle>01 Saga</sorttitle>" in c and "\n\n</set>" not in c
    s = sn.edit("<set>\n  <title>T</title>\n  <originaltitle/>\n</set>\n", "T", "O", "")
    assert sn.read(s)["originaltitle"] == "O" and s.count("originaltitle>") == 2


def test_edit_refuses_a_non_set_document():
    import pytest
    with pytest.raises(ValueError):
        sn.edit("<movie><title>x</title></movie>", "x")
    assert sn.values("<movie/>") is None


def test_replace_tag_adds_originaltitle():
    t = sn.replace_tag("<set>\n  <title>C</title>\n</set>\n", "originaltitle", "Orig")
    assert sn.read(t)["originaltitle"] == "Orig"


def test_build_then_edit_round_trip():
    b = sn.build("Minha Coleção", "Uma & duas", "My Collection")
    assert sn.values(b) == {"title": "Minha Coleção", "originaltitle": "My Collection", "overview": "Uma & duas"}
    ET.fromstring(sn.edit(b, "Minha Coleção", "", "Nova <sinopse>").split("?>", 1)[1])   # still valid XML


# ── v0.20.2 SE / CG: which collections are the user's own (collection_rules.collection_kind) ──
def test_collection_kind():
    import collection_rules as cr
    k = cr.collection_kind
    saga = [{"coll_nfo": {"name": "Saga"}, "coll_tmdb": {"id": 10, "name": "Saga"}} for _ in range(3)]
    assert k(saga) == ("tmdb", 10)
    # the user, 2026-11-22: 3 movies of a saga + one TMDB lists in no collection = still the saga
    assert k(saga + [{"coll_nfo": {"name": "Saga"}, "coll_tmdb": {"id": None}}]) == ("tmdb", 10)
    assert k([{"coll_nfo": {"name": "Mine"}, "coll_tmdb": {"id": 10, "name": "Mine"}},
              {"coll_nfo": {"name": "Mine"}, "coll_tmdb": {"id": 20, "name": "Mine"}}]) == ("mixed", None)
    assert k([{"coll_nfo": {"name": "Mine"}, "coll_tmdb": {"id": None}}]) == ("user", None)
    assert k([{"coll_nfo": {"name": "Old", "tmdbcolid": "5"}, "coll_tmdb": {"id": None}}]) == ("gone", None)
    assert k([{"coll_nfo": {"name": "X"}}]) == ("unchecked", None)
    assert k([{"coll_nfo": {"name": "X", "tmdbcolid": "7"}}]) == ("tmdb", 7)               # not checked: the NFO decides
    assert k([{"coll_nfo": {"name": "X", "tmdbcolid": "7"}}, {"coll_tmdb": {"id": 9}}]) == ("tmdb", 9)   # online first
    # the user, 2026-11-22: a saga renamed in the NFOs ("My Saga", no tmdbcolid) is still the TMDB collection
    ren = [{"coll_nfo": {"name": "My Saga"}, "coll_tmdb": {"id": 10, "name": "Saga", "lang": "en"}} for _ in range(3)]
    assert k(ren, {"10": {"names": {"en": "Saga"}}}) == ("tmdb", 10)
    # Verify IDs flagged the movie: its TMDB data is left out (not checked)
    bad = [{"coll_nfo": {"name": "X"}, "coll_tmdb": {"id": 10, "name": "X"}, "id_check": {"result": "Wrong: other film"}}]
    assert k(bad) == ("unchecked", None)
