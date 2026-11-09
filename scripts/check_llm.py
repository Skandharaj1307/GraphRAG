import sys
import time
import asyncio
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graph.llm_client import (
    LLM_BASE_URL,
    LLM_MODEL,
    ROUTER_MODEL,
    ANSWER_MODEL,
    JUDGE_MODEL,
    LLM_TIMEOUT,
    LLM_CACHE,
    get_base_url_host,
    complete_chat,
    tolerant_json_parse,
    LLMInfraError,
)


async def check_llm():
    print("=" * 60)
    print("LLM HEALTH & ENDPOINT VERIFICATION")
    print("=" * 60)
    host = get_base_url_host(LLM_BASE_URL)
    print(f"Base URL Host: {host}")
    print(f"Default Model: {LLM_MODEL}")
    print(f"Router Model:  {ROUTER_MODEL}")
    print(f"Answer Model:  {ANSWER_MODEL}")
    print(f"Judge Model:   {JUDGE_MODEL}")
    print(f"Timeout:       {LLM_TIMEOUT}s")
    print(f"Disk Cache:    {LLM_CACHE}")
    print("-" * 60)

    # 1. One-word prompt test
    print("\n[TEST 1] Sending one-word prompt...")
    t0 = time.time()
    try:
        reply = await complete_chat(
            messages=[{"role": "user", "content": "Reply with exactly one word: READY."}],
            role="llm",
            temperature=0.0,
            max_tokens=300,
        )
        latency = round(time.time() - t0, 3)
        clean_reply = reply.strip()
        print(f"  Latency: {latency}s")
        print(f"  Reply:   '{clean_reply}'")

        if not clean_reply:
            print("  ERROR: Empty reply received!")
            return False
        print("  ✓ Test 1 Passed.")
    except Exception as e:
        print(f"  ERROR in Test 1: {e}")
        return False

    # 2. JSON-output prompt test
    print("\n[TEST 2] Sending JSON-output prompt...")
    t0 = time.time()
    try:
        json_reply = await complete_chat(
            messages=[
                {
                    "role": "user",
                    "content": "Return ONLY a JSON object with keys 'status' (string value 'ok') and 'count' (integer value 42). Do not include any other text.",
                }
            ],
            role="router",
            temperature=0.0,
            max_tokens=500,
        )
        latency = round(time.time() - t0, 3)
        print(f"  Latency: {latency}s")
        print(f"  Raw Reply: {json_reply.strip()[:100]}")

        parsed = tolerant_json_parse(json_reply)
        print(f"  Parsed JSON: {parsed}")

        if parsed.get("status") != "ok" or int(parsed.get("count", 0)) != 42:
            print(f"  ERROR: Unexpected JSON content: {parsed}")
            return False
        print("  ✓ Test 2 Passed.")
    except Exception as e:
        print(f"  ERROR in Test 2: {e}")
        return False

    print("\n" + "=" * 60)
    print("ALL LLM CHECKS PASSED SUCCESSFULLY")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(check_llm())
    if not success:
        sys.exit(1)
    sys.exit(0)
