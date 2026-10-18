"""Reading order: follow calls from the entry point; each type belongs to the first code that mentions it."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .model import Edge, Spec

FREE = "$free"  # owner of types that no code block mentions


@dataclass
class Order:
    code_nodes: List[str] = field(default_factory=list)
    depth: Dict[str, int] = field(default_factory=dict)
    tree_parent: Dict[str, Optional[str]] = field(default_factory=dict)
    members: Dict[str, List[str]] = field(default_factory=dict)
    child_depth: Dict[str, int] = field(default_factory=dict)
    owner: Dict[str, str] = field(default_factory=dict)
    tdepth: Dict[str, int] = field(default_factory=dict)
    owned: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    unreached: List[str] = field(default_factory=list)
    reading: Dict[str, List[str]] = field(default_factory=dict)

    def flat(self, owner_id: str) -> List[str]:
        """Types owned by owner_id, each followed by the types it owns."""
        out: List[str] = []
        for t in self.owned.get(owner_id, []):
            out.append(t)
            out.extend(self.flat(t))
        return out


def reading_order(spec: Spec) -> Order:
    order = Order()
    edges_from: Dict[str, List[Edge]] = defaultdict(list)
    for e in spec.edges:
        edges_from[e.src].append(e)
    for items in edges_from.values():
        items.sort(key=lambda e: e.line)

    def is_type(block_id: str) -> bool:
        return spec.block(block_id).role == "type"

    def container_members(cid: str, first: Optional[str]) -> List[str]:
        kids = {c.id for c in spec.children(cid)}
        members: List[str] = []

        def walk(bid: str, d: int) -> None:
            if bid in order.child_depth:
                return
            order.child_depth[bid] = d
            members.append(bid)
            for e in edges_from[bid]:
                if e.dst in kids:
                    walk(e.dst, d + 1)

        if first:
            walk(first, 0)
        for child in sorted(spec.children(cid), key=lambda c: c.start):
            walk(child.id, 0)
        return members

    def sources(node: str) -> List[str]:
        return [node] + order.members[node] if spec.block(node).role == "container" else [node]

    def visit(entering: str, parent: Optional[str], d: int) -> None:
        node = spec.node_of(entering)
        if node in order.depth:
            return
        order.depth[node] = d
        order.tree_parent[node] = parent
        order.code_nodes.append(node)
        if spec.block(node).role == "container":
            order.members[node] = container_members(node, entering if entering != node else None)
        else:
            order.members[node] = [node]
        for src in sources(node):
            for e in edges_from[src]:
                if not is_type(e.dst) and spec.node_of(e.dst) != node:
                    visit(e.dst, node, d + 1)

    for entry in spec.entry:
        visit(entry, None, 0)
    for b in spec.blocks:
        if b.role != "type" and not b.parent and b.id not in order.depth:
            order.unreached.append(b.id)
            visit(b.id, None, 0)

    def own(t: str, by: str, d: int) -> None:
        if t in order.owner:
            return
        order.owner[t] = by
        order.tdepth[t] = d
        order.owned[by].append(t)
        for e in edges_from[t]:
            if is_type(e.dst):
                own(e.dst, t, d + 1)

    for node in order.code_nodes:
        for src in sources(node):
            for e in edges_from[src]:
                if is_type(e.dst):
                    own(e.dst, node, 1)
    for b in spec.blocks:
        if b.role == "type" and b.id not in order.owner:
            own(b.id, FREE, 1)

    drawn = [b for n in order.code_nodes for b in order.members[n]]
    order.reading["column"] = drawn + [t for n in order.code_nodes for t in order.flat(n)] + order.flat(FREE)
    beside: List[str] = []
    for n in order.code_nodes:
        beside += order.members[n] + order.flat(n)
    order.reading["beside"] = beside + order.flat(FREE)
    return order
