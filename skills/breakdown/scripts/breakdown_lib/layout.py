"""Place every block on the canvas, in the two layouts.

column ("B", the default): columns by call depth, then every type in a final Data column.
beside ("A"): the same code columns, with each type under the first code that mentions it.

Both layouts are computed here so the HTML canvas and the Excalidraw file share coordinates.
The canvas draws code in 11px JetBrains Mono, whose advance is 0.6em: 6.6px per character.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .model import Block, Spec
from .order import FREE, Order

CHAR_W = 6.6
LH = 16          # line height of code
CAP = 22         # caption row (file:lines and reading number) at the top of a box
PADX = 12
PADB = 10
MINW = 200
LABEL = 30       # band above a box for its label
INDENT = 26      # a component type sits this far right of the type that owns it
COL_GAP = 124
DATA_GAP = 180
GAP_GROUP = 66   # between unrelated boxes in a column
GAP_IN = 46      # between a box and the types it owns
X0 = 140
Y0 = 150
CPAD = 22        # container side padding
CHILD_COL_GAP = 104
TAIL = 26        # room for a container's closing line
TAB = 4
CLOSERS = {"}", "};", "})", "end", "end;", "};"}


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    def as_list(self) -> List[float]:
        return [round(self.x, 1), round(self.y, 1), round(self.w, 1), round(self.h, 1)]


@dataclass
class Layout:
    mode: str
    boxes: Dict[str, Box]
    heads: List[Tuple[str, float, float]]
    bounds: Tuple[float, float, float, float]


def display(line: str) -> str:
    return line.expandtabs(TAB)


def text_width(lines: List[str]) -> float:
    return max((len(display(l)) for l in lines), default=0) * CHAR_W


def block_size(lines: List[str]) -> Tuple[float, float]:
    w = max(MINW, math.ceil(text_width(lines) + PADX * 2 + 4))
    return float(w), float(CAP + len(lines) * LH + PADB)


def container_parts(spec: Spec, cid: str) -> Tuple[List[str], Optional[str]]:
    """The lines a container shows itself: its head above the first method, and a lone closing line."""
    c = spec.block(cid)
    first = min(child.start for child in spec.children(cid))
    head = c.lines[: max(1, first - c.start)]
    while len(head) > 1 and not head[-1].strip():
        head = head[:-1]
    last = c.lines[-1].strip()
    return head, (c.lines[-1] if last in CLOSERS else None)


class Sizer:
    """Sizes of every drawn box; containers are sized from the methods inside them."""

    def __init__(self, spec: Spec, order: Order):
        self.spec = spec
        self.order = order
        self.size: Dict[str, Tuple[float, float]] = {}
        self.inner: Dict[str, Dict[str, Tuple[float, float]]] = {}
        for b in spec.blocks:
            if b.role != "container":
                self.size[b.id] = block_size(b.shown)
        for b in spec.blocks:
            if b.role == "container":
                self._container(b)

    def _container(self, c: Block) -> None:
        members = self.order.members.get(c.id) or [k.id for k in self.spec.children(c.id)]
        cols: Dict[int, List[str]] = {}
        for m in members:
            cols.setdefault(self.order.child_depth.get(m, 0), []).append(m)
        head, tail = container_parts(self.spec, c.id)
        head_h = CAP + len(head) * LH
        x = CPAD
        inner_h = 0.0
        rel: Dict[str, Tuple[float, float]] = {}
        for d in sorted(cols):
            y = 0.0
            for i, m in enumerate(cols[d]):
                if i:
                    y += GAP_IN
                rel[m] = (x, head_h + LABEL + y)
                y += self.size[m][1]
            inner_h = max(inner_h, y)
            x += max(self.size[m][0] for m in cols[d]) + CHILD_COL_GAP
        inner_w = x - CHILD_COL_GAP + CPAD
        w = max(MINW, math.ceil(text_width(head + ([tail] if tail else [])) + PADX * 2 + 4), inner_w)
        h = head_h + LABEL + inner_h + (TAIL if tail else 18)
        self.size[c.id] = (float(w), float(h))
        self.inner[c.id] = rel


def _expand(spec: Spec, sizer: Sizer, pos: Dict[str, Tuple[float, float]]) -> Dict[str, Box]:
    boxes: Dict[str, Box] = {}
    for bid, (x, y) in pos.items():
        w, h = sizer.size[bid]
        boxes[bid] = Box(x, y, w, h)
        for child, (rx, ry) in sizer.inner.get(bid, {}).items():
            cw, ch = sizer.size[child]
            boxes[child] = Box(x + rx, y + ry, cw, ch)
    return boxes


def _columns(order: Order) -> List[List[str]]:
    cols: List[List[str]] = []
    for node in order.code_nodes:
        d = order.depth[node]
        while len(cols) <= d:
            cols.append([])
        cols[d].append(node)
    return cols


def _data_column(order: Order, sizer: Sizer, types: List[str], x: float, code_bottom: float,
                 pos: Dict[str, Tuple[float, float]]) -> None:
    # Wrap into a second Data column only when one column would be much taller than the code beside it.
    limit = max((code_bottom - Y0) * 1.6, 1400.0)
    y, colw, first = float(Y0), 0.0, True
    for t in types:
        d = order.tdepth[t]
        w, h = sizer.size[t]
        gap = 0.0 if first else float(GAP_GROUP if d == 1 else GAP_IN)
        if not first and d == 1 and (y + gap + h - Y0) > limit:
            x += colw + COL_GAP
            y, colw, gap = float(Y0), 0.0, 0.0
        pos[t] = (x + (d - 1) * INDENT, y + gap)
        y = pos[t][1] + h
        colw = max(colw, (d - 1) * INDENT + w)
        first = False


def _bounds(boxes: Dict[str, Box], heads: List[Tuple[str, float, float]]) -> Tuple[float, float, float, float]:
    xs = [b.x for b in boxes.values()] + [hx for _, hx, _ in heads]
    ys = [b.y - LABEL for b in boxes.values()] + [hy for _, _, hy in heads]
    return (min(xs) - 110, min(ys) - 30,
            max(b.x + b.w for b in boxes.values()) + 50, max(b.y + b.h for b in boxes.values()) + 50)


def layout(spec: Spec, order: Order, mode: str) -> Layout:
    sizer = Sizer(spec, order)
    pos: Dict[str, Tuple[float, float]] = {}
    heads: List[Tuple[str, float, float]] = []
    x = float(X0)
    for nodes in _columns(order):
        y = float(Y0)
        colw = 0.0
        for n in nodes:
            parent = order.tree_parent.get(n)
            if parent is not None:
                y = max(y, pos[parent][1])
            pos[n] = (x, y)
            w, h = sizer.size[n]
            y += h
            colw = max(colw, w)
            if mode == "beside":
                for t in order.flat(n):
                    tw, th = sizer.size[t]
                    y += GAP_IN
                    pos[t] = (x + order.tdepth[t] * INDENT, y)
                    y += th
                    colw = max(colw, order.tdepth[t] * INDENT + tw)
            y += GAP_GROUP
        x += colw + COL_GAP

    if mode == "beside":
        data_types = order.flat(FREE)
    else:
        data_types = [t for n in order.code_nodes for t in order.flat(n)] + order.flat(FREE)
    if data_types:
        x += DATA_GAP - COL_GAP
        code_bottom = max((pos[n][1] + sizer.size[n][1] for n in order.code_nodes), default=float(Y0))
        heads.append(("Data", x, Y0 - 76))
        _data_column(order, sizer, data_types, x, code_bottom, pos)

    boxes = _expand(spec, sizer, pos)
    return Layout(mode=mode, boxes=boxes, heads=heads, bounds=_bounds(boxes, heads))
