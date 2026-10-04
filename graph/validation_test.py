import asyncio

from graph.final_answer import FinalAnswerGenerator


# ============================================================
# PART 6.6.3 - VALIDATION & ERROR HANDLING
# ============================================================


class ValidationTester:

    """
    Complete validation and error-handling tests for the
    GraphRAG final answer pipeline.

    Tests:

        1. Empty query
        2. Retrieval failure
        3. Empty retrieval result
        4. Empty context
        5. Mistral/API failure handling
        6. Grounding validation failure
        7. Resource cleanup
    """

    def __init__(self):

        print()
        print("=" * 60)
        print("INITIALIZING VALIDATION TESTER")
        print("=" * 60)

        self.generator = FinalAnswerGenerator()

        print()
        print("✓ Final Answer Pipeline created")

    # ========================================================
    # TEST 1 - EMPTY QUERY
    # ========================================================

    async def test_empty_query(self):

        print()
        print("=" * 60)
        print("TEST 1 - EMPTY QUERY")
        print("=" * 60)

        try:

            await self.generator.generate("")

            print()
            print(
                "✗ FAILED - Empty query was accepted."
            )

            return False

        except ValueError as error:

            print()
            print(
                "✓ ValueError correctly raised"
            )

            print(
                f"  Message: {error}"
            )

            if str(error) == "Query cannot be empty.":

                print(
                    "✓ Error message verified"
                )

                return True

            print(
                "✗ Unexpected error message"
            )

            return False

    # ========================================================
    # TEST 2 - RETRIEVAL FAILURE
    # ========================================================

    async def test_retrieval_failure(self):

        print()
        print("=" * 60)
        print("TEST 2 - RETRIEVAL FAILURE")
        print("=" * 60)

        original_retriever = (
            self.generator.retriever
        )

        class FailingRetriever:

            async def retrieve(self, query):

                raise RuntimeError(
                    "Simulated retrieval failure."
                )

        self.generator.retriever = (
            FailingRetriever()
        )

        try:

            await self.generator.generate(
                "Why did execution EXEC-003016 fail?"
            )

            print()
            print(
                "✗ FAILED - Retrieval failure "
                "was not propagated."
            )

            return False

        except RuntimeError as error:

            print()
            print(
                "✓ Retrieval failure correctly propagated"
            )

            print(
                f"  Message: {error}"
            )

            return (
                str(error)
                == "Simulated retrieval failure."
            )

        finally:

            self.generator.retriever = (
                original_retriever
            )

    # ========================================================
    # TEST 3 - EMPTY RETRIEVAL RESULT
    # ========================================================

    async def test_empty_retrieval_result(self):

        print()
        print("=" * 60)
        print("TEST 3 - EMPTY RETRIEVAL RESULT")
        print("=" * 60)

        original_retriever = (
            self.generator.retriever
        )

        class EmptyRetriever:

            async def retrieve(self, query):

                return None

        self.generator.retriever = (
            EmptyRetriever()
        )

        try:

            await self.generator.generate(
                "Find test information."
            )

            print()
            print(
                "✗ FAILED - Empty retrieval "
                "result was accepted."
            )

            return False

        except RuntimeError as error:

            print()
            print(
                "✓ Empty retrieval result rejected"
            )

            print(
                f"  Message: {error}"
            )

            return (
                str(error)
                == "Hybrid Retriever returned no result."
            )

        finally:

            self.generator.retriever = (
                original_retriever
            )

    # ========================================================
    # TEST 4 - EMPTY CONTEXT
    # ========================================================

    async def test_empty_context(self):

        print()
        print("=" * 60)
        print("TEST 4 - EMPTY CONTEXT")
        print("=" * 60)

        original_assembler = (
            self.generator.context_assembler
        )

        class EmptyContextAssembler:

            def assemble(self, retrieval_result):

                return None

        self.generator.context_assembler = (
            EmptyContextAssembler()
        )

        original_retriever = (
            self.generator.retriever
        )

        class ValidRetriever:

            async def retrieve(self, query):

                return {
                    "route": {
                        "route": "neo4j"
                    }
                }

        self.generator.retriever = (
            ValidRetriever()
        )

        try:

            await self.generator.generate(
                "Give me test information."
            )

            print()
            print(
                "✗ FAILED - Empty context "
                "was accepted."
            )

            return False

        except RuntimeError as error:

            print()
            print(
                "✓ Empty context rejected"
            )

            print(
                f"  Message: {error}"
            )

            return (
                str(error)
                == "Context Assembler returned empty context."
            )

        finally:

            self.generator.context_assembler = (
                original_assembler
            )

            self.generator.retriever = (
                original_retriever
            )

    # ========================================================
    # TEST 5 - MISTRAL/API FAILURE
    # ========================================================

    async def test_llm_failure(self):

        print()
        print("=" * 60)
        print("TEST 5 - FINAL LLM FAILURE")
        print("=" * 60)

        original_build_context = (
            self.generator.build_context
        )

        original_llm = (
            self.generator.llm
        )

        # ----------------------------------------------------
        # Provide valid synthetic context
        # ----------------------------------------------------

        async def fake_build_context(query):

            return {
                "query": query,
                "retrieval_route": "neo4j",
                "entities": [],
                "relationships": [],
                "structured_evidence": [],
                "semantic_evidence": [],
                "screenshots": [],
                "statistics": {
                    "entities": 0,
                    "relationships": 0,
                    "structured_records": 0,
                    "semantic_chunks": 0,
                    "screenshots": 0,
                    "inconsistent_screenshots": 0
                }
            }

        self.generator.build_context = (
            fake_build_context
        )

        class FailingLLM:

            async def generate_text(
                self,
                messages,
                max_tokens=1000
            ):

                raise RuntimeError(
                    "Simulated Mistral HTTP 429."
                )

        self.generator.llm = (
            FailingLLM()
        )

        try:

            await self.generator.generate(
                "Test LLM failure."
            )

            print()
            print(
                "✗ FAILED - LLM failure "
                "was not propagated."
            )

            return False

        except RuntimeError as error:

            print()
            print(
                "✓ LLM failure correctly propagated"
            )

            print(
                f"  Message: {error}"
            )

            return (
                str(error)
                == "Simulated Mistral HTTP 429."
            )

        finally:

            self.generator.build_context = (
                original_build_context
            )

            self.generator.llm = (
                original_llm
            )

    # ========================================================
    # TEST 6 - GROUNDING VALIDATION FAILURE
    # ========================================================

    async def test_grounding_failure(self):

        print()
        print("=" * 60)
        print("TEST 6 - GROUNDING VALIDATION FAILURE")
        print("=" * 60)

        original_build_context = (
            self.generator.build_context
        )

        original_build_messages = (
            self.generator.build_llm_messages
        )

        original_llm = (
            self.generator.llm
        )

        original_validator = (
            self.generator.validator
        )

        # ----------------------------------------------------
        # Synthetic context
        # ----------------------------------------------------

        async def fake_build_context(query):

            return {
                "query": query,
                "retrieval_route": "neo4j",
                "entities": [
                    {
                        "id": "TC-000001",
                        "type": "TestCase"
                    }
                ],
                "relationships": [],
                "structured_evidence": [],
                "semantic_evidence": [],
                "screenshots": [],
                "statistics": {
                    "entities": 1,
                    "relationships": 0,
                    "structured_records": 1,
                    "semantic_chunks": 0,
                    "screenshots": 0,
                    "inconsistent_screenshots": 0
                }
            }

        self.generator.build_context = (
            fake_build_context
        )

        # ----------------------------------------------------
        # Synthetic LLM messages
        # ----------------------------------------------------

        def fake_build_messages(context):

            return [
                {
                    "role": "system",
                    "content": "Grounding test."
                },
                {
                    "role": "user",
                    "content": "Answer from evidence."
                }
            ]

        self.generator.build_llm_messages = (
            fake_build_messages
        )

        # ----------------------------------------------------
        # Synthetic LLM
        # ----------------------------------------------------

        class FakeLLM:

            async def generate_text(
                self,
                messages,
                max_tokens=1000
            ):

                return (
                    "The result contains "
                    "BUG-999999."
                )

        self.generator.llm = (
            FakeLLM()
        )

        # ----------------------------------------------------
        # Synthetic validator
        # ----------------------------------------------------

        class FailingValidator:

            def validate(
                self,
                answer,
                context
            ):

                return {
                    "valid": False,
                    "errors": [
                        "Unsupported ID: BUG-999999"
                    ],
                    "warnings": []
                }

        self.generator.validator = (
            FailingValidator()
        )

        try:

            result = await self.generator.generate(
                "Test grounding failure."
            )

            if result["valid"]:

                print()
                print(
                    "✗ FAILED - Invalid answer "
                    "was accepted."
                )

                return False

            print()
            print(
                "✓ Grounding failure correctly detected"
            )

            print(
                f"  Errors: "
                f"{result['errors']}"
            )

            return True

        finally:

            self.generator.build_context = (
                original_build_context
            )

            self.generator.build_llm_messages = (
                original_build_messages
            )

            self.generator.llm = (
                original_llm
            )

            self.generator.validator = (
                original_validator
            )

    # ========================================================
    # TEST 7 - RESOURCE CLEANUP
    # ========================================================

    async def test_cleanup(self):

        print()
        print("=" * 60)
        print("TEST 7 - RESOURCE CLEANUP")
        print("=" * 60)

        try:

            await self.generator.close()

            print()
            print(
                "✓ Pipeline cleanup completed"
            )

            return True

        except Exception as error:

            print()
            print(
                "✗ Cleanup failed"
            )

            print(
                f"  Error: {error}"
            )

            return False


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 60)
    print("PART 6.6.3 - VALIDATION & ERROR HANDLING")
    print("=" * 60)

    tester = None

    results = []

    try:

        # ----------------------------------------------------
        # Create tester
        # ----------------------------------------------------

        tester = ValidationTester()

        # ----------------------------------------------------
        # Run tests
        # ----------------------------------------------------

        results.append(
            await tester.test_empty_query()
        )

        results.append(
            await tester.test_retrieval_failure()
        )

        results.append(
            await tester.test_empty_retrieval_result()
        )

        results.append(
            await tester.test_empty_context()
        )

        results.append(
            await tester.test_llm_failure()
        )

        results.append(
            await tester.test_grounding_failure()
        )

        results.append(
            await tester.test_cleanup()
        )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        passed = sum(
            1 for result in results
            if result
        )

        total = len(results)

        print()
        print("=" * 60)
        print("VALIDATION & ERROR HANDLING SUMMARY")
        print("=" * 60)

        print()
        print(
            f"Tests passed: "
            f"{passed}/{total}"
        )

        for index, result in enumerate(
            results,
            start=1
        ):

            status = (
                "PASS"
                if result
                else "FAIL"
            )

            print(
                f"  Test {index}: "
                f"{status}"
            )

        # ----------------------------------------------------
        # Final status
        # ----------------------------------------------------

        if passed == total:

            print()
            print("=" * 60)
            print(
                "✓ 6.6.3 VALIDATION & ERROR "
                "HANDLING PASSED"
            )
            print("=" * 60)

        else:

            print()
            print("=" * 60)
            print(
                "✗ 6.6.3 VALIDATION & ERROR "
                "HANDLING FAILED"
            )
            print("=" * 60)

    except Exception as error:

        print()
        print("=" * 60)
        print("UNEXPECTED VALIDATION ERROR")
        print("=" * 60)

        print()
        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

    finally:

        # ----------------------------------------------------
        # Ensure cleanup if Test 7 wasn't reached
        # ----------------------------------------------------

        if tester is not None:

            # Test 7 may already have closed it.
            # Calling close again should remain safe.
            try:

                await tester.generator.close()

            except Exception:
                pass


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )