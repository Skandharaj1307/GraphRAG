import os
import json
import re
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from openai import AsyncOpenAI


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from project root
load_dotenv(BASE_DIR / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY not found in .env"
    )

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Free model used for query understanding
MODEL_NAME = "openrouter/free"


# ============================================================
# QUERY UNDERSTANDING
# ============================================================

class QueryUnderstanding:

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )

    # --------------------------------------------------------
    # SYSTEM PROMPT
    # --------------------------------------------------------

    def _build_system_prompt(self) -> str:

        return """
You are a Query Understanding module for a Test Management
Graph RAG system.

Your job is ONLY to analyze the user's query.

Do NOT answer the user's question.
Do NOT retrieve data.
Do NOT invent IDs or facts.

Return ONLY valid JSON.

The JSON must have exactly this structure:

{
    "intent": "",
    "entities": {
        "test_case_ids": [],
        "execution_ids": [],
        "defect_ids": []
    },
    "filters": {},
    "low_level_keywords": [],
    "high_level_keywords": []
}

------------------------------------------------------------
INTENT
------------------------------------------------------------

Choose the most appropriate intent:

- testcase_lookup
- execution_lookup
- defect_lookup
- testcase_execution_analysis
- defect_analysis
- failure_analysis
- screenshot_lookup
- semantic_search
- general_test_analysis

------------------------------------------------------------
ENTITY EXTRACTION
------------------------------------------------------------

Extract explicit IDs from the query.

Test case IDs:
TC-XXXXXX

Execution IDs:
EXEC-XXXXXX

Defect IDs:
BUG-XXXXXX

Only include IDs that actually appear in the query.

------------------------------------------------------------
FILTERS
------------------------------------------------------------

Extract explicit structured filters when present.

Possible filter fields include:

- status
- severity
- priority
- module
- environment
- browser
- operating_system
- build_number
- tester
- developer
- assigned_to
- automation_status
- release
- risk
- regression

Example:

"critical defects in production"

should produce:

{
    "severity": "Critical",
    "environment": "PROD"
}

Do NOT invent filters that are not explicitly stated.

------------------------------------------------------------
LOW-LEVEL KEYWORDS
------------------------------------------------------------

These should identify specific entities, IDs, technical terms,
or concrete concepts useful for retrieval.

Examples:

TC-000001
EXEC-003016
BUG-000176
permission error
validation exception
Safari
POS

------------------------------------------------------------
HIGH-LEVEL KEYWORDS
------------------------------------------------------------

These should describe the broader semantic topic of the query.

Examples:

defects found during test execution
test execution failure
permission related failures
production defects
test case performance

------------------------------------------------------------
IMPORTANT
------------------------------------------------------------

Preserve IDs exactly.

Do not create IDs.

Do not answer the question.

Return JSON only.
"""


    # --------------------------------------------------------
    # JSON CLEANING
    # --------------------------------------------------------

    def _extract_json(self, text: str) -> Dict[str, Any]:

        text = text.strip()

        # Remove markdown code fences if the model adds them
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        text = text.strip()

        try:
            return json.loads(text)

        except json.JSONDecodeError:

            # Try to locate the JSON object
            start = text.find("{")
            end = text.rfind("}")

            if start != -1 and end != -1:
                candidate = text[start:end + 1]

                try:
                    return json.loads(candidate)

                except json.JSONDecodeError:
                    pass

        raise ValueError(
            f"Query Understanding returned invalid JSON:\n{text}"
        )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def _validate_result(
        self,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:

        required_top_level = [
            "intent",
            "entities",
            "filters",
            "low_level_keywords",
            "high_level_keywords",
        ]

        for field in required_top_level:

            if field not in result:
                raise ValueError(
                    f"Missing required field: {field}"
                )

        entities = result["entities"]

        required_entities = [
            "test_case_ids",
            "execution_ids",
            "defect_ids",
        ]

        for field in required_entities:

            if field not in entities:
                raise ValueError(
                    f"Missing entity field: {field}"
                )

            if not isinstance(entities[field], list):
                raise ValueError(
                    f"{field} must be a list"
                )

        if not isinstance(result["filters"], dict):
            raise ValueError(
                "filters must be a dictionary"
            )

        if not isinstance(result["low_level_keywords"], list):
            raise ValueError(
                "low_level_keywords must be a list"
            )

        if not isinstance(result["high_level_keywords"], list):
            raise ValueError(
                "high_level_keywords must be a list"
            )

        return result


    # --------------------------------------------------------
    # ANALYZE QUERY
    # --------------------------------------------------------

    async def analyze(
        self,
        query: str
    ) -> Dict[str, Any]:

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        response = await self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": self._build_system_prompt(),
                },
                {
                    "role": "user",
                    "content": query,
                },
            ],
            temperature=0,
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError(
                "Query Understanding LLM returned empty response."
            )

        result = self._extract_json(content)

        return self._validate_result(result)


# ============================================================
# TEST
# ============================================================

async def main():

    print("=" * 60)
    print("QUERY UNDERSTANDING TEST")
    print("=" * 60)

    query_understanding = QueryUnderstanding()

    test_queries = [

        # TestCase → Execution → Defect
        "Which defects were found in the execution of test case TC-000001?",

        # Specific defect
        "Give me details about defect BUG-000176.",

        # Execution failure
        "Why did execution EXEC-003016 fail?",

        # Structured filters
        "Show me critical defects in PROD.",

        # Semantic query
        "Find failures related to permission errors.",

    ]

    for index, query in enumerate(test_queries, start=1):

        print()
        print("-" * 60)
        print(f"TEST QUERY {index}")
        print("-" * 60)

        print("Query:")
        print(query)

        try:

            result = await query_understanding.analyze(query)

            print()
            print("Query Understanding Result:")
            print(json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            ))

        except Exception as e:

            print()
            print("ERROR:")
            print(e)

    print()
    print("=" * 60)
    print("✓ QUERY UNDERSTANDING TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":

    import asyncio

    asyncio.run(main())