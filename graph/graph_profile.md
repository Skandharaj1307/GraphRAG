# Neo4j Graph Profile

## 1. Environment and overall shape

### Query 1

```cypher
CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition;
```

| name | versions | edition |
| --- | --- | --- |
| Neo4j Kernel | ["2026.09.0"] | enterprise |
| Cypher | ["5", "25"] |  |

### Query 2

```cypher
MATCH (n) RETURN labels(n) AS labels, count(*) AS nodes ORDER BY nodes DESC;
```

| labels | nodes |
| --- | --- |
| ["TestCase"] | 20000 |
| ["Execution"] | 20000 |
| ["Screenshot"] | 14000 |
| ["Defect"] | 10000 |

### Query 3

```cypher
MATCH (a)-[r]->(b)
RETURN labels(a) AS from, type(r) AS rel, labels(b) AS to, count(*) AS n
ORDER BY n DESC;
```

| from | rel | to | n |
| --- | --- | --- | --- |
| ["TestCase"] | HAS_EXECUTION | ["Execution"] | 20000 |
| ["TestCase"] | HAS_SCREENSHOT | ["Screenshot"] | 14000 |
| ["Execution"] | CAPTURED_SCREENSHOT | ["Screenshot"] | 14000 |
| ["Defect"] | HAS_SCREENSHOT | ["Screenshot"] | 14000 |
| ["TestCase"] | HAS_DEFECT | ["Defect"] | 10000 |
| ["Execution"] | FOUND_DEFECT | ["Defect"] | 10000 |

## 2. Properties, constraints and indexes

### Query 4

```cypher
CALL db.schema.nodeTypeProperties()
YIELD nodeLabels, propertyName, propertyTypes, mandatory
RETURN nodeLabels, propertyName, propertyTypes, mandatory
ORDER BY nodeLabels, propertyName;
```

