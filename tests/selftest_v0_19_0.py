# =============================================================================
# selftest_v0_19_0.py
# Metadata & MediaClinic — v0.19.0 self-test
# Author:  Luiz Junqueira & Claude AI
#
# Builds a synthetic movie library in a temp folder (NFO/XML/JPEG/MKV files
# generated on the fly), then exercises scanning, health rules, Quick Scan,
# FFprobe-flag handling, the export module, the results cache, the settings
# dialog and the main window — all against an ISOLATED config directory so
# your real settings.json is never touched.
#
# RUN (from the v.0.19.0 folder):
#   python selftest_v0_19_0.py
# Exit code 0 = all tests passed.  A real FFmpeg install is used when found
# (video/audio tests are skipped otherwise).  The main window stays hidden;
# a few dialogs may flash briefly.
# =============================================================================

import os, sys, io, csv, json, time, shutil, tempfile, threading, traceback
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_HERE = os.path.dirname(os.path.abspath(__file__))
# The main script is either next to this file (version folder) or one level up
# (GitHub layout: tests/selftest.py + mediaclinic.py in the repo root), and is
# named mediaclinic.py on GitHub or mediaclinic_v0_18_3.py locally.
_APP_DIR = _HERE
for _cand in (_HERE, os.path.dirname(_HERE)):
    if any(os.path.isfile(os.path.join(_cand, n)) for n in ("mediaclinic.py", "mediaclinic_v0_19_0.py")):
        _APP_DIR = _cand; break
os.chdir(_APP_DIR)
sys.path.insert(0, _APP_DIR)

_TMP = tempfile.mkdtemp(prefix="mediaclinic_selftest_")
os.environ["MEDIACLINIC_CONFIG_DIR"] = os.path.join(_TMP, "config")

# Pre-seed settings so the import does not depend on the machine (keys, lang)
os.makedirs(os.environ["MEDIACLINIC_CONFIG_DIR"], exist_ok=True)
_SEED = {
    "lang_ok_code": "PT", "use_ffprobe": True, "ffmpeg_path": r"C:\FFmpeg\bin",
    "poster_quality_level": "Full HD",          # legacy label → must migrate to 1080p
    "health_rules": {"folder_name_mismatch": False},
    "last_results": [{"subfolder": "OldRow", "subfolder_path": "X:/nowhere/OldRow"}],
}
with open(os.path.join(os.environ["MEDIACLINIC_CONFIG_DIR"], "settings.json"), "w", encoding="utf-8") as f:
    json.dump(_SEED, f)

try:
    import mediaclinic as mc                     # GitHub layout
except ImportError:
    import mediaclinic_v0_19_0 as mc             # local versioned copy
import export_list
import settings_controller as sc
from settings_model import DEFAULT_SETTINGS
import tkinter as tk
import tkinter.filedialog as fd

PASS, FAIL = [], []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (f"  -- {detail}" if (detail and not cond) else ""))

def section(t):
    print(f"\n== {t} ==")

# ── Synthetic library ─────────────────────────────────────────────────────────
LIB = os.path.join(_TMP, "Filmes")
os.makedirs(LIB)

def _jpeg(path, w, h, noisy=False):
    """noisy=True makes a large file (random pixels) so the KB-minimum rule passes."""
    from PIL import Image
    if noisy:
        img = Image.frombytes("RGB", (w, h), os.urandom(w * h * 3))
    else:
        img = Image.new("RGB", (w, h), (40, 60, 80))
    img.save(path, "JPEG", quality=90)

def _nfo(path, title, year="2001", original=None, genres=("Drama",), rating="7.3",
         votes="1200", imdb="tt0000001", tmdb="123", extra=""):
    """tmdb=None omits the tag; tmdb='' writes an empty tag."""
    orig = original or title
    g = "".join(f"\t<genre>{x}</genre>\n" for x in genres)
    t_tmdb = "" if tmdb is None else f"\t<tmdbid>{tmdb}</tmdbid>\n"
    txt = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n<movie>\n'
           f"\t<title>{title}</title>\n\t<originaltitle>{orig}</originaltitle>\n"
           f"\t<year>{year}</year>\n\t<rating>{rating}</rating>\n\t<votes>{votes}</votes>\n"
           f"{g}\t<id>{imdb}</id>\n\t<imdbid>{imdb}</imdbid>\n{t_tmdb}"
           f"\t<language>por</language>\n{extra}</movie>\n")
    io.open(path, "w", encoding="utf-8", newline="\n").write(txt)

def _xml(path, local, year="2001", original=None, genres=("Drama",), rating="7.3",
         votes="1200", imdb="tt0000001", tmdb="123", lang="Portuguese", extra=""):
    """tmdb=None omits the tag; tmdb='' writes an empty tag."""
    orig = original or local
    g = "".join(f"\t\t<Genre>{x}</Genre>\n" for x in genres)
    t_tmdb = "" if tmdb is None else f"\t<TMDB>{tmdb}</TMDB>\n"
    txt = (f'<?xml version="1.0" encoding="utf-8"?>\n<Item>\n'
           f"\t<LocalTitle>{local}</LocalTitle>\n\t<OriginalTitle>{orig}</OriginalTitle>\n"
           f"\t<ProductionYear>{year}</ProductionYear>\n\t<IMDBrating>{rating}</IMDBrating>\n"
           f"\t<Votes>{votes}</Votes>\n\t<IMDB>{imdb}</IMDB>\n{t_tmdb}"
           f"\t<Language>{lang}</Language>\n\t<Genres>\n{g}\t</Genres>\n{extra}</Item>\n")
    io.open(path, "w", encoding="utf-8", newline="\n").write(txt)

import itertools
_ID_SEQ = itertools.count(2)

def make_movie(name, nfo=True, xml=True, images=True, backdrops=6, video=True,
               poster_wh=(1000, 1500), fanart_wh=(1920, 1080), fanart_noisy=True, **kw):   # v0.19.0 sizes
    d = os.path.join(LIB, name); os.makedirs(d, exist_ok=True)
    # unique IDs per movie unless the caller sets them (duplicate detection would
    # otherwise flag the whole synthetic library)
    n = next(_ID_SEQ)
    for side in ("nfo_", "xml_"):
        if not any(k.startswith(side) and k[4:] in ("imdb",) for k in kw) and "imdb" not in kw:
            kw.setdefault(side + "imdb", f"tt{n:07d}")
        if not any(k.startswith(side) and k[4:] in ("tmdb",) for k in kw) and "tmdb" not in kw:
            kw.setdefault(side + "tmdb", str(100 + n))
    nfo_kw = {k[4:]: v for k, v in kw.items() if k.startswith("nfo_")}
    xml_kw = {k[4:]: v for k, v in kw.items() if k.startswith("xml_")}
    title = kw.get("title", name)
    if nfo: _nfo(os.path.join(d, name + ".nfo"), nfo_kw.pop("title", title), **nfo_kw)
    if xml: _xml(os.path.join(d, "movie.xml"), xml_kw.pop("local", title), **xml_kw)
    if images:
        _jpeg(os.path.join(d, "poster.jpg"), poster_wh[0], poster_wh[1], noisy=True)
        shutil.copy2(os.path.join(d, "poster.jpg"), os.path.join(d, "folder.jpg"))
        _jpeg(os.path.join(d, "fanart.jpg"), fanart_wh[0], fanart_wh[1], noisy=fanart_noisy)
    for i in range(backdrops):
        _jpeg(os.path.join(d, "backdrop.jpg" if i == 0 else f"backdrop{i}.jpg"), 1280, 720)
    if video and SAMPLE_VIDEO:
        shutil.copy2(SAMPLE_VIDEO, os.path.join(d, name + ".mkv"))
        io.open(os.path.join(d, name + ".pt.srt"), "w", encoding="utf-8").write("1\n00:00:01,000 --> 00:00:02,000\nOlá\n")
    return d

