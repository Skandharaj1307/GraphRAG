# GraphRAG Evaluation Benchmark Report (V2)
**Run Timestamp**: `20261109_122645` | **Mode**: `router_only`

## 1. Overall System Performance
| Metric | Value |
| :--- | :---: |
| **Total Cases** | 12 |
| **Valid Cases Evaluated** | 12 |
| **Infrastructure Errors (429/5xx)** | 0 |
| **Pipeline Errors** | 0 |
| **Latency p50** | 8.628s |
| **Latency p95** | 13.768s |
| **filter_accuracy** | 98.3% |
| **group_by_accuracy** | 100.0% |
| **id_precision** | 100.0% |
| **id_recall** | 100.0% |
| **intent_accuracy** | 50.0% |

## 2. Performance by Query Type
| Query Type | Count | Node Recall | Node Precision | Field Recall | Aggregation Exact | Agg Pairs Match | Agg Order Match | Agg Filters Match | Intent Accuracy | Id Recall |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `aggregation` | 2 | — | — | — | — | — | — | — | 100.0% | 100.0% |
| `defect_to_testcase` | 2 | — | — | — | — | — | — | — | 0.0% | 100.0% |
| `execution_context` | 2 | — | — | — | — | — | — | — | 0.0% | 100.0% |
| `id_lookup` | 2 | — | — | — | — | — | — | — | 100.0% | 100.0% |
| `requirements` | 2 | — | — | — | — | — | — | — | 100.0% | 100.0% |
| `unstructured_logs` | 2 | — | — | — | — | — | — | — | 0.0% | 100.0% |
