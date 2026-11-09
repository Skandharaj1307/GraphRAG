# GraphRAG Evaluation Benchmark Report
**Run Timestamp**: `20261108_213203`

**Testset File**: `E:\GraphRAG-1\graph\testset.json`

## 1. Overall System Performance
| Metric | Value |
| :--- | :--- |
| **Total Test Cases** | 27 |
| **Valid Pipeline Cases Evaluated** | 22 |
| **Infrastructure Failures Excluded** | 5 |
| **Extraction Exact Match** | 100.0% |
| **Intent Accuracy (Raw Strict)** | 95.5% |
| **Intent Accuracy (Aliased)** | 95.5% |
| **Routing Accuracy** | 90.9% |
| **Retrieval Field Recall** | 77.3% |
| **Empty Retrieval Rate** | 0.0% |
| **Answer Correctness** | 73.9% |
| **Unanswerable Pass Rate** | 0.0% |
| **Faithfulness (Judge)** | N/A |
| **Completeness (Judge)** | N/A |
| **Latency p50** | 47.87s |
| **Latency p95** | 107.07s |

## 2. Failure Funnel
| Stage             |   Failed First Count |
|:------------------|---------------------:|
| extraction        |                    1 |
| routing           |                    1 |
| retrieval         |                    3 |
| generation        |                    3 |
| infra_error       |                    5 |
| none (All Passed) |                   14 |

## 3. Performance by Question Type
| Question Type               |   Count | Extraction Match %   | Intent Raw %   | Intent Aliased %   | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|:----------------------------|--------:|:---------------------|:---------------|:-------------------|:----------------|:---------------------------|:-----------------------|:--------------|
| broad_summary               |       2 | 100.0%               | 50.0%          | 50.0%              | 0.0%            | 0.0%                       | 0.0%                   | 0.0%          |
| defect_lookup               |       2 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_multi_property       |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_to_testcase          |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| execution_context           |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 75.0%                  | 0.0%          |
| screenshot_lookup           |       2 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| testcase_executions_summary |       2 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| testcase_to_defects         |       2 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| unanswerable                |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 0.0%                       | 0.0%                   | 0.0%          |

## 4. Performance by Hop Count
|   Hops |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|-------:|--------:|:----------------|:---------------------------|:-----------------------|:--------------|
|      0 |      13 | 84.6%           | 61.5%                      | 55.8%                  | 38.5%         |
|      1 |       4 | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
|      2 |       5 | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |

## 5. Routing Accuracy & Confusion Matrix
| Expected Route   |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   |
|:-----------------|--------:|:----------------|:---------------------------|:-----------------------|
| hybrid           |       1 | 0.0%            | 0.0%                       | 0.0%                   |
| lightrag         |       1 | 0.0%            | 0.0%                       | 0.0%                   |
| neo4j            |      20 | 100.0%          | 85.0%                      | 81.2%                  |

### Routing Confusion Matrix
| Expected   |   neo4j |
|:-----------|--------:|
| hybrid     |       1 |
| lightrag   |       1 |
| neo4j      |      20 |