# MEDIACLINIC — HEALTH RULES REDESIGN PROMPT (v2.5)
### Full specification for the Health Rules system redesign.
### Application version: v0.18.2
### Read and follow this entire document before writing any code.

---

## PART 0 — CONTEXT AND SCOPE

This change redesigns how movie health status is computed and displayed.
It affects `mediaclinic_v0_18_0.py`, `settings_model.py`, `settings_dialog.py`,
and `settings_schema.json`.

The current system uses a single hardcoded function `_compute_health(row)` at
line 11044 that evaluates a fixed set of conditions and returns `"red"`,
`"yellow"`, or `"green"`. This redesign replaces it with a configurable,
rule-driven system where the user controls which conditions affect health.

This is a large change. Follow MASTER_CLAUDE_REVISION_PROMPT and CLAUDE_RULES
in full. Propose a plan first. Wait for approval before writing any code.

---

## PART 0.1 — MANDATORY PRE-CODING READS

Before proposing an implementation plan, Claude must read these functions
in full from the uploaded source files.

| Function | File | Why |
|----------|------|-----|
| `_on_settings_changed()` line 8052 | `mediaclinic_v0_18_0.py` | Insertion point for health recalculation; must not break `_post_save_refresh` |
| `_take_rescan_snapshot()` and `_rescan_changed()` lines 1429–1526 | `settings_dialog.py` | `health_rules` snapshot must follow exact same structure |
| `_offer_rescan()` line 1528 | `settings_dialog.py` | New `_offer_health_update()` is modelled on this |
| `_save_close()` line 1611 | `settings_dialog.py` | Insertion point for `_hr_vars` write-back and new scheduling |
| `_build_browser_tab()` line 650 | `settings_dialog.py` | Reference for `trace_add` + inline control pattern |

---

## PART 1 — MIGRATION CONTRACT (DO THIS FIRST)

### 1.1 — Rename the health field and its values everywhere

| Old field / value     | New field / value      |
|-----------------------|------------------------|
| `row["row_health"]`   | `row["health_status"]` |
| `"red"`               | `"error"`              |
| `"yellow"`            | `"warning"`            |
| `"green"`             | `"ok"`                 |

All call sites that read or write `row_health` must be updated. Known locations:

- `_compute_health()` definition and all callers (lines 3638, 3708, 3761,
  10638, 10708, 10761, 10777, 10821, 10822, 10924, 10925, 10995, 11036)
- `_phase_update()` tag computation
- `_scan_done()` stats computation
- `_insert_or_update()` tag computation
- `scan_one_subfolder()` return dict (line 3186)
- Stub initialization in `worker()` (line 10585: `"row_health": "yellow"`)
- Sort options `SORT_OPTIONS` (lines 3285–3287)
- `_results_from_json()` defaults dict
- Status bar update calls
- Any tag name strings built from `row_health` value

Tag names in the Treeview are built as `f"{row['health_status']}_odd"` etc.
All `tag_configure` calls using `"red"`, `"yellow"`, `"green"` as tag names
must be updated to `"error"`, `"warning"`, `"ok"`.

### 1.2 — Remove the old _compute_health function

After `compute_movie_health()` is in place, delete `_compute_health()` entirely.
Do not keep it as a shim or alias.

### 1.3 — Remove min_backdrops from the Improvements tab

`min_backdrops` currently lives in the Improvements tab (line 901) as
`_min_backdrops_var`. It must be removed from the Improvements tab UI and
from `_save_close()`. Replace all reads of `SETTINGS["min_backdrops"]` with
`SETTINGS["health_rules"].get("backdrop_min_count", 5)`, including in
`run_improvements()` (line 3376).

Keep `"min_backdrops"` in `DEFAULT_SETTINGS` and `settings_schema.json` as a
deprecated key for one version — do not write it back on save, do not show it
in the UI.

### 1.4 — New Phase 3 extractions required

The following fields must be added to each row dict during Phase 3
(metadata scan). They are needed by new health rules:

| New row key         | Source                                           | Extraction function          |
|---------------------|--------------------------------------------------|------------------------------|
| `"movie_title_raw"` | `<title>` from NFO, `<LocalTitle>` from XML      | `get_movie_titles_from_files()` (already exists, line 2996) |
| `"movie_year_raw"`  | `<year>` from NFO, `<ProductionYear>` from XML   | use existing `get_movie_year_from_files()` (line 1780) — returns int or None |

In Phase 3 of `worker()`, after the existing metadata extraction, add:

```python
# v0.18.2 — title and year raw fields for health rules
titles = get_movie_titles_from_files(nfo_p2, xml_p2)
row["movie_title_raw"]  = titles          # list of unique titles found
row["movie_year_raw"]   = get_movie_year_from_files(nfo_p2, xml_p2)  # int or None
```

Also add these fields to:
- `_results_from_json()` defaults: `"movie_title_raw": [], "movie_year_raw": None`
- Stub initialization in `worker()` Phase 1: `"movie_title_raw": [], "movie_year_raw": None`
- `scan_one_subfolder()` return dict

---

## PART 2 — THE NEW compute_movie_health() FUNCTION

### 2.1 — Signature

```python
def compute_movie_health(row: dict, rules: dict,
                         settings: dict | None = None) -> tuple[str, list[str]]:
```

Returns:
- `status`: one of `"error"`, `"warning"`, `"ok"`
- `reasons`: list of human-readable strings

`rules` = `SETTINGS["health_rules"]`.
`settings` = full `SETTINGS` dict (needed only for `nfo_xml_too_large` rule).

### 2.2 — Priority logic

```
If ANY enabled ERROR rule fires  → return ("error",  reasons)
Else if ANY WARNING rule fires   → return ("warning", reasons)
Else                             → return ("ok",      [])
```

A disabled rule (boolean key is `False`) is completely skipped.

### 2.3 — Store both outputs in the row

```python
row["health_status"]  = status
row["health_reasons"] = reasons
```

Both fields must be persisted in `_results_to_json` / `_results_from_json`
with defaults `"warning"` and `[]` respectively.

### 2.4 — Call sites

Replace every `_compute_health(row)` call with:
```python
status, reasons = compute_movie_health(row, SETTINGS["health_rules"], SETTINGS)
row["health_status"]  = status
row["health_reasons"] = reasons
```

### 2.5 — Parameter keys pattern

Rules that carry a configurable value use a paired key pattern:
- Boolean key: enables/disables the rule
- Parameter key: carries the threshold/value

See Part 4.1 for the full list.

---

## PART 3 — LANGUAGE CODE MAPPING

### 3.1 — The problem

Subtitle language codes in the movie row dict come from two sources that use
different formats:

| Source              | Field                     | Format                          | Example     |
|---------------------|---------------------------|---------------------------------|-------------|
| FFprobe (internal)  | `subs_internal[n]["lang"]`| ISO 639-2 three-letter, any case| `"por"`, `"eng"`, `"fre"` |
| External filenames  | `subs_external[n]["lang"]`| Parsed from filename suffix     | `"pt"`, `"en"`, `"fr"`, or free-form text |

