---
name: breakdown
description: Use when someone asks to break down, trace, walk through, or show the flow of a specific file, HTTP endpoint or route, pull request or branch, and wants the real code laid out in call order instead of an explanation; also when they ask for a code storyline, a flow canvas, or an Excalidraw drawing of specific code.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/breakdown.py *) Bash(gh pr view *) Bash(git fetch *) Bash(git diff *) Bash(git show *) Bash(git grep *) Bash(git log *) Bash(git merge-base *) Bash(git rev-parse *)
---

# Breakdown

Turn a file, an endpoint or a change into a canvas of the real code: the entry point first, then what it calls in call order, then the types they use. The canvas is the answer. You do not explain the code.

**You never type code into the output.** You choose blocks as file and line ranges, and declare the arrows between them. The script cuts the text out of the files and refuses any range or arrow that does not match the code.

Request: $ARGUMENTS

The script is `${CLAUDE_SKILL_DIR}/scripts/breakdown.py`. If that path still shows `${CLAUDE_SKILL_DIR}`, use `scripts/breakdown.py` in the folder that holds this SKILL.md. Run it with `python3` (or `python` where that is the name), one command per call. Give it the absolute path of the spec; it finds the repository from there, so no `cd` is needed.

## Steps

1. **Read the request.**
   - Target: a path is a **file**; `METHOD /path` is an **endpoint**; `#123`, a PR URL or a branch name is a **change**. With no target in the request, take it from the conversation, or ask.
   - `--excalidraw` or the word Excalidraw: add `--excalidraw` when you render, now and for follow-ups.
   - `--beside` or "types next to the code": add `--beside`.
2. **Find the entry point.**

   | Target | Entry point |
   |---|---|
   | File | The function or functions in the file that nothing else in the file calls; exported or public ones first |
   | Endpoint | The handler registered for that method and path. Patterns per framework: [references/entry-points.md](references/entry-points.md) |
   | Change | Follow [references/pull-requests.md](references/pull-requests.md); for a change, its rules for choosing blocks come first |

3. **Choose blocks.** Read from the entry point and follow every call into the repository's own code. One block per declaration: a function, a method, or a type. Stop at framework and library code.

   The canvas reads best with 16 blocks or fewer, so trim to 16. The check warns above 20. Leave out, in this order: exception classes, small enums and constants, helpers that only compute a value, then types used by a single block. Never leave out the entry point, or the calls that lead to a write (database, network, file, queue) together with the types that write stores.
4. **Write `<repository root>/.breakdown/spec.json`**, in the format below.
5. **Check:** `python3 <script> check <root>/.breakdown/spec.json`. Each error carries a `fix`; apply it and check again until `"ok": true`. Then read the hints. Some name a block that mentions another block with no arrow drawn: add the arrow when the code uses it. Others name a declaration in a file you already use that no block covers: add the block, or leave it out on purpose.
6. **Render:** `python3 <script> render <root>/.breakdown/spec.json --open`, adding `--excalidraw` or `--beside` when step 1 says so. Leave out `--open` on a machine with no display.

   The first render also adds `.breakdown/` to `.git/info/exclude`. When the user wants nothing written outside `.breakdown/`, add `--no-exclude`; `.breakdown/` then shows as untracked in `git status`.
7. **Reply** with these lines and nothing more:
   - the path to `canvas.html`, and on its own line the path to `breakdown.excalidraw` when you made one;
   - `<N> blocks, <M> arrows, starting at <entry>`;
   - `Left out: <names>`, listing the functions, methods and types the flow reaches that you did not draw;
   - one line for each warning the render printed.

   With nothing left out and no warnings, the reply is the path lines and the counts. The user asks follow-up questions in the chat; the canvas carries no commentary.

## spec.json

```json
{
  "kind": "endpoint",
  "title": "POST /invoices",
  "entry": ["create_invoice"],
  "blocks": [
    {"id": "create_invoice", "file": "billing/api.py", "start": 21, "end": 34, "label": "Entry point"},
    {"id": "InvoiceService", "file": "billing/service.py", "start": 8, "end": 40, "role": "container"},
    {"id": "InvoiceService.issue", "file": "billing/service.py", "start": 15, "end": 27, "parent": "InvoiceService", "label": "Writes DB"},
    {"id": "InvoiceService.next_number", "file": "billing/service.py", "start": 29, "end": 40, "parent": "InvoiceService"},
    {"id": "Invoice", "file": "billing/models.py", "start": 12, "end": 20, "role": "type", "label": "invoices table"}
  ],
  "edges": [
    {"from": "create_invoice", "to": "InvoiceService.issue"},
    {"from": "InvoiceService.issue", "to": "InvoiceService.next_number"},
    {"from": "InvoiceService.issue", "to": "Invoice"}
  ]
}
```

- `kind` is `file`, `endpoint` or `pr`. `title` is what the user asked for, such as `POST /orders` or `feature/coupons vs main`.
- `id` is the name in the code; a method is `Class.method`. `file` is the path from the repository root. `start` and `end` are the 1-based lines of the whole declaration; the check pulls in decorators and doc comments above it.
- `role`: leave it out for code. Use `type` for data shapes and error types: interfaces, type aliases, enums, schemas, ORM models, exception classes. Use `container` for a class whose methods you list as separate blocks, each with `"parent"`.
- A constructor gets its own method block only when other chosen methods read what it sets; otherwise its lines show in the class header.
- `label` is optional: two to four words naming the block's role, such as Entry point, Reads DB, Writes DB, Commits, Calls API, Changes state, Request body, Response, Error type, orders table. The check rejects judging words such as robust or clean.
- `edges` go from the block whose code names the target:
  - Draw one for each call, and for each type named in a signature, annotation, construction, `raise` or `except`.
  - A quoted forward reference such as `list["OrderLine"]` names the type.
  - Reading a type's fields without naming the type is not a use.
  - When a block names a class and also calls one of its methods, draw only the arrow to the method.
  - Skip relations that exist only as plain strings, such as `ForeignKey("products.id")` or a route name.
  - When the code reaches a block under another spelling, add `"via"` with the exact text, such as `"via": "this.books"` or `"via": "new Catalog("`; a field read this way draws as a call arrow.
  - Mentions in comments and docstrings never count.
- Every field and every check: [references/spec-format.md](references/spec-format.md).

## Before replying

- Every line of code on the canvas was cut by the script; none came from you.
- The entry point comes first in `entry`, and every block is reached from it or listed as another entry.
- Every call and type use between chosen blocks has an arrow, and every hint is resolved or named under "Left out".
- Labels name roles, never qualities.
- The reply is the paths, the counts, what you left out and the warnings.
