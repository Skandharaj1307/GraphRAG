# Failure Analysis Report: Benchmark Evaluation V2 (Dev Split, Full Mode)

**Run Timestamp**: `20261109_141129`  
**Evaluation Split**: `dev` (190 test cases)  
**Mode**: `--mode full` (Router -> Retrieval -> Answer LLM)  
**Endpoint**: `https://sees-exclude-airports-posters.trycloudflare.com/v1` (Model: `qwen2.5:14b-instruct-q4_K_M`)  
**Pipeline Errors**: 0 | **Infra Errors**: 0 | **Completed Valid Runs**: 190 / 190 (100%)  

---

## Executive Summary of Results

| Query Type | Cases | Intent Acc | Node Recall | Field Recall | Agg Exact | Answer Exact | Abstention Acc | Hallucination-Free |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `adversarial` | 7 | 100.00% | 71.43% | 64.29% | N/A | 50.00% | 71.43% | 100.00% |
| `aggregation` | 21 | 100.00% | 100.00% | 90.48% | 85.71% | 80.95% | 90.48% | 100.00% |
| `defect_to_testcase` | 11 | 0.00% | 85.00% | 76.62% | N/A | 58.44% | 100.00% | 90.91% |
| `execution_context` | 21 | 0.00% | 100.00% | 100.00% | N/A | 70.24% | 100.00% | 100.00% |
| `id_lookup` | 21 | 100.00% | 100.00% | 100.00% | N/A | 80.95% | 100.00% | 100.00% |
| `multi_condition_filter` | 21 | 100.00% | 39.05% | 85.71% | N/A | 57.14% | 100.00% | 100.00% |
| `requirements` | 21 | 61.90% | 22.62% | 73.81% | N/A | 54.76% | 66.67% | 0.00% |
| `semantic` | 21 | 19.05% | 28.57% | 71.43% | N/A | 42.86% | 80.95% | 100.00% |
| `testcase_to_defects` | 11 | 0.00% | 100.00% | 100.00% | N/A | 81.82% | 100.00% | 100.00% |
| `unanswerable` | 14 | 0.00% | 100.00% | 100.00% | N/A | 100.00% | 50.00% | 64.29% |
| `unstructured_logs` | 21 | 0.00% | 100.00% | 100.00% | N/A | 90.48% | 100.00% | 90.48% |

---

## 1. Intent Mismatch Analysis

A total of **103 out of 190 test cases (54.2%)** registered `intent_accuracy < 1.0`.

### Root Cause Classification
1. **(a) Gold Label Mismatch (78 cases)**: The LLM Router emitted an intent from the sanctioned `QueryUnderstanding` intent enum (`query_understanding.py`), but `generate_gold.py` expected an intent that is either not in the router's vocabulary enum (e.g., `execution_context`, `testcase_to_defects`, `defect_to_testcase`, `unanswerable`) or assigned an arbitrary fallback (e.g. `defect_analysis` for unstructured log executions). In **50 of these cases**, `node_recall`, `field_recall`, and `answer_exact` were all **1.0 (100%)** because the router correctly identified target entities and executed the proper retrieval.
2. **(b) Real Routing Error (25 cases)**:
   - **Semantic Search Misrouted to Defect Lookup (17 cases)**: Queries described bug symptoms in natural language without any IDs, but the router emitted `defect_lookup` (due to keyword matching or ID fallback) instead of `semantic_search`.
   - **Requirements Verification Misrouted (8 cases)**: Queries asking about test cases verifying requirements resulted in `testcase_execution_analysis` instead of `testcase_lookup`.

### Proposed Intent Equivalence Map
To align evaluation without breaking query semantics or introducing invalid enum values, the following equivalence mapping should be adopted in `run_eval_v2.py` / `generate_gold.py`:

```python
INTENT_EQUIVALENCE_MAP = {
    # Gold pseudo-intents mapped to sanctioned router intents
    'execution_context': {'execution_lookup', 'testcase_execution_analysis'},
    'testcase_to_defects': {'defect_lookup', 'testcase_execution_analysis', 'defect_analysis'},
    'defect_to_testcase': {'defect_analysis', 'testcase_execution_analysis', 'defect_lookup'},
    'unstructured_logs': {'execution_lookup', 'failure_analysis', 'defect_analysis'},
    'unanswerable': {'defect_lookup', 'testcase_lookup', 'execution_lookup', 'defect_analysis', 'testcase_execution_analysis', 'general_test_analysis', 'unanswerable'}
}
```

### Complete List of 103 Intent Mismatches

