# GraphRAG Evaluation Benchmark Report
**Run Timestamp**: `20261006_220246`

**Testset File**: `E:\GraphRAG-1\graph\testset.json`

## 1. Overall System Performance
| Metric | Value |
| :--- | :--- |
| **Total Test Cases** | 27 |
| **Valid Pipeline Cases Evaluated** | 11 |
| **Infrastructure Failures Excluded** | 16 |
| **Extraction Exact Match** | 100.0% |
| **Intent Accuracy (Raw Strict)** | 54.5% |
| **Intent Accuracy (Aliased)** | 81.8% |
| **Routing Accuracy** | 90.9% |
| **Retrieval Field Recall** | 81.8% |
| **Empty Retrieval Rate** | 0.0% |
| **Answer Correctness** | 72.7% |
| **Unanswerable Pass Rate** | N/A |
| **Faithfulness (Judge)** | 92.4% |
| **Completeness (Judge)** | 27.3% |
| **Latency p50** | 19.88s |
| **Latency p95** | 68.60s |

## 2. Failure Funnel
| Stage             |   Failed First Count |
|:------------------|---------------------:|
| extraction        |                    2 |
| routing           |                    1 |
| retrieval         |                    0 |
| generation        |                    2 |
| infra_error       |                   16 |
| none (All Passed) |                    6 |

## 3. Performance by Question Type
| Question Type         |   Count | Extraction Match %   | Intent Raw %   | Intent Aliased %   | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|:----------------------|--------:|:---------------------|:---------------|:-------------------|:----------------|:---------------------------|:-----------------------|:--------------|
| defect_lookup         |       3 | 100.0%               | 66.7%          | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_multi_property |       3 | 100.0%               | 100.0%         | 100.0%             | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
| defect_to_testcase    |       3 | 100.0%               | 0.0%           | 66.7%              | 100.0%          | 50.0%                      | 33.3%                  | 0.0%          |
| testcase_to_defects   |       2 | 100.0%               | 50.0%          | 50.0%              | 50.0%           | 75.0%                      | 50.0%                  | 0.0%          |

## 4. Performance by Hop Count
|   Hops |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   | Pass Rate %   |
|-------:|--------:|:----------------|:---------------------------|:-----------------------|:--------------|
|      0 |       6 | 100.0%          | 100.0%                     | 100.0%                 | 100.0%        |
|      2 |       5 | 80.0%           | 60.0%                      | 40.0%                  | 0.0%          |

## 5. Routing Accuracy & Confusion Matrix
| Expected Route   |   Count | Routing Acc %   | Retrieval Field Recall %   | Answer Correctness %   |
|:-----------------|--------:|:----------------|:---------------------------|:-----------------------|
| neo4j            |      11 | 90.9%           | 81.8%                      | 72.7%                  |

### Routing Confusion Matrix
| Expected   |   hybrid |   neo4j |
|:-----------|---------:|--------:|
| neo4j      |        1 |      10 |