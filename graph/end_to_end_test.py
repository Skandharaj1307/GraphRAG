import asyncio

from graph.hybrid_retriever import HybridRetriever
from graph.context_assembler import ContextAssembler
from graph.context_to_llm import ContextToLLMFormatter
from graph.grounding_validator import GroundingValidator


# ============================================================
# PART 6.6.2 - END-TO-END TESTING
# ============================================================


class EndToEndTester:

    """
    End-to-end validation of the GraphRAG pipeline.

    This test intentionally does NOT call Mistral.

    It validates:

        Query
          ↓
        Query Understanding
          ↓
        Retrieval Router
          ↓
        Neo4j / LightRAG
          ↓
        Context Assembly
          ↓
        Context → LLM
          ↓
        Grounding Validator
    """

    def __init__(self):

        print()
        print("=" * 60)
        print("INITIALIZING END-TO-END TEST")
        print("=" * 60)

        self.retriever = HybridRetriever()
        self.context_assembler = ContextAssembler()
        self.context_formatter = ContextToLLMFormatter()
        self.validator = GroundingValidator()

        print()
        print("✓ Hybrid Retriever created")
        print("✓ Context Assembler created")
        print("✓ Context → LLM Formatter created")
        print("✓ Grounding Validator created")

    # ========================================================
    # INITIALIZE
    # ========================================================

    async def initialize(self):

        print()
        print("=" * 60)
        print("INITIALIZING RETRIEVAL LAYER")
        print("=" * 60)

        await self.retriever.initialize()

        print()
        print("✓ Retrieval layer initialized")

    # ========================================================
    # RUN SINGLE TEST
    # ========================================================

    async def run_test(
        self,
        test_number: int,
        query: str,
        expected_route: str
    ):

        print()
        print("=" * 60)
        print(
            f"TEST {test_number}"
        )
        print("=" * 60)

        print()
        print(
            f"Query:\n{query}"
        )

        print()
        print(
            f"Expected route: "
            f"{expected_route}"
        )

        # ----------------------------------------------------
        # Retrieval
        # ----------------------------------------------------

        retrieval_result = (
            await self.retriever.retrieve(
                query
            )
        )

        if not retrieval_result:

            raise RuntimeError(
                "Retrieval returned no result."
            )

        # ----------------------------------------------------
        # Route
        # ----------------------------------------------------

        route = retrieval_result.get(
            "route",
            {}
        )

        actual_route = route.get(
            "route"
        )

        print()
        print(
            f"Actual route: "
            f"{actual_route}"
        )

        if actual_route != expected_route:

            print()
            print(
                "⚠ Route differs from expected route."
            )

        else:

            print(
                "✓ Retrieval route verified"
            )

        # ----------------------------------------------------
        # Context Assembly
        # ----------------------------------------------------

        context = (
            self.context_assembler.assemble(
                retrieval_result
            )
        )

        if not context:

            raise RuntimeError(
                "Context assembly returned empty context."
            )

        statistics = context.get(
            "statistics",
            {}
        )

        print()
        print("Context:")

        print(
            f"  Entities           : "
            f"{statistics.get('entities', 0)}"
        )

        print(
            f"  Relationships      : "
            f"{statistics.get('relationships', 0)}"
        )

        print(
            f"  Structured records : "
            f"{statistics.get('structured_records', 0)}"
        )

        print(
            f"  Semantic chunks    : "
            f"{statistics.get('semantic_chunks', 0)}"
        )

        print(
            f"  Screenshots        : "
            f"{statistics.get('screenshots', 0)}"
        )

        # ----------------------------------------------------
        # Context → LLM
        # ----------------------------------------------------

        messages = (
            self._build_messages(
                context
            )
        )

        if len(messages) != 2:

            raise RuntimeError(
                "Expected exactly two LLM messages."
            )

        print()
        print(
            f"✓ LLM messages created: "
            f"{len(messages)}"
        )

        print(
            f"  System message: "
            f"{len(messages[0]['content'])} characters"
        )

        print(
            f"  User message: "
            f"{len(messages[1]['content'])} characters"
        )

        # ----------------------------------------------------
        # Return Test Result
        # ----------------------------------------------------

        print()
        print(
            f"✓ TEST {test_number} COMPLETED"
        )

        return {
            "query": query,
            "route": actual_route,
            "context": context,
            "messages": messages
        }

    # ========================================================
    # BUILD LLM MESSAGES
    # ========================================================

    def _build_messages(
        self,
        context: dict
    ):

        """
        Convert context into LLM messages.

        Uses the existing ContextToLLMFormatter
        implementation.
        """

        import json
        import os
        import tempfile

        temp_path = None

        try:

            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
                encoding="utf-8"
            ) as temp_file:

                json.dump(
                    context,
                    temp_file,
                    indent=2,
                    ensure_ascii=False
                )

                temp_path = temp_file.name

            messages = (
                self.context_formatter.process(
                    temp_path
                )
            )

            return messages

        finally:

            if (
                temp_path is not None
                and os.path.exists(temp_path)
            ):

                os.remove(
                    temp_path
                )

    # ========================================================
    # GROUNDING VALIDATOR TEST
    # ========================================================

    def test_grounding_validator(
        self,
        context: dict
    ):

        print()
        print("=" * 60)
        print("GROUNDING VALIDATOR END-TO-END TEST")
        print("=" * 60)

        # ----------------------------------------------------
        # Extract known IDs
        # ----------------------------------------------------

        evidence_ids = (
            self.validator.get_evidence_ids(
                context
            )
        )

        print()
        print("Evidence IDs:")

        for evidence_id in sorted(
            evidence_ids
        ):

            print(
                f"  {evidence_id}"
            )

        # ----------------------------------------------------
        # Valid Answer
        # ----------------------------------------------------

        valid_answer = (
            "Test case TC-000001 has execution "
            "EXEC-003016, which found defects "
            "BUG-000176 and BUG-009797."
        )

        print()
        print("Testing valid grounded answer:")

        validation = (
            self.validator.validate(
                valid_answer,
                context
            )
        )

        print(
            f"  Valid: "
            f"{validation['valid']}"
        )

        if validation["valid"]:

            print(
                "  ✓ Valid grounded answer accepted"
            )

        else:

            print(
                "  ✗ Valid grounded answer rejected"
            )

            for error in validation.get(
                "errors",
                []
            ):

                print(
                    f"    ERROR: {error}"
                )

        # ----------------------------------------------------
        # Hallucinated Answer
        # ----------------------------------------------------

        hallucinated_answer = (
            "Test case TC-000001 found defect "
            "BUG-123456."
        )

        print()
        print(
            "Testing hallucinated answer:"
        )

        validation = (
            self.validator.validate(
                hallucinated_answer,
                context
            )
        )

        print(
            f"  Valid: "
            f"{validation['valid']}"
        )

        if not validation["valid"]:

            print(
                "  ✓ Hallucinated ID detected"
            )

            for error in validation.get(
                "errors",
                []
            ):

                print(
                    f"    ERROR: {error}"
                )

        else:

            print(
                "  ✗ Hallucinated ID was not detected"
            )

        print()
        print(
            "✓ GROUNDING VALIDATOR TEST COMPLETED"
        )

    # ========================================================
    # RUN ALL TESTS
    # ========================================================

    async def run_all_tests(self):

        results = []

        # ----------------------------------------------------
        # TEST 1
        # ----------------------------------------------------

        results.append(
            await self.run_test(
                1,
                "Give me details about defect BUG-000176.",
                "neo4j"
            )
        )

        # ----------------------------------------------------
        # TEST 2
        # ----------------------------------------------------

        results.append(
            await self.run_test(
                2,
                (
                    "Which defects were found in the "
                    "execution of test case TC-000001?"
                ),
                "hybrid"
            )
        )

        # ----------------------------------------------------
        # TEST 3
        # ----------------------------------------------------

        results.append(
            await self.run_test(
                3,
                "Why did execution EXEC-003016 fail?",
                "hybrid"
            )
        )

        # ----------------------------------------------------
        # TEST 4
        # ----------------------------------------------------

        results.append(
            await self.run_test(
                4,
                "Find failures related to permission errors.",
                "hybrid"
            )
        )

        # ----------------------------------------------------
        # TEST 5
        # ----------------------------------------------------

        results.append(
            await self.run_test(
                5,
                "Show me critical defects in PROD.",
                "neo4j"
            )
        )

        # ----------------------------------------------------
        # Grounding Validator
        # ----------------------------------------------------

        self.test_grounding_validator(
            results[1]["context"]
        )

        return results

    # ========================================================
    # CLOSE
    # ========================================================

    async def close(self):

        print()
        print("=" * 60)
        print("CLOSING END-TO-END TEST")
        print("=" * 60)

        try:

            self.retriever.close()

            print(
                "✓ Hybrid Retriever closed"
            )

        except Exception as error:

            print(
                f"⚠ Error closing Hybrid Retriever: "
                f"{error}"
            )


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 60)
    print("PART 6.6.2 - END-TO-END TESTING")
    print("=" * 60)

    tester = None

    try:

        # ----------------------------------------------------
        # Create Tester
        # ----------------------------------------------------

        tester = EndToEndTester()

        # ----------------------------------------------------
        # Initialize
        # ----------------------------------------------------

        await tester.initialize()

        # ----------------------------------------------------
        # Run Tests
        # ----------------------------------------------------

        results = (
            await tester.run_all_tests()
        )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("END-TO-END TEST SUMMARY")
        print("=" * 60)

        print()
        print(
            f"Total retrieval tests: "
            f"{len(results)}"
        )

        print()

        for index, result in enumerate(
            results,
            start=1
        ):

            print(
                f"Test {index}: "
                f"{result['route']}"
            )

        print()
        print("=" * 60)
        print(
            "✓ 6.6.2 END-TO-END TESTING COMPLETED"
        )
        print("=" * 60)

        print()
        print(
            "No Mistral API request was made."
        )

    except Exception as error:

        print()
        print("=" * 60)
        print("END-TO-END TEST ERROR")
        print("=" * 60)

        print()
        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

    finally:

        if tester is not None:

            await tester.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )