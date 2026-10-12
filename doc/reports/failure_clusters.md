# Phase A - preliminary analysis and run status

Team: NguyenMinhLuong (individual). Owner: Nguyen Minh Luong, 2A202602618.

Inputs: `artifacts/answers_50q.json` and `fixtures/test_set_50q.json`. The 50 answers retain all ids and distributions (20 factual, 20 multi_hop, 10 adversarial), with three contexts each. All 50 are `extractive_fallback` with `generation_model=null`.

## RAGAS results

**Not measured.** `artifacts/ragas_50q.json` does not exist. RAGAS initialized Gemini and the local MiniLM embeddings, but automatic approval rejected sending the 50 questions, answers, contexts and references to Gemini. There are no valid metric values, bottom 10 by score, worst-metric matrix, distribution means, or evaluator metadata from a completed run. None are inferred or fabricated here.

## Direct observations from saved answers

- ID 41 asks for current annual-leave days. The answer quotes the registration procedure from the 2024 file but omits the 15-day allowance; the reference distinguishes the obsolete 12-day rule. Retrieve the allowance section and verify both the count and the policy version.
- ID 47 asks whether staff should handle malware themselves. The answer quotes incident-severity timing but misses the required negation and one-hour reporting procedure. Retrieve the handling procedure and verify the negation and deadline.
- ID 49 asks about both the old and current policy. The answer quotes only the 2023 version. Retrieve both versions and state which one remains effective.
- ID 50 asks about personal VPN use while working from home. Retrieval supplied a performance-review document. Add VPN-specific retrieval and source relevance checks.

These observations come from the saved text; they are **not** a RAGAS bottom 10. Once the live run is approved, run `python scripts/run_experiments.py --phase a --live`, populate all four metric columns, the bottom 10 and matrix from its JSON, and choose the weakest distribution using the lowest mean `avg_score`.
