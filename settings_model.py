# =============================================================================
# settings_model.py
# Metadata & MediaClinic — Pure Data Model
# Version: 0.18.2                                              ### MODIFIED_BY_CLAUDE_v18.2 ###
# Author:  Luiz Junqueira & Claude AI
#
# PURPOSE
# -------
# Single source of truth for all pure data that the settings subsystem
# depends on:
#   - Application defaults (_DEFAULT_SETTINGS / DEFAULT_SETTINGS)
#   - Default NFO↔XML tag comparison pairs
#   - World language list
#   - Image quality tier tables and classification logic
#
# RULES (enforced by CLAUDE_RULES.md)
# ------------------------------------
#   • NO imports of tkinter, subprocess, shutil, os, or any I/O module
#   • NO side effects at module level beyond defining constants
#   • NO references to SETTINGS (the live dict) — only DEFAULT_SETTINGS
#   • All functions are pure (same input → same output, no state mutation)
#
# CONSUMERS
# ---------
#   mediaclinic.py      — imports DEFAULT_SETTINGS, quality tiers, helpers
#   settings_controller.py — imports DEFAULT_SETTINGS
#   settings_context.py    — imports SettingsContext (defined here)
#   settings_dialog.py     — reads context.defaults, context.poster_quality_tiers …
# =============================================================================

