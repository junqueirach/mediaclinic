"""Review Posters One by One (v0.20.1 TF5) — the pure part, no Tk and no file access.

The window (in the main file) shows one movie at a time: the current poster, the online posters in the artwork
language order (TF3), and "Fix proportions" / "Upscale (AI)". This module holds what does not need a window:

- ReviewSession: which movie is shown, what was done to each (used / upscaled / fixed / skipped), Back, Stop, the
  counts for the end message, the movie whose online posters load in the background.
- grid_move / page_of / page_slice: the keyboard moves in the grid of online posters.
- preselect: which online poster is highlighted when a movie opens (the one Replace Low-Resolution Posters would take).
- lang_tag: the language tag under each image ("pt", "en", "no text").

Series-ready (SR2): nothing here knows about movies; an item is any object the caller passes.
"""
from collections import Counter
from typing import Iterable, List, Optional, Sequence

import artwork_online as _ao

SETS = ("low", "ratio", "selection", "filter")      # step 1: below the tier + corrupt / wrong proportions / selected / filtered
CHANGES = ("used", "upscaled", "fixed")             # outcomes that changed a file
OUTCOMES = CHANGES + ("skipped",)
PAGE_SIZE = 8                                       # online posters per page (2 rows of 4)
COLS = 4


class ReviewSession:
    """The position in the list and the outcome of each item.

    use(outcome) records a change and moves on; skip() moves on without a change. Back moves to the previous item and
    keeps its change (the user's decision for v0.20.1: Undo is in Backup History). A Skip after Back never hides a
    change made before: the change stays counted."""

    def __init__(self, items: Iterable):
        self.items = list(items)
        self.pos = 0
        self.outcome = {}                           # index -> one of OUTCOMES
        self.stopped = False

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def finished(self) -> bool:
        return self.stopped or self.pos >= len(self.items)

    def current(self):
        return None if self.finished else self.items[self.pos]

    def position(self) -> tuple:
        """(1-based number shown, total) — "37 of 1,213"."""
        return (min(self.pos + 1, len(self.items)), len(self.items))

    def _advance(self):
        self.pos = min(self.pos + 1, len(self.items))

    def use(self, outcome: str = "used"):
        if outcome not in CHANGES:
            raise ValueError(outcome)
        if not self.finished:
            self.outcome[self.pos] = outcome
            self._advance()

    def skip(self):
        if not self.finished:
            if self.outcome.get(self.pos) not in CHANGES:
                self.outcome[self.pos] = "skipped"
            self._advance()

    def can_back(self) -> bool:
        return not self.stopped and self.pos > 0

    def back(self) -> bool:
        if not self.can_back():
            return False
        self.pos -= 1
        return True

    def stop(self):
        self.stopped = True

    def changed_here(self) -> Optional[str]:
        """The change made earlier to the item shown (after Back), or None."""
        o = self.outcome.get(self.pos)
        return o if o in CHANGES else None

    def next_index(self) -> Optional[int]:
        """The item whose online posters load in the background while this one is shown."""
        n = self.pos + 1
        return n if (not self.finished and n < len(self.items)) else None

    def counts(self) -> Counter:
        """used / upscaled / fixed / skipped, plus 'not_seen' (left when Stop was pressed)."""
        c = Counter(self.outcome.values())
        seen = len(self.outcome)
        if seen < len(self.items):
            c["not_seen"] = len(self.items) - seen
        return c

    def changed_items(self) -> list:
        return [self.items[i] for i in sorted(self.outcome) if self.outcome[i] in CHANGES]


def page_of(index: int, per: int = PAGE_SIZE) -> int:
    return max(0, int(index)) // per


def page_count(n: int, per: int = PAGE_SIZE) -> int:
    return max(1, (int(n) + per - 1) // per)


def page_slice(n: int, page: int, per: int = PAGE_SIZE) -> range:
    """The indexes shown on *page* (clamped to the last page)."""
    page = max(0, min(int(page), page_count(n, per) - 1))
    return range(page * per, min(n, (page + 1) * per))


def grid_move(index: int, key: str, n: int, cols: int = COLS) -> int:
    """The highlighted image after an arrow key / Home / End in a grid of *n* images (*cols* per row). Moves past the
    page end go on to the next page (the window shows the page of the result). -1 when there is no image."""
    if n <= 0:
        return -1
    i = max(0, min(int(index), n - 1))
    step = {"Left": -1, "Right": 1, "Up": -cols, "Down": cols}.get(key)
    if key == "Home":
        return 0
    if key == "End":
        return n - 1
    if step is None:
        return i
    return max(0, min(n - 1, i + step))


def preselect(entries: Sequence[dict], kind: str, lang: str, mode: str, min_wh: tuple,
              current_wh: Optional[tuple] = None, textless_first: bool = True) -> int:
    """Index in *entries* (the list as shown) of the image highlighted when a movie opens: the one Replace
    Low-Resolution Posters would take (best_replacement); when none qualifies, the first image; -1 for an empty list."""
    entries = list(entries)
    if not entries:
        return -1
    best, _why = _ao.best_replacement(entries, kind, lang, mode, min_wh, current_wh, textless_first)
    if best is None:
        return 0
    for i, e in enumerate(entries):
        if e is best:
            return i
    return 0


def lang_tag(entry: dict) -> str:
    """'pt', 'en' … or '' for an image without text (the window shows its own word for '')."""
    return _ao.norm_lang(entry.get("lang"))


def end_counts_text(counts: Counter, words: dict) -> List[str]:
    """The end message's count lines in a fixed order; *words* maps an outcome to its text with {n}
    (e.g. {"used": "Replaced from online: {n}"}). Outcomes without a word or with 0 are left out."""
    out = []
    for k in CHANGES + ("skipped", "not_seen"):
        if counts.get(k) and k in words:
            out.append(words[k].format(n=counts[k]))
    return out
