# GraphRAG Evaluation Benchmark Report
**Run Timestamp**: `20261106_141429`

**Testset File**: `E:\GraphRAG-1\graph\testset.json`

## 1. Overall System Performance
| Metric | Value |
| :--- | :--- |
| **Total Test Cases** | 27 |
| **Valid Pipeline Cases Evaluated** | 27 |
| **Infrastructure Failures Excluded** | 0 |
| **Extraction Exact Match** | 100.0% |
| **Intent Accuracy (Raw Strict)** | 77.8% |
| **Intent Accuracy (Aliased)** | 77.8% |
| **Routing Accuracy** | 88.9% |
| **Retrieval Field Recall** | 77.8% |
| **Empty Retrieval Rate** | 0.0% |
| **Answer Correctness** | 71.3% |
| **Unanswerable Pass Rate** | 0.0% |
| **Faithfulness (Judge)** | N/A |
| **Completeness (Judge)** | N/A |
| **Latency p50** | 20.12s |
| **Latency p95** | 83.02s |

## 2. Failure Funnel
| Stage             |   Failed First Count |
|:------------------|---------------------:|
| extraction        |                    6 |
| routing           |                    2 |
| retrieval         |                    3 |
| generation        |                    4 |
| infra_error       |                    0 |
| none (All Passed) |                   12 |

## 3. Performance by Question Type
| Question Type               |   Count | Extraction Match %   | Intent Raw %   | Intent Aliased %   | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|:----------------------------|--------:|:---------------------|:---------------|:-------------------|:----------------|:---------------------------|:-----------------------|:--------------|
| broad_summary               |       3 | 100.0%               | 66.7%          | 66.7%              | 0.0%            | 0.0%                       | 0.0%                   | 0.0%          |
| defect_lookup               |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_multi_property       |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_to_testcase          |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| execution_context           |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 75.0%                  | 0.0%          |
| screenshot_lookup           |       3 | 100.0%               | 0.0%           | 0.0%               | 100.0%          | 100.0%                     | 100.0%                 | 0.0%          |
| testcase_executions_summary |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 66.7%                  | 66.7%         |
| testcase_to_defects         |       3 | 100.0%               | 33.3%          | 33.3%              | 100.0%          | 100.0%                     | 100.0%                 | 33.3%         |
| unanswerable                |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 0.0%                       | 0.0%                   | 0.0%          |

## 4. Performance by Hop Count
|   Hops |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|-------:|--------:|:----------------|:---------------------------|:-----------------------|:--------------|
|      0 |      15 | 80.0%           | 60.0%                      | 55.0%                  | 40.0%         |
|      1 |       6 | 100.0%          | 100.0%                     | 83.3%                  | 33.3%         |
|      2 |       6 | 100.0%          | 100.0%                     | 100.0%                 | 66.7%         |

## 5. Routing Accuracy & Confusion Matrix
| Expected Route   |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   |
|:-----------------|--------:|:----------------|:---------------------------|:-----------------------|
| hybrid           |       1 | 0.0%            | 0.0%                       | 0.0%                   |
| lightrag         |       2 | 0.0%            | 0.0%                       | 0.0%                   |
| neo4j            |      24 | 100.0%          | 87.5%                      | 80.2%                  |

### Routing Confusion Matrix
| Expected   |   neo4j |
|:-----------|--------:|
| hybrid     |       1 |
| lightrag   |       2 |
| neo4j      |      24 |