# tiny real video with an English audio track (needs ffmpeg)
SAMPLE_VIDEO = None
try:
    import subprocess
    ff = mc.FFMPEG_PATH
    if ff:
        SAMPLE_VIDEO = os.path.join(_TMP, "sample.mkv")
        # The non-ASCII title tag reproduces a real-world case: ffprobe prints UTF-8
        # JSON, which crashed the subprocess reader on cp1252 consoles before v0.18.3.
        r = subprocess.run([ff, "-y", "-loglevel", "error",
                            "-f", "lavfi", "-i", "testsrc=duration=3:size=1280x720:rate=10",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                            "-metadata:s:a:0", "language=eng",
                            "-metadata:s:a:0", "title=Português – Dolby Digital 5.1 \u0081",
                            "-metadata", "title=Amélie – Fabuleux destin", "-shortest", SAMPLE_VIDEO],
                           capture_output=True, encoding="utf-8", errors="replace", timeout=120,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0 or not os.path.isfile(SAMPLE_VIDEO):
            print("ffmpeg sample generation failed:", r.stderr[-300:]); SAMPLE_VIDEO = None
except Exception as e:
    print("no sample video:", e); SAMPLE_VIDEO = None
print("Sample video:", SAMPLE_VIDEO, "| ffprobe:", mc.FFPROBE_PATH)

# Movies
M_OK      = make_movie("Perfect Movie", nfo_imdb="tt0000001", xml_imdb="tt0000001", nfo_tmdb="123", xml_tmdb="123")  # all good
M_COMMA   = make_movie('Amor, Estranho Amor', title='Amor, Estranho "Amor"')     # export edge case (comma + quotes in title)
M_NONFO   = make_movie("No NFO Here", nfo=False)
M_BADXML  = make_movie("Broken XML", xml=False)
io.open(os.path.join(M_BADXML, "movie.xml"), "w", encoding="utf-8").write("<Item>\n<LocalTitle>Broken XML</LocalTitle>\n<Genres>\n</Item>\n")
M_CONFL   = make_movie("Conflicting IDs", nfo_imdb="tt0000005", xml_imdb="tt0000009")
M_EMPTY   = make_movie("Empty TMDB Tags", nfo_tmdb="", xml_tmdb="")               # <tmdbid/> and <TMDB></TMDB> both empty
M_HALFEMP = make_movie("Half Empty TMDB", nfo_tmdb="123", xml_tmdb="")            # NFO has it, XML tag empty
M_PARTIAL = make_movie("Partial TMDB", nfo_tmdb="123", xml_tmdb=None)             # XML has no TMDB tag at all
M_TITLE   = make_movie("Title Mismatch", nfo_title="Cidade de Deus", xml_local="City of God",
                       nfo_original="Cidade de Deus", xml_original="Cidade de Deus")
M_FOREIGN = make_movie("Foreign OK", nfo_title="Cidade de Deus", xml_local="Cidade de Deus",
                       nfo_original="City of God", xml_original="City of God")    # must NOT mismatch
M_RATING  = make_movie("Rating Conflict", nfo_rating="7.0", xml_rating="8.5", nfo_votes="10", xml_votes="20")
M_BADRATE = make_movie("Bad Rating", nfo_rating="n/a", xml_rating="n/a")
M_GENRE   = make_movie("Merged Genre", nfo_genres=("Family/Fantasy",), xml_genres=("Family/Fantasy",))
M_NOVID   = make_movie("No Video", video=False)
M_KODI    = make_movie("Kodi Ratings", nfo_rating="", nfo_votes="", xml_rating="8.1", xml_votes="500",
                       nfo_extra=("\t<ratings>\n\t\t<rating name=\"themoviedb\" max=\"10\"><value>7.0</value><votes>10</votes></rating>\n"
                                  "\t\t<rating name=\"imdb\" max=\"10\" default=\"true\"><value>8.1</value><votes>500</votes></rating>\n\t</ratings>\n"))
M_DUP     = make_movie("Perfect Movie (copy)", title="Perfect Movie", nfo_imdb="tt0000001", xml_imdb="tt0000001",
                       nfo_tmdb="123", xml_tmdb="123")                               # same IMDB id + title/year as Perfect Movie
M_LOWRES  = make_movie("Low Res Images", poster_wh=(793, 1190), fanart_wh=(1280, 720), fanart_noisy=False)  # v0.19.0: 720p + small KB, NOT corrupt
M_BADIMG  = make_movie("Bad Images")                                                   # v0.19.0: truncated / garbage / png-as-jpg
_src = open(os.path.join(M_LOWRES, "poster.jpg"), "rb").read()
open(os.path.join(M_BADIMG, "poster.jpg"), "wb").write(_src[: len(_src) // 2])        # truncated JPEG
open(os.path.join(M_BADIMG, "fanart.jpg"), "wb").write(b"not an image " * 20000)       # garbage bytes
from PIL import Image as _PILImg
_PILImg.new("RGB", (1000, 1500), (5, 5, 5)).save(os.path.join(M_BADIMG, "folder.png"), "PNG")
os.replace(os.path.join(M_BADIMG, "folder.png"), os.path.join(M_BADIMG, "folder.jpg"))  # PNG named .jpg
M_CUST1   = make_movie("Custom Genre A", nfo_genres=("Drama", "Weirdo"), xml_genres=("Drama", "Weirdo"))   # v0.19.0 item 2
M_CUST2   = make_movie("Custom Genre B", nfo_genres=("Comedy", "Oddball"), xml_genres=("Comedy", "Oddball"))
M_NOTM1   = make_movie("No TMDB A", nfo_tmdb=None, xml_tmdb=None)                        # TMDB tags absent
M_NOTM2   = make_movie("No TMDB B", nfo_tmdb=None, xml_tmdb=None)
# v0.19.0 item 4 — ID verification fixtures (canned TMDb answers in section 2c)
M_V_OK    = make_movie("Xuxa OK", title="A Princesa Xuxa e os Trapalh\u00f5es", nfo_year="1989", xml_year="1989", nfo_imdb="tt0121654", xml_imdb="tt0121654", nfo_tmdb="123571", xml_tmdb="123571")
M_V_OTHER = make_movie("Wrong Film", title="Totally Different Movie", nfo_year="1989", xml_year="1989", nfo_imdb="tt0121654", xml_imdb="tt0121654", nfo_tmdb="123571", xml_tmdb="123571")
M_V_DIFF  = make_movie("Mixed Ids", title="The Matrix", nfo_year="1999", xml_year="1999", nfo_imdb="tt0121654", xml_imdb="tt0121654", nfo_tmdb="603", xml_tmdb="603")
M_V_404   = make_movie("Dead Ids", title="Ghost", nfo_year="2000", xml_year="2000", nfo_imdb="tt9999999", xml_imdb="tt9999999", nfo_tmdb="404", xml_tmdb="404")
M_V_DIS   = make_movie("Disagree Ids", title="The Matrix", nfo_year="1999", xml_year="1999", nfo_imdb="tt0133093", xml_imdb="tt0133093", nfo_tmdb="603", xml_tmdb="123571")
M_V_YEAR  = make_movie("City of God (2002) [1080p]", title="Cidade de Deus", nfo_year="2002", xml_year="2002", nfo_imdb="tt0317248", xml_imdb="tt0317248", nfo_tmdb="598", xml_tmdb="598")
# v0.19.0 item 5 — Auto Repair fixtures
M_AR_IDS  = make_movie("Auto Ids", title="Auto Ids", nfo_year="2001", xml_year="2001", nfo_tmdb=None, xml_tmdb=None)   # missing TMDb → exact search hit
M_AR_ASK  = make_movie("Ask Ids", title="Ask Ids", nfo_year="2001", xml_year="2001", nfo_tmdb=None, xml_tmdb=None)      # missing TMDb → no exact → chooser
M_AR_CONF = make_movie("Auto Conflict", title="Auto Conflict", nfo_year="2001", xml_year="2001", nfo_imdb="tt0000777", xml_imdb="tt0000778", nfo_tmdb="777", xml_tmdb="777")
M_AR_BARE = make_movie("Bare Movie", title="Bare Movie", nfo_year="1995", xml_year="1995", nfo_tmdb="555", xml_tmdb="555", nfo_imdb="tt0000555", xml_imdb="tt0000555")
M_AR_TTL  = make_movie("Title Copy", title="Title Copy", nfo_year="2001", xml_year="2001")
M_AR_RAT  = make_movie("Auto Rating", title="Auto Rating", nfo_rating="5.0", xml_rating="6.0", nfo_votes="10", xml_votes="20")
M_AR_GEN  = make_movie("Auto Genre", title="Auto Genre", nfo_genres=("Family/Fantasy", "Sci-Fi"), xml_genres=("Family/Fantasy", "Sci-Fi"))
# bare movie: no year, no genres, no XML <Language>; title copy: empty NFO title
for _f, _pairs in ((os.path.join(M_AR_BARE, "Bare Movie.nfo"), (("\t<year>1995</year>\n", ""), ("\t<genre>Drama</genre>\n", ""))),
                   (os.path.join(M_AR_BARE, "movie.xml"), (("\t<ProductionYear>1995</ProductionYear>\n", ""), ("\t\t<Genre>Drama</Genre>\n", ""), ("\t<Language>Portuguese</Language>\n", ""))),
                   (os.path.join(M_AR_TTL, "Title Copy.nfo"), (("<title>Title Copy</title>", "<title></title>"),))):
    _t = io.open(_f, encoding="utf-8").read()
    for _a, _b in _pairs:
        assert _a in _t, (_f, _a)
        _t = _t.replace(_a, _b)
    io.open(_f, "w", encoding="utf-8", newline="\n").write(_t)
M_ENT     = make_movie("Entity Title", nfo_title="Tom &amp; Jerry \u2013 Movie", xml_local="Tom &amp; Jerry - Movie")  # entities + dash must compare equal

# ══════════════════════════════════════════════════════════════════════════════
section("1. settings load / migration")
check("legacy quality label migrated", mc.SETTINGS.get("poster_quality_level") == "1080p", mc.SETTINGS.get("poster_quality_level"))
check("health_rules deep-merged with new keys", mc.SETTINGS["health_rules"].get("imdb_id_partial") is True and mc.SETTINGS["health_rules"].get("folder_name_mismatch") is False)
check("defaults not shared with SETTINGS (deep copy)", mc.SETTINGS["health_rules"] is not DEFAULT_SETTINGS["health_rules"])
check("last_results migrated out of settings.json", mc.SETTINGS.get("last_results") == [] and os.path.isfile(sc.RESULTS_CACHE_PATH))
check("cache file holds migrated row", sc.load_results_cache() and sc.load_results_cache()[0]["subfolder"] == "OldRow")
_cfg = json.load(open(sc.CONFIG_PATH, encoding="utf-8"))
check("settings.json no longer contains rows", _cfg.get("last_results") == [])
check("APP_VERSION", mc.APP_VERSION == "0.19.0")

# ══════════════════════════════════════════════════════════════════════════════
section("2. scan_one_subfolder + health rules")
mc.clear_read_caches()
def scan(d, **kw):
    return mc.scan_one_subfolder(d, os.path.basename(d), **kw)

r = scan(M_OK)
check("perfect movie: no errors",  r["health_status"] != "error", r["health_reasons"])
check("perfect movie: title fields", r["nfo_title"] == "Perfect Movie" and r["xml_localtitle"] == "Perfect Movie")
check("perfect movie: scan_mtime recorded", isinstance(r.get("scan_mtime"), float) and r["scan_mtime"] > 0)
check("perfect movie: genres ok", r["genre_status"] == mc.STATUS_OK, r["genre_display"])
check("perfect movie: backdrops counted", r["backdrop_count"] == 6)
if SAMPLE_VIDEO:
    check("ffprobe ran + audio track ENG", r["ffprobe_ran"] and any(t["language"] == "ENG" for t in r["audio_tracks"]), r["audio_tracks"])
    _full = mc._get_ffprobe_full(r["video_path"], use_ffprobe=True)
    check("ffprobe JSON with non-ASCII tags decoded (UTF-8, no cp1252 crash)", bool(_full.get("streams")) and "Am" in (_full.get("format", {}).get("tags", {}).get("title", "")), str(_full)[:200])
    _dur, _est = mc.get_video_duration(r["video_path"])
    check("video duration read", _dur and 2.5 <= _dur <= 3.5 and not _est, (_dur, _est))
    check("video quality 720p", r["video_quality"] == "720p", r["video_quality"])
    check("external pt subtitle → lang_ok Y", r["lang_ok"] == "Y", r["lang_ok"])
    check("no 'required subtitle' warning (PT sub present)", not any("subtitle language" in x for x in r["health_reasons"]), r["health_reasons"])

r2 = scan(M_OK, use_ffprobe=False)
check("use_ffprobe=False: no audio tracks, ffprobe_ran False", r2["audio_tracks"] == [] and r2["ffprobe_ran"] is False)
check("use_ffprobe=False: still finds external subtitle", any(s["lang"] == "pt" for s in r2["subs_external"]))

r = scan(M_CONFL)
check("IMDB conflict → error with both ids", any("IMDB ID conflict" in x and "tt0000009" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_EMPTY)
check("both TMDB tags empty → 'Missing TMDb ID (tag present but empty)'", any("Missing TMDb ID (tag present but empty)" in x for x in r["health_reasons"]), r["health_reasons"])
check("empty tags never reported as conflict", not any("conflict" in x.lower() and "TMDb" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_HALFEMP)
check("NFO has TMDB, XML tag empty → 'empty in others' (not conflict)", any("TMDb ID present in some tags but empty in others" in x for x in r["health_reasons"]) and not any("conflict" in x and "TMDb" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_PARTIAL)
check("TMDB only in NFO → partial warning", any("TMDb ID present in one file only" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_TITLE)
check("title vs LocalTitle differ → mismatch warning", any(x.startswith("Title mismatch") for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_FOREIGN)
check("different original title only → NO mismatch", not any("Title mismatch" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_RATING)
check("rating values differ → conflict error", any("Rating conflict" in x for x in r["health_reasons"]), r["health_reasons"])
check("votes differ → votes conflict error", any("Votes conflict" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_BADRATE)
check("non-numeric rating → unreadable warning, not 'present in one file'", any("Rating tag unreadable" in x for x in r["health_reasons"]) and not any("one file only" in x and "Rating" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_NONFO)
check("missing NFO → error", r["health_status"] == "error" and "Missing NFO file" in r["health_reasons"])
r = scan(M_BADXML)
check("broken XML → corrupt error", any("Corrupt XML" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_GENRE)
check("merged genre → warning status", r["genre_status"] == mc.STATUS_WARN)
check("merged genre normalises to 2", mc.normalize_genre_list(["Family/Fantasy"])[0] == ["Family", "Fantasy"])
r = scan(M_NOVID)
check("no video → error", "Missing video file" in r["health_reasons"])
check("error row keeps its warnings too (errors + warnings)", r["health_status"] == "error" and r["health_errors"] and r["health_warnings"] and r["health_reasons"] == r["health_errors"] + r["health_warnings"], (r["health_errors"], r["health_warnings"]))
r = scan(M_KODI)
check("Kodi v17 <ratings> block → rating 8.1 / votes 500 from default=true element", r["rating_str"] == "8.1" and r["rating_votes"] == 500 and r["votes_int"] == 500, (r["rating_str"], r["rating_votes"], r["votes_int"], r["rating_status"]))
check("Kodi ratings: no conflict with XML 8.1", r["rating_status"] == mc.STATUS_OK and r["votes_status"] == mc.STATUS_OK, (r["rating_status"], r["votes_status"]))
r = scan(M_ENT)
check("title compare tolerant to &amp; and en-dash", not any("Title mismatch" in x for x in r["health_reasons"]), r["health_reasons"])
check("Kodi _replace_kodi_rating updates value/votes", "<value>9.9</value><votes>42</votes>" in mc._replace_kodi_rating('<ratings><rating name="imdb" default="true"><value>8.1</value><votes>500</votes></rating></ratings>', "9.9", "42"))
# duplicates + finalize
rows_d = [scan(M_OK, use_ffprobe=False), scan(M_DUP, use_ffprobe=False), scan(M_CONFL, use_ffprobe=False)]
mc.finalize_results(rows_d)
check("duplicate detection flags both copies", rows_d[0]["duplicate_of"] == ["Perfect Movie (copy)"] and rows_d[1]["duplicate_of"] == ["Perfect Movie"] and not rows_d[2]["duplicate_of"], [r["duplicate_of"] for r in rows_d])
check("duplicate health warning", any(x.startswith("Possible duplicate of") for x in rows_d[0]["health_reasons"]), rows_d[0]["health_reasons"])
check("duplicates report lists the group", "Same IMDB ID" in mc.format_duplicates_report(rows_d) and "Perfect Movie (copy)" in mc.format_duplicates_report(rows_d))
stats = mc.format_library_statistics(rows_d)
check("library statistics report renders", "HEALTH" in stats and "GENRES" in stats and "DECADES" in stats and "2000s" in stats, stats[:300])
# stale cached reasons (v0.18.2 style) are replaced on finalize
stale = dict(rows_d[2]); stale["health_reasons"] = ["Title mismatch between NFO and XML"]; stale["health_status"] = "warning"
stale.pop("health_errors", None); stale.pop("health_warnings", None)
mc.finalize_results([stale])
check("stale cached reason replaced by recompute", not any("Title mismatch" in x for x in stale["health_reasons"]), stale["health_reasons"])
lst = mc._FolderListing(M_OK)
check("folder listing: files found, newest mtime, case-insensitive", lst.has("POSTER.JPG") and lst.size("poster.jpg") > 0 and lst.newest_mtime() > 0 and lst.path_of("poster.jpg").endswith("poster.jpg"))
check("reason key collapses specifics", mc._reason_key("IMDB ID conflict between tags (tt1, tt2)") == "IMDB ID conflict between tags" and mc._reason_key("Title mismatch: NFO 'x' vs 'y'") == "Title mismatch")

# ── v0.19.0: image status split / corruption detection ───────────────────────
section("2b. image status (v0.19.0)")
r = scan(M_LOWRES, use_ffprobe=False)
check("v0.19 low-res images are NOT corrupt", not (r["poster_corrupt"] or r["folder_corrupt"] or r["fanart_corrupt"]) and r["health_status"] != "error", (r["poster_status"], r["fanart_desc"], r["health_errors"]))
check("v0.19 low-res → quality + size warnings", any("Poster/folder quality below minimum (720p < 1080p)" in x for x in r["health_warnings"]) and any("Fanart image file below minimum size" in x for x in r["health_warnings"]), r["health_warnings"])
check("v0.19 image facts stored on the row", r["poster_format"] == "JPEG" and r["poster_decode_ok"] is True and r["poster_flags"].get("low_res") is True and r["poster_dim"] == "793\u00d71190")
check("v0.19 desc text is per-reason and names the rule level", "below the minimum quality '1080p'" in r["poster_desc"] and "corrupt" not in r["poster_desc"].lower(), r["poster_desc"])
r = scan(M_BADIMG, use_ffprobe=False)
check("v0.19 truncated JPEG → corrupt poster error", r["poster_corrupt"] and r["poster_status"] == mc.STATUS_ERROR and "Corrupt poster image (cannot be decoded)" in r["health_errors"], (r["poster_desc"], r["health_errors"]))
check("v0.19 garbage .jpg → corrupt fanart error", r["fanart_corrupt"] and "Corrupt fanart image (cannot be decoded)" in r["health_errors"], r["fanart_desc"])
check("v0.19 PNG named folder.jpg decoded + mismatch warning", (not r["folder_corrupt"]) and r["folder_format"] == "PNG" and r["folder_dim"] == "1000\u00d71500" and r["folder_quality"] == "1080p" and any("folder.jpg is a PNG file (extension mismatch)" in x for x in r["health_warnings"]), (r["folder_format"], r["folder_dim"], r["health_warnings"]))
check("v0.19 probe_image: signature not extension", mc.detect_image_format(os.path.join(M_BADIMG, "folder.jpg")) == "PNG" and mc.probe_image(os.path.join(M_BADIMG, "fanart.jpg"))["format"] is None)
_pad = os.path.join(_TMP, "pad.jpg"); open(_pad, "wb").write(_src + b"\x00" * 32)
check("v0.19 trailing padding after EOI is not corrupt", mc.probe_image(_pad)["decode_ok"] is True)
check("v0.19 is_valid_jpeg rejects truncated file", mc.is_valid_jpeg(os.path.join(M_BADIMG, "poster.jpg")) is False and mc.is_valid_jpeg(_pad) is True)
# one authoritative minimum: Health Rules; 720p → no quality reason and no "below ... 1080p" anywhere
_hr = mc.SETTINGS["health_rules"]
_hr["poster_folder_quality_level"] = "720p"; _hr["fanart_quality_level_minimum"] = "720p"
_old_fkb = mc.SETTINGS["min_fanart_kb"]; mc.SETTINGS["min_fanart_kb"] = 0
mc.SETTINGS["poster_quality_level"] = "1080p"     # stale mirror must NOT matter
rows_q = [scan(M_LOWRES, use_ffprobe=False)]
mc.finalize_results(rows_q)
_texts = rows_q[0]["health_reasons"] + [rows_q[0]["poster_desc"], rows_q[0]["fanart_desc"],
          mc.format_health_report(rows_q), mc.format_improvements_report(mc.run_improvements(rows_q)),
          mc.format_library_statistics(rows_q)]
check("v0.19 minimum 720p: no quality reason for 720p images", not any("quality below minimum" in x for x in rows_q[0]["health_reasons"]), rows_q[0]["health_reasons"])
check("v0.19 minimum 720p: no 'below ... 1080p' text anywhere", not any(("1080p" in t and "below" in t) for t in _texts))
check("v0.19 _min_quality_level reads Health Rules only", mc._min_quality_level("poster") == "720p" and mc._min_quality_level("fanart") == "720p")
_hr["poster_folder_quality_level"] = "1080p"; _hr["fanart_quality_level_minimum"] = "1080p"; mc.SETTINGS["min_fanart_kb"] = _old_fkb
check("v0.19 sync_quality_mirrors rewrites Image Sizes keys", sc.sync_quality_mirrors(mc.SETTINGS) is False and mc.SETTINGS["poster_quality_level"] == "1080p" and mc.SETTINGS["folder_quality_level"] == "1080p")
# stale v0.18.4 cache row: status ✕ from a resolution problem → re-derived on load
_stale = {"subfolder": "Old", "subfolder_path": "X:/old", "poster_exists": True, "poster_path": "X:/old/poster.jpg",
          "poster_bytes": 113000, "poster_dim": "793\u00d71190", "poster_corrupt": True, "poster_status": mc.STATUS_ERROR,
          "poster_desc": "Resolution 793x1190 is below minimum quality '1080p' (1000x1500)", "poster_quality": "720p",
          "video_count": 1, "nfo_exists": True, "xml_exists": True, "health_status": "error", "health_reasons": ["Corrupt poster image"]}
_rows_s = mc._results_from_json([_stale]); mc.finalize_results(_rows_s)
check("v0.19 stale cached 'corrupt' re-derived on load", (not _rows_s[0]["poster_corrupt"]) and _rows_s[0]["poster_status"] == mc.STATUS_WARN and not any("Corrupt" in x for x in _rows_s[0]["health_reasons"]) and any("quality below minimum" in x for x in _rows_s[0]["health_reasons"]), (_rows_s[0]["poster_status"], _rows_s[0]["health_reasons"]))
_stale2 = dict(_stale); _stale2["poster_dim"] = None; _stale2["poster_quality"] = "\u2014"
_rows_s2 = mc._results_from_json([_stale2]); mc.finalize_results(_rows_s2)
check("v0.19 stale cached row without dimensions stays corrupt", _rows_s2[0]["poster_corrupt"] and "Corrupt poster image (cannot be decoded)" in _rows_s2[0]["health_errors"])
mc.SETTINGS["health_rules"]["image_format_mismatch"] = False
_rb = [scan(M_BADIMG, use_ffprobe=False)]; mc.finalize_results(_rb)
check("v0.19 image_format_mismatch rule OFF removes the warning", not any("extension mismatch" in x for x in _rb[0]["health_reasons"]))
mc.SETTINGS["health_rules"]["image_format_mismatch"] = True

# ── v0.19.0 item 4: verify IMDb/TMDb IDs (canned TMDb) ───────────────────────
section("2c. verify IMDb/TMDb IDs (v0.19.0)")
import urllib.error as _ue, re as _re
_TMDB = {
    "123571": {"id": 123571, "title": "Princess Xuxa and the Trapalhoes", "original_title": "A Princesa Xuxa e os Trapalh\u00f5es",
               "release_date": "1989-06-22", "external_ids": {"imdb_id": "tt0121654"},
               "translations": {"translations": [{"iso_639_1": "pt", "data": {"title": "A Princesa Xuxa e os Trapalh\u00f5es"}}]},
               "alternative_titles": {"titles": [{"title": "Xuxa Princess"}]}},
    "603":    {"id": 603, "title": "The Matrix", "original_title": "The Matrix", "release_date": "1999-03-30",
               "external_ids": {"imdb_id": "tt0133093"}, "translations": {"translations": []}, "alternative_titles": {"titles": []}},
    "598":    {"id": 598, "title": "City of God", "original_title": "Cidade de Deus", "release_date": "2003-01-10",
               "external_ids": {"imdb_id": "tt0317248"}, "translations": {"translations": []}, "alternative_titles": {"titles": []}},
}
_FIND = {"tt0121654": [{"id": 123571, "title": "Princess Xuxa and the Trapalhoes", "release_date": "1989-06-22"}],
         "tt0133093": [{"id": 603, "title": "The Matrix", "release_date": "1999-03-30"}],
         "tt0317248": [{"id": 598, "title": "City of God", "release_date": "2003-01-10"}],
         "tt9999999": []}
_fetch_log = []
def _fake_tmdb(url, timeout=15):
    _fetch_log.append(url)
    m = _re.search(r"/movie/(\d+)\?", url)
    if m:
        if m.group(1) not in _TMDB:
            raise _ue.HTTPError(url, 404, "not found", {}, io.BytesIO(b'{"status_message":"gone"}'))
        return dict(_TMDB[m.group(1)])
    m = _re.search(r"/find/(tt\d+)\?", url)
    if m:
        return {"movie_results": list(_FIND.get(m.group(1), []))}
    raise AssertionError("unexpected url " + url)
def _verify(d, **kw):
    r = scan(d, use_ffprobe=False)
    r.update(kw)
    return mc.verify_movie_ids(r, "k", "pt-BR", fetch=_fake_tmdb)
v = _verify(M_V_OK)
check("verify: Portuguese title matched through translations → OK", v["result"] == mc.ID_OK and v["tmdb_title"] == "Princess Xuxa and the Trapalhoes" and v["tmdb_year"] == "1989", v)
check("verify: requests use translations + alternative_titles + external_ids, and /find", any("append_to_response=external_ids,alternative_titles,translations" in u for u in _fetch_log) and any("/find/tt0121654" in u and "external_source=imdb_id" in u for u in _fetch_log))
v = _verify(M_V_OTHER)
check("verify: right ids, wrong local title → ID belongs to another film", v["result"] == mc.ID_OTHER and "similarity" in v["detail"], v)
v = _verify(M_V_DIFF)
check("verify: IMDb → 123571 but TMDb 603 → different films", v["result"] == mc.ID_DIFFERENT and "603" in v["detail"] and "123571" in v["detail"], v)
v = _verify(M_V_404)
check("verify: unknown ids → ID does not exist (both named)", v["result"] == mc.ID_NOT_FOUND and "TMDb 404" in v["detail"] and "IMDb tt9999999" in v["detail"], v)
v = _verify(M_V_DIS)
check("verify: NFO and XML disagree (no network call needed)", v["result"] == mc.ID_DISAGREE and "603" in v["detail"], v)
_n0 = len(_fetch_log); _verify(M_V_DIS)
check("verify: disagree short-circuits before any request", len(_fetch_log) == _n0)
v = mc.verify_movie_ids({"subfolder": "Nothing (2001)", "subfolder_path": "X:/n", "nfo_exists": False, "xml_exists": False}, "k", "pt-BR", fetch=_fake_tmdb)
check("verify: no ids → no IDs", v["result"] == mc.ID_NONE)
v = _verify(M_V_YEAR)
check("verify: year 2002 vs TMDb 2003 accepted (±1), original title matched", v["result"] == mc.ID_OK, v)
v = _verify(M_V_YEAR, movie_year_raw="2000", movie_year="2000")
check("verify: year 2000 vs 2003 → another film", v["result"] == mc.ID_OTHER and "year 2000 vs TMDb 2003" in v["detail"], v)
r_f = scan(M_V_DIFF, use_ffprobe=False); r_f["movie_title_raw"] = []; r_f["nfo_title"] = ""; r_f["xml_localtitle"] = ""; r_f["movie_name"] = ""
r_f["subfolder"] = "The Matrix (1999) [1080p] [Action]"
r_f["nfo_exists"] = False; r_f["xml_exists"] = True
check("verify: folder name (year/tags stripped) counts as a local title", "The Matrix" in mc._local_titles_for(r_f) and "[1080p]" not in " ".join(mc._local_titles_for(r_f)), mc._local_titles_for(r_f))
check("verify: accent-insensitive difflib match", mc._titles_match(["A Princesa e o Robo"], ["A Princesa e o Rob\u00f4"])[0] is True and mc._titles_match(["Completely Else"], ["A Princesa e o Rob\u00f4"])[0] is False)
check("verify: language mapping PT → pt-BR", mc._tmdb_lang_for("PT") == "pt-BR" and mc._tmdb_lang_for("EN") == "en-US")
# network error propagates (the worker turns it into a message)
def _down(url, timeout=15): raise _ue.URLError("getaddrinfo failed")
try:
    mc.verify_movie_ids(scan(M_V_OK, use_ffprobe=False), "k", "pt-BR", fetch=_down); _raised = False
except Exception as ex:
    _raised = "resolve" in mc._tmdb_error_message(ex) or "Network" in mc._tmdb_error_message(ex)
check("verify: network error propagates with a clear message", _raised is True)
# rate limiter: 41st request within 10 s must wait
_orig_fetch_json, _orig_sleep = mc._tmdb_fetch_json, mc.time.sleep
_sleeps = []
mc._tmdb_fetch_json = lambda url, timeout=15: {}
mc.time.sleep = lambda x: _sleeps.append(x)
try:
    mc._TMDB_RATE_TIMES.clear()
    for _i in range(41):
        mc._tmdb_rate_limited_fetch("u")
    check("verify: rate limiter sleeps on the 41st request within 10 s", len(_sleeps) >= 1 and all(0 < x <= 10.1 for x in _sleeps), _sleeps[:3])
finally:
    mc._tmdb_fetch_json, mc.time.sleep = _orig_fetch_json, _orig_sleep
    mc._TMDB_RATE_TIMES.clear()
_rep = mc.format_id_verify_report([dict(scan(M_V_OK, use_ffprobe=False), id_check=_verify(M_V_OK)), dict(scan(M_V_DIFF, use_ffprobe=False), id_check=_verify(M_V_DIFF))])
check("verify: text report lists counts and details", "1  OK" in _rep and mc.ID_DIFFERENT in _rep and "tt0121654" in _rep, _rep[:300])

# ── v0.19.0 item 5: atomic writes, root-close insertion, plan ─────────────────
section("2d. auto repair helpers (v0.19.0)")
_aw = os.path.join(_TMP, "atomic.txt")
mc._atomic_write_text(_aw, "first")
_orig_replace = os.replace
def _boom(a, b): raise OSError("disk full")
os.replace = _boom
try:
    try:
        mc._atomic_write_text(_aw, "second"); _ok = False
    except OSError:
        _ok = True
finally:
    os.replace = _orig_replace
check("atomic write: failed replace leaves the original intact and no temp file", _ok and io.open(_aw, encoding="utf-8").read() == "first" and not os.path.exists(_aw + ".mctmp"))
mc._atomic_write_text(_aw, "second")
check("atomic write: normal write replaces the content", io.open(_aw, encoding="utf-8").read() == "second")
_tx = os.path.join(_TMP, "title_root.xml")
io.open(_tx, "w", encoding="utf-8", newline="\n").write('<?xml version="1.0" encoding="utf-8"?>\n<Title>\n\t<LocalTitle>Root Test</LocalTitle>\n\t<IMDB>tt0000001</IMDB>\n</Title>\n')
_tn = os.path.join(_TMP, "title_root.nfo")
io.open(_tn, "w", encoding="utf-8", newline="\n").write('<movie>\n\t<title>Root Test</title>\n</movie>\n')
ok, err = mc._write_source_id_to_files(_tn, _tx, "TMDB", "4242")
import xml.etree.ElementTree as _ET
_root = _ET.parse(_tx).getroot()
check("<Title>-root movie.xml stays valid after inserting missing ID tags (v0.18 bug)", ok and _root.tag == "Title" and _root.findtext("TMDB") == "4242" and _root.findtext("TMDbId") == "4242" and _root.findtext("TMDB_ID") == "4242", (ok, err, io.open(_tx, encoding="utf-8").read()))
_nroot = _ET.parse(_tn).getroot()
check("NFO without the tag gets <tmdbid> and <id moviedb> inside <movie>", _nroot.findtext("tmdbid") == "4242" and any(e.get("moviedb") == "tmdb" for e in _nroot.findall("id")))
ok, err = mc._write_tag_in_files(_tn, _tx, "year", "ProductionYear", "1999")
check("_write_tag_in_files inserts missing tags inside the root", ok and _ET.parse(_tn).getroot().findtext("year") == "1999" and _ET.parse(_tx).getroot().findtext("ProductionYear") == "1999", err)
ok, err = mc._write_tag_in_files(_tn, None, "year", None, "2000")
check("_write_tag_in_files replaces an existing tag", ok and _ET.parse(_tn).getroot().findtext("year") == "2000" and io.open(_tn, encoding="utf-8").read().count("<year>") == 1)
# TMDb search (canned)
_SEARCH = {
    "Auto Ids":      [{"id": 9001, "title": "Auto Ids", "original_title": "Auto Ids", "release_date": "2001-05-05", "poster_path": ""}],
    "Ask Ids":       [{"id": 9002, "title": "Ask Ids Reloaded", "original_title": "Ask Ids Reloaded", "release_date": "2001-05-05", "poster_path": ""},
                      {"id": 9003, "title": "Ask Ids", "original_title": "Ask Ids", "release_date": "1988-01-01", "poster_path": ""}],
    "Auto Conflict": [{"id": 777, "title": "Auto Conflict", "original_title": "Auto Conflict", "release_date": "2001-01-01", "poster_path": ""}],
}
_EXT = {"9001": "tt0009001", "9002": "tt0009002", "9003": "tt0009003", "777": "tt0000777", "555": "tt0000555"}
_FULL = {"777": {"id": 777, "title": "Auto Conflict", "original_title": "Auto Conflict", "release_date": "2001-01-01",
                 "external_ids": {"imdb_id": "tt0000777"}, "translations": {"translations": []}, "alternative_titles": {"titles": []},
                 "genres": [{"name": "Drama"}]},
         "9002": {"id": 9002, "title": "Ask Ids Reloaded", "original_title": "Ask Ids Reloaded", "release_date": "2001-05-05",
                  "external_ids": {"imdb_id": "tt0009002"}, "translations": {"translations": []}, "alternative_titles": {"titles": []}, "genres": []},
         "555": {"id": 555, "title": "Bare Movie", "original_title": "Bare Movie", "release_date": "1995-03-03",
                 "external_ids": {"imdb_id": "tt0000555"}, "translations": {"translations": []}, "alternative_titles": {"titles": []},
                 "genres": [{"name": "Science Fiction"}, {"name": "Adventure"}]}}
_FIND5 = {"tt0000777": [{"id": 777, "title": "Auto Conflict", "release_date": "2001-01-01"}],
          "tt0000778": [{"id": 31337, "title": "Something Else", "release_date": "1975-01-01"}],
          "tt0000555": [{"id": 555, "title": "Bare Movie", "release_date": "1995-03-03"}],
          "tt0009002": [{"id": 9002, "title": "Ask Ids Reloaded", "release_date": "2001-05-05"}]}
import urllib.parse as _up
def _fake_tmdb5(url, timeout=15):
    _fetch_log.append(url)
    if "/search/movie" in url:
        q = _up.unquote(_re.search(r"query=([^&]+)", url).group(1))
        yr = _re.search(r"&year=(\d{4})", url)
        res = list(_SEARCH.get(q, []))
        if yr:
            res = [r for r in res if r["release_date"][:4] == yr.group(1)]
        return {"results": res}
    m = _re.search(r"/movie/(\d+)/external_ids", url)
    if m:
        return {"imdb_id": _EXT.get(m.group(1), "")}
    m = _re.search(r"/movie/(\d+)\?", url)
    if m:
        if m.group(1) not in _FULL:
            raise _ue.HTTPError(url, 404, "nf", {}, io.BytesIO(b"{}"))
        return dict(_FULL[m.group(1)])
    m = _re.search(r"/find/(tt\d+)\?", url)
    if m:
        return {"movie_results": list(_FIND5.get(m.group(1), []))}
    raise AssertionError("unexpected " + url)
_c = mc._tmdb_search_movie("Auto Ids", "2001", "k", "en-US", fetch=_fake_tmdb5)
check("tmdb search: exact title+year flagged, imdb filled from external_ids", len(_c) == 1 and _c[0]["exact"] is True and _c[0]["imdb_id"] == "tt0009001" and _c[0]["tmdb_id"] == "9001", _c)
_c = mc._tmdb_search_movie("Ask Ids", "2001", "k", "en-US", fetch=_fake_tmdb5)
check("tmdb search: no exact match (title differs / year differs)", _c and not any(x["exact"] for x in _c), _c)
_c = mc._tmdb_search_movie("Ask Ids", "1977", "k", "en-US", fetch=_fake_tmdb5)
check("tmdb search: retried without the year when the year finds nothing", len(_c) == 2, _c)
# plan
mc.clear_read_caches()
def _codes(d, **kw):
    r = scan(d, use_ffprobe=False); r.update(kw)
    return [c for c, _l in mc._auto_repair_plan(r, mc.SETTINGS)]
check("plan: missing TMDb → ids_search", _codes(M_AR_IDS) == ["ids_search"], _codes(M_AR_IDS))
check("plan: conflicting IMDb → ids_resolve (no partial)", _codes(M_AR_CONF) == ["ids_resolve"], _codes(M_AR_CONF))
check("plan: ID in one file only → ids_partial", "ids_partial" in _codes(M_PARTIAL), _codes(M_PARTIAL))
check("plan: rating/votes conflict → ratings", _codes(M_AR_RAT) == ["ratings"], _codes(M_AR_RAT))
check("plan: non-standard genres → genres", _codes(M_AR_GEN) == ["genres"], _codes(M_AR_GEN))
check("plan: bare movie → genres from TMDb, year from TMDb, language", _codes(M_AR_BARE) == ["genres_tmdb", "year_tmdb", "language"], _codes(M_AR_BARE))
check("plan: empty NFO title with XML title → title_copy", "title_copy" in _codes(M_AR_TTL), _codes(M_AR_TTL))
check("plan: failed verification → ids_search", _codes(M_OK, id_check={"result": mc.ID_OTHER}) == ["ids_search"])
check("plan: perfect movie → nothing", _codes(M_OK) == [], _codes(M_OK))
check("plan: images never planned", not any(c in ("poster", "fanart", "folder", "backdrops") for c in _codes(M_LOWRES) + _codes(M_BADIMG)))
_rules_off = dict(mc.SETTINGS["health_rules"]); _rules_off.update({"genre_warning": False, "rating_conflict": False, "votes_conflict": False})
check("plan: disabled rules are not repaired", mc._auto_repair_plan(scan(M_AR_GEN, use_ffprobe=False), mc.SETTINGS, _rules_off) == [] and mc._auto_repair_plan(scan(M_AR_RAT, use_ffprobe=False), mc.SETTINGS, _rules_off) == [])
_sum = mc.format_auto_repair_summary([{"name": "A", "planned": ["x"], "fixed": ["did x"], "skipped": [], "failed": [], "failing": ["still y"]},
                                      {"name": "B", "planned": [], "fixed": [], "skipped": ["nothing"], "failed": [], "failing": []}])
check("summary: fixed / skipped / still failing rendered", "A   [FIXED / STILL FAILING]" in _sum and "did x" in _sum and "still y" in _sum and "B   [SKIPPED]" in _sum, _sum)
check("summary: dry run header", "DRY RUN" in mc.format_auto_repair_summary([{"name": "A", "planned": ["x"]}], dry_run=True))

# ── v0.19.0 item 7: library_folders migration ────────────────────────────────
section("2e. library migration (v0.19.0)")
_cfg_tmp = os.path.join(_TMP, "migr_settings.json")
_orig_cfg = sc.CONFIG_PATH
try:
    sc.CONFIG_PATH = _cfg_tmp
    json.dump({"last_folder": r"D:\Movies", "hidden_columns": ["year"]}, open(_cfg_tmp, "w", encoding="utf-8"))
    _m = sc.load_settings()
    check("migration: last_folder becomes the first library, last_folder kept", _m["library_folders"] == [r"D:\Movies"] and _m["last_folder"] == r"D:\Movies", _m.get("library_folders"))
    check("migration: Library column hidden on the first v0.19 run", _m["hidden_columns"] == ["year", "library"], _m["hidden_columns"])
    json.dump({"last_folder": r"D:\Movies", "library_folders": [r"D:\Movies", r"E:\More"], "hidden_columns": []}, open(_cfg_tmp, "w", encoding="utf-8"))
    _m = sc.load_settings()
    check("migration runs only once (existing library_folders untouched)", _m["library_folders"] == [r"D:\Movies", r"E:\More"] and _m["hidden_columns"] == [], (_m["library_folders"], _m["hidden_columns"]))
    json.dump({}, open(_cfg_tmp, "w", encoding="utf-8"))
    check("migration: no last_folder → empty library list", sc.load_settings()["library_folders"] == [])
finally:
    sc.CONFIG_PATH = _orig_cfg
check("rows carry library_root", scan(M_OK, use_ffprobe=False)["library_root"] == LIB)
check("cached rows without library_root get it from the path", mc._results_from_json([{"subfolder": "x", "subfolder_path": os.path.join(LIB, "x")}])[0]["library_root"] == LIB)
check("export field Library", export_list.build_table([scan(M_OK, use_ffprobe=False)], ["library"])[1][0] == [LIB])

# cache behaviour: edit NFO → new content picked up without clearing cache
p = os.path.join(M_OK, "Perfect Movie.nfo")
t0 = mc._read_text(p)
time.sleep(0.05)
io.open(p, "w", encoding="utf-8").write(t0.replace("<year>2001</year>", "<year>1999</year>"))
check("read cache invalidates on file change", mc.get_movie_year_display(p, None) == "1999")
io.open(p, "w", encoding="utf-8").write(t0)

# ══════════════════════════════════════════════════════════════════════════════
section("3. export_list")
mc.clear_read_caches()
rows = [scan(d, use_ffprobe=False) for d in (M_OK, M_COMMA, M_NONFO)]
out = os.path.join(_TMP, "out")
os.makedirs(out)
for fmt in ("csv_comma", "csv_semicolon", "tsv", "txt", "xlsx"):
    path = os.path.join(out, "list" + export_list.default_extension(fmt))
    try:
        n = export_list.export_rows(rows, export_list.PRESETS["Standard"], fmt, path)
        check(f"export {fmt}: 3 rows written", n == 3 and os.path.getsize(path) > 0)
    except Exception as e:
        check(f"export {fmt}", False, repr(e)); continue
    if fmt.startswith("csv") or fmt == "tsv":
        delim = {"csv_comma": ",", "csv_semicolon": ";", "tsv": "\t"}[fmt]
        enc = "utf-8-sig" if fmt != "tsv" else "utf-8"
        with open(path, newline="", encoding=enc) as f:
            data = list(csv.reader(f, delimiter=delim))
        names = [row[0] for row in data[1:]]
        check(f"export {fmt}: comma/quote name intact", 'Amor, Estranho "Amor"' in names, names)
        check(f"export {fmt}: header + 3 rows, equal column count", len(data) == 4 and len({len(r) for r in data}) == 1)
    elif fmt == "txt":
        lines = io.open(path, encoding="utf-8").read().splitlines()
        check("export txt: 'Name (Year)' lines", any(l.startswith("Perfect Movie (2001)") for l in lines), lines)
    elif fmt == "xlsx":
        import openpyxl
        ws = openpyxl.load_workbook(path).active
        vals = [[c.value for c in r] for r in ws.iter_rows()]
        check("export xlsx: header + 3 rows", len(vals) == 4 and vals[0][0] == "Movie Name")
        check("export xlsx: year numeric, comma name intact", vals[1][1] == 2001 and any(v[0] == 'Amor, Estranho "Amor"' for v in vals[1:]))
hdr, data = export_list.build_table(rows, export_list.ALL_FIELD_KEYS)
check("build_table all fields", len(hdr) == len(export_list.ALL_FIELD_KEYS) == len(data[0]))
hdr, data = export_list.build_table(rows, export_list.PRESETS["Identify"])
check("Identify preset: links + outline", hdr == ["Movie Name", "Year", "IMDB Link", "TMDB Link", "Outline"] and data[0][2] == "https://www.imdb.com/title/tt0000001/" and data[0][3] == "https://www.themoviedb.org/movie/123", data[0])
_pf = os.path.join(M_OK, "Perfect Movie.nfo"); _t = io.open(_pf, encoding="utf-8").read()
time.sleep(0.05)
io.open(_pf, "w", encoding="utf-8").write(_t.replace("</movie>", "\t<outline>Short &amp; sweet</outline>\n\t<plot>Line one\n   line two</plot>\n</movie>"))
hdr, data = export_list.build_table([scan(M_OK, use_ffprobe=False)], ["outline", "plot"])
check("outline/plot read from NFO, entities decoded, whitespace collapsed", data[0] == ["Short & sweet", "Line one line two"], data[0])
io.open(_pf, "w", encoding="utf-8").write(_t)
check("suggested filename", export_list.suggested_filename("csv_semicolon", "Filmes") == "movie_list_Filmes.csv")

# ══════════════════════════════════════════════════════════════════════════════
section("4. TMDB download retry order")
import urllib.error, urllib.request
calls = {"n": 0}
_real_open = urllib.request.urlopen
_real_sleep = time.sleep
class _Resp:
    def __init__(s, data): s.d = data
    def read(s): return s.d
    def __enter__(s): return s
    def __exit__(s, *a): return False
def _fake_open(req, timeout=None):
    calls["n"] += 1
    if calls["n"] < 3:
        raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, io.BytesIO(b"{}"))
    return _Resp(b"\xff\xd8JPEGDATA")
urllib.request.urlopen = _fake_open
time.sleep = lambda s: None
try:
    dest = os.path.join(_TMP, "dl.jpg")
    ok, err = mc._tmdb_download_image("https://image.tmdb.org/t/p/original/x.jpg", dest)
    check("503 is retried and eventually succeeds", ok and calls["n"] == 3, f"ok={ok} err={err} calls={calls['n']}")
    calls["n"] = 0
    def _fake_404(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, io.BytesIO(b'{"status_message":"gone"}'))
    urllib.request.urlopen = _fake_404
    ok, err = mc._tmdb_download_image("https://image.tmdb.org/t/p/original/x.jpg", dest)
    check("404 not retried, readable message", (not ok) and calls["n"] == 1 and "404" in err, err)
finally:
    urllib.request.urlopen = _real_open
    time.sleep = _real_sleep

# ══════════════════════════════════════════════════════════════════════════════
section("5. App window: full scan, no-ffprobe scan, quick scan, export dialog, settings")
# The app's worker threads call widget.after(); Python's tkinter requires the
# main thread to be inside mainloop() for that, so the UI tests run on a
# helper thread while the main thread runs mainloop().  Message boxes are
# replaced by recorders so nothing blocks.
_boxes = []
_orig_boxes = (mc.messagebox.showinfo, mc.messagebox.showwarning, mc.messagebox.showerror, mc.messagebox.askyesno)
mc.messagebox.showinfo    = lambda *a, **k: _boxes.append(("info", a[:2]))
mc.messagebox.showwarning = lambda *a, **k: _boxes.append(("warning", a[:2]))
mc.messagebox.showerror   = lambda *a, **k: _boxes.append(("error", a[:2]))
mc.messagebox.askyesno    = lambda *a, **k: False
_orig_ask = fd.asksaveasfilename

app = mc.App()
app.withdraw()
n_movies = len([d for d in os.listdir(LIB) if os.path.isdir(os.path.join(LIB, d))])
shared = {}

def wait_for(cond, timeout=240):
    t0 = time.time()
    while not cond() and time.time() - t0 < timeout:
        time.sleep(0.05)
    return cond()

def ui_tests():
    try:
        app._folder = LIB; app.folder_var.set(LIB)
        app._start_scan(LIB, use_ff=True)
        check("full scan finished", wait_for(lambda: not app._scanning), "timeout")
        check(f"all {n_movies} movies scanned", len(app._results) == n_movies, len(app._results))
        check("results cache written", os.path.isfile(sc.RESULTS_CACHE_PATH) and len(sc.load_results_cache()) == n_movies)
        check("settings.json stays small", os.path.getsize(sc.CONFIG_PATH) < 20000, os.path.getsize(sc.CONFIG_PATH))
        by = {r["subfolder"]: r for r in app._results}
        if SAMPLE_VIDEO:
            check("full scan: audio tracks found", by["Perfect Movie"]["audio_tracks"] and by["Perfect Movie"]["ffprobe_ran"])
            app._start_scan(LIB.replace("\\", "/"), use_ff=False)   # other slash style → keys must still match
            check("no-ffprobe scan finished", wait_for(lambda: not app._scanning))
            by = {r["subfolder"]: r for r in app._results}
            check("no-ffprobe scan keeps audio tracks", by["Perfect Movie"]["audio_tracks"] != [], by["Perfect Movie"]["audio_tracks"])
            check("no-ffprobe scan keeps video quality + lang_ok", by["Perfect Movie"]["video_quality"] == "720p" and by["Perfect Movie"]["lang_ok"] == "Y", (by["Perfect Movie"]["video_quality"], by["Perfect Movie"]["lang_ok"]))
            check("no-ffprobe scan keeps ffprobe_ran", by["Perfect Movie"]["ffprobe_ran"] is True)

        errs = []
        for iid in app.tree.get_children():
            for ci in range(len(mc.COLUMN_MODEL)):
                try: app._tooltip(iid, ci)
                except Exception as e: errs.append((ci, repr(e)))
        check("tooltips for all cells render", not errs, errs[:3])
        check("row values length matches column model", all(len(app._rv(r)) == len(mc.COLUMN_MODEL) for r in app._results))

        app._filter_var.set("conflict"); app._refresh_table()
        check("filter narrows the view", 0 < len(app.tree.get_children()) < n_movies, len(app.tree.get_children()))
        app._filter_var.set(""); app._refresh_table()

        # Quick scan — modify one NFO, add one folder, remove one folder
        pm_nfo = os.path.join(M_OK, "Perfect Movie.nfo")
        time.sleep(1.1)
        txt = io.open(pm_nfo, encoding="utf-8").read().replace("<rating>7.3</rating>", "<rating>8.8</rating>")
        io.open(pm_nfo, "w", encoding="utf-8").write(txt)
        make_movie("Brand New Movie", video=False)
        shutil.rmtree(M_NOVID)
        app._start_quick_scan(LIB)
        check("quick scan finished", wait_for(lambda: not app._scanning))
        by = {r["subfolder"]: r for r in app._results}
        check("quick scan: modified movie re-read (rating 8.8)", by.get("Perfect Movie", {}).get("rating_str") == "8.8", by.get("Perfect Movie", {}).get("rating_str"))
        check("quick scan: new folder added", "Brand New Movie" in by)
        check("quick scan: removed folder dropped", "No Video" not in by)
        check("quick scan: unchanged movie not rescanned (object identity kept)", by["Conflicting IDs"] is shared.get("confl_row", by["Conflicting IDs"]))
        if SAMPLE_VIDEO:
            check("quick scan: FFprobe data restored and health recomputed with it",
                  by["Perfect Movie"]["audio_tracks"] and not any("subtitle language" in x for x in by["Perfect Movie"]["health_reasons"]),
                  by["Perfect Movie"]["health_reasons"])
        # second quick scan with nothing changed → "up to date"
        _boxes.clear()
        app._start_quick_scan(LIB)
        wait_for(lambda: not app._scanning)
        check("quick scan: no changes → 'up to date' message", any("up to date" in str(b) for b in _boxes), _boxes)
        if SAMPLE_VIDEO:
            # Quick Scan probes a NEW movie with FFprobe when the box is ticked (v0.18.4)
            make_movie("Probe Me New")
            app._use_ffprobe.set(True)
            app._start_quick_scan(LIB)
            wait_for(lambda: not app._scanning)
            by = {r["subfolder"]: r for r in app._results}
            check("quick scan (box ticked): new movie probed (audio tracks present)", by.get("Probe Me New", {}).get("ffprobe_ran") and by["Probe Me New"]["audio_tracks"], by.get("Probe Me New", {}).get("audio_tracks"))
            # Update (no FFprobe) sees a NEW external subtitle (v0.18.4 fix)
            iid_p = next(i for i, d in app._item_map.items() if d["subfolder"] == "Probe Me New")
            io.open(os.path.join(LIB, "Probe Me New", "Probe Me New.en.srt"), "w", encoding="utf-8").write("1\n00:00:01,000 --> 00:00:02,000\nHi\n")
            app._reval_no_ffmpeg(iid_p, app._item_map[iid_p])
            dP = app._item_map[iid_p]
            check("Update (no FFprobe) picks up new external subtitle, keeps audio", any(x["lang"] == "en" for x in dP["subs_external"]) and dP["audio_tracks"] and "Ext: " in dP["subs_summary"] and "en" in dP["subs_summary"], (dP["subs_external"], dP["subs_summary"]))
        # health chips + problems only + reason filter
        app._set_health_filter("error")
        check("Errors chip filters the view", all(app._item_map[i]["health_status"] == "error" for i in app.tree.get_children()) and len(app.tree.get_children()) > 0)
        app._set_health_filter("problems")
        check("Problems only hides green rows", all(app._item_map[i]["health_status"] != "ok" for i in app.tree.get_children()) and app._problems_only_var.get())
        app._set_health_filter(None)
        app._filter_var.set("missing nfo"); app._refresh_table()
        check("filter matches health reason text", all(any("missing nfo" in x.lower() for x in app._item_map[i]["health_reasons"]) for i in app.tree.get_children()) and len(app.tree.get_children()) > 0, len(app.tree.get_children()))
        app._filter_var.set(""); app._refresh_table()
        # column chooser mapping
        mc.SETTINGS["hidden_columns"] = ["year", "genre", "rating"]; app._apply_column_visibility()
        check("hidden columns: display index maps to model index", app._model_col_index(0) == mc.COL_MOVIE_NAME and app._model_col_index(1) == mc.COL_VOTES, (app._model_col_index(1), mc.COL_VOTES))
        _first = list(app.tree.get_children())[0]
        check("tooltips work with hidden columns", bool(app._tooltip(_first, 0)) and ("Votes" in (app._tooltip(_first, 1) or "")), app._tooltip(_first, 1))
        mc.SETTINGS["hidden_columns"] = []; app._apply_column_visibility()
        check("show all columns restores #all", app._model_col_index(1) == 1)
        # poster → folder fix
        by = {r["subfolder"]: r for r in app._results}
        d_cf = by["Conflicting IDs"]
        _jpeg(d_cf["folder_path"], 600, 900, noisy=True)        # make folder.jpg differ
        app._reval_no_ffmpeg(next(i for i, d in app._item_map.items() if d["subfolder"] == "Conflicting IDs"), d_cf)
        d_cf = {r["subfolder"]: r for r in app._results}["Conflicting IDs"]
        check("poster/folder differ detected", d_cf["poster_bytes"] != d_cf["folder_bytes"] and any("Poster and folder image are different" in x for x in d_cf["health_reasons"]), d_cf["health_reasons"])
        _boxes.clear()
        app._copy_poster_to_folder([d_cf], confirm=False)
        wait_for(lambda: any("folder.jpg updated" in str(b) for b in _boxes), 30)
        time.sleep(0.1); wait_for(app._refresh_idle, 15)          # v0.19.0: automatic refresh runs in the background
        d_cf = {r["subfolder"]: r for r in app._results}["Conflicting IDs"]
        check("copy poster → folder: sizes equal, warning gone, backup made", d_cf["poster_bytes"] == d_cf["folder_bytes"] and not any("Poster and folder image are different" in x for x in d_cf["health_reasons"]) and any(n.startswith("backup_") for n in os.listdir(os.path.join(_APP_DIR, "backup"))), (d_cf["poster_bytes"], d_cf["folder_bytes"], d_cf["health_reasons"]))
        # reports + dialogs
        st_dlg = mc.TextReportDialog(app, "stats", mc.format_library_statistics(app._results)); st_dlg.destroy()
        cc = mc.ColumnChooserDialog(app); cc._vars["year"].set(False); cc._ok()
        check("column chooser persists + applies", mc.SETTINGS["hidden_columns"] == ["year"] and app._model_col_index(1) == mc.COL_GENRE)
        mc.SETTINGS["hidden_columns"] = []; app._apply_column_visibility()
        rpt2 = mc.format_health_report(app._results)
        _nv = [r for r in app._results if r["health_status"] == "error" and r["health_warnings"]]
        check("health report shows ⚠ lines inside an [ERROR] block + 'Most common issues'", bool(_nv) and "Most common issues:" in rpt2 and ("\u26a0  " + _nv[0]["health_warnings"][0]) in rpt2, _nv[0]["health_warnings"][:1] if _nv else "no error row with warnings")

        iid0 = next(i for i, d in app._item_map.items() if d["subfolder"] == "Perfect Movie")
        app._reval_no_ffmpeg(iid0, app._item_map[iid0])
        d0 = app._item_map[iid0]
        if SAMPLE_VIDEO:
            check("Update (no FFprobe) keeps audio + ffprobe_ran", d0["audio_tracks"] and d0["ffprobe_ran"])

        # Improvements batch (was crashing with NameError)
        rep = os.path.join(_TMP, "improve.txt")
        _boxes.clear()
        app._run_improvements_batch(list(app._results), rep)
        check("improvements batch writes report", wait_for(lambda: any("Complete" in str(b) for b in _boxes), 60) and os.path.getsize(rep) > 50, _boxes)
        check("improvements report lists a movie", "Movie:" in io.open(rep, encoding="utf-8").read())
        check("no error boxes so far", not any(b[0] == "error" for b in _boxes), _boxes)

        rpt = mc.format_health_report(app._results)
        check("health report text", "Health Status Report" in rpt and "ERROR movies" in rpt)

        # Export dialog (UI)
        dlg = mc.ExportListDialog(app, app._results, [app._item_map[i] for i in app.tree.get_children()], "Filmes")
        dlg._preset_var.set("All"); dlg._apply_preset()
        check("export dialog: All preset selects every field", dlg.selected_fields() == export_list.ALL_FIELD_KEYS)
        dlg._field_vars["path"].set(False); dlg._on_field_toggle()
        check("export dialog: unticking switches to Custom", dlg._preset_var.get() == "Custom")
        dlg._fmt_var.set("csv_semicolon"); dlg._scope_var.set("view")
        _target = os.path.join(_TMP, "ui_export.csv")
        fd.asksaveasfilename = lambda **k: _target
        try:
            dlg._do_export()
        finally:
            fd.asksaveasfilename = _orig_ask
        with open(_target, newline="", encoding="utf-8-sig") as f:
            rows_out = list(csv.reader(f, delimiter=";"))
        check("export dialog: semicolon CSV of current view", len(rows_out) == len(app.tree.get_children()) + 1 and 'Amor, Estranho "Amor"' in [r[0] for r in rows_out], (len(rows_out), len(app.tree.get_children())))
        check("export prefs remembered", mc.SETTINGS["export_prefs"].get("format") == "csv_semicolon" and "path" not in mc.SETTINGS["export_prefs"]["fields"])
        # second open restores Custom selection
        dlg2 = mc.ExportListDialog(app, app._results, [], "Filmes")
        check("export dialog: reopened with remembered fields", dlg2._preset_var.get() == "Custom" and not dlg2._field_vars["path"].get() and dlg2._fmt_var.get() == "csv_semicolon")
        dlg2.destroy()

        # ── v0.19.0 item 2: Sync Ratings memories (primary + zero-votes fallback) ──
        section("5b. ratings sync memories (v0.19.0)")
        by = {r["subfolder"]: r for r in app._results}
        # five movies with UNIQUE ids (several fixtures share TMDb 123 / an IMDb id on purpose for the duplicate tests)
        tg = [by[n] for n in ("Rating Conflict", "Bad Rating", "Merged Genre", "Kodi Ratings", "Foreign OK")]
        _t = {by["Rating Conflict"]["source_tmdb_val"]: ("7.5", "100"),
              by["Bad Rating"]["source_tmdb_val"]: ("6.0", "50"),
              by["Merged Genre"]["source_tmdb_val"]: ("0.0", "0"),
              by["Foreign OK"]["source_tmdb_val"]: ("7.0", "10")}
        _o = {by["Rating Conflict"]["source_imdb_val"]: ("8.0", "500"),
              by["Bad Rating"]["source_imdb_val"]: ("0.0", "0"),
              by["Merged Genre"]["source_imdb_val"]: ("0.0", "0"),
              by["Foreign OK"]["source_imdb_val"]: ("7.0", "10")}
        check("v0.19 fixture ids are unique", len({d["source_tmdb_val"] for d in tg}) == 5 and len({d["source_imdb_val"] for d in tg}) == 5, [(d["source_tmdb_val"], d["source_imdb_val"]) for d in tg])
        _orig_ft, _orig_fo = mc._fetch_tmdb_rating, mc._fetch_omdb_rating
        mc._fetch_tmdb_rating = lambda tid, key: _t.get(tid, (None, None))
        mc._fetch_omdb_rating = lambda iid, key: _o.get(iid, (None, None))
        calls = []
        def _script(answers):
            def _ask(movie_name, tr, tv, or_, ov, show_checkboxes, fallback_mode=False):
                calls.append((movie_name, tr, or_, show_checkboxes, fallback_mode))
                base = {"choice": "cancel", "apply_all": False, "use_more_votes": False,
                        "manual_r": None, "manual_v": None, "apply_fallback": False}
                base.update(answers[1] if fallback_mode else answers[0])
                return base
            return _ask
        def _rating_of(d):
            return mc.extract_rating_from_files(d["nfo_path"], d["xml_path"])[0], mc.extract_votes_from_files(d["nfo_path"], d["xml_path"])[0]
        try:
            # run 1: "use the source with more votes" + fallback typed 5.5/7 applied to all zero/zero
            app._ask_ratings_dialog = _script([{"choice": "tmdb", "use_more_votes": True},
                                               {"choice": "manual", "manual_r": 5.5, "manual_v": 7, "apply_fallback": True}])
            _boxes.clear(); app._sync_ratings_worker(tg, "k", "k", None); time.sleep(0.5)
            check("v0.19 run 1: exactly one primary + one fallback prompt", len(calls) == 2 and calls[0][4] is False and calls[1][4] is True, calls)
            check("v0.19 run 1: invalid source hidden from the dialog (0/0 → None)", calls[0][1] == "7.5" and calls[0][2] == "8.0" and calls[0][3] is True, calls[0])
            check("v0.19 run 1: more votes picked (OMDb 8.0/500)", _rating_of(by["Rating Conflict"]) == ("8.0", 500), _rating_of(by["Rating Conflict"]))
            check("v0.19 run 1: other valid source substituted (TMDb 6.0/50, OMDb was 0/0)", _rating_of(by["Bad Rating"]) == ("6.0", 50), _rating_of(by["Bad Rating"]))
            check("v0.19 run 1: tie → average 7.0 / 10", _rating_of(by["Foreign OK"]) == ("7.0", 10), _rating_of(by["Foreign OK"]))
            check("v0.19 run 1: zero/zero movies get the remembered fallback 5.5/7", _rating_of(by["Merged Genre"]) == ("5.5", 7) and _rating_of(by["Kodi Ratings"]) == ("5.5", 7), (_rating_of(by["Merged Genre"]), _rating_of(by["Kodi Ratings"])))
            check("v0.19 run 1: fallback prompt opened for the FIRST zero/zero movie only", calls[1][0] == by["Merged Genre"]["movie_name"], calls[1])
            # run 2: memories reset; "Type Values" + "Apply to all" → every movie, one prompt, no skipping
            calls.clear()
            app._ask_ratings_dialog = _script([{"choice": "manual", "manual_r": 9.1, "manual_v": 3, "apply_all": True}, {}])
            app._sync_ratings_worker(tg, "k", "k", None); time.sleep(0.5)
            check("v0.19 run 2: memories are per run (asked again) and manual+apply-all prompts once", len(calls) == 1, calls)
            check("v0.19 run 2: typed values written to all 5 movies incl. zero/zero", all(_rating_of(d) == ("9.1", 3) for d in tg), [_rating_of(d) for d in tg])
            # run 3: "Use TMDb" + apply to all; zero/zero → skip all (remembered); nothing written as 0.0 / 0
            calls.clear()
            app._ask_ratings_dialog = _script([{"choice": "tmdb", "apply_all": True}, {"choice": "cancel", "apply_fallback": True}])
            app._sync_ratings_worker(tg, "k", "k", None); time.sleep(0.5)
            check("v0.19 run 3: two prompts (primary + skip-all fallback)", len(calls) == 2, calls)
            check("v0.19 run 3: zero/zero movies skipped, never 0.0", _rating_of(by["Merged Genre"]) == ("9.1", 3) and _rating_of(by["Kodi Ratings"]) == ("9.1", 3) and _rating_of(by["Bad Rating"]) == ("6.0", 50) and _rating_of(by["Rating Conflict"]) == ("7.5", 100), (_rating_of(by["Merged Genre"]), _rating_of(by["Bad Rating"]), _rating_of(by["Rating Conflict"])))
            # single movie: no checkboxes offered
            calls.clear(); app._ask_ratings_dialog = _script([{"choice": "omdb"}, {}])
            app._sync_ratings_worker([by["Rating Conflict"]], "k", "k", None); time.sleep(0.3)
            check("v0.19 single movie: checkboxes hidden", len(calls) == 1 and calls[0][3] is False, calls)
            check("v0.19 _rating_valid rejects 0.0 and 0 votes", mc.App._rating_valid("0.0", "10") is False and mc.App._rating_valid("7.0", "0") is False and mc.App._rating_valid("7.0", "1,200") is True)
            # dialogs build in both modes (smoke)
            _d1 = mc.RatingsCompareDialog(app, "x", None, None, None, None, show_checkboxes=True, fallback_mode=True); _d1.update(); _d1.destroy()
            _d2 = mc.CustomGenreDialog(app, "m", ["x"], show_apply_all=True); _d2.update(); _d2.destroy()
            _d3 = mc._SourceManualEntryDialog(app, "m", "TMDB", show_skip_all=True); _d3.update(); _d3.destroy()
            check("v0.19 new dialog variants build", True)
        finally:
            mc._fetch_tmdb_rating, mc._fetch_omdb_rating = _orig_ft, _orig_fo
            del app._ask_ratings_dialog
        # custom-genre dialog: "apply to all remaining" remembered for the run
        asked = []
        _orig_ask_ui = app._ask_on_ui
        app._ask_on_ui = lambda make, read, timeout=600: (asked.append(1) or (True, True))   # delete custom, apply to all
        _boxes.clear()
        app._normalize_genres_worker([by["Custom Genre A"], by["Custom Genre B"]], None); time.sleep(0.5)
        _ga = mc.get_genres_from_nfo(by["Custom Genre A"]["nfo_path"]); _gb = mc.get_genres_from_nfo(by["Custom Genre B"]["nfo_path"])
        check("v0.19 custom-genre choice remembered (1 prompt, both cleaned)", len(asked) == 1 and "Weirdo" not in _ga and "Oddball" not in _gb, (asked, _ga, _gb))
        # Normalize Sources: "Skip all remaining" remembered
        asked.clear()
        app._ask_on_ui = lambda make, read, timeout=600: (asked.append(1) or (None, True))    # no id, skip all
        app._normalize_sources_worker([by["No TMDB A"], by["No TMDB B"]], None); time.sleep(0.5)
        check("v0.19 Normalize Sources skip-all remembered (1 prompt)", len(asked) == 1, asked)
        app._ask_on_ui = _orig_ask_ui
        _boxes.clear()

        # ── v0.19.0 item 3: window size / position memory ─────────────────────
        section("5c. window memory (v0.19.0)")
        # transient dialogs inherit the parent's withdrawn state (then Tk reports
        # no usable geometry), so the hidden test window is shown for this block
        app.deiconify(); app.update(); time.sleep(0.3)
        def _geom(win):
            m = mc._GEOM_RE.match(win.geometry()); return tuple(int(m.group(i)) for i in (1, 2, 3, 4)) if m else None
        def _near(a, b, tol=40):
            return a is not None and b is not None and all(abs(x - y) <= tol for x, y in zip(a, b))
        check("v0.19 clamp: off-screen position pulled back", mc._clamp_geometry("800x600+9000+9000", app) is not None and mc._GEOM_RE.match(mc._clamp_geometry("800x600+9000+9000", app)).group(3).lstrip("+").isdigit() and int(mc._GEOM_RE.match(mc._clamp_geometry("800x600+9000+9000", app)).group(3)) < 9000)
        check("v0.19 clamp: garbage geometry rejected", mc._clamp_geometry("-5000x-5000+0+0", app) is None and mc._clamp_geometry("", app) is None and mc._clamp_geometry(None, app) is None)
        check("v0.19 clamp: negative x (second monitor) kept when inside the virtual screen or clamped", mc._clamp_geometry("640x480-200+10", app) is not None)
        mc.SETTINGS["window_geometry"] = {}
        wd = mc.TextReportDialog(app, "geomtest", "x\ny", "geomtest")
        wd.geometry("700x500+120+80"); wd.update(); time.sleep(0.7); wd.update()
        _e = mc.SETTINGS["window_geometry"].get("TextReportDialog:geomtest") or {}
        _m = mc._GEOM_RE.match(_e.get("geometry", ""))
        check("v0.19 <Configure> debounce stores the geometry in memory", bool(_m) and _near(tuple(int(_m.group(i)) for i in (1, 2, 3, 4)), (700, 500, 120, 80)), _e)
        _before = os.path.getmtime(sc.CONFIG_PATH)
        wd.destroy(); time.sleep(0.3)
        _cfg = json.load(open(sc.CONFIG_PATH, encoding="utf-8"))
        check("v0.19 settings.json written on close with window_geometry", "TextReportDialog:geomtest" in (_cfg.get("window_geometry") or {}), list((_cfg.get("window_geometry") or {}).keys()))
        wd2 = mc.TextReportDialog(app, "geomtest", "x", "geomtest"); wd2.update()
        check("v0.19 reopened dialog restored where it was left", _near(_geom(wd2), (700, 500, 120, 80)), _geom(wd2))
        wd2.destroy()
        wd3 = mc.TextReportDialog(app, "other", "x", "other"); wd3.update()
        check("v0.19 same class, other stem → own default geometry", not _near(_geom(wd3), (700, 500, 120, 80), 5), _geom(wd3))
        wd3.destroy()
        # off-screen values written into settings.json still open visibly
        mc.SETTINGS["window_geometry"]["ColumnChooserDialog"] = {"geometry": "300x200+9000+9000", "zoomed": False}
        mc.SETTINGS["window_geometry"]["TextReportDialog:bad"] = {"geometry": "-5000x-5000+0+0", "zoomed": False}
        cc2 = mc.ColumnChooserDialog(app); cc2.update()
        check("v0.19 off-screen position clamped onto the screen", cc2.winfo_x() < cc2.winfo_screenwidth() - 100 and cc2.winfo_y() < cc2.winfo_screenheight() - 50, (cc2.winfo_x(), cc2.winfo_y()))
        cc2.destroy()
        bd = mc.TextReportDialog(app, "bad", "x", "bad"); bd.update()
        check("v0.19 garbage geometry ignored (default size used)", bd.winfo_width() > 300 and bd.winfo_height() > 200, (bd.winfo_width(), bd.winfo_height()))
        bd.destroy()
        # non-resizable dialogs: position only
        mc.SETTINGS["window_geometry"]["ColumnChooserDialog"] = {"geometry": "900x900+60+70", "zoomed": False}
        cc3 = mc.ColumnChooserDialog(app); cc3.update()
        check("v0.19 non-resizable dialog restores position, keeps its own size", cc3.winfo_width() < 850 and abs(cc3.winfo_x() - 60) <= 40 and abs(cc3.winfo_y() - 70) <= 60, (cc3.winfo_width(), cc3.winfo_x(), cc3.winfo_y()))
        cc3.destroy()
        # main window: zoomed state captured by the close path
        if sys.platform == "win32":   # Tk accepts state("zoomed") only on Windows (CI runs on Linux)
            app.state("zoomed"); app.update(); time.sleep(0.4); app.update()
            app._mc_geom_capture()
            check("v0.19 main window zoomed state captured", mc.SETTINGS["window_geometry"].get("App", {}).get("zoomed") is True, mc.SETTINGS["window_geometry"].get("App"))
        app.state("normal"); app.update(); app.geometry("1300x700+30+40"); app.update(); time.sleep(0.7); app.update()
        check("v0.19 main window normal geometry captured", _near(tuple(int(mc._GEOM_RE.match(mc.SETTINGS["window_geometry"]["App"]["geometry"]).group(i)) for i in (1, 2, 3, 4)), (1300, 700, 30, 40)) and mc.SETTINGS["window_geometry"]["App"]["zoomed"] is False, mc.SETTINGS["window_geometry"].get("App"))
        # ── v0.19.0 item 4: verification worker + report dialog ───────────────
        section("5d. verify IDs worker + report (v0.19.0)")
        by = {r["subfolder"]: r for r in app._results}
        _vrows = [by["Xuxa OK"], by["Wrong Film"], by["Mixed Ids"], by["Dead Ids"], by["Disagree Ids"]]
        _reports = []
        class _RecReport:
            def __init__(self, parent, rows): _reports.append(rows)
        _orig_rl, _orig_dlg = mc._tmdb_rate_limited_fetch, mc._IdVerifyReportDialog
        mc._tmdb_rate_limited_fetch = _fake_tmdb; mc._IdVerifyReportDialog = _RecReport
        try:
            _boxes.clear()
            app._verify_ids_worker(list(_vrows), "k", None)
            check("verify worker: report opened with all checked rows", wait_for(lambda: bool(_reports), 10) and len(_reports[0]) == 5)
            check("verify worker: id_check stored on rows + results", by["Xuxa OK"]["id_check"]["result"] == mc.ID_OK and by["Mixed Ids"]["id_check"]["result"] == mc.ID_DIFFERENT and by["Dead Ids"]["id_check"]["result"] == mc.ID_NOT_FOUND)
            _iid = next(i for i, d in app._item_map.items() if d["subfolder"] == "Mixed Ids")
            check("verify worker: Source tooltip shows the result", "Verified" in app._tooltip(_iid, mc.COL_SOURCE) and mc.ID_DIFFERENT in app._tooltip(_iid, mc.COL_SOURCE), app._tooltip(_iid, mc.COL_SOURCE))
            check("verify worker: result survives the results cache", any(r.get("id_check", {}).get("result") == mc.ID_OK for r in sc.load_results_cache() if r["subfolder"] == "Xuxa OK"))
            check("verify worker: no error boxes", not any(b[0] == "error" for b in _boxes), _boxes)
            # network failure → clear message, partial results kept
            _reports.clear(); _boxes.clear()
            _calls = {"n": 0}
            def _flaky(url, timeout=15):
                _calls["n"] += 1
                if _calls["n"] > 2: raise _ue.URLError("getaddrinfo failed")
                return _fake_tmdb(url, timeout)
            mc._tmdb_rate_limited_fetch = _flaky
            app._verify_ids_worker(list(_vrows), "k", None)
            wait_for(lambda: any(b[0] == "error" for b in _boxes), 10)
            check("verify worker: network error → error box with a clear message, partial report", any(b[0] == "error" and "stopped" in str(b[1][0]) for b in _boxes) and _reports and len(_reports[0]) == 1, (_boxes, len(_reports[0]) if _reports else None))
        finally:
            mc._tmdb_rate_limited_fetch, mc._IdVerifyReportDialog = _orig_rl, _orig_dlg
        # the real report dialog: sorting + save
        for d in _vrows:
            if not d.get("id_check"):
                d["id_check"] = {"result": mc.ID_NONE, "detail": "", "imdb_id": None, "tmdb_id": None, "tmdb_title": "", "tmdb_year": "", "when": ""}
        rd = mc._IdVerifyReportDialog(app, _vrows); rd.update()
        _first = rd.sorted_rows()[0]["id_check"]["result"]
        check("verify report: problems sorted first, OK last", _first != mc.ID_OK and rd.sorted_rows()[-1]["id_check"]["result"] == mc.ID_OK, [r["id_check"]["result"] for r in rd.sorted_rows()])
        rd._sort_by("movie")
        _names = [r["movie_name"] for r in rd.sorted_rows()]
        check("verify report: sort by movie name (displayed title)", _names == sorted(_names, key=str.lower), _names)
        rd._sort_by("movie")
        check("verify report: second click reverses", [r["movie_name"] for r in rd.sorted_rows()] == list(reversed(_names)))
        _csv = os.path.join(_TMP, "verify.csv"); _txt = os.path.join(_TMP, "verify.txt")
        rd.save_to(_csv); rd.save_to(_txt)
        with open(_csv, newline="", encoding="utf-8-sig") as f:
            _rows_csv = list(csv.reader(f))
        check("verify report: CSV + TXT saved", _rows_csv[0][0] == "Movie" and len(_rows_csv) == 6 and "ID verification" in io.open(_txt, encoding="utf-8").read())
        rd._tree.selection_set(rd._tree.get_children()[0]); rd._update_fix_state()
        check("verify report: Fix… enabled only for non-OK rows", str(rd._fix_btn.cget("state")) == ("normal" if rd.sorted_rows()[0]["id_check"]["result"] != mc.ID_OK else "disabled"))
        rd.destroy()
        _boxes.clear()

        # ── v0.19.0 item 5: Auto Repair worker ────────────────────────────────
        section("5e. auto repair worker (v0.19.0)")
        by = {r["subfolder"]: r for r in app._results}
        _ar_rows = [by[n] for n in ("Auto Ids", "Ask Ids", "Auto Conflict", "Bare Movie", "Title Copy", "Auto Rating", "Auto Genre", "Perfect Movie")]
        by["Bare Movie"]["id_check"] = {"result": mc.ID_OK, "tmdb_id": "555", "imdb_id": "tt0000555", "detail": "", "when": ""}
        _img_mtimes = {d["subfolder"]: tuple(os.path.getmtime(d[k + "_path"]) for k in ("poster", "folder", "fanart")) for d in _ar_rows}
        _t_rat = {by["Auto Rating"]["source_tmdb_val"]: ("7.2", "300")}
        _o_rat = {by["Auto Rating"]["source_imdb_val"]: ("8.4", "900")}
        _orig = (mc._fetch_tmdb_rating, mc._fetch_omdb_rating, mc.TextReportDialog, mc._tmdb_rate_limited_fetch)
        mc._fetch_tmdb_rating = lambda tid, key: _t_rat.get(tid, (None, None))
        mc._fetch_omdb_rating = lambda iid, key: _o_rat.get(iid, (None, None))
        mc._tmdb_rate_limited_fetch = _fake_tmdb5
        _summaries = []
        class _RecSummary:
            def __init__(self, parent, title, text, stem="x"): _summaries.append((title, text))
        mc.TextReportDialog = _RecSummary
        _chooser_calls = []
        app._ask_id_chooser = lambda name, year, cands, show_apply_all=False, preselect=None: (_chooser_calls.append((name, len(cands), show_apply_all)) or (None, True))
        _n_backups = len([n for n in os.listdir(os.path.join(_APP_DIR, "backup")) if n.startswith("backup_")])
        try:
            _boxes.clear()
            app._auto_repair_worker(list(_ar_rows), {"tmdb_key": "k", "omdb_key": "k", "lang": "en-US", "rating_pref": "votes", "multi": True, "fetch": _fake_tmdb5}, None)
            wait_for(lambda: bool(_summaries), 10); time.sleep(0.5)
            _txt = _summaries[0][1] if _summaries else ""
            def _ids(d): return mc.get_movie_ids_robust(d["nfo_path"], d["xml_path"])
            check("auto repair: exact title+year → IDs written to NFO and XML without asking", _ids(by["Auto Ids"]) == ("tt0009001", "9001") and mc.extract_source_ids_from_files(by["Auto Ids"]["nfo_path"], by["Auto Ids"]["xml_path"])["tmdb_status"] == mc.STATUS_OK, _ids(by["Auto Ids"]))
            check("auto repair: no exact match → chooser once, skip-all remembered", len(_chooser_calls) == 1 and _chooser_calls[0][0] == "Ask Ids" and _chooser_calls[0][2] is True and _ids(by["Ask Ids"])[1] is None, (_chooser_calls, _ids(by["Ask Ids"])))
            check("auto repair: conflicting IMDb resolved to the one TMDb confirms", _ids(by["Auto Conflict"]) == ("tt0000777", "777") and len(set(mc.extract_source_ids_from_files(by["Auto Conflict"]["nfo_path"], by["Auto Conflict"]["xml_path"])["imdb_all_vals"])) == 1, _ids(by["Auto Conflict"]))
            _bn = io.open(by["Bare Movie"]["nfo_path"], encoding="utf-8").read(); _bx = io.open(by["Bare Movie"]["xml_path"], encoding="utf-8").read()
            check("auto repair: year + genres from the verified TMDb ID", "<year>1995</year>" in _bn and "<ProductionYear>1995</ProductionYear>" in _bx and "<genre>Science Fiction</genre>" in _bn and "<Genre>Adventure</Genre>" in _bx, (_bn[:400], _bx[:400]))
            check("auto repair: XML <Language> filled from NFO <language>por</language>", "<Language>Portuguese</Language>" in _bx, _bx[:500])
            check("auto repair: empty NFO <title> copied from XML <LocalTitle>", "<title>Title Copy</title>" in io.open(by["Title Copy"]["nfo_path"], encoding="utf-8").read())
            check("auto repair: ratings synced with the one-time choice (more votes → 8.4/900)", _rating_of(by["Auto Rating"]) == ("8.4", 900), _rating_of(by["Auto Rating"]))
            check("auto repair: genres normalized, synonyms resolved", mc.get_genres_from_nfo(by["Auto Genre"]["nfo_path"]) == ["Family", "Fantasy", "Science Fiction"], mc.get_genres_from_nfo(by["Auto Genre"]["nfo_path"]))
            check("auto repair: images untouched", all(_img_mtimes[d["subfolder"]] == tuple(os.path.getmtime(d[k + "_path"]) for k in ("poster", "folder", "fanart")) for d in _ar_rows))
            _n_backups2 = len([n for n in os.listdir(os.path.join(_APP_DIR, "backup")) if n.startswith("backup_")])
            check("auto repair: one batch backup folder for the run (+ per-write rating backups)", _n_backups2 >= _n_backups + 1)
            _need = ["[FIXED", "skipped: no exact TMDb match", "Perfect Movie", "6  movie(s) fixed", "still: "]
            _missing = [x for x in _need if x not in _txt]
            check("auto repair: summary dialog lists fixed / skipped / still failing", bool(_summaries) and "Auto Repair" in _summaries[0][0] and not _missing, (_missing, _txt[_txt.find("Perfect Movie"):][:300]))
            by2 = {r["subfolder"]: r for r in app._results}
            check("auto repair: rows refreshed in the table (no FFprobe), IDs now ⬤", by2["Auto Ids"]["source_tmdb_status"] == mc.STATUS_OK and by2["Auto Ids"] is not by["Auto Ids"] and not any("Missing TMDb ID" in x for x in by2["Auto Ids"]["health_reasons"]), by2["Auto Ids"]["health_reasons"])
            if SAMPLE_VIDEO:
                check("auto repair: refreshed row keeps FFprobe data", by2["Auto Ids"]["audio_tracks"] and by2["Auto Ids"]["ffprobe_ran"])
            check("auto repair: no error boxes", not any(b[0] == "error" for b in _boxes), _boxes)
            # options / preview / chooser dialogs build
            _od = mc._AutoRepairOptionsDialog(app, 3, offer_dry_run=True); _od.update(); _od._ok()
            check("auto repair: options dialog returns the rating preference + dry run", _od.result == {"rating_pref": "votes", "dry_run": True})
            _pv = mc._PreviewRunDialog(app, "preview", "text"); _pv.update(); _pv._run()
            check("auto repair: preview dialog Run button", _pv.run is True)
            _ch = mc._IdChooserDialog(app, "m", "2001", mc._tmdb_search_movie("Ask Ids", "2001", "k", "en-US", fetch=_fake_tmdb5), show_apply_all=True, preselect=0)
            _ch.update(); _ch._apply()
            check("auto repair: chooser returns the selected candidate", _ch.result and _ch.result["tmdb_id"] == "9002" and _ch.skip_all is False)
            # Fix… from the verification report uses the chooser
            _chooser_calls.clear()
            app._ask_id_chooser = lambda name, year, cands, show_apply_all=False, preselect=None: (_chooser_calls.append((name, preselect)) or (cands[0], False))
            _fixed = []
            _old_key = mc.SETTINGS.get("tmdb_api_key", ""); mc.SETTINGS["tmdb_api_key"] = "k"
            app._fix_ids_for(by2["Ask Ids"], on_done=lambda r: _fixed.append(r))
            wait_for(lambda: bool(_fixed), 10); mc.SETTINGS["tmdb_api_key"] = _old_key
            check("fix from report: chooser shown, IDs written, row re-verified + refreshed", wait_for(lambda: bool(_fixed), 10) and _ids(by2["Ask Ids"]) == ("tt0009002", "9002") and (by2["Ask Ids"].get("id_check") or {}).get("result") in (mc.ID_OK, mc.ID_OTHER), (_ids(by2["Ask Ids"]), by2["Ask Ids"].get("id_check")))
        finally:
            mc._fetch_tmdb_rating, mc._fetch_omdb_rating, mc.TextReportDialog, mc._tmdb_rate_limited_fetch = _orig
            if "_ask_id_chooser" in app.__dict__: del app._ask_id_chooser
        _boxes.clear()

        # ── v0.19.0 item 6: central automatic refresh ─────────────────────────
        section("5f. automatic refresh (v0.19.0)")
        wait_for(app._refresh_idle, 15)
        by = {r["subfolder"]: r for r in app._results}
        _paths = [by[n]["subfolder_path"] for n in ("Perfect Movie", "Rating Conflict", "Merged Genre", "Foreign OK", "Kodi Ratings")]
        _saves = []; _orig_save = app._incremental_save
        app._incremental_save = lambda res, throttle=False: (_saves.append(1), _orig_save(res, throttle))
        _probe = {"ff": 0, "noff": 0}
        _orig_rr, _orig_rn = app._rescan_row, app._rescan_row_no_probe
        app._rescan_row = lambda d, use_ffprobe=None, force_ffprobe=False: (_probe.__setitem__("ff", _probe["ff"] + 1), _orig_rr(d, use_ffprobe, force_ffprobe))[1]
        app._rescan_row_no_probe = lambda d: (_probe.__setitem__("noff", _probe["noff"] + 1), _orig_rn(d))[1]
        try:
            _runs0 = app._rf_runs
            for _i in range(10):                                   # ten rapid requests from a worker thread
                app._schedule_refresh([_paths[_i % 5]], need_ffprobe=False)
            time.sleep(0.1)
            check("refresh: requests are coalesced (one pending batch)", len(app._rf_pending) == 5 and app._rf_timer is not None, (len(app._rf_pending), app._rf_timer))
            wait_for(lambda: app._rf_runs > _runs0 and app._refresh_idle(), 20)
            check("refresh: ten requests → ONE background run, ONE cache save", app._rf_runs == _runs0 + 1 and len(_saves) == 1, (app._rf_runs - _runs0, len(_saves)))
            check("refresh: metadata changes use the no-FFprobe path (5 rows)", _probe == {"ff": 0, "noff": 5}, _probe)
            by2 = {r["subfolder"]: r for r in app._results}
            check("refresh: rows replaced in results and table", all(by2[n] is not by[n] for n in ("Perfect Movie", "Rating Conflict")) and any(app._item_map[i] is by2["Perfect Movie"] for i in app.tree.get_children()))
            if SAMPLE_VIDEO:
                check("refresh: FFprobe data kept by the no-FFprobe refresh", by2["Perfect Movie"]["audio_tracks"] and by2["Perfect Movie"]["ffprobe_ran"])
            # a request made while a batch runs is queued (exactly one follow-up)
            _saves.clear(); _runs0 = app._rf_runs
            _slow_evt = threading.Event()
            def _slow(d):
                _slow_evt.wait(3); return _orig_rn(d)
            app._rescan_row_no_probe = _slow
            app._schedule_refresh([_paths[0]])
            wait_for(lambda: app._rf_running, 5)
            app._schedule_refresh([_paths[1]]); app._schedule_refresh([_paths[2]])
            time.sleep(0.2)
            check("refresh: request during a run is queued, not started in parallel", app._rf_running and len(app._rf_pending) == 2 and app._rf_timer is None, (app._rf_running, app._rf_pending, app._rf_timer))
            _slow_evt.set()
            wait_for(lambda: app._rf_runs >= _runs0 + 2 and app._refresh_idle(), 20)
            check("refresh: queued request runs exactly once afterwards", app._rf_runs == _runs0 + 2 and len(_saves) == 2, (app._rf_runs - _runs0, len(_saves)))
            app._rescan_row_no_probe = lambda d: (_probe.__setitem__("noff", _probe["noff"] + 1), _orig_rn(d))[1]
            # need_ffprobe → the FFprobe path; merged flag wins
            _probe.update(ff=0, noff=0); _runs0 = app._rf_runs
            app._schedule_refresh([_paths[3]], need_ffprobe=False); app._schedule_refresh([_paths[3]], need_ffprobe=True)
            wait_for(lambda: app._rf_runs > _runs0 and app._refresh_idle(), 30)
            check("refresh: need_ffprobe=True uses the FFprobe rescan (flag merged)", _probe == {"ff": 1, "noff": 0}, _probe)
            # wrapper used by the fetch dialogs / search apply
            _probe.update(ff=0, noff=0); _runs0 = app._rf_runs
            app.after(0, lambda: app._reval_by_path(by2["Foreign OK"]))
            wait_for(lambda: app._rf_runs > _runs0 and app._refresh_idle(), 20)
            check("refresh: _reval_by_path → no-FFprobe central refresh", _probe == {"ff": 0, "noff": 1}, _probe)
            # actions: ratings sync refreshes once at the end, without FFprobe
            _probe.update(ff=0, noff=0); _saves.clear(); _runs0 = app._rf_runs
            _of, _oo = mc._fetch_tmdb_rating, mc._fetch_omdb_rating
            mc._fetch_tmdb_rating = lambda tid, key: ("6.6", "66"); mc._fetch_omdb_rating = lambda iid, key: (None, None)
            app._ask_ratings_dialog = lambda *a, **k: {"choice": "tmdb", "apply_all": True, "use_more_votes": False, "manual_r": None, "manual_v": None, "apply_fallback": False}
            try:
                app._sync_ratings_worker([by2[n] for n in ("Perfect Movie", "Rating Conflict", "Merged Genre")], "k", "", None)
            finally:
                mc._fetch_tmdb_rating, mc._fetch_omdb_rating = _of, _oo
                del app._ask_ratings_dialog
            wait_for(lambda: app._rf_runs > _runs0 and app._refresh_idle(), 20)
            by3 = {r["subfolder"]: r for r in app._results}
            check("action refresh: ratings sync → one batch, no FFprobe, row shows the new rating", app._rf_runs == _runs0 + 1 and _probe == {"ff": 0, "noff": 3} and by3["Perfect Movie"]["rating_str"] == "6.6", (app._rf_runs - _runs0, _probe, by3["Perfect Movie"]["rating_str"]))
            # normalize genres rescans (v0.18.4 only redrew)
            _probe.update(ff=0, noff=0); _runs0 = app._rf_runs
            _gm = by3["Merged Genre"]
            _gn = io.open(_gm["nfo_path"], encoding="utf-8").read()
            io.open(_gm["nfo_path"], "w", encoding="utf-8").write(_gn.replace("<genre>Drama</genre>", "<genre>Family/Fantasy</genre>"))
            app._normalize_genres_worker([_gm], None)
            wait_for(lambda: app._rf_runs > _runs0 and app._refresh_idle(), 20)
            check("action refresh: normalize genres → row rescanned without FFprobe", _probe["noff"] >= 1 and _probe["ff"] == 0, _probe)
        finally:
            app._incremental_save = _orig_save
            app._rescan_row, app._rescan_row_no_probe = _orig_rr, _orig_rn
        _boxes.clear()

        # ── v0.19.0 item 7: multiple library folders ──────────────────────────
        section("5g. multiple libraries (v0.19.0)")
        def on_ui(fn, timeout=30):
            """Run fn on the Tk main thread and wait (table rebuilds must not
            interleave with the main loop's own updates)."""
            ev = threading.Event(); box = {}
            def _run():
                try: box["r"] = fn()
                except Exception: box["e"] = traceback.format_exc()
                finally: ev.set()
            app.after(0, _run); ev.wait(timeout)
            if "e" in box: raise RuntimeError(box["e"])
            return box.get("r")
        wait_for(app._refresh_idle, 15)
        LIB2 = os.path.join(_TMP, "Filmes2"); os.makedirs(LIB2, exist_ok=True)
        _save_lib = LIB
        def _mk2(name, **kw):
            global LIB
            LIB = LIB2
            try:
                return make_movie(name, video=False, **kw)
            finally:
                LIB = _save_lib
        _mk2("Second Lib Movie", title="Second Lib Movie")
        _mk2("Perfect Movie Copy2", title="Perfect Movie", nfo_imdb="tt0000001", xml_imdb="tt0000001", nfo_tmdb="123", xml_tmdb="123")
        n_lib1 = len([d for d in os.listdir(LIB) if os.path.isdir(os.path.join(LIB, d))])
        on_ui(lambda: app._set_libraries([LIB, LIB2], select=""))
        check("libraries: combobox lists All + both roots", list(app._lib_combo.cget("values")) == [mc._ALL_LIBS, LIB, LIB2], app._lib_combo.cget("values"))
        on_ui(lambda: app._start_scan(app._scope_roots(), use_ff=False))
        wait_for(lambda: not app._scanning, 120)
        by = {r["subfolder"]: r for r in app._results}
        check("libraries: one combined table with both roots", len(app._results) == n_lib1 + 2 and "Second Lib Movie" in by and by["Second Lib Movie"]["library_root"] == LIB2, (len(app._results), n_lib1))
        check("libraries: duplicate detected across roots", "Perfect Movie Copy2" in (by["Perfect Movie"].get("duplicate_of") or []), by["Perfect Movie"].get("duplicate_of"))
        if SAMPLE_VIDEO:
            check("libraries: FFprobe data of root 1 kept by the no-FFprobe scan", by["Perfect Movie"]["audio_tracks"])
        _iid = next(i for i, d in app._item_map.items() if d["subfolder"] == "Second Lib Movie")
        check("libraries: Movie Name tooltip shows the library", ("Library: " + LIB2) in app._tooltip(_iid, mc.COL_MOVIE_NAME))
        check("libraries: Library column value + tooltip", app._rv(by["Second Lib Movie"])[mc.COL_LIBRARY] == LIB2 and LIB2 in app._tooltip(_iid, mc.COL_LIBRARY))
        _rep = mc.format_health_report(app._results); _st = mc.format_library_statistics(app._results)
        check("libraries: health report and statistics show the library", ("Library: " + LIB2) in _rep and "LIBRARIES" in _st and LIB2 in _st)
        # filter → view + scope
        on_ui(lambda: (app._lib_filter_var.set(LIB2), app._on_library_filter()))
        check("libraries: filter shows only that library", {app._item_map[i]["library_root"] for i in app.tree.get_children()} == {LIB2} and len(app.tree.get_children()) == 2)
        check("libraries: scope of the scans = the selected library", app._scope_roots() == [LIB2])
        _keep = by["Conflicting IDs"]
        on_ui(lambda: app._start_scan(app._scope_roots(), use_ff=False))
        wait_for(lambda: not app._scanning, 60)
        by = {r["subfolder"]: r for r in app._results}
        check("libraries: scanning one library keeps the other library's rows untouched", len(app._results) == n_lib1 + 2 and by["Conflicting IDs"] is _keep, len(app._results))
        _mk2("Third In Lib2", title="Third In Lib2")
        on_ui(lambda: app._start_quick_scan(app._scope_roots()))
        wait_for(lambda: not app._scanning, 60)
        by = {r["subfolder"]: r for r in app._results}
        check("libraries: Quick Scan of one library adds its new movie, keeps the rest", "Third In Lib2" in by and by["Conflicting IDs"] is _keep and len(app._results) == n_lib1 + 3, len(app._results))
        on_ui(lambda: (app._lib_filter_var.set(mc._ALL_LIBS), app._on_library_filter()))
        check("libraries: 'All libraries' shows everything", len(app.tree.get_children()) == n_lib1 + 3)
        # offline library: rename root 2, scan all → its rows kept, flagged offline
        LIB2_OFF = LIB2 + "_offline"; os.rename(LIB2, LIB2_OFF)
        try:
            _boxes.clear()
            on_ui(lambda: app._start_scan(app._scope_roots(), use_ff=False))
            wait_for(lambda: not app._scanning, 120)
            by = {r["subfolder"]: r for r in app._results}
            check("offline: cached rows of the unreachable library are kept", "Second Lib Movie" in by and "Third In Lib2" in by and len(app._results) == n_lib1 + 3, len(app._results))
            check("offline: marked offline (status bar + tooltip + Library cell)", mc._pkey(LIB2) in app._offline_roots and "Offline" in app._sb_action.cget("text") and "(offline)" in app._rv(by["Second Lib Movie"])[mc.COL_LIBRARY])
            check("offline: results cache still holds its rows", any(r["subfolder"] == "Second Lib Movie" for r in sc.load_results_cache()))
            on_ui(lambda: (app._lib_filter_var.set(LIB2), app._on_library_filter()))
            _boxes.clear(); on_ui(lambda: app._start_scan(app._scope_roots(), use_ff=False))
            check("offline: scanning only the offline library warns and changes nothing", any("offline" in str(b).lower() for b in _boxes) and not app._scanning and len(app._results) == n_lib1 + 3, _boxes)
            on_ui(lambda: (app._lib_filter_var.set(mc._ALL_LIBS), app._on_library_filter()))
        finally:
            os.rename(LIB2_OFF, LIB2)
        on_ui(lambda: app._start_quick_scan(app._scope_roots())); wait_for(lambda: not app._scanning, 60)
        check("offline: back online → flag cleared", mc._pkey(LIB2) not in app._offline_roots)
        # Libraries dialog: remove root 2 → its rows leave the table
        ld = on_ui(lambda: mc._LibrariesDialog(app))
        check("libraries dialog lists both roots", ld._items == [LIB, LIB2])
        on_ui(lambda: (ld._lb.selection_set(1), ld._remove(), ld._ok()))
        check("libraries dialog: removing a library drops its rows and saves the list", mc.SETTINGS["library_folders"] == [LIB] and not any(r["library_root"] == LIB2 for r in app._results) and json.load(open(sc.CONFIG_PATH, encoding="utf-8"))["library_folders"] == [LIB], mc.SETTINGS["library_folders"])
        check("libraries: duplicates recomputed after removal", not (({r["subfolder"]: r for r in app._results}["Perfect Movie"].get("duplicate_of") or []) and "Perfect Movie Copy2" in {r["subfolder"]: r for r in app._results}["Perfect Movie"]["duplicate_of"]))
        check("libraries: last_folder kept = first library", mc.SETTINGS["last_folder"] == LIB)
        _boxes.clear()

        # Settings dialog restores through the hook
        mc.SETTINGS["window_geometry"]["SettingsDialog"] = {"geometry": "900x700+90+60", "zoomed": False}
        _boxes.clear()

        # Settings dialog
        sd = mc.SettingsDialog(app, tab=10)
        time.sleep(0.3)
        check("settings dialog: 12 tabs", len(sd._nb.tabs()) == 12, len(sd._nb.tabs()))
        check("v0.19 SettingsDialog restored via hook", _near(_geom(sd), (900, 700, 90, 60)), _geom(sd))
        app.withdraw()
        check("settings dialog: parallel workers + duplicate rule vars", hasattr(sd, "_scan_workers_var") and "duplicate_movie" in sd._hr_vars)
        check("settings dialog: new partial rules present", "imdb_id_partial" in sd._hr_vars and "tmdb_id_partial" in sd._hr_vars)
        reg = {lbl: idx for idx, lbl, _ in mc.SettingsDialog._TAB_REGISTRY}
        check("settings menu maps every entry to an existing tab", all(t in reg for _, _, t in mc._SETTINGS_MENU_ITEMS) and reg["Health Rules"] == 10 and reg["Ratings"] == 6)
        check("snapshot unchanged → no rescan", sd._rescan_changed()["any"] is False, sd._rescan_changed())
        # Save & Apply / Cancel bar must be visible on EVERY tab (v0.18.4 regression fix)
        sd.deiconify(); sd.update()
        bar = [w for w in sd.winfo_children() if isinstance(w, tk.Frame) and w.winfo_children()
               and any(isinstance(c, tk.Frame) for c in w.winfo_children())][0]
        hidden_on = []
        for t in sd._nb.tabs():
            sd._nb.select(t); sd.update()
            if not (bar.winfo_ismapped() and bar.winfo_y() + bar.winfo_height() <= sd.winfo_height()):
                hidden_on.append(sd._nb.tab(t, "text"))
        check("Save & Apply bar visible on all 12 tabs", not hidden_on, hidden_on)
        # blank numeric fields must not break change detection or save
        sd._max_nfo_kb_var.set(""); sd._hr_int_vars["backdrop_min_count"].set("")
        try:
            ch0 = sd._rescan_changed(); blank_ok = True
        except Exception as ex:
            ch0 = {}; blank_ok = False; print("   rescan_changed raised:", ex)
        check("blank spinboxes tolerated by change detection", blank_ok and ch0.get("health_rules") is False and ch0.get("any") is False, ch0)
        sd._hr_vars["imdb_id_partial"].set(False)
        ch = sd._rescan_changed()
        check("health rule change detected", ch["health_rules"] is True and ch["image_sizes"] is False)
        # v0.19.0 — Image Sizes combo and Health Rules combo are one setting
        sd._fanart_ql_var.set("720p")
        check("v0.19 image-sizes combo mirrors the health-rule combo", sd._hr_str_vars["fanart_quality_level_minimum"].get() == "720p")
        sd._hr_str_vars["poster_folder_quality_level"].set("540p")
        check("v0.19 health-rule combo mirrors poster AND folder combos", sd._poster_ql_var.get() == "540p" and sd._folder_ql_var.get() == "540p")
        sd._hr_str_vars["poster_folder_quality_level"].set("1080p")
        applied = {"n": 0}
        _orig_apply = app._apply_health_rules_inplace
        def _spy():
            applied["n"] += 1; _orig_apply()
        app._apply_health_rules_inplace = _spy
        sd._save_close()
        wait_for(lambda: applied["n"] > 0, 5)
        app._apply_health_rules_inplace = _orig_apply
        check("Save & Apply recomputes health automatically (no prompt)", applied["n"] == 1 and mc.SETTINGS["health_rules"]["imdb_id_partial"] is False and "Health rules applied" in app._sb_action.cget("text"), (applied, app._sb_action.cget("text")))
        check("v0.19 mirrors written on save + applied in place (fanart 720p → no warning)",
              mc.SETTINGS["fanart_quality_level"] == "720p" and mc.SETTINGS["health_rules"]["fanart_quality_level_minimum"] == "720p"
              and not any("Fanart quality below minimum" in x for x in {r["subfolder"]: r for r in app._results}["Low Res Images"]["health_reasons"]),
              (mc.SETTINGS["fanart_quality_level"], {r["subfolder"]: r for r in app._results}["Low Res Images"]["health_reasons"]))
        check("blank spinboxes saved as defaults", mc.SETTINGS["max_nfo_kb"] == 50 and mc.SETTINGS["health_rules"]["backdrop_min_count"] == 5, (mc.SETTINGS["max_nfo_kb"], mc.SETTINGS["health_rules"]["backdrop_min_count"]))
        check("settings.json written with rule", json.load(open(sc.CONFIG_PATH, encoding="utf-8"))["health_rules"]["imdb_id_partial"] is False)
        by = {r["subfolder"]: r for r in app._results}
        check("table health respects the disabled rule right after save", not any("IMDB ID present in one file" in x for x in by["Partial TMDB"]["health_reasons"]), by["Partial TMDB"]["health_reasons"])
        check("no rescan prompt for a rules-only change", not any("Update Scan" in str(b) for b in _boxes))

        hd = mc.HelpDialog(app, tab=7)
        nb = [w for w in hd.winfo_children() if isinstance(w, tk.ttk.Notebook)]
        check("help dialog: 9 tabs", bool(nb) and len(nb[0].tabs()) == 9)
        hd.destroy()

        mc.SETTINGS["compact_mode"] = True; app._on_settings_changed(); time.sleep(0.5)
        check("compact mode applied to Treeview style", str(tk.ttk.Style(app).lookup("Treeview", "rowheight")) == "20", tk.ttk.Style(app).lookup("Treeview", "rowheight"))

        shared["rows"] = len(by)
        check("no error boxes during UI tests", not any(b[0] == "error" for b in _boxes), [b for b in _boxes if b[0] == "error"])
    except Exception:
        check("UI test thread crashed", False, traceback.format_exc())
    finally:
        app.after(0, lambda: (app._on_app_close()))   # closes window → mainloop returns

# remember one unchanged row object before the quick scan
def _remember():
    pass
threading.Thread(target=ui_tests, daemon=True).start()
app.mainloop()

_cfg = json.load(open(sc.CONFIG_PATH, encoding="utf-8"))
check("close: column widths saved, no rows in settings.json", _cfg["column_widths"] and _cfg["last_results"] == [])
check("close: cache has all rows", len(sc.load_results_cache()) == shared.get("rows", -1), (len(sc.load_results_cache()), shared.get("rows")))

# ══════════════════════════════════════════════════════════════════════════════
section("6. restore last session from cache on a fresh App")
mc.SETTINGS["window_geometry"]["App"] = {"geometry": "1250x650+35+45", "zoomed": False}
app2 = mc.App(); app2.withdraw()
def ui_tests2():
    try:
        wait_for(lambda: bool(app2._results), 10)
        check("fresh App restores results from last_results.json", len(app2._results) == shared.get("rows", -1), len(app2._results))
        check("restored rows get new default keys", all("nfo_title" in r and "scan_mtime" in r for r in app2._results))
        app2.deiconify(); app2.update(); time.sleep(0.3); _g2 = app2.geometry(); app2.withdraw()
        check("v0.19 fresh App restores its saved geometry", _g2.startswith("1250x650"), _g2)
    except Exception:
        check("UI test 2 crashed", False, traceback.format_exc())
    finally:
        app2.after(0, app2.destroy)
threading.Thread(target=ui_tests2, daemon=True).start()
app2.mainloop()

for fn, orig in zip(("showinfo", "showwarning", "showerror", "askyesno"), _orig_boxes):
    setattr(mc.messagebox, fn, orig)

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f_ in FAIL: print("   FAILED:", f_)
try: shutil.rmtree(_TMP, ignore_errors=True)
except Exception: pass
sys.exit(1 if FAIL else 0)
