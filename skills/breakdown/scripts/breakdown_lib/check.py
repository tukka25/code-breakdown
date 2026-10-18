"""Check a spec against the source: ranges, declarations, brackets, arrows and labels.

Every problem says where it is, what is wrong and a concrete fix, so an agent can
correct the spec and run the check again without guessing.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from .model import Block, Edge, Spec, err, load_spec
from .source import Source, SourceError

MAX_BLOCKS = 40
WARN_BLOCKS = 20
LABEL_WORDS = 4
LABEL_CHARS = 32
JUDGING = {
    "robust", "clean", "cleaner", "safe", "safely", "unsafe", "simple", "simply", "elegant",
    "efficient", "optimal", "optimized", "critical", "important", "crucial", "key", "best",
    "good", "great", "nice", "smart", "powerful", "seamless", "solid", "proper", "properly",
    "correct", "correctly", "buggy", "bad", "ugly", "messy", "magic", "smelly", "hacky",
}

PYTHON = {".py", ".pyi", ".pyw"}
HASH = {".rb", ".sh", ".bash", ".zsh", ".pl", ".pm", ".r", ".ex", ".exs", ".cr", ".nim", ".jl", ".coffee"}
C_LIKE = {
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".java", ".kt", ".kts", ".scala",
    ".go", ".rs", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".cs", ".swift", ".php", ".dart",
    ".groovy", ".m", ".mm", ".zig", ".v", ".sol",
}
SQL = {".sql"}

IDENT = re.compile(r"^[A-Za-z_$][\w$]*$")
SNAPPABLE = re.compile(
    r"^\s*(@|#\[|///?|/\*|\*|--|"
    r"#(?!\s*(?:include|define|if|ifdef|ifndef|endif|else|elif|pragma|undef|import)\b)|"
    r"\[[A-Za-z_][^\]]*\]\s*$)"
)
# Declarations worth suggesting as blocks when a chosen block mentions them but no block covers them.
DECLARATION = {
    "python": re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)"),
    "c": re.compile(
        r"^\s*(?:export\s+)?(?:default\s+)?"
        r"(?:(?:public|private|protected|internal|static|abstract|final|async|sealed|open|pub(?:\([^)]*\))?)\s+)*"
        r"(?:function\*?|class|interface|type|enum|struct|trait|fn|func|record)\s+(?:\([^)]*\)\s*)?([A-Za-z_$][\w$]*)"
    ),
    "hash": re.compile(r"^\s*(?:def|class|module)\s+(?:self\.)?([A-Za-z_]\w*)"),
}
ARROW_FUNCTION = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s+)?"
    r"(?:function\b|\([^)]*\)\s*(?::[^=]+)?=>|[A-Za-z_$][\w$]*\s*=>)"
)
DEF_HINT = re.compile(
    r"\b(def|class|function|func|fn|interface|type|struct|enum|trait|impl|module|record|object|"
    r"let|const|var|val|async|export|public|private|protected|internal|static|override|sub)\b"
)


def word(text: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![\w$])" + re.escape(text) + r"(?![\w$])")


def family(path: str) -> Optional[str]:
    ext = PurePosixPath(path).suffix.lower()
    if ext in PYTHON:
        return "python"
    if ext in C_LIKE:
        return "c"
    if ext in HASH:
        return "hash"
    if ext in SQL:
        return "sql"
    return None


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


class Scanner:
    """Track bracket depth line by line, skipping strings and comments."""

    def __init__(self, fam: Optional[str], rust: bool = False):
        self.fam = fam
        self.rust = rust
        self.depth = 0
        self.min_depth = 0
        self.opened = False
        self.mode: Any = None  # None, "block" for /* */, or ("str", delimiter)

    @property
    def inside(self) -> bool:
        return self.depth > 0 or self.mode is not None

    def feed(self, line: str) -> int:
        i, n = 0, len(line)
        while i < n:
            c = line[i]
            if self.mode == "block":
                j = line.find("*/", i)
                if j < 0:
                    return self.depth
                i, self.mode = j + 2, None
                continue
            if isinstance(self.mode, tuple):
                delim = self.mode[1]
                if c == "\\":
                    i += 2
                    continue
                if line.startswith(delim, i):
                    i += len(delim)
                    self.mode = None
                    continue
                i += 1
                continue
            if c == "#" and self.fam in ("python", "hash"):
                break
            if self.fam in ("c", "sql") and line.startswith("/*", i):
                self.mode, i = "block", i + 2
                continue
            if self.fam == "c" and line.startswith("//", i):
                break
            if self.fam == "sql" and line.startswith("--", i):
                break
            if c in "\"'`":
                if self.fam == "python" and line.startswith(c * 3, i):
                    self.mode, i = ("str", c * 3), i + 3
                    continue
                if c == "`" and self.fam != "c":
                    i += 1
                    continue
                if c == "'" and self.rust:
                    m = re.match(r"'(\\.[^']*|[^\\'])'", line[i:])
                    i += len(m.group(0)) if m else 1
                    continue
                self.mode, i = ("str", c), i + 1
                continue
            if c in "([{":
                self.depth += 1
                self.opened = True
            elif c in ")]}":
                self.depth -= 1
                self.min_depth = min(self.min_depth, self.depth)
            i += 1
        # Single-quoted and double-quoted strings end with the line; triple quotes and backticks carry on.
        if isinstance(self.mode, tuple) and self.mode[1] in ("'", '"'):
            self.mode = None
        return self.depth


def indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def is_note(line: str) -> bool:
    """A decorator, attribute or comment line that belongs to the declaration below it."""
    return bool(line.strip()) and bool(SNAPPABLE.match(line))


def _decorator_top(lines: List[str], s: int, fam: Optional[str]) -> Optional[int]:
    """The 1-based line of an @decorator whose arguments close on the line above s."""
    for top in range(s - 2, max(0, s - 18), -1):
        if lines[top - 1].lstrip().startswith("@"):
            sc = Scanner(fam)
            for k in range(top - 1, s - 1):
                sc.feed(lines[k])
            return top if sc.depth == 0 and sc.mode is None else None
    return None


def snap_start(lines: List[str], start: int, fam: Optional[str]) -> int:
    """Move start up over decorators and doc comments directly above it (1-based)."""
    s = start
    while s > 1:
        above = lines[s - 2]
        if is_note(above):
            s -= 1
            continue
        # A decorator whose arguments span several lines ends with a closing bracket above the def.
        if above.strip()[:1] in (")", "]") and fam in ("python", "c"):
            top = _decorator_top(lines, s, fam)
            if top is not None:
                s = top  # always above s, so the loop moves on
                continue
        break
    return s


def definition_line(lines: List[str], token: str) -> Optional[int]:
    """Index of the line in a block that names it, skipping decorators and comments."""
    pattern = word(token)
    code_lines = 0
    for i, line in enumerate(lines[:30]):
        if not line.strip() or is_note(line):
            continue
        if pattern.search(line):
            return i
        code_lines += 1
        if code_lines >= 4:
            break
    return None


def find_definitions(lines: List[str], token: str, limit: int = 3) -> List[int]:
    """1-based lines in a file that look like the declaration of token."""
    pattern = word(token)
    strong, weak = [], []
    for n, line in enumerate(lines, 1):
        if not pattern.search(line) or is_note(line):
            continue
        stripped = line.lstrip()
        if DEF_HINT.search(line.split(token)[0] + " ") or stripped.startswith(token):
            strong.append(n)
        else:
            weak.append(n)
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
    """The 1-based line where the brackets opened on a declaration's first line close again.

    A brace on the next line (Allman style) continues the declaration.
    """
    sc = Scanner(fam, rust)
    k = def_abs
    while k < min(len(lines), def_abs + 4000):
        sc.feed(lines[k])
        if sc.opened and sc.depth <= 0 and sc.mode is None:
            nxt = next((j for j in range(k + 1, len(lines)) if lines[j].strip()), None)
            if nxt is None or not lines[nxt].lstrip().startswith("{"):
                return k + 1
        k += 1
    return None


def python_extent(lines: List[str], def_abs: int) -> int:
    """The 1-based last line of the Python statement whose header is at def_abs (0-based)."""
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
        if not line.strip() and not inside:
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

    # Blocks ---------------------------------------------------------------

    def refs(self) -> bool:
        spec = self.spec
        ok = True
        for name in ("base", "head"):
            ref = getattr(spec, name)
            if ref and not self.source.verify_ref(ref):
                self.error(name, f'"{ref}" is not a commit in this repository',
                           "fetch it first (for a PR: git fetch origin pull/<n>/head) or use a sha from gh pr view")
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
        def_idx = definition_line(block_lines, b.token)
        if def_idx is None:
            found = find_definitions(lines, b.token)
            if found:
                n = found[0]
                fix = f'"{_excerpt(lines[n - 1])}" is at line {n}; start the block there'
            else:
                fix = (f'"{b.token}" does not appear in {b.file}; check the path, or set "name" to the '
                       "identifier on the block's first line")
            self.error(b.where, f'{b.span} does not start with the declaration of "{b.token}"', fix)
            return
        b.def_line = def_idx
        def_abs = b.start - 1 + def_idx

        if fam == "python":
            decorator: Optional[Scanner] = None
            for k in range(b.start - 1, def_abs):
                if decorator is not None and decorator.inside:
                    decorator.feed(lines[k])  # an argument line of a decorator that spans several lines
                    continue
                if lines[k].lstrip().startswith("@"):
                    decorator = Scanner("python")
                    decorator.feed(lines[k])
                    continue
                if lines[k].strip() and not is_note(lines[k]):
                    self.error(b.where, f"line {k + 1} comes before the declaration of {b.token} at line {def_abs + 1}",
                               f"start the block at line {def_abs + 1}, or at the decorators right above it")
                    return
            real_end = python_extent(lines, def_abs)
            if b.end < real_end:
                self.error(b.where, f"{b.span} stops before the end of {b.token}; line {b.end + 1} is still part of it",
                           f"end the block at line {real_end}")
                return
            tail = [k for k in range(real_end, b.end) if lines[k].strip() and not is_note(lines[k])]
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
                self.error(b.where, f"{b.span} closes a bracket it never opened, so it starts inside another declaration",
                           f"start the block at the declaration of {b.token}, line {def_abs + 1}")
                return
            if sc.depth > 0:
                real_end = bracket_end(lines, b.start, fam, rust)
                fix = (f"end the block at line {real_end}" if real_end
                       else 'check the range; if a regex or string confuses the count, add "no_bracket_check": true')
                self.error(b.where, f"{b.span} leaves {sc.depth} bracket(s) open, so it stops too early", fix)
                return
            if fam == "c":
                decl_end = declaration_end(lines, def_abs, fam, rust)
                extra = [k for k in range(decl_end or b.end, b.end) if lines[k].strip() and not is_note(lines[k])]
                if decl_end and extra:
                    k = extra[0]
                    self.report.warnings.append(
                        f'{b.where}: {b.span} seems to run past the end of {b.token} (line {decl_end}) into '
                        f'line {k + 1} ("{_excerpt(lines[k])}"); if so, end the block at line {decl_end}')
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

    # Arrows ---------------------------------------------------------------

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
            pattern = word(evidence) if IDENT.match(evidence) else re.compile(re.escape(evidence))
            line = next((i for i, text in enumerate(src.lines) if pattern.search(text)), -1)
            if line < 0:
                self.error(e.where, f'"{evidence}" does not appear in {src.id} ({src.span})',
                           'if the code reaches it under another spelling, set "via" to the exact text '
                           "(such as \"new Catalog(\" or \"this.repo\"); otherwise remove the arrow")
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
                pattern = word(tok)
                idx = next((i for i, text in enumerate(a.lines) if pattern.search(text)), -1)
                if idx >= 0:
                    self.report.hints.append(
                        f"{a.id} mentions {tok} at {a.file}:{a.start + idx} with no arrow to {b.id}; "
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
                pattern = word(name)
                idx = next((i for i, text in enumerate(b.lines) if pattern.search(text)), -1)
                if idx >= 0:
                    hinted.add(name)
                    self.report.hints.append(
                        f"{b.id} mentions {name} at {b.file}:{b.start + idx}, declared at {path}:{n} but not a block; "
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
                                        "consider leaving out exception classes and small helpers, or splitting the flow")

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