# ── Default settings ──────────────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "ffmpeg_path":        "",
    "text_editor":        "",          # path to preferred text editor exe
    "scraper_path":       "",          # path to video scraper exe
    "last_folder":        "",
    "last_results":       [],
    "sort_option":        "Movie Name (A-Z)",
    "extract_timeout":    60,
    "use_ffprobe":        True,        # ffprobe checkbox
    "lang_ok_code":       "PT",        # language for "OK?" column
    # Improvement thresholds
    "improve_checks": {
        "large_xml":      True,
        "nfo_xml_diff":   True,
        "ffprobe_diff":   True,
        "poster_folder":  True,
        "proportions":    True,
        "backdrops":      True,
    },
    "max_nfo_kb":         50,
    "max_xml_kb":         25,
    "min_backdrops":      5,
    "tag_pairs":          None,        # None = use DEFAULT_TAG_PAIRS
    # Phase 2 — API keys
    "tmdb_api_key":       "",
    "omdb_api_key":       "",
    # Phase 2 — Browser
    "default_browser":    "",          # path to browser exe; "" = system default
    # Phase 2 — Image minimum sizes (KB); 0 = skip check
    "min_poster_kb":      100,
    "min_folder_kb":      100,
    "min_fanart_kb":      200,
    # Phase 2 — Backdrop extraction count
    "backdrop_count":     10,
    # v0.10.0 — UI preferences
    "alternating_rows":   True,
    "show_header_tips":   True,        # v0.10.5 — show column header tooltips
    # v0.11.0 — Image quality resolution tiers      ### UPDATED v0.16.1 ###
    "poster_quality_level":  "1080p",   # default poster/folder quality minimum
    "folder_quality_level":  "1080p",
    "fanart_quality_level":  "1080p",
    "fanart_accept_168":     False,    # accept 16:8 (~1.50) ratio as valid
    "poster_accept_34":      False,    # accept 3:4 (0.75) ratio as valid (v0.12.0)
    "show_image_size":       False,    # show Size columns alongside Quality columns
    # Phase 2 — Genre list (one per line; stored as newline-joined string)
    "genre_list":         (
        "Action\nAdventure\nAnimation\nComedy\nCrime\nDocumentary\nDrama\n"
        "Family\nFantasy\nHistory\nHorror\nMusic\nMystery\nRomance\n"
        "Science Fiction\nThriller\nWar\nWestern"
    ),
    # Phase 2 — Metadata source (future scraper target)
    "metadata_source":    "tmdb",      # "tmdb" | "omdb"
    # v0.12.0 — Backup folder maintenance
    "max_backup_size_mb":    500,
    "backup_cleanup_enabled": True,
    # v0.12.0 — UI preferences (extended)
    "compact_mode":          False,
    "dark_theme":            True,
    "auto_fit_columns":      True,
    "rating_apply_all_movies": False,    ### NEW v0.15.0 ###
    "rating_use_more_votes":   False,    ### NEW v0.15.0 ###
    "column_widths":           {},       # ADDED_BY_CLAUDE_v18: persisted column widths keyed by column id
    # v0.18.2 — Health Rules (configurable rule engine)        ### ADDED_BY_CLAUDE_v18.2 ###
    "health_rules": {
        # ── Group A: Critical Error Rules (default ON) ──────────────────────
        "missing_video_file":              True,
        "corrupt_nfo":                     True,
        "missing_nfo":                     True,
        "corrupt_xml":                     True,
        "missing_xml":                     True,
        "corrupt_poster":                  True,
        "corrupt_fanart":                  True,
        "corrupt_folder":                  True,
        "missing_imdb_id":                 True,
        "corrupt_imdb_id":                 True,
        "missing_tmdb_id":                 True,
        "corrupt_tmdb_id":                 True,
        "rating_conflict":                 True,
        "no_audio_tracks":                 True,
        "video_quality_minimum":           True,
        "video_quality_minimum_level":     "720p",
        "votes_conflict":                  True,
        "genre_missing":                   True,
        "missing_movie_year":              True,
        # ── Group B: Warning Rules ───────────────────────────────────────────
        "multiple_video_files":            False,
        "missing_poster":                  True,
        "missing_fanart":                  True,
        "missing_folder":                  True,
        "poster_proportion":               True,
        "fanart_proportion":               True,
        "folder_proportion":               True,
        "poster_folder_quality_minimum":   True,
        "poster_folder_quality_level":     "1080p",
        "fanart_quality_minimum":          True,
        "fanart_quality_level_minimum":    "1080p",
        "poster_folder_identical":         True,
        "insufficient_backdrops":          True,
        "backdrop_min_count":              5,
        "backdrop_too_small":              True,
        "backdrop_min_avg_kb":             20,
        "missing_rating":                  True,
        "rating_warning":                  True,
        "suspicious_rating":               True,
        "suspicious_rating_threshold":     1.0,
        "genre_warning":                   True,
        "missing_votes":                   True,
        "votes_warning":                   True,
        "lang_not_ok":                     True,
        "missing_language_field":          True,
        "nfo_xml_too_large":               True,
        "required_audio_language":         True,
        "required_audio_language_code":    "ENG",
        "required_subtitle_language":      True,
        "required_subtitle_language_code": "POR",
        "missing_movie_title":             True,
        "title_mismatch":                  True,
        "folder_name_mismatch":            False,
    },
}

