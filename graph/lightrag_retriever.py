import asyncio
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from lightrag.llm.openai import openai_complete_if_cache

from graph.graph_retriever import Neo4jGraphRetriever


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Use a NEW directory for this Neo4j integration test.
# This prevents the old 4-entity test data from mixing with
# the real Neo4j data.
LIGHTRAG_WORKING_DIR = BASE_DIR / "lightrag_neo4j_test"

EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
EMBEDDING_DIMENSION = 1024
EMBEDDING_MAX_TOKEN_SIZE = 32768

from graph.llm_client import (
    LLM_BASE_URL,
    LLM_API_KEY,
    LLM_MODEL,
    get_openrouter_headers,
)


# ============================================================
# LIGHTRAG LLM
# ============================================================

async def llm_model_func(
    prompt,
    system_prompt=None,
    history_messages=None,
    **kwargs,
):

    if history_messages is None:
        history_messages = []

    headers = get_openrouter_headers(LLM_BASE_URL)
    return await openai_complete_if_cache(
        model=LLM_MODEL,
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        headers=headers if headers else None,
        **kwargs,
    )


# ============================================================
# LIGHTRAG RETRIEVER
# ============================================================

class LightRAGRetriever:

    def __init__(self):

        print("=" * 60)
        print("INITIALIZING LIGHTRAG")
        print("=" * 60)

        LIGHTRAG_WORKING_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ----------------------------------------------------
        # Load Qwen embedding model
        # ----------------------------------------------------

        print(
            f"\nLoading embedding model: "
            f"{EMBEDDING_MODEL}"
        )

        device = (
            "cuda"
            if __import__("torch").cuda.is_available()
            else "cpu"
        )

        self.embedding_model = SentenceTransformer(
            EMBEDDING_MODEL,
            device=device,
        )

        dimension = (
            self.embedding_model
            .get_embedding_dimension()
        )

        print(f"Embedding dimension: {dimension}")
        print(f"Embedding device: {device}")

        if dimension != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Expected embedding dimension "
                f"{EMBEDDING_DIMENSION}, "
                f"but got {dimension}"
            )

        # ----------------------------------------------------
        # LightRAG embedding function
        # ----------------------------------------------------

        async def embedding_func(
            texts: list[str],
        ) -> np.ndarray:

            embeddings = self.embedding_model.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )

            return embeddings.astype(np.float32)

        self.embedding_func = EmbeddingFunc(
            embedding_dim=EMBEDDING_DIMENSION,
            max_token_size=EMBEDDING_MAX_TOKEN_SIZE,
            model_name=EMBEDDING_MODEL,
            func=embedding_func,
        )

        print("✓ Embedding function configured")

        # ----------------------------------------------------
        # Initialize LightRAG
        # ----------------------------------------------------

        print("\nCreating LightRAG instance...")

        self.rag = LightRAG(
            working_dir=str(LIGHTRAG_WORKING_DIR),
            embedding_func=self.embedding_func,
            llm_model_func=llm_model_func,
        )

        print("✓ LightRAG instance created")

    # ========================================================
    # INITIALIZE STORAGE
    # ========================================================

    async def initialize(self):

        print("\nInitializing LightRAG storages...")

        await self.rag.initialize_storages()

        print("✓ LightRAG storages initialized")

    # ========================================================
    # CONVERT NEO4J PROPERTIES TO TEXT
    # ========================================================

    @staticmethod
    def properties_to_text(properties):

        if not properties:
            return ""

        parts = []

        for key, value in properties.items():

            if value is None:
                continue

            # Avoid huge / meaningless values
            if isinstance(value, (list, tuple)):
                value = ", ".join(
                    str(item)
                    for item in value
                )

            parts.append(
                f"{key}: {value}"
            )

        return "\n".join(parts)

    # ========================================================
    # BUILD ENTITY
    # ========================================================

    @staticmethod
    def build_entity(
        entity_name,
        entity_type,
        properties,
    ):

        description = (
            f"{entity_type} {entity_name}\n"
            f"{LightRAGRetriever.properties_to_text(properties)}"
        )

        return {
            "entity_name": entity_name,
            "entity_type": entity_type,
            "description": description,
            "source_id": "neo4j_structured_data",
        }

    # ========================================================
    # BUILD RELATIONSHIP
    # ========================================================

    @staticmethod
    def build_relationship(
        src_id,
        tgt_id,
        relation_type,
        description,
    ):

        return {
            "src_id": src_id,
            "tgt_id": tgt_id,
            "description": description,
            "keywords": relation_type.lower(),
            "weight": 1.0,
            "source_id": "neo4j_structured_data",
        }

    # ========================================================
    # GET TESTCASE DATA FROM NEO4J
    # ========================================================

    def get_testcase_from_neo4j(
        self,
        test_case_id,
    ):

        neo4j = Neo4jGraphRetriever()

        try:

            # ------------------------------------------------
            # TestCase
            # ------------------------------------------------

            testcase = neo4j.get_testcase(
                test_case_id
            )

            if testcase is None:
                raise ValueError(
                    f"TestCase {test_case_id} "
                    f"was not found in Neo4j."
                )

            # ------------------------------------------------
            # TestCase → Execution → Defect
            # ------------------------------------------------

            paths = neo4j.get_testcase_execution_defects(
                test_case_id
            )

            return testcase, paths

        finally:

            neo4j.close()

    # ========================================================
    # CONVERT NEO4J SAMPLE TO LIGHTRAG CUSTOM KG
    # ========================================================

    def build_custom_kg_from_neo4j(
        self,
        test_case_id,
    ):

        print("\nReading data from Neo4j...")

        testcase, paths = (
            self.get_testcase_from_neo4j(
                test_case_id
            )
        )

        print(
            f"✓ TestCase retrieved: "
            f"{test_case_id}"
        )

        print(
            f"✓ Multi-hop paths retrieved: "
            f"{len(paths)}"
        )

        entities = {}
        relationships = []

        # ----------------------------------------------------
        # TestCase entity
        # ----------------------------------------------------

        entities[test_case_id] = (
            self.build_entity(
                entity_name=test_case_id,
                entity_type="TestCase",
                properties=testcase,
            )
        )

        # ----------------------------------------------------
        # Process each TestCase → Execution → Defect path
        # ----------------------------------------------------

        for path in paths:

            execution = path["execution"]
            defect = path["defect"]

            execution_id = execution.get(
                "execution_id"
            )

            defect_id = defect.get(
                "defect_id"
            )

            if not execution_id or not defect_id:
                continue

            # -----------------------------------------------
            # Execution entity
            # -----------------------------------------------

            entities[execution_id] = (
                self.build_entity(
                    entity_name=execution_id,
                    entity_type="Execution",
                    properties=execution,
                )
            )

            # -----------------------------------------------
            # Defect entity
            # -----------------------------------------------

            entities[defect_id] = (
                self.build_entity(
                    entity_name=defect_id,
                    entity_type="Defect",
                    properties=defect,
                )
            )

            # -----------------------------------------------
            # TestCase → Execution
            # -----------------------------------------------

            relationships.append(
                self.build_relationship(
                    src_id=test_case_id,
                    tgt_id=execution_id,
                    relation_type="HAS_EXECUTION",
                    description=(
                        f"TestCase {test_case_id} "
                        f"has execution {execution_id}."
                    ),
                )
            )

            # -----------------------------------------------
            # TestCase → Defect
            # -----------------------------------------------

            relationships.append(
                self.build_relationship(
                    src_id=test_case_id,
                    tgt_id=defect_id,
                    relation_type="HAS_DEFECT",
                    description=(
                        f"TestCase {test_case_id} "
                        f"has defect {defect_id}."
                    ),
                )
            )

            # -----------------------------------------------
            # Execution → Defect
            # -----------------------------------------------

            relationships.append(
                self.build_relationship(
                    src_id=execution_id,
                    tgt_id=defect_id,
                    relation_type="FOUND_DEFECT",
                    description=(
                        f"Execution {execution_id} "
                        f"found defect {defect_id}."
                    ),
                )
            )

        # ----------------------------------------------------
        # Remove duplicate relationships
        # ----------------------------------------------------

        unique_relationships = {}

        for relationship in relationships:

            key = (
                relationship["src_id"],
                relationship["tgt_id"],
                relationship["keywords"],
            )

            unique_relationships[key] = relationship

        relationships = list(
            unique_relationships.values()
        )

        # ----------------------------------------------------
        # Build textual chunk
        # ----------------------------------------------------

        chunk_lines = []

        for entity in entities.values():

            chunk_lines.append(
                entity["description"]
            )

        for relationship in relationships:

            chunk_lines.append(
                relationship["description"]
            )

        chunk = {
            "content": "\n".join(chunk_lines),
            "source_id": "neo4j_structured_data",
        }

        custom_kg = {
            "entities": list(entities.values()),
            "relationships": relationships,
            "chunks": [chunk],
        }

        return custom_kg

    # ========================================================
    # INSERT NEO4J DATA INTO LIGHTRAG
    # ========================================================

    async def insert_neo4j_testcase(
        self,
        test_case_id,
    ):

        print("\n" + "=" * 60)
        print("NEO4J → LIGHTRAG")
        print("=" * 60)

        custom_kg = (
            self.build_custom_kg_from_neo4j(
                test_case_id
            )
        )

        print(
            f"\nEntities prepared: "
            f"{len(custom_kg['entities'])}"
        )

        print(
            f"Relationships prepared: "
            f"{len(custom_kg['relationships'])}"
        )

        print(
            f"Chunks prepared: "
            f"{len(custom_kg['chunks'])}"
        )

        print("\nInserting into LightRAG...")

        await self.rag.ainsert_custom_kg(
            custom_kg
        )

        print("✓ Neo4j data inserted into LightRAG")

    # ========================================================
    # QUERY LIGHTRAG
    # ========================================================

    async def query(
        self,
        question,
        mode="hybrid",
    ):

        param = QueryParam(
            mode=mode,
            only_need_context=True,
            top_k=10,
            enable_rerank=False,
        )

        result = await self.rag.aquery_data(
            question,
            param=param,
        )

        return result


# ============================================================
# MAIN TEST
# ============================================================

async def main():

    print("=" * 60)
    print("NEO4J → LIGHTRAG INTEGRATION TEST")
    print("=" * 60)

    test_case_id = "TC-000001"

    retriever = LightRAGRetriever()

    await retriever.initialize()

    # --------------------------------------------------------
    # Import real Neo4j data
    # --------------------------------------------------------

    await retriever.insert_neo4j_testcase(
        test_case_id
    )

    # --------------------------------------------------------
    # Query
    # --------------------------------------------------------

    question = (
        "Which defects were found in the execution "
        "of test case TC-000001?"
    )

    print("\n" + "=" * 60)
    print("QUERY")
    print("=" * 60)

    print(f"\nQuestion:")
    print(question)

    print("\nRetrieval mode:")
    print("hybrid")

    result = await retriever.query(
        question,
        mode="hybrid",
    )

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("LIGHTRAG RETRIEVAL RESULT")
    print("=" * 60)

    print(result)

    print("\n" + "=" * 60)
    print("✓ NEO4J → LIGHTRAG TEST COMPLETED")
    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())