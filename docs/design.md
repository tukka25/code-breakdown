# code-breakdown: design

Status: v1, October 2026.

## What it is

A skill for coding agents (Claude Code, Codex) that turns a file, an HTTP endpoint or a pull request into a **storyline of the real code**. It shows the entry point first, then what it calls in call order, then the types it uses, drawn as boxes and arrows on a canvas. It does not write an explanation of the code.

The idea comes from a graphicule.dev reel (2026-10-06): parse code into blocks at declaration boundaries, then lay the blocks out in the order a reader needs them. [research/README.md](research/README.md) records why each choice below was made.

## The rule everything rests on

**The model never types code into the output.** It chooses blocks as `file:start-end` ranges and declares the arrows between them. A bundled script cuts the text out of the files, rejects ranges that miss their declaration, and rejects arrows whose target name does not appear in the source block. So a box can't contain paraphrased or invented code, and an arrow can't claim a call that isn't in the code.

## Inputs

| Target | How the user asks | Entry point |
|---|---|---|
| File | `/breakdown src/loans.ts` | The function or functions in the file that nothing else in the file calls |
| Endpoint | `/breakdown POST /orders` | The handler registered for that method and path |
| Pull request | `/breakdown #123`, a PR URL, or a branch name | The highest changed functions on each call path |

Options:

- `--excalidraw`, or naming Excalidraw in the request, also writes `breakdown.excalidraw`.
- `--beside`, or asking for types beside their code, opens the canvas in layout A instead of B.

## Output

Each run writes one folder in the repository being analysed. Re-running the same target on the same day replaces that folder.

```
.breakdown/2026-10-18-endpoint-post-orders/
  canvas.html            always; one standalone file that works offline
  tree.json              the checked blocks, arrows and both layouts
  spec.json              the spec as written, so it can be rendered again
  breakdown.excalidraw   only when asked
```

The first run adds `.breakdown/` to `.git/info/exclude`, so breakdowns stay out of commits without touching `.gitignore`.

## The canvas

- **Look:** a dark canvas, light under a light system theme. Boxes and arrows are hand-drawn with rough.js, and the code is crisp JetBrains Mono with syntax colours. Labels use Barlow Condensed and the interface uses Barlow. All three fonts and rough.js are embedded, so the file needs no network.
- **Layout B, the default:** columns by call depth, read left to right. Each callee starts level with its caller. Every type sits in a final "Data" column, with its own component types indented under it.
- **Layout A:** the same boxes, but each type sits under the first block that mentions it. A toggle switches layouts with an animation, and both layouts are computed when the file is generated.
- **A box** shows the verbatim lines, a `file:start-end` caption that opens the file in VS Code, its place in the reading order, and an optional label of two to four words. A class whose methods are separate blocks becomes a container drawn around its methods.
- **An arrow** leaves from the line that mentions its target. Calls are solid, and type uses are dashed. A type use other than the first one is hidden until you click a box.
- **Interaction:**
  - drag to pan; zoom with a pinch, Ctrl or Cmd and the scroll wheel, or the buttons;
  - click a box to trace everything it touches and highlight the lines involved;
  - step through the reading order with ◀ ▶ or the arrow keys.
- **The canvas prints its ordering rule and its blind spots.** It does not show runtime order, dynamic dispatch, behaviour on failure, or tests.
- **For a pull request or a branch:**
  - Added lines get a `+` gutter.
  - Lines the change removed or replaced are shown in place, marked `−`, and cut from the merge base.
  - Each box gets a status: new, changed, same (dimmed), or deleted. A deleted box is cut from the merge base.
  - Arrows leaving a changed line always show.
  - "Author's claim" quotes the PR title and description, or the branch's commit messages when there is no PR. The skill never writes its own summary.

## The spec the model writes

The model writes `.breakdown/spec.json`:

```json
{
  "kind": "endpoint",
  "title": "POST /orders",
  "entry": ["create_order"],
  "blocks": [
    {"id": "create_order", "file": "app/api/orders.py", "start": 14, "end": 26, "label": "Entry point"},
    {"id": "place_order", "file": "app/services/orders.py", "start": 13, "end": 21},
    {"id": "OrderRow", "file": "app/models.py", "start": 32, "end": 38, "role": "type"}
  ],
  "edges": [
    {"from": "create_order", "to": "place_order"},
    {"from": "place_order", "to": "OrderRow"}
  ]
}
```

