"""Shared paths and example loaders for the tests."""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "breakdown" / "scripts"
EXAMPLES = ROOT / "examples"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def example(name):
    """Return (repo root, spec dict) for one of the example projects."""
    root = EXAMPLES / name
    spec = json.loads((root / "spec.json").read_text(encoding="utf-8"))
    return root, copy.deepcopy(spec)


def block(spec, block_id):
    return next(b for b in spec["blocks"] if b["id"] == block_id)
