from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json, math, asyncio, time
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass, asdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run the four RAGAS metrics and report the evaluator models actually used."""
    metric_names = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
    if not (len(questions) == len(answers) == len(contexts) == len(ground_truths)):
        raise ValueError("Evaluation inputs must have equal lengths")
    if not questions:
        raise ValueError("RAGAS requires at least one question")

    from config import OPENAI_API_KEY, GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL, EMBEDDING_MODEL
    # On Windows, load Torch before RAGAS/LangChain to avoid a late c10.dll load failure.
    import torch  # noqa: F401
    from datasets import Dataset
    from langchain_openai import ChatOpenAI
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from ragas.run_config import RunConfig

    api_key = OPENAI_API_KEY or GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("An OpenAI or Gemini API key is required for RAGAS evaluation")
    llm_model = os.getenv("RAGAS_EVALUATOR_MODEL", "gpt-4o-mini" if OPENAI_API_KEY else GEMINI_MODEL)
    llm_kwargs = {"model": llm_model, "api_key": api_key, "temperature": 0}
    if not OPENAI_API_KEY:
        llm_kwargs["base_url"] = GEMINI_BASE_URL
        llm_kwargs["max_retries"] = 0
    llm = ChatOpenAI(**llm_kwargs)
    if not OPENAI_API_KEY:
        from openai import RateLimitError

        request_lock = asyncio.Lock()
        next_start = 0.0

        class GeminiSingleCompletion(BaseChatModel):
            """Use one candidate per request and respect Gemini's free-tier rate."""

            delegate: Any

            @property
            def _llm_type(self) -> str:
                return "gemini_single_completion"

            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                kwargs.pop("n", None)
                return self.delegate._generate(messages, stop=stop,
                                               run_manager=run_manager, n=1, **kwargs)

            async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
                nonlocal next_start
                kwargs.pop("n", None)
                async with request_lock:
                    wait = next_start - time.monotonic()
                    if wait > 0:
                        await asyncio.sleep(wait)
                    next_start = time.monotonic() + 4.5
                try:
                    return await self.delegate._agenerate(messages, stop=stop,
                                                          run_manager=run_manager, n=1, **kwargs)
                except RateLimitError:
                    async with request_lock:
                        next_start = max(next_start, time.monotonic() + 65)
                    raise

        llm = GeminiSingleCompletion(delegate=llm)
    embedding_model = EMBEDDING_MODEL
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu", "local_files_only": True},
        )
    except (OSError, ValueError):
        embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu", "local_files_only": True},
        )
    dataset = Dataset.from_dict({
        "question": questions, "answer": answers,
        "contexts": contexts, "ground_truth": ground_truths,
    })
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(timeout=600, max_retries=2, max_workers=4),
        raise_exceptions=True,
    )
    frame = result.to_pandas()
    if len(frame) != len(questions):
        raise ValueError(f"RAGAS returned {len(frame)} rows for {len(questions)} questions")
    per_question = []
    for index, (_, row) in enumerate(frame.iterrows()):
        scores = {name: float(row[name]) for name in metric_names}
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in scores.values()):
            raise ValueError(f"Invalid RAGAS score at row {index}: {scores}")
        per_question.append(EvalResult(
            question=questions[index], answer=answers[index],
            contexts=contexts[index], ground_truth=ground_truths[index],
            **scores,
        ))
    return {
        **{name: sum(getattr(item, name) for item in per_question) / len(per_question)
           for name in metric_names},
        "per_question": per_question,
        "metadata": {"evaluator_models": [llm_model, embedding_model]},
        "status": "evaluated",
    }


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating", "Tighten system prompt and set temperature to 0"),
        "context_recall": ("Missing relevant chunks", "Improve chunking or add BM25 keywords"),
        "context_precision": ("Irrelevant chunks ranked too high", "Add cross-encoder reranking or metadata filter"),
        "answer_relevancy": ("Answer misses the question", "Rewrite prompt for a direct answer"),
    }
    metrics = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
    failures = []
    for item in eval_results:
        values = {name: getattr(item, name) for name in metrics}
        worst_metric = min(values, key=values.get)
        diagnosis, suggested_fix = diagnostic_tree[worst_metric]
        failures.append({
            "question": item.question,
            "answer": item.answer,
            "ground_truth": item.ground_truth,
            "contexts": item.contexts,
            "metrics": values,
            "worst_metric": worst_metric,
            "score": sum(values.values()) / len(values),
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })
    return sorted(failures, key=lambda item: item["score"])[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    evaluated = [asdict(item) for item in results.get("per_question", [])]
    predictions = results.get("predictions", [])
    report = {
        "aggregate": {k: results[k] if results.get("status") == "evaluated" else None
                      for k in ("faithfulness", "answer_relevancy", "context_precision", "context_recall")},
        "num_questions": len(predictions) if predictions else len(evaluated),
        "failures": failures,
        "per_question": evaluated if evaluated else predictions,
        "status": results.get("status", "unknown"),
    }
    if results.get("error"):
        report["error"] = results["error"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
