"""Pure tests of poster_review.py (v0.20.1 TF5). No Tk, no network, no files."""
import poster_review as pr


def test_session_use_skip_back_and_counts():
    s = pr.ReviewSession(["a", "b", "c", "d"])
    assert s.current() == "a" and s.position() == (1, 4) and not s.can_back()
    s.use("used")
    assert s.current() == "b" and s.next_index() == 2
    s.skip()
    s.use("upscaled")
    assert s.current() == "d"
    assert s.back() and s.current() == "c" and s.changed_here() == "upscaled"
    s.skip()                                   # Skip after Back never hides the change made before
    assert s.outcome[2] == "upscaled"
    s.use("fixed")
    assert s.finished and s.current() is None and s.next_index() is None
    c = s.counts()
    assert (c["used"], c["upscaled"], c["fixed"], c["skipped"], c["not_seen"]) == (1, 1, 1, 1, 0)
    assert s.changed_items() == ["a", "c", "d"]


def test_session_stop_counts_not_seen_and_rejects_bad_outcome():
    s = pr.ReviewSession(range(5))
    s.use("used")
    s.stop()
    assert s.finished and not s.can_back() and s.counts()["not_seen"] == 4
    try:
        pr.ReviewSession([1]).use("skipped")
        assert False, "skipped is not a change"
    except ValueError:
        pass


def test_grid_moves_pages_and_preselect():
    assert pr.grid_move(0, "Right", 10) == 1 and pr.grid_move(0, "Left", 10) == 0
    assert pr.grid_move(1, "Down", 10) == 5 and pr.grid_move(9, "Down", 10) == 9
    assert pr.grid_move(3, "End", 10) == 9 and pr.grid_move(7, "Home", 10) == 0 and pr.grid_move(0, "Up", 0) == -1
    assert pr.page_of(8) == 1 and pr.page_count(17) == 3 and list(pr.page_slice(17, 2)) == [16]
    assert list(pr.page_slice(17, 9)) == [16]  # clamped to the last page
    es = [{"lang": "en", "width": 2000, "height": 3000}, {"lang": "pt", "width": 1000, "height": 1500},
          {"lang": "pt", "width": 400, "height": 600}]
    # Prefer pt: the first pt image that reaches 1080p and beats the current one
    assert pr.preselect(es, "poster", "pt", "prefer", (1000, 1500), (480, 720)) == 1
    # nothing reaches 4K: the first image is highlighted
    assert pr.preselect(es, "poster", "pt", "prefer", (2000, 3000), (2000, 3000)) == 0
    assert pr.preselect([], "poster", "pt", "prefer", (1000, 1500)) == -1
    assert pr.lang_tag({"lang": None}) == "" and pr.lang_tag({"lang": "PT"}) == "pt"


def test_end_counts_text_order():
    c = pr.ReviewSession(range(3))
    c.skip(); c.use("used"); c.stop()
    lines = pr.end_counts_text(c.counts(), {"used": "U {n}", "skipped": "S {n}", "not_seen": "N {n}"})
    assert lines == ["U 1", "S 1", "N 1"]
