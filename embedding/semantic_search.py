import numpy as np
import pandas as pd
from pathlib import Path

from .embedder import EmbeddingModel


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "dataset" / "structured"
EMBEDDING_DIR = BASE_DIR / "embedding" / "data"

TESTCASES_FILE = DATA_DIR / "testcases.csv"
DEFECTS_FILE = DATA_DIR / "defects.csv"

TESTCASE_EMBEDDINGS_FILE = (
    EMBEDDING_DIR / "testcase_embeddings.npy"
)

TESTCASE_IDS_FILE = (
    EMBEDDING_DIR / "testcase_ids.csv"
)

DEFECT_EMBEDDINGS_FILE = (
    EMBEDDING_DIR / "defect_embeddings.npy"
)

DEFECT_IDS_FILE = (
    EMBEDDING_DIR / "defect_ids.csv"
)


# ============================================================
# SEMANTIC SEARCH
# ============================================================

class SemanticSearch:

    def __init__(self):

        print("Loading vector data...")

        # ----------------------------------------------------
        # Load embeddings
        # ----------------------------------------------------

        self.testcase_embeddings = np.load(
            TESTCASE_EMBEDDINGS_FILE
        )

        self.defect_embeddings = np.load(
            DEFECT_EMBEDDINGS_FILE
        )

        # ----------------------------------------------------
        # Load embedding IDs
        # ----------------------------------------------------

        self.testcase_ids = pd.read_csv(
            TESTCASE_IDS_FILE
        )

        self.defect_ids = pd.read_csv(
            DEFECT_IDS_FILE
        )

        # ----------------------------------------------------
        # Load original datasets
        # ----------------------------------------------------

        self.testcases = pd.read_csv(
            TESTCASES_FILE
        )

        self.defects = pd.read_csv(
            DEFECTS_FILE
        )

        # ----------------------------------------------------
        # Create ID → row lookup
        # ----------------------------------------------------

        self.testcase_lookup = (
            self.testcases
            .set_index("test_case_id")
        )

        self.defect_lookup = (
            self.defects
            .set_index("defect_id")
        )

        print(
            f"✓ TestCase vectors: "
            f"{self.testcase_embeddings.shape}"
        )

        print(
            f"✓ Defect vectors: "
            f"{self.defect_embeddings.shape}"
        )

        print(
            f"✓ TestCases loaded: "
            f"{len(self.testcases):,}"
        )

        print(
            f"✓ Defects loaded: "
            f"{len(self.defects):,}"
        )

        # ----------------------------------------------------
        # Load embedding model
        # ----------------------------------------------------

        self.embedder = EmbeddingModel()

        print("✓ Semantic search initialized")

    # ========================================================
    # TESTCASE SEARCH
    # ========================================================

    def search_testcases(
        self,
        query,
        top_k=5,
    ):

        query_embedding = (
            self.embedder.embed_query(query)
        )

        # Since both vectors are normalized:
        # cosine similarity = dot product

        scores = np.dot(
            self.testcase_embeddings,
            query_embedding,
        )

        top_indices = np.argsort(
            scores
        )[::-1][:top_k]

        results = []

        for index in top_indices:

            test_case_id = (
                self.testcase_ids.iloc[index][
                    "test_case_id"
                ]
            )

            row = self.testcase_lookup.loc[
                test_case_id
            ]

            results.append({
                "test_case_id": test_case_id,
                "score": float(scores[index]),
                "module": row.get("module", ""),
                "feature": row.get("feature", ""),
                "priority": row.get("priority", ""),
                "severity": row.get("severity", ""),
                "status": row.get("status", ""),
                "test_steps": row.get("test_steps", ""),
                "expected_result": row.get(
                    "expected_result",
                    "",
                ),
                "actual_result": row.get(
                    "actual_result",
                    "",
                ),
            })

        return results

    # ========================================================
    # DEFECT SEARCH
    # ========================================================

    def search_defects(
        self,
        query,
        top_k=5,
    ):

        query_embedding = (
            self.embedder.embed_query(query)
        )

        scores = np.dot(
            self.defect_embeddings,
            query_embedding,
        )

        top_indices = np.argsort(
            scores
        )[::-1][:top_k]

        results = []

        for index in top_indices:

            defect_id = (
                self.defect_ids.iloc[index][
                    "defect_id"
                ]
            )

            row = self.defect_lookup.loc[
                defect_id
            ]

            results.append({
                "defect_id": defect_id,
                "score": float(scores[index]),
                "title": row.get("title", ""),
                "description": row.get(
                    "description",
                    "",
                ),
                "module": row.get("module", ""),
                "severity": row.get(
                    "severity",
                    "",
                ),
                "priority": row.get(
                    "priority",
                    "",
                ),
                "status": row.get(
                    "status",
                    "",
                ),
                "root_cause": row.get(
                    "root_cause",
                    "",
                ),
            })

        return results


