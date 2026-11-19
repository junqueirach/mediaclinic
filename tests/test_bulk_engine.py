# =============================================================================
# test_bulk_engine.py — pure tests of bulk_engine.py (no Tk, no files)
# MediaClinic v0.20.1 RV13                                       ### NEW v0.20.1 RV13 ###
# RUN:  python -m pytest -q test_bulk_engine.py   (GitHub layout: tests/test_bulk_engine.py)
# =============================================================================
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.dirname(_HERE)):
    if os.path.isfile(os.path.join(_cand, "bulk_engine.py")):
        sys.path.insert(0, _cand)
        break

import bulk_engine as be  # noqa: E402


def test_counts_done_skip_error_in_order():
    seen = []

    def step(it):
        seen.append(it)
        if it == 2:
            raise be.Skip("no_id", "no TMDB ID")
        if it == 3:
            raise ValueError("bad file")
        return it != 4                       # 4 = nothing to change

    res = be.run_steps([1, 2, 3, 4, 5], step, name_of=lambda i: f"M{i}")
    assert seen == [1, 2, 3, 4, 5]
    assert (res.total, res.processed, res.done) == (5, 5, 2)
    assert res.skipped == {"no_id": 1} and res.skipped_items == [("M2", "no_id", "no TMDB ID")]
    assert res.errors == ["M3: bad file"] and not res.cancelled


def test_cancel_stops_before_the_next_item():
    ctl = be.BulkControl()

    def step(it):
        if it == 2:
            ctl.cancel()
        return True

    res = be.run_steps(range(10), step, control=ctl)
    assert res.cancelled and res.processed == 3 and res.done == 3


def test_cancel_through_a_callable_like_a_dialog():
    flag = {"c": False}
    ctl = be.BulkControl(cancelled=lambda: flag["c"])
    res = be.run_steps(range(5), lambda it: flag.__setitem__("c", it == 0) or True, control=ctl)
    assert res.processed == 1 and res.cancelled


def test_pause_waits_between_items_and_resumes():
    state = {"paused": False, "sleeps": 0}
    ctl = be.BulkControl(paused=lambda: state["paused"])

    def fake_sleep(_s):
        state["sleeps"] += 1
        if state["sleeps"] == 3:
            state["paused"] = False          # the user clicks Resume

    order = []

    def step(it):
        order.append(it)
        if it == 1:
            state["paused"] = True           # the user clicks Pause during item 1
        return True

    # run_steps uses time.sleep; patch the control's wait to use the fake clock
    ctl.wait_while_paused = lambda poll=0.1, sleep=fake_sleep: be.BulkControl.wait_while_paused(ctl, poll, sleep)
    res = be.run_steps([0, 1, 2], step, control=ctl)
    assert order == [0, 1, 2] and res.done == 3 and state["sleeps"] == 3


def test_cancel_ends_a_pause():
    ctl = be.BulkControl()
    ctl.pause()
    ctl.cancel()
    ctl.wait_while_paused(sleep=lambda s: (_ for _ in ()).throw(AssertionError("slept")))
    res = be.run_steps([1, 2], lambda it: True, control=ctl)
    assert res.cancelled and res.processed == 0


def test_checkpoints_every_n_and_at_the_end():
    calls = []
    res = be.run_steps(range(7), lambda it: True, checkpoint=lambda r: calls.append(r.processed), checkpoint_every=3)
    assert calls == [3, 6, 7] and res.checkpoints == 3
    calls.clear()
    be.run_steps(range(6), lambda it: True, checkpoint=lambda r: calls.append(r.processed), checkpoint_every=3)
    assert calls == [3, 6]                   # no extra call when the end falls on a checkpoint
    calls.clear()
    be.run_steps([], lambda it: True, checkpoint=lambda r: calls.append(r.processed), checkpoint_every=3)
    assert calls == []


def test_progress_after_every_item():
    got = []
    be.run_steps("abc", lambda it: True, on_progress=lambda k, n: got.append((k, n)))
    assert got == [(1, 3), (2, 3), (3, 3)]


def test_plan_counts_for_a_preview():
    todo, skipped = be.plan_counts(range(10), lambda i: None if i % 3 else ("no_id" if i else "conflict"))
    assert todo == [1, 2, 4, 5, 7, 8] and skipped == {"no_id": 3, "conflict": 1}


def test_items_of_any_kind():                # SR3: the engine never reads an item's fields
    items = [{"kind": "movie", "n": 1}, {"kind": "episode", "n": 2}, ("tvshow", 3)]
    res = be.run_steps(items, lambda it: True, name_of=repr)
    assert res.done == 3
