"""Pure tests of html_export.py (v0.20.1 TF7). No Tk, no network; images are made in a temp folder."""
import json
import os
import re
import shutil
import subprocess

import pytest

import html_export as hx


def _rows():
    return [{"movie_name": 'Amor, "Estranho" <Amor>', "movie_year": "1999", "genres": ["Drama", "Romance"], "rating_str": "7.4",
             "votes_int": 1200, "source_imdb_val": "tt0000001", "source_tmdb_val": "603", "video_quality": "4K",
             "audio_tracks": [{"language": "POR", "codec": "EAC3", "channels": "5.1"}], "subs_external": [{"lang": "en"}],
             "coll_nfo": {"name": "Trilogy"}, "subfolder_path": "C:/private/Amor", "subfolder": "Amor (1999)"},
            {"movie_name": "Plain", "movie_year": "-", "genres": [], "rating_str": "-", "subfolder_path": "C:/private/Plain"}]


def _data(page):
    return json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1))


def test_record_and_page_keep_data_safe_and_private(tmp_path):
    p = str(tmp_path / "list.html")
    assert hx.write_export(_rows(), ["movie_name", "year", "rating"], p, {"theme": "aurora", "title": "Mine"}) == 2
    page = open(p, encoding="utf-8").read()
    d = _data(page)
    m0, m1 = d["m"]
    assert m0["t"] == 'Amor, "Estranho" <Amor>' and m0["y"] == 1999 and m0["r"] == 7.4 and m0["col"] == "Trilogy"
    assert m0["res"] == "4K" and m0["au"] == "E-AC3 5.1" and m0["al"] == ["POR"] and m0["sl"] == ["EN"]
    assert m1["y"] is None and "r" not in m1 and m1["g"] == []
    assert "C:/private" not in page and "<Amor>" not in page.split('id="data">', 1)[1].split("</script>", 1)[0]
    assert 'class="t-aurora"' in page and "<title>Mine</title>" in page and d["k"] == ["movie_name", "year", "rating"]
    assert not os.path.exists(p + ".mctmp")


def test_options_without_ratings_plot_cast_flags_leave_them_out(tmp_path):
    p = str(tmp_path / "x.html")
    hx.write_export(_rows(), ["movie_name"], p, {"ratings": False, "cast": False, "flags": False, "plot": False})
    m0 = _data(open(p, encoding="utf-8").read())["m"][0]
    assert not ({"r", "v", "d", "a", "au", "vc", "hdr", "sl", "p"} & set(m0))


def test_online_mode_takes_only_https_links_from_the_nfo(tmp_path):
    nfo = tmp_path / "m.nfo"
    nfo.write_text('<movie><thumb aspect="poster">https://image.tmdb.org/t/p/original/p.jpg</thumb>'
                   '<fanart><thumb>https://image.tmdb.org/t/p/original/f.jpg</thumb></fanart></movie>', encoding="utf-8")
    r = dict(_rows()[1], nfo_exists=True, nfo_path=str(nfo))
    bad = tmp_path / "b.nfo"
    bad.write_text('<movie><thumb aspect="poster">javascript:alert(1)</thumb></movie>', encoding="utf-8")
    r2 = dict(_rows()[1], nfo_exists=True, nfo_path=str(bad))
    p = str(tmp_path / "o.html")
    hx.write_export([r, r2], ["movie_name"], p, {"images": "online"})
    d = _data(open(p, encoding="utf-8").read())
    assert d["m"][0]["pi"].endswith("/p.jpg") and d["m"][0]["fi"].endswith("/f.jpg") and "pi" not in d["m"][1]


def test_estimate_and_single_pass_template():
    assert hx.estimate_bytes(1000, "embed") > 30_000_000 > hx.estimate_bytes(1000, "online")
    page = hx.build_page([], [], [], hx.options({"title": "%%CSS%% %%DATA%%"}))
    assert page.count("<style>") == 1 and "&lt;" not in page.split("<title>")[1].split("</title>")[0]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_page_script_is_valid_javascript(tmp_path):
    js = tmp_path / "page.js"
    js.write_text(hx._JS, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr


def test_reexport_replaces_the_images_folder_and_each_export_has_its_own_storage_id(tmp_path):
    from PIL import Image
    pp = str(tmp_path / "p.jpg"); Image.new("RGB", (300, 450), (9, 9, 9)).save(pp)
    rows = [dict(r, poster_exists=True, poster_path=pp) for r in _rows()]
    p = str(tmp_path / "h #1.html")
    hx.write_export(rows, ["year"], p, {"images": "folder"}, when="2026-11-19 10:00")
    d1 = _data(open(p, encoding="utf-8").read())
    assert d1["k"][0] == "movie_name"                              # the title column is always there
    assert d1["m"][0]["pi"] == "h%20%231_images/0.jpg"            # the link is URL-encoded
    assert sorted(os.listdir(str(tmp_path / "h #1_images"))) == ["0.jpg", "1.jpg"]
    hx.write_export(rows[:1], ["year"], p, {"images": "folder"}, when="2026-11-19 10:05")
    d2 = _data(open(p, encoding="utf-8").read())
    assert os.listdir(str(tmp_path / "h #1_images")) == ["0.jpg"]  # no image of the earlier export is left
    assert d1["id"] != d2["id"] and not os.path.exists(str(tmp_path / "h #1_images.mctmp"))
    try:
        hx.write_export(rows, ["year"], p, {"images": "folder"}, cancelled=lambda: True)
    except RuntimeError:
        pass
    assert os.listdir(str(tmp_path / "h #1_images")) == ["0.jpg"] and not os.path.exists(p + ".mctmp")
