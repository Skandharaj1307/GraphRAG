from neo4j import GraphDatabase


class Neo4jGraphRetriever:

    def __init__(
        self,
        uri="neo4j://127.0.0.1:7687",
        username="neo4j",
        password="qazwsxedc",
    ):
        self.driver = GraphDatabase.driver(
            uri,
            auth=(username, password)
        )

    def close(self):
        self.driver.close()

    # ---------------------------------------------------------
    # Connection Test
    # ---------------------------------------------------------

    def test_connection(self):
        with self.driver.session() as session:
            result = session.run(
                "RETURN 1 AS result"
            )
            return result.single()["result"] == 1

    # ---------------------------------------------------------
    # Retrieve TestCase by ID
    # ---------------------------------------------------------

    def get_testcase(self, test_case_id):

        query = """
        MATCH (t:TestCase {test_case_id: $test_case_id})
        RETURN properties(t) AS testcase
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                test_case_id=test_case_id
            )

            record = result.single()

            if record is None:
                return None

            return record["testcase"]

    # ---------------------------------------------------------
    # Retrieve Execution by ID
    # ---------------------------------------------------------

    def get_execution(self, execution_id):

        query = """
        MATCH (e:Execution {execution_id: $execution_id})
        RETURN properties(e) AS execution
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                execution_id=execution_id
            )

            record = result.single()

            if record is None:
                return None

            return record["execution"]

    # ---------------------------------------------------------
    # Retrieve Defect by ID
    # ---------------------------------------------------------

    def get_defect(self, defect_id):

        query = """
        MATCH (d:Defect {defect_id: $defect_id})
        RETURN properties(d) AS defect
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                defect_id=defect_id
            )

            record = result.single()

            if record is None:
                return None

            return record["defect"]

    # ---------------------------------------------------------
    # Retrieve Screenshot by ID
    # ---------------------------------------------------------

    def get_screenshot(self, screenshot_id):

        query = """
        MATCH (s:Screenshot {screenshot_id: $screenshot_id})
        RETURN properties(s) AS screenshot
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                screenshot_id=screenshot_id
            )

            record = result.single()

            if record is None:
                return None

            return record["screenshot"]

    # ---------------------------------------------------------
    # TestCase → Execution → Defect
    # ---------------------------------------------------------

    def get_testcase_execution_defects(self, test_case_id):

        query = """
        MATCH (t:TestCase {test_case_id: $test_case_id})
              -[:HAS_EXECUTION]->
              (e:Execution)
              -[:FOUND_DEFECT]->
              (d:Defect)

        RETURN
            properties(t) AS testcase,
            properties(e) AS execution,
            properties(d) AS defect
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                test_case_id=test_case_id
            )

            records = []

            for record in result:
                records.append({
                    "testcase": record["testcase"],
                    "execution": record["execution"],
                    "defect": record["defect"],
                })

            return records

    # ---------------------------------------------------------
    # TestCase → Execution → Defect → Screenshot
    # ---------------------------------------------------------

    def get_full_testcase_context(self, test_case_id):

        query = """
        MATCH (t:TestCase {test_case_id: $test_case_id})
              -[:HAS_EXECUTION]->
              (e:Execution)
              -[:FOUND_DEFECT]->
              (d:Defect)
              -[:HAS_SCREENSHOT]->
              (s:Screenshot)

        RETURN
            properties(t) AS testcase,
            properties(e) AS execution,
            properties(d) AS defect,
            properties(s) AS screenshot
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                test_case_id=test_case_id
            )

            records = []

            for record in result:
                records.append({
                    "testcase": record["testcase"],
                    "execution": record["execution"],
                    "defect": record["defect"],
                    "screenshot": record["screenshot"],
                })

            return records

    # ---------------------------------------------------------
    # Defect → Execution → TestCase → Screenshot
    # ---------------------------------------------------------

    def get_full_defect_context(self, defect_id):

        query = """
        MATCH (d:Defect {defect_id: $defect_id})
              <-[:FOUND_DEFECT]-
              (e:Execution)
              <-[:HAS_EXECUTION]-
              (t:TestCase)

        OPTIONAL MATCH (d)-[:HAS_SCREENSHOT]->(s:Screenshot)

        RETURN
            properties(d) AS defect,
            properties(e) AS execution,
            properties(t) AS testcase,
            collect(properties(s)) AS screenshots
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                defect_id=defect_id
            )

            record = result.single()

            if record is None:
                return None

            return {
                "defect": record["defect"],
                "execution": record["execution"],
                "testcase": record["testcase"],
                "screenshots": record["screenshots"],
            }

    # ---------------------------------------------------------
    # Generic Multi-Hop Graph Retrieval
    # ---------------------------------------------------------

    def get_graph_context(self, entity_id):

        if entity_id.startswith("TC-"):
            return self.get_full_testcase_context(entity_id)

        if entity_id.startswith("BUG-"):
            return self.get_full_defect_context(entity_id)

        if entity_id.startswith("EXEC-"):
            return self.get_execution_context(entity_id)

        if entity_id.startswith("SCR-"):
            return self.get_screenshot_context(entity_id)

        return None

    # ---------------------------------------------------------
    # Execution → TestCase → Defect → Screenshot
    # ---------------------------------------------------------

    def get_execution_context(self, execution_id):

        query = """
        MATCH (e:Execution {execution_id: $execution_id})
              <-[:HAS_EXECUTION]-
              (t:TestCase)

        OPTIONAL MATCH (e)-[:FOUND_DEFECT]->(d:Defect)

        OPTIONAL MATCH (d)-[:HAS_SCREENSHOT]->(s:Screenshot)

        RETURN
            properties(e) AS execution,
            properties(t) AS testcase,
            collect(properties(d)) AS defects,
            collect(properties(s)) AS screenshots
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                execution_id=execution_id
            )

            record = result.single()

            if record is None:
                return None

            return {
                "execution": record["execution"],
                "testcase": record["testcase"],
                "defects": record["defects"],
                "screenshots": record["screenshots"],
            }

    # ---------------------------------------------------------
    # Screenshot → TestCase / Execution / Defect
    # ---------------------------------------------------------

    def get_screenshot_context(self, screenshot_id):

        query = """
        MATCH (s:Screenshot {screenshot_id: $screenshot_id})

        OPTIONAL MATCH (t:TestCase)-[:HAS_SCREENSHOT]->(s)

        OPTIONAL MATCH (e:Execution)-[:CAPTURED_SCREENSHOT]->(s)

        OPTIONAL MATCH (d:Defect)-[:HAS_SCREENSHOT]->(s)

        RETURN
            properties(s) AS screenshot,
            collect(DISTINCT properties(t)) AS testcases,
            collect(DISTINCT properties(e)) AS executions,
            collect(DISTINCT properties(d)) AS defects
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                screenshot_id=screenshot_id
            )

            record = result.single()

            if record is None:
                return None

            return {
                "screenshot": record["screenshot"],
                "testcases": record["testcases"],
                "executions": record["executions"],
                "defects": record["defects"],
            }


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    retriever = Neo4jGraphRetriever(
        password="qazwsxedc"
    )

    try:

        print("=" * 60)
        print("NEO4J GRAPH RETRIEVER TEST")
        print("=" * 60)

        # -----------------------------------------------------
        # 1. Connection
        # -----------------------------------------------------

        if retriever.test_connection():
            print("✓ Neo4j connection successful")
        else:
            print("✗ Neo4j connection failed")
            exit()

        # -----------------------------------------------------
        # 2. TestCase
        # -----------------------------------------------------

        testcase_id = "TC-000001"

        testcase = retriever.get_testcase(testcase_id)

        if testcase:
            print(f"\n✓ TestCase found: {testcase_id}")
            print(f"  Module : {testcase.get('module')}")
            print(f"  Status : {testcase.get('status')}")
        else:
            print(f"\n✗ TestCase not found: {testcase_id}")

        # -----------------------------------------------------
        # 3. Multi-hop TestCase → Execution → Defect
        # -----------------------------------------------------

        results = retriever.get_testcase_execution_defects(
            testcase_id
        )

        print(
            f"\n✓ TestCase → Execution → Defect paths: "
            f"{len(results)}"
        )

        for item in results[:5]:

            print(
                f"  {item['testcase'].get('test_case_id')}"
                f" → {item['execution'].get('execution_id')}"
                f" → {item['defect'].get('defect_id')}"
            )

        # -----------------------------------------------------
        # 4. Full graph context
        # -----------------------------------------------------

        full_context = retriever.get_full_testcase_context(
            testcase_id
        )

        print(
            f"\n✓ Full TestCase graph paths: "
            f"{len(full_context)}"
        )

        for item in full_context[:5]:

            print(
                f"  {item['testcase'].get('test_case_id')}"
                f" → {item['execution'].get('execution_id')}"
                f" → {item['defect'].get('defect_id')}"
                f" → {item['screenshot'].get('screenshot_id')}"
            )

        print("\n" + "=" * 60)
        print("✓ GRAPH RETRIEVER TEST COMPLETED")
        print("=" * 60)

    finally:
        retriever.close()