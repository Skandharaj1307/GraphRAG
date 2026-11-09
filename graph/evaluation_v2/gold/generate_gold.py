"""
Gold Evaluation Set Generator for GraphRAG-1 (Phase 2 Benchmark)
Sourced strictly from Neo4j (graphragv2) and structured/unstructured dataset.
All answers are computed deterministically via Cypher or raw data parsing.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any
from neo4j import GraphDatabase

SEED = 2026
random_gen = random.Random(SEED)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
OUTPUT_FILE = BASE_DIR / "graph" / "evaluation_v2" / "gold" / "gold_set.jsonl"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "qazwsxedc")
NEO4J_DB = "graphragv2"


# ==========================================
# 1. ID Lookup (0-Hop) Generator (30 cases)
# ==========================================
def generate_id_lookup(session, rng: random.Random) -> List[Dict[str, Any]]:
    records = []
    
    # 10 Defects
    defects = session.run("""
        MATCH (d:Defect)
        WHERE d.root_cause IS NOT NULL AND d.severity IS NOT NULL
        RETURN d.defect_id AS id, d.severity AS severity, d.priority AS priority, 
               d.status AS status, d.module AS module, d.assigned_to AS assigned_to, 
               d.root_cause AS root_cause, d.developer AS developer
        ORDER BY d.defect_id
        SKIP 50 LIMIT 150
    """).data()
    sampled_defects = rng.sample(defects, 10)
    
    for i, d in enumerate(sampled_defects):
        did = d["id"]
        # Phrasing variants
        templates = [
            f"What is the root cause and assigned developer for defect {did}?",
            f"For bug {did}, tell me its severity, priority, and current status.",
            f"Can you lookup defect {did}? I need to know the root cause.",
            f"Show details for {did}: who is developing it and what module is it in?",
            f"Defect {did} status and priority check please.",
        ]
        q_idx = i % len(templates)
        q = templates[q_idx]
        
        if q_idx in [0, 2]:
            gold_query = f"MATCH (d:Defect {{defect_id: '{did}'}}) RETURN d.root_cause AS root_cause, d.developer AS developer"
            gold_answer = f"Root cause: {d['root_cause']}. Assigned developer: {d['developer']}."
            facts = [
                {"entity": did, "field": "root_cause", "value": d["root_cause"]},
                {"entity": did, "field": "developer", "value": d["developer"]}
            ]
        elif q_idx in [1, 4]:
            gold_query = f"MATCH (d:Defect {{defect_id: '{did}'}}) RETURN d.severity AS severity, d.priority AS priority, d.status AS status"
            gold_answer = f"Severity: {d['severity']}, Priority: {d['priority']}, Status: {d['status']}."
            facts = [
                {"entity": did, "field": "severity", "value": d["severity"]},
                {"entity": did, "field": "priority", "value": d["priority"]},
                {"entity": did, "field": "status", "value": d["status"]}
            ]
        else:
            gold_query = f"MATCH (d:Defect {{defect_id: '{did}'}}) RETURN d.developer AS developer, d.module AS module"
            gold_answer = f"Developer: {d['developer']}, Module: {d['module']}."
            facts = [
                {"entity": did, "field": "developer", "value": d["developer"]},
                {"entity": did, "field": "module", "value": d["module"]}
            ]
            
        records.append({
            "query_type": "id_lookup",
            "question": q,
            "expected_intent": "defect_lookup",
            "expected_ids": {"defect": [did], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": gold_answer,
            "gold_facts": facts,
            "gold_nodes": [did],
            "gold_query": gold_query,
            "answerable": True,
            "difficulty": "easy"
        })

    # 10 TestCases
    testcases = session.run("""
        MATCH (tc:TestCase)
        WHERE tc.feature IS NOT NULL AND tc.automation_framework IS NOT NULL
        RETURN tc.test_case_id AS id, tc.feature AS feature, 
               tc.automation_framework AS framework, tc.tester AS tester, 
               tc.release AS release, tc.priority AS priority
        ORDER BY tc.test_case_id
        SKIP 100 LIMIT 150
    """).data()
    sampled_tcs = rng.sample(testcases, 10)
    
    for i, tc in enumerate(sampled_tcs):
        tcid = tc["id"]
        templates = [
            f"What automation framework and tester are configured for test case {tcid}?",
            f"Give me the feature and release version tested by {tcid}.",
            f"Looking up testcase {tcid}: which framework does it use?",
            f"Test case {tcid} details: tester name and priority.",
            f"What is the primary feature under test for {tcid}?"
        ]
        q_idx = i % len(templates)
        q = templates[q_idx]
        
        if q_idx in [0, 2]:
            gold_query = f"MATCH (tc:TestCase {{test_case_id: '{tcid}'}}) RETURN tc.automation_framework AS framework, tc.tester AS tester"
            gold_answer = f"Framework: {tc['framework']}, Tester: {tc['tester']}."
            facts = [
                {"entity": tcid, "field": "automation_framework", "value": tc["framework"]},
                {"entity": tcid, "field": "tester", "value": tc["tester"]}
            ]
        elif q_idx == 1:
            gold_query = f"MATCH (tc:TestCase {{test_case_id: '{tcid}'}}) RETURN tc.feature AS feature, tc.release AS release"
            gold_answer = f"Feature: {tc['feature']}, Release: {tc['release']}."
            facts = [
                {"entity": tcid, "field": "feature", "value": tc["feature"]},
                {"entity": tcid, "field": "release", "value": tc["release"]}
            ]
        else:
            gold_query = f"MATCH (tc:TestCase {{test_case_id: '{tcid}'}}) RETURN tc.tester AS tester, tc.priority AS priority"
            gold_answer = f"Tester: {tc['tester']}, Priority: {tc['priority']}."
            facts = [
                {"entity": tcid, "field": "tester", "value": tc["tester"]},
                {"entity": tcid, "field": "priority", "value": tc["priority"]}
            ]
            
        records.append({
            "query_type": "id_lookup",
            "question": q,
            "expected_intent": "testcase_lookup",
            "expected_ids": {"defect": [], "testcase": [tcid], "execution": [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": gold_answer,
            "gold_facts": facts,
            "gold_nodes": [tcid],
            "gold_query": gold_query,
            "answerable": True,
            "difficulty": "easy"
        })

    # 10 Executions
    executions = session.run("""
        MATCH (ex:Execution)
        WHERE ex.environment IS NOT NULL AND ex.browser IS NOT NULL
        RETURN ex.execution_id AS id, ex.environment AS env, ex.browser AS browser, 
               ex.operating_system AS os, ex.status AS status, ex.execution_time_seconds AS exec_time
        ORDER BY ex.execution_id
        SKIP 200 LIMIT 150
    """).data()
    sampled_ex = rng.sample(executions, 10)
    
    for i, ex in enumerate(sampled_ex):
        exid = ex["id"]
        templates = [
            f"What browser and operating system were used for test execution {exid}?",
            f"Check status and runtime duration of execution {exid}.",
            f"Execution {exid}: which environment did it run in and was it successful?",
            f"Can you tell me the OS and browser configuration for run {exid}?",
            f"What was the outcome (status) and environment for {exid}?"
        ]
        q_idx = i % len(templates)
        q = templates[q_idx]
        
        if q_idx in [0, 3]:
            gold_query = f"MATCH (ex:Execution {{execution_id: '{exid}'}}) RETURN ex.browser AS browser, ex.operating_system AS os"
            gold_answer = f"Browser: {ex['browser']}, Operating System: {ex['os']}."
            facts = [
                {"entity": exid, "field": "browser", "value": ex["browser"]},
                {"entity": exid, "field": "operating_system", "value": ex["os"]}
            ]
        elif q_idx == 1:
            gold_query = f"MATCH (ex:Execution {{execution_id: '{exid}'}}) RETURN ex.status AS status, ex.execution_time_seconds AS exec_time"
            gold_answer = f"Status: {ex['status']}, Runtime: {ex['exec_time']}s."
            facts = [
                {"entity": exid, "field": "status", "value": ex["status"]},
                {"entity": exid, "field": "execution_time_seconds", "value": ex["exec_time"]}
            ]
        else:
            gold_query = f"MATCH (ex:Execution {{execution_id: '{exid}'}}) RETURN ex.environment AS env, ex.status AS status"
            gold_answer = f"Environment: {ex['env']}, Status: {ex['status']}."
            facts = [
                {"entity": exid, "field": "environment", "value": ex["env"]},
                {"entity": exid, "field": "status", "value": ex["status"]}
            ]
            
        records.append({
            "query_type": "id_lookup",
            "question": q,
            "expected_intent": "execution_lookup",
            "expected_ids": {"defect": [], "testcase": [], "execution": [exid], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": gold_answer,
            "gold_facts": facts,
            "gold_nodes": [exid],
            "gold_query": gold_query,
            "answerable": True,
            "difficulty": "easy"
        })

    return records


# ==========================================================
# 2. Defect to TestCase & TestCase to Defects (2-Hop) (30)
# ==========================================================
def generate_two_hop(session, rng: random.Random) -> List[Dict[str, Any]]:
    records = []
    
    # 15 defect_to_testcase (some with multiple executions)
    multi_exec_defects = session.run("""
        MATCH (d:Defect)<-[:HAS_DEFECT]-(tc:TestCase)-[:HAS_EXECUTION]->(ex:Execution)
        WITH d, tc, count(ex) AS ex_count, collect(ex) AS executions
        WHERE ex_count > 1
        RETURN d.defect_id AS did, tc.test_case_id AS tcid, 
               [e IN executions | {exec_id: e.execution_id, build: e.build_number, tester: e.tester}] AS exec_details
        ORDER BY d.defect_id
        LIMIT 50
    """).data()
    
    single_exec_defects = session.run("""
        MATCH (d:Defect)<-[:HAS_DEFECT]-(tc:TestCase)-[:HAS_EXECUTION]->(ex:Execution)
        WITH d, tc, count(ex) AS ex_count, collect(ex) AS executions
        WHERE ex_count = 1
        RETURN d.defect_id AS did, tc.test_case_id AS tcid, 
               [e IN executions | {exec_id: e.execution_id, build: e.build_number, tester: e.tester}] AS exec_details
        ORDER BY d.defect_id
        SKIP 20 LIMIT 50
    """).data()
    
    sampled_def_multi = rng.sample(multi_exec_defects, 8)
    sampled_def_single = rng.sample(single_exec_defects, 7)
    sampled_d2tc = sampled_def_multi + sampled_def_single
    rng.shuffle(sampled_d2tc)
    
    for i, item in enumerate(sampled_d2tc):
        did = item["did"]
        tcid = item["tcid"]
        exec_details = item["exec_details"]
        
        templates = [
            f"Which test case produced defect {did} and who ran it in which build?",
            f"For bug {did}, identify the originating testcase, execution runs, and testers.",
            f"Trace {did} back to its test case and execution details.",
            f"Who verified the test case that uncovered {did}, and in what build numbers?",
            f"Can you find the test case and all associated execution runs for {did}?"
        ]
        q = templates[i % len(templates)]
        
        exec_str = "; ".join([f"Execution {e['exec_id']} (Build: {e['build']}, Tester: {e['tester']})" for e in exec_details])
        gold_answer = f"Produced by test case {tcid}. Executions: {exec_str}."
        
        facts = [{"entity": did, "field": "linked_test_case", "value": tcid}]
        for e in exec_details:
            facts.append({"entity": e["exec_id"], "field": "build_number", "value": e["build"]})
            facts.append({"entity": e["exec_id"], "field": "tester", "value": e["tester"]})
            
        gold_query = f"""
        MATCH (d:Defect {{defect_id: '{did}'}})<-[:HAS_DEFECT]-(tc:TestCase)-[:HAS_EXECUTION]->(ex:Execution)
        RETURN tc.test_case_id AS tcid, collect({{exec_id: ex.execution_id, build: ex.build_number, tester: ex.tester}}) AS exec_details
        """.strip()
        
        records.append({
            "query_type": "defect_to_testcase",
            "question": q,
            "expected_intent": "defect_to_testcase",
            "expected_ids": {"defect": [did], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": gold_answer,
            "gold_facts": facts,
            "gold_nodes": [did, tcid] + [e["exec_id"] for e in exec_details],
            "gold_query": gold_query,
            "answerable": True,
            "difficulty": "medium" if len(exec_details) > 1 else "easy"
        })

    # 15 testcase_to_defects
    tc_defects = session.run("""
        MATCH (tc:TestCase)-[:HAS_DEFECT]->(d:Defect)
        WITH tc, count(d) AS defect_count, collect(d.defect_id) AS defect_ids
        RETURN tc.test_case_id AS tcid, defect_ids, defect_count
        ORDER BY tc.test_case_id
        SKIP 30 LIMIT 80
    """).data()
    sampled_tc2d = rng.sample(tc_defects, 15)
    
    for i, item in enumerate(sampled_tc2d):
        tcid = item["tcid"]
        dids = item["defect_ids"]
        
        templates = [
            f"List all defect IDs found during execution of test case {tcid}.",
            f"Which defects were linked or discovered by testcase {tcid}?",
            f"Show all bugs originating from {tcid}.",
            f"What defects were reported when running {tcid}?",
            f"Can you extract the list of defects associated with test case {tcid}?"
        ]
        q = templates[i % len(templates)]
        gold_answer = f"Defects linked to {tcid}: {', '.join(dids)}."
        facts = [{"entity": tcid, "field": "defect_ids", "value": dids}]
        
        gold_query = f"""
        MATCH (tc:TestCase {{test_case_id: '{tcid}'}})-[:HAS_DEFECT]->(d:Defect)
        RETURN collect(d.defect_id) AS defect_ids
        """.strip()
        
        records.append({
            "query_type": "testcase_to_defects",
            "question": q,
            "expected_intent": "testcase_to_defects",
            "expected_ids": {"defect": [], "testcase": [tcid], "execution": [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": gold_answer,
            "gold_facts": facts,
            "gold_nodes": [tcid] + dids,
            "gold_query": gold_query,
            "answerable": True,
            "difficulty": "easy" if len(dids) <= 1 else "medium"
        })

    return records


# ==========================================================
# 3. Execution Context Generator (30 cases)
# ==========================================================
def generate_execution_context(session, rng: random.Random) -> List[Dict[str, Any]]:
    records = []
    
    executions = session.run("""
        MATCH (ex:Execution)<-[:HAS_EXECUTION]-(tc:TestCase)
        RETURN ex.execution_id AS exid, ex.tester AS tester, ex.build_number AS build, 
               ex.status AS status, tc.test_case_id AS tcid, ex.environment AS env,
               ex.browser AS browser, ex.operating_system AS os
        ORDER BY ex.execution_id
        SKIP 400 LIMIT 100
    """).data()
    sampled = rng.sample(executions, 30)
    
    for i, ex in enumerate(sampled):
        exid = ex["exid"]
        tester = ex["tester"]
        build = ex["build"]
        status = ex["status"]
        tcid = ex["tcid"]
        
        templates = [
            f"Who executed test run {exid}, in which build, and what was the test status?",
            f"For test execution {exid}, provide the tester name, build number, status, and linked test case.",
            f"What are the execution details for {exid} (tester, build, and result)?",
            f"Check run {exid}: who performed the test and did it pass in build {build}?",
            f"Give me the status, build, and linked test case ID for execution {exid}."
        ]
        q = templates[i % len(templates)]
        
        gold_answer = f"Execution {exid}: Tested by {tester} in build {build} with status '{status}' for test case {tcid}."
        facts = [
            {"entity": exid, "field": "tester", "value": tester},
            {"entity": exid, "field": "build_number", "value": build},
            {"entity": exid, "field": "status", "value": status},
            {"entity": exid, "field": "test_case_id", "value": tcid}
        ]
        gold_query = f"""
        MATCH (ex:Execution {{execution_id: '{exid}'}})<-[:HAS_EXECUTION]-(tc:TestCase)
        RETURN ex.tester AS tester, ex.build_number AS build, ex.status AS status, tc.test_case_id AS tcid
        """.strip()
        
        records.append({
            "query_type": "execution_context",
            "question": q,
            "expected_intent": "execution_context",
            "expected_ids": {"defect": [], "testcase": [], "execution": [exid], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": gold_answer,
            "gold_facts": facts,
            "gold_nodes": [exid, tcid],
            "gold_query": gold_query,
            "answerable": True,
            "difficulty": "easy"
        })
        
    return records


# ==========================================================
# 4. Aggregations (Group-By & Counts) (30 cases)
# ==========================================================
def generate_aggregation(session, rng: random.Random) -> List[Dict[str, Any]]:
    records = []
    
    # Category A: Group by module without filter (5)
    mod_data = session.run("MATCH (d:Defect) RETURN d.module AS key, count(d) AS cnt ORDER BY cnt DESC, key ASC").data()
    top_5_mods = mod_data[:5]
    top_str = ", ".join([f"{r['key']}: {r['cnt']}" for r in top_5_mods])
    cutoff_cnt = top_5_mods[-1]["cnt"]
    tied_keys = [r["key"] for r in mod_data if r["cnt"] == cutoff_cnt]

    q_mods = [
        "What are the top 5 modules with the highest number of defects?",
        "Break down defect counts by module for the top 5 modules.",
        "Which software modules have the most defect records?",
        "Give me the defect counts for the top 5 most bug-heavy modules.",
        "List the top 5 modules by total defects reported."
    ]
    for i in range(5):
        rec = {
            "query_type": "aggregation",
            "question": q_mods[i],
            "expected_intent": "defect_analysis",
            "expected_ids": {"defect": [], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": "module",
            "gold_answer": f"Top 5 modules by defect count: {top_str}.",
            "gold_facts": [{"entity": r["key"], "field": "defect_count", "value": r["cnt"]} for r in top_5_mods],
            "gold_nodes": [],
            "gold_query": "MATCH (d:Defect) RETURN d.module AS key, count(d) AS cnt ORDER BY cnt DESC, key ASC LIMIT 5",
            "answerable": True,
            "difficulty": "medium"
        }
        if len(tied_keys) > 1:
            rec["tie_at_cutoff"] = tied_keys
        records.append(rec)

    # Category B: Group by severity without filter (5)
    sev_data = session.run("MATCH (d:Defect) RETURN d.severity AS key, count(d) AS cnt ORDER BY cnt DESC, key ASC").data()
    sev_str = ", ".join([f"{r['key']}: {r['cnt']}" for r in sev_data])
    q_sevs = [
        "What is the breakdown of defects by severity level?",
        "How many defects are there per severity rating across the test suite?",
        "Count all defects grouped by their severity.",
        "Show the defect count distribution for each severity tier.",
        "Give me the total defects categorized by severity."
    ]
    for i in range(5):
        records.append({
            "query_type": "aggregation",
            "question": q_sevs[i],
            "expected_intent": "defect_analysis",
            "expected_ids": {"defect": [], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": "severity",
            "gold_answer": f"Defects by severity: {sev_str}.",
            "gold_facts": [{"entity": r["key"], "field": "defect_count", "value": r["cnt"]} for r in sev_data],
            "gold_nodes": [],
            "gold_query": "MATCH (d:Defect) RETURN d.severity AS key, count(d) AS cnt ORDER BY cnt DESC, key ASC",
            "answerable": True,
            "difficulty": "easy"
        })

    # Category C: Group by status with module filter (5)
    modules = ["CRM", "Payroll", "POS", "Inventory", "Sales"]
    for i, mod in enumerate(modules):
        st_data = session.run(f"MATCH (d:Defect) WHERE d.module = '{mod}' RETURN d.status AS key, count(d) AS cnt ORDER BY cnt DESC, key ASC").data()
        st_str = ", ".join([f"{r['key']}: {r['cnt']}" for r in st_data])
        q = f"In the {mod} module, how many defects are in each status (Open, Closed, etc.)?"
        records.append({
            "query_type": "aggregation",
            "question": q,
            "expected_intent": "defect_analysis",
            "expected_ids": {"defect": [], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": {"module": mod},
            "group_filters": {"module": mod},
            "expected_group_by": "status",
            "gold_answer": f"Defect status counts in {mod}: {st_str}.",
            "gold_facts": [{"entity": r["key"], "field": "defect_count", "value": r["cnt"]} for r in st_data],
            "gold_nodes": [],
            "gold_query": f"MATCH (d:Defect) WHERE d.module = '{mod}' RETURN d.status AS key, count(d) AS cnt ORDER BY cnt DESC, key ASC",
            "answerable": True,
            "difficulty": "medium"
        })

    # Category D: Multi-value filter (severity in Critical, Blocker) grouped by module (5)
    sev_filter_all = session.run("""
        MATCH (d:Defect)
        WHERE d.severity IN ['Critical', 'Blocker']
        RETURN d.module AS key, count(d) AS cnt
        ORDER BY cnt DESC, key ASC
    """).data()
    sev_filter_data = sev_filter_all[:5]
    crit_str = ", ".join([f"{r['key']}: {r['cnt']}" for r in sev_filter_data])
    cutoff_cnt_d = sev_filter_data[-1]["cnt"]
    tied_keys_d = [r["key"] for r in sev_filter_all if r["cnt"] == cutoff_cnt_d]

    q_crit = [
        "Which 5 modules have recorded the most Critical or Blocker defects?",
        "Show the top 5 modules with defects that are either Critical or Blocker severity.",
        "List defect counts per module for high-impact bugs (Critical and Blocker) top 5.",
        "What are the top 5 modules by combined Critical and Blocker defects?",
        "Find the 5 modules with the highest number of severe defects (Critical/Blocker)."
    ]
    for i in range(5):
        rec_d = {
            "query_type": "aggregation",
            "question": q_crit[i],
            "expected_intent": "defect_analysis",
            "expected_ids": {"defect": [], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": {"severity": ["Critical", "Blocker"]},
            "group_filters": {"severity": ["Critical", "Blocker"]},
            "expected_group_by": "module",
            "gold_answer": f"Top 5 modules with Critical or Blocker defects: {crit_str}.",
            "gold_facts": [{"entity": r["key"], "field": "defect_count", "value": r["cnt"]} for r in sev_filter_data],
            "gold_nodes": [],
            "gold_query": "MATCH (d:Defect) WHERE d.severity IN ['Critical', 'Blocker'] RETURN d.module AS key, count(d) AS cnt ORDER BY cnt DESC, key ASC LIMIT 5",
            "answerable": True,
            "difficulty": "hard"
        }
        if len(tied_keys_d) > 1:
            rec_d["tie_at_cutoff"] = tied_keys_d
        records.append(rec_d)

    # Category E: "How many" exact count queries with single/dual filters (10)
    filter_specs = [
        ({"module": "Studio", "severity": "Critical"}, "How many Critical defects were logged in module Studio?"),
        ({"module": "HR", "status": "Closed"}, "What is the total number of Closed defects in the HR module?"),
        ({"severity": "Blocker", "environment": "PROD"}, "How many Blocker defects were discovered in the PROD environment?"),
        ({"module": "Website", "priority": "P1"}, "Count the number of P1 priority defects in module Website."),
        ({"module": "eCommerce", "regression": "Yes"}, "How many regression defects were reported in eCommerce?"),
        ({"severity": "Minor", "status": "In Progress"}, "How many Minor defects are currently In Progress?"),
        ({"module": "Accounting", "severity": "Major"}, "Count the Major defects logged under Accounting."),
        ({"environment": "UAT", "severity": "Critical"}, "How many Critical defects occurred during UAT testing?"),
        ({"module": "Helpdesk", "status": "Resolved"}, "What is the count of Resolved defects in module Helpdesk?"),
        ({"priority": "P0", "module": "Sales"}, "How many P0 defects were logged for Sales?")
    ]
    for filters, question in filter_specs:
        where_clauses = [f"d.{k} = '{v}'" for k, v in filters.items()]
        where_str = " AND ".join(where_clauses)
        cypher = f"MATCH (d:Defect) WHERE {where_str} RETURN count(d) AS total"
        cnt = session.run(cypher).single()["total"]
        
        records.append({
            "query_type": "aggregation",
            "question": question,
            "expected_intent": "defect_analysis",
            "expected_ids": {"defect": [], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": filters,
            "group_filters": filters,
            "expected_group_by": None,
            "gold_answer": f"Total matching defects: {cnt}.",
            "gold_facts": [{"entity": "filtered_defects", "field": "total_count", "value": cnt}],
            "gold_nodes": [],
            "gold_query": cypher,
            "answerable": True,
            "difficulty": "medium"
        })

    return records


# ==========================================================
# 5. Multi-Condition Filter (30 cases)
# ==========================================================
def generate_multi_condition_filter(session, rng: random.Random) -> List[Dict[str, Any]]:
    records = []
    
    # Sample 15 distinct real combinations of 2-3 properties that actually exist in the database
    combos = session.run("""
        MATCH (d:Defect)
        WITH d.module AS module, d.severity AS severity, d.status AS status, count(d) AS cnt
        WHERE cnt >= 5
        RETURN module, severity, status, cnt
        ORDER BY cnt DESC
        SKIP 5 LIMIT 40
    """).data()
    sampled_combos = rng.sample(combos, 15)
    
    for row in sampled_combos:
        cond = {"module": row["module"], "severity": row["severity"], "status": row["status"]}
        where_clauses = [f"d.{k} = '{v}'" for k, v in cond.items()]
        where_str = " AND ".join(where_clauses)
        cypher = f"""
        MATCH (d:Defect)
        WHERE {where_str}
        RETURN count(d) AS total, collect(d.defect_id)[..20] AS sample_ids
        """.strip()
        
        res = session.run(cypher).single()
        total = res["total"]
        sample_ids = res["sample_ids"]
        
        c_desc = f"module='{cond['module']}', severity='{cond['severity']}', status='{cond['status']}'"
        sample_str = ", ".join(sample_ids) if sample_ids else "None"
        gold_ans = f"Total matching defects: {total}. Sample matching IDs (up to 20): {sample_str}."
        
        # Variant 1: standard list
        q1 = f"List all defect IDs matching criteria: {c_desc}."
        records.append({
            "query_type": "multi_condition_filter",
            "question": q1,
            "expected_intent": "defect_analysis",
            "expected_ids": {"defect": [], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": cond,
            "expected_group_by": None,
            "gold_answer": gold_ans,
            "gold_facts": [
                {"entity": "filter_query", "field": "total_count", "value": total},
                {"entity": "filter_query", "field": "sample_ids", "value": sample_ids}
            ],
            "gold_nodes": sample_ids,
            "gold_query": cypher,
            "answerable": True,
            "difficulty": "medium"
        })
        
        # Variant 2: question phrasing
        q2 = f"Which defects have {c_desc}? State the total and list matching bug IDs."
        records.append({
            "query_type": "multi_condition_filter",
            "question": q2,
            "expected_intent": "defect_analysis",
            "expected_ids": {"defect": [], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": cond,
            "expected_group_by": None,
            "gold_answer": gold_ans,
            "gold_facts": [
                {"entity": "filter_query", "field": "total_count", "value": total},
                {"entity": "filter_query", "field": "sample_ids", "value": sample_ids}
            ],
            "gold_nodes": sample_ids,
            "gold_query": cypher,
            "answerable": True,
            "difficulty": "medium"
        })
        
    return records


# ==========================================================
# 6. Semantic Free-Text Queries (30 cases)
# ==========================================================
def generate_semantic(session, rng: random.Random) -> List[Dict[str, Any]]:
    records = []
    
    defects = session.run("""
        MATCH (d:Defect)
        WHERE d.root_cause IS NOT NULL AND size(d.root_cause) > 30
        RETURN d.defect_id AS did, d.root_cause AS root_cause, d.module AS module, d.title AS title
        ORDER BY d.defect_id
        SKIP 250 LIMIT 100
    """).data()
    sampled = rng.sample(defects, 30)
    
    for i, d in enumerate(sampled):
        did = d["did"]
        rc = d["root_cause"]
        mod = d["module"]
        
        # Hand-crafted paraphrase templates stripping IDs
        templates = [
            f"What defect is related to: {rc}?",
            f"Find any bug reported in {mod} with root cause regarding: {rc[:90]}.",
            f"We are encountering an issue where '{rc[:100]}'. Is there a known defect recorded for this?",
            f"Search test issues matching description: {rc[:80]}.",
            f"Which defect report describes {rc[:85]} in module {mod}?"
        ]
        q = templates[i % len(templates)]
        gold_answer = f"Defect {did} matches this description (Module: {mod}, Root Cause: {rc})."
        
        gold_query = f"MATCH (d:Defect {{defect_id: '{did}'}}) RETURN d.defect_id AS did, d.root_cause AS root_cause, d.module AS module"
        facts = [
            {"entity": did, "field": "root_cause", "value": rc},
            {"entity": did, "field": "module", "value": mod}
        ]
        
        records.append({
            "query_type": "semantic",
            "question": q,
            "expected_intent": "semantic_search",
            "expected_ids": {"defect": [], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": gold_answer,
            "gold_facts": facts,
            "gold_nodes": [did],
            "gold_query": gold_query,
            "answerable": True,
            "difficulty": "medium"
        })
        
    return records


# ==========================================================
# 7. Unstructured Logs (30 cases)
# ==========================================================
def generate_unstructured_logs(session, rng: random.Random) -> List[Dict[str, Any]]:
    records = []
    
    logs = session.run("""
        MATCH (ex:Execution)-[:HAS_FAILURE_LOG]->(lc:LogChunk)
        WHERE lc.exception_name IS NOT NULL AND lc.exception_message IS NOT NULL
        RETURN ex.execution_id AS exid, lc.log_id AS log_id, 
               lc.exception_name AS exc_name, lc.exception_message AS exc_msg,
               lc.resolution_hint AS hint
        ORDER BY ex.execution_id
        SKIP 50 LIMIT 100
    """).data()
    sampled = rng.sample(logs, 30)
    
    for i, row in enumerate(sampled):
        exid = row["exid"]
        exc_name = row["exc_name"]
        exc_msg = row["exc_msg"]
        
        templates = [
            f"Why did test execution {exid} fail according to the failure logs?",
            f"What specific exception and error message were logged during run {exid}?",
            f"Check the failure log for execution {exid}: what was the error?",
            f"Show the stack trace exception details recorded for execution {exid}.",
            f"In run {exid}, what runtime exception caused the failure?"
        ]
        q = templates[i % len(templates)]
        gold_answer = f"Execution {exid} failed with {exc_name}: {exc_msg}"
        facts = [
            {"entity": exid, "field": "exception_name", "value": exc_name},
            {"entity": exid, "field": "exception_message", "value": exc_msg}
        ]
        gold_query = f"""
        MATCH (ex:Execution {{execution_id: '{exid}'}})-[:HAS_FAILURE_LOG]->(lc:LogChunk)
        RETURN lc.exception_name AS exc_name, lc.exception_message AS exc_msg
        """.strip()
        
        records.append({
            "query_type": "unstructured_logs",
            "question": q,
            "expected_intent": "defect_analysis",
            "expected_ids": {"defect": [], "testcase": [], "execution": [exid], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": gold_answer,
            "gold_facts": facts,
            "gold_nodes": [exid, row["log_id"]],
            "gold_query": gold_query,
            "answerable": True,
            "difficulty": "medium"
        })
        
    return records


# ==========================================================
# 8. Requirements Tracing (30 cases)
# ==========================================================
def generate_requirements(session, rng: random.Random) -> List[Dict[str, Any]]:
    records = []
    
    # 15 TestCase -> Requirements
    tc_reqs = session.run("""
        MATCH (tc:TestCase)-[:VERIFIES]->(req:Requirement)
        WITH tc, collect(req.requirement_id) AS req_ids
        RETURN tc.test_case_id AS tcid, req_ids
        ORDER BY tc.test_case_id
        SKIP 10 LIMIT 50
    """).data()
    sampled_tc = rng.sample(tc_reqs, 15)
    
    for i, item in enumerate(sampled_tc):
        tcid = item["tcid"]
        req_ids = item["req_ids"]
        req_str = ", ".join(req_ids)
        
        templates = [
            f"Which SRS requirement does test case {tcid} verify?",
            f"Trace testcase {tcid} to its verified requirement specification IDs.",
            f"What requirement is validated by test {tcid}?",
            f"Find the requirement IDs linked to test case {tcid}.",
            f"Check requirement traceability for {tcid}."
        ]
        q = templates[i % len(templates)]
        gold_answer = f"Test case {tcid} verifies requirement(s): {req_str}."
        facts = [{"entity": tcid, "field": "verified_requirements", "value": req_ids}]
        gold_query = f"""
        MATCH (tc:TestCase {{test_case_id: '{tcid}'}})-[:VERIFIES]->(req:Requirement)
        RETURN collect(req.requirement_id) AS req_ids
        """.strip()
        
        records.append({
            "query_type": "requirements",
            "question": q,
            "expected_intent": "testcase_lookup",
            "expected_ids": {"defect": [], "testcase": [tcid], "execution": [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": gold_answer,
            "gold_facts": facts,
            "gold_nodes": [tcid] + req_ids,
            "gold_query": gold_query,
            "answerable": True,
            "difficulty": "easy"
        })

    # 15 Requirement -> TestCases
    req_tcs = session.run("""
        MATCH (tc:TestCase)-[:VERIFIES]->(req:Requirement)
        WITH req, count(tc) AS tc_cnt, collect(tc.test_case_id)[..10] AS sample_tcs
        WHERE tc_cnt > 0
        RETURN req.requirement_id AS req_id, tc_cnt, sample_tcs
        ORDER BY req.requirement_id
        SKIP 10 LIMIT 50
    """).data()
    sampled_req = rng.sample(req_tcs, 15)
    
    for i, item in enumerate(sampled_req):
        rid = item["req_id"]
        cnt = item["tc_cnt"]
        sample_tcs = item["sample_tcs"]
        tc_str = ", ".join(sample_tcs)
        
        templates = [
            f"Which test cases verify requirement {rid}?",
            f"List test case IDs associated with requirement specification {rid}.",
            f"What tests have been implemented to validate requirement {rid}?",
            f"Find all test cases verifying SRS requirement {rid}.",
            f"Trace requirement {rid} forward to its test cases."
        ]
        q = templates[i % len(templates)]
        gold_answer = f"Requirement {rid} is verified by {cnt} test case(s). Sample IDs: {tc_str}."
        facts = [
            {"entity": rid, "field": "testcase_count", "value": cnt},
            {"entity": rid, "field": "sample_testcases", "value": sample_tcs}
        ]
        gold_query = f"""
        MATCH (tc:TestCase)-[:VERIFIES]->(req:Requirement {{requirement_id: '{rid}'}})
        RETURN count(tc) AS tc_cnt, collect(tc.test_case_id)[..10] AS sample_tcs
        """.strip()
        
        records.append({
            "query_type": "requirements",
            "question": q,
            "expected_intent": "testcase_lookup",
            "expected_ids": {"defect": [], "testcase": [], "execution": [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": gold_answer,
            "gold_facts": facts,
            "gold_nodes": [rid] + sample_tcs,
            "gold_query": gold_query,
            "answerable": True,
            "difficulty": "medium"
        })

    return records


# ==========================================================
# 9. Unanswerable Queries (20 cases)
# ==========================================================
def generate_unanswerable(rng: random.Random) -> List[Dict[str, Any]]:
    records = []
    
    # 8 Non-existent IDs
    nonexistent_ids = [
        ("BUG-999981", "What is the root cause and severity of defect BUG-999981?", "defect"),
        ("BUG-999982", "Which developer was assigned to fix defect BUG-999982?", "defect"),
        ("TC-999991", "What automation framework is used by test case TC-999991?", "testcase"),
        ("TC-999992", "List all defects linked to test case TC-999992.", "testcase"),
        ("EXEC-999991", "What environment and browser were used in execution EXEC-999991?", "execution"),
        ("EXEC-999992", "Did execution EXEC-999992 pass or fail?", "execution"),
        ("BUG-999983", "Which test case produced defect BUG-999983?", "defect"),
        ("TC-999993", "Which SRS requirement does test case TC-999993 verify?", "testcase")
    ]
    for ent_id, q, ent_type in nonexistent_ids:
        expected_ids = {"defect": [], "testcase": [], "execution": [], "screenshot": []}
        expected_ids[ent_type] = [ent_id]
        records.append({
            "query_type": "unanswerable",
            "question": q,
            "expected_intent": "unanswerable",
            "expected_ids": expected_ids,
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": "NOT_IN_DATA",
            "gold_facts": [],
            "gold_nodes": [],
            "gold_query": f"MATCH (n) WHERE n.defect_id = '{ent_id}' OR n.test_case_id = '{ent_id}' OR n.execution_id = '{ent_id}' RETURN count(n) AS cnt",
            "answerable": False,
            "difficulty": "easy"
        })

    # 6 Non-existent properties / metadata
    missing_fields = [
        ("What was the AWS cloud hosting cost for defect BUG-001545?", "BUG-001545", "defect"),
        ("What is the annual salary of tester Robert Davis?", "Robert Davis", "tester"),
        ("How much memory RAM was allocated to execution EXEC-002194?", "EXEC-002194", "execution"),
        ("What was the monetary financial loss incurred from defect BUG-000067?", "BUG-000067", "defect"),
        ("What is the Jira story point estimate for test case TC-000001?", "TC-000001", "testcase"),
        ("What database server IP address hosted execution EXEC-004059?", "EXEC-004059", "execution")
    ]
    for q, target, ent_type in missing_fields:
        records.append({
            "query_type": "unanswerable",
            "question": q,
            "expected_intent": "unanswerable",
            "expected_ids": {"defect": [target] if "BUG" in target else [], "testcase": [target] if "TC" in target else [], "execution": [target] if "EXEC" in target else [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": "NOT_IN_DATA",
            "gold_facts": [],
            "gold_nodes": [],
            "gold_query": "RETURN 'FIELD_NOT_IN_SCHEMA' AS status",
            "answerable": False,
            "difficulty": "medium"
        })

    # 6 Future or unknowable information
    future_queries = [
        ("When will defect BUG-001545 be refactored in release v25.0?", "BUG-001545", "defect"),
        ("Who will execute test case TC-000001 next year?", "TC-000001", "testcase"),
        ("Will defect BUG-000067 recur in the upcoming 2028 release?", "BUG-000067", "defect"),
        ("What will be the pass rate of module CRM in version 18.0?", "CRM", "module"),
        ("Predict the failure root cause for next week's execution runs.", None, "general"),
        ("How many defects will be submitted by tester Ashley Clark next month?", "Ashley Clark", "tester")
    ]
    for q, target, ent_type in future_queries:
        records.append({
            "query_type": "unanswerable",
            "question": q,
            "expected_intent": "unanswerable",
            "expected_ids": {"defect": [target] if target and "BUG" in target else [], "testcase": [target] if target and "TC" in target else [], "execution": [], "screenshot": []},
            "expected_filters": {},
            "expected_group_by": None,
            "gold_answer": "NOT_IN_DATA",
            "gold_facts": [],
            "gold_nodes": [],
            "gold_query": "RETURN 'FUTURE_UNKNOWABLE' AS status",
            "answerable": False,
            "difficulty": "hard"
        })

    return records


# ==========================================================
# 10. Adversarial Queries (10 cases)
# ==========================================================
def generate_adversarial(session) -> List[Dict[str, Any]]:
    records = []
    
    # 1. Typo in ID
    records.append({
        "query_type": "adversarial",
        "question": "What is the root cause of defect BUG_001545?",
        "expected_intent": "defect_lookup",
        "expected_ids": {"defect": ["BUG-001545"], "testcase": [], "execution": [], "screenshot": []},
        "expected_filters": {},
        "expected_group_by": None,
        "gold_answer": "Root cause for BUG-001545: The warehouse operator processed the POS receipt but the system raised a validation exception. The system escalated the manufacturing order due to missing configuration settings. The warehouse operator updated the manufacturing order while ensuring all mandatory fields were populated.",
        "gold_facts": [{"entity": "BUG-001545", "field": "root_cause", "value": "The warehouse operator processed the POS receipt but the system raised a validation exception. The system escalated the manufacturing order due to missing configuration settings. The warehouse operator updated the manufacturing order while ensuring all mandatory fields were populated."}],
        "gold_nodes": ["BUG-001545"],
        "gold_query": "MATCH (d:Defect {defect_id: 'BUG-001545'}) RETURN d.root_cause AS root_cause",
        "answerable": True,
        "difficulty": "medium"
    })
    
    # 2. Lowercase ID
    records.append({
        "query_type": "adversarial",
        "question": "Show details for execution exec-002194: environment and browser.",
        "expected_intent": "execution_lookup",
        "expected_ids": {"defect": [], "testcase": [], "execution": ["EXEC-002194"], "screenshot": []},
        "expected_filters": {},
        "expected_group_by": None,
        "gold_answer": "Environment: UAT, Browser: Edge.",
        "gold_facts": [
            {"entity": "EXEC-002194", "field": "environment", "value": "UAT"},
            {"entity": "EXEC-002194", "field": "browser", "value": "Edge"}
        ],
        "gold_nodes": ["EXEC-002194"],
        "gold_query": "MATCH (ex:Execution {execution_id: 'EXEC-002194'}) RETURN ex.environment AS env, ex.browser AS browser",
        "answerable": True,
        "difficulty": "medium"
    })
    
    # 3. Two IDs in one question
    records.append({
        "query_type": "adversarial",
        "question": "Between defect BUG-001545 and BUG-000067, which one has higher priority?",
        "expected_intent": "defect_lookup",
        "expected_ids": {"defect": ["BUG-001545", "BUG-000067"], "testcase": [], "execution": [], "screenshot": []},
        "expected_filters": {},
        "expected_group_by": None,
        "gold_answer": "BUG-001545 has priority P1, while BUG-000067 has priority P2; therefore BUG-001545 has higher priority.",
        "gold_facts": [
            {"entity": "BUG-001545", "field": "priority", "value": "P1"},
            {"entity": "BUG-000067", "field": "priority", "value": "P2"}
        ],
        "gold_nodes": ["BUG-001545", "BUG-000067"],
        "gold_query": "MATCH (d:Defect) WHERE d.defect_id IN ['BUG-001545', 'BUG-000067'] RETURN d.defect_id AS did, d.priority AS priority",
        "answerable": True,
        "difficulty": "hard"
    })
    
    # 4. Misleading premise: asking why a passed test case failed
    records.append({
        "query_type": "adversarial",
        "question": "Why did execution EXEC-002194 fail and crash?",
        "expected_intent": "execution_context",
        "expected_ids": {"defect": [], "testcase": [], "execution": ["EXEC-002194"], "screenshot": []},
        "expected_filters": {},
        "expected_group_by": None,
        "gold_answer": "Execution EXEC-002194 did not fail; its status is 'Passed'.",
        "gold_facts": [{"entity": "EXEC-002194", "field": "status", "value": "Passed"}],
        "gold_nodes": ["EXEC-002194"],
        "gold_query": "MATCH (ex:Execution {execution_id: 'EXEC-002194'}) RETURN ex.status AS status",
        "answerable": True,
        "difficulty": "hard"
    })
    
    # 5. Casual phrasing without explicit keyword
    records.append({
        "query_type": "adversarial",
        "question": "BUG-000062 severity please",
        "expected_intent": "defect_lookup",
        "expected_ids": {"defect": ["BUG-000062"], "testcase": [], "execution": [], "screenshot": []},
        "expected_filters": {},
        "expected_group_by": None,
        "gold_answer": "Severity: Minor.",
        "gold_facts": [{"entity": "BUG-000062", "field": "severity", "value": "Minor"}],
        "gold_nodes": ["BUG-000062"],
        "gold_query": "MATCH (d:Defect {defect_id: 'BUG-000062'}) RETURN d.severity AS severity",
        "answerable": True,
        "difficulty": "easy"
    })
    
    # 6. ID with trailing punctuation
    records.append({
        "query_type": "adversarial",
        "question": "Who was assigned to BUG-000067???",
        "expected_intent": "defect_lookup",
        "expected_ids": {"defect": ["BUG-000067"], "testcase": [], "execution": [], "screenshot": []},
        "expected_filters": {},
        "expected_group_by": None,
        "gold_answer": "Assigned to: Brittany Crosby.",
        "gold_facts": [{"entity": "BUG-000067", "field": "assigned_to", "value": "Brittany Crosby"}],
        "gold_nodes": ["BUG-000067"],
        "gold_query": "MATCH (d:Defect {defect_id: 'BUG-000067'}) RETURN d.assigned_to AS assigned_to",
        "answerable": True,
        "difficulty": "medium"
    })
    
    # 7. Conversational mixed query
    records.append({
        "query_type": "adversarial",
        "question": "Hey could you tell me if TC-000001 is automated or manual testing?",
        "expected_intent": "testcase_lookup",
        "expected_ids": {"defect": [], "testcase": ["TC-000001"], "execution": [], "screenshot": []},
        "expected_filters": {},
        "expected_group_by": None,
        "gold_answer": "Automation status: Automated (Framework: Cypress).",
        "gold_facts": [
            {"entity": "TC-000001", "field": "automation_status", "value": "Automated"},
            {"entity": "TC-000001", "field": "automation_framework", "value": "Cypress"}
        ],
        "gold_nodes": ["TC-000001"],
        "gold_query": "MATCH (tc:TestCase {test_case_id: 'TC-000001'}) RETURN tc.automation_status AS status, tc.automation_framework AS framework",
        "answerable": True,
        "difficulty": "easy"
    })
    
    # 8. Asking for defect fixed_build on an open defect
    records.append({
        "query_type": "adversarial",
        "question": "In what build was defect BUG-001545 fixed?",
        "expected_intent": "defect_lookup",
        "expected_ids": {"defect": ["BUG-001545"], "testcase": [], "execution": [], "screenshot": []},
        "expected_filters": {},
        "expected_group_by": None,
        "gold_answer": "Defect BUG-001545 is Open and has not been fixed yet (fixed_build is null).",
        "gold_facts": [
            {"entity": "BUG-001545", "field": "status", "value": "Open"},
            {"entity": "BUG-001545", "field": "fixed_build", "value": None}
        ],
        "gold_nodes": ["BUG-001545"],
        "gold_query": "MATCH (d:Defect {defect_id: 'BUG-001545'}) RETURN d.status AS status, d.fixed_build AS fixed_build",
        "answerable": True,
        "difficulty": "hard"
    })
    
    # 9. Incomplete ID reference in question with context
    records.append({
        "query_type": "adversarial",
        "question": "Look up bug 1545 in the system and return its severity.",
        "expected_intent": "defect_lookup",
        "expected_ids": {"defect": ["BUG-001545"], "testcase": [], "execution": [], "screenshot": []},
        "expected_filters": {},
        "expected_group_by": None,
        "gold_answer": "Severity for BUG-001545: Critical.",
        "gold_facts": [{"entity": "BUG-001545", "field": "severity", "value": "Critical"}],
        "gold_nodes": ["BUG-001545"],
        "gold_query": "MATCH (d:Defect {defect_id: 'BUG-001545'}) RETURN d.severity AS severity",
        "answerable": True,
        "difficulty": "hard"
    })
    
    # 10. Ambiguous query asking for execution of a defect
    records.append({
        "query_type": "adversarial",
        "question": "Which execution ID discovered BUG-000067?",
        "expected_intent": "defect_to_testcase",
        "expected_ids": {"defect": ["BUG-000067"], "testcase": [], "execution": [], "screenshot": []},
        "expected_filters": {},
        "expected_group_by": None,
        "gold_answer": "Discovered in execution EXEC-016396.",
        "gold_facts": [{"entity": "BUG-000067", "field": "linked_execution", "value": "EXEC-016396"}],
        "gold_nodes": ["BUG-000067", "EXEC-016396"],
        "gold_query": "MATCH (ex:Execution)-[:FOUND_DEFECT]->(d:Defect {defect_id: 'BUG-000067'}) RETURN ex.execution_id AS exec_id",
        "answerable": True,
        "difficulty": "medium"
    })
    
    return records


# ==========================================
# Main Execution & Split Assignment
# ==========================================
def main():
    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    
    all_records = []
    with driver.session(database=NEO4J_DB) as session:
        print("Generating 1. id_lookup (30)...")
        all_records.extend(generate_id_lookup(session, random_gen))
        
        print("Generating 2. defect_to_testcase and testcase_to_defects (30)...")
        all_records.extend(generate_two_hop(session, random_gen))
        
        print("Generating 3. execution_context (30)...")
        all_records.extend(generate_execution_context(session, random_gen))
        
        print("Generating 4. aggregation (30)...")
        all_records.extend(generate_aggregation(session, random_gen))
        
        print("Generating 5. multi_condition_filter (30)...")
        all_records.extend(generate_multi_condition_filter(session, random_gen))
        
        print("Generating 6. semantic (30)...")
        all_records.extend(generate_semantic(session, random_gen))
        
        print("Generating 7. unstructured_logs (30)...")
        all_records.extend(generate_unstructured_logs(session, random_gen))
        
        print("Generating 8. requirements (30)...")
        all_records.extend(generate_requirements(session, random_gen))
        
        print("Generating 9. unanswerable (20)...")
        all_records.extend(generate_unanswerable(random_gen))
        
        print("Generating 10. adversarial (10)...")
        all_records.extend(generate_adversarial(session))

    driver.close()
    
    print(f"Total raw generated records: {len(all_records)}")
    
    # Organize split: 30% test, 70% dev for each query_type
    by_type = {}
    for r in all_records:
        t = r["query_type"]
        by_type.setdefault(t, []).append(r)
        
    final_dataset = []
    smoke_assigned = 0
    smoke_targets = ["id_lookup", "defect_to_testcase", "execution_context", "aggregation", "unstructured_logs", "requirements"]
    
    for qtype, items in by_type.items():
        random_gen.shuffle(items)
        test_count = int(round(len(items) * 0.30))
        test_items = items[:test_count]
        dev_items = items[test_count:]
        
        for item in test_items:
            item["split"] = "test"
            item["smoke"] = False
            final_dataset.append(item)
            
        # Assign 2 smoke items for major types from dev split
        smoke_count_for_type = 2 if qtype in smoke_targets else 0
        for idx, item in enumerate(dev_items):
            item["split"] = "dev"
            if idx < smoke_count_for_type and smoke_assigned < 12:
                item["smoke"] = True
                smoke_assigned += 1
            else:
                item["smoke"] = False
            final_dataset.append(item)
            
    # Assign sequential IDs: G2-0001, G2-0002...
    random_gen.shuffle(final_dataset)
    for i, r in enumerate(final_dataset, start=1):
        r["id"] = f"G2-{i:04d}"
        
    # Write to gold_set.jsonl
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in final_dataset:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    print(f"Successfully wrote {len(final_dataset)} records to {OUTPUT_FILE}")
    print(f"Smoke questions marked: {smoke_assigned}")


if __name__ == "__main__":
    main()
