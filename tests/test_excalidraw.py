import unittest

from tests.helpers import example
from tests.test_render import payload_for

from breakdown_lib.render_excalidraw import render_excalidraw

BASE_FIELDS = {"id", "type", "x", "y", "width", "height", "angle", "strokeColor", "backgroundColor", "fillStyle",
               "strokeWidth", "strokeStyle", "roughness", "opacity", "groupIds", "frameId", "roundness", "seed",
               "version", "versionNonce", "isDeleted", "boundElements", "updated", "link", "locked"}


class Excalidraw(unittest.TestCase):
    def drawing(self, name, mode="column"):
        root, data = example(name)
        return render_excalidraw(payload_for(root, data), mode)

    def test_claim_names_each_commit(self):
        root, data = example("fastapi-orders")
        payload = payload_for(root, data)
        payload["meta"]["claim"] = {"source": "commits", "title": "2 commits on feature", "body": "First\n\nWhy\n\nSecond",
                                    "commits": [{"sha": "abc1234", "message": "First\n\nWhy"},
                                                {"sha": "def5678", "message": "Second"}],
                                    "number": None, "url": None}
        texts = [e["text"] for e in render_excalidraw(payload, "column")["elements"] if e["type"] == "text"]
        claim = next(t for t in texts if t.startswith("Author's claim"))
        self.assertIn("abc1234  First\n\nWhy\n\ndef5678  Second", claim)

    def test_top_level_shape(self):
        d = self.drawing("fastapi-orders")
        self.assertEqual(d["type"], "excalidraw")
        self.assertEqual(d["version"], 2)
        self.assertEqual(d["files"], {})

    def test_every_element_is_complete_and_unique(self):
        for name in ("fastapi-orders", "library-ts"):
            els = self.drawing(name)["elements"]
            ids = [e["id"] for e in els]
            self.assertEqual(len(ids), len(set(ids)), name)
            for e in els:
                self.assertTrue(BASE_FIELDS <= set(e), f"{name}: {e['id']} misses {BASE_FIELDS - set(e)}")
                if e["type"] == "text":
                    self.assertEqual(e["text"], e["originalText"])
                    self.assertIsNone(e["containerId"])

    def test_arrows_are_bound_both_ways(self):
        els = self.drawing("library-ts")["elements"]
        by_id = {e["id"]: e for e in els}
        arrows = [e for e in els if e["type"] == "arrow"]
        self.assertEqual(len(arrows), 13)
        for a in arrows:
            for end in ("startBinding", "endBinding"):
                rect = by_id[a[end]["elementId"]]
                self.assertEqual(rect["type"], "rectangle")
                self.assertIn({"id": a["id"], "type": "arrow"}, rect["boundElements"])
            self.assertEqual(a["points"][0], [0, 0])

    def test_code_moves_with_its_box(self):
        els = {e["id"]: e for e in self.drawing("library-ts")["elements"]}
        self.assertEqual(els["t-Catalog.find"]["groupIds"], els["r-Catalog.find"]["groupIds"])
        self.assertEqual(els["r-Catalog.find"]["groupIds"], ["g-Catalog.find", "g-Catalog"])
        self.assertIn("find(isbn: string): Book {", els["t-Catalog.find"]["text"])

    def test_changed_boxes_read_like_a_diff(self):
        root, data = example("library-ts")
        payload = payload_for(root, data, {"checkLimit": {"status": "changed", "added": [1], "removed": [], "inserted": {}}})
        for b in payload["blocks"]:
            if b["id"] == "checkLimit":
                b["marks"] = {"+": [1], "-": []}  # what apply_rows would give this block
        els = {e["id"]: e for e in render_excalidraw(payload)["elements"]}
        lines = els["t-checkLimit"]["text"].split("\n")
        self.assertTrue(lines[0].startswith("  function checkLimit("))
        self.assertTrue(lines[1].startswith("+   const open"))
        self.assertFalse(els["t-lendBook"]["text"].startswith("  "))

    def test_layout_choice_moves_the_types(self):
        column = {e["id"]: e for e in self.drawing("fastapi-orders", "column")["elements"]}
        beside = {e["id"]: e for e in self.drawing("fastapi-orders", "beside")["elements"]}
        self.assertNotEqual(column["r-OrderRow"]["x"], beside["r-OrderRow"]["x"])
        self.assertEqual(column["r-create_order"]["x"], beside["r-create_order"]["x"])


if __name__ == "__main__":
    unittest.main()
