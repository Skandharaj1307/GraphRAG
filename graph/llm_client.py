import os
import json
import time
import re
import hashlib
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI, APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

logger = logging.getLogger("graph.llm_client")

# -----------------------------------------------------------------------------
# 1. Environment Loading (python-dotenv override=True)
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# Fallback to local_secrets if env vars unset
_FALLBACK_KEY = ""
try:
    from graph.local_secrets import (
        OPENROUTER_API_KEY as _LOCAL_OR_KEY,
        MISTRAL_API_KEY as _LOCAL_MISTRAL_KEY,
    )
    _FALLBACK_KEY = _LOCAL_OR_KEY or _LOCAL_MISTRAL_KEY or ""
except ImportError:
    pass

# Read configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY") or _FALLBACK_KEY or "EMPTY"
LLM_MODEL = os.getenv("LLM_MODEL") or "openrouter/free"

ROUTER_MODEL = os.getenv("ROUTER_MODEL") or LLM_MODEL
ANSWER_MODEL = os.getenv("ANSWER_MODEL") or LLM_MODEL
JUDGE_MODEL = os.getenv("JUDGE_MODEL") or LLM_MODEL

try:
    LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "300"))
except ValueError:
    LLM_TIMEOUT = 300.0

LLM_CACHE = os.getenv("LLM_CACHE", "0").strip().lower() in ("1", "true", "yes")
CACHE_DIR = BASE_DIR / ".cache" / "llm"


# -----------------------------------------------------------------------------
# 2. Exceptions & Transient Error Detection
# -----------------------------------------------------------------------------
class LLMInfraError(RuntimeError):
    """Raised when an LLM infrastructure failure persists after retries (429, 5xx, timeout, conn)."""
    pass


def is_openrouter(base_url: Optional[str] = None) -> bool:
    url = (base_url or LLM_BASE_URL or "").lower()
    return "openrouter.ai" in url


def get_base_url_host(base_url: Optional[str] = None) -> str:
    url = base_url or LLM_BASE_URL
    try:
        parsed = urlparse(url)
        return parsed.netloc or parsed.path or url
    except Exception:
        return url


def is_transient_error(error: Exception) -> bool:
    """Detect if an exception is a transient infra failure (429, 5xx, timeouts, connection drops)."""
    if isinstance(error, (RateLimitError, InternalServerError, APITimeoutError, APIConnectionError, asyncio.TimeoutError)):
        return True

    err_text = str(error).lower()
    transient_indicators = [
        "429", "rate limit", "rate_limited",
        "500", "502", "503", "504", "520", "521", "522", "523", "524",
        "timeout", "timed out", "connection error", "connection refused",
        "connection reset", "cloudflare", "tunnel", "bad gateway"
    ]
    return any(ind in err_text for ind in transient_indicators)


# -----------------------------------------------------------------------------
# 3. Headers & Client Helpers
# -----------------------------------------------------------------------------
def get_openrouter_headers(base_url: Optional[str] = None) -> Dict[str, str]:
    if is_openrouter(base_url):
        return {
            "HTTP-Referer": "https://github.com/GraphRAG-1",
            "X-Title": "GraphRAG-1",
        }
    return {}


def get_model_for_role(role: str = "llm") -> str:
    role_lower = (role or "llm").lower()
    if role_lower == "router":
        return ROUTER_MODEL
    elif role_lower == "answer":
        return ANSWER_MODEL
    elif role_lower == "judge":
        return JUDGE_MODEL
    return LLM_MODEL


def get_async_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None
) -> AsyncOpenAI:
    url = base_url or LLM_BASE_URL
    key = api_key or LLM_API_KEY
    t = timeout if timeout is not None else LLM_TIMEOUT
    headers = get_openrouter_headers(url)

    return AsyncOpenAI(
        api_key=key,
        base_url=url,
        timeout=t,
        default_headers=headers if headers else None,
    )


def get_sync_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None
) -> OpenAI:
    url = base_url or LLM_BASE_URL
    key = api_key or LLM_API_KEY
    t = timeout if timeout is not None else LLM_TIMEOUT
    headers = get_openrouter_headers(url)

    return OpenAI(
        api_key=key,
        base_url=url,
        timeout=t,
        default_headers=headers if headers else None,
    )


def get_client_and_model(
    role: str = "llm",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None
) -> Tuple[AsyncOpenAI, str]:
    """Helper to get (AsyncOpenAI client, model_name) for a specific role."""
    client = get_async_client(base_url=base_url, api_key=api_key, timeout=timeout)
    model = get_model_for_role(role)
    return client, model


