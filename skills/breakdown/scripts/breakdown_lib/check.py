"""Check a spec against the source: ranges, declarations, brackets, arrows and labels.

Every problem says where it is, what is wrong and a concrete fix, so an agent can
correct the spec and run the check again without guessing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .diff import apply_rows, change_markers
from .lang import (ARROW_FUNCTION, DECLARATION, DEF_HINT, IDENT, Scanner, family, indent, looks_declared,
                   masked, note_kind, skip_decorator, word)
from .model import Block, Edge, Spec, err, load_spec
from .source import Source, SourceError

MAX_BLOCKS = 40
WARN_BLOCKS = 20
TALL_BLOCK = 150
LABEL_WORDS = 4
LABEL_CHARS = 32
JUDGING = {
    "robust", "clean", "cleaner", "simple", "simply", "elegant", "efficient", "optimal", "optimized",
    "important", "crucial", "best", "good", "great", "nice", "smart", "powerful", "seamless", "proper",
    "properly", "correct", "correctly", "buggy", "bad", "ugly", "messy", "smelly", "hacky", "safely",
}
CONTINUES = ("=>", "=", "->", "+", "-", "*", "/", "||", "&&", "??", "?", ":", ",", "(", "[", ".")


class Report:
    def __init__(self) -> None:
        self.errors: List[Dict[str, str]] = []
        self.fixes: List[str] = []
        self.hints: List[str] = []
        self.warnings: List[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"ok": self.ok}
        for name in ("errors", "fixes", "hints", "warnings"):
            value = getattr(self, name)
            if value:
                out[name] = value
        return out


def _decorator_top(lines: List[str], s: int, fam: Optional[str], decl_indent: int) -> Optional[int]:
    """The 1-based line of a decorator whose brackets open there and close on the line right above s."""
    if not lines[s - 2].strip()[:1] in (")", "]", "}"):
        return None
    for top in range(s - 2, max(0, s - 41), -1):
        line = lines[top - 1]
        if not line.strip():
            return None
        if indent(line) <= decl_indent:
            if note_kind(line, fam) != "decorator" or indent(line) != decl_indent:
                return None  # reached another statement at this level before any decorator
            sc = Scanner(fam)
            for k in range(top - 1, s - 1):
                sc.feed(lines[k])
                if k < s - 2 and not sc.inside:
                    return None  # it closes early: the line above is not this decorator's end
            return top if not sc.inside else None
    return None


def snap_start(lines: List[str], start: int, fam: Optional[str]) -> int:
    """Move start up over the decorators and doc comments that belong to the declaration (1-based)."""
    decl_indent = indent(lines[start - 1])
    s = start
    while s > 1:
        above = lines[s - 2]
        kind = note_kind(above, fam)
        if kind == "comment" and indent(above) <= decl_indent + 1:
            s -= 1
            continue
        if kind == "decorator" and indent(above) == decl_indent:
            s -= 1
            continue
        top = _decorator_top(lines, s, fam, decl_indent)
        if top is None:
            break
        s = top  # always above s, so the loop moves on
    return s


def definition_line(lines: List[str], token: str, fam: Optional[str]) -> Optional[int]:
    """Index of the line in a block that names it, skipping comments and whole decorators."""
    pattern = word(token)
    i, code_lines = 0, 0
    while i < min(len(lines), 60):
        line = lines[i]
        kind = note_kind(line, fam)
        if not line.strip() or kind == "comment":
            i += 1
            continue
        if kind == "decorator":
            i = skip_decorator(lines, i, fam)
            continue
        if pattern.search(line):
            return i
        code_lines += 1
        if code_lines >= 4:
            break
        i += 1
    return None


def find_definitions(lines: List[str], token: str, fam: Optional[str], limit: int = 3) -> List[int]:
    """1-based lines in a file that look like the declaration of token."""
    pattern = word(token)
    strong, weak = [], []
    for n, line in enumerate(lines, 1):
        if not pattern.search(line) or note_kind(line, fam):
            continue
        (strong if looks_declared(line, token, fam) else weak).append(n)
    return (strong + weak)[:limit]


def bracket_end(lines: List[str], start: int, fam: Optional[str], rust: bool) -> Optional[int]:
    """The 1-based line where brackets opened from start close again."""
    sc = Scanner(fam, rust)
    for k in range(start - 1, min(len(lines), start - 1 + 4000)):
        sc.feed(lines[k])
        if sc.opened and sc.depth <= 0 and sc.mode is None:
            return k + 1
    return None


def declaration_end(lines: List[str], def_abs: int, fam: Optional[str], rust: bool) -> Optional[int]:
    """The 1-based last line of the declaration whose first line is lines[def_abs], in a brace language.

    A line that ends in an operator or `=>`, or a next line that is indented deeper or opens a brace,
    continues the declaration.
    """
    sc = Scanner(fam, rust)
    base = indent(lines[def_abs])
    k = def_abs
    while k < min(len(lines), def_abs + 4000):
        code = sc.feed(lines[k]).rstrip()
        if sc.opened and sc.depth <= 0 and sc.mode is None:
            nxt = next((j for j in range(k + 1, len(lines)) if lines[j].strip()), None)
            continues = code.endswith(CONTINUES) or (
                nxt is not None and (indent(lines[nxt]) > base or lines[nxt].lstrip().startswith(("{", ".", "?", ":"))))
            if not continues:
                return k + 1
        k += 1
    return None


def python_extent(lines: List[str], def_abs: int) -> int:
    """The 1-based last line of the Python statement whose header is at def_abs (0-based).

    Blank lines and comment-only lines never end a body, wherever their `#` sits.
    """
    base = indent(lines[def_abs])
    sc = Scanner("python")
    k = def_abs
    while k < len(lines):
        sc.feed(lines[k])
        if not sc.inside:
            break
        k += 1
    last = k
    j = k + 1
    while j < len(lines):
        line = lines[j]
        inside = sc.inside
        stripped = line.strip()
        if not inside and (not stripped or stripped.startswith("#")):
            j += 1
            continue
        if inside or indent(line) > base:
            sc.feed(line)
            last = j
            j += 1
            continue
        break
    return last + 1


def _excerpt(line: str, width: int = 70) -> str:
    text = line.strip()
    return text if len(text) <= width else text[: width - 1] + "…"


class Checker:
    def __init__(self, spec: Spec, source: Source, report: Report):
        self.spec = spec
        self.source = source
        self.report = report
        self.base_ref: Optional[str] = None

    def error(self, at: str, problem: str, fix: str = "") -> None:
        self.report.errors.append(err(at, problem, fix))

    # Refs and paths -----------------------------------------------------

    def refs(self) -> bool:
        spec = self.spec
        if not (spec.base or spec.head or any(b.side == "base" for b in spec.blocks)):
            return True
        try:
            self.source.git("--version")
        except SourceError:
            self.error("base", "git is not available, so base and head cannot be read",
                       "install git, or remove base, head and side from the spec")
            return False
        ok = True
        for name in ("base", "head"):
            ref = getattr(spec, name)
            if ref and not self.source.verify_ref(ref):
                self.error(name, f'"{ref}" is not a commit in this repository',
                           "fetch it first (for a GitHub PR: git fetch origin pull/<n>/head) or use a sha from gh pr view")
                ok = False
        needs_base = [b for b in spec.blocks if b.side == "base"]
        if needs_base and not spec.base:
            self.error(needs_base[0].where, 'side "base" needs a "base" ref at the top of the spec',
                       'add "base": "<the PR base sha or branch>"')
            ok = False
        if ok and spec.base:
            try:
                self.base_ref = self.source.merge_base(spec.base, spec.head)
            except SourceError as exc:
                self.error("base", f"no merge base between {spec.base} and {spec.head or 'HEAD'}: {exc}",
                           "check that both refs are fetched")
                ok = False
        return ok

    def relative_path(self, b: Block) -> bool:
        path = Path(b.file)
        if not path.is_absolute():
            return True
        try:
            rel = path.resolve().relative_to(self.source.root)
        except ValueError:
            self.error(b.where, f"{b.file} is outside the repository at {self.source.root}",
                       "use a path relative to the repository root")
            return False
        b.file = str(rel).replace("\\", "/")
        self.report.fixes.append(f"{b.where}: file made relative to the repository root: {b.file}")
        return True

    # Blocks ---------------------------------------------------------------

    def file_lines(self, b: Block) -> Optional[List[str]]:
        ref = self.base_ref if b.side == "base" else self.spec.head
        try:
            return self.source.read(b.file, ref)
        except SourceError as exc:
            near = self.source.similar_paths(b.file) if not ref else []
            fix = f"did you mean {' or '.join(near)}?" if near else "paths are relative to the repository root"
            self.error(b.where, str(exc), fix)
            return None

    def block(self, b: Block) -> None:
        if not self.relative_path(b):
            return
        lines = self.file_lines(b)
        if lines is None:
            return
        total = len(lines)
        if b.end > total:
            self.error(b.where, f"lines {b.start}-{b.end} run past the end of {b.file}, which has {total} lines",
                       "read the file again and use its real line numbers")
            return
        fam = family(b.file)
        rust = b.file.endswith(".rs")

        start = snap_start(lines, b.start, fam)
        if start != b.start:
            self.report.fixes.append(f"{b.where}: start {b.start} -> {start} to include the decorators or comments above it")
            b.start = start

        block_lines = lines[b.start - 1:b.end]
        def_idx = definition_line(block_lines, b.token, fam)
        if def_idx is None:
            found = find_definitions(lines, b.token, fam)
            if found:
                n = found[0]
                fix = f'"{_excerpt(lines[n - 1])}" is at line {n}; start the block there or at its decorators'
            else:
                fix = (f'"{b.token}" does not appear in {b.file}; check the path, or set "name" to the '
                       "identifier on the block's first line")
            self.error(b.where, f'{b.span} does not start with the declaration of "{b.token}"', fix)
            return
        b.def_line = def_idx
        def_abs = b.start - 1 + def_idx
        if not looks_declared(lines[def_abs], b.token, fam):
            self.report.warnings.append(
                f'{b.where}: line {def_abs + 1} ("{_excerpt(lines[def_abs])}") uses {b.token} but does not look like '
                "its declaration; check the range")

        if fam == "python":
            k = b.start - 1
            while k < def_abs:
                if note_kind(lines[k], fam) == "decorator":
                    k = skip_decorator(lines, k, fam)
                    continue
                if lines[k].strip() and note_kind(lines[k], fam) != "comment":
                    self.error(b.where, f"line {k + 1} comes before the declaration of {b.token} at line {def_abs + 1}",
                               f"start the block at line {def_abs + 1}, or at the decorators right above it")
                    return
                k += 1
            real_end = python_extent(lines, def_abs)
            if b.end < real_end:
                self.error(b.where, f"{b.span} stops before the end of {b.token}, which runs to line {real_end}",
                           f"end the block at line {real_end}")
                return
            tail = [k for k in range(real_end, b.end) if lines[k].strip() and not note_kind(lines[k], fam)]
            if tail:
                k = tail[0]
                self.error(b.where, f'{b.span} runs past the end of {b.token} into line {k + 1} ("{_excerpt(lines[k])}")',
                           f"end the block at line {real_end}")
                return
        elif fam is not None and not b.no_bracket_check:
            sc = Scanner(fam, rust)
            for line in block_lines:
                sc.feed(line)
            if sc.min_depth < 0:
                self.error(b.where, f"{b.span} closes a bracket it never opened",
                           f"start the block at the declaration of {b.token} (line {def_abs + 1}) or above; if the "
                           'range is right and odd syntax confuses the count, add "no_bracket_check": true')
                return
            if sc.depth > 0:
                real_end = bracket_end(lines, b.start, fam, rust)
                fix = (f"end the block at line {real_end}" if real_end
                       else 'check the range; if odd syntax confuses the count, add "no_bracket_check": true')
                self.error(b.where, f"{b.span} leaves {sc.depth} bracket(s) open, so it stops too early", fix)
                return
            if fam in ("c", "php"):
                decl_end = declaration_end(lines, def_abs, fam, rust)
                extra = [k for k in range(decl_end or b.end, b.end) if lines[k].strip() and not note_kind(lines[k], fam)]
                if decl_end and extra:
                    k = extra[0]
                    self.report.warnings.append(
                        f'{b.where}: {b.span} seems to run past the end of {b.token} (line {decl_end}) into '
                        f'line {k + 1} ("{_excerpt(lines[k])}"); if so, end the block at line {decl_end}')
        if len(block_lines) > TALL_BLOCK:
            self.report.warnings.append(f"{b.where}: {len(block_lines)} lines make a very tall box; "
                                        "consider a smaller declaration or splitting it")
        b.lines = block_lines

    def containers(self) -> None:
        spec = self.spec
        for b in spec.blocks:
            if not b.parent:
                continue
            parent = spec.by_id.get(b.parent)
            if parent is None:
                self.error(b.where, f'parent "{b.parent}" is not a block id', "add the class as a block with role container")
                continue
            if b.role == "type":
                self.error(b.where, "a type cannot sit inside a container",
                           "remove its parent and keep it as its own type block")
                continue
            if parent.parent:
                self.error(b.where, f'"{parent.id}" is itself inside "{parent.parent}"; containers have one level',
                           "point the method at the outer container, or drop the nesting")
                continue
            if parent.role == "type":
                self.error(parent.where, "a type cannot hold method blocks", 'set its role to "container"')
                continue
            if parent.role == "code":
                parent.role = "container"
                self.report.fixes.append(f"{parent.where}: role set to container because blocks name it as parent")
            if b.file != parent.file or b.side != parent.side:
                self.error(b.where, f"{b.id} is not in the same file as its container {parent.id}",
                           "a container only holds blocks from its own lines")
                continue
            if not (parent.start <= b.start and b.end <= parent.end):
                self.error(b.where, f"{b.span} is not inside its container {parent.span}",
                           "a method must sit inside its class's lines; fix the range or the parent")
        for b in spec.blocks:
            if b.role == "container" and not spec.children(b.id):
                self.error(b.where, "a container needs at least one method block",
                           f'give its methods "parent": "{b.id}", or set role to "code"')

    def overlaps(self) -> None:
        blocks = [b for b in self.spec.blocks if b.lines]
        for i, a in enumerate(blocks):
            for b in blocks[i + 1:]:
                if a.file != b.file or a.side != b.side or a.parent == b.id or b.parent == a.id:
                    continue
                if a.start <= b.end and b.start <= a.end:
                    lo, hi = max(a.start, b.start), min(a.end, b.end)
                    self.error(b.where, f"{b.span} and {a.id} ({a.span}) overlap at lines {lo}-{hi}",
                               "end one block before the next starts, or make one the parent of the other")

    # Changes --------------------------------------------------------------

    def changes(self) -> None:
        """Mark changed lines before arrows are checked, so an arrow can leave from a removed line."""
        if not self.spec.base:
            return
        try:
            self.spec.markers = change_markers(self.spec, self.source)
        except SourceError as exc:
            self.error("base", f"git diff failed: {exc}", "check that base and head are fetched")
            return
        apply_rows(self.spec, self.spec.markers)

    # Arrows ---------------------------------------------------------------

    def _search(self, src: Block, text: str, *, raw: bool, keep_strings: bool, skip_own: bool) -> int:
        """First index among src's shown lines where text appears as code."""
        lines = src.shown
        if not raw:
            lines = masked(lines, family(src.file), keep_strings, rust=src.file.endswith(".rs"))
        if src.role == "container":
            # A container speaks only for its own lines; its methods' lines belong to their blocks.
            kids = [(c.start - src.start, c.end - src.start) for c in self.spec.children(src.id)]
            lines = ["" if any(lo <= i <= hi for lo, hi in kids) else line for i, line in enumerate(lines)]
        pattern = word(text) if IDENT.match(text) else re.compile(re.escape(text))
        own = src.shown_index(src.def_line) if skip_own else -1
        for i, line in enumerate(lines):
            if i != own and pattern.search(line):
                return i
        return -1

    def edges(self) -> None:
        spec = self.spec
        seen = set()
        kept: List[Edge] = []
        for e in spec.edges:
            src, dst = spec.block(e.src), spec.block(e.dst)
            if e.src == e.dst:
                self.error(e.where, "an arrow cannot point at its own block", "remove it")
                continue
            if src.parent == dst.id or dst.parent == src.id:
                self.error(e.where, "an arrow between a container and its own method adds nothing",
                           "draw arrows between the methods instead")
                continue
            if (e.src, e.dst) in seen:
                self.report.warnings.append(f"{e.where}: duplicate arrow dropped")
                continue
            seen.add((e.src, e.dst))
            if e.kind is None:
                e.kind = "uses" if dst.role == "type" else "calls"
            evidence = e.via or dst.token
            # A via is the agent's exact text, strings included. A name must appear in code; for a type,
            # a quoted forward reference such as list["OrderLine"] counts.
            line = self._search(src, evidence, raw=bool(e.via), keep_strings=dst.role == "type",
                                skip_own=not e.via and dst.token == src.token)
            if line < 0:
                self.error(e.where, f'"{evidence}" does not appear in the code of {src.id} ({src.span})',
                           'if the code reaches it under another spelling, set "via" to the exact text '
                           "(such as \"new Catalog(\" or \"this.repo\"); otherwise remove the arrow. "
                           "Mentions in comments and docstrings do not count")
                continue
            e.line = line
            kept.append(e)
        spec.edges = kept

    def hints(self) -> None:
        spec = self.spec
        arrows = {(e.src, e.dst) for e in spec.edges}
        for a in spec.blocks:
            for b in spec.blocks:
                if a is b or a.parent == b.id or b.parent == a.id or (a.id, b.id) in arrows:
                    continue
                tok = b.token
                if len(tok) < 3 or not (len(tok) >= 5 or "_" in tok or tok[:1].isupper()):
                    continue
                if b.role == "container" and any((a.id, c.id) in arrows for c in spec.children(b.id)):
                    continue
                if a.role == "container" and any(c.id == b.id or (c.id, b.id) in arrows for c in spec.children(a.id)):
                    continue
                idx = self._search(a, tok, raw=False, keep_strings=b.role == "type", skip_own=tok == a.token)
                if idx >= 0:
                    self.report.hints.append(
                        f"{a.id} mentions {tok} (line {idx + 1} of its box) with no arrow to {b.id}; "
                        "add one if the code uses it")

    def missing(self) -> None:
        """Hint at declarations in the files already used that a chosen block mentions but no block covers."""
        spec = self.spec
        tokens = {b.token for b in spec.blocks}
        declared: Dict[str, Tuple[str, int]] = {}
        for path in sorted({b.file for b in spec.blocks if b.side == "head"}):
            fam = family(path)
            pattern = DECLARATION.get(fam or "")
            if pattern is None:
                continue
            try:
                lines = self.source.read(path, spec.head)
            except SourceError:
                continue
            for n, line in enumerate(lines, 1):
                m = pattern.match(line) or (ARROW_FUNCTION.match(line) if fam == "c" else None)
                if m and len(m.group(1)) >= 4 and m.group(1) not in tokens:
                    declared.setdefault(m.group(1), (path, n))
        hinted = set()
        for b in spec.blocks:
            if b.role != "code" or b.side != "head":
                continue
            for name, (path, n) in declared.items():
                if name in hinted or (path == b.file and b.start <= n <= b.end):
                    continue
                idx = self._search(b, name, raw=False, keep_strings=False, skip_own=False)
                if idx >= 0:
                    hinted.add(name)
                    self.report.hints.append(
                        f"{b.id} mentions {name} (line {idx + 1} of its box), declared at {path}:{n} but not a block; "
                        "add it, or leave it out on purpose and name it in your reply")

    # Labels and shape -----------------------------------------------------

    def labels(self) -> None:
        for b in self.spec.blocks:
            if not b.label:
                continue
            words = b.label.split()
            judged = sorted({w.lower().strip(".,:;!?()") for w in words} & JUDGING)
            if judged:
                self.error(b.where, f'label "{b.label}" judges the code ("{judged[0]}")',
                           "name its role instead, such as Entry point, Reads DB, Writes DB or Request body")
            elif len(words) > LABEL_WORDS or len(b.label) > LABEL_CHARS:
                self.error(b.where, f'label "{b.label}" is longer than {LABEL_WORDS} words or {LABEL_CHARS} characters',
                           "use 2-4 words that name a role, such as Writes DB")

    def shape(self) -> None:
        spec = self.spec
        for e in spec.entry:
            if spec.block(e).role == "type":
                self.error("entry", f'entry "{e}" is a type', "start from the function that runs first")
        n = len(spec.blocks)
        if n > MAX_BLOCKS:
            self.error("blocks", f"{n} blocks is too many for one canvas",
                       "split the flow into separate breakdowns of about 16 blocks each")
        elif n > WARN_BLOCKS:
            self.report.warnings.append(f"{n} blocks is more than one canvas reads well (about 16); "
                                        "leave out exception classes and small helpers first, or split the flow")

    def run(self) -> None:
        if not self.refs():
            return
        for b in self.spec.blocks:
            self.block(b)
        if self.report.errors:
            return
        self.containers()
        self.overlaps()
        self.labels()
        self.shape()
        if self.report.errors:
            return
        self.changes()
        if self.report.errors:
            return
        self.edges()
        if not self.report.errors:
            self.hints()
            self.missing()


def run_check(data: Any, source: Source) -> Tuple[Optional[Spec], Report]:
    report = Report()
    spec, errors, warnings = load_spec(data)
    report.errors.extend(errors)
    report.warnings.extend(warnings)
    if spec is None:
        return None, report
    Checker(spec, source, report).run()
    return spec, report


__all__ = ["Report", "run_check", "snap_start", "definition_line", "python_extent", "declaration_end", "DEF_HINT"]