External subtitle filenames produce two-letter ISO 639-1 codes when the filename
follows the convention `MovieName.pt.srt` or `MovieName.en.srt`, but may also
produce three-letter codes, full language names, or arbitrary strings depending
on the file naming convention used.

### 3.2 — Normalization approach

The `required_subtitle_language` rule stores its target as an ISO 639-2
three-letter code (e.g. `"POR"`). Before comparison, normalize all language
tags to uppercase ISO 639-2.

Define the following lookup table in `settings_model.py`:

```python
# ISO 639-1 (2-letter) → ISO 639-2 (3-letter) mapping
# Used to normalize external subtitle language tags for health rule comparison.
ISO_639_1_TO_2 = {
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
```

Also define a helper in `settings_model.py`:

```python
def normalize_lang_code(code: str) -> str:
    """
    Normalize a language tag to uppercase ISO 639-2 (3-letter).
    Handles: 2-letter ISO 639-1, 3-letter ISO 639-2 (any case), unknown.
    Returns the input uppercased if no mapping is found.
    """
    if not code:
        return "UND"
    c = code.strip().upper()
    if len(c) == 2:
        return ISO_639_1_TO_2.get(c, c)   # map 2→3; fall back to original
    return c                               # already 3-letter (or unknown)
```

### 3.3 — Usage in required_subtitle_language rule

```python
target = rules["required_subtitle_language_code"].upper()   # e.g. "POR"

found_internal = any(
    normalize_lang_code(s["lang"]) == target
    for s in row.get("subs_internal", [])
)
found_external = any(
    normalize_lang_code(s["lang"]) == target
    for s in row.get("subs_external", [])
)
if not found_internal and not found_external:
    # rule fires
```

---

## PART 4 — COMPLETE RULE INVENTORY

Every rule specifies: settings key(s), severity, exact condition, reason string.
Rules read only from the movie row dict and the `rules` / `settings` parameters.
No rule may call FFprobe, read files, or do any I/O.

---

### GROUP A — CRITICAL ERROR RULES
#### Default: all ON. Fire at ERROR level.

| Settings key             | Condition                                                    | Reason string                                  |
|--------------------------|--------------------------------------------------------------|------------------------------------------------|
| `missing_video_file`     | `row["video_count"] == 0`                                    | `"Missing video file"`                         |
| `corrupt_nfo`            | `row["nfo_status"] == STATUS_ERROR`                          | `"Corrupt NFO file (XML error)"`               |
| `missing_nfo`            | `row["nfo_status"] == STATUS_MISSING`                        | `"Missing NFO file"`                           |
| `corrupt_xml`            | `row["xml_status"] == STATUS_ERROR`                          | `"Corrupt XML file (XML error)"`               |
| `missing_xml`            | `row["xml_status"] == STATUS_MISSING`                        | `"Missing XML file"`                           |
| `corrupt_poster`         | `row["poster_status"] == STATUS_ERROR`                       | `"Corrupt poster image"`                       |
| `corrupt_fanart`         | `row["fanart_status"] == STATUS_ERROR`                       | `"Corrupt fanart image"`                       |
| `corrupt_folder`         | `row["folder_status"] == STATUS_ERROR`                       | `"Corrupt folder image"`                       |
| `missing_imdb_id`        | `row["source_imdb_status"] == STATUS_MISSING`                | `"Missing IMDB ID"`                            |
| `corrupt_imdb_id`        | `row["source_imdb_status"] == STATUS_ERROR`                  | `"IMDB ID conflict between NFO and XML"`       |
| `missing_tmdb_id`        | `row["source_tmdb_status"] == STATUS_MISSING`                | `"Missing TMDb ID"`                            |
| `corrupt_tmdb_id`        | `row["source_tmdb_status"] == STATUS_ERROR`                  | `"TMDb ID conflict between NFO and XML"`       |
| `rating_conflict`        | `row["rating_status"] == STATUS_ERROR`                       | `"Rating conflict between NFO and XML"`        |
| `votes_conflict`         | `row["votes_status"] == STATUS_ERROR`                        | `"Votes conflict between NFO and XML"`         |
| `genre_missing`          | `row["genre_status"] == STATUS_ERROR`                        | `"Missing genre information"`                  |
| `missing_movie_year`     | `row.get("movie_year_raw") is None`                          | `"Missing movie year in NFO/XML"`              |
| `no_audio_tracks`        | `row["video_count"]==1 and row.get("ffprobe_ran") and len(row.get("audio_tracks",[]))==0` | `"No audio tracks detected"` |
| `video_quality_minimum`  | See note §4.1                                                | `"Video quality below minimum ({q} < {min})"` |

**Note — `votes_conflict`:**
Fires when `row["votes_status"] == STATUS_ERROR`. This occurs when votes values
are present in both NFO and XML but conflict beyond the allowed tolerance.
It is symmetric with `rating_conflict` and belongs at ERROR level for the same
reason — conflicting data fields indicate a metadata integrity problem.

**Note — `genre_missing`:**
Fires when `row["genre_status"] == STATUS_ERROR`. `classify_genres()` returns
`STATUS_ERROR` specifically when the genres list is empty — i.e. the NFO file
has no `<genre>` tags at all. This is distinct from `genre_warning`
(`STATUS_WARN`), which fires when genres are present but non-standard or
need normalizing. An empty genre field breaks KODI library filtering.

**Note — `missing_movie_year` (moved to ERROR):**
Fires when `row.get("movie_year_raw") is None`. `get_movie_year_from_files()`
returns `None` when no valid 4-digit year is found in either NFO or XML.
Missing year breaks KODI sorting, scraper re-matching, and library organisation.
It is therefore an ERROR, not a warning. The `movie_year` display field shows
`"-"` in this case — do not use it for the rule; use `movie_year_raw` instead.

**Note §4.1 — `video_quality_minimum`:**
Fires when enabled AND `row["video_count"] == 1` AND
`row["video_quality"] not in ("—", None, "")` AND
`_quality_sort_key(row["video_quality"]) > _quality_sort_key(rules["video_quality_minimum_level"])`.
Use `_quality_sort_key()` from `mediaclinic_v0_18_0.py` (line 1211) — this is the
video-specific sort key. Do NOT use `poster_quality_sort_key()` or
`fanart_quality_sort_key()` from `settings_model.py` — those use different tier labels.
A movie with no video file is covered by `missing_video_file`.
A movie where quality is `"—"` (FFprobe not run) does NOT fire this rule.

**Note — `no_audio_tracks`:**
`audio_tracks` is always `[]` in the row dict — it is never `None` — so the
`is not None` guard is useless and must NOT be used. The real distinction needed
is whether FFprobe actually ran for this movie or not. To make this reliable,
a new boolean field `ffprobe_ran` must be added to the row dict:

