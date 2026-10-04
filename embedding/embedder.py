import torch
from sentence_transformers import SentenceTransformer

from .config import (
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    QUERY_INSTRUCTION,
)


class EmbeddingModel:
    """
    Wrapper around Qwen3-Embedding-0.6B.
    """

    def __init__(self):
        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        print(f"Device: {self.device}")

        self.model = SentenceTransformer(
            EMBEDDING_MODEL,
            device=self.device,
        )

        self.dimension = (
            self.model.get_sentence_embedding_dimension()
        )

        print(f"Embedding dimension: {self.dimension}")

        if self.dimension != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Unexpected embedding dimension: "
                f"{self.dimension}. "
                f"Expected {EMBEDDING_DIMENSION}."
            )

    def embed_document(self, text):
        """
        Generate an embedding for a stored document/node.
        """

        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        return embedding

    def embed_query(self, query):
        """
        Generate an embedding for a user query.
        """

        embedding = self.model.encode(
            query,
            prompt_name="query",
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        return embedding