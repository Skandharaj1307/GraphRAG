import json
from collections import defaultdict

with open("graph/evaluation_v2/gold/gold_set.jsonl", "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

by_type = defaultdict(list)
for r in records:
    by_type[r["query_type"]].append(r)

sampled = []
# Pick 1-2 from each type to get 15 records
for t, items in sorted(by_type.items()):
    sampled.append(items[0])
    if len(items) > 1 and len(sampled) < 15:
        sampled.append(items[1])

print(f"Sampled {len(sampled)} records across {len(by_type)} query types:\n")
for r in sampled[:15]:
    print("=" * 70)
    print(f"[{r['id']}] Type: {r['query_type']} | Split: {r['split']} | Smoke: {r['smoke']} | Diff: {r['difficulty']}")
    print(f"Q: {r['question']}")
    print(f"Intent: {r['expected_intent']} | Answerable: {r['answerable']}")
    print(f"IDs: {r['expected_ids']}")
    print(f"Gold Answer: {r['gold_answer']}")
    print(f"Gold Query:  {r['gold_query']}")

