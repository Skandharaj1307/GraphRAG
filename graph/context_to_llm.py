import json
from pathlib import Path
from typing import Dict, Any

from graph.final_prompt import GroundedPromptBuilder


# ============================================================
# CONTEXT → LLM FORMATTER
# ============================================================

class ContextToLLMFormatter:

    """
    Converts the real ContextAssembler output into the
    message format expected by the final Mistral LLM.
    """

    def __init__(self):

        self.prompt_builder = GroundedPromptBuilder()

    # ========================================================
    # LOAD CONTEXT
    # ========================================================

    def load_context(
        self,
        context_file: str
    ) -> Dict[str, Any]:

        """
        Load the JSON output produced by ContextAssembler.
        """

        path = Path(context_file)

        if not path.exists():
            raise FileNotFoundError(
                f"Context file not found: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8"
        ) as file:

            context = json.load(file)

        if not isinstance(context, dict):
            raise ValueError(
                "Context file must contain a JSON object."
            )

        return context

    # ========================================================
    # EXTRACT QUERY
    # ========================================================

    def extract_query(
        self,
        context: Dict[str, Any]
    ) -> str:

        """
        Extract the original user query from the assembled
        context.
        """

        query = context.get("query")

        if not query:
            raise ValueError(
                "The assembled context does not contain "
                "a 'query' field."
            )

        return query

    # ========================================================
    # FORMAT FOR LLM
    # ========================================================

    def format_for_llm(
        self,
        context: Dict[str, Any]
    ) -> list:

        """
        Convert the complete assembled context into
        Mistral-compatible chat messages.
        """

        query = self.extract_query(context)

        messages = self.prompt_builder.build_messages(
            query=query,
            context=context
        )

        return messages

    # ========================================================
    # VALIDATE MESSAGES
    # ========================================================

    def validate_messages(
        self,
        messages: list
    ) -> None:

        """
        Validate that the generated messages have the
        structure required by the final LLM.
        """

        if not isinstance(messages, list):
            raise ValueError(
                "Messages must be a list."
            )

        if len(messages) != 2:
            raise ValueError(
                "Expected exactly two messages: "
                "system and user."
            )

        # ----------------------------------------------------
        # System message
        # ----------------------------------------------------

        system_message = messages[0]

        if system_message.get("role") != "system":
            raise ValueError(
                "First message must have role='system'."
            )

        if not system_message.get("content"):
            raise ValueError(
                "System message content is empty."
            )

        # ----------------------------------------------------
        # User message
        # ----------------------------------------------------

        user_message = messages[1]

        if user_message.get("role") != "user":
            raise ValueError(
                "Second message must have role='user'."
            )

        if not user_message.get("content"):
            raise ValueError(
                "User message content is empty."
            )

    # ========================================================
    # FORMAT AND VALIDATE
    # ========================================================

    def process(
        self,
        context_file: str
    ) -> list:

        """
        Complete context → LLM formatting pipeline.
        """

        context = self.load_context(
            context_file
        )

        messages = self.format_for_llm(
            context
        )

        self.validate_messages(
            messages
        )

        return messages


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 60)
    print("PART 6.3 - CONTEXT → LLM FORMATTING")
    print("=" * 60)

    # --------------------------------------------------------
    # ContextAssembler output
    # --------------------------------------------------------

    context_file = "context_assembly_test.json"

    formatter = ContextToLLMFormatter()

    # --------------------------------------------------------
    # Load and process real context
    # --------------------------------------------------------

    messages = formatter.process(
        context_file
    )

    # --------------------------------------------------------
    # Basic information
    # --------------------------------------------------------

    print()
    print("✓ Context loaded successfully")

    print()
    print(
        f"✓ Number of LLM messages: {len(messages)}"
    )

    print()
    print(
        f"✓ System message length: "
        f"{len(messages[0]['content'])} characters"
    )

    print()
    print(
        f"✓ User message length: "
        f"{len(messages[1]['content'])} characters"
    )

    # --------------------------------------------------------
    # Verify important information survived formatting
    # --------------------------------------------------------

    user_prompt = messages[1]["content"]

    required_items = [
        "TC-000001",
        "EXEC-003016",
        "BUG-000176",
        "BUG-009797",
        "HAS_EXECUTION",
        "HAS_DEFECT",
        "FOUND_DEFECT",
        "metadata_consistent",
        "graph_linkage",
        "source_metadata"
    ]

    print()
    print("Checking retrieved evidence...")

    for item in required_items:

        if item not in user_prompt:

            raise AssertionError(
                f"Required evidence missing from "
                f"LLM prompt: {item}"
            )

        print(f"  ✓ {item}")

    # --------------------------------------------------------
    # Verify grounding instructions
    # --------------------------------------------------------

    system_prompt = messages[0]["content"]

    required_rules = [
        "Neo4j graph relationships are authoritative",
        "Do not invent",
        "insufficient",
        "metadata_consistent",
        "graph_linkage"
    ]

    print()
    print("Checking grounding rules...")

    for rule in required_rules:

        if rule not in system_prompt:

            raise AssertionError(
                f"Required grounding rule missing: {rule}"
            )

        print(f"  ✓ {rule}")

    # --------------------------------------------------------
    # Display final structure
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("FINAL LLM MESSAGE STRUCTURE")
    print("=" * 60)

    print()

    print(
        f"Message 1: {messages[0]['role']}"
    )

    print(
        f"Message 2: {messages[1]['role']}"
    )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("✓ CONTEXT → LLM FORMATTING TEST PASSED")
    print("=" * 60)

    print()
    print(
        "Real ContextAssembler output successfully "
        "converted into Mistral-compatible messages."
    )

    print()
    print(
        "No Mistral API request was made."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()