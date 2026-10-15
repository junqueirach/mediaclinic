# =============================================================================
# selftest_v0_19_1.py
# Metadata & MediaClinic — v0.19.1 self-test
# Author:  Luiz Junqueira & Claude AI
#
# Builds a synthetic movie library in a temp folder (NFO/XML/JPEG/MKV files
# generated on the fly), then exercises scanning, health rules, Quick Scan,
# FFprobe-flag handling, the export module, the results cache, the settings
# dialog and the main window — all against an ISOLATED config directory so
# your real settings.json is never touched.
#
# RUN (from the v.0.19.1 folder):
#   python selftest_v0_19_1.py
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
    if any(os.path.isfile(os.path.join(_cand, n)) for n in ("mediaclinic.py", "mediaclinic_v0_19_1.py")):
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
    import mediaclinic_v0_19_1 as mc             # local versioned copy
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
_FIXTURE_IDS = {}            # name → {"nfo_imdb": …, "xml_imdb": …, "nfo_tmdb": …, "xml_tmdb": …}   ### NEW v0.19.1 I9 ###

def make_movie(name, nfo=True, xml=True, images=True, backdrops=6, video=True,
               poster_wh=(1000, 1500), fanart_wh=(1920, 1080), fanart_noisy=True,
               same_ids_as=None, **kw):   # v0.19.0 sizes
    d = os.path.join(LIB, name); os.makedirs(d, exist_ok=True)
    # unique IDs per movie unless the caller sets them (duplicate detection would
    # otherwise flag the whole synthetic library)
    # ### MODIFIED v0.19.1 I9 ### auto IDs come from their own range (tt7……… /
    # 7000xx), so they can never collide with the fixed IDs the fixtures use on
    # purpose (tt0000001, tt0000005, TMDb 123, 603 …).  same_ids_as="Other
    # Movie" copies that movie's IDs — the explicit way to ask for a duplicate.
    if same_ids_as is not None:
        for k, v in _FIXTURE_IDS[same_ids_as].items():
            kw.setdefault(k, v)
    n = next(_ID_SEQ)
    for side in ("nfo_", "xml_"):
        if not any(k.startswith(side) and k[4:] in ("imdb",) for k in kw) and "imdb" not in kw:
            kw.setdefault(side + "imdb", f"tt7{n:06d}")
        if not any(k.startswith(side) and k[4:] in ("tmdb",) for k in kw) and "tmdb" not in kw:
            kw.setdefault(side + "tmdb", str(700000 + n))
    _FIXTURE_IDS[name] = {k: kw[k] for k in ("nfo_imdb", "xml_imdb", "nfo_tmdb", "xml_tmdb") if k in kw}
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
M_DUP     = make_movie("Perfect Movie (copy)", title="Perfect Movie", same_ids_as="Perfect Movie")   # same IMDB id + title/year as Perfect Movie   ### MODIFIED v0.19.1 I9 ###
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
# v0.19.1 B1 — genre fixtures
M_G_XML   = make_movie("Genres Only XML", nfo_genres=(), xml_genres=("Comedy", "Family"))
M_G_NFO   = make_movie("Genres Only NFO", nfo_genres=("Drama",), xml_genres=())
M_G_WRONG = make_movie("Genres Wrong Tags", nfo_genres=(), xml_genres=("Action",))
_gw = os.path.join(M_G_WRONG, "Genres Wrong Tags.nfo"); _t = io.open(_gw, encoding="utf-8").read()
io.open(_gw, "w", encoding="utf-8", newline="\n").write(_t.replace("\t<language>", "\t<Genres>\n\t\t<Genre>Action</Genre>\n\t\t<Genre>Sci-Fi</Genre>\n\t</Genres>\n\t<language>", 1))
# v0.19.1 B5 — no genres anywhere
M_NOG1    = make_movie("No Genres TMDb", nfo_genres=(), xml_genres=(), nfo_tmdb="88801", xml_tmdb="88801", nfo_imdb="tt8880001", xml_imdb="tt8880001")
M_NOG2    = make_movie("No Genres OMDb", nfo_genres=(), xml_genres=(), nfo_tmdb="88802", xml_tmdb="88802", nfo_imdb="tt8880002", xml_imdb="tt8880002")
M_NOG3    = make_movie("No Genres No Id", nfo_genres=(), xml_genres=(), nfo_tmdb="", xml_tmdb="", nfo_imdb="", xml_imdb="")
M_NOG4    = make_movie("No Genres Wrong Film", nfo_genres=(), xml_genres=(), nfo_tmdb="88804", xml_tmdb="88804", nfo_imdb="tt8880004", xml_imdb="tt8880004")
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
check("APP_VERSION", mc.APP_VERSION == "0.19.1")

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
check("both TMDB tags empty → ○ 'Missing TMDb ID (empty tags ready to fill)' (v0.19.1 B13)", r["source_tmdb_status"] == mc.STATUS_MISSING and r["source_tmdb_empty"] is True and "Missing TMDb ID (empty tags ready to fill)" in r["health_errors"], (r["source_tmdb_status"], r["health_reasons"]))
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
    _raised = "No internet connection, or TMDb cannot be reached" in mc._tmdb_error_message(ex)   # B22 text
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

# ── v0.19.1 I2: one HTTP client for TMDb / OMDb ──────────────────────────────
section("2f. HTTP client (v0.19.1 I2)")
import urllib.error as _ue2, email.message as _em
def _http_err(code, retry_after=None, body=b"{}"):
    h = _em.Message()
    if retry_after is not None: h["Retry-After"] = str(retry_after)
    return _ue2.HTTPError("https://api.themoviedb.org/3/x?api_key=SECRETKEY123", code, "err", h, io.BytesIO(body))
_orig_fj, _orig_sl = mc._tmdb_fetch_json, mc.time.sleep
_calls = []; _sleeps2 = []
mc.time.sleep = lambda x: _sleeps2.append(x)
try:
    _seq = [_http_err(429, 2), _http_err(503), {"ok": 1}]
    def _fake(url, timeout=15):
        _calls.append(url); v = _seq.pop(0)
        if isinstance(v, Exception): raise v
        return v
    mc._tmdb_fetch_json = _fake; mc._HTTP_TIMES.clear(); mc._TMDB_RATE_TIMES.clear()
    _r = mc._http_get_json("tmdb", "https://api.themoviedb.org/3/x?api_key=SECRETKEY123")
    check("I2: 429 + 503 retried, then success", _r == {"ok": 1} and len(_calls) == 3, (len(_calls), _r))
    check("I2: Retry-After honoured (2 s), then backoff", _sleeps2[:2] == [2.0, 2.0] or _sleeps2[:2] == [2.0, 1.0] or (2.0 in _sleeps2), _sleeps2)
    _calls.clear(); _seq[:] = [_http_err(404)]
    try: mc._http_get_json("tmdb", "u"); _ok404 = False
    except _ue2.HTTPError as e: _ok404 = e.code == 404
    check("I2: 404 not retried", _ok404 and len(_calls) == 1, len(_calls))
    _calls.clear(); _seq[:] = [_http_err(500)] * 4
    try: mc._http_get_json("tmdb", "u"); _gave_up = False
    except _ue2.HTTPError: _gave_up = True
    check("I2: gives up after 3 retries (4 calls)", _gave_up and len(_calls) == 4, len(_calls))
    _calls.clear(); _seq[:] = [_ue2.URLError("getaddrinfo failed")]
    try: mc._http_get_json("tmdb", "u")
    except _ue2.URLError: pass
    check("I2: DNS failure not retried", len(_calls) == 1)
    # OMDb through the same client; key errors are "could not ask", not "no rating"
    mc._take_fetch_errors()
    _seq[:] = [{"Response": "False", "Error": "Invalid API key!"}]
    check("I2: OMDb invalid key → (None, None) + recorded as error", mc._fetch_omdb_rating("tt1", "k") == (None, None) and mc._take_fetch_errors())
    _seq[:] = [{"Response": "False", "Error": "Incorrect IMDb ID."}]
    check("I2: OMDb unknown title → no rating, not an error", mc._fetch_omdb_rating("tt1", "k") == (None, None) and not mc._take_fetch_errors())
    _seq[:] = [{"Response": "True", "imdbRating": "7.7", "imdbVotes": "1,234"}]
    check("I2: OMDb rating parsed through the client", mc._fetch_omdb_rating("tt1", "k") == ("7.7", "1234"))
    _seq[:] = [_ue2.URLError("timed out")] * 4
    check("I2: TMDb rating network failure recorded", mc._fetch_tmdb_rating("1", "k") == (None, None) and mc._take_fetch_errors())
    _seq[:] = [_http_err(404)]
    check("I2: TMDb rating 404 is 'no rating', not an error", mc._fetch_tmdb_rating("1", "k") == (None, None) and not mc._take_fetch_errors())
finally:
    mc._tmdb_fetch_json, mc.time.sleep = _orig_fj, _orig_sl
    mc._api_pauses_clear()                      # v0.19.1 B22: the 500/timeout fakes above started pauses
    mc._HTTP_TIMES.clear(); mc._TMDB_RATE_TIMES.clear()
check("I2: OMDb error messages (B22 texts)", "the free daily limit of 1,000 requests is used up" in mc._api_error_message(_http_err(401, body=b'{"Error":"Request limit reached!"}'), "OMDb") and "rejected the API key" in mc._api_error_message(_http_err(401, body=b'{"Error":"Invalid API key!"}'), "OMDb"))
check("I2: redaction helper", mc._redact("https://x/?api_key=ABC&apikey=DEF&q=1") == "https://x/?api_key=***&apikey=***&q=1")
check("I2: TMDb error message never contains the key", "SECRETKEY123" not in mc._tmdb_error_message(_ue2.URLError("boom https://api.themoviedb.org/3/x?api_key=SECRETKEY123")))
mc.logger.warning("test url https://api.themoviedb.org/3/movie/1?api_key=SECRETKEY123&language=en")
try:
    raise RuntimeError("failed https://www.omdbapi.com/?apikey=SECRETKEY456&i=tt1")
except RuntimeError:
    mc.logger.error("trace test", exc_info=True)
for _h in __import__("logging").getLogger().handlers: _h.flush()
_logtxt = io.open(mc.LOG_PATH, encoding="utf-8", errors="replace").read()
check("I2: API keys never written to app.log (message + traceback)", "SECRETKEY123" not in _logtxt and "SECRETKEY456" not in _logtxt and "api_key=***" in _logtxt and "apikey=***" in _logtxt)

# ── v0.19.1 B1: genres from NFO + XML ────────────────────────────────────────
section("2g. genres NFO/XML (v0.19.1 B1)")
mc.clear_read_caches()
r = scan(M_G_XML, use_ffprobe=False)
check("B1: XML genres used when the NFO has none", r["genres"] == ["Comedy", "Family"] and r["genre_source"] == "xml" and r["genre_status"] == mc.STATUS_OK, (r["genres"], r["genre_source"]))
check("B1: 'genres only in XML' warning, no 'Missing genre' error", "NFO has no <genre> tags (genres only in XML)" in r["health_warnings"] and not any("Missing genre" in x for x in r["health_errors"]), r["health_reasons"])
r = scan(M_G_NFO, use_ffprobe=False)
check("B1: 'genres only in NFO' warning", r["genres"] == ["Drama"] and "XML has no <Genre> tags (genres only in NFO)" in r["health_warnings"], r["health_reasons"])
r = scan(M_G_WRONG, use_ffprobe=False)
check("B1: <Genres>/<Genre> in NFO detected and used", r["genre_nfo_wrong_tags"] and r["genres"] == ["Action", "Sci-Fi"] and r["genre_source"] == "nfo_tags" and "NFO uses non-Kodi genre tags (<Genres>/<Genre>)" in r["health_warnings"], (r["genres"], r["health_warnings"]))
check("B1: Kodi reader still reads only lowercase <genre>", mc.get_genres_from_nfo(os.path.join(M_G_WRONG, "Genres Wrong Tags.nfo")) == [])
r = scan(M_OK, use_ffprobe=False)
check("B1: normal movie unchanged (source nfo, no new warnings)", r["genre_source"] == "nfo" and not any("genre" in x.lower() and "only" in x.lower() for x in r["health_reasons"]))
_codes_g = [c for c, _l in mc._auto_repair_plan(scan(M_G_XML, use_ffprobe=False), mc.SETTINGS)]
check("B1: Auto Repair plans the genre sync", "genres" in _codes_g, _codes_g)
_hr_off = dict(mc.SETTINGS["health_rules"]); _hr_off.update(genre_only_in_xml=False, genre_only_in_nfo=False, genre_nfo_wrong_tags=False)
_rr = scan(M_G_WRONG, use_ffprobe=False); mc._apply_health(_rr, _hr_off, mc.SETTINGS)
check("B1: rules OFF remove the warnings", not any("genre tags" in x or "genres only" in x for x in _rr["health_reasons"]), _rr["health_reasons"])

# ── v0.19.1 B3: library paths normalised ─────────────────────────────────────
section("2h. library paths (v0.19.1 B3)")
_cfg_tmp3 = os.path.join(_TMP, "migr3.json"); _orig_cfg3 = sc.CONFIG_PATH
try:
    sc.CONFIG_PATH = _cfg_tmp3
    json.dump({"last_folder": "z:/film_kids"}, open(_cfg_tmp3, "w", encoding="utf-8"))
    if sys.platform == "win32": check("B3: migrated last_folder uses backslashes", sc.load_settings()["library_folders"] == ["z:\\film_kids"], sc.load_settings()["library_folders"])   # Windows path style; CI runs on Linux
    json.dump({"library_folders": ["z:/film_kids", "Y:/a/b"], "library_filter": "Y:/a/b"}, open(_cfg_tmp3, "w", encoding="utf-8"))
    _m3 = sc.load_settings()
    if sys.platform == "win32": check("B3: stored forward slashes normalised on load", _m3["library_folders"] == ["z:\\film_kids", "Y:\\a\\b"] and _m3["library_filter"] == "Y:\\a\\b", (_m3["library_folders"], _m3["library_filter"]))   # Windows path style; CI runs on Linux
finally:
    sc.CONFIG_PATH = _orig_cfg3
if sys.platform == "win32": check("B3: cached rows get a normalised library_root", mc._results_from_json([{"subfolder": "x", "subfolder_path": "z:/film_kids/x", "library_root": "z:/film_kids"}])[0]["library_root"] == "z:\\film_kids")   # Windows path style; CI runs on Linux

# ── v0.19.1 B8: typed IDs ────────────────────────────────────────────────────
section("2i. typed IMDb/TMDb IDs (v0.19.1 B8)")
def _f8(url, timeout=15):
    if "/find/tt0133093" in url: return {"movie_results": [{"id": 603}]}
    if "/find/tt0000000" in url: return {"movie_results": []}
    if "/movie/603?" in url: return {"id": 603, "title": "The Matrix", "original_title": "The Matrix", "release_date": "1999-03-30", "external_ids": {"imdb_id": "tt0133093"}, "poster_path": "/p.jpg"}
    if "/movie/999999?" in url: raise _ue.HTTPError(url, 404, "nf", {}, io.BytesIO(b"{}"))
    raise AssertionError(url)
_c, _m = mc.lookup_typed_ids("tt0133093", "", "k", fetch=_f8)
check("B8: IMDb ID → TMDb film found (both IDs)", _c and _c["tmdb_id"] == "603" and _c["imdb_id"] == "tt0133093" and _c["year"] == "1999", (_c, _m))
_c, _m = mc.lookup_typed_ids("", "603", "k", fetch=_f8)
check("B8: TMDb ID → IMDb filled from external_ids", _c and _c["imdb_id"] == "tt0133093", _c)
check("B8: IMDb + TMDb of different films rejected", mc.lookup_typed_ids("tt0133094", "603", "k", fetch=_f8)[0] is None and "different films" in mc.lookup_typed_ids("tt0133094", "603", "k", fetch=_f8)[1])
check("B8: invalid formats rejected without a request", mc.lookup_typed_ids("tt12", "", "k", fetch=_f8)[0] is None and "not an IMDb ID" in mc.lookup_typed_ids("tt12", "", "k", fetch=_f8)[1] and "digits only" in mc.lookup_typed_ids("", "60a3", "k", fetch=_f8)[1])
check("B8: unknown IDs → clear message (B14: an IMDb ID unknown to TMDb is 'IMDb only')", "does not exist" in mc.lookup_typed_ids("", "999999", "k", fetch=_f8)[1] and mc.lookup_typed_ids("tt0000000", "", "k", fetch=_f8)[1] == "Not on TMDb — IMDb only")
check("B8: no key → message", "API key" in mc.lookup_typed_ids("tt0133093", "", "", fetch=_f8)[1])

# ── v0.19.1 I9: fixture factory ───────────────────────────────────────────────   ### NEW v0.19.1 I9 ###
section("2j. fixture factory (v0.19.1 I9)")
_auto = [(n, v) for n, ids in _FIXTURE_IDS.items() for k, v in ids.items() if v and (v.startswith("tt7") or v.startswith("7000"))]
_fixed = {v for n, ids in _FIXTURE_IDS.items() for k, v in ids.items() if v and not (v.startswith("tt7") or v.startswith("7000"))}
check("I9: auto IDs are unique per movie (one movie per auto ID)", all(len({n for n, v2 in _auto if v2 == v}) == 1 for _n, v in _auto), [x for x in _auto][:4])
check("I9: auto IDs never collide with the fixed fixture IDs", not ({v for _n, v in _auto} & _fixed))
check("I9: same_ids_as copies the IDs (explicit duplicate)", _FIXTURE_IDS["Perfect Movie (copy)"] == _FIXTURE_IDS["Perfect Movie"] == {"nfo_imdb": "tt0000001", "xml_imdb": "tt0000001", "nfo_tmdb": "123", "xml_tmdb": "123"}, _FIXTURE_IDS["Perfect Movie (copy)"])

# ── v0.19.1 B13: empty ID tags as placeholders ────────────────────────────────   ### NEW v0.19.1 B13 ###
section("2k. empty ID tags as placeholders (v0.19.1 B13)")
import xml.etree.ElementTree as _ET13
def _b13_files(name, nfo_body, xml_body, xml_root="Item"):
    d = os.path.join(_TMP, "b13", name); os.makedirs(d, exist_ok=True)
    n = os.path.join(d, name + ".nfo"); x = os.path.join(d, "movie.xml")
    io.open(n, "w", encoding="utf-8", newline="\n").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<movie>\n\t<title>{name}</title>\n{nfo_body}</movie>\n')
    io.open(x, "w", encoding="utf-8", newline="\n").write(f'<?xml version="1.0" encoding="utf-8"?>\n<{xml_root}>\n\t<LocalTitle>{name}</LocalTitle>\n{xml_body}</{xml_root}>\n')
    return n, x
def _txt(p): return io.open(p, encoding="utf-8").read()
def _valid(*ps):
    try:
        for p in ps: _ET13.parse(p)
        return True
    except Exception:
        return False
# 1) IMDb-only apply → empty TMDb tags in both files
_n, _x = _b13_files("Imdb Only", "", "")
ok, err = mc._write_both_source_ids(_n, _x, "tt7777001", None)
_nt, _xt = _txt(_n), _txt(_x)
check("B13: IMDb-only write → empty <tmdbid> and <id moviedb=\"tmdb\"> in the NFO", ok and "<tmdbid></tmdbid>" in _nt and '<id moviedb="tmdb"></id>' in _nt, (err, _nt))
check("B13: IMDb-only write → empty <TMDB>/<TMDbId>/<TMDB_ID> in the XML", all(f"<{t}></{t}>" in _xt for t in ("TMDB", "TMDbId", "TMDB_ID")), _xt)
check("B13: placeholders inside the root, both files valid XML", _valid(_n, _x) and _nt.rstrip().endswith("</movie>") and _xt.rstrip().endswith("</Item>"))
_s = mc.extract_source_ids_from_files(_n, _x)
check("B13: all-empty TMDb tags → ○ missing (not ✕), IMDb ⬤", _s["tmdb_status"] == mc.STATUS_MISSING and _s["tmdb_empty_tags"] is True and _s["imdb_status"] == mc.STATUS_OK, _s)
# 2) TMDb-only apply → empty IMDb tags (incl. the bare <id>)
_n, _x = _b13_files("Tmdb Only", "", "")
ok, err = mc._write_both_source_ids(_n, _x, None, "4711")
_nt, _xt = _txt(_n), _txt(_x)
check("B13: TMDb-only write → empty <imdbid>, <id moviedb=\"imdb\">, <id> and XML IMDb tags", ok and all(t in _nt for t in ("<imdbid></imdbid>", '<id moviedb="imdb"></id>', "<id></id>")) and all(f"<{t}></{t}>" in _xt for t in ("IMDB", "IMDbId", "IMDB_ID")) and _valid(_n, _x), (_nt, _xt))
# 3) filling the placeholders later: no duplicate tags, values everywhere
ok, err = mc._write_both_source_ids(_n, _x, "tt7777002", "4711")
_nt, _xt = _txt(_n), _txt(_x)
_s = mc.extract_source_ids_from_files(_n, _x)
check("B13: a later write fills the placeholders (no duplicate tags)", ok and _nt.count("<imdbid>") == 1 and _nt.count('moviedb="imdb"') == 1 and _xt.count("<IMDB>") == 1 and _s["imdb_status"] == mc.STATUS_OK and _s["tmdb_status"] == mc.STATUS_OK and "<id>tt7777002</id>" in _nt, (_s, _nt))
# 4) an existing non-empty value is never blanked; a value in one file = partial (no placeholders)
_n, _x = _b13_files("Tmdb In Xml", "", "\t<TMDB>603</TMDB>\n")
ok, err = mc._write_both_source_ids(_n, _x, "tt7777003", None)
_nt, _xt = _txt(_n), _txt(_x)
check("B13: existing TMDb value kept; no empty TMDb tags added when a value exists elsewhere", ok and "<TMDB>603</TMDB>" in _xt and "<tmdbid>" not in _nt and "<TMDbId>" not in _xt and mc.extract_source_ids_from_files(_n, _x)["tmdb_status"] == mc.STATUS_WARN, (_nt, _xt))
# 5) the user's case: XML already has empty TMDb tags, NFO has none → NFO gets them, XML not duplicated
_n, _x = _b13_files("Padre Pio Like", "\t<id>tt12817760</id>\n\t<imdbid>tt12817760</imdbid>\n",
                    "\t<IMDB>tt12817760</IMDB>\n\t<TMDbId></TMDbId>\n\t<TMDB></TMDB>\n\t<TMDB_ID></TMDB_ID>\n")
ok, err = mc._write_both_source_ids(_n, _x, "tt12817760", None)
_nt, _xt = _txt(_n), _txt(_x)
check("B13: empty XML TMDb tags kept once; NFO gets the empty TMDb tags", ok and _xt.count("<TMDB>") == 1 and _xt.count("<TMDbId>") == 1 and "<tmdbid></tmdbid>" in _nt and _valid(_n, _x), (_nt, _xt))
_r = scan(os.path.dirname(_n), use_ffprobe=False)
check("B13: row shows TMDb ○ with 'Missing TMDb ID (empty tags ready to fill)'", _r["source_tmdb_status"] == mc.STATUS_MISSING and "Missing TMDb ID (empty tags ready to fill)" in _r["health_reasons"] and _r["source_imdb_status"] == mc.STATUS_OK, (_r["source_tmdb_status"], _r["health_reasons"]))
# 6) <Title>-root movie.xml stays valid with placeholders; partly empty stays ✕
_n, _x = _b13_files("Title Root", "", "", xml_root="Title")
ok, err = mc._write_both_source_ids(_n, _x, "tt7777004", None)
check("B13: <Title>-root XML gets the placeholders inside </Title>", ok and _valid(_x) and _ET13.parse(_x).getroot().find("TMDB") is not None, _txt(_x))
_n, _x = _b13_files("Partly Empty", "\t<tmdbid>99</tmdbid>\n", "\t<TMDB></TMDB>\n")
_s = mc.extract_source_ids_from_files(_n, _x)
check("B13: some TMDb tags filled, some empty → still ✕ (not ○)", _s["tmdb_status"] == mc.STATUS_ERROR and _s["tmdb_empty_tags"] is False, _s)
# 7) Normalize Sources path: a single-type write adds the other source's placeholders
_n, _x = _b13_files("Single Type", "\t<imdbid>tt7777005</imdbid>\n", "")
ok, err = mc._write_source_id_to_files(_n, _x, "IMDB", "tt7777005")
check("B13: single-type write (Normalize Sources / Auto Repair) also leaves empty TMDb tags", ok and "<tmdbid></tmdbid>" in _txt(_n) and "<TMDB></TMDB>" in _txt(_x), _txt(_n))

# ── v0.19.1 B14: IMDb-only films (not on TMDb) ────────────────────────────────   ### NEW v0.19.1 B14 ###
section("2l. IMDb-only films in Search Sources / Enter ID (v0.19.1 B14)")
_PP_IMDB = "tt12817760"
_b14_urls = []
def _f14(url, timeout=15):
    _b14_urls.append(url)
    if f"/find/{_PP_IMDB}" in url: return {"movie_results": []}                       # not on TMDb
    if "/find/tt0133093" in url: return {"movie_results": [{"id": 603}]}
    if "/movie/603?" in url: return {"id": 603, "title": "The Matrix", "original_title": "The Matrix", "release_date": "1999-03-30", "external_ids": {"imdb_id": "tt0133093"}}
    if "/search/movie" in url:
        q = _up.unquote(_re.search(r"query=([^&]+)", url).group(1)); lg = _re.search(r"language=([\w-]+)", url).group(1)
        return {"results": {("Padre Pio, homem de Deus", "en-US"): [{"id": 11, "title": "Padre Pio"}],
                            ("Padre Pio, homem de Deus", "pt-BR"): [{"id": 11, "title": "Padre Pio"}, {"id": 12, "title": "Padre Pio 2"}],
                            ("Padre Pio, uomo di Dio", "pt-BR"): [{"id": 13, "title": "Uomo"}, {"id": 603, "title": "The Matrix"}]}.get((q, lg), [])}
    if "/external_ids" in url: return {"imdb_id": "tt00000" + _re.search(r"/movie/(\d+)/", url).group(1)}
    raise AssertionError("unexpected " + url)
_omdb14 = lambda url: {"Response": "True", "Title": "Padre Pio, uomo di Dio", "Year": "1999"} if _PP_IMDB in url else {"Response": "False"}
_c, _m = mc.lookup_typed_ids(_PP_IMDB, "", "k", fetch=_f14, omdb_key="ok", omdb_fetch=_omdb14)
check("B14: IMDb ID unknown to TMDb → IMDb-only candidate with OMDb title/year", _c and _c["imdb_only"] and _c["tmdb_id"] == "" and _c["title"] == "Padre Pio, uomo di Dio" and _c["year"] == "1999" and _m == "Not on TMDb — IMDb only", (_c, _m))
_c, _m = mc.lookup_typed_ids(_PP_IMDB, "", "k", fetch=_f14)
check("B14: without an OMDb key the IMDb-only candidate has no title (still usable)", _c and _c["imdb_only"] and _c["title"] == "", _c)
check("B14: format check still applies; IMDb + TMDb of different films still rejected", mc.lookup_typed_ids("tt12", "", "k", fetch=_f14)[0] is None and mc.lookup_typed_ids("tt0133094", "603", "k", fetch=_f14)[0] is None)
def _b14_row(name, nfo_ids, xml_ids, orig=None):
    d = os.path.join(_TMP, "b14", name); os.makedirs(d, exist_ok=True)
    _nfo(os.path.join(d, name + ".nfo"), "Padre Pio, homem de Deus", year="1999", original=orig, imdb=nfo_ids[0], tmdb=nfo_ids[1])
    _xml(os.path.join(d, "movie.xml"), "Padre Pio, homem de Deus", year="1999", original=orig, imdb=xml_ids[0], tmdb=xml_ids[1])
    return scan(d, use_ffprobe=False)
