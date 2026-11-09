"""
GraphRAG-1 Evaluation Runner V2
Supports modes:
  --mode retrieval_only: No LLM calls. Feeds retriever with gold intents/ids/filters.
  --mode full: End-to-end pipeline (Router -> Retrieval -> Final LLM).
  --mode router_only: Evaluates query understanding and routing accuracy.

Outputs per run:
  graph/evaluation_v2/runs/<timestamp>/
    - results.jsonl
    - summary.json
    - summary.md
    - config.json
"""

import sys
import os
import re
import json
import time
import math
import argparse
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GOLD_SET_PATH = BASE_DIR / "graph" / "evaluation_v2" / "gold" / "gold_set.jsonl"
RUNS_DIR = BASE_DIR / "graph" / "evaluation_v2" / "runs"

from graph.hybrid_retriever import HybridRetriever
from graph.context_assembler import ContextAssembler
from graph.retrieval_router import RetrievalRouter
from graph.query_understanding import QueryUnderstanding
from graph.final_prompt import GroundedPromptBuilder
from graph.final_llm import FinalLLM, sanitize_llm_output
from graph.evaluation.config import INTENT_ALIASES, REFUSAL_REGEXES, UNANSWERABLE_REGEXES
from graph.llm_client import (
    LLM_BASE_URL,
    get_base_url_host,
    get_model_for_role,
    ROUTER_MODEL,
    ANSWER_MODEL,
    JUDGE_MODEL,
    LLMInfraError,
    is_transient_error,
)


def get_git_commit() -> str:
    try:
        res = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return res.decode().strip()
    except Exception:
        return "unknown"


def extract_entity_ids(text: str) -> Set[str]:
    """Extract standard entity IDs from text using regex."""
    if not text:
        return set()
    pattern = r"\b(BUG-\d+|TC-\d+|EXEC-\d+|SCR-[a-zA-Z0-9_\-]+|REQ-\d+|LOG-EXEC-\d+)\b"
    return set(re.findall(pattern, text, re.IGNORECASE))


# ============================================================
# METRICS COMPUTATION
# ============================================================

