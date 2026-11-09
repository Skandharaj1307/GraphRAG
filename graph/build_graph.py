import re
import pandas as pd
from pathlib import Path
from neo4j import GraphDatabase


# --------------------------------------------------
# Project paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

TESTCASES_FILE = BASE_DIR / "dataset" / "structured" / "testcases.csv"
EXECUTIONS_FILE = BASE_DIR / "dataset" / "structured" / "test_execution.csv"
DEFECTS_FILE = BASE_DIR / "dataset" / "structured" / "defects.csv"
FAILURE_LOGS_DIR = BASE_DIR / "dataset" / "unstructured" / "failure_logs"
SRS_FILE = BASE_DIR / "dataset" / "unstructured" / "srs" / "srs_document.pdf"


# --------------------------------------------------
# Neo4j configuration
# --------------------------------------------------

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "qazwsxedc"
TARGET_DATABASE = "graphragv2"


# --------------------------------------------------
# Load datasets
# --------------------------------------------------

def load_data():

    testcases = pd.read_csv(TESTCASES_FILE)
    executions = pd.read_csv(EXECUTIONS_FILE)
    defects = pd.read_csv(DEFECTS_FILE)

    return testcases, executions, defects


# --------------------------------------------------
# Create TestCase nodes
# --------------------------------------------------

def create_testcase_nodes(driver, testcases):

    query = """
    UNWIND $testcases AS tc

    MERGE (t:TestCase {
        test_case_id: tc.test_case_id
    })

    SET
        t.requirement_id = tc.requirement_id,
        t.epic = tc.epic,
        t.story = tc.story,
        t.module = tc.module,
        t.submodule = tc.submodule,
        t.feature = tc.feature,
        t.priority = tc.priority,
        t.severity = tc.severity,
        t.risk = tc.risk,
        t.component = tc.component,
        t.precondition = tc.precondition,
        t.test_steps = tc.test_steps,
        t.expected_result = tc.expected_result,
        t.actual_result = tc.actual_result,
        t.status = tc.status,
        t.automation_status = tc.automation_status,
        t.automation_framework = tc.automation_framework,
        t.execution_frequency = tc.execution_frequency,
        t.tester = tc.tester,
        t.created_date = tc.created_date,
        t.updated_date = tc.updated_date,
        t.release = tc.release,
        t.environment = tc.environment,
        t.acceptance_criteria = tc.acceptance_criteria
    """

    records = testcases.to_dict("records")

    with driver.session(database=TARGET_DATABASE) as session:

        session.run(
            query,
            testcases=records
        )

    print(
        f"✓ Created/updated {len(records):,} TestCase nodes"
    )


# --------------------------------------------------
# Create Execution nodes and relationships
# --------------------------------------------------

def create_execution_nodes(driver, executions):

    query = """
    UNWIND $executions AS ex

    MERGE (e:Execution {
        execution_id: ex.execution_id
    })

    SET
        e.test_case_id = ex.test_case_id,
        e.build_number = ex.build_number,
        e.execution_date = ex.execution_date,
        e.tester = ex.tester,
        e.environment = ex.environment,
        e.browser = ex.browser,
        e.operating_system = ex.operating_system,
        e.execution_time_seconds = ex.execution_time_seconds,
        e.status = ex.status,
        e.execution_notes = ex.execution_notes

    WITH e, ex

    MATCH (t:TestCase {
        test_case_id: ex.test_case_id
    })

    MERGE (t)-[:HAS_EXECUTION]->(e)
    """

    records = executions.to_dict("records")

    with driver.session(database=TARGET_DATABASE) as session:

        session.run(
            query,
            executions=records
        )

    print(
        f"✓ Created/updated {len(records):,} Execution nodes"
    )

    print(
        "✓ Created HAS_EXECUTION relationships"
    )


# --------------------------------------------------
# Create Defect nodes and relationships
# --------------------------------------------------