_r14 = _b14_row("PP Search", (_PP_IMDB, None), (_PP_IMDB, ""), orig="Padre Pio, uomo di Dio")
_b14_urls.clear()
_e14 = mc._search_sources_for_row(_r14, "k", "pt-BR", "ok", fetch=_f14, omdb_fetch=_omdb14)
check("B14: current IDs read from the files (IMDb tt12817760, TMDb —)", _e14["current"] == {"imdb": _PP_IMDB, "tmdb": ""}, _e14["current"])
check("B14: pinned row for the current IMDb ID even though TMDb does not know it", _e14["pinned"]["from"] == "IMDb" and _e14["pinned"]["cand"]["imdb_only"] and _e14["pinned"]["cand"]["title"] == "Padre Pio, uomo di Dio", _e14["pinned"])
_qs = [(_up.unquote(_re.search(r"query=([^&]+)", u).group(1)), _re.search(r"language=([\w-]+)", u).group(1)) for u in _b14_urls if "/search/movie" in u]
check("B14: title search in en-US, in the library language and with the original title", _qs == [("Padre Pio, homem de Deus", "en-US"), ("Padre Pio, homem de Deus", "pt-BR"), ("Padre Pio, uomo di Dio", "pt-BR")], _qs)
check("B14: results merged without duplicates", [m["tmdb_id"] for m in _e14["matches"]] == ["11", "12", "13", "603"], [m["tmdb_id"] for m in _e14["matches"]])
_r14b = _b14_row("PP Matrix Imdb", ("tt0133093", None), ("tt0133093", None))
_e14b = mc._search_sources_for_row(_r14b, "k", "en-US", "", fetch=_f14)
check("B14: IMDb ID that IS on TMDb → pinned film with both IDs ('From your current IMDb ID'), not repeated below", _e14b["pinned"]["from"] == "IMDb" and _e14b["pinned"]["cand"]["tmdb_id"] == "603" and _e14b["pinned"]["cand"]["imdb_id"] == "tt0133093" and "603" not in [m["tmdb_id"] for m in _e14b["matches"]], _e14b)
_r14c = _b14_row("PP Matrix Tmdb", ("", "603"), ("", "603"))
_e14c = mc._search_sources_for_row(_r14c, "k", "en-US", "", fetch=_f14)
check("B14: TMDb-only movie → pinned 'From your current TMDb ID' with the IMDb ID from TMDb", _e14c["pinned"]["from"] == "TMDb" and _e14c["pinned"]["cand"]["imdb_id"] == "tt0133093" and _e14c["current"] == {"imdb": "", "tmdb": "603"}, _e14c)
# id_check: verify keeps a confirmed IMDb-only film; Auto Repair stops proposing a TMDb search
_r14["id_check"] = mc._imdb_only_check(_PP_IMDB, "Padre Pio, uomo di Dio", "1999")
_v14 = mc.verify_movie_ids(_r14, "k", "pt-BR", fetch=_f14)
check("B14: Verify IDs keeps 'OK (IMDb only — not on TMDb)' while TMDb still does not know it", _v14["result"] == mc.ID_IMDB_ONLY, _v14)
_r14x = dict(_r14); _r14x["id_check"] = None
check("B14: without the confirmation Verify IDs still says 'ID does not exist'", mc.verify_movie_ids(_r14x, "k", "pt-BR", fetch=_f14)["result"] == mc.ID_NOT_FOUND)
check("B14: Auto Repair plans no TMDb search for a confirmed IMDb-only film", "ids_search" not in [c for c, _l in mc._auto_repair_plan(_r14, mc.SETTINGS)] and "ids_search" in [c for c, _l in mc._auto_repair_plan(_r14x, mc.SETTINGS)])

# ── v0.19.1 B15: hard-coded subtitles (tags) ──────────────────────────────────   ### NEW v0.19.1 B15 ###
section("2m. hard-coded subtitles (v0.19.1 B15)")
_n, _x = _b13_files("Hardsub A", "\t<tag>Favorites</tag>\n", "\t<Tags>\n\t\t<Tag>Classic</Tag>\n\t</Tags>\n")
ok, err = mc._write_hardsub_tags(_n, _x, ["eng", "SPA", "PO"])          # lower case accepted, invalid code ignored
_nt, _xt = _txt(_n), _txt(_x)
check("B15: one tag per language in both files, other tags kept", ok and "<tag>Hardsub ENG</tag>" in _nt and "<tag>Hardsub SPA</tag>" in _nt and "<tag>Favorites</tag>" in _nt
      and "<Tag>Hardsub ENG</Tag>" in _xt and "<Tag>Hardsub SPA</Tag>" in _xt and "<Tag>Classic</Tag>" in _xt and "Hardsub PO<" not in _nt, (err, _nt, _xt))
check("B15: Hardsub tags inside <movie> and inside the existing <Tags>, files valid", _valid(_n, _x) and len(_ET13.parse(_x).getroot().find("Tags").findall("Tag")) == 3 and _ET13.parse(_n).getroot().findall("tag")[-1].text == "Hardsub SPA")
check("B15: scanner reader returns the codes", mc.get_hardsub_langs(_n, _x) == ["ENG", "SPA"], mc.get_hardsub_langs(_n, _x))
ok, err = mc._write_hardsub_tags(_n, _x, ["ENG"])
_nt, _xt = _txt(_n), _txt(_x)
check("B15: unticking a language removes only that tag", ok and "Hardsub SPA" not in _nt + _xt and "<tag>Hardsub ENG</tag>" in _nt and "<Tag>Hardsub ENG</Tag>" in _xt and "<tag>Favorites</tag>" in _nt and "<Tag>Classic</Tag>" in _xt and _valid(_n, _x), (_nt, _xt))
ok, err = mc._write_hardsub_tags(_n, _x, [])
_nt, _xt = _txt(_n), _txt(_x)
check("B15: 'None' removes every Hardsub tag; <Tags> with other tags kept", ok and "<tag>Hardsub" not in _nt and "<Tag>Hardsub" not in _xt and "<Tag>Classic</Tag>" in _xt and _valid(_n, _x), _xt)
_n, _x = _b13_files("Hardsub B", "", "", xml_root="Title")
ok, err = mc._write_hardsub_tags(_n, _x, ["POR"])
check("B15: XML without <Tags> (Title root) gets a new <Tags> block inside the root", ok and _valid(_x) and [e.text for e in _ET13.parse(_x).getroot().find("Tags")] == ["Hardsub POR"], _txt(_x))
ok, err = mc._write_hardsub_tags(_n, _x, [])
check("B15: an emptied <Tags> block that held only Hardsub is removed", ok and "<Tags" not in _txt(_x) and _valid(_x), _txt(_x))
_n, _x = _b13_files("Hardsub C", "", "\t<Tags><Tag>Classic</Tag></Tags>\n")
ok, err = mc._write_hardsub_tags(_n, _x, ["ITA"])
check("B15: one-line <Tags>…</Tags> gets the tag inline", ok and _valid(_x) and [e.text for e in _ET13.parse(_x).getroot().find("Tags")] == ["Classic", "Hardsub ITA"], _txt(_x))
check("B15: Lang OK? = Y from a hard-coded target-language subtitle", mc.compute_lang_ok("x.mkv", [], [], None, None, "PT", use_ffprobe=False, subs_hard=["POR"]) == "Y" and mc.compute_lang_ok("x.mkv", [], [], None, None, "PT", use_ffprobe=False, subs_hard=["ENG"]) == "N")
_hr15 = {"health_rules": dict(mc.SETTINGS["health_rules"], required_subtitle_language=True, required_subtitle_language_code="POR")}
_row15 = {"video_count": 1, "subs_internal": [], "subs_external": [], "subs_hard": ["POR"]}
mc._apply_health(_row15, _hr15["health_rules"], mc.SETTINGS)
check("B15: 'Required subtitle language' satisfied by a hard-coded subtitle", not any("Required subtitle language" in x for x in _row15["health_reasons"]), _row15["health_reasons"])
check("B15: summary + export field 'Subtitles' show 'Hard: …'", mc._subs_summary([], [{"lang": "pt"}], "v.mkv", ["ENG", "SPA"]) == "Ext: pt | Hard: ENG, SPA"
      and export_list.build_table([{"subs_summary": "Hard: POR"}], ["subtitles"])[1][0] == ["Hard: POR"])

# ── v0.19.1 B16: audio language from NFO/XML when FFprobe has none ───────────   ### NEW v0.19.1 B16 ###
section("2n. audio language fallback (v0.19.1 B16)")
def _sd_audio(*langs):
    a = "".join(f"\t\t\t<audio><codec>aac</codec><language>{l}</language></audio>\n" for l in langs)
    return f"\t<fileinfo>\n\t\t<streamdetails>\n{a}\t\t</streamdetails>\n\t</fileinfo>\n"
_U = lambda n=1: [{"language": "UND", "codec": "AAC", "channels": "2.0", "bitrate": 128} for _ in range(n)]
_n, _x = _b13_files("Audio One", _sd_audio("por"), "")
_t1 = mc.fill_audio_lang_from_files(_U(1), _n, _x)
check("B16: one UND track + NFO streamdetails 'por' → POR (language_src NFO)", _t1[0]["language"] == "POR" and _t1[0]["language_src"] == "NFO" and _t1[0]["language_raw"] == "UND", _t1)
_t1b = mc.fill_audio_lang_from_files([{"language": "ENG"}], _n, _x)
check("B16: a language tag present in the video is never overridden", _t1b == [{"language": "ENG"}], _t1b)
_n, _x = _b13_files("Audio Two", _sd_audio("por", "eng"), "")
_t2 = mc.fill_audio_lang_from_files(_U(2), _n, _x)
check("B16: same number of languages as tracks → matched by position", [t["language"] for t in _t2] == ["POR", "ENG"], _t2)
_t2b = mc.fill_audio_lang_from_files([{"language": "ITA"}, {"language": "UND"}], _n, _x)
check("B16: position match fills only the UND track", [t["language"] for t in _t2b] == ["ITA", "ENG"] and "language_src" not in _t2b[0], _t2b)
_t3 = mc.fill_audio_lang_from_files(_U(3), _n, _x)
check("B16: ambiguous (3 tracks, 2 different languages) → stays UND", [t["language"] for t in _t3] == ["UND"] * 3 and not any("language_src" in t for t in _t3), _t3)
_n, _x = _b13_files("Audio Single", _sd_audio("por"), "")
check("B16: two UND tracks but one listed language → stays UND (no guessing)", [t["language"] for t in mc.fill_audio_lang_from_files(_U(2), _n, _x)] == ["UND", "UND"])
_n, _x = _b13_files("Audio Same", _sd_audio("por", "por"), "")
check("B16: several listed languages all the same → used for every UND track", [t["language"] for t in mc.fill_audio_lang_from_files(_U(3), _n, _x)] == ["POR"] * 3)
_n, _x = _b13_files("Audio Xml", "", "\t<MediaInfo>\n\t\t<Audio>\n\t\t\t<Language>Portuguese</Language>\n\t\t</Audio>\n\t</MediaInfo>\n")
_tx = mc.fill_audio_lang_from_files(_U(1), _n, _x)
check("B16: XML MediaInfo/Audio/Language 'Portuguese' → POR (language_src XML)", _tx[0]["language"] == "POR" and _tx[0]["language_src"] == "XML", _tx)
_n, _x = _b13_files("Audio Video Lang", "\t<fileinfo><streamdetails><video><language>spa</language></video></streamdetails></fileinfo>\n", "")
check("B16: NFO <video><language> used as the last fallback", mc.fill_audio_lang_from_files(_U(1), _n, _x)[0]["language"] == "SPA")
_n, _x = _b13_files("Audio Refill", _sd_audio("eng"), "")
_tr = mc.fill_audio_lang_from_files([{"language": "POR", "language_src": "NFO", "language_raw": "UND"}], _n, _x)
check("B16: an earlier fill is redone from scratch (edited NFO picked up)", _tr[0]["language"] == "ENG" and _tr[0]["language_src"] == "NFO", _tr)
_n, _x = _b13_files("Audio Nothing", "", "")
check("B16: no language in the files → stays UND, nothing written", mc.fill_audio_lang_from_files(_U(1), _n, _x)[0]["language"] == "UND" and "Hardsub" not in _txt(_n) and "<audio>" not in _txt(_n))
_rr16 = {"audio_tracks": _U(1), "nfo_exists": True, "nfo_path": os.path.join(_TMP, "b13", "Audio One", "Audio One.nfo"),
         "xml_exists": False, "video_path": "v.mkv", "lang_ok": "N", "video_count": 1}
mc._refill_audio_row(_rr16)
check("B16: filled target-language track → Lang OK? = Y", _rr16["lang_ok"] == "Y" and _rr16["audio_tracks"][0]["language"] == "POR")
_rr16["subs_internal"] = []; _rr16["subs_external"] = []
mc._apply_health(_rr16, dict(mc.SETTINGS["health_rules"], required_audio_language=True, required_audio_language_code="POR"), mc.SETTINGS)
check("B16: 'Required audio language' rule uses the filled language", not any("Required audio language" in x for x in _rr16["health_reasons"]), _rr16["health_reasons"])
if SAMPLE_VIDEO:
    _und_vid = os.path.join(_TMP, "sample_und.mkv")
    _rc = subprocess.run([mc.FFMPEG_PATH, "-y", "-loglevel", "error", "-i", SAMPLE_VIDEO, "-c", "copy",
                          "-metadata:s:a:0", "language=und", _und_vid], capture_output=True, timeout=60,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    _d16 = os.path.join(_TMP, "b16", "Und Audio Movie"); os.makedirs(_d16, exist_ok=True)
    shutil.copy2(_und_vid, os.path.join(_d16, "Und Audio Movie.mkv"))
    _nfo(os.path.join(_d16, "Und Audio Movie.nfo"), "Und Audio Movie", imdb="tt7716001", tmdb="716001", extra=_sd_audio("por"))
    _xml(os.path.join(_d16, "movie.xml"), "Und Audio Movie", imdb="tt7716001", tmdb="716001")
    _r16 = scan(_d16, use_ffprobe=True)
    check("B16: real video without an audio language tag → POR from the NFO (FFprobe primary)", _r16["audio_tracks"] and _r16["audio_tracks"][0]["language"] == "POR" and _r16["audio_tracks"][0].get("language_src") == "NFO", _r16["audio_tracks"])
    _r16b = scan(M_OK, use_ffprobe=True)
    check("B16: real video WITH a language tag keeps it (ENG, no language_src)", _r16b["audio_tracks"][0]["language"] == "ENG" and "language_src" not in _r16b["audio_tracks"][0], _r16b["audio_tracks"])

# ── v0.19.1 B24: how a missing source is reported ─────────────────────────────   ### NEW v0.19.1 B24 ###
section("2o. single-source / no-source severity (v0.19.1 B24)")
check("B24: new keys default to 'error' (behaviour unchanged)", DEFAULT_SETTINGS["health_rules"]["single_source_level"] == "error" and DEFAULT_SETTINGS["health_rules"]["no_source_level"] == "error")
_r24 = scan(os.path.join(_TMP, "b14", "PP Search"), use_ffprobe=False)        # IMDb only
_r24n = scan(M_NOG3, use_ffprobe=False)                                       # no IMDb, no TMDb
def _lv(row, **kw):
    r = dict(row); mc._apply_health(r, dict(mc.SETTINGS["health_rules"], **kw), mc.SETTINGS); return r
_a = _lv(_r24)
check("B24: one source + 'error' → 'Missing TMDb ID…' is an error", any(x.startswith("Missing TMDb ID") for x in _a["health_errors"]), _a["health_reasons"])
_a = _lv(_r24, single_source_level="warning")
check("B24: one source + 'warning' → reported as a warning, not an error", any(x.startswith("Missing TMDb ID") for x in _a["health_warnings"]) and not any(x.startswith("Missing TMDb ID") for x in _a["health_errors"]), (_a["health_errors"], _a["health_warnings"]))
_a = _lv(_r24, single_source_level="off")
check("B24: one source + 'off' → not reported at all", not any("Missing TMDb ID" in x or "Missing IMDB ID" in x for x in _a["health_reasons"]), _a["health_reasons"])
_a = _lv(_r24n, single_source_level="off")
check("B24: no source + 'error' (single 'off') → both missing IDs are errors", sum(1 for x in _a["health_errors"] if x.startswith("Missing ")) >= 2 and any("IMDB" in x for x in _a["health_errors"]), _a["health_errors"])
_a = _lv(_r24n, no_source_level="warning")
check("B24: no source + 'warning' → both as warnings", any(x.startswith("Missing IMDB ID") for x in _a["health_warnings"]) and any(x.startswith("Missing TMDb ID") for x in _a["health_warnings"]) and not any(x.startswith("Missing ") and " ID" in x for x in _a["health_errors"]), (_a["health_errors"], _a["health_warnings"]))
_a = _lv(_r24n, no_source_level="off")
check("B24: no source + 'off' → not reported", not any(x.startswith("Missing IMDB ID") or x.startswith("Missing TMDb ID") for x in _a["health_reasons"]), _a["health_reasons"])
_a = _lv(_r24, single_source_level="warning", missing_tmdb_id=False)
check("B24: the 'Missing TMDb ID' checkbox OFF still switches the reason off", not any("Missing TMDb ID" in x for x in _a["health_reasons"]))
check("B24: Auto Repair plans no TMDb search when the level is 'off'", "ids_search" not in [c for c, _l in mc._auto_repair_plan(_r24, mc.SETTINGS, dict(mc.SETTINGS["health_rules"], single_source_level="off"))]
      and "ids_search" in [c for c, _l in mc._auto_repair_plan(_r24, mc.SETTINGS, dict(mc.SETTINGS["health_rules"], single_source_level="warning"))])

# ── v0.19.1 B23: Kodi artwork + NFO naming ────────────────────────────────────   ### NEW v0.19.1 B23 ###
section("2p. Kodi naming (v0.19.1 B23)")
def _kodi_dir(folder, video, files):
    """files: {name: ("jpg"|"png", w, h) | "nfo" | "tbn"}"""
    d = os.path.join(_TMP, "b23", folder); os.makedirs(d, exist_ok=True)
    if video:
        open(os.path.join(d, video), "wb").write(b"\0" * 1024)
    for name, spec in files.items():
        fp = os.path.join(d, name)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        if spec == "nfo":
            _nfo(fp, folder, imdb="tt7723001", tmdb="723001")
        elif spec == "xml":
            _xml(fp, folder, imdb="tt7723001", tmdb="723001")
        else:
            kind, w, h = spec
            from PIL import Image as _I23
            _I23.frombytes("RGB", (w, h), os.urandom(w * h * 3)).save(fp, "PNG" if kind == "png" else "JPEG", quality=90)
    return d
_P, _F = ("jpg", 1000, 1500), ("jpg", 1920, 1080)
_k1 = _kodi_dir("Kodi Movie (1999)", "Kodi Movie (1999).mkv",
                {"Kodi Movie (1999).nfo": "nfo", "movie.xml": "xml", "Kodi Movie (1999)-poster.jpg": _P, "Kodi Movie (1999)-fanart.jpg": _F})
_r = scan(_k1, use_ffprobe=False)
check("B23: '<video>-poster.jpg' and '-fanart.jpg' found (not Missing), Kodi style", _r["poster_exists"] and _r["fanart_exists"] and os.path.basename(_r["poster_path"]) == "Kodi Movie (1999)-poster.jpg" and _r["poster_style"] == "kodi" and _r["art_style"] == "kodi", (_r["poster_path"], _r["poster_style"]))
check("B23: no 'Missing poster/fanart'; folder.jpg optional with a Kodi poster (rule ON)", not any(x in ("Missing poster", "Missing fanart", "Missing folder image") for x in _r["health_reasons"]), _r["health_reasons"])
_rr = dict(_r); mc._apply_health(_rr, dict(mc.SETTINGS["health_rules"], folder_optional_with_kodi_poster=False), mc.SETTINGS)
check("B23: rule OFF → 'Missing folder image' reported again", "Missing folder image" in _rr["health_reasons"])
_k2 = _kodi_dir("Kodi Png (2001)", "Kodi Png (2001).mkv",
                {"Kodi Png (2001).nfo": "nfo", "Kodi Png (2001)-poster.png": ("png", 1000, 1500), "Kodi Png (2001)-fanart.png": ("png", 1920, 1080)})
_r = scan(_k2, use_ffprobe=False)
check("B23: PNG variant found, PNG format, no extension-mismatch warning", _r["poster_exists"] and _r["fanart_exists"] and _r["poster_format"] == "PNG" and not any("extension mismatch" in x for x in _r["health_reasons"]), (_r["poster_path"], _r["health_reasons"]))
_k3 = _kodi_dir("Kodi Export", "Kodi.Export.1999.1080p.BluRay.mkv",
                {"Kodi.Export.1999.1080p.BluRay.nfo": "nfo", "Kodi.Export.1999.1080p.BluRay-poster.jpg": _P, "Kodi.Export.1999.1080p.BluRay-fanart.jpg": _F})
_r = scan(_k3, use_ffprobe=False)
check("B23: Kodi export — NFO '<video>.nfo' found although the folder has another name", _r["nfo_exists"] and os.path.basename(_r["nfo_path"]) == "Kodi.Export.1999.1080p.BluRay.nfo" and "Missing NFO file" not in _r["health_reasons"] and _r["poster_exists"], (_r["nfo_path"], _r["health_reasons"]))
_k4 = _kodi_dir("Kodi Legacy", "Legacy.mkv", {"movie.nfo": "nfo", "movie.tbn": _P})
_r = scan(_k4, use_ffprobe=False)
check("B23: movie.nfo + legacy movie.tbn poster found", _r["nfo_exists"] and os.path.basename(_r["nfo_path"]) == "movie.nfo" and _r["poster_exists"] and os.path.basename(_r["poster_path"]) == "movie.tbn" and _r["poster_style"] == "kodi", (_r["nfo_path"], _r["poster_path"]))
_k5 = _kodi_dir("Folder Named Nfo", "Other.Name.mkv", {"Folder Named Nfo.nfo": "nfo", "poster.jpg": _P})
_r = scan(_k5, use_ffprobe=False)
check("B23: NFO only as '<folder>.nfo' while the video is named differently → Kodi warning", _r["nfo_exists"] and _r["nfo_kodi_name"] is False and any("Kodi reads '<video file name>.nfo'" in x for x in _r["health_warnings"]), _r["health_warnings"])
_rr = dict(_r); mc._apply_health(_rr, dict(mc.SETTINGS["health_rules"], nfo_name_not_kodi=False), mc.SETTINGS)
check("B23: NFO-name rule OFF removes that warning", not any("Kodi reads" in x for x in _rr["health_reasons"]))
check("B23: normal MediaClinic movie (video named like the folder) → no NFO warning, plain style", (lambda r: r["nfo_kodi_name"] is True and r["poster_style"] == "plain" and os.path.basename(r["poster_path"]).lower() == "poster.jpg")(scan(M_OK, use_ffprobe=False)))
_k6 = _kodi_dir("Kodi Mixed", "Kodi Mixed.mkv", {"Kodi Mixed.nfo": "nfo", "poster.jpg": ("jpg", 600, 900), "Kodi Mixed-poster.jpg": _P})
_r = scan(_k6, use_ffprobe=False)
check("B23: mixed folder → the '<video>-poster' Kodi prefers is the one shown", os.path.basename(_r["poster_path"]) == "Kodi Mixed-poster.jpg" and _r["poster_dim"] == "1000×1500", (_r["poster_path"], _r["poster_dim"]))
_k7 = _kodi_dir("Kodi Extra Fanart", "Kodi Extra Fanart.mkv", {"Kodi Extra Fanart.nfo": "nfo", "Kodi Extra Fanart-fanart.jpg": _F, "fanart1.jpg": _F,
                "Kodi Extra Fanart-fanart2.jpg": _F, os.path.join("extrafanart", "a.jpg"): _F, os.path.join("extrafanart", "b.png"): ("png", 1280, 720), "backdrop.jpg": _F})
_r = scan(_k7, use_ffprobe=False)
check("B23: Kodi extra fanart counted as backdrops (fanart1, <video>-fanart2, extrafanart/*)", _r["backdrop_count"] == 5 and os.path.basename(_r["backdrop_paths"][0]) == "backdrop.jpg", (_r["backdrop_count"], [os.path.basename(p) for p in _r["backdrop_paths"]]))
# write targets
check("B23: Fetch Poster in a Kodi folder writes '<video>-poster.jpg' only (no folder.jpg created)", mc.artwork_targets_for_fetch(_k1, "poster") == ([os.path.join(_k1, "Kodi Movie (1999)-poster.jpg")], []), mc.artwork_targets_for_fetch(_k1, "poster"))
check("B23: Fetch Poster in a plain folder still writes poster.jpg + folder.jpg", [os.path.basename(x) for x in mc.artwork_targets_for_fetch(M_OK, "poster")[0]] == ["poster.jpg", "folder.jpg"], mc.artwork_targets_for_fetch(M_OK, "poster"))
check("B23: an existing '-poster.png' → write the '.jpg' of the same name, remove the .png after", mc.artwork_write_target(_k2, "poster") == (os.path.join(_k2, "Kodi Png (2001)-poster.jpg"), os.path.join(_k2, "Kodi Png (2001)-poster.png")))
check("B23: legacy movie.tbn kept; new poster written as '<video>-poster.jpg' (Kodi's first choice)", mc.artwork_write_target(_k4, "poster") == (os.path.join(_k4, "Legacy-poster.jpg"), None), mc.artwork_write_target(_k4, "poster"))
check("B23: Fetch Fanart in a Kodi folder writes '<video>-fanart.jpg'", mc.artwork_targets_for_fetch(_k3, "fanart")[0] == [os.path.join(_k3, "Kodi.Export.1999.1080p.BluRay-fanart.jpg")])
_kodi_png_poster = os.path.join(_k2, "Kodi Png (2001)-poster.png"); _fj = os.path.join(_k2, "folder.jpg")
mc._copy_image_as(_kodi_png_poster, _fj)
check("B23: Copy poster → folder converts a PNG poster to a real JPEG folder.jpg", mc.probe_image(_fj)["format"] == "JPEG" and mc.probe_image(_fj)["w"] == 1000)
_r = scan(_k2, use_ffprobe=False)
check("B23: PNG poster + converted folder.jpg with the same size → not 'different images'", not any("Poster and folder image are different" in x for x in _r["health_reasons"]), _r["health_reasons"])

# ── v0.19.1 B23 (2): DVD / Blu-ray structures + Kodi backdrop names ──────────   ### NEW v0.19.1 B23 ###
section("2q. disc folders + Kodi backdrop names (v0.19.1 B23)")
def _bin(path, size):
    os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "wb").write(b"\0" * size)
