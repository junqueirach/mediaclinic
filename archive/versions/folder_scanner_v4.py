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

# ── External subtitle extensions ─────────────────────────────────────────────
SUBTITLE_EXTENSIONS = {'.srt', '.sub', '.ssa', '.ass', '.vtt', '.idx', '.sup'}

# ── Column index constants ────────────────────────────────────────────────────
COL_SUBFOLDER    = 0
COL_POSTER       = 1
COL_POSTER_DIM   = 2
COL_POSTER_SIZE  = 3
COL_FANART       = 4
COL_FANART_DIM   = 5
COL_FANART_SIZE  = 6
COL_FOLDER_IMG   = 7
COL_FOLDER_DIM   = 8
COL_FOLDER_SIZE  = 9
COL_NFO          = 10
COL_NFO_STATUS   = 11
COL_XML          = 12
COL_XML_STATUS   = 13
COL_VIDEO        = 14
COL_VIDEO_EXT    = 15
COL_VIDEO_SIZE   = 16
COL_SUBS         = 17

# ── Health status constants ───────────────────────────────────────────────────
STATUS_OK      = "✅"
STATUS_MISSING = "❌"
STATUS_ERROR   = "⚠️"
STATUS_WARN    = "⚠️"

# ── ffprobe availability (checked once at startup) ────────────────────────────
FFPROBE_PATH = shutil.which("ffprobe")


# ══════════════════════════════════════════════════════════════════════════════
# Utility helpers
# ══════════════════════════════════════════════════════════════════════════════

def format_size(size_bytes):
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


def os_open(path):
    """Open a file or folder with the default OS application."""
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
                    f.read(2)
                    f.read(1)
                    hw = f.read(4)
                    if len(hw) < 4:
                        return None, None
                    height = struct.unpack(">H", hw[0:2])[0]
                    width  = struct.unpack(">H", hw[2:4])[0]
                    return width, height
                elif m in (0xD9, 0xDA):
                    return None, None
                else:
                    seg_len_data = f.read(2)
                    if len(seg_len_data) < 2:
                        return None, None
                    seg_len = struct.unpack(">H", seg_len_data)[0]
                    f.seek(seg_len - 2, 1)
    except Exception:
        return None, None


def get_png_dimensions(filepath):
    try:
        with open(filepath, "rb") as f:
            sig = f.read(8)
            if sig[:4] != b'\x89PNG':
                return None, None
            f.read(4)
            if f.read(4) != b'IHDR':
                return None, None
            data = f.read(8)
            if len(data) < 8:
                return None, None
            width  = struct.unpack(">I", data[0:4])[0]
            height = struct.unpack(">I", data[4:8])[0]
            return width, height
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
    return "—"


def is_valid_jpeg(filepath):
    try:
        if os.path.getsize(filepath) == 0:
            return False
        with open(filepath, "rb") as f:
            return f.read(2) == b'\xff\xd8'
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Video & Subtitle detection
# ══════════════════════════════════════════════════════════════════════════════

def scan_video_files(sub_path):
    """
    Find video files in a subfolder.
    Returns dict with:
      video_count, video_files (list of names), video_ext, video_path,
      video_bytes, video_size
    """
    videos = []
    try:
        for f in os.scandir(sub_path):
            if f.is_file():
                ext = os.path.splitext(f.name)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    videos.append(f)
    except PermissionError:
        pass

    if not videos:
        return {
            "video_count": 0, "video_files": [], "video_ext": "—",
            "video_path": None, "video_bytes": 0, "video_size": "—",
        }

    # Sort by size descending — the largest is likely the main movie
    videos.sort(key=lambda e: e.stat().st_size, reverse=True)
    main = videos[0]
    ext = os.path.splitext(main.name)[1].lower()
    size = main.stat().st_size

    return {
        "video_count": len(videos),
        "video_files": [v.name for v in videos],
        "video_ext":   ext.lstrip('.').upper(),
        "video_path":  main.path,
        "video_bytes": size,
        "video_size":  format_size(size),
    }


