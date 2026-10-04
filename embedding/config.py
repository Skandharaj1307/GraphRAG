from pathlib import Path


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent


# Dataset paths
TESTCASES_FILE = (
    BASE_DIR / "dataset" / "structured" / "testcases.csv"
)

DEFECTS_FILE = (
    BASE_DIR / "dataset" / "structured" / "defects.csv"
)


# Embedding model
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"

# Expected embedding dimension
EMBEDDING_DIMENSION = 1024


# Embedding instruction
QUERY_INSTRUCTION = (
    "Given a test management query, retrieve relevant "
    "test cases and defects."
)