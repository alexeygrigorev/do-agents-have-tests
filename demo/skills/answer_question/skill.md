---
name: Answer Field Guide Question
description: >
  Answer questions about the AI engineering job market from the AI
  Engineering Field Guide: who is hiring, which skills employers ask for,
  interview processes, interview questions, and career preparation.
  Activate only when the user asks such a question.
---

Answer one question using the field guide corpus, never your own knowledge.

1. Turn the request into a short keyword query and call `search_field_guide`.
   For who-is-hiring questions or questions about a specific company, pass
   `section: "job"`. For interview process, interview questions, skills,
   trends, or preparation advice, pass `section: "guide"`. When unsure, leave
   `section` empty.
2. Answer from the results only, in two to four sentences. Name the
   companies, roles, or guide sections the answer comes from.
3. If the results do not answer the question, say the guide does not cover
   it. Never invent companies, roles, skills, salaries, or statistics.
