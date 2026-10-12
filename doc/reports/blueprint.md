# Task 13 - proposed RAG and guard CI/CD blueprint

Team: NguyenMinhLuong (individual). Owner: Nguyen Minh Luong, 2A202602618.

This is a **proposal**, not an implemented workflow. Current evidence comprises 50 extractive-fallback answers, 91 passing offline tests, and live Phase A/B artifacts. Phase C is being measured separately; attack rate, false-positive rate and P95 will be reported from its saved artifact.

## Flow and failure actions

Input -> Presidio -> NeMo input -> RAG -> NeMo output -> response. Presidio detects and redacts national IDs, Vietnamese phone numbers and email addresses; an input carrying PII is blocked before RAG. NeMo input checks jailbreak, impersonation and requests for private data while allowing general policy questions. RAG should retrieve the effective policy version before generation. NeMo output checks identifiers, credentials and individual salary while preserving permitted policy answers. On guard API error or timeout, return a safe error and log the failure; an exception is not an `allowed` decision.

Log request id, rail type, decision, model id, config version and latency with PII redacted. Do not log raw secrets or sensitive contexts. Keep API keys in local `.env` or a CI secret store. If generation uses `extractive_fallback`, record that mode and a null generation model; do not present the text as LLM generation.

## Measurements and proposed gates

Phase A measured overall four-metric mean 0.718 across 50 answers; `multi_hop` has the lowest mean (0.596), versus factual 0.803 and adversarial 0.793. Phase B measured Cohen's κ=1.0 on the ten supplied `model_answer` records, with 0/5 swap disagreements and 2/3 longer winners among decisive pairs. These small sets support regression tracking, not production reliability claims. Phase C guard and latency measurements are in progress.

Task 12 scope is `input_layers_sequential`: two real warm-up calls, then at least 20 timed samples of Presidio followed by NeMo input in one event loop. Compute linear P50/P95/P99 from raw durations and the per-sample sum, never from the sum of layer percentiles. RAG, output rail and full request are **not measured** in this task. The input-layer P95 target is 500 ms; if the measured value exceeds it, retain the actual value and analyze the NeMo/API cost. Measure full request separately from entry to response, including actual short-circuit paths.

A proposed CI job first runs offline tests and the schema/source-hash checker. In an environment with secrets, it then runs A/B/C and fails on RAGAS faithfulness mean below 0.75, overall `avg_score` below 0.65, multi-hop `avg_score` below 0.65, fewer than 18/20 attacks blocked, any of 8 clean inputs blocked, or any of 4 outputs wrong. The measured A batch would **fail** the proposed multi-hop gate (0.596), giving a concrete repair target. The lab minimum is 15/20 attacks; 18/20 is the bonus and proposed CI threshold. Add a full-request P95 <500 ms gate only after measuring that scope. Scripts must check these values and exit nonzero; Markdown thresholds alone do not create gates.

## Monitoring and improvements

Track weekly metric means by distribution, cited policy versions, fallback rate, judge swap disagreement, clean false positives, attack pass rate, output blocks and per-layer P95. Review redacted false positives, adjust policy and add clean regression cases. Rerun the 50 questions whenever corpus, effective dates, model or prompt changes. The 50/20/8/4 lab sets are small; production evaluation needs larger de-identified traffic samples. The measured Phase A bottom 10 prioritizes multi-hop evidence joining (IDs 25/27/30/33/35/40), extraction of the decisive span (IDs 2/5/7), and effective-policy selection (IDs 33/49).

NeMo 0.10.0 uses `src/nemo_exact_index.py` for its small flow indexes when native Annoy is unavailable on Windows. The local MiniLM model and exact cosine ranking were smoke-tested; future Phase C metadata/report should disclose this search backend. This does not replace NeMo input/output LLM checks.

Offline Presidio check on the supplied input fixtures flagged attack ids 1-4 and no clean input. This checks only local PII detection, not NeMo attack blocking, output safety or sequential latency.
