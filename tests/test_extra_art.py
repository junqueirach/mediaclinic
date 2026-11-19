# =============================================================================
# test_extra_art.py — pure tests of extra_art.py (EA1, EA2, EA4, EA5)
# MediaClinic v0.20.1                                            ### NEW v0.20.1 EA ###
# RUN:  python -m pytest -q test_extra_art.py   (GitHub layout: tests/test_extra_art.py)
# =============================================================================
import os
import struct
import sys
import tempfile
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.dirname(_HERE)):
    if os.path.isfile(os.path.join(_cand, "extra_art.py")):
        sys.path.insert(0, _cand)
        break

import extra_art as ea  # noqa: E402


def _png(path, color_type, trns=False):
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, color_type, 0, 0, 0))
    if trns:
        data += chunk(b"tRNS", b"\x00\x00")
    data += chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) + chunk(b"IEND", b"")
    open(path, "wb").write(data)


def test_kind_of():
    assert ea.kind_of("clearlogo.png", ea.SKIN_KINDS) == "clearlogo"
    assert ea.kind_of("Movie (2001)-discart.png", ea.SKIN_KINDS) == "discart"
    assert ea.kind_of("poster.jpg", ea.SKIN_KINDS) is None


def test_png_alpha():
    d = tempfile.mkdtemp()
    a, b, c, j = (os.path.join(d, n) for n in ("a.png", "b.png", "c.png", "j.png"))
    _png(a, 6); _png(b, 2); _png(c, 2, trns=True); open(j, "wb").write(b"\xff\xd8\xff")
    assert (ea.png_alpha(a), ea.png_alpha(b), ea.png_alpha(c), ea.png_alpha(j)) == (True, False, True, None)


def test_summary_counts_and_notes():
    names = ["logo.png", "disc.png", "clearart.jpg", "banner.jpg", "landscape.jpg", "Movie-keyart.jpg", "fanart.jpg"]
    s = ea.summary(names, {"logo.png": True, "disc.png": False}, ("kodi",), has_extrafanart=True)
    assert s["count"] == 6 and s["missing"] == []
    codes = {(n, c) for n, c, _t in s["notes"]}
    assert ("logo.png", "kodi_name") in codes and ("disc.png", "kodi_name") in codes
    assert ("clearart.jpg", "not_png") in codes and ("disc.png", "no_alpha") in codes and ("extrafanart", "extrafanart") in codes
    assert ("logo.png", "clearlogo.png") in s["renames"] and ("disc.png", "discart.png") in s["renames"]


def test_rename_only_when_every_ticked_program_reads_the_new_name():
    assert ea.rename_allowed("logo", ("kodi",)) and ea.rename_allowed("logo", ("kodi", "emby", "jellyfin"))
    assert not ea.rename_allowed("disc", ("kodi", "emby"))        # Emby does not read discart
    assert not ea.rename_allowed("logo", ("kodi", "plex"))        # Plex: not known
    assert not ea.rename_allowed("logo", ("emby",))               # Kodi not ticked: no reason to rename
    s = ea.summary(["disc.png"], {}, ("kodi", "emby"))
    assert s["renames"] == [] and s["notes"][0][1] == "kodi_name"


def test_fanart_numbers_plan_never_overwrites():
    plan = ea.fanart_numbers_plan(["a.jpg", "b.png", "notes.txt", "c.jpeg"], ["fanart1.jpg", "fanart.jpg"])
    assert plan == [("a.jpg", "fanart2.jpg"), ("b.png", "fanart3.png"), ("c.jpeg", "fanart4.jpg")]
    assert ea.fanart_numbers_plan(["a.jpg"], [], prefix="Movie (2001)-") == [("a.jpg", "Movie (2001)-fanart1.jpg")]
