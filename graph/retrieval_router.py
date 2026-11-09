import json
import re
from typing import Dict, Any, List
from graph.retrieval_config import LIGHTRAG_ENABLED


# ============================================================
# RETRIEVAL ROUTER
# ============================================================

class RetrievalRouter:

    """
    Deterministic router for the Graph RAG retrieval layer.
    """

    # --------------------------------------------------------
    # MAIN ROUTING METHOD
    # --------------------------------------------------------

    def route(
        self,
        query_understanding: Dict[str, Any]
    ) -> Dict[str, Any]:

        intent = query_understanding.get("intent", "")
        entities = query_understanding.get("entities", {})
        filters = query_understanding.get("filters", {})
        target_entity = query_understanding.get("target_entity")
        operation = query_understanding.get("operation")
        group_by_field = query_understanding.get("group_by_field")

        test_case_ids = entities.get("test_case_ids", [])
        execution_ids = entities.get("execution_ids", [])
        defect_ids = entities.get("defect_ids", [])
        screenshot_ids = entities.get("screenshot_ids", [])

        has_any_id = bool(test_case_ids or execution_ids or defect_ids or screenshot_ids)

        # Default operation if absent
        if not operation:
            if has_any_id:
                operation = "lookup"
            elif filters:
                operation = "list"
            elif intent == "semantic_search":
                operation = "semantic"
            else:
                operation = "semantic"

        # Default target entity if absent
        if not target_entity or target_entity == "unknown":
            if defect_ids:
                target_entity = "defect"
            elif test_case_ids:
                target_entity = "test_case"
            elif execution_ids:
                target_entity = "execution"
            elif screenshot_ids:
                target_entity = "screenshot"
            elif intent == "screenshot_lookup":
                target_entity = "screenshot"
            elif intent in ("testcase_lookup", "testcase_execution_analysis"):
                target_entity = "test_case"
            elif intent in ("execution_lookup", "failure_analysis"):
                target_entity = "execution"
            else:
                target_entity = "defect"

        # ----------------------------------------------------
        # RULE 1
        # Any of defect_ids, test_case_ids, execution_ids, screenshot_ids present
        # ----------------------------------------------------

        if has_any_id:
            retrievers = ["neo4j"]
            if LIGHTRAG_ENABLED and intent in [
                "failure_analysis",
                "testcase_execution_analysis",
                "testcase_analysis",
                "defect_analysis",
            ]:
                retrievers.append("lightrag")

            route_name = "hybrid" if len(retrievers) > 1 else "neo4j"
            reason = "Specific ID requires authoritative structured lookup."
            if len(retrievers) > 1:
                reason = "Specific ID lookup benefits from graph context and semantic evidence."

            return self._build_route(
                route=route_name,
                reason=reason,
                retrievers=retrievers,
                query_type="specific_entity_lookup",
                plan={
                    "kind": "id_lookup",
                    "target_entity": target_entity,
                    "operation": "lookup",
                },
                fallback_chain=[],
            )

        # ----------------------------------------------------
        # RULE 2
        # Operation in {list, count} with validated filter, or group_by
        # ----------------------------------------------------

        fb_chain_structured = ["semantic", "lightrag"]

        low_kw = query_understanding.get("low_level_keywords", [])
        high_kw = query_understanding.get("high_level_keywords", [])
        filter_vals = {str(v).lower() for v in filters.values()}
        ignore_tokens = {
            "show", "list", "filter", "count", "how", "many", "all", "in", "of", "the",
            "defect", "defects", "bug", "bugs", "issue", "issues",
            "testcase", "testcases", "test", "case", "cases",
            "execution", "executions", "result", "results",
            "dev", "qa", "uat", "staging", "prod",
            "critical", "blocker", "major", "minor", "failed", "passed", "skipped", "blocked",
            "module", "environment", "status", "severity", "priority",
        } | filter_vals

        combined_text = " ".join([str(k) for k in low_kw + high_kw]).lower()
        all_tokens = re.findall(r"\b\w+\b", combined_text)
        substantial_free_text = any(
            len(t) > 3 and t not in ignore_tokens
            for t in all_tokens
        )

        if operation in ("list", "count") and filters:
            if substantial_free_text:
                return self._build_route(
                    route="hybrid",
                    reason="Query contains both structured filters and free-text semantic description.",
                    retrievers=["neo4j", "semantic"],
                    query_type="semantic_filtered",
                    plan={
                        "kind": "semantic_filtered",
                        "target_entity": target_entity,
                        "operation": operation,
                    },
                    fallback_chain=fb_chain_structured,
                )

            kind = "filter_count" if operation == "count" else "filter_list"
            return self._build_route(
                route="neo4j",
                reason=f"Structured filters require exact property-based {operation} retrieval.",
                retrievers=["neo4j"],
                query_type=f"structured_{operation}",
                plan={
                    "kind": kind,
                    "target_entity": target_entity,
                    "operation": operation,
                },
                fallback_chain=fb_chain_structured,
            )

        if operation == "group_by" or group_by_field:
            return self._build_route(
                route="neo4j",
                reason="Aggregation query requires exact property grouping.",
                retrievers=["neo4j"],
                query_type="group_by",
                plan={
                    "kind": "group_by",
                    "target_entity": target_entity,
                    "operation": "group_by",
                    "group_by_field": group_by_field,
                    "filters": filters,
                },
                fallback_chain=fb_chain_structured,
            )

        # ----------------------------------------------------
        # RULE 3
        # Operation semantic or semantic/exploratory intents
        # ----------------------------------------------------

        fb_chain_semantic = ["lightrag"]

        if intent == "screenshot_lookup":
            return self._build_route(
                route="semantic",
                reason="Screenshot exploratory query without ID routed to semantic search.",
                retrievers=["semantic"],
                query_type="semantic_search",
                plan={
                    "kind": "semantic",
                    "target_entity": "screenshot",
                    "operation": "semantic",
                },
                fallback_chain=fb_chain_semantic,
            )

        sem_retrievers = ["semantic"]
        if LIGHTRAG_ENABLED and intent == "general_test_analysis":
            sem_retrievers.append("lightrag")

        if operation == "semantic" or intent in [
            "semantic_search",
            "failure_analysis",
            "defect_analysis",
            "general_test_analysis",
        ]:
            route_name = "hybrid" if len(sem_retrievers) > 1 else "semantic"
            return self._build_route(
                route=route_name,
                reason="Semantic or exploratory query is best suited to vector retrieval.",
                retrievers=sem_retrievers,
                query_type="semantic_search",
                plan={
                    "kind": "semantic",
                    "target_entity": target_entity,
                    "operation": "semantic",
                },
                fallback_chain=fb_chain_semantic,
            )

        # ----------------------------------------------------
        # RULE 4
        # Default
        # ----------------------------------------------------

        return self._build_route(
            route="semantic",
            reason="No strong structured signal was detected; use semantic retrieval.",
            retrievers=["semantic"],
            query_type="default_semantic_search",
            plan={
                "kind": "semantic",
                "target_entity": target_entity,
                "operation": "semantic",
            },
            fallback_chain=fb_chain_semantic,
        )

    # --------------------------------------------------------
    # ROUTE RESULT BUILDER
    # --------------------------------------------------------

    def _build_route(
        self,
        route: str,
        reason: str,
        retrievers: list,
        query_type: str,
        plan: Dict[str, Any],
        fallback_chain: List[str],
    ) -> Dict[str, Any]:

        return {
            "route": route,
            "retrievers": retrievers,
            "query_type": query_type,
            "reason": reason,
            "plan": plan,
            "fallback_chain": fallback_chain,
        }


