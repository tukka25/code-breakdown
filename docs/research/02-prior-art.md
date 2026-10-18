# 02 · Prior art: code maps, code canvases and guided reading

Compiled 2026-10-18. Bracketed dates are source dates; statuses are from pages fetched that day.

## 1. Bottom line

- **graphicule.dev is James, cofounder of Etchpad.** Etchpad is a waitlist-only Rust "Spatial Code Editor" that parses a whole codebase into a map, zooms down to the code and overlays PRs. No public build exists.
- **Code on a canvas has helped since 2010** with long call paths and unfamiliar code. The tools faded because they replaced the editor, ran in one IDE, made users arrange boxes and needed an indexer per language.
- **The 2025-2026 tools put AI first.** They order code by flow, but they show summaries, links or model-grouped hunks, not verbatim blocks joined by checked edges.
- **Research supports entry point first, then calls. It does not support data types last.**

## 2. Tools

| Tool | What it draws | Real code on canvas? | Input | Structure source | Status | Link |
|---|---|---|---|---|---|---|
| Etchpad (graphicule.dev) | Zoomable wiring diagram; PR overlay | Yes, when zoomed in (claimed) | Local project, PR | Tree-sitter grammar forks | Waitlist; 4 languages claimed | [etchpad.ai](https://etchpad.ai/) |
| Code Bubbles | Method bubbles on a 2D canvas | Yes | Java (Eclipse) | Eclipse | Research; commit 2026-10-14 | [CHI 2010](https://stars.library.ucf.edu/scopus2010/1077), [repo](https://github.com/StevenReiss/bubbles) |
| Code Canvas | Zoomable surface of all project files | Yes | VS 2010 | Visual Studio | Prototype (2010) | [MSR](https://www.microsoft.com/en-us/research/project/code-canvas/) |
| Debugger Canvas | Bubble per executed method, call arrows | Yes | Debug session | VS code model | VS 2010 Ultimate only; nothing after 2012 found | [ICSE 2012](https://microsoft.com/en-us/research/wp-content/uploads/2016/02/p1064-213-deline.pdf) |
| Sourcetrail | Symbol dependency graph | Names | C/C++, Java | Per-language indexers | Archived 2021; main fork slowing | [repo](https://github.com/CoatiSoftware/Sourcetrail), [fork](https://github.com/petermost/Sourcetrail) |
| CodeSee | Codebase maps; PR Review Maps | No | Repo, PR | Not stated | GitKraken bought it [2024-05]; site down | [GitKraken](https://www.gitkraken.com/blog/gitkraken-launches-devex-platform-acquires-codesee) |
| Haystack | Functions as windows, with arrows | Yes | VS Code fork | LSP (inferred) | Pivoted; editor idle since 2024-11 | [Show HN](https://news.ycombinator.com/item?id=41068719) |
| CodeViz, GitDiagram | Architecture diagrams | Links to source | Repo | GitDiagram: LLM; CodeViz not stated | Alive; GitDiagram has a Claude Code plugin | [CodeViz](https://www.codeviz.ai/), [GitDiagram](https://github.com/ahmedkhaleel2004/gitdiagram) |
| VS Code Maps | Graph from assemblies down to members | No | C#, VB, C++ | VS code model | Alive; Enterprise only [2026-04] | [Learn](https://learn.microsoft.com/en-us/visualstudio/modeling/map-dependencies-across-your-solutions) |
| madge, dependency-cruiser | Module import graph | No | JS/TS | Import parsing | Alive | [madge](https://github.com/pahen/madge), [d-c](https://github.com/sverweij/dependency-cruiser) |
| Understand, Doxygen, code2flow | Call trees and call graphs | No | Source tree | Static analysis; Graphviz | Understand commercial; code2flow last push 2025-07 | [Understand](https://en.wikipedia.org/wiki/Understand_(software)), [Doxygen](https://www.doxygen.nl/manual/config.html), [code2flow](https://github.com/scottrogowski/code2flow) |
| Glamorous Toolkit | Custom views per object | In views you build | Many languages | You build the views | Alive, MIT | [gtoolkit.com](https://gtoolkit.com/) |
| CodeTour, literate programming | Tour of file/line steps; program as prose | Yes | Written by hand | Author | CodeTour last commit 2025-08 | [CodeTour](https://github.com/microsoft/codetour), [Knuth](https://www-cs-faculty.stanford.edu/~knuth/lp.html) |
| Swimm | Code-coupled docs (formerly) | n/a | n/a | n/a | Pivoted to COBOL modernization | [swimm.io](https://swimm.io/) |
| Windsurf Codemaps | Map for one question | No; links to lines | Prompt | LLM | Launched [2025-11] | [post](https://cognition.com/blog/codemaps) |
| CodeRabbit | Walkthrough, sequence diagrams, Change Stack layers | Diff hunks | PR | LLM | Alive; Change Stack in preview | [docs](https://docs.coderabbit.ai/pr-reviews/change-stack.md) |
| Devin Review, cubic | PR hunks or files regrouped for reading | Diff | PR | LLM; cubic not stated | Launched [2026-01] | [Devin](https://cognition.com/blog/devin-review), [cubic](https://docs.cubic.dev/code-review-platform/intelligent-diff-ordering) |
| Greptile, Copilot PR summary, Graphite | Summaries or comments; Greptile adds a diagram | No | PR | LLM | Alive; Cursor bought Graphite [2025-12] | [Greptile](https://www.greptile.com/docs/code-review/first-pr-review.md), [Copilot](https://docs.github.com/en/copilot/responsible-use/pull-request-summaries), [Graphite](https://siliconangle.com/2025/12/19/cursor-acquires-ai-code-review-startup-graphite/) |
| Warp pr-walkthrough skill | Four D3 PR canvases with tours | No; summaries | PR, in an agent | Agent | Added 2026-05 | [SKILL.md](https://github.com/warpdotdev/common-skills/blob/main/.agents/skills/pr-walkthrough/SKILL.md) |
| Difftastic, GumTree, SemanticDiff | Structural diffs; GumTree, SemanticDiff detect moves | Yes | Two versions | Tree-sitter; SemanticDiff undocumented | Alive | [Difftastic](https://difftastic.wilfred.me.uk/parsing.html), [GumTree](https://github.com/GumTreeDiff/gumtree/wiki/Languages), [SemanticDiff](https://semanticdiff.com/) |

## 3. Closest matches

**Etchpad** takes the reel's idea to codebase scale: "Every block is a construct in your code, every wire a reference that actually exists" and "Zoom out for architecture; zoom in until you're reading the code". It promises "Clear separation of the ground truth code and the AI inferences" and lists "Read one scope at a time".

**Debugger Canvas** [2012] is the closest tool that shipped. Each method the debugger enters opens as a bubble of real code, with call arrows. One user said "The left-to-right, top-to-bottom spanning of the tree makes intuitive sense." Others said "For a 'normal' project it isn't worth the hassle with performance" and "Sometimes I need to see field definitions." Of 72 survey respondents who had used it, 19 had stopped.

**Windsurf Codemaps** [2025-11-04] makes one map per question, "densely linked to the exact lines of code", for code that "starts to outstrip their ability to understand it". Its nodes are AI annotations, not code.

**Devin Review** "groups together changes that are logically connected, orders the hunks of code, and explains each hunk". **CodeRabbit** says its grouping "is produced by a model" and may change when it reruns.

**Warp's pr-walkthrough skill** [2026-05] writes a self-contained, script-checked HTML canvas and puts "lower-level dependencies farther right/down from their callers". Its nodes are prose summaries.

## 4. Why these tools struggled

- **Money.** Sourcetrail dropped paid licences because there were not enough paying customers ([Le Monde Informatique, 2019-11-27](https://www.lemondeinformatique.fr/actualites/lire-l-outil-d-exploration-de-code-sourcetrail-passe-en-open-source-77216.html)). In the [shutdown thread](https://news.ycombinator.com/item?id=28637193), a commenter argued call-graph viewers are needed only occasionally. CodeSee's site no longer loads ([Repowise, 2026-10-12](https://repowise.dev/blog/comparisons/codesee-alternatives-codebase-maps)).
- **One indexer per language.** A user in the same thread judged the work "too much to keep it as a side project" and expected the last build to fall behind on language features. The main fork covers only C/C++ and Java, and on 2026-08-01 its maintainer said work will slow.
- **Scale.** Doxygen cuts call graphs off at 50 nodes and warns that they "significantly increase the time of a run". VS Code Maps warns that "memory limitations may prevent you from expanding all the groups".
- **Arranging boxes by hand.** Code Bubbles users spent significantly more time arranging code than Patchworks users, who also made fewer navigation mistakes with a fixed grid and one-way ribbon ([CHI 2014](https://austinhenley.com/pubs/Henley2014CHI_Patchworks.pdf)). On Haystack's Show HN (2024-07), azhenley wrote "We found the canvas provided too much freedom" and andybak wrote "I viscerally dislike manually arranging windows".
- **Replacing the editor.** Debugger Canvas's authors concluded it "is best implemented as a mode in the existing user experience rather than a replacement".
- **Stale output and noise.** CodeTour needs a CI action to catch "tour drift". Copilot summaries are not refreshed. One CodeRabbit user turned off "the poems and sequence diagram noise" ([HN, 2025-12-17](https://news.ycombinator.com/item?id=46305487)).

## 5. Comprehension research

The classic models split into top-down and bottom-up reading. In Brooks's model, readers form hypotheses and check them against "beacons". Soloway, Adelson and Ehrlich describe top-down reading through programming plans. Pennington found that on new code, readers first build a "program model" of control flow bottom-up, then a "situation model" of data flow. Letovsky's model is opportunistic. Von Mayrhauser and Vans report that "programmers switch between all three comprehension models" ([Computer, 1995](https://www.cs.kent.edu/~jmaletic/cs69995-PC/papers/von_mayrhauser-1995.pdf)), and [Siegmund (2016)](https://www.se.cs.uni-saarland.de/publications/docs/FoSE16.pdf) notes they read top-down where they can. Eye tracking points to execution order: "The Execution Order model better explains the experts' reading approach than Story Order does" ([Busjahn et al., ICPC 2015](https://huang.isis.vanderbilt.edu/cs8395-f23/paper/linear-order-eye.pdf)). The code's own linearity shapes reading order more than experience does ([Peitek et al., ICPC 2020](https://www.se.cs.uni-saarland.de/publications/docs/PSA20.pdf)). For review, [Baum et al. (ICSME 2017)](https://sback.it/publications/icsme2017.pdf) found that a good order mostly groups related parts and should "Provide information before it is needed". 85% of 130 respondents preferred reading callees before callers, though many interviewees read callers first. One seeded defect had 64% lower odds of being found when its file came last ([Fregnan et al., FSE 2022](https://arxiv.org/abs/2208.04259)). So starting at the entry point and following the calls fits how experts read unfamiliar code. Putting the data types last does not, because readers often need a type before the code that uses it.

## 6. Lessons for the skill

1. **Keep each map to one flow, with a cap on boxes.** Doxygen cuts graphs off at 50 nodes, and Code Maps can run out of memory. Split a big flow into linked storylines.
2. **Lay boxes out automatically in one direction, with no dragging.** Patchworks' fixed layout beat free arrangement, and Debugger Canvas users liked left-to-right call trees.
3. **Build edges from the code. Use the model only for labels and for picking the entry point.** Etchpad sells this split, CodeRabbit's order can change between runs, and the reel drew a wrong edge by eye (00-reel.md).
4. **Place callees and types next to their first user.** Baum found the closest distance is "visible on the screen at the same time", and Debugger Canvas users missed field definitions.
5. **State the ordering rule on the canvas.** 86% of Baum's respondents rated a tour with no sensible rule the worst.
6. **Run next to the editor, not instead of it.** Write a file and link each box to file:line. Haystack dropped its editor fork.
7. **Find blocks with tree-sitter instead of keeping an indexer per language.** Indexer upkeep sank Sourcetrail. GumTree bundles tree-sitter, Etchpad's GitHub holds tree-sitter grammar forks, and Difftastic's atom-and-list tree defines blocks without language-specific code.
8. **Regenerate on every run, and size the output to the input.** CodeTour tours drift. Google Code Wiki regenerates after every change ([InfoQ, 2025-11-21](https://infoq.com/news/2025/11/google-code-wiki/)). Greptile skips diagrams for trivial changes.

## 7. The gap

As of 2026-10-18, I found no tool that works inside a coding agent and turns a file, an endpoint or a PR into verbatim declaration-level blocks joined by checked call and type edges. Etchpad comes closest, but it is unreleased, standalone and maps whole codebases. Debugger Canvas needed a running debugger. Codemaps, Devin Review, CodeRabbit and Warp's skill show summaries, links or diff hunks grouped by a model. The risk is that Etchpad ships "Read one scope at a time" first.

## 8. Unverified leads

- Sourcetrail's own shutdown post (the archive was blocked).
- CodeSee's closing date: a LinkedIn post says "Feb 22" but gives no year.
- Whether HN user jmsfltchruk, who wrote on 2025-09-09 about building etchpad.dev, is James.
- Whether Etchpad runs on real projects. His Instagram clips (2026-10-05 to 10-13) had no readable captions.
- Not checked: Greptile's old diagram page (now 404), SemanticDiff's parser, Understand's current version (vendor site returned 403), DeepWiki, Light Table, AppMap and CodeRibbon.