In Phase 4 of `worker()` and in `scan_one_subfolder()`, after the FFprobe block:
```python
row["ffprobe_ran"] = bool(use_ff and vi["video_path"] and FFPROBE_PATH)
```

Add `"ffprobe_ran": False` to:
- Phase 1 `worker()` stub
- `_results_from_json()` defaults
- `scan_one_subfolder()` return dict

The rule then fires only when `row.get("ffprobe_ran")` is `True` AND
`len(row.get("audio_tracks", [])) == 0` AND `row["video_count"] == 1`.
This correctly distinguishes "FFprobe ran and found no audio" from
"FFprobe was not run (Quick Scan)".

---

### GROUP B — WARNING RULES
#### Default as noted. Fire at WARNING level.

| Settings key                    | Default | Condition                                         | Reason string                                          |
|---------------------------------|---------|---------------------------------------------------|--------------------------------------------------------|
| `multiple_video_files`          | OFF     | `row["video_count"] > 1`                          | `"Multiple video files in same folder"`                |
| `missing_poster`                | ON      | `not row["poster_exists"]`                        | `"Missing poster"`                                     |
| `missing_fanart`                | ON      | `not row["fanart_exists"]`                        | `"Missing fanart"`                                     |
| `missing_folder`                | ON      | `not row["folder_exists"]`                        | `"Missing folder image"`                               |
| `poster_proportion`             | ON      | `row["poster_status"] == STATUS_WARN`             | `"Poster has wrong proportions"`                       |
| `fanart_proportion`             | ON      | `row["fanart_status"] == STATUS_WARN`             | `"Fanart has wrong proportions"`                       |
| `folder_proportion`             | ON      | `row["folder_status"] == STATUS_WARN`             | `"Folder image has wrong proportions"`                 |
| `poster_folder_quality_minimum` | ON      | See note §4.2                                     | `"Poster/folder quality below minimum ({q} < {min})"` |
| `fanart_quality_minimum`        | ON      | See note §4.3                                     | `"Fanart quality below minimum ({q} < {min})"`        |
| `poster_folder_identical`       | ON      | See note §4.4                                     | `"Poster and folder image are identical (same size)"`  |
| `insufficient_backdrops`        | ON      | `row["backdrop_count"] < rules["backdrop_min_count"]` | `"Too few backdrops ({n} of {min} required)"`      |
| `backdrop_too_small`            | ON      | See note §4.5                                     | `"Backdrop images suspiciously small (avg {kb} KB)"`  |
| `missing_rating`                | ON      | `row["rating_status"] == STATUS_MISSING`          | `"Missing rating"`                                     |
| `rating_warning`                | ON      | `row["rating_status"] == STATUS_WARN`             | `"Rating present in one file only"`                    |
| `suspicious_rating`             | ON      | See note §4.6                                     | `"Suspicious rating value ({v})"`                      |
| `genre_warning`                 | ON      | `row["genre_status"] == STATUS_WARN`              | `"Genre issues detected (non-standard genres)"`        |
| `missing_votes`                 | ON      | `row["votes_status"] == STATUS_MISSING`           | `"Missing votes"`                                      |
| `votes_warning`                 | ON      | `row["votes_status"] == STATUS_WARN`              | `"Votes present in one file only"`                     |
| `lang_not_ok`                   | ON      | `row["lang_ok"] == "N"`                           | `"Target language not found in audio or subtitles"`    |
| `missing_language_field`        | ON      | `row.get("language","—") in ("—","",None)`        | `"Language field missing in XML"`                      |
| `nfo_xml_too_large`             | ON      | See note §4.7                                     | `"NFO or XML file exceeds maximum size"`               |
| `required_audio_language`       | ON      | See note §4.8                                     | `"Required audio language not found ({lang})"`         |
| `required_subtitle_language`    | ON      | See note §4.9                                     | `"Required subtitle language not found ({lang})"`      |
| `missing_movie_title`           | ON      | `len(row.get("movie_title_raw", [])) == 0`        | `"Missing movie title in NFO/XML"`                     |
| `title_mismatch`                | ON      | See note §4.10                                    | `"Title mismatch between NFO and XML"`                 |
| `folder_name_mismatch`          | OFF     | See note §4.11                                    | `"Folder name doesn't match movie title"`              |

**Note §4.2 — `poster_folder_quality_minimum`:**
Fires if enabled AND image exists AND quality is not `"—"` AND
`poster_quality_sort_key(row["poster_quality"]) > poster_quality_sort_key(rules["poster_folder_quality_level"])`.
Checked independently for poster and folder image — either can trigger the rule.
Missing images are not checked by this rule (`missing_poster`/`missing_folder`
cover that).

**Note §4.3 — `fanart_quality_minimum`:**
Same pattern as §4.2 but uses `fanart_quality_sort_key` and
`rules["fanart_quality_level_minimum"]`.

**Note §4.4 — `poster_folder_identical`:**
Fires when enabled AND `row["poster_exists"]` AND `row["folder_exists"]` AND
`row["poster_bytes"] > 0` AND `row["poster_bytes"] == row["folder_bytes"]`.
Byte-size equality is used as the proxy for identical files — exact enough
for practical purposes and requires no I/O at rule evaluation time.

**Note §4.5 — `backdrop_too_small`:**
Fires when enabled AND `row["backdrop_count"] > 0` AND
`row["backdrop_avg_bytes"] > 0` AND
`row["backdrop_avg_bytes"] < rules["backdrop_min_avg_kb"] * 1024`.
Does not fire when `backdrop_count == 0` (missing backdrops rule covers that).
Default threshold: 20 KB.

**Note §4.6 — `suspicious_rating`:**
Fires when enabled AND `row["rating_value"] is not None` AND
`row["rating_value"] >= 0.0` (not the sentinel `-1.0`) AND
`row["rating_value"] < rules["suspicious_rating_threshold"]`.
Default threshold: `1.0`.

**Note §4.7 — `nfo_xml_too_large`:**
Fires when enabled AND (`settings` param is not None) AND:
- `row["nfo_exists"] AND row["nfo_bytes"] > settings["max_nfo_kb"] * 1024`, OR
- `row["xml_exists"] AND row["xml_bytes"] > settings["max_xml_kb"] * 1024`
When `settings` is None, skip this rule silently.

**Note §4.8 — `required_audio_language`:**
Fires when enabled AND `row["video_count"] == 1` AND
`row.get("audio_tracks")` is a non-empty list (FFprobe was run) AND
`not any(t["language"].upper() == rules["required_audio_language_code"].upper()
         for t in row["audio_tracks"])`.
Do not fire when `row.get("ffprobe_ran")` is `False` — empty `audio_tracks`
without FFprobe having run is indeterminate, not confirmed absent.

**Note §4.9 — `required_subtitle_language`:**
Uses `normalize_lang_code()` from Part 3 for all comparisons.
Fires when enabled AND `row["video_count"] == 1` AND
BOTH internal AND external subtitle lists are missing the required language:
```python
target = rules["required_subtitle_language_code"].upper()
found = any(normalize_lang_code(s["lang"]) == target
            for s in row.get("subs_internal", []) + row.get("subs_external", []))
if not found: # rule fires
```