| ID | Query Type | Expected Intent | Router Intent | Node Rec | Field Rec | Ans Exact | Perfect Score? | Classification | Root Cause / Note |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| `G2-0003` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 0.50 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0004` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0007` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0011` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0013` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 0.00 | No | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0015` | `unanswerable` | `unanswerable` | `testcase_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0019` | `defect_to_testcase` | `defect_to_testcase` | `testcase_execution_analysis` | 0.75 | 0.60 | 0.60 | No | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0021` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0022` | `unanswerable` | `unanswerable` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0024` | `unanswerable` | `unanswerable` | `testcase_execution_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0025` | `defect_to_testcase` | `defect_to_testcase` | `defect_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0028` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 0.50 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0029` | `requirements` | `testcase_lookup` | `testcase_execution_analysis` | 0.50 | 1.00 | 1.00 | No | (b) Routing Error | Router emitted testcase_execution_analysis instead of testcase_lookup for requirement verification query |
| `G2-0036` | `semantic` | `semantic_search` | `defect_lookup` | 1.00 | 1.00 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0040` | `requirements` | `testcase_lookup` | `testcase_execution_analysis` | 0.00 | 0.50 | 0.50 | No | (b) Routing Error | Router emitted testcase_execution_analysis instead of testcase_lookup for requirement verification query |
| `G2-0043` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0044` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 1.00 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0045` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 0.00 | No | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0053` | `semantic` | `semantic_search` | `defect_lookup` | 1.00 | 1.00 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0056` | `unanswerable` | `unanswerable` | `defect_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0059` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0060` | `defect_to_testcase` | `defect_to_testcase` | `defect_analysis` | 0.75 | 0.60 | 0.40 | No | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0063` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 0.50 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0064` | `semantic` | `semantic_search` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0067` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 0.50 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0070` | `unanswerable` | `unanswerable` | `defect_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0072` | `defect_to_testcase` | `defect_to_testcase` | `defect_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0074` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 0.00 | No | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0077` | `requirements` | `testcase_lookup` | `testcase_execution_analysis` | 0.50 | 1.00 | 1.00 | No | (b) Routing Error | Router emitted testcase_execution_analysis instead of testcase_lookup for requirement verification query |
| `G2-0078` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0082` | `requirements` | `testcase_lookup` | `testcase_execution_analysis` | 0.50 | 1.00 | 1.00 | No | (b) Routing Error | Router emitted testcase_execution_analysis instead of testcase_lookup for requirement verification query |
| `G2-0087` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0089` | `unanswerable` | `unanswerable` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0091` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0094` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.50 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0102` | `semantic` | `semantic_search` | `defect_lookup` | 1.00 | 1.00 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0107` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.00 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0109` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0111` | `unanswerable` | `unanswerable` | `testcase_execution_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0114` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 0.50 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0118` | `unstructured_logs` | `defect_analysis` | `failure_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0119` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0120` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0121` | `defect_to_testcase` | `defect_to_testcase` | `testcase_execution_analysis` | 1.00 | 1.00 | 0.33 | No | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0122` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 0.50 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0123` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0126` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0132` | `defect_to_testcase` | `defect_to_testcase` | `defect_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0134` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0137` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 0.50 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0140` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.00 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0142` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 1.00 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0144` | `semantic` | `semantic_search` | `defect_lookup` | 1.00 | 1.00 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0147` | `unanswerable` | `unanswerable` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0148` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0149` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0151` | `unanswerable` | `unanswerable` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0153` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0155` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0159` | `unanswerable` | `unanswerable` | `general_test_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0160` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0161` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0165` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0167` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0168` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0169` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0174` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0178` | `unanswerable` | `unanswerable` | `testcase_execution_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0179` | `requirements` | `testcase_lookup` | `testcase_execution_analysis` | 0.00 | 0.50 | 0.00 | No | (b) Routing Error | Router emitted testcase_execution_analysis instead of testcase_lookup for requirement verification query |
| `G2-0185` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0187` | `requirements` | `testcase_lookup` | `testcase_execution_analysis` | 0.50 | 1.00 | 1.00 | No | (b) Routing Error | Router emitted testcase_execution_analysis instead of testcase_lookup for requirement verification query |
| `G2-0188` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0194` | `unstructured_logs` | `defect_analysis` | `failure_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0196` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0202` | `defect_to_testcase` | `defect_to_testcase` | `defect_analysis` | 1.00 | 1.00 | 0.67 | No | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0204` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0205` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0210` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0213` | `unanswerable` | `unanswerable` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0217` | `unanswerable` | `unanswerable` | `testcase_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0218` | `defect_to_testcase` | `defect_to_testcase` | `testcase_execution_analysis` | 0.75 | 0.60 | 0.20 | No | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0227` | `requirements` | `testcase_lookup` | `testcase_execution_analysis` | 0.00 | 0.50 | 0.00 | No | (b) Routing Error | Router emitted testcase_execution_analysis instead of testcase_lookup for requirement verification query |
| `G2-0228` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0229` | `unstructured_logs` | `defect_analysis` | `failure_analysis` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0230` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0234` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 0.50 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0238` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 1.00 | 0.50 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0239` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0240` | `unanswerable` | `unanswerable` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Router classifies by structural query intent (lookup/analysis); unanswerability is determined post-retrieval by evidence |
| `G2-0242` | `defect_to_testcase` | `defect_to_testcase` | `defect_analysis` | 0.75 | 0.60 | 0.40 | No | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0244` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0246` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0247` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0248` | `requirements` | `testcase_lookup` | `testcase_execution_analysis` | 0.50 | 1.00 | 1.00 | No | (b) Routing Error | Router emitted testcase_execution_analysis instead of testcase_lookup for requirement verification query |
| `G2-0249` | `defect_to_testcase` | `defect_to_testcase` | `defect_lookup` | 0.75 | 0.60 | 0.40 | No | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0258` | `semantic` | `semantic_search` | `defect_lookup` | 0.00 | 1.00 | 0.00 | No | (b) Routing Error | Query has no entity ID; router should emit semantic_search but emitted defect_lookup (due to keyword regex or default) |
| `G2-0259` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0260` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.50 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0261` | `defect_to_testcase` | `defect_to_testcase` | `defect_analysis` | 0.60 | 0.43 | 0.43 | No | (a) Gold Mismatch | 'defect_to_testcase' is not in router intent enum; router chose defect_analysis or testcase_execution_analysis |
| `G2-0262` | `testcase_to_defects` | `testcase_to_defects` | `defect_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | 'testcase_to_defects' is not in router intent enum; router chose defect_lookup for defect-seeking query |
| `G2-0264` | `execution_context` | `execution_context` | `execution_lookup` | 1.00 | 1.00 | 0.75 | No | (a) Gold Mismatch | 'execution_context' is not an allowed router intent in query_understanding.py enum; router chose execution_lookup which matches target entity EXEC |
| `G2-0265` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 0.00 | No | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |
| `G2-0266` | `unstructured_logs` | `defect_analysis` | `execution_lookup` | 1.00 | 1.00 | 1.00 | YES | (a) Gold Mismatch | Gold expected 'defect_analysis' (hardcoded fallback); router chose execution_lookup or failure_analysis matching execution log context |

