# Research summary

Researched 2026-10-18. Each track has a full report with sources:

| Report | Question |
|---|---|
| [00-reel.md](00-reel.md) | What the graphicule.dev reel shows, and what this project took from it |
| [01-pain.md](01-pain.md) | Is reading AI-written code a real pain, and where do readers get lost? |
| [02-prior-art.md](02-prior-art.md) | Who has drawn code as a map or a guided tour, and why did those tools fade? |
| [03-skill-craft.md](03-skill-craft.md) | How to build, invoke and test a Claude Code skill like this one |
| [04-building-blocks.md](04-building-blocks.md) | Which parsers, layout, drawing and file formats to use, tested on this machine |

## Bottom line

- **The pain is real and measured, and a tool can fix the reading order.** Reviewers miss more when they read in the wrong order. GitHub shows a PR's files alphabetically, not in call order.
- **No shipping tool does this.** Nothing that runs inside a coding agent shows the real code, cut at declaration boundaries, joined by arrows checked against the code. Etchpad comes closest, and it is an unreleased standalone editor.
- **The build is small.** It needs stdlib Python 3 scripts, three vendored JavaScript files, and git and gh for PRs.

## The pain (01)

- 66% of Stack Overflow's 2025 respondents cite AI output that is "almost right, but not quite". In Sonar's 2026 survey, 96% don't fully trust AI code and 38% say it takes more effort to review than human code.
- AI PRs are bigger and slower to land. Faros measured PR size up 154% in 2025. LinearB found 32.7% of AI PRs merged within 30 days, against 84.4% of manual ones.
- Order changes what reviewers catch. Files shown earlier in a PR get more comments. In a 106-person experiment, reviewers had 64% lower odds of finding one of the two seeded defect types when its file came last (Fregnan et al., ESEC/FSE 2022).
- Polish lowers the reviewer's guard, which the CMU study calls "surface plausibility". The output must not add more polish.
- AI prose pushed into a review gets distrusted, because it is confident and nobody can check it. Explanations a reader asks for do help: 66% in Sonar's survey rate AI explanations of existing code effective. So the skill pushes structure and leaves questions to the chat.
- Simon Willison makes Claude include snippets with `sed`, `grep` or `cat` so it never retypes code. That is this skill's central rule, reached independently.
- Counter-evidence: code-level differences between AI and human code look small, and Haystack found a full code canvas "too confusing for code reviews".

## Prior art (02)

- **graphicule.dev redirects to etchpad.ai** (checked with curl). Etchpad is a waitlist-only "Spatial Code Editor" written in Rust. It maps whole codebases and overlays PRs.
- **Debugger Canvas** (Microsoft Research, 2012) is the closest tool that shipped: real code per called method, with arrows left to right. Users liked it for long call chains. They missed field definitions and found it not worth the hassle on normal projects.
- **Why canvas tools faded:**
  - they replaced the editor;
  - they needed an indexer per language;
  - they grew into hairballs;
  - users had to arrange the boxes by hand;
  - the output went stale;
  - they couldn't find enough paying customers.
