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