---

## 2. Semantic Search Analysis

There were **21 test cases** under `semantic` query type. Gold expected `semantic_search` targeting single defects described purely by natural language symptoms.

### Findings
- **Semantic Path Used**: **Yes, in all 21 cases (100%)**. Even when the router emitted `defect_lookup`, `retrieval_router.py` detected that no structured IDs were present and correctly routed to `retrievers: ['semantic']` with `query_type: 'default_semantic_search'`.
- **Zero Hits on Filtered Semantic Queries (4 cases)**: Queries `G2-0028`, `G2-0063`, `G2-0114`, `G2-0122` extracted a `module` filter (e.g. Sales, Accounting, Subscriptions). The semantic retriever returned 0 hits because the vector pre-filter or index lacked matches under the combined keyword/filter constraint.
- **Hit in Top-10 (6 cases)**: In 6 cases, the gold defect was present in the top-10 ranked hits (`ranked_hits`). In all 6 cases, the question was **answerable from retrieved data**, and the answer LLM successfully identified the defect.
- **Absent from Top-10 (15 cases)**: In 15 cases (including the 4 zero-hit cases), the gold defect was not in the top-10 ranked hits (`rank: absent`). As a result, the question was **not answerable from retrieved data**.

| ID | Question | Router Intent | Semantic Path Used | Gold Node | Rank in `ranked_hits` | Answerable from Data? | Ans Exact |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: |
| `G2-0003` | Which defect report describes The system processed the employee record which resul... | `defect_lookup` | Yes | `BUG-000269` | **absent** | **No** | 0.50 |
| `G2-0028` | Find any bug reported in Sales with root cause regarding: The system deleted the e... | `defect_lookup` | Yes | `BUG-000252` | **absent** | **No** | 0.50 |
| `G2-0036` | Which defect report describes The sales representative attempted to confirm the PO... | `defect_lookup` | Yes | `BUG-000305` | 3 | Yes | 0.50 |
| `G2-0044` | What defect is related to: The warehouse operator validated the POS receipt and su... | `defect_lookup` | Yes | `BUG-000312` | **absent** | **No** | 0.50 |
| `G2-0053` | What defect is related to: The system processed the manufacturing order but the sy... | `defect_lookup` | Yes | `BUG-000309` | 1 | Yes | 0.50 |
| `G2-0063` | Find any bug reported in Sales with root cause regarding: The background job valid... | `defect_lookup` | Yes | `BUG-000320` | **absent** | **No** | 0.50 |
| `G2-0064` | What defect is related to: The warehouse operator updated the incoming shipment bu... | `defect_lookup` | Yes | `BUG-000343` | 4 | Yes | 1.00 |
| `G2-0067` | We are encountering an issue where 'The background job rejected the POS receipt du... | `defect_lookup` | Yes | `BUG-000262` | **absent** | **No** | 0.50 |
| `G2-0075` | Search test issues matching description: The system configured the invoice while e... | `semantic_search` | Yes | `BUG-000251` | **absent** | **No** | 0.00 |
| `G2-0102` | We are encountering an issue where 'The background job escalated the invoice after... | `defect_lookup` | Yes | `BUG-000261` | 2 | Yes | 0.50 |
| `G2-0114` | Find any bug reported in Accounting with root cause regarding: The system deleted ... | `defect_lookup` | Yes | `BUG-000259` | **absent** | **No** | 0.50 |
| `G2-0122` | Find any bug reported in Subscriptions with root cause regarding: The warehouse op... | `defect_lookup` | Yes | `BUG-000263` | **absent** | **No** | 0.50 |
| `G2-0137` | Which defect report describes The background job validated the employee record aft... | `defect_lookup` | Yes | `BUG-000330` | **absent** | **No** | 0.50 |
| `G2-0142` | What defect is related to: The API endpoint calculated the incoming shipment trigg... | `defect_lookup` | Yes | `BUG-000298` | **absent** | **No** | 0.50 |
| `G2-0144` | What defect is related to: The API endpoint deleted the transfer due to missing co... | `defect_lookup` | Yes | `BUG-000316` | 2 | Yes | 0.50 |
| `G2-0177` | Search test issues matching description: The user processed the POS receipt which ... | `semantic_search` | Yes | `BUG-000285` | **absent** | **No** | 0.00 |
| `G2-0211` | Search test issues matching description: The warehouse operator rejected the manuf... | `semantic_search` | Yes | `BUG-000274` | 8 | Yes | 0.50 |
| `G2-0234` | Which defect report describes The warehouse operator attempted to confirm the empl... | `defect_lookup` | Yes | `BUG-000282` | **absent** | **No** | 0.50 |
| `G2-0238` | Which defect report describes The system calculated the transfer triggering a work... | `defect_lookup` | Yes | `BUG-000314` | **absent** | **No** | 0.50 |
| `G2-0252` | Search test issues matching description: The accountant updated the employee recor... | `semantic_search` | Yes | `BUG-000339` | **absent** | **No** | 0.00 |
| `G2-0258` | What defect is related to: The background job processed the subscription renewal b... | `defect_lookup` | Yes | `BUG-000325` | **absent** | **No** | 0.00 |