| nodeLabels | propertyName | propertyTypes | mandatory |
| --- | --- | --- | --- |
| ["Defect"] | assigned_to | ["STRING NOT NULL"] | True |
| ["Defect"] | bug_type | ["STRING NOT NULL"] | True |
| ["Defect"] | comments | ["STRING NOT NULL"] | True |
| ["Defect"] | created_date | ["STRING NOT NULL"] | True |
| ["Defect"] | defect_id | ["STRING NOT NULL"] | True |
| ["Defect"] | description | ["STRING NOT NULL"] | True |
| ["Defect"] | developer | ["STRING NOT NULL"] | True |
| ["Defect"] | environment | ["STRING NOT NULL"] | True |
| ["Defect"] | fix_version | ["STRING NOT NULL"] | True |
| ["Defect"] | fixed_build | ["STRING NOT NULL"] | True |
| ["Defect"] | found_in_build | ["STRING NOT NULL"] | True |
| ["Defect"] | linked_execution | ["STRING NOT NULL"] | True |
| ["Defect"] | linked_test_case | ["STRING NOT NULL"] | True |
| ["Defect"] | module | ["STRING NOT NULL"] | True |
| ["Defect"] | priority | ["STRING NOT NULL"] | True |
| ["Defect"] | regression | ["STRING NOT NULL"] | True |
| ["Defect"] | reported_by | ["STRING NOT NULL"] | True |
| ["Defect"] | reproducibility | ["STRING NOT NULL"] | True |
| ["Defect"] | resolved_date | ["STRING NOT NULL"] | True |
| ["Defect"] | root_cause | ["STRING NOT NULL"] | True |
| ["Defect"] | severity | ["STRING NOT NULL"] | True |
| ["Defect"] | status | ["STRING NOT NULL"] | True |
| ["Defect"] | title | ["STRING NOT NULL"] | True |
| ["Execution"] | browser | ["STRING NOT NULL"] | True |
| ["Execution"] | build_number | ["STRING NOT NULL"] | True |
| ["Execution"] | environment | ["STRING NOT NULL"] | True |
| ["Execution"] | execution_date | ["STRING NOT NULL"] | True |
| ["Execution"] | execution_id | ["STRING NOT NULL"] | True |
| ["Execution"] | execution_notes | ["STRING NOT NULL"] | True |
| ["Execution"] | execution_time_seconds | ["INTEGER NOT NULL"] | True |
| ["Execution"] | operating_system | ["STRING NOT NULL"] | True |
| ["Execution"] | status | ["STRING NOT NULL"] | True |
| ["Execution"] | test_case_id | ["STRING NOT NULL"] | True |
| ["Execution"] | tester | ["STRING NOT NULL"] | True |
| ["Screenshot"] | bug_id | ["STRING NOT NULL"] | True |
| ["Screenshot"] | buttons | ["LIST<STRING NOT NULL> NOT NULL"] | True |
| ["Screenshot"] | captured_time | ["STRING NOT NULL"] | True |
| ["Screenshot"] | dialog_boxes | ["LIST<STRING NOT NULL> NOT NULL"] | True |
| ["Screenshot"] | error_messages | ["LIST<STRING NOT NULL> NOT NULL"] | True |
| ["Screenshot"] | execution_id | ["STRING NOT NULL"] | True |
| ["Screenshot"] | field_values | ["STRING NOT NULL"] | True |
| ["Screenshot"] | labels | ["LIST<STRING NOT NULL> NOT NULL"] | True |
| ["Screenshot"] | menus | ["LIST<STRING NOT NULL> NOT NULL"] | True |
| ["Screenshot"] | module | ["STRING NOT NULL"] | True |
| ["Screenshot"] | screen_name | ["STRING NOT NULL"] | True |
| ["Screenshot"] | screenshot_id | ["STRING NOT NULL"] | True |
| ["Screenshot"] | source_file | ["STRING NOT NULL"] | True |
| ["Screenshot"] | source_index | ["INTEGER NOT NULL"] | True |
| ["Screenshot"] | tables | ["LIST<STRING NOT NULL> NOT NULL"] | True |
| ["Screenshot"] | test_case_id | ["STRING NOT NULL"] | True |
| ["Screenshot"] | user_action | ["STRING NOT NULL"] | True |
| ["Screenshot"] | warning_messages | ["LIST<STRING NOT NULL> NOT NULL"] | True |
| ["TestCase"] | acceptance_criteria | ["STRING NOT NULL"] | True |
| ["TestCase"] | actual_result | ["STRING NOT NULL"] | True |
| ["TestCase"] | automation_framework | ["FLOAT NOT NULL", "STRING NOT NULL"] | True |
| ["TestCase"] | automation_status | ["STRING NOT NULL"] | True |
| ["TestCase"] | component | ["FLOAT NOT NULL", "STRING NOT NULL"] | True |
| ["TestCase"] | created_date | ["STRING NOT NULL"] | True |
| ["TestCase"] | environment | ["STRING NOT NULL"] | True |
| ["TestCase"] | epic | ["STRING NOT NULL"] | True |
| ["TestCase"] | execution_frequency | ["STRING NOT NULL"] | True |
| ["TestCase"] | expected_result | ["STRING NOT NULL"] | True |
| ["TestCase"] | feature | ["STRING NOT NULL"] | True |
| ["TestCase"] | module | ["STRING NOT NULL"] | True |
| ["TestCase"] | precondition | ["STRING NOT NULL"] | True |
| ["TestCase"] | priority | ["STRING NOT NULL"] | True |
| ["TestCase"] | release | ["STRING NOT NULL"] | True |
| ["TestCase"] | requirement_id | ["STRING NOT NULL"] | True |
| ["TestCase"] | risk | ["STRING NOT NULL"] | True |
| ["TestCase"] | severity | ["STRING NOT NULL"] | True |
| ["TestCase"] | status | ["STRING NOT NULL"] | True |
| ["TestCase"] | story | ["STRING NOT NULL"] | True |
| ["TestCase"] | submodule | ["FLOAT NOT NULL", "STRING NOT NULL"] | True |
| ["TestCase"] | test_case_id | ["STRING NOT NULL"] | True |
| ["TestCase"] | test_steps | ["STRING NOT NULL"] | True |
| ["TestCase"] | tester | ["STRING NOT NULL"] | True |
| ["TestCase"] | updated_date | ["STRING NOT NULL"] | True |

### Query 5

```cypher
SHOW CONSTRAINTS;
```

| id | name | type | entityType | labelsOrTypes | properties | enforcedLabel | ownedIndex | propertyType |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7 | defect_id_unique | NODE_PROPERTY_UNIQUENESS | NODE | ["Defect"] | ["defect_id"] | null | defect_id_unique | null |
| 5 | execution_id_unique | NODE_PROPERTY_UNIQUENESS | NODE | ["Execution"] | ["execution_id"] | null | execution_id_unique | null |
| 3 | testcase_id_unique | NODE_PROPERTY_UNIQUENESS | NODE | ["TestCase"] | ["test_case_id"] | null | testcase_id_unique | null |

### Query 6

```cypher
SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state
RETURN name, type, labelsOrTypes, properties, state;
```

