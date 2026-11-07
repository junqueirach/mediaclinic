# =============================================================================
# selftest_v0_19_5.py
# Metadata & MediaClinic — v0.19.4 self-test
# Author:  Luiz Junqueira & Claude AI
#
# Builds a synthetic movie library in a temp folder (NFO/XML/JPEG/MKV files
# generated on the fly), then exercises scanning, health rules, Quick Scan,
# FFprobe-flag handling, the export module, the results cache, the settings
# dialog and the main window — all against an ISOLATED config directory so
# your real settings.json is never touched.
#
# RUN (from the v.0.19.5 folder):
#   python selftest_v0_19_5.py
# Exit code 0 = all tests passed.  A real FFmpeg install is used when found
# (video/audio tests are skipped otherwise).  The main window stays hidden;
# a few dialogs may flash briefly.
# =============================================================================

import os, sys, io, csv, json, time, shutil, tempfile, threading, traceback
import faulthandler as _fh_ci, os as _os_ci, sys as _sys_ci
if _os_ci.environ.get("CI"):                     # a hang on CI: all thread stacks in the log, the run ends
    _fh_ci.dump_traceback_later(1500, exit=True, file=_sys_ci.stderr)
import re
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
    if any(os.path.isfile(os.path.join(_cand, n)) for n in ("mediaclinic.py", "mediaclinic_v0_19_5.py")):
        _APP_DIR = _cand; break
os.chdir(_APP_DIR)
sys.path.insert(0, _APP_DIR)

_TMP = tempfile.mkdtemp(prefix="mediaclinic_selftest_")
os.environ["MEDIACLINIC_CONFIG_DIR"] = os.path.join(_TMP, "config")
# ### NEW v0.19.2 B31 ### test backups go to the temp folder, never into the
# program's own backup\ folder (which is listed now and compared at the end).
_BK = os.path.join(_TMP, "backup")
os.environ["MEDIACLINIC_BACKUP_DIR"] = _BK
os.makedirs(_BK, exist_ok=True)
_PROG_BK = os.path.join(_APP_DIR, "back" + "up")   # the program's real folder (spelled so a bulk rename never hits it)
def _tree31(root):
    out = {}
    for dp, _dn, fn in os.walk(root):
        for n in fn:
            p = os.path.join(dp, n)
            try:
                st = os.stat(p); out[os.path.relpath(p, root)] = (st.st_size, st.st_mtime_ns)
            except OSError:
                pass
    return out
_PROG_BK_BEFORE = (os.path.isdir(_PROG_BK), _tree31(_PROG_BK))

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
    import mediaclinic_v0_19_5 as mc             # local versioned copy
import export_list
import settings_controller as sc
mc.IGNORED_REPORT_AUTO = False      # ### NEW v0.19.2 B53 ### the Ignored folders window opens only where a test asks
from settings_model import DEFAULT_SETTINGS
import tkinter as tk
import tkinter.font
import tkinter.filedialog as fd
import logging as _logging27

# ### NEW v0.19.2 B27 ### — every "Unhandled exception" the app logs during the
# whole run is counted here (independent of app.log rotation); the final check
# allows only the ones the B27 tests provoke on purpose.
class _UnhandledCounter(_logging27.Handler):
    def __init__(self):
        super().__init__(); self.records = []
    def emit(self, rec):
        if rec.getMessage().startswith("Unhandled exception"):
            self.records.append(rec)
_UNH = _UnhandledCounter()
mc.logger.addHandler(_UNH)
_UNH_PROVOKED = []

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
M_NOG1    = make_movie("No Genres TMDB", nfo_genres=(), xml_genres=(), nfo_tmdb="88801", xml_tmdb="88801", nfo_imdb="tt8880001", xml_imdb="tt8880001")
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
check("APP_VERSION", mc.APP_VERSION == "0.19.5")
# ### NEW v0.19.2 B35 ### the seeded settings.json has no migration marker → the one-time switch-off ran at import
check("B35: migration at start: both folder rules OFF, marker saved; no notice (this seed never stored them ON)",
      mc.SETTINGS["health_rules"]["missing_folder"] is False and mc.SETTINGS["health_rules"]["poster_folder_identical"] is False
      and "b35_folder_rules_off" in _cfg.get("settings_migrations", []) and sc.SETTINGS_MIGRATION_NOTICES == [],
      (_cfg.get("settings_migrations"), sc.SETTINGS_MIGRATION_NOTICES))

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
check("IMDb conflict → error with both ids", any("IMDb ID conflict" in x and "tt0000009" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_EMPTY)
check("both TMDB tags empty → ○ 'Missing TMDB ID (empty tags ready to fill)' (v0.19.1 B13)", r["source_tmdb_status"] == mc.STATUS_MISSING and r["source_tmdb_empty"] is True and "Missing TMDB ID (empty tags ready to fill)" in r["health_errors"], (r["source_tmdb_status"], r["health_reasons"]))
check("empty tags never reported as conflict", not any("conflict" in x.lower() and "TMDB" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_HALFEMP)
check("NFO has TMDB, XML tag empty → 'empty in others' (not conflict)", any("TMDB ID present in some tags but empty in others" in x for x in r["health_reasons"]) and not any("conflict" in x and "TMDB" in x for x in r["health_reasons"]), r["health_reasons"])
r = scan(M_PARTIAL)
check("TMDB only in NFO → partial warning", any("TMDB ID present in one file only" in x for x in r["health_reasons"]), r["health_reasons"])
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
check("duplicates report lists the group", "Same IMDb ID" in mc.format_duplicates_report(rows_d) and "Perfect Movie (copy)" in mc.format_duplicates_report(rows_d))
stats = mc.format_library_statistics(rows_d)
check("library statistics report renders", "HEALTH" in stats and "GENRES" in stats and "DECADES" in stats and "2000s" in stats, stats[:300])
# stale cached reasons (v0.18.2 style) are replaced on finalize
stale = dict(rows_d[2]); stale["health_reasons"] = ["Title mismatch between NFO and XML"]; stale["health_status"] = "warning"
stale.pop("health_errors", None); stale.pop("health_warnings", None)
mc.finalize_results([stale])
check("stale cached reason replaced by recompute", not any("Title mismatch" in x for x in stale["health_reasons"]), stale["health_reasons"])
lst = mc._FolderListing(M_OK)
check("folder listing: files found, newest mtime, case-insensitive", lst.has("POSTER.JPG") and lst.size("poster.jpg") > 0 and lst.newest_mtime() > 0 and lst.path_of("poster.jpg").endswith("poster.jpg"))
check("reason key collapses specifics", mc._reason_key("IMDb ID conflict between tags (tt1, tt2)") == "IMDb ID conflict between tags" and mc._reason_key("Title mismatch: NFO 'x' vs 'y'") == "Title mismatch")

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
section("2c. verify IMDb/TMDB IDs (v0.19.0)")
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
check("verify: IMDb → 123571 but TMDB 603 → different films", v["result"] == mc.ID_DIFFERENT and "603" in v["detail"] and "123571" in v["detail"], v)
v = _verify(M_V_404)
check("verify: unknown ids → ID does not exist (both named)", v["result"] == mc.ID_NOT_FOUND and "TMDB 404" in v["detail"] and "IMDb tt9999999" in v["detail"], v)
v = _verify(M_V_DIS)
check("verify: NFO and XML disagree (no network call needed)", v["result"] == mc.ID_DISAGREE and "603" in v["detail"], v)
_n0 = len(_fetch_log); _verify(M_V_DIS)
check("verify: disagree short-circuits before any request", len(_fetch_log) == _n0)
v = mc.verify_movie_ids({"subfolder": "Nothing (2001)", "subfolder_path": "X:/n", "nfo_exists": False, "xml_exists": False}, "k", "pt-BR", fetch=_fake_tmdb)
check("verify: no ids → no IDs", v["result"] == mc.ID_NONE)
v = _verify(M_V_YEAR)
check("verify: year 2002 vs TMDB 2003 accepted (±1), original title matched", v["result"] == mc.ID_OK, v)
v = _verify(M_V_YEAR, movie_year_raw="2000", movie_year="2000")
check("verify: year 2000 vs 2003 → another film", v["result"] == mc.ID_OTHER and "year 2000 vs TMDB 2003" in v["detail"], v)
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
    _raised = "No internet connection, or TMDB cannot be reached" in mc._tmdb_error_message(ex)   # B22 text
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
check("plan: missing TMDB → ids_search", _codes(M_AR_IDS) == ["ids_search"], _codes(M_AR_IDS))
check("plan: conflicting IMDb → ids_resolve (no partial)", _codes(M_AR_CONF) == ["ids_resolve"], _codes(M_AR_CONF))
check("plan: ID in one file only → ids_partial", "ids_partial" in _codes(M_PARTIAL), _codes(M_PARTIAL))
check("plan: rating/votes conflict → ratings", _codes(M_AR_RAT) == ["ratings"], _codes(M_AR_RAT))
check("plan: non-standard genres → genres", _codes(M_AR_GEN) == ["genres"], _codes(M_AR_GEN))
check("plan: bare movie → genres from TMDB, year from TMDB (B121: no language step)", _codes(M_AR_BARE) == ["genres_tmdb", "year_tmdb"], _codes(M_AR_BARE))
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
    check("migration: Library column hidden on the first v0.19 run", _m["hidden_columns"] == ["year", "library", "collection"], _m["hidden_columns"])   # + B110a (intended)
    json.dump({"last_folder": r"D:\Movies", "library_folders": [r"D:\Movies", r"E:\More"], "hidden_columns": []}, open(_cfg_tmp, "w", encoding="utf-8"))
    _m = sc.load_settings()
    check("migration runs only once (existing library_folders untouched)", _m["library_folders"] == [r"D:\Movies", r"E:\More"] and _m["hidden_columns"] == ["collection"], (_m["library_folders"], _m["hidden_columns"]))   # B110a hides its new column once (intended)
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
    check("I2: TMDB rating network failure recorded", mc._fetch_tmdb_rating("1", "k") == (None, None) and mc._take_fetch_errors())
    _seq[:] = [_http_err(404)]
    check("I2: TMDB rating 404 is 'no rating', not an error", mc._fetch_tmdb_rating("1", "k") == (None, None) and not mc._take_fetch_errors())
finally:
    mc._tmdb_fetch_json, mc.time.sleep = _orig_fj, _orig_sl
    mc._api_pauses_clear()                      # v0.19.1 B22: the 500/timeout fakes above started pauses
    mc._HTTP_TIMES.clear(); mc._TMDB_RATE_TIMES.clear()
check("I2: OMDb error messages (B22 texts)", "the free daily limit of 1,000 requests is used up" in mc._api_error_message(_http_err(401, body=b'{"Error":"Request limit reached!"}'), "OMDb") and "rejected the API key" in mc._api_error_message(_http_err(401, body=b'{"Error":"Invalid API key!"}'), "OMDb"))
check("I2: redaction helper", mc._redact("https://x/?api_key=ABC&apikey=DEF&q=1") == "https://x/?api_key=***&apikey=***&q=1")
check("I2: TMDB error message never contains the key", "SECRETKEY123" not in mc._tmdb_error_message(_ue2.URLError("boom https://api.themoviedb.org/3/x?api_key=SECRETKEY123")))
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
    if sys.platform == "win32": check("B3: migrated last_folder uses backslashes", sc.load_settings()["library_folders"] == ["z:\\film_kids"], sc.load_settings()["library_folders"])
    json.dump({"library_folders": ["z:/film_kids", "Y:/a/b"], "library_filter": "Y:/a/b",
               "settings_migrations": ["b35_folder_rules_off", "b55_library_filter_reset"]},   # v0.19.2 B55: no one-time reset here
              open(_cfg_tmp3, "w", encoding="utf-8"))
    _m3 = sc.load_settings()
    if sys.platform == "win32": check("B3: stored forward slashes normalised on load", _m3["library_folders"] == ["z:\\film_kids", "Y:\\a\\b"] and _m3["library_filter"] == "Y:\\a\\b", (_m3["library_folders"], _m3["library_filter"]))
finally:
    sc.CONFIG_PATH = _orig_cfg3
if sys.platform == "win32": check("B3: cached rows get a normalised library_root", mc._results_from_json([{"subfolder": "x", "subfolder_path": "z:/film_kids/x", "library_root": "z:/film_kids"}])[0]["library_root"] == "z:\\film_kids")

# ── v0.19.1 B8: typed IDs ────────────────────────────────────────────────────
section("2i. typed IMDb/TMDB IDs (v0.19.1 B8)")
def _f8(url, timeout=15):
    if "/find/tt0133093" in url: return {"movie_results": [{"id": 603}]}
    if "/find/tt0000000" in url: return {"movie_results": []}
    if "/movie/603?" in url: return {"id": 603, "title": "The Matrix", "original_title": "The Matrix", "release_date": "1999-03-30", "external_ids": {"imdb_id": "tt0133093"}, "poster_path": "/p.jpg"}
    if "/movie/999999?" in url: raise _ue.HTTPError(url, 404, "nf", {}, io.BytesIO(b"{}"))
    raise AssertionError(url)
_c, _m = mc.lookup_typed_ids("tt0133093", "", "k", fetch=_f8)
check("B8: IMDb ID → TMDB film found (both IDs)", _c and _c["tmdb_id"] == "603" and _c["imdb_id"] == "tt0133093" and _c["year"] == "1999", (_c, _m))
_c, _m = mc.lookup_typed_ids("", "603", "k", fetch=_f8)
check("B8: TMDB ID → IMDb filled from external_ids", _c and _c["imdb_id"] == "tt0133093", _c)
check("B8: IMDb + TMDB of different films rejected", mc.lookup_typed_ids("tt0133094", "603", "k", fetch=_f8)[0] is None and "different films" in mc.lookup_typed_ids("tt0133094", "603", "k", fetch=_f8)[1])
check("B8: invalid formats rejected without a request", mc.lookup_typed_ids("tt12", "", "k", fetch=_f8)[0] is None and "not an IMDb ID" in mc.lookup_typed_ids("tt12", "", "k", fetch=_f8)[1] and "digits only" in mc.lookup_typed_ids("", "60a3", "k", fetch=_f8)[1])
check("B8: unknown IDs → clear message (B14: an IMDb ID unknown to TMDB is 'IMDb only')", "does not exist" in mc.lookup_typed_ids("", "999999", "k", fetch=_f8)[1] and mc.lookup_typed_ids("tt0000000", "", "k", fetch=_f8)[1] == "Not on TMDB — IMDb only")
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
check("B13: all-empty TMDB tags → ○ missing (not ✕), IMDb ⬤", _s["tmdb_status"] == mc.STATUS_MISSING and _s["tmdb_empty_tags"] is True and _s["imdb_status"] == mc.STATUS_OK, _s)
# 2) TMDb-only apply → empty IMDb tags (incl. the bare <id>)
_n, _x = _b13_files("Tmdb Only", "", "")
ok, err = mc._write_both_source_ids(_n, _x, None, "4711")
_nt, _xt = _txt(_n), _txt(_x)
check("B13: TMDB-only write → empty <imdbid>, <id moviedb=\"imdb\">, <id> and XML IMDb tags", ok and all(t in _nt for t in ("<imdbid></imdbid>", '<id moviedb="imdb"></id>', "<id></id>")) and all(f"<{t}></{t}>" in _xt for t in ("IMDB", "IMDbId", "IMDB_ID")) and _valid(_n, _x), (_nt, _xt))
# 3) filling the placeholders later: no duplicate tags, values everywhere
ok, err = mc._write_both_source_ids(_n, _x, "tt7777002", "4711")
_nt, _xt = _txt(_n), _txt(_x)
_s = mc.extract_source_ids_from_files(_n, _x)
check("B13: a later write fills the placeholders (no duplicate tags)", ok and _nt.count("<imdbid>") == 1 and _nt.count('moviedb="imdb"') == 1 and _xt.count("<IMDB>") == 1 and _s["imdb_status"] == mc.STATUS_OK and _s["tmdb_status"] == mc.STATUS_OK and "<id>tt7777002</id>" in _nt, (_s, _nt))
# 4) an existing non-empty value is never blanked; a value in one file = partial (no placeholders)
_n, _x = _b13_files("Tmdb In Xml", "", "\t<TMDB>603</TMDB>\n")
ok, err = mc._write_both_source_ids(_n, _x, "tt7777003", None)
_nt, _xt = _txt(_n), _txt(_x)
check("B13: existing TMDB value kept; no empty TMDB tags added when a value exists elsewhere", ok and "<TMDB>603</TMDB>" in _xt and "<tmdbid>" not in _nt and "<TMDbId>" not in _xt and mc.extract_source_ids_from_files(_n, _x)["tmdb_status"] == mc.STATUS_WARN, (_nt, _xt))
# 5) the user's case: XML already has empty TMDb tags, NFO has none → NFO gets them, XML not duplicated
_n, _x = _b13_files("Padre Pio Like", "\t<id>tt12817760</id>\n\t<imdbid>tt12817760</imdbid>\n",
                    "\t<IMDB>tt12817760</IMDB>\n\t<TMDbId></TMDbId>\n\t<TMDB></TMDB>\n\t<TMDB_ID></TMDB_ID>\n")
ok, err = mc._write_both_source_ids(_n, _x, "tt12817760", None)
_nt, _xt = _txt(_n), _txt(_x)
check("B13: empty XML TMDB tags kept once; NFO gets the empty TMDB tags", ok and _xt.count("<TMDB>") == 1 and _xt.count("<TMDbId>") == 1 and "<tmdbid></tmdbid>" in _nt and _valid(_n, _x), (_nt, _xt))
_r = scan(os.path.dirname(_n), use_ffprobe=False)
check("B13: row shows TMDB ○ with 'Missing TMDB ID (empty tags ready to fill)'", _r["source_tmdb_status"] == mc.STATUS_MISSING and "Missing TMDB ID (empty tags ready to fill)" in _r["health_reasons"] and _r["source_imdb_status"] == mc.STATUS_OK, (_r["source_tmdb_status"], _r["health_reasons"]))
# 6) <Title>-root movie.xml stays valid with placeholders; partly empty stays ✕
_n, _x = _b13_files("Title Root", "", "", xml_root="Title")
ok, err = mc._write_both_source_ids(_n, _x, "tt7777004", None)
check("B13: <Title>-root XML gets the placeholders inside </Title>", ok and _valid(_x) and _ET13.parse(_x).getroot().find("TMDB") is not None, _txt(_x))
_n, _x = _b13_files("Partly Empty", "\t<tmdbid>99</tmdbid>\n", "\t<TMDB></TMDB>\n")
_s = mc.extract_source_ids_from_files(_n, _x)
check("B13: some TMDB tags filled, some empty → still ✕ (not ○)", _s["tmdb_status"] == mc.STATUS_ERROR and _s["tmdb_empty_tags"] is False, _s)
# 7) Normalize Sources path: a single-type write adds the other source's placeholders
_n, _x = _b13_files("Single Type", "\t<imdbid>tt7777005</imdbid>\n", "")
ok, err = mc._write_source_id_to_files(_n, _x, "IMDB", "tt7777005")
check("B13: single-type write (Normalize Sources / Auto Repair) also leaves empty TMDB tags", ok and "<tmdbid></tmdbid>" in _txt(_n) and "<TMDB></TMDB>" in _txt(_x), _txt(_n))

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
check("B14: IMDb ID unknown to TMDB → IMDb-only candidate with OMDb title/year", _c and _c["imdb_only"] and _c["tmdb_id"] == "" and _c["title"] == "Padre Pio, uomo di Dio" and _c["year"] == "1999" and _m == "Not on TMDB — IMDb only", (_c, _m))
_c, _m = mc.lookup_typed_ids(_PP_IMDB, "", "k", fetch=_f14)
check("B14: without an OMDb key the IMDb-only candidate has no title (still usable)", _c and _c["imdb_only"] and _c["title"] == "", _c)
check("B14: format check still applies; IMDb + TMDB of different films still rejected", mc.lookup_typed_ids("tt12", "", "k", fetch=_f14)[0] is None and mc.lookup_typed_ids("tt0133094", "603", "k", fetch=_f14)[0] is None)
def _b14_row(name, nfo_ids, xml_ids, orig=None):
    d = os.path.join(_TMP, "b14", name); os.makedirs(d, exist_ok=True)
    _nfo(os.path.join(d, name + ".nfo"), "Padre Pio, homem de Deus", year="1999", original=orig, imdb=nfo_ids[0], tmdb=nfo_ids[1])
    _xml(os.path.join(d, "movie.xml"), "Padre Pio, homem de Deus", year="1999", original=orig, imdb=xml_ids[0], tmdb=xml_ids[1])
    return scan(d, use_ffprobe=False)
_r14 = _b14_row("PP Search", (_PP_IMDB, None), (_PP_IMDB, ""), orig="Padre Pio, uomo di Dio")
_b14_urls.clear()
_e14 = mc._search_sources_for_row(_r14, "k", "pt-BR", "ok", fetch=_f14, omdb_fetch=_omdb14)
check("B14: current IDs read from the files (IMDb tt12817760, TMDB —)", _e14["current"] == {"imdb": _PP_IMDB, "tmdb": ""}, _e14["current"])
check("B14: pinned row for the current IMDb ID even though TMDB does not know it", _e14["pinned"]["from"] == "IMDb" and _e14["pinned"]["cand"]["imdb_only"] and _e14["pinned"]["cand"]["title"] == "Padre Pio, uomo di Dio", _e14["pinned"])
_qs = [(_up.unquote(_re.search(r"query=([^&]+)", u).group(1)), _re.search(r"language=([\w-]+)", u).group(1)) for u in _b14_urls if "/search/movie" in u]
check("B14: title search in en-US, in the library language and with the original title", _qs == [("Padre Pio, homem de Deus", "en-US"), ("Padre Pio, homem de Deus", "pt-BR"), ("Padre Pio, uomo di Dio", "pt-BR")], _qs)
check("B14: results merged without duplicates", [m["tmdb_id"] for m in _e14["matches"]] == ["11", "12", "13", "603"], [m["tmdb_id"] for m in _e14["matches"]])
_r14b = _b14_row("PP Matrix Imdb", ("tt0133093", None), ("tt0133093", None))
_e14b = mc._search_sources_for_row(_r14b, "k", "en-US", "", fetch=_f14)
check("B14: IMDb ID that IS on TMDB → pinned film with both IDs ('From your current IMDb ID'), not repeated below", _e14b["pinned"]["from"] == "IMDb" and _e14b["pinned"]["cand"]["tmdb_id"] == "603" and _e14b["pinned"]["cand"]["imdb_id"] == "tt0133093" and "603" not in [m["tmdb_id"] for m in _e14b["matches"]], _e14b)
_r14c = _b14_row("PP Matrix Tmdb", ("", "603"), ("", "603"))
_e14c = mc._search_sources_for_row(_r14c, "k", "en-US", "", fetch=_f14)
check("B14: TMDB-only movie → pinned 'From your current TMDB ID' with the IMDb ID from TMDB", _e14c["pinned"]["from"] == "TMDB" and _e14c["pinned"]["cand"]["imdb_id"] == "tt0133093" and _e14c["current"] == {"imdb": "", "tmdb": "603"}, _e14c)
# id_check: verify keeps a confirmed IMDb-only film; Auto Repair stops proposing a TMDb search
_r14["id_check"] = mc._imdb_only_check(_PP_IMDB, "Padre Pio, uomo di Dio", "1999")
_v14 = mc.verify_movie_ids(_r14, "k", "pt-BR", fetch=_f14)
check("B14: Verify IDs keeps 'OK (IMDb only — not on TMDB)' while TMDB still does not know it", _v14["result"] == mc.ID_IMDB_ONLY, _v14)
_r14x = dict(_r14); _r14x["id_check"] = None
check("B14: without the confirmation Verify IDs still says 'ID does not exist'", mc.verify_movie_ids(_r14x, "k", "pt-BR", fetch=_f14)["result"] == mc.ID_NOT_FOUND)
check("B14: Auto Repair plans no TMDB search for a confirmed IMDb-only film", "ids_search" not in [c for c, _l in mc._auto_repair_plan(_r14, mc.SETTINGS)] and "ids_search" in [c for c, _l in mc._auto_repair_plan(_r14x, mc.SETTINGS)])

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
check("B24: one source + 'error' → 'Missing TMDB ID…' is an error", any(x.startswith("Missing TMDB ID") for x in _a["health_errors"]), _a["health_reasons"])
_a = _lv(_r24, single_source_level="warning")
check("B24: one source + 'warning' → reported as a warning, not an error", any(x.startswith("Missing TMDB ID") for x in _a["health_warnings"]) and not any(x.startswith("Missing TMDB ID") for x in _a["health_errors"]), (_a["health_errors"], _a["health_warnings"]))
_a = _lv(_r24, single_source_level="off")
check("B24: one source + 'off' → not reported at all", not any("Missing TMDB ID" in x or "Missing IMDb ID" in x for x in _a["health_reasons"]), _a["health_reasons"])
_a = _lv(_r24n, single_source_level="off")
check("B24: no source + 'error' (single 'off') → both missing IDs are errors", sum(1 for x in _a["health_errors"] if x.startswith("Missing ")) >= 2 and any("IMDb" in x for x in _a["health_errors"]), _a["health_errors"])   # B108 rule e (intended)
_a = _lv(_r24n, no_source_level="warning")
check("B24: no source + 'warning' → both as warnings", any(x.startswith("Missing IMDb ID") for x in _a["health_warnings"]) and any(x.startswith("Missing TMDB ID") for x in _a["health_warnings"]) and not any(x.startswith("Missing ") and " ID" in x for x in _a["health_errors"]), (_a["health_errors"], _a["health_warnings"]))
_a = _lv(_r24n, no_source_level="off")
check("B24: no source + 'off' → not reported", not any(x.startswith("Missing IMDb ID") or x.startswith("Missing TMDB ID") for x in _a["health_reasons"]), _a["health_reasons"])
_a = _lv(_r24, single_source_level="warning", missing_tmdb_id=False)
check("B24: the 'Missing TMDB ID' checkbox OFF still switches the reason off", not any("Missing TMDB ID" in x for x in _a["health_reasons"]))
check("B24: Auto Repair plans no TMDB search when the level is 'off'", "ids_search" not in [c for c, _l in mc._auto_repair_plan(_r24, mc.SETTINGS, dict(mc.SETTINGS["health_rules"], single_source_level="off"))]
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
# ### MODIFIED v0.19.2 B35 (intended) ### missing_folder is OFF by default now, so this check turns it ON
_rr = dict(_r); mc._apply_health(_rr, dict(mc.SETTINGS["health_rules"], folder_optional_with_kodi_poster=False, missing_folder=True), mc.SETTINGS)
check("B23: rule OFF (with 'Missing folder image' ON, B35) → 'Missing folder image' reported again", "Missing folder image" in _rr["health_reasons"])
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
check("B19: health reports the IMDb conflict (both values named)", any("IMDb ID conflict" in x and "tt7719002" in x and "tt7719003" in x for x in _ru["health_reasons"]), _ru["health_reasons"])
check("B19: Kodi's default=\"true\" uniqueid is the ID used (Kodi reads it first)", mc.get_movie_ids_robust(_u2, None)[0] == "tt7719002")
ok, err = mc._write_source_id_to_files(_u2, None, "IMDB", "tt7719009")
_t = _txt(_u2)
check("B19: Apply/Normalize updates the existing <uniqueid> (default attr kept), conflict gone", ok and '<uniqueid type="imdb" default="true">tt7719009</uniqueid>' in _t and _t.count("<uniqueid") == 1 and len(set(mc.extract_source_ids_from_files(_u2, None)["imdb_all_vals"])) == 1, _t)
_u3 = _uid_nfo("No Uid", '\t<imdbid>tt7719004</imdbid>\n')
ok, err = mc._write_both_source_ids(_u3, None, "tt7719004", "719004")
check("B125: an NFO without <uniqueid> gets one with the ID written; its other tags too", ok and '<uniqueid type="tmdb" default="true">719004</uniqueid>' in _txt(_u3) and "<tmdbid>719004</tmdbid>" in _txt(_u3), _txt(_u3))
_u4 = _uid_nfo("Uid Selfclose", '\t<uniqueid type="imdb" default="true">tt7719005</uniqueid>\n\t<uniqueid type="tmdb" />\n')
_s = mc.extract_source_ids_from_files(_u4, None)
check("B19: an empty <uniqueid type=\"tmdb\"/> counts as an empty tag (○, ready to fill)", _s["tmdb_status"] == mc.STATUS_MISSING and _s["tmdb_empty_tags"] is True, _s)
ok, err = mc._write_source_id_to_files(_u4, None, "TMDB", "719005")
_t = _txt(_u4)
check("B19: the self-closing <uniqueid type=\"tmdb\"/> is filled in place", ok and '<uniqueid type="tmdb">719005</uniqueid>' in _t and _t.count('type="tmdb"') == 1 and _valid(_u4), _t)
_u5 = _uid_nfo("Uid Themoviedb", '\t<uniqueid type="themoviedb">719006</uniqueid>\n')
check("B19: type=\"themoviedb\" accepted as TMDB", mc.extract_source_ids_from_files(_u5, None)["tmdb_val"] == "719006")

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
    check("B20: the final message names it once (+ B22 advice)", len(_sum20) == 1 and _sum20[0].startswith("OMDb (IMDb data) unavailable for the rest of this run (daily request limit reached) — not asked again (3 requests saved).") and "Try again in a few hours or tomorrow" in _sum20[0], _sum20)
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
    check("B20: TMDB 'invalid API key' (HTTP 401) → blocked after the first answer", len(_calls20) == 1 and mc._service_blocked("tmdb") == "invalid_key", (len(_calls20), mc._service_blocked("tmdb")))
    try:
        mc._tmdb_rate_limited_fetch("https://api.themoviedb.org/3/movie/1?api_key=SECRET"); _su = None
    except mc.ServiceUnavailable as ex:
        _su = str(ex)
    check("B20: a blocked service raises ServiceUnavailable with a clear text (no key in it)", _su == "TMDB unavailable (API key rejected)" and "SECRET" not in (_su or ""), _su)
    mc._service_run_end()
finally:
    mc._tmdb_fetch_json, mc.time.sleep = _ofj20, _osl20
    mc._service_run_end(); mc._HTTP_TIMES.clear(); mc._TMDB_RATE_TIMES.clear()
    mc._api_pauses_clear()

# ── v0.19.1 B22: failure kinds, messages, pauses ──────────────────────────────   ### NEW v0.19.1 B22 ###
section("2t. TMDB/OMDb failure messages + pauses (v0.19.1 B22)")
_cases22 = [("tmdb", _http_err(429), "rate_limited"), ("omdb", _http_err(401, body=b'{"Error":"Request limit reached!"}'), "daily_limit"),
            ("tmdb", _http_err(401, body=b'{"status_message":"Invalid API key"}'), "invalid_key"), ("tmdb", _http_err(503), "server_error"),
            ("tmdb", _ue2.URLError("timed out"), "timeout"), ("tmdb", _ue2.URLError("getaddrinfo failed"), "offline"), ("tmdb", _http_err(404), None)]
_got22 = [mc.classify_api_failure(s, exc=e) for s, e, _k in _cases22]
check("B22: every failure is classified (rate_limited, daily_limit, invalid_key, server_error, timeout, offline; 404 = none)", _got22 == [k for _s, _e, k in _cases22], _got22)
check("B22: OMDb JSON 'Request limit reached!' = daily_limit; 'Movie not found!' = no failure", mc.classify_api_failure("omdb", data={"Response": "False", "Error": "Request limit reached!"}) == "daily_limit" and mc.classify_api_failure("omdb", data={"Response": "False", "Error": "Movie not found!"}) is None)
_texts22 = {k: mc.api_failure_message(s, k) for s, k in (("tmdb", "rate_limited"), ("omdb", "daily_limit"), ("tmdb", "invalid_key"), ("tmdb", "offline"), ("tmdb", "server_error"))}
check("B22: TMDB rate limit → 'too many requests … Wait about a minute and try again.'", _texts22["rate_limited"] == "TMDB is receiving too many requests from this computer. Wait about a minute and try again.", _texts22["rate_limited"])
check("B22: OMDb daily limit → 'OMDb (IMDb data): the free daily limit … Try again in a few hours or tomorrow. TMDB ratings still work.'", _texts22["daily_limit"] == "OMDb (IMDb data): the free daily limit of 1,000 requests is used up. Try again in a few hours or tomorrow. TMDB ratings still work.", _texts22["daily_limit"])
check("B22: invalid key / offline / server error texts", _texts22["invalid_key"] == "TMDB rejected the API key. Check Settings → API Keys (Validate)." and _texts22["offline"].startswith("No internet connection, or TMDB cannot be reached.") and _texts22["server_error"].startswith("TMDB is not responding right now. Try again in a few minutes"), _texts22)
check("B22: Enter ID… / Fetch / Verify use the same text (via _tmdb_error_message)", mc._tmdb_error_message(_http_err(429)).startswith(_texts22["rate_limited"]) and "SECRETKEY123" not in mc._tmdb_error_message(_http_err(429)))
import settings_dialog as _sd22
check("B22: Settings → Validate buttons use the same texts", _sd22._validate_failure_text("TMDB", "rate_limited") == "✗ " + _texts22["rate_limited"])
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
    check("B22: TMDB 429 after the retries → TMDB paused about a minute", _p22 and _p22["kind"] == "rate_limited" and 0 < (_dt22.datetime.fromisoformat(_p22["until"]) - _dt22.datetime.now()).total_seconds() <= 60, _p22)
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
check("B22: Search Sources remembers that TMDB did not answer (search_error)", _e22s["matches"] == [] and (_e22s.get("search_error") or "").startswith("TMDB is receiving too many requests"), _e22s.get("search_error"))
_o_rl22 = mc._tmdb_rate_limited_fetch; _ok22 = mc.SETTINGS.get("tmdb_api_key", "")
try:
    mc.SETTINGS["tmdb_api_key"] = "k"
    mc._tmdb_rate_limited_fetch = _f22_429
    _lk = mc._lookup_id_info_ex("TMDB", "603")
    mc._tmdb_rate_limited_fetch = lambda url, timeout=15: (_ for _ in ()).throw(_http_err(404))
    _lk404 = mc._lookup_id_info_ex("TMDB", "999")
finally:
    mc._tmdb_rate_limited_fetch = _o_rl22; mc.SETTINGS["tmdb_api_key"] = _ok22
check("B22: Normalize Sources lookup tells 'TMDB did not answer' from 'ID not found'", _lk[0] is None and (_lk[2] or "").startswith("TMDB is receiving too many requests") and _lk404 == (None, None, None), (_lk, _lk404))
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
check("I10: each entry shows its source, size and likes", mc.image_entry_text(_bb10[0])[0] == "fanart.tv" and "~1920×1080" in mc.image_entry_text(_bb10[0])[1] and "♥7" in mc.image_entry_text(_bb10[0])[1] and mc.image_entry_text(_tm10[0])[0] == "TMDB")
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
    check("I10: asked by TMDB ID with api_key and client_key", _e10 is None and _d10 is _fd10 and len(_calls10) == 1 and _calls10[0][0] == "fanarttv" and "/v3/movies/603?api_key=SECRETFAN&client_key=SECRETVIP" in _calls10[0][1], _calls10)
    check("I10: the keys are redacted in log text", "SECRET" not in mc._redact(_calls10[0][1]))
    _calls10.clear()
    _d10b, _ = mc.fanarttv_fetch("603", "tt0133093")
    check("I10: the answer is cached (no second request)", not _calls10 and _d10b == _fd10)
    _cft = io.open(sc.FANARTTV_CACHE_PATH, encoding="utf-8").read()
    check("I10: fanarttv_cache.json next to settings.json, without any key", os.path.dirname(sc.FANARTTV_CACHE_PATH) == os.path.dirname(sc.CONFIG_PATH) and "tmdb:603" in json.loads(_cft) and "SECRET" not in _cft)
    _calls10.clear()
    _d10c, _e10c = mc.fanarttv_fetch("604", "tt0000604")
    check("I10: not found by TMDB ID → asked by IMDb ID", [u.split("/movies/")[1].split("?")[0] for _s, u in _calls10] == ["604", "tt0000604"] and _e10c is None and _d10c == _fd10, _calls10)
    _calls10.clear()
    mc.fanarttv_fetch("604", None)
    check("I10: a 'not on fanart.tv' answer is cached too", not _calls10, _calls10)
    check("I10: no TMDB or IMDb ID → the dialog says so", "no TMDB or IMDb ID" in (mc.fanarttv_fetch(None, None)[1] or ""))
    check("I10: an old cache entry (> 7 days) is asked again", (mc._FANARTTV_CACHE.__setitem__("tmdb:603", {"t": time.time() - 8 * 86400, "data": _fd10}), mc.fanarttv_fetch("603", None), len(_calls10))[2] == 1, _calls10)
    sc.save_fanarttv_cache({"tmdb:1": {"t": time.time() - 9 * 86400, "data": {"a": 1}}, "tmdb:2": {"t": time.time(), "data": {}}})
    check("I10: old entries are dropped when the cache is saved", list(sc.load_fanarttv_cache()) == ["tmdb:2"])
    io.open(sc.FANARTTV_CACHE_PATH, "w", encoding="utf-8").write("{ broken")
    check("I10: a corrupt cache file is ignored", sc.load_fanarttv_cache() == {})
    # ### NEW v0.19.5 I20 ### another program reading the cache must not lose a save (Windows refuses the replace meanwhile)
    if sys.platform == "win32":
        _p20 = os.path.join(_TMP, "i20_cache.json")
        open(_p20, "w", encoding="utf-8").write('{"a": 0}')
        def _hold20(sec):
            f = open(_p20, "r", encoding="utf-8"); time.sleep(sec); f.close()
        _th20 = threading.Thread(target=_hold20, args=(0.2,), daemon=True); _th20.start(); time.sleep(0.05)
        sc._save_json_atomic(_p20, {"a": 1}); _th20.join()
        check("I20: a save waits for a short read of the file and is not lost", json.load(open(_p20, encoding="utf-8")) == {"a": 1})
        _th20 = threading.Thread(target=_hold20, args=(1.5,), daemon=True); _th20.start(); time.sleep(0.05)
        _er20 = ""
        try:
            sc._save_json_atomic(_p20, {"a": 2})
        except PermissionError as _x20:
            _er20 = str(_x20)
        _th20.join()
        check("I20: a file held longer: the save fails with an error (not silently), the old file is intact, no temp file is left",
              bool(_er20) and json.load(open(_p20, encoding="utf-8")) == {"a": 1} and not [n for n in os.listdir(_TMP) if n.startswith("i20_cache.json.")], _er20)
    mc._LAST_IMAGE_SOURCE[0] = None
    check("I10: default source = Both with a fanart.tv key, fanart.tv when TMDB cannot be used", mc.default_image_source() == "both" and mc.default_image_source(tmdb_ok=False) == "fanarttv")
    mc._LAST_IMAGE_SOURCE[0] = "fanarttv"
    check("I10: the choice made in a dialog is kept for the session", mc.default_image_source() == "fanarttv")
    mc.SETTINGS["fanarttv_api_key"] = ""
    check("I10: no fanart.tv key → TMDB, and fanart.tv is not asked", mc.default_image_source() == "tmdb" and "No fanart.tv API key" in mc.fanarttv_fetch("603", None)[1])
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
    def _fake_ex11(video, ts, outp, timeout_sec=60, **kw):     # **kw: cancel / keyframes since v0.19.2 B28
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
    mc.extract_single_frame = lambda v, ts, o, timeout_sec=60, **kw: (False, "boom")   # **kw since v0.19.2 B28
    try:
        check("B11: FFmpeg failing → a clear message, no frames", mc.extract_movie_frames(SAMPLE_VIDEO, os.path.join(_TMP, "b11_frames3"))[1].startswith("FFmpeg could not extract frames: boom"))
    finally:
        mc.extract_single_frame = _o11

# ── v0.19.2 B26: window and taskbar icon ──────────────────────────────────────   ### NEW v0.19.2 B26 ###
section("2z. window icon (v0.19.2 B26)")
from PIL import Image as _PILImage26
_ico26 = mc._app_icon_path()
if sys.platform == "win32": check("B26: _app_icon_path() finds MediaClinic.ico next to the script", _ico26 is not None and os.path.normcase(os.path.dirname(_ico26)) == os.path.normcase(_APP_DIR) and os.path.basename(_ico26) == "MediaClinic.ico", _ico26)
_sizes26 = set()
try:
    _sizes26 = {s[0] for s in _PILImage26.open(_ico26).info.get("sizes", set())}
except Exception as _e26:
    _sizes26 = {str(_e26)}
if sys.platform == "win32": check("B26: the .ico opens with Pillow and has 16 px and 256 px images", {16, 256} <= _sizes26, sorted(map(str, _sizes26)))
_corners26 = []
for _n26 in (16, 32, 256):
    _im26 = _PILImage26.open(_ico26); _im26.size = (_n26, _n26); _im26 = _im26.convert("RGBA")
    _corners26.append((_n26, _im26.getpixel((0, 0))[3], _im26.getpixel((_n26 // 2, _n26 // 2))[3]))
check("B54: icon has transparent corners and an opaque centre (16 / 32 / 256 px)", all(c == 0 and m == 255 for _n, c, m in _corners26), _corners26)
check("B54: the B51 small title-bar icon exists (16–32 px)", {16, 32} <= {s[0] for s in _PILImage26.open(os.path.join(_APP_DIR, "MediaClinic-small.ico")).info.get("sizes", set())})

# ── v0.19.2 B27: a legacy cached row gets every key of a fresh row ────────────   ### NEW v0.19.2 B27 ###
section("2za. legacy cached rows + exception hooks (v0.19.2 B27)")
_fresh27 = scan(M_OK)
_old27 = mc._results_from_json([{"subfolder": "OldRow", "subfolder_path": "X:/nowhere/OldRow"},
                                {"subfolder": "OldRow2", "subfolder_path": "X:/nowhere/OldRow2"}])
_miss27 = sorted(set(_fresh27) - set(_old27[0]) - {"subfolder", "subfolder_path"})
check("B27: a legacy cached row gets every key a fresh scan row has (no KeyError 'poster_exists')", not _miss27 and _old27[0]["poster_exists"] is False and _old27[0]["nfo_status"] == mc.STATUS_MISSING, _miss27)
_old27[0]["backdrop_paths"].append("x"); _old27[0]["poster_tried"].append("y")
check("B27: restored rows never share a default list", _old27[1]["backdrop_paths"] == [] and _old27[1]["poster_tried"] == [])
mc.finalize_results(_old27)
check("B27: finalize_results accepts the legacy rows", all("health_status" in r for r in _old27))
check("B27: the exception hooks are installed (sys + threading, chained)", sys.excepthook is mc._sys_hook and threading.excepthook is mc._thread_hook and mc._prev_thread_hook is not mc._thread_hook)
def _log27(want):                                   ### NEW v0.19.5 I22 ### the line, not a fixed moment; the log may have rotated after it
    def _rd():
        out = ""
        for p in (mc.LOG_PATH + ".1", mc.LOG_PATH):
            if os.path.isfile(p):
                out += io.open(p, encoding="utf-8", errors="replace").read()
        return out
    _end = time.time() + 10
    while want not in _rd() and time.time() < _end:
        time.sleep(0.05)
    return _rd()
_t27 = threading.Thread(target=lambda: {}["b27_thread_key"], daemon=True, name="B27-test")
_t27.start(); _t27.join(5); _UNH_PROVOKED.append("thread")
_l27 = _log27("KeyError: 'b27_thread_key'")
check("B27: an uncaught worker-thread exception is logged with its traceback", "Unhandled exception (thread B27-test)" in _l27 and "KeyError: 'b27_thread_key'" in _l27)
def _leak27():
    raise RuntimeError("download failed: https://x.test/?api_key=SECRETB27KEY")
_t27b = threading.Thread(target=_leak27, daemon=True, name="B27-key")
_t27b.start(); _t27b.join(5); _UNH_PROVOKED.append("thread-key")
_l27 = _log27("api_key=***")
check("B27: an API key in an unhandled exception is redacted in app.log", "Unhandled exception (thread B27-key)" in _l27 and "SECRETB27KEY" not in _l27 and "api_key=***" in _l27)

# ── v0.19.2 B36: settings.json atomic + locked; corrupt file kept ─────────────   ### NEW v0.19.2 B36 ###
section("2zb. settings.json safe save / corrupt file kept (v0.19.2 B36)")
_d36 = os.path.join(_TMP, "b36"); os.makedirs(_d36, exist_ok=True)
_cfg36 = os.path.join(_d36, "settings.json")
_orig_cfg36 = sc.CONFIG_PATH
sc.CONFIG_PATH = _cfg36
try:
    _ok36 = []
    def _saver36(tag):
        for i in range(200):
            _ok36.append(sc.save_settings({"who": tag, "i": i, "pad": "x" * (i * 37 % 4000), "health_rules": {"a": i}}))
    _th36 = [threading.Thread(target=_saver36, args=(t,), daemon=True) for t in ("A", "B")]
    for t in _th36: t.start()
    for t in _th36: t.join(60)
    _last36 = json.load(open(_cfg36, encoding="utf-8"))
    check("B36: 2 threads × 200 saves → every save succeeded and settings.json is valid JSON", len(_ok36) == 400 and all(_ok36) and _last36.get("i") == 199, (len(_ok36), _ok36.count(False), _last36.get("i")))
    check("B36: no temp file left behind", [n for n in os.listdir(_d36) if n != "settings.json"] == [], os.listdir(_d36))
    # a truncated file (crash in the middle of an old-style write)
    _bad36 = b'{\n  "tmdb_api_key": "abc",\n  "library_folders": ["Z:\\\\Filmes'
    with open(_cfg36, "wb") as f:
        f.write(_bad36)
    sc.SETTINGS_LOAD_PROBLEM.update(error="", corrupt_copy=None)
    _s36 = sc.load_settings()
    _kept36 = sc.SETTINGS_LOAD_PROBLEM.get("corrupt_copy")
    check("B36: a settings.json that does not parse → defaults in use", _s36.get("library_folders") == DEFAULT_SETTINGS.get("library_folders") and _s36.get("health_rules") == DEFAULT_SETTINGS["health_rules"])
    check("B36: … and it is kept as settings.json.corrupt-YYYYMMDD-HHMMSS (same bytes) + flag set",
          bool(_kept36) and _re.search(r"settings\.json\.corrupt-\d{8}-\d{6}$", _kept36) is not None
          and open(_kept36, "rb").read() == _bad36 and sc.SETTINGS_LOAD_PROBLEM.get("error"), (_kept36, sc.SETTINGS_LOAD_PROBLEM))
    sc.save_settings(_s36)
    check("B36: the next save never overwrites the kept copy", open(_kept36, "rb").read() == _bad36)
    os.remove(_kept36)
    with open(_cfg36, "w", encoding="utf-8") as f:
        f.write("[1, 2]")
    sc.SETTINGS_LOAD_PROBLEM.update(error="", corrupt_copy=None)
    sc.load_settings()
    check("B36: a file whose top level is not an object is kept aside too", bool(sc.SETTINGS_LOAD_PROBLEM.get("corrupt_copy")))
    os.remove(sc.SETTINGS_LOAD_PROBLEM["corrupt_copy"]); os.remove(_cfg36)
    sc.SETTINGS_LOAD_PROBLEM.update(error="", corrupt_copy=None)
    sc.load_settings()
    check("B36: a missing settings.json is no problem (first start)", not sc.SETTINGS_LOAD_PROBLEM.get("error"))
    sc.CONFIG_PATH = os.path.join(_d36, "no_such_folder", "settings.json")
    _r36 = sc.save_settings({"a": 1})
    _l36 = io.open(mc.LOG_PATH, encoding="utf-8", errors="replace").read()
    check("B36: a failed save is logged, not swallowed (returns False)", _r36 is False and "settings.json not saved" in _l36)
finally:
    sc.CONFIG_PATH = _orig_cfg36
    sc.SETTINGS_LOAD_PROBLEM.update(error="", corrupt_copy=None)

# ── v0.19.2 B37: non-UTF-8 NFO/XML never rewritten; BOM kept ──────────────────   ### NEW v0.19.2 B37 ###
section("2zc. non-UTF-8 NFO/XML are never corrupted (v0.19.2 B37)")
_d37 = os.path.join(_TMP, "b37"); os.makedirs(_d37, exist_ok=True)
_cp37 = os.path.join(_d37, "cp1252.nfo")
_cp37_bytes = ('<?xml version="1.0" encoding="windows-1252"?>\n<movie>\n  <title>Amélie</title>\n'
               '  <rating>7.1</rating>\n  <votes>100</votes>\n  <genre>Comédie</genre>\n'
               '  <imdbid>tt0211915</imdbid>\n</movie>\n').encode("cp1252")
with open(_cp37, "wb") as f:
    f.write(_cp37_bytes)
_cpx37 = os.path.join(_d37, "cp1252.xml")
_cpx37_bytes = '<Title>\n  <LocalTitle>Amélie</LocalTitle>\n  <Rating>7.1</Rating>\n</Title>\n'.encode("cp1252")
with open(_cpx37, "wb") as f:
    f.write(_cpx37_bytes)
def _same37():
    return open(_cp37, "rb").read() == _cp37_bytes and open(_cpx37, "rb").read() == _cpx37_bytes
_e37 = mc.write_rating_to_files(_cp37, _cpx37, "8.0", "2000", movie_name="B37 test")
check("B37: Sync Ratings on cp1252 NFO + XML → both files byte-identical, 'not UTF-8 — not changed' reported", _same37() and len(_e37) == 2 and all("is not UTF-8 — not changed" in e for e in _e37), _e37)
_g37 = (mc.write_genres_to_nfo(_cp37, ["Drama", "Comedy"]), mc.write_genres_to_xml(_cpx37, ["Drama"]))
check("B37: Normalize Genres writers leave cp1252 files untouched", _same37() and all(ok is False and "not UTF-8" in msg for ok, msg in _g37), _g37)
_i37 = mc._write_source_id_to_files(_cp37, _cpx37, "TMDB", "194")
check("B37: an ID write leaves cp1252 files untouched", _same37() and _i37[0] is False and "not UTF-8" in _i37[1], _i37)
_t37 = mc._write_tag_in_files(_cp37, _cpx37, "title", "LocalTitle", "Amélie")
_h37 = mc._write_hardsub_tags(_cp37, _cpx37, ["POR"])
check("B37: tag writer (Auto Repair) and hard-sub writer leave cp1252 files untouched", _same37() and _t37[0] is False and _h37[0] is False, (_t37, _h37))
_n37 = []
mc.validate_xml_file(_cp37, True, infos=_n37)
check("B37: the scan adds an info note 'Not UTF-8 (byte 0xE9)' with its line", any(n["message"].startswith("Not UTF-8 (byte 0xE9)") and n["line"] == 3 for n in _n37), _n37)
_ok37 = os.path.join(_d37, "plain.nfo")
with open(_ok37, "w", encoding="utf-8") as f:
    f.write("<movie>\n  <title>Amélie</title>\n  <rating>7.1</rating>\n</movie>\n")
_n37b = []
mc.validate_xml_file(_ok37, True, infos=_n37b)
check("B37: a UTF-8 file gets no 'Not UTF-8' note", not any("Not UTF-8" in n["message"] for n in _n37b), _n37b)
# UTF-8 with BOM: written, BOM kept, text intact
_bom37 = os.path.join(_d37, "bom.nfo")
with open(_bom37, "wb") as f:
    f.write(b"\xef\xbb\xbf" + "<movie>\n  <title>Amélie</title>\n  <rating>7.1</rating>\n</movie>\n".encode("utf-8"))
_eb37 = mc.write_rating_to_files(_bom37, None, "8.0", "2000", movie_name="B37 test")
_bb37 = open(_bom37, "rb").read()
check("B37: a UTF-8-BOM NFO is written and keeps its BOM (one BOM, text intact)", not _eb37 and _bb37.startswith(b"\xef\xbb\xbf<movie>") and _bb37.count(b"\xef\xbb\xbf") == 1 and "Amélie" in _bb37.decode("utf-8-sig") and "<rating>8.0</rating>" in _bb37.decode("utf-8-sig"), _bb37[:40])
_ep37 = mc.write_rating_to_files(_ok37, None, "8.0", "2000", movie_name="B37 test")
_pb37 = open(_ok37, "rb").read()
check("B37: plain UTF-8 is written as before (no BOM added)", not _ep37 and not _pb37.startswith(b"\xef\xbb\xbf") and b"<rating>8.0</rating>" in _pb37, _pb37[:40])

# ── v0.19.2 B38: Sync Ratings changes only the chosen Kodi <ratings> block ────   ### NEW v0.19.2 B38 ###
section("2zd. Sync Ratings and the Kodi <ratings> block (v0.19.2 B38)")
_tmdb38 = ('    <rating name="themoviedb" max="10">\n      <value>7.4</value>\n      <votes>5321</votes>\n'
           '    </rating>\n')
_trakt38 = ('    <rating name="trakt" max="10">\n      <value>7.9</value>\n      <votes>888</votes>\n'
            '    </rating>\n')
_nfo38 = os.path.join(_d37, "kodi_ratings.nfo")
with open(_nfo38, "w", encoding="utf-8", newline="\n") as f:
    f.write('<movie>\n  <title>Ratings</title>\n  <rating>7.0</rating>\n  <votes>10</votes>\n  <ratings>\n'
            '    <rating name="imdb" max="10" default="true">\n      <value>7.1</value>\n      <votes>100</votes>\n'
            '    </rating>\n' + _tmdb38 + _trakt38 + '  </ratings>\n</movie>\n')
_e38 = mc.write_rating_to_files(_nfo38, None, "8.2", "2000", movie_name="B38 test")
_t38 = open(_nfo38, encoding="utf-8").read()
_imdb38 = mc._KODI_RATING_RE.search(mc._KODI_RATINGS_RE.search(_t38).group(1))   # first <rating> INSIDE the block
check("B38: legacy <rating>/<votes> outside the block are updated", not _e38 and "<rating>8.2</rating>" in _t38 and "<votes>2000</votes>\n  <ratings>" in _t38, _t38)
check("B38: the chosen (default / imdb) block gets the new value and votes", _imdb38 and 'name="imdb"' in _imdb38.group(1) and "<value>8.2</value>" in _imdb38.group(2) and "<votes>2000</votes>" in _imdb38.group(2), _t38)
check("B38: the themoviedb and trakt blocks stay byte-identical", _tmdb38 in _t38 and _trakt38 in _t38, _t38)

# ── v0.19.5 B122: each value under its own source's name ──   ### NEW v0.19.5 B122 ###
_p122 = os.path.join(_TMP, "b122.nfo")
_N122 = ('<movie>\n  <title>R</title>\n  <rating>8.8</rating>\n  <votes>2530924</votes>\n  <ratings>\n'
         '    <rating name="imdb" max="10" default="true">\n      <value>8.8</value>\n      <votes>2530924</votes>\n    </rating>\n'
         '    <rating name="trakt" max="10">\n      <value>8.1</value>\n      <votes>5</votes>\n    </rating>\n  </ratings>\n</movie>\n')
def _w122(text, *args, **kw):
    io.open(_p122, "w", encoding="utf-8", newline="\n").write(text)
    err = mc.write_rating_to_files(_p122, None, *args, backup=False, **kw)
    return err, io.open(_p122, encoding="utf-8").read()
def _ents122(t):
    b = mc._KODI_RATINGS_RE.search(t).group(1)
    return [(re.search(r'name="(\w+)"', i.group(1)).group(1), 'default="true"' in i.group(1), re.search(r"<value>([^<]*)", i.group(2)).group(1),
             re.search(r"<votes>([^<]*)", i.group(2)).group(1)) for i in mc._KODI_RATING_RE.finditer(b)]
_e122, _t122 = _w122(_N122, "7.4", "7761", source="themoviedb")
check("B122: TMDB's value goes in a themoviedb entry, the only default, last; IMDb's value is not lost; the flat tags follow",
      not _e122 and _ents122(_t122) == [("imdb", False, "8.8", "2530924"), ("trakt", False, "8.1", "5"), ("themoviedb", True, "7.4", "7761")]
      and "<rating>7.4</rating>" in _t122 and "<votes>7761</votes>" in _t122, _t122)
_e122, _t122b = _w122(_t122, "8.9", "2600000", source="imdb")
check("B122: IMDb chosen next: its entry updated and default, moved last; TMDB's kept",
      not _e122 and _ents122(_t122b) == [("trakt", False, "8.1", "5"), ("themoviedb", False, "7.4", "7761"), ("imdb", True, "8.9", "2600000")], _t122b)
_e122, _t122c = _w122(_N122, "6.0", "10")
check("B122: a typed value has no source: it stays on the current default entry",
      not _e122 and _ents122(_t122c)[0] == ("imdb", True, "6.0", "10") and _ents122(_t122c)[1] == ("trakt", False, "8.1", "5"), _t122c)
_e122, _t122d = _w122("<movie>\n  <title>R</title>\n</movie>\n", "7.0", "100", source="imdb")
check("B122: an NFO with no block gets one; WR-A5: nothing is counted as written without a tag",
      not _e122 and _ents122(_t122d) == [("imdb", True, "7.0", "100")] and _t122d.rstrip().endswith("</movie>"), _t122d)
_e122, _t122e = _w122("<movie>\n  <title>R</title>\n</movie>\n", "7.0", "100")
check("WR-A5: a typed value with no tag creates <rating> and <votes>", not _e122 and "<rating>7.0</rating>" in _t122e and "<votes>100</votes>" in _t122e, _t122e)
check("B122: every result is well-formed XML", all(mc.ET.fromstring(t) is not None for t in (_t122, _t122b, _t122c, _t122d, _t122e)) if hasattr(mc, "ET") else True)
check("B122: the label → the source; typed and average → none",
      (mc._rating_source_name("TMDB"), mc._rating_source_name("OMDb/IMDb"), mc._rating_source_name("typed"), mc._rating_source_name("average"))
      == ("themoviedb", "imdb", None, None))
check("WR-A5: no NFO and no XML is an error, not a success", mc.write_rating_to_files(None, None, "7", "1", backup=False) != [])

# ── v0.19.5 WR-A1, WR-A2, WR-A4, AS-A7, B125: the writers ──   ### NEW v0.19.5 ###
def _f125(text, name="w125.nfo"):
    p = os.path.join(_TMP, name); io.open(p, "w", encoding="utf-8", newline="\n").write(text); return p
_rd125 = lambda p: io.open(p, encoding="utf-8").read()
def _ok125(p):
    try:
        mc.ET.parse(p); return True
    except mc.ET.ParseError:
        return False
_p = _f125("<movie><title>x</title><genre>Drama</genre></movie>\n")
_r = mc._write_tag_in_files(_p, None, "year", "ProductionYear", "2000")
check("WR-A2: a one-line NFO stays valid; the new tag is inside the root", _r[0] and _ok125(_p) and mc.ET.parse(_p).getroot().findtext("year") == "2000", _rd125(_p))
_p = _f125("<movie><title>x</title></movie>\n")
_r = mc._write_source_id_to_files(_p, None, "IMDB", "tt0133093")
check("WR-A2: IDs on a one-line NFO too", _r[0] and _ok125(_p) and mc.ET.parse(_p).getroot().findtext("imdbid") == "tt0133093", (_r, _rd125(_p)))
_p = _f125("not xml at all\n"); _b = _rd125(_p)
_r = mc._write_tag_in_files(_p, None, "year", None, "2000")
check("WR-A2: text that is not XML is refused and left as it was", not _r[0] and _rd125(_p) == _b, _r)
_p = _f125("<Title><LocalTitle>Bad</Title>\n", "w125.xml"); _b = _rd125(_p)
_r = mc._write_tag_in_files(None, _p, None, "LocalTitle", "New")
check("AS-A7: a corrupt movie.xml gets no more junk and the fix is not reported as done", not _r[0] and _rd125(_p) == _b, _r)
_p = _f125("<movie>\n  <title />\n  <year>2000</year>\n</movie>\n")
_r = mc._write_tag_in_files(_p, None, "title", None, "Foo")
check("WR-A1: <title /> is filled in place, no second tag", _r[0] and mc.ET.parse(_p).getroot().findtext("title") == "Foo" and _rd125(_p).count("<title") == 1, _rd125(_p))
_p = _f125("<movie>\n  <title><![CDATA[Old]]></title>\n</movie>\n")
_r = mc._write_tag_in_files(_p, None, "title", None, "New")
check("WR-A1: a CDATA title is replaced", _r[0] and mc.ET.parse(_p).getroot().findtext("title") == "New" and _rd125(_p).count("<title") == 1, _rd125(_p))
_p = _f125("<Title>\n  <IMDB />\n</Title>\n", "w125.xml")
_r = mc._write_source_id_to_files(None, _p, "IMDB", "tt0133093")
check("WR-A1: <IMDB /> is filled in place", _r[0] and "<IMDB>tt0133093</IMDB>" in _rd125(_p) and _rd125(_p).count("<IMDB>") == 1, _rd125(_p))
_p = _f125('<movie>\n  <id moviedb="tmdb" />\n</movie>\n')
_r = mc._write_source_id_to_files(_p, None, "TMDB", "603")
check("WR-A1: <id moviedb=\"tmdb\" /> is filled in place, its attribute kept", _r[0] and '<id moviedb="tmdb">603</id>' in _rd125(_p) and _rd125(_p).count('moviedb="tmdb"') == 1, _rd125(_p))
_p = _f125("<movie>\n  <imdbid></imdbid>\n</movie>\n")
_r = mc._write_source_id_to_files(_p, None, "IMDB", "tt0133093\\")
check("WR-A4: a value ending in a backslash no longer breaks the file", _r[0] and _ok125(_p) and "<imdbid>tt0133093</imdbid>" in _rd125(_p), _rd125(_p))
_p = _f125('<movie>\n  <id moviedb="tmdb">603</id>\n  <title>T</title>\n</movie>\n')
_r = mc._write_source_id_to_files(_p, None, "IMDB", "tt0133093")
_t = _rd125(_p)
check("B125: the plain <id> comes before <id moviedb=…>, so Kodi's first id is the IMDb one", _r[0] and _t.index("<id>tt0133093</id>") < _t.index('<id moviedb="tmdb"'), _t)
_p = _f125('<movie>\n  <uniqueid type="tmdb" default="true" extra="1">1</uniqueid>\n</movie>\n')
_r = mc._write_source_id_to_files(_p, None, "TMDB", "603")
_r2 = mc._write_source_id_to_files(_p, None, "IMDB", "tt0133093")
_t = _rd125(_p)
check("B125: an existing uniqueid keeps its attributes and one default stays; the missing type is added, not as default",
      '<uniqueid type="tmdb" default="true" extra="1">603</uniqueid>' in _t and '<uniqueid type="imdb">tt0133093</uniqueid>' in _t and _t.count('default="true"') == 1, _t)
_p = _f125("<movie>\n  <title>T</title>\n</movie>\n")
mc._write_source_id_to_files(_p, None, "TMDB", "603")
_ids125 = mc.get_movie_ids_robust(_p, None)
check("B125: an NFO with no IDs reads them back; the file is valid", _ok125(_p) and _ids125[1] == "603", (_ids125, _rd125(_p)))

# ── v0.19.5 B127: one codec, many names ──   ### NEW v0.19.5 B127 ###
import collection_rules as _cr
_same127 = [("h264", "H.264"), ("h264", "AVC"), ("h264", "x264"), ("h264", "MPEG-4 AVC"), ("hevc", "H.265"), ("hevc", "x265"), ("hevc", "HEVC"), ("hevc", "hvc1"),
            ("mpeg4", "XviD"), ("mpeg4", "DivX"), ("mpeg4", "DX50"), ("mpeg4", "MP4V"), ("mpeg4", "MPEG-4 Visual"), ("msmpeg4v3", "XviD"), ("mpeg2video", "MPEG-2"), ("mpeg1video", "MPEG-1"),
            ("vc1", "VC-1"), ("vc1", "WVC1"), ("wmv3", "WMV9"), ("av1", "AV1"), ("vp9", "VP9"), ("vp8", "VP8"), ("h263", "H.263"),
            ("aac", "AAC LC"), ("aac", "Advanced Audio Coding"), ("aac", "HE-AAC"), ("aac", "MP4A"), ("ac3", "AC-3"), ("ac3", "Dolby Digital"), ("ac3", "DD"), ("ac3", "A52"),
            ("eac3", "E-AC-3"), ("eac3", "E-AC3"), ("eac3", "Dolby Digital Plus"), ("eac3", "DD+"), ("eac3", "DDP"), ("dts", "DTS-HD MA"), ("dts", "dca"), ("dts", "DTS-ES"), ("dts", "DTS:X"),
            ("truehd", "Dolby TrueHD"), ("truehd", "MLP FBA"), ("mp3", "MP3"), ("mp2", "MP2"), ("flac", "FLAC"), ("opus", "Opus"), ("vorbis", "Vorbis"),
            ("pcm_s16le", "PCM"), ("pcm_s24le", "LPCM"), ("wmav2", "WMA"), ("wmapro", "WMA Pro")]
_bad127 = [p for p in _same127 if mc.codec_family(p[0]) is None or mc.codec_family(p[0]) != mc.codec_family(p[1])]
check(f"B127: every line of the table: {len(_same127)} name pairs are one codec", not _bad127, _bad127)
check("B127: a true difference is still a difference; an unknown name is not called wrong", mc.codecs_differ(["h264"], ["hevc"]) and mc.codecs_differ(["ac3"], ["aac"])
      and not mc.codecs_differ(["h264"], ["H.264"]) and not mc.codecs_differ(["h264"], ["SomeNewCodec"]) and mc.unknown_codecs(["h264"], ["SomeNewCodec"]) == ["SomeNewCodec"])
check("B127: channel layouts as a count", (mc._norm_numeric("stereo"), mc._norm_numeric("5.1(side)"), mc._norm_numeric("5.1"), mc._norm_numeric("6.1"), mc._norm_numeric("mono"), mc._norm_numeric("7.1"), mc._norm_numeric("6"))
      == (2.0, 6.0, 6.0, 7.0, 1.0, 8.0, 6.0))
_d127 = os.path.join(_TMP, "b127"); os.makedirs(_d127, exist_ok=True)
_n127, _x127 = os.path.join(_d127, "m.nfo"), os.path.join(_d127, "m.xml")
io.open(_n127, "w", encoding="utf-8").write("<movie><title>T</title><fileinfo><streamdetails><video><codec>h264</codec></video><audio><codec>ac3</codec><channels>6</channels></audio></streamdetails></fileinfo></movie>")
io.open(_x127, "w", encoding="utf-8").write("<Title><LocalTitle>T</LocalTitle><VideoCodec>H.264</VideoCodec><MediaInfo><Video><Codec>AVC</Codec></Video><Audio><Codec>AC-3</Codec><Channels>5.1(side)</Channels></Audio></MediaInfo></Title>")
_row127 = dict(mc.row_defaults(), subfolder="T", movie_name="T", nfo_exists=True, xml_exists=True, nfo_path=_n127, xml_path=_x127, nfo_bytes=1, xml_bytes=1,
               poster_exists=False, folder_exists=False, fanart_exists=False, video_path=None, video_width=0, video_height=0)
_row127.update({k: _row127.get(k, 0) for k in ("poster_path", "poster_bytes", "folder_path", "folder_bytes", "fanart_path", "fanart_bytes")})
_res127 = mc.run_improvements([_row127], {"nfo_xml_diff": True, "ffprobe_diff": False, "large_xml": False, "poster_folder": False})
_txt127 = str(_res127)
check("B127: an MCM-style file against a Kodi-style one: no codec or channel finding", "Codec" not in _txt127 and "Channels" not in _txt127 and "Audio Channels" not in _txt127, _txt127[:400])
io.open(_x127, "w", encoding="utf-8").write("<Title><LocalTitle>T</LocalTitle><MediaInfo><Video><Codec>HEVC</Codec></Video></MediaInfo></Title>")
check("B127: a true difference (h264, HEVC) is still a finding", "Video Codec" in str(mc.run_improvements([_row127], {"nfo_xml_diff": True, "ffprobe_diff": False, "large_xml": False, "poster_folder": False})))
# ── v0.19.5 B126: year against premiered ──   ### NEW v0.19.5 B126 ###
_c126 = [0]
def _y126(t):
    _c126[0] += 1; _p = os.path.join(_d127, f"y{_c126[0]}.nfo"); io.open(_p, "w", encoding="utf-8").write(t)
    return mc.year_premiered_diff(_p)
check("B126: year and premiered: different years reported, same year or a missing one not",
      _y126("<movie><year>1999</year><premiered>2000-01-02</premiered></movie>") == "year 1999, premiered 2000" and _y126("<movie><year>2000</year><premiered>2000-01-02</premiered></movie>") == ""
      and _y126("<movie><year>1999</year></movie>") == "" and _y126("<movie><premiered>2000-01-02</premiered></movie>") == "")
_w126 = []; mc._hr_year_premiered({"year_premiered_diff": "year 1999, premiered 2000"}, {"year_premiered_differ": True}, {}, [], _w126)
_w126b = []; mc._hr_year_premiered({"year_premiered_diff": "x"}, {"year_premiered_differ": False}, {}, [], _w126b)
check("B126: the warning follows its rule key", len(_w126) == 1 and "premiered" in _w126[0] and not _w126b and DEFAULT_SETTINGS["health_rules"]["year_premiered_differ"] is True)
# ── v0.19.5 WR-A3: the structure fix touches only direct children of the root ──   ### NEW v0.19.5 ###
_n_a3 = os.path.join(_TMP, "a3.nfo")
io.open(_n_a3, "w", encoding="utf-8", newline="\n").write('<movie>\n  <id>tt0133093/</id>\n  <title>A</title>\n  <title>A</title>\n  <votes>2000</votes>\n  <ratings>\n    <rating name="imdb">\n      <votes>2000</votes>\n    </rating>\n    <rating name="tmdb">\n      <votes>2000</votes>\n    </rating>\n  </ratings>\n  <fileinfo><streamdetails>\n    <audio>\n      <title>Stereo</title>\n    </audio>\n    <audio>\n      <title>Stereo</title>\n    </audio>\n  </streamdetails></fileinfo>\n</movie>\n')
_st_a3 = mc.App._ar_struct_fix(None, {"nfo": _n_a3, "xml": None, "backup": lambda: None})
_t_a3 = io.open(_n_a3, encoding="utf-8").read()
check("WR-A3: a repeated top-level title goes and the ID is cleaned; votes and audio titles inside blocks stay",
      _st_a3[0] == "fixed" and _t_a3.count("<title>A</title>") == 1 and "<id>tt0133093</id>" in _t_a3 and _t_a3.count("<votes>2000</votes>") == 3 and _t_a3.count("<title>Stereo</title>") == 2, _t_a3)
# ── v0.19.5 I37 pack 1: CO-D1, CO-D3, CO-D4, SH-E1 ──   ### NEW v0.19.5 ###
_t_d3 = "<movie>\n  <set />\n  <title>T</title>\n  <plot>P</plot>\n  <set><name>Saga</name></set>\n</movie>\n"
_o_d3 = _cr.replace_set_in_text(_t_d3, "New")
check("CO-D3: <set /> followed by another <set> loses nothing", all(x in _o_d3 for x in ("<title>T</title>", "<plot>P</plot>", "New")), _o_d3)
check("CO-D3: the reader treats <set /> and <set/> alike", _cr.read_set(_t_d3) == _cr.read_set(_t_d3.replace("<set />", "<set/>")))
check("CO-D4: a name of only dots is never an empty folder name", _cr.kodi_legal_name("...") == "_" and _cr.kodi_legal_name(" . ") == "_" and _cr.kodi_legal_name("Saga.") == "Saga")
_rw_d1 = {"coll_nfo": None, "coll_tmdb": {"id": 10, "name": "Star Wars Collection"}, "id_check": {"result": "ID belongs to another film"}}
_cache_d1 = {"10": {"names": {"en": "Star Wars Collection"}}}
_st_d1 = {}
mc.take_collection_data(_st_d1, {"result": mc.ID_OTHER, "coll_tmdb": {"id": 10, "name": "Star Wars Collection"}, "title_langs": [], "tmdb_titles": {}})
_st_d1b = {}
mc.take_collection_data(_st_d1b, {"result": mc.ID_OK, "coll_tmdb": {"id": 10, "name": "Star Wars Collection"}, "title_langs": [], "tmdb_titles": {}})
check("CO-D1: a flagged ID's collection is not kept, not warned about, not written; a good ID's is",
      "coll_tmdb" not in _st_d1 and "coll_tmdb" in _st_d1b and _cr.mismatch_reasons(_rw_d1, _cache_d1) == []
      and _cr.fix_target(_rw_d1, _cache_d1)[0] is None and "flagged" in _cr.fix_target(_rw_d1, _cache_d1)[3]
      and _cr.fix_target(dict(_rw_d1, id_check={"result": mc.ID_OK}), _cache_d1)[0] == "Star Wars Collection")
if sys.platform == "win32":
    import ctypes as _ct_e1
    _d_e1 = os.path.join(_TMP, "e1"); os.makedirs(_d_e1, exist_ok=True)
    _cfg_e1 = os.path.join(_d_e1, "settings.json"); _ocfg_e1 = sc.CONFIG_PATH; sc.CONFIG_PATH = _cfg_e1
    _good_e1 = json.dumps({"tmdb_api_key": "FAKE", "library_folders": ["X:\\Movies"]})
    io.open(_cfg_e1, "w", encoding="utf-8").write(_good_e1)
    _k_e1 = _ct_e1.WinDLL("kernel32"); _k_e1.CreateFileW.restype = _ct_e1.c_void_p
    _h_e1 = _k_e1.CreateFileW(_cfg_e1, 0x80000000, 0, None, 3, 0, None)
    try:
        sc.SETTINGS_LOAD_PROBLEM.update(error="", corrupt_copy=None)
        _s_e1 = sc.load_settings()
    finally:
        _k_e1.CloseHandle(_ct_e1.c_void_p(_h_e1))
    _saved_e1 = sc.save_settings(_s_e1)
    check("SH-E1: a settings file held at the start is not replaced by defaults when the app saves",
          sc.SETTINGS_SAVE_BLOCKED[0] and _saved_e1 is False and io.open(_cfg_e1, encoding="utf-8").read() == _good_e1, (_saved_e1, sc.SETTINGS_SAVE_BLOCKED))
    sc.SETTINGS_SAVE_BLOCKED[0] = False; sc.SETTINGS_LOAD_PROBLEM.update(error="", corrupt_copy=None); sc.CONFIG_PATH = _ocfg_e1

# ── v0.19.5 I29: docs/help match the app's Help ──   ### NEW v0.19.5 ###
_tools_i29 = os.path.join(_APP_DIR, "tools")
if os.path.isfile(os.path.join(_tools_i29, "make_help_docs.py")):
    sys.path.insert(0, _tools_i29)
    import make_help_docs as _mh_i29
    sys.path.remove(_tools_i29)
    _bad_i29 = _mh_i29.check_pages(os.path.join(_APP_DIR, "docs", "help"))
    check("I29: docs/help match the app's Help (run tools/make_help_docs.py after changing the Help)", not _bad_i29, _bad_i29)
check("AS-A22: the sort text does not say 'empty values last' when a level asks for empty first", "empty values last" not in mc._se.describe([{"key": "rating", "dir": "low", "empty": "first"}]) and "empty values last" in mc._se.describe([{"key": "rating", "dir": "low"}]))
# ── v0.19.5 CO-D2: your own collection ──   ### NEW v0.19.5 ###
_own_d2 = {"coll_nfo": {"name": "Oscar winners", "tmdbcolid": None}, "coll_tmdb": {"id": 10, "name": "Star Wars Collection"}}
_cc_d2 = {"10": {"names": {"en": "Star Wars Collection"}}}
check("CO-D2: a name with no TMDB ID that matches no TMDB name is yours: no warning, no automatic write", _cr.mismatch_reasons(_own_d2, _cc_d2) == [] and _cr.fix_target(_own_d2, _cc_d2)[0] is None
      and "your own" in _cr.fix_target(_own_d2, _cc_d2)[3])
check("CO-D2: an explicit Fix can still write TMDB's name; a same name without an ID, or another ID, is not 'yours'", _cr.fix_target(_own_d2, _cc_d2, explicit=True)[0] == "Star Wars Collection"
      and _cr.mismatch_reasons(dict(_own_d2, coll_nfo={"name": "Oscar winners", "tmdbcolid": 7}), _cc_d2) != [])
# ── v0.19.5 I37 pack 3 ──   ### NEW v0.19.5 ###
check("CO-D6: parts of a saga are not a match; the same part is", not mc._titles_match(["Kill Bill: Vol. 2"], ["Kill Bill: Vol. 1"])[0]
      and not mc._titles_match(["Rocky II"], ["Rocky III"])[0] and mc._titles_match(["Kill Bill: Vol. 1"], ["Kill Bill Vol. 1"])[0] and mc._titles_match(["The Matrixx"], ["The Matrix"])[0])
_d_p3 = os.path.join(_TMP, "pack3"); os.makedirs(_d_p3, exist_ok=True)
def _np3(name, t):
    p = os.path.join(_d_p3, name); io.open(p, "w", encoding="utf-8").write(t); return p
_v8 = mc.verify_movie_ids({"nfo_path": _np3("d8.nfo", "<movie><title>X</title><tmdbid>60 3</tmdbid></movie>"), "xml_path": None, "nfo_exists": True, "xml_exists": False, "movie_name": "X", "subfolder": "X"}, "k")
check("CO-D8: an odd ID is this movie's result, no request and no exception", _v8["result"] == mc.ID_NOT_FOUND and "valid" in _v8["detail"], _v8)
import urllib.error as _ue_d13
_e_d13 = _ue_d13.HTTPError("http://x", 404, "nf", {}, io.BytesIO(b"null"))
check("CO-D13: an HTTP error body that is not an object", mc._http_error_body(_e_d13) == {})
_u_d7 = {}
def _fetch_d7(url, *a, **k):
    _u_d7[url.split("?")[0]] = 1
    if "/find/" in url:
        return {"movie_results": [{"id": 238, "title": "The Godfather", "original_title": "The Godfather", "release_date": "1972-03-14"}]}
    return {"id": 238, "title": "The Godfather", "original_title": "The Godfather", "release_date": "1972-03-14", "external_ids": {"imdb_id": "tt0068646"},
            "translations": {"translations": [{"iso_639_1": "pt", "data": {"title": "O Poderoso Chefão"}}]}, "alternative_titles": {"titles": []}}
_v7 = mc.verify_movie_ids({"nfo_path": _np3("d7.nfo", "<movie><title>O Poderoso Chefão</title><year>1972</year><imdbid>tt0068646</imdbid></movie>"), "xml_path": None, "nfo_exists": True, "xml_exists": False,
                           "movie_name": "O Poderoso Chefão", "movie_year": "1972", "subfolder": "X", "nfo_title": "O Poderoso Chefão"}, "k", "en-US", _fetch_d7)
check("CO-D7: a local title with only an IMDb ID is checked against the translations", _v7["result"] == mc.ID_OK, _v7)
check("AS-A10: Brazilian and modern codes", all(mc.is_target_lang(x, "PT") for x in ("pob", "pb", "ptb", "Português", "Brazilian", "Portuguese (Brazil)")) and mc.is_target_lang("cmn", "ZH") and mc.is_target_lang("yue", "ZH")
      and mc.lang_same("pob", "por") and mc.lang_same("esp", "spa") and not mc.is_target_lang("eng", "PT"))
_e_d5 = _cr.coll_cache_entry({"name": "Coleção BR", "overview": "Sobre BR"}, {"translations": [{"iso_639_1": "pt", "data": {"title": "Saga PT", "overview": "Sobre PT"}}, {"iso_639_1": "en", "data": {"title": "Saga"}}]}, "pt-BR", 1)
check("CO-D5: the answer asked for in the library's language wins for it", _e_d5["names"]["pt"] == "Coleção BR" and _e_d5["overviews"]["pt"] == "Sobre BR" and _e_d5["names"]["en"] == "Saga", _e_d5)
_png_i10 = io.BytesIO()
from PIL import Image as _Im_i10
_Im_i10.new("RGB", (40, 60), (1, 2, 3)).save(_png_i10, "PNG")
_de_i10 = os.path.join(_d_p3, "poster.jpg")
mc.write_image_atomic(_de_i10, _png_i10.getvalue())
_t_i10 = io.BytesIO(); _Im_i10.new("RGB", (40, 60), (1, 2, 3)).save(_t_i10, "TIFF")
_de2_i10 = os.path.join(_d_p3, "fanart.jpg"); _Im_i10.new("RGB", (40, 60)).save(_de2_i10, "JPEG"); _b2_i10 = open(_de2_i10, "rb").read()
try:
    mc.write_image_atomic(_de2_i10, _t_i10.getvalue()); _tiff_i10 = False
except mc.NotAnImageError:
    _tiff_i10 = True
check("IM-10: a PNG for a .jpg is stored as JPEG; a format the app does not read leaves the old file", mc.detect_image_format(_de_i10) == "JPEG" and _tiff_i10 and open(_de2_i10, "rb").read() == _b2_i10
      and not [n for n in os.listdir(_d_p3) if ".mctmp" in n], (mc.detect_image_format(_de_i10), _tiff_i10))
# ── v0.19.5 I37 pack 2 ──   ### NEW v0.19.5 ###
_d_p2 = os.path.join(_TMP, "pack2"); os.makedirs(_d_p2, exist_ok=True)
if sys.platform == "win32":
    _f_b1 = os.path.join(_d_p2, "b1.nfo"); io.open(_f_b1, "w", encoding="utf-8").write("<movie/>")
    def _hold_b1(sec):
        f = open(_f_b1, "rb"); time.sleep(sec); f.close()
    _th_b1 = threading.Thread(target=_hold_b1, args=(0.3,), daemon=True); _th_b1.start(); time.sleep(0.05)
    mc._atomic_write_text(_f_b1, "<movie><a/></movie>"); _th_b1.join()
    check("WR-B1: an NFO write waits for a short read by another program", io.open(_f_b1, encoding="utf-8").read() == "<movie><a/></movie>")
    _th_b1 = threading.Thread(target=_hold_b1, args=(1.5,), daemon=True); _th_b1.start(); time.sleep(0.05)
    _e_b1 = ""
    try:
        mc._atomic_write_text(_f_b1, "<movie><b/></movie>")
    except OSError as _x_b1:
        _e_b1 = str(_x_b1)
    _th_b1.join()
    check("WR-B1: held longer: the old file stays, no temp file, and the message says what to do", "run the action again" in _e_b1 and "<a/>" in io.open(_f_b1, encoding="utf-8").read() and not os.path.exists(_f_b1 + ".mctmp"), _e_b1)
_rx_a8 = {"subfolder_path": os.path.join(_d_p2, "gone"), "subfolder": "gone", "video_width": 1920, "audio_tracks": [{"language": "POR"}]}
_ofl_a8 = mc._FolderListing
class _BadList_a8:
    error = "Access is denied"
    def __init__(self, *a, **k): pass
mc._FolderListing = _BadList_a8
try:
    _r_a8, _k_a8 = mc.rescan_or_keep(_rx_a8, use_ffprobe=False)
finally:
    mc._FolderListing = _ofl_a8
check("AS-A8: a folder that cannot be read for a moment keeps its row and its FFprobe data, marked", _k_a8 and _r_a8["read_error"] == "Access is denied" and _r_a8["video_width"] == 1920 and _r_a8["audio_tracks"], _r_a8)

# ── v0.19.2 B39: every value written into NFO/XML is escaped exactly once ─────   ### NEW v0.19.2 B39 ###
section("2ze. values with & < > are escaped when written (v0.19.2 B39)")
import xml.etree.ElementTree as _ET39
_x39 = os.path.join(_d37, "esc.xml"); _n39 = os.path.join(_d37, "esc.nfo")
with open(_x39, "w", encoding="utf-8") as f:
    f.write("<Title>\n  <LocalTitle>Old</LocalTitle>\n  <Overview>Tom &amp; Jerry</Overview>\n</Title>\n")
with open(_n39, "w", encoding="utf-8") as f:
    f.write("<movie>\n  <title>Old</title>\n  <plot>Tom &amp; Jerry</plot>\n  <genre>Drama</genre>\n</movie>\n")
_w39 = (mc._write_tag_in_files(_n39, _x39, "title", "LocalTitle", "Fast & Furious <2>"),
        mc.write_genres_to_nfo(_n39, ["Rock & Roll", "Drama"]), mc.write_genres_to_xml(_x39, ["Rock & Roll"]))
def _parses39(p):
    try:
        _ET39.parse(p); return True
    except Exception:
        return False
_tn39, _tx39 = open(_n39, encoding="utf-8").read(), open(_x39, encoding="utf-8").read()
check("B39: after writing 'Fast & Furious <2>' and 'Rock & Roll' both files parse (strict XML)", all(ok for ok, _e in _w39) and _parses39(_n39) and _parses39(_x39), (_w39, _tn39, _tx39))
check("B39: the values read back unchanged (escaped once, not twice)",
      mc.get_primary_titles(_n39, _x39)[0] == "Fast & Furious <2>" and mc.get_genres_from_nfo(_n39)[0] == "Rock & Roll"
      and mc.get_genres_from_xml(_x39) == ["Rock & Roll"] and "&amp;amp;" not in _tn39 + _tx39, (mc.get_primary_titles(_n39, _x39), mc.get_genres_from_nfo(_n39), mc.get_genres_from_xml(_x39)))
check("B39: an existing '&amp;' elsewhere in the file stays '&amp;'", "Tom &amp; Jerry" in _tn39 and "Tom &amp; Jerry" in _tx39)

# ── v0.19.2 B40: a failed backup stops the change ─────────────────────────────   ### NEW v0.19.2 B40 ###
section("2zf. a failed backup stops the change (v0.19.2 B40)")
_d40 = os.path.join(_TMP, "b40lib"); os.makedirs(_d40, exist_ok=True)
_blocker40 = os.path.join(_TMP, "b40_not_a_folder.txt")
with open(_blocker40, "w") as f:
    f.write("x")
_BAD_ROOT40 = os.path.join(_blocker40, "backup")             # its parent is a file → every backup fails
_LIB_SAVE40, LIB = LIB, _d40
try:
    _mv40 = make_movie("B40 Movie", nfo_genres=("Family/Fantasy", "Sci-Fi"), xml_genres=("Family/Fantasy", "Sci-Fi"), video=False, backdrops=1)
finally:
    LIB = _LIB_SAVE40
_jpeg(os.path.join(_mv40, "poster.jpg"), 1000, 1500, noisy=False)   # poster ≠ folder.jpg now
_files40 = [os.path.join(_mv40, n) for n in ("B40 Movie.nfo", "movie.xml", "folder.jpg")]
_snap40 = {p: open(p, "rb").read() for p in _files40}
def _unchanged40():
    return all(open(p, "rb").read() == b for p, b in _snap40.items())
_orig_root40 = mc._BACKUP_ROOT
mc._BACKUP_ROOT = _BAD_ROOT40
try:
    check("B40: _backup_ok / _batch_backup_ok are False when the copy fails", mc._backup_ok("B40", _files40[0]) is False and mc._batch_backup_ok("B40", [None], _files40[0]) is False)
    check("B40: … and True when there is nothing to back up", mc._backup_ok("B40", os.path.join(_mv40, "nope.nfo")) is True and mc._batch_backup_ok("B40", [None], None) is True)
    _e40 = mc.write_rating_to_files(_files40[0], _files40[1], "9.9", "5", movie_name="B40 Movie")
    check("B40: Sync Ratings with a failing backup writes nothing and says so", _e40 == [mc.BACKUP_FAILED_TEXT] and _unchanged40(), _e40)
finally:
    mc._BACKUP_ROOT = _orig_root40

# ── v0.19.2 B28: one FFmpeg runner — timeout, cancel, priority, budgets ──────   ### NEW v0.19.2 B28 ###
section("2zg. FFmpeg runner: never hang, background priority (v0.19.2 B28)")
_SLEEPER28 = os.path.join(_TMP, "fake_ffmpeg_sleep.py")
with open(_SLEEPER28, "w", encoding="utf-8") as f:
    f.write("import sys, time\ntime.sleep(float(sys.argv[1]))\n")
def _wait28(cond, timeout=10):
    t = time.monotonic()
    while not cond() and time.monotonic() - t < timeout:
        time.sleep(0.05)
    return cond()
def _sleep_cmd28(sec):
    return [sys.executable, _SLEEPER28, str(sec)]
def _in_thread28(fn):
    box = {}
    def _r():
        box["t0"] = time.monotonic(); box["r"] = fn(); box["t1"] = time.monotonic()
    th = threading.Thread(target=_r, daemon=True); th.start()
    return th, box
_t0 = time.monotonic()
_r28 = mc._run_ffmpeg(_sleep_cmd28(30), timeout=1)
check("B28: the per-frame timeout kills FFmpeg (status 'timeout', about 1 s, no process left)", _r28[0] == mc.FF_TIMEOUT and time.monotonic() - _t0 < 3 and not mc._FF_PROCS, (_r28[0], round(time.monotonic() - _t0, 2)))
_flag28 = {"c": False}
_th28, _bx28 = _in_thread28(lambda: mc._run_ffmpeg(_sleep_cmd28(30), timeout=60, cancel=lambda: _flag28["c"]))
_wait28(lambda: bool(mc._FF_PROCS), 10)
_prio28 = None
if os.name == "nt" and mc._FF_PROCS:
    import ctypes as _ct28
    _pid28 = next(iter(mc._FF_PROCS)).pid
    _h28 = _ct28.windll.kernel32.OpenProcess(0x1000, False, _pid28)      # PROCESS_QUERY_LIMITED_INFORMATION
    _prio28 = _ct28.windll.kernel32.GetPriorityClass(_h28); _ct28.windll.kernel32.CloseHandle(_h28)
    check("B28: FFmpeg runs at background priority (BELOW_NORMAL_PRIORITY_CLASS) without a window", _prio28 == 0x4000 and mc._FF_CFLAGS & 0x08000000, hex(_prio28 or 0))
_tc28 = time.monotonic(); _flag28["c"] = True; _th28.join(5)
check("B28: cancel stops the run within 0.5 s (status 'cancelled', process gone)", _bx28.get("r", ("",))[0] == mc.FF_CANCELLED and _bx28["t1"] - _tc28 < 0.5 and not mc._FF_PROCS, (_bx28.get("r", ("",))[0], round(_bx28.get("t1", 99) - _tc28, 2)))
_th28b, _bx28b = _in_thread28(lambda: mc._run_ffmpeg(_sleep_cmd28(30), timeout=60))
_wait28(lambda: bool(mc._FF_PROCS), 10)
_nk28 = mc.kill_all_ffmpeg(); _th28b.join(5)
check("B28: kill_all_ffmpeg (app close / exit) kills every running FFmpeg", _nk28 == 1 and "r" in _bx28b and not mc._FF_PROCS, (_nk28, _bx28b.get("r", ("",))[0]))
# the commands: 2 threads, no audio/subtitles/data, key frames for the grid, exact frame as fallback
_cmds28 = []
_orig_run28 = mc._run_ffmpeg
mc._run_ffmpeg = lambda cmd, timeout=None, cancel=None: (_cmds28.append(cmd) or (mc.FF_OK, 0, "", ""))
try:
    mc.extract_single_frame(SAMPLE_VIDEO or "x.mkv", "1.000", os.path.join(_TMP, "b28_none.jpg"), timeout_sec=20, keyframes=True)
finally:
    mc._run_ffmpeg = _orig_run28
check("B28: the frame-grid command uses -threads 2, -an -sn -dn, -nostdin and '-skip_frame nokey' before -i",
      len(_cmds28) == 2 and all(x in _cmds28[0] for x in ("-threads", "2", "-an", "-sn", "-dn", "-nostdin", "-skip_frame", "nokey"))
      and _cmds28[0].index("-skip_frame") < _cmds28[0].index("-i"), _cmds28[:1])
check("B28: …and falls back to the exact frame when no key frame came out (short clips)", len(_cmds28) == 2 and "-skip_frame" not in _cmds28[1] and "-threads" in _cmds28[1], _cmds28[1:])
# breaker and budget (fake runner / fake duration)
_orig_dur28 = mc.get_video_duration
mc.get_video_duration = lambda v, cancel=None: (3600.0, False)
_calls28 = []
mc._run_ffmpeg = lambda cmd, timeout=None, cancel=None: (_calls28.append(timeout) or (mc.FF_TIMEOUT, -1, "", ""))
_st28 = {}
try:
    _e28, _m28 = mc.extract_movie_frames("slow.mkv", os.path.join(_TMP, "b28_slow"), n=10, state=_st28, frame_timeout=7)
finally:
    mc._run_ffmpeg = _orig_run28
check("B28: 2 timeouts in a row stop the run with the 'very slow to read' message", _e28 == [] and str(_m28).startswith("This video is very slow to read") and len(_calls28) == 2 and set(_calls28) == {7}, (_m28, _calls28))
check("B28: the spinner state shows frame 2 / 10 and is inactive at the end", _st28.get("n") == 10 and _st28.get("i") == 2 and _st28.get("active") is False, _st28)
def _slow_ok28(cmd, timeout=None, cancel=None):
    time.sleep(0.3); shutil.copy2(_ns11, cmd[-1]); return mc.FF_OK, 0, "", ""
mc._run_ffmpeg = _slow_ok28
try:
    _e28b, _m28b = mc.extract_movie_frames("slow.mkv", os.path.join(_TMP, "b28_budget"), n=10, run_budget=0.5)
finally:
    mc._run_ffmpeg = _orig_run28
    mc.get_video_duration = _orig_dur28
check("B28: the run budget stops the run and keeps the frames already extracted", 1 <= len(_e28b) <= 3 and str(_m28b).startswith("Stopped after 0:00 (time limit"), (len(_e28b), _m28b))
check("B28: defaults 20 s per frame / 180 s per run", mc._ff_frame_timeout() == 20 and mc._ff_run_budget() == 180)

# ── v0.19.2 B35: folder rules OFF by default + one-time migration ─────────────   ### NEW v0.19.2 B35 ###
section("2zi. folder rules off by default; one-time switch-off (v0.19.2 B35)")
check("B35: 'Missing folder image' and 'Poster and folder image are different' are OFF by default (keys unchanged)",
      DEFAULT_SETTINGS["health_rules"]["missing_folder"] is False and DEFAULT_SETTINGS["health_rules"]["poster_folder_identical"] is False
      and DEFAULT_SETTINGS.get("settings_migrations") == [])
_d35 = os.path.join(_TMP, "b35", "Poster Only"); os.makedirs(_d35, exist_ok=True)
io.open(os.path.join(_d35, "Poster Only.nfo"), "w", encoding="utf-8").write("<movie>\n  <title>Poster Only</title>\n</movie>\n")
_jpeg(os.path.join(_d35, "poster.jpg"), 1000, 1500, noisy=True)
_r35 = mc.scan_one_subfolder(_d35, "Poster Only", use_ffprobe=False)
_def35 = dict(DEFAULT_SETTINGS["health_rules"])
_h35 = dict(_r35); mc._apply_health(_h35, _def35, mc.SETTINGS)
_h35on = dict(_r35); mc._apply_health(_h35on, dict(_def35, missing_folder=True), mc.SETTINGS)
check("B35: default rules → a poster-only movie gets no 'Missing folder image'; rule ON → it does",
      "Missing folder image" not in _h35["health_reasons"] and "Missing folder image" in _h35on["health_reasons"], (_h35["health_reasons"], _h35on["health_reasons"]))
_jpeg(os.path.join(_d35, "folder.jpg"), 600, 900, noisy=True)
_r35b = mc.scan_one_subfolder(_d35, "Poster Only", use_ffprobe=False)
_h35b = dict(_r35b); mc._apply_health(_h35b, _def35, mc.SETTINGS)
_h35bon = dict(_r35b); mc._apply_health(_h35bon, dict(_def35, poster_folder_identical=True), mc.SETTINGS)
check("B35: default rules → poster ≠ folder gives no warning; rule ON → 'Poster and folder image are different'",
      not any("Poster and folder image are different" in x for x in _h35b["health_reasons"])
      and any("Poster and folder image are different" in x for x in _h35bon["health_reasons"]), (_h35b["health_reasons"], _h35bon["health_reasons"]))
_cfg35 = os.path.join(_TMP, "b35_settings.json")
_orig_cfg35 = sc.CONFIG_PATH
_notes35 = list(sc.SETTINGS_MIGRATION_NOTICES)
sc.CONFIG_PATH = _cfg35
try:
    def _seed35(d):
        with open(_cfg35, "w", encoding="utf-8") as f:
            json.dump(d, f)
    del sc.SETTINGS_MIGRATION_NOTICES[:]
    _seed35({"health_rules": {"missing_folder": True, "poster_folder_identical": True}})
    _s35 = sc.load_settings(); _disk35 = json.load(open(_cfg35, encoding="utf-8"))
    check("B35: an existing user with both rules ON → both OFF, marker saved, one notice",
          _s35["health_rules"]["missing_folder"] is False and _s35["health_rules"]["poster_folder_identical"] is False
          and "b35_folder_rules_off" in _disk35.get("settings_migrations", []) and _disk35["health_rules"]["missing_folder"] is False
          and len(sc.SETTINGS_MIGRATION_NOTICES) == 1, (_disk35.get("settings_migrations"), sc.SETTINGS_MIGRATION_NOTICES))
    del sc.SETTINGS_MIGRATION_NOTICES[:]
    _disk35["health_rules"]["missing_folder"] = True                 # the user turns it on again later
    _seed35(_disk35)
    _s35b = sc.load_settings()
    check("B35: second start → the migration never runs again; a rule turned ON later stays ON, no notice",
          _s35b["health_rules"]["missing_folder"] is True and not sc.SETTINGS_MIGRATION_NOTICES, sc.SETTINGS_MIGRATION_NOTICES)
    _seed35({"health_rules": {"missing_folder": False, "poster_folder_identical": False}})
    _s35c = sc.load_settings()
    check("B35: both rules already OFF → marker set, no notice", not sc.SETTINGS_MIGRATION_NOTICES and "b35_folder_rules_off" in _s35c["settings_migrations"])
    os.remove(_cfg35)
    _s35d = sc.load_settings()
    check("B35: first start (no settings.json) → nothing to migrate, no notice, nothing written", not sc.SETTINGS_MIGRATION_NOTICES and not os.path.exists(_cfg35) and "b35_folder_rules_off" in _s35d["settings_migrations"])
finally:
    sc.CONFIG_PATH = _orig_cfg35
    sc.SETTINGS_MIGRATION_NOTICES[:] = _notes35

# ── v0.19.2 B55: every library shown (pure texts + one-time filter reset) ─────   ### NEW v0.19.2 B55 ###
section("2zj. every library shown (v0.19.2 B55)")
_A55, _B55 = r"Z:\Filmes_Espiritualistas", r"Z:\Filmes_Kids"
_rows55 = [{"subfolder": f"a{i}", "subfolder_path": _A55 + f"\\a{i}", "library_root": _A55} for i in range(3)] + \
          [{"subfolder": f"b{i}", "subfolder_path": _B55 + f"\\b{i}", "library_root": _B55} for i in range(2)]
_ov55 = mc.library_overview([_A55, _B55], _A55, _rows55)
check("B55: folder box lists both libraries, ▶ on the filtered one, 'showing 1 of 2 (filter)'",
      _ov55["box"] == f"Libraries (2):  ▶ {_A55}   ·   {_B55}   — showing 1 of 2 (filter)", _ov55["box"])
if sys.platform == "win32": check("B55: dropdown 'All libraries (5)' + each library with its count; per-library counts; 1 hidden",
      [d for d, _p in _ov55["choices"]] == ["All libraries (5)", f"{_A55} (3)", f"{_B55} (2)"]
      and _ov55["per_lib"] == "Filmes_Espiritualistas 3  ·  Filmes_Kids 2" and _ov55["hidden"] == 1, _ov55)
check("B55: no filter → no 'showing' note, nothing hidden; one library → just its path",
      "showing" not in mc.library_overview([_A55, _B55], "", _rows55)["box"] and mc.library_overview([_A55, _B55], "", _rows55)["hidden"] == 0
      and mc.library_overview([_A55], "", _rows55)["box"] == _A55)
check("B55: the tooltip lists every library with its count (offline marked)",
      mc.library_overview([_A55, _B55], "", _rows55, offline=[_B55])["tooltip"].startswith(f"{_A55}  —  3 movies\n{_B55}  —  2 movies  (offline, last scan kept)"))
check("B55: the scan summary names every library, offline ones too",
      mc.library_scan_summary("Full Scan", [_A55, _B55], _rows55, offline=[_B55]) == f"Full Scan: 2 libraries — {_A55} 3 · {_B55} 2 (offline, last scan kept)"
      and mc.library_scan_summary("Full Scan", [_A55], _rows55) == "Full Scan complete")
_cfg55 = os.path.join(_TMP, "b55_settings.json")
_orig_cfg55 = sc.CONFIG_PATH
_st55 = list(sc.SETTINGS_MIGRATION_STATUS); _nt55 = list(sc.SETTINGS_MIGRATION_NOTICES)
sc.CONFIG_PATH = _cfg55
try:
    del sc.SETTINGS_MIGRATION_STATUS[:]
    json.dump({"library_folders": [_A55, _B55], "library_filter": _A55}, open(_cfg55, "w", encoding="utf-8"))
    _m55 = sc.load_settings()
    check("B55: a filter saved by v0.19.1 with 2 libraries is reset once; the status bar says so",
          _m55["library_filter"] == "" and sc.SETTINGS_MIGRATION_STATUS == [sc.B55_STATUS]
          and "b55_library_filter_reset" in json.load(open(_cfg55, encoding="utf-8"))["settings_migrations"], (_m55["library_filter"], sc.SETTINGS_MIGRATION_STATUS))
    del sc.SETTINGS_MIGRATION_STATUS[:]
    _d55 = json.load(open(_cfg55, encoding="utf-8")); _d55["library_filter"] = _B55
    json.dump(_d55, open(_cfg55, "w", encoding="utf-8"))
    check("B55: …and never again: a filter chosen later stays", sc.load_settings()["library_filter"] == _B55 and not sc.SETTINGS_MIGRATION_STATUS)
    json.dump({"library_folders": [_A55], "library_filter": _A55}, open(_cfg55, "w", encoding="utf-8"))
    check("B55: one library only → nothing to reset", sc.load_settings()["library_filter"] == _A55 and not sc.SETTINGS_MIGRATION_STATUS)
finally:
    sc.CONFIG_PATH = _orig_cfg55
    sc.SETTINGS_MIGRATION_STATUS[:] = _st55; sc.SETTINGS_MIGRATION_NOTICES[:] = _nt55

# ── v0.19.2 B58: FFmpeg / FFprobe found like the other apps ───────────────────   ### NEW v0.19.2 B58 ###
section("2zk. FFmpeg finder: Settings, PATH, registry PATH, known folders, scan (v0.19.2 B58)")
_r58 = os.path.join(_TMP, "b58")
def _mkff58(folder, probe=True):
    os.makedirs(folder, exist_ok=True)
    for n in (("ffmpeg.exe", "ffprobe.exe") if probe else ("ffmpeg.exe",)):
        open(os.path.join(folder, n), "wb").write(b"MZ")
    return folder
_A58 = _mkff58(os.path.join(_r58, "custom", "bin")); _B58 = _mkff58(os.path.join(_r58, "which"))
_C58 = _mkff58(os.path.join(_r58, "registry")); _D58 = _mkff58(os.path.join(_r58, "known", "ffmpeg-7.1", "bin"))
_E58 = _mkff58(os.path.join(_r58, "deep", "a", "b", "bin")); _H58 = _mkff58(os.path.join(_r58, "half"), probe=False)
_ok58 = {os.path.normcase(os.path.join(d, n)) for d in (_A58, _B58, _C58, _D58, _E58, _H58) for n in ("ffmpeg.exe", "ffprobe.exe")}
_orig58 = (sc.ff_works, sc.shutil.which, sc.live_path_dirs, list(sc.FFMPEG_GLOBS_WIN), list(sc.FFMPEG_DEEP_ROOTS_WIN))
sc.ff_works = lambda p: os.path.normcase(p) in _ok58 and os.path.isfile(p)
try:
    sc.shutil.which = lambda n: None; sc.live_path_dirs = lambda: []
    sc.FFMPEG_GLOBS_WIN[:] = []; sc.FFMPEG_DEEP_ROOTS_WIN[:] = []
    _f1 = sc.find_ffmpeg_ffprobe(os.path.join(_r58, "custom")); _h1 = dict(sc.FFMPEG_FOUND)
    _f1b = sc.find_ffmpeg_ffprobe(os.path.join(_A58, "ffmpeg.exe"))
    if sys.platform == "win32": check("B58: the Settings folder (or its bin\\, or the exe itself) comes first", _f1[0] == os.path.join(_A58, "ffmpeg.exe") and _f1[1] == os.path.join(_A58, "ffprobe.exe")
          and _h1 == {"how": "Settings folder", "dir": _A58} and _f1b[0] == os.path.join(_A58, "ffmpeg.exe"), (_f1, _h1, _f1b))
    sc.shutil.which = lambda n: os.path.join(_B58, "ffmpeg.exe")
    if sys.platform == "win32": check("B58: then the PATH of the process (shutil.which)", sc.find_ffmpeg_ffprobe("")[0] == os.path.join(_B58, "ffmpeg.exe") and sc.FFMPEG_FOUND["how"] == "PATH")
    sc.shutil.which = lambda n: None
    sc.live_path_dirs = lambda: [_H58, _C58]
    if sys.platform == "win32": check("B58: then the PATH read live from the registry; a folder with ffmpeg but no ffprobe is skipped",
          sc.find_ffmpeg_ffprobe("")[0] == os.path.join(_C58, "ffmpeg.exe") and sc.FFMPEG_FOUND == {"how": "PATH (registry)", "dir": _C58}, sc.FFMPEG_FOUND)
    sc.live_path_dirs = lambda: []
    sc.FFMPEG_GLOBS_WIN[:] = [os.path.join(_r58, "known", "ffmpeg*", "bin", "ffmpeg.exe")]
    if sys.platform == "win32": check("B58: then the known install folders (winget, scoop, C:\\ffmpeg*, Downloads…)", sc.find_ffmpeg_ffprobe("")[0] == os.path.join(_D58, "ffmpeg.exe") and sc.FFMPEG_FOUND["how"] == "known install folder")
    sc.FFMPEG_GLOBS_WIN[:] = []
    sc.FFMPEG_DEEP_ROOTS_WIN[:] = [os.path.join(_r58, "deep")]
    _nf58 = sc.find_ffmpeg_ffprobe(""); _hn58 = dict(sc.FFMPEG_FOUND)
    _dp58 = sc.find_ffmpeg_ffprobe("", deep=True)
    if sys.platform == "win32": check("B58: nothing found → (None, None) 'not found'; 'Search again' (deep) scans the folders", _nf58 == (None, None) and _hn58["how"] == "not found"
          and _dp58[0] == os.path.join(_E58, "ffmpeg.exe") and sc.FFMPEG_FOUND["how"] == "found by scan", (_nf58, _hn58, _dp58))
finally:
    sc.ff_works, sc.shutil.which, sc.live_path_dirs = _orig58[0], _orig58[1], _orig58[2]
    sc.FFMPEG_GLOBS_WIN[:] = _orig58[3]; sc.FFMPEG_DEEP_ROOTS_WIN[:] = _orig58[4]
_runs58 = []
_orig_run58 = sc.subprocess.run
sc.subprocess.run = lambda *a, **k: (_runs58.append(a[0]) or type("R", (), {"returncode": 0, "stdout": b"ffmpeg version 7.1 Copyright", "stderr": b""})())
try:
    sc.forget_ffmpeg_cache()
    _w58 = (sc.ff_works(os.path.join(_A58, "ffmpeg.exe")), sc.ff_works(os.path.join(_A58, "ffmpeg.exe")))
finally:
    sc.subprocess.run = _orig_run58
    sc.forget_ffmpeg_cache()
if sys.platform == "win32": check("B58: every candidate must run '-version'; the answer is cached (one run per file)", _w58 == (True, True) and len(_runs58) == 1 and "-version" in _runs58[0], _runs58)
if sys.platform == "win32": check("B58: the registry PATH reader returns folders (this PC: the real PATH, read only)", isinstance(sc.live_path_dirs(), list))

# ── v0.19.2 B59: single instance ───────────────────────────────────────────────   ### NEW v0.19.2 B59 ###
section("2zl. single instance (v0.19.2 B59)")
_name59 = f"Local\\MediaClinic.SelfTest.{os.getpid()}"            # never the real app's mutex
_h59a, _f59a = mc.acquire_single_instance(_name59)
_h59b, _f59b = mc.acquire_single_instance(_name59)
mc.release_single_instance(_h59a)
_h59c, _f59c = mc.acquire_single_instance(_name59)
mc.release_single_instance(_h59c)
if sys.platform == "win32": check("B59: first start owns the mutex; a second start sees it; after the first closes the lock is gone",
      _f59a is True and _h59a and _f59b is False and _h59b is None and _f59c is True, (_f59a, _f59b, _f59c))
_title59 = f"MC-SelfTest-B59-{os.getpid()}"
_p59 = subprocess.Popen([sys.executable, "-c", "import tkinter as t, sys; r=t.Tk(); r.title(sys.argv[1]); r.geometry('200x80+60+60'); r.after(20000, r.destroy); r.mainloop()", _title59],
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
try:
    _t59 = time.time(); _fw59 = False
    while time.time() - _t59 < 10 and not _fw59:
        time.sleep(0.3); _fw59 = mc.bring_running_window_forward(title_start=_title59)
    if sys.platform == "win32": check("B59: a second start finds the running window (other process) and brings it forward", _fw59)
    _own59 = tk.Tk(); _own59.title(f"MC-SelfTest-Own-{os.getpid()}"); _own59.update()
    try:
        _ownres59 = mc.bring_running_window_forward(title_start=f"MC-SelfTest-Own-{os.getpid()}")
    finally:
        _own59.destroy()
    check("B59: …but never a window of its own process; no window → False",
          _ownres59 is False and mc.bring_running_window_forward(title_start=f"Nothing-{os.getpid()}") is False)
finally:
    _p59.kill(); _p59.wait(5)
_src59 = io.open(mc.__file__, encoding="utf-8").read()
check("B59: the start checks the mutex before the App is created", _src59.index("_si_handle, _si_first = acquire_single_instance()") < _src59.rindex("app = App()"))

# ── v0.19.2 B33: unescaped & in an NFO = warning + Auto Repair fix ────────────   ### NEW v0.19.2 B33 ###
section("2zh. unescaped '&' in an NFO (v0.19.2 B33)")
_src33 = "Tom & Jerry &amp; &#38; &#x26; &eacute;t&eacute; &foo; <!-- a & b --> <![CDATA[x & y]]> R&D"
_new33, _n33 = mc.fix_unescaped_amp(_src33)
check("B33: '&' → '&amp;'; '&amp;' / '&#38;' / '&#x26;' kept; '&eacute;' → 'é'; comments and CDATA untouched",
      _new33 == "Tom &amp; Jerry &amp; &#38; &#x26; été &amp;foo; <!-- a & b --> <![CDATA[x & y]]> R&amp;D" and _n33 == 5, (_new33, _n33))
_d33 = os.path.join(_TMP, "b33", "Amp Movie"); os.makedirs(_d33, exist_ok=True)
io.open(os.path.join(_d33, "Amp Movie.nfo"), "w", encoding="utf-8").write(
    "<movie>\n  <title>Amp Movie</title>\n  <plot>Fast & Furious, Tom &amp; Jerry</plot>\n  <year>2001</year>\n</movie>\n")
_r33 = mc.scan_one_subfolder(_d33, "Amp Movie", use_ffprobe=False)
_amp33 = "NFO has an unescaped '&' — Jellyfin may ignore the whole NFO (Auto Repair fixes it)"
check("B33: a bare '&' in the NFO is a warning (rule ON by default); the file itself is still valid", DEFAULT_SETTINGS["health_rules"]["nfo_unescaped_amp"] is True and _amp33 in _r33["health_warnings"] and not _r33["nfo_errors"], _r33["health_reasons"])
_rr33 = dict(_r33); mc._apply_health(_rr33, dict(mc.SETTINGS["health_rules"], nfo_unescaped_amp=False), mc.SETTINGS)
check("B33: rule OFF → no warning", _amp33 not in _rr33["health_reasons"])
check("B33: Auto Repair plans the '&' fix first", (mc._auto_repair_plan(_r33) or [("",)])[0][0] == "amp_fix", mc._auto_repair_plan(_r33))
check("B33: no '&' fix planned when the NFO is clean", not any(c == "amp_fix" for c, _l in mc._auto_repair_plan(scan(M_OK))))

# ── v0.19.2 F5: naming intelligence (Jellyfin / Emby / Plex names) ────────────   ### NEW v0.19.2 F5 ###
section("2zm. names every media server reads (v0.19.2 F5)")
import naming_catalog as _nc5
check("F5: naming_catalog is pure data (no os / tkinter / logging import)",
      not any(m in open(_nc5.__file__, encoding="utf-8").read() for m in ("import os", "import tkinter", "import logging")))
def _img5(fp, w, h, fmt):
    from PIL import Image as _I5
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    _I5.frombytes("RGB", (w, h), os.urandom(w * h * 3)).save(fp, fmt)
# Jellyfin / Plex style: "<video>.jpg" poster, backdrop.jpeg fanart, backdrop-1 / background-2.webp extra backdrops
_j5 = _kodi_dir("Jelly Movie (2000)", "Jelly Movie (2000).mkv", {"Jelly Movie (2000).nfo": "nfo", "Jelly Movie (2000).jpg": _P})
_img5(os.path.join(_j5, "backdrop.jpeg"), 1920, 1080, "JPEG"); _img5(os.path.join(_j5, "backdrop-1.jpg"), 1920, 1080, "JPEG")
_img5(os.path.join(_j5, "background-2.webp"), 1920, 1080, "WEBP")
_r = scan(_j5, use_ffprobe=False)
check("F5: Jellyfin/Plex '<video>.jpg' poster and 'backdrop.jpeg' fanart found (no Missing)",
      os.path.basename(_r["poster_path"]) == "Jelly Movie (2000).jpg" and os.path.basename(_r["fanart_path"]) == "backdrop.jpeg"
      and not any(x in ("Missing poster", "Missing fanart") for x in _r["health_reasons"]), (_r["poster_path"], _r["fanart_path"], _r["health_reasons"]))
check("F5: poster tooltip data — '<video>.jpg' is read by Jellyfin, Emby and Plex (not Kodi)", _r.get("poster_servers") == ["jellyfin", "emby", "plex"], _r.get("poster_servers"))
check("F5: backdrop-1.jpg and background-2.webp count as backdrops (with backdrop.jpeg)", _r["backdrop_count"] == 3, (_r["backdrop_count"], [os.path.basename(p) for p in _r["backdrop_paths"]]))
_e5 = _kodi_dir("Emby Cover", "Emby Cover.mkv", {"Emby Cover.nfo": "nfo"})
_img5(os.path.join(_e5, "cover.webp"), 1000, 1500, "WEBP"); _img5(os.path.join(_e5, "background.png"), 1920, 1080, "PNG")
_r = scan(_e5, use_ffprobe=False)
check("F5: 'cover.webp' poster (Jellyfin only: Emby/Plex do not read .webp) and 'background.png' fanart",
      os.path.basename(_r["poster_path"]) == "cover.webp" and _r.get("poster_servers") == ["jellyfin"] and os.path.basename(_r["fanart_path"]) == "background.png"
      and _r["poster_format"] == "WEBP", (_r["poster_path"], _r.get("poster_servers"), _r["fanart_path"], _r["poster_format"]))
_r = scan(_k1, use_ffprobe=False)
check("F5: Kodi folder rows unchanged — '<video>-poster.jpg' read by Kodi, Jellyfin, Emby", os.path.basename(_r["poster_path"]) == "Kodi Movie (1999)-poster.jpg" and _r["poster_style"] == "kodi" and _r.get("poster_servers") == ["kodi", "jellyfin", "emby"], _r.get("poster_servers"))
# folder.jpg without a poster (F5.7 item 3)
_f5 = _kodi_dir("Folder Only (2002)", "Folder Only (2002).mkv", {"Folder Only (2002).nfo": "nfo", "folder.jpg": _P, "fanart.jpg": _F})
_r = scan(_f5, use_ffprobe=False)
check("F5: folder.jpg without a poster → no warning (poster_missing_with_folder OFF by default)",
      DEFAULT_SETTINGS["health_rules"]["poster_missing_with_folder"] is False and not any(x.startswith("Missing poster") for x in _r["health_reasons"]), _r["health_reasons"])
_rr = dict(_r); mc._apply_health(_rr, dict(mc.SETTINGS["health_rules"], poster_missing_with_folder=True), mc.SETTINGS)
check("F5: rule ON → 'Missing poster (only folder.jpg)'", "Missing poster (only folder.jpg)" in _rr["health_reasons"], _rr["health_reasons"])
_rr = dict(_r, folder_exists=False); mc._apply_health(_rr, mc.SETTINGS["health_rules"], mc.SETTINGS)
check("F5: neither poster nor folder image → 'Missing poster' as before", "Missing poster" in _rr["health_reasons"], _rr["health_reasons"])
check("F5: writers unchanged — Fetch Poster still writes poster.jpg + folder.jpg", [os.path.basename(x) for x in mc.artwork_targets_for_fetch(_f5, "poster")[0]] == ["poster.jpg", "folder.jpg"], mc.artwork_targets_for_fetch(_f5, "poster"))
# NFO order: movie.nfo first; two readable NFOs = warning; edits go to movie.nfo
_n5 = _kodi_dir("Two Nfo (2003)", "Two.Nfo.2003.mkv", {"movie.nfo": "nfo", "Two.Nfo.2003.nfo": "nfo"})
_r = scan(_n5, use_ffprobe=False)
_w5 = "2 NFO files: movie.nfo (used), Two.Nfo.2003.nfo — delete the one you do not need (Kodi, Jellyfin and Emby read movie.nfo first)"
check("F5: movie.nfo + '<video>.nfo' → movie.nfo is read; warning multiple_nfo_files (identical contents)",
      os.path.basename(_r["nfo_path"]) == "movie.nfo" and _w5 in _r["health_warnings"] and _r["nfo_all_differ"] is False, (_r["nfo_path"], _r["health_warnings"]))
_nfo(os.path.join(_n5, "Two.Nfo.2003.nfo"), "Other title", imdb="tt7723099", tmdb="723099")
_r = scan(_n5, use_ffprobe=False)
check("F5: …different contents → still the warning, tooltip says 'contents differ'", _w5 in _r["health_warnings"] and _r["nfo_all_differ"] is True)
_rr = dict(_r); mc._apply_health(_rr, dict(mc.SETTINGS["health_rules"], multiple_nfo_files=False), mc.SETTINGS)
check("F5: rule multiple_nfo_files OFF → no warning", not any("NFO files:" in x for x in _rr["health_reasons"]))
mc._write_hardsub_tags(_r["nfo_path"], None, ["POR"])
check("F5: an edit (Hard-coded subtitles) lands in movie.nfo only",
      "Hardsub POR" in open(os.path.join(_n5, "movie.nfo"), encoding="utf-8").read()
      and "Hardsub" not in open(os.path.join(_n5, "Two.Nfo.2003.nfo"), encoding="utf-8").read())
_r = scan(_k3, use_ffprobe=False)
check("F5: only '<video>.nfo' → no multiple-NFO warning, it is the one read", os.path.basename(_r["nfo_path"]) == "Kodi.Export.1999.1080p.BluRay.nfo" and not any("NFO files:" in x for x in _r["health_reasons"]))
check("F5: a new NFO keeps B23's name (<folder>.nfo)", os.path.basename(scan(_kodi_dir("No Nfo Yet", "No Nfo Yet.mkv", {}), use_ffprobe=False)["nfo_path"]) == "No Nfo Yet.nfo")
# other videos: trailers, samples, extras, stacks, versions, editions
def _vid5(folder, names):
    d = os.path.join(_TMP, "f5v", folder); os.makedirs(d, exist_ok=True)
    for i, (n, size) in enumerate(names):
        open(os.path.join(d, n), "wb").write(b"\0" * size)
    return d
_mv5 = "Multiple video files in same folder"
for _lbl, _names, _main in (
        ("trailer", [("Film (2004).mkv", 9000), ("Film (2004)-trailer.mkv", 2000), ("trailer.mp4", 1500)], "Film (2004).mkv"),
        ("sample", [("Film.2005.mkv", 9000), ("Film.2005.sample.mkv", 500)], "Film.2005.mkv"),
        ("extras", [("Film (2006).mkv", 9000), ("Making of-featurette.mkv", 12000), ("Cut-deleted.mkv", 800)], "Film (2006).mkv"),
        ("stack cd", [("Film (2007) cd2.avi", 9000), ("Film (2007) cd1.avi", 8000)], "Film (2007) cd1.avi"),
        ("stack part a/b", [("Film (2008) - part b.mkv", 9500), ("Film (2008) - part a.mkv", 9000)], "Film (2008) - part a.mkv"),
        ("versions", [("Film (2009) - 1080p.mkv", 9000), ("Film (2009) - 720p.mkv", 5000)], "Film (2009) - 1080p.mkv"),
        ("Plex edition", [("Film (2010) {edition-Director's Cut}.mkv", 9900), ("Film (2010).mkv", 9000)], "Film (2010) {edition-Director's Cut}.mkv")):
    _d = _vid5(_lbl, _names)
    _r = scan(_d, use_ffprobe=False); mc._apply_health(_r, dict(mc.SETTINGS["health_rules"], multiple_video_files=True), mc.SETTINGS)
    check(f"F5: {_lbl} → no 'Multiple video files' (rule ON); main video = {_main}",
          _mv5 not in _r["health_reasons"] and _r["video_count"] == 1 and os.path.basename(_r["video_path"]) == _main,
          (_r["video_count"], _r["video_path"], _r.get("video_kinds"), _r["health_reasons"]))
_d = _vid5("trailer kinds", [("Film (2004).mkv", 9000), ("Film (2004)-trailer.mkv", 99000)])
check("F5: a trailer larger than the movie is never the main video", os.path.basename(scan(_d, use_ffprobe=False)["video_path"]) == "Film (2004).mkv")
check("F5: tooltip text '+ 1 trailer, 2 extras'", mc.video_kinds_text({"a": "trailer", "b": "extra", "c": "extra"}) == "+ 1 trailer, 2 extras")
_d = _vid5("two movies", [("Alien (1979).mkv", 9000), ("Aliens (1986).mkv", 9500)])
_rr = scan(_d, use_ffprobe=False); mc._apply_health(_rr, dict(mc.SETTINGS["health_rules"], multiple_video_files=True), mc.SETTINGS)
check("F5: two unrelated main videos still give 'Multiple video files' (rule ON)", _rr["video_count"] == 2 and _mv5 in _rr["health_reasons"], (_rr["video_count"], _rr["health_reasons"]))
_d = _vid5("extras folder", [("Film (2011).mkv", 9000)]); os.makedirs(os.path.join(_d, "Trailers"), exist_ok=True)
open(os.path.join(_d, "Trailers", "t.mkv"), "wb").write(b"\0" * 99999)
_r = scan(_d, use_ffprobe=False)
check("F5: a Trailers\\ folder is listed (not scanned, its videos not counted)", _r["video_count"] == 1 and _r.get("extra_dirs") == ["Trailers"], (_r["video_count"], _r.get("extra_dirs")))
# subtitles: flags + Subs\ folder
_d = _vid5("subs", [("Film (2012).mkv", 9000), ("Film (2012).pt.forced.srt", 10), ("Film (2012).en.sdh.srt", 10), ("Film (2012).hi.srt", 10)])
os.makedirs(os.path.join(_d, "Subs"), exist_ok=True); open(os.path.join(_d, "Subs", "Film (2012).fr.srt"), "w").write("1")
_r = scan(_d, use_ffprobe=False)
_s5 = {e["file"]: (e["lang"], e.get("flags", [])) for e in _r["subs_external"]}
check("F5: subtitle flags forced / SDH read; '.hi' alone = Hindi; Subs\\ folder read",
      _s5.get("Film (2012).pt.forced.srt") == ("pt", ["forced"]) and _s5.get("Film (2012).en.sdh.srt") == ("en", ["hearing impaired"])
      and _s5.get("Film (2012).hi.srt") == ("hi", []) and _s5.get("Subs\\Film (2012).fr.srt") == ("fr", []), _s5)
check("F5: a .txt file is never a subtitle", ".txt" not in mc.SUBTITLE_EXTENSIONS)
# information notes: Kodi name case, mymovies.xml, extra artwork
_c5 = _kodi_dir("Case Movie", "Case Movie.mkv", {"case movie-poster.jpg": _P, "clearlogo.png": ("png", 400, 155), "mymovies.xml": "xml"})
_r = scan(_c5, use_ffprobe=False)
check("F5: Kodi name-case note, mymovies.xml note, extra artwork listed (information only)",
      any("case-sensitively" in n for n in _r["art_notes"]) and any("mymovies.xml" in n for n in _r["xml_notes"]) and _r["extra_art"] == ["clearlogo.png"]
      and not any("clearlogo" in x or "mymovies" in x for x in _r["health_reasons"]), (_r["art_notes"], _r["xml_notes"], _r["extra_art"]))
_ok5 = True
for _row5 in (scan(x, use_ffprobe=False) for x in (_k1, _k2, _k4, _k6, _k7, M_OK)):
    _ok5 = _ok5 and all(k in _row5 for k in ("nfo_all", "xml_notes", "art_notes", "extra_art", "video_kinds", "video_group"))
check("F5: every scanned row carries the naming fields", _ok5)
_legacy5 = mc._results_from_json([{"subfolder": "Old", "subfolder_path": "x"}])[0]
check("F5: a cached row of an older version gets empty naming fields", _legacy5["nfo_all"] == [] and _legacy5["video_kinds"] == {} and _legacy5["video_group"] is None)

# ── v0.19.2 B53: folders that are not movies (pure classifier) ────────────────   ### NEW v0.19.2 B53 ###
section("2zn. folders that are not movies — classifier (v0.19.2 B53)")
import folder_classifier as _fc53
check("B53: folder_classifier is pure (no os / tkinter / logging import)",
      not any(m in open(_fc53.__file__, encoding="utf-8").read() for m in ("import os", "import tkinter", "import logging")))
def _d53(name, files=(), dirs=()):
    """files: names (a .nfo gets a <movie> NFO unless given as (name, text)); dirs: 'a/b.mkv' paths too."""
    d = os.path.join(_TMP, "b53", name); os.makedirs(d, exist_ok=True)
    for f in files:
        fn, txt = f if isinstance(f, tuple) else (f, None)
        fp = os.path.join(d, fn)
        if txt is not None:
            io.open(fp, "w", encoding="utf-8").write(txt)
        elif fn.lower().endswith(".nfo"):
            _nfo(fp, name, imdb="tt7753001", tmdb="753001")
        else:
            open(fp, "wb").write(b"\0" * 64)
    for sub in dirs:
        p = os.path.join(d, *sub.split("/"))
        if "." in os.path.basename(p):
            os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(b"\0" * 64)
        else:
            os.makedirs(p, exist_ok=True)
    return d
def _k53(d):
    return mc.classify_listing(mc._FolderListing(d))
_cases53 = [
    ("movie + Featurettes folder", _d53("Feat Movie (2001)", ["Feat Movie (2001).mkv"], ["Featurettes/making.mkv"]), "movie"),
    ("movie.nfo + video + stray Season 1 (metadata wins)", _d53("Stray Season (2002)", ["movie.nfo", "Stray.mkv"], ["Season 1"]), "movie"),
    ("tvshow.nfo only", _d53("Breaking Test", [("tvshow.nfo", "<tvshow><title>x</title></tvshow>")]), "series"),
    ("season folders only", _d53("Season Show", [], ["Season 01/e1.mkv", "Season 02/e1.mkv", "Specials"]), "series"),
    ("2 episode videos at the top", _d53("Episode Show", ["Show.S01E01.mkv", "Show.S01E02.mkv"]), "series"),
    ("<folder>.nfo with a <tvshow> root + 1x02 files", _d53("Root Show", [("Root Show.nfo", "<?xml version='1.0'?>\n<tvshow><title>R</title></tvshow>"), "r.1x01.mkv", "r.1x02.mkv"]), "series"),
    ("mini-series: one S01E01 video", _d53("Mini Series", ["Mini.S01E01.mkv"]), "movie"),
    ("DVD structure", _d53("DVD Struct", [], ["VIDEO_TS/VIDEO_TS.IFO"]), "movie"),
    ("Blu-ray structure", _d53("BD Struct", [], ["BDMV/index.bdmv"]), "movie"),
    ("CD1 / CD2 parts", _d53("Parts (1990)", ["Parts (1990) CD1.avi", "Parts (1990) CD2.avi"]), "movie"),
    ("3 unrelated videos", _d53("Downloads", ["Alien.mkv", "Heat.mkv", "Ronin.mkv"]), "loose_videos"),
    ("container of 3 movie folders", _d53("Marvel", [], ["Iron Man (2008)/Iron Man (2008).mkv", "Thor (2011)/Thor (2011).mkv", "Hulk (2003)/Hulk (2003).nfo"]), "container"),
    ("empty folder", _d53("Empty Dir"), "no_media"),
    ("jpg-only folder", _d53("Pics Only", ["a.jpg"]), "no_media"),
    ("$RECYCLE.BIN", _d53("$RECYCLE.BIN", ["x.mkv"]), "system"),
    ("NFO/XML without video", _d53("Only Meta (2004)", ["Only Meta (2004).nfo", "movie.xml"]), "metadata_only"),
    ("one video, no NFO/XML", _d53("Just Video (2005)", ["Just Video (2005).mkv"]), "movie"),
]
for _lbl, _d, _want in _cases53:
    _got = _k53(_d)
    check(f"B53 classifier: {_lbl} → {_want}", _got[0] == _want, _got)
_un53 = mc._FolderListing(os.path.join(_TMP, "b53", "does not exist"))
_g53 = mc.classify_listing(_un53)
check("B53 classifier: a listing that raised OSError → unreadable, the error text kept", _g53[0] == "unreadable" and _un53.error and _un53.error in _g53[1], _g53)
check("B53: series evidence names what was found", _k53(os.path.join(_TMP, "b53", "Season Show"))[2] == "3 season folders", _k53(os.path.join(_TMP, "b53", "Season Show")))
check("B53: container detail lists sub-folders", _k53(os.path.join(_TMP, "b53", "Marvel"))[2] == "e.g. Hulk (2003), Iron Man (2008) … (3 sub-folders)", _k53(os.path.join(_TMP, "b53", "Marvel")))
check("B53: no-media detail", _k53(os.path.join(_TMP, "b53", "Empty Dir"))[2] == "empty" and _k53(os.path.join(_TMP, "b53", "Pics Only"))[2] == "1 file: .jpg")
_peeks53 = []
_r53 = _fc53.classify_folder(mc._FolderListing(os.path.join(_TMP, "b53", "Feat Movie (2001)")), peek=lambda p: _peeks53.append(p))
check("B53: a folder with a video at the top is never peeked into", _r53[0] == "movie" and _peeks53 == [], (_r53, _peeks53))
_nr53 = []
_r53 = _fc53.classify_folder(mc._FolderListing(_d53("Normal Nfo (2006)", ["Normal Nfo (2006).mkv", "Normal Nfo (2006).nfo"])),
                             nfo_root=lambda p: _nr53.append(p))
check("B53: a normal movie folder's NFO is not opened by the classifier (no extra file read)", _r53[0] == "movie" and _nr53 == [], (_r53, _nr53))
# report text
_items53 = [{"path": r"Z:\Movies\Breaking Bad (2008)", "library_root": r"Z:\Movies", "kind": "series", "reason": _fc53.KIND_REASON["series"], "detail": "tvshow.nfo · 5 season folders"},
            {"path": r"Z:\Movies\Amélie Série", "library_root": r"Z:\Movies", "kind": "series", "reason": _fc53.KIND_REASON["series"], "detail": "2 episode files"},
            {"path": r"Z:\Movies\Marvel", "library_root": r"Z:\Movies", "kind": "container", "reason": _fc53.KIND_REASON["container"], "detail": "e.g. Iron Man (2008), Thor (2011) … (23 sub-folders)"},
            {"path": r"Z:\Movies\$RECYCLE.BIN", "library_root": r"Z:\Movies", "kind": "system", "reason": "", "detail": ""}]
_kept53 = [{"path": r"Z:\Movies\Gone (2001)", "library_root": r"Z:\Movies", "kind": "metadata_only", "reason": "", "detail": "Gone (2001).nfo"}]
check("B53: counts line", _fc53.summary_line(1204, _items53 + _kept53) ==
      "Scan finished: 1,204 movies. 4 folders were not added: 2 TV series · 1 holding other folders · 1 system folder. · 1 movie with NFO/XML but no video is in the table.",
      _fc53.summary_line(1204, _items53 + _kept53))
check("B53: hint when one kind dominates (system folders do not count)", _fc53.hint_line(_items53).startswith("Most folders here are TV series"), _fc53.hint_line(_items53))
_txt53 = _fc53.report_text({"scan_date": "2026-10-16 14:32", "scan_kind": "Full Scan", "libraries": [r"Z:\Movies"], "items": _items53,
                            "root_videos": {r"Z:\Movies": ["loose.mkv"]}}, "0.19.2", 1204, _kept53)
check("B53: TXT report — header, groups in order, sorted, root videos, kept group last",
      _txt53[0] == "MediaClinic 0.19.2 — folders not added as movies" and _txt53[1] == r"Scan: 2026-10-16 14:32 (Full Scan) · Libraries: Z:\Movies"
      and _txt53[4] == "TV series (2) — MediaClinic handles movies; the Series tab is planned"
      and _txt53[5].startswith(r"  Z:\Movies\Amélie Série") and _txt53[6].startswith(r"  Z:\Movies\Breaking Bad (2008)    tvshow.nfo")
      and r"  Z:\Movies\loose.mkv" in _txt53 and _txt53[-3].startswith("Metadata without video (1)"), _txt53)
_p53 = os.path.join(_TMP, "b53_export.txt")
mc.export_ignored_txt(_p53, _txt53)
_raw53 = open(_p53, "rb").read()
check("B53: TXT export is UTF-8 with BOM, CRLF line ends, non-ASCII names round-trip",
      _raw53.startswith(b"\xef\xbb\xbf") and b"\r\n" in _raw53 and b"\n" not in _raw53.replace(b"\r\n", b"")
      and _raw53.decode("utf-8-sig").split("\r\n")[:-1] == _txt53)
check("B53: merge keeps other libraries' items, replaces the scanned library's", [i["path"] for i in _fc53.merge_items(
      _items53, [{"path": r"Y:\K\New", "library_root": r"Y:\K", "kind": "no_media"}], [r"Z:\Movies"])] == [r"Y:\K\New"]
      and len(_fc53.merge_items(_items53, [], [r"Y:\K"])) == 4)
# ── v0.19.2 F4a: fix image proportions / size (Pillow pipeline) ─────────────   ### NEW v0.19.2 F4a ###
section("2zo. fix image proportions / size (v0.19.2 F4a)")
import image_fix as _ifx4
from PIL import Image as _I4
check("F4: image_fix has no tkinter / os / file access", not any(m in open(_ifx4.__file__, encoding="utf-8").read()
      for m in ("import os", "import tkinter", "open(", "logging")))
def _pic4(w, h, seed=1):
    im = _I4.new("RGB", (w, h), (40, 60, 90))
    for i in range(0, w, max(1, w // 12)):
        im.paste((200, (i * seed) % 255, 80), (i, h // 3, min(w, i + w // 24 + 1), 2 * h // 3))
    return im
_ok4 = []
for _k4, (_w4, _h4) in (("poster", (700, 1000)), ("poster", (500, 1000)), ("folder", (1100, 1500)),
                        ("fanart", (1920, 800)), ("fanart", (1200, 1000)), ("poster", (1000, 1530))):
    for _m4 in _ifx4.METHODS:
        _src4 = _pic4(_w4, _h4)
        _cw4, _ch4 = _ifx4.corrected_size(_w4, _h4, _k4, _m4)
        _opts4, _d4 = _ifx4.size_options(_k4, _cw4, _ch4)
        _o4 = _opts4[_d4]
        _out4 = _ifx4.render(_src4, _k4, _m4, None if _o4["key"] == "keep" else (_o4["w"], _o4["h"]))
        _p4 = os.path.join(_TMP, f"f4_{_k4}_{_w4}x{_h4}_{_m4}.jpg"); _out4.save(_p4, "JPEG", quality=92)
        _st4, _desc4, _fl4 = mc.evaluate_image(mc.probe_image(_p4), _k4, dict(mc.SETTINGS, **{f"min_{_k4}_kb": 0}))
        _tier4 = mc.classify_image_quality(_out4.size[0], _out4.size[1], _k4)
        _ok4.append((not _fl4["bad_ratio"]) and (_o4["key"] == "keep" or (_out4.size == (_o4["w"], _o4["h"]) and _tier4 == _o4["key"]))
                    or (_k4, _w4, _h4, _m4, _out4.size, _o4["key"], _desc4))
check("F4: every wrong ratio × every method → right proportions, exactly on the chosen tier (evaluate_image passes)",
      all(x is True for x in _ok4), [x for x in _ok4 if x is not True][:3])
check("F4: 700×1000 poster + blur fill → 700×1050; default 720p 666×1000 (×0.95 ✓), 1080p ×1.43 ⚠, 4K ✕",
      (lambda o, d: _ifx4.corrected_size(700, 1000, "poster", "blur") == (700, 1050) and o[d]["key"] == "720p"
       and o[d]["mark"] == "ok" and abs(o[d]["factor"] - 0.952) < 0.01
       and next(x for x in o if x["key"] == "1080p")["mark"] == "warn" and next(x for x in o if x["key"] == "4K")["mark"] == "no"
       and o[-1]["key"] == "keep")(*_ifx4.size_options("poster", 700, 1050)))
check("F4: crop removes only the excess; a deviation ≤ 3 % is stretched",
      _ifx4.corrected_size(1920, 800, "fanart", "crop_center") == (1422, 800) and _ifx4.effective_method(1000, 1530, "poster", "blur") == "stretch")
check("F4: upscaling limits from settings_model (plain 1.25/1.5, AI 2/4)", mc._ifx.UPSCALE_LIMITS == {"plain": (1.25, 1.5), "ai": (2.0, 4.0)}
      and _ifx4.mark_for(1.3) == "warn" and _ifx4.mark_for(1.6) == "no" and _ifx4.mark_for(1.6, ai=True) == "ok" and _ifx4.mark_for(3.0, ai=True) == "warn")
check("F4: the minimum-tier note when it needs more than the recommended enlargement",
      _ifx4.min_tier_note("poster", 750, "1080p") == "Reaching 1080p needs ×2.0. ✓ with AI upscale, ✕ without it. A better online image is recommended."
      and _ifx4.min_tier_note("poster", 1450, "1080p") == "", _ifx4.min_tier_note("poster", 750, "1080p"))
check("F4 batch: only ✓ sizes — 700×1000 with minimum 1080p is skipped ('needs ×1.4'), 1100×1500 → 1000×1500",
      _ifx4.batch_choice("poster", 700, 1000, "blur", "1080p")[0] is None and "needs ×1.4" in _ifx4.batch_choice("poster", 700, 1000, "blur", "1080p")[1]
      and _ifx4.batch_choice("poster", 1100, 1500, "blur", "1080p")[0] == (1000, 1500), (_ifx4.batch_choice("poster", 700, 1000, "blur", "1080p"), _ifx4.batch_choice("poster", 1100, 1500, "blur", "1080p")))
_sm4 = _I4.new("RGB", (1920, 1440), (30, 30, 30))
_sm4.paste(_I4.frombytes("RGB", (1920, 400), os.urandom(1920 * 400 * 3)), (0, 1040))
_c4 = _ifx4.fix_ratio(_sm4, "fanart", "crop_smart")
check("F4: smart crop keeps the detailed part (noise at the bottom → bottom window)", _c4.size == (1920, 1080) and _ifx4._smart_offset(_sm4, 1920, 1080)[1] >= 300, _ifx4._smart_offset(_sm4, 1920, 1080))
_up4 = []
_r4 = _ifx4.render(_pic4(500, 750), "poster", "blur", (1000, 1500), upscale=lambda im: (_up4.append(im.size), im.resize((im.size[0] * 4, im.size[1] * 4)))[1])
check("F4: an upscaler is used on the ORIGINAL when the target is larger, result exactly the target", _up4 == [(500, 750)] and _r4.size == (1000, 1500), (_up4, _r4.size))
# on disk: apply_image_fix
_f4d = os.path.join(_TMP, "f4", "Fix Me (2001)"); os.makedirs(_f4d, exist_ok=True)
open(os.path.join(_f4d, "Fix Me (2001).mkv"), "wb").write(b"\0" * 64)
_nfo(os.path.join(_f4d, "Fix Me (2001).nfo"), "Fix Me", imdb="tt7744001", tmdb="744001")
_pic4(700, 1000).save(os.path.join(_f4d, "poster.jpg"), "JPEG", quality=90)
shutil.copy2(os.path.join(_f4d, "poster.jpg"), os.path.join(_f4d, "folder.jpg"))
_pic4(1920, 800).save(os.path.join(_f4d, "fanart.png"), "PNG")
_r4 = scan(_f4d, use_ffprobe=False)
check("F4: the fixture has image warnings (poster ratio, fanart ratio)", mc.image_fix_kinds(_r4) == ["poster", "folder", "fanart"], mc.image_fix_kinds(_r4))
_n_bk4 = len(os.listdir(_BK))
_w4 = mc._with_backup_action(mc.IMAGE_FIX_ACTION, mc.apply_image_fix, _r4, "poster", "blur", (666, 1000))
_wf4 = mc._with_backup_action(mc.IMAGE_FIX_ACTION, mc.apply_image_fix, _r4, "fanart", "crop_smart", (1280, 720))
_r4b = scan(_f4d, use_ffprobe=False)
check("F4: poster fixed in place (JPEG 666×1000), folder.jpg kept identical, fanart PNG stays PNG 1280×720",
      [os.path.basename(p) for p in _w4] == ["poster.jpg", "folder.jpg"] and _r4b["poster_dim"] == "666×1000" and _r4b["poster_format"] == "JPEG"
      and open(os.path.join(_f4d, "poster.jpg"), "rb").read() == open(os.path.join(_f4d, "folder.jpg"), "rb").read()
      and _r4b["fanart_format"] == "PNG" and _r4b["fanart_dim"] == "1280×720" and [os.path.basename(p) for p in _wf4] == ["fanart.png"],
      (_w4, _r4b["poster_dim"], _r4b["fanart_dim"], _r4b["fanart_format"]))
check("F4: after the fix no proportion warning remains", not (_r4b["poster_flags"] or {}).get("bad_ratio") and not (_r4b["fanart_flags"] or {}).get("bad_ratio"), (_r4b["poster_desc"], _r4b["fanart_desc"]))
check("F4: a backup was made first (labelled for Backup History / Undo)", len(os.listdir(_BK)) > _n_bk4)
_f4w = os.path.join(_TMP, "f4", "Webp Cover"); os.makedirs(_f4w, exist_ok=True)
open(os.path.join(_f4w, "Webp Cover.mkv"), "wb").write(b"\0" * 64)
_pic4(700, 1000).save(os.path.join(_f4w, "cover.webp"), "WEBP")
_r4w = scan(_f4w, use_ffprobe=False)
mc.apply_image_fix(_r4w, "poster", "blur", (666, 1000))
check("F4: a .webp poster (F5 name) is written as the .jpg of the same name; the .webp removed after the write",
      sorted(n for n in os.listdir(_f4w) if not n.endswith(".mkv")) == ["cover.jpg"] and mc.probe_image(os.path.join(_f4w, "cover.jpg"))["format"] == "JPEG",
      os.listdir(_f4w))
_f4j = os.path.join(_TMP, "f4", "Jpeg Poster"); os.makedirs(_f4j, exist_ok=True)
open(os.path.join(_f4j, "Jpeg Poster.mkv"), "wb").write(b"\0" * 64)
_pic4(666, 1000).save(os.path.join(_f4j, "poster.jpeg"), "JPEG")
check("F4/F5: Fetch / fix overwrite a 'poster.jpeg' under its own name (no second poster)", mc.artwork_write_target(_f4j, "poster") == (os.path.join(_f4j, "poster.jpeg"), None))
_plan4 = mc.image_fix_batch_plan([_r4, _r4w])
check("F4 batch plan: one line per image to fix (an identical folder.jpg follows its poster), text lists each",
      [(os.path.basename(r["subfolder_path"]), k) for r, k, _m, _t, _n in _plan4] == [("Fix Me (2001)", "poster"), ("Fix Me (2001)", "fanart"), ("Webp Cover", "poster")]
      and "🎬 Fix Me" in mc.image_fix_batch_text(_plan4), [(r["subfolder"], k) for r, k, *_ in _plan4])

# ── v0.19.2 F4b: AI upscaler download + upscale (no network, no GPU) ─────────   ### NEW v0.19.2 F4b ###
section("2zp. AI upscaler — pinned download, test, upscale (v0.19.2 F4b)")
import zipfile as _zip4b, hashlib as _hl4b, pathlib as _pl4b, re
_U4 = mc.UPSCALER_DOWNLOAD
check("F4b: the pinned release is recorded (official GitHub asset, size, SHA-256, exe, model, licences)",
      _U4["url"].startswith("https://github.com/xinntao/Real-ESRGAN/releases/download/") and _U4["size"] == 45_474_481
      and re.fullmatch(r"[0-9a-f]{64}", _U4["sha256"]) and _U4["exe"] == "realesrgan-ncnn-vulkan.exe"
      and all(os.path.isfile(os.path.join(os.path.dirname(mc.__file__), "third_party", l)) for l in _U4["licences"]))
check("F4b: installed under the config folder (tools\\realesrgan), never next to the program",
      os.path.normcase(mc.upscaler_dir()).startswith(os.path.normcase(os.environ["MEDIACLINIC_CONFIG_DIR"])), mc.upscaler_dir())
_z4b = os.path.join(_TMP, "f4b_fake_release.zip")
with _zip4b.ZipFile(_z4b, "w") as z:
    z.writestr("realesrgan-ncnn-vulkan.exe", b"MZ fake")
    z.writestr("models/realesrgan-x4plus.param", "param")
    z.writestr("models/realesrgan-x4plus.bin", b"\0" * 100)
    z.writestr("input.jpg", b"demo"); z.writestr("onepiece_demo.mp4", b"demo")
    z.writestr("../evil.txt", "outside")
_b4b = open(_z4b, "rb").read()
_info4b = dict(_U4, url=_pl4b.Path(_z4b).as_uri(), size=len(_b4b), sha256=_hl4b.sha256(_b4b).hexdigest())
_prog4b = []
_d4b = mc.download_upscaler(progress=lambda n, t: _prog4b.append((n, t)), info=_info4b)
_files4b = sorted(os.path.relpath(os.path.join(r, f), _d4b).replace("\\", "/") for r, _ds, fs in os.walk(_d4b) for f in fs)
check("F4b: download checked and unpacked — exe, models, both licence texts; no demo files; no path outside the folder",
      _files4b == sorted(["realesrgan-ncnn-vulkan.exe", "models/realesrgan-x4plus.param", "models/realesrgan-x4plus.bin"] + list(_U4["licences"]))
      and not os.path.exists(os.path.join(os.path.dirname(_d4b), "evil.txt")) and _prog4b and _prog4b[-1][0] == len(_b4b), _files4b)
_bad4b = dict(_info4b, sha256="0" * 64)
try:
    mc.download_upscaler(info=_bad4b); _e4b = ""
except Exception as e:
    _e4b = str(e)
check("F4b: a download that does not match the SHA-256 is refused; the installed copy stays; no temp files left",
      "does not match the pinned release" in _e4b and os.path.isfile(mc.upscaler_exe())
      and not os.path.exists(_d4b + ".download") and not os.path.exists(_d4b + ".new"), _e4b)
try:
    mc.download_upscaler(info=_info4b, cancel=lambda: True); _e4b = ""
except Exception as e:
    _e4b = str(e)
check("F4b: Cancel stops the download", _e4b == "cancelled", _e4b)
_fake4b = os.path.join(_TMP, "fake_upscaler.py")
io.open(_fake4b, "w", encoding="utf-8").write(
    "import sys\nfrom PIL import Image\nif len(sys.argv) > 3: sys.exit(int(sys.argv[3]))\n"
    "im = Image.open(sys.argv[1]); im.resize((im.size[0] * 4, im.size[1] * 4)).save(sys.argv[2])\n")
_cmd4b = mc.upscaler_cmd
_prefs4b = dict(mc.SETTINGS.get("image_fix_prefs") or {})
class _WinOnly(Exception):
    pass
try:
    if sys.platform != "win32":
        raise _WinOnly   # the AI upscaler is Windows only; CI runs on Linux
    check("F4b: installed but not tested → AI off ('not tested yet')", mc.upscaler_state() == (False, "AI upscale: installed, not tested yet"), mc.upscaler_state())
    mc.upscaler_cmd = lambda i, o, scale=4: [sys.executable, _fake4b, i, o, "3"]
    check("F4b: the GPU test reads a failing upscaler as 'no usable Vulkan GPU'", mc.test_upscaler(timeout=30) == (False, "no usable Vulkan GPU (exit code 3)"), mc.test_upscaler(timeout=30))
    mc.upscaler_cmd = lambda i, o, scale=4: [sys.executable, _fake4b, i, o]
    check("F4b: the GPU test passes with a working upscaler (32×32 → 128×128, through the B28 runner)", mc.test_upscaler(timeout=30) == (True, ""))
    mc.SETTINGS["image_fix_prefs"] = dict(_prefs4b, ai_test="no usable Vulkan GPU (exit code 3)")
    check("F4b: a failed test keeps AI off with the reason", mc.upscaler_state()[0] is False and "no usable Vulkan GPU" in mc.upscaler_state()[1] and mc.upscale_function() is None)
    mc.SETTINGS["image_fix_prefs"] = dict(_prefs4b, ai_test="ok")
    _up4b = mc.upscale_function()
    _f4bd = os.path.join(_TMP, "f4", "Ai Fix"); os.makedirs(_f4bd, exist_ok=True)
    open(os.path.join(_f4bd, "Ai Fix.mkv"), "wb").write(b"\0" * 64)
    _pic4(500, 750).save(os.path.join(_f4bd, "poster.jpg"), "JPEG")
    mc.apply_image_fix(scan(_f4bd, use_ffprobe=False), "poster", "blur", (1000, 1500), _up4b)
    check("F4b: AI upscale used for an enlargement (500×750 → 1000×1500 via the upscaler, no failure)",
          mc.upscaler_state()[0] is True and _up4b is not None and _up4b.failed == [] and mc.probe_image(os.path.join(_f4bd, "poster.jpg"))["w"] == 1000)
    mc.upscaler_cmd = lambda i, o, scale=4: [sys.executable, _fake4b, i, o, "2"]
    _up4c = mc.upscale_function()
    _pic4(500, 750).save(os.path.join(_f4bd, "poster.jpg"), "JPEG")
    mc.apply_image_fix(scan(_f4bd, use_ffprobe=False), "poster", "blur", (1000, 1500), _up4c)
    check("F4b: when the upscaler fails, the plain resize is used and the failure is recorded",
          _up4c.failed and mc.probe_image(os.path.join(_f4bd, "poster.jpg"))["w"] == 1000, _up4c.failed)
except _WinOnly:
    pass
finally:
    mc.upscaler_cmd = _cmd4b
    mc.SETTINGS["image_fix_prefs"] = _prefs4b

# ── v0.19.2 B50 / B56: check for updates, download and install (no network) ──   ### NEW v0.19.2 B50 / B56 ###
section("2zr. check for updates + install an update (v0.19.2 B50 / B56)")
import inspect, datetime
check("B50: parse_version / is_newer", mc.parse_version("v0.19.10") == (0, 19, 10) and mc.parse_version("nightly") is None
      and mc.is_newer("v0.19.10", "0.19.9") and mc.is_newer("0.20.0", "0.19.2") and not mc.is_newer("v0.19.2", "0.19.2")
      and not mc.is_newer("v0.19.1", "0.19.2") and not mc.is_newer("garbage", "0.19.2"))
def _fg50(code, body=None, exc=None):
    def g(url, timeout):
        if exc:
            raise exc
        return code, json.dumps(body).encode() if body is not None else b""
    return g
_c50 = {k: mc.check_latest_release(get=g) for k, g in (
    ("newer", _fg50(200, {"tag_name": "v0.20.0", "html_url": "https://github.com/junqueirach/mediaclinic/releases/tag/v0.20.0"})),
    ("same", _fg50(200, {"tag_name": "v0.19.2"})), ("older", _fg50(200, {"tag_name": "v0.19.1"})),
    ("404", _fg50(404)), ("503", _fg50(503)), ("badtag", _fg50(200, {"tag_name": "nightly"})),
    ("exc", _fg50(0, exc=OSError("no route to host"))))}
check("B50: check_latest_release — newer / same / older / 404 / 503 / bad tag / exception, never raises",
      _c50["newer"]["status"] == "newer" and _c50["newer"]["version"] == "0.20.0" and _c50["same"]["status"] == "latest"
      and _c50["older"]["status"] == "latest" and _c50["404"]["status"] == "none" and _c50["503"]["status"] == "error"
      and "503" in _c50["503"]["error"] and _c50["badtag"]["status"] == "error" and _c50["exc"]["status"] == "error"
      and "no route" in _c50["exc"]["error"], {k: (v["status"], v["error"]) for k, v in _c50.items()})
check("B50: the default API is GitHub's releases/latest of junqueirach/mediaclinic (no TMDB client)",
      mc._DEFAULT_UPDATE_API == "https://api.github.com/repos/junqueirach/mediaclinic/releases/latest"
      and "_http_get_json" not in inspect.getsource(mc.check_latest_release))
# a fake release on disk
_R56 = os.path.join(_TMP, "b56"); os.makedirs(_R56, exist_ok=True)
def _rel56(version="0.19.98",   # v0.19.3: above APP_VERSION (was "0.19.3", intended change)
           entries=None, sha="good", digest=None, url_override=None):
    zp = os.path.join(_R56, f"MediaClinic-{version}-win64.zip")
    with _zip4b.ZipFile(zp, "w") as z:
        for n, data in (entries or [("MediaClinic/MediaClinic.exe", b"MZ new"), ("MediaClinic/_internal/x.dll", b"dll")]):
            z.writestr(n, data)
    h = _hl4b.sha256(open(zp, "rb").read()).hexdigest()
    assets = [{"name": os.path.basename(zp), "size": os.path.getsize(zp), "browser_download_url": url_override or _pl4b.Path(zp).as_uri()}]
    if digest:
        assets[0]["digest"] = "sha256:" + (h if digest == "good" else "0" * 64)
    if sha:
        sp = zp + ".sha256"
        open(sp, "w").write(f"{h if sha == 'good' else '1' * 64}  {os.path.basename(zp)}\n")
        assets.append({"name": os.path.basename(sp), "browser_download_url": _pl4b.Path(sp).as_uri()})
    lj = os.path.join(_R56, "latest.json")
    json.dump({"tag_name": f"v{version}", "html_url": "https://github.com/junqueirach/mediaclinic/releases", "assets": assets}, open(lj, "w"))
    return _pl4b.Path(lj).as_uri()
def _try56(rel, base, **kw):
    try:
        return mc.download_update(rel, base, **kw), ""
    except Exception as e:
        return None, str(e)
_base56 = os.path.join(_TMP, "b56_apps"); os.makedirs(os.path.join(_base56, "MediaClinic"), exist_ok=True)
open(os.path.join(_base56, "MediaClinic", "MediaClinic.exe"), "wb").write(b"MZ running")
os.environ["MEDIACLINIC_UPDATE_API"] = _rel56()
try:
    _rel = mc.check_latest_release()
    _t56, _e56 = _try56(_rel, _base56)
    check("B56: a newer release is downloaded, checked (.sha256), unpacked next to the running folder (top folder flattened)",
          _rel["status"] == "newer" and _e56 == "" and os.path.isfile(os.path.join(_base56, "MediaClinic 0.19.98", "MediaClinic.exe"))
          and os.path.isfile(os.path.join(_base56, "MediaClinic 0.19.98", "_internal", "x.dll"))
          and open(os.path.join(_base56, "MediaClinic", "MediaClinic.exe"), "rb").read() == b"MZ running"
          and not [n for n in os.listdir(_base56) if n.endswith((".part", ".new"))], (_e56, os.listdir(_base56)))
    _t56, _e56 = _try56(_rel, _base56)
    check("B56: an existing target folder → message, untouched", "already exists" in _e56
          and open(os.path.join(_base56, "MediaClinic 0.19.98", "MediaClinic.exe"), "rb").read() == b"MZ new", _e56)
    def _clean56():
        return sorted(n for n in os.listdir(_base56) if n != "MediaClinic" and n != "MediaClinic 0.19.98")
    os.environ["MEDIACLINIC_UPDATE_API"] = _rel56("0.19.4", sha="bad")
    _t56, _e56 = _try56(mc.check_latest_release(), _base56)
    check("B56: a wrong hash → refused, nothing left behind", "does not match" in _e56 and _clean56() == [], (_e56, _clean56()))
    os.environ["MEDIACLINIC_UPDATE_API"] = _rel56("0.19.4", sha=None)
    _t56, _e56 = _try56(mc.check_latest_release(), _base56)
    check("B56: no checksum → refused", "no checksum" in _e56 and _clean56() == [], _e56)
    os.environ["MEDIACLINIC_UPDATE_API"] = _rel56("0.19.5", sha=None, digest="good")
    _t56, _e56 = _try56(mc.check_latest_release(), _base56)
    check("B56: the API's 'digest' field is accepted as the checksum", _e56 == "" and os.path.isfile(os.path.join(_base56, "MediaClinic 0.19.5", "MediaClinic.exe")), _e56)
    os.environ["MEDIACLINIC_UPDATE_API"] = _rel56("0.19.6")
    _t56, _e56 = _try56(mc.check_latest_release(), _base56, cancel=lambda: True)
    check("B56: Cancel → no .part, no folder", _e56 == "cancelled" and not os.path.exists(os.path.join(_base56, "MediaClinic 0.19.6"))
          and not [n for n in os.listdir(_base56) if n.endswith(".part")], (_e56, os.listdir(_base56)))
    os.environ["MEDIACLINIC_UPDATE_API"] = _rel56("0.19.7", entries=[("MediaClinic/MediaClinic.exe", b"MZ"), ("../evil.txt", b"x")])
    _t56, _e56 = _try56(mc.check_latest_release(), _base56)
    check("B56: a zip with '..' entries → refused, nothing written outside or inside", "unsafe entry" in _e56
          and not os.path.exists(os.path.join(_TMP, "evil.txt")) and not os.path.exists(os.path.join(_base56, "MediaClinic 0.19.7")), _e56)
    _rel8 = mc.check_latest_release()
    del os.environ["MEDIACLINIC_UPDATE_API"]
    _rel8 = dict(_rel8, assets=[dict(_rel8["assets"][0], browser_download_url="https://example.com/MediaClinic-0.19.7-win64.zip")] + _rel8["assets"][1:])
    _t56, _e56 = _try56(_rel8, _base56)
    check("B56: a non-GitHub link (no test hook) → refused", "not a GitHub link" in _e56, _e56)
finally:
    os.environ.pop("MEDIACLINIC_UPDATE_API", None)
check("B50: keys check_updates (OFF), last_update_check, skipped_version (model + schema)",
      DEFAULT_SETTINGS.get("check_updates") is False and DEFAULT_SETTINGS.get("last_update_check") == "" and DEFAULT_SETTINGS.get("skipped_version") == ""
      and all(k in json.load(open(os.path.join(os.path.dirname(mc.__file__), "settings_schema.json"), encoding="utf-8"))["properties"]
              for k in ("check_updates", "last_update_check", "skipped_version")))

# ── v0.19.2 B51: dark title bar + small transparent icon (pure parts) ─────────   ### NEW v0.19.2 B51 ###
section("2zq. dark title bar and title-bar icon (v0.19.2 B51)")
check("B51: _colorref('#1e1e2e') == 0x002E1E1E", mc._colorref("#1e1e2e") == 0x002E1E1E, hex(mc._colorref("#1e1e2e")))
check("B51: the helpers never raise with a fake window", mc._set_dark_title_bar(object()) is False and mc._set_window_icons(object()) is False
      and mc.decorate_window(object()) == (False, False))
_si51 = mc._small_icon_path()
_ok51 = []
if _si51:
    with _I4.open(_si51) as _ico51:
        _sz51 = sorted(_ico51.ico.sizes())
        for _s51 in _sz51:
            _im51 = _ico51.ico.getimage(_s51).convert("RGBA")
            _w51, _h51 = _im51.size
            _ok51.append(all(_im51.getpixel(p)[3] == 0 for p in ((0, 0), (_w51 - 1, 0), (0, _h51 - 1), (_w51 - 1, _h51 - 1)))
                         and _im51.getpixel((_w51 // 2, _h51 // 2))[3] == 255)
check("B51: MediaClinic-small.ico has 16 / 20 / 24 / 32 px, transparent corners, an opaque centre",
      bool(_si51) and _sz51 == [(16, 16), (20, 20), (24, 24), (32, 32)] and all(_ok51), (_si51, _sz51 if _si51 else None, _ok51))
check("B51: key dark_title_bar default ON (model + schema)", DEFAULT_SETTINGS.get("dark_title_bar") is True
      and json.load(open(os.path.join(os.path.dirname(mc.__file__), "settings_schema.json"), encoding="utf-8"))["properties"]["dark_title_bar"]["default"] is True)

check("B53: key scan_ignored_report default ON (model + schema)", DEFAULT_SETTINGS.get("scan_ignored_report") is True
      and json.load(open(os.path.join(os.path.dirname(mc.__file__), "settings_schema.json"), encoding="utf-8"))["properties"]["scan_ignored_report"]["default"] is True)

section("2zs. title mismatch: both local titles, hint, title_sync (v0.19.3 B60)")   ### NEW v0.19.3 B60 ###
_r60 = {"nfo_title": "O Auto da Compadecida", "xml_localtitle": "A Dog's Will", "original_title": "A Dog's Will",
        "subfolder": "O Auto da Compadecida (2000)"}
_m60 = mc.title_mismatch_reason(_r60)
check("B60: the warning names both local titles and their tags",
      _m60.startswith('Title mismatch: NFO <title> "O Auto da Compadecida" vs XML <LocalTitle> "A Dog\'s Will"'), _m60)
check("B60: hint when the XML title is the original title (the user's case)",
      "the XML title is the original title" in _m60 and 'probably "O Auto da Compadecida"' in _m60, _m60)
check("B60: the reason key stays 'Title mismatch' (statistics)", mc._reason_key(_m60) == "Title mismatch", mc._reason_key(_m60))
check("B60: accents / punctuation only → its own hint",
      "only in accents" in mc.title_mismatch_reason({"nfo_title": "Amélie!", "xml_localtitle": "Amelie"}))
_c60 = mc.title_sync_choice(_r60)
check("B60: title_sync_choice — the original-title side gives way (write XML <LocalTitle>)",
      _c60[:2] == ("O Auto da Compadecida", "xml"), _c60)
_c60 = mc.title_sync_choice({"nfo_title": "A Dog's Will", "xml_localtitle": "O Auto da Compadecida", "original_title": "A Dog's Will"})
check("B60: …and the other way round (write NFO <title>)", _c60[:2] == ("O Auto da Compadecida", "nfo"), _c60)
_c60 = mc.title_sync_choice({"nfo_title": "Bacurau", "xml_localtitle": "Bacurau 2", "subfolder": "Bacurau (2019)"})
_c60b = mc.title_sync_choice({"nfo_title": "Bacurau 2", "xml_localtitle": "Bacurau", "subfolder": "Bacurau [2019] 1080p"})
check("B60: the side that matches the folder name wins", _c60[:2] == ("Bacurau", "xml") and _c60b[:2] == ("Bacurau", "nfo"), (_c60, _c60b))
_c60 = mc.title_sync_choice({"nfo_title": "Alpha", "xml_localtitle": "Beta", "subfolder": "Gamma (2000)"}, "nfo")
check("B60: unclear → the NFO title is kept by default (user decision)", _c60[:2] == ("Alpha", "xml") and "NFO title is kept" in _c60[2], _c60)
_c60 = mc.title_sync_choice({"nfo_title": "Alpha", "xml_localtitle": "Beta", "subfolder": "Gamma (2000)"}, "skip")
check("B60: unclear + 'skip' → nothing written, both titles named, how to fix",
      _c60[0] is None and '"Alpha"' in _c60[2] and '"Beta"' in _c60[2] and "Make titles the same" in _c60[2], _c60)
check("B60: equal titles (entities, case) → nothing to do",
      mc.title_sync_choice({"nfo_title": "Fast &amp; Furious", "xml_localtitle": "fast & furious"})[0] is None)
_p60 = dict(_r60, nfo_exists=True, xml_exists=True)
check("B60: Auto Repair plans title_sync when both titles are filled and differ",
      "title_sync" in [c for c, _l in mc._auto_repair_plan(_p60)], mc._auto_repair_plan(_p60))
check("B60: …not when the rule is off, nor when the titles match",
      "title_sync" not in [c for c, _l in mc._auto_repair_plan(_p60, rules={"title_mismatch": False})]
      and "title_sync" not in [c for c, _l in mc._auto_repair_plan(dict(_p60, xml_localtitle="O Auto da Compadecida"))])
_k60 = mc._fix_issue_keys({"health_reasons": ['Title mismatch: NFO <title> "Backdrop Story" vs XML <LocalTitle> "Rating Days"']})
check("B60: ⚠ Fix issues key 'title' (a title holding 'backdrop' / 'rating' is not misread)",
      "title" in _k60 and "backdrops" not in _k60 and "ratings" not in _k60, _k60)
_tt60 = mc.health_tooltip_lines({"health_errors": ["Missing IMDb ID"], "health_warnings": [_m60 + " and a much longer tail " * 3]})
check("B60: movie tooltip lists every reason, wrapped, never cut",
      "Health: 1 error, 1 warning" in _tt60 and "✕  Missing IMDb ID" in _tt60 and "⚠  Title mismatch" in _tt60
      and "a much longer tail" in " ".join(_tt60.split()) and "…" not in _tt60
      and max(len(l) for l in _tt60.splitlines()) <= 90, _tt60)
check("B60: a healthy row adds nothing to the tooltip", mc.health_tooltip_lines({"health_reasons": []}) == "")
# on disk: the user's case, then Auto Repair's title_sync on temp files
_d60 = os.path.join(_TMP, "b60", "O Auto da Compadecida (2000)"); os.makedirs(_d60, exist_ok=True)
_nfo(os.path.join(_d60, "movie.nfo"), "O Auto da Compadecida", year="2000", original="A Dog's Will")
_xml(os.path.join(_d60, "movie.xml"), "A Dog's Will", year="2000", original="A Dog's Will")
open(os.path.join(_d60, "O Auto da Compadecida (2000).mkv"), "wb").write(b"\0" * 64)
_s60 = scan(_d60, use_ffprobe=False)
check("B60: scan keeps the original title and warns with the hint",
      _s60.get("original_title") == "A Dog's Will" and any("the XML title is the original title" in x for x in _s60["health_reasons"]),
      (_s60.get("original_title"), _s60["health_reasons"]))
_nb60 = open(_s60["nfo_path"], "rb").read(); _xb60 = open(_s60["xml_path"], "rb").read()
_bk60 = []
_ctx60 = {"d": _s60, "nfo": _s60["nfo_path"], "xml": _s60["xml_path"], "backup": lambda: _bk60.append(1)}
_res60 = mc.App._ar_title_sync(None, _ctx60)
_xa60 = open(_s60["xml_path"], "rb").read()
_chg60 = [(a, b) for a, b in zip(_xb60.split(b"\n"), _xa60.split(b"\n")) if a != b]
check("B60: title_sync writes only XML <LocalTitle>, backup first, NFO untouched",
      _res60[0] == "fixed" and _bk60 == [1] and open(_s60["nfo_path"], "rb").read() == _nb60
      and len(_chg60) == 1 and b"<LocalTitle>O Auto da Compadecida</LocalTitle>" in _chg60[0][1]
      and len(_xb60.split(b"\n")) == len(_xa60.split(b"\n")), (_res60, _chg60))
_s60b = scan(_d60, use_ffprobe=False)
check("B60: after the fix the warning is gone (original title unchanged)",
      not any(x.startswith("Title mismatch") for x in _s60b["health_reasons"]) and _s60b["original_title"] == "A Dog's Will",
      _s60b["health_reasons"])
_d60b = os.path.join(_TMP, "b60", "Fast and Furious (2001)"); os.makedirs(_d60b, exist_ok=True)
_nfo(os.path.join(_d60b, "movie.nfo"), "Velozes &amp; Furiosos", year="2001", original="The Fast and the Furious")
_xml(os.path.join(_d60b, "movie.xml"), "The Fast and the Furious", year="2001", original="The Fast and the Furious")
_s60c = scan(_d60b, use_ffprobe=False)
_r60c = mc.App._ar_title_sync(None, {"d": _s60c, "nfo": _s60c["nfo_path"], "xml": _s60c["xml_path"], "backup": lambda: None})
check("B60: '&' is escaped once when written; the XML still parses and reads back",
      _r60c[0] == "fixed" and b"<LocalTitle>Velozes &amp; Furiosos</LocalTitle>" in open(_s60c["xml_path"], "rb").read()
      and mc.get_primary_titles(None, _s60c["xml_path"])[1] == "Velozes & Furiosos", _r60c)
_d60c = os.path.join(_TMP, "b60", "Cp1252 (2002)"); os.makedirs(_d60c, exist_ok=True)
_nfo(os.path.join(_d60c, "movie.nfo"), "Ação", year="2002", original="Action")
io.open(os.path.join(_d60c, "movie.xml"), "w", encoding="cp1252", newline="\n").write(
    '<?xml version="1.0" encoding="windows-1252"?>\n<Item>\n\t<LocalTitle>Action</LocalTitle>\n\t<OriginalTitle>Action</OriginalTitle>\n\t<Overview>Açúcar</Overview>\n</Item>\n')
_xc60 = open(os.path.join(_d60c, "movie.xml"), "rb").read()
_s60d = scan(_d60c, use_ffprobe=False)
_r60d = mc.App._ar_title_sync(None, {"d": _s60d, "nfo": _s60d["nfo_path"], "xml": os.path.join(_d60c, "movie.xml"), "backup": lambda: None})
check("B60: a non-UTF-8 XML is not changed (B37) and the step reports it",
      _r60d[0] == "failed" and open(os.path.join(_d60c, "movie.xml"), "rb").read() == _xc60, _r60d)
check("B60: title_sync_default is a Health Rules key ('nfo' by default)",
      mc._DEFAULT_SETTINGS["health_rules"].get("title_sync_default") == "nfo")

section("2zt. Replace All Backdrops: how many (v0.19.3 B61)")   ### NEW v0.19.3 B61 ###
_m61 = mc.backdrop_count_message(6, 12, "TMDB", 3)
check("B61: fewer than you have → 'You will get 3 — the 3 with the highest resolution (3 fewer)' + 'Replace anyway'",
      _m61[0] == "You have 6 backdrops. TMDB offers 12.\nYou will get 3 — the 3 with the highest resolution (3 fewer)."
      and _m61[1] == "Replace anyway" and _m61[2] is True, _m61)
_m61 = mc.backdrop_count_message(6, 12, "TMDB", 6)
_m61b = mc.backdrop_count_message(2, 12, "fanart.tv", 1)
_m61c = mc.backdrop_count_message(2, 12, "TMDB", 9)
check("B61: the same number / one / more", "(the same number)" in _m61[0] and _m61[1] == "Replace" and _m61[2] is False
      and "the best one" in _m61b[0] and "(7 more)" in _m61c[0], (_m61, _m61b, _m61c))
check("B61: without n the old B17 texts are unchanged", mc.backdrop_count_message(14, 8)[0] == "You have 14 backdrops. TMDB offers 8.\nReplacing would leave you with 8 (6 fewer).")
check("B61: the number shown at first = the movie's current count, at most what is offered; all when it has none",
      (mc.backdrop_count_default(6, 12), mc.backdrop_count_default(14, 8), mc.backdrop_count_default(0, 9)) == (6, 8, 9))

section("2zu. image fix in the background, real-freeze guards (v0.19.3 B62)")   ### NEW v0.19.3 B62 ###
_t62 = time.monotonic()
_st62 = mc._run_ffmpeg([sys.executable, "-c", "import time; time.sleep(60)"], timeout=30, hung_after=1.5)
_dt62 = time.monotonic() - _t62
if sys.platform == "win32": check("B62: a child that uses no CPU is stopped as hung (FF_HUNG) after the hung time, not after the timeout",
      _st62[0] == mc.FF_HUNG and _dt62 < 12, (_st62[0], round(_dt62, 1)))
_st62 = mc._run_ffmpeg([sys.executable, "-c", "print('ok')"], timeout=60, priority="idle", hung_after=45)   # v0.19.5: on a busy PC an idle-priority child can wait over 5 s to start
check("B62: IDLE priority run works and returns the output", _st62[0] == mc.FF_OK and "ok" in _st62[2], _st62[:3])
_ifp62 = dict(mc.SETTINGS.get("image_fix_prefs") or {})
try:
    mc.SETTINGS["image_fix_prefs"] = dict(_ifp62, ai_mode="gentle")
    _g62 = mc.upscaler_cmd("in.png", "out.png")
    mc.SETTINGS["image_fix_prefs"] = dict(_ifp62, ai_mode="fast")
    _f62 = mc.upscaler_cmd("in.png", "out.png")
    mc.SETTINGS["image_fix_prefs"] = dict(_ifp62)
    _d62 = mc.upscaler_mode()
finally:
    mc.SETTINGS["image_fix_prefs"] = _ifp62
check("B62: AI 'gentle' (default) adds 256-px tiles and one thread each; 'fast' does not",
      _g62[-4:] == ["-t", "256", "-j", "1:1:1"] and "-t" not in _f62 and _d62 == "gentle", (_g62, _f62, _d62))
check("B62: thread stacks for the watchdog name the threads", "--- thread MainThread" in mc.format_thread_stacks())
_d62i = os.path.join(_TMP, "b62", "Stop Movie (2004)"); os.makedirs(_d62i, exist_ok=True)
open(os.path.join(_d62i, "Stop Movie (2004).mkv"), "wb").write(b"\0" * 64)
_jpeg(os.path.join(_d62i, "poster.jpg"), 800, 1000)
_p62 = open(os.path.join(_d62i, "poster.jpg"), "rb").read()
_r62 = scan(_d62i, use_ffprobe=False)
try:
    mc.apply_image_fix(_r62, "poster", "blur", (1000, 1500), None, None, lambda: True)
    _e62 = ""
except Exception as _ex:
    _e62 = type(_ex).__name__
check("B62: Stop before writing → ImageFixStopped, the image is unchanged",
      _e62 == "ImageFixStopped" and open(os.path.join(_d62i, "poster.jpg"), "rb").read() == _p62, _e62)

section("2zv. sort builder — levels, empty last, tie-break, presets, Date added (v0.19.3 B63)")   ### NEW v0.19.3 B63 ###
import sort_engine as _se63
check("B63: sort_engine is pure (no os / tkinter / logging import)",
      not any(m in open(_se63.__file__, encoding="utf-8").read() for m in ("import os", "import tkinter", "import logging")))
check("B63: every sort key has a value function (all 21 columns + Health, Number of issues, Date added)",
      set(mc.SORT_VALUE_FNS) == set(_se63.KIND) and len(_se63.COLUMNS) == 21 and len(_se63.MORE) == 3, set(_se63.KIND) ^ set(mc.SORT_VALUE_FNS))
def _row63(name, year="2001", **kw):
    r = {"movie_name": name, "subfolder": name, "movie_year": year, "rating_value": -1.0, "rating_status": mc.STATUS_MISSING,
         "poster_quality": "—", "health_status": "ok", "health_reasons": []}
    r.update(kw); return r
def _order63(rows, spec):
    return [r["movie_name"] for r in _se63.sort_rows(rows, spec, mc.SORT_VALUE_FNS, mc._sort_name_key, mc._sort_year_key)]
_rt = lambda v: {"rating_value": v, "rating_status": mc.STATUS_OK}
_rows63 = [_row63("Bravo", **_rt(7.0)), _row63("Alpha", **_rt(7.0)), _row63("Empty"), _row63("Charlie", **_rt(9.0))]
check("B63: High → low — equal ratings stay A → Z (the old tie-break bug), no rating last",
      _order63(_rows63, [{"key": "rating", "dir": "high"}]) == ["Charlie", "Alpha", "Bravo", "Empty"], _order63(_rows63, [{"key": "rating", "dir": "high"}]))
check("B63: Low → high — empty values still last",
      _order63(_rows63, [{"key": "rating", "dir": "low"}]) == ["Alpha", "Bravo", "Charlie", "Empty"])
check("B63: 'empty first' (the Missing metadata preset) puts the empty ones first",
      _order63(_rows63, [{"key": "rating", "dir": "low", "empty": "first"}])[0] == "Empty")
# the mock-up's example: Poster worst first, then Rating high → low
_mk = [("Interstellar", "1080p", 8.7), ("Parasite", "1080p", 8.5), ("Amélie", "720p", 8.3), ("Blade Runner", "720p", 8.1),
       ("Bacurau", "720p", None), ("Central do Brasil", "360p", 8.0), ("O Auto da Compadecida", "360p", 8.6), ("Cidade de Deus", "360p", 8.6)]
_rows63b = [_row63(n, poster_quality=q, **(_rt(v) if v is not None else {})) for n, q, v in _mk]
_o63 = _order63(_rows63b, [{"key": "poster", "dir": "worst"}, {"key": "rating", "dir": "high"}])
check("B63: the mock-up's order (Poster worst first › Rating high → low)",
      _o63 == ["Cidade de Deus", "O Auto da Compadecida", "Central do Brasil", "Amélie", "Blade Runner", "Bacurau",
               "Interstellar", "Parasite"], _o63)
check("B63: accents do not change the name order (Élan sorts with E)",
      _order63([_row63("Fargo"), _row63("Élan"), _row63("Delta")], [{"key": "movie_name", "dir": "asc"}]) == ["Delta", "Élan", "Fargo"])
check("B63: every old 'Sort:' text migrates to a level, unknown text → Movie Name A → Z, and back",
      all(_se63.spec_from_old(t)[0]["key"] in _se63.KIND for t in _se63.OLD_SORT_OPTIONS)
      and _se63.spec_from_old("nonsense") == [{"key": "movie_name", "dir": "asc"}]
      and all(_se63.old_text_for(_se63.spec_from_old(t)) == t for t in _se63.OLD_SORT_OPTIONS))
_ms63 = {"sort_option": "Rating (high→low)", "settings_migrations": []}
_sp63 = mc.sort_spec_from_settings(_ms63)
check("B63: first start — the old sort_option becomes the sort, once",
      _sp63 == [{"key": "rating", "dir": "high"}] and "b63_sort_spec" in _ms63["settings_migrations"]
      and mc.sort_spec_from_settings(dict(_ms63, sort_spec=[{"key": "year", "dir": "oldest"}])) == [{"key": "year", "dir": "oldest"}])
_c63 = _se63.click_heading([{"key": "movie_name", "dir": "asc"}], "rating")
_c63b = _se63.click_heading(_c63, "rating")
_c63c = _se63.click_heading(_c63b, "year", shift=True)
_c63d = _se63.click_heading(_se63.click_heading(_c63c, "votes", shift=True), "genre", shift=True)
check("B63: heading click → level 1 (old ones follow); again → reversed; Shift+click → next level; a 4th replaces level 3",
      [l["key"] for l in _c63] == ["rating", "movie_name"] and _c63b[0]["dir"] != _c63[0]["dir"]
      and [l["key"] for l in _c63c] == ["rating", "movie_name", "year"]
      and [l["key"] for l in _c63d] == ["rating", "movie_name", "genre"], (_c63, _c63b, _c63c, _c63d))
check("B63: summary line and heading marks",
      _se63.describe([{"key": "poster", "dir": "worst"}, {"key": "rating", "dir": "high"}])
      == "Sorted by Poster quality (worst first), then Rating (high → low), then Movie Name (A → Z) · empty values last"
      and _se63.heading_marks([{"key": "poster", "dir": "worst"}, {"key": "rating", "dir": "low"}]) == {"poster": "▼1", "rating": "▲2"})
check("B63: preset names — unique, not a built-in name, at most 20",
      _se63.valid_preset_name("Best rated", []) != "" and _se63.valid_preset_name("Mine", [{"name": "mine", "levels": []}]) != ""
      and _se63.valid_preset_name("Mine", [{"name": f"p{i}", "levels": []} for i in range(20)]) != ""
      and _se63.valid_preset_name("Mine", []) == "" and len(_se63.BUILTIN_PRESETS) == 7)   # 7: v0.19.4 fix 16 (By collection name)
check("B63: dates — '2021-05-03 12:00', '5/3/2021' read; nonsense ignored",
      (mc._date_text("2021-05-03 12:00:00"), mc._date_text("5/3/2021 9:00 PM"), mc._date_text("yesterday"), mc._date_text("0000-00-00"))
      == ("2021-05-03", "2021-05-03", None, None))
# ### NEW v0.19.5 B124 ### day/month or month/day
import datetime as _dt124
_n124 = _dt124.datetime(2026, 11, 5).timestamp()
check("B124: 03/11/2026 written in November is 3 November; a number over 12 decides in both orders; an ISO date is unchanged; no file date: month/day",
      (mc._date_text("03/11/2026", _n124), mc._date_text("15/11/2026", _n124), mc._date_text("11/15/2026", _n124), mc._date_text("2026-03-11", _n124), mc._date_text("03/11/2026"))
      == ("2026-11-03", "2026-11-15", "2026-11-15", "2026-03-11", "2026-03-11"))
# ### NEW v0.19.5 B123, WR-A5 ### the rating shown is Kodi's
_p123 = os.path.join(_TMP, "b123.nfo")
def _r123(t):
    io.open(_p123, "w", encoding="utf-8", newline="\n").write(t)
    return mc.extract_rating_from_files(_p123, None)
_blk123 = '<ratings><rating name="imdb" default="true"><value>8.8</value><votes>100</votes></rating></ratings>'
_a123, _b123, _c123, _d123 = (_r123(f"<movie><rating>8.8</rating><votes>100</votes>{_blk123}</movie>"), _r123(f"<movie><rating>7.4</rating><votes>9</votes>{_blk123}</movie>"),
                              _r123(f"<movie>{_blk123}</movie>"), _r123("<movie><rating>7.4</rating></movie>"))
check("B123: both tags equal: no conflict; different: the block's value and a conflict; each alone is read",
      (_a123[0], _a123[1]) == ("8.8", mc.STATUS_OK) and (_b123[0], _b123[1], _b123[3]) == ("8.8", mc.STATUS_WARN, 100) and _c123[0] == "8.8" and _d123[0] == "7.4", (_a123, _b123, _c123, _d123))
_x123 = os.path.join(_TMP, "b123.xml")
io.open(_x123, "w", encoding="utf-8", newline="\n").write("<Title>\n  <LocalTitle>X</LocalTitle>\n</Title>\n")
_e123 = mc.write_rating_to_files(None, _x123, "7.0", "50", backup=False)
_t123 = io.open(_x123, encoding="utf-8").read()
io.open(_p123, "w", encoding="utf-8", newline="\n").write("<movie>\n  <rating />\n  <votes />\n</movie>\n")
mc.write_rating_to_files(_p123, None, "7.0", "50", backup=False)
_t123b = io.open(_p123, encoding="utf-8").read()
check("WR-A5: a movie.xml with no rating tags gets them inside its root; an empty <rating /> is filled in place",
      not _e123 and "<Rating>7.0</Rating>" in _t123 and "<Votes>50</Votes>" in _t123 and _t123.rstrip().endswith("</Title>")
      and "<rating>7.0</rating>" in _t123b and "<votes>50</votes>" in _t123b and _t123b.count("<rating") == 1, (_t123, _t123b))
_d63 = os.path.join(_TMP, "b63", "Dated (2001)"); os.makedirs(_d63, exist_ok=True)
_nfo(os.path.join(_d63, "movie.nfo"), "Dated", extra="\t<dateadded>2020-01-02 03:04:05</dateadded>\n")
_xml(os.path.join(_d63, "movie.xml"), "Dated", extra="\t<DateAdded>2019-09-09</DateAdded>\n")
open(os.path.join(_d63, "Dated (2001).mkv"), "wb").write(b"\0" * 64)
_s63 = scan(_d63, use_ffprobe=False)
_x63 = mc.date_added_for(None, os.path.join(_d63, "movie.xml"), None, None)
_v63 = mc.date_added_for(None, None, os.path.join(_d63, "Dated (2001).mkv"), _d63)
_f63 = mc.date_added_for(None, None, None, _d63)
check("B63: Date added — NFO <dateadded> first, then XML <DateAdded>, then the video, then the folder",
      (_s63["date_added"], _s63["date_added_src"]) == ("2020-01-02", "nfo") and _x63 == ("2019-09-09", "xml")
      and _v63[1] == "video" and len(_v63[0]) == 10 and _f63[1] == "folder", (_s63.get("date_added"), _x63, _v63, _f63))
import random as _rnd63
_big63 = [_row63(f"Movie {i:05d}", year=str(1950 + i % 70), poster_quality=["4K", "1080p", "720p", "360p", "—"][i % 5],
                 health_status=["ok", "warning", "error"][i % 3], **(_rt(round(_rnd63.random() * 10, 1)) if i % 7 else {}))
          for i in range(10000)]
_t63 = time.perf_counter()
_ = _se63.sort_rows(_big63, [{"key": "health", "dir": "errors"}, {"key": "poster", "dir": "worst"}, {"key": "rating", "dir": "high"}],
                    mc.SORT_VALUE_FNS, mc._sort_name_key, mc._sort_year_key)
_dt63 = time.perf_counter() - _t63
if sys.platform == "win32": check(f"B63: 10,000 rows, 3 levels sorted in {_dt63 * 1000:.0f} ms (< 150 ms)", _dt63 < 0.15, round(_dt63, 3))

section("2zw. 'Not a duplicate' (v0.19.3 B64)")   ### NEW v0.19.3 B64 ###
def _r64(name, path, imdb="", tmdb="", year="2001", title=None):
    return {"movie_name": title or name, "subfolder": name, "subfolder_path": path, "movie_year": year,
            "source_imdb_val": imdb, "source_tmdb_val": tmdb}
_a64 = _r64("Hamlet A", r"Z:\Lib\Hamlet A", imdb="tt1000001", title="Hamlet", year="1996")
_b64 = _r64("Hamlet B", r"Z:\Lib\Hamlet B", imdb="tt1000002", title="Hamlet", year="1996")
_c64 = _r64("Hamlet C", r"Z:\Lib\Hamlet C", imdb="", title="Hamlet", year="1996")
mc._detect_duplicates([_a64, _b64, _c64], marks=set())
check("B64: same title + year with DIFFERENT IMDb IDs is not a duplicate (user decision); without an ID it still is",
      _a64["duplicate_of"] == ["Hamlet C"] and _b64["duplicate_of"] == ["Hamlet C"] and sorted(_c64["duplicate_of"]) == ["Hamlet A", "Hamlet B"],
      (_a64["duplicate_of"], _b64["duplicate_of"], _c64["duplicate_of"]))
_x64 = [_r64(n, rf"Z:\Lib\{n}", imdb="tt2000001") for n in ("Copy 1", "Copy 2", "Copy 3")]
_m64 = {mc._not_dup_key(_x64[0]["subfolder_path"], _x64[1]["subfolder_path"])}
mc._detect_duplicates(_x64, marks=_m64)
check("B64: a marked pair loses the flag; a third copy is still flagged against both",
      _x64[0]["duplicate_of"] == ["Copy 3"] and _x64[1]["duplicate_of"] == ["Copy 3"] and _x64[2]["duplicate_of"] == ["Copy 1", "Copy 2"],
      [x["duplicate_of"] for x in _x64])
_m64 |= {mc._not_dup_key(_x64[0]["subfolder_path"], _x64[2]["subfolder_path"]), mc._not_dup_key(_x64[1]["subfolder_path"], _x64[2]["subfolder_path"])}
mc._detect_duplicates(_x64, marks=_m64)
check("B64: every pair marked → nobody flagged", not any(x["duplicate_of"] for x in _x64))
if sys.platform == "win32": check("B64: the pair key ignores order, case and slashes",
      mc._not_dup_key(r"Z:\Lib\A", "z:/lib/b") == mc._not_dup_key("Z:/LIB/B", r"z:\lib\a"))
_nd0 = mc._NOT_DUP["pairs"]
try:
    mc._sc.save_not_duplicates([{"a": "x", "b": "y", "why": "Same IMDb ID tt1", "at": "2026-10-23 10:00"}])
    mc._NOT_DUP["pairs"] = None
    _ld64 = mc.not_dup_pairs()
    open(mc._sc.NOT_DUP_PATH, "w", encoding="utf-8").write("{ broken")
    mc._NOT_DUP["pairs"] = None
    _bad64 = mc.not_dup_pairs()
    _kept64 = [n for n in os.listdir(os.path.dirname(mc._sc.NOT_DUP_PATH)) if n.startswith("not_duplicates.json.corrupt-")]
    check("B64: marks saved and read back; a broken file is kept as .corrupt-<date> and the marks start empty",
          _ld64 and _ld64[0]["a"] == "x" and _bad64 == [] and _kept64, (_ld64, _bad64, _kept64))
    check("B64: the file lives in the config folder (isolated in the self-test)",
          os.path.dirname(mc._sc.NOT_DUP_PATH) == mc._sc.get_config_dir())
finally:
    for n in os.listdir(os.path.dirname(mc._sc.NOT_DUP_PATH)):
        if n.startswith("not_duplicates.json"):
            os.remove(os.path.join(os.path.dirname(mc._sc.NOT_DUP_PATH), n))
    mc._NOT_DUP["pairs"] = None
check("B64: ⚠ Fix issues key 'dup' for 'Possible duplicate of: …'",
      "dup" in mc._fix_issue_keys({"health_reasons": ["Possible duplicate of: Perfect Movie"]}))

section("2zx. previews before writing (v0.19.3 I6)")   ### NEW v0.19.3 I6 ###
_ps6 = mc.sources_preview_text([
    {"movie_name": "Same Id", "source_imdb_status": mc.STATUS_WARN, "source_imdb_all": ["tt1234567", ""], "source_tmdb_status": mc.STATUS_OK},
    {"movie_name": "Two Ids", "source_imdb_status": mc.STATUS_WARN, "source_imdb_all": ["tt1", "tt2"], "source_tmdb_status": mc.STATUS_OK},
    {"movie_name": "No Id", "source_imdb_status": mc.STATUS_OK, "source_tmdb_status": mc.STATUS_MISSING, "source_tmdb_all": []}])
check("I6: Normalize Sources preview — copied / you will be asked which / you will be asked to type",
      "tt1234567 → copied" in _ps6 and "the IDs differ (tt1 / tt2)" in _ps6 and "TMDB: no ID — you will be asked to type one" in _ps6, _ps6)
_pc6 = mc.copy_poster_preview_text([{"movie_name": "A", "folder_exists": True, "folder_size": "120 KB", "poster_path": r"x\poster.jpg", "poster_size": "300 KB"},
                                    {"movie_name": "B", "folder_exists": False, "poster_path": r"y\poster.jpg", "poster_size": "200 KB"}])
if sys.platform == "win32": check("I6: Copy poster → folder preview names every folder.jpg (overwritten / created)",
      "A:  folder.jpg (120 KB) ← poster.jpg (300 KB)" in _pc6 and "B:  no folder.jpg → created from poster.jpg (200 KB)" in _pc6, _pc6)
_pg6 = mc.genres_preview_text([{"movie_name": "Old Genres", "genres": ["Sci-Fi"]}, {"movie_name": "No Genres", "genres": []}])
check("I6: Normalize Genres preview — current → normalized; no genres → looked up online",
      "Old Genres:  Sci-Fi  →  Science Fiction" in _pg6 and "1 movie has no genres" in _pg6, _pg6)
_pr6 = mc.ratings_preview_text([({"rating_str": "7.3", "votes_int": 1200}, "Rated", None, None, ("8.1", "1234", "TMDB"))])
check("I6: Sync Ratings preview — current → new with the source", "Rated:  7.3 / 1200 votes  →  8.1 / 1234 votes  (TMDB)" in _pr6, _pr6)

section("2zy. NFO / XML content checks (v0.19.3 I8)")   ### NEW v0.19.3 I8 ###
_d8 = os.path.join(_TMP, "i8", "Struct Movie (1999)"); os.makedirs(_d8, exist_ok=True)
io.open(os.path.join(_d8, "movie.nfo"), "w", encoding="utf-8", newline="\n").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<movie>\n\t<title>Struct Movie</title>\n\t<title>Struct Movie</title>\n'
    '\t<year>19999</year>\n\t<rating>85</rating>\n\t<votes>12k</votes>\n\t<imdbid>tt0133093/</imdbid>\n'
    '\t<tmdbid>603a</tmdbid>\n\t<plot></plot>\n</movie>\n')
io.open(os.path.join(_d8, "movie.xml"), "w", encoding="utf-8", newline="\n").write(
    '<?xml version="1.0" encoding="utf-8"?>\n<Movie>\n\t<LocalTitle>Struct Movie</LocalTitle>\n\t<IMDB>tt123</IMDB>\n</Movie>\n')
open(os.path.join(_d8, "Struct Movie (1999).mkv"), "wb").write(b"\0" * 64)
_s8 = scan(_d8, use_ffprobe=False)
_k8 = sorted({k for k, _m in _s8["struct_issues"]})
check("I8: every rule finds its problem (IDs, year, numbers, duplicate tag, empty tag, root)",
      _k8 == ["duplicate_single_tag", "empty_required_tag", "id_format_invalid", "numeric_field_invalid", "unexpected_root", "year_out_of_range"],
      _s8["struct_issues"])
_txt8 = " | ".join(m for _k, m in _s8["struct_issues"])
check("I8: the messages name the file, tag and value",
      "NFO: <imdbid> 'tt0133093/' is not a valid IMDb ID" in _txt8 and "XML: <IMDB> 'tt123'" in _txt8 and "NFO: <tmdbid> '603a'" in _txt8
      and "year 19999 is out of range" in _txt8 and "<rating> 85 is not on a 0–10 scale" in _txt8 and "<votes> '12k' is not a whole number" in _txt8
      and "NFO: <title> appears 2 times" in _txt8 and "XML: the root element is <Movie>" in _txt8, _txt8)
check("I8: the warnings appear in the health reasons; 'empty tag' is OFF by default",
      any("tt0133093/" in x for x in _s8["health_reasons"]) and not any("is empty" in x for x in _s8["health_reasons"]), _s8["health_reasons"])
check("I8: Auto Repair plans the safe fix (ID with junk around it, the same line twice)",
      _s8["struct_fixable"] is True and "struct_fix" in [c for c, _l in mc._auto_repair_plan(_s8)])
_nb8 = open(_s8["nfo_path"], "rb").read()
_bk8 = []
_r8 = mc.App._ar_struct_fix(None, {"nfo": _s8["nfo_path"], "xml": _s8["xml_path"], "backup": lambda: _bk8.append(1)})
_na8 = open(_s8["nfo_path"], "rb").read()
check("I8: struct_fix trims 'tt0133093/' and drops the repeated <title> line; everything else is untouched; backup first",
      _r8[0] == "fixed" and b"<imdbid>tt0133093</imdbid>" in _na8 and _na8.count(b"<title>") == 1 and b"<tmdbid>603a</tmdbid>" in _na8
      and _bk8 and len(_na8.split(b"\n")) == len(_nb8.split(b"\n")) - 1, (_r8, _na8[:300]))
_s8b = scan(_d8, use_ffprobe=False)
check("I8: after the fix those two problems are gone (the rest stays reported)",
      not any("tt0133093/" in m or "appears 2 times" in m for _k, m in _s8b["struct_issues"]) and any("603a" in m for _k, m in _s8b["struct_issues"]),
      _s8b["struct_issues"])
check("I8: a clean fixture has no content problems", not scan(M_OK, use_ffprobe=False)["struct_issues"], scan(M_OK, use_ffprobe=False)["struct_issues"])

section("2zz. read cache forgets written files; backup clean-up switch (v0.19.3 I11 / I12)")   ### NEW v0.19.3 I11 / I12 ###
_d11 = os.path.join(_TMP, "i11"); os.makedirs(_d11, exist_ok=True)
_p11 = os.path.join(_d11, "movie.nfo")
io.open(_p11, "w", encoding="utf-8", newline="\n").write("<movie>\n\t<rating>7.5</rating>\n</movie>\n")
_st11 = os.stat(_p11)
_ = mc._read_text(_p11); _ = mc._parse_root(_p11)
mc._atomic_write_text(_p11, "<movie>\n\t<rating>7.6</rating>\n</movie>\n")
os.utime(_p11, ns=(_st11.st_atime_ns, _st11.st_mtime_ns))           # same size, same mtime: a 2-s-mtime share
check("I11: a same-size write with the same mtime is seen at once (cache forgotten by the writer)",
      os.stat(_p11).st_size == _st11.st_size and "7.6" in mc._read_text(_p11) and mc._parse_root(_p11).findtext("rating") == "7.6",
      mc._read_text(_p11))
mc._IMG_WH_CACHE[(os.path.join(_d11, "poster.jpg"), (1, 2))] = (10, 10)
mc._cache_forget(os.path.join(_d11, "POSTER.jpg"))
if sys.platform == "win32": check("I11: image facts are forgotten too (case-insensitive path)", not any(k[0].endswith("poster.jpg") for k in mc._IMG_WH_CACHE if k[0].startswith(_d11)))
_b12 = os.path.join(_TMP, "i12"); os.makedirs(os.path.join(_b12, "backup_Old_2020-01-01_00-00-00", "extrafanart"), exist_ok=True)
time.sleep(0.3)                                  # distinct creation times: "oldest first" must not tie
os.makedirs(os.path.join(_b12, "backup_New_2026-01-01_00-00-00"), exist_ok=True)
open(os.path.join(_b12, "backup_Old_2020-01-01_00-00-00", "extrafanart", "a.jpg"), "wb").write(b"\0" * (2 * 1024 * 1024))
open(os.path.join(_b12, "backup_New_2026-01-01_00-00-00", "b.nfo"), "wb").write(b"\0" * 10)
sc.clean_backup_folder_if_needed(_b12, {"max_backup_size_mb": 1, "backup_cleanup_enabled": False})
_after_off = sorted(os.listdir(_b12))
sc.clean_backup_folder_if_needed(_b12, {"max_backup_size_mb": 1, "backup_cleanup_enabled": True})
_after_on = sorted(os.listdir(_b12))
check("I12: switch OFF → nothing deleted over the limit; ON → the oldest goes (its 2 MB in a sub-folder are counted)",
      len(_after_off) == 2 and _after_on == ["backup_New_2026-01-01_00-00-00"], (_after_off, _after_on))

section("2zzc. last_results.json read row by row (v0.19.3 I4)")   ### NEW v0.19.3 I4 ###
_lr4 = os.path.join(_TMP, "i4_cache.json")
_o4 = sc.RESULTS_CACHE_PATH
try:
    sc.RESULTS_CACHE_PATH = _lr4
    _rows4 = [{"subfolder": f"M{i}", "x": [1, {"y": "a,]b"}], "t": "é\n"} for i in range(450)]
    json.dump(_rows4, open(_lr4, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    _same4 = sc.load_results_cache_stepwise() == _rows4 == sc.load_results_cache()
    open(_lr4, "w", encoding="utf-8").write('[{"a": 1}, {"b": 2')
    _bad4 = sc.load_results_cache_stepwise()
    open(_lr4, "w", encoding="utf-8").write("[]")
    _empty4 = sc.load_results_cache_stepwise()
finally:
    sc.RESULTS_CACHE_PATH = _o4
check("I4: the row-by-row reader gives the same rows; a truncated file → [], an empty list → []",
      _same4 and _bad4 == [] and _empty4 == [], (_same4, _bad4, _empty4))

section("2zza. the health engine as a list of rule functions (v0.19.3 I7)")   ### NEW v0.19.3 I7 ###
check("I7: compute_movie_health_detailed runs HEALTH_RULES in order (no rule left inline)",
      len(mc.HEALTH_RULES) >= 40 and all(f.__name__.startswith("_hr_") for f in mc.HEALTH_RULES)
      and 'rules.get("' not in inspect.getsource(mc.compute_movie_health_detailed), len(mc.HEALTH_RULES))
check("I7: each rule function has the same signature (row, rules, settings, error_reasons, warning_reasons)",
      all(list(inspect.signature(f).parameters) == ["row", "rules", "settings", "error_reasons", "warning_reasons"] for f in mc.HEALTH_RULES))

section("2zzb. tooltips as a dispatch table (v0.19.3 I7)")   ### NEW v0.19.3 I7 ###
check("I7: every table column that had a tooltip has its method (Language never had one) — a dispatch table, no if-chain",
      set(mc._TOOLTIP_METHODS) == {getattr(mc, f"COL_{c['id'].upper()}") for c in mc.COLUMN_MODEL} - {mc.COL_LANGUAGE}
      and all(callable(getattr(mc.App, m, None)) for m in mc._TOOLTIP_METHODS.values())
      and "if ci ==" not in inspect.getsource(mc.App._tooltip), sorted(mc._TOOLTIP_METHODS.values()))

section("2zzd. poster.jpg and folder.jpg fixed together (v0.19.3 B66, B67)")   ### NEW v0.19.3 B66 / B67 ###
def _pair66(name, pw=(486, 640), fw=(477, 629)):
    d = os.path.join(_TMP, "b66", name); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, name + ".mkv"), "wb").write(b"\0" * 64)
    _pic4(*pw, seed=3).save(os.path.join(d, "poster.jpg"), "JPEG", quality=90)
    _pic4(*fw, seed=7).save(os.path.join(d, "folder.jpg"), "JPEG", quality=90)
    _pic4(1920, 1080).save(os.path.join(d, "fanart.jpg"), "JPEG", quality=90)
    return d
def _same66(d):
    return open(os.path.join(d, "poster.jpg"), "rb").read() == open(os.path.join(d, "folder.jpg"), "rb").read()
_all_rules66 = {k: (True if isinstance(v, bool) else v) for k, v in (mc.SETTINGS.get("health_rules") or {}).items()}
def _img_warn66(r):
    _st, _er, _wr = mc.compute_movie_health_detailed(r, _all_rules66, mc.SETTINGS)
    return [x for x in _er + _wr if "proportion" in x.lower() or "poster and folder" in x.lower()]
# the user's case (2026-10-23): two different pictures, both 0.76, fixed one after the other
_d66 = _pair66("Doutrina Case (2018)")
_r66 = scan(_d66, use_ffprobe=False)
check("B66: fixture = the user's case (poster and folder.jpg two different pictures, both wrong proportions)",
      mc.image_fix_kinds(_r66) == ["poster", "folder"] and mc._poster_folder_differ(_r66), mc.image_fix_kinds(_r66))
check("B66: 'Also copy the result to …' is offered for poster → folder and folder → poster, not for fanart or a missing file",
      mc.image_fix_copy_default(_r66, "poster") == "folder" and mc.image_fix_copy_default(_r66, "folder") == "poster"
      and mc.image_fix_copy_default(_r66, "fanart") is None
      and mc.image_fix_copy_default(dict(_r66, folder_exists=False), "poster") is None)
_old_runs66 = {r['name'] for r in sc.list_backup_runs(_BK)}
# ### NEW v0.19.5 WR-B6, WR-C2 ###
_d_b6 = os.path.join(_TMP, "b6", "Fix Later (2001)"); os.makedirs(_d_b6, exist_ok=True)
io.open(os.path.join(_d_b6, "Fix Later (2001).mkv"), "wb").write(b"\0" * 64)
_jpeg(os.path.join(_d_b6, "poster.jpg"), 800, 800); _jpeg(os.path.join(_d_b6, "folder.jpg"), 300, 300)
_fo_b6 = os.path.join(_d_b6, "folder.jpg"); os.chmod(_fo_b6, 0o444)
_rw_b6 = scan(_d_b6, use_ffprobe=False)
_w_b6 = mc.apply_image_fix(_rw_b6, "poster", "blur", (1000, 1500), copy_to="folder")
from PIL import Image as _Im_b6
with _Im_b6.open(os.path.join(_d_b6, "poster.jpg")) as _i_b6:
    _sz_b6 = _i_b6.size
os.chmod(_fo_b6, 0o666)
if sys.platform == "win32": check("WR-B6: folder.jpg cannot be written: the poster IS changed, and the result says what was not done", _sz_b6 == (1000, 1500) and getattr(_w_b6, "problems", None) and "folder.jpg" in _w_b6.problems[0], (_sz_b6, getattr(_w_b6, "problems", None)))
_d_c2 = os.path.join(_TMP, "c2", "Web Pic (2001)"); os.makedirs(_d_c2, exist_ok=True)
io.open(os.path.join(_d_c2, "Web Pic (2001).mkv"), "wb").write(b"\0" * 64)
_Im_b6.new("RGB", (800, 800), (9, 9, 9)).save(os.path.join(_d_c2, "poster.webp"), "WEBP")
_bw_c2 = open(os.path.join(_d_c2, "poster.webp"), "rb").read()
_rw_c2 = scan(_d_c2, use_ffprobe=False); _ref_c2 = [None]
mc.apply_image_fix(_rw_c2, "poster", "blur", (1000, 1500), batch_ref=_ref_c2)
_before_c2 = sorted(os.listdir(_d_c2))
mc._sc.restore_backup_run(mc._BACKUP_ROOT, _ref_c2[0])
check("WR-C2: Undo of a fixed .webp: the new poster.jpg goes, the webp is back with its bytes", "poster.jpg" in _before_c2 and "poster.jpg" not in os.listdir(_d_c2)
      and open(os.path.join(_d_c2, "poster.webp"), "rb").read() == _bw_c2, (_before_c2, os.listdir(_d_c2)))
_old_runs66 = {r['name'] for r in sc.list_backup_runs(_BK)}   # again: the two checks above made runs
_w66 = mc._with_backup_action(mc.IMAGE_FIX_ACTION, mc.apply_image_fix, _r66, "poster", "blur", (1000, 1500),
                              None, None, None, "folder")
_r66b = scan(_d66, use_ffprobe=False)
_runs66 = [r for r in sc.list_backup_runs(_BK) if r['name'] not in _old_runs66]   # the run(s) this fix made
_orig66 = sorted(os.path.basename(f["original"]) for f in (_runs66[0]["files"] if _runs66 else []))
check("B66: ticked (poster) → poster.jpg fixed AND copied to folder.jpg: same bytes, 1000×1500, ONE backup run with both files",
      [os.path.basename(p) for p in _w66] == ["poster.jpg", "folder.jpg"] and _same66(_d66)
      and _r66b["folder_dim"] == "1000×1500" and len(_runs66) == 1 and _orig66 == ["folder.jpg", "poster.jpg"],
      (_w66, _r66b["folder_dim"], _orig66))
check("B67: the user's case after ONE fix with the box ticked: no image warning, every rule on (also 'Poster and folder image are different')",
      _img_warn66(_r66b) == [], _img_warn66(_r66b))
_d66u = _pair66("Unticked (2019)")
_f66u = open(os.path.join(_d66u, "folder.jpg"), "rb").read()
_w66u = mc.apply_image_fix(scan(_d66u, use_ffprobe=False), "poster", "blur", (1000, 1500), copy_to=False)
check("B66: unticked → only poster.jpg written, folder.jpg untouched",
      [os.path.basename(p) for p in _w66u] == ["poster.jpg"] and open(os.path.join(_d66u, "folder.jpg"), "rb").read() == _f66u)
_r66u = scan(_d66u, use_ffprobe=False)
check("B67: the warning that stays says how to clear it ('— Copy poster → folder makes them the same') and ⚠ Fix issues offers 'copy'",
      any(x.startswith("Poster and folder image are different") and "Copy poster → folder makes them the same" in x for x in _img_warn66(_r66u))
      and "copy" in mc._fix_issue_keys(dict(_r66u, health_reasons=_img_warn66(_r66u))), _img_warn66(_r66u))
_d66f = _pair66("Folder First (2020)")
_w66f = mc.apply_image_fix(scan(_d66f, use_ffprobe=False), "folder", "blur", (1000, 1500), copy_to="poster")
check("B66: folder.jpg chosen + ticked → folder.jpg fixed and copied to poster.jpg",
      [os.path.basename(p) for p in _w66f] == ["folder.jpg", "poster.jpg"] and _same66(_d66f))
_d66i = _pair66("Identical (2021)", fw=(486, 640))
shutil.copy2(os.path.join(_d66i, "poster.jpg"), os.path.join(_d66i, "folder.jpg"))
_w66i = mc.apply_image_fix(scan(_d66i, use_ffprobe=False), "poster", "blur", (1000, 1500))
check("B66: copy_to not given → as before (an identical folder.jpg follows its poster)",
      [os.path.basename(p) for p in _w66i] == ["poster.jpg", "folder.jpg"] and _same66(_d66i))
_d66g = _pair66("Good Folder (2022)", fw=(1500, 2250))
_r66g = scan(_d66g, use_ffprobe=False)
_d66b = _pair66("Batch Pair (2023)", pw=(1100, 1500), fw=(1110, 1500))
_r66bt = scan(_d66b, use_ffprobe=False)
_plan66 = mc.image_fix_batch_plan([_r66bt, _r66g])
check("B66 batch: poster + a folder.jpg that needs a fix → ONE poster line '(+ copied to folder.jpg)'; a good different folder.jpg is left alone",
      [(os.path.basename(r["subfolder_path"]), k) for r, k, *_ in _plan66] == [("Batch Pair (2023)", "poster"), ("Good Folder (2022)", "poster")]
      and mc.image_fix_batch_copy(_r66bt, "poster") == "folder" and mc.image_fix_batch_copy(_r66g, "poster") is False
      and "(+ copied to folder.jpg)" in mc.image_fix_batch_text(_plan66)
      and mc.image_fix_batch_text(_plan66).count("(+ copied to") == 1, mc.image_fix_batch_text(_plan66))

section("2zze. Health first in the sort lists (v0.19.3 B69)")   ### NEW v0.19.3 B69 ###
import sort_engine as _se69
check("B69: the Sort by list starts with Health and Number of issues; every sort key once",
      _se69.MENU_KEYS[:2] == ["health", "issues"] and sorted(_se69.MENU_KEYS) == sorted(_se69.KIND)
      and len(_se69.MENU_KEYS) == len(set(_se69.MENU_KEYS)) and _se69.LABEL["health"] == "Health", _se69.MENU_KEYS[:4])
check("B69: Health directions Errors first → Warnings first → OK first; the old 'Health (Warning 1st)' still migrates",
      _se69.dir_label("health", _se69.default_dir("health")) == "Errors first"
      and _se69.dir_label("health", _se69.next_dir("health", "errors")) == "Warnings first"
      and _se69.next_dir("health", "warnings") == "ok"
      and _se69.spec_from_old("Health (Warning 1st)")[0] == {"key": "health", "dir": "warnings"},
      _se69.spec_from_old("Health (Warning 1st)"))

section("2zzf. ⚠ Fix issues: video quality is not an image problem (v0.19.3 B71)")   ### NEW v0.19.3 B71 ###
_r71 = {"health_reasons": ["Missing IMDb ID (empty tags ready to fill)", "Missing TMDB ID (empty tags ready to fill)",
                           "Video quality below minimum (480p < 720p)", "Required audio language not found (ENG)",
                           "Required subtitle language not found (POR)"]}       # the user's movie, 2026-10-23
_k71 = mc._fix_issue_keys(_r71)
check("B71: the user's Doutrina warnings → no 'Image proportions / size' entry; the video one has its own (greyed) entry",
      "images" not in _k71 and "video" in _k71 and {"ids_search", "audio", "subs"} <= _k71
      and "needs a better copy of the video" in mc._FIX_ISSUE_LABELS["video"] and "video" in mc._FIX_ISSUE_ORDER, sorted(_k71))
check("B71: real image reasons still map to 'images' (proportions, poster/folder and fanart quality, file size)",
      all(mc._fix_issue_keys({"health_reasons": [x]}) & {"images"} for x in (
          "Poster has wrong proportions", "Poster/folder quality below minimum (720p < 1080p)",
          "Fanart quality below minimum (720p < 1080p)", "Fanart image file below minimum size (90 KB < 200 KB)")))
check("B71: the video entry has no action (greyed, 'no automatic fix')",
      mc.App._ctx_fix_action(type("A", (), {})(), "video", [{}]) == (None, "no automatic fix"))

section("2zzg. Rename a folder-named NFO for Kodi (v0.19.3 B73)")   ### NEW v0.19.3 B73 ###
def _mv73(folder, videos, nfo=True, disc=False):
    d = os.path.join(_TMP, "b73", folder); os.makedirs(d, exist_ok=True)
    for i, v in enumerate(videos):
        open(os.path.join(d, v), "wb").write(b"\0" * (1000 + 100 * i))
    if disc:
        os.makedirs(os.path.join(d, "VIDEO_TS"), exist_ok=True)
        open(os.path.join(d, "VIDEO_TS", "VIDEO_TS.IFO"), "wb").write(b"\0" * 64)
        open(os.path.join(d, "VIDEO_TS", "VTS_01_1.VOB"), "wb").write(b"\0" * 4096)
    if nfo:
        _nfo(os.path.join(d, folder + ".nfo"), folder.split(" (")[0], year="2001", imdb="tt7730001", tmdb="773001")
    return d
_d73 = _mv73("One Video (2001)", ["One.Video.2001.1080p.mkv"])
_r73 = scan(_d73, use_ffprobe=False)
_p73 = mc.nfo_rename_plan(_d73)
check("B73: one video → warning 'NFO named after the folder'; plan: <video>.nfo (default) or movie.nfo",
      _r73["nfo_kodi_name"] is False and any(x.startswith("NFO named after the folder") for x in _r73["health_reasons"])
      and _p73["default"] == "video" and [n for _m, _d, n in _p73["choices"]] == ["One.Video.2001.1080p.nfo", "movie.nfo"]
      and _p73["why"] is None, (_p73, _r73["health_reasons"]))
check("B73: ⚠ Fix issues → 'nfo_name'; Auto Repair plans the rename LAST",
      "nfo_name" in mc._fix_issue_keys(_r73) and "Rename NFO for Kodi" in mc._FIX_ISSUE_LABELS["nfo_name"]
      and mc._auto_repair_plan(_r73)[-1][0] == "nfo_name", [c for c, _l in mc._auto_repair_plan(_r73)])
_nb73 = open(_p73["src"], "rb").read()
_old_runs73 = {r["name"] for r in sc.list_backup_runs(_BK)}
_dest73 = mc._with_backup_action(mc.NFO_RENAME_ACTION, mc.apply_nfo_rename, _p73, "video", "One Video")
_r73b = scan(_d73, use_ffprobe=False)
check("B73: A — renamed to One.Video.2001.1080p.nfo (same bytes, old name gone); a rescan: Kodi reads it, no warning",
      os.path.basename(_dest73) == "One.Video.2001.1080p.nfo" and open(_dest73, "rb").read() == _nb73
      and not os.path.exists(_p73["src"]) and _r73b["nfo_kodi_name"] is True
      and not any(x.startswith("NFO named after the folder") for x in _r73b["health_reasons"]), _r73b["health_reasons"])
_run73 = [r for r in sc.list_backup_runs(_BK) if r["name"] not in _old_runs73]
check("B73: one backup run labelled 'Rename NFO for Kodi', the manifest records the new name",
      len(_run73) == 1 and _run73[0]["action"] == mc.NFO_RENAME_ACTION
      and os.path.basename(_run73[0]["files"][0].get("renamed_to") or "") == "One.Video.2001.1080p.nfo",
      _run73[:1])
_res73, _err73, _ = sc.restore_backup_run(_BK, _run73[0]["folder"]) if _run73 else ([], ["no run"], None)
check("B73: Undo puts the old name back and removes the new one",
      not _err73 and os.path.isfile(_p73["src"]) and not os.path.exists(_dest73) and open(_p73["src"], "rb").read() == _nb73,
      (_res73, _err73, os.listdir(_d73)))
_p73m = mc.nfo_rename_plan(_d73)
mc.apply_nfo_rename(_p73m, "movie", "One Video")
check("B73: B — movie.nfo on request", os.path.isfile(os.path.join(_d73, "movie.nfo")) and not os.path.exists(_p73m["src"])
      and scan(_d73, use_ffprobe=False)["nfo_kodi_name"] is True)
_ds73 = _mv73("Stack Film (2002)", ["Stack.Film.cd1.avi", "Stack.Film.cd2.avi"])
_dv73 = _mv73("Versions Film (2003)", ["Versions Film (2003) - 1080p.mkv", "Versions Film (2003) - 2160p.mkv"])
_dd73 = _mv73("Disc Film (2004)", [], disc=True)
_ps73, _pv73, _pd73 = (mc.nfo_rename_plan(x) for x in (_ds73, _dv73, _dd73))
check("B73: multi-part / several versions / DVD folder → movie.nfo by default (with the reason); a DVD gets no <video>.nfo choice",
      _ps73 and _ps73["default"] == "movie" and _ps73["why"] == "multi-part movie"
      and _pv73 and _pv73["default"] == "movie" and _pv73["why"] == "several versions"
      and _pd73 and _pd73["default"] == "movie" and _pd73["why"] == "DVD folder" and [m for m, *_x in _pd73["choices"]] == ["movie"],
      (_ps73, _pv73, _pd73))
_dk73 = _mv73("Kodi Fine (2005)", ["Kodi Fine (2005).mkv"])
check("B73: video named like the folder → nothing to rename (no plan, no Fix issues entry)",
      mc.nfo_rename_plan(_dk73) is None and "nfo_name" not in mc._fix_issue_keys(scan(_dk73, use_ffprobe=False)))
_dc73 = _mv73("Clash Film (2006)", ["Clash.Film.mkv"])
_pc73 = mc.nfo_rename_plan(_dc73)
open(os.path.join(_dc73, "Clash.Film.nfo"), "w", encoding="utf-8").write("<movie><title>Other</title></movie>")
try:
    mc.apply_nfo_rename(_pc73, "video", "Clash Film"); _cl73 = "renamed"
except RuntimeError as ex:
    _cl73 = str(ex)
check("B73: the new name already exists → not renamed (never overwritten), both files kept",
      "already exists" in _cl73 and os.path.isfile(_pc73["src"])
      and "Other" in open(os.path.join(_dc73, "Clash.Film.nfo"), encoding="utf-8").read(), _cl73)
_t73 = mc.nfo_rename_batch_text([({"movie_name": "Stack Film"}, _ps73), ({"movie_name": "One"}, _p73)])
check("B73: preview text — one line per movie 'old → new (reason)' + the movie.nfo note",
      "Stack Film (2002).nfo  →  movie.nfo   (multi-part movie)" in _t73 and "separate folders" in _t73, _t73)

# ══ v0.19.4 pure checks (Part 9a fixes) ══════════════════════════════════════   ### NEW v0.19.4 ###
section("2zzf. v0.19.4 data safety (B80, B76, B75, B79 …)")
_bk80 = os.path.join(_TMP, "b80_backup"); _m80 = os.path.join(_TMP, "b80", "Film"); os.makedirs(_m80, exist_ok=True)
_f80a, _f80b = os.path.join(_m80, "movie.nfo"), os.path.join(_m80, "movie.xml")
for _f, _c in ((_f80a, "<movie>orig a</movie>\n"), (_f80b, "<Item>orig b</Item>\n")):
    io.open(_f, "w", encoding="utf-8", newline="\n").write(_c)
_ref80 = [None]
with sc.backup_action("B80 Run"):
    sc.make_batch_backup(_bk80, "Film", _ref80, _f80a, _f80b)
for _f, _c in ((_f80a, "<movie>changed a</movie>\n"), (_f80b, "<Item>changed b</Item>\n")):
    io.open(_f, "w", encoding="utf-8", newline="\n").write(_c)
_orig_mbb = sc.make_batch_backup
def _mbb80(root, name, ref, *paths, logger=None):          # the safety copy of movie.xml fails
    if any(p.endswith("movie.xml") for p in paths):
        return None
    return _orig_mbb(root, name, ref, *paths, logger=logger)
sc.make_batch_backup = _mbb80
try:
    _res80, _err80, _ = sc.restore_backup_run(_bk80, _ref80[0])
finally:
    sc.make_batch_backup = _orig_mbb
check("B80: Undo leaves a file alone when its own safety backup failed, and names it; the other file is restored",
      _txt(_f80b) == "<Item>changed b</Item>\n" and _txt(_f80a) == "<movie>orig a</movie>\n"
      and len(_err80) == 1 and _err80[0].startswith("movie.xml: not restored") and _res80 == [_f80a], (_res80, _err80))
_orig_wm = sc._write_manifest
def _wm80(folder, m):
    raise OSError("disk full (test)")
sc._write_manifest = _wm80
try:
    _single80 = sc.make_backup(_bk80, "Film", _f80a)
    _batch80 = sc.make_batch_backup(_bk80, "Film", [None], _f80a)
finally:
    sc._write_manifest = _orig_wm
check("B80: a backup whose manifest could not be written does not count (None → the change does not go ahead, B40)",
      _single80 is None and _batch80 is None, (_single80, _batch80))
_bk76 = os.path.join(_TMP, "b76_backup"); _m76 = os.path.join(_TMP, "b76", "Film"); os.makedirs(_m76, exist_ok=True)
_f76 = os.path.join(_m76, "movie.nfo"); io.open(_f76, "w", encoding="utf-8", newline="\n").write("<movie>0</movie>\n")
_r76a, _r76b = [None], [None]
with sc.backup_action("B76 first"):
    sc.make_batch_backup(_bk76, "Film", _r76a, _f76)
io.open(_f76, "w", encoding="utf-8", newline="\n").write("<movie>after run one</movie>\n"); sc.note_written([_m76])
time.sleep(0.05)
with sc.backup_action("B76 second"):
    sc.make_batch_backup(_bk76, "Film", _r76b, _f76)
io.open(_f76, "w", encoding="utf-8", newline="\n").write("<movie>after the second run, longer</movie>\n"); sc.note_written([_m76])
_e76a = sc.read_manifest(_r76a[0])["files"][0]; _e76b = sc.read_manifest(_r76b[0])["files"][0]
check("B76: a later run does not overwrite the older run's 'after' state — restoring the older run warns ('changed since')",
      sc.file_changed_since_run(_e76a) is True and sc.file_changed_since_run(_e76b) is False, (_e76a, _e76b))

_bk75 = os.path.join(_TMP, "b75_backup"); os.makedirs(_bk75, exist_ok=True)
_log75_old = sc.BACKUP_CLEANUP_LOG_PATH
sc.BACKUP_CLEANUP_LOG_PATH = os.path.join(_TMP, "b75_cleanup_log.json")
def _run75(name, created, action):                       # a finished run (not open in this session), 2 MB
    d = os.path.join(_bk75, name); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "a.jpg"), "wb").write(b"\0" * (2 * 1024 * 1024))
    sc._write_manifest(d, {"version": 1, "created": created, "action": action, "run_id": name,
                           "files": [{"original": os.path.join(_TMP, "b75", name, "a.jpg"), "backup": "a.jpg"}]})
    return d
_old75 = _run75("backup_Old_2020-01-01_00-00-00", "2020-01-01 00:00:00", "Delete extrafanart")
_new75 = _run75("backup_Recent_2020-01-02_00-00-00",
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 3 * 86400)), "Ratings Sync")
_m75 = os.path.join(_TMP, "b75", "Film"); os.makedirs(_m75, exist_ok=True)
_f75 = os.path.join(_m75, "fanart.jpg"); open(_f75, "wb").write(b"\0" * (2 * 1024 * 1024))
_r75 = [None]
with sc.backup_action("B75 session run"):
    sc.make_batch_backup(_bk75, "Film", _r75, _f75)
with sc._MF_LOCK:                                         # this session's run, dated long ago: still protected
    sc._OPEN_MANIFESTS[_r75[0]]["created"] = "2019-06-01 00:00:00"
    sc._write_manifest(_r75[0], sc._OPEN_MANIFESTS[_r75[0]])
try:
    _res75 = sc.clean_backup_folder_if_needed(_bk75, {"max_backup_size_mb": 1, "backup_cleanup_enabled": True})
    _runs75 = sc.list_backup_runs(_bk75)
finally:
    sc.BACKUP_CLEANUP_LOG_PATH, _logp75 = _log75_old, sc.BACKUP_CLEANUP_LOG_PATH
check("B75: over the limit, only the old finished run is deleted; a run from the last 14 days and one of this session are kept",
      not os.path.isdir(_old75) and os.path.isdir(_new75) and os.path.isdir(_r75[0])
      and _res75 and _res75["removed"] == [os.path.basename(_old75)] and _res75["total"] > _res75["limit"], (_res75,))
_rm75 = [r for r in _runs75 if r.get("removed")]
check("B75: Backup History lists the removed run as 'removed by the size cleanup' (no folder, no Undo)",
      len(_rm75) == 1 and _rm75[0]["name"] == os.path.basename(_old75) and _rm75[0]["folder"] is None
      and _rm75[0]["action"] == "Delete extrafanart" and _rm75[0]["created"] == "2020-01-01 00:00:00"
      and len(_runs75) == 3, [(r["name"], r.get("removed")) for r in _runs75])
_w75 = sc.backup_run_size_warning(3 * 1024 * 1024, {"max_backup_size_mb": 1, "backup_cleanup_enabled": True})
check("B75: warning before a run larger than the limit (its size and the limit); none when it fits or the cleanup is off",
      _w75 and "3.0 MB" in _w75 and "1 MB" in _w75 and "14 days" in _w75
      and sc.backup_run_size_warning(512 * 1024, {"max_backup_size_mb": 1}) is None
      and sc.backup_run_size_warning(3 * 1024 * 1024, {"max_backup_size_mb": 1, "backup_cleanup_enabled": False}) is None
      and sc.backup_run_size_warning(3 * 1024 * 1024, {"max_backup_size_mb": 0}) is None, _w75)
import settings_dialog as _sd75
check("B75: the Backup tab says by how much the limit is passed",
      "1.5 MB over the 1 MB limit" in _sd75.backup_usage_text(int(2.5 * 1024 * 1024), 1)
      and _sd75.backup_usage_text(512 * 1024, 1) == "Backup folder size now: 0.5 MB of 1 MB", _sd75.backup_usage_text(int(2.5 * 1024 * 1024), 1))

_d79 = os.path.join(_TMP, "b79"); os.makedirs(_d79, exist_ok=True)
_good79 = os.path.join(_d79, "poster.jpg"); _jpeg(_good79, 200, 300)
_gb79 = open(_good79, "rb").read()
_html79 = b"<!DOCTYPE html><html><body>Rate limit</body></html>"
_e79 = []
for _body79 in (_html79, b""):
    try:
        mc.write_image_atomic(_good79, _body79)
    except mc.NotAnImageError as e:
        _e79.append(str(e))
check("B79: an HTML page or an empty body never replaces a good poster ('not an image'); no temp file left",
      len(_e79) == 2 and all("not an image" in x for x in _e79) and open(_good79, "rb").read() == _gb79
      and not os.path.exists(_good79 + ".mctmp"), _e79)
_cut79 = os.path.join(_d79, "cut.jpg"); open(_cut79, "wb").write(_gb79[: len(_gb79) // 2])
check("B79: a cut-off JPEG fails the check, a whole one passes", not mc.image_file_ok(_cut79) and mc.image_file_ok(_good79))
import urllib.request
class _Resp79:
    def __init__(s, data): s.d = data
    def read(s): return s.d
    def __enter__(s): return s
    def __exit__(s, *a): return False
_ro79 = urllib.request.urlopen
_fold79 = os.path.join(_d79, "folder.jpg"); _jpeg(_fold79, 200, 300)
_fb79 = open(_fold79, "rb").read()
_new79 = os.path.join(_d79, "new_src.jpg"); _jpeg(_new79, 400, 600)
_nb79 = open(_new79, "rb").read()
_bodies79 = [_html79, _nb79]
urllib.request.urlopen = lambda req, timeout=None: _Resp79(_bodies79.pop(0))
try:
    _dl79a = mc._tmdb_download_image("https://image.tmdb.org/t/p/original/h.jpg", _fold79)
    _kept79 = open(_fold79, "rb").read() == _fb79
    _dl79b = mc._tmdb_download_image("https://image.tmdb.org/t/p/original/g.jpg", _fold79)
finally:
    urllib.request.urlopen = _ro79
check("B79: a download that is not an image fails with a message and keeps the old file; a real image replaces it",
      _dl79a[0] is False and "did not send an image" in _dl79a[1] and _kept79
      and _dl79b == (True, None) and open(_fold79, "rb").read() == _nb79, (_dl79a, _dl79b))
_bad79 = os.path.join(_d79, "bad_poster.jpg"); open(_bad79, "wb").write(_html79)
_fb79 = open(_fold79, "rb").read()
try:
    mc._copy_image_as(_bad79, _fold79); _c79 = "copied"
except mc.NotAnImageError as e:
    _c79 = str(e)
_oc79 = shutil.copy2
def _cut_copy79(s, d, *a, **k):                           # the share drops in the middle of the copy
    open(d, "wb").write(open(s, "rb").read()[:100]); raise OSError("network name no longer available (test)")
shutil.copy2 = _cut_copy79
try:
    mc._copy_image_as(_new79, _fold79); _c79b = "copied"
except OSError as e:
    _c79b = str(e)
finally:
    shutil.copy2 = _oc79
check("B79: Copy poster → folder: a poster that is not an image, or a copy cut off midway, leaves folder.jpg as it was",
      "not an image" in _c79 and "network name" in _c79b and open(_fold79, "rb").read() == _fb79
      and not os.path.exists(_fold79 + ".mctmp"), (_c79, _c79b))

_d81 = os.path.join(_TMP, "b81"); os.makedirs(_d81, exist_ok=True)
def _x81(name, text):
    pth = os.path.join(_d81, name); open(pth, "wb").write(text.encode("utf-8")); return pth
_one81 = _x81("one.xml", '<?xml version="1.0"?><Title><LocalTitle>One</LocalTitle><Genres><Genre>Old</Genre></Genres><ProductionYear>2001</ProductionYear></Title>')
_w81 = mc.write_genres_to_xml(_one81, ["Drama", "Rock & Roll"])
_t81 = open(_one81, "rb").read().decode("utf-8")
check("B81: a one-line movie.xml keeps the rest of the document; only the Genres block changes",
      _w81 == (True, "") and _t81 == '<?xml version="1.0"?><Title><LocalTitle>One</LocalTitle><Genres><Genre>Drama</Genre><Genre>Rock &amp; Roll</Genre></Genres><ProductionYear>2001</ProductionYear></Title>', _t81)
_sc81 = _x81("selfclose.xml", "<Title>\r\n  <LocalTitle>Two</LocalTitle>\r\n  <Genres />\r\n  <ProductionYear>2002</ProductionYear>\r\n</Title>\r\n")
mc.write_genres_to_xml(_sc81, ["Drama"])
_t81b = open(_sc81, "rb").read().decode("utf-8")
check("B81: '<Genres />' is replaced (not a second block); CRLF and the other lines byte for byte",
      _t81b == "<Title>\r\n  <LocalTitle>Two</LocalTitle>\r\n  <Genres>\r\n  \t<Genre>Drama</Genre>\r\n  </Genres>\r\n  <ProductionYear>2002</ProductionYear>\r\n</Title>\r\n"
      and _t81b.count("<Genres") == 1, repr(_t81b))
_ml81 = _x81("multi.xml", "<Title>\n\t<LocalTitle>Three</LocalTitle>\n\t<Genres>\n\t\t<Genre>A</Genre>\n\t\t<Genre>B</Genre>\n\t</Genres>\n</Title>\n")
mc.write_genres_to_xml(_ml81, ["Comedy"])
check("B81: a normal block keeps its indentation; a file without Genres gets one before the root's end",
      open(_ml81, "rb").read().decode("utf-8") == "<Title>\n\t<LocalTitle>Three</LocalTitle>\n\t<Genres>\n\t\t<Genre>Comedy</Genre>\n\t</Genres>\n</Title>\n"
      and (lambda pth: (mc.write_genres_to_xml(pth, ["War"]), open(pth, "rb").read().decode("utf-8"))[1])(
          _x81("none.xml", "<Title>\n\t<LocalTitle>Four</LocalTitle>\n</Title>\n"))
      == "<Title>\n\t<LocalTitle>Four</LocalTitle>\n\t<Genres>\n\t\t<Genre>War</Genre>\n\t</Genres>\n</Title>\n",
      open(_ml81, "rb").read())

_d83 = os.path.join(_TMP, "b83"); os.makedirs(_d83, exist_ok=True)
_n83 = os.path.join(_d83, "has.nfo"); io.open(_n83, "w", encoding="utf-8", newline="\n").write(
    '<movie>\n  <title>Has</title>\n  <uniqueid type="imdb"></uniqueid>\n  <uniqueid type="tmdb"></uniqueid>\n  <imdbid></imdbid>\n  <tmdbid></tmdbid>\n  <id></id>\n</movie>\n')
_e83 = os.path.join(_d83, "empty.nfo"); io.open(_e83, "w", encoding="utf-8", newline="\n").write('<movie>\n  <title>Empty</title>\n</movie>\n')
_eb83 = open(_e83, "rb").read()
check("B83: 'Write empty ID tags' knows when nothing would be added (no backup, not counted); the dry run writes nothing",
      mc.empty_id_tags_needed(_e83, None) is True and open(_e83, "rb").read() == _eb83
      and (mc._write_empty_source_tags(_e83, None, "TMDB"), mc._write_empty_source_tags(_e83, None, "IMDB"),
           mc.empty_id_tags_needed(_e83, None))[2] is False,
      (mc.empty_id_tags_needed(_e83, None), open(_e83, "rb").read()))
class _Prog83:
    def __init__(s): s.cancelled = False; s.n = 0
    def advance(s, i):                                       # v0.19.4 L5: was update() (intended)
        s.n = i
        if i == 1: s.cancelled = True                      # Cancel pressed during the first movie
    def close(s): pass
class _App83:
    def _schedule_refresh(s, paths, need_ffprobe=False): pass
    def after(s, ms, fn): fn()
_res83 = []
_job83 = mc._BatchJob(_App83(), [{"movie_name": "A"}, {"movie_name": "B"}, {"movie_name": "C"}], "B83 test", prog=_Prog83())
def _drain83():                                              # v0.19.4 group C: the finish goes through ui_post;
    while not mc._UI_QUEUE.empty():                          # no main window here, so the test runs it itself
        _f83, _a83 = mc._UI_QUEUE.get_nowait(); _f83(*_a83)
_job83._work(lambda job, it: True, lambda job: _res83.append(job.cancel_note())); _drain83()
_job83b = mc._BatchJob(_App83(), [{"movie_name": "A"}], "B83 test")
_job83b._work(lambda job, it: True, lambda job: _res83.append(job.cancel_note())); _drain83()
check("B83: a cancelled batch says 'Cancelled after 1 of 3; 2 left out'; a finished one adds nothing",
      _res83 == ["\n\nCancelled after 1 of 3; 2 left out (not changed).", ""], _res83)
import zipfile as _zip83, hashlib as _h83
_up83 = os.path.join(_TMP, "b83_up", "realesrgan"); os.makedirs(_up83, exist_ok=True)
open(os.path.join(_up83, "realesrgan.exe"), "wb").write(b"OLD")
_zb83 = io.BytesIO()
with _zip83.ZipFile(_zb83, "w") as _z:
    _z.writestr("pack/realesrgan.exe", b"NEW")
_zbytes83 = _zb83.getvalue()
_info83 = {"url": "https://example.invalid/x.zip", "size": len(_zbytes83), "sha256": _h83.sha256(_zbytes83).hexdigest(),
           "exe": "pack/realesrgan.exe", "licences": (), "release": "test"}
class _R83:
    def __init__(s): s.b = io.BytesIO(_zbytes83)
    def read(s, n=-1): return s.b.read(n)
    def __enter__(s): return s
    def __exit__(s, *a): return False
import urllib.request as _ur83
_o83 = (mc.upscaler_dir, _ur83.urlopen, os.replace)
mc.upscaler_dir = lambda: _up83
_ur83.urlopen = lambda url, timeout=None: _R83()
def _locked83(a, b, *x, **k):
    if os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(_up83)):
        raise PermissionError(32, "The process cannot access the file because it is being used by another process")
    return _o83[2](a, b, *x, **k)
try:
    os.replace = _locked83
    try:
        mc.download_upscaler(info=_info83); _l83 = "installed"
    except RuntimeError as e:
        _l83 = str(e)
    os.replace = _o83[2]
    _kept83 = open(os.path.join(_up83, "realesrgan.exe"), "rb").read()
    _d83b = mc.download_upscaler(info=_info83)
finally:
    mc.upscaler_dir, _ur83.urlopen, os.replace = _o83
check("B83: upscaler re-install with a locked file keeps the old install working; a normal re-install swaps cleanly",
      "old install was kept" in _l83 and _kept83 == b"OLD"
      and open(os.path.join(_up83, "pack", "realesrgan.exe"), "rb").read() == b"NEW"
      and not os.path.exists(_up83 + ".old") and not os.path.exists(_up83 + ".new"), (_l83, _kept83))

_ms94 = list(sc.SETTINGS_MIGRATION_STATUS)
_m94 = copy.deepcopy(DEFAULT_SETTINGS) if "copy" in globals() else json.loads(json.dumps(DEFAULT_SETTINGS))
_m94["health_rules"] = None; _m94["max_nfo_kb"] = "abc"; _m94["dark_theme"] = 1; _m94["genre_list"] = ["Drama", "War"]
_m94["improve_checks"] = dict(_m94["improve_checks"]); _k94 = next(iter(_m94["improve_checks"])); _m94["improve_checks"][_k94] = "yes"
_r94 = sc.reset_wrong_types(_m94)
_st94 = [x for x in sc.SETTINGS_MIGRATION_STATUS if x not in _ms94]
sc.SETTINGS_MIGRATION_STATUS[:] = _ms94
check("B94: on load, wrongly typed keys get their default (logged, one status line); 1 → True; a genre list → text",
      set(_r94) == {"health_rules", "max_nfo_kb", f"improve_checks.{_k94}"} and isinstance(_m94["health_rules"], dict)
      and _m94["max_nfo_kb"] == DEFAULT_SETTINGS["max_nfo_kb"] and _m94["dark_theme"] is True
      and _m94["genre_list"] == "Drama\nWar" and len(_st94) == 1 and "3 values of the wrong type" in _st94[0], (_r94, _st94))
_cp94 = sc.CONFIG_PATH
sc.CONFIG_PATH = os.path.join(_TMP, "b94_settings.json")
io.open(sc.CONFIG_PATH, "w", encoding="utf-8").write('{"health_rules": null, "max_nfo_kb": 61}')
try:
    _l94 = sc.load_settings()
    _sv94 = sc.save_settings(_l94)
finally:
    sc.CONFIG_PATH = _cp94
    sc.SETTINGS_MIGRATION_STATUS[:] = _ms94
check("B94: settings.json with \"health_rules\": null loads with the default rules and can be saved again",
      isinstance(_l94["health_rules"], dict) and _l94["health_rules"] == {**DEFAULT_SETTINGS["health_rules"], **_l94["health_rules"]}
      and _l94["max_nfo_kb"] == 61 and _sv94 is True, (_l94.get("health_rules"), _sv94))

_ro95 = os.path.join(_TMP, "b95_file"); open(_ro95, "w").write("x")       # a FILE: no folder can be made under it
_ok95 = os.path.join(_TMP, "b95_cfg", "logs")
_h95, _p95 = mc._open_log_handler([os.path.join(_ro95, "logs"), _ok95])
_h95.close()
_env95 = os.environ.get("MEDIACLINIC_CONFIG_DIR")
try:
    os.environ["MEDIACLINIC_CONFIG_DIR"] = os.path.join(_TMP, "b95_cfgdir")
    _c95a = mc._log_dir_candidates()
    os.environ.pop("MEDIACLINIC_CONFIG_DIR", None)
    _c95b = mc._log_dir_candidates()
finally:
    if _env95 is None:
        os.environ.pop("MEDIACLINIC_CONFIG_DIR", None)
    else:
        os.environ["MEDIACLINIC_CONFIG_DIR"] = _env95
check("B95: a log folder that cannot be made falls back to the next one (config folder, then temp)",
      _p95 == os.path.join(_ok95, "app.log") and os.path.isfile(_p95), _p95)
check("B95: MEDIACLINIC_CONFIG_DIR moves the logs; without it logs\\ next to the program comes first; Pillow logs at INFO",
      _c95a[0] == os.path.join(os.path.join(_TMP, "b95_cfgdir"), "logs") and not any(x.startswith(mc._APP_DIR) for x in _c95a)
      and _c95b[0] == os.path.join(mc._APP_DIR, "logs") and len(_c95b) == 3
      and _logging27.getLogger("PIL").level == _logging27.INFO
      and os.path.dirname(mc.LOG_PATH) == (os.path.join(sc.get_config_dir(), "logs") if os.environ.get("MEDIACLINIC_CONFIG_DIR", "").strip()
                                           else os.path.join(mc._APP_DIR, "logs")), (_c95a, _c95b, mc.LOG_PATH))

import settings_dialog as _sd96
_bad96 = []
for _n96 in ("pkg/sub:stream/x.exe", "pkg/dir./x.exe", "pkg/dir /x.exe", "pkg/../x.exe", "/abs/x.exe"):
    try:
        mc._safe_members([_n96]); _bad96.append(("accepted", _n96))
    except mc.UpdateError:
        pass
check("B96: the update unpack rejects ':' / a trailing dot or space in ANY part, '..' and absolute paths",
      not _bad96 and mc._safe_members(["pkg/a/b.exe", "pkg/c.txt"]) == [("pkg/a/b.exe", ["a", "b.exe"]), ("pkg/c.txt", ["c.txt"])], _bad96)
check("B96: the resolved target must stay inside the destination",
      mc.inside_dir(os.path.join(_TMP, "x", "y.txt"), _TMP) and not mc.inside_dir(os.path.join(_TMP, "..", "y.txt"), _TMP)
      and not mc.inside_dir(os.path.join(_TMP + "_other", "y.txt"), _TMP))
_waits96, _os96 = [], time.sleep
class _Stop96(Exception): pass
def _sleep96(s):
    _waits96.append(s); raise _Stop96()
mc._HTTP_TIMES["b96test"] = mc.collections.deque([time.monotonic() - 0.5] * 10)   # default limit: 10 per 1.0 s
time.sleep = _sleep96
try:
    mc._http_rate_wait("b96test")
except _Stop96:
    pass
finally:
    time.sleep = _os96
    mc._HTTP_TIMES.pop("b96test", None)
check("B96: the rate limiter counts on the monotonic clock (full bucket → waits about 0.55 s, never hours)",
      len(_waits96) == 1 and 0.3 < _waits96[0] < 1.1, _waits96)
_r96 = _sd96.redact_key_text("✗ Error: URLError: https://api.themoviedb.org/3/configuration?api_key=SECRETKEY96 failed (SECRETKEY96)", "SECRETKEY96")
check("B96: Validate messages never show the key; the Validate buttons send the app's own User-Agent",
      "SECRETKEY96" not in _r96 and "api_key=***" in _r96 and _sd96.USER_AGENT == mc._UA == f"MediaClinic/{mc.APP_VERSION}"
      and "MediaClinic/0." not in io.open(_sd96.__file__, encoding="utf-8").read(), _r96)

_pr84 = [{"subfolder": "A", "subfolder_path": r"Z:\Lib\A", "nfo_exists": True, "scan_mtime": 5.0},
         {"subfolder": "B", "subfolder_path": r"Z:\Lib\B", "nfo_exists": True, "scan_mtime": 6.0}]
_rw84 = [{"subfolder": "A", "subfolder_path": "z:/lib/a", "nfo_exists": False, "scan_mtime": None},
         {"subfolder": "B", "subfolder_path": r"Z:\Lib\B", "nfo_exists": True, "scan_mtime": 9.0},
         {"subfolder": "C", "subfolder_path": r"Z:\Lib\C", "nfo_exists": False, "scan_mtime": None}]
_mg84 = mc.merge_unfinished_rows(_rw84, _pr84)
if sys.platform == "win32": check("B84: an unfinished row → the previous row of its folder; a finished row stays; a new folder keeps its unfinished row (no scan time)",
      _mg84[0] is _pr84[0] and _mg84[1] is _rw84[1] and _mg84[2] is _rw84[2] and _mg84[2]["scan_mtime"] is None, _mg84)

_d85 = os.path.join(_TMP, "b85", "Sig Movie (2001)"); os.makedirs(os.path.join(_d85, "Subs"), exist_ok=True)
open(os.path.join(_d85, "Sig Movie (2001).mkv"), "wb").write(b"\0" * 64)
_jpeg(os.path.join(_d85, "poster.jpg"), 100, 150); _jpeg(os.path.join(_d85, "fanart.jpg"), 192, 108)
open(os.path.join(_d85, "Subs", "eng.srt"), "w").write("1\n00:00:01,000 --> 00:00:02,000\nHi\n")
_s85 = [mc.folder_signature(_d85)]
_newest85 = mc._folder_mtime(_d85)
os.remove(os.path.join(_d85, "poster.jpg")); _s85.append(mc.folder_signature(_d85))                    # deleted poster
os.rename(os.path.join(_d85, "fanart.jpg"), os.path.join(_d85, "backdrop.jpg")); _s85.append(mc.folder_signature(_d85))   # a rename
_old85 = os.path.join(_TMP, "b85", "old_poster.jpg"); _jpeg(_old85, 120, 180); os.utime(_old85, (1000000000, 1000000000))
_nb85 = mc._folder_mtime(_d85)
shutil.copy2(_old85, os.path.join(_d85, "poster.jpg")); _s85.append(mc.folder_signature(_d85))       # a copy that keeps an OLD mtime
_na85 = mc._folder_mtime(_d85)
time.sleep(1.2)                                   # NTFS updates a folder's time on a later write, not within the same instant
open(os.path.join(_d85, "Subs", "por.srt"), "w").write("1\n00:00:01,000 --> 00:00:02,000\nOi\n"); _s85.append(mc.folder_signature(_d85))   # Subs\
check("B85: the folder signature changes for a deleted poster, a rename, a copy with an old mtime and a new file in Subs\\",
      len(set(_s85)) == 5 and mc.folder_signature(_d85) == _s85[-1], _s85)
check("B85: …while the newest mtime alone misses the copy with an old mtime",
      _nb85 == _na85 and _s85[2] != _s85[3], (_nb85, _na85))

_v86 = {"video_path": r"Z:\Lib\M\m.mkv", "video_bytes": 1000, "video_mtime": 100.0}
if sys.platform == "win32": check("B86: FFprobe data is reused only for the same video (path, size, mtime; an old row without mtime: path + size)",
      mc.ffprobe_reusable(_v86, {"video_path": "z:/lib/m/M.MKV", "video_bytes": 1000, "video_mtime": 100.4})
      and not mc.ffprobe_reusable(_v86, {"video_path": r"Z:\Lib\M\m.mkv", "video_bytes": 2000, "video_mtime": 100.0})
      and not mc.ffprobe_reusable(_v86, {"video_path": r"Z:\Lib\M\m.mkv", "video_bytes": 1000, "video_mtime": 500.0})
      and not mc.ffprobe_reusable(_v86, {"video_path": r"Z:\Lib\M\other.mkv", "video_bytes": 1000, "video_mtime": 100.0})
      and mc.ffprobe_reusable({"video_path": r"Z:\Lib\M\m.mkv", "video_bytes": 1000}, {"video_path": r"Z:\Lib\M\m.mkv", "video_bytes": 1000, "video_mtime": 7.0})
      and not mc.ffprobe_reusable(None, _v86) and not mc.ffprobe_reusable(_v86, {"video_path": None}))

_d87 = os.path.join(_TMP, "b87", "Broken Video (2001)"); os.makedirs(_d87, exist_ok=True)
open(os.path.join(_d87, "Broken Video (2001).mkv"), "wb").write(b"\0" * 4096)
_nfo(os.path.join(_d87, "Broken Video (2001).nfo"), "Broken Video")
_o87 = (mc.FFPROBE_PATH, mc._run_ffprobe_json)
_runs87 = []
def _fail87(path, timeout=30):
    _runs87.append(path); return {}                       # a failed / timed-out probe
try:
    mc.FFPROBE_PATH = r"C:\fake\ffprobe.exe"; mc._run_ffprobe_json = _fail87
    mc.clear_read_caches()
    _r87 = mc.scan_one_subfolder(_d87, "Broken Video (2001)", use_ffprobe=True)
    _n87a = len(_runs87)
    mc.clear_read_caches()                                # a new scan tries once more
    mc.scan_one_subfolder(_d87, "Broken Video (2001)", use_ffprobe=True)
    _n87b = len(_runs87)
finally:
    mc.FFPROBE_PATH, mc._run_ffprobe_json = _o87
    mc.clear_read_caches()
check("B87: a failed probe runs ONCE per scan (resolution, audio, subtitles, Lang OK? all reuse the failure); a new scan tries again",
      _n87a == 1 and _n87b == 2, (_n87a, _n87b))
check("B87: the row says ffprobe_failed and 'FFprobe could not read the video', not 'No audio tracks detected'",
      _r87["ffprobe_failed"] is True and mc.FFPROBE_FAILED_TEXT in _r87["health_reasons"]
      and "No audio tracks detected" not in _r87["health_reasons"], _r87["health_reasons"])

check("B89: language codes compare as one ('en' = 'English' = 'eng', 'ger' = 'deu', 'pt-BR' = 'por'; 'por' ≠ 'eng')",
      mc.lang_same("en", "English") and mc.lang_same("eng", "EN") and mc.lang_same("ger", "DEU") and mc.lang_same("German", "ger")
      and mc.lang_same("pt-BR", "POR") and not mc.lang_same("por", "eng") and not mc.lang_same("und", "und") and not mc.lang_same("", ""),
      [mc.lang_key(x) for x in ("en", "English", "eng", "ger", "deu", "German", "pt-BR", "por")])
def _hr89(fn, row, rules):
    e, w = [], []
    fn(row, rules, mc.SETTINGS, e, w)
    return e + w
_sub89 = {"required_subtitle_language": True, "required_subtitle_language_code": "POR"}
_aud89 = {"required_audio_language": True, "required_audio_language_code": "DEU"}
check("B89: the subtitle rule is skipped when FFprobe never ran (internal subtitles unknown) or failed; it still works after a probe",
      _hr89(mc._hr_required_subtitle_language, {"video_count": 1, "ffprobe_ran": False, "subs_internal": [], "subs_external": []}, _sub89) == []
      and _hr89(mc._hr_required_subtitle_language, {"video_count": 1, "ffprobe_ran": True, "ffprobe_failed": True, "subs_internal": [], "subs_external": []}, _sub89) == []
      and _hr89(mc._hr_required_subtitle_language, {"video_count": 1, "ffprobe_ran": True, "subs_internal": [], "subs_external": []}, _sub89) == ["Required subtitle language not found (POR)"]
      and _hr89(mc._hr_required_subtitle_language, {"video_count": 1, "ffprobe_ran": True, "subs_internal": [{"lang": "pt"}], "subs_external": []}, _sub89) == [])
check("B89: the audio rule accepts 'ger' for DEU and 'en' / 'English' for ENG",
      _hr89(mc._hr_required_audio_language, {"video_count": 1, "ffprobe_ran": True, "audio_tracks": [{"language": "GER"}]}, _aud89) == []
      and _hr89(mc._hr_required_audio_language, {"video_count": 1, "ffprobe_ran": True, "audio_tracks": [{"language": "English"}]},
                {"required_audio_language": True, "required_audio_language_code": "ENG"}) == []
      and _hr89(mc._hr_required_audio_language, {"video_count": 1, "ffprobe_ran": True, "audio_tracks": [{"language": "ITA"}]}, _aud89)
      == ["Required audio language not found (DEU)"])
_d89 = os.path.join(_TMP, "b89"); os.makedirs(_d89, exist_ok=True)
_x89a = os.path.join(_d89, "meta.xml"); io.open(_x89a, "w", encoding="utf-8").write(
    "<Title>\n  <LocalTitle>X</LocalTitle>\n  <Language>Portuguese</Language>\n</Title>\n")
_x89b = os.path.join(_d89, "audio.xml"); io.open(_x89b, "w", encoding="utf-8").write(
    "<Title>\n  <Language>English</Language>\n  <MediaInfo>\n    <Audio>\n      <Language>por</Language>\n    </Audio>\n  </MediaInfo>\n</Title>\n")
# ### NEW v0.19.5 B121 ### the metadata language is not the film's language
_w121 = lambda name, txt: (io.open(os.path.join(_d89, name), "w", encoding="utf-8").write(txt), os.path.join(_d89, name))[1]
_v121 = os.path.join(_d89, "v.mkv")
_L121 = lambda nfo=None, xml=None: mc.compute_lang_ok(_v121, [], [], nfo, xml, "PT", use_ffprobe=False)
check("B121: Lang OK? ignores XML <LanguageCode> and a top-level NFO <language>", _L121(xml=_w121("c.xml", "<Title><LanguageCode>pt</LanguageCode></Title>")) == "N"
      and _L121(nfo=_w121("t.nfo", "<movie><language>por</language></movie>")) == "N")
check("B121: Lang OK? counts the NFO's audio and subtitle streams and the XML's audio and subtitle",
      _L121(nfo=_w121("a.nfo", "<movie><fileinfo><streamdetails><audio><language>por</language></audio></streamdetails></fileinfo></movie>")) == "Y"
      and _L121(nfo=_w121("s.nfo", "<movie><fileinfo><streamdetails><subtitle><language>por</language></subtitle></streamdetails></fileinfo></movie>")) == "Y"
      and _L121(xml=_w121("s.xml", "<Title><MediaInfo><Subtitle><Language>por</Language></Subtitle></MediaInfo></Title>")) == "Y")
check("B121: a stream's language is read even in an NFO that does not parse; its top-level <language> is not",
      _L121(nfo=_w121("b.nfo", "<movie><language>eng</language><streamdetails><audio><language>por</language></audio></streamdetails>")) == "Y"
      and _L121(nfo=_w121("b2.nfo", "<movie><language>por</language><streamdetails><audio><language>eng</language></audio></streamdetails>")) == "N")
_C121 = lambda t: mc.extract_language_from_xml(_w121("col.xml", t))
check("B121: the Language column: the top-level tag only, a stream's eng is not it, every empty form alike",
      _C121("<Title><Language>Portuguese</Language><MediaInfo><Audio><Language>eng</Language></Audio></MediaInfo></Title>") == "Portuguese"
      and [_C121(f"<Title>{e}<MediaInfo><Audio><Language>eng</Language></Audio></MediaInfo></Title>") for e in ("<Language/>", "<Language />", "<Language></Language>")] == ["Unknown"] * 3
      and _C121("<Title><MediaInfo><Audio><Language>eng</Language></Audio></MediaInfo></Title>") == "—")
check("B121: the warning and the Auto Repair step are retired; the settings key stays, ignored",
      "missing_language_field" in DEFAULT_SETTINGS["health_rules"] and not hasattr(mc, "_hr_missing_language_field") and not hasattr(mc.App, "_ar_language")
      and "language" not in mc._AR_LABELS and not any("Language field" in str(f) for f in [mc.HEALTH_RULES]))
# ### NEW v0.19.5 AS-A1 ### an old Y does not override the files
_o121 = mc.ffprobe_reusable; mc.ffprobe_reusable = lambda a, b: True
try:
    _k121 = lambda d: mc.carry_after_rescan({"video_path": "v.mkv", "lang_ok": "N", "subs_internal": [], "subs_external": [], "subs_hard": [], "audio_tracks": []},
                                            dict({"ffprobe_ran": True, "lang_ok": "Y", "video_path": "v.mkv"}, **d))["lang_ok"]
    check("AS-A1: after a rescan an old Y with nothing behind it turns to N; stored POR audio or subtitles keep Y",
          _k121({"audio_tracks": [{"language": "ENG"}]}) == "N" and _k121({"audio_tracks": [{"language": "POR"}]}) == "Y"
          and _k121({"subs_internal": [{"lang": "por"}]}) == "Y")
finally:
    mc.ffprobe_reusable = _o121
check("B89: Lang OK? does not count the XML's metadata <Language> as audio; an <Audio><Language> still counts",
      mc.compute_lang_ok(os.path.join(_d89, "v.mkv"), [], [], None, _x89a, "PT", use_ffprobe=False) == "N"
      and mc.compute_lang_ok(os.path.join(_d89, "v.mkv"), [], [], None, _x89b, "PT", use_ffprobe=False) == "Y")

_rc93 = sc.RESULTS_CACHE_PATH; _nt93 = list(sc.RESULTS_CACHE_NOTES)
sc.RESULTS_CACHE_PATH = os.path.join(_TMP, "b93", "last_results.json"); os.makedirs(os.path.dirname(sc.RESULTS_CACHE_PATH), exist_ok=True)
_bad93 = b'[{"subfolder": "A", "x": 1}, {"subfolder": "B", "x'
open(sc.RESULTS_CACHE_PATH, "wb").write(_bad93)
try:
    _l93 = sc.load_results_cache_stepwise()
    _cor93 = [n for n in os.listdir(os.path.dirname(sc.RESULTS_CACHE_PATH)) if n.startswith("last_results.json.corrupt-")]
    _new93 = [x for x in sc.RESULTS_CACHE_NOTES if x not in _nt93]
finally:
    sc.RESULTS_CACHE_PATH = _rc93; sc.RESULTS_CACHE_NOTES[:] = _nt93
check("B93: a truncated last_results.json is kept as .corrupt-<date> (same bytes) and a status-bar note says so",
      _l93 == [] and len(_cor93) == 1 and open(os.path.join(_TMP, "b93", _cor93[0]), "rb").read() == _bad93
      and len(_new93) == 1 and "could not be read" in _new93[0], (_l93, _cor93, _new93))
_fc93 = sc.FFPROBE_CACHE_PATH; _mc93 = (mc._FFPROBE_CACHE, mc._FFPROBE_DIRTY[0])
sc.FFPROBE_CACHE_PATH = os.path.join(_TMP, "b93", "ffprobe_cache.json")
_ka93 = os.path.normcase(os.path.abspath(os.path.join(_TMP, "b93", "a.mkv")))
_kb93 = os.path.normcase(os.path.abspath(os.path.join(_TMP, "b93", "gone.mkv")))
try:
    mc._FFPROBE_CACHE = {_ka93: {"size": 1, "mtime_ns": 1, "data": {"streams": []}},
                         _kb93: {"size": 2, "mtime_ns": 2, "data": {"streams": []}}}
    mc._FFPROBE_DIRTY[0] = False
    mc._ffprobe_cache_flush([os.path.join(_TMP, "b93", "a.mkv")])
    _saved93 = json.load(open(sc.FFPROBE_CACHE_PATH, encoding="utf-8"))
    _errs93 = []
    def _save93():
        try:
            for _ in range(25):
                sc.save_ffprobe_cache({_ka93: {"size": 1, "mtime_ns": 1, "data": {}}})
        except Exception as e:
            _errs93.append(repr(e))
    _th93 = [threading.Thread(target=_save93) for _ in range(3)]
    [t.start() for t in _th93]; [t.join() for t in _th93]
    _left93 = [n for n in os.listdir(os.path.join(_TMP, "b93")) if n.endswith(".tmp")]
    _ok93 = json.load(open(sc.FFPROBE_CACHE_PATH, encoding="utf-8"))
finally:
    sc.FFPROBE_CACHE_PATH = _fc93; mc._FFPROBE_CACHE, mc._FFPROBE_DIRTY[0] = _mc93
check("B93: the ffprobe cache keeps only the videos in the table; saves from several threads never collide",
      list(_saved93) == [_ka93] and not _errs93 and not _left93 and list(_ok93) == [_ka93], (list(_saved93), _errs93, _left93))

_pf103 = {"poster_exists": True, "folder_exists": True, "poster_bytes": 1200, "folder_bytes": 900,
          "poster_format": "PNG", "folder_format": "JPEG", "poster_dim": "1000x1500", "folder_dim": "1000x1500"}
check("B103: 'Copy poster → folder' counts with the action's own test (a PNG poster + its JPEG folder copy = nothing to do)",
      mc.copy_poster_needed(_pf103) is False and mc.copy_poster_needed(dict(_pf103, folder_dim="500x750")) is True
      and mc.copy_poster_needed(dict(_pf103, folder_exists=False)) is True and mc.copy_poster_needed(dict(_pf103, poster_exists=False)) is False)

import tokenize as _tok105
_src105 = io.open(mc.__file__, encoding="utf-8").read()
_lines105 = _src105.split("\n")
_ok105 = ("Extract Backdrop(s)", "Custom Genre(s)", "Custom genre(s)", "Open Website(s)", ".xml file(s)",
          "language(s) burned", "selected movie(s)", "timeout (s)")      # uncounted texts kept (user decision 2026-11-02)
_bad105 = []
for _t in _tok105.generate_tokens(io.StringIO(_src105).readline):
    if _t.type in (_tok105.STRING, getattr(_tok105, "FSTRING_MIDDLE", -1)):
        _ln = _lines105[_t.start[0] - 1]
        if "logger." in _ln or _ln.lstrip().startswith("#") or _t.string.lstrip("rbuRBUfF")[:3] in ('"' * 3, "'" * 3):
            continue
        _txt = re.sub(r"\{[^{}]*\}", "", _t.string)   # Python < 3.12 gives a whole f-string: its {code} is not text
        if (re.search(r"\b1 (movies|files|folders|images)\b", _txt) or "kind(s)" in _txt
                or ("(s)" in _txt and not any(k in _ln for k in _ok105))):
            _bad105.append((_t.start[0], _txt[:60]))
check("B105: no user-visible '1 movies', 'kind(s)' or counted '(s)' text is left (log lines and the kept uncounted labels aside)",
      not _bad105, _bad105[:8])
check("B105: _n() — 1 movie / 2 movies / 0 movies, 1 entry / 3 entries, a number format",
      mc._n(1, "movie") == "1 movie" and mc._n(2, "movie") == "2 movies" and mc._n(0, "movie") == "0 movies"
      and mc._n(1, "entry") == "1 entry" and mc._n(3, "entry") == "3 entries" and mc._n(1234, "file", ",") == "1,234 files")

_tools13 = ["📤  Export Movie List…  (Ctrl+Shift+E)", "🧱  Choose Columns…", mc.IGNORED_MENU_LABEL, "-",
            "📊  Library Statistics", "👯  Duplicate Movies Report", mc.NOT_DUP_MANAGE_LABEL, "♻  Recompute Health Status (no rescan)", "-",
            "💾  Save Scan Results…", "🕘  Backup History / Undo…", "📂  Open Scan Results…", "-",
            "⭐  Sync Ratings Online — All Movies…", "🔗  Normalize Sources — All Movies…", "🔎  Search Sources — All Movies…",
            "✅  Verify IMDb/TMDB IDs — All Movies…", mc.CHECK_COLL_LABEL, mc.FIX_COLL_ALL_LABEL, mc.CREATE_COLL_ALL_LABEL,   # + v0.19.4 B110b / e / f / g (intended)
            "🛠  Auto Repair — All Movies…", "🎬  Normalize Genres — All Movies…",
            "🔍  Run Improvements Check — All Movies…", "🏥  Health Status Report — All Movies", "🔁  Refresh Icons — All Movies", "-",
            "🖼  Copy poster.jpg → folder.jpg — All Movies with Differences…", mc.IMAGE_FIX_ALL_LABEL, mc.NFO_RENAME_ALL_LABEL,
            mc.EXTRAFANART_MENU_LABEL]
check("I13: the Tools menu list from the registry = the menu as it was (after B108), entry for entry",
      ["-" if a == "-" else mc.ACTIONS[a]["label"] for a in mc.TOOLS_MENU] == _tools13)
check("I13: menu paths come from the registry ('Tools → Backup History / Undo…'); every shortcut has an action",
      mc.menu_path("backup_history") == "Tools → Backup History / Undo…" and mc.menu_path("export_list") == "Tools → Export Movie List…"
      and mc.UNDO_HINT.startswith("Tools → Backup History / Undo…")
      and {k for a in mc.ACTIONS.values() for k in a["keys"]} >= {"<F5>", "<Control-r>", "<Control-Shift-R>", "<Control-i>", "<Control-e>", "<Control-Shift-E>"})

# ── v0.19.4 B110a: collections — the data ──  ### NEW v0.19.4 B110a ###
import collection_rules as _cr
_r110 = [_cr.read_set("<movie><set>Harry &amp; Co</set></movie>"),
         _cr.read_set('<movie>\n <set tmdbcolid="1241">\n  <name>Harry Potter Collection</name>\n  <overview>Ov</overview>\n </set>\n <set>Other</set>\n</movie>'),
         _cr.read_set('<movie><set tmdbcolid="5"/></movie>'), _cr.read_set("<movie><set><overview>a</overview></set></movie>"),
         _cr.read_set("<movie><set>  </set></movie>"), _cr.read_set("<movie><title>x</title></movie>")]
check("B110a: <set> read in both forms (first one counts, tmdbcolid, overview, &amp;); no name = no set (as Kodi)",
      _r110[0] == {"name": "Harry & Co", "tmdbcolid": None, "overview": None, "count": 1}
      and _r110[1] == {"name": "Harry Potter Collection", "tmdbcolid": 1241, "overview": "Ov", "count": 2}
      and _r110[2:] == [None, None, None, None], _r110)
check("B110a: name comparison — case, spaces, quotes and dashes unified; accents kept",
      _cr.norm_name("Harry  Potter – Collection’s") == _cr.norm_name("harry potter - collection's")
      and _cr.norm_name("Coleção") != _cr.norm_name("Colecao"))
check("B110a: Kodi's legal folder name (/ \\ ? : * \" < > | → _, trailing dots and spaces removed)",
      _cr.kodi_legal_name("Star Wars: Episode I? . ") == "Star Wars_ Episode I_" and _cr.kodi_legal_name('A/B\\C"D<E>F|G*') == "A_B_C_D_E_F_G_",
      _cr.kodi_legal_name("Star Wars: Episode I? . "))
check("B110a: language decision — disjoint → warn, overlap → ok, one unknown → not checked",
      _cr.language_decision({"pt"}, {"en"}) == ("warn", "pt", "en") and _cr.language_decision({"pt", "en"}, {"en"})[0] == "ok"
      and _cr.language_decision(set(), {"en"})[0] == "unknown")
_g110 = _cr.group_rows([{"movie_name": "A", "coll_nfo": {"name": "Saga"}}, {"movie_name": "B", "coll_nfo": None},
                        {"movie_name": "C", "coll_nfo": {"name": "saga"}}, {"movie_name": "D", "coll_nfo": {"name": "Other"}}])
check("B110a: grouping — a collection sits where its first movie sits, the case-folded name groups, single movies stay",
      [(i[0], i[2] if i[0] == "coll" else i[1]["movie_name"], len(i[3]) if i[0] == "coll" else 1) for i in _g110]
      == [("coll", "Saga", 2), ("movie", "B", 1), ("coll", "Other", 1)], _g110)
_t110 = '<?xml version="1.0" encoding="utf-8"?>\r\n<movie>\r\n  <title>A</title>\r\n</movie>\r\n'
_n110 = _cr.replace_set_in_text(_t110, "Saga & Co", 10)
_o110 = _cr.replace_set_in_text('<movie>\n  <set>Old</set>\n  <set>2nd</set>\n</movie>\n', "New", None, "ov")
check("B110a: the <set> text change — inserted before </movie> (CRLF kept, escaped), the old form becomes the Jarvis form, removal gives the file back",
      _n110 == '<?xml version="1.0" encoding="utf-8"?>\r\n<movie>\r\n  <title>A</title>\r\n  <set tmdbcolid="10">\r\n    <name>Saga &amp; Co</name>\r\n  </set>\r\n</movie>\r\n'
      and _o110 == '<movie>\n  <set>\n    <name>New</name>\n    <overview>ov</overview>\n  </set>\n  <set>2nd</set>\n</movie>\n'
      and _cr.remove_set_in_text(_n110) == _t110, (_n110, _o110))
_d110 = tempfile.mkdtemp(prefix="mc_b110a_")
_m110 = os.path.join(_d110, "Saga One (2001)"); os.makedirs(_m110)
open(os.path.join(_m110, "Saga One (2001).mkv"), "wb").write(b"\0" * 64)
open(os.path.join(_m110, "Saga One (2001).nfo"), "w", encoding="utf-8").write(
    '<movie>\n  <title>Saga One</title>\n  <set tmdbcolid="77"><name>The Saga</name></set>\n</movie>\n')
open(os.path.join(_m110, "movie.xml"), "w", encoding="utf-8").write("<Title><BoxSetName>x</BoxSetName><LocalTitle>a</LocalTitle></Title>")
_row110 = mc.scan_one_subfolder(_m110, "Saga One (2001)", use_ffprobe=False)
check("B110a: the scan keeps the NFO collection (coll_nfo), coll_xml None (D11), coll_tmdb None (not checked), the movie.xml hint count",
      (_row110.get("coll_nfo") or {}).get("name") == "The Saga" and _row110["coll_nfo"]["tmdbcolid"] == 77
      and _row110.get("coll_xml") == {"name": None, "tmdbcolid": None, "stray": False}   # v0.19.4 fix 6 (intended): movie.xml is read now
      and _row110.get("coll_tmdb") is None and _row110.get("title_langs") == []
      and _row110.get("coll_xml_hint") == 1, {k: _row110.get(k) for k in ("coll_nfo", "coll_xml", "coll_tmdb", "coll_xml_hint")})
check("B110a: the filter finds the collection name; export and sort know 'collection'",
      mc._matches_filter(_row110, "the saga") and not mc._matches_filter(_row110, "zzz")
      and "collection" in export_list.ALL_FIELD_KEYS and "collection" in mc._se.KIND and mc.SORT_VALUE_FNS["collection"](_row110, "asc"))
_leg110 = mc._results_from_json([{"subfolder": "Old", "subfolder_path": "x"}, dict(_row110)])
check("B110a: a row cached before B110 is marked for the next Quick Scan's <set> read; a new row is not",
      _leg110[0].get("coll_unread") is True and _leg110[0].get("coll_nfo") is None and not _leg110[1].get("coll_unread"),
      [(r.get("coll_unread"), r.get("coll_nfo")) for r in _leg110])
check("B110a: the Collection column exists, hidden by default (model + schema)",
      "collection" in mc._COL_IDX and "collection" in DEFAULT_SETTINGS["hidden_columns"]
      and "b110_collection_column_hidden" in sc._MIGRATIONS)
shutil.rmtree(_d110, ignore_errors=True)

# ── v0.19.4 B110b: collections — the online data (fakes only) ──  ### NEW v0.19.4 B110b ###
_mv110 = {"id": 671, "title": "Harry Potter and the Philosopher's Stone", "original_title": "Harry Potter and the Philosopher's Stone",
          "original_language": "en", "belongs_to_collection": {"id": 1241, "name": "Harry Potter Collection"},
          "translations": {"translations": [{"iso_639_1": "pt", "data": {"title": "Harry Potter e a Pedra Filosofal"}},
                                            {"iso_639_1": "es", "data": {"title": ""}}]}}
_ct110 = _cr.coll_from_movie(_mv110, "pt-BR", 100.0)
check("B110b: coll_tmdb from a /movie answer; no collection → id None; not a movie → None",
      _ct110 == {"id": 1241, "name": "Harry Potter Collection", "lang": "pt-BR", "when": 100.0}
      and _cr.coll_from_movie({"id": 5}, "en", 1.0) == {"id": None, "when": 1.0} and _cr.coll_from_movie({}, "en", 1.0) is None)
check("B110b: title_langs — the languages whose TMDB title is the local title (an empty translation never matches)",
      _cr.title_langs_from(_mv110, ["Harry Potter e a Pedra Filosofal"]) == ["pt"]
      and _cr.title_langs_from(_mv110, ["harry potter and the philosopher’s stone"]) == ["en"]
      and _cr.title_langs_from(_mv110, [""]) == [])
_ce110 = _cr.coll_cache_entry({"name": "Harry Potter - Coleção", "overview": "Ov PT", "parts": [{"id": 671}, {"id": 672}]},
                              {"translations": [{"iso_639_1": "en", "data": {"title": "Harry Potter Collection", "overview": "Ov EN"}},
                                                {"iso_639_1": "de", "data": {"title": ""}}]}, "pt-BR", 5.0)
check("B110b: a collection cache entry — names / overviews per language, its parts",
      _ce110 == {"names": {"en": "Harry Potter Collection", "pt": "Harry Potter - Coleção"},
                 "overviews": {"en": "Ov EN", "pt": "Ov PT"}, "parts": [671, 672], "when": 5.0}, _ce110)
check("B110b: asked again only when missing or older than 30 days",
      _cr.needs_check({}, 1e9) and _cr.needs_check({"coll_tmdb": {"id": 1, "when": 1e9 - 31 * 86400}}, 1e9)
      and not _cr.needs_check({"coll_tmdb": {"id": None, "when": 1e9 - 86400}}, 1e9))
_ok110 = sc.save_collections_cache({"1241": _ce110}) and sc.load_collections_cache() == {"1241": _ce110}
open(sc.COLLECTIONS_CACHE_PATH, "w", encoding="utf-8").write("{not json")
_bad110 = sc.load_collections_cache()
_kept110 = [f for f in os.listdir(os.path.dirname(sc.COLLECTIONS_CACHE_PATH)) if f.startswith("collections_cache.json.corrupt-")]
check("B110b: collections_cache.json — saved and read back; a corrupt file is kept as .corrupt-<date> and reads as {}",
      _ok110 and _bad110 == {} and _kept110, (_ok110, _bad110, _kept110))
for _f110 in _kept110:
    os.remove(os.path.join(os.path.dirname(sc.COLLECTIONS_CACHE_PATH), _f110))
_chk110 = {"result": "OK", "coll_tmdb": _ct110, "title_langs": ["pt"]}
_row110b = mc.take_collection_data({"source_tmdb_val": "671"}, _chk110)
_new110 = mc.carry_collection_data({"source_tmdb_val": "671", "coll_tmdb": None}, _row110b)
_oth110 = mc.carry_collection_data({"source_tmdb_val": "999", "coll_tmdb": None}, _row110b)
check("B110b: Verify IDs' collection data moves into the row; a rescan keeps it while the TMDB ID is the same",
      _row110b["coll_tmdb"] == _ct110 and "coll_tmdb" not in _chk110 and _new110["coll_tmdb"] == _ct110
      and _oth110["coll_tmdb"] is None)
check("B110b: a movie without TMDB ID or with a flagged ID is skipped (and why)",
      mc.collection_check_ready({"source_tmdb_val": ""})[1] == "no TMDB ID"
      and mc.collection_check_ready({"source_tmdb_val": "1", "id_check": {"result": mc.ID_OTHER}})[0] is False
      and mc.collection_check_ready({"source_tmdb_val": "1", "id_check": {"result": mc.ID_OK}}) == (True, None))

# ── v0.19.4 B110c: the collection rules ──  ### NEW v0.19.4 B110c ###
_cc110 = {"1241": {"names": {"en": "Harry Potter Collection", "pt": "Harry Potter - Coleção"}, "overviews": {}, "parts": [], "when": 1}}
_tm110 = {"id": 1241, "name": "Harry Potter Collection", "lang": "en-US", "when": 1}
def _cr110(nfo=None, tm=_tm110, tl=()):
    return {"coll_nfo": nfo, "coll_tmdb": tm, "title_langs": list(tl)}
_mis = lambda r, sp=None: _cr.mismatch_reasons(r, _cc110, sp)
check("B110c: TMDB lists a collection, the NFO has none → 'Collection: missing (TMDB: …)'",
      _mis(_cr110()) == ["Collection: missing (TMDB: 'Harry Potter Collection')"], _mis(_cr110()))
check("B110c: the NFO names another collection (name or tmdbcolid) → 'Collection: NFO says …, TMDB says …'",
      _mis(_cr110({"name": "Wizards", "tmdbcolid": 999})) == ["Collection: NFO says 'Wizards', TMDB says 'Harry Potter Collection'"]
      and _mis(_cr110({"name": "Harry Potter Collection", "tmdbcolid": 99}))[0].startswith("Collection: NFO links TMDB collection 99"))   # P4 (F6)
check("B110c: a name in any TMDB language is the same collection; a user-made set and 'not checked' never warn",
      _mis(_cr110({"name": "harry potter – coleção", "tmdbcolid": 1241})) == []
      and _mis(_cr110({"name": "Disney"}, tm={"id": None, "when": 1})) == [] and _mis(_cr110({"name": "Disney"}, tm=None)) == [])
_sp110 = _cr.spellings_index([_cr110({"name": "Harry Potter Collection"}), _cr110({"name": "Harry Potter Collection"}),
                              _cr110({"name": "Harry Potter - Coleção"})])
check("B110c: one collection written two ways → 'written as X here and as Y in n other movies (Kodi shows two sets)'",
      _mis(_cr110({"name": "Harry Potter - Coleção"}), _sp110)
      == ["Collection: written as 'Harry Potter - Coleção' here and as 'Harry Potter Collection' in 2 other movies (Kodi shows two sets)"],
      _mis(_cr110({"name": "Harry Potter - Coleção"}), _sp110))
_k110 = mc._fix_issue_keys({"health_reasons": ["Collection: missing (TMDB: 'Backdrop Rating Saga')"]})
check("B110c: ⚠ Fix issues key collection (a collection name may hold any word: 'Backdrop Rating Saga' is not backdrops / ratings)",
      "collection" in _k110 and "backdrops" not in _k110 and "ratings" not in _k110, _k110)
_occ110 = dict(mc.COLL_CACHE); mc.COLL_CACHE.clear(); mc.COLL_CACHE.update(_cc110)
try:
    _rw110 = dict(_row110, coll_tmdb=_tm110, title_langs=["pt"], coll_nfo={"name": "Harry Potter Collection", "tmdbcolid": 1241},
                  nfo_title="Harry Potter e a Pedra Filosofal", tmdb_titles={"pt": "Harry Potter e a Pedra Filosofal"})
    mc.finalize_results([_rw110])                                   # the one name (P4: 1 of 1 title in Portuguese)
    _on110 = mc.compute_movie_health_detailed(_rw110, dict(mc.SETTINGS["health_rules"], collection_mismatch=True), mc.SETTINGS)
    _off110 = mc.compute_movie_health_detailed(_rw110, dict(mc.SETTINGS["health_rules"], collection_mismatch=False), mc.SETTINGS)
finally:
    mc.COLL_CACHE.clear(); mc.COLL_CACHE.update(_occ110)
check("B110c: the rules run inside the health check (warnings), and each one can be turned off",
      any(x.startswith("Collection:") for x in _on110[2]) and not any(x.startswith("Collection") for x in _off110[1] + _off110[2])
      and DEFAULT_SETTINGS["health_rules"]["collection_mismatch"] is True and "collection_language" not in DEFAULT_SETTINGS["health_rules"],
      (_on110[2], _off110[2]))
_rep110 = mc.format_health_report([dict(_row110, coll_tmdb=None, source_tmdb_val="603", health_status="ok", health_reasons=[]),
                                   dict(_row110, coll_tmdb=None, source_tmdb_val="", health_status="ok", health_reasons=[])])
check("B110c / P4: the Health report counts the movies whose collection was not checked online — only those that can be",
      "Collections not checked online: 1 movie (Tools → Check Collections Online)" in _rep110, _rep110[:400])

# ── v0.19.4 B110e: the <set> writer and the fix plan ──  ### NEW v0.19.4 B110e ###
_dw110 = tempfile.mkdtemp(prefix="mc_b110e_")
_pa110 = os.path.join(_dw110, "a.nfo")
_ba110 = b'\xef\xbb\xbf<?xml version="1.0" encoding="UTF-8"?>\r\n<movie>\r\n  <title>Saga</title>\r\n  <plot>A &amp; B</plot>\r\n</movie>\r\n'
open(_pa110, "wb").write(_ba110)
_w110 = mc.write_collection_to_nfo(_pa110, "Saga & Co", 77)
_aa110 = open(_pa110, "rb").read()
check("B110e: <set> written before </movie>: BOM, CRLF and every other byte kept, the name escaped, tmdbcolid",
      _w110 == (True, "") and _aa110 == _ba110.replace(b"</movie>", b'<set tmdbcolid="77">\r\n    <name>Saga &amp; Co</name>\r\n  </set>\r\n</movie>', 1).replace(
          b'  <plot>A &amp; B</plot>\r\n<set', b'  <plot>A &amp; B</plot>\r\n  <set', 1), _aa110)
_r2110 = mc.remove_collection_from_nfo(_pa110)
check("B110e: Remove from Collection gives the file back byte for byte", _r2110 == (True, "") and open(_pa110, "rb").read() == _ba110)
_pb110 = os.path.join(_dw110, "b.nfo")
open(_pb110, "wb").write(b"<movie>\n  <set>Old Name</set>\n  <set>Second</set>\n  <title>T</title>\n</movie>\n")
mc.write_collection_to_nfo(_pb110, "New Name", None, "Over")
check("B110e: the old one-line form becomes the Jarvis form in place; the 2nd <set> and the rest untouched; no tmdbcolid without an ID",
      open(_pb110, "rb").read() == b"<movie>\n  <set>\n    <name>New Name</name>\n    <overview>Over</overview>\n  </set>\n  <set>Second</set>\n  <title>T</title>\n</movie>\n",
      open(_pb110, "rb").read())
_pc110 = os.path.join(_dw110, "c.nfo")
_bc110 = "<movie>\n  <title>Coração</title>\n</movie>\n".encode("cp1252")
open(_pc110, "wb").write(_bc110)
_wc110 = mc.write_collection_to_nfo(_pc110, "X", 1)
check("B110e: a cp1252 NFO is refused (B37) and stays byte for byte", _wc110[0] is False and open(_pc110, "rb").read() == _bc110, _wc110)
shutil.rmtree(_dw110, ignore_errors=True)
_cc110e = {"1241": {"names": {"en": "Harry Potter Collection", "pt": "Harry Potter - Coleção"}, "overviews": {"pt": "Ov PT"}}}
_tme = {"id": 1241, "name": "Harry Potter Collection", "when": 1}
_tte = {"pt": "Harry Potter e a Pedra Filosofal", "en": "Harry Potter and the Philosopher's Stone", "de": "Harry Potter und der Stein der Weisen"}
check("B110e: fix target (fix 9) — the name in the local title's language (with its overview), else English (not the library language)",
      _cr.fix_target({"coll_tmdb": _tme, "nfo_title": "Harry Potter e a Pedra Filosofal", "tmdb_titles": _tte}, _cc110e, "en-US")
      == ("Harry Potter - Coleção", 1241, "Ov PT", None)
      and _cr.fix_target({"coll_tmdb": _tme, "nfo_title": "Harry Potter and the Philosopher's Stone", "tmdb_titles": _tte}, _cc110e, "pt-BR")[0] == "Harry Potter Collection"
      and _cr.fix_target({"coll_tmdb": _tme, "title_langs": []}, _cc110e, "pt-BR")[0] == "Harry Potter Collection"
      and _cr.fix_target({"coll_tmdb": _tme, "nfo_title": "Harry Potter und der Stein der Weisen", "tmdb_titles": _tte}, _cc110e, "fr-FR")[0] == "Harry Potter Collection")
check("B110e: skipped — not checked online, a user-made set (never changed), already right",
      _cr.fix_target({"coll_tmdb": None}, _cc110e)[3].startswith("not checked online")
      and "your own collection is kept" in _cr.fix_target({"coll_tmdb": {"id": None}, "coll_nfo": {"name": "Disney"}}, _cc110e)[3]
      and _cr.fix_target({"coll_tmdb": _tme, "title_langs": ["en"], "coll_nfo": {"name": "Harry Potter Collection", "tmdbcolid": 1241}}, _cc110e)[3] == "already right")

# ── v0.19.4 B110f: the collection language fix (pure) ──  ### NEW v0.19.4 B110f ###
_cf = {"1241": {"names": {"en": "Harry Potter Collection", "pt": "Harry Potter - Coleção"}, "overviews": {"pt": "Ov PT"}}}
_tmf = {"id": 1241, "name": "Harry Potter Collection", "when": 1}
_a_f = {"movie_name": "A", "nfo_exists": True, "coll_nfo": {"name": "Harry Potter Collection"}, "coll_tmdb": _tmf, "title_langs": ["pt"],
        "tmdb_titles": {"pt": "Harry Potter e a Pedra Filosofal", "en": "Harry Potter and the Philosopher's Stone"}}
_b_f = {"movie_name": "B", "nfo_exists": True, "coll_nfo": {"name": "Harry Potter Collection", "tmdbcolid": 1241}, "coll_tmdb": None, "title_langs": []}
_c_f = {"movie_name": "C", "nfo_exists": True, "coll_nfo": {"name": "Other"}, "coll_tmdb": {"id": 9}, "title_langs": ["pt"]}
check("B110f: tmdb_titles from a /movie answer (empty translations left out)",
      _cr.titles_by_lang(_mv110) == {"pt": "Harry Potter e a Pedra Filosofal", "en": "Harry Potter and the Philosopher's Stone"})

# ── v0.19.4 B110g: the collection folder ──  ### NEW v0.19.4 B110g ###
check("B110g: the set folder — exact; case-only (found, Windows / SMB); accent-only is NOT the folder (named)",
      _cr.match_folder("Harry Potter Collection", ["harry potter collection"]) == ("harry potter collection", "case")
      and _cr.match_folder("Coleção", ["Colecao"]) == ("Colecao", "accent") and _cr.match_folder("X", ["Y"]) == (None, None)
      and _cr.match_folder("X", ["X"]) == ("X", None))
check("B110g: art files by type (any picture extension, any case); other files ignored",
      _cr.art_types(["Poster.PNG", "fanart.jpg", "clearlogo.webp", "notes.txt", "set.nfo"]) == {"poster": "Poster.PNG", "fanart": "fanart.jpg", "clearlogo": "clearlogo.webp"})
check("B110g: warnings — folder missing (an accent look-alike named), poster / fanart missing; not checked → none",
      _cr.artwork_reasons({"dir": None, "near": "accent", "near_name": "Colecao"})[0].startswith("Collection artwork: folder missing (a folder 'Colecao' exists")
      and _cr.artwork_reasons({"dir": "x", "art": {"poster": "poster.jpg"}}) == ["Collection artwork: fanart missing"]
      and _cr.artwork_reasons(None) == [])
_imgs110 = [{"file_path": "/en.jpg", "iso_639_1": "en", "width": 2000, "height": 3000},
            {"file_path": "/pt.jpg", "iso_639_1": "pt", "width": 500, "height": 750},
            {"file_path": "/none.jpg", "iso_639_1": None, "width": 1000, "height": 1500}]
check("B110g: image choice — poster in the library language first; fanart without language first",
      _cr.pick_image(_imgs110, "poster", "pt-BR")["file_path"] == "/pt.jpg" and _cr.pick_image(_imgs110, "fanart", "pt-BR")["file_path"] == "/none.jpg"
      and _cr.pick_image([], "poster") is None)
_dg110 = tempfile.mkdtemp(prefix="mc_b110g_")
os.makedirs(os.path.join(_dg110, "Star Wars_ Episode I_")); open(os.path.join(_dg110, "Star Wars_ Episode I_", "poster.jpg"), "wb").write(b"x")
os.makedirs(os.path.join(_dg110, "Colecao"))
_rf110 = mc.read_collection_folders(_dg110, ["Star Wars: Episode I? ", "Coleção", "Absent"])
check("B110g: the reader — Kodi's legal name, the art found, an accent look-alike, a missing folder; an unreachable root → None",
      _rf110[_cr.norm_name("Star Wars: Episode I? ")]["art"] == {"poster": "poster.jpg"}
      and _rf110[_cr.norm_name("Coleção")]["dir"] is None and _rf110[_cr.norm_name("Coleção")]["near"] == "accent"
      and _rf110["absent"]["dir"] is None and mc.read_collection_folders(os.path.join(_dg110, "nope"), ["x"]) is None, _rf110)
_ref110 = [None]
_bk110 = tempfile.mkdtemp(prefix="mc_b110g_bk_")
_made110 = os.path.join(_dg110, "New Set"); os.makedirs(_made110)
_new110 = os.path.join(_made110, "poster.jpg"); open(_new110, "wb").write(b"img")
_ok110 = sc.note_created(_bk110, "New Set", _ref110, _new110, _made110)
_res110 = sc.restore_backup_run(_bk110, _ref110[0])
check("B110g: Undo of a created file — Backup History removes it and the folder the run made",
      _ok110 and not os.path.exists(_new110) and not os.path.exists(_made110) and _res110[0] == [os.path.abspath(_new110)], _res110)
shutil.rmtree(_dg110, ignore_errors=True); shutil.rmtree(_bk110, ignore_errors=True)

# ── v0.19.4 B110h: the grouped view (pure parts) ──  ### NEW v0.19.4 B110h ###
_src_h = io.open(mc.__file__, encoding="utf-8").read().splitlines()
_direct_h = [i + 1 for i, ln in enumerate(_src_h) if ("self.tree.get_children()" in ln or "self.tree.selection()" in ln)
             and "B110h helper" not in ln]
check("B110h: no caller reads the tree's rows or selection directly (only the helpers _view_movie_iids / _selected_rows …)",
      not _direct_h, _direct_h[:8])
_big_h = [{"movie_name": f"M{i:05d}", "health_status": "ok", "movie_year": "2000",
           "coll_nfo": ({"name": f"Saga {(i // 3) % 1500}"} if i % 3 else None)} for i in range(10000)]
_t_h = time.perf_counter(); _g_h = _cr.group_rows(_big_h); _dt_h = time.perf_counter() - _t_h
check(f"B110h: 10,000 movies in 1,500 collections grouped in {_dt_h * 1000:.0f} ms (< 300 ms)",
      _dt_h < 0.3 and sum(1 for x in _g_h if x[0] == "coll") == 1500 and sum(1 for x in _g_h if x[0] == "movie") == 3334, round(_dt_h, 3))
# ### NEW v0.19.5 B118 ### a collection row under a text column, and under a number column
_rows118 = [{"movie_name": "Alpha", "movie_year": "2000", "health_status": "ok"},
            {"movie_name": "Zulu One", "movie_year": "2005", "health_status": "ok", "coll_nfo": {"name": "Mango Saga"}},
            {"movie_name": "Bravo", "movie_year": "2001", "health_status": "ok", "coll_nfo": {"name": "Mango Saga"}},
            {"movie_name": "Yankee", "movie_year": "2003", "health_status": "ok"}]
def _names118(spec):
    _v = mc._se.sort_rows(_rows118, spec, mc.SORT_VALUE_FNS, mc._sort_name_key, mc._sort_year_key)
    return [x[2] if x[0] == "coll" else x[1]["movie_name"] for x in _cr.group_rows(_v, mc.group_order(spec))]
check("B118: A → Z, a collection row sits by its own name", _names118([{"key": "movie_name", "dir": "asc"}]) == ["Alpha", "Mango Saga", "Yankee"], _names118([{"key": "movie_name", "dir": "asc"}]))
check("B118: Z → A too", _names118([{"key": "movie_name", "dir": "desc"}]) == ["Yankee", "Mango Saga", "Alpha"], _names118([{"key": "movie_name", "dir": "desc"}]))
check("B118: another kind of column: it stays where its first movie sits", mc.group_order([{"key": "year", "dir": "newest"}]) is None
      and _names118([{"key": "year", "dir": "newest"}]) == ["Mango Saga", "Yankee", "Alpha"], _names118([{"key": "year", "dir": "newest"}]))
_o118 = mc.group_order([{"key": "movie_name", "dir": "asc"}])
_t118 = time.perf_counter(); _cr.group_rows(_big_h, _o118); _dt118 = time.perf_counter() - _t118
check(f"B118: 10,000 movies grouped and placed in {_dt118 * 1000:.0f} ms (< 300 ms)", _dt118 < 0.3, round(_dt118, 3))
check("B110h: year span and the worst health of a collection",
      _cr.year_span([{"movie_year": "2011"}, {"movie_year": "2001"}, {"movie_year": "-"}]) == "2001–2011"
      and _cr.worst_health([{"health_status": "ok"}, {"health_status": "error"}]) == "error" and DEFAULT_SETTINGS["group_by_collection"] is False)

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
check("Identify preset: links + outline", hdr == ["Movie Name", "Year", "IMDb Link", "TMDB Link", "Outline"] and data[0][2] == "https://www.imdb.com/title/tt0000001/" and data[0][3] == "https://www.themoviedb.org/movie/123", data[0])
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
_jpeg(os.path.join(_TMP, "real4.jpg"), 8, 8); _REAL_JPEG4 = open(os.path.join(_TMP, "real4.jpg"), "rb").read()   ### NEW v0.19.4 B79 ###
def _fake_open(req, timeout=None):
    calls["n"] += 1
    if calls["n"] < 3:
        raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, io.BytesIO(b"{}"))
    return _Resp(_REAL_JPEG4)                    ### MODIFIED v0.19.4 B79 — was b"\xff\xd8JPEGDATA" (not an image) ###
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

_b26_calls = []                                                   ### NEW v0.19.2 B26 — spy on the window icon ###
_b26_orig_iconbitmap = mc.App.iconbitmap
def _b26_spy(self, *a, **k):
    _b26_calls.append((a, k))
    return _b26_orig_iconbitmap(self, *a, **k)
mc.App.iconbitmap = _b26_spy
try:
    app = mc.App()
finally:
    mc.App.iconbitmap = _b26_orig_iconbitmap
app.withdraw()
n_movies =len([d for d in os.listdir(LIB) if os.path.isdir(os.path.join(LIB, d))])
shared = {}

def _pkey62(row):
    return mc._pkey(row["subfolder_path"])

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
    mc.ui_post(_run)                       # ### MODIFIED v0.19.5 I25 ### a.after() from this thread blocks with no limit on a stuck Tk thread
    if not ev.wait(timeout):
        raise RuntimeError(f"on_ui: main thread did not run the step within {timeout} s")
    if "e" in box:
        raise RuntimeError(box["e"])
    return box.get("r")

def _fire(w, seq, delta=0, x=0, y=0, rootx=0, rooty=0):      ### NEW v0.19.5 I24 ###
    """Tk thread: run w's bindings for seq in bindtag order, as Tk would, with no keyboard focus involved. event_generate
    sends key and wheel events to the window with the focus, so another window in front made those checks fail.
    Returns how many bindings ran, so a binding that is gone fails the check that asked for it."""
    vals = {"W": str(w), "D": str(delta), "x": str(x), "y": str(y), "X": str(rootx), "Y": str(rooty), "%": "%"}
    ran = 0
    for tag in w.bindtags():
        script = str(w.tk.call("bind", tag, seq))
        if not script:
            continue
        ran += 1
        code = str(w.tk.eval("catch {" + re.sub(r"%(.)", lambda m: vals.get(m.group(1), "0"), script) + "}"))
        if code == "1":
            raise RuntimeError(f"_fire {seq} on {w}: {w.tk.eval('set errorInfo')}")
        if code == "3":                                           # the binding said "break"
            break
    if not ran:
        raise RuntimeError(f"_fire: no binding for {seq} on {w}")
    return ran

_SETTLE_KNOWN = set(threading.enumerate())                    ### NEW v0.19.5 I23 ###

def _settle(timeout=20):
    """Wait for the result of the last action, not for a fixed time: the threads started since the last _settle have
    ended, the queue has passed a marker (a request posted earlier has arrived), no refresh is due or running, the table
    is not filling, and nothing changed during that round. Test thread only."""
    a = _UI_APP[-1]
    me = threading.current_thread()
    def _new():
        return [t for t in threading.enumerate() if t not in _SETTLE_KNOWN and t is not me and t is not threading.main_thread()]
    def _quiet():
        return not _new() and a._refresh_idle() and not getattr(a, "_tbl_filling", False)
    end = time.time() + timeout
    done = False
    while time.time() < end:
        if _quiet():
            r0 = a._rf_runs
            on_ui(lambda: None, timeout=max(1, end - time.time()))
            if _quiet() and a._rf_runs == r0:
                done = True
                break
        time.sleep(0.02)
    if not done:
        print(f"   note: _settle gave up after {timeout} s: threads {[t.name for t in _new()]}, refresh idle {a._refresh_idle()}")
    _SETTLE_KNOWN.update(threading.enumerate())
    return done

def _flat57(menu, out=None, depth=0):                       ### NEW v0.19.2 B57 — every entry of a menu tree ###
    """[(depth, label, state, menu, index)] — separators skipped, cascades followed (Tk thread)."""
    out = [] if out is None else out
    end = menu.index("end")
    for i in range(0 if end is None else end + 1):
        t = menu.type(i)
        if t == "separator":
            continue
        out.append((depth, menu.entrycget(i, "label"), str(menu.entrycget(i, "state")), menu, i))
        if t == "cascade":
            _flat57(menu.nametowidget(menu.entrycget(i, "menu")), out, depth + 1)
    return out

def kids(app_=None):
    """The table rows, read on the main thread."""
    return on_ui(lambda: list((app_ or _UI_APP[-1]).tree.get_children()), app_=app_)

_UI_APP.append(app)

def ui_tests():
    try:
        # ### NEW v0.19.5 I25 ### a stuck Tk thread: on_ui raises within its timeout, it does not wait for the Tk thread
        mc.ui_post(time.sleep, 3)
        _t25 = time.monotonic(); _e25 = ""
        try:
            on_ui(lambda: None, timeout=1)
        except RuntimeError as _x25:
            _e25 = str(_x25)
        _dt25 = time.monotonic() - _t25
        check("I25: a stuck Tk thread makes on_ui raise within its timeout", "did not run the step" in _e25 and _dt25 < 2.5, (round(_dt25, 2), _e25))
        on_ui(lambda: None)                # the Tk thread is free again
        # ### NEW v0.19.5 B113 ### idle: the slower rate; the first item is still picked up quickly and restores the fast rate
        wait_for(lambda: getattr(app, "_ui_idle_rounds", 0) >= 40, 30)
        _idle113 = getattr(app, "_ui_idle_rounds", 0)
        _t113 = time.monotonic(); on_ui(lambda: None); _dt113 = time.monotonic() - _t113
        check("B113: after 1 s with nothing queued the timer slows down, and the next item restores the fast rate",
              _idle113 >= 40 and getattr(app, "_ui_idle_rounds", 99) < 40, (_idle113, getattr(app, "_ui_idle_rounds", None)))
        check("B113: an item that arrives while idle waits at most about one slow round", _dt113 < 1.0, round(_dt113, 3))
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
        # ### MODIFIED v0.19.2 B35 (intended) ### the rule is OFF by default now: ON for this check
        _pfi35 = mc.SETTINGS["health_rules"].get("poster_folder_identical")
        mc.SETTINGS["health_rules"]["poster_folder_identical"] = True
        by = {r["subfolder"]: r for r in app._results}
        d_cf = by["Conflicting IDs"]
        _jpeg(d_cf["folder_path"], 600, 900, noisy=True)        # make folder.jpg differ
        on_ui(lambda: app._reval_no_ffmpeg(next(i for i, d in app._item_map.items() if d["subfolder"] == "Conflicting IDs"), d_cf))
        d_cf = {r["subfolder"]: r for r in app._results}["Conflicting IDs"]
        check("poster/folder differ detected", d_cf["poster_bytes"] != d_cf["folder_bytes"] and any("Poster and folder image are different" in x for x in d_cf["health_reasons"]), d_cf["health_reasons"])
        _boxes.clear()
        on_ui(lambda: app._copy_poster_to_folder([d_cf], confirm=False))
        wait_for(lambda: any("folder.jpg updated" in str(b) for b in _boxes), 30)
        _settle()          # v0.19.0: automatic refresh runs in the background
        d_cf = {r["subfolder"]: r for r in app._results}["Conflicting IDs"]
        check("copy poster → folder: sizes equal, warning gone, backup made", d_cf["poster_bytes"] == d_cf["folder_bytes"] and not any("Poster and folder image are different" in x for x in d_cf["health_reasons"]) and any(n.startswith("backup_") for n in os.listdir(_BK)), (d_cf["poster_bytes"], d_cf["folder_bytes"], d_cf["health_reasons"]))
        mc.SETTINGS["health_rules"]["poster_folder_identical"] = _pfi35        # v0.19.2 B35: back to the default
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
        _oa_imp = mc.messagebox.askyesno            # v0.19.4 B109b (intended): "Saved to … Open it now?" (answer No)
        mc.messagebox.askyesno = lambda *a, **k: (_boxes.append(("ask", a[:2])), False)[1]
        try:
            on_ui(lambda: app._run_improvements_batch(list(app._results), rep))
            _imp_ok = wait_for(lambda: any("Complete" in str(b) for b in _boxes), 60)
        finally:
            mc.messagebox.askyesno = _oa_imp
        check("improvements batch writes report", _imp_ok and os.path.getsize(rep) > 50, _boxes)
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
            check("v0.19 run 1: other valid source substituted (TMDB 6.0/50, OMDb was 0/0)", _rating_of(by["Bad Rating"]) == ("6.0", 50), _rating_of(by["Bad Rating"]))
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
        _n_backups = len([n for n in os.listdir(_BK) if n.startswith("backup_")])
        try:
            _boxes.clear()
            app._auto_repair_worker(list(_ar_rows), {"tmdb_key": "k", "omdb_key": "k", "lang": "en-US", "rating_pref": "votes", "multi": True, "fetch": _fake_tmdb5}, None)
            wait_for(lambda: bool(_summaries), 10); time.sleep(0.5)
            _txt = _summaries[0][1] if _summaries else ""
            def _ids(d): return mc.get_movie_ids_robust(d["nfo_path"], d["xml_path"])
            check("auto repair: exact title+year → IDs written to NFO and XML without asking", _ids(by["Auto Ids"]) == ("tt0009001", "9001") and mc.extract_source_ids_from_files(by["Auto Ids"]["nfo_path"], by["Auto Ids"]["xml_path"])["tmdb_status"] == mc.STATUS_OK, _ids(by["Auto Ids"]))
            check("auto repair: no exact match → chooser once, skip-all remembered", len(_chooser_calls) == 1 and _chooser_calls[0][0] == "Ask Ids" and _chooser_calls[0][2] is True and _ids(by["Ask Ids"])[1] is None, (_chooser_calls, _ids(by["Ask Ids"])))
            check("auto repair: conflicting IMDb resolved to the one TMDB confirms", _ids(by["Auto Conflict"]) == ("tt0000777", "777") and len(set(mc.extract_source_ids_from_files(by["Auto Conflict"]["nfo_path"], by["Auto Conflict"]["xml_path"])["imdb_all_vals"])) == 1, _ids(by["Auto Conflict"]))
            _bn = io.open(by["Bare Movie"]["nfo_path"], encoding="utf-8").read(); _bx = io.open(by["Bare Movie"]["xml_path"], encoding="utf-8").read()
            check("auto repair: year + genres from the verified TMDB ID", "<year>1995</year>" in _bn and "<ProductionYear>1995</ProductionYear>" in _bx and "<genre>Science Fiction</genre>" in _bn and "<Genre>Adventure</Genre>" in _bx, (_bn[:400], _bx[:400]))
            check("B121: auto repair leaves XML <Language> alone", "<Language>Portuguese</Language>" not in _bx, _bx[:500])
            check("auto repair: empty NFO <title> copied from XML <LocalTitle>", "<title>Title Copy</title>" in io.open(by["Title Copy"]["nfo_path"], encoding="utf-8").read())
            check("auto repair: ratings synced with the one-time choice (more votes → 8.4/900)", _rating_of(by["Auto Rating"]) == ("8.4", 900), _rating_of(by["Auto Rating"]))
            check("auto repair: genres normalized, synonyms resolved", mc.get_genres_from_nfo(by["Auto Genre"]["nfo_path"]) == ["Family", "Fantasy", "Science Fiction"], mc.get_genres_from_nfo(by["Auto Genre"]["nfo_path"]))
            check("auto repair: images untouched", all(_img_mtimes[d["subfolder"]] == tuple(os.path.getmtime(d[k + "_path"]) for k in ("poster", "folder", "fanart")) for d in _ar_rows))
            _n_backups2 = len([n for n in os.listdir(_BK) if n.startswith("backup_")])
            check("auto repair: one batch backup folder for the run (+ per-write rating backups)", _n_backups2 >= _n_backups + 1)
            _need = ["[FIXED", "skipped: no exact TMDB match", "Perfect Movie", "6 movies fixed", "still: "]
            _missing = [x for x in _need if x not in _txt]
            check("auto repair: summary dialog lists fixed / skipped / still failing", bool(_summaries) and "Auto Repair" in _summaries[0][0] and not _missing, (_missing, _txt[_txt.find("Perfect Movie"):][:300]))
            by2 = {r["subfolder"]: r for r in app._results}
            check("auto repair: rows refreshed in the table (no FFprobe), IDs now ⬤", by2["Auto Ids"]["source_tmdb_status"] == mc.STATUS_OK and by2["Auto Ids"] is not by["Auto Ids"] and not any("Missing TMDB ID" in x for x in by2["Auto Ids"]["health_reasons"]), by2["Auto Ids"]["health_reasons"])
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
            wait_for(lambda: len(app._rf_pending) == 5, 5)         # group C: the requests arrive through the queue
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
        # ### MODIFIED v0.19.2 B55 (intended) ### the dropdown entries carry the movie counts
        _cv55 = list(app._lib_combo.cget("values"))
        check("libraries: combobox lists All + both roots (with counts, B55)", len(_cv55) == 3 and _cv55[0].startswith(mc._ALL_LIBS + " (")
              and _cv55[1].startswith(LIB + " (") and _cv55[2].startswith(LIB2 + " ("), _cv55)
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
        # ── v0.19.2 B55: the window shows every library, also with a filter ───  ### NEW v0.19.2 B55 ###
        _fv55 = on_ui(app.folder_var.get)
        _mv55 = on_ui(lambda: (app._sb_movies.cget("text"), app._sb_libhidden.cget("text")))
        check("B55: with a filter the folder box still lists both libraries (▶ marks the shown one, 'showing 1 of 2')",
              LIB in _fv55 and ("▶ " + LIB2) in _fv55 and "showing 1 of 2 (filter)" in _fv55, _fv55)
        check("B55: the counters name the library and say '1 library hidden by the filter — show all'",
              _mv55[0].strip() == f"Movies: 3 ({LIB2})" and _mv55[1] == "· 1 library hidden by the filter — show all", _mv55)
        check("B55: the stats line has per-library counts", f"{os.path.basename(LIB)} {n_lib1}" in on_ui(app.stats_var.get)
              and f"{os.path.basename(LIB2)} 3" in on_ui(app.stats_var.get), on_ui(app.stats_var.get))
        on_ui(app._show_all_libraries)
        check("B55: 'show all' sets the filter to All libraries", mc.SETTINGS.get("library_filter") == "" and on_ui(lambda: app._sb_libhidden.cget("text")) == ""
              and "showing" not in on_ui(app.folder_var.get) and on_ui(app._lib_filter_var.get).startswith(mc._ALL_LIBS))
        on_ui(lambda: (app._lib_filter_var.set(LIB2), app._on_library_filter()))
        _oad55 = mc.filedialog.askdirectory
        mc.filedialog.askdirectory = lambda **k: LIB
        try:
            on_ui(app._browse)
        finally:
            mc.filedialog.askdirectory = _oad55
        check("B55: Browse… with an existing library switches to / stays on 'All libraries'", mc.SETTINGS.get("library_filter") == "", mc.SETTINGS.get("library_filter"))
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
            wait_for(lambda: not app._scanning and any("offline" in str(b).lower() for b in _boxes), 20)   # P6: listed in a worker
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
        mc._fetch_tmdb_rating = lambda tid, key: (mc._note_fetch_error("TMDB", mc.urllib.error.URLError("timed out") if hasattr(mc, "urllib") else RuntimeError("timed out")), (None, None))[1]
        mc._fetch_omdb_rating = lambda iid, key: (None, None)
        app._ask_ratings_dialog = lambda *a, **k: (_asked.append(1), {"choice": "cancel"})[1]
        try:
            _before = [_rating_of(by[n]) for n in ("Perfect Movie", "Rating Conflict")]
            _boxes.clear()
            app._sync_ratings_worker([by["Perfect Movie"], by["Rating Conflict"]], "k", "k", None)
            wait_for(lambda: any("Ratings Sync Complete" in str(b) for b in _boxes), 10)
            check("I2: unreachable source → no zero-votes prompt, nothing written", not _asked and [_rating_of(by[n]) for n in ("Perfect Movie", "Rating Conflict")] == _before, (_asked, _before))
            check("I2: summary lists the movies that could not be checked", any("could not be reached" in str(b) and "2 movies skipped" in str(b) for b in _boxes), _boxes)
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
            _settle()
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
        wait_for(lambda: not any(r["subfolder"] == "Delete Me Twin" for r in sc.load_results_cache()), 10)   # I22: the save may still run
        check("B2: cache updated + status bar message", not any(r["subfolder"] == "Delete Me Twin" for r in sc.load_results_cache()) and "Removed 1 movie" in on_ui(lambda: app._sb_action.cget("text")), on_ui(lambda: app._sb_action.cget("text")))
        _dm2 = make_movie("Delete Me Refresh", video=False)
        on_ui2(lambda: app._start_quick_scan(app._scope_roots())); wait_for(lambda: not app._scanning, 60)
        shutil.rmtree(_dm2)
        _d2 = {r["subfolder"]: r for r in app._results}["Delete Me Refresh"]
        app._schedule_refresh([_d2["subfolder_path"]])
        _settle()
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
        # ### MODIFIED v0.19.2 B53 (intended) ### an empty folder is "no media" now: the movie gets a video
        open(os.path.join(LIB3, "Lib3 Movie", "Lib3 Movie.mkv"), "wb").write(b"\0" * 64)
        ld3 = on_ui2(lambda: mc._LibrariesDialog(app))
        on_ui2(lambda: ld3.add_path(LIB3.replace("\\", "/")))
        if sys.platform == "win32": check("B3: dialog shows the added path with backslashes", ld3._items[-1] == os.path.normpath(LIB3) and "/" not in ld3._items[-1], ld3._items)
        on_ui2(lambda: ld3._ok())
        if sys.platform == "win32": check("B3: settings store backslash paths", all("/" not in x for x in mc.SETTINGS["library_folders"]), mc.SETTINGS["library_folders"])
        check("B4: adding a library offers a scan with Quick Scan as default", app._lib_prompt is not None and app._lib_prompt.default_kind == "quick")
        on_ui2(lambda: app._lib_prompt._buttons["quick"].invoke())
        wait_for(lambda: not app._scanning, 60); time.sleep(0.3); wait_for(lambda: not app._scanning, 60)
        check("B4: Quick Scan from the prompt adds the new library's movie (B53: a folder with a video)", "Lib3 Movie" in {r["subfolder"] for r in app._results})
        check("B4: no prompt when the list did not change", (on_ui2(lambda: app._set_libraries(app._libraries())) or (set(), set())) == (set(), set()))
        on_ui2(lambda: app._set_libraries([x for x in app._libraries() if mc._pkey(x) != mc._pkey(LIB3)]))
        _boxes.clear()

        # ── v0.19.1 B5: Normalize Genres fetches missing genres online ────────
        section("5l. genres from TMDB/OMDb (v0.19.1 B5)")
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
            app._normalize_genres_worker([by[n] for n in ("No Genres TMDB", "No Genres OMDb", "No Genres No Id", "No Genres Wrong Film")], None)
            wait_for(lambda: not any("Missing genre" in x for x in next((r for r in app._results if r["subfolder"] == "No Genres TMDB"), {}).get("health_reasons", ["Missing genre"])), 20)   # the row itself: the refresh request comes through the queue
            wait_for(app._refresh_idle, 20)
        finally:
            mc._tmdb_rate_limited_fetch, mc._http_get_json = _orl, _ohg
            mc.SETTINGS["tmdb_api_key"], mc.SETTINGS["omdb_api_key"] = _old_k
            del app._ask_genre_preview
        _pv = _previews[0] if _previews else ""
        check("B5: one preview listing every fetched movie and the skipped ones", len(_previews) == 1 and "No Genres TMDB" in _pv and "Comedy/Science Fiction" in _pv and "No Genres No Id: no IMDb/TMDB ID" in _pv and "Verify IDs says" in _pv, _pv)
        check("B5: TMDB genres written to NFO and XML", mc.get_genres_from_nfo(by["No Genres TMDB"]["nfo_path"]) == ["Comedy", "Science Fiction"] and mc.get_genres_from_xml(by["No Genres TMDB"]["xml_path"]) == ["Comedy", "Science Fiction"])
        check("B5: OMDb fallback (Sci-Fi → Science Fiction)", mc.get_genres_from_nfo(by["No Genres OMDb"]["nfo_path"]) == ["Drama", "Science Fiction"], mc.get_genres_from_nfo(by["No Genres OMDb"]["nfo_path"]))
        check("B5: no ID / wrong-film ID → nothing written", mc.get_genres_from_nfo(by["No Genres No Id"]["nfo_path"]) == [] and mc.get_genres_from_nfo(by["No Genres Wrong Film"]["nfo_path"]) == [])
        by2 = {r["subfolder"]: r for r in app._results}
        check("B5: rows refreshed — 'Missing genre' gone for the fetched movies", not any("Missing genre" in x for x in by2["No Genres TMDB"]["health_reasons"]) and any("Missing genre" in x for x in by2["No Genres No Id"]["health_reasons"]))
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
        _settle()
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
            def advance(s, k): s.n = k                          # v0.19.4 L5: was update() (intended)
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
        check("B14: header 'Current: IMDb tt12817760 · TMDB —'", "Current: IMDb tt12817760 · TMDB —" in ssd14._labels, ssd14._labels)
        _pb = ssd14._pinned_btns.get(_rowpp["movie_name"])
        check("B14: pinned row 'IMDb tt12817760 — not on TMDB · Padre Pio, uomo di Dio (1999)' + Confirm IMDb", "IMDb tt12817760 — not on TMDB · Padre Pio, uomo di Dio (1999)" in ssd14._labels and _pb and _pb[0] == "Confirm IMDb", (ssd14._labels, _pb))
        _boxes.clear()
        on_ui(lambda: _pb[1].invoke())
        _settle()
        _nt, _xt = io.open(_rowpp["nfo_path"], encoding="utf-8").read(), io.open(_rowpp["xml_path"], encoding="utf-8").read()
        _ok_tags = all(s in _nt for s in (f"<id>{_PP_IMDB}</id>", f"<imdbid>{_PP_IMDB}</imdbid>", f'<id moviedb="imdb">{_PP_IMDB}</id>')) \
                   and all(f"<{t}>{_PP_IMDB}</{t}>" in _xt for t in ("IMDB", "IMDbId", "IMDB_ID"))
        _empty_tm = "<tmdbid></tmdbid>" in _nt and '<id moviedb="tmdb"></id>' in _nt and all(f"<{t}></{t}>" in _xt for t in ("TMDB", "TMDbId", "TMDB_ID"))
        check("B14: Confirm IMDb → tt12817760 in every IMDb tag of both files, empty TMDB tags, valid XML", _ok_tags and _empty_tm and _valid(_rowpp["nfo_path"], _rowpp["xml_path"]), (_nt[-400:], _xt[-400:]))
        _rp = {r["subfolder"]: r for r in app._results}["Padre Pio, Uomo di Dio (1999)"]
        check("B14: row refreshed — IMDb ⬤, TMDB ○, id_check 'OK (IMDb only — not on TMDB)'", _rp["source_imdb_status"] == mc.STATUS_OK and _rp["source_tmdb_status"] == mc.STATUS_MISSING and (_rp.get("id_check") or {}).get("result") == mc.ID_IMDB_ONLY, (_rp["source_imdb_status"], _rp["source_tmdb_status"], _rp.get("id_check")))
        check("B14: 'Confirmed' message, no error box", any(b[0] == "info" and "Confirmed" in str(b[1]) for b in _boxes) and not any(b[0] == "error" for b in _boxes), _boxes)
        # Enter ID… with an IMDb ID TMDb does not know
        _ok14 = (mc.SETTINGS.get("tmdb_api_key", ""), mc.SETTINGS.get("omdb_api_key", ""))
        mc.SETTINGS["tmdb_api_key"] = "k"; mc.SETTINGS["omdb_api_key"] = "k"
        try:
            ed14 = on_ui(lambda: mc._EnterIdDialog(app, "Padre Pio Enter Id"))
            ed14._omdb_fetch = lambda url: {"Response": "True", "Title": "Padre Pio Two", "Year": "2001"}
            on_ui(lambda: (ed14._imdb_var.set("tt12817761"), ed14.lookup(fetch=_f14b, sync=True)))
            _inf = on_ui(lambda: ed14._info.cget("text")); _st = on_ui(lambda: str(ed14._apply_btn.cget("state")))
            check("B14: Enter ID… accepts an IMDb ID unknown to TMDB ('Not on TMDB — IMDb only', OMDb title, Apply enabled)", "Not on TMDB — IMDb only" in _inf and "Padre Pio Two" in _inf and _st == "normal", (_inf, _st))
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
        _settle()
        _n2 = io.open(_rowpp2["nfo_path"], encoding="utf-8").read()
        _rp2 = {r["subfolder"]: r for r in app._results}["Padre Pio Enter Id"]
        check("B14: Enter ID… IMDb-only Apply writes the IMDb ID + empty TMDB tags and records 'IMDb only'", "<imdbid>tt12817761</imdbid>" in _n2 and "<tmdbid></tmdbid>" in _n2 and (_rp2.get("id_check") or {}).get("result") == mc.ID_IMDB_ONLY, (_n2[-300:], _rp2.get("id_check")))
        # TMDb-only movie: pinned 'From your current TMDb ID' + Apply
        ssd14c = on_ui(lambda: mc._SearchSourcesResultDialog(app, [_e14c], [_r14c]))
        _pc = ssd14c._pinned_btns.get(_r14c["movie_name"])
        check("B14: TMDB-only movie → 'From your current TMDB ID: The Matrix …' with Apply", any(l.startswith("From your current TMDB ID:  The Matrix") for l in ssd14c._labels) and _pc and _pc[0] == "Apply", ssd14c._labels)
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
            _settle()
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
        check("B17: fewer online → 'You have 14 … TMDB offers 8 … leave you with 8 (6 fewer)' + 'Replace anyway'", _m17[0] == "You have 14 backdrops. TMDB offers 8.\nReplacing would leave you with 8 (6 fewer)." and _m17[1] == "Replace anyway" and _m17[2] is True, _m17)
        _m17b = mc.backdrop_count_message(3, 8)
        check("B17: more online → both numbers in a one-step confirmation ('Replace')", "You have 3 backdrops. TMDB offers 8." in _m17b[0] and "gives you 8 (5 more)" in _m17b[0] and _m17b[1] == "Replace" and _m17b[2] is False, _m17b)
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
        _bk = lambda: sorted(n for n in os.listdir(_BK) if "Backdrop" in n and "Many" in n)
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
            _bfiles = os.listdir(os.path.join(_BK, _newbk[0])) if _newbk else []
            check("B17 (fixed data-loss bug): all 6 original backdrops really are in the backup folder", len([f for f in _bfiles if f.startswith("backdrop")]) == 6, (_newbk, _bfiles))
        finally:
            mc._tmdb_rate_limited_fetch, mc._tmdb_download_image = _orl17, _odl17
            mc.SETTINGS["tmdb_api_key"] = _ok17
            del app._ask_backdrop_count
        _boxes.clear()

        # ── v0.19.3 B61: Replace All Backdrops — how many, best first ──────────   ### NEW v0.19.3 B61 ###
        section("5t2. Replace All Backdrops: how many (v0.19.3 B61)")
        _cd61 = on_ui(lambda: mc._BackdropCountDialog(app, "Count Movie", 6, 12))
        check("B61: the dialog opens with the current count (6 of 12) and 'Replace'",
              on_ui(lambda: _cd61._n_var.get()) == "6" and "You will get 6" in _cd61.message and _cd61.button_label == "Replace", _cd61.message)
        on_ui(lambda: _cd61._n_var.set("abc"))
        check("B61: an invalid number disables Replace and says why",
              on_ui(lambda: str(_cd61._ok_btn.cget("state"))) == "disabled" and "from 1 to 12" in _cd61.message, _cd61.message)
        on_ui(lambda: _cd61._n_var.set("3"))
        on_ui(_cd61._ok)
        check("B61: OK returns the source and the number", _cd61.result is True and _cd61.count == 3, (_cd61.result, _cd61.count))
        mc._LAST_IMAGE_SOURCE[0] = None
        _cd61b = on_ui(lambda: mc._BackdropCountDialog(app, "Fan Count", 5, 1, sources={"tmdb": 10, "fanarttv": 4}))
        on_ui(lambda: (_cd61b.choice.set("fanarttv"), _cd61b._recount()))
        check("B61: a source with fewer images clamps the number (10 → fanart.tv 4) and notes fanart.tv's sizes",
              on_ui(lambda: _cd61b._n_var.get()) == "4" and "offers 4" in _cd61b.message
              and "no image sizes" in on_ui(lambda: _cd61b._fan_lbl.cget("text")), (on_ui(lambda: _cd61b._n_var.get()), _cd61b.message))
        on_ui(_cd61b.destroy)
        mc._LAST_IMAGE_SOURCE[0] = None
        # the worker: 3 of 8, the 3 largest; a failed one is replaced by the next
        _d61 = os.path.join(_TMP, "b61", "Count Backdrops"); os.makedirs(_d61, exist_ok=True)
        for _i in range(2):
            _jpeg(os.path.join(_d61, "backdrop.jpg" if _i == 0 else f"backdrop{_i}.jpg"), 640, 360)
        _row61 = {"source_tmdb_val": "761001", "subfolder_path": _d61, "movie_name": "Count Backdrops", "subfolder": "Count Backdrops"}
        _sizes61 = [(1280, 720), (3840, 2160), (1920, 1080), (2560, 1440), (1366, 768), (3000, 1688), (800, 450), (2048, 1152)]
        _o61 = (mc._tmdb_rate_limited_fetch, mc._tmdb_download_image, mc.SETTINGS.get("tmdb_api_key", ""), mc.SETTINGS.get("fanarttv_api_key", ""))
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {"backdrops": [{"file_path": f"/w{w}.jpg", "width": w, "height": h} for w, h in _sizes61]}
        _dl61, _bad61 = [], set()
        def _fake_dl61(url, dest):
            _dl61.append(url)
            if any(url.endswith(f"/w{b}.jpg") for b in _bad61):
                return False, "HTTP 404"
            _jpeg(dest, 640, 360); return True, ""
        mc._tmdb_download_image = _fake_dl61
        mc.SETTINGS["tmdb_api_key"] = "k"; mc.SETTINGS["fanarttv_api_key"] = ""
        try:
            for _want, _bad, _label in ((3, set(), "plain"), (3, {3840}, "one fails"), (3, {3840, 3000, 2560, 2048, 1920, 1366}, "only 2 work")):
                _dl61.clear(); _bad61.clear(); _bad61.update(_bad); _boxes.clear()
                for f in os.listdir(_d61):
                    os.remove(os.path.join(_d61, f))
                for _i in range(2):
                    _jpeg(os.path.join(_d61, "backdrop.jpg" if _i == 0 else f"backdrop{_i}.jpg"), 640, 360)
                app._ask_backdrop_count = (lambda w: (lambda movie, local_n, online_n, sources=None: (True, w)))(_want)
                on_ui(lambda: app._replace_all_backdrops(_row61))
                wait_for(lambda: any("Replace All Backdrops" in str(b) for b in _boxes), 20)
                _files61 = sorted(f for f in os.listdir(_d61) if f.startswith("backdrop"))
                _ok61 = [u.rsplit("/w", 1)[1].split(".")[0] for u in _dl61 if not any(u.endswith(f"/w{b}.jpg") for b in _bad61)]
                if _label == "plain":
                    check("B61: 3 of 8 → exactly 3 files, the 3 largest (3840, 3000, 2560) in that order",
                          len(_files61) == 3 and _ok61 == ["3840", "3000", "2560"] and len(_dl61) == 3, (_files61, _dl61))
                elif _label == "one fails":
                    check("B61: a failed download is replaced by the next image (still 3: 3000, 2560, 2048)",
                          len(_files61) == 3 and _ok61 == ["3000", "2560", "2048"], (_files61, _dl61))
                else:
                    check("B61: only 2 work → 2 files and the summary says 'Only 2 of the 3 asked for'",
                          len(_files61) == 2 and any("Only 2 of the 3 asked for" in str(b) for b in _boxes), (_files61, _boxes))
            # ### NEW v0.19.4 B78 ### nothing arrives -> the originals stay and the result says so
            _dl61.clear(); _bad61.clear(); _bad61.update(w for w, _h in _sizes61); _boxes.clear()
            for f in os.listdir(_d61):
                os.remove(os.path.join(_d61, f))
            for _i in range(2):
                _jpeg(os.path.join(_d61, "backdrop.jpg" if _i == 0 else f"backdrop{_i}.jpg"), 640, 360)
            _before78 = {f: open(os.path.join(_d61, f), "rb").read() for f in os.listdir(_d61)}
            app._ask_backdrop_count = lambda movie, local_n, online_n, sources=None: (True, 3)
            on_ui(lambda: app._replace_all_backdrops(_row61))
            wait_for(lambda: any("Replace All Backdrops" in str(b) for b in _boxes), 20)
            _after78 = {f: open(os.path.join(_d61, f), "rb").read() for f in os.listdir(_d61)}
            check("B78: no download arrives -> the original backdrops stay untouched, no temp file, the result says 'Nothing was changed'",
                  _after78 == _before78 and any("Nothing was changed" in str(b) for b in _boxes)
                  and not any("Completed Successfully" in str(b) for b in _boxes), (sorted(_after78), _boxes))
            _bad61.clear(); _boxes.clear()
            on_ui(lambda: app._replace_all_backdrops(_row61))
            wait_for(lambda: any("Replace All Backdrops" in str(b) for b in _boxes), 20)
            _f78 = sorted(os.listdir(_d61))
            check("B78: a good run swaps after the downloads: 3 new backdrops under their final names, no temp file left",
                  len([f for f in _f78 if f.startswith("backdrop")]) == 3
                  and not any(f.endswith((".mcnew", ".mctmp")) for f in _f78)
                  and any("Completed Successfully" in str(b) for b in _boxes), (_f78, _boxes))
        finally:
            mc._tmdb_rate_limited_fetch, mc._tmdb_download_image = _o61[0], _o61[1]
            mc.SETTINGS["tmdb_api_key"], mc.SETTINGS["fanarttv_api_key"] = _o61[2], _o61[3]
            if "_ask_backdrop_count" in app.__dict__:
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
        _bk23 = lambda: sorted(n for n in os.listdir(_BK) if "Kodi" in n and "Png" in n)
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
        check("B23: the replaced .png poster (and folder.jpg) were backed up first", _nb and any(f.endswith("-poster.png") for f in os.listdir(os.path.join(_BK, _nb[0]))), (_nb, os.listdir(os.path.join(_BK, _nb[0])) if _nb else None))
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
        check("B22: the batch asked ONCE: OMDb daily limit, offering 'Continue with TMDB'", _asked22 == [("omdb", "daily_limit", "TMDB")], _asked22)
        _msg20 = " ".join(str(b) for b in _boxes if "Ratings Sync Complete" in str(b))
        check("B20: Ratings Sync asks OMDb once for 3 movies", _omdb_n() == 1, _omdb_n())
        check("B20: the other movies use TMDB (7.0 / 100 written)", [_rating_of(d) for d in _rows20[1:]] == [("7.0", 100), ("7.0", 100)], [_rating_of(d) for d in _rows20])
        check("B20: the final message says it once ('OMDb (IMDb data) unavailable for the rest of this run')", _msg20.count("unavailable for the rest of this run") == 1, _msg20[:400])
        check("B20: after the run nothing stays blocked (single-movie actions ask normally)", mc._service_blocked("omdb") is None)
        _settle()
        _boxes.clear()

        # ── v0.19.1 B22: pause indicator, Try anyway, failure dialog ────────────   ### NEW v0.19.1 B22 ###
        section("5x. TMDB/OMDb pause in the window (v0.19.1 B22)")
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
        _fdl = on_ui(lambda: mc._ServiceFailureDialog(app, "omdb", "daily_limit", "TMDB"))
        _fb = {k: on_ui(lambda b=b: b.cget("text")).strip() for k, b in _fdl.buttons.items()}
        check("B22: batch failure window — [Pause this run (until about …)] [Continue with TMDB] [Cancel]", _fb["pause"].startswith("Pause this run (until about ") and _fb["continue"] == "Continue with TMDB" and _fb["cancel"] == "Cancel", _fb)
        on_ui(lambda: _fdl.buttons["cancel"].invoke())
        check("B22: its Cancel answers 'cancel'", _fdl.result == "cancel")
        _fdk = on_ui(lambda: mc._ServiceFailureDialog(app, "tmdb", "invalid_key", None))
        check("B22: no pause offered for a rejected key; 'Continue without TMDB'", "pause" not in _fdk.buttons and on_ui(lambda: _fdk.buttons["continue"].cget("text")).strip() == "Continue without TMDB")
        on_ui(_fdk.destroy)
        _ss22 = on_ui(lambda: mc._SearchSourcesResultDialog(app, [dict(_e22s)], [_r14x]))
        check("B22: Search Sources says 'TMDB did not answer — …' instead of 'No results found'", any(l.startswith("TMDB did not answer — TMDB is receiving too many requests") for l in _ss22._labels) and not any("No results found" in l for l in _ss22._labels), _ss22._labels)
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
            check("I10: Fetch Backdrops — source selector TMDB | fanart.tv | Both, default Both, both lists merged",
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
            check("I10: count dialog — Both counts 5; TMDB (1 < 3) asks 'Replace anyway'; OK returns the source",
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
            _bk11 = lambda: sorted(n for n in os.listdir(_BK) if "Frame" in n)
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

                # ── v0.19.2 B28: closing the dialog / Stop kills the running FFmpeg; spinner ──  ### NEW v0.19.2 B28 ###
                _res28 = []
                _orig_emf28 = mc.extract_movie_frames
                def _fake_emf28(video, out_dir, n=10, cancel=None, state=None, **kw):
                    t = time.monotonic()
                    state.update(active=True, i=1, n=n, t_frame=t, t_run=t)
                    r = mc._run_ffmpeg(_sleep_cmd28(30), timeout=60, cancel=cancel)
                    state["active"] = False
                    _res28.append((r[0], time.monotonic()))
                    return [], "Stopped — 0 frame(s) extracted."
                mc.extract_movie_frames = _fake_emf28
                try:
                    _dq28 = on_ui(lambda: mc._FetchImageDialog(app, _row11, "fanart", "k", "711001"))
                    on_ui(_dq28._frames_btn.invoke)
                    wait_for(lambda: bool(mc._FF_PROCS), 10); time.sleep(0.5)
                    def _lbl28():
                        try:
                            return _dq28._ff_label.cget("text")
                        except Exception as ex:
                            return f"<label gone: {ex}>"
                    _sp28 = on_ui(_lbl28)
                    check("B28: Fetch Fanart shows a spinner 'Frame 1 / 10 · … on this frame · … total' and a Stop button",
                          _sp28[:1] in "◐◓◑◒" and "Frame 1 / 10" in _sp28 and "on this frame" in _sp28 and "total" in _sp28
                          and on_ui(lambda: _dq28._ff_stop_btn.cget("text")).strip() == "Stop", _sp28)
                    _tq28 = time.monotonic(); on_ui(_dq28._done); _tu28 = time.monotonic() - _tq28   # I21: how long the Tk thread took
                    wait_for(lambda: bool(_res28), 5)
                    check("B28: closing the Fetch dialog (Done) kills the running FFmpeg at once", _res28 and _res28[0][0] == mc.FF_CANCELLED and _res28[0][1] - _tq28 < 1.0 and not mc._FF_PROCS, (_res28, round(_res28[0][1] - _tq28, 2), "Tk thread", round(_tu28, 2) if _res28 else None))
                    # ### NEW v0.19.5 I21 ### Done during a download: the window waits for the download, FFmpeg does not
                    _dq21 = on_ui(lambda: mc._FetchImageDialog(app, _row11, "fanart", "k", "711001"))
                    on_ui(_dq21._frames_btn.invoke)
                    wait_for(lambda: bool(mc._FF_PROCS), 10); time.sleep(0.3)
                    on_ui(_dq21._dl_begin); on_ui(_dq21._done); _t21 = time.monotonic()   # from the moment the Tk thread ran it (I21's limit)
                    wait_for(lambda: len(_res28) == 2, 5)
                    check("I21: Done while a download runs: FFmpeg stops at once, the window stays ('Finishing…') until the download ends",
                          len(_res28) == 2 and _res28[1][0] == mc.FF_CANCELLED and _res28[1][1] - _t21 < 1.5 and not mc._FF_PROCS
                          and on_ui(_dq21.winfo_exists) and "Finishing" in on_ui(lambda: _dq21._done_btn.cget("text")), (_res28, time.monotonic() - _t21))
                    on_ui(_dq21._dl_end)
                    check("I21: …and it closes when the download ends", not on_ui(_dq21.winfo_exists))
                    del _res28[1:]
                    _db28 = on_ui(lambda: mc._FetchBackdropDialog(app, _row11, "k", "711001"))
                    on_ui(_db28._frames_btn.invoke)
                    wait_for(lambda: bool(mc._FF_PROCS), 10); time.sleep(0.3)
                    on_ui(_db28._ff_stop_btn.invoke)
                    wait_for(lambda: len(_res28) == 2, 5)
                    wait_for(lambda: "Stopped" in on_ui(lambda: _db28._status_lbl.cget("text")), 15)   # I22: the note after a busy Tk thread
                    check("B28: Stop in Fetch Backdrops stops FFmpeg and the dialog stays open with the note",
                          len(_res28) == 2 and _res28[1][0] == mc.FF_CANCELLED and not mc._FF_PROCS and on_ui(_db28.winfo_exists)
                          and "Stopped" in on_ui(lambda: _db28._status_lbl.cget("text")), (_res28, on_ui(lambda: _db28._status_lbl.cget("text"))))
                    on_ui(_db28._done)
                finally:
                    mc.extract_movie_frames = _orig_emf28
                    mc.kill_all_ffmpeg()                                  # never leave the fake FFmpeg running

                # ── v0.19.2 B29: selection keeps the scroll position; wheel everywhere ──  ### NEW v0.19.2 B29 ###
                import settings_dialog as _sdm29
                _src29 = io.open(mc.__file__, encoding="utf-8").read() + io.open(_sdm29.__file__, encoding="utf-8").read()
                check("B29: no bind_all('<MouseWheel>') left in the main script or settings_dialog.py",
                      'bind_all("<MouseWheel>"' not in _src29 and "bind_all('<MouseWheel>'" not in _src29 and 'bind_all("<Button-4>"' not in _src29)
                def _fake_emf29(video, out_dir, n=10, cancel=None, state=None, **kw):
                    os.makedirs(out_dir, exist_ok=True); out = []
                    for i in range(10):
                        p = os.path.join(out_dir, f"f29_{i}.jpg"); _jpeg(p, 1280, 720, noisy=True)
                        out.append({"source": "frame", "local": True, "url": p, "time": float(i), "width": 1280, "height": 720,
                                    "file_size": os.path.getsize(p), "votes": 0, "likes": 0, "lang": "", "dims_typical": False,
                                    "low_res": False, "min_level": "1080p", "thumbs": ()})
                    return out, None
                mc.extract_movie_frames = _fake_emf29
                try:
                    _db29 = on_ui(lambda: mc._FetchBackdropDialog(app, _row11, "k", "711001"))
                    on_ui(_db29._frames_btn.invoke)
                    wait_for(lambda: len(_db29._images) == 10 and len(_db29.__dict__.get("_thumb_cache", {})) >= 5, 30)
                    on_ui(_db29.update_idletasks)
                    on_ui(lambda: _db29._canvas.yview_moveto(0.6)); on_ui(_db29.update_idletasks)
                    _y0 = on_ui(lambda: _db29._canvas.canvasy(0))        # top pixel shown (the fraction changes when
                    _ids0 = on_ui(lambda: {gi: (str(w["row"]), str(w["thumb"])) for gi, w in _db29._tmdb_rows.items()})
                    on_ui(lambda: _db29._select_tmdb(3)); on_ui(_db29.update_idletasks)
                    _y1 = on_ui(lambda: _db29._canvas.canvasy(0))        # the '✓ Selected' line makes the list taller)
                    _ids1 = on_ui(lambda: {gi: (str(w["row"]), str(w["thumb"])) for gi, w in _db29._tmdb_rows.items()})
                    _sel29 = on_ui(lambda: {gi: w["sel"] is not None for gi, w in _db29._tmdb_rows.items()})
                    check("B29: selecting a backdrop keeps the scroll position (was: jump to the top)", _y0 > 50 and _y1 == _y0, (_y0, _y1))
                    check("B29: …no row is rebuilt; only the selected row shows '✓ Selected'", _ids1 == _ids0 and _sel29 == {0: False, 1: False, 2: False, 3: True, 4: False}, (_sel29, _ids0 == _ids1))
                    on_ui(lambda: _db29._select_tmdb(1))
                    _sel29b = on_ui(lambda: {gi: w["sel"] is not None for gi, w in _db29._tmdb_rows.items()})
                    check("B29: selecting another row restyles exactly the old and the new row", _sel29b == {0: False, 1: True, 2: False, 3: False, 4: False}, _sel29b)
                    _n_cache29 = len(_db29._thumb_cache)
                    on_ui(_db29._tmdb_more); on_ui(_db29._tmdb_back)
                    wait_for(lambda: len(_db29._thumb_cache) >= 10, 20)
                    check("B29: thumbnails are cached per image (going back shows page 1 without a new download)", _n_cache29 >= 5 and all(on_ui(lambda w=w: bool(str(w["thumb"].cget("image")))) for w in _db29._tmdb_rows.values()))
                    on_ui(lambda: _db29._canvas.yview_moveto(0)); on_ui(_db29.update_idletasks)
                    def _wheel29():
                        lbl = _db29._tmdb_rows[2]["thumb"]
                        _fire(lbl, "<MouseWheel>", delta=-240, x=5, y=5,
                              rootx=lbl.winfo_rootx() + 5, rooty=lbl.winfo_rooty() + 5)
                        _db29.update_idletasks()
                        return _db29._canvas.yview()
                    _y2 = on_ui(_wheel29)
                    check("B29: the mouse wheel over a thumbnail scrolls the list", _y2[0] > 0, _y2)
                    on_ui(_db29._done)
                finally:
                    mc.extract_movie_frames = _orig_emf28

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
                        # ### MODIFIED v0.19.2 B57 (intended) ### the actions live in submenus now
                        return {lbl: st for _dp, lbl, st, _m, _i in _flat57(app._ctx)}
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
        _settle()
        check("I1: the batch changed the files", all("Hardsub ITA" in io.open(p, encoding="utf-8").read() for p in _before_i1))
        _bh = on_ui(lambda: mc.BackupHistoryDialog(app))
        on_ui(lambda: _bh.load(sync=True))
        _top = on_ui(lambda: _bh._runs[0])
        check("I1: Backup History shows the batch first: action 'Hard-coded subtitles', 2 movies, 4 files, ready", _top["action"] == "Hard-coded subtitles" and _top["movies"] == 2 and len(_top["files"]) == 4 and not _top["changed"], (_top["action"], _top["movies"], len(_top["files"]), _top["changed"]))
        _boxes.clear()
        on_ui(lambda: (_bh._tree.selection_set("0"), _bh._show_files(), _bh._restore(sync=True)))
        _settle()
        check("I1: 'Restore this run' puts the files back exactly", all(io.open(p, encoding="utf-8").read() == c for p, c in _before_i1.items()))
        _rr_i1 = {r["subfolder"]: r for r in app._results}
        check("I1: the rows are refreshed after the restore (Hardsub SPA again, no ITA)", _rr_i1["Hardsub Movie"]["subs_hard"] == ["SPA"], _rr_i1["Hardsub Movie"].get("subs_hard"))
        check("I1: the restore message names the safety backup", any(re.search(r"\d+ files? restored", str(b)) and "before the undo" in str(b) for b in _boxes), _boxes)
        time.sleep(1.0); on_ui(lambda: None)        # the dialog reloads in the background after a restore — let it finish
        os.makedirs(os.path.join(_BK, "backup_Legacy_Test_2020-01-01_00-00-00"), exist_ok=True)
        on_ui(lambda: _bh.load(sync=True))
        _li = on_ui(lambda: next(i for i, r in enumerate(_bh._runs) if r["name"] == "backup_Legacy_Test_2020-01-01_00-00-00"))
        on_ui(lambda: (_bh._tree.selection_set(str(_li)), _bh._show_files()))
        check("I1: a legacy backup shows 'legacy (manual restore only)' and Restore is disabled", on_ui(lambda: _bh._tree.set(str(_li), "state")) == "legacy (manual restore only)" and on_ui(lambda: str(_bh._restore_btn.cget("state"))) == "disabled")
        on_ui(_bh.destroy)
        shutil.rmtree(os.path.join(_BK, "backup_Legacy_Test_2020-01-01_00-00-00"), ignore_errors=True)
        _boxes.clear()

        # ── v0.19.2 B26: window icon ──────────────────────────────────────    ### NEW v0.19.2 B26 ###
        if sys.platform == "win32": check("B26: App() set the default window icon once, with default=<MediaClinic.ico>", _b26_calls == [((), {"default": mc._app_icon_path()})], _b26_calls)
        _bad26 = os.path.join(_TMP, "broken.ico")
        with open(_bad26, "wb") as f:
            f.write(b"not an icon")
        _o26 = mc._app_icon_path
        try:
            mc._app_icon_path = lambda: _bad26
            on_ui(app._apply_app_icon)
            mc._app_icon_path = lambda: None
            on_ui(app._apply_app_icon)
        finally:
            mc._app_icon_path = _o26
        _log26 = io.open(mc.LOG_PATH, encoding="utf-8", errors="replace").read()
        if sys.platform == "win32": check("B26: a broken / missing .ico never stops the app (logged 'Window icon not set')", "Window icon not set" in _log26 and "MediaClinic.ico not found" in _log26 and on_ui(app.winfo_exists))
        if sys.platform == "win32": on_ui(lambda: app.iconbitmap(default=mc._app_icon_path()))    # back to the real icon

        # ── v0.19.2 B27: Tk callback errors reach app.log; notice once ──────  ### NEW v0.19.2 B27 ###
        _n27 = len(_UNH.records)
        on_ui(lambda: app.after(0, lambda: 1 / 0)); _UNH_PROVOKED.append("tk-1")
        wait_for(lambda: len(_UNH.records) > _n27, 5)
        wait_for(lambda: "ZeroDivisionError" in io.open(mc.LOG_PATH, encoding="utf-8", errors="replace").read(), 5)   # the file line may come later
        _l27 = io.open(mc.LOG_PATH, encoding="utf-8", errors="replace").read()
        check("B27: an error in a Tk callback is logged ('Unhandled exception (Tk callback)', ZeroDivisionError)", "Unhandled exception (Tk callback)" in _l27 and "ZeroDivisionError" in _l27)
        check("B27: the first one shows a status-bar notice", wait_for(lambda: "internal error was logged" in on_ui(lambda: app._sb_notice.cget("text")), 5), on_ui(lambda: app._sb_notice.cget("text")))
        on_ui(lambda: app._sb_set_notice(""))
        on_ui(lambda: app.after(0, lambda: [][1])); _UNH_PROVOKED.append("tk-2")
        wait_for(lambda: len(_UNH.records) > _n27 + 1, 5); time.sleep(0.2)
        check("B27: a second error adds a log line but no second notice", len(_UNH.records) == _n27 + 2 and on_ui(lambda: app._sb_notice.cget("text")) == "", (len(_UNH.records) - _n27, on_ui(lambda: app._sb_notice.cget("text"))))
        def _legacy_stats27():
            keep = app._results
            try:
                app._results = mc._results_from_json([{"subfolder": "OldRow", "subfolder_path": "X:/nowhere/OldRow"}])
                mc.finalize_results(app._results)
                app._update_stats()
                return True
            finally:
                app._results = keep
                app._update_stats()
        check("B27: the status bar counts a legacy cached row without KeyError", on_ui(_legacy_stats27) is True)

        # ── v0.19.2 B36: the user is told once about a settings.json that was kept aside ──  ### NEW v0.19.2 B36 ###
        _boxes.clear()
        sc.SETTINGS_LOAD_PROBLEM.update(error="Expecting value: line 3 column 1", corrupt_copy=r"C:\cfg\settings.json.corrupt-20261022-101500")
        on_ui(app._tell_settings_problem); on_ui(app._tell_settings_problem)
        _w36 = [b for b in _boxes if b[0] == "warning" and b[1][0] == "Settings file could not be read"]
        check("B36: one warning names the kept copy; asked twice → shown once", len(_w36) == 1 and "settings.json.corrupt-20261022-101500" in _w36[0][1][1] and not sc.SETTINGS_LOAD_PROBLEM.get("error"), _boxes)
        _boxes.clear()

        # ── v0.19.2 B47: Fetch Poster/Folder reports a folder.jpg it could not write ──  ### NEW v0.19.2 B47 ###
        import stat as _stat47
        _d47 = os.path.join(_TMP, "b47", "Locked Folder"); os.makedirs(_d47, exist_ok=True)
        io.open(os.path.join(_d47, "Locked Folder.nfo"), "w", encoding="utf-8").write("<movie>\n  <title>Locked Folder</title>\n</movie>\n")
        _jpeg(os.path.join(_d47, "poster.jpg"), 600, 900); _jpeg(os.path.join(_d47, "folder.jpg"), 600, 900)
        _fj47 = os.path.join(_d47, "folder.jpg")
        _fb47 = open(_fj47, "rb").read()
        os.chmod(_fj47, _stat47.S_IREAD)
        _r47 = mc.scan_one_subfolder(_d47, "Locked Folder", use_ffprobe=False)
        _o47 = (mc._tmdb_rate_limited_fetch, mc._tmdb_download_image)
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {"posters": [], "backdrops": [], "logos": []}
        def _dl47(url, dest):
            _jpeg(dest, 1000, 1500, noisy=True); return True, ""
        mc._tmdb_download_image = _dl47
        _boxes.clear()
        try:
            _fd47 = on_ui(lambda: mc._FetchImageDialog(app, _r47, "poster", "k", "747001"))
            on_ui(lambda: _fd47._apply_image("https://image.tmdb.org/t/p/original/p47.jpg"))
            wait_for(lambda: not on_ui(_fd47.winfo_exists), 15); time.sleep(0.2)
        finally:
            mc._tmdb_rate_limited_fetch, mc._tmdb_download_image = _o47
            os.chmod(_fj47, _stat47.S_IWRITE | _stat47.S_IREAD)
        _m47 = next((b for b in _boxes if b[1] and b[1][0] == "Fetch Complete"), None)
        if sys.platform == "win32": check("B47: a folder.jpg that cannot be written is named in the message (warning), poster.jpg is saved",
              _m47 is not None and _m47[0] == "warning" and "poster.jpg" in _m47[1][1].split("\n\n")[0]
              and "folder.jpg could not be written" in _m47[1][1] and "folder.jpg" not in _m47[1][1].split("\n\n")[0]
              and mc.get_image_wh(os.path.join(_d47, "poster.jpg")) == (1000, 1500) and open(_fj47, "rb").read() == _fb47, _boxes)
        _boxes.clear()

        # ── v0.19.2 B48: Search Sources names the files really written ────────  ### NEW v0.19.2 B48 ###
        _d48 = os.path.join(_TMP, "b48", "Nfo Only"); os.makedirs(_d48, exist_ok=True)
        io.open(os.path.join(_d48, "Nfo Only.nfo"), "w", encoding="utf-8").write("<movie>\n  <title>Nfo Only</title>\n</movie>\n")
        _r48 = mc.scan_one_subfolder(_d48, "Nfo Only", use_ffprobe=False)
        _pc48 = []
        _oinfo48 = mc.messagebox.showinfo
        mc.messagebox.showinfo = lambda *a, **k: (_pc48.append((a[:2], k.get("parent"))), _boxes.append(("info", a[:2])))
        try:
            _sd48 = on_ui(lambda: mc._SearchSourcesResultDialog(app, [{"movie_name": "Nfo Only", "year": "", "matches": []}], [_r48]))
            on_ui(lambda: _sd48._apply(_r48, "603", "tt0133093"))
        finally:
            mc.messagebox.showinfo = _oinfo48
        _a48 = [x for x in _pc48 if x[0] and x[0][0] == "Applied"]
        check("B48: a movie with only an NFO → 'Written to NFO.' (not 'NFO and XML'), message parented to the dialog",
              len(_a48) == 1 and _a48[0][0][1].endswith("Written to NFO.") and _a48[0][1] is _sd48, _pc48)
        check("B48: the label helper", mc._files_written_label("a.nfo", None) == "NFO" and mc._files_written_label(None, "m.xml") == "XML"
              and mc._files_written_label("a.nfo", "m.xml") == "NFO and XML")
        try:
            on_ui(_sd48.destroy)
        except Exception:
            pass
        _boxes.clear()

        # ── v0.19.2 B41: Sync Ratings write errors go into the summary ────────  ### NEW v0.19.2 B41 ###
        _d41 = os.path.join(_TMP, "b41")
        def _mk41(name, cp1252):
            d = os.path.join(_d41, name); os.makedirs(d, exist_ok=True)
            body = (f"<movie>\n  <title>{name}</title>\n  <rating>5.0</rating>\n  <votes>10</votes>\n"
                    f"  <imdbid>tt41{abs(hash(name)) % 100000:05d}</imdbid>\n  <tmdbid>41{abs(hash(name)) % 1000}</tmdbid>\n"
                    f"  <plot>{'Amélie' if cp1252 else 'Amelie'}</plot>\n</movie>\n")
            open(os.path.join(d, name + ".nfo"), "wb").write(body.encode("cp1252" if cp1252 else "utf-8"))
            return mc.scan_one_subfolder(d, name, use_ffprobe=False)
        _r41 = [_mk41("Writable One", False), _mk41("Latin Two", True), _mk41("Latin Three", True)]
        _o41 = (mc._fetch_tmdb_rating, mc._fetch_omdb_rating, app._ask_ratings_dialog)
        mc._fetch_tmdb_rating = lambda tid, key: ("7.7", "1234")
        mc._fetch_omdb_rating = lambda iid, key: ("7.7", "1234")
        app._ask_ratings_dialog = lambda *a, **k: {"choice": "tmdb", "apply_all": True, "use_more_votes": False,
                                                    "manual_r": None, "manual_v": None, "apply_fallback": False}
        _boxes.clear()
        try:
            app._sync_ratings_worker(_r41, "k", "k", None); wait_for(lambda: any(b[1] and b[1][0] == "Ratings Sync Complete" for b in _boxes), 10)
        finally:
            mc._fetch_tmdb_rating, mc._fetch_omdb_rating, app._ask_ratings_dialog = _o41
        _sum41 = next((b[1][1] for b in _boxes if b[1] and b[1][0] == "Ratings Sync Complete"), "")
        check("B41: no pop-up per movie for write errors; the summary says '1 updated' and '2 could not be written'",
              not any(b[1] and b[1][0] == "Write Error" for b in _boxes) and "; 1 updated." in _sum41
              and "2 could not be written:" in _sum41 and "Latin Two" in _sum41 and "not UTF-8" in _sum41, (_boxes, _sum41))
        _boxes.clear()

        # ── v0.19.2 B35: the migration notice is shown once, from the App ─────  ### NEW v0.19.2 B35 ###
        _boxes.clear()
        sc.SETTINGS_MIGRATION_NOTICES[:] = [sc.B35_NOTICE]
        on_ui(app._tell_migrations); on_ui(app._tell_migrations)
        _m35 = [b for b in _boxes if b[1] and b[1][0] == "Health rules changed"]
        check("B35: the App shows the 'Health rules changed' message once (from after(), never at import)",
              len(_m35) == 1 and "Missing folder image" in _m35[0][1][1] and not sc.SETTINGS_MIGRATION_NOTICES, _boxes)
        _boxes.clear()

        # ── v0.19.2 B30: Search Sources "not found" → empty ID tags ──────────  ### NEW v0.19.2 B30 ###
        _d30 = os.path.join(_TMP, "b30")
        def _mk30(name, nfo_body="", xml_body=""):
            d = os.path.join(_d30, name); os.makedirs(d, exist_ok=True)
            io.open(os.path.join(d, name + ".nfo"), "w", encoding="utf-8").write(f"<movie>\n  <title>{name}</title>\n{nfo_body}</movie>\n")
            io.open(os.path.join(d, "movie.xml"), "w", encoding="utf-8").write(f"<Item>\n  <LocalTitle>{name}</LocalTitle>\n{xml_body}</Item>\n")
            return mc.scan_one_subfolder(d, name, use_ffprobe=False)
        def _e30(r, matches=(), err=None):
            return {"movie_name": r["movie_name"] or r["subfolder"], "year": "", "matches": list(matches), "search_error": err}
        _r30a = _mk30("NoIds One")
        _r30n = _r30a["movie_name"] or "NoIds One"
        _bk30 = lambda: [n for n in os.listdir(_BK) if "NoIds_One" in n]
        _bk30a = len(_bk30())
        _boxes.clear()
        _sd30 = on_ui(lambda: mc._SearchSourcesResultDialog(app, [_e30(_r30a)], [_r30a]))
        check("B30: a movie TMDB found nothing for gets 'Write empty ID tags' (no footer button for one movie)", _r30n in _sd30._empty_btns and _sd30._empty_all_btn is None, list(_sd30._empty_btns))
        on_ui(lambda: _sd30._empty_btns[_r30n].invoke())
        wait_for(lambda: any(b[1] and b[1][0] == "Write empty ID tags" for b in _boxes), 10); time.sleep(0.3)
        _n30 = io.open(_r30a["nfo_path"], encoding="utf-8").read(); _x30 = io.open(_r30a["xml_path"], encoding="utf-8").read()
        check("B30: …it writes the empty TMDB and IMDb tags into NFO and XML, both files stay valid",
              all(t in _n30 for t in ("<tmdbid></tmdbid>", "<imdbid></imdbid>", '<id moviedb="tmdb"></id>'))
              and all(t in _x30 for t in ("<TMDB></TMDB>", "<IMDB></IMDB>")) and mc._parse_root(_r30a["nfo_path"]) is not None and mc._parse_root(_r30a["xml_path"]) is not None, (_n30, _x30))
        check("B30: …with a backup first", len(_bk30()) > _bk30a, _bk30())
        _rr30 = mc.scan_one_subfolder(os.path.dirname(_r30a["nfo_path"]), "NoIds One", use_ffprobe=False)
        check("B30: …and the row shows ○ 'Missing TMDB ID (empty tags ready to fill)'", _rr30["source_tmdb_status"] == mc.STATUS_MISSING and _rr30["source_tmdb_empty"] is True)
        check("B30: the button changes to '✓ Empty tags written'", "Empty tags written" in on_ui(lambda: _sd30._empty_btns[_r30n].cget("text")))
        on_ui(_sd30.destroy)
        _sd30e = on_ui(lambda: mc._SearchSourcesResultDialog(app, [_e30(_r30a, err="TMDB is not reachable")], [_r30a]))
        check("B30: no button when TMDB did not answer (a failed search is not 'not found')", not _sd30e._empty_btns)
        on_ui(_sd30e.destroy)
        _r30b = _mk30("NoIds Four"); _r30c = _mk30("Has Imdb Two", "  <imdbid>tt0111161</imdbid>\n", "  <IMDB>tt0111161</IMDB>\n"); _r30d = _mk30("Found Three")
        _b30d = (open(_r30d["nfo_path"], "rb").read(), open(_r30d["xml_path"], "rb").read())
        _match30 = [{"tmdb_id": "603", "imdb_id": "tt0133093", "title": "The Matrix", "year": "1999", "popularity": 1.0}]
        _boxes.clear()
        _sd30b = on_ui(lambda: mc._SearchSourcesResultDialog(app, [_e30(_r30b), _e30(_r30c), _e30(_r30d, _match30)], [_r30b, _r30c, _r30d]))
        check("B30: Search Sources — All Movies offers one footer button for the 2 movies not found", _sd30b._empty_all_btn is not None and "for the 2 movies not found" in on_ui(lambda: _sd30b._empty_all_btn.cget("text")))
        on_ui(_sd30b._empty_all_btn.invoke)
        wait_for(lambda: any(b[1] and b[1][0] == "Write empty ID tags" for b in _boxes), 10); time.sleep(0.3)
        _nc30 = io.open(_r30c["nfo_path"], encoding="utf-8").read()
        check("B30: the batch writes only the not-found movies; an existing IMDb value is never blanked",
              "<tmdbid></tmdbid>" in io.open(_r30b["nfo_path"], encoding="utf-8").read()
              and "<imdbid>tt0111161</imdbid>" in _nc30 and _nc30.count("<imdbid") == 1 and "<tmdbid></tmdbid>" in _nc30
              and (open(_r30d["nfo_path"], "rb").read(), open(_r30d["xml_path"], "rb").read()) == _b30d, _nc30)
        on_ui(_sd30b.destroy)
        _boxes.clear()

        # ── v0.19.2 B33: Auto Repair escapes the '&' (backup first) ───────────  ### NEW v0.19.2 B33 ###
        _sum33 = []
        _orig_trd33 = mc.TextReportDialog
        class _Rec33:
            def __init__(self, parent, title, text, stem="x"): _sum33.append((title, text))
        mc.TextReportDialog = _Rec33
        _bk33a = [n for n in os.listdir(_BK) if "Amp_Movie" in n]
        try:
            app._auto_repair_worker([_r33], {"tmdb_key": "", "omdb_key": "", "lang": "en-US", "rating_pref": "votes", "multi": False, "fetch": _fake_tmdb5}, None)
            wait_for(lambda: bool(_sum33), 10)
        finally:
            mc.TextReportDialog = _orig_trd33
        _t33 = io.open(os.path.join(_d33, "Amp Movie.nfo"), encoding="utf-8").read()
        import xml.etree.ElementTree as _ET33
        try:
            _ET33.fromstring(_t33); _strict33 = True
        except Exception:
            _strict33 = False
        check("B33: Auto Repair writes '&amp;', keeps the existing '&amp;', and the NFO now parses strictly",
              "Fast &amp; Furious, Tom &amp; Jerry" in _t33 and _strict33 and "unescaped '&' escaped" in (_sum33[0][1] if _sum33 else ""), (_t33, _sum33[:1]))
        _bk33b = [n for n in os.listdir(_BK) if "Amp_Movie" in n]
        check("B33: …after a backup of the NFO", len(_bk33b) > len(_bk33a) and any(os.path.isfile(os.path.join(_BK, n, "Amp Movie.nfo")) for n in _bk33b), _bk33b)
        _boxes.clear()

        # ── v0.19.2 B34: Delete extrafanart Subfolders — label, warning, Cancel default ──  ### NEW v0.19.2 B34 ###
        _w34 = mc.extrafanart_warning_text(2, 5)
        check("B34: the warning says Emby and Jellyfin USE extrafanart, Kodi and Plex do NOT, with the counts",
              "Emby and Jellyfin USE them" in _w34 and "Kodi and Plex do NOT read them" in _w34 and "2 folders, 5 images" in _w34)
        _d34 = os.path.join(_TMP, "b34")
        def _mk34(name, n):
            d = os.path.join(_d34, name); os.makedirs(os.path.join(d, "extrafanart", "sub"), exist_ok=True)
            io.open(os.path.join(d, name + ".nfo"), "w", encoding="utf-8").write(f"<movie>\n  <title>{name}</title>\n</movie>\n")
            for i in range(n):
                _jpeg(os.path.join(d, "extrafanart", f"fanart{i}.jpg"), 1280, 720)
            _jpeg(os.path.join(d, "extrafanart", "sub", "deep.jpg"), 1280, 720)
            return mc.scan_one_subfolder(d, name, use_ffprobe=False)
        _r34 = [_mk34("Extra One", 2), _mk34("Extra Two", 1)]
        _cnt34a = mc.count_backdrops(_r34[0]["subfolder_path"])[0]
        _ef34 = [os.path.join(r["subfolder_path"], "extrafanart") for r in _r34]
        _keep34 = app._results
        app._results = _r34
        try:
            for _how34 in ("<Escape>", "<Return>"):
                app._ef_preview = None
                app.after(0, app._delete_extrafanart_all)
                wait_for(lambda: getattr(app, "_ef_preview", None) is not None and on_ui(app._ef_preview.winfo_exists), 10)
                if _how34 == "<Escape>":
                    check("B34: the confirmation shows the Emby/Jellyfin text; Cancel is the default button",
                          "Emby and Jellyfin USE them" in app._ef_warning and on_ui(lambda: str(app._ef_cancel_btn.cget("default"))) == "active"
                          and on_ui(lambda: app._ef_delete_btn.cget("text")).strip() == "Delete")
                on_ui(lambda h=_how34: _fire(app._ef_preview, h))
                wait_for(lambda: not on_ui(app._ef_preview.winfo_exists), 5); time.sleep(0.3)
                if on_ui(app._ef_preview.winfo_exists):              ### v0.19.4 B98 — test cleanup: a synthetic key that did not
                    print(f"   note: B34 {_how34} did not reach the confirmation — closed by the test")   # arrive left it open (it would get the grab back)
                    on_ui(app._ef_preview.destroy)
                check(f"B34: {_how34[1:-1]} = Cancel → nothing deleted", all(os.path.isdir(p) for p in _ef34))
            # B40: a failed backup keeps the folder
            mc._BACKUP_ROOT = _BAD_ROOT40
            try:
                _dl40, _er40 = app._extrafanart_delete_worker([("Extra One", _ef34[0])], None)
            finally:
                mc._BACKUP_ROOT = _orig_root40
            check("B40: extrafanart delete with a failing backup keeps the folder and says so", _dl40 == 0 and os.path.isdir(_ef34[0]) and mc.BACKUP_FAILED_TEXT in " ".join(_er40), _er40)
            _boxes.clear()
            app._ef_preview = None
            app.after(0, app._delete_extrafanart_all)
            wait_for(lambda: getattr(app, "_ef_preview", None) is not None and on_ui(app._ef_preview.winfo_exists), 10)
            on_ui(app._ef_delete_btn.invoke)
            wait_for(lambda: any(b[1] and b[1][0] == "Delete Complete" for b in _boxes), 15); time.sleep(0.3)
            _bk34 = [n for n in os.listdir(_BK) if "Extra_One" in n or "Extra_Two" in n]
            _man34 = [json.load(open(os.path.join(_BK, n, "manifest.json"), encoding="utf-8")) for n in _bk34 if os.path.isfile(os.path.join(_BK, n, "manifest.json"))]
            check("B34: Delete removes both folders (sub-folders too) after a backup labelled 'Delete extrafanart'",
                  not any(os.path.isdir(p) for p in _ef34) and len(_bk34) >= 2
                  and any(m.get("action") == "Delete extrafanart" for m in _man34)
                  and sum(len(m.get("files", [])) for m in _man34) >= 5, (_bk34, [m.get("action") for m in _man34]))
            _cnt34b = mc.count_backdrops(_r34[0]["subfolder_path"])[0]
            _settle(15)
            check("B34: the backdrop count drops after the delete, and the refreshed row shows it", _cnt34a == 2 and _cnt34b == 0
                  and [r["backdrop_count"] for r in app._results if r["subfolder"] == "Extra One"] == [0],
                  (_cnt34a, _cnt34b, _r34[0]["backdrop_count"], os.listdir(_r34[0]["subfolder_path"])))
            _settle(15)
        finally:
            app._results = _keep34
        _labels34 = on_ui(lambda: [app._tools_menu.entrycget(i, "label") for i in range(app._tools_menu.index("end") + 1)
                                   if app._tools_menu.type(i) == "command"])
        check("B34: Tools menu entry 'Delete extrafanart Subfolders — All Movies…', no 'legacy' anywhere",
              mc.EXTRAFANART_MENU_LABEL in _labels34 and not any("legacy" in l.lower() for l in _labels34), _labels34)
        _boxes.clear()

        # ── v0.19.2 B40: batch tools skip a movie whose backup failed ─────────  ### NEW v0.19.2 B40 ###
        _r40 = mc.scan_one_subfolder(_mv40, "B40 Movie", use_ffprobe=False)
        _sum40 = []
        _orig_trd40 = mc.TextReportDialog
        class _Rec40:
            def __init__(self, parent, title, text, stem="x"): _sum40.append((title, text))
        mc.TextReportDialog = _Rec40
        mc._BACKUP_ROOT = _BAD_ROOT40
        try:
            app._normalize_genres_worker([_r40], None); time.sleep(0.5)
            app._hardsubs_worker([_r40], ["ITA"], None); time.sleep(0.5)
            on_ui(lambda: app._copy_poster_to_folder([_r40], confirm=False))
            wait_for(lambda: any(b[1] and b[1][0] == "Copy poster.jpg → folder.jpg" for b in _boxes) or any("folder.jpg" in str(b) for b in _boxes), 10); time.sleep(0.5)
            app._auto_repair_worker([_r40], {"tmdb_key": "", "omdb_key": "", "lang": "en-US", "rating_pref": "votes", "multi": False, "fetch": _fake_tmdb5}, None)
            wait_for(lambda: bool(_sum40), 10); time.sleep(0.3)
        finally:
            mc._BACKUP_ROOT = _orig_root40
            mc.TextReportDialog = _orig_trd40
        _msgs40 = " ".join(str(b) for b in _boxes) + " ".join(t for _t, t in _sum40)
        check("B40: Normalize Genres, Hard-coded subtitles, Copy poster → folder and Auto Repair change nothing when the backup fails", _unchanged40(), [os.path.basename(p) for p, b in _snap40.items() if open(p, "rb").read() != b])
        check("B40: … and each reports 'backup failed — not changed'", _msgs40.count("backup failed — not changed") >= 4, (_boxes, _sum40))
        _boxes.clear()

        # ── v0.19.4 B77: Auto Repair — a file error fails one movie, a network error stops the run ──  ### NEW v0.19.4 B77 ###
        import urllib.error as _ue77
        check("B77: network errors are told apart from file errors",
              mc.is_network_error(_ue77.URLError("getaddrinfo failed")) and mc.is_network_error(TimeoutError("timed out"))
              and mc.is_network_error(ConnectionResetError(10054, "reset")) and not mc.is_network_error(PermissionError(13, "Permission denied"))
              and not mc.is_network_error(OSError(22, "Invalid argument")) and not mc.is_network_error(_ue77.HTTPError("u", 404, "nf", {}, None)))
        _rows77 = [{"movie_name": n, "subfolder": n, "nfo_exists": False, "xml_exists": False, "health_reasons": ["x"]} for n in ("Locked One", "Next One")]
        _calls77, _sum77 = [], []
        class _Rec77:
            def __init__(self, parent, title, text, stem="x"): _sum77.append(text)
        _o77 = (mc._auto_repair_plan, mc.TextReportDialog)
        mc._auto_repair_plan = lambda d, s, r: [("struct_fix", "Structure"), ("genres", "Genres")]
        mc.TextReportDialog = _Rec77
        def _raise77(kind):
            def _f(ctx):
                _calls77.append((ctx["name"], kind))
                if ctx["name"] == "Locked One":
                    raise (PermissionError(13, "Permission denied", "Locked One.nfo") if kind == "file"
                           else _ue77.URLError("getaddrinfo failed"))
                return "skipped", "test"
            return _f
        try:
            for _kind77 in ("file", "net"):
                _calls77.clear(); _sum77.clear(); _boxes.clear()
                app._ar_struct_fix = _raise77(_kind77); app._ar_genres = _raise77(_kind77)
                app._auto_repair_worker(list(_rows77), {"tmdb_key": "", "omdb_key": "", "lang": "en-US", "rating_pref": "votes", "multi": True}, None)
                wait_for(lambda: bool(_sum77), 10); time.sleep(0.3)
                _txt77 = _sum77[0] if _sum77 else ""
                if _kind77 == "file":
                    check("B77: a locked NFO fails that movie with the real reason; the run goes on to the next movie (no 'stopped' box)",
                          ("Locked One", "file") in _calls77 and ("Next One", "file") in _calls77
                          and _calls77.count(("Locked One", "file")) == 1 and "Permission denied" in _txt77
                          and not any(b[0] == "error" for b in _boxes), (_calls77, _txt77[:600], _boxes))
                else:
                    check("B77: a network error still stops the run (the next movie is not touched, 'stopped' box)",
                          ("Locked One", "net") in _calls77 and not any(c[0] == "Next One" for c in _calls77)
                          and any(b[0] == "error" and "stopped" in str(b[1][0]) for b in _boxes), (_calls77, _boxes))
        finally:
            mc._auto_repair_plan, mc.TextReportDialog = _o77
            for _a77 in ("_ar_struct_fix", "_ar_genres"):
                if _a77 in app.__dict__:
                    delattr(app, _a77)
        _boxes.clear()

        # ── v0.19.4 B82: ratings inside a batch → one backup folder per run ──  ### NEW v0.19.4 B82 ###
        def _mk82(name, n):
            d = os.path.join(_TMP, "b82", name); os.makedirs(d, exist_ok=True)
            io.open(os.path.join(d, name + ".nfo"), "w", encoding="utf-8", newline="\n").write(
                f"<movie>\n  <title>{name}</title>\n  <year>2001</year>\n  <rating>5.0</rating>\n  <votes>10</votes>\n"
                f"  <uniqueid type=\"imdb\">tt008200{n}</uniqueid>\n  <uniqueid type=\"tmdb\">8200{n}</uniqueid>\n</movie>\n")
            return mc.scan_one_subfolder(d, name, use_ffprobe=False)
        _r82 = [_mk82("Batch One", 1), _mk82("Batch Two", 2)]
        _bk82 = lambda: {n for n in os.listdir(mc._BACKUP_ROOT) if n.startswith("backup_")}
        _o82 = (mc._fetch_tmdb_rating, mc._fetch_omdb_rating, mc._auto_repair_plan, mc.TextReportDialog)
        mc._fetch_tmdb_rating = lambda tid, key: ("8.1", "5000")
        mc._fetch_omdb_rating = lambda iid, key: (None, None)
        app._ask_ratings_dialog = lambda *a, **k: {"choice": "tmdb", "apply_all": True, "use_more_votes": False,
                                                    "manual_r": None, "manual_v": None, "apply_fallback": False}
        _sum82 = []
        class _Rec82:
            def __init__(self, parent, title, text, stem="x"): _sum82.append(text)
        _boxes.clear()
        try:
            _b0 = _bk82()
            app._sync_ratings_worker(_r82, "k", "k", None)
            wait_for(lambda: any(b[1] and b[1][0] == "Ratings Sync Complete" for b in _boxes), 10)
            _settle()        # the run's row refresh settles before the next checks
            _new82 = sorted(_bk82() - _b0)
            _m82 = sc.read_manifest(os.path.join(mc._BACKUP_ROOT, _new82[0])) if len(_new82) == 1 else None
            check("B82: Sync Ratings on 2 movies → ONE backup folder (one Backup History line) with both NFOs, ratings written",
                  len(_new82) == 1 and _m82 and len(_m82["files"]) == 2 and _m82["action"] == "Ratings Sync"
                  and all("<rating>8.1</rating>" in io.open(r["nfo_path"], encoding="utf-8").read() for r in _r82), (_new82, _m82, _boxes))
            _r82 = [mc.scan_one_subfolder(r["subfolder_path"], r["subfolder"], use_ffprobe=False) for r in _r82]
            mc._fetch_tmdb_rating = lambda tid, key: ("8.8", "7777")
            mc._auto_repair_plan = lambda d, s, r: [("ratings", "Ratings")]
            mc.TextReportDialog = _Rec82
            _b1 = _bk82()
            app._auto_repair_worker(list(_r82), {"tmdb_key": "k", "omdb_key": "", "lang": "en-US", "rating_pref": "tmdb", "multi": True}, None)
            wait_for(lambda: bool(_sum82), 10)
            _settle()
            _new82b = sorted(_bk82() - _b1)
            _m82b = sc.read_manifest(os.path.join(mc._BACKUP_ROOT, _new82b[0])) if len(_new82b) == 1 else None
            check("B82: Auto Repair ratings on 2 movies → ONE backup folder (no second backup per movie)",
                  len(_new82b) == 1 and _m82b and len(_m82b["files"]) == 2 and _m82b["action"] == "Auto Repair"
                  and all("<rating>8.8</rating>" in io.open(r["nfo_path"], encoding="utf-8").read() for r in _r82), (_new82b, _m82b, _sum82[:1]))
        finally:
            mc._fetch_tmdb_rating, mc._fetch_omdb_rating, mc._auto_repair_plan, mc.TextReportDialog = _o82
            if "_ask_ratings_dialog" in app.__dict__:
                del app._ask_ratings_dialog
        _boxes.clear()

        # ── v0.19.4 B83: Auto Repair's language fix escapes '&' once ──  ### NEW v0.19.4 B83 ###
        _d83l = os.path.join(_TMP, "b83l"); os.makedirs(_d83l, exist_ok=True)
        _n83l = os.path.join(_d83l, "m.nfo"); _x83l = os.path.join(_d83l, "m.xml")
        io.open(_n83l, "w", encoding="utf-8", newline="\n").write("<movie>\n  <language>Serbo &amp; Croatian</language>\n</movie>\n")
        io.open(_x83l, "w", encoding="utf-8", newline="\n").write("<Title>\n  <Language></Language>\n</Title>\n")

        # ── v0.19.4 B96: a failed automatic update check is tried again next start ──  ### NEW v0.19.4 B96 ###
        _luc96 = mc.SETTINGS.get("last_update_check", "")
        on_ui(lambda: app._auto_update_done({"status": "error", "error": "offline (test)"}, "2099-01-01"))
        _after_err96 = mc.SETTINGS.get("last_update_check", "")
        on_ui(lambda: app._auto_update_done({"status": "latest"}, "2099-01-02"))
        _after_ok96 = mc.SETTINGS.get("last_update_check", "")
        mc.SETTINGS["last_update_check"] = _luc96; mc._save_settings(mc.SETTINGS)
        check("B96: a failed automatic update check is not counted as 'checked today'; a good one is",
              _after_err96 == _luc96 and _after_ok96 == "2099-01-02", (_luc96, _after_err96, _after_ok96))

        # ── v0.19.2 B43: one Help window, Esc closes it, the grab goes back ──  ### NEW v0.19.2 B43 ###
        def _helps43():
            return [w for w in app.winfo_children() if isinstance(w, mc.HelpDialog) and w.winfo_exists()]
        _h43a = on_ui(lambda: mc.open_help(app, 2)); _h43b = on_ui(lambda: mc.open_help(app, 5))
        _sel43 = on_ui(lambda: _h43b._nb.index(_h43b._nb.select()))
        check("B43: F1 / Help twice → one Help window, switched to the new tab", _h43a is _h43b and len(on_ui(_helps43)) == 1 and _sel43 == 5, (len(on_ui(_helps43)), _sel43))
        on_ui(lambda: _fire(_h43b, "<Escape>"))
        check("B43: Esc closes the Help window", not on_ui(_helps43))
        _sd43 = on_ui(lambda: mc.SettingsDialog(app, tab=0))
        _g43a = on_ui(lambda: str(app.grab_current()))
        _h43c = on_ui(lambda: mc.open_help(app, 1))
        _g43b = on_ui(lambda: str(app.grab_current()))
        on_ui(_h43c._close)
        _g43c = on_ui(lambda: str(app.grab_current()))
        check("B43: Help opened over Settings takes the grab and gives it back to Settings when it closes",
              _g43a == str(_sd43) and _g43b == str(_h43c) and _g43c == str(_sd43), (_g43a, _g43b, _g43c))
        on_ui(_sd43.destroy)

        # ── v0.19.2 B45: Esc closes every view-only dialog ─────────────────────  ### NEW v0.19.2 B45 ###
        _row45 = dict({r["subfolder"]: r for r in app._results}["Perfect Movie"])
        _orl45 = mc._tmdb_rate_limited_fetch
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {}
        _mk45 = [
            ("ImprovementsDialog",         lambda: mc.ImprovementsDialog(app, "report", 1)),
            ("HealthReportDialog",         lambda: mc.HealthReportDialog(app, "report", 1)),
            ("SubtitleDialog",             lambda: mc.SubtitleDialog(app, "Perfect Movie", _row45)),
            ("ErrorDialog",                lambda: mc.ErrorDialog(app, "NFO errors", _row45["nfo_path"], [{"line": 1, "col": 0, "message": "x"}])),
            ("CopyMovieNameDialog",        lambda: mc.CopyMovieNameDialog(app, ["Perfect Movie"])),
            ("_SearchSourcesResultDialog", lambda: mc._SearchSourcesResultDialog(app, [{"movie_name": "Perfect Movie", "year": "", "matches": []}], [_row45])),
            ("_SourceDisagreementDialog",  lambda: mc._SourceDisagreementDialog(app, "Perfect Movie", "IMDB", ["tt0000001", "tt0000002"])),
        ]
        _left45 = []
        _nfo45 = open(_row45["nfo_path"], "rb").read()
        try:
            for _n45, _f45 in _mk45:
                _d45 = on_ui(_f45)
                on_ui(lambda d=_d45: _fire(d, "<Escape>"))
                time.sleep(0.05)
                if on_ui(_d45.winfo_exists):
                    _left45.append(_n45); on_ui(_d45.destroy)
            _pr45 = on_ui(lambda: mc._PreviewRunDialog(app, "Auto Repair — preview", "plan"))
            on_ui(lambda: _fire(_pr45, "<Escape>"))
            if on_ui(_pr45.winfo_exists):
                _left45.append("_PreviewRunDialog"); on_ui(_pr45.destroy)
        finally:
            mc._tmdb_rate_limited_fetch = _orl45
        check("B45: Esc closes Improvements, Health report, Subtitles, Error, Copy name, Search Sources results, ID conflict and the Run preview",
              not _left45, _left45)
        check("B45: …the preview closed with Esc is not a Run, and the ID conflict closed with Esc is a Skip; nothing written",
              _pr45.run is False and open(_row45["nfo_path"], "rb").read() == _nfo45)

        # ── v0.19.2 B46: error dialog — "Open in Editor" + "Open Folder" ──────  ### NEW v0.19.2 B46 ###
        _calls46 = []
        _o46 = (mc.open_in_editor, mc.os_open)
        mc.open_in_editor = lambda p: _calls46.append(("editor", p))
        mc.os_open = lambda p: _calls46.append(("open", p))
        try:
            _ed46 = on_ui(lambda: mc.ErrorDialog(app, "NFO errors", _row45["nfo_path"], [{"line": 1, "col": 0, "message": "x"}]))
            _txt46 = on_ui(lambda: (_ed46._editor_btn.cget("text").strip(), _ed46._folder_btn.cget("text").strip()))
            on_ui(_ed46._editor_btn.invoke); on_ui(_ed46._folder_btn.invoke)
            on_ui(_ed46.destroy)
        finally:
            mc.open_in_editor, mc.os_open = _o46
        # ── v0.19.2 B57: right-click menu — groups, Fix issues, Repeat, Shift+F10 ──  ### NEW v0.19.2 B57 ###
        _old_actions57 = ["📂  Open Folder", "🖼  Open ", "🎞  Extract Backdrop(s)", "🎬  Play Video", "💬  Subtitles…",
                          "📝  Open .nfo", "[!] NFO errors", "📝  Open movie.xml", "[!] XML errors", "🌐  Open on IMDb",
                          "🌐  Open on TMDB", "🌐  Open on Fanart.tv", "🌐  Open on OpenSubtitles.org", "📋  Copy Movie Name",
                          "🎬  Open in Scraper", "🔍  Run Improvements Check", "🏥  Health Status Report", "⭐  Sync Ratings",
                          "🔗  Normalize Sources", "🔎  Search Sources", "✅  Verify IMDb/TMDB IDs", "🛠  Auto Repair",
                          "🎬  Normalize Genres", "🔤  Hard-coded subtitles…", "🖼  Fetch Poster/Folder", "🎨  Fetch Fanart",
                          "🖼  Fetch Backdrops", "🔄  Replace All Backdrops", "🖼  Copy poster.jpg → folder.jpg",
                          "➕  Add Custom Genre(s) to Settings", "🔄  Update (no FFprobe)", "🔬  Update (with FFprobe)",
                          "✖  Remove from list"]   # v0.19.4 I17: "🔁  Refresh Icons" is in Tools ▾ only (intended)
        _iid57 = on_ui(lambda: app.tree.get_children()[0])
        _d57 = dict(app._item_map[_iid57], poster_exists=False,
                    health_reasons=["Missing poster", "Missing rating"], nfo_errors=[{"line": 2, "col": 0, "message": "x"}])
        _d57b = dict(_d57, subfolder="Other57", movie_name="Other57", subfolder_path=_d57["subfolder_path"] + "_b")
        def _menu57(sel):
            app._build_ctx_menu(_iid57, sel[0], sel)
            return _flat57(app._ctx)
        _one57 = on_ui(lambda: _menu57([_d57]))
        _many57 = on_ui(lambda: _menu57([_d57, _d57b]))
        _lab1 = [l for _dp, l, _s, _m, _i in _one57]; _labm = [l for _dp, l, _s, _m, _i in _many57]
        _miss57 = [a for a in _old_actions57 if not any(l.startswith(a) for l in _lab1)]
        _missm = [a for a in _old_actions57 if not any(l.startswith(a) for l in _labm)]
        check("B57: every v0.19.1 action is still in the menu (one movie and several)", not _miss57 and not _missm, (_miss57, _missm))
        _top57 = [l for dp, l, _s, _m, _i in _one57 if dp == 0]
        check("B57: first level ≤ 15 lines: title, Fix issues, Open Folder / Play / Edit NFO, 7 groups, Remove",
              len(_top57) <= 15 and _top57[0].startswith("▸ ") and "issues" in _top57[0]
              and all(any(t.startswith(g) for t in _top57) for g in ("⚠  Fix issues", "🖼  Artwork", "📝  Metadata", "🔗  IDs & Sources",
                                                                     "🎞  Video & Subtitles", "🌐  Open online", "🩺  Check & Repair", "🔄  Update")), _top57)
        check("B57: no '(N movies)' suffix with several movies; title says 'N movies selected'",
              not any(" movies)" in l for l in _labm if not l.startswith("➕")) and _labm[0].startswith("▸ 2 movies selected"), _labm[:6])
        check("B57: single-movie actions stay in place, greyed '(one movie only)' with several",
              dict((l, s) for _dp, l, s, _m, _i in _many57).get("📂  Open Folder (one movie only)") == "disabled")
        _fix57 = [l for dp, l, _s, _m, _i in _one57 if dp == 1 and "→" in l]
        check("B57: 'Fix issues' lists the row's problems (poster, NFO errors, ratings)",
              any(l.startswith("Poster / folder image missing") for l in _fix57) and any(l.startswith("NFO errors") for l in _fix57)
              and any(l.startswith("Rating / votes") for l in _fix57), _fix57)
        _called57 = []
        _ofp57 = app._fetch_poster_folder
        app._fetch_poster_folder = lambda rows: _called57.append(("poster", [r["subfolder"] for r in rows]))
        try:
            def _invoke57(prefix, sel):
                ents = _menu57(sel)
                dp, l, s, mn, i = next(e for e in ents if e[1].startswith(prefix))
                mn.invoke(i)
                return l
            _l57 = on_ui(lambda: _invoke57("Poster / folder image missing", [_d57]))
            _lm57 = on_ui(lambda: _invoke57("Poster / folder image missing", [_d57, _d57b]))
            check("B57: a Fix issues entry runs its action on just those movies; several → '— 2 movies'",
                  _called57 == [("poster", [_d57["subfolder"]]), ("poster", [_d57["subfolder"], "Other57"])] and _lm57.endswith("— 2 movies"), (_called57, _lm57))
            _rep57 = on_ui(lambda: [l for dp, l, _s, _m, _i in _menu57([_d57]) if dp == 0][2])   # [1] = B64's "Not a duplicate" line (v0.19.3, intended)
            check("B57: 'Repeat: <last action>' follows under the title (after B64's 'Not a duplicate' line)", _rep57.startswith("↻  Repeat: Poster / folder image missing"), _rep57)
            on_ui(lambda: _invoke57("↻  Repeat:", [_d57]))
            check("B57: Repeat runs the last action again", len(_called57) == 3, _called57)
            check("B101: Repeat runs on the CURRENT selection (1 movie now, the action was last run on 2)",   ### NEW v0.19.4 B101 ###
                  _called57[-1] == ("poster", [_d57["subfolder"]]), _called57)
            check("B101: the action key drops the counts ('— 2 movies', '(3)', '— 1 of 2 need it')",
                  mc.ctx_action_key("Missing NFO — 2 movies") == "Missing NFO" and mc.ctx_action_key("[!] NFO errors (3)") == "[!] NFO errors"
                  and mc.ctx_action_key("🖼  Copy poster.jpg → folder.jpg — 1 of 2 need it") == "🖼  Copy poster.jpg → folder.jpg"
                  and mc.ctx_action_key("➕  Add Custom Genre(s) to Settings (4)") == "➕  Add Custom Genre(s) to Settings")
            mc.SETTINGS["ctx_repeat_last"] = False
            _norep57 = on_ui(lambda: [l for dp, l, _s, _m, _i in _menu57([_d57]) if dp == 0])
            mc.SETTINGS["ctx_repeat_last"] = True
            check("B57: setting OFF → no Repeat line", not any(l.startswith("↻") for l in _norep57), _norep57[:3])
        finally:
            app._fetch_poster_folder = _ofp57
        _pop57 = []
        app._ctx.tk_popup = lambda x, y: _pop57.append((x, y))
        try:
            on_ui(lambda: (app.tree.selection_set(_iid57), app.tree.focus(_iid57), app._ctx_from_keyboard()))
        finally:
            del app._ctx.tk_popup
        check("B57: Shift+F10 / Menu key open the menu at the selected row", len(_pop57) == 1 and on_ui(lambda: bool(app.bind("<Shift-F10>"))), _pop57)

        check("B46: the error dialog has 'Open in Editor' and 'Open Folder', each with its own action",
              _txt46 == ("Open in Editor", "Open Folder")
              and _calls46 == [("editor", _row45["nfo_path"]), ("open", os.path.dirname(_row45["nfo_path"]))], (_txt46, _calls46))

        # ── v0.19.2 B53: folders that are not movies, in a real scan ──────────   ### NEW v0.19.2 B53 ###
        LIB53 = os.path.join(_TMP, "Lib53"); os.makedirs(LIB53, exist_ok=True)
        def _m53(root, rel, files):
            d = os.path.join(root, rel); os.makedirs(d, exist_ok=True)
            for f in files:
                p = os.path.join(d, *f.split("/")); os.makedirs(os.path.dirname(p), exist_ok=True)
                if p.lower().endswith(".nfo") and not p.lower().endswith("tvshow.nfo"):
                    _nfo(p, os.path.basename(d), imdb="tt7753101", tmdb="753101")
                else:
                    open(p, "wb").write(b"\0" * 64)
            return d
        _m53(LIB53, "Real Movie (2001)", ["Real Movie (2001).mkv", "Real Movie (2001).nfo"])
        _bs53 = _m53(LIB53, "Becomes Series", ["Becomes Series.mkv"])
        _m53(LIB53, "Série Amélie", ["tvshow.nfo", "Season 1/e01.mkv"])
        _m53(LIB53, "Collection", ["Inner A (2001)/Inner A (2001).mkv", "Inner B (2002)/Inner B (2002).mkv"])
        _nh53 = _m53(LIB53, "Nothing Here", ["readme.txt"])
        _m53(LIB53, "$RECYCLE.BIN", ["junk.mkv"])
        _m53(LIB53, "Meta Only (2003)", ["Meta Only (2003).nfo"])
        open(os.path.join(LIB53, "Loose Root Movie.mkv"), "wb").write(b"\0" * 64)
        _save53 = (list(app._results), dict(app._ignored_data or {}))
        _in53 = lambda r: mc._pkey(r.get("library_root", "")) == mc._pkey(LIB53)
        mc.IGNORED_REPORT_AUTO = True
        try:
            on_ui(lambda: app._start_scan([LIB53], use_ff=False))
            wait_for(lambda: not app._scanning, 60)
            wait_for(lambda: getattr(app, "_ignored_dlg", None) is not None, 5)
        finally:
            mc.IGNORED_REPORT_AUTO = False
        _rows53 = sorted(r["subfolder"] for r in app._results if _in53(r))
        _ign53 = {os.path.basename(i["path"]): i["kind"] for i in app._ignored_data.get("items", []) if _in53(i)}
        check("B53 scan: rows only for the movies (one with NFO but no video kept)", _rows53 == ["Becomes Series", "Meta Only (2003)", "Real Movie (2001)"], _rows53)
        check("B53 scan: the other folders are listed with their kind",
              _ign53 == {"Série Amélie": "series", "Collection": "container", "Nothing Here": "no_media", "$RECYCLE.BIN": "system"}, _ign53)
        check("B53 scan: videos lying directly in the library are listed", app._ignored_data.get("root_videos", {}).get(mc._norm_lib(LIB53)) == ["Loose Root Movie.mkv"], app._ignored_data.get("root_videos"))
        check("B53 scan: last_ignored.json written", len([i for i in sc.load_ignored().get("items", []) if _in53(i)]) == 4)
        _nlink53 = (sum(1 for i in app._ignored_data.get("items", []) if i["kind"] in mc._fc.IGNORED_KINDS)
                    + sum(len(v) for v in app._ignored_data.get("root_videos", {}).values()))
        check("B53 scan: status bar link 'n folders not added — View' (all libraries, root videos included)",
              _nlink53 >= 5 and on_ui(lambda: app._sb_ignored.cget("text")) == f"{_nlink53} folders not added — View", on_ui(lambda: app._sb_ignored.cget("text")))
        check("B53: Tools menu has 'Ignored Folders of the Last Scan…'", any(t[1] == mc.IGNORED_MENU_LABEL for t in on_ui(lambda: _flat57(app._tools_menu))))
        _dlg53 = getattr(app, "_ignored_dlg", None)
        check("B53: the Ignored folders window opened by itself after the scan", _dlg53 is not None and on_ui(_dlg53.winfo_exists))
        if _dlg53 is not None:
            _sum53 = on_ui(lambda: _dlg53._summary.cget("text"))
            check("B53 window: counts line (per kind, kept movies named separately)", _sum53.startswith("Scan finished: ")
                  and "folders were not added: 1 TV series · 1 holding other folders · " in _sum53 and "with no video, NFO or XML" in _sum53
                  and "1 system folder." in _sum53 and "with NFO/XML but no video are in the table." in _sum53, _sum53)
            _n_all53 = on_ui(lambda: len(_dlg53._tree.get_children()))
            on_ui(lambda: (_dlg53._filter.set("series"), _dlg53._fill()))
            _ser53 = on_ui(lambda: [_dlg53._tree.set(k, "folder") for k in _dlg53._tree.get_children()])
            on_ui(lambda: (_dlg53._filter.set("all"), _dlg53._fill()))
            check("B53 window: filter (All → TV series) and the root video + kept rows listed", _ser53 == ["Série Amélie"] and _n_all53 >= 6, (_ser53, _n_all53))
            _o1 = on_ui(lambda: [_dlg53._tree.set(k, "folder") for k in _dlg53._tree.get_children()])
            on_ui(lambda: _dlg53._sort_by("folder"))
            _o2 = on_ui(lambda: [_dlg53._tree.set(k, "folder") for k in _dlg53._tree.get_children()])
            check("B53 window: clicking a column heading sorts (again = reversed)", _o2 == list(reversed(_o1)) and _o1 == sorted(_o1, key=str.lower), (_o1, _o2))
            _op53 = []
            _dlg53._opener = _op53.append
            on_ui(lambda: (_dlg53._tree.selection_set(_dlg53._tree.get_children()[0]), _dlg53._open_selected()))
            check("B53 window: double-click / Enter opens the folder", len(_op53) == 1 and os.path.isdir(_op53[0]), _op53)
            _ex53 = os.path.join(_TMP, "b53_window_export.txt")
            _asf53 = mc.filedialog.asksaveasfilename
            mc.filedialog.asksaveasfilename = lambda **k: _ex53
            try:
                on_ui(_dlg53._export)
            finally:
                mc.filedialog.asksaveasfilename = _asf53
            _t53 = open(_ex53, "rb").read() if os.path.isfile(_ex53) else b""
            check("B53 window: Export to TXT (BOM, CRLF, 'Série Amélie' round-trip, groups)",
                  _t53.startswith(b"\xef\xbb\xbf") and "Série Amélie" in _t53.decode("utf-8-sig") and b"TV series (1)" in _t53
                  and b"Videos directly in the library folder" in _t53 and b"\r\n" in _t53, _t53[:300])
            on_ui(_dlg53._copy_all)
            check("B53 window: Copy all puts the report on the clipboard", "folders not added as movies" in on_ui(app.clipboard_get))
            on_ui(lambda: (_dlg53._auto_var.set(False), _dlg53._auto_changed()))
            check("B53 window: 'Show this window after a scan' saves scan_ignored_report", mc.SETTINGS.get("scan_ignored_report") is False)
            on_ui(lambda: (_dlg53._auto_var.set(True), _dlg53._auto_changed()))
            check("B53 window: Esc closes it", on_ui(lambda: bool(_dlg53.bind("<Escape>"))))
            on_ui(_dlg53.destroy)
        # Quick Scan: a movie that became a series, and a v0.19.1 cached row of a non-movie folder, disappear
        time.sleep(0.05)
        _m53(LIB53, "Becomes Series", ["tvshow.nfo", "Season 1/e01.mkv"])
        _legacy53 = mc._results_from_json([{"subfolder": "Nothing Here", "subfolder_path": _nh53, "library_root": mc._norm_lib(LIB53),
                                            "video_count": 0, "scan_mtime": mc._folder_mtime(_nh53)}])[0]
        on_ui(lambda: setattr(app, "_results", app._results + [_legacy53]))
        on_ui(lambda: app._start_quick_scan([LIB53]))
        wait_for(lambda: not app._scanning, 60)
        _rows53 = sorted(r["subfolder"] for r in app._results if _in53(r))
        _ign53 = {os.path.basename(i["path"]): i["kind"] for i in app._ignored_data.get("items", []) if _in53(i)}
        if sys.platform == "win32": check("B53 Quick Scan: the movie that became a series and the old cached non-movie row are removed",
              _rows53 == ["Meta Only (2003)", "Real Movie (2001)"] and _ign53.get("Becomes Series") == "series" and _ign53.get("Nothing Here") == "no_media"
              and _ign53.get("Collection") == "container", (_rows53, _ign53))
        _boxes.clear()
        on_ui(lambda: app._start_quick_scan([LIB53]))
        wait_for(lambda: not app._scanning, 60)
        check("B53 Quick Scan: unchanged ignored folders are not 'changes' ('up to date')", any("up to date" in str(b) for b in _boxes), _boxes)
        # no extra os.scandir for normal movie folders
        LIB53m = os.path.join(_TMP, "Lib53m"); os.makedirs(LIB53m, exist_ok=True)
        for _n in ("Plain A (2001)", "Plain B (2002)", "Plain C (2003)"):
            _m53(LIB53m, _n, [f"{_n}.mkv", f"{_n}.nfo"])
        _sd53 = os.scandir; _cnt53 = [0]
        def _count_sd(p="."):
            _cnt53[0] += 1
            return _sd53(p)
        _cls53 = mc.classify_listing
        _calls53 = []
        try:
            mc.os.scandir = _count_sd
            mc.classify_listing = lambda lst: ("movie", "", "")
            on_ui(lambda: app._start_scan([LIB53m], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            _calls53.append(_cnt53[0]); _cnt53[0] = 0
            mc.classify_listing = _cls53
            on_ui(lambda: app._start_scan([LIB53m], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            _calls53.append(_cnt53[0])
        finally:
            mc.os.scandir = _sd53; mc.classify_listing = _cls53
        check("B53: no extra os.scandir for normal movie folders (same count with and without the classifier)", _calls53[0] == _calls53[1] and _calls53[0] > 0, _calls53)
        on_ui(lambda: (setattr(app, "_results", _save53[0]), setattr(app, "_ignored_data", _save53[1]),
                       app._refresh_table(), app._update_ignored_link(), app._incremental_save(app._results)))
        sc.save_ignored(_save53[1])

        # ── v0.19.4 B84: cancel a Full Scan halfway, then Quick Scan ──  ### NEW v0.19.4 B84 ###
        LIB84 = os.path.join(_TMP, "Lib84"); os.makedirs(LIB84, exist_ok=True)
        def _m84(name):
            d = os.path.join(LIB84, name); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, name + ".mkv"), "wb").write(b"\0" * 64)
            _nfo(os.path.join(d, name + ".nfo"), name.split(" (")[0])
            return d
        for _i84 in range(6):
            _m84(f"Cancel Movie {_i84} (200{_i84})")
        _save84 = (list(app._results), dict(app._ignored_data or {}))
        _in84 = lambda r: mc._pkey(r.get("library_root", "")) == mc._pkey(LIB84)
        _ov84 = mc.validate_xml_file
        try:
            on_ui(lambda: app._start_scan([LIB84], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            _full84 = {r["subfolder"] for r in app._results if _in84(r) and r["nfo_exists"]}
            _m84("Cancel Movie New (2010)")                                   # a new folder, no previous row
            _n84 = [0]
            def _val84(*a, **k):
                _n84[0] += 1
                if _n84[0] == 2:
                    app._cancel_scan = True                                    # Cancel pressed during phase 3
                return _ov84(*a, **k)
            mc.validate_xml_file = _val84
            on_ui(lambda: app._start_scan([LIB84], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            mc.validate_xml_file = _ov84
            _can84 = [r for r in app._results if _in84(r)]
            check("B84: a cancelled Full Scan keeps the previous rows of the folders it did not finish; no half-built row carries a scan time",
                  len(_full84) == 6 and _n84[0] >= 2
                  and all(r["nfo_exists"] for r in _can84 if r["subfolder"] in _full84)
                  and not any((not r["nfo_exists"]) and r.get("scan_mtime") is not None for r in _can84),
                  [(r["subfolder"], r["nfo_exists"], r.get("scan_mtime")) for r in _can84])
            on_ui(lambda: app._start_quick_scan([LIB84])); wait_for(lambda: not app._scanning, 60)
            _q84 = [r for r in app._results if _in84(r)]
            check("B84: …then Quick Scan → all 7 movies complete, no 'Missing NFO' row left from the cancel",
                  len(_q84) == 7 and all(r["nfo_exists"] and r.get("scan_mtime") is not None for r in _q84),
                  [(r["subfolder"], r["nfo_exists"], r.get("scan_mtime")) for r in _q84])
        finally:
            mc.validate_xml_file = _ov84
            on_ui(lambda: (setattr(app, "_results", _save84[0]), setattr(app, "_ignored_data", _save84[1]),
                           app._refresh_table(), app._update_ignored_link(), app._incremental_save(app._results)))
            sc.save_ignored(_save84[1])
        _boxes.clear()

        # ── v0.19.4 B110a: a REAL Full Scan and Quick Scan read the NFO <set> ──  ### NEW v0.19.4 B110a ###
        LIBC = os.path.join(_TMP, "LibColl"); os.makedirs(LIBC, exist_ok=True)
        for _nc in ("Saga One (2001)", "Saga Two (2003)", "Alone (2005)"):
            _dc = os.path.join(LIBC, _nc); os.makedirs(_dc, exist_ok=True)
            open(os.path.join(_dc, _nc + ".mkv"), "wb").write(b"\0" * 64)
            _setc = "  <set>\n    <name>Real Saga</name>\n  </set>\n" if _nc.startswith("Saga") else ""
            open(os.path.join(_dc, _nc + ".nfo"), "w", encoding="utf-8").write(
                f"<movie>\n  <title>{_nc[:-7]}</title>\n{_setc}</movie>\n")
        _savec = (list(app._results), dict(app._ignored_data or {}))
        _inc = lambda r: mc._pkey(r.get("library_root", "")) == mc._pkey(LIBC)
        try:
            on_ui(lambda: app._start_scan([LIBC], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            _fc = {r["subfolder"]: mc.collection_name(r) for r in app._results if _inc(r)}
            on_ui(lambda: app._start_quick_scan([LIBC])); wait_for(lambda: not app._scanning, 60)
            _qc = {r["subfolder"]: mc.collection_name(r) for r in app._results if _inc(r)}
            _want_c = {"Saga One (2001)": "Real Saga", "Saga Two (2003)": "Real Saga", "Alone (2005)": ""}
            check("B110a: a real Full Scan (phase 3) and a Quick Scan keep the NFO collection", _fc == _want_c and _qc == _want_c, (_fc, _qc))
        finally:
            on_ui(lambda: (setattr(app, "_results", _savec[0]), setattr(app, "_ignored_data", _savec[1]),
                           app._refresh_table(), app._update_ignored_link(), app._incremental_save(app._results)))
            sc.save_ignored(_savec[1])
        _boxes.clear()

        # ── v0.19.4 review fix 1: a cache written by v0.19.3 (no coll_nfo) restored, then grouped ──  ### NEW v0.19.4 fix 1 ###
        LIBR = os.path.join(_TMP, "LibRestore"); os.makedirs(LIBR, exist_ok=True)
        for _nr in ("Old Saga One (2001)", "Old Saga Two (2003)", "Old Alone (2005)"):
            _dr = os.path.join(LIBR, _nr); os.makedirs(_dr, exist_ok=True)
            open(os.path.join(_dr, _nr + ".mkv"), "wb").write(b"\0" * 64)
            _setr = "  <set>\n    <name>Old Saga</name>\n  </set>\n" if "Saga" in _nr else ""
            open(os.path.join(_dr, _nr + ".nfo"), "w", encoding="utf-8").write(
                f"<movie>\n  <title>{_nr[:-7]}</title>\n{_setr}</movie>\n")
        _saver = (list(app._results), dict(app._ignored_data or {}), mc.SETTINGS.get("group_by_collection"),
                  sc.load_results_cache(), list(mc.SETTINGS.get("library_folders") or []), app._folder)
        _inr = lambda r: mc._pkey(r.get("library_root", "")) == mc._pkey(LIBR)
        try:
            _old = [dict(mc.scan_one_subfolder(os.path.join(LIBR, _nr), _nr, use_ffprobe=False))
                    for _nr in ("Old Saga One (2001)", "Old Saga Two (2003)", "Old Alone (2005)")]
            for _o in _old:                                   # as v0.19.3 wrote them: no B110 keys
                _o["library_root"] = LIBR
                for _kx in ("coll_nfo", "coll_xml", "coll_xml_hint", "coll_tmdb", "title_langs", "tmdb_titles"):
                    _o.pop(_kx, None)
            sc.save_results_cache(_old)
            def _go_restore():
                mc.SETTINGS["library_folders"] = [LIBR]; app._folder = LIBR
                app._results = []; app._clear_tree()
                app._restore_last_session()
            on_ui(_go_restore); wait_for(lambda: bool(app._results), 30)
            wait_for(lambda: not any(r.get("coll_unread") for r in app._results), 10)
            def _go_group():
                mc.SETTINGS["group_by_collection"] = True; app._group_var.set(True); app._refresh_table()
            on_ui(_go_group); wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)
            _cm = on_ui(lambda: sorted((v[1], len(v[2])) for v in app._coll_map.values()))
            _rc = {r["subfolder"]: mc.collection_name(r) for r in app._results if _inr(r)}
            wait_for(lambda: all("coll_nfo" in r for r in (sc.load_results_cache() or [])), 10)
            _saved = sc.load_results_cache() or []
            # ### MODIFIED v0.19.5 I20 ### split: a failure now says which condition failed and what the cache held
            check("B110a fix 1: a v0.19.3 cache restored → Group by collection groups the movies by their <set>", _cm == [("Old Saga", 2)], _cm)
            check("B110a fix 1: …each movie has its collection name at once", _rc.get("Old Alone (2005)") == "" and _rc.get("Old Saga One (2001)") == "Old Saga", _rc)
            check("B110a fix 1: …no row is left marked unread", not any(r.get("coll_unread") for r in app._results))
            check("B110a fix 1: …the cache is saved with the collections read", bool(_saved) and all("coll_nfo" in r and not r.get("coll_unread") for r in _saved),
                  [(r.get("subfolder"), "coll_nfo" in r, r.get("coll_unread")) for r in _saved][:6])
            _off = mc._results_from_json([{"subfolder": "Gone", "subfolder_path": os.path.join(_TMP, "NoSuchLib", "Gone"),
                                           "library_root": os.path.join(_TMP, "NoSuchLib"), "nfo_exists": True,
                                           "nfo_path": os.path.join(_TMP, "NoSuchLib", "Gone", "Gone.nfo")}])
            # ### NEW v0.19.5 ### a row saved by v0.19.4: new values with no rescan, once
            _d195 = os.path.join(_TMP, "t195", "Old Tags (2001)"); os.makedirs(_d195, exist_ok=True)
            io.open(os.path.join(_d195, "Old Tags (2001).mkv"), "wb").write(b"\0" * 64)
            _n195 = os.path.join(_d195, "movie.nfo")
            io.open(_n195, "w", encoding="utf-8", newline="\n").write('<movie>\n  <title>Old Tags</title>\n  <language>por</language>\n  <rating>7.4</rating>\n  <ratings><rating name="imdb" default="true"><value>8.8</value><votes>9</votes></rating></ratings>\n</movie>\n')
            _old195 = dict(mc.scan_one_subfolder(_d195, "Old Tags (2001)", use_ffprobe=False), lang_ok="Y", rating_str="7.4", language="eng")
            _old195["library_root"] = os.path.dirname(_d195)
            _rows195 = mc._results_from_json([json.loads(json.dumps(_old195, default=str))])
            _got195 = mc.read_old_tag_values(_rows195, True)
            check("v0.19.5: a row saved before it gets the new Language OK, Language and rating with no rescan", _got195 == 1
                  and (_rows195[0]["lang_ok"], _rows195[0]["rating_str"], _rows195[0]["language"]) == ("N", "8.8", "—"), _rows195[0].get("lang_ok"))
            _rows195b = mc._results_from_json([dict(json.loads(json.dumps(_old195, default=str)), library_root="Q:\\nowhere", lang_ok="Y")])
            _got195b = mc.read_old_tag_values(_rows195b, True)
            check("v0.19.5: a library out of reach keeps the mark, and the row is read at a later start", _got195b == 0 and _rows195b[0].get("tags_unread") is True and mc.read_old_tag_values(_rows195b, False) == 0 and _rows195b[0].get("tags_unread") is True)
            check("B110a fix 1: an unreachable library keeps the mark (read on the next scan)",
                  mc.read_unread_collections(_off) == 0 and _off[0].get("coll_unread") is True, _off[0].get("coll_unread"))
        finally:
            def _back_r():
                mc.SETTINGS["group_by_collection"] = _saver[2]; app._group_var.set(bool(_saver[2]))
                mc.SETTINGS["library_folders"] = _saver[4]; app._folder = _saver[5]
                app._results = _saver[0]; app._ignored_data = _saver[1]
                app._refresh_table(); app._update_ignored_link()
            on_ui(_back_r)
            sc.save_results_cache(_saver[3] or [])
            sc.save_ignored(_saver[1])
        _boxes.clear()

        # ── v0.19.4 B85: Quick Scan finds changes the newest mtime missed; first run per D3 ──  ### NEW v0.19.4 B85 ###
        LIB85 = os.path.join(_TMP, "Lib85"); os.makedirs(LIB85, exist_ok=True)
        def _m85(name):
            d = os.path.join(LIB85, name); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, name + ".mkv"), "wb").write(b"\0" * 64)
            _nfo(os.path.join(d, name + ".nfo"), name.split(" (")[0])
            _jpeg(os.path.join(d, "poster.jpg"), 200, 300)
            return d
        _a85, _b85 = _m85("Sig A (2001)"), _m85("Sig B (2002)")
        _save85 = (list(app._results), dict(app._ignored_data or {}))
        _in85 = lambda r: mc._pkey(r.get("library_root", "")) == mc._pkey(LIB85)
        try:
            on_ui(lambda: app._start_scan([LIB85], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            # D3: rows from before v0.19.4 (no signature) — the first Quick Scan stores it without a rescan
            for _r in app._results:
                if _in85(_r):
                    _r.pop("scan_sig", None)
            _boxes.clear()
            on_ui(lambda: app._start_quick_scan([LIB85])); wait_for(lambda: not app._scanning, 60)
            _d3_85 = any("up to date" in str(b) for b in _boxes) and all(r.get("scan_sig") for r in app._results if _in85(r))
            # a deleted poster: the newest mtime does not change (the other files are newer)
            _old85 = {f: os.path.getmtime(os.path.join(_a85, f)) for f in os.listdir(_a85)}
            os.remove(os.path.join(_a85, "poster.jpg"))
            _boxes.clear()
            on_ui(lambda: app._start_quick_scan([LIB85])); wait_for(lambda: not app._scanning, 60)
            _ra85 = next(r for r in app._results if _in85(r) and r["subfolder"] == "Sig A (2001)")
            check("B85: first Quick Scan after the update stores the signatures, no rescan ('up to date'); D3",
                  _d3_85, _boxes)
            check("B85: Quick Scan finds a deleted poster (the newest mtime did not change)",
                  not _ra85["poster_exists"] and not any("up to date" in str(b) for b in _boxes), (_ra85["poster_exists"], _boxes))
        finally:
            on_ui(lambda: (setattr(app, "_results", _save85[0]), setattr(app, "_ignored_data", _save85[1]),
                           app._refresh_table(), app._update_ignored_link(), app._incremental_save(app._results)))
            sc.save_ignored(_save85[1])
        _boxes.clear()

        # ── v0.19.4 B86: a replaced video does not keep the old FFprobe data ──  ### NEW v0.19.4 B86 ###
        LIB86 = os.path.join(_TMP, "Lib86"); os.makedirs(LIB86, exist_ok=True)
        def _m86(name, vbytes):
            d = os.path.join(LIB86, name); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, name + ".mkv"), "wb").write(b"\0" * vbytes)
            _nfo(os.path.join(d, name + ".nfo"), name.split(" (")[0])
            return d
        _a86, _b86 = _m86("Replaced Video (2001)", 64), _m86("Same Video (2002)", 64)
        _save86 = (list(app._results), dict(app._ignored_data or {}))
        _uf86 = on_ui(app._use_ffprobe.get)
        _in86 = lambda r: mc._pkey(r.get("library_root", "")) == mc._pkey(LIB86)
        try:
            on_ui(lambda: app._use_ffprobe.set(False))
            on_ui(lambda: app._start_scan([LIB86], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            for _r in app._results:                               # as if FFprobe had read both videos as 720p
                if _in86(_r):
                    _r.update({"video_width": 1280, "video_height": 720, "video_quality": "720p", "ffprobe_ran": True,
                               "audio_tracks": [{"language": "ENG", "codec": "AAC", "channels": "2.0", "bitrate": ""}]})
            time.sleep(1.2)
            open(os.path.join(_a86, "Replaced Video (2001).mkv"), "wb").write(b"\0" * 128)   # the video is replaced
            _nfo(os.path.join(_b86, "Same Video (2002).nfo"), "Same Video", year="2002")      # only the NFO changes
            on_ui(lambda: app._start_quick_scan([LIB86])); wait_for(lambda: not app._scanning, 60)
            _by86 = {r["subfolder"]: r for r in app._results if _in86(r)}
            check("B86: Quick Scan without FFprobe — a replaced video loses the old 720p / audio; the same video keeps them",
                  _by86["Replaced Video (2001)"]["video_quality"] == "—" and not _by86["Replaced Video (2001)"]["ffprobe_ran"]
                  and _by86["Same Video (2002)"]["video_quality"] == "720p" and _by86["Same Video (2002)"]["ffprobe_ran"],
                  {k: (v["video_quality"], v["ffprobe_ran"]) for k, v in _by86.items()})
            for _r in app._results:
                if _in86(_r) and _r["subfolder"] == "Same Video (2002)":
                    _r.update({"video_quality": "720p", "ffprobe_ran": True})
            open(os.path.join(_b86, "Same Video (2002).mkv"), "wb").write(b"\0" * 256)       # now this one is replaced too
            on_ui(lambda: app._start_scan([LIB86], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            _by86b = {r["subfolder"]: r for r in app._results if _in86(r)}
            check("B86: Full Scan without FFprobe — a replaced video does not keep the stored 720p",
                  _by86b["Same Video (2002)"]["video_quality"] == "—", {k: v["video_quality"] for k, v in _by86b.items()})
        finally:
            on_ui(lambda: app._use_ffprobe.set(_uf86))
            on_ui(lambda: (setattr(app, "_results", _save86[0]), setattr(app, "_ignored_data", _save86[1]),
                           app._refresh_table(), app._update_ignored_link(), app._incremental_save(app._results)))
            sc.save_ignored(_save86[1])
        _boxes.clear()

        # ── v0.19.4 B88: a folder that cannot be read keeps its previous row, flagged ──  ### NEW v0.19.4 B88 ###
        LIB88 = os.path.join(_TMP, "Lib88"); os.makedirs(LIB88, exist_ok=True)
        def _m88(name):
            d = os.path.join(LIB88, name); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, name + ".mkv"), "wb").write(b"\0" * 64)
            _nfo(os.path.join(d, name + ".nfo"), name.split(" (")[0])
            return d
        _hic88, _ok88 = _m88("Hiccup Movie (2001)"), _m88("Fine Movie (2002)")
        _save88 = (list(app._results), dict(app._ignored_data or {}))
        _in88 = lambda r: mc._pkey(r.get("library_root", "")) == mc._pkey(LIB88)
        _cls88 = mc.classify_listing
        def _unread88(lst):
            if mc._pkey(lst.path) == mc._pkey(_hic88):
                return "unreadable", "Could not be read: Access is denied (test)", ""
            return _cls88(lst)
        try:
            on_ui(lambda: app._start_scan([LIB88], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            for _r in app._results:                               # FFprobe data, an ID check and a duplicate mark to keep
                if _in88(_r) and _r["subfolder"] == "Hiccup Movie (2001)":
                    _r.update({"video_quality": "1080p", "ffprobe_ran": True, "id_check": {"result": mc.ID_OK},
                               "duplicate_of": ["Fine Movie (2002)"]})
            mc.classify_listing = _unread88
            on_ui(lambda: app._start_scan([LIB88], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            _h88 = next((r for r in app._results if _in88(r) and r["subfolder"] == "Hiccup Movie (2001)"), None)
            _tip88 = on_ui(lambda: app._tip_movie_name(_h88, None, None)) if _h88 else ""
            check("B88: Full Scan — a folder that cannot be read keeps its previous row (FFprobe data, ID check), flagged 'not read'",
                  _h88 is not None and _h88.get("read_error") and _h88["video_quality"] == "1080p" and _h88["nfo_exists"]
                  and (_h88.get("id_check") or {}).get("result") == mc.ID_OK and "[NOT READ]" in _tip88
                  and not any(i.get("kind") == "unreadable" and mc._pkey(i["path"]) == mc._pkey(_hic88)
                              for i in (app._ignored_data or {}).get("items", [])), (_h88, _tip88))
            on_ui(lambda: app._start_quick_scan([LIB88])); wait_for(lambda: not app._scanning, 60)
            _h88q = next((r for r in app._results if _in88(r) and r["subfolder"] == "Hiccup Movie (2001)"), None)
            mc.classify_listing = _cls88
            on_ui(lambda: app._start_quick_scan([LIB88])); wait_for(lambda: not app._scanning, 60)
            _h88r = next((r for r in app._results if _in88(r) and r["subfolder"] == "Hiccup Movie (2001)"), None)
            check("B88: Quick Scan keeps the flagged row while unreadable; once readable again, the next Quick Scan reads it (flag gone)",
                  _h88q is not None and _h88q.get("read_error") and _h88r is not None and not _h88r.get("read_error")
                  and _h88r["nfo_exists"], (_h88q and _h88q.get("read_error"), _h88r and _h88r.get("read_error")))
        finally:
            mc.classify_listing = _cls88
            on_ui(lambda: (setattr(app, "_results", _save88[0]), setattr(app, "_ignored_data", _save88[1]),
                           app._refresh_table(), app._update_ignored_link(), app._incremental_save(app._results)))
            sc.save_ignored(_save88[1])
        _boxes.clear()

        # ── v0.19.4 B90: Full Scan = Quick Scan for Date Added; the ID check survives a scan ──  ### NEW v0.19.4 B90 ###
        LIB90 = os.path.join(_TMP, "Lib90"); os.makedirs(LIB90, exist_ok=True)
        _d90 = os.path.join(LIB90, "Kept Check (2001)"); os.makedirs(_d90, exist_ok=True)
        _nfo(os.path.join(_d90, "Kept Check (2001).nfo"), "Kept Check", imdb="tt0090001", tmdb="90001")
        time.sleep(1.1)
        open(os.path.join(_d90, "Kept Check (2001).mkv"), "wb").write(b"\0" * 64)
        _save90 = (list(app._results), dict(app._ignored_data or {}))
        _in90 = lambda r: mc._pkey(r.get("library_root", "")) == mc._pkey(LIB90)
        _row90 = lambda: next(r for r in app._results if _in90(r))
        try:
            on_ui(lambda: app._start_scan([LIB90], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            _one90 = mc.scan_one_subfolder(_d90, "Kept Check (2001)", use_ffprobe=False)
            check("B90: Full Scan's Date Added = Quick Scan's (from the video, not the folder)",
                  (_row90()["date_added"], _row90()["date_added_src"]) == (_one90["date_added"], _one90["date_added_src"])
                  and _one90["date_added_src"] == "video", ((_row90()["date_added"], _row90()["date_added_src"]), (_one90["date_added"], _one90["date_added_src"])))
            _row90()["id_check"] = {"result": mc.ID_OK, "imdb_id": "tt0090001", "tmdb_id": "90001", "detail": "", "when": ""}
            on_ui(lambda: app._start_scan([LIB90], use_ff=False)); wait_for(lambda: not app._scanning, 60)
            _kept90 = (_row90().get("id_check") or {}).get("result")
            _row90()["id_check"] = {"result": mc.ID_OK, "imdb_id": "tt0090001", "tmdb_id": "90001", "detail": "", "when": ""}
            time.sleep(1.1)
            _nfo(os.path.join(_d90, "Kept Check (2001).nfo"), "Kept Check", imdb="tt0090002", tmdb="90002")   # other IDs
            on_ui(lambda: app._start_quick_scan([LIB90])); wait_for(lambda: not app._scanning, 60)
            check("B90: the online ID check survives a scan while the IDs are the same; new IDs drop it",
                  _kept90 == mc.ID_OK and not _row90().get("id_check"), (_kept90, _row90().get("id_check")))
        finally:
            on_ui(lambda: (setattr(app, "_results", _save90[0]), setattr(app, "_ignored_data", _save90[1]),
                           app._refresh_table(), app._update_ignored_link(), app._incremental_save(app._results)))
            sc.save_ignored(_save90[1])
        _boxes.clear()

        # ── v0.19.4 B92: a library that drops offline mid-listing is not half-listed ──  ### NEW v0.19.4 B92 ###
        LIB92a = os.path.join(_TMP, "Lib92a"); LIB92b = os.path.join(_TMP, "Lib92b")
        for _l92 in (LIB92a, LIB92b):
            for _n92 in ("One (2001)", "Two (2002)", "Three (2003)"):
                os.makedirs(os.path.join(_l92, _n92), exist_ok=True)
        _sd92 = mc.os.scandir
        def _drop92(p="."):
            it = _sd92(p)
            if mc._pkey(p) != mc._pkey(LIB92a):
                return it
            def _gen():
                n = 0
                for e in it:
                    n += 1
                    if n == 2:
                        raise OSError(64, "The specified network name is no longer available (test)")
                    yield e
            return _gen()
        try:
            mc.os.scandir = _drop92
            _e92, _on92, _off92 = app._collect_entries([LIB92a, LIB92b])
        finally:
            mc.os.scandir = _sd92
        check("B92: a library that drops offline mid-listing is listed as offline only (no half list → no duplicate of its kept rows)",
              _off92 == [LIB92a] and _on92 == [LIB92b] and len(_e92) == 3
              and all(mc._pkey(os.path.dirname(e.path)) == mc._pkey(LIB92b) for e in _e92), (_off92, _on92, [e.path for e in _e92]))

        # ── v0.19.4 B91: one guard, one message, for every action during a scan ──  ### NEW v0.19.4 B91 ###
        _acts91 = ["_recompute_health", "_open_scan_results", "_save_scan_results", "_sync_ratings_all",
                   "_normalize_sources_all", "_search_sources_all", "_verify_ids_all", "_auto_repair_all",
                   "_normalize_genres_all", "_run_improvements_all", "_show_health_report_all", "_refresh_icons",
                   "_delete_extrafanart_all", "_reval_selected_no_ffmpeg", "_reval_selected_ffmpeg", "_show_statistics",
                   "_show_duplicates", "_export_list_dialog", "_fix_images_all", "_nfo_rename_all"]
        _res91 = list(app._results); _got91 = {}
        on_ui(lambda: setattr(app, "_scanning", True))
        try:
            for _a91 in _acts91 + ["_copy_poster_to_folder", "_auto_repair", "_fix_images_for", "_show_health_report"]:
                _boxes.clear()
                if _a91 in ("_copy_poster_to_folder", "_auto_repair", "_fix_images_for", "_show_health_report"):
                    on_ui(lambda a=_a91: getattr(app, a)(list(app._results[:2])))
                else:
                    on_ui(lambda a=_a91: getattr(app, a)())
                _got91[_a91] = [b for b in _boxes if mc.SCAN_BUSY_TEXT in str(b)]
        finally:
            on_ui(lambda: setattr(app, "_scanning", False))
        _bad91 = [a for a, v in _got91.items() if len(v) != 1]
        check("B91: every results action refuses during a scan with ONE message ('A scan is running. Wait for it to finish or cancel it.')",
              not _bad91 and app._results == _res91 and len(_got91) == 24, _bad91)
        _boxes.clear()

        # ── v0.19.4 B98: grabs are given back (a question during a batch, the service-failure dialog) ──  ### NEW v0.19.4 B98 ###
        def _g98(w):
            return None if w is None else (type(w).__name__, str(w), w.title() if hasattr(w, "title") else "", bool(w.winfo_viewable()))
        _g0_98 = on_ui(lambda: _g98(app.grab_current()))
        def _b98():
            g0 = app.grab_current()
            prog = mc._BatchProgressDialog(app, "B98 batch", total=5)
            app.update()
            g1 = app.grab_current()
            q = mc._ServiceFailureDialog(app, "omdb", "daily_limit")
            app.update()
            g2 = app.grab_current()
            q.destroy(); app.update()
            g3 = app.grab_current()
            prog.destroy(); app.update()
            g4 = app.grab_current()
            return g1 is prog, g2 is q, g3 is prog, g4 is g0          # back to whoever had it before (normally nobody)
        _r98 = on_ui(_b98)
        check("B98: a batch window holds the grab; a question during it takes it and gives it BACK when closed (the main window stays blocked)",
              _r98 == (True, True, True, True), (_r98, "grab before:", _g0_98))
        _boxes.clear()

        # ── v0.19.4 B99: thread and key bugs ──  ### NEW v0.19.4 B99 ###
        import inspect as _insp99
        _w99 = _insp99.getsource(mc.FrameExtractionDialog._worker) + _insp99.getsource(mc.FrameExtractionDialog._worker_frames)
        _l99 = _insp99.getsource(mc._FetchImageDialog._load_local_image)
        check("B99: Frame extraction reads its Tk variables on the Tk thread; the fetch preview builds no PhotoImage in its worker",
              "_var.get()" not in _w99 and "PhotoImage(" in _insp99.getsource(mc._FetchImageDialog._load_local_image).split("def _show", 1)[1]
              and "PhotoImage(" not in _l99.split("def _show", 1)[0] and "_load_photo(" not in _l99)
        check("B99: the animation stops with its window; the close paths cancel timers in Tcl (no after_cancel)",
              "winfo_exists" in _insp99.getsource(mc.FrameExtractionDialog._animate_progress)
              and 'tk.call("after", "cancel"' in _insp99.getsource(mc.FrameExtractionDialog._stop_anim)
              and "after_cancel" not in _insp99.getsource(mc._remember_window).split("def _on_destroy", 1)[1])
        _canc99 = []; _oc99 = app._cancel
        app._cancel = lambda *a: _canc99.append(1)
        try:
            on_ui(lambda: (setattr(app, "_scanning", True), app._filter_var.set("abc")))
            on_ui(lambda: (_fire(app._filter_entry, "<Escape>"), app.update()))
            _fv99 = on_ui(app._filter_var.get)
        finally:
            app._cancel = _oc99
            on_ui(lambda: (setattr(app, "_scanning", False), app._filter_var.set("")))   # I24: a missed Esc cannot empty the table
        check("B99: Esc in the Filter box clears the filter and does NOT cancel a running scan",
              _fv99 == "" and _canc99 == [], (_fv99, _canc99))
        _dlg99, _res99 = [], []
        def _mk99():
            d = tk.Toplevel(app); _dlg99.append(d); return d
        threading.Thread(target=lambda: _res99.append(app._ask_on_ui(_mk99, lambda d: "answer", timeout=3)), daemon=True).start()
        wait_for(lambda: bool(_dlg99), 10)                        # I22: built first, also on a busy PC
        wait_for(lambda: bool(_res99), 10); time.sleep(0.3)
        check("B99: _ask_on_ui gives up after its timeout AND closes its question window",
              _res99 == [None] and _dlg99 and not on_ui(lambda: bool(_dlg99[0].winfo_exists())), (_res99, len(_dlg99)))

        # ### NEW v0.19.5 I22 ### the time ran out before the Tk thread could build the question
        _dlg99b, _res99b = [], []
        def _mk99b():
            d = tk.Toplevel(app); _dlg99b.append(d); return d
        mc.ui_post(time.sleep, 1.0)
        threading.Thread(target=lambda: _res99b.append(app._ask_on_ui(_mk99b, lambda d: "answer", timeout=0.1)), daemon=True).start()
        wait_for(lambda: bool(_res99b), 10); on_ui(lambda: None); on_ui(lambda: None)
        check("I22: a question that timed out before the Tk thread was free is never opened", _res99b == [None] and not _dlg99b, (_res99b, len(_dlg99b)))

        # ── v0.19.4 B100: no disk / FFprobe work on the Tk thread (heartbeat with a slow fake share) ──  ### NEW v0.19.4 B100 ###
        LIB100 = os.path.join(_TMP, "Lib100"); os.makedirs(os.path.join(LIB100, "Slow Share Movie (2001)"), exist_ok=True)
        open(os.path.join(LIB100, "Slow Share Movie (2001)", "Slow Share Movie (2001).mkv"), "wb").write(b"\0" * 64)
        _save100 = (list(app._results), dict(app._ignored_data or {}))
        _sd100 = mc.os.scandir
        def _slow100(pth="."):
            if mc._pkey(pth) == mc._pkey(LIB100):
                time.sleep(1.5)                                        # a slow network share
            return _sd100(pth)
        _hb100, _stop100 = [], [False]
        def _beat100():
            _hb100.append(time.monotonic())
            if not _stop100[0]:
                app.after(20, _beat100)
        try:
            mc.os.scandir = _slow100
            on_ui(lambda: app.after(0, _beat100)); time.sleep(0.2)
            on_ui(lambda: app._start_quick_scan([LIB100]))
            wait_for(lambda: not app._scanning, 60); time.sleep(0.2)
        finally:
            mc.os.scandir = _sd100; _stop100[0] = True
            on_ui(lambda: (setattr(app, "_results", _save100[0]), setattr(app, "_ignored_data", _save100[1]),
                           app._refresh_table(), app._update_ignored_link(), app._incremental_save(app._results)))
            sc.save_ignored(_save100[1])
        _gap100 = max((b - a for a, b in zip(_hb100, _hb100[1:])), default=99)
        check("B100: Quick Scan on a slow share (1.5 s listing) — the Tk loop never pauses over 250 ms",
              len(_hb100) > 20 and _gap100 < 0.25, (len(_hb100), round(_gap100, 3)))
        import inspect as _insp100
        _ai100 = _insp100.getsource(mc._FetchImageDialog._apply_image).split("def _worker", 1)
        _rl100 = _insp100.getsource(mc._FetchBackdropDialog._replace_local)
        _lc100 = _insp100.getsource(mc.App._on_settings_changed) if hasattr(mc, "App") else ""
        check("B100: the Fetch dialogs back up in their worker; the language recompute runs in a worker",
              "_backup_ok(" not in _ai100[0] and "_backup_ok(" in _ai100[1] and "_backup_ok(" not in _rl100
              and "backup_of=(movie, fpath)" in _rl100
              and (not _lc100 or ("threading.Thread(target=_lang_work" in _lc100)))
        _boxes.clear()

        # ── v0.19.4 B102: Ctrl+R / Ctrl+Shift+R act on every selected movie ──  ### NEW v0.19.4 B102 ###
        _calls102 = []
        _o102 = {n: app.__dict__.get(n) for n in ("_reval_no_ffmpeg", "_reval_ffmpeg", "_reval_multi_no_ffmpeg", "_reval_multi_ffmpeg")}
        app._reval_no_ffmpeg = lambda iid, d: _calls102.append(("one", 1))
        app._reval_ffmpeg = lambda iid, d: _calls102.append(("one ff", 1))
        app._reval_multi_no_ffmpeg = lambda iids, data: _calls102.append(("multi", len(data)))
        app._reval_multi_ffmpeg = lambda iids, data: _calls102.append(("multi ff", len(data)))
        _sel102 = on_ui(lambda: app.tree.selection())
        try:
            _kids102 = on_ui(lambda: list(app.tree.get_children())[:3])
            on_ui(lambda: app.tree.selection_set(_kids102))
            on_ui(app._reval_selected_no_ffmpeg); on_ui(app._reval_selected_ffmpeg)
            on_ui(lambda: app.tree.selection_set(_kids102[:1]))
            on_ui(app._reval_selected_no_ffmpeg)
        finally:
            for _n102, _v102 in _o102.items():
                if _v102 is None:
                    app.__dict__.pop(_n102, None)
                else:
                    setattr(app, _n102, _v102)
            on_ui(lambda: app.tree.selection_set(_sel102))
        check("B102: Ctrl+R / Ctrl+Shift+R update every selected movie (3 → the 'several' update); one selected → the single update",
              len(_kids102) == 3 and _calls102 == [("multi", 3), ("multi ff", 3), ("one", 1)], (_calls102, len(_kids102)))

        # ── v0.19.4 B104: Clear All and the Ignored Folders list; no scan yet ──  ### NEW v0.19.4 B104 ###
        _ask104 = []
        _oa104 = mc.messagebox.askyesno
        mc.messagebox.askyesno = lambda title, msg, **k: (_ask104.append(msg), False)[1]   # answer No: nothing cleared
        _keep104 = (list(app._results), app._ignored_data)
        try:
            on_ui(app._clear_all)
            _boxes.clear()
            on_ui(lambda: (setattr(app, "_results", []), setattr(app, "_ignored_data", {})))
            on_ui(app._show_ignored)
            _nos104 = [b for b in _boxes if "No scan has run yet" in str(b)]
        finally:
            mc.messagebox.askyesno = _oa104
            on_ui(lambda: (setattr(app, "_results", _keep104[0]), setattr(app, "_ignored_data", _keep104[1])))
        check("B104: Clear All's question says the Ignored Folders list is emptied too; Ignored Folders before any scan says 'No scan has run yet'",
              len(_ask104) == 1 and "Ignored Folders list" in _ask104[0] and len(_nos104) == 1 and len(app._results) == len(_keep104[0]),
              (_ask104, _boxes))
        _boxes.clear()

        # ── v0.19.4 B106: Update with FFprobe — one: status bar; several: progress + Cancel; one wording ──  ### NEW v0.19.4 B106 ###
        _rows106 = [r for r in app._results if os.path.isdir(r.get("subfolder_path", ""))][:3]
        _iids106 = on_ui(lambda: [next((i for i, d in app._item_map.items() if d is r), None) for r in _rows106])
        _o106 = app.__dict__.get("_rescan_row")
        _n106 = [0]
        def _fake106(d, force_ffprobe=False):
            _n106[0] += 1
            if _n106[0] == 2 and getattr(app, "_reval_prog", None) is not None and _multi106[0]:
                app._reval_prog.cancelled = True                 # Cancel pressed while the 2nd movie is probed
            return dict(d)
        _multi106 = [False]
        app._rescan_row = _fake106
        _boxes.clear()
        try:
            on_ui(lambda: app._reval_ffmpeg(_iids106[0], _rows106[0]))
            wait_for(lambda: mc.UPDATE_FF_TEXT in on_ui(lambda: app._sb_action.cget("text")), 10)
            _one106 = (list(_boxes), on_ui(lambda: app._sb_action.cget("text")))
            _boxes.clear(); _n106[0] = 0; _multi106[0] = True
            on_ui(lambda: app._reval_multi_ffmpeg(list(_iids106), list(_rows106)))
            wait_for(lambda: any(b[1] and b[1][0] == mc.UPDATE_FF_TEXT for b in _boxes), 15); time.sleep(0.2)
            _many106 = [b for b in _boxes if b[1] and b[1][0] == mc.UPDATE_FF_TEXT]
        finally:
            if _o106 is None:
                app.__dict__.pop("_rescan_row", None)
            else:
                app._rescan_row = _o106
        check("B106: Update with FFprobe on one movie → a status-bar line, no pop-up",
              len(_rows106) == 3 and None not in _iids106 and _one106[0] == [] and mc.UPDATE_FF_TEXT in _one106[1], _one106)
        check("B106: several → the progress window with Cancel; the result says 'Cancelled after 2 of 3' in the same wording",
              len(_many106) == 1 and "Cancelled after 2 of 3" in str(_many106[0]) and "Re-validat" not in str(_many106[0])
              and not any("FFprobe Done" in str(b) or "Re-validate Done" in str(b) for b in _boxes), _boxes)
        _boxes.clear()

        # ── v0.19.4 B107: "Rename NFO for Kodi…" in the right-click Metadata submenu ──  ### NEW v0.19.4 B107 ###
        def _meta107(rows):
            app._build_ctx_menu(None, rows[0], rows)
            md = next(sm for sm in app._ctx_subs if any(str(sm.entrycget(i, "label")).startswith("📝  Open .nfo")
                                                         for i in range(sm.index("end") + 1) if sm.type(i) == "command"))
            return [(str(md.entrycget(i, "label")), str(md.entrycget(i, "state"))) for i in range(md.index("end") + 1)
                    if md.type(i) == "command" and str(md.entrycget(i, "label")).startswith(mc.NFO_RENAME_LABEL)]
        _base107 = next(r for r in app._results if r.get("nfo_exists"))
        _bad107 = dict(_base107, nfo_kodi_name=False); _ok107 = dict(_base107, nfo_kodi_name=True)
        _e107a = on_ui(lambda: _meta107([_bad107])); _e107b = on_ui(lambda: _meta107([_ok107]))
        _e107c = on_ui(lambda: _meta107([_bad107, _ok107]))
        check("B107: 'Rename NFO for Kodi…' is in the right-click Metadata submenu; greyed when Kodi already reads the NFO; '— 1 of 2' for several",
              _e107a == [(mc.NFO_RENAME_LABEL, "normal")] and len(_e107b) == 1 and _e107b[0][1] == "disabled"
              and "Kodi already reads the NFO" in _e107b[0][0] and _e107c and _e107c[0][0].endswith("— 1 of 2"), (_e107a, _e107b, _e107c))

        # ── v0.19.4 B109: small improvements a–f ──  ### NEW v0.19.4 B109 ###
        _r109 = on_ui(lambda: mc.HealthReportDialog(app, "line one\nline two\nline three", 3))
        try:
            _btn109 = on_ui(lambda: [str(w.cget("text")).strip() for w in _r109._btn_row.winfo_children()
                                     if isinstance(w, tk.Button)])   # v0.19.4 L4: the frame's button row (intended)
            on_ui(_r109._copy)
            _sb109 = on_ui(lambda: app._sb_action.cget("text"))
        finally:
            on_ui(_r109.destroy)
        check("B109 a/f: the Health report has Copy / Save to .txt / Close (no 'OK'); Copy flashes 'Copied 3 lines'",
              _btn109[-3:] == ["📋 Copy", "💾 Save to .txt", "Close"] and "Copied 3 lines" in _sb109, (_btn109, _sb109))
        _ask109, _open109 = [], []
        _oa109, _oo109 = mc.messagebox.askyesno, mc.os_open
        mc.messagebox.askyesno = lambda t, m, **k: (_ask109.append(m), True)[1]
        mc.os_open = lambda pth: _open109.append(pth)
        try:
            mc.saved_offer_open(app, "Saved", os.path.join(_TMP, "r109.txt"), "Report saved to")
        finally:
            mc.messagebox.askyesno, mc.os_open = _oa109, _oo109
        check("B109 b: a saved report offers 'Open it now?' and opens the file on yes",
              _ask109 and "Open it now?" in _ask109[0] and _open109 == [os.path.join(_TMP, "r109.txt")], (_ask109, _open109))
        _nonfo109 = dict(next(r for r in app._results), nfo_exists=False, movie_name="No Nfo Movie")
        _ed109 = []; _oe109 = mc.open_in_editor; mc.open_in_editor = lambda pth: _ed109.append(pth)
        _iid109 = on_ui(lambda: app.tree.get_children()[0]); _keep109 = app._item_map.get(_iid109)
        try:
            app._item_map[_iid109] = _nonfo109
            on_ui(lambda: (app.tree.selection_set(_iid109), app._open_editor_shortcut()))
            _sb109c = on_ui(lambda: app._sb_action.cget("text"))
        finally:
            app._item_map[_iid109] = _keep109; mc.open_in_editor = _oe109
        check("B109 c: Ctrl+E on a movie without NFO says so in the status bar (no empty editor)",
              _ed109 == [] and "no NFO to open" in _sb109c, (_ed109, _sb109c))
        _filt109 = on_ui(lambda: (app._filter_var.get()))
        on_ui(lambda: app._filter_var.set("zzz-no-such-movie-109")); time.sleep(0.6); on_ui(lambda: app.update())
        _note109 = on_ui(lambda: mc.all_movies_note(app))
        on_ui(lambda: app._filter_var.set(_filt109)); time.sleep(0.6); on_ui(lambda: app.update())
        check("B109 d: an '— All Movies' preview says 'all N movies in all libraries (the filter shows M)' while a filter hides rows",
              _note109.startswith("This runs on all ") and "(the filter shows 0)" in _note109, _note109)
        check("B109 e: batch results mention Backup History / Undo", "Backup History / Undo" in mc.UNDO_HINT
              and "UNDO_HINT" in io.open(mc.__file__, encoding="utf-8").read().split("def _sync_ratings_worker_run", 1)[1][:20000])
        _boxes.clear()

        # ── v0.19.4: a Tk object collected on another thread while the Tk thread waits for that thread (a freeze CI found) ──
        import gc as _gc_del
        _box_del = {"v": on_ui(lambda: tk.StringVar(app, value="x"))}
        _name_del = str(_box_del["v"])
        _done_del, _res_del = threading.Event(), []

        def _worker_del():
            _box_del.clear()                                   # the last reference goes here: __del__ runs on this thread
            _gc_del.collect()
            _done_del.set()
        on_ui(lambda: (threading.Thread(target=_worker_del, daemon=True).start(), _res_del.append(_done_del.wait(8))))
        check("freeze: a Tk variable collected on another thread does not wait for the Tk thread that waits for it", _res_del == [True], _res_del)
        wait_for(lambda: not on_ui(lambda: app.tk.getboolean(app.tk.call("info", "exists", _name_del))), 10)
        check("freeze: …and its clean-up still runs, on the Tk thread", not on_ui(lambda: app.tk.getboolean(app.tk.call("info", "exists", _name_del))), _name_del)
        check("freeze: Variable, Image, Font (B114) and Pillow's PhotoImage / BitmapImage all clean up this way",
              all(getattr(c.__del__, "_mc_safe", False) for c in (tk.Variable, tk.Image, tkinter.font.Font, mc._PILImageTk.PhotoImage, mc._PILImageTk.BitmapImage)))
        # ### NEW v0.19.5 B114 ### a Font collected on another thread is deleted later, on the Tk thread
        _fn114 = on_ui(lambda: (lambda f: (f.name, f))(tkinter.font.Font(font=("Helvetica", 10))))
        _name114 = _fn114[0]
        def _drop114(box=[_fn114[1]]):
            box.clear()
        del _fn114
        _td114 = threading.Thread(target=_drop114.__defaults__[0].clear, daemon=True); _td114.start(); _td114.join(5)
        import gc as _gc114
        _gc114.collect()
        wait_for(lambda: _name114 not in on_ui(lambda: app.tk.splitlist(app.tk.call("font", "names"))), 5)
        check("B114: a Font released on another thread is deleted on the Tk thread", not _td114.is_alive()
              and _name114 not in on_ui(lambda: app.tk.splitlist(app.tk.call("font", "names"))))

        # ── v0.19.4 I13: the built menus = the registry; the shortcuts run registry actions ──  ### NEW v0.19.4 I13 ###
        _tm13 = on_ui(lambda: ["-" if app._tools_menu.type(i) == "separator" else app._tools_menu.entrycget(i, "label")
                               for i in range(app._tools_menu.index("end") + 1)])
        _ran13 = []
        _orig13 = mc.ACTIONS["refresh_icons"]["run"]
        mc.ACTIONS["refresh_icons"]["run"] = lambda a: _ran13.append("refresh")
        try:
            on_ui(lambda: _fire(app, "<Control-i>"))
            on_ui(lambda: (app.update(), app.run_action("refresh_icons")))
        finally:
            mc.ACTIONS["refresh_icons"]["run"] = _orig13
        check("I13: the Tools menu as built = the registry list; an action runs through the registry",
              _tm13 == ["-" if a == "-" else mc.ACTIONS[a]["label"] for a in mc.TOOLS_MENU] and "refresh" in _ran13, (_tm13[:4], _ran13))

        # ── v0.19.5 AS-A9, SH-E2, SH-E4 ──  ### NEW v0.19.5 ###
        _keep_p3 = (list(app._results),)
        _ra9 = [dict(r) for r in app._results[:2]]
        if len(_ra9) == 2:
            try:
                _ra9[0].update(source_imdb_val="tt7770001", source_imdb_all=["tt7770001"], source_tmdb_val="", duplicate_of=[], movie_name="Dup Alpha", movie_year="1991", subfolder="Dup Alpha")
                _ra9[1].update(source_imdb_val="tt7770001", source_imdb_all=["tt7770001"], source_tmdb_val="", duplicate_of=[], movie_name="Dup Omega", movie_year="1992", subfolder="Dup Omega")
                on_ui(lambda: setattr(app, "_results", _ra9))
                on_ui(app._recheck_duplicates)
                _b9 = bool(_ra9[0].get("duplicate_of"))
                _o9 = _ra9[1]
                _n9 = dict(_o9, source_imdb_val="tt7770002", source_imdb_all=["tt7770002"])
                def _sw9():
                    app._results[1] = _n9
                    app._regroup_if_moved(_o9, _n9)
                on_ui(_sw9)
                wait_for(lambda: not on_ui(lambda: app._results[0].get("duplicate_of")), 5)
                check("AS-A9: a changed ID: the duplicate warning goes without a scan", _b9 and not on_ui(lambda: app._results[0].get("duplicate_of")), (_b9, on_ui(lambda: app._results[0].get("duplicate_of"))))
                on_ui(lambda: (setattr(app, "_results", []), app._refresh_table()))
                check("SH-E2: the last rows leave the screen too", on_ui(lambda: (not app.tree.get_children()) and not app._item_map))
            finally:
                on_ui(lambda: (setattr(app, "_results", _keep_p3[0]), mc.finalize_results(app._results), app._refresh_table()))
                _settle()
        _ask_e4 = []
        _oy_e4 = mc.messagebox.askyesno
        mc.messagebox.askyesno = lambda t, m, **k: (_ask_e4.append(m), False)[1]
        try:
            on_ui(lambda: setattr(app, "_bg_running", 1))
            on_ui(app._on_app_close)
        finally:
            on_ui(lambda: setattr(app, "_bg_running", 0)); mc.messagebox.askyesno = _oy_e4
        check("SH-E4: closing during an action asks; No keeps the app open", len(_ask_e4) == 1 and "still running" in _ask_e4[0] and on_ui(lambda: bool(app.winfo_exists())), _ask_e4)

        # ── v0.19.5 B120: no default heading is cut off ──  ### NEW v0.19.5 B120 ###
        def _heads120():
            base = float(app.tk.call("tk", "scaling")); bad = []
            try:
                fn = ttk_style_font = mc.ttk.Style(app).lookup("Treeview.Heading", "font")
                for pct in (100, 125, 150):
                    app.tk.call("tk", "scaling", 96 / 72 * pct / 100)
                    f = tkinter.font.Font(root=app, font=fn)
                    for c in mc.COLUMN_MODEL:
                        lab = str(app.tree.heading(c["id"], "text")).split("  ")[0]
                        if f.measure(lab) + 12 > int(round(c["width"] * pct / 100)):
                            bad.append((pct, c["id"], lab))
            finally:
                app.tk.call("tk", "scaling", base)
            return bad
        _bad120 = on_ui(_heads120)
        check("B120: no default column heading is cut off at 100, 125 and 150 %", not _bad120, _bad120)

        # ── v0.19.5 B112: another program's PrintWindow can stop Tk's timers; the watchdog wakes the loop ──  ### NEW v0.19.5 B112 ###
        # In a child process with its own App: PrintWindow is run from here, as another program would, and upsets no other test.
        if sys.platform == "win32":
            import ctypes as _ct112, subprocess as _sp112
            _d112 = os.path.join(_TMP, "b112"); os.makedirs(os.path.join(_d112, "cfg"), exist_ok=True)
            _hb112, _hw112 = os.path.join(_d112, "hb"), os.path.join(_d112, "hw")
            _code112 = (f"import sys; sys.path.insert(0, {_APP_DIR!r}); import {mc.__name__} as mc\n"
                        "app = mc.App(); app.update()\n"
                        f"open({_hw112!r}, 'w').write(str(int(app.wm_frame(), 16)))\n"
                        "n = [0]\n"
                        f"def beat():\n    n[0] += 1; open({_hb112!r}, 'w').write(str(n[0])); app.after(100, beat)\n"
                        "beat(); app.mainloop()\n")
            _env112 = dict(os.environ, MEDIACLINIC_CONFIG_DIR=os.path.join(_d112, "cfg"), MEDIACLINIC_BACKUP_DIR=os.path.join(_d112, "bk"),
                           MEDIACLINIC_UPDATE_API="file:///nonexistent/fake.json", PYTHONIOENCODING="utf-8")
            _p112 = _sp112.Popen([sys.executable, "-c", _code112], env=_env112, cwd=_APP_DIR, stdout=_sp112.DEVNULL, stderr=_sp112.DEVNULL)
            _gaps112 = []
            try:
                wait_for(lambda: os.path.exists(_hw112) and os.path.getsize(_hw112) > 0, 120)
                time.sleep(2)
                _u112, _g112 = _ct112.windll.user32, _ct112.windll.gdi32
                _u112.GetDC.restype = _g112.CreateCompatibleDC.restype = _g112.CreateCompatibleBitmap.restype = _ct112.c_void_p
                _g112.CreateCompatibleDC.argtypes = [_ct112.c_void_p]
                _g112.CreateCompatibleBitmap.argtypes = [_ct112.c_void_p, _ct112.c_int, _ct112.c_int]
                _g112.SelectObject.argtypes = [_ct112.c_void_p, _ct112.c_void_p]
                _u112.PrintWindow.argtypes = [_ct112.c_void_p, _ct112.c_void_p, _ct112.c_uint]
                _sdc112 = _u112.GetDC(None); _dc112 = _g112.CreateCompatibleDC(_sdc112)
                _g112.SelectObject(_dc112, _g112.CreateCompatibleBitmap(_sdc112, 400, 300))
                _h112 = int(open(_hw112).read())
                def _beat112():
                    try:
                        return open(_hb112).read()
                    except OSError:
                        return ""
                for _i112 in range(6):
                    _u112.PrintWindow(_ct112.c_void_p(_h112), _dc112, 2)
                    _b112 = _beat112(); _t112 = time.monotonic()
                    while _beat112() == _b112 and time.monotonic() - _t112 < 15:
                        time.sleep(0.05)
                    _gaps112.append(round(time.monotonic() - _t112, 1))
            finally:
                _p112.kill()
            check("B112: after another program's PrintWindow the Tk timers run again, with nobody at the mouse", _gaps112 and max(_gaps112) < 14, _gaps112)

        # ── v0.19.4 B110b: Check Collections Online (fake TMDB) ──  ### NEW v0.19.4 B110b ###
        _rows2b = [r for r in app._results if (r.get("source_tmdb_val") or "").strip()][:2]
        if len(_rows2b) < 2:
            _rows2b = list(app._results)[:2]
        _keep2b = [{k: r.get(k) for k in ("source_tmdb_val", "coll_tmdb", "title_langs", "id_check")} for r in _rows2b]
        for _i2b, _r2b in enumerate(_rows2b):
            _r2b["source_tmdb_val"] = str(800 + _i2b); _r2b["coll_tmdb"] = None; _r2b["id_check"] = None
        _calls2b = []

        def _fake2b(url):
            _calls2b.append(url)
            if "/collection/" in url and "/translations" in url:
                return {"translations": [{"iso_639_1": "en", "data": {"title": "Fake Saga"}}]}
            if "/collection/" in url:
                return {"name": "Fake Saga", "parts": [{"id": 800}, {"id": 801}]}
            return {"id": int(url.split("/movie/")[1].split("?")[0]), "title": "x", "belongs_to_collection": {"id": 55, "name": "Fake Saga"}}
        _oks2b = mc.SETTINGS.get("tmdb_api_key", ""); mc.SETTINGS["tmdb_api_key"] = "fake-key"
        _ocs2b = app._confirm_services; app._confirm_services = lambda s: True
        try:
            app._coll_check_done = None; _boxes.clear()
            on_ui(lambda: app._check_collections(list(_rows2b), fetch=_fake2b))
            wait_for(lambda: app._coll_check_done is not None, 20)
            _res2b = app._coll_check_done
            _mov2b = [u for u in _calls2b if "/movie/" in u]; _col2b = [u for u in _calls2b if "/collection/" in u]
            check("B110b: Check Collections Online — one request per movie, two per collection; the rows get coll_tmdb; a summary",
                  _res2b and _res2b[:2] == (2, 1) and len(_mov2b) == 2 and len(_col2b) == 2
                  and all((r.get("coll_tmdb") or {}).get("id") == 55 for r in _rows2b) and "55" in mc.COLL_CACHE
                  and any("2 movies checked" in str(b) for b in _boxes), (_res2b, len(_mov2b), len(_col2b), _boxes[-1:]))
            _calls2b.clear(); app._coll_check_done = None
            on_ui(lambda: app._check_collections(list(_rows2b), fetch=_fake2b))
            wait_for(lambda: app._coll_check_done is not None or any("checked less than" in str(b) for b in _boxes), 10)
            check("B110b: checked less than 30 days ago → not asked again", not _calls2b, _calls2b)
            # fix 12: … unless the user says "Check them again now?" → Yes
            _calls2b.clear(); app._coll_check_done = None
            _oask12 = mc.messagebox.askyesno
            mc.messagebox.askyesno = lambda *a, **k: (_boxes.append(("ask", a[:2])), True)[1]
            try:
                on_ui(lambda: app._check_collections(list(_rows2b), fetch=_fake2b))
                wait_for(lambda: app._coll_check_done is not None, 20)
            finally:
                mc.messagebox.askyesno = _oask12
            check("fix 12: all checked recently → 'Check them again now?' → Yes checks them again",
                  any(b[0] == "ask" and "again now?" in str(b[1]) for b in _boxes)
                  and len([u for u in _calls2b if "/movie/" in u]) == 2, (_calls2b, _boxes[-2:]))
            # fix 10: TMDB's translations without an English name → the collection is asked in English; a cached
            # collection without it is checked again
            _calls2b.clear(); app._coll_check_done = None
            mc.COLL_CACHE["55"] = {"names": {"pt": "Saga Falsa"}, "overviews": {}, "parts": [], "when": time.time()}

            def _fake10(url):
                _calls2b.append(url)
                if "/collection/" in url and "/translations" in url:
                    return {"translations": [{"iso_639_1": "en", "data": {"title": ""}},
                                             {"iso_639_1": "pt", "data": {"title": "Saga Falsa"}}]}
                if "/collection/" in url:
                    return ({"name": "Fake Saga", "overview": "ov en"} if "language=en-US" in url
                            else {"name": "Saga Falsa", "parts": [{"id": 800}, {"id": 801}]})
                return _fake2b(url)
            on_ui(lambda: app._check_collections(list(_rows2b), fetch=_fake10))
            wait_for(lambda: app._coll_check_done is not None, 20)
            _en10 = [u for u in _calls2b if "/collection/" in u and "language=en-US" in u]
            check("fix 10: no English name cached → checked again; TMDB's empty English entry → the collection is asked in English",
                  app._coll_check_done is not None and len(_en10) == 1
                  and mc.COLL_CACHE.get("55", {}).get("names", {}).get("en") == "Fake Saga"
                  and mc.COLL_CACHE["55"]["overviews"].get("en") == "ov en", (_calls2b, mc.COLL_CACHE.get("55")))
            import urllib.error as _ue2b
            for _r2b in _rows2b:
                _r2b["coll_tmdb"] = None

            def _fail2b(url):
                if url.split("/movie/")[-1].startswith("801"):
                    raise _ue2b.URLError("offline")
                return _fake2b(url)
            app._coll_check_done = None; _boxes.clear()
            on_ui(lambda: app._check_collections(list(_rows2b), fetch=_fail2b))
            wait_for(lambda: app._coll_check_done is not None, 20)
            _res2c = app._coll_check_done
            check("B110b: a network error stops the run, keeps what was fetched and says so",
                  _res2c and _res2c[0] == 1 and _res2c[3] and (_rows2b[0].get("coll_tmdb") or {}).get("id") == 55
                  and any(b[0] == "error" for b in _boxes), (_res2c, _boxes[-1:]))
            _boxes.clear()
        finally:
            mc.SETTINGS["tmdb_api_key"] = _oks2b; app._confirm_services = _ocs2b
            for _r2b, _k2b in zip(_rows2b, _keep2b):
                _r2b.update(_k2b)
            on_ui(lambda: (mc.finalize_results(app._results), app._refresh_table()))
            _settle()

        # ── v0.19.4 B110e: the collection fix / Set / Remove on real files (temp copies) ──  ### NEW v0.19.4 B110e ###
        _de = tempfile.mkdtemp(prefix="mc_b110e_ui_")
        _rows_e = []
        for _i_e, _nm_e in enumerate(("Saga One (2001)", "Saga Two (2003)")):
            _p_e = os.path.join(_de, _nm_e); os.makedirs(_p_e)
            open(os.path.join(_p_e, _nm_e + ".nfo"), "w", encoding="utf-8").write(f"<movie>\n  <title>{_nm_e[:-7]}</title>\n</movie>\n")
            _rows_e.append({"movie_name": _nm_e[:-7], "subfolder": _nm_e, "subfolder_path": _p_e, "nfo_exists": True,
                            "nfo_path": os.path.join(_p_e, _nm_e + ".nfo"), "coll_nfo": None, "title_langs": ["en"],
                            "coll_tmdb": {"id": 55, "name": "Fake Saga", "when": time.time()}})
        _occ_e = dict(mc.COLL_CACHE); mc.COLL_CACHE["55"] = {"names": {"en": "Fake Saga"}, "overviews": {}}
        _osr_e = app._schedule_refresh; app._schedule_refresh = lambda *a, **k: None
        try:
            app._coll_write_done = None; _boxes.clear()
            on_ui(lambda: app._fix_collections_for(list(_rows_e), preview=False))
            wait_for(lambda: app._coll_write_done is not None, 15)
            _txt_e = [open(r["nfo_path"], encoding="utf-8").read() for r in _rows_e]
            check("B110e: Fix Collection writes TMDB's collection to every selected NFO; summary with Undo",
                  app._coll_write_done == (2, []) and all('<set tmdbcolid="55">' in x and "<name>Fake Saga</name>" in x for x in _txt_e)
                  and any("Backup History / Undo" in str(b) for b in _boxes), (app._coll_write_done, _txt_e[0], _boxes[-1:]))
            app._coll_write_done = None
            on_ui(lambda: app._set_collection_for(_rows_e[:1], name="My Own Set"))
            wait_for(lambda: app._coll_write_done is not None, 15)
            _t1_e = open(_rows_e[0]["nfo_path"], encoding="utf-8").read()
            check("B110e: Set Collection… writes a user-made set (no tmdbcolid for a name TMDB does not know)",
                  "<set>\n    <name>My Own Set</name>" in _t1_e and "tmdbcolid" not in _t1_e, _t1_e)
            for _r_e in _rows_e:
                _r_e["coll_nfo"] = {"name": "x"}
            app._coll_write_done = None
            on_ui(lambda: app._remove_collection_for(list(_rows_e), ask=False))
            wait_for(lambda: app._coll_write_done is not None, 15)
            check("B110e: Remove from Collection… takes the <set> out of each NFO (only this entry removes one)",
                  all("<set" not in open(r["nfo_path"], encoding="utf-8").read() for r in _rows_e))
            _plan_e = mc._auto_repair_plan(dict(_rows_e[0], coll_nfo={"name": "Wrong", "tmdbcolid": 999}), mc.SETTINGS)   # v0.19.5 CO-D2: with no ID it would be the user's own
            check("B110e: Auto Repair plans the step 'collection' when TMDB lists another collection; never for a user-made set",
                  ("collection", mc._AR_LABELS["collection"]) in _plan_e
                  and ("collection", mc._AR_LABELS["collection"]) not in mc._auto_repair_plan(dict(_rows_e[0], coll_tmdb={"id": None, "when": 1},
                                                                                                   coll_nfo={"name": "Disney"}), mc.SETTINGS), _plan_e)
            _boxes.clear()
        finally:
            app._schedule_refresh = _osr_e
            mc.COLL_CACHE.clear(); mc.COLL_CACHE.update(_occ_e)
            shutil.rmtree(_de, ignore_errors=True)

        # ── v0.19.4 B110f + L4 follow-up: the preview's Run button sits in the button row ──  ### NEW v0.19.4 B110f ###
        _pv_f = on_ui(lambda: mc._PreviewRunDialog(app, "Preview test", "line", run_label="  ▶ Run it  "))
        try:
            _row_f = on_ui(lambda: [str(w.cget("text")).strip() for w in _pv_f._btn_row.winfo_children()])
        finally:
            on_ui(lambda: _pv_f.winfo_exists() and _pv_f.destroy())
        check("L4: the preview's Run button is in the bottom button row (right of Close)", _row_f[-2:] == ["Close", "▶ Run it"], _row_f)
        # ── v0.19.4 B110g: Create Collection Folders (fake TMDB, fake image writer, temp folders) ──  ### NEW v0.19.4 B110g ###
        _dgu = tempfile.mkdtemp(prefix="mc_b110g_ui_")
        os.makedirs(os.path.join(_dgu, "Kept Saga")); open(os.path.join(_dgu, "Kept Saga", "poster.jpg"), "wb").write(b"old")
        _rg = [{"movie_name": "M1", "subfolder": "M1", "subfolder_path": os.path.join(_dgu, "m1"), "coll_nfo": {"name": "Fake Saga: Part?"},
                "coll_tmdb": {"id": 55, "name": "Fake Saga", "when": 1}},
               {"movie_name": "M2", "subfolder": "M2", "subfolder_path": os.path.join(_dgu, "m2"), "coll_nfo": {"name": "Kept Saga"},
                "coll_tmdb": {"id": 66, "name": "Kept Saga", "when": 1}},
               {"movie_name": "M3", "subfolder": "M3", "subfolder_path": os.path.join(_dgu, "m3"), "coll_nfo": {"name": "My Own"}, "coll_tmdb": None}]
        _imgs_g = {"posters": [{"file_path": "/p.jpg", "iso_639_1": "en", "width": 10, "height": 15}],
                   "backdrops": [{"file_path": "/b.jpg", "iso_639_1": None, "width": 19, "height": 10}]}
        _saved_g, _refs_g = [], []
        _ofe_g, _osi_g, _onc_g = mc._tmdb_rate_limited_fetch, mc._save_image_from, mc._sc.note_created
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: _imgs_g
        mc._save_image_from = lambda src, dest: (_saved_g.append((src, dest)), open(dest, "wb").write(b"jpg"), (True, ""))[2]
        mc._sc.note_created = lambda root, name, ref, path, made=None, logger=None: (_onc_g(root, name, ref, path, made, logger), _refs_g.append(ref[0]))[0]
        _ok_g = mc.SETTINGS.get("tmdb_api_key", ""); mc.SETTINGS["tmdb_api_key"] = "fake-key"
        _osr_g = app._schedule_refresh; app._schedule_refresh = lambda *a, **k: None
        _orc_g = app._read_collection_folders; app._read_collection_folders = lambda then=None: None
        try:
            mc.COLL_FOLDERS.clear(); mc.COLL_FOLDERS.update(mc.read_collection_folders(_dgu, ["Fake Saga: Part?", "Kept Saga", "My Own"]))
            _items_g = mc.collection_folder_items(_rg, _dgu)
            app._coll_create_done = None; _boxes.clear()
            on_ui(lambda: app._create_collection_folders_for(list(_rg), preview=False, root=_dgu))
            wait_for(lambda: app._coll_create_done is not None, 15)
            _new_g = os.path.join(_dgu, "Fake Saga_ Part_")
            check("B110g: Create Collection Folders — the set folder (Kodi's legal name) with poster + fanart from TMDB; "
                  "an existing poster kept; a user-made set gets the folder only",
                  app._coll_create_done[0] == 3 and sorted(os.listdir(_new_g)) == ["fanart.jpg", "poster.jpg"]
                  and open(os.path.join(_dgu, "Kept Saga", "poster.jpg"), "rb").read() == b"old"
                  and os.path.isfile(os.path.join(_dgu, "Kept Saga", "fanart.jpg")) and os.path.isdir(os.path.join(_dgu, "My Own"))
                  and not os.listdir(os.path.join(_dgu, "My Own")), (app._coll_create_done, os.listdir(_dgu), _saved_g))
            _run_g = next((r for r in _refs_g if r), None)
            _undo_g = mc._sc.restore_backup_run(mc._BACKUP_ROOT, _run_g) if _run_g else ([], ["no run"], None)
            check("B119: Undo removes a folder made with no image (a user-made set)", not os.path.exists(os.path.join(_dgu, "My Own")), os.listdir(_dgu))   # NEW v0.19.5
            check("B110g: Undo removes the created images and the folder the run made; the old poster stays",
                  not os.path.exists(_new_g) and open(os.path.join(_dgu, "Kept Saga", "poster.jpg"), "rb").read() == b"old"
                  and not os.path.exists(os.path.join(_dgu, "Kept Saga", "fanart.jpg")), (_undo_g[:2], os.listdir(_dgu)))
            # ### NEW v0.19.5 B117 ### Replace off (kept), on (replaced\\ holds the old one), Undo
            _d117 = os.path.join(_dgu, "Rep Saga"); os.makedirs(_d117)
            open(os.path.join(_d117, "poster.png"), "wb").write(b"oldp"); open(os.path.join(_d117, "fanart.jpg"), "wb").write(b"oldf")
            _r117 = [{"movie_name": "M9", "subfolder": "M9", "subfolder_path": os.path.join(_dgu, "m9"), "coll_nfo": {"name": "Rep Saga"},
                      "coll_tmdb": {"id": 77, "name": "Rep Saga", "when": 1}}]
            mc.COLL_FOLDERS.clear(); mc.COLL_FOLDERS.update(mc.read_collection_folders(_dgu, ["Rep Saga"]))
            _pv117 = []
            def _go117(tick):
                def _start():
                    app._create_collection_folders_for(list(_r117), preview=True, root=_dgu)
                def _pick():
                    p = getattr(app, "_coll_folder_preview", None)
                    if p is None or p in _pv117 or not p.winfo_exists() or not hasattr(p, "_replace_var"):
                        return False
                    _pv117.append(p); p._replace_var.set(tick); p._run()
                    return True
                app.after(0, _start)
                wait_for(lambda: on_ui(_pick), 10)
            app._coll_create_done = None; _boxes.clear(); _nrefs117 = len(_refs_g)
            _go117(False); time.sleep(0.5)
            check("B117: the tick is off by default; off keeps the existing images (nothing to do, says so)",
                  open(os.path.join(_d117, "poster.png"), "rb").read() == b"oldp" and open(os.path.join(_d117, "fanart.jpg"), "rb").read() == b"oldf"
                  and sorted(os.listdir(_d117)) == ["fanart.jpg", "poster.png"] and any("Nothing was changed" in str(b) for b in _boxes), (os.listdir(_d117), _boxes))
            app._coll_create_done = None; _boxes.clear()
            _go117(True); wait_for(lambda: app._coll_create_done is not None, 15)
            _rd117 = os.path.join(_d117, "replaced")
            check("B117: on: the new poster and fanart are in place, the old ones are in replaced\\",
                  app._coll_create_done[0] == 1 and open(os.path.join(_d117, "poster.jpg"), "rb").read() == b"jpg" and open(os.path.join(_d117, "fanart.jpg"), "rb").read() == b"jpg"
                  and not os.path.exists(os.path.join(_d117, "poster.png")) and open(os.path.join(_rd117, "poster.png"), "rb").read() == b"oldp"
                  and open(os.path.join(_rd117, "fanart.jpg"), "rb").read() == b"oldf", (app._coll_create_done, os.listdir(_d117)))
            _run117 = next((r for r in _refs_g[_nrefs117:] if r), None)
            _undo117 = mc._sc.restore_backup_run(mc._BACKUP_ROOT, _run117) if _run117 else ([], ["no run"], None)
            check("B117: Undo puts the old images back, removes the new ones and replaced\\",
                  sorted(os.listdir(_d117)) == ["fanart.jpg", "poster.png"] and open(os.path.join(_d117, "poster.png"), "rb").read() == b"oldp"
                  and open(os.path.join(_d117, "fanart.jpg"), "rb").read() == b"oldf", (_undo117[:2], os.listdir(_d117)))
            mc.COLL_FOLDERS.clear(); mc.COLL_FOLDERS.update(mc.read_collection_folders(_dgu, ["Fake Saga: Part?", "Kept Saga", "My Own"]))   # after B117's own state
            _w_g = mc.compute_movie_health_detailed(dict(_rg[0], coll_nfo={"name": "Kept Saga"}),
                                                    dict(mc.SETTINGS["health_rules"], collection_artwork=True), dict(mc.SETTINGS, collection_folder=_dgu))
            check("B110g: rule collection_artwork — a missing fanart is a warning while a collection folder is set",
                  "Collection artwork: fanart missing" in _w_g[2], _w_g[2])
            _boxes.clear()
        finally:
            mc._tmdb_rate_limited_fetch, mc._save_image_from, mc._sc.note_created = _ofe_g, _osi_g, _onc_g
            mc.SETTINGS["tmdb_api_key"] = _ok_g; app._schedule_refresh = _osr_g; app._read_collection_folders = _orc_g
            mc.COLL_FOLDERS.clear()
            shutil.rmtree(_dgu, ignore_errors=True)

        # ── v0.19.4 review fix 2: folder path, no silent folder-only run, resize, Year column, panel, Collection Artwork ──
        _d2 = tempfile.mkdtemp(prefix="mc_fix2_")
        _it2 = mc.collection_folder_items([{"coll_nfo": {"name": "Greyhound Collection"}, "subfolder_path": "x"}], _d2.replace("\\", "/"))
        if sys.platform == "win32": check("fix 2e: the collection folder path has one kind of separator (askdirectory gives 'Z:/x')",
              "/" not in _it2[0]["dir"] and "/" not in mc.collection_folder_text(_it2) and "Collection Artwork…" in mc.collection_folder_text(_it2),
              _it2[0]["dir"])
        check("fix 2d: TMDB link — the collection page with the id, a TMDB collection search without it",
              mc.collection_tmdb_url(10, "x") == "https://www.themoviedb.org/collection/10"
              and mc.collection_tmdb_url(None, "Greyhound Collection") == "https://www.themoviedb.org/search/collection?query=Greyhound%20Collection"
              and mc.collection_tmdb_id([{"coll_nfo": {"name": "a", "tmdbcolid": 7}}, {"coll_tmdb": {"id": 9}}]) == 9, None)

        # f: a TMDB collection without a key / without a fanart is an error of the run, not a silent folder
        _rg2 = [{"movie_name": "N1", "subfolder": "N1", "subfolder_path": os.path.join(_d2, "n1"), "coll_nfo": {"name": "Key Saga"},
                 "coll_tmdb": {"id": 77, "name": "Key Saga", "when": 1}}]
        _ofe2, _osi2 = mc._tmdb_rate_limited_fetch, mc._save_image_from
        _ok2 = mc.SETTINGS.get("tmdb_api_key", "")
        _osr2 = app._schedule_refresh; app._schedule_refresh = lambda *a, **k: None
        _orc2 = app._read_collection_folders; app._read_collection_folders = lambda then=None: (then() if then else None)
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: {"posters": [{"file_path": "/p.jpg", "iso_639_1": "en", "width": 10, "height": 15}], "backdrops": []}
        mc._save_image_from = lambda src, dest: (open(dest, "wb").write(b"jpg"), (True, ""))[1]
        try:
            mc.COLL_FOLDERS.clear()
            mc.SETTINGS["tmdb_api_key"] = ""
            app._coll_create_done = None; _boxes.clear()
            on_ui(lambda: app._create_collection_folders_for(list(_rg2), preview=False, root=_d2))
            wait_for(lambda: app._coll_create_done is not None, 15)
            _e2a = list(app._coll_create_done[1])
            mc.SETTINGS["tmdb_api_key"] = "fake-key"
            shutil.rmtree(os.path.join(_d2, "Key Saga"), ignore_errors=True)
            app._coll_create_done = None
            on_ui(lambda: app._create_collection_folders_for(list(_rg2), preview=False, root=_d2))
            wait_for(lambda: app._coll_create_done is not None, 15)
            _e2b = list(app._coll_create_done[1])
            check("fix 2f: Create Collection Folder — no API key, or no fanart on TMDB, is listed as not done (no silent folder-only run)",
                  any("no TMDB API key" in e for e in _e2a) and any("TMDB has no fanart" in e for e in _e2b)
                  and os.path.isfile(os.path.join(_d2, "Key Saga", "poster.jpg")), (_e2a, _e2b))
        finally:
            mc._tmdb_rate_limited_fetch, mc._save_image_from = _ofe2, _osi2
            mc.SETTINGS["tmdb_api_key"] = _ok2
            _boxes.clear()

        # b: the drag returns "break" (Tk's own resize would move the neighbour after it) and changes one column only
        def _drag2():
            cols = list(app.tree["columns"])
            snap = {c: app.tree.column(c, "width") for c in cols}
            app._col_resize_state = {"col": "year", "start_x": 100, "start_w": snap["year"], "snapshot": snap, "all_cols": cols}
            ev = type("E", (), {"x": 140, "y": 5})()
            r1 = app._col_resize_drag(ev)
            mid = {c: app.tree.column(c, "width") for c in cols}
            r2 = app._col_resize_end(ev)
            after = {c: app.tree.column(c, "width") for c in cols}
            app.tree.column("year", width=snap["year"])
            return r1, r2, snap, mid, after, app._col_resize_just_ended
        _r1, _r2, _snap2, _mid2, _aft2, _je2 = on_ui(_drag2)
        check("fix 2b: a column drag returns 'break' (no fight with Tk's own resize) and only the dragged column changes",
              _r1 == "break" and _r2 == "break" and _aft2["year"] == _snap2["year"] + 40 and _mid2["year"] == _snap2["year"] + 40
              and all(_aft2[c] == _snap2[c] for c in _snap2 if c != "year") and not _je2, (_r1, _r2, _snap2.get("year"), _aft2.get("year")))
        _st2 = on_ui(lambda: (setattr(app, "_col_resize_state", {"x": 1}),
                              app._col_resize_start(type("E", (), {"x": 2, "y": 2})()), app._col_resize_state)[2])
        check("fix 2b: a press outside a heading edge starts no resize", _st2 == {}, _st2)

        # a / c: the Year column in the grouped view; Default Widths
        _gw2 = mc.SETTINGS.get("group_by_collection")
        try:
            on_ui(lambda: (app._group_var.set(False), app._toggle_grouping()))
            on_ui(lambda: app.tree.column("year", width=mc.px(52)))
            on_ui(lambda: (app._group_var.set(True), app._toggle_grouping()))
            _wg2 = on_ui(lambda: int(app.tree.column("year", "width")))
            _fit2 = on_ui(app._year_fit_width)
            on_ui(lambda: (app._group_var.set(False), app._toggle_grouping()))
            _wu2 = on_ui(lambda: int(app.tree.column("year", "width")))
            check("fix 2a: grouping widens the Year column for '1979–1986'; ungrouping gives the old width back",
                  _wg2 >= _fit2 > mc.px(52) and _wu2 == mc.px(52), (_wg2, _fit2, _wu2))
            on_ui(lambda: [app.tree.column(c, width=333) for c in app.tree["columns"]])
            on_ui(app._default_col_widths)
            _dw2 = on_ui(lambda: {c["id"]: int(app.tree.column(c["id"], "width")) for c in mc.COLUMN_MODEL})
            check("fix 2c: ↺ Default Widths puts every column back to its model width (Auto-size label without the ⟺ box glyph)",
                  all(_dw2[c["id"]] == mc.px(c["width"]) for c in mc.COLUMN_MODEL)
                  and "⟺" not in app._autosize_btn.cget("text") and "Default Widths" in app._defwidth_btn.cget("text"),
                  {k: v for k, v in _dw2.items() if v != mc.px(next(c["width"] for c in mc.COLUMN_MODEL if c["id"] == k))})
        finally:
            on_ui(lambda: (app._group_var.set(bool(_gw2)), app._toggle_grouping()))

        # d: the collection panel shows the set poster; Open Fanart greyed without a fanart; TMDB always
        _cd2 = os.path.join(_d2, "Panel Saga"); os.makedirs(_cd2, exist_ok=True)
        if mc._PIL_AVAILABLE:
            mc._PILImage.new("RGB", (200, 300), (200, 40, 40)).save(os.path.join(_cd2, "poster.jpg"))
        else:
            open(os.path.join(_cd2, "poster.jpg"), "wb").write(b"x")
        _pk2 = mc._cr.norm_name("Panel Saga")
        mc.COLL_FOLDERS.clear(); mc.COLL_FOLDERS.update({_pk2: {"dir": _cd2, "art": {"poster": "poster.jpg"}, "near": None, "near_name": None, "legal": "Panel Saga"}})
        _pr2 = [{"movie_name": "P1", "subfolder": "P1", "subfolder_path": os.path.join(_d2, "p1"), "coll_nfo": {"name": "Panel Saga"}, "health_status": "ok"}]
        try:
            on_ui(lambda: (setattr(app._movie_panel, "_ph", None), app._movie_panel.show_collection(_pk2, "Panel Saga", list(_pr2))))
            wait_for(lambda: app._movie_panel._ph is not None or not mc._PIL_AVAILABLE, 10)
            _bt2 = on_ui(lambda: {k: str(b.cget("state")) for k, b in app._movie_panel.coll_buttons.items()})
            check("fix 2d: the collection panel shows the set folder's poster; Open Poster on, Open Fanart greyed (none), TMDB and Artwork… on",
                  (app._movie_panel._ph is not None or not mc._PIL_AVAILABLE) and _bt2.get("🖼 Open Poster") == "normal"
                  and _bt2.get("🖼 Open Fanart") == "disabled" and _bt2.get("🌐 TMDB") == "normal" and _bt2.get("🖼 Artwork…") == "normal", _bt2)
        finally:
            mc.COLL_FOLDERS.clear()

        # g: Collection Artwork… — from the movies' own images, the folder made, an existing fanart replaced after a backup
        _ad2 = os.path.join(_d2, "art_lib")
        _arows = []
        for _i2, _nm2 in enumerate(("Grey One", "Grey Two")):
            _md2 = os.path.join(_ad2, _nm2); os.makedirs(_md2, exist_ok=True)
            _pp2, _fp2 = os.path.join(_md2, "poster.jpg"), os.path.join(_md2, "fanart.jpg")
            if mc._PIL_AVAILABLE:
                mc._PILImage.new("RGB", (100, 150), (10 * _i2, 90, 90)).save(_pp2)
                mc._PILImage.new("RGB", (192, 108), (90, 10 * _i2, 90)).save(_fp2)
            else:
                open(_pp2, "wb").write(b"p"); open(_fp2, "wb").write(b"f")
            _arows.append({"movie_name": _nm2, "subfolder": _nm2, "subfolder_path": _md2, "coll_nfo": {"name": "Greyhound Collection"},
                           "poster_exists": True, "poster_path": _pp2, "fanart_exists": True, "fanart_path": _fp2, "health_status": "warning"})
        _root2 = os.path.join(_d2, "sets"); os.makedirs(os.path.join(_root2, "Greyhound Collection"), exist_ok=True)
        open(os.path.join(_root2, "Greyhound Collection", "fanart.jpg"), "wb").write(b"OLD")
        _ocf2 = mc.SETTINGS.get("collection_folder"); mc.SETTINGS["collection_folder"] = _root2.replace("\\", "/")
        _oask2 = mc.messagebox.askyesno; mc.messagebox.askyesno = lambda *a, **k: (_boxes.append(("ask", a[:2])), True)[1]
        _osi3 = mc._save_image_from
        _refs2 = []
        _onc2 = mc._sc.note_created
        mc._sc.note_created = lambda root, name, ref, path, made=None, logger=None: (_onc2(root, name, ref, path, made, logger), _refs2.append(ref[0]))[0]
        _dlg2 = None
        try:
            mc.SETTINGS["tmdb_api_key"] = ""
            _boxes.clear()
            _dlg2 = on_ui(lambda: app._collection_art_for(mc._cr.norm_name("Greyhound Collection"), "Greyhound Collection", list(_arows)))
            wait_for(lambda: _dlg2 is not None and _dlg2.loaded is not None, 20)
            _ld2 = _dlg2.loaded if _dlg2 else None
            def _pick2():
                (e_p, c_p), (e_f, c_f) = _dlg2._cells["poster"][1], _dlg2._cells["fanart"][0]
                _dlg2._pick("poster", e_p, c_p); _dlg2._pick("fanart", e_f, c_f)
                return str(_dlg2._save_btn.cget("state")), _dlg2._pick_lbl.cget("text"), e_p["url"], e_f["url"]
            _ps2 = on_ui(_pick2)
            on_ui(_dlg2._save)
            wait_for(lambda: _dlg2.saved is not None, 20)
            _gd2 = os.path.join(_root2, "Greyhound Collection")
            _new_f2 = open(os.path.join(_gd2, "fanart.jpg"), "rb").read()
            check("fix 2g: Collection Artwork… without a TMDB key shows the movies' own images (2 posters, 2 fanart)",
                  _ld2 == ("movies", 2, 2), _ld2)
            check("fix 2g: one poster and one fanart picked → Save to Folder writes poster.jpg and replaces fanart.jpg (asked first)",
                  _ps2[0] == "normal" and _dlg2.saved[0] == 1 and not _dlg2.saved[1]
                  and open(os.path.join(_gd2, "poster.jpg"), "rb").read() == open(_ps2[2], "rb").read()
                  and _new_f2 == open(_ps2[3], "rb").read() and _new_f2 != b"OLD"
                  and any(b[0] == "ask" and "fanart.jpg" in str(b[1]) for b in _boxes), (_ps2, _dlg2.saved, _boxes[:3]))
            _run2 = next((r for r in _refs2 if r), None)
            _undo2 = mc._sc.restore_backup_run(mc._BACKUP_ROOT, _run2) if _run2 else ([], ["no run"], None)
            check("fix 2g: Undo of that run removes the new poster and puts the old fanart back",
                  not os.path.exists(os.path.join(_gd2, "poster.jpg")) and open(os.path.join(_gd2, "fanart.jpg"), "rb").read() == b"OLD",
                  (_undo2[:2], os.listdir(_gd2)))
            _fx2 = on_ui(lambda: app._ctx_fix_action("collection_art", list(_arows))[0])
            check("fix 2g: Fix on 'Collection artwork: … missing' for one collection opens Collection Artwork…",
                  _fx2 is not None and "_collection_art_for" in (getattr(_fx2, "__code__", None) and _fx2.__code__.co_names or ()), _fx2)
        finally:
            mc._sc.note_created = _onc2
            mc._save_image_from = _osi3
            mc.messagebox.askyesno = _oask2
            mc.SETTINGS["collection_folder"] = _ocf2; mc.SETTINGS["tmdb_api_key"] = _ok2
            app._schedule_refresh = _osr2; app._read_collection_folders = _orc2
            try:
                if _dlg2 is not None and on_ui(lambda: bool(_dlg2.winfo_exists())):
                    on_ui(_dlg2.destroy)
            except Exception:
                pass
            mc.COLL_FOLDERS.clear()
            _boxes.clear()
            shutil.rmtree(_d2, ignore_errors=True)

        # ── v0.19.4 review fix 3: not in a collection, gone collections, Update regroups, Set Collection with TMDB ──
        _d3 = tempfile.mkdtemp(prefix="mc_fix3_")
        _onc3 = {k: (set(v) if isinstance(v, set) else list(v)) for k, v in mc.NO_COLL.items()}
        _ok3 = mc.SETTINGS.get("tmdb_api_key", ""); _ocf3 = mc.SETTINGS.get("collection_folder")
        _osr3 = app._schedule_refresh; _ocs3 = app._confirm_services
        _gw3 = mc.SETTINGS.get("group_by_collection")
        _save3 = (list(app._results), dict(mc.COLL_CACHE))
        try:
            # rules (pure)
            _tm3 = {"id": 9, "name": "Saga", "when": 1}
            check("fix 3b: a movie marked 'not in a collection' without a <set> gets no TMDB suggestion; Fix skips it",
                  mc._cr.mismatch_reasons({"coll_nfo": None, "coll_tmdb": _tm3, "coll_none": True}) == []
                  and mc._cr.mismatch_reasons({"coll_nfo": None, "coll_tmdb": _tm3})
                  and mc._cr.fix_target({"coll_nfo": None, "coll_tmdb": _tm3, "coll_none": True}, {})[3] == "you marked it as not in a collection", None)
            _g3 = mc._cr.mismatch_reasons({"coll_nfo": {"name": "Ghost Saga", "tmdbcolid": 999}, "coll_tmdb": {"id": None, "gone": 999, "when": 1}})
            _n3 = mc._cr.mismatch_reasons({"coll_nfo": {"name": "Ghost Saga", "tmdbcolid": 999}, "coll_tmdb": {"id": None, "when": 1}})
            _o3 = mc._cr.mismatch_reasons({"coll_nfo": {"name": "Disney"}, "coll_tmdb": {"id": None, "when": 1}})
            check("fix 3c: an NFO linking a TMDB collection that is gone / not listed for the movie is a warning; your own set is not",
                  _g3 == ["Collection: 'Ghost Saga' (TMDB 999) no longer exists on TMDB"]
                  and _n3 == ["Collection: 'Ghost Saga' (TMDB 999) is not listed by TMDB for this movie"] and _o3 == []
                  and "collection_gone" in mc._fix_issue_keys({"health_reasons": _g3, "health_status": "warning"}), (_g3, _n3, _o3))

            # the mark is a file in the settings folder; it counts only while the NFO has no <set>
            _rm3 = {"movie_name": "Free Guy", "subfolder": "Free Guy (2021)", "subfolder_path": os.path.join(_d3, "Free Guy (2021)"),
                    "source_tmdb_val": "550988", "coll_nfo": None, "coll_tmdb": {"id": 9, "name": "Saga", "when": time.time()}}
            mc.no_collection_set([_rm3], True)
            _f3 = mc._sc.NO_COLL_PATH
            _in_cfg3 = os.path.normcase(os.path.dirname(_f3)) == os.path.normcase(mc._sc.get_config_dir())
            _m3a = mc.mark_coll_none(dict(_rm3)).get("coll_none")
            _m3b = mc.mark_coll_none(dict(_rm3, coll_nfo={"name": "Saga"})).get("coll_none")
            _m3c = mc.mark_coll_none(dict(_rm3, subfolder_path=os.path.join(_d3, "moved"))).get("coll_none")
            _w3 = mc.compute_movie_health_detailed(dict(_rm3), mc.SETTINGS["health_rules"], mc.SETTINGS)[2]
            check("fix 3b: no_collection.json in the settings folder; the mark follows the TMDB id; ignored while the NFO has a <set>",
                  os.path.isfile(_f3) and _in_cfg3 and _m3a is True and _m3b is None and _m3c is True
                  and not any(w.startswith("Collection:") for w in _w3), (_f3, _m3a, _m3b, _m3c, _w3))
            mc.no_collection_set([_rm3], False)
            check("fix 3b: Set Collection… (no_collection_set False) takes the mark away",
                  not mc.no_collection_marked(_rm3) and "550988" not in open(_f3, encoding="utf-8").read(), None)

            # Remove from Collection… on a movie without a <set> that TMDB puts in a collection: marked, nothing written
            _pf3 = os.path.join(_d3, "Free Guy (2021)"); os.makedirs(_pf3)
            open(os.path.join(_pf3, "Free Guy (2021).nfo"), "w", encoding="utf-8").write("<movie>\n  <title>Free Guy</title>\n</movie>\n")
            _rm3.update(nfo_exists=True, nfo_path=os.path.join(_pf3, "Free Guy (2021).nfo"))
            _b3 = open(_rm3["nfo_path"], "rb").read()
            app._coll_write_done = None; _boxes.clear()
            on_ui(lambda: app._remove_collection_for([_rm3], ask=False))
            wait_for(lambda: app._coll_write_done is not None, 10)
            check("fix 3b: Remove from Collection… on a movie TMDB puts in a collection (no <set>): marked, the NFO unchanged",
                  app._coll_write_done == (0, []) and mc.no_collection_marked(_rm3) and open(_rm3["nfo_path"], "rb").read() == _b3
                  and any("marked as not in a collection" in str(b) for b in _boxes), (app._coll_write_done, _boxes[-1:]))
            mc.no_collection_set([_rm3], False)

            # gone collection during Check Collections Online
            import urllib.error as _ue3
            _rg3 = {"movie_name": "Ghost", "subfolder": "Ghost", "subfolder_path": os.path.join(_d3, "Ghost"), "source_tmdb_val": "901",
                    "nfo_exists": True, "coll_nfo": {"name": "Ghost Saga", "tmdbcolid": 999}, "coll_tmdb": None, "id_check": None}

            def _fake3(url):
                if "/collection/" in url:
                    raise _ue3.HTTPError(url, 404, "Not Found", {}, None)
                return {"id": 901, "title": "Ghost", "belongs_to_collection": {"id": 999, "name": "Ghost Saga"}}
            mc.SETTINGS["tmdb_api_key"] = "fake-key"; app._confirm_services = lambda s: True
            app._coll_check_done = None; _boxes.clear()
            on_ui(lambda: app._check_collections([_rg3], fetch=_fake3))
            wait_for(lambda: app._coll_check_done is not None, 15)
            _wg3 = mc.compute_movie_health_detailed(dict(_rg3), mc.SETTINGS["health_rules"], mc.SETTINGS)[2]
            check("fix 3c: Check Collections Online — a collection page that is gone (404) is stored as 'gone', not 'movie not on TMDB'",
                  (_rg3.get("coll_tmdb") or {}).get("gone") == 999 and (_rg3.get("coll_tmdb") or {}).get("id") is None
                  and "Collection: 'Ghost Saga' (TMDB 999) no longer exists on TMDB" in _wg3
                  and (app._coll_check_done or (0, 0, {}))[2].get("collection no longer on TMDB") == 1, (_rg3.get("coll_tmdb"), _wg3, app._coll_check_done))
            _boxes.clear()

            # Update (no FFprobe) after the <set> was removed by hand: the online data stays, the movie leaves the group
            _lu3 = os.path.join(_d3, "LibUpd")
            _ru3 = []
            for _nm3 in ("Upd One (2001)", "Upd Two (2003)"):
                _p3 = os.path.join(_lu3, _nm3); os.makedirs(_p3)
                open(os.path.join(_p3, _nm3 + ".mkv"), "wb").write(b"\0" * 64)
                open(os.path.join(_p3, _nm3 + ".nfo"), "w", encoding="utf-8").write(
                    f"<movie>\n  <title>{_nm3[:-7]}</title>\n  <set>\n    <name>Upd Saga</name>\n  </set>\n</movie>\n")
                _rr3 = mc.scan_one_subfolder(_p3, _nm3, use_ffprobe=False)
                _rr3["library_root"] = _lu3; _rr3["coll_tmdb"] = {"id": 77, "name": "Upd Saga", "when": time.time()}
                _ru3.append(_rr3)
            mc.COLL_CACHE["77"] = {"names": {"en": "Upd Saga"}, "overviews": {}}
            on_ui(lambda: (setattr(app, "_results", list(_ru3)), mc.finalize_results(app._results),
                           app._group_var.set(True), app._toggle_grouping()))
            wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)
            _par3 = on_ui(lambda: {app._item_map[i]["subfolder"]: app.tree.parent(i) for i in app._item_map})
            open(_ru3[0]["nfo_path"], "w", encoding="utf-8").write("<movie>\n  <title>Upd One</title>\n</movie>\n")
            _rg_n3 = getattr(app, "_regrouped", 0)
            _iid3 = on_ui(lambda: next(i for i, r in app._item_map.items() if r["subfolder"] == "Upd One (2001)"))
            on_ui(lambda: app._reval_no_ffmpeg(_iid3, app._item_map[_iid3]))
            wait_for(lambda: getattr(app, "_regrouped", 0) > _rg_n3 and not getattr(app, "_tbl_filling", False), 10)
            _par3b = on_ui(lambda: {app._item_map[i]["subfolder"]: app.tree.parent(i) for i in app._item_map})
            _row3 = next(r for r in app._results if r["subfolder"] == "Upd One (2001)")
            check("fix 3a: Update after removing the <set> by hand — the movie leaves its collection row; the online data stays (warning)",
                  _par3.get("Upd One (2001)") and _par3.get("Upd Two (2003)") and _par3b.get("Upd One (2001)") == ""
                  and _par3b.get("Upd Two (2003)") and (_row3.get("coll_tmdb") or {}).get("id") == 77
                  and any(w.startswith("Collection: missing") for w in (_row3.get("health_reasons") or [])),
                  (_par3, _par3b, _row3.get("coll_tmdb"), _row3.get("health_reasons")))

            # Set Collection… dialog: TMDB search → a TMDB collection (id + name)
            mc.SETTINGS["tmdb_api_key"] = "fake-key"
            _ofe3 = mc._tmdb_rate_limited_fetch
            _urls13 = []
            mc._tmdb_rate_limited_fetch = lambda url, timeout=15: (_urls13.append(url), {"results": [{"id": 321, "name": "Ghost Collection"}]} if "/search/collection" in url else {})[1]
            try:
                _sd3 = on_ui(lambda: mc._SetCollectionDialog(app, ["Upd Saga"], "ghost", api_key="fake-key", lang="en-US", n_movies=2))
                on_ui(lambda: _sd3.search())
                wait_for(lambda: getattr(_sd3, "searched", None) is not None, 10)
                on_ui(_sd3._ok)
                check("fix 3d: Set Collection… — Search TMDB finds the collection; Set gives (TMDB name, id, folder tick)",
                      _sd3.result == ("Ghost Collection", 321, "Ghost Collection", True), _sd3.result)
                check("fix 13: Set Collection… searches TMDB in English (not the library language)",
                      any("/search/collection" in u and "language=en-US" in u for u in _urls13)
                      and not any("language=pt" in u for u in _urls13), _urls13)
            finally:
                mc._tmdb_rate_limited_fetch = _ofe3
                try:
                    if on_ui(lambda: bool(_sd3.winfo_exists())):
                        on_ui(_sd3.destroy)
                except Exception:
                    pass

            # Set Collection… with a TMDB id and the tick: NFO written with the id, the folder made, Collection Artwork… opens
            _root3 = os.path.join(_d3, "sets"); os.makedirs(_root3)
            mc.SETTINGS["collection_folder"] = _root3; mc.SETTINGS["tmdb_api_key"] = ""
            app._schedule_refresh = lambda *a, **k: None
            mc.no_collection_set([_ru3[1]], True)
            app._coll_write_done = None; app._coll_art_dialog = None; _boxes.clear()
            on_ui(lambda: app._set_collection_for([_ru3[1]], name="Ghost Collection", tmdb_id=321, folder=True))
            wait_for(lambda: app._coll_art_dialog is not None, 20)
            _ad3 = app._coll_art_dialog
            _t3 = open(_ru3[1]["nfo_path"], encoding="utf-8").read()
            check("fix 3d: Set Collection… with a TMDB collection — <set tmdbcolid> in the NFO, the mark cleared, the folder made, Collection Artwork… opens",
                  '<set tmdbcolid="321">' in _t3 and "<name>Ghost Collection</name>" in _t3 and not mc.no_collection_marked(_ru3[1])
                  and os.path.isdir(os.path.join(_root3, "Ghost Collection")) and _ad3 is not None and _ad3._tmdb == 321,
                  (_t3, os.listdir(_root3), getattr(_ad3, "_tmdb", None)))
            try:
                if _ad3 is not None and on_ui(lambda: bool(_ad3.winfo_exists())):
                    on_ui(_ad3.destroy)
            except Exception:
                pass
            _boxes.clear()
        finally:
            app._schedule_refresh = _osr3; app._confirm_services = _ocs3
            mc.SETTINGS["tmdb_api_key"] = _ok3; mc.SETTINGS["collection_folder"] = _ocf3
            mc.no_collection_load(_onc3["movies"]); mc._sc.save_no_collection(_onc3["movies"])
            mc.COLL_CACHE.clear(); mc.COLL_CACHE.update(_save3[1])
            mc.COLL_FOLDERS.clear()
            def _back3():
                app._results = _save3[0]
                mc.SETTINGS["group_by_collection"] = _gw3; app._group_var.set(bool(_gw3))
                mc.finalize_results(app._results); app._refresh_table(); app._incremental_save(app._results)
            on_ui(_back3)
            wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)
            _boxes.clear()
            shutil.rmtree(_d3, ignore_errors=True)

        # ── v0.19.4 review fix 4: Collection Artwork with a big TMDB collection (fake TMDB, slow previews) ──
        _d4 = tempfile.mkdtemp(prefix="mc_fix4_")
        _ofe4, _odp4 = mc._tmdb_rate_limited_fetch, mc._download_preview
        _ok4, _ocf4 = mc.SETTINGS.get("tmdb_api_key", ""), mc.SETTINGS.get("collection_folder")
        _big4 = {"posters": [{"file_path": f"/p{i}.jpg", "iso_639_1": "en", "width": 1000, "height": 1500} for i in range(40)],
                 "backdrops": [{"file_path": f"/b{i}.jpg", "iso_639_1": None, "width": 1920, "height": 1080} for i in range(30)]}
        _png4 = io.BytesIO()
        if mc._PIL_AVAILABLE:
            mc._PILImage.new("RGB", (60, 90), (50, 50, 200)).save(_png4, "PNG")
        _calls4 = []

        def _slow4(entry):
            _calls4.append(time.time()); time.sleep(0.3)
            return _png4.getvalue() or None
        mc._tmdb_rate_limited_fetch = lambda url, timeout=15: _big4
        mc._download_preview = _slow4
        mc.SETTINGS["tmdb_api_key"] = "fake-key"; mc.SETTINGS["collection_folder"] = _d4
        _dl4 = None
        try:
            _t04 = time.time()
            _dl4 = on_ui(lambda: app._collection_art_for(mc._cr.norm_name("Planet Saga"), "Planet Saga",
                                                          [{"movie_name": "P", "subfolder": "P", "subfolder_path": _d4,
                                                            "coll_nfo": {"name": "Planet Saga", "tmdbcolid": 173710}}]))
            wait_for(lambda: _dl4.loaded is not None, 10)
            _tl4 = time.time() - _t04
            _early4 = on_ui(lambda: (len(_dl4._cells["poster"]), len(_dl4._cells["fanart"]), _dl4._status.cget("text")))
            wait_for(lambda: _dl4.previews_done, 60)
            _td4 = time.time() - _t04
            check("fix 4 / 16: a big TMDB collection — the whole list, the first page at once (12 posters, 9 fanart), "
                  "its previews fill in 6 at a time",
                  _dl4.loaded == ("tmdb", 40, 30) and _tl4 < 3 and _early4[:2] == (12, 9) and "loading the previews" in _early4[2]
                  and _dl4.previews_done and _td4 < 0.3 * 21 * 0.6 and "Click one poster" in _dl4._status.cget("text"),
                  (_dl4.loaded, round(_tl4, 2), round(_td4, 2), _early4[2][:80]))
            # fix 16: pick a poster, Next › → the next 12 posters load; ‹ Previous → the pick is still there
            on_ui(lambda: _dl4._pick("poster", *_dl4._cells["poster"][2]))
            _n0 = len(_calls4)
            on_ui(lambda: _dl4._next("poster", 1))
            wait_for(lambda: _dl4.previews_done, 30)
            _pg16 = on_ui(lambda: ([e["file_path"] for e, _c in _dl4._cells["poster"]], _dl4._sec["poster"]["lbl"].cget("text"),
                                   str(_dl4._sec["poster"]["prev"].cget("state"))))
            _new16 = len(_calls4) - _n0
            on_ui(lambda: _dl4._next("poster", -1))
            _back16 = on_ui(lambda: (str(_dl4._cells["poster"][2][1].cget("highlightbackground")), len(_calls4) - _n0,
                                     _dl4._choice["poster"] is _dl4._cells["poster"][2][0]))
            on_ui(lambda: [_dl4._next("fanart", 1) for _ in range(5)])
            _fl16 = on_ui(lambda: (_dl4._sec["fanart"]["lbl"].cget("text"), str(_dl4._sec["fanart"]["next"].cget("state")),
                                   len(_dl4._cells["fanart"])))
            check("fix 16: Next › shows posters 13–24 (page 2 of 4) and loads only their previews; ‹ Previous brings page 1 "
                  "back from the cache with the chosen poster still marked; the last fanart page (4 of 4) has 3 and no Next",
                  _pg16[0] == [f"/p{i}.jpg" for i in range(12, 24)] and _pg16[1] == "Page 2 of 4" and _pg16[2] == "normal"
                  and _new16 == 12 and _back16[1] == 12 and _back16[2] and _back16[0] == mc.C_OK
                  and _fl16 == ("Page 4 of 4", "disabled", 3), (_pg16, _new16, _back16, _fl16))
            # fix 16: the window keeps the size the user gives it
            on_ui(lambda: _dl4.geometry("1001x701"))
            wait_for(lambda: str((mc.SETTINGS.get("window_geometry") or {}).get("CollectionArtDialog", {}).get("geometry", "")).startswith("1001x701"), 5)
            check("fix 16: Collection Artwork remembers its size (window_geometry)",
                  str((mc.SETTINGS.get("window_geometry") or {}).get("CollectionArtDialog", {}).get("geometry", "")).startswith("1001x701"),
                  (mc.SETTINGS.get("window_geometry") or {}).get("CollectionArtDialog"))
        finally:
            mc._tmdb_rate_limited_fetch, mc._download_preview = _ofe4, _odp4
            mc.SETTINGS["tmdb_api_key"] = _ok4; mc.SETTINGS["collection_folder"] = _ocf4
            try:
                if _dl4 is not None and on_ui(lambda: bool(_dl4.winfo_exists())):
                    on_ui(_dl4.destroy)
            except Exception:
                pass
            _boxes.clear()
            shutil.rmtree(_d4, ignore_errors=True)

        # ── v0.19.4 review fix 9: English name unless most local titles are in another language ──
        _qc9 = {"10": {"names": {"en": "Saga Collection", "pt": "Saga - Coleção", "es": "Saga - Colección"},
                       "overviews": {"en": "ov en", "pt": "ov pt"}}}
        _qtt9 = {"en": "The Saga", "pt": "A Saga Brasileira", "es": "La Saga", "fr": "The Saga"}

        def _qrows9(spec):
            return [{"coll_tmdb": {"id": 10}, "nfo_title": nt, "xml_localtitle": xt, "tmdb_titles": dict(_qtt9),
                     "title_langs": [], "coll_nfo": None} for nt, xt in spec]
        # English titles (one also French) and one Portuguese title, library PT → English
        _qa9 = _cr.chosen_names(_qrows9([("The Saga", ""), ("The Saga", ""), ("A Saga Brasileira", "")]), _qc9, "pt-BR")
        # most titles Portuguese → Portuguese
        _qb9 = _cr.chosen_names(_qrows9([("A Saga Brasileira", ""), ("a saga brasileira!", ""), ("The Saga", "")]), _qc9, "en-US")
        # a tie → English; unknown titles count as English
        _qd9 = _cr.chosen_names(_qrows9([("A Saga Brasileira", ""), ("The Saga", "")]), _qc9, "pt-BR")
        _qe9 = _cr.chosen_names(_qrows9([("A Saga Brasileira", ""), ("Minha Saga", ""), ("Outra", "")]), _qc9, "pt-BR")
        # the NFO wins over the XML; the XML counts when the NFO has no title
        _qf9 = _cr.chosen_names(_qrows9([("A Saga Brasileira", "The Saga"), ("", "A Saga Brasileira")]), _qc9, "en-US")
        # title_langs from the check count only when computed from the same local title (coll_tmdb "tl")
        _qg = _qrows9([("Saga BR", ""), ("Saga BR", "")])
        for _qx9 in _qg:
            _qx9["title_langs"] = ["pt"]; _qx9["coll_tmdb"]["tl"] = _cr.loose_title("Saga BR")
        _qg9 = _cr.chosen_names(_qg, _qc9, "en-US")
        for _qx9 in _qg:
            _qx9["nfo_title"] = "Renamed"
        _qg9b = _cr.chosen_names(_qg, _qc9, "en-US")
        check("fix 9: a collection's one name is English unless most local titles (NFO first, else XML) are in another language",
              _qa9[10][:3] == ("Saga Collection", "ov en", "en") and _qb9[10][2] == "pt" and _qb9[10][1] == "ov pt"
              and _qd9[10][2] == "en" and _qe9[10][2] == "en" and _qf9[10][2] == "pt"
              and _qg9[10][2] == "pt" and _qg9b[10][2] == "en", (_qa9, _qb9, _qd9, _qe9, _qf9, _qg9, _qg9b))
        # the Fix writes the English name, then it is already right (no warning, no new Fix)
        _qh9 = _qrows9([("The Saga", ""), ("The Saga", ""), ("A Saga Brasileira", "")])
        for _qx9 in _qh9:
            _qx9["coll_tmdb"]["name"] = "Saga - Coleção"; _qx9["coll_nfo"] = {"name": "Saga - Coleção", "tmdbcolid": 10}
        _qch9 = _cr.chosen_names(_qh9, _qc9, "pt-BR")
        _qt9 = [_cr.fix_target(_qx9, _qc9, "pt-BR", _qch9)[0] for _qx9 in _qh9]
        for _qx9 in _qh9:
            _qx9["coll_nfo"] = {"name": "Saga Collection", "tmdbcolid": 10}
        _qch9b = _cr.chosen_names(_qh9, _qc9, "pt-BR")
        _qagain9 = [_cr.fix_target(_qx9, _qc9, "pt-BR", _qch9b)[3] for _qx9 in _qh9]
        _qwarn9 = [_cr.mismatch_reasons(_qx9, _qc9, None, _qch9b) for _qx9 in _qh9]
        check("fix 9: Fix writes the English name to every movie, then it is already right (no warning, no new Fix)",
              _qt9 == ["Saga Collection"] * 3 and _qagain9 == ["already right"] * 3
              and _qwarn9 == [[], [], []], (_qt9, _qagain9, _qwarn9))

        # ── v0.19.4 review fix 10: no English name in the cache (TMDB's empty original-language entry) ──
        _qc10 = {"468552": {"names": {"pt": "Mulher-Maravilha: Coleção", "fr": "Wonder Woman - Saga"}, "overviews": {}}}
        _qtt10 = {"en": "Wonder Woman", "pt": "Mulher-Maravilha", "fr": "Wonder Woman"}

        def _qrows10(nm):
            return [{"coll_tmdb": {"id": 468552, "name": "Mulher-Maravilha: Coleção"}, "nfo_title": t, "tmdb_titles": dict(_qtt10),
                     "coll_nfo": {"name": nm, "tmdbcolid": 468552}} for t in ("Wonder Woman", "Wonder Woman")]
        _qa10 = _qrows10("Wonder Woman Collection")
        _qch10 = _cr.chosen_names(_qa10, _qc10, "pt-BR")
        _qw10 = [_cr.mismatch_reasons(r, _qc10, None, _qch10) for r in _qa10]
        _qf10 = [_cr.fix_target(r, _qc10, "pt-BR", _qch10)[3] for r in _qa10]
        _qb10 = _qrows10("Mulher-Maravilha: Coleção")
        _qchb10 = _cr.chosen_names(_qb10, _qc10, "pt-BR")
        _qwb10 = [_cr.mismatch_reasons(r, _qc10, None, _qchb10) for r in _qb10]
        _qfb10 = _cr.fix_target(_qb10[0], _qc10, "pt-BR", _qchb10)
        _qnc10 = _cr.fix_target(_qb10[0], _qc10, "pt-BR")          # without the chosen map: never the library language
        check("fix 10: English titles, no English name cached → the NFO's English name is kept (no warning, Fix: already right); "
              "a Portuguese NFO name is not confirmed and Fix asks for Check Collections Online",
              _qch10[468552][0] == "Wonder Woman Collection" and _qw10 == [[], []] and _qf10 == ["already right"] * 2
              and _qchb10[468552][0] is None and _qwb10 == [[], []] and _qfb10[0] is None
              and "Check Collections Online" in _qfb10[3] and _qnc10[0] != "Mulher-Maravilha: Coleção",
              (_qch10, _qw10, _qf10, _qchb10, _qwb10, _qfb10, _qnc10))

        # ── v0.19.4 review fix 11: Update rereads the NFO even when its time and size look unchanged ──
        _qd11 = tempfile.mkdtemp(prefix="mc_fix11_")
        try:
            _qp11 = os.path.join(_qd11, "Movie (2001)"); os.makedirs(_qp11)
            _qn11 = os.path.join(_qp11, "Movie (2001).nfo")

            def _qw11(nm):
                with open(_qn11, "w", encoding="utf-8", newline="\n") as _qf11:
                    _qf11.write(f"<movie>\n  <title>Movie</title>\n  <set>\n    <name>{nm}</name>\n  </set>\n</movie>\n")
            _qw11("Old Saga A"); _qst11 = os.stat(_qn11)
            _qa11 = (mc.scan_one_subfolder(_qp11, "Movie (2001)", use_ffprobe=False).get("coll_nfo") or {}).get("name")
            _qw11("New Saga B"); os.utime(_qn11, ns=(_qst11.st_atime_ns, _qst11.st_mtime_ns))   # same time, same size
            _qsame11 = mc._stat_key(_qn11) == (_qst11.st_mtime_ns, _qst11.st_size)
            _qb11 = (mc.scan_one_subfolder(_qp11, "Movie (2001)", use_ffprobe=False).get("coll_nfo") or {}).get("name")
            check("fix 11: Update rereads the NFO even when the edited file shows its old time and size (network drive)",
                  _qa11 == "Old Saga A" and _qsame11 and _qb11 == "New Saga B", (_qa11, _qsame11, _qb11))
        finally:
            shutil.rmtree(_qd11, ignore_errors=True)

        # ── v0.19.4 review fix 12: the panel's overview — the NFOs' first, else the chosen name's language ──
        _qs12 = (dict(mc.COLL_CACHE), dict(mc._COLL_CHOSEN))
        try:
            mc.COLL_CACHE["777"] = {"names": {"en": "X Collection", "pt": "X Coleção"}, "overviews": {"en": "ov en", "pt": "ov pt"}}
            mc._COLL_CHOSEN.clear(); mc._COLL_CHOSEN[777] = ("X Collection", "ov en", "en")
            _qr12 = [{"coll_nfo": {"name": "X Collection", "overview": "written ov"}}, {"coll_nfo": {"name": "X Collection"}}]
            _qa12 = mc.collection_overview(_qr12, 777)
            _qb12 = mc.collection_overview([{"coll_nfo": {"name": "X Collection"}}], 777)
            mc._COLL_CHOSEN.clear()
            _qc12 = mc.collection_overview([{"coll_nfo": {"name": "X Collection"}}], 777)
            check("fix 12: the collection panel's overview = the NFOs' <set> overview, else the chosen name's language, else English (never the library language)",
                  _qa12 == "written ov" and _qb12 == "ov en" and _qc12 == "ov en", (_qa12, _qb12, _qc12))
        finally:
            mc.COLL_CACHE.clear(); mc.COLL_CACHE.update(_qs12[0]); mc._COLL_CHOSEN.clear(); mc._COLL_CHOSEN.update(_qs12[1])

        # ── v0.19.4 review fix 13: Set Collection… writes the collection's one name, not the search result's ──
        _qs13 = dict(mc.COLL_CACHE)
        try:
            mc.COLL_CACHE["9090"] = {"names": {"en": "Nine Collection", "pt": "Nove - Coleção"}, "overviews": {}}
            _qtt13 = {"en": "Nine", "pt": "Nove"}
            _qen13 = [{"nfo_title": "Nine", "tmdb_titles": dict(_qtt13), "coll_tmdb": None}]
            _qpt13 = [{"nfo_title": "Nove", "tmdb_titles": dict(_qtt13), "coll_tmdb": None}]
            _qa13 = mc.set_collection_name("Nove - Coleção", "Nove - Coleção", 9090, _qen13, [], "pt-BR")
            _qb13 = mc.set_collection_name("Nine Collection", "Nine Collection", 9090, _qpt13, [], "en-US")
            _qc13 = mc.set_collection_name("My Nine", "Nine Collection", 9090, _qen13, [], "pt-BR")
            # a movie already in the library's collection counts too (2 English titles there, 1 Portuguese added)
            _qlib13 = [{"nfo_title": "Nine", "tmdb_titles": dict(_qtt13), "coll_tmdb": {"id": 9090}} for _ in range(2)]
            _qd13 = mc.set_collection_name("Nove - Coleção", "Nove - Coleção", 9090, _qpt13, _qlib13, "pt-BR")
            check("fix 13: Set Collection… with a TMDB result writes the collection's one name (English titles → English; "
                  "Portuguese titles → Portuguese; the library's movies count); a typed name is kept",
                  _qa13 == "Nine Collection" and _qb13 == "Nove - Coleção" and _qc13 == "My Nine" and _qd13 == "Nine Collection",
                  (_qa13, _qb13, _qc13, _qd13))
        finally:
            mc.COLL_CACHE.clear(); mc.COLL_CACHE.update(_qs13)

        # ── v0.19.4 review fix 15: a renamed collection takes its folder (images) along ──
        _qd15 = tempfile.mkdtemp(prefix="mc_fix15_")
        _qsv15 = (mc.SETTINGS.get("collection_folder"), list(app._results), dict(mc.COLL_FOLDERS),
                  mc.SETTINGS.get("library_folders"))
        try:
            def _qmk15(folder, files):
                for _qrel, _qdata in files.items():
                    _qp = os.path.join(_qd15, folder, _qrel); os.makedirs(os.path.dirname(_qp), exist_ok=True)
                    open(_qp, "wb").write(_qdata)

            def _qls15(folder):
                _qb = os.path.join(_qd15, folder)
                if not os.path.isdir(_qb):
                    return None
                return sorted(os.path.relpath(os.path.join(dp, f), _qb).replace("\\", "/") for dp, _dn, fn in os.walk(_qb) for f in fn)
            # A: both folders have a poster → the old one is kept, the new one goes to replaced\; Undo puts all back
            _qmk15("Coleção Alien", {"poster.jpg": b"OLDPOSTER", "fanart.jpg": b"OLDFANART", "extrafanart/x.jpg": b"X"})
            _qmk15("Alien Collection", {"poster.png": b"NEWPOSTER"})
            _qref15 = [None]
            with mc._sc.backup_action("Fix Collection"):
                _qn15 = mc.migrate_collection_folder(_qd15, "Coleção Alien", "Alien Collection", _qref15)
            _qa15 = (_qls15("Alien Collection"), _qls15("Coleção Alien"),
                     open(os.path.join(_qd15, "Alien Collection", "poster.jpg"), "rb").read())
            _qres15 = mc._sc.restore_backup_run(mc._BACKUP_ROOT, _qref15[0])
            _qu15 = (_qls15("Alien Collection"), _qls15("Coleção Alien"))
            check("fix 15: the old folder's files move to the new name (its poster kept, the new one in replaced\\), "
                  "the old folder removed; Undo puts everything back",
                  _qa15[0] == ["extrafanart/x.jpg", "fanart.jpg", "poster.jpg", "replaced/poster.png"] and _qa15[1] is None
                  and _qa15[2] == b"OLDPOSTER" and "3 files moved" in (_qn15 or "")
                  and _qu15[0] == ["poster.png"] and _qu15[1] == ["extrafanart/x.jpg", "fanart.jpg", "poster.jpg"]
                  and not _qres15[1], (_qn15, _qa15, _qres15[1], _qu15))
            shutil.rmtree(os.path.join(_qd15, "Alien Collection"), ignore_errors=True)
            shutil.rmtree(os.path.join(_qd15, "Coleção Alien"), ignore_errors=True)

            # B: Fix Collection on the movies: their NFO gets TMDB's name and the folder (no new one yet) comes along
            _qlib15 = os.path.join(_qd15, "lib"); _qrows15 = []
            for _qt in ("Alien", "Aliens"):
                _qp = os.path.join(_qlib15, f"{_qt} (1979)"); os.makedirs(_qp)
                open(os.path.join(_qp, f"{_qt} (1979).nfo"), "w", encoding="utf-8").write(
                    f"<movie>\n  <title>{_qt}</title>\n  <set tmdbcolid=\"8091\">\n    <name>Coleção Alien</name>\n  </set>\n</movie>\n")
                _qr = mc.scan_one_subfolder(_qp, f"{_qt} (1979)", use_ffprobe=False); _qr["library_root"] = _qlib15
                _qrows15.append(_qr)
            _qmk15("Coleção Alien", {"poster.jpg": b"P", "fanart.jpg": b"F"})
            mc.SETTINGS["collection_folder"] = _qd15
            mc.SETTINGS["library_folders"] = [_qlib15]                  # P3 (decision 5): every library loaded
            app._results = list(_qrows15)
            app._coll_write_done = None; _boxes.clear()
            app._coll_folders_read = None
            on_ui(lambda: app._write_collections([(r, ("Alien Collection", 8091, None)) for r in _qrows15], "Fix Collection"))
            wait_for(lambda: app._coll_write_done is not None, 20)
            wait_for(lambda: app._coll_folders_read is True, 20)          # the folder re-read after the move
            _qb15 = (_qls15("Alien Collection"), _qls15("Coleção Alien"), [str(b) for b in _boxes[-1:]])
            check("fix 15: Fix Collection renames the movies and their collection folder comes along (no empty new folder)",
                  app._coll_write_done[0] == 2 and _qb15[0] == ["fanart.jpg", "poster.jpg"] and _qb15[1] is None
                  and "Collection folders:" in _qb15[2][0], _qb15)
            # fix 17: once the rows carry the new name, the app knows the new folder and its images (the panel's data)
            wait_for(lambda: (mc.COLL_FOLDERS.get("alien collection") or {}).get("art", {}).get("poster") is not None, 20)
            _qst17 = dict(mc.COLL_FOLDERS.get("alien collection") or {})
            _qnm17 = on_ui(lambda: sorted({mc.collection_name(r) for r in app._results}))
            check("fix 17: after the rename the folder list has the new name with its poster and fanart (not 'not checked')",
                  _qnm17 == ["Alien Collection"] and _qst17.get("dir") and os.path.normcase(_qst17["dir"]) ==
                  os.path.normcase(os.path.join(_qd15, "Alien Collection"))
                  and sorted(_qst17.get("art") or {}) == ["fanart", "poster"], (_qnm17, _qst17))

            # C: another movie still uses the old name → the folder stays
            _qmk15("Old Saga", {"poster.jpg": b"P"})
            _qo1 = dict(_qrows15[0], coll_nfo={"name": "Old Saga"}); _qo2 = dict(_qrows15[1], coll_nfo={"name": "Old Saga"})
            app._results = [_qo1, _qo2]
            with mc._sc.backup_action("Fix Collection"):
                _qc15 = app._migrate_coll_folders([(_qo1, "Old Saga", "New Saga")], [None])
            _qmk15("Lone Saga", {"poster.jpg": b"P"})
            _qo3 = dict(_qrows15[0], coll_nfo={"name": "Lone Saga"}); app._results = [_qo3]
            mc.SETTINGS["library_folders"] = [_qlib15, os.path.join(_qd15, "never scanned")]
            with mc._sc.backup_action("Fix Collection"):
                _qr3 = app._migrate_coll_folders([(_qo3, "Lone Saga", "Lone Collection")], [None])
            mc.SETTINGS["library_folders"] = [_qlib15]
            check("P3: a collection folder is not moved while a library has no movies loaded (decision 5)",
                  _qls15("Lone Saga") == ["poster.jpg"] and _qls15("Lone Collection") is None
                  and "not loaded" in " ".join(_qr3), _qr3)
            app._results = [_qo1, _qo2]
            check("fix 15: the folder stays while another movie still uses the old name",
                  _qls15("Old Saga") == ["poster.jpg"] and _qls15("New Saga") is None and "kept" in " ".join(_qc15), _qc15)

            # D: a folder left under another TMDB name → warning → Fix moves it
            mc.COLL_CACHE["8092"] = {"names": {"en": "Predator Collection", "pt": "Predador - Coleção"}, "overviews": {}}
            _qmk15("Predador - Coleção", {"poster.jpg": b"P"})
            _qrw = dict(_qrows15[0], coll_nfo={"name": "Predator Collection", "tmdbcolid": 8092}, coll_tmdb={"id": 8092})
            _qal15 = mc.collection_aliases([_qrw])
            _qst15 = mc.read_collection_folders(_qd15, ["Predator Collection"], _qal15)["predator collection"]
            _qwr15 = mc._cr.artwork_reasons(_qst15)
            _qk15 = mc._fix_issue_keys({"health_reasons": _qwr15})
            mc.COLL_FOLDERS.clear(); mc.COLL_FOLDERS["predator collection"] = _qst15
            app._results = [_qrw]; app._coll_move_done = None
            app._coll_folders_read = None
            on_ui(lambda: app._import_old_coll_folder_for([_qrw], ask=False))
            wait_for(lambda: getattr(app, "_coll_move_done", None) is not None, 20)
            wait_for(lambda: app._coll_folders_read is True, 20)          # the folder re-read after the move
            check("fix 15: a folder left under another TMDB name of the collection → 'Collection folder: images left in …' → "
                  "Fix 'Move to the Collection Folder' moves it",
                  _qst15.get("old_name") == "Predador - Coleção" and _qwr15 and _qwr15[0].startswith("Collection folder: images left in")
                  and "collection_old" in _qk15 and app._coll_move_done[0] == 1
                  and _qls15("Predator Collection") == ["poster.jpg"] and _qls15("Predador - Coleção") is None,
                  (_qst15, _qwr15, _qk15, app._coll_move_done, _qls15("Predator Collection")))
        finally:
            mc.SETTINGS["collection_folder"] = _qsv15[0]
            mc.SETTINGS["library_folders"] = _qsv15[3]
            app._results = _qsv15[1]
            mc.COLL_FOLDERS.clear(); mc.COLL_FOLDERS.update(_qsv15[2]); mc.COLL_CACHE.pop("8092", None)
            def _qback15():
                mc.finalize_results(app._results); app._refresh_table()
            on_ui(_qback15)
            wait_for(lambda: app._refresh_idle() and not getattr(app, "_tbl_filling", False), 20)
            shutil.rmtree(_qd15, ignore_errors=True)

        # ── v0.19.4 full review P1: the view follows every change (grouped view, panel, selection) ──
        _dp1 = tempfile.mkdtemp(prefix="mc_p1_")
        _sp1 = (list(app._results), mc.SETTINGS.get("group_by_collection"))
        try:
            _rp1 = []
            for _t in ("Alpha", "Beta"):
                _p = os.path.join(_dp1, f"{_t} (2001)"); os.makedirs(_p)
                open(os.path.join(_p, f"{_t} (2001).nfo"), "w", encoding="utf-8").write(
                    f"<movie>\n  <title>{_t}</title>\n  <set>\n    <name>P1 Saga</name>\n  </set>\n</movie>\n")
                open(os.path.join(_p, f"{_t} (2001).mkv"), "wb").write(b"\0" * 1024)
                _r = mc.scan_one_subfolder(_p, f"{_t} (2001)", use_ffprobe=False); _r["library_root"] = _dp1
                _rp1.append(_r)
            _rp1[0]["health_status"] = "error"; _rp1[1]["health_status"] = "ok"

            def _setup1():
                app._results = list(_rp1)
                app._group_var.set(True); app._toggle_grouping()
            on_ui(_setup1)
            wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)

            def _state1():
                piid = next(iter(app._coll_map))
                kids = app.tree.get_children(piid)
                return piid, kids, app.tree.item(piid, "tags")
            _piid, _kids, _tag0 = on_ui(_state1)
            _kidA = next(k for k in _kids if app._item_map[k]["subfolder"] == "Alpha (2001)")
            on_ui(lambda: (app.tree.selection_set(_kidA), app.tree.focus(_kidA)))
            time.sleep(0.4)
            _ref0 = app._movie_panel.refreshes
            _newA = dict(_rp1[0], health_status="ok", health_reasons=[])     # the user's Fix made Alpha OK
            on_ui(lambda: app._apply_rescanned_row(_newA))
            time.sleep(0.5)
            _st1 = on_ui(lambda: (app.tree.item(_piid, "tags"), [r is _newA for r in app._coll_rows(_piid)],
                                  app._coll_map[_piid][2][0] is _newA or app._coll_map[_piid][2][1] is _newA))
            check("P1: grouped view — a fixed movie turns its collection row from red to OK, the collection row stands "
                  "for the NEW row, and the right panel refreshes for the selected movie",
                  _tag0[0].startswith("error") and _st1[0][0].startswith("ok") and any(_st1[1]) and _st1[2]
                  and app._movie_panel.refreshes > _ref0, (_tag0, _st1, _ref0, app._movie_panel.refreshes))

            # a rebuild keeps the selection (Beta selected → still Beta after a sort-like rebuild)
            _kidB = next(k for k in _kids if app._item_map[k]["subfolder"] == "Beta (2001)")
            on_ui(lambda: (app.tree.selection_set(_kidB), app.tree.focus(_kidB)))
            on_ui(app._refresh_table)
            wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)
            _selp = on_ui(lambda: [app._item_map[i]["subfolder"] for i in app.tree.selection() if i in app._item_map])
            check("P1: a table rebuild keeps the selected movie selected", _selp == ["Beta (2001)"], _selp)

            # an Update given an item id from before a rebuild finds the row by its folder
            _stale = _kidB
            on_ui(app._refresh_table)
            wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)
            _rowB = next(r for r in app._results if r["subfolder"] == "Beta (2001)")
            _err1 = None
            try:
                on_ui(lambda: app._reval_no_ffmpeg(_stale, _rowB))
            except Exception as _ex1:
                _err1 = str(_ex1)[:300]
            _nowB = on_ui(lambda: next(r for i, r in app._item_map.items() if r["subfolder"] == "Beta (2001)"))
            check("P1: Update with an item id from before a rebuild updates the right row (no error, no phantom item)",
                  _err1 is None and _nowB is not _rowB and _stale not in app._item_map, (_err1, _stale in app._item_map))
        finally:
            def _back1():
                app._results = _sp1[0]
                mc.SETTINGS["group_by_collection"] = _sp1[1]; app._group_var.set(bool(_sp1[1]))
                app.tree.selection_set(())
                mc.finalize_results(app._results); app._refresh_table()
            on_ui(_back1)
            wait_for(lambda: app._refresh_idle() and not getattr(app, "_tbl_filling", False), 20)
            shutil.rmtree(_dp1, ignore_errors=True)

        # ── v0.19.4 full review P2: workers and timing ──
        # 2.5 a scan waits for a running action
        _ev2 = threading.Event()
        _th2 = mc._AppJobThread(app, target=lambda: _ev2.wait(10))
        on_ui(_th2.start)
        _boxes.clear()
        on_ui(app._scan)
        _scan2 = (app._scanning, any("still running" in str(b) for b in _boxes))
        _ev2.set(); _th2.join(5)
        wait_for(lambda: getattr(app, "_bg_running", 0) == 0, 5)
        check("P2: a Full Scan waits while a long action runs (message, no scan); the count goes back to 0",
              _scan2 == (False, True) and app._bg_running == 0, (_scan2, app._bg_running))
        _boxes.clear()

        # 2.2 two collection-folder reads at once: the newer result is applied, every 'then' runs once
        _dq2 = tempfile.mkdtemp(prefix="mc_p2_")
        _occ2 = mc.SETTINGS.get("collection_folder")
        try:
            os.makedirs(os.path.join(_dq2, "Some Saga")); open(os.path.join(_dq2, "Some Saga", "poster.jpg"), "wb").write(b"x")
            mc.SETTINGS["collection_folder"] = _dq2
            _then2 = []
            on_ui(lambda: (app._read_collection_folders(then=lambda: _then2.append(1)),
                           app._read_collection_folders(then=lambda: _then2.append(2))))
            wait_for(lambda: len(_then2) >= 2, 20)
            time.sleep(0.3)
            check("P2: two collection-folder reads at once — both callbacks run once, after the newest read",
                  sorted(_then2) == [1, 2] and app._coll_folders_read is True, _then2)
        finally:
            mc.SETTINGS["collection_folder"] = _occ2
            on_ui(lambda: app._read_collection_folders())
            time.sleep(0.5)
            shutil.rmtree(_dq2, ignore_errors=True)

        # 2.7 two saves of the results cache at once leave a valid file and no temp files
        _rows27 = [dict(r) for r in list(app._results)[:5]]
        _errs27 = []

        def _save27():
            for _ in range(15):
                if not mc._sc.save_results_cache(_rows27):
                    _errs27.append("fail")
        _ts27 = [threading.Thread(target=_save27) for _ in range(3)]
        [x.start() for x in _ts27]; [x.join(30) for x in _ts27]
        _cfg27 = os.path.dirname(mc._sc.RESULTS_CACHE_PATH)
        _tmp27 = [f for f in os.listdir(_cfg27) if f.startswith(os.path.basename(mc._sc.RESULTS_CACHE_PATH)) and f.endswith(".tmp")]
        _ok27 = len(json.load(open(mc._sc.RESULTS_CACHE_PATH, encoding="utf-8"))["rows"]) == len(_rows27)
        check("P2: saving the results cache from 3 threads at once — a valid file, no temp files left",
              not _errs27 and not _tmp27 and _ok27, (_errs27, _tmp27, _ok27))

        # 2.8 a save during a Full Scan keeps the previous row of a folder the scan has not finished
        _prev28 = dict(list(app._results)[0]); _stub28 = dict(_prev28, scan_mtime=None, movie_name="STUB")
        _sv28 = (app._scanning, getattr(app, "_scan_prior", None), app._last_cache_save)
        try:
            app._scanning, app._scan_prior, app._last_cache_save = True, [_prev28], 0
            on_ui(lambda: app._incremental_save([_stub28]))
            _got28 = json.load(open(mc._sc.RESULTS_CACHE_PATH, encoding="utf-8"))["rows"]
            check("P2: a save during a Full Scan keeps the previous row of an unfinished folder (not the stub)",
                  len(_got28) == 1 and _got28[0].get("movie_name") == _prev28.get("movie_name") != "STUB",
                  [r.get("movie_name") for r in _got28])
        finally:
            app._scanning, app._scan_prior, app._last_cache_save = _sv28
            on_ui(lambda: app._incremental_save(app._results))

        # ── v0.19.4 full review P3: writes, files and Undo ──
        _dp3 = tempfile.mkdtemp(prefix="mc_p3_")
        try:
            # 3.1 a plain folder with backdrop.jpg only: Fetch Fanart writes fanart.jpg; backdrop.jpg is the main fanart
            _f31 = os.path.join(_dp3, "Plain (2001)"); os.makedirs(_f31)
            open(os.path.join(_f31, "Plain (2001).mkv"), "wb").write(b"\0" * 64)
            for _nm in ("backdrop.jpg", "cover.jpg"):
                open(os.path.join(_f31, _nm), "wb").write(b"img")
            _wt31 = (mc.artwork_targets_for_fetch(_f31, "fanart"), mc.artwork_targets_for_fetch(_f31, "poster"))
            _fx31 = mc.artwork_write_target(_f31, "poster")              # the image fix: the file that is there
            check("P3: Fetch never overwrites an image Kodi does not read — backdrop.jpg / cover.jpg stay, fanart.jpg / "
                  "poster.jpg are written (the image fix still repairs cover.jpg itself)",
                  [os.path.basename(x) for x in _wt31[0][0]] == ["fanart.jpg"] and not _wt31[0][1]
                  and os.path.basename(_wt31[1][0][0]) == "poster.jpg" and os.path.basename(_fx31[0]) == "cover.jpg",
                  (_wt31, _fx31))
            # 3.2 a one-line NFO: genres inside <movie>, the old one gone
            _n32 = os.path.join(_dp3, "one.nfo")
            open(_n32, "w", encoding="utf-8", newline="\n").write("<movie><title>T</title><genre>Drama</genre></movie>\n")
            _ok32 = mc.write_genres_to_nfo(_n32, ["Action", "Comedy"])
            _t32 = open(_n32, encoding="utf-8").read()
            import xml.etree.ElementTree as _ET32
            _g32 = [g.text for g in _ET32.fromstring(_t32).findall("genre")]
            check("P3: Normalize Genres on a one-line NFO — the genres inside <movie>, a valid NFO", _ok32[0] and _g32 == ["Action", "Comedy"], (_ok32, _t32))
            # 3.4 two <set> blocks → both removed
            _n34 = os.path.join(_dp3, "two.nfo")
            open(_n34, "w", encoding="utf-8", newline="\n").write(
                "<movie>\n  <title>T</title>\n  <set>\n    <name>A</name>\n  </set>\n  <set>B</set>\n</movie>\n")
            _ok34 = mc.remove_collection_from_nfo(_n34)
            check("P3: Remove from Collection removes every <set> block", _ok34[0] and "<set" not in open(_n34, encoding="utf-8").read(),
                  open(_n34, encoding="utf-8").read())
            # 3.5 the overview: another collection's is dropped; the same collection's is kept as written
            _tx35 = ('<movie>\n  <set tmdbcolid="1">\n    <name>Old</name>\n    <overview>Line one.\n\nLine two &amp; more.</overview>\n'
                     '  </set>\n</movie>\n')
            _a35 = mc._cr.replace_set_in_text(_tx35, "New Collection", 2, None)
            _b35 = mc._cr.replace_set_in_text(_tx35, "Old Collection", 1, None)
            check("P3: moving to ANOTHER collection drops the old overview; the SAME collection keeps it as written (paragraphs)",
                  "<overview>" not in _a35 and "<overview>Line one.\n\nLine two &amp; more.</overview>" in _b35, (_a35, _b35))
            # 3.9 typed IDs
            _c39 = [mc.clean_typed_id("imdb", "https://www.imdb.com/title/tt0133093/")[0], mc.clean_typed_id("imdb", "0133093")[0],
                    mc.clean_typed_id("imdb", "abc")[0], mc.clean_typed_id("tmdb", "https://www.themoviedb.org/movie/603-the-matrix")[0],
                    mc.clean_typed_id("tmdb", "603")[0], mc.clean_typed_id("tmdb", "abc")[0]]
            check("P3: typed IDs are checked — an IMDb / TMDB address gives its ID, 'abc' is refused",
                  _c39 == ["tt0133093", "tt0133093", None, "603", "603", None], _c39)
            # 3.6 a folder move that made the new folder: Undo removes it again
            _root36 = os.path.join(_dp3, "sets"); os.makedirs(os.path.join(_root36, "Velha Saga"))
            open(os.path.join(_root36, "Velha Saga", "poster.jpg"), "wb").write(b"P")
            open(os.path.join(_root36, "Velha Saga", "Thumbs.db"), "wb").write(b"junk")
            _ref36 = [None]
            with mc._sc.backup_action("Fix Collection"):
                _n36 = mc.migrate_collection_folder(_root36, "Velha Saga", "Old Saga", _ref36)
            _mid36 = (sorted(os.listdir(os.path.join(_root36, "Old Saga"))), os.path.isdir(os.path.join(_root36, "Velha Saga")))
            _u36 = mc._sc.restore_backup_run(mc._BACKUP_ROOT, _ref36[0])
            check("P3: a move that made the new folder — Thumbs.db not moved, the old folder gone; Undo restores it and "
                  "removes the new folder",
                  _mid36 == (["poster.jpg"], False) and not _u36[1] and not os.path.isdir(os.path.join(_root36, "Old Saga"))
                  and sorted(os.listdir(os.path.join(_root36, "Velha Saga"))) == ["Thumbs.db", "poster.jpg"], (_n36, _mid36, _u36[1]))
            # 3.10 Thumbs.db alone does not make an "old collection folder"
            os.makedirs(os.path.join(_root36, "Junk Saga")); open(os.path.join(_root36, "Junk Saga", "desktop.ini"), "wb").write(b"x")
            _st310 = mc.read_collection_folders(_root36, ["Junk Collection"], {"Junk Collection": ["Junk Saga"]})["junk collection"]
            check("P3: a folder holding only desktop.ini / Thumbs.db is not an 'old collection folder'", not _st310.get("old_dir"), _st310)
        finally:
            shutil.rmtree(_dp3, ignore_errors=True)

        # ── v0.19.4 full review P4: rules and their Fix agree ──
        _c4 = {"20": {"names": {"en": "Four Collection", "pt": "Quatro - Coleção", "es": "Cuatro - Colección"}, "overviews": {}}}
        _tt4 = {"en": "Four", "pt": "Quatro", "es": "Cuatro"}
        _r4 = lambda tl: {"coll_tmdb": {"id": 20}, "nfo_title": tl, "tmdb_titles": dict(_tt4), "coll_nfo": None}
        _v4 = [_cr.chosen_names([_r4(x) for x in s], _c4, "pt-BR")[20][2] for s in
               (["Quatro", "Quatro", "Quatro", "Four", "Four"], ["Quatro", "Quatro", "Cuatro", "Four"], ["Quatro", "Quatro", "Cuatro", "Cuatro"])]
        _f4x = _cr.chosen_names([_r4("Four"), _r4("Four")], _c4, "en-US", fixed="pt")[20][2]
        _f4y = _cr.chosen_names([_r4("Four")], {"20": {"names": {"en": "Four Collection"}, "overviews": {}}}, "en-US", fixed="pt")[20][2]
        check("P4: a language wins only with more than half of the movies (3 of 5 pt → pt; 2 pt + 1 es + 1 en → en; "
              "2 pt + 2 es → en); a fixed language from Settings wins (English when TMDB has no name in it)",
              _v4 == ["pt", "en", "en"] and _f4x == "pt" and _f4y == "en", (_v4, _f4x, _f4y))
        _tm4 = {"id": 20, "name": "Four Collection"}
        _ft4 = _cr.fix_target({"coll_tmdb": _tm4, "nfo_title": "Four", "tmdb_titles": dict(_tt4), "coll_nfo": {"name": "Four Collection"}},
                              _c4, "en-US", {20: ("Four Collection", None, "en")})
        _mr4 = _cr.mismatch_reasons({"coll_tmdb": _tm4, "coll_nfo": {"name": "Four Collection", "tmdbcolid": 99}}, _c4, None,
                                    {20: ("Four Collection", None, "en")})
        check("P4: the right name without a TMDB collection ID is right (decision 4); only the ID differs → its own words",
              _ft4[3] == "already right" and _mr4 == ["Collection: NFO links TMDB collection 99, TMDB lists 20 for this movie"], (_ft4, _mr4))
        # 4.1 empty tags next to a value → Auto Repair copies it; 4.2 rating 0.0 → rating sync planned
        _pl4 = [c for c, _l in mc._auto_repair_plan({"source_imdb_status": mc.STATUS_ERROR, "source_imdb_all": ["tt0133093", ""],
                                                     "source_tmdb_status": mc.STATUS_OK, "source_tmdb_all": ["603"],
                                                     "rating_status": mc.STATUS_OK, "votes_status": mc.STATUS_OK, "rating_value": 0.0,
                                                     "nfo_exists": True, "xml_exists": True}, mc.SETTINGS)]
        check("P4: 'IMDb ID present in some tags but empty in others' → Auto Repair copies the ID; rating 0.0 → the rating sync",
              "ids_partial" in _pl4 and any(c.startswith("rating") for c in _pl4), _pl4)
        # 4.10 4:3 HD; 4.9 one language matcher; 4.11 no XML → no "Language field missing in XML"
        _er4, _wr4 = [], []
        check("P4: 1440×1080 is 1080p, 960×720 is 720p; 'es-419' / 'pt-BR' match their language; no movie.xml → no language warning",
              mc.classify_quality(1440, 1080) == "1080p" and mc.classify_quality(960, 720) == "720p" and mc.classify_quality(1920, 800) == "1080p"
              and mc.is_target_lang("es-419", "ES") and mc.is_target_lang("pt-BR", "PT") and not mc.is_target_lang("en-US", "PT")
              and not _wr4, (mc.classify_quality(1440, 1080), mc.classify_quality(960, 720), _wr4))
        # 4.13 Fix issues for corrupt images
        _k4 = mc._fix_issue_keys({"health_reasons": ["Corrupt poster image (cannot be decoded)", "Corrupt fanart image (cannot be decoded)",
                                                      "No audio tracks detected"]})
        check("P4: a corrupt poster → Fetch Poster, a corrupt fanart → Fetch Fanart; 'No audio tracks' is not sent to Subtitles…",
              {"poster", "fanart"} <= _k4 and "audio" not in _k4, _k4)
        # 4.8 votes outside the Kodi v17+ <ratings> block
        _dv4 = tempfile.mkdtemp(prefix="mc_p4_")
        try:
            _nv4 = os.path.join(_dv4, "v.nfo")
            open(_nv4, "w", encoding="utf-8").write('<movie>\n  <ratings>\n    <rating name="themoviedb" max="10"><value>7.0</value><votes>2000</votes></rating>\n'
                                                   '    <rating name="imdb" max="10" default="true"><value>7.3</value><votes>500000</votes></rating>\n'
                                                   '  </ratings>\n</movie>\n')
            _vv4 = mc.extract_votes_from_files(_nv4, None)[0]
            check("P4: votes in a Kodi v17+ NFO come from the block the rating comes from (imdb 500000), not the first block (2000)",
                  _vv4 == 500000, _vv4)
        finally:
            shutil.rmtree(_dv4, ignore_errors=True)
        # 4.6 / 4.7 a rescan keeps FFprobe data only for the same video, the ID check only while the IDs are unchanged
        _old4 = {"ffprobe_ran": True, "video_width": 1280, "video_height": 720, "video_quality": "720p", "audio_tracks": [],
                 "subs_internal": [], "video_path": "x.mkv", "video_bytes": 100, "video_mtime": 1.0,
                 "id_check": {"result": mc.ID_DIFFERENT}, "source_imdb_val": "tt1", "source_tmdb_val": "1"}
        _new4 = {"video_path": "x.mkv", "video_bytes": 999, "video_mtime": 2.0, "subs_external": [], "subs_internal": [],
                 "video_quality": "—", "source_imdb_val": "tt2", "source_tmdb_val": "2", "id_check": None}
        mc.carry_after_rescan(_new4, _old4)
        check("P4: after a fix the rescan does not keep the OLD video's quality (video replaced) nor an ID check of OLD IDs",
              _new4.get("video_quality") != "720p" and not _new4.get("id_check"), (_new4.get("video_quality"), _new4.get("id_check")))

        # ── v0.19.4 review fix 5: one name per collection — a split collection is fixed once and stays fixed ──
        _d5 = tempfile.mkdtemp(prefix="mc_fix5_")
        _save5 = (list(app._results), dict(mc.COLL_CACHE), mc.SETTINGS.get("group_by_collection"), mc.SETTINGS.get("lang_ok_code"))
        try:
            mc.SETTINGS["lang_ok_code"] = "EN"
            mc.COLL_CACHE["173710"] = {"names": {"en": "Planet of the Apes (Reboot) Collection",
                                                 "pt": "Planeta dos Macacos (Reboot) - Coleção"}, "overviews": {}}
            _r5 = []
            for _nm5, _set5, _tl5 in (("Rise (2011)", "Planet of the Apes (Reboot) Collection", ["en"]),
                                      ("Origem (2011b)", "Planeta dos Macacos (Reboot) - Coleção", ["en"]),
                                      ("Guerra (2017)", "Planeta dos Macacos (Reboot) - Coleção", ["pt"])):
                _p5 = os.path.join(_d5, _nm5); os.makedirs(_p5)
                open(os.path.join(_p5, _nm5 + ".nfo"), "w", encoding="utf-8").write(
                    f"<movie>\n  <title>{_nm5[:-7]}</title>\n  <set tmdbcolid=\"173710\">\n    <name>{_set5}</name>\n  </set>\n</movie>\n")
                _rr5 = mc.scan_one_subfolder(_p5, _nm5, use_ffprobe=False)
                _rr5.update(library_root=_d5, coll_tmdb={"id": 173710, "name": "Planet of the Apes (Reboot) Collection", "when": time.time()},
                            title_langs=_tl5)
                _r5.append(_rr5)
            on_ui(lambda: (setattr(app, "_results", list(_r5)), mc.finalize_results(app._results),
                           app._group_var.set(True), app._toggle_grouping()))
            wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)
            _before5 = on_ui(lambda: sorted(v[1] for v in app._coll_map.values()))
            _w5 = {r["subfolder"]: [w for w in r.get("health_reasons") or [] if w.startswith("Collection")] for r in app._results}
            # the user's click: Fix on ONE movie that is "already right" in its own language
            app._coll_write_done = None; _boxes.clear()
            _rg5 = getattr(app, "_regrouped", 0)
            on_ui(lambda: app._fix_collections_for([next(r for r in app._results if r["subfolder"] == "Rise (2011)")], preview=False))
            wait_for(lambda: app._coll_write_done is not None, 15)
            wait_for(lambda: getattr(app, "_regrouped", 0) > _rg5 and app._refresh_idle() and not getattr(app, "_tbl_filling", False), 20)
            _settle()
            _after5 = on_ui(lambda: sorted(v[1] for v in app._coll_map.values()))
            _names5 = {r["subfolder"]: mc.collection_name(r) for r in app._results}
            _left5 = {r["subfolder"]: [w for w in r.get("health_reasons") or [] if w.startswith("Collection")] for r in app._results}
            _again5 = mc.collection_fix_items(mc.collection_siblings(list(app._results)[:1], app._results), None, "en-US")[0]
            check("fix 5: a collection split by language (2 sets) → ONE Fix gives every movie the one name; no warning left; Fix again finds nothing",
                  len(_before5) == 2 and any(_w5.values()) and app._coll_write_done[0] == 2
                  and len(_after5) == 1 and set(_names5.values()) == {"Planet of the Apes (Reboot) Collection"}
                  and not any(_left5.values()) and _again5 == [], (_before5, _w5, app._coll_write_done, _after5, _names5, _left5))

            # Join: your own set "Apes" joins the TMDB collection in use (its name and TMDB id)
            _pj5 = os.path.join(_d5, "Own (2001)"); os.makedirs(_pj5)
            open(os.path.join(_pj5, "Own (2001).nfo"), "w", encoding="utf-8").write(
                "<movie>\n  <title>Own</title>\n  <set>\n    <name>Apes</name>\n  </set>\n</movie>\n")
            _rj5 = mc.scan_one_subfolder(_pj5, "Own (2001)", use_ffprobe=False); _rj5["library_root"] = _d5
            on_ui(lambda: (app._results.append(_rj5), mc.finalize_results(app._results), app._refresh_table()))
            app._coll_write_done = None
            on_ui(lambda: app._set_collection_for([_rj5], name="Planet of the Apes (Reboot) Collection"))
            wait_for(lambda: app._coll_write_done is not None, 15)
            _tj5 = open(_rj5["nfo_path"], encoding="utf-8").read()
            check("fix 5: Rename / Join Collection… — choosing a collection in use joins it (its name and its TMDB id)",
                  '<set tmdbcolid="173710">' in _tj5 and "<name>Planet of the Apes (Reboot) Collection</name>" in _tj5, _tj5)
            _boxes.clear()
        finally:
            def _back5():
                app._results = _save5[0]
                mc.COLL_CACHE.clear(); mc.COLL_CACHE.update(_save5[1])
                mc.SETTINGS["group_by_collection"] = _save5[2]; app._group_var.set(bool(_save5[2]))
                mc.SETTINGS["lang_ok_code"] = _save5[3]
                mc.finalize_results(app._results); app._refresh_table(); app._incremental_save(app._results)
            _settle()
            on_ui(_back5)
            wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)
            _boxes.clear()
            shutil.rmtree(_d5, ignore_errors=True)

        # ── v0.19.4 review fix 6: the collection in movie.xml ──
        _X6 = ('<?xml version="1.0" encoding="utf-8"?>\n<Title>\n    <LocalTitle>{t}</LocalTitle>\n    <IMDB_ID>tt1</IMDB_ID>\n'
               '{coll}    <JSONDump>{{belongs_to_collection:{{id:5,name:Keep Me}}}}</JSONDump>\n</Title>\n')
        _XC6 = ("    <TMDbCollectionId>{i}</TMDbCollectionId>\n    <CollectionNumber>{i}</CollectionNumber>\n"
                "    <CollectionName>{n}</CollectionName>\n")
        _xs6 = _X6.format(t="S", coll="    <TMDbCollectionId>0</TMDbCollectionId>\n    <CollectionNumber>0</CollectionNumber>\n"
                                     "    <CollectionName>Nada: Coleção</CollectionName>\n    <set\n        tmdbcolid=\"963928\">\n"
                                     "        <name>Nada: Coleção</name>\n    </set>\n")
        _fx6 = mc._cr.xml_collection_text(_xs6, "Nada: Coleção", 963928)
        check("fix 6: movie.xml read — TMDbCollectionId / CollectionNumber / CollectionName and the stray NFO-style <set>",
              mc._cr.read_xml_collection(_X6.format(t="A", coll=_XC6.format(i=86029, n="Charlie's Angels")))
              == {"name": "Charlie's Angels", "tmdbcolid": 86029, "stray": False}
              and mc._cr.read_xml_collection(_xs6) == {"name": "Nada: Coleção", "tmdbcolid": 963928, "stray": True}
              and mc._cr.read_xml_collection(_X6.format(t="N", coll="")) == {"name": None, "tmdbcolid": None, "stray": False}, None)
        check("fix 6: movie.xml write — the ids and the name set, the stray <set> removed, <JSONDump> and every other line kept",
              "<TMDbCollectionId>963928</TMDbCollectionId>" in _fx6 and "<CollectionNumber>963928</CollectionNumber>" in _fx6
              and "<set" not in _fx6 and "<JSONDump>{belongs_to_collection:{id:5,name:Keep Me}}</JSONDump>" in _fx6
              and _fx6.count("\n") == _xs6.count("\n") - 4, _fx6)
        _d6 = tempfile.mkdtemp(prefix="mc_fix6_")
        _save6 = (list(app._results),)
        _osr6 = app._schedule_refresh
        try:
            _p6 = os.path.join(_d6, "Angels (2003)"); os.makedirs(_p6)
            open(os.path.join(_p6, "Angels (2003).nfo"), "w", encoding="utf-8").write(
                "<movie>\n  <title>Angels</title>\n  <set tmdbcolid=\"86029\">\n    <name>Charlie's Angels Collection</name>\n  </set>\n</movie>\n")
            _xp6 = os.path.join(_p6, "movie.xml")
            open(_xp6, "w", encoding="utf-8").write(_X6.format(t="Angels", coll=_XC6.format(i=86029, n="Charlie's Angels")))
            _r6 = mc.scan_one_subfolder(_p6, "Angels (2003)", use_ffprobe=False); _r6["library_root"] = _d6
            on_ui(lambda: (setattr(app, "_results", [_r6]), mc.finalize_results(app._results), app._refresh_table()))
            _w6 = [w for w in app._results[0].get("health_reasons") or [] if w.startswith("Collection: movie.xml")]
            _k6 = mc._fix_issue_keys(app._results[0])
            app._coll_write_done = None; _boxes.clear()
            on_ui(lambda: app._ctx_fix_action("collection_xml", [app._results[0]])[0](None, None, None))
            wait_for(lambda: app._coll_write_done is not None, 15)
            _settle()
            _settle()
            _x6 = open(_xp6, encoding="utf-8").read()
            _left6 = [w for w in app._results[0].get("health_reasons") or [] if w.startswith("Collection")]
            _boxes.clear()
            on_ui(lambda: app._sync_collection_xml_for([app._results[0]]))
            check("fix 6: movie.xml says another collection → warning → Sync gives movie.xml the NFO's → the warning is gone; Sync again: nothing to do",
                  _w6 == ["Collection: movie.xml says 'Charlie's Angels', the NFO says 'Charlie's Angels Collection'"]
                  and "collection_xml" in _k6 and "<CollectionName>Charlie's Angels Collection</CollectionName>" in _x6
                  and "<TMDbCollectionId>86029</TMDbCollectionId>" in _x6 and not _left6
                  and any("already say the same collection" in str(b) for b in _boxes), (_w6, _k6, _x6, _left6, _boxes[-1:]))
            # Remove from Collection cleans movie.xml too (ids 0, the name removed)
            app._schedule_refresh = lambda *a, **k: None
            app._coll_write_done = None; _boxes.clear()
            on_ui(lambda: app._remove_collection_for([app._results[0]], ask=False))
            wait_for(lambda: app._coll_write_done is not None, 15)
            _x6b = open(_xp6, encoding="utf-8").read()
            check("fix 6: Remove from Collection… — the NFO <set> removed AND movie.xml cleaned (ids 0, CollectionName removed, the rest kept)",
                  "<set" not in open(_r6["nfo_path"], encoding="utf-8").read() and "<TMDbCollectionId>0</TMDbCollectionId>" in _x6b
                  and "<CollectionNumber>0</CollectionNumber>" in _x6b and "CollectionName" not in _x6b and "<JSONDump>" in _x6b, _x6b)
            # Set Collection writes movie.xml too
            app._coll_write_done = None
            on_ui(lambda: app._set_collection_for([app._results[0]], name="Angels Own"))
            wait_for(lambda: app._coll_write_done is not None, 15)
            _x6c = open(_xp6, encoding="utf-8").read()
            check("fix 6: Set Collection… writes movie.xml too (your own collection: ids 0, CollectionName)",
                  "<CollectionName>Angels Own</CollectionName>" in _x6c and "<TMDbCollectionId>0</TMDbCollectionId>" in _x6c, _x6c)
            # a cache written before fix 6: the movie.xml collection is read at the restore
            _lg6 = mc._results_from_json([dict({k: v for k, v in _r6.items() if k not in ("coll_xml", "coll_xml_read")})])
            _n6 = mc.read_unread_collections(_lg6)
            check("fix 6: rows cached before the movie.xml read get their movie.xml collection at the restore",
                  _n6 == 1 and (_lg6[0].get("coll_xml") or {}).get("name") == "Angels Own" and _lg6[0].get("coll_xml_read") == 1,
                  (_n6, _lg6[0].get("coll_xml")))
            _boxes.clear()
        finally:
            app._schedule_refresh = _osr6
            _settle()
            on_ui(lambda: (setattr(app, "_results", _save6[0]), mc.finalize_results(app._results), app._refresh_table(),
                           app._incremental_save(app._results)))
            wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)
            _boxes.clear()
            shutil.rmtree(_d6, ignore_errors=True)

        # ── v0.19.4 review fix 7: the movies inside a collection row are indented (and stay so after an update) ──
        _save7 = list(app._results); _gw7 = mc.SETTINGS.get("group_by_collection")
        try:
            _r7 = [dict(r) for r in list(app._results)[:3]]
            for _x7 in _r7[:2]:
                _x7["coll_nfo"] = {"name": "Indent Saga"}
            _r7[2]["coll_nfo"] = None
            on_ui(lambda: (setattr(app, "_results", _r7), mc.finalize_results(app._results),
                           app._group_var.set(True), app._toggle_grouping()))
            wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)
            def _cells7():
                out = {}
                for i in app._item_map:
                    out[app._item_map[i]["subfolder"]] = (bool(app.tree.parent(i)), app.tree.item(i, "values")[mc.COL_MOVIE_NAME])
                return out
            _c7 = on_ui(_cells7)
            _kid7 = next(i for i in app._item_map if app.tree.parent(i))
            on_ui(lambda: app._apply_rescanned_row(app._item_map[_kid7]))
            _c7b = on_ui(lambda: app.tree.item(_kid7, "values")[mc.COL_MOVIE_NAME])
            check("fix 7: the movies inside a collection row are indented (the others not); an update keeps the indent",
                  all(v.startswith(app.CHILD_INDENT) for k, (inside, v) in _c7.items() if inside)
                  and all(not v.startswith(app.CHILD_INDENT) for k, (inside, v) in _c7.items() if not inside)
                  and sum(1 for inside, v in _c7.values() if inside) == 2 and _c7b.startswith(app.CHILD_INDENT), (_c7, _c7b))
        finally:
            def _back7():
                app._results = _save7
                mc.SETTINGS["group_by_collection"] = _gw7; app._group_var.set(bool(_gw7))
                mc.finalize_results(app._results); app._refresh_table()
            on_ui(_back7)
            wait_for(lambda: not getattr(app, "_tbl_filling", False), 10)

        # ── v0.19.4 B110h: the grouped view in the real window ──  ### NEW v0.19.4 B110h ###
        _rows_h = list(app._results)[:3]
        _keep_h = [r.get("coll_nfo") for r in _rows_h]
        _rows_h[0]["coll_nfo"] = {"name": "Test Saga"}; _rows_h[1]["coll_nfo"] = {"name": "test saga"}; _rows_h[2]["coll_nfo"] = None
        try:
            on_ui(lambda: (app._group_var.set(True), app._toggle_grouping()))
            _settle()
            _cm_h = dict(app._coll_map)
            _cit_h = next(iter(_cm_h), None)
            _kids_h = on_ui(lambda: list(app.tree.get_children(_cit_h))) if _cit_h else []
            _top_h = on_ui(lambda: len(app.tree.get_children()))
            _mv_h = on_ui(lambda: len(app._view_movie_iids()))
            _shown_h = len(app._item_map)
            check("B110h: grouped — one collection row for 'Test Saga' / 'test saga' (as Kodi), its 2 movies under it, the others single",
                  len(_cm_h) == 1 and len(_kids_h) == 2 and _top_h == _shown_h - 1 and _mv_h == _shown_h
                  and on_ui(lambda: app.tree.item(_cit_h, "values")[mc.COL_MOVIE_NAME]).startswith("Test Saga  (2"), (len(_cm_h), _kids_h, _top_h, _mv_h, _shown_h))
            on_ui(lambda: (app.tree.selection_set(_cit_h), app.update()))
            time.sleep(0.3); on_ui(lambda: app.update())
            _sr_h = on_ui(lambda: app._selected_rows())
            _pt_h = on_ui(lambda: app._movie_panel._title.cget("text"))
            check("B110h: selecting the collection row = its movies for every action; the panel shows the collection",
                  len(_sr_h) == 2 and all(r.get("coll_nfo") for r in _sr_h) and _pt_h.startswith("Test Saga"), (len(_sr_h), _pt_h))
            on_ui(lambda: app._coll_set_open(_cit_h, True))
            _vis_open = on_ui(lambda: len(app._visible_iids()))
            on_ui(lambda: app._coll_set_open(_cit_h, False))
            _vis_closed = on_ui(lambda: len(app._visible_iids()))
            on_ui(lambda: app._select_all_visible(None))
            _all_h = on_ui(lambda: len(app._selected_movie_iids()))
            check("B110h: open / close a collection; Ctrl+A selects every movie, also inside a closed collection",
                  _vis_open == _vis_closed + 2 and _all_h == _shown_h and app._coll_open == set(), (_vis_open, _vis_closed, _all_h))
            on_ui(lambda: app._coll_set_open(_cit_h, True))
            on_ui(lambda: app._refresh_table()); _settle()
            _reopen_h = on_ui(lambda: [app.tree.item(i, "open") for i in app._coll_map])
            check("B110h: an open collection stays open after a refresh (session memory)", _reopen_h == [True] or _reopen_h == [1], _reopen_h)
        finally:
            for _r_h, _k_h in zip(_rows_h, _keep_h):
                _r_h["coll_nfo"] = _k_h
            on_ui(lambda: (app._group_var.set(False), app._toggle_grouping(), app.tree.selection_set(())))
            _settle()
        check("B110h: the switch off gives the flat table back (no collection rows, 'headings' only)",
              not app._coll_map and "tree" not in str(on_ui(lambda: app.tree.cget("show"))) and mc.SETTINGS["group_by_collection"] is False,
              (len(app._coll_map), str(on_ui(lambda: app.tree.cget("show"))), mc.SETTINGS["group_by_collection"]))

        # ── v0.19.4 B74: the Help covers the app; the layout reflows and stays aligned ──  ### NEW v0.19.4 B74 ###
        import re as _re74
        _help74 = "\n".join(mc._help.plain(_tx) for _l, _tx in mc._help.HELP_TABS)

        def _core74(lbl):
            s = str(lbl)
            if "  ·  " in s:                                       # the movie header line of the menu
                return ""
            if " → " in s:                                          # "problem → action": the action must be described
                s = s.split(" → ", 1)[1]
            s = s.replace("   (F1)", "")
            prev = None
            while prev != s:                                        # trailing "(reason)" / "(Ctrl+…)" / "(n)" groups
                prev = s
                s = _re74.sub(r"\s*\((?:no|with) FFprobe\)$", "", s) if s.endswith("FFprobe)") and "Update" not in s else s
                s = _re74.sub(r"\s*\((?!no FFprobe|with FFprobe)[^()]*\)$", "", s)
            s = _re74.sub(r"\s+—\s+\d+ of \d+.*$", "", s)
            s = _re74.sub(r"^[^A-Za-z0-9\[<(]+", "", s).strip()           # emoji / symbols ("ℹ" counts as a letter for \w)
            return s.rstrip("…").strip()
        _allowed74 = {"Open the NFO in the editor": "the Ctrl+E action's internal label (the Help says 'Edit NFO' / Ctrl+E)",
                      "Hide / show the selected-movie panel": "the Ctrl+B action's internal label (Shortcuts lists it)",
                      "Filter": "the Ctrl+F action (the Help describes the Filter box)", "Help": "F1 / Ctrl+H"}
        _labels74 = set()
        for _m74 in (app._tools_menu, app._help_menu, app._menus["settings"]):
            _end = _m74.index("end")
            for _i in range(0 if _end is None else _end + 1):
                if _m74.type(_i) == "command":
                    _labels74.add(_m74.entrycget(_i, "label"))
        _r74 = dict(next(r for r in app._results), nfo_errors=[{"line": 1, "col": 0, "message": "x"}])
        on_ui(lambda: app._build_ctx_menu(None, _r74, [_r74]))
        _labels74 |= {l for _d, l, _s, _m, _i in on_ui(lambda: _flat57(app._ctx))}
        _labels74 |= {a["label"] for a in mc.ACTIONS.values()} | {v.split(" → ")[-1] for v in mc._FIX_ISSUE_LABELS.values()}
        _labels74 |= set(mc._AR_LABELS.values())
        _labels74 |= {lbl for _i, lbl, _b in mc.SettingsDialog._TAB_REGISTRY}
        _miss74 = sorted({_core74(l) for l in _labels74 if _core74(l) and _core74(l) not in _help74 and _core74(l) not in _allowed74})
        check("B74: every menu, right-click, Fix issues, Settings tab and Auto Repair label appears in the Help", not _miss74, _miss74)
        _keys74 = set()
        for _a in mc.ACTIONS.values():
            for _k in _a["keys"]:
                _kk = _k.strip("<>").replace("Control", "Ctrl").replace("-", "+")
                _kk = _re74.sub(r"\+([a-z])$", lambda mm: "+" + mm.group(1).upper(), _kk)
                _keys74.add(_kk)
        _kmiss74 = sorted(k for k in _keys74 if k not in _help74)
        check("B74: every shortcut of the action registry appears in the Help", not _kmiss74, _kmiss74)
        _h74 = on_ui(lambda: mc.HelpDialog(app, tab=0))
        try:
            def _layout74(width):
                _h74.geometry(f"{width}x700"); _h74.update()
                tx = _h74._texts[0]
                tx.see("1.0"); tx.update()
                # a long paragraph: its display lines
                rng = tx.tag_ranges("p")
                p0 = str(rng[0]); p1 = tx.index(f"{p0} lineend")
                n_lines = tx.count(p0, p1, "displaylines")[0] + 1 if tx.count(p0, p1, "displaylines") else 1
                return n_lines
            _wide74 = on_ui(lambda: _layout74(1200)); _narrow74 = on_ui(lambda: _layout74(600))
            check("B74: the text reflows — a paragraph uses more lines in a 600 px window than in a 1200 px one",
                  _narrow74 > _wide74, (_narrow74, _wide74))
            def _hang74():
                tx = _h74._texts[0]
                _h74._nb.select(_h74._nb.tabs()[0]); _h74.geometry("520x700"); _h74.update()
                out = []
                last = int(tx.index("end").split(".")[0])
                for ln in range(1, last):
                    if tx.get(f"{ln}.0") != "•":
                        continue
                    if (tx.count(f"{ln}.0", f"{ln}.0 lineend", "displaylines") or [0])[0] < 1:
                        continue                                # this bullet does not wrap at this width
                    tx.see(f"{ln}.0"); tx.update()
                    t0 = tx.bbox(f"{ln}.2")                     # the first character of the bullet's text
                    w1 = tx.index(f"{ln}.0 + 1 display lines display linestart")
                    tx.see(w1); tx.update()
                    t1 = tx.bbox(w1)
                    if t0 and t1:
                        out.append((t0[0], t1[0]))
                    if len(out) >= 3:
                        break
                return out
            _hg74 = on_ui(_hang74)
            check("B74: a wrapped bullet line starts at the same x as the bullet's text (hanging indent from margins)",
                  _hg74 and all(abs(a - b) <= 2 for a, b in _hg74), _hg74)
            def _table74():
                tx = _h74._texts[1]                                 # The Window & Table: the Columns table
                _h74._nb.select(_h74._nb.tabs()[1]); _h74.geometry("900x700"); _h74.update()
                rs = tx.tag_ranges("tbl0")
                xs = []
                a = str(rs[0])
                for _row in range(4):
                    tab_at = tx.search("\t", a, stopindex=str(rs[1]))
                    if not tab_at:
                        break
                    tx.see(tab_at); tx.update()
                    bb = tx.bbox(f"{tab_at} + 1 chars")
                    if bb:
                        xs.append(bb[0])
                    a = tx.index(f"{tab_at} lineend + 1 chars")
                return xs
            _xs74 = on_ui(_table74)
            check("B74: the descriptions of one table start at one x (the key column measured from the font)",
                  len(_xs74) >= 3 and max(_xs74) - min(_xs74) <= 2, _xs74)
        finally:
            on_ui(lambda: _h74._close())

        # ── v0.19.4 L5 / I15b: theme at start, named fonts, px(), colour tokens, minimum size ──  ### NEW v0.19.4 L5 ###
        _src5 = io.open(mc.__file__, encoding="utf-8").read()
        _lit5 = [c for c in ("#1e1e2e", "#cdd6f4", "#313244", "#45475a", "#89b4fa") if _src5.count('"' + c + '"') > 1]
        check("L5: the theme colours are tokens (each literal only once, in the token block)", not _lit5, _lit5)
        _tab5 = on_ui(lambda: str(tk.ttk.Style(app).lookup("TNotebook.Tab", "background")))
        _fn5 = on_ui(lambda: sorted(f for f in tk.font.names(app) if f.startswith("MC.")))
        check("L5: the notebook tabs are styled at start (before Help / Settings opens); named fonts MC.*",
              _tab5 == mc.C_SURFACE and _fn5 == ["MC.Body", "MC.Bold", "MC.Heading", "MC.Small"], (_tab5, _fn5))
        _ms5 = on_ui(lambda: app.minsize())
        check("L5: a minimum window size is set (px, capped to the screen)",
              _ms5[0] >= min(mc.px(1200), app.winfo_screenwidth() - 80) and _ms5[1] >= 300, _ms5)
        _sv5 = mc._UI_SCALE
        try:
            mc._UI_SCALE = 1.5
            _px5 = (mc.px(320), mc.px(22))
        finally:
            mc._UI_SCALE = _sv5
        check("L5: px() scales logical pixels (150 % → 320 px = 480)", _px5 == (480, 33), _px5)
        check("L5: _BatchProgressDialog.advance() (update() no longer hides Tk's own)",
              hasattr(mc._BatchProgressDialog, "advance") and mc._BatchProgressDialog.update is tk.Misc.update)

        # ── v0.19.4 L4 / I15a / I16: one dialog frame, one report window ──  ### NEW v0.19.4 L4 ###
        import inspect as _insp4
        _off4 = [n for n, c in vars(mc).items() if _insp4.isclass(c) and issubclass(c, tk.Toplevel)
                 and c is not mc.App and not issubclass(c, mc._DialogBase)]
        check("L4: every dialog class derives from the one dialog base (Esc = the close button)", not _off4, _off4)
        check("I16: the three report windows are one ReportWindow class",
              all(issubclass(c, mc.ReportWindow) for c in (mc.ImprovementsDialog, mc.HealthReportDialog, mc.TextReportDialog)))
        _tr4 = on_ui(lambda: mc.TextReportDialog(app, "L4 report", "LINE ONE\nline two", file_stem="l4"))
        try:
            _ord4 = on_ui(lambda: [str(w.cget("text")).strip() for w in _tr4._btn_row.winfo_children()])
            _yb4 = on_ui(lambda: (_tr4.update_idletasks(), _tr4.buttons.winfo_y() + _tr4.buttons.winfo_height(),
                                  _tr4.winfo_height())[1:])
            on_ui(lambda: _tr4._esc_default())
            _gone4 = on_ui(lambda: not _tr4.winfo_exists())
        finally:
            on_ui(lambda: _tr4.winfo_exists() and _tr4.destroy())
        check("L4: report buttons in one bottom row, the main one (Close) on the right; Esc closes",
              _ord4 == ["📋 Copy", "💾 Save to .txt", "Close"] and _yb4[0] <= _yb4[1] and _gone4, (_ord4, _yb4, _gone4))
        _cp4 = []
        _cm4 = on_ui(lambda: mc.CopyMovieNameDialog(app, ["Alpha", "Beta"]))
        _oc4 = _cm4._copy
        try:
            _cm4._copy = lambda: _cp4.append(_cm4._var.get())
            on_ui(lambda: _cm4.main_button.configure(command=_cm4._copy))
            on_ui(lambda: _cm4._on_return(type("E", (), {"widget": _cm4})()))
            _ordc = on_ui(lambda: [str(w.cget("text")).strip() for w in _cm4._btn_row.winfo_children()])
        finally:
            on_ui(lambda: _cm4.winfo_exists() and _cm4.destroy())
        check("L4: Enter runs the main button (Copy Movie Name: Cancel | Copy, Copy on the right)",
              _cp4 == ["Alpha"] and _ordc == ["Cancel", "Copy"], (_cp4, _ordc))

        # ── v0.19.4 L3: the selected-movie panel ──  ### NEW v0.19.4 L3 ###
        _kids3 = on_ui(lambda: list(app.tree.get_children()))
        _shown3 = on_ui(lambda: app._panel_shown())
        _r0 = app._item_map.get(_kids3[0]) if _kids3 else None
        on_ui(lambda: (app.tree.selection_set(_kids3[0]), app.tree.focus(_kids3[0]), app.update()))
        time.sleep(0.4); on_ui(lambda: app.update())
        _t3 = on_ui(lambda: app._movie_panel._title.cget("text"))
        _want3 = (_r0 or {}).get("movie_name") or (_r0 or {}).get("subfolder", "?")
        check("L3: the selected-movie panel is shown by default (D6) and shows the selected movie",
              _shown3 and bool(_kids3) and _t3.startswith(_want3), (_shown3, _t3, _want3))
        _btns3 = on_ui(lambda: [w.cget("text") for w in app._movie_panel._body.winfo_children() if isinstance(w, tk.Button)])
        check("L3: the panel has 'All actions ▾' (the right-click menu)", "All actions ▾" in _btns3, _btns3)
        if len(_kids3) >= 2:
            on_ui(lambda: (app.tree.selection_set(_kids3[:2]), app.update()))
            time.sleep(0.4); on_ui(lambda: app.update())
            _tm3 = on_ui(lambda: app._movie_panel._title.cget("text"))
            check("L3: several movies selected → '2 movies selected'", _tm3 == "2 movies selected", _tm3)
        _n0 = app._movie_panel.refreshes
        on_ui(lambda: [app._panel_schedule() for _i in range(12)])
        time.sleep(0.5); on_ui(lambda: app.update())
        check("L3: selection changes are debounced (12 quick changes → one refresh)",
              app._movie_panel.refreshes - _n0 == 1, app._movie_panel.refreshes - _n0)
        _w0 = mc.SETTINGS.get("movie_panel_width")
        on_ui(lambda: app._toggle_movie_panel())
        _hid3 = on_ui(lambda: (not app._panel_shown(), str(app._panel_strip) in [str(x) for x in app._table_pane.panes()]))
        _set3 = mc.SETTINGS.get("movie_panel_shown")
        on_ui(lambda: app.run_action("toggle_panel"))
        _back3 = on_ui(lambda: app._panel_shown())
        check("L3: Hide ⟩ / Ctrl+B hides the panel (a slim '‹' strip stays), remembered in movie_panel_shown; shown again",
              _hid3 == (True, True) and _set3 is False and _back3 and mc.SETTINGS.get("movie_panel_shown") is True,
              (_hid3, _set3, _back3))
        check("L3: Ctrl+B is a registry shortcut (part movies)",
              "<Control-b>" in mc.ACTIONS["toggle_panel"]["keys"] and mc.ACTIONS["toggle_panel"]["part"] == "movies")
        mc.SETTINGS["movie_panel_width"] = 500
        on_ui(lambda: app._on_pane_dblclick())
        check("L3: a double-click on the divider resets the width to 320 px", mc.SETTINGS.get("movie_panel_width") == 320,
              mc.SETTINGS.get("movie_panel_width"))
        if _w0 is not None:
            mc.SETTINGS["movie_panel_width"] = _w0
        _np3 = dict(_r0 or {}, poster_exists=False, folder_exists=False, movie_name="No Poster Movie")
        def _np3_read():
            if app._panel_after is not None:
                app.tk.call("after", "cancel", app._panel_after); app._panel_after = None
            app._movie_panel.show([_np3], [_kids3[0]])
            return app._movie_panel._poster.winfo_reqwidth(), app._movie_panel._poster.cget("text")
        _pw3 = on_ui(_np3_read)
        check("L3: a movie without poster keeps a 150 px poster box with 'no poster' (not 150 characters wide)",
              _pw3[0] <= 160 and _pw3[1] == "no poster", _pw3)
        on_ui(lambda: (app._movie_panel._poster.configure(text="loading…"),
                       app._movie_panel._set_poster(app._movie_panel._gen, mc._PILImage.new("RGB", (30, 45)))))
        check("L3: a poster that has loaded carries no 'loading…' text", on_ui(lambda: app._movie_panel._poster.cget("text")) == "",
              on_ui(lambda: app._movie_panel._poster.cget("text")))
        on_ui(lambda: (app.tree.selection_set(()), app.update()))

        # ── v0.19.2 F4a: Fix image dialog + batch, in-process ──────────────────   ### NEW v0.19.2 F4a ###
        _f4u = os.path.join(_TMP, "f4", "Dialog Fix (2002)"); os.makedirs(_f4u, exist_ok=True)
        open(os.path.join(_f4u, "Dialog Fix (2002).mkv"), "wb").write(b"\0" * 64)
        _pic4(700, 1000).save(os.path.join(_f4u, "poster.jpg"), "JPEG", quality=90)
        _row4 = scan(_f4u, use_ffprobe=False)
        _act4, _why4 = on_ui(lambda: app._ctx_fix_action("images", [_row4]))
        # ### NEW v0.19.5 B116 ### the old wording is gone from everything the user sees
        _src116 = open(mc.__file__, encoding="utf-8").read()
        check("B116: window titles and the Backup label say 'Fix Image Proportions / Size'; the old wording stays only in comments",
              mc.IMAGE_FIX_ACTION == "Fix Image Proportions / Size" and '(self, "🛠  Fix image proportions' not in _src116 and 'IMAGE_FIX_ACTION = "Fix image' not in _src116 and 'messagebox.showinfo("Fix image"' not in _src116
              and '"🛠  Fix image —' not in _src116)
        check("F4: the right-click slot of B57 is filled ('Fix image proportions / size…' enabled)", callable(_act4) and _why4 is None, _why4)
        _dlg4 = on_ui(lambda: app._fix_images_for([_row4]))
        wait_for(lambda: _dlg4._src is not None and bool(_dlg4._opts), 10)
        _rb4 = on_ui(lambda: {w.cget("value"): str(w.cget("state")) for w in _dlg4._sizes_fr.winfo_children()})
        check("F4 dialog: the default size is the nearest tier (720p); ✕ sizes are disabled; Keep current size offered",
              on_ui(_dlg4._size.get) == "720p" and _rb4.get("4K") == "disabled" and _rb4.get("1080p") == "normal" and "keep" in _rb4, (on_ui(_dlg4._size.get), _rb4))
        wait_for(lambda: "×" in on_ui(lambda: _dlg4._after_lbl.cget("text")), 10)
        check("F4 dialog: before / after preview drawn, after = target size", on_ui(lambda: _dlg4._after_lbl.cget("text")) == "666×1000"
              and on_ui(lambda: len(_dlg4._cv["before"].find_all())) == 1 and on_ui(lambda: len(_dlg4._cv["after"].find_all())) == 1,
              on_ui(lambda: _dlg4._after_lbl.cget("text")))
        check("F4 dialog: AI upscale disabled until the upscaler is installed and tested (F4b)", on_ui(lambda: str(_dlg4._ai_cb.cget("state"))) == "disabled")
        check("F4 dialog: Esc closes", on_ui(lambda: bool(_dlg4.bind("<Escape>"))))
        _pr4u = dict(mc.SETTINGS.get("image_fix_prefs") or {})                     ### NEW v0.19.2 F4b ###
        try:
            if sys.platform == "win32": check("F4b dialog: installed but untested → 'Test again' button", on_ui(lambda: _dlg4._ai_btn.cget("text")) == "Test again",
                  on_ui(lambda: _dlg4._ai_btn.cget("text")))
            mc.SETTINGS["image_fix_prefs"] = dict(_pr4u, ai_test="ok")
            on_ui(lambda: (_dlg4._ai_refresh(), _dlg4._ai_var.set(True), _dlg4._build_sizes()))
            _m4u = on_ui(lambda: {o["key"]: o["mark"] for o in _dlg4._opts})
            if sys.platform == "win32": check("F4b dialog: AI ready → the box is enabled, the button hidden, and 1080p (×1.43) becomes ✓ (1440p ⚠)",
                  on_ui(lambda: str(_dlg4._ai_cb.cget("state"))) == "normal" and not on_ui(_dlg4._ai_btn.winfo_manager)
                  and _m4u.get("1080p") == "ok" and _m4u.get("1440p") == "warn", _m4u)
        finally:
            mc.SETTINGS["image_fix_prefs"] = _pr4u
            on_ui(lambda: (_dlg4._ai_var.set(False), _dlg4._ai_refresh(), _dlg4._build_sizes()))
        if sys.platform == "win32": check("F4b dialog: back to untested → the button is shown again", on_ui(_dlg4._ai_btn.winfo_manager) == "pack")
        _boxes.clear()
        check("F4b: 'Download upscaler…' asks first (No → nothing downloaded)", on_ui(lambda: app._download_upscaler(parent=_dlg4)) is None)
        on_ui(lambda: (_dlg4._method_cb.set(mc._ifx.METHOD_LABEL["crop_center"]), _dlg4._build_sizes()))
        check("F4 dialog: another method → sizes rebuilt for its corrected size (crop 700×1050 → 666×1000 still nearest)", on_ui(_dlg4._size.get) == "720p")
        _fo4 = []
        _ofp4 = app._fetch_poster_folder
        app._fetch_poster_folder = lambda rows: _fo4.append(rows)
        try:
            on_ui(_dlg4._find_online); wait_for(lambda: bool(_fo4), 5)
        finally:
            app._fetch_poster_folder = _ofp4
        check("F4 dialog: 'Find a better one online' closes it and opens Fetch Poster/Folder for that movie", _fo4 == [[_row4]] and not on_ui(_dlg4.winfo_exists))
        _dlg4 = on_ui(lambda: app._fix_images_for([_row4]))
        wait_for(lambda: _dlg4._src is not None and bool(_dlg4._opts), 10)
        _boxes.clear()
        on_ui(_dlg4._apply)
        wait_for(lambda: any("Written" in str(b) for b in _boxes) or any(b[0] == "error" for b in _boxes), 15)
        check("F4 dialog: Apply writes the fixed poster (666×1000) and reports it", _dlg4.applied and mc.probe_image(os.path.join(_f4u, "poster.jpg"))["w"] == 666
              and any("Written" in str(b) for b in _boxes), [_dlg4.applied, _boxes])
        check("F4 dialog: the chosen method is remembered (image_fix_prefs)", (mc.SETTINGS.get("image_fix_prefs") or {}).get("poster_method") == "blur")
        # batch: preview first, then the run
        _f4b = os.path.join(_TMP, "f4", "Batch Fix (2003)"); os.makedirs(_f4b, exist_ok=True)
        open(os.path.join(_f4b, "Batch Fix (2003).mkv"), "wb").write(b"\0" * 64)
        _pic4(1100, 1500).save(os.path.join(_f4b, "poster.jpg"), "JPEG", quality=90)
        _rowb4 = scan(_f4b, use_ffprobe=False)
        _boxes.clear(); app._image_fix_preview = None
        on_ui(lambda: app.after(0, lambda: app._fix_images_for([_rowb4, scan(_f4u, use_ffprobe=False)])))
        wait_for(lambda: getattr(app, "_image_fix_preview", None) is not None, 10)
        _pvt4 = on_ui(lambda: app._image_fix_preview._raw if hasattr(app._image_fix_preview, "_raw") else "")
        on_ui(lambda: app._image_fix_preview._run())
        wait_for(lambda: any(re.search(r"\d+ images? fixed", str(b)) for b in _boxes), 20)
        check("F4 batch: preview lists the movies, Run fixes with ✓ sizes only (1100×1500 → 1000×1500)",
              any("1 image fixed" in str(b) for b in _boxes) and mc.probe_image(os.path.join(_f4b, "poster.jpg"))["w"] == 1000
              and "Batch Fix (2003)" in str(_pvt4), (_boxes, str(_pvt4)[:300]))
        check("F4: Tools menu has the All Movies entry", any(t[1] == mc.IMAGE_FIX_ALL_LABEL for t in on_ui(lambda: _flat57(app._tools_menu))))

        # ── v0.19.2 B51: every Toplevel gets the dark title bar and both icons ──   ### NEW v0.19.2 B51 ###
        if sys.platform == "win32":   # dark title bar / WM_GETICON need the Windows API; CI runs on Linux
            import ctypes as _ct51
            def _dwm_dark51(w):
                v = _ct51.c_int(-1)
                _ct51.windll.dwmapi.DwmGetWindowAttribute(_ct51.c_void_p(mc._win_hwnd(w)), 20, _ct51.byref(v), _ct51.sizeof(v))
                return v.value
            def _icons51(w):
                u = _ct51.windll.user32
                u.SendMessageW.restype = _ct51.c_void_p
                u.SendMessageW.argtypes = [_ct51.c_void_p, _ct51.c_uint, _ct51.c_void_p, _ct51.c_void_p]
                h = mc._win_hwnd(w)
                return u.SendMessageW(h, 0x007F, 0, 0), u.SendMessageW(h, 0x007F, 1, 0)     # WM_GETICON small / big
            _tl51 = on_ui(lambda: tk.Toplevel(app))
            wait_for(lambda: getattr(_tl51, "_mc_decorated", False), 5)
            _ic51 = on_ui(lambda: _icons51(_tl51))
            check("B51: a new window is decorated on <Map> — dark title bar, small icon ≠ big icon",
                  getattr(_tl51, "_mc_decorated", False) and on_ui(lambda: _dwm_dark51(_tl51)) == 1 and _ic51[0] and _ic51[1] and _ic51[0] != _ic51[1], _ic51)
            _tip51 = on_ui(lambda: (lambda t: (t.wm_overrideredirect(True), t)[1])(tk.Toplevel(app)))
            time.sleep(0.3)
            check("B51: tooltips (override-redirect windows) are left alone", not getattr(_tip51, "_mc_decorated", False))
            mc.SETTINGS["dark_title_bar"] = False
            try:
                on_ui(app._apply_title_bars)
                check("B51: the setting OFF is applied live to the open windows", on_ui(lambda: _dwm_dark51(_tl51)) == 0)
            finally:
                mc.SETTINGS["dark_title_bar"] = True
                on_ui(app._apply_title_bars)
            check("B51: …and ON again", on_ui(lambda: _dwm_dark51(_tl51)) == 1)
            on_ui(lambda: (_tl51.destroy(), _tip51.destroy()))

        # ── v0.19.2 B52: dark menu row, same menus ────────────────────────────   ### NEW v0.19.2 B52 ###
        def _entries52(m):
            end = m.index("end")
            return [[m.type(i), "" if m.type(i) == "separator" else m.entrycget(i, "label"),
                     "" if m.type(i) == "separator" else m.entrycget(i, "accelerator")] for i in range(0 if end is None else end + 1)]
        _before52 = json.load(open(os.path.join(os.path.dirname(mc.__file__), "plan_assets", "B52_menu_entries_before.json"), encoding="utf-8"))
        _ren52 = {"🔧  Tools (Editor / FFmpeg / Backdrop)": "🔧  Editor & FFmpeg", "🔑  API Keys (fetchers)": "🔑  API Keys",   # v0.19.4 B108 (D4, intended)
                  "🌐  Browser Selection": "🌐  Browser", "🌍  Language OK?": "🌍  Language", "🏷  NFO-XML Tags": "🏷  NFO / XML",
                  "💾  Save Scan Results": "💾  Save Scan Results…", "📂  Open Scan Results": "📂  Open Scan Results…",
                  "⭐  Sync Ratings Online — All Movies": "⭐  Sync Ratings Online — All Movies…",
                  "🔗  Normalize Sources — All Movies": "🔗  Normalize Sources — All Movies…",
                  "🔎  Search Sources — All Movies": "🔎  Search Sources — All Movies…",
                  "✅  Verify IMDb/TMDb IDs — All Movies": "✅  Verify IMDb/TMDB IDs — All Movies…",
                  "🛠  Auto Repair — All Movies": "🛠  Auto Repair — All Movies…",
                  "🎬  Normalize Genres — All Movies": "🎬  Normalize Genres — All Movies…",
                  "🔍  Run Improvements Check — All Movies": "🔍  Run Improvements Check — All Movies…",
                  "🖼  Fix: Copy poster.jpg → folder.jpg — All Movies with differences": "🖼  Copy poster.jpg → folder.jpg — All Movies with Differences…",
                  "🛠  Fix Image Proportions / Size — All Movies with image warnings…": "🖼  Fix Image Proportions / Size — All Movies with Image Warnings…",
                  "📂  Open logs folder": "📂  Open Logs Folder"}
        _before52 = {k: [[e[0], _ren52.get(e[1], e[1]), e[2]] for e in v] for k, v in _before52.items()}
        # v0.19.4 B74 (intended): the Help topics were replaced (13 new ones); the Help menu is compared without them
        _topics52 = {"🚀  Getting Started", "📊  Table & Columns", "🔄  Scans & Libraries", "🖱  Actions & Tools", "⭐  Ratings & Genres",
                     "🎵  Audio & Images", "⚙️  Settings", "⌨  Shortcuts"} | {l for l, _x in mc._help.HELP_TABS}
        _is_topic52 = lambda lbl: lbl.replace("   (F1)", "") in _topics52
        _before52["Help"] = [e for e in _before52.get("Help", []) if not _is_topic52(e[1])]
        _now52 = on_ui(lambda: {k.capitalize(): [e for e in _entries52(m) if not (k == "help" and _is_topic52(e[1])) and e[1] not in (mc.CHECK_UPDATES_LABEL, mc.NOT_DUP_MANAGE_LABEL, mc.NFO_RENAME_ALL_LABEL,
                                                                                        getattr(mc, "CHECK_COLL_LABEL", None), getattr(mc, "FIX_COLL_ALL_LABEL", None),
                                                                                        getattr(mc, "CREATE_COLL_ALL_LABEL", None))]   # B50, v0.19.3 B64, B73, v0.19.4 B110b add one entry each (intended)
                                for k, m in app._menus.items()})
        check("B52: Settings / Tools / Help keep every entry, label and order (snapshot taken before the change)", _now52 == _before52,
              [(k, len(_now52.get(k, [])), len(v)) for k, v in _before52.items()])
        check("B52: no native menu bar any more; a dark row with 'Settings ▾', 'Tools ▾', 'Help ▾'",
              on_ui(lambda: app["menu"]) == "" and on_ui(lambda: [app._menu_btns[k].cget("text") for k in ("settings", "tools", "help")]) == ["Settings ▾", "Tools ▾", "Help ▾"]
              and on_ui(lambda: app._menu_row.cget("bg")) == mc.MENU_ROW_BG and app._help_menu is app._menus["help"] and app._tools_menu is app._menus["tools"])
        _posted52 = []
        for _k52, _m52 in app._menus.items():
            _m52.tk_popup = (lambda k: (lambda x, y: _posted52.append(k)))(_k52)
        try:
            on_ui(lambda: _fire(app.tree, "<Alt-h>"))
            on_ui(lambda: _fire(app.tree, "<Alt-T>"))
            on_ui(lambda: _fire(app.tree, "<F10>"))
            on_ui(lambda: app._menu_btns["help"].event_generate("<Button-1>"))
        finally:
            for _m52 in app._menus.values():
                del _m52.tk_popup
        check("B52: Alt+H / Alt+T / F10 / a click post Help / Tools / Settings / Help", _posted52 == ["help", "tools", "settings", "help"], _posted52)

        # ── v0.19.2 B50 / B56: the update dialog, the automatic check ──────────   ### NEW v0.19.2 B50 / B56 ###
        _new50 = {"status": "newer", "version": "0.20.0", "url": mc.RELEASES_URL, "error": "",
                  "assets": [{"name": "MediaClinic-0.20.0-win64.zip", "browser_download_url": "https://github.com/x.zip", "digest": "sha256:" + "a" * 64}]}
        _ud50 = on_ui(lambda: mc.UpdateDialog(app, _new50))
        check("B50/B56: from source the dialog offers Open download page / Skip / Close, no 'Download and install'",
              sorted(_ud50.buttons) == ["close", "open", "skip"] and on_ui(lambda: bool(_ud50.bind("<Escape>"))))
        on_ui(_ud50.destroy)
        _fz50 = mc._is_frozen
        mc._is_frozen = lambda: True
        try:
            _ud50 = on_ui(lambda: mc.UpdateDialog(app, _new50))
            check("B56: as the exe, 'Download and install' is the first button", list(_ud50.buttons)[0] == "install", list(_ud50.buttons))
            on_ui(_ud50.destroy)
        finally:
            mc._is_frozen = _fz50
        on_ui(lambda: app._update_link(_new50))
        _ud50 = on_ui(lambda: mc.UpdateDialog(app, _new50))
        on_ui(_ud50._skip)
        check("B50: Skip this version saves it and removes the status-bar link", mc.SETTINGS.get("skipped_version") == "0.20.0"
              and on_ui(lambda: app._sb_update.cget("text")) == "")
        _sv50 = {k: mc.SETTINGS.get(k) for k in ("check_updates", "last_update_check", "skipped_version")}
        _calls50 = []
        _fake50 = lambda: (_calls50.append(1), _new50)[1]
        try:
            mc.SETTINGS["check_updates"] = False
            check("B50 auto: OFF → no check", on_ui(lambda: app._auto_update_check(_fake50)) is False and _calls50 == [])
            mc.SETTINGS.update(check_updates=True, last_update_check=datetime.date.today().isoformat())
            check("B50 auto: once a day (already checked today → no check)", on_ui(lambda: app._auto_update_check(_fake50)) is False and _calls50 == [])
            mc.SETTINGS.update(last_update_check="2026-01-01", skipped_version="0.20.0")
            on_ui(lambda: app._auto_update_check(_fake50)); wait_for(lambda: mc.SETTINGS.get("last_update_check") == datetime.date.today().isoformat(), 10)
            check("B50 auto: a skipped version shows no link; the date is recorded", _calls50 == [1] and on_ui(lambda: app._sb_update.cget("text")) == "")
            mc.SETTINGS.update(last_update_check="2026-01-01", skipped_version="")
            _boxes.clear()
            on_ui(lambda: app._auto_update_check(_fake50)); wait_for(lambda: on_ui(lambda: app._sb_update.cget("text")) != "", 10)
            check("B50 auto: a newer version → '⬆ Update available: v0.20.0' in the status bar, never a pop-up",
                  on_ui(lambda: app._sb_update.cget("text")) == "⬆ Update available: v0.20.0" and not _boxes, _boxes)
        finally:
            mc.SETTINGS.update(_sv50)
            on_ui(lambda: app._update_link(None))
        # install through the app (fake release, base folder in temp; "Start it now?" → No, "Open the folder?" → No)
        os.environ["MEDIACLINIC_UPDATE_API"] = _rel56("0.19.8")
        try:
            _rel56b = mc.check_latest_release()
            app._update_result = None
            on_ui(lambda: app._install_update(_rel56b, base_dir=_base56))
            wait_for(lambda: getattr(app, "_update_result", None) is not None, 20)
        finally:
            os.environ.pop("MEDIACLINIC_UPDATE_API", None)
        check("B56: Download and install from the dialog → the new folder, then 'Start it now?' is asked",
              app._update_result and app._update_result[1] is None and os.path.isfile(os.path.join(_base56, "MediaClinic 0.19.8", "MediaClinic.exe")),
              app._update_result)
        _boxes.clear()
        check("B56: starting a missing exe → an error, the app keeps running", on_ui(lambda: app._start_new_version(os.path.join(_TMP, "nope.exe"))) is False
              and any(b[0] == "error" for b in _boxes))
        _boxes.clear()                                       # the provoked error box is not a real one

        # ── v0.19.2 B49: the About tab ─────────────────────────────────────────   ### NEW v0.19.2 B49 ###
        _hd49 = on_ui(lambda: mc.open_help(app, tab=len(mc._help.HELP_TABS)))
        _txt49 = on_ui(lambda: _hd49._about_text.get("1.0", "end"))
        check("B49: About shows the version, the four links' texts and not the old address",
              f"Version {mc.APP_VERSION}" in _txt49 and all(x in _txt49 for x in ("www.mediaclinic.dev", "github.com/junqueirach/mediaclinic", "r/MediaClinic", "info@mediaclinic.dev"))
              and "junqueira.ch@gmail.com" not in _txt49, _txt49[:400])
        _rows49 = [l for l in _txt49.splitlines() if l.strip().split("\t")[0] in ("Created by", "Website", "GitHub", "Reddit", "Contact")]
        check("B49: every identity row has exactly one tab character (aligned values)", len(_rows49) == 5 and all(l.count("\t") == 1 for l in _rows49), _rows49)
        check("B49: the feature bullets match what v0.19.2 ships", all(f"•  {b}" in _txt49 for b in mc.ABOUT_FEATURES) and len(mc.ABOUT_FEATURES) == 6)
        _op49 = []
        _wbo49 = mc.webbrowser.open
        mc.webbrowser.open = lambda u, *a, **k: (_op49.append(u), not u.startswith("mailto:"))[1]
        try:
            for _t49 in ("link_web", "link_github", "link_reddit", "link_mail", "link_issue", "link_releases"):
                on_ui(lambda t=_t49: _hd49._about_click(_hd49._about_links[t]))
        finally:
            mc.webbrowser.open = _wbo49
        check("B49: each link opens its URL (website https, GitHub, Reddit, mailto, issues, releases)",
              _op49 == [mc.APP_WEBSITE, mc.APP_GITHUB, mc.APP_REDDIT, "mailto:info@mediaclinic.dev", mc.APP_GITHUB + "/issues", mc.APP_GITHUB + "/releases"]
              and mc.APP_WEBSITE == "https://www.mediaclinic.dev", _op49)
        check("B49: no mail program → the address is copied and the status bar says so",
              on_ui(app.clipboard_get) == "info@mediaclinic.dev" and "Email address copied: info@mediaclinic.dev" in on_ui(lambda: app._sb_action.cget("text")))
        on_ui(_hd49._about_copy_version)
        check("B49: version line (source / exe, Windows build, Python, Tk) with Copy; Check for updates button",
              on_ui(app.clipboard_get) == mc.version_line() and "running from source" in mc.version_line() and " · Python " in mc.version_line()
              and " · Tk " in mc.version_line() and on_ui(lambda: _hd49._about_update_btn.cget("text")).strip() == "⬆ Check for updates")
        check("B49: the old address is nowhere in the program, README or Help",
              not any("junqueira.ch@gmail.com" in open(os.path.join(os.path.dirname(mc.__file__), f), encoding="utf-8").read()
                      for f in (os.path.basename(mc.__file__), "README.md", "help_text.py")))
        on_ui(_hd49._close)

        # ── v0.19.3 B60: tooltip, menu entries, chooser, several-movie preview ──   ### NEW v0.19.3 B60 ###
        _iid60 = next(i for i, d in app._item_map.items() if d["subfolder"] == "Title Mismatch")
        _tip60 = on_ui(lambda: app._tooltip(_iid60, mc.COL_MOVIE_NAME)) or ""
        check("B60: the movie-name tooltip shows the mismatch with both titles",
              "Health:" in _tip60 and 'NFO <title> "Cidade de Deus"' in " ".join(_tip60.split())
              and 'XML <LocalTitle> "City of God"' in " ".join(_tip60.split()), _tip60)
        _row60 = app._item_map[_iid60]
        _menu60 = on_ui(lambda: (app._build_ctx_menu(_iid60, _row60, [_row60]), _flat57(app._ctx))[1])
        _ent60 = {l: st for _dp, l, st, _m, _i in _menu60}
        check("B60: right-click → Metadata 'Make titles the same…' enabled, and '⚠ Fix issues' has the title entry",
              _ent60.get("🔤  Make titles the same (NFO ↔ XML)…") == "normal"
              and any(l.startswith("Local title differs") for l in _ent60), [l for l in _ent60 if "title" in l.lower()])
        _ok60 = next(d for d in app._item_map.values() if d["subfolder"] == "Perfect Movie")
        _menu60b = on_ui(lambda: (app._build_ctx_menu(_iid60, _ok60, [_ok60]), _flat57(app._ctx))[1])
        check("B60: …greyed '(local titles match)' for a movie without the problem",
              any(l == "🔤  Make titles the same (NFO ↔ XML)… (local titles match)" and st == "disabled" for _dp, l, st, _m, _i in _menu60b))
        # the chooser on a temp copy (the library fixture stays as it is)
        _d60u = os.path.join(_TMP, "b60u", "Title Mismatch"); shutil.copytree(os.path.dirname(_row60["nfo_path"]), _d60u)
        _row60u = scan(_d60u, use_ffprobe=False)
        _n60u = open(_row60u["nfo_path"], "rb").read(); _x60u = open(_row60u["xml_path"], "rb").read()
        _rf60 = []
        _orig_rf60 = app._schedule_refresh
        app._schedule_refresh = lambda p, need_ffprobe=False: _rf60.append(list(p))
        try:
            _dlg60 = on_ui(lambda: app._title_sync_for([_row60u]))
            check("B60: one movie → the chooser with the NFO and XML values", on_ui(lambda: isinstance(_dlg60, mc.TitleSyncDialog)
                  and set(_dlg60._choices) >= {"nfo", "xml"} and _dlg60._choices["xml"] == "City of God"))
            on_ui(lambda: _fire(_dlg60, "<Escape>"))
            check("B60: Esc closes the chooser and writes nothing",
                  not on_ui(lambda: bool(_dlg60.winfo_exists())) and open(_row60u["nfo_path"], "rb").read() == _n60u
                  and open(_row60u["xml_path"], "rb").read() == _x60u and not _rf60)
            _dlg60 = on_ui(lambda: app._title_sync_for([_row60u]))
            on_ui(lambda: (_dlg60._var.set("xml"), _dlg60._apply()))
            check("B60: Apply writes the chosen title into NFO <title> (XML already has it), refresh asked",
                  mc.get_primary_titles(_row60u["nfo_path"], _row60u["xml_path"]) == ("City of God", "City of God")
                  and open(_row60u["xml_path"], "rb").read() == _x60u and _rf60 == [[_row60u["subfolder_path"]]], _rf60)
            # several movies: preview, then the run
            _d60m = [os.path.join(_TMP, "b60m", n) for n in ("Alpha One (2001)", "Beta Two (2002)")]
            for _p, (_nt, _xt) in zip(_d60m, (("Alpha One", "Alpha Uno"), ("Beta Dos", "Beta Two"))):
                os.makedirs(_p, exist_ok=True)
                _nfo(os.path.join(_p, "movie.nfo"), _nt, year="2001", original="Zeta"); _xml(os.path.join(_p, "movie.xml"), _xt, year="2001", original="Zeta")
            _rows60m = [scan(p, use_ffprobe=False) for p in _d60m]
            _boxes.clear(); app._title_sync_preview = None
            on_ui(lambda: app.after(0, lambda: app._title_sync_for(_rows60m)))
            wait_for(lambda: getattr(app, "_title_sync_preview", None) is not None, 10)
            _pv60 = on_ui(lambda: app._title_sync_preview._raw if hasattr(app._title_sync_preview, "_raw") else "")
            on_ui(lambda: app._title_sync_preview._run())
            wait_for(lambda: any("local titles made the same" in str(b) for b in _boxes), 20)
            check("B60: several movies → preview (folder-name rule per movie), Run writes them",
                  "Alpha One" in str(_pv60) and 'becomes "Alpha One"' in str(_pv60) and 'becomes "Beta Two"' in str(_pv60)
                  and mc.get_primary_titles(_rows60m[0]["nfo_path"], _rows60m[0]["xml_path"]) == ("Alpha One", "Alpha One")
                  and mc.get_primary_titles(_rows60m[1]["nfo_path"], _rows60m[1]["xml_path"]) == ("Beta Two", "Beta Two")
                  and any("2 movies" in str(b) for b in _boxes), (str(_pv60)[:400], _boxes))
        finally:
            app._schedule_refresh = _orig_rf60

        # ── v0.19.3 B62: minimise and keep working; busy movie; Stop; watchdog ──   ### NEW v0.19.3 B62 ###
        if sys.platform == "win32":   # minimising a window needs a window manager; the CI display has none
            _d62u = os.path.join(_TMP, "b62u", "Slow Fix (2005)"); os.makedirs(_d62u, exist_ok=True)
            open(os.path.join(_d62u, "Slow Fix (2005).mkv"), "wb").write(b"\0" * 64)
            _jpeg(os.path.join(_d62u, "poster.jpg"), 900, 1000)
            _row62 = scan(_d62u, use_ffprobe=False)
            _orig_fix62 = mc.apply_image_fix
            _calls62 = []
            def _slow_fix62(row, kind, method, target, upscale=None, batch_ref=None, cancel=None, copy_to=None):
                _calls62.append((kind, copy_to))                    # v0.19.3 B66: copy_to
                t = time.monotonic()
                while time.monotonic() - t < 3.0:
                    if cancel and cancel():
                        raise mc.ImageFixStopped()
                    time.sleep(0.05)
                return [row["poster_path"]]
            mc.apply_image_fix = _slow_fix62
            _orig_rf62 = app._schedule_refresh
            app._schedule_refresh = lambda p, need_ffprobe=False: None
            try:
                _dl62 = on_ui(lambda: mc.ImageFixDialog(app, _row62, "poster"))
                wait_for(lambda: on_ui(lambda: _dl62._src is not None), 10)
                check("B62: the Fix image window is not transient (own taskbar button, minimise button)",
                      on_ui(lambda: str(_dl62.transient())) == "")
                _boxes.clear()
                on_ui(_dl62._apply)
                on_ui(_dl62.iconify)
                _rt62 = []
                for _ in range(5):
                    _t = time.monotonic(); on_ui(lambda: app.tree.get_children()); _rt62.append(time.monotonic() - _t)
                    time.sleep(0.2)
                check("B62: while Apply runs (window minimised) the movie list answers at once",
                      on_ui(lambda: _dl62.state()) == "iconic" and max(_rt62) < 0.25
                      and "you can minimise this window" in on_ui(lambda: _dl62._work_lbl.cget("text")), [round(x, 3) for x in _rt62])
                on_ui(lambda: app._fetch_poster_folder([_row62]))
                check("B62: another artwork action on that movie waits ('Fix image is still running for this movie')",
                      any("still running for this movie" in str(b) for b in _boxes) and _pkey62(_row62) in app._busy_fix, _boxes)
                wait_for(lambda: not app._busy_fix, 15)
                # ### MODIFIED v0.19.3 B68 (intended change) ### the pop-up is back, besides the status line
                check("B62/B68: done while minimised → a status-bar line AND the pop-up ('Written: …' with the movie name)",
                      "Fix image done: Slow Fix" in on_ui(lambda: app.stats_var.get())
                      and any(b[0] == "info" and "Written" in str(b) and "Slow Fix" in str(b) for b in _boxes),
                      (on_ui(lambda: app.stats_var.get()), _boxes))
                # Stop
                _dl62 = on_ui(lambda: mc.ImageFixDialog(app, _row62, "poster"))
                wait_for(lambda: on_ui(lambda: _dl62._src is not None), 10)
                on_ui(_dl62._apply)
                mc.messagebox.askyesno = lambda *a, **k: True
                try:
                    on_ui(_dl62._close)
                finally:
                    mc.messagebox.askyesno = lambda *a, **k: False
                _boxes.clear()
                wait_for(lambda: not app._busy_fix, 10)
                check("B62: Stop ends the fix (nothing written) and closes the window",
                      not on_ui(lambda: bool(_dl62.winfo_exists())) and not app._busy_fix)
                time.sleep(0.3)
                check("B68: a stopped fix shows no pop-up", not any(b[0] in ("info", "error") for b in _boxes), _boxes)
                # B68: an error while minimised → the error pop-up as well
                def _fail_fix68(*a, **k):
                    time.sleep(0.5)
                    raise RuntimeError("disk full")
                mc.apply_image_fix = _fail_fix68
                _boxes.clear()
                _dl68 = on_ui(lambda: mc.ImageFixDialog(app, _row62, "poster"))
                wait_for(lambda: on_ui(lambda: _dl68._src is not None), 10)
                on_ui(_dl68._apply)
                on_ui(_dl68.iconify)
                wait_for(lambda: not app._busy_fix, 10)
                time.sleep(0.3)
                check("B68: an error while minimised → status line and the error pop-up ('Not changed: disk full')",
                      any(b[0] == "error" and "disk full" in str(b) for b in _boxes)
                      and "Fix image not done" in on_ui(lambda: app.stats_var.get()), (_boxes, on_ui(lambda: app.stats_var.get())))
                on_ui(lambda: _dl68.destroy() if _dl68.winfo_exists() else None)
                mc.apply_image_fix = _slow_fix62
                # closing the app while a fix runs asks; No keeps it open
                app._busy_fix.add("x:\\fake")
                on_ui(app._on_app_close)
                check("B62: closing the app while a fix runs asks (No = the app stays open)", on_ui(lambda: bool(app.winfo_exists())))
                app._busy_fix.discard("x:\\fake")
            finally:
                mc.apply_image_fix = _orig_fix62
                app._schedule_refresh = _orig_rf62
        # the UI watchdog: a 6 s stall is logged with the thread stacks, a 1 s one is not
        import logging as _lg62
        _rec62 = []
        class _H62(_lg62.Handler):
            def emit(self, r):
                _rec62.append(r.getMessage())
        _h62 = _H62(); mc.logger.addHandler(_h62)
        try:
            on_ui(lambda: time.sleep(6.5), 30)
            time.sleep(2.0)
            _busy62 = [m for m in _rec62 if m.startswith("UI busy for")]
            _n62 = len(_busy62)
            on_ui(lambda: time.sleep(1.2), 30)
            time.sleep(2.0)
            check("B62: watchdog — a 6 s stall is written to app.log with every thread's stack; a 1 s stall is not",
                  _n62 == 1 and "--- thread MainThread" in _busy62[0] and "--- thread ui-watchdog" in _busy62[0]
                  and len([m for m in _rec62 if m.startswith("UI busy for")]) == 1
                  and any(m.startswith("UI responsive again") for m in _rec62), [m[:80] for m in _rec62])
        finally:
            mc.logger.removeHandler(_h62)

        # ── v0.19.3 B63: the sort row, headings, presets, kept after a scan ─────   ### NEW v0.19.3 B63 ###
        _sp0 = on_ui(lambda: list(app._sort_spec))
        _cbs63 = on_ui(lambda: [w for w in app._sort_levels_fr.winfo_children() if isinstance(w, mc.ttk.Combobox)])
        check("B63: the sort row has a 'Sort by' column box and the summary line",
              len(_cbs63) == len(_sp0) and on_ui(lambda: _cbs63[0].get()) in mc.sort_labels().values()
              and on_ui(lambda: app.sort_var.get()).startswith("Sorted by "), on_ui(lambda: app.sort_var.get()))
        on_ui(lambda: app._apply_sort([{"key": "movie_name", "dir": "asc"}]))
        on_ui(app._sort_add); on_ui(app._sort_add)
        check("B63: '+ then by' adds levels up to 3 (then the button goes)",
              len(app._sort_spec) == 3 and not any(isinstance(w, mc.tk.Button) and "then by" in str(w.cget("text"))
                                                   for w in on_ui(lambda: app._sort_levels_fr.winfo_children())), app._sort_spec)
        on_ui(lambda: app._sort_set_key(1, "movie_name"))
        check("B63: choosing a column used by another level moves it (no column twice)",
              [l["key"] for l in app._sort_spec].count("movie_name") == 1, app._sort_spec)
        on_ui(lambda: app._apply_sort([{"key": "rating", "dir": "high"}, {"key": "year", "dir": "newest"}]))
        on_ui(lambda: app._sort_remove(1))
        _hd63 = on_ui(lambda: app.tree.heading("rating")["text"])
        check("B63: ✕ removes a level; the heading shows ▼1", app._sort_spec == [{"key": "rating", "dir": "high"}] and _hd63.endswith("▼1"), (_hd63, app._sort_spec))
        _vis63 = on_ui(lambda: [app._item_map[i] for i in app.tree.get_children()])
        _rated63 = [d["rating_value"] for d in _vis63 if (d.get("rating_value") or -1) >= 0 and d.get("rating_status") != mc.STATUS_MISSING]
        check("B63: the table follows (highest rating first)", (not _rated63) or _vis63[0].get("rating_value") == max(_rated63),
              (_vis63[0].get("rating_value") if _vis63 else None, max(_rated63) if _rated63 else None))
        # heading: single click sorts after the double-click window; a double-click only auto-sizes
        _as63 = []
        _o_as63 = app._auto_size_col
        app._auto_size_col = lambda c: _as63.append(c)
        try:
            app._hdr_click_time.clear()
            on_ui(lambda: (setattr(app, "_col_resize_just_ended", False), setattr(app, "_hdr_shift", False), app._on_header_dblclick_guard("year")))
            time.sleep(0.6); on_ui(lambda: None)
            _after1 = list(app._sort_spec)
            app._hdr_click_time.clear()
            on_ui(lambda: (setattr(app, "_col_resize_just_ended", False), app._on_header_dblclick_guard("votes"), app._on_header_dblclick_guard("votes")))
            time.sleep(0.6); on_ui(lambda: None)
            _after2 = list(app._sort_spec)
            on_ui(lambda: (setattr(app, "_col_resize_just_ended", False), setattr(app, "_hdr_shift", True), app._on_header_dblclick_guard("genre")))
            time.sleep(0.6); on_ui(lambda: setattr(app, "_hdr_shift", False))
            _after3 = list(app._sort_spec)
        finally:
            app._auto_size_col = _o_as63
        check("B63: a heading click sorts by it; a double-click auto-sizes without sorting; Shift+click adds a level",
              _after1[0]["key"] == "year" and _after2 == _after1 and _as63 == ["votes"]
              and [l["key"] for l in _after3][-1] == "genre" and len(_after3) == len(_after1) + 1, (_after1, _after2, _after3, _as63))
        # presets: Ctrl+n, save, rename, delete, the menu
        on_ui(lambda: _fire(app.tree, "<Control-Key-4>"))
        if sys.platform == "win32": check("B63: Ctrl+4 applies the 4th preset (Best rated)", app._sort_spec == mc._se.clean_spec(_se63.BUILTIN_PRESETS[3]["levels"]), app._sort_spec)
        _sv63 = (list(mc.SETTINGS.get("sort_presets") or []))
        mc.SETTINGS["sort_presets"] = []
        try:
            _pd63 = on_ui(lambda: mc.SortPresetDialog(app, "save"))
            on_ui(lambda: (_pd63._name_var.set("Best rated"), _pd63._save()))
            _why63 = on_ui(lambda: _pd63._msg.cget("text"))
            on_ui(lambda: (_pd63._name_var.set("Brazilian films"), _pd63._save()))
            check("B63: Save preset — a built-in name is refused, a new name is saved with the levels",
                  "exists" in _why63 and [p["name"] for p in mc.SETTINGS["sort_presets"]] == ["Brazilian films"]
                  and mc.SETTINGS["sort_presets"][0]["levels"] == [dict(l) for l in app._sort_spec], (_why63, mc.SETTINGS["sort_presets"]))
            _menu63 = [l for _d, l, _s, _m, _i in on_ui(lambda: _flat57(app._build_presets_menu()))]
            check("B63: the Presets menu lists built-in and own presets with Ctrl+n, Save, Rename / delete, Back to Movie Name",
                  any(l.startswith("Problems first") for l in _menu63) and any(l.startswith("Brazilian films") for l in _menu63)
                  and "Save current sort as preset…" in _menu63 and "Back to Movie Name (A → Z)" in _menu63, _menu63)
            on_ui(lambda: _fire(app.tree, "<Control-Key-7>"))
            if sys.platform == "win32": check("fix 16: Ctrl+7 applies the built-in preset By collection name",
                  app._sort_spec == mc._se.clean_spec(mc._se.BUILTIN_PRESETS[6]["levels"]) and mc._se.BUILTIN_PRESETS[6]["name"] == "By collection name",
                  app._sort_spec)
            on_ui(lambda: _fire(app.tree, "<Control-Key-8>"))
            check("B63: Ctrl+8 applies the first own preset (Ctrl+7 since v0.19.4 fix 16)", app._sort_spec == mc._se.clean_spec(mc.SETTINGS["sort_presets"][0]["levels"]))
            _mg63 = on_ui(lambda: mc.SortPresetDialog(app, "manage"))
            on_ui(lambda: (_mg63._lb.selection_set(0), _mg63._name_var.set("BR films"), _mg63._rename()))
            _ren63 = [p["name"] for p in mc.SETTINGS["sort_presets"]]
            on_ui(lambda: (_mg63._lb.selection_set(0), _mg63._delete()))
            check("B63: Rename / Delete own presets", _ren63 == ["BR films"] and mc.SETTINGS["sort_presets"] == [], _ren63)
            on_ui(_mg63.destroy)
        finally:
            mc.SETTINGS["sort_presets"] = _sv63
        # the sort is kept after a scan and saved for the next start
        on_ui(lambda: app._apply_sort([{"key": "year", "dir": "oldest"}]))
        check("B63: scans and restores keep the user's sort (no reset to Movie Name)",
              all("_apply_default_sort()" not in inspect.getsource(f) for f in (mc.App._scan_done, mc.App._restore_last_session))
              and mc.SETTINGS["sort_spec"] == [{"key": "year", "dir": "oldest"}] and mc.SETTINGS["sort_option"] == "Year (older first)")
        on_ui(app._apply_default_sort)
        check("B63: 'Back to Movie Name (A → Z)'", app._sort_spec == [{"key": "movie_name", "dir": "asc"}])

        # ── v0.19.3 B64: "Not a duplicate" in the right-click menu ───────────────   ### NEW v0.19.3 B64 ###
        _dupr = next((d for d in app._results if d.get("duplicate_of")), None)
        _okr = next((d for d in app._results if not d.get("duplicate_of")), None)
        check("B64: the self-test library has a flagged movie to work with", _dupr is not None and _okr is not None)
        if _dupr is not None:
            _iid64 = next(i for i, d in app._item_map.items() if d is _dupr) if any(d is _dupr for d in app._item_map.values()) else None
            _m64 = on_ui(lambda: (app._build_ctx_menu(_iid64, _dupr, [_dupr]), _flat57(app._ctx))[1])
            _m64b = on_ui(lambda: (app._build_ctx_menu(_iid64, _okr, [_okr]), _flat57(app._ctx))[1])
            check("B64: right below the title line — 'Not a duplicate…' enabled for a flagged movie, greyed otherwise",
                  _m64[1][1] == mc.NOT_DUP_LABEL and _m64[1][2] == "normal"
                  and _m64b[1][1] == mc.NOT_DUP_LABEL + " (no duplicate found)" and _m64b[1][2] == "disabled",
                  ([x[1:3] for x in _m64[:3]], [x[1:3] for x in _m64b[:3]]))
            _was64 = list(_dupr["duplicate_of"])
            _res64 = on_ui(lambda: app._not_duplicate_for([_dupr]))
            if isinstance(_res64, mc.NotDuplicateDialog):
                on_ui(_res64._ok)
            check("B64: marked → the warning is gone at once (no rescan) and the status bar says so",
                  not _dupr["duplicate_of"] and not any(x.startswith("Possible duplicate") for x in _dupr.get("health_reasons", []))
                  and "Marked" in on_ui(lambda: app.stats_var.get()), (_was64, _dupr["duplicate_of"], on_ui(lambda: app.stats_var.get())))
            mc._detect_duplicates(app._results)
            check("B64: …and stays gone after the duplicates are found again (saved in not_duplicates.json)",
                  not _dupr["duplicate_of"] and os.path.isfile(mc._sc.NOT_DUP_PATH) and len(mc.not_dup_pairs()) >= 1)
            check("B64: the Duplicate Movies Report lists the marks", "Marked as not duplicates" in mc.format_duplicates_report(app._results))
            _m64c = on_ui(lambda: (app._build_ctx_menu(_iid64, _dupr, [_dupr]), _flat57(app._ctx))[1])
            check("B64: the same line now offers 'Undo …'", _m64c[1][1].startswith("↺  Undo 'not a duplicate'"), _m64c[1][1])
            _ud64 = on_ui(lambda: mc.NotDuplicateDialog(app, _dupr, "undo"))
            on_ui(lambda: ([v.set(False) for v, _x, _p in _ud64._vars], _ud64._ok()))
            check("B64: Undo (untick) → flagged again", sorted(_dupr["duplicate_of"]) == sorted(_was64) and not mc.not_dup_pairs(),
                  (_dupr["duplicate_of"], mc.not_dup_pairs()))
            # the manage window
            on_ui(lambda: app._mark_not_dup([(_dupr, _p, "Same IMDb ID") for _p, _w in mc.duplicate_partners(_dupr, app._results)]))
            _mg64 = on_ui(lambda: mc.NotDuplicateManageDialog(app))
            _n64 = on_ui(lambda: len(_mg64._tv.get_children()))
            on_ui(lambda: (_mg64._tv.selection_set(_mg64._tv.get_children()), _mg64._remove()))
            check("B64: Tools → Manage marks lists the pairs; Remove takes them out (the warning returns)",
                  _n64 >= 1 and not mc.not_dup_pairs() and _dupr["duplicate_of"], (_n64, mc.not_dup_pairs()))
            on_ui(_mg64.destroy)
            check("B64: the Tools menu has the Manage entry", any(t[1] == mc.NOT_DUP_MANAGE_LABEL for t in on_ui(lambda: _flat57(app._tools_menu))))
            check("B64: Clear All does not touch not_duplicates.json",
                  "not_dup" not in inspect.getsource(mc.App._clear_all) and "NOT_DUP" not in inspect.getsource(mc.App._clear_all))
        mc._NOT_DUP["pairs"] = []

        # ── v0.19.3 B65: Subtitles window → OpenSubtitles.org ───────────────────   ### NEW v0.19.3 B65 ###
        _ns65 = dict(next(iter(app._item_map.values())), subs_internal=[], subs_external=[], subs_summary="—")
        _calls65 = []
        _o65 = app._open_opensubtitles
        app._open_opensubtitles = lambda d: _calls65.append(d)
        try:
            _sd65 = on_ui(lambda: mc.SubtitleDialog(app, _ns65["subfolder"], _ns65))
            on_ui(lambda: _sd65._osub_btn.invoke())
            check("B65: the Subtitles window opens OpenSubtitles.org for the movie (same action as the menu)",
                  "OpenSubtitles" in on_ui(lambda: _sd65._osub_btn.cget("text")) and len(_calls65) == 1 and _calls65[0] is _ns65, _calls65)
            on_ui(lambda: _fire(_sd65, "<Escape>"))
            check("B65: Esc still closes it", not on_ui(lambda: bool(_sd65.winfo_exists())))
        finally:
            app._open_opensubtitles = _o65
        _m65 = on_ui(lambda: (app._build_ctx_menu(None, _ns65, [_ns65]), _flat57(app._ctx))[1])
        check("B65: right-click 'Subtitles…' is enabled for a movie without subtitles",
              any(l == "💬  Subtitles…" and st == "normal" for _d, l, st, _m, _i in _m65), [x[1:3] for x in _m65 if "Subtitles" in x[1]])

        # ── v0.19.3 I6: previews before writing ──────────────────────────────────   ### NEW v0.19.3 I6 ###
        def _pv6(start):
            app._last_preview = None
            on_ui(lambda: app.after(0, start))
            wait_for(lambda: getattr(app, "_last_preview", None) is not None and on_ui(lambda: bool(app._last_preview.winfo_exists())), 15)
            return app._last_preview
        # Copy poster → folder for several movies: preview, close = nothing, Run = copied
        _rows6 = []
        for _n6 in ("Copy Six A", "Copy Six B"):
            _p6 = os.path.join(_TMP, "i6", _n6); os.makedirs(_p6, exist_ok=True)
            _jpeg(os.path.join(_p6, "poster.jpg"), 1000, 1500); _jpeg(os.path.join(_p6, "folder.jpg"), 400, 600)
            open(os.path.join(_p6, _n6 + ".mkv"), "wb").write(b"\0" * 64)
            _rows6.append(scan(_p6, use_ffprobe=False))
        def _rd6(pth):                                   # v0.19.4: the app replaces folder.jpg atomically; a read during
            try:                                         # the swap is refused by Windows (Errno 13) — "not yet", not a crash
                return open(pth, "rb").read()
            except OSError:
                return None
        def _same6(r):
            a, b = _rd6(os.path.join(r["subfolder_path"], "folder.jpg")), _rd6(r["poster_path"])
            return a is not None and a == b
        _f6 = lambda: [_same6(r) for r in _rows6]
        _orf6 = app._schedule_refresh
        app._schedule_refresh = lambda p, need_ffprobe=False: None
        try:
            _pv = _pv6(lambda: app._copy_poster_to_folder(list(_rows6)))
            _t6 = on_ui(lambda: _pv._raw if hasattr(_pv, "_raw") else "")
            on_ui(_pv.destroy); time.sleep(0.5)
            _none6 = _f6()
            _pv = _pv6(lambda: app._copy_poster_to_folder(list(_rows6)))
            _boxes.clear(); on_ui(_pv._run)
            wait_for(lambda: all(_f6()), 15)
            check("I6: Copy poster → folder (2 movies) — preview lists both; closing writes nothing; Run copies",
                  "Copy Six A" in str(_t6) and "Copy Six B" in str(_t6) and _none6 == [False, False] and all(_f6()), (str(_t6)[:200], _none6, _f6()))
        finally:
            app._schedule_refresh = _orf6
        # Normalize Sources — All and Normalize Genres — All: the run starts only on Run
        for _name6, _attr6, _start6 in (("Normalize Sources", "_normalize_sources_for", app._normalize_sources_all),
                                        ("Normalize Genres", "_normalize_genres_for", app._normalize_genres_all)):
            _called6 = []
            setattr(app, _attr6, lambda rows, *a, **k: _called6.append(len(rows)))
            try:
                _boxes.clear()
                _pv = _pv6(_start6)
                on_ui(_pv.destroy); time.sleep(0.3)
                _n6a = list(_called6)
                _pv = _pv6(_start6)
                on_ui(_pv._run); time.sleep(0.3)
                check(f"I6: {_name6} — All: preview first; closing does nothing, Run starts it", _n6a == [] and len(_called6) == 1, (_n6a, _called6))
            finally:
                delattr(app, _attr6)
        # Sync Ratings: fetched first, preview, Run writes (no second question)
        _d6r = os.path.join(_TMP, "i6", "Rated Six"); os.makedirs(_d6r, exist_ok=True)
        _nfo(os.path.join(_d6r, "movie.nfo"), "Rated Six", rating="7.3", votes="1200", tmdb="761234")
        _xml(os.path.join(_d6r, "movie.xml"), "Rated Six", rating="7.3", votes="1200", tmdb="761234")
        _r6r = scan(_d6r, use_ffprobe=False)
        _o6r = (mc._fetch_tmdb_rating, mc._fetch_omdb_rating)
        mc._fetch_tmdb_rating = lambda tid, key: ("8.1", "4321")
        mc._fetch_omdb_rating = lambda iid, key: (None, None)
        _asked6 = []
        app._ask_ratings_dialog = lambda *a, **k: (_asked6.append(1), {"choice": "tmdb", "apply_all": True})[1]
        app._schedule_refresh = lambda p, need_ffprobe=False: None
        try:
            for _go6 in (False, True):
                _boxes.clear(); app._last_preview = None
                threading.Thread(target=lambda: app._sync_ratings_worker_run([_r6r], "k", "", None, True), daemon=True).start()
                wait_for(lambda: any(isinstance(w, mc._PreviewRunDialog) for w in on_ui(lambda: app.winfo_children())), 20)
                _pv = on_ui(lambda: next(w for w in app.winfo_children() if isinstance(w, mc._PreviewRunDialog)))
                _t6r = on_ui(lambda: _pv._raw if hasattr(_pv, "_raw") else "")
                on_ui(_pv._run if _go6 else _pv.destroy)
                wait_for(lambda: any("Ratings Sync Complete" in str(b) for b in _boxes), 20)
                if not _go6:
                    check("I6: Sync Ratings — the preview shows current → new; closing writes nothing",
                          "7.3 / 1200 votes  →  8.1 / 4321 votes  (TMDB)" in str(_t6r) and "<rating>7.3</rating>" in open(_r6r["nfo_path"], encoding="utf-8").read()
                          and any("nothing was written" in str(b) for b in _boxes), (str(_t6r)[:200], _boxes))
                else:
                    check("I6: Sync Ratings — Run writes what the preview showed (no second question)",
                          "8.1" in open(_r6r["nfo_path"], encoding="utf-8").read() and len(_asked6) == 2, (_asked6, _boxes))
        finally:
            mc._fetch_tmdb_rating, mc._fetch_omdb_rating = _o6r
            del app._ask_ratings_dialog
            app._schedule_refresh = _orf6
        _boxes.clear()

        # ── v0.19.3 I7: the _BatchJob helper ─────────────────────────────────────   ### NEW v0.19.3 I7 ###
        _bj = [os.path.join(_TMP, "i7", f"Job {i}") for i in range(3)]
        for _p in _bj:
            os.makedirs(_p, exist_ok=True); open(os.path.join(_p, "movie.nfo"), "w", encoding="utf-8").write("<movie/>")
        _items7 = [{"movie_name": f"Job {i}", "subfolder": f"Job {i}", "subfolder_path": p} for i, p in enumerate(_bj)]
        _rf7, _fin7 = [], {}
        _orf7 = app._schedule_refresh
        app._schedule_refresh = lambda p, need_ffprobe=False: _rf7.append(list(p))
        try:
            def _step7(job, it):
                if it["movie_name"] == "Job 1":
                    raise RuntimeError("disk full")
                assert job.backup(it["movie_name"], os.path.join(it["subfolder_path"], "movie.nfo"))
                job.changed += [it["subfolder_path"], it["subfolder_path"]]
                return True
            _job7 = on_ui(lambda: mc._BatchJob(app, _items7, "I7 test job", progress_title="Testing…"))
            _had_prog7 = _job7.prog is not None
            _job7.run(_step7, lambda job: _fin7.update(done=job.done, errors=list(job.errors)))
            wait_for(lambda: "done" in _fin7, 15)
            _runs7 = [r for r in sc.list_backup_runs(_BK) if r.get("action") == "I7 test job"] if hasattr(sc, "list_backup_runs") else ["?"]
            check("I7: _BatchJob — progress window from 3 items, errors named, done counted, ONE refresh with each folder once, labelled backups",
                  _had_prog7 and _fin7 == {"done": 2, "errors": ["Job 1: disk full"]}
                  and _rf7 == [[_bj[0], _bj[2]]] and len(_runs7) == 1, (_fin7, _rf7, len(_runs7)))
        finally:
            app._schedule_refresh = _orf7

        # ── v0.19.3 B66: the "Also copy the result to …" tickbox ────────────────   ### NEW v0.19.3 B66 ###
        _d66ui = os.path.join(_TMP, "b66ui", "Tick Box (2004)"); os.makedirs(_d66ui, exist_ok=True)
        open(os.path.join(_d66ui, "Tick Box (2004).mkv"), "wb").write(b"\0" * 64)
        _jpeg(os.path.join(_d66ui, "poster.jpg"), 700, 1000); _jpeg(os.path.join(_d66ui, "folder.jpg"), 690, 1000)
        _jpeg(os.path.join(_d66ui, "fanart.jpg"), 1920, 800)
        _row66 = scan(_d66ui, use_ffprobe=False)
        _dl66 = on_ui(lambda: mc.ImageFixDialog(app, _row66, "poster"))
        try:
            _st66 = on_ui(lambda: (str(_dl66._copy_cb.cget("text")), bool(_dl66._copy_cb.winfo_manager()),
                                   _dl66._copy_var.get(), _dl66._copy_target()))
            on_ui(lambda: (_dl66._kind.set("fanart"), _dl66._kind_changed()))
            _fa66 = on_ui(lambda: (bool(_dl66._copy_cb.winfo_manager()), _dl66._copy_target()))
            on_ui(lambda: (_dl66._kind.set("folder"), _dl66._kind_changed()))
            _fo66 = on_ui(lambda: (str(_dl66._copy_cb.cget("text")), _dl66._copy_target()))
            on_ui(lambda: _dl66._copy_var.set(False))
            _un66 = on_ui(_dl66._copy_target)
            on_ui(lambda: (_dl66._kind.set("poster"), _dl66._kind_changed()))
            _back66 = on_ui(lambda: _dl66._copy_var.get())
            # the window's position: above the buttons, below the AI line
            # ### MODIFIED v0.19.5 I22 ### wait for the layout: on a busy PC the row was read before Tk had placed it (y = 0)
            def _ys66f():
                _dl66.update()
                return _dl66._copy_fr.winfo_rooty(), _dl66._apply_btn.master.winfo_rooty()   # on the screen: they can sit in different parents
            wait_for(lambda: on_ui(_ys66f)[1] > 0, 10)
            _ys66 = on_ui(_ys66f)
        finally:
            on_ui(lambda: _dl66.destroy())
        check("B66: Fix image window — poster: 'Also copy the result to folder.jpg', ticked; folder: '… to poster.jpg'; "
              "fanart: no box; unticked → False; ticked again when the image changes; above the buttons",
              _st66 == ("Also copy the result to folder.jpg", True, True, "folder") and _fa66 == (False, False)
              and _fo66 == ("Also copy the result to poster.jpg", "poster") and _un66 is False and _back66 is True
              and _ys66[0] < _ys66[1], (_st66, _fa66, _fo66, _un66, _back66, _ys66))

        # ── v0.19.3 B69: Health at the top of the Sort by list, warnings first ──   ### NEW v0.19.3 B69 ###
        _spec69 = [dict(l) for l in app._sort_spec]
        try:
            _cb69 = on_ui(lambda: [w for w in app._sort_levels_fr.winfo_children() if isinstance(w, mc.ttk.Combobox)][0])
            _vals69 = on_ui(lambda: list(_cb69.cget("values")))
            on_ui(lambda: app._sort_set_key(0, "health"))
            _d69a = on_ui(lambda: app._sort_spec[0]["dir"])
            on_ui(lambda: app._sort_toggle(0))
            wait_for(lambda: on_ui(lambda: app._refresh_idle()) if hasattr(app, "_refresh_idle") else True, 5)
            time.sleep(0.5)
            _hs69 = on_ui(lambda: [app._item_map[i].get("health_status") for i in app.tree.get_children() if i in app._item_map])
            _first69 = next((h for h in _hs69 if h != "ok"), None)
        finally:
            on_ui(lambda: app._apply_sort(_spec69))
        check("B69: the list's first entries are Health, Number of issues; Health → 'Errors first', one click → 'Warnings first' (warnings at the top)",
              _vals69[:2] == ["Health", "Number of issues"] and _d69a == "errors" and _first69 in (None, "warning")
              and ("warning" not in _hs69 or _hs69.index("warning") < min([_hs69.index("error")] if "error" in _hs69 else [len(_hs69)])),
              (_vals69[:3], _d69a, _hs69[:12]))

        # ── v0.19.3 B72: "Update View" after the last sort level ───────────────   ### NEW v0.19.3 B72 ###
        _spec72 = [dict(l) for l in app._sort_spec]
        _rt72 = []
        _orig_rt72 = app._refresh_table
        try:
            def _order72():
                ws = app._sort_levels_fr.winfo_children()
                return [str(w.cget("text")).strip() for w in ws if isinstance(w, mc.tk.Button)]
            on_ui(lambda: app._apply_sort([{"key": "movie_name", "dir": "asc"}]))
            _o1 = on_ui(_order72)
            on_ui(app._sort_add)
            _o2 = on_ui(_order72)
            on_ui(app._sort_add)
            _o3 = on_ui(_order72)
            app._refresh_table = lambda *a, **k: _rt72.append(1)
            on_ui(lambda: app._render_sort_row())
            on_ui(lambda: app._update_view_btn.invoke())
        finally:
            app._refresh_table = _orig_rt72
            on_ui(lambda: app._apply_sort(_spec72))
        check("B72: '↺ Update View' is the last control of the sort row (1, 2 and 3 levels — it moves with the levels) and refreshes the view",
              all(o and o[-1] == "↺ Update View" for o in (_o1, _o2, _o3)) and "+ then by" in _o1 and "+ then by" not in _o3
              and _o3.count("✕") == 2 and _rt72 == [1], (_o1, _o2, _o3, _rt72))

        # ── v0.19.3 B70: layout — sort block centred, equal gaps (B70_GAP), legend on the filter row, FFprobe switch ──   ### NEW v0.19.3 B70 ###
        def _geo70():
            app.update_idletasks()
            blk = app._sort_block
            sl = blk.master.pack_slaves()
            i = sl.index(blk)
            above, below = sl[i - 1], sl[i + 1]
            fi = sl.index(app._filter_row)
            cnt = next(w for w in sl[fi + 1:] if w is not app.progress_frame)
            y = lambda w: w.winfo_y(); b = lambda w: w.winfo_y() + w.winfo_height()
            btn_mid = app._sort_btns.winfo_y() + app._sort_btns.winfo_height() / 2
            return {"above": y(blk) - b(above), "below": y(below) - b(blk), "below_is_filter": below is app._filter_row,
                    "filter_to_counters": y(cnt) - b(app._filter_row),
                    "btn_off": abs(btn_mid - blk.winfo_height() / 2),
                    "legend_in_filter": app._legend.master is app._filter_row,
                    "picker_has_tickbox": any(isinstance(w, mc.tk.Checkbutton) and "FFprobe" in str(w.cget("text"))
                                              for w in above.winfo_children())}
        _g70 = on_ui(_geo70)
        _G70 = mc.B70_GAP                                         # 16 px since the user's check on 2026-10-23
        check(f"B70: {_G70} px above and below the sort block (folder row / filter row) and from the filter row to the counters; "
              "Presets / Auto-size centred on the block; legend on the filter row; no FFprobe tickbox in the button row",
              _G70 - 1 <= _g70["above"] <= _G70 + 1 and _G70 - 1 <= _g70["below"] <= _G70 + 1 and abs(_g70["above"] - _g70["below"]) <= 1
              and _G70 - 1 <= _g70["filter_to_counters"] <= _G70 + 2 and _G70 == 16 and _g70["below_is_filter"] and _g70["btn_off"] <= 2
              and _g70["legend_in_filter"] and not _g70["picker_has_tickbox"], _g70)
        _fp0 = on_ui(lambda: bool(app._use_ffprobe.get()))
        try:
            _st70a = on_ui(lambda: (app._fp_state.cget("text"), app._ff_frame.master is app._ff_chip))
            on_ui(app._toggle_ffprobe_switch)
            _st70b = on_ui(lambda: (bool(app._use_ffprobe.get()), app._fp_state.cget("text"), mc.SETTINGS.get("use_ffprobe")))
            on_ui(lambda: app._use_ffprobe.set(_fp0))              # set from elsewhere → the switch follows
            _st70c = on_ui(lambda: app._fp_state.cget("text"))
        finally:
            on_ui(lambda: (app._use_ffprobe.set(_fp0), app._on_ffprobe_toggle()))
        check("B70: FFprobe switch in the FFmpeg chip — shows On/Off, a click flips the variable and the setting, follows the variable",
              _st70a == ("On" if _fp0 else "Off", True) and _st70b == (not _fp0, "On" if not _fp0 else "Off", not _fp0)
              and _st70c == ("On" if _fp0 else "Off"), (_fp0, _st70a, _st70b, _st70c))

        # ── v0.19.3 B73: Rename NFO for Kodi — dialog, preview, Auto Repair step ──   ### NEW v0.19.3 B73 ###
        _rf73 = []
        _orig_rf73 = app._schedule_refresh
        app._schedule_refresh = lambda p, need_ffprobe=False: _rf73.append(list(p))
        try:
            _du73 = os.path.join(_TMP, "b73ui", "Dialog Film (2007)"); os.makedirs(_du73, exist_ok=True)
            open(os.path.join(_du73, "Dialog.Film.2007.mkv"), "wb").write(b"\0" * 64)
            _nfo(os.path.join(_du73, "Dialog Film (2007).nfo"), "Dialog Film", year="2007", imdb="tt7730007", tmdb="773007")
            _ru73 = scan(_du73, use_ffprobe=False)
            _boxes.clear()
            _dlg73 = on_ui(lambda: app._nfo_rename_for([_ru73]))
            _st73 = on_ui(lambda: (_dlg73._mode.get(), [m for m, *_x in _dlg73._plan["choices"]]))
            on_ui(_dlg73._apply)
            wait_for(lambda: os.path.isfile(os.path.join(_du73, "Dialog.Film.2007.nfo")), 10)
            wait_for(lambda: any(b[0] == "info" and "Renamed" in str(b) for b in _boxes), 10)
            check("B73: one movie → the dialog ('<video>.nfo' selected, movie.nfo offered); Rename renames, refresh asked, pop-up",
                  _st73 == ("video", ["video", "movie"]) and not os.path.exists(os.path.join(_du73, "Dialog Film (2007).nfo"))
                  and _rf73 == [[_du73]] and any("Dialog.Film.2007.nfo" in str(b) for b in _boxes), (_st73, _rf73, _boxes))
            # several → preview, then the run
            _dm73 = []
            for _n in ("Batch One (2008)", "Batch Two (2009)"):
                _p = os.path.join(_TMP, "b73ui", _n); os.makedirs(_p, exist_ok=True)
                open(os.path.join(_p, _n.replace(" ", ".") + ".mkv"), "wb").write(b"\0" * 64)
                _nfo(os.path.join(_p, _n + ".nfo"), _n.split(" (")[0], year="2008")
                _dm73.append(_p)
            _rows73 = [scan(p, use_ffprobe=False) for p in _dm73]
            _boxes.clear(); app._nfo_rename_preview = None
            on_ui(lambda: app.after(0, lambda: app._nfo_rename_for(_rows73)))
            wait_for(lambda: getattr(app, "_nfo_rename_preview", None) is not None, 10)
            on_ui(lambda: app._nfo_rename_preview._run())
            wait_for(lambda: any("NFO(s) renamed" in str(b) for b in _boxes), 20)
            check("B73: several movies → preview, Run renames each to <video>.nfo ('2 NFO(s) renamed')",
                  all(os.path.isfile(os.path.join(p, os.path.basename(p).replace(" ", ".") + ".nfo")) for p in _dm73)
                  and any("2 NFOs renamed" in str(b) for b in _boxes), (_boxes, [os.listdir(p) for p in _dm73]))
            # Auto Repair step (never the video)
            _da73 = os.path.join(_TMP, "b73ui", "Repair Film (2010)"); os.makedirs(_da73, exist_ok=True)
            open(os.path.join(_da73, "Repair.Film.mkv"), "wb").write(b"\0" * 64)
            _nfo(os.path.join(_da73, "Repair Film (2010).nfo"), "Repair Film", year="2010")
            _ra73 = scan(_da73, use_ffprobe=False)
            _bk73 = []
            _ctx73 = {"d": _ra73, "nfo": _ra73["nfo_path"], "xml": None, "name": "Repair Film", "backup": lambda: _bk73.append(1)}
            _ar73 = app._ar_nfo_name(_ctx73)
            check("B73: Auto Repair step — backup, NFO renamed to Repair.Film.nfo, the video untouched, ctx points to the new NFO",
                  _ar73[0] == "fixed" and "Repair.Film.nfo" in _ar73[1] and _bk73 == [1]
                  and sorted(os.listdir(_da73)) == ["Repair.Film.mkv", "Repair.Film.nfo"]
                  and os.path.basename(_ctx73["nfo"]) == "Repair.Film.nfo", (_ar73, os.listdir(_da73)))
            check("B73: Tools menu has 'Rename NFOs for Kodi — All Movies…'",
                  any(t[1] == mc.NFO_RENAME_ALL_LABEL for t in on_ui(lambda: _flat57(app._tools_menu))))
        finally:
            app._schedule_refresh = _orig_rf73

        # Settings dialog
        sd = on_ui(lambda: mc.SettingsDialog(app, tab=10))    # ### MODIFIED v0.19.1 I9 ### — Tk steps below via on_ui
        time.sleep(0.3)
        check("settings dialog: 12 tabs", len(on_ui(sd._nb.tabs)) == 12, len(on_ui(sd._nb.tabs)))
        def _sd_wheel29():                                              ### NEW v0.19.2 B29 ###
            sd.deiconify(); sd.update()
            reg = getattr(sd, "_mc_wheel", None)
            cv = [c for c in (reg or {}).get("canvases", []) if c.winfo_ismapped()]
            if not cv:
                return None, None
            c = cv[0]; c.yview_moveto(0); sd.update_idletasks()
            inner = c.winfo_children()[0]
            kid = (inner.winfo_children() or [inner])[min(3, len(inner.winfo_children()) - 1)]
            _fire(kid, "<MouseWheel>", delta=-240, x=2, y=2,
                  rootx=kid.winfo_rootx() + 2, rooty=kid.winfo_rooty() + 2)
            sd.update_idletasks()
            return len(reg["canvases"]), c.yview()
        _n29, _ysd29 = on_ui(_sd_wheel29)
        check("B29: the Settings tabs still scroll with the wheel (one Toplevel binding for every tab canvas)", bool(_n29) and _n29 >= 3 and _ysd29[0] > 0, (_n29, _ysd29))
        # ### NEW v0.19.5 SH-E7, E8, E21 ### the controls that did nothing are gone; their keys stay, ignored
        check("SH-E7, E8, E21: no control for Metadata source, Auto-fit, Show image size, Dark theme", not any(hasattr(sd, a) for a in ("_meta_src_var", "_auto_fit_var", "_show_image_size_var", "_dark_theme_var"))
              and all(k in DEFAULT_SETTINGS for k in ("metadata_source", "auto_fit_columns", "show_image_size", "dark_theme")))
        check("v0.19 SettingsDialog restored via hook", _near(_geom(sd), (900, 700, 90, 60)), _geom(sd))
        on_ui(app.withdraw)
        check("settings dialog: parallel workers + duplicate rule vars", hasattr(sd, "_scan_workers_var") and "duplicate_movie" in sd._hr_vars)
        check("settings dialog: new partial rules present", "imdb_id_partial" in sd._hr_vars and "tmdb_id_partial" in sd._hr_vars)
        check("I5: Tools tab has the 'Remember FFprobe results' checkbox (ON)", hasattr(sd, "_ffprobe_cache_var") and on_ui(sd._ffprobe_cache_var.get) is True)
        check("B24: Health Rules tab has the single-source / no-source severity combos", on_ui(lambda: (sd._hr_str_vars["single_source_level"].get(), sd._hr_str_vars["no_source_level"].get())) == ("error", "error"))
        reg = {lbl: idx for idx, lbl, _ in mc.SettingsDialog._TAB_REGISTRY}
        check("settings menu maps every entry to an existing tab", all(t in reg for _, _, t in mc._SETTINGS_MENU_ITEMS) and reg["Health Rules"] == 10 and reg["Ratings"] == 6)
        check("I10: Settings menu says 'API Keys' (B108, intended) and opens the API Keys tab (index 1)", [t for _, l, t in mc._SETTINGS_MENU_ITEMS if l == "API Keys"] == ["API Keys"] and reg["API Keys"] == 1 and not any("TMDB / OMDb" in l for _, l, _t in mc._SETTINGS_MENU_ITEMS))
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
        check("table health respects the disabled rule right after save", not any("IMDb ID present in one file" in x for x in by["Partial TMDB"]["health_reasons"]), by["Partial TMDB"]["health_reasons"])
        check("no rescan prompt for a rules-only change", not any("Update Scan" in str(b) for b in _boxes))

        # ── v0.19.4 B94: Save & Apply — save result checked, values applied only when all are valid ──  ### NEW v0.19.4 B94 ###
        _nfo94 = mc.SETTINGS["max_nfo_kb"]
        sd94 = on_ui(lambda: mc.SettingsDialog(app, tab=0))
        _cp94u = sc.CONFIG_PATH
        try:
            on_ui(lambda: sd94._max_nfo_kb_var.set(_nfo94 + 27))
            _boxes.clear()
            sc.CONFIG_PATH = _TMP                                  # a folder: settings.json cannot be written
            on_ui(sd94._save_close)
            sc.CONFIG_PATH = _cp94u
            check("B94: settings.json not written → the window stays open with 'Settings not saved', nothing applied",
                  on_ui(sd94.winfo_exists) and mc.SETTINGS["max_nfo_kb"] == _nfo94
                  and any(b[0] == "error" and b[1][0] == "Settings not saved" for b in _boxes), (_boxes, mc.SETTINGS["max_nfo_kb"]))
            _boxes.clear()
            on_ui(lambda: (sd94._tags_text.delete("1.0", "end"), sd94._tags_text.insert("1.0", "rating\tRating\tRating\t5%\n")))
            on_ui(sd94._save_close)
            def _tab94():
                c, p = sd94._tags_text, sd94._tags_text.master
                while p is not None and not isinstance(p, tk.ttk.Notebook):
                    c, p = p, p.master
                return p is not None and str(p.select()) == str(c)
            check("B94: a bad tag line ('5%') is named, its tab is shown, and NO value is applied (not even the valid ones)",
                  on_ui(sd94.winfo_exists) and mc.SETTINGS["max_nfo_kb"] == _nfo94 and on_ui(_tab94)
                  and any(b[0] == "error" and "Tag pairs: line 1: the tolerance '5%'" in str(b[1]) for b in _boxes), (_boxes, mc.SETTINGS["max_nfo_kb"]))
        finally:
            sc.CONFIG_PATH = _cp94u
            on_ui(lambda: sd94.destroy() if sd94.winfo_exists() else None)
        _boxes.clear()


        def _help_info():
            hd = mc.HelpDialog(app, tab=[l for l, _x in mc._help.HELP_TABS].index("⌨  Shortcuts"))   # v0.19.4 B74: tab 11 (intended)
            nb = [hd._nb] if isinstance(getattr(hd, "_nb", None), tk.ttk.Notebook) else []   # v0.19.4 B74: next to the contents list (intended)
            info = (bool(nb), len(nb[0].tabs()) if nb else 0,
                    [nb[0].tab(x, "text") for x in nb[0].tabs()] if nb else [],
                    nb[0].tab(nb[0].select(), "text") if nb else "")
            hd.destroy()
            return info
        _has_nb, _n_tabs, _tab_labels, _sel_label = on_ui(_help_info)
        check("help dialog: 14 tabs (13 topics + About; v0.19.4 B74, intended)", _has_nb and _n_tabs == len(mc._help.HELP_TABS) + 1 == 14, _n_tabs)
        # v0.19.1 B9/B10
        check("B9: no Version History tab; About last", "Version History" not in " ".join(_tab_labels) and _tab_labels[-1] == mc._help.ABOUT_LABEL, _tab_labels)
        check("B9: the Shortcuts tab selected", _sel_label.endswith("Shortcuts"), _sel_label)
        _menu_labels = on_ui(lambda: [app._help_menu.entrycget(i, "label") for i in range(app._help_menu.index("end") + 1)
                                      if app._help_menu.type(i) == "command"])
        # ### MODIFIED v0.19.2 B32 (intended) ### tool entries (Open logs folder, …) follow About after a separator
        _tab_part = _menu_labels[:_menu_labels.index(mc._help.ABOUT_LABEL) + 1] if mc._help.ABOUT_LABEL in _menu_labels else _menu_labels
        # ### MODIFIED v0.19.2 B50 (intended) ### "Check for updates…" sits right above About
        check("B50: Help menu has 'Check for updates…' right above About", _tab_part[-2:] == [mc.CHECK_UPDATES_LABEL, mc._help.ABOUT_LABEL], _tab_part[-3:])
        _tab_part = [m for m in _tab_part if m != mc.CHECK_UPDATES_LABEL]
        check("B9: Help menu = the Help tabs in the same order, About last (tool entries after it)", [m.replace("   (F1)", "") for m in _tab_part] == _tab_labels, (_menu_labels, _tab_labels))
        check("B32: Help menu has '📂 Open logs folder' after About", mc.OPEN_LOGS_LABEL in _menu_labels[len(_tab_part):], _menu_labels)
        _pop32 = []
        _orig_pop32 = mc._logs_popen
        mc._logs_popen = lambda cmd: _pop32.append(cmd)
        try:
            _i32 = on_ui(lambda: [i for i in range(app._help_menu.index("end") + 1) if app._help_menu.type(i) == "command"
                                  and app._help_menu.entrycget(i, "label") == mc.OPEN_LOGS_LABEL][0])
            on_ui(lambda: app._help_menu.invoke(_i32))
        finally:
            mc._logs_popen = _orig_pop32
        if sys.platform == "win32": check("B32: …it opens Explorer on logs\\ with app.log selected", _pop32 == [f'explorer /select,"{mc.LOG_PATH}"'] and os.path.isfile(mc.LOG_PATH), _pop32)
        check("B9: no 'Version History' anywhere in Help", not any("Version History" in tx for _l, tx in mc._help.HELP_TABS) and not hasattr(mc._help, "TAB_VERSION"))
        # v0.19.4 B74 (intended): the B10 fixed-width rule (72 characters, space indents) is retired — see B74 below
        _lint = {_l: mc._help.format_errors(_tx) for _l, _tx in mc._help.HELP_TABS if mc._help.format_errors(_tx)}
        check("B74: every Help tab parses with the markup — a title first, no space indents, no old markers, no unclosed ** / [[", not _lint, _lint)
        check("B10: help mentions the v0.19 features", all(k in " ".join(tx for _l, tx in mc._help.HELP_TABS) for k in ("Libraries…", "Auto Repair", "Verify", "Remove from list", "Enter ID…", "Shift+PageUp")))

        mc.SETTINGS["compact_mode"] = True; on_ui(app._on_settings_changed); time.sleep(0.5)
        _rh = on_ui(lambda: str(tk.ttk.Style(app).lookup("Treeview", "rowheight")))
        check("compact mode applied to Treeview style", _rh == str(mc.px(20)), _rh)   # px(): the display's scaling

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
import gc as _gc6
_gc6.collect()   # v0.19.3 I4: free the closed App's Tk variables HERE (main thread); collected in the
                 # restore worker they each wait ~1 s for a main loop that never runs again (test-only: two Apps)
_old115 = []                                                      ### NEW v0.19.5 B115 ###
mc._UI_QUEUE.put((lambda: _old115.append(1), ()))                 # an item a late worker of the closed window posted
app2 = mc.App(); app2.withdraw()
_UI_APP.append(app2)                                              ### NEW v0.19.1 I9 ###
def ui_tests2():
    try:
        wait_for(lambda: bool(app2._results), 10)
        on_ui(lambda: None)
        check("B115: an item left from the closed window does not run in the new window, and the new window's queue works", _old115 == [])
        check("fresh App restores results from last_results.json", len(app2._results) == shared.get("rows", -1), len(app2._results))
        check("restored rows get new default keys", all("nfo_title" in r and "scan_mtime" in r for r in app2._results))
        on_ui(lambda: (app2.deiconify(), app2.update())); time.sleep(0.3)
        _g2 = on_ui(lambda: (app2.geometry(), app2.withdraw())[0])
        check("v0.19 fresh App restores its saved geometry", _g2.startswith("1250x650"), _g2)
        check("B22: the pause saved in settings.json survives the restart (status bar)", "omdb" in _disk22 and wait_for(lambda: on_ui(lambda: app2._sb_pause.cget("text")).startswith("⚠ OMDb (IMDb data) paused"), 5), (_disk22, on_ui(lambda: app2._sb_pause.cget("text"))))
        mc._api_pauses_clear()
        on_ui(lambda: app2.after(60000, lambda: None))              ### NEW v0.19.2 B27 — must be cancelled by destroy() ###
        shared["after27"] = on_ui(lambda: len(app2.tk.splitlist(app2.tk.call("after", "info"))))
    except Exception:
        check("UI test 2 crashed", False, traceback.format_exc())
    finally:
        app2.after(0, app2.destroy)
threading.Thread(target=ui_tests2, daemon=True).start()
app2.mainloop()
try:                                                                ### NEW v0.19.2 B27 ###
    _left27 = app2.tk.splitlist(app2.tk.call("after", "info"))
except Exception as _e27:
    _left27 = [repr(_e27)]
check("B27: destroy() cancels every pending after() timer (no bgerror on a destroyed window)", shared.get("after27", 0) >= 1 and len(_left27) == 0, (shared.get("after27"), _left27))

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
    _gc6.collect()                                                # v0.19.3 I4 — see section 6
    app3 = mc.App(); app3.withdraw()
    _UI_APP.append(app3)
    _t3 = {}
    def ui_tests3():
        try:
            wait_for(lambda: len(app3._results) == 10000, 120)     # the automatic restore (after 200 ms) runs first
            ### MODIFIED v0.19.3 I4 ### the restore runs in a worker and fills the table in
            ### chunks: measure how long the window is blocked, how long until the table
            ### is complete, and the longest pause of the Tk loop meanwhile (intended change)
            # a heartbeat INSIDE the Tk loop (every 20 ms) measures the real pauses; the
            # helper thread only reads plain attributes, so it never adds Tk work itself
            _hb3 = {"on": None, "last": None, "load": [], "fill": []}
            def _beat3():
                now = time.perf_counter()
                if _hb3["on"] and _hb3["last"] is not None:
                    _hb3[_hb3["on"]].append(now - _hb3["last"])
                _hb3["last"] = now
                app3.after(20, _beat3)
            on_ui(lambda: app3.after(20, _beat3))
            for _run in range(3):                                   # best of 3 (timings vary a lot on this PC)
                def _timed():
                    app3._results = []; app3._item_map.clear(); app3.tree.delete(*app3.tree.get_children())
                    t0 = time.perf_counter()
                    app3._restore_last_session()
                    app3.update_idletasks()
                    return time.perf_counter() - t0
                _blk = on_ui(_timed, timeout=300)
                _hb3["load"], _hb3["fill"], _hb3["last"], _hb3["on"] = [], [], None, "load"
                _t0 = time.perf_counter()
                while time.perf_counter() - _t0 < 120:
                    if _hb3["on"] == "load" and len(app3._results) == 10000:
                        _hb3["on"] = "fill"
                    if len(app3._item_map) == 10000 and not getattr(app3, "_tbl_filling", True):
                        break
                    time.sleep(0.02)
                _hb3["on"] = None
                _tot = time.perf_counter() - _t0 + _blk
                _t3.setdefault("load_gaps", []).append(round(max(_hb3["load"] or [0]), 3))
                _t3.setdefault("fill_gaps", []).append(round(max(_hb3["fill"] or [0]), 3))
                if "s" not in _t3 or _tot < _t3["s"]:
                    _t3.update(s=_tot, block=_blk)
            _t3["gap"] = min(_t3["fill_gaps"])                     # best of 3, like the total
            _t3["load_gap"] = min(_t3["load_gaps"])
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
      f"  (table complete; rows {_t3.get('rows')}, table {_t3.get('shown')}) · window blocked {round(_t3.get('block') or 0, 3)} s"
      f" · longest Tk pause while loading {_t3.get('load_gap')} s (the worker reads last_results.json row by row)"
      f" · while filling {_t3.get('gap')} s (runs: load {_t3.get('load_gaps')}, fill {_t3.get('fill_gaps')})"
      f"   (v0.19.3 I4; v0.19.2: 4.5 s, all on the Tk thread)")
check("I4: the window is blocked < 0.25 s by the restore (load / parse / finalize run in a worker)", (_t3.get("block") or 9) < 0.25, _t3)
check("I4: while the 10,000 rows are put into the table the Tk loop never pauses longer than 0.5 s", (_t3.get("gap") or 9) < 0.5, _t3)
check("I4: while last_results.json is read and checked in the worker the Tk loop pauses less than 2 s (v0.19.2: 4.5 s blocked)",
      (_t3.get("load_gap") or 9) < 2.0, _t3)
check("I9: 10,000-row cache restored into results and table", _t3.get("rows") == 10000 and _t3.get("shown") == 10000, _t3)
check("I9: startup timing measured", isinstance(STARTUP_10K_SECONDS, float) and STARTUP_10K_SECONDS > 0, STARTUP_10K_SECONDS)

for fn, orig in zip(("showinfo", "showwarning", "showerror", "askyesno"), _orig_boxes):
    setattr(mc.messagebox, fn, orig)

# ### NEW v0.19.2 B42 ### — Clear All also clears the saved results
section("7b. Clear All empties last_results.json (v0.19.2 B42)")
_c42 = os.path.join(_TMP, "last_results_b42.json")
with open(_c42, "w", encoding="utf-8") as f:
    json.dump(_base_rows[:2], f)
_orig_cache42 = sc.RESULTS_CACHE_PATH
sc.RESULTS_CACHE_PATH = _c42
_orig_ign53 = sc.IGNORED_CACHE_PATH                            # ### NEW v0.19.2 B53 ### last_ignored.json too
sc.IGNORED_CACHE_PATH = os.path.join(_TMP, "last_ignored_b53.json")
sc.save_ignored({"scan_date": "2026-10-22 10:00", "items": [{"path": r"Z:\M\Show", "library_root": r"Z:\M", "kind": "series", "reason": "", "detail": ""}]})
_ask42 = mc.messagebox.askyesno
_r42 = {}
try:
    mc.messagebox.askyesno = lambda *a, **k: True
    app4 = mc.App(); app4.withdraw(); _UI_APP.append(app4)
    def ui_tests4():
        try:
            wait_for(lambda: len(app4._results) == 2, 20)
            _r42["before"] = len(app4._results)
            _r42["ign_loaded"] = len((app4._ignored_data or {}).get("items", []))
            on_ui(app4._clear_all, app_=app4)
            _r42["cache"] = sc.load_results_cache()
            _r42["ign_after"] = sc.load_ignored()
            _r42["table"] = len(kids(app4))
        except Exception:
            check("UI test 4 crashed", False, traceback.format_exc())
        finally:
            app4.after(0, app4.destroy)
    threading.Thread(target=ui_tests4, daemon=True).start()
    app4.mainloop()
    app5 = mc.App(); app5.withdraw(); _UI_APP.append(app5)
    def ui_tests5():
        try:
            time.sleep(1.0)                                  # the restore runs 200 ms after start
            _r42["restart"] = len(app5._results)
            _r42["ign_restart"] = app5._ignored_data
        finally:
            app5.after(0, app5.destroy)
    threading.Thread(target=ui_tests5, daemon=True).start()
    app5.mainloop()
finally:
    mc.messagebox.askyesno = _ask42
    sc.RESULTS_CACHE_PATH = _orig_cache42
    sc.IGNORED_CACHE_PATH = _orig_ign53
check("B42: Clear All empties the table AND last_results.json; a new start shows an empty table",
      _r42.get("before") == 2 and _r42.get("cache") == [] and _r42.get("table") == 0 and _r42.get("restart") == 0, _r42)
check("B53: last_ignored.json is loaded at start, emptied by Clear All, and stays empty after a restart",
      _r42.get("ign_loaded") == 1 and _r42.get("ign_after") == {} and _r42.get("ign_restart") == {}, _r42)

# ### NEW v0.19.2 B31 ### — test backups went to the temp folder only
section("8. self-test leaves the program's backup folder alone (v0.19.2 B31)")
_old31 = os.environ.pop("MEDIACLINIC_BACKUP_DIR")
try:
    _def31 = sc.get_backup_root(r"C:\Prog")
finally:
    os.environ["MEDIACLINIC_BACKUP_DIR"] = _old31
check("B31 / P5: MEDIACLINIC_BACKUP_DIR is honoured (app and settings_controller); without it backup\\ in the config folder",
      os.path.normcase(mc._BACKUP_ROOT) == os.path.normcase(_BK) and sc.get_backup_root(r"C:\Prog") == _BK
      and _def31 == os.path.join(sc.get_config_dir(), "backup"), (mc._BACKUP_ROOT, _def31))
_d5 = tempfile.mkdtemp(prefix="mc_p5_")
try:
    _old5, _new5 = os.path.join(_d5, "prog", "backup"), os.path.join(_d5, "cfg", "backup")
    for _nm5 in ("backup_A_2026-01-01_10-00-00", "backup_B_2026-01-02_10-00-00"):
        os.makedirs(os.path.join(_old5, _nm5)); open(os.path.join(_old5, _nm5, "manifest.json"), "w").write("{}")
    os.makedirs(os.path.join(_new5, "backup_B_2026-01-02_10-00-00"))
    _mv5 = sc.migrate_legacy_backups(_old5, _new5)
    check("P5: the runs of the program folder's backup\\ move to the new folder once; a run already there is left and named",
          _mv5[0] == 1 and len(_mv5[1]) == 1 and os.path.isfile(os.path.join(_new5, "backup_A_2026-01-01_10-00-00", "manifest.json"))
          and os.path.isdir(os.path.join(_old5, "backup_B_2026-01-02_10-00-00"))
          and sc.migrate_legacy_backups(_old5, _new5)[0] == 0, _mv5)
finally:
    shutil.rmtree(_d5, ignore_errors=True)
check("B31: the self-test made its backups in the temp folder", any(n.startswith("backup_") for n in os.listdir(_BK)))
check("B31: the program's own backup\\ folder is unchanged after the whole self-test",
      (os.path.isdir(_PROG_BK), _tree31(_PROG_BK)) == _PROG_BK_BEFORE,
      sorted(set(_tree31(_PROG_BK)) ^ set(_PROG_BK_BEFORE[1]))[:5])

# ### NEW v0.19.2 B27 ### — the whole run: no unhandled exception except the provoked ones
_unexp27 = [r.getMessage() + " " + (str(r.exc_info[1]) if r.exc_info else "") for r in _UNH.records]
check(f"B27: no unexpected 'Unhandled exception' in the whole self-test (provoked: {len(_UNH_PROVOKED)})", len(_UNH.records) == len(_UNH_PROVOKED), _unexp27)

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f_ in FAIL: print("   FAILED:", f_)
try: shutil.rmtree(_TMP, ignore_errors=True)
except Exception: pass
sys.exit(1 if FAIL else 0)