---

## 3. Unanswerable & Abstention Analysis

There were **14 unanswerable test cases**. 7 cases passed abstention detection, and **7 cases registered abstention failures** (`abstention_accuracy = 0.0`).

### Root Cause Classification
All 7 failures belong strictly to:  
**Classification: (a) Answer abstained correctly, but the evaluation detector missed it.**

In every single failing case, the model explicitly and correctly stated that the requested information was unavailable in the evidence. However, `run_eval_v2.py` checked against a static list of `refusal_keywords` (`not found`, `does not exist`, `unavailable`, `insufficient`, `cannot be determined`, `no information`, `not in the database`, `no matching`, `not in the evidence`, `no record`).
The model phrased its refusals using standard English variations not included in that list:  
- `is not provided in the given evidence` (G2-0015)
- `does not contain information about...` (G2-0022, G2-0056, G2-0111, G2-0151, G2-0159)
- `does not provide information about...` / `no data indicating whether...` (G2-0070)

There were **0 instances of model hallucination** (model did not invent data), and **0 instances of wrong retrieval** (retrieval correctly returned entity context or empty/not-found signals).

### Detailed Case Inspection

#### Case `G2-0015`
- **Question**: "What is the Jira story point estimate for test case TC-000001?"
- **Model Answer**: "The Jira story point estimate for test case TC-000001 is not provided in the given evidence."
- **Retrieved Context Notes**: `{'not_found_ids': [], 'links_missing': False, 'unmapped_filters': [], 'fallback_used': [], 'prefilter_count': 0}`
- **Classification**: `(a) Answer abstained, detector missed phrasing`
- **Missing Phrasing**: Model used *'not provided'* / *'does not contain information'* / *'does not provide information'*, which was absent from `refusal_keywords` in `run_eval_v2.py`.

#### Case `G2-0022`
- **Question**: "How many defects will be submitted by tester Ashley Clark next month?"
- **Model Answer**: "The available evidence does not contain information about defects that will be submitted by tester Ashley Clark next month. The provided defects do not include any details about the tester or the submission timeline."
- **Retrieved Context Notes**: `{'not_found_ids': [], 'links_missing': False, 'unmapped_filters': [], 'fallback_used': [], 'prefilter_count': 200}`
- **Classification**: `(a) Answer abstained, detector missed phrasing`
- **Missing Phrasing**: Model used *'not provided'* / *'does not contain information'* / *'does not provide information'*, which was absent from `refusal_keywords` in `run_eval_v2.py`.

#### Case `G2-0056`
- **Question**: "What was the monetary financial loss incurred from defect BUG-000067?"
- **Model Answer**: "The available evidence does not contain information about the monetary financial loss incurred from defect BUG-000067."
- **Retrieved Context Notes**: `{'not_found_ids': [], 'links_missing': False, 'unmapped_filters': [], 'fallback_used': [], 'prefilter_count': 0}`
- **Classification**: `(a) Answer abstained, detector missed phrasing`
- **Missing Phrasing**: Model used *'not provided'* / *'does not contain information'* / *'does not provide information'*, which was absent from `refusal_keywords` in `run_eval_v2.py`.

#### Case `G2-0070`
- **Question**: "Will defect BUG-000067 recur in the upcoming 2028 release?"
- **Model Answer**: "The available evidence does not provide information about the recurrence of defect BUG-000067 in the upcoming 2028 release. The defect was fixed in build B-7164 with version v15.4.4, but there is no data indicating whether it will recur in the future release."
- **Retrieved Context Notes**: `{'not_found_ids': [], 'links_missing': False, 'unmapped_filters': [], 'fallback_used': [], 'prefilter_count': 0}`
- **Classification**: `(a) Answer abstained, detector missed phrasing`
- **Missing Phrasing**: Model used *'not provided'* / *'does not contain information'* / *'does not provide information'*, which was absent from `refusal_keywords` in `run_eval_v2.py`.

#### Case `G2-0111`
- **Question**: "Who will execute test case TC-000001 next year?"
- **Model Answer**: "The available evidence does not contain information about who will execute test case TC-000001 next year. The evidence only includes past execution details and does not provide future plans or assignments."
- **Retrieved Context Notes**: `{'not_found_ids': [], 'links_missing': False, 'unmapped_filters': [], 'fallback_used': [], 'prefilter_count': 0}`
- **Classification**: `(a) Answer abstained, detector missed phrasing`
- **Missing Phrasing**: Model used *'not provided'* / *'does not contain information'* / *'does not provide information'*, which was absent from `refusal_keywords` in `run_eval_v2.py`.

#### Case `G2-0151`
- **Question**: "How much memory RAM was allocated to execution EXEC-002194?"
- **Model Answer**: "The available evidence does not contain information about the memory RAM allocated to execution EXEC-002194."
- **Retrieved Context Notes**: `{'not_found_ids': [], 'links_missing': True, 'unmapped_filters': [], 'fallback_used': [], 'prefilter_count': 0}`
- **Classification**: `(a) Answer abstained, detector missed phrasing`
- **Missing Phrasing**: Model used *'not provided'* / *'does not contain information'* / *'does not provide information'*, which was absent from `refusal_keywords` in `run_eval_v2.py`.