**Note §4.10 — `title_mismatch`:**
Fires when enabled AND `len(row.get("movie_title_raw", [])) >= 2`.
`get_movie_titles_from_files()` returns only unique non-empty titles from both
NFO and XML. If it returns 2 or more distinct values, the titles disagree.

**Note §4.11 — `folder_name_mismatch`:**
Fires when enabled AND `len(row.get("movie_title_raw", [])) >= 1` AND
the folder name (`row["subfolder"]`) does not match the primary title
(`row["movie_title_raw"][0]`) after normalizing both:
- Strip year suffix `(YYYY)` from folder name
- Lowercase both, strip punctuation and extra whitespace
- Compare using `difflib.SequenceMatcher(None, norm_folder, norm_title).ratio()`
  from the Python standard library. If ratio < 0.60, fire the rule.
  `difflib` is already in the standard library — no new dependency.
Default: OFF. Many users name folders differently from titles intentionally.

---

### RULES NOT INCLUDED IN v1 (deferred)

The following require new Phase 3 extraction beyond what is added in §1.4:

- Missing plot, director, cast, runtime, certification, country, trailer

---

## PART 5 — SETTINGS MODEL CHANGES

### 5.1 — New key in DEFAULT_SETTINGS

```python
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
    "genre_missing":                   True,
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
```

### 5.2 — Language and quality lists (add to settings_model.py)

```python
# VIDEO_QUALITY_LEVELS must match the labels returned by classify_quality()
# exactly (line 1192 of mediaclinic_v0_18_0.py). DO NOT change these strings.
VIDEO_QUALITY_LEVELS = [
    "4K UHD", "1440p", "1080p", "720p", "576p/DVD", "480p", "360p", "240p", "SD"
]

# POSTER/FANART quality levels must match POSTER_QUALITY_TIERS and
# FANART_QUALITY_TIERS labels (settings_model.py). DO NOT change these strings.
POSTER_QUALITY_LEVELS = ["4K", "1440p", "1080p", "720p", "540p", "480p", "360p"]
FANART_QUALITY_LEVELS  = ["4K", "1440p", "1080p", "720p", "540p", "480p", "360p"]
# NOTE: video quality and image quality use DIFFERENT tier labels.
# Video: classify_quality() uses _quality_sort_key() (line 1211) for comparison.
# Image: classify_image_quality() uses poster_quality_sort_key() /
#        fanart_quality_sort_key() (settings_model.py) for comparison.
# Never mix these two sort key functions.

AUDIO_LANGUAGES = [
    ("ENG", "English"),    ("POR", "Portuguese"), ("SPA", "Spanish"),
    ("FRE", "French"),     ("GER", "German"),      ("ITA", "Italian"),
    ("JPN", "Japanese"),   ("KOR", "Korean"),      ("ZHO", "Mandarin Chinese"),
    ("RUS", "Russian"),    ("ARA", "Arabic"),       ("HIN", "Hindi"),
    ("NLD", "Dutch"),      ("POL", "Polish"),       ("TUR", "Turkish"),
]

SUBTITLE_LANGUAGES = [
    ("ENG", "English"),    ("POR", "Portuguese"), ("SPA", "Spanish"),
    ("FRE", "French"),     ("GER", "German"),      ("ITA", "Italian"),
    ("JPN", "Japanese"),   ("KOR", "Korean"),      ("ZHO", "Mandarin Chinese"),
    ("RUS", "Russian"),    ("ARA", "Arabic"),       ("HIN", "Hindi"),
    ("NLD", "Dutch"),      ("POL", "Polish"),       ("TUR", "Turkish"),
]

```

### 5.3 — settings_schema.json

Add a `"health_rules"` object property with `additionalProperties: false`.
Type each sub-key appropriately:
- Boolean keys: `{ "type": "boolean", "default": true/false }`
- Integer keys: `{ "type": "integer", "minimum": 0, "default": N }`
- Float keys: `{ "type": "number", "minimum": 0.0, "default": N }`
- String keys: `{ "type": "string", "default": "..." }`

### 5.4 — Deep merge in settings loader

`health_rules` must receive the same deep-merge treatment as `improve_checks`:
missing keys are filled from `DEFAULT_SETTINGS["health_rules"]` at load time.

---

## PART 6 — NEW SETTINGS TAB: "Health Rules"

### 6.1 — Tab registry position

```python
(10, "Health Rules",   "_build_health_rules_tab"),
(11, "Backup",         "_build_backup_tab"),
```

Update `CLAUDE_RULES.md` and `settings_test_harness.py` T04 to expect 12 tabs.

### 6.2 — Widget variable naming

```python
self._hr_vars      # dict: key (str) → tk.BooleanVar
self._hr_int_vars  # dict: key (str) → tk.IntVar
self._hr_flt_vars  # dict: key (str) → tk.DoubleVar  (replaces _hr_str for floats)
self._hr_str_vars  # dict: key (str) → tk.StringVar
```

In `_save_close()`:
```python
hr = ctx.settings.setdefault("health_rules", {})
for k, v in self._hr_vars.items():     hr[k] = v.get()
for k, v in self._hr_int_vars.items(): hr[k] = v.get()
for k, v in self._hr_flt_vars.items(): hr[k] = round(v.get(), 2)
for k, v in self._hr_str_vars.items(): hr[k] = v.get()
```

Add all four dicts to the protected variable list in `CLAUDE_RULES.md`.

### 6.3 — Tab layout

Tab content must be inside a scrollable frame (Canvas + Scrollbar), same
pattern as the Tags tab. Group separators use `ttk.Separator` with bold label.

Inline controls appear on the same row as the checkbox, greyed when checkbox
is unchecked. Bind each checkbox BooleanVar with `trace_add("write", cb)` to
update inline control state. Trace callbacks must not cause infinite loops.

