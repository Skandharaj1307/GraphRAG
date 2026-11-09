import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Base paths
EVAL_DIR = Path(__file__).resolve().parent
GRAPH_DIR = EVAL_DIR.parent
BASE_DIR = GRAPH_DIR.parent

# Load environment variables from project root .env
load_dotenv(BASE_DIR / ".env")

# Database & Model Configurations (Never hardcoded)
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "qazwsxedc")

from graph.llm_client import (
    LLM_BASE_URL as OPENROUTER_BASE_URL,
    LLM_API_KEY as OPENROUTER_API_KEY,
    JUDGE_MODEL,
)

# Judge LLM Settings (falling back to unified LLM settings)
JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", OPENROUTER_BASE_URL)
JUDGE_API_KEY = os.getenv("JUDGE_API_KEY", OPENROUTER_API_KEY)

# Intent Aliases Mapping (Bidirectional equivalence between code labels and testset labels)
INTENT_ALIASES = {
    "defect_lookup": ["defect_lookup", "defect_analysis"],
    "defect_analysis": ["defect_analysis", "defect_lookup"],
    "testcase_lookup": ["testcase_lookup"],
    "execution_lookup": ["execution_lookup"],
    "testcase_execution_analysis": ["testcase_execution_analysis"],
    "failure_analysis": ["failure_analysis", "defect_analysis"],
    "screenshot_lookup": ["screenshot_lookup", "defect_lookup"],
    "semantic_search": ["semantic_search"],
    "general_test_analysis": ["general_test_analysis"]
}

# Specific Fields to Score per Question Type (ignores unrequested metadata like title or defect_id in lookup questions)
SCORED_FIELDS_PER_TYPE = {
    "defect_lookup": ["root_cause"],
    "defect_multi_property": ["severity", "priority", "status", "assigned_to"],
    "defect_to_testcase": ["test_case_id", "build_number", "tester"],
    "testcase_to_defects": ["defect_ids"],
    "testcase_executions_summary": ["total_executions", "failed_executions"],
    "execution_context": ["environment", "browser", "operating_system", "status"],
    "screenshot_lookup": ["error_messages", "warning_messages", "screen_name"],
}

# Scoring Thresholds
TEXT_RECALL_THRESHOLD = 0.8
RETRIEVAL_MIN_FIELD_RECALL = 1.0
MIN_REQUEST_INTERVAL = 3.1

# Chain of Thought / Reasoning Leak Detection Regexes
REASONING_LEAK_REGEXES = [
    re.compile(r"here'?s a thinking process", re.IGNORECASE),
    re.compile(r"\bchain of thought\b", re.IGNORECASE),
    re.compile(r"\binternal reasoning\b", re.IGNORECASE),
    re.compile(r"let'?s analyze the user question", re.IGNORECASE),
    re.compile(r"\bstep-by-step reasoning\b", re.IGNORECASE),
]

# Unanswerable Fallback Detection Regexes
UNANSWERABLE_REGEXES = [
    re.compile(r"\bnot found\b", re.IGNORECASE),
    re.compile(r"\bno record\b", re.IGNORECASE),
    re.compile(r"\bdoes not exist\b", re.IGNORECASE),
    re.compile(r"\bunable to find\b", re.IGNORECASE),
    re.compile(r"\bno information\b", re.IGNORECASE),
    re.compile(r"\bno defect\b", re.IGNORECASE),
    re.compile(r"\bno test case\b", re.IGNORECASE),
    re.compile(r"\bno execution\b", re.IGNORECASE),
    re.compile(r"\bcould not be found\b", re.IGNORECASE),
]

# Refusal / Safety Classifier Label Detection Regexes
REFUSAL_REGEXES = [
    re.compile(r"\buser safety:\b", re.IGNORECASE),
    re.compile(r"\bsafety categories:\b", re.IGNORECASE),
    re.compile(r"\bpii/privacy\b", re.IGNORECASE),
    re.compile(r"\bi cannot help\b", re.IGNORECASE),
    re.compile(r"\bi am unable to assist\b", re.IGNORECASE),
    re.compile(r"\bi cannot fulfill\b", re.IGNORECASE),
    re.compile(r"\bas an ai language model\b", re.IGNORECASE),
]

DEFAULT_TESTSET_PATH = GRAPH_DIR / "testset.json"
DEFAULT_RUNS_DIR = EVAL_DIR / "runs"
