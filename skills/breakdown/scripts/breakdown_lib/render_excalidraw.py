"""The same breakdown as an Excalidraw drawing, placed with the layout computed for the canvas.

Each box is a rectangle grouped with its code, caption and label, so it drags as one piece.
Arrows are bound to the rectangles they join. Second uses of a type are drawn faint, because
an Excalidraw file has no click-to-trace.
"""

from __future__ import annotations

import time
import zlib
from typing import Any, Dict, List, Optional, Tuple

STROKE = {"code": "#1971c2", "type": "#6741d9", "container": "#9c36b5"}
EDGE_STROKE = {"calls": "#1971c2", "uses": "#6741d9"}
STATUS_FILL = {"new": "#ebfbee", "changed": "#ebfbee", "deleted": "#fff5f5"}
INK = "#1e1e1e"
MUTED = "#868e96"
FONT_CODE = 8   # Comic Shanns, Excalidraw's code font
FONT_HAND = 5   # Excalifont
CODE_SIZE = 11
CLAIM_CHARS = 1200


def _seed(key: str) -> int:
    return zlib.crc32(key.encode("utf-8")) % 2_000_000_000 + 1


class Drawing:
    def __init__(self) -> None:
        self.elements: List[Dict[str, Any]] = []
        self.now = int(time.time() * 1000)

    def base(self, eid: str, kind: str, x: float, y: float, w: float, h: float, **extra: Any) -> Dict[str, Any]:
        el: Dict[str, Any] = {
            "id": eid, "type": kind, "x": round(x, 2), "y": round(y, 2), "width": round(w, 2), "height": round(h, 2),
            "angle": 0, "strokeColor": INK, "backgroundColor": "transparent", "fillStyle": "solid",
            "strokeWidth": 1, "strokeStyle": "solid", "roughness": 1, "opacity": 100, "groupIds": [],
            "frameId": None, "roundness": None, "seed": _seed(eid), "version": 1, "versionNonce": _seed(eid + "#"),
            "isDeleted": False, "boundElements": [], "updated": self.now, "link": None, "locked": False,
        }
        el.update(extra)
        self.elements.append(el)
        return el

    def text(self, eid: str, x: float, y: float, text: str, size: float, family: int,
             color: str = INK, line_px: Optional[float] = None, char_em: float = 0.6, **extra: Any) -> Dict[str, Any]:
        lines = text.split("\n")
        line_height = (line_px / size) if line_px else 1.25
        w = max((len(l) for l in lines), default=1) * size * char_em
        h = len(lines) * size * line_height
        return self.base(eid, "text", x, y, w, h, strokeColor=color, text=text, originalText=text,
                         fontSize=size, fontFamily=family, textAlign="left", verticalAlign="top",
                         containerId=None, autoResize=True, lineHeight=round(line_height, 4), **extra)


def _anchors(edge: Dict[str, Any], boxes: Dict[str, List[float]], blocks: Dict[str, Dict[str, Any]],
             lh: float, cap: float) -> Tuple[str, float, float, float, float]:
    s, t = boxes[edge["from"]], boxes[edge["to"]]
    sy = s[1] + cap + (edge["line"] + 0.5) * lh
    ty = t[1] + cap + (blocks[edge["to"]]["def"] + 0.5) * lh
    s_left, s_right, t_left, t_right = s[0], s[0] + s[2], t[0], t[0] + t[2]
    if t_left >= s_right + 12:
        return "rl", s_right + 6, sy, t_left - 7, ty
    if t_right <= s_left - 12:
        return "lr", s_left - 6, sy, t_right + 7, ty
    return "ll", s_left - 6, sy, t_left - 7, ty


def _curve(mode: str, sx: float, sy: float, tx: float, ty: float) -> List[Tuple[float, float]]:
    """The canvas's cubic Bezier for this arrow, sampled at five points."""
    if mode == "rl":
        dx = max(44.0, (tx - sx) * 0.5)
        c1, c2 = (sx + dx, sy), (tx - dx, ty)
    elif mode == "lr":
        dx = max(44.0, (sx - tx) * 0.5)
        c1, c2 = (sx - dx, sy), (tx + dx, ty)
    else:
        lx = min(sx, tx) - (26 + min(64.0, abs(ty - sy) * 0.12))
        c1, c2 = (lx, sy), (lx, ty)
    out = []
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        u = 1 - t
        x = u ** 3 * sx + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * tx
        y = u ** 3 * sy + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * ty
        out.append((x, y))
    return out