_dvd = _kodi_dir("DVD Movie (1990)", None, {os.path.join("VIDEO_TS", "VIDEO_TS-poster.jpg"): _P, os.path.join("VIDEO_TS", "VIDEO_TS.nfo"): "nfo", "fanart.jpg": _F})
_bin(os.path.join(_dvd, "VIDEO_TS", "VIDEO_TS.IFO"), 2048); _bin(os.path.join(_dvd, "VIDEO_TS", "VTS_01_0.VOB"), 4096); _bin(os.path.join(_dvd, "VIDEO_TS", "VTS_01_1.VOB"), 9000)
_r = scan(_dvd, use_ffprobe=False)
check("B23 disc: DVD (VIDEO_TS) counts as the video — no 'Missing video file', type DVD, largest VOB probed", _r["video_count"] == 1 and _r["video_ext"] == "DVD" and os.path.basename(_r["video_path"]) == "VTS_01_1.VOB" and "Missing video file" not in _r["health_reasons"], (_r["video_ext"], _r["video_path"], _r["health_reasons"]))
check("B23 disc: VIDEO_TS\\VIDEO_TS-poster.jpg found (Kodi naming), fanart.jpg in the movie folder found", _r["poster_exists"] and os.path.basename(_r["poster_path"]) == "VIDEO_TS-poster.jpg" and _r["poster_style"] == "kodi" and _r["fanart_exists"], (_r["poster_path"], _r["fanart_path"]))
check("B23 disc: VIDEO_TS.nfo found and read by Kodi", _r["nfo_exists"] and os.path.basename(_r["nfo_path"]) == "VIDEO_TS.nfo" and _r["nfo_kodi_name"] is True, _r["nfo_path"])
check("B23 disc: Fetch Poster writes VIDEO_TS\\VIDEO_TS-poster.jpg", mc.artwork_targets_for_fetch(_dvd, "poster")[0] == [os.path.join(_dvd, "VIDEO_TS", "VIDEO_TS-poster.jpg")])
_dvd2 = _kodi_dir("DVD Flat", None, {"movie.nfo": "nfo", "poster.jpg": _P})
_bin(os.path.join(_dvd2, "VIDEO_TS.IFO"), 2048); _bin(os.path.join(_dvd2, "VTS_01_1.VOB"), 5000)
_r = scan(_dvd2, use_ffprobe=False)
check("B23 disc: VIDEO_TS.IFO directly in the movie folder + movie.nfo + poster.jpg", _r["video_ext"] == "DVD" and os.path.basename(_r["nfo_path"]) == "movie.nfo" and _r["poster_exists"] and _r["poster_style"] == "plain", (_r["video_ext"], _r["nfo_path"]))
check("B23 disc: plain disc folder → Fetch Poster writes poster.jpg + folder.jpg", [os.path.basename(x) for x in mc.artwork_targets_for_fetch(_dvd2, "poster")[0]] == ["poster.jpg", "folder.jpg"])
_bd = _kodi_dir("BluRay Movie (2010)", None, {os.path.join("BDMV", "index-poster.png"): ("png", 1000, 1500), os.path.join("BDMV", "index.nfo"): "nfo", os.path.join("BDMV", "index-fanart.jpg"): _F})
_bin(os.path.join(_bd, "BDMV", "index.bdmv"), 1024); _bin(os.path.join(_bd, "BDMV", "STREAM", "00001.m2ts"), 3000); _bin(os.path.join(_bd, "BDMV", "STREAM", "00002.m2ts"), 8000)
_r = scan(_bd, use_ffprobe=False)
check("B23 disc: Blu-ray (BDMV) — video, index-poster.png, index-fanart.jpg, index.nfo all found", _r["video_ext"] == "BLU-RAY" and os.path.basename(_r["video_path"]) == "00002.m2ts" and os.path.basename(_r["poster_path"]) == "index-poster.png"
      and os.path.basename(_r["fanart_path"]) == "index-fanart.jpg" and os.path.basename(_r["nfo_path"]) == "index.nfo", (_r["video_path"], _r["poster_path"], _r["nfo_path"]))
_dvd3 = _kodi_dir("DVD Folder Nfo", None, {"DVD Folder Nfo.nfo": "nfo"})
_bin(os.path.join(_dvd3, "VIDEO_TS", "VIDEO_TS.IFO"), 2048)
_r = scan(_dvd3, use_ffprobe=False)
check("B23 disc: '<folder>.nfo' next to a DVD structure → 'Kodi reads …' warning", _r["nfo_exists"] and _r["nfo_kodi_name"] is False and any("Kodi reads" in x for x in _r["health_warnings"]), _r["health_warnings"])
if SAMPLE_VIDEO:
    _dvd4 = os.path.join(_TMP, "b23", "DVD Real Video"); os.makedirs(os.path.join(_dvd4, "VIDEO_TS"), exist_ok=True)
    _bin(os.path.join(_dvd4, "VIDEO_TS", "VIDEO_TS.IFO"), 2048)
    shutil.copy2(SAMPLE_VIDEO, os.path.join(_dvd4, "VIDEO_TS", "VTS_01_1.VOB"))
    _r = scan(_dvd4, use_ffprobe=True)
    check("B23 disc: FFprobe reads the VOB (resolution + audio)", _r["video_quality"] == "720p" and _r["audio_tracks"], (_r["video_quality"], _r["audio_tracks"]))
# backdrop names in the folder's style
check("B23 backdrops: Kodi folder → new backdrops '<video>-fanart1.jpg', '-fanart2.jpg'", [os.path.basename(x) for x in mc.new_backdrop_paths(_k1, 2)] == ["Kodi Movie (1999)-fanart1.jpg", "Kodi Movie (1999)-fanart2.jpg"])
check("B23 backdrops: numbers already used are skipped (fanart1, -fanart2 exist → 3, 4)", [os.path.basename(x) for x in mc.new_backdrop_paths(_k7, 2)] == ["Kodi Extra Fanart-fanart3.jpg", "Kodi Extra Fanart-fanart4.jpg"], mc.new_backdrop_paths(_k7, 2))
check("B23 backdrops: plain folder unchanged (backdrop.jpg … backdrop5.jpg exist → backdrop6.jpg)", [os.path.basename(x) for x in mc.new_backdrop_paths(M_OK, 1)] == ["backdrop6.jpg"])
check("B23 backdrops: Kodi disc folder → fanart1.jpg in the movie folder", [os.path.basename(x) for x in mc.new_backdrop_paths(_dvd, 1)] == ["fanart1.jpg"] and os.path.dirname(mc.new_backdrop_paths(_dvd, 1)[0]) == _dvd)
check("B23 backdrops: Replace All replaces Kodi extra fanart in a Kodi folder (not backdrop.jpg, not the main fanart)", sorted(os.path.basename(x) for x in mc.replaceable_backdrops(_k7)) == ["Kodi Extra Fanart-fanart2.jpg", "a.jpg", "b.png", "fanart1.jpg"], [os.path.basename(x) for x in mc.replaceable_backdrops(_k7)])
check("B23 backdrops: Replace All in a plain folder = backdrop*.jpg as before", len(mc.replaceable_backdrops(M_OK)) == 6)
_jpeg(os.path.join(_dvd, "VIDEO_TS", "VIDEO_TS-fanart1.jpg"), 1920, 1080)
check("B23 backdrops: 'VIDEO_TS-fanart1.jpg' next to the IFO is counted", scan(_dvd, use_ffprobe=False)["backdrop_count"] == 1)

# ── v0.19.1 B19: Kodi <uniqueid> ID tags ──────────────────────────────────────   ### NEW v0.19.1 B19 ###
section("2r. Kodi <uniqueid> tags (v0.19.1 B19)")
def _uid_nfo(name, body):
    d = os.path.join(_TMP, "b19", name); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name + ".nfo")
    io.open(p, "w", encoding="utf-8", newline="\n").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<movie>\n\t<title>{name}</title>\n{body}</movie>\n')
    return p
_u1 = _uid_nfo("Uid Only", '\t<uniqueid type="imdb" default="true">tt7719001</uniqueid>\n\t<uniqueid type="tmdb">719001</uniqueid>\n')
_s = mc.extract_source_ids_from_files(_u1, None)
check("B19: NFO with only <uniqueid> tags → both IDs found (⬤)", _s["imdb_val"] == "tt7719001" and _s["tmdb_val"] == "719001" and _s["imdb_status"] == mc.STATUS_OK and _s["tmdb_status"] == mc.STATUS_OK, _s)
check("B19: get_movie_ids_robust reads <uniqueid> too", mc.get_movie_ids_robust(_u1, None) == ("tt7719001", "719001"))
_u2 = _uid_nfo("Uid Conflict", '\t<uniqueid type="imdb" default="true">tt7719002</uniqueid>\n\t<imdbid>tt7719003</imdbid>\n\t<id>tt7719003</id>\n')
_s = mc.extract_source_ids_from_files(_u2, None)
check("B19: a <uniqueid> that disagrees with the other tags is a conflict", set(_s["imdb_all_vals"]) == {"tt7719002", "tt7719003"} and _s["imdb_status"] == mc.STATUS_WARN, _s)
_ru = scan(os.path.dirname(_u2), use_ffprobe=False)
check("B19: health reports the IMDb conflict (both values named)", any("IMDB ID conflict" in x and "tt7719002" in x and "tt7719003" in x for x in _ru["health_reasons"]), _ru["health_reasons"])
check("B19: Kodi's default=\"true\" uniqueid is the ID used (Kodi reads it first)", mc.get_movie_ids_robust(_u2, None)[0] == "tt7719002")
ok, err = mc._write_source_id_to_files(_u2, None, "IMDB", "tt7719009")
_t = _txt(_u2)
check("B19: Apply/Normalize updates the existing <uniqueid> (default attr kept), conflict gone", ok and '<uniqueid type="imdb" default="true">tt7719009</uniqueid>' in _t and _t.count("<uniqueid") == 1 and len(set(mc.extract_source_ids_from_files(_u2, None)["imdb_all_vals"])) == 1, _t)
_u3 = _uid_nfo("No Uid", '\t<imdbid>tt7719004</imdbid>\n')
ok, err = mc._write_both_source_ids(_u3, None, "tt7719004", "719004")
check("B19: an NFO without <uniqueid> never gets one added", ok and "<uniqueid" not in _txt(_u3) and "<tmdbid>719004</tmdbid>" in _txt(_u3), _txt(_u3))
_u4 = _uid_nfo("Uid Selfclose", '\t<uniqueid type="imdb" default="true">tt7719005</uniqueid>\n\t<uniqueid type="tmdb" />\n')
_s = mc.extract_source_ids_from_files(_u4, None)
check("B19: an empty <uniqueid type=\"tmdb\"/> counts as an empty tag (○, ready to fill)", _s["tmdb_status"] == mc.STATUS_MISSING and _s["tmdb_empty_tags"] is True, _s)
ok, err = mc._write_source_id_to_files(_u4, None, "TMDB", "719005")
_t = _txt(_u4)
check("B19: the self-closing <uniqueid type=\"tmdb\"/> is filled in place", ok and '<uniqueid type="tmdb">719005</uniqueid>' in _t and _t.count('type="tmdb"') == 1 and _valid(_u4), _t)
_u5 = _uid_nfo("Uid Themoviedb", '\t<uniqueid type="themoviedb">719006</uniqueid>\n')
check("B19: type=\"themoviedb\" accepted as TMDb", mc.extract_source_ids_from_files(_u5, None)["tmdb_val"] == "719006")

# ── v0.19.1 B20: a service that refuses is not asked again in the run ─────────   ### NEW v0.19.1 B20 ###
section("2s. refused service blocked for the run (v0.19.1 B20)")
_calls20 = []
_mode20 = {"omdb": "limit", "tmdb": "ok"}
def _fake20(url, timeout=15):
    _calls20.append(url)
    if "omdbapi" in url:
        if _mode20["omdb"] == "limit":
            return {"Response": "False", "Error": "Request limit reached!"}
        if _mode20["omdb"] == "timeout":
            raise _ue2.URLError("timed out")
        return {"Response": "True", "imdbRating": "8.0", "imdbVotes": "900"}
    if _mode20["tmdb"] == "401":
        raise _http_err(401, body=b'{"status_message":"Invalid API key: You must be granted a valid key."}')
    return {"vote_average": 7.0, "vote_count": 100}
_omdb_n = lambda: sum(1 for u in _calls20 if "omdbapi" in u)
_ofj20, _osl20 = mc._tmdb_fetch_json, mc.time.sleep
mc._tmdb_fetch_json = _fake20; mc.time.sleep = lambda x: None
mc._HTTP_TIMES.clear(); mc._TMDB_RATE_TIMES.clear()
try:
    mc._service_run_begin()
    _res20 = [mc._fetch_omdb_rating(f"tt77200{i}", "k") for i in range(4)]
    check("B20: OMDb 'Request limit reached!' → asked ONCE in the run (not once per movie)", _omdb_n() == 1 and all(r == (None, None) for r in _res20), _omdb_n())
    check("B20: OMDb marked unavailable (daily limit) for the run", mc._service_blocked("omdb") == "daily_limit")
    _sum20 = mc._service_run_summary()
    check("B20: the final message names it once (+ B22 advice)", len(_sum20) == 1 and _sum20[0].startswith("OMDb (IMDb data) unavailable for the rest of this run (daily request limit reached) — not asked again (3 request(s) saved).") and "Try again in a few hours or tomorrow" in _sum20[0], _sum20)
    _errs20 = mc._take_fetch_errors()
    check("B20: the skipped movies are noted as 'OMDb (IMDb data) unavailable (daily request limit reached)'",
          sum(1 for x in _errs20 if "OMDb (IMDb data) unavailable (daily request limit reached)" in x) == 3, _errs20)
    mc._service_run_end()
    mc._api_pauses_clear()                      # B22: the daily-limit pause is tested in 2t
    _calls20.clear(); mc._service_run_begin()
    mc._fetch_omdb_rating("tt7720010", "k"); mc._fetch_omdb_rating("tt7720011", "k")
    check("B20: a new run asks again (once)", _omdb_n() == 1)
    mc._service_run_end()
    _calls20.clear()
    mc._fetch_omdb_rating("tt7720012", "k"); mc._fetch_omdb_rating("tt7720013", "k")
    check("B20: outside a batch run (single movie) nothing is blocked", _omdb_n() == 2 and mc._service_blocked("omdb") is None)
    mc._api_pauses_clear()
    _calls20.clear(); _mode20["omdb"] = "timeout"
    mc._fetch_omdb_rating("tt7720014", "k"); mc._fetch_omdb_rating("tt7720015", "k")
    check("B20: outside a run, timeouts are retried per request (4 tries each)", _omdb_n() == 8, _omdb_n())
    mc._api_pauses_clear(); _calls20.clear(); mc._service_run_begin()
    mc._fetch_omdb_rating("tt7720016", "k"); mc._fetch_omdb_rating("tt7720017", "k")
    check("B22: in a run, repeated timeouts pause OMDb — the next movie is not asked (no failing movie by movie)", _omdb_n() == 4 and mc._service_blocked("omdb") == "timeout" and mc.api_pause_get("omdb")["kind"] == "timeout", (_omdb_n(), mc._service_blocked("omdb")))
    mc._service_run_end(); mc._api_pauses_clear()
    mc._service_run_end()
    _calls20.clear(); _mode20.update(omdb="ok", tmdb="401"); mc._service_run_begin()
    mc._fetch_tmdb_rating("720001", "k"); mc._fetch_tmdb_rating("720002", "k")
    check("B20: TMDb 'invalid API key' (HTTP 401) → blocked after the first answer", len(_calls20) == 1 and mc._service_blocked("tmdb") == "invalid_key", (len(_calls20), mc._service_blocked("tmdb")))
    try:
        mc._tmdb_rate_limited_fetch("https://api.themoviedb.org/3/movie/1?api_key=SECRET"); _su = None
    except mc.ServiceUnavailable as ex:
        _su = str(ex)
    check("B20: a blocked service raises ServiceUnavailable with a clear text (no key in it)", _su == "TMDb unavailable (API key rejected)" and "SECRET" not in (_su or ""), _su)
    mc._service_run_end()
finally:
    mc._tmdb_fetch_json, mc.time.sleep = _ofj20, _osl20
    mc._service_run_end(); mc._HTTP_TIMES.clear(); mc._TMDB_RATE_TIMES.clear()
    mc._api_pauses_clear()

# ── v0.19.1 B22: failure kinds, messages, pauses ──────────────────────────────   ### NEW v0.19.1 B22 ###
section("2t. TMDb/OMDb failure messages + pauses (v0.19.1 B22)")
_cases22 = [("tmdb", _http_err(429), "rate_limited"), ("omdb", _http_err(401, body=b'{"Error":"Request limit reached!"}'), "daily_limit"),
            ("tmdb", _http_err(401, body=b'{"status_message":"Invalid API key"}'), "invalid_key"), ("tmdb", _http_err(503), "server_error"),
            ("tmdb", _ue2.URLError("timed out"), "timeout"), ("tmdb", _ue2.URLError("getaddrinfo failed"), "offline"), ("tmdb", _http_err(404), None)]
_got22 = [mc.classify_api_failure(s, exc=e) for s, e, _k in _cases22]
check("B22: every failure is classified (rate_limited, daily_limit, invalid_key, server_error, timeout, offline; 404 = none)", _got22 == [k for _s, _e, k in _cases22], _got22)
check("B22: OMDb JSON 'Request limit reached!' = daily_limit; 'Movie not found!' = no failure", mc.classify_api_failure("omdb", data={"Response": "False", "Error": "Request limit reached!"}) == "daily_limit" and mc.classify_api_failure("omdb", data={"Response": "False", "Error": "Movie not found!"}) is None)
_texts22 = {k: mc.api_failure_message(s, k) for s, k in (("tmdb", "rate_limited"), ("omdb", "daily_limit"), ("tmdb", "invalid_key"), ("tmdb", "offline"), ("tmdb", "server_error"))}
check("B22: TMDb rate limit → 'too many requests … Wait about a minute and try again.'", _texts22["rate_limited"] == "TMDb is receiving too many requests from this computer. Wait about a minute and try again.", _texts22["rate_limited"])
check("B22: OMDb daily limit → 'OMDb (IMDb data): the free daily limit … Try again in a few hours or tomorrow. TMDb ratings still work.'", _texts22["daily_limit"] == "OMDb (IMDb data): the free daily limit of 1,000 requests is used up. Try again in a few hours or tomorrow. TMDb ratings still work.", _texts22["daily_limit"])
check("B22: invalid key / offline / server error texts", _texts22["invalid_key"] == "TMDb rejected the API key. Check Settings → API Keys (Validate)." and _texts22["offline"].startswith("No internet connection, or TMDb cannot be reached.") and _texts22["server_error"].startswith("TMDb is not responding right now. Try again in a few minutes"), _texts22)
check("B22: Enter ID… / Fetch / Verify use the same text (via _tmdb_error_message)", mc._tmdb_error_message(_http_err(429)).startswith(_texts22["rate_limited"]) and "SECRETKEY123" not in mc._tmdb_error_message(_http_err(429)))
import settings_dialog as _sd22
check("B22: Settings → Validate buttons use the same texts", _sd22._validate_failure_text("TMDb", "rate_limited") == "✗ " + _texts22["rate_limited"])
# pauses
mc._api_pauses_clear()
_e22 = mc.api_pause_start("omdb", "daily_limit")
_cfg22 = json.load(open(sc.CONFIG_PATH, encoding="utf-8"))
import datetime as _dt22
_mins22 = (_dt22.datetime.fromisoformat(_e22["until"]) - _dt22.datetime.now()).total_seconds() / 60
check("B22: OMDb daily limit → pause of about 2 hours, saved in settings.json 'api_pauses'", 115 < _mins22 <= 120 and _cfg22.get("api_pauses", {}).get("omdb", {}).get("kind") == "daily_limit" and "daily limit" in _cfg22["api_pauses"]["omdb"]["message"], (_mins22, _cfg22.get("api_pauses")))
check("B22: api_pause_get / api_pauses_active see it", mc.api_pause_get("omdb") and list(mc.api_pauses_active()) == ["omdb"])
mc.api_pause_end("omdb")
check("B22: ending the pause removes it from settings.json", "omdb" not in (json.load(open(sc.CONFIG_PATH, encoding="utf-8")).get("api_pauses") or {}) and mc.api_pause_get("omdb") is None)
check("B22: invalid key and offline do not pause", mc.api_pause_start("tmdb", "invalid_key") is None and mc.api_pause_start("tmdb", "offline") is None and not mc.api_pauses_active())
_past = (_dt22.datetime.now() - _dt22.timedelta(minutes=5)).isoformat(timespec="seconds")
_fut = (_dt22.datetime.now() + _dt22.timedelta(minutes=50)).isoformat(timespec="seconds")
mc.SETTINGS["api_pauses"] = {"tmdb": {"until": _past, "kind": "rate_limited", "message": "x"},
                             "omdb": {"until": _fut, "kind": "daily_limit", "message": "y"}}
_act22 = mc.api_pauses_load()
check("B22: on start the saved pauses are restored, expired ones dropped (and settings.json cleaned)", list(_act22) == ["omdb"] and list(json.load(open(sc.CONFIG_PATH, encoding="utf-8")).get("api_pauses") or {}) == ["omdb"], (_act22, mc.SETTINGS.get("api_pauses")))
mc._api_pauses_clear()
check("B22: 'api_pauses' is a settings key (DEFAULT_SETTINGS + schema)", DEFAULT_SETTINGS.get("api_pauses") == {} and "api_pauses" in json.load(open(os.path.join(_APP_DIR, "settings_schema.json"), encoding="utf-8"))["properties"])
# the client: 429 → pause; run decisions
_seq22 = []
def _fake22(url, timeout=15):
    _seq22.append(url); v = _plan22.pop(0) if _plan22 else {"ok": 1}
    if isinstance(v, Exception): raise v
    return v
_ofj22, _osl22 = mc._tmdb_fetch_json, mc.time.sleep
mc._tmdb_fetch_json = _fake22; mc.time.sleep = lambda x: None; mc._HTTP_TIMES.clear(); mc._TMDB_RATE_TIMES.clear()
try:
    _plan22 = [_http_err(429)] * 4
    try: mc._http_get_json("tmdb", "u")
    except Exception: pass
    _p22 = mc.api_pause_get("tmdb")
    check("B22: TMDb 429 after the retries → TMDb paused about a minute", _p22 and _p22["kind"] == "rate_limited" and 0 < (_dt22.datetime.fromisoformat(_p22["until"]) - _dt22.datetime.now()).total_seconds() <= 60, _p22)
    mc._api_pauses_clear(); _seq22.clear()
    # in a run: the user is asked ONCE; "cancel" stops the run
    _asked = []
    mc._service_run_begin(on_failure=lambda s, k, o: (_asked.append((s, k, o)), "cancel")[1], alternatives={"tmdb": None})
    _plan22 = [_http_err(503)] * 8
    for _ in range(2):
        try: mc._http_get_json("tmdb", "u")
        except Exception: pass
    check("B22: a batch run asks once (server error) and 'Cancel' stops the run", _asked == [("tmdb", "server_error", None)] and mc._service_run_cancelled() and len(_seq22) == 4, (_asked, len(_seq22)))
    mc._service_run_end(); mc._api_pauses_clear(); _seq22.clear()
    # "Pause this run": wait for the pause, then the SAME request is retried and succeeds
    mc._service_run_begin(on_failure=lambda s, k, o: (mc.api_pause_end(s), "pause")[1])   # the pause "expires" at once
    _plan22 = [_http_err(429)] * 4 + [{"answer": 42}]
    _r22 = mc._http_get_json("tmdb", "u")
    check("B22: 'Pause this run' waits for the pause and then retries the same request", _r22 == {"answer": 42} and len(_seq22) == 5 and not mc._service_blocked("tmdb"), (_r22, len(_seq22)))
    mc._service_run_end(); mc._api_pauses_clear(); _seq22.clear()
    # a paused service inside a run is not asked (no failing movie by movie)
    mc.api_pause_start("omdb", "daily_limit")
    mc._service_run_begin(on_failure=lambda s, k, o: "continue")
    try:
        mc._http_get_json("omdb", "u"); _su22 = None
    except mc.ServiceUnavailable as ex:
        _su22 = ex.kind
    check("B22: inside a run a paused service raises ServiceUnavailable without a request", _su22 == "daily_limit" and not _seq22)
    mc._service_run_end()
finally:
    mc._tmdb_fetch_json, mc.time.sleep = _ofj22, _osl22
    mc._service_run_end(); mc._api_pauses_clear(); mc._HTTP_TIMES.clear(); mc._TMDB_RATE_TIMES.clear()
# Search Sources / Normalize Sources say WHY
def _f22_429(url, timeout=15): raise _http_err(429)
_e22s = mc._search_sources_for_row(_r14x, "k", "en-US", "", fetch=lambda u, timeout=15: (_ for _ in ()).throw(_http_err(429)) if "/search/" in u else _f14(u, timeout))
check("B22: Search Sources remembers that TMDb did not answer (search_error)", _e22s["matches"] == [] and (_e22s.get("search_error") or "").startswith("TMDb is receiving too many requests"), _e22s.get("search_error"))
_o_rl22 = mc._tmdb_rate_limited_fetch; _ok22 = mc.SETTINGS.get("tmdb_api_key", "")
try:
    mc.SETTINGS["tmdb_api_key"] = "k"
    mc._tmdb_rate_limited_fetch = _f22_429
    _lk = mc._lookup_id_info_ex("TMDB", "603")
    mc._tmdb_rate_limited_fetch = lambda url, timeout=15: (_ for _ in ()).throw(_http_err(404))
    _lk404 = mc._lookup_id_info_ex("TMDB", "999")
finally:
    mc._tmdb_rate_limited_fetch = _o_rl22; mc.SETTINGS["tmdb_api_key"] = _ok22
check("B22: Normalize Sources lookup tells 'TMDb did not answer' from 'ID not found'", _lk[0] is None and (_lk[2] or "").startswith("TMDb is receiving too many requests") and _lk404 == (None, None, None), (_lk, _lk404))
mc._api_pauses_clear()

# ── v0.19.1 B12: exact NFO/XML error lines and tag names ──────────────────────   ### NEW v0.19.1 B12 ###
section("2u. NFO/XML errors with line + tag names (v0.19.1 B12)")
def _b12(name, text):
    p = os.path.join(_TMP, "b12", name); os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(text); return p
