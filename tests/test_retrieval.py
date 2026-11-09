import pytest
from unittest.mock import MagicMock

from graph.query_understanding import (
    normalize_text,
    extract_regex_ids,
    validate_and_map_filters,
    QueryUnderstanding,
)
from graph.retrieval_router import RetrievalRouter
from graph.semantic_retriever import escape_lucene_query, SemanticRetriever
from graph.graph_retriever import _clean_props, Neo4jGraphRetriever
from graph.context_assembler import ContextAssembler


# ============================================================
# 1. ID REGEX & NORMALIZATION
# ============================================================

def test_text_normalization():
    # Test Unicode dashes
    raw = "BUG\u20100001 \u2013 TC\u20140002 \u2212 EXEC\u20150003"
    norm = normalize_text(raw)
    assert "BUG-0001" in norm
    assert "TC-0002" in norm
    assert "EXEC-0003" in norm


def test_id_regex_extraction_and_digits():
    text = "Found BUG-000176, malformed BUG-00000099, TC-000001, EXEC-003016, and SCR-ocr_batch_001-0000."
    ids = extract_regex_ids(text)
    assert ids["defect_ids"] == ["BUG-000176", "BUG-00000099"]
    assert ids["test_case_ids"] == ["TC-000001"]
    assert ids["execution_ids"] == ["EXEC-003016"]
    assert ids["screenshot_ids"] == ["SCR-ocr_batch_001-0000"]


# ============================================================
# 2. VOCABULARY VALIDATION & ALIASES
# ============================================================

def test_vocabulary_validation_aliases():
    vocab = {
        "severity": ["Critical", "Major", "Minor", "Blocker"],
        "priority": ["P0", "P1", "P2", "P3"],
        "status": ["New", "In Progress", "Resolved", "Closed"],
        "execution_status": ["Passed", "Failed", "Skipped", "Blocked"],
        "environments": ["DEV", "QA", "UAT", "STAGING"],
        "modules": ["Accounting", "Sales", "CRM"],
    }

    raw = {
        "severity": "crit",
        "priority": "p1",
        "environment": "uat",
        "status": "failed",
    }
    validated, unmapped = validate_and_map_filters(raw, vocab)
    assert validated["severity"] == "Critical"
    assert validated["priority"] == "P1"
    assert validated["environment"] == "UAT"
    assert validated["status"] == "Failed"
    assert unmapped == []


def test_vocabulary_unmapped_filters():
    vocab = {
        "environments": ["DEV", "QA", "UAT"],
    }
    raw = {"environment": "PROD"}
    validated, unmapped = validate_and_map_filters(raw, vocab)
    assert "environment" not in validated
    assert len(unmapped) == 1
    assert unmapped[0]["value"] == "PROD"


# ============================================================
# 3. ROUTER DECISIONS FOR 15 QUESTIONS
# ============================================================

def test_router_15_questions():
    router = RetrievalRouter()
    qu = QueryUnderstanding()

    questions = [
        # 5 ID questions -> plan.kind: id_lookup, fallback_chain: []
        ("BUG-000176 details", "id_lookup", []),
        ("SCR-ocr_batch_001-0000 details", "id_lookup", []),
        ("Show execution EXEC-003016 results", "id_lookup", []),
        ("What is the status of test case TC-000001?", "id_lookup", []),
        ("Check malformed ID BUG-00000099", "id_lookup", []),

        # 5 Filter / Aggregate -> plan.kind: filter_list / filter_count / group_by, fb: ['semantic', 'lightrag']
        ("show all Critical defects", "filter_list", ["semantic", "lightrag"]),
        ("how many Failed executions in UAT", "filter_count", ["semantic", "lightrag"]),
        ("defects grouped by severity", "group_by", ["semantic", "lightrag"]),
        ("top modules by defects", "group_by", ["semantic", "lightrag"]),
        ("list test cases in Accounting module", "filter_list", ["semantic", "lightrag"]),

        # 5 Semantic -> plan.kind: semantic, fb: ['lightrag']
        ("defects about login timeouts", "semantic", ["lightrag"]),
        ("payment failure after checkout", "semantic", ["lightrag"]),
        ("slow page load on dashboard", "semantic", ["lightrag"]),
        ("UI misaligned on mobile", "semantic", ["lightrag"]),
        ("permission denied error when submitting form", "semantic", ["lightrag"]),
    ]

    for q, expected_kind, expected_fb in questions:
        under = qu._fallback_parse(q)
        route = router.route(under)
        assert route["plan"]["kind"] == expected_kind, f"Failed for '{q}': got {route['plan']['kind']}"
        assert route["fallback_chain"] == expected_fb, f"Failed fb for '{q}': got {route['fallback_chain']}"


# ============================================================
# 4. LUCENE ESCAPING
# ============================================================

def test_lucene_escaping():
    raw_query = 'login: timeout AND (error OR crash) + "server issue"!'
    escaped = escape_lucene_query(raw_query)
    # Special characters must be backslash escaped
    assert r"\:" in escaped
    assert r"\(" in escaped
    assert r"\)" in escaped
    assert r"\+" in escaped
    assert r'\"' in escaped
    assert r"\!" in escaped
    # Reserved boolean operators should not be isolated
    assert "AND" not in escaped.split()
    assert "OR" not in escaped.split()


# ============================================================
# 5. RRF FUSION MATH
# ============================================================

