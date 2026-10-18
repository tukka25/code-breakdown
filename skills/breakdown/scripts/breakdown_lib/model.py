"""The spec an agent writes: blocks of code by line range, and the arrows between them."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

KINDS = ("file", "endpoint", "pr")
ROLES = ("code", "type", "container")
EDGE_KINDS = ("calls", "uses")
SIDES = ("head", "base")

TOP_KEYS = {"kind", "title", "entry", "blocks", "edges", "pr", "base", "head"}
BLOCK_KEYS = {"id", "file", "start", "end", "role", "parent", "name", "label", "side", "no_bracket_check"}
EDGE_KEYS = {"from", "to", "kind", "via"}


def err(at: str, problem: str, fix: str = "") -> Dict[str, str]:
    return {"at": at, "problem": problem, "fix": fix}


@dataclass
class Block:
    id: str
    file: str
    start: int
    end: int
    role: str = "code"
    parent: Optional[str] = None
    name: Optional[str] = None
    label: Optional[str] = None
    side: str = "head"
    no_bracket_check: bool = False
    index: int = 0
    # Filled in by the check: the verbatim lines from start to end, and which of them names the block.
    lines: List[str] = field(default_factory=list)
    def_line: int = 0
    # Filled in for a change: the lines to draw, as (text, mark) with mark "", "add" or "del",
    # and where each of `lines` sits among them. Removed lines are cut from the base version.
    rows: Optional[List[Tuple[str, str]]] = None
    index_map: Optional[List[int]] = None

    @property
    def shown(self) -> List[str]:
        return [text for text, _ in self.rows] if self.rows is not None else self.lines

    def shown_index(self, i: int) -> int:
        return self.index_map[i] if self.index_map is not None and 0 <= i < len(self.index_map) else i

    @property
    def token(self) -> str:
        """The identifier that names this block in the code."""
        return self.name or self.id.split(".")[-1]

    @property
    def where(self) -> str:
        return f"blocks[{self.index}] {self.id}"

    @property
    def span(self) -> str:
        return f"{self.file}:{self.start}-{self.end}"


@dataclass
class Edge:
    src: str
    dst: str
    kind: Optional[str] = None
    via: Optional[str] = None
    index: int = 0
    # Filled in by the check: index into the source block's lines where the evidence first appears.
    line: int = -1

    @property
    def where(self) -> str:
        return f"edges[{self.index}] {self.src} -> {self.dst}"

    @property
    def evidence(self) -> str:
        return self.via or ""


@dataclass
class Spec:
    kind: str
    title: str
    entry: List[str]
    blocks: List[Block]
    edges: List[Edge]
    pr: Optional[int] = None
    base: Optional[str] = None
    head: Optional[str] = None

    def __post_init__(self) -> None:
        self.by_id = {b.id: b for b in self.blocks}

    def block(self, block_id: str) -> Block:
        return self.by_id[block_id]

    def children(self, block_id: str) -> List[Block]:
        return [b for b in self.blocks if b.parent == block_id]

    def node_of(self, block_id: str) -> str:
        """The top-level box a block is drawn in: its container, or itself."""
        b = self.by_id[block_id]
        return b.parent or b.id


def _text(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _line_number(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _pr_number(value: Any) -> Tuple[Optional[int], bool]:
    """Accept 123, "123" or "#123". Returns (number, ok)."""
    if value is None:
        return None, True
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value, True
    if isinstance(value, str) and value.lstrip("#").isdigit():
        return int(value.lstrip("#")), True
    return None, False


def load_spec(data: Any) -> Tuple[Optional[Spec], List[Dict[str, str]], List[str]]:
    """Validate the shape of a spec. Returns (spec or None, errors, warnings)."""
    errors: List[Dict[str, str]] = []
    warnings: List[str] = []
    if not isinstance(data, dict):
        return None, [err("spec", "the spec is not a JSON object",
                          'write an object with "kind", "title", "entry", "blocks" and "edges"')], []

    for key in sorted(set(data) - TOP_KEYS):
        warnings.append(f'unknown field "{key}" is ignored')

    kind = data.get("kind")
    if kind not in KINDS:
        errors.append(err("kind", f"kind is {kind!r}", f"use one of: {', '.join(KINDS)}"))
    title = _text(data.get("title"))
    if title is None:
        errors.append(err("title", "title is missing", 'name the target, for example "POST /orders" or "src/loans.ts"'))

    entry = data.get("entry")
    if isinstance(entry, str):
        entry = [entry]
    if not isinstance(entry, list) or not entry or not all(_text(e) for e in entry):
        errors.append(err("entry", "entry must list at least one block id",
                          'for example "entry": ["create_order"]'))
        entry = []
    entry = [e.strip() for e in entry if isinstance(e, str)]

    blocks: List[Block] = []
    raw_blocks = data.get("blocks")
    if not isinstance(raw_blocks, list) or not raw_blocks:
        errors.append(err("blocks", "blocks must be a non-empty list",
                          'each block is {"id", "file", "start", "end"}'))
        raw_blocks = []
    seen = set()
    for i, raw in enumerate(raw_blocks):
        at = f"blocks[{i}]"
        if not isinstance(raw, dict):
            errors.append(err(at, "a block must be an object", '{"id": "...", "file": "...", "start": 1, "end": 9}'))
            continue
        for key in sorted(set(raw) - BLOCK_KEYS):
            warnings.append(f'{at}: unknown field "{key}" is ignored')
        bid = _text(raw.get("id"))
        if bid is None or any(ch.isspace() for ch in bid):
            errors.append(err(at, f"id {raw.get('id')!r} is missing or contains spaces",
                              "use the function or type name, such as create_order or Catalog.find"))
            continue
        at = f"blocks[{i}] {bid}"
        if bid in seen:
            errors.append(err(at, f'duplicate id "{bid}"', "give every block its own id"))
            continue
        seen.add(bid)
        path = _text(raw.get("file"))
        if path is None:
            errors.append(err(at, "file is missing", "give the path relative to the repository root"))
            continue
        path = path.replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        start, end = _line_number(raw.get("start")), _line_number(raw.get("end"))
        if start is None or end is None:
            errors.append(err(at, "start and end must be line numbers of 1 or more",
                              "use the 1-based line numbers you see in the file"))
            continue
        if start > end:
            errors.append(err(at, f"start {start} is after end {end}", "swap them"))
            continue
        role = raw.get("role", "code")
        if role not in ROLES:
            errors.append(err(at, f"role is {role!r}", f"use one of: {', '.join(ROLES)}"))
            continue
        side = raw.get("side", "head")
        if side not in SIDES:
            errors.append(err(at, f"side is {side!r}", f"use one of: {', '.join(SIDES)}"))
            continue
        label = raw.get("label")
        if label is not None and _text(label) is None:
            errors.append(err(at, "label is empty", "remove it or name a role, such as Entry point"))
            continue
        blocks.append(Block(
            id=bid, file=path, start=start, end=end, role=role,
            parent=_text(raw.get("parent")), name=_text(raw.get("name")),
            label=_text(label), side=side, no_bracket_check=bool(raw.get("no_bracket_check", False)),
            index=i,
        ))

    ids = {b.id for b in blocks}
    edges: List[Edge] = []
    raw_edges = data.get("edges", [])
    if not isinstance(raw_edges, list):
        errors.append(err("edges", "edges must be a list", '[{"from": "a", "to": "b"}]'))
        raw_edges = []
    for j, raw in enumerate(raw_edges):
        at = f"edges[{j}]"
        if not isinstance(raw, dict):
            errors.append(err(at, "an arrow must be an object", '{"from": "a", "to": "b"}'))
            continue
        for key in sorted(set(raw) - EDGE_KEYS):
            warnings.append(f'{at}: unknown field "{key}" is ignored')
        src, dst = _text(raw.get("from")), _text(raw.get("to"))
        at = f"edges[{j}] {src} -> {dst}"
        missing = [x for x in (src, dst) if x is None or (x not in ids and x not in seen)]
        if missing:
            errors.append(err(at, f"unknown block id {', '.join(repr(m) for m in missing)}",
                              "use ids from blocks, or add the missing block"))
            continue
        kind_ = raw.get("kind")
        if kind_ is not None and kind_ not in EDGE_KINDS:
            errors.append(err(at, f"kind is {kind_!r}", f"use one of: {', '.join(EDGE_KINDS)}, or leave it out"))
            continue
        via = raw.get("via")
        if via is not None and _text(via) is None:
            errors.append(err(at, "via is empty", "remove it, or give the text that appears in the source block"))
            continue
        edges.append(Edge(src=src, dst=dst, kind=kind_, via=_text(via), index=j))

    for e in entry:
        if e not in seen:
            errors.append(err("entry", f'entry "{e}" is not a block id', "use the id of the block where the flow starts"))

    pr, pr_ok = _pr_number(data.get("pr"))
    if not pr_ok:
        errors.append(err("pr", f"pr is {data.get('pr')!r}", "use the pull request number, such as 123"))
    base, head = data.get("base"), data.get("head")
    for name, value in (("base", base), ("head", head)):
        if value is not None and _text(value) is None:
            errors.append(err(name, f"{name} is empty", "give a git ref such as origin/main or a commit sha, or remove it"))

    if errors or kind not in KINDS or title is None:
        return None, errors, warnings
    return Spec(kind=kind, title=title, entry=entry, blocks=blocks, edges=edges,
                pr=pr, base=_text(base), head=_text(head)), [], warnings
