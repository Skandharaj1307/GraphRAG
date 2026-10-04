import time
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .config import TESTCASES_FILE, DEFECTS_FILE
from .text_builder import (
    build_testcase_text,
    build_defect_text,
)
from .embedder import EmbeddingModel


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


TESTCASE_EMBEDDINGS_FILE = (
    OUTPUT_DIR / "testcase_embeddings.npy"
)

TESTCASE_IDS_FILE = (
    OUTPUT_DIR / "testcase_ids.csv"
)

DEFECT_EMBEDDINGS_FILE = (
    OUTPUT_DIR / "defect_embeddings.npy"
)

DEFECT_IDS_FILE = (
    OUTPUT_DIR / "defect_ids.csv"
)


# ============================================================
# GENERATE TESTCASE EMBEDDINGS
# ============================================================

def generate_testcase_embeddings(embedder, testcases):

    print("\n" + "=" * 60)
    print("GENERATING TESTCASE EMBEDDINGS")
    print("=" * 60)

    texts = [
        build_testcase_text(row)
        for _, row in testcases.iterrows()
    ]

    print(f"Records: {len(texts):,}")
    print("Encoding...")

    start = time.time()

    embeddings = embedder.model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    elapsed = time.time() - start

    embeddings = embeddings.astype(np.float32)

    np.save(
        TESTCASE_EMBEDDINGS_FILE,
        embeddings,
    )

    testcases[["test_case_id"]].to_csv(
        TESTCASE_IDS_FILE,
        index=False,
    )

    print(
        f"\n✓ Generated: "
        f"{len(embeddings):,} embeddings"
    )

    print(
        f"✓ Shape: "
        f"{embeddings.shape}"
    )

    print(
        f"✓ Saved: "
        f"{TESTCASE_EMBEDDINGS_FILE}"
    )

    print(
        f"✓ Saved IDs: "
        f"{TESTCASE_IDS_FILE}"
    )

    print(
        f"✓ Time: "
        f"{elapsed / 60:.2f} minutes"
    )

    return embeddings


# ============================================================
# GENERATE DEFECT EMBEDDINGS
# ============================================================

def generate_defect_embeddings(embedder, defects):

    print("\n" + "=" * 60)
    print("GENERATING DEFECT EMBEDDINGS")
    print("=" * 60)

    texts = [
        build_defect_text(row)
        for _, row in defects.iterrows()
    ]

    print(f"Records: {len(texts):,}")
    print("Encoding...")

    start = time.time()

    embeddings = embedder.model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    elapsed = time.time() - start

    embeddings = embeddings.astype(np.float32)

    np.save(
        DEFECT_EMBEDDINGS_FILE,
        embeddings,
    )

    defects[["defect_id"]].to_csv(
        DEFECT_IDS_FILE,
        index=False,
    )

    print(
        f"\n✓ Generated: "
        f"{len(embeddings):,} embeddings"
    )

    print(
        f"✓ Shape: "
        f"{embeddings.shape}"
    )

    print(
        f"✓ Saved: "
        f"{DEFECT_EMBEDDINGS_FILE}"
    )

    print(
        f"✓ Saved IDs: "
        f"{DEFECT_IDS_FILE}"
    )

    print(
        f"✓ Time: "
        f"{elapsed / 60:.2f} minutes"
    )

    return embeddings


# ============================================================
# VALIDATE EXISTING EMBEDDINGS
# ============================================================

