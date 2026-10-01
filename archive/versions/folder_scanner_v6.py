import os
import csv
import configparser
import json
import re
import struct
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import shutil
import webbrowser

# ── Video / subtitle extensions ───────────────────────────────────────────────
VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.m4v', '.wmv', '.mov', '.flv',
                    '.ts', '.m2ts', '.mpg', '.mpeg', '.divx', '.ogm', '.webm'}
SUBTITLE_EXTENSIONS = {'.srt', '.sub', '.ssa', '.ass', '.vtt', '.idx', '.sup'}

# ── Column indices ────────────────────────────────────────────────────────────
COL_SUBFOLDER = 0; COL_POSTER = 1; COL_POSTER_SZ = 2
COL_FOLDER = 3; COL_FOLDER_SZ = 4; COL_FANART = 5; COL_FANART_SZ = 6
COL_BACKDROPS = 7; COL_NFO = 8; COL_NFO_OK = 9
COL_XML = 10; COL_XML_OK = 11; COL_LANGUAGE = 12
COL_VID_EXT = 13; COL_VID_SIZE = 14; COL_SUBS = 15

STATUS_OK = "✅"; STATUS_MISSING = "❌"; STATUS_ERROR = "⚠️"

# ── Config file for FFmpeg path persistence ───────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "folder_scanner.ini")


def _load_config():
    cfg = configparser.ConfigParser()
    if os.path.isfile(CONFIG_FILE):
        cfg.read(CONFIG_FILE, encoding="utf-8")
    return cfg


def _save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)


def _find_ffmpeg_ffprobe():
    """Find ffmpeg and ffprobe paths. Returns (ffmpeg_path, ffprobe_path)."""
    cfg = _load_config()
    custom = cfg.get("ffmpeg", "path", fallback="").strip()

    # If custom path set, check it
    if custom and os.path.isdir(custom):
        ff = os.path.join(custom, "ffmpeg.exe") if os.name == "nt" else os.path.join(custom, "ffmpeg")
        fp = os.path.join(custom, "ffprobe.exe") if os.name == "nt" else os.path.join(custom, "ffprobe")
        if not os.path.isfile(ff):
            ff = os.path.join(custom, "ffmpeg")
        if not os.path.isfile(fp):
            fp = os.path.join(custom, "ffprobe")
        if os.path.isfile(ff) and os.path.isfile(fp):
            return ff, fp

    # Try system PATH
    ff = shutil.which("ffmpeg")
    fp = shutil.which("ffprobe")
    return ff, fp


FFMPEG_PATH, FFPROBE_PATH = _find_ffmpeg_ffprobe()


def refresh_ffmpeg_paths():
    global FFMPEG_PATH, FFPROBE_PATH
    FFMPEG_PATH, FFPROBE_PATH = _find_ffmpeg_ffprobe()


# ══════════════════════════════════════════════════════════════════════════════
# Utility helpers
# ══════════════════════════════════════════════════════════════════════════════

def format_size(size_bytes):
    if size_bytes < 1024: return f"{size_bytes} B"
    elif size_bytes < 1024**2: return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3: return f"{size_bytes/(1024**2):.1f} MB"
    else: return f"{size_bytes/(1024**3):.2f} GB"


def os_open(path):
    try:
        os.startfile(path)
    except AttributeError:
        try: subprocess.Popen(["xdg-open", path])
        except FileNotFoundError: subprocess.Popen(["open", path])
    except Exception as e:
        messagebox.showerror("Cannot open", str(e))


def get_jpeg_dimensions(filepath):
    try:
        with open(filepath, "rb") as f:
            if f.read(2) != b'\xff\xd8': return None, None
            while True:
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF: return None, None
                m = marker[1]
                while m == 0xFF:
                    b = f.read(1)
                    if len(b) < 1: return None, None
                    m = b[0]
                if m in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
                    f.read(3); hw = f.read(4)
                    if len(hw) < 4: return None, None
                    return struct.unpack(">H", hw[2:4])[0], struct.unpack(">H", hw[0:2])[0]
                elif m in (0xD9, 0xDA): return None, None
                else:
                    d = f.read(2)
                    if len(d) < 2: return None, None
                    f.seek(struct.unpack(">H", d)[0] - 2, 1)
    except Exception: return None, None


def get_png_dimensions(filepath):
    try:
        with open(filepath, "rb") as f:
            if f.read(8)[:4] != b'\x89PNG': return None, None
            f.read(4)
            if f.read(4) != b'IHDR': return None, None
            d = f.read(8)
            if len(d) < 8: return None, None
            return struct.unpack(">I", d[0:4])[0], struct.unpack(">I", d[4:8])[0]
    except Exception: return None, None


