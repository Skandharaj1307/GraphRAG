# Neo4j Graph Profile 2

## Query 1: Real category values (fixed)

```cypher
MATCH (d:Defect) RETURN 'defect.severity' AS field, d.severity AS value, count(*) AS n
UNION ALL MATCH (d:Defect) RETURN 'defect.priority' AS field, d.priority AS value, count(*) AS n
UNION ALL MATCH (d:Defect) RETURN 'defect.status' AS field, d.status AS value, count(*) AS n
UNION ALL MATCH (d:Defect) RETURN 'defect.bug_type' AS field, d.bug_type AS value, count(*) AS n
UNION ALL MATCH (d:Defect) RETURN 'defect.regression' AS field, d.regression AS value, count(*) AS n
UNION ALL MATCH (d:Defect) RETURN 'defect.reproducibility' AS field, d.reproducibility AS value, count(*) AS n
UNION ALL MATCH (e:Execution) RETURN 'exec.status' AS field, e.status AS value, count(*) AS n
UNION ALL MATCH (e:Execution) RETURN 'exec.environment' AS field, e.environment AS value, count(*) AS n
UNION ALL MATCH (e:Execution) RETURN 'exec.browser' AS field, e.browser AS value, count(*) AS n
UNION ALL MATCH (e:Execution) RETURN 'exec.os' AS field, e.operating_system AS value, count(*) AS n
UNION ALL MATCH (t:TestCase) RETURN 'tc.priority' AS field, t.priority AS value, count(*) AS n
UNION ALL MATCH (t:TestCase) RETURN 'tc.severity' AS field, t.severity AS value, count(*) AS n
UNION ALL MATCH (t:TestCase) RETURN 'tc.status' AS field, t.status AS value, count(*) AS n
UNION ALL MATCH (t:TestCase) RETURN 'tc.automation_status' AS field, t.automation_status AS value, count(*) AS n;
```

| field | value | n |
| --- | --- | --- |
| defect.severity | Minor | 2511 |
| defect.severity | Major | 2557 |
| defect.severity | Blocker | 2399 |
| defect.severity | Critical | 2533 |
| defect.priority | P2 | 2558 |
| defect.priority | P3 | 2544 |
| defect.priority | P1 | 2531 |
| defect.priority | P0 | 2367 |
| defect.status | Closed | 2022 |
| defect.status | In Progress | 2010 |
| defect.status | Resolved | 1974 |
| defect.status | New | 2072 |
| defect.status | Reopened | 1922 |
| defect.bug_type | Performance | 2035 |
| defect.bug_type | Security | 2071 |
| defect.bug_type | Functional | 2017 |
| defect.bug_type | UI/UX | 1949 |
| defect.bug_type | Integration | 1928 |
| defect.regression | Yes | 4997 |
| defect.regression | No | 5003 |
| defect.reproducibility | Unable to Reproduce | 2455 |
| defect.reproducibility | Once | 2525 |
| defect.reproducibility | Intermittent | 2536 |
| defect.reproducibility | Always | 2484 |
| exec.status | Failed | 4929 |
| exec.status | Passed | 5008 |
| exec.status | Skipped | 5072 |
| exec.status | Blocked | 4991 |
| exec.environment | DEV | 5006 |
| exec.environment | UAT | 5072 |
| exec.environment | QA | 4973 |
| exec.environment | STAGING | 4949 |
| exec.browser | Safari | 5003 |
| exec.browser | Chrome | 4954 |
| exec.browser | Firefox | 5027 |
| exec.browser | Edge | 5016 |
| exec.os | iOS | 4033 |
| exec.os | Windows 11 | 3950 |
| exec.os | Ubuntu | 3950 |
| exec.os | Android | 4045 |
| exec.os | macOS | 4022 |
| tc.priority | High | 5031 |
| tc.priority | Medium | 5052 |
| tc.priority | Critical | 4995 |
| tc.priority | Low | 4922 |
| tc.severity | Critical | 3950 |
| tc.severity | Trivial | 4045 |
| tc.severity | Blocker | 4011 |
| tc.severity | Minor | 4008 |
| tc.severity | Major | 3986 |
| tc.status | Review | 5005 |
| tc.status | Draft | 4964 |
| tc.status | Deprecated | 5109 |
| tc.status | Active | 4922 |
| tc.automation_status | Automated | 4967 |
| tc.automation_status | Not Automatable | 4936 |
| tc.automation_status | Manual | 4995 |
| tc.automation_status | In Progress | 5102 |

