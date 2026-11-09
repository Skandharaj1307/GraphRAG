# GraphRAG Schema and Dataset Report (Source of Truth)

## 1. Neo4j Graph Schema (`graphragv2`)

### Node Labels and Counts
| Label | Count | Property Count | Key Properties & 2 Examples |
| :--- | :---: | :---: | :--- |
| `Defect` | 10,000 | 25 | `assigned_to`: ["John Pacheco", "Brittany Crosby"]<br>`bug_type`: ["Performance", "Security"]<br>`comments`: ["The sales representative calculated the manufacturing order while ensuring all mandatory fields were populated. The API ", "The sales representative updated the POS receipt after verifying the related documents. The system deleted the POS recei"]<br>`created_date`: ["2026-07-13", "2026-07-13"]<br>`defect_id`: ["BUG-000062", "BUG-000067"]<br>`description`: ["The API endpoint calculated the incoming shipment triggering a workflow notification. The user validated the subscriptio", "The background job updated the transfer but encountered a permission error. The sales representative configured the empl"]<br>`developer`: ["Katherine Ortega", "Debra Brady"]<br>`embedding_model`: ["Qwen3-Embedding-0.6B", "Qwen3-Embedding-0.6B"]<br>`environment`: ["QA", "UAT"]<br>`fix_version`: ["v15.2.7", "v15.4.4"]<br>`fixed_build`: ["B-9721", "B-7164"]<br>`found_in_build`: ["B-3875", "B-4713"]<br>`linked_execution`: ["EXEC-003817", "EXEC-016396"]<br>`linked_test_case`: ["TC-000036", "TC-000078"]<br>`module`: ["CRM", "Payroll"]<br>`priority`: ["P2", "P2"]<br>`regression`: ["Yes", "No"]<br>`reported_by`: ["Michael Shepard", "Albert Duke"]<br>`reproducibility`: ["Unable to Reproduce", "Unable to Reproduce"]<br>`resolved_date`: ["2026-07-14", "2026-07-14"]<br>`root_cause`: ["The manager attempted to confirm the transfer but encountered a permission error. The accountant calculated the incoming", "The user validated the transfer due to missing configuration settings."]<br>`severity`: ["Minor", "Minor"]<br>`status`: ["Closed", "In Progress"]<br>`title`: ["Issue in Sales: Optimized optimizing matrix", "Issue in Studio: Right-sized optimal secured line"] |
| `Environment` | 4 | 1 | `name`: ["DEV", "UAT"] |
| `Execution` | 20,000 | 11 | `browser`: ["Safari", "Chrome"]<br>`build_number`: ["B-2894", "B-3857"]<br>`environment`: ["DEV", "DEV"]<br>`execution_date`: ["2026-01-12", "2026-02-21"]<br>`execution_id`: ["EXEC-000248", "EXEC-000605"]<br>`execution_notes`: ["The user configured the employee record while ensuring all mandatory fields were populated. The accountant escalated the", "The system verified the subscription renewal but the system raised a validation exception."]<br>`execution_time_seconds`: ["38", "138"]<br>`operating_system`: ["iOS", "iOS"]<br>`status`: ["Failed", "Passed"]<br>`test_case_id`: ["TC-000096", "TC-000013"]<br>`tester`: ["Ashley Clark", "Mrs. Kelly Farley"] |
| `LogChunk` | 10,547 | 11 | `database_error`: ["ERROR: duplicate key value violates unique constraint \"hr_unique_id\"\nDETAIL: Key (name)=(Test_Record_001) already exists", "ERROR: duplicate key value violates unique constraint \"website_unique_id\"\nDETAIL: Key (name)=(Test_Record_001) already e"]<br>`defect_id`: ["BUG-003596", "BUG-003688"]<br>`exception_message`: ["odoo.exceptions.AccessError: Access Denied: You do not have the required permissions.", "odoo.exceptions.AccessError: Access Denied: You do not have the required permissions."]<br>`exception_name`: ["AccessError", "AccessError"]<br>`execution_id`: ["EXEC-016067", "EXEC-013238"]<br>`http_status`: ["404", "500"]<br>`log_id`: ["LOG-EXEC-016067", "LOG-EXEC-013238"]<br>`resolution_hint`: ["The background job escalated the subscription renewal which resulted in an AccessError.", "The system updated the manufacturing order due to missing configuration settings."]<br>`stack_frames`: ["['/odoo/addons/hr/models/record.py:158 in action_confirm', '/odoo/odoo/models.py:1666 in _validate_permissions']", "['/odoo/addons/website/models/record.py:418 in action_confirm', '/odoo/odoo/models.py:1533 in _validate_permissions']"]<br>`test_case_id`: ["TC-015914", "TC-009863"]<br>`traceback`: ["Traceback (most recent call last):\n  File \"/odoo/addons/hr/models/record.py\", line 158, in action_confirm\n    self._vali", "Traceback (most recent call last):\n  File \"/odoo/addons/website/models/record.py\", line 418, in action_confirm\n    self."] |
| `Module` | 20 | 1 | `name`: ["POS", "Quality"] |
| `Requirement` | 8,878 | 1 | `requirement_id`: ["REQ-1924", "REQ-1754"] |
| `Screenshot` | 14,000 | 20 | `bug_id`: ["BUG-001585", "BUG-003851"]<br>`buttons`: ["['Ago', 'Imagine', 'Bed', 'Agree', 'Author']", "['Relationship', 'Bank', 'Few', 'Practice', 'Offer']"]<br>`captured_time`: ["1979-12-05T16:39:33", "1999-06-10T03:47:57"]<br>`dialog_boxes`: ["['Confirm Spend?']", "['Confirm Life?']"]<br>`embedding_model`: ["Qwen3-Embedding-0.6B", "Qwen3-Embedding-0.6B"]<br>`error_messages`: ["['The user configured the POS receipt which resulted in an AccessError.']", "['']"]<br>`execution_id`: ["EXEC-002249", "EXEC-017509"]<br>`field_values`: ["{\"government\": \"avoid\", \"like\": \"interview\", \"the\": \"pressure\"}", "{\"audience\": \"more\", \"share\": \"action\", \"early\": \"time\"}"]<br>`labels`: ["['Our', 'Another', 'Notice']", "['Will', 'That', 'Her', 'Some']"]<br>`menus`: ["['File', 'Edit', 'View', 'Reports', 'Configuration']", "['File', 'Edit', 'View', 'Reports', 'Configuration']"]<br>`module`: ["HR", "Project"]<br>`screen_name`: ["Inventory Dashboard", "Studio Dashboard"]<br>`screenshot_id`: ["SCR-ocr_batch_001-0000", "SCR-ocr_batch_001-0001"]<br>`source_file`: ["ocr_batch_001.json", "ocr_batch_001.json"]<br>`source_index`: ["0", "1"]<br>`tables`: ["['Film List']", "['Authority List']"]<br>`test_case_id`: ["TC-014555", "TC-019679"]<br>`user_action`: ["The warehouse operator configured the incoming shipment but the system raised a validation exception. The system configu", "The accountant configured the subscription renewal which resulted in an AccessError. The manager processed the transfer "]<br>`warning_messages`: ["['The API endpoint attempted to confirm the manufacturing order and successfully completed the transaction.']", "['The warehouse operator configured the invoice due to missing configuration settings.']"] |
| `TestCase` | 20,000 | 27 | `acceptance_criteria`: ["The API endpoint escalated the transfer after verifying the related documents. The system escalated the invoice triggeri", "The user validated the incoming shipment which resulted in an AccessError. The background job calculated the transfer af"]<br>`actual_result`: ["The accountant configured the transfer and successfully completed the transaction.", "The API endpoint processed the invoice which resulted in an AccessError. The accountant escalated the subscription renew"]<br>`automation_framework`: ["Cypress", "Cypress"]<br>`automation_status`: ["Automated", "Not Automatable"]<br>`component`: ["Face", "Almost"]<br>`created_date`: ["2025-04-26", "2024-07-23"]<br>`embedding_model`: ["Qwen3-Embedding-0.6B", "Qwen3-Embedding-0.6B"]<br>`environment`: ["DEV", "PROD"]<br>`epic`: ["EPIC-22", "EPIC-204"]<br>`execution_frequency`: ["Release", "Weekly"]<br>`expected_result`: ["The warehouse operator updated the invoice but the system raised a validation exception.", "The background job verified the transfer while ensuring all mandatory fields were populated. The sales representative re"]<br>`feature`: ["Customizable 4thgeneration support", "Cross-group optimizing interface"]<br>`module`: ["POS", "Quality"]<br>`precondition`: ["The system calculated the employee record but encountered a permission error.", "The accountant verified the manufacturing order and successfully completed the transaction. The warehouse operator escal"]<br>`priority`: ["High", "Medium"]<br>`release`: ["v17.2", "v15.4"]<br>`requirement_id`: ["REQ-1924", "REQ-1754"]<br>`risk`: ["High", "Medium"]<br>`severity`: ["Critical", "Critical"]<br>`status`: ["Review", "Review"]<br>`story`: ["STORY-1618", "STORY-669"]<br>`submodule`: ["Purpose", "Offer"]<br>`test_case_id`: ["TC-000001", "TC-000002"]<br>`test_steps`: ["1. The system rejected the incoming shipment but encountered a permission error.\r\n2. The background job rejected the emp", "1. The API endpoint updated the invoice while ensuring all mandatory fields were populated.\r\n2. The user rejected the PO"]<br>`tester`: ["Charles Garcia", "Daniel Wagner"]<br>`updated_date`: ["2026-06-24", "2026-02-15"] |

