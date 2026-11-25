# =============================================================================
# test_renamer.py — pure tests of renamer.py (v0.20.2 RN)
# RUN:  python -m pytest -q test_renamer.py   (GitHub layout: tests/test_renamer.py)
# =============================================================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import renamer as rn  # noqa: E402

F = {"title": "The Matrix", "originaltitle": "The Matrix", "year": "1999", "quality": "1080p", "codec": "HEVC",
     "audio": "DTS", "genre": ["Action", "Sci-Fi"], "imdb": "tt0133093", "tmdb": "603", "hdr": ""}


def test_patterns():
    assert rn.folder_name_for(F, 1) == ("The Matrix (1999)", None)
    assert rn.folder_name_for(F, 2) == ("The Matrix (1999) [1080p]", None)
    assert rn.folder_name_for(F, 3) == ("The Matrix (1999) [1080p] [Action]", None)
    assert rn.folder_name_for(F, 4) == ("The Matrix (1999) [imdbid-tt0133093]", None)
    assert rn.folder_name_for(F, 5) == ("The Matrix (1999) [tmdb-603]", None)      # the one form all three read
    assert rn.folder_name_for(F, 6) == ("The Matrix (1999) [1080p HEVC DTS]", None)
    assert rn.folder_name_for(dict(F, tmdb=""), 5) == ("", "no_tmdb")
    assert rn.folder_name_for(dict(F, imdb=None), 4) == ("", "no_imdb")
    assert rn.folder_name_for(dict(F, title="", originaltitle=""), 1) == ("", "no_title")


def test_empty_groups_vanish():
    g = dict(F, quality="", codec="", audio="")
    assert rn.folder_name_for(g, 2)[0] == "The Matrix (1999)"
    assert rn.folder_name_for(g, 6)[0] == "The Matrix (1999)"
    assert rn.folder_name_for(dict(F, codec=""), 6)[0] == "The Matrix (1999) [1080p DTS]"
    assert rn.folder_name_for(dict(F, year=""), 1) == ("", "no_year")          # a pattern with {year} needs one
    assert rn.folder_name_for(dict(F, year=""), 7, "{title} [{quality}]")[0] == "The Matrix [1080p]"
    assert rn.render("{title} [tmdb-{tmdb}] - {collection}", dict(F, tmdb="")) == "The Matrix"


def test_custom_article_dots():
    assert rn.folder_name_for(F, 7, "{originaltitle} - {year}")[0] == "The Matrix - 1999"
    assert rn.folder_name_for(F, 7, "")[0] == "The Matrix (1999)"                   # empty custom → pattern 1
    assert rn.folder_name_for(F, 1, article=True)[0] == "Matrix, The (1999)"
    assert rn.move_article("O Auto da Compadecida", "pt") == "Auto da Compadecida, O"
    assert rn.move_article("Amélie", "fr") == "Amélie"
    assert rn.move_article("L'Odyssée", "fr") == "Odyssée, L'"
    assert rn.folder_name_for(F, 2, dots=True)[0] == "The.Matrix.(1999).[1080p]"
    assert rn.changing_tokens("{title} [{quality}] [{genre}]") == ["quality", "genre"]
    assert rn.unknown_tokens("{title} {foo}") == ["foo"]


def test_safe_names():
    assert rn.safe_name("Mission: Impossible") == ("Mission - Impossible", None)
    assert rn.safe_name('What? "Now" <x>|y*') == ("What Now xy", None)
    assert rn.safe_name("Movie. ") == ("Movie", None)
    assert rn.safe_name("CON") == ("CON", "reserved")
    assert rn.safe_name("nul.txt")[1] == "reserved"
    assert rn.safe_name("  ") == ("", "empty")
    nfd = "Ame\u0301lie (2001)"
    assert rn.safe_name(nfd)[0] == "Amélie (2001)"
    assert rn.same_name(nfd, "Amélie (2001)")
    assert rn.quality_text("4K UHD") == "2160p" and rn.quality_text("576p/DVD") == "576p" and rn.quality_text("—") == ""


def test_follows():
    b = "the matrix"
    for n in ("the matrix.mkv", "The Matrix.nfo", "the matrix-poster.jpg", "the matrix.pt.forced.srt",
              "the matrix-trailer.mkv", "the matrix-cd1.mkv", "the matrix - 1080p.mkv", "the matrix {edition-Cut}.mkv"):
        assert rn.follows(n, b), n
    for n in ("the matrix reloaded.mkv", "poster.jpg", "movie.nfo", "the matrix", "the matrix2.mkv"):
        assert not rn.follows(n, b), n


def test_plan_single():
    files = ["the.matrix.1999.mkv", "the.matrix.1999.nfo", "the.matrix.1999-poster.jpg", "poster.jpg", "movie.nfo",
             "the.matrix.1999.pt.srt"]
    p = rn.plan_movie(r"M:\Movies\the matrix (1999)", files, "the.matrix.1999.mkv", None,
                      new_folder="The Matrix (1999)")
    assert p["problem"] is None and p["case_only"]
    assert p["folder"] == (os.path.join(r"M:\Movies", "the matrix (1999)"), os.path.join(r"M:\Movies", "The Matrix (1999)"))
    assert dict(p["files"]) == {"the.matrix.1999.mkv": "The Matrix (1999).mkv",
                                "the.matrix.1999.nfo": "The Matrix (1999).nfo",
                                "the.matrix.1999-poster.jpg": "The Matrix (1999)-poster.jpg",
                                "the.matrix.1999.pt.srt": "The Matrix (1999).pt.srt"}
    # an NFO named after the old folder AND one after the video would both become "The Matrix (1999).nfo"
    p = rn.plan_movie(r"M:\Movies\the matrix (1999)", files + ["the matrix (1999).nfo"], "the.matrix.1999.mkv", None,
                      new_folder="The Matrix (1999)")
    assert p["problem"] == "same_target" and p["folder"] is None


