# Rasa vs. Alternatives — Internal Comparison

Internal notes for the LinkedIn post decision (not for publication). What Rasa is actually
good at, and where it falls short, judged against the axes that matter for the post's thesis:
*"do your agents have tests?"* — testing, versioning, deployability, auditability.

Verified against rasa.com, rasa.com/docs, and by hands-on use of Rasa Open Source (see
`demo/` in this repo).

## TL;DR

Rasa is the only mainstream agent framework where the answer to "do your agents have tests?"
is a first-class, file-based, CI-ready test suite — not a vendor web console. That is exactly
the discipline the post (and Rasa's own brief) says most teams are missing. The tradeoffs:
steep learning curve, YAML-heavy authoring, the LLM-native features (CALM) are locked behind
a Rasa Pro license, and the ecosystem is much smaller than LangChain's.

## Comparison matrix

| Axis | Rasa OSS/Pro | LangGraph / LangChain | Dialogflow CX / AWS Lex | Botpress / Voiceflow | DIY (pytest + eval libs) |
|---|---|---|---|---|---|
| Regression/conversation tests | First-class: YAML test stories, `rasa test`, `rasa test nlu --cross-validation`, JSON/Markdown reports, non-zero exit on failure | DIY with pytest/LangSmith (paid SaaS) | Web console test cases; not file-based, weak git story | In-builder testing; no real regression suite | Full control, zero scaffolding |
| Versioning / git-friendliness | Everything (NLU data, stories, config, tests) is files → PRs, diffs, reviews | Code-first, so git-native too | Flows exportable but awkward in git; versioning is platform concepts | Cloud-first, git story weak | Git-native |
| Deployment on own infra | Core strength: self-hosted, on-prem, air-gapped; Apache-2.0 OSS core | Self-host is DIY/possible; LangGraph Platform is a paid product | Managed only (vendor cloud) | Managed SaaS | Yours by definition |
| Auditability / inspectability | Full access to prompts, policies, training data, traces; deterministic core + LLM flexibility | Full (it's your code) | Black box; limited export | Black box | Full |
| LLM-native (2026) | Pro-only: CALM, flows, NL generation; OSS 3.6 is pre-LLM-era core | Strongest: built around LLMs | Vendor-managed LLM features | Decent | Whatever you build |
| Time to first demo | Slow: YAML, concepts (domains, stories, rules, slots), training step | Medium: code, but you wire everything | Fast: wizards, consoles | Fastest: visual builder | Slowest |
| Ecosystem / hiring | Niche but deep conversational-AI pool; fewer tutorials/examples | Largest community, most examples | Large enterprise pool | Small | n/a |
| Cost / licensing | OSS free; Pro requires license (the modern features) | OSS free; LangSmith paid | Usage-based cloud pricing | Subscription | Free, you pay in time |
| Heavy dependencies | Big install (TensorFlow), Python ≤3.11 for OSS 3.6 | Light-ish | none (API) | none | Light |

## Where Rasa is genuinely great

1. **The testing story is real, not marketing.** `rasa test nlu` runs k-fold cross-validation
   over your training data; conversation tests are YAML files in `tests/` that replay whole
   dialogues (including end-to-end mode that skips NLU); reports come out as JSON/Markdown;
   failed tests exit non-zero, so `rasa test` drops straight into CI. Verified in `demo/`.
2. **The agent is an artifact built from a repo.** NLU data, stories, config, and tests are
   plain files → reviewable PRs, diffs on behavior change, reproducible builds. This is the
   brief's "inspect, reproduce, and own what you ship" — and it holds up.
3. **Own infrastructure, for real.** Self-hosted/on-prem/air-gapped deployment, no data leaves
   your network. This is why banks (N26) are their customers, and why the managed-vendor
   black-box criticism doesn't apply to them.
4. **Proven in regulated industries.** N26 (bank, production in their secure cloud), ERGO,
   nib (five bots consolidated into one assistant, fallback rate 18% → 3.5%) — the "single
   foundation" pitch demonstrated in the wild.
5. **Determinism where it matters.** Rules/flows give predictable behavior for compliance-
   sensitive paths; LLM flexibility is opt-in rather than the default source of truth.

## Where Rasa is lacking

1. **The modern LLM-era features are paywalled.** CALM (build agents in natural language,
   flows) is Rasa Pro — license required. The pip-installable OSS (3.6.x) is the older
   intents/stories core. The brief's "build agents in natural language" is Pro-only.
2. **Steep learning curve.** Domains, intents, stories vs. rules, slots, actions, pipelines —
   far slower to first working bot than Dialogflow/Voiceflow, and the docs have rough edges
   (outdated pages exist).
3. **Slow OSS cadence, heavy stack.** OSS pins Python ≤3.11 and drags in TensorFlow; the
   install is hundreds of MB. Feels like 2019 engineering in an LLM world.
4. **Smaller ecosystem.** Fewer examples, integrations, Stack Overflow answers, and hires
   compared to LangChain/LangGraph. The conversational-AI niche is deep but narrow.
5. **You bring your own CI/CD.** It's CI-*friendly* (files + exit codes) but there's no
   productized pipeline story on the site — contrast with the brief's "agent factory" framing.
6. **No managed convenience.** Scaling, channel integrations, observability at scale are your
   ops problem. (This is the flip side of the on-prem strength.)

## Bottom line for the post

The comparison *strengthens* the post rather than undermining it: Rasa's genuine differentiator
is exactly the boring discipline (tests-as-files, reproducible deploys, own-infra auditability)
that the job-market data says is increasingly demanded. Where Rasa is weak (learning curve,
Pro licensing, ecosystem size) doesn't touch the post's claims — the post doesn't mention the
product at all.