# ── Default NFO↔XML tag comparison pairs ──────────────────────────────────────
# Each tuple: (nfo_path, xml_path, label, numeric_tolerance_pct)
# nfo_path / xml_path: dot-separated path from root element
DEFAULT_TAG_PAIRS = [
    ("title",                               "LocalTitle",                  "Title",            0),
    ("originaltitle",                       "OriginalTitle",               "Original Title",   0),
    ("year",                                "ProductionYear",              "Year",             0),
    ("releasedate",                         "ReleaseDate",                 "Release Date",     0),
    ("releasedate",                         "PremiereDate",                "Premiere Date",    0),
    ("votes",                               "Votes",                       "Votes",            5),
    ("rating",                              "IMDBrating",                  "Rating (IMDB)",    5),
    ("rating",                              "Rating",                      "Rating",           5),
    ("id",                                  "IMDB_ID",                     "IMDB ID",          0),
    ("id",                                  "IMDB",                        "IMDB",             0),
    ("imdbid",                              "IMDB_ID",                     "IMDb ID",          0),
    ("imdbid",                              "IMDB",                        "IMDb",             0),
    ("tmdbid",                              "TMDbId",                      "TMDb ID",          0),
    ("tmdbid",                              "TMDB",                        "TMDb",             0),
    ("tmdbid",                              "TMDB_ID",                     "TMDb ID2",         0),
    ("country",                             "Country",                     "Country",          0),
    ("runtime",                             "RunningTime",                 "Runtime",          5),
    ("runtime",                             "Runtime",                     "Runtime2",         5),
    ("plot",                                "Overview",                    "Plot/Overview",    0),
    ("plot",                                "Synopsis",                    "Plot/Synopsis",    0),
    ("plot",                                "Plot",                        "Plot",             0),
    ("plot",                                "Description",                 "Plot/Desc",        0),
    ("outline",                             "Outline",                     "Outline",          0),
    ("genre",                               "Genres.Genre",                "Genre",            0),
    ("studio",                              "Studios.Studio",              "Studio",           0),
    ("director",                            "Director",                    "Director",         0),
    ("fileinfo.streamdetails.audio.channels",    "MediaInfo.Audio.Channels",   "Audio Channels",   5),
    ("fileinfo.streamdetails.audio.codec",       "MediaInfo.Audio.Codec",      "Audio Codec",      0),
    ("fileinfo.streamdetails.video.codec",       "MediaInfo.Video.Codec",      "Video Codec",      0),
    ("fileinfo.streamdetails.video.durationinseconds", "MediaInfo.Video.DurationSeconds", "Duration", 5),
    ("fileinfo.streamdetails.video.language",    "MediaInfo.Audio.Language",   "Video Language",   0),
    ("fileinfo.streamdetails.video.scantype",    "MediaInfo.Video.ScanType",   "Scan Type",        0),
    ("fileinfo.streamdetails.video.height",      "MediaInfo.Video.Height",     "Video Height",     0),
    ("fileinfo.streamdetails.video.width",       "MediaInfo.Video.Width",      "Video Width",      0),
]

# ── World languages (ISO 639-1 + display name) ────────────────────────────────
WORLD_LANGUAGES = [
    ("ZH", "Chinese"),    ("ES", "Spanish"),    ("EN", "English"),
    ("HI", "Hindi"),      ("AR", "Arabic"),     ("PT", "Portuguese"),
    ("BN", "Bengali"),    ("RU", "Russian"),    ("JA", "Japanese"),
    ("PA", "Punjabi"),    ("DE", "German"),     ("KO", "Korean"),
    ("FR", "French"),     ("TE", "Telugu"),     ("MR", "Marathi"),
    ("TR", "Turkish"),    ("TA", "Tamil"),      ("VI", "Vietnamese"),
    ("IT", "Italian"),    ("UR", "Urdu"),       ("FA", "Persian"),
    ("PL", "Polish"),     ("NL", "Dutch"),      ("UK", "Ukrainian"),
    ("MS", "Malay"),      ("SV", "Swedish"),    ("DA", "Danish"),
    ("FI", "Finnish"),    ("NO", "Norwegian"),  ("EL", "Greek"),
]

# ── ISO 639-1 → ISO 639-2 mapping (v0.18.2) ──────────────────────────────────
# Used to normalise external subtitle language tags for health rule comparison.
ISO_639_1_TO_2 = {                                               ### ADDED_BY_CLAUDE_v18.2 ###
    "AF": "AFR", "SQ": "ALB", "AR": "ARA", "HY": "ARM", "EU": "BAQ",
    "BE": "BEL", "BN": "BEN", "BS": "BOS", "BG": "BUL", "CA": "CAT",
    "ZH": "ZHO", "HR": "HRV", "CS": "CZE", "DA": "DAN", "NL": "NLD",
    "EN": "ENG", "ET": "EST", "FI": "FIN", "FR": "FRE", "GL": "GLG",
    "KA": "GEO", "DE": "GER", "EL": "GRE", "HE": "HEB", "HI": "HIN",
    "HU": "HUN", "IS": "ICE", "ID": "IND", "IT": "ITA", "JA": "JPN",
    "KK": "KAZ", "KO": "KOR", "LV": "LAV", "LT": "LIT", "MK": "MAC",
    "MS": "MAY", "NO": "NOR", "PL": "POL", "PT": "POR", "RO": "RUM",
    "RU": "RUS", "SR": "SRP", "SK": "SLO", "SL": "SLV", "ES": "SPA",
    "SW": "SWA", "SV": "SWE", "TH": "THA", "TR": "TUR", "UK": "UKR",
    "UR": "URD", "VI": "VIE",
}