def _msgs(errs): return [(e["line"], e["message"]) for e in errs]
_body = "".join(f"\t<x{i}>v</x{i}>\n" for i in range(30))
_p = _b12("unclosed.nfo", "<movie>\n\t<title>A</title>\n" + "\t<n>1</n>\n" * 9 + "\t<plot>long text\n" + _body + "</movie>\n")
_e = mc.validate_xml_file(_p, is_nfo=True)
check("B12: unclosed tag → 'Line 12: `<plot>` opened here is never closed (expected `</plot>` before `</movie>` on line 43)'", _msgs(_e) == [(12, "`<plot>` opened here is never closed (expected `</plot>` before `</movie>` on line 43)")], _msgs(_e))
_p = _b12("mismatch.nfo", "<movie>\n" + "\t<n>1</n>\n" * 25 + "\t<title>A</titel>\n</movie>\n")
check("B12: mismatched tag → 'Line 27: closing `</titel>` does not match the open `<title>` (line 27)' — once", _msgs(mc.validate_xml_file(_p, True)) == [(27, "closing `</titel>` does not match the open `<title>` (line 27)")], _msgs(mc.validate_xml_file(_p, True)))
_p = _b12("missinggt.nfo", "<movie>\n" + "\t<n>1</n>\n" * 31 + "\t<rating 7.3</rating>\n</movie>\n")
check("B12: missing '>' → 'Line 33: `<rating` missing `>`'", _msgs(mc.validate_xml_file(_p, True)) == [(33, "`<rating` missing `>`")], _msgs(mc.validate_xml_file(_p, True)))
_p = _b12("trailing.xml", "<Item>\n" + "\t<n>1</n>\n" * 47 + "</Item>\n\nleft-over text\n")
check("B12: text after the root → 'Line 51: text after the root element `</Item>`'", _msgs(mc.validate_xml_file(_p)) == [(51, "text after the root element `</Item>`")], _msgs(mc.validate_xml_file(_p)))
_p = _b12("several.nfo", "<movie>\n\t<plot>x\n\t<title>A</titel>\n\t<rating 7</rating>\n</movie>\n")
check("B12: several errors in one file are ALL reported, in line order", _msgs(mc.validate_xml_file(_p, True)) == [(2, "`<plot>` opened here is never closed (expected `</plot>` before `</movie>` on line 5)"), (3, "closing `</titel>` does not match the open `<title>` (line 3)"), (4, "`<rating` missing `>`")], _msgs(mc.validate_xml_file(_p, True)))
_p = _b12("eof.nfo", "<movie>\n\t<title>A</title>\n")
check("B12: root never closed → '… before the end of the file'", _msgs(mc.validate_xml_file(_p, True)) == [(1, "`<movie>` opened here is never closed (expected `</movie>` before the end of the file)")], _msgs(mc.validate_xml_file(_p, True)))
_inf = []
_p = _b12("amp.nfo", "<movie>\n" + "\t<n>1</n>\n" * 6 + "\t<title>Tom & Jerry</title>\n</movie>\n")
check("B12: unescaped '&' → info only (file stays valid): 'Line 8: `&` not escaped (Kodi accepts it, Emby may not)'", mc.validate_xml_file(_p, True, infos=_inf) == [] and _msgs(_inf) == [(8, "`&` not escaped (Kodi accepts it, Emby may not)")], (_msgs(_inf)))
_p = _b12("valid.nfo", '<?xml version="1.0"?>\n<!-- c <x> -->\n<movie>\n\t<id moviedb="imdb">tt1</id>\n\t<a b="x>y"/>\n\t<plot><![CDATA[ <b>bold</b> ]]></plot>\n</movie>\n')
check("B12: comments, CDATA, attributes with '>' and self-closing tags → valid, no false alarm", mc.validate_xml_file(_p, True) == [] and mc.scan_xml_structure(io.open(_p, encoding="utf-8").read())[0] == [])
check("B12: the parser stays a cross-check (a file the parser rejects is never OK)", mc.validate_xml_file(_b12("dup.nfo", '<movie a="1" a="2">\n</movie>\n'), True) != [])
_r12 = scan(M_BADXML, use_ffprobe=False)
check("B12: the broken fixture XML names the tag and both lines", _msgs(_r12["xml_errors"]) == [(3, "`<Genres>` opened here is never closed (expected `</Genres>` before `</Item>` on line 4)")], _msgs(_r12["xml_errors"]))

# ── v0.19.1 I1: backup manifest + restore ─────────────────────────────────────   ### NEW v0.19.1 I1 ###
section("2v. backup manifest + restore (v0.19.1 I1)")
_bkr = os.path.join(_TMP, "i1_backup")                 # own backup root (the app's backup/ stays untouched)
_m1 = os.path.join(_TMP, "i1", "Movie One"); _m2 = os.path.join(_TMP, "i1", "Movie Two")
for _d in (_m1, _m2): os.makedirs(_d, exist_ok=True)
_f1, _f2 = os.path.join(_m1, "x.nfo"), os.path.join(_m2, "x.nfo")        # same name → x.nfo / x_2.nfo in the backup
_f3 = os.path.join(_m1, "movie.xml")
for _f, _c in ((_f1, "<movie>one</movie>\n"), (_f2, "<movie>two</movie>\n"), (_f3, "<Item>three</Item>\n")):
    io.open(_f, "w", encoding="utf-8", newline="\n").write(_c)
_ref = [None]
with sc.backup_action("Test Run"):
    sc.make_batch_backup(_bkr, "Movie One", _ref, _f1, _f3)
    sc.make_batch_backup(_bkr, "Movie Two", _ref, _f2)
    sc.make_batch_backup(_bkr, "Movie One", _ref, _f1)        # a second backup of the same original is not listed again
_man = sc.read_manifest(_ref[0])
check("I1: every backup folder gets manifest.json (action, run id, original path, backup name, size, mtime)",
      _man and _man["action"] == "Test Run" and _man["run_id"] and [(os.path.basename(os.path.dirname(f["original"])), f["backup"]) for f in _man["files"]] == [("Movie One", "x.nfo"), ("Movie One", "movie.xml"), ("Movie Two", "x_2.nfo")]
      and all("size" in f and "mtime" in f for f in _man["files"]), _man)
for _f, _c in ((_f1, "<movie>ONE CHANGED</movie>\n"), (_f2, "<movie>TWO CHANGED</movie>\n"), (_f3, "<Item>THREE CHANGED</Item>\n")):
    io.open(_f, "w", encoding="utf-8", newline="\n").write(_c)
sc.note_written([_m1, _m2])                              # what _schedule_refresh does after a change
_man = sc.read_manifest(_ref[0])
check("I1: after the run the manifest knows how the run left each file (not 'changed since')", all("after_mtime" in f for f in _man["files"]) and not any(sc.file_changed_since_run(f) for f in _man["files"]))
time.sleep(0.05); io.open(_f3, "w", encoding="utf-8", newline="\n").write("<Item>EDITED LATER BY HAND</Item>\n")
check("I1: a file edited after the run is detected ('changed since')", [os.path.basename(f["original"]) for f in sc.read_manifest(_ref[0])["files"] if sc.file_changed_since_run(f)] == ["movie.xml"])
_legacy = os.path.join(_bkr, "backup_Old_Movie_2026-01-01_10-00-00"); os.makedirs(_legacy, exist_ok=True)
io.open(os.path.join(_legacy, "old.nfo"), "w").write("x")
_runs = sc.list_backup_runs(_bkr)
check("I1: Backup History lists the runs newest first; folders without a manifest are 'legacy'", [r["legacy"] for r in _runs] == [False, True] and _runs[0]["action"] == "Test Run" and _runs[0]["movies"] == 2 and len(_runs[0]["files"]) == 3, [(r["name"], r["legacy"]) for r in _runs])
_restored, _errs, _safety = sc.restore_backup_run(_bkr, _ref[0], skip={_f3})
check("I1: restore puts the files back byte for byte — both 'x.nfo' to the right movie (collision handled)", _txt(_f1) == "<movie>one</movie>\n" and _txt(_f2) == "<movie>two</movie>\n" and not _errs, (_txt(_f1), _txt(_f2), _errs))
check("I1: a skipped (changed) file is left alone", _txt(_f3) == "<Item>EDITED LATER BY HAND</Item>\n")
_sman = sc.read_manifest(_safety) if _safety else None
check("I1: the current files were backed up first ('Before undo — Test Run …')", _sman and _sman["action"].startswith("Before undo — Test Run") and len(_sman["files"]) == 2, _sman)
_r2, _e2, _s2 = sc.restore_backup_run(_bkr, _safety)
check("I1: an undo can itself be undone", _txt(_f1) == "<movie>ONE CHANGED</movie>\n" and _txt(_f2) == "<movie>TWO CHANGED</movie>\n" and not _e2)
check("I1: no temp files left behind", not [x for d in (_m1, _m2) for x in os.listdir(d) if x.endswith(".mcrestore")])
check("I1: a legacy backup cannot be restored automatically", sc.restore_backup_run(_bkr, _legacy)[1] == ["No manifest — this backup can only be restored by hand."])

# ── v0.19.1 I5: one ffprobe per video + cache ─────────────────────────────────   ### NEW v0.19.1 I5 ###
section("2w. FFprobe cache (v0.19.1 I5)")
check("I5: new key ffprobe_cache_enabled (default ON, schema)", DEFAULT_SETTINGS.get("ffprobe_cache_enabled") is True and "ffprobe_cache_enabled" in json.load(open(os.path.join(_APP_DIR, "settings_schema.json"), encoding="utf-8"))["properties"])
if SAMPLE_VIDEO:
    _d5 = os.path.join(_TMP, "i5", "Cache Movie"); os.makedirs(_d5, exist_ok=True)
    shutil.copy2(SAMPLE_VIDEO, os.path.join(_d5, "Cache Movie.mkv"))
    _nfo(os.path.join(_d5, "Cache Movie.nfo"), "Cache Movie", imdb="tt7750001", tmdb="750001")
    _v5 = os.path.join(_d5, "Cache Movie.mkv")
    mc._FFPROBE_STATS.update(runs=0, hits=0)
    _r5 = scan(_d5, use_ffprobe=True)
    check("I5: ONE ffprobe process per video (resolution, audio, subtitles, Lang OK? from the same JSON)", mc._FFPROBE_STATS["runs"] == 1 and _r5["video_quality"] == "720p" and _r5["audio_tracks"] and _r5["audio_tracks"][0]["language"] == "ENG", (mc._FFPROBE_STATS, _r5["video_quality"]))
    mc._FFPROBE_STATS.update(runs=0, hits=0)
    _r5b = scan(_d5, use_ffprobe=True)
    check("I5: second FFprobe scan of the unchanged video runs 0 ffprobe processes (spy)", mc._FFPROBE_STATS["runs"] == 0 and mc._FFPROBE_STATS["hits"] >= 1 and _r5b["audio_tracks"] == _r5["audio_tracks"] and _r5b["video_quality"] == "720p", mc._FFPROBE_STATS)
    os.utime(_v5, ns=(os.stat(_v5).st_atime_ns, os.stat(_v5).st_mtime_ns + 5_000_000_000))
    mc._FFPROBE_STATS.update(runs=0, hits=0)
    scan(_d5, use_ffprobe=True)
    check("I5: a touched (changed) video is probed again", mc._FFPROBE_STATS["runs"] == 1, mc._FFPROBE_STATS)
    mc._FFPROBE_STATS.update(runs=0, hits=0)
    mc.scan_one_subfolder(_d5, "Cache Movie", force_ffprobe=True)
    check("I5: Update (with FFprobe) forces a fresh probe", mc._FFPROBE_STATS["runs"] == 1, mc._FFPROBE_STATS)
    mc.SETTINGS["ffprobe_cache_enabled"] = False
    mc._FFPROBE_STATS.update(runs=0, hits=0)
    scan(_d5, use_ffprobe=True); _n_off1 = mc._FFPROBE_STATS["runs"]
    mc._FFPROBE_MEMO.clear()                                 # = a later scan (the memo lives ~10 s)
    scan(_d5, use_ffprobe=True)
    mc.SETTINGS["ffprobe_cache_enabled"] = True
    check("I5: with the cache switched off: still ONE process per video, and every scan probes", _n_off1 == 1 and mc._FFPROBE_STATS["runs"] == 2 and mc._FFPROBE_STATS["hits"] == 0, (_n_off1, mc._FFPROBE_STATS))
    mc._ffprobe_cache_flush()
    _cf = json.load(open(sc.FFPROBE_CACHE_PATH, encoding="utf-8"))
    _k5 = os.path.normcase(os.path.abspath(_v5))
    check("I5: ffprobe_cache.json next to settings.json, keyed by path with size + mtime_ns", os.path.dirname(sc.FFPROBE_CACHE_PATH) == os.path.dirname(sc.CONFIG_PATH) and _k5 in _cf and _cf[_k5]["size"] == os.path.getsize(_v5) and _cf[_k5]["mtime_ns"] == os.stat(_v5).st_mtime_ns)
    io.open(sc.FFPROBE_CACHE_PATH, "w", encoding="utf-8").write("{ not json")
    mc._FFPROBE_CACHE = None                                 # as after a restart
    mc._FFPROBE_STATS.update(runs=0, hits=0)
    _r5c = scan(_d5, use_ffprobe=True)
    check("I5: a corrupt cache file is ignored (probe again, scan works)", sc.load_ffprobe_cache() == {} and mc._FFPROBE_STATS["runs"] == 1 and _r5c["video_quality"] == "720p", mc._FFPROBE_STATS)
    mc._ffprobe_cache_flush()
    check("I5: …and rewritten valid on the next save", isinstance(json.load(open(sc.FFPROBE_CACHE_PATH, encoding="utf-8")), dict))

# ── v0.19.1 I10: fanart.tv ───────────────────────────────────────────────────   ### NEW v0.19.1 I10 ###
section("2x. fanart.tv (v0.19.1 I10)")
_sch10 = json.load(open(os.path.join(_APP_DIR, "settings_schema.json"), encoding="utf-8"))["properties"]
check("I10: new keys fanarttv_api_key / fanarttv_client_key (default empty, schema)", DEFAULT_SETTINGS.get("fanarttv_api_key") == "" and DEFAULT_SETTINGS.get("fanarttv_client_key") == "" and "fanarttv_api_key" in _sch10 and "fanarttv_client_key" in _sch10)
check("I10: fanart.tv has its own rate limit in the shared client", "fanarttv" in mc._HTTP_LIMITS and mc._SERVICE_LABEL["fanarttv"] == "fanart.tv")
check("I10: image URLs made absolute (bare paths go on the assets host)",
      mc.fanarttv_abs_url("http://assets.fanart.tv/fanart/movies/603/x.jpg") == "https://assets.fanart.tv/fanart/movies/603/x.jpg"
      and mc.fanarttv_abs_url("/fanart/movies/603/x.jpg") == "https://assets.fanart.tv/fanart/movies/603/x.jpg"
      and mc.fanarttv_abs_url("//assets.fanart.tv/a.jpg") == "https://assets.fanart.tv/a.jpg" and mc.fanarttv_abs_url(None) == "")
check("I10: preview thumbnail URL", mc.fanarttv_preview_url("https://assets.fanart.tv/fanart/movies/1/a.jpg") == "https://assets.fanart.tv/preview/movies/1/a.jpg")
_fd10 = {"name": "X", "tmdb_id": "603",
         "movieposter": [{"url": "https://assets.fanart.tv/fanart/movies/603/p_en.jpg", "lang": "en", "likes": "9"},
                         {"url": "https://assets.fanart.tv/fanart/movies/603/p_de.jpg", "lang": "de", "likes": "20"},
                         {"url": "https://assets.fanart.tv/fanart/movies/603/p_00.jpg", "lang": "00", "likes": "1"},
                         {"url": "https://assets.fanart.tv/fanart/movies/603/p_pt.jpg", "lang": "pt", "likes": "0"},
                         {"url": "https://assets.fanart.tv/fanart/movies/603/p_pt.jpg", "lang": "pt", "likes": "0"}],
         "moviebackground": [{"url": "https://assets.fanart.tv/fanart/movies/603/b1.jpg", "lang": "", "likes": "2"},
                             {"url": "/fanart/movies/603/b2.jpg", "lang": "", "likes": "7"}],
         "moviethumb": [{"url": "https://assets.fanart.tv/fanart/movies/603/t1.jpg", "lang": "en", "likes": "1"}]}
_pp10 = mc.fanarttv_image_entries(_fd10, "poster", "PT")
check("I10: posters — your library language first, then no language, then English (duplicates once)", [e["lang"] for e in _pp10] == ["pt", "00", "en", "de"], [e["lang"] for e in _pp10])
_bb10 = mc.fanarttv_image_entries(_fd10, "fanart")
check("I10: backgrounds by likes, 1920×1080 (fanart.tv's size), thumbs only when asked", [e["likes"] for e in _bb10] == [7, 2] and _bb10[0]["width"] == 1920 and _bb10[0]["dims_typical"] and len(mc.fanarttv_image_entries(_fd10, "fanart", include_thumbs=True)) == 3)
_tm10 = mc.tmdb_image_entries([{"file_path": "/a.jpg", "width": 3840, "height": 2160, "vote_count": 3},
                               {"file_path": "/b.jpg", "width": 1280, "height": 720}, {"file_path": ""}])
_mg10 = mc.merge_image_sources(_tm10, _bb10 + [_bb10[0]])
check("I10: Both = one list by resolution, then votes / likes; the same URL once", [e["source"] for e in _mg10] == ["tmdb", "fanarttv", "fanarttv", "tmdb"] and len(_mg10) == 4, [(e["source"], e["width"]) for e in _mg10])
check("I10: each entry shows its source, size and likes", mc.image_entry_text(_bb10[0])[0] == "fanart.tv" and "~1920×1080" in mc.image_entry_text(_bb10[0])[1] and "♥7" in mc.image_entry_text(_bb10[0])[1] and mc.image_entry_text(_tm10[0])[0] == "TMDb")
_o10 = (mc._http_get_json, mc.SETTINGS.get("fanarttv_api_key", ""), mc.SETTINGS.get("fanarttv_client_key", ""))
_calls10 = []
def _fake_fan10(service, url, timeout=15, _waited=False):
    _calls10.append((service, url))
    if "/movies/604" in url:
        import urllib.error as _ue10
        raise _ue10.HTTPError(url, 404, "Not Found", {}, None)
    return _fd10
try:
    mc._http_get_json = _fake_fan10
    mc.SETTINGS["fanarttv_api_key"] = "SECRETFAN"; mc.SETTINGS["fanarttv_client_key"] = "SECRETVIP"
    mc._FANARTTV_CACHE = {}
    _d10, _e10 = mc.fanarttv_fetch("603", "tt0133093")
    check("I10: asked by TMDb ID with api_key and client_key", _e10 is None and _d10 is _fd10 and len(_calls10) == 1 and _calls10[0][0] == "fanarttv" and "/v3/movies/603?api_key=SECRETFAN&client_key=SECRETVIP" in _calls10[0][1], _calls10)
    check("I10: the keys are redacted in log text", "SECRET" not in mc._redact(_calls10[0][1]))
    _calls10.clear()
    _d10b, _ = mc.fanarttv_fetch("603", "tt0133093")
    check("I10: the answer is cached (no second request)", not _calls10 and _d10b == _fd10)
    _cft = io.open(sc.FANARTTV_CACHE_PATH, encoding="utf-8").read()
    check("I10: fanarttv_cache.json next to settings.json, without any key", os.path.dirname(sc.FANARTTV_CACHE_PATH) == os.path.dirname(sc.CONFIG_PATH) and "tmdb:603" in json.loads(_cft) and "SECRET" not in _cft)
    _calls10.clear()
    _d10c, _e10c = mc.fanarttv_fetch("604", "tt0000604")
    check("I10: not found by TMDb ID → asked by IMDb ID", [u.split("/movies/")[1].split("?")[0] for _s, u in _calls10] == ["604", "tt0000604"] and _e10c is None and _d10c == _fd10, _calls10)
    _calls10.clear()
    mc.fanarttv_fetch("604", None)
    check("I10: a 'not on fanart.tv' answer is cached too", not _calls10, _calls10)
    check("I10: no TMDb or IMDb ID → the dialog says so", "no TMDb or IMDb ID" in (mc.fanarttv_fetch(None, None)[1] or ""))
    check("I10: an old cache entry (> 7 days) is asked again", (mc._FANARTTV_CACHE.__setitem__("tmdb:603", {"t": time.time() - 8 * 86400, "data": _fd10}), mc.fanarttv_fetch("603", None), len(_calls10))[2] == 1, _calls10)
    sc.save_fanarttv_cache({"tmdb:1": {"t": time.time() - 9 * 86400, "data": {"a": 1}}, "tmdb:2": {"t": time.time(), "data": {}}})
    check("I10: old entries are dropped when the cache is saved", list(sc.load_fanarttv_cache()) == ["tmdb:2"])
    io.open(sc.FANARTTV_CACHE_PATH, "w", encoding="utf-8").write("{ broken")
    check("I10: a corrupt cache file is ignored", sc.load_fanarttv_cache() == {})
    mc._LAST_IMAGE_SOURCE[0] = None
    check("I10: default source = Both with a fanart.tv key, fanart.tv when TMDb cannot be used", mc.default_image_source() == "both" and mc.default_image_source(tmdb_ok=False) == "fanarttv")
    mc._LAST_IMAGE_SOURCE[0] = "fanarttv"
    check("I10: the choice made in a dialog is kept for the session", mc.default_image_source() == "fanarttv")
    mc.SETTINGS["fanarttv_api_key"] = ""
    check("I10: no fanart.tv key → TMDb, and fanart.tv is not asked", mc.default_image_source() == "tmdb" and "No fanart.tv API key" in mc.fanarttv_fetch("603", None)[1])
finally:
    mc._http_get_json = _o10[0]; mc.SETTINGS["fanarttv_api_key"] = _o10[1]; mc.SETTINGS["fanarttv_client_key"] = _o10[2]
    mc._LAST_IMAGE_SOURCE[0] = None; mc._FANARTTV_CACHE = None

# ── v0.19.1 B11: frames from the movie ───────────────────────────────────────   ### NEW v0.19.1 B11 ###
section("2y. Frames from the movie (v0.19.1 B11)")
import random as _rnd11
_ft11 = mc.frame_times(100.0, 10, _rnd11.Random(1)); _ft11b = mc.frame_times(100.0, 10, _rnd11.Random(2))
check("B11: 10 times spread over 10 %–90 % of the running time, a new set differs", len(_ft11) == 10 and all(10.0 <= x <= 90.0 for x in _ft11) and _ft11 == sorted(_ft11) and _ft11 != _ft11b, _ft11)
check("B11: no running time → no frames", mc.frame_times(0) == [] and mc.frame_times(None) == [])
_bl11 = os.path.join(_TMP, "b11_black.jpg"); _jpeg(_bl11, 320, 180)
from PIL import Image as _Im11
_Im11.new("RGB", (320, 180), (0, 0, 0)).save(_bl11, "JPEG")
_ns11 = os.path.join(_TMP, "b11_noise.jpg"); _jpeg(_ns11, 320, 180, noisy=True)
_fl11 = os.path.join(_TMP, "b11_flat.jpg"); _jpeg(_fl11, 320, 180)
check("B11: black and flat frames are rejected, a normal frame is kept", mc.frame_is_flat(_bl11) and mc.frame_is_flat(_fl11) and not mc.frame_is_flat(_ns11) and mc.frame_is_flat(os.path.join(_TMP, "missing.jpg")))
check("B11: the button needs FFmpeg and a video", mc.frames_available({"video_path": "x.mkv"}) == bool(mc.FFMPEG_PATH) and not mc.frames_available({"video_path": None}))
if SAMPLE_VIDEO:
    _fd11 = os.path.join(_TMP, "b11_frames")
    _fr11, _er11 = mc.extract_movie_frames(SAMPLE_VIDEO, _fd11)
    check("B11: 10 frames from the 3-second sample, all inside 10 %–90 %", _er11 is None and len(_fr11) == 10 and all(0.25 <= e["time"] <= 2.75 for e in _fr11) and all(os.path.isfile(e["url"]) for e in _fr11), (_er11, [round(e["time"], 2) for e in _fr11]))
    check("B11: frames keep the video's resolution and are flagged below the fanart minimum (720p < 1080p)", all((e["width"], e["height"]) == (1280, 720) and e["low_res"] for e in _fr11) and "below the 1080p minimum" in mc.image_entry_text(_fr11[0])[1] and mc.image_entry_text(_fr11[0])[0] == "Frame")
    check("B11: a frame's thumbnail is read from disk", (mc._download_preview(_fr11[0]) or b"")[:2] == b"\xff\xd8")
    # black first try → a nearby time is used instead
    _oe11 = mc.extract_single_frame; _calls11 = []
    def _fake_ex11(video, ts, outp, timeout_sec=60):
        _calls11.append(ts)
        if len(_calls11) % 2 == 1:
            _Im11.new("RGB", (320, 180), (0, 0, 0)).save(outp, "JPEG")
        else:
            shutil.copy2(_ns11, outp)
        return True, ""
    mc.extract_single_frame = _fake_ex11
    try:
        _fr11b, _ = mc.extract_movie_frames(SAMPLE_VIDEO, os.path.join(_TMP, "b11_frames2"), n=3)
    finally:
        mc.extract_single_frame = _oe11
    check("B11: a black frame is replaced by a nearby time (2 extractions per frame here)", len(_fr11b) == 3 and len(_calls11) == 6 and _calls11[0] != _calls11[1] and not any(os.path.basename(e["url"]).endswith("_0.jpg") for e in _fr11b), _calls11)
    _o11 = mc.extract_single_frame
    mc.extract_single_frame = lambda v, ts, o, timeout_sec=60: (False, "boom")
    try:
        check("B11: FFmpeg failing → a clear message, no frames", mc.extract_movie_frames(SAMPLE_VIDEO, os.path.join(_TMP, "b11_frames3"))[1].startswith("FFmpeg could not extract frames: boom"))
    finally:
        mc.extract_single_frame = _o11

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

# ### NEW v0.19.1 I9 ### — ONE main-thread helper for every UI step.  The tests
# run on a helper thread; every Tk action goes through on_ui(fn), which runs fn
# inside the main loop and waits for it.  A debounced filter refresh that fn
# triggered (_on_filter_changed → after(150, _refresh_table)) is run at once in
# the same call, so the table is never rebuilt behind the test's back — the
# v0.19.1 baseline failed on exactly that race ("Conflicting IDs" missing from
# _item_map while the delayed refresh was rebuilding it).
_UI_APP = []

def on_ui(fn, timeout=60, app_=None):
    a = app_ or _UI_APP[-1]
    ev = threading.Event(); box = {}
    def _run():
        try:
            box["r"] = fn()
            aid = getattr(a, "_filter_after_id", None)
            if aid is not None and aid in a.tk.splitlist(a.tk.call("after", "info")):
                a.after_cancel(aid); a._filter_after_id = None
                a._refresh_table()
        except Exception:
            box["e"] = traceback.format_exc()
        finally:
            ev.set()
    a.after(0, _run)
    if not ev.wait(timeout):
        raise RuntimeError(f"on_ui: main thread did not run the step within {timeout} s")
    if "e" in box:
        raise RuntimeError(box["e"])
    return box.get("r")

def kids(app_=None):
    """The table rows, read on the main thread."""
    return on_ui(lambda: list((app_ or _UI_APP[-1]).tree.get_children()), app_=app_)

_UI_APP.append(app)

