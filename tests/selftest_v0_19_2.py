# =============================================================================
# selftest_v0_19_2.py
# Metadata & MediaClinic — v0.19.2 self-test
# Author:  Luiz Junqueira & Claude AI
#
# Builds a synthetic movie library in a temp folder (NFO/XML/JPEG/MKV files
# generated on the fly), then exercises scanning, health rules, Quick Scan,
# FFprobe-flag handling, the export module, the results cache, the settings
# dialog and the main window — all against an ISOLATED config directory so
# your real settings.json is never touched.
#
# RUN (from the v.0.19.2 folder):
#   python selftest_v0_19_2.py
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
    if any(os.path.isfile(os.path.join(_cand, n)) for n in ("mediaclinic.py", "mediaclinic_v0_19_2.py")):
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
    import mediaclinic_v0_19_2 as mc             # local versioned copy
import export_list
import settings_controller as sc
mc.IGNORED_REPORT_AUTO = False      # ### NEW v0.19.2 B53 ### the Ignored folders window opens only where a test asks
from settings_model import DEFAULT_SETTINGS
import tkinter as tk
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
check("APP_VERSION", mc.APP_VERSION == "0.19.2")
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
    json.dump({"library_folders": ["z:/film_kids", "Y:/a/b"], "library_filter": "Y:/a/b",
               "settings_migrations": ["b35_folder_rules_off", "b55_library_filter_reset"]},   # v0.19.2 B55: no one-time reset here
              open(_cfg_tmp3, "w", encoding="utf-8"))
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
_t27 = threading.Thread(target=lambda: {}["b27_thread_key"], daemon=True, name="B27-test")
_t27.start(); _t27.join(5); _UNH_PROVOKED.append("thread")
_l27 = io.open(mc.LOG_PATH, encoding="utf-8", errors="replace").read()
check("B27: an uncaught worker-thread exception is logged with its traceback", "Unhandled exception (thread B27-test)" in _l27 and "KeyError: 'b27_thread_key'" in _l27)
def _leak27():
    raise RuntimeError("download failed: https://x.test/?api_key=SECRETB27KEY")
_t27b = threading.Thread(target=_leak27, daemon=True, name="B27-key")
_t27b.start(); _t27b.join(5); _UNH_PROVOKED.append("thread-key")
_l27 = io.open(mc.LOG_PATH, encoding="utf-8", errors="replace").read()
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
      mc.library_overview([_A55, _B55], "", _rows55, offline=[_B55])["tooltip"].startswith(f"{_A55}  —  3 movie(s)\n{_B55}  —  2 movie(s)  (offline, last scan kept)"))
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
check("B50: the default API is GitHub's releases/latest of junqueirach/mediaclinic (no TMDb client)",
      mc._DEFAULT_UPDATE_API == "https://api.github.com/repos/junqueirach/mediaclinic/releases/latest"
      and "_http_get_json" not in inspect.getsource(mc.check_latest_release))
