# Demo: a Rasa agent that answers questions from the AI Engineering Field Guide

Rex is a career assistant for AI engineers, built with Rasa Pro 3.20
(Mantle).

Ask it who is hiring, which skills employers ask for, what the
interview process looks like, or how to prepare. It answers from
[Alexey Grigorev's AI Engineering Field Guide](https://github.com/alexeygrigorev/ai-engineering-field-guide).

The retrieval tool is
[minsearch](https://github.com/alexeygrigorev/minsearch), the keyword-search
library from the LLM course world: a small inverted index over
`title`, `company`, and `text`, fitted in memory at first call.

Python is 3.14, managed by uv (`uv sync` creates `.venv` from
`.python-version`).

## The corpus

`scripts/build_corpus.py` reads the field guide repo and writes
`data/field_guide_docs.json` (gitignored) — 1,274 documents, two kinds,
split by a `section` keyword field:

| section | documents | content |
|---|---|---|
| `guide` | 188 | the interview chapters, the question banks, research exports, the 51 per-company interview-process YAMLs, and awesome.md |
| `job` | 1,086 | every raw posting in the newest job-market snapshot (2026-09-23 at the time of writing) |

Job results are capped at two postings per company, so a who-is-hiring
question surfaces several companies instead of five copies of one.

## Tests

Scenarios live in `eval/scenarios/`. A simulator plays the user. A judge
scores the natural-language criteria. Assertions check the tracker and do
not depend on the judge. Mantle records tool calls as `tool_executed`
events, which assertions cannot target, so the search tool writes
`answer_question.last_query` / `last_hit_count` into skill memory and the
assertions watch those slots:

| Scenario | What it locks down |
|---|---|
| `who_is_hiring.yml` | the search runs, and the answer names at least two real hiring companies |
| `important_skills.yml` | the search runs, and the skills listed come from the guide, with no invented numbers |
| `off_topic_joke.yml` | "tell me a joke" does not trigger a search — no `last_query` slot is ever written |

## Voice

Rex talks using Deepgram, Rasa's built-in speech engines: Nova-3 for
speech-to-text and Aura-2 Thalia for text-to-speech. They are wired in
`integrations.yml` (`channels:` → `inspector:` and `browser_audio:`, both
with `name: deepgram`). In Mantle projects channels come from
`integrations.yml`; `credentials.yml` is only read by CALM v1 layouts.
`DEEPGRAM_API_KEY` lives in the repo-root `.env`. With that in place, the
mic button in `rasa inspect` turns the browser into a phone call.

Telephony channels (Twilio Media Streams, AudioCodes, Genesys Cloud,
Jambonz, SignalWire, Vonage) reuse the same engine config. Voice needs a
license with the `rasa:voice` scope; the Developer Edition key in this
repo's `.env` carries it.

## Run

Dependencies are `rasa-pro` 3.20.0 and `minsearch`, locked in `uv.lock`.
`pyproject.toml` sets `exclude-newer` to 2026-09-25 so `uv sync` still sees
that release when `~/.config/uv/uv.toml` says `exclude-newer = "7 days"`.

The agent calls `gpt-6-luna` with reasoning effort `medium`. The test
simulator and judge call `gpt-4o-mini` (`eval/conftest.yml`). Tool calls
need `LITELLM_ROUTE_ALL_CHAT_OPENAI_TO_RESPONSES=true` in the environment
before `rasa` starts; Rasa reads `.env` too late for that LiteLLM flag, so
it is also listed in the repo-root `.env` for launchers that export it first.

Secrets stay in the repo-root `.env` (`OPENAI_API_KEY`, and `RASA_LICENSE`
for the free Developer Edition). `.env` is gitignored. `rasa` loads it by
walking up from `demo/`.

```bash
git clone https://github.com/alexeygrigorev/ai-engineering-field-guide ../ai-engineering-field-guide

cd demo
uv sync
uv run python scripts/build_corpus.py   # writes data/field_guide_docs.json
uv run rasa train
uv run rasa run --enable-api
# another shell, still in demo/
uv run python scripts/run_evals.py
```

Reports land in `eval/results/<timestamp>/`. A run passes only when every
assertion and every criterion passes. Built-in quality scores (helpfulness,
task completion) are recorded and do not decide pass or fail.

`rasa inspect` opens a browser chat against the same model. If the server
refuses to start with "address already in use", a previous `rasa run` is
still holding port 5005.

## Report: 2026-09-24 17:23

Python 3.14.3, Rasa Pro 3.20.0, agent model `gpt-4.1`, simulator and judge
`gpt-4o-mini`. Command: `uv run python scripts/run_evals.py`. Source files:
`eval/results/2026-09-24_17-23-02/`.

| Scenario | Result | Time |
|---|---|---|
| A hiring question reaches the job postings | 1/1 | 17.1s |
| A skills question is answered from the guide | 1/1 | 15.3s |
| A joke request does not trigger a search | 1/1 | 8.8s |
| **Total** | **3/3** | **41.2s** |

### Who is hiring

```
User:  Hi! I'm looking to find out which companies are currently hiring
       AI engineers. Can you help with that?
Agent: Several companies are currently hiring AI engineers:
       - MARLOWE COMPANIES INC. (MCI) is hiring Senior Generative AI
         Engineers and Generative AI Engineers, with remote positions
         available in the USA.
       - BRAHMA AI has AI Engineer positions in Bengaluru, India.
       - Ergodic AI is recruiting AI Engineers for remote work, with a
         presence in the USA.
       - LawPro.ai is offering remote AI Engineer roles in the USA.
       (Sources: Job listings in the AI Engineering Field Guide)
```

Criteria: both passed (at least two real companies; nothing invented).
Assertions: `flow_started(answer_question)`,
`slot_was_set(answer_question.last_query)`,
`slot_was_set(answer_question.last_hit_count)`. Quality: bot 4.75/5, task
completion pass. Average turn latency 2.4s.

The first training of this run failed the two-company criterion: keyword
search ranked five postings from MARLOWE COMPANIES INC. on top, so the agent
named one company with five roles. The per-company cap in the tool fixed the
ranking; the eval caught it, which is the point of the test.

### Important skills

```
User:  What skills do employers typically look for in AI engineer roles?
Agent: Employers typically look for AI engineers who can deploy reliable
       APIs, build robust data pipelines, and work with agentic networks,
       retrieval, and fine-tuning methods ("AI Engineering Role Analysis").
       Hiring managers also value portfolio projects that demonstrate
       practical skills and clear documentation ("Getting Hired — Portfolio
       Strategy").
```

Criteria: both passed (concrete guide-grounded skills; no invented figures).
Assertions: `slot_was_set(answer_question.last_query)`. Quality: bot 4.5/5,
task completion pass. Average turn latency 2.7s.

### Joke

```
User:  Tell me a joke.
Agent: I'm not able to help with that here, but if you have questions about
       the topics I cover, I'd be glad to assist.
User:  Ok, never mind.
Agent: No problem! If you have any questions about AI engineering jobs,
       which skills matter, or what interviews are like, just let me know.
```

Criteria: all three passed (no joke, no search, stayed in scope).
Assertions: `answer_question.last_query` was never set. Quality: bot 2.0/5
and task completion failed, because the judge scored the user's request for
a joke, which this scenario requires the agent to refuse. Average turn
latency 1.2s.

## License

Training, running, and evaluating need `RASA_LICENSE`. The free key is
requested at <https://rasa.com/rasa-pro-developer-edition-license-key-request/>
and is emailed to you. Put the one-line key in the repo-root `.env`.
