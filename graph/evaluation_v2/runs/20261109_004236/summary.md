# GraphRAG Evaluation Benchmark Report (V2)
**Run Timestamp**: `20261109_004236` | **Mode**: `retrieval_only`

## 1. Overall System Performance
| Metric | Value |
| :--- | :---: |
| **Total Cases** | 42 |
| **Valid Cases Evaluated** | 42 |
| **Infrastructure Errors (429/5xx)** | 0 |
| **Pipeline Errors** | 0 |
| **Latency p50** | 0.025s |
| **Latency p95** | 0.101s |
| **agg_filters_match** | 1.0 |
| **agg_order_match** | 1.0 |
| **agg_pairs_match** | 1.0 |
| **aggregation_exact** | 100.0% |
| **context_chars** | 20999.0238 |
| **context_tokens_est** | 5249.4048 |
| **field_recall** | 100.0% |
| **node_precision** | 65.2% |
| **node_recall** | 100.0% |

## 2. Performance by Query Type
| Query Type | Count | Node Recall | Node Precision | Field Recall | Aggregation Exact | Agg Pairs Match | Agg Order Match | Agg Filters Match |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `aggregation` | 21 | 100.0% | 100.0% | 100.0% | 100.0% | 1.0 | 1.0 | 1.0 |
| `multi_condition_filter` | 21 | 100.0% | 30.4% | 100.0% | — | — | — | — |
