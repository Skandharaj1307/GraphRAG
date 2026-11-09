# GraphRAG Evaluation Benchmark Report
**Run Timestamp**: `20261108_172915`

**Testset File**: `E:\GraphRAG-1\graph\testset.json`

## 1. Overall System Performance
| Metric | Value |
| :--- | :--- |
| **Total Test Cases** | 27 |
| **Valid Pipeline Cases Evaluated** | 24 |
| **Infrastructure Failures Excluded** | 3 |
| **Extraction Exact Match** | 100.0% |
| **Intent Accuracy (Raw Strict)** | 75.0% |
| **Intent Accuracy (Aliased)** | 75.0% |
| **Routing Accuracy** | 87.5% |
| **Retrieval Field Recall** | 75.0% |
| **Empty Retrieval Rate** | 0.0% |
| **Answer Correctness** | 69.8% |
| **Unanswerable Pass Rate** | 0.0% |
| **Faithfulness (Judge)** | N/A |
| **Completeness (Judge)** | N/A |
| **Latency p50** | 39.15s |
| **Latency p95** | 99.74s |

## 2. Failure Funnel
| Stage             |   Failed First Count |
|:------------------|---------------------:|
| extraction        |                    6 |
| routing           |                    1 |
| retrieval         |                    3 |
| generation        |                    2 |
| infra_error       |                    3 |
| none (All Passed) |                   12 |

## 3. Performance by Question Type
| Question Type               |   Count | Extraction Match %   | Intent Raw %   | Intent Aliased %   | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|:----------------------------|--------:|:---------------------|:---------------|:-------------------|:----------------|:---------------------------|:-----------------------|:--------------|
| broad_summary               |       3 | 100.0%               | 33.3%          | 33.3%              | 0.0%            | 0.0%                       | 33.3%                  | 0.0%          |
| defect_lookup               |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_multi_property       |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_to_testcase          |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| execution_context           |       1 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 75.0%                  | 0.0%          |
| screenshot_lookup           |       3 | 100.0%               | 66.7%          | 66.7%              | 100.0%          | 100.0%                     | 66.7%                  | 66.7%         |
| testcase_executions_summary |       2 | 100.0%               | 50.0%          | 50.0%              | 100.0%          | 100.0%                     | 100.0%                 | 50.0%         |
| testcase_to_defects         |       3 | 100.0%               | 33.3%          | 33.3%              | 100.0%          | 100.0%                     | 66.7%                  | 0.0%          |
| unanswerable                |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 0.0%                       | 0.0%                   | 0.0%          |

## 4. Performance by Hop Count
|   Hops |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|-------:|--------:|:----------------|:---------------------------|:-----------------------|:--------------|
|      0 |      13 | 76.9%           | 53.8%                      | 59.6%                  | 46.2%         |
|      1 |       5 | 100.0%          | 100.0%                     | 80.0%                  | 60.0%         |
|      2 |       6 | 100.0%          | 100.0%                     | 83.3%                  | 50.0%         |

## 5. Routing Accuracy & Confusion Matrix
| Expected Route   |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   |
|:-----------------|--------:|:----------------|:---------------------------|:-----------------------|
| hybrid           |       1 | 0.0%            | 0.0%                       | 0.0%                   |
| lightrag         |       2 | 0.0%            | 0.0%                       | 50.0%                  |
| neo4j            |      21 | 100.0%          | 85.7%                      | 75.0%                  |

### Routing Confusion Matrix
| Expected   |   neo4j |
|:-----------|--------:|
| lightrag   |       2 |
| neo4j      |      21 |