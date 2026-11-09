import json
from typing import Dict, Any, List, Optional

from graph.hybrid_retriever import HybridRetriever


# ============================================================
# CONTEXT ASSEMBLER
# ============================================================

class ContextAssembler:
    """
    Combines Neo4j, Semantic, and LightRAG retrieval results into
    one structured evidence package.

    This class does NOT generate an answer.
    It prepares grounded evidence for the final LLM.
    """

    # ========================================================
    # MAIN ASSEMBLY METHOD
    # ========================================================

    def assemble(
        self,
        retrieval_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        query = retrieval_result.get("query", "")
        route = retrieval_result.get("route", {})
        neo4j_data = retrieval_result.get("neo4j")
        lightrag_data = retrieval_result.get("lightrag")
        semantic_data = retrieval_result.get("semantic")
        understanding = retrieval_result.get("query_understanding", {})
        trace = retrieval_result.get("trace", {})

        # ----------------------------------------------------
        # 1. Structured evidence from Neo4j
        # ----------------------------------------------------
        structured_evidence = self._extract_neo4j_evidence(neo4j_data)

        # ----------------------------------------------------
        # 2. Semantic / LightRAG evidence
        # ----------------------------------------------------
        semantic_evidence = self._extract_lightrag_evidence(lightrag_data)

        # ----------------------------------------------------
        # 3. Deduplicate entities & relationships
        # ----------------------------------------------------
        entities = self._merge_entities(
            structured_evidence["entities"],
            semantic_evidence["entities"],
        )

        relationships = self._merge_relationships(
            structured_evidence["relationships"],
            semantic_evidence["relationships"],
        )

        # ----------------------------------------------------
        # 4. Screenshot normalization
        # ----------------------------------------------------
        screenshots = self._normalize_screenshots(
            structured_evidence["screenshots"],
            relationships,
        )

        # ----------------------------------------------------
        # 5. Extract new output keys
        # ----------------------------------------------------
        filter_results = neo4j_data.get("filter_results") if neo4j_data else None
        aggregates = neo4j_data.get("aggregates") if neo4j_data else None
        ranked_hits = semantic_data.get("hits", []) if semantic_data else []

        not_found_ids = []
        if neo4j_data and neo4j_data.get("not_found_ids"):
            not_found_ids = neo4j_data["not_found_ids"]
        elif trace and trace.get("not_found_ids"):
            not_found_ids = trace["not_found_ids"]

        links_missing = bool(neo4j_data.get("links_missing", False)) if neo4j_data else False
        unmapped_filters = list(understanding.get("unmapped_filters", []))
        if neo4j_data and "unmapped_filters" in neo4j_data:
            for uf in neo4j_data["unmapped_filters"]:
                if uf not in unmapped_filters:
                    unmapped_filters.append(uf)
        fallback_used = trace.get("fallback_used", []) if trace else []
        prefilter_count = semantic_data.get("prefilter_count", 0) if semantic_data else 0

        notes = {
            "not_found_ids": not_found_ids,
            "links_missing": links_missing,
            "unmapped_filters": unmapped_filters,
            "fallback_used": fallback_used,
            "prefilter_count": prefilter_count,
        }

        # ----------------------------------------------------
        # 6. Final context
        # ----------------------------------------------------
        context = {
            "query": query,
            "retrieval_route": route,
            "entities": entities,
            "relationships": relationships,
            "structured_evidence": structured_evidence["records"],
            "semantic_evidence": semantic_evidence["chunks"],
            "screenshots": screenshots,
            "filter_results": filter_results,
            "aggregates": aggregates,
            "ranked_hits": ranked_hits,
            "notes": notes,
            "statistics": {
                "entities": len(entities),
                "relationships": len(relationships),
                "structured_records": len(structured_evidence["records"]),
                "semantic_chunks": len(semantic_evidence["chunks"]),
                "screenshots": len(screenshots),
                "ranked_hits": len(ranked_hits),
                "inconsistent_screenshots": sum(
                    1 for s in screenshots if not s.get("metadata_consistent", True)
                ),
            },
        }

        return context

    # ========================================================
    # NEO4J EVIDENCE EXTRACTION
    # ========================================================

    def _extract_neo4j_evidence(
        self,
        neo4j_data: Any,
    ) -> Dict[str, Any]:
        records = []
        entities = []
        relationships = []
        screenshots = []

        if not neo4j_data:
            return {
                "records": records,
                "entities": entities,
                "relationships": relationships,
                "screenshots": screenshots,
            }

        neo4j_results = neo4j_data.get("results", [])

        for result in neo4j_results:
            if not isinstance(result, dict):
                continue

            res_type = result.get("type")
            data = result.get("data") if "data" in result else result

            if not data:
                continue

            # ------------------------------------------------
            # SHAPE 1: DICT-SHAPED CONTEXTS
            # ------------------------------------------------
            if isinstance(data, dict):
                # Shape 1A: defect_context {defect, executions, testcases, screenshots}
                if res_type == "defect_context" or (res_type is None and data.get("defect")):
                    df = data.get("defect")
                    ex_list = data.get("executions") or ([data.get("execution")] if data.get("execution") else [])
                    tc_list = data.get("testcases") or ([data.get("testcase")] if data.get("testcase") else [])
                    sc_list = data.get("screenshots") or []
                    lc_raw = data.get("failure_logs") or data.get("failure_log")
                    lc_list = lc_raw if isinstance(lc_raw, list) else ([lc_raw] if lc_raw else [])

                    if df and isinstance(df, dict):
                        df_id = df.get("defect_id")
                        entities.append({"id": df_id, "type": "Defect", "source": "neo4j", "properties": df})

                        for ex in ex_list:
                            if ex and isinstance(ex, dict):
                                ex_id = ex.get("execution_id")
                                entities.append({"id": ex_id, "type": "Execution", "source": "neo4j", "properties": ex})
                                relationships.append({"source": "neo4j", "source_id": ex_id, "target_id": df_id, "relationship": "FOUND_DEFECT"})

                        for tc in tc_list:
                            if tc and isinstance(tc, dict):
                                tc_id = tc.get("test_case_id")
                                entities.append({"id": tc_id, "type": "TestCase", "source": "neo4j", "properties": tc})
                                relationships.append({"source": "neo4j", "source_id": tc_id, "target_id": df_id, "relationship": "HAS_DEFECT"})
                                for ex in ex_list:
                                    if ex and isinstance(ex, dict):
                                        if not ex.get("test_case_id") or ex.get("test_case_id") == tc_id:
                                            relationships.append({"source": "neo4j", "source_id": tc_id, "target_id": ex.get("execution_id"), "relationship": "HAS_EXECUTION"})

                        for sc in sc_list:
                            if isinstance(sc, dict):
                                sc_id = sc.get("screenshot_id")
                                entities.append({"id": sc_id, "type": "Screenshot", "source": "neo4j", "properties": sc})
                                screenshots.append({"id": sc_id, "source": "neo4j", "properties": sc})
                                relationships.append({"source": "neo4j", "source_id": df_id, "target_id": sc_id, "relationship": "HAS_SCREENSHOT"})
                                for ex in ex_list:
                                    if ex and isinstance(ex, dict):
                                        relationships.append({"source": "neo4j", "source_id": ex.get("execution_id"), "target_id": sc_id, "relationship": "CAPTURED_SCREENSHOT"})

                        for lc in lc_list:
                            if lc and isinstance(lc, dict):
                                lc_id = lc.get("log_id")
                                entities.append({"id": lc_id, "type": "LogChunk", "source": "neo4j", "properties": lc})
                                if lc.get("execution_id"):
                                    relationships.append({"source": "neo4j", "source_id": lc.get("execution_id"), "target_id": lc_id, "relationship": "HAS_FAILURE_LOG"})

                    records.append({
                        "defect": df,
                        "defect_id": df.get("defect_id") if df else None,
                        "execution": ex_list[0] if ex_list else None,
                        "testcase": tc_list[0] if tc_list else None,
                        "failure_log": lc_list[0] if lc_list else None,
                        "executions": ex_list,
                        "testcases": tc_list,
                        "screenshots": sc_list,
                        "failure_logs": lc_list,
                    })

                # Shape 1B: execution_context {execution, testcase/testcases, defects, screenshots}
                elif res_type == "execution_context" or (res_type is None and data.get("execution")):
                    ex = data.get("execution")
                    tc_raw = data.get("testcases") or data.get("testcase")
                    tc_list = tc_raw if isinstance(tc_raw, list) else ([tc_raw] if tc_raw else [])
                    df_raw = data.get("defects") or data.get("defect")
                    df_list = df_raw if isinstance(df_raw, list) else ([df_raw] if df_raw else [])
                    sc_raw = data.get("screenshots") or data.get("screenshot")
                    sc_list = sc_raw if isinstance(sc_raw, list) else ([sc_raw] if sc_raw else [])
                    lc_raw = data.get("failure_logs") or data.get("failure_log")
                    lc_list = lc_raw if isinstance(lc_raw, list) else ([lc_raw] if lc_raw else [])

                    if ex and isinstance(ex, dict):
                        ex_id = ex.get("execution_id")
                        entities.append({"id": ex_id, "type": "Execution", "source": "neo4j", "properties": ex})

                        for tc in tc_list:
                            if tc and isinstance(tc, dict):
                                tc_id = tc.get("test_case_id")
                                entities.append({"id": tc_id, "type": "TestCase", "source": "neo4j", "properties": tc})
                                relationships.append({"source": "neo4j", "source_id": tc_id, "target_id": ex_id, "relationship": "HAS_EXECUTION"})

                        for df in df_list:
                            if isinstance(df, dict):
                                df_id = df.get("defect_id")
                                entities.append({"id": df_id, "type": "Defect", "source": "neo4j", "properties": df})
                                relationships.append({"source": "neo4j", "source_id": ex_id, "target_id": df_id, "relationship": "FOUND_DEFECT"})
                                for tc in tc_list:
                                    if tc and isinstance(tc, dict):
                                        relationships.append({"source": "neo4j", "source_id": tc.get("test_case_id"), "target_id": df_id, "relationship": "HAS_DEFECT"})

                        for sc in sc_list:
                            if isinstance(sc, dict):
                                sc_id = sc.get("screenshot_id")
                                entities.append({"id": sc_id, "type": "Screenshot", "source": "neo4j", "properties": sc})
                                screenshots.append({"id": sc_id, "source": "neo4j", "properties": sc})
                                relationships.append({"source": "neo4j", "source_id": ex_id, "target_id": sc_id, "relationship": "CAPTURED_SCREENSHOT"})

                        for lc in lc_list:
                            if isinstance(lc, dict):
                                lc_id = lc.get("log_id")
                                entities.append({"id": lc_id, "type": "LogChunk", "source": "neo4j", "properties": lc})
                                relationships.append({"source": "neo4j", "source_id": ex_id, "target_id": lc_id, "relationship": "HAS_FAILURE_LOG"})

                    records.append({
                        "execution": ex,
                        "execution_id": ex.get("execution_id") if ex else None,
                        "testcase": tc_list[0] if tc_list else None,
                        "defect": df_list[0] if df_list else None,
                        "failure_log": lc_list[0] if lc_list else None,
                        "testcases": tc_list,
                        "defects": df_list,
                        "screenshots": sc_list,
                        "failure_logs": lc_list,
                    })

                # Shape 1C: testcase_context {testcase, executions, defects, screenshots}
                elif res_type == "testcase_context" or (res_type is None and data.get("testcase")):
                    tc = data.get("testcase")
                    ex_raw = data.get("executions") or data.get("execution")
                    ex_list = ex_raw if isinstance(ex_raw, list) else ([ex_raw] if ex_raw else [])
                    df_raw = data.get("defects") or data.get("defect")
                    df_list = df_raw if isinstance(df_raw, list) else ([df_raw] if df_raw else [])
                    sc_raw = data.get("screenshots") or data.get("screenshot")
                    sc_list = sc_raw if isinstance(sc_raw, list) else ([sc_raw] if sc_raw else [])
                    lc_raw = data.get("failure_logs") or data.get("failure_log")
                    lc_list = lc_raw if isinstance(lc_raw, list) else ([lc_raw] if lc_raw else [])

                    if tc and isinstance(tc, dict):
                        tc_id = tc.get("test_case_id")
                        entities.append({"id": tc_id, "type": "TestCase", "source": "neo4j", "properties": tc})

                        for ex in ex_list:
                            if isinstance(ex, dict):
                                ex_id = ex.get("execution_id")
                                entities.append({"id": ex_id, "type": "Execution", "source": "neo4j", "properties": ex})
                                relationships.append({"source": "neo4j", "source_id": tc_id, "target_id": ex_id, "relationship": "HAS_EXECUTION"})

                        for df in df_list:
                            if isinstance(df, dict):
                                df_id = df.get("defect_id")
                                entities.append({"id": df_id, "type": "Defect", "source": "neo4j", "properties": df})
                                relationships.append({"source": "neo4j", "source_id": tc_id, "target_id": df_id, "relationship": "HAS_DEFECT"})
                                for ex in ex_list:
                                    if isinstance(ex, dict):
                                        relationships.append({"source": "neo4j", "source_id": ex.get("execution_id"), "target_id": df_id, "relationship": "FOUND_DEFECT"})

                        for sc in sc_list:
                            if isinstance(sc, dict):
                                sc_id = sc.get("screenshot_id")
                                entities.append({"id": sc_id, "type": "Screenshot", "source": "neo4j", "properties": sc})
                                screenshots.append({"id": sc_id, "source": "neo4j", "properties": sc})
                                relationships.append({"source": "neo4j", "source_id": tc_id, "target_id": sc_id, "relationship": "HAS_SCREENSHOT"})

                        for lc in lc_list:
                            if isinstance(lc, dict):
                                lc_id = lc.get("log_id")
                                entities.append({"id": lc_id, "type": "LogChunk", "source": "neo4j", "properties": lc})
                                if lc.get("execution_id"):
                                    relationships.append({"source": "neo4j", "source_id": lc.get("execution_id"), "target_id": lc_id, "relationship": "HAS_FAILURE_LOG"})

                    records.append({
                        "testcase": tc,
                        "test_case_id": tc.get("test_case_id") if tc else None,
                        "execution": ex_list[0] if ex_list else None,
                        "defect": df_list[0] if df_list else None,
                        "failure_log": lc_list[0] if lc_list else None,
                        "executions": ex_list,
                        "defects": df_list,
                        "screenshots": sc_list,
                        "failure_logs": lc_list,
                    })

                # Shape 1D: screenshot_context {screenshot, testcases, executions, defects}
                elif res_type == "screenshot_context" or ("screenshot" in data and ("testcases" in data or "executions" in data or "defects" in data)):
                    sc = data.get("screenshot")
                    tc_list = data.get("testcases") or []
                    ex_list = data.get("executions") or []
                    df_list = data.get("defects") or []

                    if sc and isinstance(sc, dict):
                        sc_id = sc.get("screenshot_id")
                        entities.append({"id": sc_id, "type": "Screenshot", "source": "neo4j", "properties": sc})
                        screenshots.append({
                            "id": sc_id,
                            "source": "neo4j",
                            "properties": sc,
                            "context_shape": "screenshot_context",
                            "context_data": data,
                        })

                        for tc in tc_list:
                            if isinstance(tc, dict):
                                tc_id = tc.get("test_case_id")
                                entities.append({"id": tc_id, "type": "TestCase", "source": "neo4j", "properties": tc})
                                relationships.append({"source": "neo4j", "source_id": tc_id, "target_id": sc_id, "relationship": "HAS_SCREENSHOT"})

                        for ex in ex_list:
                            if isinstance(ex, dict):
                                ex_id = ex.get("execution_id")
                                entities.append({"id": ex_id, "type": "Execution", "source": "neo4j", "properties": ex})
                                relationships.append({"source": "neo4j", "source_id": ex_id, "target_id": sc_id, "relationship": "CAPTURED_SCREENSHOT"})

                        for df in df_list:
                            if isinstance(df, dict):
                                df_id = df.get("defect_id")
                                entities.append({"id": df_id, "type": "Defect", "source": "neo4j", "properties": df})
                                relationships.append({"source": "neo4j", "source_id": df_id, "target_id": sc_id, "relationship": "HAS_SCREENSHOT"})

                    records.append({
                        "screenshot": sc,
                        "screenshot_id": sc.get("screenshot_id") if sc else None,
                        "testcases": tc_list,
                        "executions": ex_list,
                        "defects": df_list,
                    })

                # Shape 1E: Flat single entity
                else:
                    if data.get("defect_id"):
                        entities.append({"id": data["defect_id"], "type": "Defect", "source": "neo4j", "properties": data})
                    elif data.get("test_case_id"):
                        entities.append({"id": data["test_case_id"], "type": "TestCase", "source": "neo4j", "properties": data})
                    elif data.get("execution_id"):
                        entities.append({"id": data["execution_id"], "type": "Execution", "source": "neo4j", "properties": data})
                    elif data.get("screenshot_id"):
                        entities.append({"id": data["screenshot_id"], "type": "Screenshot", "source": "neo4j", "properties": data})
                        screenshots.append({"id": data["screenshot_id"], "source": "neo4j", "properties": data})
                    records.append(data)

            # ------------------------------------------------
            # SHAPE 2: LIST-SHAPED (List of paths or list of samples)
            # ------------------------------------------------
            elif isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue

                    # If item is a path dict: {testcase, execution, defect, screenshot}
                    if any(k in item for k in ("testcase", "execution", "defect", "screenshot")):
                        testcase = item.get("testcase")
                        execution = item.get("execution")
                        defect = item.get("defect")
                        screenshot = item.get("screenshot")

                        if testcase and isinstance(testcase, dict):
                            entities.append({"id": testcase.get("test_case_id"), "type": "TestCase", "source": "neo4j", "properties": testcase})
                        if execution and isinstance(execution, dict):
                            entities.append({"id": execution.get("execution_id"), "type": "Execution", "source": "neo4j", "properties": execution})
                        if defect and isinstance(defect, dict):
                            entities.append({"id": defect.get("defect_id"), "type": "Defect", "source": "neo4j", "properties": defect})
                        if screenshot and isinstance(screenshot, dict):
                            sc_id = screenshot.get("screenshot_id")
                            entities.append({"id": sc_id, "type": "Screenshot", "source": "neo4j", "properties": screenshot})
                            screenshots.append({"id": sc_id, "source": "neo4j", "properties": screenshot})

                        if testcase and execution:
                            relationships.append({"source": "neo4j", "source_id": testcase.get("test_case_id"), "target_id": execution.get("execution_id"), "relationship": "HAS_EXECUTION"})
                        if testcase and defect:
                            relationships.append({"source": "neo4j", "source_id": testcase.get("test_case_id"), "target_id": defect.get("defect_id"), "relationship": "HAS_DEFECT"})
                        if execution and defect:
                            relationships.append({"source": "neo4j", "source_id": execution.get("execution_id"), "target_id": defect.get("defect_id"), "relationship": "FOUND_DEFECT"})
                        if defect and screenshot:
                            relationships.append({"source": "neo4j", "source_id": defect.get("defect_id"), "target_id": screenshot.get("screenshot_id"), "relationship": "HAS_SCREENSHOT"})
                        if execution and screenshot:
                            relationships.append({"source": "neo4j", "source_id": execution.get("execution_id"), "target_id": screenshot.get("screenshot_id"), "relationship": "CAPTURED_SCREENSHOT"})

                    # Otherwise flat entity item (e.g. from filter_results sample)
                    else:
                        if item.get("defect_id"):
                            entities.append({"id": item["defect_id"], "type": "Defect", "source": "neo4j", "properties": item})
                        elif item.get("test_case_id"):
                            entities.append({"id": item["test_case_id"], "type": "TestCase", "source": "neo4j", "properties": item})
                        elif item.get("execution_id"):
                            entities.append({"id": item["execution_id"], "type": "Execution", "source": "neo4j", "properties": item})
                        elif item.get("screenshot_id"):
                            entities.append({"id": item["screenshot_id"], "type": "Screenshot", "source": "neo4j", "properties": item})
                            screenshots.append({"id": item["screenshot_id"], "source": "neo4j", "properties": item})

                    records.append(item)

        return {
            "records": records,
            "entities": entities,
            "relationships": relationships,
            "screenshots": screenshots,
        }

    # ========================================================
    # LIGHTRAG EVIDENCE
    # ========================================================

    def _extract_lightrag_evidence(
        self,
        lightrag_data: Any,
    ) -> Dict[str, Any]:
        entities = []
        relationships = []
        chunks = []

        if not lightrag_data or not isinstance(lightrag_data, dict):
            return {
                "entities": entities,
                "relationships": relationships,
                "chunks": chunks,
            }

        result = lightrag_data.get("results", {})
        if not isinstance(result, dict):
            return {
                "entities": entities,
                "relationships": relationships,
                "chunks": chunks,
            }

        data = result.get("data", {})
        if not isinstance(data, dict):
            return {
                "entities": entities,
                "relationships": relationships,
                "chunks": chunks,
            }

        # Entities
        for entity in data.get("entities", []):
            if isinstance(entity, dict) and entity.get("entity_name"):
                entities.append({
                    "id": entity.get("entity_name"),
                    "type": entity.get("entity_type", "Entity"),
                    "source": "lightrag",
                    "description": entity.get("description", ""),
                })

        # Relationships
        for rel in data.get("relationships", []):
            if isinstance(rel, dict) and rel.get("src_id") and rel.get("tgt_id"):
                relationships.append({
                    "source": "lightrag",
                    "source_id": rel.get("src_id"),
                    "target_id": rel.get("tgt_id"),
                    "relationship": rel.get("rel_name", "RELATED_TO"),
                    "description": rel.get("description", ""),
                })

        # Text chunks
        for chunk in data.get("chunks", []):
            if isinstance(chunk, dict) and chunk.get("content"):
                chunks.append(chunk["content"])
            elif isinstance(chunk, str):
                chunks.append(chunk)

        return {
            "entities": entities,
            "relationships": relationships,
            "chunks": chunks,
        }

    # ========================================================
    # ENTITY MERGING
    # ========================================================

    def _merge_entities(
        self,
        neo4j_entities: List[Dict[str, Any]],
        lightrag_entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        merged = {}
        for entity in neo4j_entities:
            eid = entity.get("id")
            if eid and eid not in merged:
                merged[eid] = entity

        for entity in lightrag_entities:
            eid = entity.get("id")
            if not eid:
                continue
            if eid not in merged:
                merged[eid] = entity
            elif entity.get("description"):
                merged[eid]["semantic_description"] = entity["description"]

        return list(merged.values())

    # ========================================================
    # RELATIONSHIP MERGING
    # ========================================================

    def _merge_relationships(
        self,
        neo4j_relationships: List[Dict[str, Any]],
        lightrag_relationships: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        merged = {}
        for rel in neo4j_relationships:
            key = (rel.get("source_id"), rel.get("target_id"), rel.get("relationship"))
            merged[key] = rel

        for rel in lightrag_relationships:
            key = (rel.get("source_id"), rel.get("target_id"), rel.get("relationship"))
            if key not in merged:
                merged[key] = rel
            elif rel.get("description"):
                merged[key]["semantic_description"] = rel["description"]

        return list(merged.values())

    # ========================================================
    # SCREENSHOT EVIDENCE NORMALIZATION
    # ========================================================

    def _normalize_screenshots(
        self,
        screenshots: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        normalized = []
        seen_ids = set()

        for screenshot in screenshots:
            sc_id = screenshot.get("id")
            if not sc_id or sc_id in seen_ids:
                continue
            seen_ids.add(sc_id)

            properties = screenshot.get("properties", {})

            # ------------------------------------------------
            # Handle screenshot_context shape
            # ------------------------------------------------
            if screenshot.get("context_shape") == "screenshot_context":
                ctx_data = screenshot.get("context_data", {})
                graph_tcs = [tc["test_case_id"] for tc in ctx_data.get("testcases", []) if isinstance(tc, dict) and tc.get("test_case_id")]
                graph_exs = [ex["execution_id"] for ex in ctx_data.get("executions", []) if isinstance(ex, dict) and ex.get("execution_id")]
                graph_dfs = [df["defect_id"] for df in ctx_data.get("defects", []) if isinstance(df, dict) and df.get("defect_id")]

                source_tc = properties.get("test_case_id")
                source_ex = properties.get("execution_id")
                source_df = properties.get("bug_id") or properties.get("defect_id")

                warnings = []
                tc_match = (not source_tc or source_tc in graph_tcs)
                ex_match = (not source_ex or source_ex in graph_exs)
                df_match = (not source_df or source_df in graph_dfs)

                if not tc_match:
                    warnings.append(f"Screenshot test_case_id '{source_tc}' not found in graph linkage: {graph_tcs}")
                if not ex_match:
                    warnings.append(f"Screenshot execution_id '{source_ex}' not found in graph linkage: {graph_exs}")
                if not df_match:
                    warnings.append(f"Screenshot defect_id '{source_df}' not found in graph linkage: {graph_dfs}")

                metadata_consistent = tc_match and ex_match and df_match

                normalized.append({
                    "id": sc_id,
                    "source": "neo4j",
                    "source_metadata": {
                        "test_case_id": source_tc,
                        "execution_id": source_ex,
                        "defect_id": source_df,
                    },
                    "graph_linkage": {
                        "test_case_ids": graph_tcs,
                        "execution_ids": graph_exs,
                        "defect_ids": graph_dfs,
                    },
                    "metadata_consistent": metadata_consistent,
                    "metadata_warnings": warnings,
                    "properties": properties,
                })

            # ------------------------------------------------
            # Handle general screenshot shape (e.g. via defect/path)
            # ------------------------------------------------
            else:
                source_tc = properties.get("test_case_id")
                source_ex = properties.get("execution_id")
                source_df = properties.get("bug_id") or properties.get("defect_id")

                authoritative_tcs = []
                authoritative_exs = []
                authoritative_dfs = []

                for rel in relationships:
                    if rel.get("target_id") == sc_id:
                        if rel.get("relationship") == "HAS_SCREENSHOT":
                            authoritative_dfs.append(rel.get("source_id"))
                            authoritative_tcs.append(rel.get("source_id"))
                        elif rel.get("relationship") == "CAPTURED_SCREENSHOT":
                            authoritative_exs.append(rel.get("source_id"))

                authoritative_tcs = [x for x in dict.fromkeys(authoritative_tcs) if x and str(x).startswith("TC-")]
                authoritative_exs = [x for x in dict.fromkeys(authoritative_exs) if x and str(x).startswith("EXEC-")]
                authoritative_dfs = [x for x in dict.fromkeys(authoritative_dfs) if x and str(x).startswith("BUG-")]

                warnings = []
                tc_match = (not source_tc or not authoritative_tcs or source_tc in authoritative_tcs)
                ex_match = (not source_ex or not authoritative_exs or source_ex in authoritative_exs)
                df_match = (not source_df or not authoritative_dfs or source_df in authoritative_dfs)

                if not tc_match:
                    warnings.append(f"Screenshot metadata test_case_id '{source_tc}' mismatch with graph {authoritative_tcs}")
                if not ex_match:
                    warnings.append(f"Screenshot metadata execution_id '{source_ex}' mismatch with graph {authoritative_exs}")
                if not df_match:
                    warnings.append(f"Screenshot metadata defect_id '{source_df}' mismatch with graph {authoritative_dfs}")

                metadata_consistent = tc_match and ex_match and df_match

                normalized.append({
                    "id": sc_id,
                    "source": "neo4j",
                    "source_metadata": {
                        "test_case_id": source_tc,
                        "execution_id": source_ex,
                        "defect_id": source_df,
                    },
                    "graph_linkage": {
                        "test_case_ids": authoritative_tcs,
                        "execution_ids": authoritative_exs,
                        "defect_id": source_df,
                    },
                    "metadata_consistent": metadata_consistent,
                    "metadata_warnings": warnings,
                    "properties": properties,
                })

        return normalized


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
    print("CONTEXT ASSEMBLER TEST")
    print("=" * 60)

    retriever = HybridRetriever()
    assembler = ContextAssembler()
    try:
        await retriever.initialize()

        test_q = "BUG-000176 details"
        res = await retriever.retrieve(test_q)
        context = assembler.assemble(res)

        print("\nASSEMBLED CONTEXT:")
        print(f"Entities: {len(context['entities'])}")
        print(f"Relationships: {len(context['relationships'])}")
        print(f"Notes: {context['notes']}")

    finally:
        retriever.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())