```
┌───────────────────────────────────────────────────────────────────────┐
│  Health Rules control which conditions affect each movie's health      │
│  status. Rules that are OFF are ignored and treated as OK.             │
│                                                                        │
│  [Reset to defaults]                                                   │
│                                                                        │
│  ── Critical Error Rules ──────────────────────────────────────────   │
│  These mark a movie as ERROR (shown in red).                           │
│                                                                        │
│  [x] Missing video file                                                │
│  [x] Corrupt NFO file (XML parse error)                                │
│  [x] Missing NFO file                                                  │
│  [x] Corrupt XML file (XML parse error)                                │
│  [x] Missing XML file                                                  │
│  [x] Corrupt poster image                                              │
│  [x] Corrupt fanart image                                              │
│  [x] Corrupt folder image                                              │
│  [x] Missing IMDB ID                                                   │
│  [x] IMDB ID conflict between NFO and XML                              │
│  [x] Missing TMDb ID                                                   │
│  [x] TMDb ID conflict between NFO and XML                              │
│  [x] Rating conflict between NFO and XML                               │
│  [x] No audio tracks detected                                          │
│  [x] Votes conflict between NFO and XML                                │
│  [x] Missing genre information                                         │
│  [x] Missing movie year in NFO/XML                                     │
│  [x] Video quality below minimum:  [720p        ▼]                    │
│                                                                        │
│  ── Warning Rules ─────────────────────────────────────────────────   │
│  These mark a movie as WARNING (shown in yellow).                      │
│                                                                        │
│  [ ] Multiple video files in same folder        (default: OFF)         │
│  [x] Missing poster                                                    │
│  [x] Missing fanart                                                    │
│  [x] Missing folder image                                              │
│  [x] Poster has wrong proportions                                      │
│  [x] Fanart has wrong proportions                                      │
│  [x] Folder image has wrong proportions                                │
│  [x] Poster/folder quality below minimum:  [1080p       ▼]            │
│  [x] Fanart quality below minimum:  [1080p       ▼]                   │
│  [x] Poster and folder image are identical (same file size)            │
│  [x] Backdrop images below minimum:  [5  ⬆⬇]                         │
│  [x] Backdrop images suspiciously small (avg KB below):  [20  ⬆⬇]    │
│  [x] Missing rating                                                    │
│  [x] Rating present in one file only                                   │
│  [x] Suspicious rating value (below):  [1.0  ⬆⬇]                     │
│  [x] Genre issues detected (non-standard genres)                       │
│  [x] Missing votes count                                               │
│  [x] Votes present in one file only                                    │
│  [x] Target language not found (Lang OK? column)                       │
│  [x] Language field missing in XML                                     │
│  [x] NFO or XML file too large (uses max KB from Improvements tab)     │
│  [x] Required audio language missing:  [ENG ▼]  English               │
│  [x] Required subtitle language missing:  [POR ▼]  Portuguese         │
│  [x] Missing movie title in NFO/XML                                    │
│  [x] Title mismatch between NFO and XML                                │
│  [ ] Folder name doesn't match movie title      (default: OFF)         │
└───────────────────────────────────────────────────────────────────────┘
```

**Inline control specifications:**

- Quality dropdowns: `ttk.Combobox`, `state="readonly"`, width=12.
  Values from `VIDEO_QUALITY_LEVELS` / `POSTER_QUALITY_LEVELS` / `FANART_QUALITY_LEVELS`.

- `backdrop_min_count`: `tk.Spinbox` from=1, to=50, width=4.

- `backdrop_min_avg_kb`: `tk.Spinbox` from=1, to=500, width=5.

- `suspicious_rating_threshold`: `tk.Spinbox` from=0.0, to=10.0,
  increment=0.1, width=5, format="%.1f". Use `tk.DoubleVar`.

- Language dropdowns: `ttk.Combobox`, `state="readonly"`, width=6.
  Values: list of `"CODE"` strings (display as `"CODE — Name"` in the widget,
  store only the code). Show the language name as a static label to the right.

**Enable/disable behavior:**
`BooleanVar.trace_add("write", callback)` per inline control.
When checkbox is unchecked: inline control `state="disabled"`.
When checked: `state="normal"` or `state="readonly"` for comboboxes.

**"Reset to defaults" button:**
Restores all `_hr_vars`, `_hr_int_vars`, `_hr_flt_vars`, `_hr_str_vars` to
their default values and updates all inline control states. Does not save.

### 6.4 — Rescan snapshot

Add `health_rules` to `_take_rescan_snapshot()` as a deep copy of the entire
dict (boolean keys AND parameter values). Any change to any key must be
reflected in `_rescan_changed()["any"]`.

---

## PART 7 — HEALTH UPDATE ON SETTINGS SAVE

### 7.1 — Two separate change tracks

Settings changes fall into two independent tracks:

| Track | Examples | Action |
|-------|----------|--------|
| **Health-rules-only** | Rule checkboxes, backdrop minimum, quality threshold | `_offer_health_update()` — in-memory recalculation, no re-scan |
| **Scan-relevant** | Language code, image quality tiers, genre list, tag pairs | Existing `_offer_rescan()` — offers Update Scan |

Both can fire in the same save: health update dialog first, rescan dialog second.

### 7.2 — New snapshot key: health_rules

Add to `_take_rescan_snapshot()` in `settings_dialog.py`:

```python
"health_rules": copy.deepcopy(s.get("health_rules", {})),
```

Add `import copy` at the top of `settings_dialog.py` if not already present.

Add a new comparison key to `_rescan_changed()`, before `changed["any"]`:

```python
hr_changed = False
if hasattr(self, "_hr_vars"):
    snap_hr = snap.get("health_rules", {})
    curr_hr = {}
    for k, v in self._hr_vars.items():     curr_hr[k] = v.get()
    for k, v in self._hr_int_vars.items(): curr_hr[k] = v.get()
    for k, v in self._hr_flt_vars.items(): curr_hr[k] = round(v.get(), 2)
    for k, v in self._hr_str_vars.items(): curr_hr[k] = v.get()
    hr_changed = (curr_hr != snap_hr)
changed["health_rules"] = hr_changed
```

Update `changed["any"]`:

```python
changed["any"] = any([img, lang, genres, tags, hr_changed])
```

`health_rules` must NOT be merged into `image_sizes`, `language`, `genres`,
or `tags` tracks. It drives only `_offer_health_update()`, never `_offer_rescan()`.

### 7.3 — New dialog: _offer_health_update()

Add `_offer_health_update(parent_app)` to `SettingsDialog`, modelled exactly
on `_offer_rescan()` (same non-blocking pattern, centering logic, grab_set).

Dialog text:
```
Health Rules have changed.

Would you like to update the health status of all
loaded movies using the new rules?

This does not require a re-scan. It uses the
existing scan data already in memory.
```

Buttons:

| Button | Colour | Action |
|--------|--------|--------|
| Update Health Status | `#a6e3a1` (green) | `grab_release()`, `destroy()`, `parent_app._apply_health_rules_inplace()` |
| Skip | `#45475a` (grey) | `grab_release()`, `destroy()` |

Guard: if `not parent_app or not getattr(parent_app, "_results", None)`, return immediately.

Must never use `wait_window()`. Follow `_offer_rescan()` exactly.

### 7.4 — New method: App._apply_health_rules_inplace()

Add to `App` in `mediaclinic_v0_18_0.py`:

```python
def _apply_health_rules_inplace(self):
    if not self._results:
        return
    rules = SETTINGS.get("health_rules", {})
    for r in self._results:
        try:
            status, reasons = compute_movie_health(r, rules, SETTINGS)
            r["health_status"]  = status
            r["health_reasons"] = reasons
        except Exception:
            pass
    self._phase_update(self._results, "")
    self._update_stats()
```

Runs on the main thread. No I/O, no re-scan. Under 5ms for 500 movies.
Directly callable from other code paths.

