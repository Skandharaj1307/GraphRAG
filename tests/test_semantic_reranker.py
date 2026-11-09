import pytest
from embedding.text_builder import build_defect_text, extract_error_signature
from graph.semantic_retriever import SemanticRetriever, _format_candidate_text
from graph.graph_retriever import Neo4jGraphRetriever


def test_extract_error_signature():
    text1 = "The background job calculated the incoming shipment which resulted in an AccessError."
    sig1 = extract_error_signature(text1)
    assert "AccessError" in sig1

    text2 = "User encountered a permission error and then a validation exception."
    sig2 = extract_error_signature(text2)
    assert "permission error" in sig2
    assert "validation exception" in sig2


def test_build_defect_text_enriched():
    row = {
        "defect_id": "BUG-999999",
        "title": "Crash during invoice sync",
        "description": "Invoice sync timed out with timeout error",
        "module": "Accounting",
        "severity": "Critical",
        "priority": "P0",
        "status": "Open",
        "root_cause": "The worker node exhausted memory while parsing large XML payloads.",
        "test_steps": "1. Go to Invoices\n2. Click Sync All",
        "execution_notes": "Execution failed with OutOfMemoryError after 120s",
        "bug_type": "Crash",
        "reproducibility": "Always",
        "environment": "Prod",
        "regression": "Yes",
    }
    text = build_defect_text(row)

    # Verify root cause is present
    assert "Root Cause:\nThe worker node exhausted memory" in text
    # Verify linked test steps are present
    assert "Linked Test Steps:\n1. Go to Invoices" in text
    # Verify error signature is extracted
    assert "Error Signature:" in text
    assert "OutOfMemoryError" in text


def test_format_candidate_text():
    cand = {
        "defect_id": "BUG-001",
        "title": "Database connection drop",
        "description": "Connection dropped on heavy load",
        "root_cause": "Pool size too small",
        "module": "Infrastructure",
        "severity": "Major",
    }
    fmt = _format_candidate_text(cand, "defect")
    assert "Title: Database connection drop" in fmt
    assert "Root Cause: Pool size too small" in fmt
    assert "Module: Infrastructure" in fmt


def test_reranker_scoring_and_sorting():
    retriever = SemanticRetriever()
    query = "database connection timeout in infrastructure"
    candidates = [
        {
            "defect_id": "BUG-001",
            "title": "Button UI misaligned in CSS style",
            "description": "The button on the profile page is shifted 5px to the left.",
            "module": "Frontend",
            "severity": "Low",
        },
        {
            "defect_id": "BUG-002",
            "title": "Database connection pool timeout error",
            "description": "The postgres connection timed out after 30s during infrastructure failover.",
            "root_cause": "Database connection timeout under peak load.",
            "module": "Infrastructure",
            "severity": "Critical",
        },
    ]

    reranked = retriever._rerank_candidates(query, candidates, "defect", top_k=2)
    retriever.close()

    assert len(reranked) == 2
    assert "rerank_score" in reranked[0]
    assert "rerank_score" in reranked[1]
    # The database defect should be ranked first by the cross-encoder
    assert reranked[0]["defect_id"] == "BUG-002"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]


def test_reranker_ab_flag():
    retriever = SemanticRetriever()
    query = "invoice permission error"
    
    # Test with reranker disabled
    res_off = retriever.search(query, limit=5, enable_reranker=False)
    assert "reranked" not in res_off["template"]

    # Test with reranker enabled
    res_on = retriever.search(query, limit=5, enable_reranker=True)
    if res_on["hits"]:
        assert "reranked" in res_on["template"]

    retriever.close()

