import asyncio
import json
import os
import tempfile

from graph.hybrid_retriever import HybridRetriever
from graph.context_assembler import ContextAssembler
from graph.context_to_llm import ContextToLLMFormatter
from graph.final_llm import FinalLLM
from graph.grounding_validator import GroundingValidator


# ============================================================
# COMPLETE GRAPHRAG ANSWER-GENERATION PIPELINE
# ============================================================


class FinalAnswerGenerator:

    """
    Complete GraphRAG answer-generation pipeline.

    Pipeline:

        User Query
            ↓
        Hybrid Retriever
            ↓
        Context Assembler
            ↓
        Context → LLM Formatter
            ↓
        Final LLM
            ↓
        Grounding Validator
            ↓
        Final Answer
    """

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        print()
        print("=" * 60)
        print("INITIALIZING FINAL ANSWER PIPELINE")
        print("=" * 60)

        # ----------------------------------------------------
        # Hybrid Retrieval
        # ----------------------------------------------------

        self.retriever = HybridRetriever()

        # ----------------------------------------------------
        # Context Assembly
        # ----------------------------------------------------

        self.context_assembler = ContextAssembler()

        # ----------------------------------------------------
        # Context → LLM Formatter
        # ----------------------------------------------------

        self.context_formatter = ContextToLLMFormatter()

        # ----------------------------------------------------
        # Final LLM
        # ----------------------------------------------------

        self.llm = FinalLLM()

        # ----------------------------------------------------
        # Grounding Validator
        # ----------------------------------------------------

        self.validator = GroundingValidator()

        print()
        print("✓ Hybrid Retriever created")
        print("✓ Context Assembler created")
        print("✓ Context → LLM Formatter created")
        print("✓ Final LLM created")
        print("✓ Grounding Validator created")

    # ========================================================
    # INITIALIZE RETRIEVERS
    # ========================================================

    async def initialize(self):

        """
        Initialize Neo4j and LightRAG through the existing
        HybridRetriever.
        """

        print()
        print("=" * 60)
        print("INITIALIZING RETRIEVAL LAYER")
        print("=" * 60)

        await self.retriever.initialize()

        print()
        print("✓ Retrieval layer initialized")

    # ========================================================
    # BUILD LLM MESSAGES
    # ========================================================

    def build_llm_messages(
        self,
        context: dict
    ):

        """
        Convert assembled context into the exact messages
        expected by the final LLM.

        ContextToLLMFormatter currently works with a JSON
        context file, so the in-memory context is temporarily
        written to a JSON file.

        The temporary file is deleted afterwards.
        """

        temp_path = None

        try:

            # ------------------------------------------------
            # Create temporary context file
            # ------------------------------------------------

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

            # ------------------------------------------------
            # Convert context into LLM messages
            # ------------------------------------------------

            messages = (
                self.context_formatter.process(
                    temp_path
                )
            )

            if not messages:

                raise RuntimeError(
                    "Context formatter returned empty messages."
                )

            if len(messages) != 2:

                raise RuntimeError(
                    "Expected exactly 2 LLM messages "
                    "(system + user)."
                )

            return messages

        finally:

            # ------------------------------------------------
            # Remove temporary file
            # ------------------------------------------------

            if (
                temp_path is not None
                and os.path.exists(temp_path)
            ):

                os.remove(
                    temp_path
                )

    # ========================================================
    # BUILD CONTEXT
    # ========================================================

    async def build_context(
        self,
        query: str
    ):

        """
        Run:

            Query
              ↓
        Hybrid Retrieval
              ↓
        Context Assembly
        """

        if not query or not query.strip():

            raise ValueError(
                "Query cannot be empty."
            )

        query = query.strip()

        # ----------------------------------------------------
        # STEP 1 - HYBRID RETRIEVAL
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("STEP 1 - HYBRID RETRIEVAL")
        print("=" * 60)

        print()
        print("User Query:")
        print(query)

        retrieval_result = (
            await self.retriever.retrieve(
                query
            )
        )

        if not retrieval_result:

            raise RuntimeError(
                "Hybrid Retriever returned no result."
            )

        print()
        print("✓ Hybrid retrieval completed")

        # ----------------------------------------------------
        # STEP 2 - CONTEXT ASSEMBLY
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("STEP 2 - CONTEXT ASSEMBLY")
        print("=" * 60)

        context = (
            self.context_assembler.assemble(
                retrieval_result
            )
        )

        if not context:

            raise RuntimeError(
                "Context Assembler returned empty context."
            )

        print()
        print("✓ Context assembly completed")

        # ----------------------------------------------------
        # Display Context Statistics
        # ----------------------------------------------------

        statistics = context.get(
            "statistics",
            {}
        )

        print()
        print("Context statistics:")

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

        print(
            f"  Inconsistent shots : "
            f"{statistics.get('inconsistent_screenshots', 0)}"
        )

        return context

    # ========================================================
    # GENERATE FINAL ANSWER
    # ========================================================

    async def generate(
        self,
        query: str
    ):

        """
        Run the complete GraphRAG answer-generation pipeline.

        Steps:

            1. Hybrid Retrieval
            2. Context Assembly
            3. Context → LLM Formatting
            4. Final LLM Generation
            5. Grounding Validation
        """

        # ----------------------------------------------------
        # STEP 1 + STEP 2
        # ----------------------------------------------------

        context = await self.build_context(
            query
        )

        # ----------------------------------------------------
        # STEP 3 - CONTEXT → LLM
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("STEP 3 - CONTEXT → LLM FORMATTING")
        print("=" * 60)

        messages = (
            self.build_llm_messages(
                context
            )
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
        # STEP 4 - FINAL LLM
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("STEP 4 - FINAL LLM GENERATION")
        print("=" * 60)

        print()
        print(
            "Sending ONE request to OpenRouter..."
        )

        answer = await self.llm.generate_text(
            messages=messages,
            max_tokens=1000
        )

        if not answer:

            raise RuntimeError(
                "Final LLM returned an empty answer."
            )

        answer = answer.strip()

        print()
        print("✓ Final LLM generated an answer")

        # ----------------------------------------------------
        # STEP 5 - GROUNDING VALIDATION
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("STEP 5 - GROUNDING VALIDATION")
        print("=" * 60)

        validation = (
            self.validator.validate(
                answer,
                context
            )
        )

        print()
        print(
            f"Validation result: "
            f"{validation['valid']}"
        )

        # ----------------------------------------------------
        # Validation Failed
        # ----------------------------------------------------

        if not validation["valid"]:

            print()
            print(
                "✗ Grounding validation FAILED"
            )

            for error in validation.get(
                "errors",
                []
            ):

                print(
                    f"  ERROR: {error}"
                )

            return {
                "query": query,
                "answer": answer,
                "valid": False,
                "errors": validation.get(
                    "errors",
                    []
                ),
                "warnings": validation.get(
                    "warnings",
                    []
                ),
                "context": context
            }

        # ----------------------------------------------------
        # Validation Passed
        # ----------------------------------------------------

        print()
        print(
            "✓ Grounding validation PASSED"
        )

        # ----------------------------------------------------
        # Warnings
        # ----------------------------------------------------

        warnings = validation.get(
            "warnings",
            []
        )

        if warnings:

            print()
            print("Warnings:")

            for warning in warnings:

                print(
                    f"  ⚠ {warning}"
                )

        return {
            "query": query,
            "answer": answer,
            "valid": True,
            "errors": [],
            "warnings": warnings,
            "context": context
        }

    # ========================================================
    # CLOSE
    # ========================================================

    async def close(self):

        """
        Close all resources safely.

        HybridRetriever.close() is synchronous,
        so it must NOT be awaited.
        """

        print()
        print("=" * 60)
        print("CLOSING FINAL ANSWER PIPELINE")
        print("=" * 60)

        # ----------------------------------------------------
        # Close Hybrid Retriever
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Close Final LLM
        # ----------------------------------------------------

        try:

            await self.llm.close()

            print(
                "✓ Final LLM closed"
            )

        except Exception as error:

            print(
                f"⚠ Error closing Final LLM: "
                f"{error}"
            )


# ============================================================
# INTERACTIVE TERMINAL
# ============================================================

async def main():

    print("=" * 60)
    print("GRAPHRAG INTERACTIVE QUERY")
    print("=" * 60)

    print()
    print("Enter your question below.")
    print("Type 'exit' to stop the program.")
    print()

    # --------------------------------------------------------
    # USER ENTERS QUESTION
    # --------------------------------------------------------

    query = input(
        "Enter your question: "
    ).strip()

    if not query:

        print()
        print(
            "Question cannot be empty."
        )

        return

    if query.lower() == "exit":

        print()
        print(
            "Exiting GraphRAG."
        )

        return

    generator = None

    try:

        # ----------------------------------------------------
        # Create Complete Pipeline
        # ----------------------------------------------------

        generator = (
            FinalAnswerGenerator()
        )

        # ----------------------------------------------------
        # Initialize Retrieval Layer
        # ----------------------------------------------------

        await generator.initialize()

        # ----------------------------------------------------
        # Run Complete Pipeline
        # ----------------------------------------------------

        result = await generator.generate(
            query
        )

        # ----------------------------------------------------
        # Display Result
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("PIPELINE RESULT")
        print("=" * 60)

        print()
        print(
            f"Query:\n{result['query']}"
        )

        print()
        print(
            f"Grounding Valid: "
            f"{result['valid']}"
        )

        # ----------------------------------------------------
        # Valid Answer
        # ----------------------------------------------------

        if result["valid"]:

            print()
            print("=" * 60)
            print("FINAL GROUNDED ANSWER")
            print("=" * 60)

            print()
            print(
                result["answer"]
            )

            print()
            print("=" * 60)
            print(
                "✓ PIPELINE EXECUTION COMPLETED"
            )
            print("=" * 60)

        # ----------------------------------------------------
        # Invalid Answer
        # ----------------------------------------------------

        else:

            print()
            print("=" * 60)
            print(
                "✗ GROUNDING VALIDATION FAILED"
            )
            print("=" * 60)

            print()

            for error in result.get(
                "errors",
                []
            ):

                print(
                    f"ERROR: {error}"
                )

    # ========================================================
    # FINAL LLM / RUNTIME ERROR
    # ========================================================

    except RuntimeError as error:

        print()
        print("=" * 60)
        print("PIPELINE ERROR")
        print("=" * 60)

        print()
        print(error)

        print()
        print(
            "The retrieval and context stages may "
            "still have completed successfully."
        )

    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as error:

        print()
        print("=" * 60)
        print("UNEXPECTED PIPELINE ERROR")
        print("=" * 60)

        print()
        print(
            f"{type(error).__name__}: {error}"
        )

    # ========================================================
    # ALWAYS CLOSE RESOURCES
    # ========================================================

    finally:

        if generator is not None:

            await generator.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )