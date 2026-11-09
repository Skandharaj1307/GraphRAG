# GraphRAG Evaluation Benchmark Report
**Run Timestamp**: `20261106_233942`

**Testset File**: `E:\GraphRAG-1\graph\testset.json`

## 1. Overall System Performance
| Metric | Value |
| :--- | :--- |
| **Total Test Cases** | 27 |
| **Valid Pipeline Cases Evaluated** | 21 |
| **Infrastructure Failures Excluded** | 6 |
| **Extraction Exact Match** | 100.0% |
| **Intent Accuracy (Raw Strict)** | 76.2% |
| **Intent Accuracy (Aliased)** | 76.2% |
| **Routing Accuracy** | 85.7% |
| **Retrieval Field Recall** | 71.4% |
| **Empty Retrieval Rate** | 0.0% |
| **Answer Correctness** | 63.1% |
| **Unanswerable Pass Rate** | 0.0% |
| **Faithfulness (Judge)** | N/A |
| **Completeness (Judge)** | N/A |
| **Latency p50** | 62.24s |
| **Latency p95** | 132.41s |

## 2. Failure Funnel
| Stage             |   Failed First Count |
|:------------------|---------------------:|
| extraction        |                    5 |
| routing           |                    2 |
| retrieval         |                    3 |
| generation        |                    3 |
| infra_error       |                    6 |
| none (All Passed) |                    8 |

## 3. Performance by Question Type
| Question Type               |   Count | Extraction Match %   | Intent Raw %   | Intent Aliased %   | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|:----------------------------|--------:|:---------------------|:---------------|:-------------------|:----------------|:---------------------------|:-----------------------|:--------------|
| broad_summary               |       3 | 100.0%               | 66.7%          | 66.7%              | 0.0%            | 0.0%                       | 33.3%                  | 0.0%          |
| defect_lookup               |       2 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_multi_property       |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_to_testcase          |       2 | 100.0%               | 50.0%          | 50.0%              | 100.0%          | 100.0%                     | 100.0%                 | 50.0%         |
| execution_context           |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 75.0%                  | 0.0%          |
| screenshot_lookup           |       1 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| testcase_executions_summary |       3 | 100.0%               | 33.3%          | 33.3%              | 100.0%          | 100.0%                     | 66.7%                  | 33.3%         |
| testcase_to_defects         |       1 | 100.0%               | 0.0%           | 0.0%               | 100.0%          | 100.0%                     | 0.0%                   | 0.0%          |
| unanswerable                |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 0.0%                       | 0.0%                   | 0.0%          |

## 4. Performance by Hop Count
|   Hops |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|-------:|--------:|:----------------|:---------------------------|:-----------------------|:--------------|
|      0 |      14 | 78.6%           | 57.1%                      | 58.9%                  | 35.7%         |
|      1 |       4 | 100.0%          | 100.0%                     | 75.0%                  | 50.0%         |
|      2 |       3 | 100.0%          | 100.0%                     | 66.7%                  | 33.3%         |

## 5. Routing Accuracy & Confusion Matrix
| Expected Route   |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   |
|:-----------------|--------:|:----------------|:---------------------------|:-----------------------|
| hybrid           |       1 | 0.0%            | 0.0%                       | 0.0%                   |
| lightrag         |       2 | 0.0%            | 0.0%                       | 50.0%                  |
| neo4j            |      18 | 100.0%          | 83.3%                      | 68.1%                  |

### Routing Confusion Matrix
| Expected   |   neo4j |
|:-----------|--------:|
| hybrid     |       1 |
| lightrag   |       2 |
| neo4j      |      18 |