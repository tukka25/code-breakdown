"""Read source files from the working tree or from a git ref."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SKIP_DIRS = {".git", ".breakdown", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", "target"}


class SourceError(Exception):
    pass


def run_git(cwd: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    """Run git with UTF-8 output whatever the system code page, so code is never garbled."""
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def git_root(start: Path) -> Optional[Path]:
    try:
        out = run_git(start, "rev-parse", "--show-toplevel")
    except OSError:
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return Path(out.stdout.strip())


def split_lines(text: str) -> List[str]:
    """Split the way editors number lines: on \\n, \\r\\n or \\r, without a phantom last line."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


class Source:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self._cache: Dict[Tuple[str, Optional[str]], List[str]] = {}
        self._merge_bases: Dict[Tuple[str, str], str] = {}

    def git(self, *args: str) -> str:
        try:
            out = run_git(self.root, *args)
        except OSError as exc:
            raise SourceError(f"git is not available: {exc}") from exc
        if out.returncode != 0:
            raise SourceError(out.stderr.strip() or f"git {' '.join(args)} failed")
        return out.stdout

    def read(self, path: str, ref: Optional[str] = None) -> List[str]:
        key = (path, ref)
        if key in self._cache:
            return self._cache[key]
        if ref:
            try:
                text = self.git("show", f"{ref}:{path}")
            except SourceError as exc:
                raise SourceError(f"{path} is not in {ref}: {exc}") from exc
        else:
            full = (self.root / path).resolve()
            if full != self.root and not str(full).startswith(str(self.root) + os.sep):
                raise SourceError(f"{path} is outside the repository at {self.root}")
            if not full.is_file():
                raise SourceError(f"{path} does not exist under {self.root}")
            text = full.read_text(encoding="utf-8", errors="replace")
        lines = split_lines(text)
        self._cache[key] = lines
        return lines

    def exists(self, path: str, ref: str) -> bool:
        try:
            self.git("cat-file", "-e", f"{ref}:{path}")
            return True
        except SourceError:
            return False

    def merge_base(self, base: str, head: Optional[str]) -> str:
        key = (base, head or "HEAD")
        if key not in self._merge_bases:
            self._merge_bases[key] = self.git("merge-base", base, head or "HEAD").strip()
        return self._merge_bases[key]

    def verify_ref(self, ref: str) -> bool:
        try:
            self.git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
            return True
        except SourceError:
            return False

    def similar_paths(self, path: str, limit: int = 3) -> List[str]:
        """Files elsewhere in the repository with the same name, to suggest when a path is wrong."""
        name = Path(path).name
        found: List[str] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            if name in filenames:
                found.append(str((Path(dirpath) / name).relative_to(self.root)).replace(os.sep, "/"))
                if len(found) >= limit:
                    break
        return found