def compute_retrieval_metrics(gold: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    metrics = {}
    query_type = gold.get("query_type")
    gold_nodes = set(gold.get("gold_nodes", []))
    gold_facts = gold.get("gold_facts", [])

    # 1. Collect all retrieved nodes
    retrieved_nodes = set()
    for ent in context.get("entities", []):
        if ent.get("id"):
            retrieved_nodes.add(str(ent["id"]).upper())
    for item in context.get("structured_evidence", []):
        for k in ["id", "defect_id", "execution_id", "test_case_id", "screenshot_id", "log_id"]:
            if item.get(k):
                retrieved_nodes.add(str(item[k]).upper())
    filter_res = context.get("filter_results") or {}
    for sid in filter_res.get("sample", []):
        retrieved_nodes.add(str(sid).upper())
    for hit in context.get("ranked_hits", []):
        for k in ["defect_id", "test_case_id", "execution_id", "screenshot_id", "id"]:
            if hit.get(k):
                retrieved_nodes.add(str(hit[k]).upper())

    # Node Recall & Precision
    norm_gold_nodes = {str(n).upper() for n in gold_nodes}
    if not norm_gold_nodes:
        metrics["node_recall"] = 1.0
        metrics["node_precision"] = 1.0
    else:
        matched = norm_gold_nodes.intersection(retrieved_nodes)
        metrics["node_recall"] = round(len(matched) / len(norm_gold_nodes), 4)
        metrics["node_precision"] = round(len(matched) / len(retrieved_nodes), 4) if retrieved_nodes else 0.0

    # 2. Field Recall (Gold facts verified in context)
    if not gold_facts:
        metrics["field_recall"] = 1.0
    else:
        matched_facts = 0
        ctx_str = json.dumps(context).lower()
        for fact in gold_facts:
            f_val = fact.get("value")
            if f_val is None:
                matched_facts += 1
                continue
            if isinstance(f_val, list):
                # check if at least one or subset present
                found = any(str(v).lower() in ctx_str for v in f_val)
                if found:
                    matched_facts += 1
            else:
                str_val = str(f_val).lower()
                if str_val in ctx_str:
                    matched_facts += 1
        metrics["field_recall"] = round(matched_facts / len(gold_facts), 4)

    # 3. Aggregation Exactness
    if query_type == "aggregation" or gold.get("expected_group_by"):
        agg_pairs_match = 0.0
        agg_order_match = 0.0
        agg_filters_match = 0.0

        expected_filters = gold.get("expected_filters") or gold.get("group_filters") or {}
        q_text = gold.get("question", "").lower()
        is_ordered = any(kw in q_text for kw in ["top", "highest", "most", "rank", "descending", "order"])

        def norm_val(v):
            if isinstance(v, str):
                return v.strip().lower()
            if isinstance(v, list):
                return sorted([norm_val(x) for x in v])
            return v

        norm_exp_filters = {str(k).strip().lower(): norm_val(v) for k, v in expected_filters.items()}

        aggregates = context.get("aggregates") or {}
        rows = aggregates.get("rows", [])
        retrieved_filters = aggregates.get("filters_applied") or {}

        if rows:
            # Group-by aggregation
            gold_pairs = [
                (str(f.get("entity", "")).strip().lower(), int(f.get("value", 0)))
                for f in gold_facts if f.get("field") in ("defect_count", "critical_blocker_count")
            ]
            retrieved_pairs = [
                (str(r.get("key", "")).strip().lower(), int(r.get("count", 0)))
                for r in rows
            ]
            slice_len = len(gold_pairs)
            ret_slice = retrieved_pairs[:slice_len]
            tie_keys = [str(k).strip().lower() for k in gold.get("tie_at_cutoff", [])]

            # (a) Set of (key, count) pairs match
            if gold_pairs and set(gold_pairs) == set(ret_slice):
                agg_pairs_match = 1.0
            elif gold_pairs and tie_keys and slice_len > 0:
                cutoff_cnt = gold_pairs[-1][1]
                gold_untied = [(k, c) for k, c in gold_pairs if c != cutoff_cnt]
                ret_untied = [(k, c) for k, c in ret_slice if c != cutoff_cnt]
                gold_tied_in_slice = [(k, c) for k, c in gold_pairs if c == cutoff_cnt]
                ret_tied_in_slice = [(k, c) for k, c in ret_slice if c == cutoff_cnt]

                if (
                    set(gold_untied) == set(ret_untied)
                    and len(gold_tied_in_slice) == len(ret_tied_in_slice)
                    and all(k in tie_keys and c == cutoff_cnt for k, c in ret_tied_in_slice)
                ):
                    agg_pairs_match = 1.0

            # (b) Order match when top-N or ordered
            if is_ordered:
                if ret_slice == gold_pairs:
                    agg_order_match = 1.0
                else:
                    # accommodate ties with equal count
                    ret_counts = [cnt for _, cnt in ret_slice]
                    gold_counts = [cnt for _, cnt in gold_pairs]
                    if ret_counts == gold_counts:
                        if set(gold_pairs) == set(ret_slice):
                            agg_order_match = 1.0
                        elif tie_keys and agg_pairs_match == 1.0:
                            gold_untied_keys = [k for k, c in gold_pairs if c != gold_pairs[-1][1]]
                            ret_untied_keys = [k for k, c in ret_slice if c != gold_pairs[-1][1]]
                            if gold_untied_keys == ret_untied_keys:
                                agg_order_match = 1.0
            else:
                agg_order_match = agg_pairs_match

            # (c) filters_applied in retrieved equals gold expected_filters
            norm_ret_filters = {str(k).strip().lower(): norm_val(v) for k, v in retrieved_filters.items()}
            if norm_ret_filters == norm_exp_filters:
                agg_filters_match = 1.0

        else:
            # Count query (e.g. filter_results)
            exp_count = None
            for f in gold_facts:
                if f.get("field") == "total_count":
                    exp_count = f.get("value")
                    break

            ret_count = filter_res.get("total")
            if exp_count is not None and ret_count == exp_count:
                agg_pairs_match = 1.0
            agg_order_match = 1.0  # order trivial for scalar count

            ret_f = filter_res.get("filters_applied") or filter_res.get("filters") or {}
            norm_ret_f = {str(k).strip().lower(): norm_val(v) for k, v in ret_f.items()}
            if norm_ret_f == norm_exp_filters:
                agg_filters_match = 1.0

        aggregation_exact = 1.0 if (agg_pairs_match == 1.0 and agg_order_match == 1.0 and agg_filters_match == 1.0) else 0.0

        metrics["agg_pairs_match"] = agg_pairs_match
        metrics["agg_order_match"] = agg_order_match
        metrics["agg_filters_match"] = agg_filters_match
        metrics["aggregation_exact"] = aggregation_exact
    else:
        metrics["agg_pairs_match"] = None
        metrics["agg_order_match"] = None
        metrics["agg_filters_match"] = None
        metrics["aggregation_exact"] = None

    # 4. Semantic Ranking Metrics (Recall@5, Recall@10, MRR, nDCG)
    if query_type == "semantic" and gold.get("gold_nodes"):
        target_node = str(gold["gold_nodes"][0]).upper()
        ranked_hits = []
        for h in context.get("ranked_hits", []):
            hid = h.get("defect_id") or h.get("id") or h.get("test_case_id")
            if hid:
                ranked_hits.append(str(hid).upper())

        metrics["recall_at_5"] = 1.0 if target_node in ranked_hits[:5] else 0.0
        metrics["recall_at_10"] = 1.0 if target_node in ranked_hits[:10] else 0.0
        
        mrr = 0.0
        ndcg = 0.0
        if target_node in ranked_hits:
            rank_idx = ranked_hits.index(target_node) # 0-indexed
            mrr = 1.0 / (rank_idx + 1)
            ndcg = 1.0 / math.log2(rank_idx + 2)
        metrics["mrr"] = round(mrr, 4)
        metrics["ndcg"] = round(ndcg, 4)
    else:
        metrics["recall_at_5"] = None
        metrics["recall_at_10"] = None
        metrics["mrr"] = None
        metrics["ndcg"] = None

    # 5. Context Size
    ctx_serialized = json.dumps(context)
    metrics["context_chars"] = len(ctx_serialized)
    metrics["context_tokens_est"] = len(ctx_serialized) // 4

    return metrics


def compute_routing_metrics(gold: Dict[str, Any], router_output: Dict[str, Any]) -> Dict[str, Any]:
    metrics = {}
    expected_intent = gold.get("expected_intent")
    actual_intent = router_output.get("intent")

    # Intent accuracy
    valid_intents = INTENT_ALIASES.get(expected_intent, [expected_intent])
    metrics["intent_accuracy"] = 1.0 if (actual_intent in valid_intents or actual_intent == expected_intent) else 0.0

    # ID precision & recall
    gold_ids = set()
    for id_list in gold.get("expected_ids", {}).values():
        gold_ids.update([str(i).upper() for i in id_list])

    extracted_ids = set()
    ent_dict = router_output.get("entities", {})
    if isinstance(ent_dict, dict):
        for id_list in ent_dict.values():
            if isinstance(id_list, list):
                extracted_ids.update([str(i).upper() for i in id_list])

    if not gold_ids:
        metrics["id_precision"] = 1.0 if not extracted_ids else 0.0
        metrics["id_recall"] = 1.0
    else:
        matched = gold_ids.intersection(extracted_ids)
        metrics["id_precision"] = round(len(matched) / len(extracted_ids), 4) if extracted_ids else 0.0
        metrics["id_recall"] = round(len(matched) / len(gold_ids), 4)

    # Filter accuracy
    expected_filters = gold.get("expected_filters", {})
    actual_filters = router_output.get("filters", {})
    if not expected_filters:
        metrics["filter_accuracy"] = 1.0 if not actual_filters else 0.8
    else:
        match_f = sum(1 for k, v in expected_filters.items() if actual_filters.get(k) == v)
        metrics["filter_accuracy"] = round(match_f / len(expected_filters), 4)

    # Group By accuracy
    expected_gb = gold.get("expected_group_by")
    actual_gb = router_output.get("group_by_field")
    metrics["group_by_accuracy"] = 1.0 if (expected_gb == actual_gb) else 0.0

    return metrics


def compute_generation_metrics(gold: Dict[str, Any], answer: str, context: Dict[str, Any]) -> Dict[str, Any]:
    metrics = {}
    gold_facts = gold.get("gold_facts", [])
    answerable = gold.get("answerable", True)
    ans_clean = (answer or "").lower()

    # 1. Answer exact (presence of gold facts values)
    if not gold_facts:
        metrics["answer_exact"] = 1.0 if not answerable else 0.0
    else:
        matched = 0
        for f in gold_facts:
            val = f.get("value")
            if val is None:
                matched += 1
                continue
            if isinstance(val, list):
                if any(str(v).lower() in ans_clean for v in val):
                    matched += 1
            else:
                if str(val).lower() in ans_clean:
                    matched += 1
        metrics["answer_exact"] = round(matched / len(gold_facts), 4)

    # 2. Abstention Accuracy
    refusal_keywords = [
        "not found", "does not exist", "unavailable", "insufficient",
        "cannot be determined", "no information", "not in the database",
        "no matching", "not in the evidence", "no record"
    ]
    refused = any(kw in ans_clean for kw in refusal_keywords)
    if not answerable:
        # Should refuse
        metrics["abstention_accuracy"] = 1.0 if refused else 0.0
    else:
        # Should NOT refuse
        metrics["abstention_accuracy"] = 0.0 if (refused and len(gold_facts) > 0) else 1.0

    # 3. Hallucinated IDs (IDs in answer not present in retrieved context)
    retrieved_nodes = set()
    for ent in context.get("entities", []):
        if ent.get("id"):
            retrieved_nodes.add(str(ent["id"]).upper())
    for item in context.get("structured_evidence", []):
        for k in ["id", "defect_id", "execution_id", "test_case_id", "screenshot_id"]:
            if item.get(k):
                retrieved_nodes.add(str(item[k]).upper())
    for hit in context.get("ranked_hits", []):
        for k in ["defect_id", "test_case_id", "execution_id", "screenshot_id", "id"]:
            if hit.get(k):
                retrieved_nodes.add(str(hit[k]).upper())

    answer_ids = {i.upper() for i in extract_entity_ids(answer)}
    hallucinated = list(answer_ids - retrieved_nodes)
    metrics["hallucinated_ids"] = hallucinated
    metrics["hallucination_free"] = 1.0 if len(hallucinated) == 0 else 0.0

    return metrics


# ============================================================
# EVALUATION RUNNER
# ============================================================

class EvaluatorV2:
    def __init__(self, args):
        self.args = args
        self.retriever = HybridRetriever()
        self.assembler = ContextAssembler()
        self.router = RetrievalRouter()
        self.query_understanding = QueryUnderstanding() if args.mode in ("full", "router_only") else None
        self.prompt_builder = GroundedPromptBuilder() if args.mode == "full" else None
        self.final_llm = FinalLLM() if args.mode == "full" else None

    async def initialize(self):
        await self.retriever.initialize()

    def close(self):
        self.retriever.close()

    async def evaluate_single(self, gold_item: Dict[str, Any]) -> Dict[str, Any]:
        t0 = time.time()
        qid = gold_item["id"]
        q = gold_item["question"]
        mode = self.args.mode
        status = "ok"
        error_detail = None

        router_out = {}
        context = {}
        answer = ""
        metrics = {}

        try:
            # ----------------------------------------------------
            # 1. ROUTING STEP
            # ----------------------------------------------------
            if mode in ("full", "router_only"):
                try:
                    router_out = await self.query_understanding.analyze(q)
                    if isinstance(router_out, dict) and router_out.get("status") == "infra_error":
                        return {
                            "id": qid, "split": gold_item.get("split"), "query_type": gold_item.get("query_type"),
                            "question": q, "router_output": router_out, "retrieved_context": None, "answer": None,
                            "gold_answer": gold_item.get("gold_answer"), "gold_facts": gold_item.get("gold_facts"),
                            "metrics": {}, "latency_s": round(time.time() - t0, 3), "status": "infra_error",
                            "error_detail": router_out.get("error", "Router infrastructure error")
                        }
                except Exception as e:
                    if isinstance(e, LLMInfraError) or is_transient_error(e):
                        return {
                            "id": qid, "split": gold_item.get("split"), "query_type": gold_item.get("query_type"),
                            "question": q, "router_output": None, "retrieved_context": None, "answer": None,
                            "gold_answer": gold_item.get("gold_answer"), "gold_facts": gold_item.get("gold_facts"),
                            "metrics": {}, "latency_s": round(time.time() - t0, 3), "status": "infra_error",
                            "error_detail": str(e)
                        }
                    else:
                        raise e
            else:
                # In retrieval_only: construct understanding directly from gold
                gold_ids = gold_item.get("expected_ids", {})
                entities = {
                    "defect_ids": list(gold_ids.get("defect", [])),
                    "test_case_ids": list(gold_ids.get("testcase", [])),
                    "execution_ids": list(gold_ids.get("execution", [])),
                    "screenshot_ids": list(gold_ids.get("screenshot", []))
                }
                target_entity = "defect"
                if gold_ids.get("execution"):
                    target_entity = "execution"
                elif gold_ids.get("testcase"):
                    target_entity = "test_case"
                elif gold_ids.get("screenshot"):
                    target_entity = "screenshot"
                elif gold_item.get("expected_intent") in ("testcase_lookup", "testcase_to_defects", "requirements"):
                    target_entity = "test_case"
                elif gold_item.get("expected_intent") in ("execution_context", "execution_lookup"):
                    target_entity = "execution"

                operation = "lookup"
                if gold_item.get("expected_group_by"):
                    operation = "group_by"
                elif gold_item.get("expected_filters"):
                    operation = "list"
                elif gold_item.get("expected_intent") == "semantic_search":
                    operation = "semantic"

                router_out = {
                    "intent": gold_item.get("expected_intent"),
                    "entities": entities,
                    "filters": gold_item.get("expected_filters", {}),
                    "group_by_field": gold_item.get("expected_group_by"),
                    "target_entity": target_entity,
                    "operation": operation,
                    "limit": 50
                }

            if mode in ("full", "router_only"):
                r_metrics = compute_routing_metrics(gold_item, router_out)
                metrics.update(r_metrics)

            if mode == "router_only":
                return {
                    "id": qid, "split": gold_item.get("split"), "query_type": gold_item.get("query_type"),
                    "question": q, "router_output": router_out, "retrieved_context": None, "answer": None,
                    "gold_answer": gold_item.get("gold_answer"), "gold_facts": gold_item.get("gold_facts"),
                    "metrics": metrics, "latency_s": round(time.time() - t0, 3), "status": "ok"
                }

            # ----------------------------------------------------
            # 2. RETRIEVAL STEP
            # ----------------------------------------------------
            route = self.router.route(router_out)
            plan = route.get("plan", {})
            retrievers = route.get("retrievers", [])
            qtype = gold_item.get("query_type")

            neo4j_res = None
            semantic_res = None

            if "neo4j" in retrievers:
                neo4j_res = self.retriever.retrieve_from_neo4j(q, router_out, plan)

            if "semantic" in retrievers or plan.get("kind") in ("semantic", "semantic_filtered") or qtype == "semantic":
                semantic_res = self.retriever.semantic_retriever.search(q, understanding=router_out)

            context = self.assembler.assemble({
                "query": q,
                "route": route,
                "neo4j": neo4j_res,
                "semantic": semantic_res,
                "lightrag": None,
                "query_understanding": router_out,
                "trace": {}
            })

            ret_metrics = compute_retrieval_metrics(gold_item, context)
            metrics.update(ret_metrics)

            if mode == "retrieval_only":
                return {
                    "id": qid, "split": gold_item.get("split"), "query_type": gold_item.get("query_type"),
                    "question": q, "router_output": router_out, "retrieved_context": context, "answer": None,
                    "gold_answer": gold_item.get("gold_answer"), "gold_facts": gold_item.get("gold_facts"),
                    "metrics": metrics, "latency_s": round(time.time() - t0, 3), "status": "ok"
                }

            # ----------------------------------------------------
            # 3. GENERATION STEP (FULL MODE)
            # ----------------------------------------------------
            messages = self.prompt_builder.build_messages(query=q, context=context)
            try:
                raw_answer = await self.final_llm.generate(messages)
                if hasattr(raw_answer, "choices"):
                    answer = sanitize_llm_output(raw_answer.choices[0].message.content)
                else:
                    answer = sanitize_llm_output(str(raw_answer))
            except Exception as e:
                err_str = str(e)
                if isinstance(e, LLMInfraError) or is_transient_error(e) or "429" in err_str or "rate limit" in err_str.lower() or "5" in err_str[:3]:
                    status = "infra_error"
                    return {
                        "id": qid, "split": gold_item.get("split"), "query_type": gold_item.get("query_type"),
                        "question": q, "router_output": router_out, "retrieved_context": context, "answer": None,
                        "gold_answer": gold_item.get("gold_answer"), "gold_facts": gold_item.get("gold_facts"),
                        "metrics": metrics, "latency_s": round(time.time() - t0, 3), "status": "infra_error",
                        "error_detail": err_str
                    }
                else:
                    raise e

            gen_metrics = compute_generation_metrics(gold_item, answer, context)
            metrics.update(gen_metrics)

        except Exception as e:
            if isinstance(e, LLMInfraError) or is_transient_error(e):
                status = "infra_error"
            else:
                status = "pipeline_error"
            error_detail = str(e)
            print(f"Error processing {qid} ({status}): {e}")

        return {
            "id": qid,
            "split": gold_item.get("split"),
            "query_type": gold_item.get("query_type"),
            "question": q,
            "router_output": router_out,
            "retrieved_context": context,
            "answer": answer,
            "gold_answer": gold_item.get("gold_answer"),
            "gold_facts": gold_item.get("gold_facts"),
            "metrics": metrics,
            "latency_s": round(time.time() - t0, 3),
            "status": status,
            "error_detail": error_detail
        }


# ============================================================
# REPORT GENERATION
# ============================================================

def generate_summary(results: List[Dict[str, Any]], run_dir: Path, flags: Dict[str, Any]):
    valid_results = [r for r in results if r["status"] == "ok"]
    infra_errors = [r for r in results if r["status"] == "infra_error"]
    pipeline_errors = [r for r in results if r["status"] == "pipeline_error"]

    latencies = [r["latency_s"] for r in valid_results]
    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    # Aggregate metric names
    all_keys = set()
    for r in valid_results:
        all_keys.update(r.get("metrics", {}).keys())

    # Overall metrics
    overall_metrics = {}
    for k in sorted(all_keys):
        vals = [float(r["metrics"][k]) for r in valid_results if isinstance(r.get("metrics", {}).get(k), (int, float))]
        if vals:
            overall_metrics[k] = round(sum(vals) / len(vals), 4)

    # By Query Type
    by_type = defaultdict(list)
    for r in valid_results:
        by_type[r["query_type"]].append(r)

    type_metrics = {}
    for qt, q_results in by_type.items():
        type_metrics[qt] = {"count": len(q_results)}
        for k in sorted(all_keys):
            vals = [float(r["metrics"][k]) for r in q_results if isinstance(r.get("metrics", {}).get(k), (int, float))]
            if vals:
                type_metrics[qt][k] = round(sum(vals) / len(vals), 4)

    # By Split
    by_split = defaultdict(list)
    for r in valid_results:
        by_split[r["split"]].append(r)

    split_metrics = {}
    for sp, sp_results in by_split.items():
        split_metrics[sp] = {"count": len(sp_results)}
        for k in sorted(all_keys):
            vals = [float(r["metrics"][k]) for r in sp_results if isinstance(r.get("metrics", {}).get(k), (int, float))]
            if vals:
                split_metrics[sp][k] = round(sum(vals) / len(vals), 4)

    summary_data = {
        "run_timestamp": run_dir.name,
        "mode": flags.get("mode"),
        "total_cases": len(results),
        "valid_cases": len(valid_results),
        "infra_errors": len(infra_errors),
        "pipeline_errors": len(pipeline_errors),
        "latency_p50": round(p50, 3),
        "latency_p95": round(p95, 3),
        "overall_metrics": overall_metrics,
        "by_type": type_metrics,
        "by_split": split_metrics
    }

    # Write summary.json
    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Write summary.md
    md_lines = []
    md_lines.append(f"# GraphRAG Evaluation Benchmark Report (V2)")
    md_lines.append(f"**Run Timestamp**: `{run_dir.name}` | **Mode**: `{flags.get('mode')}`\n")
    md_lines.append("## 1. Overall System Performance")
    md_lines.append("| Metric | Value |")
    md_lines.append("| :--- | :---: |")
    md_lines.append(f"| **Total Cases** | {len(results)} |")
    md_lines.append(f"| **Valid Cases Evaluated** | {len(valid_results)} |")
    md_lines.append(f"| **Infrastructure Errors (429/5xx)** | {len(infra_errors)} |")
    md_lines.append(f"| **Pipeline Errors** | {len(pipeline_errors)} |")
    md_lines.append(f"| **Latency p50** | {round(p50, 3)}s |")
    md_lines.append(f"| **Latency p95** | {round(p95, 3)}s |")
    for k, v in overall_metrics.items():
        display_val = f"{v * 100:.1f}%" if ("recall" in k or "precision" in k or "exact" in k or "accuracy" in k) else str(v)
        md_lines.append(f"| **{k}** | {display_val} |")

    md_lines.append("\n## 2. Performance by Query Type")
    table_cols = ["query_type", "count", "node_recall", "node_precision", "field_recall", "aggregation_exact", "agg_pairs_match", "agg_order_match", "agg_filters_match"]
    if flags.get("mode") in ("full", "router_only"):
        table_cols.extend(["intent_accuracy", "id_recall"])
    if flags.get("mode") == "full":
        table_cols.extend(["answer_exact", "abstention_accuracy", "hallucination_free"])

    header = " | ".join([c.replace("_", " ").title() for c in table_cols])
    sep = " | ".join([":---" if i == 0 else ":---:" for i in range(len(table_cols))])
    md_lines.append(f"| {header} |")
    md_lines.append(f"| {sep} |")

    for qt in sorted(type_metrics.keys()):
        row = [f"`{qt}`", str(type_metrics[qt]["count"])]
        for col in table_cols[2:]:
            val = type_metrics[qt].get(col)
            if val is None:
                row.append("—")
            elif "recall" in col or "precision" in col or "exact" in col or "accuracy" in col or "free" in col:
                row.append(f"{val * 100:.1f}%")
            else:
                row.append(str(val))
        md_lines.append(f"| {' | '.join(row)} |")

    with open(run_dir / "summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")


# ============================================================
# MAIN CLI
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="GraphRAG Evaluation Runner V2")
    parser.add_argument("--mode", choices=["retrieval_only", "full", "router_only"], default="retrieval_only")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="all")
    parser.add_argument("--smoke", action="store_true", help="Run only smoke test cases")
    parser.add_argument("--types", type=str, default=None, help="Comma-separated query types")
    parser.add_argument("--limit", type=int, default=None, help="Max test cases to run")
    parser.add_argument("--resume", type=str, default=None, help="Resume from an existing run folder")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat count")
    parser.add_argument("--workers", type=int, default=1, help="Worker count (default: 1 sequential)")
    args = parser.parse_args()

    # Create run folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / timestamp if not args.resume else Path(args.resume)
    run_dir.mkdir(parents=True, exist_ok=True)

    endpoint_host = get_base_url_host(LLM_BASE_URL)
    router_model = get_model_for_role("router")
    answer_model = get_model_for_role("answer")
    judge_model = get_model_for_role("judge")

    print("\n" + "=" * 60)
    print("GRAPH RAG EVALUATION RUNNER V2")
    print(f"  Effective Base URL Host: {endpoint_host}")
    print(f"  Router Model:            {router_model}")
    print(f"  Answer Model:            {answer_model}")
    print(f"  Judge Model:             {judge_model}")
    print("=" * 60 + "\n")

    # Save config.json (host only, no keys)
    config_data = {
        "git_commit": get_git_commit(),
        "mode": args.mode,
        "base_url_host": endpoint_host,
        "models": {
            "router": router_model,
            "answer": answer_model,
            "judge": judge_model,
        },
        "flags": vars(args),
        "seed": 2026
    }
    with open(run_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    # Load gold dataset
    print(f"Loading gold dataset from {GOLD_SET_PATH}...")
    gold_records = []
    with open(GOLD_SET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                gold_records.append(json.loads(line))

    # Apply filters
    filtered = gold_records
    if args.split != "all":
        filtered = [r for r in filtered if r.get("split") == args.split]
    if args.smoke:
        filtered = [r for r in filtered if r.get("smoke") is True]
    if args.types:
        req_types = [t.strip() for t in args.types.split(",")]
        filtered = [r for r in filtered if r.get("query_type") in req_types]
    if args.limit:
        filtered = filtered[:args.limit]

    print(f"Total test cases selected: {len(filtered)} (mode: {args.mode}, split: {args.split}, smoke: {args.smoke})")

    # Handle resume
    completed_ids = set()
    results = []
    results_file = run_dir / "results.jsonl"
    if args.resume and results_file.exists():
        with open(results_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    completed_ids.add(item["id"])
                    results.append(item)
        filtered = [r for r in filtered if r["id"] not in completed_ids]
        print(f"Resuming: {len(completed_ids)} already completed, {len(filtered)} remaining.")

    evaluator = EvaluatorV2(args)
    await evaluator.initialize()

    # Execute run
    print("\nRunning evaluation cases...")
    for idx, item in enumerate(filtered, 1):
        print(f"[{idx}/{len(filtered)}] {item['id']} ({item['query_type']}): {item['question'][:65]}...")
        res = await evaluator.evaluate_single(item)
        results.append(res)
        with open(results_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")

    evaluator.close()

    # Generate summary
    generate_summary(results, run_dir, vars(args))
    print(f"\nEvaluation completed! Results and summary saved to: {run_dir}")

    # Print summary to console
    with open(run_dir / "summary.md", "r", encoding="utf-8") as f:
        print("\n" + f.read())


if __name__ == "__main__":
    asyncio.run(main())

