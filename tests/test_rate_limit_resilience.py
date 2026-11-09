import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from graph.query_understanding import QueryUnderstanding, is_transient_error


def test_is_transient_error():
    assert is_transient_error(Exception("Error code: 429 - Rate limit exceeded"))
    assert is_transient_error(Exception("HTTP 500 Internal Server Error"))
    assert is_transient_error(Exception("502 Bad Gateway"))
    assert is_transient_error(Exception("503 Service Unavailable"))
    assert is_transient_error(Exception("504 Gateway Timeout"))
    assert is_transient_error(Exception("You have been rate_limited by provider"))

    # Non-transient errors
    assert not is_transient_error(ValueError("Invalid JSON returned"))
    assert not is_transient_error(KeyError("missing key"))
    assert not is_transient_error(Exception("Authentication failed (401)"))


def test_analyze_retries_and_succeeds():
    async def _run():
        qu = QueryUnderstanding()

        # Mock client to fail on attempt 1 with 429, then succeed on attempt 2
        mock_success_response = MagicMock()
        mock_success_response.choices = [
            MagicMock(message=MagicMock(content='{"intent": "defect_lookup", "target_entity": "defect", "operation": "lookup", "entities": {"defect_ids": ["BUG-000176"]}, "filters": {}}'))
        ]

        qu.client.chat.completions.create = AsyncMock(
            side_effect=[
                Exception("Error code: 429 - Rate limit exceeded"),
                mock_success_response,
            ]
        )

        result = await qu.analyze("Give me details about defect BUG-000176.", max_retries=3, base_backoff=0.01)

        assert result.get("status") != "infra_error"
        assert "BUG-000176" in result["entities"]["defect_ids"]
        assert qu.client.chat.completions.create.call_count == 2

    asyncio.run(_run())


def test_analyze_exhausts_retries_and_returns_infra_error():
    async def _run():
        qu = QueryUnderstanding()

        # Mock client to always fail with 429
        qu.client.chat.completions.create = AsyncMock(
            side_effect=Exception("Error code: 429 - Rate limit exceeded: free-models-per-day")
        )

        result = await qu.analyze("Give me details about defect BUG-000176.", max_retries=3, base_backoff=0.01)

        assert result.get("status") == "infra_error"
        assert result.get("intent") == "infra_error"
        assert "429" in result.get("error", "")
        assert qu.client.chat.completions.create.call_count == 3

    asyncio.run(_run())