# -----------------------------------------------------------------------------
# 4. Tolerant JSON Parser
# -----------------------------------------------------------------------------
def tolerant_json_parse(text: str) -> Dict[str, Any]:
    """
    Extract and parse JSON from LLM output tolerantly:
    - Strips markdown code blocks (```json ... ``` or ``` ... ```)
    - Extracts the outermost or first {...} block
    - Logs clear diagnostic messages on parse failure
    """
    if not text:
        raise ValueError("Empty text cannot be parsed as JSON.")

    cleaned = text.strip()

    # 1. Direct parse attempt
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2. Strip code fences
    fence_pattern = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
    match = fence_pattern.search(cleaned)
    if match:
        fenced_content = match.group(1).strip()
        try:
            parsed = json.loads(fenced_content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # 3. Regex extract first {...} block with balanced or best-effort braces
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace:last_brace + 1].strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            # Handle common LLM trailing comma issue
            sanitized = re.sub(r",\s*([\]}])", r"\1", candidate)
            try:
                parsed = json.loads(sanitized)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

    logger.warning("Failed to parse JSON from LLM output. Raw snippet: %s", cleaned[:200])
    raise ValueError(f"Could not parse valid JSON from LLM output snippet: {cleaned[:150]}")


# -----------------------------------------------------------------------------
# 5. Disk Cache Implementation
# -----------------------------------------------------------------------------
def _hash_cache_key(base_url: str, model: str, messages: Any, temperature: float) -> str:
    serialized = json.dumps(
        {
            "base_url": base_url,
            "model": model,
            "messages": messages,
            "temperature": round(temperature, 4),
        },
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _read_cache(cache_key: str) -> Optional[str]:
    if not LLM_CACHE:
        return None
    cache_path = CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("content")
        except Exception:
            return None
    return None


def _write_cache(cache_key: str, content: str, model: str, base_url: str):
    if not LLM_CACHE:
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = CACHE_DIR / f"{cache_key}.json"
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "content": content,
                    "model": model,
                    "base_url": base_url,
                    "timestamp": time.time(),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        logger.debug("Failed to write to LLM cache: %s", e)


# -----------------------------------------------------------------------------
# 6. Unified Resilient Async Completion Function
# -----------------------------------------------------------------------------
async def complete_chat(
    messages: List[Dict[str, str]],
    role: str = "llm",
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    max_retries: int = 3,
    base_backoff: float = 2.0,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
    client: Optional[AsyncOpenAI] = None,
    model: Optional[str] = None,
) -> str:
    """
    Unified async chat completion call:
    - Role-based model selection (router, answer, judge, llm)
    - Disk caching (when LLM_CACHE=1)
    - 3-attempt exponential backoff retry for transient errors (429, 5xx, timeouts, conn)
    - Raises LLMInfraError on persistent infra failure
    """
    url = base_url or LLM_BASE_URL
    chosen_model = model or get_model_for_role(role)
    cli = client or get_async_client(base_url=url, api_key=api_key, timeout=timeout)

    cache_key = _hash_cache_key(url, chosen_model, messages, temperature)
    cached_content = _read_cache(cache_key)
    if cached_content is not None:
        return cached_content

    call_params: Dict[str, Any] = {
        "model": chosen_model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        call_params["max_tokens"] = max_tokens

    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            response = await cli.chat.completions.create(**call_params)
            if not response or not response.choices:
                raise ValueError("LLM response contains no choices.")
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM response returned empty message content.")

            # Only cache successful completion
            _write_cache(cache_key, str(content), chosen_model, url)
            return str(content)

        except Exception as err:
            last_error = err
            if is_transient_error(err):
                if attempt < max_retries - 1:
                    sleep_time = base_backoff * (2 ** attempt)
                    logger.warning(
                        "[LLM RETRY] Role='%s', Model='%s', Transient error on attempt %d/%d: %s. Retrying in %.1fs...",
                        role, chosen_model, attempt + 1, max_retries, err, sleep_time
                    )
                    await asyncio.sleep(sleep_time)
                    continue
                else:
                    logger.error(
                        "[LLM INFRA ERROR] Exhausted %d retries for Role='%s' on base_url='%s': %s",
                        max_retries, role, get_base_url_host(url), err
                    )
                    raise LLMInfraError(f"LLM infrastructure failure ({type(err).__name__}): {err}") from err
            else:
                # Non-transient error: do not retry
                raise err

    if last_error:
        raise LLMInfraError(f"LLM infrastructure failure: {last_error}") from last_error
    raise LLMInfraError("Unknown LLM completion error.")

