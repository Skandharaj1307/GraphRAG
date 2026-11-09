import os
import json
import pytest
from unittest.mock import patch, MagicMock

from graph.llm_client import (
    tolerant_json_parse,
    is_openrouter,
    get_openrouter_headers,
    get_base_url_host,
    get_model_for_role,
    _hash_cache_key,
    _read_cache,
    _write_cache,
    is_transient_error,
    LLMInfraError,
)


# ==============================================================================
# 1. Tolerant JSON Parser Tests
# ==============================================================================

def test_tolerant_json_parse_clean():
    raw = '{"status": "ok", "count": 42}'
    parsed = tolerant_json_parse(raw)
    assert parsed == {"status": "ok", "count": 42}


def test_tolerant_json_parse_code_fences():
    raw = '```json\n{"intent": "defect_lookup", "target_entity": "defect"}\n```'
    parsed = tolerant_json_parse(raw)
    assert parsed["intent"] == "defect_lookup"
    assert parsed["target_entity"] == "defect"


def test_tolerant_json_parse_conversational_wrapping():
    raw = """
    Here is the analysis of the query you requested:
    ```json
    {
        "intent": "defect_analysis",
        "operation": "group_by",
        "group_by_field": "severity"
    }
    ```
    Hope this helps!
    """
    parsed = tolerant_json_parse(raw)
    assert parsed["intent"] == "defect_analysis"
    assert parsed["operation"] == "group_by"
    assert parsed["group_by_field"] == "severity"


def test_tolerant_json_parse_raw_braces():
    raw = 'Sure thing! {"entities": {"defect_ids": ["BUG-000100"]}, "operation": "lookup"} done.'
    parsed = tolerant_json_parse(raw)
    assert parsed["entities"]["defect_ids"] == ["BUG-000100"]
    assert parsed["operation"] == "lookup"


def test_tolerant_json_parse_trailing_commas():
    raw = '{"name": "test", "items": [1, 2, ], }'
    parsed = tolerant_json_parse(raw)
    assert parsed["name"] == "test"


def test_tolerant_json_parse_invalid_raises():
    with pytest.raises(ValueError, match="Could not parse valid JSON"):
        tolerant_json_parse("This is just plain text without any JSON object at all.")


# ==============================================================================
# 2. Base URL, Headers, and Host Detection Tests
# ==============================================================================

def test_openrouter_detection_and_headers():
    or_url = "https://openrouter.ai/api/v1"
    assert is_openrouter(or_url) is True
    headers = get_openrouter_headers(or_url)
    assert "HTTP-Referer" in headers
    assert "X-Title" in headers

    ollama_url = "http://localhost:11434/v1"
    assert is_openrouter(ollama_url) is False
    assert get_openrouter_headers(ollama_url) == {}

    cf_url = "https://ollama-tunnel.example.com/v1"
    assert is_openrouter(cf_url) is False
    assert get_openrouter_headers(cf_url) == {}


def test_get_base_url_host():
    assert get_base_url_host("https://openrouter.ai/api/v1") == "openrouter.ai"
    assert get_base_url_host("http://localhost:11434/v1") == "localhost:11434"
    assert get_base_url_host("https://tunnel.example.com/v1") == "tunnel.example.com"


# ==============================================================================
# 3. Role Models and Fallbacks Tests
# ==============================================================================

def test_role_model_selection():
    with patch.dict(os.environ, {
        "LLM_MODEL": "default-model",
        "ROUTER_MODEL": "special-router",
        "ANSWER_MODEL": "",
        "JUDGE_MODEL": "",
    }, clear=False):
        # Dynamically verify fallback logic
        from graph import llm_client
        orig_router = llm_client.ROUTER_MODEL
        orig_answer = llm_client.ANSWER_MODEL
        orig_llm = llm_client.LLM_MODEL

        try:
            llm_client.LLM_MODEL = "default-model"
            llm_client.ROUTER_MODEL = "special-router"
            llm_client.ANSWER_MODEL = "default-model"
            llm_client.JUDGE_MODEL = "default-model"

            assert get_model_for_role("router") == "special-router"
            assert get_model_for_role("answer") == "default-model"
            assert get_model_for_role("judge") == "default-model"
            assert get_model_for_role("unknown") == "default-model"
        finally:
            llm_client.ROUTER_MODEL = orig_router
            llm_client.ANSWER_MODEL = orig_answer
            llm_client.LLM_MODEL = orig_llm