def ui_tests():
    try:
        # ### MODIFIED v0.19.1 I9 ### every Tk action below goes through on_ui()
        on_ui(lambda: (setattr(app, "_folder", LIB), app.folder_var.set(LIB), app._start_scan(LIB, use_ff=True)))
        check("full scan finished", wait_for(lambda: not app._scanning), "timeout")
        check(f"all {n_movies} movies scanned", len(app._results) == n_movies, len(app._results))
        check("results cache written", os.path.isfile(sc.RESULTS_CACHE_PATH) and len(sc.load_results_cache()) == n_movies)
        check("settings.json stays small", os.path.getsize(sc.CONFIG_PATH) < 20000, os.path.getsize(sc.CONFIG_PATH))
        by = {r["subfolder"]: r for r in app._results}
        if SAMPLE_VIDEO:
            check("full scan: audio tracks found", by["Perfect Movie"]["audio_tracks"] and by["Perfect Movie"]["ffprobe_ran"])
            on_ui(lambda: app._start_scan(LIB.replace("\\", "/"), use_ff=False))   # other slash style → keys must still match
            check("no-ffprobe scan finished", wait_for(lambda: not app._scanning))
            by = {r["subfolder"]: r for r in app._results}
            check("no-ffprobe scan keeps audio tracks", by["Perfect Movie"]["audio_tracks"] != [], by["Perfect Movie"]["audio_tracks"])
            check("no-ffprobe scan keeps video quality + lang_ok", by["Perfect Movie"]["video_quality"] == "720p" and by["Perfect Movie"]["lang_ok"] == "Y", (by["Perfect Movie"]["video_quality"], by["Perfect Movie"]["lang_ok"]))
            check("no-ffprobe scan keeps ffprobe_ran", by["Perfect Movie"]["ffprobe_ran"] is True)

        errs = []
        def _all_tips():
            for iid in app.tree.get_children():
                for ci in range(len(mc.COLUMN_MODEL)):
                    try: app._tooltip(iid, ci)
                    except Exception as e: errs.append((ci, repr(e)))
        on_ui(_all_tips)
        check("tooltips for all cells render", not errs, errs[:3])
        check("row values length matches column model", all(len(app._rv(r)) == len(mc.COLUMN_MODEL) for r in app._results))

        on_ui(lambda: (app._filter_var.set("conflict"), app._refresh_table()))
        check("filter narrows the view", 0 < len(kids()) < n_movies, len(kids()))
        on_ui(lambda: (app._filter_var.set(""), app._refresh_table()))

        # Quick scan — modify one NFO, add one folder, remove one folder
        pm_nfo = os.path.join(M_OK, "Perfect Movie.nfo")
        time.sleep(1.1)
        txt = io.open(pm_nfo, encoding="utf-8").read().replace("<rating>7.3</rating>", "<rating>8.8</rating>")
        io.open(pm_nfo, "w", encoding="utf-8").write(txt)
        make_movie("Brand New Movie", video=False)
        shutil.rmtree(M_NOVID)
        on_ui(lambda: app._start_quick_scan(LIB))
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
        on_ui(lambda: app._start_quick_scan(LIB))
        wait_for(lambda: not app._scanning)
        check("quick scan: no changes → 'up to date' message", any("up to date" in str(b) for b in _boxes), _boxes)
        if SAMPLE_VIDEO:
            # Quick Scan probes a NEW movie with FFprobe when the box is ticked (v0.18.4)
            make_movie("Probe Me New")
            on_ui(lambda: (app._use_ffprobe.set(True), app._start_quick_scan(LIB)))
            wait_for(lambda: not app._scanning)
            by = {r["subfolder"]: r for r in app._results}
            check("quick scan (box ticked): new movie probed (audio tracks present)", by.get("Probe Me New", {}).get("ffprobe_ran") and by["Probe Me New"]["audio_tracks"], by.get("Probe Me New", {}).get("audio_tracks"))
            # Update (no FFprobe) sees a NEW external subtitle (v0.18.4 fix)
            iid_p = next(i for i, d in app._item_map.items() if d["subfolder"] == "Probe Me New")
            io.open(os.path.join(LIB, "Probe Me New", "Probe Me New.en.srt"), "w", encoding="utf-8").write("1\n00:00:01,000 --> 00:00:02,000\nHi\n")
            on_ui(lambda: app._reval_no_ffmpeg(iid_p, app._item_map[iid_p]))
            dP = app._item_map[iid_p]
            check("Update (no FFprobe) picks up new external subtitle, keeps audio", any(x["lang"] == "en" for x in dP["subs_external"]) and dP["audio_tracks"] and "Ext: " in dP["subs_summary"] and "en" in dP["subs_summary"], (dP["subs_external"], dP["subs_summary"]))
        # health chips + problems only + reason filter
        on_ui(lambda: app._set_health_filter("error"))
        _k = kids()
        check("Errors chip filters the view", all(app._item_map[i]["health_status"] == "error" for i in _k) and len(_k) > 0)
        on_ui(lambda: app._set_health_filter("problems"))
        _k = kids()
        check("Problems only hides green rows", all(app._item_map[i]["health_status"] != "ok" for i in _k) and app._problems_only_var.get())
        on_ui(lambda: (app._set_health_filter(None), app._filter_var.set("missing nfo"), app._refresh_table()))
        _k = kids()
        check("filter matches health reason text", all(any("missing nfo" in x.lower() for x in app._item_map[i]["health_reasons"]) for i in _k) and len(_k) > 0, len(_k))
        on_ui(lambda: (app._filter_var.set(""), app._refresh_table()))
        # column chooser mapping
        mc.SETTINGS["hidden_columns"] = ["year", "genre", "rating"]; on_ui(app._apply_column_visibility)
        _mi = on_ui(lambda: (app._model_col_index(0), app._model_col_index(1)))
        check("hidden columns: display index maps to model index", _mi == (mc.COL_MOVIE_NAME, mc.COL_VOTES), (_mi, mc.COL_VOTES))
        _tips = on_ui(lambda: (lambda f: (app._tooltip(f, 0), app._tooltip(f, 1)))(list(app.tree.get_children())[0]))
        check("tooltips work with hidden columns", bool(_tips[0]) and ("Votes" in (_tips[1] or "")), _tips[1])
        mc.SETTINGS["hidden_columns"] = []; on_ui(app._apply_column_visibility)
        check("show all columns restores #all", on_ui(lambda: app._model_col_index(1)) == 1)
        # poster → folder fix
        by = {r["subfolder"]: r for r in app._results}
        d_cf = by["Conflicting IDs"]
        _jpeg(d_cf["folder_path"], 600, 900, noisy=True)        # make folder.jpg differ
        on_ui(lambda: app._reval_no_ffmpeg(next(i for i, d in app._item_map.items() if d["subfolder"] == "Conflicting IDs"), d_cf))
        d_cf = {r["subfolder"]: r for r in app._results}["Conflicting IDs"]
        check("poster/folder differ detected", d_cf["poster_bytes"] != d_cf["folder_bytes"] and any("Poster and folder image are different" in x for x in d_cf["health_reasons"]), d_cf["health_reasons"])
        _boxes.clear()
        on_ui(lambda: app._copy_poster_to_folder([d_cf], confirm=False))
        wait_for(lambda: any("folder.jpg updated" in str(b) for b in _boxes), 30)
        time.sleep(0.1); wait_for(app._refresh_idle, 15)          # v0.19.0: automatic refresh runs in the background
        d_cf = {r["subfolder"]: r for r in app._results}["Conflicting IDs"]
        check("copy poster → folder: sizes equal, warning gone, backup made", d_cf["poster_bytes"] == d_cf["folder_bytes"] and not any("Poster and folder image are different" in x for x in d_cf["health_reasons"]) and any(n.startswith("backup_") for n in os.listdir(os.path.join(_APP_DIR, "backup"))), (d_cf["poster_bytes"], d_cf["folder_bytes"], d_cf["health_reasons"]))
        # reports + dialogs
        on_ui(lambda: mc.TextReportDialog(app, "stats", mc.format_library_statistics(app._results)).destroy())
        on_ui(lambda: (lambda cc: (cc._vars["year"].set(False), cc._ok()))(mc.ColumnChooserDialog(app)))
        check("column chooser persists + applies", mc.SETTINGS["hidden_columns"] == ["year"] and on_ui(lambda: app._model_col_index(1)) == mc.COL_GENRE)
        mc.SETTINGS["hidden_columns"] = []; on_ui(app._apply_column_visibility)
        rpt2 = mc.format_health_report(app._results)
        _nv = [r for r in app._results if r["health_status"] == "error" and r["health_warnings"]]
        check("health report shows ⚠ lines inside an [ERROR] block + 'Most common issues'", bool(_nv) and "Most common issues:" in rpt2 and ("\u26a0  " + _nv[0]["health_warnings"][0]) in rpt2, _nv[0]["health_warnings"][:1] if _nv else "no error row with warnings")

        iid0 = on_ui(lambda: next(i for i, d in app._item_map.items() if d["subfolder"] == "Perfect Movie"))
        on_ui(lambda: app._reval_no_ffmpeg(iid0, app._item_map[iid0]))
        d0 = app._item_map[iid0]
        if SAMPLE_VIDEO:
            check("Update (no FFprobe) keeps audio + ffprobe_ran", d0["audio_tracks"] and d0["ffprobe_ran"])

        # Improvements batch (was crashing with NameError)
        rep = os.path.join(_TMP, "improve.txt")
        _boxes.clear()
        on_ui(lambda: app._run_improvements_batch(list(app._results), rep))
        check("improvements batch writes report", wait_for(lambda: any("Complete" in str(b) for b in _boxes), 60) and os.path.getsize(rep) > 50, _boxes)
        check("improvements report lists a movie", "Movie:" in io.open(rep, encoding="utf-8").read())
        check("no error boxes so far", not any(b[0] == "error" for b in _boxes), _boxes)

        rpt = mc.format_health_report(app._results)
        check("health report text", "Health Status Report" in rpt and "ERROR movies" in rpt)

        # Export dialog (UI)
        dlg = on_ui(lambda: mc.ExportListDialog(app, app._results, [app._item_map[i] for i in app.tree.get_children()], "Filmes"))
        on_ui(lambda: (dlg._preset_var.set("All"), dlg._apply_preset()))
        check("export dialog: All preset selects every field", on_ui(dlg.selected_fields) == export_list.ALL_FIELD_KEYS)
        on_ui(lambda: (dlg._field_vars["path"].set(False), dlg._on_field_toggle()))
        check("export dialog: unticking switches to Custom", dlg._preset_var.get() == "Custom")
        on_ui(lambda: (dlg._fmt_var.set("csv_semicolon"), dlg._scope_var.set("view")))
        _target = os.path.join(_TMP, "ui_export.csv")
        fd.asksaveasfilename = lambda **k: _target
        try:
            on_ui(dlg._do_export)
        finally:
            fd.asksaveasfilename = _orig_ask
        with open(_target, newline="", encoding="utf-8-sig") as f:
            rows_out = list(csv.reader(f, delimiter=";"))
        _nk = len(kids())
        check("export dialog: semicolon CSV of current view", len(rows_out) == _nk + 1 and 'Amor, Estranho "Amor"' in [r[0] for r in rows_out], (len(rows_out), _nk))
        check("export prefs remembered", mc.SETTINGS["export_prefs"].get("format") == "csv_semicolon" and "path" not in mc.SETTINGS["export_prefs"]["fields"])
        # second open restores Custom selection
        dlg2 = on_ui(lambda: mc.ExportListDialog(app, app._results, [], "Filmes"))
        check("export dialog: reopened with remembered fields", on_ui(lambda: dlg2._preset_var.get() == "Custom" and not dlg2._field_vars["path"].get() and dlg2._fmt_var.get() == "csv_semicolon"))
        on_ui(dlg2.destroy)

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
            def _smoke():
                _d1 = mc.RatingsCompareDialog(app, "x", None, None, None, None, show_checkboxes=True, fallback_mode=True); _d1.update(); _d1.destroy()
                _d2 = mc.CustomGenreDialog(app, "m", ["x"], show_apply_all=True); _d2.update(); _d2.destroy()
                _d3 = mc._SourceManualEntryDialog(app, "m", "TMDB", show_skip_all=True); _d3.update(); _d3.destroy()
            on_ui(_smoke)
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
        on_ui(lambda: (app.deiconify(), app.update())); time.sleep(0.3)
        def _geom(win):
            m = mc._GEOM_RE.match(on_ui(win.geometry)); return tuple(int(m.group(i)) for i in (1, 2, 3, 4)) if m else None
        def _near(a, b, tol=40):
            return a is not None and b is not None and all(abs(x - y) <= tol for x, y in zip(a, b))
        _cl = on_ui(lambda: (mc._clamp_geometry("800x600+9000+9000", app), mc._clamp_geometry("-5000x-5000+0+0", app), mc._clamp_geometry("", app), mc._clamp_geometry(None, app), mc._clamp_geometry("640x480-200+10", app)))
        check("v0.19 clamp: off-screen position pulled back", _cl[0] is not None and mc._GEOM_RE.match(_cl[0]).group(3).lstrip("+").isdigit() and int(mc._GEOM_RE.match(_cl[0]).group(3)) < 9000)
        check("v0.19 clamp: garbage geometry rejected", _cl[1] is None and _cl[2] is None and _cl[3] is None)
        check("v0.19 clamp: negative x (second monitor) kept when inside the virtual screen or clamped", _cl[4] is not None)
        mc.SETTINGS["window_geometry"] = {}
        wd = on_ui(lambda: mc.TextReportDialog(app, "geomtest", "x\ny", "geomtest"))
        on_ui(lambda: (wd.geometry("700x500+120+80"), wd.update())); time.sleep(0.7); on_ui(wd.update)
        _e = mc.SETTINGS["window_geometry"].get("TextReportDialog:geomtest") or {}
        _m = mc._GEOM_RE.match(_e.get("geometry", ""))
        check("v0.19 <Configure> debounce stores the geometry in memory", bool(_m) and _near(tuple(int(_m.group(i)) for i in (1, 2, 3, 4)), (700, 500, 120, 80)), _e)
        _before = os.path.getmtime(sc.CONFIG_PATH)
        on_ui(wd.destroy); time.sleep(0.3)
        _cfg = json.load(open(sc.CONFIG_PATH, encoding="utf-8"))
        check("v0.19 settings.json written on close with window_geometry", "TextReportDialog:geomtest" in (_cfg.get("window_geometry") or {}), list((_cfg.get("window_geometry") or {}).keys()))
        wd2 = on_ui(lambda: (lambda w: (w.update(), w)[1])(mc.TextReportDialog(app, "geomtest", "x", "geomtest")))
        check("v0.19 reopened dialog restored where it was left", _near(_geom(wd2), (700, 500, 120, 80)), _geom(wd2))
        on_ui(wd2.destroy)
        wd3 = on_ui(lambda: (lambda w: (w.update(), w)[1])(mc.TextReportDialog(app, "other", "x", "other")))
        check("v0.19 same class, other stem → own default geometry", not _near(_geom(wd3), (700, 500, 120, 80), 5), _geom(wd3))
        on_ui(wd3.destroy)
        # off-screen values written into settings.json still open visibly
        mc.SETTINGS["window_geometry"]["ColumnChooserDialog"] = {"geometry": "300x200+9000+9000", "zoomed": False}
        mc.SETTINGS["window_geometry"]["TextReportDialog:bad"] = {"geometry": "-5000x-5000+0+0", "zoomed": False}
        _w = on_ui(lambda: (lambda w: (w.update(), (w.winfo_x(), w.winfo_y(), w.winfo_screenwidth(), w.winfo_screenheight()), w.destroy())[1])(mc.ColumnChooserDialog(app)))
        check("v0.19 off-screen position clamped onto the screen", _w[0] < _w[2] - 100 and _w[1] < _w[3] - 50, _w[:2])
        _w = on_ui(lambda: (lambda w: (w.update(), (w.winfo_width(), w.winfo_height()), w.destroy())[1])(mc.TextReportDialog(app, "bad", "x", "bad")))
        check("v0.19 garbage geometry ignored (default size used)", _w[0] > 300 and _w[1] > 200, _w)
        # non-resizable dialogs: position only
        mc.SETTINGS["window_geometry"]["ColumnChooserDialog"] = {"geometry": "900x900+60+70", "zoomed": False}
        _w = on_ui(lambda: (lambda w: (w.update(), (w.winfo_width(), w.winfo_x(), w.winfo_y()), w.destroy())[1])(mc.ColumnChooserDialog(app)))
        check("v0.19 non-resizable dialog restores position, keeps its own size", _w[0] < 850 and abs(_w[1] - 60) <= 40 and abs(_w[2] - 70) <= 60, _w)
        # main window: zoomed state captured by the close path
        if sys.platform == "win32":   # Tk accepts state("zoomed") only on Windows (CI runs on Linux)
            on_ui(lambda: (app.state("zoomed"), app.update())); time.sleep(0.4)
            on_ui(lambda: (app.update(), app._mc_geom_capture()))
            check("v0.19 main window zoomed state captured", mc.SETTINGS["window_geometry"].get("App", {}).get("zoomed") is True, mc.SETTINGS["window_geometry"].get("App"))
        on_ui(lambda: (app.state("normal"), app.update(), app.geometry("1300x700+30+40"), app.update())); time.sleep(0.7); on_ui(app.update)
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
            _tipS = on_ui(lambda: app._tooltip(next(i for i, d in app._item_map.items() if d["subfolder"] == "Mixed Ids"), mc.COL_SOURCE))
            check("verify worker: Source tooltip shows the result", "Verified" in _tipS and mc.ID_DIFFERENT in _tipS, _tipS)
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
        rd = on_ui(lambda: (lambda w: (w.update(), w)[1])(mc._IdVerifyReportDialog(app, _vrows)))
        _first = rd.sorted_rows()[0]["id_check"]["result"]
        check("verify report: problems sorted first, OK last", _first != mc.ID_OK and rd.sorted_rows()[-1]["id_check"]["result"] == mc.ID_OK, [r["id_check"]["result"] for r in rd.sorted_rows()])
        on_ui(lambda: rd._sort_by("movie"))
        _names = [r["movie_name"] for r in rd.sorted_rows()]
        check("verify report: sort by movie name (displayed title)", _names == sorted(_names, key=str.lower), _names)
        on_ui(lambda: rd._sort_by("movie"))
        check("verify report: second click reverses", [r["movie_name"] for r in rd.sorted_rows()] == list(reversed(_names)))
        _csv = os.path.join(_TMP, "verify.csv"); _txt = os.path.join(_TMP, "verify.txt")
        on_ui(lambda: (rd.save_to(_csv), rd.save_to(_txt)))
        with open(_csv, newline="", encoding="utf-8-sig") as f:
            _rows_csv = list(csv.reader(f))
        check("verify report: CSV + TXT saved", _rows_csv[0][0] == "Movie" and len(_rows_csv) == 6 and "ID verification" in io.open(_txt, encoding="utf-8").read())
        _fix_state = on_ui(lambda: (rd._tree.selection_set(rd._tree.get_children()[0]), rd._update_fix_state(), str(rd._fix_btn.cget("state")))[2])
        check("verify report: Fix… enabled only for non-OK rows", _fix_state == ("normal" if rd.sorted_rows()[0]["id_check"]["result"] != mc.ID_OK else "disabled"))
        on_ui(rd.destroy)
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
            _od = on_ui(lambda: (lambda w: (w.update(), w._ok(), w)[2])(mc._AutoRepairOptionsDialog(app, 3, offer_dry_run=True)))
            check("auto repair: options dialog returns the rating preference + dry run", _od.result == {"rating_pref": "votes", "dry_run": True})
            _pv = on_ui(lambda: (lambda w: (w.update(), w._run(), w)[2])(mc._PreviewRunDialog(app, "preview", "text")))
            check("auto repair: preview dialog Run button", _pv.run is True)
            _cands = mc._tmdb_search_movie("Ask Ids", "2001", "k", "en-US", fetch=_fake_tmdb5)
            _ch = on_ui(lambda: (lambda w: (w.update(), w._apply(), w)[2])(mc._IdChooserDialog(app, "m", "2001", _cands, show_apply_all=True, preselect=0)))
            check("auto repair: chooser returns the selected candidate", _ch.result and _ch.result["tmdb_id"] == "9002" and _ch.skip_all is False)
            # Fix… from the verification report uses the chooser
            _chooser_calls.clear()
            app._ask_id_chooser = lambda name, year, cands, show_apply_all=False, preselect=None: (_chooser_calls.append((name, preselect)) or (cands[0], False))
            _fixed = []
            _old_key = mc.SETTINGS.get("tmdb_api_key", ""); mc.SETTINGS["tmdb_api_key"] = "k"
            on_ui(lambda: app._fix_ids_for(by2["Ask Ids"], on_done=lambda r: _fixed.append(r)))
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
        # (the local on_ui helper of v0.19.0 is now the module-level on_ui — v0.19.1 I9)
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
        _tl = on_ui(lambda: (lambda i: (app._tooltip(i, mc.COL_MOVIE_NAME), app._tooltip(i, mc.COL_LIBRARY)))(next(i for i, d in app._item_map.items() if d["subfolder"] == "Second Lib Movie")))
        check("libraries: Movie Name tooltip shows the library", ("Library: " + LIB2) in _tl[0])
        check("libraries: Library column value + tooltip", app._rv(by["Second Lib Movie"])[mc.COL_LIBRARY] == LIB2 and LIB2 in _tl[1])
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
        check("B4: removal-only change offers a scan with 'Not now' as default", getattr(app, "_lib_prompt", None) is not None and app._lib_prompt.winfo_exists() and app._lib_prompt.default_kind == "none")
        on_ui(lambda: app._lib_prompt._buttons["none"].invoke())
        check("B4: 'Not now' closes the prompt and starts nothing", app._lib_prompt is None and not app._scanning)
        check("libraries dialog: removing a library drops its rows and saves the list", mc.SETTINGS["library_folders"] == [LIB] and not any(r["library_root"] == LIB2 for r in app._results) and json.load(open(sc.CONFIG_PATH, encoding="utf-8"))["library_folders"] == [LIB], mc.SETTINGS["library_folders"])
        check("libraries: duplicates recomputed after removal", not (({r["subfolder"]: r for r in app._results}["Perfect Movie"].get("duplicate_of") or []) and "Perfect Movie Copy2" in {r["subfolder"]: r for r in app._results}["Perfect Movie"]["duplicate_of"]))
        check("libraries: last_folder kept = first library", mc.SETTINGS["last_folder"] == LIB)
        _boxes.clear()

        # Settings dialog restores through the hook
        mc.SETTINGS["window_geometry"]["SettingsDialog"] = {"geometry": "900x700+90+60", "zoomed": False}
        _boxes.clear()

        # ── v0.19.1 I2: Ratings Sync skips sources that could not be asked ────
        section("5h. ratings sync — unreachable source (v0.19.1 I2)")
        wait_for(app._refresh_idle, 15)
        by = {r["subfolder"]: r for r in app._results}
        _ofr, _oom = mc._fetch_tmdb_rating, mc._fetch_omdb_rating
        _asked = []
        mc._fetch_tmdb_rating = lambda tid, key: (mc._note_fetch_error("TMDb", mc.urllib.error.URLError("timed out") if hasattr(mc, "urllib") else RuntimeError("timed out")), (None, None))[1]
        mc._fetch_omdb_rating = lambda iid, key: (None, None)
        app._ask_ratings_dialog = lambda *a, **k: (_asked.append(1), {"choice": "cancel"})[1]
        try:
            _before = [_rating_of(by[n]) for n in ("Perfect Movie", "Rating Conflict")]
            _boxes.clear()
            app._sync_ratings_worker([by["Perfect Movie"], by["Rating Conflict"]], "k", "k", None)
            wait_for(lambda: any("Ratings Sync Complete" in str(b) for b in _boxes), 10)
            check("I2: unreachable source → no zero-votes prompt, nothing written", not _asked and [_rating_of(by[n]) for n in ("Perfect Movie", "Rating Conflict")] == _before, (_asked, _before))
            check("I2: summary lists the movies that could not be checked", any("could not be reached" in str(b) and "2 movie(s) skipped" in str(b) for b in _boxes), _boxes)
        finally:
            mc._fetch_tmdb_rating, mc._fetch_omdb_rating = _ofr, _oom
            del app._ask_ratings_dialog
        _boxes.clear()

        # ── v0.19.1 B1: Normalize Genres syncs NFO and XML ────────────────────
        section("5i. normalize genres sync (v0.19.1 B1)")
        wait_for(app._refresh_idle, 15)
        by = {r["subfolder"]: r for r in app._results}
        _orig_ask_ui2 = app._ask_on_ui
        app._ask_on_ui = lambda make, read, timeout=600: (False, False)       # keep custom genres
        try:
            app._normalize_genres_worker([by["Genres Only XML"], by["Genres Only NFO"], by["Genres Wrong Tags"]], None)
            wait_for(lambda: app._refresh_idle(), 20); time.sleep(0.3); wait_for(app._refresh_idle, 20)
        finally:
            app._ask_on_ui = _orig_ask_ui2
        import xml.etree.ElementTree as _ETg
        def _nfo_g(n): return mc.get_genres_from_nfo(by[n]["nfo_path"])
        def _xml_g(n): return mc.get_genres_from_xml(by[n]["xml_path"])
        check("B1: XML-only genres copied to the NFO as <genre>", _nfo_g("Genres Only XML") == ["Comedy", "Family"] and _xml_g("Genres Only XML") == ["Comedy", "Family"], (_nfo_g("Genres Only XML"), _xml_g("Genres Only XML")))
        check("B1: NFO-only genres copied to the XML <Genres>", _xml_g("Genres Only NFO") == ["Drama"], _xml_g("Genres Only NFO"))
        _wt = io.open(by["Genres Wrong Tags"]["nfo_path"], encoding="utf-8").read()
        check("B1: <Genres>/<Genre> in NFO converted to Kodi <genre> (Sci-Fi normalized)", "<Genres>" not in _wt and "<Genre>" not in _wt and _nfo_g("Genres Wrong Tags") == ["Action", "Science Fiction"] and _xml_g("Genres Wrong Tags") == ["Action", "Science Fiction"], (_nfo_g("Genres Wrong Tags"), _wt[-400:]))
        _okxml = True
        for n in ("Genres Only XML", "Genres Only NFO", "Genres Wrong Tags"):
            for k in ("nfo_path", "xml_path"):
                try: _ETg.parse(by[n][k])
                except Exception: _okxml = False
        check("B1: all rewritten files are valid XML", _okxml)
        by2 = {r["subfolder"]: r for r in app._results}
        check("B1: warnings gone after the automatic refresh", not any(("genres only" in x) or ("genre tags" in x) for n in ("Genres Only XML", "Genres Only NFO", "Genres Wrong Tags") for x in by2[n]["health_reasons"]), [by2[n]["health_reasons"] for n in ("Genres Only XML", "Genres Only NFO", "Genres Wrong Tags")])
        _boxes.clear()

        # ── v0.19.1 B2: deleted movie folders leave the table ─────────────────
        section("5j. deleted movie folders (v0.19.1 B2)")
        on_ui2 = on_ui      # v0.19.1 I9: one helper (name kept for the later sections)
        wait_for(app._refresh_idle, 15)
        _dm = make_movie("Delete Me Twin", title="Perfect Movie", same_ids_as="Perfect Movie", video=False)
        on_ui2(lambda: app._start_quick_scan(app._scope_roots())); wait_for(lambda: not app._scanning, 60)
        by = {r["subfolder"]: r for r in app._results}
        check("B2: twin flagged as duplicate before the delete", "Delete Me Twin" in (by["Perfect Movie"].get("duplicate_of") or []), by["Perfect Movie"].get("duplicate_of"))
        shutil.rmtree(_dm)
        _iid_dm = next(i for i, d in app._item_map.items() if d["subfolder"] == "Delete Me Twin")
        _boxes.clear()
        on_ui2(lambda: app._reval_no_ffmpeg(_iid_dm, app._item_map[_iid_dm]))
        by = {r["subfolder"]: r for r in app._results}
        check("B2: Update on a deleted folder removes the row (no error box)", "Delete Me Twin" not in by and not any(b[0] == "error" for b in _boxes) and not any(d["subfolder"] == "Delete Me Twin" for d in app._item_map.values()), _boxes)
        check("B2: twin loses the duplicate warning", not (by["Perfect Movie"].get("duplicate_of") or []) or "Delete Me Twin" not in by["Perfect Movie"]["duplicate_of"])
        check("B2: cache updated + status bar message", not any(r["subfolder"] == "Delete Me Twin" for r in sc.load_results_cache()) and "Removed 1 movie" in app._sb_action.cget("text"), app._sb_action.cget("text"))
        _dm2 = make_movie("Delete Me Refresh", video=False)
        on_ui2(lambda: app._start_quick_scan(app._scope_roots())); wait_for(lambda: not app._scanning, 60)
        shutil.rmtree(_dm2)
        _d2 = {r["subfolder"]: r for r in app._results}["Delete Me Refresh"]
        app._schedule_refresh([_d2["subfolder_path"]])
        time.sleep(0.2); wait_for(app._refresh_idle, 20)
        check("B2: automatic refresh removes a deleted folder", "Delete Me Refresh" not in {r["subfolder"] for r in app._results})
        check("B2: offline library root → kept (not deleted)", app._folder_gone({"subfolder_path": os.path.join("Q:\\nowhere_root_x", "m")}) == "offline")
        _keep = list(app._results)[0]
        on_ui2(lambda: app._remove_from_list([_keep]))
        check("B2: right-click Remove from list drops the row (files untouched)", _keep["subfolder"] not in {r["subfolder"] for r in app._results} and os.path.isdir(_keep["subfolder_path"]))
        on_ui2(lambda: app._start_quick_scan(app._scope_roots())); wait_for(lambda: not app._scanning, 60)
        check("B2: a removed-but-existing movie comes back with the next scan", _keep["subfolder"] in {r["subfolder"] for r in app._results})
        _boxes.clear()

        # ── v0.19.1 B3/B4: normalised paths + scan prompt after adding ────────
        section("5k. library paths + scan prompt (v0.19.1 B3/B4)")
        wait_for(app._refresh_idle, 15)
        LIB3 = os.path.join(_TMP, "Filmes3"); os.makedirs(os.path.join(LIB3, "Lib3 Movie"), exist_ok=True)
        ld3 = on_ui2(lambda: mc._LibrariesDialog(app))
        on_ui2(lambda: ld3.add_path(LIB3.replace("\\", "/")))
        if sys.platform == "win32": check("B3: dialog shows the added path with backslashes", ld3._items[-1] == os.path.normpath(LIB3) and "/" not in ld3._items[-1], ld3._items)   # Windows path style; CI runs on Linux
        on_ui2(lambda: ld3._ok())
        if sys.platform == "win32": check("B3: settings store backslash paths", all("/" not in x for x in mc.SETTINGS["library_folders"]), mc.SETTINGS["library_folders"])   # Windows path style; CI runs on Linux
        check("B4: adding a library offers a scan with Quick Scan as default", app._lib_prompt is not None and app._lib_prompt.default_kind == "quick")
        on_ui2(lambda: app._lib_prompt._buttons["quick"].invoke())
        wait_for(lambda: not app._scanning, 60); time.sleep(0.3); wait_for(lambda: not app._scanning, 60)
        check("B4: Quick Scan from the prompt adds the new library's movie", "Lib3 Movie" in {r["subfolder"] for r in app._results})
        check("B4: no prompt when the list did not change", (on_ui2(lambda: app._set_libraries(app._libraries())) or (set(), set())) == (set(), set()))
        on_ui2(lambda: app._set_libraries([x for x in app._libraries() if mc._pkey(x) != mc._pkey(LIB3)]))
        _boxes.clear()

        # ── v0.19.1 B5: Normalize Genres fetches missing genres online ────────
        section("5l. genres from TMDb/OMDb (v0.19.1 B5)")
        wait_for(app._refresh_idle, 15)
        by = {r["subfolder"]: r for r in app._results}
        by["No Genres Wrong Film"]["id_check"] = {"result": mc.ID_OTHER}
        _orl, _ohg = mc._tmdb_rate_limited_fetch, mc._http_get_json
        def _f_tmdb(url, timeout=15):
            if "/movie/88801?" in url: return {"id": 88801, "genres": [{"name": "Comedy"}, {"name": "Science Fiction"}]}
            if "/movie/88802?" in url: return {"id": 88802, "genres": []}
            raise AssertionError("unexpected " + url)
        def _f_http(service, url, timeout=15):
            if service == "omdb" and "tt8880002" in url: return {"Response": "True", "Genre": "Drama, Sci-Fi"}
            return _orl(url, timeout) if service == "tmdb" else {"Response": "False"}
        mc._tmdb_rate_limited_fetch = _f_tmdb; mc._http_get_json = _f_http
        _old_k = (mc.SETTINGS.get("tmdb_api_key", ""), mc.SETTINGS.get("omdb_api_key", ""))
        mc.SETTINGS["tmdb_api_key"] = "k"; mc.SETTINGS["omdb_api_key"] = "k"
        _previews = []
        app._ask_genre_preview = lambda text: (_previews.append(text), True)[1]
        try:
            _boxes.clear()
            app._normalize_genres_worker([by[n] for n in ("No Genres TMDb", "No Genres OMDb", "No Genres No Id", "No Genres Wrong Film")], None)
            time.sleep(0.3); wait_for(app._refresh_idle, 20)
        finally:
            mc._tmdb_rate_limited_fetch, mc._http_get_json = _orl, _ohg
            mc.SETTINGS["tmdb_api_key"], mc.SETTINGS["omdb_api_key"] = _old_k
            del app._ask_genre_preview
        _pv = _previews[0] if _previews else ""
        check("B5: one preview listing every fetched movie and the skipped ones", len(_previews) == 1 and "No Genres TMDb" in _pv and "Comedy/Science Fiction" in _pv and "No Genres No Id: no IMDb/TMDb ID" in _pv and "Verify IDs says" in _pv, _pv)
        check("B5: TMDb genres written to NFO and XML", mc.get_genres_from_nfo(by["No Genres TMDb"]["nfo_path"]) == ["Comedy", "Science Fiction"] and mc.get_genres_from_xml(by["No Genres TMDb"]["xml_path"]) == ["Comedy", "Science Fiction"])
        check("B5: OMDb fallback (Sci-Fi → Science Fiction)", mc.get_genres_from_nfo(by["No Genres OMDb"]["nfo_path"]) == ["Drama", "Science Fiction"], mc.get_genres_from_nfo(by["No Genres OMDb"]["nfo_path"]))
        check("B5: no ID / wrong-film ID → nothing written", mc.get_genres_from_nfo(by["No Genres No Id"]["nfo_path"]) == [] and mc.get_genres_from_nfo(by["No Genres Wrong Film"]["nfo_path"]) == [])
        by2 = {r["subfolder"]: r for r in app._results}
        check("B5: rows refreshed — 'Missing genre' gone for the fetched movies", not any("Missing genre" in x for x in by2["No Genres TMDb"]["health_reasons"]) and any("Missing genre" in x for x in by2["No Genres No Id"]["health_reasons"]))
        # preview declined → nothing written
        app._ask_genre_preview = lambda text: False
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {"id": 1, "genres": [{"name": "War"}]}
        mc.SETTINGS["tmdb_api_key"] = "k"
        try:
            by2["No Genres Wrong Film"]["id_check"] = None
            app._normalize_genres_worker([by2["No Genres Wrong Film"]], None); time.sleep(0.3)
        finally:
            mc._tmdb_rate_limited_fetch = _orl; mc.SETTINGS["tmdb_api_key"] = _old_k[0]; del app._ask_genre_preview
        check("B5: declining the preview writes nothing", mc.get_genres_from_nfo(by2["No Genres Wrong Film"]["nfo_path"]) == [])
        _boxes.clear()

        # ── v0.19.1 B6/B7: double-click on ✕ files, Shift paging ──────────────
        section("5m. double-click + Shift paging (v0.19.1 B6/B7)")
        wait_for(app._refresh_idle, 15)
        _opened = []; _orig_oe = mc.open_in_editor; _orig_ed = mc.ErrorDialog
        mc.open_in_editor = lambda pth: _opened.append(pth)
        mc.ErrorDialog = lambda *a, **k: _opened.append("ERRORDIALOG")
        try:
            _bad = {r["subfolder"]: r for r in app._results}["Broken XML"]
            _acts = app._get_dblclick_actions()
            on_ui(lambda: _acts["open_xml_unified"](app, _bad))
            check("B6: double-click on a ✕ XML opens the file, not the error list", _opened == [_bad["xml_path"]], _opened)
            _tip = on_ui(lambda: app._tooltip(next(i for i, d in app._item_map.items() if d["subfolder"] == "Broken XML"), mc.COL_XML)) or ""
            check("B6: hover lists the errors and says double-click opens the file", "parse error" in _tip and "Line" in _tip and "Double-click to open the file" in _tip and "[!] XML errors" in _tip, _tip)
        finally:
            mc.open_in_editor = _orig_oe; mc.ErrorDialog = _orig_ed
        class _Ev:
            def __init__(s, k): s.keysym = k
        def _sel_idx():
            ch = list(app.tree.get_children()); return [ch.index(i) for i in app.tree.selection()]
        def _do(k): return on_ui2(lambda: app._shift_page(_Ev(k)))
        on_ui2(lambda: (app._set_health_filter(None), app._refresh_table()))
        _n = len(app.tree.get_children())
        _pg = on_ui2(app._page_rows)
        on_ui2(lambda: (app.tree.selection_set(list(app.tree.get_children())[2]), app._reset_sel_anchor()))
        _do("Next")
        check("B7: Shift+PageDown extends from the anchor by one page", _sel_idx() == list(range(2, min(_n - 1, 2 + _pg) + 1)), (_sel_idx()[:3], _pg))
        _do("End")
        check("B7: Shift+End extends to the last row", _sel_idx() == list(range(2, _n)), (_sel_idx()[:2], _sel_idx()[-1:], _n))
        _do("Home")
        check("B7: Shift+Home extends from the anchor to the first row", _sel_idx() == [0, 1, 2], _sel_idx())
        _do("Prior")
        check("B7: Shift+PageUp keeps the anchor", 2 in _sel_idx() and 0 in _sel_idx())
        check("B7: Shift keys are bound on the table", all(app.tree.bind(k) for k in ("<Shift-Prior>", "<Shift-Next>", "<Shift-Home>", "<Shift-End>")))
        _boxes.clear()

        # ── v0.19.1 B8: Enter ID dialog + Search Sources apply ────────────────
        section("5n. Enter ID dialog (v0.19.1 B8)")
        wait_for(app._refresh_idle, 15)
        _old_k8 = mc.SETTINGS.get("tmdb_api_key", ""); mc.SETTINGS["tmdb_api_key"] = "k"
        try:
            ed = on_ui2(lambda: mc._EnterIdDialog(app, "Typed Id Test"))
            on_ui2(lambda: (ed._imdb_var.set("tt0133093"), ed.lookup(fetch=_f8, sync=True)))
            check("B8: dialog shows the found film and enables Apply", "The Matrix" in ed._info.cget("text") and str(ed._apply_btn.cget("state")) == "normal", ed._info.cget("text"))
            on_ui2(lambda: ed._apply())
            check("B8: Apply returns the candidate", ed.result and ed.result["tmdb_id"] == "603")
            ed2 = on_ui2(lambda: mc._EnterIdDialog(app, "Typed Id Test"))
            on_ui2(lambda: (ed2._tmdb_var.set("x1"), ed2.lookup(fetch=_f8, sync=True)))
            check("B8: invalid input → message, Apply stays disabled", "digits only" in ed2._info.cget("text") and str(ed2._apply_btn.cget("state")) == "disabled")
            on_ui2(lambda: ed2.destroy())
            # Search Sources window: Enter ID… writes both IDs to NFO and XML
            _row8 = {r["subfolder"]: r for r in app._results}["Ask Ids"]
            _orig_cls = mc._EnterIdDialog
            class _AutoEnter:
                def __init__(s, parent, name, imdb="", tmdb=""): s.result = {"tmdb_id": "603", "imdb_id": "tt0133093"}
                def winfo_exists(s): return False
            mc._EnterIdDialog = _AutoEnter
            _orig_info = mc.messagebox.showinfo
            try:
                ssd = on_ui2(lambda: mc._SearchSourcesResultDialog(app, [{"movie_name": "Ask Ids", "year": "2001", "matches": []}], [_row8]))
                _orig_ww = app.wait_window
                ssd.wait_window = lambda w=None: None
                on_ui2(lambda: ssd._enter_id(_row8, "Ask Ids"))
            finally:
                mc._EnterIdDialog = _orig_cls
            check("B8: Search Sources → Enter ID… writes both IDs", mc.get_movie_ids_robust(_row8["nfo_path"], _row8["xml_path"]) == ("tt0133093", "603"), mc.get_movie_ids_robust(_row8["nfo_path"], _row8["xml_path"]))
        finally:
            mc.SETTINGS["tmdb_api_key"] = _old_k8
        time.sleep(0.3); wait_for(app._refresh_idle, 20)
        _boxes.clear()

        # ── v0.19.1 I3: progress + cancel ─────────────────────────────────────
        section("5o. progress and cancel (v0.19.1 I3)")
        wait_for(app._refresh_idle, 15)
        check("I3: progress from 3 movies up", mc._PROGRESS_MIN == 3)
        rows3 = list(app._results)[:4]
        class _Prog:
            def __init__(s, cancel_after): s.n = 0; s.cancel_after = cancel_after; s.closed = False
            @property
            def cancelled(s): return s.n >= s.cancel_after
            def update(s, k): s.n = k
            def close(s): s.closed = True
        _shown = []
        _orig_ssd = mc._SearchSourcesResultDialog
        mc._SearchSourcesResultDialog = lambda parent, results, rows: _shown.append((results, rows))
        _orig_rl3 = mc._tmdb_rate_limited_fetch
        _calls3 = []
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: (_calls3.append(url), {"results": [{"id": 5, "title": "x", "release_date": "2001"}]} if "/search/" in url else {"imdb_id": "tt0000005"})[1]
        try:
            _p = _Prog(2)
            app._search_sources_worker(rows3, "k", True, _p)
            wait_for(lambda: bool(_shown), 10)
            check("I3: Search Sources stops at Cancel and shows the partial results", _shown and len(_shown[0][0]) == 2 and len(_shown[0][1]) == 2 and _p.closed, (len(_shown[0][0]) if _shown else None))
        finally:
            mc._SearchSourcesResultDialog = _orig_ssd; mc._tmdb_rate_limited_fetch = _orig_rl3
        _imp = []
        _orig_imd = mc.ImprovementsDialog
        mc.ImprovementsDialog = lambda parent, report, n: _imp.append((threading.current_thread() is threading.main_thread(), n))
        try:
            on_ui2(lambda: app._run_improvements_on(rows3))
            wait_for(lambda: bool(_imp), 30)
            check("I3: Improvements Check for a selection runs in a worker, report on the UI thread", _imp and _imp[0] == (True, 4), _imp)
        finally:
            mc.ImprovementsDialog = _orig_imd
            time.sleep(0.3)
        _boxes.clear()

        # ── v0.19.1 B13: Source tooltip for placeholder tags ───────────────────   ### NEW v0.19.1 B13 ###
        section("5p. empty ID tags in the table (v0.19.1 B13)")
        wait_for(app._refresh_idle, 15)
        _tip13 = on_ui(lambda: app._tooltip(next(i for i, d in app._item_map.items() if d["subfolder"] == "Empty TMDB Tags"), mc.COL_SOURCE)) or ""
        check("B13: Source tooltip says 'TMDB: — (empty tags ready to fill)'", "TMDB: — (empty tags ready to fill)" in _tip13 and "parse error" not in _tip13, _tip13)
        _tip13b = on_ui(lambda: app._tooltip(next(i for i, d in app._item_map.items() if d["subfolder"] == "Half Empty TMDB"), mc.COL_SOURCE)) or ""
        check("B13: partly empty → value shown + '(some tags are empty)', not 'parse error'", "(some tags are empty)" in _tip13b and "parse error" not in _tip13b, _tip13b)

        # ── v0.19.1 B14: Search Sources / Enter ID… for an IMDb-only film ─────   ### NEW v0.19.1 B14 ###
        section("5q. IMDb-only film — Confirm IMDb / Enter ID (v0.19.1 B14)")
        wait_for(app._refresh_idle, 15)
        make_movie("Padre Pio, Uomo di Dio (1999)", title="Padre Pio, homem de Deus", nfo_imdb=_PP_IMDB, xml_imdb=_PP_IMDB,
                   nfo_tmdb=None, xml_tmdb="", nfo_original="Padre Pio, uomo di Dio", xml_original="Padre Pio, uomo di Dio",
                   nfo_year="1999", xml_year="1999", video=False)
        make_movie("Padre Pio Enter Id", title="Padre Pio Enter Id", nfo_imdb="tt12817761", xml_imdb="tt12817761",
                   nfo_tmdb=None, xml_tmdb=None, video=False)
        on_ui(lambda: app._start_quick_scan(app._scope_roots())); wait_for(lambda: not app._scanning, 60)
        by = {r["subfolder"]: r for r in app._results}
        _rowpp, _rowpp2 = by["Padre Pio, Uomo di Dio (1999)"], by["Padre Pio Enter Id"]
        def _f14b(url, timeout=15):
            if "/find/tt1281776" in url and _PP_IMDB not in url: return {"movie_results": []}
            return _f14(url, timeout)
        _epp = mc._search_sources_for_row(_rowpp, "k", "pt-BR", "ok", fetch=_f14b, omdb_fetch=_omdb14)
        ssd14 = on_ui(lambda: mc._SearchSourcesResultDialog(app, [_epp], [_rowpp]))
        check("B14: header 'Current: IMDb tt12817760 · TMDb —'", "Current: IMDb tt12817760 · TMDb —" in ssd14._labels, ssd14._labels)
        _pb = ssd14._pinned_btns.get(_rowpp["movie_name"])
        check("B14: pinned row 'IMDb tt12817760 — not on TMDb · Padre Pio, uomo di Dio (1999)' + Confirm IMDb", "IMDb tt12817760 — not on TMDb · Padre Pio, uomo di Dio (1999)" in ssd14._labels and _pb and _pb[0] == "Confirm IMDb", (ssd14._labels, _pb))
        _boxes.clear()
        on_ui(lambda: _pb[1].invoke())
        time.sleep(0.3); wait_for(app._refresh_idle, 20)
        _nt, _xt = io.open(_rowpp["nfo_path"], encoding="utf-8").read(), io.open(_rowpp["xml_path"], encoding="utf-8").read()
        _ok_tags = all(s in _nt for s in (f"<id>{_PP_IMDB}</id>", f"<imdbid>{_PP_IMDB}</imdbid>", f'<id moviedb="imdb">{_PP_IMDB}</id>')) \
                   and all(f"<{t}>{_PP_IMDB}</{t}>" in _xt for t in ("IMDB", "IMDbId", "IMDB_ID"))
        _empty_tm = "<tmdbid></tmdbid>" in _nt and '<id moviedb="tmdb"></id>' in _nt and all(f"<{t}></{t}>" in _xt for t in ("TMDB", "TMDbId", "TMDB_ID"))
        check("B14: Confirm IMDb → tt12817760 in every IMDb tag of both files, empty TMDb tags, valid XML", _ok_tags and _empty_tm and _valid(_rowpp["nfo_path"], _rowpp["xml_path"]), (_nt[-400:], _xt[-400:]))
        _rp = {r["subfolder"]: r for r in app._results}["Padre Pio, Uomo di Dio (1999)"]
        check("B14: row refreshed — IMDb ⬤, TMDb ○, id_check 'OK (IMDb only — not on TMDb)'", _rp["source_imdb_status"] == mc.STATUS_OK and _rp["source_tmdb_status"] == mc.STATUS_MISSING and (_rp.get("id_check") or {}).get("result") == mc.ID_IMDB_ONLY, (_rp["source_imdb_status"], _rp["source_tmdb_status"], _rp.get("id_check")))
        check("B14: 'Confirmed' message, no error box", any(b[0] == "info" and "Confirmed" in str(b[1]) for b in _boxes) and not any(b[0] == "error" for b in _boxes), _boxes)
        # Enter ID… with an IMDb ID TMDb does not know
        _ok14 = (mc.SETTINGS.get("tmdb_api_key", ""), mc.SETTINGS.get("omdb_api_key", ""))
        mc.SETTINGS["tmdb_api_key"] = "k"; mc.SETTINGS["omdb_api_key"] = "k"
        try:
            ed14 = on_ui(lambda: mc._EnterIdDialog(app, "Padre Pio Enter Id"))
            ed14._omdb_fetch = lambda url: {"Response": "True", "Title": "Padre Pio Two", "Year": "2001"}
            on_ui(lambda: (ed14._imdb_var.set("tt12817761"), ed14.lookup(fetch=_f14b, sync=True)))
            _inf = on_ui(lambda: ed14._info.cget("text")); _st = on_ui(lambda: str(ed14._apply_btn.cget("state")))
            check("B14: Enter ID… accepts an IMDb ID unknown to TMDb ('Not on TMDb — IMDb only', OMDb title, Apply enabled)", "Not on TMDb — IMDb only" in _inf and "Padre Pio Two" in _inf and _st == "normal", (_inf, _st))
            on_ui(ed14._apply)
            _res14 = ed14.result
            _orig_cls14 = mc._EnterIdDialog
            class _AutoEnter14:
                def __init__(s, parent, name, imdb="", tmdb=""): s.result = _res14
            mc._EnterIdDialog = _AutoEnter14
            try:
                ssd14b = on_ui(lambda: mc._SearchSourcesResultDialog(app, [{"movie_name": "Padre Pio Enter Id", "year": "", "matches": []}], [_rowpp2]))
                ssd14b.wait_window = lambda w=None: None
                on_ui(lambda: ssd14b._enter_id(_rowpp2, "Padre Pio Enter Id"))
            finally:
                mc._EnterIdDialog = _orig_cls14
        finally:
            mc.SETTINGS["tmdb_api_key"], mc.SETTINGS["omdb_api_key"] = _ok14
        time.sleep(0.3); wait_for(app._refresh_idle, 20)
        _n2 = io.open(_rowpp2["nfo_path"], encoding="utf-8").read()
        _rp2 = {r["subfolder"]: r for r in app._results}["Padre Pio Enter Id"]
        check("B14: Enter ID… IMDb-only Apply writes the IMDb ID + empty TMDb tags and records 'IMDb only'", "<imdbid>tt12817761</imdbid>" in _n2 and "<tmdbid></tmdbid>" in _n2 and (_rp2.get("id_check") or {}).get("result") == mc.ID_IMDB_ONLY, (_n2[-300:], _rp2.get("id_check")))
        # TMDb-only movie: pinned 'From your current TMDb ID' + Apply
        ssd14c = on_ui(lambda: mc._SearchSourcesResultDialog(app, [_e14c], [_r14c]))
        _pc = ssd14c._pinned_btns.get(_r14c["movie_name"])
        check("B14: TMDb-only movie → 'From your current TMDb ID: The Matrix …' with Apply", any(l.startswith("From your current TMDb ID:  The Matrix") for l in ssd14c._labels) and _pc and _pc[0] == "Apply", ssd14c._labels)
        on_ui(ssd14c.destroy)
        _boxes.clear()

        # ── v0.19.1 B15: Hard-coded subtitles… ─────────────────────────────────   ### NEW v0.19.1 B15 ###
        section("5r. hard-coded subtitles dialog (v0.19.1 B15)")
        wait_for(app._refresh_idle, 15)
        _hm = make_movie("Hardsub Movie", title="Hardsub Movie")
        _hm2 = make_movie("Hardsub Movie Two", title="Hardsub Movie Two", video=False)
        for _f in os.listdir(_hm):
            if _f.endswith(".srt"): os.remove(os.path.join(_hm, _f))            # no PT subtitle → POR missing
        on_ui(lambda: app._start_quick_scan(app._scope_roots())); wait_for(lambda: not app._scanning, 60)
        _by = {r["subfolder"]: r for r in app._results}
        if SAMPLE_VIDEO:
            check("B15: before marking — 'Required subtitle language not found (POR)'", any("Required subtitle language not found (POR)" in x for x in _by["Hardsub Movie"]["health_reasons"]), _by["Hardsub Movie"]["health_reasons"])
        _hd = on_ui(lambda: app._hardsubs_for([_by["Hardsub Movie"]]))
        check("B15: dialog lists the Health Rules languages with checkboxes + Other…", all(c in _hd._vars for c in ("POR", "ENG", "SPA", "FRE", "GER", "ITA")) and not any(v.get() for v in _hd._vars.values()))
        def _hs_wait():
            """B15 worker done = its status-bar message (v0.19.1 B19 run: fixed a test race —
            reading the NFO while the worker replaced it gave PermissionError on Windows)."""
            wait_for(lambda: "Hard-coded subtitles" in on_ui(lambda: app._sb_action.cget("text")), 30)
            time.sleep(0.2); wait_for(app._refresh_idle, 20)
        on_ui(lambda: app._sb_action.configure(text=''))
        on_ui(lambda: (_hd._vars["POR"].set(True), _hd._vars["ENG"].set(True), _hd._apply()))
        _hs_wait()
        _rh = {r["subfolder"]: r for r in app._results}["Hardsub Movie"]
        _nh = io.open(_rh["nfo_path"], encoding="utf-8").read()
        check("B15: Apply writes <tag>Hardsub ENG/POR</tag> and the XML <Tags>, row rescanned", "<tag>Hardsub ENG</tag>" in _nh and "<tag>Hardsub POR</tag>" in _nh and "<Tag>Hardsub POR</Tag>" in io.open(_rh["xml_path"], encoding="utf-8").read() and _rh["subs_hard"] == ["ENG", "POR"], (_rh.get("subs_hard"), _nh[-200:]))
        check("B15: Subtitles column shows 'Hard: ENG, POR'", "Hard: ENG, POR" in _rh["subs_summary"], _rh["subs_summary"])
        if SAMPLE_VIDEO:
            check("B15: Lang OK? = Y and no 'Required subtitle language' warning", _rh["lang_ok"] == "Y" and not any("Required subtitle language" in x for x in _rh["health_reasons"]), (_rh["lang_ok"], _rh["health_reasons"]))
        _tip15 = on_ui(lambda: app._tooltip(next(i for i, d in app._item_map.items() if d["subfolder"] == "Hardsub Movie"), mc.COL_SUBS)) or ""
        check("B15: tooltip 'burned into the picture (marked by you)'", "Hard-coded: ENG, POR — burned into the picture (marked by you)" in _tip15, _tip15)
        _hd2 = on_ui(lambda: app._hardsubs_for([_rh]))
        check("B15: reopened dialog starts with the marked languages ticked", _hd2._vars["POR"].get() and _hd2._vars["ENG"].get() and not _hd2._vars["SPA"].get())
        on_ui(lambda: (_hd2._other_var.set("PO"), _hd2._apply()))
        check("B15: an invalid 'Other…' code is refused with a message", on_ui(_hd2.winfo_exists) and "not a 3-letter" in on_ui(lambda: _hd2._msg.cget("text")))
        on_ui(lambda: app._sb_action.configure(text=''))
        on_ui(lambda: (_hd2._other_var.set(""), _hd2._vars["ENG"].set(False), _hd2._apply()))
        _hs_wait()
        _rh = {r["subfolder"]: r for r in app._results}["Hardsub Movie"]
        check("B15: unticking ENG removes only that tag", _rh["subs_hard"] == ["POR"] and "Hardsub ENG" not in io.open(_rh["nfo_path"], encoding="utf-8").read(), _rh.get("subs_hard"))
        # selection: confirmation; declining writes nothing; accepting sets exactly the ticked set on every movie
        _sel = [_rh, {r["subfolder"]: r for r in app._results}["Hardsub Movie Two"]]
        on_ui(lambda: app._hardsubs_apply(_sel, ["SPA"]))          # askyesno is patched to answer No
        time.sleep(0.4)
        check("B15: selection — declining the confirmation writes nothing", mc.get_hardsub_langs(_sel[1]["nfo_path"], _sel[1]["xml_path"]) == [])
        on_ui(lambda: app._sb_action.configure(text=''))
        on_ui(lambda: app._hardsubs_apply(_sel, ["SPA"], confirm=False))
        _hs_wait()
        check("B15: selection — every selected movie gets exactly the ticked languages", all(mc.get_hardsub_langs(d["nfo_path"], d["xml_path"]) == ["SPA"] for d in _sel), [mc.get_hardsub_langs(d["nfo_path"], d["xml_path"]) for d in _sel])
        _boxes.clear()

        # ── v0.19.1 B16: Audio tooltip names the source of a filled language ──   ### NEW v0.19.1 B16 ###
        section("5s. audio language tooltip (v0.19.1 B16)")
        def _tip16():
            app._item_map["__b16__"] = {"audio_tracks": [{"language": "POR", "language_src": "NFO", "language_raw": "UND", "codec": "AAC", "channels": "2.0", "bitrate": 128}]}
            try:
                return app._tooltip("__b16__", mc.COL_AUDIO)
            finally:
                app._item_map.pop("__b16__", None)
        _t16 = on_ui(_tip16) or ""
        check("B16: Audio tooltip 'POR — from NFO (FFprobe: undefined)'", "Language: POR — from NFO (FFprobe: undefined)" in _t16, _t16)

        # ── v0.19.1 B17: Replace All Backdrops count warning ───────────────────   ### NEW v0.19.1 B17 ###
        section("5t. Replace All Backdrops count warning (v0.19.1 B17)")
        _m17 = mc.backdrop_count_message(14, 8)
        check("B17: fewer online → 'You have 14 … TMDb offers 8 … leave you with 8 (6 fewer)' + 'Replace anyway'", _m17[0] == "You have 14 backdrops. TMDb offers 8.\nReplacing would leave you with 8 (6 fewer)." and _m17[1] == "Replace anyway" and _m17[2] is True, _m17)
        _m17b = mc.backdrop_count_message(3, 8)
        check("B17: more online → both numbers in a one-step confirmation ('Replace')", "You have 3 backdrops. TMDb offers 8." in _m17b[0] and "gives you 8 (5 more)" in _m17b[0] and _m17b[1] == "Replace" and _m17b[2] is False, _m17b)
        # the real chain: worker → _ask_on_ui → dialog → answer
        _ans = {}
        def _ask_thread(): _ans["r"] = app._ask_backdrop_count("Chain Test", 14, 8)
        threading.Thread(target=_ask_thread, daemon=True).start()
        wait_for(lambda: on_ui(lambda: any(isinstance(w, mc._BackdropCountDialog) for w in app.winfo_children())), 10)
        _dlg17 = on_ui(lambda: next(w for w in app.winfo_children() if isinstance(w, mc._BackdropCountDialog)))
        check("B17: dialog shows the counts and 'Replace anyway'", "6 fewer" in _dlg17.message and _dlg17.button_label == "Replace anyway")
        on_ui(_dlg17.destroy)                                     # Cancel / [X]
        wait_for(lambda: "r" in _ans, 10)
        check("B17: Cancel / [X] → False", _ans.get("r") is False, _ans)
        # the worker: nothing is backed up or deleted until confirmed
        _d17 = os.path.join(_TMP, "b17", "Backdrop Many"); os.makedirs(_d17, exist_ok=True)
        for _i in range(6):
            _jpeg(os.path.join(_d17, "backdrop.jpg" if _i == 0 else f"backdrop{_i}.jpg"), 640, 360)
        _snap = lambda: sorted((f, os.path.getsize(os.path.join(_d17, f)), os.path.getmtime(os.path.join(_d17, f))) for f in os.listdir(_d17))
        _before17 = _snap()
        _bk = lambda: sorted(n for n in os.listdir(os.path.join(_APP_DIR, "backup")) if "Backdrop" in n and "Many" in n)
        _bk0 = _bk()
        _row17 = {"source_tmdb_val": "717001", "subfolder_path": _d17, "movie_name": "Backdrop Many", "subfolder": "Backdrop Many"}
        _orl17, _odl17 = mc._tmdb_rate_limited_fetch, mc._tmdb_download_image
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {"backdrops": [{"file_path": f"/b{i}.jpg", "width": 1920, "height": 1080} for i in range(3)]}
        def _fake_dl(url, dest):
            _jpeg(dest, 1920, 1080); return True, ""
        mc._tmdb_download_image = _fake_dl
        _asked17 = []
        app._ask_backdrop_count = lambda movie, local_n, online_n: (_asked17.append((movie, local_n, online_n)), False)[1]
        _ok17 = mc.SETTINGS.get("tmdb_api_key", ""); mc.SETTINGS["tmdb_api_key"] = "k"
        try:
            _boxes.clear()
            on_ui(lambda: app._replace_all_backdrops(_row17))
            wait_for(lambda: bool(_asked17), 10); time.sleep(0.5)
            check("B17: counts asked before any change (local 6, online 3)", _asked17 == [("Backdrop Many", 6, 3)], _asked17)
            check("B17: Cancel → every backdrop untouched, no backup made", _snap() == _before17 and _bk() == _bk0, (_snap()[:2], _bk()))
            app._ask_backdrop_count = lambda movie, local_n, online_n: True
            on_ui(lambda: app._replace_all_backdrops(_row17))
            wait_for(lambda: any("Replace All Backdrops" in str(b) for b in _boxes), 20)
            check("B17: 'Replace anyway' → replaced by the 3 online backdrops", len([f for f in os.listdir(_d17) if f.startswith("backdrop")]) == 3, os.listdir(_d17))
            _newbk = [n for n in _bk() if n not in _bk0]
            _bfiles = os.listdir(os.path.join(_APP_DIR, "backup", _newbk[0])) if _newbk else []
            check("B17 (fixed data-loss bug): all 6 original backdrops really are in the backup folder", len([f for f in _bfiles if f.startswith("backdrop")]) == 6, (_newbk, _bfiles))
        finally:
            mc._tmdb_rate_limited_fetch, mc._tmdb_download_image = _orl17, _odl17
            mc.SETTINGS["tmdb_api_key"] = _ok17
            del app._ask_backdrop_count
        _boxes.clear()

        # ── v0.19.1 B18: Fetch dialogs say "Done"; Done waits for a download ─   ### NEW v0.19.1 B18 ###
        section("5u. Fetch dialogs — Done (v0.19.1 B18)")
        _d18 = os.path.join(_TMP, "b18", "Fetch Done Movie"); os.makedirs(_d18, exist_ok=True)
        _jpeg(os.path.join(_d18, "fanart.jpg"), 1280, 720)
        _row18 = {"subfolder_path": _d18, "subfolder": "Fetch Done Movie", "movie_name": "Fetch Done Movie",
                  "poster_path": os.path.join(_d18, "poster.jpg"), "fanart_path": os.path.join(_d18, "fanart.jpg"),
                  "folder_path": os.path.join(_d18, "folder.jpg"), "poster_exists": False, "fanart_exists": True,
                  "folder_exists": False, "backdrop_paths": []}
        _orl18, _odl18 = mc._tmdb_rate_limited_fetch, mc._tmdb_download_image
        _gate = threading.Event()
        def _slow_dl(url, dest):
            _gate.wait(10); _jpeg(dest, 1920, 1080); return True, ""
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {"posters": [], "backdrops": [], "logos": []}
        mc._tmdb_download_image = _slow_dl
        def _btn_texts(w):
            out = []
            for c in w.winfo_children():
                if isinstance(c, tk.Button): out.append(c.cget("text").strip())
                out += _btn_texts(c)
            return out
        try:
            for _kind, _mk in (("Fetch Fanart", lambda: mc._FetchImageDialog(app, _row18, "fanart", "k", "718001")),
                               ("Fetch Poster/Folder", lambda: mc._FetchImageDialog(app, _row18, "poster", "k", "718001")),
                               ("Fetch Backdrops", lambda: mc._FetchBackdropDialog(app, _row18, "k", "718001"))):
                _dlg = on_ui(_mk)
                _bt = on_ui(lambda: _btn_texts(_dlg))
                check(f"B18: {_kind} footer says 'Done', no 'Cancel'", "Done" in _bt and "Cancel" not in _bt, _bt)
                _esc, _wm = on_ui(lambda: (_dlg.bind("<Escape>"), _dlg.protocol("WM_DELETE_WINDOW")))
                on_ui(_dlg._done)
                check(f"B18: {_kind} — Esc and [X] are bound to Done; Done closes it when idle", bool(_esc) and bool(_wm) and "_done" in str(_wm) and not on_ui(_dlg.winfo_exists), (_esc, _wm))
            # Fanart: Done during a running download waits ("Finishing…"), then closes; applied stays True
            _gate.clear(); _boxes.clear()
            _df = on_ui(lambda: mc._FetchImageDialog(app, _row18, "fanart", "k", "718001"))
            on_ui(lambda: _df._apply_image("https://image.tmdb.org/t/p/original/x.jpg"))
            on_ui(_df._done)
            check("B18: Done during a download → 'Finishing…', window stays open", on_ui(_df.winfo_exists) and on_ui(lambda: _df._done_btn.cget("text")).strip() == "Finishing…" and on_ui(lambda: str(_df._done_btn.cget("state"))) == "disabled")
            _gate.set()
            wait_for(lambda: not on_ui(_df.winfo_exists), 10)
            check("B18: …then closes by itself with applied=True (the row refresh still runs)", not on_ui(_df.winfo_exists) and _df.applied is True)
            # Backdrops: same through _download_to
            _gate.clear()
            _db = on_ui(lambda: mc._FetchBackdropDialog(app, _row18, "k", "718001"))
            _res18 = []
            on_ui(lambda: (setattr(_db, "_images", [{"file_path": "/b.jpg"}]), setattr(_db, "_sel_idx", 0),
                           _db._download_to(os.path.join(_d18, "backdrop7.jpg"), lambda ok, info: _res18.append(ok))))
            on_ui(lambda: _db._done_btn.invoke())
            check("B18: Fetch Backdrops — Done waits for the running download", on_ui(_db.winfo_exists) and "Finishing" in on_ui(lambda: _db._done_btn.cget("text")))
            _gate.set()
            wait_for(lambda: not on_ui(_db.winfo_exists), 10)
            check("B18: Fetch Backdrops — closes after the download, file written, applied=True", _res18 == [True] and _db.applied is True and os.path.isfile(os.path.join(_d18, "backdrop7.jpg")))
        finally:
            mc._tmdb_rate_limited_fetch, mc._tmdb_download_image = _orl18, _odl18
            _gate.set()
        _boxes.clear()

        # ── v0.19.1 B23: Kodi naming in the UI (tooltips + Fetch writes) ────────   ### NEW v0.19.1 B23 ###
        section("5v. Kodi naming — tooltips and Fetch Poster (v0.19.1 B23)")
        _rk = scan(_k1, use_ffprobe=False)
        def _tips23():
            app._item_map["__b23__"] = _rk
            try:
                return app._tooltip("__b23__", mc.COL_POSTER), app._tooltip("__b23__", mc.COL_FOLDER)
            finally:
                app._item_map.pop("__b23__", None)
        _tp, _tf = on_ui(_tips23)
        check("B23: poster tooltip names the file found ('Found: … -poster.jpg  (Kodi naming)')", "Found: Kodi Movie (1999)-poster.jpg  (Kodi naming)" in (_tp or ""), _tp)
        check("B23: folder tooltip lists the names looked for and says it is optional", "Looked for: folder.jpg, folder.png" in (_tf or "") and "Optional: Kodi uses" in (_tf or ""), _tf)
        _rp2 = scan(_k2, use_ffprobe=False)
        _orl23, _odl23 = mc._tmdb_rate_limited_fetch, mc._tmdb_download_image
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {"posters": [], "backdrops": [], "logos": []}
        def _dl23(url, dest):
            _jpeg(dest, 1000, 1500, noisy=True); return True, ""
        mc._tmdb_download_image = _dl23
        _bk23 = lambda: sorted(n for n in os.listdir(os.path.join(_APP_DIR, "backup")) if "Kodi" in n and "Png" in n)
        _bk23_0 = _bk23()
        try:
            _fd23 = on_ui(lambda: mc._FetchImageDialog(app, _rp2, "poster", "k", "723001"))
            on_ui(lambda: _fd23._apply_image("https://image.tmdb.org/t/p/original/p.jpg"))
            wait_for(lambda: not on_ui(_fd23.winfo_exists), 15)
        finally:
            mc._tmdb_rate_limited_fetch, mc._tmdb_download_image = _orl23, _odl23
        _files23 = sorted(os.listdir(_k2))
        check("B23: Fetch Poster in a Kodi PNG folder → '<video>-poster.jpg' written, old .png removed, no poster.jpg", "Kodi Png (2001)-poster.jpg" in _files23 and "Kodi Png (2001)-poster.png" not in _files23 and "poster.jpg" not in [f.lower() for f in _files23], _files23)
        _nb = [n for n in _bk23() if n not in _bk23_0]
        # Replace All Backdrops in a Kodi folder: Kodi names in, Kodi extra fanart out
        _k8 = _kodi_dir("Kodi Replace", "Kodi Replace.mkv", {"Kodi Replace.nfo": "nfo", "Kodi Replace-poster.jpg": _P, "Kodi Replace-fanart.jpg": _F, "fanart1.jpg": _F, "Kodi Replace-fanart2.jpg": _F})
        _row8 = {"source_tmdb_val": "723008", "subfolder_path": _k8, "movie_name": "Kodi Replace", "subfolder": "Kodi Replace"}
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {"backdrops": [{"file_path": f"/k{i}.jpg", "width": 1920, "height": 1080} for i in range(3)]}
        mc._tmdb_download_image = _dl23
        app._ask_backdrop_count = lambda movie, a, b: True
        _okk = mc.SETTINGS.get("tmdb_api_key", ""); mc.SETTINGS["tmdb_api_key"] = "k"
        try:
            _boxes.clear()
            on_ui(lambda: app._replace_all_backdrops(_row8))
            wait_for(lambda: any("Replace All Backdrops" in str(b) for b in _boxes), 20)
        finally:
            mc._tmdb_rate_limited_fetch, mc._tmdb_download_image = _orl23, _odl23
            mc.SETTINGS["tmdb_api_key"] = _okk; del app._ask_backdrop_count
        _files8 = sorted(os.listdir(_k8))
        check("B23: Replace All Backdrops in a Kodi folder → '<video>-fanart1..3.jpg', old extra fanart gone, main fanart kept, no backdrop*.jpg",
              [f for f in _files8 if "fanart" in f.lower()] == ["Kodi Replace-fanart.jpg", "Kodi Replace-fanart1.jpg", "Kodi Replace-fanart2.jpg", "Kodi Replace-fanart3.jpg"] and not any(f.startswith("backdrop") for f in _files8), _files8)
        check("B23: the replaced .png poster (and folder.jpg) were backed up first", _nb and any(f.endswith("-poster.png") for f in os.listdir(os.path.join(_APP_DIR, "backup", _nb[0]))), (_nb, os.listdir(os.path.join(_APP_DIR, "backup", _nb[0])) if _nb else None))
        _boxes.clear()

        # ── v0.19.1 B20: Ratings Sync with OMDb's daily limit ──────────────────   ### NEW v0.19.1 B20 ###
        section("5w. Ratings Sync — OMDb refuses (v0.19.1 B20)")
        wait_for(app._refresh_idle, 15)
        _by20 = {r["subfolder"]: r for r in app._results}
        _rows20 = [_by20[n] for n in ("Rating Conflict", "Bad Rating", "Foreign OK")]
        _calls20.clear(); _mode20.update(omdb="limit", tmdb="ok")
        _ofj20b, _osl20b = mc._tmdb_fetch_json, mc.time.sleep
        mc._tmdb_fetch_json = _fake20; mc.time.sleep = lambda x: None
        mc._HTTP_TIMES.clear(); mc._TMDB_RATE_TIMES.clear()
        app._ask_ratings_dialog = lambda *a, **k: {"choice": "tmdb", "apply_all": True, "use_more_votes": False,
                                                   "manual_r": None, "manual_v": None, "apply_fallback": False}
        _asked22 = []
        app._ask_service_failure = lambda s, k, o: (_asked22.append((s, k, o)), "continue")[1]   # B22: asked once
        try:
            _boxes.clear()
            app._sync_ratings_worker(_rows20, "k", "k", None)
            wait_for(lambda: any("Ratings Sync Complete" in str(b) for b in _boxes), 10)
        finally:
            mc._tmdb_fetch_json, mc.time.sleep = _ofj20b, _osl20b
            mc._HTTP_TIMES.clear(); mc._TMDB_RATE_TIMES.clear()
            del app._ask_ratings_dialog; del app._ask_service_failure
            mc._api_pauses_clear()
        check("B22: the batch asked ONCE: OMDb daily limit, offering 'Continue with TMDb'", _asked22 == [("omdb", "daily_limit", "TMDb")], _asked22)
        _msg20 = " ".join(str(b) for b in _boxes if "Ratings Sync Complete" in str(b))
        check("B20: Ratings Sync asks OMDb once for 3 movies", _omdb_n() == 1, _omdb_n())
        check("B20: the other movies use TMDb (7.0 / 100 written)", [_rating_of(d) for d in _rows20[1:]] == [("7.0", 100), ("7.0", 100)], [_rating_of(d) for d in _rows20])
        check("B20: the final message says it once ('OMDb (IMDb data) unavailable for the rest of this run')", _msg20.count("unavailable for the rest of this run") == 1, _msg20[:400])
        check("B20: after the run nothing stays blocked (single-movie actions ask normally)", mc._service_blocked("omdb") is None)
        time.sleep(0.3); wait_for(app._refresh_idle, 20)
        _boxes.clear()

        # ── v0.19.1 B22: pause indicator, Try anyway, failure dialog ────────────   ### NEW v0.19.1 B22 ###
        section("5x. TMDb/OMDb pause in the window (v0.19.1 B22)")
        mc._api_pauses_clear(); time.sleep(0.2)
        mc.api_pause_start("omdb", "daily_limit")               # from a worker thread, like a real failure
        wait_for(lambda: "paused" in on_ui(lambda: app._sb_pause.cget("text")), 5)
        _sbp = on_ui(lambda: app._sb_pause.cget("text"))
        check("B22: status bar shows '⚠ OMDb (IMDb data) paused — daily request limit reached (retry after about HH:MM)'", _sbp.startswith("⚠ OMDb (IMDb data) paused — daily request limit reached (retry after about "), _sbp)
        _tries = []
        app._ask_try_anyway = lambda s, e: (_tries.append((s, e["kind"])), False)[1]
        check("B22: a paused service → 'Try anyway?' before the action; Cancel = not started, pause kept", on_ui(lambda: app._confirm_services(("tmdb", "omdb"))) is False and _tries == [("omdb", "daily_limit")] and mc.api_pause_get("omdb"))
        app._ask_try_anyway = lambda s, e: True
        check("B22: 'Try anyway' starts the action and ends the pause", on_ui(lambda: app._confirm_services(("omdb",))) is True and mc.api_pause_get("omdb") is None)
        del app._ask_try_anyway
        wait_for(lambda: on_ui(lambda: app._sb_pause.cget("text")) == "", 5)
        check("B22: the status-bar indicator disappears when the pause ends", on_ui(lambda: app._sb_pause.cget("text")) == "")
        _pd = on_ui(lambda: mc._PauseAskDialog(app, "omdb", {"until": "2026-10-14T23:40:00", "kind": "daily_limit", "message": mc.api_failure_message("omdb", "daily_limit")}))
        check("B22: 'Try anyway?' window shows until when + message + advice", "paused until about 23:40" in _pd.text and "Try again in a few hours or tomorrow" in _pd.text, _pd.text)
        on_ui(_pd.destroy)
        _fdl = on_ui(lambda: mc._ServiceFailureDialog(app, "omdb", "daily_limit", "TMDb"))
        _fb = {k: on_ui(lambda b=b: b.cget("text")).strip() for k, b in _fdl.buttons.items()}
        check("B22: batch failure window — [Pause this run (until about …)] [Continue with TMDb] [Cancel]", _fb["pause"].startswith("Pause this run (until about ") and _fb["continue"] == "Continue with TMDb" and _fb["cancel"] == "Cancel", _fb)
        on_ui(lambda: _fdl.buttons["cancel"].invoke())
        check("B22: its Cancel answers 'cancel'", _fdl.result == "cancel")
        _fdk = on_ui(lambda: mc._ServiceFailureDialog(app, "tmdb", "invalid_key", None))
        check("B22: no pause offered for a rejected key; 'Continue without TMDb'", "pause" not in _fdk.buttons and on_ui(lambda: _fdk.buttons["continue"].cget("text")).strip() == "Continue without TMDb")
        on_ui(_fdk.destroy)
        _ss22 = on_ui(lambda: mc._SearchSourcesResultDialog(app, [dict(_e22s)], [_r14x]))
        check("B22: Search Sources says 'TMDb did not answer — …' instead of 'No results found'", any(l.startswith("TMDb did not answer — TMDb is receiving too many requests") for l in _ss22._labels) and not any("No results found" in l for l in _ss22._labels), _ss22._labels)
        on_ui(_ss22.destroy)
        mc._api_pauses_clear()
        # a pause that must survive the restart (checked by the fresh App in section 6)
        mc.api_pause_start("omdb", "daily_limit")
        _boxes.clear()

        # ── v0.19.1 B21: "N selected" + Ctrl+A ──────────────────────────────────   ### NEW v0.19.1 B21 ###
        section("5y. selection count + Ctrl+A (v0.19.1 B21)")
        wait_for(app._refresh_idle, 15)
        on_ui(lambda: (app._set_health_filter(None), app._filter_var.set(""), app._refresh_table()))
        _k21 = kids()
        on_ui(lambda: (app.tree.selection_set(_k21[:3]), app.update()))
        check("B21: status bar shows '3 selected' for a 3-row selection", on_ui(lambda: app._sb_sel.cget("text")).strip() == "3 selected", on_ui(lambda: app._sb_sel.cget("text")))
        on_ui(lambda: (app.tree.selection_set(_k21[:1]), app.update()))
        check("B21: one selected row → no counter", on_ui(lambda: app._sb_sel.cget("text")) == "")
        on_ui(lambda: (app._filter_var.set("conflict"), app._refresh_table()))
        _vis21 = kids()
        _orig_fg = app.focus_get
        app.focus_get = lambda: app.tree
        try:
            _r21 = on_ui(app._select_all_visible)
        finally:
            app.focus_get = _orig_fg
        check("B21: Ctrl+A selects exactly the visible (filtered) rows", _r21 == "break" and set(on_ui(app.tree.selection)) == set(_vis21) and 0 < len(_vis21) < len(_k21), (len(_vis21), len(_k21)))
        check("B21: the counter follows Ctrl+A", on_ui(lambda: app._sb_sel.cget("text")).strip() == f"{len(_vis21)} selected" if len(_vis21) > 1 else True)
        on_ui(lambda: app.tree.selection_set(_vis21[:1]))
        app.focus_get = lambda: app._filter_entry
        try:
            _r21b = on_ui(app._select_all_visible)
        finally:
            app.focus_get = _orig_fg
        check("B21: with the Filter box focused Ctrl+A does not touch the table (text selection there)", _r21b is None and len(on_ui(app.tree.selection)) == 1 and bool(on_ui(lambda: app._filter_entry.bind("<Control-a>"))))
        check("B21: Ctrl+A is bound on the window and Help → Shortcuts lists it", bool(on_ui(lambda: app.bind("<Control-a>"))) and "Ctrl+A" in dict(mc._help.HELP_TABS)[[l for l, _t in mc._help.HELP_TABS if l.endswith("Shortcuts")][0]])
        on_ui(lambda: (app._filter_var.set(""), app._refresh_table()))
        _boxes.clear()

        # ── v0.19.1 B12: NFO tooltip — first 5 errors + "n more", info notes ───   ### NEW v0.19.1 B12 ###
        section("5z. NFO/XML error tooltip (v0.19.1 B12)")
        def _tip12():
            app._item_map["__b12__"] = {"nfo_exists": True, "nfo_path": "x.nfo", "nfo_size": "1 KB",
                                        "nfo_errors": [{"line": i, "col": 1, "message": f"err {i}"} for i in range(1, 8)],
                                        "nfo_infos": [{"line": 9, "col": 3, "message": "`&` not escaped (Kodi accepts it, Emby may not)"}]}
            try:
                return app._tooltip("__b12__", mc.COL_NFO)
            finally:
                app._item_map.pop("__b12__", None)
        _t12 = on_ui(_tip12) or ""
        check("B12: tooltip lists the first 5 errors, '... 2 more' and the info note", "Line 5: err 5" in _t12 and "Line 6:" not in _t12 and "... 2 more" in _t12 and "(i) Line 9: `&` not escaped" in _t12, _t12)

        # ── v0.19.1 I10: fanart.tv in the Fetch dialogs and Replace All ─────────   ### NEW v0.19.1 I10 ###
        section("5ac. fanart.tv in the Fetch dialogs (v0.19.1 I10)")
        _d10 = os.path.join(_TMP, "i10", "Fan Movie"); os.makedirs(_d10, exist_ok=True)
        for _i in range(2):
            _jpeg(os.path.join(_d10, "backdrop.jpg" if _i == 0 else f"backdrop{_i}.jpg"), 640, 360)
        _row10 = {"source_tmdb_val": "710001", "source_imdb_val": "tt7100010", "subfolder_path": _d10,
                  "movie_name": "Fan Movie", "subfolder": "Fan Movie", "poster_path": os.path.join(_d10, "poster.jpg"),
                  "fanart_path": os.path.join(_d10, "fanart.jpg"), "poster_exists": False, "fanart_exists": False}
        _fan10 = {"moviebackground": [{"url": f"https://assets.fanart.tv/fanart/movies/710001/bg{i}.jpg", "lang": "", "likes": str(i)} for i in range(4)],
                  "movieposter": [{"url": "https://assets.fanart.tv/fanart/movies/710001/p.jpg", "lang": "pt", "likes": "1"}]}
        _o10 = (mc._tmdb_rate_limited_fetch, mc.fanarttv_fetch, mc._tmdb_download_image, mc._download_preview,
                mc.SETTINGS.get("fanarttv_api_key", ""), mc.SETTINGS.get("tmdb_api_key", ""))
        _dl10 = []
        def _fake_dl10(url, dest):
            _dl10.append(url); _jpeg(dest, 1920, 1080); return True, ""
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {"backdrops": [{"file_path": "/t1.jpg", "width": 3840, "height": 2160}],
                                                               "posters": [{"file_path": "/tp.jpg", "width": 2000, "height": 3000}]}
        mc.fanarttv_fetch = lambda tmdb_id=None, imdb_id=None: (_fan10, None)
        mc._tmdb_download_image = _fake_dl10
        mc._download_preview = lambda entry: None
        mc.SETTINGS["fanarttv_api_key"] = "k"; mc.SETTINGS["tmdb_api_key"] = "k"
        mc._LAST_IMAGE_SOURCE[0] = None
        try:
            _df10 = on_ui(lambda: mc._FetchBackdropDialog(app, _row10, "k", "710001"))
            wait_for(lambda: len(_df10._images) == 5, 10)
            check("I10: Fetch Backdrops — source selector TMDb | fanart.tv | Both, default Both, both lists merged",
                  on_ui(lambda: _df10._src_var.get()) == "Both" and [e["source"] for e in _df10._images] == ["tmdb"] + ["fanarttv"] * 4,
                  (on_ui(lambda: _df10._src_var.get()), [e["source"] for e in _df10._images]))
            on_ui(lambda: _df10._on_source_change("fanarttv", False))
            wait_for(lambda: len(_df10._images) == 4, 10)
            on_ui(lambda: _df10._select_tmdb(0))
            check("I10: switch to fanart.tv → only fanart.tv backdrops, most liked first; the selection gives its full URL",
                  on_ui(_df10._get_selected_image_url) == "https://assets.fanart.tv/fanart/movies/710001/bg3.jpg")
            on_ui(_df10._download_new)
            wait_for(lambda: os.path.isfile(os.path.join(_d10, "backdrop2.jpg")) and bool(_boxes), 10); time.sleep(0.3)
            check("I10: 'Download as New File' saves the fanart.tv image with the folder's naming (backdrop2.jpg)",
                  _dl10 == ["https://assets.fanart.tv/fanart/movies/710001/bg3.jpg"] and os.path.isfile(os.path.join(_d10, "backdrop2.jpg")), (_dl10, os.listdir(_d10)))
            _boxes.clear()
            on_ui(_df10._done)
            _dp10 = on_ui(lambda: mc._FetchImageDialog(app, _row10, "poster", "k", "710001"))
            wait_for(lambda: len(_dp10._images) == 1, 10)
            check("I10: Fetch Poster/Folder opens with the session's last choice (fanart.tv) and lists its poster",
                  on_ui(lambda: _dp10._src_var.get()) == "fanart.tv" and [e["url"] for e in _dp10._images] == ["https://assets.fanart.tv/fanart/movies/710001/p.jpg"],
                  (on_ui(lambda: _dp10._src_var.get()), len(_dp10._images)))
            on_ui(_dp10._done)
            # Replace All Backdrops: the source is chosen with the counts
            _asked10 = []
            app._ask_backdrop_count = lambda movie, local_n, online_n, sources=None: (_asked10.append((local_n, online_n, sources)), "fanarttv")[1]
            _dl10.clear(); _boxes.clear()
            on_ui(lambda: app._replace_all_backdrops(_row10))
            wait_for(lambda: any("Replace All Backdrops" in str(b) for b in _boxes), 20)
            check("I10: Replace All Backdrops asks with the count of each source", _asked10 == [(3, 1, {"tmdb": 1, "fanarttv": 4})], _asked10)
            check("I10: …and downloads only the chosen source (fanart.tv: 4 backdrops)", sorted(_dl10) == sorted(f"https://assets.fanart.tv/fanart/movies/710001/bg{i}.jpg" for i in range(4))
                  and len([f for f in os.listdir(_d10) if f.startswith("backdrop")]) == 4, (_dl10, os.listdir(_d10)))
            check("I10: the final message names the source", any("(fanart.tv)" in str(b) for b in _boxes), _boxes[-1:])
            del app._ask_backdrop_count
            # the count dialog itself: radio per source, the warning follows the choice
            mc._LAST_IMAGE_SOURCE[0] = None
            _cd10 = on_ui(lambda: mc._BackdropCountDialog(app, "Fan Movie", 3, 1, sources={"tmdb": 1, "fanarttv": 4}))
            _m_both = on_ui(lambda: _cd10.message)
            on_ui(lambda: (_cd10.choice.set("tmdb"), _cd10._recount()))
            _m_tmdb, _b_tmdb = on_ui(lambda: (_cd10.message, _cd10.button_label))
            on_ui(_cd10._ok)
            check("I10: count dialog — Both counts 5; TMDb (1 < 3) asks 'Replace anyway'; OK returns the source",
                  "offers 5" in _m_both and "offers 1" in _m_tmdb and _b_tmdb == "Replace anyway" and _cd10.result == "tmdb", (_m_both, _m_tmdb, _cd10.result))
        finally:
            (mc._tmdb_rate_limited_fetch, mc.fanarttv_fetch, mc._tmdb_download_image, mc._download_preview,
             _fk10, _tk10) = _o10
            mc.SETTINGS["fanarttv_api_key"] = _fk10; mc.SETTINGS["tmdb_api_key"] = _tk10
            mc._LAST_IMAGE_SOURCE[0] = None
            if hasattr(app, "_ask_backdrop_count") and "_ask_backdrop_count" in app.__dict__:
                del app._ask_backdrop_count
        _boxes.clear()

        # ── v0.19.1 B11: frames from the movie in Fetch Fanart / Backdrops ───────   ### NEW v0.19.1 B11 ###
        section("5ad. Frames from the movie (v0.19.1 B11)")
        if SAMPLE_VIDEO:
            _d11 = os.path.join(_TMP, "b11", "Frame Movie"); os.makedirs(_d11, exist_ok=True)
            _v11 = os.path.join(_d11, "Frame Movie.mkv"); shutil.copy2(SAMPLE_VIDEO, _v11)
            _jpeg(os.path.join(_d11, "fanart.jpg"), 640, 360)
            _row11 = {"subfolder_path": _d11, "subfolder": "Frame Movie", "movie_name": "Frame Movie", "video_path": _v11,
                      "poster_path": os.path.join(_d11, "poster.jpg"), "fanart_path": os.path.join(_d11, "fanart.jpg"),
                      "poster_exists": False, "fanart_exists": True}
            _orl11 = mc._tmdb_rate_limited_fetch
            mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {"posters": [], "backdrops": []}
            _bk11 = lambda: sorted(n for n in os.listdir(os.path.join(_APP_DIR, "backup")) if "Frame" in n)
            _bk11a = _bk11()
            try:
                _dp11 = on_ui(lambda: mc._FetchImageDialog(app, _row11, "poster", "k", "711001"))
                check("B11: no Frames button in Fetch Poster/Folder", not hasattr(_dp11, "_frames_btn"))
                on_ui(_dp11._done)
                _df11 = on_ui(lambda: mc._FetchImageDialog(app, _row11, "fanart", "k", "711001"))
                check("B11: Fetch Fanart shows '🎞 Frames from movie'", "Frames from movie" in on_ui(lambda: _df11._frames_btn.cget("text")))
                on_ui(_df11._frames_btn.invoke)
                wait_for(lambda: len(_df11._images) == 10, 60)
                _root11 = _df11._frames_root
                check("B11: the frames fill the list (source 'Movie frames', button now 'More frames')",
                      [e["source"] for e in _df11._images] == ["frame"] * 10 and on_ui(lambda: _df11._src_var.get()) == "Movie frames" and "More frames" in on_ui(lambda: _df11._frames_btn.cget("text")) and mc._LAST_IMAGE_SOURCE[0] != "frames")
                _first11 = _df11._images[0]["url"]
                on_ui(_df11._frames_btn.invoke)
                wait_for(lambda: len(_df11._images) == 10 and _df11._images[0]["url"] != _first11, 60)
                check("B11: 'More frames' gives a new set", _df11._images[0]["url"] != _first11 and os.path.dirname(_df11._images[0]["url"]) != os.path.dirname(_first11))
                _boxes.clear()
                _pick11 = _df11._images[3]["url"]
                on_ui(lambda: _df11._apply_image(_pick11))
                wait_for(lambda: not on_ui(_df11.winfo_exists), 20)
                check("B11: Use This writes fanart.jpg from the frame (1280×720)", mc.get_image_wh(os.path.join(_d11, "fanart.jpg")) == (1280, 720) and _df11.applied is True, mc.get_image_wh(os.path.join(_d11, "fanart.jpg")))
                check("B11: …after a backup of the old fanart.jpg", len(_bk11()) > len(_bk11a), _bk11())
                check("B11: the temp frames are deleted when the dialog closes", _root11 and not os.path.exists(_root11), _root11)
                _db11 = on_ui(lambda: mc._FetchBackdropDialog(app, _row11, "k", "711001"))
                on_ui(_db11._frames_btn.invoke)
                wait_for(lambda: len(_db11._images) == 10, 60)
                on_ui(lambda: _db11._select_tmdb(5)); _boxes.clear()
                on_ui(_db11._download_new)
                wait_for(lambda: os.path.isfile(os.path.join(_d11, "backdrop.jpg")) and bool(_boxes), 20)
                check("B11: Fetch Backdrops — 'Download as New File' saves the selected frame as backdrop.jpg", mc.get_image_wh(os.path.join(_d11, "backdrop.jpg")) == (1280, 720))
                _root11b = _db11._frames_root
                on_ui(_db11._done)
                check("B11: …and its frames are deleted on Done", _root11b and not os.path.exists(_root11b))
                _nv11 = dict(_row11, video_path=None)
                _dn11 = on_ui(lambda: mc._FetchBackdropDialog(app, _nv11, "k", "711001"))
                check("B11: no video → no Frames button", not hasattr(_dn11, "_frames_btn"))
                on_ui(_dn11._done)

                # ── v0.19.1 B25: no TMDB ID → Fetch Fanart / Backdrops still work (frames, fanart.tv) ──
                _nt25 = dict(_row11, source_tmdb_val=None, source_imdb_val=None)
                _ok25 = mc.SETTINGS.get("tmdb_api_key", ""); _fk25 = mc.SETTINGS.get("fanarttv_api_key", "")
                mc.SETTINGS["tmdb_api_key"] = "k"; mc.SETTINGS["fanarttv_api_key"] = ""
                try:
                    check("B25: sources without TMDB ID — fanart/backdrops: frames; poster: none",
                          mc.image_sources_for(_nt25, "fanart") == ["frames"] and mc.image_sources_for(_nt25, "backdrops") == ["frames"]
                          and mc.image_sources_for(_nt25, "poster") == [])
                    mc.SETTINGS["fanarttv_api_key"] = "f"
                    check("B25: with a fanart.tv key and an IMDb ID the poster can come from fanart.tv",
                          mc.image_sources_for(dict(_nt25, source_imdb_val="tt0000001"), "poster") == ["fanarttv"]
                          and mc.image_sources_for(dict(_nt25, source_imdb_val="tt0000001"), "fanart") == ["fanarttv", "frames"])
                    mc.SETTINGS["fanarttv_api_key"] = ""
                    # right-click menu on a movie without TMDB ID (row data swapped in, menu not shown)
                    _iid25 = on_ui(lambda: app.tree.get_children()[0])
                    _orig25 = app._item_map[_iid25]
                    app._item_map[_iid25] = dict(_orig25, source_tmdb_val=None, source_imdb_val=None,
                                                 video_path=_v11, subfolder_path=_d11)
                    def _menu25():
                        app.tree.selection_set(_iid25); app.tree.see(_iid25); app.update()
                        _bb = app.tree.bbox(_iid25)
                        app._ctx.tk_popup = lambda x, y: None
                        try:
                            app._rclick(type("E", (), {"y": _bb[1] + 2, "x_root": 0, "y_root": 0})())
                        finally:
                            del app._ctx.tk_popup
                        out = {}
                        for i in range(app._ctx.index("end") + 1):
                            try:
                                out[app._ctx.entrycget(i, "label")] = str(app._ctx.entrycget(i, "state"))
                            except Exception:
                                pass
                        return out
                    try:
                        _m25 = on_ui(_menu25)
                    finally:
                        app._item_map[_iid25] = _orig25
                    _st25 = lambda pre: next((s for l, s in _m25.items() if l.startswith(pre)), None)
                    check("B25: menu — Fetch Fanart and Fetch Backdrops enabled without TMDB ID (frames)",
                          _st25("🎨  Fetch Fanart") == "normal" and _st25("🖼  Fetch Backdrops") == "normal", _m25)
                    check("B25: menu — Fetch Poster/Folder greyed with the reason; Replace All Backdrops still greyed",
                          _st25("🖼  Fetch Poster/Folder") == "disabled" and "fanart.tv" in next(l for l in _m25 if l.startswith("🖼  Fetch Poster/Folder"))
                          and _st25("🔄  Replace All Backdrops") == "disabled", _m25)
                    # the launcher opens the dialog directly on the movie's frames
                    on_ui(lambda: app.after(0, lambda: app._fetch_fanart([_nt25])))
                    wait_for(lambda: on_ui(lambda: any(isinstance(w, mc._FetchImageDialog) for w in app.winfo_children())), 10)
                    _dg25 = on_ui(lambda: next(w for w in app.winfo_children() if isinstance(w, mc._FetchImageDialog)))
                    wait_for(lambda: len(_dg25._images) == 10, 60)
                    check("B25: Fetch Fanart without TMDB ID opens on 'Movie frames' and lists 10 frames",
                          _dg25._source == "frames" and on_ui(lambda: _dg25._src_var.get()) == "Movie frames"
                          and [e["source"] for e in _dg25._images] == ["frame"] * 10 and "More frames" in on_ui(lambda: _dg25._frames_btn.cget("text")))
                    on_ui(_dg25._done)
                finally:
                    mc.SETTINGS["tmdb_api_key"] = _ok25; mc.SETTINGS["fanarttv_api_key"] = _fk25
            finally:
                mc._tmdb_rate_limited_fetch = _orl11
            _boxes.clear()

        # ── v0.19.1 I5: Full Scan with FFprobe twice — the second probes nothing ──   ### NEW v0.19.1 I5 ###
        section("5ab. FFprobe cache in a real Full Scan (v0.19.1 I5)")
        if SAMPLE_VIDEO:
            wait_for(app._refresh_idle, 15)
            on_ui(lambda: app._start_scan(app._scope_roots(), use_ff=True)); wait_for(lambda: not app._scanning, 240)
            mc._FFPROBE_STATS.update(runs=0, hits=0)
            on_ui(lambda: app._start_scan(app._scope_roots(), use_ff=True)); wait_for(lambda: not app._scanning, 240)
            _by5 = {r["subfolder"]: r for r in app._results}
            check("I5: a second Full Scan with FFprobe of the unchanged library runs 0 ffprobe processes", mc._FFPROBE_STATS["runs"] == 0 and mc._FFPROBE_STATS["hits"] > 0, mc._FFPROBE_STATS)
            check("I5: …and the rows still carry the FFprobe data", _by5["Perfect Movie"]["audio_tracks"] and _by5["Perfect Movie"]["video_quality"] == "720p" and _by5["Perfect Movie"]["ffprobe_ran"])
            wait_for(app._refresh_idle, 15)

        # ── v0.19.1 I1: Backup History → Restore a real batch ───────────────────   ### NEW v0.19.1 I1 ###
        section("5aa. Backup History / Undo (v0.19.1 I1)")
        wait_for(app._refresh_idle, 15)
        _rows_i1 = [{r["subfolder"]: r for r in app._results}[n] for n in ("Hardsub Movie", "Hardsub Movie Two")]
        _before_i1 = {d["nfo_path"]: io.open(d["nfo_path"], encoding="utf-8").read() for d in _rows_i1}
        app._hardsubs_worker(list(_rows_i1), ["ITA"], None)          # a real batch (worker thread = this thread)
        time.sleep(0.3); wait_for(app._refresh_idle, 20)
        check("I1: the batch changed the files", all("Hardsub ITA" in io.open(p, encoding="utf-8").read() for p in _before_i1))
        _bh = on_ui(lambda: mc.BackupHistoryDialog(app))
        on_ui(lambda: _bh.load(sync=True))
        _top = on_ui(lambda: _bh._runs[0])
        check("I1: Backup History shows the batch first: action 'Hard-coded subtitles', 2 movies, 4 files, ready", _top["action"] == "Hard-coded subtitles" and _top["movies"] == 2 and len(_top["files"]) == 4 and not _top["changed"], (_top["action"], _top["movies"], len(_top["files"]), _top["changed"]))
        _boxes.clear()
        on_ui(lambda: (_bh._tree.selection_set("0"), _bh._show_files(), _bh._restore(sync=True)))
        time.sleep(0.3); wait_for(app._refresh_idle, 20)
        check("I1: 'Restore this run' puts the files back exactly", all(io.open(p, encoding="utf-8").read() == c for p, c in _before_i1.items()))
        _rr_i1 = {r["subfolder"]: r for r in app._results}
        check("I1: the rows are refreshed after the restore (Hardsub SPA again, no ITA)", _rr_i1["Hardsub Movie"]["subs_hard"] == ["SPA"], _rr_i1["Hardsub Movie"].get("subs_hard"))
        check("I1: the restore message names the safety backup", any("file(s) restored" in str(b) and "before the undo" in str(b) for b in _boxes), _boxes)
        time.sleep(1.0); on_ui(lambda: None)        # the dialog reloads in the background after a restore — let it finish
        os.makedirs(os.path.join(_APP_DIR, "backup", "backup_Legacy_Test_2020-01-01_00-00-00"), exist_ok=True)
        on_ui(lambda: _bh.load(sync=True))
        _li = on_ui(lambda: next(i for i, r in enumerate(_bh._runs) if r["name"] == "backup_Legacy_Test_2020-01-01_00-00-00"))
        on_ui(lambda: (_bh._tree.selection_set(str(_li)), _bh._show_files()))
        check("I1: a legacy backup shows 'legacy (manual restore only)' and Restore is disabled", on_ui(lambda: _bh._tree.set(str(_li), "state")) == "legacy (manual restore only)" and on_ui(lambda: str(_bh._restore_btn.cget("state"))) == "disabled")
        on_ui(_bh.destroy)
        shutil.rmtree(os.path.join(_APP_DIR, "backup", "backup_Legacy_Test_2020-01-01_00-00-00"), ignore_errors=True)
        _boxes.clear()

        # Settings dialog
        sd = on_ui(lambda: mc.SettingsDialog(app, tab=10))    # ### MODIFIED v0.19.1 I9 ### — Tk steps below via on_ui
        time.sleep(0.3)
        check("settings dialog: 12 tabs", len(on_ui(sd._nb.tabs)) == 12, len(on_ui(sd._nb.tabs)))
        check("v0.19 SettingsDialog restored via hook", _near(_geom(sd), (900, 700, 90, 60)), _geom(sd))
        on_ui(app.withdraw)
        check("settings dialog: parallel workers + duplicate rule vars", hasattr(sd, "_scan_workers_var") and "duplicate_movie" in sd._hr_vars)
        check("settings dialog: new partial rules present", "imdb_id_partial" in sd._hr_vars and "tmdb_id_partial" in sd._hr_vars)
        check("I5: Tools tab has the 'Remember FFprobe results' checkbox (ON)", hasattr(sd, "_ffprobe_cache_var") and on_ui(sd._ffprobe_cache_var.get) is True)
        check("B24: Health Rules tab has the single-source / no-source severity combos", on_ui(lambda: (sd._hr_str_vars["single_source_level"].get(), sd._hr_str_vars["no_source_level"].get())) == ("error", "error"))
        reg = {lbl: idx for idx, lbl, _ in mc.SettingsDialog._TAB_REGISTRY}
        check("settings menu maps every entry to an existing tab", all(t in reg for _, _, t in mc._SETTINGS_MENU_ITEMS) and reg["Health Rules"] == 10 and reg["Ratings"] == 6)
        check("I10: Settings menu says 'API Keys (fetchers)' and opens the API Keys tab (index 1)", [t for _, l, t in mc._SETTINGS_MENU_ITEMS if l == "API Keys (fetchers)"] == ["API Keys"] and reg["API Keys"] == 1 and not any("TMDb / OMDb" in l for _, l, _t in mc._SETTINGS_MENU_ITEMS))
        check("I10: API Keys tab has the fanart.tv block", all(hasattr(sd, a) for a in ("_fanarttv_var", "_fanarttv_client_var", "_fanarttv_link")))
        _ch_ = on_ui(sd._rescan_changed)
        check("snapshot unchanged → no rescan", _ch_["any"] is False, _ch_)
        # Save & Apply / Cancel bar must be visible on EVERY tab (v0.18.4 regression fix)
        def _bar_check():
            sd.deiconify(); sd.update()
            bar = [w for w in sd.winfo_children() if isinstance(w, tk.Frame) and w.winfo_children()
                   and any(isinstance(c, tk.Frame) for c in w.winfo_children())][0]
            hidden = []
            for t in sd._nb.tabs():
                sd._nb.select(t); sd.update()
                if not (bar.winfo_ismapped() and bar.winfo_y() + bar.winfo_height() <= sd.winfo_height()):
                    hidden.append(sd._nb.tab(t, "text"))
            return hidden
        hidden_on = on_ui(_bar_check)
        check("Save & Apply bar visible on all 12 tabs", not hidden_on, hidden_on)
        # blank numeric fields must not break change detection or save
        on_ui(lambda: (sd._max_nfo_kb_var.set(""), sd._hr_int_vars["backdrop_min_count"].set("")))
        try:
            ch0 = on_ui(sd._rescan_changed); blank_ok = True
        except Exception as ex:
            ch0 = {}; blank_ok = False; print("   rescan_changed raised:", ex)
        check("blank spinboxes tolerated by change detection", blank_ok and ch0.get("health_rules") is False and ch0.get("any") is False, ch0)
        on_ui(lambda: sd._hr_vars["imdb_id_partial"].set(False))
        ch = on_ui(sd._rescan_changed)
        check("health rule change detected", ch["health_rules"] is True and ch["image_sizes"] is False)
        # v0.19.0 — Image Sizes combo and Health Rules combo are one setting
        on_ui(lambda: sd._fanart_ql_var.set("720p"))
        check("v0.19 image-sizes combo mirrors the health-rule combo", on_ui(sd._hr_str_vars["fanart_quality_level_minimum"].get) == "720p")
        on_ui(lambda: sd._hr_str_vars["poster_folder_quality_level"].set("540p"))
        check("v0.19 health-rule combo mirrors poster AND folder combos", on_ui(lambda: (sd._poster_ql_var.get(), sd._folder_ql_var.get())) == ("540p", "540p"))
        on_ui(lambda: sd._hr_str_vars["poster_folder_quality_level"].set("1080p"))
        applied = {"n": 0}
        _orig_apply = app._apply_health_rules_inplace
        def _spy():
            applied["n"] += 1; _orig_apply()
        app._apply_health_rules_inplace = _spy
        on_ui(sd._save_close)
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

        def _help_info():
            hd = mc.HelpDialog(app, tab=7)
            nb = [w for w in hd.winfo_children() if isinstance(w, tk.ttk.Notebook)]
            info = (bool(nb), len(nb[0].tabs()) if nb else 0,
                    [nb[0].tab(x, "text") for x in nb[0].tabs()] if nb else [],
                    nb[0].tab(nb[0].select(), "text") if nb else "")
            hd.destroy()
            return info
        _has_nb, _n_tabs, _tab_labels, _sel_label = on_ui(_help_info)
        check("help dialog: 9 tabs (8 topics + About)", _has_nb and _n_tabs == 9)
        # v0.19.1 B9/B10
        check("B9: no Version History tab; About last", "Version History" not in " ".join(_tab_labels) and _tab_labels[-1] == mc._help.ABOUT_LABEL, _tab_labels)
        check("B9: tab 7 selected = Shortcuts", _sel_label.endswith("Shortcuts"), _sel_label)
        _menu_labels = on_ui(lambda: [app._help_menu.entrycget(i, "label") for i in range(app._help_menu.index("end") + 1)
                                      if app._help_menu.type(i) == "command"])
        check("B9: Help menu = the Help tabs in the same order, About last", [m.replace("   (F1)", "") for m in _menu_labels] == _tab_labels, (_menu_labels, _tab_labels))
        check("B9: no 'Version History' anywhere in Help", not any("Version History" in tx for _l, tx in mc._help.HELP_TABS) and not hasattr(mc._help, "TAB_VERSION"))
        _lint = []
        import re as _re10
        for _l, _tx in mc._help.HELP_TABS:
            for _ln in _tx.splitlines():
                _ind = len(_ln) - len(_ln.lstrip(" "))
                if len(_ln) > 72 or "\t" in _ln or _ln != _ln.rstrip() or (_ln.strip() and _ind in (1, 3)) \
                   or (_ln.lstrip().startswith("•") and not _re10.match(r"^  •  \S", _ln)):
                    _lint.append((_l, _ln))
        check("B10: help texts follow one layout (≤72 chars, 2-space body, aligned bullets)", not _lint, _lint[:3])
        check("B10: help mentions the v0.19 features", all(k in " ".join(tx for _l, tx in mc._help.HELP_TABS) for k in ("Libraries…", "Auto Repair", "Verify", "Remove from list", "Enter ID…", "Shift+PageUp")))

        mc.SETTINGS["compact_mode"] = True; on_ui(app._on_settings_changed); time.sleep(0.5)
        _rh = on_ui(lambda: str(tk.ttk.Style(app).lookup("Treeview", "rowheight")))
        check("compact mode applied to Treeview style", _rh == "20", _rh)

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
# v0.19.1 B22: a restart reads api_pauses from settings.json
_disk22 = (json.load(open(sc.CONFIG_PATH, encoding="utf-8")).get("api_pauses") or {})
mc._API_PAUSES.clear(); mc.SETTINGS["api_pauses"] = _disk22
app2 = mc.App(); app2.withdraw()
_UI_APP.append(app2)                                              ### NEW v0.19.1 I9 ###
def ui_tests2():
    try:
        wait_for(lambda: bool(app2._results), 10)
        check("fresh App restores results from last_results.json", len(app2._results) == shared.get("rows", -1), len(app2._results))
        check("restored rows get new default keys", all("nfo_title" in r and "scan_mtime" in r for r in app2._results))
        on_ui(lambda: (app2.deiconify(), app2.update())); time.sleep(0.3)
        _g2 = on_ui(lambda: (app2.geometry(), app2.withdraw())[0])
        check("v0.19 fresh App restores its saved geometry", _g2.startswith("1250x650"), _g2)
        check("B22: the pause saved in settings.json survives the restart (status bar)", "omdb" in _disk22 and wait_for(lambda: on_ui(lambda: app2._sb_pause.cget("text")).startswith("⚠ OMDb (IMDb data) paused"), 5), (_disk22, on_ui(lambda: app2._sb_pause.cget("text"))))
        mc._api_pauses_clear()
    except Exception:
        check("UI test 2 crashed", False, traceback.format_exc())
    finally:
        app2.after(0, app2.destroy)
