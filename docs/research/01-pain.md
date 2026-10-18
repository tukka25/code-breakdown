# 01 · The pain: where readers get lost in AI-written code

Track: the pain. Researched 2026-10-18. Every number was read on the linked page. I couldn't fetch Reddit, X or Lobsters (section 8), so Reddit voices come only through D15.

## 1. Bottom line

The pain is real and widely measured. 66% of Stack Overflow's 2025 respondents cite "almost right, but not quite" output, and 96% of Sonar's 2026 respondents don't fully trust AI code. Telemetry shows larger AI PRs that wait longer and merge less often (D1, D3, D8, D9). The evidence is strongest for five moments: volume, polish that lowers the reviewer's guard, alphabetical instead of call order, duplicated logic, and missing intent. A storyline of verbatim blocks answers "where does it start, what calls what, what does it touch". It can't answer "why" or "is it correct", and it must not look as if it does. The bet against prose holds for review, but explanations a reader asks for do help. A full code canvas also failed one tool team (Q20), so the canvas must stay small and ordered.

## 2. Data table

| # | Source | Finding | What was measured | Date | Link |
|---|---|---|---|---|---|
| D1 | Stack Overflow survey 2025 | 66% cite "AI solutions that are almost right, but not quite"; 45.2% say debugging AI code takes more time; 16.3% find it "hard to understand how or why the code works". Trust 33%, distrust 46% | 49,000+ responses (questions: n=31,476; n=33,244) | Jul 2025 | [survey](https://survey.stackoverflow.co/2025/ai) |
| D2 | Stack Overflow survey 2026 | 48.0% trust AI output "when I can easily verify the output"; 6.6% trust it for important decisions; 49.7% use AI to understand a codebase | 30,903 responses (n=14,304; n=12,547) | Oct 2026 | [data](https://survey.stackoverflow.co/2026/ai/data), [blog](https://stackoverflow.blog/2026/10/06/the-results-of-the-2026-developer-survey-are-here/) |
| D3 | Sonar State of Code (vendor) | 96% don't fully trust AI code; 48% always check it; 38% say it takes more effort to review than human code; 53% cite code "that looks correct but isn't reliable". 66% rate AI explanation of existing code effective | 1,100+ developers | Jan 2026 | [release](https://www.sonarsource.com/company/press-releases/sonar-data-reveals-critical-verification-gap-in-ai-coding/), [blog](https://www.sonarsource.com/blog/state-of-code-developer-survey-report-the-current-reality-of-ai-coding/) |
| D4 | METR RCT and follow-up | 19% slower with AI, while believing they were 20% faster; <44% of generations accepted; 9% of time spent reviewing or cleaning AI output. The 2026 rerun (−18% and −4% time) is unreliable by METR's own account | 16 developers, 246 issues; rerun 57 developers | Jul 2025; Feb 2026 | [2025](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/), [paper](https://arxiv.org/abs/2507.09089), [2026](https://metr.org/blog/2026-02-24-uplift-update/) |
| D5 | GitClear 2025 (vendor) | In 2024 copy/pasted lines (12.3%) passed moved lines (9.5%, down from 24.8% in 2021). Commits with a 5+ line duplicate block: 6.66% vs 0.45% in 2022 | 211M changed lines, 2020–2024 | Feb 2025 | [PDF](https://public.amplenote.com/ZRbxXhi9FamWYbKEFaD9h7Qh) |
| D6 | GitClear 2026, via LeadDev (vendor) | Duplication +81%; moved code −70%; "error masking" (catch/rescue blocks, safe-navigation, stubbed methods) +47%; calls into other functions −35% | 623M changes, 2023–2026 | Jul 2026 | [LeadDev](https://leaddev.com/ai/code-maintainability-plummets-in-the-ai-coding-era) |
| D7 | CodeRabbit (vendor) | AI PRs: 10.83 vs 6.45 issues each; readability issues >3×; logic errors +75%; error-handling gaps ~2×; concurrency errors ~2× | 470 OSS PRs (320 AI) | Dec 2025 | [report](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report) |
| D8 | Faros AI (vendor) | 2025: PR review time +91%, PR size +154%. 2026 Q2: median review time 5×. Q3: PR size +71.8%, merges with no review +76.3%, incidents per PR +14.5% (Q2: 3×) | Telemetry; 10,000+ then 22,000 developers | Jul 2025; Q2 & Sep 2026 | [2025](https://www.faros.ai/blog/ai-software-engineering), [Q2](https://www.faros.ai/research/ai-acceleration-whiplash), [Q3](https://www.faros.ai/blog/ai-speed-trap-takeaways) |
| D9 | LinearB benchmarks (vendor) | AI PRs merged within 30 days: 32.7% vs 84.4% for manual PRs; they wait 4.6× longer for review | 8.1M+ PRs, 4,800+ organizations | Dec 2025 | [report](https://linearb.io/blog/engineering-benchmarks-report) |
| D10 | DORA | 2024: per 25% more AI adoption, stability −7.2%, throughput −1.5%; 39% little or no trust. 2025: 90% use AI; 30% trust it "a little" or "not at all"; instability still rising | Surveys; ~5,000 respondents in 2025 | Oct 2024; Sep 2025 | [2024](https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report), [2025](https://blog.google/technology/developers/dora-report-2025/), [InfoQ](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025) |
| D11 | Fregnan et al., ESEC/FSE | Files shown earlier get more comments; 64% lower odds of finding a defect when its file is last | 219,476 PRs; 106-person experiment | 2022 | [arXiv](https://arxiv.org/abs/2208.04259) |
| D12 | File-ordering study | Latent-bug rate 56.7% at file position 1 and 61.5% at position 30; each extra file cuts the odds of any comment by ~8.7% | 330,343 PRs, 182 projects | Sep 2026 | [arXiv](https://arxiv.org/abs/2609.22610) |
| D13 | Anthropic RCT | AI group 50% vs 67% on a comprehension quiz; participants who asked for explanations ≥65%, those who delegated <40% | 52 developers | Jan 2026 | [Anthropic](https://www.anthropic.com/research/AI-assistance-coding-skills) |
| D14 | Copilot brownfield study | Faster with Copilot, but no comprehension gain (p=0.59) | 15 graduate students | Nov 2025 | [arXiv](https://arxiv.org/abs/2511.02922) |
| D15 | CMU grey-literature theory | Drivers of weaker review that practitioners describe: volume, "surface plausibility", "code opacity (lost intent)" | 38,709 documents, incl. 31,079 Reddit threads | Jul 2026 | [arXiv](https://arxiv.org/abs/2607.07980) |
| D16 | Counter: code-level studies | AI–human code-level differences are "rather small"; AI functions are "roughly half the size and branching" of human ones | Repo study; 787,562 function pairs | Mar & Sep 2026 | [1](https://arxiv.org/abs/2603.27130), [2](https://arxiv.org/abs/2609.12708) |

## 3. Taxonomy of where readers get lost

Rows are ordered by strength of evidence. The evidence added rows 4, 5 and 9, merged "types far from use" with "needless indirection" (row 6), and reframed "defensive noise" (row 7).

| # | Where readers get lost | Reader's question | Evidence | What the storyline must show |
|---|---|---|---|---|
| 1 | Too much at once | "How big is this, and what comes first?" | D8, D9, D12; Q6, Q7, B19, B20 | Counts; the main path first; independent subtrees as split points. It can't shrink the PR. |
| 2 | Polish lowers the guard | "Is this right, or just tidy?" | D1, D3 (53%), D15; Q8, Q9, B6, B18 | It can't prove correctness. It can remove the polish: no prose, neutral labels, and the markers from rows 5–9. |
| 3 | Wrong reading order | "Where does it start? What calls what?" | D11, D12; Q2, Q4, Q5 | Entry block first, callees in call order, changed blocks marked, unchanged context dimmed. This is the skill's core strength. |
| 4 | Lost intent | "Why does this exist?" | D15, B5; Q15, Q16 | Code can't answer this. Quote the ticket or PR text at the root as the author's claim. |
| 5 | Duplicate code | "Does this already exist? Which copy runs?" | D5, D6; Q10 | Near-duplicates found by a deterministic match, placed side by side. |
| 6 | Scattered pieces, needless hops | "Where is this defined? How many hops to the real work?" | Q12, Q1, Q13; D6 (−35% calls) | Each type next to its first user; single-use pass-through functions marked; file:line on every box. |
| 7 | Error handling masks or misses failures | "What happens when it fails?" | D6 (+47%), D7 (~2× gaps); Q13, B16 | Catch and fallback lines marked where they sit; blocks with no handling shown. |
| 8 | Hidden state and invariants | "What does this touch, and in what order?" | D7; Q14 | Partly: "writes/reads" edges for fields, globals, DB and network. Runtime order and invariants aren't visible in a static tree; say so. |
| 9 | Dead or phantom code | "Is this even used?" | Q11 | Orphan boxes listed; unresolved imports flagged. |

**Counter-evidence.**
- Code-level gaps are small (D16), and studies disagree on whether agent PRs are larger (D15). The pain looks systemic rather than a matter of tangled function bodies.
- Some effects are fading: the METR rerun (D4), Faros incidents per PR (D8), and a falling share of agent PRs merged with no review (D15).
- Legacy code was hard to follow before AI ([aabdi](https://news.ycombinator.com/item?id=49273037), [tom_m](https://news.ycombinator.com/item?id=45428211)), and only 16.3% name comprehension as a frustration (D1).
- Haystack found a code canvas "too confusing for code reviews" (Q20) and full call graphs messy (B11).
- Most figures come from vendors.

## 4. AI explanations: what fails, what helps

**What fails.**
- Confident text nobody can check (Q1, Q18).
- Framing that spins the PR (Q17, B21).
- Expansion instead of distillation (Q19, B7).
- Summaries at the wrong level. Willison's "Archimedean spiral" summary "did not help me much!" A code walkthrough gave him the structure, and an animation gave the intuition (B2).
- PR descriptions that report what the agent generated, not what was asked (B4, B3).

**What helps.** Walkthroughs whose snippets are cut by `sed`/`grep`/`cat` (B1). Ordered chapters or intent-based commits (Q6, B9, B12). Tests beside the code (B13). Stepping from a test with the full file visible (B10). A "simple visual indication of control flow or dependency" (Q19).

**Against the bet.** 66% rate AI explanation of existing code effective (D3). 49.7% use AI to understand codebases (D2). Asking for explanations protected quiz scores (D13). Fowler has seen LLMs help explain legacy code (B15). One user asks for an "essay" version of each plan (B17). On balance, explanations a reader asks for help, and explanations pushed into a review get skipped or distrusted. Push structure and leave questions to the chat.

## 5. Coping strategies

| Strategy | Evidence | Signal for the skill |
|---|---|---|
| Start from the ticket or PR text | B4, B14 | Quote it at the root |
| Start from data and irreversible changes (schemas, types) | B8, B4 | Offer a data-first order |
| Start from entry points, then each block | Q2, Q3 | Default order |
| Step through commits, chapters or split PRs | B9, B12, Q6, B3 | Subtrees as chapters |
| Read tests or use a debugger | B13, B10 | Link tests that reach the entry block |
| Retype the code to build a "spatial map" | Q13 | Keep file:line and a stable layout |
| Skim or rubber-stamp | Q7, D8 (no-review merges +76.3%) | The failure the skill competes with |

## 6. Implications for the skill

1. **Order by flow, in two modes.** Entry-first is the default. Data-first (types, schemas) is an option, because reviewers split on this (Q2 vs B4, B8). In a PR, never use alphabetical order: order changed blocks along the call path and dim unchanged neighbours (D11, D12, Q4).
2. **Check edges as well as snippets.** Keep the no-retyping rule (B1). Every "calls", "uses type" or "writes" arrow must come from a resolved reference, because the reel drew a wrong edge on a 60-line file. Each box links to its full file (B10).
3. **Use structural labels only.** Allow 2–3 word roles ("Entry point", "Writes DB"). Allow no "robust", "safe" or "clean", and no summary prose (Q17, Q9, D15).
4. **Add deterministic markers for what a skim misses:** no callers (Q11); near-duplicate, counted as ≥5 matching lines like GitClear (D5); single-use pass-through (Q12).
5. **Mark error handling and state changes where they sit:** catch, except and rescue blocks, `?.` and `??` fallbacks, and empty handlers. Draw "writes" edges to fields, globals, DB and network (D6, D7, Q14).
6. **Cap the view** at ~12 boxes on the main path and fold the rest into named subtrees. Past ~10 files or ~400 changed lines (B4), split the canvas into subtrees listed as possible split points (D8, D12, B11).
7. **Quote intent, never generate it.** The PR root shows the title, description and ticket verbatim as "Author's claim", or "No stated intent" when there is none (D15, B3, Q15).
8. **State the blind spots** in a fixed footer: runtime order, invariants, failure behaviour and test coverage were not checked. List the tests that reach the entry block (Q14, D14).

## 7. Appendix

### A. Practitioner quotes

Verbatim; typographic quotes normalised. "[...]" marks an omission. HN links point to the comment.

| # | Quote | Author | Platform | Date | Link |
|---|---|---|---|---|---|
| Q1 | "So where does the data come from?" "Hmm... actually I don't know. Let me ask Claude." You sit next to each other watching an endless wall of text appear on the screen. Neither of you has any idea whether any of it is true but Claude seems very confident. [...] This project has become so convoluted, with so many layers and services, that no one on your team could possibly start to understand what's going on. | Florian Herrengt | Blog (HN: 937 comments) | 2026-08-11 | [link](https://blog.florianherrengt.com/ai-removing-middle-class-software-engineering.html) |
| Q2 | Non-trivial PRs need two passes: first grok the entrypoints and touched files to grasp the conceptual change and review order, then dive into each block of changes with context. | irrationalfab | Hacker News | 2025-09-10 | [link](https://news.ycombinator.com/item?id=45203664) |
| Q3 | I don't care what writes the code, but if I commit it or approve the merge, I need to be able to explain it, full stop. I don't need go line by line, just point and explain this does this does that which leads to that. | efields | Hacker News | 2026-08-12 | [link](https://news.ycombinator.com/item?id=49277487) |
| Q4 | I've been using Claude Code for a few months, and while it's amazing at writing code, reviewing the changes became a bottleneck. The diff is just files in alphabetical order. No context. No explanation of intent. | mo-dulaimi | Hacker News (Show HN: Codebrief) | 2026-03-08 | [link](https://news.ycombinator.com/item?id=47295556) |
| Q5 | We used to work at big companies, where reviewing non-trivial pull requests felt like reading a book with its pages out of order. We would jump and scroll between files, trying to piece together the author's intent before we could even start reviewing. [...] AI has made this even trickier. Today it's not uncommon for a pull request to contain code the author doesn't fully understand themselves! | akshaysg | Hacker News (Show HN: Haystack) | 2025-09-10 | [link](https://news.ycombinator.com/item?id=45201703) |
| Q6 | As coding agents took off, we saw our PR backlog pile up faster than we could handle. Not only that, the PRs themselves were getting larger and harder to understand, and we found ourselves spending most of our time trying to build a mental model of what a PR was actually doing. | cpan22 | Hacker News (Show HN: Stage) | 2026-04-16 | [link](https://news.ycombinator.com/item?id=47796818) |
| Q7 | Most of human review I see of AI code is rubber stamping at this point, the volume is too big for human to keep up. | stackskipton | Hacker News | 2026-04-17 | [link](https://news.ycombinator.com/item?id=47810228) |
| Q8 | The problem is that code that looks good is not the same as code that is good, but they are superficially similar to a reviewer. and... you can absolutely bury reviewers in it. | m463 | Hacker News | 2025-09-17 | [link](https://news.ycombinator.com/item?id=45280127) |
| Q9 | AI-generated code is written so as to look plausibly correct, even when it's faulty. [...] This makes it more difficult for a human reviewer to detect a fault in the code. | Diomidis Spinellis | Blog | 2026-05-23 | [link](https://www.spinellis.gr/blog/20260523/) |
| Q10 | The things I struggle more with when I use LLMs to generate entire features with limited guidance (so far only in hobby projects) is the LLM duplicating functionality or not sticking to existing abstractions. For example if in existing code A calls B to get some data, and now you need to do some additional work on that data (e.g. enriching or verifying) that change could be made in A, made in B, or you could make a new B2 that is just like B but with that slight tweak. | wongarsu | Hacker News | 2025-09-30 | [link](https://news.ycombinator.com/item?id=45424446) |
| Q11 | Code reviewing coworkers are rapidly losing their minds as they come to the crushing realization that they are now the first layer of quality control instead of one of the last. Asked to review; forced to pick apart. Calling out freshly added functions that are never called, hallucinated library additions, and obvious runtime or compilation errors. | Simon Højberg, quoted by Simon Willison | Blog | 2025-10-08 | [link](https://simonwillison.net/2025/Oct/8/simon-hojberg/) ([original](https://hojberg.xyz/the-programmer-identity-crisis/)) |
| Q12 | The default output splits logic across five functions (parse_args, build_dataloaders, train, evaluate, main), each called exactly once. This inflates live time: model is created in main() at line 161, passed to train() at 162, then to evaluate() at 163 — the reader must jump across three function boundaries to follow its lifecycle. | markrogersjr ("Tighten") | Blog | 2026-03-07 | [link](https://inmimo.me/blog/tighten) |
| Q13 | Poring over hundreds of lines of overly-defensive, badly-commented, subtly incorrect code is not fun. [...] Most importantly, this workflow allows me to build a spatial map of my codebase. I know where every bit of functionality lives in the codebase. | Ankur Sethi | Blog | 2026-08-02 | [link](https://ankursethi.com/blog/prevent-cognitive-debt-by-manually-retyping-llm-generated-code/) |
| Q14 | From what I've seen they're great at identifying trees and bad at mapping the forest. In other words, they can help you identify what fairly isolated pieces of code are doing. That's helpful, but it's also the single easiest part of understanding legacy code. The real challenges are things like identifying and mapping out any instances of temporal coupling, understanding implicit business rules, and inferring undocumented contracts and invariants. | bunderbunder | Hacker News | 2025-09-30 | [link](https://news.ycombinator.com/item?id=45426620) |
| Q15 | When I met with them, the team initially blamed technical debt: messy code, poor architecture, hurried implementations. But as we dug deeper, the real problem emerged: no one on the team could explain why certain design decisions had been made or how different parts of the system were supposed to work together. | Margaret-Anne Storey | Blog | 2026-02-09 | [link](https://margaretstorey.com/blog/2026/02/09/cognitive-debt/) |
| Q16 | I've been experimenting with prompting entire new features into existence without reviewing their implementations and, while it works surprisingly well, I've found myself getting lost in my own projects. I no longer have a firm mental model of what they can do and how they work, which means each additional feature becomes harder to reason about | Simon Willison | Blog | 2026-02-15 | [link](https://simonwillison.net/2026/Feb/15/cognitive-debt/) |
| Q17 | The bulk of difficulty in reviewing AI outputs is escaping the framing they never stop trying to apply. It's never just some code. It's always some code that is 'supposed to look like something', alongside a ton of convincing prose promising that it _really_ does do that thing | hexaga | Hacker News | 2026-04-17 | [link](https://news.ycombinator.com/item?id=47811593) |
| Q18 | I've seen tools designed to "understand" and document repos hallucinate many times, often coming up with a plausible but completely wrong explanation of how things actually work, or, even more subtly, of why they work the way they work. | int_19h | Hacker News | 2025-10-01 | [link](https://news.ycombinator.com/item?id=45433150) |
| Q19 | the whole point should be to combat the verbosity and featurelessness of LLM-generated code and text. Using an LLM on the backend to discover meaningful connections in the codebase may sometimes be the right call but the output of that analysis should be some simple visual indication of control flow or dependency like you mention. At a first look the output in the editor looks more like an expansion rather than a distillation. | ray__ | Hacker News | 2025-09-10 | [link](https://news.ycombinator.com/item?id=45203022) |
| Q20 | We may go back to code visualization for editors, but after testing it with a lot of engineers, we found that it was too confusing for code reviews. The main issue was just how alien the interface is! | akshaysg (Haystack co-founder) | Hacker News | 2025-09-11 | [link](https://news.ycombinator.com/item?id=45211762) |

### B. Other verbatim excerpts cited

| # | Excerpt | Source | Date | Link |
|---|---|---|---|---|
| B1 | By telling it to use "sed or grep or cat or whatever you need to include snippets of code you are talking about" I ensured that Claude Code would not manually copy snippets of code into the document, since that could introduce a risk of hallucinations or mistakes. | Simon Willison, "Linear walkthroughs" | 2026-02-25 | [link](https://simonwillison.net/guides/agentic-engineering-patterns/linear-walkthroughs/) |
| B2 | Claude's report said it uses "Archimedean spiral placement with per-word random angular offset for natural-looking layouts". This did not help me much! I requested a linear walkthrough of the codebase which helped me understand the Rust code in more detail | Simon Willison, "Interactive explanations" | 2026-02-28 | [link](https://simonwillison.net/guides/agentic-engineering-patterns/interactive-explanations/) |
| B3 | Several small PRs beats one big one [...] Agents write convincing looking pull request descriptions. You need to review these too! | Simon Willison, "Anti-patterns" | 2026-03-04 | [link](https://simonwillison.net/guides/agentic-engineering-patterns/anti-patterns/) |
| B4 | Pull request descriptions summarize what an agent generated rather than what the team requested. [...] Treat 10 files or 400 changed lines as signals for deliberate review planning. [...] Begin reviews with schemas, shared types, interfaces, configurations, migrations, and utilities before moving to dependent logic. A dependency-aware order provides clearer context than alphabetical file sequences. | CodeRabbit guide (vendor) | 2026-09-22 | [link](https://www.coderabbit.ai/guides/code-review-best-practices-for-ai-generated-code) |
| B5 | "polish can lower the reviewer's guard" (G2222) [...] "One reason AI-generated code is harder to review is that you're reconstructing intent" (G2066) [...] "reviewing 5k lines of AI-generated code after the fact is miserable" (G978, a Reddit r/vibecoding thread) | Agarwal et al. (CMU), quoting practitioner sources | 2026-07-08 | [link](https://arxiv.org/abs/2607.07980) |
| B6 | The output is syntactically clean, often well-formatted, superficially correct—precisely the signals that historically triggered merge confidence. But surface correctness is not systemic correctness. | Addy Osmani (O'Reilly repost) | 2026-04-13 | [link](https://www.oreilly.com/radar/comprehension-debt-the-hidden-cost-of-ai-generated-code/) |
| B7 | Whereas AI code review comments are long winded not as precise. | xmprt, Hacker News | 2026-01-26 | [link](https://news.ycombinator.com/item?id=46773031) |
| B8 | We review irreversible decisions first (e.g. schema changes). | azihsoyn, Hacker News | 2026-03-10 | [link](https://news.ycombinator.com/item?id=47320092) |
| B9 | you just step through each commit in turn and you can see how the code got to be where it is now, rather than Github's default "here's everything, good luck" view. | jon-wood, Hacker News | 2025-09-11 | [link](https://news.ycombinator.com/item?id=45210574) |
| B10 | Starting from the test, allow me to step through the program execution, just like a debugger, to observe variables, surrounding code, and the complete file. If you read only the covered lines of code in a linear way, you'd miss the refactoring opportunities because you aren't looking at the rest of the file. | DTrejo, Hacker News | 2025-09-12 | [link](https://news.ycombinator.com/item?id=45222535) |
| B11 | We tried to kind of do this in previous iterations (show call graphs all at once) and it gets messy very fast. | akshaysg, Hacker News | 2025-09-11 | [link](https://news.ycombinator.com/item?id=45211736) |
| B12 | I've got a setup where the agent reads the implementation plan, then creates a commit history based on intent rather than location. | lbreakjai, Hacker News | 2026-04-17 | [link](https://news.ycombinator.com/item?id=47809169) |
| B13 | Reviewing the code is very pleasant because you get both the tests and production code and you can rely on the symmetry between them to understand the code's intent | cadamsdotcom, Hacker News | 2025-09-17 | [link](https://news.ycombinator.com/item?id=45281161) |
| B14 | sometimes the best entry point is the PR description or an external ticket. sometimes you need to read the code first to understand the reasoning behind the changes. | philipnee, Hacker News | 2026-04-18 | [link](https://news.ycombinator.com/item?id=47812764) |
| B15 | I have seen compelling evidence that LLMs help a great deal in understanding what legacy code is doing. | Martin Fowler | 2026-04-02 | [link](https://martinfowler.com/fragments/2026-04-02.html) |
| B16 | That shortcut becomes tech debt for the maintainers, who eventually need to ascertain which error handling was added for cause, versus those added for AI expediency | Bill Harding (GitClear), quoted by LeadDev | 2026-07-07 | [link](https://leaddev.com/ai/code-maintainability-plummets-in-the-ai-coding-era) |
| B17 | my current favorite trick for reducing "cognitive debt" (h/t @simonw) is to ask the LLM to write two versions of the plan: The version for it (highly technical and detailed) The version for me (an entertaining essay designed to build my intuition) | Nathan Baschez on X, quoted by Simon Willison (counter-evidence: prose that helps) | 2026-02-17 | [link](https://simonwillison.net/tags/cognitive-debt/) |
| B18 | AI-produced code often looks consistent but violates local patterns around naming, clarity, and structure. | CodeRabbit report (vendor) | 2025-12-17 | [link](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report) |
| B19 | Larger changes are harder to understand, harder to review, harder to verify, and more expensive to unwind when something goes wrong. | Faros AI, "Speed Trap" (vendor) | 2026-09-18 | [link](https://www.faros.ai/blog/ai-speed-trap-takeaways) |
| B20 | you can't review code being generated faster than you can read it. You either become a bottleneck (defeats the point) or you rubber-stamp it (creates the debt). | trjordan, Hacker News | 2025-09-30 | [link](https://news.ycombinator.com/item?id=45424824) |
| B21 | If the narrative reads like a glow up photoshoot for the PR, something has gone extremely wrong. | hexaga, Hacker News | 2026-04-18 | [link](https://news.ycombinator.com/item?id=47813036) |

## 8. Unverified leads

Access gaps:
- **Reddit:** blocked to both fetch and search (HTTP 403; search refused the domain). The only Reddit material here comes through D15 and B5.
- **X:** fetch returned HTTP 402.
- **Lobsters:** protected by the Anubis anti-scraper page, so I didn't search it.

Leads:
- **X posts (snippets, search results only):**
  - Hunter Leath (@jhleath): "the team is starting to move away from AI coding completely (devin/claude/etc) because it's so much harder to review the AI code than writing things themselves" ([x.com](https://x.com/jhleath/status/1999589156314578961)).
  - Santiago (@svpino): "developers are now spending 70% of their time checking that code" (no source given for the 70%) ([x.com](https://x.com/svpino/status/1996610800040157642)).
  - Pratham (@Prathkum): "AI has made code generation 10 times easier but code review 10 times harder." ([x.com](https://x.com/Prathkum/status/1976031885630509543)).
  - donatj's tweet linked from [HN](https://news.ycombinator.com/item?id=44726992), not fetched.
- **Reddit threads listed by title only in the CMU appendix (D15):**
  - "made one rule for PRs: no diagram means no review. reviews got way faster." (r/devops)
  - "Is a large, mechanical PR better than a smaller, more complex one?" (r/ExperiencedDevs)
  - "the most productive thing i do every morning is read yesterday's merged PRs" (r/ExperiencedDevs)
- **GitClear "Write-Only Mode" primary page** ([link](https://www.gitclear.com/write_only_mode_ai_research)) returned 403. D6 rests on LeadDev's account.
- **LinearB figures seen only in CodeRabbit's guide:** "AI-assisted pull requests are 2.6 times larger", and 75th-percentile AI changes "exceeding 400 lines compared to 157 lines". I didn't find either on LinearB's pages.
- **Harness, "67% of developers spend more time debugging AI-generated code":** secondhand only.
- **Lightrun 2026, "43% of AI-generated code still requires manual debugging in production":** snippet only.
- **Baum, Schneider, Bacchelli (EMSE 2019), change ordering and working memory:** the snippet says review effectiveness is "significantly larger for small code changes". The Springer page was not fetched.
- **The file-ordering study (D12) cites prior work** in which developers found alphabetical ordering "cognitively misaligned" with how they understand multi-file PRs. I didn't look up that paper.
- **Tools named by practitioners as aids** (prior-art track): Stage, Haystack, Codebrief, Plannotator code tour, SmallDocs annotated walkthroughs, Google Code Wiki.
