"""Cases from review and from agents using the skill: each one failed before its fix."""

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import tests.helpers  # noqa: F401  (puts the scripts folder on sys.path)

import breakdown
from breakdown_lib.check import run_check
from breakdown_lib.diff import _insertions
from breakdown_lib.model import Block
from breakdown_lib.source import Source

GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=GIT_ENV)


class Files(unittest.TestCase):
    """Write files into a temporary folder and check one spec against them."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def check(self, blocks, edges=(), entry=None, **top):
        data = {"kind": "file", "title": "t", "entry": entry or [blocks[0]["id"]], "blocks": list(blocks),
                "edges": list(edges), **top}
        return run_check(data, Source(self.root))

    def assertOk(self, report):
        self.assertTrue(report.ok, [f"{e['at']}: {e['problem']} -> {e['fix']}" for e in report.errors])


class Decorators(Files):
    BLACK = ('@router.post(\n    "/orders",\n    response_model=OrderOut,\n    status_code=201,\n)\n'
             "async def create_order(body):\n    return await place(body)\n")

    def test_exploded_decorator_from_the_def_line(self):
        self.write("api.py", self.BLACK)
        spec, report = self.check([{"id": "create_order", "file": "api.py", "start": 6, "end": 7}])
        self.assertOk(report)
        self.assertEqual(spec.block("create_order").start, 1)
        self.assertEqual(spec.block("create_order").lines[5], "async def create_order(body):")

    def test_exploded_decorator_from_the_at_line(self):
        self.write("api.py", self.BLACK)
        _, report = self.check([{"id": "create_order", "file": "api.py", "start": 1, "end": 7}])
        self.assertOk(report)

    def test_route_path_that_names_the_handler(self):
        self.write("api.py", '@router.post(\n    "/login",\n    response_model=Token,\n)\n'
                             "async def login(form):\n    return token(form)\n")
        spec, report = self.check([{"id": "login", "file": "api.py", "start": 1, "end": 6}])
        self.assertOk(report)
        self.assertEqual(spec.block("login").def_line, 4)

    def test_multi_line_java_annotation(self):
        self.write("C.java", "class C {\n  @RequestMapping(\n    value = \"/orders\",\n    method = POST\n  )\n"
                             "  public Order create(Order o) {\n    return repo.save(o);\n  }\n}\n")
        spec, report = self.check([{"id": "create", "file": "C.java", "start": 6, "end": 8}])
        self.assertOk(report)
        self.assertEqual(spec.block("create").start, 2)

    def test_snapping_never_swallows_the_function_above(self):
        self.write("m.py", '@app.get("/a")\ndef a():\n    return [\n        1,\n    ]\ndef b():\n    return 2\n')
        spec, report = self.check([{"id": "b", "file": "m.py", "start": 6, "end": 7}])
        self.assertOk(report)
        self.assertEqual(spec.block("b").start, 6)

    def test_continuation_line_is_not_a_comment(self):
        self.write("k.py", "class K:\n    def a(self):\n        return call(x,\n            *args)\n"
                           "    def b(self):\n        return 1\n")
        spec, report = self.check([{"id": "K.b", "file": "k.py", "start": 5, "end": 6}])
        self.assertOk(report)
        self.assertEqual(spec.block("K.b").start, 5)


class PythonBodies(Files):
    def test_column_zero_comment_inside_a_body(self):
        self.write("p.py", "def process(order):\n    a = check(order)\n#    log(a)\n    return save(a)\n")
        _, report = self.check([{"id": "process", "file": "p.py", "start": 1, "end": 4}])
        self.assertOk(report)

    def test_trailing_comment_before_the_next_method(self):
        self.write("k.py", "class K:\n    def a(self):\n        x = 1\n        # note\n    def b(self):\n        return 2\n")
        _, report = self.check([
            {"id": "K", "file": "k.py", "start": 1, "end": 6, "role": "container"},
            {"id": "K.a", "file": "k.py", "start": 2, "end": 4, "parent": "K"},
            {"id": "K.b", "file": "k.py", "start": 5, "end": 6, "parent": "K"},
        ], entry=["K.a"])
        self.assertOk(report)


class Evidence(Files):
    def test_docstrings_and_comments_do_not_prove_a_call(self):
        self.write("s.py", 'def place(order):\n    """Ends in save_order, eventually."""\n    # save_order(order)\n'
                           "    return order\n\n\ndef save_order(o):\n    return o\n")
        _, report = self.check([{"id": "place", "file": "s.py", "start": 1, "end": 4},
                                {"id": "save_order", "file": "s.py", "start": 7, "end": 8}],
                               edges=[{"from": "place", "to": "save_order"}])
        self.assertFalse(report.ok)
        self.assertIn("comments and docstrings", report.errors[0]["fix"])

    def test_a_method_does_not_prove_a_call_with_its_own_name(self):
        self.write("svc.py", "class OrderService:\n    def create(self, o):\n        return self.repo.create(o)\n\n\n"
                             "class OrderRepo:\n    def create(self, o):\n        return o\n")
        blocks = [
            {"id": "OrderService", "file": "svc.py", "start": 1, "end": 3, "role": "container"},
            {"id": "OrderService.create", "file": "svc.py", "start": 2, "end": 3, "parent": "OrderService"},
            {"id": "OrderRepo", "file": "svc.py", "start": 6, "end": 8, "role": "container"},
            {"id": "OrderRepo.create", "file": "svc.py", "start": 7, "end": 8, "parent": "OrderRepo"},
        ]
        _, report = self.check(blocks, edges=[{"from": "OrderRepo.create", "to": "OrderService.create"}],
                               entry=["OrderService.create"])
        self.assertFalse(report.ok)
        _, report = self.check(blocks, edges=[{"from": "OrderService.create", "to": "OrderRepo.create"}],
                               entry=["OrderService.create"])
        self.assertOk(report)
        self.assertEqual(report.hints, [])

    def test_quoted_forward_reference_is_a_type_use(self):
        self.write("models.py", 'class Order:\n    lines: list["OrderLine"]\n\n\nclass OrderLine:\n    qty: int\n\n\n'
                                "def build():\n    return Order()\n")
        _, report = self.check([{"id": "build", "file": "models.py", "start": 9, "end": 10},
                                {"id": "Order", "file": "models.py", "start": 1, "end": 2, "role": "type"},
                                {"id": "OrderLine", "file": "models.py", "start": 5, "end": 6, "role": "type"}],
                               edges=[{"from": "build", "to": "Order"}, {"from": "Order", "to": "OrderLine"}])
        self.assertOk(report)


class BraceLanguages(Files):
    def test_expression_bodied_arrow_function(self):
        self.write("add.ts", "export const add = (a: number, b: number) =>\n  a + b;\n\nexport const two = 2;\n")
        _, report = self.check([{"id": "add", "file": "add.ts", "start": 1, "end": 2}])
        self.assertOk(report)
        self.assertEqual(report.warnings, [])

    def test_java_text_block(self):
        self.write("Q.java", 'class Q {\n  String sql() {\n    return """\n      select ( from\n      """;\n  }\n}\n')
        _, report = self.check([{"id": "sql", "file": "Q.java", "start": 2, "end": 6}])
        self.assertOk(report)

    def test_closing_bracket_error_offers_the_escape_hatch(self):
        self.write("x.ts", "function f() {\n  return 1;\n}\n}\n")
        _, report = self.check([{"id": "f", "file": "x.ts", "start": 1, "end": 4}])
        self.assertFalse(report.ok)
        self.assertIn("no_bracket_check", report.errors[0]["fix"])


class SpecRules(Files):
    def test_type_inside_a_container_is_refused(self):
        self.write("s.py", "class Service:\n    class Config:\n        x = 1\n\n    def run(self):\n        return 1\n")
        _, report = self.check([
            {"id": "Service", "file": "s.py", "start": 1, "end": 6, "role": "container"},
            {"id": "Service.Config", "file": "s.py", "start": 2, "end": 3, "role": "type", "parent": "Service"},
            {"id": "Service.run", "file": "s.py", "start": 5, "end": 6, "parent": "Service"},
        ], entry=["Service.run"])
        self.assertFalse(report.ok)

    def test_a_call_site_is_not_a_declaration(self):
        self.write("o.py", "def outer(x):\n    y = create_order(x)\n    return y\n")
        _, report = self.check([{"id": "create_order", "file": "o.py", "start": 2, "end": 2, "no_bracket_check": "false"}])
        self.assertTrue(any("does not look like" in w for w in report.warnings), report.warnings)

    def test_absolute_paths_are_made_relative(self):
        self.write("a.py", "def a():\n    return 1\n")
        spec, report = self.check([{"id": "a", "file": str(self.root / "a.py"), "start": 1, "end": 2}])
        self.assertOk(report)
        self.assertEqual(spec.block("a").file, "a.py")

    def test_role_words_are_not_judging_words(self):
        self.write("a.py", "def a():\n    return 1\n")
        _, report = self.check([{"id": "a", "file": "a.py", "start": 1, "end": 2, "label": "Builds cache key"}])
        self.assertOk(report)


class Changes(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo)
        git(self.repo, "init", "-q", "-b", "main")

    def commit(self, files, message):
        for name, text in files.items():
            (self.repo / name).write_text(text)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)

    def test_merged_hunks_stay_in_their_own_block(self):
        b = Block(id="place", file="o.py", start=1, end=3, lines=["def place(o):", "    check(o)", "    return save(o)"])
        base = ["def place(o):", "    legacy(o)", "    return save(o)", "", "", "def legacy(o):", "    return o"]
        inserted = _insertions([(2, 6, 2, 1)], b, base)
        self.assertEqual(inserted, {1: ["    legacy(o)", "    return save(o)"]})

    def test_deleting_the_last_python_statement_is_shown(self):
        self.commit({"f.py": "def f():\n    a()\n    b()\n"}, "base")
        git(self.repo, "checkout", "-q", "-b", "feature")
        self.commit({"f.py": "def f():\n    a()\n"}, "drop b")
        spec, report = run_check({"kind": "pr", "title": "t", "base": "main", "head": "feature", "entry": ["f"],
                                  "blocks": [{"id": "f", "file": "f.py", "start": 1, "end": 2}], "edges": []},
                                 Source(self.repo))
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(spec.markers["f"]["status"], "changed")
        self.assertEqual(spec.block("f").rows[-1], ("    b()", "del"))

    def test_untracked_file_in_the_working_tree_is_new(self):
        self.commit({"a.py": "def a():\n    return 1\n"}, "base")
        (self.repo / "b.py").write_text("def b():\n    return 2\n")
        spec, report = run_check({"kind": "pr", "title": "t", "base": "main", "entry": ["b"],
                                  "blocks": [{"id": "b", "file": "b.py", "start": 1, "end": 2}], "edges": []},
                                 Source(self.repo))
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(spec.markers["b"]["status"], "new")

    def test_renamed_file_keeps_its_unchanged_lines(self):
        self.commit({"orders.py": "def place(o):\n    return o\n"}, "base")
        git(self.repo, "checkout", "-q", "-b", "feature")
        git(self.repo, "mv", "orders.py", "shop.py")
        git(self.repo, "commit", "-q", "-m", "rename")
        spec, report = run_check({"kind": "pr", "title": "t", "base": "main", "head": "feature", "entry": ["place"],
                                  "blocks": [{"id": "place", "file": "shop.py", "start": 1, "end": 2}], "edges": []},
                                 Source(self.repo))
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(spec.markers["place"]["status"], "same")

    def test_an_arrow_can_leave_from_a_removed_line(self):
        self.commit({"o.py": "def place(o):\n    legacy_total(o)\n    return o\n\n\ndef legacy_total(o):\n    return 0\n"}, "base")
        git(self.repo, "checkout", "-q", "-b", "feature")
        self.commit({"o.py": "def place(o):\n    return o\n"}, "drop legacy")
        spec, report = run_check({
            "kind": "pr", "title": "t", "base": "main", "head": "feature", "entry": ["place"],
            "blocks": [{"id": "place", "file": "o.py", "start": 1, "end": 2},
                       {"id": "legacy_total", "file": "o.py", "start": 6, "end": 7, "side": "base"}],
            "edges": [{"from": "place", "to": "legacy_total"}]}, Source(self.repo))
        self.assertTrue(report.ok, report.errors)
        edge = spec.edges[0]
        self.assertEqual(spec.block("place").rows[edge.line], ("    legacy_total(o)", "del"))


class Cli(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo)
        git(self.repo, "init", "-q")
        (self.repo / "a.py").write_text("def a():\n    return 1\n")
        (self.repo / ".breakdown").mkdir()
        self.spec = self.repo / ".breakdown" / "spec.json"
        self.data = {"kind": "file", "title": "a.py", "entry": ["a"],
                     "blocks": [{"id": "a", "file": "a.py", "start": 1, "end": 2}], "edges": []}

    def run_cli(self, *args, cwd=None):
        out = io.StringIO()
        old = os.getcwd()
        os.chdir(cwd or tempfile.gettempdir())
        try:
            with contextlib.redirect_stdout(out):
                code = breakdown.main(list(args))
        finally:
            os.chdir(old)
        return code, json.loads(out.getvalue())

    def test_root_comes_from_where_the_spec_lives(self):
        self.spec.write_text(json.dumps(self.data))
        code, out = self.run_cli("render", str(self.spec), "--no-exclude")
        self.assertEqual(code, 0, out)
        folder = Path(out["folder"])
        self.assertEqual(folder.parent, self.repo / ".breakdown")
        self.assertEqual(json.loads((folder / "spec.json").read_text()), self.data)

    def test_spec_with_a_byte_order_mark(self):
        self.spec.write_text("\ufeff" + json.dumps(self.data), encoding="utf-8")
        code, out = self.run_cli("check", str(self.spec))
        self.assertEqual(code, 0, out)

    def test_folder_instead_of_spec(self):
        code, out = self.run_cli("check", str(self.repo))
        self.assertEqual(code, 2)
        self.assertIn("folder", out["errors"][0]["problem"])

    def test_symlinked_output_folder_is_refused(self):
        outside = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, outside)
        shutil.rmtree(self.repo / ".breakdown")
        (self.repo / ".breakdown").symlink_to(outside, target_is_directory=True)
        spec = self.repo / "spec.json"
        spec.write_text(json.dumps(self.data))
        code, out = self.run_cli("render", str(spec), "--root", str(self.repo), "--no-exclude")
        self.assertEqual(code, 2, out)
        self.assertEqual(list(outside.iterdir()), [])


class CanvasLinks(unittest.TestCase):
    def test_file_names_with_hash_or_question_mark(self):
        from tests.test_render import payload_for
        from breakdown_lib.render_html import render_html
        root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, root)
        (root / "a#b?.js").write_text("function f() {\n  return 1;\n}\n")
        html = render_html(payload_for(root, {"kind": "file", "title": "t", "entry": ["f"],
                                              "blocks": [{"id": "f", "file": "a#b?.js", "start": 1, "end": 3}]}))
        self.assertIn("encodeURIComponent(seg)", html)
        self.assertIsNotNone(re.search(r'"file":"a#b\?\.js"', html))


if __name__ == "__main__":
    unittest.main()