### 7.5 — Replace the existing _offer_rescan scheduling in _save_close()

Replace the existing line (line 1713):

```python
if changed["any"] and parent_app:
    parent_app.after(0, lambda: self._offer_rescan(parent_app))
```

With:

```python
# Health-rules-only: offer in-memory recalculation, no re-scan
if changed.get("health_rules") and parent_app and getattr(parent_app, "_results", None):
    parent_app.after(0, lambda: self._offer_health_update(parent_app))

# Scan-relevant: offer re-scan only for scan-relevant keys
_scan_relevant = any([
    changed.get("image_sizes"),
    changed.get("language"),
    changed.get("genres"),
    changed.get("tags"),
])
if _scan_relevant and parent_app:
    parent_app.after(0, lambda: self._offer_rescan(parent_app))
```

Never use `changed["any"]` to decide whether to show the rescan offer.

### 7.6 — _on_settings_changed() — no changes needed

`_on_settings_changed()` already handles deferred refresh via `_post_save_refresh()`.
Do NOT add health recalculation there — it would bypass user confirmation.

---

## PART 8 — HEALTH STATUS REPORT

### 8.1 — Overview

The Health Status Report generates a human-readable summary of all health
warnings and errors for a set of movies, organised by movie name. It is
accessible from three entry points:

1. Right-click menu → `"🏥  Health Status Report"` (single or multi-selection)
2. Tools menu → `"🏥  Health Status Report — All Movies"`

Both entry points call the same underlying function with different input lists.

### 8.2 — Report format function

Add a new function to `mediaclinic_v0_18_0.py`:

```python
def format_health_report(results: list[dict]) -> str:
```

This function takes a list of movie row dicts and returns a formatted text
report string. It reads `health_status` and `health_reasons` from each row —
it does not recompute health. Only movies where `health_status != "ok"` are
included. Movies with no issues are counted but not listed.

Report structure:
```
Health Status Report — {n} movie(s) checked
Generated: {datetime}
============================================================

⚠  WARNING movies: {w}    ✕  ERROR movies: {e}    ✓  OK movies: {ok}

============================================================

📁  {Movie Name}  [{YEAR}]               [ERROR]
────────────────────────────────────────────────
  ✕  Corrupt NFO file (XML error)
  ✕  Missing IMDB ID

📁  {Movie Name}  [{YEAR}]               [WARNING]
────────────────────────────────────────────────
  ⚠  Missing poster
  ⚠  Too few backdrops (3 of 5 required)
  ⚠  Required audio language not found (ENG)

============================================================
Total issues: {total_issues} across {affected} movie(s)
{ok_count} movie(s) have no health issues.
```

Sort order in report: ERROR movies first, then WARNING movies, each group
sorted alphabetically by movie name.

Use `row.get("movie_name") or row.get("subfolder", "Unknown")` as the
display name. Use `row.get("movie_year", "-")` for the year.

### 8.3 — Dialog class: HealthReportDialog

Add a new class `HealthReportDialog(tk.Toplevel)` modelled closely on
`ImprovementsDialog` (line 3949). Reuse the same visual style, scrollable
`tk.Text` widget with colour tags, and button layout.

Colour tags for the report text widget:
- `"h"`: headers (blue `#89b4fa`, bold)
- `"mv_err"`: movie name when ERROR (red `#f38ba8`, bold)
- `"mv_warn"`: movie name when WARNING (yellow `#f9e2af`, bold)
- `"err_line"`: error reason lines (red `#f38ba8`)
- `"warn_line"`: warning reason lines (yellow `#f9e2af`)
- `"ok"`: OK summary line (green `#a6e3a1`)
- `"sep"`: separators (dim `#45475a`)

Buttons:
- `"  💾 Save to .txt  "` — calls `filedialog.asksaveasfilename`, default
  filename `"health_report_{date}.txt"`. Same pattern as `ImprovementsDialog._save()`.
- `"  OK  "` — calls `self.destroy()`.

No "Copy to Clipboard" button is required (simplify vs ImprovementsDialog).

Window title: `"🏥  Health Status Report — {n} movie(s)"`
Window size: `780x580`, resizable.

### 8.4 — Progress protection

The report is generated from already-scanned in-memory data (`health_status`
and `health_reasons` are already computed). For a typical 500-movie library,
`format_health_report()` completes in under 100ms — no progress dialog is
needed for the report generation itself.

However, the entry point must check whether a scan has been run:
```python
if not self._results:
    messagebox.showinfo("No Data",
        "No scan results available. Please run a scan first.",
        parent=self)
    return
```

If the user invokes the report while a scan is in progress (`self._scanning`
is True), show:
```python
if self._scanning:
    messagebox.showinfo("Scan in Progress",
        "Please wait for the scan to complete before generating a report.",
        parent=self)
    return
```

For the "All Movies" entry point, if the library is very large and report
generation takes longer than expected (future-proofing), the function is
structured to allow wrapping in `run_async` later without refactoring. Write
`format_health_report()` as a pure function (no Tk calls) for this reason.

### 8.5 — Right-click menu integration

In `_build_rclick_menu()` (line 8675), add after the "Run Improvements Check"
entry (line 8753):

```python
label_hr = (f"🏥  Health Status Report ({len(sel_data)} movies)"
            if multi else "🏥  Health Status Report")
m.add_command(label=label_hr,
              command=lambda dd=sel_data: self._show_health_report(dd))
```

### 8.6 — Tools menu integration

In the Tools menu setup (line 7430), add after "Run Improvements Check — All Movies":

```python
tools_menu.add_command(
    label="🏥  Health Status Report — All Movies",
    command=self._show_health_report_all)
```

### 8.7 — Handler methods

```python
def _show_health_report(self, data_list: list[dict]):
    """Show health report for the given list of movie row dicts."""
    if self._scanning:
        messagebox.showinfo("Scan in Progress",
            "Please wait for the scan to complete.", parent=self); return
    if not data_list:
        messagebox.showinfo("No Selection",
            "No movies selected.", parent=self); return
    report = format_health_report(data_list)
    HealthReportDialog(self, report, len(data_list))

def _show_health_report_all(self):
    """Show health report for all loaded movies."""
    if self._scanning:
        messagebox.showinfo("Scan in Progress",
            "Please wait for the scan to complete.", parent=self); return
    if not self._results:
        messagebox.showinfo("No Data",
            "No scan results available. Please run a scan first.",
            parent=self); return
    report = format_health_report(self._results)
    HealthReportDialog(self, report, len(self._results))
```

---

## PART 9 — UI CONSISTENCY

### 9.1 — Health icons (do not change STATUS_* constants)

```python
STATUS_OK      = "⬤"   # green  — individual column: present/valid
STATUS_WARN    = "◐"   # yellow — individual column: proportion warning
STATUS_MISSING = "○"   # white  — individual column: file missing
STATUS_ERROR   = "✕"   # red    — individual column: corrupt/conflict
```

Row-level health uses `"ok"`, `"warning"`, `"error"` for tags and status bar only.