| name | type | labelsOrTypes | properties | state |
| --- | --- | --- | --- | --- |
| defect_id_unique | RANGE | ["Defect"] | ["defect_id"] | ONLINE |
| execution_id_unique | RANGE | ["Execution"] | ["execution_id"] | ONLINE |
| index_1b9dcc97 | LOOKUP | null | null | ONLINE |
| index_460996c0 | LOOKUP | null | null | ONLINE |
| testcase_id_unique | RANGE | ["TestCase"] | ["test_case_id"] | ONLINE |

## 3. One real example per label

### Query 7

```cypher
MATCH (n:TestCase)   RETURN properties(n) AS p LIMIT 2;
```

| p |
| --- |
| {"test_case_id": "TC-000001", "release": "v17.2", "tester": "Charles Garcia", "test_steps": "1. The system rejected the incoming shipment but encountered a permission error.\r\n2. The background jo... |
| {"test_case_id": "TC-000002", "release": "v15.4", "tester": "Daniel Wagner", "test_steps": "1. The API endpoint updated the invoice while ensuring all mandatory fields were populated.\r\n2. The use... |

### Query 8

```cypher
MATCH (n:Execution)  RETURN properties(n) AS p LIMIT 2;
```

| p |
| --- |
| {"test_case_id": "TC-000096", "execution_id": "EXEC-000248", "environment": "DEV", "execution_notes": "The user configured the employee record while ensuring all mandatory fields were populated. Th... |
| {"test_case_id": "TC-000013", "execution_id": "EXEC-000605", "environment": "DEV", "execution_notes": "The system verified the subscription renewal but the system raised a validation exception.", "... |

### Query 9

```cypher
MATCH (n:Defect)     RETURN properties(n) AS p LIMIT 2;
```

| p |
| --- |
| {"severity": "Minor", "comments": "The sales representative calculated the manufacturing order while ensuring all mandatory fields were populated. The API endpoint deleted the subscription renewal ... |
| {"severity": "Minor", "comments": "The sales representative updated the POS receipt after verifying the related documents. The system deleted the POS receipt and successfully completed the transact... |

### Query 10

```cypher
MATCH (n:Screenshot) RETURN properties(n) AS p LIMIT 2;
```

| p |
| --- |
| {"test_case_id": "TC-014555", "user_action": "The warehouse operator configured the incoming shipment but the system raised a validation exception. The system configured the manufacturing order and... |
| {"test_case_id": "TC-019679", "user_action": "The accountant configured the subscription renewal which resulted in an AccessError. The manager processed the transfer triggering a workflow notificat... |

## 4. Real category values

### Query 11

```cypher
MATCH (d:Defect) RETURN 'defect.severity' AS field, d.severity AS value, count(*) AS n
UNION ALL MATCH (d:Defect) RETURN 'defect.priority', d.priority, count(*)
UNION ALL MATCH (d:Defect) RETURN 'defect.status', d.status, count(*)
UNION ALL MATCH (d:Defect) RETURN 'defect.bug_type', d.bug_type, count(*)
UNION ALL MATCH (d:Defect) RETURN 'defect.regression', d.regression, count(*)
UNION ALL MATCH (d:Defect) RETURN 'defect.reproducibility', d.reproducibility, count(*)
UNION ALL MATCH (e:Execution) RETURN 'exec.status', e.status, count(*)
UNION ALL MATCH (e:Execution) RETURN 'exec.environment', e.environment, count(*)
UNION ALL MATCH (e:Execution) RETURN 'exec.browser', e.browser, count(*)
UNION ALL MATCH (e:Execution) RETURN 'exec.os', e.operating_system, count(*)
UNION ALL MATCH (t:TestCase) RETURN 'tc.priority', t.priority, count(*)
UNION ALL MATCH (t:TestCase) RETURN 'tc.severity', t.severity, count(*)
UNION ALL MATCH (t:TestCase) RETURN 'tc.status', t.status, count(*)
UNION ALL MATCH (t:TestCase) RETURN 'tc.automation_status', t.automation_status, count(*);
```

**Error:**
```
{neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: All sub queries in an UNION must have the same return column names (line 4, column 1 (offset: 231))
"UNION ALL MATCH (d:Defect) RETURN 'defect.bug_type', d.bug_type, count(*)"
 ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}
```

## 5. How many distinct values are there

### Query 12

```cypher
MATCH (t:TestCase) WITH count(DISTINCT t.module) AS tc_modules, count(DISTINCT t.submodule) AS submodules,
     count(DISTINCT t.epic) AS epics, count(DISTINCT t.story) AS stories,
     count(DISTINCT t.requirement_id) AS requirements, count(DISTINCT t.feature) AS features
MATCH (d:Defect) WITH tc_modules, submodules, epics, stories, requirements, features,
     count(DISTINCT d.module) AS defect_modules, count(DISTINCT d.assigned_to) AS assignees,
     count(DISTINCT d.reported_by) AS reporters, count(DISTINCT d.found_in_build) AS found_builds,
     count(DISTINCT d.fixed_build) AS fixed_builds
MATCH (e:Execution)
RETURN tc_modules, submodules, epics, stories, requirements, features,
       defect_modules, assignees, reporters, found_builds, fixed_builds,
       count(DISTINCT e.build_number) AS exec_builds, count(DISTINCT e.tester) AS testers;
```

| tc_modules | submodules | epics | stories | requirements | features | defect_modules | assignees | reporters | found_builds | fixed_builds | exec_builds | testers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 998 | 491 | 1901 | 8608 | 19812 | 20 | 9375 | 9404 | 3658 | 4328 | 8020 | 17931 |

## 6. Do the module lists agree?

### Query 13

```cypher
MATCH (t:TestCase) RETURN 'testcase' AS src, t.module AS module, count(*) AS n
UNION ALL MATCH (d:Defect) RETURN 'defect', d.module, count(*)
ORDER BY module, src;
```

**Error:**
```
{neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: All sub queries in an UNION must have the same return column names (line 2, column 1 (offset: 79))
"UNION ALL MATCH (d:Defect) RETURN 'defect', d.module, count(*)"
 ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}
```

## 7. Missing values, key properties

### Query 14

```cypher
MATCH (d:Defect)
RETURN count(*) AS defects,
  sum(CASE WHEN d.linked_test_case IS NULL THEN 1 ELSE 0 END) AS no_linked_tc,
  sum(CASE WHEN d.linked_execution IS NULL THEN 1 ELSE 0 END) AS no_linked_exec,
  sum(CASE WHEN d.root_cause IS NULL OR d.root_cause = '' THEN 1 ELSE 0 END) AS no_root_cause,
  sum(CASE WHEN d.module IS NULL THEN 1 ELSE 0 END) AS no_module,
  sum(CASE WHEN d.assigned_to IS NULL THEN 1 ELSE 0 END) AS no_assignee,
  sum(CASE WHEN d.fixed_build IS NULL THEN 1 ELSE 0 END) AS no_fixed_build;
```

| defects | no_linked_tc | no_linked_exec | no_root_cause | no_module | no_assignee | no_fixed_build |
| --- | --- | --- | --- | --- | --- | --- |
| 10000 | 0 | 0 | 0 | 0 | 0 | 0 |

### Query 15

```cypher
MATCH (t:TestCase)
RETURN count(*) AS testcases,
  sum(CASE WHEN t.requirement_id IS NULL THEN 1 ELSE 0 END) AS no_req,
  sum(CASE WHEN t.epic IS NULL THEN 1 ELSE 0 END) AS no_epic,
  sum(CASE WHEN t.story IS NULL THEN 1 ELSE 0 END) AS no_story,
  sum(CASE WHEN t.module IS NULL THEN 1 ELSE 0 END) AS no_module;
```

| testcases | no_req | no_epic | no_story | no_module |
| --- | --- | --- | --- | --- |
| 20000 | 0 | 0 | 0 | 0 |

## 8. Do relationships match the property links?

### Query 16

```cypher
MATCH (d:Defect)
RETURN count(*) AS defects,
  sum(CASE WHEN EXISTS { (:Execution)-[:FOUND_DEFECT]->(d) } THEN 1 ELSE 0 END) AS has_found_defect_rel,
  sum(CASE WHEN EXISTS { (:TestCase)-[:HAS_DEFECT]->(d) } THEN 1 ELSE 0 END) AS has_has_defect_rel,
  sum(CASE WHEN EXISTS { (d)-[:HAS_SCREENSHOT]->(:Screenshot) } THEN 1 ELSE 0 END) AS defect_has_screenshot_rel;
```

| defects | has_found_defect_rel | has_has_defect_rel | defect_has_screenshot_rel |
| --- | --- | --- | --- |
| 10000 | 10000 | 10000 | 7516 |

### Query 17

```cypher
MATCH (d:Defect) WHERE d.linked_execution IS NOT NULL
  AND NOT EXISTS { MATCH (:Execution {execution_id: d.linked_execution}) }
RETURN 'defects pointing to a missing execution' AS issue, count(*) AS n
UNION ALL
MATCH (d:Defect) WHERE d.linked_test_case IS NOT NULL
  AND NOT EXISTS { MATCH (:TestCase {test_case_id: d.linked_test_case}) }
RETURN 'defects pointing to a missing test case', count(*)
UNION ALL
MATCH (e:Execution) WHERE e.test_case_id IS NOT NULL
  AND NOT EXISTS { MATCH (:TestCase {test_case_id: e.test_case_id}) }
RETURN 'executions pointing to a missing test case', count(*);
```

**Error:**
```
{neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: All sub queries in an UNION must have the same return column names (line 8, column 1 (offset: 399))
"UNION ALL"
 ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}
```

### Query 18

```cypher
MATCH (t:TestCase)-[:HAS_DEFECT]->(d:Defect)
OPTIONAL MATCH (t2:TestCase)-[:HAS_EXECUTION]->(:Execution)-[:FOUND_DEFECT]->(d)
RETURN count(*) AS has_defect_rels,
  sum(CASE WHEN t2 IS NULL THEN 1 ELSE 0 END) AS no_route_via_execution,
  sum(CASE WHEN t2 IS NOT NULL AND t2 <> t THEN 1 ELSE 0 END) AS different_testcase;
```

| has_defect_rels | no_route_via_execution | different_testcase |
| --- | --- | --- |
| 10000 | 0 | 0 |

## 9. Screenshots

### Query 19

```cypher
MATCH (s:Screenshot)
RETURN count(*) AS screenshots,
  sum(CASE WHEN EXISTS { (:TestCase)-[:HAS_SCREENSHOT]->(s) } THEN 1 ELSE 0 END) AS linked_from_testcase,
  sum(CASE WHEN EXISTS { (:Execution)-[:CAPTURED_SCREENSHOT]->(s) } THEN 1 ELSE 0 END) AS linked_from_execution,
  sum(CASE WHEN s.bug_id IS NOT NULL THEN 1 ELSE 0 END) AS has_bug_id,
  sum(CASE WHEN s.bug_id IS NOT NULL AND EXISTS { MATCH (:Defect {defect_id: s.bug_id}) } THEN 1 ELSE 0 END) AS bug_id_matches_defect;
```

| screenshots | linked_from_testcase | linked_from_execution | has_bug_id | bug_id_matches_defect |
| --- | --- | --- | --- | --- |
| 14000 | 14000 | 14000 | 14000 | 14000 |

## 10. Cardinality (how connected is it)

### Query 20

```cypher
MATCH (t:TestCase) OPTIONAL MATCH (t)-[:HAS_EXECUTION]->(e)
WITH t, count(e) AS n RETURN 'executions per testcase' AS metric, min(n) AS min, avg(n) AS avg, max(n) AS max;
```

| metric | min | avg | max |
| --- | --- | --- | --- |
| executions per testcase | 0 | 0.9999999999999992 | 6 |

### Query 21

```cypher
MATCH (e:Execution) OPTIONAL MATCH (e)-[:FOUND_DEFECT]->(d)
WITH e, count(d) AS n RETURN 'defects per execution' AS metric, min(n) AS min, avg(n) AS avg, max(n) AS max;
```

| metric | min | avg | max |
| --- | --- | --- | --- |
| defects per execution | 0 | 0.5000000000000021 | 8 |

## 11. Duplicate IDs and orphans

### Query 22

```cypher
MATCH (d:Defect) WITH d.defect_id AS id, count(*) AS c WHERE c > 1 RETURN 'dup defect_id' AS issue, count(*) AS n
UNION ALL MATCH (t:TestCase) WITH t.test_case_id AS id, count(*) AS c WHERE c > 1 RETURN 'dup test_case_id', count(*)
UNION ALL MATCH (e:Execution) WITH e.execution_id AS id, count(*) AS c WHERE c > 1 RETURN 'dup execution_id', count(*)
UNION ALL MATCH (n) WHERE NOT (n)--() RETURN 'orphan nodes', count(*);
```

**Error:**
```
{neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: All sub queries in an UNION must have the same return column names (line 4, column 1 (offset: 351))
"UNION ALL MATCH (n) WHERE NOT (n)--() RETURN 'orphan nodes', count(*);"
 ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}
```

## 12. ID formats

### Query 23

```cypher
MATCH (d:Defect) RETURN 'defect_id' AS field, size(d.defect_id) AS length, count(*) AS n
UNION ALL MATCH (t:TestCase) RETURN 'test_case_id', size(t.test_case_id), count(*)
UNION ALL MATCH (e:Execution) RETURN 'execution_id', size(e.execution_id), count(*);
```

**Error:**
```
{neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: All sub queries in an UNION must have the same return column names (line 3, column 1 (offset: 172))
"UNION ALL MATCH (e:Execution) RETURN 'execution_id', size(e.execution_id), count(*);"
 ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}
```
