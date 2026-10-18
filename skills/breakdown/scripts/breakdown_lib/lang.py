"""What a line is, per language family: comment, decorator, declaration; and where strings and comments sit.

The checks and the change markers share these, so they agree about where a declaration starts and ends.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath
from typing import Any, List, Optional

PYTHON = {".py", ".pyi", ".pyw"}
HASH = {".rb", ".sh", ".bash", ".zsh", ".pl", ".pm", ".r", ".ex", ".exs", ".cr", ".nim", ".jl", ".coffee"}
C_LIKE = {
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".java", ".kt", ".kts", ".scala",
    ".go", ".rs", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".cs", ".swift", ".dart",
    ".groovy", ".m", ".mm", ".zig", ".v", ".sol",
}
PHP = {".php"}
SQL = {".sql"}

IDENT = re.compile(r"^[A-Za-z_$][\w$]*$")
JSDOC_LINE = re.compile(r"^\*(\s|/|$)")
CSHARP_ATTRIBUTE = re.compile(r"^\[[A-Za-z_][\w.]*(\(.*)?\]?\s*$")

# Declarations, to find blocks an agent left out and to see where one declaration ends and the next begins.
DECLARATION = {
    "python": re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)"),
    "c": re.compile(
        r"^\s*(?:export\s+)?(?:default\s+)?"
        r"(?:(?:public|private|protected|internal|static|abstract|final|async|sealed|open|pub(?:\([^)]*\))?)\s+)*"
        r"(?:function\*?|class|interface|type|enum|struct|trait|fn|func|record)\s+(?:\([^)]*\)\s*)?([A-Za-z_$][\w$]*)"
    ),
    "hash": re.compile(r"^\s*(?:def|class|module)\s+(?:self\.)?([A-Za-z_]\w*)"),
}
DECLARATION["php"] = re.compile(
    r"^\s*(?:(?:public|private|protected|static|abstract|final)\s+)*(?:function|class|interface|trait|enum)\s+([A-Za-z_]\w*)"
)
ARROW_FUNCTION = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s+)?"
    r"(?:function\b|\([^)]*\)\s*(?::[^=]+)?=>|[A-Za-z_$][\w$]*\s*=>)"
)
DEF_HINT = re.compile(
    r"\b(def|class|function|func|fn|interface|type|struct|enum|trait|impl|module|record|object|"
    r"let|const|var|val|async|export|public|private|protected|internal|static|override|sub)\b"
)


def family(path: str) -> Optional[str]:
    ext = PurePosixPath(path).suffix.lower()
    for name, exts in (("python", PYTHON), ("c", C_LIKE), ("php", PHP), ("hash", HASH), ("sql", SQL)):
        if ext in exts:
            return name
    return None


def word(text: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![\w$])" + re.escape(text) + r"(?![\w$])")


def indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def display_width(text: str) -> int:
    """Columns a monospace font needs: wide and full-width characters take two."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def note_kind(line: str, fam: Optional[str]) -> Optional[str]:
    """"comment" or "decorator" for lines that belong to the declaration below them, else None."""
    s = line.strip()
    if not s:
        return None
    if s.startswith("#!"):
        return None  # a shebang belongs to the file, not to the first declaration
    if fam in ("c", "php"):
        if s.startswith(("//", "/*", "*/")) or JSDOC_LINE.match(s):
            return "comment"
        if fam == "php" and s.startswith("#") and not s.startswith("#["):
            return "comment"
        if s.startswith(("@", "#[")) or (fam == "c" and CSHARP_ATTRIBUTE.match(s)):
            return "decorator"
        return None
    if fam in ("python", "hash"):
        if s.startswith("#"):
            return "comment"
        return "decorator" if s.startswith("@") else None
    if fam == "sql":
        return "comment" if s.startswith(("--", "/*", "*/")) or JSDOC_LINE.match(s) else None
    if s.startswith(("#", "//", "--", "/*")):
        return "comment"
    return "decorator" if s.startswith("@") else None


