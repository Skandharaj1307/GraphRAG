import csv
from pathlib import Path

import numpy as np

from .embedder import EmbeddingModel


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SCREENSHOT_EMBEDDINGS_FILE = (
    BASE_DIR
    / "embedding"
    / "data"
    / "screenshot_embeddings.npy"
)

SCREENSHOT_IDS_FILE = (
    BASE_DIR
    / "embedding"
    / "data"
    / "screenshot_ids.csv"
)

SCREENSHOT_DIR = (
    BASE_DIR
    / "dataset"
    / "unstructured"
    / "screenshots"
)


# ============================================================
# LOAD EMBEDDINGS
# ============================================================

def load_embeddings():

    if not SCREENSHOT_EMBEDDINGS_FILE.exists():

        raise FileNotFoundError(
            f"Screenshot embeddings not found:\n"
            f"{SCREENSHOT_EMBEDDINGS_FILE}"
        )

    embeddings = np.load(
        SCREENSHOT_EMBEDDINGS_FILE
    )

    return embeddings


# ============================================================
# LOAD SCREENSHOT IDS
# ============================================================

def load_screenshot_ids():

    if not SCREENSHOT_IDS_FILE.exists():

        raise FileNotFoundError(
            f"Screenshot IDs not found:\n"
            f"{SCREENSHOT_IDS_FILE}"
        )

    screenshot_ids = []

    with open(
        SCREENSHOT_IDS_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            screenshot_ids.append(
                row["screenshot_id"]
            )

    return screenshot_ids


# ============================================================
# LOAD ORIGINAL SCREENSHOT RECORDS
# ============================================================

def load_screenshot_records():

    records = {}

    files = sorted(
        SCREENSHOT_DIR.glob(
            "ocr_batch_*.json"
        )
    )

    for file_path in files:

        import json

        with open(
            file_path,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        for index, record in enumerate(data):

            screenshot_id = (
                f"SCR-"
                f"{file_path.stem}-"
                f"{index:04d}"
            )

            records[screenshot_id] = record

    return records


# ============================================================
# SEARCH
# ============================================================

def search_screenshots(
    query,
    model,
    embeddings,
    screenshot_ids,
    records,
    top_k=5,
):

    # --------------------------------------------------------
    # Embed query
    # --------------------------------------------------------

    query_embedding = model.embed_query(
        query
    )

    # --------------------------------------------------------
    # Cosine similarity
    #
    # Since all vectors are normalized:
    #
    # cosine similarity = dot product
    # --------------------------------------------------------

    scores = np.dot(
        embeddings,
        query_embedding,
    )

    # --------------------------------------------------------
    # Get top-k indices
    # --------------------------------------------------------

    top_indices = np.argsort(
        scores
    )[::-1][:top_k]

    results = []

    for rank, index in enumerate(
        top_indices,
        start=1
    ):

        screenshot_id = (
            screenshot_ids[index]
        )

        record = records.get(
            screenshot_id,
            {}
        )

        results.append(
            {
                "rank": rank,
                "screenshot_id": screenshot_id,
                "score": float(
                    scores[index]
                ),
                "record": record,
            }
        )

    return results


# ============================================================
# DISPLAY RESULTS
# ============================================================

def display_results(
    query,
    results,
):

    print("\n" + "=" * 70)

    print(
        "SCREENSHOT SEMANTIC SEARCH"
    )

    print("=" * 70)

    print(
        f"\nQuery:\n{query}"
    )

    print(
        "\n" + "-" * 70
    )

    for result in results:

        record = result["record"]

        print(
            f"\n#{result['rank']} "
            f"{result['screenshot_id']}"
        )

        print(
            f"Similarity: "
            f"{result['score']:.4f}"
        )

        print(
            f"Test Case: "
            f"{record.get('test_case_id', '')}"
        )

        print(
            f"Execution: "
            f"{record.get('execution_id', '')}"
        )

        print(
            f"Defect: "
            f"{record.get('bug_id', '')}"
        )

        print(
            f"Screen: "
            f"{record.get('screen_name', '')}"
        )

        print(
            f"Module: "
            f"{record.get('module', '')}"
        )

        # ----------------------------------------------------
        # Errors
        # ----------------------------------------------------

        errors = record.get(
            "error_messages",
            []
        )

        if errors:

            print("Errors:")

            for error in errors:

                print(
                    f"  - {error}"
                )

        # ----------------------------------------------------
        # Warnings
        # ----------------------------------------------------

        warnings = record.get(
            "warning_messages",
            []
        )

        if warnings:

            print("Warnings:")

            for warning in warnings:

                print(
                    f"  - {warning}"
                )

        # ----------------------------------------------------
        # User action
        # ----------------------------------------------------

        user_action = record.get(
            "user_action",
            ""
        )

        if user_action:

            print(
                f"User Action: "
                f"{user_action}"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("LOADING SCREENSHOT SEARCH")
    print("=" * 70)

    # --------------------------------------------------------
    # Load embeddings
    # --------------------------------------------------------

    embeddings = load_embeddings()

    print(
        f"Screenshot embeddings: "
        f"{embeddings.shape}"
    )

    # --------------------------------------------------------
    # Load IDs
    # --------------------------------------------------------

    screenshot_ids = (
        load_screenshot_ids()
    )

    print(
        f"Screenshot IDs: "
        f"{len(screenshot_ids):,}"
    )

    # --------------------------------------------------------
    # Verify count
    # --------------------------------------------------------

    if (
        embeddings.shape[0]
        != len(screenshot_ids)
    ):

        raise ValueError(
            "Embedding count does not "
            "match screenshot ID count."
        )

    # --------------------------------------------------------
    # Load original records
    # --------------------------------------------------------

    records = (
        load_screenshot_records()
    )

    print(
        f"Screenshot records: "
        f"{len(records):,}"
    )

    # --------------------------------------------------------
    # Load embedding model
    # --------------------------------------------------------

    model = EmbeddingModel()

    # --------------------------------------------------------
    # Interactive search
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("READY FOR SCREENSHOT SEARCH")
    print("=" * 70)

    print(
        "\nType a query."
        "\nType 'exit' to stop."
    )

    while True:

        query = input(
            "\nQuery: "
        ).strip()

        if query.lower() == "exit":

            print(
                "\nExiting..."
            )

            break

        if not query:

            continue

        results = search_screenshots(
            query=query,
            model=model,
            embeddings=embeddings,
            screenshot_ids=screenshot_ids,
            records=records,
            top_k=5,
        )

        display_results(
            query,
            results,
        )


if __name__ == "__main__":
    main()