### Relationships (Type, Direction, and Count)
| Relationship Pattern | Count | Description / Purpose |
| :--- | :---: | :--- |
| `(:TestCase)-[:VERIFIES]->(:Requirement)` | 32,225 | Link between TestCase and Requirement |
| `(:TestCase)-[:HAS_EXECUTION]->(:Execution)` | 20,000 | Link between TestCase and Execution |
| `(:TestCase)-[:IN_MODULE]->(:Module)` | 20,000 | Link between TestCase and Module |
| `(:Execution)-[:RAN_IN]->(:Environment)` | 20,000 | Link between Execution and Environment |
| `(:TestCase)-[:HAS_SCREENSHOT]->(:Screenshot)` | 14,000 | Link between TestCase and Screenshot |
| `(:Execution)-[:CAPTURED_SCREENSHOT]->(:Screenshot)` | 14,000 | Link between Execution and Screenshot |
| `(:Defect)-[:HAS_SCREENSHOT]->(:Screenshot)` | 14,000 | Link between Defect and Screenshot |
| `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` | 10,547 | Link between Execution and LogChunk |
| `(:TestCase)-[:HAS_DEFECT]->(:Defect)` | 10,000 | Link between TestCase and Defect |
| `(:Execution)-[:FOUND_DEFECT]->(:Defect)` | 10,000 | Link between Execution and Defect |
| `(:Defect)-[:REPORTED_IN_MODULE]->(:Module)` | 10,000 | Link between Defect and Module |