def create_defect_nodes(driver, defects):

    query = """
    UNWIND $defects AS d

    MERGE (bug:Defect {
        defect_id: d.defect_id
    })

    SET
        bug.linked_test_case = d.linked_test_case,
        bug.linked_execution = d.linked_execution,
        bug.title = d.title,
        bug.description = d.description,
        bug.severity = d.severity,
        bug.priority = d.priority,
        bug.module = d.module,
        bug.status = d.status,
        bug.assigned_to = d.assigned_to,
        bug.reported_by = d.reported_by,
        bug.created_date = d.created_date,
        bug.resolved_date = d.resolved_date,
        bug.root_cause = d.root_cause,
        bug.bug_type = d.bug_type,
        bug.reproducibility = d.reproducibility,
        bug.found_in_build = d.found_in_build,
        bug.fixed_build = d.fixed_build,
        bug.regression = d.regression,
        bug.environment = d.environment,
        bug.developer = d.developer,
        bug.comments = d.comments,
        bug.fix_version = d.fix_version

    WITH bug, d

    MATCH (t:TestCase {
        test_case_id: d.linked_test_case
    })

    MERGE (t)-[:HAS_DEFECT]->(bug)

    WITH bug, d

    MATCH (e:Execution {
        execution_id: d.linked_execution
    })

    MERGE (e)-[:FOUND_DEFECT]->(bug)
    """

    records = defects.to_dict("records")

    with driver.session(database=TARGET_DATABASE) as session:

        session.run(
            query,
            defects=records
        )

    print(
        f"✓ Created/updated {len(records):,} Defect nodes"
    )

    print(
        "✓ Created HAS_DEFECT relationships"
    )

    print(
        "✓ Created FOUND_DEFECT relationships"
    )


# --------------------------------------------------
# Parse and Ingest Failure Logs (Phase 6)
# --------------------------------------------------

def parse_failure_log_block(block: str) -> dict:
    """
    Parse a single failure log block into structured attributes.
    Extracts execution_id, defect_id, test_case_id, exception_name,
    stack_frames, message, database_error, http_status, and resolution_hint.
    """
    lines = block.split("\n")
    header = lines[0] if lines else ""
    exec_m = re.search(r"Execution ID:\s*([A-Za-z0-9_\-]+)", header)
    if not exec_m:
        return None

    exec_id = exec_m.group(1).strip()
    bug_m = re.search(r"Bug ID:\s*([A-Za-z0-9_\-]+)", header)
    bug_id = bug_m.group(1).strip() if bug_m else None
    tc_m = re.search(r"Test Case ID:\s*([A-Za-z0-9_\-]+)", header)
    tc_id = tc_m.group(1).strip() if tc_m else None

    exc_m = re.search(r"\nException:\s*([^\r\n]+)", block)
    exc_name = exc_m.group(1).strip() if exc_m else None

    http_m = re.search(r"\nHTTP Status:\s*(\d+)", block)
    http_status = int(http_m.group(1)) if http_m else None

    tb_m = re.search(r"Python Traceback:\s*(.*?)(?=\n(?:Database Error|HTTP Status|Server Log|Exception):|\Z)", block, re.DOTALL)
    traceback_text = tb_m.group(1).strip() if tb_m else ""
    frames = re.findall(r'File "([^"]+)", line (\d+), in (\w+)', traceback_text)
    frame_list = [f"{file}:{line} in {func}" for file, line, func in frames]

    tb_lines = [l.strip() for l in traceback_text.split("\n") if l.strip()]
    exc_msg = tb_lines[-1] if tb_lines and ":" in tb_lines[-1] else exc_name

    db_m = re.search(r"Database Error:\s*(.*?)(?=\n(?:HTTP Status|Server Log|Exception):|\Z)", block, re.DOTALL)
    db_error = db_m.group(1).strip() if db_m else ""

    hint_m = re.search(r"Resolution Hint:\s*(.*?)(?=\Z)", block, re.DOTALL)
    hint = hint_m.group(1).strip() if hint_m else ""

    return {
        "log_id": f"LOG-{exec_id}",
        "execution_id": exec_id,
        "defect_id": bug_id,
        "test_case_id": tc_id,
        "exception_name": exc_name,
        "exception_message": exc_msg,
        "stack_frames": frame_list,
        "traceback": traceback_text,
        "database_error": db_error,
        "http_status": http_status,
        "resolution_hint": hint,
    }


