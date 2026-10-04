import json
from typing import Dict, Any

from graph.query_understanding import QueryUnderstanding
from graph.retrieval_router import RetrievalRouter
from graph.graph_retriever import Neo4jGraphRetriever
from graph.lightrag_retriever import LightRAGRetriever


# ============================================================
# HYBRID RETRIEVER
# ============================================================

class HybridRetriever:

    """
    Orchestrates:

        1. Query Understanding
        2. Retrieval Routing
        3. Neo4j retrieval
        4. LightRAG retrieval

    This module does NOT generate the final answer.
    It only collects retrieval evidence.
    """

    def __init__(self):

        print("Initializing Hybrid Retriever...")

        # ----------------------------------------------------
        # Query Understanding
        # ----------------------------------------------------

        self.query_understanding = QueryUnderstanding()

        # ----------------------------------------------------
        # Retrieval Router
        # ----------------------------------------------------

        self.router = RetrievalRouter()

        # ----------------------------------------------------
        # Neo4j Retriever
        # ----------------------------------------------------

        self.neo4j = Neo4jGraphRetriever()

        # ----------------------------------------------------
        # LightRAG Retriever
        # ----------------------------------------------------

        self.lightrag = LightRAGRetriever()

        self.lightrag_initialized = False

        print("✓ Hybrid Retriever created")

    # ========================================================
    # INITIALIZE
    # ========================================================

    async def initialize(self):

        print()
        print("=" * 60)
        print("INITIALIZING RETRIEVERS")
        print("=" * 60)

        # ----------------------------------------------------
        # Test Neo4j
        # ----------------------------------------------------

        if self.neo4j.test_connection():

            print("✓ Neo4j connection successful")

        else:

            raise RuntimeError(
                "Neo4j connection failed."
            )

        # ----------------------------------------------------
        # Initialize LightRAG
        # ----------------------------------------------------

        await self.lightrag.initialize()

        self.lightrag_initialized = True

        print("✓ LightRAG initialized")

    # ========================================================
    # NEO4J RETRIEVAL
    # ========================================================

    def retrieve_from_neo4j(
        self,
        query: str,
        understanding: Dict[str, Any]
    ) -> Dict[str, Any]:

        entities = understanding.get(
            "entities",
            {}
        )

        test_case_ids = entities.get(
            "test_case_ids",
            []
        )

        execution_ids = entities.get(
            "execution_ids",
            []
        )

        defect_ids = entities.get(
            "defect_ids",
            []
        )

        results = []

        # ----------------------------------------------------
        # TestCase retrieval
        # ----------------------------------------------------

        for test_case_id in test_case_ids:

            context = self.neo4j.get_full_testcase_context(
                test_case_id
            )

            results.append({
                "type": "testcase_context",
                "id": test_case_id,
                "data": context
            })

        # ----------------------------------------------------
        # Execution retrieval
        # ----------------------------------------------------

        for execution_id in execution_ids:

            context = self.neo4j.get_execution_context(
                execution_id
            )

            results.append({
                "type": "execution_context",
                "id": execution_id,
                "data": context
            })

        # ----------------------------------------------------
        # Defect retrieval
        # ----------------------------------------------------

        for defect_id in defect_ids:

            context = self.neo4j.get_defect(
                defect_id
            )

            results.append({
                "type": "defect",
                "id": defect_id,
                "data": context
            })

        return {
            "source": "neo4j",
            "results": results
        }

    # ========================================================
    # LIGHTRAG RETRIEVAL
    # ========================================================

    async def retrieve_from_lightrag(
        self,
        query: str
    ) -> Dict[str, Any]:

        if not self.lightrag_initialized:

            raise RuntimeError(
                "LightRAG has not been initialized."
            )

        result = await self.lightrag.query(
            query,
            mode="hybrid"
        )

        return {
            "source": "lightrag",
            "results": result
        }

    # ========================================================
    # MAIN RETRIEVAL
    # ========================================================

    async def retrieve(
        self,
        query: str
    ) -> Dict[str, Any]:

        print()
        print("=" * 60)
        print("HYBRID RETRIEVAL")
        print("=" * 60)

        print()
        print("User Query:")
        print(query)

        # ----------------------------------------------------
        # Step 1 — Query Understanding
        # ----------------------------------------------------

        print()
        print("1. Query Understanding")

        understanding = await self.query_understanding.analyze(
            query
        )

        print(
            json.dumps(
                understanding,
                indent=4
            )
        )

        # ----------------------------------------------------
        # Step 2 — Routing
        # ----------------------------------------------------

        print()
        print("2. Retrieval Routing")

        route = self.router.route(
            understanding
        )

        print(
            json.dumps(
                route,
                indent=4
            )
        )

        # ----------------------------------------------------
        # Step 3 — Retrieval
        # ----------------------------------------------------

        neo4j_result = None
        lightrag_result = None

        retrievers = route.get(
            "retrievers",
            []
        )

        # ----------------------------------------------------
        # Neo4j
        # ----------------------------------------------------

        if "neo4j" in retrievers:

            print()
            print("3A. Neo4j Retrieval")

            neo4j_result = self.retrieve_from_neo4j(
                query,
                understanding
            )

            print(
                f"✓ Neo4j results: "
                f"{len(neo4j_result['results'])}"
            )

        # ----------------------------------------------------
        # LightRAG
        # ----------------------------------------------------

        if "lightrag" in retrievers:

            print()
            print("3B. LightRAG Retrieval")

            lightrag_result = await self.retrieve_from_lightrag(
                query
            )

            print("✓ LightRAG retrieval completed")

        # ----------------------------------------------------
        # Combined result
        # ----------------------------------------------------

        return {
            "query": query,
            "query_understanding": understanding,
            "route": route,
            "neo4j": neo4j_result,
            "lightrag": lightrag_result
        }

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        if self.neo4j:

            self.neo4j.close()

        print("✓ Hybrid Retriever closed")


# ============================================================
# TEST
# ============================================================

async def main():

    print("=" * 60)
    print("HYBRID RETRIEVER TEST")
    print("=" * 60)

    retriever = HybridRetriever()

    try:

        await retriever.initialize()

        # ----------------------------------------------------
        # Test query
        # ----------------------------------------------------

        query = (
            "Which defects were found in the execution "
            "of test case TC-000001?"
        )

        result = await retriever.retrieve(
            query
        )

        print()
        print("=" * 60)
        print("HYBRID RETRIEVAL RESULT")
        print("=" * 60)

        print(
            json.dumps(
                result,
                indent=4,
                default=str
            )
        )

        print()
        print("=" * 60)
        print("✓ HYBRID RETRIEVER TEST COMPLETED")
        print("=" * 60)

    finally:

        retriever.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    import asyncio

    asyncio.run(main())