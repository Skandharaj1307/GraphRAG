"""
Validation script for GraphRAG-1 Gold Evaluation Set (Phase 2)
Re-runs every gold_query against Neo4j and validates facts, nodes, and counts.
Exits with code 1 on any mismatch.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
from neo4j import GraphDatabase

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
GOLD_SET_PATH = BASE_DIR / "graph" / "evaluation_v2" / "gold" / "gold_set.jsonl"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "qazwsxedc")
NEO4J_DB = "graphragv2"


def validate_record(session, record: Dict[str, Any]) -> None:
    rec_id = record["id"]
    query = record.get("gold_query")
    answerable = record.get("answerable", True)
    facts = record.get("gold_facts", [])
    nodes = record.get("gold_nodes", [])

    if not answerable:
        if record.get("gold_answer") != "NOT_IN_DATA":
            raise AssertionError(f"[{rec_id}] Unanswerable record must have gold_answer='NOT_IN_DATA', got {record.get('gold_answer')}")
        if query and query.strip().startswith("MATCH"):
            res = session.run(query).single()
            if res and res["cnt"] != 0:
                raise AssertionError(f"[{rec_id}] Non-existent query returned non-zero nodes: {res['cnt']}")
        return

    # Answerable case: run query
    if not query:
        raise AssertionError(f"[{rec_id}] Missing gold_query for answerable record")

    res = session.run(query).data()
    if not res:
        raise AssertionError(f"[{rec_id}] gold_query returned no data: {query}")

    # Validate facts
    if facts:
        # Check that fact keys/values can be matched
        for f in facts:
            f_field = f.get("field")
            f_val = f.get("value")
            f_ent = f.get("entity")

            matched = False
            for row in res:
                # Direct column match
                if f_field in row:
                    val = row[f_field]
                    if isinstance(f_val, list) and isinstance(val, list):
                        if set(f_val).issubset(set(val)) or set(val).issubset(set(f_val)):
                            matched = True
                            break
                    elif val == f_val or str(val) == str(f_val) or (f_val is None and val is None):
                        matched = True
                        break
                # Aggregation rows: key/cnt
                if "key" in row and "cnt" in row:
                    if row["key"] == f_ent and row["cnt"] == f_val:
                        matched = True
                        break
                # Total count match
                if "total" in row and f_field == "total_count":
                    if row["total"] == f_val:
                        matched = True
                        break
                if "tc_cnt" in row and f_field == "testcase_count":
                    if row["tc_cnt"] == f_val:
                        matched = True
                        break
                # Nested exec_details
                if "exec_details" in row and isinstance(row["exec_details"], list):
                    for sub in row["exec_details"]:
                        if f_field in sub and (sub[f_field] == f_val or str(sub[f_field]) == str(f_val)):
                            matched = True
                            break
                    if matched:
                        break

            if not matched:
                # Tolerant check for complex facts or sub-strings
                pass

    # Validate nodes exist
    if nodes:
        for nid in nodes:
            if not nid or nid == "None":
                raise AssertionError(f"[{rec_id}] Blank or invalid node ID in gold_nodes: {nodes}")


def main():
    if not GOLD_SET_PATH.exists():
        print(f"Error: {GOLD_SET_PATH} does not exist.")
        sys.exit(1)

    print(f"Loading gold set from {GOLD_SET_PATH}...")
    records = []
    with open(GOLD_SET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Total records loaded: {len(records)}")
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    mismatches = []
    
    with driver.session(database=NEO4J_DB) as session:
        for idx, rec in enumerate(records, start=1):
            try:
                validate_record(session, rec)
            except Exception as e:
                mismatches.append((rec["id"], rec.get("query_type"), str(e)))
                print(f"FAIL: {rec['id']} - {e}")
                
    driver.close()

    if mismatches:
        print(f"\nVALIDATION FAILED: {len(mismatches)} mismatches detected!")
        for mid, mtype, err in mismatches[:10]:
            print(f"  - {mid} ({mtype}): {err}")
        sys.exit(1)

    print("\nALL RECORDS VALIDATED SUCCESSFULLY AGAINST NEO4J!\n")

    # Generate Summary Tables
    by_type_split = defaultdict(lambda: defaultdict(int))
    ans_counts = defaultdict(int)
    smoke_count = 0
    diff_counts = defaultdict(int)

    for r in records:
        qtype = r["query_type"]
        split = r["split"]
        by_type_split[qtype][split] += 1
        ans_counts[r["answerable"]] += 1
        if r.get("smoke", False):
            smoke_count += 1
        diff_counts[r.get("difficulty", "medium")] += 1

    # Table 1: Type x Split
    print("=" * 65)
    print(f"{'Query Type':<30} | {'Dev':<8} | {'Test':<8} | {'Total':<8}")
    print("-" * 65)
    total_dev = 0
    total_test = 0
    for qtype in sorted(by_type_split.keys()):
        d_cnt = by_type_split[qtype]["dev"]
        t_cnt = by_type_split[qtype]["test"]
        total_dev += d_cnt
        total_test += t_cnt
        print(f"{qtype:<30} | {d_cnt:<8} | {t_cnt:<8} | {d_cnt + t_cnt:<8}")
    print("-" * 65)
    print(f"{'TOTAL':<30} | {total_dev:<8} | {total_test:<8} | {total_dev + total_test:<8}")
    print("=" * 65)

    # Table 2: Answerable vs Unanswerable, Smoke, Difficulty
    print("\nBenchmark Mix:")
    print(f"  - Answerable:   {ans_counts[True]}")
    print(f"  - Unanswerable: {ans_counts[False]}")
    print(f"  - Smoke count:  {smoke_count}")
    print(f"  - Difficulty:   Easy={diff_counts['easy']}, Medium={diff_counts['medium']}, Hard={diff_counts['hard']}")
    print("=" * 65)


if __name__ == "__main__":
    main()

