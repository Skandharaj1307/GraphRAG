import os

from dotenv import load_dotenv
from openai import AsyncOpenAI


load_dotenv()


# ============================================================
# OPENROUTER FINAL LLM CONFIGURATION
# ============================================================

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

FINAL_LLM_MODEL = "openrouter/free"

OPENROUTER_BASE_URL = (
    "https://openrouter.ai/api/v1"
)


# ============================================================
# FINAL LLM
# ============================================================

class FinalLLM:

    """
    Final answer LLM client.

    Provider:
        OpenRouter

    Model:
        openrouter/free

    This class replaces the previous direct Mistral API
    client while keeping the same interface used by the
    rest of the GraphRAG pipeline.
    """

    def __init__(self):

        if not OPENROUTER_API_KEY:

            raise ValueError(
                "OPENROUTER_API_KEY is not configured. "
                "Please check your .env file."
            )

        self.client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL
        )

        self.model = FINAL_LLM_MODEL

        print(
            f"✓ Final LLM configured: "
            f"{self.model}"
        )

        print(
            "✓ Provider: OpenRouter"
        )

        print(
            f"✓ API endpoint: "
            f"{OPENROUTER_BASE_URL}"
        )

    # ========================================================
    # CONNECTION TEST
    # ========================================================

    async def test_connection(self):

        if not OPENROUTER_API_KEY:

            raise ValueError(
                "OPENROUTER_API_KEY is not configured."
            )

        print(
            "✓ OpenRouter client configuration is valid."
        )

        print(
            "No inference request was sent."
        )

        return True

    # ========================================================
    # GENERATE
    # ========================================================

    async def generate(
        self,
        messages,
        max_tokens=2000
    ):

        if not messages:

            raise ValueError(
                "Messages cannot be empty."
            )

        try:

            response = (
                await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens
                )
            )

        except Exception as error:

            error_text = str(error)

            # ------------------------------------------------
            # Rate-limit handling
            # ------------------------------------------------

            if (
                "429" in error_text
                or
                "rate limit" in error_text.lower()
                or
                "rate_limited" in error_text.lower()
            ):

                raise RuntimeError(
                    "OpenRouter API rate limit reached "
                    "(HTTP 429).\n"
                    "The GraphRAG pipeline and prompt "
                    "formatting completed successfully, "
                    "but OpenRouter rejected the inference "
                    "request because the API key/model is "
                    "currently rate-limited.\n"
                    "Please wait before retrying."
                ) from None

            # ------------------------------------------------
            # Other API errors
            # ------------------------------------------------

            raise RuntimeError(
                f"OpenRouter API request failed:\n"
                f"{error_text}"
            ) from None

        # ====================================================
        # RESPONSE VALIDATION
        # ====================================================

        if not response:

            raise RuntimeError(
                "OpenRouter returned an empty response."
            )

        if not response.choices:

            raise RuntimeError(
                "OpenRouter response contains no choices."
            )

        message = (
            response.choices[0].message
        )

        if message is None:

            raise RuntimeError(
                "OpenRouter returned an empty message."
            )

        content = message.content

        if content is None:

            raise RuntimeError(
                "OpenRouter returned empty content."
            )

        return str(
            content
        ).strip()

    # ========================================================
    # GENERATE TEXT
    # ========================================================

    async def generate_text(
        self,
        messages,
        max_tokens=2000
    ):

        return await self.generate(
            messages=messages,
            max_tokens=max_tokens
        )

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