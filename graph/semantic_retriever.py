import re
from typing import Dict, Any, List, Optional
import numpy as np

from graph.retrieval_config import (
    VECTOR_INDEXES,
    FULLTEXT_INDEX,
    VECTOR_TOP_K,
    VECTOR_OVERFETCH,
    RRF_K,
    EMBEDDING_DIM,
    QUERY_INSTRUCTION,
    USE_QUERY_INSTRUCTION,
    ENABLE_RERANKER,
    RERANKER_MODEL,
    RERANK_CANDIDATE_LIMIT,
)
from graph.graph_retriever import Neo4jGraphRetriever, _clean_props


_embedder_instance = None
_numpy_search_instance = None
_reranker_instance = None


def get_embedder():
    """Lazy module-level singleton for EmbeddingModel."""
    global _embedder_instance
    if _embedder_instance is None:
        from embedding.embedder import EmbeddingModel
        _embedder_instance = EmbeddingModel()
    return _embedder_instance


def get_numpy_search():
    """Lazy singleton for numpy brute-force SemanticSearch fallback."""
    global _numpy_search_instance
    if _numpy_search_instance is None:
        from embedding.semantic_search import SemanticSearch
        _numpy_search_instance = SemanticSearch()
    return _numpy_search_instance


def get_reranker():
    """Lazy singleton for local CrossEncoder reranker (BAAI/bge-reranker-base)."""
    global _reranker_instance
    if _reranker_instance is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker_instance = CrossEncoder(RERANKER_MODEL)
        except Exception as e:
            print(f"Warning: Could not initialize CrossEncoder reranker ({e})")
            _reranker_instance = None
    return _reranker_instance


def _format_candidate_text(hit: Dict[str, Any], target_entity: str) -> str:
    """Format candidate attributes into a clean text block for cross-encoder scoring."""
    if target_entity == "defect":
        parts = []
        if hit.get("title"):
            parts.append(f"Title: {hit['title']}")
        if hit.get("description"):
            parts.append(f"Description: {hit['description']}")
        if hit.get("root_cause"):
            parts.append(f"Root Cause: {hit['root_cause']}")
        if hit.get("module"):
            parts.append(f"Module: {hit['module']}")
        if hit.get("bug_type"):
            parts.append(f"Bug Type: {hit['bug_type']}")
        if hit.get("severity"):
            parts.append(f"Severity: {hit['severity']}")
        return "\n".join(parts) if parts else str(hit)
    elif target_entity == "test_case":
        parts = []
        if hit.get("feature"):
            parts.append(f"Feature: {hit['feature']}")
        if hit.get("module"):
            parts.append(f"Module: {hit['module']}")
        if hit.get("test_steps"):
            parts.append(f"Test Steps: {hit['test_steps']}")
        if hit.get("expected_result"):
            parts.append(f"Expected Result: {hit['expected_result']}")
        return "\n".join(parts) if parts else str(hit)
    elif target_entity == "screenshot":
        parts = []
        if hit.get("screen_name"):
            parts.append(f"Screen: {hit['screen_name']}")
        if hit.get("user_action"):
            parts.append(f"Action: {hit['user_action']}")
        if hit.get("error_messages"):
            parts.append(f"Errors: {hit['error_messages']}")
        return "\n".join(parts) if parts else str(hit)
    return str(hit)


def sanitize_lucene_query(terms: Any) -> str:
    """Escape Lucene special characters and drop bare boolean words."""
    if isinstance(terms, str):
        terms = [t for t in re.findall(r'[^\s]+', terms)]
    stopwords = {"and", "or", "not", "the", "a", "an", "in", "on", "for", "of", "to", "at", "by", "with", "is", "was"}
    sanitized = []
    for t in terms:
        t_clean = t.strip()
        if not t_clean or t_clean.lower() in stopwords:
            continue
        escaped = ""
        for ch in t_clean:
            if ch in r'+-!(){}[]^"~*?:\/':
                escaped += "\\" + ch
            else:
                escaped += ch
        if escaped and escaped.upper() not in {"AND", "OR", "NOT"}:
            sanitized.append(escaped)
    return " ".join(sanitized)