# ==============================================================================
# 4. Transient Error Detection Tests
# ==============================================================================

def test_is_transient_error():
    assert is_transient_error(Exception("HTTP 429: Too Many Requests")) is True
    assert is_transient_error(Exception("Server returned 502 Bad Gateway")) is True
    assert is_transient_error(Exception("Cloudflare tunnel 524 timed out")) is True
    assert is_transient_error(Exception("Connection refused by peer")) is True
    assert is_transient_error(ValueError("Invalid syntax")) is False


# ==============================================================================
# 5. Caching Logic Tests
# ==============================================================================

def test_cache_key_hash():
    k1 = _hash_cache_key("http://url", "model-a", [{"role": "user", "content": "hi"}], 0.0)
    k2 = _hash_cache_key("http://url", "model-a", [{"role": "user", "content": "hi"}], 0.0)
    k3 = _hash_cache_key("http://url", "model-b", [{"role": "user", "content": "hi"}], 0.0)

    assert k1 == k2
    assert k1 != k3


# ==============================================================================
# 6. Type Consistency on Cache Miss vs Hit & Call Sites
# ==============================================================================

@pytest.mark.anyio
async def test_complete_chat_returns_same_type_on_hit_and_miss(tmp_path):
    from graph import llm_client
    from unittest.mock import AsyncMock

    orig_cache = llm_client.LLM_CACHE
    orig_cache_dir = llm_client.CACHE_DIR
    llm_client.LLM_CACHE = True
    llm_client.CACHE_DIR = tmp_path / "llm_cache"

    try:
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "canonical string response"
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "hello world test"}]

        # 1. First call (cache miss)
        res1 = await llm_client.complete_chat(
            messages=messages,
            client=mock_client,
            model="test-model",
            base_url="https://api.test/v1"
        )
        assert isinstance(res1, str)
        assert res1 == "canonical string response"
        assert mock_client.chat.completions.create.call_count == 1

        # 2. Second call with exact same parameters (cache hit)
        res2 = await llm_client.complete_chat(
            messages=messages,
            client=mock_client,
            model="test-model",
            base_url="https://api.test/v1"
        )
        assert isinstance(res2, str)
        assert res2 == "canonical string response"
        # Type match check: both MUST be identical type (str)
        assert type(res1) is type(res2)
        # Verify API was NOT called again on cache hit
        assert mock_client.chat.completions.create.call_count == 1
    finally:
        llm_client.LLM_CACHE = orig_cache
        llm_client.CACHE_DIR = orig_cache_dir


@pytest.mark.anyio
async def test_router_and_final_answer_call_sites_work_with_str_contract():
    from unittest.mock import patch
    from graph.query_understanding import QueryUnderstanding
    from graph.final_llm import FinalLLM

    # 1. Router call site
    router_json = '{"intent": "defect_lookup", "target_entity": "defect", "operation": "lookup", "entities": {"defect_ids": ["BUG-000001"]}}'
    with patch("graph.query_understanding.complete_chat", return_value=router_json):
        qu = QueryUnderstanding(client=MagicMock(), model="test-router")
        parsed = await qu.analyze("lookup BUG-000001")
        assert isinstance(parsed, dict)
        assert parsed["intent"] == "defect_lookup"
        assert parsed["target_entity"] == "defect"

    # 2. FinalLLM call site
    llm_text = "The issue was caused by a null pointer error."
    with patch("graph.final_llm.complete_chat", return_value=llm_text):
        final_llm = FinalLLM(client=MagicMock(), model="test-answer")
        ans = await final_llm.generate([{"role": "user", "content": "explain defect"}])
        assert isinstance(ans, str)
        assert ans == "The issue was caused by a null pointer error."