# a fake release on disk
_R56 = os.path.join(_TMP, "b56"); os.makedirs(_R56, exist_ok=True)
def _rel56(version="0.19.3", entries=None, sha="good", digest=None, url_override=None):
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
          _rel["status"] == "newer" and _e56 == "" and os.path.isfile(os.path.join(_base56, "MediaClinic 0.19.3", "MediaClinic.exe"))
          and os.path.isfile(os.path.join(_base56, "MediaClinic 0.19.3", "_internal", "x.dll"))
          and open(os.path.join(_base56, "MediaClinic", "MediaClinic.exe"), "rb").read() == b"MZ running"
          and not [n for n in os.listdir(_base56) if n.endswith((".part", ".new"))], (_e56, os.listdir(_base56)))
    _t56, _e56 = _try56(_rel, _base56)
    check("B56: an existing target folder → message, untouched", "already exists" in _e56
          and open(os.path.join(_base56, "MediaClinic 0.19.3", "MediaClinic.exe"), "rb").read() == b"MZ new", _e56)
    def _clean56():
        return sorted(n for n in os.listdir(_base56) if n != "MediaClinic" and n != "MediaClinic 0.19.3")
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
        time.sleep(0.1); wait_for(app._refresh_idle, 15)          # v0.19.0: automatic refresh runs in the background
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
        _n_backups = len([n for n in os.listdir(_BK) if n.startswith("backup_")])
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
            _n_backups2 = len([n for n in os.listdir(_BK) if n.startswith("backup_")])
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
        # ### MODIFIED v0.19.2 B53 (intended) ### an empty folder is "no media" now: the movie gets a video
        open(os.path.join(LIB3, "Lib3 Movie", "Lib3 Movie.mkv"), "wb").write(b"\0" * 64)
        ld3 = on_ui2(lambda: mc._LibrariesDialog(app))
        on_ui2(lambda: ld3.add_path(LIB3.replace("\\", "/")))
        if sys.platform == "win32": check("B3: dialog shows the added path with backslashes", ld3._items[-1] == os.path.normpath(LIB3) and "/" not in ld3._items[-1], ld3._items)   # Windows path style; CI runs on Linux
        on_ui2(lambda: ld3._ok())
        if sys.platform == "win32": check("B3: settings store backslash paths", all("/" not in x for x in mc.SETTINGS["library_folders"]), mc.SETTINGS["library_folders"])   # Windows path style; CI runs on Linux
        check("B4: adding a library offers a scan with Quick Scan as default", app._lib_prompt is not None and app._lib_prompt.default_kind == "quick")
        on_ui2(lambda: app._lib_prompt._buttons["quick"].invoke())
        wait_for(lambda: not app._scanning, 60); time.sleep(0.3); wait_for(lambda: not app._scanning, 60)
        check("B4: Quick Scan from the prompt adds the new library's movie (B53: a folder with a video)", "Lib3 Movie" in {r["subfolder"] for r in app._results})
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
                    _tq28 = time.monotonic(); on_ui(_dq28._done)
                    wait_for(lambda: bool(_res28), 5)
                    check("B28: closing the Fetch dialog (Done) kills the running FFmpeg at once", _res28 and _res28[0][0] == mc.FF_CANCELLED and _res28[0][1] - _tq28 < 1.0 and not mc._FF_PROCS, (_res28, round(_res28[0][1] - _tq28, 2) if _res28 else None))
                    _db28 = on_ui(lambda: mc._FetchBackdropDialog(app, _row11, "k", "711001"))
                    on_ui(_db28._frames_btn.invoke)
                    wait_for(lambda: bool(mc._FF_PROCS), 10); time.sleep(0.3)
                    on_ui(_db28._ff_stop_btn.invoke)
                    wait_for(lambda: len(_res28) == 2, 5); time.sleep(0.3)
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
                        lbl.event_generate("<MouseWheel>", delta=-240, x=5, y=5,
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
        check("B47: a folder.jpg that cannot be written is named in the message (warning), poster.jpg is saved",
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
        check("B30: a movie TMDb found nothing for gets 'Write empty ID tags' (no footer button for one movie)", _r30n in _sd30._empty_btns and _sd30._empty_all_btn is None, list(_sd30._empty_btns))
        on_ui(lambda: _sd30._empty_btns[_r30n].invoke())
        wait_for(lambda: any(b[1] and b[1][0] == "Write empty ID tags" for b in _boxes), 10); time.sleep(0.3)
        _n30 = io.open(_r30a["nfo_path"], encoding="utf-8").read(); _x30 = io.open(_r30a["xml_path"], encoding="utf-8").read()
        check("B30: …it writes the empty TMDb and IMDb tags into NFO and XML, both files stay valid",
              all(t in _n30 for t in ("<tmdbid></tmdbid>", "<imdbid></imdbid>", '<id moviedb="tmdb"></id>'))
              and all(t in _x30 for t in ("<TMDB></TMDB>", "<IMDB></IMDB>")) and mc._parse_root(_r30a["nfo_path"]) is not None and mc._parse_root(_r30a["xml_path"]) is not None, (_n30, _x30))
        check("B30: …with a backup first", len(_bk30()) > _bk30a, _bk30())
        _rr30 = mc.scan_one_subfolder(os.path.dirname(_r30a["nfo_path"]), "NoIds One", use_ffprobe=False)
        check("B30: …and the row shows ○ 'Missing TMDb ID (empty tags ready to fill)'", _rr30["source_tmdb_status"] == mc.STATUS_MISSING and _rr30["source_tmdb_empty"] is True)
        check("B30: the button changes to '✓ Empty tags written'", "Empty tags written" in on_ui(lambda: _sd30._empty_btns[_r30n].cget("text")))
        on_ui(_sd30.destroy)
        _sd30e = on_ui(lambda: mc._SearchSourcesResultDialog(app, [_e30(_r30a, err="TMDb is not reachable")], [_r30a]))
        check("B30: no button when TMDb did not answer (a failed search is not 'not found')", not _sd30e._empty_btns)
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
              "Emby and Jellyfin USE them" in _w34 and "Kodi and Plex do NOT read them" in _w34 and "2 folder(s), 5 image(s)" in _w34)
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
                on_ui(lambda h=_how34: app._ef_preview.event_generate(h))
                wait_for(lambda: not on_ui(app._ef_preview.winfo_exists), 5); time.sleep(0.3)
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
            wait_for(lambda: not app._rf_running and not app._rf_pending, 15)
            check("B34: the backdrop count drops after the delete, and the refreshed row shows it", _cnt34a == 2 and _cnt34b == 0
                  and [r["backdrop_count"] for r in app._results if r["subfolder"] == "Extra One"] == [0],
                  (_cnt34a, _cnt34b, _r34[0]["backdrop_count"], os.listdir(_r34[0]["subfolder_path"])))
            wait_for(lambda: not app._rf_running and not app._rf_pending, 15)
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

        # ── v0.19.2 B43: one Help window, Esc closes it, the grab goes back ──  ### NEW v0.19.2 B43 ###
        def _helps43():
            return [w for w in app.winfo_children() if isinstance(w, mc.HelpDialog) and w.winfo_exists()]
        _h43a = on_ui(lambda: mc.open_help(app, 2)); _h43b = on_ui(lambda: mc.open_help(app, 5))
        _sel43 = on_ui(lambda: _h43b._nb.index(_h43b._nb.select()))
        check("B43: F1 / Help twice → one Help window, switched to the new tab", _h43a is _h43b and len(on_ui(_helps43)) == 1 and _sel43 == 5, (len(on_ui(_helps43)), _sel43))
        on_ui(lambda: _h43b.event_generate("<Escape>"))
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
                on_ui(lambda d=_d45: (d.focus_force(), d.event_generate("<Escape>")))
                time.sleep(0.05)
                if on_ui(_d45.winfo_exists):
                    _left45.append(_n45); on_ui(_d45.destroy)
            _pr45 = on_ui(lambda: mc._PreviewRunDialog(app, "Auto Repair — preview", "plan"))
            on_ui(lambda: (_pr45.focus_force(), _pr45.event_generate("<Escape>")))
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
                          "🌐  Open on TMDb", "🌐  Open on Fanart.tv", "🌐  Open on OpenSubtitles.org", "📋  Copy Movie Name",
                          "🎬  Open in Scraper", "🔍  Run Improvements Check", "🏥  Health Status Report", "⭐  Sync Ratings",
                          "🔗  Normalize Sources", "🔎  Search Sources", "✅  Verify IMDb/TMDb IDs", "🛠  Auto Repair",
                          "🎬  Normalize Genres", "🔤  Hard-coded subtitles…", "🖼  Fetch Poster/Folder", "🎨  Fetch Fanart",
                          "🖼  Fetch Backdrops", "🔄  Replace All Backdrops", "🖼  Copy poster.jpg → folder.jpg",
                          "➕  Add Custom Genre(s) to Settings", "🔄  Update (no FFprobe)", "🔬  Update (with FFprobe)",
                          "🔁  Refresh Icons", "✖  Remove from list"]
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
            _rep57 = on_ui(lambda: [l for dp, l, _s, _m, _i in _menu57([_d57]) if dp == 0][1])
            check("B57: 'Repeat: <last action>' follows under the title", _rep57.startswith("↻  Repeat: Poster / folder image missing"), _rep57)
            on_ui(lambda: _invoke57("↻  Repeat:", [_d57]))
            check("B57: Repeat runs the last action again", len(_called57) == 3, _called57)
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

        # ── v0.19.2 F4a: Fix image dialog + batch, in-process ──────────────────   ### NEW v0.19.2 F4a ###
        _f4u = os.path.join(_TMP, "f4", "Dialog Fix (2002)"); os.makedirs(_f4u, exist_ok=True)
        open(os.path.join(_f4u, "Dialog Fix (2002).mkv"), "wb").write(b"\0" * 64)
        _pic4(700, 1000).save(os.path.join(_f4u, "poster.jpg"), "JPEG", quality=90)
        _row4 = scan(_f4u, use_ffprobe=False)
        _act4, _why4 = on_ui(lambda: app._ctx_fix_action("images", [_row4]))
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
        wait_for(lambda: any("image(s) fixed" in str(b) for b in _boxes), 20)
        check("F4 batch: preview lists the movies, Run fixes with ✓ sizes only (1100×1500 → 1000×1500)",
              any("1 image(s) fixed" in str(b) for b in _boxes) and mc.probe_image(os.path.join(_f4b, "poster.jpg"))["w"] == 1000
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
        _now52 = on_ui(lambda: {k.capitalize(): [e for e in _entries52(m) if e[1] != mc.CHECK_UPDATES_LABEL]   # B50 adds one entry (intended)
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
            on_ui(lambda: app.tree.event_generate("<Alt-h>"))
            on_ui(lambda: app.tree.event_generate("<Alt-T>"))
            on_ui(lambda: app.tree.event_generate("<F10>"))
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
            kid.event_generate("<MouseWheel>", delta=-240, x=2, y=2,
                               rootx=kid.winfo_rootx() + 2, rooty=kid.winfo_rooty() + 2)
            sd.update_idletasks()
            return len(reg["canvases"]), c.yview()
        _n29, _ysd29 = on_ui(_sd_wheel29)
        check("B29: the Settings tabs still scroll with the wheel (one Toplevel binding for every tab canvas)", bool(_n29) and _n29 >= 3 and _ysd29[0] > 0, (_n29, _ysd29))
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
check("B31: MEDIACLINIC_BACKUP_DIR is honoured (app and settings_controller); without it backup\\ next to the program",
      os.path.normcase(mc._BACKUP_ROOT) == os.path.normcase(_BK) and sc.get_backup_root(r"C:\Prog") == _BK
      and _def31 == os.path.join(r"C:\Prog", "backup"), (mc._BACKUP_ROOT, _def31))
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
