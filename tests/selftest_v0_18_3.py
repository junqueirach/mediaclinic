# =============================================================================
# selftest_v0_18_3.py
# Metadata & MediaClinic — v0.18.3 self-test
# Author:  Luiz Junqueira & Claude AI
#
# Builds a synthetic movie library in a temp folder (NFO/XML/JPEG/MKV files
# generated on the fly), then exercises scanning, health rules, Quick Scan,
# FFprobe-flag handling, the export module, the results cache, the settings
# dialog and the main window — all against an ISOLATED config directory so
# your real settings.json is never touched.
#
# RUN (from the v.0.18.3 folder):
#   python selftest_v0_18_3.py
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
    if any(os.path.isfile(os.path.join(_cand, n)) for n in ("mediaclinic.py", "mediaclinic_v0_18_3.py")):
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
    import mediaclinic_v0_18_3 as mc             # local versioned copy
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

def make_movie(name, nfo=True, xml=True, images=True, backdrops=6, video=True, **kw):
    d = os.path.join(LIB, name); os.makedirs(d, exist_ok=True)
    nfo_kw = {k[4:]: v for k, v in kw.items() if k.startswith("nfo_")}
    xml_kw = {k[4:]: v for k, v in kw.items() if k.startswith("xml_")}
    title = kw.get("title", name)
    if nfo: _nfo(os.path.join(d, name + ".nfo"), nfo_kw.pop("title", title), **nfo_kw)
    if xml: _xml(os.path.join(d, "movie.xml"), xml_kw.pop("local", title), **xml_kw)
    if images:
        _jpeg(os.path.join(d, "poster.jpg"), 1000, 1500, noisy=True)
        shutil.copy2(os.path.join(d, "poster.jpg"), os.path.join(d, "folder.jpg"))
        _jpeg(os.path.join(d, "fanart.jpg"), 1920, 1080, noisy=True)
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
M_OK      = make_movie("Perfect Movie")                                           # all good
M_COMMA   = make_movie('Amor, Estranho Amor', title='Amor, Estranho "Amor"')     # export edge case (comma + quotes in title)
M_NONFO   = make_movie("No NFO Here", nfo=False)
M_BADXML  = make_movie("Broken XML", xml=False)
io.open(os.path.join(M_BADXML, "movie.xml"), "w", encoding="utf-8").write("<Item>\n<LocalTitle>Broken XML</LocalTitle>\n<Genres>\n</Item>\n")
M_CONFL   = make_movie("Conflicting IDs", nfo_imdb="tt0000001", xml_imdb="tt0000009")
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

# ══════════════════════════════════════════════════════════════════════════════
section("1. settings load / migration")
check("legacy quality label migrated", mc.SETTINGS.get("poster_quality_level") == "1080p", mc.SETTINGS.get("poster_quality_level"))
check("health_rules deep-merged with new keys", mc.SETTINGS["health_rules"].get("imdb_id_partial") is True and mc.SETTINGS["health_rules"].get("folder_name_mismatch") is False)
check("defaults not shared with SETTINGS (deep copy)", mc.SETTINGS["health_rules"] is not DEFAULT_SETTINGS["health_rules"])
check("last_results migrated out of settings.json", mc.SETTINGS.get("last_results") == [] and os.path.isfile(sc.RESULTS_CACHE_PATH))
check("cache file holds migrated row", sc.load_results_cache() and sc.load_results_cache()[0]["subfolder"] == "OldRow")
_cfg = json.load(open(sc.CONFIG_PATH, encoding="utf-8"))
check("settings.json no longer contains rows", _cfg.get("last_results") == [])
check("APP_VERSION", mc.APP_VERSION == "0.18.3")

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

        # Settings dialog
        sd = mc.SettingsDialog(app, tab=10)
        time.sleep(0.3)
        check("settings dialog: 12 tabs", len(sd._nb.tabs()) == 12, len(sd._nb.tabs()))
        check("settings dialog: new partial rules present", "imdb_id_partial" in sd._hr_vars and "tmdb_id_partial" in sd._hr_vars)
        reg = {lbl: idx for idx, lbl, _ in mc.SettingsDialog._TAB_REGISTRY}
        check("settings menu maps every entry to an existing tab", all(t in reg for _, _, t in mc._SETTINGS_MENU_ITEMS) and reg["Health Rules"] == 10 and reg["Ratings"] == 6)
        check("snapshot unchanged → no rescan", sd._rescan_changed()["any"] is False, sd._rescan_changed())
        sd._hr_vars["imdb_id_partial"].set(False)
        ch = sd._rescan_changed()
        check("health rule change detected", ch["health_rules"] is True and ch["image_sizes"] is False)
        offered = {"health": False}
        sd._offer_health_update = lambda parent_app: offered.__setitem__("health", True)
        sd._save_close()
        wait_for(lambda: offered["health"], 5)
        check("save chain ran + health update offered (no rescan)", offered["health"] and mc.SETTINGS["health_rules"]["imdb_id_partial"] is False)
        check("settings.json written with rule", json.load(open(sc.CONFIG_PATH, encoding="utf-8"))["health_rules"]["imdb_id_partial"] is False)
        app._apply_health_rules_inplace()
        by = {r["subfolder"]: r for r in app._results}
        check("in-memory health update respects disabled rule", not any("IMDB ID present in one file" in x for x in by["Partial TMDB"]["health_reasons"]))

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
app2 = mc.App(); app2.withdraw()
def ui_tests2():
    try:
        wait_for(lambda: bool(app2._results), 10)
        check("fresh App restores results from last_results.json", len(app2._results) == shared.get("rows", -1), len(app2._results))
        check("restored rows get new default keys", all("nfo_title" in r and "scan_mtime" in r for r in app2._results))
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