def scan_subtitles(sub_path, video_path):
    """
    Detect embedded subtitles (via ffprobe) and external .srt/.sub files.
    Returns dict with:
      subs_internal: list of {"lang": str, "title": str}
      subs_external: list of {"lang": str, "file": str}
      subs_summary:  display string
    """
    result = {
        "subs_internal": [],
        "subs_external": [],
        "subs_summary":  "—",
    }

    # ── External subtitles ───────────────────────────────────────
    try:
        for f in os.scandir(sub_path):
            if f.is_file():
                ext = os.path.splitext(f.name)[1].lower()
                if ext in SUBTITLE_EXTENSIONS:
                    # Try to extract language from filename patterns:
                    # movie.en.srt, movie.eng.srt, movie.English.srt
                    name_no_ext = os.path.splitext(f.name)[0]
                    parts = name_no_ext.rsplit('.', 1)
                    lang = parts[-1] if len(parts) > 1 else "unknown"
                    # Clean up — if the "lang" part is very long, it's likely
                    # the movie name itself (no language tag)
                    if len(lang) > 20:
                        lang = "unknown"
                    result["subs_external"].append({
                        "lang": lang,
                        "file": f.name,
                    })
    except PermissionError:
        pass

    # ── Embedded subtitles (via ffprobe) ─────────────────────────
    if video_path and FFPROBE_PATH:
        try:
            proc = subprocess.run(
                [
                    FFPROBE_PATH, "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams", "-select_streams", "s",
                    video_path
                ],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                for stream in data.get("streams", []):
                    tags = stream.get("tags", {})
                    lang = (tags.get("language")
                            or tags.get("LANGUAGE")
                            or "und")
                    title = (tags.get("title")
                             or tags.get("TITLE")
                             or "")
                    result["subs_internal"].append({
                        "lang":  lang,
                        "title": title,
                    })
        except (subprocess.TimeoutExpired, json.JSONDecodeError,
                FileNotFoundError, OSError):
            pass

    # ── Build summary string ─────────────────────────────────────
    parts = []
    if result["subs_internal"]:
        langs = [s["lang"] for s in result["subs_internal"]]
        parts.append(f"Int: {', '.join(langs)}")
    if result["subs_external"]:
        langs = [s["lang"] for s in result["subs_external"]]
        parts.append(f"Ext: {', '.join(langs)}")

    if parts:
        result["subs_summary"] = " | ".join(parts)
    elif not video_path:
        result["subs_summary"] = "—"
    else:
        result["subs_summary"] = "None"

    return result


# ══════════════════════════════════════════════════════════════════════════════
# XML / NFO Validation
# ══════════════════════════════════════════════════════════════════════════════

def _is_url_only_nfo(content):
    stripped = content.strip()
    if '\n' not in stripped and stripped.startswith(('http://', 'https://')):
        return True
    return False


def validate_xml_file(filepath, is_nfo=False):
    """
    Validate an XML file for well-formedness.
    Returns a list of error dicts: [{"line": int, "col": int, "message": str}]
    """
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

    # Strip BOM
    if content.startswith('\ufeff'):
        content = content[1:]

    # ── Pass 1: standard XML parser ──────────────────────────────
    try:
        ET.fromstring(content)
    except ET.ParseError as e:
        line, col = e.position if hasattr(e, 'position') else (0, 0)
        errors.append({"line": line, "col": col, "message": str(e)})

    # ── Pass 2: heuristic checks for common manual-edit mistakes ─
    lines = content.splitlines()

    for line_num, line_text in enumerate(lines, start=1):
        stripped_lt = line_text.strip()
        if stripped_lt.startswith('<?') or stripped_lt.startswith('<!--'):
            continue

        # Heuristic A: broken opening tag that never closes
        # FIX: if <tag ends the line, peek at following lines to see if
        #       they contain the closing > (multi-line attribute tags).
        broken = re.findall(r'<([A-Za-z_][\w.\-]*)(?=[^>]*(?:<|$))', line_text)
        for b in broken:
            segment = line_text[line_text.index(f"<{b}"):]
            after_tag = segment[1:]
            next_lt = after_tag.find('<')
            next_gt = after_tag.find('>')
            if next_gt == -1 or (next_lt != -1 and next_lt < next_gt):
                # No > on this line — check if the tag continues on next lines
                # (multi-line attributes like <set\n  tmdbcolid="591028">)
                is_multiline_tag = False
                if next_gt == -1:  # no > at all on this line
                    for peek_num in range(line_num, min(line_num + 5, len(lines))):
                        peek_line = lines[peek_num]  # 0-indexed: line_num is next
                        if '>' in peek_line:
                            # Found the closing > on a subsequent line
                            gt_pos = peek_line.index('>')
                            lt_pos = peek_line.find('<')
                            if lt_pos == -1 or gt_pos < lt_pos:
                                is_multiline_tag = True
                            break
                        if '<' in peek_line:
                            # Another tag opened before > — genuinely broken
                            break

                if not is_multiline_tag:
                    already = any(err["line"] == line_num for err in errors)
                    if not already:
                        errors.append({
                            "line": line_num,
                            "col": line_text.index(f"<{b}") + 1,
                            "message": (f"Possibly malformed tag '<{b}…' — "
                                        f"missing '>' or typo in tag name")
                        })

        # Heuristic B: closing tag missing final >
        stripped = line_text.rstrip()
        if re.search(r'</[A-Za-z_][\w.\-]*\s*$', stripped):
            if not stripped.endswith('>'):
                already = any(err["line"] == line_num for err in errors)
                if not already:
                    errors.append({
                        "line": line_num,
                        "col": len(stripped),
                        "message": "Closing tag appears to be missing final '>'"
                    })

        # Heuristic C: missing < before /tagname>
        slash_missing = re.findall(
            r'<([A-Za-z_][\w.\-]*)>([^<]*)/\1>', line_text
        )
        for tag_name, _ in slash_missing:
            already = any(err["line"] == line_num for err in errors)
            if not already:
                errors.append({
                    "line": line_num,
                    "col": line_text.index(f"/{tag_name}>") + 1,
                    "message": (f"Closing tag for '<{tag_name}>' is missing "
                                f"'<' before '/{tag_name}>'")
                })

    # Deduplicate
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
# Scanning — single subfolder
# ══════════════════════════════════════════════════════════════════════════════

def scan_one_subfolder(sub_path, sub_name):
    """Scan a single subfolder and return its result dict."""

    poster_path = os.path.join(sub_path, "poster.jpg")
    fanart_path = os.path.join(sub_path, "fanart.jpg")
    folder_path = os.path.join(sub_path, "folder.jpg")

    poster_exists = os.path.isfile(poster_path)
    fanart_exists = os.path.isfile(fanart_path)
    folder_exists = os.path.isfile(folder_path)

    poster_bytes = os.path.getsize(poster_path) if poster_exists else 0
    fanart_bytes = os.path.getsize(fanart_path) if fanart_exists else 0
    folder_bytes = os.path.getsize(folder_path) if folder_exists else 0

    poster_dim = get_image_dimensions(poster_path) if poster_exists else "—"
    fanart_dim = get_image_dimensions(fanart_path) if fanart_exists else "—"
    folder_dim = get_image_dimensions(folder_path) if folder_exists else "—"

    poster_corrupt = poster_exists and not is_valid_jpeg(poster_path)
    fanart_corrupt = fanart_exists and not is_valid_jpeg(fanart_path)
    folder_corrupt = folder_exists and not is_valid_jpeg(folder_path)

    nfo_path   = os.path.join(sub_path, sub_name + ".nfo")
    nfo_exists = os.path.isfile(nfo_path)
    nfo_bytes  = os.path.getsize(nfo_path) if nfo_exists else 0
    nfo_errors = validate_xml_file(nfo_path, is_nfo=True) if nfo_exists else []

    xml_path   = os.path.join(sub_path, "movie.xml")
    xml_exists = os.path.isfile(xml_path)
    xml_bytes  = os.path.getsize(xml_path) if xml_exists else 0
    xml_errors = validate_xml_file(xml_path, is_nfo=False) if xml_exists else []

    if nfo_exists:
        nfo_status = STATUS_ERROR if nfo_errors else STATUS_OK
    else:
        nfo_status = STATUS_MISSING

    if xml_exists:
        xml_status = STATUS_ERROR if xml_errors else STATUS_OK
    else:
        xml_status = STATUS_MISSING

    # ── Video file detection ─────────────────────────────────────
    video_info = scan_video_files(sub_path)

    # ── Subtitle detection ───────────────────────────────────────
    subs_info = scan_subtitles(sub_path, video_info["video_path"])

    # ── Video status ─────────────────────────────────────────────
    if video_info["video_count"] == 0:
        video_status = STATUS_MISSING
    elif video_info["video_count"] > 1:
        video_status = STATUS_WARN     # multiple video files — unusual
    else:
        video_status = STATUS_OK

    return {
        "subfolder":       sub_name,
        "subfolder_path":  sub_path,
        "poster_exists":   poster_exists,
        "poster_path":     poster_path,
        "poster_bytes":    poster_bytes,
        "poster_size":     format_size(poster_bytes) if poster_exists else "—",
        "poster_dim":      poster_dim,
        "poster_corrupt":  poster_corrupt,
        "fanart_exists":   fanart_exists,
        "fanart_path":     fanart_path,
        "fanart_bytes":    fanart_bytes,
        "fanart_size":     format_size(fanart_bytes) if fanart_exists else "—",
        "fanart_dim":      fanart_dim,
        "fanart_corrupt":  fanart_corrupt,
        "folder_exists":   folder_exists,
        "folder_path":     folder_path,
        "folder_bytes":    folder_bytes,
        "folder_size":     format_size(folder_bytes) if folder_exists else "—",
        "folder_dim":      folder_dim,
        "folder_corrupt":  folder_corrupt,
        "nfo_exists":      nfo_exists,
        "nfo_path":        nfo_path,
        "nfo_bytes":       nfo_bytes,
        "nfo_size":        format_size(nfo_bytes) if nfo_exists else "—",
        "nfo_status":      nfo_status,
        "nfo_errors":      nfo_errors,
        "xml_exists":      xml_exists,
        "xml_path":        xml_path,
        "xml_bytes":       xml_bytes,
        "xml_size":        format_size(xml_bytes) if xml_exists else "—",
        "xml_status":      xml_status,
        "xml_errors":      xml_errors,
        # video
        "video_count":     video_info["video_count"],
        "video_files":     video_info["video_files"],
        "video_ext":       video_info["video_ext"],
        "video_path":      video_info["video_path"],
        "video_bytes":     video_info["video_bytes"],
        "video_size":      video_info["video_size"],
        "video_status":    video_status,
        # subtitles
        "subs_internal":   subs_info["subs_internal"],
        "subs_external":   subs_info["subs_external"],
        "subs_summary":    subs_info["subs_summary"],
        # row health
        "row_health":      _row_health(
            poster_exists, fanart_exists, folder_exists,
            poster_corrupt, fanart_corrupt, folder_corrupt,
            nfo_status, xml_status, video_info["video_count"]
        ),
    }


def _row_health(poster, fanart, folder,
                poster_corrupt, fanart_corrupt, folder_corrupt,
                nfo_status, xml_status, video_count):
    """Return 'green', 'yellow', or 'red' for the row."""
    has_error = (nfo_status == STATUS_ERROR or xml_status == STATUS_ERROR
                 or poster_corrupt or fanart_corrupt or folder_corrupt)
    if has_error:
        return "red"
    all_present = poster and fanart and folder
    all_nfo_xml = nfo_status == STATUS_OK and xml_status == STATUS_OK
    has_video = video_count == 1
    if all_present and all_nfo_xml and has_video:
        return "green"
    return "yellow"


# ── Sort options ──────────────────────────────────────────────────────────────
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
    "Health (errors first)":           (lambda r: {"red": 0, "yellow": 1, "green": 2}[r["row_health"]], False),
    "Health (OK first)":               (lambda r: {"green": 0, "yellow": 1, "red": 2}[r["row_health"]], False),
}


