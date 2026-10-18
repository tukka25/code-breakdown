# 03 Skill craft

Researched 2026-10-18 (Claude Code 2.1.283).

Sources: [CC] code.claude.com/docs/en/skills; [PERM] code.claude.com/docs/en/permissions; [EVAL] code.claude.com/docs/en/plugin-evals; [BP] platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices; [OV] platform.claude.com/docs/en/agents-and-tools/agent-skills/overview; [ENG] anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills; [SPEC] agentskills.io/specification; [SCR], [DESC], [AEV], [ABP] agentskills.io/skill-creation/{using-scripts,optimizing-descriptions,evaluating-skills,best-practices}; [WS] superpowers writing-skills (obra/superpowers 6.2.0); [SC] the skill-creator skill (Anthropic); [EF] an existing hand-written skill (explain-frontend); [REPO] github.com/anthropics/skills@dbd4588 (2026-10-09).

## 1. Bottom line

- Ship `breakdown` in a `code-breakdown` plugin in this repo, symlinked into `~/.claude/skills/` for daily use [CC].
- SKILL.md opens with the rule: the model writes `spec.json` (ranges, edges) and a script cuts the text. [WS]: automate whatever is "enforceable with regex/validation".
- `$ARGUMENTS` carries the target and `--excalidraw`; output is HTML unless the flag or the word "Excalidraw" appears.
- A stdlib Python script, pre-approved in `allowed-tools`, validates the spec and renders one offline HTML file. Test against a no-skill baseline [CC, SC, EVAL].

## 2. Frontmatter reference

Claude Code ignores unknown fields silently. claude.ai and the Skills API accept only fields marked SPEC [CC].

| Field | What it does | Source |
|---|---|---|
| `name` | Command name; defaults to the folder. Spec: lowercase, hyphens, max 64 chars, equal to the folder | CC, SPEC |
| `description` | What and when; Claude matches requests against it. Max 1,024 chars | CC, SPEC, BP |
| `when_to_use` | Extra trigger text; with `description`, cut at 1,536 chars | CC |
| `argument-hint`, `arguments` | Autocomplete hint, such as `[issue-number]`; names for `$name` positions | CC |
| `disable-model-invocation`, `user-invocable` | `true` makes it user-only (description leaves context); `false` makes it Claude-only | CC |
| `allowed-tools` | Listed tools skip prompts during the invoking turn; restricts nothing | CC, SPEC |
| `disallowed-tools` | Removes tools while active | CC |
| `model`, `effort` | Overrides while the skill is active | CC |
| `context`, `agent`, `background` | `context: fork` runs an `agent` subagent without the conversation; `background: false` waits | CC |
| `hooks` | Registered at invocation for the session; `once: true` drops one after its first run | CC |
| `paths`, `shell` | Globs that limit auto-loading; `bash` or `powershell` for `!` commands | CC |
| `metadata`, `license`, `compatibility` | Accepted, not acted on | CC, SPEC |

## 3. Recommended layout

```
breakdown_code/
  .claude-plugin/plugin.json       plugin "code-breakdown"
  skills/breakdown/                name: breakdown
    SKILL.md
    references/spec-format.md      fields, error codes
    references/entry-points.md     routes per framework
    references/pull-requests.md    gh commands, diffs
    references/excalidraw.md       read only when asked
    scripts/breakdown.py           check, render [--excalidraw]
    assets/canvas.html             template with one data marker
    assets/vendor/                 JS, fonts, licenses
  evals/<case>/                    prompt.md, graders/, case.yaml
```

Per run: `breakdowns/<slug>/` with `spec.json`, `canvas.html`, and `breakdown.excalidraw` only when asked.

## 4. Answers

**a. Location and invocation.** Project skills load only in their repo; personal ones skip Cowork and cloud sessions; plugins carry versioned skills to teammates (code.claude.com/docs/en/plugins). A personal skill folder may be a symlink, so one tree serves both. Commands: `/code-breakdown:breakdown`, or bare `/breakdown` while no other command holds it [CC].

Start the message with the name (`/breakdown #123 --excalidraw`); mid-sentence it only grants permission [CC]. Read `$ARGUMENTS`, "the full argument string as typed". Positional placeholders fail: `POST /orders` splits across `$0` and `$1`, a missing `$2` stays literal, and named `arguments` map by position [CC]. Claude's own invocations pass the text in the Skill tool's `args` (tool schema). SKILL.md opens: "Request: $ARGUMENTS. If empty, read the target and format from the user's message." Set `argument-hint: "[file | METHOD /path | #PR] [--excalidraw]"`. Skip `context: fork`: the subagent cannot see the conversation [CC].

**b. Description and triggering.** Third person, what plus when [BP]; no workflow, which agents follow instead of the body [WS]; "a little bit pushy", since Claude undertriggers; no angle brackets [SC].

> Turns a file, HTTP endpoint, or pull request into a left-to-right canvas of verbatim code snippets ordered by call flow. Use when the user asks to break down, walk through, trace, or show the flow of specific code, such as how POST /orders works end to end or what a PR changes, even without asking for a diagram. Not for one-line questions about a single snippet.

Triggering on plain "explain this code" widens reach, but a false trigger runs a script and writes files for a one-line answer, and collides with explain-frontend ("walk through frontend work" [EF]) and `/code-review`. Trigger on flow-shaped requests only; test the boundary with near-misses.