def ingest_failure_logs(driver, database=TARGET_DATABASE, batch_size=500):
    """
    Ingest failure logs into (:LogChunk) nodes and link as
    (:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk). Idempotent via MERGE.
    """
    if not FAILURE_LOGS_DIR.exists():
        print(f"Warning: failure_logs directory not found at {FAILURE_LOGS_DIR}")
        return 0

    print("\n" + "=" * 60)
    print("PARSING FAILURE LOGS")
    print("=" * 60)

    all_logs = []
    log_files = sorted(FAILURE_LOGS_DIR.glob("*.txt"))
    for file_path in log_files:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        raw_blocks = text.split("======================================================================")
        for b in raw_blocks:
            if "Execution ID:" in b:
                parsed = parse_failure_log_block(b.strip())
                if parsed:
                    all_logs.append(parsed)

    print(f"✓ Parsed {len(all_logs):,} failure log blocks from {len(log_files)} files")

    constraint_cypher = """
    CREATE CONSTRAINT log_chunk_id IF NOT EXISTS
    FOR (lc:LogChunk) REQUIRE lc.log_id IS UNIQUE
    """

    ingest_cypher = """
    UNWIND $logs AS log
    MERGE (lc:LogChunk {log_id: log.log_id})
    SET lc.execution_id = log.execution_id,
        lc.defect_id = log.defect_id,
        lc.test_case_id = log.test_case_id,
        lc.exception_name = log.exception_name,
        lc.exception_message = log.exception_message,
        lc.stack_frames = log.stack_frames,
        lc.traceback = log.traceback,
        lc.database_error = log.database_error,
        lc.http_status = log.http_status,
        lc.resolution_hint = log.resolution_hint
    WITH lc, log
    MATCH (e:Execution {execution_id: log.execution_id})
    MERGE (e)-[:HAS_FAILURE_LOG]->(lc)
    """

    with driver.session(database=database) as session:
        try:
            session.run(constraint_cypher).consume()
        except Exception as e:
            print(f"Note on constraint: {e}")

        for i in range(0, len(all_logs), batch_size):
            batch = all_logs[i:i + batch_size]
            session.run(ingest_cypher, logs=batch).consume()
            print(f"LogChunk: {min(i + batch_size, len(all_logs)):,}/{len(all_logs):,}", end="\r")

    print(f"\n✓ Ingested/merged {len(all_logs):,} LogChunk nodes and HAS_FAILURE_LOG relationships")
    return len(all_logs)


# --------------------------------------------------
# Parse and Ingest SRS Requirements (Phase 6)
# --------------------------------------------------