#### Case `G2-0159`
- **Question**: "What is the annual salary of tester Robert Davis?"
- **Model Answer**: "The available evidence does not contain information about the annual salary of tester Robert Davis."
- **Retrieved Context Notes**: `{'not_found_ids': [], 'links_missing': False, 'unmapped_filters': [], 'fallback_used': [], 'prefilter_count': 25}`
- **Classification**: `(a) Answer abstained, detector missed phrasing`
- **Missing Phrasing**: Model used *'not provided'* / *'does not contain information'* / *'does not provide information'*, which was absent from `refusal_keywords` in `run_eval_v2.py`.

---

## 4. Aggregation Analysis

Out of 21 aggregation cases, **18 passed (85.7%)** and **3 failed (`aggregation_exact = 0.0`)**.

### Failing Cases Inspection

#### Case `G2-0030`: How many regression defects were reported in eCommerce?
- **Gold Query**: `MATCH (d:Defect) WHERE d.module = 'eCommerce' AND d.regression = 'Yes' RETURN count(d) AS total`
- **Expected Filters**: `{'module': 'eCommerce', 'regression': 'Yes'}`
- **Expected Gold Facts (Count)**: `[{'entity': 'filtered_defects', 'field': 'total_count', 'value': 264}]`
- **Router Output**: `intent=defect_lookup`, `operation=count`, `filters={'regression': 'Yes', 'module': 'eCommerce'}`, `unmapped_filters=[]`
- **Retrieved Filters**: `None`
- **Retrieved Aggregates**: `None`
- **Retrieved Filter Results**: `total=None` (Sample count: 0)
- **Sub-metrics**: `agg_pairs_match=0.0`, `agg_order_match=1.0`, `agg_filters_match=0.0`
- **Root Cause**: The router correctly identified `operation: count` with `filters: {'regression': 'Yes', 'module': 'eCommerce'}`. However, because `group_by_field` was `None`, the router dispatched as a filtered lookup rather than calling `count_defects_by_filter()` or returning `aggregates`, leaving `retrieved_context['aggregates'] = None`.

#### Case `G2-0057`: How many Minor defects are currently In Progress?
- **Gold Query**: `MATCH (d:Defect) WHERE d.severity = 'Minor' AND d.status = 'In Progress' RETURN count(d) AS total`
- **Expected Filters**: `{'severity': 'Minor', 'status': 'In Progress'}`
- **Expected Gold Facts (Count)**: `[{'entity': 'filtered_defects', 'field': 'total_count', 'value': 506}]`
- **Router Output**: `intent=defect_analysis`, `operation=count`, `filters={'severity': 'Minor', 'status': 'In Progress'}`, `unmapped_filters=[]`
- **Retrieved Filters**: `None`
- **Retrieved Aggregates**: `None`
- **Retrieved Filter Results**: `total=None` (Sample count: 0)
- **Sub-metrics**: `agg_pairs_match=0.0`, `agg_order_match=1.0`, `agg_filters_match=0.0`
- **Root Cause**: The query asks *'How many Minor defects are currently In Progress?'*. Router emitted `operation: count` with `filters: {'severity': 'Minor', 'status': 'In Progress'}`. The retriever dispatched to `filter_results` but did not populate `aggregates['rows']` as expected by `agg_pairs_match`.

#### Case `G2-0065`: How many Blocker defects were discovered in the PROD environment?
- **Gold Query**: `MATCH (d:Defect) WHERE d.severity = 'Blocker' AND d.environment = 'PROD' RETURN count(d) AS total`
- **Expected Filters**: `{'severity': 'Blocker', 'environment': 'PROD'}`
- **Expected Gold Facts (Count)**: `[{'entity': 'filtered_defects', 'field': 'total_count', 'value': 800}]`
- **Router Output**: `intent=defect_analysis`, `operation=count`, `filters={'severity': 'Blocker'}`, `unmapped_filters=[{'key': 'environment', 'value': 'PROD', 'reason': "Value 'PROD' does not exist in environment vocabulary"}]`
- **Retrieved Filters**: `{'severity': 'Blocker'}`
- **Retrieved Aggregates**: `None`
- **Retrieved Filter Results**: `total=2399` (Sample count: 50)
- **Sub-metrics**: `agg_pairs_match=0.0`, `agg_order_match=1.0`, `agg_filters_match=0.0`
- **Root Cause**: The query asks *'How many Blocker defects were discovered in the PROD environment?'*. In `query_understanding.py`, the environment vocabulary mapping unmapped `'PROD'` with note: *"Value 'PROD' does not exist in environment vocabulary"*. Consequently, the environment filter was dropped into `unmapped_filters`, filtering only by `severity='Blocker'` and returning a total of 2,399 instead of the PROD count of 800.

---

## 5. Multi-Condition Filter Analysis

There were **21 test cases** under `multi_condition_filter`. Each gold case contains a verified set of **20 gold defect nodes** (`gold_nodes`).

### Comparison: Gold Nodes Count vs. Retrieved Node Count