## 2. Structured Dataset (`dataset/structured/`)
| File Name | Row Count | Column Count | Columns |
| :--- | :---: | :---: | :--- |
| `defects.csv` | 10,000 | 23 | `defect_id`, `linked_test_case`, `linked_execution`, `title`, `description`, `severity`, `priority`, `module`, `status`, `assigned_to`, `reported_by`, `created_date`, `resolved_date`, `root_cause`, `bug_type`, `reproducibility`, `found_in_build`, `fixed_build`, `regression`, `environment`, `developer`, `comments`, `fix_version` |
| `test_execution.csv` | 20,000 | 11 | `execution_id`, `test_case_id`, `build_number`, `execution_date`, `tester`, `environment`, `browser`, `operating_system`, `execution_time_seconds`, `status`, `execution_notes` |
| `testcases.csv` | 20,000 | 25 | `test_case_id`, `requirement_id`, `epic`, `story`, `module`, `submodule`, `feature`, `priority`, `severity`, `risk`, `component`, `precondition`, `test_steps`, `expected_result`, `actual_result`, `status`, `automation_status`, `automation_framework`, `execution_frequency`, `tester`, `created_date`, `updated_date`, `release`, `environment`, `acceptance_criteria` |

## 3. Unstructured Dataset (`dataset/unstructured/`)
### Failure Logs (`dataset/unstructured/failure_logs/`)
- Total failure log text files: 10
| File Name | File Size (KB) | Graph Ingestion & Link |
| :--- | :---: | :--- |
| `logs_001.txt` | 1802.78 KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |
| `logs_002.txt` | 1803.93 KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |
| `logs_003.txt` | 1802.21 KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |
| `logs_004.txt` | 1801.74 KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |
| `logs_005.txt` | 1801.75 KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |
| `logs_006.txt` | 1804.02 KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |
| `logs_007.txt` | 1802.43 KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |
| `logs_008.txt` | 1802.53 KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |
| `logs_009.txt` | 1802.24 KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |
| `logs_010.txt` | 1802.29 KB | Parsed into `(:LogChunk)` nodes and linked via `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` |

