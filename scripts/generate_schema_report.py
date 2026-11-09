import os
import json
import glob
import pandas as pd
from neo4j import GraphDatabase
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BASE_DIR / "graph" / "evaluation_v2" / "schema_report.md"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "qazwsxedc"))

report_lines = []
report_lines.append("# GraphRAG Schema and Dataset Report (Source of Truth)")
report_lines.append("")

# 1. Neo4j Schema
report_lines.append("## 1. Neo4j Graph Schema (`graphragv2`)")
report_lines.append("")
with driver.session(database="graphragv2") as session:
    labels_res = session.run("CALL db.labels() YIELD label RETURN label").values()
    labels = sorted([r[0] for r in labels_res])
    
    report_lines.append("### Node Labels and Counts")
    report_lines.append("| Label | Count | Property Count | Key Properties & 2 Examples |")
    report_lines.append("| :--- | :---: | :---: | :--- |")
    
    for lbl in labels:
        count = session.run(f"MATCH (n:`{lbl}`) RETURN count(n)").single()[0]
        sample_nodes = session.run(f"MATCH (n:`{lbl}`) RETURN properties(n) as props LIMIT 2").data()
        if sample_nodes:
            all_keys = set()
            for row in sample_nodes:
                all_keys.update(row["props"].keys())
            # exclude big embedding arrays from markdown readability
            all_keys = sorted([k for k in all_keys if k != "embedding"])
            
            examples_list = []
            for k in all_keys:
                vals = [str(row["props"].get(k, ""))[:120] for row in sample_nodes if k in row["props"]]
                examples_list.append(f"`{k}`: {json.dumps(vals[:2])}")
            examples_str = "<br>".join(examples_list)
            prop_count = len(all_keys) + (1 if "embedding" in sample_nodes[0]["props"] else 0)
        else:
            prop_count = 0
            examples_str = "N/A"
            
        report_lines.append(f"| `{lbl}` | {count:,} | {prop_count} | {examples_str} |")
    
    report_lines.append("")
    report_lines.append("### Relationships (Type, Direction, and Count)")
    report_lines.append("| Relationship Pattern | Count | Description / Purpose |")
    report_lines.append("| :--- | :---: | :--- |")
    
    rel_query = """
    MATCH (a)-[r]->(b)
    WITH labels(a)[0] AS from_label, type(r) AS rel_type, labels(b)[0] AS to_label, count(r) AS count
    RETURN from_label, rel_type, to_label, count
    ORDER BY count DESC
    """
    rel_rows = session.run(rel_query).data()
    for row in rel_rows:
        pattern = f"(:{row['from_label']})-[:{row['rel_type']}]->(:{row['to_label']})"
        report_lines.append(f"| `{pattern}` | {row['count']:,} | Link between {row['from_label']} and {row['to_label']} |")

driver.close()

# 2. Structured CSVs
report_lines.append("")
report_lines.append("## 2. Structured Dataset (`dataset/structured/`)")
report_lines.append("| File Name | Row Count | Column Count | Columns |")
report_lines.append("| :--- | :---: | :---: | :--- |")

csv_files = sorted(glob.glob(str(BASE_DIR / "dataset" / "structured" / "*.csv")))
for csv_path in csv_files:
    fname = os.path.basename(csv_path)
    try:
        df = pd.read_csv(csv_path)
        cols_str = ", ".join([f"`{c}`" for c in df.columns])
        report_lines.append(f"| `{fname}` | {len(df):,} | {len(df.columns)} | {cols_str} |")
    except Exception as e:
        report_lines.append(f"| `{fname}` | Error | 0 | {e} |")

# 3. Unstructured Dataset
report_lines.append("")
report_lines.append("## 3. Unstructured Dataset (`dataset/unstructured/`)")

report_lines.append("### Failure Logs (`dataset/unstructured/failure_logs/`)")
log_files = sorted(glob.glob(str(BASE_DIR / "dataset" / "unstructured" / "failure_logs" / "*.txt")))
report_lines.append(f"- Total failure log text files: {len(log_files)}")
report_lines.append("| File Name | File Size (KB) | Graph Ingestion & Link |")
report_lines.append("| :--- | :---: | :--- |")
for lf in log_files:
    lf_name = os.path.basename(lf)
    size_kb = round(os.path.getsize(lf) / 1024, 2)
    report_lines.append(f"| `{lf_name}` | {size_kb} KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |")

report_lines.append("")
report_lines.append("### Screenshots OCR (`dataset/unstructured/screenshots/`)")
ocr_files = sorted(glob.glob(str(BASE_DIR / "dataset" / "unstructured" / "screenshots" / "*.json")))
report_lines.append(f"- Total screenshot OCR batch files: {len(ocr_files)}")
report_lines.append("| File Name | File Size (KB) | Graph Ingestion & Link |")
report_lines.append("| :--- | :---: | :--- |")
for of in ocr_files:
    of_name = os.path.basename(of)
    size_kb = round(os.path.getsize(of) / 1024, 2)
    report_lines.append(f"| `{of_name}` | {size_kb} KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |")

