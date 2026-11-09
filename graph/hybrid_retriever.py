import json
import time
from typing import Dict, Any, Optional, List

from graph.retrieval_config import LIGHTRAG_ENABLED, NEO4J_DATABASE
from graph.query_understanding import QueryUnderstanding
from graph.retrieval_router import RetrievalRouter
from graph.graph_retriever import Neo4jGraphRetriever
from graph.semantic_retriever import SemanticRetriever
from graph.lightrag_retriever import LightRAGRetriever
from graph.trace import write_trace


# ============================================================
# HYBRID RETRIEVER
# ============================================================

class HybridRetriever:
    """
    Orchestrates:
        1. Query Understanding
        2. Retrieval Routing
        3. Neo4j retrieval (id_lookup, filter_list, filter_count, group_by)
        4. Semantic retrieval (vector search, RRF fusion)
        5. LightRAG retrieval (lazy, optional)
        6. Fallback handling
        7. Tracing

    This module does NOT generate the final answer.
    It collects and structures retrieval evidence.
    """

    def __init__(self):
        print("Initializing Hybrid Retriever...")
        self.query_understanding = QueryUnderstanding()
        self.router = RetrievalRouter()
        self.neo4j = Neo4jGraphRetriever()
        self.semantic_retriever = SemanticRetriever(graph_retriever=self.neo4j)

        # Lazy LightRAG
        self.lightrag = None
        self.lightrag_initialized = False

        print("✓ Hybrid Retriever created")

    # ========================================================
    # INITIALIZE
    # ========================================================

    async def initialize(self):
        print("=" * 60)
        print("INITIALIZING RETRIEVERS")
        print("=" * 60)

        if self.neo4j.test_connection():
            print("✓ Neo4j connection successful")
        else:
            raise RuntimeError("Neo4j connection failed.")

        if LIGHTRAG_ENABLED:
            if self.lightrag is None:
                self.lightrag = LightRAGRetriever()
            await self.lightrag.initialize()
            self.lightrag_initialized = True
            print("✓ LightRAG initialized")
        else:
            print("✓ LightRAG disabled in config (lazy store)")

    # ========================================================
    # NEO4J RETRIEVAL DISPATCH
    # ========================================================

    def retrieve_from_neo4j(
        self,
        query: str,
        understanding: Dict[str, Any],
        plan: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if plan is None:
            plan = self.router.route(understanding).get("plan", {})

        kind = plan.get("kind", "id_lookup")
        target_entity = plan.get("target_entity", "defect")
        if not target_entity or target_entity == "unknown":
            target_entity = "defect"

        entities = understanding.get("entities", {})
        filters = understanding.get("filters", {})
        limit = understanding.get("limit") or 50

        results = []
        not_found_ids = []
        links_missing = False

        # ----------------------------------------------------
        # DISPATCH 1: ID LOOKUP
        # ----------------------------------------------------
        if kind == "id_lookup":
            test_case_ids = entities.get("test_case_ids", [])
            execution_ids = entities.get("execution_ids", [])
            defect_ids = entities.get("defect_ids", [])
            screenshot_ids = entities.get("screenshot_ids", [])

            for tc_id in test_case_ids:
                ctx = self.neo4j.get_testcase_context(tc_id)
                if not ctx or ctx.get("testcase") is None:
                    not_found_ids.append(tc_id)
                    results.append({"type": "testcase_context", "id": tc_id, "data": None})
                else:
                    if not ctx.get("executions") and not ctx.get("defects"):
                        links_missing = True
                    results.append({"type": "testcase_context", "id": tc_id, "data": ctx})

            for ex_id in execution_ids:
                ctx = self.neo4j.get_execution_context(ex_id)
                if not ctx or ctx.get("execution") is None:
                    not_found_ids.append(ex_id)
                    results.append({"type": "execution_context", "id": ex_id, "data": None})
                else:
                    if not ctx.get("defects"):
                        links_missing = True
                    results.append({"type": "execution_context", "id": ex_id, "data": ctx})

            for df_id in defect_ids:
                ctx = self.neo4j.get_full_defect_context(df_id)
                if not ctx or ctx.get("defect") is None:
                    not_found_ids.append(df_id)
                    results.append({"type": "defect_context", "id": df_id, "data": None})
                else:
                    if ctx.get("execution") is None:
                        links_missing = True
                    results.append({"type": "defect_context", "id": df_id, "data": ctx})

            for sc_id in screenshot_ids:
                ctx = self.neo4j.get_screenshot_context(sc_id)
                if not ctx or ctx.get("screenshot") is None:
                    not_found_ids.append(sc_id)
                    results.append({"type": "screenshot_context", "id": sc_id, "data": None})
                else:
                    results.append({"type": "screenshot_context", "id": sc_id, "data": ctx})

            found_count = len([r for r in results if r.get("id") not in not_found_ids])
            return {
                "source": "neo4j",
                "results": results,
                "not_found_ids": not_found_ids,
                "links_missing": links_missing,
                "row_count": found_count,
                "template_name": "id_lookup",
            }

        # ----------------------------------------------------
        # DISPATCH 2: FILTER LIST / FILTER COUNT
        # ----------------------------------------------------
        elif kind in ("filter_list", "filter_count"):
            if target_entity == "test_case":
                filter_res = self.neo4j.testcases_by_filters(filters, limit=limit)
            elif target_entity == "execution":
                filter_res = self.neo4j.executions_by_filters(filters, limit=limit)
            else:
                filter_res = self.neo4j.defects_by_filters(filters, limit=limit)

            sample_rows = [] if kind == "filter_count" else filter_res.get("sample", [])
            return {
                "source": "neo4j",
                "results": sample_rows,
                "filter_results": filter_res,
                "row_count": filter_res.get("total", 0),
                "template_name": filter_res.get("template", kind),
                "not_found_ids": [],
                "links_missing": False,
                "unmapped_filters": filter_res.get("unmapped_filters", []),
            }

        # ----------------------------------------------------
        # DISPATCH 3: GROUP BY / AGGREGATION
        # ----------------------------------------------------
        elif kind == "group_by":
            group_by_field = plan.get("group_by_field") or understanding.get("group_by_field")
            filters = plan.get("filters") or understanding.get("filters", {})
            q_lower = query.lower()

            if target_entity == "test_case" and (group_by_field == "module" or "module" in q_lower):
                agg_res = self.neo4j.count_testcases_by_module()
            elif target_entity == "execution":
                field = group_by_field if group_by_field in Neo4jGraphRetriever.EXEC_AGG_WHITELIST else "status"
                agg_res = self.neo4j.count_executions_by(field)
            else:
                field = (
                    group_by_field
                    if (group_by_field and group_by_field in Neo4jGraphRetriever.DEFECT_AGG_WHITELIST)
                    else "module"
                    if ("module" in q_lower or "modules" in q_lower)
                    else "severity"
                )
                valid_filters = {}
                unmapped_agg = []
                for fk, fv in (filters or {}).items():
                    norm_k = "regression" if (fk in ("type", "defect_type") and str(fv).lower() in ("regression", "yes")) else ("bug_type" if fk in ("type", "defect_type") else fk)
                    if norm_k in Neo4jGraphRetriever.DEFECT_FILTER_FIELD_MAP:
                        valid_filters[fk] = fv
                    else:
                        unmapped_agg.append(fk)

                agg_res = self.neo4j.aggregate_defects(group_by=field, filters=valid_filters, limit=10)
                if unmapped_agg:
                    agg_res["unmapped_filters"] = unmapped_agg

            return {
                "source": "neo4j",
                "results": agg_res.get("rows", []),
                "aggregates": agg_res,
                "row_count": len(agg_res.get("rows", [])),
                "total": agg_res.get("total", 0),
                "template_name": agg_res.get("template", "group_by"),
                "not_found_ids": [],
                "links_missing": False,
                "unmapped_filters": agg_res.get("unmapped_filters", []),
            }

        # ----------------------------------------------------
        # DEFAULT / SEMANTIC
        # ----------------------------------------------------
        return {
            "source": "neo4j",
            "results": [],
            "row_count": 0,
            "template_name": None,
            "not_found_ids": [],
            "links_missing": False,
        }

    # ========================================================
    # LIGHTRAG RETRIEVAL (LAZY)
    # ========================================================

    async def retrieve_from_lightrag(
        self,
        query: str,
    ) -> Dict[str, Any]:
        if not LIGHTRAG_ENABLED:
            return {
                "source": "lightrag",
                "results": "LightRAG is disabled in config",
            }

        if self.lightrag is None:
            self.lightrag = LightRAGRetriever()
            await self.lightrag.initialize()
            self.lightrag_initialized = True
        elif not self.lightrag_initialized:
            await self.lightrag.initialize()
            self.lightrag_initialized = True

        result = await self.lightrag.query(query, mode="hybrid")
        return {
            "source": "lightrag",
            "results": result,
        }

    # ========================================================
    # MAIN RETRIEVAL
    # ========================================================

    async def retrieve(
        self,
        query: str,
    ) -> Dict[str, Any]:
        t0 = time.time()
        errors = []

        print()
        print("=" * 60)
        print("HYBRID RETRIEVAL")
        print("=" * 60)
        print(f"User Query: {query}")

        # ----------------------------------------------------
        # Step 1 — Query Understanding
        # ----------------------------------------------------
        print("\n1. Query Understanding")
        understanding = await self.query_understanding.analyze(query)
        print(f"   Intent: {understanding.get('intent')} | Target: {understanding.get('target_entity')} | Op: {understanding.get('operation')}")
        if understanding.get("filters"):
            print(f"   Filters: {understanding.get('filters')}")
        if understanding.get("unmapped_filters"):
            print(f"   Unmapped Filters: {understanding.get('unmapped_filters')}")

        # ----------------------------------------------------
        # Step 2 — Routing
        # ----------------------------------------------------
        print("\n2. Retrieval Routing")
        route = self.router.route(understanding)
        plan = route.get("plan", {})
        plan_kind = plan.get("kind", "semantic")
        retrievers = route.get("retrievers", [])
        fallback_chain = route.get("fallback_chain", [])
        print(f"   Route: {route.get('route')} | Plan Kind: {plan_kind} | Retrievers: {retrievers}")

        # ----------------------------------------------------
        # Step 3 — Execution
        # ----------------------------------------------------
        neo4j_result = None
        semantic_result = None
        lightrag_result = None
        fallback_used = []
        template_names = []

        # 3A. Neo4j retrieval
        if "neo4j" in retrievers:
            print("\n3A. Neo4j Retrieval")
            try:
                neo4j_result = self.retrieve_from_neo4j(query, understanding, plan)
                tmpl = neo4j_result.get("template_name")
                if tmpl:
                    template_names.append(tmpl)
                print(f"✓ Neo4j result count: {neo4j_result.get('row_count', 0)} (template: {tmpl})")
            except Exception as e:
                errors.append(f"Neo4j retrieval error: {e}")
                print(f"✗ Neo4j error: {e}")

        # 3B. Semantic retrieval
        if "semantic" in retrievers or plan_kind in ("semantic", "semantic_filtered"):
            print("\n3B. Semantic Retrieval")
            try:
                semantic_result = self.semantic_retriever.search(query, understanding=understanding)
                tmpl = semantic_result.get("template")
                if tmpl:
                    template_names.append(tmpl)
                print(f"✓ Semantic hits: {len(semantic_result.get('hits', []))} (backend: {semantic_result.get('backend')})")
            except Exception as e:
                errors.append(f"Semantic retrieval error: {e}")
                print(f"✗ Semantic error: {e}")

        # 3C. LightRAG retrieval
        if "lightrag" in retrievers and LIGHTRAG_ENABLED:
            print("\n3C. LightRAG Retrieval")
            try:
                lightrag_result = await self.retrieve_from_lightrag(query)
                template_names.append("lightrag")
                print("✓ LightRAG retrieval completed")
            except Exception as e:
                errors.append(f"LightRAG error: {e}")
                print(f"✗ LightRAG error: {e}")

        # ----------------------------------------------------
        # Step 4 — Fallback Chain
        # ----------------------------------------------------
        if plan_kind != "id_lookup":
            primary_empty = False
            if plan_kind in ("filter_list", "filter_count", "group_by"):
                primary_empty = (neo4j_result is None or neo4j_result.get("row_count", 0) == 0)
            elif plan_kind == "semantic":
                primary_empty = (semantic_result is None or len(semantic_result.get("hits", [])) == 0)
            elif plan_kind == "semantic_filtered":
                primary_empty = (
                    (neo4j_result is None or neo4j_result.get("row_count", 0) == 0) and
                    (semantic_result is None or len(semantic_result.get("hits", [])) == 0)
                )

            if primary_empty and fallback_chain:
                print(f"\n4. Fallback Triggered (primary empty, chain: {fallback_chain})")
                for fb_kind in fallback_chain:
                    if fb_kind == "semantic" and semantic_result is None:
                        fallback_used.append("semantic")
                        print("   -> Trying fallback: semantic")
                        try:
                            semantic_result = self.semantic_retriever.search(query, understanding=understanding)
                            if semantic_result.get("template"):
                                template_names.append(semantic_result["template"])
                            if semantic_result.get("hits"):
                                print(f"   ✓ Fallback semantic produced {len(semantic_result['hits'])} hits")
                                break
                        except Exception as e:
                            errors.append(f"Fallback semantic error: {e}")
                    elif fb_kind == "lightrag" and LIGHTRAG_ENABLED and lightrag_result is None:
                        fallback_used.append("lightrag")
                        print("   -> Trying fallback: lightrag")
                        try:
                            lightrag_result = await self.retrieve_from_lightrag(query)
                            template_names.append("lightrag")
                            if lightrag_result and lightrag_result.get("results"):
                                break
                        except Exception as e:
                            errors.append(f"Fallback lightrag error: {e}")

        # ----------------------------------------------------
        # Step 5 — Trace and Response Building
        # ----------------------------------------------------
        not_found_ids = []
        if neo4j_result and neo4j_result.get("not_found_ids"):
            not_found_ids = neo4j_result["not_found_ids"]

        row_count = 0
        if neo4j_result:
            row_count += neo4j_result.get("row_count", 0)
        if semantic_result:
            row_count += len(semantic_result.get("hits", []))

        latency_ms = round((time.time() - t0) * 1000, 2)

        if semantic_result and semantic_result.get("backend"):
            backend = semantic_result["backend"]
        elif neo4j_result:
            backend = "neo4j"
        else:
            backend = "unknown"

        tmpl_str = template_names[0] if len(template_names) == 1 else (", ".join(template_names) if template_names else "none")

        trace_record = {
            "question": query,
            "intent": understanding.get("intent", ""),
            "target_entity": plan.get("target_entity", ""),
            "operation": plan.get("operation", ""),
            "filters": understanding.get("filters", {}),
            "unmapped_filters": understanding.get("unmapped_filters", []),
            "route": route.get("route", ""),
            "plan_kind": plan_kind,
            "template_name": tmpl_str,
            "row_count": row_count,
            "not_found_ids": not_found_ids,
            "fallback_used": fallback_used,
            "backend": backend,
            "database": NEO4J_DATABASE,
            "latency_ms": latency_ms,
            "understanding_fallback": understanding.get("understanding_fallback", False),
            "errors": errors,
        }

        write_trace(trace_record)

        return {
            "query": query,
            "query_understanding": understanding,
            "route": route,
            "neo4j": neo4j_result,
            "lightrag": lightrag_result,
            "semantic": semantic_result,
            "trace": trace_record,
        }

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):
        if self.neo4j:
            self.neo4j.close()
        if self.semantic_retriever:
            self.semantic_retriever.close()
        if self.lightrag and hasattr(self.lightrag, "close"):
            self.lightrag.close()
        print("✓ Hybrid Retriever closed")


# ============================================================
# ENTRY POINT / TEST
# ============================================================

async def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 60)
    print("HYBRID RETRIEVER TEST")
    print("=" * 60)

    retriever = HybridRetriever()
    try:
        await retriever.initialize()

        test_questions = [
            "BUG-000176 details",
            "show all Critical defects",
            "defects about login timeouts",
        ]

        for q in test_questions:
            res = await retriever.retrieve(q)
            tr = res.get("trace", {})
            print(f"\nTRACE: {json.dumps(tr, ensure_ascii=False)}")

    finally:
        retriever.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())