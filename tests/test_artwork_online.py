# =============================================================================
# test_artwork_online.py — pure tests of artwork_online.py (TF3 / TF1)
# MediaClinic v0.20.1                                            ### NEW v0.20.1 TF3 ###
# RUN:  python -m pytest -q test_artwork_online.py   (GitHub layout: tests/test_artwork_online.py)
# =============================================================================
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.dirname(_HERE)):
    if os.path.isfile(os.path.join(_cand, "artwork_online.py")):
        sys.path.insert(0, _cand)
        break

import artwork_online as ao  # noqa: E402


def E(lang, w=1000, h=1500, votes=0, src="tmdb"):
    return {"source": src, "lang": lang, "width": w, "height": h, "votes": votes}


def test_norm_lang():
    assert [ao.norm_lang(x) for x in ("pt-BR", "PT", "pt_BR", None, "", "00", "null", "xx", "es")] == \
        ["pt", "pt", "pt", "", "", "", "", "", "es"]


def test_settings_defaults_follow_the_library_language():
    assert ao.settings_language({}, "PT") == "pt" and ao.settings_language({"artwork_language": "library"}, "ES") == "es"
    assert ao.settings_language({"artwork_language": "de"}, "PT") == "de"
    assert ao.settings_mode({}) == "prefer" and ao.settings_mode({"artwork_language_mode": "x"}) == "prefer"
    assert ao.settings_textless({}) is True and ao.settings_textless({"artwork_textless_backgrounds": False}) is False


def test_poster_order_prefer_language_then_no_text_then_english():
    es = [E("en", 2000, 3000), E("fr", 2000, 3000), E(None, 1000, 1500), E("pt", 1000, 1500), E("pt", 2000, 3000)]
    out = ao.order_entries(es, "poster", "pt")
    assert [(e["lang"], e["width"]) for e in out] == [("pt", 2000), ("pt", 1000), (None, 1000), ("en", 2000), ("fr", 2000)]


def test_background_order_textless_first_or_language_first():
    es = [E("pt", 1920, 1080), E(None, 1280, 720), E("en", 3840, 2160)]
    assert [e["lang"] for e in ao.order_entries(es, "fanart", "pt", True)] == [None, "pt", "en"]
    assert [e["lang"] for e in ao.order_entries(es, "fanart", "pt", False)] == ["pt", None, "en"]


def test_english_library_no_duplicate_group():
    es = [E("de"), E("en"), E(None)]
    assert [e["lang"] for e in ao.order_entries(es, "poster", "en")] == ["en", None, "de"]


def test_only_mode_hides_other_languages_unless_show_all():
    es = [E("en"), E("pt"), E(None)]
    assert [e["lang"] for e in ao.offered(es, "poster", "pt", "only")] == ["pt"]
    assert len(ao.offered(es, "poster", "pt", "only", show_all=True)) == 3
    assert [e["lang"] for e in ao.offered(es, "fanart", "pt", "only", True)] == [None, "pt"]
    assert len(ao.offered(es, "poster", "pt", "prefer")) == 3


def test_best_replacement():
    es = [E("en", 2000, 3000), E("pt", 680, 1000), E("pt", 1400, 2100)]
    best, why = ao.best_replacement(es, "poster", "pt", "prefer", (1000, 1500), (480, 720))
    assert why is None and (best["lang"], best["width"]) == ("pt", 1400)
    best, why = ao.best_replacement([E("en", 2000, 3000)], "poster", "pt", "only", (1000, 1500), (480, 720))
    assert best is None and why == "other_language"
    best, why = ao.best_replacement([E("pt", 500, 750)], "poster", "pt", "prefer", (1000, 1500), (480, 720))
    assert best is None and why == "too_small"
    assert ao.best_replacement([], "poster", "pt", "prefer", (1000, 1500)) == (None, "no_images")
    best, _ = ao.best_replacement([E("pt", 960, 1440)], "poster", "pt", "prefer", (1000, 1500), (480, 720))
    assert best is not None                                   # within the ±5 % tolerance
    best, why = ao.best_replacement([E("pt", 1000, 1500)], "poster", "pt", "prefer", (1000, 1500), (1000, 1500))
    assert best is None and why == "too_small"                # not larger than the current one


def test_never_drops_or_reads_movie_fields():                   # SR3
    es = [{"lang": "pt", "width": 1, "height": 1}, {"lang": None}]
    assert len(ao.order_entries(es, "poster", "pt")) == 2
