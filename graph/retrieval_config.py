from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Neo4j configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_DATABASE = "graphragv2"

# Flags and limits
LIGHTRAG_ENABLED = False  # Phase 0 confirmed 0 entities in lightrag_neo4j_test
DEFAULT_LIMIT = 25
MAX_PATHS = 200
VECTOR_TOP_K = 10
VECTOR_OVERFETCH = 200
RRF_K = 60

# Reranker configuration
ENABLE_RERANKER = True  # Set to False to bypass cross-encoder reranking (A/B testing)
RERANKER_MODEL = "BAAI/bge-reranker-base"
RERANK_CANDIDATE_LIMIT = 25  # Number of RRF candidates passed to cross-encoder

# Search indexes
FULLTEXT_INDEX = "defect_text"
VECTOR_INDEXES = {
    "defect": "defect_embedding",
    "screenshot": "screenshot_embedding",
    "test_case": "testcase_embedding",
}

# Embedding model settings
EMBEDDING_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
EMBEDDING_DIM = 1024
QUERY_INSTRUCTION = "Given a software defect search query, retrieve relevant defect reports"
USE_QUERY_INSTRUCTION = False

# LLM model
from graph.llm_client import LLM_MODEL

# Traces
TRACE_FILE = PROJECT_ROOT / "traces" / "retrieval_trace.jsonl"
