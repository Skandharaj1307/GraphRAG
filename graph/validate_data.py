import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# File paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

TESTCASES_FILE = BASE_DIR / "dataset" / "structured" / "testcases.csv"
EXECUTIONS_FILE = BASE_DIR / "dataset" / "structured" / "test_execution.csv"
DEFECTS_FILE = BASE_DIR / "dataset" / "structured" / "defects.csv"


# ---------------------------------------------------------
# Expected columns
# ---------------------------------------------------------

TESTCASE_COLUMNS = {
    "test_case_id",
    "requirement_id",
    "epic",
    "story",
    "module",
    "submodule",
    "feature",
    "priority",
    "severity",
    "risk",
    "component",
    "precondition",
    "test_steps",
    "expected_result",
    "actual_result",
    "status",
    "automation_status",
    "automation_framework",
    "execution_frequency",
    "tester",
    "created_date",
    "updated_date",
    "release",
    "environment",
    "acceptance_criteria",
}

EXECUTION_COLUMNS = {
    "execution_id",
    "test_case_id",
    "build_number",
    "execution_date",
    "tester",
    "environment",
    "browser",
    "operating_system",
    "execution_time_seconds",
    "status",
    "execution_notes",
}

DEFECT_COLUMNS = {
    "defect_id",
    "linked_test_case",
    "linked_execution",
    "title",
    "description",
    "severity",
    "priority",
    "module",
    "status",
    "assigned_to",
    "reported_by",
    "created_date",
    "resolved_date",
    "root_cause",
    "bug_type",
    "reproducibility",
    "found_in_build",
    "fixed_build",
    "regression",
    "environment",
    "developer",
    "comments",
    "fix_version",
}


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def clean_id(value):
    """Convert an ID to a clean string."""
    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def check_columns(df, expected_columns, name):
    """Check whether the CSV has the expected columns."""

    actual_columns = set(df.columns)

    missing = expected_columns - actual_columns
    extra = actual_columns - expected_columns

    print(f"\n{name} column check")

    if not missing and not extra:
        print("  ✓ Columns are correct")

    if missing:
        print("  ✗ Missing columns:")
        for column in sorted(missing):
            print(f"      {column}")

    if extra:
        print("  ! Extra columns:")
        for column in sorted(extra):
            print(f"      {column}")


def check_duplicate_ids(df, column, name):
    """Check duplicate primary IDs."""

    ids = df[column].dropna().astype(str).str.strip()

    duplicates = ids[ids.duplicated()].unique()

    print(f"\n{name} duplicate ID check")

    if len(duplicates) == 0:
        print("  ✓ No duplicate IDs")
    else:
        print(f"  ✗ Found {len(duplicates)} duplicate IDs")
        print("  Sample:", list(duplicates[:10]))


def check_missing_ids(df, column, name):
    """Check missing primary IDs."""

    missing = df[column].isna() | (
        df[column].astype(str).str.strip() == ""
    )

    count = missing.sum()

    print(f"\n{name} missing ID check")

    if count == 0:
        print("  ✓ No missing IDs")
    else:
        print(f"  ✗ {count} rows have missing IDs")


