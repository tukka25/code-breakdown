import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import block, example

from breakdown_lib.check import run_check
from breakdown_lib.source import Source


def check(name, edit=None):
    root, spec = example(name)
    if edit:
        edit(spec)
    return run_check(spec, Source(root))


def problems(report):
    return " | ".join(f"{e['at']}: {e['problem']} -> {e['fix']}" for e in report.errors)


class ExamplesPass(unittest.TestCase):
    def test_fastapi_example_is_clean(self):
        spec, report = check("fastapi-orders")
        self.assertTrue(report.ok, problems(report))
        # The example leaves authentication out on purpose; the check notices the User model it skipped.
        self.assertEqual(len(report.hints), 1, report.hints)
        self.assertIn("User", report.hints[0])
        self.assertIn("app/models.py:18", report.hints[0])
        self.assertEqual(spec.block("place_order").lines[0],
                         "def place_order(db: Session, user_id: int, body: CreateOrderIn) -> OrderRow:")

    def test_typescript_example_is_clean(self):
        spec, report = check("library-ts")
        self.assertTrue(report.ok, problems(report))
        self.assertEqual(spec.block("Catalog.constructor").lines,
                         ["  constructor(private books: Map<string, Book>) {}"])

    def test_edges_record_the_line_that_mentions_the_target(self):
        spec, _ = check("fastapi-orders")
        edge = next(e for e in spec.edges if e.src == "place_order" and e.dst == "apply_coupon")
        self.assertEqual(spec.block("place_order").lines[edge.line].strip(),
                         "total = apply_coupon(db, body.coupon, total)")


class Ranges(unittest.TestCase):
    def test_range_past_the_end_of_the_file(self):
        _, report = check("fastapi-orders", lambda s: block(s, "get_db").update(end=99))
        self.assertFalse(report.ok)
        self.assertIn("17 lines", problems(report))

    def test_range_that_misses_the_declaration_points_at_it(self):
        _, report = check("fastapi-orders", lambda s: block(s, "place_order").update(start=24, end=31))
        self.assertFalse(report.ok)
        self.assertIn("line 13", problems(report))

    def test_decorator_above_the_start_is_pulled_in(self):
        spec, report = check("fastapi-orders", lambda s: block(s, "create_order").update(start=15))
        self.assertTrue(report.ok, problems(report))
        self.assertEqual(spec.block("create_order").start, 14)
        self.assertTrue(any("create_order" in f and "14" in f for f in report.fixes), report.fixes)

    def test_unclosed_brace_suggests_the_real_end(self):
        _, report = check("library-ts", lambda s: block(s, "Catalog.find").update(end=30))
        self.assertFalse(report.ok)
        self.assertIn("32", problems(report))

    def test_python_body_cut_short_suggests_the_real_end(self):
        _, report = check("fastapi-orders", lambda s: block(s, "place_order").update(end=18))
        self.assertFalse(report.ok)
        self.assertIn("21", problems(report))

    def test_python_block_running_into_the_next_function(self):
        _, report = check("fastapi-orders", lambda s: block(s, "place_order").update(end=26))
        self.assertFalse(report.ok)
        self.assertIn("21", problems(report))

    def test_overlapping_blocks(self):
        def edit(s):
            s["blocks"].append({"id": "OrderRowAgain", "file": "app/models.py", "start": 32, "end": 38,
                                "role": "type", "name": "OrderRow"})
        _, report = check("fastapi-orders", edit)
        self.assertFalse(report.ok)
        self.assertIn("overlap", problems(report))

    def test_child_outside_its_container(self):
        _, report = check("library-ts", lambda s: block(s, "dueDate").update(parent="Catalog"))
        self.assertFalse(report.ok)
        self.assertIn("inside", problems(report))

    def test_missing_file_suggests_a_path(self):
        _, report = check("fastapi-orders", lambda s: block(s, "get_db").update(file="db.py"))
        self.assertFalse(report.ok)
        self.assertIn("app/db.py", problems(report))