# ============================================================
# DISPLAY TESTCASE RESULTS
# ============================================================

def display_testcase_results(results):

    print("\n" + "=" * 70)
    print("RETRIEVED TEST CASE DETAILS")
    print("=" * 70)

    for rank, result in enumerate(
        results,
        start=1,
    ):

        print("\n" + "-" * 70)

        print(
            f"Result #{rank}"
        )

        print(
            f"Test Case ID : "
            f"{result['test_case_id']}"
        )

        print(
            f"Similarity   : "
            f"{result['score']:.4f}"
        )

        print(
            f"Module       : "
            f"{result['module']}"
        )

        print(
            f"Feature      : "
            f"{result['feature']}"
        )

        print(
            f"Priority     : "
            f"{result['priority']}"
        )

        print(
            f"Severity     : "
            f"{result['severity']}"
        )

        print(
            f"Status       : "
            f"{result['status']}"
        )

        print("\nTest Steps:")

        print(
            result["test_steps"]
        )

        print("\nExpected Result:")

        print(
            result["expected_result"]
        )

        print("\nActual Result:")

        print(
            result["actual_result"]
        )


# ============================================================
# DISPLAY DEFECT RESULTS
# ============================================================

def display_defect_results(results):

    print("\n" + "=" * 70)
    print("RETRIEVED DEFECT DETAILS")
    print("=" * 70)

    for rank, result in enumerate(
        results,
        start=1,
    ):

        print("\n" + "-" * 70)

        print(
            f"Result #{rank}"
        )

        print(
            f"Defect ID    : "
            f"{result['defect_id']}"
        )

        print(
            f"Similarity   : "
            f"{result['score']:.4f}"
        )

        print(
            f"Title        : "
            f"{result['title']}"
        )

        print(
            f"Module       : "
            f"{result['module']}"
        )

        print(
            f"Severity     : "
            f"{result['severity']}"
        )

        print(
            f"Priority     : "
            f"{result['priority']}"
        )

        print(
            f"Status       : "
            f"{result['status']}"
        )

        print("\nDescription:")

        print(
            result["description"]
        )

        print("\nRoot Cause:")

        print(
            result["root_cause"]
        )


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 70)
    print("PHASE 1 - PART 3")
    print("SEMANTIC SEARCH QUALITY VALIDATION")
    print("=" * 70)

    search = SemanticSearch()

    # ========================================================
    # TESTCASE QUERY
    # ========================================================

    query = (
        "Find test cases where the user encountered "
        "a permission error while performing a transaction"
    )

    print("\nQuery:")
    print(query)

    results = search.search_testcases(
        query,
        top_k=5,
    )

    display_testcase_results(
        results
    )

    # ========================================================
    # DEFECT QUERY
    # ========================================================

    defect_query = (
        "Find defects related to "
        "permission and access errors"
    )

    print("\n\nDefect Query:")
    print(defect_query)

    defect_results = search.search_defects(
        defect_query,
        top_k=5,
    )

    display_defect_results(
        defect_results
    )

    # ========================================================
    # COMPLETE
    # ========================================================

    print("\n" + "=" * 70)
    print("✓ SEMANTIC SEARCH QUALITY TEST COMPLETED")
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()