## Query 2: Do the modules match? (fixed)

```cypher
MATCH (t:TestCase) RETURN 'testcase' AS src, t.module AS module, count(*) AS n
UNION ALL MATCH (d:Defect) RETURN 'defect' AS src, d.module AS module, count(*) AS n;
```

| src | module | n |
| --- | --- | --- |
| testcase | POS | 978 |
| testcase | Quality | 992 |
| testcase | Documents | 984 |
| testcase | eCommerce | 988 |
| testcase | Rental | 1038 |
| testcase | Purchase | 981 |
| testcase | Payroll | 947 |
| testcase | Website | 964 |
| testcase | Helpdesk | 1008 |
| testcase | Accounting | 1012 |
| testcase | Manufacturing | 1003 |
| testcase | CRM | 1012 |
| testcase | Knowledge | 974 |
| testcase | Inventory | 983 |
| testcase | Studio | 1001 |
| testcase | HR | 995 |
| testcase | Project | 1082 |
| testcase | Sales | 978 |
| testcase | Maintenance | 1077 |
| testcase | Subscriptions | 1003 |
| defect | CRM | 503 |
| defect | Payroll | 515 |
| defect | Studio | 524 |
| defect | Helpdesk | 516 |
| defect | Project | 502 |
| defect | Subscriptions | 515 |
| defect | Purchase | 474 |
| defect | Documents | 509 |
| defect | Sales | 512 |
| defect | eCommerce | 475 |
| defect | HR | 517 |
| defect | Manufacturing | 503 |
| defect | Website | 476 |
| defect | POS | 470 |
| defect | Rental | 475 |
| defect | Quality | 509 |
| defect | Knowledge | 520 |
| defect | Accounting | 480 |
| defect | Maintenance | 490 |
| defect | Inventory | 515 |

## Query 3: Dangling property references (fixed)

```cypher
MATCH (d:Defect) WHERE NOT EXISTS { MATCH (:Execution {execution_id: d.linked_execution}) }
RETURN 'defect -> missing execution' AS issue, count(*) AS n
UNION ALL MATCH (d:Defect) WHERE NOT EXISTS { MATCH (:TestCase {test_case_id: d.linked_test_case}) }
RETURN 'defect -> missing testcase' AS issue, count(*) AS n
UNION ALL MATCH (e:Execution) WHERE NOT EXISTS { MATCH (:TestCase {test_case_id: e.test_case_id}) }
RETURN 'execution -> missing testcase' AS issue, count(*) AS n;
```

*Query returned 0 rows.*

## Query 4: Duplicates and orphans (fixed)

```cypher
MATCH (s:Screenshot) WITH s.screenshot_id AS id, count(*) AS c WHERE c > 1
RETURN 'dup screenshot_id' AS issue, count(*) AS n
UNION ALL MATCH (n) WHERE NOT (n)--() RETURN 'orphan nodes' AS issue, count(*) AS n;
```

| issue | n |
| --- | --- |
| orphan nodes | 3665 |

## Query 5: ID formats (fixed)

```cypher
MATCH (d:Defect) RETURN 'defect_id' AS field, size(d.defect_id) AS length, count(*) AS n
UNION ALL MATCH (t:TestCase) RETURN 'test_case_id' AS field, size(t.test_case_id) AS length, count(*) AS n
UNION ALL MATCH (e:Execution) RETURN 'execution_id' AS field, size(e.execution_id) AS length, count(*) AS n;
```