**c. Bundled scripts.** Code gives "deterministic reliability" [ENG]. Use stdlib-only Python 3, like Claude Code's visual-output example [CC]; Claude Code needs no Node (code.claude.com/docs/en/setup). Declare the runtime in `compatibility` [SCR]. Call scripts via `${CLAUDE_SKILL_DIR}` (the skill's folder), not the relative paths of [SCR] and pdf [REPO]: commands run in the session's working directory [CC].

`allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/breakdown.py *) Bash(gh pr view *) Bash(gh pr diff *)` matches SKILL.md's command, since the variable is substituted in both [CC]. Rules must match each part of `cd x && …`, and `>` counts as a file write [PERM]: one command per call, `--out` instead of redirects. The grant ends at the next user message; follow-ups prompt unless the user reruns `/breakdown` or adds a settings rule [CC].

The flag is a closed option in `--help` [SCR]. SKILL.md branches on an observable fact, as [WS] prefers over rule-plus-exemption: "Add `--excalidraw` to the render command when the request contains `--excalidraw` or names Excalidraw, now or in a follow-up. Otherwise render HTML only."

Errors: JSON on stdout, such as `{"ok": false, "errors": [{"snippet": "s3", "problem": "range 40-88 ends past line 72", "hint": "createOrder spans 40-71"}]}`; diagnostics on stderr; no prompts; documented exit codes [SCR]. Name valid options, like the pdf validators' "Valid values are: …" [REPO, BP].

**d. HTML template.** `assets/canvas.html` holds one data marker. The script finds it via `Path(__file__).parent`, like skill-creator's `generate_review.py` [SC], and inlines vendored JS, CSS and fonts, as web-artifacts-builder inlines its bundle; keep font licenses, as canvas-design does [REPO]. skill-creator's viewer and algorithmic-art use CDNs. Escape `<` in the embedded JSON: the raw `json.dumps` insert in `generate_review.py` would end the script element at any `</script>` in a snippet. The model never edits the template; the script prints the output path [CC].

**e. Content split.** Loading levels [OV]: metadata always (about 100 tokens), the body on trigger (under 5k tokens), references when read, scripts as output only. SKILL.md: the central rule, inputs and format branch, a copyable checklist [BP], spec essentials with one tiny worked example, the ordering rule, gotchas [ABP] and a closing checklist, under 500 lines [BP]. References: per-target and per-failure material, linked directly with when to read each [BP, CC]. From explain-frontend [EF]: one bold rule with its reason, a lookup table (target type, entry point, first snippet), a real worked example, a "Do not" list, the no-slop rules, "Check each. Fix and re-check."

**f. Testing.**
1. Baseline: run each target in fresh sessions without the skill (`skillOverrides: "off"`, `without_skill` subagents, or `claude plugin eval`'s no-plugin arm); record behavior verbatim [CC, SC, EVAL, WS].
2. Write only fixes for recorded failures; rerun with the skill [WS, BP].
3. Script checks: re-cut snippets from `spec.json` and compare bytes; entry point first; edges join real snippets; `check` before `render` (`tool_order`); no `*.excalidraw` unless asked (`file_exists`, `exists: false`) [EVAL, AEV]. Review layout by eye [SC].
4. Triggering: 20 queries, half near-misses, 3 runs each, threshold 0.5, 60/40 split, best held-out score wins [SC, DESC].
5. Haiku, Sonnet and Opus [BP]; micro-test wording at 5+ reps with a no-guidance control [WS].

Targets, on scaffolded fixture repos [EVAL]: `/breakdown src/pricing.ts` (three functions, one type); `/breakdown POST /orders` (route to DTO, five files); "walk me through feature/discounts vs main", plus one real `#N`; `--excalidraw` and "as excalidraw"; `/breakdown src/missing.ts` fails cleanly; "what does this regex do?" must not trigger.

## 5. Checklist for this SKILL.md

1. Central rule first; compaction keeps 5,000 tokens [CC].
2. Under 500 lines; each line costs every turn [CC, BP].
3. Description: third person, outcome, triggers, no steps [BP, WS].
4. `python3 ${CLAUDE_SKILL_DIR}/scripts/breakdown.py`, one per call, mirrored in `allowed-tools` [CC, PERM].
5. "Run" with `--help`; don't read script source [BP; REPO webapp-testing].
6. Copyable checklist: spec, check, fix, render [BP].
7. Branch on observable facts; one default [WS, ABP].
8. Standing instructions for follow-ups [CC].
9. References one level deep, each with when to read [BP, CC].
10. Gotchas fed by test failures [ABP].
11. One term per concept; reasons over capital MUSTs [BP, SC, EF].
12. One worked example; a before-returning checklist [WS, EF].

## 6. Unverified points

- Empty `$ARGUMENTS` expansion: implied, not stated.
- Whether auto-invocation on "as excalidraw" passes `--excalidraw` (tested above).
- Whether settings.json rules expand `${CLAUDE_SKILL_DIR}`, and whether `scripts/*` rules normalize `..`.
- Whether `#123` survives shell-style splitting; `$ARGUMENTS` sidesteps it.
- Whether every machine has `python3`.
- Whether `claude plugin eval` is enabled here ([EVAL] lists an "early access" error).
- Community collections: aggregators only, none used.

Outdated or conflicting: [BP] says "There is not currently a built-in way to run these evaluations"; Claude Code has `claude plugin eval` [CC]. [WS] shows `name: Skill-Name-With-Hyphens` and "ONLY when to use"; [SPEC] requires lowercase, [BP] what and when. [SC]'s `quick_validate.py` rejects `argument-hint`; use `claude plugin validate` [CC].
