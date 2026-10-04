import json
from pathlib import Path

from neo4j import GraphDatabase


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SCREENSHOT_DIR = (
    BASE_DIR
    / "dataset"
    / "unstructured"
    / "screenshots"
)

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "qazwsxedc"

BATCH_SIZE = 500


# ============================================================
# LOAD JSON FILES
# ============================================================

def load_screenshot_records():

    files = sorted(
        SCREENSHOT_DIR.glob("ocr_batch_*.json")
    )

    if not files:
        raise FileNotFoundError(
            f"No screenshot JSON files found in:\n"
            f"{SCREENSHOT_DIR}"
        )

    print(f"Found {len(files)} screenshot files")

    all_records = []

    for file_path in files:

        print(f"Reading: {file_path.name}")

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(
                f"{file_path.name} does not contain "
                f"a JSON list."
            )

        print(
            f"  Records: {len(data):,}"
        )

        for index, record in enumerate(data):

            record["_source_file"] = file_path.name
            record["_source_index"] = index

            all_records.append(record)

    print(
        f"\nTotal screenshot records: "
        f"{len(all_records):,}"
    )

    return all_records


# ============================================================
# PREPARE RECORD
# ============================================================

def prepare_record(record):

    bug_id = record.get(
        "bug_id",
        ""
    )

    execution_id = record.get(
        "execution_id",
        ""
    )

    test_case_id = record.get(
        "test_case_id",
        ""
    )

    source_file = record.get(
        "_source_file",
        ""
    )

    source_index = record.get(
        "_source_index",
        0
    )

    # --------------------------------------------------------
    # Deterministic screenshot ID
    # --------------------------------------------------------

    screenshot_id = (
        f"SCR-"
        f"{Path(source_file).stem}-"
        f"{source_index:04d}"
    )

    # --------------------------------------------------------
    # field_values is a dictionary.
    # Neo4j node properties cannot directly store maps,
    # so store it as JSON text.
    # --------------------------------------------------------

    field_values = record.get(
        "field_values",
        {}
    )

    if field_values is None:
        field_values = {}

    field_values_json = json.dumps(
        field_values,
        ensure_ascii=False
    )

    return {

        # ----------------------------------------------------
        # Screenshot identity
        # ----------------------------------------------------

        "screenshot_id": screenshot_id,

        # ----------------------------------------------------
        # Existing graph IDs
        # ----------------------------------------------------

        "bug_id": bug_id,
        "execution_id": execution_id,
        "test_case_id": test_case_id,

        # ----------------------------------------------------
        # Screenshot information
        # ----------------------------------------------------

        "screen_name": record.get(
            "screen_name",
            ""
        ),

        "module": record.get(
            "module",
            ""
        ),

        # ----------------------------------------------------
        # UI elements
        # ----------------------------------------------------

        "buttons": record.get(
            "buttons",
            []
        ) or [],

        "labels": record.get(
            "labels",
            []
        ) or [],

        "menus": record.get(
            "menus",
            []
        ) or [],

        "dialog_boxes": record.get(
            "dialog_boxes",
            []
        ) or [],

        "tables": record.get(
            "tables",
            []
        ) or [],

        # ----------------------------------------------------
        # Messages
        # ----------------------------------------------------

        "warning_messages": record.get(
            "warning_messages",
            []
        ) or [],

        "error_messages": record.get(
            "error_messages",
            []
        ) or [],

        # ----------------------------------------------------
        # Field values
        # ----------------------------------------------------

        "field_values": field_values_json,

        # ----------------------------------------------------
        # Other information
        # ----------------------------------------------------

        "captured_time": record.get(
            "captured_time",
            ""
        ),

        "user_action": record.get(
            "user_action",
            ""
        ),

        # ----------------------------------------------------
        # Source tracking
        # ----------------------------------------------------

        "source_file": source_file,

        "source_index": source_index,
    }


# ============================================================
# CREATE SCREENSHOT NODES + RELATIONSHIPS
# ============================================================

CREATE_SCREENSHOTS_QUERY = """

UNWIND $screenshots AS s

MERGE (
    sc:Screenshot {
        screenshot_id: s.screenshot_id
    }
)

SET

    sc.bug_id = s.bug_id,

    sc.execution_id = s.execution_id,

    sc.test_case_id = s.test_case_id,

    sc.screen_name = s.screen_name,

    sc.module = s.module,

    sc.buttons = s.buttons,

    sc.labels = s.labels,

    sc.menus = s.menus,

    sc.dialog_boxes = s.dialog_boxes,

    sc.tables = s.tables,

    sc.warning_messages = s.warning_messages,

    sc.error_messages = s.error_messages,

    sc.field_values = s.field_values,

    sc.captured_time = s.captured_time,

    sc.user_action = s.user_action,

    sc.source_file = s.source_file,

    sc.source_index = s.source_index

WITH sc, s


// ========================================================
// TestCase → Screenshot
// ========================================================

OPTIONAL MATCH (
    t:TestCase {
        test_case_id: s.test_case_id
    }
)

FOREACH (_ IN CASE
    WHEN t IS NOT NULL THEN [1]
    ELSE []
END |

    MERGE (
        t
    )-[:HAS_SCREENSHOT]->(
        sc
    )
)

WITH sc, s


// ========================================================
// Execution → Screenshot
// ========================================================

OPTIONAL MATCH (
    e:Execution {
        execution_id: s.execution_id
    }
)

FOREACH (_ IN CASE
    WHEN e IS NOT NULL THEN [1]
    ELSE []
END |

    MERGE (
        e
    )-[:CAPTURED_SCREENSHOT]->(
        sc
    )
)

WITH sc, s


// ========================================================
// Defect → Screenshot
// ========================================================

OPTIONAL MATCH (
    d:Defect {
        defect_id: s.bug_id
    }
)

FOREACH (_ IN CASE
    WHEN d IS NOT NULL THEN [1]
    ELSE []
END |

    MERGE (
        d
    )-[:HAS_SCREENSHOT]->(
        sc
    )
)

RETURN count(sc) AS processed

"""


