import os
import csv
import json
import re
import struct
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import shutil

# ── Video file extensions recognised as movie files ───────────────────────────
VIDEO_EXTENSIONS = {
    '.mkv', '.mp4', '.avi', '.m4v', '.wmv', '.mov', '.flv',
    '.ts', '.m2ts', '.mpg', '.mpeg', '.divx', '.ogm', '.webm',
}
SUBTITLE_EXTENSIONS = {'.srt', '.sub', '.ssa', '.ass', '.vtt', '.idx', '.sup'}

# ── Column indices (match the order in the Treeview) ─────────────────────────
COL_SUBFOLDER   = 0
COL_POSTER      = 1
COL_POSTER_SZ   = 2
COL_FOLDER      = 3
COL_FOLDER_SZ   = 4
COL_FANART      = 5
COL_FANART_SZ   = 6
COL_BACKDROPS   = 7
COL_NFO         = 8
COL_NFO_OK      = 9
COL_XML         = 10
COL_XML_OK      = 11
COL_LANGUAGE    = 12
COL_VID_EXT     = 13
COL_VID_SIZE    = 14
COL_SUBS        = 15

STATUS_OK      = "✅"
STATUS_MISSING = "❌"
STATUS_ERROR   = "⚠️"

FFPROBE_PATH = shutil.which("ffprobe")


# ══════════════════════════════════════════════════════════════════════════════
# Utility helpers
# ══════════════════════════════════════════════════════════════════════════════

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


def os_open(path):
    try:
        os.startfile(path)
    except AttributeError:
        try:
            subprocess.Popen(["xdg-open", path])
        except FileNotFoundError:
            subprocess.Popen(["open", path])
    except Exception as e:
        messagebox.showerror("Cannot open", str(e))


def get_jpeg_dimensions(filepath):
    try:
        with open(filepath, "rb") as f:
            if f.read(2) != b'\xff\xd8':
                return None, None
            while True:
                marker = f.read(2)
                if len(marker) < 2:
                    return None, None
                if marker[0] != 0xFF:
                    return None, None
                m = marker[1]
                while m == 0xFF:
                    byte = f.read(1)
                    if len(byte) < 1:
                        return None, None
                    m = byte[0]
                if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                         0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    f.read(2); f.read(1)
                    hw = f.read(4)
                    if len(hw) < 4:
                        return None, None
                    return struct.unpack(">H", hw[2:4])[0], struct.unpack(">H", hw[0:2])[0]
                elif m in (0xD9, 0xDA):
                    return None, None
                else:
                    d = f.read(2)
                    if len(d) < 2:
                        return None, None
                    f.seek(struct.unpack(">H", d)[0] - 2, 1)
    except Exception:
        return None, None


def get_png_dimensions(filepath):
    try:
        with open(filepath, "rb") as f:
            if f.read(8)[:4] != b'\x89PNG':
                return None, None
            f.read(4)
            if f.read(4) != b'IHDR':
                return None, None
            d = f.read(8)
            if len(d) < 8:
                return None, None
            return struct.unpack(">I", d[0:4])[0], struct.unpack(">I", d[4:8])[0]
    except Exception:
        return None, None


