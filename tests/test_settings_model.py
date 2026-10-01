"""Contract tests for the pure settings model (see docs/CLAUDE_RULES.md)."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import settings_model as m  # noqa: E402  (pure module: no tkinter, no I/O)


def test_defaults_match_schema_keys():
    schema = json.loads((ROOT / "settings_schema.json").read_text(encoding="utf-8"))
    assert set(m.DEFAULT_SETTINGS) == set(schema["properties"])


def test_defaults_validate_against_schema():
    import jsonschema
    schema = json.loads((ROOT / "settings_schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(m.DEFAULT_SETTINGS, schema)


def test_image_quality_tiers():
    assert m.classify_image_quality(3840, 2160, "poster") == "1440p"
    assert m.classify_image_quality(1920, 1080, "fanart") == "1080p"
    assert m.classify_image_quality(600, 900, "poster") == "540p"