### 9.2 — Treeview tag names

```python
self.tree.tag_configure("ok",          background=COLOR_ROW_OK)
self.tree.tag_configure("ok_odd",      background=COLOR_ROW_OK_ODD)
self.tree.tag_configure("warning",     background=COLOR_ROW_WARNING)
self.tree.tag_configure("warning_odd", background=COLOR_ROW_WARNING_ODD)
self.tree.tag_configure("error",       background=COLOR_ROW_ERROR)
self.tree.tag_configure("error_odd",   background=COLOR_ROW_ERROR_ODD)
```

### 9.3 — Status bar

```python
errors   = sum(1 for r in results if r["health_status"] == "error")
warnings = sum(1 for r in results if r["health_status"] == "warning")
ok       = len(results) - errors - warnings
```

### 9.4 — Sort options

```python
"Health (Errors 1st)":  (lambda r: {"error":0,"warning":1,"ok":2}.get(r["health_status"],1), False),
"Health (Warning 1st)": (lambda r: {"warning":0,"error":1,"ok":2}.get(r["health_status"],1), False),
"Health (OK 1st)":      (lambda r: {"ok":0,"warning":1,"error":2}.get(r["health_status"],1), False),
```

### 9.5 — health_reasons in detail panel

When `health_status != "ok"`, show in the movie detail/tooltip panel:
```
Health: WARNING
Reasons:
  • Missing poster
  • Too few backdrops (3 of 5 required)
```
When `health_status == "ok"`, show `"Health: OK"` only.

---

## PART 10 — SAFETY AND REGRESSION CHECKLIST

Before outputting any code, verify all of the following:

### Migration
- [ ] All `row_health` → `health_status` (all ~20 locations)
- [ ] All `"red"`/`"yellow"`/`"green"` → `"error"`/`"warning"`/`"ok"`
- [ ] All `tag_configure` tag name strings updated
- [ ] `_compute_health()` deleted, not aliased
- [ ] `min_backdrops` removed from Improvements tab UI and `_save_close()`
- [ ] `run_improvements()` reads `health_rules["backdrop_min_count"]`
- [ ] Phase 3 `worker()` populates `movie_title_raw` and `movie_year_raw`
- [ ] Phase 4 `worker()` populates `ffprobe_ran` (bool)
- [ ] `scan_one_subfolder()` return dict includes `movie_title_raw`, `movie_year_raw`, `ffprobe_ran`
- [ ] `_results_from_json()` defaults include `movie_title_raw: []`, `movie_year_raw: None`, `ffprobe_ran: False`
- [ ] Stub in Phase 1 `worker()` includes `movie_title_raw: []`, `movie_year_raw: None`, `ffprobe_ran: False`

### Language normalization
- [ ] `ISO_639_1_TO_2` and `normalize_lang_code()` defined in `settings_model.py`
- [ ] `required_subtitle_language` uses `normalize_lang_code()` for all comparisons
- [ ] `required_audio_language` uppercases both sides before comparison

### New function
- [ ] `compute_movie_health()` is the only health computation path
- [ ] No rule does any I/O
- [ ] `nfo_xml_too_large` reads from `settings` param; skips when `settings is None`
- [ ] `no_audio_tracks` uses `ffprobe_ran` field; never fires when FFprobe was not run
- [ ] `required_audio_language` skips when `audio_tracks` is empty
- [ ] `video_quality_minimum` skips when quality is `"—"`
- [ ] Image quality rules skip when image is missing or quality is `"—"`
- [ ] `suspicious_rating` skips when `rating_value == -1.0`
- [ ] `backdrop_too_small` skips when `backdrop_count == 0`
- [ ] `poster_folder_identical` skips when either image is missing or size is 0
- [ ] `title_mismatch` fires only when 2+ distinct titles found
- [ ] `folder_name_mismatch` default is OFF
- [ ] `genre_missing` fires on `STATUS_ERROR` only (empty genre list)
- [ ] `genre_warning` fires on `STATUS_WARN` only (non-standard genres)
- [ ] `missing_movie_year` fires on `movie_year_raw is None` (ERROR level)
- [ ] `votes_conflict` fires on `votes_status == STATUS_ERROR` (ERROR level)

### Settings
- [ ] `health_rules` deep-merged in settings loader
- [ ] `health_rules` in rescan snapshot (full deep copy)
- [ ] `settings_schema.json` updated
- [ ] `VIDEO_QUALITY_LEVELS`, `AUDIO_LANGUAGES`, `SUBTITLE_LANGUAGES`,
      `POSTER_QUALITY_LEVELS`, `FANART_QUALITY_LEVELS`, `ISO_639_1_TO_2`,
      `normalize_lang_code` defined in `settings_model.py`

### UI / Settings dialog
- [ ] Health Rules tab at index 10; Backup at index 11
- [ ] Inline controls greyed when checkbox unchecked
- [ ] `trace_add` bindings do not create infinite loops
- [ ] `_save_close()` writes all four variable dicts
- [ ] "Reset to defaults" restores all defaults without saving
- [ ] Tab is scrollable
- [ ] `CLAUDE_RULES.md` tab registry updated to 12 tabs
- [ ] `settings_test_harness.py` T04 updated to expect 12 tabs
- [ ] `_hr_vars`, `_hr_int_vars`, `_hr_flt_vars`, `_hr_str_vars` in protected list in `CLAUDE_RULES.md`

### Health update on settings save
- [ ] `health_rules` added to `_take_rescan_snapshot()` as `copy.deepcopy`
- [ ] `import copy` present in `settings_dialog.py`
- [ ] `changed["health_rules"]` computed in `_rescan_changed()` from all four `_hr_*` dicts
- [ ] `changed["any"]` updated to include `hr_changed`
- [ ] `_offer_health_update()` added — non-blocking, no `wait_window()`
- [ ] `_apply_health_rules_inplace()` added to `App` — no I/O, no re-scan
- [ ] Old `if changed["any"]` guard replaced by conditional block in `_save_close()`
- [ ] `_offer_rescan()` fires only when `image_sizes`, `language`, `genres`, or `tags` changed
- [ ] `_offer_health_update()` fires only when `health_rules` changed AND results loaded
- [ ] Both dialogs can fire in same save: health update first, rescan second
- [ ] `_apply_health_rules_inplace()` callable independently
- [ ] `health_reasons` persisted in `_results_to_json` / `_results_from_json`
- [ ] `health_status` default in `_results_from_json` is `"warning"` (safe fallback)

### Health Status Report
- [ ] `format_health_report()` is a pure function (no Tk calls)
- [ ] `HealthReportDialog` matches visual style of `ImprovementsDialog`
- [ ] Right-click menu entry added after "Run Improvements Check"
- [ ] Tools menu entry added after "Run Improvements Check — All Movies"
- [ ] Both entry points check for `_scanning` and empty `_results`
- [ ] "Save to .txt" uses `filedialog.asksaveasfilename`
- [ ] "OK" button closes dialog
- [ ] No blocking calls in `_show_health_report()` or `_show_health_report_all()`