def ingest_srs_requirements(driver, database=TARGET_DATABASE):
    """
    Extract sections and requirements from srs_document.pdf into
    (:Requirement {id, text, name, section}) linked as (:TestCase)-[:VERIFIES]->(:Requirement).
    Only links where a reliable match exists; reports unmatched items rather than guessing.
    Idempotent via MERGE.
    """
    if not SRS_FILE.exists():
        print(f"Warning: SRS PDF file not found at {SRS_FILE}")
        return 0, 0

    print("\n" + "=" * 60)
    print("PARSING SRS REQUIREMENTS DOCUMENT")
    print("=" * 60)

    try:
        from pypdf import PdfReader
    except ImportError:
        print("Error: pypdf is required to parse SRS document. Please run `pip install pypdf`.")
        return 0, 0

    reader = PdfReader(str(SRS_FILE))
    print(f"Reading SRS Document ({len(reader.pages)} pages)...")

    KNOWN_HEADINGS = [
        "Executive Summary", "Business Overview", "Functional Requirements",
        "Non Functional Requirements", "Business Rules", "Use Cases",
        "User Stories", "Acceptance Criteria", "Workflow Descriptions",
        "Architecture", "Data Flow", "ER Diagram descriptions",
        "API Specifications", "Security", "Performance", "Scalability",
        "Multi Company", "Multi Currency",
    ]

    sections = []
    current_section = None
    current_text = []

    for page in reader.pages:
        txt = page.extract_text() or ""
        for line in txt.split("\n"):
            line_clean = line.strip()
            matched_h = None
            for kh in KNOWN_HEADINGS:
                if line_clean == kh or line_clean.startswith(f"{kh} - Detailed"):
                    matched_h = line_clean
                    break
            if matched_h:
                if current_section and current_text:
                    sections.append({
                        "title": current_section,
                        "text": "\n".join(current_text).strip(),
                    })
                current_section = matched_h
                current_text = []
            else:
                if current_section:
                    current_text.append(line)

    if current_section and current_text:
        sections.append({
            "title": current_section,
            "text": "\n".join(current_text).strip(),
        })

    req_records = []
    for idx, sec in enumerate(sections, start=1):
        req_records.append({
            "id": f"SRS-SEC-{idx:03d}",
            "name": sec["title"],
            "text": sec["text"],
            "section": sec["title"].split(" - ")[0],
            "source": "srs_document.pdf",
        })

    print(f"✓ Extracted {len(req_records)} requirement sections from SRS document")

    srs_cypher = """
    UNWIND $reqs AS r
    MERGE (req:Requirement {requirement_id: r.id})
    SET req.id = r.id,
        req.name = r.name,
        req.text = r.text,
        req.section = r.section,
        req.source = r.source
    """

    with driver.session(database=database) as session:
        session.run(srs_cypher, reqs=req_records).consume()
        print(f"✓ Ingested/merged {len(req_records)} SRS Requirement nodes")

        link_cypher = """
        MATCH (t:TestCase)
        WHERE t.component IS NOT NULL
        MATCH (req:Requirement)
        WHERE req.source = 'srs_document.pdf' AND req.name CONTAINS t.component
        MERGE (t)-[v:VERIFIES]->(req)
        RETURN count(DISTINCT t) AS matched_tcs, count(DISTINCT req) AS matched_reqs
        """
        link_res = session.run(link_cypher).single()
        matched_tcs = link_res["matched_tcs"] if link_res else 0
        matched_reqs = link_res["matched_reqs"] if link_res else 0

        unmatched_srs = len(req_records) - matched_reqs
        print(f"✓ Reliable match linking: {matched_tcs:,} TestCases verified across {matched_reqs} SRS Requirements")
        print(f"✓ Unmatched SRS sections: {unmatched_srs} sections preserved unlinked (reported without guessing)")

    return len(req_records), matched_reqs


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    import sys

    print("=" * 60)
    print("GRAPH BUILD AND UNSTRUCTURED INGESTION")
    print("=" * 60)

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USER,
            NEO4J_PASSWORD
        )
    )

    try:
        with driver.session(database=TARGET_DATABASE) as session:
            result = session.run("RETURN 1 AS result")
            value = result.single()["result"]
            print(f"\nNeo4j connection successful to '{TARGET_DATABASE}': {value}")

        unstructured_only = "--unstructured" in sys.argv or "--logs-only" in sys.argv or "--srs-only" in sys.argv

        if not unstructured_only or "--structured" in sys.argv:
            testcases, executions, defects = load_data()
            create_testcase_nodes(driver, testcases)
            create_execution_nodes(driver, executions)
            create_defect_nodes(driver, defects)

        if not sys.argv[1:] or "--unstructured" in sys.argv or "--logs-only" in sys.argv:
            ingest_failure_logs(driver, database=TARGET_DATABASE)

        if not sys.argv[1:] or "--unstructured" in sys.argv or "--srs-only" in sys.argv:
            ingest_srs_requirements(driver, database=TARGET_DATABASE)

    finally:
        driver.close()

    print("\n" + "=" * 60)
    print("✓ GRAPH INGESTION PIPELINE COMPLETED")
    print("=" * 60)


# --------------------------------------------------
# Program entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()