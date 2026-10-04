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


# --------------------------------------------------
# Neo4j configuration
# --------------------------------------------------

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "qazwsxedc"


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

    with driver.session() as session:

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

    with driver.session() as session:

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

    with driver.session() as session:

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
# Main
# --------------------------------------------------

def main():

    print("=" * 60)
    print("FULL GRAPH BUILD")
    print("=" * 60)

    # Load complete datasets
    testcases, executions, defects = load_data()

    print("\nDataset:")
    print(f"  TestCases : {len(testcases):,}")
    print(f"  Executions: {len(executions):,}")
    print(f"  Defects   : {len(defects):,}")

    # Connect to Neo4j
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USER,
            NEO4J_PASSWORD
        )
    )

    try:

        # Test connection
        with driver.session() as session:

            result = session.run(
                "RETURN 1 AS result"
            )

            value = result.single()["result"]

            print(
                f"\nNeo4j connection successful: {value}"
            )

        # Build TestCase layer
        create_testcase_nodes(
            driver,
            testcases
        )

        # Build Execution layer
        create_execution_nodes(
            driver,
            executions
        )

        # Build Defect layer
        create_defect_nodes(
            driver,
            defects
        )

    finally:

        driver.close()

    print("\n" + "=" * 60)
    print("✓ FULL GRAPH BUILD COMPLETED")
    print("=" * 60)


# --------------------------------------------------
# Program entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()