class Snapping(unittest.TestCase):
    def run_on(self, name, text, block):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / name).write_text(text)
        data = {"kind": "file", "title": name, "entry": [block["id"]], "blocks": [block], "edges": []}
        return run_check(data, Source(tmp))

    def test_decorator_spanning_several_lines_is_pulled_in(self):
        text = '@router.post(\n    "/x",\n    status_code=201,\n)\ndef handler():\n    return 1\n'
        spec, report = self.run_on("api.py", text, {"id": "handler", "file": "api.py", "start": 5, "end": 6})
        self.assertTrue(report.ok, problems(report))
        self.assertEqual(spec.block("handler").start, 1)

    def test_unbalanced_decorator_stack_stops(self):
        text = '@outer(\n    "x",\n@inner\n)\ndef handler():\n    return 1\n'
        spec, report = self.run_on("api.py", text, {"id": "handler", "file": "api.py", "start": 5, "end": 6})
        self.assertTrue(report.ok, problems(report))
        self.assertEqual(spec.block("handler").start, 5)

    def test_block_swallowing_the_next_function_warns(self):
        text = "function a() {\n  return 1;\n}\n\nfunction b() {\n  return 2;\n}\n"
        _, report = self.run_on("x.ts", text, {"id": "a", "file": "x.ts", "start": 1, "end": 7})
        self.assertTrue(report.ok, problems(report))
        self.assertTrue(any("line 3" in w for w in report.warnings), report.warnings)

    def test_allman_braces_are_one_declaration(self):
        text = "void Run()\n{\n    Go();\n}\n"
        _, report = self.run_on("x.cs", text, {"id": "Run", "file": "x.cs", "start": 1, "end": 4})
        self.assertTrue(report.ok, problems(report))
        self.assertEqual(report.warnings, [])


class Arrows(unittest.TestCase):
    def test_arrow_without_evidence_is_rejected(self):
        _, report = check("fastapi-orders",
                          lambda s: s["edges"].append({"from": "create_order", "to": "apply_coupon"}))
        self.assertFalse(report.ok)
        self.assertIn("via", problems(report))

    def test_via_must_appear_in_the_source_block(self):
        def edit(s):
            next(e for e in s["edges"] if e.get("via"))["via"] = "this.shelves"
        _, report = check("library-ts", edit)
        self.assertFalse(report.ok)
        self.assertIn("this.shelves", problems(report))

    def test_unknown_ids_and_duplicates(self):
        def edit(s):
            s["edges"].append({"from": "create_order", "to": "nowhere"})
            s["blocks"].append(dict(block(s, "get_db")))
            s["entry"] = ["missing"]
        _, report = check("fastapi-orders", edit)
        text = problems(report)
        self.assertIn("nowhere", text)
        self.assertIn("missing", text)
        self.assertIn("duplicate", text)

    def test_declarations_left_out_become_hints(self):
        def edit(s):
            s["blocks"] = [b for b in s["blocks"] if b["id"] != "checkLimit"]
            s["edges"] = [e for e in s["edges"] if "checkLimit" not in (e["from"], e["to"])]
        _, report = check("library-ts", edit)
        self.assertTrue(report.ok, problems(report))
        self.assertTrue(any("checkLimit" in h and "src/loans.ts:50" in h for h in report.hints), report.hints)

    def test_names_without_arrows_become_hints(self):
        def edit(s):
            s["edges"] = [e for e in s["edges"] if not (e["from"] == "place_order" and e["to"] == "OrderRow")]
        spec, report = check("fastapi-orders", edit)
        self.assertTrue(report.ok, problems(report))
        self.assertTrue(any("OrderRow" in h for h in report.hints), report.hints)


class Labels(unittest.TestCase):
    def test_judging_words_are_rejected(self):
        _, report = check("fastapi-orders", lambda s: block(s, "get_db").update(label="Robust session"))
        self.assertFalse(report.ok)
        self.assertIn("robust", problems(report).lower())

    def test_long_labels_are_rejected(self):
        _, report = check("fastapi-orders",
                          lambda s: block(s, "get_db").update(label="Opens a database session for the request"))
        self.assertFalse(report.ok)


class SpecShape(unittest.TestCase):
    def test_unknown_kind_lists_the_valid_ones(self):
        _, report = check("fastapi-orders", lambda s: s.update(kind="module"))
        self.assertIn("file, endpoint, pr", problems(report))

    def test_entry_cannot_be_a_type(self):
        _, report = check("fastapi-orders", lambda s: s.update(entry=["OrderRow"]))
        self.assertFalse(report.ok)

    def test_side_base_needs_a_base_ref(self):
        _, report = check("fastapi-orders", lambda s: block(s, "get_db").update(side="base"))
        self.assertFalse(report.ok)
        self.assertIn("base", problems(report))


if __name__ == "__main__":
    unittest.main()
