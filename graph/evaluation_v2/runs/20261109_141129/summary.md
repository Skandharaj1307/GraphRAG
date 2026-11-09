# GraphRAG Evaluation Benchmark Report (V2)
**Run Timestamp**: `20261109_141129` | **Mode**: `full`

## 1. Overall System Performance
| Metric | Value |
| :--- | :---: |
| **Total Cases** | 190 |
| **Valid Cases Evaluated** | 190 |
| **Infrastructure Errors (429/5xx)** | 0 |
| **Pipeline Errors** | 0 |
| **Latency p50** | 29.896s |
| **Latency p95** | 59.515s |
| **abstention_accuracy** | 88.4% |
| **agg_filters_match** | 0.8571 |
| **agg_order_match** | 1.0 |
| **agg_pairs_match** | 0.8571 |
| **aggregation_exact** | 85.7% |
| **answer_exact** | 70.1% |
| **context_chars** | 14779.0579 |
| **context_tokens_est** | 3694.3789 |
| **field_recall** | 88.6% |
| **filter_accuracy** | 97.1% |
| **group_by_accuracy** | 99.5% |
| **hallucination_free** | 0.8474 |
| **id_precision** | 99.0% |
| **id_recall** | 99.0% |
| **intent_accuracy** | 45.8% |
| **mrr** | 0.129 |
| **ndcg** | 0.167 |
| **node_precision** | 42.7% |
| **node_recall** | 74.9% |
| **recall_at_10** | 28.6% |
| **recall_at_5** | 23.8% |

## 2. Performance by Query Type
| Query Type | Count | Node Recall | Node Precision | Field Recall | Aggregation Exact | Agg Pairs Match | Agg Order Match | Agg Filters Match | Intent Accuracy | Id Recall | Answer Exact | Abstention Accuracy | Hallucination Free |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `adversarial` | 7 | 71.4% | 12.9% | 64.3% | — | — | — | — | 100.0% | 71.4% | 50.0% | 71.4% | 100.0% |
| `aggregation` | 21 | 100.0% | 100.0% | 90.5% | 85.7% | 0.8571 | 1.0 | 0.8571 | 100.0% | 100.0% | 81.0% | 90.5% | 100.0% |
| `defect_to_testcase` | 11 | 85.0% | 54.9% | 76.6% | — | — | — | — | 0.0% | 100.0% | 58.4% | 100.0% | 90.9% |
| `execution_context` | 21 | 100.0% | 43.6% | 100.0% | — | — | — | — | 0.0% | 100.0% | 70.2% | 100.0% | 100.0% |
| `id_lookup` | 21 | 100.0% | 23.1% | 100.0% | — | — | — | — | 100.0% | 100.0% | 81.0% | 100.0% | 100.0% |
| `multi_condition_filter` | 21 | 39.1% | 51.4% | 85.7% | — | — | — | — | 100.0% | 100.0% | 57.1% | 100.0% | 100.0% |
| `requirements` | 21 | 22.6% | 17.2% | 73.8% | — | — | — | — | 61.9% | 100.0% | 54.8% | 66.7% | 0.0% |
| `semantic` | 21 | 28.6% | 2.9% | 71.4% | — | — | — | — | 19.1% | 100.0% | 42.9% | 81.0% | 100.0% |
| `testcase_to_defects` | 11 | 100.0% | 25.3% | 100.0% | — | — | — | — | 0.0% | 100.0% | 81.8% | 100.0% | 100.0% |
| `unanswerable` | 14 | 100.0% | 100.0% | 100.0% | — | — | — | — | 0.0% | 100.0% | 100.0% | 50.0% | 64.3% |
| `unstructured_logs` | 21 | 100.0% | 35.2% | 100.0% | — | — | — | — | 0.0% | 100.0% | 90.5% | 100.0% | 90.5% |