def test_rrf_fusion_math():
    mock_retriever = SemanticRetriever(graph_retriever=MagicMock())

    vector_hits = [
        {"defect_id": "BUG-1", "score": 0.95},
        {"defect_id": "BUG-2", "score": 0.85},
    ]
    fulltext_hits = [
        {"defect_id": "BUG-2", "score": 4.5},
        {"defect_id": "BUG-3", "score": 2.1},
    ]

    fused = mock_retriever._rrf_fuse_defects(vector_hits, fulltext_hits, limit=3)
    # BUG-2 appeared in both: vector rank 2, fulltext rank 1
    # score = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 ~= 0.016129 + 0.016393 ~= 0.03252
    # BUG-1: vector rank 1 -> 1/(60+1) ~= 0.016393
    # BUG-3: fulltext rank 2 -> 1/(60+2) ~= 0.016129
    assert fused[0]["defect_id"] == "BUG-2"
    assert "vector" in fused[0]["sources"] and "fulltext" in fused[0]["sources"]
    assert fused[1]["defect_id"] == "BUG-1"
    assert fused[2]["defect_id"] == "BUG-3"


# ============================================================
# 6. _clean_props
# ============================================================

def test_clean_props():
    props = {
        "defect_id": "BUG-000176",
        "title": "Login crash",
        "embedding": [0.12, -0.45, 0.99] * 341,
        "embedding_model": "Qwen3-Embedding-0.6B",
        "nested": {
            "key": "val",
            "embedding": [0.1, 0.2],
        },
    }
    cleaned = _clean_props(props)
    assert "defect_id" in cleaned
    assert "title" in cleaned
    assert "embedding" not in cleaned
    assert "embedding_model" not in cleaned
    assert cleaned["nested"] == {"key": "val"}

    # List of dicts
    cleaned_list = _clean_props([props, {"a": 1, "embedding": [0.0]}])
    assert "embedding" not in cleaned_list[0]
    assert cleaned_list[1] == {"a": 1}


# ============================================================
# 7. FILTER REGISTRY REJECTION OF UNKNOWN KEYS
# ============================================================

def test_filter_registry_rejection():
    mock_retriever = Neo4jGraphRetriever.__new__(Neo4jGraphRetriever)
    mock_retriever.has_modules = True
    mock_retriever.has_environments = True

    # Test invalid field in count_defects_by
    with pytest.raises(ValueError, match="not in defect aggregation whitelist"):
        mock_retriever.count_defects_by("invalid_column")

    # Test invalid field in count_executions_by
    with pytest.raises(ValueError, match="not in execution aggregation whitelist"):
        mock_retriever.count_executions_by("invalid_column")


# ============================================================
# 8. CONTEXT ASSEMBLER DATA SHAPES
# ============================================================

def test_context_assembler_shapes():
    assembler = ContextAssembler()

    # Shape 1: defect_context
    ret_defect = {
        "query": "BUG-1 details",
        "route": {"route": "neo4j"},
        "neo4j": {
            "results": [
                {
                    "type": "defect_context",
                    "id": "BUG-1",
                    "data": {
                        "defect": {"defect_id": "BUG-1", "title": "Crash"},
                        "execution": {"execution_id": "EXEC-1", "status": "Failed"},
                        "testcase": {"test_case_id": "TC-1", "feature": "Login"},
                        "screenshots": [{"screenshot_id": "SCR-1"}],
                    },
                }
            ],
            "not_found_ids": [],
            "links_missing": False,
        },
    }
    ctx1 = assembler.assemble(ret_defect)
    assert len(ctx1["entities"]) == 4
    rel_names = {r["relationship"] for r in ctx1["relationships"]}
    assert "FOUND_DEFECT" in rel_names
    assert "HAS_DEFECT" in rel_names
    assert "HAS_EXECUTION" in rel_names
    assert "HAS_SCREENSHOT" in rel_names
    assert ctx1["notes"]["not_found_ids"] == []

    # Shape 2: execution_context
    ret_exec = {
        "query": "EXEC-1 results",
        "route": {"route": "neo4j"},
        "neo4j": {
            "results": [
                {
                    "type": "execution_context",
                    "id": "EXEC-1",
                    "data": {
                        "execution": {"execution_id": "EXEC-1"},
                        "testcase": {"test_case_id": "TC-1"},
                        "defects": [{"defect_id": "BUG-1"}],
                        "screenshots": [{"screenshot_id": "SCR-1"}],
                    },
                }
            ],
        },
    }
    ctx2 = assembler.assemble(ret_exec)
    assert len(ctx2["entities"]) == 4
    rel_names2 = {r["relationship"] for r in ctx2["relationships"]}
    assert "CAPTURED_SCREENSHOT" in rel_names2

    # Shape 3: screenshot_context
    ret_scr = {
        "query": "SCR-1",
        "route": {"route": "neo4j"},
        "neo4j": {
            "results": [
                {
                    "type": "screenshot_context",
                    "id": "SCR-1",
                    "data": {
                        "screenshot": {"screenshot_id": "SCR-1", "test_case_id": "TC-1"},
                        "testcases": [{"test_case_id": "TC-1"}],
                        "executions": [{"execution_id": "EXEC-1"}],
                        "defects": [{"defect_id": "BUG-1"}],
                    },
                }
            ],
        },
    }
    ctx3 = assembler.assemble(ret_scr)
    assert len(ctx3["screenshots"]) == 1
    assert ctx3["screenshots"][0]["metadata_consistent"] is True
    assert ctx3["screenshots"][0]["graph_linkage"]["test_case_ids"] == ["TC-1"]

    # Shape 4: not_found_id
    ret_not_found = {
        "query": "BUG-9999",
        "route": {"route": "neo4j"},
        "neo4j": {
            "results": [{"type": "defect_context", "id": "BUG-9999", "data": None}],
            "not_found_ids": ["BUG-9999"],
            "links_missing": False,
        },
    }
    ctx4 = assembler.assemble(ret_not_found)
    assert ctx4["notes"]["not_found_ids"] == ["BUG-9999"]
