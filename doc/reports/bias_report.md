# Phase B - judge calibration run status

Team: NguyenMinhLuong (individual). Owner: Nguyen Minh Luong, 2A202602618.

**No live judgments yet.** `artifacts/judge_results.json` has not been created. Mock tests verify the source logic but cannot supply genuine winners, kappa or bias rates.

The fixed pair ids are 1, 5, 12, 21 and 41. Candidate A comes from `artifacts/answers_50q.json:answer`; B comes from `fixtures/human_labels_10q.json:model_answer`; question and ground truth come from `fixtures/test_set_50q.json`. The second pairwise pass reverses A/B, then maps its winner and scores back to the original identities. The ten binary judgments score the exact supplied `model_answer` against its reference, without passing `human_label` or `human_note` to the judge.

After approval to send those fields to Gemini, run `python scripts/run_experiments.py --phase b --live`. Then report both passes and reasoning/scores for all five pairs; judge and human labels in the same order for all ten items; observed and expected agreement and Cohen's kappa; position inconsistency; and longer-winner counts among decisive cases. With five pairs and ten labels, inspect each disagreement before attributing it to position or answer length.