### Filter bar
- [ ] `_filter_var`, `_filter_entry`, `_filter_after_id` in `CLAUDE_RULES.md` protected list
- [ ] `_matches_filter()` placed near `compute_movie_health()` at module level; name verified unique
- [ ] `_matches_filter()` is a pure function (no Tk calls, no I/O)
- [ ] `self._results` never modified by filter
- [ ] Status bar reflects total `self._results` count, not filtered count
- [ ] Export CSV uses `self._results` (unfiltered)
- [ ] Health Status Report Tools menu uses `self._results` (unfiltered)
- [ ] Filter cleared at start of `_start_scan()`
- [ ] Debounce via `after(150)` prevents blocking on keystroke
- [ ] `Ctrl+F` focuses filter entry
- [ ] `Escape` clears filter entry
- [ ] `_filter_after_id` cancelled before scheduling new refresh

### Architecture
- [ ] Save chain unchanged
- [ ] No new blocking operations
- [ ] No threading model changes
- [ ] No circular imports

---

## PART 11 — FILTER BAR

### 11.1 — Overview

Add a live filter bar above the table. The filter narrows visible rows by
typing. It never modifies `self._results` — it is a view-only control applied
inside `_refresh_table()` after sorting.

### 11.2 — Widget placement

Insert a new filter row between the sort row and the progress bar, inside `_mt`:

```python
fr = tk.Frame(_mt, bg="#1e1e2e")
fr.pack(fill="x", padx=20, pady=(0, 3))
tk.Label(fr, text="Filter:", font=("Helvetica", 10),
         bg="#1e1e2e", fg="#a6adc8").pack(side="left")
self._filter_var = tk.StringVar()
self._filter_entry = tk.Entry(
    fr, textvariable=self._filter_var,
    font=("Helvetica", 10), bg="#313244", fg="#cdd6f4",
    insertbackground="#cdd6f4", relief="flat", width=28)
self._filter_entry.pack(side="left", padx=(6, 0), ipady=3)
tk.Button(fr, text="x", font=("Helvetica", 10, "bold"),
          bg="#313244", fg="#6c7086", relief="flat", cursor="hand2",
          command=self._clear_filter).pack(side="left", padx=(4, 0))
self._filter_label = tk.Label(fr, text="", font=("Helvetica", 9),
    bg="#1e1e2e", fg="#6c7086")
self._filter_label.pack(side="left", padx=(10, 0))
self._filter_var.trace_add("write", self._on_filter_changed)
self._filter_after_id = None
```

Add `_filter_var`, `_filter_entry`, and `_filter_after_id` to the protected
widget variable list in `CLAUDE_RULES.md`.

### 11.3 — Filter fields

A row is shown if ANY of the following fields match (OR logic):

| Field | Row key | Match type |
|-------|---------|------------|
| Movie name | `movie_name` (fallback `subfolder`) | Case-insensitive substring |
| Year | `movie_year` | Exact prefix ("199" matches "1995") |
| Genre | `genre_display` | Case-insensitive substring |
| Health status | `health_status` | Exact word: "ok", "warning", "error" |
| Language | `language` | Case-insensitive substring |
| Video quality | `video_quality` | Case-insensitive substring |

An empty filter string shows all rows.

### 11.4 — Filter helper function

Add as a module-level pure function immediately after `compute_movie_health()`
(which will be near the end of the file, replacing `_compute_health()`). Verify
no existing function named `_matches_filter` is present before adding.
No Tk calls, no I/O:

```python
def _matches_filter(row: dict, term: str) -> bool:
    if not term or not term.strip():
        return True
    t = term.strip().lower()
    name    = (row.get("movie_name") or row.get("subfolder", "")).lower()
    year    = str(row.get("movie_year", "-")).lower()
    genre   = row.get("genre_display", "").lower()
    health  = row.get("health_status", "").lower()
    lang    = row.get("language", "").lower()
    quality = row.get("video_quality", "").lower()
    return (t in name or year.startswith(t) or t in genre
            or t == health or t in lang or t in quality)
```

### 11.5 — _refresh_table() integration

After sorting and before inserting rows, apply the filter:

```python
term     = self._filter_var.get() if hasattr(self, "_filter_var") else ""
filtered = [r for r in sorted_results if _matches_filter(r, term)]

for i, r in enumerate(filtered):         # MODIFIED_BY_CLAUDE_v18.2
    tag = r["health_status"] + ("_odd" if i % 2 else "")
    iid = self.tree.insert("", "end", values=self._rv(r), tags=(tag,))
    self._item_map[iid] = r

if hasattr(self, "_filter_label"):        # MODIFIED_BY_CLAUDE_v18.2
    if term.strip():
        self._filter_label.configure(
            text=f"{len(filtered)} of {len(self._results)} shown")
    else:
        self._filter_label.configure(text="")
```

`self._results` is never modified. All scan operations and bulk actions
continue to use `self._results` unchanged.

### 11.6 — Debounced keystroke handler

```python
def _on_filter_changed(self, *_):
    if self._filter_after_id is not None:
        try: self.after_cancel(self._filter_after_id)
        except Exception: pass
    self._filter_after_id = self.after(150, self._refresh_table)

def _clear_filter(self):
    self._filter_var.set("")
    self._filter_entry.focus_set()
```

150ms debounce prevents rebuilding on every keystroke while feeling instant.

### 11.7 — Keyboard shortcuts

```python
self.bind("<Control-f>", lambda e: self._filter_entry.focus_set())
self.bind("<Control-F>", lambda e: self._filter_entry.focus_set())
self._filter_entry.bind("<Escape>", lambda e: self._clear_filter())
```

### 11.8 — Clear filter on scan start

At the top of `_start_scan()`, after clearing `self._results`:

```python
if hasattr(self, "_filter_var"):
    self._filter_var.set("")
```

### 11.9 — Interactions with other features

| Feature | Behaviour |
|---------|----------|
| Sort combo | Sort first, then filter, inside `_refresh_table()` |
| Status bar | Always reflects `len(self._results)` (total), never filtered count |
| Health Status Report — right-click | Operates on selected visible rows |
| Health Status Report — Tools menu | Always uses `self._results` (unfiltered) |
| Export CSV | Always exports `self._results` (unfiltered) |
| Jump-to-letter keyboard nav | Navigates within currently visible rows only |
| `_phase_update()` during scan | Filter is cleared at scan start, so no effect |

---

## PART 12 — OUTPUT FORMAT

Follow MASTER_CLAUDE_REVISION_PROMPT Section 4 strictly:

1. Propose an implementation plan listing files in order.
2. Wait for approval before writing any code.
3. Output changes file by file, modified sections only, tagged with
   `# ADDED_BY_CLAUDE_v18.2` or `# MODIFIED_BY_CLAUDE_v18.2`.
4. After all files: provide verification report against Part 10 checklist.