def get_image_dimensions(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    w, h = (get_jpeg_dimensions(filepath) if ext in ('.jpg','.jpeg')
            else get_png_dimensions(filepath) if ext == '.png' else (None, None))
    return f"{w}×{h}" if w is not None and h is not None and (w > 0 or h > 0) else None


def is_valid_jpeg(filepath):
    try:
        if os.path.getsize(filepath) == 0: return False
        with open(filepath, "rb") as f: return f.read(2) == b'\xff\xd8'
    except Exception: return False


# ══════════════════════════════════════════════════════════════════════════════
# Backdrop / Video / Subtitle / Language / XML validation
# ══════════════════════════════════════════════════════════════════════════════

def count_backdrops(sub_path):
    count = 0; paths = []
    p = os.path.join(sub_path, "backdrop.jpg")
    if os.path.isfile(p): count += 1; paths.append(p)
    for i in range(1, 100):
        p = os.path.join(sub_path, f"backdrop{i}.jpg")
        if os.path.isfile(p): count += 1; paths.append(p)
        else: break
    return count, paths


def next_backdrop_number(sub_path):
    """Return the next available backdrop number (e.g. 3 if backdrop.jpg, backdrop1, backdrop2 exist)."""
    if not os.path.isfile(os.path.join(sub_path, "backdrop.jpg")):
        return 0  # will create backdrop.jpg first? No — we use backdropX numbering
    # Find the highest existing number
    highest = 0
    for i in range(1, 200):
        if os.path.isfile(os.path.join(sub_path, f"backdrop{i}.jpg")):
            highest = i
        # Don't break on gaps — scan further to be safe
    # Also check backdrop.jpg (number 0 equivalent)
    start = highest + 1 if highest > 0 else 1
    # But if backdrop.jpg doesn't exist, check from 0
    if not os.path.isfile(os.path.join(sub_path, "backdrop.jpg")):
        start = 0
    else:
        # backdrop.jpg exists, find first free numbered slot
        for i in range(1, 200):
            if not os.path.isfile(os.path.join(sub_path, f"backdrop{i}.jpg")):
                start = i
                break
    return start


def scan_video_files(sub_path):
    videos = []
    try:
        for f in os.scandir(sub_path):
            if f.is_file() and os.path.splitext(f.name)[1].lower() in VIDEO_EXTENSIONS:
                videos.append(f)
    except PermissionError: pass
    if not videos:
        return {"video_count": 0, "video_files": [], "video_ext": "—",
                "video_path": None, "video_bytes": 0, "video_size": "—"}
    videos.sort(key=lambda e: e.stat().st_size, reverse=True)
    main = videos[0]; ext = os.path.splitext(main.name)[1].lower()
    return {"video_count": len(videos), "video_files": [v.name for v in videos],
            "video_ext": ext.lstrip('.').upper(), "video_path": main.path,
            "video_bytes": main.stat().st_size, "video_size": format_size(main.stat().st_size)}


def scan_subtitles(sub_path, video_path):
    result = {"subs_internal": [], "subs_external": [], "subs_summary": "—"}
    try:
        for f in os.scandir(sub_path):
            if f.is_file() and os.path.splitext(f.name)[1].lower() in SUBTITLE_EXTENSIONS:
                parts = os.path.splitext(f.name)[0].rsplit('.', 1)
                lang = parts[-1] if len(parts) > 1 and len(parts[-1]) <= 20 else "unknown"
                result["subs_external"].append({"lang": lang, "file": f.name})
    except PermissionError: pass
    if video_path and FFPROBE_PATH:
        try:
            proc = subprocess.run(
                [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-select_streams", "s", video_path],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if proc.returncode == 0 and proc.stdout.strip():
                for stream in json.loads(proc.stdout).get("streams", []):
                    tags = stream.get("tags", {})
                    result["subs_internal"].append({
                        "lang": tags.get("language") or tags.get("LANGUAGE") or "und",
                        "title": tags.get("title") or tags.get("TITLE") or ""})
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, OSError): pass
    parts = []
    if result["subs_internal"]: parts.append(f"Int: {', '.join(s['lang'] for s in result['subs_internal'])}")
    if result["subs_external"]: parts.append(f"Ext: {', '.join(s['lang'] for s in result['subs_external'])}")
    result["subs_summary"] = " | ".join(parts) if parts else ("None" if video_path else "—")
    return result


def extract_language_from_xml(filepath):
    if not filepath or not os.path.isfile(filepath): return "—"
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f: content = f.read()
        m = re.search(r'<Language>([^<]+)</Language>', content)
        if m: lang = m.group(1).strip(); return lang if lang else "Unknown"
        if '<Language></Language>' in content or '<Language />' in content: return "Unknown"
        return "—"
    except Exception: return "—"


def _is_url_only_nfo(content):
    s = content.strip()
    return '\n' not in s and s.startswith(('http://', 'https://'))


def validate_xml_file(filepath, is_nfo=False):
    errors = []
    if not os.path.isfile(filepath): return errors
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f: content = f.read()
    except Exception as e:
        return [{"line": 0, "col": 0, "message": f"Cannot read: {e}"}]
    if not content.strip(): return [{"line": 1, "col": 0, "message": "File is empty"}]
    if is_nfo and _is_url_only_nfo(content): return errors
    if content.startswith('\ufeff'): content = content[1:]

    try:
        ET.fromstring(content)
    except ET.ParseError as e:
        line, col = e.position if hasattr(e, 'position') else (0, 0)
        raw_msg = str(e); src_lines = content.splitlines()
        if 0 < line <= len(src_lines):
            offending = src_lines[line - 1]
            if re.search(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', offending):
                raw_msg = "Unescaped '&' (should be '&amp;'). Common in scraper files — won't break KODI"
            elif "mismatched tag" in raw_msg:
                raw_msg = f"mismatched tag at line {line} — likely caused by a broken tag earlier (see below)"
        errors.append({"line": line, "col": col, "message": raw_msg})

    lines = content.splitlines()
    for ln, lt in enumerate(lines, 1):
        sl = lt.strip()
        if sl.startswith('<?') or sl.startswith('<!--'): continue
        for b in re.findall(r'<([A-Za-z_][\w.\-]*)(?=[^>]*(?:<|$))', lt):
            seg = lt[lt.index(f"<{b}"):]
            at = seg[1:]; nlt = at.find('<'); ngt = at.find('>')
            if ngt == -1 or (nlt != -1 and nlt < ngt):
                ml = False
                if ngt == -1:
                    for pk in range(ln, min(ln + 5, len(lines))):
                        pl = lines[pk]
                        if '>' in pl:
                            gp = pl.index('>'); lp = pl.find('<')
                            if lp == -1 or gp < lp: ml = True
                            break
                        if '<' in pl: break
                if not ml and not any(e["line"] == ln for e in errors):
                    errors.append({"line": ln, "col": lt.index(f"<{b}")+1,
                                   "message": f"Malformed tag '<{b}…' — missing '>'"})
        stripped = lt.rstrip()
        if re.search(r'</[A-Za-z_][\w.\-]*\s*$', stripped) and not stripped.endswith('>'):
            if not any(e["line"] == ln for e in errors):
                errors.append({"line": ln, "col": len(stripped), "message": "Closing tag missing '>'"})
        for tn, _ in re.findall(r'<([A-Za-z_][\w.\-]*)(?:\s[^>]*)?>([^<]*)/\1>', lt):
            if not any(e["line"] == ln for e in errors):
                errors.append({"line": ln, "col": lt.index(f"/{tn}>")+1,
                               "message": f"'/{tn}>' missing '<' — should be '</{tn}>'"})
    seen = set(); unique = []
    for e in errors:
        k = (e["line"], e["message"][:60])
        if k not in seen: seen.add(k); unique.append(e)
    unique.sort(key=lambda e: (e["line"], e["col"]))
    return unique


# ══════════════════════════════════════════════════════════════════════════════
# Scanning
# ══════════════════════════════════════════════════════════════════════════════

def scan_one_subfolder(sub_path, sub_name):
    poster_path = os.path.join(sub_path, "poster.jpg")
    fanart_path = os.path.join(sub_path, "fanart.jpg")
    folder_path = os.path.join(sub_path, "folder.jpg")
    pe = os.path.isfile(poster_path); fe = os.path.isfile(fanart_path); fle = os.path.isfile(folder_path)
    pb = os.path.getsize(poster_path) if pe else 0
    fb = os.path.getsize(fanart_path) if fe else 0
    flb = os.path.getsize(folder_path) if fle else 0
    pd = get_image_dimensions(poster_path) if pe else None
    fd = get_image_dimensions(fanart_path) if fe else None
    fld = get_image_dimensions(folder_path) if fle else None
    pc = pe and not is_valid_jpeg(poster_path)
    fc = fe and not is_valid_jpeg(fanart_path)
    flc = fle and not is_valid_jpeg(folder_path)
    bc, bp = count_backdrops(sub_path)
    nfo_path = os.path.join(sub_path, sub_name + ".nfo")
    ne = os.path.isfile(nfo_path); nb = os.path.getsize(nfo_path) if ne else 0
    nerr = validate_xml_file(nfo_path, is_nfo=True) if ne else []
    xml_path = os.path.join(sub_path, "movie.xml")
    xe = os.path.isfile(xml_path); xb = os.path.getsize(xml_path) if xe else 0
    xerr = validate_xml_file(xml_path, is_nfo=False) if xe else []
    lang = extract_language_from_xml(xml_path) if xe else "—"
    ns = (STATUS_ERROR if nerr else STATUS_OK) if ne else STATUS_MISSING
    xs = (STATUS_ERROR if xerr else STATUS_OK) if xe else STATUS_MISSING
    vi = scan_video_files(sub_path); si = scan_subtitles(sub_path, vi["video_path"])
    vs = STATUS_MISSING if vi["video_count"]==0 else STATUS_ERROR if vi["video_count"]>1 else STATUS_OK
    has_err = ns==STATUS_ERROR or xs==STATUS_ERROR or pc or fc or flc
    health = "red" if has_err else ("green" if pe and fe and fle and ns==STATUS_OK and xs==STATUS_OK and vi["video_count"]==1 else "yellow")
    return {
        "subfolder": sub_name, "subfolder_path": sub_path,
        "poster_exists": pe, "poster_path": poster_path, "poster_bytes": pb,
        "poster_size": format_size(pb) if pe else "—", "poster_dim": pd, "poster_corrupt": pc,
        "fanart_exists": fe, "fanart_path": fanart_path, "fanart_bytes": fb,
        "fanart_size": format_size(fb) if fe else "—", "fanart_dim": fd, "fanart_corrupt": fc,
        "folder_exists": fle, "folder_path": folder_path, "folder_bytes": flb,
        "folder_size": format_size(flb) if fle else "—", "folder_dim": fld, "folder_corrupt": flc,
        "backdrop_count": bc, "backdrop_paths": bp,
        "nfo_exists": ne, "nfo_path": nfo_path, "nfo_bytes": nb,
        "nfo_size": format_size(nb) if ne else "—", "nfo_status": ns, "nfo_errors": nerr,
        "xml_exists": xe, "xml_path": xml_path, "xml_bytes": xb,
        "xml_size": format_size(xb) if xe else "—", "xml_status": xs, "xml_errors": xerr,
        "language": lang,
        "video_count": vi["video_count"], "video_files": vi["video_files"],
        "video_ext": vi["video_ext"], "video_path": vi["video_path"],
        "video_bytes": vi["video_bytes"], "video_size": vi["video_size"], "video_status": vs,
        "subs_internal": si["subs_internal"], "subs_external": si["subs_external"],
        "subs_summary": si["subs_summary"], "row_health": health,
    }


SORT_OPTIONS = {
    "Subfolder (A→Z)": (lambda r: r["subfolder"].lower(), False),
    "Subfolder (Z→A)": (lambda r: r["subfolder"].lower(), True),
    "Poster size (lg→sm)": (lambda r: r["poster_bytes"], True),
    "Poster size (sm→lg)": (lambda r: r["poster_bytes"], False),
    "Fanart size (lg→sm)": (lambda r: r["fanart_bytes"], True),
    "Video size (lg→sm)": (lambda r: r["video_bytes"], True),
    "Video size (sm→lg)": (lambda r: r["video_bytes"], False),
    "Language (A→Z)": (lambda r: r["language"].lower(), False),
    "Backdrops (most)": (lambda r: r["backdrop_count"], True),
    "Health (errors 1st)": (lambda r: {"red":0,"yellow":1,"green":2}[r["row_health"]], False),
    "Health (OK 1st)": (lambda r: {"green":0,"yellow":1,"red":2}[r["row_health"]], False),
}


# ══════════════════════════════════════════════════════════════════════════════
# Frame Extraction with FFmpeg
# ══════════════════════════════════════════════════════════════════════════════

def get_video_duration(video_path):
    """Get video duration in seconds via ffprobe."""
    if not FFPROBE_PATH: return None
    try:
        proc = subprocess.run(
            [FFPROBE_PATH, "-v", "quiet", "-print_format", "json", "-show_format", video_path],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            return float(data.get("format", {}).get("duration", 0))
    except Exception: pass
    return None


def extract_single_frame(video_path, time_sec, output_path):
    """Extract one frame at the given timestamp. Returns True on success."""
    if not FFMPEG_PATH: return False
    try:
        proc = subprocess.run(
            [FFMPEG_PATH, "-y", "-ss", str(time_sec), "-i", video_path,
             "-frames:v", "1", "-q:v", "1", output_path],
            capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return proc.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 0
    except Exception: return False


class FrameExtractionDialog(tk.Toplevel):
    """Progress dialog for extracting 10 frames from a video."""

    def __init__(self, parent, video_path, sub_path):
        super().__init__(parent)
        self.title("Extracting Frames…")
        self.geometry("480x220")
        self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._video_path = video_path
        self._sub_path = sub_path
        self._cancelled = False
        self._extracted = []

        tk.Label(self, text="🎬  Extracting backdrop frames…",
                 font=("Helvetica", 12, "bold"), bg="#1e1e2e", fg="#cdd6f4"
                 ).pack(pady=(16, 4))
        tk.Label(self, text=os.path.basename(video_path),
                 font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086").pack(pady=(0, 10))

        self.status_var = tk.StringVar(value="Preparing…")
        tk.Label(self, textvariable=self.status_var, font=("Helvetica", 10),
                 bg="#1e1e2e", fg="#a6adc8").pack()

        # Progress bar with percentage
        pf = tk.Frame(self, bg="#1e1e2e"); pf.pack(fill="x", padx=30, pady=(8, 4))
        self.pbar_canvas = tk.Canvas(pf, height=24, bg="#313244",
                                      highlightthickness=0, relief="flat")
        self.pbar_canvas.pack(fill="x")
        self.pbar_rect = None
        self.pbar_text = None
        self._draw_progress(0)

        tk.Button(self, text="  Cancel  ", font=("Helvetica", 10, "bold"),
                  bg="#f38ba8", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=self._on_cancel).pack(pady=(8, 16))

        self.after(100, self._start)

    def _draw_progress(self, pct):
        c = self.pbar_canvas
        c.delete("all")
        w = c.winfo_width() or 420
        h = 24
        # Background
        c.create_rectangle(0, 0, w, h, fill="#313244", outline="")
        # Fill
        fill_w = int(w * pct / 100)
        if fill_w > 0:
            c.create_rectangle(0, 0, fill_w, h, fill="#2d6e3f", outline="")
        # Percentage text
        c.create_text(w // 2, h // 2, text=f"{pct}%",
                      fill="#cdd6f4", font=("Helvetica", 10, "bold"))

    def _on_cancel(self):
        self._cancelled = True
        self.status_var.set("Cancelling…")

    def _start(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        video = self._video_path
        sub = self._sub_path

        # Get duration
        self.after(0, lambda: self.status_var.set("Reading video duration…"))
        duration = get_video_duration(video)
        if not duration or duration < 600:
            # For short videos (< 10 min), use 10% and 90% marks
            if duration and duration > 60:
                start_sec = duration * 0.05
                end_sec = duration * 0.95
            elif duration:
                start_sec = 5
                end_sec = max(duration - 5, start_sec + 10)
            else:
                self.after(0, lambda: messagebox.showerror(
                    "Error", "Cannot read video duration. The file may be corrupt.\n"
                             "Please check the video file.", parent=self))
                self.after(0, self.destroy)
                return
        else:
            start_sec = 300  # 5 minutes
            end_sec = duration - 300  # 5 minutes before end

        if end_sec <= start_sec:
            end_sec = duration * 0.9
            start_sec = duration * 0.1

        # Calculate 10 evenly spaced timestamps
        interval = (end_sec - start_sec) / 9 if end_sec > start_sec else 1
        timestamps = [start_sec + i * interval for i in range(10)]

        # Find next available backdrop number
        start_num = next_backdrop_number(sub)

        extracted = []
        for i, ts in enumerate(timestamps):
            if self._cancelled:
                break

            num = start_num + i
            fname = f"backdrop{num}.jpg"
            out_path = os.path.join(sub, fname)
            mins = int(ts // 60); secs = int(ts % 60)

            self.after(0, lambda i=i, m=mins, s=secs, fn=fname:
                       (self.status_var.set(f"Frame {i+1}/10 at {m}:{s:02d} → {fn}"),
                        self._draw_progress(int((i) / 10 * 100))))

            ok = extract_single_frame(video, ts, out_path)
            if not ok:
                self.after(0, lambda: messagebox.showerror(
                    "Extraction Failed",
                    f"Failed to extract frame at {mins}:{secs:02d}.\n"
                    f"The video file may be corrupt or unreadable.\n"
                    f"Please check the video file.",
                    parent=self))
                # Clean up any partially extracted files
                for p in extracted:
                    try: os.remove(p)
                    except OSError: pass
                self.after(0, self.destroy)
                return

            extracted.append(out_path)

        self._extracted = extracted

        if self._cancelled:
            # Clean up
            for p in extracted:
                try: os.remove(p)
                except OSError: pass
            self.after(0, lambda: (self.status_var.set("Cancelled."), self.destroy()))
        else:
            self.after(0, lambda: self._draw_progress(100))
            self.after(0, lambda: messagebox.showinfo(
                "Done",
                f"Successfully extracted {len(extracted)} frames:\n"
                f"backdrop{start_num}.jpg → backdrop{start_num + len(extracted) - 1}.jpg",
                parent=self))
            self.after(0, self.destroy)


# ══════════════════════════════════════════════════════════════════════════════
# Dialogs
# ══════════════════════════════════════════════════════════════════════════════

class SubtitleDialog(tk.Toplevel):
    def __init__(self, parent, name, data):
        super().__init__(parent)
        self.title(f"Subtitles — {name}"); self.geometry("620x400"); self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        tk.Label(self, text=f"Subtitles — {name}", font=("Helvetica", 13, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", padx=16, pady=(14, 2))
        if data["video_path"]:
            tk.Label(self, text=f"Video: {os.path.basename(data['video_path'])}",
                     font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086").pack(anchor="w", padx=16, pady=(0, 10))
        fr = tk.Frame(self, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        t = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4", font=("Consolas", 10), relief="flat", padx=10, pady=10)
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview); t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        t.tag_configure("h", foreground="#89b4fa", font=("Consolas", 10, "bold"))
        t.tag_configure("l", foreground="#a6e3a1"); t.tag_configure("d", foreground="#a6adc8")
        t.tag_configure("s", foreground="#45475a"); t.tag_configure("n", foreground="#f38ba8")
        t.insert("end", "  EMBEDDED SUBTITLES", "h")
        t.insert("end", f"  {'(via ffprobe)' if FFPROBE_PATH else '(ffprobe not found)'}\n", "d" if FFPROBE_PATH else "n")
        if data["subs_internal"]:
            for i, s in enumerate(data["subs_internal"], 1):
                tl = f'  "{s["title"]}"' if s["title"] else ""
                t.insert("end", f"    {i}. ", "d"); t.insert("end", s["lang"], "l"); t.insert("end", f"{tl}\n", "d")
        elif FFPROBE_PATH: t.insert("end", "    None found\n", "n")
        t.insert("end", "\n  " + "─"*50 + "\n\n", "s"); t.insert("end", "  EXTERNAL FILES\n", "h")
        if data["subs_external"]:
            for i, s in enumerate(data["subs_external"], 1):
                t.insert("end", f"    {i}. ", "d"); t.insert("end", s["lang"], "l"); t.insert("end", f'  →  {s["file"]}\n', "d")
        else: t.insert("end", "    None found\n", "n")
        t.configure(state="disabled")
        tk.Button(self, text="  Close  ", font=("Helvetica", 10, "bold"), bg="#89b4fa", fg="#1e1e2e",
                  relief="flat", cursor="hand2", command=self.destroy).pack(pady=(4, 14))


class ErrorDialog(tk.Toplevel):
    def __init__(self, parent, title, filepath, errors):
        super().__init__(parent)
        self.title(title); self.geometry("740x440"); self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        tk.Label(self, text=title, font=("Helvetica", 13, "bold"), bg="#1e1e2e", fg="#f38ba8"
                 ).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(self, text=filepath, font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086",
                 wraplength=700, justify="left").pack(anchor="w", padx=16, pady=(0, 10))
        fr = tk.Frame(self, bg="#1e1e2e"); fr.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        t = tk.Text(fr, wrap="word", bg="#313244", fg="#cdd6f4", font=("Consolas", 10), relief="flat", padx=10, pady=10)
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview); t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        t.tag_configure("eh", foreground="#f38ba8", font=("Consolas", 10, "bold"))
        t.tag_configure("ed", foreground="#fab387"); t.tag_configure("sl", foreground="#a6adc8")
        t.tag_configure("sp", foreground="#45475a")
        sl = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f: sl = f.readlines()
        except: pass
        for i, e in enumerate(errors, 1):
            loc = f"Line {e['line']}" + (f", Col {e['col']}" if e["col"] else "")
            t.insert("end", f"  Error {i}:  ", "eh"); t.insert("end", f"{loc}\n", "ed")
            t.insert("end", f"    {e['message']}\n", "ed")
            if 0 < e["line"] <= len(sl): t.insert("end", f"    → {sl[e['line']-1].rstrip()}\n", "sl")
            if i < len(errors): t.insert("end", "    " + "─"*60 + "\n", "sp")
        t.configure(state="disabled")
        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(4, 14))
        tk.Button(bf, text="  Open in editor  ", font=("Helvetica", 10, "bold"), bg="#a6e3a1", fg="#1e1e2e",
                  relief="flat", cursor="hand2", command=lambda: os_open(filepath)).pack(side="left", padx=(0, 8))
        tk.Button(bf, text="  Close  ", font=("Helvetica", 10, "bold"), bg="#89b4fa", fg="#1e1e2e",
                  relief="flat", cursor="hand2", command=self.destroy).pack(side="left")


# ══════════════════════════════════════════════════════════════════════════════
# Tooltip
# ══════════════════════════════════════════════════════════════════════════════

class TreeviewTooltip:
    def __init__(self, tree, fn):
        self.tree = tree; self.fn = fn; self.tw = None; self._lc = (None, None)
        tree.bind("<Motion>", self._m); tree.bind("<Leave>", self._h)
    def _m(self, e):
        i = self.tree.identify_row(e.y); c = self.tree.identify_column(e.x)
        if not i or not c: self._h(); return
        if (i, c) == self._lc: return
        self._lc = (i, c); t = self.fn(i, int(c.lstrip("#"))-1)
        if t: self._s(e, t)
        else: self._h()
    def _s(self, e, t):
        self._h()
        self.tw = w = tk.Toplevel(self.tree); w.wm_overrideredirect(True)
        w.wm_geometry(f"+{e.x_root+16}+{e.y_root+10}"); w.configure(bg="#45475a")
        tk.Label(w, text=t, bg="#45475a", fg="#cdd6f4", font=("Consolas", 9, "bold"), padx=8, pady=4).pack()
    def _h(self, e=None):
        if self.tw: self.tw.destroy(); self.tw = None
        self._lc = (None, None)


# ══════════════════════════════════════════════════════════════════════════════
# Main Application
# ══════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎬  Subfolder Image & Metadata Scanner")
        self.geometry("1440x720"); self.minsize(1100, 520); self.configure(bg="#1e1e2e")
        self._item_map = {}; self._results = []; self._folder = None
        self._scanning = False; self._cancel_scan = False
        self._build_ui()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#1e1e2e"); header.pack(fill="x", padx=20, pady=(18, 6))
        tk.Label(header, text="🎬  Subfolder Image & Metadata Scanner",
                 font=("Helvetica", 17, "bold"), bg="#1e1e2e", fg="#cdd6f4").pack(side="left")

        # FFmpeg status (right side of header)
        ff_frame = tk.Frame(header, bg="#1e1e2e"); ff_frame.pack(side="right")
        self._build_ffmpeg_status(ff_frame)

        # Picker row
        picker = tk.Frame(self, bg="#1e1e2e"); picker.pack(fill="x", padx=20, pady=(0, 8))
        self.folder_var = tk.StringVar(value="No folder selected")
        tk.Label(picker, textvariable=self.folder_var, font=("Helvetica", 10), bg="#313244", fg="#a6adc8",
                 anchor="w", padx=10, pady=6, relief="flat").pack(side="left", fill="x", expand=True, ipady=2)
        tk.Button(picker, text="  Browse…  ", font=("Helvetica", 10, "bold"), bg="#89b4fa", fg="#1e1e2e",
                  relief="flat", cursor="hand2", command=self._browse).pack(side="left", padx=(8, 0))
        self.scan_btn = tk.Button(picker, text="  Scan  ", font=("Helvetica", 10, "bold"), bg="#a6e3a1",
                                   fg="#1e1e2e", relief="flat", cursor="hand2", command=self._scan)
        self.scan_btn.pack(side="left", padx=(6, 0))
        self.cancel_btn = tk.Button(picker, text="  Cancel  ", font=("Helvetica", 10, "bold"), bg="#f38ba8",
                                     fg="#1e1e2e", relief="flat", cursor="hand2", command=self._cancel)
        self.extract_btn = tk.Button(picker, text="  Extract Frames  ", font=("Helvetica", 10, "bold"),
                                      bg="#fab387", fg="#1e1e2e", relief="flat", cursor="hand2",
                                      command=self._extract_frames)
        self.extract_btn.pack(side="left", padx=(6, 0))
        tk.Button(picker, text="  Export CSV  ", font=("Helvetica", 10, "bold"), bg="#cba6f7", fg="#1e1e2e",
                  relief="flat", cursor="hand2", command=self._export_csv).pack(side="left", padx=(6, 0))

        # Sort + legend
        sr = tk.Frame(self, bg="#1e1e2e"); sr.pack(fill="x", padx=20, pady=(0, 4))
        tk.Label(sr, text="Sort:", font=("Helvetica", 10), bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        self.sort_var = tk.StringVar(value="Subfolder (A→Z)")
        sm = ttk.Combobox(sr, textvariable=self.sort_var, values=list(SORT_OPTIONS.keys()),
                          state="readonly", width=28, font=("Helvetica", 10))
        sm.pack(side="left", padx=(6, 0)); sm.bind("<<ComboboxSelected>>", lambda _: self._refresh_table())
        lg = tk.Frame(sr, bg="#1e1e2e"); lg.pack(side="right")
        for c, l in [("#a6e3a1","All OK"),("#f9e2af","Missing"),("#f38ba8","Errors")]:
            tk.Label(lg, text="■", font=("Helvetica", 12), bg="#1e1e2e", fg=c).pack(side="left", padx=(10, 0))
            tk.Label(lg, text=l, font=("Helvetica", 9), bg="#1e1e2e", fg="#a6adc8").pack(side="left", padx=(2, 0))

        # Progress bar (custom canvas for dark green + percentage)
        self.progress_frame = tk.Frame(self, bg="#1e1e2e"); self.progress_frame.pack(fill="x", padx=20, pady=(0, 2))
        self.pbar_canvas = tk.Canvas(self.progress_frame, height=22, bg="#313244", highlightthickness=0)
        self.pbar_label = tk.Label(self.progress_frame, text="", font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086")

        # Stats
        self.stats_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.stats_var, font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086").pack(anchor="w", padx=22)

        # Table
        tf = tk.Frame(self, bg="#1e1e2e"); tf.pack(fill="both", expand=True, padx=20, pady=(4, 16))
        style = ttk.Style(self); style.theme_use("clam")
        style.configure("Treeview", background="#313244", foreground="#cdd6f4",
                         fieldbackground="#313244", rowheight=26, font=("Helvetica", 10))
        style.configure("Treeview.Heading", background="#45475a", foreground="#89b4fa",
                         font=("Helvetica", 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#585b70")], foreground=[("selected", "#cdd6f4")])

        cols = ("subfolder","poster","poster_sz","folder","folder_sz","fanart","fanart_sz",
                "backdrops","nfo","nfo_ok","xml","xml_ok","language","vid_ext","vid_size","subs")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="browse")
        for cid, h, w, a, s in [
            ("subfolder","Subfolder",240,"w",True),("poster","Poster",56,"center",False),
            ("poster_sz","Size",72,"center",False),("folder","Folder",56,"center",False),
            ("folder_sz","Size",72,"center",False),("fanart","Fanart",56,"center",False),
            ("fanart_sz","Size",72,"center",False),("backdrops","Bkdrps",50,"center",False),
            ("nfo",".nfo",44,"center",False),("nfo_ok","OK?",40,"center",False),
            ("xml",".xml",44,"center",False),("xml_ok","OK?",40,"center",False),
            ("language","Language",82,"center",False),("vid_ext","Video",52,"center",False),
            ("vid_size","Size",74,"center",False),("subs","Subtitles",170,"w",True)]:
            self.tree.heading(cid, text=h); self.tree.column(cid, width=w, anchor=a, stretch=s)

        for t in ["green","green_odd","yellow","yellow_odd","red","red_odd"]:
            bg = {"green":"#1e3a2f","green_odd":"#243d33","yellow":"#3a351e",
                  "yellow_odd":"#3d3824","red":"#3a1e1e","red_odd":"#3d2424"}[t]
            self.tree.tag_configure(t, background=bg)

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew"); tf.rowconfigure(0, weight=1); tf.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self._dblclick); self.tree.bind("<Button-3>", self._rclick)
        self.tree.bind("<Button-2>", self._rclick)
        self._ctx = tk.Menu(self, tearoff=0, bg="#313244", fg="#cdd6f4", activebackground="#585b70",
                             activeforeground="#cdd6f4", font=("Helvetica", 10))
        TreeviewTooltip(self.tree, self._tooltip)

    # ── FFmpeg status bar ────────────────────────────────────────
    def _build_ffmpeg_status(self, parent):
        for w in parent.winfo_children(): w.destroy()
        if FFMPEG_PATH and FFPROBE_PATH:
            ff_dir = os.path.dirname(FFMPEG_PATH)
            self._ff_label = tk.Label(parent, text="FFmpeg ✓", font=("Helvetica", 9, "bold"),
                                       bg="#1e1e2e", fg="#a6e3a1", cursor="hand2")
            self._ff_label.pack(side="right")
            # Tooltip on hover showing path
            self._ff_tip = None
            def _show(e):
                self._ff_tip = tw = tk.Toplevel(parent); tw.wm_overrideredirect(True)
                tw.wm_geometry(f"+{e.x_root+10}+{e.y_root+15}"); tw.configure(bg="#45475a")
                tk.Label(tw, text=f"Path: {ff_dir}\nClick to change", bg="#45475a", fg="#cdd6f4",
                         font=("Consolas", 9), padx=8, pady=4).pack()
            def _hide(e):
                if self._ff_tip: self._ff_tip.destroy(); self._ff_tip = None
            self._ff_label.bind("<Enter>", _show); self._ff_label.bind("<Leave>", _hide)
            self._ff_label.bind("<Button-1>", lambda e: self._set_ffmpeg_path())
        else:
            tk.Label(parent, text="FFmpeg ✗", font=("Helvetica", 9, "bold"),
                     bg="#1e1e2e", fg="#f38ba8").pack(side="right", padx=(0, 6))
            tk.Button(parent, text="Set path", font=("Helvetica", 8), bg="#45475a", fg="#cdd6f4",
                      relief="flat", cursor="hand2", command=self._set_ffmpeg_path
                      ).pack(side="right", padx=(0, 4))
            tk.Button(parent, text="Download", font=("Helvetica", 8), bg="#45475a", fg="#89b4fa",
                      relief="flat", cursor="hand2",
                      command=lambda: webbrowser.open("https://ffmpeg.org/download.html")
                      ).pack(side="right", padx=(0, 4))

    def _set_ffmpeg_path(self):
        path = filedialog.askdirectory(title="Select folder containing ffmpeg/ffprobe")
        if not path: return
        # Verify
        ff = os.path.join(path, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        fp = os.path.join(path, "ffprobe.exe" if os.name == "nt" else "ffprobe")
        if not os.path.isfile(ff) and not os.path.isfile(os.path.join(path, "ffmpeg")):
            messagebox.showerror("Not found", f"ffmpeg not found in:\n{path}")
            return
        cfg = _load_config()
        if not cfg.has_section("ffmpeg"): cfg.add_section("ffmpeg")
        cfg.set("ffmpeg", "path", path)
        _save_config(cfg)
        refresh_ffmpeg_paths()
        # Rebuild status
        for w in self.winfo_children():
            # Find the header frame
            pass
        # Simpler: rebuild the ffmpeg status in header
        header = self.winfo_children()[0]  # first frame = header
        ff_frame = header.winfo_children()[-1] if header.winfo_children() else header
        # Find the ff_frame
        for child in header.winfo_children():
            if isinstance(child, tk.Frame):
                ff_frame = child
        self._build_ffmpeg_status(ff_frame)
        messagebox.showinfo("FFmpeg", f"FFmpeg path set to:\n{path}")

    # ── Tooltip ──────────────────────────────────────────────────
    def _tooltip(self, iid, ci):
        d = self._item_map.get(iid)
        if not d: return None
        if ci == COL_POSTER_SZ and d["poster_exists"] and d["poster_dim"]: return f"Dimensions: {d['poster_dim']}"
        if ci == COL_FOLDER_SZ and d["folder_exists"] and d["folder_dim"]: return f"Dimensions: {d['folder_dim']}"
        if ci == COL_FANART_SZ and d["fanart_exists"] and d["fanart_dim"]: return f"Dimensions: {d['fanart_dim']}"
        return None

    # ── Double-click ─────────────────────────────────────────────
    def _dblclick(self, e):
        if self._scanning: return
        iid = self.tree.identify_row(e.y); cid = self.tree.identify_column(e.x)
        if not iid or not cid: return
        ci = int(cid.lstrip("#"))-1; d = self._item_map.get(iid)
        if not d: return
        if ci in (COL_POSTER, COL_POSTER_SZ):
            os_open(d["poster_path"]) if d["poster_exists"] else messagebox.showinfo("Missing","poster.jpg not found.")
        elif ci in (COL_FOLDER, COL_FOLDER_SZ):
            os_open(d["folder_path"]) if d["folder_exists"] else messagebox.showinfo("Missing","folder.jpg not found.")
        elif ci in (COL_FANART, COL_FANART_SZ):
            os_open(d["fanart_path"]) if d["fanart_exists"] else messagebox.showinfo("Missing","fanart.jpg not found.")
        elif ci == COL_BACKDROPS:
            os_open(d["backdrop_paths"][0]) if d["backdrop_count"]>0 else messagebox.showinfo("Missing","No backdrops.")
        elif ci in (COL_NFO, COL_NFO_OK):
            if not d["nfo_exists"]: messagebox.showinfo("Missing",f"Expected: {os.path.basename(d['nfo_path'])}")
            elif d["nfo_errors"]: ErrorDialog(self,f"NFO Errors — {d['subfolder']}",d["nfo_path"],d["nfo_errors"])
            else: os_open(d["nfo_path"])
        elif ci in (COL_XML, COL_XML_OK):
            if not d["xml_exists"]: messagebox.showinfo("Missing","movie.xml not found.")
            elif d["xml_errors"]: ErrorDialog(self,f"XML Errors — {d['subfolder']}",d["xml_path"],d["xml_errors"])
            else: os_open(d["xml_path"])
        elif ci == COL_LANGUAGE:
            if d["xml_exists"]: os_open(d["xml_path"])
        elif ci in (COL_VID_EXT, COL_VID_SIZE):
            os_open(d["video_path"]) if d["video_path"] else messagebox.showinfo("Missing","No video.")
        elif ci == COL_SUBS: SubtitleDialog(self, d["subfolder"], d)
        elif ci == COL_SUBFOLDER: os_open(d["subfolder_path"])

    # ── Right-click ──────────────────────────────────────────────
    def _rclick(self, e):
        if self._scanning: return
        iid = self.tree.identify_row(e.y)
        if not iid: return
        self.tree.selection_set(iid); d = self._item_map.get(iid)
        if not d: return
        m = self._ctx; m.delete(0, "end")
        m.add_command(label="📂  Open subfolder", command=lambda: os_open(d["subfolder_path"]))
        m.add_separator()
        for lb, ke, kp in [("🖼 poster","poster_exists","poster_path"),("🖼 folder","folder_exists","folder_path"),
                             ("🖼 fanart","fanart_exists","fanart_path")]:
            if d[ke]: p=d[kp]; m.add_command(label=lb, command=lambda p=p: os_open(p))
            else: m.add_command(label=lb+" (missing)", state="disabled")
        if d["backdrop_count"]:
            m.add_command(label=f"🖼  Backdrops ({d['backdrop_count']})", command=lambda: os_open(d["backdrop_paths"][0]))
        m.add_separator()
        if d["video_path"]:
            m.add_command(label=f"🎬 Play video", command=lambda: os_open(d["video_path"]))
            if FFMPEG_PATH:
                m.add_command(label="🎞️  Extract 10 backdrop frames",
                              command=lambda: self._do_extract(d))
        else: m.add_command(label="🎬 Video (missing)", state="disabled")
        if d["subs_internal"] or d["subs_external"]:
            m.add_command(label="💬 Subtitles…", command=lambda: SubtitleDialog(self, d["subfolder"], d))
        m.add_separator()
        if d["nfo_exists"]:
            m.add_command(label="📝 .nfo", command=lambda: os_open(d["nfo_path"]))
            if d["nfo_errors"]:
                m.add_command(label=f"⚠️ NFO errors ({len(d['nfo_errors'])})",
                              command=lambda: ErrorDialog(self,f"NFO — {d['subfolder']}",d["nfo_path"],d["nfo_errors"]))
        if d["xml_exists"]:
            m.add_command(label="📝 movie.xml", command=lambda: os_open(d["xml_path"]))
            if d["xml_errors"]:
                m.add_command(label=f"⚠️ XML errors ({len(d['xml_errors'])})",
                              command=lambda: ErrorDialog(self,f"XML — {d['subfolder']}",d["xml_path"],d["xml_errors"]))
        m.add_separator()
        m.add_command(label="🔄 Re-validate", command=lambda: self._reval(iid, d))
        m.tk_popup(e.x_root, e.y_root)

    def _reval(self, iid, data):
        sp, sn = data["subfolder_path"], data["subfolder"]
        if not os.path.isdir(sp): messagebox.showerror("Error","Folder gone."); return
        r = scan_one_subfolder(sp, sn); self._item_map[iid] = r
        for i, o in enumerate(self._results):
            if o["subfolder_path"] == sp: self._results[i] = r; break
        tag = r["row_health"] + ("_odd" if self.tree.index(iid)%2 else "")
        self.tree.item(iid, values=self._rv(r), tags=(tag,)); self._update_stats()

    # ── Extract frames ───────────────────────────────────────────
    def _extract_frames(self):
        """Extract frames from the selected row's video."""
        if self._scanning: return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a row first."); return
        d = self._item_map.get(sel[0])
        if not d: return
        self._do_extract(d)

    def _do_extract(self, d):
        if not FFMPEG_PATH:
            messagebox.showerror("FFmpeg missing", "FFmpeg is not installed or not configured.\n"
                                 "Use the FFmpeg status in the header to set the path or download it.")
            return
        if not d["video_path"]:
            messagebox.showwarning("No video", "No video file in this subfolder."); return

        dlg = FrameExtractionDialog(self, d["video_path"], d["subfolder_path"])
        self.wait_window(dlg)

        # After extraction, re-validate the row to update backdrop count
        sel = self.tree.selection()
        if sel:
            iid = sel[0]
            if iid in self._item_map:
                self._reval(iid, self._item_map[iid])

    # ── Browse / Scan / Cancel ───────────────────────────────────
    def _browse(self):
        if self._scanning: return
        p = filedialog.askdirectory(title="Select root folder")
        if p:
            self._folder = p; self.folder_var.set(p); self.stats_var.set("")
            self._results = []; self._item_map.clear()
            for r in self.tree.get_children(): self.tree.delete(r)

    def _draw_scan_progress(self, pct, text):
        c = self.pbar_canvas; c.delete("all")
        w = c.winfo_width() or 400; h = 22
        c.create_rectangle(0, 0, w, h, fill="#313244", outline="")
        fw = int(w * pct / 100)
        if fw > 0: c.create_rectangle(0, 0, fw, h, fill="#2d6e3f", outline="")
        c.create_text(w//2, h//2, text=f"{pct}%", fill="#cdd6f4", font=("Helvetica", 10, "bold"))
        self.pbar_label.configure(text=text)

    def _scan(self):
        if self._scanning: return
        if not self._folder: messagebox.showwarning("No folder", "Select a folder first."); return
        try: dirs = sorted([e for e in os.scandir(self._folder) if e.is_dir()], key=lambda e: e.name.lower())
        except PermissionError: messagebox.showerror("Error", f"Cannot access: {self._folder}"); return
        if not dirs: messagebox.showinfo("Empty","No subfolders."); return
        self._results = []; self._item_map.clear()
        for r in self.tree.get_children(): self.tree.delete(r)
        self._scanning = True; self._cancel_scan = False
        self.scan_btn.configure(state="disabled"); self.cancel_btn.pack(side="left", padx=(6, 0))
        self.pbar_canvas.pack(side="left", fill="x", expand=True)
        self.pbar_label.pack(side="left", padx=(8, 0))
        self._draw_scan_progress(0, "Starting…")
        total = len(dirs)
        def worker():
            results = []
            for i, entry in enumerate(dirs):
                if self._cancel_scan: break
                results.append(scan_one_subfolder(entry.path, entry.name))
                pct = int((i+1)/total*100)
                self.after(0, self._draw_scan_progress, pct, f"Scanning {i+1}/{total}…")
            self.after(0, _done, results)
        def _done(results):
            self._scanning = False; self.scan_btn.configure(state="normal")
            self.cancel_btn.pack_forget(); self.pbar_canvas.pack_forget(); self.pbar_label.pack_forget()
            self._results = results
            if not results: self.stats_var.set("Cancelled or empty."); return
            self._update_stats(); self._refresh_table()
        threading.Thread(target=worker, daemon=True).start()

    def _cancel(self):
        self._cancel_scan = True; self.pbar_label.configure(text="Cancelling…")

    def _update_stats(self):
        t = len(self._results)
        pc=sum(1 for r in self._results if r["poster_exists"])
        fc=sum(1 for r in self._results if r["folder_exists"])
        ac=sum(1 for r in self._results if r["fanart_exists"])
        nc=sum(1 for r in self._results if r["nfo_exists"])
        ne=sum(1 for r in self._results if r["nfo_errors"])
        xc=sum(1 for r in self._results if r["xml_exists"])
        xe=sum(1 for r in self._results if r["xml_errors"])
        vc=sum(1 for r in self._results if r["video_count"]==1)
        ul=sum(1 for r in self._results if r["language"]=="Unknown")
        self.stats_var.set("  •  ".join([f"{t} folders",f"poster:{pc}/{t}",f"folder:{fc}/{t}",
            f"fanart:{ac}/{t}",f"nfo:{nc}/{t}({ne}err)",f"xml:{xc}/{t}({xe}err)",
            f"video:{vc}/{t}"]+([f"unknown lang:{ul}"] if ul else [])))

    def _rv(self, r):
        def s(ex, cor): return STATUS_MISSING if not ex else (STATUS_ERROR if cor else STATUS_OK)
        return (r["subfolder"], s(r["poster_exists"],r["poster_corrupt"]), r["poster_size"],
                s(r["folder_exists"],r["folder_corrupt"]), r["folder_size"],
                s(r["fanart_exists"],r["fanart_corrupt"]), r["fanart_size"],
                str(r["backdrop_count"]) if r["backdrop_count"]>0 else "—",
                STATUS_OK if r["nfo_exists"] else STATUS_MISSING, r["nfo_status"],
                STATUS_OK if r["xml_exists"] else STATUS_MISSING, r["xml_status"],
                r["language"], r["video_ext"] if r["video_count"]>0 else "✗",
                r["video_size"], r["subs_summary"])

    def _refresh_table(self):
        if not self._results: return
        for r in self.tree.get_children(): self.tree.delete(r)
        self._item_map.clear(); kf, rev = SORT_OPTIONS[self.sort_var.get()]
        for i, r in enumerate(sorted(self._results, key=kf, reverse=rev)):
            tag = r["row_health"]+("_odd" if i%2 else "")
            iid = self.tree.insert("", "end", values=self._rv(r), tags=(tag,))
            self._item_map[iid] = r

    def _export_csv(self):
        if self._scanning: return
        if not self._results: messagebox.showinfo("Empty","Scan first."); return
        p = filedialog.asksaveasfilename(title="Export", defaultextension=".csv",
                                          filetypes=[("CSV","*.csv")], initialfile="scan_results.csv")
        if not p: return
        def _st(s): return "OK" if s==STATUS_OK else ("Error" if s==STATUS_ERROR else "Missing")
        try:
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Subfolder","Path","poster.jpg","Poster Size","Poster Dim","Poster Corrupt",
                            "folder.jpg","Folder Size","Folder Dim","Folder Corrupt",
                            "fanart.jpg","Fanart Size","Fanart Dim","Fanart Corrupt","Backdrops",
                            ".nfo","NFO Valid","NFO Errors","movie.xml","XML Valid","XML Errors",
                            "Language","Video Files","Video Ext","Video Size","Embedded Subs","External Subs","Health"])
                for r in self._results:
                    w.writerow([r["subfolder"],r["subfolder_path"],
                        "Y" if r["poster_exists"] else "N",r["poster_size"],r["poster_dim"] or "—","Y" if r["poster_corrupt"] else "N",
                        "Y" if r["folder_exists"] else "N",r["folder_size"],r["folder_dim"] or "—","Y" if r["folder_corrupt"] else "N",
                        "Y" if r["fanart_exists"] else "N",r["fanart_size"],r["fanart_dim"] or "—","Y" if r["fanart_corrupt"] else "N",
                        r["backdrop_count"],"Y" if r["nfo_exists"] else "N",_st(r["nfo_status"]),
                        "; ".join(f"L{e['line']}:{e['message']}" for e in r["nfo_errors"]) or "",
                        "Y" if r["xml_exists"] else "N",_st(r["xml_status"]),
                        "; ".join(f"L{e['line']}:{e['message']}" for e in r["xml_errors"]) or "",
                        r["language"],r["video_count"],r["video_ext"],r["video_size"],
                        ", ".join(s["lang"] for s in r["subs_internal"]) or "None",
                        ", ".join(f'{s["lang"]}({s["file"]})' for s in r["subs_external"]) or "None",
                        r["row_health"]])
            messagebox.showinfo("Exported", f"Saved {len(self._results)} rows to:\n{p}")
        except Exception as e: messagebox.showerror("Export failed", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()