### Screenshots OCR (`dataset/unstructured/screenshots/`)
- Total screenshot OCR batch files: 10
| File Name | File Size (KB) | Graph Ingestion & Link |
| :--- | :---: | :--- |
| `ocr_batch_001.json` | 1801.62 KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |
| `ocr_batch_002.json` | 1806.36 KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |
| `ocr_batch_003.json` | 1799.83 KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |
| `ocr_batch_004.json` | 1801.98 KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |
| `ocr_batch_005.json` | 1799.16 KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |
| `ocr_batch_006.json` | 1799.79 KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |
| `ocr_batch_007.json` | 1797.41 KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |
| `ocr_batch_008.json` | 1806.22 KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |
| `ocr_batch_009.json` | 1800.92 KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |
| `ocr_batch_010.json` | 1805.75 KB | Parsed into `(:Screenshot)` nodes and linked to `Defect`, `Execution`, and `TestCase` |

### SRS Document (`dataset/unstructured/srs/`)
- File: `srs_document.pdf` (1.36 MB, 769 pages)
- Graph Ingestion: Parsed into `(:Requirement {id, name, text, section, source})` nodes and linked via `(:TestCase)-[:VERIFIES]->(:Requirement)`.

## 4. Query Router Intents & Function Mappings
Sourced directly from `graph/query_understanding.py` and `graph/retrieval_router.py`:

| Router Intent | Target Entity / Route | Retrieval Function Called | Extracted Fields (IDs, Filters, Group By) |
| :--- | :--- | :--- | :--- |
| `defect_lookup` | `defect` (`neo4j`) | `get_full_defect_context(defect_id)` | IDs: `defect_ids`; Filters: None |
| `defect_multi_property` | `defect` (`neo4j`) | `get_full_defect_context(defect_id)` | IDs: `defect_ids`; Filters: None |
| `defect_to_testcase` | `defect` (`neo4j`) | `get_full_defect_context(defect_id)` (2-hop ego expansion) | IDs: `defect_ids`; Filters: None |
| `testcase_lookup` | `testcase` (`neo4j`) | `get_testcase_context(test_case_id)` | IDs: `test_case_ids`; Filters: None |
| `testcase_to_defects` | `testcase` (`neo4j`) | `get_testcase_context(test_case_id)` (2-hop ego expansion) | IDs: `test_case_ids`; Filters: None |
| `execution_context` / `execution_lookup` | `execution` (`neo4j`) | `get_execution_context(execution_id)` | IDs: `execution_ids`; Filters: None |
| `testcase_executions_summary` | `testcase` (`neo4j`) | `get_testcase_context(test_case_id)` or `get_execution_context` | IDs: `test_case_ids` / `execution_ids`; Filters: None |
| `screenshot_lookup` | `screenshot` / `defect` (`neo4j`) | `get_screenshot_context(screenshot_id)` or `get_full_defect_context(defect_id)` | IDs: `screenshot_ids` / `defect_ids`; Filters: None |
| `defect_analysis` / `group_by` / `aggregation` | `module` / `defect` (`neo4j`) | `aggregate_defects(group_by, filters)` | Group-by: `group_by_field` (`module`, `severity`, `status`, `build`, `tester`, `root_cause`); Filters: `module`, `severity`, `status`, etc. |
| `semantic_search` | `semantic` (`semantic`) | `search(query, k=...)` + Cross-Encoder reranker | IDs: None; Filters: None |
| `general_test_analysis` / `broad_summary` | `hybrid` / `lightrag` / `neo4j` | `route_query` -> `hybrid` or `neo4j` aggregation | IDs: None; Filters/Group-by as extracted |
| `unanswerable` | `neo4j` | Handled via ID lookup with empty graph results -> fallback refusal | Non-existent or missing IDs |

## 5. Existing Retrieval Features
1. **Multi-Hop Subgraph Expansion**: Bi-directional 2-hop traversals across `Defect` <-> `Execution` <-> `TestCase` <-> `Screenshot` with parameterized ego limits.
2. **Parametric Whitelisted Aggregation (`aggregate_defects`)**: Injects validated property filters (`module`, `severity`, `status`, `build`, `tester`, etc.) and group-by clauses safely into Cypher.
3. **Local Cross-Encoder Reranker**: `BAAI/bge-reranker-base` local reranker reranks the top 25 semantic embedding hits in `semantic_retriever.py`.
4. **Failure Log Retrieval**: `(:Execution)-[:HAS_FAILURE_LOG]->(:LogChunk)` returns structured error logs (exception type, message, stack trace snippet) attached to execution contexts.
5. **Requirement Tracing**: `(:TestCase)-[:VERIFIES]->(:Requirement)` links test cases to SRS requirements sections.