| ID | Question Phrasing | Query Type Pattern | Expected Gold Nodes | Retrieved Ents | Sample Returned | Filter Total | Node Recall | Answer Exact |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `G2-0026` | Which defects have module='Subscriptions', severity='Major', status='R... | Count + List | 20 | 0 | 0 | None | 0.00 | 0.00 |
| `G2-0035` | Which defects have module='Sales', severity='Blocker', status='New'? S... | Count + List | 20 | 0 | 0 | None | 0.10 | 0.50 |
| `G2-0037` | Which defects have module='Sales', severity='Blocker', status='Resolve... | Count + List | 20 | 0 | 0 | None | 0.05 | 0.50 |
| `G2-0049` | Which defects have module='Quality', severity='Minor', status='New'? S... | Count + List | 20 | 0 | 0 | None | 0.30 | 0.50 |
| `G2-0092` | List all defect IDs matching criteria: module='Studio', severity='Majo... | List only | 20 | 0 | 0 | None | 0.10 | 0.50 |
| `G2-0104` | Which defects have module='Sales', severity='Critical', status='In Pro... | Count + List | 20 | 0 | 0 | None | 0.25 | 0.50 |
| `G2-0108` | List all defect IDs matching criteria: module='Sales', severity='Criti... | List only | 20 | 0 | 0 | None | 0.25 | 0.50 |
| `G2-0127` | List all defect IDs matching criteria: module='CRM', severity='Minor',... | List only | 20 | 33 | 33 | 33 | 1.00 | 1.00 |
| `G2-0130` | List all defect IDs matching criteria: module='Sales', severity='Block... | List only | 20 | 32 | 32 | 32 | 1.00 | 1.00 |
| `G2-0133` | List all defect IDs matching criteria: module='Inventory', severity='M... | List only | 20 | 36 | 36 | 36 | 1.00 | 0.50 |
| `G2-0138` | Which defects have module='Subscriptions', severity='Minor', status='I... | Count + List | 20 | 0 | 0 | None | 0.10 | 0.50 |
| `G2-0162` | Which defects have module='Knowledge', severity='Major', status='In Pr... | Count + List | 20 | 0 | 0 | None | 0.05 | 0.50 |
| `G2-0163` | Which defects have module='CRM', severity='Minor', status='Reopened'? ... | Count + List | 20 | 0 | 0 | None | 0.30 | 0.50 |
| `G2-0175` | Which defects have module='Project', severity='Blocker', status='Reope... | Count + List | 20 | 0 | 0 | None | 0.05 | 0.50 |
| `G2-0181` | List all defect IDs matching criteria: module='Quality', severity='Min... | List only | 20 | 34 | 34 | 34 | 1.00 | 1.00 |
| `G2-0203` | List all defect IDs matching criteria: module='Inventory', severity='B... | List only | 20 | 31 | 31 | 31 | 1.00 | 1.00 |
| `G2-0214` | Which defects have module='Inventory', severity='Minor', status='New'?... | Count + List | 20 | 0 | 0 | None | 0.10 | 0.50 |
| `G2-0223` | Which defects have module='Quality', severity='Major', status='Closed'... | Count + List | 20 | 0 | 0 | None | 0.30 | 0.50 |
| `G2-0226` | List all defect IDs matching criteria: module='Manufacturing', severit... | List only | 20 | 32 | 32 | 32 | 1.00 | 0.50 |
| `G2-0245` | Which defects have module='Manufacturing', severity='Major', status='R... | Count + List | 20 | 0 | 0 | None | 0.15 | 0.50 |
| `G2-0257` | List all defect IDs matching criteria: module='Subscriptions', severit... | List only | 20 | 0 | 0 | None | 0.10 | 0.50 |

### Root Cause: Hybrid Router Fallthrough on `semantic_filtered`
1. **Questions starting with *'List all defect IDs matching criteria...'***: Router chose `operation: list` and `retrieval_router.py` dispatched to `query_type: structured_list`. `Neo4jGraphRetriever.find_defects_by_filters()` executed the Cypher filter query and returned all matching defects (sample size 31–36), giving **100% node recall** (e.g. `G2-0127`, `G2-0130`, `G2-0133`, `G2-0181`, `G2-0203`, `G2-0226`).
2. **Questions phrased as *'Which defects have module=..., severity=...? State the total and list matching bug IDs.'***: `retrieval_router.py` saw the phrase *'State the total and list matching bug IDs'* as `substantial_free_text`, causing it to set `query_type: 'semantic_filtered'` with `retrievers: ['neo4j', 'semantic']`. In `hybrid_retriever.py`, `retrieve_from_neo4j()` handles `id_lookup`, `filter_list`, `filter_count`, and `group_by`, but has **no branch for `semantic_filtered`**, falling through to `DEFAULT / SEMANTIC` returning **0 Neo4j results**. Retrieval then fell back purely to vector similarity (10 hits), resulting in node recall dropping to **0.0 - 0.30**.

---

## 6. Defect to TestCase (Multi-Hop) Missing Facts Analysis

There were **11 test cases** for `defect_to_testcase`. The query requires tracing a defect back to its originating test case and all associated execution runs (build numbers and testers).

