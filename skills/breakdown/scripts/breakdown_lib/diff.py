"""Changes: which lines in each block were added or removed, and the author's own words about them."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple

from .lang import DECLARATION, family, indent
from .model import Block, Spec
from .source import Source, SourceError

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
CLAIM_CHARS = 20000
Hunk = Tuple[int, int, int, int]


def parse_hunks(text: str) -> List[Hunk]:
    """(old_start, old_count, new_start, new_count) for each hunk of a zero-context diff."""
    hunks = []
    for line in text.splitlines():
        m = HUNK.match(line)
        if m:
            a, b, c, d = m.groups()
            hunks.append((int(a), 1 if b is None else int(b), int(c), 1 if d is None else int(d)))
    return hunks


def changed_lines(hunks: List[Hunk]) -> Tuple[Set[int], Set[int], Set[int]]:
    """Removed base lines, added head lines, and head lines right after which something was deleted."""
    removed: Set[int] = set()
    added: Set[int] = set()
    cut: Set[int] = set()
    for a, b, c, d in hunks:
        removed.update(range(a, a + b))
        added.update(range(c, c + d))
        if d == 0:
            cut.add(c)
    return removed, added, cut


def _declares_other(line: str, token: str, fam: Optional[str]) -> bool:
    pattern = DECLARATION.get(fam or "")
    m = pattern.match(line) if pattern else None
    return bool(m) and m.group(1) != token


def _clip(old: List[str], def_indent: int, token: str, fam: Optional[str]) -> List[str]:
    """The removed lines that belong to this block: stop where another declaration at its level begins."""
    out: List[str] = []
    for line in old:
        if line.strip() and indent(line) <= def_indent and _declares_other(line, token, fam):
            break
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return out


def _deeper(old: List[str], def_indent: int) -> List[str]:
    """Leading removed lines indented deeper than the declaration: the end of a Python body."""
    out: List[str] = []
    for line in old:
        if line.strip() and indent(line) <= def_indent:
            break
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return out


def _insertions(hunks: List[Hunk], b: Block, base_lines: List[str]) -> Dict[int, List[str]]:
    """Removed base lines to show inside a head block, keyed by the head line index they come before."""
    fam = family(b.file)
    def_indent = indent(b.lines[b.def_line]) if b.lines else 0
    out: Dict[int, List[str]] = {}
    for a, count, c, d in hunks:
        if count == 0:
            continue
        old = base_lines[a - 1:a - 1 + count]
        if d > 0:
            # A replacement: the old lines go just before the new ones, which start at head line c.
            if not b.start <= c <= b.end:
                continue
            index, run = c - b.start, _clip(old, def_indent, b.token, fam)
        elif b.start <= c < b.end:
            # A pure deletion between head lines c and c + 1.
            index, run = c + 1 - b.start, _clip(old, def_indent, b.token, fam)
        elif c == b.end and fam == "python":
            # Python bodies have no closing line, so a deletion right after the last line may end the body.
            index, run = c + 1 - b.start, _deeper(old, def_indent)
        else:
            continue
        if run:
            out.setdefault(index, []).extend(run)
    return out


def _renames(source: Source, base: str, head: Optional[str]) -> Dict[str, str]:
    """New path -> old path for files the change renamed."""
    args = ["diff", "--name-status", "-M", "--no-color", base] + ([head] if head else [])
    renames: Dict[str, str] = {}
    for line in source.git(*args).splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].startswith("R"):
            renames[parts[2]] = parts[1]
    return renames


def change_markers(spec: Spec, source: Source) -> Dict[str, Dict[str, Any]]:
    """Per block: status (new, changed, same, deleted), added line indexes, and removed lines to show."""
    if not spec.base:
        return {}
    base = source.merge_base(spec.base, spec.head)
    renames = _renames(source, base, spec.head)
    per_file: Dict[str, Tuple[List[Hunk], bool, str]] = {}
    for path in sorted({b.file for b in spec.blocks if b.side == "head"}):
        old_path = renames.get(path, path)
        if not source.exists(old_path, base):
            per_file[path] = ([], False, old_path)  # new in this change, tracked or not
            continue
        args = ["diff", "-U0", "-M", "--no-color", "--no-ext-diff", base] + ([spec.head] if spec.head else [])
        paths = [old_path, path] if old_path != path else [path]
        per_file[path] = (parse_hunks(source.git(*args, "--", *paths)), True, old_path)
    base_side: Dict[str, List[Hunk]] = {}
    for path in sorted({b.file for b in spec.blocks if b.side == "base"}):
        args = ["diff", "-U0", "--no-color", "--no-ext-diff", base] + ([spec.head] if spec.head else [])
        base_side[path] = parse_hunks(source.git(*args, "--", path))

    markers: Dict[str, Dict[str, Any]] = {}
    for b in spec.blocks:
        numbers = range(b.start, b.end + 1)
        if b.side == "base":
            removed, _, _ = changed_lines(base_side[b.file])
            gone = [i for i, n in enumerate(numbers) if n in removed]
            status = "deleted" if len(gone) == len(numbers) else "changed"
            markers[b.id] = {"status": status, "added": [], "removed": gone, "inserted": {}}
            continue
        hunks, existed, old_path = per_file[b.file]
        if not existed:
            markers[b.id] = {"status": "new", "added": list(range(len(numbers))), "removed": [], "inserted": {}}
            continue
        _, added, cut = changed_lines(hunks)
        plus = [i for i, n in enumerate(numbers) if n in added]
        inserted: Dict[int, List[str]] = {}
        if b.role != "container" and any(count for _, count, _, _ in hunks):
            inserted = _insertions(hunks, b, source.read(old_path, base))
        trimmed = any(b.start <= n < b.end for n in cut)
        if plus and len(plus) == len(numbers):
            status = "new"
        elif plus or trimmed or inserted:
            status = "changed"
        else:
            status = "same"
        markers[b.id] = {"status": status, "added": plus, "removed": [], "inserted": inserted}
    return markers


def apply_rows(spec: Spec, markers: Dict[str, Dict[str, Any]]) -> None:
    """Give each changed block the rows to draw: its lines, marked, with removed lines in place."""
    for b in spec.blocks:
        mark = markers.get(b.id)
        if not mark or b.role == "container":
            continue
        added = set(mark.get("added", []))
        removed = set(mark.get("removed", []))
        inserted = mark.get("inserted", {})
        rows: List[Tuple[str, str]] = []
        index_map: List[int] = []
        for i, line in enumerate(b.lines):
            rows.extend((old, "del") for old in inserted.get(i, []))
            index_map.append(len(rows))
            kind = "del" if b.side == "base" and i in removed else ("add" if i in added else "")
            rows.append((line, kind))
        rows.extend((old, "del") for old in inserted.get(len(b.lines), []))
        b.rows, b.index_map = rows, index_map


def pull_request(source: Source, number: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Fetch the PR title and description verbatim with gh. Returns (claim, warning)."""
    try:
        out = subprocess.run(["gh", "pr", "view", str(number), "--json", "number,title,body,url"],
                             cwd=str(source.root), capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"could not run gh to read PR #{number}: {exc}"
    if out.returncode != 0:
        return None, f"gh could not read PR #{number}: {out.stderr.strip()}"
    try:
        data = json.loads(out.stdout)
    except ValueError:
        return None, f"gh returned something other than JSON for PR #{number}"
    claim = {k: data.get(k) for k in ("number", "title", "body", "url")}
    claim["source"] = "pr"
    return claim, None


def commit_messages(source: Source, base: str, head: Optional[str]) -> Optional[Dict[str, Any]]:
    """For a branch with no PR: its commit messages, verbatim and oldest first, as the author's claim."""
    try:
        start = source.merge_base(base, head)
        text = source.git("log", "--reverse", "--format=%h%x01%s%n%n%b%x00", f"{start}..{head or 'HEAD'}")
    except SourceError:
        return None
    commits = []
    for entry in text.split("\x00"):
        sha, _, message = entry.strip().partition("\x01")
        if message.strip():
            commits.append({"sha": sha, "message": message.strip()})
    if not commits:
        return None
    body = "\n\n".join(c["message"] for c in commits)
    if len(body) > CLAIM_CHARS:
        body = body[:CLAIM_CHARS] + "\n\n(cut at 20,000 characters)"
    # The same budget for the per-commit list; the commit that crosses it is cut and carries the note.
    kept, room = [], CLAIM_CHARS
    for c in commits:
        if len(c["message"]) > room:
            kept.append({**c, "message": c["message"][:room].rstrip() + "\n\n(cut at 20,000 characters)"})
            break
        kept.append(c)
        room -= len(c["message"])
    count = len(commits)
    return {"source": "commits", "title": f"{count} commit{'s' if count != 1 else ''} on {head or 'HEAD'}",
            "body": body, "commits": kept, "number": None, "url": None}
