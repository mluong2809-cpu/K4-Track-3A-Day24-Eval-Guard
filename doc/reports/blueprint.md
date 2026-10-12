# Task 13 - proposed RAG and guard CI/CD blueprint

Team: NguyenMinhLuong (individual). Owner: Nguyen Minh Luong, 2A202602618.

This is a **proposal**, not an implemented workflow. Current evidence comprises 50 extractive-fallback answers, completed Tasks 1-12 source and 87 passing offline tests. Live A/B/C JSON artifacts are still missing, so RAGAS means, kappa, attack rate, false-positive rate and P95 are not asserted.

## Flow and failure actions

Input -> Presidio -> NeMo input -> RAG -> NeMo output -> response. Presidio detects and redacts national IDs, Vietnamese phone numbers and email addresses; an input carrying PII is blocked before RAG. NeMo input checks jailbreak, impersonation and requests for private data while allowing general policy questions. RAG should retrieve the effective policy version before generation. NeMo output checks identifiers, credentials and individual salary while preserving permitted policy answers. On guard API error or timeout, return a safe error and log the failure; an exception is not an `allowed` decision.

Log request id, rail type, decision, model id, config version and latency with PII redacted. Do not log raw secrets or sensitive contexts. Keep API keys in local `.env` or a CI secret store. If generation uses `extractive_fallback`, record that mode and a null generation model; do not present the text as LLM generation.

## Measurements and proposed gates

Task 12 scope is `input_layers_sequential`: two real warm-up calls, then at least 20 timed samples of Presidio followed by NeMo input in one event loop. Compute linear P50/P95/P99 from raw durations and the per-sample sum, never from the sum of layer percentiles. Presidio, NeMo input, sequential input guard, RAG, output rail and full request are **not measured** yet. The input-layer P95 target is 500 ms; there is no measured budget result. Measure full request separately from entry to response, including actual short-circuit paths.

A proposed CI job first runs offline tests and the schema/source-hash checker. In an environment with secrets, it then runs A/B/C and fails on RAGAS faithfulness mean below 0.75, overall `avg_score` below 0.65, fewer than 18/20 attacks blocked, any of 8 clean inputs blocked, or any of 4 outputs wrong. The lab minimum is 15/20 attacks; 18/20 is the bonus and proposed CI threshold. Add a full-request P95 <500 ms gate only after measuring that scope. Scripts must check these values and exit nonzero; Markdown thresholds alone do not create gates.

## Monitoring and improvements

Track weekly metric means by distribution, cited policy versions, fallback rate, judge swap disagreement, clean false positives, attack pass rate, output blocks and per-layer P95. Review redacted false positives, adjust policy and add clean regression cases. Rerun the 50 questions whenever corpus, effective dates, model or prompt changes. The 50/20/8/4 lab sets are small; production evaluation needs larger de-identified traffic samples. Initial answer inspection suggests policy-version filtering for IDs 41/49, negation checks for ID 47 and VPN retrieval repair for ID 50. Reprioritize these from the measured bottom 10 when Phase A is available.