class Scanner:
    """Walk code line by line, tracking bracket depth and skipping strings and comments.

    With keep_strings set, feed() also returns the line with comments blanked out; without it,
    strings are blanked too. Blanking keeps positions, so a match still points at the right column.
    """

    def __init__(self, fam: Optional[str], rust: bool = False, keep_strings: bool = False):
        self.fam = fam
        self.rust = rust
        self.keep_strings = keep_strings
        self.depth = 0
        self.min_depth = 0
        self.opened = False
        self.mode: Any = None  # None, "block" for /* */, or ("str", delimiter)

    @property
    def inside(self) -> bool:
        return self.depth > 0 or self.mode is not None

    def feed(self, line: str) -> str:
        out = list(line)
        i, n = 0, len(line)

        def blank(a: int, b: int, string: bool) -> None:
            if string and self.keep_strings:
                return
            for k in range(a, min(b, n)):
                out[k] = " "

        while i < n:
            c = line[i]
            if self.mode == "block":
                j = line.find("*/", i)
                end = n if j < 0 else j + 2
                blank(i, end, False)
                i = end
                if j >= 0:
                    self.mode = None
                continue
            if isinstance(self.mode, tuple):
                delim = self.mode[1]
                j = i
                closed = False
                while j < n:
                    if line[j] == "\\":
                        j += 2
                        continue
                    if line.startswith(delim, j):
                        closed = True
                        break
                    j += 1
                blank(i, j, True)
                if closed:
                    i = j + len(delim)
                    self.mode = None
                else:
                    i = n
                continue
            if c == "#" and (self.fam in ("python", "hash") or (self.fam == "php" and not line.startswith("#[", i))):
                blank(i, n, False)
                break
            if self.fam in ("c", "php", "sql") and line.startswith("/*", i):
                self.mode = "block"
                blank(i, i + 2, False)
                i += 2
                continue
            if self.fam in ("c", "php") and line.startswith("//", i):
                blank(i, n, False)
                break
            if self.fam == "sql" and line.startswith("--", i):
                blank(i, n, False)
                break
            if c in "\"'`":
                if self.fam in ("python", "c") and line.startswith(c * 3, i) and c != "`":
                    self.mode, i = ("str", c * 3), i + 3
                    continue
                if c == "`" and self.fam != "c":
                    i += 1
                    continue
                if c == "'" and self.rust:
                    m = re.match(r"'(\\.[^']*|[^\\'])'", line[i:])
                    if m:
                        blank(i + 1, i + len(m.group(0)) - 1, True)
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
        return "".join(out)


def masked(lines: List[str], fam: Optional[str], keep_strings: bool, rust: bool = False) -> List[str]:
    """The lines with comments blanked, and strings too unless keep_strings."""
    sc = Scanner(fam, rust, keep_strings)
    return [sc.feed(line) for line in lines]


def skip_decorator(lines: List[str], i: int, fam: Optional[str]) -> int:
    """Index of the first line after the decorator that starts at lines[i], following its brackets."""
    sc = Scanner(fam)
    k = i
    while k < len(lines):
        sc.feed(lines[k])
        k += 1
        if not sc.inside:
            break
    return k


def looks_declared(line: str, token: str, fam: Optional[str]) -> bool:
    """Whether a line plausibly declares token, rather than only using it."""
    pattern = DECLARATION.get(fam or "")
    m = pattern.match(line) if pattern else None
    if m and m.group(1) == token:
        return True
    if fam == "c" and (m := ARROW_FUNCTION.match(line)) and m.group(1) == token:  # noqa: F841 (3.9 has :=)
        return True
    stripped = line.lstrip()
    if re.match(re.escape(token) + r"\s*(\(|<|=|:|\{)", stripped):
        return True  # a method or field written by name, an assignment, a type alias
    if fam in ("c", "php"):
        # A return type before the name: `void Run(`, `public Order create(`, `std::string name(`.
        m = re.search(r"([\w$<>\[\],.?*&:]+)\s+" + re.escape(token) + r"\s*\(", line)
        if m and m.group(1).split("<")[0].split("::")[-1] not in CALL_PREFIXES:
            return True
    before = line.split(token, 1)[0]
    return bool(DEF_HINT.search(before))


CALL_PREFIXES = {"return", "await", "new", "throw", "yield", "else", "case", "typeof", "delete", "in", "of",
                 "not", "and", "or", "do", "go", "defer", "echo", "print"}
