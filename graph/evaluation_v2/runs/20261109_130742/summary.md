# GraphRAG Evaluation Benchmark Report (V2)
**Run Timestamp**: `20261109_130742` | **Mode**: `full`

## 1. Overall System Performance
| Metric | Value |
| :--- | :---: |
| **Total Cases** | 12 |
| **Valid Cases Evaluated** | 12 |
| **Infrastructure Errors (429/5xx)** | 0 |
| **Pipeline Errors** | 0 |
| **Latency p50** | 26.451s |
| **Latency p95** | 77.279s |
| **abstention_accuracy** | 91.7% |
| **agg_filters_match** | 1.0 |
| **agg_order_match** | 1.0 |
| **agg_pairs_match** | 1.0 |
| **aggregation_exact** | 100.0% |
| **answer_exact** | 82.5% |
| **context_chars** | 14801.0 |
| **context_tokens_est** | 3699.9167 |
| **field_recall** | 92.5% |
| **filter_accuracy** | 98.3% |
| **group_by_accuracy** | 100.0% |
| **hallucination_free** | 0.8333 |
| **id_precision** | 100.0% |
| **id_recall** | 100.0% |
| **intent_accuracy** | 50.0% |
| **node_precision** | 54.9% |
| **node_recall** | 85.4% |

## 2. Performance by Query Type
| Query Type | Count | Node Recall | Node Precision | Field Recall | Aggregation Exact | Agg Pairs Match | Agg Order Match | Agg Filters Match | Intent Accuracy | Id Recall | Answer Exact | Abstention Accuracy | Hallucination Free |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `aggregation` | 2 | 100.0% | 100.0% | 100.0% | 100.0% | 1.0 | 1.0 | 1.0 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| `defect_to_testcase` | 2 | 87.5% | 60.0% | 80.0% | — | — | — | — | 0.0% | 100.0% | 70.0% | 100.0% | 100.0% |
| `execution_context` | 2 | 100.0% | 56.7% | 100.0% | — | — | — | — | 0.0% | 100.0% | 50.0% | 100.0% | 100.0% |
| `id_lookup` | 2 | 100.0% | 22.5% | 100.0% | — | — | — | — | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| `requirements` | 2 | 25.0% | 50.0% | 75.0% | — | — | — | — | 100.0% | 100.0% | 75.0% | 50.0% | 0.0% |
| `unstructured_logs` | 2 | 100.0% | 40.0% | 100.0% | — | — | — | — | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
