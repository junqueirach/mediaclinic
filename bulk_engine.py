# =============================================================================
# bulk_engine.py — the loop every bulk tool runs, without Tk
# MediaClinic v0.20.1 RV13                                       ### NEW v0.20.1 RV13 ###
#
# One loop for the bulk tools (BF2 <uniqueid> for Kodi, BF3 Fix one issue,
# TF1 Replace low-resolution posters, AC3 actor photos, EA5 extrafanart and the
# older _BatchJob users): every item in turn, Cancel, Pause / Resume, an
# optional "save as it goes" checkpoint, skip reasons with counts for previews
# and end messages, and the error list.
#
# Series-ready (plan rule SR3): an *item* is whatever the caller passes (a
# movie row today; a show, season or episode later). The engine never reads
# its fields: the caller gives name_of(item) and the step.
#
# Thread use: run_steps() runs on the worker thread. The control's flags are
# plain reads of callables, so a Tk dialog can own them (it sets booleans on
# the Tk thread; the worker only reads them).
# =============================================================================
from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional


class Skip(Exception):
    """Raised by a step: this item is left as it is, for *reason* (a short code or text).

    Counted per reason (BulkResult.skipped) and listed with the item's name; it is not an error."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


class BulkControl:
    """Cancel and Pause for a run. Either its own flags, or read through callables (e.g. a progress dialog's)."""

    def __init__(self, cancelled: Optional[Callable[[], bool]] = None,
                 paused: Optional[Callable[[], bool]] = None) -> None:
        self._cancel_flag = False
        self._pause_flag = False
        self._cancelled_fn = cancelled
        self._paused_fn = paused

    def cancel(self) -> None:
        self._cancel_flag = True

    def pause(self, on: bool = True) -> None:
        self._pause_flag = bool(on)

    def cancelled(self) -> bool:
        return self._cancel_flag or bool(self._cancelled_fn and self._cancelled_fn())

    def paused(self) -> bool:
        return self._pause_flag or bool(self._paused_fn and self._paused_fn())

    def wait_while_paused(self, poll: float = 0.1, sleep: Callable[[float], None] = time.sleep) -> None:
        """Block the worker while paused; returns at once when resumed or cancelled."""
        while self.paused() and not self.cancelled():
            sleep(poll)


@dataclass
class BulkResult:
    """What a run did: counts, skip reasons, errors, and whether it was cancelled."""
    total: int = 0
    processed: int = 0
    done: int = 0
    skipped: Counter = field(default_factory=Counter)          # reason → count
    skipped_items: list = field(default_factory=list)           # (name, reason, detail)
    errors: list = field(default_factory=list)                  # "name: error"
    cancelled: bool = False
    checkpoints: int = 0


def run_steps(items: Iterable[Any], step: Callable[[Any], bool], *,
              name_of: Callable[[Any], str] = str,
              control: Optional[BulkControl] = None,
              on_progress: Optional[Callable[[int, int], None]] = None,
              checkpoint: Optional[Callable[[BulkResult], None]] = None,
              checkpoint_every: int = 0,
              result: Optional[BulkResult] = None) -> BulkResult:
    """Run *step* on every item in order and return the BulkResult.

    step(item) returns True when it changed something (counted in ``done``), False otherwise; it raises Skip to leave
    the item for a reason, or any other exception to report an error ("<name>: <error>"). Cancel stops before the next
    item; Pause waits between items. on_progress(processed, total) after every item. checkpoint(result) every
    *checkpoint_every* items (0 = never) and once at the end when anything was processed. A *result* passed in is
    filled in place (the caller can read it while the run goes on)."""
    items = list(items)
    res = result if result is not None else BulkResult()
    res.total = len(items)
    ctl = control or BulkControl()
    for item in items:
        ctl.wait_while_paused()
        if ctl.cancelled():
            res.cancelled = True
            break
        try:
            if step(item):
                res.done += 1
        except Skip as sk:
            res.skipped[sk.reason] += 1
            res.skipped_items.append((name_of(item), sk.reason, sk.detail))
        except Exception as ex:                                  # a step's failure is reported, the run goes on
            res.errors.append(f"{name_of(item)}: {ex}")
        res.processed += 1
        if on_progress:
            on_progress(res.processed, res.total)
        if checkpoint and checkpoint_every and res.processed % checkpoint_every == 0:
            checkpoint(res)
            res.checkpoints += 1
    if checkpoint and res.processed and (not checkpoint_every or res.processed % checkpoint_every):
        checkpoint(res)
        res.checkpoints += 1
    return res


def plan_counts(items: Iterable[Any], classify: Callable[[Any], Optional[str]]) -> tuple[list, Counter]:
    """For a preview: (items to do, Counter of skip reasons). classify(item) returns None to do it, else a reason."""
    todo: list = []
    skipped: Counter = Counter()
    for it in items:
        why = classify(it)
        if why is None:
            todo.append(it)
        else:
            skipped[why] += 1
    return todo, skipped
