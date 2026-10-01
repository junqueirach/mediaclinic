"""Smoke tests: no GUI or heavy dependencies needed, they run on any CI machine."""
import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEY_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_-]{40,}")
SKIP_DIRS = {".git"}


def test_main_file_parses():
    src = (ROOT / "mediaclinic.py").read_text(encoding="utf-8")
    ast.parse(src)

def test_version_constant_present():
    src = (ROOT / "mediaclinic.py").read_text(encoding="utf-8")
    assert re.search(r'APP_VERSION = "v?\d+\.\d+\.\d+"', src), "APP_VERSION not found"


def test_all_python_files_parse():
    for path in ROOT.rglob("*.py"):
        if SKIP_DIRS & set(path.parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:  # archive/versions/ may hold an old broken draft
            assert "archive" in path.parts, f"{path}: {exc}"


def test_no_real_api_keys_committed():
    for path in ROOT.rglob("*"):
        if not path.is_file() or SKIP_DIRS & set(path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".ico", ".exe", ".zip"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not KEY_PATTERN.search(text), f"possible API key in {path}"