def get_image_dimensions(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    w, h = None, None
    if ext in ('.jpg', '.jpeg'):
        w, h = get_jpeg_dimensions(filepath)
    elif ext == '.png':
        w, h = get_png_dimensions(filepath)
    if w is not None and h is not None and (w > 0 or h > 0):
        return f"{w}×{h}"
    return None


def is_valid_jpeg(filepath):
    try:
        if os.path.getsize(filepath) == 0:
            return False
        with open(filepath, "rb") as f:
            return f.read(2) == b'\xff\xd8'
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Backdrop scanning
# ══════════════════════════════════════════════════════════════════════════════

def count_backdrops(sub_path):
    """Count backdrop images: backdrop.jpg, backdrop1.jpg, backdrop2.jpg, ..."""
    count = 0
    paths = []
    p = os.path.join(sub_path, "backdrop.jpg")
    if os.path.isfile(p):
        count += 1
        paths.append(p)
    for i in range(1, 100):
        p = os.path.join(sub_path, f"backdrop{i}.jpg")
        if os.path.isfile(p):
            count += 1
            paths.append(p)
        else:
            break
    return count, paths


# ══════════════════════════════════════════════════════════════════════════════
# Video & Subtitle detection
# ══════════════════════════════════════════════════════════════════════════════

def scan_video_files(sub_path):
    videos = []
    try:
        for f in os.scandir(sub_path):
            if f.is_file() and os.path.splitext(f.name)[1].lower() in VIDEO_EXTENSIONS:
                videos.append(f)
    except PermissionError:
        pass
    if not videos:
        return {"video_count": 0, "video_files": [], "video_ext": "—",
                "video_path": None, "video_bytes": 0, "video_size": "—"}
    videos.sort(key=lambda e: e.stat().st_size, reverse=True)
    main = videos[0]
    ext = os.path.splitext(main.name)[1].lower()
    size = main.stat().st_size
    return {"video_count": len(videos), "video_files": [v.name for v in videos],
            "video_ext": ext.lstrip('.').upper(), "video_path": main.path,
            "video_bytes": size, "video_size": format_size(size)}


def scan_subtitles(sub_path, video_path):
    result = {"subs_internal": [], "subs_external": [], "subs_summary": "—"}
    try:
        for f in os.scandir(sub_path):
            if f.is_file() and os.path.splitext(f.name)[1].lower() in SUBTITLE_EXTENSIONS:
                name_no_ext = os.path.splitext(f.name)[0]
                parts = name_no_ext.rsplit('.', 1)
                lang = parts[-1] if len(parts) > 1 and len(parts[-1]) <= 20 else "unknown"
                result["subs_external"].append({"lang": lang, "file": f.name})
    except PermissionError:
        pass
    if video_path and FFPROBE_PATH:
        try:
            proc = subprocess.run(
                [FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-select_streams", "s", video_path],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                for stream in data.get("streams", []):
                    tags = stream.get("tags", {})
                    lang = tags.get("language") or tags.get("LANGUAGE") or "und"
                    title = tags.get("title") or tags.get("TITLE") or ""
                    result["subs_internal"].append({"lang": lang, "title": title})
        except (subprocess.TimeoutExpired, json.JSONDecodeError,
                FileNotFoundError, OSError):
            pass
    parts = []
    if result["subs_internal"]:
        parts.append(f"Int: {', '.join(s['lang'] for s in result['subs_internal'])}")
    if result["subs_external"]:
        parts.append(f"Ext: {', '.join(s['lang'] for s in result['subs_external'])}")
    result["subs_summary"] = " | ".join(parts) if parts else ("None" if video_path else "—")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Language extraction from movie.xml
# ══════════════════════════════════════════════════════════════════════════════

def extract_language_from_xml(filepath):
    if not filepath or not os.path.isfile(filepath):
        return "—"
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        match = re.search(r'<Language>([^<]+)</Language>', content)
        if match:
            lang = match.group(1).strip()
            return lang if lang else "Unknown"
        if '<Language></Language>' in content or '<Language />' in content:
            return "Unknown"
        return "—"
    except Exception:
        return "—"


# ══════════════════════════════════════════════════════════════════════════════
# XML / NFO Validation
# ══════════════════════════════════════════════════════════════════════════════

def _is_url_only_nfo(content):
    stripped = content.strip()
    return '\n' not in stripped and stripped.startswith(('http://', 'https://'))


def validate_xml_file(filepath, is_nfo=False):
    errors = []
    if not os.path.isfile(filepath):
        return errors
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        errors.append({"line": 0, "col": 0, "message": f"Cannot read file: {e}"})
        return errors
    if not content.strip():
        errors.append({"line": 1, "col": 0, "message": "File is empty"})
        return errors
    if is_nfo and _is_url_only_nfo(content):
        return errors
    if content.startswith('\ufeff'):
        content = content[1:]

    # Pass 1: standard XML parser with improved error messages
    try:
        ET.fromstring(content)
    except ET.ParseError as e:
        line, col = e.position if hasattr(e, 'position') else (0, 0)
        raw_msg = str(e)
        src_lines = content.splitlines()
        if 0 < line <= len(src_lines):
            offending = src_lines[line - 1]
            # Check for unescaped &
            if re.search(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', offending):
                raw_msg = (
                    "Unescaped '&' character (should be '&amp;'). "
                    "Common in scraper-generated files — won't break KODI "
                    "but is technically invalid XML"
                )
            # For "mismatched tag" errors, scan earlier lines for the root cause
            elif "mismatched tag" in raw_msg:
                raw_msg = (
                    f"mismatched tag at line {line} — likely caused by a "
                    f"broken tag on an earlier line (check errors below)"
                )
        errors.append({"line": line, "col": col, "message": raw_msg})

    # Pass 2: heuristics for manual-edit mistakes
    lines = content.splitlines()
    for line_num, line_text in enumerate(lines, start=1):
        stripped_lt = line_text.strip()
        if stripped_lt.startswith('<?') or stripped_lt.startswith('<!--'):
            continue

        # Heuristic A: broken opening tag — with multi-line peek
        broken = re.findall(r'<([A-Za-z_][\w.\-]*)(?=[^>]*(?:<|$))', line_text)
        for b in broken:
            segment = line_text[line_text.index(f"<{b}"):]
            after_tag = segment[1:]
            next_lt = after_tag.find('<')
            next_gt = after_tag.find('>')
            if next_gt == -1 or (next_lt != -1 and next_lt < next_gt):
                is_multiline_tag = False
                if next_gt == -1:
                    for peek_num in range(line_num, min(line_num + 5, len(lines))):
                        peek_line = lines[peek_num]
                        if '>' in peek_line:
                            gt_pos = peek_line.index('>')
                            lt_pos = peek_line.find('<')
                            if lt_pos == -1 or gt_pos < lt_pos:
                                is_multiline_tag = True
                            break
                        if '<' in peek_line:
                            break
                if not is_multiline_tag:
                    if not any(err["line"] == line_num for err in errors):
                        errors.append({
                            "line": line_num,
                            "col": line_text.index(f"<{b}") + 1,
                            "message": f"Possibly malformed tag '<{b}…' — missing '>' or typo"
                        })

        # Heuristic B: closing tag missing final >
        stripped = line_text.rstrip()
        if re.search(r'</[A-Za-z_][\w.\-]*\s*$', stripped) and not stripped.endswith('>'):
            if not any(err["line"] == line_num for err in errors):
                errors.append({"line": line_num, "col": len(stripped),
                               "message": "Closing tag missing final '>'"})

        # Heuristic C: missing < before /tagname>
        # Matches both <tag>value/tag> AND <tag attr="x">value/tag>
        for tag_name, _ in re.findall(r'<([A-Za-z_][\w.\-]*)(?:\s[^>]*)?>([^<]*)/\1>', line_text):
            if not any(err["line"] == line_num for err in errors):
                errors.append({
                    "line": line_num,
                    "col": line_text.index(f"/{tag_name}>") + 1,
                    "message": f"Closing tag '/{tag_name}>' is missing '<' — should be '</{tag_name}>'"
                })

    seen = set()
    unique = []
    for err in errors:
        key = (err["line"], err["message"][:60])
        if key not in seen:
            seen.add(key)
            unique.append(err)
    unique.sort(key=lambda e: (e["line"], e["col"]))
    return unique


# ══════════════════════════════════════════════════════════════════════════════
# Scanning
# ══════════════════════════════════════════════════════════════════════════════

def scan_one_subfolder(sub_path, sub_name):
    poster_path = os.path.join(sub_path, "poster.jpg")
    fanart_path = os.path.join(sub_path, "fanart.jpg")
    folder_path = os.path.join(sub_path, "folder.jpg")

    poster_exists = os.path.isfile(poster_path)
    fanart_exists = os.path.isfile(fanart_path)
    folder_exists = os.path.isfile(folder_path)

    poster_bytes = os.path.getsize(poster_path) if poster_exists else 0
    fanart_bytes = os.path.getsize(fanart_path) if fanart_exists else 0
    folder_bytes = os.path.getsize(folder_path) if folder_exists else 0

    poster_dim = get_image_dimensions(poster_path) if poster_exists else None
    fanart_dim = get_image_dimensions(fanart_path) if fanart_exists else None
    folder_dim = get_image_dimensions(folder_path) if folder_exists else None

    poster_corrupt = poster_exists and not is_valid_jpeg(poster_path)
    fanart_corrupt = fanart_exists and not is_valid_jpeg(fanart_path)
    folder_corrupt = folder_exists and not is_valid_jpeg(folder_path)

    backdrop_count, backdrop_paths = count_backdrops(sub_path)

    nfo_path   = os.path.join(sub_path, sub_name + ".nfo")
    nfo_exists = os.path.isfile(nfo_path)
    nfo_bytes  = os.path.getsize(nfo_path) if nfo_exists else 0
    nfo_errors = validate_xml_file(nfo_path, is_nfo=True) if nfo_exists else []

    xml_path   = os.path.join(sub_path, "movie.xml")
    xml_exists = os.path.isfile(xml_path)
    xml_bytes  = os.path.getsize(xml_path) if xml_exists else 0
    xml_errors = validate_xml_file(xml_path, is_nfo=False) if xml_exists else []

    language = extract_language_from_xml(xml_path) if xml_exists else "—"

    nfo_status = (STATUS_ERROR if nfo_errors else STATUS_OK) if nfo_exists else STATUS_MISSING
    xml_status = (STATUS_ERROR if xml_errors else STATUS_OK) if xml_exists else STATUS_MISSING

    video_info = scan_video_files(sub_path)
    subs_info  = scan_subtitles(sub_path, video_info["video_path"])

    video_status = (STATUS_MISSING if video_info["video_count"] == 0
                    else STATUS_ERROR if video_info["video_count"] > 1
                    else STATUS_OK)

    return {
        "subfolder": sub_name, "subfolder_path": sub_path,
        "poster_exists": poster_exists, "poster_path": poster_path,
        "poster_bytes": poster_bytes, "poster_size": format_size(poster_bytes) if poster_exists else "—",
        "poster_dim": poster_dim, "poster_corrupt": poster_corrupt,
        "fanart_exists": fanart_exists, "fanart_path": fanart_path,
        "fanart_bytes": fanart_bytes, "fanart_size": format_size(fanart_bytes) if fanart_exists else "—",
        "fanart_dim": fanart_dim, "fanart_corrupt": fanart_corrupt,
        "folder_exists": folder_exists, "folder_path": folder_path,
        "folder_bytes": folder_bytes, "folder_size": format_size(folder_bytes) if folder_exists else "—",
        "folder_dim": folder_dim, "folder_corrupt": folder_corrupt,
        "backdrop_count": backdrop_count, "backdrop_paths": backdrop_paths,
        "nfo_exists": nfo_exists, "nfo_path": nfo_path, "nfo_bytes": nfo_bytes,
        "nfo_size": format_size(nfo_bytes) if nfo_exists else "—",
        "nfo_status": nfo_status, "nfo_errors": nfo_errors,
        "xml_exists": xml_exists, "xml_path": xml_path, "xml_bytes": xml_bytes,
        "xml_size": format_size(xml_bytes) if xml_exists else "—",
        "xml_status": xml_status, "xml_errors": xml_errors,
        "language": language,
        "video_count": video_info["video_count"], "video_files": video_info["video_files"],
        "video_ext": video_info["video_ext"], "video_path": video_info["video_path"],
        "video_bytes": video_info["video_bytes"], "video_size": video_info["video_size"],
        "video_status": video_status,
        "subs_internal": subs_info["subs_internal"], "subs_external": subs_info["subs_external"],
        "subs_summary": subs_info["subs_summary"],
        "row_health": _row_health(
            poster_exists, fanart_exists, folder_exists,
            poster_corrupt, fanart_corrupt, folder_corrupt,
            nfo_status, xml_status, video_info["video_count"]),
    }


def _row_health(poster, fanart, folder,
                poster_corrupt, fanart_corrupt, folder_corrupt,
                nfo_status, xml_status, video_count):
    has_error = (nfo_status == STATUS_ERROR or xml_status == STATUS_ERROR
                 or poster_corrupt or fanart_corrupt or folder_corrupt)
    if has_error:
        return "red"
    if poster and fanart and folder and nfo_status == STATUS_OK and xml_status == STATUS_OK and video_count == 1:
        return "green"
    return "yellow"


SORT_OPTIONS = {
    "Subfolder name (A → Z)":          (lambda r: r["subfolder"].lower(),  False),
    "Subfolder name (Z → A)":          (lambda r: r["subfolder"].lower(),  True),
    "poster.jpg size (large → small)": (lambda r: r["poster_bytes"],       True),
    "poster.jpg size (small → large)": (lambda r: r["poster_bytes"],       False),
    "fanart.jpg size (large → small)": (lambda r: r["fanart_bytes"],       True),
    "fanart.jpg size (small → large)": (lambda r: r["fanart_bytes"],       False),
    "folder.jpg size (large → small)": (lambda r: r["folder_bytes"],       True),
    "folder.jpg size (small → large)": (lambda r: r["folder_bytes"],       False),
    "Video size (large → small)":      (lambda r: r["video_bytes"],        True),
    "Video size (small → large)":      (lambda r: r["video_bytes"],        False),
    "Language (A → Z)":                (lambda r: r["language"].lower(),    False),
    "Backdrops (most → fewest)":       (lambda r: r["backdrop_count"],     True),
    "Health (errors first)":           (lambda r: {"red": 0, "yellow": 1, "green": 2}[r["row_health"]], False),
    "Health (OK first)":               (lambda r: {"green": 0, "yellow": 1, "red": 2}[r["row_health"]], False),
}


# ══════════════════════════════════════════════════════════════════════════════
# Dialogs
# ══════════════════════════════════════════════════════════════════════════════

class SubtitleDialog(tk.Toplevel):
    def __init__(self, parent, subfolder_name, data):
        super().__init__(parent)
        self.title(f"Subtitles — {subfolder_name}")
        self.geometry("620x400"); self.configure(bg="#1e1e2e")
        self.transient(parent); self.grab_set()
        tk.Label(self, text=f"Subtitles — {subfolder_name}", font=("Helvetica", 13, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(anchor="w", padx=16, pady=(14, 2))
        if data["video_path"]:
            tk.Label(self, text=f"Video: {os.path.basename(data['video_path'])}",
                     font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086").pack(anchor="w", padx=16, pady=(0, 10))
        frame = tk.Frame(self, bg="#1e1e2e"); frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        text = tk.Text(frame, wrap="word", bg="#313244", fg="#cdd6f4", font=("Consolas", 10),
                       relief="flat", padx=10, pady=10)
        sb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=sb.set); text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        text.tag_configure("header", foreground="#89b4fa", font=("Consolas", 10, "bold"))
        text.tag_configure("lang", foreground="#a6e3a1"); text.tag_configure("detail", foreground="#a6adc8")
        text.tag_configure("sep", foreground="#45475a"); text.tag_configure("none", foreground="#f38ba8")
        text.insert("end", "  EMBEDDED SUBTITLES", "header")
        text.insert("end", f"  {'(via ffprobe)' if FFPROBE_PATH else '(ffprobe not found)'}\n",
                     "detail" if FFPROBE_PATH else "none")
        if data["subs_internal"]:
            for i, s in enumerate(data["subs_internal"], 1):
                t = f'  "{s["title"]}"' if s["title"] else ""
                text.insert("end", f"    {i}. ", "detail"); text.insert("end", s["lang"], "lang")
                text.insert("end", f"{t}\n", "detail")
        elif FFPROBE_PATH:
            text.insert("end", "    No embedded subtitles found\n", "none")
        text.insert("end", "\n  " + "─" * 50 + "\n\n", "sep")
        text.insert("end", "  EXTERNAL SUBTITLE FILES\n", "header")
        if data["subs_external"]:
            for i, s in enumerate(data["subs_external"], 1):
                text.insert("end", f"    {i}. ", "detail"); text.insert("end", s["lang"], "lang")
                text.insert("end", f'  →  {s["file"]}\n', "detail")
        else:
            text.insert("end", "    No external subtitle files found\n", "none")
        text.configure(state="disabled")
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
        frame = tk.Frame(self, bg="#1e1e2e"); frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        text = tk.Text(frame, wrap="word", bg="#313244", fg="#cdd6f4", font=("Consolas", 10),
                       relief="flat", padx=10, pady=10)
        sb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=sb.set); text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        text.tag_configure("err_header", foreground="#f38ba8", font=("Consolas", 10, "bold"))
        text.tag_configure("err_detail", foreground="#fab387"); text.tag_configure("src_line", foreground="#a6adc8")
        text.tag_configure("separator", foreground="#45475a")
        src_lines = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                src_lines = f.readlines()
        except Exception:
            pass
        for i, err in enumerate(errors, 1):
            loc = f"Line {err['line']}" + (f", Col {err['col']}" if err["col"] else "")
            text.insert("end", f"  Error {i}:  ", "err_header"); text.insert("end", f"{loc}\n", "err_detail")
            text.insert("end", f"    {err['message']}\n", "err_detail")
            if 0 < err["line"] <= len(src_lines):
                text.insert("end", f"    → {src_lines[err['line']-1].rstrip()}\n", "src_line")
            if i < len(errors):
                text.insert("end", "    " + "─" * 60 + "\n", "separator")
        text.configure(state="disabled")
        bf = tk.Frame(self, bg="#1e1e2e"); bf.pack(pady=(4, 14))
        tk.Button(bf, text="  Open in editor  ", font=("Helvetica", 10, "bold"), bg="#a6e3a1", fg="#1e1e2e",
                  relief="flat", cursor="hand2", command=lambda: os_open(filepath)).pack(side="left", padx=(0, 8))
        tk.Button(bf, text="  Close  ", font=("Helvetica", 10, "bold"), bg="#89b4fa", fg="#1e1e2e",
                  relief="flat", cursor="hand2", command=self.destroy).pack(side="left")


# ══════════════════════════════════════════════════════════════════════════════
# Tooltip helper — shows image dimensions on hover over Size columns
# ══════════════════════════════════════════════════════════════════════════════

class TreeviewTooltip:
    def __init__(self, tree, get_text_fn):
        self.tree = tree
        self.get_text_fn = get_text_fn
        self.tip_window = None
        self._last_cell = (None, None)
        tree.bind("<Motion>", self._on_motion)
        tree.bind("<Leave>", self._hide)

    def _on_motion(self, event):
        item_id = self.tree.identify_row(event.y)
        col_id  = self.tree.identify_column(event.x)
        if not item_id or not col_id:
            self._hide(); return
        cell = (item_id, col_id)
        if cell == self._last_cell:
            return
        self._last_cell = cell
        col_index = int(col_id.lstrip("#")) - 1
        text = self.get_text_fn(item_id, col_index)
        if text:
            self._show(event, text)
        else:
            self._hide()

    def _show(self, event, text):
        self._hide()
        x, y = event.x_root + 16, event.y_root + 10
        self.tip_window = tw = tk.Toplevel(self.tree)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg="#45475a")
        tk.Label(tw, text=text, justify="left", bg="#45475a", fg="#cdd6f4",
                 font=("Consolas", 9, "bold"), padx=8, pady=4).pack()

    def _hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
        self._last_cell = (None, None)


# ══════════════════════════════════════════════════════════════════════════════
# Main Application
# ══════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎬  Subfolder Image & Metadata Scanner")
        self.geometry("1420x720")
        self.minsize(1100, 520)
        self.configure(bg="#1e1e2e")
        self._item_map: dict[str, dict] = {}
        self._results:  list[dict]      = []
        self._folder = None
        self._scanning = False
        self._cancel_scan = False
        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self, bg="#1e1e2e"); header.pack(fill="x", padx=20, pady=(18, 6))
        tk.Label(header, text="🎬  Subfolder Image & Metadata Scanner",
                 font=("Helvetica", 17, "bold"), bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        ffp_text = "ffprobe ✓" if FFPROBE_PATH else "ffprobe ✗ (install FFmpeg for embedded subs)"
        tk.Label(header, text=ffp_text, font=("Helvetica", 9), bg="#1e1e2e",
                 fg="#a6e3a1" if FFPROBE_PATH else "#f38ba8").pack(side="right")

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
        tk.Button(picker, text="  Export CSV  ", font=("Helvetica", 10, "bold"), bg="#cba6f7", fg="#1e1e2e",
                  relief="flat", cursor="hand2", command=self._export_csv).pack(side="left", padx=(6, 0))

        sort_row = tk.Frame(self, bg="#1e1e2e"); sort_row.pack(fill="x", padx=20, pady=(0, 4))
        tk.Label(sort_row, text="Sort by:", font=("Helvetica", 10), bg="#1e1e2e", fg="#a6adc8").pack(side="left")
        self.sort_var = tk.StringVar(value="Subfolder name (A → Z)")
        sm = ttk.Combobox(sort_row, textvariable=self.sort_var, values=list(SORT_OPTIONS.keys()),
                          state="readonly", width=36, font=("Helvetica", 10))
        sm.pack(side="left", padx=(8, 0)); sm.bind("<<ComboboxSelected>>", lambda _: self._refresh_table())
        legend = tk.Frame(sort_row, bg="#1e1e2e"); legend.pack(side="right")
        for c, l in [("#a6e3a1", "All OK"), ("#f9e2af", "Missing/Warn"), ("#f38ba8", "Errors")]:
            tk.Label(legend, text="■", font=("Helvetica", 12), bg="#1e1e2e", fg=c).pack(side="left", padx=(12, 0))
            tk.Label(legend, text=l, font=("Helvetica", 9), bg="#1e1e2e", fg="#a6adc8").pack(side="left", padx=(2, 0))

        self.progress_frame = tk.Frame(self, bg="#1e1e2e"); self.progress_frame.pack(fill="x", padx=20, pady=(0, 2))
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.progress_label = tk.Label(self.progress_frame, text="", font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086")

        self.stats_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.stats_var, font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086"
                 ).pack(anchor="w", padx=22)

        # ── Table with column-group header colors ────────────────
        table_frame = tk.Frame(self, bg="#1e1e2e")
        table_frame.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        style = ttk.Style(self)
        style.theme_use("clam")

        # Column-group header styles (distinct background per group)
        HDR_DEFAULT = "#45475a"    # subfolder, backdrops, language
        HDR_POSTER  = "#3b4261"    # blue tint
        HDR_FOLDER  = "#3b5249"    # green tint
        HDR_FANART  = "#4a3b52"    # purple tint
        HDR_NFO     = "#524a3b"    # amber tint
        HDR_XML     = "#3b4a52"    # teal tint
        HDR_VIDEO   = "#52413b"    # warm tint

        # We'll create custom heading styles per group
        for name, bg_color in [("Default", HDR_DEFAULT), ("Poster", HDR_POSTER),
                                ("Folder", HDR_FOLDER), ("Fanart", HDR_FANART),
                                ("Nfo", HDR_NFO), ("Xml", HDR_XML), ("Video", HDR_VIDEO)]:
            style.configure(f"{name}.Treeview.Heading", background=bg_color,
                            foreground="#89b4fa", font=("Helvetica", 10, "bold"), relief="flat")

        style.configure("Treeview", background="#313244", foreground="#cdd6f4",
                         fieldbackground="#313244", rowheight=26, font=("Helvetica", 10))
        style.configure("Treeview.Heading", background=HDR_DEFAULT, foreground="#89b4fa",
                         font=("Helvetica", 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#585b70")], foreground=[("selected", "#cdd6f4")])

        columns = ("subfolder", "poster", "poster_sz", "folder", "folder_sz",
                   "fanart", "fanart_sz", "backdrops", "nfo", "nfo_ok",
                   "xml", "xml_ok", "language", "vid_ext", "vid_size", "subs")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        #            col_id       heading     width  anchor   stretch
        col_defs = [
            ("subfolder",  "Subfolder",   240, "w",      True),
            ("poster",     "Poster",       56, "center", False),
            ("poster_sz",  "Size",         72, "center", False),
            ("folder",     "Folder",       56, "center", False),
            ("folder_sz",  "Size",         72, "center", False),
            ("fanart",     "Fanart",       56, "center", False),
            ("fanart_sz",  "Size",         72, "center", False),
            ("backdrops",  "Bkdrps",       50, "center", False),
            ("nfo",        ".nfo",         44, "center", False),
            ("nfo_ok",     "OK?",          40, "center", False),
            ("xml",        ".xml",         44, "center", False),
            ("xml_ok",     "OK?",          40, "center", False),
            ("language",   "Language",     82, "center", False),
            ("vid_ext",    "Video",        52, "center", False),
            ("vid_size",   "Size",         74, "center", False),
            ("subs",       "Subtitles",   170, "w",      True),
        ]
        for col_id, heading, width, anchor, stretch in col_defs:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, anchor=anchor, stretch=stretch)

        # Row color tags — health priority
        self.tree.tag_configure("green",      background="#1e3a2f")
        self.tree.tag_configure("green_odd",  background="#243d33")
        self.tree.tag_configure("yellow",     background="#3a351e")
        self.tree.tag_configure("yellow_odd", background="#3d3824")
        self.tree.tag_configure("red",        background="#3a1e1e")
        self.tree.tag_configure("red_odd",    background="#3d2424")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1); table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Button-2>", self._on_right_click)
        self._ctx_menu = tk.Menu(self, tearoff=0, bg="#313244", fg="#cdd6f4",
                                  activebackground="#585b70", activeforeground="#cdd6f4", font=("Helvetica", 10))

        # Tooltip for dimension hover on Size columns
        TreeviewTooltip(self.tree, self._get_tooltip_text)

    def _get_tooltip_text(self, item_id, col_index):
        d = self._item_map.get(item_id)
        if d is None:
            return None
        if col_index == COL_POSTER_SZ and d["poster_exists"] and d["poster_dim"]:
            return f"Dimensions: {d['poster_dim']}"
        if col_index == COL_FOLDER_SZ and d["folder_exists"] and d["folder_dim"]:
            return f"Dimensions: {d['folder_dim']}"
        if col_index == COL_FANART_SZ and d["fanart_exists"] and d["fanart_dim"]:
            return f"Dimensions: {d['fanart_dim']}"
        return None

    def _on_double_click(self, event):
        if self._scanning: return
        item_id = self.tree.identify_row(event.y); col_id = self.tree.identify_column(event.x)
        if not item_id or not col_id: return
        ci = int(col_id.lstrip("#")) - 1; d = self._item_map.get(item_id)
        if d is None: return
        if ci in (COL_POSTER, COL_POSTER_SZ):
            os_open(d["poster_path"]) if d["poster_exists"] else messagebox.showinfo("Missing", "poster.jpg not found.")
        elif ci in (COL_FOLDER, COL_FOLDER_SZ):
            os_open(d["folder_path"]) if d["folder_exists"] else messagebox.showinfo("Missing", "folder.jpg not found.")
        elif ci in (COL_FANART, COL_FANART_SZ):
            os_open(d["fanart_path"]) if d["fanart_exists"] else messagebox.showinfo("Missing", "fanart.jpg not found.")
        elif ci == COL_BACKDROPS:
            os_open(d["backdrop_paths"][0]) if d["backdrop_count"] > 0 else messagebox.showinfo("Missing", "No backdrops.")
        elif ci in (COL_NFO, COL_NFO_OK):
            if not d["nfo_exists"]: messagebox.showinfo("Missing", f"Expected: {os.path.basename(d['nfo_path'])}")
            elif d["nfo_errors"]: ErrorDialog(self, f"NFO Errors — {d['subfolder']}", d["nfo_path"], d["nfo_errors"])
            else: os_open(d["nfo_path"])
        elif ci in (COL_XML, COL_XML_OK):
            if not d["xml_exists"]: messagebox.showinfo("Missing", "movie.xml not found.")
            elif d["xml_errors"]: ErrorDialog(self, f"XML Errors — {d['subfolder']}", d["xml_path"], d["xml_errors"])
            else: os_open(d["xml_path"])
        elif ci == COL_LANGUAGE:
            if d["xml_exists"]: os_open(d["xml_path"])
        elif ci in (COL_VID_EXT, COL_VID_SIZE):
            os_open(d["video_path"]) if d["video_path"] else messagebox.showinfo("Missing", "No video file.")
        elif ci == COL_SUBS:
            SubtitleDialog(self, d["subfolder"], d)
        elif ci == COL_SUBFOLDER:
            os_open(d["subfolder_path"])

    def _on_right_click(self, event):
        if self._scanning: return
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        self.tree.selection_set(item_id); d = self._item_map.get(item_id)
        if d is None: return
        m = self._ctx_menu; m.delete(0, "end")
        m.add_command(label="📂  Open subfolder", command=lambda: os_open(d["subfolder_path"]))
        m.add_separator()
        for lbl, ke, kp in [("🖼  poster.jpg","poster_exists","poster_path"),
                              ("🖼  folder.jpg","folder_exists","folder_path"),
                              ("🖼  fanart.jpg","fanart_exists","fanart_path")]:
            if d[ke]: p=d[kp]; m.add_command(label=lbl, command=lambda p=p: os_open(p))
            else: m.add_command(label=lbl+" (missing)", state="disabled")
        if d["backdrop_count"]:
            m.add_command(label=f"🖼  Backdrops ({d['backdrop_count']})", command=lambda: os_open(d["backdrop_paths"][0]))
        m.add_separator()
        if d["video_path"]:
            m.add_command(label=f"🎬  Play {os.path.basename(d['video_path'])}", command=lambda: os_open(d["video_path"]))
        else: m.add_command(label="🎬  Video (missing)", state="disabled")
        if d["subs_internal"] or d["subs_external"]:
            m.add_command(label="💬  Subtitle details…", command=lambda: SubtitleDialog(self, d["subfolder"], d))
        m.add_separator()
        if d["nfo_exists"]:
            m.add_command(label="📝  Open .nfo", command=lambda: os_open(d["nfo_path"]))
            if d["nfo_errors"]:
                m.add_command(label=f"⚠️  NFO errors ({len(d['nfo_errors'])})",
                              command=lambda: ErrorDialog(self,f"NFO Errors — {d['subfolder']}",d["nfo_path"],d["nfo_errors"]))
        if d["xml_exists"]:
            m.add_command(label="📝  Open movie.xml", command=lambda: os_open(d["xml_path"]))
            if d["xml_errors"]:
                m.add_command(label=f"⚠️  XML errors ({len(d['xml_errors'])})",
                              command=lambda: ErrorDialog(self,f"XML Errors — {d['subfolder']}",d["xml_path"],d["xml_errors"]))
        m.add_separator()
        m.add_command(label="🔄  Re-validate", command=lambda: self._revalidate_row(item_id, d))
        m.tk_popup(event.x_root, event.y_root)

    def _revalidate_row(self, item_id, data):
        sp, sn = data["subfolder_path"], data["subfolder"]
        if not os.path.isdir(sp): messagebox.showerror("Error", "Subfolder gone."); return
        r = scan_one_subfolder(sp, sn)
        self._item_map[item_id] = r
        for i, old in enumerate(self._results):
            if old["subfolder_path"] == sp: self._results[i] = r; break
        tag = r["row_health"] + ("_odd" if self.tree.index(item_id) % 2 else "")
        self.tree.item(item_id, values=self._row_values(r), tags=(tag,)); self._update_stats()

    def _browse(self):
        if self._scanning: return
        path = filedialog.askdirectory(title="Select root folder")
        if path:
            self._folder = path; self.folder_var.set(path); self.stats_var.set("")
            self._results = []; self._item_map.clear()
            for row in self.tree.get_children(): self.tree.delete(row)

    def _scan(self):
        if self._scanning: return
        if not self._folder: messagebox.showwarning("No folder", "Select a folder first."); return
        try:
            dirs = sorted([e for e in os.scandir(self._folder) if e.is_dir()], key=lambda e: e.name.lower())
        except PermissionError:
            messagebox.showerror("Error", f"Cannot access: {self._folder}"); return
        if not dirs: messagebox.showinfo("Empty", "No subfolders."); return
        self._results = []; self._item_map.clear()
        for row in self.tree.get_children(): self.tree.delete(row)
        self._scanning = True; self._cancel_scan = False
        self.scan_btn.configure(state="disabled"); self.cancel_btn.pack(side="left", padx=(6, 0))
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.progress_label.pack(side="left", padx=(8, 0)); self.progress_var.set(0)
        total = len(dirs)
        def worker():
            results = []
            for i, entry in enumerate(dirs):
                if self._cancel_scan: break
                results.append(scan_one_subfolder(entry.path, entry.name))
                self.after(0, _prog, i+1, total)
            self.after(0, _done, results)
        def _prog(c, t):
            self.progress_var.set(int(c/t*100) if t else 100)
            self.progress_label.configure(text=f"Scanning {c}/{t}…")
        def _done(results):
            self._scanning = False; self.scan_btn.configure(state="normal")
            self.cancel_btn.pack_forget(); self.progress_bar.pack_forget(); self.progress_label.pack_forget()
            self._results = results
            if not results: self.stats_var.set("Cancelled or empty."); return
            self._update_stats(); self._refresh_table()
        threading.Thread(target=worker, daemon=True).start()

    def _cancel(self):
        self._cancel_scan = True; self.progress_label.configure(text="Cancelling…")

    def _update_stats(self):
        t = len(self._results)
        pc = sum(1 for r in self._results if r["poster_exists"])
        fc = sum(1 for r in self._results if r["folder_exists"])
        ac = sum(1 for r in self._results if r["fanart_exists"])
        nc = sum(1 for r in self._results if r["nfo_exists"])
        ne = sum(1 for r in self._results if r["nfo_errors"])
        xc = sum(1 for r in self._results if r["xml_exists"])
        xe = sum(1 for r in self._results if r["xml_errors"])
        vc = sum(1 for r in self._results if r["video_count"] == 1)
        ul = sum(1 for r in self._results if r["language"] == "Unknown")
        self.stats_var.set("  •  ".join([
            f"{t} subfolder(s)", f"poster: {pc}/{t}", f"folder: {fc}/{t}",
            f"fanart: {ac}/{t}", f"nfo: {nc}/{t} ({ne} err)", f"xml: {xc}/{t} ({xe} err)",
            f"video: {vc}/{t}"] + ([f"unknown lang: {ul}"] if ul else [])))

    def _row_values(self, r):
        def img_s(ex, cor):
            return STATUS_MISSING if not ex else (STATUS_ERROR if cor else STATUS_OK)
        return (
            r["subfolder"],
            img_s(r["poster_exists"], r["poster_corrupt"]), r["poster_size"],
            img_s(r["folder_exists"], r["folder_corrupt"]), r["folder_size"],
            img_s(r["fanart_exists"], r["fanart_corrupt"]), r["fanart_size"],
            str(r["backdrop_count"]) if r["backdrop_count"] > 0 else "—",
            STATUS_OK if r["nfo_exists"] else STATUS_MISSING, r["nfo_status"],
            STATUS_OK if r["xml_exists"] else STATUS_MISSING, r["xml_status"],
            r["language"],
            r["video_ext"] if r["video_count"] > 0 else "✗", r["video_size"],
            r["subs_summary"],
        )

    def _refresh_table(self):
        if not self._results: return
        for row in self.tree.get_children(): self.tree.delete(row)
        self._item_map.clear()
        key_fn, reverse = SORT_OPTIONS[self.sort_var.get()]
        for i, r in enumerate(sorted(self._results, key=key_fn, reverse=reverse)):
            tag = r["row_health"] + ("_odd" if i % 2 else "")
            iid = self.tree.insert("", "end", values=self._row_values(r), tags=(tag,))
            self._item_map[iid] = r

    def _export_csv(self):
        if self._scanning: return
        if not self._results: messagebox.showinfo("Empty", "Run a scan first."); return
        path = filedialog.asksaveasfilename(title="Export", defaultextension=".csv",
                                             filetypes=[("CSV","*.csv")], initialfile="scan_results.csv")
        if not path: return
        def _st(s):
            return "OK" if s == STATUS_OK else ("Error" if s == STATUS_ERROR else "Missing")
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Subfolder","Path","poster.jpg","Poster Size","Poster Dim","Poster Corrupt",
                            "folder.jpg","Folder Size","Folder Dim","Folder Corrupt",
                            "fanart.jpg","Fanart Size","Fanart Dim","Fanart Corrupt","Backdrops",
                            ".nfo exists","NFO Valid","NFO Errors","movie.xml exists","XML Valid","XML Errors",
                            "Language","Video Files","Video Ext","Video Size","Embedded Subs","External Subs","Health"])
                for r in self._results:
                    w.writerow([
                        r["subfolder"], r["subfolder_path"],
                        "Yes" if r["poster_exists"] else "No", r["poster_size"], r["poster_dim"] or "—",
                        "Yes" if r["poster_corrupt"] else "No",
                        "Yes" if r["folder_exists"] else "No", r["folder_size"], r["folder_dim"] or "—",
                        "Yes" if r["folder_corrupt"] else "No",
                        "Yes" if r["fanart_exists"] else "No", r["fanart_size"], r["fanart_dim"] or "—",
                        "Yes" if r["fanart_corrupt"] else "No", r["backdrop_count"],
                        "Yes" if r["nfo_exists"] else "No", _st(r["nfo_status"]),
                        "; ".join(f"L{e['line']}: {e['message']}" for e in r["nfo_errors"]) or "",
                        "Yes" if r["xml_exists"] else "No", _st(r["xml_status"]),
                        "; ".join(f"L{e['line']}: {e['message']}" for e in r["xml_errors"]) or "",
                        r["language"], r["video_count"], r["video_ext"], r["video_size"],
                        ", ".join(s["lang"] for s in r["subs_internal"]) or "None",
                        ", ".join(f'{s["lang"]} ({s["file"]})' for s in r["subs_external"]) or "None",
                        r["row_health"]])
            messagebox.showinfo("Exported", f"Saved {len(self._results)} rows to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()