Block fields:

- `id`, `file`, `start` and `end` are required.
- `role` is `code` by default. The other values are `type` for data shapes and `container` for a class whose methods are listed as blocks.
- `parent` points a method at its container.
- `name` is the identifier to look for, if it isn't the last part of `id`.
- `label` is optional.
- `side` is set to `base` for code a PR deletes.

Edge fields:

- `from` and `to` are required.
- `kind` defaults to `calls` for code targets and `uses` for types.
- `via` gives the text to look for when a reference is spelled differently, as in `new Catalog(`.

For a pull request, add `pr`, `base` and `head`.

## The script

`scripts/breakdown.py` runs on Python 3.9 or newer, using only the standard library.

- **`check spec.json`** validates and prints JSON. On failure, each error names the block, the problem, and a concrete fix. The checks:
  - each range is inside its file and its declaration line contains the block's name;
  - brackets balance, ignoring strings and comments;
  - a Python block is not cut off part-way;
  - a child sits inside its parent, and blocks do not overlap;
  - each arrow's evidence appears in its source block;
  - labels have at most four words and no judging words such as "robust" or "clean".

  As fixes, the check extends a block upward to take in its decorators and doc comments. As hints, it lists two things:
  - names that appear in a block with no arrow drawn for them;
  - declarations in the files already used that a block mentions but no block covers.

  It warns above 20 blocks and refuses above 40.
- **`render spec.json [--excalidraw] [--beside] [--open] [--no-exclude]`** runs the same checks and computes both layouts. It then writes the output folder, updates `.git/info/exclude` (unless `--no-exclude`), and prints the paths.
- **For a change:**
  - It reads blocks at the head commit.
  - It marks added lines from `git diff -U0` and inserts removed lines from the merge base, so boxes are sized with them.
  - It fetches the PR title and body with `gh`. For a branch with no PR, it uses `git log` instead.

Both layouts are computed in Python, so the HTML canvas and the Excalidraw file share the same coordinates. The Excalidraw writer uses plain JSON from the standard library. Arrows are bound to boxes, and each box's code and caption are grouped with it.

## The skill file

`skills/breakdown/SKILL.md` opens with the rule, then gives:
- a checklist: find the entry point, choose blocks, write the spec, check, fix, render, then a short reply;
- the spec format with one example;
- how to choose blocks and labels.

Details that only some runs need go in `references/`:
- the full spec reference;
- route-finding patterns per web framework;
- the PR workflow.

The description says when to use the skill, not how it works. It triggers on "break down", "trace", "walk through" or "show the flow of" a specific file, endpoint or PR. It does not trigger on a plain "explain this code".

The skill works in both agents. Claude Code replaces `${CLAUDE_SKILL_DIR}`, and the file tells other agents to use the folder that holds `SKILL.md`. `allowed-tools` pre-approves the script in Claude Code, and Codex ignores the field.

## Distribution

The repository is a Claude Code plugin marketplace with one plugin, `code-breakdown`, whose root is the repository itself. The README gives these install routes:
- **Claude Code plugin:** `/plugin marketplace add tukka25/code-breakdown`, then `/plugin install code-breakdown@code-breakdown`.
- **Personal skill:** copy or link `skills/breakdown` into `~/.claude/skills/`.
- **Codex:** copy or link it into `~/.agents/skills/`.
- **claude.ai:** upload a zip of the skill folder.

## Testing

- **Unit tests** (stdlib `unittest`):
  - spec and range checks, snapping, arrow evidence and labels;
  - layout invariants: no overlapping boxes, the entry point in the first column, types where each layout puts them, containers enclosing their children;
  - HTML escaping (a snippet containing `</script>`);
  - output naming and the git exclude;
  - Excalidraw structure and bindings;
  - PR change marking in a temporary git repository.
- **Browser smoke test:** headless Chrome loads `canvas.html` and the page reports that it rendered. The test is skipped when Chrome is missing.
- **Skill test:** a fresh agent without the skill attempts a breakdown as a baseline, then fresh agents with the skill run the same tasks. Every snippet is then compared with the source, byte for byte.

## Not in v1

- Folding parts of a large flow on the canvas. For now the skill asks for at most about 16 blocks and splits bigger flows into several canvases.
- "Writes DB" and "reads field" arrow kinds beyond labels.
- tree-sitter parsing.
- Detecting near-duplicate code.
