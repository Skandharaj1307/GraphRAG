"""
===============================================================================
GraphRAG Evaluation Framework CLI & Pipeline Instrumentation
===============================================================================
"""

import sys
import os
import json
import time
import re
import hashlib
import argparse
import asyncio
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from tqdm import tqdm

from graph.query_understanding import QueryUnderstanding
from graph.retrieval_router import RetrievalRouter
from graph.hybrid_retriever import HybridRetriever
from graph.context_assembler import ContextAssembler
from graph.context_to_llm import ContextToLLMFormatter
from graph.final_llm import FinalLLM

from graph.evaluation.config import (
    DEFAULT_TESTSET_PATH,
    DEFAULT_RUNS_DIR,
    INTENT_ALIASES,
    SCORED_FIELDS_PER_TYPE,
    TEXT_RECALL_THRESHOLD,
    RETRIEVAL_MIN_FIELD_RECALL,
    MIN_REQUEST_INTERVAL,
    UNANSWERABLE_REGEXES,
    REFUSAL_REGEXES,
    OPENROUTER_API_KEY,
)
from graph.evaluation.scorers import (
    score_extraction,
    score_intent,
    score_routing,
    score_retrieval,
    score_final_answer,
    detect_reasoning_leak,
)
from graph.evaluation.judge import LLMJudge, export_judge_inputs, import_judge_outputs
from graph.evaluation.report import generate_reports


class DailyQuotaExhausted(Exception):
    """Raised immediately when OpenRouter daily free-model quota is exhausted."""
    pass


def is_daily_quota_error(err_str: str) -> bool:
    """Detect if error message indicates daily quota exhaustion."""
    msg = str(err_str).lower()
    keywords = [
        "daily", "per-day", "per day", "quota", "free-models",
        "day limit", "daily limit", "quota_exceeded", "free_tier",
        "rate limit exceeded for daily", "free model rate limit",
        "user_daily_limit", "daily_quota", "usage_daily"
    ]
    return any(kw in msg for kw in keywords)


class RateLimiter:
    """Enforces minimum spacing between actual LLM API requests."""

    def __init__(self, interval: float = MIN_REQUEST_INTERVAL):
        self.interval = interval
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def wait(self):
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                await asyncio.sleep(sleep_time)
            self.last_request_time = time.time()