def normalize_lang_code(code: str) -> str:                       ### ADDED_BY_CLAUDE_v18.2 ###
    """
    Normalise a language tag to uppercase ISO 639-2 (3-letter).
    Handles: 2-letter ISO 639-1, 3-letter ISO 639-2 (any case), unknown.
    Returns the input uppercased if no mapping is found.
    """
    if not code:
        return "UND"
    c = code.strip().upper()
    if len(c) == 2:
        return ISO_639_1_TO_2.get(c, c)   # map 2→3; fall back to original
    return c                               # already 3-letter (or unknown)


# ── Quality level label lists (v0.18.2) ───────────────────────────────────────
# VIDEO_QUALITY_LEVELS must match the labels returned by classify_quality()
# in mediaclinic. DO NOT change these strings.
VIDEO_QUALITY_LEVELS = [                                         ### ADDED_BY_CLAUDE_v18.2 ###
    "4K UHD", "1440p", "1080p", "720p", "576p/DVD", "480p", "360p", "240p", "SD"
]

# POSTER/FANART quality levels must match POSTER_QUALITY_TIERS /
# FANART_QUALITY_TIERS labels. DO NOT change these strings.
POSTER_QUALITY_LEVELS = ["4K", "1440p", "1080p", "720p", "540p", "480p", "360p"]  ### ADDED_BY_CLAUDE_v18.2 ###
FANART_QUALITY_LEVELS  = ["4K", "1440p", "1080p", "720p", "540p", "480p", "360p"] ### ADDED_BY_CLAUDE_v18.2 ###

AUDIO_LANGUAGES = [                                              ### ADDED_BY_CLAUDE_v18.2 ###
    ("ENG", "English"),    ("POR", "Portuguese"), ("SPA", "Spanish"),
    ("FRE", "French"),     ("GER", "German"),      ("ITA", "Italian"),
    ("JPN", "Japanese"),   ("KOR", "Korean"),      ("ZHO", "Mandarin Chinese"),
    ("RUS", "Russian"),    ("ARA", "Arabic"),       ("HIN", "Hindi"),
    ("NLD", "Dutch"),      ("POL", "Polish"),       ("TUR", "Turkish"),
]

SUBTITLE_LANGUAGES = [                                           ### ADDED_BY_CLAUDE_v18.2 ###
    ("ENG", "English"),    ("POR", "Portuguese"), ("SPA", "Spanish"),
    ("FRE", "French"),     ("GER", "German"),      ("ITA", "Italian"),
    ("JPN", "Japanese"),   ("KOR", "Korean"),      ("ZHO", "Mandarin Chinese"),
    ("RUS", "Russian"),    ("ARA", "Arabic"),       ("HIN", "Hindi"),
    ("NLD", "Dutch"),      ("POL", "Polish"),       ("TUR", "Turkish"),
]

# ══════════════════════════════════════════════════════════════════════════════
# Image Quality Tier System  (updated v0.16.1)
# ══════════════════════════════════════════════════════════════════════════════
#
# Quality is resolution-driven.  Each tier is defined by a (width, height)
# minimum.  Classification always picks the HIGHEST tier whose thresholds
# are met (±5% tolerance).  The lowest tier absorbs all images below it.

