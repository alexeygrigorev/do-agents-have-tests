# Research Notes — Rasa brief vs. reality

Background research done before writing the post (Sept 2026). Sources: Rasa's
collaboration brief (PDF), rasa.com, rasa.com/docs, and hands-on use of Rasa.

The runnable demo in `demo/` is a **Rasa Pro 3.20 Mantle agent** (LLM skill +
tools) with simulation scenarios under `eval/scenarios/`. It needs Python
3.11–3.14 (this machine uses 3.12) and `RASA_LICENSE`. The notes below about
Open Source 3.6.21 are the earlier intent/story experiment, kept as findings,
not a description of the current demo.

## The brief (what Rasa asked for)

- One LinkedIn post, Alexey's angle and words, no script. Rasa reviews for
  **factual accuracy and messaging fit only** — "not rewriting your voice."
- Part 1 of the brief is the premise to *react to*: agent projects are
  scattered across teams (prototype here, demo-grade bot there, managed vendor
  elsewhere) with none of the discipline that makes software maintainable —
  no shared components, no tests, no repeatable deploys. Both standard fixes
  cost the same discipline: build your own framework (maintenance burden) or
  rent a managed vendor (black box you can't test, deploy, or audit on your
  own terms).
- Rasa's position: an "agent factory" — a single foundation on **your own
  infrastructure**, shared reusable components, full lifecycle (build, test,
  release, improve from real conversations).
- The explicit ask: *"A reaction. The most useful post you could write is the
  one you'd write anyway if we weren't paying you."*
- Process: publish from Alexey's account with a paid-partnership disclosure;
  Rasa amplifies via LinkedIn Thought Leader Ads (post stays under Alexey's
  name); flat fee, independent of performance.

## Verification: brief claims vs. rasa.com / docs

| Brief claim | Reality check | Verdict |
|---|---|---|
| "Runs in your own infrastructure… inspect, reproduce, own what you ship" | Homepage leads with on-prem/private-cloud deployment (incl. air-gapped), "built with regulated industries in mind"; open framework, full access to prompts/policies/codebase | ✅ accurate |
| "Test them before going live… release without breaking production" | Docs open with "build, test, deploy, and analyze AI agents at scale"; versioning, tracing, and eval tooling are first-class | ✅ accurate (hands-on: `demo/`) |
| "Build agents in natural language" | That's **CALM — Rasa Pro only**. Pip-installable OSS 3.6.x is the older intents/stories core | ⚠️ Pro-only, not OSS |
| "Trusted by some of the largest, most demanding companies" | Named customers: N26 (bank — "concept to production in four weeks in their secure cloud"), ERGO, nib, Swisscom, T-Mobile, Orange, Albert Heijn; homepage hero is a banking-agent demo | ✅ accurate, banking is literal |

Useful case study found while checking: **nib Group consolidated five bots
into a single assistant**, fallback rate 18% → 3.5% — the brief's "replace the
scatter with a single foundation" pitch demonstrated in the wild.

## Hands-on findings (Rasa OSS 3.6.21, Python 3.11)

1. **Packaging gap:** no dask pin for Python ≥3.11 — a plain install crashes
   on `rasa train`; newest dask versions break the graph runner ("Cycle
   detected"). Needs `dask<2024.12` pinned by hand.
2. **`rasa test` exits 0 even when conversation tests fail** — CI must parse
   `story_report.json` itself.
3. Test-story `user:` steps need `intent:` annotations; text-only steps reach
   policies as raw text and intent-trained policies can't act on them.
4. **The modern end-to-end test framework (`rasa test e2e`: fixtures, response
   assertions) is Rasa Pro only.** OSS gets YAML test stories — still more
   than most frameworks ship.
5. Rules can't span two user turns (validation catches it clearly); multi-turn
   flows go in stories.

Full competitive comparison: `docs/rasa-vs-alternatives.md`.

## How this maps to the post (`post/draft.md`)

- The post's thesis (59.7% of AI-first roles demand evaluation skills; teams
  that treat agents like software survive production) is **independent
  evidence for the brief's premise** — without naming the product, which is
  exactly what the brief asks for ("a reaction, not an endorsement").
- The "ran this experiment myself" paragraph is backed by commits 2–4 of this
  repo: conversation test caught the missing out-of-scope path, fix in one
  reviewable diff.
- Every number in the post comes from Alexey's own published research
  (AI Engineering Field Guide, ~7k job descriptions), so the factual-accuracy
  review has nothing to flag.
