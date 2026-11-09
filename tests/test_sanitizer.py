import pytest
from graph.final_llm import sanitize_llm_output
from graph.evaluation.scorers import detect_reasoning_leak


def test_sanitize_think_tags_enclosed():
    raw = (
        "<think>\n"
        "The user is asking about BUG-000176.\n"
        "Let me check the properties.\n"
        "Severity is Critical.\n"
        "</think>\n"
        "Defect BUG-000176 has Critical severity and is currently Open."
    )
    cleaned = sanitize_llm_output(raw)
    assert "<think>" not in cleaned
    assert "</think>" not in cleaned
    assert "Defect BUG-000176 has Critical severity and is currently Open." == cleaned
    assert not detect_reasoning_leak(cleaned)


def test_sanitize_think_tags_truncated():
    raw = (
        "<think>\n"
        "The user wants test case executions.\n"
        "I need to check EXEC-003016..."
    )
    cleaned = sanitize_llm_output(raw)
    assert cleaned == ""
    assert not detect_reasoning_leak(cleaned)


def test_sanitize_heres_a_thinking_process_with_answer_marker():
    raw = (
        "Here's a thinking process:\n\n"
        "1.  **Analyze User Question**: \n"
        "   - 'Which test case produced defect BUG-003422, and who executed the run in which build?'\n\n"
        "2.  **Examine the Context**:\n"
        "   - The context is a JSON structure from GraphRAG retrieval.\n\n"
        "**Answer:**\n"
        "Test case TC-004710 produced defect BUG-003422. The run was executed in build B-5388 by Jacqueline Sheppard."
    )
    cleaned = sanitize_llm_output(raw)
    assert not detect_reasoning_leak(cleaned)
    assert "TC-004710" in cleaned
    assert "BUG-003422" in cleaned
    assert "Jacqueline Sheppard" in cleaned
    assert "thinking process" not in cleaned.lower()


def test_sanitize_thinking_process_based_on_evidence():
    raw = (
        "Here is a thinking process:\n"
        "Let me inspect the defect details for BUG-009290.\n"
        "Execution is EXEC-004665.\n\n"
        "Based on the provided evidence:\n"
        "Test case TC-013388 produced defect BUG-009290."
    )
    cleaned = sanitize_llm_output(raw)
    assert not detect_reasoning_leak(cleaned)
    assert cleaned.startswith("Based on the provided evidence:")
    assert "TC-013388" in cleaned


def test_sanitize_conversational_preamble():
    raw = (
        "Hello! Sure, here is the answer:\n"
        "Test case TC-000001 had execution EXEC-003016, which found defects BUG-000176 and BUG-009797."
    )
    cleaned = sanitize_llm_output(raw)
    assert cleaned.startswith("Test case TC-000001")
    assert "Hello" not in cleaned
    assert "Sure" not in cleaned


def test_clean_output_preserved():
    clean = "Test case TC-000001 had execution EXEC-003016, which found defects BUG-000176 and BUG-009797."
    cleaned = sanitize_llm_output(clean)
    assert cleaned == clean
    assert not detect_reasoning_leak(cleaned)

