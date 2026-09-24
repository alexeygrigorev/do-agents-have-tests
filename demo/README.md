# Demo: a Rasa agent, with the tests Rasa ships for agents

Ada is a small bank assistant built with **Rasa Pro 3.20 (Mantle)**, the
current release. She is an LLM agent: a skill description routes the
conversation, and Python tools return the balance. This is not the older
intent/story bot (Rasa Open Source 3.6).

Python 3.11 through 3.14 work. This machine uses 3.12. The Open Source 3.6
line, which stopped at Python 3.11, is not used here.

## What the tests check

Scenarios live in `eval/scenarios/`. A simulator plays the customer. A judge
scores the natural-language criteria. Assertions check the tracker and do not
depend on the judge:

| Scenario | What it locks down |
|---|---|
| `balance_named_up_front.yml` | "Rainy Day Savings" starts `check_balance`, calls `get_balance`, and the reply contains €1,234.56 |
| `joke_starts_nothing.yml` | "tell me a joke" does not select an account and does not speak either balance |

That second case is the out-of-scope path. The agent rules say a joke must
not start a skill and must not be answered as a joke.

## Run

`rasa-pro` 3.20.0 is installed in `../.venv-pro` (Python 3.12). A global uv
setting, `exclude-newer = "7 days"` in `~/.config/uv/uv.toml`, hides that
release until the cutoff is moved. The install that created this environment
used `--exclude-newer 2026-09-25`.

Secrets stay in the repo-root `.env` (`OPENAI_API_KEY`, and `RASA_LICENSE`
for the free Developer Edition). `.env` is gitignored. `rasa` loads it by
walking up from `demo/`.

```bash
cd demo
../.venv-pro/bin/rasa train
../.venv-pro/bin/rasa run
# another shell, still in demo/
../.venv-pro/bin/python scripts/run_evals.py
```

Reports land in `eval/results/<timestamp>/`. A run passes only when every
assertion and every criterion passes.

`rasa inspect` opens a browser chat against the same model.

## License

Training, running, and evaluating need `RASA_LICENSE`. The free key is
requested at <https://rasa.com/rasa-pro-developer-edition-license-key-request/>
and is emailed to you. Put the one-line key in the repo-root `.env`.