report_lines.append("")
report_lines.append("### SRS Document (`dataset/unstructured/srs/`)")
srs_path = BASE_DIR / "dataset" / "unstructured" / "srs" / "srs_document.pdf"
if srs_path.exists():
    size_mb = round(srs_path.stat().st_size / (1024 * 1024), 2)
    report_lines.append(f"- File: `{srs_path.name}` ({size_mb} MB, 769 pages)")
    report_lines.append("- Graph Ingestion: Parsed into `(:Requirement {id, name, text, section, source})` nodes and linked via `(:TestCase)-[:VERIFIES]->(:Requirement)`.")
else:
    report_lines.append("- File: Not found")

# 4. Query Router Intents
report_lines.append("")
report_lines.append("## 4. Query Router Intents & Function Mappings")
report_lines.append("Sourced directly from `graph/query_understanding.py` and `graph/retrieval_router.py`:")
report_lines.append("")
report_lines.append("| Router Intent | Target Entity / Route | Retrieval Function Called | Extracted Fields (IDs, Filters, Group By) |")
report_lines.append("| :--- | :--- | :--- | :--- |")
report_lines.append("| `defect_lookup` | `defect` (`neo4j`) | `get_full_defect_context(defect_id)` | IDs: `defect_ids`; Filters: None |")
report_lines.append("| `defect_multi_property` | `defect` (`neo4j`) | `get_full_defect_context(defect_id)` | IDs: `defect_ids`; Filters: None |")
report_lines.append("| `defect_to_testcase` | `defect` (`neo4j`) | `get_full_defect_context(defect_id)` (2-hop ego expansion) | IDs: `defect_ids`; Filters: None |")
report_lines.append("| `testcase_lookup` | `testcase` (`neo4j`) | `get_testcase_context(test_case_id)` | IDs: `test_case_ids`; Filters: None |")
report_lines.append("| `testcase_to_defects` | `testcase` (`neo4j`) | `get_testcase_context(test_case_id)` (2-hop ego expansion) | IDs: `test_case_ids`; Filters: None |")
report_lines.append("| `execution_context` / `execution_lookup` | `execution` (`neo4j`) | `get_execution_context(execution_id)` | IDs: `execution_ids`; Filters: None |")
report_lines.append("| `testcase_executions_summary` | `testcase` (`neo4j`) | `get_testcase_context(test_case_id)` or `get_execution_context` | IDs: `test_case_ids` / `execution_ids`; Filters: None |")
report_lines.append("| `screenshot_lookup` | `screenshot` / `defect` (`neo4j`) | `get_screenshot_context(screenshot_id)` or `get_full_defect_context(defect_id)` | IDs: `screenshot_ids` / `defect_ids`; Filters: None |")
report_lines.append("| `defect_analysis` / `group_by` / `aggregation` | `module` / `defect` (`neo4j`) | `aggregate_defects(group_by, filters)` | Group-by: `group_by_field` (`module`, `severity`, `status`, `build`, `tester`, `root_cause`); Filters: `module`, `severity`, `status`, etc. |")
report_lines.append("| `semantic_search` | `semantic` (`semantic`) | `search(query, k=...)` + Cross-Encoder reranker | IDs: None; Filters: None |")
report_lines.append("| `general_test_analysis` / `broad_summary` | `hybrid` / `lightrag` / `neo4j` | `route_query` -> `hybrid` or `neo4j` aggregation | IDs: None; Filters/Group-by as extracted |")
report_lines.append("| `unanswerable` | `neo4j` | Handled via ID lookup with empty graph results -> fallback refusal | Non-existent or missing IDs |")

# 5. Existing retrieval features
report_lines.append("")
report_lines.append("## 5. Existing Retrieval Features")
report_lines.append("1. **Multi-Hop Subgraph Expansion**: Bi-directional 2-hop traversals across `Defect` <-> `Execution` <-> `TestCase` <-> `Screenshot` with parameterized ego limits.")
report_lines.append("2. **Parametric Whitelisted Aggregation (`aggregate_defects`)**: Injects validated property filters (`module`, `severity`, `status`, `build`, `tester`, etc.) and group-by clauses safely into Cypher.")
report_lines.append("3. **Local Cross-Encoder Reranker**: `BAAI/bge-reranker-base` local reranker reranks the top 25 semantic embedding hits in `semantic_retriever.py`.")
report_lines.append("4. **Failure Log Retrieval**: `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` returns structured error logs (exception type, message, stack trace snippet) attached to execution contexts.")
report_lines.append("5. **Requirement Tracing**: `(:TestCase)-[:VERIFIES]->(:Requirement)` links test cases to SRS requirements sections.")

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines) + "\n")

print(f"Schema report written successfully to {OUTPUT_PATH}")