# ══════════════════════════════════════════════════════════════════════════════
# Subtitle Detail Dialog
# ══════════════════════════════════════════════════════════════════════════════

class SubtitleDialog(tk.Toplevel):
    """Modal dialog showing subtitle details for a movie folder."""

    def __init__(self, parent, subfolder_name, data):
        super().__init__(parent)
        self.title(f"Subtitles — {subfolder_name}")
        self.geometry("620x400")
        self.configure(bg="#1e1e2e")
        self.transient(parent)
        self.grab_set()

        tk.Label(
            self, text=f"Subtitles — {subfolder_name}",
            font=("Helvetica", 13, "bold"),
            bg="#1e1e2e", fg="#89b4fa"
        ).pack(anchor="w", padx=16, pady=(14, 2))

        if data["video_path"]:
            tk.Label(
                self, text=f"Video: {os.path.basename(data['video_path'])}",
                font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086",
            ).pack(anchor="w", padx=16, pady=(0, 10))

        frame = tk.Frame(self, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        text = tk.Text(
            frame, wrap="word",
            bg="#313244", fg="#cdd6f4",
            font=("Consolas", 10),
            relief="flat", padx=10, pady=10,
        )
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        text.tag_configure("header",  foreground="#89b4fa",
                           font=("Consolas", 10, "bold"))
        text.tag_configure("lang",    foreground="#a6e3a1")
        text.tag_configure("detail",  foreground="#a6adc8")
        text.tag_configure("sep",     foreground="#45475a")
        text.tag_configure("none",    foreground="#f38ba8")

        # Internal subtitles
        text.insert("end", "  EMBEDDED SUBTITLES", "header")
        if FFPROBE_PATH:
            text.insert("end", f"  (via ffprobe)\n", "detail")
        else:
            text.insert("end", f"  (ffprobe not found — install FFmpeg)\n", "none")

        if data["subs_internal"]:
            for i, s in enumerate(data["subs_internal"], 1):
                title_str = f'  "{s["title"]}"' if s["title"] else ""
                text.insert("end", f"    {i}. ", "detail")
                text.insert("end", f'{s["lang"]}', "lang")
                text.insert("end", f"{title_str}\n", "detail")
        elif FFPROBE_PATH:
            text.insert("end", "    No embedded subtitles found\n", "none")

        text.insert("end", "\n  " + "─" * 50 + "\n\n", "sep")

        # External subtitles
        text.insert("end", "  EXTERNAL SUBTITLE FILES\n", "header")
        if data["subs_external"]:
            for i, s in enumerate(data["subs_external"], 1):
                text.insert("end", f"    {i}. ", "detail")
                text.insert("end", f'{s["lang"]}', "lang")
                text.insert("end", f'  →  {s["file"]}\n', "detail")
        else:
            text.insert("end", "    No external subtitle files found\n", "none")

        text.configure(state="disabled")

        tk.Button(
            self, text="  Close  ",
            font=("Helvetica", 10, "bold"),
            bg="#89b4fa", fg="#1e1e2e", relief="flat",
            activebackground="#74c7ec", cursor="hand2",
            command=self.destroy
        ).pack(pady=(4, 14))


# ══════════════════════════════════════════════════════════════════════════════
# Error Detail Dialog
# ══════════════════════════════════════════════════════════════════════════════

class ErrorDialog(tk.Toplevel):
    """Modal dialog showing XML/NFO validation errors."""

    def __init__(self, parent, title, filepath, errors):
        super().__init__(parent)
        self.title(title)
        self.geometry("740x440")
        self.configure(bg="#1e1e2e")
        self.transient(parent)
        self.grab_set()

        tk.Label(
            self, text=title,
            font=("Helvetica", 13, "bold"),
            bg="#1e1e2e", fg="#f38ba8"
        ).pack(anchor="w", padx=16, pady=(14, 2))

        tk.Label(
            self, text=filepath,
            font=("Consolas", 9), bg="#1e1e2e", fg="#6c7086",
            wraplength=700, justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 10))

        frame = tk.Frame(self, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        text = tk.Text(
            frame, wrap="word",
            bg="#313244", fg="#cdd6f4",
            font=("Consolas", 10),
            relief="flat", padx=10, pady=10,
            insertbackground="#cdd6f4",
            selectbackground="#585b70"
        )
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        text.tag_configure("err_header", foreground="#f38ba8",
                           font=("Consolas", 10, "bold"))
        text.tag_configure("err_detail", foreground="#fab387")
        text.tag_configure("src_line",   foreground="#a6adc8")
        text.tag_configure("separator",  foreground="#45475a")

        src_lines = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                src_lines = f.readlines()
        except Exception:
            pass

        for i, err in enumerate(errors, 1):
            loc = f"Line {err['line']}"
            if err["col"]:
                loc += f", Col {err['col']}"

            text.insert("end", f"  Error {i}:  ", "err_header")
            text.insert("end", f"{loc}\n", "err_detail")
            text.insert("end", f"    {err['message']}\n", "err_detail")

            if 0 < err["line"] <= len(src_lines):
                src_line = src_lines[err["line"] - 1].rstrip()
                text.insert("end", f"    → {src_line}\n", "src_line")

            if i < len(errors):
                text.insert("end", "    " + "─" * 60 + "\n", "separator")

        text.configure(state="disabled")

        btn_frame = tk.Frame(self, bg="#1e1e2e")
        btn_frame.pack(pady=(4, 14))

        tk.Button(
            btn_frame, text="  Open file in editor  ",
            font=("Helvetica", 10, "bold"),
            bg="#a6e3a1", fg="#1e1e2e", relief="flat",
            activebackground="#94e2d5", cursor="hand2",
            command=lambda: os_open(filepath)
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame, text="  Close  ",
            font=("Helvetica", 10, "bold"),
            bg="#89b4fa", fg="#1e1e2e", relief="flat",
            activebackground="#74c7ec", cursor="hand2",
            command=self.destroy
        ).pack(side="left")


# ══════════════════════════════════════════════════════════════════════════════
# Main Application
# ══════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎬  Subfolder Image & Metadata Scanner")
        self.geometry("1520x720")
        self.minsize(1200, 520)
        self.configure(bg="#1e1e2e")

        self._item_map: dict[str, dict] = {}
        self._results:  list[dict]      = []
        self._folder = None
        self._scanning = False
        self._cancel_scan = False
        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self, bg="#1e1e2e")
        header.pack(fill="x", padx=20, pady=(18, 6))
        tk.Label(
            header, text="🎬  Subfolder Image & Metadata Scanner",
            font=("Helvetica", 17, "bold"),
            bg="#1e1e2e", fg="#cdd6f4"
        ).pack(side="left")

        # ffprobe status
        if FFPROBE_PATH:
            tk.Label(
                header, text="ffprobe ✓",
                font=("Helvetica", 9), bg="#1e1e2e", fg="#a6e3a1"
            ).pack(side="right", padx=(0, 8))
        else:
            tk.Label(
                header, text="ffprobe ✗ (install FFmpeg for embedded subs)",
                font=("Helvetica", 9), bg="#1e1e2e", fg="#f38ba8"
            ).pack(side="right", padx=(0, 8))

        # ── Folder picker ────────────────────────────────────────
        picker = tk.Frame(self, bg="#1e1e2e")
        picker.pack(fill="x", padx=20, pady=(0, 8))

        self.folder_var = tk.StringVar(value="No folder selected")
        tk.Label(
            picker, textvariable=self.folder_var,
            font=("Helvetica", 10), bg="#313244", fg="#a6adc8",
            anchor="w", padx=10, pady=6, relief="flat"
        ).pack(side="left", fill="x", expand=True, ipady=2)

        tk.Button(
            picker, text="  Browse…  ",
            font=("Helvetica", 10, "bold"),
            bg="#89b4fa", fg="#1e1e2e", relief="flat",
            activebackground="#74c7ec", cursor="hand2",
            command=self._browse
        ).pack(side="left", padx=(8, 0))

        self.scan_btn = tk.Button(
            picker, text="  Scan  ",
            font=("Helvetica", 10, "bold"),
            bg="#a6e3a1", fg="#1e1e2e", relief="flat",
            activebackground="#94e2d5", cursor="hand2",
            command=self._scan
        )
        self.scan_btn.pack(side="left", padx=(6, 0))

        self.cancel_btn = tk.Button(
            picker, text="  Cancel  ",
            font=("Helvetica", 10, "bold"),
            bg="#f38ba8", fg="#1e1e2e", relief="flat",
            activebackground="#eba0ac", cursor="hand2",
            command=self._cancel
        )

        tk.Button(
            picker, text="  Export CSV  ",
            font=("Helvetica", 10, "bold"),
            bg="#cba6f7", fg="#1e1e2e", relief="flat",
            activebackground="#b4befe", cursor="hand2",
            command=self._export_csv
        ).pack(side="left", padx=(6, 0))

        # ── Sort + legend row ────────────────────────────────────
        sort_row = tk.Frame(self, bg="#1e1e2e")
        sort_row.pack(fill="x", padx=20, pady=(0, 4))

        tk.Label(
            sort_row, text="Sort by:",
            font=("Helvetica", 10), bg="#1e1e2e", fg="#a6adc8"
        ).pack(side="left")

        self.sort_var = tk.StringVar(value="Subfolder name (A → Z)")
        sort_menu = ttk.Combobox(
            sort_row, textvariable=self.sort_var,
            values=list(SORT_OPTIONS.keys()),
            state="readonly", width=36,
            font=("Helvetica", 10)
        )
        sort_menu.pack(side="left", padx=(8, 0))
        sort_menu.bind("<<ComboboxSelected>>", lambda _: self._refresh_table())

        legend = tk.Frame(sort_row, bg="#1e1e2e")
        legend.pack(side="right")
        for color, label in [("#a6e3a1", "All OK"),
                              ("#f9e2af", "Missing/Warn"),
                              ("#f38ba8", "Errors/Corrupt")]:
            tk.Label(legend, text="■", font=("Helvetica", 12),
                     bg="#1e1e2e", fg=color).pack(side="left", padx=(12, 0))
            tk.Label(legend, text=label, font=("Helvetica", 9),
                     bg="#1e1e2e", fg="#a6adc8").pack(side="left", padx=(2, 0))

        # ── Progress bar ─────────────────────────────────────────
        self.progress_frame = tk.Frame(self, bg="#1e1e2e")
        self.progress_frame.pack(fill="x", padx=20, pady=(0, 2))
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, variable=self.progress_var,
            maximum=100, mode="determinate"
        )
        self.progress_label = tk.Label(
            self.progress_frame, text="",
            font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086"
        )

        # ── Stats bar ────────────────────────────────────────────
        self.stats_var = tk.StringVar(value="")
        tk.Label(
            self, textvariable=self.stats_var,
            font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086"
        ).pack(anchor="w", padx=22)

        # ── Table ────────────────────────────────────────────────
        table_frame = tk.Frame(self, bg="#1e1e2e")
        table_frame.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview",
                         background="#313244", foreground="#cdd6f4",
                         fieldbackground="#313244", rowheight=26,
                         font=("Helvetica", 10))
        style.configure("Treeview.Heading",
                         background="#45475a", foreground="#89b4fa",
                         font=("Helvetica", 10, "bold"), relief="flat")
        style.map("Treeview",
                   background=[("selected", "#585b70")],
                   foreground=[("selected", "#cdd6f4")])

        columns = (
            "subfolder",
            "poster",   "poster_dim",  "poster_size",
            "fanart",   "fanart_dim",  "fanart_size",
            "folder",   "folder_dim",  "folder_size",
            "nfo",      "nfo_status",
            "xml",      "xml_status",
            "video",    "video_ext",   "video_size",
            "subs",
        )
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings",
            selectmode="browse"
        )

        headings = {
            "subfolder":    ("Subfolder",      260, "w",      True),
            "poster":       ("poster.jpg",      64, "center", False),
            "poster_dim":   ("Dimensions",      82, "center", False),
            "poster_size":  ("Size",            70, "center", False),
            "fanart":       ("fanart.jpg",      64, "center", False),
            "fanart_dim":   ("Dimensions",      82, "center", False),
            "fanart_size":  ("Size",            70, "center", False),
            "folder":       ("folder.jpg",      64, "center", False),
            "folder_dim":   ("Dimensions",      82, "center", False),
            "folder_size":  ("Size",            70, "center", False),
            "nfo":          (".nfo",            48, "center", False),
            "nfo_status":   ("NFO?",            48, "center", False),
            "xml":          ("movie.xml",       64, "center", False),
            "xml_status":   ("XML?",            48, "center", False),
            "video":        ("Video",           48, "center", False),
            "video_ext":    ("Ext.",            48, "center", False),
            "video_size":   ("Video Size",      80, "center", False),
            "subs":         ("Subtitles",      180, "w",      True),
        }
        for col_name, (text, width, anchor, stretch) in headings.items():
            self.tree.heading(col_name, text=text)
            self.tree.column(col_name, width=width, anchor=anchor, stretch=stretch)

        self.tree.tag_configure("green",      background="#1e3a2f")
        self.tree.tag_configure("green_odd",  background="#243d33")
        self.tree.tag_configure("yellow",     background="#3a351e")
        self.tree.tag_configure("yellow_odd", background="#3d3824")
        self.tree.tag_configure("red",        background="#3a1e1e")
        self.tree.tag_configure("red_odd",    background="#3d2424")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Button-2>", self._on_right_click)

        self._ctx_menu = tk.Menu(self, tearoff=0,
                                  bg="#313244", fg="#cdd6f4",
                                  activebackground="#585b70",
                                  activeforeground="#cdd6f4",
                                  font=("Helvetica", 10))

    # ══════════════════════════════════════════════════════════════
    # Double-click handler
    # ══════════════════════════════════════════════════════════════

    def _on_double_click(self, event):
        if self._scanning:
            return
        item_id = self.tree.identify_row(event.y)
        col_id  = self.tree.identify_column(event.x)
        if not item_id or not col_id:
            return
        col_index = int(col_id.lstrip("#")) - 1
        data = self._item_map.get(item_id)
        if data is None:
            return

        if col_index in (COL_POSTER, COL_POSTER_DIM, COL_POSTER_SIZE):
            if data["poster_exists"]:
                os_open(data["poster_path"])
            else:
                messagebox.showinfo("Not found", "poster.jpg missing.")

        elif col_index in (COL_FANART, COL_FANART_DIM, COL_FANART_SIZE):
            if data["fanart_exists"]:
                os_open(data["fanart_path"])
            else:
                messagebox.showinfo("Not found", "fanart.jpg missing.")

        elif col_index in (COL_FOLDER_IMG, COL_FOLDER_DIM, COL_FOLDER_SIZE):
            if data["folder_exists"]:
                os_open(data["folder_path"])
            else:
                messagebox.showinfo("Not found", "folder.jpg missing.")

        elif col_index in (COL_NFO, COL_NFO_STATUS):
            if not data["nfo_exists"]:
                messagebox.showinfo("Not found",
                    f"Expected: {os.path.basename(data['nfo_path'])}")
            elif data["nfo_errors"]:
                ErrorDialog(self, f"NFO Errors — {data['subfolder']}",
                            data["nfo_path"], data["nfo_errors"])
            else:
                os_open(data["nfo_path"])

        elif col_index in (COL_XML, COL_XML_STATUS):
            if not data["xml_exists"]:
                messagebox.showinfo("Not found", "movie.xml missing.")
            elif data["xml_errors"]:
                ErrorDialog(self, f"XML Errors — {data['subfolder']}",
                            data["xml_path"], data["xml_errors"])
            else:
                os_open(data["xml_path"])

        elif col_index in (COL_VIDEO, COL_VIDEO_EXT, COL_VIDEO_SIZE):
            if data["video_path"]:
                os_open(data["video_path"])
            else:
                messagebox.showinfo("Not found", "No video file found.")

        elif col_index == COL_SUBS:
            SubtitleDialog(self, data["subfolder"], data)

        elif col_index == COL_SUBFOLDER:
            os_open(data["subfolder_path"])

    # ══════════════════════════════════════════════════════════════
    # Right-click context menu
    # ══════════════════════════════════════════════════════════════

    def _on_right_click(self, event):
        if self._scanning:
            return
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        self.tree.selection_set(item_id)
        data = self._item_map.get(item_id)
        if data is None:
            return

        menu = self._ctx_menu
        menu.delete(0, "end")

        menu.add_command(label="📂  Open subfolder",
                         command=lambda: os_open(data["subfolder_path"]))
        menu.add_separator()

        for label, key_exists, key_path in [
            ("🖼  Open poster.jpg",  "poster_exists", "poster_path"),
            ("🖼  Open fanart.jpg",  "fanart_exists", "fanart_path"),
            ("🖼  Open folder.jpg",  "folder_exists", "folder_path"),
        ]:
            if data[key_exists]:
                path = data[key_path]
                menu.add_command(label=label, command=lambda p=path: os_open(p))
            else:
                menu.add_command(label=label + "  (missing)", state="disabled")

        menu.add_separator()

        # Video
        if data["video_path"]:
            vname = os.path.basename(data["video_path"])
            menu.add_command(label=f"🎬  Play {vname}",
                             command=lambda: os_open(data["video_path"]))
            if data["video_count"] > 1:
                menu.add_command(
                    label=f"⚠️  {data['video_count']} video files in folder",
                    state="disabled"
                )
        else:
            menu.add_command(label="🎬  Video  (missing)", state="disabled")

        # Subtitles
        has_subs = data["subs_internal"] or data["subs_external"]
        if has_subs:
            menu.add_command(
                label="💬  Subtitle details…",
                command=lambda: SubtitleDialog(self, data["subfolder"], data)
            )
        else:
            menu.add_command(label="💬  No subtitles", state="disabled")

        menu.add_separator()

        # NFO
        if data["nfo_exists"]:
            menu.add_command(label="📝  Open .nfo file",
                             command=lambda: os_open(data["nfo_path"]))
            if data["nfo_errors"]:
                n = len(data["nfo_errors"])
                menu.add_command(
                    label=f"⚠️  Show NFO errors ({n})",
                    command=lambda: ErrorDialog(
                        self, f"NFO Errors — {data['subfolder']}",
                        data["nfo_path"], data["nfo_errors"])
                )
        else:
            menu.add_command(label="📝  .nfo  (missing)", state="disabled")

        # XML
        if data["xml_exists"]:
            menu.add_command(label="📝  Open movie.xml",
                             command=lambda: os_open(data["xml_path"]))
            if data["xml_errors"]:
                n = len(data["xml_errors"])
                menu.add_command(
                    label=f"⚠️  Show XML errors ({n})",
                    command=lambda: ErrorDialog(
                        self, f"XML Errors — {data['subfolder']}",
                        data["xml_path"], data["xml_errors"])
                )
        else:
            menu.add_command(label="📝  movie.xml  (missing)", state="disabled")

        menu.add_separator()
        menu.add_command(label="🔄  Re-validate this row",
                         command=lambda: self._revalidate_row(item_id, data))

        menu.tk_popup(event.x_root, event.y_root)

    def _revalidate_row(self, item_id, data):
        sub_path = data["subfolder_path"]
        sub_name = data["subfolder"]
        if not os.path.isdir(sub_path):
            messagebox.showerror("Error", "Subfolder no longer exists.")
            return

        r = scan_one_subfolder(sub_path, sub_name)

        self._item_map[item_id] = r
        for idx, old in enumerate(self._results):
            if old["subfolder_path"] == sub_path:
                self._results[idx] = r
                break

        tag = r["row_health"]
        row_index = self.tree.index(item_id)
        if row_index % 2:
            tag = tag + "_odd"
        self.tree.item(item_id, values=self._row_values(r), tags=(tag,))
        self._update_stats()

    # ══════════════════════════════════════════════════════════════
    # Browse / Scan (THREADED) / Cancel / Refresh / Export
    # ══════════════════════════════════════════════════════════════

    def _browse(self):
        if self._scanning:
            return
        path = filedialog.askdirectory(title="Select root folder")
        if path:
            self._folder = path
            self.folder_var.set(path)
            self.stats_var.set("")
            self._results = []
            self._item_map.clear()
            for row in self.tree.get_children():
                self.tree.delete(row)

    def _scan(self):
        if self._scanning:
            return
        if not self._folder:
            messagebox.showwarning("No folder", "Please select a folder first.")
            return

        try:
            dirs = sorted(
                [e for e in os.scandir(self._folder) if e.is_dir()],
                key=lambda e: e.name.lower()
            )
        except PermissionError:
            messagebox.showerror("Permission Error",
                                 f"Cannot access: {self._folder}")
            return

        if not dirs:
            messagebox.showinfo("Empty", "No subfolders found.")
            self.stats_var.set("")
            return

        self._results = []
        self._item_map.clear()
        for row in self.tree.get_children():
            self.tree.delete(row)

        self._scanning = True
        self._cancel_scan = False
        self.scan_btn.configure(state="disabled")
        self.cancel_btn.pack(side="left", padx=(6, 0))
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.progress_label.pack(side="left", padx=(8, 0))
        self.progress_var.set(0)
        self.stats_var.set("")

        total = len(dirs)

        def worker():
            results = []
            for i, entry in enumerate(dirs):
                if self._cancel_scan:
                    break
                r = scan_one_subfolder(entry.path, entry.name)
                results.append(r)
                self.after(0, _update_progress, i + 1, total)
            self.after(0, _scan_complete, results)

        def _update_progress(current, total):
            pct = int(current / total * 100) if total else 100
            self.progress_var.set(pct)
            self.progress_label.configure(
                text=f"Scanning {current}/{total}…"
            )

        def _scan_complete(results):
            self._scanning = False
            self._cancel_scan = False
            self.scan_btn.configure(state="normal")
            self.cancel_btn.pack_forget()
            self.progress_bar.pack_forget()
            self.progress_label.pack_forget()

            self._results = results
            if not self._results:
                self.stats_var.set("Scan cancelled or no results.")
                return

            self._update_stats()
            self._refresh_table()

        threading.Thread(target=worker, daemon=True).start()

    def _cancel(self):
        self._cancel_scan = True
        self.progress_label.configure(text="Cancelling…")

    def _update_stats(self):
        total        = len(self._results)
        poster_count = sum(1 for r in self._results if r["poster_exists"])
        fanart_count = sum(1 for r in self._results if r["fanart_exists"])
        folder_count = sum(1 for r in self._results if r["folder_exists"])
        nfo_count    = sum(1 for r in self._results if r["nfo_exists"])
        nfo_err      = sum(1 for r in self._results if r["nfo_errors"])
        xml_count    = sum(1 for r in self._results if r["xml_exists"])
        xml_err      = sum(1 for r in self._results if r["xml_errors"])
        video_count  = sum(1 for r in self._results if r["video_count"] == 1)
        multi_video  = sum(1 for r in self._results if r["video_count"] > 1)
        no_video     = sum(1 for r in self._results if r["video_count"] == 0)
        corrupt      = sum(1 for r in self._results
                           if r["poster_corrupt"] or r["fanart_corrupt"]
                           or r["folder_corrupt"])

        parts = [
            f"{total} subfolder(s)",
            f"poster: {poster_count}/{total}",
            f"fanart: {fanart_count}/{total}",
            f"folder: {folder_count}/{total}",
            f"nfo: {nfo_count}/{total} ({nfo_err} errors)",
            f"xml: {xml_count}/{total} ({xml_err} errors)",
            f"video: {video_count}/{total}",
        ]
        if multi_video:
            parts.append(f"multi-video: {multi_video}")
        if no_video:
            parts.append(f"no video: {no_video}")
        if corrupt:
            parts.append(f"corrupt images: {corrupt}")

        self.stats_var.set("  •  ".join(parts))

    def _row_values(self, r):
        def img_status(exists, corrupt):
            if not exists:
                return STATUS_MISSING
            return STATUS_ERROR if corrupt else STATUS_OK

        return (
            r["subfolder"],
            img_status(r["poster_exists"], r["poster_corrupt"]),
            r["poster_dim"],
            r["poster_size"],
            img_status(r["fanart_exists"], r["fanart_corrupt"]),
            r["fanart_dim"],
            r["fanart_size"],
            img_status(r["folder_exists"], r["folder_corrupt"]),
            r["folder_dim"],
            r["folder_size"],
            STATUS_OK if r["nfo_exists"] else STATUS_MISSING,
            r["nfo_status"],
            STATUS_OK if r["xml_exists"] else STATUS_MISSING,
            r["xml_status"],
            # video
            r["video_status"],
            r["video_ext"],
            r["video_size"],
            # subtitles
            r["subs_summary"],
        )

    def _refresh_table(self):
        if not self._results:
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._item_map.clear()

        key_fn, reverse = SORT_OPTIONS[self.sort_var.get()]
        sorted_results  = sorted(self._results, key=key_fn, reverse=reverse)

        for i, r in enumerate(sorted_results):
            tag = r["row_health"]
            if i % 2:
                tag = tag + "_odd"
            iid = self.tree.insert("", "end",
                                    values=self._row_values(r),
                                    tags=(tag,))
            self._item_map[iid] = r

    def _export_csv(self):
        if self._scanning:
            return
        if not self._results:
            messagebox.showinfo("Nothing to export", "Run a scan first.")
            return

        path = filedialog.asksaveasfilename(
            title="Export scan results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="scan_results.csv"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Subfolder", "Path",
                    "poster.jpg", "Poster Dim", "Poster Size", "Poster Corrupt",
                    "fanart.jpg", "Fanart Dim", "Fanart Size", "Fanart Corrupt",
                    "folder.jpg", "Folder Dim", "Folder Size", "Folder Corrupt",
                    ".nfo exists", "NFO Size", "NFO Valid", "NFO Errors",
                    "movie.xml exists", "XML Size", "XML Valid", "XML Errors",
                    "Video Files", "Video Ext", "Video Size",
                    "Embedded Subs", "External Subs",
                    "Health"
                ])

                def _status_text(s):
                    if s == STATUS_OK:    return "OK"
                    if s == STATUS_ERROR: return "Error"
                    return "Missing"

                for r in self._results:
                    nfo_err_text = "; ".join(
                        f"L{e['line']}: {e['message']}"
                        for e in r["nfo_errors"]
                    ) if r["nfo_errors"] else ""
                    xml_err_text = "; ".join(
                        f"L{e['line']}: {e['message']}"
                        for e in r["xml_errors"]
                    ) if r["xml_errors"] else ""
                    int_subs = ", ".join(
                        s["lang"] for s in r["subs_internal"]
                    ) if r["subs_internal"] else "None"
                    ext_subs = ", ".join(
                        f'{s["lang"]} ({s["file"]})'
                        for s in r["subs_external"]
                    ) if r["subs_external"] else "None"

                    writer.writerow([
                        r["subfolder"], r["subfolder_path"],
                        "Yes" if r["poster_exists"] else "No",
                        r["poster_dim"], r["poster_size"],
                        "Yes" if r["poster_corrupt"] else "No",
                        "Yes" if r["fanart_exists"] else "No",
                        r["fanart_dim"], r["fanart_size"],
                        "Yes" if r["fanart_corrupt"] else "No",
                        "Yes" if r["folder_exists"] else "No",
                        r["folder_dim"], r["folder_size"],
                        "Yes" if r["folder_corrupt"] else "No",
                        "Yes" if r["nfo_exists"] else "No",
                        r["nfo_size"],
                        _status_text(r["nfo_status"]), nfo_err_text,
                        "Yes" if r["xml_exists"] else "No",
                        r["xml_size"],
                        _status_text(r["xml_status"]), xml_err_text,
                        r["video_count"], r["video_ext"], r["video_size"],
                        int_subs, ext_subs,
                        r["row_health"],
                    ])
            messagebox.showinfo(
                "Exported",
                f"Saved {len(self._results)} rows to:\n{path}"
            )
        except Exception as e:
            messagebox.showerror("Export failed", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()