def openrouter_preflight_check(api_key: str) -> Dict[str, Any]:
    """Inspect OpenRouter key status and daily quota information without printing key."""
    from graph.llm_client import is_openrouter, LLM_BASE_URL
    if not is_openrouter(LLM_BASE_URL):
        print(f"[PREFLIGHT INFO] Custom/Local endpoint detected ({LLM_BASE_URL}). Skipping OpenRouter preflight check.")
        return {"usable": True, "reason": "Non-OpenRouter endpoint"}

    if not api_key:
        print("[PREFLIGHT WARNING] No OpenRouter API key provided.")
        return {"usable": False, "reason": "No API key"}

    print("\n" + "=" * 50)
    print("OPENROUTER PREFLIGHT CHECK")
    print("=" * 50)

    try:
        resp = requests.get(
            "https://openrouter.ai/api/v1/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            label = data.get("label", "N/A")
            usage = data.get("usage", 0.0)
            limit = data.get("limit", None)
            is_free_tier = data.get("is_free_tier", False)
            rate_limit_info = data.get("rate_limit", {})

            print(f"  - Key Label/ID: {label}")
            print(f"  - Usage (USD): {usage}")
            print(f"  - Limit (USD): {limit if limit is not None else 'No limit'}")
            print(f"  - Is Free Tier: {is_free_tier}")
            if rate_limit_info:
                print(f"  - Rate Limit Info: {rate_limit_info}")

            if is_free_tier and limit is not None and usage >= limit:
                print("\n[PREFLIGHT ERROR] OpenRouter daily quota is EXHAUSTED!")
                return {"usable": False, "reason": "Daily quota exhausted", "data": data}

            print("  - Preflight Status: USABLE\n")
            return {"usable": True, "data": data}

        else:
            print(f"  - Key endpoint returned HTTP {resp.status_code}: {resp.text}")
            if resp.status_code == 429:
                return {"usable": False, "reason": "429 Rate limited during preflight", "text": resp.text}
            return {"usable": True, "text": resp.text}

    except Exception as e:
        print(f"[PREFLIGHT WARNING] Could not connect to OpenRouter key endpoint: {e}")
        return {"usable": True, "error": str(e)}


def estimate_api_budget(num_cases: int, preflight_data: Dict[str, Any]):
    """Estimate number of OpenRouter LLM inference calls required."""
    calls_per_case = 2  # Stage 1: Query Understanding + Stage 4: Final LLM Answer
    total_calls = num_cases * calls_per_case

    print("=" * 50)
    print("API CALL BUDGET ESTIMATE")
    print("=" * 50)
    print(f"  - Cases requested: {num_cases}")
    print(f"  - Estimated LLM calls/case: {calls_per_case} (1 Query Understanding + 1 Final Answer)")
    print(f"  - Estimated total LLM calls: {total_calls}")
    print(f"  - Request Spacing Interval: {MIN_REQUEST_INTERVAL}s between inference calls")
    print(f"  - Minimum estimated runtime: ~{total_calls * MIN_REQUEST_INTERVAL:.1f}s")
    print("=" * 50 + "\n")


def round_robin_order(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Order test cases round-robin by question type to maximize diversity across partial runs."""
    by_type = {}
    for c in cases:
        t = c.get("type", "unknown")
        by_type.setdefault(t, []).append(c)

    ordered = []
    max_len = max((len(v) for v in by_type.values()), default=0)
    types = list(by_type.keys())

    for i in range(max_len):
        for t in types:
            if i < len(by_type[t]):
                ordered.append(by_type[t][i])
    return ordered


def compute_file_hash(filepath: Path) -> str:
    """Compute MD5 hash of testset file for meta tracking."""
    if not filepath.exists():
        return ""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


class PipelineRunner:
    """Orchestrates individual pipeline stage calls with rate limiting and quota detection."""

    def __init__(self, rate_limiter: RateLimiter):
        self.query_understanding = QueryUnderstanding()
        self.router = RetrievalRouter()
        self.hybrid_retriever = HybridRetriever()
        self.context_assembler = ContextAssembler()
        self.context_formatter = ContextToLLMFormatter()
        self.llm = FinalLLM()
        self.rate_limiter = rate_limiter
        self.initialized = False

    async def initialize(self):
        if not self.initialized:
            await self.hybrid_retriever.initialize()
            self.initialized = True

    async def run_stage_by_stage(self, query: str) -> Dict[str, Any]:
        """Execute pipeline stage by stage with rate limiting and 429 quota handling."""
        await self.initialize()

        # --- Stage 1: Query Understanding ---
        t0 = time.time()
        understanding = None
        backoffs = [10, 20, 30]

        for attempt in range(4):
            await self.rate_limiter.wait()
            try:
                understanding = await self.query_understanding.analyze(query)
                if understanding and isinstance(understanding, dict):
                    break
            except Exception as e:
                err_str = str(e)
                if is_daily_quota_error(err_str):
                    raise DailyQuotaExhausted(f"Daily quota exhausted in Query Understanding: {err_str}")
                if "429" in err_str or "rate limit" in err_str.lower() or "50" in err_str:
                    if attempt < 3:
                        wait_sec = backoffs[attempt]
                        print(f"\n[STAGE 1 429/TRANSIENT] Retry {attempt + 1}/3 in {wait_sec}s...")
                        await asyncio.sleep(wait_sec)
                        continue
                if attempt == 3:
                    raise RuntimeError(f"Query Understanding failed after retries: {e}")

        if not understanding:
            raise RuntimeError("Query Understanding returned empty response.")
        if understanding.get("status") == "infra_error":
            raise RuntimeError(f"Query Understanding returned infra_error: {understanding.get('error')}")

        t1 = time.time()
        stage1_lat = t1 - t0

        # --- Stage 2: Routing (Reuses Stage 1 output without duplicate LLM call) ---
        route_info = self.router.route(understanding)
        t2 = time.time()
        stage2_lat = t2 - t1

        # --- Stage 3: Retrieval ---
        chosen_route = route_info.get("route", "neo4j")
        if chosen_route == "neo4j":
            raw_retrieval = self.hybrid_retriever.retrieve_from_neo4j(query, understanding)
        elif chosen_route == "lightrag":
            raw_retrieval = await self.hybrid_retriever.retrieve_from_lightrag(query)
        else:
            raw_retrieval = await self.hybrid_retriever.retrieve(query)

        # Context assembly
        assembled_context = self.context_assembler.assemble(
            {"query": query, "route": route_info, "neo4j": raw_retrieval if chosen_route == "neo4j" else None, "lightrag": raw_retrieval if chosen_route == "lightrag" else None}
            if chosen_route != "hybrid" else raw_retrieval
        )
        t3 = time.time()
        stage3_lat = t3 - t2

        # --- Stage 4: Answer Generation ---
        import tempfile
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tf:
                json.dump(assembled_context, tf, indent=2, ensure_ascii=False)
                temp_path = tf.name
            messages = self.context_formatter.process(temp_path)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

        answer_text = None
        for attempt in range(4):
            await self.rate_limiter.wait()
            try:
                answer_text = await self.llm.generate_text(messages=messages, max_tokens=1000)
                if answer_text and answer_text.strip():
                    break
            except Exception as e:
                err_str = str(e)
                if is_daily_quota_error(err_str):
                    raise DailyQuotaExhausted(f"Daily quota exhausted in Final LLM: {err_str}")
                if "429" in err_str or "rate limit" in err_str.lower() or "50" in err_str:
                    if attempt < 3:
                        wait_sec = backoffs[attempt]
                        print(f"\n[STAGE 4 429/TRANSIENT] Retry {attempt + 1}/3 in {wait_sec}s...")
                        await asyncio.sleep(wait_sec)
                        continue
                if attempt == 3:
                    raise RuntimeError(f"Final LLM generation failed after retries: {e}")

        if not answer_text or not answer_text.strip():
            raise RuntimeError("Final LLM returned empty response.")

        t4 = time.time()
        stage4_lat = t4 - t3

        return {
            "understanding": understanding,
            "route_info": route_info,
            "assembled_context": assembled_context,
            "answer_text": answer_text,
            "latencies": {
                "stage1_sec": round(stage1_lat, 4),
                "stage2_sec": round(stage2_lat, 4),
                "stage3_sec": round(stage3_lat, 4),
                "stage4_sec": round(stage4_lat, 4),
                "total_sec": round(t4 - t0, 4)
            }
        }


async def evaluate_single_case(
    case: Dict[str, Any],
    pipeline: PipelineRunner,
    judge: LLMJudge,
    semaphore: Optional[asyncio.Semaphore] = None
) -> Dict[str, Any]:
    """Run evaluation for a single test case with complete diagnostic schema."""
    async def _run():
        cid = case["id"]
        qtype = case.get("type", "unknown")
        hops = case.get("hops", 0)
        question = case["question"]
        expected_entities = case.get("expected_entities", {})
        expected_intent = case.get("expected_intent", "")
        expected_route = case.get("expected_route", "neo4j")
        gold_answer = case.get("gold_answer")

        is_infra_error = False
        error_text = ""

        try:
            pipe_res = await pipeline.run_stage_by_stage(question)

            extracted_entities = pipe_res["understanding"].get("entities", {})
            extracted_intent = pipe_res["understanding"].get("intent", "")
            router_route = pipe_res["route_info"].get("route", "")
            retrieved_context = pipe_res["assembled_context"]

            # Determine retriever_route from context
            retriever_route = router_route
            if isinstance(retrieved_context, dict):
                retriever_route = retrieved_context.get("route_used", router_route)

            chosen_route = router_route
            answer = pipe_res["answer_text"]
            latencies = pipe_res["latencies"]

        except DailyQuotaExhausted:
            # Re-raise daily quota error so main loop catches it and saves checkpoint
            raise

        except Exception as e:
            is_infra_error = True
            error_text = f"INFRASTRUCTURE ERROR: {str(e)}"
            extracted_entities = {}
            extracted_intent = ""
            router_route = "infra_error"
            retriever_route = "infra_error"
            chosen_route = "infra_error"
            retrieved_context = None
            answer = ""
            latencies = {"stage1_sec": 0, "stage2_sec": 0, "stage3_sec": 0, "stage4_sec": 0, "total_sec": 0}

        route_consistent = (router_route == retriever_route)
        answer_reasoning_leak = detect_reasoning_leak(answer) if answer else False

        # If infrastructure error occurred, return infra_error record
        if is_infra_error:
            return {
                "id": cid,
                "type": qtype,
                "hops": hops,
                "question": question,
                "expected_entities": expected_entities,
                "extracted_entities": extracted_entities,
                "expected_intent": expected_intent,
                "extracted_intent": extracted_intent,
                "predicted_intent": extracted_intent,
                "expected_route": expected_route,
                "chosen_route": chosen_route,
                "router_route": router_route,
                "retriever_route": retriever_route,
                "route_consistent": False,
                "retrieved_context": None,
                "generated_answer": "",
                "answer": "",
                "gold_answer": gold_answer,
                "scores": {
                    "extraction": {"overall_exact_match": False},
                    "intent": {"intent_acc_raw": False, "intent_acc_aliased": False},
                    "routing": {"route_exact_match": False},
                    "retrieval": {"empty_retrieval": True, "field_recall": 0.0, "pass_retrieval": False},
                    "final_answer": {"answer_correctness": 0.0, "pass_answer": False},
                    "judge": {"skipped": True},
                },
                "retrieval_metrics": {"field_recall": 0.0},
                "field_recall": 0.0,
                "answer_metrics": {"answer_correctness": 0.0},
                "answer_reasoning_leak": False,
                "stage_pass": {
                    "stage1": False,
                    "stage2": False,
                    "stage3": False,
                    "stage4": False,
                },
                "first_failing_stage": "infra_error",
                "failed_fields": [f"infra_error: {error_text}"],
                "status": "infra_error",
                "latency": 0.0,
                "total_latency_sec": 0.0,
                "stage_latencies_sec": latencies,
                "error": error_text,
                "error_text": error_text,
            }

        # --- Score Stage 1: Extraction & Intent ---
        ext_scores = score_extraction(extracted_entities, expected_entities)
        intent_scores = score_intent(extracted_intent, expected_intent, aliases=INTENT_ALIASES)
        stage1_pass = ext_scores["overall_exact_match"] and intent_scores["intent_exact_match"]

        # --- Score Stage 2: Routing ---
        route_scores = score_routing(chosen_route, expected_route)
        stage2_pass = route_scores["route_exact_match"]

        # --- Score Stage 3: Retrieval ---
        ret_scores = score_retrieval(retrieved_context, gold_answer, chosen_route, min_field_recall=RETRIEVAL_MIN_FIELD_RECALL)
        stage3_pass = ret_scores["pass_retrieval"]

        # --- Score Stage 4: Answer Generation ---
        ans_scores = score_final_answer(
            answer,
            gold_answer,
            qtype=qtype,
            scored_fields_map=SCORED_FIELDS_PER_TYPE,
            unanswerable_regexes=UNANSWERABLE_REGEXES,
            refusal_regexes=REFUSAL_REGEXES
        )
        stage4_pass = ans_scores["pass_answer"]

        # Optional Judge scoring
        judge_scores = {"skipped": True}
        if judge.mode == "endpoint" and not error_text:
            judge_scores = await judge.evaluate_item(question, retrieved_context, answer)

        # Build detailed failed_fields explanation
        failed_fields = []
        if not stage1_pass:
            if not intent_scores["intent_exact_match"]:
                failed_fields.append(f"extraction: intent got {extracted_intent}, expected {expected_intent}")
            for entity_key in ["test_case_ids", "execution_ids", "defect_ids"]:
                es = ext_scores.get(entity_key, {})
                if not es.get("exact_match", True):
                    prec = es.get("precision", 0.0)
                    rec = es.get("recall", 0.0)
                    failed_fields.append(f"extraction: {entity_key} precision {prec:.2f}, recall {rec:.2f}")

        if not stage2_pass:
            failed_fields.append(f"routing: got {chosen_route}, expected {expected_route}")

        if not route_consistent:
            failed_fields.append(f"route mismatch: router = {router_route}, retriever = {retriever_route}")

        if not stage3_pass:
            f_rec = ret_scores.get("field_recall", 0.0)
            failed_fields.append(f"retrieval: field_recall {f_rec:.2f} < required {RETRIEVAL_MIN_FIELD_RECALL:.2f}")
            missing_f = ret_scores.get("missing_fields", [])
            if missing_f:
                failed_fields.append(f"retrieval: missing fields [{', '.join(missing_f)}]")

        if not stage4_pass:
            ans_ff = ans_scores.get("failed_fields", [])
            for aff in ans_ff:
                failed_fields.append(f"answer: {aff}")

        # Determine First Failing Stage
        if not stage1_pass:
            first_failing = "extraction"
        elif not stage2_pass:
            first_failing = "routing"
        elif not stage3_pass:
            first_failing = "retrieval"
        elif not stage4_pass:
            first_failing = "generation"
        else:
            first_failing = "none"

        # Determine Status: stage_mismatch_only vs completed
        if (not stage1_pass or not stage2_pass) and stage3_pass and stage4_pass:
            status = "stage_mismatch_only"
        else:
            status = "completed"

        context_dump = json.dumps(retrieved_context, ensure_ascii=False) if isinstance(retrieved_context, (dict, list)) else str(retrieved_context or "")
        truncated_context = context_dump[:4000]

        return {
            "id": cid,
            "type": qtype,
            "hops": hops,
            "question": question,
            "expected_entities": expected_entities,
            "extracted_entities": extracted_entities,
            "expected_intent": expected_intent,
            "extracted_intent": extracted_intent,
            "predicted_intent": extracted_intent,
            "expected_route": expected_route,
            "chosen_route": chosen_route,
            "router_route": router_route,
            "retriever_route": retriever_route,
            "route_consistent": route_consistent,
            "retrieved_context": truncated_context,
            "generated_answer": answer,
            "answer": answer,
            "gold_answer": gold_answer,
            "scores": {
                "extraction": ext_scores,
                "intent": intent_scores,
                "routing": route_scores,
                "retrieval": ret_scores,
                "final_answer": ans_scores,
                "judge": judge_scores,
            },
            "retrieval_metrics": ret_scores,
            "field_recall": ret_scores.get("field_recall", 0.0),
            "answer_metrics": ans_scores,
            "answer_reasoning_leak": answer_reasoning_leak,
            "stage_pass": {
                "stage1": stage1_pass,
                "stage2": stage2_pass,
                "stage3": stage3_pass,
                "stage4": stage4_pass,
            },
            "first_failing_stage": first_failing,
            "failed_fields": failed_fields if failed_fields else ["N/A"],
            "status": status,
            "latency": latencies["total_sec"],
            "total_latency_sec": latencies["total_sec"],
            "stage_latencies_sec": latencies,
            "error": error_text,
            "error_text": error_text,
        }

    if semaphore:
        async with semaphore:
            return await _run()
    else:
        return await _run()


async def main_async(args):
    """Main CLI execution loop."""
    print("=" * 70)
    print("GRAPHRAG EVALUATION FRAMEWORK RUNNER")
    print("=" * 70)

    testset_path = Path(args.testset)
    if not testset_path.exists():
        raise FileNotFoundError(f"Testset file not found at: {testset_path}")

    # Output directory setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) if args.out else DEFAULT_RUNS_DIR / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    results_jsonl = out_dir / "results.jsonl"

    print(f"Testset: {testset_path}")
    print(f"Output Directory: {out_dir}")
    print(f"Judge Mode: {args.judge}")

    # Preflight Check
    preflight = openrouter_preflight_check(OPENROUTER_API_KEY)
    if not preflight.get("usable", True):
        print("[ABORTING RUN] OpenRouter preflight check failed. Daily quota is exhausted.")
        sys.exit(1)

    # Load testset items
    with open(testset_path, "r", encoding="utf-8") as f:
        all_cases = json.load(f)

    # Filter types if specified
    if args.types:
        selected_types = [t.strip() for t in args.types.split(",") if t.strip()]
        all_cases = [c for c in all_cases if c.get("type") in selected_types]
        print(f"Filtered by types ({selected_types}): {len(all_cases)} cases remaining")

    # Apply --per-type N filtering
    if args.per_type and args.per_type > 0:
        per_type_cases = []
        by_type = {}
        for c in all_cases:
            t = c.get("type", "unknown")
            by_type.setdefault(t, []).append(c)
        for t, cases in by_type.items():
            per_type_cases.extend(cases[:args.per_type])
        all_cases = per_type_cases
        print(f"Applied --per-type ({args.per_type}): {len(all_cases)} total cases across {len(by_type)} question types")

    # Apply global limit
    if args.limit and args.limit > 0:
        all_cases = all_cases[:args.limit]
        print(f"Applied limit ({args.limit}): {len(all_cases)} cases to evaluate")

    # Handle --resume logic cleanly
    completed_ids = set()
    existing_records = []

    if args.resume and results_jsonl.exists():
        with open(results_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line.strip())
                    rec_status = rec.get("status", "")
                    rec_id = rec.get("id")

                    # Skip ONLY completed and stage_mismatch_only cases
                    if rec_status in ["completed", "stage_mismatch_only"]:
                        completed_ids.add(rec_id)
                        existing_records.append(rec)
                    else:
                        print(f"  - Re-queuing unfinished/infra_error case: {rec_id} (status: {rec_status})")

        print(f"Resuming run: skipped {len(completed_ids)} completed cases. Re-running infra_error & pending cases.")

    # Filter cases to run
    cases_to_run = [c for c in all_cases if c["id"] not in completed_ids]

    # Order pending cases round-robin by question type
    cases_to_run = round_robin_order(cases_to_run)
    print(f"Pending cases to run ({len(cases_to_run)}) ordered round-robin by question type.")

    # Estimate API budget
    estimate_api_budget(len(cases_to_run), preflight.get("data", {}))

    # Initialize Rate Limiter & Pipeline
    rate_limiter = RateLimiter(interval=MIN_REQUEST_INTERVAL)
    judge = LLMJudge(mode=args.judge)
    pipeline = PipelineRunner(rate_limiter=rate_limiter)

    if cases_to_run:
        await pipeline.initialize()

    # Save meta information
    run_meta = {
        "timestamp": timestamp,
        "testset_path": str(testset_path),
        "testset_hash": compute_file_hash(testset_path),
        "judge_mode": args.judge,
        "total_cases_evaluated": len(all_cases),
        "cases_executed": len(cases_to_run),
        "limit": args.limit,
        "per_type": args.per_type,
        "concurrency": args.concurrency,
        "types_filter": args.types,
        "min_request_interval_sec": MIN_REQUEST_INTERVAL,
        "retrieval_min_field_recall": RETRIEVAL_MIN_FIELD_RECALL,
    }
    with open(out_dir / "run_meta.json", "w", encoding="utf-8") as f:
        json.dump(run_meta, f, indent=2)

    # Concurrency limit semaphore
    concurrency_limit = args.concurrency if args.concurrency and args.concurrency > 1 else 1
    semaphore = asyncio.Semaphore(concurrency_limit) if concurrency_limit > 1 else None

    # Execute evaluation loop with progress bar and DailyQuotaExhausted catch
    new_results = []
    quota_exhausted_triggered = False

    with open(results_jsonl, "a" if args.resume else "w", encoding="utf-8") as jsonl_f:
        pbar = tqdm(total=len(cases_to_run), desc="Evaluating GraphRAG Pipeline")

        try:
            if concurrency_limit > 1:
                async def worker(c):
                    res = await evaluate_single_case(c, pipeline, judge, semaphore)
                    jsonl_f.write(json.dumps(res, ensure_ascii=False) + "\n")
                    jsonl_f.flush()
                    pbar.update(1)
                    return res

                tasks = [worker(c) for c in cases_to_run]
                new_results = await asyncio.gather(*tasks)
            else:
                for case in cases_to_run:
                    res = await evaluate_single_case(case, pipeline, judge)
                    new_results.append(res)
                    jsonl_f.write(json.dumps(res, ensure_ascii=False) + "\n")
                    jsonl_f.flush()
                    pbar.update(1)

        except DailyQuotaExhausted as e:
            quota_exhausted_triggered = True
            print(f"\n\n[DAILY QUOTA EXHAUSTED]: {e}")
            print(f"Checkpoint saved cleanly to: {results_jsonl}")
            print(f"Resume command when ready:\n  python -m graph.evaluation.run_eval --out {out_dir} --resume --judge {args.judge}")

        finally:
            pbar.close()

    all_results = existing_records + new_results

    if quota_exhausted_triggered:
        # Generate interim reports on whatever completed so far
        if all_results:
            generate_reports(all_results, run_meta, str(out_dir))
        sys.exit(0)

    # Handle --judge export or import modes
    if args.judge == "export":
        jsonl_path, notebook_path = export_judge_inputs(all_results, str(out_dir))
        print(f"\n[EXPORT COMPLETED]")
        print(f"  - Judge Inputs JSONL: {jsonl_path}")
        print(f"  - Kaggle Notebook Script: {notebook_path}")

    elif args.judge == "import":
        try:
            judge_outputs = import_judge_outputs(str(out_dir))
            for r in all_results:
                if r["id"] in judge_outputs:
                    r["scores"]["judge"] = judge_outputs[r["id"]]
            print(f"\n[IMPORT COMPLETED] Merged {len(judge_outputs)} judge scores.")
        except Exception as e:
            print(f"\n[IMPORT ERROR]: {e}")

    # Generate final reports (summary.md, summary.csv, failures.csv, etc.)
    generate_reports(all_results, run_meta, str(out_dir))


def main():
    parser = argparse.ArgumentParser(description="GraphRAG Evaluation Framework CLI")
    parser.add_argument("--testset", type=str, default=str(DEFAULT_TESTSET_PATH), help="Path to testset JSON")
    parser.add_argument("--out", type=str, default="", help="Output directory for run results")
    parser.add_argument("--judge", type=str, choices=["none", "endpoint", "export", "import"], default="none", help="Judge backend mode")
    parser.add_argument("--limit", type=int, default=None, help="Limit total number of test cases to run")
    parser.add_argument("--per-type", type=int, default=None, help="Select N test cases per question type for balanced coverage")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of concurrent test cases to evaluate in parallel")
    parser.add_argument("--types", type=str, default=None, help="Comma-separated list of question types to evaluate")
    parser.add_argument("--resume", action="store_true", help="Resume previous run from results.jsonl")

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
