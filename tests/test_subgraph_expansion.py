import pytest
from graph.graph_retriever import Neo4jGraphRetriever
from graph.context_assembler import ContextAssembler


@pytest.fixture(scope="module")
def neo4j():
    retriever = Neo4jGraphRetriever()
    yield retriever
    retriever.close()


def test_defect_2hop_expansion_preserves_neighbors(neo4j):
    """
    Test BUG-003422 (target failure TEST-0051):
    Should return executions with tester and build_number,
    and testcases with test_case_id and module.
    """
    ctx = neo4j.get_full_defect_context("BUG-003422", limit=20)
    assert ctx is not None
    assert ctx["defect"]["defect_id"] == "BUG-003422"

    # Execution neighbor attributes
    assert "executions" in ctx
    assert len(ctx["executions"]) > 0
    testers = [e.get("tester") for e in ctx["executions"]]
    builds = [e.get("build_number") for e in ctx["executions"]]
    assert "Jacqueline Sheppard" in testers
    assert "B-5388" in builds

    # TestCase neighbor attributes
    assert "testcases" in ctx
    assert len(ctx["testcases"]) > 0
    tc_ids = [t.get("test_case_id") for t in ctx["testcases"]]
    assert "TC-004710" in tc_ids
    tc_modules = [t.get("module") for t in ctx["testcases"]]
    assert "Accounting" in tc_modules


def test_testcase_2hop_expansion(neo4j):
    """
    Test TC-005349:
    Should expand to connected defects and executions.
    """
    ctx = neo4j.get_testcase_context("TC-005349", limit=20)
    assert ctx is not None
    assert ctx["testcase"]["test_case_id"] == "TC-005349"

    # Defects linked directly or via execution
    assert "defects" in ctx
    assert len(ctx["defects"]) > 0
    defect_ids = [d.get("defect_id") for d in ctx["defects"]]
    assert "BUG-000950" in defect_ids


def test_context_assembler_preserves_distinct_neighbor_attributes(neo4j):
    """
    Verify ContextAssembler preserves Execution.tester, Execution.build_number,
    and TestCase.module distinctly in structured_evidence records.
    """
    raw_ctx = neo4j.get_full_defect_context("BUG-003422")
    retrieval_result = {
        "query": "Which test case and tester found defect BUG-003422?",
        "route": {"query_type": "specific_entity_lookup"},
        "neo4j": {
            "source": "neo4j",
            "results": [
                {
                    "type": "defect_context",
                    "id": "BUG-003422",
                    "data": raw_ctx,
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

    # Verify defect module and testcase module are not conflated
    assert rec["defect"]["defect_id"] == "BUG-003422"
    assert rec["defect"]["module"] == "Manufacturing"

    # Execution neighbor attributes preserved
    assert rec["execution"]["tester"] == "Jacqueline Sheppard"
    assert rec["execution"]["build_number"] == "B-5388"

    # TestCase neighbor attributes preserved
    assert rec["testcase"]["test_case_id"] == "TC-004710"
    assert rec["testcase"]["module"] == "Accounting"

    # Entities and relationships populated
    entity_ids = {e["id"] for e in assembled["entities"]}
    assert "BUG-003422" in entity_ids
    assert "TC-004710" in entity_ids
    assert "EXEC-018001" in entity_ids

    rels = {(r["source_id"], r["relationship"], r["target_id"]) for r in assembled["relationships"]}
    assert ("EXEC-018001", "FOUND_DEFECT", "BUG-003422") in rels
    assert ("TC-004710", "HAS_EXECUTION", "EXEC-018001") in rels
