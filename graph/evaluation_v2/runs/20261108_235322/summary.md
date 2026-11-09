# GraphRAG Evaluation Benchmark Report (V2)
**Run Timestamp**: `20261108_235322` | **Mode**: `retrieval_only`

## 1. Overall System Performance
| Metric | Value |
| :--- | :---: |
| **Total Cases** | 12 |
| **Valid Cases Evaluated** | 12 |
| **Infrastructure Errors (429/5xx)** | 0 |
| **Pipeline Errors** | 0 |
| **Latency p50** | 0.044s |
| **Latency p95** | 45.928s |
| **aggregation_exact** | 50.0% |
| **context_chars** | 17010.1667 |
| **context_tokens_est** | 4252.25 |
| **field_recall** | 92.5% |
| **node_precision** | 54.9% |
| **node_recall** | 85.4% |

## 2. Performance by Query Type
| Query Type | Count | Node Recall | Node Precision | Field Recall | Aggregation Exact |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `aggregation` | 2 | 100.0% | 100.0% | 100.0% | 50.0% |
| `defect_to_testcase` | 2 | 87.5% | 60.0% | 80.0% | — |
| `execution_context` | 2 | 100.0% | 56.7% | 100.0% | — |
| `id_lookup` | 2 | 100.0% | 22.5% | 100.0% | — |
| `requirements` | 2 | 25.0% | 50.0% | 75.0% | — |
| `unstructured_logs` | 2 | 100.0% | 40.0% | 100.0% | — |
