# GraphRAG Evaluation Benchmark Report
**Run Timestamp**: `20261106_144250`

**Testset File**: `E:\GraphRAG-1\graph\testset.json`

## 1. Overall System Performance
| Metric | Value |
| :--- | :--- |
| **Total Test Cases** | 27 |
| **Valid Pipeline Cases Evaluated** | 19 |
| **Infrastructure Failures Excluded** | 8 |
| **Extraction Exact Match** | 100.0% |
| **Intent Accuracy (Raw Strict)** | 84.2% |
| **Intent Accuracy (Aliased)** | 84.2% |
| **Routing Accuracy** | 94.7% |
| **Retrieval Field Recall** | 94.7% |
| **Empty Retrieval Rate** | 0.0% |
| **Answer Correctness** | 80.3% |
| **Unanswerable Pass Rate** | N/A |
| **Faithfulness (Judge)** | N/A |
| **Completeness (Judge)** | N/A |
| **Latency p50** | 32.75s |
| **Latency p95** | 88.77s |

## 2. Failure Funnel
| Stage             |   Failed First Count |
|:------------------|---------------------:|
| extraction        |                    3 |
| routing           |                    0 |
| retrieval         |                    0 |
| generation        |                    5 |
| infra_error       |                    8 |
| none (All Passed) |                   11 |

## 3. Performance by Question Type
| Question Type               |   Count | Extraction Match %   | Intent Raw %   | Intent Aliased %   | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|:----------------------------|--------:|:---------------------|:---------------|:-------------------|:----------------|:---------------------------|:-----------------------|:--------------|
| broad_summary               |       1 | 100.0%               | 0.0%           | 0.0%               | 0.0%            | 0.0%                       | 0.0%                   | 0.0%          |
| defect_lookup               |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 66.7%                  | 66.7%         |
| defect_multi_property       |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_to_testcase          |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| execution_context           |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 75.0%                  | 0.0%          |
| screenshot_lookup           |       2 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 50.0%                  | 50.0%         |
| testcase_executions_summary |       2 | 100.0%               | 50.0%          | 50.0%              | 100.0%          | 100.0%                     | 100.0%                 | 50.0%         |
| testcase_to_defects         |       2 | 100.0%               | 50.0%          | 50.0%              | 100.0%          | 100.0%                     | 100.0%                 | 50.0%         |

## 4. Performance by Hop Count
|   Hops |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|-------:|--------:|:----------------|:---------------------------|:-----------------------|:--------------|
|      0 |      10 | 90.0%           | 90.0%                      | 72.5%                  | 50.0%         |
|      1 |       4 | 100.0%          | 100.0%                     | 75.0%                  | 50.0%         |
|      2 |       5 | 100.0%          | 100.0%                     | 100.0%                 | 80.0%         |

## 5. Routing Accuracy & Confusion Matrix
| Expected Route   |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   |
|:-----------------|--------:|:----------------|:---------------------------|:-----------------------|
| lightrag         |       1 | 0.0%            | 0.0%                       | 0.0%                   |
| neo4j            |      18 | 100.0%          | 100.0%                     | 84.7%                  |

### Routing Confusion Matrix
| Expected   |   neo4j |
|:-----------|--------:|
| lightrag   |       1 |
| neo4j      |      18 |