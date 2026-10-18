import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tests.helpers  # noqa: F401  (puts the scripts folder on sys.path)

from breakdown_lib.check import run_check
from breakdown_lib.diff import apply_rows, change_markers, commit_messages, parse_hunks, pull_request
from breakdown_lib.source import Source

BASE = '''def place(order):
    check(order)
    return save(order)


def check(order):
    if not order.lines:
        raise ValueError("empty order")


def save(order):
    return order


def legacy_total(order):
    return sum(line.price for line in order.lines)
'''

HEAD = '''def place(order):
    check(order)
    notify(order)
    return save(order)


def check(order):
    if not order.lines:
        raise ValueError("an order needs at least one line")


def save(order):
    return order


def notify(order):
    print("placed", order.id)
'''


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"})


class Hunks(unittest.TestCase):
    def test_parse_zero_context_headers(self):
        text = "@@ -3,0 +4 @@\n+x\n@@ -10,2 +11,0 @@\n-a\n-b\n"
        self.assertEqual(parse_hunks(text), [(3, 0, 4, 1), (10, 2, 11, 0)])


class Markers(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "orders.py").write_text(BASE)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "base")
        git(self.repo, "checkout", "-q", "-b", "feature")
        (self.repo / "orders.py").write_text(HEAD)
        git(self.repo, "commit", "-q", "-am", "notify instead of legacy total")

    def spec(self):
        return {
            "kind": "pr", "title": "feature vs main", "base": "main", "head": "feature", "entry": ["place"],
            "blocks": [
                {"id": "place", "file": "orders.py", "start": 1, "end": 4},
                {"id": "check", "file": "orders.py", "start": 7, "end": 9},
                {"id": "notify", "file": "orders.py", "start": 16, "end": 17},
                {"id": "legacy_total", "file": "orders.py", "start": 15, "end": 16, "side": "base"},
            ],
            "edges": [{"from": "place", "to": "check"}, {"from": "place", "to": "notify"}],
        }

    def test_status_and_line_marks(self):
        source = Source(self.repo)
        spec, report = run_check(self.spec(), source)
        self.assertTrue(report.ok, report.errors)
        marks = change_markers(spec, source)
        self.assertEqual(marks["place"], {"status": "changed", "added": [2], "removed": [], "inserted": {}})
        self.assertEqual(marks["check"]["status"], "changed")
        self.assertEqual(marks["notify"]["status"], "new")
        self.assertEqual(marks["legacy_total"]["status"], "deleted")
        self.assertEqual(marks["legacy_total"]["removed"], [0, 1])

    def test_replaced_lines_show_the_old_line_before_the_new(self):
        source = Source(self.repo)
        spec, _ = run_check(self.spec(), source)
        apply_rows(spec, change_markers(spec, source))
        check = spec.block("check")
        self.assertEqual(check.rows, [
            ("def check(order):", ""),
            ("    if not order.lines:", ""),
            ('        raise ValueError("empty order")', "del"),
            ('        raise ValueError("an order needs at least one line")', "add"),
        ])
        self.assertEqual(check.index_map, [0, 1, 3])
        self.assertTrue(all(mark == "del" for _, mark in spec.block("legacy_total").rows))

    def test_commit_messages_stand_in_for_a_missing_pr(self):
        claim = commit_messages(Source(self.repo), "main", "feature")
        self.assertEqual(claim["source"], "commits")
        self.assertEqual(claim["title"], "1 commit on feature")
        self.assertEqual(claim["body"], "notify instead of legacy total")
        self.assertEqual([c["message"] for c in claim["commits"]], ["notify instead of legacy total"])
        self.assertRegex(claim["commits"][0]["sha"], r"^[0-9a-f]{7,}$")

    def test_each_commit_keeps_its_own_message(self):
        (self.repo / "orders.py").write_text(HEAD + "\n\ndef audit(order):\n    return order\n")
        git(self.repo, "commit", "-q", "-am", "Add audit\n\nKeeps a trail.")
        claim = commit_messages(Source(self.repo), "main", "feature")
        self.assertEqual(claim["title"], "2 commits on feature")
        self.assertEqual([c["message"] for c in claim["commits"]],
                         ["notify instead of legacy total", "Add audit\n\nKeeps a trail."])

    def test_base_blocks_are_read_from_the_base_version(self):
        spec, report = run_check(self.spec(), Source(self.repo))
        self.assertEqual(spec.block("legacy_total").lines[0], "def legacy_total(order):")

    def test_unknown_ref_is_an_error(self):
        data = self.spec()
        data["base"] = "no-such-branch"
        _, report = run_check(data, Source(self.repo))
        self.assertFalse(report.ok)
        self.assertIn("no-such-branch", report.errors[0]["problem"])


class PullRequestText(unittest.TestCase):
    def test_reads_title_and_body_verbatim(self):
        fake = mock.Mock(returncode=0, stdout=json.dumps(
            {"number": 7, "title": "Add notify", "body": "Sends a note.\n\nFixes #3", "url": "https://example.com/7"}))
        with mock.patch("breakdown_lib.diff.subprocess.run", return_value=fake):
            info, warning = pull_request(Source(Path(".")), 7)
        self.assertIsNone(warning)
        self.assertEqual(info["body"], "Sends a note.\n\nFixes #3")

    def test_gh_failure_becomes_a_warning(self):
        fake = mock.Mock(returncode=1, stdout="", stderr="no pull requests found")
        with mock.patch("breakdown_lib.diff.subprocess.run", return_value=fake):
            info, warning = pull_request(Source(Path(".")), 7)
        self.assertIsNone(info)
        self.assertIn("no pull requests found", warning)


if __name__ == "__main__":
    unittest.main()
