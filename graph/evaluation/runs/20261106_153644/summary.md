# GraphRAG Evaluation Benchmark Report
**Run Timestamp**: `20261106_153644`

**Testset File**: `E:\GraphRAG-1\graph\testset.json`

## 1. Overall System Performance
| Metric | Value |
| :--- | :--- |
| **Total Test Cases** | 27 |
| **Valid Pipeline Cases Evaluated** | 19 |
| **Infrastructure Failures Excluded** | 8 |
| **Extraction Exact Match** | 100.0% |
| **Intent Accuracy (Raw Strict)** | 78.9% |
| **Intent Accuracy (Aliased)** | 78.9% |
| **Routing Accuracy** | 94.7% |
| **Retrieval Field Recall** | 84.2% |
| **Empty Retrieval Rate** | 0.0% |
| **Answer Correctness** | 81.6% |
| **Unanswerable Pass Rate** | 0.0% |
| **Faithfulness (Judge)** | N/A |
| **Completeness (Judge)** | N/A |
| **Latency p50** | 41.77s |
| **Latency p95** | 74.76s |

## 2. Failure Funnel
| Stage             |   Failed First Count |
|:------------------|---------------------:|
| extraction        |                    4 |
| routing           |                    0 |
| retrieval         |                    2 |
| generation        |                    3 |
| infra_error       |                    8 |
| none (All Passed) |                   10 |

## 3. Performance by Question Type
| Question Type               |   Count | Extraction Match %   | Intent Raw %   | Intent Aliased %   | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|:----------------------------|--------:|:---------------------|:---------------|:-------------------|:----------------|:---------------------------|:-----------------------|:--------------|
| broad_summary               |       1 | 100.0%               | 0.0%           | 0.0%               | 0.0%            | 0.0%                       | 100.0%                 | 0.0%          |
| defect_lookup               |       1 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_multi_property       |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_to_testcase          |       2 | 100.0%               | 50.0%          | 50.0%              | 100.0%          | 100.0%                     | 100.0%                 | 50.0%         |
| execution_context           |       2 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 75.0%                  | 0.0%          |
| screenshot_lookup           |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| testcase_executions_summary |       3 | 100.0%               | 66.7%          | 66.7%              | 100.0%          | 100.0%                     | 66.7%                  | 33.3%         |
| testcase_to_defects         |       2 | 100.0%               | 50.0%          | 50.0%              | 100.0%          | 100.0%                     | 100.0%                 | 50.0%         |
| unanswerable                |       2 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 0.0%                       | 0.0%                   | 0.0%          |

## 4. Performance by Hop Count
|   Hops |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|-------:|--------:|:----------------|:---------------------------|:-----------------------|:--------------|
|      0 |       9 | 88.9%           | 66.7%                      | 72.2%                  | 44.4%         |
|      1 |       6 | 100.0%          | 100.0%                     | 83.3%                  | 66.7%         |
|      2 |       4 | 100.0%          | 100.0%                     | 100.0%                 | 50.0%         |

## 5. Routing Accuracy & Confusion Matrix
| Expected Route   |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   |
|:-----------------|--------:|:----------------|:---------------------------|:-----------------------|
| lightrag         |       1 | 0.0%            | 0.0%                       | 100.0%                 |
| neo4j            |      18 | 100.0%          | 88.9%                      | 80.6%                  |

### Routing Confusion Matrix
| Expected   |   neo4j |
|:-----------|--------:|
| lightrag   |       1 |
| neo4j      |      18 |