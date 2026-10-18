"""Changes: which lines in each block were added or removed, and the author's own words about them."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple

from .model import Spec
from .source import Source, SourceError

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
CLAIM_CHARS = 20000


def parse_hunks(text: str) -> List[Tuple[int, int, int, int]]:
    """(old_start, old_count, new_start, new_count) for each hunk of a zero-context diff."""
    hunks = []
    for line in text.splitlines():
        m = HUNK.match(line)
        if m:
            a, b, c, d = m.groups()
            hunks.append((int(a), 1 if b is None else int(b), int(c), 1 if d is None else int(d)))
    return hunks


def changed_lines(hunks: List[Tuple[int, int, int, int]]) -> Tuple[Set[int], Set[int], Set[int]]:
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


def _insertions(hunks: List[Tuple[int, int, int, int]], start: int, end: int,
                base_lines: List[str]) -> Dict[int, List[str]]:
    """Removed base lines to show inside a head block, keyed by the head line index they come before."""
    out: Dict[int, List[str]] = {}
    for a, b, c, d in hunks:
        if b == 0:
            continue
        if d > 0:
            # A replacement: the old lines go just before the new ones, which start at head line c.
            if not start <= c <= end:
                continue
            index = c - start
        else:
            # A pure deletion between head lines c and c + 1, counted only when it falls inside the block.
            if not start <= c < end:
                continue
            index = c + 1 - start
        out.setdefault(index, []).extend(base_lines[a - 1:a - 1 + b])
    return out


def change_markers(spec: Spec, source: Source) -> Dict[str, Dict[str, Any]]:
    """Per block: status (new, changed, same, deleted), added line indexes, and removed lines to show."""
    if not spec.base:
        return {}
    base = source.merge_base(spec.base, spec.head)
    per_file: Dict[str, List[Tuple[int, int, int, int]]] = {}
    for path in sorted({b.file for b in spec.blocks}):
        args = ["diff", "-U0", "--no-color", "--no-ext-diff", base]
        if spec.head:
            args.append(spec.head)
        per_file[path] = parse_hunks(source.git(*args, "--", path))

    markers: Dict[str, Dict[str, Any]] = {}
    for b in spec.blocks:
        hunks = per_file[b.file]
        removed, added, cut = changed_lines(hunks)
        numbers = range(b.start, b.end + 1)
        if b.side == "base":
            gone = [i for i, n in enumerate(numbers) if n in removed]
            status = "deleted" if len(gone) == len(numbers) else "changed"
            markers[b.id] = {"status": status, "added": [], "removed": gone, "inserted": {}}
            continue
        plus = [i for i, n in enumerate(numbers) if n in added]
        inserted: Dict[int, List[str]] = {}
        if b.role != "container" and any(bb for _, bb, _, _ in hunks):
            try:
                inserted = _insertions(hunks, b.start, b.end, source.read(b.file, base))
            except SourceError:
                inserted = {}  # the file is new in head, so nothing was removed from it
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
                             cwd=str(source.root), capture_output=True, text=True, timeout=60)
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
        text = source.git("log", "--reverse", "--format=%s%n%n%b%x00", f"{start}..{head or 'HEAD'}")
    except SourceError:
        return None
    messages = [m.strip() for m in text.split("\x00") if m.strip()]
    if not messages:
        return None
    body = "\n\n".join(messages)
    if len(body) > CLAIM_CHARS:
        body = body[:CLAIM_CHARS] + "\n\n(cut at 20,000 characters)"
    count = len(messages)
    return {"source": "commits", "title": f"{count} commit{'s' if count != 1 else ''} on {head or 'HEAD'}",
            "body": body, "number": None, "url": None}
