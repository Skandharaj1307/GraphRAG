import json

with open("graph/evaluation_v2/runs/20261109_001434/results.jsonl", "r", encoding="utf-8") as f:
    results = [json.loads(line) for line in f]

below_1 = [r for r in results if r["metrics"].get("aggregation_exact", 1.0) < 1.0]
print(f"Total cases below 1.0: {len(below_1)} out of {len(results)}\n")

for r in below_1:
    print("=" * 70)
    print(f"ID: {r['id']} | Question: {r['question']}")
    m = r["metrics"]
    print(f"Metrics: exact={m.get('aggregation_exact')}, pairs={m.get('agg_pairs_match')}, order={m.get('agg_order_match')}, filters={m.get('agg_filters_match')}")
    print(f"Expected Group By: {r['router_output'].get('group_by_field')} | Filters: {r['router_output'].get('filters')}")
    print(f"Gold Facts: {r.get('gold_facts')}")
    print(f"Gold Query: {r.get('gold_query')}")
    agg = r["retrieved_context"].get("aggregates")
    filt = r["retrieved_context"].get("filter_results")
    if agg:
        print(f"Retrieved Aggregates: template={agg.get('template')}, total={agg.get('total')}, filters_applied={agg.get('filters_applied')}")
        print(f"Retrieved Rows: {agg.get('rows')[:6]}")
    if filt:
        print(f"Retrieved Filter Results: total={filt.get('total')}, filters={filt.get('filters_applied') or filt.get('filters')}")