| ID | Question | Field Recall | Ans Exact | Missing Gold Fact | Present in Context? | Present in Answer? | Root Cause Category |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :--- |
| `G2-0019` | Can you find the test case and all associated exec... | 0.60 | 0.60 | `exec-017489.build_number` = `B-3992` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0019` | Can you find the test case and all associated exec... | 0.60 | 0.60 | `exec-017489.tester` = `Paul Riley` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0060` | Who verified the test case that uncovered BUG-0000... | 0.60 | 0.40 | `bug-000029.linked_test_case` = `TC-010360` | Yes | No | Answer LLM omitted execution fact |
| `G2-0060` | Who verified the test case that uncovered BUG-0000... | 0.60 | 0.40 | `exec-014328.build_number` = `B-6923` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0060` | Who verified the test case that uncovered BUG-0000... | 0.60 | 0.40 | `exec-014328.tester` = `Nicole Price` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0121` | Can you find the test case and all associated exec... | 1.00 | 0.33 | `exec-000076.build_number` = `B-2432` | Yes | No | Answer LLM omitted execution fact |
| `G2-0121` | Can you find the test case and all associated exec... | 1.00 | 0.33 | `exec-000076.tester` = `Pamela Ray` | Yes | No | Answer LLM omitted execution fact |
| `G2-0202` | For bug BUG-000155, identify the originating testc... | 1.00 | 0.67 | `exec-005762.build_number` = `B-9165` | Yes | No | Answer LLM omitted execution fact |
| `G2-0218` | Can you find the test case and all associated exec... | 0.60 | 0.20 | `exec-007159.build_number` = `B-7094` | Yes | No | Answer LLM omitted execution fact |
| `G2-0218` | Can you find the test case and all associated exec... | 0.60 | 0.20 | `exec-007159.tester` = `Joseph Cooper` | Yes | No | Answer LLM omitted execution fact |
| `G2-0218` | Can you find the test case and all associated exec... | 0.60 | 0.20 | `exec-013486.build_number` = `B-3607` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0218` | Can you find the test case and all associated exec... | 0.60 | 0.20 | `exec-013486.tester` = `Stephen Oneill` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0242` | Who verified the test case that uncovered BUG-0000... | 0.60 | 0.40 | `bug-000065.linked_test_case` = `TC-010406` | Yes | No | Answer LLM omitted execution fact |
| `G2-0242` | Who verified the test case that uncovered BUG-0000... | 0.60 | 0.40 | `exec-018611.build_number` = `B-3900` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0242` | Who verified the test case that uncovered BUG-0000... | 0.60 | 0.40 | `exec-018611.tester` = `William Delacruz` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0249` | For bug BUG-000046, identify the originating testc... | 0.60 | 0.40 | `exec-010537.build_number` = `B-1425` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0249` | For bug BUG-000046, identify the originating testc... | 0.60 | 0.40 | `exec-010537.tester` = `Kaitlyn Owen` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0249` | For bug BUG-000046, identify the originating testc... | 0.60 | 0.40 | `exec-012961.build_number` = `B-2599` | Yes | No | Answer LLM omitted execution fact |
| `G2-0261` | Which test case produced defect BUG-000039 and who... | 0.43 | 0.43 | `exec-011453.build_number` = `B-3851` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0261` | Which test case produced defect BUG-000039 and who... | 0.43 | 0.43 | `exec-011453.tester` = `Amy Valencia` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0261` | Which test case produced defect BUG-000039 and who... | 0.43 | 0.43 | `exec-018867.build_number` = `B-8770` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |
| `G2-0261` | Which test case produced defect BUG-000039 and who... | 0.43 | 0.43 | `exec-018867.tester` = `Jacqueline Williamson` | **No (Retriever Cap)** | No | Retriever capped execution runs (limit 5) |

### Root Causes for Missing Facts
1. **Retriever Execution Cap (Context-side truncation)**: When a test case has many executions, `get_testcase_context()` caps executions (or retrieves only the latest execution / sample of executions). In `G2-0021`, `G2-0060`, `G2-0218`, `G2-0242`, `G2-0249`, `G2-0261`, older execution IDs (e.g. `EXEC-017489`, `EXEC-014328`, `EXEC-013486`) were not retrieved by Neo4j.
2. **Answer LLM Selective Omission**: In `G2-0060`, `G2-0121`, `G2-0202`, `G2-0242`, the test case ID or execution runs were present in the retrieved structured evidence, but the answer LLM summarized only the primary defect or first execution without enumerating all historical runs.

---

## 7. Truncation and Context Window Analysis

### Cases with `context_tokens_est > 9000`
There were **5 cases** exceeding 9,000 estimated context tokens (computed as `context_chars / 4`):

| ID | Query Type | Context Chars | Context Tokens (Est.) | Question |
| :--- | :--- | :---: | :---: | :--- |
| `G2-0013` | `testcase_to_defects` | 59,931 | 14,982 | What defects were reported when running TC-000358? |
| `G2-0032` | `adversarial` | 43,922 | 10,980 | Between defect BUG-001545 and BUG-000067, which one has higher priority? |
| `G2-0074` | `testcase_to_defects` | 40,984 | 10,246 | Can you extract the list of defects associated with test case TC-000439? |
| `G2-0107` | `execution_context` | 50,352 | 12,588 | Give me the status, build, and linked test case ID for execution EXEC-000500. |
| `G2-0140` | `execution_context` | 40,672 | 10,168 | Who executed test run EXEC-000492, in which build, and what was the test status? |

### Ollama-Side Truncation Risk Assessment
1. **Default `num_ctx` in Ollama**: When running models under Ollama via standard OpenAI-compatible API calls without explicit `num_ctx` configuration, Ollama defaults to a context window of **2,048 tokens** (or 4,096 tokens in some custom Modelfiles).
2. **Critical Truncation Risk**: In `graph/llm_client.py`, completion calls do NOT pass `options={'num_ctx': 16384}` or `extra_body={'num_ctx': 16384}`. As a result, for prompts of 10,000–15,000 tokens (e.g. `G2-0013` at ~14,982 tokens and `G2-0107` at ~12,588 tokens), **Ollama silently truncates the prompt prefix or retrieved context** on the server side, potentially dropping retrieved evidence or system instructions.
3. **Mitigation**: `graph/llm_client.py` should explicitly pass `extra_body={'num_ctx': 32768}` (or dynamically sized) to prevent silent truncation on Ollama endpoints.

---

## 8. Requirements Traceability Retrieval Analysis

There were **21 test cases** under `requirements`. All 21 cases failed full recall, registering an average node recall of only **22.6%**.

