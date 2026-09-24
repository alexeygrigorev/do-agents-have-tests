# Demo: a Rasa agent, with the tests Rasa ships for agents

Ada is a small bank assistant built with **Rasa Pro 3.20 (Mantle)**, the
current release. She is an LLM agent: a skill description routes the
conversation, and Python tools return the balance. This is not the older
intent/story bot (Rasa Open Source 3.6).

Python is 3.14, managed by uv (`uv sync` creates `.venv` from
`.python-version`). The Open Source 3.6 line, which stopped at Python 3.11,
is not used here.

## What the tests check

Scenarios live in `eval/scenarios/`. A simulator plays the customer. A judge
scores the natural-language criteria. Assertions check the tracker and do not
depend on the judge:

| Scenario | What it locks down |
|---|---|
| `balance_named_up_front.yml` | "Rainy Day Savings" starts `check_balance`, `get_balance` writes the account label, and the reply contains €1,234.56 |
| `joke_starts_nothing.yml` | "tell me a joke" does not select an account and does not speak either balance |

That second case is the out-of-scope path. The agent rules say a joke must
not start a skill and must not be answered as a joke.

## Run

Dependencies are `rasa-pro` 3.20.0, locked in `uv.lock`. `pyproject.toml`
sets `exclude-newer` to 2026-09-25 so `uv sync` still sees that release
when `~/.config/uv/uv.toml` says `exclude-newer = "7 days"`.

The agent calls `gpt-4.1`. The test simulator and judge call `gpt-4o-mini`
(`eval/conftest.yml`).

Secrets stay in the repo-root `.env` (`OPENAI_API_KEY`, and `RASA_LICENSE`
for the free Developer Edition). `.env` is gitignored. `rasa` loads it by
walking up from `demo/`.

```bash
cd demo
uv sync
uv run rasa train
uv run rasa run --enable-api
# another shell, still in demo/
uv run python scripts/run_evals.py
```

Reports land in `eval/results/<timestamp>/`. A run passes only when every
assertion and every criterion passes. Built-in quality scores (helpfulness,
task completion) are recorded and do not decide pass or fail.

`rasa inspect` opens a browser chat against the same model.

## Report: 2026-09-24 16:20

Python 3.14.3, Rasa Pro 3.20.0, agent model `gpt-4.1`, simulator and judge
`gpt-4o-mini`. Command: `uv run python scripts/run_evals.py`. Source files:
`eval/results/2026-09-24_16-20-53/`.

| Scenario | Result | Time |
|---|---|---|
| Customer names the savings account and gets its balance | 1/1 | 18.6s |
| A joke request does not start a balance lookup | 1/1 | 10.0s |
| **Total** | **2/2** | **28.6s** |

### Balance

```
User:  Could you tell me the balance of my Rainy Day Savings account?
Agent: Your Rainy Day Savings account balance is €1,234.56.
User:  Thanks, that's all I needed.
Agent: Can I assist you with anything else?
```

Criteria: both passed (did not ask which account; stated the savings balance
and the account name). Assertions: `flow_started(check_balance)`,
`slot_was_set(check_balance.selected_account_id='acc_savings')`,
`slot_was_set(check_balance.selected_account_label='Rainy Day Savings')`,
`bot_uttered` matching `1,234.56`. Quality: bot 5.0/5, task completion pass.
Average turn latency 3.8s.

### Joke

```
User:  Tell me a joke.
Agent: I can’t help with that here, but I’m happy to assist if you have a question about what I’m set up to do.
User:  Ok, never mind.
Agent: No problem! If you need to check an account balance, just let me know.
```

Criteria: all three passed (no joke, no balance lookup, offered a balance
check or refused the joke). Assertions: `selected_account_id` was not set,
and neither €1,234.56 nor €1,284.53 was spoken. Quality: bot 2.75/5.
Helpfulness 1/5 and task completion failed, because the judge scored the
user's request for a joke, which this scenario requires the agent to refuse.
Average turn latency 1.8s.

## License

Training, running, and evaluating need `RASA_LICENSE`. The free key is
requested at <https://rasa.com/rasa-pro-developer-edition-license-key-request/>
and is emailed to you. Put the one-line key in the repo-root `.env`.
