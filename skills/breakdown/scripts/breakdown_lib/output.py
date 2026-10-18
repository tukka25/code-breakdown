"""Where a breakdown is written, and keeping it out of commits."""

from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .model import Spec

FOLDER = ".breakdown"


def slug(text: str, limit: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(s) > limit:
        s = s[:limit].rsplit("-", 1)[0] or s[:limit]
    return s or "breakdown"


def folder_name(spec: Spec, today: Optional[str] = None) -> str:
    day = today or dt.date.today().isoformat()
    s = slug(spec.title)
    if s == spec.kind or s.startswith(spec.kind + "-"):
        return f"{day}-{s}"
    return f"{day}-{spec.kind}-{s}"


def output_dir(root: Path, spec: Spec, today: Optional[str] = None) -> Path:
    return Path(root) / FOLDER / folder_name(spec, today)


def ensure_git_exclude(root: Path) -> bool:
    """Add .breakdown/ to .git/info/exclude once. Returns True when it was added."""
    try:
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-path", "info/exclude"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    path = Path(out.stdout.strip())
    if not path.is_absolute():
        path = Path(root) / path
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    if any(line.strip() in (FOLDER, FOLDER + "/", "/" + FOLDER, "/" + FOLDER + "/") for line in existing):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        if existing and existing[-1].strip():
            fh.write("\n")
        fh.write("# code breakdowns\n" + FOLDER + "/\n")
    return True


def open_file(path: Path) -> bool:
    """Open a file with the system's default app. Returns False when that is not possible here."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True, capture_output=True)
        elif os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(path)], check=True, capture_output=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False
