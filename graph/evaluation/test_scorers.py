import pytest
import re
from graph.evaluation.scorers import (
    normalize_text,
    normalize_id,
    score_extraction,
    score_intent,
    score_routing,
    score_retrieval,
    compute_text_metrics,
    score_final_answer,
    extract_ids_from_text,
)


def test_normalize_functions_dashes():
    # Test non-breaking hyphen U+2011 and smart quotes
    assert normalize_text("BUG\u2011005861 \u201cDetails\u201d") == "bug-005861 details"
    assert normalize_id(" bug\u2011005861 ") == "BUG-005861"


def test_score_extraction():
    expected = {
        "defect_ids": ["BUG-100"],
        "test_case_ids": ["TC-200"],
        "execution_ids": []
    }
    extracted_exact = {
        "defect_ids": ["bug\u2011100"],
        "test_case_ids": ["TC-200"],
        "execution_ids": []
    }
    res = score_extraction(extracted_exact, expected)
    assert res["overall_exact_match"] is True
    assert res["defect_ids"]["exact_match"] is True

    extracted_wrong = {
        "defect_ids": ["BUG-100", "BUG-999"],
        "test_case_ids": ["TC-200"],
        "execution_ids": []
    }
    res_wrong = score_extraction(extracted_wrong, expected)
    assert res_wrong["overall_exact_match"] is False
    assert res_wrong["defect_ids"]["precision"] == 0.5
    assert res_wrong["defect_ids"]["recall"] == 1.0


def test_score_intent_raw_and_aliased():
    aliases = {"defect_lookup": ["defect_analysis"]}

    # Match raw
    res1 = score_intent("defect_lookup", "defect_lookup", aliases=aliases)
    assert res1["intent_acc_raw"] is True
    assert res1["intent_acc_aliased"] is True

    # Mismatch raw, match aliased
    res2 = score_intent("defect_analysis", "defect_lookup", aliases=aliases)
    assert res2["intent_acc_raw"] is False
    assert res2["intent_acc_aliased"] is True

    # Mismatch both
    res3 = score_intent("testcase_lookup", "defect_lookup", aliases=aliases)
    assert res3["intent_acc_raw"] is False
    assert res3["intent_acc_aliased"] is False


def test_score_routing():
    assert score_routing("neo4j", "neo4j")["route_exact_match"] is True
    assert score_routing("lightrag", "neo4j")["route_exact_match"] is False


def test_extract_ids_from_text():
    # Context with non-breaking hyphens
    text = "Error found in bug\u2011001234 during run exec-998811 for test case tc-000111."
    ids = extract_ids_from_text(text)
    assert ids["defect_ids"] == ["BUG-001234"]
    assert ids["execution_ids"] == ["EXEC-998811"]
    assert ids["test_case_ids"] == ["TC-000111"]


def test_compute_text_metrics():
    gold = "The manager verified the employee record after verifying documents."
    # Verbose answer containing gold
    verbose_ans = "Based on the retrieved evidence for BUG-001, Severity: Major. Root cause: The manager verified the employee record after verifying documents."

    metrics = compute_text_metrics(verbose_ans, gold)
    assert metrics["substring_match"] is True
    assert metrics["gold_recall"] == 1.0
    assert metrics["pass_text"] is True

    # Slightly reworded answer with gold recall >= 0.8
    reworded_ans = "The manager verified the employee record after verifying related documents."
    metrics2 = compute_text_metrics(reworded_ans, gold)
    assert metrics2["gold_recall"] >= 0.8
    assert metrics2["pass_text"] is True


def test_score_retrieval():
    gold = {"defect_id": "BUG-001", "severity": "Critical", "defect_ids": ["BUG-001", "BUG-101", "BUG-102"]}
    context = "Retrieved defect bug-001 with severity critical. Linked bugs: bug-101, bug-102."

    res = score_retrieval(context, gold, "neo4j")
    assert res["empty_retrieval"] is False
    assert res["field_recall"] == 1.0
    assert res["set_f1"] == 1.0
    assert res["pass_retrieval"] is True

    # Single-field lookup has set_f1 as None
    single_gold = {"defect_id": "BUG-001", "root_cause": "Database connection error"}
    res_single = score_retrieval(context, single_gold, "neo4j")
    assert res_single["set_f1"] is None


def test_score_final_answer_field_filtering():
    # defect_lookup asks for root_cause. Title should not be scored!
    gold = {
        "defect_id": "BUG-005861",
        "root_cause": "The employee record was not created properly due to missing validation.",
        "title": "Unrequested title metadata string"
    }
    scored_map = {"defect_lookup": ["root_cause"]}
    answer = "The root cause of defect BUG-005861 is: The employee record was not created properly due to missing validation."

    res = score_final_answer(answer, gold, qtype="defect_lookup", scored_fields_map=scored_map)
    assert res["pass_answer"] is True
    assert res["answer_correctness"] == 1.0
    assert "title" not in res["field_details"]
