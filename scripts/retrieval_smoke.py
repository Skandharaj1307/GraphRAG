import os
import sys
import json
import asyncio
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from graph.retrieval_config import NEO4J_DATABASE, TRACE_FILE
from graph.graph_retriever import Neo4jGraphRetriever
from graph.semantic_retriever import SemanticRetriever
from graph.hybrid_retriever import HybridRetriever
from graph.context_assembler import ContextAssembler


async def run_smoke():
    print("=" * 80)
    print(f"GRAPHRAG RETRIEVAL SMOKE TEST (DB: {NEO4J_DATABASE})")
    print("=" * 80)

    results = []

    def record(phase: str, test_name: str, passed: bool, detail: str = ""):
        results.append({
            "phase": phase,
            "test": test_name,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        })

    # ========================================================
    # PHASE 2: GRAPH RETRIEVER CHECKS
    # ========================================================
    gr = Neo4jGraphRetriever()
    try:
        # Check 1: Connection
        conn_ok = gr.test_connection()
        record("Phase 2", "Neo4j Connection", conn_ok, f"database={NEO4J_DATABASE}")

        # Check 2: Filter query
        crit_res = gr.defects_by_filters({"severity": "Critical"})
        crit_total = crit_res.get("total", 0)
        record("Phase 2", "Defects by Filter (Critical)", crit_total == 2533 or crit_total > 0, f"total={crit_total}")

        # Check 3: Aggregation sum
        sev_agg = gr.count_defects_by("severity")
        agg_total = sev_agg.get("total", 0)
        record("Phase 2", "Severity Aggregation (10k sum)", agg_total == 10000, f"sum={agg_total}, rows={len(sev_agg.get('rows', []))}")

        # Check 4: Full defect context
        df_ctx = gr.get_full_defect_context("BUG-000176")
        has_df = df_ctx and df_ctx.get("defect") is not None
        record("Phase 2", "Full Defect Context (BUG-000176)", bool(has_df), f"has_execution={bool(df_ctx.get('execution')) if df_ctx else False}")

        # Check 5: Vocabulary
        vocab = gr.get_vocabulary()
        vocab_ok = bool(vocab.get("modules") and vocab.get("severity") and vocab.get("environments"))
        record("Phase 2", "Cached Vocabulary", vocab_ok, f"modules={len(vocab.get('modules', []))}, envs={len(vocab.get('environments', []))}")

    except Exception as e:
        record("Phase 2", "GraphRetriever Exception", False, str(e))
    finally:
        gr.close()

    # ========================================================
    # PHASE 4: SEMANTIC RETRIEVER CHECKS
    # ========================================================
    sr = SemanticRetriever()
    try:
        # Check 6: Semantic hybrid search
        sem_res = sr.search("defects about login timeouts", limit=10)
        hits = sem_res.get("hits", [])
        backend = sem_res.get("backend", "unknown")
        record("Phase 4", "Defect Semantic Search (RRF)", len(hits) == 10, f"hits={len(hits)}, backend={backend}")

        # Check 7: Screenshot semantic search
        scr_res = sr.search("checkout button failure", understanding={"target_entity": "screenshot"}, limit=5)
        scr_hits = scr_res.get("hits", [])
        record("Phase 4", "Screenshot Semantic Search", len(scr_hits) > 0, f"hits={len(scr_hits)}, backend={scr_res.get('backend')}")

    except Exception as e:
        record("Phase 4", "SemanticRetriever Exception", False, str(e))
    finally:
        sr.close()

    # ========================================================
    # PHASE 6: HYBRID RETRIEVER & TRACE CHECKS
    # ========================================================
    hr = HybridRetriever()
    ca = ContextAssembler()
    try:
        await hr.initialize()

        # Check 8: End-to-end ID Lookup
        id_res = await hr.retrieve("BUG-000176 details")
        id_tr = id_res.get("trace", {})
        id_ok = id_tr.get("plan_kind") == "id_lookup" and id_tr.get("row_count") == 1
        record("Phase 6", "Hybrid ID Lookup (BUG-000176)", id_ok, f"kind={id_tr.get('plan_kind')}, rows={id_tr.get('row_count')}")

        # Check 9: Malformed ID not-found tracking
        mal_res = await hr.retrieve("Check malformed ID BUG-00000099")
        mal_tr = mal_res.get("trace", {})
        mal_ok = "BUG-00000099" in mal_tr.get("not_found_ids", []) and mal_tr.get("row_count") == 0
        record("Phase 6", "Malformed ID Handled (BUG-00000099)", mal_ok, f"not_found={mal_tr.get('not_found_ids')}")

        # Check 10: Filter Count
        cnt_res = await hr.retrieve("how many Failed executions in UAT")
        cnt_tr = cnt_res.get("trace", {})
        cnt_ok = cnt_tr.get("plan_kind") == "filter_count" and cnt_tr.get("row_count") > 0
        record("Phase 6", "Hybrid Filter Count", cnt_ok, f"count={cnt_tr.get('row_count')}, fb={cnt_tr.get('fallback_used')}")

        # Check 11: Semantic Query End-to-End
        sq_res = await hr.retrieve("payment failure after checkout")
        sq_tr = sq_res.get("trace", {})
        sq_ok = sq_tr.get("plan_kind") == "semantic" and sq_tr.get("row_count") == 10
        record("Phase 6", "Hybrid Semantic Search", sq_ok, f"rows={sq_tr.get('row_count')}, backend={sq_tr.get('backend')}")

        # Check 12: Context Assembler Notes
        ctx = ca.assemble(id_res)
        notes_ok = "not_found_ids" in ctx.get("notes", {}) and "links_missing" in ctx.get("notes", {})
        record("Phase 7", "Context Assembler & Notes", notes_ok, f"entities={len(ctx.get('entities', []))}")

        # Check 13: Trace file written
        trace_path = Path(TRACE_FILE)
        trace_ok = trace_path.exists() and trace_path.stat().st_size > 0
        record("Phase 1", "Trace File Logging", trace_ok, f"file={TRACE_FILE}")

    except Exception as e:
        record("Phase 6", "HybridRetriever Exception", False, str(e))
    finally:
        hr.close()

    # ========================================================
    # PRINT PASS/FAIL SUMMARY TABLE
    # ========================================================
    print("\n" + "=" * 80)
    print(f"{'PHASE':<10} | {'TEST NAME':<35} | {'STATUS':<8} | {'DETAIL'}")
    print("=" * 80)
    all_passed = True
    for r in results:
        status_marker = "PASS" if r["status"] == "PASS" else "FAIL"
        if r["status"] != "PASS":
            all_passed = False
        print(f"{r['phase']:<10} | {r['test']:<35} | {status_marker:<8} | {r['detail']}")
    print("=" * 80)

    if all_passed:
        print("ALL RETRIEVAL SMOKE CHECKS PASSED.")
    else:
        print("SOME SMOKE CHECKS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_smoke())