| field | length | n |
| --- | --- | --- |
| defect_id | 10 | 10000 |
| test_case_id | 9 | 20000 |
| execution_id | 11 | 20000 |

## Query 6: Executions with a defect, test cases with an execution

```cypher
MATCH (e:Execution)
RETURN 'executions with a defect' AS metric, sum(CASE WHEN EXISTS { (e)-[:FOUND_DEFECT]->() } THEN 1 ELSE 0 END) AS n, count(*) AS total
UNION ALL MATCH (t:TestCase)
RETURN 'testcases with an execution' AS metric, sum(CASE WHEN EXISTS { (t)-[:HAS_EXECUTION]->() } THEN 1 ELSE 0 END) AS n, count(*) AS total;
```

| metric | n | total |
| --- | --- | --- |
| executions with a defect | 6342 | 20000 |
| testcases with an execution | 12586 | 20000 |

## Query 7: Is the hierarchy clean? (0 means perfectly nested)

```cypher
MATCH (t:TestCase) WITH t.story AS k, count(DISTINCT t.epic) AS c WHERE c > 1
RETURN 'stories under several epics' AS issue, count(*) AS n
UNION ALL MATCH (t:TestCase) WITH t.requirement_id AS k, count(DISTINCT t.story) AS c WHERE c > 1
RETURN 'requirements under several stories' AS issue, count(*) AS n
UNION ALL MATCH (t:TestCase) WITH t.submodule AS k, count(DISTINCT t.module) AS c WHERE c > 1
RETURN 'submodules under several modules' AS issue, count(*) AS n;
```

| issue | n |
| --- | --- |
| stories under several epics | 1898 |
| requirements under several stories | 5926 |
| submodules under several modules | 970 |

## Query 8: The mixed STRING/FLOAT properties

```cypher
MATCH (t:TestCase) RETURN 'submodule' AS prop, valueType(t.submodule) AS type, count(*) AS n
UNION ALL MATCH (t:TestCase) RETURN 'component' AS prop, valueType(t.component) AS type, count(*) AS n
UNION ALL MATCH (t:TestCase) RETURN 'automation_framework' AS prop, valueType(t.automation_framework) AS type, count(*) AS n;
```

| prop | type | n |
| --- | --- | --- |
| submodule | STRING NOT NULL | 19972 |
| submodule | FLOAT NOT NULL | 28 |
| component | STRING NOT NULL | 19977 |
| component | FLOAT NOT NULL | 23 |
| automation_framework | STRING NOT NULL | 16087 |
| automation_framework | FLOAT NOT NULL | 3913 |

## Query 9: Do duplicated properties agree across linked nodes?

```cypher
MATCH (t:TestCase)-[:HAS_EXECUTION]->(e:Execution)
RETURN 'execution.test_case_id = parent id' AS check, sum(CASE WHEN e.test_case_id = t.test_case_id THEN 1 ELSE 0 END) AS agree, count(*) AS total
UNION ALL MATCH (e:Execution)-[:FOUND_DEFECT]->(d:Defect)
RETURN 'exec build = defect found_in_build' AS check, sum(CASE WHEN e.build_number = d.found_in_build THEN 1 ELSE 0 END) AS agree, count(*) AS total
UNION ALL MATCH (e:Execution)-[:FOUND_DEFECT]->(d:Defect)
RETURN 'exec environment = defect environment' AS check, sum(CASE WHEN e.environment = d.environment THEN 1 ELSE 0 END) AS agree, count(*) AS total
UNION ALL MATCH (t:TestCase)-[:HAS_DEFECT]->(d:Defect)
RETURN 'testcase module = defect module' AS check, sum(CASE WHEN t.module = d.module THEN 1 ELSE 0 END) AS agree, count(*) AS total;
```

| check | agree | total |
| --- | --- | --- |
| execution.test_case_id = parent id | 20000 | 20000 |
| exec build = defect found_in_build | 2 | 10000 |
| exec environment = defect environment | 1680 | 10000 |
| testcase module = defect module | 494 | 10000 |