threading.Thread(target=ui_tests2, daemon=True).start()
app2.mainloop()

# ══════════════════════════════════════════════════════════════════════════════
# ### NEW v0.19.1 I9 ### — startup timing with a synthetic 10,000-row cache.
# Measures _restore_last_session (load last_results.json → _results_from_json →
# finalize_results → table) on the Tk thread.  The number decides whether I4
# (faster startup) is needed in v0.19.2: > about 2 s → do I4.
section("7. startup timing — 10,000-row cache (v0.19.1 I9)")
STARTUP_10K_SECONDS = None
_base_rows = sc.load_results_cache()
_big = []
for _i in range(10000):
    _r = dict(_base_rows[_i % len(_base_rows)])
    _r["subfolder"] = f"{_r['subfolder']} #{_i:05d}"
    _r["subfolder_path"] = os.path.join(LIB, _r["subfolder"])
    _r["movie_name"] = f"{_r.get('movie_name') or _r['subfolder']} #{_i:05d}"
    _r["source_imdb_val"] = f"tt6{_i:06d}"; _r["source_tmdb_val"] = str(600000 + _i)
    _big.append(_r)
_big_path = os.path.join(_TMP, "last_results_10k.json")
with open(_big_path, "w", encoding="utf-8") as f:
    json.dump(_big, f)
