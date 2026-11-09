import sys
import json
import random
from pathlib import Path
import pandas as pd

# Force UTF-8 stdout for Windows terminals
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# -----------------------------------------------------------------------------
# Configuration & Seed
# -----------------------------------------------------------------------------
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "qazwsxedc"

BASE_DIR = Path(__file__).resolve().parent.parent
TESTCASES_FILE = BASE_DIR / "dataset" / "structured" / "testcases.csv"
EXECUTIONS_FILE = BASE_DIR / "dataset" / "structured" / "test_execution.csv"
DEFECTS_FILE = BASE_DIR / "dataset" / "structured" / "defects.csv"
SCREENSHOT_DIR = BASE_DIR / "dataset" / "unstructured" / "screenshots"
OUTPUT_FILE = BASE_DIR / "graph" / "testset.json"


def fetch_data_from_neo4j():
    """Fetch structured records and aggregations from Neo4j."""
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("RETURN 1 AS test")

    def run_cypher(query, **kwargs):
        with driver.session() as session:
            result = session.run(query, **kwargs)
            return [record.data() for record in result]

    print("[INFO] Successfully connected to Neo4j database.")

    # Existing IDs
    all_defects = {r["id"] for r in run_cypher("MATCH (d:Defect) RETURN d.defect_id AS id")}
    all_tcs = {r["id"] for r in run_cypher("MATCH (t:TestCase) RETURN t.test_case_id AS id")}
    all_execs = {r["id"] for r in run_cypher("MATCH (e:Execution) RETURN e.execution_id AS id")}

    # 1. Defect lookups
    defects = run_cypher("""
        MATCH (d:Defect)
        WHERE d.root_cause IS NOT NULL AND trim(d.root_cause) <> ''
        RETURN d.defect_id AS defect_id, d.title AS title, d.root_cause AS root_cause,
               d.severity AS severity, d.status AS status, d.assigned_to AS assigned_to,
               d.priority AS priority, d.module AS module
    """)

    # 2. Defect -> Execution -> TestCase
    defect_traversals = run_cypher("""
        MATCH (d:Defect)<-[:FOUND_DEFECT]-(e:Execution)<-[:HAS_EXECUTION]-(t:TestCase)
        RETURN d.defect_id AS defect_id, e.execution_id AS execution_id, e.tester AS tester,
               e.build_number AS build_number, t.test_case_id AS test_case_id, t.module AS module
    """)

    # 3. TestCase -> Defects (set)
    testcase_defects = run_cypher("""
        MATCH (t:TestCase)-[:HAS_EXECUTION]->(e:Execution)-[:FOUND_DEFECT]->(d:Defect)
        WITH t, collect(DISTINCT d.defect_id) AS defect_ids
        WHERE size(defect_ids) > 0
        RETURN t.test_case_id AS test_case_id, defect_ids
    """)

    # 4. TestCase Executions summary (PREFER testcases with failed_executions > 0)
    testcase_executions = run_cypher("""
        MATCH (t:TestCase)-[:HAS_EXECUTION]->(e:Execution)
        WITH t, count(e) AS total_executions, 
             sum(CASE WHEN toUpper(e.status) IN ['FAIL', 'FAILED'] THEN 1 ELSE 0 END) AS failed_executions
        RETURN t.test_case_id AS test_case_id, total_executions, failed_executions
        ORDER BY failed_executions DESC, total_executions DESC
    """)

    # 5. Execution context
    executions = run_cypher("""
        MATCH (e:Execution)
        WHERE e.environment IS NOT NULL AND e.browser IS NOT NULL
        RETURN e.execution_id AS execution_id, e.environment AS environment, 
               e.browser AS browser, e.operating_system AS operating_system, 
               e.tester AS tester, e.status AS status, e.test_case_id AS test_case_id
    """)

    # 6. Screenshots with NON-EMPTY error/warning messages
    bug_screenshots = run_cypher("""
        MATCH (d:Defect)-[:HAS_SCREENSHOT]->(s:Screenshot)
        WHERE s.error_messages IS NOT NULL AND size(s.error_messages) > 0
        RETURN d.defect_id AS defect_id, s.screenshot_id AS screenshot_id, 
               s.screen_name AS screen_name, s.error_messages AS error_messages, 
               s.warning_messages AS warning_messages
    """)
    # Filter out empty string elements in python
    filtered_bug_sc = []
    for sc in bug_screenshots:
        errs = [m for m in sc.get("error_messages", []) if str(m).strip() != ""]
        warns = [m for m in sc.get("warning_messages", []) if str(m).strip() != ""]
        if errs or warns:
            sc["error_messages"] = errs
            sc["warning_messages"] = warns
            filtered_bug_sc.append(sc)

    tc_screenshots = run_cypher("""
        MATCH (t:TestCase)-[:HAS_SCREENSHOT]->(s:Screenshot)
        WHERE s.error_messages IS NOT NULL AND size(s.error_messages) > 0
        RETURN t.test_case_id AS test_case_id, s.screenshot_id AS screenshot_id, 
               s.screen_name AS screen_name, s.error_messages AS error_messages, 
               s.warning_messages AS warning_messages
    """)
    filtered_tc_sc = []
    for sc in tc_screenshots:
        errs = [m for m in sc.get("error_messages", []) if str(m).strip() != ""]
        warns = [m for m in sc.get("warning_messages", []) if str(m).strip() != ""]
        if errs or warns:
            sc["error_messages"] = errs
            sc["warning_messages"] = warns
            filtered_tc_sc.append(sc)

    # 7. Aggregations for 20 Genuinely Unique Broad Questions
    broad_golds = {
        "top_defect_modules": run_cypher("MATCH (d:Defect) WHERE toUpper(d.severity) IN ['CRITICAL','HIGH','BLOCKER'] RETURN d.module AS module, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "top_root_causes": run_cypher("MATCH (d:Defect) WHERE d.root_cause IS NOT NULL AND trim(d.root_cause) <> '' RETURN d.root_cause AS root_cause, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "regression_modules": run_cypher("MATCH (d:Defect) WHERE toUpper(toString(d.regression)) IN ['YES','TRUE','1'] RETURN d.module AS module, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "severity_dist": run_cypher("MATCH (d:Defect) WHERE d.severity IS NOT NULL RETURN d.severity AS severity, count(*) AS count ORDER BY count DESC"),
        "priority_dist": run_cypher("MATCH (d:Defect) WHERE d.priority IS NOT NULL RETURN d.priority AS priority, count(*) AS count ORDER BY count DESC"),
        "failed_environments": run_cypher("MATCH (e:Execution) WHERE toUpper(e.status) IN ['FAIL','FAILED'] RETURN e.environment AS env, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "failed_os": run_cypher("MATCH (e:Execution) WHERE toUpper(e.status) IN ['FAIL','FAILED'] RETURN e.operating_system AS os, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "failed_browsers": run_cypher("MATCH (e:Execution) WHERE toUpper(e.status) IN ['FAIL','FAILED'] RETURN e.browser AS browser, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "top_testers": run_cypher("MATCH (e:Execution) RETURN e.tester AS tester, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "top_bug_types": run_cypher("MATCH (d:Defect) WHERE d.bug_type IS NOT NULL RETURN d.bug_type AS bug_type, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "top_tc_components": run_cypher("MATCH (t:TestCase) WHERE t.component IS NOT NULL RETURN t.component AS component, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "top_epics": run_cypher("MATCH (t:TestCase) WHERE t.epic IS NOT NULL RETURN t.epic AS epic, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "defect_status_dist": run_cypher("MATCH (d:Defect) RETURN d.status AS status, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "automation_frameworks": run_cypher("MATCH (t:TestCase) WHERE t.automation_framework IS NOT NULL RETURN t.automation_framework AS framework, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "top_build_defects": run_cypher("MATCH (d:Defect) WHERE d.found_in_build IS NOT NULL RETURN d.found_in_build AS build, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "execution_frequencies": run_cypher("MATCH (t:TestCase) WHERE t.execution_frequency IS NOT NULL RETURN t.execution_frequency AS frequency, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "automated_modules": run_cypher("MATCH (t:TestCase) WHERE toUpper(toString(t.automation_status)) IN ['AUTOMATED','YES'] RETURN t.module AS module, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "manual_modules": run_cypher("MATCH (t:TestCase) WHERE toUpper(toString(t.automation_status)) IN ['MANUAL','NO','NOT AUTOMATED'] RETURN t.module AS module, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "fix_versions": run_cypher("MATCH (d:Defect) WHERE d.fix_version IS NOT NULL RETURN d.fix_version AS version, count(*) AS count ORDER BY count DESC LIMIT 5"),
        "screenshot_screens": run_cypher("MATCH (s:Screenshot) WHERE s.screen_name IS NOT NULL AND s.screen_name <> '' RETURN s.screen_name AS screen, count(*) AS count ORDER BY count DESC LIMIT 5"),
    }

    driver.close()
    return {
        "all_defects": all_defects,
        "all_tcs": all_tcs,
        "all_execs": all_execs,
        "defects": defects,
        "defect_traversals": defect_traversals,
        "testcase_defects": testcase_defects,
        "testcase_executions": testcase_executions,
        "executions": executions,
        "bug_screenshots": filtered_bug_sc,
        "tc_screenshots": filtered_tc_sc,
        "broad_golds": broad_golds
    }


def fetch_data_from_csv():
    """Fallback: Compute gold datasets directly from local CSV files."""
    print("! Neo4j not reachable. Reading directly from CSV files...")

    testcases_df = pd.read_csv(TESTCASES_FILE)
    executions_df = pd.read_csv(EXECUTIONS_FILE)
    defects_df = pd.read_csv(DEFECTS_FILE)

    all_defects = set(defects_df["defect_id"].dropna().astype(str))
    all_tcs = set(testcases_df["test_case_id"].dropna().astype(str))
    all_execs = set(executions_df["execution_id"].dropna().astype(str))

    valid_defects = defects_df.dropna(subset=["root_cause"])
    defects = valid_defects.to_dict("records")

    merged = defects_df.merge(executions_df, left_on="linked_execution", right_on="execution_id", suffixes=('', '_ex'))
    merged = merged.merge(testcases_df, left_on="linked_test_case", right_on="test_case_id", suffixes=('', '_tc'))
    defect_traversals = merged.to_dict("records")

    tc_def = defects_df.groupby("linked_test_case")["defect_id"].unique().reset_index()
    testcase_defects = [
        {"test_case_id": row["linked_test_case"], "defect_ids": list(row["defect_id"])}
        for _, row in tc_def.iterrows()
    ]

    ex_summary = executions_df.groupby("test_case_id").agg(
        total_executions=("execution_id", "count"),
        failed_executions=("status", lambda s: sum(s.astype(str).str.upper().isin(["FAIL", "FAILED"])))
    ).reset_index()
    # Sort so testcases with failures come first
    ex_summary = ex_summary.sort_values(by=["failed_executions", "total_executions"], ascending=False)
    testcase_executions = ex_summary.to_dict("records")

    executions = executions_df.to_dict("records")

    # Screenshots from JSON with non-empty error/warning messages
    filtered_bug_sc = []
    filtered_tc_sc = []
    for json_file in sorted(SCREENSHOT_DIR.glob("ocr_batch_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            records = json.load(f)
            for idx, rec in enumerate(records):
                errs = [m for m in (rec.get("error_messages") or []) if str(m).strip() != ""]
                warns = [m for m in (rec.get("warning_messages") or []) if str(m).strip() != ""]
                if not errs and not warns:
                    continue
                sc_id = f"SCR-{json_file.stem}-{idx:04d}"
                entry = {
                    "screenshot_id": sc_id,
                    "screen_name": rec.get("screen_name", ""),
                    "error_messages": errs,
                    "warning_messages": warns,
                }
                if rec.get("bug_id"):
                    entry["defect_id"] = rec["bug_id"]
                    filtered_bug_sc.append(entry)
                if rec.get("test_case_id"):
                    entry["test_case_id"] = rec["test_case_id"]
                    filtered_tc_sc.append(entry)

    # Aggregations for 20 Genuinely Unique Broad Questions
    high_sev = defects_df[defects_df["severity"].astype(str).str.upper().isin(["CRITICAL", "HIGH", "BLOCKER"])]
    failed_ex = executions_df[executions_df["status"].astype(str).str.upper().isin(["FAIL", "FAILED"])]
    regr = defects_df[defects_df["regression"].astype(str).str.upper().isin(["YES", "TRUE", "1"])]

    broad_golds = {
        "top_defect_modules": high_sev.groupby("module").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "top_root_causes": defects_df.groupby("root_cause").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "regression_modules": regr.groupby("module").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "severity_dist": defects_df.groupby("severity").size().reset_index(name="count").sort_values(by="count", ascending=False).to_dict("records"),
        "priority_dist": defects_df.groupby("priority").size().reset_index(name="count").sort_values(by="count", ascending=False).to_dict("records"),
        "failed_environments": failed_ex.groupby("environment").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "failed_os": failed_ex.groupby("operating_system").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "failed_browsers": failed_ex.groupby("browser").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "top_testers": executions_df.groupby("tester").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "top_bug_types": defects_df.groupby("bug_type").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "top_tc_components": testcases_df.groupby("component").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "top_epics": testcases_df.groupby("epic").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "defect_status_dist": defects_df.groupby("status").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "automation_frameworks": testcases_df.groupby("automation_framework").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "top_build_defects": defects_df.groupby("found_in_build").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "execution_frequencies": testcases_df.groupby("execution_frequency").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "automated_modules": testcases_df[testcases_df["automation_status"].astype(str).str.upper().isin(["AUTOMATED","YES"])].groupby("module").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "manual_modules": testcases_df[testcases_df["automation_status"].astype(str).str.upper().isin(["MANUAL","NO","NOT AUTOMATED"])].groupby("module").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "fix_versions": defects_df.groupby("fix_version").size().reset_index(name="count").sort_values(by="count", ascending=False).head(5).to_dict("records"),
        "screenshot_screens": [],
    }

    return {
        "all_defects": all_defects,
        "all_tcs": all_tcs,
        "all_execs": all_execs,
        "defects": defects,
        "defect_traversals": defect_traversals,
        "testcase_defects": testcase_defects,
        "testcase_executions": testcase_executions,
        "executions": executions,
        "bug_screenshots": filtered_bug_sc,
        "tc_screenshots": filtered_tc_sc,
        "broad_golds": broad_golds
    }


def generate_testset():
    print("=" * 60)
    print("GENERATING GRAPH RAG EVALUATION TESTSET")
    print("=" * 60)

    try:
        data = fetch_data_from_neo4j()
    except Exception as e:
        print(f"Neo4j connection error: {e}")
        data = fetch_data_from_csv()

    tests = []

    # 1. Defect Root Cause Lookup (25 items)
    defect_sample = random.sample(data["defects"], min(25, len(data["defects"])))
    for d in defect_sample:
        did = d["defect_id"]
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "defect_lookup",
            "hops": 0,
            "question": f"What is the root cause of defect {did}?",
            "expected_entities": {"test_case_ids": [], "execution_ids": [], "defect_ids": [did]},
            "expected_intent": "defect_lookup",
            "expected_route": "neo4j",
            "gold_answer": {
                "defect_id": did,
                "root_cause": str(d.get("root_cause", "")).strip(),
                "title": str(d.get("title", "")).strip()
            }
        })

    # 2. Defect Multi-Property Lookup (25 items)
    rem_defects = [d for d in data["defects"] if d not in defect_sample]
    defect_multi_sample = random.sample(rem_defects, min(25, len(rem_defects))) if rem_defects else defect_sample
    for d in defect_multi_sample:
        did = d["defect_id"]
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "defect_multi_property",
            "hops": 0,
            "question": f"What are the severity, priority, status, and assigned owner for defect {did}?",
            "expected_entities": {"test_case_ids": [], "execution_ids": [], "defect_ids": [did]},
            "expected_intent": "defect_lookup",
            "expected_route": "neo4j",
            "gold_answer": {
                "defect_id": did,
                "severity": str(d.get("severity", "")),
                "priority": str(d.get("priority", "")),
                "status": str(d.get("status", "")),
                "assigned_to": str(d.get("assigned_to", ""))
            }
        })

    # 3. Defect -> Execution -> TestCase Multi-hop (25 items - no question leakage!)
    traversal_sample = random.sample(data["defect_traversals"], min(25, len(data["defect_traversals"])))
    for r in traversal_sample:
        did = r["defect_id"]
        tcase = r["test_case_id"]
        build = r.get("build_number", "")
        tester = r.get("tester", "")
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "defect_to_testcase",
            "hops": 2,
            "question": f"Which test case produced defect {did}, and who executed the run in which build?",
            "expected_entities": {"test_case_ids": [], "execution_ids": [], "defect_ids": [did]},
            "expected_intent": "defect_lookup",
            "expected_route": "neo4j",
            "gold_answer": {
                "defect_id": did,
                "test_case_id": tcase,
                "build_number": str(build),
                "tester": str(tester)
            }
        })

    # 4. TestCase -> Defects Set Lookup (25 items)
    tc_def_sample = random.sample(data["testcase_defects"], min(25, len(data["testcase_defects"])))
    for r in tc_def_sample:
        tcase = r["test_case_id"]
        defects_list = r["defect_ids"]
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "testcase_to_defects",
            "hops": 2,
            "question": f"List all defect IDs found during execution of test case {tcase}.",
            "expected_entities": {"test_case_ids": [tcase], "execution_ids": [], "defect_ids": []},
            "expected_intent": "testcase_execution_analysis",
            "expected_route": "neo4j",
            "gold_answer": {
                "test_case_id": tcase,
                "defect_ids": list(defects_list)
            }
        })

    # 5. TestCase Executions Summary (25 items - Guaranteed failed_executions > 0 where available)
    all_tc_ex = data["testcase_executions"]
    tc_ex_with_failures = [r for r in all_tc_ex if r["failed_executions"] > 0]
    tc_ex_zero_failures = [r for r in all_tc_ex if r["failed_executions"] == 0]

    needed = 25
    tc_ex_sample = random.sample(tc_ex_with_failures, min(needed, len(tc_ex_with_failures)))
    if len(tc_ex_sample) < needed:
        remainder = needed - len(tc_ex_sample)
        tc_ex_sample.extend(random.sample(tc_ex_zero_failures, min(remainder, len(tc_ex_zero_failures))))

    for r in tc_ex_sample:
        tcase = r["test_case_id"]
        total_ex = r["total_executions"]
        failed_ex = r["failed_executions"]
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "testcase_executions_summary",
            "hops": 1,
            "question": f"How many times has test case {tcase} been executed, and how many runs failed?",
            "expected_entities": {"test_case_ids": [tcase], "execution_ids": [], "defect_ids": []},
            "expected_intent": "testcase_execution_analysis",
            "expected_route": "neo4j",
            "gold_answer": {
                "test_case_id": tcase,
                "total_executions": int(total_ex),
                "failed_executions": int(failed_ex)
            }
        })

    # 6. Execution Context Lookup (25 items)
    exec_sample = random.sample(data["executions"], min(25, len(data["executions"])))
    for e in exec_sample:
        exec_id = e["execution_id"]
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "execution_context",
            "hops": 0,
            "question": f"What environment, browser, and operating system was test execution {exec_id} run in?",
            "expected_entities": {"test_case_ids": [], "execution_ids": [exec_id], "defect_ids": []},
            "expected_intent": "execution_lookup",
            "expected_route": "neo4j",
            "gold_answer": {
                "execution_id": exec_id,
                "environment": str(e.get("environment", "")),
                "browser": str(e.get("browser", "")),
                "operating_system": str(e.get("operating_system", "")),
                "status": str(e.get("status", ""))
            }
        })

    # 7. Screenshot Details via Defect or TestCase (20 items - GUARANTEED non-empty messages!)
    bug_sc_pool = data["bug_screenshots"]
    bug_sc_sample = random.sample(bug_sc_pool, min(10, len(bug_sc_pool))) if bug_sc_pool else []
    for s in bug_sc_sample:
        did = s["defect_id"]
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "screenshot_lookup",
            "hops": 1,
            "question": f"What error or warning messages appear in the screenshot captured for defect {did}?",
            "expected_entities": {"test_case_ids": [], "execution_ids": [], "defect_ids": [did]},
            "expected_intent": "defect_lookup",
            "expected_route": "neo4j",
            "gold_answer": {
                "defect_id": did,
                "screenshot_id": s["screenshot_id"],
                "error_messages": s.get("error_messages", []),
                "warning_messages": s.get("warning_messages", [])
            }
        })

    tc_sc_pool = data["tc_screenshots"]
    tc_sc_sample = random.sample(tc_sc_pool, min(10, len(tc_sc_pool))) if tc_sc_pool else []
    for s in tc_sc_sample:
        tcase = s["test_case_id"]
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "screenshot_lookup",
            "hops": 1,
            "question": f"What screen name and UI messages are shown in the screenshot for test case {tcase}?",
            "expected_entities": {"test_case_ids": [tcase], "execution_ids": [], "defect_ids": []},
            "expected_intent": "screenshot_lookup",
            "expected_route": "neo4j",
            "gold_answer": {
                "test_case_id": tcase,
                "screenshot_id": s["screenshot_id"],
                "screen_name": str(s.get("screen_name", "")),
                "error_messages": s.get("error_messages", [])
            }
        })

    # 8. Unanswerable Queries (Guaranteed no collision with real IDs) (20 items)
    all_defects = data["all_defects"]
    all_tcs = data["all_tcs"]
    all_execs = data["all_execs"]

    for i in range(10):
        fake_id = f"BUG-99{random.randint(100000, 999999)}"
        while fake_id in all_defects:
            fake_id = f"BUG-99{random.randint(100000, 999999)}"
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "unanswerable",
            "hops": 0,
            "question": f"What is the root cause and assigned developer for defect {fake_id}?",
            "expected_entities": {"test_case_ids": [], "execution_ids": [], "defect_ids": [fake_id]},
            "expected_intent": "defect_lookup",
            "expected_route": "neo4j",
            "gold_answer": None
        })

    for i in range(5):
        fake_tc = f"TC-99{random.randint(100000, 999999)}"
        while fake_tc in all_tcs:
            fake_tc = f"TC-99{random.randint(100000, 999999)}"
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "unanswerable",
            "hops": 0,
            "question": f"What are the execution steps and expected results for test case {fake_tc}?",
            "expected_entities": {"test_case_ids": [fake_tc], "execution_ids": [], "defect_ids": []},
            "expected_intent": "testcase_lookup",
            "expected_route": "neo4j",
            "gold_answer": None
        })

    for i in range(5):
        fake_ex = f"EXEC-99{random.randint(100000, 999999)}"
        while fake_ex in all_execs:
            fake_ex = f"EXEC-99{random.randint(100000, 999999)}"
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "unanswerable",
            "hops": 0,
            "question": f"Which build and browser was execution {fake_ex} run on?",
            "expected_entities": {"test_case_ids": [], "execution_ids": [fake_ex], "defect_ids": []},
            "expected_intent": "execution_lookup",
            "expected_route": "neo4j",
            "gold_answer": None
        })

    # 9. 20 GENUINELY DISTINCT Broad / Global Questions with Accurate Cypher Gold Aggregations
    bg = data["broad_golds"]
    distinct_broad_questions = [
        ("Which software modules have recorded the highest number of critical or blocker defects?", "lightrag", "general_test_analysis", {"top_modules": bg["top_defect_modules"]}),
        ("What are the most frequent root causes of defect failures across the test suite?", "lightrag", "defect_analysis", {"top_root_causes": bg["top_root_causes"]}),
        ("Which modules are experiencing the highest rate of regression bugs?", "hybrid", "defect_analysis", {"regression_modules": bg["regression_modules"]}),
        ("What is the distribution of defect counts across different severity levels?", "lightrag", "general_test_analysis", {"severity_distribution": bg["severity_dist"]}),
        ("What is the distribution of defect counts across priority levels?", "lightrag", "general_test_analysis", {"priority_distribution": bg["priority_dist"]}),
        ("Which testing environments have recorded the highest number of failed test executions?", "hybrid", "failure_analysis", {"failed_environments": bg["failed_environments"]}),
        ("Which operating systems encountered the most test execution failures?", "hybrid", "failure_analysis", {"failed_os": bg["failed_os"]}),
        ("Which web browsers recorded the highest number of failed test executions?", "hybrid", "failure_analysis", {"failed_browsers": bg["failed_browsers"]}),
        ("Which QA testers have logged the highest number of test execution runs?", "lightrag", "general_test_analysis", {"top_testers": bg["top_testers"]}),
        ("What are the most frequent bug types reported across defects in the system?", "lightrag", "defect_analysis", {"top_bug_types": bg["top_bug_types"]}),
        ("Which system components have the highest concentration of test cases?", "lightrag", "general_test_analysis", {"top_tc_components": bg["top_tc_components"]}),
        ("Which epics have the largest number of associated test cases?", "lightrag", "general_test_analysis", {"top_epics": bg["top_epics"]}),
        ("What is the breakdown of defect statuses across all logged bugs?", "lightrag", "defect_analysis", {"defect_status_distribution": bg["defect_status_dist"]}),
        ("Which test automation frameworks are used most frequently across test cases?", "lightrag", "general_test_analysis", {"automation_frameworks": bg["automation_frameworks"]}),
        ("Which software builds have recorded the most defects during test runs?", "hybrid", "defect_analysis", {"top_build_defects": bg["top_build_defects"]}),
        ("What is the distribution of test cases across execution frequencies (e.g. Daily, Smoke, Regression)?", "lightrag", "general_test_analysis", {"execution_frequencies": bg["execution_frequencies"]}),
        ("Which modules contain the highest number of automated test cases?", "lightrag", "general_test_analysis", {"automated_modules": bg["automated_modules"]}),
        ("Which modules contain the highest number of manual test cases?", "lightrag", "general_test_analysis", {"manual_modules": bg["manual_modules"]}),
        ("What are the top fix versions targeted for resolved defects?", "lightrag", "defect_analysis", {"fix_versions": bg["fix_versions"]}),
        ("Which UI screens captured the highest number of error screenshots during test execution?", "hybrid", "failure_analysis", {"screenshot_screens": bg["screenshot_screens"]})
    ]

    for q_text, route, intent, gold_dict in distinct_broad_questions:
        tests.append({
            "id": f"TEST-{len(tests)+1:04d}",
            "type": "broad_summary",
            "hops": 0,
            "question": q_text,
            "expected_entities": {"test_case_ids": [], "execution_ids": [], "defect_ids": []},
            "expected_intent": intent,
            "expected_route": route,
            "gold_answer": gold_dict
        })

    # Write output testset JSON file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(tests, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Successfully generated {len(tests)} evaluation test cases!")
    print(f"[SUCCESS] Saved to: {OUTPUT_FILE}")

    # Print distributions
    df_summary = pd.DataFrame(tests)
    print("\n--- Testcase Distribution by Type ---")
    print(df_summary["type"].value_counts().to_string())

    print("\n--- Testcase Distribution by Expected Route ---")
    print(df_summary["expected_route"].value_counts().to_string())


if __name__ == "__main__":
    generate_testset()
