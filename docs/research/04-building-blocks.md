# 04 · Technical building blocks

Checked 2026-10-18. Checks ran in a temporary folder on macOS (arm64). Markdown output was dropped, so it is skipped.

## 1. Machine inventory

| Item | Result |
|---|---|
| python3 | 3.13.1 (Homebrew). `/usr/bin/python3` is 3.9.6 |
| pygments, tree_sitter | neither imports |
| node / npm | v24.15.0 / 11.12.1 |
| git / gh | 2.47.1 / 2.95.0 (logged in) |
| ctags | Apple BSD ctags (`--version` → "illegal option"), not universal-ctags |
| ast-grep, tree-sitter CLI, dot | not installed |
| Other | uv 0.8.15, Chrome, VS Code; arm64, macOS 26.6.2 |

## 2. Splitting a file into blocks

| Option | Keeps comments and decorators | Install | Notes |
|---|---|---|---|
| py-tree-sitter 0.26.0 + grammar wheels | yes, if you also walk adjacent comment siblings | venv, Python ≥3.10, arm64 wheels | exact; gives a tree |
| tree-sitter-language-pack 1.22.1 | same | 2.2 MB wheel | [downloads each parser on first use](https://github.com/xberg-io/tree-sitter-language-pack), so not offline |
| ast-grep 0.51.0 | no: `class_definition` starts after `@dataclass` | pip `ast-grep-cli` (17 MB) | flat list; `sg` name deprecated |
| universal-ctags | `--fields=+ne` (`n` line, `e` end) | brew; not on this machine | end lines exist for Python, Go, C/C++ and Java; no end-line code in `jscript.c`/`typescript.c` |
| LSP documentSymbol | [spec](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_documentSymbol): `range` includes comments | a server per language | has `children` |
| Model picks lines, stdlib script validates | via an upward "snap" rule | none; ran on Python 3.9.6 | default |

tree-sitter check (1-based):

```
orders.ts  class OrderService L11-21 (comment + @Injectable kept); create L16-20 (JSDoc kept)
orders.py  LineItem L4-8 (@dataclass kept); validate L16-20 (@staticmethod kept)
orders.go  LineItem L3-7; method Create L15-18 (top level, so group methods by receiver)
Java       OrderService L5-21 (Javadoc + @Service); create L12-16 (@Transactional kept)
```

Validator check: a good tree passed. It rejected `L27-99 outside file (1-30)` and `computeTotal L23-24 unbalanced brackets (depth 1)`.

**Recommendation.** By default, a stdlib validator checks four things:
- the range is inside the file;
- brackets balance once strings and comments are stripped;
- for Python, the next non-blank line is not indented deeper;
- each child sits inside its parent.

It then extends the start upward over adjacent comment and decorator lines. The upgrade is a tree-sitter outline: the model picks block ids, and ranges snap to syntax nodes.

## 3. Finding edges

| Option | Notes |
|---|---|
| LSP call hierarchy (`prepareCallHierarchy`, `outgoingCalls` with `fromRanges`, since 3.16) | needs a server per language. [multilspy](https://github.com/microsoft/multilspy) 0.1.1 downloads servers itself, but its high-level API has no call hierarchy |
| SCIP (scip-typescript 0.4.0, scip-python 0.6.6; repo moved to [scip-code](https://github.com/scip-code/scip)) | each project must build; the proto says a definition's `enclosing_range` should include its docs |
| stack-graphs | [archived](https://github.com/github/stack-graphs), last push 2025-09-09 |
| ctags + grep | uctags is not installed, and it gives no JS/TS end lines |
| ast-grep or tree-sitter call sites | names only; good as hints |
| Agent reads the code, script checks the callee name is in the caller's range | no setup |

ast-grep (`call_expression`, `new_expression`) found `L18 computeTotal, L19 this.repo.save, L28 new OrderService, L29 svc.create`. The validator rejected a false edge: `b5->b7 (OrderId): name not in caller range`.

**Recommendation.** The agent declares the edges, and a word-boundary name check validates them. Upgrade: tree-sitter call sites suggest missed edges.

## 4. Layout

| Library | Version | Size, raw / gzip | Nested containers | Notes |
|---|---|---|---|---|
| [elkjs](https://github.com/kieler/elkjs) | 0.12.0 | `elk.bundled.js` 1.61 MB / 467 KB | yes (`hierarchyHandling: INCLUDE_CHILDREN`) | jsDelivr/unpkg only; EPL-2.0 OR GPL-3.0+ |
| @dagrejs/dagre | 3.1.1 | 49 KB / 17 KB | compound | crashes on node id `constructor`; cdnjs has only 0.8.5 |
| @viz-js/viz (Graphviz 16.1.0) | 3.31.0 | 1.33 MB / 480 KB | clusters | sizes in inches, positions in points |
| @hpcc-js/wasm-graphviz | 1.29.2 | 815 KB / 632 KB | clusters | same model |
| cytoscape + cytoscape-elk | 3.34.4 + 2.3.0 | 436 KB + 11 KB, plus ELK | via ELK | only `canvas` and `null` renderers, so code would not be DOM text |

Checks:
- **ELK** sized the class container from its children, routed edges into a nested method, and gave identical boxes in Node and headless Chrome.
- **dagre** threw `TypeError: Cannot convert undefined or null to object` on a node named `constructor`.

**Recommendation.** Use elkjs, with opaque ids (`b1`).

## 5. Hand-drawn look

[rough.js](https://github.com/rough-stuff/rough) 4.6.6 is MIT, released 2023-11-20. `bundled/rough.js` is 27.7 KB (8.9 KB gzip). cdnjs only has 3.1.0, so vendor it.
- **API:** `rough.svg(svg)` methods return a `<g>`: `rectangle(x,y,w,h,opts)`, `curve(points)`, `path(d)`, `linearPath`.
- **Defaults** (from the bundle): roughness 1, bowing 1, strokeWidth 1, curveFitting 0.95.
- **Arrowheads:** none built in. Draw two `linearPath` strokes along the end tangent.
- **Seed:** give each element a fixed `seed`, so redraws keep the same wobble.

**Recommendation.** Draw borders and arrows in an SVG layer, and put the code in HTML `<pre>` boxes on top so it stays crisp. A prototype screenshot confirmed the look.

## 6. Syntax highlighting

| Option | Version | Size for TS/JS/Py/Go/Java | Coverage |
|---|---|---|---|
| highlight.js | 11.12.0 | one file, 129 KB / 44 KB | 36 languages in the default build |
| Prism | 1.30.0 | about 20 KB; load components in dependency order | 298 component files |
| Shiki | 4.5.0 | ESM only; grammars 535 KB, core 50 KB, plus 622 KB WASM or the JS engine | VS Code grammars |
| Pygments | 2.21.0 | no JS; CSS 5.1 KB; HTML is 5–9× the source | 602 lexers; needs pip |

**Recommendation.** Inline highlight.js. Pygments is optional once a venv exists. Mark diff lines with absolutely positioned row overlays, so the highlighted HTML is never split.

## 7. Pan, zoom, drag

| Option | Min / gzip |
|---|---|
| panzoom 9.4.4 | 33.8 / 9.2 KB |
| @panzoom/panzoom 4.6.2 | 10.1 / 3.9 KB |
| svg-pan-zoom 3.6.2 (SVG only) | 29.8 / 8.3 KB |
| Hand-rolled | about 15 lines |

**Recommendation.** Hand-roll it.
- **Pan and zoom:** one `translate() scale()` on a world `div` that holds the SVG layer and the code boxes. The wheel zooms around the cursor, and dragging the background pans.
- **Dragging a box:** move it by the pointer delta divided by the scale. Then redraw only its edges, between side anchors, with the same seeds.

## 8. Excalidraw output

Sources (master `4c37956`): [json-schema.mdx](https://github.com/excalidraw/excalidraw/blob/master/dev-docs/docs/codebase/json-schema.mdx), [types.ts](https://github.com/excalidraw/excalidraw/blob/master/packages/element/src/types.ts), [restore.ts](https://github.com/excalidraw/excalidraw/blob/master/packages/excalidraw/data/restore.ts), [constants.ts](https://github.com/excalidraw/excalidraw/blob/master/packages/common/src/constants.ts).

**Top level.** `{type:"excalidraw", version:2, source, elements, appState, files}`.

**Base fields.** `id type x y width height angle strokeColor backgroundColor fillStyle strokeWidth strokeStyle roughness opacity roundness seed version versionNonce index isDeleted groupIds frameId boundElements updated created link locked`.

**Minimum.** `restore()` defaults almost every field. In practice you need `type`, the geometry, `text` for text, and `points` for arrows. Emit everything anyway.

**Text in a box.** Set `text.containerId = rect.id`, and add `{type:"text", id}` to `rect.boundElements`. Bound text wraps, so size the box to the longest line.

**Arrows.** Master uses `startBinding`/`endBinding = {elementId, fixedPoint:[ratio x, y], mode:"orbit"|"inside"|"skip"}`. The older `{elementId, focus, gap}` form is migrated. Both shapes list the arrow in `boundElements`. `points` are relative to the arrow and start at `[0,0]`.

**Class container.** Use a shared `groupIds` entry (it keeps the rough rectangle). The alternative is a `frame` element: children set `frameId` and sit just below the frame in the array, and the frame can clip them.

**Monospace font.** `fontFamily` 3 is Cascadia. It is crisper but marked `deprecated`. 8, Comic Shanns, is the non-deprecated monospace family.

**From Python.** Use stdlib `json`. Width is characters × fontSize × 0.6, and height is lines × fontSize × lineHeight.

**Validation.** Python generated a 7-element file and a 20-element file. I loaded both with @excalidraw/excalidraw 0.18.1 `restore()` and `loadFromBlob()` (the app's open-file path), using esbuild, jsdom and a canvas stub.

```
restored elements: 20 of 20 | deleted: 0
bindings kept 12, lost 0; bound texts kept 6, lost 0
loadFromBlob (file-open path): 20 elements; bg #1e1e1e
bad type rejected: Error: invalid file
```

`restore` changed only `index`, `version`, `versionNonce` and `updated`, plus `lastCommittedPoint` on arrows.

**Opening.**
- excalidraw.com: open the file.
- VS Code: the [extension](https://github.com/excalidraw/excalidraw-vscode) `pomdtr.excalidraw-editor` 3.9.3 opens `*.excalidraw` and bundles ^0.18.1, the version validated here.
- Obsidian: the [plugin](https://github.com/zsviczian/obsidian-excalidraw-plugin) treats `.excalidraw` as a legacy format next to its Markdown-based drawings.

### One tree.json for both renderers: yes

```json
{"blocks":[{"id":"b4","file":"orders.ts","start":16,"end":20,"kind":"method","name":"create","parent":"b2"}],
 "edges":[{"from":"b4","to":"b5","kind":"calls"}]}
```

The flow was tree.json, then the validator, then a stdlib ELK-graph builder (sizes come from snippet text).
- **HTML:** one 1.77 MB file with the tree, ELK, rough.js and highlight.js inlined. Opened from `file://` in headless Chrome, it reported `OK boxes=7 paths=19 hl=19`.
- **Excalidraw:** the same tree.json and ELK layout produced the validated 20-element file.

Save `tree.json` in each breakdown directory.

## 9. PR input

- `gh pr diff` 2.95.0 has no context-lines flag. Get the SHAs with `gh pr view N --json baseRefOid,headRefOid`.
- `git diff -U0 base...head` diffs from the merge-base. Parse `@@ -a,b +c,d @@`.
- Map removed lines to blocks in the base text (`git show <merge-base>:path`), and added lines to head blocks. A fully covered block is deleted or added; otherwise it is modified.

Check (throwaway repo):

```
base: OrderId       L9-9   deleted  lines -[9]
base: computeTotal  L23-25 modified lines -[24]
head: computeTotal  L21-24 modified lines +[22, 23]
head: audit         L31-33 added    lines +[31, 32, 33]
```

Inside a box, show the head text with `+` row overlays and the removed base lines interleaved.

## 10. Minimal dependency set for v1

- **Python 3.9+ stdlib scripts:** cut and validate, ELK graph, HTML writer, Excalidraw writer.
- **Vendored and inlined:** elk.bundled.js 0.12.0, rough.js 4.6.6, highlight.js 11.12.0 and a dark theme. That is about 1.8 MB per HTML file.
- **git and gh** for PRs.
- **node, only for Excalidraw layout.** It runs `require()` on the vendored ELK with no npm install. Without node, fall back to a Python column layout (untested).

Can wait: a tree-sitter venv, Pygments, ast-grep, LSP/SCIP and Graphviz.

## 11. Risks and unknowns

- The validator is a heuristic. Regex literals, template-string braces and the comment-snap rule are untested.
- The name check misses same-name targets and dynamic dispatch.
- tree-sitter needs a node-type map per language.
- universal-ctags and the SCIP indexers were not run. Their claims come from reading source.
- ELK adds 1.6 MB to each file. Check that its EPL/GPL licence allows vendoring.
- The Excalidraw check covered only 0.18.1. Master's handling of v2 bindings comes from reading `restore.ts`. The 0.6 em width estimate may re-wrap text.
- Pan, zoom and drag were not exercised interactively.
- rough.js has had no release since 2023.
