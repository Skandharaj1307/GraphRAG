import json
from collections import defaultdict

with open("graph/evaluation_v2/gold/gold_set.jsonl", "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

by_type = defaultdict(list)
for r in records:
    by_type[r["query_type"]].append(r)

sampled = []
# Ensure each type has at least 1-2
types_order = [
    "id_lookup", "defect_to_testcase", "testcase_to_defects",
    "execution_context", "aggregation", "multi_condition_filter",
    "semantic", "unstructured_logs", "requirements",
    "unanswerable", "adversarial"
]
for t in types_order:
    sampled.append(by_type[t][0])

# add second items until 15
for t in ["id_lookup", "defect_to_testcase", "aggregation", "unstructured_logs"]:
    if len(sampled) < 15 and len(by_type[t]) > 1:
        sampled.append(by_type[t][1])

for idx, r in enumerate(sampled[:15], 1):
    print(f"### Record {idx}: [{r['id']}] `{r['query_type']}` — Split: `{r['split']}` | Smoke: `{r['smoke']}` | Difficulty: `{r['difficulty']}`")
    print(f"- **Question**: {r['question']}")
    print(f"- **Expected Intent**: `{r['expected_intent']}` | **Answerable**: `{r['answerable']}`")
    print(f"- **Target IDs**: `{json.dumps(r['expected_ids'])}`")
    print(f"- **Gold Answer**: {r['gold_answer']}")
    print(f"- **Gold Query**: `{r['gold_query']}`\n")

