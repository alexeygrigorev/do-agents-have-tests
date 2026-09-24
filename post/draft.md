# LinkedIn post — draft 2 (data-backed)

I analyzed nearly 7,000 AI engineering job descriptions. 60% require evaluation-related skills: LLM evaluation, guardrails, monitoring, observability.

The most wanted skill in AI engineering is not building agents. It's making sure they work.

That's the real problem with AI agents right now. You create a proof of concept in a day, but it breaks when real customers start using it.

To solve this problem, we treat the agent as the rest of the production code: we add tests, evals and versioning. 

With Rasa, it's very simple: evals are YAML files. For each case you describe

- the scenario
- the evaluation criteria
- deterministic checks

And run it with a simple command. 

Here in this demo I show how I do it. 

Do your agents have tests?


This post was created in collaboration with Rasa. Thank you for supporting our community!

![alt text](image.png)