# POSTER / FOLDER  (2:3 portrait, sorted best→worst)           ### v0.16.1 ###
POSTER_QUALITY_TIERS = [
    # (label,   min_w, min_h,  total_px,  est_size_str)
    ("4K",      2000,  3000,  6_000_000, "1.5–3.0 MB"),
    ("1440p",   1500,  2250,  3_375_000, "800 KB–1.5 MB"),
    ("1080p",   1000,  1500,  1_500_000, "300–600 KB"),
    ("720p",     666,  1000,    666_000, "150–250 KB"),
    ("540p",     540,   810,    437_400, "120–150 KB"),
    ("480p",     480,   720,    345_600, "70–120 KB"),
    ("360p",     360,   540,    194_400, "40–70 KB"),
]

# FANART  (16:9 landscape, sorted best→worst)                  ### v0.16.1 ###
FANART_QUALITY_TIERS = [
    # (label,   min_w, min_h,  total_px,  est_size_str)
    ("4K",      3840,  2160,  8_294_400, "2.0–4.5 MB"),
    ("1440p",   2560,  1440,  3_686_400, "1.0–2.0 MB"),
    ("1080p",   1920,  1080,  2_073_600, "400–800 KB"),
    ("720p",    1280,   720,    921_600, "200–350 KB"),
    ("540p",     960,   540,    518_400, "130–180 KB"),
    ("480p",     854,   480,    409_920, "80–130 KB"),
    ("360p",     640,   360,    230_400, "40–75 KB"),
]

# Tolerance margin (±5%) applied to dimension comparisons
_IMG_QUALITY_TOLERANCE = 0.05


def classify_image_quality(width, height, image_type):
    """
    Classify image quality tier based on pixel dimensions.

    Parameters
    ----------
    width, height : int | None
        Actual image dimensions in pixels.
    image_type : str
        'poster', 'folder' (both use POSTER_QUALITY_TIERS) or 'fanart'.

    Returns
    -------
    str
        Tier label string.  "—" when dimensions are unavailable.
        The lowest tier (360p) absorbs all images below its threshold.
    """
    if not width or not height:
        return "—"
    if image_type in ("poster", "folder"):
        tiers = POSTER_QUALITY_TIERS
    elif image_type == "fanart":
        tiers = FANART_QUALITY_TIERS
    else:
        return "—"
    # MODIFIED_BY_CLAUDE_v18 — extracted shared tier-walk into single path
    tol = 1 - _IMG_QUALITY_TOLERANCE
    for label, mw, mh, _, _ in tiers:
        if width >= mw * tol and height >= mh * tol:
            return label
    return "360p"   # absorb all images below lowest tier


def poster_quality_sort_key(label):
    """Sort key for poster/folder quality (lower index = higher quality)."""
    order = {t[0]: i for i, t in enumerate(POSTER_QUALITY_TIERS)}
    return order.get(label, len(POSTER_QUALITY_TIERS) + 1)


def fanart_quality_sort_key(label):
    """Sort key for fanart quality (lower index = higher quality)."""
    order = {t[0]: i for i, t in enumerate(FANART_QUALITY_TIERS)}
    return order.get(label, len(FANART_QUALITY_TIERS) + 1)


def poster_quality_sort_key_missing_last(r, key, high_to_low):
    """
    Sort helper that always puts missing files at the extreme end.
    high_to_low=True  → higher quality first  → missing = last  (key 9999)
    high_to_low=False → lower quality first   → missing = first (key -1)
    """
    val = r.get(key)
    if val is None or val == "—":
        return 9999 if high_to_low else -1
    return poster_quality_sort_key(val)


def fanart_quality_sort_key_missing_last(r, key, high_to_low):
    """Same as poster_quality_sort_key_missing_last but for fanart tiers."""
    val = r.get(key)
    if val is None or val == "—":
        return 9999 if high_to_low else -1
    return fanart_quality_sort_key(val)
