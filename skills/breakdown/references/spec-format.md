# spec.json reference

The spec lists blocks of code by file and line range, and the arrows between them. You never put code in it. `breakdown.py check` validates it against the files; `breakdown.py render` checks again and draws it.

## Top level

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | `file`, `endpoint` or `pr`. It names the output folder and the header |
| `title` | yes | What the user asked for: `src/loans.ts`, `POST /orders`, `PR #42: Add coupons` |
| `entry` | yes | Block ids where reading starts, in order. Usually one; a file with several independent exported functions can list each |
| `blocks` | yes | The blocks, below |
| `edges` | no | The arrows, below |
| `pr` | no | Pull request number. The render fetches its title and description with `gh` and shows them verbatim |
| `base` | no | Git ref the change is compared against: a branch name or a sha. Turns on change markers. Without `pr`, the canvas quotes the commit messages between `base` and `head` as the author's claim |
| `head` | no | Git ref the blocks are read from. Leave it out to read the working tree |

## Blocks

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | The declaration's name, no spaces. Methods: `Class.method`. Must be unique |
| `file` | yes | Path from the repository root, forward slashes |
| `start`, `end` | yes | 1-based, inclusive. Cover the whole declaration |
| `role` | no | `code` (default); `type` for data shapes and error types (interfaces, type aliases, enums, schemas, ORM models, exception classes); `container` for a class whose methods are separate blocks |
| `parent` | no | For a method: the id of its container |
| `name` | no | The identifier to look for when it differs from the last part of `id`. Needed for anonymous handlers: an Express `router.post("/orders", async (req, res) => ...)` can be `{"id": "post_orders", "name": "post", ...}` |
| `label` | no | Two to four words, at most 32 characters, naming the block's role |
| `side` | no | `base` for code the change deletes; it is read from the base version. Needs `base` at the top level |
| `no_bracket_check` | no | `true` skips the bracket count for a block where a regex literal or odd string confuses it. Use only after reading the lines yourself |

What the check does to each block:

- Moves `start` up over decorators, attributes and doc comments directly above it, and reports that as a fix.
- Requires the block's name in its first lines (after decorators and comments). If it is not there, the error gives the line where the declaration really is.
- For Python, requires the block to end where the indented body ends: not before, not into the next declaration. The error gives the right `end`.
- For brace languages, requires brackets to balance once strings and comments are skipped. An unclosed block gets the line where it really closes. A block that seems to continue past its declaration into the next one gets a warning with the line to end at.
- Rejects blocks that overlap, unless one is the other's parent, and methods that sit outside their container's lines.

## Containers

A class drawn as a frame around its methods, as in this example:

```json
{"id": "Catalog", "file": "src/loans.ts", "start": 23, "end": 42, "role": "container"},
{"id": "Catalog.constructor", "file": "src/loans.ts", "start": 24, "end": 24, "parent": "Catalog"},
{"id": "Catalog.find", "file": "src/loans.ts", "start": 26, "end": 32, "parent": "Catalog"}
```

The frame shows the class's own lines above its first method (the declaration and any fields) and a closing brace. Methods inside are ordered by the calls between them. One level only: a container cannot sit inside another.

Give the constructor its own block only when other chosen methods read what it sets. In the example, `find` reads `this.books`, so `find -> Catalog.constructor` with `"via": "this.books"`. Otherwise leave it out, and its lines show in the class header.

When a class is only data (a dataclass, a pydantic model, an ORM model, an interface), make it one block with `"role": "type"` instead.

## Edges

| Field | Required | Meaning |
|---|---|---|
| `from` | yes | The block whose code mentions the target |
| `to` | yes | The block it calls or uses |
| `kind` | no | `calls` (default when the target is code) or `uses` (default when the target is a type) |
| `via` | no | The exact text in the source block that reaches the target, when the target's name is not it: `"this.books"`, `"new Catalog("`, `"self.repo.save"` |

The check finds the first line in the source block that contains the evidence (the target's name, or `via`). The arrow leaves the canvas from that line. With no match, the arrow is refused.

Which arrows to draw:

- **Calls:** every call from one chosen block to another.
- **Type uses:** every chosen type whose name appears in the block, whether in a signature, an annotation, a construction, `isinstance`, `raise` or `except`. Reading a type's fields without naming the type is not a use.
- **Types that name other types:** `Order` uses `OrderItem`.
- **Not:** relations that exist only as strings, such as `ForeignKey("products.id")` or a dependency-injection token.
- **Classes:** when a block calls a method of a drawn class, the arrow goes to that method. Never draw an arrow between a method and its own container.

## Hints

`check` prints two kinds of hint. Neither stops the render.

- **A name with no arrow:** a block mentions another chosen block but has no arrow to it. Add the arrow when the code uses it. Short lowercase names (under 5 characters with no underscore, such as `find` or `save`) are too common to hint, so check calls to them yourself.
- **A declaration with no block:** a block mentions a function or class declared in one of the files you already use, but no block covers it. Add it, or leave it out on purpose and list it under "Left out" in your reply. Declarations in files you have not used yet are not checked, so follow every call yourself.

## Changes

With `base` set, the render compares each block with the merge base:

- Added lines get a `+` gutter.
- Lines that were removed or replaced appear in place, marked `−`, cut from the base version.
- Each box is marked new, changed, same (dimmed) or deleted.
- An arrow that leaves a changed line always shows, even when it is a type's second use.

## Reading order and layouts

The render follows calls depth-first from each entry, in the order the calls appear in the code. Each type belongs to the first block that mentions it.

- **column** (default): code in columns by call depth, then every type in a final Data column, grouped by first use.
- **beside** (`--beside`): each type sits under the first block that mentions it.

Code that is never reached from an entry is drawn as its own start, and the render prints a warning. Fix the arrows or add it to `entry`.

## Output

`render` writes `.breakdown/<date>-<kind>-<slug>/` at the repository root:

- `canvas.html`: one standalone file, works offline. It holds the repository's local path for the VS Code links.
- `tree.json`: the checked blocks, arrows and both layouts.
- `spec.json`: the spec as you wrote it. To draw it again later, run `render` on this copy.
- `breakdown.excalidraw`: only with `--excalidraw`. Opens at excalidraw.com or in the VS Code Excalidraw extension.

The repository root is the folder that holds `.breakdown/` when the spec lives there. Otherwise it is the git root of the current folder; `--root` overrides both.

It also adds `.breakdown/` to `.git/info/exclude` the first time. That is its only write outside `.breakdown/`; `--no-exclude` skips it.

One canvas reads well up to about 16 blocks. `check` warns above 20 and refuses above 40.

## Exit codes

`0` ok. `1` the spec needs fixing: read `errors[].fix`. `2` the command could not run (missing spec file, git failure).
