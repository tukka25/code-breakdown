#!/usr/bin/env python3
"""Check and render a code breakdown.

  breakdown.py check  SPEC             validate the blocks and arrows against the source
  breakdown.py render SPEC [options]   check, then write .breakdown/<date>-<kind>-<slug>/

Both print one JSON object. Exit codes: 0 ok, 1 the spec needs fixing, 2 the command could not run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from breakdown_lib import __version__  # noqa: E402
from breakdown_lib.check import Report, run_check  # noqa: E402
from breakdown_lib.diff import apply_rows, change_markers, commit_messages, pull_request  # noqa: E402
from breakdown_lib.layout import layout  # noqa: E402
from breakdown_lib.order import reading_order  # noqa: E402
from breakdown_lib.output import ensure_git_exclude, open_file, output_dir  # noqa: E402
from breakdown_lib.payload import build_payload  # noqa: E402
from breakdown_lib.render_excalidraw import render_excalidraw  # noqa: E402
from breakdown_lib.render_html import render_html  # noqa: E402
from breakdown_lib.source import Source, SourceError, git_root  # noqa: E402


def emit(data: Dict[str, Any], code: int) -> int:
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return code


def load(spec_path: Path) -> Any:
    try:
        return json.loads(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(emit({"ok": False, "errors": [{
            "at": str(spec_path), "problem": "the spec file does not exist",
            "fix": "write the spec first, for example to .breakdown/spec.json"}]}, 2))
    except ValueError as exc:
        raise SystemExit(emit({"ok": False, "errors": [{
            "at": str(spec_path), "problem": f"the spec is not valid JSON: {exc}", "fix": "fix the JSON syntax"}]}, 1))


def resolve_root(arg: str, spec_path: Path) -> Path:
    if arg:
        return Path(arg).resolve()
    for start in (Path.cwd(), spec_path.resolve().parent):
        found = git_root(start)
        if found:
            return found
    return Path.cwd().resolve()


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(prog="breakdown.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"code-breakdown {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "render"):
        p = sub.add_parser(name)
        p.add_argument("spec", help="path to the spec JSON, usually .breakdown/spec.json")
        p.add_argument("--root", default="", help="repository root; default: the git root of the current directory")
        if name == "render":
            p.add_argument("--excalidraw", action="store_true", help="also write breakdown.excalidraw")
            p.add_argument("--beside", action="store_true", help="open with types beside their first use (layout A)")
            p.add_argument("--open", action="store_true", help="open canvas.html in the default browser")
            p.add_argument("--no-exclude", action="store_true",
                           help="do not add .breakdown/ to .git/info/exclude (the only write outside .breakdown/)")
            p.add_argument("--out", default="", help="output folder; default: .breakdown/<date>-<kind>-<slug>")
            p.add_argument("--today", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    data = load(spec_path)
    root = resolve_root(args.root, spec_path)
    source = Source(root)
    try:
        spec, report = run_check(data, source)
    except SourceError as exc:
        return emit({"ok": False, "errors": [{"at": "git", "problem": str(exc), "fix": "check the repository and refs"}]}, 2)

    if args.command == "check" or spec is None or not report.ok:
        out = report.as_dict()
        if spec is not None and report.ok:
            out.update(blocks=len(spec.blocks), arrows=len(spec.edges))
        return emit(out, 0 if report.ok else 1)

    order = reading_order(spec)
    for node in order.unreached:
        report.warnings.append(f"{node} is not reached from the entry point; it is drawn as its own start")
    try:
        markers = change_markers(spec, source)
    except SourceError as exc:
        return emit({"ok": False, "errors": [{"at": "base", "problem": f"git diff failed: {exc}",
                                              "fix": "check that base and head are fetched"}]}, 2)
    apply_rows(spec, markers)  # before the layout, so boxes are sized with their removed lines
    layouts = {mode: layout(spec, order, mode) for mode in ("column", "beside")}
    claim = None
    if spec.pr:
        claim, warning = pull_request(source, spec.pr)
        if warning:
            report.warnings.append(warning + "; the canvas shows no author's claim")
    elif spec.base:
        claim = commit_messages(source, spec.base, spec.head)
    default = "beside" if args.beside else "column"
    payload = build_payload(spec, order, layouts, root=root, default=default, report=report,
                            markers=markers, claim=claim)

    folder = Path(args.out).resolve() if args.out else output_dir(root, spec, args.today or None)
    folder.mkdir(parents=True, exist_ok=True)
    canvas = folder / "canvas.html"
    canvas.write_text(render_html(payload), encoding="utf-8")
    tree = folder / "tree.json"
    tree.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result: Dict[str, Any] = {"ok": True, "folder": str(folder), "canvas": str(canvas), "tree": str(tree)}
    drawing = folder / "breakdown.excalidraw"
    if args.excalidraw:
        drawing.write_text(json.dumps(render_excalidraw(payload, default), indent=1, ensure_ascii=False) + "\n",
                           encoding="utf-8")
        result["excalidraw"] = str(drawing)
    elif drawing.exists():
        drawing.unlink()  # a stale drawing from an earlier run would no longer match the canvas
    if not args.no_exclude and ensure_git_exclude(root):
        result["excluded"] = ".breakdown/ added to .git/info/exclude"
    if args.open:
        result["opened"] = open_file(canvas)
    result.update(blocks=len(spec.blocks), arrows=len(spec.edges), layout=default)
    for key in ("fixes", "hints", "warnings"):
        value = getattr(report, key)
        if value:
            result[key] = value
    return emit(result, 0)


if __name__ == "__main__":
    sys.exit(main())
