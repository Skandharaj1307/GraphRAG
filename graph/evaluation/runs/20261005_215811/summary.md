# GraphRAG Evaluation Benchmark Report
**Run Timestamp**: `20261005_215811`

**Testset File**: `E:\GraphRAG-1\graph\testset.json`

## 1. Overall System Performance
| Metric | Value |
| :--- | :--- |
| **Total Test Cases** | 5 |
| **Extraction Exact Match** | 100.0% |
| **Intent Accuracy** | 100.0% |
| **Routing Accuracy** | 100.0% |
| **Retrieval Field Recall** | 100.0% |
| **Retrieval Set F1** | 0.0% |
| **Empty Retrieval Rate** | 0.0% |
| **Answer Correctness** | 33.3% |
| **Unanswerable Pass Rate** | N/A |
| **Faithfulness (Judge)** | N/A |
| **Completeness (Judge)** | N/A |
| **Latency p50** | 22.11s |
| **Latency p95** | 56.76s |

## 2. Failure Funnel
| Stage             |   Failed First Count |   Count |
|:------------------|---------------------:|--------:|
| extraction        |                    0 |     nan |
| routing           |                    0 |     nan |
| retrieval         |                    0 |     nan |
| generation        |                    4 |     nan |
| none (All Passed) |                  nan |       1 |

## 3. Performance by Question Type
| Question Type   |   Count | Extraction Match %   | Intent Acc %   | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|:----------------|--------:|:---------------------|:---------------|:----------------|:---------------------------|:-----------------------|:--------------|
| defect_lookup   |       5 | 100.0%               | 100.0%         | 100.0%          | 100.0%                     | 33.3%                  | 20.0%         |

## 4. Performance by Hop Count
|   Hops |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|-------:|--------:|:----------------|:---------------------------|:-----------------------|:--------------|
|      0 |       5 | 100.0%          | 100.0%                     | 33.3%                  | 20.0%         |

## 5. Routing Accuracy & Confusion Matrix
| Expected Route   |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   |
|:-----------------|--------:|:----------------|:---------------------------|:-----------------------|
| neo4j            |       5 | 100.0%          | 100.0%                     | 33.3%                  |

### Routing Confusion Matrix
| Expected   |   neo4j |
|:-----------|--------:|
| neo4j      |       5 |