# GraphRAG Evaluation Benchmark Report
**Run Timestamp**: `20261108_164751`

**Testset File**: `E:\GraphRAG-1\graph\testset.json`

## 1. Overall System Performance
| Metric | Value |
| :--- | :--- |
| **Total Test Cases** | 27 |
| **Valid Pipeline Cases Evaluated** | 25 |
| **Infrastructure Failures Excluded** | 2 |
| **Extraction Exact Match** | 100.0% |
| **Intent Accuracy (Raw Strict)** | 80.0% |
| **Intent Accuracy (Aliased)** | 80.0% |
| **Routing Accuracy** | 92.0% |
| **Retrieval Field Recall** | 80.0% |
| **Empty Retrieval Rate** | 0.0% |
| **Answer Correctness** | 73.7% |
| **Unanswerable Pass Rate** | 0.0% |
| **Faithfulness (Judge)** | N/A |
| **Completeness (Judge)** | N/A |
| **Latency p50** | 14.87s |
| **Latency p95** | 62.90s |

## 2. Failure Funnel
| Stage             |   Failed First Count |
|:------------------|---------------------:|
| extraction        |                    5 |
| routing           |                    1 |
| retrieval         |                    3 |
| generation        |                    3 |
| infra_error       |                    2 |
| none (All Passed) |                   13 |

## 3. Performance by Question Type
| Question Type               |   Count | Extraction Match %   | Intent Raw %   | Intent Aliased %   | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|:----------------------------|--------:|:---------------------|:---------------|:-------------------|:----------------|:---------------------------|:-----------------------|:--------------|
| broad_summary               |       2 | 100.0%               | 50.0%          | 50.0%              | 0.0%            | 0.0%                       | 0.0%                   | 0.0%          |
| defect_lookup               |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_multi_property       |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_to_testcase          |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 88.9%                  | 66.7%         |
| execution_context           |       2 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 87.5%                  | 50.0%         |
| screenshot_lookup           |       3 | 100.0%               | 66.7%          | 66.7%              | 100.0%          | 100.0%                     | 100.0%                 | 66.7%         |
| testcase_executions_summary |       3 | 100.0%               | 66.7%          | 66.7%              | 100.0%          | 100.0%                     | 100.0%                 | 66.7%         |
| testcase_to_defects         |       3 | 100.0%               | 33.3%          | 33.3%              | 100.0%          | 100.0%                     | 66.7%                  | 0.0%          |
| unanswerable                |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 0.0%                       | 0.0%                   | 0.0%          |

## 4. Performance by Hop Count
|   Hops |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|-------:|--------:|:----------------|:---------------------------|:-----------------------|:--------------|
|      0 |      13 | 84.6%           | 61.5%                      | 59.6%                  | 53.8%         |
|      1 |       6 | 100.0%          | 100.0%                     | 100.0%                 | 66.7%         |
|      2 |       6 | 100.0%          | 100.0%                     | 77.8%                  | 33.3%         |

## 5. Routing Accuracy & Confusion Matrix
| Expected Route   |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   |
|:-----------------|--------:|:----------------|:---------------------------|:-----------------------|
| lightrag         |       2 | 0.0%            | 0.0%                       | 0.0%                   |
| neo4j            |      23 | 100.0%          | 87.0%                      | 80.1%                  |

### Routing Confusion Matrix
| Expected   |   neo4j |
|:-----------|--------:|
| lightrag   |       2 |
| neo4j      |      23 |