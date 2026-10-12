from __future__ import annotations

"""Phase C: Production Guardrails — Presidio PII + NeMo Guardrails + P95 Latency."""

import asyncio
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (ADVERSARIAL_SET_PATH, GUARDRAILS_CONFIG_DIR, LATENCY_BUDGET_P95_MS,
                    PRESIDIO_LANGUAGE, OPENAI_API_KEY, GEMINI_API_KEY, GEMINI_MODEL,
                    GEMINI_BASE_URL)


# ─── Task 9a: Presidio PII Detection ─────────────────────────────────────────

def setup_presidio():
    """Khởi tạo Presidio engine với custom Vietnamese PII recognizers. (Đã implement sẵn)

    Pattern recognizers used:
        VN_CCCD  — số CCCD 12 chữ số hoặc CMND 9 chữ số
        VN_PHONE — số điện thoại Việt Nam (0[3-9]xxxxxxxx)
        EMAIL_ADDRESS — địa chỉ email

    A NoOp NLP engine keeps these deterministic recognizers usable without a
    downloaded spaCy model; it does not perform general named-entity detection.
    """
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
    from presidio_analyzer.nlp_engine import NoOpNlpEngine
    from presidio_anonymizer import AnonymizerEngine

    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        patterns=[
            Pattern("CCCD 12 digits", r"\b\d{12}\b", 0.9),
            Pattern("CMND 9 digits",  r"\b\d{9}\b",  0.7),
        ],
    )
    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        patterns=[Pattern("VN mobile", r"\b0[3-9]\d{8}\b", 0.9)],
    )
    email_recognizer = PatternRecognizer(
        supported_entity="EMAIL_ADDRESS",
        patterns=[Pattern("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", 0.85)],
    )

    registry = RecognizerRegistry()
    registry.add_recognizer(cccd_recognizer)
    registry.add_recognizer(phone_recognizer)
    registry.add_recognizer(email_recognizer)

    # Pattern recognizers work without the large spaCy model; NoOp does no NER.
    nlp_engine = NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "noop"}])
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


def pii_scan(text: str, analyzer=None, anonymizer=None) -> dict:
    """Task 9a: Quét PII trong văn bản bằng Presidio.

    Returns:
        {
          "has_pii":    bool,
          "entities":   [{"type": str, "text": str, "score": float, "start": int, "end": int}],
          "anonymized": str,   # text với PII được thay bằng <TYPE>
        }
    """
    # if analyzer is None or anonymizer is None:
    #     analyzer, anonymizer = setup_presidio()
    #
    # results = analyzer.analyze(text=text, language=PRESIDIO_LANGUAGE)
    # if not results:
    #     return {"has_pii": False, "entities": [], "anonymized": text}
    #
    # anonymized = anonymizer.anonymize(text=text, analyzer_results=results).text
    # entities = [
    #     {"type": r.entity_type, "text": text[r.start:r.end],
    #      "score": round(r.score, 3), "start": r.start, "end": r.end}
    #     for r in results
    # ]
    # return {"has_pii": True, "entities": entities, "anonymized": anonymized}
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()
    matches = analyzer.analyze(text=text, language=PRESIDIO_LANGUAGE)
    entities = [{"type": match.entity_type, "text": text[match.start:match.end],
                 "score": float(match.score), "start": match.start, "end": match.end}
                for match in matches]
    anonymized = anonymizer.anonymize(text=text, analyzer_results=matches).text if matches else text
    return {"has_pii": bool(matches), "entities": entities, "anonymized": anonymized}


# ─── Task 9b + 11: NeMo Guardrails ───────────────────────────────────────────

def setup_nemo_rails():
    """Khởi tạo NeMo Guardrails từ guardrails/config.yml. (Đã implement sẵn)

    Config directory: guardrails/
        config.yml  — model + rails config
        rails.co    — câu từ chối Colang 1.0; built-in self-check flows được bật trong YAML
    """
    try:
        import annoy  # noqa: F401
        has_annoy = True
    except ImportError:
        has_annoy = False
    from nemoguardrails import RailsConfig, LLMRails
    config = RailsConfig.from_path(GUARDRAILS_CONFIG_DIR)
    if GEMINI_API_KEY and not OPENAI_API_KEY:
        for model in config.models:
            if model.type == "main":
                model.model = GEMINI_MODEL
                model.parameters.update({"base_url": GEMINI_BASE_URL, "api_key": GEMINI_API_KEY})
        from langchain_openai import ChatOpenAI
        from src.gemini_backend import RateLimitedGeminiChat
        llm = RateLimitedGeminiChat(delegate=ChatOpenAI(
            model=GEMINI_MODEL, api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL,
            temperature=0, max_retries=0,
            model_kwargs={"reasoning_effort": "low"},
        ))
    else:
        llm = None
    if has_annoy:
        rails = LLMRails(config, llm=llm)
    else:
        from src.nemo_exact_index import ExactMiniLMIndex, warm_model
        warm_model()

        class RailsWithExactIndex(LLMRails):
            def _get_embeddings_search_provider_instance(self, esp_config=None):
                return ExactMiniLMIndex()

        rails = RailsWithExactIndex(config, llm=llm)
    return rails


