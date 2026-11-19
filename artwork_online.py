# =============================================================================
# artwork_online.py — which online image to offer first, and which one replaces a weak one
# MediaClinic v0.20.1 TF3 / TF1                                  ### NEW v0.20.1 TF3 ###
#
# Pure (no Tk, no network, no files). The entries are the common dicts of the
# Fetch windows ({"source", "width", "height", "lang", "votes", "likes", …}).
#
# TF3 — the artwork language (the user's decisions of 2026-11-18):
#   language = the library language (default) or a chosen ISO 639-1 code;
#   mode     = "prefer" (default): the language → no text → English → the rest,
#              or "only": other languages are not offered;
#   textless_backgrounds (default True): fanart / backdrops without text first,
#              then the language.
#   Inside each group: the largest image first, then votes / likes.
# TF1 — best_replacement(): the first entry, in that order, that reaches the
#   minimum size and is larger than the current image.
#
# Series-ready (plan rule SR3): nothing here knows movies; *kind* is "poster"
# or "fanart" (any image kind that has a poster-like or background-like role).
# =============================================================================
from __future__ import annotations

from typing import Iterable, Optional

DEFAULTS = {"artwork_language": "library", "artwork_language_mode": "prefer", "artwork_textless_backgrounds": True}
NO_TEXT = ""                                                   # TMDB null, fanart.tv "00"
BACKGROUND_KINDS = frozenset({"fanart", "backdrop", "backdrops", "background", "landscape"})
# The choices of Settings → Images & Artwork → Artwork language: the common ones first, then the others TMDB has posters in.
LANGUAGES = (("en", "English"), ("pt", "Português"), ("es", "Español"), ("de", "Deutsch"), ("fr", "Français"),
             ("it", "Italiano"), ("nl", "Nederlands"), ("sv", "Svenska"), ("da", "Dansk"), ("no", "Norsk"), ("fi", "Suomi"),
             ("pl", "Polski"), ("cs", "Čeština"), ("sk", "Slovenčina"), ("hu", "Magyar"), ("ro", "Română"), ("bg", "Български"),
             ("hr", "Hrvatski"), ("sr", "Српски"), ("sl", "Slovenščina"), ("lt", "Lietuvių"), ("lv", "Latviešu"), ("et", "Eesti"),
             ("ru", "Русский"), ("uk", "Українська"), ("el", "Ελληνικά"), ("tr", "Türkçe"), ("he", "עברית"), ("ar", "العربية"),
             ("fa", "فارسی"), ("hi", "हिन्दी"), ("th", "ไทย"), ("vi", "Tiếng Việt"), ("id", "Bahasa Indonesia"),
             ("ms", "Bahasa Melayu"), ("zh", "中文"), ("ja", "日本語"), ("ko", "한국어"), ("ca", "Català"), ("eu", "Euskara"),
             ("gl", "Galego"))


def language_name(code) -> str:
    """'pt' → 'Português'; an unknown code is shown as it is."""
    c = norm_lang(code)
    return dict(LANGUAGES).get(c, c or "—")


def norm_lang(code) -> str:
    """'pt-BR' / 'PT' / 'pt' → 'pt'; None / '' / 'null' / '00' / 'xx' → '' (an image without text)."""
    c = str(code or "").strip().lower()
    if c in ("", "null", "none", "00", "xx"):
        return NO_TEXT
    return c.replace("_", "-").split("-")[0][:3]


def settings_language(settings: dict, library_iso: str) -> str:
    """The artwork language in use: the chosen code, or the library language (*library_iso*, e.g. 'PT') when the
    setting is 'library' (the default) or missing."""
    v = (settings or {}).get("artwork_language", DEFAULTS["artwork_language"])
    return norm_lang(library_iso if v in (None, "", "library") else v) or "en"


def settings_mode(settings: dict) -> str:
    v = (settings or {}).get("artwork_language_mode", DEFAULTS["artwork_language_mode"])
    return v if v in ("prefer", "only") else "prefer"


def settings_textless(settings: dict) -> bool:
    return bool((settings or {}).get("artwork_textless_backgrounds", DEFAULTS["artwork_textless_backgrounds"]))


def group_of(entry: dict, lang: str, kind: str, textless_first: bool) -> int:
    """0 = offered first … 3 = last. Posters: language, no text, English, rest. Backgrounds with textless_first:
    no text, language, English, rest."""
    el = norm_lang(entry.get("lang"))
    lang = norm_lang(lang)
    if kind in BACKGROUND_KINDS and textless_first:
        order = [NO_TEXT, lang, "en"]
    else:
        order = [lang, NO_TEXT, "en"]
    for i, g in enumerate(dict.fromkeys(order)):               # dict.fromkeys: "en" twice when lang is English
        if el == g:
            return i
    return 3


def order_entries(entries: Iterable[dict], kind: str, lang: str, textless_first: bool = True) -> list:
    """All entries, best first: by language group, then the largest, then votes / likes. Never drops an entry."""
    def key(e):
        return (group_of(e, lang, kind, textless_first), -(int(e.get("width") or 0) * int(e.get("height") or 0)),
                -int(e.get("votes") or e.get("likes") or 0))
    return sorted(entries, key=key)


def allowed(entry: dict, kind: str, lang: str, mode: str, textless_first: bool = True) -> bool:
    """False only in mode 'only' for an image in another language (no text counts as allowed for backgrounds when
    textless_first, and never for posters — a poster without text is not in 'your language')."""
    if mode != "only":
        return True
    el = norm_lang(entry.get("lang"))
    if el == norm_lang(lang):
        return True
    return kind in BACKGROUND_KINDS and textless_first and el == NO_TEXT


def offered(entries: Iterable[dict], kind: str, lang: str, mode: str, textless_first: bool = True,
            show_all: bool = False) -> list:
    """What a Fetch window lists: ordered; in mode 'only' the other languages hidden unless *show_all*."""
    out = order_entries(entries, kind, lang, textless_first)
    return out if (show_all or mode != "only") else [e for e in out if allowed(e, kind, lang, mode, textless_first)]


def best_replacement(entries: Iterable[dict], kind: str, lang: str, mode: str, min_wh: tuple,
                     current_wh: Optional[tuple] = None, textless_first: bool = True) -> tuple:
    """(entry, None) — the image that replaces a weak one — or (None, reason).

    The first entry in the offered order (mode applied) that reaches *min_wh* (±5 %, like the Health Rules) and is
    larger than *current_wh*. Reasons: 'no_images', 'other_language' (mode 'only': none in the language),
    'too_small' (none reaches the minimum or beats the current image)."""
    entries = list(entries)
    if not entries:
        return None, "no_images"
    pool = offered(entries, kind, lang, mode, textless_first)
    if not pool:
        return None, "other_language"
    mw, mh = (int(min_wh[0] or 0), int(min_wh[1] or 0)) if min_wh else (0, 0)
    cw, ch = (int(current_wh[0] or 0), int(current_wh[1] or 0)) if current_wh else (0, 0)
    for e in pool:
        w, h = int(e.get("width") or 0), int(e.get("height") or 0)
        if w >= mw * 0.95 and h >= mh * 0.95 and w * h > cw * ch:
            return e, None
    return None, "too_small"
