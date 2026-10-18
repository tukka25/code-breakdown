import itertools
import unittest

from tests.helpers import example

from breakdown_lib.check import run_check
from breakdown_lib.layout import LABEL, layout
from breakdown_lib.order import reading_order
from breakdown_lib.source import Source


def prepared(name, edit=None):
    root, data = example(name)
    if edit:
        edit(data)
    spec, report = run_check(data, Source(root))
    assert report.ok, report.errors
    return spec, reading_order(spec)


def overlaps(a, b, pad=0.0):
    return a.x < b.x + b.w + pad and b.x < a.x + a.w + pad and a.y < b.y + b.h + pad and b.y < a.y + a.h + pad


class ReadingOrder(unittest.TestCase):
    def test_code_follows_calls_in_line_order(self):
        _, order = prepared("fastapi-orders")
        self.assertEqual(order.code_nodes, ["create_order", "get_db", "place_order", "load_products",
                                            "price_lines", "apply_coupon", "reserve_stock", "insert_order"])

    def test_column_order_puts_types_last_grouped_by_first_user(self):
        _, order = prepared("fastapi-orders")
        self.assertEqual(order.reading["column"][8:], ["OrderOut", "OrderStatus", "CreateOrderIn", "LineIn",
                                                       "OrderRow", "OrderLineRow", "ProductRow", "CouponRow"])

    def test_beside_order_puts_each_type_after_its_first_user(self):
        _, order = prepared("fastapi-orders")
        self.assertEqual(order.reading["beside"][:6], ["create_order", "OrderOut", "OrderStatus",
                                                       "CreateOrderIn", "LineIn", "get_db"])

    def test_container_methods_follow_internal_calls(self):
        _, order = prepared("library-ts")
        self.assertEqual(order.code_nodes, ["lendBook", "checkLimit", "Catalog", "dueDate"])
        self.assertEqual(order.members["Catalog"], ["Catalog.takeCopy", "Catalog.find", "Catalog.constructor"])

    def test_unreached_code_becomes_its_own_root(self):
        def edit(data):
            data["edges"] = [e for e in data["edges"] if e["to"] != "dueDate"]
        _, order = prepared("library-ts", edit)
        self.assertEqual(order.unreached, ["dueDate"])
        self.assertIn("dueDate", order.reading["column"])


class Geometry(unittest.TestCase):
    CASES = [(name, mode) for name in ("fastapi-orders", "library-ts") for mode in ("column", "beside")]

    def test_boxes_and_their_labels_never_overlap(self):
        for name, mode in self.CASES:
            spec, order = prepared(name)
            boxes = layout(spec, order, mode).boxes
            for a, b in itertools.combinations(spec.blocks, 2):
                if a.parent == b.id or b.parent == a.id:
                    continue
                ra, rb = boxes[a.id], boxes[b.id]
                # Grow each box upward by the label band so labels count too.
                la = type(ra)(ra.x, ra.y - LABEL, ra.w, ra.h + LABEL)
                lb = type(rb)(rb.x, rb.y - LABEL, rb.w, rb.h + LABEL)
                self.assertFalse(overlaps(la, lb), f"{name}/{mode}: {a.id} overlaps {b.id}")

    def test_entry_point_is_leftmost(self):
        for name, mode in self.CASES:
            spec, order = prepared(name)
            boxes = layout(spec, order, mode).boxes
            entry = boxes[spec.entry[0]]
            self.assertEqual(entry.x, min(boxes[b.id].x for b in spec.blocks if not b.parent), f"{name}/{mode}")

    def test_callees_never_sit_above_their_caller(self):
        for name, mode in self.CASES:
            spec, order = prepared(name)
            boxes = layout(spec, order, mode).boxes
            for node, parent in order.tree_parent.items():
                if parent:
                    self.assertGreaterEqual(boxes[node].y, boxes[parent].y, f"{name}/{mode}: {node}")

    def test_column_layout_puts_every_type_right_of_all_code(self):
        spec, order = prepared("fastapi-orders")
        boxes = layout(spec, order, "column").boxes
        code_right = max(boxes[b.id].x + boxes[b.id].w for b in spec.blocks if b.role != "type")
        self.assertTrue(all(boxes[b.id].x > code_right for b in spec.blocks if b.role == "type"))

    def test_beside_layout_puts_types_under_their_owner(self):
        spec, order = prepared("fastapi-orders")
        boxes = layout(spec, order, "beside").boxes
        for t, owner in order.owner.items():
            node = owner
            while node in order.owner:  # a component type sits under the type that owns it
                node = order.owner[node]
            self.assertGreater(boxes[t].x, boxes[node].x - 1, t)
            self.assertGreater(boxes[t].y, boxes[node].y + boxes[node].h - 1, t)

    def test_containers_enclose_their_methods(self):
        for mode in ("column", "beside"):
            spec, order = prepared("library-ts")
            boxes = layout(spec, order, mode).boxes
            c = boxes["Catalog"]
            for child in spec.children("Catalog"):
                r = boxes[child.id]
                self.assertTrue(c.x < r.x and r.x + r.w < c.x + c.w and c.y < r.y and r.y + r.h < c.y + c.h,
                                f"{mode}: {child.id}")


if __name__ == "__main__":
    unittest.main()
