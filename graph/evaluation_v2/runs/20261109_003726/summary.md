# GraphRAG Evaluation Benchmark Report (V2)
**Run Timestamp**: `20261109_003726` | **Mode**: `retrieval_only`

## 1. Overall System Performance
| Metric | Value |
| :--- | :---: |
| **Total Cases** | 21 |
| **Valid Cases Evaluated** | 21 |
| **Infrastructure Errors (429/5xx)** | 0 |
| **Pipeline Errors** | 0 |
| **Latency p50** | 0.024s |
| **Latency p95** | 0.44s |
| **context_chars** | 26122.0952 |
| **context_tokens_est** | 6530.1429 |
| **field_recall** | 100.0% |
| **node_precision** | 30.4% |
| **node_recall** | 100.0% |

## 2. Performance by Query Type
| Query Type | Count | Node Recall | Node Precision | Field Recall | Aggregation Exact | Agg Pairs Match | Agg Order Match | Agg Filters Match |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `multi_condition_filter` | 21 | 100.0% | 30.4% | 100.0% | — | — | — | — |