async def check_input_rail(text: str, rails=None) -> dict:
    """Task 9b: Kiểm tra input qua NeMo input rails (topic guard + jailbreak guard).

    Returns:
        {
          "allowed":        bool,
          "blocked_reason": str | None,
          "response":       str,          # NeMo's raw response
        }
    """
    # if rails is None:
    #     rails = setup_nemo_rails()
    #
    # result = await rails.generate_async(
    #     messages=[{"role": "user", "content": text}],
    #     options={"rails": ["input"], "log": {"activated_rails": True}},
    # )
    # response = result.response[0]["content"]
    # # Đọc quyết định rail; không suy ra blocked từ từ khóa có thể nằm trong input sạch.
    # blocked = any(rail.stop for rail in result.log.activated_rails)
    # return {
    #     "allowed":        not blocked,
    #     "blocked_reason": "nemo_input_rail" if blocked else None,
    #     "response":       response,
    # }
    if rails is None:
        rails = setup_nemo_rails()
    result = await rails.generate_async(
        messages=[{"role": "user", "content": text}],
        options={"rails": ["input"], "log": {"activated_rails": True}},
    )
    blocked = any(rail.stop for rail in result.log.activated_rails)
    return {"allowed": not blocked,
            "blocked_reason": "nemo_input_rail" if blocked else None,
            "response": result.response[0]["content"]}


async def check_output_rail(question: str, answer: str, rails=None) -> dict:
    """Task 11: Kiểm tra LLM output qua NeMo output rails trước khi trả về user.

    NeMo output rails hoạt động trong context của cả cuộc hội thoại (input + output).
    Kiểm tra PII và nội dung nhạy cảm. Self-check này không thay RAGAS faithfulness
    hoặc kiểm tra factual accuracy với retrieved contexts.

    Returns:
        {
          "safe":           bool,
          "flagged_reason": str | None,
          "final_answer":   str,          # answer đã qua guard (có thể bị redact)
        }
    """
    # if rails is None:
    #     rails = setup_nemo_rails()
    #
    # # Cung cấp context đầy đủ để output rail hoạt động
    # result = await rails.generate_async(
    #     messages=[
    #         {"role": "user", "content": question},
    #         {"role": "assistant", "content": answer},
    #     ],
    #     options={"rails": ["output"], "log": {"activated_rails": True}},
    # )
    # response = result.response[0]["content"]
    # flagged = any(rail.stop for rail in result.log.activated_rails)
    # return {
    #     "safe":           not flagged,
    #     "flagged_reason": "nemo_output_rail" if flagged else None,
    #     "final_answer":   response if flagged else answer,
    # }
    if rails is None:
        rails = setup_nemo_rails()
    result = await rails.generate_async(
        messages=[{"role": "user", "content": question},
                  {"role": "assistant", "content": answer}],
        options={"rails": ["output"], "log": {"activated_rails": True}},
    )
    flagged = any(rail.stop for rail in result.log.activated_rails)
    return {"safe": not flagged,
            "flagged_reason": "nemo_output_rail" if flagged else None,
            "final_answer": result.response[0]["content"] if flagged else answer}


# ─── Task 10: Adversarial Test Suite ─────────────────────────────────────────

