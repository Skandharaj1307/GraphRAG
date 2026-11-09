# GraphRAG Evaluation Benchmark Report (V2)
**Run Timestamp**: `20261109_001434` | **Mode**: `retrieval_only`

## 1. Overall System Performance
| Metric | Value |
| :--- | :---: |
| **Total Cases** | 21 |
| **Valid Cases Evaluated** | 21 |
| **Infrastructure Errors (429/5xx)** | 0 |
| **Pipeline Errors** | 0 |
| **Latency p50** | 0.043s |
| **Latency p95** | 0.231s |
| **agg_filters_match** | 0.9048 |
| **agg_order_match** | 0.8571 |
| **agg_pairs_match** | 0.7619 |
| **aggregation_exact** | 76.2% |
| **context_chars** | 15810.0476 |
| **context_tokens_est** | 3952.1429 |
| **field_recall** | 95.2% |
| **node_precision** | 100.0% |
| **node_recall** | 100.0% |

## 2. Performance by Query Type
| Query Type | Count | Node Recall | Node Precision | Field Recall | Aggregation Exact | Agg Pairs Match | Agg Order Match | Agg Filters Match |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `aggregation` | 21 | 100.0% | 100.0% | 95.2% | 76.2% | 0.7619 | 0.8571 | 0.9048 |