# ============================================================
# GRAPH VALIDATION
# ============================================================

VALIDATION_QUERY = """

RETURN

    count {
        MATCH (s:Screenshot)
    }
    AS screenshots,

    count {
        MATCH
        (:TestCase)
        -[:HAS_SCREENSHOT]->
        (:Screenshot)
    }
    AS testcase_screenshot_relationships,

    count {
        MATCH
        (:Execution)
        -[:CAPTURED_SCREENSHOT]->
        (:Screenshot)
    }
    AS execution_screenshot_relationships,

    count {
        MATCH
        (:Defect)
        -[:HAS_SCREENSHOT]->
        (:Screenshot)
    }
    AS defect_screenshot_relationships

"""


# ============================================================
# REFERENCE VALIDATION
# ============================================================

REFERENCE_VALIDATION_QUERY = """

MATCH (s:Screenshot)

OPTIONAL MATCH (
    t:TestCase {
        test_case_id: s.test_case_id
    }
)

OPTIONAL MATCH (
    e:Execution {
        execution_id: s.execution_id
    }
)

OPTIONAL MATCH (
    d:Defect {
        defect_id: s.bug_id
    }
)

RETURN

    count(s)
    AS total_screenshots,

    sum(
        CASE
            WHEN t IS NULL THEN 1
            ELSE 0
        END
    )
    AS missing_testcases,

    sum(
        CASE
            WHEN e IS NULL THEN 1
            ELSE 0
        END
    )
    AS missing_executions,

    sum(
        CASE
            WHEN d IS NULL THEN 1
            ELSE 0
        END
    )
    AS missing_defects

"""


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("SCREENSHOT GRAPH BUILD")
    print("=" * 70)

    # --------------------------------------------------------
    # Load all screenshot JSON files
    # --------------------------------------------------------

    raw_records = load_screenshot_records()

    # --------------------------------------------------------
    # Prepare records
    # --------------------------------------------------------

    screenshots = [
        prepare_record(record)
        for record in raw_records
    ]

    print(
        f"\nPrepared "
        f"{len(screenshots):,} screenshot records"
    )

    # --------------------------------------------------------
    # Connect to Neo4j
    # --------------------------------------------------------

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USER,
            NEO4J_PASSWORD
        )
    )

    try:

        # ====================================================
        # CONNECTION TEST
        # ====================================================

        with driver.session() as session:

            result = session.run(
                "RETURN 1 AS result"
            )

            value = result.single()["result"]

            print(
                f"\nNeo4j connection successful: "
                f"{value}"
            )

        # ====================================================
        # PROCESS SCREENSHOTS IN BATCHES
        # ====================================================

        total = len(screenshots)

        print(
            f"\nLoading {total:,} screenshots..."
        )

        for start in range(
            0,
            total,
            BATCH_SIZE
        ):

            end = min(
                start + BATCH_SIZE,
                total
            )

            batch = screenshots[
                start:end
            ]

            with driver.session() as session:

                result = session.run(
                    CREATE_SCREENSHOTS_QUERY,
                    screenshots=batch
                )

                result.single()

            print(
                f"Processed "
                f"{end:,} / {total:,}"
            )

        # ====================================================
        # GRAPH VALIDATION
        # ====================================================

        print("\n" + "-" * 70)
        print("GRAPH VALIDATION")
        print("-" * 70)

        with driver.session() as session:

            result = session.run(
                VALIDATION_QUERY
            )

            record = result.single()

            print(
                f"Screenshot nodes              : "
                f"{record['screenshots']:,}"
            )

            print(
                f"TestCase → Screenshot         : "
                f"{record['testcase_screenshot_relationships']:,}"
            )

            print(
                f"Execution → Screenshot        : "
                f"{record['execution_screenshot_relationships']:,}"
            )

            print(
                f"Defect → Screenshot           : "
                f"{record['defect_screenshot_relationships']:,}"
            )

        # ====================================================
        # REFERENCE VALIDATION
        # ====================================================

        print("\n" + "-" * 70)
        print("REFERENCE VALIDATION")
        print("-" * 70)

        with driver.session() as session:

            result = session.run(
                REFERENCE_VALIDATION_QUERY
            )

            record = result.single()

            print(
                f"Total screenshots : "
                f"{record['total_screenshots']:,}"
            )

            print(
                f"Missing TestCases : "
                f"{record['missing_testcases']:,}"
            )

            print(
                f"Missing Executions: "
                f"{record['missing_executions']:,}"
            )

            print(
                f"Missing Defects   : "
                f"{record['missing_defects']:,}"
            )

    finally:

        driver.close()

    # ========================================================
    # COMPLETION
    # ========================================================

    print("\n" + "=" * 70)
    print("✓ SCREENSHOT GRAPH BUILD COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()