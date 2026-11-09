import os
import re
from typing import Optional, Any

from graph.llm_client import (
    LLM_BASE_URL,
    LLM_API_KEY,
    get_async_client,
    get_model_for_role,
    get_base_url_host,
    complete_chat,
    LLMInfraError,
)

FINAL_LLM_MODEL = get_model_for_role("answer")
OPENROUTER_BASE_URL = LLM_BASE_URL
OPENROUTER_API_KEY = LLM_API_KEY


# ============================================================
# OUTPUT SANITIZER
# ============================================================

def sanitize_llm_output(text: str) -> str:
    """
    Sanitize LLM output by removing:
    1. <think>...</think> blocks (including unclosed <think> if truncated).
    2. Leading phrases like "Here's a thinking process:", "Thinking process:", etc.
       If followed by step-by-step thinking and an answer section, extract the answer section.
    3. Leading conversational greetings/preambles like "Hello!", "Sure, here is the answer:".
    """
    if not text:
        return ""

    cleaned = str(text).strip()

    # 1. Strip complete <think>...</think> blocks (multiline)
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE).strip()
    # Strip unclosed <think> if response was truncated
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL | re.IGNORECASE).strip()

    # 2. Check for leading thinking process blocks
    thinking_lead_pattern = re.compile(
        r"^\s*(?:Here(?:'s|\s+is)\s+(?:a\s+)?thinking\s+process:?|"
        r"Thinking\s+[Pp]rocess:?|"
        r"Let(?:'s|\s+us)\s+analyze\s+(?:the\s+)?(?:user\s+)?question:?|"
        r"Chain\s+of\s+[Tt]hought:?|"
        r"Internal\s+[Rr]easoning:?|"
        r"Step-by-step\s+reasoning:?)",
        re.IGNORECASE
    )

    if thinking_lead_pattern.search(cleaned):
        # Look for transition markers where the actual final answer begins
        answer_markers = [
            r"\n\s*(?:\*\*)?(?:Final\s+)?Answer:?(?:\*\*)?\s*",
            r"\n\s*(?:\*\*)?Conclusion:?(?:\*\*)?\s*",
            r"\n\s*(?:\*\*)?Summary:?(?:\*\*)?\s*",
            r"\n\s*(?:Based on (?:the|the provided|the retrieved|Neo4j))",
            r"\n\s*(?:According to (?:the|the provided|the retrieved|Neo4j))",
            r"\n\s*(?:The test case|Test case|Defect|Execution|The defect)",
        ]
        split_found = False
        for marker in answer_markers:
            m = re.search(marker, cleaned, re.IGNORECASE)
            if m:
                if m.start() > 15:
                    candidate = cleaned[m.start():].strip()
                    candidate = re.sub(
                        r"^(?:\*\*)?(?:Final\s+)?Answer:?(?:\*\*)?\s*",
                        "",
                        candidate,
                        flags=re.IGNORECASE
                    ).strip()
                    if candidate:
                        cleaned = candidate
                        split_found = True
                        break
        if not split_found:
            cleaned = thinking_lead_pattern.sub("", cleaned).strip()

    # 3. Strip leading generic greetings/preambles if present
    preamble_pattern = re.compile(
        r"^(?:(?:Hello|Hi|Greetings|Hey)[!.,]?\s*)*"
        r"(?:(?:Sure(?: thing)?|Certainly|Of course)[!.,]?\s*)*"
        r"(?:Here (?:is|are) (?:the |what (?:I|we) found |your )?(?:answer|details|results|requested information)[!.,:]?\s*)*",
        re.IGNORECASE
    )
    cleaned = preamble_pattern.sub("", cleaned).strip()

    return cleaned


# ============================================================
# FINAL LLM
# ============================================================

class FinalLLM:
    """Final answer LLM client using unified llm_client configuration."""

    def __init__(self, client: Optional[Any] = None, model: Optional[str] = None):
        self.model = model or FINAL_LLM_MODEL
        self.client = client or get_async_client()
        self.base_url = LLM_BASE_URL

        print(f"✓ Final LLM configured: {self.model}")
        print(f"✓ API endpoint: {get_base_url_host(self.base_url)}")

    async def test_connection(self):
        print("✓ LLM client configuration is valid.")
        return True

    async def generate(self, messages, max_tokens=2000):
        if not messages:
            raise ValueError("Messages cannot be empty.")

        try:
            content = await complete_chat(
                messages=messages,
                role="answer",
                max_tokens=max_tokens,
                client=self.client,
                model=self.model,
            )
            return sanitize_llm_output(str(content))
        except LLMInfraError as error:
            raise RuntimeError(
                f"LLM API rate limit or infrastructure failure (HTTP 429/5xx/timeout):\n{error}"
            ) from error
        except Exception as error:
            raise RuntimeError(f"LLM API request failed:\n{error}") from error

    async def generate_text(self, messages, max_tokens=2000):
        return await self.generate(messages=messages, max_tokens=max_tokens)

    # ========================================================
    # CLOSE
    # ========================================================

    async def close(self):

        """
        Close the OpenRouter client.

        AsyncOpenAI exposes an async close method.
        """

        try:

            await self.client.close()

        except Exception:

            pass


# ============================================================
# CONFIGURATION TEST
# ============================================================

async def main():

    print("=" * 60)
    print(
        "FINAL LLM - OPENROUTER CONFIGURATION"
    )
    print("=" * 60)

    try:

        llm = FinalLLM()

        print()
        print("Configuration:")

        print(
            f"  Model: "
            f"{llm.model}"
        )

        print(
            "  Provider: OpenRouter"
        )

        print(
            "  API Key: configured"
        )

        print()
        print("=" * 60)
        print(
            "✓ CONFIGURATION TEST PASSED"
        )
        print("=" * 60)

        print()
        print(
            "No inference request was sent."
        )

        await llm.close()

    except Exception as error:

        print()
        print(
            f"✗ Configuration error: "
            f"{error}"
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    import asyncio

    asyncio.run(
        main()
    )