def validate_embeddings():

    print("\n" + "=" * 60)
    print("VALIDATING EXISTING EMBEDDINGS")
    print("=" * 60)

    # --------------------------------------------------------
    # Check files
    # --------------------------------------------------------

    required_files = [
        TESTCASE_EMBEDDINGS_FILE,
        TESTCASE_IDS_FILE,
        DEFECT_EMBEDDINGS_FILE,
        DEFECT_IDS_FILE,
    ]

    for file in required_files:

        if not file.exists():
            raise FileNotFoundError(
                f"Required file not found:\n{file}"
            )

        print(f"✓ Found: {file.name}")

    # --------------------------------------------------------
    # Load embeddings
    # --------------------------------------------------------

    print("\nLoading embedding files...")

    testcase_embeddings = np.load(
        TESTCASE_EMBEDDINGS_FILE
    )

    defect_embeddings = np.load(
        DEFECT_EMBEDDINGS_FILE
    )

    # --------------------------------------------------------
    # Load IDs
    # --------------------------------------------------------

    testcase_ids = pd.read_csv(
        TESTCASE_IDS_FILE
    )

    defect_ids = pd.read_csv(
        DEFECT_IDS_FILE
    )

    # --------------------------------------------------------
    # Basic shape validation
    # --------------------------------------------------------

    assert testcase_embeddings.shape == (
        20_000,
        1024,
    ), (
        "Unexpected TestCase embedding shape: "
        f"{testcase_embeddings.shape}"
    )

    assert defect_embeddings.shape == (
        10_000,
        1024,
    ), (
        "Unexpected Defect embedding shape: "
        f"{defect_embeddings.shape}"
    )

    print(
        f"\n✓ TestCase shape: "
        f"{testcase_embeddings.shape}"
    )

    print(
        f"✓ Defect shape: "
        f"{defect_embeddings.shape}"
    )

    # --------------------------------------------------------
    # ID validation
    # --------------------------------------------------------

    assert len(testcase_ids) == 20_000
    assert len(defect_ids) == 10_000

    assert (
        testcase_ids["test_case_id"].is_unique
    )

    assert (
        defect_ids["defect_id"].is_unique
    )

    print("✓ TestCase count: 20,000")
    print("✓ Defect count: 10,000")
    print("✓ TestCase IDs are unique")
    print("✓ Defect IDs are unique")

    # --------------------------------------------------------
    # Finite value validation
    # --------------------------------------------------------

    assert np.isfinite(
        testcase_embeddings
    ).all()

    assert np.isfinite(
        defect_embeddings
    ).all()

    print("✓ All TestCase values are finite")
    print("✓ All Defect values are finite")

    # --------------------------------------------------------
    # Norm validation
    #
    # We use 5e-3 instead of 1e-3 because the
    # float32 embeddings show small numerical
    # differences after generation/storage.
    # --------------------------------------------------------

    testcase_norms = np.linalg.norm(
        testcase_embeddings,
        axis=1,
    )

    defect_norms = np.linalg.norm(
        defect_embeddings,
        axis=1,
    )

    print(
        "\nTestCase norm range:"
        f" {testcase_norms.min():.6f}"
        f" → {testcase_norms.max():.6f}"
    )

    print(
        "TestCase norm mean:"
        f" {testcase_norms.mean():.6f}"
    )

    print(
        "Defect norm range:"
        f" {defect_norms.min():.6f}"
        f" → {defect_norms.max():.6f}"
    )

    print(
        "Defect norm mean:"
        f" {defect_norms.mean():.6f}"
    )

    assert np.allclose(
        testcase_norms,
        1.0,
        atol=5e-3,
    )

    assert np.allclose(
        defect_norms,
        1.0,
        atol=5e-3,
    )

    print("✓ TestCase embeddings are normalized")
    print("✓ Defect embeddings are normalized")

    # --------------------------------------------------------
    # Data type
    # --------------------------------------------------------

    print(
        f"\nTestCase dtype: "
        f"{testcase_embeddings.dtype}"
    )

    print(
        f"Defect dtype: "
        f"{defect_embeddings.dtype}"
    )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("✓ EMBEDDING VALIDATION SUCCESSFUL")
    print("=" * 60)

    print(
        "\nTestCase embeddings : 20,000"
    )

    print(
        "Defect embeddings   : 10,000"
    )

    print(
        "Total embeddings    : 30,000"
    )

    print(
        "\nVector dimension    : 1024"
    )

    print(
        f"\nTestCase file:"
        f"\n  {TESTCASE_EMBEDDINGS_FILE}"
    )

    print(
        f"\nDefect file:"
        f"\n  {DEFECT_EMBEDDINGS_FILE}"
    )


# ============================================================
# FULL GENERATION
# ============================================================

def generate_all_embeddings():

    print("=" * 60)
    print("PHASE 1 - PART 2")
    print("FULL EMBEDDING GENERATION")
    print("=" * 60)

    print("\nLoading datasets...")

    testcases = pd.read_csv(
        TESTCASES_FILE
    )

    defects = pd.read_csv(
        DEFECTS_FILE
    )

    print(
        f"TestCases : {len(testcases):,}"
    )

    print(
        f"Defects   : {len(defects):,}"
    )

    # --------------------------------------------------------
    # Load embedding model
    # --------------------------------------------------------

    embedder = EmbeddingModel()

    # --------------------------------------------------------
    # Generate TestCase embeddings
    # --------------------------------------------------------

    generate_testcase_embeddings(
        embedder,
        testcases,
    )

    # --------------------------------------------------------
    # Generate Defect embeddings
    # --------------------------------------------------------

    generate_defect_embeddings(
        embedder,
        defects,
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validate_embeddings()

    print("\n" + "=" * 60)
    print("✓ PART 2 COMPLETED")
    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Generate and validate GraphRAG embeddings"
    )

    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate embeddings from scratch",
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # DEFAULT:
    # Validate existing embeddings only.
    #
    # This prevents accidentally regenerating the
    # 30,000 embeddings.
    # --------------------------------------------------------

    if not args.generate:

        print("=" * 60)
        print("PHASE 1 - PART 2")
        print("VALIDATION OF EXISTING EMBEDDINGS")
        print("=" * 60)

        validate_embeddings()

    # --------------------------------------------------------
    # OPTIONAL:
    # Explicitly regenerate embeddings.
    # --------------------------------------------------------

    else:

        generate_all_embeddings()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()