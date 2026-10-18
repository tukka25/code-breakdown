import contextlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import EXAMPLES, example

import breakdown
from breakdown_lib.check import run_check
from breakdown_lib.layout import layout
from breakdown_lib.order import reading_order
from breakdown_lib.output import folder_name, slug
from breakdown_lib.payload import build_payload
from breakdown_lib.render_html import render_html
from breakdown_lib.source import Source

DATA = re.compile(r'<script type="application/json" id="bd-data">(.*?)</script>', re.S)


def payload_for(root, data, markers=None):
    source = Source(root)
    spec, report = run_check(data, source)
    assert report.ok, report.errors
    order = reading_order(spec)
    layouts = {m: layout(spec, order, m) for m in ("column", "beside")}
    return build_payload(spec, order, layouts, root=Path(root), default="column", report=report,
                         markers=markers, generated="2026-10-18T09:00:00+00:00")


def run_cli(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = breakdown.main(list(args))
        except SystemExit as exc:
            code = exc.code
    return code, json.loads(out.getvalue())


def git_repo_copy(name):
    tmp = Path(tempfile.mkdtemp()).resolve()  # macOS: /var is a link to /private/var
    shutil.copytree(EXAMPLES / name, tmp / name)
    repo = tmp / name
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return tmp, repo


class Html(unittest.TestCase):
    def test_code_cannot_close_the_data_script(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "evil.js").write_text('function render() {\n  return "</script><script>alert(1)</script>";\n}\n')
        data = {"kind": "file", "title": "evil.js", "entry": ["render"],
                "blocks": [{"id": "render", "file": "evil.js", "start": 1, "end": 3}], "edges": []}
        html = render_html(payload_for(tmp, data))
        self.assertNotIn("<script>alert(1)", html)
        embedded = json.loads(DATA.search(html).group(1))
        self.assertIn("</script><script>alert(1)</script>", embedded["blocks"][0]["lines"][1])

    def test_template_markers_inside_code_are_left_alone(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "m.py").write_text('def marker():\n    return "__BD_TITLE__ /*__BD_ROUGH__*/"\n')
        data = {"kind": "file", "title": "m.py", "entry": ["marker"],
                "blocks": [{"id": "marker", "file": "m.py", "start": 1, "end": 2}], "edges": []}
        html = render_html(payload_for(tmp, data))
        self.assertIn("<title>m.py · breakdown</title>", html)
        embedded = json.loads(DATA.search(html).group(1))
        self.assertIn("__BD_TITLE__ /*__BD_ROUGH__*/", embedded["blocks"][0]["lines"][1])

    def test_canvas_needs_no_network(self):
        root, data = example("fastapi-orders")
        html = render_html(payload_for(root, data))
        self.assertEqual(html.count("@font-face"), 5)
        self.assertIn("var rough=", html)
        self.assertIsNone(re.search(r'<(script|link)[^>]+(src|href)="https?:', html))


class Arrows(unittest.TestCase):
    def test_second_uses_are_hidden_until_they_come_from_a_changed_line(self):
        root, data = example("library-ts")

        def arrow(payload):
            return next(e for e in payload["edges"] if e["from"] == "checkLimit" and e["to"] == "Member")

        self.assertFalse(arrow(payload_for(root, data))["primary"])
        changed = {"checkLimit": {"status": "changed", "added": [0], "removed": [], "inserted": {}}}
        self.assertTrue(arrow(payload_for(root, data, changed))["primary"])


class Naming(unittest.TestCase):
    def test_slugs(self):
        self.assertEqual(slug("POST /orders"), "post-orders")
        self.assertEqual(slug("src/loans.ts"), "src-loans-ts")
        self.assertEqual(slug("!!!"), "breakdown")

    def test_folder_names(self):
        root, data = example("fastapi-orders")
        spec, _ = run_check(data, Source(root))
        self.assertEqual(folder_name(spec, "2026-10-18"), "2026-10-18-endpoint-post-orders")
        spec.kind, spec.title = "pr", "PR #12: Add coupons"
        self.assertEqual(folder_name(spec, "2026-10-18"), "2026-10-18-pr-12-add-coupons")


class Cli(unittest.TestCase):
    def test_check_reports_errors_with_exit_code_1(self):
        root, data = example("fastapi-orders")
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        data["blocks"][0]["end"] = 999
        spec_path = tmp / "spec.json"
        spec_path.write_text(json.dumps(data))
        code, out = run_cli("check", str(spec_path), "--root", str(root))
        self.assertEqual(code, 1)
        self.assertFalse(out["ok"])
        self.assertTrue(out["errors"][0]["fix"])

    def test_invalid_json_is_reported(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "spec.json").write_text("{ not json")
        code, out = run_cli("check", str(tmp / "spec.json"), "--root", str(tmp))
        self.assertEqual(code, 1)
        self.assertIn("JSON", out["errors"][0]["problem"])

    def test_render_writes_the_folder_and_keeps_it_out_of_git(self):
        tmp, repo = git_repo_copy("fastapi-orders")
        self.addCleanup(shutil.rmtree, tmp)
        spec_path = str(repo / "spec.json")
        code, out = run_cli("render", spec_path, "--root", str(repo), "--today", "2026-10-18")
        self.assertEqual(code, 0, out)
        folder = repo / ".breakdown" / "2026-10-18-endpoint-post-orders"
        self.assertEqual(Path(out["folder"]), folder)
        self.assertTrue((folder / "canvas.html").is_file())
        self.assertTrue((folder / "tree.json").is_file())
        self.assertFalse((folder / "breakdown.excalidraw").exists())
        self.assertIn(".breakdown/", (repo / ".git" / "info" / "exclude").read_text())

        code, out = run_cli("render", spec_path, "--root", str(repo), "--today", "2026-10-18", "--excalidraw", "--beside")
        self.assertEqual(code, 0, out)
        self.assertTrue((folder / "breakdown.excalidraw").is_file())
        self.assertEqual(out["layout"], "beside")
        self.assertNotIn("excluded", out)  # already excluded on the first run

        code, out = run_cli("render", spec_path, "--root", str(repo), "--today", "2026-10-18")
        self.assertFalse((folder / "breakdown.excalidraw").exists())

    def test_no_exclude_leaves_git_alone(self):
        tmp, repo = git_repo_copy("library-ts")
        self.addCleanup(shutil.rmtree, tmp)
        exclude = repo / ".git" / "info" / "exclude"
        before = exclude.read_text() if exclude.exists() else None
        code, out = run_cli("render", str(repo / "spec.json"), "--root", str(repo), "--no-exclude")
        self.assertEqual(code, 0, out)
        self.assertEqual(exclude.read_text() if exclude.exists() else None, before)


if __name__ == "__main__":
    unittest.main()
