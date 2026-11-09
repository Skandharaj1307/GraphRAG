import pytest
from graph.build_graph import parse_failure_log_block
from graph.graph_retriever import Neo4jGraphRetriever
from graph.context_assembler import ContextAssembler


@pytest.fixture(scope="module")
def neo4j():
    retriever = Neo4jGraphRetriever()
    yield retriever
    retriever.close()


def test_parse_failure_log_block():
    sample_block = """
Bug ID: BUG-003596 | Execution ID: EXEC-016067 | Test Case ID: TC-015914
Timestamp: 1973-06-05T07:17:25
Module: HR
User Action: The API endpoint calculated the transfer due to missing configuration settings.
----------------------------------------------------------------------
Python Traceback:
Traceback (most recent call last):
  File "/odoo/addons/hr/models/record.py", line 158, in action_confirm
    self._validate_permissions()
  File "/odoo/odoo/models.py", line 1666, in _validate_permissions
    raise AccessError("Access Denied")
odoo.exceptions.AccessError: Access Denied: You do not have the required permissions.

Database Error:
ERROR: duplicate key value violates unique constraint "hr_unique_id"
DETAIL: Key (name)=(Test_Record_001) already exists.

HTTP Status: 404

Server Log:
INFO  hr - User attempted action resulting in failure. Session ID: 0c5836b3-6ad1-49f5-a61a-fa3184412070

Exception: AccessError
Resolution Hint: The background job escalated the subscription renewal which resulted in an AccessError.
"""
    parsed = parse_failure_log_block(sample_block.strip())
    assert parsed is not None
    assert parsed["execution_id"] == "EXEC-016067"
    assert parsed["defect_id"] == "BUG-003596"
    assert parsed["test_case_id"] == "TC-015914"
    assert parsed["exception_name"] == "AccessError"
    assert "Access Denied" in parsed["exception_message"]
    assert len(parsed["stack_frames"]) >= 2
    assert "/odoo/addons/hr/models/record.py:158 in action_confirm" in parsed["stack_frames"]
    assert parsed["http_status"] == 404
    assert "hr_unique_id" in parsed["database_error"]


def test_retrieval_returns_failure_log_for_execution(neo4j):
    """
    Test retrieval support for "why did EXEC-xxxx fail?":
    get_execution_context must return failure_log with actual exception.
    """
    ctx = neo4j.get_execution_context("EXEC-016067")
    assert ctx is not None
    assert "failure_log" in ctx
    log = ctx["failure_log"]
    assert log is not None
    assert log.get("exception_name") == "AccessError"
    assert "Access Denied" in log.get("exception_message", "")
    assert len(log.get("stack_frames", [])) >= 1


def test_srs_requirements_in_neo4j(neo4j):
    """
    Test SRS requirements ingested into (:Requirement) nodes with text and section.
    """
    with neo4j._session() as session:
        res = session.run("""
            MATCH (r:Requirement)
            WHERE r.source = 'srs_document.pdf'
            RETURN count(r) AS c, collect(r.name)[..5] AS sample_names
        """).single()
        assert res["c"] > 0
        names = res["sample_names"]
        assert any("Detailed Component" in n or "Requirements" in n or "Summary" in n for n in names)


def test_context_assembler_failure_log_integration(neo4j):
    """
    Test ContextAssembler preserves failure_log in structured_evidence,
    LogChunk in entities, and HAS_FAILURE_LOG in relationships.
    """
    ctx = neo4j.get_execution_context("EXEC-016067")
    retrieval_result = {
        "query": "Why did execution EXEC-016067 fail?",
        "route": {"query_type": "specific_entity_lookup"},
        "neo4j": {
            "source": "neo4j",
            "results": [
                {
                    "type": "execution_context",
                    "id": "EXEC-016067",
                    "data": ctx,
                }
            ],
            "not_found_ids": [],
            "links_missing": False,
        },
        "lightrag": None,
        "semantic": None,
    }

    assembler = ContextAssembler()
    assembled = assembler.assemble(retrieval_result)

    records = assembled.get("structured_evidence", [])
    assert len(records) > 0
    rec = records[0]
    assert "failure_log" in rec
    assert rec["failure_log"]["exception_name"] == "AccessError"

    entity_types = {e["type"] for e in assembled["entities"]}
    assert "LogChunk" in entity_types
    assert "Execution" in entity_types

    rel_names = {r["relationship"] for r in assembled["relationships"]}
    assert "HAS_FAILURE_LOG" in rel_names