- **The 2025–2026 AI review tools** (CodeRabbit, Devin Review, cubic, Windsurf Codemaps, Warp's pr-walkthrough skill) order a change by flow. They show summaries, links or model-grouped diff hunks, not verbatim blocks with checked edges.

## Building the skill (03)

- **Location:** one personal skill, `/breakdown`, kept in this repo and linked into `~/.claude/skills/`. Package it as a plugin only when sharing it. Doing both would load the skill twice.
- **Arguments:** read the whole request from `$ARGUMENTS`. Numbered arguments would split `POST /orders` in two. Add the Excalidraw file only when the request says `--excalidraw` or names Excalidraw.
- **Scripts:** reference them as `python3 ${CLAUDE_SKILL_DIR}/scripts/...`. Pre-approve that command in `allowed-tools`, one command per call. Scripts report errors as JSON with a concrete fix, and the model loops: check, fix, check, render.
- **HTML safety:** escape `<` in the data embedded in the page, so a snippet containing `</script>` can't break it.
- **Triggering:** trigger on "break down", "walk through" or "show the flow of" a file, route or PR. Don't trigger on a bare "explain this code", which collides with `explain-frontend` and `/code-review`.
- **Testing:** run the same targets with and without the skill in fresh sessions. A script re-cuts every snippet and compares it character for character. Another check fails the run if an Excalidraw file appears unasked.

## Building blocks (04)

| Part | Choice | Checked |
|---|---|---|
| Blocks | The model picks line ranges. A stdlib validator rejects ranges outside the file, unbalanced brackets and cut-off Python bodies, and snaps a block upward over its comments and decorators. tree-sitter is the later upgrade. | Rejected a bad range and an unbalanced block |
| Edges | The model declares them. A script checks that the called name appears inside the caller's block. | Rejected a false edge |
| Layout | elkjs 0.12.0, including a class box holding its methods | Same coordinates in Node and Chrome. dagre crashed on a node named `constructor` |
| Drawing | rough.js 4.6.6 draws borders and arrows in SVG. Code sits in HTML boxes on top, so it stays sharp. | Prototype rendered |
| Highlighting | highlight.js 11.12.0: one file, 129 KB, 36 languages | |
| Pan, zoom, drag | About 15 hand-written lines | Not tried interactively |
| Excalidraw | Written by stdlib Python from the same `tree.json` | Two files opened intact in Excalidraw 0.18.1 (the VS Code extension's version) |
| PRs | `git diff -U0 base...head`, plus `git show` for the base version | Added, modified and deleted blocks mapped correctly |

## Checked by hand

- **Fregnan et al., ESEC/FSE 2022:** the abstract says "64% lower odds to identify it when its file is last as opposed to first". This applies to one of two defect types, with 106 participants.
- **Baum, Schneider & Bacchelli, ICSME 2017 (full text):**
  - 111 of 130 survey respondents (85%) rated bottom-up best, but only for a change where one callee had four callers.
  - Many interviewees preferred top-down, and the authors call the direction of call flow "more subjective".
  - For a declaration and its use, the preferred direction is declaration before use.
  - 112 of 130 (86%) rated an order with no sensible rule among the worst.
  - Principle 5: the closest distance between two related parts is "visible on the screen at the same time".
  - Principle 3: when grouping and direction conflict, grouping wins (82 of 119 respondents).
- **Haystack's co-founder, Hacker News, 2025-09-11:** "we found that it was too confusing for code reviews. The main issue was just how alien the interface is!"

## What the research changes in the design

1. **Types can sit beside the first block that uses them** (Baum: declaration before use, both visible together). After comparing both layouts on a FastAPI endpoint, the reel's final Data column stayed the default ("column"), and types-beside became the "beside" option.
2. **The main path holds about 12 boxes.** The rest folds into named branches that open on click.
3. **Layout is automatic and runs in one direction.** Dragging a box is allowed but never needed (Patchworks, CHI 2014: arranging boxes by hand cost time).
4. **Every snippet is cut by a script and every arrow is checked** against the code. The reel drew a wrong arrow on a 60-line file.
5. **Labels are 2–3 word roles** such as "Entry point" or "Writes DB". There is no summary prose and no evaluative words.
6. **PRs are shown in call order.** Changed blocks follow the call path, and unchanged neighbours are dimmed. The PR title and description are quoted verbatim at the root as "Author's claim", never generated.
7. **The canvas prints its ordering rule and its blind spots.** Runtime order, invariants and failure behaviour are not checked.

## Decided after research

- **Layout is computed in Python, not elkjs.** One flow is small (16 blocks or so), so a layered layout written for this case is enough. Both outputs share its coordinates. That removes node, keeps each `canvas.html` near 225 KB instead of 1.8 MB, and avoids elkjs's licence question.
- **Excalidraw output uses the same layout,** written as plain JSON. Excalidraw 0.18.1's own loader restores every element and keeps every arrow binding.

## Later versions

- Markers for dead code, near-duplicates, error handling and "writes" arrows.
- Folding parts of a large flow on the canvas.
- tree-sitter parsing to snap ranges to exact syntax nodes.
