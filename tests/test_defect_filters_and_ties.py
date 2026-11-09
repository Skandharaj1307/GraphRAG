import pytest
from graph.graph_retriever import Neo4jGraphRetriever
from graph.evaluation_v2.run_eval_v2 import compute_retrieval_metrics


@pytest.fixture(scope="module")
def retriever():
    r = Neo4jGraphRetriever()
    yield r
    r.close()


def test_regression_yes_in_ecommerce_returns_264(retriever):
    """Verify that regression=Yes in eCommerce returns exactly 264."""
    # Test canonical form
    res1 = retriever.defects_by_filters({"module": "eCommerce", "regression": "Yes"})
    assert res1["total"] == 264
    assert res1["filters_applied"]["module"] == "eCommerce"
    assert res1["filters_applied"]["regression"] == "Yes"

    # Test value normalization with lowercase and boolean
    res2 = retriever.defects_by_filters({"module": "ecommerce", "regression": "yes"})
    assert res2["total"] == 264

    res3 = retriever.defects_by_filters({"module": "eCommerce", "regression": True})
    assert res3["total"] == 264


def test_severity_blocker_and_environment_prod_returns_800(retriever):
    """Verify that severity=Blocker and environment=PROD returns exactly 800."""
    # Test canonical form
    res1 = retriever.defects_by_filters({"severity": "Blocker", "environment": "PROD"})
    assert res1["total"] == 800
    assert res1["filters_applied"]["severity"] == "Blocker"
    assert res1["filters_applied"]["environment"] == "PROD"

    # Test value normalization with lowercase
    res2 = retriever.defects_by_filters({"severity": "blocker", "environment": "prod"})
    assert res2["total"] == 800

    # Also test in aggregate_defects with filters
    agg_res = retriever.aggregate_defects(
        group_by="module",
        filters={"severity": "blocker", "environment": "prod"},
        limit=50
    )
    assert agg_res["total"] == 800


def test_tied_top_5_case(retriever):
    """Verify tied top-5 aggregation and eval metric handling with tie_at_cutoff."""
    # Aggregation with ORDER BY count DESC, key ASC
    agg_res = retriever.aggregate_defects(group_by="module", limit=5)
    rows = agg_res["rows"]
    assert len(rows) == 5

    # Top 4 are Studio (524), Knowledge (520), HR (517), Helpdesk (516)
    assert rows[0] == {"key": "Studio", "count": 524}
    assert rows[1] == {"key": "Knowledge", "count": 520}
    assert rows[2] == {"key": "HR", "count": 517}
    assert rows[3] == {"key": "Helpdesk", "count": 516}

    # Rank 5 is Inventory (515) due to key ASC breaking tie with Payroll (515) and Subscriptions (515)
    assert rows[4] == {"key": "Inventory", "count": 515}

    # Evaluate metric with tie_at_cutoff
    gold_item = {
        "id": "G2-TEST-TIE",
        "query_type": "aggregation",
        "question": "What are the top 5 modules with the highest number of defects?",
        "expected_group_by": "module",
        "expected_filters": {},
        "tie_at_cutoff": ["Inventory", "Payroll", "Subscriptions"],
        "gold_facts": [
            {"entity": "Studio", "field": "defect_count", "value": 524},
            {"entity": "Knowledge", "field": "defect_count", "value": 520},
            {"entity": "HR", "field": "defect_count", "value": 517},
            {"entity": "Helpdesk", "field": "defect_count", "value": 516},
            {"entity": "Inventory", "field": "defect_count", "value": 515},
        ],
        "gold_nodes": [],
    }

    # Context with Inventory (exact match)
    ctx1 = {"aggregates": {"rows": rows, "filters_applied": {}}}
    m1 = compute_retrieval_metrics(gold_item, ctx1)
    assert m1["agg_pairs_match"] == 1.0
    assert m1["agg_order_match"] == 1.0
    assert m1["aggregation_exact"] == 1.0

    # Context with Payroll at cutoff (alternative tied key)
    alt_rows = list(rows[:4]) + [{"key": "Payroll", "count": 515}]
    ctx2 = {"aggregates": {"rows": alt_rows, "filters_applied": {}}}
    m2 = compute_retrieval_metrics(gold_item, ctx2)
    assert m2["agg_pairs_match"] == 1.0
    assert m2["agg_order_match"] == 1.0
    assert m2["aggregation_exact"] == 1.0


def test_unsupported_filter_not_dropped(retriever):
    """Verify that unsupported filters are placed into unmapped_filters rather than dropped silently."""
    res = retriever.defects_by_filters({"nonexistent_filter_xyz": "value123", "severity": "Blocker"})
    assert "nonexistent_filter_xyz" in res["unmapped_filters"]
    assert res["filters_applied"]["severity"] == "Blocker"

