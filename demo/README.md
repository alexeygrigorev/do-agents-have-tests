# Demo: "Do your agents have tests?"

A deliberately tiny Rasa 3.6 agent (bank balance lookup) that backs up the
LinkedIn post's thesis with a working example: **conversation tests as code,
failures caught before production, fixes in a diff you can review.**

## The story in the git history

1. `docs:` — internal comparison of Rasa vs alternatives (see `../docs/`).
2. `demo:` — the agent: balance flow, greetings, **no out-of-scope handling**
   (like most demo-grade agents).
3. `test:` — two conversation tests added, *test-first*:
   - happy path (balance lookup) → **passes**;
   - "tell me a joke" → expected `utter_default` → **fails**: the bot has no
     out-of-scope behavior, so it flails (`action_listen` / `action_default_fallback`).
     This is the exact failure mode the post talks about: the demo works,
     the untested path is broken, and nobody noticed — until a test ran.
4. `fix:` — out_of_scope intent + examples, FallbackClassifier, two fallback
   rules. Retrain, rerun: **2/2 stories, 10/10 actions green.**

The failing state is preserved in commit 3 (`results/` contains the failure
reports), the fix is commit 4 — the regression catch and the fix are both
reviewable diffs.

## How to run

```bash
# Rasa OSS 3.6.x needs Python 3.10/3.11
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python rasa "dask<2024.12"

cd demo
../.venv/bin/rasa train --fixed-model-name demo
../.venv/bin/rasa test --nlu data/nlu.yml --stories tests/test_stories.yml
```

Results land in `demo/results/` (`story_report.json`, `failed_test_stories.yml`).

## Hands-on findings (fed into the comparison doc)

1. **Packaging gap:** Rasa 3.6.21 has no dask pin for Python ≥3.11, so a plain
   `pip install rasa` on 3.11 leaves out dask and `rasa train` crashes; the
   newest dask versions break graph execution ("Cycle detected").
2. **`rasa test` exits 0 even when tests fail** (observed: 1/2 stories passing,
   exit code 0). You must parse `story_report.json` yourself for CI.
3. **E2E `user:` steps need intent annotations.** Text-only `user:` steps reach
   policies as raw text (no intent), and intent-trained policies can't predict
   from them — the documented format annotates each `user:` with its intent.
4. **The real end-to-end test framework (`rasa test e2e`: fixtures, response
   assertions) is Rasa Pro only.** OSS gets test stories, which is still more
   than most frameworks ship.
5. **Rules can't span two user turns** — validation catches it with a clear
   error (good!), you use stories for multi-turn flows.
