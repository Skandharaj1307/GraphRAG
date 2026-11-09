import pytest
from graph.graph_retriever import Neo4jGraphRetriever
from graph.query_understanding import validate_and_map_filters


def test_aggregate_defects_with_list_filters():
    retriever = Neo4jGraphRetriever()
    try:
        # Group by module with list filter for severity
        res = retriever.aggregate_defects(
            group_by="module",
            filters={"severity": ["Critical", "Blocker"]},
            limit=5,
        )
        assert res["group_by"] == "module"
        assert len(res["rows"]) <= 5
        assert res["total"] > 0
        keys = [r["key"] for r in res["rows"]]
        assert "Payroll" in keys
        assert "HR" in keys
    finally:
        retriever.close()


def test_aggregate_defects_with_scalar_filter():
    retriever = Neo4jGraphRetriever()
    try:
        # Group by module with scalar filter for regression
        res = retriever.aggregate_defects(
            group_by="module",
            filters={"regression": "Yes"},
            limit=5,
        )
        assert res["group_by"] == "module"
        assert len(res["rows"]) <= 5
        assert res["total"] > 0
        keys = [r["key"] for r in res["rows"]]
        assert "HR" in keys

        # Group by module with alias type: regression
        res2 = retriever.aggregate_defects(
            group_by="module",
            filters={"type": "regression"},
            limit=5,
        )
        assert res2["group_by"] == "module"
        assert len(res2["rows"]) <= 5
        assert [r["key"] for r in res2["rows"]] == keys
    finally:
        retriever.close()


def test_aggregate_defects_injection_protection():
    retriever = Neo4jGraphRetriever()
    try:
        # Invalid group_by must raise ValueError
        with pytest.raises(ValueError, match="not in defect aggregation whitelist"):
            retriever.aggregate_defects("malicious_field; DROP DATABASE;")

        # Invalid filter field must raise ValueError
        with pytest.raises(ValueError, match="not allowed"):
            retriever.aggregate_defects("module", filters={"malicious_attr": "evil"})
    finally:
        retriever.close()


def test_count_defects_by_and_top_modules_backward_compat():
    retriever = Neo4jGraphRetriever()
    try:
        # count_defects_by wrapper
        res1 = retriever.count_defects_by("severity")
        assert res1["group_by"] == "severity"
        assert res1["total"] > 0
        assert len(res1["rows"]) > 0

        # top_modules_by_defects wrapper
        res2 = retriever.top_modules_by_defects(k=5)
        assert res2["group_by"] == "module"
        assert len(res2["rows"]) <= 5
    finally:
        retriever.close()


def test_validate_and_map_filters_multivalue():
    vocab = {
        "severity": ["Critical", "Blocker", "Major", "Minor"],
        "environments": ["DEV", "QA", "UAT", "STAGING"],
        "modules": ["Payroll", "HR", "Documents", "Studio"],
    }

    # 1. Comma-separated string
    val, unmapped = validate_and_map_filters({"severity": "Critical, Blocker"}, vocab)
    assert val["severity"] == ["Critical", "Blocker"]
    assert unmapped == []

    # 2. List of values with aliases
    val2, unmapped2 = validate_and_map_filters({"severity": ["crit", "blocker"]}, vocab)
    assert val2["severity"] == ["Critical", "Blocker"]
    assert unmapped2 == []

    # 3. Boolean/regression string
    val3, unmapped3 = validate_and_map_filters({"regression": "yes"}, vocab)
    assert val3["regression"] == "Yes"
    assert unmapped3 == []