# ============================================================
# TEST
# ============================================================

def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 60)
    print("RETRIEVAL ROUTER TEST")
    print("=" * 60)

    router = RetrievalRouter()

    test_cases = [
        # 1. ID lookup
        {
            "intent": "defect_lookup",
            "target_entity": "defect",
            "operation": "lookup",
            "entities": {"defect_ids": ["BUG-000176"], "test_case_ids": [], "execution_ids": [], "screenshot_ids": []},
            "filters": {},
            "low_level_keywords": ["BUG-000176"],
            "high_level_keywords": ["defect details"],
        },
        # 2. Screenshot ID
        {
            "intent": "screenshot_lookup",
            "target_entity": "screenshot",
            "operation": "lookup",
            "entities": {"defect_ids": [], "test_case_ids": [], "execution_ids": [], "screenshot_ids": ["SCR-ocr_batch_001-0000"]},
            "filters": {},
            "low_level_keywords": ["SCR-ocr_batch_001-0000"],
            "high_level_keywords": ["screenshot details"],
        },
        # 3. Filter list
        {
            "intent": "defect_lookup",
            "target_entity": "defect",
            "operation": "list",
            "entities": {"defect_ids": [], "test_case_ids": [], "execution_ids": [], "screenshot_ids": []},
            "filters": {"severity": "Critical"},
            "low_level_keywords": ["Critical"],
            "high_level_keywords": ["critical defects"],
        },
        # 4. Filter count
        {
            "intent": "failure_analysis",
            "target_entity": "execution",
            "operation": "count",
            "entities": {"defect_ids": [], "test_case_ids": [], "execution_ids": [], "screenshot_ids": []},
            "filters": {"status": "Failed", "environment": "UAT"},
            "low_level_keywords": ["Failed", "UAT"],
            "high_level_keywords": ["failed executions in UAT"],
        },
        # 5. Group by
        {
            "intent": "defect_analysis",
            "target_entity": "defect",
            "operation": "group_by",
            "group_by_field": "severity",
            "entities": {"defect_ids": [], "test_case_ids": [], "execution_ids": [], "screenshot_ids": []},
            "filters": {},
            "low_level_keywords": ["severity"],
            "high_level_keywords": ["defects grouped by severity"],
        },
        # 6. Semantic
        {
            "intent": "semantic_search",
            "target_entity": "defect",
            "operation": "semantic",
            "entities": {"defect_ids": [], "test_case_ids": [], "execution_ids": [], "screenshot_ids": []},
            "filters": {},
            "low_level_keywords": ["login", "timeout"],
            "high_level_keywords": ["defects about login timeouts"],
        },
        # 7. Malformed ID
        {
            "intent": "defect_lookup",
            "target_entity": "defect",
            "operation": "lookup",
            "entities": {"defect_ids": ["BUG-00000099"], "test_case_ids": [], "execution_ids": [], "screenshot_ids": []},
            "filters": {},
            "low_level_keywords": ["BUG-00000099"],
            "high_level_keywords": ["malformed ID check"],
        },
    ]

    for index, query_result in enumerate(test_cases, start=1):
        print(f"\nTEST CASE {index}")
        result = router.route(query_result)
        print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    print("✓ RETRIEVAL ROUTER TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()