escape_lucene_query = sanitize_lucene_query


class SemanticRetriever:

    def __init__(self, graph_retriever: Optional[Neo4jGraphRetriever] = None):
        self._graph_retriever = graph_retriever
        self._own_graph_retriever = False
        if self._graph_retriever is None:
            self._graph_retriever = Neo4jGraphRetriever()
            self._own_graph_retriever = True

    def close(self):
        if self._own_graph_retriever and self._graph_retriever:
            self._graph_retriever.close()

    def _get_query_vector(self, question: str, use_instruction: bool = USE_QUERY_INSTRUCTION) -> List[float]:
        """Compute normalized float list query embedding."""
        embedder = get_embedder()
        q_text = f"Instruct: {QUERY_INSTRUCTION}\nQuery: {question}" if use_instruction else question
        vec = embedder.embed_query(q_text)
        assert len(vec) == EMBEDDING_DIM, f"Query vector dim {len(vec)} != {EMBEDDING_DIM}"
        vec_f32 = np.asarray(vec, dtype=np.float32)
        norm = np.linalg.norm(vec_f32)
        if norm > 0:
            vec_f32 = vec_f32 / norm
        return [float(x) for x in vec_f32]

    def _vector_search_neo4j(
        self,
        target_entity: str,
        vec: List[float],
        k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """Run vector search in Neo4j with optional over-fetching and WHERE filtering."""
        idx_name = VECTOR_INDEXES.get(target_entity, VECTOR_INDEXES["defect"])
        where_clauses = []
        params = {"index": idx_name, "k": k, "vec": vec}

        # Where clauses for over-fetched filtering
        if filters:
            if target_entity == "defect":
                for f_key, val in filters.items():
                    if f_key in Neo4jGraphRetriever.DEFECT_FILTER_REGISTRY and val:
                        pname = f"f_{f_key}"
                        col = Neo4jGraphRetriever.DEFECT_FILTER_REGISTRY[f_key].replace("d.", "node.")
                        where_clauses.append(f"{col} = ${pname}")
                        params[pname] = val
                    elif f_key == "module" and val:
                        where_clauses.append("node.module = $f_module")
                        params["f_module"] = val
            elif target_entity == "test_case":
                for f_key, val in filters.items():
                    if f_key in Neo4jGraphRetriever.TC_FILTER_REGISTRY and val:
                        pname = f"f_{f_key}"
                        col = Neo4jGraphRetriever.TC_FILTER_REGISTRY[f_key].replace("t.", "node.")
                        where_clauses.append(f"{col} = ${pname}")
                        params[pname] = val
                    elif f_key == "module" and val:
                        where_clauses.append("node.module = $f_module")
                        params["f_module"] = val

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        if target_entity == "defect":
            cypher = f"""
            CALL db.index.vector.queryNodes($index, $k, $vec) YIELD node, score
            {where_str}
            RETURN node.defect_id AS defect_id,
                   node.title AS title,
                   node.description AS description,
                   node.root_cause AS root_cause,
                   node.severity AS severity,
                   node.priority AS priority,
                   node.status AS status,
                   node.module AS module,
                   node.bug_type AS bug_type,
                   score
            ORDER BY score DESC
            """
        elif target_entity == "test_case":
            cypher = f"""
            CALL db.index.vector.queryNodes($index, $k, $vec) YIELD node, score
            {where_str}
            RETURN node.test_case_id AS test_case_id,
                   node.module AS module,
                   node.feature AS feature,
                   node.test_steps AS test_steps,
                   node.expected_result AS expected_result,
                   node.priority AS priority,
                   node.severity AS severity,
                   node.status AS status,
                   score
            ORDER BY score DESC
            """
        elif target_entity == "screenshot":
            cypher = f"""
            CALL db.index.vector.queryNodes($index, $k, $vec) YIELD node, score
            {where_str}
            RETURN node.screenshot_id AS screenshot_id,
                   node.screen_name AS screen_name,
                   node.user_action AS user_action,
                   node.error_messages AS error_messages,
                   node.warning_messages AS warning_messages,
                   node.module AS module,
                   score
            ORDER BY score DESC
            """
        else:
            raise ValueError(f"Unknown target entity: {target_entity}")

        with self._graph_retriever._session() as session:
            res = session.run(cypher, params)
            hits = [dict(r) for r in res]
            prefilter_count = k

        return hits, prefilter_count

    def _fulltext_search_defects(self, keywords: List[str], k: int) -> List[Dict[str, Any]]:
        """Run fulltext search on defect_text index."""
        if not self._graph_retriever.has_fulltext:
            return []
        q_str = sanitize_lucene_query(keywords)
        if not q_str:
            return []

        cypher = """
        CALL db.index.fulltext.queryNodes($index, $q, {limit: $k}) YIELD node, score
        RETURN node.defect_id AS defect_id,
               node.title AS title,
               node.description AS description,
               node.root_cause AS root_cause,
               node.severity AS severity,
               node.priority AS priority,
               node.status AS status,
               node.module AS module,
               node.bug_type AS bug_type,
               score
        ORDER BY score DESC
        """
        with self._graph_retriever._session() as session:
            res = session.run(cypher, {"index": FULLTEXT_INDEX, "q": q_str, "k": k})
            return [dict(r) for r in res]

    def _rrf_fuse_defects(
        self,
        vector_hits: List[Dict[str, Any]],
        fulltext_hits: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion over vector and fulltext lists."""
        fused = {}
        for rank, hit in enumerate(vector_hits, start=1):
            did = hit["defect_id"]
            if did not in fused:
                fused[did] = {
                    **hit,
                    "vector_rank": rank,
                    "fulltext_rank": None,
                    "sources": ["vector"],
                    "fused_score": 1.0 / (RRF_K + rank),
                }

        for rank, hit in enumerate(fulltext_hits, start=1):
            did = hit["defect_id"]
            score_addition = 1.0 / (RRF_K + rank)
            if did in fused:
                fused[did]["fulltext_rank"] = rank
                fused[did]["sources"].append("fulltext")
                fused[did]["fused_score"] += score_addition
            else:
                fused[did] = {
                    **hit,
                    "vector_rank": None,
                    "fulltext_rank": rank,
                    "sources": ["fulltext"],
                    "fused_score": score_addition,
                }

        sorted_hits = sorted(fused.values(), key=lambda x: x["fused_score"], reverse=True)
        return sorted_hits[:limit]

    def _rerank_candidates(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        target_entity: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates using local CrossEncoder model (BAAI/bge-reranker-base).
        Attaches 'rerank_score' to each candidate and returns top_k.
        """
        if not candidates:
            return []

        reranker = get_reranker()
        if reranker is None:
            return candidates[:top_k]

        try:
            pairs = [(query, _format_candidate_text(c, target_entity)) for c in candidates]
            scores = reranker.predict(pairs)
            reranked = []
            for idx, cand in enumerate(candidates):
                score_raw = scores[idx]
                score_val = float(score_raw) if hasattr(score_raw, "__float__") else float(score_raw[0])
                cand_copy = dict(cand)
                cand_copy["rerank_score"] = score_val
                reranked.append(cand_copy)

            reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
            return reranked[:top_k]
        except Exception as e:
            print(f"Warning: Reranker prediction failed ({e}). Falling back to candidate order.")
            return candidates[:top_k]

    def search(
        self,
        question: str,
        understanding: Optional[Dict[str, Any]] = None,
        limit: int = VECTOR_TOP_K,
        enable_reranker: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Perform semantic search across Defect, TestCase, or Screenshot.
        Optionally applies second-stage cross-encoder reranking over top candidates.
        """
        understanding = understanding or {}
        target_entity = understanding.get("target_entity", "defect")
        if target_entity not in {"defect", "test_case", "screenshot"}:
            target_entity = "defect"

        use_reranker = ENABLE_RERANKER if enable_reranker is None else enable_reranker
        filters = understanding.get("filters", {})
        has_filters = bool(filters)
        errors = []

        # Backend selection
        backend = "neo4j_vector" if self._graph_retriever.has_vector(target_entity) else "numpy"

        hits = []
        prefilter_count = 0
        template = "semantic_vector"

        try:
            vec = self._get_query_vector(question)
        except Exception as e:
            errors.append(f"Vector embedding failed: {e}")
            return {
                "template": template,
                "target_entity": target_entity,
                "backend": backend,
                "hits": [],
                "prefilter_count": 0,
                "filters_applied": filters,
                "errors": errors,
            }

        if backend == "neo4j_vector":
            fetch_k = VECTOR_OVERFETCH if has_filters else (max(limit, RERANK_CANDIDATE_LIMIT) if use_reranker else limit)
            try:
                raw_hits, prefilter_count = self._vector_search_neo4j(
                    target_entity=target_entity,
                    vec=vec,
                    k=fetch_k,
                    filters=filters if has_filters else None,
                )
            except Exception as e:
                errors.append(f"Neo4j vector search error: {e}")
                raw_hits = []

            if has_filters:
                template = "semantic_filtered"
                if use_reranker and len(raw_hits) > 1:
                    cand_k = min(len(raw_hits), max(limit, RERANK_CANDIDATE_LIMIT))
                    hits = self._rerank_candidates(question, raw_hits[:cand_k], target_entity, limit)
                    template = "semantic_filtered_reranked"
                else:
                    hits = raw_hits[:limit]
            elif target_entity == "defect" and self._graph_retriever.has_fulltext:
                # Hybrid RRF fusion with fulltext
                template = "semantic_hybrid"
                kw = understanding.get("low_level_keywords", [])
                if not kw:
                    kw = [w for w in re.findall(r"\b\w+\b", question) if len(w) > 3]
                try:
                    ft_hits = self._fulltext_search_defects(kw, fetch_k)
                except Exception as e:
                    errors.append(f"Fulltext search error: {e}")
                    ft_hits = []

                cand_k = max(limit, RERANK_CANDIDATE_LIMIT) if use_reranker else limit
                fused = self._rrf_fuse_defects(raw_hits, ft_hits, cand_k)
                if use_reranker and len(fused) > 1:
                    hits = self._rerank_candidates(question, fused, target_entity, limit)
                    template = "semantic_hybrid_reranked"
                else:
                    hits = fused[:limit]
            else:
                if use_reranker and len(raw_hits) > 1:
                    cand_k = min(len(raw_hits), max(limit, RERANK_CANDIDATE_LIMIT))
                    hits = self._rerank_candidates(question, raw_hits[:cand_k], target_entity, limit)
                    template = "semantic_vector_reranked"
                else:
                    template = "semantic_vector"
                    hits = raw_hits[:limit]

        else:
            # Numpy brute-force fallback
            try:
                np_search = get_numpy_search()
                fetch_limit = max(limit, RERANK_CANDIDATE_LIMIT) if use_reranker else limit
                if target_entity == "defect":
                    raw_np_hits = np_search.search_defects(question, top_k=fetch_limit)
                else:
                    raw_np_hits = np_search.search_testcases(question, top_k=fetch_limit)
                prefilter_count = len(raw_np_hits)

                if use_reranker and len(raw_np_hits) > 1:
                    hits = self._rerank_candidates(question, raw_np_hits, target_entity, limit)
                    template = "semantic_numpy_reranked"
                else:
                    template = "semantic_numpy"
                    hits = raw_np_hits[:limit]
            except Exception as e:
                errors.append(f"Numpy fallback error: {e}")
                hits = []

        return {
            "template": template,
            "target_entity": target_entity,
            "backend": backend,
            "hits": hits,
            "prefilter_count": prefilter_count,
            "filters_applied": filters,
            "errors": errors,
        }