_orig_cache_path = sc.RESULTS_CACHE_PATH
sc.RESULTS_CACHE_PATH = _big_path
try:
    app3 = mc.App(); app3.withdraw()
    _UI_APP.append(app3)
    _t3 = {}
    def ui_tests3():
        try:
            wait_for(lambda: len(app3._results) == 10000, 120)     # the automatic restore (after 200 ms) runs first
            def _timed():
                app3._results = []; app3._item_map.clear()
                t0 = time.perf_counter()
                app3._restore_last_session()
                app3.update_idletasks()
                return time.perf_counter() - t0
            _t3["s"] = on_ui(_timed, timeout=300)
            _t3["rows"] = len(app3._results); _t3["shown"] = len(kids(app3))
        except Exception:
            check("UI test 3 crashed", False, traceback.format_exc())
        finally:
            app3.after(0, app3.destroy)      # destroy, not _on_app_close: the 10k rows are never saved
    threading.Thread(target=ui_tests3, daemon=True).start()
    app3.mainloop()
finally:
    sc.RESULTS_CACHE_PATH = _orig_cache_path
STARTUP_10K_SECONDS = _t3.get("s")
print(f"   STARTUP_10K_SECONDS = {STARTUP_10K_SECONDS if STARTUP_10K_SECONDS is None else round(STARTUP_10K_SECONDS, 2)}"
      f"  (rows {_t3.get('rows')}, table {_t3.get('shown')})  →  I4 {'NEEDED' if (STARTUP_10K_SECONDS or 0) > 2 else 'not needed'} (threshold ≈ 2 s)")
check("I9: 10,000-row cache restored into results and table", _t3.get("rows") == 10000 and _t3.get("shown") == 10000, _t3)
check("I9: startup timing measured", isinstance(STARTUP_10K_SECONDS, float) and STARTUP_10K_SECONDS > 0, STARTUP_10K_SECONDS)

for fn, orig in zip(("showinfo", "showwarning", "showerror", "askyesno"), _orig_boxes):
    setattr(mc.messagebox, fn, orig)

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f_ in FAIL: print("   FAILED:", f_)
try: shutil.rmtree(_TMP, ignore_errors=True)
except Exception: pass
sys.exit(1 if FAIL else 0)
