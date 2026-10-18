---
name: breakdown
description: Use when someone asks to break down, trace, walk through, or show the flow of a specific file, HTTP endpoint or route, pull request or branch, and wants the real code laid out in call order instead of an explanation; also when they ask for a code storyline, a flow canvas, or an Excalidraw drawing of specific code.
argument-hint: "<file | METHOD /path | #PR | branch> [--excalidraw] [--beside]"
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/breakdown.py *) Bash(gh pr view *) Bash(git fetch *) Bash(git diff *) Bash(git show *) Bash(git log *) Bash(git merge-base *) Bash(git rev-parse *)
---

# Breakdown

Turn a file, an endpoint or a change into a canvas of the real code: the entry point first, then what it calls in call order, then the types they use. The canvas is the answer. You do not explain the code.

**You never type code into the output.** You choose blocks as file and line ranges, and declare the arrows between them. The script cuts the text out of the files and refuses any range or arrow that does not match the code.

Request: $ARGUMENTS

The script is `${CLAUDE_SKILL_DIR}/scripts/breakdown.py`. If that path still shows `${CLAUDE_SKILL_DIR}`, use `scripts/breakdown.py` in the folder that holds this SKILL.md. Run it with `python3` (or `python` where that is the name), one command per call, from the repository root.

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
   | Change | Follow [references/pull-requests.md](references/pull-requests.md) |

3. **Choose blocks.** Read from the entry point and follow every call into the repository's own code. One block per declaration: a function, a method, or a type. Stop at framework and library code.

   Aim for 16 blocks or fewer; the check warns above 20. When the flow is bigger, leave out in this order until it fits: exception classes, small enums and constants, helpers that only compute a value, then types used by a single block. Never leave out the entry point or anything on the path to a write (database, network, file, queue).
4. **Write `.breakdown/spec.json`** at the repository root, in the format below.
5. **Check:** `python3 <script> check .breakdown/spec.json`. Each error carries a `fix`; apply it and check again until `"ok": true`. Then read the hints. Some name a block that mentions another block with no arrow drawn: add the arrow when the code uses it. Others name a declaration in a file you already use that no block covers: add the block, or leave it out on purpose and say so in your reply.
6. **Render:** `python3 <script> render .breakdown/spec.json --open`, plus `--excalidraw` or `--beside` when step 1 says so. The first render in a repository also adds `.breakdown/` to `.git/info/exclude`; add `--no-exclude` when the user wants nothing written outside `.breakdown/`.
7. **Reply** with these lines and nothing more:
   - the path to `canvas.html`, and to `breakdown.excalidraw` when you made one;
   - `<N> blocks, <M> arrows, starting at <entry>`;
   - `Left out: <names>` when you left anything out;
   - one line for each warning the render printed.

   With nothing left out and no warnings, the reply is the first two lines. The user asks follow-up questions in the chat; the canvas carries no commentary.

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
- `label` is optional: two to four words naming the block's role, such as Entry point, Reads DB, Writes DB, Commits, Calls API, Request body, Response, orders table. The check rejects judging words such as robust or clean.
- `edges`:
  - Draw one from a block to every chosen block whose name appears in it: each call, and each type it names in a signature, annotation, construction, `raise` or `except`. Reading a type's fields without naming the type is not a use.
  - When a block calls a method of a drawn class, the arrow goes to the method, not the class.
  - Skip relations that exist only as strings, such as `ForeignKey("products.id")`.
  - When the code reaches a block under another spelling, add `"via"` with the exact text, such as `"via": "this.books"` or `"via": "new Catalog("`.
- Every field and every check: [references/spec-format.md](references/spec-format.md).

## Before replying

- Every line of code on the canvas was cut by the script; none came from you.
- The entry point comes first in `entry`, and every block is reached from it or listed as another entry.
- Every call and type use between chosen blocks has an arrow, and every hint is resolved or named under "Left out".
- Labels name roles, never qualities.
- The reply is the paths, the counts, what you left out and the warnings.
