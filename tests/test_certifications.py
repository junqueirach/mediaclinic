# =============================================================================
# test_certifications.py — pure tests of certifications.py (v0.20.2 CR)
# RUN:  python -m pytest -q test_certifications.py   (GitHub layout: tests/test_certifications.py)
# =============================================================================
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.dirname(_HERE)):
    if os.path.isfile(os.path.join(_cand, "certifications.py")):
        sys.path.insert(0, _cand)
        break

import certifications as ce  # noqa: E402


def test_defaults_and_countries():
    assert ce.default_countries("pt_BR") == ["BR", "US"] and ce.default_countries("es") == ["ES", "US"]
    assert ce.default_countries("en") == ["US"] and ce.default_countries(None) == ["US"]
    assert ce.clean_countries("br, US de;us x1") == ["BR", "US", "DE"]


def test_parse_styles():
    p = ce.parse("US:PG-13 / BR:12")
    assert [(x["cc"], x["value"], x["style"]) for x in p] == [("US", "PG-13", "cc"), ("BR", "12", "cc")]
    assert [(x["cc"], x["value"]) for x in ce.parse("US: R; DE: 16; FR: 12")] == [("US", "R"), ("DE", "16"), ("FR", "12")]
    assert [(x["cc"], x["style"]) for x in ce.parse("Rated PG-13")] == [("US", "rated")]
    assert [(x["cc"], x["style"]) for x in ce.parse("PG-13")] == [("US", "bare")]   # not Papua New Guinea "13"
    assert [(x["cc"], x["value"]) for x in ce.parse("BR-12")] == [("BR", "12")]
    assert [(x["cc"], x["value"]) for x in ce.parse("FSK 12")] == [("DE", "FSK 12")]
    assert ce.parse("12")[0]["cc"] is None and ce.parse("⠀") == [] and ce.parse("") == []


def test_pick_tmdb_theatrical_first_earliest():
    res = [{"iso_3166_1": "BR", "release_dates": [{"type": 4, "certification": "14", "release_date": "2001-01-01"},
                                                 {"type": 3, "certification": "12", "release_date": "2002-01-01"},
                                                 {"type": 3, "certification": "16", "release_date": "2003-01-01"}]},
           {"iso_3166_1": "US", "release_dates": [{"type": 3, "certification": "", "release_date": "2001-01-01"},
                                                 {"type": 5, "certification": "R", "release_date": "2002-01-01"}]},
           {"iso_3166_1": "FR", "release_dates": [{"type": 3, "certification": ""}]}]
    assert ce.pick_tmdb(res) == {"BR": "12", "US": "R"}
    assert ce.omdb_us("N/A") is None and ce.omdb_us(" PG ") == "PG"


def test_plan_styles_order_max_and_adding():
    tags = {"nfo:mpaa": "Rated R", "nfo:certification": None,
            "xml:ContentRating": "R", "xml:MPAARating": None, "xml:certification": None,
            "xml:FullCertifications": "US: R; DE: 16; FR: 12; GB: 15", "xml:FormalMPAA": None}
    p = ce.plan(tags, ["BR", "US", "DE"], 2, online={"BR": "16"})
    assert p["status"] == "change" and p["values"] == [("BR", "16"), ("US", "R"), ("DE", "16")]
    assert p["writes"] == {"nfo:mpaa": "Rated 16", "xml:ContentRating": "16",          # each tag in its own style
                           "xml:FullCertifications": "BR: 16; US: R"}               # the list up to the max, FR / GB gone
    # a missing <mpaa> is added as CC:value; <certification> is never added
    p = ce.plan({"nfo:mpaa": None, "nfo:certification": None}, ["BR", "US"], 3, online={"BR": "12"})
    assert p["writes"] == {"nfo:mpaa": "BR:12"}
    # nothing to change
    assert ce.plan({"nfo:mpaa": "BR:12", "nfo:certification": None}, ["BR"], 3, online={})["status"] == "ok"
    # Kodi-style list in a single-value tag → one value
    assert ce.plan({"nfo:mpaa": "US:PG-13 / BR:12"}, ["BR", "US"], 3)["writes"] == {"nfo:mpaa": "BR:12"}


def test_plan_fallbacks_and_edge_case():
    # none of the accepted countries → the US rating, the user is told
    p = ce.plan({"nfo:mpaa": None}, ["BR"], 3, online={"US": "PG"})
    assert p["us_fallback"] and p["writes"] == {"nfo:mpaa": "US:PG"}
    # nothing anywhere → the tag stays blank, status "none"
    assert ce.plan({"nfo:mpaa": None}, ["BR"], 3, online={})["status"] == "none"
    assert ce.plan({"nfo:mpaa": ""}, ["BR"], 3, online={}) ["writes"] == {}
    # only other countries in the file and nothing online → ask; keep / blank
    tags = {"nfo:mpaa": "FR:12", "nfo:certification": "FR:12"}
    assert ce.plan(tags, ["BR"], 3, online={})["status"] == "ask"
    assert ce.plan(tags, ["BR"], 3, online={}, choice="keep")["writes"] == {}
    assert ce.plan(tags, ["BR"], 3, online={}, choice="blank")["writes"] == {"nfo:mpaa": "", "nfo:certification": ""}


def test_findings():
    tags = {"nfo:mpaa": "US:PG-13 / BR:12", "xml:FullCertifications": "US: R; DE: 16; FR: 12; GB: 15",
            "xml:ContentRating": None}
    f = ce.findings(tags, ["US", "BR", "DE"], 3)
    assert ("several", "mpaa", 2) in f and ("other_country", "FullCertifications", "FR") in f
    assert ("too_many", "FullCertifications", 4) in f
    assert ce.findings({"nfo:mpaa": "BR:12"}, ["BR"], 3) == [] and ce.findings({"nfo:mpaa": "12"}, ["BR"], 3) == []


def test_read_and_write_tags():
    nfo = "<movie>\n  <title>X</title>\n  <mpaa>Rated R</mpaa>\n  <certification/>\n</movie>\n"
    assert ce.read_tags(nfo, "nfo") == {"nfo:mpaa": "Rated R", "nfo:certification": ""}
    assert ce.read_tags(None, "nfo") == {}
    t = ce.write_tag(nfo, "mpaa", "BR:12 & <x>")
    assert "<mpaa>BR:12 &amp; &lt;x&gt;</mpaa>" in t and t.count("<mpaa>") == 1
    t = ce.write_tag(t, "certification", "BR:12")
    assert "<certification>BR:12</certification>" in t
    a = ce.write_tag("<movie>\n  <title>X</title>\n</movie>\n", "mpaa", "BR:12")
    assert a == "<movie>\n  <title>X</title>\n  <mpaa>BR:12</mpaa>\n</movie>\n"
    x = ce.write_tag("<Title>\n\t<LocalTitle>X</LocalTitle>\n</Title>", "ContentRating", "BR:12")
    assert "\t<ContentRating>BR:12</ContentRating>\n</Title>" in x