# ---------------------------------------------------------
# Main validation
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("TEST MANAGEMENT DATASET VALIDATION")
    print("=" * 70)

    # -----------------------------------------------------
    # Load CSVs
    # -----------------------------------------------------

    print("\nLoading datasets...")

    testcases = pd.read_csv(TESTCASES_FILE)
    executions = pd.read_csv(EXECUTIONS_FILE)
    defects = pd.read_csv(DEFECTS_FILE)

    print("✓ All CSV files loaded successfully")


    # -----------------------------------------------------
    # Dataset sizes
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("DATASET SIZES")
    print("=" * 70)

    print(f"Test cases : {len(testcases):,}")
    print(f"Executions : {len(executions):,}")
    print(f"Defects    : {len(defects):,}")


    # -----------------------------------------------------
    # Column validation
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("COLUMN VALIDATION")
    print("=" * 70)

    check_columns(
        testcases,
        TESTCASE_COLUMNS,
        "testcases.csv"
    )

    check_columns(
        executions,
        EXECUTION_COLUMNS,
        "test_execution.csv"
    )

    check_columns(
        defects,
        DEFECT_COLUMNS,
        "defects.csv"
    )


    # -----------------------------------------------------
    # Primary key validation
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("PRIMARY KEY VALIDATION")
    print("=" * 70)

    check_missing_ids(
        testcases,
        "test_case_id",
        "TestCase"
    )

    check_duplicate_ids(
        testcases,
        "test_case_id",
        "TestCase"
    )

    check_missing_ids(
        executions,
        "execution_id",
        "Execution"
    )

    check_duplicate_ids(
        executions,
        "execution_id",
        "Execution"
    )

    check_missing_ids(
        defects,
        "defect_id",
        "Defect"
    )

    check_duplicate_ids(
        defects,
        "defect_id",
        "Defect"
    )


    # -----------------------------------------------------
    # Build ID sets
    # -----------------------------------------------------

    testcase_ids = set(
        testcases["test_case_id"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    execution_ids = set(
        executions["execution_id"]
        .dropna()
        .astype(str)
        .str.strip()
    )


    # -----------------------------------------------------
    # Execution → TestCase
    # -----------------------------------------------------

    execution_testcases = set(
        executions["test_case_id"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    missing_execution_testcases = (
        execution_testcases - testcase_ids
    )

    print("\n" + "=" * 70)
    print("EXECUTION → TEST CASE")
    print("=" * 70)

    print(
        f"Unique test cases referenced by executions: "
        f"{len(execution_testcases):,}"
    )

    print(
        f"Missing TestCase references: "
        f"{len(missing_execution_testcases):,}"
    )

    if missing_execution_testcases:
        print("\nSample missing IDs:")
        for value in list(missing_execution_testcases)[:10]:
            print(" ", value)
    else:
        print("✓ All execution → test case references are valid")


    # -----------------------------------------------------
    # Defect → TestCase
    # -----------------------------------------------------

    defect_testcases = set(
        defects["linked_test_case"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    missing_defect_testcases = (
        defect_testcases - testcase_ids
    )

    print("\n" + "=" * 70)
    print("DEFECT → TEST CASE")
    print("=" * 70)

    print(
        f"Unique test cases referenced by defects: "
        f"{len(defect_testcases):,}"
    )

    print(
        f"Missing TestCase references: "
        f"{len(missing_defect_testcases):,}"
    )

    if missing_defect_testcases:
        print("\nSample missing IDs:")
        for value in list(missing_defect_testcases)[:10]:
            print(" ", value)
    else:
        print("✓ All defect → test case references are valid")


    # -----------------------------------------------------
    # Defect → Execution
    # -----------------------------------------------------

    defect_executions = set(
        defects["linked_execution"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    missing_defect_executions = (
        defect_executions - execution_ids
    )

    print("\n" + "=" * 70)
    print("DEFECT → EXECUTION")
    print("=" * 70)

    print(
        f"Unique executions referenced by defects: "
        f"{len(defect_executions):,}"
    )

    print(
        f"Missing Execution references: "
        f"{len(missing_defect_executions):,}"
    )

    if missing_defect_executions:
        print("\nSample missing IDs:")
        for value in list(missing_defect_executions)[:10]:
            print(" ", value)
    else:
        print("✓ All defect → execution references are valid")


    # -----------------------------------------------------
    # Relationship consistency
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("CROSS-DATA CONSISTENCY")
    print("=" * 70)

    # Check whether a defect's testcase and execution point
    # to the same testcase.

    merged = defects[
        ["defect_id", "linked_test_case", "linked_execution"]
    ].merge(
        executions[
            ["execution_id", "test_case_id"]
        ],
        left_on="linked_execution",
        right_on="execution_id",
        how="left"
    )

    valid_relationships = (
        merged["linked_test_case"].astype(str).str.strip()
        ==
        merged["test_case_id"].astype(str).str.strip()
    )

    # Ignore rows where execution was missing
    execution_exists = merged["test_case_id"].notna()

    inconsistent = (
        merged[execution_exists]
        [~valid_relationships[execution_exists]]
    )

    print(
        f"Defects with both TestCase and Execution: "
        f"{execution_exists.sum():,}"
    )

    print(
        f"Inconsistent TestCase ↔ Execution links: "
        f"{len(inconsistent):,}"
    )

    if len(inconsistent) > 0:

        print("\nSample inconsistencies:")

        print(
            inconsistent[
                [
                    "defect_id",
                    "linked_test_case",
                    "linked_execution",
                    "test_case_id",
                ]
            ].head(10).to_string(index=False)
        )

    else:
        print(
            "✓ Defect → Execution → TestCase relationships are consistent"
        )


    # -----------------------------------------------------
    # Useful value statistics
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("IMPORTANT VALUE STATISTICS")
    print("=" * 70)

    print("\nTestCase status:")
    print(
        testcases["status"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nExecution status:")
    print(
        executions["status"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nDefect status:")
    print(
        defects["status"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nDefect severity:")
    print(
        defects["severity"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nDefect modules:")
    print(
        defects["module"]
        .value_counts(dropna=False)
        .head(15)
        .to_string()
    )


    # -----------------------------------------------------
    # Final summary
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

    if (
        len(missing_execution_testcases) == 0
        and len(missing_defect_testcases) == 0
        and len(missing_defect_executions) == 0
        and len(inconsistent) == 0
    ):
        print(
            "\n✓ Dataset relationships are ready for graph construction."
        )
    else:
        print(
            "\n⚠ Some relationship problems were found."
        )
        print(
            "We should inspect them before inserting the data into Neo4j."
        )


if __name__ == "__main__":
    main()