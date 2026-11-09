"""
Standalone Kaggle/GPU LLM Judge script using vLLM & Qwen/Qwen2.5-7B-Instruct-AWQ.
Run this on Kaggle GPU instance to evaluate judge scores offline for free!
"""
import json
import os
import re

# Install vLLM if needed: pip install vllm

from vllm import LLM, SamplingParams

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct-AWQ"
INPUT_FILE = "judge_inputs.jsonl"
OUTPUT_FILE = "judge_outputs.jsonl"

FAITHFULNESS_PROMPT = """
Context:
{context}

Answer:
{answer}

Check if the generated Answer is faithful to the Provided Context. Return ONLY valid JSON:
{{"faithfulness": 1.0}}
"""

COMPLETENESS_PROMPT = """
Question:
{question}

Answer:
{answer}

Check if the Answer completely addresses the user's Question. Return ONLY valid JSON:
{{"completeness": 1, "reason": "Reason text"}}
"""

def parse_json_defensive(raw_text):
    if not raw_text: return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try: return json.loads(match.group(0))
            except: pass
    return None

def main():
    print(f"Loading model {MODEL_NAME}...")
    llm = LLM(model=MODEL_NAME, max_model_len=4096)
    sampling_params = SamplingParams(temperature=0.0, max_tokens=256)

    records = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))

    print(f"Processing {len(records)} items...")
    outputs = []

    for i, item in enumerate(records):
        ctx_str = json.dumps(item.get("retrieved_context") or "")[:2500]
        ans_str = str(item.get("answer") or "")
        q_str = str(item.get("question") or "")

        f_prompt = FAITHFULNESS_PROMPT.format(context=ctx_str, answer=ans_str)
        c_prompt = COMPLETENESS_PROMPT.format(question=q_str, answer=ans_str)

        f_out = llm.generate([f_prompt], sampling_params)[0].outputs[0].text
        c_out = llm.generate([c_prompt], sampling_params)[0].outputs[0].text

        f_json = parse_json_defensive(f_out) or {"faithfulness": 0.0}
        c_json = parse_json_defensive(c_out) or {"completeness": 0, "reason": "Parse error"}

        item_res = {
            "id": item["id"],
            "judge_error": (f_json is None or c_json is None),
            "faithfulness": f_json.get("faithfulness", 0.0),
            "completeness": c_json.get("completeness", 0),
            "completeness_reason": c_json.get("reason", "")
        }
        outputs.append(item_res)

        # Checkpoint every 20 items
        if (i + 1) % 20 == 0 or (i + 1) == len(records):
            with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
                for out_item in outputs:
                    out_f.write(json.dumps(out_item, ensure_ascii=False) + "\n")
            print(f"Saved checkpoint: {i + 1}/{len(records)}")

    print(f"✓ Completed judge evaluation. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
