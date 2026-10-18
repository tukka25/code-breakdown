#!/usr/bin/env python3
"""Check and render a code breakdown.

  breakdown.py check  SPEC             validate the blocks and arrows against the source
  breakdown.py render SPEC [options]   check, then write .breakdown/<date>-<kind>-<slug>/

The repository root is the folder that holds .breakdown/ when the spec lives there; otherwise
the git root of the current folder. Both commands print one JSON object.
Exit codes: 0 ok, 1 the spec needs fixing, 2 the command could not run.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from breakdown_lib import __version__  # noqa: E402
from breakdown_lib.check import run_check  # noqa: E402
from breakdown_lib.diff import commit_messages, pull_request  # noqa: E402
from breakdown_lib.layout import layout  # noqa: E402
from breakdown_lib.order import reading_order  # noqa: E402
from breakdown_lib.output import FOLDER, ensure_git_exclude, open_file, output_dir  # noqa: E402
from breakdown_lib.payload import build_payload  # noqa: E402
from breakdown_lib.render_excalidraw import render_excalidraw  # noqa: E402
from breakdown_lib.render_html import render_html  # noqa: E402
from breakdown_lib.source import Source, SourceError, git_root  # noqa: E402


class Stop(Exception):
    """End the command with this JSON and exit code."""

    def __init__(self, data: Dict[str, Any], code: int):
        super().__init__(data)
        self.data, self.code = data, code


def emit(data: Dict[str, Any], code: int) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return code


def failure(at: str, problem: str, fix: str, code: int) -> Stop:
    return Stop({"ok": False, "errors": [{"at": at, "problem": problem, "fix": fix}]}, code)


def load(spec_path: Path) -> Any:
    if spec_path.is_dir():
        raise failure(str(spec_path), "this is a folder, not a spec file", "pass the path to spec.json", 2)
    try:
        text = spec_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise failure(str(spec_path), "the spec file does not exist",
                      "write the spec first, for example to .breakdown/spec.json", 2)
    except UnicodeDecodeError as exc:
        raise failure(str(spec_path), f"the spec is not UTF-8 text: {exc}", "save it as UTF-8", 1)
    try:
        return json.loads(text)
    except ValueError as exc:
        raise failure(str(spec_path), f"the spec is not valid JSON: {exc}", "fix the JSON syntax", 1)


def resolve_root(arg: str, spec_path: Path) -> Path:
    if arg:
        return Path(arg).resolve()
    spec_dir = spec_path.resolve().parent
    if spec_dir.name == FOLDER:
        return git_root(spec_dir.parent) or spec_dir.parent
    return git_root(spec_dir) or git_root(Path.cwd()) or Path.cwd().resolve()


def render(args: argparse.Namespace, data: Any, spec: Any, report: Any, source: Source, root: Path) -> int:
    order = reading_order(spec)
    for node in order.unreached:
        report.warnings.append(f"{node} is not reached from the entry point; it is drawn as its own start")
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
                            markers=spec.markers, claim=claim)

    if args.out:
        folder = Path(args.out).resolve()
    else:
        if (root / FOLDER).is_symlink():
            raise failure(str(root / FOLDER), f"{FOLDER} is a symbolic link, so output would leave the repository",
                          f"remove the link and let the script create a real {FOLDER} folder, or pass --out", 2)
        folder = output_dir(root, spec, args.today or None)
    folder.mkdir(parents=True, exist_ok=True)
    canvas = folder / "canvas.html"
    canvas.write_text(render_html(payload), encoding="utf-8")
    tree = folder / "tree.json"
    tree.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # The spec as written, so the breakdown can be rendered again after .breakdown/spec.json is reused.
    (folder / "spec.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(prog="breakdown.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"code-breakdown {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "render"):
        p = sub.add_parser(name)
        p.add_argument("spec", help="path to the spec JSON, usually <repo>/.breakdown/spec.json")
        p.add_argument("--root", default="", help="repository root; default: the folder that holds .breakdown/")
        if name == "render":
            p.add_argument("--excalidraw", action="store_true", help="also write breakdown.excalidraw")
            p.add_argument("--beside", action="store_true", help="open with types beside their first use (layout A)")
            p.add_argument("--open", action="store_true", help="open canvas.html in the default browser")
            p.add_argument("--no-exclude", action="store_true",
                           help="do not add .breakdown/ to .git/info/exclude (the only write outside .breakdown/)")
            p.add_argument("--out", default="", help="output folder; default: .breakdown/<date>-<kind>-<slug>")
            p.add_argument("--today", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    try:
        spec_path = Path(args.spec)
        data = load(spec_path)
        root = resolve_root(args.root, spec_path)
        source = Source(root)
        spec, report = run_check(data, source)
        if args.command == "check" or spec is None or not report.ok:
            out = report.as_dict()
            if spec is not None and report.ok:
                out.update(blocks=len(spec.blocks), arrows=len(spec.edges))
            return emit(out, 0 if report.ok else 1)
        return render(args, data, spec, report, source, root)
    except Stop as stop:
        return emit(stop.data, stop.code)
    except SourceError as exc:
        return emit({"ok": False, "errors": [{"at": "git", "problem": str(exc),
                                              "fix": "check the repository path and that git refs exist"}]}, 2)
    except Exception as exc:  # report anything unexpected as JSON, never as a bare traceback
        return emit({"ok": False, "errors": [{
            "at": "breakdown.py", "problem": f"unexpected {type(exc).__name__}: {exc}",
            "fix": "this is a bug in the script; the details are in 'trace'"}],
            "trace": traceback.format_exc(limit=6)}, 2)


if __name__ == "__main__":
    sys.exit(main())