def render_excalidraw(payload: Dict[str, Any], mode: str = "column") -> Dict[str, Any]:
    lay = payload["layouts"][mode]
    boxes: Dict[str, List[float]] = lay["boxes"]
    blocks = {b["id"]: b for b in payload["blocks"]}
    lh, cap = payload["consts"]["LH"], payload["consts"]["CAP"]
    number = {bid: i + 1 for i, bid in enumerate(lay["order"])}
    d = Drawing()
    rect_of: Dict[str, Dict[str, Any]] = {}

    meta = payload["meta"]
    x0, y0 = lay["bounds"][0], lay["bounds"][1]
    kind = {"file": "File", "endpoint": "Endpoint", "pr": "Pull request"}.get(meta["kind"], meta["kind"])
    d.text("title", x0, y0 - 70, f"{kind}: {meta['title']}", 26, FONT_HAND)
    claim = meta.get("claim")
    if claim:
        body = (claim.get("body") or "").strip() or "This pull request has no description."
        if len(body) > CLAIM_CHARS:
            body = body[:CLAIM_CHARS] + "\n(first 1200 characters; the canvas has the full text)"
        source = f"PR #{claim.get('number')}" if claim.get("number") else "commit messages"
        d.text("claim", x0, y0 - 30, f"Author's claim ({source}): {claim.get('title', '')}\n\n{body}",
               13, FONT_HAND, color=MUTED)

    for text, hx, hy in lay["heads"]:
        d.text(f"head-{text}", hx, hy, text, 28, FONT_HAND)

    ordered = [b for b in payload["blocks"] if b["role"] == "container"] + \
              [b for b in payload["blocks"] if b["role"] != "container"]
    for b in ordered:
        x, y, w, h = boxes[b["id"]]
        gid = f"g-{b['id']}"
        groups = [gid] + ([f"g-{b['parent']}"] if b.get("parent") else [])
        status = b.get("status")
        rect = d.base(f"r-{b['id']}", "rectangle", x, y, w, h, strokeColor=STROKE[b["role"]], groupIds=groups,
                      backgroundColor=STATUS_FILL.get(status, "transparent"),
                      opacity=60 if status == "same" else 100, roughness=1, strokeWidth=1 if b["role"] == "container" else 2)
        rect_of[b["id"]] = rect
        caption = f"{b['file']}:{b['start']}-{b['end']}"
        if status and status != "same":
            caption += f"  [{status}]"
        d.text(f"c-{b['id']}", x + 12, y + 5, caption, 9, FONT_CODE, color=MUTED, groupIds=groups)
        if b["id"] in number:
            d.text(f"n-{b['id']}", x + w - 22, y + 3, str(number[b["id"]]), 14, FONT_HAND,
                   color=STROKE[b["role"]], groupIds=groups)
        marks = b.get("marks") or {}
        if marks.get("+") or marks.get("-"):
            # No per-line colour in Excalidraw text, so changed boxes read like a diff.
            plus, minus = set(marks.get("+", [])), set(marks.get("-", []))
            code = "\n".join(("+ " if i in plus else "- " if i in minus else "  ") + line
                             for i, line in enumerate(b["lines"]))
            d.text(f"t-{b['id']}", x + 4, y + cap, code, CODE_SIZE, FONT_CODE, line_px=lh, groupIds=groups)
        else:
            d.text(f"t-{b['id']}", x + 12, y + cap, "\n".join(b["lines"]), CODE_SIZE, FONT_CODE,
                   line_px=lh, groupIds=groups)
        if b.get("tail"):
            d.text(f"e-{b['id']}", x + 12, y + h - lh - 6, b["tail"], CODE_SIZE, FONT_CODE, line_px=lh, groupIds=groups)
        if b.get("label"):
            d.text(f"l-{b['id']}", x + 1, y - 26, b["label"], 17, FONT_HAND, groupIds=groups)

    for i, e in enumerate(payload["edges"]):
        mode_, sx, sy, tx, ty = _anchors(e, boxes, blocks, lh, cap)
        pts = _curve(mode_, sx, sy, tx, ty)
        rel = [[round(px - sx, 2), round(py - sy, 2)] for px, py in pts]
        xs, ys = [p[0] for p in rel], [p[1] for p in rel]
        aid = f"a-{i}-{e['from']}-{e['to']}"
        arrow = d.base(aid, "arrow", sx, sy, max(xs) - min(xs), max(ys) - min(ys),
                       strokeColor=EDGE_STROKE.get(e["kind"], INK), strokeWidth=2 if e["kind"] == "calls" else 1,
                       strokeStyle="solid" if e["kind"] == "calls" else "dashed",
                       opacity=100 if e["primary"] else 35, roundness={"type": 2}, points=rel,
                       lastCommittedPoint=None, startArrowhead=None, endArrowhead="arrow", elbowed=False,
                       startBinding={"elementId": rect_of[e["from"]]["id"], "focus": 0, "gap": 6},
                       endBinding={"elementId": rect_of[e["to"]]["id"], "focus": 0, "gap": 7})
        rect_of[e["from"]]["boundElements"].append({"id": arrow["id"], "type": "arrow"})
        rect_of[e["to"]]["boundElements"].append({"id": arrow["id"], "type": "arrow"})

    return {
        "type": "excalidraw",
        "version": 2,
        "source": payload.get("generator", "code-breakdown"),
        "elements": d.elements,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
        "files": {},
    }
