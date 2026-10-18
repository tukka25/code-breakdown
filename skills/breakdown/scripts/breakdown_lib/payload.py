"""Everything the renderers need, as one JSON-ready dict. It is also saved as tree.json."""

from __future__ import annotations

import datetime as dt
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

from . import __version__
from .check import Report
from .layout import CAP, CHAR_W, LH, Layout, container_parts, display
from .model import Spec
from .order import Order

LANG_BY_EXT = {
    ".py": "python", ".pyi": "python",
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js", ".ts": "js", ".tsx": "js", ".mts": "js", ".cts": "js",
    ".go": "go", ".java": "java", ".kt": "java", ".kts": "java", ".scala": "java", ".groovy": "java",
    ".cs": "csharp", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".c": "c", ".h": "c", ".cc": "c", ".cpp": "c", ".cxx": "c", ".hpp": "c", ".hh": "c", ".m": "c", ".mm": "c",
    ".swift": "swift", ".dart": "js", ".sql": "sql",
}


def lang_of(path: str) -> str:
    return LANG_BY_EXT.get(PurePosixPath(path).suffix.lower(), "plain")


def build_payload(spec: Spec, order: Order, layouts: Dict[str, Layout], *, root: Path, default: str,
                  report: Report, markers: Optional[Dict[str, Dict[str, Any]]] = None,
                  claim: Optional[Dict[str, Any]] = None, generated: Optional[str] = None) -> Dict[str, Any]:
    markers = markers or {}
    blocks: List[Dict[str, Any]] = []
    head_len: Dict[str, int] = {}
    for b in spec.blocks:
        item: Dict[str, Any] = {
            "id": b.id, "file": b.file, "start": b.start, "end": b.end, "role": b.role,
            "side": b.side, "def": b.shown_index(b.def_line), "lang": lang_of(b.file),
        }
        if b.label:
            item["label"] = b.label
        if b.parent:
            item["parent"] = b.parent
        if b.role == "container":
            head, tail = container_parts(spec, b.id)
            head_len[b.id] = len(head)
            item["lines"] = [display(line) for line in head]
            item["tail"] = display(tail) if tail else None
            if b.id in markers:
                item["marks"] = {"+": [i for i in markers[b.id].get("added", []) if i < len(head)], "-": []}
        elif b.rows is not None:
            item["lines"] = [display(text) for text, _ in b.rows]
            item["marks"] = {"+": [i for i, (_, m) in enumerate(b.rows) if m == "add"],
                             "-": [i for i, (_, m) in enumerate(b.rows) if m == "del"]}
        else:
            item["lines"] = [display(line) for line in b.lines]
        mark = markers.get(b.id)
        if mark:
            item["status"] = mark["status"]
        blocks.append(item)

    edges: List[Dict[str, Any]] = []
    for e in spec.edges:
        src = spec.block(e.src)
        line = e.line
        if src.role == "container" and line >= head_len.get(src.id, 1):
            line = src.def_line
        dst_role = spec.block(e.dst).role
        primary = dst_role != "type" or order.owner.get(e.dst) in (spec.node_of(e.src), e.src)
        # e.line already counts the shown rows, removed lines included.
        if src.rows is not None:
            changed = {i for i, (_, mark) in enumerate(src.rows) if mark}
        else:
            changed = set(markers.get(e.src, {}).get("added", []))
        if e.line in changed:
            primary = True  # an arrow that leaves a changed line is part of the change, so always show it
        edges.append({"from": e.src, "to": e.dst, "kind": e.kind, "line": line, "primary": bool(primary)})

    counts: Dict[str, int] = {
        "blocks": len(spec.blocks), "arrows": len(spec.edges), "files": len({b.file for b in spec.blocks}),
    }
    if markers:
        statuses = [m["status"] for m in markers.values()]
        counts.update(changed=statuses.count("changed"), added=statuses.count("new"), deleted=statuses.count("deleted"))

    meta: Dict[str, Any] = {
        "title": spec.title, "kind": spec.kind, "default": default, "root": str(root),
        "generated": generated or dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "counts": counts, "unreached": order.unreached,
    }
    if spec.base:
        meta["base"] = spec.base
        meta["head"] = spec.head
    if claim:
        meta["claim"] = claim

    return {
        "version": 1,
        "generator": f"code-breakdown {__version__}",
        "meta": meta,
        "consts": {"LH": LH, "CAP": CAP, "CHAR_W": CHAR_W},
        "blocks": blocks,
        "edges": edges,
        "layouts": {
            mode: {
                "boxes": {bid: box.as_list() for bid, box in lay.boxes.items()},
                "heads": [[text, round(x, 1), round(y, 1)] for text, x, y in lay.heads],
                "bounds": [round(v, 1) for v in lay.bounds],
                "order": order.reading[mode],
            }
            for mode, lay in layouts.items()
        },
        "check": report.as_dict(),
    }