def run_adversarial_suite(adversarial_set: list[dict], rails=None,
                           analyzer=None, anonymizer=None) -> list[dict]:
    """Task 10: Chạy 20 adversarial inputs qua full guard stack, so sánh với expected.

    Guard stack order:
        1. pii_scan()         → block nếu has_pii (cho category pii_injection)
        2. check_input_rail() → block nếu jailbreak / off-topic / prompt injection

    Returns:
        list of {
          "id": int, "category": str, "input": str,
          "expected": "blocked"|"allowed",
          "actual":   "blocked"|"allowed",
          "blocked_by": str | None,       # "presidio" | "nemo_input" | None
          "passed": bool,
        }
    """
    # if analyzer is None or anonymizer is None:
    #     analyzer, anonymizer = setup_presidio()
    # if rails is None:
    #     rails = setup_nemo_rails()
    # async def _run_all():
    #     results = []
    #     for item in adversarial_set:
    #         blocked_by = None
    #
    #         # Layer 1: Presidio PII (synchronous, fast)
    #         pii_result = pii_scan(item["input"], analyzer, anonymizer)
    #         if pii_result["has_pii"]:
    #             blocked_by = "presidio"
    #
    #         # Layer 2: NeMo input rail (async — await, không dùng asyncio.run())
    #         if blocked_by is None:
    #             rail_result = await check_input_rail(item["input"], rails)
    #             if not rail_result["allowed"]:
    #                 blocked_by = "nemo_input"
    #
    #         actual = "blocked" if blocked_by else "allowed"
    #         results.append({
    #             "id":         item["id"],
    #             "category":   item["category"],
    #             "input":      item["input"],
    #             "expected":   item["expected"],
    #             "actual":     actual,
    #             "blocked_by": blocked_by,
    #             "passed":     actual == item["expected"],
    #         })
    #     return results
    #
    # results = asyncio.run(_run_all())   # một lần duy nhất — không gọi asyncio.run() trong loop
    # passed = sum(1 for r in results if r["passed"])
    # print(f"Adversarial suite: {passed}/{len(results)} passed")
    # return results
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()
    if rails is None:
        rails = setup_nemo_rails()

    async def run_all():
        rows = []
        for item in adversarial_set:
            pii = pii_scan(item["input"], analyzer, anonymizer)
            blocked_by = "presidio" if pii["has_pii"] else None
            if blocked_by is None:
                rail = await check_input_rail(item["input"], rails)
                if not rail["allowed"]:
                    blocked_by = "nemo_input"
            actual = "blocked" if blocked_by else "allowed"
            rows.append({"id": item["id"], "category": item["category"],
                         "input": item["input"], "expected": item["expected"],
                         "actual": actual, "blocked_by": blocked_by,
                         "passed": actual == item["expected"]})
        return rows

    return asyncio.run(run_all())


# ─── Task 12: P95 Latency Measurement ────────────────────────────────────────

def measure_p95_latency(test_inputs: list[str], n_runs: int = 20,
                         rails=None, analyzer=None, anonymizer=None) -> dict:
    """Task 12: measure INPUT layers sequentially, not end-to-end guard/RAG latency.

    Reuse engines. Inside ONE event loop, execute two real warm-up calls per layer,
    excluded from samples. Then collect exactly n_runs timed samples (cycle clean
    inputs), always measuring BOTH PII and NeMo input even if PII blocks.
    Use perf_counter; keep raw milliseconds. summarize_latency() supplies linear
    percentiles at (n - 1) * q. Submission requires n_runs >= 20.
    Short-circuit request timing, RAG and output timing are outside this scope.
    """
    # from src.experiment_support import summarize_latency
    # if not test_inputs or n_runs < 1:
    #     raise ValueError("Need inputs and n_runs >= 1")
    # if analyzer is None or anonymizer is None:
    #     analyzer, anonymizer = setup_presidio()
    # if rails is None:
    #     rails = setup_nemo_rails()
    # async def _measure():
    #     for i in range(2):
    #         text = test_inputs[i % len(test_inputs)]
    #         pii_scan(text, analyzer, anonymizer)
    #         await check_input_rail(text, rails)
    #     samples = []
    #     for i in range(n_runs):
    #         text = test_inputs[i % len(test_inputs)]
    #         t0 = time.perf_counter()
    #         pii_scan(text, analyzer, anonymizer)
    #         pii_ms = (time.perf_counter() - t0) * 1000
    #         t1 = time.perf_counter()
    #         await check_input_rail(text, rails)
    #         nemo_ms = (time.perf_counter() - t1) * 1000
    #         samples.append({"presidio_ms": pii_ms, "nemo_input_ms": nemo_ms,
    #                         "input_guard_ms": pii_ms + nemo_ms})
    #     return samples
    # return summarize_latency(asyncio.run(_measure()), warmup_runs=2)
    from src.experiment_support import summarize_latency
    if not test_inputs or n_runs < 1:
        raise ValueError("Need inputs and positive n_runs")
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()
    if rails is None:
        rails = setup_nemo_rails()

    async def measure():
        for index in range(2):
            value = test_inputs[index % len(test_inputs)]
            pii_scan(value, analyzer, anonymizer)
            await check_input_rail(value, rails)
        samples = []
        for index in range(n_runs):
            value = test_inputs[index % len(test_inputs)]
            start = time.perf_counter()
            pii_scan(value, analyzer, anonymizer)
            presidio_ms = (time.perf_counter() - start) * 1000
            start = time.perf_counter()
            await check_input_rail(value, rails)
            nemo_ms = (time.perf_counter() - start) * 1000
            samples.append({"presidio_ms": presidio_ms, "nemo_input_ms": nemo_ms,
                            "input_guard_ms": presidio_ms + nemo_ms})
        return samples

    return summarize_latency(asyncio.run(measure()), warmup_runs=2)


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "c", *sys.argv[1:]]))
