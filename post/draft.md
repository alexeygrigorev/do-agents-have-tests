# LinkedIn post — draft 2 (data-backed)

Status: ready to send to Maria for factual-accuracy review.
Disclosure line required by Rasa's brief included at the bottom.

---

I analyzed 6,964 AI engineering job descriptions.

59.7% of AI-first roles now require evaluation-related skills: LLM evaluation, guardrails,
monitoring, observability.

The most wanted skill in AI engineering isn't building agents. It's proving they actually work.

I keep hearing the same story from teams: three different agents built by three different
teams, and not one of them has a test suite.

That's the real problem with AI agents right now. Not the models — they're good and getting
better. The problem is that a demo takes a weekend, and something you'd trust with your
customers takes software engineering: prompt tests, an eval dataset, staged rollouts,
monitoring, versioning.

The job market is catching on. It's demanding the boring discipline.

I ran this experiment myself: I built a tiny customer-assistant agent, wrote its conversation
tests first, and the tests caught a broken path that every demo had sailed straight past.
Fixed in one diff. That's the whole game.

The teams that treat agents like software — tests, evals, versioning, rollbacks — are the
ones whose agents survive production.

Everyone else is still showing demos.

Do your agents have tests?

_Paid partnership with Rasa._

---

### Notes for the factual-accuracy review

- 6,964 job descriptions, 59.7% of AI-First roles: from my own published research
  (AI Engineering Field Guide, skills analysis, Evaluation Skills section).
- The mid-post paragraph about scattered agents is intentionally generic — no vendor claims.
- The "ran this experiment myself" paragraph is backed by the demo in this repo
  (conversation test caught a missing fallback path; fix in one commit).
- No mention of Rasa or any product anywhere in the post — per the brief, a reaction,
  not an endorsement.
