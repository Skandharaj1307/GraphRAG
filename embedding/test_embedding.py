import pandas as pd

from .config import TESTCASES_FILE, DEFECTS_FILE
from .text_builder import (
    build_testcase_text,
    build_defect_text,
)
from .embedder import EmbeddingModel


def main():

    print("=" * 60)
    print("PHASE 1 - PART 1 EMBEDDING TEST")
    print("=" * 60)

    # -----------------------------------------
    # Load datasets
    # -----------------------------------------

    testcases = pd.read_csv(TESTCASES_FILE)
    defects = pd.read_csv(DEFECTS_FILE)

    print("\nDatasets loaded:")
    print(f"  TestCases : {len(testcases):,}")
    print(f"  Defects   : {len(defects):,}")

    # -----------------------------------------
    # Select one real record
    # -----------------------------------------

    testcase = testcases.iloc[0]
    defect = defects.iloc[0]

    # -----------------------------------------
    # Build semantic text
    # -----------------------------------------

    testcase_text = build_testcase_text(testcase)
    defect_text = build_defect_text(defect)

    print("\n" + "=" * 60)
    print("TESTCASE EMBEDDING TEXT")
    print("=" * 60)

    print(testcase_text)

    print("\n" + "=" * 60)
    print("DEFECT EMBEDDING TEXT")
    print("=" * 60)

    print(defect_text)

    # -----------------------------------------
    # Load embedding model
    # -----------------------------------------

    embedder = EmbeddingModel()

    # -----------------------------------------
    # Generate embeddings
    # -----------------------------------------

    testcase_embedding = embedder.embed_document(
        testcase_text
    )

    defect_embedding = embedder.embed_document(
        defect_text
    )

    # -----------------------------------------
    # Validate
    # -----------------------------------------

    print("\n" + "=" * 60)
    print("EMBEDDING VALIDATION")
    print("=" * 60)

    print(
        f"TestCase ID: "
        f"{testcase['test_case_id']}"
    )

    print(
        f"TestCase embedding shape: "
        f"{testcase_embedding.shape}"
    )

    print(
        f"Defect ID: "
        f"{defect['defect_id']}"
    )

    print(
        f"Defect embedding shape: "
        f"{defect_embedding.shape}"
    )

    print(
        f"TestCase embedding dimension: "
        f"{len(testcase_embedding)}"
    )

    print(
        f"Defect embedding dimension: "
        f"{len(defect_embedding)}"
    )

    print(
        f"TestCase embedding norm: "
        f"{(testcase_embedding ** 2).sum() ** 0.5:.6f}"
    )

    print(
        f"Defect embedding norm: "
        f"{(defect_embedding ** 2).sum() ** 0.5:.6f}"
    )

    # -----------------------------------------
    # Final checks
    # -----------------------------------------

    assert len(testcase_embedding) == 1024
    assert len(defect_embedding) == 1024

    print("\n✓ TestCase embedding generated")
    print("✓ Defect embedding generated")
    print("✓ Embedding dimension = 1024")
    print("✓ Part 1 embedding test successful")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()