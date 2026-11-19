"""Pure tests of id_repair.py (v0.20.1 T1 / T2 / T5). The fixture is a trimmed copy of the NFO a tester sent
(55 Days at Peking, written by Emby): the TMDB number 27759 sits in the IMDb tags."""
import id_repair as ir

PEKING = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<movie>
  <title>55 Days at Peking</title>
  <actor>
    <name>Charlton Heston</name>
    <tmdbid>10017</tmdbid>
    <imdbid>nm0000032</imdbid>
  </actor>
  <actor>
    <name>Ava Gardner</name>
    <tmdbid>27759</tmdbid>
    <imdbid>27759</imdbid>
  </actor>
  <director tmdbid="2765" imdbid="nm0712947">Nicholas Ray</director>
  <year>1963</year>
  <imdbid>27759</imdbid>
  <tvdbid>12956</tvdbid>
  <tmdbid>27759</tmdbid>
  <uniqueid type="imdb">27759</uniqueid>
  <uniqueid type="tvdb">12956</uniqueid>
  <uniqueid type="tmdb">27759</uniqueid>
  <imdb id="tt0056800">https://www.imdb.com/title/tt0056800</imdb>
  <tmdb id="27759">https://www.themoviedb.org/movie/27759</tmdb>
</movie>
"""


def test_link_ids_reads_emby_link_lines():
    assert ir.link_ids(PEKING) == {"imdb": ["tt0056800"], "tmdb": ["27759"]}
    assert ir.link_ids("<imdb>no id</imdb>") == {"imdb": [], "tmdb": []}


def test_diagnose_tmdb_number_invalid_and_reverse():
    d = ir.diagnose("imdb", ["27759"], [], ["tt0056800"], ["27759"])
    assert d == {"kind": "imdb", "values": ["27759"], "why": "tmdb_number", "suggest": "tt0056800", "from": "link"}
    # digits that are NOT the file's TMDB ID: "not a correct IMDb ID" (the user's rule), no suggestion → ask TMDB
    d2 = ir.diagnose("imdb", ["0056800"], [], [], ["27759"])
    assert d2["why"] == "invalid" and d2["suggest"] == ""
    assert ir.diagnose("imdb", ["tt005680"], ["tt0056800"], [], [])["from"] == "tag"      # a typo next to a good tag
    assert ir.diagnose("tmdb", ["tt0056800"], [], ["27759"], ["tt0056800"])["why"] == "imdb_id"
    assert ir.diagnose("imdb", [], [], [], []) is None


def test_replace_ids_touches_only_existing_root_tags():
    new, n = ir.replace_ids(PEKING, "imdb", ["27759"], "tt0056800")
    assert n == 2
    assert "<imdbid>tt0056800</imdbid>" in new and '<uniqueid type="imdb">tt0056800</uniqueid>' in new
    assert "<imdbid>27759</imdbid>\n  </actor>" in new                      # the actor's tag is not the movie's
    assert new.count("<imdbid>") == PEKING.count("<imdbid>") and new.count("<uniqueid") == PEKING.count("<uniqueid")
    assert "<tmdbid>27759</tmdbid>\n  <uniqueid" in new                      # the TMDB tags keep 27759
    assert new.replace(">tt0056800<", ">27759<") == PEKING                   # nothing else changed


def test_replace_ids_keeps_crlf_spacing_and_plain_id_rules():
    crlf = "<movie>\r\n  <id> 27759 </id>\r\n  <id>tt005680</id>\r\n</movie>\r\n"
    new, n = ir.replace_ids(crlf, "imdb", ["27759", "tt005680"], "tt0056800")
    # a plain numeric <id> is Kodi's default ID (often TMDB's number): left alone; a plain tt-typo is corrected
    assert n == 1 and new == "<movie>\r\n  <id> 27759 </id>\r\n  <id>tt0056800</id>\r\n</movie>\r\n"
    xml = "<Title>\n  <IMDB>27759</IMDB>\n  <TMDbId>27759</TMDbId>\n</Title>\n"
    assert ir.replace_ids(xml, "imdb", ["27759"], "tt0056800", xml=True) == (xml.replace("<IMDB>27759", "<IMDB>tt0056800"), 1)
    try:
        ir.replace_ids(PEKING, "imdb", ["27759"], "27759")
        assert False, "an invalid replacement is refused"
    except ValueError:
        pass


def test_root_level_only_cdata_and_link_lines():
    t = ("<movie>\n  <set />\n  <producer><imdbid>27759</imdbid></producer>\n"
         "  <imdbid><![CDATA[27759]]></imdbid>\n  <set><name>X</name></set>\n"
         "  <plot>see https://www.imdb.com/title/tt9999999/</plot>\n</movie>\n")
    new, n = ir.replace_ids(t, "imdb", ["27759"], "tt0056800")
    assert n == 1 and "<imdbid>tt0056800</imdbid>" in new                 # the CDATA value at root level
    assert "<producer><imdbid>27759</imdbid></producer>" in new          # a deeper tag is not the movie's
    assert ir.link_ids(t) == {"imdb": [], "tmdb": []}                    # an address in the plot is not the movie's ID
    assert ir.link_ids("<imdb>https://www.imdb.com/title/tt0056800</imdb>")["imdb"] == ["tt0056800"]
    assert ir.diagnose("imdb", ["27759"], ["tt0056800/"], [], ["27759"])["suggest"] == "tt0056800"
