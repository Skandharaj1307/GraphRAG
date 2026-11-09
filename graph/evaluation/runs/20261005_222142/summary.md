# GraphRAG Evaluation Benchmark Report
**Run Timestamp**: `20261005_222142`

**Testset File**: `E:\GraphRAG-1\graph\testset.json`

## 1. Overall System Performance
| Metric | Value |
| :--- | :--- |
| **Total Test Cases** | 5 |
| **Extraction Exact Match** | 80.0% |
| **Intent Accuracy (Raw Strict)** | 60.0% |
| **Intent Accuracy (Aliased)** | 80.0% |
| **Routing Accuracy** | 80.0% |
| **Retrieval Field Recall** | 80.0% |
| **Empty Retrieval Rate** | 20.0% |
| **Answer Correctness** | 60.0% |
| **Unanswerable Pass Rate** | N/A |
| **Faithfulness (Judge)** | N/A |
| **Completeness (Judge)** | N/A |
| **Latency p50** | 21.14s |
| **Latency p95** | 29.29s |

## 2. Failure Funnel
| Stage             |   Failed First Count |   Count |
|:------------------|---------------------:|--------:|
| extraction        |                    1 |     nan |
| routing           |                    0 |     nan |
| retrieval         |                    0 |     nan |
| generation        |                    1 |     nan |
| none (All Passed) |                  nan |       3 |

## 3. Performance by Question Type
| Question Type   |   Count | Extraction Match %   | Intent Raw %   | Intent Aliased %   | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|:----------------|--------:|:---------------------|:---------------|:-------------------|:----------------|:---------------------------|:-----------------------|:--------------|
| defect_lookup   |       5 | 80.0%                | 60.0%          | 80.0%              | 80.0%           | 80.0%                      | 60.0%                  | 60.0%         |

## 4. Performance by Hop Count
|   Hops |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|-------:|--------:|:----------------|:---------------------------|:-----------------------|:--------------|
|      0 |       5 | 80.0%           | 80.0%                      | 60.0%                  | 60.0%         |

## 5. Routing Accuracy & Confusion Matrix
| Expected Route   |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   |
|:-----------------|--------:|:----------------|:---------------------------|:-----------------------|
| neo4j            |       5 | 80.0%           | 80.0%                      | 60.0%                  |

### Routing Confusion Matrix
| Expected   |   error |   neo4j |
|:-----------|--------:|--------:|
| neo4j      |       1 |       4 |