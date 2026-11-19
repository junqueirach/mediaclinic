# =============================================================================
# test_actors.py — pure tests of actors.py (AC1–AC6)
# MediaClinic v0.20.1                                            ### NEW v0.20.1 AC ###
# RUN:  python -m pytest -q test_actors.py   (GitHub layout: tests/test_actors.py)
# =============================================================================
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.dirname(_HERE)):
    if os.path.isfile(os.path.join(_cand, "actors.py")):
        sys.path.insert(0, _cand)
        break

import actors as ac  # noqa: E402

NFO = """<movie><title>X</title>
  <actor><name>Tom Hanks</name><role>A</role><thumb>https://image.tmdb.org/t/p/original/a.jpg</thumb></actor>
  <actor><name>Robin Wright</name><thumb>https://image.tmdb.org/t/p/original/b.png</thumb></actor>
  <actor><name>Gary Sinise</name></actor>
  <actor><name>  </name></actor>
  <actor><name>Mykelti Williamson &amp; Co</name><thumb></thumb></actor>
</movie>"""


def test_kodi_file_stem():
    assert ac.kodi_file_stem("Tom Hanks") == "Tom_Hanks"
    # Kodi 20 FetchActorThumbs: only spaces change; the compare is exact
    assert ac.kodi_file_stem("Sally Field.") == "Sally_Field." and ac.kodi_file_stem("Robert Downey Jr.") + ".jpg" == "Robert_Downey_Jr..jpg"
    assert not ac.storable(ac.kodi_file_stem('AC/DC: "Live"?')) and ac.storable("Lupita_Nyong'o")
    assert ac.download_plan([("AC/DC", "https://x/a.jpg"), ("Sally Field.", "https://x/b.jpg")], []) == [("Sally Field.", "https://x/b.jpg", "Sally_Field..jpg")]


def test_read_actors():
    got = ac.read_actors(NFO)
    assert [n for n, _u in got] == ["Tom Hanks", "Robin Wright", "Gary Sinise", "Mykelti Williamson & Co"]
    assert got[0][1].endswith("a.jpg") and got[2][1] == ""


def test_states():
    a = ac.read_actors(NFO)
    assert ac.actors_state([], [])["state"] == "none"
    assert ac.actors_state(a, None)["state"] == "links"
    s = ac.actors_state(a, ["Tom_Hanks.jpg", "Robin_Wright.png"])
    assert (s["state"], s["local"], s["links"], s["nophoto"], s["total"]) == ("local", 2, 0, 2, 4)
    s = ac.actors_state(a, ["Tom_Hanks.jpg"])
    assert s["state"] == "links" and s["local"] == 1 and s["links"] == 1
    assert ac.actors_state([("A", "")], [])["state"] == "none"     # actors, but no photo anywhere


def test_mismatches_and_orphans():
    a = ac.read_actors(NFO)
    s = ac.actors_state(a, ["Tom Hanks.jpg", "robin_wright.png", "Gary_Sinse.jpg", "Someone_Else.jpg", "notes.txt"])
    assert s["mismatches"] == [("Gary_Sinse.jpg", "Gary_Sinise.jpg"), ("Tom Hanks.jpg", "Tom_Hanks.jpg"),
                               ("robin_wright.png", "Robin_Wright.png")]
    assert s["orphans"] == ["Someone_Else.jpg"]


def test_download_plan_never_overwrites():
    a = ac.read_actors(NFO)
    plan = ac.download_plan(a, ["Tom_Hanks.png"])
    assert plan == [("Robin Wright", "https://image.tmdb.org/t/p/original/b.png", "Robin_Wright.png")]
