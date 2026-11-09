"""
Unit tests for the Gold Evaluation Set Generator (Phase 2)
Tests:
- id_lookup generator
- two_hop (2-hop defect_to_testcase and testcase_to_defects) generator
- aggregation generator
- unanswerable generator
"""

import random
import pytest
from unittest.mock import MagicMock
from graph.evaluation_v2.gold.generate_gold import (
    generate_id_lookup,
    generate_two_hop,
    generate_aggregation,
    generate_unanswerable
)


def test_generate_unanswerable():
    rng = random.Random(2026)
    records = generate_unanswerable(rng)
    assert len(records) == 20
    for r in records:
        assert r["query_type"] == "unanswerable"
        assert r["answerable"] is False
        assert r["gold_answer"] == "NOT_IN_DATA"
        assert "gold_query" in r
        assert r["difficulty"] in ["easy", "medium", "hard"]
        assert isinstance(r["expected_ids"], dict)


def test_generate_id_lookup_mocked():
    rng = random.Random(2026)
    mock_session = MagicMock()
    
    # Mock defect, testcase, and execution queries
    mock_defects = [
        {"id": f"BUG-{i:06d}", "severity": "Critical", "priority": "P1", "status": "Open",
         "module": "POS", "assigned_to": "Tester", "root_cause": "NullPointer in handler", "developer": "Dev"}
        for i in range(1, 25)
    ]
    mock_testcases = [
        {"id": f"TC-{i:06d}", "feature": "Checkout flow", "framework": "Selenium",
         "tester": "Alice", "release": "v1.0", "priority": "High"}
        for i in range(1, 25)
    ]
    mock_executions = [
        {"id": f"EXEC-{i:06d}", "env": "UAT", "browser": "Chrome", "os": "Linux",
         "status": "Passed", "exec_time": 120}
        for i in range(1, 25)
    ]
    
    mock_res_def = MagicMock()
    mock_res_def.data.return_value = mock_defects
    mock_res_tc = MagicMock()
    mock_res_tc.data.return_value = mock_testcases
    mock_res_ex = MagicMock()
    mock_res_ex.data.return_value = mock_executions
    
    mock_session.run.side_effect = [mock_res_def, mock_res_tc, mock_res_ex]
    
    records = generate_id_lookup(mock_session, rng)
    assert len(records) == 30
    for r in records:
        assert r["query_type"] == "id_lookup"
        assert r["answerable"] is True
        assert len(r["gold_nodes"]) > 0
        assert len(r["gold_facts"]) > 0
        assert r["gold_query"].startswith("MATCH")


def test_generate_two_hop_mocked():
    rng = random.Random(2026)
    mock_session = MagicMock()
    
    mock_multi = [
        {"did": f"BUG-{i:06d}", "tcid": f"TC-{i:06d}",
         "exec_details": [{"exec_id": f"EXEC-{i}01", "build": "B-100", "tester": "Bob"},
                          {"exec_id": f"EXEC-{i}02", "build": "B-101", "tester": "Carol"}]}
        for i in range(1, 20)
    ]
    mock_single = [
        {"did": f"BUG-{i+20:06d}", "tcid": f"TC-{i+20:06d}",
         "exec_details": [{"exec_id": f"EXEC-{i}03", "build": "B-102", "tester": "Dave"}]}
        for i in range(1, 20)
    ]
    mock_tc2d = [
        {"tcid": f"TC-{i:06d}", "defect_ids": [f"BUG-{i:06d}", f"BUG-{i+50:06d}"], "defect_count": 2}
        for i in range(1, 30)
    ]
    
    m1 = MagicMock(); m1.data.return_value = mock_multi
    m2 = MagicMock(); m2.data.return_value = mock_single
    m3 = MagicMock(); m3.data.return_value = mock_tc2d
    mock_session.run.side_effect = [m1, m2, m3]
    
    records = generate_two_hop(mock_session, rng)
    assert len(records) == 30
    d2tc = [r for r in records if r["query_type"] == "defect_to_testcase"]
    tc2d = [r for r in records if r["query_type"] == "testcase_to_defects"]
    assert len(d2tc) == 15
    assert len(tc2d) == 15
    for r in records:
        assert r["answerable"] is True
        assert len(r["gold_nodes"]) >= 2
        assert "MATCH" in r["gold_query"]


def test_generate_aggregation_mocked():
    rng = random.Random(2026)
    mock_session = MagicMock()
    
    mock_mod = [{"key": "POS", "cnt": 50}, {"key": "HR", "cnt": 40}, {"key": "CRM", "cnt": 30}]
    mock_sev = [{"key": "Critical", "cnt": 20}, {"key": "Minor", "cnt": 80}]
    mock_stat = [{"key": "Open", "cnt": 15}, {"key": "Closed", "cnt": 35}]
    mock_crit = [{"key": "Studio", "cnt": 12}, {"key": "Payroll", "cnt": 10}]
    
    # 1 for mod, 1 for sev, 5 for status in modules, 1 for crit filter, 10 for how-many counts
    side_effects = []
    
    m_mod = MagicMock(); m_mod.data.return_value = mock_mod
    side_effects.append(m_mod)
    
    m_sev = MagicMock(); m_sev.data.return_value = mock_sev
    side_effects.append(m_sev)
    
    for _ in range(5):
        m_st = MagicMock(); m_st.data.return_value = mock_stat
        side_effects.append(m_st)
        
    m_crit = MagicMock(); m_crit.data.return_value = mock_crit
    side_effects.append(m_crit)
    
    for cnt in range(10):
        m_cnt = MagicMock(); m_cnt.single.return_value = {"total": 42}
        side_effects.append(m_cnt)
        
    mock_session.run.side_effect = side_effects
    
    records = generate_aggregation(mock_session, rng)
    assert len(records) == 30
    for r in records:
        assert r["query_type"] == "aggregation"
        assert r["answerable"] is True
        assert "MATCH" in r["gold_query"]
        assert len(r["gold_facts"]) > 0

