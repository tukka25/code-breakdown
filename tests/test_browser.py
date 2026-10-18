"""Load each example canvas in headless Chrome and check the page says it rendered. Skipped without Chrome."""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import example
from tests.test_render import payload_for

from breakdown_lib.render_html import render_html

CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome",
]


def find_chrome():
    for c in CANDIDATES:
        path = c if Path(c).is_file() else shutil.which(c)
        if path:
            return path
    return None


CHROME = find_chrome()


@unittest.skipUnless(CHROME, "Chrome or Chromium is not installed")
class Browser(unittest.TestCase):
    def test_examples_render_without_errors(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        for name in ("fastapi-orders", "library-ts"):
            root, data = example(name)
            page = tmp / f"{name}.html"
            page.write_text(render_html(payload_for(root, data)), encoding="utf-8")
            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=4000",
                                  "--dump-dom", page.as_uri()], capture_output=True, text=True, timeout=90)
            match = re.search(r'data-rendered="(\w+)"', out.stdout)
            self.assertIsNotNone(match, f"{name}: page never finished")
            self.assertEqual(match.group(1), "ok", name)


if __name__ == "__main__":
    unittest.main()