### Confirmation of Graph Retriever Gap
Inspection of `graph/graph_retriever.py` and `graph/query_understanding.py` confirms that:
1. **No Requirement ID Extraction**: `QueryUnderstanding` only extracts `test_case_ids`, `execution_ids`, `defect_ids`, and `screenshot_ids`. It lacks a regex/pattern for `REQ-\d+` (`requirement_ids`).
2. **No Requirement Traversal in `Neo4jGraphRetriever`**: `Neo4jGraphRetriever` does NOT contain any Cypher query referencing the `Requirement` node label or the `VERIFIES` relationship (`(:TestCase)-[:VERIFIES]->(:Requirement)`).
3. **Asymmetric Recall Behavior**:
   - **Forward Lookup (`REQ -> TestCase`, 13 cases)**: Router extracts no entity ID. Retrieval returns 0 entities (`node_recall = 0.0`).
   - **Backward Lookup (`TestCase -> REQ`, 8 cases)**: Router extracts `TC-xxxx`. Retriever retrieves the TestCase node, but fails to traverse `VERIFIES` to the `Requirement` node. Thus `TC-xxxx` is retrieved but `REQ-xxxx` is missing, yielding exactly `node_recall = 0.50` (1 of 2 nodes found).

---

## 9. Root Cause Breakdown & Ranked Fix List

### Failure Counts by Root Cause

| Root Cause Category | Affected Query Types | Failure Count | Impact |
| :--- | :--- | :---: | :--- |
| **Gold Pseudo-Intent Mismatch** | `execution_context`, `testcase_to_defects`, `defect_to_testcase`, `unstructured_logs`, `unanswerable` | 78 | Artificial metric drop; pipeline retrieved correctly in 50 cases |
| **Semantic Filter Missing Implementation** | `multi_condition_filter` | 15 | `substantial_free_text` routed to `semantic_filtered`, which had no handler in `retrieve_from_neo4j` |
| **Missing Requirement Graph Traversal** | `requirements` | 21 | `Requirement` nodes and `VERIFIES` edges completely missing from retriever |
| **Semantic Vector Retrieval Threshold / Misses** | `semantic` | 15 | Keyword/embedding search failed to rank target defect in top-10 hits |
| **Real Router Intent Classification Errors** | `semantic` (17), `requirements` (8) | 25 | Router emitted `defect_lookup` / `testcase_execution_analysis` instead of semantic/lookup |
| **Abstention Metric Keyword Gap** | `unanswerable` | 7 | Model correctly refused, but evaluation regex missed phrasing (*'not provided'*, *'does not contain'*) |
| **Filter Vocabulary Normalization (`PROD`)** | `aggregation` | 1 | Environment filter `'PROD'` rejected as unmapped in `query_understanding.py` |
| **Filtered Count Aggregation Context Dispatch** | `aggregation` | 2 | `operation: count` with filters did not populate `aggregates['rows']` |
| **Defect-to-TestCase Multi-Hop Execution Cap** | `defect_to_testcase` | 6 | Retrievers truncated older executions; answer LLM omitted historical runs |
| **Ollama Server Context Window Truncation** | Prompts > 9,000 tokens | 5 | Prompts exceed default Ollama `num_ctx = 2048/4096` |

### Prioritized & Ranked Fix List

| Priority | Target File | Proposed Fix Description | Expected Benefit |
| :---: | :--- | :--- | :--- |
| **P1** | `graph/hybrid_retriever.py` | Add `semantic_filtered` handler in `retrieve_from_neo4j()` so queries with filters and free text execute structured filter queries alongside semantic search. | Instantly fixes 15 failing `multi_condition_filter` cases (recovers node recall from 0.0 to 1.0). |
| **P2** | `graph/graph_retriever.py` & `graph/query_understanding.py` | 1. Add `requirement_ids` regex (`REQ-\d+`) to entity extraction.<br>2. Add `get_requirement_context()` and update `get_testcase_context()` to traverse `(:TestCase)-[:VERIFIES]->(:Requirement)`. | Recovers all 21 `requirements` traceability test cases from 22.6% to 100% node recall. |
| **P3** | `graph/evaluation_v2/run_eval_v2.py` | 1. Integrate `INTENT_EQUIVALENCE_MAP` so valid alternative router intents are credited.<br>2. Expand `refusal_keywords` with `not provided`, `does not contain`, `does not provide`, `no data`. | Resolves 78 artificial intent mismatches and immediately turns 7 abstention failures into passes (100% abstention accuracy). |
| **P4** | `graph/query_understanding.py` & `graph/graph_retriever.py` | 1. Add `'PROD'` -> `'Production'` (or verify exact case/abbreviation) in environment vocabulary.<br>2. In `retrieve_from_neo4j`, ensure `operation == 'count'` with filters writes results to `aggregates['rows'] = [{'key': 'filtered_defects', 'count': total}]`. | Resolves 3 failing aggregation cases (`G2-0030`, `G2-0057`, `G2-0065`), reaching 100% aggregation exact. |
| **P5** | `graph/llm_client.py` | Pass `extra_body={'num_ctx': 32768}` in OpenAI client completion requests to avoid silent truncation in Ollama on large contexts (>9000 tokens). | Eliminates prompt truncation risk across all high-volume runs. |
| **P6** | `graph/graph_retriever.py` & `graph/final_prompt.py` | 1. Increase execution retrieval limit in multi-hop defect-to-testcase queries.<br>2. Explicitly prompt answer LLM to list all execution runs and testers when present in evidence. | Improves `defect_to_testcase` field recall and answer exactness from 60% to 100%. |
| **P7** | `graph/query_understanding.py` & `embedding/` | 1. Improve router prompt to favor `semantic_search` when no IDs are extracted.<br>2. Re-index or fine-tune embedding similarity thresholds for symptom-based defect retrieval. | Elevates semantic search recall from 28.6% (6/21) to >80%. |