def test_plan_same_target_and_exists():
    # two NFOs (video name and old folder name) would get the same new name → the movie is skipped
    p = rn.plan_movie(r"M:\M\Old", ["vid.mkv", "vid.nfo", "Old.nfo"], "vid.mkv", None, new_folder="New (2000)")
    assert p["problem"] == "same_target" and p["folder"] is None
    p = rn.plan_movie(r"M:\M\Old", ["vid.mkv"], "vid.mkv", None, new_folder="Taken",
                      exists=lambda path: path.endswith("Taken"))
    assert p["problem"] == "exists"
    # a case-sensitive NAS: "The Matrix (1999)" exists next to "the matrix (1999)" → a conflict, not a case-only rename
    p = rn.plan_movie(r"M:\M\the matrix (1999)", ["v.mkv"], "v.mkv", None, new_folder="The Matrix (1999)",
                      siblings=["the matrix (1999)", "The Matrix (1999)"])
    assert p["problem"] == "exists"
    p = rn.plan_movie(r"M:\M\the matrix (1999)", ["v.mkv"], "v.mkv", None, new_folder="The Matrix (1999)",
                      siblings=["the matrix (1999)"])
    assert p["problem"] is None and p["case_only"]
    # a file that does not move already has the new name
    p = rn.plan_movie(r"M:\M\Old", ["vid.mkv", "New (2000).mkv"], "vid.mkv", None, new_folder="New (2000)")
    assert p["problem"] == "file_exists"
    p = rn.plan_movie(r"M:\M\Same (1999)", ["Same (1999).mkv"], "Same (1999).mkv", None, new_folder="Same (1999)")
    assert p["problem"] == "nothing"
    p = rn.plan_movie(r"M:\M\Old", ["vid.mkv"], "vid.mkv", None, new_folder="N" * 300)
    assert p["problem"] == "too_long"


def test_plan_stack_versions_disc():
    p = rn.plan_movie(r"M:\M\Old", ["Old-cd1.mkv", "Old-cd2.mkv", "Old-poster.jpg", "Old.nfo"], "Old-cd1.mkv",
                      "stack", new_folder="New (2000)", stack_title="Old")
    assert dict(p["files"]) == {"Old-cd1.mkv": "New (2000)-cd1.mkv", "Old-cd2.mkv": "New (2000)-cd2.mkv",
                                "Old-poster.jpg": "New (2000)-poster.jpg", "Old.nfo": "New (2000).nfo"}
    p = rn.plan_movie(r"M:\M\Movie (2021)", ["Movie (2021) - 1080p.mkv", "Movie (2021) - 720p.mkv", "movie.nfo"],
                      "Movie (2021) - 1080p.mkv", "versions", new_folder="Movie (2021) [tmdb-1]")
    assert dict(p["files"]) == {"Movie (2021) - 1080p.mkv": "Movie (2021) [tmdb-1] - 1080p.mkv",
                                "Movie (2021) - 720p.mkv": "Movie (2021) [tmdb-1] - 720p.mkv"}
    p = rn.plan_movie(r"M:\M\old dvd", ["old dvd.nfo", "poster.jpg"], None, None, new_folder="New (1990)", disc=True)
    assert p["folder"] and dict(p["files"]) == {"old dvd.nfo": "New (1990).nfo"}


def test_files_only_and_batch():
    p = rn.plan_movie(r"M:\M\Heat (1995)", ["heat.mkv", "heat.nfo"], "heat.mkv", None, new_folder="X",
                      rename_folder=False)
    assert p["folder"] is None and dict(p["files"]) == {"heat.mkv": "Heat (1995).mkv", "heat.nfo": "Heat (1995).nfo"}
    a = {"folder": ("M:\\a", "M:\\Same (2000)")}
    b = {"folder": ("M:\\b", "M:\\same (2000)")}
    assert rn.batch_conflicts([a, None, b]) == {0: "same_folder", 2: "same_folder"}


def test_repath():
    row = {"subfolder_path": r"M:\Movies\Old", "subfolder": "Old", "nfo_path": r"M:\Movies\Old\a.nfo",
           "backdrop_paths": [r"M:\Movies\Old\extrafanart\f1.jpg"], "library_root": r"M:\Movies",
           "x": r"M:\Movies\Older\a.nfo", "n": 3}
    out = rn.repath(row, r"M:\Movies\Old", r"M:\Movies\New (2000)")
    assert out["subfolder_path"] == os.path.normpath(r"M:\Movies\New (2000)")
    assert out["nfo_path"] == os.path.join(os.path.normpath(r"M:\Movies\New (2000)"), "a.nfo")
    assert out["backdrop_paths"][0].endswith(os.path.join("New (2000)", "extrafanart", "f1.jpg"))
    assert out["library_root"] == r"M:\Movies" and out["x"] == r"M:\Movies\Older\a.nfo" and out["n"] == 3
