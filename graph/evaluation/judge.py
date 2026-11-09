import os
import json
import re
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from openai import AsyncOpenAI
from graph.evaluation.config import JUDGE_BASE_URL, JUDGE_API_KEY, JUDGE_MODEL
from graph.llm_client import get_async_client, complete_chat, tolerant_json_parse


FAITHFULNESS_PROMPT = """
Context:
{context}

Answer:
{answer}

Instructions:
1. List the key factual claims made in the Answer.
2. For each claim, check if it is supported by the Provided Context (1 for supported, 0 for unsupported).
3. Compute faithfulness = (supported_claims) / (total_claims). If there are no claims, return 1.0.

Return ONLY valid JSON matching this schema:
{{
  "claims": ["claim 1", "claim 2"],
  "supported_claims": 2,
  "total_claims": 2,
  "faithfulness": 1.0
}}
"""

COMPLETENESS_PROMPT = """
Question:
{question}

Answer:
{answer}

Instructions:
Does the answer address every part of the question?
Return 1 if completely answered, or 0 if incomplete/missing parts.

Return ONLY valid JSON matching this schema:
{{
  "completeness": 1,
  "reason": "Brief explanation"
}}
"""


def parse_json_defensive(raw_text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON string defensively, stripping markdown code blocks if present."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        # Fallback regex search for { ... } block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None


class LLMJudge:
    """LLM Judge interface supporting endpoint, export, and import modes."""

    def __init__(
        self,
        mode: str = "none",
        base_url: str = JUDGE_BASE_URL,
        api_key: str = JUDGE_API_KEY,
        model: str = JUDGE_MODEL,
        concurrency_limit: int = 5
    ):
        self.mode = mode
        self.model = model
        self.semaphore = asyncio.Semaphore(concurrency_limit)

        if mode == "endpoint":
            self.client = get_async_client(api_key=api_key, base_url=base_url)
        else:
            self.client = None

    async def evaluate_item(
        self,
        question: str,
        retrieved_context: Any,
        answer: str
    ) -> Dict[str, Any]:
        """Evaluate a single test case using the LLM judge (mode='endpoint')."""
        if self.mode == "none":
            return {"judge_error": False, "skipped": True}

        if self.mode != "endpoint" or not self.client:
            return {"judge_error": True, "reason": f"Judge mode is '{self.mode}', not endpoint."}

        context_str = json.dumps(retrieved_context, ensure_ascii=False) if isinstance(retrieved_context, (dict, list)) else str(retrieved_context or "")
        truncated_context = context_str[:3000]

        async with self.semaphore:
            faithfulness_res = await self._call_judge_with_retry(
                FAITHFULNESS_PROMPT.format(context=truncated_context, answer=answer)
            )
            completeness_res = await self._call_judge_with_retry(
                COMPLETENESS_PROMPT.format(question=question, answer=answer)
            )

        f_parsed = parse_json_defensive(faithfulness_res)
        c_parsed = parse_json_defensive(completeness_res)

        # Correct judge_error flag: true if EITHER parse failed
        judge_error = (f_parsed is None or c_parsed is None)

        faithfulness_score = f_parsed.get("faithfulness", 0.0) if f_parsed else 0.0
        completeness_score = c_parsed.get("completeness", 0) if c_parsed else 0
        completeness_reason = c_parsed.get("reason", "") if c_parsed else "Parse error"

        return {
            "judge_error": judge_error,
            "faithfulness": round(faithfulness_score, 4),
            "completeness": completeness_score,
            "completeness_reason": completeness_reason,
            "raw_faithfulness": f_parsed,
            "raw_completeness": c_parsed
        }

    async def _call_judge_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Call judge LLM with timeout and exponential backoff retries."""
        messages = [
            {"role": "system", "content": "You are a precise evaluation judge. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        try:
            return await complete_chat(
                messages=messages,
                role="judge",
                temperature=0,
                max_retries=max_retries,
                client=self.client,
                model=self.model,
            )
        except Exception:
            return ""


def export_judge_inputs(records: List[Dict[str, Any]], out_dir: str) -> Tuple[str, str]:
    """
    Export judge inputs to judge_inputs.jsonl (skipping infra errors)
    and generate judge_kaggle_notebook.py with vLLM batched chat template execution.
    """
    os.makedirs(out_dir, exist_ok=True)
    jsonl_path = os.path.join(out_dir, "judge_inputs.jsonl")
    notebook_path = os.path.join(out_dir, "judge_kaggle_notebook.py")

    valid_records = []
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in records:
            # Skip infrastructure errors from judge export payload
            if r.get("first_failing_stage") == "infra_error" or r.get("error_text"):
                continue
            item = {
                "id": r["id"],
                "question": r["question"],
                "retrieved_context": r.get("retrieved_context"),
                "answer": r.get("answer"),
                "gold_answer": r.get("gold_answer")
            }
            valid_records.append(item)
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    notebook_script = '''"""
Standalone Kaggle GPU LLM Judge script using vLLM & Qwen/Qwen2.5-7B-Instruct-AWQ.
Features:
  - Batched vLLM chat template execution (llm.chat) in chunks of 20
  - Claims-listing Faithfulness + Completeness evaluation
  - Resumption from existing judge_outputs.jsonl
  - Accurate judge_error flagging
  - GPU memory optimization with dtype="half"
"""

import json
import os
import re
from vllm import LLM, SamplingParams

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct-AWQ"
INPUT_FILE = "judge_inputs.jsonl"
OUTPUT_FILE = "judge_outputs.jsonl"
BATCH_SIZE = 20

FAITHFULNESS_PROMPT = """
Context:
{context}

Answer:
{answer}

Instructions:
1. List the key factual claims made in the Answer.
2. For each claim, check if it is supported by the Provided Context (1 for supported, 0 for unsupported).
3. Compute faithfulness = (supported_claims) / (total_claims). If no claims, return 1.0.

Return ONLY valid JSON matching this schema:
{{
  "claims": ["claim 1", "claim 2"],
  "supported_claims": 2,
  "total_claims": 2,
  "faithfulness": 1.0
}}
"""

COMPLETENESS_PROMPT = """
Question:
{question}

Answer:
{answer}

Instructions:
Does the answer address every part of the question?
Return 1 if completely answered, or 0 if incomplete/missing parts.

Return ONLY valid JSON matching this schema:
{{
  "completeness": 1,
  "reason": "Brief explanation"
}}
"""

def parse_json_defensive(raw_text):
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\\n?", "", cleaned)
        cleaned = re.sub(r"\\n?```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\\{.*\\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None

def main():
    print("=" * 60)
    print("KAGGLE VLLM JUDGE RUNNER")
    print("=" * 60)

    # 1. Resume check
    evaluated_ids = set()
    existing_outputs = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line.strip())
                    evaluated_ids.add(item["id"])
                    existing_outputs.append(item)
        print(f"✓ Resuming run: skipped {len(evaluated_ids)} already evaluated judge items.")

    # 2. Read inputs
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    records = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line.strip())
                if item["id"] not in evaluated_ids:
                    records.append(item)

    print(f"Total remaining items to evaluate: {len(records)}")

    if not records:
        print("✓ All items already evaluated!")
        return

    # 3. Initialize vLLM with chat template support and dtype='half'
    print(f"Loading vLLM model: {MODEL_NAME}...")
    llm = LLM(model=MODEL_NAME, dtype="half", max_model_len=4096, trust_remote_code=True)
    sampling_params = SamplingParams(temperature=0.0, max_tokens=300)

    all_outputs = list(existing_outputs)

    # 4. Process in batches using llm.chat
    for i in range(0, len(records), BATCH_SIZE):
        chunk = records[i:i + BATCH_SIZE]
        print(f"Processing batch {i + 1} - {min(i + BATCH_SIZE, len(records))} of {len(records)}...")

        # Build chat message batches for Faithfulness and Completeness
        f_chats = []
        c_chats = []

        for item in chunk:
            ctx_raw = item.get("retrieved_context")
            ctx_str = json.dumps(ctx_raw, ensure_ascii=False) if isinstance(ctx_raw, (dict, list)) else str(ctx_raw or "")
            ctx_plain = ctx_str[:3000]
            ans_str = str(item.get("answer") or "")
            q_str = str(item.get("question") or "")

            f_chats.append([
                {"role": "system", "content": "You are a precise evaluation judge. Return valid JSON only."},
                {"role": "user", "content": FAITHFULNESS_PROMPT.format(context=ctx_plain, answer=ans_str)}
            ])

            c_chats.append([
                {"role": "system", "content": "You are a precise evaluation judge. Return valid JSON only."},
                {"role": "user", "content": COMPLETENESS_PROMPT.format(question=q_str, answer=ans_str)}
            ])

        # Execute batched generation using Qwen's chat template
        f_results = llm.chat(f_chats, sampling_params)
        c_results = llm.chat(c_chats, sampling_params)

        for idx, item in enumerate(chunk):
            f_text = f_results[idx].outputs[0].text
            c_text = c_results[idx].outputs[0].text

            f_json = parse_json_defensive(f_text)
            c_json = parse_json_defensive(c_text)

            # Accurate judge_error calculation
            judge_error = (f_json is None or c_json is None)

            f_score = f_json.get("faithfulness", 0.0) if f_json else 0.0
            c_score = c_json.get("completeness", 0) if c_json else 0
            c_reason = c_json.get("reason", "") if c_json else "Parse error"

            item_res = {
                "id": item["id"],
                "judge_error": judge_error,
                "faithfulness": round(f_score, 4),
                "completeness": c_score,
                "completeness_reason": c_reason,
                "raw_faithfulness": f_json,
                "raw_completeness": c_json
            }
            all_outputs.append(item_res)

        # Checkpoint outputs line by line
        with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
            for out_item in all_outputs:
                out_f.write(json.dumps(out_item, ensure_ascii=False) + "\\n")
        print(f"  ✓ Checkpointed {len(all_outputs)} total outputs to {OUTPUT_FILE}")

    print("\\n" + "=" * 60)
    print(f"✓ KAGGLE LLM JUDGE COMPLETED! Saved to {OUTPUT_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    main()
'''

    with open(notebook_path, "w", encoding="utf-8") as f:
        f.write(notebook_script)

    return jsonl_path, notebook_path


def import_judge_outputs(run_dir: str) -> Dict[str, Dict[str, Any]]:
    """Import judge scores from judge_outputs.jsonl into a dictionary keyed by test case ID."""
    outputs_path = os.path.join(run_dir, "judge_outputs.jsonl")
    if not os.path.exists(outputs_path):
        raise FileNotFoundError(f"Judge output file not found at: {outputs_path}")

    judge_dict = {}
    with open(outputs_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line.strip())
                judge_dict[item["id"]] = item
    return judge_dict
