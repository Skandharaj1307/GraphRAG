import json
from typing import Dict, Any, List

from graph.hybrid_retriever import HybridRetriever


# ============================================================
# CONTEXT ASSEMBLER
# ============================================================

class ContextAssembler:

    """
    Combines Neo4j and LightRAG retrieval results into one
    structured evidence package.

    This class does NOT generate an answer.
    It only prepares grounded evidence for the final LLM.
    """

    # ========================================================
    # MAIN ASSEMBLY METHOD
    # ========================================================

    def assemble(
        self,
        retrieval_result: Dict[str, Any]
    ) -> Dict[str, Any]:

        query = retrieval_result.get(
            "query",
            ""
        )

        route = retrieval_result.get(
            "route",
            {}
        )

        neo4j_data = retrieval_result.get(
            "neo4j"
        )

        lightrag_data = retrieval_result.get(
            "lightrag"
        )

        # ----------------------------------------------------
        # Structured evidence
        # ----------------------------------------------------

        structured_evidence = self._extract_neo4j_evidence(
            neo4j_data
        )

        # ----------------------------------------------------
        # Semantic / graph evidence
        # ----------------------------------------------------

        semantic_evidence = self._extract_lightrag_evidence(
            lightrag_data
        )

        # ----------------------------------------------------
        # Deduplicate entities
        # ----------------------------------------------------

        entities = self._merge_entities(
            structured_evidence["entities"],
            semantic_evidence["entities"]
        )

        # ----------------------------------------------------
        # Deduplicate relationships
        # ----------------------------------------------------

        relationships = self._merge_relationships(
            structured_evidence["relationships"],
            semantic_evidence["relationships"]
        )

        # ----------------------------------------------------
        # Screenshot normalization
        #
        # Neo4j graph relationships are treated as the
        # authoritative linkage.
        #
        # Original screenshot metadata is preserved.
        # ----------------------------------------------------

        screenshots = self._normalize_screenshots(
            structured_evidence["screenshots"],
            relationships
        )

        # ----------------------------------------------------
        # Final context
        # ----------------------------------------------------

        context = {
            "query": query,

            "retrieval_route": route,

            "entities": entities,

            "relationships": relationships,

            "structured_evidence": structured_evidence[
                "records"
            ],

            "semantic_evidence": semantic_evidence[
                "chunks"
            ],

            "screenshots": screenshots,

            "statistics": {
                "entities": len(entities),
                "relationships": len(relationships),
                "structured_records": len(
                    structured_evidence["records"]
                ),
                "semantic_chunks": len(
                    semantic_evidence["chunks"]
                ),
                "screenshots": len(screenshots),
                "inconsistent_screenshots": sum(
                    1
                    for screenshot in screenshots
                    if not screenshot[
                        "metadata_consistent"
                    ]
                )
            }
        }

        return context

    # ========================================================
    # NEO4J EVIDENCE
    # ========================================================

    def _extract_neo4j_evidence(
        self,
        neo4j_data: Any
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
                "screenshots": screenshots
            }

        neo4j_results = neo4j_data.get(
            "results",
            []
        )

        for result in neo4j_results:

            data = result.get(
                "data"
            )

            if not data:
                continue

            records.append(data)

            if isinstance(data, list):

                for path in data:

                    if not isinstance(path, dict):
                        continue

                    testcase = path.get(
                        "testcase"
                    )

                    execution = path.get(
                        "execution"
                    )

                    defect = path.get(
                        "defect"
                    )

                    screenshot = path.get(
                        "screenshot"
                    )

                    # ----------------------------------------
                    # TestCase
                    # ----------------------------------------

                    if testcase:

                        entities.append({
                            "id": testcase.get(
                                "test_case_id"
                            ),
                            "type": "TestCase",
                            "source": "neo4j",
                            "properties": testcase
                        })

                    # ----------------------------------------
                    # Execution
                    # ----------------------------------------

                    if execution:

                        entities.append({
                            "id": execution.get(
                                "execution_id"
                            ),
                            "type": "Execution",
                            "source": "neo4j",
                            "properties": execution
                        })

                    # ----------------------------------------
                    # Defect
                    # ----------------------------------------

                    if defect:

                        entities.append({
                            "id": defect.get(
                                "defect_id"
                            ),
                            "type": "Defect",
                            "source": "neo4j",
                            "properties": defect
                        })

                    # ----------------------------------------
                    # Screenshot
                    # ----------------------------------------

                    if screenshot:

                        screenshot_id = screenshot.get(
                            "screenshot_id"
                        )

                        screenshots.append({
                            "id": screenshot_id,
                            "source": "neo4j",
                            "properties": screenshot
                        })

                    # ----------------------------------------
                    # Relationships
                    # ----------------------------------------

                    if testcase and execution:

                        relationships.append({
                            "source": "neo4j",
                            "source_id": testcase.get(
                                "test_case_id"
                            ),
                            "target_id": execution.get(
                                "execution_id"
                            ),
                            "relationship": "HAS_EXECUTION"
                        })

                    if testcase and defect:

                        relationships.append({
                            "source": "neo4j",
                            "source_id": testcase.get(
                                "test_case_id"
                            ),
                            "target_id": defect.get(
                                "defect_id"
                            ),
                            "relationship": "HAS_DEFECT"
                        })

                    if execution and defect:

                        relationships.append({
                            "source": "neo4j",
                            "source_id": execution.get(
                                "execution_id"
                            ),
                            "target_id": defect.get(
                                "defect_id"
                            ),
                            "relationship": "FOUND_DEFECT"
                        })

        return {
            "records": records,
            "entities": entities,
            "relationships": relationships,
            "screenshots": screenshots
        }

    # ========================================================
    # LIGHTRAG EVIDENCE
    # ========================================================

    def _extract_lightrag_evidence(
        self,
        lightrag_data: Any
    ) -> Dict[str, Any]:

        entities = []

        relationships = []

        chunks = []

        if not lightrag_data:

            return {
                "entities": entities,
                "relationships": relationships,
                "chunks": chunks
            }

        result = lightrag_data.get(
            "results",
            {}
        )

        data = result.get(
            "data",
            {}
        )

        # ----------------------------------------------------
        # Entities
        # ----------------------------------------------------

        for entity in data.get(
            "entities",
            []
        ):

            entities.append({
                "id": entity.get(
                    "entity_name"
                ),
                "type": entity.get(
                    "entity_type"
                ),
                "source": "lightrag",
                "description": entity.get(
                    "description"
                )
            })

        # ----------------------------------------------------
        # Relationships
        # ----------------------------------------------------

        for relation in data.get(
            "relationships",
            []
        ):

            relationships.append({
                "source": "lightrag",
                "source_id": relation.get(
                    "src_id"
                ),
                "target_id": relation.get(
                    "tgt_id"
                ),
                "relationship": relation.get(
                    "keywords"
                ),
                "description": relation.get(
                    "description"
                )
            })

        # ----------------------------------------------------
        # Chunks
        # ----------------------------------------------------

        for chunk in data.get(
            "chunks",
            []
        ):

            chunks.append({
                "reference_id": chunk.get(
                    "reference_id"
                ),
                "content": chunk.get(
                    "content"
                ),
                "source": "lightrag"
            })

        return {
            "entities": entities,
            "relationships": relationships,
            "chunks": chunks
        }

    # ========================================================
    # ENTITY MERGING
    # ========================================================

    def _merge_entities(
        self,
        neo4j_entities: List[Dict[str, Any]],
        lightrag_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        merged = {}

        # Neo4j has priority
        for entity in neo4j_entities:

            entity_id = entity.get(
                "id"
            )

            if not entity_id:
                continue

            merged[entity_id] = entity

        # Add LightRAG information
        for entity in lightrag_entities:

            entity_id = entity.get(
                "id"
            )

            if not entity_id:
                continue

            if entity_id not in merged:

                merged[entity_id] = entity

            else:

                if entity.get(
                    "description"
                ):

                    merged[
                        entity_id
                    ][
                        "semantic_description"
                    ] = entity.get(
                        "description"
                    )

        return list(
            merged.values()
        )

    # ========================================================
    # RELATIONSHIP MERGING
    # ========================================================

    def _merge_relationships(
        self,
        neo4j_relationships: List[Dict[str, Any]],
        lightrag_relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        merged = {}

        # Neo4j relationships have priority
        for relation in neo4j_relationships:

            key = (
                relation.get(
                    "source_id"
                ),
                relation.get(
                    "target_id"
                ),
                relation.get(
                    "relationship"
                )
            )

            merged[key] = relation

        # Add LightRAG-only relationships
        for relation in lightrag_relationships:

            key = (
                relation.get(
                    "source_id"
                ),
                relation.get(
                    "target_id"
                ),
                relation.get(
                    "relationship"
                )
            )

            if key not in merged:

                merged[key] = relation

            else:

                if relation.get(
                    "description"
                ):

                    merged[
                        key
                    ][
                        "semantic_description"
                    ] = relation.get(
                        "description"
                    )

        return list(
            merged.values()
        )

    # ========================================================
    # SCREENSHOT EVIDENCE NORMALIZATION
    # ========================================================

    def _normalize_screenshots(
        self,
        screenshots: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        """
        Normalize screenshot evidence using Neo4j graph
        relationships as the authoritative linkage.

        The original screenshot metadata is preserved.

        If screenshot metadata disagrees with the graph,
        the mismatch is explicitly recorded.
        """

        normalized = []

        # ----------------------------------------------------
        # Process every screenshot
        # ----------------------------------------------------

        for screenshot in screenshots:

            properties = screenshot.get(
                "properties",
                {}
            )

            screenshot_id = screenshot.get(
                "id"
            )

            source_testcase_id = properties.get(
                "test_case_id"
            )

            source_execution_id = properties.get(
                "execution_id"
            )

            source_defect_id = properties.get(
                "bug_id"
            )

            # ------------------------------------------------
            # Find authoritative graph relationships
            # for this screenshot.
            #
            # Current Neo4j retrieval reaches the screenshot
            # through the TestCase -> Execution -> Defect
            # path. Therefore the defect ID from the
            # screenshot is used to find the authoritative
            # TestCase and Execution.
            # ------------------------------------------------

            authoritative_testcases = []

            authoritative_executions = []

            if source_defect_id:

                # TestCase -> Defect
                for relation in relationships:

                    if (
                        relation.get(
                            "relationship"
                        ) == "HAS_DEFECT"
                        and relation.get(
                            "target_id"
                        ) == source_defect_id
                    ):

                        testcase_id = relation.get(
                            "source_id"
                        )

                        if testcase_id:

                            authoritative_testcases.append(
                                testcase_id
                            )

                # Execution -> Defect
                for relation in relationships:

                    if (
                        relation.get(
                            "relationship"
                        ) == "FOUND_DEFECT"
                        and relation.get(
                            "target_id"
                        ) == source_defect_id
                    ):

                        execution_id = relation.get(
                            "source_id"
                        )

                        if execution_id:

                            authoritative_executions.append(
                                execution_id
                            )

            # ------------------------------------------------
            # Remove duplicates while preserving order
            # ------------------------------------------------

            authoritative_testcases = list(
                dict.fromkeys(
                    authoritative_testcases
                )
            )

            authoritative_executions = list(
                dict.fromkeys(
                    authoritative_executions
                )
            )

            # ------------------------------------------------
            # Consistency checks
            # ------------------------------------------------

            testcase_match = (
                not source_testcase_id
                or source_testcase_id
                in authoritative_testcases
            )

            execution_match = (
                not source_execution_id
                or source_execution_id
                in authoritative_executions
            )

            defect_match = (
                not source_defect_id
                or any(
                    relation.get(
                        "target_id"
                    ) == source_defect_id
                    and relation.get(
                        "relationship"
                    ) in (
                        "HAS_DEFECT",
                        "FOUND_DEFECT"
                    )
                    for relation in relationships
                )
            )

            metadata_consistent = (
                testcase_match
                and execution_match
                and defect_match
            )

            # ------------------------------------------------
            # Build normalized screenshot
            # ------------------------------------------------

            normalized_screenshot = {

                "id": screenshot_id,

                "source": "neo4j",

                # --------------------------------------------
                # Original source metadata
                # --------------------------------------------

                "source_metadata": {
                    "test_case_id": source_testcase_id,
                    "execution_id": source_execution_id,
                    "defect_id": source_defect_id
                },

                # --------------------------------------------
                # Authoritative graph linkage
                # --------------------------------------------

                "graph_linkage": {
                    "test_case_ids": (
                        authoritative_testcases
                    ),
                    "execution_ids": (
                        authoritative_executions
                    ),
                    "defect_id": source_defect_id
                },

                # --------------------------------------------
                # Consistency status
                # --------------------------------------------

                "metadata_consistent": (
                    metadata_consistent
                ),

                "metadata_warnings": [],

                # --------------------------------------------
                # Original screenshot properties
                # --------------------------------------------

                "properties": properties
            }

            # ------------------------------------------------
            # Add testcase warning
            # ------------------------------------------------

            if not testcase_match:

                normalized_screenshot[
                    "metadata_warnings"
                ].append(
                    "Screenshot test_case_id "
                    "does not match the "
                    "authoritative Neo4j graph linkage."
                )

            # ------------------------------------------------
            # Add execution warning
            # ------------------------------------------------

            if not execution_match:

                normalized_screenshot[
                    "metadata_warnings"
                ].append(
                    "Screenshot execution_id "
                    "does not match the "
                    "authoritative Neo4j graph linkage."
                )

            # ------------------------------------------------
            # Add defect warning
            # ------------------------------------------------

            if not defect_match:

                normalized_screenshot[
                    "metadata_warnings"
                ].append(
                    "Screenshot bug_id does not match "
                    "any authoritative Neo4j defect linkage."
                )

            normalized.append(
                normalized_screenshot
            )

        return normalized


# ============================================================
# REAL END-TO-END TEST
# ============================================================

async def main():

    print("=" * 60)
    print("REAL CONTEXT ASSEMBLY TEST")
    print("=" * 60)

    query = (
        "Which defects were found in the execution "
        "of test case TC-000001?"
    )

    hybrid_retriever = HybridRetriever()

    try:

        # ----------------------------------------------------
        # Initialize real retrievers
        # ----------------------------------------------------

        await hybrid_retriever.initialize()

        # ----------------------------------------------------
        # Real retrieval
        # ----------------------------------------------------

        retrieval_result = await hybrid_retriever.retrieve(
            query
        )

        # ----------------------------------------------------
        # Context assembly
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("ASSEMBLING REAL CONTEXT")
        print("=" * 60)

        assembler = ContextAssembler()

        context = assembler.assemble(
            retrieval_result
        )

        # ----------------------------------------------------
        # Print summary
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("ASSEMBLED CONTEXT SUMMARY")
        print("=" * 60)

        print(
            f"Query: {context['query']}"
        )

        print(
            f"Route: "
            f"{context['retrieval_route']['route']}"
        )

        print(
            f"Entities: "
            f"{context['statistics']['entities']}"
        )

        print(
            f"Relationships: "
            f"{context['statistics']['relationships']}"
        )

        print(
            f"Structured records: "
            f"{context['statistics']['structured_records']}"
        )

        print(
            f"Semantic chunks: "
            f"{context['statistics']['semantic_chunks']}"
        )

        print(
            f"Screenshots: "
            f"{context['statistics']['screenshots']}"
        )

        print(
            f"Inconsistent screenshots: "
            f"{context['statistics']['inconsistent_screenshots']}"
        )

        # ----------------------------------------------------
        # Print entity summary
        # ----------------------------------------------------

        print()
        print("ENTITIES")

        for entity in context["entities"]:

            print(
                f"  {entity['type']}: "
                f"{entity['id']}"
            )

        # ----------------------------------------------------
        # Print relationships
        # ----------------------------------------------------

        print()
        print("RELATIONSHIPS")

        for relation in context["relationships"]:

            print(
                f"  {relation['source_id']}"
                f" --[{relation['relationship']}]--> "
                f"{relation['target_id']}"
            )

        # ----------------------------------------------------
        # Print normalized screenshots
        # ----------------------------------------------------

        print()
        print("SCREENSHOTS")

        for screenshot in context[
            "screenshots"
        ]:

            source_metadata = screenshot.get(
                "source_metadata",
                {}
            )

            graph_linkage = screenshot.get(
                "graph_linkage",
                {}
            )

            print(
                f"  {screenshot['id']}"
            )

            print(
                f"    Source metadata:"
            )

            print(
                f"      TestCase="
                f"{source_metadata.get('test_case_id')}"
            )

            print(
                f"      Execution="
                f"{source_metadata.get('execution_id')}"
            )

            print(
                f"      Defect="
                f"{source_metadata.get('defect_id')}"
            )

            print(
                f"    Graph linkage:"
            )

            print(
                f"      TestCases="
                f"{graph_linkage.get('test_case_ids')}"
            )

            print(
                f"      Executions="
                f"{graph_linkage.get('execution_ids')}"
            )

            print(
                f"      Defect="
                f"{graph_linkage.get('defect_id')}"
            )

            print(
                f"    Metadata consistent="
                f"{screenshot.get('metadata_consistent')}"
            )

            warnings = screenshot.get(
                "metadata_warnings",
                []
            )

            if warnings:

                print(
                    "    Warnings:"
                )

                for warning in warnings:

                    print(
                        f"      - {warning}"
                    )

        # ----------------------------------------------------
        # Save complete context
        # ----------------------------------------------------

        output_file = (
            "context_assembly_test.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                context,
                file,
                indent=4,
                ensure_ascii=False,
                default=str
            )

        print()
        print(
            f"✓ Full context saved to: "
            f"{output_file}"
        )

        print()
        print("=" * 60)
        print("✓ REAL CONTEXT ASSEMBLY TEST COMPLETED")
        print("=" * 60)

    finally:

        hybrid_retriever.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    import asyncio

    asyncio.run(main())