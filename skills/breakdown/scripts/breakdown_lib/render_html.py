"""Write the standalone canvas: the template plus embedded fonts, rough.js and the payload."""

from __future__ import annotations

import base64
import html
import json
import re
from pathlib import Path
from typing import Any, Dict

ASSETS = Path(__file__).resolve().parents[2] / "assets"
FONTS = [
    ("BD Mono", "jetbrains-mono-latin-400-normal.woff2", 400),
    ("BD Condensed", "barlow-condensed-latin-600-normal.woff2", 600),
    ("BD Sans", "barlow-latin-400-normal.woff2", 400),
    ("BD Sans", "barlow-latin-500-normal.woff2", 500),
    ("BD Sans", "barlow-latin-600-normal.woff2", 600),
]
TOKENS = re.compile(r"/\*__BD_FONTS__\*/|/\*__BD_ROUGH__\*/|__BD_DATA__|__BD_TITLE__")


def font_css() -> str:
    rules = []
    for family, name, weight in FONTS:
        data = base64.b64encode((ASSETS / "vendor" / "fonts" / name).read_bytes()).decode("ascii")
        rules.append(f'@font-face {{ font-family: "{family}"; src: url(data:font/woff2;base64,{data}) format("woff2"); '
                     f"font-weight: {weight}; font-style: normal; font-display: block; }}")
    return "\n".join(rules)


def embed_json(data: Any) -> str:
    """JSON that is safe inside a <script> element: no "</script>", no "<!--", no line separators."""
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def render_html(payload: Dict[str, Any]) -> str:
    template = (ASSETS / "canvas.html").read_text(encoding="utf-8")
    values = {
        "/*__BD_FONTS__*/": font_css(),
        "/*__BD_ROUGH__*/": (ASSETS / "vendor" / "rough.js").read_text(encoding="utf-8"),
        "__BD_DATA__": embed_json(payload),
        "__BD_TITLE__": html.escape(payload["meta"]["title"] + " · breakdown"),
    }
    found = TOKENS.findall(template)
    if sorted(found) != sorted(values):
        raise RuntimeError(f"canvas template markers are wrong: {found}")
    # One pass over the template, so text inside the inserted values is never substituted again.
    return TOKENS.sub(lambda m: values[m.group(0)], template)
